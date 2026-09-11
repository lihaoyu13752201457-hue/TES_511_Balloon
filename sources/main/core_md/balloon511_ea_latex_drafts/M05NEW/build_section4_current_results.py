#!/usr/bin/env python3
"""Rebuild the current Section 4 statistics and affected figures.

Only compact, validated CSV/JSON summaries are read.  No event catalogue,
SIM, NPZ, or transport job is opened or launched.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


HERE = Path(__file__).resolve().parent
OUT = HERE / "figures" / "section4_current"
REPO_ROOT = Path("/home/ubuntu/TES_511_Balloon")
PACKAGE70 = (
    REPO_ROOT
    / "engineering/geometry_optimization_20260815"
    / "70_m05_sg3_sh3_prompt_statistics_integration_20260828"
)
SCENARIO_ID = "M05_SECTION4_SG3_SH3_BACKGROUND_SCOPE_20260828_V2"
TIMELINES = {
    "A": PACKAGE70 / "outputs/03_section4_timeline_a_authority_v2",
    "B": PACKAGE70 / "outputs/03_section4_timeline_b_authority_v2",
}
UNCERTAINTY_PRODUCTS = {
    "A": PACKAGE70 / "outputs/04_uncertainty_products_a_formal_v2p1_20260829",
    "B": PACKAGE70 / "outputs/04_uncertainty_products_b_formal_v2p1_20260829",
}
MODEL_ID = {"A": "a", "B": "b"}
FORMAL_CONFIG = {
    "A": {
        "exposure_s_per_anchor": 20_000.0,
        "signal_probe_trials_per_anchor": 2_000_000,
    },
    "B": {
        "exposure_s_per_anchor": 200_000.0,
        "signal_probe_trials_per_anchor": 2_000_000,
    },
}
GEOMETRY = (
    REPO_ROOT
    / "engineering/geometry_optimization_20260815"
    / "66_m05new_mxc_bpe_veto_review_20260821"
    / "data/cross_section_geometry_contract.csv"
)
EXACT_INTERVAL_CSV = HERE / "M05_SECTION4_PROMPT_FAMILY_EXACT_INTERVALS.csv"

W2 = "w2_510p58_511p42"
BROAD = "broad_480_550"
FINAL = "compton_trajectory_veto"
STAGES = (
    "pre_veto",
    "plastic_positron_veto",
    "bgo_active_scintillator_veto",
    "combined_active_veto",
    FINAL,
)
REPORT_STAGES = ("pre_veto", "combined_active_veto", FINAL)
REPORT_COMPONENTS = ("other", "gamma_continuum")
PROMPT_FAMILIES = ("alpha", "eminus", "eplus", "muminus", "muplus", "n", "p")
PHYSICAL_STREAM_FILTERS = {
    "prompt_seven": {"stream": "prompt", "component": "other"},
    "gamma_continuum": {"stream": "prompt", "component": "gamma_continuum"},
    "delayed": {"stream": "delayed", "component": "other"},
}
F0 = 1.0e-4

COLORS = {
    "ink": "#222222",
    "muted": "#6B7280",
    "grid": "#D8DEE8",
    "A": "#0072B2",
    "B": "#D55E00",
    "prompt": "#0072B2",
    "delayed": "#CC79A7",
    "prompt_seven": "#0072B2",
    "other": "#7A7A7A",
    "gamma_continuum": "#009E73",
    "accent": "#E69F00",
}
STAGE_LABEL = {
    "pre_veto": "Pre-veto",
    "plastic_positron_veto": "Plastic",
    "bgo_active_scintillator_veto": "BGO",
    "combined_active_veto": "Active veto",
    FINAL: "Compton final",
}
PHYSICAL_STREAM_LABEL = {
    "prompt_seven": "Seven prompt families",
    "gamma_continuum": "Gamma continuum",
    "delayed": "Delayed activation",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"JSON root is not an object: {path}")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def close(
    actual: float,
    expected: float,
    label: str,
    *,
    rtol: float = 5.0e-11,
    atol: float = 1.0e-12,
) -> None:
    if not math.isclose(actual, expected, rel_tol=rtol, abs_tol=atol):
        raise RuntimeError(f"{label}: {actual!r} != {expected!r}")


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(path)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def f(row: dict[str, str], key: str) -> float:
    return float(row[key])


def i(row: dict[str, str], key: str) -> int:
    return int(float(row[key]))


def effective_sample_size(rate: float, variance: float) -> float:
    return rate * rate / variance if variance > 0.0 else 0.0


def select(rows: Iterable[dict[str, str]], **filters: str) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if all(str(row.get(key)) == str(value) for key, value in filters.items())
    ]


def aggregate(
    rows: Iterable[dict[str, str]],
    *,
    components: tuple[str, ...] = REPORT_COMPONENTS,
    **filters: str,
) -> dict[str, float | int]:
    chosen = [
        row
        for row in rows
        if row.get("component") in components
        and all(str(row.get(key)) == str(value) for key, value in filters.items())
    ]
    rate = math.fsum(f(row, "sumw_cps") for row in chosen)
    variance = math.fsum(f(row, "sumw2_cps2") for row in chosen)
    raw = sum(i(row, "selected_raw") for row in chosen)
    return {
        "raw": raw,
        "rate_cps": rate,
        "variance_cps2": variance,
        "sigma_cps": math.sqrt(variance),
        "effective_sample_size": effective_sample_size(rate, variance),
    }


def component_aggregate(
    rows: Iterable[dict[str, str]], component: str, **filters: str
) -> dict[str, float | int]:
    return aggregate(rows, components=(component,), **filters)


def physical_stream_aggregate(
    rows: Iterable[dict[str, str]], physical_stream: str, **filters: str
) -> dict[str, float | int]:
    require(
        physical_stream in PHYSICAL_STREAM_FILTERS,
        f"unknown physical stream: {physical_stream}",
    )
    stream_filters = dict(PHYSICAL_STREAM_FILTERS[physical_stream])
    stream_filters.update(filters)
    component = stream_filters.pop("component")
    return aggregate(rows, components=(component,), **stream_filters)


def asimov_significance(signal: float, background: float) -> float:
    if signal <= 0.0:
        return 0.0
    if background <= 0.0:
        return math.sqrt(2.0 * signal)
    return math.sqrt(
        2.0
        * ((signal + background) * math.log1p(signal / background) - signal)
    )


def asimov_required_signal(background: float, target_z: float) -> float:
    if background <= 0.0:
        return 0.5 * target_z * target_z
    low = 0.0
    high = max(target_z * math.sqrt(background), 1.0)
    while asimov_significance(high, background) < target_z:
        high *= 2.0
    for _ in range(80):
        middle = 0.5 * (low + high)
        if asimov_significance(middle, background) < target_z:
            low = middle
        else:
            high = middle
    return high


def fmins(background: float, kernel: float) -> dict[str, float]:
    return {
        "F3_gaussian": 3.0 * math.sqrt(background) / kernel,
        "F5_gaussian": 5.0 * math.sqrt(background) / kernel,
        "F3_asimov": asimov_required_signal(background, 3.0) / kernel,
        "F5_asimov": asimov_required_signal(background, 5.0) / kernel,
    }


def crossing_day(days: list[float], values: list[float], target: float) -> float:
    require(len(days) == len(values) and len(days) >= 2, "threshold curve length mismatch")
    require(math.isfinite(target), "threshold target is not finite")
    for index, (day, value) in enumerate(zip(days, values)):
        require(
            math.isfinite(day) and math.isfinite(value),
            f"threshold curve contains a non-finite value at index {index}",
        )
        if index:
            require(days[index] > days[index - 1], "threshold day axis is not strictly increasing")
            require(
                values[index] >= values[index - 1],
                f"threshold curve is not nondecreasing at index {index}",
            )
    upcrossings = [
        left
        for left in range(len(days) - 1)
        if values[left] < target <= values[left + 1]
    ]
    require(
        len(upcrossings) == 1,
        f"threshold {target} requires exactly one upcrossing; observed {len(upcrossings)}",
    )
    left = upcrossings[0]
    y0, y1 = values[left], values[left + 1]
    require(y1 > y0, f"threshold {target} upcrossing has zero slope")
    fraction = (target - y0) / (y1 - y0)
    return days[left] + fraction * (days[left + 1] - days[left])


def configure() -> None:
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 7.5,
            "axes.titlesize": 8.5,
            "axes.labelsize": 7.5,
            "xtick.labelsize": 6.8,
            "ytick.labelsize": 6.8,
            "legend.fontsize": 6.4,
            "axes.linewidth": 0.7,
            "lines.linewidth": 1.35,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.facecolor": "white",
        }
    )


def tidy(ax: mpl.axes.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, color=COLORS["grid"], linewidth=0.55, alpha=0.85)
    ax.set_axisbelow(True)


def panel(ax: mpl.axes.Axes, label: str) -> None:
    ax.text(
        -0.16,
        1.08,
        label,
        transform=ax.transAxes,
        fontsize=9.0,
        fontweight="bold",
    )


def save(fig: mpl.figure.Figure, basename: str) -> None:
    fixed = {"Title": basename, "Creator": Path(__file__).name}
    fig.savefig(OUT / f"{basename}.pdf", bbox_inches="tight", metadata=fixed)
    fig.savefig(
        OUT / f"{basename}.png",
        dpi=360,
        bbox_inches="tight",
        metadata={"Software": Path(__file__).name},
    )
    plt.close(fig)


def validate_authority_inputs(
    model: str,
    timeline_dir: Path,
    uncertainty_dir: Path,
    timeline_summary: dict[str, Any],
    uncertainty_summary: dict[str, Any],
) -> None:
    model_id = MODEL_ID[model]
    require(
        timeline_summary.get("status") == "PASS__M05_SECTION4_COMMON_TIME_TIMELINE",
        f"model {model}: timeline status is not the completed V2 authority",
    )
    require(timeline_summary.get("model") == model_id, f"model {model}: timeline model mismatch")
    require(int(timeline_summary.get("schema_version", -1)) == 3, f"model {model}: timeline schema mismatch")
    scenario = timeline_summary.get("analysis_scenario", {})
    scenario_values = (
        scenario.get("scenario_id"),
        timeline_summary.get("run_parameters", {}).get("analysis_scenario_id"),
        timeline_summary.get("input_fingerprint", {}).get("parameters", {}).get("analysis_scenario_id"),
        timeline_summary.get("input_fingerprint", {}).get("analysis_scenario", {}).get("scenario_id"),
    )
    require(
        all(value == SCENARIO_ID for value in scenario_values),
        f"model {model}: timeline is not bound consistently to Section-4 scenario V2",
    )
    require(
        scenario.get("scope_applied_at") == "category_rate_matrix_before_poisson_arrivals",
        f"model {model}: background scope was not applied before the common axis",
    )
    require(
        scenario.get("enabled_components") == ["other", "gamma_continuum"],
        f"model {model}: enabled background-component scope mismatch",
    )
    require(
        scenario.get("disabled_components") == ["atm511"],
        f"model {model}: disabled background-component scope mismatch",
    )
    grouping = str(scenario.get("grouping_then_response_contract", ""))
    require(
        "Poisson arrivals" in grouping and "response -> veto -> Compton" in grouping,
        f"model {model}: common-axis response/veto order mismatch",
    )
    product_schema = timeline_summary.get("day15_product_schema", {})
    require(
        int(product_schema.get("schema_version", -1)) == 2
        and product_schema.get("closure_status") == "PASS__DAY15_PRODUCTS_ADDITIVE_CUTFLOW_CLOSED",
        f"model {model}: day-15 additive products are not closed",
    )
    input_fingerprint = timeline_summary.get("input_fingerprint", {})
    fingerprint_sha = str(timeline_summary.get("input_fingerprint_sha256", ""))
    require(
        canonical_sha256(input_fingerprint) == fingerprint_sha,
        f"model {model}: timeline input fingerprint SHA-256 does not close",
    )

    require(
        uncertainty_summary.get("status") == "PASS__SECTION4_UNCERTAINTY_PRODUCTS",
        f"model {model}: formal uncertainty status is not PASS",
    )
    require(
        uncertainty_summary.get("model") == model_id
        and uncertainty_summary.get("scenario_id") == SCENARIO_ID,
        f"model {model}: formal uncertainty model/scenario mismatch",
    )
    require(
        uncertainty_summary.get("day15_diagnostic_closure", {}).get("status")
        == "PASS__DAY15_DIAGNOSTIC_CSV_SHA_AND_ADDITIVE_CLOSURE",
        f"model {model}: day-15 diagnostic CSV closure is not PASS",
    )
    scope = uncertainty_summary.get("scope", {})
    require(
        scope.get("day15_prompt_families") == list(PROMPT_FAMILIES)
        and scope.get("window_id") == W2
        and scope.get("stage") == FINAL,
        f"model {model}: formal prompt-family scope mismatch",
    )
    require(
        scope.get("mono511_catalog_component_disabled_before_poisson") is True,
        f"model {model}: pre-common-axis component-scope gate is absent",
    )
    receipts = uncertainty_summary.get("timeline_receipts", {})
    expected_config = FORMAL_CONFIG[model]
    require(
        receipts.get("status") == "PASS__FIVE_ANCHOR_RECEIPTS_COMPLETE"
        and receipts.get("formal_authority_config_match") is True
        and receipts.get("run_classification") == "FORMAL_AUTHORITY_CONFIG_MATCH",
        f"model {model}: five-anchor formal classification mismatch",
    )
    require(
        receipts.get("anchor_time_bin_ids") == [0, 20, 40, 60, 80]
        and receipts.get("expected_formal_config") == expected_config,
        f"model {model}: formal anchor-node/config contract mismatch",
    )
    close(
        float(receipts.get("exposure_s_per_anchor")),
        float(expected_config["exposure_s_per_anchor"]),
        f"model {model}: formal exposure",
    )
    require(
        int(receipts.get("signal_probe_trials_per_anchor", -1))
        == int(expected_config["signal_probe_trials_per_anchor"]),
        f"model {model}: formal signal-probe count mismatch",
    )
    run_parameters = timeline_summary.get("run_parameters", {})
    close(
        float(run_parameters.get("exposure_s_per_anchor")),
        float(expected_config["exposure_s_per_anchor"]),
        f"model {model}: timeline exposure",
    )
    require(
        int(run_parameters.get("signal_probe_trials_per_anchor", -1))
        == int(expected_config["signal_probe_trials_per_anchor"]),
        f"model {model}: timeline signal-probe count mismatch",
    )

    binding = uncertainty_summary.get("input_binding", {})
    require(
        Path(str(binding.get("timeline_dir", ""))).resolve() == timeline_dir.resolve(),
        f"model {model}: formal uncertainty binds another timeline directory",
    )
    require(
        binding.get("timeline_input_fingerprint_sha256") == fingerprint_sha,
        f"model {model}: formal/timeline input fingerprint mismatch",
    )
    timeline_hashes = binding.get("timeline_file_sha256", {})
    required_hashes = {
        "summary.json",
        "direct_cutflow_day15.csv",
        "direct_hit_multiplicity_day15.csv",
        "direct_measured_energy_day15_0p25keV.csv",
        "anchor_timeline_rates.csv",
        "mission_timeline_81nodes.csv",
        "mission_transport_components.csv",
    }
    require(
        set(timeline_hashes) == required_hashes,
        f"model {model}: formal timeline file-hash coverage mismatch",
    )
    for filename, expected_sha in timeline_hashes.items():
        require(
            sha256_file(timeline_dir / filename) == expected_sha,
            f"model {model}: timeline hash mismatch for {filename}",
        )
    receipt_hashes = binding.get("anchor_receipt_file_sha256", {})
    expected_receipts = {f"anchor_{node:03d}.json" for node in (0, 20, 40, 60, 80)}
    require(
        set(receipt_hashes) == expected_receipts,
        f"model {model}: formal receipt-hash coverage mismatch",
    )
    for filename, expected_sha in receipt_hashes.items():
        require(
            sha256_file(timeline_dir / "receipts" / filename) == expected_sha,
            f"model {model}: anchor receipt hash mismatch for {filename}",
        )
    interval_contract = uncertainty_summary.get("outputs", {}).get(
        "day15_prompt_family_exact_intervals.csv", {}
    )
    interval_path = uncertainty_dir / "day15_prompt_family_exact_intervals.csv"
    require(
        int(interval_contract.get("rows", -1)) == len(PROMPT_FAMILIES)
        and sha256_file(interval_path) == interval_contract.get("sha256"),
        f"model {model}: exact-interval CSV row/hash contract mismatch",
    )


def normalize_exact_intervals(
    model: str,
    rows: list[dict[str, str]],
    cutflow: list[dict[str, str]],
) -> list[dict[str, Any]]:
    model_id = MODEL_ID[model]
    require(len(rows) == len(PROMPT_FAMILIES), f"model {model}: exact-interval row count mismatch")
    by_family: dict[str, dict[str, str]] = {}
    for row in rows:
        family = row.get("family", "")
        require(family in PROMPT_FAMILIES and family not in by_family, f"model {model}: invalid/duplicate exact family {family!r}")
        require(
            row.get("model") == model_id
            and row.get("scenario_id") == SCENARIO_ID
            and i(row, "time_bin_id") == 60
            and math.isclose(f(row, "day_mid"), 15.0)
            and row.get("stream") == "prompt"
            and row.get("component") == "other"
            and row.get("window_id") == W2
            and row.get("stage") == FINAL,
            f"model {model}: exact-interval scope mismatch for {family}",
        )
        by_family[family] = row
    require(set(by_family) == set(PROMPT_FAMILIES), f"model {model}: exact-family coverage mismatch")

    selected_cutflow: dict[str, dict[str, str]] = {}
    for row in cutflow:
        if (
            i(row, "time_bin_id") == 60
            and row.get("stream") == "prompt"
            and row.get("component") == "other"
            and row.get("window_id") == W2
            and row.get("stage") == FINAL
            and row.get("family") in PROMPT_FAMILIES
        ):
            family = str(row["family"])
            require(family not in selected_cutflow, f"model {model}: duplicate final prompt cutflow row for {family}")
            selected_cutflow[family] = row
    require(set(selected_cutflow) == set(PROMPT_FAMILIES), f"model {model}: final prompt cutflow family coverage mismatch")

    normalized: list[dict[str, Any]] = []
    for family in PROMPT_FAMILIES:
        row = by_family[family]
        selected = selected_cutflow[family]
        n = i(row, "selected_raw")
        old_t = f(row, "T_old_s")
        new_t = f(row, "T_new_s")
        total_t = f(row, "T_total_s")
        weight = f(row, "unified_weight_cps")
        scale = f(row, "day15_family_scale")
        scaled_weight = f(row, "scaled_selected_event_weight_cps")
        rate = f(row, "rate_hat_cps")
        require(old_t > 0.0 and new_t >= 0.0 and total_t > 0.0, f"model {model}: invalid exposure for {family}")
        close(total_t, old_t + new_t, f"model {model} {family}: T_total=T_old+T_new")
        close(weight, 1.0 / total_t, f"model {model} {family}: unified weight")
        close(scaled_weight, weight * scale, f"model {model} {family}: scaled weight")
        close(rate, n * scaled_weight, f"model {model} {family}: exact rate")
        require(i(selected, "selected_raw") == n, f"model {model} {family}: exact/cutflow raw mismatch")
        close(f(selected, "sumw_cps"), rate, f"model {model} {family}: exact/cutflow rate")
        close(f(selected, "sumw2_cps2"), n * scaled_weight * scaled_weight, f"model {model} {family}: exact/cutflow variance")
        low = f(row, "garwood_central_lower_rate_cps")
        high = f(row, "garwood_central_upper_rate_cps")
        upper = f(row, "one_sided_upper_rate_cps")
        simultaneous_upper = f(row, "bonferroni_familywise_upper_rate_cps")
        require(
            0.0 <= low <= rate <= high <= simultaneous_upper
            and rate <= upper <= simultaneous_upper,
            f"model {model} {family}: malformed exact interval",
        )
        expected_policy = "exact_nonzero_upper_limits" if n == 0 else "exact_count_interval"
        require(row.get("zero_count_uncertainty_policy") == expected_policy, f"model {model} {family}: zero-count policy mismatch")
        normalized.append(
            {
                "model": model,
                "physical_stream": "prompt_seven",
                "family": family,
                "selected_raw": n,
                "T_old_s": old_t,
                "T_new_s": new_t,
                "T_total_s": total_t,
                "unified_weight_cps": weight,
                "day15_family_scale": scale,
                "rate_hat_cps": rate,
                "garwood_central_confidence_level": f(row, "garwood_central_confidence_level"),
                "garwood_central_lower_rate_cps": low,
                "garwood_central_upper_rate_cps": high,
                "one_sided_confidence_level": f(row, "one_sided_confidence_level"),
                "one_sided_upper_rate_cps": upper,
                "bonferroni_familywise_confidence_at_least": f(row, "bonferroni_familywise_confidence_at_least"),
                "bonferroni_familywise_upper_rate_cps": simultaneous_upper,
                "zero_count_uncertainty_policy": expected_policy,
            }
        )
    return normalized


def model_data(model: str) -> dict[str, Any]:
    timeline_dir = TIMELINES[model]
    uncertainty_dir = UNCERTAINTY_PRODUCTS[model]
    require(timeline_dir.is_dir(), f"model {model}: formal V2 timeline directory is missing")
    require(uncertainty_dir.is_dir(), f"model {model}: formal V2 uncertainty directory is missing")
    timeline_summary_path = timeline_dir / "summary.json"
    uncertainty_summary_path = uncertainty_dir / "summary.json"
    timeline_summary = read_json(timeline_summary_path)
    uncertainty_summary = read_json(uncertainty_summary_path)
    validate_authority_inputs(
        model,
        timeline_dir,
        uncertainty_dir,
        timeline_summary,
        uncertainty_summary,
    )
    cutflow_path = timeline_dir / "direct_cutflow_day15.csv"
    multiplicity_path = timeline_dir / "direct_hit_multiplicity_day15.csv"
    mission_path = timeline_dir / "mission_timeline_81nodes.csv"
    anchor_path = timeline_dir / "anchor_timeline_rates.csv"
    mission_components_path = timeline_dir / "mission_transport_components.csv"
    measured_energy_path = timeline_dir / "direct_measured_energy_day15_0p25keV.csv"
    interval_path = uncertainty_dir / "day15_prompt_family_exact_intervals.csv"
    cutflow = read_csv(cutflow_path)
    mission = read_csv(mission_path)
    mission.sort(key=lambda row: i(row, "time_bin_id"))
    intervals = normalize_exact_intervals(model, read_csv(interval_path), cutflow)
    return {
        "cutflow": cutflow,
        "multiplicity": read_csv(multiplicity_path),
        "mission": mission,
        "anchor": read_csv(anchor_path),
        "summary": timeline_summary,
        "uncertainty_summary": uncertainty_summary,
        "prompt_family_exact_intervals": intervals,
        "input_paths": {
            "timeline_summary": timeline_summary_path,
            "cutflow": cutflow_path,
            "multiplicity": multiplicity_path,
            "anchors": anchor_path,
            "mission": mission_path,
            "mission_transport_components": mission_components_path,
            "measured_energy_diagnostic": measured_energy_path,
            "uncertainty_summary": uncertainty_summary_path,
            "prompt_family_exact_intervals": interval_path,
        },
    }


def mission_arrays(data: dict[str, Any]) -> dict[str, list[float]]:
    rows = data["mission"]
    require(len(rows) == 81, "mission timeline must contain exactly 81 nodes")
    require([i(row, "time_bin_id") for row in rows] == list(range(81)), "mission node IDs are not 0..80")
    for index, row in enumerate(rows):
        close(f(row, "day_mid"), index / 4.0, f"mission node {index}: day-axis closure")
        close(
            f(row, "cumulative_background_counts"),
            f(row, "cumulative_other_background_counts")
            + f(row, "cumulative_gamma_continuum_background_counts"),
            f"mission node {index}: cumulative total/component closure",
            atol=1.0e-8,
        )
        close(
            f(row, "cumulative_transport_sum_W_i2_counts2"),
            f(row, "cumulative_other_sum_W_i2_counts2")
            + f(row, "cumulative_gamma_continuum_sum_W_i2_counts2"),
            f"mission node {index}: cumulative variance/component closure",
            atol=1.0e-6,
        )
        close(
            f(row, "direct_W2_final_no_coincidence_cps"),
            f(row, "direct_other_cps") + f(row, "direct_gamma_continuum_cps"),
            f"mission node {index}: direct total/component closure",
        )
        close(
            f(row, "direct_sum_W_i2_cps2"),
            f(row, "direct_other_sum_W_i2_cps2")
            + f(row, "direct_gamma_continuum_sum_W_i2_cps2"),
            f"mission node {index}: direct variance/component closure",
        )
        close(
            f(row, "mature_background_W2_final_cps"),
            f(row, "direct_W2_final_no_coincidence_cps")
            * f(row, "interpolated_background_timeline_ratio"),
            f"mission node {index}: direct/timeline-ratio closure",
        )

    days = [f(row, "day_mid") for row in rows]
    background = [f(row, "cumulative_background_counts") for row in rows]
    variance = [f(row, "cumulative_transport_sum_W_i2_counts2") for row in rows]
    kernel = [f(row, "cumulative_signal_counts_per_unit_flux") for row in rows]
    signal = [F0 * value for value in kernel]
    z_gaussian = [
        value / math.sqrt(bg) if bg > 0.0 else 0.0
        for value, bg in zip(signal, background)
    ]
    z_asimov = [
        asimov_significance(value, bg) if bg > 0.0 else 0.0
        for value, bg in zip(signal, background)
    ]
    F3_gaussian = [
        3.0 * math.sqrt(bg) / k if k > 0.0 else math.nan
        for bg, k in zip(background, kernel)
    ]
    F3_asimov = [
        asimov_required_signal(bg, 3.0) / k if k > 0.0 else math.nan
        for bg, k in zip(background, kernel)
    ]
    direct = [f(row, "direct_W2_final_no_coincidence_cps") for row in rows]
    ratio = [f(row, "interpolated_background_timeline_ratio") for row in rows]
    common = [f(row, "mature_background_W2_final_cps") for row in rows]
    endpoint = data["summary"].get("mission_final_20day", {})
    for key in (
        "cumulative_background_counts",
        "cumulative_transport_sum_W_i2_counts2",
        "cumulative_signal_counts_per_unit_flux",
        "direct_W2_final_no_coincidence_cps",
    ):
        close(f(rows[-1], key), float(endpoint[key]), f"mission endpoint summary closure: {key}", atol=1.0e-8)
    return {
        "days": days,
        "background": background,
        "variance": variance,
        "kernel": kernel,
        "signal": signal,
        "z_gaussian": z_gaussian,
        "z_asimov": z_asimov,
        "F3_gaussian": F3_gaussian,
        "F3_asimov": F3_asimov,
        "direct": direct,
        "ratio": ratio,
        "common": common,
    }


def propagated_uncertainty(
    data: dict[str, Any], arrays: dict[str, list[float]]
) -> dict[str, Any]:
    authority = data["summary"].get("statistical_uncertainty", {})
    fmin_authority = authority.get("Fmin", {})
    mapping = {
        "F3_gaussian": "Fmin_3sigma_gaussian_ph_cm2_s",
        "F3_asimov": "Fmin_3sigma_poisson_asimov_ph_cm2_s",
        "F5_gaussian": "Fmin_5sigma_gaussian_ph_cm2_s",
        "F5_asimov": "Fmin_5sigma_poisson_asimov_ph_cm2_s",
    }
    point = fmins(arrays["background"][-1], arrays["kernel"][-1])
    results: dict[str, Any] = {
        "scope": "local_propagated_standard_errors_not_joint_uncertainty",
        "background_transport_sigma_counts": float(authority["background_transport_MC_sigma_counts"]),
        "background_timeline_sigma_counts": float(authority["background_timeline_replay_sigma_counts"]),
        "background_combined_sigma_counts": float(authority["background_combined_sigma_counts"]),
        "background_combined_relative_sigma": float(authority["background_combined_relative_sigma"]),
        "signal_combined_relative_sigma": float(authority["signal_combined_relative_sigma"]),
    }
    close(
        results["background_transport_sigma_counts"],
        math.sqrt(arrays["variance"][-1]),
        "transport uncertainty/mission variance closure",
        atol=1.0e-8,
    )
    for output_key, authority_key in mapping.items():
        item = fmin_authority.get(authority_key, {})
        require(set(item) >= {"value", "standard_error", "relative_standard_error"}, f"missing formal Fmin uncertainty: {authority_key}")
        close(float(item["value"]), point[output_key], f"formal/recomputed {output_key}")
        results[output_key] = {
            "value": float(item["value"]),
            "standard_error": float(item["standard_error"]),
            "relative_standard_error": float(item["relative_standard_error"]),
        }
    return results


def mission_thresholds(arrays: dict[str, list[float]]) -> dict[str, float]:
    return {
        "T3_gaussian": crossing_day(arrays["days"], arrays["z_gaussian"], 3.0),
        "T3_asimov": crossing_day(arrays["days"], arrays["z_asimov"], 3.0),
        "T5_gaussian": crossing_day(arrays["days"], arrays["z_gaussian"], 5.0),
        "T5_asimov": crossing_day(arrays["days"], arrays["z_asimov"], 5.0),
    }


def build_geometry_background(data_b: dict[str, Any]) -> None:
    fig, axes = plt.subplots(
        1,
        3,
        figsize=(7.45, 3.35),
        constrained_layout=True,
        gridspec_kw={"width_ratios": [1.3, 1.12, 0.92]},
    )
    fig.set_constrained_layout_pads(
        w_pad=0.035, h_pad=0.05, wspace=0.07, hspace=0.08
    )
    geometry = select(read_csv(GEOMETRY), geometry="SH3_OptV3")
    ax = axes[0]
    ax.add_patch(
        Rectangle(
            (-45.75, -13.85),
            30.75,
            22.10,
            facecolor="#EEF1F3",
            edgecolor=COLORS["ink"],
            lw=1.0,
            hatch="..",
            label="Welded saddle/chimney envelope",
        )
    )
    for row in geometry:
        x0, x1 = f(row, "x_min_cm"), f(row, "x_max_cm")
        z0, z1 = f(row, "z_min_cm"), f(row, "z_max_cm")
        if row["kind"] == "cold_plate":
            ax.add_patch(
                Rectangle(
                    (x0, z0),
                    x1 - x0,
                    z1 - z0,
                    facecolor="#C67C4E",
                    edgecolor="#7D462A",
                    lw=0.7,
                    hatch="//",
                )
            )
        elif row["kind"] == "TES_active_layer":
            ax.add_patch(
                Rectangle(
                    (x0, z0),
                    x1 - x0,
                    z1 - z0,
                    facecolor=COLORS["accent"],
                    edgecolor=COLORS["ink"],
                    lw=0.6,
                )
            )
    ax.add_patch(
        Rectangle(
            (-41.7, -7.0),
            13.0,
            8.4,
            fill=False,
            edgecolor=COLORS["A"],
            lw=1.1,
            ls="--",
            label="TES/BGO neighborhood",
        )
    )
    ax.annotate(
        "six TES layers\nin lateral chimney",
        xy=(-35.5, -2.8),
        xytext=(-10.0, 13.0),
        fontsize=6.4,
        ha="center",
        arrowprops={"arrowstyle": "->", "lw": 0.8},
    )
    ax.set(
        xlim=(-48, 20),
        ylim=(-15, 34),
        xlabel="Cross-section x (cm)",
        ylabel="z (cm)",
        title="Mass model B detector--shield section",
    )
    ax.set_aspect("equal", adjustable="box")
    ax.legend(frameon=False, fontsize=6.1, loc="upper left")
    ax.text(
        0.02,
        0.02,
        "Geometry schematic; not a dose map",
        transform=ax.transAxes,
        fontsize=5.6,
        color=COLORS["muted"],
        bbox={
            "facecolor": "white",
            "edgecolor": "none",
            "alpha": 0.82,
            "pad": 0.5,
        },
    )

    display_stages = (
        "pre_veto",
        "bgo_active_scintillator_veto",
        FINAL,
    )
    positions = list(range(len(display_stages)))
    for physical_stream, marker, linestyle in (
        ("prompt_seven", "o", "-"),
        ("gamma_continuum", "^", "-."),
        ("delayed", "s", "--"),
    ):
        values, errors = [], []
        for stage in display_stages:
            value = physical_stream_aggregate(
                data_b["cutflow"],
                physical_stream,
                window_id=W2,
                stage=stage,
            )
            values.append(float(value["rate_cps"]))
            errors.append(float(value["sigma_cps"]))
        axes[1].errorbar(
            positions,
            values,
            yerr=errors,
            color=COLORS[physical_stream],
            marker=marker,
            ls=linestyle,
            ms=3,
            capsize=2,
            label=PHYSICAL_STREAM_LABEL[physical_stream],
        )
    axes[1].set_xticks(
        positions,
        [STAGE_LABEL[stage] for stage in display_stages],
        rotation=30,
        ha="right",
    )
    axes[1].set(
        ylabel="Day-15 W2 rate (s$^{-1}$)",
        title="Model-B physical-stream cutflow",
    )
    axes[1].tick_params(axis="x", labelsize=6.3)
    axes[1].set_yscale("log")
    axes[1].legend(
        frameon=False,
        fontsize=5.8,
        handlelength=2.4,
        loc="upper right",
    )

    component_values = {
        physical_stream: float(
            physical_stream_aggregate(
                data_b["cutflow"],
                physical_stream,
                window_id=W2,
                stage=FINAL,
            )["rate_cps"]
        )
        for physical_stream in PHYSICAL_STREAM_FILTERS
    }
    total = math.fsum(component_values.values())
    order = sorted(
        PHYSICAL_STREAM_FILTERS,
        key=lambda physical_stream: (
            -component_values[physical_stream],
            physical_stream,
        ),
    )
    fractions = [component_values[physical_stream] / total for physical_stream in order]
    axes[2].barh(
        range(len(order)),
        fractions,
        color=[COLORS[physical_stream] for physical_stream in order],
        hatch=["..", "//", "xx"],
        edgecolor="white",
    )
    axes[2].set_yticks(
        range(len(order)),
        [PHYSICAL_STREAM_LABEL[physical_stream] for physical_stream in order],
    )
    axes[2].invert_yaxis()
    for index, fraction in enumerate(fractions):
        axes[2].text(
            fraction + 0.012,
            index,
            f"{100 * fraction:.1f}%",
            va="center",
            fontsize=7,
        )
    axes[2].set_xlim(0, max(fractions) * 1.28)
    axes[2].set(
        xlabel="Fraction of W2 final",
        title="Model-B final composition",
    )
    axes[2].tick_params(axis="y", labelsize=6.6)
    for label, axis in zip(("(a)", "(b)", "(c)"), axes):
        axis.text(
            -0.18,
            1.15,
            label,
            transform=axis.transAxes,
            fontsize=9.0,
            fontweight="bold",
        )
        tidy(axis)
    save(fig, "fig09_mass_model_b_geometry_background")


def multiplicity_series(
    rows: list[dict[str, str]], window: str
) -> tuple[list[int], list[float], list[float], list[int]]:
    chosen = [
        row
        for row in rows
        if row["window_id"] == window
        and row["stage"] == FINAL
        and row["component"] in REPORT_COMPONENTS
    ]
    grouped: dict[int, list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0])
    for row in chosen:
        multiplicity = i(row, "hit_multiplicity")
        grouped[multiplicity][0] += f(row, "sumw_cps")
        grouped[multiplicity][1] += f(row, "sumw2_cps2")
        grouped[multiplicity][2] += i(row, "selected_raw")
    x = sorted(grouped)
    return (
        x,
        [grouped[value][0] for value in x],
        [math.sqrt(grouped[value][1]) for value in x],
        [round(grouped[value][2]) for value in x],
    )


def build_multiplicity(data: dict[str, dict[str, Any]]) -> dict[str, Any]:
    fig, axes = plt.subplots(
        1, 2, figsize=(7.15, 3.0), constrained_layout=True, sharey=True
    )
    report: dict[str, Any] = {}
    for ax, window, label, title in zip(
        axes,
        (BROAD, W2),
        ("(a)", "(b)"),
        ("Broad window: 480--550 keV", "W2: 510.58--511.42 keV"),
    ):
        report[window] = {}
        for model, linestyle, marker in (
            ("A", "-", "o"),
            ("B", "--", "s"),
        ):
            x, y, sigma, raw = multiplicity_series(
                data[model]["multiplicity"], window
            )
            positive = [value if value > 0.0 else math.nan for value in y]
            ax.errorbar(
                x,
                positive,
                yerr=sigma,
                color=COLORS[model],
                ls=linestyle,
                marker=marker,
                ms=3.2,
                capsize=2,
                label=f"Model {model}",
            )
            nonzero = [value for value, rate in zip(x, y) if rate > 0.0]
            raw_total = sum(raw)
            rate_total = math.fsum(y)
            five_index = x.index(5) if 5 in x else None
            single_index = x.index(1) if 1 in x else None
            multi_indices = [index for index, value in enumerate(x) if value >= 2]
            report[window][model] = {
                "selected_raw": raw_total,
                "rate_cps": rate_total,
                "highest_nonzero_multiplicity": max(nonzero) if nonzero else 0,
                "single_pixel": {
                    "selected_raw": raw[single_index]
                    if single_index is not None
                    else 0,
                    "rate_cps": y[single_index]
                    if single_index is not None
                    else 0.0,
                    "sigma_cps": sigma[single_index]
                    if single_index is not None
                    else 0.0,
                },
                "multi_pixel": {
                    "selected_raw": sum(raw[index] for index in multi_indices),
                    "rate_cps": math.fsum(y[index] for index in multi_indices),
                    "sigma_cps": math.sqrt(
                        math.fsum(sigma[index] ** 2 for index in multi_indices)
                    ),
                },
                "five_hit_raw": raw[five_index] if five_index is not None else 0,
                "five_hit_rate_cps": y[five_index]
                if five_index is not None
                else 0.0,
                "five_hit_fraction": (
                    y[five_index] / rate_total
                    if five_index is not None and rate_total > 0.0
                    else 0.0
                ),
                "five_hit_fraction_definition": "five-hit weighted rate divided by total final weighted rate in this window",
            }
        ax.set_yscale("log")
        ax.set(xlabel="TES hit multiplicity", title=title)
        ax.set_xticks(range(1, 7))
        ax.set_xlim(0.7, 6.3)
        panel(ax, label)
        tidy(ax)
    axes[0].set_ylabel(r"Day-15 final rate (s$^{-1}$)")
    axes[0].legend(frameon=False)
    save(fig, "fig07_hit_multiplicity")
    return report


def build_anchor_figure(
    data: dict[str, dict[str, Any]],
    arrays: dict[str, dict[str, list[float]]],
) -> None:
    fig, axes = plt.subplots(
        1, 2, figsize=(7.15, 2.9), constrained_layout=True
    )
    for model, linestyle, marker in (
        ("A", "-", "o"),
        ("B", "--", "s"),
    ):
        values = arrays[model]
        days = values["days"]
        axes[0].plot(
            days,
            values["direct"],
            color=COLORS[model],
            linestyle=":",
            linewidth=1.0,
            label=f"{model} direct",
        )
        axes[0].plot(
            days,
            values["common"],
            color=COLORS[model],
            linestyle=linestyle,
            label=f"{model} timing-corrected",
        )
        anchors = select(data[model]["anchor"], window_id=W2, stage=FINAL)
        anchors.sort(key=lambda row: i(row, "time_bin_id"))
        anchor_days = [f(row, "day_mid") for row in anchors]
        anchor_indices = [i(row, "time_bin_id") for row in anchors]
        ratio = [f(row, "timeline_to_direct_ratio") for row in anchors]
        ratio_error = [
            f(row, "timeline_rate_standard_error_cps")
            / f(row, "direct_no_coincidence_rate_cps")
            for row in anchors
        ]
        survival = [f(row, "signal_accidental_survival") for row in anchors]
        survival_error = [
            f(row, "signal_survival_standard_error") for row in anchors
        ]
        direct_anchor = [values["direct"][index] for index in anchor_indices]
        common_anchor = [
            values["common"][index] for index in anchor_indices
        ]
        axes[0].errorbar(
            anchor_days,
            common_anchor,
            yerr=[
                direct_rate * error
                for direct_rate, error in zip(direct_anchor, ratio_error)
            ],
            fmt=marker,
            ms=3.2,
            color=COLORS[model],
            markerfacecolor="white",
            capsize=2.0,
            zorder=5,
        )
        axes[1].plot(
            days,
            values["ratio"],
            color=COLORS[model],
            linestyle=linestyle,
            label=rf"{model} $\rho$",
        )
        survival_curve = [
            f(row, "conditional_signal_accidental_survival")
            for row in data[model]["mission"]
        ]
        axes[1].plot(
            days,
            survival_curve,
            color=COLORS[model],
            linestyle=":",
            label=rf"{model} $\eta$",
        )
        axes[1].errorbar(
            anchor_days,
            ratio,
            yerr=ratio_error,
            fmt=marker,
            ms=3.0,
            color=COLORS[model],
            markerfacecolor="white",
            capsize=2.0,
            zorder=5,
        )
        axes[1].errorbar(
            anchor_days,
            survival,
            yerr=survival_error,
            fmt="^" if model == "A" else "v",
            ms=3.0,
            color=COLORS[model],
            markerfacecolor="white",
            capsize=2.0,
            zorder=5,
        )
    axes[0].set(
        xlabel="Mission day",
        ylabel=r"Final-window rate (s$^{-1}$)",
        title="81-node rate curves and five anchors",
    )
    axes[0].set_xlim(0, 20)
    axes[0].legend(frameon=False, ncol=1, loc="center right")
    axes[1].axhline(
        1.0,
        color=COLORS["muted"],
        linestyle=(0, (3, 2)),
        linewidth=0.8,
    )
    axes[1].set(
        xlabel="Mission day",
        ylabel="Dimensionless factor",
        title="Fixed-anchor timing factors",
    )
    axes[1].set_xlim(0, 20)
    axes[1].set_ylim(0.82, 1.06)
    axes[1].legend(frameon=False, ncol=2, loc="lower center")
    for label, ax in zip(("(a)", "(b)"), axes):
        panel(ax, label)
        tidy(ax)
    save(fig, "fig04_common_time_normalization")


def build_mission_figure(
    arrays: dict[str, dict[str, list[float]]],
    uncertainties: dict[str, dict[str, Any]],
) -> None:
    fig, axes = plt.subplots(
        1, 2, figsize=(7.15, 3.05), constrained_layout=True
    )
    for model, linestyle, marker in (
        ("A", "-", "o"),
        ("B", "--", "s"),
    ):
        values = arrays[model]
        axes[0].plot(
            values["days"],
            values["z_gaussian"],
            color=COLORS[model],
            ls=linestyle,
            marker=marker,
            markevery=10,
            ms=3,
            label=f"Model {model}",
        )
        axes[1].plot(
            values["days"],
            values["F3_gaussian"],
            color=COLORS[model],
            ls=linestyle,
            marker=marker,
            markevery=10,
            ms=3,
            label=f"Model {model} Gaussian",
        )
        axes[1].plot(
            values["days"],
            values["F3_asimov"],
            color=COLORS[model],
            ls=":" if model == "A" else "-.",
            marker="^" if model == "A" else "v",
            markevery=10,
            ms=3,
            label=f"Model {model} Asimov",
        )
        endpoint = uncertainties[model]["F3_gaussian"]
        axes[1].errorbar(
            [values["days"][-1]],
            [endpoint["value"]],
            yerr=[endpoint["standard_error"]],
            fmt=marker,
            color=COLORS[model],
            capsize=3,
            ms=4,
        )
    for threshold, label in ((3.0, "3σ"), (5.0, "5σ")):
        axes[0].axhline(
            threshold,
            color=COLORS["muted"],
            linewidth=0.8,
            linestyle="--" if threshold == 3 else ":",
        )
        axes[0].text(
            20.05,
            threshold,
            label,
            va="center",
            fontsize=6.8,
            color=COLORS["muted"],
        )
    axes[0].set(
        xlabel="Mission day",
        ylabel=r"Gaussian significance $S/\sqrt{B}$",
        title=r"81-node fold at $F_0=10^{-4}$ ph cm$^{-2}$ s$^{-1}$",
    )
    axes[0].set_xlim(0.0, 20.8)
    axes[0].legend(frameon=False)
    axes[1].set_yscale("log")
    axes[1].set(
        xlabel="Mission day",
        ylabel=r"3σ $F_{\min}$ (ph cm$^{-2}$ s$^{-1}$)",
        title="Gaussian and Poisson-Asimov thresholds",
    )
    axes[1].legend(frameon=False, ncol=2, fontsize=6.5)
    axes[1].text(
        0.02,
        0.02,
        "Endpoint bars: local propagated 1σ (not joint); curves are point estimates",
        transform=axes[1].transAxes,
        fontsize=6.3,
        color=COLORS["muted"],
    )
    for label, ax in zip(("(a)", "(b)"), axes):
        panel(ax, label)
        tidy(ax)
    save(fig, "fig10_mission_performance")


def build_report(
    data: dict[str, dict[str, Any]],
    arrays: dict[str, dict[str, list[float]]],
    uncertainties: dict[str, dict[str, Any]],
    multiplicity: dict[str, Any],
) -> dict[str, Any]:
    models: dict[str, Any] = {}
    for model in ("A", "B"):
        cutflow = data[model]["cutflow"]
        stages = {
            stage: aggregate(cutflow, window_id=W2, stage=stage)
            for stage in REPORT_STAGES
        }
        physical_stream_cutflow = {
            physical_stream: {
                stage: physical_stream_aggregate(
                    cutflow,
                    physical_stream,
                    window_id=W2,
                    stage=stage,
                )
                for stage in REPORT_STAGES
            }
            for physical_stream in PHYSICAL_STREAM_FILTERS
        }
        for stage in REPORT_STAGES:
            branch_values = [
                physical_stream_cutflow[physical_stream][stage]
                for physical_stream in PHYSICAL_STREAM_FILTERS
            ]
            require(
                sum(int(value["raw"]) for value in branch_values)
                == int(stages[stage]["raw"]),
                f"model {model} {stage}: physical-stream raw closure failed",
            )
            close(
                math.fsum(float(value["rate_cps"]) for value in branch_values),
                float(stages[stage]["rate_cps"]),
                f"model {model} {stage}: physical-stream rate closure",
            )
            close(
                math.fsum(float(value["variance_cps2"]) for value in branch_values),
                float(stages[stage]["variance_cps2"]),
                f"model {model} {stage}: physical-stream variance closure",
            )
        final_components = {
            physical_stream: dict(physical_stream_cutflow[physical_stream][FINAL])
            for physical_stream in PHYSICAL_STREAM_FILTERS
        }
        final_rate = float(stages[FINAL]["rate_cps"])
        for value in final_components.values():
            value["fraction_of_final"] = float(value["rate_cps"]) / final_rate
        values = arrays[model]
        endpoint_fmins = fmins(values["background"][-1], values["kernel"][-1])
        day15_rows = select(data[model]["mission"], time_bin_id="60")
        require(len(day15_rows) == 1, f"model {model}: mission day-15 row is not unique")
        models[model] = {
            "day15_cutflow": stages,
            "day15_physical_stream_cutflow": physical_stream_cutflow,
            "day15_final_physical_streams": final_components,
            "day15_prompt_family_exact_intervals": data[model][
                "prompt_family_exact_intervals"
            ],
            "day15_signal_rate_F0_cps": F0
            * f(day15_rows[0], "conditional_signal_kernel_cm2"),
            "signal_effective_area_cm2": float(
                data[model]["summary"]["signal_proxy"]["aeff_cm2"]
            ),
            "signal_effective_area_sigma_cm2": float(
                data[model]["summary"]["signal_proxy"]["aeff_sigma_cm2"]
            ),
            "mission_20d": {
                "background_counts": values["background"][-1],
                "background_variance_counts2": values["variance"][-1],
                "signal_counts_F0": values["signal"][-1],
                "signal_kernel_counts_per_unit_flux": values["kernel"][-1],
                "Z_gaussian": values["z_gaussian"][-1],
                "Z_asimov": values["z_asimov"][-1],
                "threshold_days": mission_thresholds(values),
                **endpoint_fmins,
            },
            "local_propagated_statistical_uncertainty": uncertainties[model],
        }
    a = models["A"]
    b = models["B"]
    comparisons = {
        "day15_background_B_over_A": float(
            b["day15_cutflow"][FINAL]["rate_cps"]
        )
        / float(a["day15_cutflow"][FINAL]["rate_cps"]),
        "mission20_background_B_over_A": b["mission_20d"]["background_counts"]
        / a["mission_20d"]["background_counts"],
        "mission20_signal_kernel_B_over_A": b["mission_20d"][
            "signal_kernel_counts_per_unit_flux"
        ]
        / a["mission_20d"]["signal_kernel_counts_per_unit_flux"],
        "F3_gaussian_A_over_B": a["mission_20d"]["F3_gaussian"]
        / b["mission_20d"]["F3_gaussian"],
        "F3_gaussian_B_over_A": b["mission_20d"]["F3_gaussian"]
        / a["mission_20d"]["F3_gaussian"],
        "Aeff_B_over_A": b["signal_effective_area_cm2"]
        / a["signal_effective_area_cm2"],
    }
    inputs: dict[str, Any] = {}
    authority_contract: dict[str, Any] = {}
    for model in ("A", "B"):
        inputs[model] = {
            key: {"path": str(path), "sha256": sha256_file(path)}
            for key, path in data[model]["input_paths"].items()
        }
        timeline_summary = data[model]["summary"]
        uncertainty_summary = data[model]["uncertainty_summary"]
        authority_contract[model] = {
            "timeline_status": timeline_summary["status"],
            "uncertainty_status": uncertainty_summary["status"],
            "day15_diagnostic_closure_status": uncertainty_summary[
                "day15_diagnostic_closure"
            ]["status"],
            "timeline_input_fingerprint_sha256": timeline_summary[
                "input_fingerprint_sha256"
            ],
            "five_anchor_status": uncertainty_summary["timeline_receipts"][
                "status"
            ],
            "formal_authority_config_match": uncertainty_summary[
                "timeline_receipts"
            ]["formal_authority_config_match"],
            "formal_config": uncertainty_summary["timeline_receipts"][
                "expected_formal_config"
            ],
            "common_axis_scope_status": "PASS__BACKGROUND_SCOPE_APPLIED_BEFORE_POISSON_ARRIVALS",
            "mission_axis_status": "PASS__81_NODES_AND_TOTAL_COMPONENT_CLOSURE",
        }
    return {
        "schema_version": 2,
        "status": "PASS__M05_SECTION4_V2_FORMAL_RESULTS",
        "scenario_id": SCENARIO_ID,
        "authority_contract": authority_contract,
        "inputs": {
            **inputs,
            "geometry": {
                "path": str(GEOMETRY),
                "sha256": sha256_file(GEOMETRY),
            },
        },
        "production_decision_boundary": {
            "decision": "NO_TOPUP",
            "scope": "No new simulations are started; all existing accepted samples are exhausted and integrated.",
            "not_inferred_from": [
                "a local propagated Fmin relative standard error",
                "a zero selected-event point estimate",
                "the exact prompt-family intervals",
            ],
            "does_not_claim": "joint finite-template, replay-MC, signal-efficiency, source-model, response-model, or instrumental-systematic closure",
        },
        "uncertainty_boundaries": {
            "prompt_family_exact_intervals": "conditional exact finite-template intervals for seven constant-weight prompt families",
            "gamma_continuum": "not assigned the equal-weight Garwood construction because selected templates have non-equal event-level importance weights",
            "delayed": "not assigned the equal-weight Garwood construction because isotope/category normalizations and activities are heterogeneous and time dependent",
            "joint_propagation": "finite-template intervals, five-anchor replay MC, signal efficiency, and source/response systematics are reported as separate layers and are not jointly propagated",
            "quality_model_B_sensitivity": "conditional on the retained geometry, response/veto/Compton chain, environment, and incomplete joint uncertainty treatment",
        },
        "models": models,
        "comparisons": comparisons,
        "multiplicity": multiplicity,
        "outputs": [
            str(OUT / "fig09_mass_model_b_geometry_background.pdf"),
            str(OUT / "fig09_mass_model_b_geometry_background.png"),
            str(OUT / "fig07_hit_multiplicity.pdf"),
            str(OUT / "fig07_hit_multiplicity.png"),
            str(OUT / "fig04_common_time_normalization.pdf"),
            str(OUT / "fig04_common_time_normalization.png"),
            str(OUT / "fig10_mission_performance.pdf"),
            str(OUT / "fig10_mission_performance.png"),
            str(EXACT_INTERVAL_CSV),
        ],
    }


def assert_manuscript_output_safe(value: Any) -> None:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True).lower()
    for forbidden in ("atm511", "mono511"):
        require(
            forbidden not in serialized,
            f"manuscript-facing output contains a forbidden component name: {forbidden}",
        )


def write_exact_interval_csv(data: dict[str, dict[str, Any]]) -> None:
    rows = [
        row
        for model in ("A", "B")
        for row in data[model]["prompt_family_exact_intervals"]
    ]
    require(len(rows) == 2 * len(PROMPT_FAMILIES), "combined exact-interval CSV row count mismatch")
    assert_manuscript_output_safe(rows)
    with EXACT_INTERVAL_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    data = {model: model_data(model) for model in ("A", "B")}
    arrays = {model: mission_arrays(data[model]) for model in ("A", "B")}
    uncertainties = {
        model: propagated_uncertainty(data[model], arrays[model])
        for model in ("A", "B")
    }
    require(GEOMETRY.is_file(), f"geometry contract is missing: {GEOMETRY}")
    OUT.mkdir(parents=True, exist_ok=True)
    configure()
    build_geometry_background(data["B"])
    multiplicity = build_multiplicity(data)
    build_anchor_figure(data, arrays)
    build_mission_figure(arrays, uncertainties)
    report = build_report(data, arrays, uncertainties, multiplicity)
    assert_manuscript_output_safe(report)
    write_exact_interval_csv(data)
    destination = HERE / "M05_SECTION4_CURRENT_RESULTS.json"
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(destination)
    for path in report["outputs"]:
        print(path)


if __name__ == "__main__":
    main()
