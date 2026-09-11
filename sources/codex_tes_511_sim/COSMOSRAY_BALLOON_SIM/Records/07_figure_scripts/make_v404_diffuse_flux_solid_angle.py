#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate V404 and diffuse-source flux/solid-angle definition records."""

from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/codex_tes_511_matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Ellipse, FancyArrowPatch, Polygon, Rectangle


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "Records/02_point_diffuse_source_model"
DATE_TAG = "20260522"

DIFFUSE_TABLE = ROOT / "reports2.0/09_SOURCE_CASES_ABC/diffuse_aperture_foreground.csv"
V404_BANDPASS = ROOT / "reports2.0/09_SOURCE_CASES_ABC/v404_bandpass_loss.csv"
LAUE_V404_SCAN = ROOT / "Records/05_laue_current_mainline/source_significance_time_dependent_20260522/v404_flux_scan_time_dependent.csv"
CHANNEL_V404_SCAN = ROOT / "Records/06_channel_current_mainline/source_significance_time_dependent_20260522/v404_flux_scan_time_dependent.csv"

SCHEMATIC = OUT_DIR / f"v404_diffuse_flux_solid_angle_schematic_{DATE_TAG}.png"
SUMMARY_JSON = OUT_DIR / f"v404_diffuse_flux_solid_angle_summary_{DATE_TAG}.json"
SUMMARY_CSV = OUT_DIR / f"v404_diffuse_flux_solid_angle_table_{DATE_TAG}.csv"
README_MD = OUT_DIR / f"v404_diffuse_flux_solid_angle_{DATE_TAG}.md"

FOV_RADIUS_DEG = 0.0745
FOV_RADIUS_ARCMIN = FOV_RADIUS_DEG * 60.0

V404_LITERATURE = [
    {
        "orbit": "1554",
        "feature": "thermal pair annihilation",
        "flux_ph_cm2_s": 1.9e-3,
        "flux_unc_ph_cm2_s": 1.2e-3,
        "kT_keV": 29.0,
        "kT_unc_keV": 14.0,
        "local_proxy": "v404_kT30_no_shift",
        "basis": "Siegert et al. 2016 Nature/arXiv:1603.01169 Extended Data Table 1",
    },
    {
        "orbit": "1555",
        "feature": "thermal pair annihilation",
        "flux_ph_cm2_s": 6.5e-3,
        "flux_unc_ph_cm2_s": 1.6e-3,
        "kT_keV": 173.0,
        "kT_unc_keV": 46.0,
        "local_proxy": "v404_kT170_no_shift",
        "basis": "Siegert et al. 2016 Nature/arXiv:1603.01169 Extended Data Table 1",
    },
    {
        "orbit": "1557",
        "feature": "thermal pair annihilation",
        "flux_ph_cm2_s": 1.2e-3,
        "flux_unc_ph_cm2_s": 0.9e-3,
        "kT_keV": 2.0,
        "kT_unc_keV": 1.0,
        "local_proxy": "redshifted narrow/broad stress proxy",
        "basis": "Siegert et al. 2016 Nature/arXiv:1603.01169 Extended Data Table 1",
    },
    {
        "orbit": "1557a",
        "feature": "redshifted second 511 feature",
        "flux_ph_cm2_s": 1.5e-3,
        "flux_unc_ph_cm2_s": 0.5e-3,
        "centroid_keV": 458.0,
        "centroid_unc_keV": 25.0,
        "kT_keV": 4.0,
        "kT_unc_keV": 3.0,
        "local_proxy": "v404_redshift_z0p10_narrow_proxy",
        "basis": "Siegert et al. 2016 Nature/arXiv:1603.01169 Extended Data Table 5",
    },
    {
        "orbit": "1557b",
        "feature": "ortho-positronium/redshifted alternative",
        "flux_ph_cm2_s": 5.3e-3,
        "flux_unc_ph_cm2_s": 1.9e-3,
        "centroid_keV": 466.0,
        "local_proxy": "v404_redshift_z0p10_broad_proxy",
        "basis": "Siegert et al. 2016 Nature/arXiv:1603.01169 Extended Data Table 5",
    },
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def f(row: dict[str, str], key: str, default: float = float("nan")) -> float:
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def fmt(value: Any, digits: int = 4) -> str:
    try:
        val = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(val):
        return "nan"
    return f"{val:.{digits}g}"


def fov_solid_angle(radius_deg: float) -> tuple[float, float]:
    theta = math.radians(radius_deg)
    return 2.0 * math.pi * (1.0 - math.cos(theta)), math.pi * radius_deg * radius_deg


def unique_fluxes(path: Path) -> list[float]:
    if not path.exists():
        return []
    values = {f(row, "input_flux_top_atm_ph_cm2_s") for row in read_csv(path)}
    return sorted(v for v in values if math.isfinite(v))


def build_summary() -> dict[str, Any]:
    diffuse_rows = read_csv(DIFFUSE_TABLE)
    v404_rows = read_csv(V404_BANDPASS)
    omega_sr, area_deg2 = fov_solid_angle(FOV_RADIUS_DEG)

    diffuse_by_model = {row["sky_model"]: row for row in diffuse_rows}
    default_total = f(diffuse_by_model["bulge_gaussian_fwhm_8deg"], "total_flux_ph_cm2_s") + f(
        diffuse_by_model["disk_thick_gaussian"], "total_flux_ph_cm2_s"
    )
    default_fov = f(diffuse_by_model["bulge_gaussian_fwhm_8deg"], "fov_flux_ph_cm2_s") + f(
        diffuse_by_model["disk_thick_gaussian"], "fov_flux_ph_cm2_s"
    )
    default_fraction = default_fov / default_total

    laue_fluxes = unique_fluxes(LAUE_V404_SCAN)
    channel_fluxes = unique_fluxes(CHANNEL_V404_SCAN)
    scan_fluxes = sorted(set(laue_fluxes + channel_fluxes))

    return {
        "date": DATE_TAG,
        "fov": {
            "radius_deg": FOV_RADIUS_DEG,
            "radius_arcmin": FOV_RADIUS_ARCMIN,
            "solid_angle_sr": omega_sr,
            "small_angle_area_deg2": area_deg2,
            "definition": "Omega = 2*pi*(1-cos(theta)); theta is the local optics FoV radius.",
            "authority": "local current 4.47 arcmin optical-acceptance top-hat proxy, not the Be-window physical size and not an astrophysical source size",
            "production_rule": "Production diffuse folding should use front-optics A_eff(E, theta, phi) and PSF/focal-plane clipping; the present top-hat is only a documented proxy.",
        },
        "diffuse": {
            "literature_flux_basis": "Siegert et al. 2016 A&A/arXiv:1512.00325",
            "local_aperture_table": str(DIFFUSE_TABLE.relative_to(ROOT)),
            "shape_caveat": "The local bulge_gaussian_fwhm_* and disk_thick_gaussian rows are FoV foreground proxies normalized to SPI fluxes; they are not claimed to be an exact re-fit of the SPI sky templates.",
            "models": diffuse_rows,
            "default_composite": {
                "components": ["bulge_gaussian_fwhm_8deg", "disk_thick_gaussian"],
                "total_flux_ph_cm2_s": default_total,
                "fov_flux_ph_cm2_s": default_fov,
                "fov_fraction": default_fraction,
            },
            "handling": "aperture/FoV integral foreground; not a Cosima focal-spot source",
        },
        "v404": {
            "literature_flux_basis": "Siegert et al. 2016 Nature/arXiv:1603.01169",
            "source_solid_angle_policy": "point-source benchmark: one sky direction; no finite source solid-angle integral",
            "local_bandpass_table": str(V404_BANDPASS.relative_to(ROOT)),
            "literature_anchors": V404_LITERATURE,
            "scan_fluxes_top_atm_ph_cm2_s": scan_fluxes,
            "scan_min_ph_cm2_s": scan_fluxes[0] if scan_fluxes else None,
            "scan_max_ph_cm2_s": scan_fluxes[-1] if scan_fluxes else None,
            "scan_outputs": {
                "laue": str(LAUE_V404_SCAN.relative_to(ROOT)),
                "channel": str(CHANNEL_V404_SCAN.relative_to(ROOT)),
            },
            "bandpass_rows": v404_rows,
        },
        "atmosphere_policy": "Literature/source-case fluxes are treated as top-of-atmosphere photon fluxes and multiplied by T_atm_511(t) in the time-dependent significance records.",
        "laue_channel_fov_policy": {
            "current_numeric_policy": "Laue and Channel both use the same 4.47 arcmin front-optics top-hat FoV proxy for diffuse aperture flux.",
            "current_numeric_difference": "none in the diffuse aperture flux itself; route differences enter through the on-axis/scalar optics response used downstream.",
            "production_physics_difference": "real Laue and Channel off-axis A_eff/PSF/focal-map responses can differ and should be installed before production diffuse imaging claims.",
            "materiality_to_current_conclusion": "not material for the current source-significance conclusion: V404/point-source benchmarks are on-axis, and the default diffuse FoV flux is orders below point-source anchors.",
            "decision": "do not change current numerical chain; record as a response-model limitation and future production requirement.",
        },
    }


def build_table(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    fov = summary["fov"]
    rows += [
        {
            "case": "B_GC_DIFFUSE_BULGE_DISK",
            "quantity": "FoV_radius",
            "value": fov["radius_arcmin"],
            "unit": "arcmin",
            "basis": "local optics/FoV reference aperture",
            "local_use": "sets aperture solid angle for diffuse sky integration",
        },
        {
            "case": "B_GC_DIFFUSE_BULGE_DISK",
            "quantity": "FoV_solid_angle",
            "value": fov["solid_angle_sr"],
            "unit": "sr",
            "basis": "Omega = 2*pi*(1-cos(theta))",
            "local_use": "integral over sky brightness inside pointed FoV",
        },
    ]
    diffuse = summary["diffuse"]
    for model in diffuse["models"]:
        rows.append(
            {
                "case": "B_GC_DIFFUSE_BULGE_DISK",
                "quantity": model["sky_model"],
                "value": model["fov_flux_ph_cm2_s"],
                "unit": "ph cm^-2 s^-1",
                "basis": "Siegert et al. Milky-Way 511-keV flux folded by local Gaussian/FoV model",
                "local_use": "FoV aperture foreground flux",
            }
        )
    rows.append(
        {
            "case": "B_GC_DIFFUSE_BULGE_DISK",
            "quantity": "default_bulge8_plus_disk_fov_flux",
            "value": diffuse["default_composite"]["fov_flux_ph_cm2_s"],
            "unit": "ph cm^-2 s^-1",
            "basis": "bulge total 0.96e-3 + disk total 1.7e-3 from Siegert et al.; local FoV aperture model",
            "local_use": "default diffuse source in time-dependent 3sigma records",
        }
    )
    for row in summary["v404"]["literature_anchors"]:
        rows.append(
            {
                "case": "C_V404_2015_TRANSIENT_BENCHMARK",
                "quantity": f"orbit_{row['orbit']}_{row['feature']}",
                "value": row["flux_ph_cm2_s"],
                "uncertainty": row["flux_unc_ph_cm2_s"],
                "unit": "ph cm^-2 s^-1",
                "basis": row["basis"],
                "local_use": row["local_proxy"],
            }
        )
    scan = summary["v404"]["scan_fluxes_top_atm_ph_cm2_s"]
    rows.append(
        {
            "case": "C_V404_2015_TRANSIENT_BENCHMARK",
            "quantity": "local_flux_scan",
            "value": ",".join(fmt(v, 5) for v in scan),
            "unit": "ph cm^-2 s^-1",
            "basis": "literature-motivated transient flux grid; extended to include the 6.5e-3 orbit-1555 anchor",
            "local_use": "linear response rescale through Laue and channel optics significance records",
        }
    )
    for row in summary["v404"]["bandpass_rows"]:
        rows.append(
            {
                "case": "C_V404_2015_TRANSIENT_BENCHMARK",
                "quantity": f"{row['spectrum']}_bandpass_factor",
                "value": row["Aeff_weighted_fraction"],
                "unit": "dimensionless",
                "basis": "local placeholder optics bandpass folding table",
                "local_use": row["bandpass_status"],
            }
        )
    return rows


def draw_schematic(summary: dict[str, Any]) -> None:
    fig = plt.figure(figsize=(15, 8.2), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=[2.2, 1.05])
    ax_point = fig.add_subplot(gs[0, 0])
    ax_diff = fig.add_subplot(gs[0, 1])
    ax_notes = fig.add_subplot(gs[1, :])
    for ax in (ax_point, ax_diff, ax_notes):
        ax.set_axis_off()

    # Point-source side.
    ax_point.set_xlim(0, 10)
    ax_point.set_ylim(0, 7)
    ax_point.set_title("V404 benchmark: point-source flux scan", fontsize=15, weight="bold")
    ax_point.add_patch(Rectangle((4.35, 0.6), 0.45, 5.8, color="#BFD7EA", alpha=0.65))
    ax_point.text(4.58, 6.55, "atmosphere\nT_atm(t)", ha="center", va="top", fontsize=10)
    ax_point.add_patch(Ellipse((7.2, 3.5), 0.35, 4.8, facecolor="#6C9A8B", edgecolor="#345", lw=1.3))
    ax_point.text(7.2, 6.15, "front optics", ha="center", fontsize=10)
    ax_point.add_patch(Rectangle((8.65, 2.25), 0.12, 2.5, facecolor="#333", alpha=0.85))
    ax_point.text(8.82, 4.95, "focal\nplane", ha="left", fontsize=10)
    ax_point.scatter([1.1], [3.5], s=220, marker="*", color="#F58518", edgecolor="#6b3d00", zorder=4)
    ax_point.text(1.1, 4.15, "V404 Cygni\none sky direction", ha="center", fontsize=10)
    for y in [2.6, 3.1, 3.6, 4.1, 4.6]:
        ax_point.add_patch(FancyArrowPatch((1.45, y), (7.0, y), arrowstyle="->", mutation_scale=11, lw=1.4, color="#4C78A8"))
    cone = Polygon([[7.25, 2.2], [8.65, 3.2], [8.65, 3.8], [7.25, 4.8]], closed=True, facecolor="#F58518", alpha=0.14, edgecolor="#F58518")
    ax_point.add_patch(cone)
    ax_point.text(2.8, 1.08, "F_scan at top of atmosphere\n(no source solid-angle integral)", ha="center", fontsize=10)
    ax_point.text(6.55, 0.55, "R_sig(t) = F_scan x T_atm(t) x bandpass x response", ha="center", fontsize=10, color="#333")

    # Diffuse side.
    ax_diff.set_xlim(0, 10)
    ax_diff.set_ylim(0, 7)
    ax_diff.set_title("Diffuse bulge/disk: FoV aperture integral", fontsize=15, weight="bold")
    ax_diff.add_patch(Ellipse((2.7, 3.6), 3.2, 2.3, facecolor="#D6A03D", edgecolor="#8a651d", alpha=0.48, lw=1.4))
    ax_diff.add_patch(Ellipse((2.7, 3.6), 6.6, 0.82, facecolor="#72B7B2", edgecolor="#2b6864", alpha=0.38, lw=1.2))
    ax_diff.add_patch(Circle((2.7, 3.6), 0.22, facecolor="none", edgecolor="#C44E52", lw=2.0))
    ax_diff.text(2.7, 5.35, "Milky-Way 511 keV\nbulge + disk template", ha="center", fontsize=10)
    ax_diff.text(2.7, 2.62, "FoV radius\n4.47 arcmin", ha="center", fontsize=9, color="#C44E52")
    ax_diff.add_patch(Rectangle((6.35, 0.6), 0.45, 5.8, color="#BFD7EA", alpha=0.65))
    ax_diff.text(6.58, 6.55, "atmosphere\nT_atm(t)", ha="center", va="top", fontsize=10)
    ax_diff.add_patch(Ellipse((8.1, 3.5), 0.35, 4.8, facecolor="#6C9A8B", edgecolor="#345", lw=1.3))
    ax_diff.add_patch(Rectangle((9.18, 2.25), 0.12, 2.5, facecolor="#333", alpha=0.85))
    for y0 in [3.2, 3.6, 4.0]:
        ax_diff.add_patch(FancyArrowPatch((2.95, y0), (8.0, 3.5), arrowstyle="->", mutation_scale=10, lw=1.1, color="#4C78A8", alpha=0.8))
    ax_diff.text(5.25, 0.6, "F_FoV = integral_FoV I(l,b) dOmega\nnot a Be-window focal spot source", ha="center", fontsize=10, color="#333")

    v404 = summary["v404"]
    diffuse = summary["diffuse"]
    fov = summary["fov"]
    scan = v404["scan_fluxes_top_atm_ph_cm2_s"]
    v404_anchor_lines = [
        "V404 anchors from Siegert et al. 2016:",
        "orbit 1554: I_TPA = 1.9e-3, kT ~ 29 keV",
        "orbit 1555: I_TPA = 6.5e-3, kT ~ 173 keV",
        "orbit 1557: I_TPA = 1.2e-3; redshifted alternatives 1.5e-3 / 5.3e-3",
        f"local scan: {fmt(scan[0])} ... {fmt(scan[-1])} ph cm^-2 s^-1",
    ]
    diffuse_lines = [
        "Diffuse anchors from Siegert et al. 2016:",
        "bulge flux = 0.96e-3; disk flux ~ 1.7e-3 ph cm^-2 s^-1",
        f"FoV Omega = {fmt(fov['solid_angle_sr'])} sr; area = {fmt(fov['small_angle_area_deg2'])} deg^2",
        f"default bulge8+disk FoV flux = {fmt(diffuse['default_composite']['fov_flux_ph_cm2_s'])} ph cm^-2 s^-1",
        "FoV radius is a local optics setting, not an astrophysical source size.",
    ]
    ax_notes.text(0.02, 0.92, "\n".join(v404_anchor_lines), ha="left", va="top", fontsize=10.5, family="monospace")
    ax_notes.text(0.54, 0.92, "\n".join(diffuse_lines), ha="left", va="top", fontsize=10.5, family="monospace")
    ax_notes.add_patch(Rectangle((0.005, 0.05), 0.99, 0.9, transform=ax_notes.transAxes, fill=False, edgecolor="#CCCCCC", lw=1.0))

    fig.savefig(SCHEMATIC, dpi=190)
    plt.close(fig)


def write_markdown(summary: dict[str, Any]) -> None:
    fov = summary["fov"]
    diffuse = summary["diffuse"]
    v404 = summary["v404"]
    scan = v404["scan_fluxes_top_atm_ph_cm2_s"]
    lines = [
        "# V404 与弥散源的通量、立体角定义",
        "",
        f"更新时间：2026-05-22",
        "",
        f"![V404 and diffuse source definition]({SCHEMATIC.name})",
        "",
        "## 结论先行",
        "",
        "1. `C_V404_2015_TRANSIENT_BENCHMARK` 按点源/瞬变基准处理：只有一个天空方向，不做源本身的立体角积分。通量输入是文献启发的 feature flux scan，并在气球口径中按 `F_top_atm * T_atm_511(t)` 做大气透过修正。",
        "2. `B_GC_DIFFUSE_BULGE_DISK` 按弥散源处理：不能把全天/大尺度 bulge+disk 通量当点源。当前只积分进入光学 FoV 的小角锥，作为 aperture foreground；没有生成 Cosima focal-spot source。",
        "3. FoV 半径 `4.47 arcmin = 0.0745 deg` 应理解为当前本地前端光学 angular-acceptance 的 top-hat proxy，用于定义弥散源积分范围；它不是 Be 窗物理尺寸本身，也不是 V404 或银河弥散源论文给出的天体源大小。",
        "",
        "## V404 点源基准",
        "",
        "V404 的论文依据是 Siegert et al. 2016 的 INTEGRAL/SPI 结果。论文报告 V404 Cygni 2015 爆发期间 511 keV 附近出现可变正负电子湮没特征；本地只把它作为 transient flux/bandpass benchmark，不把它作为本项目科学目标。",
        "",
        "| orbit/model | literature flux | spectral anchor | local proxy |",
        "|---|---:|---:|---|",
    ]
    for row in V404_LITERATURE:
        spec = f"kT={fmt(row.get('kT_keV'))} keV" if "kT_keV" in row else f"centroid={fmt(row.get('centroid_keV'))} keV"
        lines.append(
            f"| {row['orbit']} {row['feature']} | {fmt(row['flux_ph_cm2_s'])} +/- {fmt(row['flux_unc_ph_cm2_s'])} ph cm^-2 s^-1 | {spec} | `{row['local_proxy']}` |"
        )
    lines += [
        "",
        "本地 V404 flux scan 已重生成，范围为：",
        "",
        f"`{', '.join(fmt(v, 5) for v in scan)} ph cm^-2 s^-1`",
        "",
        "这个范围现在覆盖到 `6.5e-3 ph cm^-2 s^-1` 的 orbit-1555 高通量锚点，并额外给到 `1e-2` 作为外推检查。对应输出：",
        "",
        f"- Laue: `{v404['scan_outputs']['laue']}`",
        f"- Channel: `{v404['scan_outputs']['channel']}`",
        "",
        "V404 的能窗折叠不是简单把全 feature flux 全算进 511 keV 线窗：",
        "",
        "| spectrum | Aeff-weighted fraction | fraction 480-550 | fraction 510.3-511.8 | status |",
        "|---|---:|---:|---:|---|",
    ]
    for row in v404["bandpass_rows"]:
        lines.append(
            f"| `{row['spectrum']}` | {fmt(row['Aeff_weighted_fraction'])} | {fmt(row['fraction_480_550'])} | {fmt(row['fraction_510p3_511p8'])} | {row['bandpass_status']} |"
        )
    lines += [
        "",
        "## 弥散源 FoV 积分",
        "",
        "弥散源的论文通量依据是 Siegert et al. 2016 对银河 511 keV emission 的 SPI 模型拟合：总 Galactic line flux 约 `2.7e-3 ph cm^-2 s^-1`，本地采用其中 bulge `0.96e-3` 与 disk `~1.7e-3 ph cm^-2 s^-1` 作为归一化锚点。",
        "",
        "注意：本地 `bulge_gaussian_fwhm_*` 和 `disk_thick_gaussian` 是为了估计当前窄 FoV 内 foreground 的 proxy sky model。它们的总通量归一化有 SPI 论文依据，但角宽/形状不应表述为对 Siegert et al. sky-template fit 的逐项复刻。",
        "",
        "当前 FoV 定义：",
        "",
        f"- 半径：`{fmt(fov['radius_deg'])} deg = {fmt(fov['radius_arcmin'])} arcmin`，当前作为前端聚焦光学接受角的 top-hat proxy",
        f"- 立体角：`Omega = 2*pi*(1-cos(theta)) = {fmt(fov['solid_angle_sr'])} sr`",
        f"- 小角近似面积：`pi*theta^2 = {fmt(fov['small_angle_area_deg2'])} deg^2`",
        "- Be 窗/焦平面几何只能作为角度到焦平面半径的 clipping 或 detector acceptance 约束；真正的弥散源角积分应由 Laue/channel optics 的 `A_eff(E, theta, phi)` 和 PSF/focal-map 决定。",
        "",
        "弥散源积分公式是：",
        "",
        "```text",
        "current top-hat proxy:",
        "  F_FoV(E,t) = integral_inside_optics_proxy I(E,l,b) dOmega",
        "",
        "production optics-weighted form:",
        "  R_sig(t) = integral I(E,l,b) * T_atm(E,l,b,t)",
        "             * A_eff(E,theta,phi) * detector_selection(x,y,E) dOmega dE",
        "```",
        "",
        "| sky model | total flux | FoV flux | FoV fraction |",
        "|---|---:|---:|---:|",
    ]
    for row in diffuse["models"]:
        lines.append(
            f"| `{row['sky_model']}` | {fmt(row['total_flux_ph_cm2_s'])} | {fmt(row['fov_flux_ph_cm2_s'])} | {fmt(row['fov_fraction'])} |"
        )
    dc = diffuse["default_composite"]
    lines += [
        "",
        f"默认弥散源为 `bulge_gaussian_fwhm_8deg + disk_thick_gaussian`，总通量 `{fmt(dc['total_flux_ph_cm2_s'])} ph cm^-2 s^-1`，FoV 内通量 `{fmt(dc['fov_flux_ph_cm2_s'])} ph cm^-2 s^-1`，FoV fraction `{fmt(dc['fov_fraction'])}`。",
        "",
        "## Laue 与 Channel 的 FoV 差异是否需要现在处理",
        "",
        "当前不改数值链，理由如下：",
        "",
        "- 当前 Laue 与 Channel 两条路线的弥散源 FoV flux 都用同一个 `4.47 arcmin` 前端光学 top-hat proxy。因此在 `F_FoV` 这一步没有路线差异。",
        "- 两条路线现在的差异主要来自各自的 on-axis/scalar optics response，而不是 route-specific off-axis `A_eff(E,theta,phi)`。",
        "- 真实物理上 Laue 和 Channel 的 off-axis response、PSF tail、focal-plane clipping 会不同；这对 production diffuse imaging 是重要项。",
        "- 但对当前结论不敏感：V404/点源基准是 on-axis；默认弥散源 FoV flux 只有 `2.723e-7 ph cm^-2 s^-1`，远小于当前点源扫描锚点。即使 route-specific FoV correction 有因子级变化，也不会改变“当前 pointed 构型不适合测 SPI 大尺度弥散源”的结论。",
        "",
        "因此本轮只记录该限制，不重新定义 Laue/Channel 两套 FoV，也不重跑显著度。后续如果要发表 production 级弥散源结果，应为 Laue 和 Channel 分别提供 `A_eff(E,theta,phi)`、PSF/focal map 和焦平面 clipping 后再重算。",
        "",
        "## 口径边界",
        "",
        "- V404：当前是点源瞬变 benchmark。它可以用于测试通量、线宽、红移和能窗损失，但不能写成“系统科学目标就是 V404”。",
        "- 弥散源：当前是 FoV aperture foreground，不是完整 diffuse optics focal map。若要 production 级弥散源，需要先把 sky map 经过真实 Laue/channel optics ray tracing 变成焦平面 photon map。",
        "- V404 和弥散源的通量都在时变 3sigma 记录里按 top-of-atmosphere flux 处理，再乘 `T_atm_511(t)`；不是直接使用地面/探测器处通量。",
        "",
        "## 参考依据",
        "",
        "- V404: Siegert et al., *Positron annihilation signatures associated with the outburst of the microquasar V404 Cygni*, Nature 531, 341-343 (2016), arXiv: https://arxiv.org/abs/1603.01169",
        "- 银河弥散 511 keV: Siegert et al., *Gamma-ray spectroscopy of Positron Annihilation in the Milky Way*, A&A 586, A84 (2016), arXiv: https://arxiv.org/abs/1512.00325",
        "- 聚焦 511 keV 仪器概念背景: Shirazi et al., *The 511-CAM Mission*, JATIS 9, 024006 (2023), arXiv: https://arxiv.org/abs/2206.14652",
        "",
        "## 机器可读文件",
        "",
        f"- `{SUMMARY_CSV.name}`",
        f"- `{SUMMARY_JSON.name}`",
    ]
    README_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = build_summary()
    table = build_table(summary)
    write_csv(SUMMARY_CSV, table)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    draw_schematic(summary)
    write_markdown(summary)
    print(README_MD.relative_to(ROOT))
    print(SCHEMATIC.relative_to(ROOT))


if __name__ == "__main__":
    main()
