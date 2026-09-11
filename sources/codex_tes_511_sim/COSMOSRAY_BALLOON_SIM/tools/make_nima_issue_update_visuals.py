#!/usr/bin/env python3
"""Generate focused visual addenda for the NIMA-style manuscript.

The figures answer three report-level questions:
1. how the 511-keV science source is injected,
2. how intrinsic line broadening enters Cosima source files,
3. how RPIP activation sampling relates to detector geometry.
"""

from __future__ import annotations

import csv
import json
import math
import os
import shutil
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R2 = ROOT / "reports2.0"
OUT = R2 / "04_FIGURES" / "nima_update"
RPIP_OUT = R2 / "03_NEXT_PHASE_SUPPORT" / "activation_rpip_sampling"
MPL_CACHE = ROOT / ".matplotlib_cache"

os.environ.setdefault("MPLCONFIGDIR", str(MPL_CACHE))
MPL_CACHE.mkdir(parents=True, exist_ok=True)

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def physical_volume_group(volume: str) -> tuple[str, str]:
    if volume.startswith("TES_L") or volume.startswith("TP_L"):
        return (
            "Ta TES pixels",
            "inventory/source proxy is TES_L*/TP_L*, but the plotted mass is the Ta pixel footprint inside the TES_L vacuum mother",
        )
    if volume.startswith("Substrate_L"):
        return ("Si substrates", "physical silicon substrate layers")
    if volume in {"Copper", "Cu_Base", "Cu_SupportPole"}:
        return ("Cu base/support", "inventory aggregates Copper; transport diagnostics split Cu_Base and Cu_SupportPole")
    if volume.startswith("CollBar") or volume == "CollimatorVac":
        return ("W collimator bars", "CollBarX/Y are physical W bars; CollimatorVac is a transport/source-volume proxy")
    if volume.startswith("Win_"):
        return ("Entrance windows", "Be/Nb entrance window volumes")
    if volume == "Nb_Shield":
        return ("Nb shield", "physical niobium shield")
    if volume == "W_Shield":
        return ("W shield", "physical tungsten shield")
    if volume == "BGO_Shield":
        return ("BGO shield", "physical active BGO veto shield")
    if volume == "Al_Shell":
        return ("Al shell", "physical aluminum shell")
    if volume == "Cryo_Shell":
        return ("Cryostat shell", "physical cryostat shell")
    return (volume, "as named in the source table")


def make_activation_geometry_summary() -> list[dict[str, object]]:
    inventory = read_csv(R2 / "02_PHASE2_CORE_MATERIALS" / "activation_inventory" / "inventory_parentfed_day15.csv")
    diagnostics = read_csv(R2 / "03_NEXT_PHASE_SUPPORT" / "activation_511_diagnostics" / "delayed_511_by_nuclide_volume.csv")

    activity_by_group: dict[str, float] = defaultdict(float)
    broad_by_group: dict[str, float] = defaultdict(float)
    line_by_group: dict[str, float] = defaultdict(float)
    notes: dict[str, str] = {}

    for row in inventory:
        group, note = physical_volume_group(row["VN"])
        activity_by_group[group] += float(row["Activity_Bq_parentfed"])
        notes.setdefault(group, note)

    for row in diagnostics:
        group, note = physical_volume_group(row["source_volume_proxy"])
        broad_by_group[group] += float(row["broad_480_550_final_cps"])
        line_by_group[group] += float(row["line_510p3_511p8_final_cps"])
        notes.setdefault(group, note)

    groups = sorted(
        set(activity_by_group) | set(broad_by_group) | set(line_by_group),
        key=lambda g: (broad_by_group[g], line_by_group[g], activity_by_group[g]),
        reverse=True,
    )
    rows: list[dict[str, object]] = []
    for group in groups:
        if activity_by_group[group] + broad_by_group[group] + line_by_group[group] <= 0:
            continue
        rows.append(
            {
                "geometry_group": group,
                "day15_parentfed_activity_Bq": activity_by_group[group],
                "broad_480_550_final_cps": broad_by_group[group],
                "line_510p3_511p8_final_cps": line_by_group[group],
                "geometry_note": notes.get(group, ""),
            }
        )

    RPIP_OUT.mkdir(parents=True, exist_ok=True)
    out = RPIP_OUT / "activation_geometry_volume_summary.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "geometry_group",
            "day15_parentfed_activity_Bq",
            "broad_480_550_final_cps",
            "line_510p3_511p8_final_cps",
            "geometry_note",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def add_geometry_schematic(ax, title: str, source: bool = True) -> None:
    """Draw a compact r-z cross-section using the current XZTES authority."""
    ax.set_title(title, fontsize=11)
    ax.set_xlabel("r (geometry units)")
    ax.set_ylabel("z (geometry units)")
    ax.set_xlim(0, 72)
    ax.set_ylim(-78, 132)
    ax.grid(True, alpha=0.18)

    shells = [
        ("Al shell", 0, 67, -73, 127.65, "#D7B5A6", 0.18),
        ("BGO shield", 19, 64, -70, 124.65, "#6B8E23", 0.20),
        ("Cryo shell", 19, 43, -19, 103.65, "#B8B8B8", 0.22),
        ("W shield", 19, 40, -16, 100.65, "#7F7F7F", 0.25),
        ("Nb shield", 19, 34, -10, 94.65, "#8FB1D9", 0.25),
        ("Cu base", 0, 30, -5.0, 0.0, "#C97D32", 0.55),
    ]
    label_pos = {
        "Al shell": (57, 121),
        "BGO shield": (49, 112),
        "Cryo shell": (40, 103),
        "W shield": (35, 96),
        "Nb shield": (24, 88),
        "Cu base": (31, -2.5),
    }
    for label, r0, r1, z0, z1, color, alpha in shells:
        ax.add_patch(Rectangle((r0, z0), r1 - r0, z1 - z0, facecolor=color, edgecolor=color, alpha=alpha, lw=1.0))
        tx, tz = label_pos[label]
        ax.text(
            tx,
            tz,
            label,
            fontsize=7,
            va="center",
            ha="center",
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.55, "pad": 1.5},
        )

    ax.add_patch(Rectangle((0, 0.01), 2.0, 9.83, facecolor="#C97D32", alpha=0.72, edgecolor="#8A4D12", lw=0.8))
    ax.text(6.0, 5.0, "Cu support\npole", fontsize=7, va="center", ha="left")

    for i, zc in enumerate([11.65, 23.65, 35.65, 47.65, 59.65, 71.65]):
        substrate_z = 10.0 + 12.0 * i
        ax.add_patch(Rectangle((0, substrate_z - 0.15), 19.0, 0.30, facecolor="#222222", alpha=0.58, lw=0))
        ax.add_patch(Rectangle((0, zc - 1.5), 15.5, 3.0, facecolor="#4C78A8", alpha=0.42, edgecolor="#244F7A", lw=0.8))
        ax.plot([15.5, 39.0], [zc + 1.6, zc + 1.6], color="#4C78A8", lw=0.55, ls="--", alpha=0.50)
        ax.plot([15.5, 39.0], [zc - 1.6, zc - 1.6], color="#4C78A8", lw=0.55, ls="--", alpha=0.50)
        ax.text(17.0, zc, f"Ta pixels L{i}", fontsize=7, va="center")

    ax.text(
        31,
        72.5,
        "TES_L* vacuum mother half-width=39\nnot drawn as active mass",
        fontsize=7,
        va="top",
        ha="center",
        color="#244F7A",
        bbox={"facecolor": "white", "edgecolor": "#9AB6D6", "alpha": 0.72, "pad": 1.8},
    )

    ax.add_patch(Rectangle((0, 125.7), 20.53, 1.0, facecolor="#575757", alpha=0.68, edgecolor="#222222", lw=0.8))
    for r in np.linspace(2.7, 18.0, 6):
        ax.plot([r, r], [125.7, 126.7], color="white", lw=0.45, alpha=0.75)
    ax.text(23.0, 126.2, "W collimator\nbars", fontsize=7, va="center")

    ax.add_patch(Rectangle((0, 127.5), 18.98, 0.15, facecolor="#F58518", alpha=0.70, edgecolor="#F58518"))
    ax.text(21, 127.58, "Be window", fontsize=8, va="center")

    if source:
        ax.plot([0, 18], [127.66, 127.66], color="#E45756", lw=4, solid_capstyle="butt")
        ax.annotate(
            "post-optics\nHomogeneousBeam\nz=127.66, r=18, -z",
            xy=(18, 127.66),
            xytext=(33, 118),
            arrowprops={"arrowstyle": "->", "color": "#E45756", "lw": 1.2},
            fontsize=8,
            color="#8C1D18",
        )
        for r in [4, 10, 16]:
            ax.annotate("", xy=(r, 106), xytext=(r, 126.5), arrowprops={"arrowstyle": "->", "color": "#E45756", "lw": 1.0})


def load_spectrum(path: Path) -> tuple[np.ndarray, np.ndarray]:
    e, y = [], []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line.startswith("DP "):
                continue
            _, xs, ys = line.split()
            e.append(float(xs))
            y.append(float(ys))
    arr_e = np.array(e)
    arr_y = np.array(y)
    area = np.trapezoid(arr_y, arr_e)
    if area > 0:
        arr_y = arr_y / area
    return arr_e, arr_y


def make_source_and_line_figure(line_fraction: list[dict[str, str]], line_sensitivity: list[dict[str, str]]) -> None:
    fig = plt.figure(figsize=(13.2, 7.4), constrained_layout=True)
    gs = fig.add_gridspec(2, 3, width_ratios=[1.0, 1.15, 1.05])
    ax_geo = fig.add_subplot(gs[:, 0])
    ax_line = fig.add_subplot(gs[0, 1:])
    ax_stat = fig.add_subplot(gs[1, 1:])

    add_geometry_schematic(ax_geo, "Science source placement")

    spectra_dir = ROOT / "run_configs" / "nextphase_science_sources" / "spectra"
    models_to_plot = [
        ("mono", None, "#333333"),
        ("gaussian_fwhm_0p5", spectra_dir / "science_511_gaussian_fwhm_0p5.dat", "#4C78A8"),
        ("gaussian_fwhm_1p5", spectra_dir / "science_511_gaussian_fwhm_1p5.dat", "#F58518"),
        ("gaussian_fwhm_2p5", spectra_dir / "science_511_gaussian_fwhm_2p5.dat", "#E45756"),
        ("velocity_sigma_600", spectra_dir / "science_511_velocity_sigma_600.dat", "#54A24B"),
        ("velocity_sigma_1000", spectra_dir / "science_511_velocity_sigma_1000.dat", "#B279A2"),
    ]
    for label, path, color in models_to_plot:
        if path is None:
            ax_line.axvline(511.0, color=color, lw=1.8, label="mono")
            continue
        e, y = load_spectrum(path)
        mask = (e >= 506) & (e <= 516)
        ax_line.plot(e[mask], y[mask], color=color, lw=1.6, label=label)
    ax_line.axvspan(510.3, 511.8, color="#F58518", alpha=0.14, label="line window")
    ax_line.set_title("Intrinsic source spectra used by Cosima line-model source files")
    ax_line.set_xlabel("Photon energy at source plane (keV)")
    ax_line.set_ylabel("Normalized density")
    ax_line.grid(True, alpha=0.25)
    ax_line.legend(fontsize=8, ncols=3)

    one_ms = [
        r for r in line_sensitivity
        if r["exposure_s"] == "1000000.0" and r["energy_window"] == "line_510p3_511p8"
    ]
    labels = [r["model_id"].replace("gaussian_", "g_").replace("velocity_", "v_") for r in one_ms]
    x = np.arange(len(one_ms))
    frac = [float(r["source_fraction_in_window"]) for r in one_ms]
    thr = [float(r["flux_3sigma_ph_cm2_s"]) * 1.0e4 for r in one_ms]
    ax_stat.bar(x - 0.18, frac, width=0.36, color="#4C78A8", label="fraction in 510.3-511.8")
    ax_stat2 = ax_stat.twinx()
    ax_stat2.plot(x + 0.18, thr, color="#E45756", marker="o", lw=1.8, label="3σ threshold x1e4")
    ax_stat.set_xticks(x, labels, rotation=35, ha="right", fontsize=8)
    ax_stat.set_ylim(0, 1.08)
    ax_stat.set_ylabel("Source fraction")
    ax_stat2.set_ylabel("1 Ms 3σ flux threshold (1e-4 ph cm$^{-2}$ s$^{-1}$)")
    ax_stat.set_title("Line broadening changes narrow-window acceptance and sensitivity")
    ax_stat.grid(True, axis="y", alpha=0.25)
    lines, line_labels = ax_stat.get_legend_handles_labels()
    lines2, line_labels2 = ax_stat2.get_legend_handles_labels()
    ax_stat.legend(lines + lines2, line_labels + line_labels2, fontsize=8, loc="upper left")

    fig.suptitle("Science source convention: generic post-optics 511-keV response source, not a V404-specific source", fontsize=13)
    fig.savefig(OUT / "science_source_and_line_broadening.png", dpi=220)
    plt.close(fig)


def make_rpip_geometry_context(activation_summary: list[dict[str, object]]) -> None:
    original_candidates = [
        Path("/home/ubuntu/cosmosray_bg_2602/cosmosray_buildup_rpmpia/decay_rpip_out/plot_check_day15.png"),
        ROOT / "production_runs" / "decay_from_buildup_equiv2602" / "plot_check_day15.png",
    ]
    original = next((p for p in original_candidates if p.exists()), None)
    if original is None:
        raise FileNotFoundError("Could not locate plot_check_day15.png")
    packaged = RPIP_OUT / "plot_check_day15_2602.png"
    shutil.copy2(original, packaged)

    img = mpimg.imread(packaged)
    fig = plt.figure(figsize=(13.4, 7.8), constrained_layout=True)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 0.78])
    ax_img = fig.add_subplot(gs[0, 0])
    ax_geo = fig.add_subplot(gs[0, 1])
    ax_img.imshow(img)
    ax_img.axis("off")
    ax_img.set_title("2602 RPIP day-15 sampling check\n(actual isotope positions sampled from buildup records)", fontsize=11)
    add_geometry_schematic(ax_geo, "Geometry context omitted by the RPIP plot", source=False)
    key_groups = {str(r["geometry_group"]): r for r in activation_summary}
    tes_rate = float(key_groups.get("Ta TES pixels", {}).get("broad_480_550_final_cps", 0.0))
    cu_rate = float(key_groups.get("Cu base/support", {}).get("broad_480_550_final_cps", 0.0))
    coll_rate = float(key_groups.get("W collimator bars", {}).get("broad_480_550_final_cps", 0.0))
    ax_geo.text(
        3,
        -68,
        "RP/IP records carry isotope, volume and position.\n"
        "Delayed source blocks are sampled by nuclide and true production position,\n"
        "then transported in the unchanged XZTES geometry.\n"
        "TES mass is shown as Ta pixel footprint, not the TES_L vacuum mother.\n"
        f"Day-15 480-550 keV final cps: TES={tes_rate:.3g}, Cu={cu_rate:.3g}, collimator={coll_rate:.3g}.",
        fontsize=8.2,
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "edgecolor": "#999999", "alpha": 0.92},
    )
    fig.savefig(OUT / "rpip_sampling_geometry_context.png", dpi=220)
    plt.close(fig)


def make_activation_geometry_volume_map(activation_summary: list[dict[str, object]]) -> None:
    preferred = [
        "Si substrates",
        "Ta TES pixels",
        "Cu base/support",
        "W collimator bars",
        "Entrance windows",
        "Nb shield",
        "W shield",
        "BGO shield",
        "Al shell",
    ]
    by_group = {str(r["geometry_group"]): r for r in activation_summary}
    selected = [by_group[g] for g in preferred if g in by_group]

    labels = [str(r["geometry_group"]) for r in selected]
    activity = np.array([float(r["day15_parentfed_activity_Bq"]) for r in selected])
    broad = np.array([float(r["broad_480_550_final_cps"]) for r in selected])
    line = np.array([float(r["line_510p3_511p8_final_cps"]) for r in selected])
    floor_activity = max(min(activity[activity > 0]) * 0.2, 1.0e-4) if np.any(activity > 0) else 1.0e-4
    floor_rate = max(min(broad[broad > 0]) * 0.2, 1.0e-6) if np.any(broad > 0) else 1.0e-6

    fig = plt.figure(figsize=(14.2, 7.4), constrained_layout=True)
    gs = fig.add_gridspec(1, 3, width_ratios=[0.88, 0.70, 0.78])
    ax_geo = fig.add_subplot(gs[0, 0])
    ax_act = fig.add_subplot(gs[0, 1])
    ax_rate = fig.add_subplot(gs[0, 2])

    add_geometry_schematic(ax_geo, "Physical geometry used for activation interpretation", source=False)
    y = np.arange(len(labels))
    ax_act.barh(y, np.maximum(activity, floor_activity), color="#4C78A8", alpha=0.82)
    ax_act.set_yticks(y, labels, fontsize=8)
    ax_act.invert_yaxis()
    ax_act.set_xscale("log")
    ax_act.set_xlabel("Day-15 parent-fed activity (Bq)")
    ax_act.set_title("Inventory by physical group")
    ax_act.grid(True, axis="x", alpha=0.25)

    ax_rate.barh(y - 0.18, np.maximum(broad, floor_rate), height=0.34, color="#E45756", label="480-550 final")
    ax_rate.barh(y + 0.18, np.maximum(line, floor_rate), height=0.34, color="#F58518", label="510.3-511.8 final")
    ax_rate.set_yticks(y, [])
    ax_rate.invert_yaxis()
    ax_rate.set_xscale("log")
    ax_rate.set_xlabel("Final delayed rate (cps)")
    ax_rate.set_title("Transported delayed contribution")
    ax_rate.grid(True, axis="x", alpha=0.25)
    ax_rate.legend(fontsize=8, loc="lower right")

    ax_geo.text(
        3,
        -72,
        "The plotted TES radius is the active pixel envelope (~15.5), while TES_L* remains a source-volume proxy.\n"
        "Cu and W-collimator activation are present; earlier compact plots hid them by scale and proxy naming.",
        fontsize=8.0,
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "edgecolor": "#999999", "alpha": 0.92},
    )
    fig.savefig(OUT / "activation_geometry_volume_map.png", dpi=220)
    plt.close(fig)


def make_stat_dashboard(day15: dict, image8: list[dict[str, str]], likelihood: list[dict[str, str]], injection: list[dict[str, str]], delayed_manifest: list[dict[str, str]]) -> None:
    fig, axs = plt.subplots(2, 2, figsize=(12.8, 8.2), constrained_layout=True)

    broad = [r for r in image8 if r["window"] == "broad_480_550"]
    labels = [r["component"] for r in broad]
    vals = [float(r["final_cps"]) for r in broad]
    axs[0, 0].bar(labels, vals, color=["#4C78A8", "#F58518", "#54A24B"])
    axs[0, 0].set_yscale("log")
    axs[0, 0].set_ylabel("Final rate (cps, log)")
    axs[0, 0].set_title("480-550 keV final component rates")
    axs[0, 0].tick_params(axis="x", rotation=25)
    axs[0, 0].grid(True, axis="y", alpha=0.25)

    like_rows = [
        r for r in likelihood
        if r["exposure_s"] == "1000000.0"
        and r["model"] in {"window_counting_same_events", "energy_radius_layer_template"}
    ]
    like_labels = [f"{r['energy_window'].replace('_', ' ')}\n{r['model']}" for r in like_rows]
    like_vals = [float(r["profiled_flux_3sigma_ph_cm2_s"]) * 1.0e4 for r in like_rows]
    axs[0, 1].bar(np.arange(len(like_vals)), like_vals, color="#E45756")
    axs[0, 1].set_xticks(np.arange(len(like_vals)), like_labels, rotation=30, ha="right", fontsize=7)
    axs[0, 1].set_ylabel("3σ threshold (1e-4 ph cm$^{-2}$ s$^{-1}$)")
    axs[0, 1].set_title("1 Ms profiled-proxy thresholds")
    axs[0, 1].grid(True, axis="y", alpha=0.25)

    inj_rows = [r for r in injection if r["model"] == "energy_radius_layer_template"]
    inj_labels = [r["energy_window"].replace("_", " ") for r in inj_rows]
    p3 = [float(r["P3"]) for r in inj_rows]
    p5 = [float(r["P5"]) for r in inj_rows]
    x = np.arange(len(inj_rows))
    axs[1, 0].bar(x - 0.18, p3, 0.36, label="P>=3σ", color="#4C78A8")
    axs[1, 0].bar(x + 0.18, p5, 0.36, label="P>=5σ", color="#F58518")
    axs[1, 0].set_xticks(x, inj_labels, rotation=20, ha="right")
    axs[1, 0].set_ylim(0, 1)
    axs[1, 0].set_ylabel("Probability")
    axs[1, 0].set_title("1e-4 ph cm$^{-2}$ s$^{-1}$ injection, 1 Ms")
    axs[1, 0].legend()
    axs[1, 0].grid(True, axis="y", alpha=0.25)

    days = [float(r["day"]) for r in delayed_manifest]
    acts = [float(r["total_activity_Bq"]) for r in delayed_manifest]
    axs[1, 1].plot(days, acts, marker="o", color="#54A24B", lw=2)
    axs[1, 1].set_xlabel("Day")
    axs[1, 1].set_ylabel("Total delayed activity (Bq)")
    axs[1, 1].set_title("Phase2 Level-1 delayed source activity")
    axs[1, 1].grid(True, alpha=0.25)

    fig.suptitle(
        f"Small statistical dashboard: final background={day15['expectation_rates_cps']['final']:.4g} cps, "
        f"science response={day15['science_sensitivity']['science_final_response_cps_per_ph_cm-2_s-1']:.4g} cps/(ph cm$^{{-2}}$ s$^{{-1}}$)",
        fontsize=13,
    )
    fig.savefig(OUT / "nima_small_stat_dashboard.png", dpi=220)
    plt.close(fig)


def make_optics_focused_background_concept() -> None:
    focused_summary_path = R2 / "03_NEXT_PHASE_SUPPORT" / "optics_focused_gamma_background" / "focused_gamma_background_summary.csv"
    if focused_summary_path.exists():
        focused_rows = {r["window"]: r for r in read_csv(focused_summary_path)}
        broad_rate = float(focused_rows["broad_480_550"]["mean_final_focused_gamma_cps"])
        line_rate = float(focused_rows["line_510p3_511p8"]["mean_final_focused_gamma_cps"])
        numeric_text = f"Computed Level-1 addendum:\n480-550 keV: {broad_rate:.3e} cps\n510.3-511.8 keV: {line_rate:.3e} cps"
    else:
        numeric_text = "Computed Level-1 addendum:\nnot found; run estimate_optics_focused_gamma_background.py"

    fig, ax = plt.subplots(figsize=(11.5, 6.2), constrained_layout=True)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")

    lens_x = 3.0
    focal_x = 7.1
    ax.add_patch(Rectangle((lens_x - 0.08, 1.0), 0.16, 4.0, facecolor="#666666", alpha=0.75))
    ax.text(lens_x, 5.25, "Laue / focusing optics\nhandled as Level-1 aperture acceptance", ha="center", va="bottom", fontsize=11)
    ax.add_patch(Rectangle((focal_x, 2.35), 0.18, 1.3, facecolor="#F58518", alpha=0.85))
    ax.text(focal_x + 0.35, 3.0, "Be window\n+ TES stack", va="center", fontsize=11)

    for y in [2.65, 3.0, 3.35]:
        ax.annotate("", xy=(lens_x - 0.12, y), xytext=(0.6, y), arrowprops={"arrowstyle": "->", "lw": 1.8, "color": "#4C78A8"})
        ax.annotate("", xy=(focal_x, 3.0), xytext=(lens_x + 0.12, y), arrowprops={"arrowstyle": "->", "lw": 1.6, "color": "#4C78A8"})
    ax.text(0.55, 3.65, "target 511-keV photons\nfrom source direction", color="#2F5F92", fontsize=10)

    for y0, y1 in [(5.5, 3.4), (5.15, 3.1), (4.8, 2.8)]:
        ax.annotate("", xy=(lens_x - 0.12, y1), xytext=(0.7, y0), arrowprops={"arrowstyle": "->", "lw": 1.35, "color": "#E45756", "linestyle": "--"})
        ax.annotate("", xy=(focal_x, 3.0), xytext=(lens_x + 0.12, y1), arrowprops={"arrowstyle": "->", "lw": 1.2, "color": "#E45756", "linestyle": "--"})
    ax.text(0.55, 5.55, "diffuse / atmospheric gamma\ninside optical bandpass and FoV", color="#9A1F1A", fontsize=10)

    for y in [0.65, 0.95, 1.25]:
        ax.annotate("", xy=(focal_x, y), xytext=(0.6, y), arrowprops={"arrowstyle": "->", "lw": 1.4, "color": "#54A24B"})
    ax.text(0.55, 0.28, "direct environmental gamma prompt\ncurrently simulated as full-sphere source", color="#2D6B2D", fontsize=10)

    ax.text(
        5.2,
        5.55,
        "Implemented separate term:\n"
        "R_opt,bg = ∫ I_bg(E,Ω,t) A_opt(E,Ω) P_focus(x,y,E'|E,Ω) dE dΩ\n"
        "Here P_focus is approximated by FoV solid angle, A_eff and measured post-optics efficiency.\n"
        "This is distinct from direct prompt γ and from the science response source.",
        fontsize=10,
        ha="left",
        va="top",
        bbox={"boxstyle": "round,pad=0.45", "facecolor": "white", "edgecolor": "#999999", "alpha": 0.95},
    )
    ax.text(
        5.25,
        0.45,
        "No-double-count rule: the direct full-sphere prompt γ stream is unchanged.\n"
        "Only the optical-aperture subset is added as a separately labelled focused γ component.\n"
        f"{numeric_text}",
        fontsize=10,
        ha="left",
        va="bottom",
        bbox={"boxstyle": "round,pad=0.45", "facecolor": "#FFF6E5", "edgecolor": "#C47F00", "alpha": 0.95},
    )
    fig.savefig(OUT / "optics_focused_gamma_background_concept.png", dpi=220)
    plt.close(fig)


def make_optics_focused_background_rate_figure() -> None:
    summary_path = R2 / "03_NEXT_PHASE_SUPPORT" / "optics_focused_gamma_background" / "focused_gamma_background_summary.csv"
    addendum_path = R2 / "03_NEXT_PHASE_SUPPORT" / "optics_focused_gamma_background" / "focused_gamma_sensitivity_addendum.csv"
    if not summary_path.exists() or not addendum_path.exists():
        return
    addendum = read_csv(addendum_path)
    labels = [r["window"].replace("_", " ") for r in addendum]
    old_bg = np.array([float(r["old_background_cps"]) for r in addendum])
    focused = np.array([float(r["focused_gamma_addendum_cps"]) for r in addendum])
    new_thr = np.array([float(r["new_threshold_flux_ph_cm2_s"]) * 1.0e4 for r in addendum])
    old_thr = np.array([float(r["old_threshold_flux_ph_cm2_s"]) * 1.0e4 for r in addendum])

    fig, axs = plt.subplots(1, 2, figsize=(11.8, 5.0), constrained_layout=True)
    x = np.arange(len(labels))
    axs[0].bar(x - 0.18, old_bg, width=0.36, color="#4C78A8", label="direct + delayed background")
    axs[0].bar(x + 0.18, focused, width=0.36, color="#E45756", label="focused aperture γ addendum")
    axs[0].set_yscale("log")
    axs[0].set_xticks(x, labels, rotation=18, ha="right")
    axs[0].set_ylabel("Final rate (cps)")
    axs[0].set_title("Focused γ is added as a separate rate component")
    axs[0].grid(True, axis="y", alpha=0.25)
    axs[0].legend(fontsize=8)

    axs[1].bar(x - 0.18, old_thr, width=0.36, color="#54A24B", label="old")
    axs[1].bar(x + 0.18, new_thr, width=0.36, color="#F58518", label="with focused γ")
    axs[1].set_xticks(x, labels, rotation=18, ha="right")
    axs[1].set_ylabel("1 Ms 3σ threshold (1e-4 ph cm$^{-2}$ s$^{-1}$)")
    axs[1].set_title("Sensitivity change from the aperture term")
    axs[1].grid(True, axis="y", alpha=0.25)
    axs[1].legend(fontsize=8)

    fig.savefig(OUT / "optics_focused_gamma_background_addendum.png", dpi=220)
    plt.close(fig)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    RPIP_OUT.mkdir(parents=True, exist_ok=True)
    line_fraction = read_csv(R2 / "03_NEXT_PHASE_SUPPORT" / "science_line_models" / "source_fraction_in_windows.csv")
    line_sensitivity = read_csv(R2 / "03_NEXT_PHASE_SUPPORT" / "science_line_models" / "sensitivity_by_line_model.csv")
    day15 = load_json(R2 / "02_PHASE2_CORE_MATERIALS" / "authorities" / "complete_day15_summary.json")
    image8 = read_csv(R2 / "02_PHASE2_CORE_MATERIALS" / "image8_tables" / "image8_style_component_rates.csv")
    likelihood = read_csv(R2 / "02_PHASE2_CORE_MATERIALS" / "likelihood_profiled" / "asimov_profiled_sensitivity.csv")
    injection = read_csv(R2 / "02_PHASE2_CORE_MATERIALS" / "source_injection" / "source_injection_profiled_summary.csv")
    injection = [r for r in injection if r["exposure_s"] == "1000000.0" and r["input_flux_ph_cm2_s"] == "0.0001"]
    delayed_manifest = read_csv(R2 / "02_PHASE2_CORE_MATERIALS" / "delayed_sources" / "delayed_source_level1_manifest.csv")
    activation_summary = make_activation_geometry_summary()

    make_source_and_line_figure(line_fraction, line_sensitivity)
    make_rpip_geometry_context(activation_summary)
    make_activation_geometry_volume_map(activation_summary)
    make_stat_dashboard(day15, image8, likelihood, injection, delayed_manifest)
    make_optics_focused_background_concept()
    make_optics_focused_background_rate_figure()

    manifest = {
        "status": "PASS",
        "tool": "matplotlib Agg",
        "outputs": [
            "reports2.0/04_FIGURES/nima_update/science_source_and_line_broadening.png",
            "reports2.0/04_FIGURES/nima_update/rpip_sampling_geometry_context.png",
            "reports2.0/04_FIGURES/nima_update/activation_geometry_volume_map.png",
            "reports2.0/04_FIGURES/nima_update/nima_small_stat_dashboard.png",
            "reports2.0/04_FIGURES/nima_update/optics_focused_gamma_background_concept.png",
            "reports2.0/04_FIGURES/nima_update/optics_focused_gamma_background_addendum.png",
            "reports2.0/03_NEXT_PHASE_SUPPORT/activation_rpip_sampling/plot_check_day15_2602.png",
            "reports2.0/03_NEXT_PHASE_SUPPORT/activation_rpip_sampling/activation_geometry_volume_summary.csv",
        ],
        "note": "Figures clarify science-source convention, intrinsic line broadening, optics-focused gamma background addendum without direct-background double counting, RPIP position sampling with corrected physical geometry context, and compact statistics.",
    }
    (OUT / "nima_issue_update_visuals_summary.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
