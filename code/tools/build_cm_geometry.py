#!/usr/bin/env python3
"""Build the Cosima-safe cm version of the NEW_GEO_RE ADR geometry.

The raw ADR v4c files are explicitly authored in millimetres, while MEGAlib /
Cosima interprets bare geometry/source lengths as centimetres.  This tool keeps
the raw files as provenance and writes a globally scaled cm authority for
transport.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "outputs" / "geometry" / "raw_mm"
RAW_GEO = RAW_DIR / "TibetTES_ADR_v4c_mkflange.geo"
RAW_DET = RAW_DIR / "TibetTES_ADR_v4c_mkflange.det"
RAW_BOUNDS = RAW_DIR / "bounds.json"
OUT = ROOT / "outputs" / "geometry" / "XZTES_ADR_v4c_mkflange_cm"
SCALE = 0.1

FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?"


def fmt(x: float) -> str:
    return f"{x:.9g}"


def scale_geo_line(line: str) -> str:
    stripped = line.strip()
    if ".Shape BRIK " in stripped:
        prefix, rest = line.split("BRIK", 1)
        vals = [float(x) for x in rest.split()]
        if len(vals) == 3:
            return f"{prefix}BRIK {' '.join(fmt(v * SCALE) for v in vals)}\n"
    if ".Shape PCON " in stripped:
        prefix, rest = line.split("PCON", 1)
        vals = rest.split()
        if len(vals) >= 3:
            phi0, dphi, nplanes = vals[:3]
            nums = [float(x) for x in vals[3:]]
            if len(nums) % 3 == 0:
                scaled = []
                for i, v in enumerate(nums):
                    # PCON triplets are z, rmin, rmax.  Angles and plane count are not lengths.
                    scaled.append(fmt(v * SCALE))
                return f"{prefix}PCON {phi0} {dphi} {nplanes} {' '.join(scaled)}\n"
    m = re.match(rf"^(?P<prefix>\S+\.Position\s+)(?P<x>{FLOAT})\s+(?P<y>{FLOAT})\s+(?P<z>{FLOAT})(?P<tail>\s*)$", stripped)
    if m:
        return (
            f"{m.group('prefix')}"
            f"{fmt(float(m.group('x')) * SCALE)} "
            f"{fmt(float(m.group('y')) * SCALE)} "
            f"{fmt(float(m.group('z')) * SCALE)}"
            f"{m.group('tail')}\n"
        )
    return line


def scale_det_line(line: str) -> str:
    stripped = line.strip()
    for token in (".StructuralPitch ", ".StructuralOffset "):
        if token in stripped:
            prefix, rest = line.split(token, 1)
            vals = [float(x) for x in rest.split()]
            if len(vals) == 3:
                return f"{prefix}{token}{' '.join(fmt(v * SCALE) for v in vals)}\n"
    return line


LENGTH_KEYS_EXACT = {
    "TES_LAYER_PITCH",
    "r",
    "h",
    "zc",
    "r_in",
    "r_out",
    "wall",
    "z_in_bot",
    "z_in_top",
    "z_out_bot",
    "z_out_top",
    "top_extra",
    "z_extra",
    "hole",
    "thick",
    "r_max",
    "hz",
    "z_center",
    "z_bot",
    "z_top",
    "pitch",
    "web",
}


def is_length_key(key: str) -> bool:
    if key in LENGTH_KEYS_EXACT:
        return True
    if key.endswith("_mm"):
        return True
    if key.startswith("z_") or key.startswith("r_"):
        return True
    return False


def scaled_key(key: str) -> str:
    if key.endswith("_mm"):
        return key[:-3] + "_cm"
    return key


def scale_bounds(obj: Any, key: str | None = None) -> Any:
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if k == "UNITS":
                out[k] = "cm"
            elif k == "VERSION":
                out[k] = str(v) + "_cm"
            else:
                out[scaled_key(k)] = scale_bounds(v, k)
        return out
    if isinstance(obj, list):
        return [scale_bounds(v, key) for v in obj]
    if isinstance(obj, bool) or obj is None:
        return obj
    if isinstance(obj, (int, float)) and key is not None and is_length_key(key):
        return obj * SCALE
    return obj


def write_materials() -> None:
    text = """# Custom materials for NEW_GEO_RE ADR v4c cm geometry
Include $(MEGALIB)/resource/examples/geomega/materials/Materials.geo

Material Nb
Nb.Density 8.57
Nb.Component Nb 1

Material W
W.Density 19.30
W.Component W 1

Material Ta
Ta.Density 16.69
Ta.Component Ta 1

Material Be
Be.Density 1.85
Be.Component Be 1

Material Mylar
Mylar.Density 1.39
Mylar.Component C 10
Mylar.Component H 8
Mylar.Component O 4

# CeBr3 active-shield material from the raw generator note: density 5.1 g/cm3.
Material CeBr3
CeBr3.Density 5.1
CeBr3.Component Ce 1
CeBr3.Component Br 3

"""
    (OUT / "Materials_TibetTES.geo").write_text(text, encoding="utf-8")


def write_intro() -> None:
    text = """Name MassmodelTibetTES_ADR_v4c_new_geo_re_cm
Version 1

Include Materials_TibetTES.geo
AbsorptionFileDirectory crossections

Volume WorldVolume
WorldVolume.Visibility 0
WorldVolume.Material Vacuum
WorldVolume.Shape BRIK 1000 1000 1000
WorldVolume.Mother 0
"""
    (OUT / "Intro_TibetTES.geo").write_text(text, encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    geo_out = OUT / "TibetTES_ADR_v4c_mkflange_cm.geo"
    det_out = OUT / "TibetTES_ADR_v4c_mkflange_cm.det"
    bounds_out = OUT / "bounds.json"
    raw_bounds_out = OUT / "bounds_raw_mm.json"

    geo_out.write_text("".join(scale_geo_line(line) for line in RAW_GEO.read_text(encoding="utf-8").splitlines(keepends=True)), encoding="utf-8")
    det_out.write_text("".join(scale_det_line(line) for line in RAW_DET.read_text(encoding="utf-8").splitlines(keepends=True)), encoding="utf-8")

    raw_bounds = json.loads(RAW_BOUNDS.read_text(encoding="utf-8"))
    scaled = scale_bounds(raw_bounds)
    scaled.setdefault("META", {})
    scaled["META"].update(
        {
            "length_unit": "cm",
            "source_design_unit": "mm",
            "length_scale_to_cm": SCALE,
            "tes_pixel_thickness_cm": 0.3,
            "science_beam_z_cm": 16.051,
            "science_beam_radius_cm": 1.8,
            "source_placement_basis": "1 micron above scaled W-collimator top; beam radius matches TES active footprint",
            "material_policy": "CeBr3 stoichiometric material; A4K/Cryoperm omitted in Step01 simplified background prototype",
        }
    )
    raw_bounds_out.write_text(json.dumps(raw_bounds, indent=2, ensure_ascii=False), encoding="utf-8")
    bounds_out.write_text(json.dumps(scaled, indent=2, ensure_ascii=False), encoding="utf-8")

    write_materials()
    write_intro()
    setup = """Name TibetTES_ADR_v4c_mkflange_cm
Version 1
Include TibetTES_ADR_v4c_mkflange_cm.geo
Include TibetTES_ADR_v4c_mkflange_cm.det
SurroundingSphere 35 0 0 -3 35
"""
    (OUT / "TibetTES_ADR_v4c_mkflange_cm.geo.setup").write_text(setup, encoding="utf-8")

    print(json.dumps({
        "status": "PASS",
        "outdir": str(OUT),
        "scale": SCALE,
        "tes_pixel_thickness_cm": 0.3,
        "science_beam_z_cm": 16.051,
        "science_beam_radius_cm": 1.8,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
