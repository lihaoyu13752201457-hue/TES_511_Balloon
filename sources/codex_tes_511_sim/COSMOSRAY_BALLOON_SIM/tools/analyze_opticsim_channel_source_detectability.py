#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build source detectability tables for the current opticsim channel route."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/codex_tes_511_matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import analyze_opticsim_source_detectability as base  # noqa: E402


DEFAULT_REPLAY = ROOT / "reports_260516/opticsim_channel_wallbywall_511_replay_20260521/summary.json"
DEFAULT_OUT = ROOT / "reports_260516/opticsim_channel_wallbywall_511_source_detectability_20260521"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", type=Path, default=DEFAULT_REPLAY)
    parser.add_argument("--diffuse", type=Path, default=base.DEFAULT_DIFFUSE)
    parser.add_argument("--transmission", type=Path, default=base.DEFAULT_TRANS)
    parser.add_argument("--background", type=Path, default=base.DEFAULT_BACKGROUND)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--label",
        default="current public-geometry wall-by-wall 511 keV channel optics detector replay",
    )
    return parser.parse_args()


def optics_area_summary(replay: dict[str, Any]) -> tuple[float, float]:
    if "estimated_channel_optics_effective_area_cm2" in replay:
        return (
            float(replay["estimated_channel_optics_effective_area_cm2"]),
            float(replay["channel_aperture_area_cm2"]),
        )
    channel = replay.get("channel", {})
    return (
        float(channel["effective_area_cm2"]),
        float(channel["aperture_area_cm2"]),
    )


def literature_audit_rows(replay: dict[str, Any]) -> list[dict[str, Any]]:
    fov_radius_deg = 0.0745
    omega_sr, area_deg2 = base.fov_solid_angle(fov_radius_deg)
    optics_aeff, aperture_area = optics_area_summary(replay)
    channel = replay.get("channel", {})
    return [
        {
            "item": "SPI total Galactic 511-keV line flux",
            "value": "2.74e-3 ph cm^-2 s^-1",
            "reference": "Siegert et al. 2016 A&A 586 A84 / arXiv:1512.00325",
            "usage": "context only; not a point-source input",
            "status": "OK",
        },
        {
            "item": "SPI central point-like model component",
            "value": "8.0e-5 +/- 1.9e-5 ph cm^-2 s^-1",
            "reference": "Siegert et al. 2016 A&A 586 A84 / arXiv:1512.00325",
            "usage": "point-source flux-scan anchor; identity not confirmed",
            "status": "OK_WITH_CAVEAT",
        },
        {
            "item": "SPI bulge and disk diffuse flux",
            "value": "bulge 0.96e-3; disk 1.66e-3 ph cm^-2 s^-1",
            "reference": "Siegert et al. 2016 A&A 586 A84 / arXiv:1512.00325",
            "usage": "diffuse FoV aperture integral, not on-axis point source",
            "status": "OK",
        },
        {
            "item": "FoV solid angle",
            "value": f"radius 0.0745 deg = 4.47 arcmin; Omega {omega_sr:.6e} sr; area {area_deg2:.6e} deg2",
            "reference": "CAM511 FoV radius carried in local CAM511-derived source model",
            "usage": "diffuse aperture fraction",
            "status": "OK_SMALL_FOV",
        },
        {
            "item": "Atmospheric transmission",
            "value": f"reference T_atm={base.REFERENCE_T_ATM_511}",
            "reference": "reports/phase2_real_flight_physical_production/environment_grid_real/science_atmospheric_transmission.csv",
            "usage": "multiply top-of-atmosphere literature flux before detector response",
            "status": "OK",
        },
        {
            "item": "Current channel effective area",
            "value": f"{optics_aeff:.6g} cm2 estimated optics Aeff; aperture area {aperture_area:.6g} cm2; transmissivity {float(channel.get('transmissivity', math.nan)):.6g}",
            "reference": "local opticsim channel_wallbywall_rebuild summary",
            "usage": "current channel scaffold normalization",
            "status": "LIMITED_PUBLIC_GEOMETRY_RECONSTRUCTION",
        },
    ]


def plot_point(rows: list[dict[str, Any]], outdir: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.3, 4.8))
    for window, color in [("broad_480_550", "#4C78A8"), ("line_510p3_511p8", "#F58518")]:
        use = [r for r in rows if r["window"] == window]
        x = [float(r["flux_top_of_atmosphere_ph_cm2_s"]) for r in use]
        y = [float(r["T3_days_ref_atm"]) for r in use]
        ax.plot(x, y, marker="o", ms=3.5, lw=1.4, color=color, label=f"{window}, T_atm ref")
    ax.axvline(8.0e-5, color="#54A24B", ls="--", lw=1.2, label="SPI central compact anchor")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("top-of-atmosphere point-source flux (ph cm$^{-2}$ s$^{-1}$)")
    ax.set_ylabel("3-sigma exposure (days)")
    ax.set_title("Current channel point-source flux scan")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(outdir / "point_source_flux_scan_current_channel.png", dpi=200)
    plt.close(fig)


def plot_diffuse(rows: list[dict[str, Any]], outdir: Path) -> None:
    use = [
        r
        for r in rows
        if r["window"] == "broad_480_550" and not str(r["source_case"]).startswith("INVALID")
    ]
    labels = [str(r["source_case"]).replace("bulge_gaussian_", "bulge_").replace("_", "\n") for r in use]
    years = [float(r["T3_years_ref_atm"]) for r in use]
    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    ax.bar(labels, years, color="#4C78A8")
    ax.set_yscale("log")
    ax.set_ylabel("3-sigma exposure with reference atmosphere (years)")
    ax.set_title("Diffuse 511-keV flux intercepted by the 4.47 arcmin FoV")
    ax.grid(True, axis="y", which="both", alpha=0.25)
    ax.tick_params(axis="x", labelsize=8)
    fig.tight_layout()
    fig.savefig(outdir / "diffuse_fov_detectability_current_channel.png", dpi=200)
    plt.close(fig)


def find_point(rows: list[dict[str, Any]], window: str, flux: float) -> dict[str, Any]:
    for row in rows:
        if row["window"] == window and abs(float(row["flux_top_of_atmosphere_ph_cm2_s"]) - flux) < flux * 1.0e-9:
            return row
    raise KeyError((window, flux))


def find_diff(rows: list[dict[str, Any]], case: str, window: str = "broad_480_550") -> dict[str, Any]:
    for row in rows:
        if row["source_case"] == case and row["window"] == window:
            return row
    raise KeyError((case, window))


def write_readme(
    outdir: Path,
    point_rows: list[dict[str, Any]],
    diffuse_rows: list[dict[str, Any]],
    audit_rows: list[dict[str, Any]],
    trans: dict[int, dict[str, float]],
    label: str,
    replay: dict[str, Any],
) -> None:
    t_values = [float(v["T_atm_511"]) for v in trans.values()]
    anchor = find_point(point_rows, "broad_480_550", 8.0e-5)
    p1e4 = find_point(point_rows, "broad_480_550", 1.0e-4)
    line_anchor = find_point(point_rows, "line_510p3_511p8", 8.0e-5)
    line_p1e4 = find_point(point_rows, "line_510p3_511p8", 1.0e-4)
    default_diff = find_diff(diffuse_rows, "B_default_bulge8deg_plus_disk")
    wrong = find_diff(diffuse_rows, "INVALID_total_bulge8deg_plus_disk_treated_as_point_source")
    optics_aeff, aperture_area = optics_area_summary(replay)
    lines = [
        "# Current Opticsim Channel Source Detectability",
        "",
        "Status: `PASS_WITH_EXPLICIT_CAVEATS`",
        "",
        f"This report recalculates point-source and diffuse-source detectability using `{label}`. Literature fluxes are top-of-atmosphere astrophysical fluxes and are multiplied by atmospheric transmission before detector-response counting.",
        "",
        "## Source And Geometry Audit",
        "",
        "| item | value | usage | status |",
        "|---|---|---|---|",
    ]
    for row in audit_rows:
        lines.append(f"| {row['item']} | {row['value']} | {row['usage']} | {row['status']} |")
    lines.extend(
        [
            "",
            "## Atmospheric Transmission",
            "",
            f"- Reference `T_atm_511`: `{base.REFERENCE_T_ATM_511:.6g}`.",
            f"- Time grid `T_atm_511` range: `{min(t_values):.6g}` to `{max(t_values):.6g}`.",
            "- The time-dependent table uses the actual `T_atm_511 * earth_occultation_factor` in each trajectory bin.",
            "",
            "## Current Point-Source Scan",
            "",
            "| case | window | flux top-of-atm | T3 no atmosphere | T3 reference atmosphere | T3 time-dependent avg extrapolated |",
            "|---|---|---:|---:|---:|---:|",
            f"| SPI central compact anchor | 480-550 | 8e-5 | {float(anchor['T3_days_no_atm']):.4g} d | {float(anchor['T3_days_ref_atm']):.4g} d | {float(anchor['td_T3_days_avg_extrapolated']):.4g} d |",
            f"| generic point | 480-550 | 1e-4 | {float(p1e4['T3_days_no_atm']):.4g} d | {float(p1e4['T3_days_ref_atm']):.4g} d | {float(p1e4['td_T3_days_avg_extrapolated']):.4g} d |",
            f"| SPI central compact anchor | 510.3-511.8 | 8e-5 | {float(line_anchor['T3_days_no_atm']):.4g} d | {float(line_anchor['T3_days_ref_atm']):.4g} d | {float(line_anchor['td_T3_days_avg_extrapolated']):.4g} d |",
            f"| generic point | 510.3-511.8 | 1e-4 | {float(line_p1e4['T3_days_no_atm']):.4g} d | {float(line_p1e4['T3_days_ref_atm']):.4g} d | {float(line_p1e4['td_T3_days_avg_extrapolated']):.4g} d |",
            "",
            "## Diffuse Source",
            "",
            "| case | window | total flux | FoV flux | FoV fraction | T3 reference atmosphere |",
            "|---|---|---:|---:|---:|---:|",
            f"| default SPI bulge8+disk | 480-550 | {float(default_diff['total_flux_top_of_atmosphere_ph_cm2_s']):.4g} | {float(default_diff['fov_flux_top_of_atmosphere_ph_cm2_s']):.4g} | {float(default_diff['fov_fraction']):.4g} | {float(default_diff['T3_years_ref_atm']):.4g} yr |",
            f"| invalid total-flux-as-point comparison | 480-550 | {float(wrong['total_flux_top_of_atmosphere_ph_cm2_s']):.4g} | {float(wrong['fov_flux_top_of_atmosphere_ph_cm2_s']):.4g} | 1 | {float(wrong['T3_days_ref_atm']):.4g} d |",
            "",
            "The invalid row is intentionally included only as a warning: it collapses a many-degree diffuse sky distribution into an on-axis point source and must not be used as the diffuse detectability claim.",
            "",
            "## Claim Control",
            "",
            f"The current channel route uses `{optics_aeff:.4g} cm2` estimated optics effective area over `{aperture_area:.4g} cm2` aperture area. It is a wall-by-wall public-geometry reconstruction plus XZTES detector replay, not the unpublished original 511-CAM IDL/IMD model.",
            "",
            "## Files",
            "",
            "- `point_source_flux_scan_current_channel.csv`",
            "- `diffuse_source_detectability_current_channel.csv`",
            "- `source_geometry_atmosphere_audit.csv`",
            "- `point_source_flux_scan_current_channel.png`",
            "- `diffuse_fov_detectability_current_channel.png`",
        ]
    )
    (outdir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    replay = base.load_json(args.replay)
    responses = base.response_table(replay)
    bg = base.background_by_window(args.background)
    trans = base.transmission_by_bin(args.transmission)
    point_rows = base.build_point_rows(responses, bg, trans)
    diffuse_rows = base.build_diffuse_rows(args.diffuse, responses, bg, trans)
    audit_rows = literature_audit_rows(replay)

    base.write_csv(args.outdir / "point_source_flux_scan_current_channel.csv", point_rows)
    base.write_csv(args.outdir / "diffuse_source_detectability_current_channel.csv", diffuse_rows)
    base.write_csv(args.outdir / "source_geometry_atmosphere_audit.csv", audit_rows)
    plot_point(point_rows, args.outdir)
    plot_diffuse(diffuse_rows, args.outdir)

    t_values = [float(v["T_atm_511"]) for v in trans.values()]
    summary = {
        "status": "PASS_WITH_EXPLICIT_CAVEATS",
        "claim_level": "CURRENT_OPTICSIM_CHANNEL_SOURCE_DETECTABILITY_COUNTING_NOT_PROFILED_FINAL",
        "optics_label": args.label,
        "inputs": {
            "replay_summary": str(args.replay),
            "diffuse_aperture": str(args.diffuse),
            "atmospheric_transmission": str(args.transmission),
            "background_time_variation": str(args.background),
        },
        "responses": responses,
        "reference_T_atm_511": base.REFERENCE_T_ATM_511,
        "time_grid_T_atm_min": min(t_values),
        "time_grid_T_atm_max": max(t_values),
        "point_rows": len(point_rows),
        "diffuse_rows": len(diffuse_rows),
        "key_results": {
            "point_broad_8e_minus_5_ref_atm_T3_days": next(
                float(r["T3_days_ref_atm"])
                for r in point_rows
                if r["window"] == "broad_480_550"
                and abs(float(r["flux_top_of_atmosphere_ph_cm2_s"]) - 8.0e-5) < 1e-12
            ),
            "point_broad_1e_minus_4_ref_atm_T3_days": next(
                float(r["T3_days_ref_atm"])
                for r in point_rows
                if r["window"] == "broad_480_550"
                and abs(float(r["flux_top_of_atmosphere_ph_cm2_s"]) - 1.0e-4) < 1e-12
            ),
            "point_line_8e_minus_5_ref_atm_T3_days": next(
                float(r["T3_days_ref_atm"])
                for r in point_rows
                if r["window"] == "line_510p3_511p8"
                and abs(float(r["flux_top_of_atmosphere_ph_cm2_s"]) - 8.0e-5) < 1e-12
            ),
            "point_line_1e_minus_4_ref_atm_T3_days": next(
                float(r["T3_days_ref_atm"])
                for r in point_rows
                if r["window"] == "line_510p3_511p8"
                and abs(float(r["flux_top_of_atmosphere_ph_cm2_s"]) - 1.0e-4) < 1e-12
            ),
            "diffuse_default_broad_ref_atm_T3_years": next(
                float(r["T3_years_ref_atm"])
                for r in diffuse_rows
                if r["source_case"] == "B_default_bulge8deg_plus_disk" and r["window"] == "broad_480_550"
            ),
            "diffuse_default_line_ref_atm_T3_years": next(
                float(r["T3_years_ref_atm"])
                for r in diffuse_rows
                if r["source_case"] == "B_default_bulge8deg_plus_disk" and r["window"] == "line_510p3_511p8"
            ),
        },
        "caveats": [
            "Literature fluxes are top-of-atmosphere/source fluxes; reference and time-dependent atmospheric attenuation are applied explicitly.",
            "Diffuse rows use the existing 4.47 arcmin FoV aperture integral and on-axis channel response as an upper-bound scaffold, not a full off-axis diffuse focal map.",
            "Point rows are full-window counting numbers for the new channel replay, not optimized profile-likelihood sensitivity.",
            "The channel optics is a public-geometry wall-by-wall reconstruction, not the unpublished original 511-CAM IDL/IMD model.",
        ],
    }
    (args.outdir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_readme(args.outdir, point_rows, diffuse_rows, audit_rows, trans, args.label, replay)
    print(json.dumps({"status": summary["status"], "summary": str(args.outdir / "summary.json")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
