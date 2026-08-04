#!/usr/bin/env python3
"""Close the O8 TES energy response stated in the EA manuscript.

The retained O8 event catalogue contains unnoised Cosima energy deposits.  This
postprocessor leaves those retained products untouched and applies the paper's
420 eV FWHM Gaussian response independently to each pixel-level TES readout.
It then applies the detector-map 0.3 keV TES hit threshold before rebuilding
event sums and rerunning the frozen W2, active-veto, and side-entry topology/FoV
selection.  Prompt, neutron-delayed, focused-signal, and atmospheric-511
streams are treated with the same response contract.

One preregistered response seed supplies the integer cut flow used for the
paper authority.  A deterministic seed ensemble checks that this realization
is representative; the ensemble is a numerical-response convergence audit and
is not added as a physical systematic uncertainty.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import math
import multiprocessing as mp
import pickle
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable

import numpy as np
from scipy.stats import beta, chi2


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parents[1]
DATA = PACKAGE / "data"
OUTPUTS = PACKAGE / "outputs"

O8 = (
    ROOT
    / "engineering/geometry_optimization_20260704"
    / "43_geoopt_s3d_o8_fallback_20260712"
)
BASE_CATALOG = O8 / "fullchain/step05/work/event_catalog.pkl"
BASE_STEP05 = O8 / "fullchain/step05/step05_s3d_o8_fullchain_l1_response_summary.json"
BASE_STEP06_CSV = O8 / "fullchain/step06/background_time_variation.csv"
BASE_STEP08 = O8 / "fullchain/step08/step08_s3d_o8_fullchain_time_dependent_summary.json"
BASE_ATM_SUMMARY = O8 / "data/s3d_o8_atm511_replay_summary.json"
BASE_ATM_SIM = (
    ROOT
    / "runs/geometry_optimization_20260704/s3d_o8_atm511_sidecar_3m_20260712"
    / "Atm511SidecarS3dO8_3M.inc1.id1.sim.gz"
)
BASE_ATM_PARSER = (
    ROOT
    / "engineering/geometry_optimization_20260704/12_atm511_sidecar_replay_20260708"
    / "build_geo_opt_atm511_sidecar_replay.py"
)
STEP05_IMPLEMENTATION = ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"
STEP09_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5"
    / "step09_optics_bridge_summary.json"
)
O8_GEOMETRY_SETUP = O8 / "geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
O8_DETECTOR_MAP = O8_GEOMETRY_SETUP.parent / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det"

REFERENCE_STEP05_ROOT = (
    ROOT
    / "stepwise_maintenance/step05_veto_time_axis"
    / "outputs_Mass_model_511_fullstat_v1_l1"
)
REFERENCE_CATALOG = REFERENCE_STEP05_ROOT / "work/event_catalog.pkl"
REFERENCE_STEP05 = REFERENCE_STEP05_ROOT / "step05_Mass_model_511_fullstat_v1_l1_response_summary.json"
REFERENCE_STEP06_CSV = (
    ROOT
    / "stepwise_maintenance/step06_mission_time_variation"
    / "outputs_Mass_model_511_fullstat_v1/background_time_variation.csv"
)
REFERENCE_STEP08 = (
    ROOT
    / "stepwise_maintenance/step08_significance"
    / "outputs_Mass_model_511_fullstat_v1"
    / "step08_Mass_model_511_fullstat_v1_time_dependent_summary.json"
)

ATM_CACHE = DATA / "o8_atm511_compact_catalog.pkl"
SUMMARY_JSON = DATA / "o8_energy_response_closure_summary.json"
REPLICAS_CSV = DATA / "o8_energy_response_replicas.csv"
TIMELINE_CSV = OUTPUTS / "w2_energy_response_timeline.csv"
REFERENCE_TIMELINE_CSV = OUTPUTS / "reference_w2_energy_response_timeline.csv"
README = PACKAGE / "README.md"

FWHM_KEV = 0.420
GAUSSIAN_SIGMA_KEV = FWHM_KEV / (2.0 * math.sqrt(2.0 * math.log(2.0)))
TES_HIT_THRESHOLD_KEV = 0.3
ACTIVE_VETO_THRESHOLD_KEV = 50.0
WINDOWS = {
    "broad_480_550": (480.0, 550.0),
    "w2_510p58_511p42": (510.58, 511.42),
}
PRIMARY_RESPONSE_SEED = 26_071_301
RESPONSE_SEED_STRIDE = 7_919
SIGNAL_TRIALS = 37_194
REFERENCE_FLUX = 1.0e-4
COINCIDENCE_WINDOW_S = 1.0e-6
SECONDS_PER_DAY = 86_400.0
CONFIDENCE = 0.95
ALPHA_TWO_SIDED = 1.0 - CONFIDENCE


class ClosureError(RuntimeError):
    """An input or numerical closure check failed."""


@dataclass(frozen=True)
class CompactCatalog:
    """TES-hit events plus the information needed by the frozen selection."""

    label: str
    event_id: np.ndarray
    stream: np.ndarray
    tag: np.ndarray
    rate_hz: np.ndarray
    active_keV: np.ndarray
    raw_total_keV: np.ndarray
    hit_start: np.ndarray
    hit_count: np.ndarray
    hit_uid: np.ndarray
    hit_layer: np.ndarray
    hit_e_keV: np.ndarray
    hit_x_cm: np.ndarray
    hit_y_cm: np.ndarray
    hit_z_cm: np.ndarray
    active_only_rate_by_stream: dict[str, float]
    active_only_events_by_stream: dict[str, int]
    generated_events: int | None = None


_WORKER_MAIN: CompactCatalog | None = None
_WORKER_ATM: CompactCatalog | None = None
_WORKER_STEP05: Any | None = None
_WORKER_DISK: dict[str, Any] | None = None
_WORKER_REFERENCE: CompactCatalog | None = None


def now_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    rows = list(rows)
    if not rows:
        raise ClosureError(f"refusing to write empty CSV: {path}")
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ClosureError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def is_active_veto_volume(volume: str) -> bool:
    upper = str(volume).upper()
    return (
        upper.startswith("CSI_")
        or "ACTIVE_SHIELD" in upper
        or "ACTIVESHIELD" in upper
        or "CEBR3" in upper
        or "BGO" in upper
        or upper.startswith("GEOOPT_S1_PLASTICFULLWRAP")
        or upper.startswith("GEOOPT_S2B_CRYOSHELL_PLASTIC")
    )


def load_step05_selection() -> tuple[Any, dict[str, Any]]:
    step05 = load_module("ea_response_step05", STEP05_IMPLEMENTATION)
    step05.ROOT = ROOT
    step05.STEP09_SUMMARY = STEP09_SUMMARY
    step05.is_v3p5_active_veto_volume = is_active_veto_volume
    return step05, step05.side_entry_disk()


def audit_detector_contract() -> dict[str, Any]:
    text = O8_DETECTOR_MAP.read_text(encoding="utf-8", errors="replace")
    resolution_rows: list[tuple[float, float, float]] = []
    thresholds: list[float] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(tuple(f"D{i}.EnergyResolution Gauss" for i in range(1, 7))):
            fields = stripped.split()
            resolution_rows.append(tuple(float(value) for value in fields[-3:]))
        if stripped.startswith(tuple(f"D{i}.TriggerThreshold" for i in range(1, 7))):
            thresholds.append(float(stripped.split()[-2]))
    if len(resolution_rows) != 12:
        raise ClosureError(f"expected 12 TES resolution rows, found {len(resolution_rows)}")
    if thresholds != [TES_HIT_THRESHOLD_KEV] * 6:
        raise ClosureError(f"TES thresholds={thresholds}, expected six 0.3-keV values")
    configured_sigmas = sorted(set(row[2] for row in resolution_rows))
    return {
        "geometry_setup": rel(O8_GEOMETRY_SETUP),
        "detector_map": rel(O8_DETECTOR_MAP),
        "detector_map_sha256": sha256(O8_DETECTOR_MAP),
        "paper_fwhm_keV": FWHM_KEV,
        "paper_sigma_keV": GAUSSIAN_SIGMA_KEV,
        "detector_map_sigma_keV_before_closure": configured_sigmas,
        "tes_hit_threshold_keV": TES_HIT_THRESHOLD_KEV,
        "interpretation": (
            "MEGAlib MDDetector::ApplyEnergyResolution uses the third Gauss "
            "parameter as one standard deviation; the paper's 0.420-keV FWHM "
            "therefore corresponds to sigma=FWHM/2.354820045."
        ),
    }


def _group_sum(values: np.ndarray, groups: np.ndarray) -> dict[str, float]:
    return {
        str(group): float(np.sum(values[groups == group]))
        for group in sorted(set(str(value) for value in groups))
    }


def _group_count(mask: np.ndarray, groups: np.ndarray) -> dict[str, int]:
    return {
        str(group): int(np.count_nonzero(mask & (groups == group)))
        for group in sorted(set(str(value) for value in groups))
    }


def compact_event_catalog(path: Path, label: str) -> CompactCatalog:
    with path.open("rb") as handle:
        raw = pickle.load(handle)
    counts_all = np.asarray(raw["pix_count"], dtype=np.int64)
    tes_mask = counts_all > 0
    event_indices = np.flatnonzero(tes_mask)
    counts = counts_all[tes_mask]
    starts = np.asarray(raw["pix_start"], dtype=np.int64)[tes_mask]
    expected_starts = np.concatenate(
        [np.asarray([0], dtype=np.int64), np.cumsum(counts[:-1], dtype=np.int64)]
    )
    if not np.array_equal(starts, expected_starts):
        raise ClosureError(f"{label} TES hit slices are not contiguous")
    if int(np.sum(counts)) != len(raw["pix_e"]):
        raise ClosureError(f"{label} hit-count closure failed")

    stream_all = np.asarray(raw["stream"], dtype=object)
    rate_all = np.asarray(raw["rate_hz"], dtype=np.float64)
    active_all = np.asarray(raw["bgo_total_keV"], dtype=np.float64)
    active_only = (~tes_mask) & (active_all > 0.0)
    active_only_rates = _group_sum(rate_all[active_only], stream_all[active_only])
    active_only_counts = _group_count(active_only, stream_all)

    return CompactCatalog(
        label=label,
        event_id=event_indices.astype(np.int64),
        stream=stream_all[tes_mask].copy(),
        tag=np.asarray(raw["tag"], dtype=object)[tes_mask].copy(),
        rate_hz=rate_all[tes_mask].copy(),
        active_keV=active_all[tes_mask].copy(),
        raw_total_keV=np.asarray(raw["tes_total_keV"], dtype=np.float64)[tes_mask].copy(),
        hit_start=expected_starts,
        hit_count=counts.copy(),
        hit_uid=np.asarray(raw["pix_uid"], dtype=object).copy(),
        hit_layer=np.asarray(raw["pix_layer"], dtype=np.int16).copy(),
        hit_e_keV=np.asarray(raw["pix_e"], dtype=np.float64).copy(),
        hit_x_cm=np.asarray(raw["pix_x"], dtype=np.float64).copy(),
        hit_y_cm=np.asarray(raw["pix_y"], dtype=np.float64).copy(),
        hit_z_cm=np.asarray(raw["pix_z"], dtype=np.float64).copy(),
        active_only_rate_by_stream=active_only_rates,
        active_only_events_by_stream=active_only_counts,
        generated_events=int(raw.get("n_generated_events_seen", 0)),
    )


def compact_main_catalog() -> CompactCatalog:
    return compact_event_catalog(BASE_CATALOG, "o8_fullchain_prompt_delayed_signal")


def build_or_load_atm_catalog(rebuild: bool) -> CompactCatalog:
    if ATM_CACHE.is_file() and not rebuild:
        with ATM_CACHE.open("rb") as handle:
            cached = pickle.load(handle)
        if isinstance(cached, CompactCatalog):
            compact = cached
        elif isinstance(cached, dict):
            compact = CompactCatalog(**cached)
        else:
            raise ClosureError(f"unexpected atmospheric cache type: {type(cached)}")
        # Keep the on-disk cache independent of the script's import name.
        with ATM_CACHE.open("wb") as handle:
            pickle.dump(compact.__dict__, handle, protocol=pickle.HIGHEST_PROTOCOL)
        return compact

    parser = load_module("ea_response_atm_parser", BASE_ATM_PARSER)
    parser.SIM = BASE_ATM_SIM
    parser.is_active_veto_volume = is_active_veto_volume
    cat = parser.parse_catalog()
    counts_all = np.asarray(cat["pix_count"], dtype=np.int64)
    tes_mask = counts_all > 0
    counts = counts_all[tes_mask]
    starts = np.asarray(cat["pix_start"], dtype=np.int64)[tes_mask]
    expected_starts = np.concatenate(
        [np.asarray([0], dtype=np.int64), np.cumsum(counts[:-1], dtype=np.int64)]
    )
    if not np.array_equal(starts, expected_starts):
        raise ClosureError("atmospheric TES hit slices are not contiguous")
    if int(np.sum(counts)) != len(cat["pix_e"]):
        raise ClosureError("atmospheric hit-count closure failed")

    base_atm = load_json(BASE_ATM_SUMMARY)
    event_weight = float(base_atm["normalization"]["event_rate_weight_cps"])
    active_all = np.asarray(cat["active_total_keV"], dtype=np.float64)
    active_only = (~tes_mask) & (active_all > 0.0)
    compact = CompactCatalog(
        label="o8_atm511_sidecar",
        event_id=np.asarray(cat["local_id"], dtype=np.int64)[tes_mask].copy(),
        stream=np.full(int(np.count_nonzero(tes_mask)), "atm511_sidecar", dtype=object),
        tag=np.full(int(np.count_nonzero(tes_mask)), "atm511", dtype=object),
        rate_hz=np.full(int(np.count_nonzero(tes_mask)), event_weight, dtype=np.float64),
        active_keV=active_all[tes_mask].copy(),
        raw_total_keV=np.asarray(cat["tes_total_keV"], dtype=np.float64)[tes_mask].copy(),
        hit_start=expected_starts,
        hit_count=counts.copy(),
        hit_uid=np.asarray(cat["pix_uid"], dtype=object).copy(),
        hit_layer=np.asarray(cat["pix_layer"], dtype=np.int16).copy(),
        hit_e_keV=np.asarray(cat["pix_e"], dtype=np.float64).copy(),
        hit_x_cm=np.asarray(cat["pix_x"], dtype=np.float64).copy(),
        hit_y_cm=np.asarray(cat["pix_y"], dtype=np.float64).copy(),
        hit_z_cm=np.asarray(cat["pix_z"], dtype=np.float64).copy(),
        active_only_rate_by_stream={"atm511_sidecar": float(np.count_nonzero(active_only)) * event_weight},
        active_only_events_by_stream={"atm511_sidecar": int(np.count_nonzero(active_only))},
        generated_events=int(cat["generated_events"]),
    )
    ATM_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with ATM_CACHE.open("wb") as handle:
        pickle.dump(compact.__dict__, handle, protocol=pickle.HIGHEST_PROTOCOL)
    return compact


def measured_hits(
    cat: CompactCatalog,
    seed: int | None,
    *,
    apply_response: bool,
    apply_threshold: bool,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if apply_response:
        if seed is None:
            raise ClosureError("response seed is required when response is active")
        rng = np.random.default_rng(seed)
        hits = cat.hit_e_keV + rng.normal(0.0, GAUSSIAN_SIGMA_KEV, len(cat.hit_e_keV))
    else:
        hits = cat.hit_e_keV.copy()
    if apply_threshold:
        hits[hits < TES_HIT_THRESHOLD_KEV] = 0.0
    totals = np.add.reduceat(hits, cat.hit_start)
    multiplicity = np.add.reduceat((hits > 0.0).astype(np.int32), cat.hit_start)
    return hits, totals, multiplicity


def _event_hits(cat: CompactCatalog, event_index: int, hits: np.ndarray) -> list[Any]:
    start = int(cat.hit_start[event_index])
    stop = start + int(cat.hit_count[event_index])
    out: list[Any] = []
    for hit_index in range(start, stop):
        energy = float(hits[hit_index])
        if energy <= 0.0:
            continue
        out.append(
            SimpleNamespace(
                x=float(cat.hit_x_cm[hit_index]),
                y=float(cat.hit_y_cm[hit_index]),
                z=float(cat.hit_z_cm[hit_index]),
                e=energy,
                pixel_uid=str(cat.hit_uid[hit_index]),
                layer=int(cat.hit_layer[hit_index]),
            )
        )
    return out


def evaluate_catalog(
    cat: CompactCatalog,
    step05: Any,
    disk: dict[str, Any],
    seed: int | None,
    *,
    apply_response: bool,
    apply_threshold: bool,
    include_details: bool,
) -> dict[str, Any]:
    hits, totals, multiplicity = measured_hits(
        cat,
        seed,
        apply_response=apply_response,
        apply_threshold=apply_threshold,
    )
    broad_lo, broad_hi = WINDOWS["broad_480_550"]
    broad_active = (
        (totals >= broad_lo)
        & (totals < broad_hi)
        & (cat.active_keV < ACTIVE_VETO_THRESHOLD_KEV)
    )
    keep = np.zeros(len(totals), dtype=bool)
    classes = np.full(len(totals), "not_evaluated", dtype=object)
    one = broad_active & (multiplicity == 1)
    keep[one] = True
    classes[one] = "single"
    # The retained policy keeps sequence-reconstruction failures.  Multiplicity
    # > MAX_ENUM_HITS is therefore a direct reject_kept result.
    many = broad_active & (multiplicity > int(step05.MAX_ENUM_HITS))
    keep[many] = True
    classes[many] = "reject_kept"
    complex_indices = np.flatnonzero(
        broad_active & (multiplicity >= 2) & (multiplicity <= int(step05.MAX_ENUM_HITS))
    )
    for index in complex_indices:
        accepted, classification = step05.side_keep_from_hits(
            _event_hits(cat, int(index), hits), disk, "keep"
        )
        keep[index] = bool(accepted)
        classes[index] = str(classification)

    windows: dict[str, Any] = {}
    streams = sorted(set(str(value) for value in cat.stream))
    for name, (lo, hi) in WINDOWS.items():
        raw_mask = (totals >= lo) & (totals < hi)
        active_mask = raw_mask & (cat.active_keV < ACTIVE_VETO_THRESHOLD_KEV)
        final_mask = active_mask & keep
        by_stream: dict[str, Any] = {}
        for stream in streams:
            stream_mask = cat.stream == stream
            record: dict[str, Any] = {}
            for stage, mask in (
                ("raw", raw_mask),
                ("active_veto_pass", active_mask),
                ("side_compton_fov_pass", final_mask),
            ):
                selected = stream_mask & mask
                record[f"{stage}_events"] = int(np.count_nonzero(selected))
                record[f"{stage}_rate_cps"] = float(np.sum(cat.rate_hz[selected]))
                record[f"{stage}_rate_stat_sigma_cps"] = float(
                    math.sqrt(float(np.sum(np.square(cat.rate_hz[selected]))))
                )
            if include_details:
                class_mask = stream_mask & active_mask
                class_names = sorted(set(str(value) for value in classes[class_mask]))
                record["side_compton_class_counts"] = dict(
                    sorted(Counter(str(value) for value in classes[class_mask]).items())
                )
                record["side_compton_class_rate_cps"] = {
                    name: float(np.sum(cat.rate_hz[class_mask & (classes == name)]))
                    for name in class_names
                }
                record["side_compton_class_rate_stat_sigma_cps"] = {
                    name: float(
                        math.sqrt(
                            float(
                                np.sum(
                                    np.square(
                                        cat.rate_hz[class_mask & (classes == name)]
                                    )
                                )
                            )
                        )
                    )
                    for name in class_names
                }
            by_stream[stream] = record

        prompt_tags: dict[str, Any] = {}
        if "prompt" in streams:
            for tag in sorted(set(str(value) for value in cat.tag[cat.stream == "prompt"])):
                mask = final_mask & (cat.stream == "prompt") & (cat.tag == tag)
                rates = cat.rate_hz[mask]
                all_rates = cat.rate_hz[(cat.stream == "prompt") & (cat.tag == tag)]
                unique_weights = np.unique(all_rates)
                if len(unique_weights) != 1:
                    raise ClosureError(f"prompt tag {tag} has non-unique event weights")
                prompt_tags[tag] = {
                    "events": int(np.count_nonzero(mask)),
                    "rate_cps": float(np.sum(rates)),
                    "event_weight_cps": float(unique_weights[0]),
                }
        windows[name] = {
            "window_keV": [lo, hi],
            "by_stream": by_stream,
            "prompt_final_by_tag": prompt_tags,
        }

    occupancy: dict[str, Any] = {}
    has_tes = multiplicity > 0
    for stream in streams:
        event_mask = cat.stream == stream
        tes_only = event_mask & has_tes & (cat.active_keV <= 0.0)
        both_or_active = event_mask & (cat.active_keV > 0.0)
        active_only_rate = float(cat.active_only_rate_by_stream.get(stream, 0.0))
        active_only_events = int(cat.active_only_events_by_stream.get(stream, 0))
        occupancy[stream] = {
            "events": int(np.count_nonzero(tes_only | both_or_active)) + active_only_events,
            "rate_hz": float(np.sum(cat.rate_hz[tes_only | both_or_active])) + active_only_rate,
        }
    return {
        "catalog": cat.label,
        "response_seed": seed,
        "apply_response": apply_response,
        "apply_threshold": apply_threshold,
        "tes_events_before_response": len(cat.event_id),
        "pixel_hits_before_response": len(cat.hit_e_keV),
        "tes_events_after_threshold": int(np.count_nonzero(has_tes)),
        "pixel_hits_after_threshold": int(np.count_nonzero(hits > 0.0)),
        "windows": windows,
        "occupancy": occupancy,
    }


def _assert_close(actual: float, expected: float, label: str, atol: float = 1.0e-12) -> None:
    if not math.isclose(actual, expected, rel_tol=1.0e-10, abs_tol=atol):
        raise ClosureError(f"{label}: actual={actual:.17g}, expected={expected:.17g}")


def validate_unsmeared_reproduction(
    main: dict[str, Any], atm: dict[str, Any]
) -> dict[str, Any]:
    base = load_json(BASE_STEP05)
    base_atm = load_json(BASE_ATM_SUMMARY)
    checks: list[dict[str, Any]] = []
    for window_name in WINDOWS:
        for stream in ("prompt", "delayed", "science"):
            expected = base["windows"][window_name]["by_stream"][stream]
            actual = main["windows"][window_name]["by_stream"][stream]
            for stage in ("raw", "active_veto_pass", "side_compton_fov_pass"):
                event_key = f"{stage}_events"
                base_rate_key = f"{stage}_rate_s-1"
                actual_rate_key = f"{stage}_rate_cps"
                if int(actual[event_key]) != int(expected[event_key]):
                    raise ClosureError(
                        f"unsmeared {window_name}/{stream}/{event_key}: "
                        f"{actual[event_key]} != {expected[event_key]}"
                    )
                _assert_close(
                    float(actual[actual_rate_key]),
                    float(expected[base_rate_key]),
                    f"unsmeared {window_name}/{stream}/{actual_rate_key}",
                )
                checks.append(
                    {
                        "window": window_name,
                        "stream": stream,
                        "stage": stage,
                        "events": int(actual[event_key]),
                        "rate_cps": float(actual[actual_rate_key]),
                    }
                )

        expected_atm = base_atm["windows"][window_name]
        actual_atm = atm["windows"][window_name]["by_stream"]["atm511_sidecar"]
        for stage, base_event_key, base_rate_key in (
            ("raw", "raw_events", "raw_rate_cps"),
            ("active_veto_pass", "active_veto_pass_events", "active_rate_cps"),
            ("side_compton_fov_pass", "side_compton_fov_pass_events", "final_rate_cps"),
        ):
            event_key = f"{stage}_events"
            rate_key = f"{stage}_rate_cps"
            if int(actual_atm[event_key]) != int(expected_atm[base_event_key]):
                raise ClosureError(
                    f"unsmeared {window_name}/atm/{event_key}: "
                    f"{actual_atm[event_key]} != {expected_atm[base_event_key]}"
                )
            _assert_close(
                float(actual_atm[rate_key]),
                float(expected_atm[base_rate_key]),
                f"unsmeared {window_name}/atm/{rate_key}",
            )
            checks.append(
                {
                    "window": window_name,
                    "stream": "atm511_sidecar",
                    "stage": stage,
                    "events": int(actual_atm[event_key]),
                    "rate_cps": float(actual_atm[rate_key]),
                }
            )
    return {
        "status": "PASS_EXACT_UNSMEARED_REPRODUCTION",
        "checks": checks,
        "base_step05": rel(BASE_STEP05),
        "base_atm_summary": rel(BASE_ATM_SUMMARY),
    }


def validate_unsmeared_reference_reproduction(reference: dict[str, Any]) -> dict[str, Any]:
    base = load_json(REFERENCE_STEP05)
    checks: list[dict[str, Any]] = []
    for window_name in WINDOWS:
        for stream in ("prompt", "delayed", "science"):
            expected = base["windows"][window_name]["by_stream"][stream]
            actual = reference["windows"][window_name]["by_stream"][stream]
            for stage in ("raw", "active_veto_pass", "side_compton_fov_pass"):
                event_key = f"{stage}_events"
                actual_rate_key = f"{stage}_rate_cps"
                expected_rate_key = f"{stage}_rate_s-1"
                if int(actual[event_key]) != int(expected[event_key]):
                    raise ClosureError(
                        f"reference unsmeared {window_name}/{stream}/{event_key}: "
                        f"{actual[event_key]} != {expected[event_key]}"
                    )
                _assert_close(
                    float(actual[actual_rate_key]),
                    float(expected[expected_rate_key]),
                    f"reference unsmeared {window_name}/{stream}/{actual_rate_key}",
                )
                checks.append(
                    {
                        "window": window_name,
                        "stream": stream,
                        "stage": stage,
                        "events": int(actual[event_key]),
                        "rate_cps": float(actual[actual_rate_key]),
                    }
                )
    return {
        "status": "PASS_EXACT_REFERENCE_UNSMEARED_REPRODUCTION",
        "checks": checks,
        "base_step05": rel(REFERENCE_STEP05),
    }


def poisson_upper_95(count: int) -> float:
    return float(0.5 * chi2.ppf(1.0 - ALPHA_TWO_SIDED / 2.0, 2.0 * (count + 1)))


def poisson_interval_95(count: int, weight: float) -> list[float]:
    low_count = (
        0.0
        if count == 0
        else 0.5 * float(chi2.ppf(ALPHA_TWO_SIDED / 2.0, 2.0 * count))
    )
    high_count = poisson_upper_95(count)
    return [low_count * weight, high_count * weight]


def binomial_lower_95(successes: int, trials: int) -> float:
    if successes <= 0 or trials <= 0:
        return 0.0
    if successes >= trials:
        return float(beta.ppf(ALPHA_TWO_SIDED / 2.0, successes, 1))
    return float(beta.ppf(ALPHA_TWO_SIDED / 2.0, successes, trials - successes + 1))


def primary_step05(main: dict[str, Any], atm: dict[str, Any]) -> dict[str, Any]:
    base = load_json(BASE_STEP05)
    injection_rate = float(
        base["science_physical_normalization"]["rate_to_v3p5_injection_plane_s-1"]
    )
    windows: dict[str, Any] = {}
    for name, bounds in WINDOWS.items():
        by = dict(main["windows"][name]["by_stream"])
        by["atm511_sidecar"] = atm["windows"][name]["by_stream"]["atm511_sidecar"]
        prompt = float(by["prompt"]["side_compton_fov_pass_rate_cps"])
        delayed = float(by["delayed"]["side_compton_fov_pass_rate_cps"])
        atmosphere = float(by["atm511_sidecar"]["side_compton_fov_pass_rate_cps"])
        science_unit = float(by["science"]["side_compton_fov_pass_rate_cps"])
        signal = science_unit * injection_rate
        background = prompt + delayed + atmosphere

        prompt_upper = 0.0
        prompt_components: list[dict[str, Any]] = []
        selected_prompt = main["windows"][name]["prompt_final_by_tag"]
        prompt_norm_rows = base["normalization"]["prompt_normalization_audit"]["rows"]
        for norm_row in prompt_norm_rows:
            tag = str(norm_row["tag"])
            weight = float(norm_row["rate_hz_per_event"])
            record = selected_prompt.get(
                tag,
                {"events": 0, "rate_cps": 0.0, "event_weight_cps": weight},
            )
            if not math.isclose(
                float(record["event_weight_cps"]), weight, rel_tol=0.0, abs_tol=1.0e-18
            ):
                raise ClosureError(f"prompt response weight mismatch for tag={tag}")
            upper = poisson_upper_95(int(record["events"])) * weight
            prompt_upper += upper
            prompt_components.append(
                {
                    **record,
                    "tag": tag,
                    "rate_interval95_cps": poisson_interval_95(int(record["events"]), weight),
                    "rate_upper95_cps": upper,
                }
            )
        delayed_events = int(by["delayed"]["side_compton_fov_pass_events"])
        delayed_weight = 1.0 / float(base["normalization"]["delayed_time_s"])
        if delayed_events > 0:
            _assert_close(
                float(by["delayed"]["side_compton_fov_pass_rate_cps"]) / delayed_events,
                delayed_weight,
                f"{name} delayed event weight",
                atol=1.0e-18,
            )
        delayed_upper = poisson_upper_95(delayed_events) * delayed_weight
        atm_events = int(by["atm511_sidecar"]["side_compton_fov_pass_events"])
        atm_weight = float(load_json(BASE_ATM_SUMMARY)["normalization"]["event_rate_weight_cps"])
        atm_upper = poisson_upper_95(atm_events) * atm_weight
        signal_successes = int(by["science"]["side_compton_fov_pass_events"])
        signal_acceptance_lower = binomial_lower_95(signal_successes, SIGNAL_TRIALS)
        signal_lower = signal_acceptance_lower * injection_rate
        background_upper = prompt_upper + delayed_upper + atm_upper

        windows[name] = {
            "window_keV": list(bounds),
            "by_stream": by,
            "physical_reference_flux": {
                "reference_flux_ph_cm2_s": REFERENCE_FLUX,
                "rate_to_injection_plane_cps": injection_rate,
                "prompt_background_cps": prompt,
                "delayed_background_cps": delayed,
                "atm511_background_cps": atmosphere,
                "background_cps": background,
                "science_unit_acceptance": science_unit,
                "signal_cps_at_reference_flux": signal,
                "uncertainty_95": {
                    "method": (
                        "independent exact Garwood two-sided 95% upper counts per "
                        "background component and Clopper-Pearson two-sided 95% "
                        "lower focused-signal acceptance, evaluated after the fixed "
                        "event-level response realization"
                    ),
                    "prompt_components": prompt_components,
                    "prompt_background_upper95_cps": prompt_upper,
                    "delayed_background_interval95_cps": poisson_interval_95(
                        delayed_events, delayed_weight
                    ),
                    "delayed_background_upper95_cps": delayed_upper,
                    "atm511_background_interval95_cps": poisson_interval_95(
                        atm_events, atm_weight
                    ),
                    "atm511_background_upper95_cps": atm_upper,
                    "background_upper95_cps": background_upper,
                    "signal_trials": SIGNAL_TRIALS,
                    "signal_successes": signal_successes,
                    "signal_acceptance_lower95": signal_acceptance_lower,
                    "signal_cps_lower95_at_reference_flux": signal_lower,
                },
            },
        }
    return {
        "status": "PASS_O8_EVENT_LEVEL_420EV_FWHM_RESPONSE_STEP05",
        "response_seed": PRIMARY_RESPONSE_SEED,
        "response_model": {
            "distribution": "independent Gaussian per aggregated TES pixel readout",
            "fwhm_keV": FWHM_KEV,
            "sigma_keV": GAUSSIAN_SIGMA_KEV,
            "post_noise_hit_threshold_keV": TES_HIT_THRESHOLD_KEV,
            "ordering": [
                "aggregate Cosima deposits by TES pixel",
                "apply independent Gaussian energy response",
                "discard measured TES hits below 0.3 keV",
                "sum surviving TES hits into event energy",
                "apply W2/broad window and 50-keV active-veto selection",
                "evaluate side-entry Compton/FoV topology with measured hit energies",
            ],
        },
        "occupancy_day15": {**main["occupancy"], **atm["occupancy"]},
        "windows": windows,
    }


def reference_response_step05(reference: dict[str, Any]) -> dict[str, Any]:
    base = load_json(REFERENCE_STEP05)
    injection_rate = float(
        base["science_physical_normalization"]["rate_to_v3p5_injection_plane_s-1"]
    )
    windows: dict[str, Any] = {}
    for name, bounds in WINDOWS.items():
        by = reference["windows"][name]["by_stream"]
        prompt = float(by["prompt"]["side_compton_fov_pass_rate_cps"])
        delayed = float(by["delayed"]["side_compton_fov_pass_rate_cps"])
        science_unit = float(by["science"]["side_compton_fov_pass_rate_cps"])
        signal = science_unit * injection_rate
        windows[name] = {
            "window_keV": list(bounds),
            "by_stream": by,
            "physical_reference_flux": {
                "reference_flux_ph_cm2_s": REFERENCE_FLUX,
                "rate_to_injection_plane_cps": injection_rate,
                "prompt_background_cps": prompt,
                "delayed_background_cps": delayed,
                "background_cps": prompt + delayed,
                "science_unit_acceptance": science_unit,
                "signal_cps_at_reference_flux": signal,
                "selected_effective_area_cm2": signal / REFERENCE_FLUX,
            },
        }
    return {
        "status": "PASS_REFERENCE_EVENT_LEVEL_420EV_FWHM_RESPONSE_STEP05",
        "response_seed": PRIMARY_RESPONSE_SEED,
        "occupancy_day15": reference["occupancy"],
        "windows": windows,
    }


def fold_w2_mission(step05: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    with BASE_STEP06_CSV.open("r", encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["selection_id"] == "w2_510p58_511p42"]
    rows.sort(key=lambda row: int(row["time_bin_id"]))
    if len(rows) != 81:
        raise ClosureError(f"expected 81 W2 mission bins, found {len(rows)}")
    day15 = next(row for row in rows if math.isclose(float(row["day_mid"]), 15.0))

    occ = step05["occupancy_day15"]
    ratios = {
        "prompt": float(occ["prompt"]["rate_hz"]) / float(day15["prompt_event_rate_hz"]),
        "delayed": float(occ["delayed"]["rate_hz"]) / float(day15["delayed_event_rate_hz"]),
        "atm511_sidecar": float(occ["atm511_sidecar"]["rate_hz"]) / float(day15["atm511_event_rate_hz"]),
    }
    phys = step05["windows"]["w2_510p58_511p42"]["physical_reference_flux"]
    prompt_day15 = float(phys["prompt_background_cps"])
    delayed_day15 = float(phys["delayed_background_cps"])
    atm_day15 = float(phys["atm511_background_cps"])
    signal_day15 = float(phys["signal_cps_at_reference_flux"])
    unc = phys["uncertainty_95"]
    prompt_upper_day15 = float(unc["prompt_background_upper95_cps"])
    delayed_upper_day15 = float(unc["delayed_background_upper95_cps"])
    atm_upper_day15 = float(unc["atm511_background_upper95_cps"])
    signal_lower_day15 = float(unc["signal_cps_lower95_at_reference_flux"])

    cumulative_signal = 0.0
    cumulative_background = 0.0
    cumulative_signal_lower = 0.0
    cumulative_background_upper = 0.0
    timeline: list[dict[str, Any]] = []
    days: list[float] = []
    zs: list[float] = []
    zs_conservative: list[float] = []
    elapsed_s = 0.0
    for row in rows:
        dt_s = float(row["dt_s"])
        prompt_scale = float(row["prompt_scale_to_day15"])
        delayed_scale = float(row["delayed_activity_scale_to_day15"])
        atm_scale = float(row["atm511_phi_4pi_scale_to_day15"])
        science_scale = float(row["science_atm_scale_to_day15"])
        prompt_occ = float(row["prompt_event_rate_hz"]) * ratios["prompt"]
        delayed_occ = float(row["delayed_event_rate_hz"]) * ratios["delayed"]
        atm_occ = float(row["atm511_event_rate_hz"]) * ratios["atm511_sidecar"]
        occupancy = prompt_occ + delayed_occ + atm_occ
        live = math.exp(-occupancy * COINCIDENCE_WINDOW_S)
        prompt_rate = prompt_day15 * prompt_scale
        delayed_rate = delayed_day15 * delayed_scale
        atm_rate = atm_day15 * atm_scale
        background = prompt_rate + delayed_rate + atm_rate
        signal = signal_day15 * science_scale
        background_upper = (
            prompt_upper_day15 * prompt_scale
            + delayed_upper_day15 * delayed_scale
            + atm_upper_day15 * atm_scale
        )
        signal_lower = signal_lower_day15 * science_scale
        cumulative_signal += signal * live * dt_s
        cumulative_background += background * live * dt_s
        cumulative_signal_lower += signal_lower * live * dt_s
        cumulative_background_upper += background_upper * live * dt_s
        elapsed_s += dt_s
        z = cumulative_signal / math.sqrt(cumulative_background)
        z_cons = cumulative_signal_lower / math.sqrt(cumulative_background_upper)
        day = elapsed_s / SECONDS_PER_DAY
        days.append(day)
        zs.append(z)
        zs_conservative.append(z_cons)
        timeline.append(
            {
                "time_bin_id": int(row["time_bin_id"]),
                "day_mid": float(row["day_mid"]),
                "elapsed_stop_day": day,
                "dt_s": dt_s,
                "prompt_event_rate_hz": prompt_occ,
                "delayed_event_rate_hz": delayed_occ,
                "atm511_event_rate_hz": atm_occ,
                "coincidence_occupancy_rate_hz": occupancy,
                "accidental_live_factor": live,
                "prompt_final_cps_noacc": prompt_rate,
                "delayed_final_cps_noacc": delayed_rate,
                "atm511_final_cps_noacc": atm_rate,
                "background_final_cps_noacc": background,
                "signal_final_cps_noacc": signal,
                "background_final_upper95_cps_noacc": background_upper,
                "signal_final_lower95_cps_noacc": signal_lower,
                "cumulative_source_counts": cumulative_signal,
                "cumulative_background_counts": cumulative_background,
                "cumulative_source_lower95_counts": cumulative_signal_lower,
                "cumulative_background_upper95_counts": cumulative_background_upper,
                "counting_Z": z,
                "counting_Z_conservative95": z_cons,
            }
        )

    def crossing(values: list[float], threshold: float) -> float | None:
        for index, value in enumerate(values):
            if value < threshold:
                continue
            if index == 0:
                return days[0]
            x0, x1 = days[index - 1], days[index]
            y0, y1 = values[index - 1], values[index]
            return x1 if y1 == y0 else x0 + (threshold - y0) * (x1 - x0) / (y1 - y0)
        return None

    def time_or_extrapolate(values: list[float], threshold: float) -> float:
        value = crossing(values, threshold)
        if value is not None:
            return value
        return days[-1] * (threshold / values[-1]) ** 2

    z20 = zs[-1]
    z20_cons = zs_conservative[-1]
    summary = {
        "status": "PASS_O8_EVENT_LEVEL_420EV_FWHM_RESPONSE_MISSION_FOLD",
        "reference_flux_ph_cm2_s": REFERENCE_FLUX,
        "day15_selected_rates_cps": {
            "prompt": prompt_day15,
            "delayed": delayed_day15,
            "atm511": atm_day15,
            "background": prompt_day15 + delayed_day15 + atm_day15,
            "signal": signal_day15,
            "background_upper95": prompt_upper_day15 + delayed_upper_day15 + atm_upper_day15,
            "signal_lower95": signal_lower_day15,
        },
        "occupancy_response_to_retained_ratio": ratios,
        "source_counts_20d": cumulative_signal,
        "background_counts_20d": cumulative_background,
        "source_lower95_counts_20d": cumulative_signal_lower,
        "background_upper95_counts_20d": cumulative_background_upper,
        "Z20d": z20,
        "Z20d_conservative95": z20_cons,
        "flux_3sigma_20d_ph_cm2_s": REFERENCE_FLUX * 3.0 / z20,
        "flux_3sigma_20d_conservative95_ph_cm2_s": REFERENCE_FLUX * 3.0 / z20_cons,
        "T3_day": time_or_extrapolate(zs, 3.0),
        "T5_day": time_or_extrapolate(zs, 5.0),
        "T3_day_conservative95": time_or_extrapolate(zs_conservative, 3.0),
        "T5_day_conservative95": time_or_extrapolate(zs_conservative, 5.0),
        "accidental_loss_min": min(1.0 - float(row["accidental_live_factor"]) for row in timeline),
        "accidental_loss_max": max(1.0 - float(row["accidental_live_factor"]) for row in timeline),
    }
    return summary, timeline


def fold_reference_w2_mission(step05: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    with REFERENCE_STEP06_CSV.open("r", encoding="utf-8", newline="") as handle:
        rows = [
            row
            for row in csv.DictReader(handle)
            if row["selection_id"] == "w2_510p58_511p42"
        ]
    rows.sort(key=lambda row: int(row["time_bin_id"]))
    if len(rows) != 81:
        raise ClosureError(f"expected 81 reference W2 mission bins, found {len(rows)}")
    day15 = next(row for row in rows if math.isclose(float(row["day_mid"]), 15.0))
    occ = step05["occupancy_day15"]
    ratios = {
        "prompt": float(occ["prompt"]["rate_hz"]) / float(day15["prompt_event_rate_hz"]),
        "delayed": float(occ["delayed"]["rate_hz"]) / float(day15["delayed_event_rate_hz"]),
    }
    phys = step05["windows"]["w2_510p58_511p42"]["physical_reference_flux"]
    prompt_day15 = float(phys["prompt_background_cps"])
    delayed_day15 = float(phys["delayed_background_cps"])
    signal_day15 = float(phys["signal_cps_at_reference_flux"])
    cumulative_signal = 0.0
    cumulative_background = 0.0
    elapsed_s = 0.0
    days: list[float] = []
    zs: list[float] = []
    timeline: list[dict[str, Any]] = []
    for row in rows:
        dt_s = float(row["dt_s"])
        prompt_scale = float(row["prompt_scale_to_day15"])
        delayed_scale = float(row["delayed_activity_scale_to_day15"])
        science_scale = float(row["science_atm_scale_to_day15"])
        prompt_occ = float(row["prompt_event_rate_hz"]) * ratios["prompt"]
        delayed_occ = float(row["delayed_event_rate_hz"]) * ratios["delayed"]
        occupancy = prompt_occ + delayed_occ
        live = math.exp(-occupancy * COINCIDENCE_WINDOW_S)
        prompt_rate = prompt_day15 * prompt_scale
        delayed_rate = delayed_day15 * delayed_scale
        background = prompt_rate + delayed_rate
        signal = signal_day15 * science_scale
        cumulative_signal += signal * live * dt_s
        cumulative_background += background * live * dt_s
        elapsed_s += dt_s
        day = elapsed_s / SECONDS_PER_DAY
        z = cumulative_signal / math.sqrt(cumulative_background)
        days.append(day)
        zs.append(z)
        timeline.append(
            {
                "time_bin_id": int(row["time_bin_id"]),
                "day_mid": float(row["day_mid"]),
                "elapsed_stop_day": day,
                "dt_s": dt_s,
                "prompt_event_rate_hz": prompt_occ,
                "delayed_event_rate_hz": delayed_occ,
                "coincidence_occupancy_rate_hz": occupancy,
                "accidental_live_factor": live,
                "prompt_final_cps_noacc": prompt_rate,
                "delayed_final_cps_noacc": delayed_rate,
                "background_final_cps_noacc": background,
                "signal_final_cps_noacc": signal,
                "cumulative_source_counts": cumulative_signal,
                "cumulative_background_counts": cumulative_background,
                "counting_Z": z,
            }
        )

    def crossing(threshold: float) -> float:
        for index, value in enumerate(zs):
            if value < threshold:
                continue
            if index == 0:
                return days[0]
            x0, x1 = days[index - 1], days[index]
            y0, y1 = zs[index - 1], zs[index]
            return x1 if y1 == y0 else x0 + (threshold - y0) * (x1 - x0) / (y1 - y0)
        return days[-1] * (threshold / zs[-1]) ** 2

    z20 = zs[-1]
    return {
        "status": "PASS_REFERENCE_EVENT_LEVEL_420EV_FWHM_RESPONSE_MISSION_FOLD",
        "day15_selected_rates_cps": {
            "prompt": prompt_day15,
            "delayed": delayed_day15,
            "background": prompt_day15 + delayed_day15,
            "signal": signal_day15,
        },
        "occupancy_response_to_retained_ratio": ratios,
        "source_counts_20d": cumulative_signal,
        "background_counts_20d": cumulative_background,
        "Z20d": z20,
        "flux_3sigma_20d_ph_cm2_s": REFERENCE_FLUX * 3.0 / z20,
        "T3_day": crossing(3.0),
        "T5_day": crossing(5.0),
        "accidental_loss_min": min(1.0 - float(row["accidental_live_factor"]) for row in timeline),
        "accidental_loss_max": max(1.0 - float(row["accidental_live_factor"]) for row in timeline),
    }, timeline


def validate_reference_mission_fold_reproduction(reference_unsmeared: dict[str, Any]) -> dict[str, Any]:
    step = reference_response_step05(reference_unsmeared)
    actual, _timeline = fold_reference_w2_mission(step)
    expected_checks = load_json(REFERENCE_STEP08)["checks"]
    expected = {
        "Z20d": float(expected_checks["A_reference_w2_Z20d_time_dependent"]),
        "flux_3sigma_20d_ph_cm2_s": float(
            expected_checks["A_reference_w2_flux_3sigma_20d_ph_cm2_s"]
        ),
        "T3_day": float(expected_checks["A_reference_w2_T3_day"]),
        "T5_day": float(expected_checks["A_reference_w2_T5_day"]),
    }
    for key, value in expected.items():
        _assert_close(float(actual[key]), value, f"reference mission-fold reproduction {key}")
    return {
        "status": "PASS_EXACT_REFERENCE_STEP08_REPRODUCTION",
        "base_step08": rel(REFERENCE_STEP08),
        "expected": expected,
        "reproduced": {key: actual[key] for key in expected},
    }


def validate_mission_fold_reproduction() -> dict[str, Any]:
    """Prove that the local fold reproduces the retained O8 Step08 authority."""
    base05 = load_json(BASE_STEP05)
    base08 = load_json(BASE_STEP08)
    with BASE_STEP06_CSV.open("r", encoding="utf-8", newline="") as handle:
        rows = [
            row
            for row in csv.DictReader(handle)
            if row["selection_id"] == "w2_510p58_511p42"
        ]
    day15 = next(row for row in rows if math.isclose(float(row["day_mid"]), 15.0))
    phys = base05["windows"]["w2_510p58_511p42"]["physical_reference_flux"]
    proxy = {
        "occupancy_day15": {
            "prompt": {"rate_hz": float(day15["prompt_event_rate_hz"])},
            "delayed": {"rate_hz": float(day15["delayed_event_rate_hz"])},
            "atm511_sidecar": {"rate_hz": float(day15["atm511_event_rate_hz"])},
        },
        "windows": {
            "w2_510p58_511p42": {
                "physical_reference_flux": {
                    "prompt_background_cps": float(phys["prompt_background_cps"]),
                    "delayed_background_cps": float(phys["delayed_background_cps"]),
                    "atm511_background_cps": float(phys["atm511_sidecar_background_cps"]),
                    "signal_cps_at_reference_flux": float(phys["signal_cps_at_reference_flux"]),
                    "uncertainty_95": phys["uncertainty_95"],
                }
            }
        },
    }
    actual, _timeline = fold_w2_mission(proxy)
    checks = base08["checks"]
    expected = {
        "Z20d": float(checks["A_reference_w2_Z20d_time_dependent"]),
        "Z20d_conservative95": float(checks["A_reference_w2_Z20d_conservative95"]),
        "flux_3sigma_20d_ph_cm2_s": float(
            checks["A_reference_w2_flux_3sigma_20d_ph_cm2_s"]
        ),
        "flux_3sigma_20d_conservative95_ph_cm2_s": float(
            checks["A_reference_w2_flux_3sigma_20d_conservative95_ph_cm2_s"]
        ),
        "T3_day": float(checks["A_reference_w2_T3_day"]),
        "T5_day": float(checks["A_reference_w2_T5_day"]),
        "T3_day_conservative95": float(checks["A_reference_w2_T3_day_conservative95"]),
        "T5_day_conservative95": float(checks["A_reference_w2_T5_day_conservative95"]),
    }
    for key, value in expected.items():
        _assert_close(float(actual[key]), value, f"mission-fold reproduction {key}", atol=1.0e-12)
    return {
        "status": "PASS_EXACT_RETAINED_STEP08_REPRODUCTION",
        "base_step08": rel(BASE_STEP08),
        "expected": expected,
        "reproduced": {key: actual[key] for key in expected},
    }


def flatten_replica(
    replica_index: int,
    seed: int,
    main: dict[str, Any],
    atm: dict[str, Any],
    mission: dict[str, Any],
) -> dict[str, Any]:
    w2 = main["windows"]["w2_510p58_511p42"]["by_stream"]
    atm_w2 = atm["windows"]["w2_510p58_511p42"]["by_stream"]["atm511_sidecar"]
    return {
        "replica_index": replica_index,
        "response_seed": seed,
        "prompt_final_events": w2["prompt"]["side_compton_fov_pass_events"],
        "prompt_final_cps": w2["prompt"]["side_compton_fov_pass_rate_cps"],
        "delayed_final_events": w2["delayed"]["side_compton_fov_pass_events"],
        "delayed_final_cps": w2["delayed"]["side_compton_fov_pass_rate_cps"],
        "atm511_final_events": atm_w2["side_compton_fov_pass_events"],
        "atm511_final_cps": atm_w2["side_compton_fov_pass_rate_cps"],
        "science_final_events": w2["science"]["side_compton_fov_pass_events"],
        "science_unit_acceptance": w2["science"]["side_compton_fov_pass_rate_cps"],
        "day15_background_cps": mission["day15_selected_rates_cps"]["background"],
        "day15_signal_cps": mission["day15_selected_rates_cps"]["signal"],
        "Z20d": mission["Z20d"],
        "flux_3sigma_20d_ph_cm2_s": mission["flux_3sigma_20d_ph_cm2_s"],
    }


def evaluate_replica_worker(index: int) -> dict[str, Any]:
    if (
        _WORKER_MAIN is None
        or _WORKER_ATM is None
        or _WORKER_REFERENCE is None
        or _WORKER_STEP05 is None
        or _WORKER_DISK is None
    ):
        raise ClosureError("response worker context is not initialized")
    seed = PRIMARY_RESPONSE_SEED + index * RESPONSE_SEED_STRIDE
    main = evaluate_catalog(
        _WORKER_MAIN,
        _WORKER_STEP05,
        _WORKER_DISK,
        seed,
        apply_response=True,
        apply_threshold=True,
        include_details=index == 0,
    )
    # Separate seed stream prevents catalogue length/order from correlating the
    # atmospheric response with the main catalogue response.
    atm_seed = seed + 1_000_000_007
    atm = evaluate_catalog(
        _WORKER_ATM,
        _WORKER_STEP05,
        _WORKER_DISK,
        atm_seed,
        apply_response=True,
        apply_threshold=True,
        include_details=index == 0,
    )
    step = primary_step05(main, atm)
    mission, timeline = fold_w2_mission(step)
    reference = evaluate_catalog(
        _WORKER_REFERENCE,
        _WORKER_STEP05,
        _WORKER_DISK,
        seed,
        apply_response=True,
        apply_threshold=True,
        include_details=index == 0,
    )
    reference_step = reference_response_step05(reference)
    reference_mission, reference_timeline = fold_reference_w2_mission(reference_step)
    row = flatten_replica(index, seed, main, atm, mission)
    reference_w2 = reference_step["windows"]["w2_510p58_511p42"]
    row.update(
        {
            "reference_prompt_final_cps": reference_w2["physical_reference_flux"]["prompt_background_cps"],
            "reference_delayed_final_cps": reference_w2["physical_reference_flux"]["delayed_background_cps"],
            "reference_signal_final_cps": reference_w2["physical_reference_flux"]["signal_cps_at_reference_flux"],
            "reference_Z20d": reference_mission["Z20d"],
            "reference_flux_3sigma_20d_ph_cm2_s": reference_mission["flux_3sigma_20d_ph_cm2_s"],
        }
    )
    result: dict[str, Any] = {
        "index": index,
        "row": row,
    }
    if index == 0:
        result["primary"] = {
            "main": main,
            "atm": atm,
            "step": step,
            "mission": mission,
            "timeline": timeline,
            "reference": reference,
            "reference_step": reference_step,
            "reference_mission": reference_mission,
            "reference_timeline": reference_timeline,
        }
    return result


def ensemble_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = [
        "prompt_final_cps",
        "delayed_final_cps",
        "atm511_final_cps",
        "science_unit_acceptance",
        "day15_background_cps",
        "day15_signal_cps",
        "Z20d",
        "flux_3sigma_20d_ph_cm2_s",
        "reference_prompt_final_cps",
        "reference_delayed_final_cps",
        "reference_signal_final_cps",
        "reference_Z20d",
        "reference_flux_3sigma_20d_ph_cm2_s",
    ]
    summary: dict[str, Any] = {}
    for metric in metrics:
        values = np.asarray([float(row[metric]) for row in rows], dtype=np.float64)
        half = len(values) // 2
        first = float(np.mean(values[:half]))
        second = float(np.mean(values[half:]))
        mean = float(np.mean(values))
        sample_sd = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
        primary = float(rows[0][metric])
        standardized = (
            abs(primary - mean) / sample_sd
            if sample_sd > 0.0
            else (0.0 if primary == mean else math.inf)
        )
        summary[metric] = {
            "mean": mean,
            "sample_sd": sample_sd,
            "mean_standard_error": float(sample_sd / math.sqrt(len(values)))
            if len(values) > 1
            else 0.0,
            "q02p5": float(np.quantile(values, 0.025)),
            "q16": float(np.quantile(values, 0.16)),
            "median": float(np.median(values)),
            "q84": float(np.quantile(values, 0.84)),
            "q97p5": float(np.quantile(values, 0.975)),
            "first_half_mean": first,
            "second_half_mean": second,
            "half_mean_relative_difference": abs(first - second) / abs(mean) if mean else 0.0,
            "primary_value": primary,
            "primary_relative_deviation_from_mean": abs(primary - mean) / abs(mean)
            if mean
            else 0.0,
            "primary_standardized_deviation": standardized,
            "primary_within_95_response_interval": bool(
                np.quantile(values, 0.025) <= primary <= np.quantile(values, 0.975)
            ),
        }
    failures = [
        metric
        for metric, record in summary.items()
        if record["primary_standardized_deviation"] > 3.0
        or record["primary_relative_deviation_from_mean"] > 0.20
        or record["half_mean_relative_difference"] > 0.10
    ]
    if len(rows) < 32:
        failures.append("replica_count_below_32")
    return {
        "status": "PASS_RESPONSE_SEED_ENSEMBLE" if not failures else "FAIL_RESPONSE_SEED_ENSEMBLE",
        "replicas": len(rows),
        "primary_seed": PRIMARY_RESPONSE_SEED,
        "seed_stride": RESPONSE_SEED_STRIDE,
        "failure_metrics": failures,
        "acceptance_contract": (
            "at least 32 replicas; the preregistered primary value is within three "
            "response-ensemble standard deviations and 20% of the ensemble mean; "
            "first/second-half means differ by no more than 10% for every audited metric"
        ),
        "metrics": summary,
    }


def render_readme(payload: dict[str, Any]) -> str:
    mission = payload["primary_authority"]["mission_fold"]
    reference_mission = payload["primary_authority"]["reference_mission_fold"]
    rates = mission["day15_selected_rates_cps"]
    ensemble = payload["response_seed_ensemble"]
    return "\n".join(
        [
            "# EA O8 detector-energy-response closure (2026-07-13)",
            "",
            f"Status: `{payload['status']}`",
            "",
            "This package applies the manuscript's 420 eV FWHM TES response at the pixel-readout level without modifying retained O8 transport products. Each aggregated TES-pixel deposit receives an independent Gaussian response with sigma = 0.17836 keV, measured hits below 0.3 keV are removed, and the retained W2, 50-keV active-veto, and side-entry Compton/FoV selection is rerun with the measured hit energies.",
            "",
            "## Primary W2 result",
            "",
            f"- Response seed: `{PRIMARY_RESPONSE_SEED}`.",
            f"- Day-15 selected background: `{rates['background']:.12g}` cps (prompt `{rates['prompt']:.12g}`, neutron-delayed `{rates['delayed']:.12g}`, atmospheric-511 `{rates['atm511']:.12g}`).",
            f"- Reference-flux signal: `{rates['signal']:.12g}` cps.",
            f"- Folded 20 d counting significance: `{mission['Z20d']:.8g}`.",
            f"- Folded 20 d 3-sigma flux threshold: `{mission['flux_3sigma_20d_ph_cm2_s']:.8g}` ph cm^-2 s^-1.",
            f"- Conservative counting threshold: `{mission['flux_3sigma_20d_conservative95_ph_cm2_s']:.8g}` ph cm^-2 s^-1.",
            f"- Response-convolved Mass_model_511 reference threshold: `{reference_mission['flux_3sigma_20d_ph_cm2_s']:.8g}` ph cm^-2 s^-1.",
            "",
            "## Validation",
            "",
            f"- The response-off replay reproduces every retained Step05/atmospheric cut-flow count and rate exactly: `{payload['unsmeared_reproduction']['status']}`.",
            f"- The reference response-off replay reproduces the retained Mass_model_511 Step05 and Step08 authorities: `{payload['reference_mission_fold_reproduction']['status']}`.",
            f"- Detector-response seed convergence: `{ensemble['status']}` across `{ensemble['replicas']}` deterministic replicas.",
            "- The response ensemble is a numerical integration audit; it is not added as a separate physical systematic uncertainty.",
            "",
            "## Authorities",
            "",
            f"- Retained event catalogue: `{rel(BASE_CATALOG)}`.",
            f"- Retained Mass_model_511 reference catalogue: `{rel(REFERENCE_CATALOG)}`.",
            f"- Retained atmospheric SIM: `{rel(BASE_ATM_SIM)}`.",
            f"- Machine-readable closure: `{rel(SUMMARY_JSON)}`.",
            f"- Response replicas: `{rel(REPLICAS_CSV)}`.",
            f"- W2 mission timeline: `{rel(TIMELINE_CSV)}`.",
            "",
        ]
    )


def self_test() -> dict[str, Any]:
    sigma_expected = 0.178357578060484
    if not math.isclose(GAUSSIAN_SIGMA_KEV, sigma_expected, rel_tol=0.0, abs_tol=1.0e-15):
        raise ClosureError(f"FWHM-to-sigma conversion changed: {GAUSSIAN_SIGMA_KEV}")
    fake = CompactCatalog(
        label="self_test",
        event_id=np.asarray([1, 2], dtype=np.int64),
        stream=np.asarray(["science", "science"], dtype=object),
        tag=np.asarray(["x", "x"], dtype=object),
        rate_hz=np.asarray([0.5, 0.5]),
        active_keV=np.asarray([0.0, 0.0]),
        raw_total_keV=np.asarray([511.0, 511.0]),
        hit_start=np.asarray([0, 1], dtype=np.int64),
        hit_count=np.asarray([1, 2], dtype=np.int64),
        hit_uid=np.asarray(["a", "b", "c"], dtype=object),
        hit_layer=np.asarray([0, 0, 1], dtype=np.int16),
        hit_e_keV=np.asarray([511.0, 510.8, 0.2]),
        hit_x_cm=np.zeros(3),
        hit_y_cm=np.zeros(3),
        hit_z_cm=np.zeros(3),
        active_only_rate_by_stream={},
        active_only_events_by_stream={},
        generated_events=2,
    )
    hits, totals, multiplicity = measured_hits(
        fake, None, apply_response=False, apply_threshold=True
    )
    if not np.array_equal(hits, np.asarray([511.0, 510.8, 0.0])):
        raise ClosureError("threshold self-test failed")
    if not np.allclose(totals, [511.0, 510.8]):
        raise ClosureError("event-sum self-test failed")
    if not np.array_equal(multiplicity, [1, 1]):
        raise ClosureError("multiplicity self-test failed")
    return {
        "status": "PASS_SELF_TEST",
        "fwhm_keV": FWHM_KEV,
        "sigma_keV": GAUSSIAN_SIGMA_KEV,
        "threshold_keV": TES_HIT_THRESHOLD_KEV,
    }


def run(replicas: int, workers: int, rebuild_atm_cache: bool) -> dict[str, Any]:
    if replicas < 4 or replicas % 2:
        raise ClosureError("--replicas must be an even integer >= 4")
    if workers < 1:
        raise ClosureError("--workers must be >= 1")
    for path in (
        BASE_CATALOG,
        BASE_STEP05,
        BASE_STEP06_CSV,
        BASE_STEP08,
        BASE_ATM_SUMMARY,
        BASE_ATM_SIM,
        BASE_ATM_PARSER,
        STEP05_IMPLEMENTATION,
        STEP09_SUMMARY,
        O8_DETECTOR_MAP,
        REFERENCE_CATALOG,
        REFERENCE_STEP05,
        REFERENCE_STEP06_CSV,
        REFERENCE_STEP08,
    ):
        if not path.is_file():
            raise ClosureError(f"required authority is missing: {rel(path)}")

    detector_contract = audit_detector_contract()
    step05, disk = load_step05_selection()
    main_cat = compact_main_catalog()
    atm_cat = build_or_load_atm_catalog(rebuild_atm_cache)
    reference_cat = compact_event_catalog(
        REFERENCE_CATALOG, "reference_mass_model_511_prompt_delayed_signal"
    )

    unsmeared_main = evaluate_catalog(
        main_cat,
        step05,
        disk,
        None,
        apply_response=False,
        apply_threshold=False,
        include_details=True,
    )
    unsmeared_atm = evaluate_catalog(
        atm_cat,
        step05,
        disk,
        None,
        apply_response=False,
        apply_threshold=False,
        include_details=True,
    )
    reproduction = validate_unsmeared_reproduction(unsmeared_main, unsmeared_atm)
    mission_reproduction = validate_mission_fold_reproduction()
    unsmeared_reference = evaluate_catalog(
        reference_cat,
        step05,
        disk,
        None,
        apply_response=False,
        apply_threshold=False,
        include_details=True,
    )
    reference_reproduction = validate_unsmeared_reference_reproduction(unsmeared_reference)
    reference_mission_reproduction = validate_reference_mission_fold_reproduction(
        unsmeared_reference
    )

    global _WORKER_MAIN, _WORKER_ATM, _WORKER_REFERENCE, _WORKER_STEP05, _WORKER_DISK
    _WORKER_MAIN = main_cat
    _WORKER_ATM = atm_cat
    _WORKER_REFERENCE = reference_cat
    _WORKER_STEP05 = step05
    _WORKER_DISK = disk
    replica_rows: list[dict[str, Any]] = []
    primary_main: dict[str, Any] | None = None
    primary_atm: dict[str, Any] | None = None
    primary_step: dict[str, Any] | None = None
    primary_mission: dict[str, Any] | None = None
    primary_timeline: list[dict[str, Any]] | None = None
    primary_reference: dict[str, Any] | None = None
    primary_reference_step: dict[str, Any] | None = None
    primary_reference_mission: dict[str, Any] | None = None
    primary_reference_timeline: list[dict[str, Any]] | None = None
    worker_count = min(workers, replicas)
    if worker_count == 1:
        results = map(evaluate_replica_worker, range(replicas))
        pool = None
    else:
        pool = mp.get_context("fork").Pool(processes=worker_count)
        results = pool.imap(evaluate_replica_worker, range(replicas), chunksize=1)
    try:
        for completed, result in enumerate(results, start=1):
            replica_rows.append(result["row"])
            if "primary" in result:
                primary = result["primary"]
                primary_main = primary["main"]
                primary_atm = primary["atm"]
                primary_step = primary["step"]
                primary_mission = primary["mission"]
                primary_timeline = primary["timeline"]
                primary_reference = primary["reference"]
                primary_reference_step = primary["reference_step"]
                primary_reference_mission = primary["reference_mission"]
                primary_reference_timeline = primary["reference_timeline"]
            if completed % max(1, replicas // 8) == 0 or completed == replicas:
                print(f"[response] completed {completed}/{replicas} replicas", flush=True)
    finally:
        if pool is not None:
            pool.close()
            pool.join()
    replica_rows.sort(key=lambda row: int(row["replica_index"]))

    assert primary_main is not None
    assert primary_atm is not None
    assert primary_step is not None
    assert primary_mission is not None
    assert primary_timeline is not None
    assert primary_reference is not None
    assert primary_reference_step is not None
    assert primary_reference_mission is not None
    assert primary_reference_timeline is not None
    ensemble = ensemble_summary(replica_rows)
    status = (
        "PASS_O8_EVENT_LEVEL_420EV_FWHM_ENERGY_RESPONSE_CLOSURE"
        if ensemble["status"] == "PASS_RESPONSE_SEED_ENSEMBLE"
        else "FAIL_O8_EVENT_LEVEL_420EV_FWHM_ENERGY_RESPONSE_CLOSURE"
    )
    payload = {
        "status": status,
        "generated_at_utc": now_utc(),
        "claim": (
            "Paper-stated 420 eV FWHM TES energy response applied at pixel-readout "
            "level before the complete retained O8 detector selection."
        ),
        "input_authorities": {
            "o8_event_catalog": rel(BASE_CATALOG),
            "o8_event_catalog_sha256": sha256(BASE_CATALOG),
            "o8_step05": rel(BASE_STEP05),
            "o8_step05_sha256": sha256(BASE_STEP05),
            "o8_atm511_sim": rel(BASE_ATM_SIM),
            "o8_atm511_sim_sha256": sha256(BASE_ATM_SIM),
            "o8_atm511_summary": rel(BASE_ATM_SUMMARY),
            "selection_implementation": rel(STEP05_IMPLEMENTATION),
            "selection_implementation_sha256": sha256(STEP05_IMPLEMENTATION),
            "mission_scale_authority": rel(BASE_STEP06_CSV),
            "mission_scale_authority_sha256": sha256(BASE_STEP06_CSV),
            "reference_event_catalog": rel(REFERENCE_CATALOG),
            "reference_event_catalog_sha256": sha256(REFERENCE_CATALOG),
            "reference_step05": rel(REFERENCE_STEP05),
            "reference_step06": rel(REFERENCE_STEP06_CSV),
            "reference_step08": rel(REFERENCE_STEP08),
        },
        "detector_contract": detector_contract,
        "unsmeared_reproduction": reproduction,
        "mission_fold_reproduction": mission_reproduction,
        "reference_unsmeared_reproduction": reference_reproduction,
        "reference_mission_fold_reproduction": reference_mission_reproduction,
        "primary_authority": {
            "response_seed": PRIMARY_RESPONSE_SEED,
            "main_catalog_selection": primary_main,
            "atm511_selection": primary_atm,
            "step05": primary_step,
            "mission_fold": primary_mission,
            "reference_catalog_selection": primary_reference,
            "reference_step05": primary_reference_step,
            "reference_mission_fold": primary_reference_mission,
        },
        "response_seed_ensemble": ensemble,
        "outputs": {
            "summary_json": rel(SUMMARY_JSON),
            "replicas_csv": rel(REPLICAS_CSV),
            "timeline_csv": rel(TIMELINE_CSV),
            "reference_timeline_csv": rel(REFERENCE_TIMELINE_CSV),
            "atm_compact_cache": rel(ATM_CACHE),
        },
        "scope": (
            "This package changes detector response and derived selection only. It does "
            "not replace particle transport, source normalization, activity inventory, "
            "or trajectory scale authorities."
        ),
    }
    write_json(SUMMARY_JSON, payload)
    write_csv(REPLICAS_CSV, replica_rows)
    write_csv(TIMELINE_CSV, primary_timeline)
    write_csv(REFERENCE_TIMELINE_CSV, primary_reference_timeline)
    README.write_text(render_readme(payload), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replicas", type=int, default=64)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--rebuild-atm-cache", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        payload = (
            self_test()
            if args.self_test
            else run(args.replicas, args.workers, args.rebuild_atm_cache)
        )
        print(json.dumps(payload if args.self_test else {
            "status": payload["status"],
            "summary": rel(SUMMARY_JSON),
            "Z20d": payload["primary_authority"]["mission_fold"]["Z20d"],
            "F3_20d": payload["primary_authority"]["mission_fold"]["flux_3sigma_20d_ph_cm2_s"],
        }, indent=2))
        return 0 if str(payload["status"]).startswith("PASS") else 2
    except (ClosureError, OSError, ValueError, KeyError, EOFError, gzip.BadGzipFile) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
