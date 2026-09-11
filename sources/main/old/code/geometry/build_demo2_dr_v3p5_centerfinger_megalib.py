#!/usr/bin/env python3
"""Build a MEGAlib/Cosima scaffold for DEMO2_DR_v3p5 center-finger geometry.

The source of truth remains the design-level bounds package in ``geo_refer``.
This generator intentionally creates a loadable MEGAlib proxy, not final CAD:

* z-axis cylinders/annuli are emitted as PCON solids;
* x-axis discs, annuli, cans, rods, and tubes are emitted as BRIK panel proxies;
* side ports in z-axis shells are approximated by a rectangular z-band plus
  azimuth cutout around the declared port.

All lengths are cm.
"""

from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "geo_refer"
REF_BOUNDS = REF / "DEMO2_DR_v3p5_minpatch_centerfinger_bounds.json"
REF_MASS = REF / "DEMO2_DR_v3p5_minpatch_centerfinger_mass_budget.csv"
REF_VALIDATION = REF / "DEMO2_DR_v3p5_minpatch_centerfinger_validation.json"
REF_GUIDE = REF / "DEMO2_DR_v3p5_minpatch_centerfinger_MEGAlib_implementation_guide.md"

GEOM_NAME = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
OUT = ROOT / "outputs" / "geometry" / GEOM_NAME
GEO = OUT / f"{GEOM_NAME}.geo"
DET = OUT / f"{GEOM_NAME}.det"
SETUP = OUT / f"{GEOM_NAME}.geo.setup"
INTRO = OUT / f"Intro_{GEOM_NAME}.geo"
MATERIALS = OUT / "Materials_DEMO2_DR_v3p5.geo"
VALIDATION = OUT / "geometry_proxy_validation.json"
README = OUT / "README.md"
OVERLAP_SOURCE = OUT / "overlap_check.source"
OVERLAP_LOG = OUT / "cosima_overlap.log"

COSIMA = Path("/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima")
CONTACT_GAP_CM = 0.01
PAD_PROXY_INNER_R_CM = 0.18
ANGULAR_GAP_DEG = 0.05
DOWNSTREAM_SUPPORT_DISK_X_CM = 3.42
DOWNSTREAM_SUPPORT_DISK_HALF_THICK_CM = 0.175
INSTRUMENT_FRAME_NAME = "InstrumentFrame"
INSTRUMENT_FRAME_HALF_SIZE_CM = 80.0
SIDE_WINDOW_LOOK_ELEVATION_DEG = 45.0
INSTRUMENT_FRAME_ROTATION_DEG = (0.0, SIDE_WINDOW_LOOK_ELEVATION_DEG, 0.0)
SURROUNDING_SPHERE_MARGIN_CM = 10.0


CUSTOM_MATERIALS = {
    "Nb": (8.57, [("Nb", 1)]),
    "W": (19.30, [("W", 1)]),
    "Ta": (16.69, [("Ta", 1)]),
    "Be": (1.85, [("Be", 1)]),
    "Cryoperm": (8.70, [("Ni", 4), ("Fe", 1)]),
    "StainlessSteel": (8.00, [("Fe", 70), ("Cr", 18), ("Ni", 10), ("Mn", 2)]),
    "G10": (1.85, [("Si", 1), ("O", 2), ("C", 3), ("H", 3)]),
    "Kapton": (1.42, [("C", 22), ("H", 10), ("N", 2), ("O", 5)]),
    "CuNi": (8.90, [("Cu", 7), ("Ni", 3)]),
    "SilverSinterProxy": (5.00, [("Ag", 1)]),
    "CharcoalProxy": (1.20, [("C", 1)]),
    "NbTiCableProxy": (6.50, [("Nb", 1), ("Ti", 1)]),
}


@dataclass
class GeneratedVolume:
    name: str
    material: str
    category: str
    source_cid: str
    source_name: str
    proxy_note: str
    detector_name: str | None = None
    threshold_kev: float = 0.001
    sensitive: bool = True
    detector_type: str = "Scintillator"
    detector_volume: str | None = None
    structural_pitch_cm: tuple[float, float, float] | None = None
    energy_resolution_sigma_kev: float = 1.0


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


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def safe_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", name)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned:
        raise ValueError(f"Cannot sanitize empty volume name from {name!r}")
    if cleaned[0].isdigit():
        cleaned = "V_" + cleaned
    return cleaned


def pcon(planes: list[tuple[float, float, float]], phi0: float = 0.0, dphi: float = 360.0) -> str:
    phi0 = phi0 % 360.0
    toks = ["PCON", fmt(phi0), fmt(dphi), str(len(planes))]
    for z, r0, r1 in planes:
        toks.extend([fmt(z), fmt(r0), fmt(r1)])
    return " ".join(toks)


def cylinder_shape(radius: float, halfz: float, phi0: float = 0.0, dphi: float = 360.0) -> str:
    return pcon([(-halfz, 0.0, radius), (halfz, 0.0, radius)], phi0, dphi)


def annulus_shape(r_in: float, r_out: float, halfz: float, phi0: float = 0.0, dphi: float = 360.0) -> str:
    return pcon([(-halfz, r_in, r_out), (halfz, r_in, r_out)], phi0, dphi)


def brik_shape(hx: float, hy: float, hz: float) -> str:
    return f"BRIK {fmt(hx)} {fmt(hy)} {fmt(hz)}"


def volume_def(name: str, material: str, shape: str, vis: int = 1) -> str:
    return (
        f"// Volume {name}; material={material}\n"
        f"Volume {name}\n"
        f"{name}.Material {material}\n"
        f"{name}.Visibility {vis}\n"
        f"{name}.Shape {shape}\n\n"
    )


def place(name: str, x: float, y: float, z: float, mother: str = INSTRUMENT_FRAME_NAME) -> str:
    return f"{name}.Position {fmt(x)} {fmt(y)} {fmt(z)}\n{name}.Mother {mother}\n\n"


def pixel_positions(radius: float = 1.8, pitch: float = 0.155, expected: int = 376) -> list[tuple[float, float]]:
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
        raise RuntimeError(f"TES footprint produced only {len(positions)} pixels; expected {expected}")
    return sorted(positions[:expected])


def phi_ranges_minus_hole(phi0: float, dphi: float, hole_center: float, hole_half_width: float) -> list[tuple[float, float]]:
    start = phi0
    end = phi0 + dphi
    center = hole_center
    while center + hole_half_width < start:
        center += 360.0
    while center - hole_half_width > end:
        center -= 360.0
    cut0 = center - hole_half_width
    cut1 = center + hole_half_width
    if cut1 <= start or cut0 >= end:
        return [(phi0, dphi)]
    ranges: list[tuple[float, float]] = []
    left_end = min(cut0, end)
    if left_end - start > 1.0e-6:
        ranges.append((start, left_end - start))
    right_start = max(cut1, start)
    if end - right_start > 1.0e-6:
        ranges.append((right_start, end - right_start))
    return ranges


class GeometryBuilder:
    def __init__(self) -> None:
        self.geo: list[str] = [f"Include Intro_{GEOM_NAME}.geo\n\n"]
        self.records: list[GeneratedVolume] = []
        self.component_to_volumes: dict[str, list[str]] = {}
        self.proxy_notes: list[str] = []

    def add_volume(
        self,
        comp: dict[str, Any],
        name: str,
        material: str,
        shape: str,
        pos: tuple[float, float, float],
        *,
        note: str,
        detector_name: str | None = None,
        threshold_kev: float = 0.001,
        sensitive: bool = True,
        detector_type: str = "Scintillator",
        detector_volume: str | None = None,
        structural_pitch_cm: tuple[float, float, float] | None = None,
        energy_resolution_sigma_kev: float = 1.0,
        vis: int = 1,
    ) -> None:
        vname = safe_name(name)
        if any(r.name == vname for r in self.records):
            raise ValueError(f"Duplicate generated volume name: {vname}")
        self.geo.append(volume_def(vname, material, shape, vis=vis))
        self.geo.append(place(vname, *pos))
        self.add_record(
            comp,
            vname,
            material,
            note=note,
            detector_name=detector_name,
            threshold_kev=threshold_kev,
            sensitive=sensitive,
            detector_type=detector_type,
            detector_volume=detector_volume,
            structural_pitch_cm=structural_pitch_cm,
            energy_resolution_sigma_kev=energy_resolution_sigma_kev,
        )

    def add_record(
        self,
        comp: dict[str, Any],
        name: str,
        material: str,
        *,
        note: str,
        detector_name: str | None = None,
        threshold_kev: float = 0.001,
        sensitive: bool = True,
        detector_type: str = "Scintillator",
        detector_volume: str | None = None,
        structural_pitch_cm: tuple[float, float, float] | None = None,
        energy_resolution_sigma_kev: float = 1.0,
    ) -> None:
        vname = safe_name(name)
        if any(r.name == vname for r in self.records):
            raise ValueError(f"Duplicate generated volume name: {vname}")
        rec = GeneratedVolume(
            name=vname,
            material=material,
            category=comp.get("category", "unknown"),
            source_cid=comp.get("cid", ""),
            source_name=comp.get("name", ""),
            proxy_note=note,
            detector_name=detector_name,
            threshold_kev=threshold_kev,
            sensitive=sensitive,
            detector_type=detector_type,
            detector_volume=detector_volume,
            structural_pitch_cm=structural_pitch_cm,
            energy_resolution_sigma_kev=energy_resolution_sigma_kev,
        )
        self.records.append(rec)
        self.component_to_volumes.setdefault(comp.get("cid", comp.get("name", "")), []).append(vname)

    def add_annulus_with_optional_side_hole(
        self,
        comp: dict[str, Any],
        base_name: str,
        material: str,
        r_in: float,
        r_out: float,
        z0: float,
        z1: float,
        *,
        phi0: float = 0.0,
        dphi: float = 360.0,
        note: str,
    ) -> None:
        p = comp["params"]
        hole = p.get("side_hole")
        if not hole:
            halfz = 0.5 * (z1 - z0)
            self.add_volume(
                comp,
                base_name,
                material,
                annulus_shape(r_in, r_out, halfz, phi0, dphi),
                (0.0, 0.0, 0.5 * (z0 + z1)),
                note=note,
            )
            return

        hole_z = float(hole["z_cm"])
        hole_r = float(hole["r_cm"])
        band0 = max(z0, hole_z - hole_r)
        band1 = min(z1, hole_z + hole_r)
        if band0 > z0 + 1.0e-6:
            halfz = 0.5 * (band0 - z0)
            self.add_volume(
                comp,
                base_name + "_below_side_port",
                material,
                annulus_shape(r_in, r_out, halfz, phi0, dphi),
                (0.0, 0.0, 0.5 * (z0 + band0)),
                note=note + "; below side-port band",
            )
        if band1 < z1 - 1.0e-6:
            halfz = 0.5 * (z1 - band1)
            self.add_volume(
                comp,
                base_name + "_above_side_port",
                material,
                annulus_shape(r_in, r_out, halfz, phi0, dphi),
                (0.0, 0.0, 0.5 * (band1 + z1)),
                note=note + "; above side-port band",
            )
        if band1 <= band0 + 1.0e-6:
            return

        # Conservative rectangular proxy for the circular side port:
        # remove the declared z band and azimuth wedge centered on the port.
        radius_for_angle = max(r_in, 1.0e-6)
        half_width = math.degrees(math.asin(min(0.95, hole_r / radius_for_angle))) + 0.5
        hole_center = float(hole.get("azimuth_deg", 180.0))
        halfz = 0.5 * (band1 - band0)
        for idx, (seg_phi0, seg_dphi) in enumerate(phi_ranges_minus_hole(phi0, dphi, hole_center, half_width)):
            adj_phi0 = seg_phi0 + 0.5 * ANGULAR_GAP_DEG
            adj_dphi = max(0.0, seg_dphi - ANGULAR_GAP_DEG)
            if adj_dphi <= 1.0e-6:
                continue
            self.add_volume(
                comp,
                f"{base_name}_side_port_band_{idx:02d}",
                material,
                annulus_shape(r_in, r_out, halfz, adj_phi0, adj_dphi),
                (0.0, 0.0, 0.5 * (band0 + band1)),
                note=note + "; rectangular azimuth/z side-port cutout proxy",
            )

    def add_x_disc_stack(self, comp: dict[str, Any]) -> None:
        p = comp["params"]
        mat = comp["material"]
        if mat == "Ta":
            self.add_tes_pixel_stack(comp)
            return
        base = safe_name(comp["name"])
        half_profile = float(p["disc_r_cm"])
        note = "x_disc_stack represented by one square BRIK substrate per layer; declared radius is used as square half-side"
        if comp["name"] == "Si_Substrate_Stack_side_entry":
            # The four edge rods sit at |y,z|=1.95 cm. A 1.80 cm half-side
            # still covers the full TES pixel footprint but leaves a real gap.
            half_profile = min(half_profile, 1.80)
            note = "Si substrate represented by a square BRIK per layer; half-side chosen to cover the TES footprint and clear edge rods"
        hx = 0.5 * float(p["disc_t_cm"])
        y = float(p.get("axis_y_cm", 0.0))
        z = float(p.get("axis_z_cm", 0.0))
        for i, x in enumerate(p["x_centers_cm"]):
            self.add_volume(
                comp,
                f"{base}_L{i}",
                mat,
                brik_shape(hx, half_profile, half_profile),
                (float(x), y, z),
                note=note,
            )

    def add_tes_pixel_stack(self, comp: dict[str, Any]) -> None:
        p = comp["params"]
        n_layers = int(p["n_layers"])
        x_centers = [float(x) for x in p["x_centers_cm"]]
        if n_layers != len(x_centers):
            raise ValueError(f"{comp['name']} declares {n_layers} layers but has {len(x_centers)} x centers")
        expected = int(p["pixels_per_layer"])
        pix_y_cm, pix_z_cm, pix_depth_cm = (float(v) for v in p["pixel_size_cm"])
        pitch = float(p.get("pixel_pitch_cm", 0.155))
        footprint = pixel_positions(float(p["disc_r_cm"]), pitch, expected)
        axis_y = float(p.get("axis_y_cm", 0.0))
        axis_z = float(p.get("axis_z_cm", 0.0))
        hx = 0.5 * pix_depth_cm
        hy = 0.5 * pix_y_cm
        hz = 0.5 * pix_z_cm
        max_transverse = max(max(abs(y), abs(z)) for y, z in footprint)
        envelope_half = max_transverse + max(hy, hz) + 0.02
        for i, x in enumerate(x_centers):
            template = f"TES_Pixel_L{i}"
            container = f"TES_L{i}"
            self.geo.append(volume_def(template, "Ta", brik_shape(hx, hy, hz), vis=1))
            self.add_record(
                comp,
                template,
                "Ta",
                note="TES pixel template; 376 copies per layer, rotated so absorber depth lies along x",
                detector_name=f"D{i + 1}",
                threshold_kev=0.3,
                detector_type="MDCalorimeter",
                detector_volume=container,
                structural_pitch_cm=(pitch, pitch, 0.1),
                energy_resolution_sigma_kev=0.14,
            )
            self.geo.append(volume_def(container, "Vacuum", brik_shape(hx, envelope_half, envelope_half), vis=0))
            self.geo.append(place(container, x, axis_y, axis_z))
            self.add_record(
                comp,
                container,
                "Vacuum",
                note="TES detector-volume envelope for one side-entry pixel layer",
                sensitive=False,
            )
            for j, (local_y, local_z) in enumerate(footprint):
                cname = f"TP_L{i}_{j:05d}"
                self.geo.append(f"{template}.Copy {cname}\n")
                self.geo.append(
                    f"{cname}.Position 0 {fmt(local_y)} {fmt(local_z)}\n"
                    f"{cname}.Mother {container}\n"
                    f"{cname}.Visibility 0\n\n"
                )
                self.add_record(
                    comp,
                    cname,
                    "Ta",
                    note="TES pixel copy in legacy 376-pixel footprint",
                    sensitive=False,
                )

    def add_x_disc(self, comp: dict[str, Any]) -> None:
        p = comp["params"]
        half_profile = float(p["r_cm"])
        self.add_volume(
            comp,
            comp["name"],
            comp["material"],
            brik_shape(0.5 * float(p["thickness_cm"]), half_profile, half_profile),
            (float(p["x_center_cm"]), float(p.get("axis_y_cm", 0.0)), float(p.get("axis_z_cm", 0.0))),
            note="x_disc represented by a square BRIK window/filter proxy; declared radius is used as square half-side",
        )

    def add_x_annulus(self, comp: dict[str, Any]) -> None:
        p = comp["params"]
        x = float(p["x_center_cm"])
        y0 = float(p.get("axis_y_cm", 0.0))
        z0 = float(p.get("axis_z_cm", 0.0))
        hx = 0.5 * float(p["thickness_cm"])
        r_in = float(p["r_in_cm"])
        r_out = float(p["r_out_cm"])
        band = 0.5 * (r_out - r_in)
        inner_span = max(0.05, r_in - 0.12)
        mat = comp["material"]
        note = "x_annulus represented by four BRIK panels; center kept open; panel span trimmed for edge-rod clearance"
        self.add_volume(comp, comp["name"] + "_ZP_panel", mat, brik_shape(hx, inner_span, band), (x, y0, z0 + r_in + band), note=note)
        self.add_volume(comp, comp["name"] + "_ZM_panel", mat, brik_shape(hx, inner_span, band), (x, y0, z0 - r_in - band), note=note)
        self.add_volume(comp, comp["name"] + "_YP_panel", mat, brik_shape(hx, band, inner_span), (x, y0 + r_in + band, z0), note=note)
        self.add_volume(comp, comp["name"] + "_YM_panel", mat, brik_shape(hx, band, inner_span), (x, y0 - r_in - band, z0), note=note)

    def add_x_cylinder_offaxis(self, comp: dict[str, Any]) -> None:
        p = comp["params"]
        x0 = float(p["x0_cm"])
        x1 = float(p["x1_cm"])
        note = "x_cylinder_offaxis represented by an inscribed-square BRIK rod"
        if comp["name"].startswith("Cu_ColdFinger_OffAxis_"):
            # The design component touches the support disk and vertical stem.
            # Separate proxy volumes need a small gap for Geant4 overlap checks.
            x0 += 0.5 * 0.35 + CONTACT_GAP_CM
            x1 -= float(p["r_cm"]) + CONTACT_GAP_CM
            note += "; contact ends trimmed by a small proxy gap"
        elif comp["name"].startswith("Cu_SubstrateSupport_EdgeRod_"):
            # The rods mechanically terminate at the downstream support disk.
            # Keep a small proxy gap so the square disk and rods do not overlap.
            x1 = min(x1, DOWNSTREAM_SUPPORT_DISK_X_CM - DOWNSTREAM_SUPPORT_DISK_HALF_THICK_CM - CONTACT_GAP_CM)
            note += "; downstream end trimmed before the support disk by a small proxy gap"
        hx = 0.5 * (x1 - x0)
        r = float(p["r_cm"]) / math.sqrt(2.0)
        self.add_volume(
            comp,
            comp["name"],
            comp["material"],
            brik_shape(hx, r, r),
            (0.5 * (x0 + x1), float(p["y_center_cm"]), float(p["z_center_cm"])),
            note=note,
        )

    def add_z_cylinder(self, comp: dict[str, Any]) -> None:
        p = comp["params"]
        if "z_center_cm" in p:
            zc = float(p["z_center_cm"])
            halfz = 0.5 * float(p["h_cm"])
        else:
            zc = 0.5 * (float(p["z0_cm"]) + float(p["z1_cm"]))
            halfz = 0.5 * (float(p["z1_cm"]) - float(p["z0_cm"]))
        note = "z_cylinder emitted as PCON"
        if comp["name"] == "Passive_W_Bottom_Plate_detector_bay":
            zc = -14.30
            halfz = min(halfz, 0.095)
            note += "; centered and thinned by 0.01 cm in proxy to clear CsI bottom and W liner boundaries"
        self.add_volume(
            comp,
            comp["name"],
            comp["material"],
            cylinder_shape(float(p["r_cm"]), halfz),
            (float(p.get("x_center_cm", 0.0)), float(p.get("y_center_cm", 0.0)), zc),
            note=note,
        )

    def add_z_cylinder_offaxis(self, comp: dict[str, Any]) -> None:
        p = comp["params"]
        z0 = float(p["z0_cm"])
        z1 = float(p["z1_cm"])
        if comp["name"].startswith("Cu_MXC_Clamp_Pad_"):
            self.add_volume(
                comp,
                comp["name"],
                comp["material"],
                annulus_shape(PAD_PROXY_INNER_R_CM, float(p["r_cm"]), 0.5 * (z1 - z0)),
                (float(p["x_center_cm"]), float(p["y_center_cm"]), 0.5 * (z0 + z1)),
                note="MXC clamp pad represented as annular PCON proxy so the stem passes through without volume overlap",
            )
            return
        self.add_volume(
            comp,
            comp["name"],
            comp["material"],
            cylinder_shape(float(p["r_cm"]), 0.5 * (z1 - z0)),
            (float(p["x_center_cm"]), float(p["y_center_cm"]), 0.5 * (z0 + z1)),
            note="z_cylinder_offaxis emitted as offset PCON cylinder",
        )

    def add_z_annulus(self, comp: dict[str, Any]) -> None:
        p = comp["params"]
        self.add_annulus_with_optional_side_hole(
            comp,
            comp["name"],
            comp["material"],
            float(p["r_in_cm"]),
            float(p["r_out_cm"]),
            float(p["z0_cm"]),
            float(p["z1_cm"]),
            note="z_annulus emitted as PCON annulus",
        )

    def add_z_annulus_phi(self, comp: dict[str, Any]) -> None:
        p = comp["params"]
        dphi = 360.0 * float(p.get("phi_frac", 1.0))
        phi0 = float(p.get("azimuth_center_deg", 0.5 * dphi)) - 0.5 * dphi if "azimuth_center_deg" in p else 0.0
        note = "z_annulus_phi emitted as PCON phi segment"
        if comp["name"].startswith("NbTi_Bundle_"):
            center = 90.0 if comp["name"] == "NbTi_Bundle_bay_to_MXC" else 130.0
            phi0 = center - 0.5 * dphi
            note += "; service-bundle proxy azimuth moved away from CuNi capillaries"
        if comp["name"].startswith("G10_Support_Ring_"):
            phi0 = 210.0
            note += "; support-ring proxy azimuth moved away from service bundles and precool link"
        self.add_annulus_with_optional_side_hole(
            comp,
            comp["name"],
            comp["material"],
            float(p["r_in_cm"]),
            float(p["r_out_cm"]),
            float(p["z0_cm"]),
            float(p["z1_cm"]),
            phi0=phi0,
            dphi=dphi,
            note=note,
        )

    def add_z_annulus_phi_segment(self, comp: dict[str, Any]) -> None:
        p = comp["params"]
        self.add_annulus_with_optional_side_hole(
            comp,
            comp["name"],
            comp["material"],
            float(p["r_in_cm"]),
            float(p["r_out_cm"]),
            float(p["z0_cm"]),
            float(p["z1_cm"]),
            phi0=float(p["phi0_deg"]),
            dphi=float(p["dphi_deg"]),
            note="z_annulus_phi_segment emitted as PCON sector",
        )

    def add_z_can_open_top(self, comp: dict[str, Any]) -> None:
        p = comp["params"]
        mat = comp["material"]
        z_out_bot = float(p["z_out_bot_cm"])
        z_in_bot = float(p["z_in_bot_cm"])
        z_top = float(p["z_top_cm"])
        r_in = float(p["r_in_cm"])
        r_out = float(p["r_out_cm"])
        if z_in_bot > z_out_bot:
            self.add_volume(
                comp,
                comp["name"] + "_bottom_cap",
                mat,
                cylinder_shape(r_out, 0.5 * (z_in_bot - z_out_bot)),
                (0.0, 0.0, 0.5 * (z_out_bot + z_in_bot)),
                note="z_can_open_top bottom cap emitted as PCON disk",
            )
        self.add_annulus_with_optional_side_hole(
            comp,
            comp["name"] + "_side_wall",
            mat,
            r_in,
            r_out,
            z_in_bot,
            z_top,
            note="z_can_open_top side wall emitted as PCON annulus with side-port proxy if declared",
        )

    def add_z_shell_top_annulus(self, comp: dict[str, Any]) -> None:
        p = comp["params"]
        mat = comp["material"]
        r_in = float(p["r_in_cm"])
        r_out = float(p["r_out_cm"])
        z_in_bot = float(p["z_in_bot_cm"])
        z_out_bot = float(p["z_out_bot_cm"])
        z_top = float(p["z_top_cm"])
        if z_in_bot > z_out_bot:
            self.add_volume(
                comp,
                comp["name"] + "_bottom_cap",
                mat,
                cylinder_shape(r_out, 0.5 * (z_in_bot - z_out_bot)),
                (0.0, 0.0, 0.5 * (z_out_bot + z_in_bot)),
                note="z_shell_top_annulus bottom cap emitted as PCON disk",
            )
        self.add_annulus_with_optional_side_hole(
            comp,
            comp["name"] + "_side_wall",
            mat,
            r_in,
            r_out,
            z_in_bot,
            z_top,
            note="z_shell_top_annulus side wall emitted as PCON annulus with side-port proxy",
        )
        self.add_volume(
            comp,
            comp["name"] + "_top_annulus",
            mat,
            annulus_shape(float(p["top_hole_r_cm"]), r_out, 0.5 * (float(p["top_ann_z1_cm"]) - float(p["top_ann_z0_cm"]))),
            (0.0, 0.0, 0.5 * (float(p["top_ann_z0_cm"]) + float(p["top_ann_z1_cm"]))),
            note="z_shell_top_annulus top annulus emitted as PCON annulus",
        )

    def add_x_tube(self, comp: dict[str, Any]) -> None:
        p = comp["params"]
        x0 = float(p["x0_cm"])
        x1 = float(p["x1_cm"])
        hx = 0.5 * (x1 - x0)
        y0 = float(p.get("axis_y_cm", 0.0))
        z0 = float(p.get("axis_z_cm", 0.0))
        r_in = float(p["r_in_cm"])
        r_out = float(p["r_out_cm"])
        band = 0.5 * (r_out - r_in)
        mat = comp["material"]
        note = "x_tube represented by four square-bore BRIK panels; declared radii are square half-sides and central beam aperture is kept open"
        self.add_volume(comp, comp["name"] + "_ZP_panel", mat, brik_shape(hx, r_out, band), (0.5 * (x0 + x1), y0, z0 + r_in + band), note=note)
        self.add_volume(comp, comp["name"] + "_ZM_panel", mat, brik_shape(hx, r_out, band), (0.5 * (x0 + x1), y0, z0 - r_in - band), note=note)
        self.add_volume(comp, comp["name"] + "_YP_panel", mat, brik_shape(hx, band, r_in), (0.5 * (x0 + x1), y0 + r_in + band, z0), note=note)
        self.add_volume(comp, comp["name"] + "_YM_panel", mat, brik_shape(hx, band, r_in), (0.5 * (x0 + x1), y0 - r_in - band, z0), note=note)

    def add_x_can(self, comp: dict[str, Any]) -> None:
        p = comp["params"]
        x0 = float(p["x0_cm"])
        x1 = float(p["x1_cm"])
        hx = 0.5 * (x1 - x0)
        x = 0.5 * (x0 + x1)
        y0 = float(p.get("axis_y_cm", 0.0))
        z0 = float(p.get("axis_z_cm", 0.0))
        r_in = float(p["r_in_cm"])
        r_out = float(p["r_out_cm"])
        band = 0.5 * (r_out - r_in)
        mat = comp["material"]
        note = "x_can represented by open-ended BRIK side panels; end-cap ports/feedthroughs are kept open"
        skip_zp = bool(p.get("plus_x_thermal_finger_feedthroughs") or p.get("top_stem_slots"))
        if not skip_zp:
            self.add_volume(comp, comp["name"] + "_ZP_panel", mat, brik_shape(hx, r_out, band), (x, y0, z0 + r_in + band), note=note)
        self.add_volume(comp, comp["name"] + "_ZM_panel", mat, brik_shape(hx, r_out, band), (x, y0, z0 - r_in - band), note=note)
        self.add_volume(comp, comp["name"] + "_YP_panel", mat, brik_shape(hx, band, r_in), (x, y0 + r_in + band, z0), note=note)
        self.add_volume(comp, comp["name"] + "_YM_panel", mat, brik_shape(hx, band, r_in), (x, y0 - r_in - band, z0), note=note)

    def add_box(self, comp: dict[str, Any]) -> None:
        p = comp["params"]
        z0 = float(p["z0_cm"])
        z1 = float(p["z1_cm"])
        hy = float(p["hy_cm"])
        note = "box emitted as BRIK"
        if comp["name"] == "SQUID_uMUX_Box_Al_relocated_offbeam_minimal":
            hy = min(hy, 0.25)
            note += "; y half-width trimmed in proxy to keep the box inside the 4K shield envelope"
        self.add_volume(
            comp,
            comp["name"],
            comp["material"],
            brik_shape(float(p["hx_cm"]), hy, 0.5 * (z1 - z0)),
            (float(p.get("x_cm", 0.0)), float(p.get("y_cm", 0.0)), 0.5 * (z0 + z1)),
            note=note,
        )

    def add_component(self, comp: dict[str, Any]) -> None:
        shape = comp["shape"]
        handlers = {
            "x_disc_stack": self.add_x_disc_stack,
            "x_annulus": self.add_x_annulus,
            "x_disc": self.add_x_disc,
            "x_cylinder_offaxis": self.add_x_cylinder_offaxis,
            "z_cylinder": self.add_z_cylinder,
            "z_cylinder_offaxis": self.add_z_cylinder_offaxis,
            "x_can": self.add_x_can,
            "z_can_open_top": self.add_z_can_open_top,
            "z_annulus": self.add_z_annulus,
            "z_annulus_phi": self.add_z_annulus_phi,
            "z_annulus_phi_segment": self.add_z_annulus_phi_segment,
            "x_tube": self.add_x_tube,
            "z_shell_top_annulus": self.add_z_shell_top_annulus,
            "box": self.add_box,
        }
        if shape not in handlers:
            raise ValueError(f"Unsupported shape {shape!r} for {comp['cid']} {comp['name']}")
        handlers[shape](comp)


def write_materials() -> None:
    lines = [
        "# Custom materials for DEMO2_DR_v3p5 center-finger MEGAlib proxy.",
        "Include $(MEGALIB)/resource/examples/geomega/materials/Materials.geo",
        "",
        "# Copper, Aluminium, Silicon, CsI, and Vacuum are taken from MEGAlib standard materials.",
        "",
    ]
    for name, (density, components) in CUSTOM_MATERIALS.items():
        lines.append(f"Material {name}")
        lines.append(f"{name}.Density {fmt(density)}")
        for element, amount in components:
            lines.append(f"{name}.Component {element} {fmt(amount)}")
        lines.append("")
    write_text(MATERIALS, "\n".join(lines) + "\n")


def write_intro() -> None:
    text = f"""Name Massmodel_{GEOM_NAME}
Version 1

Include {MATERIALS.name}
AbsorptionFileDirectory crossections

Volume WorldVolume
WorldVolume.Visibility 0
WorldVolume.Material Vacuum
WorldVolume.Shape BRIK 1000 1000 1000
WorldVolume.Mother 0

Volume {INSTRUMENT_FRAME_NAME}
{INSTRUMENT_FRAME_NAME}.Visibility 0
{INSTRUMENT_FRAME_NAME}.Material Vacuum
{INSTRUMENT_FRAME_NAME}.Shape BRIK {fmt(INSTRUMENT_FRAME_HALF_SIZE_CM)} {fmt(INSTRUMENT_FRAME_HALF_SIZE_CM)} {fmt(INSTRUMENT_FRAME_HALF_SIZE_CM)}
{INSTRUMENT_FRAME_NAME}.Position 0 0 0
{INSTRUMENT_FRAME_NAME}.Rotation {fmt(INSTRUMENT_FRAME_ROTATION_DEG[0])} {fmt(INSTRUMENT_FRAME_ROTATION_DEG[1])} {fmt(INSTRUMENT_FRAME_ROTATION_DEG[2])}
{INSTRUMENT_FRAME_NAME}.Mother WorldVolume
"""
    write_text(INTRO, text)


def rotate_y(point: tuple[float, float, float], angle_deg: float) -> tuple[float, float, float]:
    x, y, z = point
    angle = math.radians(angle_deg)
    c = math.cos(angle)
    s = math.sin(angle)
    return (c * x + s * z, y, -s * x + c * z)


def parse_generated_geometry_extents(geo_text: str) -> dict[str, Any]:
    shapes: dict[str, list[str]] = {}
    positions: dict[str, tuple[float, float, float]] = {}
    mothers: dict[str, str] = {}
    for match in re.finditer(r"^(\w+)\.Shape\s+(BRIK\s+[-+0-9.eE]+\s+[-+0-9.eE]+\s+[-+0-9.eE]+|PCON\s+.*)$", geo_text, re.MULTILINE):
        shapes[match.group(1)] = match.group(2).split()
    for match in re.finditer(r"^(\w+)\.Position\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)", geo_text, re.MULTILINE):
        positions[match.group(1)] = tuple(float(v) for v in match.groups()[1:])
    for match in re.finditer(r"^(\w+)\.Mother\s+(\w+)", geo_text, re.MULTILINE):
        mothers[match.group(1)] = match.group(2)

    mins = [float("inf"), float("inf"), float("inf")]
    maxs = [float("-inf"), float("-inf"), float("-inf")]
    parsed = 0
    for name, toks in shapes.items():
        if name not in positions or name == "WorldVolume":
            continue
        x, y, z = positions[name]
        local_corners: list[tuple[float, float, float]]
        if toks[0] == "BRIK":
            hx, hy, hz = (float(v) for v in toks[1:4])
            local_corners = [
                (x + sx * hx, y + sy * hy, z + sz * hz)
                for sx in (-1.0, 1.0)
                for sy in (-1.0, 1.0)
                for sz in (-1.0, 1.0)
            ]
        elif toks[0] == "PCON":
            values = [float(v) for v in toks[1:]]
            n_planes = int(values[2])
            planes = values[3:]
            z_values: list[float] = []
            radii: list[float] = []
            for i in range(n_planes):
                pz, r0, r1 = planes[3 * i : 3 * i + 3]
                z_values.append(pz)
                radii.append(max(abs(r0), abs(r1)))
            radius = max(radii)
            z_min = min(z_values)
            z_max = max(z_values)
            local_corners = [
                (x + sx * radius, y + sy * radius, z + pz)
                for sx in (-1.0, 1.0)
                for sy in (-1.0, 1.0)
                for pz in (z_min, z_max)
            ]
        else:
            continue

        parsed += 1
        if mothers.get(name) == INSTRUMENT_FRAME_NAME:
            corners = [rotate_y(corner, SIDE_WINDOW_LOOK_ELEVATION_DEG) for corner in local_corners]
        else:
            corners = local_corners
        for corner in corners:
            for i, value in enumerate(corner):
                mins[i] = min(mins[i], value)
                maxs[i] = max(maxs[i], value)

    if parsed == 0:
        raise RuntimeError("No generated volumes could be parsed for geometry extents")

    center = [0.5 * (lo + hi) for lo, hi in zip(mins, maxs)]
    half_extents = [0.5 * (hi - lo) for lo, hi in zip(mins, maxs)]
    bounding_radius = math.sqrt(sum(v * v for v in half_extents))
    recommended = math.ceil((bounding_radius + SURROUNDING_SPHERE_MARGIN_CM) / 5.0) * 5.0
    local_look = (-1.0, 0.0, 0.0)
    sky_look = rotate_y(local_look, SIDE_WINDOW_LOOK_ELEVATION_DEG)
    elevation = math.degrees(math.asin(sky_look[2] / math.sqrt(sum(v * v for v in sky_look))))
    return {
        "parsed_volume_count": parsed,
        "mins_cm": mins,
        "maxs_cm": maxs,
        "center_cm": center,
        "half_extents_cm": half_extents,
        "bounding_radius_cm": bounding_radius,
        "recommended_farfield_radius_cm": recommended,
        "instrument_frame": {
            "name": INSTRUMENT_FRAME_NAME,
            "rotation_deg": list(INSTRUMENT_FRAME_ROTATION_DEG),
            "side_window_local_look_axis": "-x",
            "side_window_global_look_vector": list(sky_look),
            "side_window_look_elevation_deg": elevation,
            "incoming_photon_global_axis": [-v for v in sky_look],
        },
    }


def write_setup(extents: dict[str, Any]) -> None:
    center = extents["center_cm"]
    radius = extents["recommended_farfield_radius_cm"]
    text = f"""Name {GEOM_NAME}
Version 1
Include {GEO.name}
Include {DET.name}
SurroundingSphere {fmt(radius)} {fmt(center[0])} {fmt(center[1])} {fmt(center[2])} {fmt(radius)}
"""
    write_text(SETUP, text)


def scintillator_block(det_name: str, volume_name: str, threshold_kev: float, eres_sigma: float = 1.0) -> str:
    return (
        f"Scintillator {det_name}\n"
        f"{det_name}.SensitiveVolume {volume_name}\n"
        f"{det_name}.DetectorVolume {volume_name}\n"
        f"{det_name}.TriggerThreshold {fmt(threshold_kev)}\n"
        f"{det_name}.EnergyResolution Gauss {fmt(threshold_kev)} {fmt(threshold_kev)} {fmt(eres_sigma)}\n"
        f"{det_name}.EnergyResolution Gauss 3000 3000 {fmt(eres_sigma)}\n\n"
    )


def mdcalorimeter_block(
    det_name: str,
    sensitive_volume: str,
    detector_volume: str,
    threshold_kev: float,
    pitch: tuple[float, float, float],
    eres_sigma: float = 0.14,
) -> str:
    return (
        f"MDCalorimeter {det_name}\n"
        f"{det_name}.SensitiveVolume {sensitive_volume}\n"
        f"{det_name}.DetectorVolume {detector_volume}\n"
        f"{det_name}.StructuralPitch {fmt(pitch[0])} {fmt(pitch[1])} {fmt(pitch[2])}\n"
        f"{det_name}.StructuralOffset 0 0 0\n"
        f"{det_name}.TriggerThreshold {fmt(threshold_kev)} 0.0\n"
        f"{det_name}.EnergyResolution Gauss {fmt(threshold_kev)} {fmt(threshold_kev)} {fmt(eres_sigma)}\n"
        f"{det_name}.EnergyResolution Gauss 3000 3000 {fmt(eres_sigma)}\n\n"
    )


def write_det(records: list[GeneratedVolume]) -> None:
    lines = [
        f"// {GEOM_NAME} detector map",
        "// TES core follows the legacy DEMO2 6-layer MDCalorimeter pixel map; native veto timing is handled downstream.",
        "",
    ]
    used: set[str] = set()
    for rec in records:
        if rec.material == "Vacuum" or not rec.sensitive:
            continue
        if rec.detector_name:
            det_name = rec.detector_name
        else:
            det_name = f"{rec.name}_SD"
        if det_name in used:
            det_name = f"{rec.name}_SD"
        used.add(det_name)
        threshold = 80.0 if rec.material == "CsI" else rec.threshold_kev
        sigma = rec.energy_resolution_sigma_kev
        if rec.detector_type == "MDCalorimeter":
            block = mdcalorimeter_block(
                det_name,
                rec.name,
                rec.detector_volume or rec.name,
                threshold,
                rec.structural_pitch_cm or (0.155, 0.155, 0.1),
                sigma,
            )
        else:
            block = scintillator_block(det_name, rec.name, threshold, sigma)
        if rec.material == "CsI":
            block = block.replace(
                f"{det_name}.TriggerThreshold 80\n",
                f"{det_name}.TriggerThreshold 80\n{det_name}.NoiseThresholdEqualsTriggerThreshold true\n",
            )
        lines.append(block)
    lines.append("// Native MEGAlib Trigger/Veto blocks intentionally absent in this proxy scaffold.\n")
    write_text(DET, "\n".join(lines))


def build_geo(bounds: dict[str, Any]) -> tuple[str, list[GeneratedVolume], dict[str, list[str]]]:
    builder = GeometryBuilder()
    for comp in bounds["COMPONENTS"]:
        builder.add_component(comp)
    return "".join(builder.geo), builder.records, builder.component_to_volumes


def write_overlap_source() -> None:
    text = f"""Version                     1
Geometry                    {SETUP}
CheckForOverlaps            10000 0.0001
PhysicsListEM               LivermorePol
Run Minimum
Minimum.FileName            /tmp/DelMe_v3p5_centerfinger_proxy_overlap
Minimum.NEvents             1
Minimum.Source MinimumS
MinimumS.ParticleType       1
MinimumS.Beam               PointSource 0 0 0
MinimumS.Spectrum           Mono 511
MinimumS.Flux               1.0
"""
    write_text(OVERLAP_SOURCE, text)


def run_cosima_overlap() -> dict[str, Any]:
    write_overlap_source()
    if not COSIMA.exists():
        write_text(OVERLAP_LOG, f"ERROR: missing cosima executable: {COSIMA}\n")
        return {"available": False, "status": "MISSING_COSIMA", "path": rel(OVERLAP_LOG), "problems": ["missing_cosima"]}
    proc = subprocess.run(
        [str(COSIMA), str(OVERLAP_SOURCE)],
        cwd=OUT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    write_text(OVERLAP_LOG, proc.stdout)
    patterns = {
        "overlap_warnings": "GeomVol1002",
        "duplicate_material": "already exists",
        "detector_init_failure": "Unable to initalize",
        "detector_initialize_failure": "Unable to initialize",
        "geometry_parse_error": "Unable to parse",
        "missing_run_summary": "Summary for run Minimum",
    }
    problems: list[str] = []
    for label, pattern in patterns.items():
        present = pattern in proc.stdout
        if label == "missing_run_summary":
            if not present:
                problems.append(label)
        elif present:
            problems.append(label)
    return {
        "available": True,
        "status": "PASS" if proc.returncode == 0 and not problems else "FAIL",
        "returncode": proc.returncode,
        "path": rel(OVERLAP_LOG),
        "problems": problems,
    }


def generated_summary(records: list[GeneratedVolume]) -> dict[str, Any]:
    by_material: dict[str, int] = {}
    by_category: dict[str, int] = {}
    by_note: dict[str, int] = {}
    by_detector_type: dict[str, int] = {}
    for rec in records:
        by_material[rec.material] = by_material.get(rec.material, 0) + 1
        by_category[rec.category] = by_category.get(rec.category, 0) + 1
        by_note[rec.proxy_note] = by_note.get(rec.proxy_note, 0) + 1
        if rec.sensitive and rec.material != "Vacuum":
            by_detector_type[rec.detector_type] = by_detector_type.get(rec.detector_type, 0) + 1
    return {
        "generated_volume_count": len(records),
        "generated_by_material": dict(sorted(by_material.items())),
        "generated_by_category": dict(sorted(by_category.items())),
        "proxy_note_counts": dict(sorted(by_note.items())),
        "sensitive_detector_type_counts": dict(sorted(by_detector_type.items())),
    }


def detector_core_check(records: list[GeneratedVolume], bounds: dict[str, Any]) -> dict[str, Any]:
    comps = bounds["COMPONENTS"]
    tes = next(c for c in comps if c["name"] == "TES_Ta_Absorber_Stack_side_entry")
    p = tes["params"]
    expected_layers = int(p["n_layers"])
    expected_pixels = int(p["pixels_per_layer"])
    expected_total = expected_layers * expected_pixels
    templates = sorted(r.name for r in records if re.fullmatch(r"TES_Pixel_L\d+", r.name))
    containers = sorted(r.name for r in records if re.fullmatch(r"TES_L\d+", r.name))
    slab_records = sorted(r.name for r in records if re.fullmatch(r"TES_Ta_Absorber_L\d+", r.name))
    copy_counts: dict[str, int] = {}
    for rec in records:
        m = re.fullmatch(r"TP_L(\d+)_(\d{5})", rec.name)
        if m:
            layer = m.group(1)
            copy_counts[layer] = copy_counts.get(layer, 0) + 1
    md_records = sorted(
        r.detector_name or r.name
        for r in records
        if r.detector_type == "MDCalorimeter" and r.sensitive and r.material == "Ta"
    )
    pixel_size = [float(v) for v in p["pixel_size_cm"]]
    active_volume_cm3 = expected_total
    for value in pixel_size:
        active_volume_cm3 *= value
    source_volume_cm3 = float(tes["volume_cm3"])
    volume_ratio = active_volume_cm3 / source_volume_cm3 if source_volume_cm3 else 0.0
    problems = []
    if len(templates) != expected_layers:
        problems.append("wrong_tes_pixel_template_count")
    if len(containers) != expected_layers:
        problems.append("wrong_tes_detector_volume_count")
    if slab_records:
        problems.append("tes_slab_fallback_present")
    if sum(copy_counts.values()) != expected_total:
        problems.append("wrong_total_tes_pixel_copy_count")
    if any(copy_counts.get(str(i), 0) != expected_pixels for i in range(expected_layers)):
        problems.append("wrong_tes_pixel_copy_count_by_layer")
    if len(md_records) != expected_layers:
        problems.append("wrong_mdcalorimeter_record_count")
    if abs(volume_ratio - 1.0) > 1.0e-9:
        problems.append("tes_active_volume_mismatch")
    return {
        "status": "PASS" if not problems else "FAIL",
        "problems": problems,
        "expected_layers": expected_layers,
        "expected_pixels_per_layer": expected_pixels,
        "expected_total_pixels": expected_total,
        "pixel_templates": templates,
        "detector_volumes": containers,
        "pixel_copies_by_layer": {str(i): copy_counts.get(str(i), 0) for i in range(expected_layers)},
        "total_pixel_copies": sum(copy_counts.values()),
        "mdcalorimeter_records": md_records,
        "slab_records": slab_records,
        "source_active_volume_cm3": source_volume_cm3,
        "generated_active_volume_cm3": active_volume_cm3,
        "active_volume_ratio": volume_ratio,
    }


def design_input_checks(bounds: dict[str, Any]) -> dict[str, Any]:
    comps = bounds["COMPONENTS"]
    by_name = {c["name"]: c for c in comps}
    validation = load_json(REF_VALIDATION) if REF_VALIDATION.exists() else {}
    support = by_name["Cu_SubstrateSupport_SolidDisk_L0_deepest"]["params"]
    fingers = [c for c in comps if c["name"].startswith("Cu_ColdFinger_OffAxis_")]
    stems = [c for c in comps if c["name"].startswith("Cu_ColdFinger_Stem_")]
    pads = [c for c in comps if c["name"].startswith("Cu_MXC_Clamp_Pad_")]
    csi03 = by_name["CsI_Side_Segment_03"]["params"].get("side_hole")
    csi04 = by_name["CsI_Side_Segment_04"]["params"].get("side_hole")
    feedthrough_counts = {
        c["name"]: len(c["params"].get("plus_x_thermal_finger_feedthroughs", []))
        for c in comps
        if c["shape"] == "x_can"
    }
    top_slot_counts = {
        c["name"]: len(c["params"].get("top_stem_slots", []))
        for c in comps
        if c["shape"] == "x_can"
    }
    return {
        "source_validation_status": validation.get("status"),
        "source_validation_problem_count": len(validation.get("problems", [])),
        "source_component_count": len(comps),
        "support_disk_clearance_cm": support.get("clearance_to_last_substrate_cm"),
        "offaxis_finger_count": len(fingers),
        "offaxis_stem_count": len(stems),
        "offaxis_pad_count": len(pads),
        "offaxis_finger_radial_offsets_cm": [c["params"].get("radial_offset_from_beam_axis_cm") for c in fingers],
        "csi_side_segment_03_has_hole": csi03 is not None,
        "csi_side_segment_04_has_hole": csi04 is not None,
        "x_can_feedthrough_counts": feedthrough_counts,
        "x_can_top_slot_counts": top_slot_counts,
    }


def beam_path_proxy_check(records: list[GeneratedVolume]) -> dict[str, Any]:
    """Check only generated BRIK proxies whose central aperture should be open.

    A full MEGAlib ray-trace is outside this script. This catches the common
    scaffold error of filling the x-axis support rings/cans/tube with BRIK mass
    on the optical axis y=0, z=-5.2.
    """
    risky = []
    for rec in records:
        if any(token in rec.proxy_note for token in ("center kept open", "central beam aperture kept open", "open-ended")):
            if rec.name.endswith(("_ZP_panel", "_ZM_panel", "_YP_panel", "_YM_panel")):
                continue
            risky.append(rec.name)
    return {
        "status": "PASS" if not risky else "FAIL",
        "risky_centerline_proxy_names": risky,
    }


def write_readme(bounds: dict[str, Any], records: list[GeneratedVolume], overlap: dict[str, Any], extents: dict[str, Any]) -> None:
    summary = generated_summary(records)
    lines = [
        f"# {GEOM_NAME}",
        "",
        "This directory contains a MEGAlib/Cosima proxy scaffold generated from the v3p5 center-finger bounds package.",
        "",
        "Generated files:",
        f"- `{GEO.name}`",
        f"- `{DET.name}`",
        f"- `{SETUP.name}`",
        f"- `{MATERIALS.name}`",
        f"- `{VALIDATION.name}`",
        f"- `{OVERLAP_SOURCE.name}` / `{OVERLAP_LOG.name}`",
        "",
        "Important limitation: this is not final CAD. x-axis windows/substrates/W sleeve/supports are square BRIK-panel proxies, and side holes in z-axis annuli are rectangular azimuth/z cutouts.",
        "",
        "Detector-core fidelity: the TES stack is emitted as 6 MDCalorimeter layers with 376 Ta pixel copies per layer, rotated for the side-entry beam axis.",
        "",
        "Pointing policy: generated detector volumes are children of an invisible `InstrumentFrame` rotated by `0 45 0` degrees. The local side-window look axis `-x` therefore points 45 degrees above the global horizon in the zenith-frame source coordinates.",
        "",
        "Checks:",
        f"- source design validation: `{load_json(REF_VALIDATION).get('status') if REF_VALIDATION.exists() else 'UNKNOWN'}`",
        f"- source components: `{len(bounds['COMPONENTS'])}`",
        f"- generated MEGAlib volumes: `{summary['generated_volume_count']}`",
        f"- TES pixel copies: `{detector_core_check(records, bounds)['total_pixel_copies']}`",
        f"- rotated geometry bounding radius: `{extents['bounding_radius_cm']:.6g} cm`",
        f"- setup/far-field radius: `{extents['recommended_farfield_radius_cm']:.6g} cm`",
        f"- side-window sky elevation: `{extents['instrument_frame']['side_window_look_elevation_deg']:.6g} deg`",
        f"- Cosima overlap status: `{overlap.get('status')}`",
        "",
        "Use this scaffold for MEGAlib syntax/load and simulation-level closure. For CAD-level transport, replace remaining BRIK x-axis proxies with rotated PCON/TUBE or the project's Boolean CSG implementation.",
        "",
    ]
    write_text(README, "\n".join(lines))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    bounds = load_json(REF_BOUNDS)

    write_materials()
    write_intro()
    geo_text, records, component_to_volumes = build_geo(bounds)
    write_text(GEO, geo_text)
    write_det(records)
    extents = parse_generated_geometry_extents(geo_text)
    write_setup(extents)

    shutil.copy2(REF_BOUNDS, OUT / REF_BOUNDS.name)
    shutil.copy2(REF_MASS, OUT / "mass_budget.csv")
    if REF_VALIDATION.exists():
        shutil.copy2(REF_VALIDATION, OUT / REF_VALIDATION.name)
    if REF_GUIDE.exists():
        shutil.copy2(REF_GUIDE, OUT / REF_GUIDE.name)

    overlap = run_cosima_overlap()
    checks = {
        "design_input": design_input_checks(bounds),
        "generated": generated_summary(records),
        "detector_core": detector_core_check(records, bounds),
        "component_to_generated_volumes": component_to_volumes,
        "beam_path_proxy": beam_path_proxy_check(records),
        "cosima_overlap": overlap,
        "known_scaffold_limitations": [
            "x-axis windows, substrates, W sleeve, annuli, cans, and rods use square BRIK/panel proxies instead of rotated PCON/TUBE or Boolean CAD.",
            "z-axis side ports are approximated by rectangular z-band plus azimuth cutouts, not exact circular Boolean holes.",
            "TES absorber stack is pixelized as 6 x 376 side-entry Ta pixels, matching the DEMO2/new_geo_re detector-core convention.",
            "Native MEGAlib Trigger/Veto blocks are not added; downstream veto timing remains separate.",
        ],
    }
    problems = []
    design = checks["design_input"]
    if design["source_validation_status"] != "DESIGN_PASS":
        problems.append("source_validation_not_design_pass")
    if design["source_validation_problem_count"] != 0:
        problems.append("source_validation_has_problems")
    if design["offaxis_finger_count"] != 4 or design["offaxis_stem_count"] != 4 or design["offaxis_pad_count"] != 4:
        problems.append("four_offaxis_thermal_paths_not_preserved")
    if not design["csi_side_segment_03_has_hole"] or not design["csi_side_segment_04_has_hole"]:
        problems.append("shared_csi_side_hole_not_preserved")
    if checks["detector_core"]["status"] != "PASS":
        problems.append("detector_core_not_faithful")
    if checks["beam_path_proxy"]["status"] != "PASS":
        problems.append("beam_path_proxy_centerline_risk")
    if overlap.get("status") != "PASS":
        problems.append("cosima_overlap_not_pass")

    payload = {
        "geometry_name": GEOM_NAME,
        "status": "PROXY_PASS" if not problems else "PROXY_NEEDS_REVIEW",
        "problems": problems,
        "source_bounds": rel(REF_BOUNDS),
        "generated_setup": rel(SETUP),
        "checks": checks,
        "geometry_extents": extents,
    }
    write_text(VALIDATION, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    write_readme(bounds, records, overlap, extents)
    print(json.dumps({"status": payload["status"], "problems": problems, "overlap": overlap}, indent=2))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
