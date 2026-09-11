#!/usr/bin/env python3
"""Generate the f=10 m Ge(111) MULTIBAND Laue design package.

This is the multi-ring extension of ``tools/make_f10m_config.py``. Where the
single-ring A1/A2 configs focus only 511 keV, this design tiles the
450-550 keV band with six coplanar Ge(111) rings, so the lens has a spectral
response across the band instead of at 511 keV alone.

Physics note (read before using the numbers):
  * All six rings share the SAME 30 arcsec mosaic and the SAME 10.218801 mm
    crystal thickness (thickness is locked to XOP-curve validity). Only the
    ring RADIUS changes, which selects the ring's design/Bragg energy.
  * Band coverage is bought by splitting the radial real-estate across six
    thin rings. Per-energy effective area therefore drops to a few cm^2 per
    ring, versus ~20 cm^2 for the single 511 keV A1 ring. This is a real
    area-for-band trade, not a bookkeeping artefact.
  * A_eff numbers written here are DESIGN-STAGE estimates using the same
    reference diffracted fraction (0.25184) that the A1 estimate uses. They
    are NOT simulated. Run laue_multiring_bfull_demo on the emitted config to
    get transported A_eff.

Support structure is scaled from the project's own optics near-field mass
proxy (add_mass/.../optics/OpticsNearfield_GeAndSupport_v2.geo, OF1 budget):
G10 tile-carrier annulus + Al outer mount annulus + four Al brackets.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

# --- locked optical constants (identical to make_f10m_config.py) -------------
HC_KEV_A = 12.398419843320026
D_SPACING_A = 3.266590088
FOCAL_MM = 10000.0
Z_OFFSET_MM = 0.0
THICKNESS_MM = 10.218801            # HARD-LOCKED: XOP curve validity depends on it
GE_DENSITY_G_CM3 = 5.3234
DIFFRACTED_FRACTION_REFERENCE = 0.25184
MOSAIC_FWHM_ARCSEC = 30.0

# --- multiband design knobs --------------------------------------------------
# 511 kept exact so the design contains the A1 anchor energy; +/-20 keV steps
# are ~ one natural-passband FWHM apart at this energy/mosaic.
ENERGIES_KEV = [451.0, 471.0, 491.0, 511.0, 531.0, 551.0]
RADIAL_DEPTH_MM = 2.2              # thin so neighbouring rings clear each other
TANGENTIAL_PITCH_MM = 2.3         # square tiles tiled densely -> thin annulus
CLEARANCE_MM = 0.3

# --- support-structure proxy (materials/densities from project OF1 budget) ---
G10_DENSITY_G_CM3 = 1.850
AL_DENSITY_G_CM3 = 2.700
MODEL_NAME = "balloon511_f10m_ge111_multiband"


def bragg(energy_kev: float) -> tuple[float, float]:
    wl = HC_KEV_A / energy_kev
    theta = math.asin(wl / (2.0 * D_SPACING_A))
    radius_mm = (FOCAL_MM - Z_OFFSET_MM) * math.tan(2.0 * theta)
    return theta, radius_mm


def natural_passband_kev(energy_kev: float, theta_b: float) -> tuple[float, float]:
    mosaic_rad = MOSAIC_FWHM_ARCSEC / 3600.0 * math.pi / 180.0
    d_e_over_e = (1.0 / math.tan(theta_b)) * mosaic_rad
    half = d_e_over_e * energy_kev / 2.0
    return energy_kev - half, energy_kev + half


def build_rings() -> list[dict]:
    rings = []
    for i, e in enumerate(ENERGIES_KEV):
        theta, r = bragg(e)
        n_tiles = int(math.floor(2.0 * math.pi * r / TANGENTIAL_PITCH_MM))
        tile_cm = RADIAL_DEPTH_MM / 10.0
        geom_area = n_tiles * tile_cm * tile_cm
        volume = geom_area * (THICKNESS_MM / 10.0)
        pb_lo, pb_hi = natural_passband_kev(e, theta)
        rings.append(
            {
                "ring_id": i,
                "design_energy_keV": e,
                "theta_b_rad": theta,
                "radius_mm": r,
                "n_tiles": n_tiles,
                "tile_size_mm": RADIAL_DEPTH_MM,
                "geometric_area_cm2": geom_area,
                "volume_cm3": volume,
                "ge_mass_g": volume * GE_DENSITY_G_CM3,
                "expected_aeff_cm2": geom_area * DIFFRACTED_FRACTION_REFERENCE,
                "natural_passband_keV": [pb_lo, pb_hi],
            }
        )
    return rings


def check_gaps(rings: list[dict]) -> list[dict]:
    radii = sorted(r["radius_mm"] for r in rings)
    need = RADIAL_DEPTH_MM + CLEARANCE_MM
    checks = []
    for a, b in zip(radii, radii[1:]):
        checks.append({"inner_mm": a, "outer_mm": b, "gap_mm": b - a,
                       "need_mm": need, "fits": (b - a) >= need})
    return checks


def write_config(path: Path, rings: list[dict]) -> None:
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ring_id", "design_energy_keV", "radius_mm", "n_tiles",
                    "material", "h", "k", "l", "d_spacing_A", "tile_size_mm",
                    "thickness_mm", "z_offset_mm"])
        for r in rings:
            w.writerow([r["ring_id"], f"{r['design_energy_keV']:.1f}",
                        f"{r['radius_mm']:.6f}", r["n_tiles"], "Ge", 1, 1, 1,
                        f"{D_SPACING_A:.9f}", f"{r['tile_size_mm']:.6f}",
                        f"{THICKNESS_MM:.6f}", f"{Z_OFFSET_MM:.6f}"])


def write_xop_map(path: Path, rings: list[dict]) -> None:
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ring_id", "design_energy_keV", "curve_csv", "source", "status"])
        for r in rings:
            if abs(r["design_energy_keV"] - 511.0) < 1e-6:
                w.writerow([r["ring_id"], "511.0", "ge111_511keV_rocking_curve.csv",
                            "CRYSTAL-diff_pat", "covered"])
            else:
                # No external curve at this energy yet. The C++ internal
                # Darwin-Hamilton backend (Ge111, energy-scaled) supplies a
                # first-look fallback when run WITHOUT --require-rocking-curve-map.
                w.writerow([r["ring_id"], f"{r['design_energy_keV']:.1f}", "",
                            "internal_darwin_fallback", "NEEDS_EXTERNAL_CURVE"])


def support_structure() -> dict:
    """G10 carrier + Al mount + 4 Al brackets, scaled to the multiband band.

    Local coordinate mirrors the project OF1/OF2 proxy: focused beam along +x,
    lens plane at x=0. Radii bracket the 67.8-85.3 mm tile band.
    """
    # G10 tile-carrier annulus just inside the Al mount, 1 mm thick, at x=+0.70
    g10 = {"material": "G10", "ri_cm": 5.5, "ro_cm": 8.8, "half_thk_cm": 0.05,
           "x_cm": 0.70}
    g10["volume_cm3"] = math.pi * (g10["ro_cm"]**2 - g10["ri_cm"]**2) * (2*g10["half_thk_cm"])
    g10["mass_kg"] = g10["volume_cm3"] * G10_DENSITY_G_CM3 / 1000.0
    # Al outer mount annulus
    al = {"material": "Aluminium", "ri_cm": 8.8, "ro_cm": 11.5, "half_thk_cm": 0.25,
          "x_cm": 0.0}
    al["volume_cm3"] = math.pi * (al["ro_cm"]**2 - al["ri_cm"]**2) * (2*al["half_thk_cm"])
    al["mass_kg"] = al["volume_cm3"] * AL_DENSITY_G_CM3 / 1000.0
    # 4 Al brackets, BRIK half-dims 0.5 x 1.0 x 2.0 cm, at +/-15 cm y & z
    brk = {"material": "Aluminium", "half_dims_cm": [0.5, 1.0, 2.0], "copies": 4}
    brk["volume_cm3"] = 8.0 * brk["copies"]
    brk["mass_kg"] = brk["volume_cm3"] * AL_DENSITY_G_CM3 / 1000.0
    return {"g10_carrier": g10, "al_outer_mount": al, "al_brackets": brk,
            "support_mass_kg": g10["mass_kg"] + al["mass_kg"] + brk["mass_kg"]}


def write_geo(path: Path, rings: list[dict], support: dict, ge_vol_cm3: float) -> None:
    """Emit a MEGAlib .geo lens+support MASS PROXY (OF1/OF2 convention).

    Ge is represented as an equal-volume annulus over the true tile band, thinned
    so its volume equals the exact tiled Ge volume (mass proxy, not tile geometry).
    """
    band_inner_cm = (min(r["radius_mm"] for r in rings) - RADIAL_DEPTH_MM / 2.0) / 10.0
    band_outer_cm = (max(r["radius_mm"] for r in rings) + RADIAL_DEPTH_MM / 2.0) / 10.0
    footprint_cm2 = math.pi * (band_outer_cm**2 - band_inner_cm**2)
    half_thk_cm = ge_vol_cm3 / (2.0 * footprint_cm2)  # preserve exact Ge volume
    g10 = support["g10_carrier"]; al = support["al_outer_mount"]
    lines = [
        "// f10m Ge(111) MULTIBAND lens + support MASS PROXY (design-stage).",
        "// Local coordinate: focused beam along +x, lens plane at x=0.",
        "// Ge = equal-volume annulus over the 6-ring tile band (mass proxy,",
        "// NOT the optical tile geometry). Support scaled from project OF1 model.",
        "",
        "Volume MB_GeActiveMass_EqualVolumeAnnulus",
        "MB_GeActiveMass_EqualVolumeAnnulus.Material GeProxy",
        "MB_GeActiveMass_EqualVolumeAnnulus.Visibility 1",
        f"MB_GeActiveMass_EqualVolumeAnnulus.Shape PCON 0 360 2 "
        f"{-half_thk_cm:.6f} {band_inner_cm:.6f} {band_outer_cm:.6f} "
        f"{half_thk_cm:.6f} {band_inner_cm:.6f} {band_outer_cm:.6f}",
        "MB_GeActiveMass_EqualVolumeAnnulus.Rotation 0 90 0",
        "MB_GeActiveMass_EqualVolumeAnnulus.Position 0 0 0",
        "MB_GeActiveMass_EqualVolumeAnnulus.Mother InstrumentFrame",
        "",
        "Volume MB_LensCarrier_G10_Annulus",
        "MB_LensCarrier_G10_Annulus.Material G10",
        "MB_LensCarrier_G10_Annulus.Visibility 1",
        f"MB_LensCarrier_G10_Annulus.Shape PCON 0 360 2 "
        f"{-g10['half_thk_cm']:.6f} {g10['ri_cm']:.6f} {g10['ro_cm']:.6f} "
        f"{g10['half_thk_cm']:.6f} {g10['ri_cm']:.6f} {g10['ro_cm']:.6f}",
        "MB_LensCarrier_G10_Annulus.Rotation 0 90 0",
        f"MB_LensCarrier_G10_Annulus.Position {g10['x_cm']:.2f} 0 0",
        "MB_LensCarrier_G10_Annulus.Mother InstrumentFrame",
        "",
        "Volume MB_LensOuterMount_Al_Annulus",
        "MB_LensOuterMount_Al_Annulus.Material Aluminium",
        "MB_LensOuterMount_Al_Annulus.Visibility 1",
        f"MB_LensOuterMount_Al_Annulus.Shape PCON 0 360 2 "
        f"{-al['half_thk_cm']:.6f} {al['ri_cm']:.6f} {al['ro_cm']:.6f} "
        f"{al['half_thk_cm']:.6f} {al['ri_cm']:.6f} {al['ro_cm']:.6f}",
        "MB_LensOuterMount_Al_Annulus.Rotation 0 90 0",
        "MB_LensOuterMount_Al_Annulus.Position 0 0 0",
        "MB_LensOuterMount_Al_Annulus.Mother InstrumentFrame",
        "",
        "Volume MB_LensMountBracket_Al",
        "MB_LensMountBracket_Al.Material Aluminium",
        "MB_LensMountBracket_Al.Visibility 1",
        "MB_LensMountBracket_Al.Shape BRIK 0.5 1.0 2.0",
    ]
    for tag, y, z in [("YP", 15.0, 0.0), ("YM", -15.0, 0.0),
                      ("ZP", 0.0, 15.0), ("ZM", 0.0, -15.0)]:
        lines += [f"MB_LensMountBracket_Al.Copy MB_LensMountBracket_{tag}",
                  f"MB_LensMountBracket_{tag}.Position 0 {y} {z}",
                  f"MB_LensMountBracket_{tag}.Mother InstrumentFrame"]
    path.write_text("\n".join(lines) + "\n")
    return {"ge_annulus_inner_cm": band_inner_cm, "ge_annulus_outer_cm": band_outer_cm,
            "ge_annulus_half_thickness_cm": half_thk_cm}


def main() -> None:
    here = Path(__file__).resolve().parent
    rings = build_rings()
    gaps = check_gaps(rings)
    support = support_structure()
    ge_vol = sum(r["volume_cm3"] for r in rings)
    ge_mass = ge_vol * GE_DENSITY_G_CM3 / 1000.0

    cfg = here / "ge111_balloon511_f10m_multiband_line_config.csv"
    xop = here / "ge111_balloon511_f10m_multiband_xop_map.csv"
    geo = here / "OpticsMultiband_GeAndSupport_f10m.geo"
    write_config(cfg, rings)
    write_xop_map(xop, rings)
    ge_annulus = write_geo(geo, rings, support, ge_vol)

    summary = {
        "model": MODEL_NAME,
        "focal_length_mm": FOCAL_MM,
        "d_spacing_A": D_SPACING_A,
        "thickness_mm": THICKNESS_MM,
        "mosaic_fwhm_arcsec": MOSAIC_FWHM_ARCSEC,
        "energies_keV": ENERGIES_KEV,
        "radial_depth_mm": RADIAL_DEPTH_MM,
        "tangential_pitch_mm": TANGENTIAL_PITCH_MM,
        "rings": rings,
        "adjacent_gap_checks": gaps,
        "all_rings_fit": all(c["fits"] for c in gaps),
        "band_coverage_keV_fwhm": [rings[0]["natural_passband_keV"][0],
                                   rings[-1]["natural_passband_keV"][1]],
        "totals": {
            "ge_volume_cm3": ge_vol,
            "ge_mass_kg": ge_mass,
            "support_mass_kg": support["support_mass_kg"],
            "lens_total_mass_kg": ge_mass + support["support_mass_kg"],
            "per_energy_expected_aeff_cm2_range": [
                min(r["expected_aeff_cm2"] for r in rings),
                max(r["expected_aeff_cm2"] for r in rings)],
        },
        "support_structure": support,
        "ge_mass_proxy_annulus": ge_annulus,
        "provenance": {
            "single_ring_reference": "balloon511_f10m_ge111_511line (A1), A_eff(511)~20.1 cm2",
            "support_model_source":
                "add_mass/TES_511_Balloon_nearfield_mass_proxy_v2/optics/"
                "OpticsNearfield_GeAndSupport_v2.geo (OF1 budget)",
            "aeff_status": "DESIGN-STAGE estimate (reference diffracted fraction "
                           "0.25184); NOT simulated. Run laue_multiring_bfull_demo "
                           "for transported A_eff.",
            "curve_status": "Only 511 keV has an external XOP/CRYSTAL curve; the "
                            "other five energies use the internal energy-scaled "
                            "Ge(111) Darwin fallback until curves are generated.",
        },
    }
    (here / "ge111_balloon511_f10m_multiband_design_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n")

    print(f"wrote {cfg.name}")
    print(f"wrote {xop.name}")
    print(f"wrote {geo.name}")
    print("wrote ge111_balloon511_f10m_multiband_design_summary.json")
    print(f"rings={len(rings)}  all_fit={summary['all_rings_fit']}  "
          f"Ge={ge_mass:.4f}kg support={support['support_mass_kg']:.4f}kg "
          f"total={ge_mass + support['support_mass_kg']:.4f}kg")
    print(f"per-energy A_eff(design) ~ "
          f"{summary['totals']['per_energy_expected_aeff_cm2_range'][0]:.2f}"
          f"..{summary['totals']['per_energy_expected_aeff_cm2_range'][1]:.2f} cm2")


if __name__ == "__main__":
    main()
