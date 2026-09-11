#!/usr/bin/env python3
"""Build deterministic, flux-closed staging replacements for M05 Figures 3--10.

This builder is deliberately fail-closed.  It will not create the staging
directory unless both model catalogs and both schema-2 common-time timelines
are complete and internally additive.  It never writes into the M05NEW paper
tree; all products are atomically promoted to package-local
``outputs/05_figures_staging``.

The default action renders all eight figures as PDF and PNG and writes a
machine-readable chart map and receipt.  ``--check-inputs`` and ``--self-test``
are read-only.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parents[2]
OUTPUTS = PACKAGE / "outputs"
STAGING = OUTPUTS / "05_figures_staging"
M05NEW = ROOT / "core_md/balloon511_ea_latex_drafts/M05NEW"

SOURCE = OUTPUTS / "00_source_closure"
LINE_A = OUTPUTS / "01_line_response_a"
LINE_B = OUTPUTS / "01_line_response_b60"
CATALOGS = {
    "a": OUTPUTS / "02_fluxclosed_catalog_a",
    "b": OUTPUTS / "02_fluxclosed_catalog_b",
}
TIMELINES = {
    "a": OUTPUTS / "03_fluxclosed_timeline_a",
    "b": OUTPUTS / "03_fluxclosed_timeline_b",
}

PACKAGE60 = (
    ROOT
    / "engineering/geometry_optimization_20260815"
    / "60_sg3b_time_audit_nuclide_section_20260818"
)
PACKAGE63 = (
    ROOT
    / "engineering/geometry_optimization_20260815"
    / "63_m05new_sg3b_signal_statistics_20260820"
)
PACKAGE66 = (
    ROOT
    / "engineering/geometry_optimization_20260815"
    / "66_m05new_mxc_bpe_veto_review_20260821"
)
OPTV3 = (
    ROOT
    / "engineering/geometry_optimization_20260815/sh3/assembly_opt_v3"
)

CATALOG_FILES = (
    "combined_event_catalog.npz",
    "category_registry.json",
    "component_registry.json",
    "audit.json",
    "summary.json",
)
TIMELINE_FILES = (
    "anchor_timeline_rates.csv",
    "anchor_transport_components.csv",
    "mission_timeline_81nodes.csv",
    "mission_transport_components.csv",
    "direct_cutflow_day15.csv",
    "direct_measured_energy_day15_0p25keV.csv",
    "direct_hit_multiplicity_day15.csv",
    "summary.json",
)
ANCHORS = (0, 20, 40, 60, 80)
WINDOWS = ("broad_480_550", "w2_510p58_511p42")
STAGES = (
    "pre_veto",
    "plastic_positron_veto",
    "bgo_active_scintillator_veto",
    "combined_active_veto",
    "compton_trajectory_veto",
)
SPECTRUM_STAGES = (
    "pre_veto",
    "combined_active_veto",
    "compton_trajectory_veto",
)
STREAMS = ("all", "prompt", "delayed")
COMPONENTS = ("all", "other", "gamma_continuum", "atm511")
NAMED_COMPONENTS = COMPONENTS[1:]
FINAL_WINDOW = "w2_510p58_511p42"
FINAL_STAGE = "compton_trajectory_veto"
F0 = 1.0e-4
SOURCE_CLOSURE_STATUS = (
    "COMPLETE__HYBRID_W118P3_G0_DELINE__W114P6_G0P15_MONO_81X80"
)
MONO_DAY15_NODE = 60
MONO_DAY15_FLUX_PH_CM2_S = 0.16651547160226118
MONO_DAY15_DEPTH_G_CM2 = 3.4614689720143224

FIGURE_BASENAMES = {
    "fig03": "fig03_corrected_kev_sources",
    "fig04": "fig04_common_time_normalization",
    "fig05": "fig05_pre_veto_spectra",
    "fig06": "fig06_bgo_veto_spectrum",
    "fig07": "fig07_hit_multiplicity",
    "fig08": "fig08_background_origins",
    "fig09": "fig09_mass_model_b_geometry_background",
    "fig10": "fig10_mission_performance",
}

# Okabe-Ito-derived, print-safe palette plus neutrals.  Every cross-model or
# cross-stage encoding also has a distinct dash, marker, or hatch.
PALETTE = {
    "ink": "#202124",
    "muted": "#667085",
    "grid": "#D9DEE7",
    "paper": "#FFFFFF",
    "a": "#0072B2",
    "b": "#D55E00",
    "prompt": "#0072B2",
    "delayed": "#CC79A7",
    "other": "#7A7A7A",
    "gamma_continuum": "#009E73",
    "atm511": "#E69F00",
    "pre_veto": "#202124",
    "combined_active_veto": "#56B4E9",
    "compton_trajectory_veto": "#D55E00",
}
MODEL_STYLE = {
    "a": {"color": PALETTE["a"], "linestyle": "-", "marker": "o"},
    "b": {"color": PALETTE["b"], "linestyle": "--", "marker": "s"},
}
STAGE_LABEL = {
    "pre_veto": "Pre-veto",
    "plastic_positron_veto": "Plastic",
    "bgo_active_scintillator_veto": "BGO",
    "combined_active_veto": "Active veto",
    "compton_trajectory_veto": "Compton final",
}
COMPONENT_LABEL = {
    "other": "Other",
    "gamma_continuum": "Gamma continuum",
    "atm511": "Atmospheric 511 line",
}

CHART_SPECS: dict[str, dict[str, Any]] = {
    "fig03": {
        "question": "How is the legacy coarse 511-keV feature replaced by an exact continuum plus the physical mono-line?",
        "grain": "20 equal-mu bins in an explicit W118.3 continuum-de-line / W114.6 mono hybrid",
        "panels": [
            "broadband proposal and exactly de-lined continuum by source bin",
            "removed coarse line, nominal W=114.6 day-15 mono target/proposal, and W=118.3 continuum-state diagnostic",
        ],
        "input_keys": [
            "source_summary",
            "source_decomposition",
            "source_trajectory",
        ],
    },
    "fig04": {
        "question": "Do the five common-time anchors preserve direct rates and signal survival for both mass models?",
        "grain": "model x five anchor nodes, W2 final selection",
        "panels": ["direct and grouped-timeline rates", "timeline/direct ratio and conditional signal survival"],
        "input_keys": ["timeline_a_anchor", "timeline_b_anchor"],
    },
    "fig05": {
        "question": "Which prompt/delayed and continuum/line components form the day-15 pre-veto spectrum?",
        "grain": "model x stream x component x 0.25-keV measured-energy bin",
        "panels": ["mass model A", "mass model B"],
        "input_keys": ["timeline_a_spectrum", "timeline_b_spectrum"],
    },
    "fig06": {
        "question": "How do active and Compton selections reshape model-B spectra and W2 component rates?",
        "grain": "model B x stage x measured-energy bin or W2 component",
        "panels": ["stage spectra", "W2 stacked components and mono-line BGO-blind transport observation"],
        "input_keys": ["timeline_b_spectrum", "timeline_b_cutflow", "line_b_cutflow", "line_b_summary"],
    },
    "fig07": {
        "question": "How does selected TES hit multiplicity differ between mass models in the broad and W2 windows?",
        "grain": "model x window x final-stage hit multiplicity",
        "panels": ["480--550 keV", "W2: 510.58--511.42 keV"],
        "input_keys": ["timeline_a_multiplicity", "timeline_b_multiplicity"],
    },
    "fig08": {
        "question": "Which transport families and delayed origins remain after the flux-closed final selection?",
        "grain": "model x family at day 15; delayed origin group; cold-stage region",
        "panels": ["new family comparison", "model-A delayed origins", "model-B delayed origins", "cold-stage region shares"],
        "input_keys": [
            "timeline_a_cutflow",
            "timeline_b_cutflow",
            "origin_a",
            "origin_a_summary",
            "origin_b",
            "origin_b_summary",
            "cold_stage_share",
        ],
    },
    "fig09": {
        "question": "How does the mass-model-B TES placement connect to its cutflow and final composition?",
        "grain": "geometry component; stream x W2 stage; final W2 component",
        "panels": ["mass-model-B geometry section", "prompt/delayed cutflow", "final component composition"],
        "input_keys": [
            "geometry_contract",
            "optv3_manifest",
            "optv3_setup",
            "timeline_b_cutflow",
        ],
    },
    "fig10": {
        "question": "How do 81-node significance and Gaussian/Asimov flux thresholds evolve over the mission?",
        "grain": "model x 81 mission nodes",
        "panels": ["Gaussian significance at F0=1e-4", "3-sigma Gaussian and Asimov Fmin"],
        "input_keys": ["timeline_a_mission", "timeline_b_mission", "timeline_a_summary", "timeline_b_summary"],
    },
}


class BuildError(RuntimeError):
    """A fail-closed input, schema, or output-contract violation."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise BuildError(message)


def relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(8 * 1024 * 1024)
            if not block:
                return digest.hexdigest()
            digest.update(block)


def load_json(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"missing required JSON: {relative(path)}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BuildError(f"cannot read {relative(path)}: {exc}") from exc
    require(isinstance(value, dict), f"JSON root is not an object: {relative(path)}")
    return value


def read_csv(path: Path) -> list[dict[str, str]]:
    require(path.is_file(), f"missing required CSV: {relative(path)}")
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            require(reader.fieldnames is not None, f"CSV has no header: {relative(path)}")
            return list(reader)
    except OSError as exc:
        raise BuildError(f"cannot read {relative(path)}: {exc}") from exc


def require_columns(rows: Sequence[Mapping[str, str]], columns: Iterable[str], label: str) -> None:
    require(bool(rows), f"{label} is empty")
    missing = set(columns) - set(rows[0])
    require(not missing, f"{label} missing columns: {sorted(missing)}")


def number(row: Mapping[str, str], key: str, label: str) -> float:
    try:
        value = float(row[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise BuildError(f"{label}: invalid numeric {key!r}") from exc
    require(math.isfinite(value), f"{label}: non-finite {key!r}")
    return value


def integer(row: Mapping[str, str], key: str, label: str) -> int:
    value = number(row, key, label)
    result = int(value)
    require(value == result, f"{label}: {key!r} is not integral")
    return result


def close(actual: float, expected: float, label: str, *, rtol: float = 5e-10, atol: float = 2e-15) -> None:
    require(math.isclose(actual, expected, rel_tol=rtol, abs_tol=atol), f"{label}: {actual:.17g} != {expected:.17g}")


def selected(rows: Sequence[Mapping[str, str]], **filters: str) -> list[Mapping[str, str]]:
    return [row for row in rows if all(str(row.get(key)) == str(value) for key, value in filters.items())]


def aggregate(rows: Sequence[Mapping[str, str]], **filters: str) -> tuple[float, float, int]:
    subset = selected(rows, **filters)
    return (
        sum(number(row, "sumw_cps", "aggregate") for row in subset),
        sum(number(row, "sumw2_cps2", "aggregate") for row in subset),
        sum(integer(row, "selected_raw", "aggregate") for row in subset),
    )


def validate_catalog(model: str, path: Path) -> list[Path]:
    required = [path / name for name in CATALOG_FILES]
    for item in required:
        require(item.is_file(), f"model-{model} catalog is incomplete: {relative(item)}")
        require(item.stat().st_size > 0, f"model-{model} catalog file is empty: {relative(item)}")
    summary = load_json(path / "summary.json")
    audit = load_json(path / "audit.json")
    registry = load_json(path / "category_registry.json")
    require(summary.get("status") == "COMPLETE__POSITIVE_FLUXCLOSED_EVENT_CATALOG", f"model-{model} catalog summary is not COMPLETE")
    require(summary.get("model") == model, f"model-{model} catalog identity differs")
    require(audit.get("status") == "PASS__FLUXCLOSED_CATALOG_AUDIT", f"model-{model} catalog audit is not PASS")
    source_audit = audit.get("source_closure", {})
    require(source_audit.get("manifest_sha256") == sha256_file(SOURCE / "source_closure.json"), f"model-{model} catalog source manifest is stale")
    require(source_audit.get("bins_sha256") == sha256_file(SOURCE / "coarse_line_decomposition_20bins.csv"), f"model-{model} catalog de-line table is stale")
    require(source_audit.get("mono_target_validation", {}).get("sha256") == sha256_file(SOURCE / "mono511_target_81x80.csv"), f"model-{model} catalog mono target is stale")
    require(isinstance(registry.get("categories"), list) and registry["categories"], f"model-{model} category registry is empty")
    for category in registry["categories"]:
        require(category.get("component") in NAMED_COMPONENTS, f"model-{model} category has invalid component")
    return required


def _validate_cutflow(model: str, rows: list[dict[str, str]]) -> None:
    require_columns(
        rows,
        ("time_bin_id", "day_mid", "stream", "family", "component", "window_id", "stage", "selected_raw", "sumw_cps", "sumw2_cps2", "sqrt_sumw2_cps", "effective_sample_size"),
        f"model-{model} cutflow",
    )
    keys: set[tuple[str, ...]] = set()
    for row in rows:
        require(integer(row, "time_bin_id", "cutflow") == 60, f"model-{model} cutflow is not day-15 node 60")
        require(row["stream"] in STREAMS[1:], f"model-{model} cutflow stream differs")
        require(row["component"] in NAMED_COMPONENTS, f"model-{model} cutflow component differs")
        require(row["window_id"] in WINDOWS, f"model-{model} cutflow window differs")
        require(row["stage"] in STAGES, f"model-{model} cutflow stage differs")
        key = tuple(row[name] for name in ("stream", "family", "component", "window_id", "stage"))
        require(key not in keys, f"model-{model} duplicate cutflow key {key}")
        keys.add(key)
        sumw = number(row, "sumw_cps", "cutflow")
        sumw2 = number(row, "sumw2_cps2", "cutflow")
        require(sumw >= 0.0 and sumw2 >= 0.0, f"model-{model} cutflow has negative weights")
        close(number(row, "sqrt_sumw2_cps", "cutflow"), math.sqrt(sumw2), "cutflow sqrt(sumw2)")


def _cutflow_total(rows: Sequence[Mapping[str, str]], window: str, stage: str, component: str | None = None, stream: str | None = None) -> tuple[float, float, int]:
    subset = [row for row in rows if row["window_id"] == window and row["stage"] == stage]
    if component is not None:
        subset = [row for row in subset if row["component"] == component]
    if stream is not None:
        subset = [row for row in subset if row["stream"] == stream]
    return (
        sum(number(row, "sumw_cps", "cutflow total") for row in subset),
        sum(number(row, "sumw2_cps2", "cutflow total") for row in subset),
        sum(integer(row, "selected_raw", "cutflow total") for row in subset),
    )


def _validate_spectrum(model: str, rows: list[dict[str, str]], cutflow: list[dict[str, str]]) -> None:
    require_columns(
        rows,
        ("time_bin_id", "day_mid", "stage", "stream", "component", "energy_low_keV", "energy_high_keV", "selected_raw", "sumw_cps", "sumw2_cps2", "sqrt_sumw2_cps"),
        f"model-{model} spectrum",
    )
    require(len(rows) == 10_080, f"model-{model} spectrum must have 10080 rows, found {len(rows)}")
    table: dict[tuple[str, str, str, int], dict[str, float]] = {}
    for row in rows:
        stage, stream, component = row["stage"], row["stream"], row["component"]
        require(stage in SPECTRUM_STAGES and stream in STREAMS and component in COMPONENTS, f"model-{model} spectrum axis differs")
        low = number(row, "energy_low_keV", "spectrum")
        high = number(row, "energy_high_keV", "spectrum")
        index = round((low - 480.0) / 0.25)
        close(low, 480.0 + 0.25 * index, "spectrum low edge")
        close(high, low + 0.25, "spectrum high edge")
        require(0 <= index < 280, f"model-{model} spectrum energy index differs")
        key = (stage, stream, component, index)
        require(key not in table, f"model-{model} duplicate spectrum key {key}")
        values = {
            "raw": float(integer(row, "selected_raw", "spectrum")),
            "sumw": number(row, "sumw_cps", "spectrum"),
            "sumw2": number(row, "sumw2_cps2", "spectrum"),
        }
        require(min(values.values()) >= 0.0, f"model-{model} spectrum has negative value")
        close(number(row, "sqrt_sumw2_cps", "spectrum"), math.sqrt(values["sumw2"]), "spectrum sqrt(sumw2)")
        table[key] = values
    expected = len(SPECTRUM_STAGES) * len(STREAMS) * len(COMPONENTS) * 280
    require(len(table) == expected, f"model-{model} spectrum key grid is incomplete")
    for stage in SPECTRUM_STAGES:
        for index in range(280):
            for moment in ("raw", "sumw", "sumw2"):
                all_value = table[(stage, "all", "all", index)][moment]
                by_stream = sum(table[(stage, stream, "all", index)][moment] for stream in STREAMS[1:])
                by_component = sum(table[(stage, "all", component, index)][moment] for component in NAMED_COMPONENTS)
                close(all_value, by_stream, f"model-{model} spectrum stream {moment} closure", rtol=5e-11)
                close(all_value, by_component, f"model-{model} spectrum component {moment} closure", rtol=5e-11)
        histogram = [table[(stage, "all", "all", index)] for index in range(280)]
        observed = (sum(x["sumw"] for x in histogram), sum(x["sumw2"] for x in histogram), round(sum(x["raw"] for x in histogram)))
        expected_total = _cutflow_total(cutflow, WINDOWS[0], stage)
        close(observed[0], expected_total[0], f"model-{model} spectrum/cutflow sumw")
        close(observed[1], expected_total[1], f"model-{model} spectrum/cutflow sumw2")
        require(observed[2] == expected_total[2], f"model-{model} spectrum/cutflow raw closure failed")


def _validate_multiplicity(model: str, rows: list[dict[str, str]], cutflow: list[dict[str, str]]) -> None:
    require_columns(
        rows,
        ("time_bin_id", "day_mid", "window_id", "stage", "component", "hit_multiplicity", "selected_raw", "sumw_cps", "sumw2_cps2", "sqrt_sumw2_cps"),
        f"model-{model} multiplicity",
    )
    table: dict[tuple[str, str, str, int], dict[str, float]] = {}
    bins_by_window: dict[str, set[int]] = defaultdict(set)
    for row in rows:
        window, stage, component = row["window_id"], row["stage"], row["component"]
        require(window in WINDOWS and stage in STAGES and component in COMPONENTS, f"model-{model} multiplicity axis differs")
        multiplicity = integer(row, "hit_multiplicity", "multiplicity")
        require(multiplicity >= 0, f"model-{model} negative hit multiplicity")
        bins_by_window[window].add(multiplicity)
        key = (window, stage, component, multiplicity)
        require(key not in table, f"model-{model} duplicate multiplicity key {key}")
        values = {
            "raw": float(integer(row, "selected_raw", "multiplicity")),
            "sumw": number(row, "sumw_cps", "multiplicity"),
            "sumw2": number(row, "sumw2_cps2", "multiplicity"),
        }
        require(min(values.values()) >= 0.0, f"model-{model} multiplicity has negative value")
        close(number(row, "sqrt_sumw2_cps", "multiplicity"), math.sqrt(values["sumw2"]), "multiplicity sqrt(sumw2)")
        table[key] = values
    for window in WINDOWS:
        require(bool(bins_by_window[window]), f"model-{model} multiplicity has no bins for {window}")
        for stage in STAGES:
            for multiplicity in bins_by_window[window]:
                for component in COMPONENTS:
                    require((window, stage, component, multiplicity) in table, f"model-{model} multiplicity grid is incomplete")
                for moment in ("raw", "sumw", "sumw2"):
                    total = table[(window, stage, "all", multiplicity)][moment]
                    components = sum(table[(window, stage, component, multiplicity)][moment] for component in NAMED_COMPONENTS)
                    close(total, components, f"model-{model} multiplicity component {moment} closure", rtol=5e-11)
            all_bins = [table[(window, stage, "all", value)] for value in bins_by_window[window]]
            observed = (sum(x["sumw"] for x in all_bins), sum(x["sumw2"] for x in all_bins), round(sum(x["raw"] for x in all_bins)))
            expected = _cutflow_total(cutflow, window, stage)
            close(observed[0], expected[0], f"model-{model} multiplicity/cutflow sumw")
            close(observed[1], expected[1], f"model-{model} multiplicity/cutflow sumw2")
            require(observed[2] == expected[2], f"model-{model} multiplicity/cutflow raw closure failed")


def validate_timeline(model: str, path: Path) -> tuple[dict[str, Any], list[Path]]:
    required = [path / name for name in TIMELINE_FILES]
    receipts = [path / "receipts" / f"anchor_{node:03d}.json" for node in ANCHORS]
    for item in required + receipts:
        require(item.is_file(), f"model-{model} timeline is incomplete: {relative(item)}")
        require(item.stat().st_size > 0, f"model-{model} timeline file is empty: {relative(item)}")
    summary = load_json(path / "summary.json")
    require(summary.get("schema_version") == 2, f"model-{model} timeline schema is not 2")
    require(summary.get("status") == "PASS__M05_FLUXCLOSED_COMMON_TIME_TIMELINE", f"model-{model} timeline status is not PASS")
    require(summary.get("model") == model, f"model-{model} timeline identity differs")
    require(set(summary.get("outputs", [])) == set(TIMELINE_FILES), f"model-{model} timeline output manifest differs")
    fingerprint = summary.get("input_fingerprint", {})
    file_hashes = fingerprint.get("file_sha256", {})
    current_fingerprint_files = (
        SOURCE / "source_closure.json",
        SOURCE / "mono511_target_81x80.csv",
        SOURCE / "trajectory_component_scales_81nodes.csv",
        CATALOGS[model] / "category_registry.json",
        CATALOGS[model] / "audit.json",
        CATALOGS[model] / "summary.json",
    )
    for current in current_fingerprint_files:
        key = relative(current)
        require(file_hashes.get(key) == sha256_file(current), f"model-{model} timeline fingerprint is stale for {key}")
    catalog_npz = CATALOGS[model] / "combined_event_catalog.npz"
    catalog_fingerprint = fingerprint.get("catalog_npz", {})
    require(catalog_fingerprint.get("path") == relative(catalog_npz), f"model-{model} timeline catalog path differs")
    require(int(catalog_fingerprint.get("bytes", -1)) == catalog_npz.stat().st_size, f"model-{model} timeline catalog size is stale")
    require(int(catalog_fingerprint.get("mtime_ns", -1)) == catalog_npz.stat().st_mtime_ns, f"model-{model} timeline catalog mtime is stale")
    product = summary.get("day15_product_schema", {})
    require(product.get("schema_version") == 2 and product.get("closure_status") == "PASS__DAY15_PRODUCTS_ADDITIVE_CUTFLOW_CLOSED", f"model-{model} day-15 schema closure is not PASS")
    for node, receipt_path in zip(ANCHORS, receipts):
        receipt = load_json(receipt_path)
        require(receipt.get("status") == "PASS__FLUXCLOSED_ANCHOR_COMPLETE", f"model-{model} anchor {node} receipt is not PASS")
        require(int(receipt.get("time_bin_id", -1)) == node, f"model-{model} anchor receipt identity differs")

    anchor = read_csv(path / "anchor_timeline_rates.csv")
    require_columns(anchor, ("time_bin_id", "day_mid", "window_id", "stage", "direct_no_coincidence_rate_cps", "direct_sum_W_i2_cps2", "direct_transport_sigma_cps", "timeline_counts", "timeline_rate_cps", "timeline_rate_standard_error_cps", "timeline_to_direct_ratio", "signal_accidental_survival", "signal_survival_standard_error"), f"model-{model} anchors")
    require(len(anchor) == 50, f"model-{model} anchor table must have 50 rows")
    anchor_keys = {(integer(row, "time_bin_id", "anchor"), row["window_id"], row["stage"]) for row in anchor}
    require(anchor_keys == {(node, window, stage) for node in ANCHORS for window in WINDOWS for stage in STAGES}, f"model-{model} anchor key coverage differs")

    mission = read_csv(path / "mission_timeline_81nodes.csv")
    require_columns(mission, ("time_bin_id", "day_mid", "cumulative_background_counts", "cumulative_signal_counts_per_unit_flux", "cumulative_transport_sum_W_i2_counts2", "Fmin_3sigma_gaussian_ph_cm2_s", "Fmin_3sigma_poisson_asimov_ph_cm2_s"), f"model-{model} mission")
    require(len(mission) == 81, f"model-{model} mission table must have 81 rows")
    mission.sort(key=lambda row: integer(row, "time_bin_id", "mission"))
    require([integer(row, "time_bin_id", "mission") for row in mission] == list(range(81)), f"model-{model} mission node coverage differs")
    days = [number(row, "day_mid", "mission") for row in mission]
    require(all(right > left for left, right in zip(days, days[1:])), f"model-{model} mission days are not strictly increasing")

    cutflow = read_csv(path / "direct_cutflow_day15.csv")
    _validate_cutflow(model, cutflow)
    spectrum = read_csv(path / "direct_measured_energy_day15_0p25keV.csv")
    _validate_spectrum(model, spectrum, cutflow)
    multiplicity = read_csv(path / "direct_hit_multiplicity_day15.csv")
    _validate_multiplicity(model, multiplicity, cutflow)
    return ({"summary": summary, "anchor": anchor, "mission": mission, "cutflow": cutflow, "spectrum": spectrum, "multiplicity": multiplicity}, required + receipts)


def input_paths() -> dict[str, Path]:
    return {
        "source_summary": SOURCE / "source_closure.json",
        "source_decomposition": SOURCE / "coarse_line_decomposition_20bins.csv",
        "source_mono_target": SOURCE / "mono511_target_81x80.csv",
        "source_trajectory": SOURCE / "trajectory_component_scales_81nodes.csv",
        "line_a_summary": LINE_A / "summary.json",
        "line_b_summary": LINE_B / "summary.json",
        "line_b_cutflow": LINE_B / "mono_line_cutflow.csv",
        "origin_a": PACKAGE60 / "outputs/selected_w2_activation_origin_groups.csv",
        "origin_a_summary": PACKAGE60 / "outputs/summary.json",
        "origin_b": PACKAGE63 / "outputs/05_optv3_delayed_origins/optv3_delayed_origin_breakdown.csv",
        "origin_b_summary": PACKAGE63 / "outputs/05_optv3_delayed_origins/summary.json",
        "cold_stage_share": PACKAGE66 / "data/cold_stage_origin_share.csv",
        "geometry_contract": PACKAGE66 / "data/cross_section_geometry_contract.csv",
        "optv3_manifest": OPTV3 / "data/assembly_opt_v3_manifest.json",
        "optv3_setup": OPTV3 / "geometry/SH3_Assembly_OptV3.geo.setup",
        "timeline_a_anchor": TIMELINES["a"] / "anchor_timeline_rates.csv",
        "timeline_b_anchor": TIMELINES["b"] / "anchor_timeline_rates.csv",
        "timeline_a_spectrum": TIMELINES["a"] / "direct_measured_energy_day15_0p25keV.csv",
        "timeline_b_spectrum": TIMELINES["b"] / "direct_measured_energy_day15_0p25keV.csv",
        "timeline_a_cutflow": TIMELINES["a"] / "direct_cutflow_day15.csv",
        "timeline_b_cutflow": TIMELINES["b"] / "direct_cutflow_day15.csv",
        "timeline_a_multiplicity": TIMELINES["a"] / "direct_hit_multiplicity_day15.csv",
        "timeline_b_multiplicity": TIMELINES["b"] / "direct_hit_multiplicity_day15.csv",
        "timeline_a_mission": TIMELINES["a"] / "mission_timeline_81nodes.csv",
        "timeline_b_mission": TIMELINES["b"] / "mission_timeline_81nodes.csv",
        "timeline_a_summary": TIMELINES["a"] / "summary.json",
        "timeline_b_summary": TIMELINES["b"] / "summary.json",
    }


def validate_reference_inputs() -> dict[str, Any]:
    paths = input_paths()
    source_summary = load_json(paths["source_summary"])
    require(source_summary.get("schema_version") == 2, "source closure schema is not 2")
    require(source_summary.get("status") == SOURCE_CLOSURE_STATUS, "source closure is not COMPLETE/current")
    continuum_state = source_summary["continuum_deline_reference_closure"]
    for key, expected in (
        ("solar_modulation_W_MV", 118.3),
        ("cutoff_rigidity_Rc_GV", 11.6),
        ("atmospheric_depth_g_cm2", 3.84535),
        ("local_geometry_g", 0.0),
    ):
        close(float(continuum_state[key]), expected, f"continuum de-line {key}")
    day15_authority = source_summary["mono511_day15_authority"]
    for key, expected in (
        ("solar_modulation_W_MV", 114.6),
        ("cutoff_rigidity_Rc_GV", 11.6),
        ("atmospheric_depth_g_cm2", MONO_DAY15_DEPTH_G_CM2),
        ("local_geometry_g", 0.15),
        ("integrated_flux_ph_cm2_s", MONO_DAY15_FLUX_PH_CM2_S),
    ):
        close(float(day15_authority[key]), expected, f"mono day15 {key}")
    require(int(day15_authority["time_bin_id"]) == MONO_DAY15_NODE, "mono day15 node differs")
    source_rows = read_csv(paths["source_decomposition"])
    require_columns(source_rows, ("source_bin20", "embedded_coarse_line_flux_ph_cm2_s", "parma511_continuum_deline_state_flux_ph_cm2_s", "mono511_day15_authority_flux_ph_cm2_s", "broadband_total_flux_ph_cm2_s", "continuum_flux_ph_cm2_s"), "source decomposition")
    require(len(source_rows) == 20 and {integer(row, "source_bin20", "source") for row in source_rows} == set(range(20)), "source decomposition is not the complete 20-bin grid")
    close(
        math.fsum(number(row, "mono511_day15_authority_flux_ph_cm2_s", "source") for row in source_rows),
        MONO_DAY15_FLUX_PH_CM2_S,
        "20-bin day15 mono closure",
    )
    target_rows = read_csv(paths["source_mono_target"])
    require_columns(target_rows, ("time_bin_id", "source_bin80", "target_flux_ph_cm2_s", "proposal_flux_ph_cm2_s", "importance_ratio", "target_W_MV", "target_Rc_GV", "target_depth_g_cm2", "target_g"), "mono target")
    require(len(target_rows) == 81 * 80, "mono target is not 81x80")
    node60 = [row for row in target_rows if integer(row, "time_bin_id", "mono target") == MONO_DAY15_NODE]
    require(len(node60) == 80 and {integer(row, "source_bin80", "mono target") for row in node60} == set(range(80)), "mono node60 is not 80 bins")
    for row in node60:
        close(number(row, "target_W_MV", "mono target"), 114.6, "mono target W")
        close(number(row, "target_g", "mono target"), 0.15, "mono target g")
        close(number(row, "target_Rc_GV", "mono target"), 11.6, "mono target Rc")
        close(number(row, "target_depth_g_cm2", "mono target"), MONO_DAY15_DEPTH_G_CM2, "mono target depth")
        close(number(row, "target_flux_ph_cm2_s", "mono target"), number(row, "proposal_flux_ph_cm2_s", "mono target"), "node60 target/proposal")
        close(number(row, "importance_ratio", "mono target"), 1.0, "node60 importance")
    close(math.fsum(number(row, "target_flux_ph_cm2_s", "mono target") for row in node60), MONO_DAY15_FLUX_PH_CM2_S, "node60 target integral")
    trajectory_rows = read_csv(paths["source_trajectory"])
    require(len(trajectory_rows) == 81, "source trajectory is not 81 nodes")
    trajectory_node60 = trajectory_rows[MONO_DAY15_NODE]
    require(integer(trajectory_node60, "time_bin_id", "source trajectory") == MONO_DAY15_NODE, "source trajectory node60 differs")
    close(number(trajectory_node60, "target_mono511_flux_ph_cm2_s", "source trajectory"), MONO_DAY15_FLUX_PH_CM2_S, "trajectory node60 mono")
    close(number(trajectory_node60, "recomposed_gamma_flux_ph_cm2_s", "source trajectory"), number(trajectory_node60, "continuum_flux_ph_cm2_s", "source trajectory") + MONO_DAY15_FLUX_PH_CM2_S, "trajectory node60 hybrid recomposition")

    for model, line_dir in (("a", LINE_A), ("b", LINE_B)):
        line_summary = load_json(line_dir / "summary.json")
        require(line_summary.get("status") == "COMPLETE__MONO_LINE_COMMON_RESPONSE" and line_summary.get("model") == model, f"model-{model} mono-line response is not COMPLETE")
    line_rows = read_csv(paths["line_b_cutflow"])
    require_columns(line_rows, ("model", "window_id", "stage", "selected_events", "weighted_rate_cps", "weighted_mc_sigma_cps"), "model-B line cutflow")
    line_pre = selected(line_rows, model="b", window_id=FINAL_WINDOW, stage="pre_veto")
    line_bgo = selected(line_rows, model="b", window_id=FINAL_WINDOW, stage="bgo_active_scintillator_veto")
    require(len(line_pre) == len(line_bgo) == 1, "model-B line cutflow lacks unique pre/BGO W2 rows")
    close(number(line_pre[0], "weighted_rate_cps", "line pre"), number(line_bgo[0], "weighted_rate_cps", "line BGO"), "model-B mono-line BGO rate equality", rtol=0.0, atol=2e-18)
    require(integer(line_pre[0], "selected_events", "line pre") == integer(line_bgo[0], "selected_events", "line BGO"), "model-B mono-line BGO selected-event equality failed")

    origin_a_summary = load_json(paths["origin_a_summary"])
    require(origin_a_summary.get("status") == "PASS__SG3B_RECEIPT_TIME_AND_SELECTED_NUCLIDE_SECTION_AUDIT", "model-A origin audit is not PASS")
    origin_a = read_csv(paths["origin_a"])
    require_columns(origin_a, ("nuclide", "source_volume_short", "selected_events", "day15_noacc_cps"), "model-A origins")
    origin_b_summary = load_json(paths["origin_b_summary"])
    require(origin_b_summary.get("status") == "PASS__EXACT_POSITION_VOLUME_MATERIAL_CLOSED", "model-B origin audit is not PASS")
    origin_b = read_csv(paths["origin_b"])
    require_columns(origin_b, ("source_material", "source_volume", "family", "source_parent_ZA", "raw_selected", "day15_rate_cps"), "model-B origins")
    cold = read_csv(paths["cold_stage_share"])
    require_columns(cold, ("geometry", "region", "day15_delayed_W2_rate_cps", "fraction_of_delayed_W2_final"), "cold-stage origin shares")
    require({"SG3B", "SH3_OptV3"}.issubset({row["geometry"] for row in cold}), "cold-stage shares lack both geometries")
    geometry = read_csv(paths["geometry_contract"])
    require_columns(geometry, ("geometry", "component", "kind", "x_min_cm", "x_max_cm", "z_min_cm", "z_max_cm"), "geometry contract")
    require(any(row["geometry"] == "SH3_OptV3" and row["kind"] == "TES_active_layer" for row in geometry), "geometry contract lacks OptV3 TES layers")
    manifest = load_json(paths["optv3_manifest"])
    require(manifest.get("status") == "PASS__SH3_ASSEMBLY_OPT_V3_BUILT", "OptV3 geometry manifest is not PASS")
    recorded_setup_hash = manifest.get("outputs", {}).get("SH3_Assembly_OptV3.geo.setup", {}).get("sha256")
    require(recorded_setup_hash == sha256_file(paths["optv3_setup"]), "OptV3 setup hash differs from its manifest")
    return {
        "source_summary": source_summary,
        "source_rows": source_rows,
        "source_target_rows": target_rows,
        "source_trajectory_rows": trajectory_rows,
        "line_rows": line_rows,
        "origin_a": origin_a,
        "origin_b": origin_b,
        "cold": cold,
        "geometry": geometry,
        "manifest": manifest,
    }


def collect_inputs() -> tuple[dict[str, Any], dict[str, Path]]:
    data = validate_reference_inputs()
    gate_paths: dict[str, Path] = {}
    for model in ("a", "b"):
        for path in validate_catalog(model, CATALOGS[model]):
            gate_paths[f"catalog_{model}_{path.name}"] = path
        timeline, timeline_paths = validate_timeline(model, TIMELINES[model])
        data[f"timeline_{model}"] = timeline
        for path in timeline_paths:
            suffix = path.name if path.parent.name != "receipts" else f"receipt_{path.stem}"
            gate_paths[f"timeline_{model}_{suffix}"] = path
    paths = input_paths()
    paths.update(gate_paths)
    return data, paths


def setup_plotting() -> Any:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise BuildError("matplotlib is required only for formal rendering") from exc
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "axes.labelsize": 8.5,
            "axes.titlesize": 9.5,
            "axes.edgecolor": PALETTE["ink"],
            "axes.linewidth": 0.8,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": PALETTE["grid"],
            "grid.linewidth": 0.55,
            "grid.alpha": 0.8,
            "legend.fontsize": 7.2,
            "lines.linewidth": 1.55,
            "savefig.facecolor": PALETTE["paper"],
            "figure.facecolor": PALETTE["paper"],
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )
    return plt


def panel_label(
    ax: Any,
    label: str,
    *,
    x: float = -0.12,
    y: float = 1.04,
    fontsize: float = 10,
) -> None:
    ax.text(x, y, label, transform=ax.transAxes, ha="left", va="bottom", weight="bold", fontsize=fontsize)


def tidy(ax: Any) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def spectrum_series(rows: Sequence[Mapping[str, str]], stage: str, stream: str, component: str) -> tuple[list[float], list[float], list[float]]:
    subset = selected(rows, stage=stage, stream=stream, component=component)
    subset.sort(key=lambda row: number(row, "energy_low_keV", "spectrum plot"))
    return (
        [(number(row, "energy_low_keV", "spectrum plot") + number(row, "energy_high_keV", "spectrum plot")) / 2.0 for row in subset],
        [number(row, "sumw_cps", "spectrum plot") for row in subset],
        [number(row, "sqrt_sumw2_cps", "spectrum plot") for row in subset],
    )


def plot_fig03(plt: Any, data: dict[str, Any]) -> Any:
    rows = sorted(data["source_rows"], key=lambda row: integer(row, "source_bin20", "source plot"))
    mu = [-0.95 + 0.1 * integer(row, "source_bin20", "source plot") for row in rows]
    broad = [number(row, "broadband_total_flux_ph_cm2_s", "source plot") for row in rows]
    continuum = [number(row, "continuum_flux_ph_cm2_s", "source plot") for row in rows]
    coarse = [number(row, "embedded_coarse_line_flux_ph_cm2_s", "source plot") for row in rows]
    nominal = [number(row, "mono511_day15_authority_flux_ph_cm2_s", "source plot") for row in rows]
    diagnostic = [number(row, "parma511_continuum_deline_state_flux_ph_cm2_s", "source plot") for row in rows]
    fig, axes = plt.subplots(1, 2, figsize=(7.15, 3.0), constrained_layout=True)
    axes[0].plot(mu, broad, color=PALETTE["ink"], marker="o", ms=3, label="Legacy broadband proposal")
    axes[0].plot(mu, continuum, color=PALETTE["gamma_continuum"], ls="--", marker="s", ms=3, label="Exact de-lined continuum")
    axes[0].fill_between(mu, continuum, broad, color=PALETTE["atm511"], alpha=0.22, hatch="///", edgecolor=PALETTE["atm511"], label="Removed coarse feature")
    axes[0].set(xlabel=r"Direction cosine $\mu$", ylabel=r"Bin-integrated flux (ph cm$^{-2}$ s$^{-1}$)", title="Source-field decomposition")
    axes[0].legend(frameon=False)
    axes[1].plot(mu, coarse, color=PALETTE["muted"], marker="x", label="Removed coarse feature")
    axes[1].plot(mu, nominal, color=PALETTE["atm511"], ls="-", marker="D", ms=3, label="Nominal target = proposal: W=114.6")
    axes[1].plot(mu, diagnostic, color=PALETTE["muted"], ls="--", marker="s", ms=3, label="W=118.3 continuum-state diagnostic")
    node60 = data["source_trajectory_rows"][MONO_DAY15_NODE]
    continuum_day15 = number(node60, "continuum_flux_ph_cm2_s", "source plot")
    mono_day15 = data["source_summary"]["mono511_day15_authority"]["integrated_flux_ph_cm2_s"]
    hybrid_day15 = number(node60, "recomposed_gamma_flux_ph_cm2_s", "source plot")
    axes[1].text(
        0.03,
        0.04,
        "Hybrid day-15 totals (ph cm$^{-2}$ s$^{-1}$)\n"
        f"W118 de-lined continuum {continuum_day15:.6f} + W114 mono {mono_day15:.6f}\n"
        f"= recomposed {hybrid_day15:.6f}; PARMA systematic excluded",
        transform=axes[1].transAxes,
        fontsize=6.8,
        va="bottom",
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": PALETTE["grid"]},
    )
    axes[1].set(xlabel=r"Direction cosine $\mu$", ylabel=r"Bin-integrated line flux (ph cm$^{-2}$ s$^{-1}$)", title="Mono-line replacement")
    axes[1].legend(frameon=False, loc="upper left")
    for label, ax in zip(("(a)", "(b)"), axes):
        panel_label(ax, label)
        tidy(ax)
    return fig


def plot_fig04(plt: Any, data: dict[str, Any]) -> Any:
    fig, axes = plt.subplots(1, 2, figsize=(7.15, 3.0), constrained_layout=True)
    for model in ("a", "b"):
        rows = selected(data[f"timeline_{model}"]["anchor"], window_id=FINAL_WINDOW, stage=FINAL_STAGE)
        rows.sort(key=lambda row: integer(row, "time_bin_id", "anchor plot"))
        days = [number(row, "day_mid", "anchor plot") for row in rows]
        direct = [number(row, "direct_no_coincidence_rate_cps", "anchor plot") for row in rows]
        timeline = [number(row, "timeline_rate_cps", "anchor plot") for row in rows]
        timeline_err = [number(row, "timeline_rate_standard_error_cps", "anchor plot") for row in rows]
        style = MODEL_STYLE[model]
        axes[0].plot(days, direct, color=style["color"], ls=":", marker=style["marker"], ms=3, label=f"{model.upper()} direct")
        axes[0].errorbar(days, timeline, yerr=timeline_err, color=style["color"], ls=style["linestyle"], marker=style["marker"], ms=3, capsize=2, label=f"{model.upper()} common time")
        ratio = [number(row, "timeline_to_direct_ratio", "anchor plot") for row in rows]
        ratio_err = [err / direct_rate if direct_rate > 0 else 0.0 for err, direct_rate in zip(timeline_err, direct)]
        survival = [number(row, "signal_accidental_survival", "anchor plot") for row in rows]
        survival_err = [number(row, "signal_survival_standard_error", "anchor plot") for row in rows]
        axes[1].errorbar(days, ratio, yerr=ratio_err, color=style["color"], ls=style["linestyle"], marker=style["marker"], ms=3, capsize=2, label=f"{model.upper()} timeline/direct")
        axes[1].errorbar(days, survival, yerr=survival_err, color=style["color"], ls=":", marker="^" if model == "a" else "v", ms=3, capsize=2, label=f"{model.upper()} signal survival")
    axes[0].set(xlabel="Mission day", ylabel="W2 final rate (s$^{-1}$)", title="Five common-time anchors")
    axes[0].set_yscale("log")
    axes[0].legend(frameon=False, loc="lower center", ncol=2, fontsize=6.4, columnspacing=0.8, handlelength=2.3)
    axes[1].axhline(1.0, color=PALETTE["muted"], lw=0.8, ls=(0, (3, 2)))
    axes[1].set(xlabel="Mission day", ylabel="Dimensionless ratio", title="Timing and signal retention")
    axes[1].legend(frameon=False, loc="lower center", ncol=2, fontsize=6.4, columnspacing=0.8, handlelength=2.3)
    for label, ax in zip(("(a)", "(b)"), axes):
        panel_label(ax, label)
        tidy(ax)
    return fig


def plot_fig05(plt: Any, data: dict[str, Any]) -> Any:
    fig, axes = plt.subplots(1, 2, figsize=(7.15, 3.45), constrained_layout=True, sharey=True)
    curves = [
        ("all", "all", "Total", PALETTE["ink"], "-", None),
        ("prompt", "all", "Prompt", PALETTE["prompt"], "--", None),
        ("delayed", "all", "Delayed", PALETTE["delayed"], ":", None),
        ("all", "gamma_continuum", "Gamma continuum", PALETTE["gamma_continuum"], "-.", "o"),
        ("all", "atm511", "Atmospheric 511", PALETTE["atm511"], (0, (5, 2)), "D"),
    ]
    for ax, model, panel in zip(axes, ("a", "b"), ("(a)", "(b)")):
        rows = data[f"timeline_{model}"]["spectrum"]
        for stream, component, label, color, linestyle, marker in curves:
            x, y, sigma = spectrum_series(rows, "pre_veto", stream, component)
            ax.plot(x, y, color=color, ls=linestyle, marker=marker, markevery=20 if marker else None, ms=2.5, label=label)
            if stream == "all" and component == "all":
                positive = [value for value in y if value > 0.0]
                floor = min(positive) * 0.25 if positive else 1e-12
                lower = [max(value - error, floor) for value, error in zip(y, sigma)]
                upper = [max(value + error, floor) for value, error in zip(y, sigma)]
                ax.fill_between(x, lower, upper, step="mid", color=PALETTE["ink"], alpha=0.12, label=r"Total MC $\sqrt{\sum w_i^2}$")
        ax.set_yscale("log")
        ax.set_xlim(480.0, 550.0)
        ax.axvspan(510.58, 511.42, facecolor=PALETTE["atm511"], alpha=0.10, hatch="///", edgecolor=PALETTE["atm511"])
        ax.set(xlabel="Measured energy (keV)", title=f"Mass model {model.upper()}: day 15 pre-veto")
        panel_label(ax, panel)
        tidy(ax)
    axes[0].set_ylabel(r"Rate per 0.25-keV bin (s$^{-1}$)")
    handles, labels = axes[1].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        frameon=False,
        loc="outside lower center",
        ncol=3,
        fontsize=6.5,
        columnspacing=1.0,
        handlelength=2.4,
    )
    return fig


def plot_fig06(plt: Any, data: dict[str, Any]) -> Any:
    fig, axes = plt.subplots(1, 2, figsize=(7.15, 3.1), constrained_layout=True)
    spectrum = data["timeline_b"]["spectrum"]
    for stage, marker in zip(SPECTRUM_STAGES, ("o", "s", "D")):
        x, y, sigma = spectrum_series(spectrum, stage, "all", "all")
        color = PALETTE[stage]
        linestyle = {"pre_veto": "-", "combined_active_veto": "--", "compton_trajectory_veto": "-."}[stage]
        axes[0].plot(x, y, color=color, ls=linestyle, marker=marker, markevery=24, ms=2.4, label=STAGE_LABEL[stage])
        if stage == FINAL_STAGE:
            positive = [value for value in y if value > 0.0]
            floor = min(positive) * 0.25 if positive else 1e-12
            axes[0].fill_between(x, [max(v - e, floor) for v, e in zip(y, sigma)], [max(v + e, floor) for v, e in zip(y, sigma)], step="mid", color=color, alpha=0.15, label=r"Final MC $\sqrt{\sum w_i^2}$")
    axes[0].set_yscale("log")
    axes[0].axvspan(510.58, 511.42, facecolor=PALETTE["atm511"], alpha=0.10, hatch="///", edgecolor=PALETTE["atm511"])
    axes[0].set(xlabel="Measured energy (keV)", ylabel=r"Rate per 0.25-keV bin (s$^{-1}$)", title="Model-B stage spectra")
    axes[0].legend(frameon=True, facecolor="white", edgecolor="none", framealpha=0.88, fontsize=6.5, labelspacing=0.25)

    cutflow = data["timeline_b"]["cutflow"]
    xstage = list(range(len(STAGES)))
    bottoms = [0.0] * len(STAGES)
    hatches = {"other": "..", "gamma_continuum": "//", "atm511": "xx"}
    for component in NAMED_COMPONENTS:
        values = [_cutflow_total(cutflow, FINAL_WINDOW, stage, component)[0] for stage in STAGES]
        axes[1].bar(xstage, values, bottom=bottoms, width=0.68, color=PALETTE[component], hatch=hatches[component], edgecolor="white", linewidth=0.5, label=COMPONENT_LABEL[component])
        bottoms = [a + b for a, b in zip(bottoms, values)]
    total_sigma = [math.sqrt(_cutflow_total(cutflow, FINAL_WINDOW, stage)[1]) for stage in STAGES]
    axes[1].errorbar(xstage, bottoms, yerr=total_sigma, fmt="none", ecolor=PALETTE["ink"], capsize=2, lw=0.9, label=r"Total MC $\sqrt{\sum w_i^2}$")
    pre = selected(data["line_rows"], model="b", window_id=FINAL_WINDOW, stage="pre_veto")[0]
    bgo = selected(data["line_rows"], model="b", window_id=FINAL_WINDOW, stage="bgo_active_scintillator_veto")[0]
    axes[1].annotate(
        f"Mono-line transport support\n{integer(pre, 'selected_events', 'annotation')} pre = {integer(bgo, 'selected_events', 'annotation')} after BGO\n(no hardware-efficiency claim)",
        xy=(2, bottoms[2]),
        xytext=(0.54, 0.50),
        textcoords="axes fraction",
        ha="left",
        va="top",
        fontsize=6.2,
        arrowprops={"arrowstyle": "->", "color": PALETTE["atm511"], "lw": 0.9},
        bbox={"boxstyle": "round,pad=0.2", "facecolor": "white", "edgecolor": PALETTE["atm511"]},
    )
    axes[1].set_xticks(xstage, [STAGE_LABEL[stage] for stage in STAGES], rotation=31, ha="right", fontsize=7.0)
    axes[1].set(ylabel="Day-15 W2 rate (s$^{-1}$)", title="Model-B W2 component cutflow")
    axes[1].legend(frameon=False, loc="upper right", fontsize=6.2, labelspacing=0.25, handlelength=2.0)
    for label, ax in zip(("(a)", "(b)"), axes):
        panel_label(ax, label)
        tidy(ax)
    return fig


def plot_fig07(plt: Any, data: dict[str, Any]) -> Any:
    from matplotlib.ticker import MaxNLocator

    fig, axes = plt.subplots(1, 2, figsize=(7.15, 3.0), constrained_layout=True, sharey=True)
    for ax, window, panel, title in zip(axes, WINDOWS, ("(a)", "(b)"), ("Broad window: 480--550 keV", "W2: 510.58--511.42 keV")):
        for model in ("a", "b"):
            rows = selected(data[f"timeline_{model}"]["multiplicity"], window_id=window, stage=FINAL_STAGE, component="all")
            rows.sort(key=lambda row: integer(row, "hit_multiplicity", "multiplicity plot"))
            x = [integer(row, "hit_multiplicity", "multiplicity plot") for row in rows]
            y = [number(row, "sumw_cps", "multiplicity plot") for row in rows]
            error = [number(row, "sqrt_sumw2_cps", "multiplicity plot") for row in rows]
            style = MODEL_STYLE[model]
            ax.errorbar(x, y, yerr=error, color=style["color"], ls=style["linestyle"], marker=style["marker"], ms=3, capsize=2, label=f"Model {model.upper()}")
        ax.set_yscale("log")
        ax.set(xlabel="TES hit multiplicity", title=title)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.legend(frameon=False)
        panel_label(ax, panel)
        tidy(ax)
    axes[0].set_ylabel("Day-15 final rate (s$^{-1}$)")
    return fig


def _short(text: str, limit: int = 30) -> str:
    aliases = {
        "Cu_SubstrateSupport_OpenRing_": "Cu open ring ",
        "SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm": "L0 Cu heat-sink ring",
        "ColdPlate_MXC_50mK_SD_anchor": "MXC 50 mK Cu plate",
        "SH3_OptV2_W_Frame_": "W frame ",
        "SH3_TES_BottomColdPlate_": "TES bottom plate ",
        "SG3B ": "",
        "SG3B_": "",
        "SH3 ": "",
        "SH3_": "",
    }
    for old, new in aliases.items():
        text = text.replace(old, new)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _top_with_other(items: list[tuple[str, float]], keep: int) -> list[tuple[str, float]]:
    items = sorted(items, key=lambda item: (-item[1], item[0]))
    if len(items) <= keep:
        return items
    return items[:keep] + [("Other", sum(value for _, value in items[keep:]))]


def plot_fig08(plt: Any, data: dict[str, Any]) -> Any:
    from matplotlib.ticker import MaxNLocator

    fig, axes = plt.subplots(2, 2, figsize=(7.15, 6.35), constrained_layout=True, gridspec_kw={"width_ratios": [0.96, 1.04]})
    fig.set_constrained_layout_pads(w_pad=0.035, h_pad=0.055, wspace=0.06, hspace=0.14)
    family_by_model: dict[str, dict[str, float]] = {}
    all_families: set[str] = set()
    for model in ("a", "b"):
        values: dict[str, float] = defaultdict(float)
        for row in selected(data[f"timeline_{model}"]["cutflow"], window_id=FINAL_WINDOW, stage=FINAL_STAGE):
            values[row["family"]] += number(row, "sumw_cps", "family plot")
        family_by_model[model] = dict(values)
        all_families.update(values)
    ranked = sorted(all_families, key=lambda family: (-max(family_by_model[m].get(family, 0.0) for m in ("a", "b")), family))
    retained = ranked[:7]
    if len(ranked) > 7:
        retained.append("Other")
    positions = list(range(len(retained)))
    width = 0.36
    for offset, model in ((-width / 2, "a"), (width / 2, "b")):
        values = []
        for family in retained:
            if family == "Other":
                values.append(sum(family_by_model[model].get(item, 0.0) for item in ranked[7:]))
            else:
                values.append(family_by_model[model].get(family, 0.0))
        axes[0, 0].bar([x + offset for x in positions], values, width=width, color=MODEL_STYLE[model]["color"], hatch="//" if model == "a" else "xx", edgecolor="white", label=f"Model {model.upper()}")
    axes[0, 0].set_xticks(positions, [_short(item, 16) for item in retained], rotation=32, ha="right", fontsize=6.6)
    axes[0, 0].set(ylabel="Day-15 W2 final rate (s$^{-1}$)")
    axes[0, 0].set_title("Flux-closed transport families", loc="left", fontsize=8.5, pad=5)
    axes[0, 0].set_yscale("log")
    axes[0, 0].legend(frameon=False)

    a_items = [(f"{_short(row['source_volume_short'], 18)} · {row['nuclide']}", number(row, "day15_noacc_cps", "A origin plot")) for row in data["origin_a"]]
    b_items = [(f"{_short(row['source_volume'], 18)} · {row['family']}", number(row, "day15_rate_cps", "B origin plot")) for row in data["origin_b"]]
    for ax, model, items, color, title in (
        (axes[0, 1], "A", _top_with_other(a_items, 6), PALETTE["a"], "Model-A delayed origins"),
        (axes[1, 0], "B", _top_with_other(b_items, 6), PALETTE["b"], "Model-B delayed origins"),
    ):
        labels, values = zip(*reversed(items))
        ax.barh(range(len(values)), values, color=color, alpha=0.82, hatch="//" if model == "A" else "xx", edgecolor="white")
        ax.set_yticks(range(len(values)), labels)
        ax.set(xlabel="Day-15 delayed W2 rate (s$^{-1}$)")
        ax.set_title(title, loc="left", fontsize=8.5, pad=5)
        ax.tick_params(axis="y", labelsize=6.4)
        ax.tick_params(axis="x", labelsize=6.2)
        ax.xaxis.set_major_locator(MaxNLocator(nbins=4))
        ax.text(0.98, 0.97, "Transport-weighted selected origins\n(no reported intervals)", transform=ax.transAxes, ha="right", va="top", fontsize=5.7, color=PALETTE["muted"])

    cold = data["cold"]
    regions = sorted({row["region"] for row in cold})
    region_colors = [PALETTE["gamma_continuum"], PALETTE["atm511"], PALETTE["muted"]]
    bottoms = [0.0, 0.0]
    geometry_order = ("SG3B", "SH3_OptV3")
    for index, region in enumerate(regions):
        values = []
        for geometry in geometry_order:
            matches = selected(cold, geometry=geometry, region=region)
            values.append(number(matches[0], "fraction_of_delayed_W2_final", "cold share plot") if matches else 0.0)
        axes[1, 1].barh([0, 1], values, left=bottoms, color=region_colors[index % len(region_colors)], hatch=("//", "xx", "..")[index % 3], edgecolor="white", label=_short(region, 23))
        bottoms = [a + b for a, b in zip(bottoms, values)]
    for y, total in enumerate(bottoms):
        axes[1, 1].text(min(total, 1.0) + 0.01, y, f"{100*total:.1f}%", va="center", fontsize=7)
    axes[1, 1].set_yticks([0, 1], ["Mass model A", "Mass model B"])
    axes[1, 1].set_xlim(0.0, max(1.05, max(bottoms) * 1.18))
    axes[1, 1].set(xlabel="Fraction of delayed W2 final")
    axes[1, 1].set_title("Delayed-origin region redistribution", loc="left", fontsize=8.5, pad=5)
    axes[1, 1].set_ylim(-0.5, 2.05)
    axes[1, 1].tick_params(axis="y", labelsize=6.5)
    axes[1, 1].legend(frameon=False, loc="upper center", fontsize=5.7, labelspacing=0.15, handlelength=1.8)
    for label, ax in zip(("(a)", "(b)", "(c)", "(d)"), axes.flat):
        panel_label(ax, label, x=0.0, y=1.13, fontsize=9)
        tidy(ax)
    return fig


def plot_fig09(plt: Any, data: dict[str, Any]) -> Any:
    from matplotlib.patches import Rectangle

    fig, axes = plt.subplots(1, 3, figsize=(7.15, 3.35), constrained_layout=True, gridspec_kw={"width_ratios": [1.3, 1.0, 0.9]})
    fig.set_constrained_layout_pads(w_pad=0.035, h_pad=0.05, wspace=0.07, hspace=0.08)
    ax = axes[0]
    geometry = selected(data["geometry"], geometry="SH3_OptV3")
    ax.add_patch(Rectangle((-45.75, -13.85), 30.75, 22.10, facecolor="#EEF1F3", edgecolor=PALETTE["ink"], lw=1.0, hatch="..", label="Welded saddle/chimney envelope"))
    for row in geometry:
        x0, x1 = number(row, "x_min_cm", "geometry plot"), number(row, "x_max_cm", "geometry plot")
        z0, z1 = number(row, "z_min_cm", "geometry plot"), number(row, "z_max_cm", "geometry plot")
        if row["kind"] == "cold_plate":
            ax.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0, facecolor="#C67C4E", edgecolor="#7D462A", lw=0.7, hatch="//"))
        elif row["kind"] == "TES_active_layer":
            ax.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0, facecolor=PALETTE["atm511"], edgecolor=PALETTE["ink"], lw=0.6))
    ax.add_patch(Rectangle((-41.7, -7.0), 13.0, 8.4, fill=False, edgecolor=PALETTE["a"], lw=1.1, ls="--", label="TES/BGO neighborhood"))
    ax.annotate("six TES layers\nin lateral chimney", xy=(-35.5, -2.8), xytext=(-10.0, 13.0), fontsize=6.4, ha="center", arrowprops={"arrowstyle": "->", "lw": 0.8})
    ax.set(xlim=(-48, 20), ylim=(-15, 34), xlabel="Cross-section x (cm)", ylabel="z (cm)")
    ax.set_title("Mass model B detector--shield section", loc="left", fontsize=8.3, pad=5)
    ax.set_aspect("equal", adjustable="box")
    ax.legend(frameon=False, fontsize=6.1, loc="upper left")
    ax.text(0.02, 0.02, "Geometry schematic; not a dose map", transform=ax.transAxes, fontsize=5.6, color=PALETTE["muted"], bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.82, "pad": 0.5})

    cutflow = data["timeline_b"]["cutflow"]
    positions = list(range(len(STAGES)))
    for stream, marker, linestyle in (("prompt", "o", "-"), ("delayed", "s", "--")):
        values, errors = [], []
        for stage in STAGES:
            rate, variance, _ = _cutflow_total(cutflow, FINAL_WINDOW, stage, stream=stream)
            values.append(rate)
            errors.append(math.sqrt(variance))
        axes[1].errorbar(positions, values, yerr=errors, color=PALETTE[stream], marker=marker, ls=linestyle, ms=3, capsize=2, label=stream.capitalize())
    axes[1].set_xticks(positions, [STAGE_LABEL[stage] for stage in STAGES], rotation=30, ha="right")
    axes[1].set(ylabel="Day-15 W2 rate (s$^{-1}$)")
    axes[1].set_title("Model-B stream cutflow", loc="left", fontsize=8.3, pad=5)
    axes[1].tick_params(axis="x", labelsize=6.3)
    axes[1].set_yscale("log")
    axes[1].legend(frameon=False)

    component_values = {component: _cutflow_total(cutflow, FINAL_WINDOW, FINAL_STAGE, component)[0] for component in NAMED_COMPONENTS}
    total = sum(component_values.values())
    require(total > 0.0, "model-B final composition total is zero")
    order = sorted(NAMED_COMPONENTS, key=lambda component: (-component_values[component], component))
    fractions = [component_values[component] / total for component in order]
    axes[2].barh(range(len(order)), fractions, color=[PALETTE[component] for component in order], hatch=[{"other": "..", "gamma_continuum": "//", "atm511": "xx"}[component] for component in order], edgecolor="white")
    axes[2].set_yticks(range(len(order)), [COMPONENT_LABEL[component] for component in order])
    axes[2].invert_yaxis()
    for index, fraction in enumerate(fractions):
        axes[2].text(fraction + 0.012, index, f"{100*fraction:.1f}%", va="center", fontsize=7)
    axes[2].set_xlim(0, max(fractions) * 1.25)
    axes[2].set(xlabel="Fraction of W2 final")
    axes[2].set_title("Model-B final composition", loc="left", fontsize=8.3, pad=5)
    axes[2].tick_params(axis="y", labelsize=6.6)
    for label, axis in zip(("(a)", "(b)", "(c)"), axes):
        panel_label(axis, label, x=0.0, y=1.13, fontsize=9)
        tidy(axis)
    return fig


def _asimov_significance(signal: float, background: float) -> float:
    if signal <= 0.0:
        return 0.0
    if background <= 0.0:
        return math.sqrt(2.0 * signal)
    return math.sqrt(2.0 * ((signal + background) * math.log1p(signal / background) - signal))


def plot_fig10(plt: Any, data: dict[str, Any]) -> Any:
    fig, axes = plt.subplots(1, 2, figsize=(7.15, 3.05), constrained_layout=True)
    for model in ("a", "b"):
        rows = data[f"timeline_{model}"]["mission"]
        days = [number(row, "day_mid", "mission plot") for row in rows]
        background = [number(row, "cumulative_background_counts", "mission plot") for row in rows]
        kernel = [number(row, "cumulative_signal_counts_per_unit_flux", "mission plot") for row in rows]
        significance = [F0 * k / math.sqrt(b) if b > 0.0 else math.nan for b, k in zip(background, kernel)]
        style = MODEL_STYLE[model]
        axes[0].plot(days, significance, color=style["color"], ls=style["linestyle"], marker=style["marker"], markevery=10, ms=3, label=f"Model {model.upper()}")
        for key, linestyle, marker, label in (
            ("Fmin_3sigma_gaussian_ph_cm2_s", style["linestyle"], style["marker"], "Gaussian"),
            ("Fmin_3sigma_poisson_asimov_ph_cm2_s", ":" if model == "a" else "-.", "^" if model == "a" else "v", "Asimov"),
        ):
            points = [(number(row, "day_mid", "Fmin plot"), float(row[key])) for row in rows if row.get(key, "") not in ("", None)]
            axes[1].plot([x for x, _ in points], [y for _, y in points], color=style["color"], ls=linestyle, marker=marker, markevery=10, ms=3, label=f"Model {model.upper()} {label}")
        uncertainty = data[f"timeline_{model}"]["summary"].get("statistical_uncertainty", {}).get("Fmin", {})
        endpoint_key = "Fmin_3sigma_gaussian_ph_cm2_s"
        endpoint = uncertainty.get(endpoint_key, {})
        if endpoint:
            axes[1].errorbar([days[-1]], [float(endpoint["value"])], yerr=[float(endpoint["standard_error"])], fmt=style["marker"], color=style["color"], capsize=3, ms=4)
    for threshold, label in ((3.0, "3σ"), (5.0, "5σ")):
        axes[0].axhline(threshold, color=PALETTE["muted"], lw=0.8, ls="--" if threshold == 3 else ":")
        axes[0].text(20.05, threshold, label, va="center", fontsize=6.8, color=PALETTE["muted"])
    axes[0].set(xlabel="Mission day", ylabel=r"Gaussian significance $S/\sqrt{B}$", title=r"81-node fold at $F_0=10^{-4}$ ph cm$^{-2}$ s$^{-1}$")
    axes[0].set_xlim(0.0, 20.8)
    axes[0].legend(frameon=False)
    axes[1].set_yscale("log")
    axes[1].set(xlabel="Mission day", ylabel=r"3σ $F_{\min}$ (ph cm$^{-2}$ s$^{-1}$)", title="Gaussian and Poisson-Asimov thresholds")
    axes[1].legend(frameon=False, ncol=2, fontsize=6.5)
    axes[1].text(0.02, 0.02, "Endpoint bars: propagated statistical 1σ; curves are point estimates", transform=axes[1].transAxes, fontsize=6.3, color=PALETTE["muted"])
    for label, ax in zip(("(a)", "(b)"), axes):
        panel_label(ax, label)
        tidy(ax)
    return fig


PLOTTERS = {
    "fig03": plot_fig03,
    "fig04": plot_fig04,
    "fig05": plot_fig05,
    "fig06": plot_fig06,
    "fig07": plot_fig07,
    "fig08": plot_fig08,
    "fig09": plot_fig09,
    "fig10": plot_fig10,
}


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def save_figure(fig: Any, directory: Path, basename: str, dpi: int) -> list[Path]:
    pdf = directory / f"{basename}.pdf"
    png = directory / f"{basename}.png"
    fixed_date = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
    fig.savefig(pdf, bbox_inches="tight", metadata={"Title": basename, "Author": "M05 flux-closure builder", "Creator": "build_m05_fluxclosed_figures.py", "CreationDate": fixed_date, "ModDate": fixed_date})
    fig.savefig(png, dpi=dpi, bbox_inches="tight", metadata={"Software": "build_m05_fluxclosed_figures.py"})
    return [pdf, png]


def input_records(paths: Mapping[str, Path]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    by_resolved: dict[Path, str] = {}
    for key in sorted(paths):
        path = paths[key]
        require(path.is_file(), f"missing input while hashing: {relative(path)}")
        resolved = path.resolve()
        if resolved not in by_resolved:
            by_resolved[resolved] = sha256_file(path)
        digest = by_resolved[resolved]
        records[key] = {"path": relative(path), "sha256": digest, "bytes": path.stat().st_size}
    return records


def chart_map(records: Mapping[str, Mapping[str, Any]], outputs_by_figure: Mapping[str, Sequence[Path]]) -> dict[str, Any]:
    figures = []
    for figure in sorted(CHART_SPECS):
        spec = CHART_SPECS[figure]
        figures.append(
            {
                "figure": figure,
                "question": spec["question"],
                "data_grain": spec["grain"],
                "panels": spec["panels"],
                "inputs": [records[key] for key in spec["input_keys"]],
                "outputs": [
                    {"path": relative(STAGING / path.name), "sha256": sha256_file(path), "bytes": path.stat().st_size}
                    for path in outputs_by_figure[figure]
                ],
            }
        )
    return {
        "schema_version": 2,
        "status": "PASS__M05_FLUXCLOSED_FIGURE_CHART_MAP",
        "output_directory": relative(STAGING),
        "visual_contract": {
            "palette": PALETTE,
            "non_color_redundancy": "model, stage, stream, and component encodings use dash, marker, or hatch in addition to color",
            "uncertainty_policy": "sqrt(sum w_i^2) is shown only where available; Fig.10 endpoint bars use the recorded propagated statistical 1-sigma; origin panels explicitly omit unavailable intervals",
            "claim_boundary": (
                "transport/statistical products only; W118.3 continuum de-line "
                "and W114.6 mono target are an explicit hybrid, not one atmosphere; "
                "physical PARMA/source-model systematics are EXCLUDED; geometry "
                "schematic is not a dose, structural, or hardware-efficiency claim"
            ),
        },
        "figures": figures,
    }


def render(data: dict[str, Any], paths: dict[str, Path], dpi: int) -> dict[str, Any]:
    require(STAGING.resolve() != M05NEW.resolve() and M05NEW.resolve() not in STAGING.resolve().parents, "refusing to write into M05NEW")
    require(STAGING == OUTPUTS / "05_figures_staging", "staging output contract changed")
    require(not STAGING.exists(), f"non-overwrite guard: {relative(STAGING)} already exists")
    require(OUTPUTS.is_dir(), f"package outputs directory is missing: {relative(OUTPUTS)}")
    records = input_records(paths)
    plt = setup_plotting()
    temporary = Path(tempfile.mkdtemp(prefix=".05_figures_staging.", dir=OUTPUTS))
    promoted = False
    try:
        outputs_by_figure: dict[str, list[Path]] = {}
        for figure in sorted(PLOTTERS):
            fig = PLOTTERS[figure](plt, data)
            outputs_by_figure[figure] = save_figure(fig, temporary, FIGURE_BASENAMES[figure], dpi)
            plt.close(fig)
        mapping = chart_map(records, outputs_by_figure)
        write_json(temporary / "chart_map.json", mapping)
        receipt = {
            "schema_version": 2,
            "status": "PASS__M05_FLUXCLOSED_FIGURES_STAGED",
            "generator": {"path": relative(Path(__file__)), "sha256": sha256_file(Path(__file__))},
            "formal_gate": {
                "source_closure": data["source_summary"]["status"],
                "source_schema_version": data["source_summary"]["schema_version"],
                "source_authority": (
                    "hybrid W118.3/g0 continuum de-line + W114.6/g0.15 mono target"
                ),
                "physical_PARMA_flux_systematic": "EXCLUDED",
                "catalogs": {model: "COMPLETE__POSITIVE_FLUXCLOSED_EVENT_CATALOG" for model in ("a", "b")},
                "timelines": {model: data[f"timeline_{model}"]["summary"]["status"] for model in ("a", "b")},
            },
            "inputs": records,
            "chart_map": {"path": relative(STAGING / "chart_map.json"), "sha256": sha256_file(temporary / "chart_map.json")},
            "outputs": {figure: mapping["figures"][index]["outputs"] for index, figure in enumerate(sorted(CHART_SPECS))},
            "non_overwrite": True,
        }
        write_json(temporary / "receipt.json", receipt)
        os.replace(temporary, STAGING)
        promoted = True
        return receipt
    finally:
        if not promoted and temporary.exists():
            shutil.rmtree(temporary)


def self_test() -> dict[str, Any]:
    require(set(CHART_SPECS) == set(FIGURE_BASENAMES) == set(PLOTTERS), "figure registry mismatch")
    require(len(set(FIGURE_BASENAMES.values())) == 8, "duplicate figure basename")
    require(len({PALETTE["a"], PALETTE["b"], PALETTE["gamma_continuum"], PALETTE["atm511"]}) == 4, "palette identities collide")
    toy = [
        {"stream": "prompt", "family": "gamma", "component": "gamma_continuum", "window_id": FINAL_WINDOW, "stage": FINAL_STAGE, "selected_raw": "2", "sumw_cps": "0.3", "sumw2_cps2": "0.05"},
        {"stream": "delayed", "family": "n", "component": "other", "window_id": FINAL_WINDOW, "stage": FINAL_STAGE, "selected_raw": "1", "sumw_cps": "0.2", "sumw2_cps2": "0.04"},
    ]
    rate, variance, raw = _cutflow_total(toy, FINAL_WINDOW, FINAL_STAGE)
    close(rate, 0.5, "self-test weighted sum")
    close(variance, 0.09, "self-test sumw2")
    require(raw == 3, "self-test raw sum")
    close(_asimov_significance(10.0, 100.0), math.sqrt(2.0 * (110.0 * math.log(1.1) - 10.0)), "self-test Asimov")
    require("hybrid" in CHART_SPECS["fig03"]["grain"].lower(), "Fig.03 does not disclose the hybrid source")
    close(MONO_DAY15_FLUX_PH_CM2_S, 0.16651547160226118, "self-test day15 mono authority")
    return {
        "status": "PASS__M05_FIGURE_BUILDER_SYNTHETIC_SELF_TEST",
        "figures": sorted(CHART_SPECS),
        "source_authority": "PASS__SPLIT_W118_CONTINUUM_W114_MONO",
        "physical_PARMA_flux_systematic": "EXCLUDED",
        "formal_outputs_created": 0,
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = value.add_mutually_exclusive_group()
    mode.add_argument("--check-inputs", action="store_true", help="validate and hash all formal inputs; do not render or create staging output")
    mode.add_argument("--self-test", action="store_true", help="run pure synthetic contract checks; do not inspect formal inputs or create output")
    value.add_argument("--dpi", type=int, default=220, help="PNG resolution for formal staging render (default: 220)")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        require(72 <= args.dpi <= 600, "--dpi must be between 72 and 600")
        if args.self_test:
            print(json.dumps(self_test(), indent=2, sort_keys=True))
            return 0
        data, paths = collect_inputs()
        if args.check_inputs:
            records = input_records(paths)
            print(json.dumps({"status": "PASS__M05_FIGURE_INPUTS_VALID", "inputs": records, "formal_outputs_created": 0}, indent=2, sort_keys=True))
            return 0
        receipt = render(data, paths, args.dpi)
        print(json.dumps({"status": receipt["status"], "output_directory": relative(STAGING), "figures": sorted(CHART_SPECS)}, indent=2, sort_keys=True))
        return 0
    except BuildError as exc:
        print(json.dumps({"status": "FAIL_CLOSED__M05_FIGURE_BUILDER", "error": str(exc), "output_created": False}, indent=2, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
