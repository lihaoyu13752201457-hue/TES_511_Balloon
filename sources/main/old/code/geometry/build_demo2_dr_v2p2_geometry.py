#!/usr/bin/env python3
"""Build DEMO2_DR_v2p2 Cu64-fix geometry for TES_511_Balloon.

This generator converts the design-level DR_v2p1 reference package in
``geo_refer/`` into MEGAlib/Cosima-ready geometry files.  The v2p2 change
requested for the migration is:

* remove the innermost Cu TES sample box as a Cu-64 background source;
* move the nearest magnetic-shield material/function into the former sample-box
  envelope as ``TES_SampleBox_Cryoperm``;
* add a bottom-center hole and a short Cu thermal finger to the 50 mK/MXC plate.

All lengths are cm.
"""

from __future__ import annotations

import csv
import json
import math
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Patch, Rectangle


ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "geo_refer"
REF_BOUNDS = REF / "DEMO2_DR_v2p1_bounds.json"
REF_MASS = REF / "DEMO2_DR_v2p1_mass_budget.csv"

GEOM_NAME = "DEMO2_DR_v2p2_cu64fix"
OUT = ROOT / "outputs" / "geometry" / GEOM_NAME
STEP = ROOT / "stepwise_maintenance" / "step00_geometry"
STEP_OUT = STEP / "outputs"

DENSITY_G_CM3 = {
    "Vacuum": 0.0,
    "Copper": 8.96,
    "Aluminium": 2.70,
    "Silicon": 2.329,
    "Ta": 16.69,
    "Nb": 8.57,
    "W": 19.30,
    "Be": 1.85,
    "CsI": 4.51,
    "Cryoperm": 8.70,
    "LowCarbonSteel": 7.87,
    "StainlessSteel": 8.00,
    "G10": 1.85,
    "Kapton": 1.42,
    "CuNi": 8.90,
    "SilverSinterProxy": 5.00,
    "CharcoalTrapProxy": 1.20,
    "NbTiCableProxy": 6.50,
    "Germanium": 5.323,
}

COLORS = {
    "CsI": "#5DA5DA",
    "Aluminium": "#B7B7B7",
    "Copper": "#B87333",
    "Cryoperm": "#4F63A8",
    "Nb": "#40BFC8",
    "Ta": "#D4504C",
    "W": "#2D2D2D",
    "Silicon": "#666666",
    "Be": "#D4C46A",
    "G10": "#6BAF5F",
    "Kapton": "#C8782A",
    "CuNi": "#158EA6",
    "SilverSinterProxy": "#D1D5DB",
    "CharcoalTrapProxy": "#111827",
    "NbTiCableProxy": "#7C3AED",
}


def fmt(x: float | int) -> str:
    x = float(x)
    if abs(x) < 5.0e-13:
        x = 0.0
    return f"{x:.9g}"


def pcon(planes: list[tuple[float, float, float]], phi0: float = 0.0, dphi: float = 360.0) -> str:
    toks = ["PCON", fmt(phi0), fmt(dphi), str(len(planes))]
    for z, r0, r1 in planes:
        toks.extend([fmt(z), fmt(r0), fmt(r1)])
    return " ".join(toks)


def vol(name: str, material: str, shape: str, vis: int = 1) -> str:
    return (
        f"// Volume {name}; material={material}\n"
        f"Volume {name}\n"
        f"{name}.Material {material}\n"
        f"{name}.Visibility {vis}\n"
        f"{name}.Shape {shape}\n\n"
    )


def place(name: str, x: float, y: float, z: float, mother: str = "WorldVolume", vis: int | None = None) -> str:
    text = f"{name}.Position {fmt(x)} {fmt(y)} {fmt(z)}\n{name}.Mother {mother}\n"
    if vis is not None:
        text += f"{name}.Visibility {vis}\n"
    return text + "\n"


def cylinder_shape(radius: float, halfz: float) -> str:
    return pcon([(-halfz, 0.0, radius), (halfz, 0.0, radius)])


def cylinder(name: str, material: str, radius: float, halfz: float, vis: int = 1) -> str:
    return vol(name, material, cylinder_shape(radius, halfz), vis)


def brik(name: str, material: str, hx: float, hy: float, hz: float, vis: int = 1) -> str:
    return vol(name, material, f"BRIK {fmt(hx)} {fmt(hy)} {fmt(hz)}", vis)


def shell_shape(
    r_in: float,
    r_out: float,
    z_in_bot: float,
    z_in_top: float,
    z_out_bot: float,
    z_out_top: float,
    top_hole: float,
    bottom_hole: float = 0.0,
) -> str:
    return pcon(
        [
            (z_out_bot, bottom_hole, r_out),
            (z_in_bot, bottom_hole, r_out),
            (z_in_bot, r_in, r_out),
            (z_in_top, r_in, r_out),
            (z_in_top, top_hole, r_out),
            (z_out_top, top_hole, r_out),
        ]
    )


def open_bottom_can_shape(r_in: float, r_out: float, z_in_bot: float, z_in_top: float, z_out_top: float, hole: float) -> str:
    return pcon([(z_in_bot, r_in, r_out), (z_in_top, r_in, r_out), (z_in_top, hole, r_out), (z_out_top, hole, r_out)])


def annulus_shape(r_in: float, r_out: float, halfz: float, phi_fraction: float = 1.0) -> str:
    return pcon([(-halfz, r_in, r_out), (halfz, r_in, r_out)], 0.0, 360.0 * phi_fraction)


def cyl_volume(radius: float, h: float) -> float:
    return math.pi * radius * radius * h


def ann_volume(r_in: float, r_out: float, h: float, phi_fraction: float = 1.0) -> float:
    return phi_fraction * math.pi * (r_out * r_out - r_in * r_in) * h


def box_volume(hx: float, hy: float, hz: float) -> float:
    return 8.0 * hx * hy * hz


def shell_volume(
    r_in: float,
    r_out: float,
    z_in_bot: float,
    z_in_top: float,
    z_out_bot: float,
    z_out_top: float,
    top_hole: float,
    bottom_hole: float = 0.0,
) -> float:
    bottom = ann_volume(bottom_hole, r_out, z_in_bot - z_out_bot)
    side = ann_volume(r_in, r_out, z_in_top - z_in_bot)
    top = ann_volume(top_hole, r_out, z_out_top - z_in_top)
    return bottom + side + top


def open_bottom_can_volume(r_in: float, r_out: float, z_in_bot: float, z_in_top: float, z_out_top: float, hole: float) -> float:
    side = ann_volume(r_in, r_out, z_in_top - z_in_bot)
    top = ann_volume(hole, r_out, z_out_top - z_in_top)
    return side + top


def mass(material: str, volume_cm3: float) -> float:
    return DENSITY_G_CM3[material] * volume_cm3 / 1000.0


def mass_row(category: str, unit: str, material: str, volume_cm3: float, notes: str) -> dict[str, Any]:
    return {
        "category": category,
        "unit": unit,
        "material": material,
        "density_g_cm3": DENSITY_G_CM3[material],
        "volume_cm3": volume_cm3,
        "mass_kg": mass(material, volume_cm3),
        "notes": notes,
    }


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        for key in ("density_g_cm3", "volume_cm3", "mass_kg"):
            if key in row:
                row[key] = float(row[key])
    return rows


def write_csv_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = ["category", "unit", "material", "density_g_cm3", "volume_cm3", "mass_kg", "notes"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def adapt_bounds(base: dict[str, Any]) -> dict[str, Any]:
    b = json.loads(json.dumps(base))
    original = b["SAMPLE_BOX"]
    thermal_finger_radius = 0.40
    b["VERSION"] = "DEMO2_DR_v2p2_cu64fix"
    b["DESIGN_NOTE"] = (
        "DEMO2 DR_v2p2 Cu64-fix: removes the innermost Cu TES sample box, "
        "moves the nearest Cryoperm magnetic shield function/material into the former sample-box envelope, "
        "and adds a short Cu thermal finger through a bottom-center hole to the 50 mK/MXC plate."
    )
    b["SAMPLE_BOX"] = {
        "name": "TES_SampleBox_Cryoperm",
        "mat": "Cryoperm",
        "r_in": original["r_in"],
        "r_out": original["r_out"],
        "z_out_bot": original["z_out_bot"],
        "z_in_bot": original["z_in_bot"],
        "z_in_top": original["z_in_top"],
        "z_out_top": original["z_out_top"],
        "hole": original["hole"],
        "bottom_hole": thermal_finger_radius,
        "moved_from": "Cryoperm_Inner_Mag_Shield",
        "replaces": "TES_SampleBox_Cu",
        "basis": (
            "Cu64-fix sample box: Cryoperm material/function from the nearest magnetic-shield box, "
            "placed in the former TES_SampleBox_Cu envelope. Bottom has a center hole for a Cu thermal finger."
        ),
        "window": original.get("window"),
    }
    b["THERMAL_FINGER"] = {
        "name": "SampleBox_Cu_ThermalFinger_50mK",
        "mat": "Copper",
        "r": thermal_finger_radius,
        "z0": original["z_out_bot"],
        "z1": original["z_in_bot"],
        "touches": ["ColdPlate_MXC_50mK_Retained", "TES_SampleBox_Cryoperm"],
        "basis": "Short Cu thermal finger through the new sample-box bottom hole; keeps a thermal path to the 50 mK/MXC plate while removing the large Cu box.",
    }
    if "WINDOWS" in b and original.get("window"):
        # Keep the low-Z top foil at the same aperture, but make the connection
        # explicit in the sample-box notes.
        for win in b["WINDOWS"]:
            if win.get("name") == original["window"]["name"]:
                win["basis"] = (
                    "Retained thin Al top foil for the v2p2 Cryoperm sample-box aperture; "
                    "not part of the removed Cu sample box mass."
                )

    # The nearest magnetic-shield proxy has been moved into SAMPLE_BOX.  Do not
    # instantiate a duplicate Cryoperm shell at the old radius.
    passive = []
    for rec in b.get("PASSIVE_PROXIES", []):
        if rec.get("name") == "Cryoperm_Inner_Mag_Shield":
            continue
        passive.append(rec)
    b["PASSIVE_PROXIES"] = passive

    meta = dict(b.get("META", {}))
    authority = list(meta.get("geometry_authority_lists", []))
    if "THERMAL_FINGER" not in authority:
        insert_at = authority.index("SAMPLE_BOX") + 1 if "SAMPLE_BOX" in authority else len(authority)
        authority.insert(insert_at, "THERMAL_FINGER")
    meta.update(
        {
            "claim_level": "DEMO2_DR_V2P2_CU64FIX_SIM_GEOMETRY_READY",
            "sample_box_policy": "TES_SampleBox_Cu removed; TES_SampleBox_Cryoperm occupies the former sample-box envelope with bottom_hole=0.40 cm.",
            "cu64_fix": {
                "removed": ["TES_SampleBox_Cu"],
                "moved_material_function": "Cryoperm_Inner_Mag_Shield -> TES_SampleBox_Cryoperm",
                "added": ["SampleBox_Cu_ThermalFinger_50mK"],
                "thermal_finger_radius_cm": thermal_finger_radius,
            },
            "geometry_authority_lists": authority,
        }
    )
    b["META"] = meta
    return b


def group_mass(rows: list[dict[str, Any]]) -> dict[str, float]:
    out: dict[str, float] = {}
    for row in rows:
        out[row["category"]] = out.get(row["category"], 0.0) + float(row["mass_kg"])
    return dict(sorted(out.items()))


def build_mass_rows(bounds: dict[str, Any], ref_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    skip = {"TES_SampleBox_Cu", "Cryoperm_Inner_Mag_Shield"}
    rows = [dict(r) for r in ref_rows if r["unit"] not in skip]
    s = bounds["SAMPLE_BOX"]
    rows.append(
        mass_row(
            "sample_box",
            s["name"],
            s["mat"],
            shell_volume(s["r_in"], s["r_out"], s["z_in_bot"], s["z_in_top"], s["z_out_bot"], s["z_out_top"], s["hole"], s["bottom_hole"]),
            s["basis"],
        )
    )
    tf = bounds["THERMAL_FINGER"]
    rows.append(
        mass_row(
            "thermal_link",
            tf["name"],
            tf["mat"],
            cyl_volume(tf["r"], tf["z1"] - tf["z0"]),
            tf["basis"],
        )
    )
    return rows


def write_materials() -> None:
    text = """# Custom materials for DEMO2_DR_v2p2_cu64fix.
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

# Standard MEGAlib already defines CsI; use that material name in volumes.

Material Cryoperm
Cryoperm.Density 8.70
Cryoperm.Component Ni 4
Cryoperm.Component Fe 1

Material LowCarbonSteel
LowCarbonSteel.Density 7.87
LowCarbonSteel.Component Fe 99
LowCarbonSteel.Component C 1

Material StainlessSteel
StainlessSteel.Density 8.00
StainlessSteel.Component Fe 70
StainlessSteel.Component Cr 18
StainlessSteel.Component Ni 10
StainlessSteel.Component Mn 2

Material G10
G10.Density 1.85
G10.Component Si 1
G10.Component O 2
G10.Component C 3
G10.Component H 3

Material Kapton
Kapton.Density 1.42
Kapton.Component C 22
Kapton.Component H 10
Kapton.Component N 2
Kapton.Component O 5

Material CuNi
CuNi.Density 8.90
CuNi.Component Cu 7
CuNi.Component Ni 3

Material SilverSinterProxy
SilverSinterProxy.Density 5.00
SilverSinterProxy.Component Ag 1

Material CharcoalTrapProxy
CharcoalTrapProxy.Density 1.20
CharcoalTrapProxy.Component C 1

Material NbTiCableProxy
NbTiCableProxy.Density 6.50
NbTiCableProxy.Component Nb 1
NbTiCableProxy.Component Ti 1

"""
    (OUT / "Materials_DEMO2_DR_v2p2.geo").write_text(text, encoding="utf-8")


def write_intro() -> None:
    text = """Name Massmodel_DEMO2_DR_v2p2_cu64fix
Version 1

Include Materials_DEMO2_DR_v2p2.geo
AbsorptionFileDirectory crossections

Volume WorldVolume
WorldVolume.Visibility 0
WorldVolume.Material Vacuum
WorldVolume.Shape BRIK 1000 1000 1000
WorldVolume.Mother 0
"""
    (OUT / "Intro_DEMO2_DR_v2p2.geo").write_text(text, encoding="utf-8")


def pixel_positions(radius: float = 1.8, pitch: float = 0.155) -> list[tuple[float, float]]:
    positions: list[tuple[float, float]] = []
    n = int(math.ceil(radius / pitch)) + 1
    for ix in range(-n, n + 1):
        for iy in range(-n, n + 1):
            x = ix * pitch
            y = iy * pitch
            if x * x + y * y <= radius * radius:
                positions.append((x, y))
    # Keep exactly the legacy 376-pixel footprint by sorting nearest to center
    # if the round grid produces extras on boundary changes.
    positions.sort(key=lambda p: (p[0] * p[0] + p[1] * p[1], p[0], p[1]))
    if len(positions) < 376:
        raise RuntimeError(f"TES footprint produced only {len(positions)} pixels")
    return sorted(positions[:376])


def add_tes_stack(geo: list[str], bounds: dict[str, Any]) -> None:
    pix = pixel_positions()
    for i, layer in enumerate(bounds["TES_LAYERS"]):
        sub = bounds["SUBSTRATES"][i]
        geo.append(cylinder(sub["name"], "Silicon", sub["r_max"], sub["hz"]))
        geo.append(vol(f"TES_Pixel_L{i}", "Ta", "BRIK 0.075 0.075 0.15"))
        geo.append(vol(f"TES_L{i}", "Vacuum", "BRIK 2.4 2.4 0.15", vis=0))
        geo.append(place(sub["name"], 0, 0, sub["z_center"]))
        geo.append(place(f"TES_L{i}", 0, 0, layer["z_center"], vis=0))
        for j, (x, y) in enumerate(pix):
            cname = f"TP_L{i}_{j:05d}"
            geo.append(f"TES_Pixel_L{i}.Copy {cname}\n")
            geo.append(place(cname, x, y, 0, f"TES_L{i}", vis=0))


def add_shell_volume(geo: list[str], rec: dict[str, Any], *, bottom_hole: float = 0.0) -> None:
    geo.append(
        vol(
            rec["name"],
            rec["mat"],
            shell_shape(
                rec["r_in"],
                rec["r_out"],
                rec["z_in_bot"],
                rec["z_in_top"],
                rec["z_out_bot"],
                rec["z_out_top"],
                rec["hole"],
                bottom_hole=bottom_hole,
            ),
        )
    )
    geo.append(place(rec["name"], 0, 0, 0))


def add_window(geo: list[str], rec: dict[str, Any]) -> None:
    mat = rec.get("mat") or rec.get("material")
    zc = rec.get("zc", rec.get("z_center"))
    r = rec.get("r", rec.get("r_max"))
    thick = rec["thick"]
    geo.append(cylinder(rec["name"], mat, r, thick / 2.0))
    geo.append(place(rec["name"], 0, 0, zc))


def add_proxy(geo: list[str], rec: dict[str, Any]) -> None:
    name = rec["name"]
    material = rec.get("mat") or rec.get("material")
    if rec.get("shape") == "cylinder":
        radius = rec["params"]["r"]
        geo.append(cylinder(name, material, radius, (rec["z1"] - rec["z0"]) / 2.0))
        geo.append(place(name, rec.get("x", 0.0), rec.get("y", 0.0), 0.5 * (rec["z0"] + rec["z1"])))
    elif rec.get("shape") == "annulus":
        p = rec["params"]
        geo.append(vol(name, material, annulus_shape(p["r_in"], p["r_out"], (rec["z1"] - rec["z0"]) / 2.0, p.get("phi_fraction", 1.0))))
        geo.append(place(name, rec.get("x", 0.0), rec.get("y", 0.0), 0.5 * (rec["z0"] + rec["z1"])))
    elif rec.get("shape") == "box":
        p = rec["params"]
        geo.append(brik(name, material, p["hx"], p["hy"], p["hz"]))
        geo.append(place(name, rec.get("x", 0.0), rec.get("y", 0.0), 0.5 * (rec["z0"] + rec["z1"])))
    elif all(k in rec for k in ("hx", "hy", "hz", "x", "y", "z")):
        geo.append(brik(name, material, rec["hx"], rec["hy"], rec["hz"]))
        geo.append(place(name, rec["x"], rec["y"], rec["z"]))
    elif "r_in" in rec and "r_out" in rec and "z0" in rec and "z1" in rec:
        geo.append(vol(name, material, annulus_shape(rec["r_in"], rec["r_out"], (rec["z1"] - rec["z0"]) / 2.0)))
        geo.append(place(name, 0, 0, 0.5 * (rec["z0"] + rec["z1"])))
    else:
        raise ValueError(f"Unsupported proxy shape: {name}")


def add_active_segments(geo: list[str], bounds: dict[str, Any]) -> None:
    active = bounds["ACTIVE_SHIELD"]
    for seg in bounds["ACTIVE_SHIELD_SEGMENTS"]:
        name = seg["name"]
        if seg["part"] == "side":
            shape = pcon([(seg["z0"], seg["r_in"], seg["r_out"]), (seg["z1"], seg["r_in"], seg["r_out"])], seg["phi0_deg"], seg["dphi_deg"])
        elif seg["part"] == "bottom":
            shape = pcon([(seg["z0"], 0.0, seg["r_out"]), (seg["z1"], 0.0, seg["r_out"])], seg["phi0_deg"], seg["dphi_deg"])
        elif seg["part"] == "top":
            shape = pcon([(seg["z0"], active["hole"], seg["r_out"]), (seg["z1"], active["hole"], seg["r_out"])], seg["phi0_deg"], seg["dphi_deg"])
        else:
            raise ValueError(seg)
        geo.append(vol(name, active["mat"], shape))
        geo.append(place(name, 0, 0, 0))


def build_geo(bounds: dict[str, Any]) -> str:
    geo: list[str] = ["Include Intro_DEMO2_DR_v2p2.geo\n\n"]
    for p in bounds["COLD_PLATES"]:
        geo.append(cylinder(p["name"], p["mat"], p["r"], p["h"] / 2.0))
        geo.append(place(p["name"], 0, 0, p["zc"]))
    add_tes_stack(geo, bounds)
    add_shell_volume(geo, bounds["SAMPLE_BOX"], bottom_hole=bounds["SAMPLE_BOX"]["bottom_hole"])
    tf = bounds["THERMAL_FINGER"]
    geo.append(cylinder(tf["name"], tf["mat"], tf["r"], (tf["z1"] - tf["z0"]) / 2.0))
    geo.append(place(tf["name"], 0, 0, 0.5 * (tf["z0"] + tf["z1"])))
    if bounds["SAMPLE_BOX"].get("window"):
        add_window(geo, bounds["SAMPLE_BOX"]["window"])
    for can in bounds["OPEN_BOTTOM_CANS"]:
        geo.append(vol(can["name"], can["mat"], open_bottom_can_shape(can["r_in"], can["r_out"], can["z_in_bot"], can["z_in_top"], can["z_out_top"], can["hole"])))
        geo.append(place(can["name"], 0, 0, 0))
    for shell in bounds["CRYOSTAT_SHELLS"]:
        add_shell_volume(geo, shell)
    for win in bounds["STAGE_WINDOWS"]:
        add_window(geo, win)
    for rec in bounds["PASSIVE_PROXIES"]:
        add_proxy(geo, rec)
    add_active_segments(geo, bounds)
    add_shell_volume(geo, bounds["OUTER_MECHANICAL_SHELL"])
    for win in bounds["WINDOWS"]:
        if win["name"] == bounds["SAMPLE_BOX"].get("window", {}).get("name"):
            continue
        add_window(geo, win)
    col = bounds["COLLIMATOR"]
    geo.append(vol(col["name"], "W", annulus_shape(col["r_inner"], col["r_max"], col["hz"])))
    geo.append(place(col["name"], 0, 0, col["z_center"]))
    return "".join(geo)


def det_block(det_type: str, det_name: str, sens: str, det_vol: str, threshold: float = 0.001, eres_sigma: float = 1.0, mdcal: bool = False) -> str:
    if mdcal:
        return (
            f"MDCalorimeter {det_name}\n"
            f"{det_name}.SensitiveVolume {sens}\n"
            f"{det_name}.DetectorVolume {det_vol}\n"
            f"{det_name}.StructuralPitch 0.155 0.155 0.1\n"
            f"{det_name}.StructuralOffset 0 0 0\n"
            f"{det_name}.TriggerThreshold {fmt(threshold)} 0.0\n"
            f"{det_name}.EnergyResolution Gauss {fmt(threshold)} {fmt(threshold)} {fmt(eres_sigma)}\n"
            f"{det_name}.EnergyResolution Gauss 3000 3000 {fmt(eres_sigma)}\n\n"
        )
    return (
        f"{det_type} {det_name}\n"
        f"{det_name}.SensitiveVolume {sens}\n"
        f"{det_name}.DetectorVolume {det_vol}\n"
        f"{det_name}.TriggerThreshold {fmt(threshold)}\n"
        f"{det_name}.EnergyResolution Gauss {fmt(threshold)} {fmt(threshold)} {fmt(eres_sigma)}\n"
        f"{det_name}.EnergyResolution Gauss 3000 3000 {fmt(eres_sigma)}\n\n"
    )


def build_det(bounds: dict[str, Any]) -> str:
    lines = ["// DEMO2_DR_v2p2 Cu64-fix detector map\n\n"]
    for i in range(len(bounds["TES_LAYERS"])):
        lines.append(det_block("", f"D{i+1}", f"TES_Pixel_L{i}", f"TES_L{i}", threshold=0.3, eres_sigma=0.14, mdcal=True))
        sub = bounds["SUBSTRATES"][i]["name"]
        lines.append(det_block("Scintillator", f"{sub}_SD", sub, sub))
    sens_names = [bounds["SAMPLE_BOX"]["name"], bounds["THERMAL_FINGER"]["name"]]
    if bounds["SAMPLE_BOX"].get("window"):
        sens_names.append(bounds["SAMPLE_BOX"]["window"]["name"])
    sens_names.extend(can["name"] for can in bounds["OPEN_BOTTOM_CANS"])
    sens_names.extend(shell["name"] for shell in bounds["CRYOSTAT_SHELLS"])
    sens_names.extend(win["name"] for win in bounds["STAGE_WINDOWS"])
    sens_names.extend(rec["name"] for rec in bounds["PASSIVE_PROXIES"])
    sens_names.extend(seg["name"] for seg in bounds["ACTIVE_SHIELD_SEGMENTS"])
    sens_names.append(bounds["OUTER_MECHANICAL_SHELL"]["name"])
    sens_names.extend(win["name"] for win in bounds["WINDOWS"] if win["name"] != bounds["SAMPLE_BOX"].get("window", {}).get("name"))
    sens_names.append(bounds["COLLIMATOR"]["name"])

    seen: set[str] = set()
    for name in sens_names:
        if name in seen:
            continue
        seen.add(name)
        det_name = f"{name}_SD"
        if name.startswith("CsI_Active_Shield"):
            lines.append(
                f"Scintillator {det_name}\n"
                f"{det_name}.SensitiveVolume {name}\n"
                f"{det_name}.DetectorVolume {name}\n"
                f"{det_name}.TriggerThreshold 80.0\n"
                f"{det_name}.NoiseThresholdEqualsTriggerThreshold true\n"
                f"{det_name}.EnergyResolution Gauss 80 80 1\n"
                f"{det_name}.EnergyResolution Gauss 3000 3000 1\n\n"
            )
        else:
            lines.append(det_block("Scintillator", det_name, name, name))
    lines.append("// Native MEGAlib Trigger/Veto blocks intentionally absent for full activation-event storage.\n")
    return "".join(lines)


@dataclass
class Interval:
    name: str
    r0: float
    r1: float
    z0: float
    z1: float
    kind: str


def add_shell_intervals(name: str, r_in: float, r_out: float, z_in_bot: float, z_in_top: float, z_out_bot: float, z_out_top: float, top_hole: float, bottom_hole: float, out: list[Interval]) -> None:
    out.append(Interval(name + ":bottom", bottom_hole, r_out, z_out_bot, z_in_bot, "shell_bottom"))
    out.append(Interval(name + ":side", r_in, r_out, z_in_bot, z_in_top, "shell_side"))
    out.append(Interval(name + ":top", top_hole, r_out, z_in_top, z_out_top, "shell_top"))


def intervals(bounds: dict[str, Any]) -> list[Interval]:
    out: list[Interval] = []
    for p in bounds["COLD_PLATES"]:
        out.append(Interval(p["name"], 0.0, p["r"], p["zc"] - p["h"] / 2.0, p["zc"] + p["h"] / 2.0, "plate"))
    s = bounds["SAMPLE_BOX"]
    add_shell_intervals(s["name"], s["r_in"], s["r_out"], s["z_in_bot"], s["z_in_top"], s["z_out_bot"], s["z_out_top"], s["hole"], s["bottom_hole"], out)
    tf = bounds["THERMAL_FINGER"]
    out.append(Interval(tf["name"], 0.0, tf["r"], tf["z0"], tf["z1"], "thermal_finger"))
    for can in bounds["OPEN_BOTTOM_CANS"]:
        out.append(Interval(can["name"] + ":side", can["r_in"], can["r_out"], can["z_in_bot"], can["z_in_top"], "can_side"))
        out.append(Interval(can["name"] + ":top", can["hole"], can["r_out"], can["z_in_top"], can["z_out_top"], "can_top"))
    for shell in bounds["CRYOSTAT_SHELLS"]:
        add_shell_intervals(shell["name"], shell["r_in"], shell["r_out"], shell["z_in_bot"], shell["z_in_top"], shell["z_out_bot"], shell["z_out_top"], shell["hole"], 0.0, out)
    for rec in bounds["PASSIVE_PROXIES"]:
        if rec.get("shape") == "cylinder":
            out.append(Interval(rec["name"], 0.0, rec["params"]["r"], rec["z0"], rec["z1"], "proxy_cyl"))
        elif rec.get("shape") == "annulus":
            out.append(Interval(rec["name"], rec["params"]["r_in"], rec["params"]["r_out"], rec["z0"], rec["z1"], "proxy_ann"))
        elif rec.get("shape") == "box":
            # Axisymmetric interval check is intentionally conservative for boxes.
            p = rec["params"]
            rmax = math.hypot(abs(rec.get("x", 0.0)) + p["hx"], abs(rec.get("y", 0.0)) + p["hy"])
            out.append(Interval(rec["name"], 0.0, rmax, rec["z0"], rec["z1"], "proxy_box_conservative"))
        elif all(k in rec for k in ("r_in", "r_out", "z0", "z1")):
            out.append(Interval(rec["name"], rec["r_in"], rec["r_out"], rec["z0"], rec["z1"], "proxy_ann"))
    active = bounds["ACTIVE_SHIELD"]
    add_shell_intervals(active["name"], active["r_in"], active["r_out"], active["z_in_bot"], active["z_in_top"], active["z_out_bot"], active["z_out_top"], active["hole"], 0.0, out)
    outer = bounds["OUTER_MECHANICAL_SHELL"]
    add_shell_intervals(outer["name"], outer["r_in"], outer["r_out"], outer["z_in_bot"], outer["z_in_top"], outer["z_out_bot"], outer["z_out_top"], outer["hole"], 0.0, out)
    return out


def overlap(a: Interval, b: Interval, tol: float = 1.0e-7) -> bool:
    if a.name.split(":")[0] == b.name.split(":")[0]:
        return False
    z = min(a.z1, b.z1) - max(a.z0, b.z0)
    r = min(a.r1, b.r1) - max(a.r0, b.r0)
    return z > tol and r > tol


def design_overlap(bounds: dict[str, Any]) -> list[dict[str, Any]]:
    ints = intervals(bounds)
    problems: list[dict[str, Any]] = []
    allowed_touch = {"SampleBox_Cu_ThermalFinger_50mK", "ColdPlate_MXC_50mK_Retained"}
    for i, a in enumerate(ints):
        for b in ints[i + 1 :]:
            if set([a.name.split(":")[0], b.name.split(":")[0]]) == allowed_touch:
                continue
            if overlap(a, b):
                # Ignore conservative false positives for off-axis box proxies; final
                # Cosima overlap check remains the authority.
                if "proxy_box_conservative" in {a.kind, b.kind}:
                    continue
                problems.append(
                    {
                        "a": a.name,
                        "b": b.name,
                        "radial_overlap_cm": min(a.r1, b.r1) - max(a.r0, b.r0),
                        "z_overlap_cm": min(a.z1, b.z1) - max(a.z0, b.z0),
                    }
                )
    return problems


def write_validation(bounds: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    names = {r["unit"] for r in rows}
    problems = []
    if "TES_SampleBox_Cu" in names:
        problems.append("TES_SampleBox_Cu remains in mass budget")
    if any(rec.get("name") == "Cryoperm_Inner_Mag_Shield" for rec in bounds.get("PASSIVE_PROXIES", [])):
        problems.append("old Cryoperm_Inner_Mag_Shield still instantiated as passive proxy")
    if bounds["SAMPLE_BOX"]["mat"] != "Cryoperm":
        problems.append("replacement sample box is not Cryoperm")
    if bounds["THERMAL_FINGER"]["mat"] != "Copper":
        problems.append("thermal finger is not Copper")
    overlaps = design_overlap(bounds)
    payload = {
        "status": "PASS" if not problems and not overlaps else "REVIEW_REQUIRED",
        "checks": {
            "removed_TES_SampleBox_Cu": "TES_SampleBox_Cu" not in names,
            "replacement_sample_box": bounds["SAMPLE_BOX"],
            "thermal_finger": bounds["THERMAL_FINGER"],
            "old_Cryoperm_proxy_removed": not any(rec.get("name") == "Cryoperm_Inner_Mag_Shield" for rec in bounds.get("PASSIVE_PROXIES", [])),
            "design_overlap_problem_count": len(overlaps),
            "mass_total_kg": sum(float(r["mass_kg"]) for r in rows),
            "group_mass_kg": group_mass(rows),
            "active_shield_threshold_keV": 80.0,
        },
        "problems": problems + overlaps,
        "note": "Design interval check only. Run Cosima overlap before production Step02.",
    }
    (OUT / "geometry_validation.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def draw_shell(ax: Any, rec: dict[str, Any], color: str, alpha: float = 0.28, bottom_hole: float = 0.0, label: str | None = None) -> None:
    r_in, r_out = rec["r_in"], rec["r_out"]
    z0, z1 = rec["z_in_bot"], rec["z_in_top"]
    ax.add_patch(Rectangle((r_in, z0), r_out - r_in, z1 - z0, facecolor=color, edgecolor=color, alpha=alpha, lw=0.8))
    ax.add_patch(Rectangle((-r_out, z0), r_out - r_in, z1 - z0, facecolor=color, edgecolor=color, alpha=alpha, lw=0.8))
    ax.add_patch(Rectangle((bottom_hole, rec["z_out_bot"]), r_out - bottom_hole, rec["z_in_bot"] - rec["z_out_bot"], facecolor=color, edgecolor=color, alpha=alpha, lw=0.8))
    ax.add_patch(Rectangle((-r_out, rec["z_out_bot"]), r_out - bottom_hole, rec["z_in_bot"] - rec["z_out_bot"], facecolor=color, edgecolor=color, alpha=alpha, lw=0.8))
    hole = rec.get("hole", 0.0)
    ax.add_patch(Rectangle((hole, rec["z_in_top"]), r_out - hole, rec["z_out_top"] - rec["z_in_top"], facecolor=color, edgecolor=color, alpha=alpha, lw=0.8))
    ax.add_patch(Rectangle((-r_out, rec["z_in_top"]), r_out - hole, rec["z_out_top"] - rec["z_in_top"], facecolor=color, edgecolor=color, alpha=alpha, lw=0.8))
    if label:
        ax.text(r_out + 0.12, 0.5 * (rec["z_in_top"] + rec["z_out_top"]), label, fontsize=7, va="center")


def draw_annulus(ax: Any, r0: float, r1: float, z0: float, z1: float, color: str, alpha: float = 0.45) -> None:
    ax.add_patch(Rectangle((r0, z0), r1 - r0, z1 - z0, facecolor=color, edgecolor=color, alpha=alpha, lw=0.6))
    ax.add_patch(Rectangle((-r1, z0), r1 - r0, z1 - z0, facecolor=color, edgecolor=color, alpha=alpha, lw=0.6))


def write_figure(bounds: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    STEP_OUT.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.7, 1.0], height_ratios=[1.0, 1.0], wspace=0.28, hspace=0.28)
    ax = fig.add_subplot(gs[:, 0])
    ax_top = fig.add_subplot(gs[0, 1])
    ax_mass = fig.add_subplot(gs[1, 1])

    draw_shell(ax, bounds["ACTIVE_SHIELD"], COLORS["CsI"], alpha=0.17, label="CsI active shield")
    draw_shell(ax, bounds["OUTER_MECHANICAL_SHELL"], COLORS["Aluminium"], alpha=0.08, label="outer Al")
    for shell in bounds["CRYOSTAT_SHELLS"]:
        draw_shell(ax, shell, COLORS["Aluminium"], alpha=0.16)
    for can in bounds["OPEN_BOTTOM_CANS"]:
        draw_annulus(ax, can["r_in"], can["r_out"], can["z_in_bot"], can["z_in_top"], COLORS["Nb"], alpha=0.42)
        draw_annulus(ax, can["hole"], can["r_out"], can["z_in_top"], can["z_out_top"], COLORS["Nb"], alpha=0.42)
    draw_shell(ax, bounds["SAMPLE_BOX"], COLORS["Cryoperm"], alpha=0.55, bottom_hole=bounds["SAMPLE_BOX"]["bottom_hole"], label="new Cryoperm sample box")
    tf = bounds["THERMAL_FINGER"]
    ax.add_patch(Rectangle((-tf["r"], tf["z0"]), 2 * tf["r"], tf["z1"] - tf["z0"], facecolor=COLORS["Copper"], edgecolor=COLORS["Copper"], alpha=0.85, lw=0.8))
    ax.annotate("Cu thermal finger\nthrough bottom hole", xy=(tf["r"], 0.5 * (tf["z0"] + tf["z1"])), xytext=(4.3, 1.2), arrowprops={"arrowstyle": "->", "lw": 0.8}, fontsize=8)
    for p in bounds["COLD_PLATES"]:
        ax.add_patch(Rectangle((-p["r"], p["zc"] - p["h"] / 2), 2 * p["r"], p["h"], facecolor=COLORS.get(p["mat"], "#999"), edgecolor=COLORS.get(p["mat"], "#999"), alpha=0.42, lw=0.6))
        ax.text(p["r"] + 0.2, p["zc"], p["name"].replace("ColdPlate_", ""), fontsize=7, va="center")
    for rec in bounds["PASSIVE_PROXIES"]:
        mat = rec.get("mat") or rec.get("material")
        color = COLORS.get(mat, "#999999")
        if rec.get("shape") == "cylinder":
            r = rec["params"]["r"]
            ax.add_patch(Rectangle((-r, rec["z0"]), 2 * r, rec["z1"] - rec["z0"], facecolor=color, edgecolor=color, alpha=0.35, lw=0.5))
        elif rec.get("shape") == "annulus":
            p = rec["params"]
            draw_annulus(ax, p["r_in"], p["r_out"], rec["z0"], rec["z1"], color, alpha=0.38)
        elif all(k in rec for k in ("r_in", "r_out", "z0", "z1")):
            draw_annulus(ax, rec["r_in"], rec["r_out"], rec["z0"], rec["z1"], color, alpha=0.38)
        elif rec.get("shape") == "box" or all(k in rec for k in ("hx", "hz", "x", "z")):
            p = rec.get("params", rec)
            x = rec.get("x", 0.0)
            zc = 0.5 * (rec.get("z0", rec.get("z", 0.0)) + rec.get("z1", rec.get("z", 0.0))) if "z0" in rec else rec.get("z", 0.0)
            ax.add_patch(Rectangle((x - p["hx"], zc - p["hz"]), 2 * p["hx"], 2 * p["hz"], facecolor=color, edgecolor=color, alpha=0.45, lw=0.5))
    for layer in bounds["TES_LAYERS"]:
        ax.add_patch(Rectangle((-layer["r_max"], layer["z_center"] - layer["hz"]), 2 * layer["r_max"], 2 * layer["hz"], facecolor=COLORS["Ta"], edgecolor=COLORS["Ta"], alpha=0.65, lw=0.5))
    for sub in bounds["SUBSTRATES"]:
        ax.add_patch(Rectangle((-sub["r_max"], sub["z_center"] - sub["hz"]), 2 * sub["r_max"], 2 * sub["hz"], facecolor=COLORS["Silicon"], edgecolor=COLORS["Silicon"], alpha=0.35, lw=0.4))
    ax.axvline(0, color="#555555", lw=0.6, ls="--")
    ax.plot([-bounds["ACTIVE_SHIELD"]["hole"], bounds["ACTIVE_SHIELD"]["hole"]], [16.051, 16.051], color="#DC2626", lw=2)
    ax.set_title("DEMO2_DR_v2p2 Cu64-fix all components: X-Z projection")
    ax.set_xlabel("X / cm")
    ax.set_ylabel("Z / cm")
    ax.set_xlim(-15.5, 15.5)
    ax.set_ylim(-23.0, 17.2)
    ax.grid(True, alpha=0.18)
    ax.legend(
        handles=[
            Patch(facecolor=COLORS["Cryoperm"], alpha=0.55, label="Cryoperm sample box"),
            Patch(facecolor=COLORS["Copper"], alpha=0.8, label="Cu thermal links/plates"),
            Patch(facecolor=COLORS["CsI"], alpha=0.25, label="CsI active shield"),
            Patch(facecolor=COLORS["Aluminium"], alpha=0.25, label="Al shells/windows"),
            Patch(facecolor=COLORS["W"], alpha=0.45, label="W passive shield"),
            Patch(facecolor=COLORS["Ta"], alpha=0.65, label="TES absorber stack"),
        ],
        loc="lower left",
        fontsize=8,
    )

    ax_top.set_aspect("equal")
    ax_top.set_title("Top view: aperture, new sample box, active well")
    active = bounds["ACTIVE_SHIELD"]
    ax_top.add_patch(Circle((0, 0), active["r_out"], facecolor=COLORS["CsI"], edgecolor=COLORS["CsI"], alpha=0.2))
    ax_top.add_patch(Circle((0, 0), active["r_in"], facecolor="white", edgecolor=COLORS["CsI"], lw=1.0))
    ax_top.add_patch(Circle((0, 0), bounds["SAMPLE_BOX"]["r_out"], facecolor=COLORS["Cryoperm"], edgecolor=COLORS["Cryoperm"], alpha=0.45))
    ax_top.add_patch(Circle((0, 0), bounds["SAMPLE_BOX"]["r_in"], facecolor="white", edgecolor=COLORS["Cryoperm"], lw=1.0))
    ax_top.add_patch(Circle((0, 0), tf["r"], facecolor=COLORS["Copper"], edgecolor=COLORS["Copper"], alpha=0.9))
    ax_top.add_patch(Circle((0, 0), active["hole"], facecolor="none", edgecolor="#DC2626", lw=2))
    ax_top.text(0, -15.0, "r(Be)=1.898 cm; sample box r=3.4-3.7 cm; Cu finger r=0.40 cm", ha="center", fontsize=8)
    ax_top.set_xlim(-15, 15)
    ax_top.set_ylim(-15, 15)
    ax_top.grid(True, alpha=0.15)
    ax_top.set_xlabel("X / cm")
    ax_top.set_ylabel("Y / cm")

    groups = group_mass(rows)
    bars = [
        ("active", sum(v for k, v in groups.items() if k.startswith("active_shield"))),
        ("sample+finger", groups.get("sample_box", 0.0) + groups.get("thermal_link", 0.0)),
        ("cold+DR", groups.get("cold_plate", 0.0) + groups.get("dr_passive", 0.0) + groups.get("service_proxy", 0.0) + groups.get("support_proxy", 0.0)),
        ("shell/passive", groups.get("cryostat_shell", 0.0) + groups.get("cryostat_passive", 0.0) + groups.get("passive_shield", 0.0)),
        ("other", sum(groups.values()) - sum(v for _, v in [])),
    ]
    # Replace "other" with the true residual after the first four groups.
    bars[-1] = ("other", sum(groups.values()) - sum(v for _, v in bars[:-1]))
    ax_mass.bar([b[0] for b in bars], [b[1] for b in bars], color=["#5DA5DA", "#4F63A8", "#B87333", "#777777", "#AAAAAA"])
    ax_mass.set_title("Nominal mass groups")
    ax_mass.set_ylabel("kg")
    ax_mass.tick_params(axis="x", rotation=25)
    for i, (_, val) in enumerate(bars):
        ax_mass.text(i, val + 0.35, f"{val:.1f}", ha="center", fontsize=8)

    png = STEP_OUT / "DEMO2_DR_v2p2_all_components_xz.png"
    fig.savefig(png, dpi=180, bbox_inches="tight")
    plt.close(fig)
    shutil.copy2(png, OUT / png.name)


def write_step00_readme(bounds: dict[str, Any], validation: dict[str, Any]) -> None:
    lines = [
        "# Step00 Geometry: DEMO2_DR_v2p2 Cu64-Fix",
        "",
        "Status: generated from `geo_refer/DEMO2_DR_v2p1_bounds.json` with the requested Cu64 mitigation.",
        "",
        "## Geometry Change",
        "",
        "- Removed `TES_SampleBox_Cu` from the simulation authority.",
        "- Removed the old outer `Cryoperm_Inner_Mag_Shield` proxy to avoid duplicate magnetic-shield material after the move.",
        "- Added `TES_SampleBox_Cryoperm` in the former Cu sample-box envelope: `r=3.4-3.7 cm`, `z=0.25-8.7 cm`, top aperture `r=1.898 cm`.",
        "- Added a bottom-center hole `r=0.40 cm` in that sample box.",
        "- Added `SampleBox_Cu_ThermalFinger_50mK`, a short Cu cylinder from `z=0.25` to `0.55 cm`, touching the 50 mK/MXC cold plate at the lower face and the sample-box bottom-hole boundary at the upper face.",
        "- Retained the thin `SampleBox_Al_Window` top foil as a low-Z aperture foil, not as part of the removed Cu box.",
        "",
        "## Simulation Files",
        "",
        f"- `{OUT.relative_to(ROOT)}/DEMO2_DR_v2p2_cu64fix.geo.setup`",
        f"- `{OUT.relative_to(ROOT)}/DEMO2_DR_v2p2_cu64fix.geo`",
        f"- `{OUT.relative_to(ROOT)}/DEMO2_DR_v2p2_cu64fix.det`",
        f"- `{OUT.relative_to(ROOT)}/Materials_DEMO2_DR_v2p2.geo`",
        f"- `{OUT.relative_to(ROOT)}/bounds.json`",
        f"- `{OUT.relative_to(ROOT)}/mass_budget.csv`",
        f"- `{OUT.relative_to(ROOT)}/geometry_validation.json`",
        "",
        "## Visualization",
        "",
        f"- `{STEP_OUT.relative_to(ROOT)}/DEMO2_DR_v2p2_all_components_xz.png`",
        "",
        "## Validation",
        "",
        f"- local design validation status: `{validation['status']}`",
        f"- design overlap problem count: `{validation['checks']['design_overlap_problem_count']}`",
        "- Native MEGAlib `Trigger/Veto` blocks are intentionally absent from the `.det`; active shield segments are sensitive volumes and downstream analysis should perform the summed-veto logic.",
        "",
        "This is a Step00 geometry authority. Before Step02 production, run a Cosima/geomega overlap check on the generated `.geo.setup`.",
        "",
    ]
    STEP.mkdir(parents=True, exist_ok=True)
    (STEP / "README.md").write_text("\n".join(lines), encoding="utf-8")


def write_setup() -> None:
    text = """Name DEMO2_DR_v2p2_cu64fix
Version 1
Include DEMO2_DR_v2p2_cu64fix.geo
Include DEMO2_DR_v2p2_cu64fix.det
SurroundingSphere 35 0 0 -3 35
"""
    (OUT / "DEMO2_DR_v2p2_cu64fix.geo.setup").write_text(text, encoding="utf-8")


def write_mass_json(rows: list[dict[str, Any]]) -> None:
    payload = {
        "total_mass_kg": sum(float(r["mass_kg"]) for r in rows),
        "group_mass_kg": group_mass(rows),
        "rows": rows,
    }
    (OUT / "mass_budget.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    STEP_OUT.mkdir(parents=True, exist_ok=True)
    base = json.loads(REF_BOUNDS.read_text(encoding="utf-8"))
    ref_rows = read_csv_rows(REF_MASS)
    bounds = adapt_bounds(base)
    rows = build_mass_rows(bounds, ref_rows)

    write_intro()
    write_materials()
    (OUT / "DEMO2_DR_v2p2_cu64fix.geo").write_text(build_geo(bounds), encoding="utf-8")
    (OUT / "DEMO2_DR_v2p2_cu64fix.det").write_text(build_det(bounds), encoding="utf-8")
    write_setup()
    (OUT / "bounds.json").write_text(json.dumps(bounds, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_csv_rows(OUT / "mass_budget.csv", rows)
    write_mass_json(rows)
    validation = write_validation(bounds, rows)
    write_figure(bounds, rows)
    write_step00_readme(bounds, validation)

    snap = STEP / "code" / "build_demo2_dr_v2p2_geometry.py"
    snap.parent.mkdir(parents=True, exist_ok=True)
    if Path(__file__).resolve() != snap.resolve():
        shutil.copy2(Path(__file__), snap)

    print(
        json.dumps(
            {
                "status": validation["status"],
                "geometry_dir": str(OUT),
                "step00": str(STEP),
                "sample_box": bounds["SAMPLE_BOX"]["name"],
                "thermal_finger": bounds["THERMAL_FINGER"]["name"],
                "total_mass_kg": validation["checks"]["mass_total_kg"],
                "outputs": [
                    str(OUT / "DEMO2_DR_v2p2_cu64fix.geo.setup"),
                    str(OUT / "DEMO2_DR_v2p2_cu64fix.geo"),
                    str(OUT / "DEMO2_DR_v2p2_cu64fix.det"),
                    str(STEP_OUT / "DEMO2_DR_v2p2_all_components_xz.png"),
                ],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if validation["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
