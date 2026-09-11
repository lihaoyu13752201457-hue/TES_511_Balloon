#!/usr/bin/env python3
"""Build fail-closed Section-4 uncertainty products from compact authorities.

This program deliberately does *not* open the integrated event NPZ or any raw
SIM.  It binds a completed Section-4 common-axis replay to the small catalog
metadata authorities, extracts the seven constant-weight prompt-family counts,
and reports exact Poisson intervals separately from the replay Monte Carlo
uncertainty in the five anchor receipts.

The output directory must not exist.  Files are staged in a private sibling
directory and renamed into place only after all closure checks pass.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    import scipy
    from scipy.stats import chi2
except Exception as exc:  # pragma: no cover - exercised only in a broken runtime
    raise RuntimeError(
        "SciPy is required for exact chi-square Poisson quantiles in this "
        "validated workspace; no network fallback is permitted"
    ) from exc


SCRIPT = Path(__file__).resolve()
REPO_ROOT = SCRIPT.parents[4]
SCENARIO_ID = "M05_SECTION4_SG3_SH3_BACKGROUND_SCOPE_20260828_V2"
FAMILIES = ("alpha", "eminus", "eplus", "muminus", "muplus", "n", "p")
ANCHOR_NODES = (0, 20, 40, 60, 80)
WINDOWS = ("broad_480_550", "w2_510p58_511p42")
BROAD_WINDOW = "broad_480_550"
STAGES = (
    "pre_veto",
    "plastic_positron_veto",
    "bgo_active_scintillator_veto",
    "combined_active_veto",
    "compton_trajectory_veto",
)
FINAL_WINDOW = "w2_510p58_511p42"
FINAL_STAGE = "compton_trajectory_veto"
DAY15_NODE = 60
DAY15 = 15.0
CENTRAL_CL = 0.95
ONE_SIDED_CL = 0.95
BONFERRONI_FAMILIES = len(FAMILIES)
FORMAL_CONFIG = {
    "a": {"exposure_s_per_anchor": 20_000.0, "signal_probe_trials_per_anchor": 2_000_000},
    "b": {"exposure_s_per_anchor": 200_000.0, "signal_probe_trials_per_anchor": 2_000_000},
}
CATALOG_FILENAMES = (
    "summary.json",
    "audit.json",
    "integration_provenance.json",
    "category_registry.json",
)
TIMELINE_FILENAMES = (
    "summary.json",
    "direct_cutflow_day15.csv",
    "direct_hit_multiplicity_day15.csv",
    "direct_measured_energy_day15_0p25keV.csv",
    "anchor_timeline_rates.csv",
    "mission_timeline_81nodes.csv",
    "mission_transport_components.csv",
)
COMPONENTS = ("other", "gamma_continuum", "atm511")
COMPONENT_LABELS = ("all",) + COMPONENTS
STREAM_LABELS = ("all", "prompt", "delayed")
ENERGY_STAGES = ("pre_veto", "combined_active_veto", FINAL_STAGE)


class ContractError(RuntimeError):
    """A fail-closed authority or numerical closure check failed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def load_json(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"missing required JSON: {path}")
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    require(isinstance(value, dict), f"JSON root is not an object: {path}")
    return value


def read_csv(path: Path) -> list[dict[str, str]]:
    require(path.is_file(), f"missing required CSV: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    require(rows, f"CSV contains no data rows: {path}")
    return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def finite_float(value: Any, label: str, *, nonnegative: bool = False) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ContractError(f"{label} is not numeric: {value!r}") from exc
    require(math.isfinite(number), f"{label} is not finite")
    if nonnegative:
        require(number >= 0.0, f"{label} is negative")
    return number


def exact_int(value: Any, label: str, *, nonnegative: bool = False) -> int:
    try:
        integer = int(value)
    except (TypeError, ValueError) as exc:
        raise ContractError(f"{label} is not an integer: {value!r}") from exc
    require(str(value).strip() == str(integer), f"{label} is not an exact integer: {value!r}")
    if nonnegative:
        require(integer >= 0, f"{label} is negative")
    return integer


def close(actual: float, expected: float, label: str, *, rtol: float = 5e-12) -> None:
    tolerance = max(2e-18, rtol * max(abs(actual), abs(expected)))
    require(abs(actual - expected) <= tolerance, f"{label}: {actual:.17g} != {expected:.17g}")


def resolve_recorded_path(value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()


def write_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        handle.write("\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    require(rows, f"refusing to write empty CSV: {path.name}")
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def garwood_counts(n: int, confidence: float = CENTRAL_CL) -> tuple[float, float]:
    """Equal-tail exact Garwood confidence interval for a Poisson mean."""
    require(n >= 0, "Garwood count must be nonnegative")
    require(0.0 < confidence < 1.0, "Garwood confidence must lie in (0,1)")
    alpha = 1.0 - confidence
    lower = 0.0 if n == 0 else 0.5 * float(chi2.ppf(alpha / 2.0, 2 * n))
    upper = 0.5 * float(chi2.ppf(1.0 - alpha / 2.0, 2 * (n + 1)))
    require(math.isfinite(lower) and math.isfinite(upper), "nonfinite Garwood interval")
    require(0.0 <= lower <= n <= upper, "invalid Garwood interval ordering")
    return lower, upper


def poisson_upper_count(n: int, confidence: float) -> float:
    """Exact one-sided upper confidence limit for a Poisson mean."""
    require(n >= 0, "Poisson count must be nonnegative")
    require(0.0 < confidence < 1.0, "one-sided confidence must lie in (0,1)")
    upper = 0.5 * float(chi2.ppf(confidence, 2 * (n + 1)))
    require(math.isfinite(upper) and upper >= n, "invalid one-sided Poisson limit")
    return upper


def assert_quantile_self_test() -> None:
    low0, high0 = garwood_counts(0)
    close(low0, 0.0, "Garwood n=0 lower", rtol=0.0)
    close(high0, -math.log(0.025), "Garwood n=0 central upper", rtol=2e-13)
    close(
        poisson_upper_count(0, 0.95),
        -math.log(0.05),
        "Poisson n=0 one-sided upper",
        rtol=2e-13,
    )


def sum_weighted_stats(rows: Iterable[dict[str, str]], label: str) -> tuple[int, float, float]:
    selected = 0
    rates: list[float] = []
    variances: list[float] = []
    for row in rows:
        selected += exact_int(row["selected_raw"], f"{label} selected_raw", nonnegative=True)
        rate = finite_float(row["sumw_cps"], f"{label} sumw", nonnegative=True)
        variance = finite_float(row["sumw2_cps2"], f"{label} sumw2", nonnegative=True)
        stored_sigma = finite_float(row["sqrt_sumw2_cps"], f"{label} sqrt_sumw2", nonnegative=True)
        close(stored_sigma, math.sqrt(variance), f"{label} row sqrt(sumw2)")
        rates.append(rate)
        variances.append(variance)
    return selected, math.fsum(rates), math.fsum(variances)


def require_stats_equal(
    actual: tuple[int, float, float],
    expected: tuple[int, float, float],
    label: str,
) -> None:
    require(actual[0] == expected[0], f"{label} selected_raw: {actual[0]} != {expected[0]}")
    close(actual[1], expected[1], f"{label} sumw")
    close(actual[2], expected[2], f"{label} sumw2")


def validate_day15_diagnostic_products(
    timeline_paths: dict[str, Path], summary: dict[str, Any]
) -> dict[str, Any]:
    """Close both manuscript diagnostic CSVs to the formal day-15 cutflow."""
    cutflow = read_csv(timeline_paths["direct_cutflow_day15.csv"])
    multiplicity = read_csv(timeline_paths["direct_hit_multiplicity_day15.csv"])
    spectrum = read_csv(timeline_paths["direct_measured_energy_day15_0p25keV.csv"])
    schema = summary.get("day15_product_schema", {})

    require(
        int(schema.get("direct_hit_multiplicity_day15.csv", {}).get("rows", -1))
        == len(multiplicity),
        "day-15 multiplicity row count differs from timeline schema",
    )
    require(
        int(schema.get("direct_measured_energy_day15_0p25keV.csv", {}).get("rows", -1))
        == len(spectrum),
        "day-15 measured-energy row count differs from timeline schema",
    )
    require(
        set(schema.get("direct_hit_multiplicity_day15.csv", {}).get("components", []))
        == set(COMPONENT_LABELS),
        "day-15 multiplicity component schema mismatch",
    )
    require(
        set(schema.get("direct_measured_energy_day15_0p25keV.csv", {}).get("components", []))
        == set(COMPONENT_LABELS),
        "day-15 measured-energy component schema mismatch",
    )

    for name, rows in (
        ("cutflow", cutflow),
        ("multiplicity", multiplicity),
        ("measured-energy", spectrum),
    ):
        require(
            all(
                exact_int(row["time_bin_id"], f"{name} time_bin_id", nonnegative=True)
                == DAY15_NODE
                and math.isclose(
                    finite_float(row["day_mid"], f"{name} day_mid"),
                    DAY15,
                    rel_tol=0.0,
                    abs_tol=1e-12,
                )
                for row in rows
            ),
            f"{name} contains a row outside the day-15 authority",
        )

    def cutflow_stats(
        window: str, stage: str, stream: str = "all", component: str = "all"
    ) -> tuple[int, float, float]:
        chosen = [
            row
            for row in cutflow
            if row["window_id"] == window
            and row["stage"] == stage
            and (stream == "all" or row["stream"] == stream)
            and (component == "all" or row["component"] == component)
        ]
        return sum_weighted_stats(chosen, f"cutflow {window}/{stage}/{stream}/{component}")

    multiplicity_keys: set[tuple[str, str, str, int]] = set()
    for row in multiplicity:
        require(row["window_id"] in WINDOWS, "multiplicity contains an unknown window")
        require(row["stage"] in STAGES, "multiplicity contains an unknown stage")
        require(row["component"] in COMPONENT_LABELS, "multiplicity contains an unknown component")
        hit_multiplicity = exact_int(
            row["hit_multiplicity"], "hit multiplicity", nonnegative=True
        )
        require(hit_multiplicity > 0, "multiplicity contains a nonpositive hit count")
        key = (row["window_id"], row["stage"], row["component"], hit_multiplicity)
        require(key not in multiplicity_keys, f"duplicate multiplicity cell: {key}")
        multiplicity_keys.add(key)
    require(
        {(window, stage, component) for window, stage, component, _ in multiplicity_keys}
        == {
            (window, stage, component)
            for window in WINDOWS
            for stage in STAGES
            for component in COMPONENT_LABELS
        },
        "multiplicity does not cover every window/stage/component cell",
    )
    for window in WINDOWS:
        for stage in STAGES:
            named_stats: list[tuple[int, float, float]] = []
            for component in COMPONENTS:
                rows = [
                    row
                    for row in multiplicity
                    if row["window_id"] == window
                    and row["stage"] == stage
                    and row["component"] == component
                ]
                actual = sum_weighted_stats(
                    rows, f"multiplicity {window}/{stage}/{component}"
                )
                expected = cutflow_stats(window, stage, component=component)
                require_stats_equal(
                    actual, expected, f"multiplicity/cutflow {window}/{stage}/{component}"
                )
                named_stats.append(actual)
            all_rows = [
                row
                for row in multiplicity
                if row["window_id"] == window
                and row["stage"] == stage
                and row["component"] == "all"
            ]
            all_stats = sum_weighted_stats(all_rows, f"multiplicity {window}/{stage}/all")
            named_total = (
                sum(value[0] for value in named_stats),
                math.fsum(value[1] for value in named_stats),
                math.fsum(value[2] for value in named_stats),
            )
            require_stats_equal(
                all_stats, named_total, f"multiplicity named-components=all {window}/{stage}"
            )
            require_stats_equal(
                all_stats, cutflow_stats(window, stage), f"multiplicity/cutflow {window}/{stage}/all"
            )

    expected_low_edges = [480.0 + 0.25 * index for index in range(280)]
    spectrum_cells: dict[tuple[str, str, str, int], dict[str, str]] = {}
    for row in spectrum:
        require(row["stage"] in ENERGY_STAGES, "measured-energy spectrum contains an unknown stage")
        require(row["stream"] in STREAM_LABELS, "measured-energy spectrum contains an unknown stream")
        require(row["component"] in COMPONENT_LABELS, "measured-energy spectrum contains an unknown component")
        low = finite_float(row["energy_low_keV"], "spectrum low edge")
        high = finite_float(row["energy_high_keV"], "spectrum high edge")
        bin_index_float = (low - 480.0) / 0.25
        bin_index = round(bin_index_float)
        require(0 <= bin_index < 280, f"spectrum bin index outside 480--550 keV: {low}")
        close(bin_index_float, float(bin_index), "spectrum 0.25-keV bin index")
        close(low, expected_low_edges[bin_index], "spectrum low-edge closure")
        close(high, low + 0.25, "spectrum bin-width closure")
        key = (row["stage"], row["stream"], row["component"], bin_index)
        require(key not in spectrum_cells, f"duplicate spectrum cell: {key}")
        spectrum_cells[key] = row
        sum_weighted_stats((row,), f"spectrum row {key}")
    expected_spectrum_keys = {
        (stage, stream, component, bin_index)
        for stage in ENERGY_STAGES
        for stream in STREAM_LABELS
        for component in COMPONENT_LABELS
        for bin_index in range(280)
    }
    require(set(spectrum_cells) == expected_spectrum_keys, "measured-energy spectrum Cartesian coverage mismatch")

    def spectrum_bin_stats(
        stage: str, stream: str, component: str, bin_index: int
    ) -> tuple[int, float, float]:
        return sum_weighted_stats(
            (spectrum_cells[(stage, stream, component, bin_index)],),
            f"spectrum {stage}/{stream}/{component}/{bin_index}",
        )

    for stage in ENERGY_STAGES:
        for bin_index in range(280):
            for component in COMPONENT_LABELS:
                all_stream = spectrum_bin_stats(stage, "all", component, bin_index)
                prompt = spectrum_bin_stats(stage, "prompt", component, bin_index)
                delayed = spectrum_bin_stats(stage, "delayed", component, bin_index)
                require_stats_equal(
                    all_stream,
                    (
                        prompt[0] + delayed[0],
                        prompt[1] + delayed[1],
                        prompt[2] + delayed[2],
                    ),
                    f"spectrum prompt+delayed=all {stage}/{component}/{bin_index}",
                )
            for stream in STREAM_LABELS:
                all_component = spectrum_bin_stats(stage, stream, "all", bin_index)
                named = [
                    spectrum_bin_stats(stage, stream, component, bin_index)
                    for component in COMPONENTS
                ]
                require_stats_equal(
                    all_component,
                    (
                        sum(value[0] for value in named),
                        math.fsum(value[1] for value in named),
                        math.fsum(value[2] for value in named),
                    ),
                    f"spectrum named-components=all {stage}/{stream}/{bin_index}",
                )
        for stream in STREAM_LABELS:
            for component in COMPONENT_LABELS:
                actual = sum_weighted_stats(
                    (
                        spectrum_cells[(stage, stream, component, bin_index)]
                        for bin_index in range(280)
                    ),
                    f"spectrum broad total {stage}/{stream}/{component}",
                )
                require_stats_equal(
                    actual,
                    cutflow_stats(
                        BROAD_WINDOW,
                        stage,
                        stream=stream,
                        component=component,
                    ),
                    f"spectrum/cutflow broad {stage}/{stream}/{component}",
                )

    return {
        "status": "PASS__DAY15_DIAGNOSTIC_CSV_SHA_AND_ADDITIVE_CLOSURE",
        "direct_cutflow_rows": len(cutflow),
        "direct_hit_multiplicity_rows": len(multiplicity),
        "direct_measured_energy_rows": len(spectrum),
        "multiplicity_contract": "named components sum to all and all cells close to direct cutflow",
        "measured_energy_contract": "prompt+delayed and named-component binwise closure plus 480--550 keV totals equal direct cutflow",
    }
    close(
        poisson_upper_count(0, 1.0 - 0.05 / BONFERRONI_FAMILIES),
        -math.log(0.05 / BONFERRONI_FAMILIES),
        "Poisson n=0 Bonferroni upper",
        rtol=2e-13,
    )


def validate_catalog(catalog_dir: Path, model: str) -> dict[str, Any]:
    paths = {name: catalog_dir / name for name in CATALOG_FILENAMES}
    payloads = {name: load_json(path) for name, path in paths.items()}
    summary = payloads["summary.json"]
    audit = payloads["audit.json"]
    provenance = payloads["integration_provenance.json"]
    registry = payloads["category_registry.json"]

    require(summary.get("status") == "COMPLETE__POSITIVE_FLUXCLOSED_EVENT_CATALOG", "catalog summary status is not complete")
    require(audit.get("status") == "PASS__FLUXCLOSED_CATALOG_AUDIT", "catalog audit status is not PASS")
    require(provenance.get("status") == "PASS__INTEGRATION_PROVENANCE", "integration provenance status is not PASS")
    for label, payload in (("summary", summary), ("audit", audit), ("provenance", provenance)):
        require(payload.get("model") == model, f"catalog {label} model mismatch")
    require(summary.get("integration_status") == "PASS__INTEGRATED_PROMPT_STATISTICS", "catalog integration status is not PASS")
    require(audit.get("integration_status") == "PASS__INTEGRATED_PROMPT_STATISTICS", "catalog audit integration status is not PASS")
    require(summary.get("integration_schema") == "m05_integrated_fluxclosed_catalog_v1", "catalog integration schema mismatch")
    require(audit.get("integration_schema") == "m05_integrated_fluxclosed_catalog_v1", "catalog audit integration schema mismatch")
    require(provenance.get("schema") == "m05_integrated_fluxclosed_catalog_v1", "provenance schema mismatch")
    require(registry.get("integration_schema") == "m05_integrated_fluxclosed_catalog_v1", "category registry integration schema mismatch")
    require(summary.get("integration_provenance") == "integration_provenance.json", "summary does not bind integration provenance")
    require(audit.get("integration_provenance") == "integration_provenance.json", "audit does not bind integration provenance")
    require(registry.get("integration_provenance") == "integration_provenance.json", "registry does not bind integration provenance")
    require(registry.get("weight_authority") == "combined_event_catalog.npz:event_base_weight_cps", "category weight authority mismatch")

    blocks = [
        summary.get("prompt_family_integration"),
        audit.get("prompt_family_integration"),
        provenance.get("families"),
    ]
    require(all(isinstance(item, dict) for item in blocks), "missing prompt-family integration block")
    require(blocks[0] == blocks[1] == blocks[2], "prompt-family integration differs across authorities")
    families: dict[str, Any] = blocks[0]
    require(set(families) == set(FAMILIES), "prompt-family integration does not contain exactly seven retained families")

    categories = registry.get("categories")
    require(isinstance(categories, list) and categories, "category registry has no categories")
    prompt_categories: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in categories:
        require(isinstance(row, dict), "category registry contains a non-object row")
        if row.get("stream") == "prompt" and row.get("component") == "other" and row.get("family") in FAMILIES:
            prompt_categories[str(row["family"])].append(row)
    require(set(prompt_categories) == set(FAMILIES), "registry prompt-family coverage mismatch")

    for family in FAMILIES:
        info = families[family]
        require(info.get("status") == "PASS__UNIFIED_OLD_PLUS_SUPPLEMENT_EXPOSURE", f"{family} integration status is not PASS")
        old_t = finite_float(info.get("old_exposure_TT_s"), f"{family} T_old", nonnegative=True)
        new_t = finite_float(info.get("supplement_exposure_TT_s"), f"{family} T_new", nonnegative=True)
        total_t = finite_float(info.get("combined_exposure_TT_s"), f"{family} T_total", nonnegative=True)
        require(old_t > 0.0 and new_t > 0.0 and total_t > 0.0, f"{family} exposure is not strictly positive")
        close(old_t + new_t, total_t, f"{family} T_old+T_new=T_total")
        weight = finite_float(info.get("unified_event_weight_cps"), f"{family} unified weight", nonnegative=True)
        close(weight, 1.0 / total_t, f"{family} unified weight=1/T_total")
        family_categories = prompt_categories[family]
        require(sum(int(row["event_count"]) for row in family_categories) == int(info["detector_positive_events"]), f"{family} registry event-count closure failed")
        for row in family_categories:
            require(row.get("weight_policy") == "constant_category_weight", f"{family} category is not constant-weight")
            require(row.get("integration_weight_policy") == "constant_family_weight__unified_old_plus_supplement_exposure", f"{family} integration weight policy mismatch")
            close(finite_float(row.get("base_event_weight_cps"), f"{family} category weight"), weight, f"{family} category unified weight")
            close(finite_float(row.get("family_old_exposure_TT_s"), f"{family} category T_old"), old_t, f"{family} category T_old closure")
            close(finite_float(row.get("family_supplement_exposure_TT_s"), f"{family} category T_new"), new_t, f"{family} category T_new closure")
            close(finite_float(row.get("family_combined_exposure_TT_s"), f"{family} category T_total"), total_t, f"{family} category T_total closure")

    hashes = {name: sha256_file(path) for name, path in paths.items()}
    metadata_fingerprint = canonical_sha256(
        {"schema": "m05_integrated_catalog_metadata_fingerprint_v1", "model": model, "file_sha256": hashes}
    )
    return {
        "summary": summary,
        "audit": audit,
        "provenance": provenance,
        "registry": registry,
        "paths": paths,
        "hashes": hashes,
        "metadata_fingerprint_sha256": metadata_fingerprint,
        "families": families,
    }


def fingerprint_file_map(timeline_summary: dict[str, Any]) -> dict[Path, str]:
    fingerprint = timeline_summary.get("input_fingerprint")
    require(isinstance(fingerprint, dict), "timeline summary lacks input_fingerprint")
    recorded = fingerprint.get("file_sha256")
    require(isinstance(recorded, dict) and recorded, "timeline input fingerprint has no file hashes")
    result: dict[Path, str] = {}
    for path_text, digest in recorded.items():
        resolved = resolve_recorded_path(str(path_text))
        require(resolved not in result, f"duplicate resolved fingerprint path: {resolved}")
        result[resolved] = str(digest)
    return result


def validate_timeline(timeline_dir: Path, catalog: dict[str, Any], model: str) -> dict[str, Any]:
    timeline_paths = {name: timeline_dir / name for name in TIMELINE_FILENAMES}
    summary = load_json(timeline_paths["summary.json"])
    require(summary.get("status") == "PASS__M05_SECTION4_COMMON_TIME_TIMELINE", "timeline summary is not complete Section-4 V2 output")
    require(summary.get("model") == model, "timeline model mismatch")
    require(set(summary.get("outputs", [])) >= set(TIMELINE_FILENAMES), "timeline summary does not declare all required completed outputs")
    for path in timeline_paths.values():
        require(path.is_file(), f"completed timeline output is missing: {path}")
    timeline_hashes_before_validation = {
        name: sha256_file(path) for name, path in timeline_paths.items()
    }

    scenario_values = (
        summary.get("analysis_scenario", {}).get("scenario_id"),
        summary.get("run_parameters", {}).get("analysis_scenario_id"),
        summary.get("input_fingerprint", {}).get("parameters", {}).get("analysis_scenario_id"),
        summary.get("input_fingerprint", {}).get("analysis_scenario", {}).get("scenario_id"),
    )
    require(all(value == SCENARIO_ID for value in scenario_values), "timeline is not bound consistently to Section-4 scenario V2")
    scenario = summary["analysis_scenario"]
    require(scenario.get("scope_applied_at") == "category_rate_matrix_before_poisson_arrivals", "component scope was not applied before Poisson arrivals")
    require(scenario.get("disabled_components") == ["atm511"], "Section-4 V2 disabled-component scope mismatch")
    require(scenario.get("enabled_components") == ["other", "gamma_continuum"], "Section-4 V2 enabled-component scope mismatch")
    grouping = str(scenario.get("grouping_then_response_contract", ""))
    require("Poisson arrivals" in grouping and "response -> veto -> Compton" in grouping, "timeline grouping/response order is not authoritative")
    require(summary.get("day15_product_schema", {}).get("closure_status") == "PASS__DAY15_PRODUCTS_ADDITIVE_CUTFLOW_CLOSED", "day-15 products are not additively closed")
    day15_diagnostic_closure = validate_day15_diagnostic_products(
        timeline_paths, summary
    )

    input_fingerprint = summary["input_fingerprint"]
    recorded_fingerprint_sha = str(summary.get("input_fingerprint_sha256", ""))
    require(canonical_sha256(input_fingerprint) == recorded_fingerprint_sha, "timeline input fingerprint SHA-256 does not close")
    require(input_fingerprint.get("model") == model, "timeline fingerprint model mismatch")
    recorded_catalog = resolve_recorded_path(str(input_fingerprint.get("catalog_npz", {}).get("path", "")))
    require(recorded_catalog.parent == catalog["paths"]["summary.json"].parent.resolve(), "timeline fingerprint points to a different integrated catalog directory")
    require(recorded_catalog.name == "combined_event_catalog.npz", "timeline fingerprint catalog basename mismatch")
    require(int(input_fingerprint.get("catalog_events", -1)) == int(catalog["summary"]["events"]), "timeline/catalog event-count mismatch")
    require(int(input_fingerprint.get("catalog_hits", -1)) == int(catalog["summary"]["hits"]), "timeline/catalog hit-count mismatch")
    require(int(input_fingerprint.get("catalog_categories", -1)) == len(catalog["registry"]["categories"]), "timeline/catalog category-count mismatch")

    recorded_hashes = fingerprint_file_map(summary)
    for name in ("summary.json", "audit.json", "category_registry.json"):
        path = catalog["paths"][name].resolve()
        require(path in recorded_hashes, f"timeline fingerprint does not bind catalog {name}")
        require(recorded_hashes[path] == catalog["hashes"][name], f"timeline fingerprint hash mismatch for catalog {name}")

    params = summary.get("run_parameters")
    require(isinstance(params, dict), "timeline summary lacks run_parameters")
    require(tuple(int(value) for value in params.get("anchor_time_bin_ids", [])) == ANCHOR_NODES, "timeline anchor nodes mismatch")
    exposure = finite_float(params.get("exposure_s_per_anchor"), "timeline exposure", nonnegative=True)
    require(exposure > 0.0, "timeline exposure is not positive")
    signal_trials = exact_int(params.get("signal_probe_trials_per_anchor"), "signal probe trials", nonnegative=True)
    require(signal_trials > 0, "signal probe trials is zero")
    close(finite_float(params.get("coincidence_window_s"), "coincidence window"), 1e-6, "coincidence window=1 us")

    expected_formal = FORMAL_CONFIG[model]
    formal = (
        math.isclose(exposure, expected_formal["exposure_s_per_anchor"], rel_tol=0.0, abs_tol=1e-12)
        and signal_trials == expected_formal["signal_probe_trials_per_anchor"]
    )

    anchors = summary.get("anchors")
    require(isinstance(anchors, dict) and set(anchors) == {str(node) for node in ANCHOR_NODES}, "timeline summary does not bind exactly five anchors")
    receipts: dict[int, dict[str, Any]] = {}
    receipt_hashes: dict[str, str] = {}
    for node in ANCHOR_NODES:
        path = timeline_dir / "receipts" / f"anchor_{node:03d}.json"
        receipt = load_json(path)
        require(receipt.get("status") == "PASS__FLUXCLOSED_ANCHOR_COMPLETE", f"anchor {node} receipt is not PASS")
        require(receipt.get("model") == model, f"anchor {node} model mismatch")
        require(int(receipt.get("time_bin_id", -1)) == node, f"anchor {node} node mismatch")
        require(receipt.get("input_fingerprint_sha256") == recorded_fingerprint_sha, f"anchor {node} fingerprint mismatch")
        close(finite_float(receipt.get("day_mid"), f"anchor {node} day"), node / 4.0, f"anchor {node} day-axis closure")
        close(finite_float(receipt.get("timeline", {}).get("exposure_s"), f"anchor {node} exposure"), exposure, f"anchor {node} exposure closure")
        require(set(receipt.get("timeline", {}).get("counts", {})) == {f"{window}__{stage}" for window in WINDOWS for stage in STAGES}, f"anchor {node} count-key coverage mismatch")
        require(set(receipt.get("direct", {})) == {f"{window}__{stage}" for window in WINDOWS for stage in STAGES}, f"anchor {node} direct-key coverage mismatch")
        require(exact_int(receipt.get("signal_probe", {}).get("trials"), f"anchor {node} signal trials", nonnegative=True) == signal_trials, f"anchor {node} signal-trial closure failed")
        summary_anchor = anchors[str(node)]
        require(isinstance(summary_anchor, dict), f"summary anchor {node} is not an object")
        recorded_receipt = resolve_recorded_path(str(summary_anchor.get("receipt", "")))
        require(recorded_receipt == path.resolve(), f"summary anchor {node} binds a different receipt")
        final_key = f"{FINAL_WINDOW}__{FINAL_STAGE}"
        final_count = exact_int(receipt["timeline"]["counts"][final_key], f"anchor {node} final count", nonnegative=True)
        final_direct_rate = finite_float(receipt["direct"][final_key]["rate_cps"], f"anchor {node} final direct rate", nonnegative=True)
        require(final_count > 0 and final_direct_rate > 0.0, f"anchor {node} final replay cell is not positive")
        final_ratio = (final_count / exposure) / final_direct_rate
        final_ratio_se = (math.sqrt(final_count) / exposure) / final_direct_rate
        close(finite_float(receipt.get("final_timeline_to_direct_ratio"), f"anchor {node} final ratio"), final_ratio, f"anchor {node} final ratio closure")
        close(finite_float(receipt.get("final_timeline_to_direct_ratio_standard_error"), f"anchor {node} final ratio SE"), final_ratio_se, f"anchor {node} final ratio SE closure")
        close(finite_float(summary_anchor.get("timeline_to_direct_ratio"), f"summary anchor {node} ratio"), final_ratio, f"summary anchor {node} ratio closure")
        close(finite_float(summary_anchor.get("timeline_to_direct_ratio_standard_error"), f"summary anchor {node} ratio SE"), final_ratio_se, f"summary anchor {node} ratio SE closure")
        receipts[node] = receipt
        receipt_hashes[path.name] = sha256_file(path)

    timeline_hashes = {name: sha256_file(path) for name, path in timeline_paths.items()}
    require(
        timeline_hashes == timeline_hashes_before_validation,
        "timeline JSON/CSV changed while hashes and additive closure were validated",
    )

    return {
        "summary": summary,
        "paths": timeline_paths,
        "recorded_hashes": recorded_hashes,
        "input_fingerprint_sha256": recorded_fingerprint_sha,
        "exposure_s_per_anchor": exposure,
        "signal_probe_trials_per_anchor": signal_trials,
        "run_classification": "FORMAL_AUTHORITY_CONFIG_MATCH" if formal else "FASTCHECK_OR_CUSTOM_COMPLETE_FIVE_ANCHOR_REPLAY",
        "formal_authority_config_match": formal,
        "receipts": receipts,
        "timeline_file_sha256": timeline_hashes,
        "receipt_file_sha256": receipt_hashes,
        "day15_diagnostic_closure": day15_diagnostic_closure,
    }


def load_family_scales(timeline: dict[str, Any]) -> tuple[Path, str, dict[str, float]]:
    matches = [
        (path, digest)
        for path, digest in timeline["recorded_hashes"].items()
        if path.name == "parma_energy_integrated_family_scales_81bins.csv"
    ]
    require(len(matches) == 1, "timeline fingerprint must bind exactly one family-scales CSV")
    path, recorded_sha = matches[0]
    require(path.is_file(), f"family-scales CSV is missing: {path}")
    actual_sha = sha256_file(path)
    require(actual_sha == recorded_sha, "family-scales CSV hash differs from timeline fingerprint")
    rows = read_csv(path)
    require(len(rows) == 81, "family-scales CSV does not contain 81 nodes")
    by_node = {exact_int(row["time_bin_id"], "family-scale time_bin_id", nonnegative=True): row for row in rows}
    require(set(by_node) == set(range(81)), "family-scales node coverage mismatch")
    day15 = by_node[DAY15_NODE]
    close(finite_float(day15["day_mid"], "family-scale day15"), DAY15, "family-scale day15 axis")
    scales = {
        family: finite_float(day15[f"scale_{family}_to_parma_reference"], f"day15 {family} scale", nonnegative=True)
        for family in FAMILIES
    }
    require(all(value > 0.0 for value in scales.values()), "day15 family scale is not strictly positive")
    return path, actual_sha, scales


def build_family_products(
    catalog: dict[str, Any], timeline: dict[str, Any], scales: dict[str, float]
) -> list[dict[str, Any]]:
    cutflow_rows = read_csv(timeline["paths"]["direct_cutflow_day15.csv"])
    selected: dict[str, dict[str, str]] = {}
    for row in cutflow_rows:
        if (
            row.get("time_bin_id") == str(DAY15_NODE)
            and row.get("stream") == "prompt"
            and row.get("component") == "other"
            and row.get("window_id") == FINAL_WINDOW
            and row.get("stage") == FINAL_STAGE
            and row.get("family") in FAMILIES
        ):
            family = str(row["family"])
            require(family not in selected, f"duplicate day15 final prompt row for {family}")
            selected[family] = row
    require(set(selected) == set(FAMILIES), "day15 final prompt cutflow does not contain exactly seven families")

    alpha_family = 1.0 - CENTRAL_CL
    alpha_one_sided = 1.0 - ONE_SIDED_CL
    alpha_bonf = alpha_one_sided / BONFERRONI_FAMILIES
    rows: list[dict[str, Any]] = []
    for family in FAMILIES:
        item = catalog["families"][family]
        cutflow = selected[family]
        n = exact_int(cutflow["selected_raw"], f"{family} selected_raw", nonnegative=True)
        old_t = finite_float(item["old_exposure_TT_s"], f"{family} T_old")
        new_t = finite_float(item["supplement_exposure_TT_s"], f"{family} T_new")
        total_t = finite_float(item["combined_exposure_TT_s"], f"{family} T_total")
        weight = finite_float(item["unified_event_weight_cps"], f"{family} weight")
        scale = scales[family]
        scaled_weight = weight * scale
        rate_hat = n * scaled_weight
        cutflow_rate = finite_float(cutflow["sumw_cps"], f"{family} cutflow rate", nonnegative=True)
        cutflow_sumw2 = finite_float(cutflow["sumw2_cps2"], f"{family} cutflow sumw2", nonnegative=True)
        close(cutflow_rate, rate_hat, f"{family} day15 rate=n*scale/T")
        close(cutflow_sumw2, n * scaled_weight * scaled_weight, f"{family} day15 sumw2=n*(scale/T)^2")

        central_low, central_high = garwood_counts(n, CENTRAL_CL)
        upper_95 = poisson_upper_count(n, ONE_SIDED_CL)
        upper_familywise = poisson_upper_count(n, 1.0 - alpha_bonf)
        rows.append(
            {
                "model": timeline["summary"]["model"],
                "scenario_id": SCENARIO_ID,
                "time_bin_id": DAY15_NODE,
                "day_mid": DAY15,
                "stream": "prompt",
                "component": "other",
                "window_id": FINAL_WINDOW,
                "stage": FINAL_STAGE,
                "family": family,
                "selected_raw": n,
                "T_old_s": old_t,
                "T_new_s": new_t,
                "T_total_s": total_t,
                "unified_weight_cps": weight,
                "day15_family_scale": scale,
                "scaled_selected_event_weight_cps": scaled_weight,
                "rate_hat_cps": rate_hat,
                "garwood_central_confidence_level": CENTRAL_CL,
                "garwood_central_alpha": alpha_family,
                "garwood_central_lower_count": central_low,
                "garwood_central_upper_count": central_high,
                "garwood_central_lower_rate_cps": central_low * scaled_weight,
                "garwood_central_upper_rate_cps": central_high * scaled_weight,
                "one_sided_confidence_level": ONE_SIDED_CL,
                "one_sided_alpha": alpha_one_sided,
                "one_sided_upper_count": upper_95,
                "one_sided_upper_rate_cps": upper_95 * scaled_weight,
                "bonferroni_family_count": BONFERRONI_FAMILIES,
                "bonferroni_per_family_alpha": alpha_bonf,
                "bonferroni_familywise_confidence_at_least": 1.0 - BONFERRONI_FAMILIES * alpha_bonf,
                "bonferroni_familywise_upper_count": upper_familywise,
                "bonferroni_familywise_upper_rate_cps": upper_familywise * scaled_weight,
                "zero_count_uncertainty_policy": "exact_nonzero_upper_limits" if n == 0 else "exact_count_interval",
            }
        )
    return rows


def build_anchor_products(timeline: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    csv_rows = read_csv(timeline["paths"]["anchor_timeline_rates.csv"])
    csv_by_key: dict[tuple[int, str, str], dict[str, str]] = {}
    for row in csv_rows:
        key = (exact_int(row["time_bin_id"], "anchor CSV node", nonnegative=True), row["window_id"], row["stage"])
        require(key not in csv_by_key, f"duplicate anchor CSV key: {key}")
        csv_by_key[key] = row
    expected_keys = {(node, window, stage) for node in ANCHOR_NODES for window in WINDOWS for stage in STAGES}
    require(set(csv_by_key) == expected_keys, "anchor timeline CSV does not contain exactly 5x2x5 rows")

    exposure = timeline["exposure_s_per_anchor"]
    rows: list[dict[str, Any]] = []
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for node in ANCHOR_NODES:
        receipt = timeline["receipts"][node]
        for window in WINDOWS:
            for stage in STAGES:
                combined_key = f"{window}__{stage}"
                csv_row = csv_by_key[(node, window, stage)]
                count = exact_int(receipt["timeline"]["counts"][combined_key], f"anchor {node} {combined_key} count", nonnegative=True)
                direct = receipt["direct"][combined_key]
                direct_rate = finite_float(direct["rate_cps"], f"anchor {node} {combined_key} direct rate", nonnegative=True)
                direct_sumw2 = finite_float(direct["sum_wi2_cps2"], f"anchor {node} {combined_key} direct sumw2", nonnegative=True)
                direct_sigma = math.sqrt(direct_sumw2)
                timeline_rate = count / exposure
                replay_se = math.sqrt(count) / exposure
                expected = direct_rate * exposure
                ratio: float | str = timeline_rate / direct_rate if direct_rate > 0.0 else ""
                ratio_se: float | str = replay_se / direct_rate if direct_rate > 0.0 else ""
                residual: float | str = (count - expected) / math.sqrt(expected) if expected > 0.0 else ""
                pearson: float | str = float(residual) ** 2 if residual != "" else ""

                require(exact_int(csv_row["timeline_counts"], "anchor CSV timeline count", nonnegative=True) == count, f"anchor {node} {combined_key} receipt/CSV count mismatch")
                close(finite_float(csv_row["timeline_rate_cps"], "anchor CSV timeline rate"), timeline_rate, f"anchor {node} {combined_key} timeline rate closure")
                close(finite_float(csv_row["timeline_rate_standard_error_cps"], "anchor CSV timeline SE"), replay_se, f"anchor {node} {combined_key} timeline SE closure")
                close(finite_float(csv_row["direct_no_coincidence_rate_cps"], "anchor CSV direct rate"), direct_rate, f"anchor {node} {combined_key} direct rate closure")
                close(finite_float(csv_row["direct_sum_W_i2_cps2"], "anchor CSV direct sumw2"), direct_sumw2, f"anchor {node} {combined_key} direct sumw2 closure")
                if ratio != "":
                    close(finite_float(csv_row["timeline_to_direct_ratio"], "anchor CSV ratio"), float(ratio), f"anchor {node} {combined_key} ratio closure")

                row = {
                    "model": timeline["summary"]["model"],
                    "scenario_id": SCENARIO_ID,
                    "timeline_run_classification": timeline["run_classification"],
                    "time_bin_id": node,
                    "day_mid": finite_float(receipt["day_mid"], f"anchor {node} day"),
                    "window_id": window,
                    "stage": stage,
                    "exposure_s": exposure,
                    "timeline_count": count,
                    "timeline_rate_cps": timeline_rate,
                    "replay_MC_standard_error_cps": replay_se,
                    "replay_MC_variance_counts2_plugin": count,
                    "replay_MC_variance_rate_cps2_plugin": count / (exposure * exposure),
                    "direct_no_coincidence_rate_cps": direct_rate,
                    "direct_expected_counts": expected,
                    "finite_template_sum_W_i2_cps2": direct_sumw2,
                    "finite_template_transport_sigma_cps": direct_sigma,
                    "finite_template_selected_raw": exact_int(direct["selected_raw"], f"anchor {node} {combined_key} direct selected_raw", nonnegative=True),
                    "timeline_to_direct_ratio": ratio,
                    "timeline_to_direct_ratio_standard_error_replay_MC_only": ratio_se,
                    "pearson_residual_vs_direct_expectation": residual,
                    "pearson_dispersion_contribution_vs_direct_expectation": pearson,
                    "uncertainty_separation": "finite_template_and_replay_MC_reported_separately_not_jointly_propagated",
                }
                rows.append(row)
                grouped[(window, stage)].append(row)

    dispersion_rows: list[dict[str, Any]] = []
    for window in WINDOWS:
        for stage in STAGES:
            values = grouped[(window, stage)]
            require(len(values) == len(ANCHOR_NODES), f"anchor dispersion group incomplete for {window}/{stage}")
            sum_count = sum(int(row["timeline_count"]) for row in values)
            sum_expected = sum(float(row["direct_expected_counts"]) for row in values)
            require(sum_expected > 0.0, f"zero direct expectation for {window}/{stage}")
            pooled_ratio = sum_count / sum_expected
            pooled_ratio_se = math.sqrt(sum_count) / sum_expected
            pearson_fixed = sum((int(row["timeline_count"]) - float(row["direct_expected_counts"])) ** 2 / float(row["direct_expected_counts"]) for row in values)
            require(pooled_ratio > 0.0, f"zero pooled replay ratio for {window}/{stage}")
            pearson_fitted = sum(
                (int(row["timeline_count"]) - pooled_ratio * float(row["direct_expected_counts"])) ** 2
                / (pooled_ratio * float(row["direct_expected_counts"]))
                for row in values
            )
            dispersion_rows.append(
                {
                    "model": timeline["summary"]["model"],
                    "scenario_id": SCENARIO_ID,
                    "timeline_run_classification": timeline["run_classification"],
                    "window_id": window,
                    "stage": stage,
                    "anchor_count": len(values),
                    "sum_timeline_counts": sum_count,
                    "sum_direct_expected_counts": sum_expected,
                    "pooled_timeline_to_direct_ratio": pooled_ratio,
                    "pooled_ratio_standard_error_replay_MC_only": pooled_ratio_se,
                    "pearson_chi2_vs_fixed_direct_expectations": pearson_fixed,
                    "pearson_df_fixed_expectations": len(values),
                    "pearson_dispersion_index_vs_fixed_direct_expectations": pearson_fixed / len(values),
                    "pearson_chi2_after_fitted_common_ratio": pearson_fitted,
                    "pearson_df_after_fitted_common_ratio": len(values) - 1,
                    "pearson_dispersion_index_after_fitted_common_ratio": pearson_fitted / (len(values) - 1),
                    "dispersion_scope": "five_independent_anchor_replay_counts_diagnostic_only",
                    "method_boundary": "direct_finite_template_uncertainty_not_included_in_dispersion_fit",
                }
            )
    return rows, dispersion_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=("a", "b"), required=True)
    parser.add_argument("--catalog-dir", type=Path, required=True)
    parser.add_argument("--timeline-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    catalog_dir = args.catalog_dir.resolve()
    timeline_dir = args.timeline_dir.resolve()
    output_dir = args.output_dir.resolve()
    require(catalog_dir.is_dir(), f"catalog directory does not exist: {catalog_dir}")
    require(timeline_dir.is_dir(), f"timeline directory does not exist: {timeline_dir}")
    require(not output_dir.exists(), f"refusing to overwrite existing output directory: {output_dir}")
    require(output_dir != catalog_dir and output_dir != timeline_dir, "output directory overlaps an input directory")

    assert_quantile_self_test()
    catalog = validate_catalog(catalog_dir, args.model)
    timeline = validate_timeline(timeline_dir, catalog, args.model)
    scale_path, scale_sha, scales = load_family_scales(timeline)
    family_rows = build_family_products(catalog, timeline, scales)
    anchor_rows, dispersion_rows = build_anchor_products(timeline)

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.staging-", dir=output_dir.parent))
    try:
        family_name = "day15_prompt_family_exact_intervals.csv"
        anchor_name = "five_anchor_replay_mc.csv"
        dispersion_name = "five_anchor_replay_dispersion.csv"
        summary_name = "summary.json"
        write_csv(staging / family_name, family_rows, list(family_rows[0]))
        write_csv(staging / anchor_name, anchor_rows, list(anchor_rows[0]))
        write_csv(staging / dispersion_name, dispersion_rows, list(dispersion_rows[0]))

        csv_hashes = {
            family_name: sha256_file(staging / family_name),
            anchor_name: sha256_file(staging / anchor_name),
            dispersion_name: sha256_file(staging / dispersion_name),
        }
        summary = {
            "schema": "m05_section4_uncertainty_products_v1",
            "schema_version": 1,
            "status": "PASS__SECTION4_UNCERTAINTY_PRODUCTS",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "model": args.model,
            "scenario_id": SCENARIO_ID,
            "scope": {
                "day15_prompt_families": list(FAMILIES),
                "window_id": FINAL_WINDOW,
                "stage": FINAL_STAGE,
                "mono511_catalog_component_disabled_before_poisson": True,
                "input_policy": "small JSON/CSV authorities only; integrated NPZ and SIM files not opened",
            },
            "input_binding": {
                "catalog_dir": str(catalog_dir),
                "catalog_metadata_file_sha256": catalog["hashes"],
                "integrated_catalog_metadata_fingerprint_sha256": catalog["metadata_fingerprint_sha256"],
                "timeline_dir": str(timeline_dir),
                "timeline_input_fingerprint_sha256": timeline["input_fingerprint_sha256"],
                "timeline_file_sha256": timeline["timeline_file_sha256"],
                "anchor_receipt_file_sha256": timeline["receipt_file_sha256"],
                "family_scales_csv": str(scale_path),
                "family_scales_csv_sha256": scale_sha,
                "script": str(SCRIPT),
                "script_sha256": sha256_file(SCRIPT),
            },
            "timeline_receipts": {
                "status": "PASS__FIVE_ANCHOR_RECEIPTS_COMPLETE",
                "anchor_time_bin_ids": list(ANCHOR_NODES),
                "exposure_s_per_anchor": timeline["exposure_s_per_anchor"],
                "signal_probe_trials_per_anchor": timeline["signal_probe_trials_per_anchor"],
                "run_classification": timeline["run_classification"],
                "formal_authority_config_match": timeline["formal_authority_config_match"],
                "expected_formal_config": FORMAL_CONFIG[args.model],
            },
            "day15_diagnostic_closure": timeline["day15_diagnostic_closure"],
            "methods": {
                "prompt_family_rate": "rate_hat = selected_raw * day15_family_scale / T_total",
                "unified_weight": "w = 1 / (T_old + T_new) = 1 / T_total",
                "garwood_central_95": "[0.5*chi2_ppf(0.025,2n), 0.5*chi2_ppf(0.975,2(n+1))], with lower=0 for n=0; multiply by day15 scale/T_total",
                "poisson_one_sided_95_upper": "0.5*chi2_ppf(0.95,2(n+1)); multiply by day15 scale/T_total",
                "bonferroni_familywise_95_upper": "per-family alpha=0.05/7 and upper=0.5*chi2_ppf(1-alpha,2(n+1)); union-bound simultaneous coverage >=95%",
                "quantile_engine": f"scipy {scipy.__version__} scipy.stats.chi2.ppf",
                "replay_MC_standard_error": "sqrt(timeline_count)/anchor_exposure; conditional on the finite catalog and response model",
                "anchor_dispersion": "Pearson diagnostics across the five independent anchor replay counts, shown both against fixed direct expectations and after fitting one pooled ratio",
            },
            "method_boundaries": {
                "exact_garwood_applies_to": "seven retained prompt families with one constant unified family weight and a common day15 family scale",
                "gamma_continuum": "excluded from Garwood because selected templates have non-equal event-level importance weights",
                "delayed": "excluded from Garwood because isotope/category contributions carry heterogeneous normalizations and time-dependent activity weights",
                "finite_template_vs_replay_MC": "reported in separate layers; this product does not claim a joint propagation or independence-based combined interval",
                "excluded_systematics": "geometry, detector response, atmospheric/source model, activation inventory, and cross-component systematics",
                "conditionality": "all prompt-family intervals are conditional on the selected response/veto/Compton chain and the retained day15 family scales",
            },
            "unresolved": [
                "joint propagation of finite-template uncertainty, common-axis replay MC, signal efficiency, and model/source/response systematics",
                "a valid non-equal-weight interval construction for gamma-continuum and delayed mixtures",
                "quality-model-B conditional sensitivity remains conditional until the joint uncertainty treatment is completed",
            ],
            "outputs": {
                family_name: {"rows": len(family_rows), "sha256": csv_hashes[family_name]},
                anchor_name: {"rows": len(anchor_rows), "sha256": csv_hashes[anchor_name]},
                dispersion_name: {"rows": len(dispersion_rows), "sha256": csv_hashes[dispersion_name]},
                summary_name: {"self_hash": "not_embedded"},
            },
            "no_overwrite_policy": "output directory must not exist; private sibling staging directory renamed only after closure",
        }
        write_json(staging / summary_name, summary)
        require(not output_dir.exists(), f"output directory appeared during staging: {output_dir}")
        os.rename(staging, output_dir)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise

    print(
        json.dumps(
            {
                "status": "PASS__SECTION4_UNCERTAINTY_PRODUCTS",
                "model": args.model,
                "timeline_run_classification": timeline["run_classification"],
                "output_dir": str(output_dir),
                "family_rows": len(family_rows),
                "anchor_rows": len(anchor_rows),
                "dispersion_rows": len(dispersion_rows),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
