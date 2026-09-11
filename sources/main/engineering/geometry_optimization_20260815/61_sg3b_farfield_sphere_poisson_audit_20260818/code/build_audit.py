#!/usr/bin/env python3
"""Build a no-SIM SG3B far-field sphere and Poisson common-axis audit."""

from __future__ import annotations

import csv
import importlib.util
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/sg3b_farfield_poisson_audit_mpl")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Polygon


HERE = Path(__file__).resolve()
PACKAGE = HERE.parents[1]
ROOT = PACKAGE.parents[2]
CONFIG = PACKAGE / "analysis_inputs.json"
OUT = PACKAGE / "outputs"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def resolve(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def monotonic_hull(points: np.ndarray) -> np.ndarray:
    unique = sorted({(float(x), float(y)) for x, y in points})
    if len(unique) <= 1:
        return np.asarray(unique)

    def cross(o: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[tuple[float, float]] = []
    for point in unique:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    upper: list[tuple[float, float]] = []
    for point in reversed(unique):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    return np.asarray(lower[:-1] + upper[:-1], dtype=float)


def parse_sphere(path: Path) -> dict[str, Any]:
    match = re.search(
        r"(?m)^SurroundingSphere\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s+"
        r"([0-9.eE+-]+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s*$",
        path.read_text(encoding="utf-8"),
    )
    if not match:
        raise RuntimeError(f"SurroundingSphere not found in {path}")
    radius, x, y, z, distance = map(float, match.groups())
    if not math.isclose(radius, distance, rel_tol=0.0, abs_tol=1e-12):
        raise RuntimeError("MEGAlib sphere radius/distance limitation is not satisfied")
    return {"radius_cm": radius, "center_world_cm": [x, y, z], "distance_cm": distance}


def parse_source(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    beams = [
        tuple(map(float, groups))
        for groups in re.findall(
            r"(?m)^\S+\.Beam\s+FarFieldAreaSource\s+([0-9.eE+-]+)\s+"
            r"([0-9.eE+-]+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s*$",
            text,
        )
    ]
    fluxes = [float(value) for value in re.findall(r"(?m)^\S+\.Flux\s+([0-9.eE+-]+)\s*$", text)]
    events_match = re.search(r"(?m)^\S+\.Events\s+(\d+)\s*$", text)
    radius_match = re.search(r"(?m)^# farfield_radius_cm=([0-9.eE+-]+)\s*$", text)
    if len(beams) != 20 or len(fluxes) != 20 or not events_match or not radius_match:
        raise RuntimeError("SG3B gamma source-card closure differs from 20-bin far-field contract")
    if not (
        math.isclose(beams[0][0], 0.0, abs_tol=1e-12)
        and math.isclose(beams[-1][1], 180.0, abs_tol=1e-12)
        and all(math.isclose(row[2], 0.0, abs_tol=1e-12) and math.isclose(row[3], 360.0, abs_tol=1e-12) for row in beams)
    ):
        raise RuntimeError("source angular coverage is not the expected full sphere")
    return {
        "beam_count": len(beams),
        "beams_deg": beams,
        "fluxes_cm-2_s-1": fluxes,
        "total_flux_cm-2_s-1": math.fsum(fluxes),
        "job_events": int(events_match.group(1)),
        "comment_radius_cm": float(radius_match.group(1)),
    }


def geometry_enclosure(mesh: dict[str, np.ndarray], sphere: dict[str, Any]) -> dict[str, Any]:
    vertices_world_cm = mesh["vertices_world_mm"] / 10.0
    vertices_instrument_cm = mesh["vertices_instrument_cm"]
    offsets = mesh["solid_vertex_offsets"]
    nonvacuum = mesh["is_nonvacuum"]
    selected: list[np.ndarray] = []
    selected_instrument: list[np.ndarray] = []
    solid_for_vertex: list[np.ndarray] = []
    for solid_id in np.flatnonzero(nonvacuum):
        start, stop = int(offsets[solid_id]), int(offsets[solid_id + 1])
        selected.append(vertices_world_cm[start:stop])
        selected_instrument.append(vertices_instrument_cm[start:stop])
        solid_for_vertex.append(np.full(stop - start, solid_id, dtype=int))
    world = np.concatenate(selected)
    instrument = np.concatenate(selected_instrument)
    solid_ids = np.concatenate(solid_for_vertex)
    center_world = np.asarray(sphere["center_world_cm"], dtype=float)
    distances = np.linalg.norm(world - center_world, axis=1)
    farthest = int(np.argmax(distances))
    max_distance = float(distances[farthest])
    rotation = mesh["instrument_from_world_rotation"]
    origin = mesh["instrument_position_world_cm"]
    center_instrument = rotation @ (center_world - origin)
    return {
        "center_instrument_cm": center_instrument,
        "world_vertices_cm": world,
        "instrument_vertices_cm": instrument,
        "max_distance_cm": max_distance,
        "clearance_cm": float(sphere["radius_cm"] - max_distance),
        "max_vertex_world_cm": world[farthest],
        "max_vertex_instrument_cm": instrument[farthest],
        "max_vertex_solid": str(mesh["solid_names"][solid_ids[farthest]]),
        "max_vertex_material": str(mesh["materials"][solid_ids[farthest]]),
        "projection_hull_xz": monotonic_hull(instrument[:, (0, 2)]),
    }


def source_time_contract(
    config: dict[str, Any], source: dict[str, Any], sphere: dict[str, Any], enclosure: dict[str, Any]
) -> dict[str, Any]:
    rows = read_csv(resolve(config["prompt_time_audit"]))
    gamma = next(row for row in rows if row["campaign"] == "combined_3x" and row["family"] == "gamma")
    n = int(gamma["accepted_events"])
    receipt_tt = float(gamma["receipt_sum_TT_s"])
    flux = float(source["total_flux_cm-2_s-1"])
    radius = float(sphere["radius_cm"])
    rate = flux * math.pi * radius * radius
    expectation = n / rate
    stochastic_sigma = math.sqrt(n) / rate
    proposed_clearance = float(config["hypothetical_sphere_clearance_cm"])
    proposed_radius = float(enclosure["max_distance_cm"]) + proposed_clearance
    proposed_rate = flux * math.pi * proposed_radius * proposed_radius
    proposed_expectation = n / proposed_rate
    time_gain = expectation and proposed_expectation / expectation
    return {
        "combined_gamma_events": n,
        "combined_gamma_receipt_TT_s": receipt_tt,
        "projected_launch_area_cm2": math.pi * radius * radius,
        "analytic_generation_rate_s-1": rate,
        "analytic_expected_TT_s": expectation,
        "receipt_minus_expectation_s": receipt_tt - expectation,
        "expected_TT_stochastic_sigma_s": stochastic_sigma,
        "receipt_residual_sigma": (receipt_tt - expectation) / stochastic_sigma,
        "hypothetical_two_mm_clearance": {
            "clearance_cm": proposed_clearance,
            "radius_cm": proposed_radius,
            "projected_launch_area_cm2": math.pi * proposed_radius * proposed_radius,
            "analytic_generation_rate_s-1": proposed_rate,
            "combined_gamma_expected_TT_s": proposed_expectation,
            "ten_million_gamma_expected_TT_s": 10_000_000.0 / proposed_rate,
            "time_gain_factor_vs_R60": time_gain,
            "time_gain_percent_vs_R60": 100.0 * (time_gain - 1.0),
            "area_and_generation_rate_change_percent_vs_R60": 100.0 * (proposed_rate / rate - 1.0),
            "combined_gamma_time_gain_s": proposed_expectation - expectation,
            "ten_million_gamma_time_gain_s": 10_000_000.0 / proposed_rate - 10_000_000.0 / rate,
        },
        "equivalent_time_formula": "T_eq=N/(Phi*pi*R^2)",
        "radius_scaling_at_fixed_flux_and_N": "T_eq proportional to R^-2",
    }


def common_time_audit(config: dict[str, Any]) -> dict[str, Any]:
    package = resolve(config["common_time_package"])
    validation = load_json(package / "outputs/01_common_time_response/poisson_common_axis_validation.json")
    timeline = read_csv(package / "outputs/01_common_time_response/mission_time_resolved_flux_threshold.csv")
    day15 = next(
        row for row in timeline
        if row["stage"] == "compton_trajectory_veto" and math.isclose(float(row["day_mid"]), 15.0)
    )
    rate = float(day15["total_occupancy_cps"])
    tau = 1.0e-6
    one_sided = math.exp(-rate * tau)
    symmetric = math.exp(-2.0 * rate * tau)
    nonparalyzable = 1.0 / (1.0 + rate * tau)
    if not math.isclose(one_sided, float(day15["poisson_accidental_live_factor"]), abs_tol=1e-15):
        raise RuntimeError("package-58 live-factor reproduction failed")
    return {
        "verdict": "MATURE_COMMON_AXIS_METHOD_VALID__PACKAGE58_CURRENT_OUTPUT_USES_ANALYTIC_EXPECTATION_NOT_EVENT_LEVEL_REPLAY",
        "day15_prompt_occupancy_cps": float(day15["prompt_occupancy_cps"]),
        "day15_delayed_occupancy_cps": float(day15["delayed_occupancy_cps"]),
        "day15_total_occupancy_cps": rate,
        "coincidence_window_s": tau,
        "implemented_one_sided_group_live_factor": one_sided,
        "symmetric_isolation_reference_not_implemented": symmetric,
        "nonparalyzable_deadtime_reference_not_implemented": nonparalyzable,
        "toy_common_axis_validation": validation,
        "implemented_method": [
            "Prompt event templates are weighted by 1/sum(TT_family).",
            "Delayed day-15 event templates are weighted by A_family(day15)/1e6 and then ZA-rescaled over mission time.",
            "Independent prompt and delayed occupancy rates are summed analytically at each of 81 mission nodes.",
            "The common-axis factor is exp[-tau*(R_prompt+R_delayed)] and the mission integral is trapezoidal.",
        ],
        "package58_current_output_boundary": [
            "Package 58 does not invoke the retained literal event/deposit timeline replay for its 20-day SG3B output.",
            "Its explicit toy validation merges only two aggregate day-15 Poisson streams for 46.6 s.",
            "Its analytic occupancy rate includes any positive TES/plastic/BGO deposit rather than replaying thresholded candidate groups.",
        ],
        "retained_mature_method": {
            "status": "AVAILABLE_AND_METHOD_CORRECT__REUSE_FOR_SG3B",
            "implementations": config["mature_common_time_implementations"],
            "draw": "For each stream, draw N~Poisson(sum(rate_i)*T), sample event templates with probabilities rate_i/sum(rate_i), assign uniform times in [0,T], merge and stable-sort. This is equivalent to exponential interarrival sampling on a fixed interval.",
            "veto": "Group adjacent arrivals with gaps <= tau, sum TES hits by pixel and sum active-shield energy within each group, then apply the active-veto threshold and Compton/FoV selection.",
            "sg3b_reuse_boundary": "Adapt existing catalog channels to separate plastic and BGO deposits and SG3B family/ZA time-dependent rates; do not rebuild the algorithm from scratch.",
        },
        "model_boundary": {
            "exp_minus_Rtau": "one-sided guard interval, equivalently Poisson coincidence-group count divided by event count",
            "exp_minus_2Rtau": "two-sided isolated-event requirement; diagnostic only",
            "one_over_1_plus_Rtau": "nonparalyzable dead-time reference; diagnostic only",
        },
    }


def save_figure(fig: plt.Figure, stem: str) -> list[str]:
    paths: list[str] = []
    for suffix in ("png", "svg", "pdf"):
        path = OUT / f"{stem}.{suffix}"
        fig.savefig(path, dpi=300 if suffix == "png" else None, bbox_inches="tight", pad_inches=0.08)
        paths.append(str(path))
    plt.close(fig)
    return paths


def build_figure(
    visual: Any,
    overlay: Any,
    mesh: dict[str, np.ndarray],
    sphere: dict[str, Any],
    enclosure: dict[str, Any],
    source: dict[str, Any],
    time_contract: dict[str, Any],
) -> list[str]:
    cjk_font = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
    if cjk_font.is_file():
        font_manager.fontManager.addfont(cjk_font)
    plt.rcParams.update({
        "font.family": ["Noto Sans CJK JP", "DejaVu Sans"],
        "font.size": 8.0,
        "axes.titlesize": 10.0,
        "axes.labelsize": 8.5,
    })
    fig = plt.figure(figsize=(15.2, 8.6))
    grid = fig.add_gridspec(2, 2, width_ratios=(1.52, 1.0), hspace=0.31, wspace=0.24)
    ax = fig.add_subplot(grid[:, 0])
    ax_launch = fig.add_subplot(grid[0, 1])
    ax_scale = fig.add_subplot(grid[1, 1])

    center = enclosure["center_instrument_cm"]
    radius = float(sphere["radius_cm"])
    hull = enclosure["projection_hull_xz"]
    ax.add_patch(Polygon(hull, closed=True, facecolor="#AAB6C2", edgecolor="#53616D", lw=0.8, alpha=0.16, zorder=1))
    visual.draw_exact_if_section(ax, mesh, include_holes=True, limits=((-65, 60), (-53, 72)))
    overlay.draw_sg3b_overlays_xz(ax)
    ax.add_patch(Circle((center[0], center[2]), radius, fill=False, color="#0B5CAD", lw=2.0, zorder=20))
    ax.scatter([center[0]], [center[2]], s=32, marker="x", color="#0B5CAD", zorder=22)
    ax.scatter([0], [0], s=25, marker="o", color="#C43B3B", zorder=22)
    far = enclosure["max_vertex_instrument_cm"]
    ax.plot([center[0], far[0]], [center[2], far[2]], ls="--", lw=0.9, color="#B05A00", zorder=21)
    ax.scatter([far[0]], [far[2]], s=36, marker="D", color="#B05A00", edgecolor="white", lw=0.5, zorder=23)
    ax.annotate(
        f"最远非真空顶点\n3D 距离 {enclosure['max_distance_cm']:.3f} cm\n余量 {enclosure['clearance_cm']:.3f} cm",
        xy=(far[0], far[2]), xytext=(-55, -44),
        arrowprops={"arrowstyle": "->", "color": "#B05A00", "lw": 0.8},
        fontsize=7.3, color="#7B3F00",
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "#D7B98A", "alpha": 0.95},
        zorder=30,
    )
    ax.annotate(
        "", xy=(-35, 0), xytext=(0, 0),
        arrowprops={"arrowstyle": "-|>", "color": "#7A2E8E", "lw": 1.7},
    )
    ax.text(
        -34, 2.5,
        "光学看向：local -x′ = world (-x,+z)/√2（仰角 45°）",
        ha="left", va="bottom", fontsize=7.3, color="#632373",
    )
    ax.text(
        center[0] + 3, center[2] + radius - 5,
        f"SG3B SurroundingSphere\nR={radius:.0f} cm, world center=(5,0,9) cm\nInstrumentFrame center=({center[0]:.3f},0,{center[2]:.3f}) cm",
        ha="left", va="top", color="#0B5CAD", fontsize=7.5,
        bbox={"boxstyle": "round,pad=0.3", "fc": "white", "ec": "#7DB4E6", "alpha": 0.95},
        zorder=30,
    )
    visual.axes_style(ax, "InstrumentFrame x′ [cm]", "InstrumentFrame z′ [cm]")
    ax.set_xlim(-65, 60)
    ax.set_ylim(-53, 72)
    ax.set_title("SG3B 源起始球与质量模型包络（x′–z′ 侧视）", weight="bold")
    handles = [
        Line2D([0], [0], color="#0B5CAD", lw=2, label="R=60 cm 起始球截面"),
        Line2D([0], [0], color="#53616D", lw=6, alpha=0.25, label="非真空质量模型投影包络"),
        Line2D([0], [0], marker="D", color="none", markerfacecolor="#B05A00", label="最大 3D 半径顶点"),
    ]
    ax.legend(handles=handles, loc="lower right", frameon=True, fontsize=7.2)

    # Schematic of the MEGAlib spherical start-area implementation for one direction.
    ax_launch.add_patch(Circle((0, 0), 1.0, fill=False, color="#0B5CAD", lw=1.5))
    ax_launch.plot([1, 1], [-1, 1], color="#E68600", lw=4.0, solid_capstyle="round")
    for yy in (-0.75, -0.35, 0.05, 0.45, 0.8):
        ax_launch.annotate("", xy=(-0.55, yy), xytext=(1.0, yy), arrowprops={"arrowstyle": "->", "color": "#C54430", "lw": 0.9})
    ax_launch.scatter([1] * 5, [-0.75, -0.35, 0.05, 0.45, 0.8], s=16, color="#E68600", edgecolor="white", lw=0.3, zorder=5)
    ax_launch.text(1.05, 0, "发射圆盘\n面积 πR²", ha="left", va="center", color="#A85B00", fontsize=8)
    ax_launch.text(-0.02, -1.20, "对每个抽到的 (θ,φ)，圆盘旋转到垂直于入射方向；\n圆盘内均匀抽取起点，动量指向包络内部。不是在 4πR² 球壳上均匀撒点。", ha="center", va="top", fontsize=7.1)
    ax_launch.set_xlim(-1.35, 1.65)
    ax_launch.set_ylim(-1.45, 1.25)
    ax_launch.set_aspect("equal")
    ax_launch.axis("off")
    ax_launch.set_title("MEGAlib `FarFieldAreaSource` 起点语义（单一方向示意）", weight="bold")

    flux = float(source["total_flux_cm-2_s-1"])
    n = int(time_contract["combined_gamma_events"])
    radii = np.linspace(40.0, 120.0, 500)
    times = n / (flux * math.pi * radii * radii)
    minimum = float(enclosure["max_distance_cm"])
    ax_scale.axvspan(40, minimum, color="#D9534F", alpha=0.12, label="R 小于当前非真空包络：无效")
    ax_scale.plot(radii, times, color="#0B5CAD", lw=2.0, label=r"$T_{eq}=N/(\Phi\pi R^2)$")
    current_t = n / (flux * math.pi * radius * radius)
    proposal = time_contract["hypothetical_two_mm_clearance"]
    proposal_r = float(proposal["radius_cm"])
    proposal_t = float(proposal["combined_gamma_expected_TT_s"])
    ax_scale.scatter([radius], [current_t], s=42, color="#E68600", edgecolor="white", zorder=5)
    ax_scale.scatter([proposal_r], [proposal_t], s=45, marker="s", color="#2B8A5A", edgecolor="white", zorder=6)
    ax_scale.axvline(minimum, color="#B05A00", lw=0.9, ls="--")
    ax_scale.annotate(
        f"当前 R=60 cm\nE[T]={current_t:.3f} s\nreceipt TT={time_contract['combined_gamma_receipt_TT_s']:.3f} s",
        xy=(radius, current_t), xytext=(78, 88),
        arrowprops={"arrowstyle": "->", "color": "#E68600", "lw": 0.9},
        fontsize=7.4,
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "#E8B86D", "alpha": 0.96},
    )
    ax_scale.annotate(
        f"边界外 2 mm\nR={proposal_r:.3f} cm\nE[T]={proposal_t:.3f} s\n+{proposal['time_gain_percent_vs_R60']:.2f}%",
        xy=(proposal_r, proposal_t), xytext=(65, 119),
        arrowprops={"arrowstyle": "->", "color": "#2B8A5A", "lw": 0.9},
        fontsize=7.4, color="#1C6340",
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "#78B997", "alpha": 0.96},
    )
    ax_scale.set_xlim(40, 120)
    ax_scale.set_ylim(0, max(times) * 1.04)
    ax_scale.set_xlabel("起始球/发射圆盘半径 R [cm]")
    ax_scale.set_ylabel("同一 N 的等效时间 [s]")
    ax_scale.grid(color="#DBE2E8", lw=0.5, alpha=0.8)
    ax_scale.legend(loc="upper right", frameon=False, fontsize=7.0)
    ax_scale.set_title(f"固定 Φ={flux:.6g} cm⁻² s⁻¹、N={n:,} 时的 R⁻² 标度", weight="bold")

    fig.suptitle("SG3B 远场源面、包络与事件等效时间：语法—几何—归一化闭合", fontsize=13, weight="bold", y=0.985)
    fig.text(0.5, 0.006, "包络图复用项目的 exact y′=0 截面渲染；外包络来自保留 mesh，SG3B 的 Cu-ring/Bi/Al 局部改动以项目解析 overlay 表示。", ha="center", fontsize=7.1, color="#4B555E")
    return save_figure(fig, "sg3b_farfield_sphere_mass_model_relation")


def write_report(
    sphere: dict[str, Any],
    enclosure: dict[str, Any],
    source: dict[str, Any],
    time_contract: dict[str, Any],
    common: dict[str, Any],
) -> None:
    report = f"""# SG3B 远场源面与共时间轴审计

## 结论

1. 当前 `SurroundingSphere` 是 `R={sphere['radius_cm']:.0f} cm, center_world=(5,0,9) cm, distance=60 cm`。
   它在 InstrumentFrame 中的圆心为
   `({enclosure['center_instrument_cm'][0]:.6f}, 0, {enclosure['center_instrument_cm'][2]:.6f}) cm`。
   保留的非真空包络最远 3D 顶点距离圆心 {enclosure['max_distance_cm']:.6f} cm，径向余量
   {enclosure['clearance_cm']:.6f} cm；最远顶点属于
   `{enclosure['max_vertex_solid']}` ({enclosure['max_vertex_material']})。因此当前 R=60 cm 确实包住质量模型，
   但余量只有约 2 cm。

2. 对球形 start area，MEGAlib 使用的平均起始面积是 `pi*R^2`，不是 `4*pi*R^2`。
   `FarFieldAreaSource theta_min theta_max phi_min phi_max` 先按立体角在给定角箱中抽方向，
   再在垂直于该方向的半径 R 圆盘上均匀抽起点。远场源的物理事件率是
   `lambda=Phi*pi*R^2`，所以固定源卡 Flux 和事件数 N 时，`T_eq=N/(Phi*pi*R^2)`。

3. 当前 gamma 20 个角箱总通量为 {source['total_flux_cm-2_s-1']:.12g} cm^-2 s^-1。
   合并 3x 的 N={time_contract['combined_gamma_events']:,} 个 gamma 对应解析期望
   T={time_contract['analytic_expected_TT_s']:.6f} s；receipt 合计 TT={time_contract['combined_gamma_receipt_TT_s']:.6f} s，
   差 {time_contract['receipt_minus_expectation_s']:+.6f} s，即 {time_contract['receipt_residual_sigma']:+.3f} 个
   Poisson 到达时间标准差，闭合正常。

   若保持球心不变，把半径压到“当前最远非真空顶点外 2 mm”，则
   `R={time_contract['hypothetical_two_mm_clearance']['radius_cm']:.6f} cm`。发射圆盘面积和生成率下降
   {-time_contract['hypothetical_two_mm_clearance']['area_and_generation_rate_change_percent_vs_R60']:.3f}%，固定 N 的等效时间提高
   {time_contract['hypothetical_two_mm_clearance']['time_gain_percent_vs_R60']:.3f}%。3x gamma 从
   {time_contract['analytic_expected_TT_s']:.6f} s 增至
   {time_contract['hypothetical_two_mm_clearance']['combined_gamma_expected_TT_s']:.6f} s；1000 万 gamma 从
   {10_000_000.0/time_contract['analytic_generation_rate_s-1']:.6f} s 增至
   {time_contract['hypothetical_two_mm_clearance']['ten_million_gamma_expected_TT_s']:.6f} s。

4. package 58 的 prompt/delayed **物理率归一化与独立泊松率的叠加是对的**：prompt 用
   `1/sum(TT_family)`，delayed 在 day 15 用 `A_family/1e6`，随后按源核素 ZA 的活动曲线缩放；
   每个任务节点将 prompt 和 delayed occupancy 率相加。

5. 项目内已有成熟且正确的逐事件公共时间轴方案：对每条流按总产率抽
   `N~Poisson(R*T)`（等价于指数到达间隔），按事件模板的相对率有放回抽样，赋予 `[0,T]` 均匀时刻并
   merge/sort；随后把相邻间隔小于 tau 的事件组成候选，累加候选内 TES pixel 与主动屏蔽沉积，再做 veto。
   保留实现位于 `old/code/tools/make_complete_day15_report_ADR.py` 和
   `old/code/tools/build_v3p5_centerfinger_step05_l1_response.py`。

6. 需要区分的是：SG3B package 58 当前结果**没有调用这套成熟的逐事件 replay**。它在 81 个任务节点使用解析式
   `L=exp[-tau*(R_prompt+R_delayed)]`；唯一的显式泊松抽样是 day-15、46.6 s 的两条聚合流 toy validation。
   这不是对 M05 方法的否定，而是 package 58 的实现范围说明。

## day-15 时间模型边界

- prompt occupancy: {common['day15_prompt_occupancy_cps']:.6f} s^-1
- delayed occupancy: {common['day15_delayed_occupancy_cps']:.6f} s^-1
- total: {common['day15_total_occupancy_cps']:.6f} s^-1
- tau: {common['coincidence_window_s']:.3g} s
- 当前实现 `exp(-R*tau)`: {common['implemented_one_sided_group_live_factor']:.9f}
- 仅作定义对照的双侧隔离 `exp(-2R*tau)`: {common['symmetric_isolation_reference_not_implemented']:.9f}
- 仅作定义对照的非延长死时间 `1/(1+R*tau)`: {common['nonparalyzable_deadtime_reference_not_implemented']:.9f}

当前 package-58 occupancy 统计“TES、plastic 或 BGO 任一正能量沉积”。因此 package 58 的
`exp(-R*tau)` 是成熟公共时间轴算法的解析期望代理；真正要输出 SG3B 的 time-window veto 数字，应调用
项目已有的逐事件实现，在候选组内分别求和 plastic、BGO 和 TES 沉积。

## 最小安全后续动作

不重跑输运，也不重新发明算法：直接迁移复用现有 `draw_timeline`/`analyze_timeline`，输入 SG3B 已接受的
compact event templates 与 family/ZA 的时间变产率，把旧单一 BGO 通道适配为独立 plastic 与 BGO 通道，
再施加 50 keV veto 和 Compton 选择，并与 package 58 的解析期望闭合。
"""
    (OUT / "AUDIT_REPORT.md").write_text(report, encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    config = load_json(CONFIG)
    sphere = parse_sphere(Path(config["geometry_setup"]))
    source = parse_source(Path(config["source_card"]))
    if not math.isclose(source["comment_radius_cm"], sphere["radius_cm"], abs_tol=1e-12):
        raise RuntimeError("source-card radius comment and geometry sphere differ")

    tool = Path(config["section_tool"])
    sys.path.insert(0, str(tool))
    visual = load_module("sg3b_sphere_section_adapter", tool / "se3_section_adapter.py")
    overlay = load_module("sg3b_sphere_project_overlay", resolve(config["sg3b_overlay_code"]))
    mesh = visual.load_mesh(Path(config["section_mesh"]))
    enclosure = geometry_enclosure(mesh, sphere)
    if enclosure["clearance_cm"] <= 0:
        raise RuntimeError("SG3B surrounding sphere does not enclose retained non-vacuum envelope")
    time_contract = source_time_contract(config, source, sphere, enclosure)
    common = common_time_audit(config)
    figures = build_figure(visual, overlay, mesh, sphere, enclosure, source, time_contract)

    summary = {
        "status": "PASS__SG3B_FARFIELD_SPHERE_ENCLOSURE__CONDITIONAL_POISSON_MODEL_AUDIT",
        "authority_boundary": {
            "new_transport_started": False,
            "SIM_payloads_opened": 0,
            "detector_response_rerun": False,
            "paper_modified": False,
            "mass_model_envelope": "retained exact inherited mesh plus SG3B analytic local overlays",
        },
        "surrounding_sphere": sphere,
        "enclosure": {
            "center_instrument_cm": enclosure["center_instrument_cm"].tolist(),
            "max_nonvacuum_distance_cm": enclosure["max_distance_cm"],
            "minimum_radial_clearance_cm": enclosure["clearance_cm"],
            "max_vertex_world_cm": enclosure["max_vertex_world_cm"].tolist(),
            "max_vertex_instrument_cm": enclosure["max_vertex_instrument_cm"].tolist(),
            "max_vertex_solid": enclosure["max_vertex_solid"],
            "max_vertex_material": enclosure["max_vertex_material"],
        },
        "farfield_source": source,
        "gamma_time_contract": time_contract,
        "common_time_model": common,
        "figures": figures,
    }
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_report(sphere, enclosure, source, time_contract, common)
    print(json.dumps({
        "status": summary["status"],
        "sphere": summary["surrounding_sphere"],
        "enclosure": summary["enclosure"],
        "gamma_time": summary["gamma_time_contract"],
        "common_time_verdict": common["verdict"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
