#!/usr/bin/env python3
"""Build lightweight WRL scenes for front-optics irradiation checks.

The scenes are visualization artifacts only.  They reuse already-produced
front-optics Monte Carlo outputs:

- 511-keV science runs: optics-history plus focal-plane phase-space records.
- Instantaneous background runs: EXPACS far-field primary CSV plus focal-plane
  phase-space crossings.

No transport is rerun here.
"""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
OPTICSIM_ROOT = Path("/home/ubuntu/opticsim")

LAUE_OUT = ROOT / "Records/05_laue_current_mainline/front_optics_wrl_visualization_20260522"
CHANNEL_OUT = ROOT / "Records/06_channel_current_mainline/front_optics_wrl_visualization_20260522"

LAUE_RING_CONFIG = ROOT / "configs/opticsim/laue_511_mono_ge111_ge220_ge311_f17p5m_square.csv"
LAUE_SIGNAL_DIR = ROOT / "runs/opticsim_laue_511_mono_ge_hkl_f17p5_100k_20260521"
LAUE_PROMPT_DIR = ROOT / "runs/opticsim_allparticle_farfield_laue_511_f17p5_20k_20260521"
LAUE_PROMPT_PRIMARIES = Path("/tmp/codex_expacs_farfield_20k_20260521_primaries.csv")

CHANNEL_RING_CONFIG = OPTICSIM_ROOT / "data/channel/cam511_channel_rings.csv"
CHANNEL_SIGNAL_DIR = OPTICSIM_ROOT / "runs/channel_wallbywall_rebuild"
CHANNEL_PROMPT_DIR = ROOT / "runs/opticsim_allparticle_farfield_channel_wallbywall_100k_20260521"
CHANNEL_PROMPT_PRIMARIES = Path("/tmp/codex_expacs_farfield_channel100k_20260521_primaries.csv")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def f(row: dict[str, str], key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def i(row: dict[str, str], key: str, default: int = 0) -> int:
    try:
        return int(float(row.get(key, default)))
    except (TypeError, ValueError):
        return default


def evenly_spaced(items: list[Any], max_items: int) -> list[Any]:
    if len(items) <= max_items:
        return items
    if max_items <= 1:
        return items[:1]
    out = []
    last = len(items) - 1
    for k in range(max_items):
        out.append(items[round(k * last / (max_items - 1))])
    return out


def fmt(v: float) -> str:
    return f"{v:.7g}"


def material(name: str, color: tuple[float, float, float], transparency: float = 0.0) -> str:
    r, g, b = color
    return (
        f"DEF {name} Appearance {{ material Material {{ "
        f"diffuseColor {fmt(r)} {fmt(g)} {fmt(b)} "
        f"emissiveColor {fmt(0.25*r)} {fmt(0.25*g)} {fmt(0.25*b)} "
        f"transparency {fmt(transparency)} }} }}\n"
    )


def line_shape(name: str, polylines: list[list[tuple[float, float, float]]], color: tuple[float, float, float]) -> str:
    if not polylines:
        return ""
    coords: list[tuple[float, float, float]] = []
    indices: list[str] = []
    for line in polylines:
        if len(line) < 2:
            continue
        start = len(coords)
        coords.extend(line)
        indices.extend(str(start + j) for j in range(len(line)))
        indices.append("-1")
    if not coords:
        return ""
    coord_txt = ",\n".join(f"        {fmt(x)} {fmt(y)} {fmt(z)}" for x, y, z in coords)
    index_txt = " ".join(indices)
    r, g, b = color
    return f"""
DEF {name} Shape {{
  appearance Appearance {{ material Material {{ emissiveColor {fmt(r)} {fmt(g)} {fmt(b)} diffuseColor {fmt(r)} {fmt(g)} {fmt(b)} }} }}
  geometry IndexedLineSet {{
    coord Coordinate {{
      point [
{coord_txt}
      ]
    }}
    coordIndex [ {index_txt} ]
  }}
}}
"""


def circle_polyline(radius: float, z: float, n: int = 160) -> list[tuple[float, float, float]]:
    pts = []
    for k in range(n + 1):
        phi = 2.0 * math.pi * k / n
        pts.append((radius * math.cos(phi), radius * math.sin(phi), z))
    return pts


def focal_plane_lines(z: float, half_width: float) -> list[list[tuple[float, float, float]]]:
    return [
        [(-half_width, -half_width, z), (half_width, -half_width, z), (half_width, half_width, z), (-half_width, half_width, z), (-half_width, -half_width, z)],
        [(-half_width, 0.0, z), (half_width, 0.0, z)],
        [(0.0, -half_width, z), (0.0, half_width, z)],
    ]


def wrl_header(title: str, focal_z: float, extent_xy: float) -> str:
    return f"""#VRML V2.0 utf8
WorldInfo {{
  title "{title}"
  info [
    "Generated from existing opticsim/COSMOSRAY Monte Carlo outputs."
    "Units are mm."
    "This is a visualization scene, not a new transport result."
  ]
}}
NavigationInfo {{ type ["EXAMINE", "ANY"] speed 1000 }}
Background {{ skyColor [ 1 1 1 ] }}
Viewpoint {{ description "front oblique" position {fmt(0.35*extent_xy)} {fmt(-1.8*extent_xy)} {fmt(0.55*focal_z)} orientation 1 0 0 0.92 fieldOfView 0.65 }}
Viewpoint {{ description "side" position {fmt(0.0)} {fmt(-2.2*extent_xy)} {fmt(0.45*focal_z)} orientation 1 0 0 1.05 fieldOfView 0.55 }}

{material("MAT_LAUE0", (0.55, 0.55, 0.65), 0.35)}
{material("MAT_LAUE1", (0.50, 0.62, 0.75), 0.35)}
{material("MAT_LAUE2", (0.65, 0.55, 0.72), 0.35)}
{material("MAT_CHANNEL", (0.48, 0.55, 0.62), 0.30)}
"""


def laue_geometry() -> tuple[str, float]:
    rows = read_rows(LAUE_RING_CONFIG)
    chunks = []
    max_r = 0.0
    ring_lines: list[list[tuple[float, float, float]]] = []
    for row in rows:
        ring_id = i(row, "ring_id")
        radius = f(row, "radius_mm")
        tile_size = f(row, "tile_size_mm")
        thickness = f(row, "thickness_mm")
        n_tiles = i(row, "n_tiles")
        max_r = max(max_r, radius)
        ring_lines.append(circle_polyline(radius, 0.0))
        for k in range(n_tiles):
            phi = 2.0 * math.pi * k / n_tiles
            x = radius * math.cos(phi)
            y = radius * math.sin(phi)
            chunks.append(
                f"""Transform {{
  translation {fmt(x)} {fmt(y)} 0
  rotation 0 0 1 {fmt(phi)}
  children [
    Shape {{ appearance USE MAT_LAUE{ring_id % 3} geometry Box {{ size {fmt(tile_size)} {fmt(tile_size)} {fmt(thickness)} }} }}
  ]
}}
"""
            )
    chunks.append(line_shape("LAUE_RING_GUIDES", ring_lines, (0.20, 0.20, 0.25)))
    return "".join(chunks), max_r


def channel_geometry() -> tuple[str, float, float]:
    rows = read_rows(CHANNEL_RING_CONFIG)
    chunks = []
    max_r = 0.0
    max_z = 0.0
    ring_lines: list[list[tuple[float, float, float]]] = []
    for row in rows:
        radius = 10.0 * f(row, "radius_cm")
        length = 10.0 * f(row, "length_cm")
        width = 10.0 * f(row, "width_cm")
        thickness = f(row, "thickness_mm")
        n_tiles = i(row, "n_tiles")
        max_r = max(max_r, radius)
        max_z = max(max_z, length)
        ring_lines.extend([circle_polyline(radius, 0.0), circle_polyline(radius, length)])
        for k in range(n_tiles):
            phi = 2.0 * math.pi * k / n_tiles
            x = radius * math.cos(phi)
            y = radius * math.sin(phi)
            chunks.append(
                f"""Transform {{
  translation {fmt(x)} {fmt(y)} {fmt(0.5*length)}
  rotation 0 0 1 {fmt(phi)}
  children [
    Shape {{ appearance USE MAT_CHANNEL geometry Box {{ size {fmt(thickness)} {fmt(width)} {fmt(length)} }} }}
  ]
}}
"""
            )
    chunks.append(line_shape("CHANNEL_RING_GUIDES", ring_lines, (0.18, 0.18, 0.24)))
    return "".join(chunks), max_r, max_z


def write_wrl(path: Path, title: str, geometry: str, ray_groups: dict[str, tuple[list[list[tuple[float, float, float]]], tuple[float, float, float]]], focal_z: float, extent_xy: float) -> dict[str, Any]:
    axis = {
        "AXIS_X": ([[(0, 0, 0), (extent_xy, 0, 0)]], (0.85, 0.05, 0.05)),
        "AXIS_Y": ([[(0, 0, 0), (0, extent_xy, 0)]], (0.05, 0.55, 0.05)),
        "AXIS_Z": ([[(0, 0, 0), (0, 0, focal_z)]], (0.05, 0.05, 0.80)),
        "FOCAL_PLANE": (focal_plane_lines(focal_z, max(12.0, 0.07 * extent_xy)), (0.15, 0.15, 0.15)),
    }
    text = [wrl_header(title, focal_z, extent_xy), geometry]
    for name, (lines, color) in {**axis, **ray_groups}.items():
        text.append(line_shape(name, lines, color))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(text), encoding="utf-8")
    return {
        "path": str(path.relative_to(ROOT)),
        "bytes": path.stat().st_size,
        "ray_groups": {name: len(lines) for name, (lines, _color) in ray_groups.items()},
    }


def load_history_by_event(path: Path) -> dict[int, list[dict[str, str]]]:
    grouped: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in read_rows(path):
        grouped[i(row, "event_id")].append(row)
    return grouped


def build_laue_signal_lines(max_rays: int = 120) -> list[list[tuple[float, float, float]]]:
    phase = read_rows(LAUE_SIGNAL_DIR / "phase_space.csv")
    history = load_history_by_event(LAUE_SIGNAL_DIR / "optics_history.csv")
    candidates = [row for row in phase if i(row, "event_id") in history]
    lines = []
    for row in evenly_spaced(candidates, max_rays):
        event_id = i(row, "event_id")
        hist = history[event_id]
        hit = next((h for h in hist if h.get("stage") == "DIFFRACT"), hist[0])
        hx, hy, hz = f(hit, "x_mm"), f(hit, "y_mm"), f(hit, "z_mm")
        ux, uy, uz = f(hit, "ux_in"), f(hit, "uy_in"), f(hit, "uz_in", 1.0)
        start = (hx - ux * 2500.0, hy - uy * 2500.0, hz - uz * 2500.0)
        focal = (f(row, "x_mm"), f(row, "y_mm"), f(row, "z_mm"))
        lines.append([start, (hx, hy, hz), focal])
    return lines


def build_channel_signal_lines(max_rays: int = 90) -> list[list[tuple[float, float, float]]]:
    phase = read_rows(CHANNEL_SIGNAL_DIR / "phase_space.csv")
    history = load_history_by_event(CHANNEL_SIGNAL_DIR / "optics_history.csv")
    candidates = [row for row in phase if i(row, "event_id") in history]
    lines = []
    for row in evenly_spaced(candidates, max_rays):
        event_id = i(row, "event_id")
        hist = sorted(history[event_id], key=lambda h: i(h, "n_bounce"))
        bounce_pts = [(f(h, "x_mm"), f(h, "y_mm"), f(h, "z_mm")) for h in hist]
        bounce_pts = evenly_spaced(bounce_pts, 18)
        if not bounce_pts:
            continue
        first = bounce_pts[0]
        start = (first[0], first[1], -500.0)
        focal = (f(row, "x_mm"), f(row, "y_mm"), f(row, "z_mm"))
        lines.append([start, *bounce_pts, focal])
    return lines


def build_prompt_lines(phase_path: Path, primaries_path: Path, max_rays: int) -> dict[str, list[list[tuple[float, float, float]]]]:
    phase_rows = read_rows(phase_path)
    event_to_phase = {i(row, "event_id"): row for row in phase_rows}
    selected_ids = set(event_to_phase)
    matched: list[tuple[dict[str, str], dict[str, str]]] = []
    with primaries_path.open("r", encoding="utf-8-sig", newline="") as fh:
        for primary in csv.DictReader(fh):
            event_id = i(primary, "event_id")
            phase = event_to_phase.get(event_id)
            if phase is not None:
                matched.append((primary, phase))
                selected_ids.discard(event_id)
    matched = evenly_spaced(matched, max_rays)
    groups: dict[str, list[list[tuple[float, float, float]]]] = defaultdict(list)
    for primary, phase in matched:
        pname = primary.get("particle_name") or primary.get("source_particle_name") or "particle"
        start = (f(primary, "x_mm"), f(primary, "y_mm"), f(primary, "z_mm"))
        focal = (f(phase, "x_mm"), f(phase, "y_mm"), f(phase, "z_mm"))
        groups[pname].append([start, focal])
    return dict(groups)


def particle_color(name: str) -> tuple[float, float, float]:
    return {
        "gamma": (0.05, 0.25, 1.0),
        "neutron": (0.0, 0.70, 0.85),
        "proton": (0.95, 0.10, 0.05),
        "p": (0.95, 0.10, 0.05),
        "e-": (0.75, 0.05, 0.85),
        "e+": (0.90, 0.50, 0.05),
        "mu+": (0.15, 0.55, 0.15),
        "mu-": (0.10, 0.45, 0.10),
        "alpha": (0.85, 0.35, 0.05),
    }.get(name, (0.25, 0.25, 0.25))


def build_all() -> dict[str, Any]:
    laue_geo, laue_r = laue_geometry()
    channel_geo, channel_r, _channel_len = channel_geometry()
    manifest: dict[str, Any] = {
        "claim_level": "visualization_from_existing_front_optics_outputs",
        "units": "mm",
        "note": "WRL files show representative ray samples; they are not additional transport statistics.",
        "outputs": [],
    }

    manifest["outputs"].append(
        write_wrl(
            LAUE_OUT / "laue_signal_source_irradiation.wrl",
            "Laue f17p5 front optics irradiated by 511-keV signal source",
            laue_geo,
            {"SIGNAL_511": (build_laue_signal_lines(), (0.00, 0.65, 0.10))},
            17500.0,
            max(350.0, 1.35 * laue_r),
        )
    )

    laue_prompt = build_prompt_lines(
        LAUE_PROMPT_DIR / "phase_space.csv",
        LAUE_PROMPT_PRIMARIES,
        max_rays=180,
    )
    manifest["outputs"].append(
        write_wrl(
            LAUE_OUT / "laue_instant_background_irradiation.wrl",
            "Laue f17p5 front optics irradiated by EXPACS instantaneous background",
            laue_geo,
            {f"PROMPT_{name.replace('+', 'plus').replace('-', 'minus')}": (lines, particle_color(name)) for name, lines in laue_prompt.items()},
            17500.0,
            15000.0,
        )
    )

    manifest["outputs"].append(
        write_wrl(
            CHANNEL_OUT / "channel_signal_source_irradiation.wrl",
            "Channel wall-by-wall front optics irradiated by 511-keV signal source",
            channel_geo,
            {"SIGNAL_511": (build_channel_signal_lines(), (0.00, 0.65, 0.10))},
            12000.0,
            max(120.0, 1.8 * channel_r),
        )
    )

    channel_prompt = build_prompt_lines(
        CHANNEL_PROMPT_DIR / "phase_space.csv",
        CHANNEL_PROMPT_PRIMARIES,
        max_rays=180,
    )
    manifest["outputs"].append(
        write_wrl(
            CHANNEL_OUT / "channel_instant_background_irradiation.wrl",
            "Channel wall-by-wall front optics irradiated by EXPACS instantaneous background",
            channel_geo,
            {f"PROMPT_{name.replace('+', 'plus').replace('-', 'minus')}": (lines, particle_color(name)) for name, lines in channel_prompt.items()},
            12000.0,
            15000.0,
        )
    )

    for outdir, route, signal_dir, prompt_dir, primaries in [
        (LAUE_OUT, "Laue f17p5", LAUE_SIGNAL_DIR, LAUE_PROMPT_DIR, LAUE_PROMPT_PRIMARIES),
        (CHANNEL_OUT, "Channel wall-by-wall", CHANNEL_SIGNAL_DIR, CHANNEL_PROMPT_DIR, CHANNEL_PROMPT_PRIMARIES),
    ]:
        route_outputs = [o for o in manifest["outputs"] if str(outdir.relative_to(ROOT)) in o["path"]]
        readme = f"""# {route} Front-Optics WRL Visualization

This directory contains WRL visualization scenes for the front optics under:

- 511-keV signal-source irradiation.
- EXPACS/PARMA instantaneous-background irradiation.

These files are visualization products generated from existing simulation
outputs; no new transport statistics are claimed.

## Inputs

- signal optics output: `{signal_dir}`
- prompt optics output: `{prompt_dir}`
- prompt primary CSV: `{primaries}`

## Outputs

"""
        for item in route_outputs:
            readme += f"- `{Path(item['path']).name}`: {item['bytes']} bytes, ray groups {item['ray_groups']}\n"
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "README.md").write_text(readme, encoding="utf-8")

    (LAUE_OUT / "front_optics_wrl_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (CHANNEL_OUT / "front_optics_wrl_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def main() -> int:
    manifest = build_all()
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
