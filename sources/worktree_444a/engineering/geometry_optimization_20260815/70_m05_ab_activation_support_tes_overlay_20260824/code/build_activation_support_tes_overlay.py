#!/usr/bin/env python3
"""Plot all transported activation-source support and the TES-impacting subset.

For each current mass model, the pale layer contains every source block retained
by the stride-5 delayed-source catalogue (10,000 blocks per incident family).
Coincident blocks are aggregated without losing their multiplicity or activity.
The coloured overlay contains mother-nuclide locations of delayed events that
survive the current final-W2 response selection.

Only compact CSV/JSON inputs and retained native WRL meshes are read.  This
script never opens a SIM file and never starts transport.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.legend_handler import HandlerTuple
from matplotlib.lines import Line2D


HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
REPO = PACKAGE.parents[2]
OUTPUTS = PACKAGE / "outputs"
BASE_SCRIPT = (
    REPO
    / "engineering/geometry_optimization_20260815"
    / "68_m05_ab_detailed_activation_sections_20260824/code"
    / "build_ab_detailed_activation_sections.py"
)

MANIFEST_A = Path(
    "/mnt/data/TES_Balloon_511_data/SG3/sg3b_m05_delayed_1m_v1/"
    "generated/activation/manifest.json"
)
MANIFEST_B = Path(
    "/mnt/data/TES_Balloon_511_data/SH3/sh3_optv3_m05_delayed_activation_v1/"
    "generated/activation/manifest.json"
)

INK = "#263746"
MUTED = "#647580"
GRID = "#DCE4E9"
ALL_SOURCE_COLOUR = "#3F7FA9"
OTHER_SELECTED_COLOUR = "#9B4F88"

GEOMETRY_STYLE = {
    "envelope": ("#8DA9B9", 0.40, 0.48, "低温与 Al 包络"),
    "al_local": ("#4F93BF", 0.72, 0.64, "Al 烟囱／局部壳层"),
    "support": ("#7E8C94", 0.60, 0.54, "结构支撑"),
    "service": ("#A7ADB2", 0.46, 0.42, "其他内部结构"),
    "silicon": ("#CFB43F", 0.82, 0.58, "Si 衬底"),
    "cu_stage": ("#C78632", 0.86, 0.72, "Cu 冷台／稀释制冷机"),
    "cu_link": ("#E06F2B", 0.96, 0.82, "Cu 支撑环／热连接"),
    "window": ("#2E83B9", 0.86, 0.70, "窗口"),
    "bgo": ("#2B9B69", 0.90, 0.76, "BGO 主动屏蔽"),
    "bpe": ("#9A9040", 0.60, 0.58, "含硼聚乙烯"),
    "plastic": ("#45A976", 0.68, 0.58, "塑料闪烁体"),
    "bi": ("#8B5FBF", 0.98, 0.98, "Bi 屏蔽"),
    "w": ("#22282D", 1.00, 1.08, "W 准直／框架"),
    "tes": ("#B51F2E", 1.00, 0.94, "TES 吸收体"),
    "hole": ("#2C66A5", 0.62, 0.43, "冷盘孔边界"),
}

DRAW_ORDER = [
    "envelope",
    "bpe",
    "plastic",
    "support",
    "service",
    "al_local",
    "silicon",
    "cu_stage",
    "cu_link",
    "window",
    "bgo",
    "hole",
    "bi",
    "w",
    "tes",
]

@dataclass
class SupportSite:
    family: str
    nuclide: str
    volume: str
    x_cm: float
    y_cm: float
    z_cm: float
    blocks: int
    activity_bq: float


@dataclass
class SupportLayer:
    sites: list[SupportSite]
    source_blocks: int
    unique_nuclides: int
    unique_volumes: int
    included_state_rows: int
    total_activity_bq: float
    family_activity_bq: dict[str, float]


@dataclass
class FigureSpec:
    key: str
    model_name: str
    title: str
    manifest: Path
    wrl: Path
    expected_solids: int
    tes_center_cm: tuple[float, float]
    support: SupportLayer
    selected: list[Any]
    selected_rate_cps: float


def import_base() -> Any:
    spec = importlib.util.spec_from_file_location("m05_ab_section_base", BASE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {BASE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BASE = import_base()

ELEMENT_SYMBOLS = BASE.ELEMENT_SYMBOLS + [
    "At",
    "Rn",
    "Fr",
    "Ra",
    "Ac",
    "Th",
    "Pa",
    "U",
    "Np",
    "Pu",
    "Am",
    "Cm",
    "Bk",
    "Cf",
    "Es",
    "Fm",
    "Md",
    "No",
    "Lr",
    "Rf",
    "Db",
    "Sg",
    "Bh",
    "Hs",
    "Mt",
    "Ds",
    "Rg",
    "Cn",
    "Nh",
    "Fl",
    "Mc",
    "Lv",
    "Ts",
    "Og",
]


def za_to_nuclide(value: str) -> str:
    za = int(float(value))
    atomic_number, mass_number = divmod(za, 1000)
    if not 0 < atomic_number < len(ELEMENT_SYMBOLS):
        return f"Z{atomic_number}-{mass_number}"
    return f"{ELEMENT_SYMBOLS[atomic_number]}-{mass_number}"


def configure_matplotlib() -> None:
    font_path = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
    if font_path.exists():
        mpl.font_manager.fontManager.addfont(str(font_path))
        family = "Noto Sans CJK JP"
    else:
        family = "DejaVu Sans"
    mpl.rcParams.update(
        {
            "font.family": family,
            "font.size": 8.3,
            "axes.titlesize": 10.2,
            "axes.labelsize": 8.8,
            "xtick.labelsize": 7.6,
            "ytick.labelsize": 7.6,
            "legend.fontsize": 7.0,
            "text.color": INK,
            "axes.labelcolor": INK,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "axes.edgecolor": "#79868F",
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            # Convert SVG labels to paths so the standalone vector export does
            # not depend on a reader having this TTC font installed.
            "svg.fonttype": "path",
        }
    )


def load_support_layer(manifest_path: Path) -> SupportLayer:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    accumulator: dict[tuple[Any, ...], list[float]] = defaultdict(
        lambda: [0.0, 0.0]
    )
    families: dict[str, float] = {}
    nuclides: set[str] = set()
    volumes: set[str] = set()
    source_blocks = 0
    included_state_rows = 0

    for cell in manifest["source_cells"]:
        family = str(cell["family"])
        activity = float(cell["transported_ground_activity_Bq"])
        blocks_expected = int(cell["transport_blocks"])
        families[family] = activity
        included_state_rows += len(cell["included_states"])
        kept = 0
        with Path(cell["positions_path"]).open(
            newline="", encoding="utf-8"
        ) as handle:
            for row in csv.DictReader(handle):
                if int(row["sample_index"]) % int(cell["closure"]["stride"]) != 0:
                    continue
                kept += 1
                world_x = float(row["x_cm"])
                world_y = float(row["y_cm"])
                world_z = float(row["z_cm"])
                x_prime = (world_x - world_z) * BASE.SQRT_HALF
                z_prime = (world_x + world_z) * BASE.SQRT_HALF
                nuclide = za_to_nuclide(row["ZA"])
                volume = row["volume"]
                key = (
                    family,
                    nuclide,
                    volume,
                    round(float(row["excitation_keV"]), 6),
                    round(x_prime, 6),
                    round(world_y, 6),
                    round(z_prime, 6),
                )
                accumulator[key][0] += 1.0
                accumulator[key][1] += activity / blocks_expected
                nuclides.add(nuclide)
                volumes.add(volume)
        if kept != blocks_expected:
            raise RuntimeError(
                f"{manifest_path}: {family} expected {blocks_expected} stride-retained "
                f"positions, got {kept}"
            )
        source_blocks += kept

    sites = [
        SupportSite(
            family=key[0],
            nuclide=key[1],
            volume=key[2],
            x_cm=key[4],
            y_cm=key[5],
            z_cm=key[6],
            blocks=int(values[0]),
            activity_bq=values[1],
        )
        for key, values in accumulator.items()
    ]
    total_activity = math.fsum(site.activity_bq for site in sites)
    manifest_total = math.fsum(families.values())
    if not math.isclose(total_activity, manifest_total, rel_tol=0.0, abs_tol=2e-10):
        raise RuntimeError(
            f"{manifest_path}: support activity closure failed: "
            f"{total_activity} != {manifest_total}"
        )
    return SupportLayer(
        sites=sites,
        source_blocks=source_blocks,
        unique_nuclides=len(nuclides),
        unique_volumes=len(volumes),
        included_state_rows=included_state_rows,
        total_activity_bq=total_activity,
        family_activity_bq=families,
    )


def axes_style(ax: plt.Axes) -> None:
    ax.set_aspect("equal", adjustable="box")
    ax.grid(color=GRID, linewidth=0.42, alpha=0.76)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_color("#7A8790")
        spine.set_linewidth(0.65)


def shifted_segments(
    segments: Iterable[np.ndarray], shift: tuple[float, float]
) -> list[np.ndarray]:
    delta = np.asarray(shift, dtype=float)
    if np.allclose(delta, 0.0):
        return list(segments)
    return [segment + delta for segment in segments]


def draw_geometry(
    ax: plt.Axes,
    section: dict[str, list[np.ndarray]],
    *,
    shift: tuple[float, float] = (0.0, 0.0),
    detail: bool = False,
    paper_style: bool = False,
    offaxis_context: bool = False,
) -> None:
    for category in DRAW_ORDER:
        segments = section.get(category, [])
        if not segments:
            continue
        colour, alpha, width, _ = GEOMETRY_STYLE[category]
        if paper_style:
            # The geometry is contextual in the manuscript figure.  A neutral
            # line system prevents its material colours from competing with
            # the two scientifically meaningful source-point layers.
            colour = "#56636B" if category in {"bi", "w", "tes"} else "#849198"
            alpha = min(0.82, 0.28 + 0.52 * alpha)
        if offaxis_context:
            colour = "#9EA9AF"
            if category == "hole":
                alpha = 0.025
                width *= 0.18
            elif category in {"tes", "w"}:
                alpha = 0.055
                width *= 0.28
            else:
                alpha = 0.18
                width *= 0.34
        if detail:
            width *= 1.38
            alpha = min(1.0, alpha + 0.10)
        kwargs: dict[str, Any] = {}
        if category == "hole":
            kwargs["linestyles"] = "dashed"
        ax.add_collection(
            LineCollection(
                shifted_segments(segments, shift),
                colors=[mpl.colors.to_rgba(colour, alpha)],
                linewidths=width,
                capstyle="round",
                joinstyle="round",
                zorder=6,
                **kwargs,
            )
        )


def full_projection_segments(
    solids: Iterable[Any],
) -> tuple[dict[str, list[np.ndarray]], int, Counter[str], int]:
    """Project every native-WRL mesh edge onto x'-z' and deduplicate it.

    The pale wireframe is a complete orthographic geometry context.  The exact
    y'=0 section is drawn over it as the darker geometric authority, while the
    TES detail panel remains a section only.
    """

    by_category: dict[str, list[np.ndarray]] = defaultdict(list)
    seen: dict[str, set[tuple[float, ...]]] = defaultdict(set)
    projected_solids = 0
    projected_categories: Counter[str] = Counter()
    for solid in solids:
        projected_solids += 1
        projected_categories[solid.category] += 1
        points_2d = solid.points_cm[:, (0, 2)]
        for face in solid.faces:
            for index, first_index in enumerate(face):
                second_index = face[(index + 1) % len(face)]
                segment = np.asarray(
                    (points_2d[int(first_index)], points_2d[int(second_index)]),
                    dtype=float,
                )
                if float(np.linalg.norm(segment[1] - segment[0])) < 1.0e-7:
                    continue
                first = tuple(np.round(segment[0], 6))
                second = tuple(np.round(segment[1], 6))
                key = first + second if first <= second else second + first
                if key in seen[solid.category]:
                    continue
                seen[solid.category].add(key)
                by_category[solid.category].append(segment)
    return (
        dict(by_category),
        projected_solids,
        projected_categories,
        sum(len(segments) for segments in by_category.values()),
    )


def draw_support(
    ax: plt.Axes,
    support: SupportLayer,
    *,
    shift: tuple[float, float] = (0.0, 0.0),
    detail: bool = False,
) -> None:
    xs = np.fromiter((site.x_cm + shift[0] for site in support.sites), dtype=float)
    zs = np.fromiter((site.z_cm + shift[1] for site in support.sites), dtype=float)
    ax.scatter(
        xs,
        zs,
        s=0.8625 if detail else 0.5175,
        color=ALL_SOURCE_COLOUR,
        alpha=0.16,
        edgecolors="none",
        rasterized=True,
        zorder=3,
    )


def visible_nuclides(selected: Iterable[Any], limit: int = 8) -> list[str]:
    rates: dict[str, float] = defaultdict(float)
    for origin in selected:
        rates[origin.nuclide] += float(origin.rate_cps)
    return [
        nuclide
        for nuclide, _ in sorted(rates.items(), key=lambda item: item[1], reverse=True)[:limit]
    ]


def selected_marker_area(rate_cps: float, *, overview: bool = False) -> float:
    # Fixed paper-scale areas keep the geometry legible and avoid introducing
    # an unexplained quantitative size encoding in the two-entry legend.
    del rate_cps
    return 2.0 if overview else 6.0


def draw_selected(
    ax: plt.Axes,
    markers: Iterable[Any],
    visible: set[str],
    *,
    shift: tuple[float, float] = (0.0, 0.0),
    overview: bool = False,
) -> None:
    for marker in sorted(markers, key=lambda item: item.rate_cps):
        colour = BASE.NUCLIDE_COLOURS.get(marker.nuclide, OTHER_SELECTED_COLOUR)
        if marker.nuclide not in visible:
            colour = OTHER_SELECTED_COLOUR
        ax.scatter(
            [marker.x_cm + shift[0]],
            [marker.z_cm + shift[1]],
            s=selected_marker_area(marker.rate_cps, overview=overview),
            marker="o",
            facecolors=mpl.colors.to_rgba(colour, 0.82),
            edgecolors="#3A2732",
            linewidths=0.20 if overview else 0.30,
            alpha=0.96,
            zorder=14,
        )


def nuclide_math(value: str) -> str:
    match = re.fullmatch(r"([A-Za-z]+)-(\d+)", value)
    if not match:
        return value
    symbol, mass = match.groups()
    return rf"$^{{{mass}}}\mathrm{{{symbol}}}$"


def draw_group_labels(
    ax: plt.Axes,
    groups: list[Any],
    *,
    shift: tuple[float, float],
    limits: tuple[tuple[float, float], tuple[float, float]],
) -> None:
    offsets = [(8, 8), (8, -11), (-13, 8), (-13, -11), (15, 1), (-17, 1)]
    (xmin, xmax), (zmin, zmax) = limits
    shown = 0
    for group in groups:
        x = group.x_cm + shift[0]
        z = group.z_cm + shift[1]
        if not (xmin <= x <= xmax and zmin <= z <= zmax):
            continue
        dx, dz = offsets[shown % len(offsets)]
        ax.annotate(
            f"{group.group_id} {nuclide_math(group.nuclide)}",
            xy=(x, z),
            xytext=(dx, dz),
            textcoords="offset points",
            ha="center",
            va="center",
            fontsize=6.7,
            fontweight="bold",
            color=INK,
            bbox={
                "boxstyle": "round,pad=0.18",
                "facecolor": "white",
                "edgecolor": "#7E8D96",
                "linewidth": 0.45,
                "alpha": 0.90,
            },
            arrowprops={
                "arrowstyle": "-",
                "color": "#71808A",
                "linewidth": 0.50,
                "shrinkA": 1,
                "shrinkB": 2,
            },
            zorder=20,
        )
        shown += 1
        if shown == 8:
            break


def short_volume_zh(name: str) -> str:
    exact = {
        "ColdPlate_MXC_50mK_SD_anchor": "50 mK 混合室板",
        "SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm": "TES 热沉环（L0）",
        "SG3B_Bi_MXC_TES_UpperHalfCylinder_Main_4p796mm": "Bi 上半圆筒屏蔽",
        "Passive_W_Bottom_Plate_detector_bay": "探测器舱 W 底板",
        "SE3_Al_Shield_Inner_Cylinder_2mm": "内层 Al 屏蔽筒",
        "Shield_60K_Al_side_window_bottom_cap": "60 K Al 屏蔽底盖",
        "DR_MixingChamber_Cu": "稀释制冷机混合室 Cu",
        "SH3_OptV2_W_Frame_Top": "SH3 W 顶框",
        "SH3_OptV2_W_Frame_Bottom": "SH3 W 底框",
        "SH3_TES_BottomColdPlate_Spoke_YM": "TES 冷盘辐条（Y−）",
        "SH3_TES_BottomColdPlate_Spoke_YP": "TES 冷盘辐条（Y+）",
        "SH3_Layer02_SideShell": "SH3 第 2 层 Al 侧壳",
        "SH3_Layer04_SideShell": "SH3 第 4 层 Al 侧壳",
    }
    if name in exact:
        return exact[name]
    ring = re.fullmatch(r"Cu_SubstrateSupport_OpenRing_L(\d)_([YZ][PM])_panel", name)
    if ring:
        sign = ring.group(2).replace("P", "+").replace("M", "−")
        return f"L{ring.group(1)} Cu 支撑环（{sign}）"
    return BASE.short_volume(name)


def family_label(value: str) -> str:
    return {
        "alpha": r"$\alpha$",
        "eminus": r"$e^-$",
        "eplus": r"$e^+$",
        "gamma": r"$\gamma$",
        "muminus": r"$\mu^-$",
        "muplus": r"$\mu^+$",
        "n": "n",
        "p": "p",
    }.get(value, value)


def draw_sidebar(
    ax: plt.Axes,
    spec: FigureSpec,
    markers: list[Any],
    groups: list[Any],
) -> None:
    ax.axis("off")
    selected_nuclides = sorted({origin.nuclide for origin in spec.selected})
    ax.text(
        0.0,
        1.0,
        "两层数据口径",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=10.5,
        fontweight="bold",
    )
    ax.text(
        0.0,
        0.955,
        "全部输运活化源",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.2,
        fontweight="bold",
        color=ALL_SOURCE_COLOUR,
    )
    ax.text(
        0.0,
        0.918,
        f"{spec.support.source_blocks:,} 个源块（8 族 × 10,000）\n"
        f"{len(spec.support.sites):,} 个唯一族–核素–位置单元\n"
        f"{spec.support.unique_nuclides} 种母核素，{spec.support.unique_volumes} 个产生体积\n"
        f"第 15 天总基态活度：{spec.support.total_activity_bq:.6f} Bq",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=7.25,
        color=MUTED,
        linespacing=1.36,
    )
    ax.text(
        0.0,
        0.778,
        "影响 TES 的最终 W2 子集",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.2,
        fontweight="bold",
        color="#9B3B4A",
    )
    ax.text(
        0.0,
        0.741,
        f"{len(spec.selected):,} 条选后事例 → {len(markers)} 个唯一母核位置\n"
        f"{len(selected_nuclides)} 种母核素；第 15 天 W2 率：{spec.selected_rate_cps:.8f} cps",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=7.25,
        color=MUTED,
        linespacing=1.36,
    )

    ax.plot(
        [0.0, 1.0],
        [0.667, 0.667],
        transform=ax.transAxes,
        color="#C9D3D9",
        linewidth=0.7,
    )
    ax.text(
        0.0,
        0.647,
        "主要 TES 相关来源",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9.0,
        fontweight="bold",
    )
    ax.text(
        0.0,
        0.616,
        "按入射族 × 母核素 × 产生体积分组",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=6.8,
        color=MUTED,
    )

    y = 0.579
    for group in groups[:8]:
        colour = BASE.NUCLIDE_COLOURS.get(group.nuclide, OTHER_SELECTED_COLOUR)
        ax.scatter(
            [0.017],
            [y - 0.004],
            s=31,
            transform=ax.transAxes,
            color=colour,
            edgecolor="#3A2732",
            linewidth=0.45,
            clip_on=False,
        )
        ax.text(
            0.045,
            y,
            f"{group.group_id}  {nuclide_math(group.nuclide)}   {family_label(group.family)}",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=7.25,
            fontweight="bold",
        )
        ax.text(
            0.045,
            y - 0.024,
            short_volume_zh(group.volume),
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=6.65,
            color=MUTED,
        )
        ax.text(
            0.99,
            y,
            f"{group.rate_cps:.3g} cps",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=6.9,
        )
        y -= 0.066

    ax.text(
        0.0,
        0.018,
        "淡蓝点大小表示源单元的第 15 天活度；彩色圆大小表示最终 W2 率。\n"
        "两类点均为三维位置在 x′–z′ 平面的投影。",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=6.75,
        color=MUTED,
        linespacing=1.34,
    )


def material_handles(section: dict[str, list[np.ndarray]]) -> list[Line2D]:
    priority = [
        "envelope",
        "al_local",
        "cu_stage",
        "cu_link",
        "bgo",
        "bi",
        "w",
        "tes",
    ]
    handles: list[Line2D] = []
    for category in priority:
        if category not in section:
            continue
        colour, alpha, width, label = GEOMETRY_STYLE[category]
        handles.append(
            Line2D(
                [0],
                [0],
                color=mpl.colors.to_rgba(colour, alpha),
                lw=max(1.5, 2.0 * width),
                label=label,
            )
        )
    return handles


def paper_source_legend(
    visible: list[str], language: str
) -> tuple[list[Any], list[str]]:
    blue = Line2D(
        [0],
        [0],
        marker="o",
        linestyle="none",
        markersize=4.8,
        markerfacecolor=ALL_SOURCE_COLOUR,
        markeredgecolor="none",
        alpha=0.65,
    )
    selected_colours = [
        BASE.NUCLIDE_COLOURS.get(nuclide, OTHER_SELECTED_COLOUR)
        for nuclide in visible[:4]
    ]
    if not selected_colours:
        selected_colours = [OTHER_SELECTED_COLOUR]
    coloured = tuple(
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="none",
            markersize=5.3,
            markerfacecolor=colour,
            markeredgecolor="#3A2732",
            markeredgewidth=0.45,
        )
        for colour in selected_colours
    )
    if language == "zh":
        labels = [
            "蓝色：全部输运的延迟活化源位置",
            "彩色：TES 510.58–511.42 keV 响应窗本底的活化母核素",
        ]
    elif language == "en":
        labels = [
            "Blue: all transported delayed-activation source sites",
            "Colored: TES-background parent nuclides in the 510.58–511.42 keV response window",
        ]
    else:
        raise ValueError(f"Unsupported language: {language}")
    return [blue, coloured], labels


def build_figure(
    spec: FigureSpec,
    section: dict[str, list[np.ndarray]],
    projection_section: dict[str, list[np.ndarray]],
    crossing_solids: int,
    crossing_categories: Counter[str],
    projection_solids: int,
    projection_categories: Counter[str],
    projection_segments: int,
    *,
    language: str,
) -> dict[str, Any]:
    markers = BASE.aggregate_markers(spec.selected)
    visible_list = visible_nuclides(spec.selected, limit=8)
    visible = set(visible_list)

    fig = plt.figure(figsize=(8.0, 4.15), constrained_layout=False)
    grid = fig.add_gridspec(
        2,
        2,
        width_ratios=(1.0, 1.28),
        height_ratios=(1.0, 0.105),
        left=0.072,
        right=0.988,
        bottom=0.055,
        top=0.985,
        wspace=0.19,
        hspace=0.15,
    )
    ax_full = fig.add_subplot(grid[0, 0])
    ax_detail = fig.add_subplot(grid[0, 1])
    ax_legend = fig.add_subplot(grid[1, :])
    ax_legend.axis("off")

    full_limits = ((-62.0, 58.0), (-50.0, 69.0))
    draw_support(ax_full, spec.support)
    draw_geometry(
        ax_full,
        projection_section,
        paper_style=True,
        offaxis_context=True,
    )
    draw_geometry(ax_full, section, paper_style=True)
    draw_selected(ax_full, markers, visible, overview=True)
    axes_style(ax_full)
    ax_full.set_xlim(*full_limits[0])
    ax_full.set_ylim(*full_limits[1])

    tes_x, tes_z = spec.tes_center_cm
    shift = (-tes_x, -tes_z)
    detail_limits = ((-11.0, 11.0), (-7.0, 8.0))
    draw_support(ax_detail, spec.support, shift=shift, detail=True)
    draw_geometry(
        ax_detail,
        section,
        shift=shift,
        detail=True,
        paper_style=True,
    )
    draw_selected(ax_detail, markers, visible, shift=shift)
    axes_style(ax_detail)
    ax_detail.set_xlim(*detail_limits[0])
    ax_detail.set_ylim(*detail_limits[1])

    if language == "zh":
        ax_full.set_xlabel(r"仪器坐标 $x'$（cm）")
        ax_full.set_ylabel(r"仪器坐标 $z'$（cm）")
        ax_detail.set_xlabel(r"相对 TES 中心 $u=x'-x'_{\rm TES}$（cm）")
        ax_detail.set_ylabel(r"相对 TES 中心 $v=z'-z'_{\rm TES}$（cm）")
    elif language == "en":
        ax_full.set_xlabel(r"Instrument-frame $x'$ (cm)")
        ax_full.set_ylabel(r"Instrument-frame $z'$ (cm)")
        ax_detail.set_xlabel(r"$u=x'-x'_{\rm TES}$ relative to TES center (cm)")
        ax_detail.set_ylabel(r"$v=z'-z'_{\rm TES}$ relative to TES center (cm)")
    else:
        raise ValueError(f"Unsupported language: {language}")

    # Panel letters are retained as manuscript navigation, not figure titles.
    for label, ax in (("a", ax_full), ("b", ax_detail)):
        ax.text(
            -0.105,
            1.015,
            label,
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=9.0,
            fontweight="bold",
            color=INK,
            clip_on=False,
        )

    legend_handles, legend_labels = paper_source_legend(visible_list, language)
    ax_legend.legend(
        handles=legend_handles,
        labels=legend_labels,
        handler_map={tuple: HandlerTuple(ndivide=None, pad=0.15)},
        loc="center",
        bbox_to_anchor=(0.5, 0.46),
        ncol=2,
        frameon=False,
        columnspacing=1.8,
        handletextpad=0.55,
        fontsize=7.0,
    )

    stem = f"model_{spec.key}_all_activation_support_and_tes_subset_{language}"
    png_path = OUTPUTS / f"{stem}.png"
    svg_path = OUTPUTS / f"{stem}.svg"
    pdf_path = OUTPUTS / f"{stem}.pdf"
    metadata_title = (
        spec.title
        if language == "zh"
        else f"Mass model {spec.model_name}: delayed-activation source sites and TES-relevant parent nuclides"
    )
    metadata = {
        "Title": metadata_title,
        "Creator": "build_activation_support_tes_overlay.py",
    }
    fig.savefig(png_path, dpi=260, facecolor="white", metadata=metadata)
    fig.savefig(svg_path, dpi=260, facecolor="white", metadata=metadata)
    # Type-3 glyph outlines avoid TTC subsetting failures in Matplotlib 3.5
    # while keeping axes, geometry, selected markers, and text as vectors.
    previous_pdf_fonttype = mpl.rcParams["pdf.fonttype"]
    mpl.rcParams["pdf.fonttype"] = 3
    try:
        fig.savefig(pdf_path, dpi=260, facecolor="white", metadata=metadata)
    finally:
        mpl.rcParams["pdf.fonttype"] = previous_pdf_fonttype
    plt.close(fig)
    output_paths = {
        "png": str(png_path.relative_to(REPO)),
        "svg": str(svg_path.relative_to(REPO)),
        "pdf": str(pdf_path.relative_to(REPO)),
    }

    return {
        "language": language,
        "model": spec.model_name,
        "geometry": {
            "wrl": str(spec.wrl.relative_to(REPO)),
            "parsed_solids": spec.expected_solids,
            "section_crossing_solids": crossing_solids,
            "section_crossing_solids_by_category": dict(
                sorted(crossing_categories.items())
            ),
            "overview_projected_solids": projection_solids,
            "overview_projected_solids_by_category": dict(
                sorted(projection_categories.items())
            ),
            "overview_unique_projected_mesh_edges": projection_segments,
            "full_panel": "complete pale native-WRL x'-z' mesh-edge projection plus exact dark InstrumentFrame y'=0 section",
            "detail_panel": "exact InstrumentFrame y'=0 section only",
        },
        "all_transported_activation_support": {
            "manifest": str(spec.manifest),
            "source_blocks": spec.support.source_blocks,
            "unique_family_nuclide_position_sites": len(spec.support.sites),
            "unique_nuclides": spec.support.unique_nuclides,
            "unique_volumes": spec.support.unique_volumes,
            "included_family_volume_nuclide_state_rows": spec.support.included_state_rows,
            "day15_total_ground_activity_bq": spec.support.total_activity_bq,
            "day15_ground_activity_by_family_bq": spec.support.family_activity_bq,
            "meaning": "all stride-retained source blocks actually used by the delayed-source catalogue; not every raw BUILDUP RP record",
        },
        "tes_impacting_final_w2_subset": {
            "selected_events": len(spec.selected),
            "unique_mother_sites": len(markers),
            "unique_mother_nuclides": len({origin.nuclide for origin in spec.selected}),
            "day15_final_w2_rate_cps": spec.selected_rate_cps,
            "top_groups": [
                {
                    "id": group.group_id,
                    "family": group.family,
                    "nuclide": group.nuclide,
                    "volume": group.volume,
                    "rate_cps": group.rate_cps,
                }
                for group in BASE.build_groups(spec.selected, limit=10)
            ],
        },
        "outputs": output_paths,
    }


def main() -> None:
    configure_matplotlib()
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    support_a = load_support_layer(MANIFEST_A)
    support_b = load_support_layer(MANIFEST_B)
    selected_a = BASE.load_model_a_origins()
    selected_b, b_factors = BASE.load_model_b_origins()
    rate_a = math.fsum(origin.rate_cps for origin in selected_a)
    rate_b = math.fsum(origin.rate_cps for origin in selected_b)

    specs = [
        FigureSpec(
            key="a_sg3b",
            model_name="A / SG3B",
            title="质量模型 A（SG3B）：全部延迟活化源与 TES 相关本底核素",
            manifest=MANIFEST_A,
            wrl=BASE.MODEL_A_WRL,
            expected_solids=3336,
            tes_center_cm=(0.0, -5.2),
            support=support_a,
            selected=selected_a,
            selected_rate_cps=rate_a,
        ),
        FigureSpec(
            key="b_sh3_optv3",
            model_name="B / SH3 OptV3",
            title="质量模型 B（SH3 OptV3）：全部延迟活化源与 TES 相关本底核素",
            manifest=MANIFEST_B,
            wrl=BASE.MODEL_B_WRL,
            expected_solids=2696,
            tes_center_cm=(-35.55, -2.8),
            support=support_b,
            selected=selected_b,
            selected_rate_cps=rate_b,
        ),
    ]

    summaries: list[dict[str, Any]] = []
    for spec in specs:
        solids = BASE.parse_wrl(spec.wrl)
        if len(solids) != spec.expected_solids:
            raise RuntimeError(
                f"{spec.model_name}: parsed {len(solids)} solids, expected "
                f"{spec.expected_solids}"
            )
        section, crossing_solids, crossing_categories = BASE.section_segments(solids)
        (
            projection_section,
            projection_solids,
            projection_categories,
            projection_segments,
        ) = full_projection_segments(solids)
        rendered = {
            language: build_figure(
                spec,
                section,
                projection_section,
                crossing_solids,
                crossing_categories,
                projection_solids,
                projection_categories,
                projection_segments,
                language=language,
            )
            for language in ("zh", "en")
        }
        model_summary = rendered["zh"]
        model_summary.pop("language", None)
        model_summary["outputs_by_language"] = {
            language: result["outputs"] for language, result in rendered.items()
        }
        model_summary.pop("outputs", None)
        summaries.append(model_summary)

    expected = {
        "A_blocks": 80000,
        "A_sites": 20970,
        "A_activity": 1352.2974936021085,
        "A_selected_events": 394,
        "A_selected_sites": 64,
        "A_selected_rate": 0.037720860604326306,
        "B_blocks": 80000,
        "B_sites": 17388,
        "B_activity": 211.3874334766397,
        "B_selected_events": 111,
        "B_selected_sites": 42,
        "B_selected_rate": 0.0035805378117859145,
    }
    observed = {
        "A_blocks": support_a.source_blocks,
        "A_sites": len(support_a.sites),
        "A_activity": support_a.total_activity_bq,
        "A_selected_events": len(selected_a),
        "A_selected_sites": len(BASE.aggregate_markers(selected_a)),
        "A_selected_rate": rate_a,
        "B_blocks": support_b.source_blocks,
        "B_sites": len(support_b.sites),
        "B_activity": support_b.total_activity_bq,
        "B_selected_events": len(selected_b),
        "B_selected_sites": len(BASE.aggregate_markers(selected_b)),
        "B_selected_rate": rate_b,
    }
    for key, value in expected.items():
        actual = observed[key]
        if isinstance(value, float):
            if not math.isclose(float(actual), value, rel_tol=0.0, abs_tol=2e-10):
                raise RuntimeError(f"Closure failed for {key}: {actual} != {value}")
        elif actual != value:
            raise RuntimeError(f"Closure failed for {key}: {actual} != {value}")

    summary = {
        "status": "PASS__ALL_TRANSPORTED_ACTIVATION_SUPPORT_AND_TES_FINAL_W2_SUBSET",
        "figure_contract": {
            "geometry": "overview combines a complete pale native-WRL x'-z' mesh-edge projection with the exact dark InstrumentFrame y'=0 section; TES detail remains the exact y'=0 section",
            "all_source_layer": "all 80,000 stride-retained delayed-source blocks, aggregated to unique family-nuclide-position sites with multiplicity and day-15 activity preserved",
            "highlight_layer": "mother-nuclide sites of delayed events surviving current final-W2 response selection",
            "projection": "all 3-D source positions projected onto InstrumentFrame x'-z'",
            "marker_areas": "fixed manuscript sizes shared across A/B: all-source sites 0.5175 pt^2 overview and 0.8625 pt^2 detail (15% larger than the prior paper revision); selected mother sites 2.0 pt^2 overview and 6.0 pt^2 detail",
            "paper_layout": "two plot panels only; no figure title, subtitle, sidebar, point callouts, material legend, or per-nuclide legend; panel letters and axes retained",
            "geometry_style": "neutral grayscale so geometry context cannot be confused with the coloured nuclide layer",
            "bottom_legend": "two entries only: all transported delayed-activation source sites and parent nuclides whose delayed-decay events enter the 510.58-511.42 keV response window",
            "languages": ["zh", "en"],
            "no_sim_or_transport_read_or_run": True,
        },
        "model_b_reference_to_current_family_rate_factors": b_factors,
        "closure_expected": expected,
        "closure_observed": observed,
        "models": summaries,
    }
    (OUTPUTS / "figure_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
