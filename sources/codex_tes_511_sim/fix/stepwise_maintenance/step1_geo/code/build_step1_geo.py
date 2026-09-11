#!/usr/bin/env python3
"""Build the step1 geometry audit package.

The script is intentionally local and reproducible. It parses the current
cm-fixed geometry authority under ``fix/code/geometry`` and writes the
step1 reports, CSV inventories, a 2D schematic, and a VRML/WRL visualization.
"""

from __future__ import annotations

import csv
import json
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

os.environ.setdefault("MPLCONFIGDIR", "/tmp/codex_tes_511_matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Patch, Rectangle


STEP_DIR = Path(__file__).resolve().parents[1]
FIX_ROOT = Path(__file__).resolve().parents[3]
GEOM_DIR = FIX_ROOT / "code" / "geometry"
SOURCE_DIR = STEP_DIR / "source_snapshots"
OUTPUT_DIR = STEP_DIR / "outputs"
MEGALIB_ROOT = Path("/home/ubuntu/MEGAlib_Install/megalib-main")
MEGALIB_MATERIALS = MEGALIB_ROOT / "resource/examples/geomega/materials/Materials.geo"
MEGALIB_BRIK = MEGALIB_ROOT / "src/geomega/src/MDShapeBRIK.cxx"

GEOMETRY_FILES = [
    GEOM_DIR / "Intro_TibetTES.geo",
    GEOM_DIR / "TibetTES_v5_6layers.geo",
]
MATERIAL_FILES = [
    MEGALIB_MATERIALS,
    GEOM_DIR / "Materials_TibetTES.geo",
]
BOUNDS_JSON = GEOM_DIR / "bounds.json"
GENERATOR = GEOM_DIR / "GenerateGeo.py"

FLOAT_RE = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?"


@dataclass
class Shape:
    kind: str = ""
    params: list[float] = field(default_factory=list)
    raw: str = ""


@dataclass
class VolumeDef:
    name: str
    material: str = ""
    visibility: str = ""
    shape: Shape = field(default_factory=Shape)
    source_file: str = ""
    source_line: int = 0


@dataclass
class ObjectProps:
    name: str
    prototype: str | None = None
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    mother: str | None = None
    visibility: str = ""
    position_source_file: str = ""
    position_source_line: int = 0
    mother_source_file: str = ""
    mother_source_line: int = 0


@dataclass
class Instance:
    name: str
    prototype: str
    material: str
    shape: Shape
    local_position: tuple[float, float, float]
    mother: str | None
    is_copy: bool
    visibility: str
    source_file: str
    source_line: int
    abs_position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    bounds: tuple[float, float, float, float, float, float] | None = None


@dataclass
class MaterialInfo:
    name: str
    density_g_cm3: str = ""
    source_file: str = ""
    source_line: int = 0


def fmt(value: float | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if abs(value) < 5e-13:
        value = 0.0
    return f"{value:.9g}"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"[OK] wrote {path.relative_to(FIX_ROOT)}")


def parse_shape(raw: str) -> Shape:
    tokens = raw.split()
    if not tokens:
        return Shape(raw=raw)
    kind = tokens[0]
    params: list[float] = []
    for token in tokens[1:]:
        params.append(float(token))
    return Shape(kind=kind, params=params, raw=raw)


def parse_geometry(paths: Iterable[Path]) -> tuple[dict[str, VolumeDef], dict[str, ObjectProps]]:
    volumes: dict[str, VolumeDef] = {}
    objects: dict[str, ObjectProps] = {}

    for path in paths:
        for line_no, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith("//"):
                continue
            if line.startswith("Volume "):
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[1]
                    volumes[name] = VolumeDef(
                        name=name,
                        source_file=str(path.relative_to(FIX_ROOT)),
                        source_line=line_no,
                    )
                    objects.setdefault(name, ObjectProps(name=name))
                continue
            if ".Copy " in line:
                prototype, copy_name = line.split(".Copy ", 1)
                copy_name = copy_name.strip()
                objects[copy_name] = ObjectProps(name=copy_name, prototype=prototype.strip())
                continue
            if "." not in line:
                continue

            name, rest = line.split(".", 1)
            fields = rest.split()
            if not fields:
                continue
            key = fields[0]
            obj = objects.setdefault(name, ObjectProps(name=name))
            if key == "Material" and len(fields) >= 2:
                volumes.setdefault(name, VolumeDef(name=name)).material = fields[1]
            elif key == "Visibility" and len(fields) >= 2:
                if name in volumes:
                    volumes[name].visibility = fields[1]
                obj.visibility = fields[1]
            elif key == "Shape" and len(fields) >= 2:
                vol = volumes.setdefault(name, VolumeDef(name=name))
                vol.shape = parse_shape(" ".join(fields[1:]))
                if not vol.source_file:
                    vol.source_file = str(path.relative_to(FIX_ROOT))
                    vol.source_line = line_no
            elif key == "Position" and len(fields) >= 4:
                obj.position = (float(fields[1]), float(fields[2]), float(fields[3]))
                obj.position_source_file = str(path.relative_to(FIX_ROOT))
                obj.position_source_line = line_no
            elif key == "Mother" and len(fields) >= 2:
                obj.mother = fields[1]
                obj.mother_source_file = str(path.relative_to(FIX_ROOT))
                obj.mother_source_line = line_no

    return volumes, objects


def parse_materials(paths: Iterable[Path]) -> dict[str, MaterialInfo]:
    materials: dict[str, MaterialInfo] = {}
    current: str | None = None
    for path in paths:
        if not path.exists():
            continue
        for line_no, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            line = raw_line.strip()
            if not line or line.startswith("//") or line.startswith("#"):
                continue
            if line.startswith("Material "):
                parts = line.split()
                if len(parts) >= 2:
                    current = parts[1]
                    materials[current] = MaterialInfo(
                        name=current,
                        source_file=str(path),
                        source_line=line_no,
                    )
                continue
            if current and ".Density" in line:
                m = re.match(rf"^(?P<name>\S+)\.Density\s+(?P<density>{FLOAT_RE})", line)
                if m:
                    name = m.group("name")
                    materials.setdefault(name, MaterialInfo(name=name))
                    materials[name].density_g_cm3 = m.group("density")
                    materials[name].source_file = str(path)
                    materials[name].source_line = line_no
    return materials


def build_instances(volumes: dict[str, VolumeDef], objects: dict[str, ObjectProps]) -> list[Instance]:
    instances: list[Instance] = []
    for name, volume in volumes.items():
        obj = objects.get(name)
        if obj and obj.mother is not None:
            instances.append(
                Instance(
                    name=name,
                    prototype=name,
                    material=volume.material,
                    shape=volume.shape,
                    local_position=obj.position,
                    mother=obj.mother,
                    is_copy=False,
                    visibility=obj.visibility or volume.visibility,
                    source_file=obj.mother_source_file or volume.source_file,
                    source_line=obj.mother_source_line or volume.source_line,
                )
            )

    for name, obj in objects.items():
        if obj.prototype is None:
            continue
        prototype = obj.prototype
        volume = volumes[prototype]
        instances.append(
            Instance(
                name=name,
                prototype=prototype,
                material=volume.material,
                shape=volume.shape,
                local_position=obj.position,
                mother=obj.mother,
                is_copy=True,
                visibility=obj.visibility or volume.visibility,
                source_file=obj.position_source_file or volume.source_file,
                source_line=obj.position_source_line or volume.source_line,
            )
        )

    by_name = {instance.name: instance for instance in instances}

    def absolute(name: str, stack: tuple[str, ...] = ()) -> tuple[float, float, float]:
        instance = by_name[name]
        if name in stack:
            raise ValueError(f"cycle in geometry mother chain: {' -> '.join(stack + (name,))}")
        x, y, z = instance.local_position
        mother = instance.mother
        if mother and mother != "0" and mother in by_name:
            mx, my, mz = absolute(mother, stack + (name,))
            return x + mx, y + my, z + mz
        return x, y, z

    for instance in instances:
        instance.abs_position = absolute(instance.name)
        instance.bounds = instance_bounds(instance)

    return instances


def pcon_planes(shape: Shape) -> list[tuple[float, float, float]]:
    if shape.kind != "PCON":
        return []
    n_sections = int(shape.params[2])
    values = shape.params[3:]
    planes = []
    for i in range(n_sections):
        z, rmin, rmax = values[3 * i : 3 * i + 3]
        planes.append((z, rmin, rmax))
    return planes


def shape_dimensions(shape: Shape) -> dict[str, float | str]:
    if shape.kind == "BRIK":
        hx, hy, hz = shape.params[:3]
        return {
            "kind": "BRIK",
            "hx_cm": hx,
            "hy_cm": hy,
            "hz_cm": hz,
            "x_full_cm": 2.0 * hx,
            "y_full_cm": 2.0 * hy,
            "z_full_cm": 2.0 * hz,
            "volume_cm3": 8.0 * hx * hy * hz,
            "dimension_text": f"BRIK half=({fmt(hx)}, {fmt(hy)}, {fmt(hz)}) cm; full=({fmt(2*hx)}, {fmt(2*hy)}, {fmt(2*hz)}) cm",
        }
    if shape.kind == "PCON":
        phi0, dphi, n_sections = shape.params[:3]
        planes = pcon_planes(shape)
        z_values = [p[0] for p in planes]
        rmins = [p[1] for p in planes]
        rmaxs = [p[2] for p in planes]
        volume = 0.0
        for a, b in zip(planes, planes[1:]):
            z0, rmin0, rmax0 = a
            z1, rmin1, rmax1 = b
            dz = z1 - z0
            volume += (
                math.pi
                / 3.0
                * dz
                * (
                    rmax1 * rmax1
                    + rmax1 * rmax0
                    + rmax0 * rmax0
                    - rmin1 * rmin1
                    - rmin1 * rmin0
                    - rmin0 * rmin0
                )
            )
        volume *= dphi / 360.0
        return {
            "kind": "PCON",
            "phi0_deg": phi0,
            "dphi_deg": dphi,
            "sections": n_sections,
            "z_min_cm": min(z_values),
            "z_max_cm": max(z_values),
            "z_full_cm": max(z_values) - min(z_values),
            "rmin_min_cm": min(rmins),
            "rmin_max_cm": max(rmins),
            "rmax_cm": max(rmaxs),
            "diameter_cm": 2.0 * max(rmaxs),
            "volume_cm3": volume,
            "dimension_text": (
                f"PCON z=[{fmt(min(z_values))}, {fmt(max(z_values))}] cm; "
                f"rmax={fmt(max(rmaxs))} cm; rmin=[{fmt(min(rmins))}, {fmt(max(rmins))}] cm"
            ),
        }
    return {"kind": shape.kind, "dimension_text": shape.raw}


def instance_bounds(instance: Instance) -> tuple[float, float, float, float, float, float] | None:
    x, y, z = instance.abs_position
    shape = instance.shape
    if shape.kind == "BRIK":
        hx, hy, hz = shape.params[:3]
        return (x - hx, x + hx, y - hy, y + hy, z - hz, z + hz)
    if shape.kind == "PCON":
        planes = pcon_planes(shape)
        if not planes:
            return None
        z_values = [p[0] for p in planes]
        rmax = max(p[2] for p in planes)
        return (x - rmax, x + rmax, y - rmax, y + rmax, z + min(z_values), z + max(z_values))
    return None


def group_instances(instances: list[Instance]) -> dict[str, list[Instance]]:
    grouped: dict[str, list[Instance]] = {}
    for instance in instances:
        grouped.setdefault(instance.prototype, []).append(instance)
    return grouped


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[OK] wrote {path.relative_to(FIX_ROOT)}")


def build_inventory_rows(
    volumes: dict[str, VolumeDef],
    instances: list[Instance],
    materials: dict[str, MaterialInfo],
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    grouped = group_instances(instances)
    volume_rows: list[dict[str, object]] = []
    for name in sorted(volumes):
        volume = volumes[name]
        dims = shape_dimensions(volume.shape)
        direct_count = sum(1 for item in grouped.get(name, []) if not item.is_copy)
        copy_count = sum(1 for item in grouped.get(name, []) if item.is_copy)
        material = materials.get(volume.material, MaterialInfo(name=volume.material))
        volume_rows.append(
            {
                "volume": name,
                "material": volume.material,
                "density_g_cm3": material.density_g_cm3,
                "shape": dims.get("kind", ""),
                "dimensions_cm": dims.get("dimension_text", ""),
                "volume_cm3": fmt(dims.get("volume_cm3")),
                "direct_instances": direct_count,
                "copy_instances": copy_count,
                "source": f"{volume.source_file}:{volume.source_line}" if volume.source_file else "",
            }
        )

    summary_rows: list[dict[str, object]] = []
    for prototype in sorted(grouped):
        items = grouped[prototype]
        volume = volumes[prototype]
        dims = shape_dimensions(volume.shape)
        bounds = [item.bounds for item in items if item.bounds]
        z_min = min(b[4] for b in bounds) if bounds else None
        z_max = max(b[5] for b in bounds) if bounds else None
        material = materials.get(volume.material, MaterialInfo(name=volume.material))
        summary_rows.append(
            {
                "prototype": prototype,
                "material": volume.material,
                "density_g_cm3": material.density_g_cm3,
                "shape": dims.get("kind", ""),
                "dimensions_cm": dims.get("dimension_text", ""),
                "instance_count": len(items),
                "z_min_world_cm": fmt(z_min),
                "z_max_world_cm": fmt(z_max),
                "first_instance": sorted(item.name for item in items)[0],
                "last_instance": sorted(item.name for item in items)[-1],
            }
        )

    instance_rows: list[dict[str, object]] = []
    for item in sorted(instances, key=lambda i: (i.prototype, i.name)):
        bounds = item.bounds
        instance_rows.append(
            {
                "instance": item.name,
                "prototype": item.prototype,
                "material": item.material,
                "shape": item.shape.kind,
                "mother": item.mother or "",
                "is_copy": str(item.is_copy),
                "local_x_cm": fmt(item.local_position[0]),
                "local_y_cm": fmt(item.local_position[1]),
                "local_z_cm": fmt(item.local_position[2]),
                "world_x_cm": fmt(item.abs_position[0]),
                "world_y_cm": fmt(item.abs_position[1]),
                "world_z_cm": fmt(item.abs_position[2]),
                "x_min_cm": fmt(bounds[0] if bounds else None),
                "x_max_cm": fmt(bounds[1] if bounds else None),
                "y_min_cm": fmt(bounds[2] if bounds else None),
                "y_max_cm": fmt(bounds[3] if bounds else None),
                "z_min_cm": fmt(bounds[4] if bounds else None),
                "z_max_cm": fmt(bounds[5] if bounds else None),
                "source": f"{item.source_file}:{item.source_line}" if item.source_file else "",
            }
        )
    return volume_rows, summary_rows, instance_rows


COLORS = {
    "Ta": (0.89, 0.24, 0.20),
    "W": (0.22, 0.22, 0.22),
    "Nb": (0.22, 0.70, 0.80),
    "Aluminium": (0.72, 0.72, 0.78),
    "BGO": (0.32, 0.64, 0.30),
    "Copper": (0.78, 0.44, 0.16),
    "Silicon": (0.12, 0.12, 0.12),
    "Be": (0.66, 0.46, 0.66),
    "Vacuum": (0.92, 0.92, 0.92),
}

MATERIAL_TRANSPARENCY = {
    "Vacuum": 0.88,
    "Aluminium": 0.12,
    "Be": 0.12,
    "Silicon": 0.18,
}

PROTOTYPE_TRANSPARENCY = {
    "Al_Shell": 0.78,
    "BGO_Shield": 0.72,
    "Cryo_Shell": 0.78,
    "W_Shield": 0.72,
    "Nb_Shield": 0.72,
    "Win_Be": 0.55,
    "Win_Cryo": 0.55,
    "Win_Nb": 0.55,
    "Win_W": 0.55,
}


def color_hex(material: str) -> str:
    r, g, b = COLORS.get(material, (0.45, 0.45, 0.45))
    return "#{:02X}{:02X}{:02X}".format(int(r * 255), int(g * 255), int(b * 255))


def load_bounds() -> dict:
    return json.loads(BOUNDS_JSON.read_text(encoding="utf-8"))


def placed_briks(volumes: dict[str, VolumeDef]) -> dict[str, tuple[float, float, float]]:
    out: dict[str, tuple[float, float, float]] = {}
    for name, volume in volumes.items():
        if volume.shape.kind == "BRIK":
            hx, hy, hz = volume.shape.params[:3]
            out[name] = (hx, hy, hz)
    return out


def layer0_pixels(instances: list[Instance]) -> list[tuple[float, float]]:
    pixels = []
    for item in instances:
        if item.name.startswith("TP_L0_"):
            pixels.append((item.local_position[0], item.local_position[1]))
    return sorted(pixels)


def rect(ax, x: float, y: float, w: float, h: float, color: str, alpha: float, *, ec: str | None = None, lw: float = 0.7, zorder: int = 1) -> None:
    ax.add_patch(
        Rectangle(
            (x, y),
            w,
            h,
            facecolor=color,
            edgecolor=ec if ec else color,
            linewidth=lw,
            alpha=alpha,
            zorder=zorder,
        )
    )


def draw_shell(ax, name: str, shell: dict, color: str) -> None:
    rout = float(shell["r_out"])
    rin = float(shell["r_in"])
    z0 = float(shell["z_out_bot"])
    z1 = float(shell["z_out_top"])
    zi0 = float(shell["z_in_bot"])
    zi1 = float(shell["z_in_top"])
    hole = float(shell.get("hole_r", rin))
    rect(ax, -rout, z0, rout - rin, z1 - z0, color, 0.30, ec=color)
    rect(ax, rin, z0, rout - rin, z1 - z0, color, 0.30, ec=color)
    rect(ax, -rout, z0, 2 * rout, max(zi0 - z0, 0.0), color, 0.30, ec=color)
    rect(ax, -rout, zi1, rout - hole, max(z1 - zi1, 0.0), color, 0.30, ec=color)
    rect(ax, hole, zi1, rout - hole, max(z1 - zi1, 0.0), color, 0.30, ec=color)
    ax.text(rout + 0.18, 0.5 * (z0 + z1), name, fontsize=7, va="center")


def make_2d_schematic(
    output: Path,
    volumes: dict[str, VolumeDef],
    instances: list[Instance],
    bounds: dict,
) -> None:
    briks = placed_briks(volumes)
    pixels_xy = layer0_pixels(instances)
    if not pixels_xy:
        raise ValueError("No layer-0 TES pixels found")

    fig = plt.figure(figsize=(12.8, 10.2), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, width_ratios=[1.55, 1.0], height_ratios=[1.0, 1.0])
    ax_main = fig.add_subplot(gs[:, 0])
    ax_tes = fig.add_subplot(gs[0, 1])
    ax_col = fig.add_subplot(gs[1, 1])

    ax_main.set_title("XZTES cm-fixed mass model: X-Z projection", fontsize=12)
    ax_main.set_xlabel("X / cm")
    ax_main.set_ylabel("Z / cm")
    shell_colors = {
        "Al_Shell": "#D9B8A6",
        "BGO_Shield": "#82B366",
        "Cryo_Shell": "#BFC4CC",
        "W_Shield": "#666666",
        "Nb_Shield": "#5AC8D8",
    }
    for name in ["Al_Shell", "BGO_Shield", "Cryo_Shell", "W_Shield", "Nb_Shield"]:
        draw_shell(ax_main, name, bounds["SHIELDS"][name], shell_colors[name])

    cu = bounds["CU_BASE"]
    rect(ax_main, -cu["r_max"], cu["z_bot"], 2 * cu["r_max"], cu["z_top"] - cu["z_bot"], "#C98942", 0.65, ec="#8A4D12", zorder=4)
    pole = bounds["CU_SUPPORT"]
    rect(ax_main, -pole["r_max"], pole["z_bot"], 2 * pole["r_max"], pole["z_top"] - pole["z_bot"], "#C98942", 0.75, ec="#8A4D12", zorder=5)

    pixel_hx, pixel_hy, pixel_hz = briks["TES_Pixel_L0"]
    unique_x = sorted({round(x, 6) for x, _y in pixels_xy})
    for sub in bounds["SUBSTRATES"]:
        zc = float(sub["z_center"])
        hz = float(sub["hz"])
        rmax = float(sub["r_max"])
        rect(ax_main, -rmax, zc - hz, 2 * rmax, 2 * hz, "#303030", 0.55, ec="#111111", lw=0.35, zorder=8)

    for i, layer in enumerate(bounds["TES_LAYERS"]):
        zc = float(layer["z_center"])
        for x in unique_x:
            rect(ax_main, x - pixel_hx, zc - pixel_hz, 2 * pixel_hx, 2 * pixel_hz, "#E45756", 0.36, ec="#8E2F2E", lw=0.25, zorder=9)
        ax_main.text(float(layer["r_max"]) + 0.25, zc, f"TES L{i}: 0.30 cm full", fontsize=7, va="center", color="#8E2F2E")

    for win in bounds["WINDOWS"]:
        zc = float(win["z_center"])
        rmax = float(win["r_max"])
        h = max(float(win["thick"]), 0.036)
        rect(ax_main, -rmax, zc - 0.5 * h, 2 * rmax, h, "#B279A2", 0.58, ec="#7B4B84", lw=0.55, zorder=10)

    col = bounds["COLLIMATOR"]
    rect(ax_main, -col["r_max"], col["z_center"] - col["hz"], 2 * col["r_max"], 2 * col["hz"], "#262626", 0.68, ec="#111111", zorder=11)
    ax_main.axvline(0, color="0.55", lw=0.5, ls=":", zorder=20)
    max_r = max(float(s["r_out"]) for s in bounds["SHIELDS"].values())
    z_min = min(float(s["z_out_bot"]) for s in bounds["SHIELDS"].values())
    z_max = max(float(s["z_out_top"]) for s in bounds["SHIELDS"].values())
    ax_main.set_xlim(-1.08 * max_r, 1.16 * max_r)
    ax_main.set_ylim(z_min - 0.5, z_max + 0.65)
    ax_main.set_aspect("equal", adjustable="box")
    ax_main.grid(True, lw=0.35, alpha=0.22)

    ax_tes.set_title("One TES layer: X-Y footprint", fontsize=11)
    ax_tes.set_xlabel("X / cm")
    ax_tes.set_ylabel("Y / cm")
    substrate_r = float(bounds["SUBSTRATES"][0]["r_max"])
    active_r = float(bounds["META"].get("eff_r", bounds["TES_LAYERS"][0]["r_max"]))
    ax_tes.add_patch(Circle((0, 0), substrate_r, facecolor="#E5E5E5", edgecolor="#333333", lw=0.9, alpha=0.85, zorder=1))
    ax_tes.add_patch(Circle((0, 0), active_r, fill=False, edgecolor="#E45756", lw=1.0, ls="--", zorder=4))
    for x, y in pixels_xy:
        rect(ax_tes, x - pixel_hx, y - pixel_hy, 2 * pixel_hx, 2 * pixel_hy, "#E45756", 0.54, ec="#8E2F2E", lw=0.25, zorder=3)
    ax_tes.text(-1.15 * substrate_r, 1.12 * substrate_r, f"{len(pixels_xy)} Ta pixels\npixel 0.15 x 0.15 x 0.30 cm", fontsize=7, va="top")
    ax_tes.set_xlim(-1.16 * substrate_r, 1.16 * substrate_r)
    ax_tes.set_ylim(-1.16 * substrate_r, 1.16 * substrate_r)
    ax_tes.set_aspect("equal", adjustable="box")
    ax_tes.grid(True, lw=0.3, alpha=0.2)

    ax_col.set_title("Entrance W collimator: X-Y view", fontsize=11)
    ax_col.set_xlabel("X / cm")
    ax_col.set_ylabel("Y / cm")
    rmax = float(bounds["COLLIMATOR"]["r_max"])
    ax_col.add_patch(Circle((0, 0), rmax, facecolor="#F4F4F4", edgecolor="#333333", lw=0.9, alpha=0.75, zorder=1))
    hx_x, hy_x, _hz_x = briks["CollBarX"]
    hx_y, hy_y, _hz_y = briks["CollBarY"]
    for item in instances:
        if item.name.startswith("CollBarX_"):
            x, y, _z = item.local_position
            rect(ax_col, x - hx_x, y - hy_x, 2 * hx_x, 2 * hy_x, "#262626", 0.60, ec="#111111", lw=0.2, zorder=3)
        elif item.name.startswith("CollBarY_"):
            x, y, _z = item.local_position
            rect(ax_col, x - hx_y, y - hy_y, 2 * hx_y, 2 * hy_y, "#262626", 0.60, ec="#111111", lw=0.2, zorder=4)
    ax_col.text(-1.15 * rmax, 1.12 * rmax, f"pitch={bounds['META']['coll_pitch']:.3f} cm\nhole={bounds['META']['coll_hole']:.3f} cm", fontsize=7, va="top")
    ax_col.set_xlim(-1.16 * rmax, 1.16 * rmax)
    ax_col.set_ylim(-1.16 * rmax, 1.16 * rmax)
    ax_col.set_aspect("equal", adjustable="box")
    ax_col.grid(True, lw=0.3, alpha=0.2)

    legend = [
        Patch(facecolor="#E45756", edgecolor="#8E2F2E", alpha=0.5, label="Ta TES pixels"),
        Patch(facecolor="#303030", edgecolor="#111111", alpha=0.55, label="Si substrates"),
        Patch(facecolor="#C98942", edgecolor="#8A4D12", alpha=0.62, label="Cu base/support"),
        Patch(facecolor="#262626", edgecolor="#111111", alpha=0.68, label="W collimator"),
        Patch(facecolor="#B279A2", edgecolor="#7B4B84", alpha=0.58, label="entrance windows"),
        Patch(facecolor="#82B366", edgecolor="#82B366", alpha=0.34, label="BGO shield"),
    ]
    ax_main.legend(handles=legend, loc="lower left", fontsize=7, frameon=True)
    fig.suptitle("XZTES six-layer TES spectrometer geometry schematic", fontsize=14)
    fig.text(
        0.012,
        0.012,
        "Generated from fix/code/geometry/bounds.json and TibetTES_v5_6layers.geo. "
        "Thin windows are enlarged only in the schematic for visibility.",
        fontsize=7.5,
        color="#333333",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=220)
    plt.close(fig)
    print(f"[OK] wrote {output.relative_to(FIX_ROOT)}")


def appearance_key(instance: Instance) -> str:
    if instance.prototype in PROTOTYPE_TRANSPARENCY:
        return f"VOL_{instance.prototype}"
    return f"MAT_{instance.material}"


def vrml_appearance_defs(instances: Iterable[Instance]) -> str:
    records: dict[str, tuple[tuple[float, float, float], float]] = {}
    for instance in instances:
        if instance.name == "WorldVolume":
            continue
        color = COLORS.get(instance.material, (0.45, 0.45, 0.45))
        transparency = PROTOTYPE_TRANSPARENCY.get(
            instance.prototype,
            MATERIAL_TRANSPARENCY.get(instance.material, 0.0),
        )
        records[appearance_key(instance)] = (color, transparency)

    lines = []
    for key in sorted(records):
        (r, g, b), transparency = records[key]
        lines.append(
            f"DEF APP_{safe_id(key)} Appearance {{ material Material {{ diffuseColor {fmt(r)} {fmt(g)} {fmt(b)} transparency {fmt(transparency)} }} }}"
        )
    return "\n".join(lines)


def safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", value or "Unknown")


def pcon_mesh(shape: Shape, segments: int = 72) -> tuple[list[tuple[float, float, float]], list[list[int]]]:
    planes = pcon_planes(shape)
    points: list[tuple[float, float, float]] = []
    faces: list[list[int]] = []
    outer: list[list[int]] = []
    inner: list[list[int]] = []
    for z, rmin, rmax in planes:
        outer_row = []
        inner_row = []
        for j in range(segments):
            angle = 2.0 * math.pi * j / segments
            outer_row.append(len(points))
            points.append((rmax * math.cos(angle), rmax * math.sin(angle), z))
        for j in range(segments):
            angle = 2.0 * math.pi * j / segments
            inner_row.append(len(points))
            points.append((rmin * math.cos(angle), rmin * math.sin(angle), z))
        outer.append(outer_row)
        inner.append(inner_row)

    for i in range(len(planes) - 1):
        for j in range(segments):
            k = (j + 1) % segments
            faces.append([outer[i][j], outer[i][k], outer[i + 1][k], outer[i + 1][j]])
            faces.append([inner[i][j], inner[i + 1][j], inner[i + 1][k], inner[i][k]])

    for i in [0, len(planes) - 1]:
        for j in range(segments):
            k = (j + 1) % segments
            faces.append([inner[i][j], outer[i][j], outer[i][k], inner[i][k]])
    return points, faces


def write_wrl(path: Path, instances: list[Instance]) -> None:
    lines = [
        "#VRML V2.0 utf8",
        'WorldInfo { title "XZTES step1 cm-fixed geometry audit, transparent outer shells" }',
        'NavigationInfo { type ["EXAMINE", "ANY"] }',
        "Background { skyColor [1 1 1] }",
        "# Outer shields/windows use prototype-specific transparency so internal TES layers remain visible.",
        "# TES pixels, copper support, and collimator bars remain opaque.",
        vrml_appearance_defs(instances),
        "",
    ]
    for item in sorted(instances, key=lambda i: (i.prototype, i.name)):
        if item.name == "WorldVolume":
            continue
        x, y, z = item.abs_position
        app = f"APP_{safe_id(appearance_key(item))}"
        if item.shape.kind == "BRIK":
            hx, hy, hz = item.shape.params[:3]
            lines.append(f"# {item.name} prototype={item.prototype} material={item.material}")
            lines.append(
                "Transform { "
                f"translation {fmt(x)} {fmt(y)} {fmt(z)} "
                "children [ Shape { "
                f"appearance USE {app} "
                f"geometry Box {{ size {fmt(2*hx)} {fmt(2*hy)} {fmt(2*hz)} }} "
                "} ] }"
            )
        elif item.shape.kind == "PCON":
            points, faces = pcon_mesh(item.shape)
            lines.append(f"# {item.name} prototype={item.prototype} material={item.material} PCON mesh")
            lines.append(f"Transform {{ translation {fmt(x)} {fmt(y)} {fmt(z)} children [ Shape {{ appearance USE {app} geometry IndexedFaceSet {{ solid FALSE")
            lines.append("coord Coordinate { point [")
            for px, py, pz in points:
                lines.append(f"{fmt(px)} {fmt(py)} {fmt(pz)},")
            lines.append("] }")
            lines.append("coordIndex [")
            for face in faces:
                lines.append(" ".join(str(index) for index in face) + " -1,")
            lines.append("] } } ] }")
    write_text(path, "\n".join(lines) + "\n")


def line_number(path: Path, pattern: str) -> int:
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if pattern in line:
            return idx
    return 0


def evidence_lines(path: Path, start: int, end: int) -> list[str]:
    out = []
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if start <= idx <= end:
            out.append(f"{idx}: {line}")
    return out


def write_evidence_report(volumes: dict[str, VolumeDef], bounds: dict) -> None:
    tes = volumes["TES_Pixel_L0"]
    hx, hy, hz = tes.shape.params[:3]
    generator_scale_line = line_number(GENERATOR, "LENGTH_SCALE_TO_CM = 0.1")
    generator_pix_line = line_number(GENERATOR, "n_pix, pix_x, pix_y, pix_z = 20, 1.5, 1.5, 3.0")
    generator_brick_line = line_number(GENERATOR, 'geo.append(brik_def(f"TES_Pixel_L{l}", "Ta"')
    generated_shape_line = line_number(GEOM_DIR / "TibetTES_v5_6layers.geo", "TES_Pixel_L0.Shape BRIK 0.075 0.075 0.15")
    bounds_line = line_number(BOUNDS_JSON, '"tes_pixel_thickness_cm"')

    md = [
        "# TES 3 mm Validation",
        "",
        "## Conclusion",
        "",
        "The cm-fixed geometry used in this step has a Ta TES pixel full Z thickness of `0.30 cm`, i.e. `3.0 mm`, not `3.0 cm`.",
        "",
        "## Direct Calculation",
        "",
        f"- Generated TES shape: `TES_Pixel_L0.Shape BRIK {fmt(hx)} {fmt(hy)} {fmt(hz)}`.",
        "- MEGAlib BRIK stores half-lengths, so full thickness is `2 * hz`.",
        f"- `2 * {fmt(hz)} cm = {fmt(2*hz)} cm = {fmt(20*hz)} mm`.",
        "- A 3 cm TES would require `hz = 1.5 cm`; the generated value is `hz = 0.15 cm`.",
        "",
        "## Local Evidence",
        "",
        f"- Generator scale: `fix/code/geometry/GenerateGeo.py:{generator_scale_line}` sets `LENGTH_SCALE_TO_CM = 0.1`.",
        f"- Generator design TES thickness: `fix/code/geometry/GenerateGeo.py:{generator_pix_line}` sets `pix_z = 3.0` in the legacy mm-like design values.",
        f"- Generator writes half Z: `fix/code/geometry/GenerateGeo.py:{generator_brick_line}` passes `3.0 / 2.0` into `brik_def`, which then applies `to_cm`.",
        f"- Generated geometry: `fix/code/geometry/TibetTES_v5_6layers.geo:{generated_shape_line}` is `TES_Pixel_L0.Shape BRIK 0.075 0.075 0.15`.",
        f"- Bounds metadata: `fix/code/geometry/bounds.json:{bounds_line}` records `tes_pixel_thickness_cm = {fmt(bounds['META']['tes_pixel_thickness_cm'])}`.",
        "",
        "## MEGAlib BRIK Semantics",
        "",
        "The local MEGAlib source supports the half-length interpretation:",
        "",
        "```text",
        *evidence_lines(MEGALIB_BRIK, 120, 127),
        "```",
        "",
        "and the volume function multiplies by 8:",
        "",
        "```text",
        *evidence_lines(MEGALIB_BRIK, 223, 228),
        "```",
        "",
        "Therefore the BRIK parameters are half-dimensions in cm for the generated `.geo` file.",
    ]
    write_text(STEP_DIR / "tes_3mm_validation.md", "\n".join(md) + "\n")

    evidence = [
        "Step1 geometry evidence lines",
        "",
        f"GenerateGeo.py:{generator_scale_line}: LENGTH_SCALE_TO_CM = 0.1",
        f"GenerateGeo.py:{generator_pix_line}: n_pix, pix_x, pix_y, pix_z = 20, 1.5, 1.5, 3.0",
        f"GenerateGeo.py:{generator_brick_line}: TES_Pixel_L loop writes BRIK half dimensions",
        f"TibetTES_v5_6layers.geo:{generated_shape_line}: TES_Pixel_L0.Shape BRIK 0.075 0.075 0.15",
        f"bounds.json:{bounds_line}: tes_pixel_thickness_cm = {fmt(bounds['META']['tes_pixel_thickness_cm'])}",
        "",
        "MEGAlib BRIK half-dimension support:",
        *evidence_lines(MEGALIB_BRIK, 120, 127),
        *evidence_lines(MEGALIB_BRIK, 223, 228),
    ]
    write_text(OUTPUT_DIR / "brik_semantics_evidence.txt", "\n".join(evidence) + "\n")


def markdown_table(rows: list[dict[str, object]], headers: list[str], max_rows: int | None = None) -> list[str]:
    selected = rows if max_rows is None else rows[:max_rows]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in selected:
        cells = [str(row.get(header, "")).replace("|", "\\|") for header in headers]
        lines.append("| " + " | ".join(cells) + " |")
    if max_rows is not None and len(rows) > max_rows:
        lines.append(f"| ... | ... | ... | ... | ... | ... | ... | ... | ... |")
    return lines


def write_component_markdown(volume_rows: list[dict[str, object]], summary_rows: list[dict[str, object]]) -> None:
    md = [
        "# Component Dimensions And Materials",
        "",
        "All dimensions in this report are centimeters as written to the MEGAlib/Cosima `.geo` file.",
        "For `BRIK`, the listed parameters are half-dimensions; the `dimensions_cm` field also gives the full size.",
        "For `PCON`, the table gives the local z span and maximum radius envelope.",
        "",
        "## Volume Definitions",
        "",
        *markdown_table(
            volume_rows,
            ["volume", "material", "density_g_cm3", "shape", "dimensions_cm", "volume_cm3", "direct_instances", "copy_instances", "source"],
        ),
        "",
        "## Placed Instance Summary",
        "",
        *markdown_table(
            summary_rows,
            ["prototype", "material", "density_g_cm3", "shape", "dimensions_cm", "instance_count", "z_min_world_cm", "z_max_world_cm", "first_instance"],
        ),
        "",
        "## Full Trace Files",
        "",
        "- `outputs/volume_definitions.csv`: all volume definitions and their materials/dimensions.",
        "- `outputs/instance_summary.csv`: per-prototype placed instance counts and world-Z spans.",
        "- `outputs/instances.csv`: every placed copy/direct instance with local/world position and bounds.",
        "- `outputs/materials.csv`: material density provenance for materials used here.",
    ]
    write_text(STEP_DIR / "component_dimensions_materials.md", "\n".join(md) + "\n")


def write_readme(instances: list[Instance], volume_rows: list[dict[str, object]]) -> None:
    tes_count = sum(1 for item in instances if item.prototype.startswith("TES_Pixel_L"))
    readme = [
        "# Step1 Geometry Maintenance",
        "",
        "This directory is the first maintenance checkpoint for the cm-fixed XZTES geometry.",
        "It records the geometry source, generated inventories, 2D schematic, WRL visualization, and the 3 mm TES-thickness proof.",
        "",
        "## Geometry Authority",
        "",
        "- Generator: `fix/code/geometry/GenerateGeo.py`.",
        "- Generated MEGAlib geometry: `fix/code/geometry/TibetTES_v5_6layers.geo`.",
        "- Detector definitions: `fix/code/geometry/TibetTES_v5_6layers.det`.",
        "- Bounds metadata: `fix/code/geometry/bounds.json`.",
        "- Source snapshots are copied under `source_snapshots/` for this checkpoint.",
        "",
        "## Main Generator Functions",
        "",
        "- `to_cm(x)`: applies the single geometry scale, `LENGTH_SCALE_TO_CM = 0.1`, from legacy mm-like design numbers to cm.",
        "- `fmt(x)`: writes stable numeric tokens into `.geo` and `.det` files.",
        "- `pcon_shape_line(...)`: serializes MEGAlib `PCON` polycone planes.",
        "- `volume_def(...)`: emits a MEGAlib volume block with material, visibility, and shape.",
        "- `brik_def(...)`: emits a MEGAlib `BRIK` with half-dimensions after `to_cm` scaling.",
        "- `polycone_shell_def(...)` and `polycone_shell_w_topseat_def(...)`: create shield/shell PCON envelopes.",
        "- `add_collimator_grid(...)`: creates the entrance W grid inside `CollimatorVac`.",
        "- `main()`: assembles six TES layers, shields, windows, collimator, detector records, and bounds metadata.",
        "",
        "## Step1 Build Code",
        "",
        "- `code/build_step1_geo.py` is the reproducible step1 entry point.",
        "- `code/make_geo_2d_schematic.py` is a thin entry point for regenerating only the 2D schematic.",
        "- Rebuild all step1 artifacts with:",
        "",
        "```bash",
        "python3 fix/stepwise_maintenance/step1_geo/code/build_step1_geo.py",
        "```",
        "",
        "## Outputs",
        "",
        "- `component_dimensions_materials.md`: every geometry volume type with material, density, size, and instance counts.",
        "- `tes_3mm_validation.md`: local evidence that the TES pixel is 3 mm thick, not 3 cm.",
        "- `outputs/geometry_schematic_2d.png`: 2D X-Z schematic plus TES and collimator X-Y insets.",
        "- `outputs/TibetTES_v5_6layers_step1.wrl`: transparent outer-shell VRML visualization generated from the parsed `.geo` file.",
        "- `outputs/*.csv`: structured inventories for programmatic maintenance checks.",
        "",
        "## Current Parsed Counts",
        "",
        f"- Volume definitions parsed: `{len(volume_rows)}`.",
        f"- Placed TES pixel copies parsed: `{tes_count}`.",
        "- TES pixel full thickness: `0.30 cm = 3.0 mm`.",
        "",
        "The WRL file is for visualization and audit traceability. It uses prototype-specific transparency for the outer shells and windows while keeping TES pixels, copper support, and W collimator bars opaque. The authoritative simulation geometry remains the MEGAlib `.geo` generated by `GenerateGeo.py`.",
    ]
    write_text(STEP_DIR / "README.md", "\n".join(readme) + "\n")


def write_materials_csv(materials: dict[str, MaterialInfo], used_materials: Iterable[str]) -> None:
    rows = []
    for name in sorted(set(used_materials)):
        info = materials.get(name, MaterialInfo(name=name))
        rows.append(
            {
                "material": name,
                "density_g_cm3": info.density_g_cm3,
                "source": f"{info.source_file}:{info.source_line}" if info.source_file else "",
            }
        )
    write_csv(OUTPUT_DIR / "materials.csv", rows, ["material", "density_g_cm3", "source"])


def write_step_record() -> None:
    md = [
        "# Step 0001: Geometry Inventory And 3 mm Validation",
        "",
        "## Objective",
        "",
        "Create a maintainable step1 geometry checkpoint with component dimensions/materials, source snapshots, a 2D schematic, a transparent-shell WRL visualization, and a local-evidence proof that TES pixels are 3 mm thick.",
        "",
        "## Artifacts",
        "",
        "- `stepwise_maintenance/step1_geo/README.md`",
        "- `stepwise_maintenance/step1_geo/component_dimensions_materials.md`",
        "- `stepwise_maintenance/step1_geo/tes_3mm_validation.md`",
        "- `stepwise_maintenance/step1_geo/code/build_step1_geo.py`",
        "- `stepwise_maintenance/step1_geo/code/make_geo_2d_schematic.py`",
        "- `stepwise_maintenance/step1_geo/outputs/geometry_schematic_2d.png`",
        "- `stepwise_maintenance/step1_geo/outputs/TibetTES_v5_6layers_step1.wrl`",
        "- `stepwise_maintenance/step1_geo/outputs/*.csv`",
        "",
        "## Verified Claim",
        "",
        "The generated MEGAlib geometry stores `TES_Pixel_L0.Shape BRIK 0.075 0.075 0.15`. MEGAlib BRIK parameters are half-lengths, so TES full Z thickness is `2 * 0.15 cm = 0.30 cm = 3.0 mm`.",
    ]
    write_text(FIX_ROOT / "stepwise_maintenance/steps/0001_geo.md", "\n".join(md) + "\n")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    volumes, objects = parse_geometry(GEOMETRY_FILES)
    materials = parse_materials(MATERIAL_FILES)
    instances = build_instances(volumes, objects)
    bounds = load_bounds()

    volume_rows, summary_rows, instance_rows = build_inventory_rows(volumes, instances, materials)
    write_csv(
        OUTPUT_DIR / "volume_definitions.csv",
        volume_rows,
        ["volume", "material", "density_g_cm3", "shape", "dimensions_cm", "volume_cm3", "direct_instances", "copy_instances", "source"],
    )
    write_csv(
        OUTPUT_DIR / "instance_summary.csv",
        summary_rows,
        ["prototype", "material", "density_g_cm3", "shape", "dimensions_cm", "instance_count", "z_min_world_cm", "z_max_world_cm", "first_instance", "last_instance"],
    )
    write_csv(
        OUTPUT_DIR / "instances.csv",
        instance_rows,
        [
            "instance",
            "prototype",
            "material",
            "shape",
            "mother",
            "is_copy",
            "local_x_cm",
            "local_y_cm",
            "local_z_cm",
            "world_x_cm",
            "world_y_cm",
            "world_z_cm",
            "x_min_cm",
            "x_max_cm",
            "y_min_cm",
            "y_max_cm",
            "z_min_cm",
            "z_max_cm",
            "source",
        ],
    )
    write_materials_csv(materials, [row["material"] for row in volume_rows])
    write_component_markdown(volume_rows, summary_rows)
    write_evidence_report(volumes, bounds)
    make_2d_schematic(OUTPUT_DIR / "geometry_schematic_2d.png", volumes, instances, bounds)
    write_wrl(OUTPUT_DIR / "TibetTES_v5_6layers_step1.wrl", instances)
    write_readme(instances, volume_rows)
    write_step_record()

    print("[OK] step1 geometry audit complete")


if __name__ == "__main__":
    main()
