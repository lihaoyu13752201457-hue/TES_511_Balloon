#!/usr/bin/env python3
"""Fail-closed validation for the environment response projection package."""

from __future__ import annotations

import csv
import gzip
import json
import math
from collections import defaultdict
from pathlib import Path

from PIL import Image


PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parents[1]
OUT = PACKAGE / "outputs"
TABLES = OUT / "tables"
FIGURES = OUT / "figures"
SIMPLE = OUT / "simple"
M05 = ROOT / "engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/outputs"
REPORT = PACKAGE / "data/validation.json"

ENVIRONMENTS = ("balloon_38km", "leo530_quiet_proxy", "lunar_surface_proxy")
GEOMETRIES = ("Mass_model_511", "S3d_O8")
FAMILIES = ("gamma", "p", "n", "alpha", "eplus", "eminus", "muminus", "muplus")
T_SECONDS = 20.0 * 86400.0


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def close(a: float, b: float, *, rtol: float = 1e-10, atol: float = 1e-12) -> bool:
    return math.isclose(a, b, rel_tol=rtol, abs_tol=atol)


def main() -> int:
    errors: list[str] = []
    checks: dict[str, object] = {}

    required = [
        OUT / "summary.json",
        TABLES / "prompt_w2_primary_energy.csv",
        TABLES / "activation_rp_primary_energy.csv.gz",
        TABLES / "activation_key_energy_response.csv",
        TABLES / "projected_background_components.csv",
        TABLES / "f3_projection.csv",
        TABLES / "w2_primary_energy_intervals.csv",
        TABLES / "net_background_reduction_by_primary_energy.csv",
    ]
    for stem in ("01_source_spectra_with_w2_response_energy", "02_current_performance_contributors", "03_projected_background_and_f3"):
        required.extend([FIGURES / f"{stem}.png", FIGURES / f"{stem}.pdf"])
    required.extend(
        [
            SIMPLE / "tables/s3do8_response_energy_bands.csv",
            SIMPLE / "tables/s3do8_environment_relative_ratios.csv",
            SIMPLE / "figures/01_s3do8_response_bands_on_spectra.png",
            SIMPLE / "figures/01_s3do8_response_bands_on_spectra.pdf",
            SIMPLE / "figures/02_s3do8_environment_relative_ratios.png",
            SIMPLE / "figures/02_s3do8_environment_relative_ratios.pdf",
        ]
    )
    public_required = [
        OUT / "public/manifest.json",
        OUT / "public/REFERENCES.md",
        OUT / "public/source_reference_audit.json",
        OUT / "public/tables/normalized_minimum_detectable_flux.csv",
    ]
    for stem in (
        "01_background_energy_bands",
        "02_full_spectrum_comparison",
        "03_normalized_minimum_detectable_flux",
    ):
        public_required.extend(
            [OUT / f"public/figures/{stem}.png", OUT / f"public/figures/{stem}.pdf"]
        )
    required.extend(public_required)
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file() or path.stat().st_size == 0]
    if missing:
        errors.append(f"missing_or_empty={missing}")

    summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
    expected_status = "PASS__ENERGY_RESPONSE_REWEIGHTING_PROXY__NOT_ENVIRONMENT_TRANSPORT_AUTHORITY"
    if summary.get("status") != expected_status:
        errors.append(f"summary_status={summary.get('status')!r}")
    expected_counts = {"prompt_exact_join_events": 9, "activation_exact_join_rp_records": 97247, "selected_lineage_events": 795}
    for key, expected in expected_counts.items():
        if summary.get(key) != expected:
            errors.append(f"{key}={summary.get(key)!r}, expected={expected}")
    checks["summary_counts"] = {key: summary.get(key) for key in expected_counts}

    prompt = rows(TABLES / "prompt_w2_primary_energy.csv")
    if len(prompt) != 9:
        errors.append(f"prompt_rows={len(prompt)}, expected=9")
    anchors = {
        ("Mass_model_511", "gamma"): [4.181172, 6.742636, 8.082979, 8.146434, 14.727526, 62.991743],
        ("Mass_model_511", "eplus"): [112.810252],
        ("S3d_O8", "gamma"): [4.148290, 5.768820],
    }
    recovered: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in prompt:
        recovered[(row["geometry"], row["family"])].append(float(row["primary_energy_MeV_total"]))
        if row.get("has_pair_ia") != "True" or row.get("has_annihilation_ia") != "True":
            errors.append(
                f"prompt_pair_annihilation_chain_missing={row['geometry']}/{row['family']}/{row['local_event_id']}"
            )
    for key, expected in anchors.items():
        actual = sorted(recovered[key])
        if len(actual) != len(expected) or any(not close(a, b, rtol=0.0, atol=1e-6) for a, b in zip(actual, expected)):
            errors.append(f"prompt_energy_anchor_{key}={actual}, expected={expected}")
    checks["prompt_energy_anchors_MeV"] = {f"{g}/{f}": sorted(v) for (g, f), v in recovered.items()}
    checks["prompt_pair_annihilation_chains"] = "9/9"

    activation_count = 0
    activation_bad = 0
    with gzip.open(TABLES / "activation_rp_primary_energy.csv.gz", "rt", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            activation_count += 1
            energy = float(row["primary_energy_keV_total"])
            if row["geometry"] not in GEOMETRIES or row["incident_family"] not in FAMILIES or not math.isfinite(energy) or energy < 0:
                activation_bad += 1
    if activation_count != 97247 or activation_bad:
        errors.append(f"activation_rows={activation_count}, bad_rows={activation_bad}")
    checks["activation_rows"] = activation_count

    components = rows(TABLES / "projected_background_components.csv")
    if len(components) != len(ENVIRONMENTS) * len(GEOMETRIES) * 2 * len(FAMILIES):
        errors.append(f"component_rows={len(components)}, expected=96")
    component_sum: dict[tuple[str, str, str], float] = defaultdict(float)
    for row in components:
        rate = float(row["projected_rate_cps"])
        sigma = float(row["conditional_mc_sigma_cps"])
        if rate < 0 or sigma < 0 or not math.isfinite(rate + sigma):
            errors.append(f"invalid_component={row}")
        component_sum[(row["environment"], row["geometry"], row["stream"])] += rate

    f3 = rows(TABLES / "f3_projection.csv")
    if len(f3) != 6:
        errors.append(f"f3_rows={len(f3)}, expected=6")
    for row in f3:
        env, geometry = row["environment"], row["geometry"]
        prompt_rate = float(row["prompt_rate_cps"])
        delayed_rate = float(row["delayed_rate_cps"])
        total = float(row["total_rate_cps"])
        area = float(row["signal_effective_area_cm2"])
        estimate = float(row["F3_mapped_continuum_plus_activation_proxy_ph_cm2_s"])
        expected = 3.0 * math.sqrt(total) / (area * math.sqrt(T_SECONDS))
        if not close(prompt_rate, component_sum[(env, geometry, "prompt")]):
            errors.append(f"prompt_component_closure={env}/{geometry}")
        if not close(delayed_rate, component_sum[(env, geometry, "delayed")]):
            errors.append(f"delayed_component_closure={env}/{geometry}")
        if not close(total, prompt_rate + delayed_rate) or not close(estimate, expected):
            errors.append(f"f3_formula_closure={env}/{geometry}")

    authority = [
        row for row in rows(M05 / "04_common_response/background_prompt_delayed_cutflow.csv")
        if row["response_state"] == "measured"
        and row["stage"] == "side_compton_fov_pass"
        and row["window_id"] == "w2_510p58_511p42"
    ]
    balloon = {(row["environment"], row["geometry"]): row for row in f3 if row["environment"] == "balloon_38km"}
    for row in authority:
        projected = balloon[("balloon_38km", row["geometry"])]
        for field in ("prompt_rate_cps", "delayed_rate_cps"):
            if not close(float(projected[field]), float(row[field])):
                errors.append(f"balloon_authority_closure={row['geometry']}/{field}")
        if not close(float(projected["total_rate_cps"]), float(row["total_background_rate_cps"])):
            errors.append(f"balloon_authority_closure={row['geometry']}/total")
    checks["balloon_authority_closure"] = "PASS" if not any("balloon_authority_closure" in e for e in errors) else "FAIL"

    budget = rows(M05 / "05_matched_comparison/w2_stream_family_budget.csv")
    budget_delta: dict[str, float] = defaultdict(float)
    for row in budget:
        sign = 1.0 if row["geometry"] == "Mass_model_511" else -1.0
        budget_delta[row["family"]] += sign * float(row["rate_cps"])
    hist_delta: dict[str, float] = defaultdict(float)
    for row in rows(TABLES / "net_background_reduction_by_primary_energy.csv"):
        hist_delta[row["family"]] += float(row["mass_minus_s3d_rate_cps"])
    for family in FAMILIES:
        if not close(hist_delta[family], budget_delta[family], rtol=1e-9, atol=1e-11):
            errors.append(f"energy_hist_budget_closure={family}: {hist_delta[family]} vs {budget_delta[family]}")
    checks["net_background_reduction_cps"] = sum(budget_delta.values())

    bands = rows(SIMPLE / "tables/s3do8_response_energy_bands.csv")
    if [row["family"] for row in bands] != ["gamma", "eplus", "p", "alpha", "n"]:
        errors.append(f"simple_band_families={[row['family'] for row in bands]}")
    band_fraction = sum(float(row["s3do8_w2_fraction"]) for row in bands)
    if not (0.995 <= band_fraction <= 1.0):
        errors.append(f"simple_band_fraction={band_fraction}")
    for row in bands:
        lo, hi = float(row["energy_lo_MeV_total"]), float(row["energy_hi_MeV_total"])
        if not (math.isfinite(lo) and math.isfinite(hi) and 0 < lo < hi):
            errors.append(f"invalid_simple_band={row}")
    checks["simple_s3do8_five_family_fraction"] = band_fraction

    relative = rows(SIMPLE / "tables/s3do8_environment_relative_ratios.csv")
    if len(relative) != 21:
        errors.append(f"simple_relative_rows={len(relative)}, expected=21")
    relative_index = {(row["row_key"], row["environment"]): row for row in relative}
    ratio_check: dict[str, object] = {}
    for environment in ENVIRONMENTS:
        b_ratio = float(relative_index[("total_w2_background", environment)]["relative_to_balloon_s3do8"])
        f_ratio = float(relative_index[("f3_proxy", environment)]["relative_to_balloon_s3do8"])
        if not close(f_ratio * f_ratio, b_ratio, rtol=2e-10, atol=1e-12):
            errors.append(f"simple_f3_squared_background_ratio={environment}: {f_ratio**2} vs {b_ratio}")
        ratio_check[environment] = {"background_ratio": b_ratio, "F3_ratio": f_ratio}
    if not math.isnan(float(relative_index[("prompt_eplus", "balloon_38km")]["relative_to_balloon_s3do8"])):
        errors.append("simple_prompt_eplus_should_be_NA")
    checks["simple_s3do8_environment_ratios"] = ratio_check

    public_rows = rows(OUT / "public/tables/normalized_minimum_detectable_flux.csv")
    if len(public_rows) != 3:
        errors.append(f"public_normalized_rows={len(public_rows)}, expected=3")
    public_values: dict[str, float] = {}
    for row in public_rows:
        environment = row["environment"]
        value = float(row["normalized_minimum_detectable_flux"])
        expected = ratio_check[environment]["F3_ratio"]
        if not close(value, expected, rtol=1e-12, atol=1e-12):
            errors.append(f"public_normalized_value={environment}: {value} vs {expected}")
        public_values[environment] = value
    checks["public_normalized_minimum_detectable_flux"] = public_values

    public_manifest = json.loads((OUT / "public/manifest.json").read_text(encoding="utf-8"))
    if public_manifest.get("normalization") != "balloon_38km=1":
        errors.append(f"public_manifest_normalization={public_manifest.get('normalization')!r}")
    if public_manifest.get("generator") != "code/build_public_figures.py":
        errors.append(f"public_manifest_generator={public_manifest.get('generator')!r}")
    if "single-direction" not in public_manifest.get("angular_quantity", ""):
        errors.append(f"public_manifest_angular_quantity={public_manifest.get('angular_quantity')!r}")

    reference_audit = json.loads((OUT / "public/source_reference_audit.json").read_text(encoding="utf-8"))
    if reference_audit.get("status") != "PASS__PRIMARY_PUBLICATION_AND_PINNED_DATA_LINKS_CROSS_CHECKED":
        errors.append(f"public_reference_status={reference_audit.get('status')!r}")
    references = reference_audit.get("references", [])
    expected_dois = {
        "10.1371/journal.pone.0144679",
        "10.3847/1538-4357/ae32f4",
        "10.1029/2021JE006930",
    }
    actual_dois = {ref.get("doi") for ref in references}
    if actual_dois != expected_dois:
        errors.append(f"public_reference_dois={sorted(actual_dois)}, expected={sorted(expected_dois)}")
    atmosphere_reference = next((ref for ref in references if ref.get("environment") == "balloon_38km"), {})
    if atmosphere_reference.get("angular_doi") != "10.1371/journal.pone.0160390":
        errors.append(f"public_reference_angular_doi={atmosphere_reference.get('angular_doi')!r}")
    if reference_audit.get("angular_scope", {}).get("balloon_38km") != "strict 4pi sum of 20 equal-mu bins":
        errors.append("public_reference_balloon_angular_scope_not_4pi")
    checks["public_figure_generator"] = public_manifest.get("generator")
    checks["public_reference_dois"] = sorted(actual_dois)
    checks["public_angular_quantity"] = public_manifest.get("angular_quantity")

    image_info: dict[str, object] = {}
    image_paths = (
        sorted(FIGURES.glob("*.png"))
        + sorted((SIMPLE / "figures").glob("*.png"))
        + sorted((OUT / "public/figures").glob("*.png"))
    )
    for path in image_paths:
        with Image.open(path) as image:
            width, height = image.size
            extrema = image.convert("RGB").getextrema()
            if width < 1600 or height < 800 or all(lo == hi for lo, hi in extrema):
                errors.append(f"invalid_figure={path.name}/{width}x{height}/{extrema}")
            image_info[str(path.relative_to(OUT))] = {"width": width, "height": height, "extrema": extrema}
    checks["figures"] = image_info

    report = {
        "schema_version": 1,
        "status": "PASS" if not errors else "FAIL",
        "authority_boundary": expected_status,
        "errors": errors,
        "checks": checks,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
