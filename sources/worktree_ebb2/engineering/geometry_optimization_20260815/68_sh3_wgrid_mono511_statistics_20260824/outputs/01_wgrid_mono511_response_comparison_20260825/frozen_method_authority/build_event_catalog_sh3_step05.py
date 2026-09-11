#!/usr/bin/env python3
"""Build the M05-compliant SH3 OptV3 compact event/deposit catalog.

Streams accepted receipts from the original four all-family rounds, 31 valid
gamma-only expansion rounds, and 33 delayed shards (8 M triggers).
into per-job npz caches keyed by (stream, family, batch, job_id), then merges
into a combined catalog with:
  - TES pixel hit list (Gaussian-smeared, threshold-cut)
  - plastic scalar (IDENTITY-PASS: always 0 in OptV3, no plastic layer)
  - BGO scalar (sum over 3 SH3_BGO40_* volumes)
  - broad / w2 stage-bit flags

Categories = (stream, family, source_parent_ZA).  Delayed source_parent_ZA is
recovered from the retained exact-production-position table.  IA INIT ZA is a
diagnostic only, as required by the M05 handoff.  Prompt has ZA = -1.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np


HERE = Path(__file__).resolve()
PACKAGE = HERE.parents[1]
CONFIG = PACKAGE / "modified/analysis_inputs_optv3_B.json"
OUT = PACKAGE / "outputs/04_event_catalog_step05_m05_fixed_20260820"
CACHE = OUT / "job_catalogs"
LEGACY_CACHE = PACKAGE / "outputs/01_event_catalog_step05/job_catalogs"

sys.path.insert(0, str(HERE.parent))
from step05_side_compton import side_keep_from_hits, side_entry_disk  # noqa: E402


FWHM_KEV = 0.420
SIGMA_KEV = FWHM_KEV / 2.3548200450309493
PIXEL_THRESHOLD_KEV = 0.3

WINDOWS = {
    "broad_480_550": (480.0, 550.0),
    "w2_510p58_511p42": (510.58, 511.42),
}
STAGE_BITS = {
    "pre_veto":                     1 << 0,
    "plastic_positron_veto":        1 << 1,
    "bgo_active_scintillator_veto": 1 << 2,
    "combined_active_veto":         1 << 3,
    "compton_trajectory_veto":      1 << 4,
}

ID_RE = re.compile(r"^ID\s+(\d+)\s+\d+")
TP_RE = re.compile(r"^TP_L(?P<layer>\d+)_(?P<pixel>\d+)$")
CC_HIT_RE = re.compile(
    r"^CC HIT\s+(\S+)\s+edep_keV=([-\deE\.+]+)\s+x=([-\deE\.+]+)\s+y=([-\deE\.+]+)\s+z=([-\deE\.+]+)"
)
_M05_COMMON: Any | None = None


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def m05_common() -> Any:
    global _M05_COMMON
    if _M05_COMMON is None:
        cfg = load_json(CONFIG)
        path = Path(cfg["m05_common_time_code"])
        spec = importlib.util.spec_from_file_location("sh3_optv3_m05_common", path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot import M05 common-time authority: {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        _M05_COMMON = module
    return _M05_COMMON


def validate_source(receipt: dict[str, Any]) -> None:
    source = Path(receipt["source_path"])
    if not source.is_file():
        raise RuntimeError(f"source card missing: {source}")
    text = source.read_text(encoding="utf-8")
    if "cosima_spectra_dp_2602units" in text:
        raise RuntimeError(f"legacy factor-1000 spectrum reference: {source}")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if digest != receipt.get("source_sha256"):
        raise RuntimeError(f"source SHA mismatch: {source}")


def validate_controller(bundle: Path, expected_jobs: int | None = None) -> None:
    state = load_json(bundle / "run/controller_state.json")
    receipts = list((bundle / "run/receipts").glob("*.json"))
    if state.get("status") != "COMPLETE" or state.get("error") is not None:
        raise RuntimeError(f"controller is not COMPLETE: {bundle}")
    if int(state.get("completed_count", -1)) != len(receipts):
        raise RuntimeError(f"controller/receipt count mismatch: {bundle}")
    if expected_jobs is not None and len(receipts) != expected_jobs:
        raise RuntimeError(f"receipt count {len(receipts)} != {expected_jobs}: {bundle}")


def keyed_standard_normal(*keys: Any) -> float:
    payload = "|".join(str(k) for k in keys).encode("utf-8")
    digest = hashlib.blake2b(payload, digest_size=16).digest()
    u1 = int.from_bytes(digest[:8], "little") / 2**64
    u2 = int.from_bytes(digest[8:], "little") / 2**64
    u1 = max(u1, 1e-300)
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def in_window(value: float, bounds: tuple[float, float]) -> bool:
    return bounds[0] <= value < bounds[1]


def topology_keep(measured_hits: list[Any]) -> bool:
    """Deprecated compatibility stub; flags_for_event uses real Step05."""
    if len(measured_hits) == 0:
        return False
    return True


def flags_for_event(
    measured_hits: list[Any], measured_total: float,
    plastic_keV: float, bgo_keV: float, threshold_keV: float,
    disk: dict[str, Any], reject_policy: str,
) -> tuple[int, int]:
    plastic_pass = plastic_keV < threshold_keV
    bgo_pass = bgo_keV < threshold_keV
    combined = plastic_pass and bgo_pass
    topo = combined and side_keep_from_hits(measured_hits, disk, reject_policy)[0]
    bits_broad = 0
    if in_window(measured_total, WINDOWS["broad_480_550"]):
        bits_broad |= STAGE_BITS["pre_veto"]
        if plastic_pass: bits_broad |= STAGE_BITS["plastic_positron_veto"]
        if bgo_pass:     bits_broad |= STAGE_BITS["bgo_active_scintillator_veto"]
        if combined:     bits_broad |= STAGE_BITS["combined_active_veto"]
        if topo:         bits_broad |= STAGE_BITS["compton_trajectory_veto"]
    bits_w2 = 0
    if in_window(measured_total, WINDOWS["w2_510p58_511p42"]):
        bits_w2 |= STAGE_BITS["pre_veto"]
        if plastic_pass: bits_w2 |= STAGE_BITS["plastic_positron_veto"]
        if bgo_pass:     bits_w2 |= STAGE_BITS["bgo_active_scintillator_veto"]
        if combined:     bits_w2 |= STAGE_BITS["combined_active_veto"]
        if topo:         bits_w2 |= STAGE_BITS["compton_trajectory_veto"]
    return bits_broad, bits_w2


def prepare_jobs(cfg: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Enumerate accepted receipts for corrected (INSTANT+BUILDUP, prompt) + delayed."""
    corrected_root = Path(cfg["campaigns"]["corrected_root"])
    corrected_root_overrides = {
        name: Path(path) for name, path in cfg["campaigns"].get("corrected_root_overrides", {}).items()
    }
    delayed_root = Path(cfg["campaigns"]["delayed_root"])
    activation_manifest = load_json(Path(cfg["campaigns"]["activation_manifest"]))
    day15 = {
        cell["family"]: float(cell["transported_ground_activity_Bq"])
        for cell in activation_manifest["activation_cells"]
    }
    positions_by_family = {
        cell["family"]: cell["positions_path"] for cell in activation_manifest["source_cells"]
    }

    plastic_volumes = list(cfg["active_veto"]["plastic_positron_veto_volumes"])
    bgo_volumes = list(cfg["active_veto"]["bgo_active_scintillator_volumes"])

    # ---- CORRECTED (prompt): TT per family = sum(TT_s) over all accepted instant receipts (across rounds) ----
    # BUILDUP is a separate physics: it produces the inventory used by delayed, but does NOT enter the
    # prompt event pool.  For the mature timeline we only sample from INSTANT.
    prompt_jobs: list[dict[str, Any]] = []
    prompt_tt_by_family: dict[str, float] = defaultdict(float)
    prompt_instant_events_by_family: dict[str, int] = defaultdict(int)

    for round_name in cfg["campaigns"]["corrected_rounds"]:
        root = corrected_root_overrides.get(round_name, corrected_root)
        bundle = root / "rounds" / round_name / "corrected"
        rec_dir = bundle / "run/receipts"
        if not rec_dir.is_dir():
            raise RuntimeError(f"configured corrected round is missing: {round_name} at {root}")
        validate_controller(bundle)
        for rpath in sorted(rec_dir.iterdir()):
            r = load_json(rpath)
            if r.get("status") != "PASS":
                raise RuntimeError(f"non-PASS receipt in configured round: {rpath}")
            if r.get("mode") != "instant":
                continue
            validate_source(r)
            expected = Path(cfg["geometry_authority"]["setup_path"]).resolve()
            if Path(r["setup_path"]).resolve() != expected:
                raise RuntimeError(f"receipt geometry mismatch: {rpath}")
            header = r.get("sim_header", {})
            if Path(str(header.get("geometry", ""))).resolve() != expected:
                raise RuntimeError(f"receipt SIM-header geometry mismatch: {rpath}")
            if int(header.get("seed", -1)) != int(r["seed"]):
                raise RuntimeError(f"receipt SIM-header seed mismatch: {rpath}")
            family = r["family"]
            tt = float(r["isotope_dat"]["TT_s"])
            prompt_tt_by_family[family] += tt
            prompt_instant_events_by_family[family] += int(r["events"])
            prompt_jobs.append({
                "stream": "prompt",
                "family": family,
                "batch_id": round_name,
                "job_id": r["job_id"],
                "seed": int(r["seed"]),
                "events": int(r["events"]),
                "sim_path": r["sim_path"],
                "sim_bytes": int(r["sim_bytes"]),
                "source_path": r["source_path"],
                "TT_s": tt,
                "expected_geometry": r["setup_path"],
                "plastic_volumes": plastic_volumes,
                "bgo_volumes": bgo_volumes,
                "positions_path": None,
                "mode": "instant",
            })

    # ---- DELAYED: per-family weight = A_f(15) / total_triggers_f (should be 1_000_000 per family) ----
    delayed_jobs: list[dict[str, Any]] = []
    delayed_triggers_by_family: dict[str, int] = defaultdict(int)
    rec_dir = delayed_root / "run/receipts"
    validate_controller(delayed_root, expected_jobs=33)
    for rpath in sorted(rec_dir.iterdir()):
        r = load_json(rpath)
        if r.get("status") != "PASS":
            raise RuntimeError(f"non-PASS delayed receipt: {rpath}")
        validate_source(r)
        expected = Path(cfg["geometry_authority"]["setup_path"]).resolve()
        if Path(r["setup_path"]).resolve() != expected:
            raise RuntimeError(f"delayed receipt geometry mismatch: {rpath}")
        header = r.get("sim_header", {})
        if Path(str(header.get("geometry", ""))).resolve() != expected:
            raise RuntimeError(f"delayed receipt SIM-header geometry mismatch: {rpath}")
        if int(header.get("seed", -1)) != int(r["seed"]):
            raise RuntimeError(f"delayed receipt SIM-header seed mismatch: {rpath}")
        family = r["family"]
        delayed_triggers_by_family[family] += int(r["events"])
        delayed_jobs.append({
            "stream": "delayed",
            "family": family,
            "batch_id": "delayed_v1",
            "job_id": r["job_id"],
            "seed": int(r["seed"]),
            "events": int(r["events"]),
            "sim_path": r["sim_path"],
            "sim_bytes": int(r["sim_bytes"]),
            "source_path": r["source_path"],
            "TT_s": None,
            "expected_geometry": r["setup_path"],
            "plastic_volumes": plastic_volumes,
            "bgo_volumes": bgo_volumes,
            "positions_path": positions_by_family[family],
            "mode": "delayed",
        })

    # Attach weights (cps per event).
    scan_index = 0
    for job in prompt_jobs:
        family = job["family"]
        total_tt = prompt_tt_by_family[family]
        job["weight_cps"] = 1.0 / total_tt if total_tt > 0 else 0.0
        job["scan_index"] = scan_index; scan_index += 1
    for job in delayed_jobs:
        family = job["family"]
        total_triggers = delayed_triggers_by_family[family]
        A15 = day15.get(family, 0.0)
        job["weight_cps"] = (A15 / total_triggers) if total_triggers > 0 else 0.0
        job["A15_Bq"] = A15
        job["scan_index"] = scan_index; scan_index += 1

    if set(delayed_triggers_by_family) != set(day15) or any(
        delayed_triggers_by_family[family] != 1_000_000 for family in day15
    ):
        raise RuntimeError(f"delayed one-million trigger closure differs: {dict(delayed_triggers_by_family)}")
    seeds = [int(job["seed"]) for job in prompt_jobs + delayed_jobs]
    if len(seeds) != len(set(seeds)):
        raise RuntimeError("registered seed reuse within analyzed jobs")

    audit = {
        "prompt_sum_TT_s_by_family": dict(prompt_tt_by_family),
        "prompt_instant_events_by_family": dict(prompt_instant_events_by_family),
        "prompt_jobs": len(prompt_jobs),
        "delayed_day15_activity_Bq_by_family": day15,
        "delayed_triggers_by_family": dict(delayed_triggers_by_family),
        "delayed_jobs": len(delayed_jobs),
    }
    return prompt_jobs + delayed_jobs, audit


def scan_job(job: dict[str, Any], cache_dir_text: str, threshold_keV: float,
             disk: dict[str, Any], reject_policy: str) -> dict[str, Any]:
    cache_dir = Path(cache_dir_text)
    cache_path = cache_dir / f"job_{int(job['scan_index']):03d}_{job['job_id']}.step05.npz"
    meta_path = cache_path.with_suffix(".json")
    if cache_path.is_file() and meta_path.is_file():
        prior = load_json(meta_path)
        if (prior.get("status") == "PASS__COMPACT_JOB_CATALOG"
                and prior.get("catalog_schema") == "step05_exactpos_v2"
                and int(prior.get("events", -1)) == int(job["events"])
                and int(prior.get("sim_bytes", -1)) == int(job["sim_bytes"])
                and int(prior.get("seed", -1)) == int(job["seed"])
                and prior.get("sim_path") == job["sim_path"]
                and prior.get("expected_geometry") == str(Path(job["expected_geometry"]).resolve())):
            return prior

    # Reuse the already-reviewed Step05 prompt cache from the four original
    # rounds.  Delayed caches are deliberately not reused because v1 assigned
    # lineage from IA INIT ZA rather than the exact-position authority.
    legacy_path = LEGACY_CACHE / f"job_{int(job['scan_index']):03d}_{job['job_id']}.step05.npz"
    legacy_meta_path = legacy_path.with_suffix(".json")
    if job["stream"] == "prompt" and legacy_path.is_file() and legacy_meta_path.is_file():
        prior = load_json(legacy_meta_path)
        if (
            prior.get("status") == "PASS__COMPACT_JOB_CATALOG"
            and prior.get("catalog_schema") == "step05_v1"
            and int(prior.get("events", -1)) == int(job["events"])
            and int(prior.get("sim_bytes", -1)) == int(job["sim_bytes"])
            and int(prior.get("seed", -1)) == int(job["seed"])
            and prior.get("sim_path") == job["sim_path"]
        ):
            return {
                **prior,
                "catalog_schema": "step05_exactpos_v2__reused_prompt_v1",
                "catalog_path": str(legacy_path),
                "expected_geometry": str(Path(job["expected_geometry"]).resolve()),
                "cache_provenance": "REUSED__FOUR_ROUND_PROMPT_STEP05_V1__RECEIPT_HEADER_REVALIDATED",
            }

    plastic_volumes = set(job["plastic_volumes"])
    bgo_volumes = set(job["bgo_volumes"])
    locator = m05_common().position_locator(Path(job["positions_path"])) if job["stream"] == "delayed" else None

    event_id: list[int] = []
    source_za: list[int] = []
    plastic_values: list[float] = []
    bgo_values: list[float] = []
    measured_totals: list[float] = []
    broad_flags: list[int] = []
    w2_flags: list[int] = []
    compton_keep: list[int] = []
    hit_start: list[int] = []
    hit_count: list[int] = []
    hit_code: list[int] = []
    hit_layer: list[int] = []
    hit_energy: list[float] = []
    hit_x: list[float] = []
    hit_y: list[float] = []
    hit_z: list[float] = []

    current_id: int | None = None
    current_za: int | None = None
    production_xyz: tuple[float, float, float] | None = None
    init_count = 0
    pixels: dict[str, dict[str, float | int]] = {}
    plastic_keV = 0.0
    bgo_keV = 0.0
    generated = 0
    header_geometry = ""
    header_seed: int | None = None
    max_position_distance = 0.0
    za_mismatch = 0

    def flush() -> None:
        nonlocal current_id, current_za, production_xyz, init_count, pixels, plastic_keV, bgo_keV
        nonlocal max_position_distance, za_mismatch
        if current_id is None:
            return
        resolved_za = -1
        if job["stream"] == "delayed":
            if init_count != 1 or current_za is None or production_xyz is None or locator is None:
                raise RuntimeError(f"{job['job_id']} event {current_id}: delayed INIT closure failed")
            source_meta, distance = m05_common().locate_source(locator, production_xyz)
            resolved_za = int(source_meta[1])
            max_position_distance = max(max_position_distance, float(distance))
            za_mismatch += int(resolved_za != current_za)

        detector_positive = bool(pixels) or plastic_keV > 0.0 or bgo_keV > 0.0
        if not detector_positive:
            current_id = None
            current_za = None
            production_xyz = None
            init_count = 0
            pixels = {}
            plastic_keV = 0.0
            bgo_keV = 0.0
            return

        raw_rows: list[tuple[int, int, float, float, float, float]] = []
        measured_hits: list[Any] = []
        for uid, record in sorted(pixels.items()):
            energy = float(record["e"])
            if energy <= 0.0:
                continue
            match = TP_RE.match(uid)
            if not match:
                raise RuntimeError(f"unrecognized TES pixel UID: {uid}")
            layer = int(match.group("layer"))
            pixel = int(match.group("pixel"))
            x = float(record["wx"]) / energy
            y = float(record["wy"]) / energy
            z = float(record["wz"]) / energy
            raw_rows.append((layer, layer * 100_000 + pixel, energy, x, y, z))
            measured = energy + SIGMA_KEV * keyed_standard_normal(
                "sh3_optv3", job["mode"], job["family"], job["batch_id"],
                int(job["seed"]), job["job_id"], int(current_id), uid,
            )
            if measured >= PIXEL_THRESHOLD_KEV:
                measured_hits.append(SimpleNamespace(
                    e=measured, x=x, y=y, z=z, pixel_uid=uid, layer=layer,
                ))
        measured_total = math.fsum(hit.e for hit in measured_hits)
        broad, w2 = flags_for_event(
            measured_hits, measured_total, plastic_keV, bgo_keV, threshold_keV,
            disk, reject_policy,
        )
        event_id.append(int(current_id))
        source_za.append(resolved_za)
        plastic_values.append(plastic_keV)
        bgo_values.append(bgo_keV)
        measured_totals.append(measured_total)
        broad_flags.append(broad)
        w2_flags.append(w2)
        compton_keep.append(1 if side_keep_from_hits(measured_hits, disk, reject_policy)[0] else 0)
        hit_start.append(len(hit_energy))
        hit_count.append(len(raw_rows))
        for layer, code, energy, x, y, z in raw_rows:
            hit_code.append(code)
            hit_layer.append(layer)
            hit_energy.append(energy)
            hit_x.append(x); hit_y.append(y); hit_z.append(z)

        current_id = None
        current_za = None
        production_xyz = None
        init_count = 0
        pixels = {}
        plastic_keV = 0.0
        bgo_keV = 0.0

    started = time.time()
    with gzip.open(job["sim_path"], "rt", encoding="utf-8", errors="strict") as handle:
        for raw in handle:
            line = raw.strip()
            if not header_geometry and line.startswith("Geometry"):
                header_geometry = line.split(maxsplit=1)[1]
            elif header_seed is None and line.startswith("Seed"):
                header_seed = int(line.split()[1])
            if line == "SE":
                flush()
                continue
            match = ID_RE.match(line)
            if match:
                if current_id is not None:
                    raise RuntimeError(f"{job['job_id']}: ID before event boundary")
                current_id = int(match.group(1))
                generated += 1
                continue
            if line.startswith("IA INIT") and job["stream"] == "delayed":
                fields = [value.strip() for value in line.split(";")]
                if len(fields) < 16:
                    continue
                init_count += 1
                try:
                    current_za = int(fields[15])
                except ValueError:
                    current_za = None
                production_xyz = (float(fields[4]), float(fields[5]), float(fields[6]))
                continue
            if not line.startswith("CC HIT "):
                continue
            m = CC_HIT_RE.match(line)
            if m is None:
                continue
            volume = m.group(1)
            edep = float(m.group(2))
            x = float(m.group(3)); y = float(m.group(4)); z = float(m.group(5))
            pixel_match = TP_RE.match(volume)
            if pixel_match:
                record = pixels.setdefault(
                    volume,
                    {"e": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0,
                     "layer": int(pixel_match.group("layer"))},
                )
                record["e"] = float(record["e"]) + edep
                record["wx"] = float(record["wx"]) + edep * x
                record["wy"] = float(record["wy"]) + edep * y
                record["wz"] = float(record["wz"]) + edep * z
            elif volume in plastic_volumes:
                plastic_keV += edep
            elif volume in bgo_volumes:
                bgo_keV += edep
    flush()

    if generated != int(job["events"]):
        raise RuntimeError(f"{job['job_id']}: generated {generated} != receipt {job['events']}")
    if header_seed != int(job["seed"]):
        raise RuntimeError(f"{job['job_id']}: seed mismatch")
    expected_geometry = str(Path(job["expected_geometry"]).resolve())
    if str(Path(header_geometry).resolve()) != expected_geometry:
        raise RuntimeError(
            f"{job['job_id']}: geometry mismatch {header_geometry!r} != {expected_geometry!r}"
        )

    arrays = {
        "event_id": np.asarray(event_id, dtype=np.int32),
        "source_za": np.asarray(source_za, dtype=np.int32),
        "plastic_keV": np.asarray(plastic_values, dtype=np.float32),
        "bgo_keV": np.asarray(bgo_values, dtype=np.float32),
        "measured_total_keV": np.asarray(measured_totals, dtype=np.float32),
        "broad_flags": np.asarray(broad_flags, dtype=np.uint8),
        "w2_flags": np.asarray(w2_flags, dtype=np.uint8),
        "compton_keep": np.asarray(compton_keep, dtype=np.uint8),
        "hit_start": np.asarray(hit_start, dtype=np.int32),
        "hit_count": np.asarray(hit_count, dtype=np.uint16),
        "hit_code": np.asarray(hit_code, dtype=np.int32),
        "hit_layer": np.asarray(hit_layer, dtype=np.uint8),
        "hit_energy_keV": np.asarray(hit_energy, dtype=np.float32),
        "hit_x_cm": np.asarray(hit_x, dtype=np.float32),
        "hit_y_cm": np.asarray(hit_y, dtype=np.float32),
        "hit_z_cm": np.asarray(hit_z, dtype=np.float32),
    }
    tmp = cache_path.with_suffix(".tmp")
    with tmp.open("wb") as handle:
        np.savez_compressed(handle, **arrays)
    os.replace(tmp, cache_path)
    meta = {
        "status": "PASS__COMPACT_JOB_CATALOG",
        "catalog_schema": "step05_exactpos_v2",
        "scan_index": int(job["scan_index"]),
        "stream": job["stream"],
        "family": job["family"],
        "batch_id": job["batch_id"],
        "job_id": job["job_id"],
        "seed": int(job["seed"]),
        "events": generated,
        "sim_path": job["sim_path"],
        "sim_bytes": int(job["sim_bytes"]),
        "expected_geometry": expected_geometry,
        "weight_cps": float(job["weight_cps"]),
        "detector_positive_events": len(event_id),
        "tes_positive_events": int(np.count_nonzero(arrays["hit_count"])),
        "active_only_events": int(np.count_nonzero(arrays["hit_count"] == 0)),
        "raw_pixel_hits": len(hit_energy),
        "max_position_match_distance_cm": max_position_distance,
        "init_source_za_mismatch_events": za_mismatch,
        "elapsed_s": time.time() - started,
        "catalog_path": str(cache_path),
    }
    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return meta


def merge_catalogs(jobs: list[dict[str, Any]], metas: list[dict[str, Any]]) -> dict[str, Any]:
    def identity(row): return (str(row["stream"]), str(row["family"]), str(row["batch_id"]), str(row["job_id"]))
    meta_by = {identity(m): m for m in metas}
    event_fields = ("plastic_keV", "bgo_keV", "measured_total_keV",
                    "broad_flags", "w2_flags", "compton_keep", "hit_start", "hit_count")
    hit_fields = ("hit_code", "hit_layer", "hit_energy_keV", "hit_x_cm", "hit_y_cm", "hit_z_cm")
    category_chunks: dict[tuple[str, str, int], dict[str, list[np.ndarray]]] = defaultdict(
        lambda: {f: [] for f in event_fields}
    )
    category_weights: dict[tuple[str, str, int], float] = {}
    global_hits: dict[str, list[np.ndarray]] = {f: [] for f in hit_fields}
    hit_offset = 0
    for job in sorted(jobs, key=lambda r: int(r["scan_index"])):
        meta = meta_by[identity(job)]
        with np.load(meta["catalog_path"], allow_pickle=False) as data:
            arrays = {k: data[k] for k in data.files}
        for f in hit_fields:
            global_hits[f].append(arrays[f])
        starts = arrays["hit_start"].astype(np.int64) + hit_offset
        hit_offset += len(arrays["hit_code"])
        zas = arrays["source_za"]
        keys = [(-1, np.arange(len(zas), dtype=np.int64))] if job["stream"] == "prompt" else [
            (int(za), np.flatnonzero(zas == za)) for za in np.unique(zas)
        ]
        for za, indices in keys:
            key = (job["stream"], job["family"], za)
            category_weights.setdefault(key, float(job["weight_cps"]))
            tgt = category_chunks[key]
            for f in event_fields:
                src = starts if f == "hit_start" else arrays[f]
                tgt[f].append(src[indices])

    combined = {f: [] for f in event_fields}
    event_category: list[np.ndarray] = []
    category_rows: list[dict[str, Any]] = []
    event_offset = 0
    for category_id, key in enumerate(sorted(category_chunks)):
        stream, family, za = key
        chunks = category_chunks[key]
        count = sum(len(c) for c in chunks["plastic_keV"])
        category_rows.append({
            "category_id": category_id,
            "stream": stream, "family": family,
            "source_parent_ZA": int(za),
            "event_start": event_offset,
            "event_count": count,
            "base_event_weight_cps": float(category_weights[key]),
            "base_detector_positive_rate_cps": float(count * category_weights[key]),
        })
        for f in event_fields:
            combined[f].append(np.concatenate(chunks[f]) if chunks[f] else np.empty(0))
        event_category.append(np.full(count, category_id, dtype=np.uint16))
        event_offset += count

    output_arrays = {f: (np.concatenate(chunks) if chunks else np.empty(0))
                     for f, chunks in combined.items()}
    output_arrays["event_category"] = np.concatenate(event_category)
    for f, chunks in global_hits.items():
        output_arrays[f] = np.concatenate(chunks) if chunks else np.empty(0)
    OUT.mkdir(parents=True, exist_ok=True)
    catalog_path = OUT / "combined_event_catalog.npz"
    tmp = catalog_path.with_suffix(".tmp")
    with tmp.open("wb") as handle:
        np.savez_compressed(handle, **output_arrays)
    os.replace(tmp, catalog_path)
    (OUT / "category_registry.json").write_text(
        json.dumps({"schema_version": 1, "categories": category_rows}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # Direct rate cutflow — no closure target here; SH3 has no package-58 rate reference.
    cutflow_rows: list[dict[str, Any]] = []
    for row in category_rows:
        start = int(row["event_start"])
        stop = start + int(row["event_count"])
        weight = float(row["base_event_weight_cps"])
        for window_id, flag_field in (("broad_480_550", "broad_flags"), ("w2_510p58_511p42", "w2_flags")):
            flags = output_arrays[flag_field][start:stop]
            for stage, bit in STAGE_BITS.items():
                cutflow_rows.append({
                    "category_id": row["category_id"],
                    "stream": row["stream"], "family": row["family"],
                    "source_parent_ZA": row["source_parent_ZA"],
                    "window_id": window_id, "stage": stage,
                    "count": int(np.count_nonzero(flags & bit)),
                    "weighted_rate_cps": float(np.count_nonzero(flags & bit)) * weight,
                })
    with (OUT / "direct_cutflow.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(cutflow_rows[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(cutflow_rows)

    # Aggregate cutflow across categories for a compact rate table
    agg: dict[tuple[str, str], float] = defaultdict(float)
    for row in cutflow_rows:
        agg[(row["window_id"], row["stage"])] += row["weighted_rate_cps"]
    agg_rows = [{"window_id": w, "stage": s, "total_rate_cps": r} for (w, s), r in sorted(agg.items())]
    with (OUT / "direct_cutflow_totals.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(agg_rows[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(agg_rows)

    return {
        "combined_catalog_path": str(catalog_path),
        "category_registry": str(OUT / "category_registry.json"),
        "event_templates": int(len(output_arrays["event_category"])),
        "raw_pixel_hits": int(len(output_arrays["hit_code"])),
        "categories": len(category_rows),
        "cutflow_csv": str(OUT / "direct_cutflow.csv"),
        "cutflow_totals_csv": str(OUT / "direct_cutflow_totals.csv"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    cfg = load_json(CONFIG)
    jobs, audit = prepare_jobs(cfg)
    threshold = float(cfg["active_veto"]["offline_threshold_keV"])
    sde = cfg["side_entry_disk"]
    disk = side_entry_disk(
        tuple(float(x) for x in sde["local_center_cm"]),
        float(sde["radius_cm"]),
        float(sde["rotation_y_deg"]),
    )
    reject_policy = str(sde.get("reject_policy", "keep"))
    metas: list[dict[str, Any]] = []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {executor.submit(scan_job, job, str(CACHE), threshold, disk, reject_policy): job for job in jobs}
        for future in as_completed(futures):
            job = futures[future]
            meta = future.result()
            metas.append(meta)
            print(json.dumps({
                "job_id": job["job_id"], "stream": job["stream"], "family": job["family"],
                "batch_id": job["batch_id"],
                "detector_positive": meta["detector_positive_events"],
                "elapsed_s": round(meta["elapsed_s"], 2),
                "complete": len(metas), "total": len(jobs),
            }), flush=True)
    merged = merge_catalogs(jobs, metas)
    summary = {
        "status": "PASS__SH3_OPTV3_COMPACT_EVENT_CATALOG__STEP05_EXACT_POSITION_V2",
        "catalog_schema": "step05_exactpos_v2",
        "side_entry_disk": {
            "local_center_cm": [float(x) for x in sde["local_center_cm"]],
            "radius_cm": float(sde["radius_cm"]),
            "rotation_y_deg": float(sde["rotation_y_deg"]),
            "reject_policy": reject_policy,
        },
        "wall_s_total": time.time() - t0,
        "authority_boundary": {
            "accepted_jobs": len(jobs),
            "prompt_jobs": audit["prompt_jobs"],
            "delayed_jobs": audit["delayed_jobs"],
            "SIM_payload_bytes_streamed": sum(int(j["sim_bytes"]) for j in jobs),
            "SIM_hashes_computed": 0,
            "Cosima_transport_started": False,
            "parma_mono511_included": False,
        },
        "normalization": {
            "prompt_rule": "instant weight = 1/sum(TT_family) over original rounds001-004 plus expansion rounds006-036; round005 excluded for canary seed reuse",
            "prompt_sum_TT_s_by_family": audit["prompt_sum_TT_s_by_family"],
            "prompt_instant_events_by_family": audit["prompt_instant_events_by_family"],
            "delayed_rule": "delayed weight = A_family(day15_Bq) / total_triggers_family",
            "delayed_day15_activity_Bq_by_family": audit["delayed_day15_activity_Bq_by_family"],
            "delayed_triggers_by_family": audit["delayed_triggers_by_family"],
            "delayed_lineage": "source_parent_ZA recovered from exact production position; IA INIT ZA retained as mismatch diagnostic",
        },
        "merged": merged,
        "jobs": sorted(metas, key=lambda r: int(r["scan_index"])),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "merged": merged,
                      "wall_s_total": round(summary["wall_s_total"], 1)}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
