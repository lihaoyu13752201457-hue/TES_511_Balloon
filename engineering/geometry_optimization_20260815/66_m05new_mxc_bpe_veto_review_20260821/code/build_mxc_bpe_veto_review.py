#!/usr/bin/env python3
"""Build the M05NEW SG3B/SH3 section and bounded BPE/plastic assessment.

This is a RAM-safe derived-data task.  It reads CSV/JSON plus two geometry text
files; it does not open SIM payloads, construct Geant4 geometry, or run transport.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/m05new_mxc_bpe_veto_mpl")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, Patch, Rectangle


HERE = Path(__file__).resolve()
PACKAGE = HERE.parents[1]
ROOT = PACKAGE.parents[2]
OUT = PACKAGE / "outputs"
DATA = PACKAGE / "data"
M05NEW = ROOT / "core_md/balloon511_ea_latex_drafts/M05NEW"
M05_FIGURES = M05NEW / "figures"

SG3B_GEO = Path(
    "/home/ubuntu/.codex/worktrees/4f50/TES_511_Balloon/engineering/"
    "geometry_optimization_20260815/55_geoopt_sg3b_bi_halfcylinder_al_harness_20260816/"
    "geometry/DEMO2_DR_v3p5_SG3B.geo"
)
SH3_GEO = Path(
    "/home/ubuntu/.codex/worktrees/e3cf/TES_511_Balloon/engineering/"
    "geometry_optimization_20260815/sh3/assembly_opt_v3/geometry/SH3_Assembly_OptV3.geo"
)
SG3B_LINEAGE = ROOT / (
    "engineering/geometry_optimization_20260815/"
    "59_sg3b_prompt_activation_coupling_20260818/outputs/02_coupling_analysis/"
    "selected_event_lineage.csv"
)
SG3B_COUPLING_SUMMARY = ROOT / (
    "engineering/geometry_optimization_20260815/"
    "59_sg3b_prompt_activation_coupling_20260818/outputs/02_coupling_analysis/summary.json"
)
OPTV3_ORIGINS = ROOT / (
    "engineering/geometry_optimization_20260815/"
    "63_m05new_sg3b_signal_statistics_20260820/outputs/05_optv3_delayed_origins/"
    "optv3_delayed_selected_events.csv"
)
OPTV3_ORIGIN_SUMMARY = ROOT / (
    "engineering/geometry_optimization_20260815/"
    "63_m05new_sg3b_signal_statistics_20260820/outputs/05_optv3_delayed_origins/summary.json"
)
DIRECT_CUTFLOW = ROOT / (
    "DEEPSEEK_CODE/outputs/04_event_catalog_step05_m05_fixed_20260820/direct_cutflow.csv"
)
TIMELINE_SUMMARY = ROOT / (
    "DEEPSEEK_CODE/outputs/05_mature_timeline_m05_fixed_20260820/summary.json"
)

TARGET_FMIN = 1.5e-5
FINAL_WINDOW = "w2_510p58_511p42"
FINAL_STAGE = "compton_trajectory_veto"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prop(text: str, name: str, key: str) -> list[float]:
    match = re.search(rf"^{re.escape(name)}\.{re.escape(key)}\s+(.+)$", text, re.MULTILINE)
    if not match:
        raise RuntimeError(f"missing geometry property: {name}.{key}")
    values: list[float] = []
    for token in match.group(1).split():
        try:
            values.append(float(token))
        except ValueError:
            # Shape properties start with a type token such as PCON/TUBS/BRIK.
            continue
    if not values:
        raise RuntimeError(f"geometry property has no numeric values: {name}.{key}")
    return values


def shape_params(text: str, shape: str) -> list[float]:
    match = re.search(rf"^{re.escape(shape)}\.Parameters\s+(.+)$", text, re.MULTILINE)
    if not match:
        raise RuntimeError(f"missing shape parameters: {shape}")
    return [float(token) for token in match.group(1).split()]


def close(actual: float, expected: float, label: str, atol: float = 1e-9) -> None:
    if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=atol):
        raise RuntimeError(f"{label}: expected {expected}, got {actual}")


def geometry_contract() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    sg = SG3B_GEO.read_text(encoding="utf-8")
    sh = SH3_GEO.read_text(encoding="utf-8")
    plates = {
        "ColdPlate_MXC_50mK_SD_anchor": (0.0, 15.0),
        "ColdPlate_CP_100mK_intercept": (5.0, 15.0),
        "ColdPlate_Still_0p7K": (11.0, 15.0),
        "ColdPlate_4K": (20.0, 17.5),
        "ColdPlate_60K": (29.0, 17.5),
    }
    rows: list[dict[str, Any]] = []
    for geometry, text in (("SG3B", sg), ("SH3_OptV3", sh)):
        for name, (z_expected, radius_expected) in plates.items():
            position = prop(text, name, "Position")
            shape = prop(text, name, "Shape")
            close(position[2], z_expected, f"{geometry}:{name}:z")
            close(shape[-1], radius_expected, f"{geometry}:{name}:radius")
            close(shape[3], -0.2, f"{geometry}:{name}:zmin")
            close(shape[-3], 0.2, f"{geometry}:{name}:zmax")
            rows.append({
                "geometry": geometry,
                "component": name,
                "kind": "cold_plate",
                "x_center_cm": position[0],
                "z_center_cm": position[2],
                "x_min_cm": -radius_expected,
                "x_max_cm": radius_expected,
                "z_min_cm": position[2] - 0.2,
                "z_max_cm": position[2] + 0.2,
                "source": str(SG3B_GEO if geometry == "SG3B" else SH3_GEO),
            })

    sg_tes_x = []
    sh_tes_x = []
    for index in range(6):
        sg_position = prop(sg, f"TES_L{index}", "Position")
        sh_position = prop(sh, f"TES_L{index}", "Position")
        sg_tes_x.append(sg_position[0])
        sh_tes_x.append(sh_position[0])
        rows.extend((
            {
                "geometry": "SG3B", "component": f"TES_L{index}", "kind": "TES_active_layer",
                "x_center_cm": sg_position[0], "z_center_cm": sg_position[2],
                "x_min_cm": sg_position[0] - 0.15, "x_max_cm": sg_position[0] + 0.15,
                "z_min_cm": sg_position[2] - 1.8, "z_max_cm": sg_position[2] + 1.8,
                "source": str(SG3B_GEO),
            },
            {
                "geometry": "SH3_OptV3", "component": f"TES_L{index}", "kind": "TES_active_layer",
                "x_center_cm": sh_position[0], "z_center_cm": sh_position[2],
                "x_min_cm": sh_position[0] - 0.15, "x_max_cm": sh_position[0] + 0.15,
                "z_min_cm": sh_position[2] - 1.8, "z_max_cm": sh_position[2] + 1.8,
                "source": str(SH3_GEO),
            },
        ))
    for actual, expected in zip(sg_tes_x, (-3.0, -1.8, -0.6, 0.6, 1.8, 3.0), strict=True):
        close(actual, expected, "SG3B TES x")
    for actual, expected in zip(sh_tes_x, (-38.55, -37.35, -36.15, -34.95, -33.75, -32.55), strict=True):
        close(actual, expected, "SH3 TES x")

    bpe = shape_params(sg, "GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm_FullShape")
    plastic = shape_params(sg, "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm_FullShape")
    sg_bgo = shape_params(sg, "BGO_S3C_FullWrap_SideShell_WindowCut_40mm_FullShellShape")
    sh_bgo = prop(sh, "SH3_BGO40_SideShield", "Shape")
    if "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm.Material" in sh:
        raise RuntimeError("OptV3 unexpectedly contains the old plastic skin")
    close(bpe[-2], 27.0, "SG3B BPE inner radius")
    close(bpe[-1], 29.0, "SG3B BPE outer radius")
    close(plastic[-2], 29.0, "SG3B plastic inner radius")
    close(plastic[-1], 30.0, "SG3B plastic outer radius")
    close(sg_bgo[-2], 21.2, "SG3B BGO inner radius")
    close(sg_bgo[-1], 25.2, "SG3B BGO outer radius")
    close(sh_bgo[0], 6.7, "SH3 BGO inner radius")
    close(sh_bgo[1], 10.7, "SH3 BGO outer radius")
    close(sh_bgo[2], 6.5, "SH3 BGO axial half-length")

    return {
        "cold_plates": plates,
        "sg3b_tes_x_cm": sg_tes_x,
        "sg3b_tes_z_cm": -5.2,
        "sh3_tes_x_cm": sh_tes_x,
        "sh3_tes_z_cm": -2.8,
        "sg3b_bgo_pcon": sg_bgo,
        "sg3b_bpe_pcon": bpe,
        "sg3b_plastic_pcon": plastic,
        "sh3_bgo_tubs": sh_bgo,
        "instrument_frame_rotation_y_deg": 45.0,
    }, rows


def classify_volume(volume: str) -> str:
    if volume.startswith("ColdPlate_") or volume == "DR_MixingChamber_Cu":
        return "DR/MXC + staged cold plates"
    near_tokens = (
        "TES_", "SubstrateSupport", "SH3_Layer", "SH3_OptV2_W_Frame",
        "BottomColdPlate", "ColdFinger", "50mK", "Bi_MXC_TES",
    )
    if any(token in volume for token in near_tokens):
        return "TES-near structures"
    return "other structures"


def load_origins() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    sg_rows: list[dict[str, Any]] = []
    for row in read_csv(SG3B_LINEAGE):
        if row["stream"] != "delayed":
            continue
        sg_rows.append({
            "geometry": "SG3B",
            "source_volume": row["source_volume"],
            "region": classify_volume(row["source_volume"]),
            "xprime_cm": float(row["source_xprime_cm"]),
            "zprime_cm": float(row["source_zprime_cm"]),
            "weight_cps": float(row["day15_noacc_cps"]),
        })

    sh_rows: list[dict[str, Any]] = []
    angle = math.radians(45.0)
    cosine, sine = math.cos(angle), math.sin(angle)
    for row in read_csv(OPTV3_ORIGINS):
        x_world = float(row["x_cm"])
        z_world = float(row["z_cm"])
        # Inverse of InstrumentFrame.Rotation 0 45 0.
        x_local = cosine * x_world - sine * z_world
        z_local = sine * x_world + cosine * z_world
        sh_rows.append({
            "geometry": "SH3_OptV3",
            "source_volume": row["source_volume"],
            "region": classify_volume(row["source_volume"]),
            "xprime_cm": x_local,
            "zprime_cm": z_local,
            "weight_cps": float(row["day15_event_weight_cps"]),
        })

    sg_summary = read_json(SG3B_COUPLING_SUMMARY)
    sh_summary = read_json(OPTV3_ORIGIN_SUMMARY)
    if len(sg_rows) != 394:
        raise RuntimeError(f"expected 394 SG3B selected delayed origins, got {len(sg_rows)}")
    if len(sh_rows) != 111:
        raise RuntimeError(f"expected 111 OptV3 selected delayed origins, got {len(sh_rows)}")
    close(sum(row["weight_cps"] for row in sg_rows), sg_summary["delayed"]["day15_noacc_cps"], "SG3B delayed origin sum", 1e-12)
    close(sum(row["weight_cps"] for row in sh_rows), sh_summary["delayed_W2_final_day15_rate_cps"], "OptV3 delayed origin sum", 1e-12)

    shares: list[dict[str, Any]] = []
    for geometry, rows in (("SG3B", sg_rows), ("SH3_OptV3", sh_rows)):
        total = sum(row["weight_cps"] for row in rows)
        grouped: dict[str, float] = defaultdict(float)
        for row in rows:
            grouped[row["region"]] += row["weight_cps"]
        for region in ("DR/MXC + staged cold plates", "TES-near structures", "other structures"):
            shares.append({
                "geometry": geometry,
                "region": region,
                "day15_delayed_W2_rate_cps": grouped[region],
                "fraction_of_delayed_W2_final": grouped[region] / total,
                "selected_event_rows": sum(1 for row in rows if row["region"] == region),
                "delayed_W2_total_cps": total,
            })
    return sg_rows, sh_rows, shares


def background_bounds() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    grouped: dict[tuple[str, str], float] = defaultdict(float)
    for row in read_csv(DIRECT_CUTFLOW):
        if row["window_id"] == FINAL_WINDOW and row["stage"] == FINAL_STAGE:
            grouped[(row["stream"], row["family"])] += float(row["weighted_rate_cps"])
    composition: list[dict[str, Any]] = []
    direct_total = sum(grouped.values())
    for (stream, family), rate in sorted(grouped.items()):
        if rate <= 0:
            continue
        composition.append({
            "stream": stream,
            "incident_family": family,
            "day15_direct_W2_final_no_coincidence_cps": rate,
            "fraction_of_direct_W2_final": rate / direct_total,
        })

    timeline = read_json(TIMELINE_SUMMARY)
    mature_b = float(timeline["per_anchor"]["60"]["timeline"]["stage_rates_cps"][FINAL_WINDOW][FINAL_STAGE])
    fmin = float(timeline["fmin_ph_cm2_s"]["fmin_3sigma_gauss_ph_cm2_s"])
    delayed_total = float(read_json(OPTV3_ORIGIN_SUMMARY)["delayed_W2_final_day15_rate_cps"])
    close(grouped[("delayed", "n")] + grouped[("delayed", "p")] + grouped[("delayed", "alpha")] + grouped[("delayed", "gamma")] + grouped[("delayed", "eplus")] + grouped[("delayed", "eminus")] + grouped[("delayed", "muminus")] + grouped.get(("delayed", "muplus"), 0.0), delayed_total, "OptV3 delayed family sum", 1e-8)
    close(direct_total, 0.009418680739114393, "OptV3 direct final total", 1e-14)
    close(grouped[("prompt", "eplus")], 0.0, "OptV3 prompt eplus survivor")
    if any(rate > 0 for (stream, family), rate in grouped.items() if stream == "prompt" and family != "gamma"):
        raise RuntimeError("OptV3 prompt-final composition is no longer gamma-only")

    common_time_scale = mature_b / direct_total
    target_b = mature_b * (TARGET_FMIN / fmin) ** 2
    neutron_delayed = grouped[("delayed", "n")]
    prompt_eplus = grouped[("prompt", "eplus")]
    scenarios = (
        ("current OptV3", mature_b, "measured mature day-15 background"),
        ("ideal removal of prompt primary e+", mature_b - prompt_eplus * common_time_scale, "plastic ceiling for the already-zero prompt-e+ final component"),
        ("ideal removal of all n-induced delayed", mature_b - neutron_delayed * common_time_scale, "unphysical 100% BPE ceiling; signal held fixed"),
        ("ideal removal of all delayed", mature_b - delayed_total * common_time_scale, "absolute activation-removal ceiling; signal held fixed"),
        ("required for 1.5e-5 target", target_b, "required background if Aeff and exposure are unchanged"),
    )
    rows: list[dict[str, Any]] = []
    for name, background, interpretation in scenarios:
        rows.append({
            "scenario": name,
            "mature_background_cps": background,
            "background_fraction_vs_current": background / mature_b,
            "background_reduction_fraction": 1.0 - background / mature_b,
            "Fmin_3sigma_gaussian_ph_cm2_s_if_Aeff_fixed": fmin * math.sqrt(background / mature_b),
            "interpretation": interpretation,
        })
    summary = {
        "current_mature_background_cps": mature_b,
        "current_Fmin_3sigma_gaussian_ph_cm2_s": fmin,
        "target_Fmin_ph_cm2_s": TARGET_FMIN,
        "target_background_cps_if_Aeff_fixed": target_b,
        "required_background_reduction_fraction_if_Aeff_fixed": 1.0 - target_b / mature_b,
        "direct_final_no_coincidence_cps": direct_total,
        "mature_to_direct_scale": common_time_scale,
        "prompt_gamma_final_cps": grouped[("prompt", "gamma")],
        "prompt_primary_eplus_final_cps": prompt_eplus,
        "delayed_total_final_cps": delayed_total,
        "neutron_induced_delayed_final_cps": neutron_delayed,
        "neutron_induced_fraction_of_direct_total": neutron_delayed / direct_total,
        "positron_induced_delayed_final_cps": grouped[("delayed", "eplus")],
        "positron_induced_fraction_of_direct_total": grouped[("delayed", "eplus")] / direct_total,
    }
    return composition, rows, summary


COLORS = {
    "ink": "#17212B",
    "grid": "#DDE3E8",
    "cold": "#D89A24",
    "cold_light": "#F5E4BA",
    "tes": "#C43C4B",
    "tes_light": "#F7DCE0",
    "bgo": "#2C6AA0",
    "bgo_light": "#CFE1F0",
    "bpe": "#6D7D2A",
    "plastic": "#B05279",
    "other": "#6C7782",
    "shell": "#AEB7BF",
}


def draw_plate(ax: plt.Axes, z: float, radius: float, label: str) -> None:
    ax.add_patch(Rectangle((-radius, z - 0.2), 2 * radius, 0.4, facecolor=COLORS["cold_light"], edgecolor=COLORS["cold"], lw=0.8, hatch="//", zorder=3))
    ax.text(radius + 0.8, z, label, va="center", ha="left", fontsize=7.2, color=COLORS["ink"])


def draw_common_cold_stages(ax: plt.Axes) -> None:
    for z, radius, label in (
        (0.0, 15.0, "MXC 50 mK plate"),
        (5.0, 15.0, "100 mK"),
        (11.0, 15.0, "Still 0.7 K"),
        (20.0, 17.5, "4 K"),
        (29.0, 17.5, "60 K"),
    ):
        draw_plate(ax, z, radius, label)
    ax.add_patch(Rectangle((-2.2, 0.31), 4.4, 1.8, facecolor="#C67C4E", edgecolor="#7D462A", lw=0.9, hatch="..", zorder=4))
    ax.text(3.0, 1.25, "mixing chamber", va="center", fontsize=7.0, color=COLORS["ink"])


def draw_tes(ax: plt.Axes, x_positions: list[float], z_center: float) -> tuple[float, float]:
    for x in x_positions:
        ax.add_patch(Rectangle((x - 0.15, z_center - 1.8), 0.3, 3.6, facecolor=COLORS["tes"], edgecolor="#7C1F2B", lw=0.7, zorder=8))
    x_min, x_max = min(x_positions) - 0.35, max(x_positions) + 0.35
    ax.add_patch(Rectangle((x_min, z_center - 2.05), x_max - x_min, 4.1, fill=False, edgecolor="#7C1F2B", lw=1.1, ls=(0, (4, 2)), zorder=8))
    ax.text((x_min + x_max) / 2, z_center - 2.8, "TES active stack", ha="center", va="top", fontsize=8.2, weight="bold", color="#7C1F2B")
    return x_min, x_max


def draw_sg3b_shields(ax: plt.Axes) -> None:
    for x0 in (-25.2, 21.2):
        ax.add_patch(Rectangle((x0, -19.4), 4.0, 60.3, facecolor=COLORS["bgo_light"], edgecolor=COLORS["bgo"], lw=1.0, alpha=0.8, zorder=1))
    for x0 in (-29.0, 27.0):
        ax.add_patch(Rectangle((x0, -24.5), 2.0, 70.5, facecolor="none", edgecolor=COLORS["bpe"], lw=1.4, ls=(0, (5, 3)), zorder=2))
    for x0 in (-30.0, 29.0):
        ax.add_patch(Rectangle((x0, -26.5), 1.0, 74.5, facecolor="none", edgecolor=COLORS["plastic"], lw=1.4, ls=(0, (1, 2)), zorder=2))
    ax.text(-23.2, 33.0, "BGO 4 cm", rotation=90, ha="center", va="top", fontsize=7.2, color=COLORS["bgo"])
    ax.text(-28.0, 33.0, "BPE 2 cm", rotation=90, ha="center", va="top", fontsize=7.2, color=COLORS["bpe"])
    ax.text(-29.5, 33.0, "plastic 1 cm", rotation=90, ha="center", va="top", fontsize=7.2, color=COLORS["plastic"])


def draw_sh3_chimney_and_shields(ax: plt.Axes) -> None:
    # Dimensionally faithful envelope; small CSG saddle/weld details are omitted.
    ax.add_patch(Rectangle((-45.75, -13.85), 30.75, 22.10, facecolor="#EEF1F3", edgecolor=COLORS["shell"], lw=1.0, zorder=0))
    ax.add_patch(Rectangle((-45.75, -13.55), 30.75, 21.50, facecolor="white", edgecolor="none", zorder=0))
    ax.text(-18.0, 7.0, "welded chimney to DR", ha="right", va="center", fontsize=7.4, color="#697680")
    # SH3 BGO side shield: axis along x', inner/outer radius 6.7/10.7 cm, half-length 6.5 cm.
    for z0 in (-13.5, 3.9):
        ax.add_patch(Rectangle((-41.7, z0), 13.0, 4.0, facecolor=COLORS["bgo_light"], edgecolor=COLORS["bgo"], lw=1.0, zorder=2))
    for x0 in (-45.7, -28.7):
        ax.add_patch(Rectangle((x0, -13.5), 4.0, 21.4, facecolor=COLORS["bgo_light"], edgecolor=COLORS["bgo"], lw=1.0, alpha=0.85, zorder=2))
    # User-requested candidate envelope: 5 cm BPE outside BGO and a notional 1 cm plastic skin.
    ax.add_patch(FancyBboxPatch((-50.7, -18.5), 32.0, 31.4, boxstyle="round,pad=0,rounding_size=1.0", fill=False, edgecolor=COLORS["bpe"], lw=1.5, ls=(0, (5, 3)), zorder=1))
    ax.add_patch(FancyBboxPatch((-51.7, -19.5), 34.0, 33.4, boxstyle="round,pad=0,rounding_size=1.0", fill=False, edgecolor=COLORS["plastic"], lw=1.3, ls=(0, (1, 2)), zorder=1))
    ax.text(-49.7, 12.2, "candidate 5 cm BPE", fontsize=7.0, color=COLORS["bpe"], ha="left")
    ax.text(-50.7, 13.8, "candidate plastic veto", fontsize=7.0, color=COLORS["plastic"], ha="left")


def plot_origins(ax: plt.Axes, rows: list[dict[str, Any]]) -> None:
    total = sum(row["weight_cps"] for row in rows)
    styles = {
        "DR/MXC + staged cold plates": (COLORS["cold"], "o", COLORS["ink"]),
        "TES-near structures": (COLORS["bgo"], "^", "white"),
        "other structures": (COLORS["other"], "x", COLORS["other"]),
    }
    for region, (color, marker, edge) in styles.items():
        selected = [row for row in rows if row["region"] == region]
        if not selected:
            continue
        sizes = [13 + 1100 * math.sqrt(row["weight_cps"] / total) for row in selected]
        kwargs: dict[str, Any] = {
            "s": sizes, "c": color, "marker": marker, "alpha": 0.70,
            "linewidths": 0.45, "zorder": 10,
        }
        if marker != "x":
            kwargs["edgecolors"] = edge
        ax.scatter([row["xprime_cm"] for row in selected], [row["zprime_cm"] for row in selected], **kwargs)


def make_figure(
    contract: dict[str, Any],
    sg_rows: list[dict[str, Any]],
    sh_rows: list[dict[str, Any]],
    shares: list[dict[str, Any]],
) -> list[Path]:
    share_lookup = {(row["geometry"], row["region"]): row for row in shares}
    fig, axes = plt.subplots(1, 2, figsize=(15.8, 8.6), sharex=True, sharey=True)
    for ax in axes:
        ax.set_xlim(-53, 33)
        ax.set_ylim(-21, 34)
        ax.set_aspect("equal", adjustable="box")
        ax.grid(True, color=COLORS["grid"], lw=0.55, zorder=-10)
        ax.set_xlabel("InstrumentFrame x′ [cm]", fontsize=9)
        ax.set_ylabel("InstrumentFrame z′ [cm]", fontsize=9)
        ax.tick_params(labelsize=7.5)
        for spine in ax.spines.values():
            spine.set_color("#88949E")
            spine.set_linewidth(0.8)

    draw_common_cold_stages(axes[0])
    draw_sg3b_shields(axes[0])
    sg_min, sg_max = draw_tes(axes[0], contract["sg3b_tes_x_cm"], contract["sg3b_tes_z_cm"])
    axes[0].add_patch(Rectangle((sg_min, -3.4), sg_max - sg_min, 36.4, facecolor=COLORS["tes_light"], edgecolor="none", alpha=0.35, zorder=0))
    axes[0].plot([0, 0], [0, -5.2], color=COLORS["cold"], lw=1.2, ls=(0, (4, 3)), zorder=6)
    plot_origins(axes[0], sg_rows)
    sg_share = share_lookup[("SG3B", "DR/MXC + staged cold plates")]["fraction_of_delayed_W2_final"]
    axes[0].set_title("SG3B: TES directly below the cold-stage stack", fontsize=11.5, weight="bold", color=COLORS["ink"])
    axes[0].text(
        0.02, 0.975,
        f"BGO + 2 cm BPE + 1 cm plastic present\nDR/MXC + staged plates: {100*sg_share:.1f}% of delayed W2",
        transform=axes[0].transAxes, ha="left", va="top", fontsize=8.1,
        bbox={"boxstyle": "round,pad=0.35", "fc": "white", "ec": "#B8C1C8", "alpha": 0.94},
        zorder=20,
    )

    draw_common_cold_stages(axes[1])
    draw_sh3_chimney_and_shields(axes[1])
    sh_min, sh_max = draw_tes(axes[1], contract["sh3_tes_x_cm"], contract["sh3_tes_z_cm"])
    axes[1].add_patch(Rectangle((sh_min, -0.75), sh_max - sh_min, 33.75, facecolor=COLORS["tes_light"], edgecolor="none", alpha=0.35, zorder=0))
    axes[1].plot([0, -35.55], [0, -2.8], color=COLORS["cold"], lw=1.2, ls=(0, (4, 3)), zorder=6)
    plot_origins(axes[1], sh_rows)
    sh_share = share_lookup[("SH3_OptV3", "DR/MXC + staged cold plates")]["fraction_of_delayed_W2_final"]
    axes[1].set_title("SH3 OptV3: TES displaced into the side chimney", fontsize=11.5, weight="bold", color=COLORS["ink"])
    axes[1].text(
        0.02, 0.975,
        f"Current authority: BGO only; candidate layers dashed\nDR/MXC + staged plates: {100*sh_share:.1f}% of delayed W2",
        transform=axes[1].transAxes, ha="left", va="top", fontsize=8.1,
        bbox={"boxstyle": "round,pad=0.35", "fc": "white", "ec": "#B8C1C8", "alpha": 0.94},
        zorder=20,
    )
    axes[1].annotate(
        "cold-stage vertical projection\nmisses the TES active x′ range",
        xy=(-35.5, 17.0), xytext=(-24.0, 22.0), fontsize=7.5, color="#7C1F2B",
        arrowprops={"arrowstyle": "->", "color": "#7C1F2B", "lw": 0.9},
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "#D6A9AF", "alpha": 0.93},
        zorder=20,
    )

    origin_handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=COLORS["cold"], markeredgecolor=COLORS["ink"], markersize=6, label="selected delayed source: DR/MXC/cold plate"),
        Line2D([0], [0], marker="^", color="none", markerfacecolor=COLORS["bgo"], markeredgecolor="white", markersize=6, label="selected delayed source: TES-near structure"),
        Line2D([0], [0], marker="x", color=COLORS["other"], markersize=6, label="selected delayed source: other"),
        Patch(facecolor=COLORS["tes"], edgecolor="#7C1F2B", label="TES active layers"),
        Patch(facecolor=COLORS["cold_light"], edgecolor=COLORS["cold"], hatch="//", label="MXC and upper cold plates"),
        Patch(facecolor=COLORS["bgo_light"], edgecolor=COLORS["bgo"], label="active BGO envelope"),
        Line2D([0], [0], color=COLORS["bpe"], ls=(0, (5, 3)), lw=1.5, label="BPE envelope"),
        Line2D([0], [0], color=COLORS["plastic"], ls=(0, (1, 2)), lw=1.5, label="plastic-veto envelope"),
    ]
    fig.legend(handles=origin_handles, loc="lower center", ncol=4, fontsize=7.5, frameon=False, bbox_to_anchor=(0.5, 0.035))
    fig.suptitle("MXC/cold-stage and TES active-region x′–z′ cross sections", fontsize=15, weight="bold", color=COLORS["ink"], y=0.985)
    fig.text(
        0.5, 0.915,
        "Same coordinate scale. Geometry envelopes are dimensionally aligned to the retained .geo files; CSG holes and small supports are omitted. "
        "Dots are exact selected delayed-source positions, sized by day-15 event weight.",
        ha="center", va="top", fontsize=8.2, color="#46525C",
    )
    fig.text(
        0.5, 0.010,
        "Interpretation: moving TES out of the cold-plate projection suppresses cold-stage coupling, but any material placed around the TES can itself activate; "
        "geometric non-overlap does not remove the finite 511-keV photon solid angle.",
        ha="center", va="bottom", fontsize=8.0, color="#384650",
    )
    fig.subplots_adjust(left=0.055, right=0.985, top=0.89, bottom=0.12, wspace=0.08)

    paths: list[Path] = []
    for target_dir in (OUT, M05_FIGURES):
        target_dir.mkdir(parents=True, exist_ok=True)
        for suffix in ("png", "svg", "pdf"):
            path = target_dir / f"fig_mxc_tes_sg3b_sh3_section.{suffix}"
            fig.savefig(path, dpi=260 if suffix == "png" else None, bbox_inches="tight", pad_inches=0.08)
            paths.append(path)
    plt.close(fig)
    return paths


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    M05_FIGURES.mkdir(parents=True, exist_ok=True)

    contract, geometry_rows = geometry_contract()
    sg_rows, sh_rows, shares = load_origins()
    composition, scenario_rows, bounds = background_bounds()
    figure_paths = make_figure(contract, sg_rows, sh_rows, shares)

    write_csv(DATA / "cross_section_geometry_contract.csv", geometry_rows)
    write_csv(DATA / "cold_stage_origin_share.csv", shares)
    write_csv(DATA / "optv3_background_composition.csv", composition)
    write_csv(DATA / "optv3_bpe_plastic_upper_bounds.csv", scenario_rows)

    cold_lookup = {(row["geometry"], row["region"]): row for row in shares}
    summary = {
        "status": "PASS__M05NEW_MXC_BPE_VETO_DERIVED_REVIEW",
        "authority_boundary": {
            "new_transport": False,
            "SIM_payloads_opened": 0,
            "detector_response_rerun": False,
            "geometry_figure": "dimensionally aligned x'-z' engineering section; full CSG holes omitted",
            "old_factor1000_rates_used": False,
            "scenario_values": "upper bounds from current corrected-keV selected components; not transport predictions",
        },
        "geometry": contract,
        "selected_delayed_origins": {
            "SG3B_rows": len(sg_rows),
            "SH3_OptV3_rows": len(sh_rows),
            "SG3B_cold_stage_fraction": cold_lookup[("SG3B", "DR/MXC + staged cold plates")]["fraction_of_delayed_W2_final"],
            "SH3_OptV3_cold_stage_fraction": cold_lookup[("SH3_OptV3", "DR/MXC + staged cold plates")]["fraction_of_delayed_W2_final"],
        },
        "background_lever_bounds": bounds,
        "decision": {
            "plastic_positron_veto": "NO_BASIS_FOR_1P5E5__OPTV3_PROMPT_PRIMARY_EPLUS_FINAL_IS_ZERO",
            "outer_5cm_BPE": "MAY_REDUCE_PART_OF_NEUTRON_ACTIVATION__100_PERCENT_N_COMPONENT_REMOVAL_STILL_FAR_FROM_TARGET",
            "combined_target_1p5e5": "NOT_SUPPORTED_WITHOUT_ALSO_REDUCING_PROMPT_GAMMA_AND_PRESERVING_SIGNAL",
            "paper_geometry_logic": "RETAIN_SG3B_BASELINE_TO_SH3_OFF_AXIS_TES_CAUSAL_STORY",
        },
        "outputs": {
            "figures": [str(path) for path in figure_paths],
            "geometry_contract_csv": str(DATA / "cross_section_geometry_contract.csv"),
            "origin_share_csv": str(DATA / "cold_stage_origin_share.csv"),
            "background_composition_csv": str(DATA / "optv3_background_composition.csv"),
            "upper_bounds_csv": str(DATA / "optv3_bpe_plastic_upper_bounds.csv"),
        },
        "input_sha256": {
            str(path): sha256(path)
            for path in (
                SG3B_GEO, SH3_GEO, SG3B_LINEAGE, SG3B_COUPLING_SUMMARY,
                OPTV3_ORIGINS, OPTV3_ORIGIN_SUMMARY, DIRECT_CUTFLOW, TIMELINE_SUMMARY,
            )
        },
    }
    write_json(OUT / "assessment.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
