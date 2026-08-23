#!/usr/bin/env python3
"""Build the source-only PARMA atmospheric-annihilation-511 package.

This program compiles and calls a narrow C++ wrapper around the archived,
unmodified official PARMA routines.  It does not call Cosima, create a SIM,
generate a continuum spectrum, or alter any retained source/transport product.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any


PACKAGE = Path(__file__).resolve().parents[1]
CODE_DIR = PACKAGE / "code"
CONFIG_DIR = PACKAGE / "config"
DATA_DIR = PACKAGE / "data"
LINE_DIR = PACKAGE / "line"
VENDOR_DIR = PACKAGE / "vendor" / "parma_cpp_official_20260810"
DRIVER_SOURCE = CODE_DIR / "parma511_driver.cpp"
DRIVER_BINARY = CODE_DIR / "parma511_driver"
SUBROUTINES = VENDOR_DIR / "subroutines.cpp"

AUTHORITY = {
    "date": "2025-08-31",
    "latitude_deg": 34.0,
    "longitude_deg": 100.0,
    "altitude_km": 38.75,
    "solar_modulation_MV": 114.6,
    "cutoff_rigidity_GV": 11.6,
    "atmospheric_depth_g_cm2": 3.4614689720143224,
    "local_geometry_g": 0.15,
    "line_energy_MeV": 0.51099895,
    "line_energy_keV": 510.99895,
}


@dataclass(frozen=True)
class BinRow:
    driver_bin_id: int
    mu_low: float
    mu_high: float
    fraction: float
    line_flux: float


@dataclass(frozen=True)
class DriverResult:
    records: dict[str, dict[str, str]]
    bins: tuple[BinRow, ...]
    raw_stdout: str


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def compile_driver() -> tuple[list[str], str]:
    command = [
        "g++",
        "-std=c++17",
        "-O2",
        "-Wall",
        "-Wextra",
        "-pedantic",
        str(DRIVER_SOURCE),
        str(SUBROUTINES),
        "-o",
        str(DRIVER_BINARY),
    ]
    subprocess.run(command, cwd=VENDOR_DIR, check=True)
    compiler = subprocess.run(
        ["g++", "--version"],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.splitlines()[0]
    return command, compiler


def parse_driver_stdout(text: str) -> DriverResult:
    records: dict[str, dict[str, str]] = {}
    bins: list[BinRow] = []
    for row in csv.reader(StringIO(text)):
        if not row:
            continue
        if row[:4] == ["record", "key", "value", "unit"]:
            continue
        if row[:6] == [
            "bin",
            "bin_id",
            "mu_low",
            "mu_high",
            "fraction",
            "line_flux_cm-2_s-1",
        ]:
            continue
        if row[0] == "bin":
            bins.append(
                BinRow(
                    driver_bin_id=int(row[1]),
                    mu_low=float(row[2]),
                    mu_high=float(row[3]),
                    fraction=float(row[4]),
                    line_flux=float(row[5]),
                )
            )
            continue
        if len(row) != 4:
            raise RuntimeError(f"unexpected driver row: {row!r}")
        category, key, value, unit = row
        records.setdefault(category, {})[key] = value
        records.setdefault(f"{category}_units", {})[key] = unit
    if not bins:
        raise RuntimeError("driver returned no angular bins")
    return DriverResult(records=records, bins=tuple(bins), raw_stdout=text)


def run_driver(bins: int, local_geometry_g: float | None = None) -> DriverResult:
    if local_geometry_g is None:
        local_geometry_g = float(AUTHORITY["local_geometry_g"])
    command = [
        str(DRIVER_BINARY),
        "--g",
        str(local_geometry_g),
        "--s",
        str(AUTHORITY["solar_modulation_MV"]),
        "--rc",
        str(AUTHORITY["cutoff_rigidity_GV"]),
        "--depth",
        repr(AUTHORITY["atmospheric_depth_g_cm2"]),
        "--bins",
        str(bins),
        "--quadrature-order",
        "64",
    ]
    completed = subprocess.run(
        command,
        cwd=VENDOR_DIR,
        check=True,
        text=True,
        capture_output=True,
    )
    if completed.stderr:
        raise RuntimeError(f"unexpected driver stderr: {completed.stderr}")
    return parse_driver_stdout(completed.stdout)


def source_order(result: DriverResult) -> list[BinRow]:
    # PARMA mu=+1 is downward and maps to Cosima polar theta=0 deg.  The C++
    # driver emits increasing mu, so reverse it for ascending Cosima theta.
    return list(reversed(result.bins))


def direction_label(row: BinRow) -> str:
    return "down" if 0.5 * (row.mu_low + row.mu_high) > 0.0 else "up"


def theta_bounds(row: BinRow) -> tuple[float, float]:
    return (
        math.degrees(math.acos(max(-1.0, min(1.0, row.mu_high)))),
        math.degrees(math.acos(max(-1.0, min(1.0, row.mu_low)))),
    )


def write_bin_csv(bins: int, result: DriverResult) -> Path:
    path = LINE_DIR / f"parma511_day15_{bins}bins.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(
            [
                "source_id",
                "theta_bin_id",
                "direction_label",
                "parma_mu_low",
                "parma_mu_high",
                "cosima_theta_low_deg",
                "cosima_theta_high_deg",
                "line_fraction",
                "line_flux_ph_cm-2_s-1",
            ]
        )
        for theta_bin_id, row in enumerate(source_order(result)):
            label = direction_label(row)
            theta_low, theta_high = theta_bounds(row)
            writer.writerow(
                [
                    f"PARMA511_bin{theta_bin_id:02d}_{label}",
                    theta_bin_id,
                    label,
                    f"{row.mu_low:.17g}",
                    f"{row.mu_high:.17g}",
                    f"{theta_low:.12f}",
                    f"{theta_high:.12f}",
                    f"{row.fraction:.17g}",
                    f"{row.line_flux:.17g}",
                ]
            )
    return path


def write_source_fragment(bins: int, result: DriverResult) -> Path:
    path = LINE_DIR / f"PARMA_atm511_day15_fullsphere_{bins}bins.inc.source"
    ordered = source_order(result)
    line_flux = float(result.records["line"]["integrated_flux"])
    lines = [
        "# Source-only PARMA atmospheric annihilation-511 module.",
        "# This fragment intentionally has no Geometry, Run, Events, or FileName directive.",
        "# It cannot launch transport by itself and does not contain a continuum component.",
        (
            "# Authority: 2025-08-31, lat=34 deg, lon=100 deg, alt=38.75 km, "
            "W=114.6 MV, Rc=11.6 GV, X=3.4614689720143224 g/cm2, g=0.15."
        ),
        f"# PARMA get511fluxCpp total: {line_flux:.17g} ph cm^-2 s^-1.",
        "# PARMA angular mu=+1 downward maps to Cosima theta=0 deg.",
        "# Spectrum Mono uses keV in Cosima: 510.99895 keV.",
        "",
    ]
    for theta_bin_id, row in enumerate(ordered):
        label = direction_label(row)
        lines.append(
            f"PARMA511Day15.Source PARMA511_bin{theta_bin_id:02d}_{label}"
        )
    lines.append("")
    for theta_bin_id, row in enumerate(ordered):
        label = direction_label(row)
        source_id = f"PARMA511_bin{theta_bin_id:02d}_{label}"
        theta_low, theta_high = theta_bounds(row)
        lines.extend(
            [
                f"{source_id}.ParticleType 1",
                (
                    f"{source_id}.Beam FarFieldAreaSource "
                    f"{theta_low:.12f} {theta_high:.12f} 0.000000000000 360.000000000000"
                ),
                f"{source_id}.Spectrum Mono 510.99895",
                f"{source_id}.Flux {row.line_flux:.17g}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--assert-only",
        action="store_true",
        help="regenerate and validate outputs just like the default mode",
    )
    parser.parse_args()

    for directory in (CONFIG_DIR, DATA_DIR, LINE_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    compile_command, compiler = compile_driver()
    results = {bins: run_driver(bins) for bins in (20, 40, 80)}
    result80 = results[80]
    g_sensitivity_results = {
        g: run_driver(80, local_geometry_g=g) for g in (0.0, 0.15, 10.0)
    }

    line_fluxes = {
        float(result.records["line"]["integrated_flux"])
        for result in results.values()
    }
    if len(line_fluxes) != 1:
        raise RuntimeError(f"line flux changed with angular bin count: {line_fluxes}")
    line_flux = line_fluxes.pop()
    if abs(line_flux - 0.16651547160226118) > 5e-15:
        raise RuntimeError(f"unexpected line-flux checksum: {line_flux:.17g}")

    derived = {
        key: float(value)
        for key, value in result80.records["derived"].items()
    }
    mu_negative = float(result80.records["angular"]["mu_negative_fraction"])
    mu_positive = float(result80.records["angular"]["mu_positive_fraction"])
    ratio = float(result80.records["angular"]["positive_to_negative_ratio"])
    if abs(mu_negative + mu_positive - 1.0) >= 1e-14:
        raise RuntimeError("hemisphere fractions do not sum to unity")
    if abs(mu_negative - 0.8232197530929204) >= 5e-13:
        raise RuntimeError(f"unexpected angular checksum: {mu_negative:.17g}")

    authority_payload = {
        "authority_status": "FROZEN_EXPLICIT_DAY15_TUPLE_FOR_MODULAR_511_REPAIR",
        "authority": AUTHORITY,
        "field_provenance": {
            "date_latitude_longitude_altitude": (
                "stepwise_maintenance/step06_mission_time_variation/"
                "outputs_geo_opt_s1_bpe_w5_fullstat_v1/trajectory_profile.csv; day_mid=15"
            ),
            "solar_modulation_MV": "official PARMA getHPcpp(2025,8,31)",
            "cutoff_rigidity_GV": "official PARMA getrcpp(34,100)",
            "atmospheric_depth_g_cm2": (
                "retained mission trajectory day-15 depth; passed explicitly to PARMA"
            ),
            "local_geometry_g": (
                "official main-generator.cpp default water fraction; g=0,0.15,10 "
                "were numerically identical for this photon-line angular distribution"
            ),
        },
        "official_derived_cross_check": derived,
        "resolved_conflict": {
            "official_getdcpp_depth_g_cm2": derived["atmospheric_depth"],
            "selected_mission_depth_g_cm2": AUTHORITY[
                "atmospheric_depth_g_cm2"
            ],
            "absolute_difference_g_cm2": abs(
                derived["atmospheric_depth"]
                - AUTHORITY["atmospheric_depth_g_cm2"]
            ),
            "policy": (
                "Keep the retained flight-trajectory depth so this replacement remains "
                "a single modular atmospheric-511 correction. Do not import the legacy "
                "38-km W=118.3 table row or the 38-km X=3.8651 scenario."
            ),
        },
        "scope": {
            "continuum_changed": False,
            "other_particles_changed": False,
            "transport_launched": False,
            "only_physical_component_changed": "atmospheric annihilation 511-keV line",
        },
    }
    authority_path = CONFIG_DIR / "day15_environment_authority.json"
    write_json(authority_path, authority_payload)

    generated_paths: list[Path] = [authority_path]
    convergence_rows: list[dict[str, Any]] = []
    for bins, result in results.items():
        fraction_sum = sum(row.fraction for row in result.bins)
        flux_sum = sum(row.line_flux for row in result.bins)
        convergence_rows.append(
            {
                "equal_mu_bins": bins,
                "fraction_sum": fraction_sum,
                "fraction_closure_abs": abs(fraction_sum - 1.0),
                "flux_sum_ph_cm-2_s-1": flux_sum,
                "flux_closure_abs_ph_cm-2_s-1": abs(flux_sum - line_flux),
                "mu_negative_fraction": float(
                    result.records["angular"]["mu_negative_fraction"]
                ),
                "mu_positive_fraction": float(
                    result.records["angular"]["mu_positive_fraction"]
                ),
                "positive_to_negative_ratio": float(
                    result.records["angular"]["positive_to_negative_ratio"]
                ),
                "full_sphere_angular_integral": float(
                    result.records["angular"]["full_sphere_integral"]
                ),
            }
        )
        generated_paths.append(write_bin_csv(bins, result))
        generated_paths.append(write_source_fragment(bins, result))
        raw_path = DATA_DIR / f"parma511_driver_stdout_{bins}bins.csv"
        raw_path.write_text(result.raw_stdout, encoding="utf-8")
        generated_paths.append(raw_path)

    convergence_path = DATA_DIR / "angular_convergence.csv"
    with convergence_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(convergence_rows[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(convergence_rows)
    generated_paths.append(convergence_path)

    g_sensitivity_path = DATA_DIR / "g_parameter_sensitivity.csv"
    g_sensitivity_rows = []
    for g, result in g_sensitivity_results.items():
        g_sensitivity_rows.append(
            {
                "local_geometry_g": g,
                "line_flux_ph_cm-2_s-1": float(
                    result.records["line"]["integrated_flux"]
                ),
                "mu_negative_fraction": float(
                    result.records["angular"]["mu_negative_fraction"]
                ),
                "mu_positive_fraction": float(
                    result.records["angular"]["mu_positive_fraction"]
                ),
                "positive_to_negative_ratio": float(
                    result.records["angular"]["positive_to_negative_ratio"]
                ),
            }
        )
    with g_sensitivity_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(g_sensitivity_rows[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(g_sensitivity_rows)
    generated_paths.append(g_sensitivity_path)
    if len(
        {
            (
                row["line_flux_ph_cm-2_s-1"],
                row["mu_negative_fraction"],
                row["mu_positive_fraction"],
                row["positive_to_negative_ratio"],
            )
            for row in g_sensitivity_rows
        }
    ) != 1:
        raise RuntimeError(
            "g=0, 0.15, and 10 do not give identical line flux/angular checksums"
        )

    source_hashes = {
        str(path.relative_to(PACKAGE)): sha256(path)
        for path in (
            DRIVER_SOURCE,
            VENDOR_DIR / "Readme.txt",
            VENDOR_DIR / "main.cpp",
            VENDOR_DIR / "main-generator.cpp",
            SUBROUTINES,
            VENDOR_DIR / "input" / "elemag" / "flux511keV.inp",
            PACKAGE / "vendor" / "parma_cpp_official_20260810.zip",
        )
    }
    closure = {
        "status": "PASS_PARMA_511_SOURCE_LEVEL_ONLY",
        "line_energy_MeV": AUTHORITY["line_energy_MeV"],
        "line_energy_keV_cosima": AUTHORITY["line_energy_keV"],
        "line_flux_ph_cm2_s": line_flux,
        "angular_checksum": {
            "mu_definition": (
                "PARMA cx: -1 upward, +1 downward; Cosima polar theta=acos(mu)"
            ),
            "mu_negative_fraction": mu_negative,
            "mu_positive_fraction": mu_positive,
            "positive_to_negative_ratio": ratio,
            "fraction_sum": mu_negative + mu_positive,
        },
        "source_bin_closure": convergence_rows,
        "local_geometry_g_sensitivity": {
            "tested_values": [0.0, 0.15, 10.0],
            "all_line_and_angular_checksums_identical": True,
            "data": str(g_sensitivity_path.relative_to(PACKAGE)),
        },
        "component_accounting": {
            "continuum_line_terms_modified": 0,
            "discrete_line_families_generated": 1,
            "continuum_transport_rerun": False,
            "other_particle_transport_rerun": False,
            "cosima_or_transport_launched": False,
        },
        "user_scope_override": {
            "m_sampling": "offline only; zero simulation",
            "parma": "replace only atmospheric annihilation-511 mono module",
            "all_other_modules": "reuse retained products and recompose",
            "handoff_transport_matrix_applicable": False,
        },
        "gates": {
            "source_flux_and_angle": "PASS",
            "single_count_accounting": "PENDING_OFFLINE_CONTINUUM_LINE_SUBTRACTION",
            "existing_line_only_response_reuse": "PENDING_READ_ONLY_LINEAGE_AUDIT",
            "detector_response": "NOT_CLAIMED_BY_SOURCE_LEVEL_PACKAGE",
        },
        "vendor_hashes": source_hashes,
    }
    closure_path = DATA_DIR / "parma_line_closure.json"
    write_json(closure_path, closure)
    generated_paths.append(closure_path)

    manifest = {
        "status": "PASS_REPRODUCIBLE_SOURCE_ONLY_BUILD_NO_SIMULATION",
        "compiler": compiler,
        "compile_command": compile_command,
        "working_directory_for_driver": str(VENDOR_DIR),
        "driver_binary_sha256": sha256(DRIVER_BINARY),
        "source_hashes": source_hashes,
        "output_hashes": {
            str(path.relative_to(PACKAGE)): sha256(path)
            for path in sorted(generated_paths)
        },
        "forbidden_calls_observed": [],
        "cosima_invoked": False,
        "sim_created": False,
    }
    write_json(DATA_DIR / "build_manifest.json", manifest)

    print(json.dumps({
        "status": manifest["status"],
        "line_flux_ph_cm2_s": line_flux,
        "mu_negative_fraction": mu_negative,
        "mu_positive_fraction": mu_positive,
        "generated_files": len(generated_paths) + 1,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
