#!/usr/bin/env python3
"""Build Phase 10 compact-source vs diffuse-null discrimination artifacts.

Phase 10 is a conservative scaffold.  It uses the validated post-optics
Be-window detector-response authority and the Phase 9 ABC source-case layer.
It does not claim production optics ray tracing or final point/diffuse imaging
separation.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import pickle
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/codex_tes_511_matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import yaml


ROOT = Path(__file__).resolve().parents[1]
R2 = ROOT / "reports2.0"
OUT_DEFAULT = R2 / "10_POINT_DIFFUSE_DISCRIMINATION"
ABC_DIR_DEFAULT = R2 / "09_SOURCE_CASES_ABC"
CFG_DIR = ROOT / "configs" / "astro_source_cases"
SCRIPT_PACKAGE_DIR = R2 / "05_SCRIPTS_AND_CONFIG" / "tools"

CATALOG_DEFAULT = ROOT / "reports" / "day15_complete_report" / "work" / "event_catalog.pkl"
MEASURED_DEFAULT = ROOT / "reports" / "phase2_real_flight_physical_production" / "event_catalog_v2_measured" / "event_catalog_v2_measured_compact.pkl"
DESIGN_TABLE_DEFAULT = R2 / "08_DESIGN_OPTIMIZATION_ADDON" / "WP_D5_design_recommendation" / "design_recommendation_table.csv"
HIGHSTAT_DEFAULT = R2 / "08_DESIGN_OPTIMIZATION_ADDON" / "WP_D1_selection_pareto_highstat" / "selection_pareto_highstat.csv"
FOCUSED_DEFAULT = R2 / "03_NEXT_PHASE_SUPPORT" / "optics_focused_gamma_background" / "focused_gamma_background_summary.csv"
V404_BANDPASS_DEFAULT = ABC_DIR_DEFAULT / "v404_bandpass_loss.csv"

REFERENCE_FLUX = 1.0e-4
EXPOSURE_S = 1.0e6
E0_KEV = 511.0

WINDOWS = {
    "broad_480_550": (480.0, 550.0),
    "line_510p3_511p8": (510.3, 511.8),
}


@dataclass(frozen=True)
class Selection:
    selection_id: str
    bgo_threshold_keV: float
    roi_radius_mm: float | None
    edge_reject: bool
    single_pixel_only: bool
    layer_mask: str
    compton_policy: str
    authority_role: str


SELECTIONS = [
    Selection("baseline", 50.0, None, False, False, "all", "keep", "validated_reference"),
    Selection("bgo30_r18_cent_single_top1_L5_keep", 30.0, 18.0, False, True, "top1_L5", "keep", "selection_only_best_candidate"),
    Selection("bgo50_reference", 50.0, None, False, False, "all", "keep", "reference_bgo_proxy"),
    Selection("no_bgo_or_loose_roi_control", 1.0e9, None, False, False, "all", "keep", "control_not_for_claim"),
]


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fields: list[str] = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
        fieldnames = fields
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_yaml(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, sort_keys=False, allow_unicode=False), encoding="utf-8")


def read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def csv_float(row: dict[str, str], key: str, default: float = float("nan")) -> float:
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def fmt(x: float, nd: int = 6) -> str:
    if not np.isfinite(x):
        return "nan"
    if x == 0:
        return "0"
    if abs(x) < 1.0e-3 or abs(x) >= 1.0e4:
        return f"{x:.{nd}e}"
    return f"{x:.{nd}g}"


def normal_survival(z: float) -> float:
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def p_ge_3_from_f3(flux: float, f3: float) -> float:
    if not np.isfinite(f3) or f3 <= 0:
        return float("nan")
    mean_z = 3.0 * flux / f3
    return normal_survival(3.0 - mean_z)


def asimov_z(signal_cps: float, background_cps: float, exposure_s: float) -> float:
    if signal_cps <= 0 or background_cps <= 0 or exposure_s <= 0:
        return 0.0
    s = signal_cps * exposure_s
    b = background_cps * exposure_s
    return math.sqrt(max(0.0, 2.0 * ((s + b) * math.log1p(s / b) - s)))


def update_source_case_ids(source_cases: Path, out: Path) -> dict[str, Any]:
    cfg = read_yaml(source_cases)
    rename_map = {"A_GC_POINT_SgrA_anchor": "A_GC_CENTRAL_COMPACT_SPI_ANCHOR"}
    for case in cfg.get("cases", []):
        if case.get("case_id") in rename_map:
            case["legacy_case_id"] = case["case_id"]
            case["case_id"] = rename_map[case["case_id"]]
            case["target"] = "Galactic_Center"
            case["hypothesis"] = "central compact / point-like 511 keV component near the Galactic centre"
            case["candidate_association"] = "Sgr A* / nuclear stellar region / unresolved central compact source"
            case["association_status"] = "assumption_only_not_claimed"
            case["current_status"] = "L1_PLACEHOLDER_OPTICS_FOLDING"
            case["forbidden_claims"] = ["confirmed_SgrA_511_source", "final_astrophysical_detectability"]
    write_yaml(out, cfg)
    return cfg


def write_optics_schema(path: Path, status: str = "PLACEHOLDER") -> dict[str, Any]:
    schema = {
        "metadata": {
            "optics_id": "optics_511_placeholder_or_real_v0",
            "status": status,
            "optics_type": "channeling_or_laue_or_hybrid",
            "focal_length_m": 12.0,
            "notes": "This file must not be used for final astrophysical detectability unless status is PRODUCTION_RAYTRACE.",
        },
        "energy_grid_keV": [460, 470, 480, 490, 500, 505, 510, 511, 512, 515, 520, 530, 540, 550],
        "aeff_cm2": {
            "on_axis": "required_array_matching_energy_grid",
            "off_axis_grid_arcmin": [0, 1, 2, 4, 6, 8, 10],
            "values_cm2": "required_2d_array_energy_by_offaxis",
        },
        "bandpass": {
            "nominal_center_keV": 511.0,
            "supported_energy_min_keV": 480.0,
            "supported_energy_max_keV": 550.0,
            "redshifted_464_status": "OUTSIDE_OR_LOW_AEFF",
        },
        "psf": {
            "focal_plane_x_mm_grid": "required",
            "focal_plane_y_mm_grid": "required",
            "point_source_kernel": "required_file",
            "encircled_energy_radius_mm": {"p50": "required", "p68": "required", "p90": "required"},
        },
        "fov": {"angular_radius_arcmin": "required", "response_vs_offaxis": "required_file"},
        "diffuse_focal_map": {"status": "NOT_AVAILABLE", "sky_model_projection_files": []},
        "pointing_visibility": {
            "status": "PLACEHOLDER",
            "source_visibility_file": "required",
            "atmospheric_transmission_file": "required",
        },
        "claim_control": {
            "allowed_claim": "L1 source-case folding only unless status=PRODUCTION_RAYTRACE",
            "forbidden_claims": ["final_GC_point_source_detectability", "final_point_diffuse_imaging_discrimination"],
        },
    }
    write_yaml(path, schema)
    return schema


def focused_gamma_rates(path: Path) -> dict[str, float]:
    rates = {"broad_480_550": 1.0229422279267938e-6, "line_510p3_511p8": 2.1533347815216934e-8}
    if path.exists():
        for row in read_csv(path):
            window = row.get("window")
            if window in rates:
                rates[window] = csv_float(row, "mean_final_focused_gamma_cps", rates[window])
    return rates


def design_rows(path: Path) -> dict[str, dict[str, str]]:
    return {row["design_case"]: row for row in read_csv(path)}


def highstat_rows(path: Path) -> dict[str, dict[str, str]]:
    rows = read_csv(path)
    return {row["variant_id"]: row for row in rows}


def source_spectrum_fractions(abc_dir: Path) -> dict[str, float]:
    out = {}
    for row in read_csv(abc_dir / "source_spectrum_summary.csv"):
        out[row["model_id"]] = csv_float(row, "aeff_weighted_fraction_of_511", 1.0)
    return out


def diffuse_default_cps(abc_summary: dict[str, Any]) -> float:
    return float(abc_summary["checks"]["B_default_diffuse_cps"])


def build_point_diffuse_table(outdir: Path, abc_dir: Path, abc_summary: dict[str, Any], design: dict[str, dict[str, str]], focused: dict[str, float]) -> list[dict[str, Any]]:
    spec_frac = source_spectrum_fractions(abc_dir)
    b_default = diffuse_default_cps(abc_summary)
    modes = [
        ("count_only_L1", "L1_COUNT_ONLY_OR_PLACEHOLDER_TEMPLATE", 1.0, "B enters as aperture foreground only; no focal morphology claim."),
        ("uniform_focal_conservative", "L1_COUNT_ONLY_OR_PLACEHOLDER_TEMPLATE", 1.25, "Conservative placeholder diffuse-template penalty; not an optics focal map."),
        ("psf_like_worst_case", "L1_COUNT_ONLY_OR_PLACEHOLDER_TEMPLATE", 2.0, "Worst-case placeholder confusion penalty; not a production PSF result."),
    ]
    selection_map = {
        "baseline": design["baseline Ta6"],
        "selection_only_best_pending_measured_audit": design["selection-only best"],
    }
    fluxes = [3e-5, 5e-5, 8e-5, 1e-4, 1.5e-4, 2e-4, 3e-4]
    spectra = ["mono_511", "gaussian_fwhm_1p5"]
    rows: list[dict[str, Any]] = []
    for selection_id, drow in selection_map.items():
        design_b = csv_float(drow, "broad_background_cps")
        design_r = csv_float(drow, "science_response_cps_per_flux")
        base_f3 = csv_float(drow, "f3_best_scaled_1Ms_ph_cm2_s")
        focused_b = focused["broad_480_550"]
        instrument_b = max(0.0, design_b - focused_b)
        total_b = instrument_b + focused_b + b_default
        for mode, status, penalty, note in modes:
            for spectrum in spectra:
                response = design_r * spec_frac.get(spectrum, 1.0)
                profiled_f3_reference = base_f3 / spec_frac.get(spectrum, 1.0) * math.sqrt(total_b / design_b) * penalty
                f3 = 3.0 * math.sqrt(total_b) / (response * math.sqrt(EXPOSURE_S)) * penalty if response > 0 and total_b > 0 else float("nan")
                f5 = f3 * 5.0 / 3.0
                for flux in fluxes:
                    s_cps = response * flux
                    rows.append(
                        {
                            "case_id": "A_GC_CENTRAL_COMPACT_SPI_ANCHOR",
                            "mode": mode,
                            "selection_id": selection_id,
                            "exposure_s": EXPOSURE_S,
                            "A_flux_ph_cm2_s": flux,
                            "A_spectrum_model": spectrum,
                            "A_expected_cps": s_cps,
                            "A_expected_counts": s_cps * EXPOSURE_S,
                            "B_diffuse_model": "B_default_bulge8_plus_disk_aperture",
                            "B_diffuse_cps": b_default,
                            "B_diffuse_counts": b_default * EXPOSURE_S,
                            "instrument_background_cps": instrument_b,
                            "focused_gamma_addendum_cps": focused_b,
                            "total_background_cps": total_b,
                            "sigma_sys_fraction": "profiled_proxy_plus_template_penalty",
                            "template_confusion_penalty": penalty,
                            "Z_asimov": asimov_z(s_cps, total_b, EXPOSURE_S) / penalty,
                            "P_ge_3sigma": p_ge_3_from_f3(flux, f3),
                            "F3_ph_cm2_s": f3,
                            "F5_ph_cm2_s": f5,
                            "F3_method": "conservative_counting_from_response_background",
                            "profiled_design_F3_reference_ph_cm2_s": profiled_f3_reference,
                            "profiled_design_P_ge_3sigma_reference": p_ge_3_from_f3(flux, profiled_f3_reference),
                            "point_diffuse_status": status,
                            "optics_status": "PLACEHOLDER_OPTICS",
                            "claim_status": "NOT_FINAL_ASTROPHYSICAL_CLAIM",
                            "notes": note,
                        }
                    )
    write_csv(outdir / "point_diffuse_discrimination.csv", rows)
    summary = {
        "status": "PASS_L1_POINT_DIFFUSE_DISCRIMINATION_SCAFFOLD",
        "rows": len(rows),
        "modes": [m[0] for m in modes],
        "case_id": "A_GC_CENTRAL_COMPACT_SPI_ANCHOR",
        "B_default_diffuse_cps": b_default,
        "claim_status": "NOT_FINAL_ASTROPHYSICAL_CLAIM",
        "optics_status": "PLACEHOLDER_OPTICS",
    }
    write_json(outdir / "point_diffuse_discrimination.json", summary)
    plot_point_diffuse(outdir, rows)
    return rows


def plot_point_diffuse(outdir: Path, rows: list[dict[str, Any]]) -> None:
    use = [r for r in rows if r["A_spectrum_model"] == "mono_511" and r["mode"] == "count_only_L1"]
    fig, ax = plt.subplots(figsize=(7.8, 4.8))
    for selection in sorted({r["selection_id"] for r in use}):
        sub = sorted([r for r in use if r["selection_id"] == selection], key=lambda x: float(x["A_flux_ph_cm2_s"]))
        ax.plot([float(r["A_flux_ph_cm2_s"]) for r in sub], [float(r["A_expected_counts"]) for r in sub], marker="o", label=selection)
    b_counts = float(use[0]["total_background_cps"]) * EXPOSURE_S if use else 0.0
    ax.axhline(b_counts, color="#555555", ls="--", lw=1.0, label="background counts")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("A compact-source flux (ph cm$^{-2}$ s$^{-1}$)")
    ax.set_ylabel("Expected counts in 1 Ms")
    ax.set_title("Phase 10 A-vs-B expected counts, L1 count-only scaffold")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(outdir / "figures" / "A_vs_B_expected_counts.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.8, 4.8))
    for mode in sorted({r["mode"] for r in rows}):
        sub = sorted(
            [r for r in rows if r["selection_id"] == "selection_only_best_pending_measured_audit" and r["A_spectrum_model"] == "mono_511" and r["mode"] == mode],
            key=lambda x: float(x["A_flux_ph_cm2_s"]),
        )
        ax.plot([float(r["A_flux_ph_cm2_s"]) for r in sub], [float(r["P_ge_3sigma"]) for r in sub], marker="o", label=mode)
    ax.axvline(1e-4, color="#555555", ls="--", lw=1.0)
    ax.set_xscale("log")
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("A compact-source flux (ph cm$^{-2}$ s$^{-1}$)")
    ax.set_ylabel("P(>=3 sigma)")
    ax.set_title("Phase 10 detection probability with placeholder template penalties")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(outdir / "figures" / "A_vs_B_detection_probability.png", dpi=220)
    plt.close(fig)


def build_fov_scan(outdir: Path, abc_dir: Path) -> list[dict[str, Any]]:
    diffuse_rows = {r["sky_model"]: r for r in read_csv(abc_dir / "diffuse_aperture_foreground.csv")}
    base_model = diffuse_rows["bulge_gaussian_fwhm_8deg"]
    total = csv_float(base_model, "total_flux_ph_cm2_s")
    fwhm = csv_float(base_model, "fwhm_l_deg")
    sigma = fwhm / 2.3548200450309493
    response = 24.858993900839696
    radii = [0.0, 1.0, 2.0, 4.47, 8.0, 12.0, 20.0, 30.0]
    rows = []
    for arcmin in radii:
        rdeg = arcmin / 60.0
        frac = 0.0 if rdeg <= 0 else 1.0 - math.exp(-(rdeg * rdeg) / (2.0 * sigma * sigma))
        fov_flux = total * frac
        rows.append(
            {
                "sky_model": "bulge_gaussian_fwhm_8deg",
                "fov_radius_arcmin": arcmin,
                "fov_fraction": frac,
                "fov_flux_ph_cm2_s": fov_flux,
                "diffuse_cps_proxy": fov_flux * response,
            }
        )
    write_csv(outdir / "B_diffuse_fov_scan.csv", rows)
    fig, ax = plt.subplots(figsize=(7.3, 4.5))
    ax.plot([r["fov_radius_arcmin"] for r in rows], [r["diffuse_cps_proxy"] for r in rows], marker="o")
    ax.set_xlabel("FoV radius (arcmin)")
    ax.set_ylabel("B diffuse proxy rate (cps)")
    ax.set_title("B diffuse foreground grows monotonically with FoV in L1 aperture model")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(outdir / "figures" / "B_diffuse_foreground_fov_scan.png", dpi=220)
    plt.close(fig)
    return rows


def layer_mask(layer: np.ndarray, name: str) -> np.ndarray:
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
    raise ValueError(name)


def compton_ok(raw: np.ndarray, pix_count: np.ndarray, policy: str) -> np.ndarray:
    if policy == "keep":
        return (raw == "single") | (raw == "keep") | (raw == "reject")
    if policy == "drop":
        return (raw == "single") | (raw == "keep")
    if policy == "strict":
        return (raw == "single") | ((raw == "keep") & (pix_count <= 3))
    raise ValueError(policy)


def build_features_for_basis(cat: dict[str, Any], meas: dict[str, np.ndarray], indices: np.ndarray, basis: str) -> dict[str, Any]:
    sys.path.insert(0, str(ROOT / "tools"))
    from make_day15_report import EventHit, classify_compton  # noqa: WPS433

    measured = basis == "measured"
    tes_total = np.asarray(meas["tes_total_measured_keV"] if measured else cat["tes_total_keV"], dtype=float)
    bgo_total = np.asarray(meas["bgo_total_measured_keV"] if measured else cat["bgo_total_keV"], dtype=float)
    pix_e_all = np.asarray(meas["pix_e_measured_keV"] if measured else cat["pix_e"], dtype=float)
    pix_start_all = np.asarray(cat["pix_start"], dtype=np.int64)
    pix_count_all = np.asarray(cat["pix_count"], dtype=np.int64)
    pix_x_all = np.asarray(cat["pix_x"], dtype=float)
    pix_y_all = np.asarray(cat["pix_y"], dtype=float)
    pix_z_all = np.asarray(cat["pix_z"], dtype=float)
    pix_uid_all = np.asarray(cat["pix_uid"]).astype(str)
    pix_layer_all = np.asarray(cat["pix_layer"], dtype=np.int16)

    n = len(indices)
    centroid_r = np.full(n, np.nan)
    max_r = np.full(n, np.nan)
    dominant_layer = np.full(n, -1, dtype=np.int16)
    positive_pix_count = np.zeros(n, dtype=np.int16)
    raw = np.empty(n, dtype=object)
    for k, idx in enumerate(indices):
        s = int(pix_start_all[idx])
        c = int(pix_count_all[idx])
        if c <= 0:
            raw[k] = "no_tes"
            continue
        sl = slice(s, s + c)
        pe0 = pix_e_all[sl]
        pos = pe0 > 0.0
        pe = pe0[pos]
        if len(pe) <= 0:
            raw[k] = "no_tes"
            continue
        px = pix_x_all[sl][pos]
        py = pix_y_all[sl][pos]
        pz = pix_z_all[sl][pos]
        uid = pix_uid_all[sl][pos]
        layers = pix_layer_all[sl][pos]
        positive_pix_count[k] = len(pe)
        total = float(np.sum(pe))
        cx = float(np.sum(pe * px) / total)
        cy = float(np.sum(pe * py) / total)
        centroid_r[k] = math.hypot(cx, cy)
        max_r[k] = float(np.max(np.sqrt(px * px + py * py)))
        dominant_layer[k] = int(layers[int(np.argmax(pe))])
        if len(pe) == 1:
            raw[k] = "single"
        else:
            hits = [
                EventHit(x=float(x), y=float(y), z=float(z), e=float(e), pixel_uid=str(u), layer=int(layer))
                for x, y, z, e, u, layer in zip(px, py, pz, pe, uid, layers)
            ]
            raw[k] = classify_compton(hits, "drop")
    return {
        "indices": indices,
        "stream": np.asarray(cat["stream"])[indices].astype(str),
        "rate_hz": np.asarray(cat["rate_hz"], dtype=float)[indices],
        "tes_total_keV": tes_total[indices],
        "bgo_total_keV": bgo_total[indices],
        "pix_count": positive_pix_count,
        "single_pixel": positive_pix_count == 1,
        "centroid_r_mm": centroid_r,
        "max_r_mm": max_r,
        "dominant_layer": dominant_layer,
        "compton_raw": raw.astype(str),
    }


def selection_mask(features: dict[str, Any], selection: Selection) -> np.ndarray:
    mask = features["bgo_total_keV"] < selection.bgo_threshold_keV
    mask &= layer_mask(features["dominant_layer"], selection.layer_mask)
    mask &= compton_ok(features["compton_raw"], features["pix_count"], selection.compton_policy)
    if selection.single_pixel_only:
        mask &= features["single_pixel"]
    if selection.roi_radius_mm is not None:
        radius = features["max_r_mm"] if selection.edge_reject else features["centroid_r_mm"]
        mask &= np.isfinite(radius) & (radius <= selection.roi_radius_mm)
    return mask


def rate_for(features: dict[str, Any], mask: np.ndarray, stream: str, lo: float, hi: float) -> tuple[float, int]:
    e = features["tes_total_keV"]
    use = mask & (features["stream"] == stream) & (e >= lo) & (e < hi)
    return float(np.sum(features["rate_hz"][use])), int(np.sum(use))


def audit_selection_measured_energy(outdir: Path, catalog_path: Path, measured_path: Path, focused: dict[str, float]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    with catalog_path.open("rb") as fh:
        cat = pickle.load(fh)
    with measured_path.open("rb") as fh:
        meas = pickle.load(fh)
    true_e = np.asarray(cat["tes_total_keV"], dtype=float)
    meas_e = np.asarray(meas["tes_total_measured_keV"], dtype=float)
    candidate = np.zeros(len(true_e), dtype=bool)
    for lo, hi in WINDOWS.values():
        candidate |= (true_e >= lo) & (true_e < hi)
        candidate |= (meas_e >= lo) & (meas_e < hi)
    indices = np.flatnonzero(candidate)
    features = {
        "true": build_features_for_basis(cat, meas, indices, "true"),
        "measured": build_features_for_basis(cat, meas, indices, "measured"),
    }
    rows: list[dict[str, Any]] = []
    by_sel_window: dict[tuple[str, str, str], dict[str, Any]] = {}
    for selection in SELECTIONS:
        for basis in ("true", "measured"):
            feat = features[basis]
            mask = selection_mask(feat, selection)
            for window, (lo, hi) in WINDOWS.items():
                prompt, n_prompt = rate_for(feat, mask, "prompt", lo, hi)
                delayed, n_delayed = rate_for(feat, mask, "delayed", lo, hi)
                science, n_science = rate_for(feat, mask, "science", lo, hi)
                response = science / REFERENCE_FLUX
                focused_cps = focused[window] * max(0.0, response / 24.858993900839696) if response > 0 else 0.0
                background = prompt + delayed + focused_cps
                f3 = 3.0 * math.sqrt(background) / (response * math.sqrt(EXPOSURE_S)) if response > 0 and background > 0 else float("nan")
                f5 = f3 * 5.0 / 3.0 if np.isfinite(f3) else float("nan")
                row = {
                    "selection_id": selection.selection_id,
                    "energy_basis": basis,
                    "window": window,
                    "source_response_cps_per_flux": response,
                    "background_cps": background,
                    "prompt_cps": prompt,
                    "delayed_cps": delayed,
                    "focused_gamma_cps": focused_cps,
                    "BGO_threshold_keV": selection.bgo_threshold_keV,
                    "ROI_radius_mm": "full" if selection.roi_radius_mm is None else selection.roi_radius_mm,
                    "layer_policy": selection.layer_mask,
                    "single_or_multihit_policy": "single" if selection.single_pixel_only else "multi_allowed",
                    "compton_policy": selection.compton_policy,
                    "n_source_events": n_science,
                    "n_background_events": n_prompt + n_delayed,
                    "F3_ph_cm2_s": f3,
                    "F5_ph_cm2_s": f5,
                    "P_ge_3sigma_at_1e_minus_4": p_ge_3_from_f3(REFERENCE_FLUX, f3),
                    "true_measured_response_rel_diff": "",
                    "true_measured_background_rel_diff": "",
                    "pass_status": "PENDING_PAIR_COMPARISON",
                    "notes": "BGO measured response remains event-total proxy.",
                }
                rows.append(row)
                by_sel_window[(selection.selection_id, window, basis)] = row

    for selection in SELECTIONS:
        for window in WINDOWS:
            tr = by_sel_window[(selection.selection_id, window, "true")]
            mr = by_sel_window[(selection.selection_id, window, "measured")]
            resp_diff = abs(float(mr["source_response_cps_per_flux"]) - float(tr["source_response_cps_per_flux"])) / max(abs(float(tr["source_response_cps_per_flux"])), 1e-300)
            bg_diff = abs(float(mr["background_cps"]) - float(tr["background_cps"])) / max(abs(float(tr["background_cps"])), 1e-300)
            resp_limit = 0.05 if window == "broad_480_550" else 0.10
            bg_limit = 0.05 if window == "broad_480_550" else 0.10
            status = "PASS_MEASURED_ENERGY_AUDIT" if resp_diff < resp_limit and bg_diff < bg_limit else "FAIL_MEASURED_ENERGY_AUDIT"
            if selection.selection_id == "no_bgo_or_loose_roi_control":
                status = "CONTROL_ROW"
            for row in (tr, mr):
                row["true_measured_response_rel_diff"] = resp_diff
                row["true_measured_background_rel_diff"] = bg_diff
                row["pass_status"] = status

    baseline_meas = by_sel_window[("baseline", "broad_480_550", "measured")]
    best_meas = by_sel_window[("bgo30_r18_cent_single_top1_L5_keep", "broad_480_550", "measured")]
    selection_gain_persisted = float(best_meas["F3_ph_cm2_s"]) < float(baseline_meas["F3_ph_cm2_s"])
    best_broad_status = best_meas["pass_status"]
    overall = "PASS_SELECTION_BEST_MEASURED_ENERGY_AUDITED" if best_broad_status == "PASS_MEASURED_ENERGY_AUDIT" and selection_gain_persisted else "FAIL_KEEP_BASELINE_PRIMARY"
    if overall.startswith("PASS"):
        promotion = "selection-only best may be used as measured-energy-audited L1 analysis configuration, not as new hardware or final flight sensitivity"
    else:
        promotion = "selection-only best remains add-on candidate; baseline remains primary authority"

    write_csv(outdir / "selection_best_measured_energy_audit.csv", rows)
    summary = {
        "status": overall,
        "catalog": rel(catalog_path),
        "measured_catalog": rel(measured_path),
        "candidate_events_union_true_or_measured_windows": int(len(indices)),
        "selection_gain_persisted_broad": bool(selection_gain_persisted),
        "baseline_measured_broad_F3": float(baseline_meas["F3_ph_cm2_s"]),
        "selection_best_measured_broad_F3": float(best_meas["F3_ph_cm2_s"]),
        "selection_best_measured_broad_P3_at_1e-4": float(best_meas["P_ge_3sigma_at_1e_minus_4"]),
        "promotion_policy": promotion,
        "known_limitation": "TES response uses measured compact per-pixel proxy; BGO response is event-total proxy.",
        "claim_status": "L1_MEASURED_ENERGY_AUDIT_NOT_FINAL_FLIGHT_SENSITIVITY",
    }
    write_json(outdir / "selection_best_measured_energy_audit.json", summary)
    plot_selection_audit(outdir, rows)
    return rows, summary


def plot_selection_audit(outdir: Path, rows: list[dict[str, Any]]) -> None:
    use = [r for r in rows if r["window"] == "broad_480_550" and r["selection_id"] in {"baseline", "bgo30_r18_cent_single_top1_L5_keep"}]
    labels = [f"{r['selection_id']}\n{r['energy_basis']}" for r in use]
    f3 = [float(r["F3_ph_cm2_s"]) for r in use]
    colors = ["#4C78A8" if r["energy_basis"] == "true" else "#F58518" for r in use]
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    ax.bar(np.arange(len(f3)), f3, color=colors)
    ax.set_xticks(np.arange(len(f3)), labels, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("Counting F3 proxy, 1 Ms (ph cm$^{-2}$ s$^{-1}$)")
    ax.set_title("Selection-only best: true vs measured-energy audit")
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(outdir / "figures" / "selection_best_true_vs_measured.png", dpi=220)
    plt.close(fig)


def write_optics_requirements(outdir: Path) -> list[dict[str, Any]]:
    rows = [
        ("REQ_AEFF_E_THETA", "Aeff(E, theta)", "yes", "yes", "yes", "PLACEHOLDER_TABLE_ON_AXIS", "Aeff(511)=50.89 cm2", "energy/off-axis response table from optics ray tracing", "Flux and bandpass normalization can be wrong."),
        ("REQ_BANDPASS", "bandpass / spectral response", "yes", "yes", "yes", "PLACEHOLDER", "480-550 keV support proxy", "validated energy-dependent optics throughput", "Broad/redshifted lines can be misclassified."),
        ("REQ_PSF", "PSF / focal spot distribution", "yes", "yes", "yes", "NOT_PRODUCTION", "homogeneous disk response source", "point-source PSF kernel and encircled-energy radii", "ROI/single-pixel gains can be overclaimed."),
        ("REQ_FOV_OFFAXIS", "FoV radius and off-axis acceptance", "yes", "yes", "yes", "PLACEHOLDER", "4.47 arcmin top-hat", "off-axis response map", "Diffuse aperture foreground can be biased."),
        ("REQ_DIFFUSE_FOCAL_MAP", "diffuse sky focal projection", "no", "yes", "no", "NOT_AVAILABLE", "aperture integral only", "ray-traced diffuse focal maps for sky models", "Point/diffuse imaging separation cannot be final."),
        ("REQ_POINTING", "pointing history", "yes", "yes", "yes", "PLACEHOLDER", "on-axis 1 Ms plan", "flight pointing/visibility timeline", "Exposure and off-axis response can be wrong."),
        ("REQ_VISIBILITY", "visibility / Earth occultation", "yes", "yes", "yes", "REFERENCE_PROFILE", "Phase2 reference profile", "measured or mission-specific visibility", "Cannot claim measured-flight prediction."),
        ("REQ_ATMOSPHERE", "atmospheric transmission", "yes", "yes", "yes", "REFERENCE_PROFILE", "PARMA reference profile", "production atmosphere for observation timeline", "Flux normalization can drift."),
        ("REQ_SPOT_ENERGY", "focal-plane spot size vs energy", "yes", "yes", "yes", "NOT_AVAILABLE", "constant 3.6 cm disk", "energy-dependent focal spot/ray-trace output", "Line-shape dependent ROI acceptance unknown."),
        ("REQ_FOCUSED_GAMMA", "focused external gamma background path", "yes", "yes", "yes", "LEVEL1_ADDENDUM", "small L1 addendum", "full optics-focused background templates", "Background addendum cannot be final."),
    ]
    out = [
        {
            "requirement_id": rid,
            "quantity": q,
            "needed_for_A": a,
            "needed_for_B": b,
            "needed_for_C": c,
            "current_status": status,
            "placeholder_value": placeholder,
            "production_requirement": prod,
            "risk_if_missing": risk,
        }
        for rid, q, a, b, c, status, placeholder, prod, risk in rows
    ]
    write_csv(outdir / "optics_requirements_matrix.csv", out)
    return out


def write_v404_anchors(outdir: Path, v404_bandpass: Path) -> list[dict[str, Any]]:
    rows = [
        {
            "anchor_id": "V404_2015_literature_placeholder",
            "paper_or_dataset": "Siegert et al. Nature 2016 / INTEGRAL-SPI 2015 flare; audit required before production",
            "epoch": "2015 flare",
            "time_bin_s": "TBD_FROM_LITERATURE",
            "line_centroid_keV": "TBD",
            "redshift_z": "0.10 proxy currently tested",
            "line_width_or_temperature": "kT30/kT170 and broad/redshifted proxies only",
            "flux_ph_cm2_s": "scan only: 0.5e-4 to 3e-3",
            "flux_definition": "not yet audited",
            "continuum_model": "not yet audited",
            "assumption_status": "LITERATURE_ANCHORING_REQUIRED",
            "usable_for_transport": "NO_PRODUCTION_TRANSPORT_YET",
            "bandpass_status": "REDSHIFTED_BELOW_480_KEV_BANDPASS_RISK for z=0.10",
            "notes": "C remains benchmark definition and bandpass-risk assessment, not final V404 detectability.",
        }
    ]
    if v404_bandpass.exists():
        for row in read_csv(v404_bandpass):
            if "redshift" in row.get("spectrum", ""):
                rows.append(
                    {
                        "anchor_id": row["spectrum"],
                        "paper_or_dataset": "Phase 9 proxy spectrum",
                        "epoch": "proxy",
                        "time_bin_s": "not time-resolved",
                        "line_centroid_keV": row.get("center_keV", ""),
                        "redshift_z": row.get("redshift", ""),
                        "line_width_or_temperature": row.get("spectrum", ""),
                        "flux_ph_cm2_s": "scan only",
                        "flux_definition": "proxy",
                        "continuum_model": "not included",
                        "assumption_status": "PROXY_ONLY",
                        "usable_for_transport": "DIAGNOSTIC_ONLY_IF_EXPLICITLY_REQUESTED",
                        "bandpass_status": row.get("bandpass_status", ""),
                        "notes": row.get("note", ""),
                    }
                )
    write_csv(outdir / "v404_literature_anchor_table.csv", rows)
    return rows


def write_source_manifest_phase10(outdir: Path) -> list[dict[str, Any]]:
    rows = [
        {
            "case_id": "A_GC_CENTRAL_COMPACT_SPI_ANCHOR",
            "source_file": "run_configs/astro_cases/Science511_A_GC_POINT_mono_511.source",
            "spectrum_model": "mono_511",
            "beam_geometry": "Gate-A Be-window HomogeneousBeam z=127.66 r=18.0",
            "run_status": "CANDIDATE_NOT_RUN",
            "n_requested": 100000,
            "n_generated": "",
            "sim_file": "",
            "response_cps_per_flux": 24.858993900839696,
            "closure_status": "FOLDING_CLOSURE_PASS_NOT_RERUN",
            "claim_status": "DIAGNOSTIC_SOURCE_CANDIDATE_NOT_NEW_AUTHORITY",
            "notes": "Minimal Cosima rerun recommended as next gate.",
        },
        {
            "case_id": "A_GC_CENTRAL_COMPACT_SPI_ANCHOR",
            "source_file": "run_configs/astro_cases/Science511_A_GC_POINT_gaussian_fwhm_1p5.source",
            "spectrum_model": "gaussian_fwhm_1p5",
            "beam_geometry": "Gate-A Be-window HomogeneousBeam z=127.66 r=18.0",
            "run_status": "CANDIDATE_NOT_RUN",
            "n_requested": 100000,
            "n_generated": "",
            "sim_file": "",
            "response_cps_per_flux": "",
            "closure_status": "NOT_TRANSPORT_VALIDATED",
            "claim_status": "DIAGNOSTIC_SOURCE_CANDIDATE_NOT_NEW_AUTHORITY",
            "notes": "Should remain diagnostic until measured-energy and selection closure pass.",
        },
        {
            "case_id": "B_GC_DIFFUSE_BULGE_DISK",
            "source_file": "",
            "spectrum_model": "diffuse aperture foreground",
            "beam_geometry": "not applicable",
            "run_status": "SKIPPED_BY_DESIGN",
            "n_requested": "",
            "n_generated": "",
            "sim_file": "",
            "response_cps_per_flux": "",
            "closure_status": "APERTURE_INTEGRAL_ONLY",
            "claim_status": "NO_FOCAL_SPOT_SOURCE_WITHOUT_RAYTRACE",
            "notes": "B must not be generated as HomogeneousBeam/focal spot before optics focal map exists.",
        },
        {
            "case_id": "C_V404_2015_TRANSIENT_BENCHMARK",
            "source_file": "run_configs/astro_cases/Science511_C_V404_v404_redshift_z0p10_narrow_proxy.source",
            "spectrum_model": "v404_redshift_z0p10_narrow_proxy",
            "beam_geometry": "Gate-A Be-window HomogeneousBeam candidate",
            "run_status": "CANDIDATE_NOT_RUN",
            "n_requested": 100000,
            "n_generated": "",
            "sim_file": "",
            "response_cps_per_flux": "",
            "closure_status": "BANDPASS_RISK",
            "claim_status": "NOT_SUPPORTED_PRODUCTION",
            "notes": "No final V404 detectability before literature anchors are audited.",
        },
    ]
    write_csv(outdir / "source_case_manifest_phase10.csv", rows)
    return rows


def write_claim_control(outdir: Path) -> None:
    text = """# Phase 10 Claim Control

Allowed:

- L1 compact-source-vs-diffuse-null discrimination scaffold.
- A represents a central compact-source hypothesis near the Galactic centre.
- B diffuse emission is treated as FoV aperture foreground/null model.
- C V404 remains a secondary transient benchmark with explicit bandpass-risk labeling.
- Selection-only best may be called measured-energy-audited only if the audit summary is PASS.

Forbidden:

- Final Galactic-centre point-source detectability simulation.
- Proof that 511 keV emission is from Sgr A*.
- Production-level point/diffuse imaging separation.
- Diffuse Galactic 511 keV source transported through real optics focal map.
- Final V404 transient detectability.
- Treating selection-only best as new hardware geometry or final flight sensitivity.

Repeated-error rule:

If the same implementation or physics error occurs twice, stop local trial-and-error, research 3-5 plausible fixes online, select the shortest defensible fix, implement it, and record the decision.
"""
    (outdir / "claim_control_phase10.md").write_text(text, encoding="utf-8")


def write_claim_boundary_plot(outdir: Path) -> None:
    labels = ["current\nL1 scaffold", "measured-energy\nselection audit", "real optics\nschema", "minimal\nCosima rerun", "production\nray trace"]
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(8.2, 3.8))
    ax.bar(x, [1, 1, 1, 0, 0], color=["#54A24B", "#54A24B", "#54A24B", "#F58518", "#E45756"])
    ax.set_xticks(x, labels)
    ax.set_yticks([0, 1], ["not done", "done/scaffolded"])
    ax.set_ylim(0, 1.25)
    ax.set_title("Phase 10 claim boundary map")
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(outdir / "figures" / "phase10_claim_boundary_map.png", dpi=220)
    plt.close(fig)


def write_readme(outdir: Path, point_rows: list[dict[str, Any]], audit_summary: dict[str, Any]) -> None:
    mono_count = [
        r
        for r in point_rows
        if r["mode"] == "count_only_L1" and r["A_spectrum_model"] == "mono_511" and abs(float(r["A_flux_ph_cm2_s"]) - 1e-4) < 1e-12
    ]
    baseline = next(r for r in mono_count if r["selection_id"] == "baseline")
    best = next(r for r in mono_count if r["selection_id"] == "selection_only_best_pending_measured_audit")
    text = f"""# Phase 10: Compact-Source vs Diffuse-Null Discrimination Scaffold

## Objective

This package evaluates the L1 discrimination scaffold between the central compact-source hypothesis A and the diffuse Galactic foreground/null model B.

## Authority Boundary

The detector-response authority remains `run_configs/Science_511_onaxis_focalbeam_local.source`. The A/B/C cases are astrophysical folding cases, not replacement detector sources.

## Current Optics Status

The current optics file is placeholder/L1. No final astrophysical detectability or final imaging discrimination is claimed.

## Inputs

- `reports2.0/09_SOURCE_CASES_ABC/source_case_summary.json`
- `configs/astro_source_cases/source_cases_511_ABC_v2.yaml`
- `configs/astro_source_cases/optics_response_511_placeholder.yaml`
- `reports/day15_complete_report/work/event_catalog.pkl`
- `reports/phase2_real_flight_physical_production/event_catalog_v2_measured/event_catalog_v2_measured_compact.pkl`

## Key Outputs

- `point_diffuse_discrimination.csv`
- `selection_best_measured_energy_audit.csv`
- `optics_requirements_matrix.csv`
- `source_case_manifest_phase10.csv`
- `claim_control_phase10.md`

## Main Conclusions

1. A baseline remains the conservative validated reference. For `F=1e-4 ph cm^-2 s^-1`, mono 511, 1 Ms, count-only L1 gives `P>=3sigma={fmt(float(baseline['P_ge_3sigma']))}` with `F3={fmt(float(baseline['F3_ph_cm2_s']))}`.
2. Selection-only best remains analysis-only, but the measured-energy audit status is `{audit_summary['status']}`. The measured broad F3 is `{fmt(float(audit_summary['selection_best_measured_broad_F3']))}` and `P>=3sigma={fmt(float(audit_summary['selection_best_measured_broad_P3_at_1e-4']))}`.
3. B diffuse remains aperture-integrated and is not a focal-spot source.
4. Current B rate is small under placeholder narrow-FoV assumptions and must not be generalized before real optics.
5. Final point/diffuse separation requires production `Aeff(E,theta)`, PSF, bandpass, diffuse focal map, and pointing/visibility history.

## Validation

Phase 10 adds dedicated validation checks through `tools/validate_phase10_point_diffuse.py` and workspace checks through `tools/validate_workspace.py`.

## Claim Boundary

Allowed: L1 source-case folding and discrimination scaffold.

Forbidden: final GC point-source detection claim, final V404 detectability, or production-level point/diffuse imaging separation.
"""
    (outdir / "README.md").write_text(text, encoding="utf-8")


def write_artifact_manifest(outdir: Path) -> None:
    rows = []
    for path in sorted(outdir.rglob("*")):
        if path.is_file() and path != outdir / "artifact_manifest.csv":
            rows.append({"relative_path": rel(path), "bytes": path.stat().st_size})
    write_csv(outdir / "artifact_manifest.csv", rows)


def package_files(outdir: Path) -> None:
    package_dir = outdir / "packaged_inputs"
    package_dir.mkdir(parents=True, exist_ok=True)
    for path in [
        CFG_DIR / "source_cases_511_ABC_v2.yaml",
        CFG_DIR / "optics_response_511_schema.yaml",
        CFG_DIR / "optics_response_511_placeholder.yaml",
        CFG_DIR / "point_diffuse_discrimination_config.yaml",
        CFG_DIR / "selection_best_measured_energy_audit.yaml",
    ]:
        if path.exists():
            shutil.copy2(path, package_dir / path.name)
    SCRIPT_PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    for script in [
        "make_511_phase10_point_diffuse_report.py",
        "update_source_case_ids_phase10.py",
        "audit_selection_best_measured_energy.py",
        "make_511_optics_requirements_matrix.py",
        "validate_phase10_point_diffuse.py",
    ]:
        src = ROOT / "tools" / script
        if src.exists():
            shutil.copy2(src, SCRIPT_PACKAGE_DIR / script)


def update_reports2_manifest() -> None:
    rows = []
    for path in sorted(R2.rglob("*")):
        if path.is_file():
            rows.append((str(path.relative_to(R2)), path.stat().st_size))
    with (R2 / "MANIFEST.tsv").open("w", encoding="utf-8") as fh:
        for rel_path, size in rows:
            fh.write(f"{rel_path}\t{size}\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-cases", type=Path, default=CFG_DIR / "source_cases_511_ABC.yaml")
    ap.add_argument("--source-cases-v2", type=Path, default=CFG_DIR / "source_cases_511_ABC_v2.yaml")
    ap.add_argument("--optics", type=Path, default=CFG_DIR / "optics_response_511_placeholder.yaml")
    ap.add_argument("--abc-dir", type=Path, default=ABC_DIR_DEFAULT)
    ap.add_argument("--outdir", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--catalog", type=Path, default=CATALOG_DEFAULT)
    ap.add_argument("--measured-catalog", type=Path, default=MEASURED_DEFAULT)
    ap.add_argument("--design-table", type=Path, default=DESIGN_TABLE_DEFAULT)
    ap.add_argument("--focused-gamma", type=Path, default=FOCUSED_DEFAULT)
    args = ap.parse_args()

    outdir = args.outdir
    (outdir / "figures").mkdir(parents=True, exist_ok=True)
    CFG_DIR.mkdir(parents=True, exist_ok=True)

    update_source_case_ids(args.source_cases, args.source_cases_v2)
    write_optics_schema(CFG_DIR / "optics_response_511_schema.yaml", status="SCHEMA_REQUIRED_FIELDS")
    write_optics_schema(args.optics, status="PLACEHOLDER")
    write_yaml(
        CFG_DIR / "point_diffuse_discrimination_config.yaml",
        {"modes": ["count_only_L1", "uniform_focal_conservative", "psf_like_worst_case"], "claim_status": "NOT_FINAL_ASTROPHYSICAL_CLAIM"},
    )
    write_yaml(
        CFG_DIR / "selection_best_measured_energy_audit.yaml",
        {"selections": [s.__dict__ for s in SELECTIONS], "known_limitation": "BGO event-total proxy"},
    )

    abc_summary = json.loads((args.abc_dir / "source_case_summary.json").read_text(encoding="utf-8"))
    focused = focused_gamma_rates(args.focused_gamma)
    design = design_rows(args.design_table)
    point_rows = build_point_diffuse_table(outdir, args.abc_dir, abc_summary, design, focused)
    build_fov_scan(outdir, args.abc_dir)
    audit_rows, audit_summary = audit_selection_measured_energy(outdir, args.catalog, args.measured_catalog, focused)
    write_optics_requirements(outdir)
    write_v404_anchors(outdir, V404_BANDPASS_DEFAULT)
    write_source_manifest_phase10(outdir)
    write_claim_control(outdir)
    write_claim_boundary_plot(outdir)
    write_readme(outdir, point_rows, audit_summary)

    summary = {
        "status": "PASS_PHASE10_L1_POINT_DIFFUSE_SCAFFOLD",
        "outdir": rel(outdir),
        "point_diffuse_rows": len(point_rows),
        "selection_audit_rows": len(audit_rows),
        "selection_audit_status": audit_summary["status"],
        "case_id": "A_GC_CENTRAL_COMPACT_SPI_ANCHOR",
        "optics_status": "PLACEHOLDER_OPTICS",
        "claim_status": "NOT_FINAL_ASTROPHYSICAL_CLAIM",
    }
    write_json(outdir / "phase10_summary.json", summary)
    package_files(outdir)
    write_artifact_manifest(outdir)
    update_reports2_manifest()
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
