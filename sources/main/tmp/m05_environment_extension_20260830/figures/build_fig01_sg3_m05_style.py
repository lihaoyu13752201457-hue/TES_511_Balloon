#!/usr/bin/env python3
"""Render mass models A and B as a matched Figure-1 geometry comparison."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib import font_manager
from matplotlib.patches import Patch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
WRL_A = HERE / "source/sg3b_native_no_transport.wrl"
WRL_B = (
    REPO
    / "engineering/geometry_optimization_20260815/sh3/assembly_opt_v3/figures"
    / "SH3_Chimney_DR_Assembly_OptV3.wrl"
)
FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"

INK = "#263746"
DEEP_BLUE = "#1F4E79"
RED = "#D84232"

PALETTE = {
    "tes": "#B51F2E",
    "w": "#20262C",
    "bi": "#8B5FBF",
    "bgo": "#2FA66F",
    "window": "#3C8FC7",
    "cu_link": "#D9792B",
    "cu_stage": "#C98A43",
    "external_support": "#58727D",
    "support": "#6E8894",
    "al_local": "#6FA8CC",
    "envelope": "#86B4D6",
    "service": "#7C8993",
    "bpe": "#B8A85A",
    "plastic": "#65B77B",
}

ALPHA_FULL = {
    "tes": 0.98,
    "w": 0.92,
    "bi": 0.82,
    "bgo": 0.075,
    "window": 0.36,
    "cu_link": 0.82,
    "cu_stage": 0.43,
    "external_support": 0.17,
    "support": 0.20,
    "al_local": 0.18,
    "envelope": 0.025,
    "service": 0.18,
}

ALPHA_DETAIL = {
    "tes": 1.00,
    "w": 0.96,
    "bi": 0.80,
    "bgo": 0.035,
    "window": 0.48,
    "cu_link": 0.90,
    "cu_stage": 0.25,
    "external_support": 0.17,
    "support": 0.00,
    "al_local": 0.16,
    "envelope": 0.00,
    "service": 0.00,
}


font_manager.fontManager.addfont("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")

mpl.rcParams.update(
    {
        "font.family": "Noto Sans CJK JP",
        "font.size": 8.2,
        "axes.titlesize": 10.0,
        "text.color": INK,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "pdf.fonttype": 3,
        "ps.fonttype": 42,
    }
)


@dataclass
class Solid:
    name: str
    category: str
    points: np.ndarray
    faces: list[np.ndarray]

    @property
    def centre(self) -> np.ndarray:
        return np.median(self.points, axis=0)

    @property
    def local_bounds(self) -> tuple[np.ndarray, np.ndarray]:
        local = world_to_local(self.points)
        return local.min(axis=0), local.max(axis=0)


def world_to_local(points: np.ndarray) -> np.ndarray:
    """Undo the 45-degree InstrumentFrame rotation; all coordinates remain in mm."""
    out = np.empty_like(points, dtype=float)
    inv_sqrt2 = 2**-0.5
    out[:, 0] = (points[:, 0] - points[:, 2]) * inv_sqrt2
    out[:, 1] = points[:, 1]
    out[:, 2] = (points[:, 0] + points[:, 2]) * inv_sqrt2
    return out


def local_to_world(points: np.ndarray) -> np.ndarray:
    """Apply the 45-degree InstrumentFrame rotation to local coordinates."""
    out = np.empty_like(points, dtype=float)
    inv_sqrt2 = 2**-0.5
    out[:, 0] = (points[:, 0] + points[:, 2]) * inv_sqrt2
    out[:, 1] = points[:, 1]
    out[:, 2] = (points[:, 2] - points[:, 0]) * inv_sqrt2
    return out


def classify(name: str) -> str:
    n = name.lower()
    if n.startswith("tp_l"):
        return "tes"
    if (
        "multihole_collimator" in n
        or "passive_w_" in n
        or "tungsten" in n
        or "_w_frame_" in n
    ):
        return "w"
    if "sg3b_bi_" in n or "bismuth" in n:
        return "bi"
    if "bgo_mechanicalal" in n:
        return "envelope"
    if ("bgo_" in n or "bgo40_" in n) and "kapton" not in n and "outer_al" not in n:
        return "bgo"
    if "bpe" in n:
        return "bpe"
    if "plastic" in n:
        return "plastic"
    if n.startswith("win_") or "beryllium" in n or "opticalwindow" in n or "opticalfilter" in n:
        return "window"
    if any(
        key in n
        for key in (
            "substratesupport",
            "coldfinger",
            "heat_sink",
            "heatsink",
            "thermal_link",
            "thermal_finger",
        )
    ):
        return "cu_link"
    if (
        n.startswith("cu_")
        or "_cu_" in n
        or n.endswith("_cu.0")
        or "coldplate_mxc" in n
        or "mixingchamber_cu" in n
        or "sinter_hex_agproxy" in n
    ):
        return "cu_stage"
    if n.startswith("nf2_outersupport"):
        return "external_support"
    if "supportrod" in n or "hardpoint" in n:
        return "support"
    if any(key in n for key in ("se3_al_shield_inner", "sg3a_al_50mk_stilllike")):
        return "al_local"
    if any(key in n for key in ("shield", "shell", "jacket", "coldplate", "plate_", "_can_", "_can.", "outer_al")):
        return "envelope"
    return "service"


def parse_wrl(path: Path) -> list[Solid]:
    text = path.read_text(encoding="utf-8")
    solids: list[Solid] = []
    for block in text.split("#---------- SOLID: ")[1:]:
        name = block.splitlines()[0].strip()
        point_match = re.search(r"point\s*\[(.*?)\]\s*}", block, re.S)
        index_match = re.search(r"coordIndex\s*\[(.*?)\]\s*solid", block, re.S)
        if not point_match or not index_match:
            continue
        values = np.asarray([float(item) for item in re.findall(FLOAT, point_match.group(1))])
        if len(values) % 3:
            raise RuntimeError(f"malformed coordinate list: {name}")
        points = values.reshape(-1, 3)
        indices = [int(item) for item in re.findall(r"-?\d+", index_match.group(1))]
        faces: list[np.ndarray] = []
        current: list[int] = []
        for index in indices:
            if index == -1:
                if len(current) >= 3:
                    faces.append(np.asarray(current, dtype=np.int32))
                current = []
            else:
                current.append(index)
        if current:
            faces.append(np.asarray(current, dtype=np.int32))
        if faces:
            solids.append(Solid(name=name, category=classify(name), points=points, faces=faces))
    if not solids:
        raise RuntimeError(f"no solids parsed from {path}")
    return solids


def camera_basis(azimuth_deg: float, elevation_deg: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    az = np.deg2rad(azimuth_deg)
    el = np.deg2rad(elevation_deg)
    depth = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
    right = np.array([-np.sin(az), np.cos(az), 0.0])
    up = np.cross(depth, right)
    up /= np.linalg.norm(up)
    return right, up, depth


def project(points: np.ndarray, basis: tuple[np.ndarray, np.ndarray, np.ndarray]) -> np.ndarray:
    right, up, depth = basis
    return np.column_stack((points @ right, points @ up, points @ depth))


def intersects_comparison_box(solid: Solid) -> bool:
    lower, upper = solid.local_bounds
    box_lower = np.array([-500.0, -235.0, -180.0])
    box_upper = np.array([240.0, 235.0, 410.0])
    return bool(np.all(upper >= box_lower) and np.all(lower <= box_upper))


def comparison_limits(
    basis: tuple[np.ndarray, np.ndarray, np.ndarray],
    solids: list[Solid],
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return one physical viewport shared by both mass-model panels."""
    lower = np.array([-500.0, -235.0, -180.0])
    upper = np.array([240.0, 235.0, 410.0])
    corners = np.asarray(
        [
            [x, y, z]
            for x in (lower[0], upper[0])
            for y in (lower[1], upper[1])
            for z in (lower[2], upper[2])
        ]
    )
    projected = project(local_to_world(corners), basis)[:, :2]
    xmin, ymin = projected.min(axis=0)
    xmax, ymax = projected.max(axis=0)
    external_support = [solid for solid in solids if solid.category == "external_support"]
    if external_support:
        support_points = np.vstack([solid.points for solid in external_support])
        support_projected = project(support_points, basis)[:, :2]
        support_min = support_projected.min(axis=0)
        support_max = support_projected.max(axis=0)
        xmin = min(xmin, float(support_min[0]))
        ymin = min(ymin, float(support_min[1]))
        xmax = max(xmax, float(support_max[0]))
        ymax = max(ymax, float(support_max[1]))
    pad_mm = 15.0
    return (xmin - pad_mm, xmax + pad_mm), (ymin - pad_mm, ymax + pad_mm)


def render_panel(
    ax,
    solids: list[Solid],
    *,
    model: str,
    scale_bar_mm: float,
    view_limits: tuple[tuple[float, float], tuple[float, float]],
) -> tuple[tuple[np.ndarray, np.ndarray, np.ndarray], list[Solid]]:
    basis = camera_basis(-132.0, 18.0)
    chosen = [
        solid
        for solid in solids
        if solid.category not in {"bpe", "plastic", "support"}
        and (solid.category == "external_support" or intersects_comparison_box(solid))
    ]
    if model == "A":
        chosen = [
            solid
            for solid in chosen
            if solid.category != "w" or "multihole_collimator" in solid.name.lower()
        ]
    elif model == "B":
        chosen = [
            solid
            for solid in chosen
            if solid.category != "w" or "_w_frame_" in solid.name.lower()
        ]
    else:
        raise ValueError(f"unknown mass model: {model}")
    alpha_map = ALPHA_FULL

    polygons: list[np.ndarray] = []
    colours: list[tuple[float, float, float, float]] = []
    depths: list[float] = []
    light = np.array([0.25, -0.35, 0.90])
    light /= np.linalg.norm(light)
    for solid in chosen:
        projected_points = project(solid.points, basis)
        base = np.asarray(mpl.colors.to_rgb(PALETTE[solid.category]))
        alpha = alpha_map[solid.category]
        if solid.category == "external_support":
            name = solid.name.lower()
            if "_g10_rod_" in name:
                alpha = 0.34
            elif "_ss_hardpoint_" in name:
                alpha = 0.42
        for face in solid.faces:
            vertices = solid.points[face]
            normal = np.cross(vertices[1] - vertices[0], vertices[2] - vertices[0])
            norm = np.linalg.norm(normal)
            if norm:
                normal /= norm
            intensity = 0.70 + 0.30 * abs(float(normal @ light))
            polygons.append(projected_points[face, :2])
            colours.append((*np.clip(base * intensity, 0.0, 1.0), alpha))
            depths.append(float(projected_points[face, 2].mean()))
    order = np.argsort(depths)
    collection = PolyCollection(
        [polygons[index] for index in order],
        facecolors=[colours[index] for index in order],
        edgecolors="none",
        linewidths=0.0,
        rasterized=True,
    )
    ax.add_collection(collection)

    xlim, ylim = view_limits
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")

    xmin, xmax = xlim
    ymin, ymax = ylim
    bar_x = xmin + 0.045 * (xmax - xmin)
    bar_y = ymin + 0.045 * (ymax - ymin)
    ax.plot([bar_x, bar_x + scale_bar_mm], [bar_y, bar_y], color=INK, lw=2.2, solid_capstyle="butt", zorder=50)
    ax.text(bar_x + scale_bar_mm / 2, bar_y + 0.018 * (ymax - ymin), f"{int(scale_bar_mm)} mm", ha="center", va="bottom", fontsize=8.1, zorder=51)
    return basis, chosen


def category_centre(solids: list[Solid], predicate) -> np.ndarray:
    selected = [solid.centre for solid in solids if predicate(solid)]
    if not selected:
        raise RuntimeError("annotation target not found")
    return np.median(np.asarray(selected), axis=0)


def label_target(ax, text: str, point: np.ndarray, basis, offset: tuple[float, float], colour: str = INK) -> None:
    xy = project(point[None, :], basis)[0, :2]
    ax.annotate(
        text,
        xy=xy,
        xytext=offset,
        textcoords="offset points",
        ha="center",
        va="center",
        fontsize=8.5,
        color=colour,
        arrowprops={"arrowstyle": "-", "color": colour, "lw": 0.75},
        bbox={"boxstyle": "round,pad=0.18", "fc": "white", "ec": "none", "alpha": 0.88},
        zorder=80,
    )


TEXT = {
    "en": {
        "title_a": "a  Mass model A: TES below cold stages",
        "title_b": "b  Mass model B: TES in lateral chimney",
        "a_tes": "six-layer TES\nbelow cold stages",
        "a_w": "multihole\nW collimator",
        "a_bgo": "active BGO",
        "b_tes": "six-layer TES\nin side chimney",
        "b_w": "open W\nfocal frame",
        "b_bgo": "three-part\nactive BGO",
        "beam": "focused 511 keV photons",
        "legend": ("active BGO", "Al / cryostat envelopes", "outer support frame", "cold Cu structures", "Bi shield (A)", "TES Ta absorbers", "W collimator / frame"),
    },
    "zh": {
        "title_a": "a  质量模型 A：TES 位于冷盘下方",
        "title_b": "b  质量模型 B：TES 移入侧烟囱",
        "a_tes": "六层 TES\n位于冷盘下方",
        "a_w": "多孔 W\n准直器",
        "a_bgo": "主动 BGO",
        "b_tes": "六层 TES\n位于侧烟囱内",
        "b_w": "开放式 W\n焦面框",
        "b_bgo": "三体主动\nBGO",
        "beam": "聚焦 511 keV 光子",
        "legend": ("主动 BGO", "Al / 低温包络", "外部支架", "冷端 Cu 结构", "Bi 屏蔽（A）", "TES Ta 吸收体", "W 准直器 / 焦面框"),
    },
}


def add_beam(ax, tes: np.ndarray, aperture: np.ndarray, basis) -> None:
    p_tes = project(tes[None, :], basis)[0, :2]
    p_aperture = project(aperture[None, :], basis)[0, :2]
    p_start = p_aperture + 0.28 * (p_aperture - p_tes)
    ax.annotate(
        "",
        xy=p_tes,
        xytext=p_start,
        arrowprops={"arrowstyle": "-|>", "color": RED, "lw": 1.8},
        zorder=90,
    )


def build(language: str, solids_a: list[Solid], solids_b: list[Solid]) -> None:
    words = TEXT[language]
    fig, axes = plt.subplots(1, 2, figsize=(7.28, 4.28), gridspec_kw={"wspace": 0.025})
    shared_basis = camera_basis(-132.0, 18.0)
    view_limits = comparison_limits(shared_basis, solids_a + solids_b)
    basis_a, shown_a = render_panel(axes[0], solids_a, model="A", scale_bar_mm=200.0, view_limits=view_limits)
    basis_b, shown_b = render_panel(axes[1], solids_b, model="B", scale_bar_mm=200.0, view_limits=view_limits)
    assert sum(solid.category == "external_support" for solid in shown_a) == 20
    assert sum(solid.category == "external_support" for solid in shown_b) == 20
    axes[0].text(0.0, 1.015, words["title_a"], transform=axes[0].transAxes, ha="left", va="bottom", fontsize=10.2, fontweight="bold")
    axes[1].text(0.0, 1.015, words["title_b"], transform=axes[1].transAxes, ha="left", va="bottom", fontsize=10.2, fontweight="bold")

    tes_a = category_centre(shown_a, lambda solid: solid.category == "tes")
    w_a = category_centre(shown_a, lambda solid: solid.category == "w")
    tes_b = category_centre(shown_b, lambda solid: solid.category == "tes")
    w_b = category_centre(shown_b, lambda solid: solid.category == "w")

    add_beam(axes[0], tes_a, w_a, basis_a)
    add_beam(axes[1], tes_b, w_b, basis_b)

    legend_labels = words["legend"]
    legend_handles = [
        Patch(facecolor=PALETTE["bgo"], alpha=0.45, label=legend_labels[0]),
        Patch(facecolor=PALETTE["envelope"], alpha=0.42, label=legend_labels[1]),
        Patch(facecolor=PALETTE["external_support"], alpha=0.45, label=legend_labels[2]),
        Patch(facecolor=PALETTE["cu_stage"], alpha=0.82, label=legend_labels[3]),
        Patch(facecolor=PALETTE["bi"], alpha=0.82, label=legend_labels[4]),
        Patch(facecolor=PALETTE["tes"], alpha=0.98, label=legend_labels[5]),
        Patch(facecolor=PALETTE["w"], alpha=0.96, label=legend_labels[6]),
    ]
    fig.legend(handles=legend_handles, loc="lower center", bbox_to_anchor=(0.5, -0.004), ncol=4, frameon=False, columnspacing=0.76, handlelength=1.05, fontsize=7.8)
    fig.subplots_adjust(bottom=0.165, top=0.92, left=0.005, right=0.995)
    stem = HERE / f"fig01_mass_models_ab_{language}"
    fig.savefig(stem.with_suffix(".pdf"), dpi=400, bbox_inches="tight", pad_inches=0.03)
    fig.savefig(stem.with_suffix(".png"), dpi=400, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)


def main() -> int:
    solids_a = parse_wrl(WRL_A)
    solids_b = parse_wrl(WRL_B)
    build("en", solids_a, solids_b)
    build("zh", solids_a, solids_b)
    print(
        f"rendered mass model A ({len(solids_a)} solids; {WRL_A.name}) and "
        f"mass model B ({len(solids_b)} solids; {WRL_B.name})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
