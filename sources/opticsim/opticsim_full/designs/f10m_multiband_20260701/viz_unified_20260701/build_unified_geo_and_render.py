#!/usr/bin/env python3
"""Build ONE unified .geo (six-ring optical TILES + support) and render it to a
single WRL + PNG, plus an overlap ledger proving the tiles do not overlap.

Why this exists: the Geant4 scene wrl has the tiles but no support; the mass
proxy wrl has the support but a smooth Ge annulus instead of tiles. This script
places BOTH in one common coordinate frame (optical axis = +x, lens plane at
x = 0, matching the project OF .geo convention) and tessellates the whole thing
with the project's own renderer, so a single file carries optics AND support.

Tiles use a SINGLE shared Ge template volume (`MB_Tile`) with one copy per tile,
so the same geometry can carry a single MEGAlib detector for a cosima MC run
(see ../mc_smoke_unified_20260701/). All tiles are identical BRIKs, so one
template is exact, not an approximation.

Overlap ledger: for each ring we emit a *guaranteed lower bound* on the
tangential separation between adjacent tiles (every point of a tile lies within
+-atan(hz/(r-hy)) of its azimuth, so if the angular pitch exceeds twice that,
the boxes cannot touch), plus the radial gaps between rings and the axial/radial
clearances to the support. Geant4's own checker (cosima CheckForOverlaps) is the
authoritative confirmation; this ledger is the analytic why.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DESIGN = HERE.parent
CONFIG = DESIGN / "ge111_balloon511_f10m_multiband_line_config.csv"
RENDERER = Path(
    "/home/ubuntu/TES_511_Balloon/add_mass/TES_511_Balloon_nearfield_mass_proxy_v2"
    "/tools/render_nearfield_mass_proxy.py"
)

GEO = HERE / "MultibandUnified_TilesAndSupport_f10m.geo"
INTRO = HERE / "unified_intro.geo"
SETUP = HERE / "multiband_unified.geo.setup"
GAPS = HERE / "overlap_ledger.json"

TILE_TEMPLATE = "MB_Tile"

# support clearances (cm), from OpticsMultiband_GeAndSupport_f10m.geo
G10_X_CENTER, G10_X_HALF = 0.70, 0.05
AL_MOUNT_INNER_R = 8.80


def load_rings() -> list[dict]:
    with CONFIG.open() as fh:
        return list(csv.DictReader(fh))


def write_intro() -> None:
    INTRO.write_text(
        "// Minimal host so the InstrumentFrame mother resolves.\n"
        "Volume WorldVolume\n"
        "WorldVolume.Material Vacuum\n"
        "WorldVolume.Shape BRIK 100 100 100\n"
        "WorldVolume.Mother 0\n\n"
        "Volume InstrumentFrame\n"
        "InstrumentFrame.Material Vacuum\n"
        "InstrumentFrame.Shape BRIK 60 60 60\n"
        "InstrumentFrame.Position 0 0 0\n"
        "InstrumentFrame.Mother WorldVolume\n"
    )


def write_setup() -> None:
    SETUP.write_text(
        "Name multiband_unified_viz\n"
        "Version 1\n"
        "Include unified_intro.geo\n"
        "Include MultibandUnified_TilesAndSupport_f10m.geo\n"
        "SurroundingSphere 60 0 0 0 60\n"
    )


def compute_gaps(rings: list[dict]) -> dict:
    """Analytic no-overlap ledger. All lengths in cm."""
    per_ring = []
    for ring in rings:
        r = float(ring["radius_mm"]) / 10.0
        n = int(ring["n_tiles"])
        hy = float(ring["tile_size_mm"]) / 2.0 / 10.0  # radial half
        hz = float(ring["tile_size_mm"]) / 2.0 / 10.0  # tangential half
        dphi = 2.0 * math.pi / n
        inner_r = r - hy
        a = math.atan(hz / inner_r)  # max azimuthal reach of a tile from its center
        tang_gap_lb_cm = inner_r * (dphi - 2.0 * a)  # guaranteed lower bound on tile separation
        per_ring.append(
            {
                "ring_id": int(ring["ring_id"]),
                "design_energy_keV": float(ring["design_energy_keV"]),
                "radius_cm": r,
                "n_tiles": n,
                "angular_pitch_rad": dphi,
                "tile_angular_halfwidth_rad": a,
                "tangential_gap_lower_bound_cm": tang_gap_lb_cm,
                "tangential_gap_lower_bound_um": tang_gap_lb_cm * 1.0e4,
            }
        )

    # radial gaps between consecutive rings (sorted outer -> inner)
    order = sorted(rings, key=lambda x: -float(x["radius_mm"]))
    radial = []
    for outer, inner in zip(order, order[1:]):
        ro = float(outer["radius_mm"]) / 10.0
        ri = float(inner["radius_mm"]) / 10.0
        hy = float(outer["tile_size_mm"]) / 2.0 / 10.0
        gap = (ro - hy) - (ri + hy)
        radial.append(
            {
                "outer_ring": int(outer["ring_id"]),
                "inner_ring": int(inner["ring_id"]),
                "radial_gap_cm": gap,
                "radial_gap_um": gap * 1.0e4,
            }
        )

    hy0 = float(rings[0]["tile_size_mm"]) / 2.0 / 10.0
    thick_half = float(rings[0]["thickness_mm"]) / 2.0 / 10.0
    max_r = max(float(x["radius_mm"]) for x in rings) / 10.0
    support = {
        "tile_to_G10_axial_clearance_cm": (G10_X_CENTER - G10_X_HALF) - thick_half,
        "tile_outer_edge_cm": max_r + hy0,
        "tile_to_Al_mount_radial_gap_cm": AL_MOUNT_INNER_R - (max_r + hy0),
    }

    min_tang = min(p["tangential_gap_lower_bound_cm"] for p in per_ring)
    min_radial = min(rr["radial_gap_cm"] for rr in radial)
    ledger = {
        "per_ring_tangential": per_ring,
        "radial_between_rings": radial,
        "tile_to_support": support,
        "min_tangential_gap_lower_bound_um": min_tang * 1.0e4,
        "min_radial_gap_um": min_radial * 1.0e4,
        "all_positive": (min_tang > 0.0 and min_radial > 0.0
                         and support["tile_to_G10_axial_clearance_cm"] > 0.0
                         and support["tile_to_Al_mount_radial_gap_cm"] > 0.0),
        "note": "Analytic lower bounds; Geant4 cosima CheckForOverlaps is the authoritative confirmation.",
    }
    GAPS.write_text(json.dumps(ledger, indent=2) + "\n")
    return ledger


def write_geo(rings: list[dict]) -> int:
    lines: list[str] = []
    lines.append("// f10m multiband UNIFIED: six-ring optical TILES + support, ONE frame.")
    lines.append("// Optical axis = +x, lens plane at x=0 (project OF convention).")
    lines.append("// SINGLE shared Ge tile template (all tiles identical) -> one MC detector.")
    lines.append("")

    hz = float(rings[0]["tile_size_mm"]) / 2.0 / 10.0
    thick_half = float(rings[0]["thickness_mm"]) / 2.0 / 10.0
    lines.append(f"Volume {TILE_TEMPLATE}")
    lines.append(f"{TILE_TEMPLATE}.Material GeProxy")
    lines.append(f"{TILE_TEMPLATE}.Visibility 1")
    # BRIK half-sizes: x=thickness (optical), y=radial, z=tangential
    lines.append(f"{TILE_TEMPLATE}.Shape BRIK {thick_half:.6f} {hz:.6f} {hz:.6f}")
    lines.append("")

    total_tiles = 0
    for ring in rings:
        rid = int(ring["ring_id"])
        radius_cm = float(ring["radius_mm"]) / 10.0
        n = int(ring["n_tiles"])
        xoff_cm = float(ring["z_offset_mm"]) / 10.0  # along optical axis
        lines.append(f"// ring {rid}: E={ring['design_energy_keV']} keV, r={radius_cm:.6f} cm, {n} tiles")
        for i in range(n):
            phi = 360.0 * i / n
            rad = math.radians(phi)
            y = radius_cm * math.cos(rad)
            z = radius_cm * math.sin(rad)
            cname = f"{TILE_TEMPLATE}_r{rid}_{i:03d}"
            lines.append(f"{TILE_TEMPLATE}.Copy {cname}")
            lines.append(f"{cname}.Position {xoff_cm:.6f} {y:.6f} {z:.6f}")
            lines.append(f"{cname}.Rotation {phi:.6f} 0 0")  # rotate tile tangent about optical axis
            lines.append(f"{cname}.Mother InstrumentFrame")
            total_tiles += 1
        lines.append("")

    # Support structure (identical to OpticsMultiband_GeAndSupport_f10m.geo).
    lines.append("// --- support structure (scaled from project OF1 model) ---")
    lines.append("Volume MB_LensCarrier_G10_Annulus")
    lines.append("MB_LensCarrier_G10_Annulus.Material G10")
    lines.append("MB_LensCarrier_G10_Annulus.Visibility 1")
    lines.append("MB_LensCarrier_G10_Annulus.Shape PCON 0 360 2 -0.050000 5.500000 8.800000 0.050000 5.500000 8.800000")
    lines.append("MB_LensCarrier_G10_Annulus.Rotation 0 90 0")
    lines.append("MB_LensCarrier_G10_Annulus.Position 0.70 0 0")
    lines.append("MB_LensCarrier_G10_Annulus.Mother InstrumentFrame")
    lines.append("")
    lines.append("Volume MB_LensOuterMount_Al_Annulus")
    lines.append("MB_LensOuterMount_Al_Annulus.Material Aluminium")
    lines.append("MB_LensOuterMount_Al_Annulus.Visibility 1")
    lines.append("MB_LensOuterMount_Al_Annulus.Shape PCON 0 360 2 -0.250000 8.800000 11.500000 0.250000 8.800000 11.500000")
    lines.append("MB_LensOuterMount_Al_Annulus.Rotation 0 90 0")
    lines.append("MB_LensOuterMount_Al_Annulus.Position 0 0 0")
    lines.append("MB_LensOuterMount_Al_Annulus.Mother InstrumentFrame")
    lines.append("")
    lines.append("Volume MB_LensMountBracket_Al")
    lines.append("MB_LensMountBracket_Al.Material Aluminium")
    lines.append("MB_LensMountBracket_Al.Visibility 1")
    lines.append("MB_LensMountBracket_Al.Shape BRIK 0.5 1.0 2.0")
    for tag, y, z in [("YP", 15.0, 0.0), ("YM", -15.0, 0.0), ("ZP", 0.0, 15.0), ("ZM", 0.0, -15.0)]:
        cname = f"MB_LensMountBracket_{tag}"
        lines.append(f"MB_LensMountBracket_Al.Copy {cname}")
        lines.append(f"{cname}.Position 0 {y} {z}")
        lines.append(f"{cname}.Mother InstrumentFrame")
    lines.append("")
    GEO.write_text("\n".join(lines))
    return total_tiles


def render() -> None:
    spec = importlib.util.spec_from_file_location("render_nearfield_mass_proxy", RENDERER)
    R = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = R
    spec.loader.exec_module(R)

    scene = {
        "setup": SETUP,
        "prefixes": None,
        "system": "optics",
        "scope": "full",
        "wrl": HERE / "multiband_unified_tiles_and_support.wrl",
        "png": HERE / "multiband_unified_tiles_and_support.png",
        "title": "f10m multiband: six-ring optical tiles + support (unified)",
        "viewpoint": 'Viewpoint { position 55 -80 55 orientation 0.74 0.21 0.64 1.04 description "multiband tiles + support" }',
        "note": "Single frame: real Ge tiles for all six rings plus G10/Al support. Optical axis = +x, lens plane at x=0.",
    }
    meshes = R.build_meshes(scene)
    if not meshes:
        raise SystemExit("no renderable meshes")
    R.write_wrl("multiband_unified", scene, meshes)
    R.write_png("multiband_unified", scene, meshes)
    tiles = sum(1 for m in meshes if m.name.startswith(TILE_TEMPLATE))
    support = [m.name for m in meshes if not m.name.startswith(TILE_TEMPLATE)]
    print(f"rendered {len(meshes)} volumes: {tiles} tiles + {len(support)} support ({', '.join(support)})")
    print(f"WRL {scene['wrl']}")
    print(f"PNG {scene['png']}")


def main() -> int:
    rings = load_rings()
    write_intro()
    write_setup()
    total = write_geo(rings)
    print(f"wrote {GEO.name}: {total} tiles across {len(rings)} rings + support")
    ledger = compute_gaps(rings)
    print(f"wrote {GAPS.name}: all_positive={ledger['all_positive']} "
          f"min_tangential>={ledger['min_tangential_gap_lower_bound_um']:.1f} um "
          f"min_radial={ledger['min_radial_gap_um']:.1f} um")
    render()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
