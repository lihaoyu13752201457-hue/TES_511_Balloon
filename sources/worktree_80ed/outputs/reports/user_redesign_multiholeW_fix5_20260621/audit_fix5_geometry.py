#!/usr/bin/env python3
"""Static geometry audits for the fix5 user redesign."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "outputs/reports/user_redesign_multiholeW_fix5_20260621"
GEOM_DIR = ROOT / "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy"
STEM = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
GEO = GEOM_DIR / f"{STEM}.geo"
DET = GEOM_DIR / f"{STEM}.det"

WINDOW_HALF_CM = 1.898
CSI_BOTTOM_TOP_Z_CM = -14.40


SIDE_CUTS = [
    ("Cu_50mK_StillLike_Can_side_wall_rectcut_window_band", 7.45, 7.65),
    ("Still_Shield_Al_side_window_side_wall_rectcut_window_band", 8.5, 8.8),
    ("Shield_4K_Al_side_window_side_wall_rectcut_window_band", 9.9, 10.2),
    ("Shield_60K_Al_side_window_side_wall_rectcut_window_band", 11.4, 11.7),
    ("Vacuum_Jacket_Al_266mmClass_side_port_side_wall_rectcut_window_band", 12.9, 13.4),
    ("CsI_Side_Segment_03_rectcut_window_band", 14.0, 18.0),
    ("CsI_Side_Segment_04_rectcut_window_band", 14.0, 18.0),
    ("ActiveShield_Flex_Kapton_detector_bay_rectcut_window_band", 18.17, 18.2),
    ("Outer_Al_Mechanical_Shell_detector_bay_side_wall_rectcut_window_band", 18.3, 19.1),
]


def volume_names(geo_text: str) -> set[str]:
    return set(re.findall(r"(?m)^Volume\s+(\S+)\s*$", geo_text))


def sensitive_refs(det_text: str) -> set[str]:
    return set(re.findall(r"(?m)\.SensitiveVolume\s+(\S+)\s*$", det_text))


def line_value(text: str, pattern: str) -> str:
    match = re.search(pattern, text, re.MULTILINE)
    if match is None:
        raise AssertionError(f"missing pattern: {pattern}")
    return match.group(1)


def pcon_bounds(text: str, name: str) -> tuple[float, float]:
    raw = line_value(text, rf"^{re.escape(name)}\.Shape\s+PCON\s+(.+)$")
    values = [float(item) for item in raw.split()]
    if int(values[2]) != 2:
        raise AssertionError(f"{name} is not a two-plane PCON")
    return values[3], values[6]


def position_z(text: str, name: str) -> float:
    raw = line_value(text, rf"^{re.escape(name)}\.Position\s+(.+)$")
    values = [float(item) for item in raw.split()]
    return values[2]


def audit_side_cut(geo_text: str, name: str, rin: float, rout: float) -> dict[str, object]:
    cut = f"{name}_RectWindowCutShape"
    orient = f"{name}_RectWindowCutOrientation"
    params = [float(item) for item in line_value(geo_text, rf"^{re.escape(cut)}\.Parameters\s+(.+)$").split()]
    center = [float(item) for item in line_value(geo_text, rf"^{re.escape(orient)}\.Position\s+(.+)$").split()]
    hx, hy, hz = params
    xcenter = center[0]
    cut_min = xcenter - hx
    cut_max = xcenter + hx
    min_outer_margin = float("inf")
    min_inner_margin = float("inf")
    samples = 401
    for idx in range(samples):
        y = -WINDOW_HALF_CM + 2.0 * WINDOW_HALF_CM * idx / (samples - 1)
        needed_min = -math.sqrt(max(0.0, rout * rout - y * y))
        needed_max = -math.sqrt(max(0.0, rin * rin - y * y))
        min_outer_margin = min(min_outer_margin, needed_min - cut_min)
        min_inner_margin = min(min_inner_margin, cut_max - needed_max)
    passed = (
        abs(hy - WINDOW_HALF_CM) < 1.0e-9
        and abs(hz - WINDOW_HALF_CM) < 1.0e-9
        and min_outer_margin >= -1.0e-8
        and min_inner_margin >= -1.0e-8
    )
    return {
        "name": name,
        "rin_cm": rin,
        "rout_cm": rout,
        "cut_x_min_cm": cut_min,
        "cut_x_max_cm": cut_max,
        "cut_y_half_cm": hy,
        "cut_z_half_cm": hz,
        "min_outer_margin_cm": min_outer_margin,
        "min_inner_margin_cm": min_inner_margin,
        "pass": passed,
    }


def audit_csi_seam(geo_text: str) -> dict[str, object]:
    bottom_top = position_z(geo_text, "CsI_Bottom_Quadrant_00") + pcon_bounds(geo_text, "CsI_Bottom_Quadrant_00")[1]
    names = [f"CsI_Side_Segment_{idx:02d}" for idx in (0, 1, 2, 5, 6, 7)]
    names += [f"CsI_Side_Segment_{idx:02d}_below_side_port" for idx in (3, 4)]
    rows = []
    for name in names:
        zmin, _zmax = pcon_bounds(geo_text, name)
        lower = position_z(geo_text, name) + zmin
        rows.append({"name": name, "global_lower_z_cm": lower, "gap_to_bottom_top_cm": lower - bottom_top})
    passed = abs(bottom_top - CSI_BOTTOM_TOP_Z_CM) < 1.0e-8 and all(
        abs(float(row["gap_to_bottom_top_cm"])) < 1.0e-8 for row in rows
    )
    return {
        "bottom_top_z_cm": bottom_top,
        "expected_bottom_top_z_cm": CSI_BOTTOM_TOP_Z_CM,
        "side_rows": rows,
        "pass": passed,
    }


def audit_magnetic_incident(geo_text: str, det_text: str) -> dict[str, object]:
    forbidden = [
        "MuMetal_MagShield_Outer_Incident_WindowCap_2mm",
        "Nb_MagShield_Inner_Incident_WindowCap_2mm",
    ]
    volumes = volume_names(geo_text)
    refs = sensitive_refs(det_text)
    return {
        "forbidden_incident_caps_absent_from_geo": all(name not in volumes for name in forbidden),
        "forbidden_incident_caps_absent_from_det": all(name not in refs for name in forbidden),
        "al_foil_volume_present": "Win_MagShield_Al_foil_side" in volumes,
        "al_foil_sensitive_ref_present": "Win_MagShield_Al_foil_side" in refs,
    }


def main() -> None:
    geo_text = GEO.read_text(encoding="utf-8")
    det_text = DET.read_text(encoding="utf-8")
    volumes = volume_names(geo_text)
    refs = sensitive_refs(det_text)
    missing = sorted(ref for ref in refs if ref not in volumes)

    side_rows = [audit_side_cut(geo_text, name, rin, rout) for name, rin, rout in SIDE_CUTS]
    magnetic = audit_magnetic_incident(geo_text, det_text)
    payload = {
        "geo": str(GEO.relative_to(ROOT)),
        "det": str(DET.relative_to(ROOT)),
        "det_reference_check": {
            "sensitive_reference_count": len(refs),
            "volume_count": len(volumes),
            "missing_count": len(missing),
            "missing": missing,
            "pass": len(missing) == 0,
        },
        "side_window_through_cut_audit": {
            "rows": side_rows,
            "pass": all(bool(row["pass"]) for row in side_rows),
        },
        "magnetic_incident_audit": {
            **magnetic,
            "pass": all(bool(value) for value in magnetic.values()),
        },
        "csi_bottom_side_seam_audit": audit_csi_seam(geo_text),
    }
    payload["overall_pass"] = (
        bool(payload["det_reference_check"]["pass"])
        and bool(payload["side_window_through_cut_audit"]["pass"])
        and bool(payload["magnetic_incident_audit"]["pass"])
        and bool(payload["csi_bottom_side_seam_audit"]["pass"])
    )

    (WORK / "geometry_det_reference_check.json").write_text(
        json.dumps(payload["det_reference_check"], indent=2) + "\n",
        encoding="utf-8",
    )
    (WORK / "side_window_material_path_audit_fix5.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"overall_pass": payload["overall_pass"], "missing_count": len(missing)}, indent=2))


if __name__ == "__main__":
    main()
