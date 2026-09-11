#!/usr/bin/env python3
"""Build a reviewed demo detector mass model for NEW_GEO_RE.

This standalone demo is intentionally generated in centimetres.  It does not
replace the current project geometry authority.  It implements the review
direction in tmp_mass_model_review_bundle:

* keep the TES/ADR detector-head core and the 1.898 cm aperture convention;
* make the nominal active shield an oxygen-free segmented CsI(Tl) well;
* add a mid-mass nearby cryogenic hardware proxy instead of the very light
  thin-shell-only passive cryostat;
* keep the output MEGAlib/Cosima geometry simple enough to inspect.
"""

from __future__ import annotations

import csv
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/new_geo_re_demo_matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Patch, Rectangle


SCRIPT = Path(__file__).resolve()
DEMO = SCRIPT.parent
OUT = DEMO / "outputs"
FIG = OUT / "figures"

MODEL = "TibetTES_ADR_v5_midmass_csi_demo"
GEO = OUT / f"{MODEL}.geo"
DET = OUT / f"{MODEL}.det"
SETUP = OUT / f"{MODEL}.geo.setup"
INTRO = OUT / "Intro_TibetTES_demo.geo"
MATERIALS = OUT / "Materials_TibetTES_demo.geo"
BOUNDS = OUT / "bounds.json"
MASS_CSV = OUT / "mass_budget.csv"
MASS_JSON = OUT / "mass_budget.json"
VALIDATION = OUT / "validation.json"
WRL = OUT / f"{MODEL}.wrl"
PNG = FIG / f"{MODEL}_schematic.png"
REPORT = OUT / "mass_model_summary.md"
README = DEMO / "README.md"


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
    "SaltProxy": 5.80,
    "G10": 1.85,
    "Mylar": 1.39,
}


COLORS = {
    "TES": "#D64B4B",
    "Substrate": "#333333",
    "Copper": "#C7813A",
    "Aluminium": "#BBBBBB",
    "Nb": "#5AC8D8",
    "Cryoperm": "#516C9D",
    "LowCarbonSteel": "#555555",
    "SaltProxy": "#8E6BBE",
    "G10": "#8BC06A",
    "CsI": "#6FA8DC",
    "Window": "#B279A2",
    "Collimator": "#202020",
    "Source": "#D62728",
}


def fmt(x: float) -> str:
    if abs(x) < 5.0e-13:
        x = 0.0
    return f"{x:.9g}"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"[OK] wrote {path.relative_to(DEMO)}")


def pcon_shape_line(phi0_deg: float, dphi_deg: float, planes: list[tuple[float, float, float]]) -> str:
    toks = ["PCON", fmt(phi0_deg), fmt(dphi_deg), str(len(planes))]
    for z, rmin, rmax in planes:
        toks.extend([fmt(z), fmt(rmin), fmt(rmax)])
    return " ".join(toks)


def volume_def(volname: str, material: str, shape_line: str, vis: int = 1) -> str:
    return (
        f"// Volume {volname}; material={material}\n"
        f"Volume {volname}\n"
        f"{volname}.Material {material}\n"
        f"{volname}.Visibility {vis}\n"
        f"{volname}.Shape {shape_line}\n\n"
    )


def place(volname: str, x: float, y: float, z: float, mother: str = "WorldVolume", vis: int | None = None) -> str:
    out = f"{volname}.Position {fmt(x)} {fmt(y)} {fmt(z)}\n{volname}.Mother {mother}\n"
    if vis is not None:
        out += f"{volname}.Visibility {vis}\n"
    return out + "\n"


def pcon_cylinder_def(volname: str, material: str, rmax: float, halfz: float, vis: int = 1) -> str:
    return volume_def(volname, material, pcon_shape_line(0.0, 360.0, [(-halfz, 0.0, rmax), (halfz, 0.0, rmax)]), vis)


def annular_cylinder_def(volname: str, material: str, rmin: float, rmax: float, z0: float, z1: float, vis: int = 1) -> str:
    return volume_def(volname, material, pcon_shape_line(0.0, 360.0, [(z0, rmin, rmax), (z1, rmin, rmax)]), vis)


def brik_def(volname: str, material: str, hx: float, hy: float, hz: float, vis: int = 1) -> str:
    return volume_def(volname, material, f"BRIK {fmt(hx)} {fmt(hy)} {fmt(hz)}", vis)


def closed_shell_def(
    volname: str,
    material: str,
    r_in: float,
    r_out: float,
    z_in_bot: float,
    z_in_top: float,
    z_out_bot: float,
    z_out_top: float,
    hole_r_top: float,
    vis: int = 1,
) -> str:
    planes = [
        (z_out_bot, 0.0, r_out),
        (z_in_bot, 0.0, r_out),
        (z_in_bot, r_in, r_out),
        (z_in_top, r_in, r_out),
        (z_in_top, hole_r_top, r_out),
        (z_out_top, hole_r_top, r_out),
    ]
    return volume_def(volname, material, pcon_shape_line(0.0, 360.0, planes), vis)


def open_bottom_can_def(
    volname: str,
    material: str,
    r_in: float,
    r_out: float,
    z_in_bot: float,
    z_in_top: float,
    z_out_top: float,
    hole_r_top: float,
    vis: int = 1,
) -> str:
    planes = [
        (z_in_bot, r_in, r_out),
        (z_in_top, r_in, r_out),
        (z_in_top, hole_r_top, r_out),
        (z_out_top, hole_r_top, r_out),
    ]
    return volume_def(volname, material, pcon_shape_line(0.0, 360.0, planes), vis)


def shell_volume_cm3(r_in: float, r_out: float, z_in_bot: float, z_in_top: float, z_out_bot: float, z_out_top: float, hole: float, phi_fraction: float = 1.0) -> float:
    side = math.pi * (r_out * r_out - r_in * r_in) * (z_in_top - z_in_bot)
    bottom = math.pi * r_out * r_out * (z_in_bot - z_out_bot)
    top = math.pi * (r_out * r_out - hole * hole) * (z_out_top - z_in_top)
    return phi_fraction * (side + bottom + top)


def open_bottom_can_volume_cm3(r_in: float, r_out: float, z_in_bot: float, z_in_top: float, z_out_top: float, hole: float) -> float:
    side = math.pi * (r_out * r_out - r_in * r_in) * (z_in_top - z_in_bot)
    top = math.pi * (r_out * r_out - hole * hole) * (z_out_top - z_in_top)
    return side + top


def cylinder_volume_cm3(r: float, h: float, phi_fraction: float = 1.0) -> float:
    return phi_fraction * math.pi * r * r * h


def annular_volume_cm3(r_in: float, r_out: float, h: float, phi_fraction: float = 1.0) -> float:
    return phi_fraction * math.pi * (r_out * r_out - r_in * r_in) * h


def brik_volume_cm3(hx: float, hy: float, hz: float) -> float:
    return 8.0 * hx * hy * hz


def mass_kg(material: str, volume_cm3: float) -> float:
    return DENSITY_G_CM3.get(material, 0.0) * volume_cm3 / 1000.0


@dataclass
class MassRow:
    category: str
    unit: str
    material: str
    volume_cm3: float
    notes: str = ""

    @property
    def mass_kg(self) -> float:
        return mass_kg(self.material, self.volume_cm3)

    def as_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "unit": self.unit,
            "material": self.material,
            "density_g_cm3": DENSITY_G_CM3.get(self.material, 0.0),
            "volume_cm3": self.volume_cm3,
            "mass_kg": self.mass_kg,
            "notes": self.notes,
        }


def det_add_mdcal(det_lines: list[str], det_name: str, sens_vol: str, det_vol: str, pitch_xyz: tuple[float, float, float], offset_xyz: tuple[float, float, float] = (0, 0, 0), thr: float = 0.001, eres_sigma: float = 1.0) -> None:
    px, py, pz = pitch_xyz
    ox, oy, oz = offset_xyz
    det_lines.append(
        f"MDCalorimeter {det_name}\n"
        f"{det_name}.SensitiveVolume {sens_vol}\n"
        f"{det_name}.DetectorVolume {det_vol}\n"
        f"{det_name}.StructuralPitch {fmt(px)} {fmt(py)} {fmt(pz)}\n"
        f"{det_name}.StructuralOffset {fmt(ox)} {fmt(oy)} {fmt(oz)}\n"
        f"{det_name}.TriggerThreshold {fmt(thr)} 0.0\n"
        f"{det_name}.EnergyResolution Gauss {fmt(thr)} {fmt(thr)} {fmt(eres_sigma)}\n"
        f"{det_name}.EnergyResolution Gauss 3000 3000 {fmt(eres_sigma)}\n\n"
    )


def det_add_scint(det_lines: list[str], det_name: str, sens_vol: str, det_vol: str, thr: float = 0.001, eres_sigma: float = 1.0) -> None:
    det_lines.append(
        f"Scintillator {det_name}\n"
        f"{det_name}.SensitiveVolume {sens_vol}\n"
        f"{det_name}.DetectorVolume {det_vol}\n"
        f"{det_name}.TriggerThreshold {fmt(thr)}\n"
        f"{det_name}.EnergyResolution Gauss {fmt(thr)} {fmt(thr)} {fmt(eres_sigma)}\n"
        f"{det_name}.EnergyResolution Gauss 3000 3000 {fmt(eres_sigma)}\n\n"
    )


def write_materials_and_intro() -> None:
    materials = """# Custom materials for the NEW_GEO_RE reviewed demo mass model.
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

# Pure CsI is used for a CsI(Tl) shield mass model; the Tl dopant is a
# sub-percent scintillation activator and is neglected for activation mass.
Material CsI
CsI.Density 4.51
CsI.Component Cs 1
CsI.Component I 1

Material Cryoperm
Cryoperm.Density 8.70
Cryoperm.Component Ni 4
Cryoperm.Component Fe 1

Material LowCarbonSteel
LowCarbonSteel.Density 7.87
LowCarbonSteel.Component Fe 99
LowCarbonSteel.Component C 1

Material SaltProxy
SaltProxy.Density 5.80
SaltProxy.Component Gd 2
SaltProxy.Component O 3

Material G10
G10.Density 1.85
G10.Component Si 1
G10.Component O 2
G10.Component C 3
G10.Component H 3

Material Mylar
Mylar.Density 1.39
Mylar.Component C 10
Mylar.Component H 8
Mylar.Component O 4

"""
    intro = """Name MassmodelTibetTES_ADR_v5_midmass_csi_demo
Version 1

Include Materials_TibetTES_demo.geo
AbsorptionFileDirectory crossections

Volume WorldVolume
WorldVolume.Visibility 0
WorldVolume.Material Vacuum
WorldVolume.Shape BRIK 1000 1000 1000
WorldVolume.Mother 0
"""
    write_text(MATERIALS, materials)
    write_text(INTRO, intro)


def build_geometry() -> dict[str, Any]:
    write_materials_and_intro()

    geo: list[str] = ["Include Intro_TibetTES_demo.geo\n\n"]
    det: list[str] = ["// Reviewed MidMass CsI nominal detector map\n\n"]
    masses: list[MassRow] = []

    # Detector/TES core retained from the current authority.
    n_layers = 6
    n_pix = 20
    pix_x = pix_y = 0.15
    pix_z = 0.30
    gap_pix = 0.005
    pitch = pix_x + gap_pix
    eff_r = 1.80
    sub_r = 2.20
    sub_h = 0.03
    z_sub_centers = [1.0 + l * 1.2 for l in range(n_layers)]
    z_tes_centers = [zc + sub_h / 2.0 + pix_z / 2.0 for zc in z_sub_centers]
    z_tes_top = max(z_tes_centers) + pix_z / 2.0

    pix_xy: list[tuple[float, float]] = []
    for i in range(n_pix):
        for j in range(n_pix):
            x = -((n_pix * pitch) / 2.0) + (pitch / 2.0) + i * pitch
            y = -((n_pix * pitch) / 2.0) + (pitch / 2.0) + j * pitch
            if math.hypot(x, y) < eff_r:
                pix_xy.append((x, y))

    plates = [
        {"name": "ColdPlate_50mK", "mat": "Copper", "r": 4.5, "h": 0.5, "zc": 0.0, "basis": "50 mK mounting plate retained as detector-head anchor."},
        {"name": "ColdPlate_1K", "mat": "Copper", "r": 5.5, "h": 0.5, "zc": -3.2, "basis": "1 K intercept plate."},
        {"name": "ColdPlate_4K", "mat": "Copper", "r": 7.0, "h": 0.6, "zc": -7.2, "basis": "4 K / pulse-tube-stage analog."},
        {"name": "ColdPlate_50K", "mat": "Aluminium", "r": 8.5, "h": 0.6, "zc": -10.8, "basis": "50 K interface plate."},
    ]
    for p in plates:
        geo.append(pcon_cylinder_def(p["name"], p["mat"], p["r"], p["h"] / 2.0))
        geo.append(place(p["name"], 0, 0, p["zc"]))
        masses.append(MassRow("cold_plate", p["name"], p["mat"], cylinder_volume_cm3(p["r"], p["h"]), p["basis"]))

    for l in range(n_layers):
        geo.append(pcon_cylinder_def(f"Substrate_L{l}", "Silicon", sub_r, sub_h / 2.0))
        geo.append(brik_def(f"TES_Pixel_L{l}", "Ta", pix_x / 2.0, pix_y / 2.0, pix_z / 2.0))
        geo.append(brik_def(f"TES_L{l}", "Vacuum", 2.4, 2.4, pix_z / 2.0 + 0.01, vis=0))
        geo.append(place(f"Substrate_L{l}", 0, 0, z_sub_centers[l]))
        geo.append(place(f"TES_L{l}", 0, 0, z_tes_centers[l], vis=0))
        for idx, (xw, yw) in enumerate(pix_xy):
            geo.append(f"TES_Pixel_L{l}.Copy TP_L{l}_{idx:05d}\n")
            geo.append(place(f"TP_L{l}_{idx:05d}", xw, yw, 0, f"TES_L{l}", vis=0))
        det_add_mdcal(det, f"D{l + 1}", f"TES_Pixel_L{l}", f"TES_L{l}", (pitch, pitch, 0.1), thr=0.3, eres_sigma=0.14)
        det_add_scint(det, f"Substrate_L{l}_SD", f"Substrate_L{l}", f"Substrate_L{l}", thr=0.001)
        masses.append(MassRow("substrate", f"Substrate_L{l}", "Silicon", cylinder_volume_cm3(sub_r, sub_h), "Si substrate mass behind TES layer."))

    masses.append(MassRow("detector", "TES pixels (6x376)", "Ta", len(pix_xy) * n_layers * brik_volume_cm3(pix_x / 2.0, pix_y / 2.0, pix_z / 2.0), "Ta absorber array; same footprint convention as current authority."))

    entrance_r = 1.898
    sample_box = {
        "name": "TES_SampleBox_Cu",
        "mat": "Copper",
        "r_in": 3.4,
        "r_out": 3.7,
        "z_out_bot": 0.25,
        "z_in_bot": 0.55,
        "z_in_top": 8.4,
        "z_out_top": 8.7,
        "hole": entrance_r,
        "basis": "Cu sample-box local shielding retained; aperture matched to Be window.",
    }
    sample_window = {"name": "SampleBox_Al_Window", "mat": "Aluminium", "r": entrance_r, "thick": 0.0025, "zc": 8.55, "basis": "Very thin Al foil placeholder; nominal only, open-aperture scan recommended."}
    geo.append(closed_shell_def(sample_box["name"], sample_box["mat"], sample_box["r_in"], sample_box["r_out"], sample_box["z_in_bot"], sample_box["z_in_top"], sample_box["z_out_bot"], sample_box["z_out_top"], sample_box["hole"]))
    geo.append(place(sample_box["name"], 0, 0, 0))
    geo.append(pcon_cylinder_def(sample_window["name"], sample_window["mat"], sample_window["r"], sample_window["thick"] / 2.0))
    geo.append(place(sample_window["name"], 0, 0, sample_window["zc"]))
    det_add_scint(det, sample_box["name"] + "_SD", sample_box["name"], sample_box["name"], thr=0.001)
    det_add_scint(det, sample_window["name"] + "_SD", sample_window["name"], sample_window["name"], thr=0.001)
    masses.append(MassRow("sample_box", sample_box["name"], sample_box["mat"], shell_volume_cm3(sample_box["r_in"], sample_box["r_out"], sample_box["z_in_bot"], sample_box["z_in_top"], sample_box["z_out_bot"], sample_box["z_out_top"], sample_box["hole"]), sample_box["basis"]))
    masses.append(MassRow("window", sample_window["name"], sample_window["mat"], cylinder_volume_cm3(sample_window["r"], sample_window["thick"]), sample_window["basis"]))

    # Nominal Nb can keeps an open aperture; the continuous Nb foil is a
    # systematic, not part of this nominal demo.
    nb_can = {"name": "Nb_SC_Detector_Can", "mat": "Nb", "r_in": 4.505, "r_out": 4.535, "z_in_bot": -0.25, "z_in_top": 9.2, "z_out_top": 9.23, "hole": entrance_r, "basis": "Open-bottom Nb superconducting can; top aperture is open in the nominal demo."}
    geo.append(open_bottom_can_def(nb_can["name"], nb_can["mat"], nb_can["r_in"], nb_can["r_out"], nb_can["z_in_bot"], nb_can["z_in_top"], nb_can["z_out_top"], nb_can["hole"]))
    geo.append(place(nb_can["name"], 0, 0, 0))
    det_add_scint(det, nb_can["name"] + "_SD", nb_can["name"], nb_can["name"], thr=0.001)
    masses.append(MassRow("can", nb_can["name"], nb_can["mat"], open_bottom_can_volume_cm3(nb_can["r_in"], nb_can["r_out"], nb_can["z_in_bot"], nb_can["z_in_top"], nb_can["z_out_top"], nb_can["hole"]), nb_can["basis"]))

    shells = [
        {"name": "Thermal_4K_Al_Shield", "mat": "Aluminium", "r_in": 7.3, "r_out": 7.38, "z_in_bot": -9.0, "z_in_top": 11.4, "z_out_bot": -9.08, "z_out_top": 11.48, "hole": entrance_r, "basis": "4 K radiation shield retained; aperture is open in nominal demo."},
        {"name": "Thermal_50K_Al_Shield", "mat": "Aluminium", "r_in": 8.8, "r_out": 8.88, "z_in_bot": -12.4, "z_in_top": 12.2, "z_out_bot": -12.48, "z_out_top": 12.28, "hole": entrance_r, "basis": "50 K radiation shield retained; aperture is open in nominal demo."},
        {"name": "Vacuum_Jacket_Al", "mat": "Aluminium", "r_in": 9.3, "r_out": 9.55, "z_in_bot": -13.2, "z_in_top": 12.6, "z_out_bot": -13.45, "z_out_top": 12.85, "hole": entrance_r, "basis": "Al vacuum-jacket mass model; Be is the only aperture closure."},
    ]
    for shell in shells:
        geo.append(closed_shell_def(shell["name"], shell["mat"], shell["r_in"], shell["r_out"], shell["z_in_bot"], shell["z_in_top"], shell["z_out_bot"], shell["z_out_top"], shell["hole"]))
        geo.append(place(shell["name"], 0, 0, 0))
        det_add_scint(det, shell["name"] + "_SD", shell["name"], shell["name"], thr=0.001)
        masses.append(MassRow("cryostat_shell", shell["name"], shell["mat"], shell_volume_cm3(shell["r_in"], shell["r_out"], shell["z_in_bot"], shell["z_in_top"], shell["z_out_bot"], shell["z_out_top"], shell["hole"]), shell["basis"]))

    # Added mid-mass nearby cryogenic hardware proxies from the review.
    dense_rings = [
        {"category": "midmass_proxy", "name": "Cryoperm_Mag_Shield", "mat": "Cryoperm", "r_in": 4.75, "r_out": 5.05, "z_in_bot": -0.25, "z_in_top": 9.6, "z_out_bot": -0.55, "z_out_top": 9.9, "hole": entrance_r, "basis": "Ni-rich magnetic-shield systematic mass near the TES/Nb can."},
        {"category": "midmass_proxy", "name": "ADR_Magnet_Coil_Cu", "mat": "Copper", "r_in": 5.65, "r_out": 7.25, "z0": -6.65, "z1": -2.45, "basis": "Simplified ADR magnet/coil copper mass inside the 4 K shield."},
        {"category": "midmass_proxy", "name": "ADR_Magnet_Yoke_Fe", "mat": "LowCarbonSteel", "r_in": 7.45, "r_out": 8.35, "z0": -8.70, "z1": -2.20, "basis": "Conservative Fe return-yoke proxy; important activation/scattering systematic."},
        {"category": "midmass_proxy", "name": "ADR_SaltPill_Proxy", "mat": "SaltProxy", "r": 2.40, "z0": -6.55, "z1": -4.25, "basis": "Dense salt-pill/regenerator proxy below detector, away from the aperture."},
        {"category": "midmass_proxy", "name": "Thermal_Bus_Cu", "mat": "Copper", "r_in": 2.60, "r_out": 5.20, "z0": -2.40, "z1": -1.20, "basis": "Cu thermal bus / heat-switch mass proxy."},
        {"category": "midmass_proxy", "name": "Vacuum_Jacket_Al_Reinforcement", "mat": "Aluminium", "r_in": 9.60, "r_out": 10.00, "z0": -12.80, "z1": 12.40, "basis": "Dewar wall/flange/port reinforcement proxy in the gap before the active shield."},
        {"category": "midmass_proxy", "name": "Vacuum_Top_Flange_Al", "mat": "Aluminium", "r_in": 2.20, "r_out": 10.00, "z0": 12.90, "z1": 13.30, "basis": "Top flange/collar mass around the entrance aperture, inside active-shield cavity."},
        {"category": "midmass_proxy", "name": "Vacuum_Bottom_Flange_Al", "mat": "Aluminium", "r_in": 2.20, "r_out": 10.00, "z0": -13.80, "z1": -13.50, "basis": "Bottom flange/collar mass near the vacuum-jacket bottom."},
        {"category": "midmass_proxy", "name": "PulseTube_ColdHead_Interface_Cu", "mat": "Copper", "r_in": 8.40, "r_out": 8.75, "z0": -11.50, "z1": -9.20, "basis": "Local cold-head interface proxy; compressor mass remains out of local model."},
    ]
    for rec in dense_rings:
        if "z_in_bot" in rec:
            geo.append(closed_shell_def(rec["name"], rec["mat"], rec["r_in"], rec["r_out"], rec["z_in_bot"], rec["z_in_top"], rec["z_out_bot"], rec["z_out_top"], rec["hole"]))
            volume = shell_volume_cm3(rec["r_in"], rec["r_out"], rec["z_in_bot"], rec["z_in_top"], rec["z_out_bot"], rec["z_out_top"], rec["hole"])
        elif "r" in rec:
            geo.append(pcon_cylinder_def(rec["name"], rec["mat"], rec["r"], (rec["z1"] - rec["z0"]) / 2.0))
            geo.append(place(rec["name"], 0, 0, 0.5 * (rec["z0"] + rec["z1"])))
            volume = cylinder_volume_cm3(rec["r"], rec["z1"] - rec["z0"])
            det_add_scint(det, rec["name"] + "_SD", rec["name"], rec["name"], thr=0.001)
            masses.append(MassRow(rec["category"], rec["name"], rec["mat"], volume, rec["basis"]))
            continue
        else:
            geo.append(annular_cylinder_def(rec["name"], rec["mat"], rec["r_in"], rec["r_out"], rec["z0"], rec["z1"]))
            volume = annular_volume_cm3(rec["r_in"], rec["r_out"], rec["z1"] - rec["z0"])
        geo.append(place(rec["name"], 0, 0, 0))
        det_add_scint(det, rec["name"] + "_SD", rec["name"], rec["name"], thr=0.001)
        masses.append(MassRow(rec["category"], rec["name"], rec["mat"], volume, rec["basis"]))

    # Light off-axis supports/readout proxies.  They are not enough mass by
    # themselves, but they stop the model from implying a perfectly empty service
    # volume.
    service_boxes = [
        {"name": "SQUID_Readout_Al_Box", "mat": "Aluminium", "hx": 0.35, "hy": 1.0, "hz": 1.6, "x": 5.8, "y": 0.0, "z": 3.0, "basis": "Readout/support box proxy offset from aperture."},
        {"name": "Harness_Cu_Bundle_A", "mat": "Copper", "hx": 0.12, "hy": 0.35, "hz": 4.0, "x": -5.7, "y": 1.4, "z": 2.8, "basis": "Cu harness/strap proxy."},
        {"name": "Harness_Cu_Bundle_B", "mat": "Copper", "hx": 0.12, "hy": 0.35, "hz": 4.0, "x": -5.7, "y": -1.4, "z": 2.8, "basis": "Cu harness/strap proxy."},
    ]
    for b in service_boxes:
        geo.append(brik_def(b["name"], b["mat"], b["hx"], b["hy"], b["hz"]))
        geo.append(place(b["name"], b["x"], b["y"], b["z"]))
        det_add_scint(det, b["name"] + "_SD", b["name"], b["name"], thr=0.001)
        masses.append(MassRow("service_proxy", b["name"], b["mat"], brik_volume_cm3(b["hx"], b["hy"], b["hz"]), b["basis"]))

    # CsI(Tl) segmented active shield.  Names deliberately include ActiveShield.
    active = {
        "name": "CsI_Active_Shield",
        "mat": "CsI",
        "r_in": 10.05,
        "r_out": 14.05,
        "z_in_bot": -13.95,
        "z_in_top": 13.35,
        "z_out_bot": -21.95,
        "z_out_top": 15.35,
        "hole": entrance_r,
        "side_thickness": 4.0,
        "bottom_thickness": 8.0,
        "top_thickness": 2.0,
        "nominal_veto_threshold_keV": 80.0,
        "threshold_scan_keV": [30, 50, 70, 80, 100],
        "basis": "Nominal oxygen-free segmented CsI(Tl) active well from review.",
    }
    active_segments: list[dict[str, Any]] = []
    for i in range(8):
        phi0 = i * 45.0
        name = f"CsI_Active_Shield_Side{i:02d}"
        planes = [(active["z_in_bot"], active["r_in"], active["r_out"]), (active["z_in_top"], active["r_in"], active["r_out"])]
        geo.append(volume_def(name, "CsI", pcon_shape_line(phi0, 45.0, planes)))
        geo.append(place(name, 0, 0, 0))
        det_add_scint(det, name + "_SD", name, name, thr=0.01)
        vol = annular_volume_cm3(active["r_in"], active["r_out"], active["z_in_top"] - active["z_in_bot"], 45.0 / 360.0)
        masses.append(MassRow("active_shield_side", name, "CsI", vol, "One of eight CsI side-panel segments."))
        active_segments.append({"name": name, "part": "side", "phi0_deg": phi0, "dphi_deg": 45.0, "r_in": active["r_in"], "r_out": active["r_out"], "z0": active["z_in_bot"], "z1": active["z_in_top"]})
    for i in range(4):
        phi0 = i * 90.0
        name = f"CsI_Active_Shield_Bottom{i:02d}"
        planes = [(active["z_out_bot"], 0.0, active["r_out"]), (active["z_in_bot"], 0.0, active["r_out"])]
        geo.append(volume_def(name, "CsI", pcon_shape_line(phi0, 90.0, planes)))
        geo.append(place(name, 0, 0, 0))
        det_add_scint(det, name + "_SD", name, name, thr=0.01)
        vol = cylinder_volume_cm3(active["r_out"], active["z_in_bot"] - active["z_out_bot"], 90.0 / 360.0)
        masses.append(MassRow("active_shield_bottom", name, "CsI", vol, "One of four CsI bottom-panel segments."))
        active_segments.append({"name": name, "part": "bottom", "phi0_deg": phi0, "dphi_deg": 90.0, "r_in": 0.0, "r_out": active["r_out"], "z0": active["z_out_bot"], "z1": active["z_in_bot"]})
    for i in range(8):
        phi0 = i * 45.0
        name = f"CsI_Active_Shield_Top{i:02d}"
        planes = [(active["z_in_top"], active["hole"], active["r_out"]), (active["z_out_top"], active["hole"], active["r_out"])]
        geo.append(volume_def(name, "CsI", pcon_shape_line(phi0, 45.0, planes)))
        geo.append(place(name, 0, 0, 0))
        det_add_scint(det, name + "_SD", name, name, thr=0.01)
        vol = annular_volume_cm3(active["hole"], active["r_out"], active["z_out_top"] - active["z_in_top"], 45.0 / 360.0)
        masses.append(MassRow("active_shield_top", name, "CsI", vol, "One of eight CsI top-annulus segments."))
        active_segments.append({"name": name, "part": "top", "phi0_deg": phi0, "dphi_deg": 45.0, "r_in": active["hole"], "r_out": active["r_out"], "z0": active["z_in_top"], "z1": active["z_out_top"]})

    outer = {
        "name": "Outer_Al_Mech_Shell",
        "mat": "Aluminium",
        "r_in": 14.25,
        "r_out": 14.45,
        "z_in_bot": -22.15,
        "z_in_top": 15.55,
        "z_out_bot": -22.35,
        "z_out_top": 15.75,
        "hole": entrance_r,
        "basis": "Outer cover/support outside segmented CsI panels; not a pressure boundary.",
    }
    geo.append(closed_shell_def(outer["name"], outer["mat"], outer["r_in"], outer["r_out"], outer["z_in_bot"], outer["z_in_top"], outer["z_out_bot"], outer["z_out_top"], outer["hole"]))
    geo.append(place(outer["name"], 0, 0, 0))
    det_add_scint(det, outer["name"] + "_SD", outer["name"], outer["name"], thr=0.001)
    masses.append(MassRow("outer_shell", outer["name"], outer["mat"], shell_volume_cm3(outer["r_in"], outer["r_out"], outer["z_in_bot"], outer["z_in_top"], outer["z_out_bot"], outer["z_out_top"], outer["hole"]), outer["basis"]))

    # Entrance Be window and W grid retained for source-plane compatibility.
    be = {"name": "Win_Be_Cryostat", "mat": "Be", "r": entrance_r, "thick": 0.015, "zc": 12.8425, "basis": "Current Be-window transport convention retained: r=1.898 cm, t=0.015 cm."}
    geo.append(pcon_cylinder_def(be["name"], be["mat"], be["r"], be["thick"] / 2.0))
    geo.append(place(be["name"], 0, 0, be["zc"]))
    det_add_scint(det, "WinBe_SD", be["name"], be["name"], thr=0.001)
    masses.append(MassRow("window", be["name"], be["mat"], cylinder_volume_cm3(be["r"], be["thick"]), be["basis"]))

    coll = {"name": "W_Collimator_Aperture_Stop", "type": "annular_aperture_stop", "z_center": 16.0, "r_inner": entrance_r, "r_max": 3.1, "hz": 0.05, "basis": "Overlap-safe W annular aperture stop retained only as first passive entrance aperture proxy; not a Laue optic."}
    geo.append(annular_cylinder_def(coll["name"], "W", coll["r_inner"], coll["r_max"], coll["z_center"] - coll["hz"], coll["z_center"] + coll["hz"]))
    geo.append(place(coll["name"], 0, 0, 0))
    det_add_scint(det, coll["name"] + "_SD", coll["name"], coll["name"], thr=0.001)
    masses.append(MassRow("collimator", coll["name"], "W", annular_volume_cm3(coll["r_inner"], coll["r_max"], 2.0 * coll["hz"]), coll["basis"]))

    write_text(GEO, "".join(geo))
    write_text(DET, "".join(det))
    setup = f"""Name {MODEL}
Version 1
Include {MODEL}.geo
Include {MODEL}.det
SurroundingSphere 40 0 0 -3 40
"""
    write_text(SETUP, setup)

    windows = [
        {"name": sample_window["name"], "material": sample_window["mat"], "z_center": sample_window["zc"], "thick": sample_window["thick"], "r_max": sample_window["r"], "basis": sample_window["basis"]},
        {"name": be["name"], "material": be["mat"], "z_center": be["zc"], "thick": be["thick"], "r_max": be["r"], "basis": be["basis"]},
    ]
    bounds = {
        "UNITS": "cm",
        "VERSION": "ADR_v5_midmass_csi_demo",
        "DESIGN_NOTE": "Reviewed demo: MidMass local ADR/TES detector-head mass model with segmented oxygen-free CsI(Tl) active well. Engineering background model, not final CAD.",
        "TES_LAYERS": [{"z_center": z, "r_max": eff_r, "hz": pix_z / 2.0} for z in z_tes_centers],
        "SUBSTRATES": [{"name": f"Substrate_L{l}", "z_center": z_sub_centers[l], "hz": sub_h / 2.0, "r_max": sub_r} for l in range(n_layers)],
        "COLD_PLATES": plates,
        "SAMPLE_BOX": sample_box | {"window": sample_window},
        "OPEN_BOTTOM_CANS": [nb_can | {"window": None, "nominal_aperture_policy": "open_aperture_no_continuous_Nb_foil"}],
        "CRYOSTAT_SHELLS": shells,
        "MIDMASS_PROXIES": dense_rings + service_boxes,
        "ACTIVE_SHIELD": active,
        "ACTIVE_SHIELD_SEGMENTS": active_segments,
        "OUTER_MECHANICAL_SHELL": outer,
        "WINDOWS": windows,
        "COLLIMATOR": coll,
        "META": {
            "length_unit": "cm",
            "source_design_unit": "cm",
            "N_LAYERS": n_layers,
            "n_pixels_per_layer": len(pix_xy),
            "tes_pixel_thickness_cm": pix_z,
            "tes_top_cm": z_tes_top,
            "be_window_radius_reference_cm": entrance_r,
            "all_axial_holes_match_be_window": True,
            "active_material_nominal": "CsI(Tl) represented as pure CsI",
            "nominal_veto_threshold_keV": active["nominal_veto_threshold_keV"],
            "threshold_scan_keV": active["threshold_scan_keV"],
            "science_beam_z_cm": 16.051,
            "science_beam_radius_cm": 1.8,
            "review_drivers": [
                "P1 passive detector-head mass closure",
                "P2 oxygen-free segmented active shield",
                "open Nb can aperture nominal; continuous Nb foil as systematic only",
                "open 4K/50K shield apertures nominal; thin foil as systematic only",
            ],
            "claim_level": "DEMO_MIDMASS_ENGINEERING_BACKGROUND_MODEL_NOT_FINAL_CAD",
        },
    }
    write_text(BOUNDS, json.dumps(bounds, indent=2, ensure_ascii=False) + "\n")

    write_mass_budget(masses)
    write_wrl(bounds)
    write_png(bounds)
    validation = validate(bounds, masses, require_final_docs=False)
    write_report(bounds, masses, validation)
    write_readme(validation)
    validation = validate(bounds, masses, require_final_docs=True)
    write_report(bounds, masses, validation)
    write_readme(validation)
    write_text(VALIDATION, json.dumps(validation, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": validation["status"], "outputs": str(OUT.relative_to(DEMO))}, indent=2))
    return validation


def add_collimator_grid(geo: list[str], coll: dict[str, float]) -> None:
    r = coll["r_max"]
    pitch = coll["pitch"]
    web = coll["web"]
    hz = coll["hz"]
    vac_h = r + pitch
    geo.append(brik_def("CollimatorVac", "Vacuum", vac_h, vac_h, hz, vis=0))
    geo.append(place("CollimatorVac", 0, 0, coll["z_center"], vis=0))
    geo.append(brik_def("CollBarX", "W", vac_h, web / 2.0, hz))
    geo.append(brik_def("CollBarY", "W", web / 2.0, vac_h, hz))
    n = int(math.ceil(r / pitch)) + 2
    idx = 0
    for k in range(-n, n + 1):
        pos = (k + 0.5) * pitch
        if abs(pos) > r:
            continue
        geo.append(f"CollBarX.Copy CollBarX_{idx:04d}\n")
        geo.append(place(f"CollBarX_{idx:04d}", 0, pos, 0, "CollimatorVac"))
        geo.append(f"CollBarY.Copy CollBarY_{idx:04d}\n")
        geo.append(place(f"CollBarY_{idx:04d}", pos, 0, 0, "CollimatorVac"))
        idx += 1


def write_mass_budget(masses: list[MassRow]) -> None:
    rows = [m.as_dict() for m in masses]
    fields = list(rows[0])
    with MASS_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    groups: dict[str, float] = {}
    for row in rows:
        groups[row["category"]] = groups.get(row["category"], 0.0) + float(row["mass_kg"])
    payload = {"rows": rows, "group_mass_kg": groups, "total_mass_kg": sum(float(r["mass_kg"]) for r in rows)}
    MASS_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[OK] wrote {MASS_CSV.relative_to(DEMO)}")
    print(f"[OK] wrote {MASS_JSON.relative_to(DEMO)}")


def vrml_color(material: str, name: str) -> tuple[float, float, float, float]:
    if "Window" in name or name.startswith("Win_"):
        return 0.70, 0.35, 0.64, 0.25
    if material == "Copper":
        return 0.75, 0.43, 0.18, 0.35
    if material == "Aluminium":
        return 0.70, 0.70, 0.70, 0.70
    if material == "Nb":
        return 0.30, 0.78, 0.85, 0.55
    if material == "CsI":
        return 0.30, 0.55, 0.85, 0.70
    if material == "Cryoperm":
        return 0.22, 0.30, 0.58, 0.45
    if material == "LowCarbonSteel":
        return 0.30, 0.30, 0.30, 0.50
    if material == "Be":
        return 0.82, 0.76, 0.42, 0.18
    if material == "Ta":
        return 0.85, 0.20, 0.20, 0.40
    return 0.55, 0.55, 0.55, 0.60


def cylinder_node(name: str, radius: float, z0: float, z1: float, material: str) -> str:
    zc = 0.5 * (z0 + z1)
    height = max(z1 - z0, 1.0e-5)
    r, g, b, t = vrml_color(material, name)
    return f"""# {name}
Transform {{
  translation 0 0 {fmt(zc)}
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


def write_wrl(bounds: dict[str, Any]) -> None:
    lines = ["#VRML V2.0 utf8", 'WorldInfo { title "NEW_GEO_RE reviewed MidMass CsI demo" }', ""]
    active = bounds["ACTIVE_SHIELD"]
    lines.append(cylinder_node("CsI_ActiveShield_envelope_segmented", active["r_out"], active["z_out_bot"], active["z_out_top"], "CsI"))
    outer = bounds["OUTER_MECHANICAL_SHELL"]
    lines.append(cylinder_node(outer["name"], outer["r_out"], outer["z_out_bot"], outer["z_out_top"], outer["mat"]))
    for shell in bounds["CRYOSTAT_SHELLS"]:
        lines.append(cylinder_node(shell["name"], shell["r_out"], shell["z_out_bot"], shell["z_out_top"], shell["mat"]))
    for can in bounds["OPEN_BOTTOM_CANS"]:
        lines.append(cylinder_node(can["name"], can["r_out"], can["z_in_bot"], can["z_out_top"], can["mat"]))
    for rec in bounds["MIDMASS_PROXIES"]:
        if "r_out" in rec:
            z0 = rec.get("z_out_bot", rec.get("z0", rec.get("z_in_bot")))
            z1 = rec.get("z_out_top", rec.get("z1", rec.get("z_in_top")))
            lines.append(cylinder_node(rec["name"], rec["r_out"], z0, z1, rec["mat"]))
    s = bounds["SAMPLE_BOX"]
    lines.append(cylinder_node(s["name"], s["r_out"], s["z_out_bot"], s["z_out_top"], s["mat"]))
    for p in bounds["COLD_PLATES"]:
        lines.append(cylinder_node(p["name"], p["r"], p["zc"] - p["h"] / 2.0, p["zc"] + p["h"] / 2.0, p["mat"]))
    for i, layer in enumerate(bounds["TES_LAYERS"]):
        lines.append(cylinder_node(f"TES_L{i}_active_envelope", layer["r_max"], layer["z_center"] - layer["hz"], layer["z_center"] + layer["hz"], "Ta"))
    for window in bounds["WINDOWS"]:
        lines.append(cylinder_node(window["name"], window["r_max"], window["z_center"] - window["thick"] / 2.0, window["z_center"] + window["thick"] / 2.0, window["material"]))
    col = bounds["COLLIMATOR"]
    lines.append(cylinder_node(col["name"], col["r_max"], col["z_center"] - col["hz"], col["z_center"] + col["hz"], "W"))
    write_text(WRL, "\n".join(lines) + "\n")


def rect(ax: Any, x: float, z: float, w: float, h: float, color: str, alpha: float = 0.45, zorder: int = 1) -> None:
    ax.add_patch(Rectangle((x, z), w, h, facecolor=color, edgecolor=color, lw=0.6, alpha=alpha, zorder=zorder))


def shell_patch(ax: Any, rec: dict[str, Any], name: str, color: str, alpha: float = 0.35, label_right: bool = True) -> None:
    rin = float(rec["r_in"])
    rout = float(rec["r_out"])
    z0 = float(rec.get("z_out_bot", rec.get("z0", rec.get("z_in_bot"))))
    z1 = float(rec.get("z_out_top", rec.get("z1", rec.get("z_in_top"))))
    zin0 = float(rec.get("z_in_bot", z0))
    zin1 = float(rec.get("z_in_top", z1))
    hole = float(rec.get("hole", rin))
    rect(ax, -rout, z0, rout - rin, z1 - z0, color, alpha)
    rect(ax, rin, z0, rout - rin, z1 - z0, color, alpha)
    if zin0 > z0:
        rect(ax, -rout, z0, 2 * rout, zin0 - z0, color, alpha)
    if z1 > zin1:
        rect(ax, -rout, zin1, rout - hole, z1 - zin1, color, alpha)
        rect(ax, hole, zin1, rout - hole, z1 - zin1, color, alpha)
    if label_right:
        ax.text(rout + 0.35, 0.5 * (z0 + z1), name, fontsize=7, va="center")


def write_png(bounds: dict[str, Any]) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(13.5, 9.2), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, width_ratios=[1.65, 1.0])
    ax = fig.add_subplot(gs[:, 0])
    ax_xy = fig.add_subplot(gs[0, 1])
    ax_mass = fig.add_subplot(gs[1, 1])

    ax.set_title("Reviewed MidMass CsI demo: X-Z projection")
    ax.set_xlabel("X / cm")
    ax.set_ylabel("Z / cm")
    shell_patch(ax, bounds["ACTIVE_SHIELD"], "segmented CsI active well", COLORS["CsI"], 0.26)
    shell_patch(ax, bounds["OUTER_MECHANICAL_SHELL"], "outer Al cover", COLORS["Aluminium"], 0.20, label_right=False)
    for rec in bounds["CRYOSTAT_SHELLS"]:
        shell_patch(ax, rec, rec["name"], COLORS["Aluminium"], 0.30, label_right=False)
    for rec in bounds["MIDMASS_PROXIES"]:
        if "r_out" in rec and "r_in" in rec:
            color = COLORS.get(rec["mat"], "#666666")
            if "z_in_bot" in rec:
                shell_patch(ax, rec, rec["name"], color, 0.38, label_right=False)
            else:
                rect(ax, -rec["r_out"], rec["z0"], rec["r_out"] - rec["r_in"], rec["z1"] - rec["z0"], color, 0.38, 6)
                rect(ax, rec["r_in"], rec["z0"], rec["r_out"] - rec["r_in"], rec["z1"] - rec["z0"], color, 0.38, 6)
        elif "r" in rec:
            rect(ax, -rec["r"], rec["z0"], 2 * rec["r"], rec["z1"] - rec["z0"], COLORS.get(rec["mat"], "#666666"), 0.35, 6)
    for rec in bounds["OPEN_BOTTOM_CANS"]:
        shell_patch(ax, rec, rec["name"], COLORS["Nb"], 0.44, label_right=False)
    shell_patch(ax, bounds["SAMPLE_BOX"], "TES sample box", COLORS["Copper"], 0.55)
    for p in bounds["COLD_PLATES"]:
        color = COLORS["Copper"] if p["mat"] == "Copper" else COLORS["Aluminium"]
        rect(ax, -p["r"], p["zc"] - p["h"] / 2.0, 2 * p["r"], p["h"], color, 0.55, 8)
        ax.text(p["r"] + 0.35, p["zc"], p["name"], fontsize=7, va="center")
    for sub in bounds["SUBSTRATES"]:
        rect(ax, -sub["r_max"], sub["z_center"] - sub["hz"], 2 * sub["r_max"], 2 * sub["hz"], COLORS["Substrate"], 0.50, 10)
    for i, layer in enumerate(bounds["TES_LAYERS"]):
        rect(ax, -layer["r_max"], layer["z_center"] - layer["hz"], 2 * layer["r_max"], 2 * layer["hz"], COLORS["TES"], 0.40, 11)
        ax.text(layer["r_max"] + 0.25, layer["z_center"], f"TES L{i}", fontsize=7, color="#8E2F2E", va="center")
    for win in bounds["WINDOWS"]:
        h = max(float(win["thick"]), 0.035)
        rect(ax, -win["r_max"], win["z_center"] - h / 2.0, 2 * win["r_max"], h, COLORS["Window"], 0.65, 12)
        ax.text(win["r_max"] + 0.3, win["z_center"], win["name"], fontsize=7, va="center")
    col = bounds["COLLIMATOR"]
    rect(ax, -col["r_max"], col["z_center"] - col["hz"], col["r_max"] - col["r_inner"], 2 * col["hz"], COLORS["Collimator"], 0.65, 13)
    rect(ax, col["r_inner"], col["z_center"] - col["hz"], col["r_max"] - col["r_inner"], 2 * col["hz"], COLORS["Collimator"], 0.65, 13)
    src_z = bounds["META"]["science_beam_z_cm"]
    src_r = bounds["META"]["science_beam_radius_cm"]
    ax.plot([-src_r, src_r], [src_z, src_z], color=COLORS["Source"], lw=2.2, zorder=20)
    ax.annotate(f"source plane z={src_z:g} cm", xy=(src_r, src_z), xytext=(src_r + 1.1, src_z + 0.9), arrowprops={"arrowstyle": "->", "lw": 0.9, "color": COLORS["Source"]}, fontsize=7, color=COLORS["Source"])
    ax.axvline(0, color="0.45", lw=0.5, ls=":")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-16.5, 18.5)
    ax.set_ylim(-23.0, 17.2)
    ax.grid(True, lw=0.35, alpha=0.22)
    ax.legend(handles=[
        Patch(facecolor=COLORS["CsI"], alpha=0.3, label="segmented CsI active well"),
        Patch(facecolor=COLORS["Cryoperm"], alpha=0.4, label="added magnetic/midmass proxies"),
        Patch(facecolor=COLORS["Aluminium"], alpha=0.3, label="Al cryostat/outer shells"),
        Patch(facecolor=COLORS["Nb"], alpha=0.4, label="Nb can"),
        Patch(facecolor=COLORS["TES"], alpha=0.4, label="Ta TES"),
        Patch(facecolor=COLORS["Copper"], alpha=0.5, label="Cu detector-head mass"),
    ], loc="lower left", fontsize=7)

    ax_xy.set_title("Active shield segmentation")
    ax_xy.add_patch(Circle((0, 0), bounds["ACTIVE_SHIELD"]["r_out"], facecolor="#E8F2FF", edgecolor="#245A8D", lw=0.8))
    ax_xy.add_patch(Circle((0, 0), bounds["ACTIVE_SHIELD"]["r_in"], facecolor="white", edgecolor="#245A8D", lw=0.8, ls="--"))
    for seg in bounds["ACTIVE_SHIELD_SEGMENTS"]:
        if seg["part"] == "side":
            phi = math.radians(seg["phi0_deg"])
            ax_xy.plot([0, bounds["ACTIVE_SHIELD"]["r_out"] * math.cos(phi)], [0, bounds["ACTIVE_SHIELD"]["r_out"] * math.sin(phi)], color="#245A8D", lw=0.6)
    ax_xy.set_xlim(-15, 15)
    ax_xy.set_ylim(-15, 15)
    ax_xy.set_aspect("equal")
    ax_xy.grid(True, lw=0.3, alpha=0.2)
    ax_xy.set_xlabel("X / cm")
    ax_xy.set_ylabel("Y / cm")

    rows = json.loads(MASS_JSON.read_text(encoding="utf-8"))
    group = rows["group_mass_kg"]
    labels = ["active", "midmass", "core passive", "outer"]
    vals = [
        sum(v for k, v in group.items() if k.startswith("active_shield")),
        group.get("midmass_proxy", 0.0) + group.get("service_proxy", 0.0),
        rows["total_mass_kg"] - sum(v for k, v in group.items() if k.startswith("active_shield")) - group.get("midmass_proxy", 0.0) - group.get("service_proxy", 0.0) - group.get("outer_shell", 0.0),
        group.get("outer_shell", 0.0),
    ]
    ax_mass.set_title("Mass budget by group")
    ax_mass.bar(labels, vals, color=["#6FA8DC", "#516C9D", "#C7813A", "#BBBBBB"])
    ax_mass.set_ylabel("kg")
    ax_mass.tick_params(axis="x", labelrotation=25)
    for i, v in enumerate(vals):
        ax_mass.text(i, v, f"{v:.1f}", ha="center", va="bottom", fontsize=8)

    fig.suptitle("NEW_GEO_RE reviewed demo mass model: MidMass CsI nominal")
    fig.savefig(PNG, dpi=220)
    print(f"[OK] wrote {PNG.relative_to(DEMO)}")


def parse_homogeneous_volume_count() -> int:
    text = GEO.read_text(encoding="utf-8")
    return len(re.findall(r"^Volume\s+", text, flags=re.M))


def defined_geo_volumes() -> set[str]:
    text = GEO.read_text(encoding="utf-8")
    return set(re.findall(r"^Volume\s+(\S+)", text, flags=re.M))


def validate_geometry_references() -> list[str]:
    problems: list[str] = []
    defined = defined_geo_volumes()
    defined.add("WorldVolume")
    geo_text = GEO.read_text(encoding="utf-8")
    det_text = DET.read_text(encoding="utf-8")
    for line in geo_text.splitlines():
        line = line.strip()
        if ".Mother " in line:
            child, mother = line.split(".Mother ", 1)
            if mother.strip() not in defined:
                problems.append(f"{child} has undefined mother {mother.strip()}")
    for line in det_text.splitlines():
        line = line.strip()
        if ".SensitiveVolume " in line or ".DetectorVolume " in line:
            _prefix, vol = line.split(None, 1)
            vol = vol.strip()
            if vol not in defined:
                problems.append(f"detector map references undefined volume {vol}")
    if "Material CsI" not in MATERIALS.read_text(encoding="utf-8"):
        problems.append("Materials file does not define CsI")
    return problems


def validate(bounds: dict[str, Any], masses: list[MassRow], require_final_docs: bool) -> dict[str, Any]:
    rows = [m.as_dict() for m in masses]
    group: dict[str, float] = {}
    for row in rows:
        group[row["category"]] = group.get(row["category"], 0.0) + float(row["mass_kg"])
    active_mass = sum(v for k, v in group.items() if k.startswith("active_shield"))
    passive_mass = sum(row["mass_kg"] for row in rows if not row["category"].startswith("active_shield"))
    midmass = group.get("midmass_proxy", 0.0) + group.get("service_proxy", 0.0)
    problems: list[str] = []
    if bounds["UNITS"] != "cm":
        problems.append("bounds unit is not cm")
    if abs(bounds["META"]["be_window_radius_reference_cm"] - 1.898) > 1.0e-9:
        problems.append("Be radius drifted from 1.898 cm")
    active = bounds["ACTIVE_SHIELD"]
    if active["mat"] != "CsI":
        problems.append("active shield is not nominal CsI")
    if abs(active["side_thickness"] - 4.0) > 1.0e-9 or abs(active["bottom_thickness"] - 8.0) > 1.0e-9 or abs(active["top_thickness"] - 2.0) > 1.0e-9:
        problems.append("active shield dimensions do not match review nominal")
    if len([s for s in bounds["ACTIVE_SHIELD_SEGMENTS"] if s["part"] == "side"]) != 8:
        problems.append("side segmentation is not 8 panels")
    if len([s for s in bounds["ACTIVE_SHIELD_SEGMENTS"] if s["part"] == "bottom"]) != 4:
        problems.append("bottom segmentation is not 4 panels")
    if len([s for s in bounds["ACTIVE_SHIELD_SEGMENTS"] if s["part"] == "top"]) != 8:
        problems.append("top segmentation is not 8 panels")
    if any(w["name"] == "Win_Nb_SC_Detector_Can" for w in bounds["WINDOWS"]):
        problems.append("nominal demo still includes continuous Nb window")
    if any(w["name"] in ("Win_4K_Al_Shield", "Win_50K_Al_Shield") for w in bounds["WINDOWS"]):
        problems.append("nominal demo still includes continuous 4K/50K Al windows")
    if not (12.0 <= passive_mass <= 30.0):
        problems.append(f"passive mass {passive_mass:.2f} kg is outside MidMass target range 12-30 kg")
    if midmass < 7.0:
        problems.append(f"added midmass proxy only {midmass:.2f} kg")
    if not (60.0 <= active_mass <= 70.0):
        problems.append(f"active CsI mass {active_mass:.2f} kg is outside expected 60-70 kg")
    for path in (GEO, DET, SETUP, MATERIALS, INTRO, BOUNDS, MASS_CSV, MASS_JSON, WRL, PNG):
        if not path.exists():
            problems.append(f"missing artifact {path.relative_to(DEMO)}")
    if require_final_docs:
        for path in (REPORT, README):
            if not path.exists() or path.stat().st_size <= 0:
                problems.append(f"missing artifact {path.relative_to(DEMO)}")
    problems.extend(validate_geometry_references())
    volume_count = parse_homogeneous_volume_count()
    if volume_count < 55:
        problems.append(f"unexpectedly low volume count {volume_count}")
    return {
        "status": "PASS" if not problems else "FAIL",
        "problems": problems,
        "checks": {
            "volume_count": volume_count,
            "passive_mass_kg": passive_mass,
            "active_mass_kg": active_mass,
            "midmass_proxy_mass_kg": midmass,
            "total_mass_kg": passive_mass + active_mass,
            "active_side_segments": len([s for s in bounds["ACTIVE_SHIELD_SEGMENTS"] if s["part"] == "side"]),
            "active_bottom_segments": len([s for s in bounds["ACTIVE_SHIELD_SEGMENTS"] if s["part"] == "bottom"]),
            "active_top_segments": len([s for s in bounds["ACTIVE_SHIELD_SEGMENTS"] if s["part"] == "top"]),
            "nominal_open_nb_aperture": not any(w["name"] == "Win_Nb_SC_Detector_Can" for w in bounds["WINDOWS"]),
            "nominal_open_thermal_shield_apertures": not any(w["name"] in ("Win_4K_Al_Shield", "Win_50K_Al_Shield") for w in bounds["WINDOWS"]),
            "geometry_reference_problems": len(validate_geometry_references()),
        },
    }


def write_report(bounds: dict[str, Any], masses: list[MassRow], validation: dict[str, Any]) -> None:
    rows = [m.as_dict() for m in masses]
    group: dict[str, float] = {}
    for row in rows:
        group[row["category"]] = group.get(row["category"], 0.0) + float(row["mass_kg"])
    active_mass = sum(v for k, v in group.items() if k.startswith("active_shield"))
    passive_mass = sum(row["mass_kg"] for row in rows if not row["category"].startswith("active_shield"))
    midmass = group.get("midmass_proxy", 0.0) + group.get("service_proxy", 0.0)
    lines = [
        "# Reviewed Demo Mass Model Summary",
        "",
        "## Status",
        "",
        f"- Validation status: **{validation['status']}**",
        f"- Claim level: `{bounds['META']['claim_level']}`",
        "- This is an engineering Geant4/Cosima background mass model, not a fabrication-ready cryostat CAD design.",
        "",
        "## Review Requirements Addressed",
        "",
        "- Nominal active shield is an oxygen-free segmented CsI(Tl) well, represented as pure CsI for mass and activation stoichiometry.",
        "- Active shield dimensions follow the review nominal: side 4.0 cm, bottom 8.0 cm, top annulus 2.0 cm, entrance aperture 1.898 cm.",
        "- Shield is split into 8 side panels, 4 bottom panels, and 8 top-annulus panels so hit maps can distinguish side/bottom/top regions.",
        "- The continuous Nb detector-can foil and the continuous 4K/50K Al aperture foils are removed from the nominal demo; they remain recommended systematic cases.",
        "- Nearby cryogenic hardware proxies are added: ADR coil, Fe yoke, salt-pill proxy, Cryoperm magnetic shield, thermal bus, vacuum reinforcement/flanges, cold-head interface, readout and harness proxies.",
        "- The overlap-prone crossing-bar W grid from the reviewed geometry is replaced by an overlap-safe annular W aperture stop; it is still only a passive entrance-aperture proxy, not a Laue optic.",
        "",
        "## Review Reconciliation",
        "",
        "- The bilingual HTML review is conservative about publication heritage and asks for BGO as a reference/control case, A4K/Cryoperm systematics, missing-mass envelopes, open internal apertures, and a W-grid overlap fix.",
        "- The later MD logs emphasize the oxygen-activation risk of BGO near a 511 keV line and recommend CsI(Tl) as the nominal oxygen-suppressed active well, with BGO and CeBr3 retained as comparison/systematic cases.",
        "- This demo follows the later CsI(Tl) nominal recommendation because the requested task is to build a new, more reasonable mass model, while preserving the HTML review's BGO/CeBr3 recommendation as required follow-up systematics rather than deleting it.",
        "",
        "## Key Numbers",
        "",
        f"- Active CsI mass: `{active_mass:.3f} kg`.",
        f"- Passive mass including outer shell and midmass proxies: `{passive_mass:.3f} kg`.",
        f"- Added midmass/service proxy mass: `{midmass:.3f} kg`.",
        f"- Total modeled local mass: `{active_mass + passive_mass:.3f} kg`.",
        f"- Current Be-window convention retained: radius `{bounds['META']['be_window_radius_reference_cm']:.3f} cm`, thickness `0.015 cm`.",
        f"- Nominal analysis veto threshold: `{bounds['ACTIVE_SHIELD']['nominal_veto_threshold_keV']:.0f} keV`; threshold scan `{bounds['ACTIVE_SHIELD']['threshold_scan_keV']}`.",
        "",
        "## Mass Budget By Category",
        "",
        "| category | mass kg |",
        "| --- | ---: |",
    ]
    for key in sorted(group):
        lines.append(f"| `{key}` | {group[key]:.3f} |")
    lines.extend([
        "",
        "## Main Generated Artifacts",
        "",
        f"- Geometry setup: `{SETUP.relative_to(DEMO)}`",
        f"- Geometry body: `{GEO.relative_to(DEMO)}`",
        f"- Detector map: `{DET.relative_to(DEMO)}`",
        f"- Machine-readable bounds: `{BOUNDS.relative_to(DEMO)}`",
        f"- Mass budget: `{MASS_CSV.relative_to(DEMO)}` and `{MASS_JSON.relative_to(DEMO)}`",
        f"- WRL visualization: `{WRL.relative_to(DEMO)}`",
        f"- 2D schematic: `{PNG.relative_to(DEMO)}`",
        f"- Validation: `{VALIDATION.relative_to(DEMO)}`",
        "",
        "## Remaining Required Physics Work",
        "",
        "- This demo has not rerun prompt or delayed activation transport. Any production use requires Step02/Step03 reruns with the new material map.",
        "- Cs/I activation products, shield self-veto, timing/dead time, and threshold scans must be evaluated before quoting new background or 3-sigma performance numbers.",
        "- BGO reference, CeBr3 oxygen-free performance, hybrid CsI/BGO, A4K/Cryoperm, open/foil window, and passive-mass Low/Mid/Full cases should remain systematic variations.",
        "- Laue optics hardware mass is still not included in this local detector-head demo.",
        "",
        "## Paper-Safe Wording",
        "",
        "Use: `a reviewed MidMass engineering ADR/TES detector-head mass model with a segmented oxygen-free CsI(Tl) active well`.",
        "",
        "Avoid: `final cryostat mechanical design`, `optimized active shield`, or `complete ADR payload mass model`.",
        "",
    ])
    write_text(REPORT, "\n".join(lines))


def write_readme(validation: dict[str, Any]) -> None:
    text = f"""# Demo Reviewed Mass Model

This directory contains a standalone reviewed demo geometry generated by:

```bash
python3 build_demo_mass_model.py
```

Current validation status: **{validation['status']}**.

Primary outputs are under `outputs/`, including the `.geo.setup`, `.geo`,
`.det`, `bounds.json`, mass budget CSV/JSON, WRL visualization, 2D schematic,
and `mass_model_summary.md`.
"""
    write_text(README, text)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    validation = build_geometry()
    return 0 if validation["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
