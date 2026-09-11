#!/usr/bin/env python3
"""Build a 2D prompt-511 incidence/leakage comparison figure.

The figure is intentionally diagnostic: it overlays selected prompt e+ proxy
origins and TES endpoints on simplified old/current geometry sections.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

try:
    import seaborn as sns
except ModuleNotFoundError:  # Keep this one-off diagnostic plot dependency-light.
    sns = None


ROOT = Path(__file__).resolve().parents[3]
OUTDIR = ROOT / "outputs" / "reports" / "prompt511_entry_audit_20260617"
OLD_RECORDS = OUTDIR / "old_eplus_prompt_final_records.json"
CURRENT_RECORDS = OUTDIR / "current_eplus_prompt_final_records.json"
SUMMARY_JSON = OUTDIR / "prompt511_entry_audit_summary.json"
OLD_BOUNDS = ROOT.parent / "codex_tes_511_sim" / "new_geo_re" / "outputs" / "geometry" / "XZTES_ADR_v4c_mkflange_cm" / "bounds.json"
CURRENT_BOUNDS = ROOT / "geo_refer" / "DEMO2_DR_v3p5_minpatch_centerfinger_bounds.json"

PNG_PATH = OUTDIR / "prompt511_prompt_incidence_xz_comparison.png"
SVG_PATH = OUTDIR / "prompt511_prompt_incidence_xz_comparison.svg"
META_PATH = OUTDIR / "prompt511_prompt_incidence_xz_comparison_metadata.json"


TOKENS = {
    "surface": "#FCFCFD",
    "panel": "#FFFFFF",
    "ink": "#1F2430",
    "muted": "#6F768A",
    "grid": "#E6E8F0",
    "axis": "#D7DBE7",
}

COLORS = {
    "tes": "#5477C4",
    "old_origin": "#CC6F47",
    "non_window": "#F0986E",
    "inner_window": "#FFE15B",
    "strict_window": "#71B436",
    "window": "#386411",
    "bore": "#D8ECBD",
    "csi": "#A3D576",
    "al": "#A3BEFA",
    "cu": "#F0986E",
    "w": "#464C55",
    "steel": "#7A828F",
    "kapton": "#F390CA",
    "nb": "#CEDFFE",
    "cryoperm": "#F5BACC",
}

CLASS_LABEL = {
    "non_window_no_window_disk_intersection": "non-window path",
    "inner_window_or_foil_only": "inner foil only",
    "strict_outer_filter_and_be_window": "strict Be+outer-Al window",
}

CLASS_COLOR = {
    "non_window_no_window_disk_intersection": COLORS["non_window"],
    "inner_window_or_foil_only": COLORS["inner_window"],
    "strict_outer_filter_and_be_window": COLORS["strict_window"],
}

MATERIAL_COLOR = {
    "CsI": COLORS["csi"],
    "Aluminium": COLORS["al"],
    "Copper": COLORS["cu"],
    "W": COLORS["w"],
    "LowCarbonSteel": COLORS["steel"],
    "StainlessSteel": "#A7ADB8",
    "Kapton": COLORS["kapton"],
    "Nb": COLORS["nb"],
    "Cryoperm": COLORS["cryoperm"],
    "Be": "#BEEB96",
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def global_to_current_local(point: Iterable[float]) -> tuple[float, float, float]:
    """Transform global coordinates into current v3p5 local side-entry frame."""
    x, y, z = point
    c = math.sqrt(0.5)
    return (c * x - c * z, y, c * x + c * z)


def primary_or_annihilation(row: dict) -> list[float] | None:
    return row.get("last_primary_cm") or row.get("annihilation_cm")


def current_origin_local(row: dict) -> tuple[float, float, float] | None:
    point = primary_or_annihilation(row)
    if point:
        return global_to_current_local(point)
    local = row.get("annihilation_local_cm")
    return tuple(local) if local else None


def old_origin(row: dict) -> tuple[float, float, float] | None:
    point = primary_or_annihilation(row)
    return tuple(point) if point else None


def rect(ax, x0, x1, z0, z1, color, alpha=0.25, edge=None, lw=0.7, zorder=1):
    ax.add_patch(
        Rectangle(
            (x0, z0),
            x1 - x0,
            z1 - z0,
            facecolor=color,
            edgecolor=edge or color,
            alpha=alpha,
            lw=lw,
            zorder=zorder,
        )
    )


def side_annulus(ax, r_in, r_out, z0, z1, color, alpha=0.20, label_side="both", zorder=1):
    if label_side in {"both", "left"}:
        rect(ax, -r_out, -r_in, z0, z1, color, alpha=alpha, zorder=zorder)
    if label_side in {"both", "right"}:
        rect(ax, r_in, r_out, z0, z1, color, alpha=alpha, zorder=zorder)


def side_annulus_with_hole(ax, r_in, r_out, z0, z1, hole_z, hole_r, color, alpha=0.25, zorder=1):
    # In x-z section, show the -x side wall with the side-port band removed.
    x0, x1 = -r_out, -r_in
    lower1, upper1 = z0, min(z1, hole_z - hole_r)
    lower2, upper2 = max(z0, hole_z + hole_r), z1
    if upper1 > lower1:
        rect(ax, x0, x1, lower1, upper1, color, alpha=alpha, zorder=zorder)
    if upper2 > lower2:
        rect(ax, x0, x1, lower2, upper2, color, alpha=alpha, zorder=zorder)


def setup_axes(ax, xlim, zlim, xlabel):
    ax.set_facecolor(TOKENS["panel"])
    ax.set_xlim(*xlim)
    ax.set_ylim(*zlim)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel(xlabel)
    ax.set_ylabel("z [cm]")
    ax.grid(True, color=TOKENS["grid"], alpha=0.65, lw=0.6)
    ax.axhline(0, color="#C5CAD3", lw=0.7, zorder=0)
    ax.axvline(0, color="#C5CAD3", lw=0.7, zorder=0)
    for spine in ax.spines.values():
        spine.set_color(TOKENS["axis"])


def draw_old_geometry(ax, old_bounds: dict, summary: dict, annotate: bool = True) -> None:
    active = old_bounds["ACTIVE_SHIELD"]
    side_annulus(
        ax,
        active["r_in"],
        active["r_out"],
        active["z_in_bot"],
        active["z_in_top"],
        COLORS["csi"],
        alpha=0.19,
        zorder=1,
    )
    outer = old_bounds["OUTER_MECHANICAL_SHELL"]
    side_annulus(
        ax,
        outer["r_in"],
        outer["r_out"],
        outer["z_in_bot"],
        outer["z_in_top"],
        COLORS["al"],
        alpha=0.16,
        zorder=1,
    )
    for item in old_bounds.get("CRYOSTAT_SHELLS", []):
        color = MATERIAL_COLOR.get(item["mat"], "#C5CAD3")
        side_annulus(ax, item["r_in"], item["r_out"], item["z_out_bot"], item["z_out_top"], color, alpha=0.11, zorder=1)
    for item in old_bounds.get("PASSIVE_PROXIES", []):
        if "r_in" in item and "r_out" in item and "z0" in item and "z1" in item:
            color = MATERIAL_COLOR.get(item.get("mat"), "#C5CAD3")
            side_annulus(ax, item["r_in"], item["r_out"], item["z0"], item["z1"], color, alpha=0.13, zorder=1)

    for idx, layer in enumerate(old_bounds.get("TES_LAYERS", [])):
        rect(
            ax,
            -layer["r_max"],
            layer["r_max"],
            layer["z_center"] - layer["hz"],
            layer["z_center"] + layer["hz"],
            COLORS["tes"],
            alpha=0.33,
            edge=COLORS["tes"],
            lw=0.8,
            zorder=3,
        )
        if idx in {0, 5}:
            ax.text(2.05, layer["z_center"], "TES", color=COLORS["tes"], fontsize=7.8, va="center")

    for win in old_bounds.get("WINDOWS", []):
        zc = win["z_center"]
        r = win["r_max"]
        color = MATERIAL_COLOR.get(win["material"], COLORS["window"])
        ax.plot([-r, r], [zc, zc], color=color, lw=1.2, alpha=0.95, zorder=4)
    collimator = old_bounds.get("COLLIMATOR", {})
    if collimator:
        zc = collimator["z_center"]
        ax.plot([-collimator["r_max"], -collimator["r_inner"]], [zc, zc], color=COLORS["w"], lw=2.0, zorder=4)
        ax.plot([collimator["r_inner"], collimator["r_max"]], [zc, zc], color=COLORS["w"], lw=2.0, zorder=4)

    blocker = summary["old_new_geo_re_current_side_region_blocker"]
    zc = -5.2
    h = 0.78
    for item in blocker["line_of_sight_components_outside_to_inside"]:
        r0, r1 = sorted(item["radial_interval_cm"])
        color = MATERIAL_COLOR.get(item["material"], "#C5CAD3")
        rect(ax, -r1, -r0, zc - h / 2, zc + h / 2, color, alpha=0.74, edge="#FFFFFF", lw=0.45, zorder=5)
    if annotate:
        ax.annotate(
            "current side line in old geometry:\nsolid material column, not a window",
            xy=(-10.8, zc),
            xytext=(-15.4, -8.25),
            ha="left",
            va="center",
            fontsize=8.2,
            color="#804126",
            arrowprops={"arrowstyle": "->", "color": "#804126", "lw": 1.0},
            zorder=8,
        )
        ax.text(-13.75, -0.3, "4.0 cm CsI\nside shield", fontsize=8.2, color="#386411", ha="left", va="center")
        ax.text(2.35, 12.4, "old axial\nwindow stack", fontsize=8.2, color=COLORS["window"], ha="left", va="center")
        ax.text(3.45, 16.0, "W top\naperture", fontsize=7.8, color=COLORS["w"], ha="left", va="center")


def draw_current_geometry(ax, current_bounds: dict) -> None:
    axis_z = -5.2
    side_hole_r = 2.7
    # Open bore around the side-port path.
    rect(ax, -18.6, -5.8, axis_z - side_hole_r, axis_z + side_hole_r, COLORS["bore"], alpha=0.22, edge=None, zorder=0)
    ax.plot([-18.6, 7.0], [axis_z, axis_z], color=COLORS["window"], lw=1.1, ls="--", alpha=0.85, zorder=2)
    ax.plot([-18.6, -5.8], [axis_z - side_hole_r, axis_z - side_hole_r], color="#71B436", lw=0.8, ls=":", alpha=0.8, zorder=2)
    ax.plot([-18.6, -5.8], [axis_z + side_hole_r, axis_z + side_hole_r], color="#71B436", lw=0.8, ls=":", alpha=0.8, zorder=2)

    components = {c["name"]: c for c in current_bounds["COMPONENTS"]}
    for name, color, alpha in [
        ("Outer_Al_Mechanical_Shell_detector_bay", COLORS["al"], 0.17),
        ("ActiveShield_Flex_Kapton_detector_bay", COLORS["kapton"], 0.17),
        ("ActiveShield_Al_Backplane_detector_bay", COLORS["al"], 0.17),
        ("CsI_Side_Segment_03", COLORS["csi"], 0.22),
        ("Passive_W_Liner_detector_bay", COLORS["w"], 0.21),
        ("Passive_Cu_Liner_detector_bay", COLORS["cu"], 0.20),
        ("Vacuum_Jacket_Al_266mmClass_side_port", COLORS["al"], 0.16),
        ("Shield_60K_Al_side_window", COLORS["al"], 0.14),
        ("Shield_4K_Al_side_window", COLORS["al"], 0.14),
        ("Still_Shield_Al_side_window", COLORS["al"], 0.14),
    ]:
        comp = components[name]
        p = comp["params"]
        r_in, r_out = p["r_in_cm"], p["r_out_cm"]
        z0 = p.get("z0_cm", p.get("z_out_bot_cm", -14.4))
        z1 = p.get("z1_cm", p.get("z_top_cm", p.get("z_in_top_cm", 2.0)))
        hole = p.get("side_hole", {"z_cm": axis_z, "r_cm": p.get("side_port_radius_cm", side_hole_r)})
        side_annulus_with_hole(ax, r_in, r_out, z0, z1, hole["z_cm"], hole["r_cm"], color, alpha=alpha, zorder=1)

    sleeve = components["W_Side_Aperture_Sleeve_collimator"]["params"]
    for z0, z1 in [
        (axis_z - sleeve["r_out_cm"], axis_z - sleeve["r_in_cm"]),
        (axis_z + sleeve["r_in_cm"], axis_z + sleeve["r_out_cm"]),
    ]:
        rect(ax, sleeve["x0_cm"], sleeve["x1_cm"], z0, z1, COLORS["w"], alpha=0.72, edge=COLORS["w"], lw=0.7, zorder=4)

    for comp in current_bounds["COMPONENTS"]:
        if comp.get("category") != "window":
            continue
        p = comp["params"]
        x = p["x_center_cm"]
        r = p["r_cm"]
        color = MATERIAL_COLOR.get(comp["material"], COLORS["window"])
        ax.plot([x, x], [axis_z - r, axis_z + r], color=color, lw=1.4, alpha=0.95, zorder=5)

    tes = components["TES_Ta_Absorber_Stack_side_entry"]["params"]
    for i, x in enumerate(tes["x_centers_cm"]):
        rect(
            ax,
            x - tes["pixel_size_cm"][2] / 2,
            x + tes["pixel_size_cm"][2] / 2,
            tes["axis_z_cm"] - tes["disc_r_cm"],
            tes["axis_z_cm"] + tes["disc_r_cm"],
            COLORS["tes"],
            alpha=0.31,
            edge=COLORS["tes"],
            lw=0.75,
            zorder=3,
        )
    ax.text(3.55, axis_z, "TES\nstack", fontsize=8.2, color=COLORS["tes"], ha="left", va="center")
    ax.text(-13.9, axis_z + 2.55, "side-window\nstack", fontsize=8.1, color=COLORS["window"], ha="left", va="bottom")
    ax.text(-17.95, axis_z - 3.45, "W sleeve", fontsize=7.8, color=COLORS["w"], ha="left", va="center")
    ax.text(-17.9, -0.8, "CsI/outer shell\nside hole", fontsize=8.0, color="#386411", ha="left", va="center")


def add_tracks(ax, segments, colors, alpha=0.21, lw=0.65, zorder=6):
    if not segments:
        return
    lc = LineCollection(segments, colors=colors, linewidths=lw, alpha=alpha, zorder=zorder)
    ax.add_collection(lc)


def plot_old_events(ax, rows: list[dict]) -> dict:
    origins = []
    tes = []
    segments = []
    for row in rows:
        origin = old_origin(row)
        endpoint = tuple(row["tes_centroid_cm"])
        if origin is None:
            continue
        origins.append(origin)
        tes.append(endpoint)
        segments.append([(origin[0], origin[2]), (endpoint[0], endpoint[2])])
    add_tracks(ax, segments, [COLORS["old_origin"]] * len(segments), alpha=0.13, lw=0.55)
    ax.scatter(
        [p[0] for p in origins],
        [p[2] for p in origins],
        s=18,
        color=COLORS["old_origin"],
        edgecolor="white",
        linewidth=0.25,
        alpha=0.65,
        zorder=7,
    )
    ax.scatter([p[0] for p in tes], [p[2] for p in tes], s=15, color=COLORS["tes"], alpha=0.75, edgecolor="white", linewidth=0.2, zorder=8)
    return {"events": len(origins)}


def plot_current_events(ax, rows: list[dict]) -> dict:
    origins_by_class: dict[str, list[tuple[float, float, float]]] = {}
    tes_by_class: dict[str, list[tuple[float, float, float]]] = {}
    crossings_by_class: dict[str, list[tuple[float, float, float]]] = {}
    segments = []
    segment_colors = []
    for row in rows:
        cls = row.get("side_window_leakage_class") or "unknown"
        origin = current_origin_local(row)
        endpoint = tuple(row["tes_centroid_local_cm"])
        if origin is None:
            continue
        origins_by_class.setdefault(cls, []).append(origin)
        tes_by_class.setdefault(cls, []).append(endpoint)
        segments.append([(origin[0], origin[2]), (endpoint[0], endpoint[2])])
        segment_colors.append(CLASS_COLOR.get(cls, "#7A828F"))
        for crossing in row.get("side_window_crossings_local_proxy", []):
            if crossing.get("inside_disk") and crossing.get("point_local_cm"):
                crossings_by_class.setdefault(cls, []).append(tuple(crossing["point_local_cm"]))
    add_tracks(ax, segments, segment_colors, alpha=0.17, lw=0.62)

    marker_for = {
        "non_window_no_window_disk_intersection": "o",
        "inner_window_or_foil_only": "^",
        "strict_outer_filter_and_be_window": "D",
    }
    for cls, points in origins_by_class.items():
        ax.scatter(
            [p[0] for p in points],
            [p[2] for p in points],
            s=24 if cls != "non_window_no_window_disk_intersection" else 18,
            marker=marker_for.get(cls, "o"),
            color=CLASS_COLOR.get(cls, "#7A828F"),
            alpha=0.78,
            edgecolor="white",
            linewidth=0.3,
            zorder=8,
            label=CLASS_LABEL.get(cls, cls),
        )
    endpoints = [p for points in tes_by_class.values() for p in points]
    ax.scatter([p[0] for p in endpoints], [p[2] for p in endpoints], s=15, color=COLORS["tes"], alpha=0.75, edgecolor="white", linewidth=0.2, zorder=9)
    for cls, points in crossings_by_class.items():
        ax.scatter(
            [p[0] for p in points],
            [p[2] for p in points],
            s=38,
            marker="x",
            color=CLASS_COLOR.get(cls, "#7A828F"),
            linewidth=1.15,
            alpha=0.95,
            zorder=11,
        )
    if crossings_by_class:
        ax.text(-14.9, -3.15, "x = window-disc\nintersection", fontsize=7.8, color=TOKENS["muted"], ha="left", va="top")
    return {
        "events": sum(len(v) for v in origins_by_class.values()),
        "class_counts": {CLASS_LABEL.get(k, k): len(v) for k, v in origins_by_class.items()},
        "window_disc_crossing_points": {CLASS_LABEL.get(k, k): len(v) for k, v in crossings_by_class.items()},
    }


def add_summary_boxes(fig, ax_old, ax_current, summary: dict) -> None:
    w = summary["window_vs_nonwindow_current_eplus_prompt_final"]
    old_block = summary["old_new_geo_re_current_side_region_blocker"]
    old_rate = summary["stage_stats"]["old"]["final"]["by_tag"]["prompt:eplus"]["rate_s-1"]
    current_rate = summary["stage_stats"]["current"]["final"]["by_tag"]["prompt:eplus"]["rate_s-1"]
    ax_old.text(
        0.02,
        0.985,
        "old final prompt e+: 106 events, %.4g cps\nold narrow W2 is still delayed-dominated" % old_rate,
        transform=ax_old.transAxes,
        ha="left",
        va="top",
        fontsize=8.5,
        color=TOKENS["ink"],
        bbox={"boxstyle": "round,pad=0.22", "fc": "white", "ec": "#E2E5EA", "alpha": 0.92},
        zorder=20,
    )
    mat = old_block["material_los_thickness_sum_cm"]
    ax_old.text(
        0.02,
        0.02,
        "same side-line blocker: CsI %.1f cm, Cu %.2f cm, Fe %.2f cm, Al %.2f cm"
        % (mat["CsI"], mat["Copper"], mat["LowCarbonSteel"], mat["Aluminium"]),
        transform=ax_old.transAxes,
        ha="left",
        va="bottom",
        fontsize=8.0,
        color=TOKENS["ink"],
        bbox={"boxstyle": "round,pad=0.22", "fc": "white", "ec": "#E2E5EA", "alpha": 0.92},
        zorder=20,
    )
    ax_current.text(
        0.02,
        0.985,
        "current final prompt e+: 80 events, %.4g cps\nnon-window: %d/80 (%.1f%% rate); any window-disc: %d/80; strict Be+outer-Al: %d/80"
        % (
            current_rate,
            w["non_window_events"],
            100.0 * w["non_window_fraction_by_rate"],
            w["any_window_disc_events"],
            w["strict_outer_filter_and_be_events"],
        ),
        transform=ax_current.transAxes,
        ha="left",
        va="top",
        fontsize=8.5,
        color=TOKENS["ink"],
        bbox={"boxstyle": "round,pad=0.22", "fc": "white", "ec": "#E2E5EA", "alpha": 0.92},
        zorder=20,
    )

    handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=COLORS["old_origin"], markeredgecolor="white", label="old primary/annihilation proxy"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=COLORS["non_window"], markeredgecolor="white", label="current non-window proxy"),
        Line2D([0], [0], marker="^", color="none", markerfacecolor=COLORS["inner_window"], markeredgecolor="white", label="current inner foil only"),
        Line2D([0], [0], marker="D", color="none", markerfacecolor=COLORS["strict_window"], markeredgecolor="white", label="current strict window"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=COLORS["tes"], markeredgecolor="white", label="TES centroid"),
        Patch(facecolor=COLORS["csi"], edgecolor=COLORS["csi"], alpha=0.35, label="CsI / shield material"),
        Patch(facecolor=COLORS["bore"], edgecolor=COLORS["bore"], alpha=0.35, label="side-port open bore"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=4, frameon=False, fontsize=8.1, bbox_to_anchor=(0.5, 0.008))


def main() -> None:
    old_rows = load_json(OLD_RECORDS)
    current_rows = load_json(CURRENT_RECORDS)
    summary = load_json(SUMMARY_JSON)
    old_bounds = load_json(OLD_BOUNDS)
    current_bounds = load_json(CURRENT_BOUNDS)

    if sns is not None:
        sns.set_theme(style="whitegrid")
    plt.rcParams.update(
        {
            "figure.facecolor": TOKENS["surface"],
            "axes.facecolor": TOKENS["panel"],
            "axes.edgecolor": TOKENS["axis"],
            "axes.labelcolor": TOKENS["ink"],
            "xtick.color": TOKENS["ink"],
            "ytick.color": TOKENS["ink"],
            "font.family": ["DejaVu Sans", "sans-serif"],
            "font.size": 9.0,
            "axes.titlesize": 12.0,
            "axes.titleweight": "bold",
        }
    )

    fig, axes = plt.subplots(1, 2, figsize=(15.2, 8.2), constrained_layout=False)
    fig.subplots_adjust(left=0.055, right=0.985, top=0.87, bottom=0.12, wspace=0.15)

    ax_old, ax_current = axes
    setup_axes(ax_old, (-16.0, 16.0), (-16.0, 18.0), "old global x [cm]")
    setup_axes(ax_current, (-22.0, 22.0), (-22.0, 22.0), "current local side-entry x [cm]")

    draw_old_geometry(ax_old, old_bounds, summary)
    draw_current_geometry(ax_current, current_bounds)
    old_event_stats = plot_old_events(ax_old, old_rows)
    current_event_stats = plot_current_events(ax_current, current_rows)

    ax_old.set_title("Old new_geo_re: axial/top window; side line is blocked")
    ax_current.set_title("Current v3p5: side port; prompt e+ mostly bypasses window discs")
    add_summary_boxes(fig, ax_old, ax_current, summary)

    fig.suptitle(
        "Prompt 511 keV e+ selected W2 incidence: old axial shielding vs current side-port leakage",
        fontsize=15.5,
        color=TOKENS["ink"],
        y=0.965,
    )
    fig.text(
        0.055,
        0.905,
        "Origin marker = last primary e+ interaction in geometry when present, otherwise annihilation point; line = proxy 511 path to selected TES centroid.",
        fontsize=9.0,
        color=TOKENS["muted"],
        ha="left",
    )

    fig.savefig(PNG_PATH, dpi=220)
    fig.savefig(SVG_PATH)
    plt.close(fig)

    metadata = {
        "status": "PASS_PROMPT511_PROMPT_INCIDENCE_FIGURE",
        "png": str(PNG_PATH.relative_to(ROOT)),
        "svg": str(SVG_PATH.relative_to(ROOT)),
        "old_events_plotted": old_event_stats,
        "current_events_plotted": current_event_stats,
        "current_window_vs_nonwindow": summary["window_vs_nonwindow_current_eplus_prompt_final"],
        "old_side_line_blocker": summary["old_new_geo_re_current_side_region_blocker"],
        "coordinate_policy": {
            "old_panel": "old global x-z cm",
            "current_panel": "current v3p5 local side-entry x-z cm, global coordinates rotated by -45 deg about y",
        },
    }
    META_PATH.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"status": metadata["status"], "png": metadata["png"], "svg": metadata["svg"]}, indent=2))


if __name__ == "__main__":
    main()
