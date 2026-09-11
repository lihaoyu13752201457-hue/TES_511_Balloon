#!/usr/bin/env python3
"""Add-on detector design optimization screen for COSMOSRAY_BG_2605.

This script is intentionally external to the validated production chain.  It
reads the frozen event catalog and report ledgers, writes only compact derived
tables/figures, and does not modify source, geometry, or legacy analysis code.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import pickle
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

os.environ.setdefault("MPLCONFIGDIR", "/tmp/codex_tes_511_matplotlib")

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
OUT_ROOT_DEFAULT = ROOT / "reports2.0" / "08_DESIGN_OPTIMIZATION_ADDON"
CATALOG_DEFAULT = ROOT / "reports" / "day15_complete_report" / "work" / "event_catalog.pkl"
SUMMARY_DEFAULT = ROOT / "reports" / "day15_complete_report" / "complete_day15_summary.json"
LINEAGE_DEFAULT = ROOT / "reports2.0" / "07_NIMA_MANUSCRIPT" / "final_numerical_lineage.csv"
FOCUSED_DEFAULT = ROOT / "reports2.0" / "03_NEXT_PHASE_SUPPORT" / "optics_focused_gamma_background" / "focused_gamma_background_summary.csv"
ACTIVATION_GEOM_DEFAULT = ROOT / "reports2.0" / "03_NEXT_PHASE_SUPPORT" / "activation_rpip_sampling" / "activation_geometry_volume_summary.csv"
TIMING_SCAN_DEFAULT = ROOT / "reports2.0" / "03_NEXT_PHASE_SUPPORT" / "timing_window_scan" / "timing_window_scan_summary.csv"

BROAD = (480.0, 550.0, "broad_480_550")
LINE = (510.3, 511.8, "line_510p3_511p8")
REFERENCE_FLUX = 1.0e-4
OBS_TIME_S = 1.0e6
F0_BEST_3SIGMA = 1.4057184857392213e-4
TARGET_FLUX = 1.0e-4


@dataclass(frozen=True)
class Variant:
    variant_id: str
    bgo_threshold_keV: float
    roi_radius: float | None
    edge_reject: bool
    single_pixel_only: bool
    layer_mask: str
    compton_policy: str


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="", errors="ignore") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys: list[str] = []
        for row in rows:
            for key in row:
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def fmt(x: float, nd: int = 6) -> str:
    if not np.isfinite(x):
        return "nan"
    if x == 0:
        return "0"
    if abs(x) < 1.0e-3 or abs(x) >= 1.0e4:
        return f"{x:.{nd}e}"
    return f"{x:.{nd}g}"


def csv_float(row: dict, key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def normal_survival(z: float) -> float:
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def p3_from_f3(f3: float, flux: float = TARGET_FLUX) -> float:
    if not np.isfinite(f3) or f3 <= 0:
        return float("nan")
    mean_z = 3.0 * flux / f3
    return normal_survival(3.0 - mean_z)


def load_baseline(summary_path: Path, lineage_path: Path, focused_path: Path) -> dict:
    summary = read_json(summary_path)
    by_stream = summary.get("expectation_rates_by_stream_cps", {})
    prompt = float(by_stream.get("prompt", {}).get("final", 1.403721701401853))
    delayed = float(by_stream.get("delayed", {}).get("final", 4.367574483641229))
    science_final = float(by_stream.get("science", {}).get("final", 0.0024858993900839696))
    response = science_final / float(summary.get("normalization", {}).get("science_flux_ph_cm2_s", REFERENCE_FLUX))

    lineage = read_csv(lineage_path)
    lineage_map = {r.get("quantity", ""): r for r in lineage}
    if "background-only 480-550" in lineage_map:
        broad_b = csv_float(lineage_map["background-only 480-550"], "value", prompt + delayed)
    else:
        broad_b = prompt + delayed
    if "corrected science response" in lineage_map:
        response = csv_float(lineage_map["corrected science response"], "value", response)
    if "broad ERL profiled 3sigma / 1 Ms" in lineage_map:
        f0_best = csv_float(lineage_map["broad ERL profiled 3sigma / 1 Ms"], "value", F0_BEST_3SIGMA)
    else:
        f0_best = F0_BEST_3SIGMA

    focused_broad = 0.0
    focused_line = 0.0
    for row in read_csv(focused_path):
        if row.get("window") == "broad_480_550":
            focused_broad = csv_float(row, "mean_final_focused_gamma_cps", 0.0)
        elif row.get("window") == "line_510p3_511p8":
            focused_line = csv_float(row, "mean_final_focused_gamma_cps", 0.0)

    return {
        "prompt_broad_final_cps": prompt,
        "delayed_broad_final_cps": delayed,
        "focused_broad_final_cps": focused_broad,
        "background_broad_final_cps": broad_b,
        "science_final_at_reference_flux_cps": science_final,
        "science_response_cps_per_flux": response,
        "f0_best_3sigma_1Ms": f0_best,
        "focused_line_final_cps": focused_line,
        "q0": response / math.sqrt(max(broad_b, 1.0e-300)),
    }


def import_complete_module():
    if str(TOOLS) not in sys.path:
        sys.path.insert(0, str(TOOLS))
    import make_complete_day15_report as complete

    return complete


def load_catalog(path: Path) -> dict:
    with path.open("rb") as fh:
        return pickle.load(fh)


def candidate_indices(cat: dict, window: tuple[float, float, str] = BROAD) -> np.ndarray:
    lo, hi, _ = window
    e = np.asarray(cat["tes_total_keV"], dtype=float)
    return np.flatnonzero((e >= lo) & (e < hi))


def lowstat_sample(cat: dict, indices: np.ndarray, max_per_stream: int, seed: int) -> tuple[np.ndarray, np.ndarray, dict]:
    rng = np.random.default_rng(seed)
    streams = np.asarray(cat["stream"]).astype(str)
    chosen: list[np.ndarray] = []
    factors: list[np.ndarray] = []
    info: dict[str, dict] = {}
    for stream in ("prompt", "delayed", "science"):
        idx = indices[streams[indices] == stream]
        n = int(len(idx))
        if n == 0:
            continue
        if n > max_per_stream:
            pick = np.sort(rng.choice(idx, size=max_per_stream, replace=False))
            factor = n / float(max_per_stream)
        else:
            pick = np.sort(idx)
            factor = 1.0
        chosen.append(pick)
        factors.append(np.full(len(pick), factor, dtype=float))
        info[stream] = {"candidate_events": n, "sampled_events": int(len(pick)), "rate_weight_factor": factor}
    if not chosen:
        return np.asarray([], dtype=np.int64), np.asarray([], dtype=float), info
    sample = np.concatenate(chosen)
    weights = np.concatenate(factors)
    order = np.argsort(sample)
    return sample[order], weights[order], info


def build_features(cat: dict, indices: np.ndarray, rate_scale: np.ndarray | None, label: str, progress_every: int = 5000) -> dict:
    complete = import_complete_module()
    n = len(indices)
    if rate_scale is None:
        rate_scale = np.ones(n, dtype=float)
    rate = np.asarray(cat["rate_hz"], dtype=float)[indices] * np.asarray(rate_scale, dtype=float)
    stream = np.asarray(cat["stream"])[indices].astype(str)
    tag = np.asarray(cat["tag"])[indices].astype(str)
    tes_e = np.asarray(cat["tes_total_keV"], dtype=float)[indices]
    bgo = np.asarray(cat["bgo_total_keV"], dtype=float)[indices]
    pix_count = np.asarray(cat["pix_count"], dtype=np.int32)[indices]

    centroid_r = np.full(n, np.nan, dtype=float)
    max_r = np.full(n, np.nan, dtype=float)
    dominant_layer = np.full(n, -1, dtype=np.int16)
    min_layer = np.full(n, -1, dtype=np.int16)
    max_layer = np.full(n, -1, dtype=np.int16)
    n_layers = np.zeros(n, dtype=np.int16)
    compton_raw = np.empty(n, dtype=object)
    single_pixel = pix_count == 1

    pix_start_all = np.asarray(cat["pix_start"], dtype=np.int64)
    pix_e_all = np.asarray(cat["pix_e"], dtype=float)
    pix_x_all = np.asarray(cat["pix_x"], dtype=float)
    pix_y_all = np.asarray(cat["pix_y"], dtype=float)
    pix_layer_all = np.asarray(cat["pix_layer"], dtype=np.int16)

    for k, idx in enumerate(indices):
        s = int(pix_start_all[idx])
        c = int(pix_count[k])
        if c <= 0:
            compton_raw[k] = "no_tes"
            continue
        sl = slice(s, s + c)
        pe = pix_e_all[sl]
        px = pix_x_all[sl]
        py = pix_y_all[sl]
        layers = pix_layer_all[sl]
        total = float(np.sum(pe))
        if total > 0:
            cx = float(np.sum(pe * px) / total)
            cy = float(np.sum(pe * py) / total)
            centroid_r[k] = math.hypot(cx, cy)
            rr = np.sqrt(px * px + py * py)
            max_r[k] = float(np.max(rr))
            dominant_layer[k] = int(layers[int(np.argmax(pe))])
            min_layer[k] = int(np.min(layers))
            max_layer[k] = int(np.max(layers))
            n_layers[k] = int(len(np.unique(layers)))
        if c == 1:
            compton_raw[k] = "single"
        else:
            hits = complete.event_hits(cat, int(idx))
            compton_raw[k] = complete.classify_compton(hits, "drop")
        if progress_every and (k + 1) % progress_every == 0:
            print(f"[{label}] feature/class cache {k + 1}/{n}", flush=True)

    return {
        "indices": indices,
        "rate_hz": rate,
        "stream": stream,
        "tag": tag,
        "tes_total_keV": tes_e,
        "bgo_total_keV": bgo,
        "pix_count": pix_count,
        "single_pixel": single_pixel,
        "centroid_r_mm": centroid_r,
        "max_r_mm": max_r,
        "dominant_layer": dominant_layer,
        "min_layer": min_layer,
        "max_layer": max_layer,
        "n_layers": n_layers,
        "compton_raw": compton_raw.astype(str),
    }


def layer_mask_bool(features: dict, name: str) -> np.ndarray:
    layer = features["dominant_layer"]
    if name == "all":
        return layer >= 0
    if name == "top1_L5":
        return layer == 5
    if name == "top2_L4L5":
        return layer >= 4
    if name == "top3_L3L5":
        return layer >= 3
    if name == "top4_L2L5":
        return layer >= 2
    if name == "central4_L1L4":
        return (layer >= 1) & (layer <= 4)
    raise ValueError(f"unknown layer mask: {name}")


def compton_mask_bool(features: dict, policy: str) -> np.ndarray:
    raw = features["compton_raw"]
    n = features["pix_count"]
    if policy == "keep":
        return (raw == "single") | (raw == "keep") | (raw == "reject")
    if policy == "drop":
        return (raw == "single") | (raw == "keep")
    if policy == "strict":
        return (raw == "single") | ((raw == "keep") & (n <= 3))
    raise ValueError(f"unknown compton policy: {policy}")


def variant_base_mask(features: dict, variant: Variant, ignore_roi: bool = False) -> np.ndarray:
    mask = features["bgo_total_keV"] < variant.bgo_threshold_keV
    mask &= layer_mask_bool(features, variant.layer_mask)
    mask &= compton_mask_bool(features, variant.compton_policy)
    if variant.single_pixel_only:
        mask &= features["single_pixel"]
    if (not ignore_roi) and variant.roi_radius is not None:
        radius = features["max_r_mm"] if variant.edge_reject else features["centroid_r_mm"]
        mask &= np.isfinite(radius) & (radius <= variant.roi_radius)
    return mask


def generate_variants() -> list[Variant]:
    variants: list[Variant] = []
    bgo_thresholds = [30.0, 50.0, 70.0, 100.0]
    roi_options: list[float | None] = [None, 18.0, 15.0, 12.0, 9.0]
    layer_masks = ["all", "top1_L5", "top2_L4L5", "top3_L3L5", "top4_L2L5", "central4_L1L4"]
    policies = ["keep", "drop", "strict"]
    for bgo in bgo_thresholds:
        for roi in roi_options:
            edge_opts = [False] if roi is None else [False, True]
            for edge in edge_opts:
                for single in (False, True):
                    for layer in layer_masks:
                        for policy in policies:
                            rid = "full" if roi is None else f"r{int(roi)}"
                            eid = "edge" if edge else "cent"
                            sid = "single" if single else "multi"
                            variant_id = f"bgo{int(bgo)}_{rid}_{eid}_{sid}_{layer}_{policy}"
                            variants.append(Variant(variant_id, bgo, roi, edge, single, layer, policy))
    return variants


def rate_for(features: dict, mask: np.ndarray, stream_name: str, lo: float, hi: float) -> float:
    e = features["tes_total_keV"]
    stream = features["stream"]
    use = mask & (stream == stream_name) & (e >= lo) & (e < hi)
    return float(np.sum(features["rate_hz"][use]))


def evaluate_variants(features: dict, variants: list[Variant], baseline: dict, source_model: str = "catalog_uniform") -> list[dict]:
    rows: list[dict] = []
    b0 = baseline["background_broad_final_cps"]
    r0 = baseline["science_response_cps_per_flux"]
    q0 = baseline["q0"]
    f0 = baseline["f0_best_3sigma_1Ms"]
    focused_broad0 = baseline["focused_broad_final_cps"]
    focused_line0 = baseline["focused_line_final_cps"]

    for variant in variants:
        mask = variant_base_mask(features, variant, ignore_roi=False)
        mask_no_roi = variant_base_mask(features, variant, ignore_roi=True)

        b_lo, b_hi, _ = BROAD
        l_lo, l_hi, _ = LINE
        prompt = rate_for(features, mask, "prompt", b_lo, b_hi)
        delayed = rate_for(features, mask, "delayed", b_lo, b_hi)
        science = rate_for(features, mask, "science", b_lo, b_hi)
        science_no_roi = rate_for(features, mask_no_roi, "science", b_lo, b_hi)

        if source_model == "focal_core_bound" and variant.roi_radius is not None:
            science_for_response = science_no_roi
            source_acceptance_note = "ROI loss removed; same non-ROI cuts retained"
        else:
            science_for_response = science
            source_acceptance_note = "catalog source acceptance"

        response = science_for_response / REFERENCE_FLUX
        source_survival = response / r0 if r0 > 0 else float("nan")
        focused_scale = max(source_survival, 0.0) if np.isfinite(source_survival) else 0.0
        focused_broad = focused_broad0 * focused_scale
        background = prompt + delayed + focused_broad
        q = response / math.sqrt(background) if background > 0 and response > 0 else float("nan")
        q_ratio = q / q0 if q0 > 0 and np.isfinite(q) else float("nan")
        f3_scaled = f0 / q_ratio if q_ratio > 0 else float("nan")
        f3_counting = 3.0 * math.sqrt(background) / (response * math.sqrt(OBS_TIME_S)) if response > 0 and background > 0 else float("nan")
        p3 = p3_from_f3(f3_scaled)

        prompt_line = rate_for(features, mask, "prompt", l_lo, l_hi)
        delayed_line = rate_for(features, mask, "delayed", l_lo, l_hi)
        science_line = rate_for(features, mask, "science", l_lo, l_hi)
        science_line_no_roi = rate_for(features, mask_no_roi, "science", l_lo, l_hi)
        science_line_for_response = science_line_no_roi if source_model == "focal_core_bound" and variant.roi_radius is not None else science_line
        line_source_survival = (science_line_for_response / REFERENCE_FLUX) / r0 if r0 > 0 else float("nan")
        focused_line = focused_line0 * max(line_source_survival, 0.0) if np.isfinite(line_source_survival) else 0.0
        line_background = prompt_line + delayed_line + focused_line

        rows.append(
            {
                "variant_id": variant.variant_id,
                "source_model": source_model,
                "bgo_threshold_keV": variant.bgo_threshold_keV,
                "roi_radius_mm": "full" if variant.roi_radius is None else variant.roi_radius,
                "edge_reject": int(variant.edge_reject),
                "single_pixel_only": int(variant.single_pixel_only),
                "layer_mask": variant.layer_mask,
                "compton_policy": variant.compton_policy,
                "prompt_broad_cps": prompt,
                "delayed_broad_cps": delayed,
                "focused_broad_cps": focused_broad,
                "background_broad_cps": background,
                "science_broad_cps_at_1e-4": science_for_response,
                "science_catalog_broad_cps_at_1e-4": science,
                "science_no_roi_broad_cps_at_1e-4": science_no_roi,
                "science_response_cps_per_flux": response,
                "science_survival_vs_baseline": source_survival,
                "q_cps_per_flux_over_sqrt_cps": q,
                "q_over_q0": q_ratio,
                "f3_best_scaled_1Ms_ph_cm2_s": f3_scaled,
                "f3_counting_no_nuisance_1Ms_ph_cm2_s": f3_counting,
                "p_ge_3sigma_at_1e-4_1Ms": p3,
                "prompt_line_cps": prompt_line,
                "delayed_line_cps": delayed_line,
                "focused_line_cps": focused_line,
                "background_line_cps": line_background,
                "science_line_cps_at_1e-4": science_line_for_response,
                "source_acceptance_note": source_acceptance_note,
            }
        )
    return rows


def add_focal_core_bound_rows(features: dict, variants: list[Variant], baseline: dict) -> list[dict]:
    roi_variants = [v for v in variants if v.roi_radius is not None]
    return evaluate_variants(features, roi_variants, baseline, source_model="focal_core_bound")


def row_float(row: dict, key: str) -> float:
    try:
        return float(row[key])
    except (KeyError, TypeError, ValueError):
        return float("nan")


def top_rows(rows: list[dict], n: int = 20, source_model: str | None = None) -> list[dict]:
    work = [r for r in rows if source_model is None or r.get("source_model") == source_model]
    return sorted(work, key=lambda r: row_float(r, "q_over_q0"), reverse=True)[:n]


def write_plots(rows: list[dict], outdir: Path, prefix: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    outdir.mkdir(parents=True, exist_ok=True)
    finite = [r for r in rows if np.isfinite(row_float(r, "q_over_q0")) and row_float(r, "background_broad_cps") > 0]
    if not finite:
        return
    bg = np.asarray([row_float(r, "background_broad_cps") for r in finite], dtype=float)
    surv = np.asarray([row_float(r, "science_survival_vs_baseline") for r in finite], dtype=float)
    q = np.asarray([row_float(r, "q_over_q0") for r in finite], dtype=float)
    models = np.asarray([r.get("source_model", "") for r in finite])

    fig, ax = plt.subplots(figsize=(7.2, 5.2), dpi=160)
    for model, marker in (("catalog_uniform", "o"), ("focal_core_bound", "^")):
        m = models == model
        if np.any(m):
            sc = ax.scatter(bg[m], q[m], c=surv[m], s=18, marker=marker, cmap="viridis", alpha=0.78, linewidths=0)
    ax.axhline(1.0, color="0.45", lw=1.0, ls="--")
    ax.axhline(1.4, color="#b23a48", lw=1.0, ls=":")
    ax.set_xlabel("Final broad background rate (cps)")
    ax.set_ylabel("Q / Q0")
    ax.set_title("WP-D1 selection Pareto")
    cbar = fig.colorbar(sc, ax=ax)
    cbar.set_label("Science survival vs baseline")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(outdir / f"{prefix}_q_vs_background.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 5.2), dpi=160)
    for model, marker in (("catalog_uniform", "o"), ("focal_core_bound", "^")):
        m = models == model
        if np.any(m):
            ax.scatter(bg[m], surv[m], c=q[m], s=18, marker=marker, cmap="plasma", alpha=0.78, linewidths=0)
    ax.set_xlabel("Final broad background rate (cps)")
    ax.set_ylabel("Science survival vs baseline")
    ax.set_title("Source acceptance versus selected background")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(outdir / f"{prefix}_source_acceptance_vs_background.png")
    plt.close(fig)


def write_selection_summary(outdir: Path, rows: list[dict], label: str) -> None:
    best_catalog = top_rows(rows, 10, "catalog_uniform")
    best_bound = top_rows(rows, 10, "focal_core_bound")
    lines = []
    lines.append(f"# WP-D1 {label} selection summary")
    lines.append("")
    lines.append("Catalog-uniform rows use the current simulated Gate-A source distribution.")
    lines.append("Focal-core bound rows retain non-ROI source losses but remove ROI loss, representing a compact true focal spot bound.")
    lines.append("")
    lines.append("## Best catalog-uniform rows")
    lines.append("")
    for row in best_catalog[:5]:
        lines.append(
            f"- `{row['variant_id']}`: Q/Q0={fmt(row_float(row, 'q_over_q0'))}, "
            f"B={fmt(row_float(row, 'background_broad_cps'))} cps, "
            f"R={fmt(row_float(row, 'science_response_cps_per_flux'))}, "
            f"F3={fmt(row_float(row, 'f3_best_scaled_1Ms_ph_cm2_s'))}."
        )
    lines.append("")
    lines.append("## Best focal-core bound rows")
    lines.append("")
    for row in best_bound[:5]:
        lines.append(
            f"- `{row['variant_id']}`: Q/Q0={fmt(row_float(row, 'q_over_q0'))}, "
            f"B={fmt(row_float(row, 'background_broad_cps'))} cps, "
            f"R={fmt(row_float(row, 'science_response_cps_per_flux'))}, "
            f"F3={fmt(row_float(row, 'f3_best_scaled_1Ms_ph_cm2_s'))}."
        )
    lines.append("")
    lines.append("## Practical interpretation")
    lines.append("")
    if best_catalog and row_float(best_catalog[0], "q_over_q0") >= 1.4:
        lines.append("The no-hardware catalog selection already clears Q/Q0>=1.4 and is therefore the most efficient immediate implementation.")
    elif best_bound and row_float(best_bound[0], "q_over_q0") >= 1.4:
        lines.append("The no-hardware catalog selection does not clear Q/Q0>=1.4, but a compact focal-spot ROI bound does.")
    else:
        lines.append("Neither the catalog-uniform nor the focal-core bound clears Q/Q0>=1.4; hardware delta transport is required.")
    (outdir / "best_no_hardware_change_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def activation_removal_bound(activation_path: Path, baseline: dict, outdir: Path) -> list[dict]:
    rows = read_csv(activation_path)
    b0 = baseline["background_broad_final_cps"]
    focused = baseline["focused_broad_final_cps"]
    prompt_floor = baseline["prompt_broad_final_cps"] + focused
    out: list[dict] = []
    for row in rows:
        group = row.get("geometry_group", "")
        broad = csv_float(row, "broad_480_550_final_cps", 0.0)
        line = csv_float(row, "line_510p3_511p8_final_cps", 0.0)
        activity = csv_float(row, "day15_parentfed_activity_Bq", 0.0)
        b_removed = max(b0 - broad, prompt_floor)
        b_half = max(b0 - 0.5 * broad, prompt_floor)
        q_full = math.sqrt(b0 / b_removed) if b_removed > 0 else float("inf")
        q_half = math.sqrt(b0 / b_half) if b_half > 0 else float("inf")
        f_full = baseline["f0_best_3sigma_1Ms"] / q_full if q_full > 0 else float("nan")
        f_half = baseline["f0_best_3sigma_1Ms"] / q_half if q_half > 0 else float("nan")
        out.append(
            {
                "geometry_group": group,
                "activity_Bq": activity,
                "delayed_broad_final_cps": broad,
                "delayed_line_final_cps": line,
                "broad_fraction_of_total_background": broad / b0 if b0 > 0 else float("nan"),
                "q_over_q0_if_removed_bound": q_full,
                "q_over_q0_if_50pct_reduced_bound": q_half,
                "f3_best_1Ms_if_removed_bound": f_full,
                "f3_best_1Ms_if_50pct_reduced_bound": f_half,
                "priority_flag": "enter_delta_test" if q_half >= 1.05 or q_full >= 1.20 else "low_priority_bound",
                "geometry_note": row.get("geometry_note", ""),
            }
        )
    out = sorted(out, key=lambda r: row_float(r, "q_over_q0_if_removed_bound"), reverse=True)
    write_csv(outdir / "high_activation_groups.csv", out)
    write_csv(outdir / "removal_bound_table.csv", out)
    lines = []
    lines.append("# WP-D3 material and geometry priority rank")
    lines.append("")
    lines.append("The table is a removal/reduction bound, not a new transport result. It ranks which delayed-activation geometry groups are worth a dedicated delta-transport test.")
    lines.append("")
    for i, row in enumerate(out, start=1):
        lines.append(
            f"{i}. {row['geometry_group']}: delayed broad={fmt(row_float(row, 'delayed_broad_final_cps'))} cps, "
            f"Q/Q0 if removed={fmt(row_float(row, 'q_over_q0_if_removed_bound'))}, "
            f"Q/Q0 if 50% reduced={fmt(row_float(row, 'q_over_q0_if_50pct_reduced_bound'))}, "
            f"flag={row['priority_flag']}."
        )
    lines.append("")
    lines.append("Priority rule: full-removal Q/Q0>1.2 or 50% reduction Q/Q0>1.05 is enough to justify a small source-isolated delta transport.")
    (outdir / "material_priority_rank.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def timing_overlay(timing_path: Path, baseline: dict, outdir: Path) -> list[dict]:
    rows = []
    r0 = baseline["science_response_cps_per_flux"]
    b0 = baseline["background_broad_final_cps"]
    q0 = baseline["q0"]
    for row in read_csv(timing_path):
        if row.get("energy_window") != "broad_480_550":
            continue
        b = csv_float(row, "background_final_cps", float("nan"))
        survival = csv_float(row, "science_survival", float("nan"))
        response = r0 * survival
        q = response / math.sqrt(b) if b > 0 else float("nan")
        q_ratio = q / q0 if q0 > 0 else float("nan")
        rows.append(
            {
                "window_us": csv_float(row, "window_us", float("nan")),
                "background_broad_cps": b,
                "science_survival": survival,
                "q_over_q0": q_ratio,
                "f3_best_scaled_1Ms_ph_cm2_s": baseline["f0_best_3sigma_1Ms"] / q_ratio if q_ratio > 0 else float("nan"),
                "note": "existing timing scan overlay; not multiplied into WP-D1 catalog rows",
            }
        )
    write_csv(outdir / "timing_window_overlay.csv", rows)
    return rows


def make_design_recommendation(
    outdir: Path,
    baseline: dict,
    low_rows: list[dict],
    high_rows: list[dict],
    removal_rows: list[dict],
    timing_rows: list[dict],
    low_info: dict,
    highstat_ran: bool,
) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    best_low_catalog = top_rows(low_rows, 1, "catalog_uniform")[0] if top_rows(low_rows, 1, "catalog_uniform") else None
    best_low_bound = top_rows(low_rows, 1, "focal_core_bound")[0] if top_rows(low_rows, 1, "focal_core_bound") else None
    best_high_catalog = top_rows(high_rows, 1, "catalog_uniform")[0] if high_rows and top_rows(high_rows, 1, "catalog_uniform") else None
    best_high_bound = top_rows(high_rows, 1, "focal_core_bound")[0] if high_rows and top_rows(high_rows, 1, "focal_core_bound") else None
    best_timing = sorted(timing_rows, key=lambda r: row_float(r, "q_over_q0"), reverse=True)[0] if timing_rows else None
    top_removal = removal_rows[0] if removal_rows else None

    summary_rows = []

    def add_case(name: str, row: dict | None, risk: str, recommendation: str) -> None:
        if row is None:
            return
        summary_rows.append(
            {
                "design_case": name,
                "science_response_cps_per_flux": row.get("science_response_cps_per_flux", ""),
                "broad_background_cps": row.get("background_broad_cps", ""),
                "line_background_cps": row.get("background_line_cps", ""),
                "q_over_q0": row.get("q_over_q0", ""),
                "f3_best_scaled_1Ms_ph_cm2_s": row.get("f3_best_scaled_1Ms_ph_cm2_s", ""),
                "p_ge_3sigma_at_1e-4_1Ms": row.get("p_ge_3sigma_at_1e-4_1Ms", ""),
                "hardware_risk": risk,
                "recommendation": recommendation,
                "variant_id": row.get("variant_id", ""),
            }
        )

    baseline_row = {
        "science_response_cps_per_flux": baseline["science_response_cps_per_flux"],
        "background_broad_cps": baseline["background_broad_final_cps"],
        "background_line_cps": "",
        "q_over_q0": 1.0,
        "f3_best_scaled_1Ms_ph_cm2_s": baseline["f0_best_3sigma_1Ms"],
        "p_ge_3sigma_at_1e-4_1Ms": p3_from_f3(baseline["f0_best_3sigma_1Ms"]),
        "variant_id": "baseline_Ta6_full_catalog",
    }
    add_case("baseline Ta6", baseline_row, "low", "validated reference")
    add_case("selection-only best", best_high_catalog or best_low_catalog, "none", "immediate analysis setting if stable")
    add_case("ROI with focal-core source bound", best_high_bound or best_low_bound, "optics-dependent", "candidate only if real focal spot is retained by ROI")
    if best_timing:
        summary_rows.append(
            {
                "design_case": f"timing overlay {fmt(row_float(best_timing, 'window_us'))} us",
                "science_response_cps_per_flux": baseline["science_response_cps_per_flux"] * row_float(best_timing, "science_survival"),
                "broad_background_cps": row_float(best_timing, "background_broad_cps"),
                "line_background_cps": "",
                "q_over_q0": row_float(best_timing, "q_over_q0"),
                "f3_best_scaled_1Ms_ph_cm2_s": row_float(best_timing, "f3_best_scaled_1Ms_ph_cm2_s"),
                "p_ge_3sigma_at_1e-4_1Ms": p3_from_f3(row_float(best_timing, "f3_best_scaled_1Ms_ph_cm2_s")),
                "hardware_risk": "DAQ/timing",
                "recommendation": "do not combine with catalog rows without a dedicated pile-up rerun",
                "variant_id": "existing_timing_scan_overlay",
            }
        )
    if top_removal:
        q = row_float(top_removal, "q_over_q0_if_removed_bound")
        summary_rows.append(
            {
                "design_case": f"remove {top_removal.get('geometry_group')} bound",
                "science_response_cps_per_flux": baseline["science_response_cps_per_flux"],
                "broad_background_cps": baseline["background_broad_final_cps"] - row_float(top_removal, "delayed_broad_final_cps"),
                "line_background_cps": "",
                "q_over_q0": q,
                "f3_best_scaled_1Ms_ph_cm2_s": baseline["f0_best_3sigma_1Ms"] / q if q > 0 else "",
                "p_ge_3sigma_at_1e-4_1Ms": p3_from_f3(baseline["f0_best_3sigma_1Ms"] / q) if q > 0 else "",
                "hardware_risk": "material/geometry",
                "recommendation": "delta transport candidate if mechanically realistic",
                "variant_id": "WP-D3_removal_bound",
            }
        )

    write_csv(outdir / "design_recommendation_table.csv", summary_rows)

    minimal_rows = []
    if best_high_catalog or best_low_catalog:
        row = best_high_catalog or best_low_catalog
        minimal_rows.append(
            {
                "variant": "V3 selection+veto+ROI optimized baseline",
                "execution_status": "high-stat catalog recomputation" if best_high_catalog else "low-stat catalog screen",
                "q_over_q0": row.get("q_over_q0", ""),
                "f3_best_scaled_1Ms_ph_cm2_s": row.get("f3_best_scaled_1Ms_ph_cm2_s", ""),
                "evidence": row.get("variant_id", ""),
                "decision": "promote first; no new geometry needed",
            }
        )
    w_row = next((r for r in removal_rows if r.get("geometry_group") == "W collimator bars"), None)
    if w_row:
        minimal_rows.append(
            {
                "variant": "V2 W collimator/bar optimized",
                "execution_status": "WP-D3 removal bound only",
                "q_over_q0": w_row.get("q_over_q0_if_removed_bound", ""),
                "f3_best_scaled_1Ms_ph_cm2_s": w_row.get("f3_best_1Ms_if_removed_bound", ""),
                "evidence": "W collimator delayed broad contribution",
                "decision": "not a strong standalone lever; combine only if mechanical redesign is already planned",
            }
        )
    if top_removal:
        minimal_rows.append(
            {
                "variant": f"V2b strongest delayed group: {top_removal.get('geometry_group')}",
                "execution_status": "WP-D3 removal bound only",
                "q_over_q0": top_removal.get("q_over_q0_if_removed_bound", ""),
                "f3_best_scaled_1Ms_ph_cm2_s": top_removal.get("f3_best_1Ms_if_removed_bound", ""),
                "evidence": "activation geometry summary",
                "decision": "candidate for source-isolated delayed delta transport",
            }
        )
    minimal_rows.append(
        {
            "variant": "V1 511-CAM-like Bi8 absorber stack",
            "execution_status": "not executed in this add-on pass",
            "q_over_q0": "",
            "f3_best_scaled_1Ms_ph_cm2_s": "",
            "evidence": "requires an external copied geometry and a new activation inventory; current Ta catalog cannot be reweighted reliably to Bi8",
            "decision": "defer until after measured-energy check of V3, to avoid unsupported material conclusions",
        }
    )
    write_csv(outdir / "minimal_delta_variant_screen.csv", minimal_rows)

    lines = []
    lines.append("# Design optimization add-on summary")
    lines.append("")
    lines.append("This add-on is read-only with respect to the validated COSMOSRAY_BG_2605 production chain.")
    lines.append("It uses the frozen day-15 event catalog and compact report ledgers; no source, geometry, or legacy analysis file is modified.")
    lines.append("")
    lines.append("## Baseline")
    lines.append("")
    lines.append(f"- Background-only broad final rate: {fmt(baseline['background_broad_final_cps'])} cps.")
    lines.append(f"- Science response: {fmt(baseline['science_response_cps_per_flux'])} cps/(ph cm^-2 s^-1).")
    lines.append(f"- Reference best-template 3 sigma threshold at 1 Ms: {fmt(baseline['f0_best_3sigma_1Ms'])} ph cm^-2 s^-1.")
    lines.append(f"- Required Q/Q0 for 1e-4 ph cm^-2 s^-1: {fmt(baseline['f0_best_3sigma_1Ms'] / TARGET_FLUX)}.")
    lines.append("")
    lines.append("## Low-stat screen")
    lines.append("")
    for stream, info in low_info.items():
        lines.append(
            f"- {stream}: sampled {info['sampled_events']} of {info['candidate_events']} broad-window candidates "
            f"(rate weight factor {fmt(info['rate_weight_factor'])})."
        )
    if best_low_catalog:
        lines.append(
            f"- Best catalog-uniform low-stat row: `{best_low_catalog['variant_id']}`, "
            f"Q/Q0={fmt(row_float(best_low_catalog, 'q_over_q0'))}, "
            f"B={fmt(row_float(best_low_catalog, 'background_broad_cps'))} cps, "
            f"science survival={fmt(row_float(best_low_catalog, 'science_survival_vs_baseline'))}."
        )
    if best_low_bound:
        lines.append(
            f"- Best focal-core bound low-stat row: `{best_low_bound['variant_id']}`, "
            f"Q/Q0={fmt(row_float(best_low_bound, 'q_over_q0'))}; this assumes ROI loss is removed by a true compact focal spot."
        )
    lines.append(f"- Full-catalog high-stat recomputation was {'run' if highstat_ran else 'not triggered'}.")
    lines.append("")
    lines.append("## High-stat result")
    lines.append("")
    if best_high_catalog:
        lines.append(
            f"- Most defensible immediate setting: `{best_high_catalog['variant_id']}` with "
            f"Q/Q0={fmt(row_float(best_high_catalog, 'q_over_q0'))}, "
            f"B={fmt(row_float(best_high_catalog, 'background_broad_cps'))} cps, "
            f"R={fmt(row_float(best_high_catalog, 'science_response_cps_per_flux'))}, "
            f"F3(best-scaled)={fmt(row_float(best_high_catalog, 'f3_best_scaled_1Ms_ph_cm2_s'))}."
        )
    if best_high_bound:
        lines.append(
            f"- Best ROI/focal-core conditional bound: `{best_high_bound['variant_id']}` with "
            f"Q/Q0={fmt(row_float(best_high_bound, 'q_over_q0'))}, "
            f"F3(best-scaled)={fmt(row_float(best_high_bound, 'f3_best_scaled_1Ms_ph_cm2_s'))}."
        )
    if top_removal:
        lines.append(
            f"- Strongest single delayed-geometry bound: {top_removal['geometry_group']} removal gives "
            f"Q/Q0={fmt(row_float(top_removal, 'q_over_q0_if_removed_bound'))}; "
            f"50% reduction gives Q/Q0={fmt(row_float(top_removal, 'q_over_q0_if_50pct_reduced_bound'))}."
        )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append("- The catalog-uniform rows are the high-confidence result because they use the current simulated source phase space.")
    lines.append("- The focal-core rows are design bounds: they ask what happens if optics or event reconstruction keeps the source inside the selected ROI while the diffuse/activation background is cut by ROI.")
    lines.append("- Focused gamma background is carried as a separate addendum and scaled with source-like acceptance; it is not added to the direct prompt gamma stream, avoiding double counting.")
    lines.append("- Timing-window rows are imported as an overlay from the existing timing scan and are not multiplied into ROI/BGO rows without a dedicated pile-up rerun.")
    lines.append("")
    lines.append("## Recommendation")
    lines.append("")
    if best_high_catalog and row_float(best_high_catalog, "q_over_q0") >= 1.4:
        lines.append("Selection-only optimization reaches the target Q/Q0>=1.4 in the current catalog and should be promoted to the next paper baseline after an independent measured-energy check.")
    elif best_high_bound and row_float(best_high_bound, "q_over_q0") >= 1.4:
        lines.append("The current catalog does not prove a no-hardware solution, but a compact focal-spot ROI combined with the best veto/selection row reaches the target bound and is the most promising design direction.")
    else:
        lines.append("No single high-confidence catalog-only setting reaches Q/Q0>=1.4; the next efficient step is a combined compact-ROI plus high-activation material/geometry delta transport.")
    lines.append("")
    lines.append("Key files are listed in `artifact_manifest.csv`.")
    (outdir / "design_optimization_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(outdir: Path) -> None:
    files = []
    for path in sorted(outdir.rglob("*")):
        if path.is_file():
            files.append(
                {
                    "relative_path": str(path.relative_to(outdir)),
                    "bytes": path.stat().st_size,
                }
            )
    write_csv(outdir / "artifact_manifest.csv", files, ["relative_path", "bytes"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", type=Path, default=CATALOG_DEFAULT)
    ap.add_argument("--outdir", type=Path, default=OUT_ROOT_DEFAULT)
    ap.add_argument("--lowstat-max-per-stream", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=260513)
    ap.add_argument("--highstat-trigger-q", type=float, default=1.01)
    ap.add_argument("--force-highstat", action="store_true")
    args = ap.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    baseline = load_baseline(SUMMARY_DEFAULT, LINEAGE_DEFAULT, FOCUSED_DEFAULT)
    variants = generate_variants()
    print(f"[INFO] loading catalog: {args.catalog}", flush=True)
    cat = load_catalog(args.catalog)
    broad_idx = candidate_indices(cat, BROAD)
    print(f"[INFO] broad-window candidates: {len(broad_idx)}", flush=True)

    low_idx, low_scale, low_info = lowstat_sample(cat, broad_idx, args.lowstat_max_per_stream, args.seed)
    low_features = build_features(cat, low_idx, low_scale, "lowstat", progress_every=2500)
    low_rows = evaluate_variants(low_features, variants, baseline, source_model="catalog_uniform")
    low_rows.extend(add_focal_core_bound_rows(low_features, variants, baseline))
    low_dir = args.outdir / "WP_D1_selection_pareto_lowstat"
    write_csv(low_dir / "selection_pareto_lowstat.csv", low_rows)
    write_csv(low_dir / "top20_catalog_uniform_lowstat.csv", top_rows(low_rows, 20, "catalog_uniform"))
    write_csv(low_dir / "top20_focal_core_bound_lowstat.csv", top_rows(low_rows, 20, "focal_core_bound"))
    write_plots(low_rows, low_dir, "lowstat")
    write_selection_summary(low_dir, low_rows, "low-stat")

    best_low = top_rows(low_rows, 1, "catalog_uniform")
    best_low_q = row_float(best_low[0], "q_over_q0") if best_low else float("nan")
    highstat_ran = bool(args.force_highstat or (np.isfinite(best_low_q) and best_low_q >= args.highstat_trigger_q))
    high_rows: list[dict] = []
    if highstat_ran:
        print("[INFO] high-stat full-catalog recomputation triggered", flush=True)
        full_features = build_features(cat, broad_idx, None, "highstat", progress_every=5000)
        high_rows = evaluate_variants(full_features, variants, baseline, source_model="catalog_uniform")
        high_rows.extend(add_focal_core_bound_rows(full_features, variants, baseline))
        high_dir = args.outdir / "WP_D1_selection_pareto_highstat"
        write_csv(high_dir / "selection_pareto_highstat.csv", high_rows)
        write_csv(high_dir / "top20_catalog_uniform_highstat.csv", top_rows(high_rows, 20, "catalog_uniform"))
        write_csv(high_dir / "top20_focal_core_bound_highstat.csv", top_rows(high_rows, 20, "focal_core_bound"))
        write_plots(high_rows, high_dir, "highstat")
        write_selection_summary(high_dir, high_rows, "high-stat")
    else:
        print(f"[INFO] high-stat skipped; best low-stat catalog Q/Q0={best_low_q:.5g}", flush=True)

    act_dir = args.outdir / "WP_D3_material_geometry_bound"
    removal_rows = activation_removal_bound(ACTIVATION_GEOM_DEFAULT, baseline, act_dir)
    timing_rows = timing_overlay(TIMING_SCAN_DEFAULT, baseline, args.outdir / "WP_D1_timing_overlay")

    rec_dir = args.outdir / "WP_D5_design_recommendation"
    make_design_recommendation(rec_dir, baseline, low_rows, high_rows, removal_rows, timing_rows, low_info, highstat_ran)
    write_json(
        args.outdir / "run_metadata.json",
        {
            "catalog": str(args.catalog),
            "output_dir": str(args.outdir),
            "lowstat_max_per_stream": args.lowstat_max_per_stream,
            "seed": args.seed,
            "highstat_trigger_q": args.highstat_trigger_q,
            "highstat_ran": highstat_ran,
            "n_variants_catalog_uniform": len(variants),
            "n_variants_total_with_bounds": len(low_rows),
            "baseline": baseline,
            "sample_info": low_info,
        },
    )
    write_manifest(args.outdir)
    print(f"[DONE] wrote add-on design optimization outputs to {args.outdir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
