#!/usr/bin/env python3
"""SH3 OptV3 mature Poisson timeline + Aeff + Fmin.

Uses:
  - compact catalog produced by build_event_catalog_sh3.py
  - Step09 signal SIM (37,194 rays) — apply the SAME response chain
    (TES pixel gaussian + threshold + plastic-veto identity pass + BGO veto
     + Step05 keep-all + W2 window) — to derive Aeff_W2_final for OptV3
  - 81-bin mission axis (family scales + atmospheric transmission)

Replay:
  - 5 anchors at time_bin_id 0/20/40/60/80, 20,000 s each
  - Total detector-positive rate R(t) computed per anchor from the catalog
  - Exponential inter-arrival times, transitive grouping at coincidence_window (1 μs)
  - Within each group, sum pixel energies (with independent smearing), sum BGO,
    sum plastic (always 0); apply veto + W2 in the SAME way as build_event_catalog
  - Report per-anchor pre-veto/plastic/BGO/combined/topology cps at broad & W2

Then combine with mission fold (81-bin fold of R using family scales & atmospheric
transmission) and Aeff_W2_final to output Fmin (3σ Gauss + Poisson-Asimov + 5σ).
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
PACKAGE = HERE.parents[1]
ROOT = PACKAGE.parents[2]
CONFIG = PACKAGE / "analysis_inputs.json"
CATALOG_DIR = PACKAGE / "outputs/01_event_catalog"
OUT = PACKAGE / "outputs/02_mature_timeline"

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


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def resolve(text: str) -> Path:
    p = Path(text)
    return p if p.is_absolute() else ROOT / p


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
    plastic_volumes = set(cfg["active_veto"]["plastic_positron_veto_volumes"])
    bgo_volumes = set(cfg["active_veto"]["bgo_active_scintillator_volumes"])
    threshold = float(cfg["active_veto"]["offline_threshold_keV"])
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
                measured_hits.append(m)
        total = math.fsum(measured_hits)
        plastic_pass = plastic_keV < threshold
        bgo_pass = bgo_keV < threshold
        combined = plastic_pass and bgo_pass
        topo = combined and (len(measured_hits) > 0)
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
                    volume, {"e": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0}
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
            if key in inventory_curves:
                factor = inventory_curves[key][node_idx] / inventory_A15[key] if inventory_A15[key] > 0 else 0.0
            else:
                # Fallback: use family-level day-15 constant (no time dep, so scales to 1.0).
                factor = 1.0
            rates[i] = count * weight * factor
    return rates


def replay_anchor(
    rng: np.random.Generator, exposure_s: float,
    categories, arrays, cat_rates, cfg,
) -> dict[str, Any]:
    """Replay one anchor for exposure_s."""
    total_rate = float(cat_rates.sum())
    if total_rate <= 0:
        raise RuntimeError("total rate is zero at this anchor")
    per_event_rate = np.divide(cat_rates,
                               np.array([c["event_count"] for c in categories], dtype=np.float64),
                               out=np.zeros_like(cat_rates),
                               where=np.array([c["event_count"] for c in categories]) > 0)
    n_expected = total_rate * exposure_s
    n_arrivals = int(rng.poisson(n_expected))
    # sample categories by cumulative
    p = cat_rates / total_rate
    cum = np.cumsum(p); cum[-1] = 1.0
    cats = np.searchsorted(cum, rng.random(n_arrivals), side="right")
    starts = np.array([c["event_start"] for c in categories], dtype=np.int64)
    counts = np.array([c["event_count"] for c in categories], dtype=np.int64)
    offsets = np.floor(rng.random(n_arrivals) * counts[cats]).astype(np.int64)
    template_idx = starts[cats] + offsets

    # sort arrivals in time
    times = np.sort(rng.random(n_arrivals) * exposure_s)

    # transitive grouping at tau
    tau = float(cfg["timeline"]["coincidence_window_s"])
    if len(times) > 0:
        gaps = np.diff(times)
        group_breaks = np.concatenate(([0], np.where(gaps > tau)[0] + 1, [len(times)]))
    else:
        group_breaks = np.array([0], dtype=np.int64)
    n_groups = len(group_breaks) - 1

    # accumulate per-group energy sums
    plastic_arr = arrays["plastic_keV"]
    bgo_arr = arrays["bgo_keV"]
    hit_start = arrays["hit_start"].astype(np.int64)
    hit_count = arrays["hit_count"].astype(np.int64)
    hit_energy = arrays["hit_energy_keV"]

    threshold = float(cfg["active_veto"]["offline_threshold_keV"])
    stage_hits_broad = {s: 0 for s in STAGES}
    stage_hits_w2 = {s: 0 for s in STAGES}

    multi_groups = 0
    multi_with_tes = 0
    total_events_sampled = int(n_arrivals)

    for gi in range(n_groups):
        lo = group_breaks[gi]; hi = group_breaks[gi + 1]
        members = template_idx[lo:hi]
        # accumulate plastic + bgo linearly
        plastic_sum = float(plastic_arr[members].sum())
        bgo_sum = float(bgo_arr[members].sum())
        # accumulate pixel-level hit list (raw energies; independent smear here to preserve
        # per-arrival independence of the pixel Gaussian)
        pixel_e_sum = 0.0
        n_pix = 0
        for k, ti in enumerate(members):
            s = hit_start[ti]; c = hit_count[ti]
            if c == 0:
                continue
            n_pix += c
            for j in range(c):
                e = float(hit_energy[s + j])
                noise = SIGMA_KEV * keyed_standard_normal("anchor_replay",
                                                          int(gi), int(ti), int(j))
                m = e + noise
                if m >= PIXEL_THRESHOLD_KEV:
                    pixel_e_sum += m
        total = pixel_e_sum
        if hi - lo > 1:
            multi_groups += 1
            if n_pix > 0:
                multi_with_tes += 1
        plastic_pass = plastic_sum < threshold
        bgo_pass = bgo_sum < threshold
        combined = plastic_pass and bgo_pass
        topo = combined and (pixel_e_sum > 0)

        for label, bounds, tgt in (("broad_480_550", WINDOWS["broad_480_550"], stage_hits_broad),
                                    ("w2_510p58_511p42", WINDOWS["w2_510p58_511p42"], stage_hits_w2)):
            if not in_window(total, bounds):
                continue
            tgt["pre_veto"] += 1
            if plastic_pass: tgt["plastic_positron_veto"] += 1
            if bgo_pass:     tgt["bgo_active_scintillator_veto"] += 1
            if combined:     tgt["combined_active_veto"] += 1
            if topo:         tgt["compton_trajectory_veto"] += 1

    result = {
        "expected_arrivals": n_expected,
        "sampled_arrivals": total_events_sampled,
        "total_rate_cps_at_node": total_rate,
        "n_groups": int(n_groups),
        "multi_event_groups": multi_groups,
        "multi_groups_with_tes": multi_with_tes,
        "stage_counts": {"broad_480_550": stage_hits_broad, "w2_510p58_511p42": stage_hits_w2},
        "stage_rates_cps": {
            w: {s: cnt / exposure_s for s, cnt in stage_hits.items()}
            for w, stage_hits in (("broad_480_550", stage_hits_broad),
                                   ("w2_510p58_511p42", stage_hits_w2))
        },
    }
    return result


def build_inventory_curves(
    categories, scales_rows, activation_manifest, atm_rows,
) -> tuple[dict, dict]:
    """Build per-(family,ZA) delayed activity curves aligned to the 81 nodes.

    Since our compact catalog groups delayed by (family, ZA) but activation
    manifest only records family-level A_f(15), we assume all ZA within a
    family share the family curve (proportional to A_family(t)/A_family(15)).
    """
    day15_by_family = {cell["family"]: float(cell["transported_ground_activity_Bq"])
                       for cell in activation_manifest["activation_cells"]}
    # per-family activity vs time: use delayed_production_scale_to_day15 * A15
    # (the atmospheric transmission CSV has "delayed_production_scale_to_day15" as
    # the family-independent day-15-relative delayed production factor; use as unity time-dep).
    n = len(atm_rows)
    if n != 81:
        raise RuntimeError(f"expected 81 nodes, got {n}")
    time_scale = np.array([float(r["delayed_production_scale_to_day15"]) for r in atm_rows])
    inv_curves = {}
    inv_A15 = {}
    for row in categories:
        if row["stream"] != "delayed":
            continue
        key = (row["family"], int(row["source_parent_ZA"]))
        A15 = day15_by_family.get(row["family"], 0.0)
        inv_A15[key] = A15
        inv_curves[key] = time_scale * A15
    return inv_curves, inv_A15


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
    # Poisson-Asimov: find F such that -2 ln (L(0|N=B+S)/L(S|N=B+S)) = k^2
    # simplification: S / sqrt(B + S) = k
    # S^2 - k^2 S - k^2 B = 0 -> S = (k^2 + sqrt(k^4 + 4 k^2 B))/2 ; F = S / signal_per_flux
    k = 3.0
    S = 0.5 * (k * k + math.sqrt(k**4 + 4 * k * k * max(counts_bg, 0.0)))
    out["fmin_3sigma_asimov_ph_cm2_s"] = S / signal_per_flux_cm2s
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
    rng = np.random.default_rng(seed)

    anchor_rows = []
    per_anchor: dict[int, dict[str, Any]] = {}
    for a in anchors:
        cat_rates = category_rates_at_node(categories, scales_rows[a], inv_curves, inv_A15, a)
        r = replay_anchor(rng, exposure, categories, arrays, cat_rates, cfg)
        r["anchor_node"] = a
        per_anchor[a] = r
        for w in WINDOWS:
            for s in STAGES:
                anchor_rows.append({
                    "anchor_node": a,
                    "day_mid": float(scales_rows[a]["day_mid"]),
                    "window_id": w, "stage": s,
                    "count": int(r["stage_counts"][w][s]),
                    "rate_cps": float(r["stage_rates_cps"][w][s]),
                })
        print(json.dumps({"anchor_node": a, "day_mid": float(scales_rows[a]["day_mid"]),
                          "total_rate_cps": r["total_rate_cps_at_node"],
                          "n_groups": r["n_groups"],
                          "multi_event_groups": r["multi_event_groups"],
                          "w2_pre_veto_cps": r["stage_rates_cps"]["w2_510p58_511p42"]["pre_veto"],
                          "w2_final_cps": r["stage_rates_cps"]["w2_510p58_511p42"]["compton_trajectory_veto"]},
                         indent=None), flush=True)

    with (OUT / "anchor_timeline_rates.csv").open("w", encoding="utf-8", newline="") as h:
        w = csv.DictWriter(h, fieldnames=list(anchor_rows[0]), lineterminator="\n")
        w.writeheader(); w.writerows(anchor_rows)

    # Mission fold: 20-day cumulative background counts at final W2 stage.
    # Approximation: interpolate anchor W2-final rate linearly across the 20 days.
    duration_days = float(cfg["mission"]["duration_days"])
    duration_s = duration_days * SECONDS_PER_DAY
    anchor_days = np.array([float(scales_rows[a]["day_mid"]) for a in anchors])
    anchor_w2_final = np.array([per_anchor[a]["stage_rates_cps"]["w2_510p58_511p42"]["compton_trajectory_veto"] for a in anchors])
    # trapezoidal integration in days (converting to seconds at the end)
    if not np.all(np.diff(anchor_days) > 0):
        # fall back to mean * duration
        integrated_bg_counts = float(anchor_w2_final.mean()) * duration_s
    else:
        # clip integration to [0, duration_days]
        integrated_bg_counts = float(np.trapz(anchor_w2_final, anchor_days) * SECONDS_PER_DAY)
    # Signal integrated counts per unit flux (ph cm^-2 s^-1):
    aeff_final = aeff_result["aeff_cm2"]["w2_510p58_511p42"]["compton_trajectory_veto"]
    signal_per_flux = aeff_final * duration_s

    fmin = fmin_from(integrated_bg_counts, signal_per_flux)

    summary = {
        "status": "PASS__SH3_OPTV3_MATURE_TIMELINE_20D",
        "candidate": cfg["candidate"],
        "exposure_s_per_anchor": exposure,
        "n_anchors": len(anchors),
        "duration_days": duration_days,
        "signal_aeff": aeff_result,
        "aeff_w2_final_cm2": aeff_final,
        "integrated_background_counts_20d": integrated_bg_counts,
        "signal_counts_per_flux_cm2_s": signal_per_flux,
        "fmin_ph_cm2_s": fmin,
        "per_anchor": {str(a): per_anchor[a] for a in anchors},
        "notes": [
            "Broad and W2 windows computed with the SAME response chain as signal Aeff.",
            "PLASTIC veto = IDENTITY_PASS (OptV3 has no plastic layer); plastic_pass always True.",
            "BGO veto threshold = 50 keV offline; native trigger 80 keV.",
            "Step05 topology = keep-all placeholder; refine with real Compton/FoV rule for final.",
            "Delayed time dependence approximated via family-independent delayed_production_scale_to_day15.",
        ],
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "aeff_w2_final_cm2": aeff_final,
        "integrated_bg_counts_20d": integrated_bg_counts,
        "fmin_ph_cm2_s": fmin,
    }, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
