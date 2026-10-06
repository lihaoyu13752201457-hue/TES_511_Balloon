#!/usr/bin/env python3
"""Fail-closed validation for the lunar source-level comparison package."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageStat


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[1]
OUTPUT_ROOT = PACKAGE_ROOT / "outputs"
TABLE_ROOT = OUTPUT_ROOT / "tables"
FIGURE_ROOT = OUTPUT_ROOT / "figures"
VALIDATION_PATH = PACKAGE_ROOT / "data" / "validation.json"

EXPECTED_INPUT_SHA256 = {
    PACKAGE_ROOT / "inputs" / "redmoon_zenodo_5561427" / "fig5.txt": "82d72b510ead4d136a289de0f32091bab5446418447c53168af32a3822f0c1f5",
    REPO_ROOT / "engineering" / "satellite_leo530_source_comparison_20260813" / "data" / "validation.json": "0c507ea29cf05d14e7af13d3d6c374e99cc28013986a6166cd6dfcd3ae5b51a7",
}

EXPECTED_OUTPUTS = (
    TABLE_ROOT / "lunar_prompt_components.csv",
    TABLE_ROOT / "three_environment_gamma_spectra.csv",
    TABLE_ROOT / "gamma_band_integrals.csv",
    TABLE_ROOT / "line_components.csv",
    FIGURE_ROOT / "three_environment_prompt_components.png",
    FIGURE_ROOT / "three_environment_prompt_components.pdf",
    FIGURE_ROOT / "gamma_balloon_leo_lunar_comparison.png",
    FIGURE_ROOT / "gamma_balloon_leo_lunar_comparison.pdf",
    OUTPUT_ROOT / "summary.json",
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


def close(actual: float, expected: float, rel: float = 2e-6, abs_tol: float = 1e-10) -> bool:
    return math.isclose(actual, expected, rel_tol=rel, abs_tol=abs_tol)


def main() -> None:
    errors: list[str] = []
    warnings = [
        "REDMoon uses a 2019 solar-minimum Apollo-17 soil proxy, not a final lunar south-pole/base-site model.",
        "The lunar total gamma curve splices a 2pi cosmic-sky proxy onto REDMoon regolith-up gamma; directional components remain separate in the tables.",
        "The 450-600 keV band is an annihilation-region proxy, not a narrow-line flux ratio.",
        "All products are prompt incident-source comparisons; activation, delayed decay, detector response, and sensitivity are outside authority.",
    ]
    metrics: dict[str, object] = {}

    for path, expected in EXPECTED_INPUT_SHA256.items():
        if not path.is_file():
            errors.append(f"missing pinned input: {path}")
            continue
        actual = sha256(path)
        if actual != expected:
            errors.append(f"input hash mismatch: {path}: {actual} != {expected}")

    for path in EXPECTED_OUTPUTS:
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"missing or empty output: {path}")

    if not errors:
        summary = json.loads((OUTPUT_ROOT / "summary.json").read_text(encoding="utf-8"))
        totals = summary["integrated_gamma_flux_cm2_s_100keV_10MeV"]
        anchors = {
            "balloon": 2.662728548943951,
            "leo": 1.940457167372,  # sum of five validated base-package bands
            "lunar_regolith": 51.831749654384424,
            "lunar_sky": 0.892160,
            "lunar_total": 52.723910,
        }
        # The sky proxy is read from rounded upstream band products, so its
        # anchor is deliberately looser than the native REDMoon/balloon gates.
        for key in ("balloon", "lunar_regolith"):
            if not close(float(totals[key]), anchors[key], rel=2e-9):
                errors.append(f"100keV-10MeV integral mismatch for {key}: {totals[key]}")
        if not close(float(totals["leo"]), anchors["leo"], rel=2e-6):
            errors.append(f"LEO total integral mismatch: {totals['leo']}")
        if not close(float(totals["lunar_sky"]), anchors["lunar_sky"], rel=3e-5):
            errors.append(f"lunar sky proxy mismatch: {totals['lunar_sky']}")
        if not close(float(totals["lunar_total"]), anchors["lunar_total"], rel=3e-5):
            errors.append(f"lunar total proxy mismatch: {totals['lunar_total']}")

        component_rows = read_csv(TABLE_ROOT / "lunar_prompt_components.csv")
        counts: dict[str, int] = {}
        previous: dict[str, float] = {}
        for row in component_rows:
            component = row["component"]
            energy = float(row["energy_MeV_total"])
            value = float(row["differential_flux_cm2_s_MeV"])
            if not math.isfinite(energy) or not math.isfinite(value) or energy <= 0 or value < 0:
                errors.append(f"invalid lunar row: {row}")
                break
            if component in previous and energy <= previous[component]:
                errors.append(f"non-increasing lunar energy axis: {component}")
                break
            previous[component] = energy
            counts[component] = counts.get(component, 0) + 1
        expected_counts = {
            "gcr_proton_reference": 21,
            "secondary_proton": 134,
            "secondary_neutron": 1091,
            "secondary_gamma": 509,
            "secondary_electron_positron": 129,
        }
        if counts != expected_counts:
            errors.append(f"REDMoon component row counts changed: {counts}")
        metrics["redmoon_component_rows"] = counts

        gamma_rows = read_csv(TABLE_ROOT / "three_environment_gamma_spectra.csv")
        peak_rows = [
            row
            for row in gamma_rows
            if row["component"] == "regolith_up_gamma"
            and close(float(row["energy_keV_total"]), 512.86, rel=0, abs_tol=1e-7)
        ]
        if len(peak_rows) != 1:
            errors.append("missing unique REDMoon 512.86-keV native gamma node")
        elif not close(
            float(peak_rows[0]["differential_flux_cm2_s_keV"]), 0.32506, rel=0, abs_tol=1e-8
        ):
            errors.append("REDMoon 512.86-keV differential node changed")

        band_rows = read_csv(TABLE_ROOT / "gamma_band_integrals.csv")
        lookup = {(row["environment"], row["component"], row["band"]): row for row in band_rows}
        key = (
            "lunar_surface_proxy",
            "total_prompt_gamma_proxy",
            "450_600_keV_annihilation_region_proxy",
        )
        if key not in lookup:
            errors.append("missing lunar 450-600-keV comparison row")
        else:
            value = float(lookup[key]["band_flux_cm2_s"])
            if not close(value, 5.291190, rel=3e-5):
                errors.append(f"lunar 450-600-keV integral mismatch: {value}")
            metrics["lunar_450_600keV_flux_cm2_s"] = value

        line_rows = read_csv(TABLE_ROOT / "line_components.csv")
        if len(line_rows) != 1 or not close(
            float(line_rows[0]["integrated_line_flux_cm2_s"]), 0.028207, rel=0, abs_tol=1e-12
        ):
            errors.append("LEO mono-511 line contract changed")
        if line_rows and "no arbitrary differential height" not in line_rows[0]["plot_treatment"]:
            errors.append("LEO delta-line plot treatment is not fail-closed")

        image_metrics: dict[str, object] = {}
        for path in (
            FIGURE_ROOT / "three_environment_prompt_components.png",
            FIGURE_ROOT / "gamma_balloon_leo_lunar_comparison.png",
        ):
            with Image.open(path) as image:
                image.load()
                width, height = image.size
                stats = ImageStat.Stat(image.convert("RGB"))
                mean_std = sum(stats.stddev) / len(stats.stddev)
            if width < 1800 or height < 900:
                errors.append(f"figure resolution too small: {path.name}: {width}x{height}")
            if mean_std < 12.0:
                errors.append(f"figure appears blank: {path.name}: RGB std {mean_std}")
            image_metrics[path.name] = {"width": width, "height": height, "rgb_std": mean_std}
        metrics["figures"] = image_metrics
        metrics["integrated_gamma_flux_cm2_s_100keV_10MeV"] = totals

    output_hashes = {
        str(path.relative_to(PACKAGE_ROOT)): sha256(path)
        for path in EXPECTED_OUTPUTS
        if path.is_file()
    }
    validation = {
        "schema_version": 1,
        "status": "PASS__SOURCE_INPUT_PROXY__NOT_TRANSPORT_AUTHORITY" if not errors else "FAIL",
        "authority_boundary": "prompt incident source comparison only; not transport, activation, delayed response, detector background, sensitivity, or geometry-promotion authority",
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
        "output_sha256": output_hashes,
    }
    VALIDATION_PATH.parent.mkdir(parents=True, exist_ok=True)
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(validation["status"])
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
