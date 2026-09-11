#!/usr/bin/env python3
"""Build detailed Model-A/Model-B activation-origin section figures.

The geometry layer is the exact intersection of the retained native Geant4 WRL
meshes with the InstrumentFrame plane y'=0.  The activation layer contains the
final-W2 delayed-event mother positions projected onto x'-z'.  No transport or
detector simulation is performed here.
"""

from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D


HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
REPO = PACKAGE.parents[2]
OUTPUTS = PACKAGE / "outputs"

MODEL_A_WRL = PACKAGE / "inputs/model_a_sg3b_native_no_transport.wrl"
MODEL_B_WRL = (
    REPO
    / "engineering/geometry_optimization_20260815/sh3/assembly_opt_v3/figures"
    / "SH3_Chimney_DR_Assembly_OptV3.wrl"
)
MODEL_A_EVENTS = (
    REPO
    / "engineering/geometry_optimization_20260815"
    / "59_sg3b_prompt_activation_coupling_20260818/outputs/02_coupling_analysis"
    / "selected_event_lineage.csv"
)
MODEL_B_EVENTS = (
    REPO
    / "engineering/geometry_optimization_20260815"
    / "63_m05new_sg3b_signal_statistics_20260820/outputs/05_optv3_delayed_origins"
    / "optv3_delayed_selected_events.csv"
)
MODEL_B_DAY15_CUTFLOW = (
    REPO
    / "engineering/geometry_optimization_20260815"
    / "69_m05_same_state_parma511_closure_20260823/inputs/package67"
    / "03_fluxclosed_timeline_b/direct_cutflow_day15.csv"
)

FLOAT_RE = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
SQRT_HALF = 2.0**-0.5
INK = "#263746"
MUTED = "#60717E"
GRID = "#DCE4E9"


# Material classes are inferred from the retained Geant4 solid names.  The
# geometry itself (shape and position) comes directly from the WRL mesh.
MATERIAL_STYLE = {
    "envelope": ("#8DB9D8", 0.42, 0.43, "Cryostat / Al envelope"),
    "al_local": ("#4F93BF", 0.76, 0.62, "Al chimney / local shell"),
    "support": ("#778891", 0.70, 0.56, "Structural / service support"),
    "service": ("#A7ADB2", 0.52, 0.40, "Other internal service"),
    "silicon": ("#D8B941", 0.83, 0.58, "Si substrate"),
    "cu_stage": ("#C78632", 0.88, 0.68, "Cu cold stage / DR"),
    "cu_link": ("#E06F2B", 0.94, 0.78, "Cu ring / thermal link"),
    "window": ("#2E83B9", 0.90, 0.70, "Window / optical opening"),
    "bgo": ("#2B9B69", 0.92, 0.76, "BGO active shield"),
    "bpe": ("#A89B43", 0.74, 0.58, "B-polyethylene"),
    "plastic": ("#45A976", 0.80, 0.58, "Plastic scintillator"),
    "bi": ("#8B5FBF", 0.98, 0.95, "Bi local shield"),
    "w": ("#22282D", 1.00, 1.05, "W collimator / frame"),
    "tes": ("#B51F2E", 1.00, 0.92, "TES absorber pixels"),
    "hole": ("#2C66A5", 0.70, 0.42, "Cold-plate hole boundary"),
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

NUCLIDE_COLOURS = {
    "Cu-62": "#E45756",
    "Cu-64": "#F28E2B",
    "Cu-61": "#EDC948",
    "O-15": "#59A14F",
    "F-18": "#3BA7A0",
    "C-11": "#4E9FB5",
    "Po-199": "#9C6ADE",
    "W-174": "#4E79A7",
    "Re-175": "#7B5EA7",
    "Re-177": "#8F63A9",
    "Al-25": "#76B7B2",
    "Cr-49": "#A06A42",
    "Fe-52": "#9C755F",
    "Sc-43": "#AF7AA1",
    "Mg-23": "#86BCB6",
    "Mg-27": "#5F9E6E",
    "Co-55": "#D37295",
}
OTHER_COLOUR = "#7D8991"

ELEMENT_SYMBOLS = [
    "n",
    "H",
    "He",
    "Li",
    "Be",
    "B",
    "C",
    "N",
    "O",
    "F",
    "Ne",
    "Na",
    "Mg",
    "Al",
    "Si",
    "P",
    "S",
    "Cl",
    "Ar",
    "K",
    "Ca",
    "Sc",
    "Ti",
    "V",
    "Cr",
    "Mn",
    "Fe",
    "Co",
    "Ni",
    "Cu",
    "Zn",
    "Ga",
    "Ge",
    "As",
    "Se",
    "Br",
    "Kr",
    "Rb",
    "Sr",
    "Y",
    "Zr",
    "Nb",
    "Mo",
    "Tc",
    "Ru",
    "Rh",
    "Pd",
    "Ag",
    "Cd",
    "In",
    "Sn",
    "Sb",
    "Te",
    "I",
    "Xe",
    "Cs",
    "Ba",
    "La",
    "Ce",
    "Pr",
    "Nd",
    "Pm",
    "Sm",
    "Eu",
    "Gd",
    "Tb",
    "Dy",
    "Ho",
    "Er",
    "Tm",
    "Yb",
    "Lu",
    "Hf",
    "Ta",
    "W",
    "Re",
    "Os",
    "Ir",
    "Pt",
    "Au",
    "Hg",
    "Tl",
    "Pb",
    "Bi",
    "Po",
]


@dataclass
class Solid:
    name: str
    category: str
    points_cm: np.ndarray
    faces: list[np.ndarray]


@dataclass
class Origin:
    family: str
    nuclide: str
    volume: str
    x_cm: float
    y_cm: float
    z_cm: float
    rate_cps: float


@dataclass
class OriginMarker:
    nuclide: str
    volume: str
    x_cm: float
    y_abs_cm: float
    z_cm: float
    rate_cps: float


@dataclass
class Group:
    group_id: str
    family: str
    nuclide: str
    volume: str
    rate_cps: float
    x_cm: float
    z_cm: float


@dataclass
class ModelSpec:
    key: str
    title: str
    short: str
    wrl: Path
    expected_solids: int
    tes_center_cm: tuple[float, float]
    origins: list[Origin]


def configure_matplotlib() -> None:
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "axes.titlesize": 10.2,
            "axes.labelsize": 8.8,
            "xtick.labelsize": 7.7,
            "ytick.labelsize": 7.7,
            "legend.fontsize": 7.4,
            "text.color": INK,
            "axes.labelcolor": INK,
            "axes.edgecolor": "#77858E",
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )


def world_mm_to_instrument_cm(points: np.ndarray) -> np.ndarray:
    out = np.empty_like(points, dtype=float)
    out[:, 0] = (points[:, 0] - points[:, 2]) * SQRT_HALF / 10.0
    out[:, 1] = points[:, 1] / 10.0
    out[:, 2] = (points[:, 0] + points[:, 2]) * SQRT_HALF / 10.0
    return out


def classify_solid(name: str) -> str:
    n = name.lower()
    if n.startswith("se3_hole_"):
        return "hole"
    if n.startswith("tp_l") or "tes_pixel" in n:
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
    if "bgo" in n and "mechanicalal" not in n and "outer_al" not in n and "kapton" not in n:
        return "bgo"
    if "bpe" in n:
        return "bpe"
    if "plastic" in n:
        return "plastic"
    if (
        n.startswith("win_")
        or "beryllium" in n
        or "opticalwindow" in n
        or "optical_window" in n
    ):
        return "window"
    if "si_substrate" in n or "silicon" in n:
        return "silicon"
    if any(
        key in n
        for key in (
            "substratesupport",
            "coldfinger",
            "cold_finger",
            "heat_sink",
            "heatsink",
            "thermal_link",
            "thermal_finger",
            "bottomcoldplate_spoke",
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
        or "bottomcoldplate_centralhub" in n
    ):
        return "cu_stage"
    if n.startswith("sh3_layer"):
        return "al_local"
    if n.startswith("sh3_drbase_"):
        return "envelope"
    if (
        n.startswith("nf2_outersupport")
        or "supportrod" in n
        or "hardpoint" in n
        or "_ss_" in n
        or "heater_ss" in n
        or "pumpline_ss" in n
    ):
        return "support"
    if any(
        key in n
        for key in (
            "se3_al_shield_inner",
            "sg3a_al_50mk_stilllike",
            "sh3_outer_al_",
        )
    ):
        return "al_local"
    if any(
        key in n
        for key in (
            "shield",
            "shell",
            "jacket",
            "coldplate",
            "plate_",
            "_can_",
            "_can.",
            "outer_al",
            "bottomcap",
            "annulus",
        )
    ):
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
        values = np.asarray(
            [float(item) for item in re.findall(FLOAT_RE, point_match.group(1))],
            dtype=float,
        )
        if values.size % 3:
            raise RuntimeError(f"Malformed coordinate list in {path}: {name}")
        points = world_mm_to_instrument_cm(values.reshape(-1, 3))
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
        if len(current) >= 3:
            faces.append(np.asarray(current, dtype=np.int32))
        if faces:
            solids.append(Solid(name, classify_solid(name), points, faces))
    if not solids:
        raise RuntimeError(f"No solids parsed from {path}")
    return solids


def polygon_plane_segments(
    polygon: np.ndarray, axis: int = 1, value: float = 0.0
) -> list[np.ndarray]:
    epsilon = 1.0e-8
    distances = polygon[:, axis] - value
    if np.all(np.abs(distances) <= epsilon):
        return [
            np.asarray((polygon[i], polygon[(i + 1) % len(polygon)]), dtype=float)
            for i in range(len(polygon))
        ]

    points: list[np.ndarray] = []
    for i in range(len(polygon)):
        j = (i + 1) % len(polygon)
        start, stop = polygon[i], polygon[j]
        d_start, d_stop = distances[i], distances[j]
        if abs(d_start) <= epsilon:
            points.append(start)
        if d_start * d_stop < 0.0:
            fraction = -d_start / (d_stop - d_start)
            points.append(start + fraction * (stop - start))

    unique: list[np.ndarray] = []
    for point in points:
        if not any(np.linalg.norm(point - prior) < 1.0e-7 for prior in unique):
            unique.append(point)
    if len(unique) < 2:
        return []
    if len(unique) > 2:
        start, stop = max(
            ((a, b) for a in unique for b in unique),
            key=lambda pair: float(np.linalg.norm(pair[0] - pair[1])),
        )
        return [np.asarray((start, stop), dtype=float)]
    return [np.asarray((unique[0], unique[1]), dtype=float)]


def section_segments(
    solids: Iterable[Solid],
) -> tuple[dict[str, list[np.ndarray]], int, Counter[str]]:
    by_category: dict[str, list[np.ndarray]] = defaultdict(list)
    seen: dict[str, set[tuple[float, ...]]] = defaultdict(set)
    crossing_solids = 0
    crossing_categories: Counter[str] = Counter()
    for solid in solids:
        y_min = float(solid.points_cm[:, 1].min())
        y_max = float(solid.points_cm[:, 1].max())
        if y_min > 1.0e-8 or y_max < -1.0e-8:
            continue
        crossing_solids += 1
        crossing_categories[solid.category] += 1
        for face in solid.faces:
            for segment_3d in polygon_plane_segments(solid.points_cm[face]):
                segment = segment_3d[:, (0, 2)]
                if float(np.linalg.norm(segment[1] - segment[0])) < 1.0e-7:
                    continue
                first = tuple(np.round(segment[0], 6))
                second = tuple(np.round(segment[1], 6))
                key = first + second if first <= second else second + first
                if key in seen[solid.category]:
                    continue
                seen[solid.category].add(key)
                by_category[solid.category].append(segment)
    return dict(by_category), crossing_solids, crossing_categories


def za_to_nuclide(value: str) -> str:
    za = int(float(value))
    z, a = divmod(za, 1000)
    if not 0 < z < len(ELEMENT_SYMBOLS):
        raise ValueError(f"Unsupported ZA code: {value}")
    return f"{ELEMENT_SYMBOLS[z]}-{a}"


def load_model_a_origins() -> list[Origin]:
    origins: list[Origin] = []
    with MODEL_A_EVENTS.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["stream"] != "delayed":
                continue
            origins.append(
                Origin(
                    family=row["family"],
                    nuclide=row["source_nuclide"],
                    volume=row["source_volume"],
                    x_cm=float(row["source_xprime_cm"]),
                    y_cm=float(row["source_yprime_cm"]),
                    z_cm=float(row["source_zprime_cm"]),
                    rate_cps=float(row["day15_noacc_cps"]),
                )
            )
    if len(origins) != 394:
        raise RuntimeError(f"Model A expected 394 delayed origins; got {len(origins)}")
    return origins


def target_model_b_family_rates() -> dict[str, float]:
    selected: dict[str, float] = {}
    with MODEL_B_DAY15_CUTFLOW.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if (
                row["stream"] == "delayed"
                and row["component"] == "other"
                and row["window_id"] == "w2_510p58_511p42"
                and row["stage"] == "compton_trajectory_veto"
            ):
                selected[row["family"]] = float(row["sumw_cps"])
    if not selected:
        raise RuntimeError("No Model B final-W2 day-15 cutflow rows found")
    return selected


def load_model_b_origins() -> tuple[list[Origin], dict[str, float]]:
    raw_rows: list[dict[str, str]] = []
    raw_family_rates: dict[str, float] = defaultdict(float)
    with MODEL_B_EVENTS.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            raw_rows.append(row)
            raw_family_rates[row["family"]] += float(row["day15_event_weight_cps"])
    if len(raw_rows) != 111:
        raise RuntimeError(f"Model B expected 111 delayed origins; got {len(raw_rows)}")

    target_rates = target_model_b_family_rates()
    factors = {
        family: target_rates.get(family, 0.0) / raw_rate
        for family, raw_rate in raw_family_rates.items()
    }
    origins: list[Origin] = []
    for row in raw_rows:
        world_x = float(row["x_cm"])
        world_y = float(row["y_cm"])
        world_z = float(row["z_cm"])
        family = row["family"]
        origins.append(
            Origin(
                family=family,
                nuclide=za_to_nuclide(row["source_parent_ZA"]),
                volume=row["source_volume"],
                x_cm=(world_x - world_z) * SQRT_HALF,
                y_cm=world_y,
                z_cm=(world_x + world_z) * SQRT_HALF,
                rate_cps=float(row["day15_event_weight_cps"]) * factors[family],
            )
        )
    return origins, factors


def aggregate_markers(origins: Iterable[Origin]) -> list[OriginMarker]:
    accum: dict[tuple[str, str, float, float, float], list[float]] = defaultdict(
        lambda: [0.0, 0.0]
    )
    for origin in origins:
        key = (
            origin.nuclide,
            origin.volume,
            round(origin.x_cm, 6),
            round(origin.y_cm, 6),
            round(origin.z_cm, 6),
        )
        accum[key][0] += origin.rate_cps
        accum[key][1] += abs(origin.y_cm) * origin.rate_cps
    markers: list[OriginMarker] = []
    for (nuclide, volume, x_cm, _y_cm, z_cm), (rate, weighted_y) in accum.items():
        markers.append(
            OriginMarker(
                nuclide=nuclide,
                volume=volume,
                x_cm=x_cm,
                y_abs_cm=weighted_y / rate,
                z_cm=z_cm,
                rate_cps=rate,
            )
        )
    return markers


def build_groups(origins: Iterable[Origin], limit: int = 10) -> list[Group]:
    accum: dict[tuple[str, str, str], list[float]] = defaultdict(
        lambda: [0.0, 0.0, 0.0]
    )
    for origin in origins:
        key = (origin.family, origin.nuclide, origin.volume)
        accum[key][0] += origin.rate_cps
        accum[key][1] += origin.rate_cps * origin.x_cm
        accum[key][2] += origin.rate_cps * origin.z_cm
    ranked = sorted(accum.items(), key=lambda item: item[1][0], reverse=True)[:limit]
    return [
        Group(
            group_id=f"G{index:02d}",
            family=key[0],
            nuclide=key[1],
            volume=key[2],
            rate_cps=values[0],
            x_cm=values[1] / values[0],
            z_cm=values[2] / values[0],
        )
        for index, (key, values) in enumerate(ranked, start=1)
    ]


def human_family(value: str) -> str:
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


def short_volume(name: str) -> str:
    replacements = {
        "Cu_SubstrateSupport_OpenRing_": "Cu support ring ",
        "SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm": "TES heat-sink ring (L0)",
        "ColdPlate_MXC_50mK_SD_anchor": "50 mK mixing-chamber plate",
        "DR_MixingChamber_Cu": "dilution refrigerator mixing chamber",
        "DR_MXC_Sinter_HEX_AgProxy": "mixing-chamber Ag sinter",
        "SE3_Al_Shield_Inner_Cylinder_2mm": "inner Al shield cylinder",
        "Passive_W_Bottom_Plate_detector_bay": "W detector-bay bottom plate",
        "SG3B_Bi_MXC_TES_UpperHalfCylinder_Main_4p796mm": "Bi upper half-cylinder",
        "SH3_OptV2_W_Frame_Top": "SH3 upper W frame",
        "SH3_OptV2_W_Frame_Bottom": "SH3 lower W frame",
        "SH3_TES_BottomColdPlate_Spoke_YM": "TES cold-plate spoke (Y-)",
        "SH3_TES_BottomColdPlate_Spoke_YP": "TES cold-plate spoke (Y+)",
    }
    if name in replacements:
        return replacements[name]
    out = name
    out = re.sub(r"_panel$", "", out)
    out = re.sub(r"_side_window_", " ", out)
    out = re.sub(r"_bottom_cap(?:_\w+)?$", " bottom cap", out)
    out = out.replace("SH3_Layer", "SH3 chimney layer ")
    out = out.replace("Shield_", " shield ")
    out = out.replace("Plate_", "plate ")
    out = out.replace("_", " ")
    out = re.sub(r"\s+", " ", out).strip()
    return out


def axes_style(ax: plt.Axes) -> None:
    ax.set_aspect("equal", adjustable="box")
    ax.grid(color=GRID, linewidth=0.45, alpha=0.78)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_color("#7B8992")
        spine.set_linewidth(0.65)


def shifted_segments(
    segments: list[np.ndarray], shift: tuple[float, float]
) -> list[np.ndarray]:
    if shift == (0.0, 0.0):
        return segments
    delta = np.asarray(shift, dtype=float)
    return [segment + delta for segment in segments]


def draw_geometry(
    ax: plt.Axes,
    section: dict[str, list[np.ndarray]],
    *,
    shift: tuple[float, float] = (0.0, 0.0),
    detail: bool = False,
) -> None:
    for category in DRAW_ORDER:
        segments = section.get(category, [])
        if not segments:
            continue
        colour, alpha, width, _label = MATERIAL_STYLE[category]
        if detail:
            width *= 1.42
            alpha = min(1.0, alpha + 0.12)
        kwargs = {}
        if category == "hole":
            kwargs["linestyles"] = "dashed"
        ax.add_collection(
            LineCollection(
                shifted_segments(segments, shift),
                colors=[mpl.colors.to_rgba(colour, alpha)],
                linewidths=width,
                capstyle="round",
                joinstyle="round",
                **kwargs,
            )
        )


def marker_area(rate_cps: float) -> float:
    # Shared absolute scale for both models.  The upper anchor is the largest
    # aggregated Model-A point, so Model-B points remain comparable rather than
    # being independently renormalised.
    return 16.0 + 235.0 * math.sqrt(max(rate_cps, 0.0) / 0.0071)


def visible_nuclides(origins: Iterable[Origin], limit: int = 8) -> list[str]:
    rates: dict[str, float] = defaultdict(float)
    for origin in origins:
        rates[origin.nuclide] += origin.rate_cps
    return [name for name, _rate in sorted(rates.items(), key=lambda item: item[1], reverse=True)[:limit]]


def draw_origins(
    ax: plt.Axes,
    markers: Iterable[OriginMarker],
    visible: set[str],
    *,
    shift: tuple[float, float] = (0.0, 0.0),
) -> None:
    # Plot low-rate points first so high-rate origins remain legible.
    for marker in sorted(markers, key=lambda item: item.rate_cps):
        colour = NUCLIDE_COLOURS.get(marker.nuclide, OTHER_COLOUR)
        if marker.nuclide not in visible:
            colour = OTHER_COLOUR
        x = marker.x_cm + shift[0]
        z = marker.z_cm + shift[1]
        # A hollow centre flags positions more than 1 cm away from the exact
        # section plane.  All positions are still explicitly described as 2-D
        # projections in the title and caption.
        far_from_plane = marker.y_abs_cm > 1.0
        face = "none" if far_from_plane else mpl.colors.to_rgba(colour, 0.82)
        ax.scatter(
            [x],
            [z],
            s=marker_area(marker.rate_cps),
            marker="o",
            facecolors=face,
            edgecolors=colour if far_from_plane else "#29333A",
            linewidths=1.05 if far_from_plane else 0.52,
            alpha=0.94,
            zorder=20,
        )


def draw_group_labels(
    ax: plt.Axes,
    groups: list[Group],
    *,
    shift: tuple[float, float],
    limits: tuple[tuple[float, float], tuple[float, float]],
) -> None:
    offsets = [(7, 7), (7, -10), (-12, 7), (-12, -10), (13, 2), (-16, 2)]
    (xmin, xmax), (zmin, zmax) = limits
    drawn = 0
    for group in groups:
        x = group.x_cm + shift[0]
        z = group.z_cm + shift[1]
        if not (xmin <= x <= xmax and zmin <= z <= zmax):
            continue
        dx, dz = offsets[drawn % len(offsets)]
        ax.annotate(
            group.group_id,
            xy=(x, z),
            xytext=(dx, dz),
            textcoords="offset points",
            ha="center",
            va="center",
            fontsize=6.7,
            fontweight="bold",
            color=INK,
            bbox={
                "boxstyle": "round,pad=0.17",
                "facecolor": "white",
                "edgecolor": "#83919A",
                "linewidth": 0.45,
                "alpha": 0.88,
            },
            arrowprops={
                "arrowstyle": "-",
                "color": "#71808A",
                "linewidth": 0.5,
                "shrinkA": 1,
                "shrinkB": 2,
            },
            zorder=30,
        )
        drawn += 1
        if drawn == 7:
            break


def material_legend_handles(section: dict[str, list[np.ndarray]]) -> list[Line2D]:
    handles: list[Line2D] = []
    for category in DRAW_ORDER:
        if category not in section:
            continue
        colour, alpha, width, label = MATERIAL_STYLE[category]
        handles.append(
            Line2D(
                [0],
                [0],
                color=mpl.colors.to_rgba(colour, alpha),
                lw=max(1.4, width * 2.0),
                linestyle="--" if category == "hole" else "-",
                label=label,
            )
        )
    return handles


def origin_legend_handles(visible: list[str]) -> list[Line2D]:
    handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="none",
            markersize=6.3,
            markerfacecolor=NUCLIDE_COLOURS.get(nuclide, OTHER_COLOUR),
            markeredgecolor="#29333A",
            markeredgewidth=0.55,
            label=nuclide,
        )
        for nuclide in visible
    ]
    handles.append(
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="none",
            markersize=6.3,
            markerfacecolor=OTHER_COLOUR,
            markeredgecolor="#29333A",
            markeredgewidth=0.55,
            label="Other nuclides",
        )
    )
    return handles


def draw_sidebar(
    ax: plt.Axes,
    spec: ModelSpec,
    groups: list[Group],
    visible: list[str],
    total_rate: float,
) -> None:
    ax.axis("off")
    ax.text(
        0.0,
        1.0,
        "Selected delayed-source groups",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=10.4,
        fontweight="bold",
        color=INK,
    )
    ax.text(
        0.0,
        0.966,
        "Ranked as incident family × mother nuclide × production volume",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=7.1,
        color=MUTED,
    )

    y = 0.925
    for group in groups:
        colour = NUCLIDE_COLOURS.get(group.nuclide, OTHER_COLOUR)
        ax.scatter(
            [0.018],
            [y - 0.005],
            s=34,
            transform=ax.transAxes,
            color=colour,
            edgecolor="#29333A",
            linewidth=0.45,
            clip_on=False,
        )
        ax.text(
            0.045,
            y,
            f"{group.group_id}  {group.nuclide}   {human_family(group.family)}",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=7.5,
            fontweight="bold",
            color=INK,
        )
        ax.text(
            0.045,
            y - 0.024,
            short_volume(group.volume),
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=6.75,
            color=MUTED,
            wrap=True,
        )
        ax.text(
            0.99,
            y,
            f"{group.rate_cps:.3g} cps",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=7.1,
            color=INK,
        )
        y -= 0.076

    ax.plot(
        [0.0, 1.0],
        [0.148, 0.148],
        transform=ax.transAxes,
        color="#CBD4DA",
        linewidth=0.7,
    )
    ax.text(
        0.0,
        0.128,
        "Point encoding",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.2,
        fontweight="bold",
    )
    ax.text(
        0.0,
        0.096,
        "Area follows one shared √(day-15 final-W2 rate) mapping, with a fixed visibility floor.\n"
        "Filled: |y′| ≤ 1 cm; hollow: |y′| > 1 cm. Both are x′–z′ projections.",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=6.8,
        color=MUTED,
        linespacing=1.34,
    )
    ax.text(
        0.0,
        0.010,
        f"All {len(spec.origins)} selected events: {total_rate:.8f} cps",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=7.4,
        fontweight="bold",
        color=INK,
    )


def build_figure(
    spec: ModelSpec,
    section: dict[str, list[np.ndarray]],
    crossing_solids: int,
    crossing_categories: Counter[str],
) -> dict[str, object]:
    origins = spec.origins
    markers = aggregate_markers(origins)
    groups = build_groups(origins, limit=10)
    visible_list = visible_nuclides(origins, limit=8)
    visible = set(visible_list)
    total_rate = sum(origin.rate_cps for origin in origins)
    off_plane_rate = sum(origin.rate_cps for origin in origins if abs(origin.y_cm) > 1.0)

    figure = plt.figure(figsize=(18.2, 9.8), constrained_layout=False)
    grid = figure.add_gridspec(
        nrows=2,
        ncols=3,
        width_ratios=(1.04, 1.18, 0.82),
        height_ratios=(1.0, 0.19),
        left=0.045,
        right=0.985,
        bottom=0.07,
        top=0.875,
        wspace=0.22,
        hspace=0.20,
    )
    ax_full = figure.add_subplot(grid[0, 0])
    ax_detail = figure.add_subplot(grid[0, 1])
    ax_side = figure.add_subplot(grid[0, 2])
    ax_legend = figure.add_subplot(grid[1, :])
    ax_legend.axis("off")

    figure.suptitle(
        spec.title,
        x=0.045,
        y=0.962,
        ha="left",
        va="top",
        fontsize=17.0,
        fontweight="bold",
        color=INK,
    )
    figure.text(
        0.045,
        0.918,
        "Exact native-mesh y′=0 section with projected mother-nuclide positions of final-W2 delayed events",
        ha="left",
        va="top",
        fontsize=10.0,
        color=MUTED,
    )

    full_limits = ((-62.0, 58.0), (-50.0, 69.0))
    draw_geometry(ax_full, section)
    draw_origins(ax_full, markers, visible)
    axes_style(ax_full)
    ax_full.set_xlim(*full_limits[0])
    ax_full.set_ylim(*full_limits[1])
    ax_full.set_xlabel(r"InstrumentFrame $x'$ (cm)")
    ax_full.set_ylabel(r"InstrumentFrame $z'$ (cm)")
    ax_full.set_title("a   Full instrument section", loc="left", fontweight="bold")

    tes_x, tes_z = spec.tes_center_cm
    shift = (-tes_x, -tes_z)
    detail_limits = ((-11.0, 11.0), (-7.0, 8.0))
    draw_geometry(ax_detail, section, shift=shift, detail=True)
    draw_origins(ax_detail, markers, visible, shift=shift)
    draw_group_labels(ax_detail, groups, shift=shift, limits=detail_limits)
    axes_style(ax_detail)
    ax_detail.set_xlim(*detail_limits[0])
    ax_detail.set_ylim(*detail_limits[1])
    ax_detail.set_xlabel(r"TES-centred $u=x'-x'_{\rm TES}$ (cm)")
    ax_detail.set_ylabel(r"TES-centred $v=z'-z'_{\rm TES}$ (cm)")
    ax_detail.set_title("b   Internal structure around the TES assembly", loc="left", fontweight="bold")
    ax_detail.text(
        0.985,
        0.018,
        f"TES centre in InstrumentFrame: ({tes_x:.2f}, {tes_z:.2f}) cm",
        transform=ax_detail.transAxes,
        ha="right",
        va="bottom",
        fontsize=6.9,
        color=MUTED,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.72, "pad": 1.5},
    )

    draw_sidebar(ax_side, spec, groups, visible_list, total_rate)

    geometry_handles = material_legend_handles(section)
    nuclide_handles = origin_legend_handles(visible_list)
    legend1 = ax_legend.legend(
        handles=geometry_handles,
        loc="upper left",
        bbox_to_anchor=(0.0, 1.02),
        ncol=7,
        frameon=False,
        title="Geometry line colours (classification inferred from retained solid names)",
        title_fontsize=7.8,
        handlelength=2.5,
        columnspacing=1.35,
    )
    ax_legend.add_artist(legend1)
    ax_legend.legend(
        handles=nuclide_handles,
        loc="lower left",
        bbox_to_anchor=(0.0, -0.03),
        ncol=9,
        frameon=False,
        title="Mother-nuclide point colours",
        title_fontsize=7.8,
        columnspacing=1.35,
        handletextpad=0.45,
    )

    stem = f"model_{spec.key}_detailed_activation_section"
    output_paths: dict[str, str] = {}
    for suffix in ("png", "svg", "pdf"):
        path = OUTPUTS / f"{stem}.{suffix}"
        save_kwargs: dict[str, object] = {
            "facecolor": "white",
            "metadata": {
                "Title": spec.title,
                "Creator": "build_ab_detailed_activation_sections.py",
            },
        }
        if suffix == "png":
            save_kwargs["dpi"] = 260
        figure.savefig(path, **save_kwargs)
        output_paths[suffix] = str(path.relative_to(REPO))
    plt.close(figure)

    return {
        "model": spec.short,
        "title": spec.title,
        "geometry": {
            "wrl": str(spec.wrl.relative_to(REPO)),
            "parsed_solids": spec.expected_solids,
            "section_crossing_solids": crossing_solids,
            "section_crossing_solids_by_category": dict(sorted(crossing_categories.items())),
            "section_segments_by_category": {
                key: len(value) for key, value in sorted(section.items())
            },
            "plane": "InstrumentFrame y'=0",
        },
        "activation_origins": {
            "selected_events": len(origins),
            "aggregated_markers": len(markers),
            "day15_final_w2_rate_cps": total_rate,
            "rate_fraction_with_abs_yprime_gt_1cm": off_plane_rate / total_rate,
            "projection": "all 3-D origins projected onto InstrumentFrame x'-z'",
            "top_groups": [
                {
                    "id": group.group_id,
                    "family": group.family,
                    "nuclide": group.nuclide,
                    "volume": group.volume,
                    "day15_final_w2_rate_cps": group.rate_cps,
                    "weighted_centroid_xprime_cm": group.x_cm,
                    "weighted_centroid_zprime_cm": group.z_cm,
                }
                for group in groups
            ],
        },
        "tes_center_instrument_cm": [spec.tes_center_cm[0], spec.tes_center_cm[1]],
        "outputs": output_paths,
    }


def main() -> None:
    configure_matplotlib()
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    origins_a = load_model_a_origins()
    origins_b, b_family_factors = load_model_b_origins()
    specs = [
        ModelSpec(
            key="a_sg3b",
            title="Mass model A (SG3B): detailed section and selected activation origins",
            short="A / SG3B",
            wrl=MODEL_A_WRL,
            expected_solids=3336,
            tes_center_cm=(0.0, -5.2),
            origins=origins_a,
        ),
        ModelSpec(
            key="b_sh3_optv3",
            title="Mass model B (SH3 OptV3): detailed section and selected activation origins",
            short="B / SH3 OptV3",
            wrl=MODEL_B_WRL,
            expected_solids=2696,
            tes_center_cm=(-35.55, -2.8),
            origins=origins_b,
        ),
    ]

    summaries: list[dict[str, object]] = []
    for spec in specs:
        solids = parse_wrl(spec.wrl)
        if len(solids) != spec.expected_solids:
            raise RuntimeError(
                f"{spec.short}: expected {spec.expected_solids} solids, parsed {len(solids)}"
            )
        section, crossing_solids, crossing_categories = section_segments(solids)
        if not any(section.values()):
            raise RuntimeError(f"{spec.short}: exact y'=0 section is empty")
        summaries.append(
            build_figure(spec, section, crossing_solids, crossing_categories)
        )

    expected_a = 0.037720860604326306
    expected_b = 0.0035805378117859145
    total_a = sum(item.rate_cps for item in origins_a)
    total_b = sum(item.rate_cps for item in origins_b)
    if not math.isclose(total_a, expected_a, rel_tol=0.0, abs_tol=2.0e-15):
        raise RuntimeError(f"Model A rate closure failed: {total_a} != {expected_a}")
    if not math.isclose(total_b, expected_b, rel_tol=0.0, abs_tol=2.0e-15):
        raise RuntimeError(f"Model B rate closure failed: {total_b} != {expected_b}")

    summary = {
        "status": "PASS__EXACT_NATIVE_SECTIONS_AND_CURRENT_DAY15_ORIGINS",
        "figure_contract": {
            "geometry": "exact retained native-WRL intersection with InstrumentFrame y'=0",
            "points": "final-W2 delayed mother positions projected onto x'-z'",
            "point_area": "shared monotonic square-root day-15-rate mapping with a fixed visibility floor",
            "filled_marker": "absolute y' <= 1 cm",
            "hollow_marker": "absolute y' > 1 cm",
            "no_transport_or_simulation": True,
        },
        "inputs": {
            "model_a_events": str(MODEL_A_EVENTS.relative_to(REPO)),
            "model_b_events": str(MODEL_B_EVENTS.relative_to(REPO)),
            "model_b_current_day15_cutflow": str(
                MODEL_B_DAY15_CUTFLOW.relative_to(REPO)
            ),
        },
        "model_b_reference_to_current_family_rate_factors": b_family_factors,
        "models": summaries,
    }
    summary_path = OUTPUTS / "figure_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
