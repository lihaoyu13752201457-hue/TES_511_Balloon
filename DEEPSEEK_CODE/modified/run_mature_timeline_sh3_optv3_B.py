#!/usr/bin/env python3
"""SH3 OptV3 mature Poisson timeline + Aeff + Fmin — design intent B.

MODIFIED (2026-08-19, option B: new focal plane = chimney axis z=-2.8):
  - signal SIM = 37,194-ray transport re-pointed to the chimney focal plane
    (eventlist translated world +(-21.566757, 0, +24.960869);
     local dx=-32.9 -> injection x=-46, dz=+2.4 -> beam line z=-2.8)
  - verifies the signal SIM SHA-256 against analysis_inputs before replay
  - writes fixed outputs to outputs/05_mature_timeline_m05_fixed_20260820
    without overwriting the interrupted-session outputs

Uses:
  - M05-fixed Step05 compact catalog with exact-position delayed lineage
  - re-pointed signal SIM (37,194 rays) — apply the SAME response chain
    (TES pixel gaussian + threshold + plastic-veto identity pass + BGO veto
     + retained side-entry Step05 + W2 window) — to derive Aeff_W2_final for OptV3
  - 81-bin mission axis (family scales + atmospheric transmission)

Replay:
  - 5 anchors at time_bin_id 0/20/40/60/80, 200,000 s each
  - Total detector-positive rate R(t) computed per anchor from the catalog
  - Exponential inter-arrival times, transitive grouping at coincidence_window (1 μs)
  - Within each group, sum pixel energies (with independent smearing), sum BGO,
    sum plastic (always 0); apply veto + W2 in the SAME way as build_event_catalog
  - Report per-anchor pre-veto/plastic/BGO/combined/topology cps at broad & W2

Then fold the exact isotope inventory, 45-degree atmospheric transmission,
accidental signal survival, and Aeff_W2_final across 81 mission nodes to output
Fmin (3σ/5σ Gaussian and correct Cowan-Asimov forms) with statistical errors.
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
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np


HERE = Path(__file__).resolve()
PACKAGE = HERE.parents[1]                                   # .../DEEPSEEK_CODE
ROOT = Path("/home/ubuntu/.codex/worktrees/e3cf/TES_511_Balloon")
CONFIG = PACKAGE / "modified/analysis_inputs_optv3_B.json"
CATALOG_DIR = PACKAGE / "outputs/04_event_catalog_step05_m05_fixed_20260820"
OUT = PACKAGE / "outputs/05_mature_timeline_m05_fixed_20260820"

sys.path.insert(0, str(HERE.parent))
from step05_side_compton import side_keep_from_hits, side_entry_disk  # noqa: E402

FWHM_KEV = 0.420
SIGMA_KEV = FWHM_KEV / 2.3548200450309493
PIXEL_THRESHOLD_KEV = 0.3

WINDOWS = {
    "broad_480_550": (480.0, 550.0),
    "w2_510p58_511p42": (510.58, 511.42),
}
STAGES = ("pre_veto", "plastic_positron_veto", "bgo_active_scintillator_veto",
          "combined_active_veto", "compton_trajectory_veto")
STAGE_BITS = {s: (1 << i) for i, s in enumerate(STAGES)}

ID_RE = re.compile(r"^ID\s+(\d+)\s+\d+")
TP_RE = re.compile(r"^TP_L(?P<layer>\d+)_(?P<pixel>\d+)$")
CC_HIT_RE = re.compile(
    r"^CC HIT\s+(\S+)\s+edep_keV=([-\deE\.+]+)\s+x=([-\deE\.+]+)\s+y=([-\deE\.+]+)\s+z=([-\deE\.+]+)"
)

SECONDS_PER_DAY = 86_400.0
REFERENCE_FLUX = 1e-4  # ph cm^-2 s^-1 reference
_M05_COMMON: Any | None = None


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def resolve(text: str) -> Path:
    p = Path(text)
    return p if p.is_absolute() else ROOT / p


def m05_common(cfg: dict[str, Any]) -> Any:
    global _M05_COMMON
    if _M05_COMMON is None:
        path = Path(cfg["m05_common_time_code"])
        spec = importlib.util.spec_from_file_location("sh3_optv3_timeline_m05_common", path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot import M05 common-time authority: {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        _M05_COMMON = module
    return _M05_COMMON


def keyed_standard_normal(*keys: Any) -> float:
    payload = "|".join(str(k) for k in keys).encode("utf-8")
    digest = hashlib.blake2b(payload, digest_size=16).digest()
    u1 = int.from_bytes(digest[:8], "little") / 2**64
    u2 = int.from_bytes(digest[8:], "little") / 2**64
    u1 = max(u1, 1e-300)
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def in_window(value: float, bounds: tuple[float, float]) -> bool:
    return bounds[0] <= value < bounds[1]


# ---------------------------------------------------------------------------
# Aeff computation via replay of the 37,194-ray signal SIM
# ---------------------------------------------------------------------------

def compute_signal_aeff(cfg: dict[str, Any]) -> dict[str, Any]:
    """Push the 37,194-ray signal SIM through the same response chain.

    The Step09 EventList has 37,194 photons injected at the Be window with
    energy 511.0 keV.  The optical aperture reference is 20.08476 cm^2.
    Aeff_stage = 20.08476 * N_pass_stage / 37,194  (for each stage and window).
    """
    sim = cfg["signal"]["sim_path"]
    expected_sha = cfg["signal"].get("sim_sha256")
    if expected_sha:
        h = hashlib.sha256()
        with open(sim, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        actual = h.hexdigest()
        if actual != expected_sha:
            raise RuntimeError(f"signal SIM sha mismatch: {sim}\n  expected {expected_sha}\n  actual   {actual}")
    plastic_volumes = set(cfg["active_veto"]["plastic_positron_veto_volumes"])
    bgo_volumes = set(cfg["active_veto"]["bgo_active_scintillator_volumes"])
    threshold = float(cfg["active_veto"]["offline_threshold_keV"])
    disk = build_side_disk(cfg)
    reject_policy = str(cfg["side_entry_disk"].get("reject_policy", "keep"))
    n_input_rays = int(cfg["signal"]["eventlist_rows"])
    A_optical = float(cfg["signal"]["optics_aperture_cm2"])

    stage_counts = {w: {s: 0 for s in STAGES} for w in WINDOWS}
    events = 0
    current_id = None
    pixels: dict[str, dict[str, float]] = {}
    plastic_keV = 0.0
    bgo_keV = 0.0

    def flush():
        nonlocal current_id, pixels, plastic_keV, bgo_keV
        if current_id is None:
            return
        measured_hits = []
        for uid, record in sorted(pixels.items()):
            e = float(record["e"])
            if e <= 0: continue
            noise = SIGMA_KEV * keyed_standard_normal(
                "sh3_optv3_signal", int(current_id), uid,
            )
            m = e + noise
            if m >= PIXEL_THRESHOLD_KEV:
                x = float(record["wx"]) / e
                y = float(record["wy"]) / e
                z = float(record["wz"]) / e
                measured_hits.append(SimpleNamespace(
                    e=m, x=x, y=y, z=z, pixel_uid=uid, layer=int(record["layer"]),
                ))
        total = math.fsum(hit.e for hit in measured_hits)
        plastic_pass = plastic_keV < threshold
        bgo_pass = bgo_keV < threshold
        combined = plastic_pass and bgo_pass
        topo = combined and side_keep_from_hits(measured_hits, disk, reject_policy)[0]
        for w, bounds in WINDOWS.items():
            if not in_window(total, bounds):
                continue
            stage_counts[w]["pre_veto"] += 1
            if plastic_pass: stage_counts[w]["plastic_positron_veto"] += 1
            if bgo_pass:     stage_counts[w]["bgo_active_scintillator_veto"] += 1
            if combined:     stage_counts[w]["combined_active_veto"] += 1
            if topo:         stage_counts[w]["compton_trajectory_veto"] += 1
        current_id = None
        pixels = {}
        plastic_keV = 0.0
        bgo_keV = 0.0

    with gzip.open(sim, "rt") as f:
        for raw in f:
            line = raw.strip()
            if line == "SE":
                flush()
                continue
            m = ID_RE.match(line)
            if m:
                if current_id is not None:
                    raise RuntimeError("ID before boundary in signal SIM")
                current_id = int(m.group(1))
                events += 1
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
                    volume, {"e": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0, "layer": int(pixel_match.group("layer"))}
                )
                record["e"] += edep
                record["wx"] += edep * x; record["wy"] += edep * y; record["wz"] += edep * z
            elif volume in plastic_volumes:
                plastic_keV += edep
            elif volume in bgo_volumes:
                bgo_keV += edep
    flush()

    if events != n_input_rays:
        raise RuntimeError(f"signal SIM events {events} != EventList rows {n_input_rays}")

    result = {
        "input_rays": n_input_rays,
        "optical_aperture_cm2": A_optical,
        "signal_sim_path": sim,
        "stage_counts": stage_counts,
        "aeff_cm2": {},
    }
    for w, per_stage in stage_counts.items():
        result["aeff_cm2"][w] = {
            s: A_optical * n / n_input_rays for s, n in per_stage.items()
        }
    return result


# ---------------------------------------------------------------------------
# Mature Poisson timeline replay
# ---------------------------------------------------------------------------

def load_catalog() -> tuple[dict[str, np.ndarray], list[dict[str, Any]], dict]:
    with np.load(CATALOG_DIR / "combined_event_catalog.npz", allow_pickle=False) as data:
        arrays = {key: data[key] for key in data.files}
    reg = load_json(CATALOG_DIR / "category_registry.json")
    summary = load_json(CATALOG_DIR / "summary.json")
    return arrays, reg["categories"], summary


def build_side_disk(cfg: dict[str, Any]) -> dict[str, Any]:
    sde = cfg["side_entry_disk"]
    return side_entry_disk(
        tuple(float(x) for x in sde["local_center_cm"]),
        float(sde["radius_cm"]),
        float(sde["rotation_y_deg"]),
    )


def category_rates_at_node(
    categories: list[dict[str, Any]], scales_row: dict[str, str],
    inventory_curves: dict[tuple[str, int], np.ndarray],
    inventory_A15: dict[tuple[str, int], float], node_idx: int,
) -> np.ndarray:
    n = len(categories)
    rates = np.zeros(n, dtype=np.float64)
    for i, row in enumerate(categories):
        family = row["family"]
        weight = float(row["base_event_weight_cps"])
        count = int(row["event_count"])
        if row["stream"] == "prompt":
            factor = float(scales_row[f"scale_{family}_to_parma_reference"])
            rates[i] = count * weight * factor
        else:
            key = (family, int(row["source_parent_ZA"]))
            if key not in inventory_curves:
                raise RuntimeError(f"delayed category absent from isotope inventory: {key}")
            factor = inventory_curves[key][node_idx] / inventory_A15[key] if inventory_A15[key] > 0 else 0.0
            rates[i] = count * weight * factor
    return rates


def replay_anchor(
    rng: np.random.Generator, exposure_s: float,
    categories, arrays, cat_rates, cfg,
) -> dict[str, Any]:
    """Replay one anchor with bounded-memory chronological Poisson chunks."""
    total_rate = float(cat_rates.sum())
    if total_rate <= 0:
        raise RuntimeError("total rate is zero at this anchor")
    starts = np.array([c["event_start"] for c in categories], dtype=np.int64)
    counts = np.array([c["event_count"] for c in categories], dtype=np.int64)
    cumulative = np.cumsum(cat_rates / total_rate)
    cumulative[-1] = 1.0
    tau = float(cfg["timeline"]["coincidence_window_s"])
    chunk = int(cfg["timeline"]["chunk_events"])
    side_disk = build_side_disk(cfg)
    reject_policy = str(cfg["side_entry_disk"].get("reject_policy", "keep"))
    state: dict[str, Any] = {
        "groups": 0,
        "multi_groups": 0,
        "multi_groups_with_tes": 0,
        "multi_serial": 0,
        "counts": defaultdict(int),
    }

    def sample_marks(n: int) -> np.ndarray:
        if n <= 0:
            return np.empty(0, dtype=np.int64)
        cats = np.searchsorted(cumulative, rng.random(n), side="right")
        offsets = np.floor(rng.random(n) * counts[cats]).astype(np.int64)
        return starts[cats] + offsets

    def combined_flags(event_indices: np.ndarray) -> tuple[int, int]:
        plastic = float(np.sum(arrays["plastic_keV"][event_indices], dtype=np.float64))
        bgo = float(np.sum(arrays["bgo_keV"][event_indices], dtype=np.float64))
        pixels: dict[int, dict[str, float | int]] = {}
        for event_index in event_indices:
            start = int(arrays["hit_start"][event_index])
            stop = start + int(arrays["hit_count"][event_index])
            for hit_index in range(start, stop):
                code = int(arrays["hit_code"][hit_index])
                energy = float(arrays["hit_energy_keV"][hit_index])
                target = pixels.setdefault(code, {
                    "e": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0,
                    "layer": int(arrays["hit_layer"][hit_index]),
                })
                target["e"] = float(target["e"]) + energy
                target["wx"] = float(target["wx"]) + energy * float(arrays["hit_x_cm"][hit_index])
                target["wy"] = float(target["wy"]) + energy * float(arrays["hit_y_cm"][hit_index])
                target["wz"] = float(target["wz"]) + energy * float(arrays["hit_z_cm"][hit_index])
        measured_hits: list[Any] = []
        seed = int(cfg["timeline"]["seed"])
        serial = int(state["multi_serial"])
        for code, record in sorted(pixels.items()):
            energy = float(record["e"])
            layer = int(record["layer"])
            measured = energy + SIGMA_KEV * keyed_standard_normal(
                "sh3_optv3", "mature_timeline", seed, serial, code
            )
            if measured < PIXEL_THRESHOLD_KEV:
                continue
            measured_hits.append(SimpleNamespace(
                e=measured,
                x=float(record["wx"]) / energy,
                y=float(record["wy"]) / energy,
                z=float(record["wz"]) / energy,
                pixel_uid=f"TP_L{layer}_{code % 100_000}",
                layer=layer,
            ))
        threshold = float(cfg["active_veto"]["offline_threshold_keV"])
        plastic_pass = plastic < threshold
        bgo_pass = bgo < threshold
        combined = plastic_pass and bgo_pass
        total = math.fsum(hit.e for hit in measured_hits)
        topo = combined and side_keep_from_hits(
            measured_hits, side_disk, reject_policy
        )[0]
        output = []
        for bounds in WINDOWS.values():
            flags = 0
            if in_window(total, bounds):
                flags |= STAGE_BITS["pre_veto"]
                if plastic_pass: flags |= STAGE_BITS["plastic_positron_veto"]
                if bgo_pass: flags |= STAGE_BITS["bgo_active_scintillator_veto"]
                if combined: flags |= STAGE_BITS["combined_active_veto"]
                if topo: flags |= STAGE_BITS["compton_trajectory_veto"]
            output.append(flags)
        return int(output[0]), int(output[1])

    def process_groups(event_indices: np.ndarray, group_starts: np.ndarray, group_ends: np.ndarray) -> None:
        if len(group_starts) == 0:
            return
        sizes = group_ends - group_starts
        state["groups"] += int(len(group_starts))
        singles = event_indices[group_starts[sizes == 1]]
        for window, field in (("broad_480_550", "broad_flags"), ("w2_510p58_511p42", "w2_flags")):
            flags = arrays[field][singles]
            for stage, bit in STAGE_BITS.items():
                state["counts"][(window, stage)] += int(np.count_nonzero(flags & bit))
        mask = sizes > 1
        if not np.any(mask):
            return
        multi_starts = group_starts[mask]
        multi_ends = group_ends[mask]
        state["multi_groups"] += int(len(multi_starts))
        tes = (arrays["hit_count"][event_indices] > 0).astype(np.int16)
        cumulative_tes = np.empty(len(tes) + 1, dtype=np.int64)
        cumulative_tes[0] = 0
        np.cumsum(tes, dtype=np.int64, out=cumulative_tes[1:])
        for start, end in zip(multi_starts, multi_ends):
            if cumulative_tes[end] - cumulative_tes[start] <= 0:
                continue
            state["multi_groups_with_tes"] += 1
            broad, w2 = combined_flags(event_indices[start:end])
            state["multi_serial"] += 1
            for window, flags in (("broad_480_550", broad), ("w2_510p58_511p42", w2)):
                for stage, bit in STAGE_BITS.items():
                    if flags & bit:
                        state["counts"][(window, stage)] += 1

    pending = np.empty(0, dtype=np.int64)
    current_time = 0.0
    generated = 0
    finished = False
    while not finished:
        gaps = rng.exponential(1.0 / total_rate, size=chunk)
        times = current_time + np.cumsum(gaps)
        accepted = int(np.searchsorted(times, exposure_s, side="right"))
        if accepted < chunk:
            gaps = gaps[:accepted]
            finished = True
        marks = sample_marks(len(gaps))
        generated += len(marks)
        if len(marks):
            current_time = float(times[len(marks) - 1])
        if len(pending):
            combined = np.concatenate((pending, marks))
            boundaries = np.zeros(len(combined), dtype=bool)
            boundaries[0] = True
            if len(marks):
                offset = len(pending)
                boundaries[offset] = gaps[0] > tau
                if len(marks) > 1:
                    boundaries[offset + 1:] = gaps[1:] > tau
        else:
            combined = marks
            boundaries = np.zeros(len(combined), dtype=bool)
            if len(combined):
                boundaries[0] = True
                if len(combined) > 1:
                    boundaries[1:] = gaps[1:] > tau
        group_starts = np.flatnonzero(boundaries)
        if finished:
            group_ends = np.r_[group_starts[1:], len(combined)].astype(np.int64)
            process_groups(combined, group_starts, group_ends)
            pending = np.empty(0, dtype=np.int64)
        elif len(group_starts):
            process_groups(combined, group_starts[:-1], group_starts[1:])
            pending = combined[group_starts[-1]:].copy()

    result = {
        "expected_arrivals": total_rate * exposure_s,
        "sampled_arrivals": generated,
        "total_rate_cps_at_node": total_rate,
        "n_groups": int(state["groups"]),
        "multi_event_groups": int(state["multi_groups"]),
        "multi_groups_with_tes": int(state["multi_groups_with_tes"]),
        "stage_counts": {
            window: {stage: int(state["counts"][(window, stage)]) for stage in STAGES}
            for window in WINDOWS
        },
    }
    result["stage_rates_cps"] = {
        window: {stage: result["stage_counts"][window][stage] / exposure_s for stage in STAGES}
        for window in WINDOWS
    }
    return result


def signal_probe(
    rng: np.random.Generator, trials: int, categories, arrays, cat_rates, cfg,
) -> dict[str, Any]:
    total_rate = float(np.sum(cat_rates))
    tau = float(cfg["timeline"]["coincidence_window_s"])
    stop_probability = math.exp(-total_rate * tau)
    starts = np.asarray([int(row["event_start"]) for row in categories], dtype=np.int64)
    counts_by_category = np.asarray([int(row["event_count"]) for row in categories], dtype=np.int64)
    cumulative = np.cumsum(cat_rates / total_rate)
    cumulative[-1] = 1.0
    plastic = np.zeros(trials, dtype=np.float32)
    bgo = np.zeros(trials, dtype=np.float32)
    tes_contaminated = np.zeros(trials, dtype=bool)
    neighbors_total = 0
    for _ in range(2):
        neighbor_counts = rng.geometric(stop_probability, size=trials) - 1
        trial_index = np.repeat(np.arange(trials, dtype=np.int64), neighbor_counts)
        cats = np.searchsorted(cumulative, rng.random(len(trial_index)), side="right")
        offsets = np.floor(rng.random(len(trial_index)) * counts_by_category[cats]).astype(np.int64)
        marks = starts[cats] + offsets
        neighbors_total += len(marks)
        if len(marks):
            plastic += np.bincount(trial_index, weights=arrays["plastic_keV"][marks], minlength=trials).astype(np.float32)
            bgo += np.bincount(trial_index, weights=arrays["bgo_keV"][marks], minlength=trials).astype(np.float32)
            contaminated = np.bincount(
                trial_index,
                weights=(arrays["hit_count"][marks] > 0).astype(np.uint8),
                minlength=trials,
            )
            tes_contaminated |= contaminated > 0
    threshold = float(cfg["active_veto"]["offline_threshold_keV"])
    keep = (~tes_contaminated) & (plastic < threshold) & (bgo < threshold)
    passed = int(np.count_nonzero(keep))
    survival = passed / trials
    return {
        "trials": trials,
        "passed": passed,
        "conditional_signal_accidental_survival": survival,
        "binomial_standard_error": math.sqrt(survival * (1.0 - survival) / trials),
        "total_background_rate_cps": total_rate,
        "sampled_neighbor_event_instances": neighbors_total,
        "proxy_boundary": "W2 signal is conservatively lost by any coincident raw-TES background deposit; active-only deposits are summed",
    }


def build_inventory_curves(
    categories, scales_rows, activation_manifest, atm_rows,
) -> tuple[dict, dict]:
    """Build isotope-resolved M05 inventory curves on the retained 81 nodes."""
    common = m05_common(load_json(CONFIG))
    inventory = common.inventory_authority(activation_manifest)
    curves = common.activity_curves(inventory, scales_rows)
    required = {
        (row["family"], int(row["source_parent_ZA"]))
        for row in categories if row["stream"] == "delayed"
    }
    missing = sorted(required - set(inventory))
    if missing:
        raise RuntimeError(f"delayed catalog categories absent from isotope inventory: {missing}")
    return (
        {key: np.asarray(value, dtype=np.float64) for key, value in curves.items()},
        {key: float(value["day15_activity_Bq"]) for key, value in inventory.items()},
    )


def fmin_from(counts_bg: float, signal_per_flux_cm2s: float) -> dict[str, float]:
    """3σ/5σ Gaussian and Poisson-Asimov minimum detectable flux."""
    out = {}
    if signal_per_flux_cm2s <= 0:
        return {"fmin_3sigma_gauss_ph_cm2_s": float("inf"),
                "fmin_3sigma_asimov_ph_cm2_s": float("inf"),
                "fmin_5sigma_gauss_ph_cm2_s": float("inf")}
    # Gaussian: F = k * sqrt(B) / S_per_flux
    for k, label in ((3.0, "3sigma_gauss"), (5.0, "5sigma_gauss")):
        F = k * math.sqrt(max(counts_bg, 0.0)) / signal_per_flux_cm2s
        out[f"fmin_{label}_ph_cm2_s"] = F
    common = m05_common(load_json(CONFIG))
    for k, label in ((3.0, "3sigma"), (5.0, "5sigma")):
        required_signal = common.asimov_required_signal(max(counts_bg, 0.0), k)
        out[f"fmin_{label}_asimov_ph_cm2_s"] = required_signal / signal_per_flux_cm2s
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast-check", action="store_true", help="use exposure=1000s to smoke")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    cfg = load_json(CONFIG)

    # Load mission axes
    scales_rows = sorted(read_csv(resolve(cfg["mission"]["family_scales"])),
                         key=lambda r: int(r["time_bin_id"]))
    atm_rows = sorted(read_csv(resolve(cfg["mission"]["atmospheric_transmission"])),
                      key=lambda r: int(r["time_bin_id"]))
    if len(scales_rows) != 81 or len(atm_rows) != 81:
        raise RuntimeError("expected 81-node mission axis")

    activation_manifest = load_json(Path(cfg["campaigns"]["activation_manifest"]))

    # Signal Aeff
    print("[stage-9] computing signal Aeff via 37,194-ray SIM replay...", flush=True)
    aeff_result = compute_signal_aeff(cfg)

    # Catalog + inventory curves
    print("[stage-9] loading catalog...", flush=True)
    arrays, categories, cat_summary = load_catalog()
    inv_curves, inv_A15 = build_inventory_curves(categories, scales_rows, activation_manifest, atm_rows)

    # Replay 5 anchors
    anchors = list(cfg["timeline"]["anchor_time_bin_ids"])
    exposure = 1000.0 if args.fast_check else float(cfg["timeline"]["exposure_s_per_anchor"])
    seed = int(cfg["timeline"]["seed"])
    trials = 200_000 if args.fast_check else int(cfg["timeline"]["signal_probe_trials_per_anchor"])

    anchor_rows = []
    per_anchor: dict[int, dict[str, Any]] = {}
    category_counts = np.asarray([int(row["event_count"]) for row in categories], dtype=np.int64)
    final_bit = STAGE_BITS["compton_trajectory_veto"]
    final_selected_by_category = np.asarray([
        int(np.count_nonzero(
            arrays["w2_flags"][int(row["event_start"]):int(row["event_start"]) + int(row["event_count"])]
            & final_bit
        ))
        for row in categories
    ], dtype=np.int64)
    for ordinal, a in enumerate(anchors):
        cat_rates = category_rates_at_node(categories, scales_rows[a], inv_curves, inv_A15, a)
        per_event_rate = np.divide(cat_rates, category_counts, out=np.zeros_like(cat_rates), where=category_counts > 0)
        direct_final = float(np.sum(final_selected_by_category * per_event_rate))
        r = replay_anchor(
            np.random.default_rng(np.random.SeedSequence([seed, ordinal, 1])),
            exposure, categories, arrays, cat_rates, cfg,
        )
        signal = signal_probe(
            np.random.default_rng(np.random.SeedSequence([seed, ordinal, 2])),
            trials, categories, arrays, cat_rates, cfg,
        )
        r["anchor_node"] = a
        final_count = int(r["stage_counts"]["w2_510p58_511p42"]["compton_trajectory_veto"])
        timeline_rate = final_count / exposure
        ratio = timeline_rate / direct_final if direct_final > 0.0 else float("nan")
        ratio_se = math.sqrt(final_count) / exposure / direct_final if direct_final > 0.0 and final_count > 0 else float("inf")
        per_anchor[a] = {
            "timeline": r,
            "signal_probe": signal,
            "direct_w2_final_cps": direct_final,
            "timeline_to_direct_ratio": ratio,
            "timeline_to_direct_ratio_standard_error": ratio_se,
        }
        for w in WINDOWS:
            for s in STAGES:
                anchor_rows.append({
                    "anchor_node": a,
                    "day_mid": float(scales_rows[a]["day_mid"]),
                    "window_id": w, "stage": s,
                    "count": int(r["stage_counts"][w][s]),
                    "rate_cps": float(r["stage_rates_cps"][w][s]),
                    "direct_w2_final_cps": direct_final if w == "w2_510p58_511p42" and s == "compton_trajectory_veto" else "",
                    "timeline_to_direct_ratio": ratio if w == "w2_510p58_511p42" and s == "compton_trajectory_veto" else "",
                    "signal_accidental_survival": signal["conditional_signal_accidental_survival"] if w == "w2_510p58_511p42" and s == "compton_trajectory_veto" else "",
                })
        print(json.dumps({"anchor_node": a, "day_mid": float(scales_rows[a]["day_mid"]),
                          "total_rate_cps": r["total_rate_cps_at_node"],
                          "n_groups": r["n_groups"],
                          "multi_event_groups": r["multi_event_groups"],
                          "w2_pre_veto_cps": r["stage_rates_cps"]["w2_510p58_511p42"]["pre_veto"],
                          "w2_final_cps": timeline_rate,
                          "direct_w2_final_cps": direct_final,
                          "timeline_to_direct_ratio": ratio,
                          "signal_survival": signal["conditional_signal_accidental_survival"]},
                         indent=None), flush=True)

    with (OUT / "anchor_timeline_rates.csv").open("w", encoding="utf-8", newline="") as h:
        w = csv.DictWriter(h, fieldnames=list(anchor_rows[0]), lineterminator="\n")
        w.writeheader(); w.writerows(anchor_rows)

    # Mission fold: exact 81-node source/inventory rates, with the five-anchor
    # common-time correction and signal-survival probes interpolated on that axis.
    duration_days = float(cfg["mission"]["duration_days"])
    if not math.isclose(float(scales_rows[-1]["day_mid"]), duration_days, abs_tol=1e-12):
        raise RuntimeError("81-node mission axis does not end at configured duration")
    anchor_nodes = np.asarray(anchors, dtype=float)
    anchor_ratios = np.asarray([per_anchor[a]["timeline_to_direct_ratio"] for a in anchors], dtype=float)
    anchor_ratio_se = np.asarray([per_anchor[a]["timeline_to_direct_ratio_standard_error"] for a in anchors], dtype=float)
    anchor_survivals = np.asarray([
        per_anchor[a]["signal_probe"]["conditional_signal_accidental_survival"] for a in anchors
    ], dtype=float)
    anchor_survival_se = np.asarray([
        per_anchor[a]["signal_probe"]["binomial_standard_error"] for a in anchors
    ], dtype=float)
    aeff_final = aeff_result["aeff_cm2"]["w2_510p58_511p42"]["compton_trajectory_veto"]
    slant = 1.0 / math.sin(math.radians(float(cfg["mission"]["source_elevation_deg"])))
    mission_rows: list[dict[str, Any]] = []
    integrated_bg_counts = 0.0
    signal_per_flux = 0.0
    integrated_weight_by_category = np.zeros(len(categories), dtype=np.float64)
    previous: tuple[float, float, float] | None = None
    previous_weights: np.ndarray | None = None
    direct_by_node = np.zeros(81, dtype=np.float64)
    transmission_by_node = np.zeros(81, dtype=np.float64)
    for node in range(81):
        cat_rates = category_rates_at_node(categories, scales_rows[node], inv_curves, inv_A15, node)
        per_event_rate = np.divide(cat_rates, category_counts, out=np.zeros_like(cat_rates), where=category_counts > 0)
        direct = float(np.sum(final_selected_by_category * per_event_rate))
        ratio = float(np.interp(node, anchor_nodes, anchor_ratios))
        survival = float(np.interp(node, anchor_nodes, anchor_survivals))
        background = direct * ratio
        transmission = float(atm_rows[node]["T_atm_511"]) ** slant
        kernel = aeff_final * transmission * survival
        corrected_weights = per_event_rate * ratio
        day = float(scales_rows[node]["day_mid"])
        direct_by_node[node] = direct
        transmission_by_node[node] = transmission
        if previous is not None:
            dt = (day - previous[0]) * SECONDS_PER_DAY
            integrated_bg_counts += 0.5 * (previous[1] + background) * dt
            signal_per_flux += 0.5 * (previous[2] + kernel) * dt
            if previous_weights is None:
                raise RuntimeError("missing previous category weights")
            integrated_weight_by_category += 0.5 * (previous_weights + corrected_weights) * dt
        mission_rows.append({
            "time_bin_id": node,
            "day_mid": day,
            "direct_w2_final_no_coincidence_cps": direct,
            "interpolated_background_timeline_ratio": ratio,
            "mature_background_w2_final_cps": background,
            "conditional_signal_accidental_survival": survival,
            "T_atm_511_slant45": transmission,
            "conditional_signal_Aeff_cm2": aeff_final,
            "conditional_signal_kernel_cm2": kernel,
            "cumulative_background_counts": integrated_bg_counts,
            "cumulative_signal_counts_per_unit_flux": signal_per_flux,
        })
        previous = (day, background, kernel)
        previous_weights = corrected_weights

    transport_background = float(np.sum(final_selected_by_category * integrated_weight_by_category))
    transport_variance = float(np.sum(final_selected_by_category * integrated_weight_by_category**2))
    transport_sigma = math.sqrt(transport_variance)
    if not math.isclose(transport_background, integrated_bg_counts, rel_tol=2e-12, abs_tol=1e-6):
        raise RuntimeError(f"mission category-weight closure differs: {transport_background} vs {integrated_bg_counts}")

    # The mission integral is linear in each anchor ratio/survival.  Build the
    # exact interpolation coefficients and propagate independent replay/probe
    # counting errors.
    days = np.asarray([float(row["day_mid"]) for row in scales_rows], dtype=float)
    trapz = getattr(np, "trapezoid", None) or np.trapz
    ratio_coefficients = []
    survival_coefficients = []
    for anchor_index in range(len(anchors)):
        basis = np.zeros(len(anchors), dtype=float)
        basis[anchor_index] = 1.0
        interpolated = np.interp(np.arange(81), anchor_nodes, basis)
        ratio_coefficients.append(float(trapz(direct_by_node * interpolated, days) * SECONDS_PER_DAY))
        survival_coefficients.append(float(trapz(aeff_final * transmission_by_node * interpolated, days) * SECONDS_PER_DAY))
    ratio_coefficients = np.asarray(ratio_coefficients)
    survival_coefficients = np.asarray(survival_coefficients)
    timeline_sigma = float(np.sqrt(np.sum((ratio_coefficients * anchor_ratio_se) ** 2)))
    signal_probe_sigma = float(np.sqrt(np.sum((survival_coefficients * anchor_survival_se) ** 2)))
    signal_count = int(aeff_result["stage_counts"]["w2_510p58_511p42"]["compton_trajectory_veto"])
    signal_trials = int(aeff_result["input_rays"])
    signal_p = signal_count / signal_trials
    aeff_sigma = float(aeff_result["optical_aperture_cm2"] * math.sqrt(signal_p * (1.0 - signal_p) / signal_trials))
    aeff_relative_sigma = aeff_sigma / aeff_final
    signal_relative_sigma = math.sqrt(
        aeff_relative_sigma**2 + (signal_probe_sigma / signal_per_flux) ** 2
    )
    background_sigma = math.sqrt(transport_sigma**2 + timeline_sigma**2)
    background_relative_sigma = background_sigma / integrated_bg_counts

    fmin = fmin_from(integrated_bg_counts, signal_per_flux)
    fmin_relative_sigma = math.sqrt((0.5 * background_relative_sigma) ** 2 + signal_relative_sigma**2)
    fmin_gauss_sigma = fmin["fmin_3sigma_gauss_ph_cm2_s"] * fmin_relative_sigma
    for row in mission_rows:
        b = float(row["cumulative_background_counts"])
        k = float(row["cumulative_signal_counts_per_unit_flux"])
        if k > 0.0:
            row.update(fmin_from(b, k))
        else:
            row.update({
                "fmin_3sigma_gauss_ph_cm2_s": "",
                "fmin_5sigma_gauss_ph_cm2_s": "",
                "fmin_3sigma_asimov_ph_cm2_s": "",
                "fmin_5sigma_asimov_ph_cm2_s": "",
            })

    with (OUT / "mission_timeline_81nodes.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(mission_rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(mission_rows)

    summary = {
        "status": "PASS__SH3_OPTV3_M05_FIXED_MATURE_TIMELINE_20D",
        "candidate": cfg["candidate"],
        "exposure_s_per_anchor": exposure,
        "n_anchors": len(anchors),
        "duration_days": duration_days,
        "signal_aeff": aeff_result,
        "aeff_w2_final_cm2": aeff_final,
        "integrated_background_counts_20d": integrated_bg_counts,
        "signal_counts_per_flux_cm2_s": signal_per_flux,
        "fmin_ph_cm2_s": fmin,
        "fmin_3sigma_gaussian_standard_error_ph_cm2_s": fmin_gauss_sigma,
        "fmin_3sigma_gaussian_relative_standard_error": fmin_relative_sigma,
        "statistical_uncertainty": {
            "background_transport_MC_sigma_counts": transport_sigma,
            "background_transport_MC_relative_sigma": transport_sigma / integrated_bg_counts,
            "background_timeline_replay_sigma_counts": timeline_sigma,
            "background_timeline_replay_relative_sigma": timeline_sigma / integrated_bg_counts,
            "background_combined_sigma_counts": background_sigma,
            "background_combined_relative_sigma": background_relative_sigma,
            "weighted_effective_transport_survivors": integrated_bg_counts**2 / transport_variance if transport_variance > 0 else float("inf"),
            "signal_Aeff_sigma_cm2": aeff_sigma,
            "signal_Aeff_relative_sigma": aeff_relative_sigma,
            "signal_accidental_probe_sigma_counts_per_unit_flux": signal_probe_sigma,
            "signal_accidental_probe_relative_sigma": signal_probe_sigma / signal_per_flux,
            "signal_combined_relative_sigma": signal_relative_sigma,
            "fmin_3sigma_gaussian_relative_sigma": fmin_relative_sigma,
            "model": "delta-method propagation; transport-template Poisson, anchor replay Poisson, signal Aeff binomial, and accidental-probe binomial terms treated as independent",
        },
        "per_anchor": {str(a): per_anchor[a] for a in anchors},
        "mission_final_20day": mission_rows[-1],
        "notes": [
            "MODIFIED 2026-08-19 option B + real Step05: signal SIM re-pointed to chimney focal plane z=-2.8.",
            "COMPTON/FOV = real side-entry rule (port of build_v3p5_centerfinger_step05_l1_response.py):",
            "  2-hit dual-order back-projected cone vs side disk; 3-6 hit CSR enumeration; >6 hit reject_kept.",
            "Side disk: local (-46.0, 0, -2.8), r=1.9 cm, rot_y=45 deg.",
            "Background catalog uses catalog_schema=step05_exactpos_v2; round005 is excluded for canary seed reuse.",
            "PLASTIC veto = IDENTITY_PASS (OptV3 has no plastic layer); plastic_pass always True.",
            "BGO veto threshold = 50 keV offline; native trigger 80 keV.",
            "Delayed lineage is exact-position resolved and mission activity is isotope-specific A_(family,ZA)(t).",
            "Signal kernel includes 45-degree slant atmospheric transmission and common-time accidental survival.",
            "Statistical error excludes response/geometry/atmosphere/model systematics.",
        ],
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "aeff_w2_final_cm2": aeff_final,
        "integrated_bg_counts_20d": integrated_bg_counts,
        "signal_counts_per_unit_flux": signal_per_flux,
        "fmin_ph_cm2_s": fmin,
        "fmin_3sigma_gaussian_standard_error": fmin_gauss_sigma,
        "fmin_3sigma_gaussian_relative_standard_error": fmin_relative_sigma,
    }, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
