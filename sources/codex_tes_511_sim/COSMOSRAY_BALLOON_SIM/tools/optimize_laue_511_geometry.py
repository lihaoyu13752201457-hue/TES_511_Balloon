#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Optimize a 511 keV monochromatic Ge Laue geometry for the current opticsim flow.

This is deliberately a geometry/throughput optimization layer, not a new
diffraction physics calibration.  It reuses the opticsim Zachariasen/Darwin
mosaic model and writes ring configs that can be consumed by
``laue_multiring_table_demo``.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/codex_tes_511_matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
OPTICSIM_ROOT = Path("/home/ubuntu/opticsim")
if str(OPTICSIM_ROOT) not in sys.path:
    sys.path.insert(0, str(OPTICSIM_ROOT))

from external_baseline.laue_raytrace_py.mosaic_darwin import (  # noqa: E402
    bragg_angle_rad,
    d_spacing_A,
    darwin_mosaic_probabilities,
    optimal_mosaic_thickness_mm,
    structure_factor_abs,
)


HC_KEV_A = 12.398419843320026
SECONDS_PER_DAY = 86400.0
REFERENCE_T_ATM_511 = 0.7390423888027
DEFAULT_OUTDIR = ROOT / "reports_260516/laue_511_geometry_optimization_20260521"
DEFAULT_CONFIG_DIR = ROOT / "configs/opticsim"
DEFAULT_REPLAY = ROOT / "reports_260516/opticsim_laue_cam511_f12m_nonoverlap_replay_20260521/summary.json"
DEFAULT_PER_RING = ROOT / "runs/opticsim_laue_cam511_f12m_nonoverlap_100k_20260521/per_ring_summary.json"
DEFAULT_BACKGROUND = ROOT / "reports_260516/source_time_update/background_time_variation.csv"


@dataclass(frozen=True)
class HklCandidate:
    material: str
    h: int
    k: int
    l: int
    d_spacing_a: float
    theta_b_rad: float
    thickness_mm: float
    p_diff: float
    p_abs: float
    p_trans: float


@dataclass(frozen=True)
class RingDesign:
    ring_id: int
    material: str
    h: int
    k: int
    l: int
    d_spacing_a: float
    radius_mm: float
    tile_size_mm: float
    n_tiles: int
    area_cm2: float
    thickness_mm: float
    p_diff: float
    p_abs: float
    p_trans: float


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def line_background_cps(path: Path) -> float:
    rows = [row for row in read_csv(path) if row.get("window") == "line_510p3_511p8"]
    if not rows:
        return 1.96814
    index = 60 if len(rows) > 60 else len(rows) - 1
    return float(rows[index]["total_background_final_cps_level1"])


def current_511_detector_survival(replay_path: Path, per_ring_path: Path) -> float:
    replay = load_json(replay_path, {})
    per_ring = load_json(per_ring_path, [])
    line_final = float(replay.get("windows", {}).get("line_510p3_511p8", {}).get("final_count", 0.0))
    n_511_diff = 0.0
    for row in per_ring:
        if abs(float(row.get("design_energy_keV", -1.0)) - 511.0) < 1.0e-6:
            n_511_diff += float(row.get("n_diffracted", 0.0))
    if line_final > 0.0 and n_511_diff > 0.0:
        return line_final / n_511_diff
    # Fallback from the current 2026-05-21 replay: 3953 / 4952.
    return 0.7982633


def t3_days(response_cps_per_flux: float, background_cps: float, flux: float, t_atm: float) -> float:
    signal_cps = response_cps_per_flux * flux * t_atm
    if signal_cps <= 0.0 or background_cps <= 0.0:
        return float("inf")
    return (3.0 * math.sqrt(background_cps) / signal_cps) ** 2 / SECONDS_PER_DAY


def allowed_ge_hkls(max_index: int) -> list[tuple[int, int, int]]:
    out: list[tuple[int, int, int]] = []
    seen: set[tuple[int, int, int]] = set()
    for h in range(1, max_index + 1):
        for k in range(0, h + 1):
            for l in range(0, k + 1):
                if h == 0 and k == 0 and l == 0:
                    continue
                hkl = tuple(sorted((h, k, l), reverse=True))
                if hkl in seen:
                    continue
                seen.add(hkl)
                try:
                    if structure_factor_abs("Ge", *hkl, 511.0) <= 0.0:
                        continue
                    d_spacing_A("Ge", *hkl)
                    bragg_angle_rad(511.0, d_spacing_A("Ge", *hkl))
                except Exception:
                    continue
                out.append(hkl)
    return sorted(out, key=lambda x: sum(v * v for v in x))


def build_hkl_candidates(
    *,
    max_index: int,
    mosaic_arcsec: float,
    crystallite_um: float,
    min_pdiff: float,
) -> list[HklCandidate]:
    out: list[HklCandidate] = []
    for h, k, l in allowed_ge_hkls(max_index):
        try:
            d = d_spacing_A("Ge", h, k, l)
            theta_b = bragg_angle_rad(511.0, d)
            thickness = optimal_mosaic_thickness_mm(
                energy_keV=511.0,
                material="Ge",
                h=h,
                k=k,
                l=l,
                mosaic_fwhm_arcsec=mosaic_arcsec,
                crystallite_thickness_um=crystallite_um,
            )
            probs = darwin_mosaic_probabilities(
                energy_keV=511.0,
                material="Ge",
                h=h,
                k=k,
                l=l,
                mosaic_fwhm_arcsec=mosaic_arcsec,
                thickness_mm=thickness,
                crystallite_thickness_um=crystallite_um,
                delta_theta_rad=0.0,
            )
        except Exception:
            continue
        if probs.p_diff < min_pdiff:
            continue
        out.append(
            HklCandidate(
                material="Ge",
                h=h,
                k=k,
                l=l,
                d_spacing_a=d,
                theta_b_rad=theta_b,
                thickness_mm=thickness,
                p_diff=probs.p_diff,
                p_abs=probs.p_abs,
                p_trans=probs.p_trans,
            )
        )
    return out


def choose_tile_sizes(
    radii: list[float],
    *,
    focal_mm: float,
    mosaic_arcsec: float,
    radial_fwhm_fraction: float,
    radial_gap_fraction: float,
    min_tile_mm: float,
    max_tile_mm: float,
) -> list[float]:
    mosaic_rad = math.radians(mosaic_arcsec / 3600.0)
    bragg_width = 2.0 * focal_mm * mosaic_rad * radial_fwhm_fraction
    raw_sizes: list[float] = []
    for i, radius in enumerate(radii):
        nearest_gap = float("inf")
        if i > 0:
            nearest_gap = min(nearest_gap, radius - radii[i - 1])
        if i + 1 < len(radii):
            nearest_gap = min(nearest_gap, radii[i + 1] - radius)
        gap_limit = nearest_gap * radial_gap_fraction if math.isfinite(nearest_gap) else max_tile_mm
        size = min(bragg_width, gap_limit, max_tile_mm)
        if size < min_tile_mm:
            raw_sizes.append(0.0)
        else:
            raw_sizes.append(size)
    return [round(v, 3) for v in raw_sizes]


def design_for_focal_length(
    candidates: list[HklCandidate],
    *,
    focal_mm: float,
    max_radius_mm: float,
    min_radius_mm: float,
    mosaic_arcsec: float,
    radial_fwhm_fraction: float,
    radial_gap_fraction: float,
    min_tile_mm: float,
    max_tile_mm: float,
) -> list[RingDesign]:
    preselected: list[tuple[float, HklCandidate]] = []
    for candidate in candidates:
        radius = focal_mm * math.tan(2.0 * candidate.theta_b_rad)
        if min_radius_mm <= radius <= max_radius_mm:
            preselected.append((radius, candidate))
    preselected.sort(key=lambda item: item[0])
    radii = [radius for radius, _ in preselected]
    sizes = choose_tile_sizes(
        radii,
        focal_mm=focal_mm,
        mosaic_arcsec=mosaic_arcsec,
        radial_fwhm_fraction=radial_fwhm_fraction,
        radial_gap_fraction=radial_gap_fraction,
        min_tile_mm=min_tile_mm,
        max_tile_mm=max_tile_mm,
    )
    rings: list[RingDesign] = []
    for radius, candidate in preselected:
        size = sizes[len(rings)]
        if size <= 0.0:
            continue
        n_tiles = max(1, int(math.floor(2.0 * math.pi * radius / size)))
        area_cm2 = n_tiles * size * size / 100.0
        rings.append(
            RingDesign(
                ring_id=len(rings),
                material=candidate.material,
                h=candidate.h,
                k=candidate.k,
                l=candidate.l,
                d_spacing_a=candidate.d_spacing_a,
                radius_mm=radius,
                tile_size_mm=size,
                n_tiles=n_tiles,
                area_cm2=area_cm2,
                thickness_mm=candidate.thickness_mm,
                p_diff=candidate.p_diff,
                p_abs=candidate.p_abs,
                p_trans=candidate.p_trans,
            )
        )
    return rings


def summarize_design(
    rings: list[RingDesign],
    *,
    focal_mm: float,
    detector_survival_511: float,
    background_cps: float,
    flux_anchor: float,
) -> dict[str, Any]:
    geom = sum(r.area_cm2 for r in rings)
    optics_aeff = sum(r.area_cm2 * r.p_diff for r in rings)
    response = optics_aeff * detector_survival_511
    return {
        "focal_length_m": focal_mm / 1000.0,
        "n_rings": len(rings),
        "outer_radius_mm": max((r.radius_mm + 0.5 * r.tile_size_mm for r in rings), default=float("nan")),
        "outer_diameter_cm": 2.0 * max((r.radius_mm + 0.5 * r.tile_size_mm for r in rings), default=0.0) / 10.0,
        "inner_radius_mm": min((r.radius_mm - 0.5 * r.tile_size_mm for r in rings), default=float("nan")),
        "geometric_crystal_area_cm2": geom,
        "estimated_optics_effective_area_cm2": optics_aeff,
        "estimated_detector_response_cps_per_ph_cm2_s": response,
        "detector_survival_511_assumed": detector_survival_511,
        "background_line_cps": background_cps,
        "T3_days_ref_atm_flux_8e_minus_5": t3_days(response, background_cps, 8.0e-5, REFERENCE_T_ATM_511),
        "T3_days_ref_atm_flux_1e_minus_4": t3_days(response, background_cps, 1.0e-4, REFERENCE_T_ATM_511),
        "T3_days_ref_atm_flux_anchor": t3_days(response, background_cps, flux_anchor, REFERENCE_T_ATM_511),
        "hkls": " ".join(f"Ge({r.h}{r.k}{r.l})" for r in rings),
    }


def write_ring_config(path: Path, rings: list[RingDesign]) -> None:
    rows = []
    for ring in rings:
        rows.append(
            {
                "ring_id": ring.ring_id,
                "design_energy_keV": "511",
                "radius_mm": f"{ring.radius_mm:.6f}",
                "n_tiles": ring.n_tiles,
                "material": ring.material,
                "h": ring.h,
                "k": ring.k,
                "l": ring.l,
                "d_spacing_A": f"{ring.d_spacing_a:.12g}",
                "tile_size_mm": f"{ring.tile_size_mm:.3f}",
                "thickness_mm": f"{ring.thickness_mm:.6g}",
            }
        )
    write_csv(path, rows)


def write_efficiency_table(
    path: Path,
    rings: list[RingDesign],
    *,
    mosaic_arcsec: float,
    crystallite_um: float,
    delta_multiple: float,
    n_delta: int,
) -> None:
    if n_delta < 3 or n_delta % 2 == 0:
        raise ValueError("n_delta must be odd and >= 3")
    delta_max = delta_multiple * math.radians(mosaic_arcsec / 3600.0)
    deltas = [-delta_max + 2.0 * delta_max * i / (n_delta - 1) for i in range(n_delta)]
    rows: list[dict[str, Any]] = []
    for ring in rings:
        theta_b = bragg_angle_rad(511.0, ring.d_spacing_a)
        for delta in deltas:
            probs = darwin_mosaic_probabilities(
                energy_keV=511.0,
                material=ring.material,
                h=ring.h,
                k=ring.k,
                l=ring.l,
                mosaic_fwhm_arcsec=mosaic_arcsec,
                thickness_mm=ring.thickness_mm,
                crystallite_thickness_um=crystallite_um,
                delta_theta_rad=delta,
            )
            rows.append(
                {
                    "E_keV": "511",
                    "theta_B_rad": f"{theta_b:.12g}",
                    "delta_theta_rad": f"{delta:.12g}",
                    "material": ring.material,
                    "h": ring.h,
                    "k": ring.k,
                    "l": ring.l,
                    "mosaic_fwhm_arcmin": f"{mosaic_arcsec / 60.0:.9g}",
                    "thickness_mm": f"{ring.thickness_mm:.9g}",
                    "p_diff": f"{probs.p_diff:.12g}",
                    "p_abs": f"{probs.p_abs:.12g}",
                    "p_trans": f"{probs.p_trans:.12g}",
                    "source": probs.source,
                }
            )
    write_csv(path, rows)


def plot_scan(rows: list[dict[str, Any]], outdir: Path) -> None:
    by_focal: dict[float, dict[str, Any]] = {}
    for row in rows:
        focal = float(row["focal_length_m"])
        if focal not in by_focal or float(row["estimated_optics_effective_area_cm2"]) > float(by_focal[focal]["estimated_optics_effective_area_cm2"]):
            by_focal[focal] = row
    ordered = [by_focal[k] for k in sorted(by_focal)]
    x = [float(r["focal_length_m"]) for r in ordered]
    aeff = [float(r["estimated_optics_effective_area_cm2"]) for r in ordered]
    t3 = [float(r["T3_days_ref_atm_flux_1e_minus_4"]) for r in ordered]

    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    ax.plot(x, aeff, marker="o", lw=1.5)
    ax.axhline(50.89, color="#b91c1c", ls="--", lw=1.1, label="CAM511 channel Aeff reference")
    ax.set_xlabel("focal length (m)")
    ax.set_ylabel("estimated 511 keV Laue optics Aeff (cm$^2$)")
    ax.set_title("Best Ge multi-hkl 511 keV Laue throughput by focal length")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(outdir / "best_aeff_by_focal_length.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    ax.plot(x, t3, marker="o", lw=1.5, color="#4C78A8")
    ax.set_yscale("log")
    ax.set_xlabel("focal length (m)")
    ax.set_ylabel("3-sigma exposure for 1e-4 flux, ref atmosphere (days)")
    ax.set_title("Estimated 511 keV line detectability from geometry scan")
    ax.grid(True, which="both", alpha=0.25)
    fig.tight_layout()
    fig.savefig(outdir / "best_t3_by_focal_length.png", dpi=220)
    plt.close(fig)


def write_readme(outdir: Path, best: dict[str, Any], selected_config: Path, selected_table: Path) -> None:
    lines = [
        "# 511 keV Laue Geometry Optimization",
        "",
        "Status: `GEOMETRY_SCAN_PASS_WITH_GEANT4_READY_CONFIG`",
        "",
        "This scan changes the Laue geometry target from the historical 480-550 keV Ge(111) broad-band scaffold to a monochromatic 511 keV point-source lens.  Because one Ge(111) ring alone cannot provide enough 511 keV throughput at fixed focal length, the scan allows multiple Ge hkl rings at 511 keV and constrains square tile size by both adjacent-ring non-overlap and the mosaic Bragg-acceptance width.",
        "",
        "## Selected Candidate",
        "",
        "| metric | value |",
        "|---|---:|",
        f"| focal length | {float(best['focal_length_m']):.3g} m |",
        f"| rings | {int(best['n_rings'])} |",
        f"| hkls | {best['hkls']} |",
        f"| outer diameter | {float(best['outer_diameter_cm']):.3g} cm |",
        f"| geometric crystal area | {float(best['geometric_crystal_area_cm2']):.3g} cm2 |",
        f"| estimated optics Aeff | {float(best['estimated_optics_effective_area_cm2']):.3g} cm2 |",
        f"| assumed detector survival for 511 keV line | {float(best['detector_survival_511_assumed']):.3g} |",
        f"| estimated detector response | {float(best['estimated_detector_response_cps_per_ph_cm2_s']):.3g} cps/(ph cm^-2 s^-1) |",
        f"| 3sigma time, flux=1e-4, ref atmosphere | {float(best['T3_days_ref_atm_flux_1e_minus_4']):.3g} d |",
        "",
        "## Interpretation",
        "",
        "- The old 12 m Ge(111) 480-550 keV scaffold is not a fair 511 keV line-optimized lens: only its 511 keV ring contributes to the narrow line response.",
        "- The selected multi-hkl design is still a scaffold: it uses the local opticsim Darwin mosaic model and square crystals.  A rectangular-tile implementation could raise area further by keeping the radial width within Bragg acceptance while increasing tangential length.",
        "- The detectability numbers in this report are pre-Geant4-detector estimates using the current measured 511 keV detector survival from the existing replay.  The generated config and efficiency table are ready for `laue_multiring_table_demo` validation.",
        "",
        "## Files",
        "",
        "- `geometry_scan.csv`",
        "- `best_candidates.csv`",
        "- `best_aeff_by_focal_length.png`",
        "- `best_t3_by_focal_length.png`",
        f"- `{selected_config.relative_to(ROOT)}`",
        f"- `{selected_table.relative_to(ROOT)}`",
    ]
    (outdir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--config-dir", type=Path, default=DEFAULT_CONFIG_DIR)
    parser.add_argument("--focal-min-m", type=float, default=6.0)
    parser.add_argument("--focal-max-m", type=float, default=18.0)
    parser.add_argument("--focal-step-m", type=float, default=0.5)
    parser.add_argument("--max-radius-mm", type=float, default=155.0, help="Current Geant4 world-safe radial limit.")
    parser.add_argument("--min-radius-mm", type=float, default=20.0)
    parser.add_argument("--max-hkl-index", type=int, default=8)
    parser.add_argument("--mosaic-arcsec", type=float, default=30.0)
    parser.add_argument("--crystallite-um", type=float, default=5.0)
    parser.add_argument("--min-pdiff", type=float, default=0.03)
    parser.add_argument("--radial-fwhm-fraction", type=float, default=0.80)
    parser.add_argument("--radial-gap-fraction", type=float, default=0.80)
    parser.add_argument("--min-tile-mm", type=float, default=0.8)
    parser.add_argument("--max-tile-mm", type=float, default=5.0)
    parser.add_argument("--flux-anchor", type=float, default=1.0e-4)
    parser.add_argument("--select-rank", type=int, default=1)
    parser.add_argument("--delta-multiple", type=float, default=4.0)
    parser.add_argument("--n-delta", type=int, default=81)
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    args.config_dir.mkdir(parents=True, exist_ok=True)

    detector_survival = current_511_detector_survival(DEFAULT_REPLAY, DEFAULT_PER_RING)
    background_cps = line_background_cps(DEFAULT_BACKGROUND)
    candidates = build_hkl_candidates(
        max_index=args.max_hkl_index,
        mosaic_arcsec=args.mosaic_arcsec,
        crystallite_um=args.crystallite_um,
        min_pdiff=args.min_pdiff,
    )
    if not candidates:
        raise RuntimeError("no Ge hkl candidates survived the scan filters")

    rows: list[dict[str, Any]] = []
    designs: list[tuple[dict[str, Any], list[RingDesign]]] = []
    n_steps = int(round((args.focal_max_m - args.focal_min_m) / args.focal_step_m)) + 1
    for i in range(n_steps):
        focal_m = args.focal_min_m + i * args.focal_step_m
        focal_mm = focal_m * 1000.0
        rings = design_for_focal_length(
            candidates,
            focal_mm=focal_mm,
            max_radius_mm=args.max_radius_mm,
            min_radius_mm=args.min_radius_mm,
            mosaic_arcsec=args.mosaic_arcsec,
            radial_fwhm_fraction=args.radial_fwhm_fraction,
            radial_gap_fraction=args.radial_gap_fraction,
            min_tile_mm=args.min_tile_mm,
            max_tile_mm=args.max_tile_mm,
        )
        if not rings:
            continue
        summary = summarize_design(
            rings,
            focal_mm=focal_mm,
            detector_survival_511=detector_survival,
            background_cps=background_cps,
            flux_anchor=args.flux_anchor,
        )
        rows.append(summary)
        designs.append((summary, rings))

    if not designs:
        raise RuntimeError("no feasible focal-length designs survived the scan filters")

    designs.sort(key=lambda item: item[0]["estimated_detector_response_cps_per_ph_cm2_s"], reverse=True)
    selected_index = max(0, min(args.select_rank - 1, len(designs) - 1))
    best, best_rings = designs[selected_index]

    write_csv(args.outdir / "geometry_scan.csv", rows)
    write_csv(args.outdir / "best_candidates.csv", [summary for summary, _ in designs[:10]])
    plot_scan(rows, args.outdir)

    focal_tag = f"f{float(best['focal_length_m']):.1f}m".replace(".", "p")
    hkl_tag = "_".join(f"ge{r.h}{r.k}{r.l}" for r in best_rings)
    selected_config = args.config_dir / f"laue_511_mono_{hkl_tag}_{focal_tag}_square.csv"
    selected_table = args.config_dir / f"laue_511_mono_{hkl_tag}_{focal_tag}_efficiency.csv"
    selected_summary = args.config_dir / f"laue_511_mono_{hkl_tag}_{focal_tag}_summary.json"
    write_ring_config(selected_config, best_rings)
    write_efficiency_table(
        selected_table,
        best_rings,
        mosaic_arcsec=args.mosaic_arcsec,
        crystallite_um=args.crystallite_um,
        delta_multiple=args.delta_multiple,
        n_delta=args.n_delta,
    )

    ring_rows = [
        {
            "ring_id": r.ring_id,
            "material": r.material,
            "hkl": f"{r.h}{r.k}{r.l}",
            "radius_mm": r.radius_mm,
            "tile_size_mm": r.tile_size_mm,
            "n_tiles": r.n_tiles,
            "area_cm2": r.area_cm2,
            "p_diff": r.p_diff,
            "p_abs": r.p_abs,
            "p_trans": r.p_trans,
            "thickness_mm": r.thickness_mm,
        }
        for r in best_rings
    ]
    summary = {
        "status": "PASS",
        "claim_level": "LAUE_511_MONO_GEOMETRY_OPTIMIZATION_PRE_GEANT4_DETECTOR_ESTIMATE",
        "selected": best,
        "ring_rows": ring_rows,
        "scan_assumptions": {
            "energy_keV": 511.0,
            "material": "Ge",
            "mosaic_arcsec": args.mosaic_arcsec,
            "crystallite_um": args.crystallite_um,
            "radial_fwhm_fraction": args.radial_fwhm_fraction,
            "radial_gap_fraction": args.radial_gap_fraction,
            "square_tile_constraint": True,
            "max_radius_mm": args.max_radius_mm,
            "min_tile_mm": args.min_tile_mm,
            "max_tile_mm": args.max_tile_mm,
            "reference_T_atm_511": REFERENCE_T_ATM_511,
            "background_line_cps": background_cps,
            "detector_survival_511_from_current_replay": detector_survival,
        },
        "outputs": {
            "scan_csv": str(args.outdir / "geometry_scan.csv"),
            "best_candidates_csv": str(args.outdir / "best_candidates.csv"),
            "selected_ring_config": str(selected_config),
            "selected_efficiency_table": str(selected_table),
        },
    }
    selected_summary.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (args.outdir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_readme(args.outdir, best, selected_config, selected_table)
    print(json.dumps({"status": "PASS", "selected": best, "config": str(selected_config)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
