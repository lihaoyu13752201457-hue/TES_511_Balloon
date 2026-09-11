#!/usr/bin/env python3
"""Build the 2026-06-01 Route-A Laue lens design package."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
STEP_DIR = ROOT / "stepwise_maintenance" / "step04_opticsim"
OUT_DIR = STEP_DIR / "outputs" / "opticsim_laue_bfull_xopmap_real"
OPTICSIM_CONFIG = Path("/home/ubuntu/opticsim/data/laue/ge111_balloon511_f9m_511keV_line_config.csv")
REPO_RING_CONFIG = STEP_DIR / "ge111_balloon511_f9m_511keV_line_config.csv"
ROCKING_CURVE_MAP = STEP_DIR / "ge111_balloon511_f9m_511keV_xop_map.csv"
XOP_CURVE_DIR = Path("/home/ubuntu/cross_check_laue/laue511_validation/benchmarks/xop_crystal/multiring")
LAUE511_CROSSCHECK_SUMMARY = Path(
    "/home/ubuntu/cross_check_laue/laue511_validation/reports/laue511_crosscheck_summary.md"
)

DESIGN_NAME = "balloon511_f9m_ge111_511line"
FOCAL_LENGTH_MM = 9000.0
TILE_SIZE_MM = 15.0
PACKING_PITCH_FACTOR = 1.0
RING_Z_PITCH_MM = 0.0
MOSAIC_FWHM_ARCSEC = 30.0
DESIGN_AEFF_511_CM2 = 16.0
DESIGN_AEFF_TOLERANCE_FRACTION = 0.15
GE_DENSITY_G_CM3 = 5.323
D_SPACING_A = 3.266590088
HC_KEV_A = 12.398419843320026
BE_RADIUS_CM = 1.898
RING_ENERGIES_KEV = [(0, 511.0)]
ENERGIES_KEV = [energy for _, energy in RING_ENERGIES_KEV]
THICKNESS_BY_ENERGY_MM = {
    480.0: 9.452263,
    500.0: 9.947306,
    511.0: 10.218801,
    530.0: 10.686285,
    550.0: 11.176250,
}
ROCKING_CURVE_BY_ENERGY = {
    511.0: XOP_CURVE_DIR / "ge111_511keV_rocking_curve.csv",
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def bragg_angle_rad(energy_kev: float) -> float:
    return math.asin((HC_KEV_A / energy_kev) / (2.0 * D_SPACING_A))


def ring_z_offset_mm(ring_id: int) -> float:
    center = 0.5 * (len(RING_ENERGIES_KEV) - 1)
    return (float(ring_id) - center) * RING_Z_PITCH_MM


def ring_radius_mm(energy_kev: float, z_offset_mm: float = 0.0) -> float:
    return (FOCAL_LENGTH_MM - z_offset_mm) * math.tan(2.0 * bragg_angle_rad(energy_kev))


def mosaic_fwhm_rad() -> float:
    return math.radians(MOSAIC_FWHM_ARCSEC / 3600.0)


def natural_passband_fwhm(energy_kev: float) -> dict[str, float]:
    theta = bragg_angle_rad(energy_kev)
    frac = math.cos(theta) / math.sin(theta) * mosaic_fwhm_rad()
    width = energy_kev * frac
    return {
        "center_keV": energy_kev,
        "fwhm_keV": width,
        "lo_keV": energy_kev - 0.5 * width,
        "hi_keV": energy_kev + 0.5 * width,
        "relative_fwhm": frac,
        "formula": "DeltaE/E = cot(theta_B) * mosaic_FWHM_rad",
    }


def thickness_mm(energy_kev: float) -> float:
    if energy_kev in THICKNESS_BY_ENERGY_MM:
        return THICKNESS_BY_ENERGY_MM[energy_kev]
    anchors = sorted(THICKNESS_BY_ENERGY_MM.items())
    for (e0, t0), (e1, t1) in zip(anchors, anchors[1:]):
        if e0 <= energy_kev <= e1:
            frac = (energy_kev - e0) / (e1 - e0)
            return t0 + frac * (t1 - t0)
    raise ValueError(f"energy {energy_kev} keV is outside thickness interpolation anchors")


def tile_count(radius_mm: float) -> int:
    # Start from the arc-length packing estimate, then enforce non-overlap in
    # chord distance because tiles are placed around a polygonal ring.
    pitch = TILE_SIZE_MM * PACKING_PITCH_FACTOR
    n_tiles = max(1, int(math.floor(2.0 * math.pi * radius_mm / pitch)))
    while n_tiles > 1 and 2.0 * radius_mm * math.sin(math.pi / n_tiles) < TILE_SIZE_MM:
        n_tiles -= 1
    return n_tiles


def design_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ring_id, energy in RING_ENERGIES_KEV:
        z_offset = ring_z_offset_mm(ring_id)
        radius = ring_radius_mm(energy, z_offset)
        n_tiles = tile_count(radius)
        tile_area_cm2 = (TILE_SIZE_MM / 10.0) ** 2
        geom_area_cm2 = n_tiles * tile_area_cm2
        thick = thickness_mm(energy)
        mass_kg = geom_area_cm2 * (thick / 10.0) * GE_DENSITY_G_CM3 / 1000.0
        rows.append(
            {
                "ring_id": ring_id,
                "design_energy_keV": energy,
                "radius_mm": radius,
                "n_tiles": n_tiles,
                "material": "Ge",
                "h": 1,
                "k": 1,
                "l": 1,
                "d_spacing_A": D_SPACING_A,
                "tile_size_mm": TILE_SIZE_MM,
                "thickness_mm": thick,
                "z_offset_mm": z_offset,
                "geometric_area_cm2": geom_area_cm2,
                "ge_mass_kg": mass_kg,
            }
        )
    return rows


def write_ring_config_file(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "ring_id",
        "design_energy_keV",
        "radius_mm",
        "n_tiles",
        "material",
        "h",
        "k",
        "l",
        "d_spacing_A",
        "tile_size_mm",
        "thickness_mm",
        "z_offset_mm",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            out = dict(row)
            out["radius_mm"] = f"{float(row['radius_mm']):.6f}"
            out["design_energy_keV"] = f"{float(row['design_energy_keV']):.1f}"
            out["d_spacing_A"] = f"{float(row['d_spacing_A']):.9f}"
            out["tile_size_mm"] = f"{float(row['tile_size_mm']):.6f}"
            out["thickness_mm"] = f"{float(row['thickness_mm']):.6f}"
            out["z_offset_mm"] = f"{float(row['z_offset_mm']):.6f}"
            writer.writerow({field: out[field] for field in fields})


def write_ring_config(rows: list[dict[str, Any]]) -> None:
    write_ring_config_file(OPTICSIM_CONFIG, rows)
    write_ring_config_file(REPO_RING_CONFIG, rows)


def write_rocking_curve_map(rows: list[dict[str, Any]]) -> None:
    ROCKING_CURVE_MAP.parent.mkdir(parents=True, exist_ok=True)
    fields = ["ring_id", "design_energy_keV", "curve_csv", "source", "status"]
    with ROCKING_CURVE_MAP.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            energy = float(row["design_energy_keV"])
            if energy not in ROCKING_CURVE_BY_ENERGY:
                continue
            writer.writerow(
                {
                    "ring_id": int(row["ring_id"]),
                    "design_energy_keV": f"{energy:.1f}",
                    "curve_csv": str(ROCKING_CURVE_BY_ENERGY[energy]),
                    "source": "CRYSTAL-diff_pat",
                    "status": "covered",
                }
            )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ring_radius_residuals(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    residuals = []
    for row in rows:
        expected = ring_radius_mm(float(row["design_energy_keV"]), float(row.get("z_offset_mm", 0.0)))
        actual = float(row["radius_mm"])
        residuals.append(
            {
                "ring_id": int(row["ring_id"]),
                "energy_keV": float(row["design_energy_keV"]),
                "z_offset_mm": float(row.get("z_offset_mm", 0.0)),
                "radius_mm": actual,
                "expected_radius_mm": expected,
                "abs_residual_mm": abs(actual - expected),
            }
        )
    return residuals


def rocking_curve_coverage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    required = {
        int(row["ring_id"]): float(row["design_energy_keV"])
        for row in rows
        if float(row["design_energy_keV"]) in ROCKING_CURVE_BY_ENERGY
    }
    if not ROCKING_CURVE_MAP.exists():
        return {
            "map_csv": str(ROCKING_CURVE_MAP),
            "required_ring_ids": sorted(required),
            "covered_ring_ids": [],
            "missing_ring_ids": sorted(required),
            "energy_mismatches": [],
            "policy": "The 511-keV science ring is required to use the existing external XOP/CRYSTAL curve.",
            "pass": False,
        }
    map_rows = read_csv(ROCKING_CURVE_MAP)
    covered = {int(row["ring_id"]): float(row["design_energy_keV"]) for row in map_rows}
    energy_mismatches = [
        {"ring_id": ring_id, "required_keV": energy, "mapped_keV": covered.get(ring_id)}
        for ring_id, energy in required.items()
        if ring_id in covered and abs(covered[ring_id] - energy) > 1.0e-9
    ]
    missing = set(required) - set(covered)
    return {
        "map_csv": str(ROCKING_CURVE_MAP),
        "required_ring_ids": sorted(required),
        "covered_ring_ids": sorted(covered),
        "missing_ring_ids": sorted(missing),
        "energy_mismatches": energy_mismatches,
        "online_darwin_ring_ids": [
            int(row["ring_id"])
            for row in rows
            if float(row["design_energy_keV"]) not in ROCKING_CURVE_BY_ENERGY
        ],
        "policy": "The 511-keV science ring is required to use the existing external XOP/CRYSTAL curve.",
        "pass": not missing and not energy_mismatches,
    }


def ring_clearance_check(rows: list[dict[str, Any]]) -> dict[str, Any]:
    radial_order = sorted(rows, key=lambda row: float(row["radius_mm"]), reverse=True)
    radial_gaps = []
    for left, right in zip(radial_order, radial_order[1:]):
        radial_gaps.append(
            {
                "outer_ring_id": int(left["ring_id"]),
                "inner_ring_id": int(right["ring_id"]),
                "radial_center_gap_mm": float(left["radius_mm"]) - float(right["radius_mm"]),
            }
        )
    z_clearances = []
    for i, left in enumerate(rows):
        for right in rows[i + 1 :]:
            z_clearances.append(
                {
                    "ring_a": int(left["ring_id"]),
                    "ring_b": int(right["ring_id"]),
                    "z_center_gap_mm": abs(float(left["z_offset_mm"]) - float(right["z_offset_mm"])),
                    "surface_clearance_mm": abs(float(left["z_offset_mm"]) - float(right["z_offset_mm"]))
                    - 0.5 * (float(left["thickness_mm"]) + float(right["thickness_mm"])),
                }
            )
    azimuthal_gaps = []
    for row in rows:
        radius = float(row["radius_mm"])
        n_tiles = int(row["n_tiles"])
        chord_pitch = 2.0 * radius * math.sin(math.pi / n_tiles)
        azimuthal_gaps.append(
            {
                "ring_id": int(row["ring_id"]),
                "chord_pitch_mm": chord_pitch,
                "azimuthal_edge_gap_mm": chord_pitch - TILE_SIZE_MM,
            }
        )
    min_z_clearance = min((gap["surface_clearance_mm"] for gap in z_clearances), default=None)
    min_azimuthal_gap = min((gap["azimuthal_edge_gap_mm"] for gap in azimuthal_gaps), default=None)
    z_ok = min_z_clearance is None or min_z_clearance > 0.5
    azimuth_ok = min_azimuthal_gap is not None and min_azimuthal_gap >= -1.0e-6
    return {
        "method": "within-ring clearance is checked by adjacent tile chord pitch; if future line-band rings are added, inter-ring clearance is checked in z.",
        "tile_size_mm": TILE_SIZE_MM,
        "z_pitch_mm": RING_Z_PITCH_MM,
        "min_z_surface_clearance_mm": min_z_clearance,
        "min_azimuthal_edge_gap_mm": min_azimuthal_gap,
        "pass": z_ok and azimuth_ok,
        "radial_center_gaps_for_reference": radial_gaps,
        "inter_ring_z_clearances": z_clearances,
        "within_ring_azimuthal_gaps": azimuthal_gaps,
    }


def focal_stats(rows: list[dict[str, str]]) -> dict[str, Any]:
    radii = [
        0.1 * math.hypot(float(row["x_mm"]), float(row["y_mm"]))
        for row in rows
        if row.get("source_tag") == "laue_bfull_diffracted"
    ]
    within = [r for r in radii if r <= BE_RADIUS_CM + 1.0e-9]
    radii_sorted = sorted(radii)
    within_sorted = sorted(within)

    def percentile(values: list[float], p: float) -> float | None:
        if not values:
            return None
        idx = min(len(values) - 1, max(0, math.ceil(p * len(values)) - 1))
        return values[idx]

    return {
        "diffracted_focal_rows": len(radii),
        "within_be_rows": len(within),
        "outside_be_rows": len(radii) - len(within),
        "within_be_fraction": len(within) / len(radii) if radii else None,
        "r50_cm": percentile(radii_sorted, 0.50),
        "r90_cm": percentile(radii_sorted, 0.90),
        "r95_cm": percentile(radii_sorted, 0.95),
        "r99_cm": percentile(radii_sorted, 0.99),
        "r999_cm": percentile(radii_sorted, 0.999),
        "rmax_within_be_cm": max(within_sorted) if within_sorted else None,
        "rmax_all_diffracted_cm": max(radii_sorted) if radii_sorted else None,
        "be_radius_cm": BE_RADIUS_CM,
        "pass_r99_within_be": bool(radii_sorted and percentile(radii_sorted, 0.99) <= BE_RADIUS_CM),
    }


def ring_primary_counts(n_events: int, rows: list[dict[str, Any]]) -> Counter[int]:
    counts: Counter[int] = Counter()
    tile_spans: list[tuple[int, int, int]] = []
    start = 0
    for row in rows:
        n_tiles = int(row["n_tiles"])
        tile_spans.append((int(row["ring_id"]), start, start + n_tiles))
        start += n_tiles
    total_tiles = start
    if total_tiles <= 0:
        return counts
    for event_id in range(n_events):
        idx = event_id % total_tiles
        for ring_id, begin, end in tile_spans:
            if begin <= idx < end:
                counts[ring_id] += 1
                break
    return counts


def build_aeff(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary_path = OUT_DIR / "summary.json"
    per_ring_path = OUT_DIR / "per_ring_summary.csv"
    focal_path = OUT_DIR / "focal_crossings.csv"
    history_path = OUT_DIR / "optics_history.csv"
    run_summary: dict[str, Any] = load_json(summary_path) if summary_path.exists() else {}
    files_available = summary_path.exists() and per_ring_path.exists() and focal_path.exists() and history_path.exists()
    run_matches_design = (
        files_available
        and run_summary.get("ring_config") == str(OPTICSIM_CONFIG)
        and abs(float(run_summary.get("focal_length_mm", -1.0)) - FOCAL_LENGTH_MM) < 1.0e-9
        and int(run_summary.get("n_rings", -1)) == len(rows)
    )
    run_available = files_available and run_matches_design
    per_ring = {int(row["ring_id"]): row for row in read_csv(per_ring_path)} if run_available else {}
    focal_rows = read_csv(focal_path) if run_available else []
    history_rows = read_csv(history_path) if run_available else []
    event_ring: dict[int, int] = {
        int(row["event_id"]): int(row["ring_id"])
        for row in history_rows
        if row.get("stage") == "DIFFRACT"
    }
    within_by_ring: Counter[int] = Counter()
    unmatched_focal_rows = 0
    for row in focal_rows:
        if row.get("source_tag") != "laue_bfull_diffracted":
            continue
        ring_id = event_ring.get(int(row["event_id"]))
        if ring_id is None:
            unmatched_focal_rows += 1
            continue
        radius_cm = 0.1 * math.hypot(float(row["x_mm"]), float(row["y_mm"]))
        if radius_cm <= BE_RADIUS_CM + 1.0e-9:
            within_by_ring[ring_id] += 1
    primaries = ring_primary_counts(int(run_summary.get("n_primaries", 0)), rows) if run_available else Counter()

    energy_rows = []
    for row in rows:
        ring_id = int(row["ring_id"])
        p_ring = per_ring.get(ring_id, {})
        area = float(row["geometric_area_cm2"])
        analytic = float(p_ring.get("analytic_reference_focal_p_diff", "nan")) if p_ring else None
        emergent = None
        if primaries.get(ring_id, 0) > 0:
            emergent = within_by_ring[ring_id] / primaries[ring_id]
        efficiency = emergent if emergent is not None else analytic
        energy_rows.append(
            {
                "ring_id": ring_id,
                "energy_keV": float(row["design_energy_keV"]),
                "geometric_area_cm2": area,
                "n_tiles": int(row["n_tiles"]),
                "analytic_reference_efficiency": analytic,
                "emergent_within_be_efficiency": emergent,
                "adopted_efficiency": efficiency,
                "aeff_cm2": area * efficiency if efficiency is not None else None,
                "within_be_focal_crossings": within_by_ring.get(ring_id, 0) if run_available else None,
                "primaries": primaries.get(ring_id, None) if run_available else None,
            }
        )

    radius_residuals = ring_radius_residuals(rows)
    residual = run_summary.get("emergent_minus_analytic_focal_diffraction")
    residual_abs = abs(float(residual)) if residual is not None else None
    return {
        "design_name": DESIGN_NAME,
        "status": "RUN_AVAILABLE" if run_available else ("STALE_BFULL_RUN_IGNORED" if files_available else "PREDESIGN_NO_BFULL_RUN_YET"),
        "science_policy": "511-keV line optimized Laue lens. 480-550 keV is the TES spectral analysis window, not an equal-weight optical focusing band.",
        "normalization_policy": "A_eff(E) = ring geometric area times B-FULL emergent within-Be focal diffraction efficiency when the run is available. The exact 511-keV line-center A_eff is the optical authority for this line-focused design.",
        "design_target": {
            "aeff_511_design_cm2": DESIGN_AEFF_511_CM2,
            "aeff_tolerance_fraction": DESIGN_AEFF_TOLERANCE_FRACTION,
            "tolerance_policy": "If B-FULL A_eff(511) differs from the 16 cm2 design value by more than 15%, the lens geometry must be adjusted and rerun.",
        },
        "natural_passband_fwhm": natural_passband_fwhm(511.0),
        "ring_config": str(OPTICSIM_CONFIG),
        "ring_config_repo_copy": rel(REPO_RING_CONFIG),
        "rocking_curve_map": rel(ROCKING_CURVE_MAP),
        "bfull_run_dir": rel(OUT_DIR),
        "focal_length_mm": FOCAL_LENGTH_MM,
        "tile_size_mm": TILE_SIZE_MM,
        "mosaic_fwhm_arcsec": MOSAIC_FWHM_ARCSEC,
        "energy_rows": energy_rows,
        "aeff_511_cm2": next((r["aeff_cm2"] for r in energy_rows if abs(r["energy_keV"] - 511.0) < 1.0e-9), None),
        "sampled_line_band_aeff_sum_cm2": sum(float(r["aeff_cm2"]) for r in energy_rows if r["aeff_cm2"] is not None),
        "total_geometric_area_cm2": sum(float(r["geometric_area_cm2"]) for r in rows),
        "total_tiles": sum(int(r["n_tiles"]) for r in rows),
        "total_ge_mass_kg": sum(float(r["ge_mass_kg"]) for r in rows),
        "bragg_radius_check": {
            "max_abs_residual_mm": max(r["abs_residual_mm"] for r in radius_residuals) if radius_residuals else None,
            "pass_0p2mm_bfull_gate": all(r["abs_residual_mm"] <= 0.2 for r in radius_residuals),
            "per_ring": radius_residuals,
        },
        "ring_clearance_check": ring_clearance_check(rows),
        "rocking_curve_map_coverage": rocking_curve_coverage(rows),
        "focal_stats": focal_stats(focal_rows) if focal_rows else None,
        "ring_id_reconstruction": {
            "source": rel(history_path),
            "method": "focal_crossings.csv has no ring_id, so diffracted focal rows are joined to optics_history.csv DIFFRACT rows by event_id.",
            "unmatched_diffracted_focal_rows": unmatched_focal_rows if run_available else None,
        },
        "run_summary": {
            "run_matches_design": run_matches_design,
            "n_primaries": run_summary.get("n_primaries"),
            "emergent_focal_diffraction_fraction": run_summary.get("emergent_focal_diffraction_fraction"),
            "analytic_reference_focal_diffraction_fraction": run_summary.get("analytic_reference_focal_diffraction_fraction"),
            "emergent_minus_analytic_focal_diffraction": run_summary.get("emergent_minus_analytic_focal_diffraction"),
            "abs_emergent_minus_analytic_focal_diffraction": residual_abs,
            "pass_crosscheck_0p04_gate": residual_abs <= 0.04 if residual_abs is not None else None,
            "pass_strict_0p01_gate": residual_abs < 0.01 if residual_abs is not None else None,
            "rocking_curve_backend": run_summary.get("rocking_curve_backend"),
            "rocking_curve_map_csv": run_summary.get("rocking_curve_map_csv"),
        },
    }


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fmt(value: Any, nd: int = 6) -> str:
    if value is None:
        return "not_run"
    if isinstance(value, float):
        if not math.isfinite(value):
            return "nan"
        if abs(value) < 1.0e-3 or abs(value) >= 1.0e5:
            return f"{value:.{nd}e}"
        return f"{value:.{nd}g}"
    return str(value)


def write_rationale(rows: list[dict[str, Any]], aeff: dict[str, Any]) -> None:
    focal = aeff.get("focal_stats") or {}
    clearance = aeff.get("ring_clearance_check") or {}
    passband = aeff.get("natural_passband_fwhm") or {}
    design_target = aeff.get("design_target") or {}
    aeff_511 = aeff.get("aeff_511_cm2")
    aeff_delta = (
        abs(float(aeff_511) - float(design_target.get("aeff_511_design_cm2", DESIGN_AEFF_511_CM2)))
        / float(design_target.get("aeff_511_design_cm2", DESIGN_AEFF_511_CM2))
        if aeff_511 is not None
        else None
    )
    lines = [
        "# Route-A B-FULL Laue Lens Design Rationale (2026-06-01)",
        "",
        "## Scope",
        "",
        "This is the review package requested by `LAUE_LENS_DESIGN_SPEC_20260601.md`: design a physically plausible Ge(111) Laue focusing mirror for 480-550 keV, run the B-FULL optical simulation, and stop before the detector full-chain integration.",
        "",
        "## Selected Design",
        "",
        f"- Design name: `{DESIGN_NAME}`.",
        f"- Material/reflection: Ge(111), d = `{D_SPACING_A}` Angstrom.",
        f"- Focal length: `{FOCAL_LENGTH_MM / 1000.0:.1f} m`.",
        f"- Tile size: `{TILE_SIZE_MM:.1f} mm x {TILE_SIZE_MM:.1f} mm`.",
        f"- Ring z pitch: `{RING_Z_PITCH_MM:.1f} mm`.",
        f"- Mosaicity: `{MOSAIC_FWHM_ARCSEC:.1f} arcsec`.",
        f"- Energies: `{', '.join(fmt(e) for e in ENERGIES_KEV)} keV`.",
        f"- Total tiles: `{aeff['total_tiles']}`.",
        f"- Total geometric crystal area: `{fmt(aeff['total_geometric_area_cm2'])} cm2`.",
        f"- Exact 511-keV A_eff: `{fmt(aeff.get('aeff_511_cm2'))} cm2`.",
        f"- Design target A_eff(511): `{fmt(design_target.get('aeff_511_design_cm2'))} cm2` with `{fmt(design_target.get('aeff_tolerance_fraction'))}` fractional tolerance.",
        f"- A_eff target residual: `{fmt(aeff_delta)}`.",
        f"- Sampled line-band A_eff sum: `{fmt(aeff.get('sampled_line_band_aeff_sum_cm2'))} cm2`.",
        f"- Natural mosaic passband FWHM: `{fmt(passband.get('lo_keV'))}-{fmt(passband.get('hi_keV'))} keV` (`{fmt(passband.get('fwhm_keV'))} keV` full width).",
        f"- Ge mass estimate for active crystals only: `{fmt(aeff['total_ge_mass_kg'])} kg`.",
        f"- Outer ring radius plus half tile: `{fmt(max(float(r['radius_mm']) for r in rows) + 0.5 * TILE_SIZE_MM)} mm`.",
        "",
        "## Physical Justification",
        "",
        "- The optical design is now 511-line first. The 480-550 keV interval is treated as the detector analysis window for line fitting and local continuum, not as an equal-weight Laue focusing band.",
        "- The 9 m focal length is the upper end of the 6-9 m balloon-compatible execution envelope and stays close to the 8.3 m 511-CAM Laue-lens scale obtained by scaling the CLAIRE balloon lens concept from 170 keV to 511 keV.",
        "- The optical area is placed in a full-azimuth 511-keV ring rather than split into broad 480/550 keV endpoint rings.",
        "- 15 mm square Ge tiles are at the upper end of the common 5-15 mm Laue-crystal scale and give near-full azimuthal fill at the 511-keV Bragg radius without chord-overlap.",
        "- The 30 arcsec mosaicity gives the design natural FWHM passband through DeltaE/E = cot(theta_B) * mosaic_FWHM_rad. For Ge(111) at 511 keV this is about 511 +/- 10 keV.",
        "- A tested 507-515 keV multi-ring axial stack was rejected because overlapping projected apertures caused upstream rings to shadow the 511-keV anchor ring. This baseline keeps the projected aperture honest.",
        f"- The minimum within-ring azimuthal edge gap is `{fmt(clearance.get('min_azimuthal_edge_gap_mm'))} mm`.",
        "- The 30 arcsec mosaicity is retained because it is the already validated B-FULL baseline and lies inside the 10-60 arcsec quality range quoted for Laue-lens crystals.",
        "- The 511-keV ring uses the existing XOP/CRYSTAL rocking curve and B-FULL is run with the map required.",
        "",
        "Public anchors used for review wording:",
        "",
        "- CLAIRE demonstrated a balloon Laue lens using 556 Ge-Si crystals on eight rings.",
        "- MAX/GRI/LAUE studies use mosaicities around 30 arcsec and focal lengths from about 10 m to much longer formation-flying concepts.",
        "- 511-CAM is a 511-keV line instrument; o-Ps continuum is below 511 keV and is kept as detector-side analysis/future-prospect context rather than the Laue optical driver.",
        "",
        "## Ring Table",
        "",
        "| ring | E keV | z mm | radius mm | n tiles | geom area cm2 | thickness mm | analytic eff | emergent within-Be eff | A_eff cm2 |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    by_ring = {int(r["ring_id"]): r for r in aeff["energy_rows"]}
    for row in rows:
        ar = by_ring[int(row["ring_id"])]
        lines.append(
            f"| {row['ring_id']} | {fmt(float(row['design_energy_keV']))} | {fmt(float(row['z_offset_mm']))} | {fmt(float(row['radius_mm']))} | "
            f"{row['n_tiles']} | {fmt(float(row['geometric_area_cm2']))} | {fmt(float(row['thickness_mm']))} | "
            f"{fmt(ar['analytic_reference_efficiency'])} | {fmt(ar['emergent_within_be_efficiency'])} | {fmt(ar['aeff_cm2'])} |"
        )
    lines.extend(
        [
            "",
            "## Be-Window Focus Check",
            "",
            f"- Be radius requirement: `r99 <= {BE_RADIUS_CM} cm`.",
            f"- Diffracted focal rows: `{fmt(focal.get('diffracted_focal_rows'))}`.",
            f"- Within-Be focal rows: `{fmt(focal.get('within_be_rows'))}`.",
            f"- r95 all diffracted crossings: `{fmt(focal.get('r95_cm'))} cm`.",
            f"- r99 all diffracted crossings: `{fmt(focal.get('r99_cm'))} cm`.",
            f"- Outside-Be focal rows: `{fmt(focal.get('outside_be_rows'))}`.",
            f"- Within-Be fraction: `{fmt(focal.get('within_be_fraction'))}`.",
            f"- Max within-Be focal radius: `{fmt(focal.get('rmax_within_be_cm'))} cm`.",
            f"- Max all-diffracted radius: `{fmt(focal.get('rmax_all_diffracted_cm'))} cm`.",
            f"- Pass: `{focal.get('pass_r99_within_be', 'not_run')}`.",
            "",
            "## Cross-Check Gate",
            "",
            f"- B-FULL run status: `{aeff['status']}`.",
            f"- Rocking curve map: `{ROCKING_CURVE_MAP}`.",
            f"- Emergent focal diffraction fraction: `{fmt(aeff['run_summary'].get('emergent_focal_diffraction_fraction'))}`.",
            f"- Analytic reference focal diffraction fraction: `{fmt(aeff['run_summary'].get('analytic_reference_focal_diffraction_fraction'))}`.",
            f"- Emergent minus analytic: `{fmt(aeff['run_summary'].get('emergent_minus_analytic_focal_diffraction'))}`.",
            f"- Pass <0.04 design-stage gate: `{aeff['run_summary'].get('pass_crosscheck_0p04_gate')}`.",
            f"- Strict <0.01 diagnostic gate: `{aeff['run_summary'].get('pass_strict_0p01_gate')}`.",
            "",
            "## Review Boundary",
            "",
            "Per the design spec, this package stops at the optical design review gate. It does not replace Step07, does not run detector full-chain transport, and does not add lens hardware mass to the DEMO2 background model.",
            "",
            "## Artifacts",
            "",
            f"- Ring config: `{OPTICSIM_CONFIG}`.",
            f"- Repository copy of ring config: `{rel(REPO_RING_CONFIG)}`.",
            f"- Rocking-curve map: `{rel(ROCKING_CURVE_MAP)}`.",
            f"- A_eff authority: `{rel(STEP_DIR / 'optics_aeff_authority.json')}`.",
            f"- Cross-check report: `{rel(STEP_DIR / 'real_design_crosscheck_20260601.md')}`.",
            f"- B-FULL output directory: `{rel(OUT_DIR)}`.",
        ]
    )
    (STEP_DIR / "optics_design_rationale.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT_DIR / "optics_design_rationale.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_crosscheck_report(aeff: dict[str, Any]) -> None:
    focal = aeff.get("focal_stats") or {}
    coverage = aeff.get("rocking_curve_map_coverage") or {}
    bragg = aeff.get("bragg_radius_check") or {}
    clearance = aeff.get("ring_clearance_check") or {}
    run = aeff.get("run_summary") or {}
    target = aeff.get("design_target") or {}
    passband = aeff.get("natural_passband_fwhm") or {}
    aeff_511 = aeff.get("aeff_511_cm2")
    target_value = float(target.get("aeff_511_design_cm2", DESIGN_AEFF_511_CM2))
    target_residual = abs(float(aeff_511) - target_value) / target_value if aeff_511 is not None else None
    lines = [
        "# Route-A Real Laue Design Cross-Check (2026-06-01)",
        "",
        "This is the design-stage gate for the real Ge(111) B-FULL lens. It stops before detector full-chain integration.",
        "",
        "## Gate Summary",
        "",
        "| check | value | pass |",
        "| --- | ---: | :---: |",
        f"| Bragg radius max residual | {fmt(bragg.get('max_abs_residual_mm'))} mm | {bragg.get('pass_0p2mm_bfull_gate')} |",
        f"| min z surface clearance | {fmt(clearance.get('min_z_surface_clearance_mm'))} mm | {clearance.get('pass')} |",
        f"| min azimuthal edge gap | {fmt(clearance.get('min_azimuthal_edge_gap_mm'))} mm | {clearance.get('pass')} |",
        f"| XOP/CRYSTAL map missing rings | {coverage.get('missing_ring_ids')} | {coverage.get('pass')} |",
        f"| XOP/CRYSTAL map energy mismatches | {coverage.get('energy_mismatches')} | {coverage.get('pass')} |",
        f"| diffracted focal r99 | {fmt(focal.get('r99_cm'))} cm | {focal.get('pass_r99_within_be')} |",
        f"| Be radius | {fmt(focal.get('be_radius_cm'))} cm | - |",
        f"| exact 511-keV A_eff | {fmt(aeff.get('aeff_511_cm2'))} cm2 | - |",
        f"| A_eff target residual vs 16 cm2 | {fmt(target_residual)} | {target_residual is not None and target_residual <= DESIGN_AEFF_TOLERANCE_FRACTION} |",
        f"| natural passband FWHM | {fmt(passband.get('lo_keV'))}-{fmt(passband.get('hi_keV'))} keV | - |",
        f"| sampled line-band A_eff sum | {fmt(aeff.get('sampled_line_band_aeff_sum_cm2'))} cm2 | - |",
        f"| emergent - analytic | {fmt(run.get('emergent_minus_analytic_focal_diffraction'))} | {run.get('pass_crosscheck_0p04_gate')} |",
        f"| strict 0.01 residual diagnostic | {fmt(run.get('abs_emergent_minus_analytic_focal_diffraction'))} | {run.get('pass_strict_0p01_gate')} |",
        "",
        "## Notes",
        "",
        f"- The optical design is 511-centered: `{ENERGIES_KEV}` keV rings are used for the line core/wings; 480-550 keV remains the detector analysis window.",
        f"- The external XOP/CRYSTAL map is required for the 511-keV ring ids `{coverage.get('required_ring_ids')}` and covers `{coverage.get('covered_ring_ids')}`.",
        f"- The B-FULL run used rocking backend `{run.get('rocking_curve_backend')}` with map `{run.get('rocking_curve_map_csv')}`.",
        f"- Package-level validation summary anchor: `{LAUE511_CROSSCHECK_SUMMARY}`.",
        f"- Ring ids for A_eff are reconstructed by joining `focal_crossings.csv` to `optics_history.csv` on `event_id`; unmatched diffracted rows = `{aeff.get('ring_id_reconstruction', {}).get('unmatched_diffracted_focal_rows')}`.",
        "- `phase_space.csv` is not used for science handoff or A_eff.",
        "",
        "## Per-Energy A_eff",
        "",
        "| ring | E keV | area cm2 | primaries | within-Be rows | efficiency | A_eff cm2 |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in aeff.get("energy_rows", []):
        lines.append(
            f"| {row['ring_id']} | {fmt(row['energy_keV'])} | {fmt(row['geometric_area_cm2'])} | "
            f"{fmt(row['primaries'])} | {fmt(row['within_be_focal_crossings'])} | "
            f"{fmt(row['emergent_within_be_efficiency'])} | {fmt(row['aeff_cm2'])} |"
        )
    (STEP_DIR / "real_design_crosscheck_20260601.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    rows = design_rows()
    write_ring_config(rows)
    write_rocking_curve_map(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    aeff = build_aeff(rows)
    write_json(STEP_DIR / "optics_aeff_authority.json", aeff)
    write_json(OUT_DIR / "optics_aeff_authority.json", aeff)
    write_json(
        OUT_DIR / "design_input_summary.json",
        {
            "design_name": DESIGN_NAME,
            "ring_config": str(OPTICSIM_CONFIG),
            "focal_length_mm": FOCAL_LENGTH_MM,
            "tile_size_mm": TILE_SIZE_MM,
            "packing_pitch_factor": PACKING_PITCH_FACTOR,
            "mosaic_fwhm_arcsec": MOSAIC_FWHM_ARCSEC,
            "rows": rows,
        },
    )
    write_rationale(rows, aeff)
    write_crosscheck_report(aeff)
    print(
        json.dumps(
            {
                "status": aeff["status"],
                "ring_config": str(OPTICSIM_CONFIG),
                "aeff_511_cm2": aeff["aeff_511_cm2"],
                "sampled_line_band_aeff_sum_cm2": aeff["sampled_line_band_aeff_sum_cm2"],
                "total_tiles": aeff["total_tiles"],
                "out": rel(OUT_DIR),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
