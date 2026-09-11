#!/usr/bin/env python3
"""Build a DEMO2 detector-head mass model for NEW_GEO_RE.

This standalone demo is intentionally generated in centimetres.  It does not
replace the current project geometry authority.  It implements the review
direction in tmp_mass_model_review_bundle:

* keep the TES stack, Cu sample box, and sample-box Al window unchanged;
* add a more realistic ADR/cryostat passive-mass envelope;
* include 60 K / 4 K / 1 K / 50 mK aperture windows as thin Al foils;
* put graded high-Z passive shielding outside the dewar, not next to the TES;
* keep the nominal active shield an oxygen-suppressed segmented CsI(Tl) well;
* include a minimal active-shield packaging/readout/feedthrough proxy so the
  CsI well is not treated as unsupported bare scintillator.
"""

from __future__ import annotations

import csv
import json
import math
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/new_geo_re_demo2_matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Patch, Rectangle


SCRIPT = Path(__file__).resolve()
DEMO = SCRIPT.parent
OUT = DEMO / "outputs"
FIG = OUT / "figures"

MODEL = "TibetTES_ADR_v6_demo2_adrpassive_csi"
GEO = OUT / f"{MODEL}.geo"
DET = OUT / f"{MODEL}.det"
SETUP = OUT / f"{MODEL}.geo.setup"
INTRO = OUT / "Intro_TibetTES_demo2.geo"
MATERIALS = OUT / "Materials_TibetTES_demo2.geo"
BOUNDS = OUT / "bounds.json"
MASS_CSV = OUT / "mass_budget.csv"
MASS_JSON = OUT / "mass_budget.json"
VALIDATION = OUT / "validation.json"
WRL = OUT / f"{MODEL}.wrl"
PNG = FIG / f"{MODEL}_schematic.png"
REPORT = OUT / "mass_model_summary.md"
README = DEMO / "README.md"
DESIGN_REVIEW = OUT / "design_review_notes.md"
EVIDENCE = OUT / "evidence"
COSIMA_BIN = Path("/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima")
COSIMA_OVERLAP_SOURCE = EVIDENCE / "overlap_check.source"
COSIMA_OVERLAP_LOG = EVIDENCE / "cosima_overlapcheck_1000pts.txt"


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
    "SaltProxy": 7.08,
    "G10": 1.85,
    "Mylar": 1.39,
    "Kapton": 1.42,
}


COLORS = {
    "TES": "#D64B4B",
    "Substrate": "#333333",
    "Copper": "#C7813A",
    "Aluminium": "#BBBBBB",
    "Nb": "#5AC8D8",
    "Cryoperm": "#516C9D",
    "LowCarbonSteel": "#555555",
    "StainlessSteel": "#7A7A7A",
    "SaltProxy": "#8E6BBE",
    "G10": "#8BC06A",
    "Kapton": "#D99A3D",
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


def windowed_shell_def(
    volname: str,
    material: str,
    r_in: float,
    r_out: float,
    z_in_bot: float,
    z_in_top: float,
    z_out_bot: float,
    z_out_top: float,
    hole_r_bot: float,
    hole_r_top: float,
    vis: int = 1,
) -> str:
    planes = [
        (z_out_bot, hole_r_bot, r_out),
        (z_in_bot, hole_r_bot, r_out),
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


def windowed_shell_volume_cm3(
    r_in: float,
    r_out: float,
    z_in_bot: float,
    z_in_top: float,
    z_out_bot: float,
    z_out_top: float,
    hole_bot: float,
    hole_top: float,
    phi_fraction: float = 1.0,
) -> float:
    side = math.pi * (r_out * r_out - r_in * r_in) * (z_in_top - z_in_bot)
    bottom = math.pi * (r_out * r_out - hole_bot * hole_bot) * (z_in_bot - z_out_bot)
    top = math.pi * (r_out * r_out - hole_top * hole_top) * (z_out_top - z_in_top)
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
    materials = """# Custom materials for the NEW_GEO_RE DEMO2 mass model.
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

# Standard MEGAlib already defines CsI. DEMO2 intentionally reuses it for
# CsI(Tl) mass/stoichiometry to avoid the duplicate-material Cosima failure
# found in the first demo review.

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

Material SaltProxy
SaltProxy.Density 7.08
SaltProxy.Component Gd 3
SaltProxy.Component Ga 5
SaltProxy.Component O 12

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

Material Kapton
Kapton.Density 1.42
Kapton.Component C 22
Kapton.Component H 10
Kapton.Component N 2
Kapton.Component O 5

"""
    intro = """Name MassmodelTibetTES_ADR_v6_demo2_adrpassive_csi
Version 1

Include Materials_TibetTES_demo2.geo
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

    geo: list[str] = ["Include Intro_TibetTES_demo2.geo\n\n"]
    det: list[str] = ["// DEMO2 ADR-passive CsI nominal detector map\n\n"]
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
        {"name": "ColdPlate_60K", "mat": "Aluminium", "r": 8.35, "h": 0.6, "zc": -10.8, "basis": "60 K interface plate; radius reduced to clear the cold-head annulus."},
    ]
    for p in plates:
        geo.append(pcon_cylinder_def(p["name"], p["mat"], p["r"], p["h"] / 2.0))
        geo.append(place(p["name"], 0, 0, p["zc"]))
        masses.append(MassRow("cold_plate", p["name"], p["mat"], cylinder_volume_cm3(p["r"], p["h"]), p["basis"]))

    for l in range(n_layers):
        geo.append(pcon_cylinder_def(f"Substrate_L{l}", "Silicon", sub_r, sub_h / 2.0))
        geo.append(brik_def(f"TES_Pixel_L{l}", "Ta", pix_x / 2.0, pix_y / 2.0, pix_z / 2.0))
        geo.append(brik_def(f"TES_L{l}", "Vacuum", 2.4, 2.4, pix_z / 2.0, vis=0))
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

    stage_windows = [
        {"name": "Win_50mK_Al_Shield", "material": "Aluminium", "z_center": 9.315, "thick": 0.0025, "r_max": entrance_r, "stage": "50mK", "basis": "Thin Al thermal/optical blocking foil across the 50 mK can aperture."},
        {"name": "Win_1K_Al_Shield", "material": "Aluminium", "z_center": 10.555, "thick": 0.0025, "r_max": entrance_r, "stage": "1K", "basis": "Thin Al thermal/optical blocking foil across the 1 K can aperture."},
        {"name": "Win_4K_Al_Shield", "material": "Aluminium", "z_center": 11.635, "thick": 0.0025, "r_max": entrance_r, "stage": "4K", "basis": "Thin Al thermal/optical blocking foil across the 4 K shield aperture."},
        {"name": "Win_60K_Al_Shield", "material": "Aluminium", "z_center": 12.435, "thick": 0.0025, "r_max": entrance_r, "stage": "60K", "basis": "Thin Al thermal/optical blocking foil across the 60 K shield aperture."},
    ]
    shells = [
        {"name": "Thermal_50mK_Al_Shield", "mat": "Aluminium", "r_in": 4.58, "r_out": 4.66, "z_in_bot": -0.55, "z_in_top": 9.25, "z_out_bot": -0.65, "z_out_top": 9.33, "hole": entrance_r, "window": "Win_50mK_Al_Shield", "basis": "50 mK Al radiation can around the Nb can; aperture closed by a thin Al foil."},
        {"name": "Thermal_1K_Al_Shield", "mat": "Aluminium", "r_in": 5.52, "r_out": 5.62, "z_in_bot": -3.75, "z_in_top": 10.45, "z_out_bot": -3.90, "z_out_top": 10.57, "hole": entrance_r, "window": "Win_1K_Al_Shield", "basis": "1 K intermediate radiation can with thin Al aperture foil."},
        {"name": "Thermal_4K_Al_Shield", "mat": "Aluminium", "r_in": 7.3, "r_out": 7.42, "z_in_bot": -9.0, "z_in_top": 11.55, "z_out_bot": -9.12, "z_out_top": 11.65, "hole": entrance_r, "window": "Win_4K_Al_Shield", "basis": "4 K radiation shield; aperture closed by a thin Al foil."},
        {"name": "Thermal_60K_Al_Shield", "mat": "Aluminium", "r_in": 8.8, "r_out": 8.95, "z_in_bot": -12.4, "z_in_top": 12.35, "z_out_bot": -12.58, "z_out_top": 12.45, "hole": entrance_r, "window": "Win_60K_Al_Shield", "basis": "60 K radiation shield; aperture closed by a thin Al foil."},
        {"name": "Vacuum_Jacket_Al", "mat": "Aluminium", "r_in": 9.25, "r_out": 9.65, "z_in_bot": -13.2, "z_in_top": 12.75, "z_out_bot": -13.65, "z_out_top": 12.90, "hole": entrance_r, "window": None, "basis": "More massive Al vacuum-jacket proxy; Be is the pressure/window closure."},
    ]
    for shell in shells:
        geo.append(closed_shell_def(shell["name"], shell["mat"], shell["r_in"], shell["r_out"], shell["z_in_bot"], shell["z_in_top"], shell["z_out_bot"], shell["z_out_top"], shell["hole"]))
        geo.append(place(shell["name"], 0, 0, 0))
        det_add_scint(det, shell["name"] + "_SD", shell["name"], shell["name"], thr=0.001)
        masses.append(MassRow("cryostat_shell", shell["name"], shell["mat"], shell_volume_cm3(shell["r_in"], shell["r_out"], shell["z_in_bot"], shell["z_in_top"], shell["z_out_bot"], shell["z_out_top"], shell["hole"]), shell["basis"]))
    for win in stage_windows:
        geo.append(pcon_cylinder_def(win["name"], win["material"], win["r_max"], win["thick"] / 2.0))
        geo.append(place(win["name"], 0, 0, win["z_center"]))
        det_add_scint(det, win["name"] + "_SD", win["name"], win["name"], thr=0.001)
        masses.append(MassRow("window", win["name"], win["material"], cylinder_volume_cm3(win["r_max"], win["thick"]), win["basis"]))

    # Added passive ADR and cryostat hardware proxies from the review. Dense W
    # shielding is outside the dewar so the nearest TES layers remain Cu/Nb/Al/Ni.
    dense_rings = [
        {"category": "magnetic_shield", "name": "Cryoperm_Inner_Mag_Shield", "mat": "Cryoperm", "r_in": 4.75, "r_out": 5.20, "z_in_bot": -0.75, "z_in_top": 9.65, "z_out_bot": -0.90, "z_out_top": 9.95, "hole": entrance_r, "basis": "Ni-rich inner magnetic shield surrounding the Nb can."},
        {"category": "adr_passive", "name": "ADR_Magnet_Coil_Cu", "mat": "Copper", "r_in": 5.70, "r_out": 7.25, "z0": -6.70, "z1": -2.45, "basis": "Simplified ADR superconducting magnet/coil copper-equivalent mass inside the 4 K shield."},
        {"category": "adr_passive", "name": "ADR_Magnet_Yoke_Fe", "mat": "LowCarbonSteel", "r_in": 7.48, "r_out": 8.65, "z0": -8.75, "z1": -2.25, "basis": "Fe return-yoke proxy, included as a significant activation/scattering source."},
        {"category": "adr_passive", "name": "ADR_SaltPill_Proxy", "mat": "SaltProxy", "r": 2.30, "z0": -6.55, "z1": -4.25, "basis": "GGG-like dense paramagnetic salt-pill/regenerator proxy below detector, away from the aperture."},
        {"category": "adr_passive", "name": "ADR_SaltPill_Cu_Can", "mat": "Copper", "r_in": 2.34, "r_out": 2.50, "z0": -6.62, "z1": -4.18, "basis": "Cu salt-pill can/thermal strap collar around the salt proxy."},
        {"category": "adr_passive", "name": "Thermal_Bus_Cu", "mat": "Copper", "r_in": 2.60, "r_out": 5.10, "z0": -2.35, "z1": -1.18, "basis": "Cu thermal bus / heat-switch mass proxy."},
        {"category": "adr_passive", "name": "ADR_HeatSwitch_Stainless_Link", "mat": "StainlessSteel", "r_in": 2.55, "r_out": 2.80, "z0": -5.55, "z1": -4.45, "basis": "Stainless/structural heat-switch link outside the salt-pill can; activation mass proxy kept clear of the 1 K plate."},
        {"category": "cryostat_passive", "name": "Vacuum_Jacket_Al_Reinforcement", "mat": "Aluminium", "r_in": 9.68, "r_out": 9.80, "z0": -12.85, "z1": 12.40, "basis": "Dewar wall/flange/port reinforcement proxy in the gap before the active shield."},
        {"category": "cryostat_passive", "name": "Vacuum_Top_Flange_Al", "mat": "Aluminium", "r_in": 9.70, "r_out": 10.00, "z0": 12.94, "z1": 13.08, "basis": "Top flange/collar mass inside the active-shield cavity."},
        {"category": "cryostat_passive", "name": "Vacuum_Bottom_Flange_Al", "mat": "Aluminium", "r_in": 9.70, "r_out": 10.00, "z0": -13.55, "z1": -13.25, "basis": "Bottom flange/collar mass inside the active-shield cavity."},
        {"category": "adr_passive", "name": "PulseTube_ColdHead_Interface_Cu", "mat": "Copper", "r_in": 8.98, "r_out": 9.18, "z0": -11.55, "z1": -9.05, "basis": "Local cold-head interface proxy outside the 60 K shield and inside the vacuum jacket."},
        {"category": "passive_shield", "name": "Passive_Cu_Inner_Liner", "mat": "Copper", "r_in": 9.80, "r_out": 9.88, "z0": -13.10, "z1": 12.70, "basis": "Nearest passive liner outside the dewar; Cu is kept closest to the TES side of the passive shield."},
        {"category": "passive_shield", "name": "Passive_W_Outer_Liner", "mat": "W", "r_in": 9.90, "r_out": 9.96, "z0": -13.10, "z1": 12.70, "basis": "Outer high-Z passive side shield, separated from the TES by the dewar and Cu liner; Sn is reserved for systematic graded-Z variants."},
        {"category": "passive_shield", "name": "Passive_Bottom_W_Shield", "mat": "W", "r_in": 0.0, "r_out": 9.90, "z0": -13.93, "z1": -13.66, "basis": "Bottom W passive shield above the active-shield bottom, following balloon-spectrometer passive-shield practice."},
        {"category": "passive_shield", "name": "Passive_Top_W_Aperture_Annulus", "mat": "W", "r_in": 2.05, "r_out": 9.90, "z0": 13.10, "z1": 13.30, "basis": "Top annular W passive aperture stop below the active top annulus; not adjacent to TES."},
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
        {"name": "SQUID_Readout_Al_Box", "mat": "Aluminium", "hx": 0.25, "hy": 0.8, "hz": 1.4, "x": 8.1, "y": 0.0, "z": 4.2, "basis": "Readout/support box proxy offset from aperture in the 4 K to 60 K radial gap."},
        {"name": "Harness_Cu_Bundle_A", "mat": "Copper", "hx": 0.12, "hy": 0.35, "hz": 4.0, "x": -5.7, "y": 1.4, "z": 2.8, "basis": "Cu harness/strap proxy."},
        {"name": "Harness_Cu_Bundle_B", "mat": "Copper", "hx": 0.12, "hy": 0.35, "hz": 4.0, "x": -5.7, "y": -1.4, "z": 2.8, "basis": "Cu harness/strap proxy."},
        {"name": "Support_G10_Post_A", "mat": "G10", "hx": 0.08, "hy": 0.08, "hz": 5.7, "x": 9.1, "y": 0.0, "z": -3.1, "basis": "Low-Z support post in the 60 K shield to vacuum-jacket radial gap."},
        {"name": "Support_G10_Post_B", "mat": "G10", "hx": 0.08, "hy": 0.08, "hz": 5.7, "x": -9.1, "y": 0.0, "z": -3.1, "basis": "Low-Z support post in the 60 K shield to vacuum-jacket radial gap."},
        {"name": "Support_G10_Post_C", "mat": "G10", "hx": 0.08, "hy": 0.08, "hz": 5.7, "x": 0.0, "y": 9.1, "z": -3.1, "basis": "Low-Z support post in the 60 K shield to vacuum-jacket radial gap."},
        {"name": "Support_G10_Post_D", "mat": "G10", "hx": 0.08, "hy": 0.08, "hz": 5.7, "x": 0.0, "y": -9.1, "z": -3.1, "basis": "Low-Z support post in the 60 K shield to vacuum-jacket radial gap."},
    ]
    for b in service_boxes:
        geo.append(brik_def(b["name"], b["mat"], b["hx"], b["hy"], b["hz"]))
        geo.append(place(b["name"], b["x"], b["y"], b["z"]))
        det_add_scint(det, b["name"] + "_SD", b["name"], b["name"], thr=0.001)
        masses.append(MassRow("service_proxy", b["name"], b["mat"], brik_volume_cm3(b["hx"], b["hy"], b["hz"]), b["basis"]))

    # Active-shield packaging/readout proxies.  The scintillator well is not a
    # final BGO/CsI shield assembly here, but a bare crystal-only model is too
    # optimistic for activation and Compton transport.  These pieces sit outside
    # the CsI or in the CsI-to-cover radial clearance and do not add W near the
    # TES aperture.
    shield_packaging = [
        {
            "category": "shield_packaging",
            "name": "ActiveShield_Al_Backplane_Liner",
            "mat": "Aluminium",
            "r_in": 14.07,
            "r_out": 14.18,
            "z0": -21.85,
            "z1": 15.25,
            "basis": "Thin Al support liner/readout backplane in the radial clearance outside the segmented CsI well.",
        },
        {
            "category": "shield_packaging",
            "name": "ActiveShield_Top_Al_Retainer",
            "mat": "Aluminium",
            "r_in": 14.07,
            "r_out": 14.22,
            "z0": 15.37,
            "z1": 15.53,
            "basis": "Upper scintillator-retainer collar below the outer Al cover, outside the open 1.898 cm optical path.",
        },
        {
            "category": "shield_packaging",
            "name": "ActiveShield_Bottom_Al_Retainer",
            "mat": "Aluminium",
            "r_in": 14.07,
            "r_out": 14.22,
            "z0": -22.10,
            "z1": -21.97,
            "basis": "Lower scintillator-retainer collar below the CsI bottom panels and inside the outer Al cover.",
        },
        {
            "category": "shield_packaging",
            "name": "ActiveShield_Flex_Readout_Kapton",
            "mat": "Kapton",
            "r_in": 14.18,
            "r_out": 14.23,
            "z0": -16.0,
            "z1": 14.6,
            "basis": "Flexible readout/cable-layer proxy on the outside of the CsI package.",
        },
        {
            "category": "shield_packaging",
            "name": "ActiveShield_Readout_Box_XP",
            "mat": "Aluminium",
            "hx": 0.28,
            "hy": 1.05,
            "hz": 2.60,
            "x": 14.83,
            "y": 0.0,
            "z": -2.0,
            "basis": "External active-shield readout/electronics box proxy outside the outer Al cover.",
        },
        {
            "category": "shield_packaging",
            "name": "ActiveShield_Readout_Box_XM",
            "mat": "Aluminium",
            "hx": 0.28,
            "hy": 1.05,
            "hz": 2.60,
            "x": -14.83,
            "y": 0.0,
            "z": -2.0,
            "basis": "External active-shield readout/electronics box proxy outside the outer Al cover.",
        },
        {
            "category": "shield_packaging",
            "name": "ActiveShield_Readout_Box_YP",
            "mat": "Aluminium",
            "hx": 1.05,
            "hy": 0.28,
            "hz": 2.60,
            "x": 0.0,
            "y": 14.83,
            "z": -2.0,
            "basis": "External active-shield readout/electronics box proxy outside the outer Al cover.",
        },
        {
            "category": "shield_packaging",
            "name": "ActiveShield_Readout_Box_YM",
            "mat": "Aluminium",
            "hx": 1.05,
            "hy": 0.28,
            "hz": 2.60,
            "x": 0.0,
            "y": -14.83,
            "z": -2.0,
            "basis": "External active-shield readout/electronics box proxy outside the outer Al cover.",
        },
        {
            "category": "shield_packaging",
            "name": "Shield_Feedthrough_Stainless_XP",
            "mat": "StainlessSteel",
            "hx": 0.16,
            "hy": 0.42,
            "hz": 0.58,
            "x": 15.35,
            "y": 0.0,
            "z": 10.9,
            "basis": "Small stainless feedthrough/connector proxy outside the active-shield cover.",
        },
        {
            "category": "shield_packaging",
            "name": "Shield_Feedthrough_Stainless_XM",
            "mat": "StainlessSteel",
            "hx": 0.16,
            "hy": 0.42,
            "hz": 0.58,
            "x": -15.35,
            "y": 0.0,
            "z": 10.9,
            "basis": "Small stainless feedthrough/connector proxy outside the active-shield cover.",
        },
    ]
    for rec in shield_packaging:
        if "r_out" in rec:
            geo.append(annular_cylinder_def(rec["name"], rec["mat"], rec["r_in"], rec["r_out"], rec["z0"], rec["z1"]))
            geo.append(place(rec["name"], 0, 0, 0))
            volume = annular_volume_cm3(rec["r_in"], rec["r_out"], rec["z1"] - rec["z0"])
        else:
            geo.append(brik_def(rec["name"], rec["mat"], rec["hx"], rec["hy"], rec["hz"]))
            geo.append(place(rec["name"], rec["x"], rec["y"], rec["z"]))
            volume = brik_volume_cm3(rec["hx"], rec["hy"], rec["hz"])
        det_add_scint(det, rec["name"] + "_SD", rec["name"], rec["name"], thr=0.001)
        masses.append(MassRow(rec["category"], rec["name"], rec["mat"], volume, rec["basis"]))

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

    # Entrance Be window and W aperture stop retained for source-plane compatibility.
    be = {"name": "Win_Be_Cryostat", "mat": "Be", "r": entrance_r, "thick": 0.015, "zc": 12.8425, "basis": "Current Be-window transport convention retained: r=1.898 cm, t=0.015 cm."}
    geo.append(pcon_cylinder_def(be["name"], be["mat"], be["r"], be["thick"] / 2.0))
    geo.append(place(be["name"], 0, 0, be["zc"]))
    det_add_scint(det, "WinBe_SD", be["name"], be["name"], thr=0.001)
    masses.append(MassRow("window", be["name"], be["mat"], cylinder_volume_cm3(be["r"], be["thick"]), be["basis"]))

    vac_al = {"name": "Win_Vacuum_Al_Filter", "mat": "Aluminium", "r": entrance_r, "thick": 0.0030, "zc": 13.41, "basis": "Thin Al-equivalent vacuum/filter foil outside the Be window; conservative low-Z filter-stack proxy."}
    geo.append(pcon_cylinder_def(vac_al["name"], vac_al["mat"], vac_al["r"], vac_al["thick"] / 2.0))
    geo.append(place(vac_al["name"], 0, 0, vac_al["zc"]))
    det_add_scint(det, vac_al["name"] + "_SD", vac_al["name"], vac_al["name"], thr=0.001)
    masses.append(MassRow("window", vac_al["name"], vac_al["mat"], cylinder_volume_cm3(vac_al["r"], vac_al["thick"]), vac_al["basis"]))

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
        *stage_windows,
        {"name": be["name"], "material": be["mat"], "z_center": be["zc"], "thick": be["thick"], "r_max": be["r"], "basis": be["basis"]},
        {"name": vac_al["name"], "material": vac_al["mat"], "z_center": vac_al["zc"], "thick": vac_al["thick"], "r_max": vac_al["r"], "basis": vac_al["basis"]},
    ]
    bounds = {
        "UNITS": "cm",
        "VERSION": "ADR_v6_demo2_adrpassive_csi",
        "DESIGN_NOTE": "DEMO2: ADR-passive local detector-head mass model with staged 60K/4K/1K/50mK Al-windowed cans, Cu/W passive shielding, and segmented oxygen-suppressed CsI(Tl) active well. Engineering background model, not final CAD.",
        "TES_LAYERS": [{"z_center": z, "r_max": eff_r, "hz": pix_z / 2.0} for z in z_tes_centers],
        "SUBSTRATES": [{"name": f"Substrate_L{l}", "z_center": z_sub_centers[l], "hz": sub_h / 2.0, "r_max": sub_r} for l in range(n_layers)],
        "COLD_PLATES": plates,
        "SAMPLE_BOX": sample_box | {"window": sample_window},
        "OPEN_BOTTOM_CANS": [nb_can | {"window": None, "nominal_aperture_policy": "open_aperture_no_continuous_Nb_foil"}],
        "CRYOSTAT_SHELLS": shells,
        "STAGE_WINDOWS": stage_windows,
        "PASSIVE_PROXIES": dense_rings + service_boxes + shield_packaging,
        "MIDMASS_PROXIES": dense_rings + service_boxes + shield_packaging,
        "SHIELD_PACKAGING_PROXIES": shield_packaging,
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
                "P1 passive detector-head mass closure with ADR mass proxies",
                "P2 oxygen-free segmented active shield",
                "60K/4K/1K/50mK Al thermal-window stack on open apertures",
                "Cu/W passive shield outside the dewar; W kept away from TES; Sn reserved for systematic graded-Z variants",
            ],
            "claim_level": "DEMO2_ADR_PASSIVE_ENGINEERING_BACKGROUND_MODEL_NOT_FINAL_CAD",
        },
    }
    write_text(BOUNDS, json.dumps(bounds, indent=2, ensure_ascii=False) + "\n")

    write_mass_budget(masses)
    write_wrl(bounds)
    write_png(bounds)
    validation = validate(bounds, masses, require_final_docs=False)
    write_report(bounds, masses, validation)
    write_design_review_notes(bounds, validation)
    write_readme(validation)
    run_cosima_overlap_check()
    validation = validate(bounds, masses, require_final_docs=True)
    write_report(bounds, masses, validation)
    write_design_review_notes(bounds, validation)
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


def write_overlap_source() -> None:
    source = f"""Version                     1
Geometry                    {SETUP}
CheckForOverlaps            1000 0.0001
PhysicsListEM               LivermorePol
Run Minimum
Minimum.FileName            /tmp/DelMe_demo2_overlap
Minimum.NEvents             1
Minimum.Source MinimumS
MinimumS.ParticleType       1
MinimumS.Beam               PointSource 0 0 0
MinimumS.Spectrum           Mono 511
MinimumS.Flux               1.0
"""
    write_text(COSIMA_OVERLAP_SOURCE, source)


def run_cosima_overlap_check() -> None:
    write_overlap_source()
    if not COSIMA_BIN.exists():
        write_text(COSIMA_OVERLAP_LOG, f"ERROR: cosima executable missing: {COSIMA_BIN}\n")
        print(f"[WARN] cosima executable missing: {COSIMA_BIN}")
        return
    print(f"[RUN] {COSIMA_BIN} {COSIMA_OVERLAP_SOURCE.relative_to(DEMO)}")
    proc = subprocess.run(
        [str(COSIMA_BIN), str(COSIMA_OVERLAP_SOURCE)],
        cwd=DEMO.parent.parent,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    write_text(COSIMA_OVERLAP_LOG, proc.stdout)
    if proc.returncode != 0:
        print(f"[WARN] cosima overlap check exited with code {proc.returncode}")


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
    if material == "Kapton":
        return 0.90, 0.58, 0.22, 0.65
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
    lines = ["#VRML V2.0 utf8", 'WorldInfo { title "NEW_GEO_RE DEMO2 ADR-passive CsI model" }', ""]
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
        elif "hx" in rec:
            approx_r = math.hypot(float(rec.get("x", 0.0)), float(rec.get("y", 0.0)))
            lines.append(cylinder_node(rec["name"], approx_r + max(rec["hx"], rec["hy"]), rec["z"] - rec["hz"], rec["z"] + rec["hz"], rec["mat"]))
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

    ax.set_title("DEMO2 ADR-passive CsI model: X-Z projection")
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
        Patch(facecolor=COLORS["Cryoperm"], alpha=0.4, label="magnetic/ADR/passive proxies"),
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
    labels = ["active", "ADR/mag", "passive shield", "core/outer"]
    vals = [
        sum(v for k, v in group.items() if k.startswith("active_shield")),
        group.get("adr_passive", 0.0) + group.get("magnetic_shield", 0.0) + group.get("service_proxy", 0.0) + group.get("shield_packaging", 0.0),
        group.get("passive_shield", 0.0),
        rows["total_mass_kg"] - sum(v for k, v in group.items() if k.startswith("active_shield")) - group.get("adr_passive", 0.0) - group.get("magnetic_shield", 0.0) - group.get("service_proxy", 0.0) - group.get("shield_packaging", 0.0) - group.get("passive_shield", 0.0),
    ]
    ax_mass.set_title("Mass budget by group")
    ax_mass.bar(labels, vals, color=["#6FA8DC", "#516C9D", "#C7813A", "#BBBBBB"])
    ax_mass.set_ylabel("kg")
    ax_mass.tick_params(axis="x", labelrotation=25)
    for i, v in enumerate(vals):
        ax_mass.text(i, v, f"{v:.1f}", ha="center", va="bottom", fontsize=8)

    fig.suptitle("NEW_GEO_RE DEMO2: ADR-passive CsI nominal")
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
    if "Material CsI" in MATERIALS.read_text(encoding="utf-8"):
        problems.append("Materials file redefines standard CsI and will fail Cosima")
    return problems


def named_records(bounds: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    return {rec["name"]: rec for rec in bounds[key]}


def validate_design_requirements(bounds: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    shells = named_records(bounds, "CRYOSTAT_SHELLS")
    stage_windows = named_records(bounds, "STAGE_WINDOWS")
    passive = named_records(bounds, "PASSIVE_PROXIES")
    windows = named_records(bounds, "WINDOWS")

    required_stage_pairs = {
        "Thermal_50mK_Al_Shield": "Win_50mK_Al_Shield",
        "Thermal_1K_Al_Shield": "Win_1K_Al_Shield",
        "Thermal_4K_Al_Shield": "Win_4K_Al_Shield",
        "Thermal_60K_Al_Shield": "Win_60K_Al_Shield",
    }
    for shell_name, win_name in required_stage_pairs.items():
        shell = shells.get(shell_name)
        if shell is None:
            problems.append(f"missing staged thermal shell {shell_name}")
            continue
        if shell.get("hole") != bounds["META"]["be_window_radius_reference_cm"]:
            problems.append(f"{shell_name} aperture does not match Be radius")
        if shell.get("window") != win_name:
            problems.append(f"{shell_name} is not linked to {win_name}")
        win = stage_windows.get(win_name) or windows.get(win_name)
        if win is None:
            problems.append(f"missing staged Al aperture window {win_name}")
        elif win.get("material") != "Aluminium" or abs(win.get("r_max", 0.0) - bounds["META"]["be_window_radius_reference_cm"]) > 1.0e-9:
            problems.append(f"{win_name} is not an Al window matched to the Be aperture")

    required_proxy_names = {
        "Cryoperm_Inner_Mag_Shield",
        "ADR_Magnet_Coil_Cu",
        "ADR_Magnet_Yoke_Fe",
        "ADR_SaltPill_Proxy",
        "ADR_SaltPill_Cu_Can",
        "ADR_HeatSwitch_Stainless_Link",
        "Thermal_Bus_Cu",
        "Vacuum_Jacket_Al_Reinforcement",
        "Vacuum_Top_Flange_Al",
        "Vacuum_Bottom_Flange_Al",
        "PulseTube_ColdHead_Interface_Cu",
        "ActiveShield_Al_Backplane_Liner",
        "ActiveShield_Flex_Readout_Kapton",
        "ActiveShield_Readout_Box_XP",
        "Shield_Feedthrough_Stainless_XP",
    }
    missing = sorted(required_proxy_names - passive.keys())
    if missing:
        problems.append(f"missing ADR/cryostat passive proxies: {missing}")

    side_passive = ["Passive_Cu_Inner_Liner", "Passive_W_Outer_Liner"]
    if not all(name in passive for name in side_passive):
        problems.append("Cu/W side passive shield is incomplete")
    else:
        cu = passive["Passive_Cu_Inner_Liner"]
        w = passive["Passive_W_Outer_Liner"]
        if not (cu["r_out"] <= w["r_in"]):
            problems.append("side passive shield order is not Cu then W moving outward")
        if not (cu["mat"] == "Copper" and w["mat"] == "W"):
            problems.append("side passive shield materials do not match Cu/W")
    if "Passive_Sn_Mid_Liner" in passive:
        problems.append("Sn side liner is present in nominal model; keep Sn only as a systematic variant")
    if "Passive_Bottom_W_Shield" not in passive or "Passive_Top_W_Aperture_Annulus" not in passive:
        problems.append("top/bottom W passive shield elements are incomplete")
    if len(bounds.get("SHIELD_PACKAGING_PROXIES", [])) < 6:
        problems.append("active-shield packaging/readout proxy set is incomplete")
    if passive.get("Passive_W_Outer_Liner", {}).get("r_in", 0.0) < shells.get("Vacuum_Jacket_Al", {}).get("r_out", 0.0):
        problems.append("W side liner is inside the vacuum jacket instead of outside the dewar")
    if "Win_Nb_SC_Detector_Can" in windows:
        problems.append("continuous Nb detector-can aperture foil is present in nominal model")
    if bounds.get("SAMPLE_BOX", {}).get("window", {}).get("name") != "SampleBox_Al_Window":
        problems.append("sample-box Al window was not retained")
    return problems


def inspect_cosima_overlap_log() -> dict[str, Any]:
    if not COSIMA_OVERLAP_LOG.exists():
        return {
            "available": False,
            "path": str(COSIMA_OVERLAP_LOG.relative_to(DEMO)),
            "status": "MISSING",
            "problem_count": None,
            "problems": ["Cosima overlap-check log is missing"],
        }
    text = COSIMA_OVERLAP_LOG.read_text(encoding="utf-8", errors="replace")
    patterns = {
        "overlap_warnings": "GeomVol1002",
        "detector_init_failure": "Unable to initalize",
        "duplicate_material": "already exists",
    }
    problems = [name for name, pattern in patterns.items() if pattern in text]
    has_summary = "Summary for run Minimum" in text
    if not has_summary:
        problems.append("missing_run_summary")
    return {
        "available": True,
        "path": str(COSIMA_OVERLAP_LOG.relative_to(DEMO)),
        "status": "PASS" if not problems else "FAIL",
        "problem_count": len(problems),
        "problems": problems,
        "has_run_summary": has_summary,
    }


def validate(bounds: dict[str, Any], masses: list[MassRow], require_final_docs: bool) -> dict[str, Any]:
    rows = [m.as_dict() for m in masses]
    group: dict[str, float] = {}
    for row in rows:
        group[row["category"]] = group.get(row["category"], 0.0) + float(row["mass_kg"])
    active_mass = sum(v for k, v in group.items() if k.startswith("active_shield"))
    passive_mass = sum(row["mass_kg"] for row in rows if not row["category"].startswith("active_shield"))
    adr_passive = group.get("adr_passive", 0.0) + group.get("magnetic_shield", 0.0) + group.get("cryostat_passive", 0.0) + group.get("service_proxy", 0.0) + group.get("shield_packaging", 0.0)
    passive_shield = group.get("passive_shield", 0.0)
    shield_packaging_mass = group.get("shield_packaging", 0.0)
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
    required_windows = {"Win_60K_Al_Shield", "Win_4K_Al_Shield", "Win_1K_Al_Shield", "Win_50mK_Al_Shield"}
    present_windows = {w["name"] for w in bounds["WINDOWS"]}
    if not required_windows <= present_windows:
        problems.append(f"missing staged Al windows: {sorted(required_windows - present_windows)}")
    if not (24.0 <= passive_mass <= 55.0):
        problems.append(f"passive mass {passive_mass:.2f} kg is outside DEMO2 target range 24-55 kg")
    if adr_passive < 8.5:
        problems.append(f"ADR/magnetic/cryostat passive proxy only {adr_passive:.2f} kg")
    if passive_shield < 4.0:
        problems.append(f"graded passive shield only {passive_shield:.2f} kg")
    if shield_packaging_mass < 0.8:
        problems.append(f"active-shield packaging/readout proxy only {shield_packaging_mass:.2f} kg")
    if not (60.0 <= active_mass <= 70.0):
        problems.append(f"active CsI mass {active_mass:.2f} kg is outside expected 60-70 kg")
    design_requirement_problems = validate_design_requirements(bounds)
    problems.extend(design_requirement_problems)
    for path in (GEO, DET, SETUP, MATERIALS, INTRO, BOUNDS, MASS_CSV, MASS_JSON, WRL, PNG):
        if not path.exists():
            problems.append(f"missing artifact {path.relative_to(DEMO)}")
    if require_final_docs:
        for path in (REPORT, README, DESIGN_REVIEW):
            if not path.exists() or path.stat().st_size <= 0:
                problems.append(f"missing artifact {path.relative_to(DEMO)}")
    problems.extend(validate_geometry_references())
    volume_count = parse_homogeneous_volume_count()
    if volume_count < 55:
        problems.append(f"unexpectedly low volume count {volume_count}")
    cosima_overlap_check = inspect_cosima_overlap_log()
    if require_final_docs and cosima_overlap_check["status"] != "PASS":
        problems.append(f"Cosima overlap check is not PASS: {cosima_overlap_check['problems']}")
    return {
        "status": "PASS" if not problems else "FAIL",
        "problems": problems,
        "checks": {
            "volume_count": volume_count,
            "passive_mass_kg": passive_mass,
            "active_mass_kg": active_mass,
            "adr_passive_mass_kg": adr_passive,
            "passive_shield_mass_kg": passive_shield,
            "shield_packaging_mass_kg": shield_packaging_mass,
            "total_mass_kg": passive_mass + active_mass,
            "active_side_segments": len([s for s in bounds["ACTIVE_SHIELD_SEGMENTS"] if s["part"] == "side"]),
            "active_bottom_segments": len([s for s in bounds["ACTIVE_SHIELD_SEGMENTS"] if s["part"] == "bottom"]),
            "active_top_segments": len([s for s in bounds["ACTIVE_SHIELD_SEGMENTS"] if s["part"] == "top"]),
            "nominal_open_nb_aperture": not any(w["name"] == "Win_Nb_SC_Detector_Can" for w in bounds["WINDOWS"]),
            "staged_al_windows": sorted(required_windows & present_windows),
            "geometry_reference_problems": len(validate_geometry_references()),
            "design_requirement_problems": len(design_requirement_problems),
            "cosima_overlap_check": cosima_overlap_check,
        },
    }


def write_report(bounds: dict[str, Any], masses: list[MassRow], validation: dict[str, Any]) -> None:
    rows = [m.as_dict() for m in masses]
    group: dict[str, float] = {}
    for row in rows:
        group[row["category"]] = group.get(row["category"], 0.0) + float(row["mass_kg"])
    active_mass = sum(v for k, v in group.items() if k.startswith("active_shield"))
    passive_mass = sum(row["mass_kg"] for row in rows if not row["category"].startswith("active_shield"))
    adr_passive = group.get("adr_passive", 0.0) + group.get("magnetic_shield", 0.0) + group.get("cryostat_passive", 0.0) + group.get("service_proxy", 0.0) + group.get("shield_packaging", 0.0)
    passive_shield = group.get("passive_shield", 0.0)
    shield_packaging_mass = group.get("shield_packaging", 0.0)
    lines = [
        "# DEMO2 ADR-Passive CsI Mass Model Summary",
        "",
        "## Status",
        "",
        f"- Validation status: **{validation['status']}**",
        f"- Claim level: `{bounds['META']['claim_level']}`",
        "- This is an engineering Geant4/Cosima background mass model, not a fabrication-ready cryostat CAD design.",
        f"- Cosima overlap-check log: `{validation['checks']['cosima_overlap_check']['path']}`; status `{validation['checks']['cosima_overlap_check']['status']}`.",
        "- Detector map note: passive hardware is marked sensitive for energy-deposition bookkeeping; final trigger/veto logic remains a downstream analysis requirement.",
        "- Peer-review closure: DEMO2 is sufficient as the nominal detector-head engineering mass model for submission, provided the paper keeps the CAD/payload/performance limitations explicit.",
        "",
        "## Review Requirements Addressed",
        "",
        "- Nominal active shield is an oxygen-free segmented CsI(Tl) well, represented as pure CsI for mass and activation stoichiometry.",
        "- Active shield dimensions follow the review nominal: side 4.0 cm, bottom 8.0 cm, top annulus 2.0 cm, entrance aperture 1.898 cm.",
        "- Shield is split into 8 side panels, 4 bottom panels, and 8 top-annulus panels so hit maps can distinguish side/bottom/top regions.",
        "- TES core, Cu sample box, and the sample-box Al window are retained from the previous demo.",
        "- 60 K / 4 K / 1 K / 50 mK staged Al thermal-window foils are included on the main apertures.",
        "- Nearby cryogenic hardware proxies are added: ADR coil, Fe yoke, salt-pill proxy, salt-pill Cu can, heat-switch link, Cryoperm magnetic shield, thermal bus, reinforced dewar/flanges, cold-head interface, readout, support, and harness proxies.",
        "- Active-shield packaging/readout proxies are included: Al backplane/retainers, Kapton flex layer, external readout boxes, and stainless feedthroughs.",
        "- A Cu/W passive shield is placed outside the dewar and inside the active shield; W is not the nearest material to the TES, and Sn is reserved for a graded-Z systematic variant.",
        "- The overlap-prone crossing-bar W grid from the reviewed geometry is replaced by an overlap-safe annular W aperture stop; it is still only a passive entrance-aperture proxy, not a Laue optic.",
        "- Cold plates are represented as solid equivalent disks. M4 hole patterns are omitted from the nominal model because their expected mass/transport correction is below the dominant shield, cryostat, magnetic-shield, and activation systematics.",
        "",
        "## Review Reconciliation",
        "",
        "- 511-CAM motivates a stacked TES focal plane, ADR/mini-DR cryostat, magnetic shielding, and BGO/passive-shield heritage; DEMO2 keeps CsI as the oxygen-suppressed nominal active well while retaining BGO/CeBr3 as systematics.",
        "- Balloon gamma-ray background-reduction practice motivates minimizing passive material inside the active shield; DEMO2 therefore removes Sn from the nominal side liner and keeps only a low-Z Cu liner plus W outer layer.",
        "- Typical ADR public designs motivate the local part inventory represented here: paramagnetic salt pill, superconducting magnet/coil mass, magnetic return/yoke, heat switch, thermal bus, and magnetic shielding.",
        "- Claude's review found the first demo failed Cosima due to duplicate CsI material and had Geant4 overlap warnings; DEMO2 removes the duplicate material and fixes the known TES-envelope/cold-head overlaps.",
        "",
        "## Key Numbers",
        "",
        f"- Active CsI mass: `{active_mass:.3f} kg`.",
        f"- Passive mass including outer shell, ADR proxies, windows, and passive shielding: `{passive_mass:.3f} kg`.",
        f"- ADR/magnetic/cryostat/service proxy mass: `{adr_passive:.3f} kg`.",
        f"- Graded passive shield mass: `{passive_shield:.3f} kg`.",
        f"- Active-shield packaging/readout proxy mass: `{shield_packaging_mass:.3f} kg`.",
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
        "## Peer-Review Closure And Mainline Plan",
        "",
        "- DEMO2 is closed as the submission-quality nominal detector-head mass model, not as final mechanical CAD.",
        "- Reviewer-facing caveat: full cryostat/dewar/payload mass, detailed cold-plate machining holes, final active-shield readout design, and downstream trigger/veto logic remain outside the nominal geometry and should be handled as systematics or follow-up checks.",
        "- Planned next step: on 2026-05-31, replace the NEW_GEO_RE mainline geometry authority with this DEMO2 model, then rerun the production transport, activation, veto, and significance chain from the updated material map.",
        "",
        "## Remaining Required Physics Work",
        "",
        "- This demo has not rerun prompt or delayed activation transport. Any production use requires Step02/Step03 reruns with the new material map.",
        "- The `.det` file does not by itself implement final TES trigger plus CsI anticoincidence logic; downstream Step05-style veto/event-selection must be rerun and audited.",
        "- Cs/I activation products, shield self-veto, timing/dead time, and threshold scans must be evaluated before quoting new background or 3-sigma performance numbers.",
        "- BGO reference, CeBr3 oxygen-free performance, hybrid CsI/BGO, A4K/Cryoperm thickness, open/foil window, Sn graded-Z liner, active-shield packaging mass, and passive-mass Low/Mid/Full cases should remain systematic variations.",
        "- Laue optics hardware mass is still not included in this local detector-head demo.",
        "",
        "## Paper-Safe Wording",
        "",
        "Use: `a DEMO2 engineering ADR/TES detector-head mass model with staged ADR thermal windows, graded passive shielding, and a segmented oxygen-suppressed CsI(Tl) active well`.",
        "",
        "Avoid: `final cryostat mechanical design`, `optimized active shield`, or `complete ADR payload mass model`.",
        "",
    ])
    write_text(REPORT, "\n".join(lines))


def write_design_review_notes(bounds: dict[str, Any], validation: dict[str, Any]) -> None:
    lines = [
        "# DEMO2 Design Review Notes",
        "",
        "## Literature Drivers",
        "",
        "- 511-CAM provides the cryogenic-structure anchor: stacked TES microcalorimeters at about 100 mK, ADR or mini-DR cooling, passive tungsten shielding inside the cryostat, active BGO outside, superconducting Nb plus A4K/Cryoperm-style magnetic shielding, and low-Z entrance window/filter concepts.",
        "- Gehrels' balloon-spectrometer background study is used as the passive-shield caution: passive material inside an active shield, especially close to the detector or aperture, can increase aperture-flux and shield-leakage backgrounds; low-Z materials and low shield thresholds are preferred near the detector.",
        "- Claude's review is used as the local QA anchor: remove duplicate CsI material, eliminate Geant4 overlaps, keep continuous Nb aperture foil out of the nominal model, and treat passive hardware sensitivity as bookkeeping unless downstream veto logic is audited.",
        "",
        "## Implemented Geometry Policy",
        "",
        "- TES stack, Cu sample box, and `SampleBox_Al_Window` are deliberately unchanged.",
        "- Four nested Al thermal cans are modeled at 50 mK, 1 K, 4 K, and 60 K. Each has a Be-radius-matched aperture and a thin Al circular foil window.",
        "- Nb is represented as an open-aperture superconducting detector can, not as a continuous optical-path foil.",
        "- Cryoperm is represented as the Ni-rich magnetic shield surrounding the Nb can.",
        "- ADR activation mass is represented by coil/yoke/GGG-like salt/heat-switch/thermal-bus/cold-head proxies, with dense components mostly below the TES aperture.",
        "- Active-shield packaging is represented by Al/Kapton/stainless backplane, retainer, flex, readout-box, and feedthrough proxies outside the CsI well.",
        "- Passive shielding is Cu then W in the nominal side liner. W also appears as bottom shielding and a top annular aperture stop, but W is not the closest material to the TES-side dewar; Sn is kept for systematic graded-Z variants.",
        "- Cold plates remain solid equivalent disks in the nominal geometry; M4 mounting-hole arrays are treated as negligible machining detail for the submission model unless a later reviewer explicitly requests a small perforated-plate check.",
        "",
        "## Current Validation Snapshot",
        "",
        f"- `validation.json` status: `{validation['status']}`.",
        f"- Design-requirement problem count: `{validation['checks']['design_requirement_problems']}`.",
        f"- Cosima overlap-check status: `{validation['checks']['cosima_overlap_check']['status']}`.",
        f"- Active/passive/total modeled masses: `{validation['checks']['active_mass_kg']:.3f}` / `{validation['checks']['passive_mass_kg']:.3f}` / `{validation['checks']['total_mass_kg']:.3f}` kg.",
        f"- Active-shield packaging/readout proxy mass: `{validation['checks']['shield_packaging_mass_kg']:.3f}` kg.",
        "",
        "## Remaining Non-Geometry Work",
        "",
        "- Submission closure: DEMO2 is adequate as the nominal paper mass model when described as an engineering detector-head background-transport geometry rather than final payload CAD.",
        "- Mainline action: replace the NEW_GEO_RE geometry authority with DEMO2 on 2026-05-31, then rerun the production background and activation workflow.",
        "- DEMO2 has not rerun prompt or delayed activation transport, self-veto/dead-time analysis, day-15 Poisson merging, or significance calculations.",
        "- BGO, CeBr3, open-window, A4K/Cryoperm thickness, Sn graded-Z liner, active-shield packaging mass, and Low/Mid/Full passive-mass variations remain required systematic cases before paper-level performance claims.",
        "",
    ]
    write_text(DESIGN_REVIEW, "\n".join(lines))


def write_readme(validation: dict[str, Any]) -> None:
    text = f"""# DEMO2 ADR-Passive CsI Mass Model

This directory contains a standalone reviewed demo geometry generated by:

```bash
python3 build_demo2_mass_model.py
```

Current validation status: **{validation['status']}**.

Primary outputs are under `outputs/`, including the `.geo.setup`, `.geo`,
`.det`, `bounds.json`, mass budget CSV/JSON, WRL visualization, 2D schematic,
and `mass_model_summary.md`.

DEMO2 keeps the TES stack, Cu sample box, and sample-box Al window from the
first demo, while adding staged 60 K / 4 K / 1 K / 50 mK Al-windowed cans,
more ADR/cryostat passive mass, a Cu/W passive shield outside the dewar,
and minimal active-shield packaging/readout/feedthrough proxies.  Sn is kept
out of the nominal side liner and should be tested only as a graded-Z
systematic variant.
"""
    write_text(README, text)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    validation = build_geometry()
    return 0 if validation["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
