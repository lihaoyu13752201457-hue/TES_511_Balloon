#!/usr/bin/env python3
"""Reuse the validated SE3 native-mesh section renderer for V2A/V2B markup.

The two figures produced here are proposal overlays on the frozen SE3 geometry.
They do not alter a geometry file and are not transport, navigation, or physics
authority.  Red/amber outlines mark current SE3 solids selected for a possible
change; green/purple graphics are explicitly non-dimensional design concepts.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/codex_mpl_se3_v2a_markup")

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_ROOT = Path(
    "/home/ubuntu/.codex/worktrees/626c/TES_511_Balloon/engineering/"
    "geometry_optimization_20260815/44_geoopt_se3_minimal_20260815"
)
DEFAULT_LINEAGE = (
    PACKAGE_ROOT.parent
    / "48_se3_background_optimization_review_20260816"
    / "data"
    / "report_delayed_volume.csv"
)
DEFAULT_OUTPUT_DIR = PACKAGE_ROOT / "figures"
DEFAULT_AUDIT = PACKAGE_ROOT / "audit" / "se3_v2a_section_markup_validation.json"

BOTTOM_CAP = "Cu_50mK_StillLike_Can_bottom_cap_2mm"
L0_DISK = "Cu_SubstrateSupport_SolidDisk_L0_deepest"
MXC_PLATE = "ColdPlate_MXC_50mK_SD_anchor"
TARGETS = (BOTTOM_CAP, L0_DISK, MXC_PLATE)

RED = "#c7352d"
AMBER = "#c57a00"
GREEN = "#18864b"
PURPLE = "#6d43a6"
BLUE = "#176a9a"
INK = "#17232d"
MUTED = "#52616c"
CJK_FONT = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")


class MarkupError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def record(path: Path, *, hash_file: bool = True) -> dict[str, Any]:
    resolved = path.resolve()
    result: dict[str, Any] = {"path": str(resolved), "size_bytes": resolved.stat().st_size}
    if hash_file:
        result["sha256"] = sha256(resolved)
    else:
        result["sha256"] = None
        result["hash_note"] = "Validated native mesh reused without a new digest."
    return result


def import_se3_visuals(source_root: Path):
    code_dir = source_root / "code"
    expected = (code_dir / "build_se3_visuals.py").resolve()
    if not expected.is_file():
        raise MarkupError(f"Missing SE3 visual generator: {expected}")
    sys.path.insert(0, str(code_dir))
    module = importlib.import_module("build_se3_visuals")
    if Path(module.__file__).resolve() != expected:
        raise MarkupError(f"Unexpected build_se3_visuals import: {module.__file__}")
    return module


def load_delayed_shares(path: Path) -> dict[str, float]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    shares = {
        row["source_volume"]: float(row["selected_rate_share"])
        for row in rows
        if row.get("source_volume") in TARGETS
    }
    missing = set(TARGETS) - set(shares)
    if missing:
        raise MarkupError(f"Delayed-volume summary lacks targets: {sorted(missing)}")
    return shares


def bounds_xz(se3, mesh: dict[str, np.ndarray], name: str) -> tuple[float, float, float, float]:
    solid_id = se3.solid_index(mesh, name)
    bounds = mesh["instrument_bounds_per_solid_cm"][solid_id]
    return float(bounds[0, 0]), float(bounds[0, 2]), float(bounds[1, 0]), float(bounds[1, 2])


def prefix_bounds_xz(mesh: dict[str, np.ndarray], prefix: str) -> tuple[float, float, float, float]:
    names = mesh["solid_names"].astype(str)
    selected = np.flatnonzero(np.char.startswith(names, prefix))
    if len(selected) == 0:
        raise MarkupError(f"No native-mesh solids match prefix {prefix!r}")
    bounds = mesh["instrument_bounds_per_solid_cm"][selected]
    return (
        float(bounds[:, 0, 0].min()),
        float(bounds[:, 0, 2].min()),
        float(bounds[:, 1, 0].max()),
        float(bounds[:, 1, 2].max()),
    )


def add_bounds_box(
    ax: plt.Axes,
    bounds: tuple[float, float, float, float],
    *,
    color: str,
    linewidth: float = 2.0,
    hatch: str | None = None,
    alpha: float = 0.08,
    linestyle: str = "--",
    zorder: float = 8,
) -> Rectangle:
    xmin, zmin, xmax, zmax = bounds
    patch = Rectangle(
        (xmin, zmin),
        xmax - xmin,
        zmax - zmin,
        facecolor=color if alpha > 0 else "none",
        edgecolor=color,
        linewidth=linewidth,
        linestyle=linestyle,
        hatch=hatch,
        alpha=alpha if hatch is None else 0.42,
        zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def centre(bounds: tuple[float, float, float, float]) -> tuple[float, float]:
    xmin, zmin, xmax, zmax = bounds
    return (0.5 * (xmin + xmax), 0.5 * (zmin + zmax))


def style(se3) -> None:
    se3.configure_matplotlib()
    if CJK_FONT.is_file():
        font_manager.fontManager.addfont(str(CJK_FONT))
        primary_font = font_manager.FontProperties(fname=str(CJK_FONT)).get_name()
    else:
        primary_font = "DejaVu Sans"
    mpl.rcParams.update(
        {
            "font.family": [primary_font, "DejaVu Sans"],
            "font.size": 9.3,
            "axes.titlesize": 11.5,
            "axes.labelsize": 9.8,
            "legend.fontsize": 8.2,
        }
    )


def save(fig: plt.Figure, output_dir: Path, stem: str) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for suffix in ("png", "svg", "pdf"):
        path = output_dir / f"{stem}.{suffix}"
        kwargs: dict[str, Any] = {"dpi": 320} if suffix == "png" else {}
        fig.savefig(path, bbox_inches="tight", pad_inches=0.10, **kwargs)
        outputs.append(path)
    plt.close(fig)
    return outputs


def draw_base_section(
    se3,
    ax: plt.Axes,
    mesh: dict[str, np.ndarray],
    limits: tuple[tuple[float, float], tuple[float, float]],
) -> None:
    se3.draw_exact_if_section(ax, mesh, include_holes=True, limits=limits)
    se3.axes_style(ax, "InstrumentFrame x′ [cm]", "InstrumentFrame z′ [cm]")
    ax.set_xlim(*limits[0])
    ax.set_ylim(*limits[1])


def build_global(
    se3,
    mesh: dict[str, np.ndarray],
    shares: dict[str, float],
    output_dir: Path,
) -> tuple[list[Path], dict[str, Any]]:
    style(se3)
    fig, ax = plt.subplots(figsize=(11.8, 11.6))
    fig.subplots_adjust(left=0.11, right=0.96, top=0.88, bottom=0.13)
    limits = ((-20.0, 20.0), (-11.0, 32.0))
    draw_base_section(se3, ax, mesh, limits)

    bottom = bounds_xz(se3, mesh, BOTTOM_CAP)
    l0 = bounds_xz(se3, mesh, L0_DISK)
    mxc = bounds_xz(se3, mesh, MXC_PLATE)
    tes = prefix_bounds_xz(mesh, "TP_L0_")
    add_bounds_box(ax, bottom, color=RED, linewidth=2.6, alpha=0.11)
    add_bounds_box(ax, l0, color=RED, linewidth=2.6, alpha=0.11)
    add_bounds_box(ax, mxc, color=AMBER, linewidth=2.3, alpha=0.08, linestyle="-.")
    add_bounds_box(ax, tes, color=BLUE, linewidth=1.8, alpha=0.05, linestyle=":")

    ax.axhline(-5.2, xmin=0.01, xmax=0.60, color=BLUE, lw=1.4, ls=":", zorder=7)
    ax.annotate(
        "focused 511-keV centreline  +x′",
        xy=(-4.0, -5.2),
        xytext=(-18.5, -5.2),
        arrowprops={"arrowstyle": "-|>", "lw": 1.5, "color": BLUE},
        color=BLUE,
        va="bottom",
    )

    ax.annotate(
        f"V2A-1  50 mK Cu can bottom cap\nsolid → annular; target share {shares[BOTTOM_CAP]*100:.1f}%",
        xy=centre(bottom),
        xytext=(-18.3, -8.1),
        arrowprops={"arrowstyle": "->", "lw": 1.3, "color": RED},
        color=RED,
        ha="left",
        bbox={"facecolor": "white", "edgecolor": RED, "alpha": 0.90},
    )
    ax.annotate(
        f"V2A-2  L0 solid Cu disk\n→ open ring/spokes; {shares[L0_DISK]*100:.1f}%",
        xy=centre(l0),
        xytext=(7.0, -3.8),
        arrowprops={"arrowstyle": "->", "lw": 1.3, "color": RED},
        color=RED,
        ha="left",
        bbox={"facecolor": "white", "edgecolor": RED, "alpha": 0.90},
    )
    ax.annotate(
        f"V2B follow-on  MXC aperture re-clock / stagger\nadds {shares[MXC_PLATE]*100:.1f}% target share",
        xy=centre(mxc),
        xytext=(4.0, 2.2),
        arrowprops={"arrowstyle": "->", "lw": 1.2, "color": AMBER},
        color=AMBER,
        ha="left",
        bbox={"facecolor": "white", "edgecolor": AMBER, "alpha": 0.90},
    )
    ax.annotate(
        "TES L0 pixel array\n(reference, unchanged)",
        xy=centre(tes),
        xytext=(-11.0, -2.7),
        arrowprops={"arrowstyle": "->", "lw": 1.1, "color": BLUE},
        color=BLUE,
        ha="left",
    )

    zoom = (-16.5, -10.5, 16.5, 2.0)
    add_bounds_box(ax, zoom, color="#49535c", linewidth=1.2, alpha=0.0, linestyle=":", zorder=6)
    ax.text(16.2, 1.6, "local zoom → second figure", ha="right", va="top", color=MUTED)

    v2a_share = shares[BOTTOM_CAP] + shares[L0_DISK]
    v2b_share = v2a_share + shares[MXC_PLATE]
    ax.set_title("全局剖面｜SE3 native mesh + V2A/V2B 拟修改区", loc="left", fontweight="bold")
    fig.suptitle(
        "SE3 下一轮几何优化标注图",
        x=0.11,
        y=0.965,
        ha="left",
        fontsize=16,
        fontweight="bold",
        color=INK,
    )
    fig.text(
        0.11,
        0.925,
        f"V2A 靶向当前 delayed W2 中约 {v2a_share*100:.1f}%；V2B 累计约 {v2b_share*100:.1f}%。"
        " 蓝色光轴仅作几何参照。",
        ha="left",
        color=MUTED,
    )
    fig.text(
        0.11,
        0.045,
        "CONCEPT MARKUP ONLY — frozen SE3 geometry is unchanged; no transport, overlap, navigation or physics validation.",
        color=RED,
        fontsize=9.2,
        fontweight="bold",
    )
    handles = [
        Patch(facecolor=RED, edgecolor=RED, alpha=0.30, label="V2A current Cu target"),
        Patch(facecolor=AMBER, edgecolor=AMBER, alpha=0.25, label="V2B follow-on target"),
        Line2D([0], [0], color=BLUE, lw=1.8, ls=":", label="TES / focused-axis reference"),
    ]
    ax.legend(handles=handles, loc="upper right", frameon=True)
    outputs = save(fig, output_dir, "se3_v2a_global_section_markup")
    return outputs, {
        "limits_xz_cm": limits,
        "v2a_target_share": v2a_share,
        "v2b_cumulative_target_share": v2b_share,
        "target_bounds_xz_cm": {BOTTOM_CAP: bottom, L0_DISK: l0, MXC_PLATE: mxc},
        "tes_l0_union_bounds_xz_cm": tes,
    }


def build_local(
    se3,
    mesh: dict[str, np.ndarray],
    shares: dict[str, float],
    output_dir: Path,
) -> tuple[list[Path], dict[str, Any]]:
    style(se3)
    fig, ax = plt.subplots(figsize=(15.2, 7.8))
    fig.subplots_adjust(left=0.07, right=0.98, top=0.84, bottom=0.16)
    limits = ((-16.5, 16.5), (-10.5, 2.0))
    draw_base_section(se3, ax, mesh, limits)

    bottom = bounds_xz(se3, mesh, BOTTOM_CAP)
    l0 = bounds_xz(se3, mesh, L0_DISK)
    mxc = bounds_xz(se3, mesh, MXC_PLATE)
    tes = prefix_bounds_xz(mesh, "TP_L0_")
    add_bounds_box(ax, bottom, color=RED, linewidth=2.6, hatch="////", alpha=0.0)
    add_bounds_box(ax, l0, color=RED, linewidth=2.6, hatch="////", alpha=0.0)
    add_bounds_box(ax, mxc, color=AMBER, linewidth=2.0, alpha=0.08, linestyle="-.")
    add_bounds_box(ax, tes, color=BLUE, linewidth=2.0, alpha=0.05, linestyle=":")

    ax.axhline(-5.2, color=BLUE, lw=1.35, ls=":", zorder=7)
    ax.annotate(
        "incoming focused 511 keV  +x′",
        xy=(-4.0, -5.2),
        xytext=(-15.6, -5.2),
        arrowprops={"arrowstyle": "-|>", "lw": 1.5, "color": BLUE},
        color=BLUE,
        va="bottom",
    )

    # Conceptual annular opening: the inner radius is deliberately not fixed.
    b_xmin, b_zmin, b_xmax, b_zmax = bottom
    concept_inner = 5.0
    ax.plot(
        [b_xmin, -concept_inner, np.nan, concept_inner, b_xmax],
        [b_zmax + 0.18] * 5,
        color=GREEN,
        lw=4.0,
        solid_capstyle="butt",
        zorder=10,
    )
    ax.annotate(
        "V2A-1: central Cu removal → annular cap\ninner radius TBD by thermal/structural review",
        xy=(0.0, b_zmax + 0.18),
        xytext=(-12.8, -8.55),
        arrowprops={"arrowstyle": "-[", "lw": 1.5, "color": GREEN},
        color=GREEN,
        ha="left",
        bbox={"facecolor": "white", "edgecolor": GREEN, "alpha": 0.92},
    )

    # Conceptual open-ring representation in this section; no dimensions are asserted.
    l_xmin, l_zmin, l_xmax, l_zmax = l0
    rim_height = 0.18 * (l_zmax - l_zmin)
    for z0 in (l_zmin, l_zmax - rim_height):
        ax.add_patch(
            Rectangle(
                (l_xmin - 0.10, z0),
                (l_xmax - l_xmin) + 0.20,
                rim_height,
                fill=False,
                edgecolor=GREEN,
                linewidth=3.0,
                zorder=10,
            )
        )
    ax.annotate(
        "V2A-2: solid L0 Cu projection\n→ open ring + sparse spokes",
        xy=centre(l0),
        xytext=(5.4, -6.7),
        arrowprops={"arrowstyle": "->", "lw": 1.5, "color": GREEN},
        color=GREEN,
        ha="left",
        bbox={"facecolor": "white", "edgecolor": GREEN, "alpha": 0.92},
    )

    tes_centre = centre(tes)
    ax.plot(
        [8.5, tes_centre[0]],
        [-9.75, tes_centre[1]],
        color=RED,
        lw=1.0,
        ls="--",
        alpha=0.75,
        zorder=7,
    )
    ax.plot(
        [centre(l0)[0], tes_centre[0]],
        [centre(l0)[1], tes_centre[1]],
        color=RED,
        lw=1.0,
        ls="--",
        alpha=0.75,
        zorder=7,
    )
    ax.text(-1.0, -7.95, "candidate delayed line-of-sight", color=RED, fontsize=8.3)

    # A route-only concept: it is not attached to an asserted existing solid.
    ax.plot(
        [centre(l0)[0], 8.5, 13.5],
        [centre(l0)[1], -2.1, -2.1],
        color=PURPLE,
        lw=2.2,
        ls=(0, (5, 3)),
        zorder=10,
    )
    ax.annotate(
        "V2A-3: reroute Cu thermal path\nout of TES direct solid angle (path TBD)",
        xy=(11.0, -2.1),
        xytext=(5.2, -1.25),
        arrowprops={"arrowstyle": "->", "lw": 1.3, "color": PURPLE},
        color=PURPLE,
        ha="left",
        bbox={"facecolor": "white", "edgecolor": PURPLE, "alpha": 0.92},
    )

    ax.annotate(
        f"V2B only after V2A: re-clock/stagger MXC apertures ({shares[MXC_PLATE]*100:.1f}% share)",
        xy=(8.5, centre(mxc)[1]),
        xytext=(-14.8, 1.25),
        arrowprops={"arrowstyle": "->", "lw": 1.3, "color": AMBER},
        color=AMBER,
        ha="left",
        bbox={"facecolor": "white", "edgecolor": AMBER, "alpha": 0.92},
    )
    ax.text(
        tes_centre[0] - 0.7,
        tes[3] + 0.35,
        "TES L0\nunchanged",
        color=BLUE,
        ha="center",
        fontweight="bold",
    )

    ax.set_title("局部放大剖面｜TES–50 mK/MXC 近场 V2A 概念改动", loc="left", fontweight="bold")
    fig.suptitle(
        "SE3-V2A：优先减 Cu / 移 Cu / 断直视固角",
        x=0.07,
        y=0.955,
        ha="left",
        fontsize=16,
        fontweight="bold",
        color=INK,
    )
    fig.text(
        0.07,
        0.905,
        "红色斜线为当前 SE3 Cu target；绿色/紫色为待工程定尺寸的设计意图，不是已生成实体。",
        ha="left",
        color=MUTED,
    )
    fig.text(
        0.07,
        0.055,
        "NO NEW PASSIVE HIGH-Z INSIDE VETO.  Candidate-own corrected activation/inventory and actual-position delayed closure remain mandatory.",
        color=RED,
        fontsize=9.1,
        fontweight="bold",
    )
    outputs = save(fig, output_dir, "se3_v2a_local_nearfield_section_markup")
    return outputs, {
        "limits_xz_cm": limits,
        "concept_annular_inner_radius_cm": None,
        "concept_l0_ring_dimensions": None,
        "concept_thermal_route_dimensions": None,
        "target_bounds_xz_cm": {BOTTOM_CAP: bottom, L0_DISK: l0, MXC_PLATE: mxc},
        "tes_l0_union_bounds_xz_cm": tes,
    }


def write_audit(
    path: Path,
    *,
    source_root: Path,
    mesh_path: Path,
    lineage_path: Path,
    outputs: list[Path],
    global_info: dict[str, Any],
    local_info: dict[str, Any],
) -> None:
    stems = {item.stem for item in outputs}
    checks = {
        "source_se3_visual_generator_reused": (source_root / "code" / "build_se3_visuals.py").is_file(),
        "native_mesh_input_exists": mesh_path.is_file(),
        "all_three_target_solids_resolved": len(global_info["target_bounds_xz_cm"]) == 3,
        "two_figure_stems": stems
        == {"se3_v2a_global_section_markup", "se3_v2a_local_nearfield_section_markup"},
        "png_svg_pdf_for_each": len(outputs) == 6,
        "all_outputs_nonempty": all(item.is_file() and item.stat().st_size > 1000 for item in outputs),
        "concept_dimensions_not_frozen": all(
            local_info[key] is None
            for key in (
                "concept_annular_inner_radius_cm",
                "concept_l0_ring_dimensions",
                "concept_thermal_route_dimensions",
            )
        ),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    payload = {
        "schema_version": "se3_v2a_section_markup_v1",
        "status": status,
        "authority": "CONCEPT_MARKUP_ONLY",
        "physics_status": "SE3 GEOMETRY UNCHANGED; NO TRANSPORT OR PHYSICS VALIDATION",
        "inputs": {
            "se3_visual_generator": record(source_root / "code" / "build_se3_visuals.py"),
            "se3_native_mesh": record(mesh_path, hash_file=False),
            "delayed_volume_summary": record(lineage_path),
            "markup_builder": record(Path(__file__)),
        },
        "outputs": [record(item) for item in outputs],
        "global_section": global_info,
        "local_section": local_info,
        "checks": checks,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)
    if status != "PASS":
        failed = [key for key, value in checks.items() if not value]
        raise MarkupError(f"Markup validation failed: {failed}")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    result.add_argument("--lineage", type=Path, default=DEFAULT_LINEAGE)
    result.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    result.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    return result


def main() -> int:
    args = parser().parse_args()
    source_root = args.source_root.resolve()
    mesh_path = source_root / "data" / "se3_geometry_mesh_products.npz"
    lineage_path = args.lineage.resolve()
    try:
        for path in (mesh_path, lineage_path):
            if not path.is_file():
                raise MarkupError(f"Required input is missing: {path}")
        se3 = import_se3_visuals(source_root)
        mesh = se3.load_mesh(mesh_path)
        shares = load_delayed_shares(lineage_path)
        global_outputs, global_info = build_global(se3, mesh, shares, args.output_dir.resolve())
        local_outputs, local_info = build_local(se3, mesh, shares, args.output_dir.resolve())
        outputs = global_outputs + local_outputs
        write_audit(
            args.audit.resolve(),
            source_root=source_root,
            mesh_path=mesh_path,
            lineage_path=lineage_path,
            outputs=outputs,
            global_info=global_info,
            local_info=local_info,
        )
    except (MarkupError, OSError, ValueError, KeyError, ImportError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print("PASS: wrote two SE3 proposal sections in PNG/SVG/PDF")
    print(f"audit: {args.audit.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
