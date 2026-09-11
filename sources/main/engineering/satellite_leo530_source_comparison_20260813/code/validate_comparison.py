#!/usr/bin/env python3
"""Fail-closed validation for the LEO-versus-balloon source comparison."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[1]
TABLE_ROOT = PACKAGE_ROOT / "outputs" / "tables"
FIGURE_ROOT = PACKAGE_ROOT / "outputs" / "figures"
SPECTRUM_ROOT = PACKAGE_ROOT / "outputs" / "spectra" / "cosi_dc4_physical_restored_unit_pdf"
VALIDATION_PATH = PACKAGE_ROOT / "data" / "validation.json"
REPORT_PATH = PACKAGE_ROOT / "VALIDATION_REPORT.md"

spec = importlib.util.spec_from_file_location("build_comparison", PACKAGE_ROOT / "code" / "build_comparison.py")
build = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = build
spec.loader.exec_module(build)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def as_float(value: str) -> float:
    return float(value)


def main() -> None:
    errors: list[str] = []
    warnings: list[str] = []
    metrics: dict[str, object] = {}

    contract = json.loads((PACKAGE_ROOT / "data" / "comparison_contract.json").read_text(encoding="utf-8"))
    pins = json.loads((PACKAGE_ROOT / "data" / "pinned_input_sha256.json").read_text(encoding="utf-8"))
    summary = json.loads((PACKAGE_ROOT / "outputs" / "summary.json").read_text(encoding="utf-8"))

    if contract["satellite_baseline"]["commit"] != pins["commit"]:
        errors.append("Pinned COSI commit differs between contracts")
    if summary.get("status") != "BUILT__SOURCE_INPUT_COMPARISON__NOT_TRANSPORT_AUTHORITY":
        errors.append("Unexpected summary status")

    pinned_rows = read_csv(TABLE_ROOT / "pinned_source_files.csv")
    if len(pinned_rows) != len(pins["files"]):
        errors.append(f"Pinned source row count mismatch: {len(pinned_rows)} != {len(pins['files'])}")
    for relative_path, expected in pins["files"].items():
        path = PACKAGE_ROOT / "inputs" / "cosi_dc4_pinned" / relative_path
        if not path.is_file():
            errors.append(f"Missing pinned input: {relative_path}")
        elif file_sha256(path) != expected:
            errors.append(f"Pinned input hash mismatch: {relative_path}")
    metrics["pinned_input_files"] = len(pins["files"])

    balloon_manifest = REPO_ROOT / "engineering" / "particle_source_unit_repair_20260811" / "data" / "source_contract_manifest.json"
    balloon_static = REPO_ROOT / "engineering" / "particle_source_unit_repair_20260811" / "data" / "static_validation.json"
    if file_sha256(balloon_manifest) != contract["balloon_baseline"]["source_contract_sha256"]:
        errors.append("Balloon source-contract SHA-256 mismatch")
    static = json.loads(balloon_static.read_text(encoding="utf-8"))
    if static.get("status") != "PASS":
        errors.append("Balloon corrected-keV static validation is not PASS")
    if static.get("spectra", {}).get("files") != 160:
        errors.append("Balloon corrected-keV package does not contain 160 spectra")
    if static.get("source_packages", {}).get("legacy_references") != 0:
        errors.append("Balloon corrected-keV package contains legacy references")

    angular_rows = read_csv(TABLE_ROOT / "balloon_angular_spectra_long.csv")
    angular_groups: dict[tuple[str, int], list[dict[str, str]]] = defaultdict(list)
    for row in angular_rows:
        angular_groups[(row["family"], int(row["bin_index"]))].append(row)
    if len(angular_groups) != 160:
        errors.append(f"Balloon angular group count mismatch: {len(angular_groups)} != 160")
    family_fluxes: dict[str, dict[int, float]] = defaultdict(dict)
    pdf_integrals = []
    for (family, bin_index), rows in angular_groups.items():
        rows.sort(key=lambda row: as_float(row["energy_keV_total"]))
        energy = np.asarray([as_float(row["energy_keV_total"]) for row in rows])
        pdf = np.asarray([as_float(row["pdf_keV_inv"]) for row in rows])
        integral = float(np.trapezoid(pdf, energy))
        pdf_integrals.append(integral)
        if abs(integral - 1.0) > 1e-8:
            errors.append(f"Balloon PDF integral mismatch: {family} bin {bin_index}: {integral}")
        flux_values = {as_float(row["bin_flux_cm2_s"]) for row in rows}
        if len(flux_values) != 1:
            errors.append(f"Balloon flux is not constant within {family} bin {bin_index}")
        family_fluxes[family][bin_index] = next(iter(flux_values))
        expected_domain = "down" if bin_index < 10 else "up"
        if {row["domain"] for row in rows} != {expected_domain}:
            errors.append(f"Balloon domain mismatch: {family} bin {bin_index}")
        omega = {as_float(row["solid_angle_sr"]) for row in rows}
        if len(omega) != 1 or abs(next(iter(omega)) - 4 * math.pi / 20) > 1e-12:
            errors.append(f"Balloon solid angle mismatch: {family} bin {bin_index}")
    metrics["balloon_angular_groups"] = len(angular_groups)
    metrics["balloon_pdf_integral_min"] = min(pdf_integrals)
    metrics["balloon_pdf_integral_max"] = max(pdf_integrals)
    metrics["balloon_solid_angle_sum_sr"] = 20 * 4 * math.pi / 20

    anchors = {
        "gamma": (1.1867514470686, 3.6129101307166, 4.7996615777852),
        "n": (0.124592840265625, 0.337646341964, 0.462239182229625),
        "p": (0.08926878476715999, 0.0230319368641741, 0.11230072163133409),
        "alpha": (0.0112237865746313, 0.00026330987560072, 0.01148709645023202),
        "eminus": (0.07748130318558501, 0.121520741386557, 0.199002044572142),
        "eplus": (0.048218077148594, 0.068762468574168, 0.11698054572276201),
        "muminus": (0.0041332555935915, 0.00083567442878357, 0.00496893002237507),
        "muplus": (0.0046484288086802, 0.00092158295738194, 0.00557001176606214),
    }
    for family, (expected_down, expected_up, expected_full) in anchors.items():
        actual_down = sum(value for index, value in family_fluxes[family].items() if index < 10)
        actual_up = sum(value for index, value in family_fluxes[family].items() if index >= 10)
        for label, actual, expected in (
            ("down", actual_down, expected_down),
            ("up", actual_up, expected_up),
            ("full", actual_down + actual_up, expected_full),
        ):
            if not math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-14):
                errors.append(f"Balloon {family} {label} flux closure mismatch: {actual} != {expected}")

    inventory = read_csv(TABLE_ROOT / "component_inventory.csv")
    if len(inventory) != 13:
        errors.append(f"Satellite component inventory count mismatch: {len(inventory)} != 13")
    continuums = [row for row in inventory if row["kind"] == "continuum"]
    mono = [row for row in inventory if row["kind"] == "mono"]
    if len(continuums) != 10 or len(mono) != 1:
        errors.append(f"Satellite spectrum-kind inventory mismatch: continua={len(continuums)}, mono={len(mono)}")
    mismatch_ids = {row["component_id"] for row in continuums if row["source_link_status"] != "match"}
    if mismatch_ids != {"albedo_neutrons_10gv_proxy"}:
        errors.append(f"Unexpected source-link mismatch set: {sorted(mismatch_ids)}")
    for row in continuums + mono:
        simulation_flux = as_float(row["simulation_flux_cm2_s"])
        physical_flux = as_float(row["physical_flux_cm2_s"])
        if not math.isclose(physical_flux, simulation_flux * 1000.0, rel_tol=1e-13):
            errors.append(f"DC4 1000-shard flux restoration mismatch: {row['component_id']}")
    card_header_ratios = {
        row["component_id"]: as_float(row["physical_card_to_header_ratio"]) for row in continuums
    }
    if not math.isclose(as_float(mono[0]["physical_flux_cm2_s"]), 0.028207, rel_tol=1e-13):
        errors.append("Atmospheric 511 line physical flux mismatch")
    metrics["satellite_continuum_components"] = len(continuums)
    metrics["satellite_mono_components"] = len(mono)
    metrics["satellite_source_link_mismatches"] = sorted(mismatch_ids)
    metrics["satellite_physical_card_to_spectrum_header_ratio"] = card_header_ratios

    restored_files = sorted(SPECTRUM_ROOT.glob("*.spectrum"))
    if len(restored_files) != 10:
        errors.append(f"Physical-restored spectrum count mismatch: {len(restored_files)} != 10")
    restored_integrals = {}
    for path in restored_files:
        parsed = build.parse_spectrum(path)
        integral = parsed.integrate()
        restored_integrals[path.stem] = integral
        if parsed.interpolation != "loglog" or abs(integral - 1.0) > 1e-8:
            errors.append(f"Restored satellite PDF validation failed: {path.name}: {integral}")
    metrics["restored_pdf_integral_min"] = min(restored_integrals.values())
    metrics["restored_pdf_integral_max"] = max(restored_integrals.values())

    contrasts = read_csv(TABLE_ROOT / "environment_contrasts.csv")
    for row in contrasts:
        validity = row["satellite_model_validity_coverage"]
        ratio = row["satellite_to_balloon_ratio"]
        satellite_flux = row["satellite_flux_cm2_s"]
        if validity in {"none", "unavailable"} and (ratio or satellite_flux):
            errors.append(
                f"Invalid/unavailable contrast is zero-filled instead of NA: {row['family']} {row['band']}"
            )
        if row["family"] in {"muminus", "muplus"} and row["satellite_profile"] != "unavailable":
            errors.append(f"Muon satellite absence is not explicit: {row['family']} {row['band']}")
    proxy_rows = [
        row
        for row in contrasts
        if row["family"] == "gamma" and row["band"] == "450_600_keV_annihilation_region_proxy"
    ]
    if len(proxy_rows) != 1 or proxy_rows[0]["comparison_grade"] != "C":
        errors.append("450–600 keV gamma comparison is not uniquely marked as grade C proxy")

    expected_figures = {
        "gamma_source_comparison.png",
        "particle_family_source_comparison.png",
        "common_support_shape_comparison.png",
        "gamma_source_comparison.pdf",
        "particle_family_source_comparison.pdf",
        "common_support_shape_comparison.pdf",
    }
    actual_figures = {path.name for path in FIGURE_ROOT.iterdir() if path.is_file()}
    if actual_figures != expected_figures:
        errors.append(f"Figure inventory mismatch: {sorted(actual_figures)}")
    image_metrics = {}
    for png_path in sorted(FIGURE_ROOT.glob("*.png")):
        with Image.open(png_path) as image:
            array = np.asarray(image.convert("RGB"))
            width, height = image.size
        if width < 1800 or height < 900:
            errors.append(f"Figure resolution too small: {png_path.name}: {width}x{height}")
        if float(array.std()) < 5.0 or np.mean(np.all(array > 250, axis=2)) > 0.98:
            errors.append(f"Figure appears blank: {png_path.name}")
        image_metrics[png_path.name] = {"width": width, "height": height, "rgb_std": float(array.std())}
    metrics["figures"] = image_metrics

    warnings.extend(
        [
            "Pinned COSI DC4 AlbedoNeutrons.source names a missing 12.6-GV file; the available 10-GV spectrum is diagnostic-only.",
            "COSI DC4 normal-background source-card rates are per one of 1000 parallel simulations; physical comparison rates restore ×1000. SAA is excluded and is not scaled here.",
            "Secondary electron/positron inputs retain 10-GV file labels and the secondary-proton card normalization differs from its spectrum-header integral.",
            "No orbit-time weighting, SAA residence, Galactic diffuse sky-map collapse, pointing history, or detector response is included.",
            "Balloon gamma is a broadband-total table with a coarse annihilation bump; the 450–600 keV result is not a line-only ratio.",
        ]
    )

    output_hashes = {}
    for path in sorted((PACKAGE_ROOT / "outputs").rglob("*")):
        if path.is_file():
            output_hashes[str(path.relative_to(PACKAGE_ROOT))] = file_sha256(path)
    validation = {
        "schema_version": 1,
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
        "output_sha256": output_hashes,
        "authority_boundary": "source-input comparison only; not transport, activation, detector-response, sensitivity, or geometry-promotion authority",
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report_lines = [
        "# Validation report",
        "",
        f"Status: `{validation['status']}`",
        "",
        "This validation reopens the pinned inputs and generated tables/spectra/figures. It does not grant detector-physics authority.",
        "",
        "## Checked",
        "",
        f"- {metrics['pinned_input_files']} hash-pinned COSI input/evidence files at commit `{pins['commit']}`.",
        f"- {metrics['balloon_angular_groups']} corrected-keV balloon family/bin spectra; every `IP LIN` PDF closes to one.",
        f"- 20 equal-mu bins close to `4π = {metrics['balloon_solid_angle_sum_sr']:.12g} sr`; down/up/full source-card flux anchors close for all eight families.",
        f"- {metrics['satellite_continuum_components']} LEO continuum components and {metrics['satellite_mono_components']} independent mono-line component.",
        "- All normal COSI component card rates restore the 1000-way parallelization factor; atmospheric 511 closes at `0.028207 cm^-2 s^-1`.",
        f"- {len(restored_files)} physical-restored satellite unit-PDF spectra close under their declared `IP LOGLOG` interpolation.",
        "- Invalid/unavailable bands are emitted as `NA`, never as an imputed zero; missing satellite muons stay explicitly unavailable.",
        "- Three PNG/PDF figure pairs are nonblank and meet the minimum raster dimensions.",
        "",
        "## Warnings retained by design",
        "",
    ]
    report_lines.extend(f"- {warning}" for warning in warnings)
    if errors:
        report_lines.extend(["", "## Errors", ""] + [f"- {error}" for error in errors])
    REPORT_PATH.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": validation["status"], "errors": len(errors), "warnings": len(warnings)}, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
