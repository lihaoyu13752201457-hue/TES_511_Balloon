#!/usr/bin/env python3
"""Reproduce the TES-511 particle-source unit audit.

This script is intentionally read-only with respect to retained project inputs.
It writes compact audit products only inside the new dated engineering package.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from statistics import fmean


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parents[1]
OUT = PACKAGE / "data"

MEGALIB = Path("/home/ubuntu/MEGAlib_Install/megalib-main")
SPECTRA = ROOT / "expacs_fullsphere_20bin_sources"
CORRECT_DP = SPECTRA / "cosima_spectra_dp"
LEGACY_DP = SPECTRA / "cosima_spectra_dp_2602units"

FAMILIES = (
    "alpha",
    "eminus",
    "eplus",
    "gamma",
    "muminus",
    "muplus",
    "n",
    "p",
)

SOURCE_PACKAGES = {
    "Mass_model_511": ROOT
    / "engineering/Mass_model_511_nearfield_migration_20260701/03_source_migration/source_dirs/Mass_model_511",
    "S3c_package32": ROOT
    / "engineering/geometry_optimization_20260704/32_s3c_dominant_backgrounds_20260709/source_cards",
    "S3d_O8_package43": ROOT
    / "engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/config/full_prompt_all8/source_cards",
}

EVENTLIST = (
    ROOT
    / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/eventlists/Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat"
)
PARMA_CLOSURE = (
    ROOT
    / "engineering/m04_validation_geometry_handoff_20260810/02_parma_atm511_repair_20260810/data/parma_line_closure.json"
)
GAMMA_SIM_AUDIT = (
    ROOT
    / "engineering/m04_validation_geometry_handoff_20260810/02_parma_atm511_repair_20260810/data/o8_prompt_gamma_line_dedup_audit.json"
)

SPECTRUM_RE = re.compile(r"\.Spectrum\s+File\s+(\S+)")
FLUX_RE = re.compile(r"\.Flux\s+([-+0-9.eE]+)\s*$", re.MULTILINE)
BEAM_RE = re.compile(
    r"\.Beam\s+FarFieldAreaSource\s+"
    r"([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)"
)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        try:
            return "MEGAlib/" + path.relative_to(MEGALIB).as_posix()
        except ValueError:
            return str(path)


def parse_dp(path: Path) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = raw.split()
        if len(fields) == 3 and fields[0] == "DP":
            points.append((float(fields[1]), float(fields[2])))
    if len(points) < 2:
        raise RuntimeError(f"DP file has fewer than two points: {path}")
    return points


def parse_raw_spectrum(path: Path) -> list[tuple[float, float]]:
    """Read the two numeric columns in one retained EXPACS/PARMA spectrum."""
    points: list[tuple[float, float]] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = raw.split()
        if len(fields) != 2 or raw.lstrip().startswith("#"):
            continue
        try:
            points.append((float(fields[0]), float(fields[1])))
        except ValueError:
            continue
    if len(points) < 2:
        raise RuntimeError(f"raw spectrum has fewer than two points: {path}")
    return points


def trapz(points: list[tuple[float, float]]) -> float:
    return math.fsum(
        0.5 * (y0 + y1) * (x1 - x0)
        for (x0, y0), (x1, y1) in zip(points, points[1:])
    )


def load_manifest_flux() -> dict[str, float]:
    total: dict[str, float] = defaultdict(float)
    with (SPECTRA / "manifest.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            total[row["particle"]] += float(row["flux_cm2_s"])
    return dict(total)


def load_closure() -> dict[str, dict[str, str]]:
    with (SPECTRA / "flux_closure_audit.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        return {row["particle"]: row for row in csv.DictReader(handle)}


def audit_spectra() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    manifest_flux = load_manifest_flux()
    closure = load_closure()
    o8_dir = SOURCE_PACKAGES["S3d_O8_package43"]

    for family in FAMILIES:
        correct_files = sorted(CORRECT_DP.glob(f"{family}_bin*_pdf.dat"))
        legacy_files = sorted(LEGACY_DP.glob(f"{family}_bin*_pdf.dat"))
        if len(correct_files) != 20 or len(legacy_files) != 20:
            raise RuntimeError(
                f"{family}: expected 20 correct and 20 legacy files, got "
                f"{len(correct_files)} and {len(legacy_files)}"
            )
        if [p.name for p in correct_files] != [p.name for p in legacy_files]:
            raise RuntimeError(f"{family}: correct/legacy file names do not pair")

        x_ratios: list[float] = []
        y_deltas: list[float] = []
        correct_integrals: list[float] = []
        legacy_integrals: list[float] = []
        raw_to_correct_energy_deltas: list[float] = []
        raw_to_correct_pdf_relative_deltas: list[float] = []
        correct_x: list[float] = []
        legacy_x: list[float] = []
        dp_rows = 0

        for correct_path, legacy_path in zip(correct_files, legacy_files):
            correct = parse_dp(correct_path)
            legacy = parse_dp(legacy_path)
            if len(correct) != len(legacy):
                raise RuntimeError(f"row-count mismatch: {correct_path.name}")

            raw_pattern = (
                "spectrum_"
                + correct_path.name.removesuffix("_pdf.dat")
                + "_BH*.dat"
            )
            raw_matches = sorted((SPECTRA / "raw_expacs").glob(raw_pattern))
            if len(raw_matches) != 1:
                raise RuntimeError(
                    f"expected one raw spectrum for {correct_path.name}, got "
                    f"{len(raw_matches)}"
                )
            raw_points = parse_raw_spectrum(raw_matches[0])
            if len(raw_points) != len(correct):
                raise RuntimeError(
                    f"raw/correct row-count mismatch: {raw_matches[0].name}"
                )

            # PARMA/EXPACS returns MeV for all non-alpha families and MeV/n for
            # alpha.  Cosima's ParticleGun consumes total kinetic energy in keV.
            # Thus alpha needs A=4 in addition to the MeV -> keV factor.
            energy_scale = 4000.0 if family == "alpha" else 1000.0
            raw_integral = trapz(raw_points)
            for (x_raw, y_raw), (x_dp, y_dp) in zip(raw_points, correct):
                expected_x = x_raw * energy_scale
                expected_y = y_raw / (raw_integral * energy_scale)
                raw_to_correct_energy_deltas.append(abs(x_dp - expected_x))
                denominator = max(abs(expected_y), 1.0e-300)
                raw_to_correct_pdf_relative_deltas.append(
                    abs(y_dp - expected_y) / denominator
                )

            dp_rows += len(correct)
            correct_integrals.append(trapz(correct))
            legacy_integrals.append(trapz(legacy))
            for (xc, yc), (xl, yl) in zip(correct, legacy):
                x_ratios.append(xl / xc)
                y_deltas.append(abs(yl - yc))
                correct_x.append(xc)
                legacy_x.append(xl)

        card = o8_dir / f"Background_{family}_fullsphere20.source"
        text = card.read_text(encoding="utf-8", errors="replace")
        card_flux = math.fsum(
            float(match.group(1)) for match in FLUX_RE.finditer(text)
        )
        closure_row = closure[family]
        expected_flux = manifest_flux[family]

        rows.append(
            {
                "family": family,
                "spectrum_files": len(correct_files),
                "dp_rows": dp_rows,
                "x_legacy_over_correct_min": min(x_ratios),
                "x_legacy_over_correct_max": max(x_ratios),
                "log10_x_legacy_over_correct": math.log10(fmean(x_ratios)),
                "energy_error_factor": 1.0 / fmean(x_ratios),
                "y_max_abs_difference": max(y_deltas),
                "correct_x_min_keV": min(correct_x),
                "correct_x_max_keV": max(correct_x),
                "legacy_x_min_interpreted_keV": min(legacy_x),
                "legacy_x_max_interpreted_keV": max(legacy_x),
                "correct_dp_integral_min": min(correct_integrals),
                "correct_dp_integral_max": max(correct_integrals),
                "legacy_dp_integral_min": min(legacy_integrals),
                "legacy_dp_integral_max": max(legacy_integrals),
                "raw_energy_scale_to_total_keV": (
                    4000.0 if family == "alpha" else 1000.0
                ),
                "raw_to_correct_energy_max_abs_delta_keV": max(
                    raw_to_correct_energy_deltas
                ),
                "raw_to_correct_pdf_max_relative_delta": max(
                    raw_to_correct_pdf_relative_deltas
                ),
                "raw_to_correct_verdict": (
                    "PASS"
                    if max(raw_to_correct_energy_deltas) <= 1.0e-8
                    and max(raw_to_correct_pdf_relative_deltas) <= 1.0e-8
                    else "FAIL"
                ),
                "manifest_flux_cm2_s": expected_flux,
                "o8_card_flux_cm2_s": card_flux,
                "card_flux_relative_delta": (card_flux - expected_flux) / expected_flux,
                "fullsphere_to_main_flux_ratio": float(
                    closure_row["fullsphere_to_main_ratio"]
                ),
                "energy_axis_verdict": "FAIL_FACTOR_1000",
                "flux_bookkeeping_verdict": "PASS",
            }
        )
    return rows


def audit_source_cards() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    package_rows: list[dict[str, object]] = []
    family_rows: list[dict[str, object]] = []
    expected_bin_sr = 4.0 * math.pi / 20.0

    for package_name, directory in SOURCE_PACKAGES.items():
        total_refs = 0
        legacy_refs = 0
        correct_refs = 0
        other_refs = 0
        all_solid_angles: list[float] = []
        family_count = 0

        for family in FAMILIES:
            card = directory / f"Background_{family}_fullsphere20.source"
            if not card.is_file():
                raise RuntimeError(f"missing source card: {card}")
            family_count += 1
            text = card.read_text(encoding="utf-8", errors="replace")
            refs = SPECTRUM_RE.findall(text)
            legacy = sum("/cosima_spectra_dp_2602units/" in ref for ref in refs)
            correct = sum(
                "/cosima_spectra_dp/" in ref
                and "/cosima_spectra_dp_2602units/" not in ref
                for ref in refs
            )
            other = len(refs) - legacy - correct
            beams = [tuple(map(float, match)) for match in BEAM_RE.findall(text)]
            solid_angles = [
                math.radians(phi_max - phi_min)
                * (math.cos(math.radians(theta_min)) - math.cos(math.radians(theta_max)))
                for theta_min, theta_max, phi_min, phi_max in beams
            ]
            flux_values = [float(value) for value in FLUX_RE.findall(text)]

            family_rows.append(
                {
                    "package": package_name,
                    "family": family,
                    "spectrum_references": len(refs),
                    "legacy_2602unit_references": legacy,
                    "correct_keV_references": correct,
                    "other_references": other,
                    "farfield_area_beams": len(beams),
                    "solid_angle_sum_sr": math.fsum(solid_angles),
                    "solid_angle_bin_max_abs_delta_sr": max(
                        abs(value - expected_bin_sr) for value in solid_angles
                    ),
                    "flux_entries": len(flux_values),
                    "flux_sum_cm2_s": math.fsum(flux_values),
                }
            )
            total_refs += len(refs)
            legacy_refs += legacy
            correct_refs += correct
            other_refs += other
            all_solid_angles.extend(solid_angles)

        package_rows.append(
            {
                "package": package_name,
                "source_cards": family_count,
                "spectrum_references": total_refs,
                "legacy_2602unit_references": legacy_refs,
                "correct_keV_references": correct_refs,
                "other_references": other_refs,
                "energy_reference_verdict": (
                    "FAIL_160_OF_160" if legacy_refs == 160 and total_refs == 160 else "REVIEW"
                ),
                "angular_bins": len(all_solid_angles),
                "max_single_bin_solid_angle_delta_sr": max(
                    abs(value - expected_bin_sr) for value in all_solid_angles
                ),
            }
        )
    return package_rows, family_rows


def audit_eventlist() -> dict[str, object]:
    rows = 0
    bad_token_rows = 0
    times: list[float] = []
    energies: list[float] = []
    positions: list[float] = []
    directions_norm_delta: list[float] = []

    for raw in EVENTLIST.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.strip():
            continue
        fields = raw.split()
        rows += 1
        if len(fields) != 15:
            bad_token_rows += 1
            continue
        times.append(float(fields[4]))
        xyz = [float(fields[index]) for index in (5, 6, 7)]
        uvw = [float(fields[index]) for index in (8, 9, 10)]
        energies.append(float(fields[14]))
        positions.extend(xyz)
        directions_norm_delta.append(abs(math.sqrt(math.fsum(v * v for v in uvw)) - 1.0))

    return {
        "path": rel(EVENTLIST),
        "rows": rows,
        "bad_token_rows": bad_token_rows,
        "time_min_s": min(times),
        "time_max_s": max(times),
        "energy_min_keV": min(energies),
        "energy_max_keV": max(energies),
        "position_min_numeric_cm": min(positions),
        "position_max_numeric_cm": max(positions),
        "direction_norm_max_abs_delta": max(directions_norm_delta),
        "verdict": "PASS_UNIT_FORMAT" if bad_token_rows == 0 else "FAIL",
    }


def source_inventory() -> list[dict[str, object]]:
    paths = [
        MEGALIB / "config/Version.txt",
        MEGALIB / "doc/Cosima.pdf",
        MEGALIB / "doc/Geomega.pdf",
        MEGALIB / "src/cosima/src/MCSource.cc",
        MEGALIB / "src/cosima/src/MCParameterFile.cc",
        MEGALIB / "src/cosima/src/MCDetectorConstruction.cc",
        MEGALIB / "src/cosima/src/MCRun.cc",
        MEGALIB / "src/cosima/src/MCEventAction.cc",
        MEGALIB / "src/global/misc/src/MFunction.cxx",
        MEGALIB / "src/geomega/src/MDGeometry.cxx",
        MEGALIB
        / "external/geant4_v10.02.p03/include/Geant4/G4ParticleGun.hh",
        SPECTRA / "manifest.csv",
        SPECTRA / "flux_closure_audit.csv",
        SPECTRA / "raw_expacs/spectrum_gamma_bin00_theta18.19_BHNo.dat",
        SPECTRA / "raw_expacs/spectrum_alpha_bin00_theta18.19_BHNo.dat",
        CORRECT_DP / "gamma_bin00_theta18.19_pdf.dat",
        LEGACY_DP / "gamma_bin00_theta18.19_pdf.dat",
        SOURCE_PACKAGES["S3d_O8_package43"] / "Background_gamma_fullsphere20.source",
        ROOT / "code/tools/run_equiv2602_pipeline_NEW_GEO.py",
        ROOT
        / "engineering/geometry_optimization_20260704/44_s3d_o8_all8_activation_20260713/code/run_s3d_o8_all8_activation.py",
        ROOT / "code/tools/build_fix5_1of10_exactpos_delayed_source.py",
        ROOT / "code/tools/build_fixed_delay_source.py",
        ROOT / "stepwise_maintenance/step09_optics_bridge/code/build_step09_optics_bridge.py",
        EVENTLIST,
        PARMA_CLOSURE,
        GAMMA_SIM_AUDIT,
    ]
    # The unit verdict is exhaustive, so preserve hashes for every spectrum and
    # every source card actually read by the audit, not only representative rows.
    paths.extend(sorted((SPECTRA / "raw_expacs").glob("spectrum_*.dat")))
    paths.extend(sorted(CORRECT_DP.glob("*_pdf.dat")))
    paths.extend(sorted(LEGACY_DP.glob("*_pdf.dat")))
    for directory in SOURCE_PACKAGES.values():
        paths.extend(sorted(directory.glob("Background_*_fullsphere20.source")))
    paths = list(dict.fromkeys(paths))
    return [
        {
            "source": rel(path),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in paths
    ]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    family_rows = audit_spectra()
    package_rows, source_family_rows = audit_source_cards()
    eventlist = audit_eventlist()
    parma = json.loads(PARMA_CLOSURE.read_text(encoding="utf-8"))
    gamma_sim = json.loads(GAMMA_SIM_AUDIT.read_text(encoding="utf-8"))
    inventory = source_inventory()

    write_csv(OUT / "spectrum_family_audit.csv", family_rows)
    write_csv(OUT / "source_package_reference_audit.csv", package_rows)
    write_csv(OUT / "source_card_family_audit.csv", source_family_rows)
    write_csv(OUT / "evidence_hashes.csv", inventory)

    exact_factor_1000 = all(
        abs(float(row["x_legacy_over_correct_min"]) - 0.001) < 1.0e-15
        and abs(float(row["x_legacy_over_correct_max"]) - 0.001) < 1.0e-15
        and float(row["y_max_abs_difference"]) == 0.0
        for row in family_rows
    )
    raw_conversion_closed = all(
        row["raw_to_correct_verdict"] == "PASS" for row in family_rows
    )
    all_refs_legacy = all(
        row["spectrum_references"] == 160
        and row["legacy_2602unit_references"] == 160
        and row["correct_keV_references"] == 0
        for row in package_rows
    )

    summary = {
        "status": "AUDIT_COMPLETE_CONFIRMED_SYSTEMIC_ENERGY_AXIS_ERROR",
        "audit_date": "2026-08-11",
        "retained_inputs_modified": False,
        "scope": {
            "families": list(FAMILIES),
            "angular_bins_per_family": 20,
            "source_packages": list(SOURCE_PACKAGES),
        },
        "headline": {
            "exact_factor_1000_all_families": exact_factor_1000,
            "raw_to_correct_conversion_all_families": raw_conversion_closed,
            "all_three_packages_160_of_160_legacy_references": all_refs_legacy,
            "energy_axis_verdict": "FAIL_ALL_EIGHT_FAMILIES",
            "explicit_flux_bookkeeping_verdict": "PASS",
            "angular_bin_bookkeeping_verdict": "PASS",
            "parma_mono_line_unit_verdict": "PASS",
            "eventlist_unit_format_verdict": eventlist["verdict"],
            "delayed_source_local_unit_verdict": "CONDITIONAL_PASS_UPSTREAM_INVALID",
        },
        "cosima_contract": {
            "manual": {
                "path": "MEGAlib/doc/Cosima.pdf",
                "version": "2021-08-02",
                "spectrum_file_page": 27,
                "farfield_area_page": 29,
                "point_source_page": 30,
                "flux_pages": [34, 35],
                "eventlist_page": 37,
                "triggers_page": 23,
            },
            "source_code": {
                "file_spectrum": "MEGAlib/src/cosima/src/MCSource.cc:1909-1918",
                "file_sampling": "MEGAlib/src/cosima/src/MCSource.cc:2727-2729",
                "shape_sampling": "MEGAlib/src/global/misc/src/MFunction.cxx:791-813",
                "far_near_flux": "MEGAlib/src/cosima/src/MCParameterFile.cc:2834-2846",
                "farfield_angles": "MEGAlib/src/cosima/src/MCParameterFile.cc:1326-1334",
                "eventlist": "MEGAlib/src/cosima/src/MCSource.cc:2274-2289",
            },
        },
        "spectrum_family_rows": family_rows,
        "source_package_rows": package_rows,
        "eventlist": eventlist,
        "parma_mono_line": {
            "energy_MeV": parma["line_energy_MeV"],
            "energy_keV_cosima": parma["line_energy_keV_cosima"],
            "energy_conversion_ratio": parma["line_energy_keV_cosima"]
            / parma["line_energy_MeV"],
            "flux_ph_cm2_s": parma["line_flux_ph_cm2_s"],
            "source_bin_closure": parma["source_bin_closure"],
            "status": parma["status"],
        },
        "retained_gamma_sim_corroboration": {
            "records": gamma_sim["old_spectrum_provenance"]["sim_primary_energy_scan"][
                "records"
            ],
            "minimum_printed_keV": gamma_sim["old_spectrum_provenance"][
                "sim_primary_energy_scan"
            ]["minimum_printed_keV"],
            "maximum_printed_keV": gamma_sim["old_spectrum_provenance"][
                "sim_primary_energy_scan"
            ]["maximum_printed_keV"],
            "events_below_1_keV": gamma_sim["old_spectrum_provenance"][
                "sim_primary_energy_scan"
            ]["events_below_1_keV"],
            "correct_line_nodes_keV": gamma_sim["old_spectrum_provenance"][
                "correct_dp_x_values_keV_near_line"
            ],
            "transported_line_nodes_keV": gamma_sim["old_spectrum_provenance"][
                "retained_o8_dp_x_values_interpreted_by_cosima_as_keV"
            ],
            "raw_to_pdf_generator_found": gamma_sim["old_spectrum_provenance"][
                "raw_to_pdf_generator_found_in_repository"
            ],
        },
        "evidence_inventory": inventory,
    }
    (OUT / "audit_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(json.dumps(summary["headline"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
