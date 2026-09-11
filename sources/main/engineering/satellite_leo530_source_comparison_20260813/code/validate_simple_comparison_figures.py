#!/usr/bin/env python3
"""Fail-closed checks for the compact four-figure comparison."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
TABLE_ROOT = PACKAGE_ROOT / "outputs" / "tables"
SIMPLE_ROOT = PACKAGE_ROOT / "outputs" / "simple"
SIMPLE_TABLE_ROOT = SIMPLE_ROOT / "tables"
FIGURE_ROOT = SIMPLE_ROOT / "figures"
VALIDATION_PATH = PACKAGE_ROOT / "data" / "simple_figures_validation.json"
REPORT_PATH = PACKAGE_ROOT / "SIMPLE_FIGURES_VALIDATION.md"

SOURCE_TABLES = (
    "environment_contrasts.csv",
    "balloon_aggregated_spectra.csv",
    "balloon_angular_spectra_long.csv",
    "satellite_profile_spectra.csv",
    "satellite_line_components.csv",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def main() -> None:
    errors: list[str] = []
    warnings: list[str] = []
    metrics: dict[str, object] = {}

    base_validation = json.loads((PACKAGE_ROOT / "data" / "validation.json").read_text(encoding="utf-8"))
    manifest = json.loads((SIMPLE_ROOT / "manifest.json").read_text(encoding="utf-8"))
    if base_validation.get("status") != "PASS":
        errors.append("Base source-input comparison validation is not PASS")
    if manifest.get("status") != "BUILT__FOUR_FIGURE_SOURCE_COMPARISON__NOT_TRANSPORT_AUTHORITY":
        errors.append("Unexpected simple-figure manifest status")
    if manifest.get("figure_count") != 4 or len(manifest.get("figures", [])) != 4:
        errors.append("Simple manifest does not declare exactly four figures")

    for filename in SOURCE_TABLES:
        path = TABLE_ROOT / filename
        relative = str(path.relative_to(PACKAGE_ROOT))
        actual = sha256(path)
        if base_validation.get("output_sha256", {}).get(relative) != actual:
            errors.append(f"Base validated hash mismatch: {relative}")
        if manifest.get("input_table_sha256", {}).get(filename) != actual:
            errors.append(f"Simple manifest input hash mismatch: {filename}")
    metrics["validated_source_tables"] = len(SOURCE_TABLES)

    contrast_rows = read_csv(TABLE_ROOT / "environment_contrasts.csv")
    contrast_lookup = {(row["family"], row["band"]): row for row in contrast_rows}
    if len(contrast_lookup) != len(contrast_rows):
        errors.append("Duplicate base contrast keys")

    gamma_rows = read_csv(SIMPLE_TABLE_ROOT / "simple_gamma_bands.csv")
    expected_gamma_bands = {
        "100_300_keV",
        "300_450_keV",
        "450_600_keV_annihilation_region_proxy",
        "600_1000_keV",
        "1_10_MeV",
    }
    if {row["band_id"] for row in gamma_rows} != expected_gamma_bands or len(gamma_rows) != 5:
        errors.append("Simple gamma table is not the expected five-band set")
    for row in gamma_rows:
        base = contrast_lookup[("gamma", row["band_id"])]
        for simple_field, base_field in (
            ("balloon_flux_cm2_s", "balloon_full_flux_cm2_s"),
            ("leo_flux_cm2_s", "satellite_flux_cm2_s"),
            ("leo_to_balloon_ratio", "satellite_to_balloon_ratio"),
        ):
            simple_value = float(row[simple_field])
            base_value = float(base[base_field])
            if not math.isclose(simple_value, base_value, rel_tol=1e-13, abs_tol=1e-15):
                errors.append(f"Simple gamma value differs from base contrast: {row['band_id']} {simple_field}")
        if not math.isclose(
            float(row["leo_flux_cm2_s"]) / float(row["balloon_flux_cm2_s"]),
            float(row["leo_to_balloon_ratio"]),
            rel_tol=1e-13,
        ):
            errors.append(f"Simple gamma ratio does not close: {row['band_id']}")
    proxy = [row for row in gamma_rows if row["band_id"] == "450_600_keV_annihilation_region_proxy"]
    if len(proxy) != 1 or proxy[0]["comparison_grade"] != "C" or "†" not in proxy[0]["display_label"]:
        errors.append("Gamma annihilation-region proxy is not explicitly grade C and dagger-marked")
    metrics["simple_gamma_bands"] = len(gamma_rows)

    matrix_rows = read_csv(SIMPLE_TABLE_ROOT / "simple_family_band_matrix.csv")
    expected_families = {"n", "p", "alpha", "eminus", "eplus", "muon"}
    expected_matrix_bands = {"1_10_MeV", "10_100_MeV", "100_MeV_1_GeV", "1_100_GeV"}
    matrix_keys = {(row["family"], row["band_id"]) for row in matrix_rows}
    if len(matrix_rows) != len(expected_families) * len(expected_matrix_bands):
        errors.append(f"Unexpected simple matrix row count: {len(matrix_rows)}")
    if matrix_keys != {(family, band) for family in expected_families for band in expected_matrix_bands}:
        errors.append("Simple matrix key set mismatch")
    if any(row["family"] == "gamma" for row in matrix_rows):
        errors.append("Gamma is duplicated in the non-gamma matrix")
    for row in matrix_rows:
        ratio_text = row["leo_to_balloon_ratio"]
        if row["family"] == "muon":
            if ratio_text or row["category"] != "NA" or row["display_label"] != "NA":
                errors.append(f"Unavailable muon cell was numerically filled: {row['band_id']}")
            continue
        base = contrast_lookup[(row["family"], row["band_id"])]
        base_ratio = base["satellite_to_balloon_ratio"]
        if not base_ratio:
            if ratio_text or row["category"] != "NA" or row["display_label"] != "NA":
                errors.append(f"Unavailable/out-of-support cell was numerically filled: {row['family']} {row['band_id']}")
        else:
            if not ratio_text:
                errors.append(f"Available matrix ratio is missing: {row['family']} {row['band_id']}")
            elif not math.isclose(float(ratio_text), float(base_ratio), rel_tol=1e-13, abs_tol=1e-15):
                errors.append(f"Matrix ratio differs from base contrast: {row['family']} {row['band_id']}")
            if base["satellite_model_validity_coverage"] == "partial_or_mixed" and "~" not in row["display_label"]:
                errors.append(f"Partial/mixed matrix ratio lacks marker: {row['family']} {row['band_id']}")
    metrics["simple_matrix_cells"] = len(matrix_rows)
    metrics["simple_matrix_na_cells"] = sum(row["category"] == "NA" for row in matrix_rows)

    readout_rows = read_csv(SIMPLE_TABLE_ROOT / "simple_readout.csv")
    if len(readout_rows) != 8:
        errors.append(f"Readout row count mismatch: {len(readout_rows)} != 8")
    status_counts: dict[str, int] = {}
    for row in readout_rows:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
    expected_status_counts = {
        "Input established": 1,
        "B-level contrast": 1,
        "Not established": 5,
        "Pilot required": 1,
    }
    if status_counts != expected_status_counts:
        errors.append(f"Readout status inventory mismatch: {status_counts}")
    compute_rows = [row for row in readout_rows if "CPU" in row["topic"]]
    if len(compute_rows) != 1 or compute_rows[0]["status"] != "Pilot required":
        errors.append("CPU/disk cost is not explicitly marked pilot required")
    if compute_rows and "multiplier" in compute_rows[0]["evidence"].lower():
        errors.append("Readout claims a compute multiplier without a pilot")
    metrics["readout_rows"] = len(readout_rows)
    metrics["readout_status_counts"] = status_counts

    component_rows = read_csv(SIMPLE_TABLE_ROOT / "simple_incident_component_spectra.csv")
    if not component_rows:
        errors.append("Incident-component source table is empty")
    component_environments = {row["environment"] for row in component_rows}
    if component_environments != {"satellite_leo530_proxy", "balloon_38km"}:
        errors.append(f"Incident-component environment set mismatch: {sorted(component_environments)}")
    if any(row["activation_or_delayed"].lower() != "false" for row in component_rows):
        errors.append("Activation/delayed rows are present in the prompt incident-component figure data")
    if any("delay" in row["component"].lower() or "activation" in row["component"].lower() for row in component_rows):
        errors.append("Activation/delayed component labels are present in the incident-source figure data")
    if any("total" == row["component"].strip().lower() for row in component_rows):
        errors.append("A cross-family source-level Total was emitted")
    if any(float(row["support_avg_intensity_cm2_s_sr_MeV"]) <= 0 for row in component_rows):
        errors.append("Incident-component table contains a nonpositive support-average intensity")
    if any(not 0.1 <= float(row["energy_MeV_total"]) <= 1.0e6 for row in component_rows):
        errors.append("Incident-component table contains an energy outside 0.1–1e6 MeV")
    expected_satellite_components = {
        "Cosmic photons",
        "Albedo photons",
        "Primary protons",
        "Secondary protons",
        "Primary alpha",
        "Primary electrons",
        "Secondary electrons",
        "Primary positrons",
        "Secondary positrons",
        "Albedo neutrons (10-GV proxy)*",
    }
    expected_balloon_components = {
        "Gamma total broadband",
        "Proton",
        "Alpha",
        "Electron",
        "Positron",
        "Neutron",
        "Muon −",
        "Muon +",
    }
    actual_satellite_components = {
        row["component"] for row in component_rows if row["environment"] == "satellite_leo530_proxy"
    }
    actual_balloon_components = {
        row["component"] for row in component_rows if row["environment"] == "balloon_38km"
    }
    if actual_satellite_components != expected_satellite_components:
        errors.append(f"Satellite incident-component inventory mismatch: {sorted(actual_satellite_components)}")
    if actual_balloon_components != expected_balloon_components:
        errors.append(f"Balloon incident-component inventory mismatch: {sorted(actual_balloon_components)}")
    metrics["incident_component_rows"] = len(component_rows)
    metrics["incident_component_environments"] = sorted(component_environments)

    expected_figure_files = {
        f"simple_0{index}_{suffix}.{extension}"
        for index, suffix in (
            (0, "incident_component_spectra"),
            (1, "gamma_source"),
            (2, "family_band_ratio"),
            (3, "readout"),
        )
        for extension in ("png", "pdf")
    }
    actual_figure_files = {path.name for path in FIGURE_ROOT.iterdir() if path.is_file()}
    if actual_figure_files != expected_figure_files:
        errors.append(f"Simple figure inventory mismatch: {sorted(actual_figure_files)}")
    image_metrics: dict[str, object] = {}
    for path in sorted(FIGURE_ROOT.glob("*.png")):
        with Image.open(path) as image:
            rgb = np.asarray(image.convert("RGB"))
            width, height = image.size
        white_fraction = float(np.mean(np.all(rgb > 250, axis=2)))
        standard_deviation = float(rgb.std())
        if width < 2200 or height < 1100:
            errors.append(f"Simple figure resolution too small: {path.name}: {width}x{height}")
        if standard_deviation < 5.0 or white_fraction > 0.98:
            errors.append(f"Simple figure appears blank: {path.name}")
        image_metrics[path.name] = {
            "width": width,
            "height": height,
            "rgb_standard_deviation": standard_deviation,
            "white_fraction": white_fraction,
        }
    for path in sorted(FIGURE_ROOT.glob("*.pdf")):
        if path.stat().st_size < 10_000:
            errors.append(f"Simple PDF appears too small: {path.name}")
    metrics["figures"] = image_metrics

    native_knots = {
        float(row["energy_keV_total"])
        for row in read_csv(TABLE_ROOT / "balloon_angular_spectra_long.csv")
        if row["family"] == "gamma" and 300.0 <= float(row["energy_keV_total"]) <= 800.0
    }
    if len(native_knots) < 3:
        errors.append("Too few balloon native gamma knots in the 300–800 keV review range")
    metrics["balloon_native_gamma_knots_300_800_keV"] = sorted(native_knots)

    warnings.extend(
        [
            "Figure 0 contains prompt incident particle spectra only; activation/delayed components and a cross-family Total are deliberately omitted.",
            "Figure 1 compares angular-domain source inputs; 450–600 keV is a broad proxy and not a narrow-line flux ratio.",
            "Figure 2 is an environment contrast only. The neutron row uses a diagnostic 10-GV fallback, partial/mixed validity is marked, and missing muons remain NA.",
            "Figure 3 deliberately leaves detector background, activation, sensitivity, and CPU/disk cost unestablished until matched transport or pilots exist.",
        ]
    )
    output_hashes = {
        str(path.relative_to(PACKAGE_ROOT)): sha256(path)
        for path in sorted(SIMPLE_ROOT.rglob("*"))
        if path.is_file()
    }
    validation = {
        "schema_version": 1,
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
        "output_sha256": output_hashes,
        "authority_boundary": "source-input comparison only; not transport, activation, response, sensitivity, or geometry-promotion authority",
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = [
        "# Simple-figure validation",
        "",
        f"Status: `{validation['status']}`",
        "",
        "This gate validates the compact four-figure product against the already validated source-comparison tables.",
        "",
        "## Checks",
        "",
        f"- {metrics['validated_source_tables']} source-table hashes match both the base PASS validation and the simple manifest.",
        f"- {metrics['simple_gamma_bands']} selected gamma bands close exactly to the base environment-contrast table.",
        f"- {metrics['simple_matrix_cells']} non-gamma matrix cells were checked; {metrics['simple_matrix_na_cells']} remain explicit NA.",
        f"- {metrics['readout_rows']} authority/readiness rows have the expected neutral status inventory.",
        f"- {metrics['incident_component_rows']} prompt incident-component data rows were checked; no activation/delayed row or cross-family Total is present.",
        "- Exactly four PNG/PDF figure pairs are present, nonblank, and above the minimum review resolution.",
        "- Native balloon gamma knots exist around the 511-keV region; the mono line remains an integrated-flux annotation.",
        "",
        "## Authority boundary",
        "",
        "PASS authorizes the compact source-input visualization only. It does not establish detector background, activation, delayed response, sensitivity, resource cost, or a geometry promotion.",
    ]
    if errors:
        report.extend(["", "## Errors", "", *[f"- {item}" for item in errors]])
    report.extend(["", "## Retained warnings", "", *[f"- {item}" for item in warnings]])
    REPORT_PATH.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"{validation['status']}: {len(errors)} errors, {len(warnings)} warnings")
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
