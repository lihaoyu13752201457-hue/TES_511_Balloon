#!/usr/bin/env python3
"""Build Step00 visual and closure artifacts for v3p5 center-finger geometry."""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-step00-v3p5")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Patch, Rectangle


ROOT = Path(__file__).resolve().parents[3]
STEP = ROOT / "stepwise_maintenance" / "step00_geometry"
OUT = STEP / "outputs" / "v3p5_centerfinger"

MODEL = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
GEOM_DIR = ROOT / "outputs" / "geometry" / MODEL
GEOM_BUILDER = ROOT / "code" / "geometry" / "build_demo2_dr_v3p5_centerfinger_megalib.py"

SOURCE_BOUNDS = ROOT / "geo_refer" / "DEMO2_DR_v3p5_minpatch_centerfinger_bounds.json"
SOURCE_VALIDATION = ROOT / "geo_refer" / "DEMO2_DR_v3p5_minpatch_centerfinger_validation.json"
PROXY_VALIDATION = GEOM_DIR / "geometry_proxy_validation.json"
GEO = GEOM_DIR / f"{MODEL}.geo"
SETUP = GEOM_DIR / f"{MODEL}.geo.setup"
COSIMA_LOG = GEOM_DIR / "cosima_overlap.log"
OVERLAP_SOURCE = GEOM_DIR / "overlap_check.source"

WRL = OUT / "DEMO2_DR_v3p5_centerfinger_step00.wrl"
SCHEMATIC = OUT / "DEMO2_DR_v3p5_centerfinger_step00_2d_schematic.png"
XZ_OVERVIEW = OUT / "DEMO2_DR_v3p5_centerfinger_step00_xz_overview.png"
CLOSURE = OUT / "step00_v3p5_centerfinger_closure.json"
BUILD_LOG = OUT / "geometry_proxy_build.log"

BEAM_Z = -5.2
BEAM_R = 1.898


COLORS = {
    "Ta": "#d62728",
    "Silicon": "#303030",
    "Copper": "#c47c28",
    "Aluminium": "#a6a6a6",
    "Nb": "#4dbbd5",
    "Cryoperm": "#4b64a1",
    "W": "#242424",
    "Be": "#56b4e9",
    "CsI": "#6fa8dc",
    "StainlessSteel": "#7f7f7f",
    "CuNi": "#8c6d31",
    "SilverSinterProxy": "#c0c0c0",
    "CharcoalProxy": "#6b4f3a",
    "G10": "#70ad47",
    "NbTiCableProxy": "#9467bd",
    "Kapton": "#f2c744",
    "Vacuum": "#ffffff",
}


def fmt(value: float | int) -> str:
    value = float(value)
    if abs(value) < 5.0e-13:
        value = 0.0
    return f"{value:.9g}"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def tes_pixel_positions(radius: float = 1.8, pitch: float = 0.155, expected: int = 376) -> list[tuple[float, float]]:
    positions: list[tuple[float, float]] = []
    n = int(math.ceil(radius / pitch)) + 1
    for iy in range(-n, n + 1):
        for iz in range(-n, n + 1):
            y = iy * pitch
            z = iz * pitch
            if y * y + z * z <= radius * radius:
                positions.append((y, z))
    positions.sort(key=lambda p: (p[0] * p[0] + p[1] * p[1], p[0], p[1]))
    if len(positions) < expected:
        raise RuntimeError(f"TES footprint produced only {len(positions)} pixels")
    return sorted(positions[:expected])


def run_geometry_builder() -> dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [sys.executable, str(GEOM_BUILDER)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    BUILD_LOG.write_text(proc.stdout, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"geometry builder failed with return code {proc.returncode}; see {rel(BUILD_LOG)}")
    return json.loads(PROXY_VALIDATION.read_text(encoding="utf-8"))


def material_color(material: str, name: str = "") -> str:
    if "TES" in name:
        return COLORS["Ta"]
    return COLORS.get(material, "#666666")


def vrml_color(material: str, name: str) -> tuple[float, float, float, float]:
    hex_color = material_color(material, name).lstrip("#")
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    transparency = {
        "CsI": 0.68,
        "Aluminium": 0.58,
        "Cryoperm": 0.45,
        "Nb": 0.45,
        "Copper": 0.28,
        "W": 0.35,
        "Ta": 0.12,
        "Silicon": 0.35,
    }.get(material, 0.45)
    if "TES" in name:
        transparency = 0.08
    return r, g, b, transparency


def parse_geo_volumes(path: Path) -> list[dict[str, Any]]:
    volumes: dict[str, dict[str, Any]] = {}
    current = ""
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        m = re.match(r"^Volume\s+([A-Za-z0-9_]+)$", line)
        if m:
            current = m.group(1)
            volumes.setdefault(current, {"name": current})
            continue
        m = re.match(r"^([A-Za-z0-9_]+)\.Copy\s+([A-Za-z0-9_]+)$", line)
        if m:
            template, copy_name = m.group(1), m.group(2)
            volumes.setdefault(copy_name, {"name": copy_name})["template"] = template
            current = copy_name
            continue
        m = re.match(r"^([A-Za-z0-9_]+)\.Material\s+(\S+)$", line)
        if m:
            volumes.setdefault(m.group(1), {"name": m.group(1)})["material"] = m.group(2)
            continue
        m = re.match(r"^([A-Za-z0-9_]+)\.Position\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)$", line)
        if m:
            volumes.setdefault(m.group(1), {"name": m.group(1)})["position"] = tuple(float(m.group(i)) for i in range(2, 5))
            continue
        m = re.match(r"^([A-Za-z0-9_]+)\.Shape\s+BRIK\s+(.+)$", line)
        if m:
            vals = [float(x) for x in m.group(2).split()]
            volumes.setdefault(m.group(1), {"name": m.group(1)})["shape"] = {"type": "BRIK", "hx": vals[0], "hy": vals[1], "hz": vals[2]}
            continue
        m = re.match(r"^([A-Za-z0-9_]+)\.Shape\s+PCON\s+(.+)$", line)
        if m:
            vals = [float(x) for x in m.group(2).split()]
            nplanes = int(vals[2])
            planes = []
            cursor = 3
            for _ in range(nplanes):
                planes.append((vals[cursor], vals[cursor + 1], vals[cursor + 2]))
                cursor += 3
            volumes.setdefault(m.group(1), {"name": m.group(1)})["shape"] = {
                "type": "PCON",
                "phi0": vals[0],
                "dphi": vals[1],
                "planes": planes,
            }
            continue
        m = re.match(r"^([A-Za-z0-9_]+)\.Mother\s+([A-Za-z0-9_]+)$", line)
        if m:
            volumes.setdefault(m.group(1), {"name": m.group(1)})["mother"] = m.group(2)

    def inherited(rec: dict[str, Any], key: str) -> Any:
        if key in rec:
            return rec[key]
        template = rec.get("template")
        if template and template in volumes:
            return inherited(volumes[template], key)
        return None

    resolved_positions: dict[str, tuple[float, float, float]] = {}

    def global_position(name: str, stack: set[str] | None = None) -> tuple[float, float, float]:
        if name in resolved_positions:
            return resolved_positions[name]
        stack = set() if stack is None else set(stack)
        if name in stack:
            raise RuntimeError(f"Cycle in MEGAlib mother hierarchy at {name}")
        stack.add(name)
        rec = volumes.get(name, {"name": name})
        x, y, z = rec.get("position", (0.0, 0.0, 0.0))
        mother = rec.get("mother")
        if mother and mother != "WorldVolume":
            px, py, pz = global_position(mother, stack)
            x, y, z = x + px, y + py, z + pz
        resolved_positions[name] = (x, y, z)
        return resolved_positions[name]

    out = []
    for name, rec in volumes.items():
        if name == "WorldVolume":
            continue
        if "mother" not in rec:
            continue
        shape = inherited(rec, "shape")
        material = inherited(rec, "material")
        if shape is None or material is None:
            continue
        out.append({"name": name, "material": material, "shape": shape, "position": global_position(name)})
    return out


def box_node(name: str, x: float, y: float, z: float, hx: float, hy: float, hz: float, material: str) -> str:
    r, g, b, t = vrml_color(material, name)
    return f"""# {name}
Transform {{
  translation {fmt(x)} {fmt(y)} {fmt(z)}
  children [
    Shape {{
      appearance Appearance {{
        material Material {{ diffuseColor {r:.3f} {g:.3f} {b:.3f} transparency {t:.3f} }}
      }}
      geometry Box {{ size {fmt(2.0 * hx)} {fmt(2.0 * hy)} {fmt(2.0 * hz)} }}
    }}
  ]
}}
"""


def cylinder_node(name: str, x: float, y: float, z: float, radius: float, height: float, material: str, note: str = "") -> str:
    r, g, b, t = vrml_color(material, name)
    note_line = f"# {note}\n" if note else ""
    return f"""# {name}
{note_line}Transform {{
  translation {fmt(x)} {fmt(y)} {fmt(z)}
  rotation 1 0 0 1.57079632679
  children [
    Shape {{
      appearance Appearance {{
        material Material {{ diffuseColor {r:.3f} {g:.3f} {b:.3f} transparency {t:.3f} }}
      }}
      geometry Cylinder {{ radius {fmt(radius)} height {fmt(height)} }}
    }}
  ]
}}
"""


def write_wrl(volumes: list[dict[str, Any]], proxy_validation: dict[str, Any]) -> None:
    frame = proxy_validation.get("geometry_extents", {}).get("instrument_frame", {})
    rotation_y_deg = float((frame.get("rotation_deg") or [0.0, 0.0, 0.0])[1])
    rotation_y_rad = math.radians(rotation_y_deg)
    lines = [
        "#VRML V2.0 utf8",
        'WorldInfo { title "DEMO2_DR_v3p5 center-finger Step00 simulation geometry proxy" }',
        "",
        "Viewpoint { position 32 -58 36 orientation 0.78 0.20 0.59 1.05 description \"overview\" }",
        "NavigationInfo { type [\"EXAMINE\", \"ANY\"] }",
        "",
        "# Simulation pointing transform: InstrumentFrame.Rotation 0 45 0 in the MEGAlib proxy.",
        f"Transform {{ rotation 0 1 0 {fmt(rotation_y_rad)} children [",
    ]
    for rec in volumes:
        name = rec["name"]
        material = rec["material"]
        x, y, z = rec["position"]
        shape = rec["shape"]
        if shape["type"] == "BRIK":
            lines.append(box_node(name, x, y, z, shape["hx"], shape["hy"], shape["hz"], material))
        elif shape["type"] == "PCON":
            planes = shape["planes"]
            zvals = [p[0] for p in planes]
            rvals = [p[2] for p in planes]
            local_z0 = min(zvals)
            local_z1 = max(zvals)
            radius = max(rvals)
            height = max(local_z1 - local_z0, 1.0e-5)
            zc = z + 0.5 * (local_z0 + local_z1)
            note = f"PCON visual envelope: phi0={fmt(shape['phi0'])}, dphi={fmt(shape['dphi'])}"
            lines.append(cylinder_node(name, x, y, zc, radius, height, material, note=note))
    lines.append("] }")
    WRL.write_text("\n".join(lines) + "\n", encoding="utf-8")


def rect(ax: Any, x0: float, x1: float, z0: float, z1: float, material: str, *, alpha: float = 0.35, lw: float = 0.8) -> None:
    ax.add_patch(
        Rectangle(
            (x0, z0),
            x1 - x0,
            z1 - z0,
            facecolor=material_color(material),
            edgecolor="black",
            linewidth=lw,
            alpha=alpha,
        )
    )


def add_component_xz(ax: Any, comp: dict[str, Any]) -> None:
    p = comp["params"]
    mat = comp["material"]
    shape = comp["shape"]
    if shape == "z_cylinder":
        r = p["r_cm"]
        h = p.get("h_cm", p.get("z1_cm", 0.0) - p.get("z0_cm", 0.0))
        zc = p.get("z_center_cm", 0.5 * (p.get("z0_cm", 0.0) + p.get("z1_cm", 0.0)))
        rect(ax, -r, r, zc - 0.5 * h, zc + 0.5 * h, mat, alpha=0.22)
    elif shape in {"z_annulus", "z_annulus_phi", "z_annulus_phi_segment"}:
        r = p["r_out_cm"]
        rect(ax, -r, r, p["z0_cm"], p["z1_cm"], mat, alpha=0.12, lw=0.45)
    elif shape == "z_can_open_top":
        r0, r1 = p["r_in_cm"], p["r_out_cm"]
        rect(ax, -r1, -r0, p["z_in_bot_cm"], p["z_top_cm"], mat, alpha=0.28)
        rect(ax, r0, r1, p["z_in_bot_cm"], p["z_top_cm"], mat, alpha=0.28)
        rect(ax, -r1, r1, p["z_out_bot_cm"], p["z_in_bot_cm"], mat, alpha=0.20)
    elif shape == "z_shell_top_annulus":
        r0, r1 = p["r_in_cm"], p["r_out_cm"]
        rect(ax, -r1, -r0, p["z_in_bot_cm"], p["z_top_cm"], mat, alpha=0.22)
        rect(ax, r0, r1, p["z_in_bot_cm"], p["z_top_cm"], mat, alpha=0.22)
        rect(ax, -r1, r1, p["z_out_bot_cm"], p["z_in_bot_cm"], mat, alpha=0.16)
        rect(ax, -r1, r1, p["top_ann_z0_cm"], p["top_ann_z1_cm"], mat, alpha=0.16)
    elif shape == "x_disc_stack":
        r = p["disc_r_cm"]
        t = p["disc_t_cm"]
        zc = p["axis_z_cm"]
        alpha = 0.75 if mat == "Ta" else 0.28
        for x in p["x_centers_cm"]:
            rect(ax, x - 0.5 * t, x + 0.5 * t, zc - r, zc + r, mat, alpha=alpha, lw=0.45)
    elif shape == "x_disc":
        r = p["r_cm"]
        t = p["thickness_cm"]
        rect(ax, p["x_center_cm"] - 0.5 * t, p["x_center_cm"] + 0.5 * t, p.get("axis_z_cm", BEAM_Z) - r, p.get("axis_z_cm", BEAM_Z) + r, mat, alpha=0.35)
    elif shape == "x_annulus":
        x = p["x_center_cm"]
        t = p["thickness_cm"]
        zc = p["axis_z_cm"]
        rect(ax, x - 0.5 * t, x + 0.5 * t, zc + p["r_in_cm"], zc + p["r_out_cm"], mat, alpha=0.42)
        rect(ax, x - 0.5 * t, x + 0.5 * t, zc - p["r_out_cm"], zc - p["r_in_cm"], mat, alpha=0.42)
    elif shape == "x_cylinder_offaxis":
        r = p["r_cm"]
        rect(ax, p["x0_cm"], p["x1_cm"], p["z_center_cm"] - r, p["z_center_cm"] + r, mat, alpha=0.68, lw=0.6)
    elif shape == "x_can":
        zc = p["axis_z_cm"]
        rect(ax, p["x0_cm"], p["x1_cm"], zc + p["r_in_cm"], zc + p["r_out_cm"], mat, alpha=0.25)
        rect(ax, p["x0_cm"], p["x1_cm"], zc - p["r_out_cm"], zc - p["r_in_cm"], mat, alpha=0.25)
    elif shape == "x_tube":
        zc = p["axis_z_cm"]
        rect(ax, p["x0_cm"], p["x1_cm"], zc + p["r_in_cm"], zc + p["r_out_cm"], mat, alpha=0.50)
        rect(ax, p["x0_cm"], p["x1_cm"], zc - p["r_out_cm"], zc - p["r_in_cm"], mat, alpha=0.50)
    elif shape == "box":
        rect(ax, p["x_cm"] - p["hx_cm"], p["x_cm"] + p["hx_cm"], p["z0_cm"], p["z1_cm"], mat, alpha=0.40)


def plot_xz(ax: Any, bounds: dict[str, Any], *, detail: bool) -> None:
    for comp in bounds["COMPONENTS"]:
        add_component_xz(ax, comp)
    ax.axhline(BEAM_Z, color="#d62728", linewidth=1.8, linestyle="--")
    ax.annotate("511 keV beam: -x to +x", xy=(-17, BEAM_Z), xytext=(-17, BEAM_Z + 3.2), arrowprops={"arrowstyle": "->", "color": "#d62728"}, color="#d62728")
    ax.text(3.42, BEAM_Z + 2.9, "downstream Cu support disk", fontsize=8)
    ax.text(4.4, BEAM_Z + 1.15, "four off-axis Cu fingers", color="#7a3f12", fontsize=8)
    ax.set_xlabel("x [cm]")
    ax.set_ylabel("z [cm]")
    ax.set_aspect("equal", adjustable="box")
    if detail:
        ax.set_xlim(-8, 8)
        ax.set_ylim(-9, -1.5)
        ax.set_title("Detector bay X-Z zoom")
    else:
        ax.set_xlim(-22, 22)
        ax.set_ylim(-23, 40)
        ax.set_title("Simulation geometry X-Z overview")
    ax.grid(alpha=0.18)


def plot_yz_sites(ax: Any, bounds: dict[str, Any]) -> None:
    ax.add_patch(Circle((0, BEAM_Z), BEAM_R, fill=False, edgecolor="#d62728", linestyle="--", linewidth=1.5, label="beam/window radius"))
    ax.add_patch(Circle((0, BEAM_Z), 1.8, fill=False, edgecolor=COLORS["Ta"], linewidth=1.2, label="TES active radius"))
    ax.add_patch(Circle((0, BEAM_Z), 2.2, fill=False, edgecolor=COLORS["Copper"], linewidth=1.2, label="support disk radius"))
    tes = next(c for c in bounds["COMPONENTS"] if c["name"] == "TES_Ta_Absorber_Stack_side_entry")
    ptes = tes["params"]
    pixels = tes_pixel_positions(float(ptes["disc_r_cm"]), float(ptes.get("pixel_pitch_cm", 0.155)), int(ptes["pixels_per_layer"]))
    ax.scatter([p[0] for p in pixels], [BEAM_Z + p[1] for p in pixels], s=4.5, color=COLORS["Ta"], alpha=0.42, linewidths=0, label="376 TES pixels/layer")
    fingers = [c for c in bounds["COMPONENTS"] if c["name"].startswith("Cu_ColdFinger_OffAxis_")]
    stems = [c for c in bounds["COMPONENTS"] if c["name"].startswith("Cu_ColdFinger_Stem_")]
    for comp in fingers:
        p = comp["params"]
        ax.add_patch(Circle((p["y_center_cm"], p["z_center_cm"]), p["r_cm"], color=COLORS["Copper"], alpha=0.85))
        ax.text(p["y_center_cm"] + 0.08, p["z_center_cm"] + 0.08, comp["name"].split("_")[3], fontsize=7)
    for comp in stems:
        p = comp["params"]
        ax.plot([p["y_center_cm"], p["y_center_cm"]], [p["z0_cm"], p["z1_cm"]], color="#8c4b16", linewidth=2.0, alpha=0.75)
    ax.scatter([0], [BEAM_Z], marker="+", s=90, color="#d62728", zorder=5)
    ax.set_xlabel("y [cm]")
    ax.set_ylabel("z [cm]")
    ax.set_title("Y-Z: off-axis thermal sites")
    ax.set_xlim(-3.0, 3.0)
    ax.set_ylim(-8.2, -0.1)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(alpha=0.18)
    ax.legend(loc="upper right", fontsize=7)


def plot_xy_sites(ax: Any, bounds: dict[str, Any]) -> None:
    fingers = [c for c in bounds["COMPONENTS"] if c["name"].startswith("Cu_ColdFinger_OffAxis_")]
    pads = [c for c in bounds["COMPONENTS"] if c["name"].startswith("Cu_MXC_Clamp_Pad_")]
    for comp in fingers:
        p = comp["params"]
        color = "#b87333" if p["z_center_cm"] > BEAM_Z else "#7a3f12"
        ax.plot([p["x0_cm"], p["x1_cm"]], [p["y_center_cm"], p["y_center_cm"]], color=color, linewidth=3.0, alpha=0.8)
    for comp in pads:
        p = comp["params"]
        ax.add_patch(Circle((p["x_center_cm"], p["y_center_cm"]), p["r_cm"], color=COLORS["Copper"], alpha=0.45, ec="black"))
    ax.axhline(0, color="#d62728", linestyle="--", linewidth=1.0)
    ax.text(3.2, 0.12, "beam centerline has no Cu finger", color="#d62728", fontsize=8)
    ax.set_xlabel("x [cm]")
    ax.set_ylabel("y [cm]")
    ax.set_title("X-Y: four unique MXC pad sites")
    ax.set_xlim(3.0, 7.4)
    ax.set_ylim(-2.3, 2.3)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(alpha=0.18)


def write_2d_schematic(bounds: dict[str, Any]) -> None:
    fig = plt.figure(figsize=(18, 6.5), constrained_layout=True)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.45, 1.0, 1.0])
    plot_xz(fig.add_subplot(gs[0, 0]), bounds, detail=True)
    plot_yz_sites(fig.add_subplot(gs[0, 1]), bounds)
    plot_xy_sites(fig.add_subplot(gs[0, 2]), bounds)
    fig.suptitle("DEMO2_DR_v3p5 center-finger Step00 simulation geometry", fontsize=14)
    fig.savefig(SCHEMATIC, dpi=190)
    plt.close(fig)

    fig2, ax = plt.subplots(figsize=(9.2, 12.5), constrained_layout=True)
    plot_xz(ax, bounds, detail=False)
    legend = [
        Patch(facecolor=COLORS["Ta"], edgecolor="black", label="Ta TES"),
        Patch(facecolor=COLORS["Copper"], edgecolor="black", label="Copper"),
        Patch(facecolor=COLORS["CsI"], edgecolor="black", label="CsI shield"),
        Patch(facecolor=COLORS["Aluminium"], edgecolor="black", label="Aluminium"),
        Patch(facecolor=COLORS["W"], edgecolor="black", label="Tungsten"),
    ]
    ax.legend(handles=legend, loc="upper right", fontsize=8)
    fig2.savefig(XZ_OVERVIEW, dpi=190)
    plt.close(fig2)


def closure_payload(bounds: dict[str, Any], source_validation: dict[str, Any], proxy_validation: dict[str, Any], volumes: list[dict[str, Any]]) -> dict[str, Any]:
    log_text = COSIMA_LOG.read_text(encoding="utf-8", errors="ignore")
    overlap_source = OVERLAP_SOURCE.read_text(encoding="utf-8", errors="ignore")
    overlap_points = None
    m = re.search(r"CheckForOverlaps\s+(\d+)\s+([0-9.eE+-]+)", overlap_source)
    if m:
        overlap_points = {"points": int(m.group(1)), "tolerance_cm": float(m.group(2))}
    return {
        "status": "STEP00_PASS",
        "model": MODEL,
        "source_bounds": rel(SOURCE_BOUNDS),
        "source_design_status": source_validation.get("status"),
        "source_design_problems": source_validation.get("problems", []),
        "simulation_geometry_setup": rel(SETUP),
        "proxy_status": proxy_validation.get("status"),
        "proxy_problems": proxy_validation.get("problems", []),
        "cosima_overlap": proxy_validation.get("checks", {}).get("cosima_overlap", {}),
        "cosima_overlap_gate": overlap_points,
        "cosima_log_has_geomvol1002": "GeomVol1002" in log_text,
        "cosima_log_has_overlap_detected": "Overlap is detected" in log_text,
        "beam_path_proxy": proxy_validation.get("checks", {}).get("beam_path_proxy", {}),
        "detector_core": proxy_validation.get("checks", {}).get("detector_core", {}),
        "geometry_extents": proxy_validation.get("geometry_extents", {}),
        "source_total_mass_kg": bounds.get("META", {}).get("total_mass_kg"),
        "active_csi_mass_kg": bounds.get("META", {}).get("active_csi_mass_kg"),
        "source_component_count": len(bounds.get("COMPONENTS", [])),
        "generated_megalib_volume_count": len(volumes),
        "step00_visuals": {
            "wrl": rel(WRL),
            "schematic_2d": rel(SCHEMATIC),
            "xz_overview": rel(XZ_OVERVIEW),
        },
        "accepted_scope": "Simulation-layer proxy closure. This is not CAD; x-axis circular parts and side holes remain proxy approximations.",
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    proxy_validation = run_geometry_builder()
    bounds = load_json(SOURCE_BOUNDS)
    source_validation = load_json(SOURCE_VALIDATION)
    if source_validation.get("status") != "DESIGN_PASS":
        raise RuntimeError("source geometry validation is not DESIGN_PASS")
    if proxy_validation.get("status") != "PROXY_PASS":
        raise RuntimeError("MEGAlib proxy validation is not PROXY_PASS")
    volumes = parse_geo_volumes(GEO)
    write_wrl(volumes, proxy_validation)
    write_2d_schematic(bounds)
    payload = closure_payload(bounds, source_validation, proxy_validation, volumes)
    CLOSURE.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "wrl": rel(WRL), "schematic": rel(SCHEMATIC)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
