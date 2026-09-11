#!/usr/bin/env python3
"""Render the audited SH3 active-BGO-small-aperture native WRL."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.collections import PolyCollection
from matplotlib.patches import Patch


SCRIPT = Path(__file__).resolve()
PACKAGE = SCRIPT.parents[1]
WRL = PACKAGE / "figures/SH3_Chimney_DR_Assembly_OptV3_BGO_SmallAp_SG3Grid.wrl"
WRL_REPORT = PACKAGE / "audit/bgo_smallap_sg3grid_wrl_export_validation.json"
OUTPUT = PACKAGE / "figures/SH3_Assembly_OptV3_BGO_SmallAp_SG3Grid_preview.png"
REPORT = PACKAGE / "audit/bgo_smallap_sg3grid_preview_validation.json"

EXPECTED_WRL_STATUS = "PASS__SH3_OPTV3_BGO_SMALLAP_SG3GRID_NATIVE_WRL_NO_TRANSPORT"
FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"

INK = "#20313F"
COLORS = {
    "grid": "#252A2E",
    "mask": "#15191C",
    "frame": "#596168",
    "tes": "#C62F36",
    "bgo": "#2EA66B",
    "window": "#348CC1",
    "copper": "#D67B2A",
    "shell": "#8BB3CD",
    "other": "#89949D",
}
ALPHA_CONTEXT = {
    "grid": 0.98,
    "mask": 0.97,
    "frame": 0.90,
    "tes": 0.95,
    "bgo": 0.075,
    "window": 0.34,
    "copper": 0.72,
    "shell": 0.08,
    "other": 0.10,
}


class PreviewError(RuntimeError):
    """Fail-closed preview error."""


@dataclass
class Solid:
    name: str
    category: str
    points: np.ndarray
    faces: list[np.ndarray]

    @property
    def center(self) -> np.ndarray:
        return np.median(self.points, axis=0)

    @property
    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        return self.points.min(axis=0), self.points.max(axis=0)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": sha256_bytes(data)}


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def world_to_instrument(points: np.ndarray) -> np.ndarray:
    """Undo the InstrumentFrame 45-degree y rotation; coordinates stay in mm."""
    local = np.empty_like(points, dtype=float)
    inv_sqrt2 = 2.0**-0.5
    local[:, 0] = (points[:, 0] - points[:, 2]) * inv_sqrt2
    local[:, 1] = points[:, 1]
    local[:, 2] = (points[:, 0] + points[:, 2]) * inv_sqrt2
    return local


def classify(name: str) -> str:
    lower = name.lower()
    if "w_multihole_collimator" in lower:
        return "grid"
    if "w_smallaperture_mask" in lower:
        return "mask"
    if "w_frame" in lower:
        return "frame"
    if lower.startswith("tp_l"):
        return "tes"
    if "bgo" in lower and "mechanicalal" not in lower:
        return "bgo"
    if "opticalwindow" in lower or "opticalfilter" in lower:
        return "window"
    if "copper" in lower or "_cu_" in lower or "coldfinger" in lower:
        return "copper"
    if any(token in lower for token in ("shell", "annulus", "jacket", "shield")):
        return "shell"
    return "other"


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
            [float(item) for item in re.findall(FLOAT, point_match.group(1))],
            dtype=float,
        )
        if values.size % 3:
            raise PreviewError(f"malformed coordinate list: {name}")
        points = world_to_instrument(values.reshape(-1, 3))
        faces: list[np.ndarray] = []
        current: list[int] = []
        for index in [int(item) for item in re.findall(r"-?\d+", index_match.group(1))]:
            if index == -1:
                if len(current) >= 3:
                    faces.append(np.asarray(current, dtype=np.int32))
                current = []
            else:
                current.append(index)
        if current:
            faces.append(np.asarray(current, dtype=np.int32))
        if faces:
            solids.append(
                Solid(name=name, category=classify(name), points=points, faces=faces)
            )
    if not solids:
        raise PreviewError(f"no solids parsed from {path}")
    return solids


def camera_basis(
    azimuth_deg: float, elevation_deg: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    azimuth = np.deg2rad(azimuth_deg)
    elevation = np.deg2rad(elevation_deg)
    depth = np.array(
        [
            np.cos(elevation) * np.cos(azimuth),
            np.cos(elevation) * np.sin(azimuth),
            np.sin(elevation),
        ]
    )
    right = np.array([-np.sin(azimuth), np.cos(azimuth), 0.0])
    up = np.cross(depth, right)
    up /= np.linalg.norm(up)
    return right, up, depth


def project(
    points: np.ndarray, basis: tuple[np.ndarray, np.ndarray, np.ndarray]
) -> np.ndarray:
    right, up, depth = basis
    return np.column_stack((points @ right, points @ up, points @ depth))


def intersects(
    solid: Solid, lower_box: np.ndarray, upper_box: np.ndarray
) -> bool:
    lower, upper = solid.bounds
    return bool(np.all(upper >= lower_box) and np.all(lower <= upper_box))


def paint(
    ax,
    solids: list[Solid],
    basis: tuple[np.ndarray, np.ndarray, np.ndarray],
    alpha: dict[str, float],
    *,
    fixed_limits: tuple[tuple[float, float], tuple[float, float]] | None = None,
) -> None:
    polygons: list[np.ndarray] = []
    facecolors: list[tuple[float, float, float, float]] = []
    edgecolors: list[tuple[float, float, float, float]] = []
    depths: list[float] = []
    light = np.array([0.35, -0.25, 0.90])
    light /= np.linalg.norm(light)
    for solid in solids:
        projected = project(solid.points, basis)
        base = np.asarray(mpl.colors.to_rgb(COLORS[solid.category]))
        for face in solid.faces:
            vertices = solid.points[face]
            normal = np.cross(vertices[1] - vertices[0], vertices[2] - vertices[0])
            norm = np.linalg.norm(normal)
            if norm:
                normal /= norm
            intensity = 0.72 + 0.28 * abs(float(normal @ light))
            polygons.append(projected[face, :2])
            facecolors.append(
                (*np.clip(base * intensity, 0.0, 1.0), alpha[solid.category])
            )
            edge_alpha = (
                0.20 if solid.category in {"grid", "mask", "frame"} else 0.0
            )
            edgecolors.append((*mpl.colors.to_rgb(INK), edge_alpha))
            depths.append(float(projected[face, 2].mean()))
    order = np.argsort(depths)
    ax.add_collection(
        PolyCollection(
            [polygons[index] for index in order],
            facecolors=[facecolors[index] for index in order],
            edgecolors=[edgecolors[index] for index in order],
            linewidths=0.12,
            rasterized=True,
        )
    )
    if fixed_limits is None:
        points = np.concatenate([solid.points for solid in solids], axis=0)
        projected = project(points, basis)[:, :2]
        lower = projected.min(axis=0)
        upper = projected.max(axis=0)
        pad = 0.055 * max(upper - lower)
        ax.set_xlim(lower[0] - pad, upper[0] + pad)
        ax.set_ylim(lower[1] - pad, upper[1] + pad)
    else:
        ax.set_xlim(*fixed_limits[0])
        ax.set_ylim(*fixed_limits[1])
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")


def scale_bar(ax, length_mm: float, label: str) -> None:
    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()
    x0 = xmin + 0.055 * (xmax - xmin)
    y0 = ymin + 0.055 * (ymax - ymin)
    ax.plot([x0, x0 + length_mm], [y0, y0], color=INK, lw=2.6, zorder=100)
    ax.text(
        x0 + length_mm / 2,
        y0 + 0.025 * (ymax - ymin),
        label,
        ha="center",
        va="bottom",
        fontsize=8.2,
        zorder=101,
    )


def configure_plot() -> None:
    font_path = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
    if font_path.is_file():
        font_manager.fontManager.addfont(str(font_path))
        family = "Noto Sans CJK JP"
    else:
        family = "DejaVu Sans"
    mpl.rcParams.update(
        {
            "font.family": family,
            "font.size": 9.0,
            "text.color": INK,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def render(solids: list[Solid]) -> None:
    configure_plot()
    grid = [solid for solid in solids if solid.category == "grid"]
    mask = [solid for solid in solids if solid.category == "mask"]
    frame = [solid for solid in solids if solid.category == "frame"]
    bgo_front = [
        solid
        for solid in solids
        if "sh3_bgo40_frontopticalannulus" in solid.name.lower()
    ]
    if len(grid) != 624 or mask or frame or len(bgo_front) != 1:
        raise PreviewError(
            "unexpected WRL component counts: "
            f"grid={len(grid)}, mask={len(mask)}, frame={len(frame)}, "
            f"bgo_front={len(bgo_front)}"
        )

    context_box_lower = np.array([-470.0, -115.0, -115.0])
    context_box_upper = np.array([-250.0, 115.0, 75.0])
    context = [
        solid
        for solid in solids
        if intersects(solid, context_box_lower, context_box_upper)
        and solid.category
        in {"grid", "mask", "frame", "tes", "bgo", "window", "copper", "shell"}
    ]

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(12.0, 6.15),
        gridspec_kw={"width_ratios": [1.08, 1.0], "wspace": 0.025},
    )
    oblique = camera_basis(18.0, 15.0)
    paint(axes[0], context, oblique, ALPHA_CONTEXT)
    scale_bar(axes[0], 50.0, "50 mm")
    axes[0].text(
        0.01,
        0.985,
        "a  SH3 光学头：主动 BGO 小口的装配位置",
        transform=axes[0].transAxes,
        ha="left",
        va="top",
        fontsize=12.0,
        fontweight="bold",
    )
    grid_center = np.median(np.asarray([solid.center for solid in grid]), axis=0)
    grid_xy = project(grid_center[None, :], oblique)[0, :2]
    axes[0].annotate(
        "中央 SG3 网格 + 外围主动 BGO",
        xy=grid_xy,
        xytext=(0.63, 0.90),
        textcoords="axes fraction",
        ha="center",
        va="center",
        fontsize=10.5,
        fontweight="bold",
        color="#15191C",
        arrowprops={"arrowstyle": "-|>", "lw": 1.3, "color": "#15191C"},
        bbox={"boxstyle": "round,pad=0.28", "fc": "white", "ec": "#B8C0C6"},
        zorder=110,
    )

    front_basis = (
        np.array([0.0, 1.0, 0.0]),
        np.array([0.0, 0.0, 1.0]),
        np.array([1.0, 0.0, 0.0]),
    )
    detail_alpha = {category: 0.0 for category in COLORS}
    detail_alpha["grid"] = 0.98
    detail_alpha["bgo"] = 0.82
    paint(
        axes[1],
        bgo_front + grid,
        front_basis,
        detail_alpha,
        fixed_limits=((-34.0, 34.0), (-34.0, 34.0)),
    )
    scale_bar(axes[1], 10.0, "10 mm")
    axes[1].text(
        0.01,
        0.985,
        "b  沿光轴正视：中央 25 × 25 通道",
        transform=axes[1].transAxes,
        ha="left",
        va="top",
        fontsize=12.0,
        fontweight="bold",
    )
    axes[1].text(
        0.98,
        0.79,
        "主动 BGO 方口 37.96 mm  ·  节距 1.55 mm  ·  W 筋宽 0.13 mm  ·  深度 7.98 mm\n"
        "旧四边 W 框已移除；Al 滤膜沿轴移 5 mm 避让填回的 BGO\n"
        "TES、其余 BGO 与冷结构保持原定义",
        transform=axes[1].transAxes,
        ha="right",
        va="top",
        fontsize=9.0,
        bbox={"boxstyle": "round,pad=0.32", "fc": "white", "ec": "#C8D0D5", "alpha": 0.94},
        zorder=120,
    )

    legend = [
        Patch(facecolor=COLORS["grid"], label="中央 25×25 W 网格"),
        Patch(facecolor=COLORS["bgo"], alpha=0.82, label="前端主动 BGO"),
        Patch(facecolor=COLORS["tes"], label="TES 阵列"),
        Patch(facecolor=COLORS["copper"], label="冷端 Cu 结构"),
        Patch(facecolor=COLORS["window"], label="光学窗 / 滤片"),
    ]
    fig.legend(
        handles=legend,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.005),
        ncol=5,
        frameon=False,
        fontsize=8.6,
        columnspacing=1.15,
        handlelength=1.25,
    )
    fig.text(
        0.5,
        0.965,
        "SH3 assembly OptV3 · active-BGO 3.796 cm small aperture",
        ha="center",
        va="top",
        fontsize=14.0,
        fontweight="bold",
        color=INK,
    )
    fig.text(
        0.5,
        0.935,
        "Native Geant4 VRML2FILE geometry · overlap-audited · no particle transport",
        ha="center",
        va="top",
        fontsize=9.2,
        color="#526675",
    )
    fig.subplots_adjust(left=0.012, right=0.992, top=0.905, bottom=0.085)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=240, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)


def main() -> int:
    if not WRL.is_file() or not WRL_REPORT.is_file():
        raise PreviewError("native small-aperture WRL or its audit report is missing")
    export = json.loads(WRL_REPORT.read_text(encoding="utf-8"))
    current = file_record(WRL)
    if export.get("status") != EXPECTED_WRL_STATUS:
        raise PreviewError("native small-aperture WRL report is not PASS")
    if export.get("output", {}).get("sha256") != current["sha256"]:
        raise PreviewError("native small-aperture WRL hash no longer matches its report")
    solids = parse_wrl(WRL)
    render(solids)
    grid_count = sum(solid.category == "grid" for solid in solids)
    mask_count = sum(solid.category == "mask" for solid in solids)
    frame_count = sum(solid.category == "frame" for solid in solids)
    bgo_front_count = sum(
        "sh3_bgo40_frontopticalannulus" in solid.name.lower() for solid in solids
    )
    report = {
        "status": (
            "PASS__SH3_OPTV3_BGO_SMALLAP_SG3GRID_PREVIEW"
            if len(solids) == 3316
            and grid_count == 624
            and mask_count == 0
            and frame_count == 0
            and bgo_front_count == 1
            else "FAIL"
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_wrl": current,
        "parsed_solid_count": len(solids),
        "grid_solid_count": grid_count,
        "solid_w_mask_count": mask_count,
        "existing_w_frame_solid_count": frame_count,
        "active_bgo_front_solid_count": bgo_front_count,
        "output": file_record(OUTPUT),
        "transport_launched": False,
    }
    atomic_json(REPORT, report)
    print(json.dumps({"status": report["status"], "output": str(OUTPUT)}, indent=2))
    return 0 if report["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
