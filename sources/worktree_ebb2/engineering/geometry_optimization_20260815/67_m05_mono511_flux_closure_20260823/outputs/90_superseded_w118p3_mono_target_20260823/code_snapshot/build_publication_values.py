#!/usr/bin/env python3
"""Build the publication-facing values bundle for package 67.

The builder is intentionally read-only with respect to the formal 00--04
results.  It accepts only the completed flux-closure chain, independently
checks the cross-file numerical closures needed by a manuscript table, and
creates one new output directory.  Existing output is never overwritten.

No raw SIM file is opened and no transport or timeline job is started.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


HERE = Path(__file__).resolve()
PACKAGE = HERE.parents[1]
OUTPUTS = PACKAGE / "outputs"
OUTPUT_DIR = OUTPUTS / "06_publication_values"

SOURCE_DIR = OUTPUTS / "00_source_closure"
LINE_DIRS = {
    "a": OUTPUTS / "01_line_response_a",
    "b": OUTPUTS / "01_line_response_b60",
}
CATALOG_DIRS = {
    "a": OUTPUTS / "02_fluxclosed_catalog_a",
    "b": OUTPUTS / "02_fluxclosed_catalog_b",
}
TIMELINE_DIRS = {
    "a": OUTPUTS / "03_fluxclosed_timeline_a",
    "b": OUTPUTS / "03_fluxclosed_timeline_b",
}
VALIDATION_PATH = OUTPUTS / "04_validation" / "topup_decision.json"
VALIDATOR_PATH = PACKAGE / "code" / "validate_fluxclosed_results.py"

SOURCE_FILES = (
    "source_closure.json",
    "coarse_line_decomposition_20bins.csv",
    "mono511_target_81x80.csv",
    "trajectory_component_scales_81nodes.csv",
)
LINE_FILES = (
    "summary.json",
    "mono_line_event_catalog.npz",
    "mono_line_cutflow.csv",
    "mono_line_final_by_source_bin80.csv",
)
CATALOG_FILES = (
    "summary.json",
    "audit.json",
    "category_registry.json",
    "component_registry.json",
    "combined_event_catalog.npz",
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

ANCHOR_NODES = (0, 20, 40, 60, 80)
FINAL_WINDOW = "w2_510p58_511p42"
FINAL_STAGE = "compton_trajectory_veto"
COMPONENTS = ("other", "gamma_continuum", "atm511")
ALL_COMPONENTS = COMPONENTS + ("total",)
FMIN_KEYS = (
    "Fmin_3sigma_gaussian_ph_cm2_s",
    "Fmin_5sigma_gaussian_ph_cm2_s",
    "Fmin_3sigma_poisson_asimov_ph_cm2_s",
    "Fmin_5sigma_poisson_asimov_ph_cm2_s",
)
MODEL_LABELS = {
    "a": {"label_en": "Model A", "label_zh": "模型 A"},
    "b": {"label_en": "Model B", "label_zh": "模型 B"},
}

EXPECTED_STATUS = {
    "source": "COMPLETE__EXACT_COARSE_SUBTRACTION__OFFICIAL_W118P3_MONO_81X80",
    "line": "COMPLETE__MONO_LINE_COMMON_RESPONSE",
    "catalog": "COMPLETE__POSITIVE_FLUXCLOSED_EVENT_CATALOG",
    "catalog_audit": "PASS__FLUXCLOSED_CATALOG_AUDIT",
    "timeline": "PASS__M05_FLUXCLOSED_COMMON_TIME_TIMELINE",
}


class PublicationError(RuntimeError):
    """A missing authority, schema mismatch, or numerical closure failure."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PublicationError(message)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PublicationError(f"cannot read valid JSON: {relative(path)}") from error


def read_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    except OSError as error:
        raise PublicationError(f"cannot read CSV: {relative(path)}") from error


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PACKAGE.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def number(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise PublicationError(f"missing/non-numeric {label}") from error
    require(math.isfinite(result), f"non-finite {label}: {result}")
    return result


def integer(value: Any, label: str) -> int:
    try:
        if isinstance(value, float):
            require(value.is_integer(), f"non-integral {label}: {value}")
            result = int(value)
        else:
            result = int(str(value).strip())
    except (TypeError, ValueError) as error:
        raise PublicationError(f"missing/non-integer {label}") from error
    return result


def row_float(row: Mapping[str, Any], key: str, label: str) -> float:
    require(key in row, f"{label} lacks {key}")
    return number(row[key], f"{label}.{key}")


def row_int(row: Mapping[str, Any], key: str, label: str) -> int:
    require(key in row, f"{label} lacks {key}")
    return integer(row[key], f"{label}.{key}")


def close(
    actual: float,
    expected: float,
    label: str,
    *,
    rtol: float = 4e-11,
    atol: float = 2e-12,
) -> None:
    if not math.isclose(actual, expected, rel_tol=rtol, abs_tol=atol):
        raise PublicationError(
            f"{label} mismatch: actual={actual:.17g}, "
            f"expected={expected:.17g}, delta={actual - expected:.17g}"
        )


def require_columns(
    rows: Sequence[Mapping[str, Any]], columns: Iterable[str], label: str
) -> None:
    require(bool(rows), f"{label} is empty")
    missing = sorted(set(columns) - set(rows[0]))
    require(not missing, f"{label} missing columns: {missing}")


def keyed_rows(
    rows: Sequence[Mapping[str, Any]],
    keys: Sequence[str],
    label: str,
) -> dict[tuple[Any, ...], Mapping[str, Any]]:
    result: dict[tuple[Any, ...], Mapping[str, Any]] = {}
    for row in rows:
        key: list[Any] = []
        for field in keys:
            require(field in row, f"{label} lacks key column {field}")
            if field == "time_bin_id":
                key.append(row_int(row, field, label))
            else:
                key.append(str(row[field]))
        composite = tuple(key)
        require(composite not in result, f"{label} duplicate key {composite}")
        result[composite] = row
    return result


def asimov_significance(signal: float, background: float) -> float:
    require(signal >= 0.0 and background > 0.0, "Asimov inputs are invalid")
    value = 2.0 * (
        (signal + background) * math.log1p(signal / background) - signal
    )
    return math.sqrt(max(value, 0.0))


def asimov_required_signal(background: float, z_value: float) -> float:
    require(background > 0.0 and z_value > 0.0, "Asimov inversion inputs invalid")
    low = 0.0
    high = max(z_value * math.sqrt(background), z_value * z_value)
    while asimov_significance(high, background) < z_value:
        high *= 2.0
    for _ in range(180):
        middle = 0.5 * (low + high)
        if asimov_significance(middle, background) < z_value:
            low = middle
        else:
            high = middle
    return 0.5 * (low + high)


def expected_fmin(background: float, kernel: float) -> dict[str, float]:
    require(background > 0.0 and kernel > 0.0, "B/K must be positive")
    return {
        "Fmin_3sigma_gaussian_ph_cm2_s": 3.0 * math.sqrt(background) / kernel,
        "Fmin_5sigma_gaussian_ph_cm2_s": 5.0 * math.sqrt(background) / kernel,
        "Fmin_3sigma_poisson_asimov_ph_cm2_s": (
            asimov_required_signal(background, 3.0) / kernel
        ),
        "Fmin_5sigma_poisson_asimov_ph_cm2_s": (
            asimov_required_signal(background, 5.0) / kernel
        ),
    }


def formal_groups() -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = {
        "00_source_closure": [SOURCE_DIR / name for name in SOURCE_FILES]
    }
    for model in ("a", "b"):
        groups[f"01_line_response_{model}"] = [
            LINE_DIRS[model] / name for name in LINE_FILES
        ]
        groups[f"02_fluxclosed_catalog_{model}"] = [
            CATALOG_DIRS[model] / name for name in CATALOG_FILES
        ]
        groups[f"03_fluxclosed_timeline_{model}"] = [
            TIMELINE_DIRS[model] / name for name in TIMELINE_FILES
        ]
    groups["04_validation"] = [VALIDATION_PATH]
    return groups


def _status_check(
    path: Path,
    expected: str,
    invalid: list[dict[str, str]],
    *,
    prefix: bool = False,
    model: str | None = None,
    schema_version: int | None = None,
) -> None:
    if not path.is_file():
        return
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        invalid.append({"path": relative(path), "reason": f"invalid JSON: {error}"})
        return
    status = str(payload.get("status", ""))
    status_ok = status.startswith(expected) if prefix else status == expected
    if not status_ok:
        invalid.append(
            {
                "path": relative(path),
                "reason": f"status={status!r}, expected={expected!r}",
            }
        )
    if model is not None and payload.get("model") != model:
        invalid.append(
            {
                "path": relative(path),
                "reason": f"model={payload.get('model')!r}, expected={model!r}",
            }
        )
    if schema_version is not None and payload.get("schema_version") != schema_version:
        invalid.append(
            {
                "path": relative(path),
                "reason": (
                    f"schema_version={payload.get('schema_version')!r}, "
                    f"expected={schema_version}"
                ),
            }
        )


def input_inventory() -> dict[str, Any]:
    groups: dict[str, Any] = {}
    missing_all: list[str] = []
    for name, paths in formal_groups().items():
        present = [relative(path) for path in paths if path.is_file()]
        missing = [relative(path) for path in paths if not path.is_file()]
        missing_all.extend(missing)
        groups[name] = {
            "required_files": len(paths),
            "present_files": len(present),
            "present": present,
            "missing": missing,
        }

    invalid: list[dict[str, str]] = []
    _status_check(
        SOURCE_DIR / "source_closure.json", EXPECTED_STATUS["source"], invalid
    )
    for model in ("a", "b"):
        _status_check(
            LINE_DIRS[model] / "summary.json",
            EXPECTED_STATUS["line"],
            invalid,
            model=model,
        )
        _status_check(
            CATALOG_DIRS[model] / "summary.json",
            EXPECTED_STATUS["catalog"],
            invalid,
            model=model,
            schema_version=2,
        )
        _status_check(
            CATALOG_DIRS[model] / "audit.json",
            EXPECTED_STATUS["catalog_audit"],
            invalid,
            model=model,
        )
        _status_check(
            TIMELINE_DIRS[model] / "summary.json",
            EXPECTED_STATUS["timeline"],
            invalid,
            model=model,
            schema_version=2,
        )
    _status_check(
        VALIDATION_PATH,
        "PASS__FLUXCLOSED_RESULTS_VALIDATED__",
        invalid,
        prefix=True,
        schema_version=1,
    )

    output_collision = OUTPUT_DIR.exists()
    if missing_all:
        status = "WAITING_FOR_FORMAL_INPUTS"
    elif invalid:
        status = "BLOCKED_INVALID_FORMAL_INPUTS"
    elif output_collision:
        status = "BLOCKED_NONOVERWRITE_OUTPUT_EXISTS"
    else:
        status = "READY_FOR_PUBLICATION_VALUE_BUILD"
    return {
        "schema_version": 1,
        "status": status,
        "ready": status == "READY_FOR_PUBLICATION_VALUE_BUILD",
        "package": str(PACKAGE),
        "formal_groups": groups,
        "missing": missing_all,
        "invalid": invalid,
        "nonoverwrite_output": relative(OUTPUT_DIR),
        "output_exists": output_collision,
        "side_effects": {
            "formal_inputs_modified": False,
            "output_created": False,
            "transport_started": False,
        },
    }


def validate_statuses(
    source: Mapping[str, Any],
    lines: Mapping[str, Mapping[str, Any]],
    catalogs: Mapping[str, Mapping[str, Any]],
    audits: Mapping[str, Mapping[str, Any]],
    timelines: Mapping[str, Mapping[str, Any]],
    validation: Mapping[str, Any],
) -> None:
    require(source.get("status") == EXPECTED_STATUS["source"], "source not COMPLETE")
    require(source.get("mono511_target", {}).get("rows") == 6480, "source lacks 81x80 target")
    require(
        source.get("mono511_target", {}).get("trajectory_nodes") == 81,
        "source target does not have 81 nodes",
    )
    require(
        source.get("mono511_target", {}).get("angular_bins_per_node") == 80,
        "source target does not have 80 angular bins",
    )
    for model in ("a", "b"):
        require(lines[model].get("status") == EXPECTED_STATUS["line"], f"line-{model} not COMPLETE")
        require(lines[model].get("model") == model, f"line-{model} model differs")
        require(catalogs[model].get("status") == EXPECTED_STATUS["catalog"], f"catalog-{model} not COMPLETE")
        require(catalogs[model].get("model") == model, f"catalog-{model} model differs")
        require(catalogs[model].get("schema_version") == 2, f"catalog-{model} schema is not 2")
        require(audits[model].get("status") == EXPECTED_STATUS["catalog_audit"], f"catalog-{model} audit not PASS")
        require(audits[model].get("model") == model, f"catalog-{model} audit model differs")
        require(timelines[model].get("status") == EXPECTED_STATUS["timeline"], f"timeline-{model} not PASS")
        require(timelines[model].get("model") == model, f"timeline-{model} model differs")
        require(timelines[model].get("schema_version") == 2, f"timeline-{model} schema is not 2")
    require(
        str(validation.get("status", "")).startswith(
            "PASS__FLUXCLOSED_RESULTS_VALIDATED__"
        ),
        "04 validation status is not PASS",
    )
    require(validation.get("schema_version") == 1, "04 validation schema is not 1")
    require(set(validation.get("model_decisions", {})) == {"a", "b"}, "04 lacks A/B decisions")


def compute_input_hashes() -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for group, paths in formal_groups().items():
        result[group] = {path.name: sha256_file(path) for path in paths}
    return result


def validate_hash_chain(
    validation: Mapping[str, Any], hashes: Mapping[str, Mapping[str, str]]
) -> None:
    sections = validation.get("validation", {})
    authority: dict[str, Mapping[str, str]] = {
        "00_source_closure": sections.get("source_closure", {}).get("hashes", {}),
        "01_line_response_a": sections.get("line_response", {}).get("a", {}).get("hashes", {}),
        "01_line_response_b": sections.get("line_response", {}).get("b", {}).get("hashes", {}),
        "02_fluxclosed_catalog_a": sections.get("catalogs", {}).get("a", {}).get("hashes", {}),
        "02_fluxclosed_catalog_b": sections.get("catalogs", {}).get("b", {}).get("hashes", {}),
        "03_fluxclosed_timeline_a": sections.get("timelines", {}).get("a", {}).get("hashes", {}),
        "03_fluxclosed_timeline_b": sections.get("timelines", {}).get("b", {}).get("hashes", {}),
    }
    for group, recorded in authority.items():
        require(recorded, f"04 validation lacks recorded hashes for {group}")
        for filename, actual in hashes[group].items():
            require(filename in recorded, f"04 validation lacks {group}/{filename} hash")
            require(
                recorded[filename] == actual,
                f"post-validation mutation detected: {group}/{filename}",
            )
    validator = validation.get("validator", {})
    require(validator.get("raw_SIM_files_opened") == 0, "validator opened raw SIM files")
    require(validator.get("transport_started") is False, "validator started transport")
    require(
        validator.get("sha256") == sha256_file(VALIDATOR_PATH),
        "04 was not produced by the current validator",
    )


def source_values(source: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    target = source["mono511_target"]
    proposal = source["proposal_denominator"]
    reference = source["source_reference_closure"]
    policy = source["trajectory_component_policy"]
    require(number(target["solar_modulation_W_MV"], "target W") == 118.3, "target W is not 118.3")
    require(number(target["local_geometry_g"], "target g") == 0.0, "target g is not 0")
    require(number(proposal["solar_modulation_W_MV"], "proposal W") == 114.6, "proposal W is not 114.6")
    require(number(proposal["local_geometry_g"], "proposal g") == 0.15, "proposal g is not 0.15")
    require(number(reference["local_geometry_g"], "reference g") == 0.0, "reference g is not 0")
    broadband = number(reference["broadband_reference_flux_ph_cm2_s"], "broadband flux")
    removed = number(reference["removed_coarse_line_reference_flux_ph_cm2_s"], "removed line flux")
    continuum = number(reference["continuum_reference_flux_ph_cm2_s"], "continuum flux")
    mono = number(reference["official_mono511_w118p3_reference_flux_ph_cm2_s"], "official mono flux")
    recomposed = number(reference["recomposed_continuum_plus_physical_line_flux_ph_cm2_s"], "recomposed flux")
    delta = number(reference["representation_delta_ph_cm2_s"], "representation delta")
    close(continuum, broadband - removed, "source exact coarse subtraction")
    close(recomposed, continuum + mono, "source physical recomposition")
    close(delta, recomposed - broadband, "source representation delta")
    require(number(target["minimum_importance_ratio"], "line importance min") >= 0.0, "negative line importance")
    require(number(source["coarse_line"]["minimum_event_importance_ratio_Jcont_over_Jtotal"], "continuum importance min") >= 0.0, "negative continuum importance")
    require(number(source["coarse_line"]["maximum_event_importance_ratio_Jcont_over_Jtotal"], "continuum importance max") <= 1.0 + 2e-15, "continuum importance exceeds one")
    require(policy.get("recomposition") == "continuum plus physical mono line; old broadband total is not enforced", "source recomposition policy differs")

    values = {
        "target_state": {
            "solar_modulation_W_MV": 118.3,
            "local_geometry_g": 0.0,
            "trajectory_nodes": 81,
            "angular_bins_per_node": 80,
            "line_energy_MeV": number(target["line_energy_MeV"], "line energy"),
        },
        "proposal_state": {
            "solar_modulation_W_MV": 114.6,
            "local_geometry_g": 0.15,
            "integrated_flux_ph_cm2_s": number(proposal["integrated_flux_ph_cm2_s"], "proposal flux"),
        },
        "reference_fluxes_ph_cm2_s": {
            "original_broadband": broadband,
            "removed_coarse_line": removed,
            "continuum": continuum,
            "official_mono511": mono,
            "recomposed_gamma": recomposed,
            "representation_delta": delta,
        },
        "importance_ranges": {
            "continuum_Jcont_over_Jtotal_min": number(source["coarse_line"]["minimum_event_importance_ratio_Jcont_over_Jtotal"], "continuum importance min"),
            "continuum_Jcont_over_Jtotal_max": number(source["coarse_line"]["maximum_event_importance_ratio_Jcont_over_Jtotal"], "continuum importance max"),
            "mono_target_over_proposal_min": number(target["minimum_importance_ratio"], "line importance min"),
            "mono_target_over_proposal_max": number(target["maximum_importance_ratio"], "line importance max"),
        },
        "reference_state_caveat": (
            "The physical mono target and de-lined reference are W=118.3, g=0; "
            "the transported line proposal is W=114.6, g=0.15, and the retained "
            "continuum trajectory scale has W_index=114.6. Importance weighting "
            "maps the line proposal to the target; no old-total renormalization is used."
        ),
    }
    row = {
        "target_W_MV": 118.3,
        "target_g": 0.0,
        "proposal_W_MV": 114.6,
        "proposal_g": 0.15,
        "proposal_flux_ph_cm2_s": values["proposal_state"]["integrated_flux_ph_cm2_s"],
        "original_broadband_flux_ph_cm2_s": broadband,
        "removed_coarse_line_flux_ph_cm2_s": removed,
        "continuum_flux_ph_cm2_s": continuum,
        "official_mono511_flux_ph_cm2_s": mono,
        "recomposed_gamma_flux_ph_cm2_s": recomposed,
        "representation_delta_ph_cm2_s": delta,
        "continuum_importance_min": values["importance_ranges"]["continuum_Jcont_over_Jtotal_min"],
        "continuum_importance_max": values["importance_ranges"]["continuum_Jcont_over_Jtotal_max"],
        "line_importance_min": values["importance_ranges"]["mono_target_over_proposal_min"],
        "line_importance_max": values["importance_ranges"]["mono_target_over_proposal_max"],
        "trajectory_nodes": 81,
        "angular_bins_per_node": 80,
    }
    return values, row


def validate_catalog_summary(
    model: str,
    line: Mapping[str, Any],
    summary: Mapping[str, Any],
    audit: Mapping[str, Any],
) -> dict[str, Any]:
    components = summary.get("components", {})
    require(set(components) == set(COMPONENTS), f"catalog-{model} components differ")
    events_sum = 0
    for component in COMPONENTS:
        item = components[component]
        events = integer(item["events"], f"catalog-{model}.{component}.events")
        sumw = number(item["sumw_cps"], f"catalog-{model}.{component}.sumw")
        sumw2 = number(item["sumw2_cps2"], f"catalog-{model}.{component}.sumw2")
        ess = number(item["effective_sample_size"], f"catalog-{model}.{component}.ESS")
        require(events > 0 and sumw > 0.0 and sumw2 > 0.0, f"catalog-{model}.{component} non-positive")
        close(ess, sumw * sumw / sumw2, f"catalog-{model}.{component} ESS")
        events_sum += events
    require(events_sum == integer(summary["events"], f"catalog-{model}.events"), f"catalog-{model} event count does not add")
    detector_positive = integer(line["detector_positive_events"], f"line-{model}.detector positive")
    require(integer(summary["line_detector_positive_events"], f"catalog-{model}.line events") == detector_positive, f"catalog-{model} line count differs from 01")
    require(integer(components["atm511"]["events"], f"catalog-{model}.atm511 events") == detector_positive, f"catalog-{model} atm511 count differs")
    gamma_join = audit.get("gamma_join", {})
    close(number(gamma_join["matching_rate"], f"catalog-{model} gamma matching"), 1.0, f"catalog-{model} gamma matching")
    require(number(gamma_join["minimum_continuum_importance_weight"], f"catalog-{model} continuum min") >= 0.0, f"catalog-{model} negative continuum importance")
    require(number(gamma_join["maximum_continuum_importance_weight"], f"catalog-{model} continuum max") <= 1.0 + 2e-15, f"catalog-{model} continuum importance exceeds one")
    return {
        "events": integer(summary["events"], f"catalog-{model}.events"),
        "hits": integer(summary["hits"], f"catalog-{model}.hits"),
        "categories": integer(summary["categories"], f"catalog-{model}.categories"),
        "components": components,
        "continuum_weight_contract": (
            "event_base_weight_cps already equals proposal_event_weight_cps "
            "times J_cont/J_total; downstream must not apply importance again"
        ),
        "gamma_IA_INIT_matching_rate": number(gamma_join["matching_rate"], f"catalog-{model} gamma matching"),
    }


def extract_model_values(
    model: str,
    line: Mapping[str, Any],
    catalog: Mapping[str, Any],
    audit: Mapping[str, Any],
    timeline: Mapping[str, Any],
    validation: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    candidate = str(timeline.get("candidate", ""))
    require(candidate, f"timeline-{model} lacks candidate")
    catalog_values = validate_catalog_summary(model, line, catalog, audit)

    anchor_path = TIMELINE_DIRS[model] / "anchor_timeline_rates.csv"
    anchor_component_path = TIMELINE_DIRS[model] / "anchor_transport_components.csv"
    mission_path = TIMELINE_DIRS[model] / "mission_timeline_81nodes.csv"
    mission_component_path = TIMELINE_DIRS[model] / "mission_transport_components.csv"
    anchor_rows_all = read_csv(anchor_path)
    anchor_component_rows_all = read_csv(anchor_component_path)
    mission_rows = read_csv(mission_path)
    mission_component_rows = read_csv(mission_component_path)

    require(len(anchor_rows_all) == 50, f"timeline-{model} anchor rate rows != 50")
    require(len(anchor_component_rows_all) == 150, f"timeline-{model} anchor component rows != 150")
    require(len(mission_rows) == 81, f"timeline-{model} mission rows != 81")
    require(len(mission_component_rows) == 4, f"timeline-{model} mission component rows != 4")
    anchor_map = keyed_rows(anchor_rows_all, ("time_bin_id", "window_id", "stage"), f"timeline-{model} anchor rates")
    anchor_component_map = keyed_rows(anchor_component_rows_all, ("time_bin_id", "window_id", "stage", "component"), f"timeline-{model} anchor components")

    anchor_rows: list[dict[str, Any]] = []
    summary_anchors = timeline.get("anchors", {})
    for node in ANCHOR_NODES:
        key = (node, FINAL_WINDOW, FINAL_STAGE)
        require(key in anchor_map, f"timeline-{model} lacks final anchor {node}")
        row = anchor_map[key]
        summary_anchor = summary_anchors.get(str(node))
        require(isinstance(summary_anchor, Mapping), f"timeline-{model} summary lacks anchor {node}")
        ratio = row_float(row, "timeline_to_direct_ratio", f"anchor-{model}-{node}")
        ratio_error = row_float(row, "timeline_rate_standard_error_cps", f"anchor-{model}-{node}") / row_float(row, "direct_no_coincidence_rate_cps", f"anchor-{model}-{node}")
        close(ratio, number(summary_anchor["timeline_to_direct_ratio"], f"summary anchor-{model}-{node} ratio"), f"anchor-{model}-{node} ratio")
        close(ratio_error, number(summary_anchor["timeline_to_direct_ratio_standard_error"], f"summary anchor-{model}-{node} ratio error"), f"anchor-{model}-{node} ratio error")
        probe = summary_anchor["signal_probe"]
        survival = row_float(row, "signal_accidental_survival", f"anchor-{model}-{node}")
        survival_error = row_float(row, "signal_survival_standard_error", f"anchor-{model}-{node}")
        close(survival, number(probe["conditional_signal_accidental_survival"], f"anchor-{model}-{node} survival"), f"anchor-{model}-{node} survival")
        close(survival_error, number(probe["binomial_standard_error"], f"anchor-{model}-{node} survival error"), f"anchor-{model}-{node} survival error")
        direct_rate = row_float(row, "direct_no_coincidence_rate_cps", f"anchor-{model}-{node}")
        direct_sumw2 = row_float(row, "direct_sum_W_i2_cps2", f"anchor-{model}-{node}")
        direct_sigma = row_float(
            row, "direct_transport_sigma_cps", f"anchor-{model}-{node}"
        )
        direct_ess = row_float(row, "direct_transport_effective_sample_size", f"anchor-{model}-{node}")
        close(direct_sigma, math.sqrt(direct_sumw2), f"anchor-{model}-{node} sigma")
        close(direct_ess, direct_rate * direct_rate / direct_sumw2, f"anchor-{model}-{node} ESS")
        output_row: dict[str, Any] = {
            "model": model,
            **MODEL_LABELS[model],
            "candidate": candidate,
            "time_bin_id": node,
            "day_mid": row_float(row, "day_mid", f"anchor-{model}-{node}"),
            "window_id": FINAL_WINDOW,
            "stage": FINAL_STAGE,
            "direct_rate_cps": direct_rate,
            "direct_sumw2_cps2": direct_sumw2,
            "direct_transport_sigma_cps": direct_sigma,
            "direct_transport_ESS": direct_ess,
            "direct_selected_raw": row_int(row, "direct_selected_raw", f"anchor-{model}-{node}"),
            "timeline_counts": row_int(row, "timeline_counts", f"anchor-{model}-{node}"),
            "timeline_rate_cps": row_float(row, "timeline_rate_cps", f"anchor-{model}-{node}"),
            "timeline_rate_standard_error_cps": row_float(row, "timeline_rate_standard_error_cps", f"anchor-{model}-{node}"),
            "timeline_to_direct_ratio": ratio,
            "timeline_to_direct_ratio_standard_error": ratio_error,
            "signal_accidental_survival": survival,
            "signal_survival_standard_error": survival_error,
        }
        component_rate_sum = 0.0
        component_sumw2_sum = 0.0
        component_selected_sum = 0
        for component in COMPONENTS:
            component_key = (node, FINAL_WINDOW, FINAL_STAGE, component)
            require(component_key in anchor_component_map, f"timeline-{model} lacks {component} anchor {node}")
            item = anchor_component_map[component_key]
            prefix = component
            component_rate = row_float(item, "direct_rate_cps", f"anchor-{model}-{node}-{component}")
            component_sumw2 = row_float(item, "direct_sum_W_i2_cps2", f"anchor-{model}-{node}-{component}")
            component_sigma = row_float(
                item,
                "direct_transport_sigma_cps",
                f"anchor-{model}-{node}-{component}",
            )
            component_ess = row_float(item, "direct_transport_effective_sample_size", f"anchor-{model}-{node}-{component}")
            close(
                component_sigma,
                math.sqrt(component_sumw2),
                f"anchor-{model}-{node}-{component} sigma",
            )
            close(component_ess, component_rate * component_rate / component_sumw2, f"anchor-{model}-{node}-{component} ESS")
            selected = row_int(item, "selected_raw", f"anchor-{model}-{node}-{component}")
            output_row[f"{prefix}_rate_cps"] = component_rate
            output_row[f"{prefix}_sumw2_cps2"] = component_sumw2
            output_row[f"{prefix}_transport_sigma_cps"] = component_sigma
            output_row[f"{prefix}_transport_ESS"] = component_ess
            output_row[f"{prefix}_selected_raw"] = selected
            component_rate_sum += component_rate
            component_sumw2_sum += component_sumw2
            component_selected_sum += selected
        close(component_rate_sum, direct_rate, f"anchor-{model}-{node} component rate closure")
        close(component_sumw2_sum, direct_sumw2, f"anchor-{model}-{node} component sumw2 closure")
        require(component_selected_sum == output_row["direct_selected_raw"], f"anchor-{model}-{node} selected closure")
        anchor_rows.append(output_row)

    day15 = timeline.get("day15_W2_final_component_rates", {})
    require(set(day15) == set(ALL_COMPONENTS), f"timeline-{model} day15 components differ")
    day15_rows: list[dict[str, Any]] = []
    named_rate = 0.0
    named_sumw2 = 0.0
    named_selected = 0
    for component in ALL_COMPONENTS:
        item = day15[component]
        rate = number(item["rate_cps"], f"day15-{model}-{component} rate")
        sumw2 = number(item["sum_wi2_cps2"], f"day15-{model}-{component} sumw2")
        sigma = number(item["transport_sigma_cps"], f"day15-{model}-{component} sigma")
        ess = number(item["effective_sample_size"], f"day15-{model}-{component} ESS")
        selected = integer(item["selected_raw"], f"day15-{model}-{component} selected")
        close(sigma, math.sqrt(sumw2), f"day15-{model}-{component} sigma")
        close(ess, rate * rate / sumw2, f"day15-{model}-{component} ESS")
        if component == "total":
            authority = anchor_map[(60, FINAL_WINDOW, FINAL_STAGE)]
            authority_rate = row_float(
                authority,
                "direct_no_coincidence_rate_cps",
                f"day15-anchor-{model}-total",
            )
            authority_sumw2 = row_float(
                authority,
                "direct_sum_W_i2_cps2",
                f"day15-anchor-{model}-total",
            )
            authority_selected = row_int(
                authority, "direct_selected_raw", f"day15-anchor-{model}-total"
            )
        else:
            authority = anchor_component_map[
                (60, FINAL_WINDOW, FINAL_STAGE, component)
            ]
            authority_rate = row_float(
                authority, "direct_rate_cps", f"day15-anchor-{model}-{component}"
            )
            authority_sumw2 = row_float(
                authority,
                "direct_sum_W_i2_cps2",
                f"day15-anchor-{model}-{component}",
            )
            authority_selected = row_int(
                authority,
                "selected_raw",
                f"day15-anchor-{model}-{component}",
            )
        close(rate, authority_rate, f"day15-{model}-{component} anchor rate")
        close(sumw2, authority_sumw2, f"day15-{model}-{component} anchor sumw2")
        require(
            selected == authority_selected,
            f"day15-{model}-{component} anchor selected differs",
        )
        day15_rows.append(
            {
                "model": model,
                **MODEL_LABELS[model],
                "candidate": candidate,
                "day_mid": 15.0,
                "window_id": FINAL_WINDOW,
                "stage": FINAL_STAGE,
                "component": component,
                "selected_raw": selected,
                "rate_cps": rate,
                "sumw2_cps2": sumw2,
                "transport_sigma_cps": sigma,
                "transport_ESS": ess,
            }
        )
        if component != "total":
            named_rate += rate
            named_sumw2 += sumw2
            named_selected += selected
    total_day15 = day15["total"]
    close(named_rate, number(total_day15["rate_cps"], f"day15-{model} total rate"), f"day15-{model} component rate closure")
    close(named_sumw2, number(total_day15["sum_wi2_cps2"], f"day15-{model} total sumw2"), f"day15-{model} component sumw2 closure")
    require(named_selected == integer(total_day15["selected_raw"], f"day15-{model} total selected"), f"day15-{model} component selected closure")

    require_columns(mission_rows, ("time_bin_id", "day_mid", "cumulative_background_counts", "cumulative_signal_counts_per_unit_flux", *FMIN_KEYS), f"timeline-{model} mission")
    for expected_node, row in enumerate(mission_rows):
        require(row_int(row, "time_bin_id", f"mission-{model}") == expected_node, f"timeline-{model} mission node axis differs")
        close(row_float(row, "day_mid", f"mission-{model}-{expected_node}"), expected_node / 4.0, f"timeline-{model} day axis")
    final = mission_rows[-1]
    background = row_float(final, "cumulative_background_counts", f"mission-{model}-final")
    kernel = row_float(final, "cumulative_signal_counts_per_unit_flux", f"mission-{model}-final")
    expected = expected_fmin(background, kernel)
    uncertainty = timeline.get("statistical_uncertainty", {})
    fmin_uncertainty = uncertainty.get("Fmin", {})
    require(set(fmin_uncertainty) == set(FMIN_KEYS), f"timeline-{model} Fmin keys differ")
    fmin_values: dict[str, dict[str, float]] = {}
    for key in FMIN_KEYS:
        csv_value = row_float(final, key, f"mission-{model}-final")
        recorded = fmin_uncertainty[key]
        value = number(recorded["value"], f"timeline-{model}.{key}.value")
        error = number(recorded["standard_error"], f"timeline-{model}.{key}.error")
        rse = number(recorded["relative_standard_error"], f"timeline-{model}.{key}.RSE")
        close(csv_value, expected[key], f"timeline-{model} recomputed {key}", atol=2e-13)
        close(value, csv_value, f"timeline-{model} summary {key}", atol=2e-13)
        close(rse, error / value, f"timeline-{model} {key} RSE", atol=2e-13)
        fmin_values[key] = {
            "value_ph_cm2_s": value,
            "standard_error_ph_cm2_s": error,
            "relative_standard_error": rse,
        }

    summary_final = timeline.get("mission_final_20day", {})
    for key in (
        "cumulative_background_counts",
        "cumulative_signal_counts_per_unit_flux",
        "cumulative_transport_sum_W_i2_counts2",
        "cumulative_transport_sigma_counts",
        "cumulative_transport_effective_sample_size",
        "conditional_signal_Aeff_cm2",
        "conditional_signal_kernel_cm2",
        "conditional_signal_accidental_survival",
        "T_atm_511_slant45",
        *FMIN_KEYS,
    ):
        close(number(summary_final[key], f"timeline-{model}.mission_final.{key}"), row_float(final, key, f"mission-{model}-final"), f"timeline-{model} final {key}", atol=2e-8 if "cumulative" in key else 2e-13)

    mission_component_map = {
        str(row["component"]): row for row in mission_component_rows
    }
    require(set(mission_component_map) == set(ALL_COMPONENTS), f"timeline-{model} mission components differ")
    mission_components: dict[str, dict[str, Any]] = {}
    for component in ALL_COMPONENTS:
        row = mission_component_map[component]
        count = row_float(row, "integrated_background_counts", f"mission-{model}-{component}")
        sumw2 = row_float(row, "sum_W_i2_counts2", f"mission-{model}-{component}")
        sigma = row_float(row, "transport_sigma_counts", f"mission-{model}-{component}")
        ess = row_float(row, "transport_effective_sample_size", f"mission-{model}-{component}")
        selected = row_int(row, "selected_raw", f"mission-{model}-{component}")
        close(sigma, math.sqrt(sumw2), f"mission-{model}-{component} sigma", atol=2e-8)
        close(ess, count * count / sumw2, f"mission-{model}-{component} ESS")
        mission_components[component] = {
            "selected_raw": selected,
            "integrated_background_counts": count,
            "sumw2_counts2": sumw2,
            "transport_sigma_counts": sigma,
            "transport_ESS": ess,
        }
        summary_component = timeline.get("mission_transport_components", {}).get(
            component
        )
        require(
            isinstance(summary_component, Mapping),
            f"timeline-{model} summary lacks mission component {component}",
        )
        require(
            integer(
                summary_component["selected_raw"],
                f"timeline-{model} summary {component} selected",
            )
            == selected,
            f"timeline-{model} summary {component} selected differs",
        )
        for field, actual in (
            ("integrated_background_counts", count),
            ("sum_W_i2_counts2", sumw2),
            ("transport_sigma_counts", sigma),
            ("transport_effective_sample_size", ess),
        ):
            close(
                number(
                    summary_component[field],
                    f"timeline-{model} summary {component}.{field}",
                ),
                actual,
                f"timeline-{model} summary {component}.{field}",
                atol=2e-6,
            )
    close(sum(mission_components[c]["integrated_background_counts"] for c in COMPONENTS), background, f"mission-{model} component B closure", atol=2e-6)
    close(sum(mission_components[c]["sumw2_counts2"] for c in COMPONENTS), mission_components["total"]["sumw2_counts2"], f"mission-{model} component sumw2 closure", atol=2e-6)
    require(sum(mission_components[c]["selected_raw"] for c in COMPONENTS) == mission_components["total"]["selected_raw"], f"mission-{model} component selected closure")

    topup = validation["model_decisions"][model]
    require(topup.get("model") == model, f"04 topup model-{model} differs")
    require(topup.get("decision") in {"NO_TOPUP", "TOPUP_REQUIRED", "LINE_TOPUP_NOT_BENEFICIAL"}, f"04 topup decision-{model} invalid")
    line_incident = integer(line["incident_photons"], f"line-{model} incident")
    line_positive = integer(line["detector_positive_events"], f"line-{model} positive")
    line_selected = integer(line["w2_final_selected_events"], f"line-{model} selected")
    require(integer(topup["line_incident_photons"], f"topup-{model} incident") == line_incident, f"topup-{model} incident differs")
    require(integer(topup["line_detector_positive_events"], f"topup-{model} positive") == line_positive, f"topup-{model} positive differs")
    require(integer(topup["line_final_selected_events"], f"topup-{model} selected") == line_selected, f"topup-{model} selected differs")
    require(mission_components["atm511"]["selected_raw"] == line_selected, f"mission-{model} line selected differs")
    close(number(topup["integrated_line_background_counts"], f"topup-{model} line B"), mission_components["atm511"]["integrated_background_counts"], f"topup-{model} line B", atol=2e-6)
    close(number(topup["integrated_line_sumw2_counts2"], f"topup-{model} line sumw2"), mission_components["atm511"]["sumw2_counts2"], f"topup-{model} line sumw2", atol=2e-6)
    close(number(topup["integrated_line_effective_sample_size"], f"topup-{model} line ESS"), mission_components["atm511"]["transport_ESS"], f"topup-{model} line ESS")
    gate = topup.get("publication_precision_gate", {})
    require(gate.get("decision_authority") is True, f"topup-{model} publication gate is not authoritative")
    require(gate.get("decision") == topup.get("decision"), f"topup-{model} gate decision differs")
    close(number(gate["thresholds"]["total_MC_relative_standard_error_max"], f"topup-{model} RSE threshold"), 0.10, f"topup-{model} RSE threshold")
    close(number(gate["thresholds"]["line_Fmin_variance_fraction_max"], f"topup-{model} variance threshold"), 0.50, f"topup-{model} line variance threshold")
    legacy = topup.get("legacy_last_digit_diagnostic", {})
    require(legacy.get("decision_authority") is False, f"topup-{model} legacy diagnostic became authoritative")

    report_timeline = validation["validation"]["timelines"][model]
    close(number(report_timeline["final_background_counts"], f"04 timeline-{model} B"), background, f"04 timeline-{model} B", atol=2e-6)
    close(number(report_timeline["final_signal_counts_per_unit_flux"], f"04 timeline-{model} K"), kernel, f"04 timeline-{model} K", atol=2e-6)
    report_line = validation["validation"]["line_response"][model]
    require(
        integer(report_line["incident_photons"], f"04 line-{model} incident")
        == line_incident,
        f"04 line-{model} incident differs",
    )
    require(
        integer(
            report_line["detector_positive_events"],
            f"04 line-{model} detector positive",
        )
        == line_positive,
        f"04 line-{model} detector-positive count differs",
    )
    require(integer(report_line["final_selected_events"], f"04 line-{model} selected") == line_selected, f"04 line-{model} selected differs")
    close(
        number(report_line["final_rate_cps"], f"04 line-{model} final rate"),
        number(line["w2_final_rate_cps"], f"line-{model} final rate"),
        f"04 line-{model} final rate",
    )
    require(
        str(report_line["geometry_setup"]) == str(line["geometry_setup"]),
        f"04 line-{model} geometry differs",
    )
    report_catalog = validation["validation"]["catalogs"][model]
    require(report_catalog.get("status") == "PASS__CATALOG_SCHEMA_POSITIVE_WEIGHTS_SUMW2_ESS", f"04 catalog-{model} validation not PASS")

    line_base_sigma = number(line["w2_final_mc_sigma_cps"], f"line-{model} base sigma")
    line_base_sumw2 = line_base_sigma * line_base_sigma
    line_base_rate = number(line["w2_final_rate_cps"], f"line-{model} base rate")
    line_base_ess = number(line["w2_final_effective_sample_size"], f"line-{model} base ESS")
    close(line_base_ess, line_base_rate * line_base_rate / line_base_sumw2, f"line-{model} base ESS")

    mission = {
        "mission_day": 20.0,
        "cumulative_background_counts_B": background,
        "cumulative_signal_counts_per_unit_flux_K": kernel,
        "transport_sumw2_counts2": row_float(final, "cumulative_transport_sum_W_i2_counts2", f"mission-{model}-final"),
        "transport_sigma_counts": row_float(final, "cumulative_transport_sigma_counts", f"mission-{model}-final"),
        "transport_ESS": row_float(final, "cumulative_transport_effective_sample_size", f"mission-{model}-final"),
        "background_combined_sigma_counts": number(uncertainty["background_combined_sigma_counts"], f"timeline-{model} background sigma"),
        "background_combined_relative_sigma": number(uncertainty["background_combined_relative_sigma"], f"timeline-{model} background RSE"),
        "signal_Aeff_cm2": row_float(final, "conditional_signal_Aeff_cm2", f"mission-{model}-final"),
        "signal_kernel_cm2": row_float(final, "conditional_signal_kernel_cm2", f"mission-{model}-final"),
        "signal_accidental_survival": row_float(final, "conditional_signal_accidental_survival", f"mission-{model}-final"),
        "atmospheric_transmission_slant45": row_float(final, "T_atm_511_slant45", f"mission-{model}-final"),
        "signal_combined_relative_sigma": number(uncertainty["signal_combined_relative_sigma"], f"timeline-{model} signal RSE"),
        "Fmin": fmin_values,
        "components": mission_components,
    }
    line_values = {
        "geometry_setup": str(line["geometry_setup"]),
        "incident_photons": line_incident,
        "detector_positive_events": line_positive,
        "physical_exposure_s": number(line["physical_exposure_s"], f"line-{model} exposure"),
        "proposal_event_weight_cps": number(line["event_weight_cps"], f"line-{model} event weight"),
        "final_selected_events": line_selected,
        "proposal_day15_final_rate_cps": line_base_rate,
        "proposal_day15_final_sumw2_cps2": line_base_sumw2,
        "proposal_day15_final_transport_sigma_cps": line_base_sigma,
        "proposal_day15_final_ESS": line_base_ess,
        "mission_integrated_background_counts": mission_components["atm511"]["integrated_background_counts"],
        "mission_integrated_sumw2_counts2": mission_components["atm511"]["sumw2_counts2"],
        "mission_integrated_transport_sigma_counts": mission_components["atm511"]["transport_sigma_counts"],
        "mission_integrated_ESS": mission_components["atm511"]["transport_ESS"],
    }
    topup_values = {
        "decision": topup["decision"],
        "required_total_incident_photons": topup.get("required_total_incident_photons"),
        "additional_incident_photons": topup.get("additional_incident_photons"),
        "publication_precision_gate": gate,
        "legacy_last_digit_diagnostic": legacy,
        "Fmin_line_MC_contributions": topup["Fmin_line_MC_contributions"],
        "physical_PARMA_flux_systematic": validation["uncertainty_scope"]["excluded"]["physical_PARMA_flux_systematic"],
    }
    model_values = {
        "model": model,
        **MODEL_LABELS[model],
        "candidate": candidate,
        "catalog": catalog_values,
        "line_response": line_values,
        "five_anchors": anchor_rows,
        "day15_W2_final_components": {row["component"]: {key: value for key, value in row.items() if key not in {"model", "label_en", "label_zh", "candidate", "day_mid", "window_id", "stage", "component"}} for row in day15_rows},
        "mission_20day": mission,
        "topup": topup_values,
    }

    model_row: dict[str, Any] = {
        "model": model,
        **MODEL_LABELS[model],
        "candidate": candidate,
        "day15_total_W2_rate_cps": number(total_day15["rate_cps"], f"day15-{model} total rate"),
        "day15_total_W2_sumw2_cps2": number(total_day15["sum_wi2_cps2"], f"day15-{model} total sumw2"),
        "day15_total_W2_transport_sigma_cps": number(total_day15["transport_sigma_cps"], f"day15-{model} total sigma"),
        "day15_total_W2_transport_ESS": number(total_day15["effective_sample_size"], f"day15-{model} total ESS"),
        "cumulative_background_counts_B": background,
        "cumulative_signal_counts_per_unit_flux_K": kernel,
        "background_combined_sigma_counts": mission["background_combined_sigma_counts"],
        "background_combined_relative_sigma": mission["background_combined_relative_sigma"],
        "signal_Aeff_cm2": mission["signal_Aeff_cm2"],
        "signal_kernel_cm2": mission["signal_kernel_cm2"],
        "signal_combined_relative_sigma": mission["signal_combined_relative_sigma"],
        "line_incident_photons": line_incident,
        "line_detector_positive_events": line_positive,
        "line_final_selected_events": line_selected,
        "line_mission_integrated_counts": line_values["mission_integrated_background_counts"],
        "line_mission_integrated_sumw2_counts2": line_values["mission_integrated_sumw2_counts2"],
        "line_mission_integrated_transport_sigma_counts": line_values["mission_integrated_transport_sigma_counts"],
        "line_mission_integrated_ESS": line_values["mission_integrated_ESS"],
        "topup_decision": topup["decision"],
        "required_total_line_incident_photons": topup.get("required_total_incident_photons"),
        "additional_line_incident_photons": topup.get("additional_incident_photons"),
        "line_MC_relative_sigma_on_total_B": number(
            topup["line_MC_relative_sigma_on_total_B"],
            f"topup-{model} line relative sigma on B",
        ),
        "Gaussian_3sigma_total_MC_relative_standard_error": number(
            gate["current"]["total_MC_relative_standard_error"],
            f"topup-{model} total Fmin RSE",
        ),
        "Gaussian_3sigma_line_Fmin_variance_fraction": number(
            gate["current"]["line_Fmin_variance_fraction"],
            f"topup-{model} line Fmin variance fraction",
        ),
        "Gaussian_3sigma_line_sigma_to_rest_sigma": gate["current"].get(
            "line_sigma_to_rest_sigma"
        ),
    }
    for key in FMIN_KEYS:
        prefix = key.removesuffix("_ph_cm2_s")
        item = fmin_values[key]
        model_row[f"{prefix}_ph_cm2_s"] = item["value_ph_cm2_s"]
        model_row[f"{prefix}_standard_error_ph_cm2_s"] = item["standard_error_ph_cm2_s"]
        model_row[f"{prefix}_relative_standard_error"] = item["relative_standard_error"]
    return model_values, anchor_rows, day15_rows, model_row


def improvement_values(model_rows: Mapping[str, Mapping[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    a = model_rows["a"]
    b = model_rows["b"]
    rows: list[dict[str, Any]] = []

    def add(
        metric: str,
        numerator_model: str,
        numerator_field: str,
        denominator_model: str,
        denominator_field: str,
        interpretation: str,
    ) -> None:
        numerator = number(model_rows[numerator_model][numerator_field], f"improvement {metric} numerator")
        denominator = number(model_rows[denominator_model][denominator_field], f"improvement {metric} denominator")
        require(denominator > 0.0, f"improvement {metric} denominator is not positive")
        rows.append(
            {
                "metric": metric,
                "value": numerator / denominator,
                "numerator_model": numerator_model,
                "numerator_field": numerator_field,
                "numerator_value": numerator,
                "denominator_model": denominator_model,
                "denominator_field": denominator_field,
                "denominator_value": denominator,
                "interpretation": interpretation,
            }
        )

    add("day15_background_reduction_factor_A_over_B", "a", "day15_total_W2_rate_cps", "b", "day15_total_W2_rate_cps", "larger than 1 means Model B has a lower day-15 final W2 background rate")
    add("cumulative_background_reduction_factor_A_over_B", "a", "cumulative_background_counts_B", "b", "cumulative_background_counts_B", "larger than 1 means Model B has fewer 20-day cumulative background counts")
    for z_value in (3, 5):
        add(f"Gaussian_{z_value}sigma_Fmin_improvement_factor_A_over_B", "a", f"Fmin_{z_value}sigma_gaussian_ph_cm2_s", "b", f"Fmin_{z_value}sigma_gaussian_ph_cm2_s", "larger than 1 means Model B has a lower flux threshold")
        add(f"Poisson_Asimov_{z_value}sigma_Fmin_improvement_factor_A_over_B", "a", f"Fmin_{z_value}sigma_poisson_asimov_ph_cm2_s", "b", f"Fmin_{z_value}sigma_poisson_asimov_ph_cm2_s", "larger than 1 means Model B has a lower flux threshold")
    add("signal_kernel_retention_B_over_A", "b", "signal_kernel_cm2", "a", "signal_kernel_cm2", "fraction of Model A 20-day signal kernel retained by Model B")
    add("signal_Aeff_retention_B_over_A", "b", "signal_Aeff_cm2", "a", "signal_Aeff_cm2", "fraction of Model A conditional signal effective area retained by Model B")
    keyed = {row["metric"]: row for row in rows}
    require(len(keyed) == len(rows), "duplicate improvement metrics")
    return keyed, rows


def json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def csv_bytes(rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> bytes:
    require(bool(rows), "refusing to emit an empty CSV")
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(
        buffer,
        fieldnames=list(fields),
        lineterminator="\n",
        extrasaction="raise",
    )
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def build_payloads() -> tuple[dict[str, bytes], dict[str, Any]]:
    inventory = input_inventory()
    require(inventory["ready"], f"fail-closed input gate: {inventory['status']}")

    source = load_json(SOURCE_DIR / "source_closure.json")
    lines = {model: load_json(LINE_DIRS[model] / "summary.json") for model in ("a", "b")}
    catalogs = {model: load_json(CATALOG_DIRS[model] / "summary.json") for model in ("a", "b")}
    audits = {model: load_json(CATALOG_DIRS[model] / "audit.json") for model in ("a", "b")}
    timelines = {model: load_json(TIMELINE_DIRS[model] / "summary.json") for model in ("a", "b")}
    validation = load_json(VALIDATION_PATH)
    validate_statuses(source, lines, catalogs, audits, timelines, validation)

    input_hashes = compute_input_hashes()
    validate_hash_chain(validation, input_hashes)
    source_block, source_row = source_values(source)
    model_blocks: dict[str, Any] = {}
    model_rows: dict[str, dict[str, Any]] = {}
    anchor_rows: list[dict[str, Any]] = []
    day15_rows: list[dict[str, Any]] = []
    for model in ("a", "b"):
        block, anchors, day15, row = extract_model_values(
            model,
            lines[model],
            catalogs[model],
            audits[model],
            timelines[model],
            validation,
        )
        model_blocks[model] = block
        model_rows[model] = row
        anchor_rows.extend(anchors)
        day15_rows.extend(day15)
    require(len(anchor_rows) == 10, "publication anchor table does not have A/B x 5 rows")
    require(len(day15_rows) == 8, "publication day15 table does not have A/B x 4 rows")
    improvement_block, improvement_rows = improvement_values(model_rows)

    publication = {
        "schema_version": 1,
        "status": "PASS__PUBLICATION_VALUES_FLUXCLOSED_A_B",
        "scope": {
            "purpose": "machine-readable bilingual-manuscript and data-table values",
            "models": ["a", "b"],
            "anchor_nodes": list(ANCHOR_NODES),
            "mission_nodes": 81,
            "mission_day_range": [0.0, 20.0],
            "window_id": FINAL_WINDOW,
            "stage": FINAL_STAGE,
            "formal_input_stages": ["00", "01", "02", "03", "04"],
        },
        "source_closure": source_block,
        "models": model_blocks,
        "A_B_improvements": improvement_block,
        "topup_global_decision": validation["decision"],
        "topup_gate_definition": validation["topup_gate_definition"],
        "uncertainty_scope": validation["uncertainty_scope"],
        "publication_precision_policy": {
            "formal_gate": (
                "Gaussian 3-sigma Fmin total MC RSE <= 10% and line Fmin "
                "variance fraction <= 50%"
            ),
            "legacy_last_digit_diagnostic_is_informational_only": True,
            "physical_PARMA_flux_systematic": "EXCLUDED",
        },
        "hash_receipt": "receipt.json",
    }

    anchor_fields = list(anchor_rows[0])
    day15_fields = list(day15_rows[0])
    model_fields = list(model_rows["a"])
    improvement_fields = list(improvement_rows[0])
    source_fields = list(source_row)
    payloads = {
        "publication_values.json": json_bytes(publication),
        "source_closure_values.csv": csv_bytes([source_row], source_fields),
        "five_anchor_values.csv": csv_bytes(anchor_rows, anchor_fields),
        "day15_component_values.csv": csv_bytes(day15_rows, day15_fields),
        "model_summary_values.csv": csv_bytes([model_rows["a"], model_rows["b"]], model_fields),
        "ab_improvement_values.csv": csv_bytes(improvement_rows, improvement_fields),
    }

    input_manifest: list[dict[str, Any]] = []
    for group, paths in formal_groups().items():
        for path in paths:
            input_manifest.append(
                {
                    "group": group,
                    "path": relative(path),
                    "bytes": path.stat().st_size,
                    "sha256": input_hashes[group][path.name],
                }
            )
    output_manifest = [
        {
            "path": name,
            "bytes": len(payload),
            "sha256": sha256_bytes(payload),
        }
        for name, payload in sorted(payloads.items())
    ]
    receipt = {
        "schema_version": 1,
        "status": "PASS__HASH_RECEIPT__FORMAL_00_TO_04_MATCH_VALIDATION_AUTHORITY",
        "created_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "builder": {
            "path": relative(HERE),
            "sha256": sha256_file(HERE),
        },
        "validation_authority": {
            "path": relative(VALIDATION_PATH),
            "sha256": input_hashes["04_validation"][VALIDATION_PATH.name],
            "status": validation["status"],
            "decision": validation["decision"],
            "validator_path": relative(VALIDATOR_PATH),
            "validator_sha256": sha256_file(VALIDATOR_PATH),
        },
        "formal_inputs": input_manifest,
        "outputs_excluding_this_receipt": output_manifest,
        "receipt_self_hash_excluded": True,
        "side_effects": {
            "formal_inputs_modified": False,
            "raw_SIM_files_opened": 0,
            "transport_started": False,
            "timeline_started": False,
        },
    }
    payloads["receipt.json"] = json_bytes(receipt)
    summary = {
        "status": publication["status"],
        "output_dir": relative(OUTPUT_DIR),
        "files": {
            name: {"bytes": len(payload), "sha256": sha256_bytes(payload)}
            for name, payload in sorted(payloads.items())
        },
        "topup_global_decision": validation["decision"],
        "A_B_improvements": {
            key: value["value"] for key, value in improvement_block.items()
        },
    }
    return payloads, summary


def write_exclusive(payloads: Mapping[str, bytes]) -> None:
    require(OUTPUT_DIR.parent.resolve() == OUTPUTS.resolve(), "output parent escaped package 67")
    require(not OUTPUT_DIR.exists(), f"non-overwrite output already exists: {relative(OUTPUT_DIR)}")
    require("receipt.json" in payloads, "completion receipt payload is missing")
    OUTPUT_DIR.mkdir(mode=0o755, parents=False, exist_ok=False)
    ordered_names = sorted(name for name in payloads if name != "receipt.json")
    ordered_names.append("receipt.json")
    for name in ordered_names:
        payload = payloads[name]
        require(Path(name).name == name, f"invalid output filename: {name}")
        path = OUTPUT_DIR / name
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    directory_fd = os.open(OUTPUT_DIR, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def self_test() -> dict[str, Any]:
    for background in (25.0, 1000.0, 100000.0):
        for z_value in (3.0, 5.0):
            signal = asimov_required_signal(background, z_value)
            close(
                asimov_significance(signal, background),
                z_value,
                "self-test Asimov inversion",
                rtol=2e-13,
                atol=2e-13,
            )
    fmin = expected_fmin(10000.0, 5.0e6)
    close(fmin["Fmin_3sigma_gaussian_ph_cm2_s"], 6.0e-5, "self-test Gaussian Fmin")
    synthetic = {
        "a": {
            "day15_total_W2_rate_cps": 0.06,
            "cumulative_background_counts_B": 90000.0,
            "Fmin_3sigma_gaussian_ph_cm2_s": 6.0e-5,
            "Fmin_5sigma_gaussian_ph_cm2_s": 1.0e-4,
            "Fmin_3sigma_poisson_asimov_ph_cm2_s": 6.1e-5,
            "Fmin_5sigma_poisson_asimov_ph_cm2_s": 1.02e-4,
            "signal_kernel_cm2": 9.5,
            "signal_Aeff_cm2": 15.0,
        },
        "b": {
            "day15_total_W2_rate_cps": 0.02,
            "cumulative_background_counts_B": 10000.0,
            "Fmin_3sigma_gaussian_ph_cm2_s": 2.0e-5,
            "Fmin_5sigma_gaussian_ph_cm2_s": 3.3333333333333335e-5,
            "Fmin_3sigma_poisson_asimov_ph_cm2_s": 2.0333333333333334e-5,
            "Fmin_5sigma_poisson_asimov_ph_cm2_s": 3.4e-5,
            "signal_kernel_cm2": 7.6,
            "signal_Aeff_cm2": 12.0,
        },
    }
    improvements, rows = improvement_values(synthetic)
    close(improvements["day15_background_reduction_factor_A_over_B"]["value"], 3.0, "self-test day15 improvement")
    close(improvements["cumulative_background_reduction_factor_A_over_B"]["value"], 9.0, "self-test cumulative improvement")
    close(improvements["signal_kernel_retention_B_over_A"]["value"], 0.8, "self-test kernel retention")
    require(len(rows) == 8, "self-test improvement row count")
    require(OUTPUT_DIR == OUTPUTS / "06_publication_values", "self-test output confinement")
    sample = json_bytes({"b": 2, "a": 1})
    require(sample == b'{\n  "a": 1,\n  "b": 2\n}\n', "self-test canonical JSON")
    return {
        "schema_version": 1,
        "status": "PASS__PUBLICATION_VALUE_BUILDER_SELF_TEST",
        "tests": {
            "Asimov_inversion": "PASS",
            "Gaussian_Fmin": "PASS",
            "A_B_improvement_orientation": "PASS",
            "canonical_JSON": "PASS",
            "output_confinement": relative(OUTPUT_DIR),
            "nonoverwrite_contract": True,
        },
        "side_effects": {
            "formal_inputs_read": False,
            "output_created": False,
            "transport_started": False,
        },
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a fail-closed, non-overwriting publication-values bundle "
            "from package-67 formal outputs 00 through 04."
        ),
        epilog=(
            "With no mode flag, all formal inputs and their validation-recorded "
            "hashes are checked before outputs/06_publication_values is created."
        ),
    )
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--check-inputs",
        action="store_true",
        help="report completeness/status and output collision without writing",
    )
    modes.add_argument(
        "--self-test",
        action="store_true",
        help="run formula/schema unit checks without reading formal inputs or writing",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.self_test:
            print(json.dumps(self_test(), indent=2, sort_keys=True, ensure_ascii=False))
            return 0
        if args.check_inputs:
            print(json.dumps(input_inventory(), indent=2, sort_keys=True, ensure_ascii=False))
            return 0
        payloads, summary = build_payloads()
        write_exclusive(payloads)
        print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    except PublicationError as error:
        print(
            json.dumps(
                {
                    "status": "FAIL_CLOSED__PUBLICATION_VALUES_NOT_WRITTEN",
                    "error": str(error),
                    "output_dir": relative(OUTPUT_DIR),
                },
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
