#!/usr/bin/env python3
"""Audit the M05 continuum-plus-mono511 flux-closed result chain.

This validator is deliberately independent of the timeline runner's numerical
helpers.  It recomputes source closure, event-template moments, the 81-node
mission quadrature, Gaussian/Cowan-Asimov thresholds, and their propagated
statistical errors.  It never opens raw SIM files and never runs transport.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve()
PACKAGE = HERE.parents[1]
ROOT = PACKAGE.parents[2]
OUTPUTS = PACKAGE / "outputs"

SECONDS_PER_DAY = 86_400.0
ANCHOR_NODES = (0, 20, 40, 60, 80)
FINAL_WINDOW = "w2_510p58_511p42"
FINAL_STAGE = "compton_trajectory_veto"
FINAL_STAGE_BIT = 1 << 4
COMPONENTS = ("other", "gamma_continuum", "atm511")
COMPONENT_CODES = {name: index for index, name in enumerate(COMPONENTS)}
STREAM_LABELS = ("all", "prompt", "delayed")
COMPONENT_LABELS = ("all",) + COMPONENTS
SPECTRUM_STAGES = (
    "pre_veto",
    "combined_active_veto",
    "compton_trajectory_veto",
)
STAGES = (
    "pre_veto",
    "plastic_positron_veto",
    "bgo_active_scintillator_veto",
    "combined_active_veto",
    "compton_trajectory_veto",
)
STAGE_BITS = {name: 1 << index for index, name in enumerate(STAGES)}
WINDOW_FIELDS = {
    "broad_480_550": "broad_flags",
    FINAL_WINDOW: "w2_flags",
}

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

EXPECTED_LINE = {
    "a": {
        "geometry_basename": "DEMO2_DR_v3p5_SG3B.geo.setup",
        "geometry_path_fragment": (
            "55_geoopt_sg3b_bi_halfcylinder_al_harness_20260816/geometry/"
            "DEMO2_DR_v3p5_SG3B.geo.setup"
        ),
        "incident_photons": 3_000_000,
        "jobs": 13,
        "detector_positive_events": 1_008_606,
        "final_selected": 12,
    },
    "b": {
        "geometry_basename": "SH3_Assembly_OptV3_60cm.geo.setup",
        "geometry_path_fragment": (
            "sh3/assembly_opt_v3/geometry/SH3_Assembly_OptV3_60cm.geo.setup"
        ),
        "incident_photons": 12_140_688,
        "jobs": 52,
        "detector_positive_events": 502_682,
        "final_selected": 143,
    },
}

PAPER_REFERENCE = {
    "path": (
        ROOT
        / "core_md/balloon511_ea_latex_drafts/M05NEW/"
        "balloon511_ea_draft_en_sg3_sh3_revision_20260821.tex"
    ),
    "background_display_step_counts": 0.01,
    "fmin_display_step_ph_cm2_s": 1.0e-8,
    "models": {
        "a": {
            "background_counts": 86_806.00,
            "Fmin_3sigma_gaussian_ph_cm2_s": 5.406e-5,
            "Fmin_3sigma_gaussian_standard_error_ph_cm2_s": 0.401e-5,
            "Fmin_3sigma_poisson_asimov_ph_cm2_s": 5.415e-5,
        },
        "b": {
            "background_counts": 15_551.68,
            "Fmin_3sigma_gaussian_ph_cm2_s": 2.229e-5,
            "Fmin_3sigma_gaussian_standard_error_ph_cm2_s": 0.209e-5,
            "Fmin_3sigma_poisson_asimov_ph_cm2_s": 2.238e-5,
        },
    },
}

PUBLICATION_TOTAL_MC_RSE_MAX = 0.10
PUBLICATION_LINE_FMIN_VARIANCE_FRACTION_MAX = 0.50
SOURCE_CLOSURE_STATUS = (
    "COMPLETE__HYBRID_W118P3_G0_DELINE__W114P6_G0P15_MONO_81X80"
)
CONTINUUM_DELINE_STATE = (118.3, 11.6, 3.84535, 0.0)
MONO_DAY15_STATE = (114.6, 11.6, 3.4614689720143224, 0.15)
MONO_DAY15_NODE = 60
MONO_DAY15_FLUX_PH_CM2_S = 0.16651547160226118


class ValidationError(RuntimeError):
    """A failed physics, schema, or numerical closure check."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def as_float(row: Mapping[str, Any], key: str) -> float:
    try:
        value = float(row[key])
    except (KeyError, TypeError, ValueError) as error:
        raise ValidationError(f"missing/non-numeric field {key}") from error
    require(math.isfinite(value), f"non-finite field {key}: {value}")
    return value


def as_int(row: Mapping[str, Any], key: str) -> int:
    try:
        text = str(row[key]).strip()
        value = int(text)
    except (KeyError, TypeError, ValueError) as error:
        raise ValidationError(f"missing/non-integer field {key}") from error
    return value


def close(
    actual: float,
    expected: float,
    label: str,
    *,
    rtol: float = 3e-11,
    atol: float = 2e-12,
) -> None:
    if not math.isclose(actual, expected, rel_tol=rtol, abs_tol=atol):
        raise ValidationError(
            f"{label} mismatch: actual={actual:.17g}, expected={expected:.17g}, "
            f"delta={actual - expected:.17g}"
        )


def require_columns(
    rows: Sequence[Mapping[str, Any]], columns: Iterable[str], label: str
) -> None:
    require(bool(rows), f"{label} is empty")
    missing = sorted(set(columns) - set(rows[0]))
    require(not missing, f"{label} missing columns: {missing}")


def stats(weights: np.ndarray, label: str) -> dict[str, float | int]:
    values = np.asarray(weights, dtype=np.float64)
    require(values.ndim == 1 and len(values) > 0, f"{label} has no weights")
    require(np.all(np.isfinite(values)), f"{label} has non-finite weights")
    require(np.all(values >= 0.0), f"{label} has negative weights")
    sumw = float(np.sum(values, dtype=np.float64))
    sumw2 = float(np.sum(values * values, dtype=np.float64))
    ess = sumw * sumw / sumw2 if sumw2 > 0.0 else 0.0
    return {
        "selected_raw": int(len(values)),
        "sumw": sumw,
        "sumw2": sumw2,
        "sigma": math.sqrt(sumw2),
        "effective_sample_size": ess,
    }


def check_axis(
    rows: Sequence[Mapping[str, Any]],
    key: str,
    expected: Sequence[int],
    label: str,
) -> None:
    actual = [as_int(row, key) for row in rows]
    require(actual == list(expected), f"{label} {key} axis differs: {actual[:12]}")


def component_name(value: Any) -> str:
    if isinstance(value, (int, np.integer)):
        code = int(value)
        require(0 <= code < len(COMPONENTS), f"bad component code: {code}")
        return COMPONENTS[code]
    text = str(value).strip().lower()
    aliases = {
        "other": "other",
        "other_prompt_delayed": "other",
        "gamma_continuum": "gamma_continuum",
        "continuum": "gamma_continuum",
        "atm511": "atm511",
        "mono511": "atm511",
        "line": "atm511",
    }
    require(text in aliases, f"unknown component label: {value!r}")
    return aliases[text]


def asimov_required_signal(background: float, target_z: float) -> float:
    """Independently invert the Cowan counting-experiment Asimov significance."""
    require(background >= 0.0, "Asimov background is negative")
    require(target_z > 0.0, "Asimov target significance is not positive")
    if background == 0.0:
        return 0.5 * target_z * target_z
    low = 0.0
    high = max(target_z * math.sqrt(background), 1.0)

    def significance(signal: float) -> float:
        term = 2.0 * (
            (signal + background) * math.log1p(signal / background) - signal
        )
        return math.sqrt(max(term, 0.0))

    while significance(high) < target_z:
        high *= 2.0
    for _ in range(100):
        middle = 0.5 * (low + high)
        if significance(middle) < target_z:
            low = middle
        else:
            high = middle
    return high


def fmin_values(background: float, kernel: float) -> dict[str, float]:
    require(background >= 0.0, "negative cumulative background")
    require(kernel > 0.0, "non-positive cumulative signal kernel")
    result: dict[str, float] = {}
    for z in (3, 5):
        result[f"Fmin_{z}sigma_gaussian_ph_cm2_s"] = (
            z * math.sqrt(background) / kernel
        )
        result[f"Fmin_{z}sigma_poisson_asimov_ph_cm2_s"] = (
            asimov_required_signal(background, float(z)) / kernel
        )
    return result


def write_json(path: Path, value: Any, *, force: bool) -> None:
    require(path.resolve().is_relative_to(PACKAGE.resolve()), "output escapes package")
    if path.exists() and not force:
        raise ValidationError(f"refusing to overwrite existing output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")
    temporary = path.parent / f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp"
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@dataclass
class SourceData:
    report: dict[str, Any]
    line_ratio: np.ndarray
    days: np.ndarray


@dataclass
class LineData:
    report: dict[str, Any]
    incident_photons: int
    detector_positive_events: int
    event_weight_cps: float
    all_bins: np.ndarray
    all_weights: np.ndarray
    all_w2_flags: np.ndarray
    selected_bins: np.ndarray
    selected_weights: np.ndarray


@dataclass
class CatalogData:
    report: dict[str, Any]
    selected_line_bins: np.ndarray
    selected_line_weights: np.ndarray


def validate_source(source_dir: Path) -> SourceData:
    manifest_path = source_dir / "source_closure.json"
    coarse_path = source_dir / "coarse_line_decomposition_20bins.csv"
    target_path = source_dir / "mono511_target_81x80.csv"
    trajectory_path = source_dir / "trajectory_component_scales_81nodes.csv"
    manifest = load_json(manifest_path)
    require(int(manifest.get("schema_version", -1)) == 2,
            "source closure schema is not version 2")
    require(
        manifest.get("status") == SOURCE_CLOSURE_STATUS,
        "source closure status is not complete/current",
    )

    coarse = read_csv(coarse_path)
    require_columns(
        coarse,
        (
            "source_bin20",
            "embedded_coarse_line_flux_ph_cm2_s",
            "broadband_total_flux_ph_cm2_s",
            "continuum_flux_ph_cm2_s",
            "line_node_continuum_importance_ratio",
            "w2_total_flux_ph_cm2_s",
            "w2_coarse_line_flux_ph_cm2_s",
            "w2_continuum_flux_ph_cm2_s",
        ),
        "coarse-line table",
    )
    require(len(coarse) == 20, f"coarse-line row count is {len(coarse)}, not 20")
    check_axis(coarse, "source_bin20", range(20), "coarse-line table")
    nonnegative_coarse = (
        "source_card_flux_ph_cm2_s",
        "embedded_coarse_line_flux_ph_cm2_s",
        "parma511_continuum_deline_state_flux_ph_cm2_s",
        "mono511_day15_authority_flux_ph_cm2_s",
        "broadband_total_flux_ph_cm2_s",
        "continuum_flux_ph_cm2_s",
        "line_node_total_density_ph_cm2_s_keV",
        "line_node_subtracted_density_ph_cm2_s_keV",
        "line_node_continuum_density_ph_cm2_s_keV",
        "line_node_continuum_importance_ratio",
        "w2_total_flux_ph_cm2_s",
        "w2_coarse_line_flux_ph_cm2_s",
        "w2_continuum_flux_ph_cm2_s",
    )
    for row in coarse:
        for key in nonnegative_coarse:
            require(as_float(row, key) >= 0.0, f"negative coarse field {key}")
        total = as_float(row, "broadband_total_flux_ph_cm2_s")
        removed = as_float(row, "embedded_coarse_line_flux_ph_cm2_s")
        continuum = as_float(row, "continuum_flux_ph_cm2_s")
        close(continuum, total - removed, "coarse broadband-line identity", atol=2e-15)
        close(
            as_float(row, "w2_continuum_flux_ph_cm2_s"),
            as_float(row, "w2_total_flux_ph_cm2_s")
            - as_float(row, "w2_coarse_line_flux_ph_cm2_s"),
            "coarse W2 line identity",
            atol=2e-15,
        )
        ratio = as_float(row, "line_node_continuum_importance_ratio")
        require(0.0 < ratio <= 1.0, f"coarse importance outside (0,1]: {ratio}")

    ref = manifest["continuum_deline_reference_closure"]
    continuum_state = (
        float(ref["solar_modulation_W_MV"]),
        float(ref["cutoff_rigidity_Rc_GV"]),
        float(ref["atmospheric_depth_g_cm2"]),
        float(ref["local_geometry_g"]),
    )
    for actual, expected, label in zip(
        continuum_state,
        CONTINUUM_DELINE_STATE,
        ("continuum W", "continuum Rc", "continuum depth", "continuum g"),
    ):
        close(actual, expected, label, atol=2e-12)
    mono_day15 = manifest["mono511_day15_authority"]
    mono_day15_state = (
        float(mono_day15["solar_modulation_W_MV"]),
        float(mono_day15["cutoff_rigidity_Rc_GV"]),
        float(mono_day15["atmospheric_depth_g_cm2"]),
        float(mono_day15["local_geometry_g"]),
    )
    for actual, expected, label in zip(
        mono_day15_state,
        MONO_DAY15_STATE,
        ("mono W", "mono Rc", "mono depth", "mono g"),
    ):
        close(actual, expected, label, atol=2e-12)
    require(as_int(mono_day15, "time_bin_id") == MONO_DAY15_NODE,
            "mono day-15 authority node differs")
    close(
        float(mono_day15["integrated_flux_ph_cm2_s"]),
        MONO_DAY15_FLUX_PH_CM2_S,
        "mono day-15 authority integral",
        atol=2e-15,
    )
    coarse_sums = {
        "broadband": math.fsum(
            as_float(row, "broadband_total_flux_ph_cm2_s") for row in coarse
        ),
        "removed": math.fsum(
            as_float(row, "embedded_coarse_line_flux_ph_cm2_s") for row in coarse
        ),
        "continuum": math.fsum(
            as_float(row, "continuum_flux_ph_cm2_s") for row in coarse
        ),
    }
    close(
        coarse_sums["broadband"],
        float(ref["broadband_reference_flux_ph_cm2_s"]),
        "coarse broadband sum",
    )
    close(
        coarse_sums["removed"],
        float(ref["removed_coarse_line_reference_flux_ph_cm2_s"]),
        "coarse removed-line sum",
    )
    close(
        coarse_sums["continuum"],
        float(ref["continuum_reference_flux_ph_cm2_s"]),
        "coarse continuum sum",
    )
    close(
        coarse_sums["continuum"] + coarse_sums["removed"],
        coarse_sums["broadband"],
        "reference exact subtraction",
    )

    target = read_csv(target_path)
    require_columns(
        target,
        (
            "time_bin_id",
            "day_mid",
            "source_bin80",
            "target_flux_ph_cm2_s",
            "proposal_flux_ph_cm2_s",
            "importance_ratio",
            "target_W_MV",
            "target_Rc_GV",
            "target_depth_g_cm2",
            "target_g",
            "driver_bin_id",
            "proposal_W_MV",
            "proposal_Rc_GV",
            "proposal_depth_g_cm2",
            "proposal_g",
        ),
        "mono511 target table",
    )
    require(len(target) == 81 * 80, f"mono511 target has {len(target)} rows")
    seen: set[tuple[int, int]] = set()
    line_ratio = np.empty((81, 80), dtype=np.float64)
    target_flux = np.empty((81, 80), dtype=np.float64)
    proposal_flux = np.empty((81, 80), dtype=np.float64)
    days = np.empty(81, dtype=np.float64)
    for row in target:
        node = as_int(row, "time_bin_id")
        source_bin = as_int(row, "source_bin80")
        require(0 <= node < 81, f"bad mono511 node {node}")
        require(0 <= source_bin < 80, f"bad mono511 source bin {source_bin}")
        require((node, source_bin) not in seen, f"duplicate mono511 key {(node, source_bin)}")
        seen.add((node, source_bin))
        day = as_float(row, "day_mid")
        close(day, node / 4.0, "mono511 day axis", atol=2e-14)
        days[node] = day
        target_value = as_float(row, "target_flux_ph_cm2_s")
        proposal_value = as_float(row, "proposal_flux_ph_cm2_s")
        ratio = as_float(row, "importance_ratio")
        require(target_value > 0.0 and proposal_value > 0.0 and ratio > 0.0,
                "mono511 target/proposal/ratio must be positive")
        close(ratio, target_value / proposal_value, "mono511 importance ratio", atol=2e-14)
        close(
            as_float(row, "target_W_MV"),
            MONO_DAY15_STATE[0],
            "target W",
            atol=2e-13,
        )
        close(
            as_float(row, "target_g"),
            MONO_DAY15_STATE[3],
            "target g",
            atol=2e-14,
        )
        for key, expected, label in (
            ("proposal_W_MV", MONO_DAY15_STATE[0], "proposal W"),
            ("proposal_Rc_GV", MONO_DAY15_STATE[1], "proposal Rc"),
            (
                "proposal_depth_g_cm2",
                MONO_DAY15_STATE[2],
                "proposal depth",
            ),
            ("proposal_g", MONO_DAY15_STATE[3], "proposal g"),
        ):
            close(as_float(row, key), expected, label, atol=2e-12)
        if node == MONO_DAY15_NODE:
            close(
                as_float(row, "target_Rc_GV"),
                MONO_DAY15_STATE[1],
                "node60 target Rc",
                atol=2e-14,
            )
            close(
                as_float(row, "target_depth_g_cm2"),
                MONO_DAY15_STATE[2],
                "node60 target depth",
                atol=2e-14,
            )
            require(
                target_value == proposal_value and ratio == 1.0,
                "node60 target/proposal must be a literal 80-bin identity",
            )
        require(as_int(row, "driver_bin_id") == 79 - source_bin,
                "PARMA/Cosima angular-bin reversal differs")
        target_flux[node, source_bin] = target_value
        proposal_flux[node, source_bin] = proposal_value
        line_ratio[node, source_bin] = ratio
    require(len(seen) == 6480, "mono511 81x80 key grid is incomplete")
    require(np.all(np.isfinite(line_ratio)) and np.all(line_ratio > 0.0),
            "mono511 ratio matrix is invalid")
    for node in range(1, 81):
        require(
            np.array_equal(proposal_flux[node], proposal_flux[0]),
            f"proposal denominator changes at node {node}",
        )
    proposal_total = float(np.sum(proposal_flux[0], dtype=np.float64))
    close(
        proposal_total,
        float(manifest["proposal_denominator"]["integrated_flux_ph_cm2_s"]),
        "proposal 80-bin integral",
    )
    day15_target_total = float(
        np.sum(target_flux[MONO_DAY15_NODE], dtype=np.float64)
    )
    day15_proposal_total = float(
        np.sum(proposal_flux[MONO_DAY15_NODE], dtype=np.float64)
    )
    close(
        day15_target_total,
        MONO_DAY15_FLUX_PH_CM2_S,
        "node60 target 80-bin integral",
        atol=2e-15,
    )
    close(
        day15_proposal_total,
        MONO_DAY15_FLUX_PH_CM2_S,
        "node60 proposal 80-bin integral",
        atol=2e-15,
    )

    trajectory = read_csv(trajectory_path)
    require_columns(
        trajectory,
        (
            "time_bin_id",
            "day_mid",
            "gamma_continuum_scale_to_reference",
            "removed_coarse_line_flux_ph_cm2_s",
            "target_mono511_flux_ph_cm2_s",
            "recomposed_gamma_flux_ph_cm2_s",
            "original_broadband_flux_ph_cm2_s",
            "representation_delta_ph_cm2_s",
            "continuum_flux_ph_cm2_s",
            "exact_subtraction_identity_residual_ph_cm2_s",
            "proposal_weighted_flux_sum_ph_cm2_s",
            "target_Rc_GV",
            "target_depth_g_cm2",
        ),
        "trajectory component table",
    )
    require(len(trajectory) == 81, f"trajectory component table has {len(trajectory)} rows")
    check_axis(trajectory, "time_bin_id", range(81), "trajectory component table")
    max_formula_residual = 0.0
    for node, row in enumerate(trajectory):
        close(as_float(row, "day_mid"), node / 4.0, "trajectory day axis")
        if node == MONO_DAY15_NODE:
            close(
                as_float(row, "target_Rc_GV"),
                MONO_DAY15_STATE[1],
                "trajectory node60 target Rc",
                atol=2e-14,
            )
            close(
                as_float(row, "target_depth_g_cm2"),
                MONO_DAY15_STATE[2],
                "trajectory node60 target depth",
                atol=2e-14,
            )
        scale = as_float(row, "gamma_continuum_scale_to_reference")
        removed = as_float(row, "removed_coarse_line_flux_ph_cm2_s")
        continuum = as_float(row, "continuum_flux_ph_cm2_s")
        original = as_float(row, "original_broadband_flux_ph_cm2_s")
        target_total = float(np.sum(target_flux[node], dtype=np.float64))
        recomposed = as_float(row, "recomposed_gamma_flux_ph_cm2_s")
        for value, label in (
            (scale, "gamma scale"),
            (removed, "removed coarse line"),
            (continuum, "continuum"),
            (original, "original broadband"),
            (target_total, "target mono line"),
            (recomposed, "recomposed gamma"),
        ):
            require(value >= 0.0, f"negative {label} at node {node}")
        close(
            removed,
            coarse_sums["removed"] * scale,
            f"removed coarse-line scale node {node}",
        )
        close(
            continuum,
            coarse_sums["continuum"] * scale,
            f"continuum scale node {node}",
        )
        close(
            original,
            coarse_sums["broadband"] * scale,
            f"broadband scale node {node}",
        )
        close(
            as_float(row, "target_mono511_flux_ph_cm2_s"),
            target_total,
            f"mono511 bin sum node {node}",
        )
        close(recomposed, continuum + target_total, f"recomposition node {node}")
        delta = as_float(row, "representation_delta_ph_cm2_s")
        close(delta, recomposed - original, f"representation delta node {node}")
        residual = continuum + removed - original
        close(
            as_float(row, "exact_subtraction_identity_residual_ph_cm2_s"),
            residual,
            f"subtraction residual node {node}",
        )
        weighted = float(np.sum(proposal_flux[node] * line_ratio[node], dtype=np.float64))
        close(weighted, target_total, f"proposal weighted target node {node}")
        close(
            as_float(row, "proposal_weighted_flux_sum_ph_cm2_s"),
            target_total,
            f"recorded proposal weighted sum node {node}",
        )
        max_formula_residual = max(
            max_formula_residual,
            abs(residual),
            abs(recomposed - original - delta),
            abs(weighted - target_total),
        )

    output_hashes: dict[str, str] = {}
    for path in (coarse_path, target_path, trajectory_path):
        actual_hash = sha256_file(path)
        output_hashes[path.name] = actual_hash
        recorded = manifest["outputs"][path.name]
        require(int(recorded["rows"]) == len(read_csv(path)),
                f"source manifest row count differs for {path.name}")
        require(recorded["sha256"] == actual_hash,
                f"source manifest hash differs for {path.name}")
    report = {
        "status": "PASS__SOURCE_CLOSURE_FORMULAS_NONNEGATIVE_81X80",
        "coarse_rows": 20,
        "mono511_rows": 6480,
        "trajectory_nodes": 81,
        "continuum_deline_state": {
            "solar_modulation_W_MV": CONTINUUM_DELINE_STATE[0],
            "cutoff_rigidity_Rc_GV": CONTINUUM_DELINE_STATE[1],
            "atmospheric_depth_g_cm2": CONTINUUM_DELINE_STATE[2],
            "local_geometry_g": CONTINUUM_DELINE_STATE[3],
        },
        "mono_target_state": {
            "solar_modulation_W_MV": MONO_DAY15_STATE[0],
            "local_geometry_g": MONO_DAY15_STATE[3],
            "Rc_depth": "per-node",
        },
        "day15_identity": {
            "time_bin_id": MONO_DAY15_NODE,
            "target_flux_ph_cm2_s": day15_target_total,
            "proposal_flux_ph_cm2_s": day15_proposal_total,
            "minimum_importance_ratio": float(
                np.min(line_ratio[MONO_DAY15_NODE])
            ),
            "maximum_importance_ratio": float(
                np.max(line_ratio[MONO_DAY15_NODE])
            ),
        },
        "broadband_reference_flux_ph_cm2_s": coarse_sums["broadband"],
        "removed_coarse_line_reference_flux_ph_cm2_s": coarse_sums["removed"],
        "continuum_reference_flux_ph_cm2_s": coarse_sums["continuum"],
        "parma511_flux_at_continuum_deline_state_ph_cm2_s": float(
            ref["parma511_flux_at_continuum_deline_state_ph_cm2_s"]
        ),
        "minimum_continuum_importance_weight": float(
            manifest["coarse_line"][
                "minimum_event_importance_ratio_Jcont_over_Jtotal"
            ]
        ),
        "minimum_line_importance_ratio": float(np.min(line_ratio)),
        "maximum_line_importance_ratio": float(np.max(line_ratio)),
        "maximum_recomputed_formula_residual": max_formula_residual,
        "hashes": {
            "source_closure.json": sha256_file(manifest_path),
            **output_hashes,
        },
        "reference_state_caveat": (
            "explicit hybrid: continuum is de-lined at W=118.3/g=0/Rc=11.6/"
            "X=3.84535 and retains the W=114.6 gamma trajectory scale; the mono "
            "target is W=114.6/g=0.15 with per-node Rc/depth. No artificial "
            "renormalization preserves the old broadband total, and physical "
            "PARMA flux systematics are EXCLUDED"
        ),
    }
    return SourceData(report=report, line_ratio=line_ratio, days=days)


def validate_merge_lineage(
    receipt: Mapping[str, Any], line_dir: Path, *, depth: int = 0
) -> Mapping[str, Any]:
    """Validate a compact merge and recursively close any promoted base merge."""
    require(depth <= 4, "model-b compact merge lineage is unexpectedly deep")
    require(
        receipt.get("status") == "PASS__B60_COMPACT_TOPUP_MERGE_AUTHORITY",
        "model-b compact top-up merge receipt status differs",
    )
    require(int(receipt.get("schema_version", -1)) == 1,
            "model-b compact top-up merge receipt schema differs")
    result = receipt.get("result", {})
    inputs = receipt.get("inputs", {})
    topup = inputs.get("topup", {})
    method = receipt.get("method", {})
    require(int(method.get("new_raw_sim_jobs_scanned", -1)) == int(topup.get("jobs", -2)),
            "model-b merge/top-up job count differs")
    require(int(result.get("job_index_minimum", -1)) == 0,
            "model-b merged minimum job index differs")
    require(int(result.get("job_index_maximum", -1)) == int(result["jobs"]) - 1,
            "model-b merged maximum job index differs")

    base = inputs.get("base_response")
    if base is None:
        # Schema-1 compatibility path for the already published first 52->67
        # compact merge receipt.
        require(int(method.get("old_raw_sim_files_scanned", -1)) == 0,
                "model-b merge rescanned old raw SIM files")
        require(int(result.get("jobs", -1))
                == int(EXPECTED_LINE["b"]["jobs"]) + int(topup["jobs"]),
                "model-b first merged job total differs")
        require(int(result.get("incident_photons", -1))
                == int(EXPECTED_LINE["b"]["incident_photons"])
                + int(topup["incident_photons"]),
                "model-b first merged incident total differs")
    else:
        require(int(method.get("prefix_raw_sim_files_scanned", -1)) == 0,
                "model-b incremental merge rescanned prefix raw SIM files")
        base_result = base.get("result", {})
        require(int(base_result.get("job_index_minimum", -1)) == 0,
                "model-b base minimum job index differs")
        require(int(base_result.get("job_index_maximum", -1))
                == int(base_result.get("jobs", -2)) - 1,
                "model-b base maximum job index differs")
        require(int(result.get("jobs", -1))
                == int(base_result["jobs"]) + int(topup["jobs"]),
                "model-b base plus incremental jobs do not close")
        require(int(result.get("incident_photons", -1))
                == int(base_result["incident_photons"])
                + int(topup["incident_photons"]),
                "model-b base plus incremental incidents do not close")
        close(
            float(result["physical_exposure_s"]),
            float(base_result["physical_exposure_s"])
            + float(topup["physical_exposure_s"]),
            "model-b base plus incremental physical exposure",
            rtol=2e-15,
            atol=0.0,
        )
        require(int(method.get("base_compact_prefix_events", -1))
                == int(base_result["detector_positive_events"]),
                "model-b base detector-positive count differs")
        base_dir = Path(base["root"])
        require(base_dir.is_dir(), "model-b base-response root is missing")
        files = base.get("files", {})
        for name, record in files.items():
            path = Path(record["path"])
            require(path.resolve().parent == base_dir.resolve(),
                    f"model-b base file escapes response root: {name}")
            require(path.is_file() and path.stat().st_size == int(record["bytes"])
                    and sha256_file(path) == record["sha256"],
                    f"model-b base file binding differs: {name}")
        mode = base.get("mode")
        if mode == "legacy_52_compact":
            require(int(base_result["jobs"]) == int(EXPECTED_LINE["b"]["jobs"])
                    and int(base_result["incident_photons"])
                    == int(EXPECTED_LINE["b"]["incident_photons"]),
                    "model-b legacy base regression differs")
        elif mode in ("promoted_67_compact", "promoted_68_compact"):
            require("MERGE_RECEIPT.json" in files,
                    "model-b promoted base lacks merge-receipt binding")
            prior = load_json(base_dir / "MERGE_RECEIPT.json")
            prior_result = validate_merge_lineage(prior, base_dir, depth=depth + 1)
            for key in ("jobs", "incident_photons", "detector_positive_events"):
                require(int(base_result[key]) == int(prior_result[key]),
                        f"model-b recursive base result differs: {key}")
            close(float(base_result["physical_exposure_s"]),
                  float(prior_result["physical_exposure_s"]),
                  "model-b recursive base exposure", rtol=2e-15, atol=0.0)
        else:
            raise ValidationError(f"unknown model-b base response mode: {mode}")

    for name in LINE_FILES:
        record = receipt.get("outputs", {}).get(name)
        require(isinstance(record, Mapping), f"model-b merge output receipt missing: {name}")
        require(sha256_file(line_dir / name) == record.get("sha256"),
                f"model-b merge output hash differs: {name}")
    return result


def validate_line_response(model: str, line_dir: Path) -> LineData:
    expected = dict(EXPECTED_LINE[model])
    summary_path = line_dir / "summary.json"
    catalog_path = line_dir / "mono_line_event_catalog.npz"
    cutflow_path = line_dir / "mono_line_cutflow.csv"
    by_bin_path = line_dir / "mono_line_final_by_source_bin80.csv"
    merge_receipt_path = line_dir / "MERGE_RECEIPT.json"
    merge_receipt: dict[str, Any] | None = None
    if model == "b" and merge_receipt_path.is_file():
        merge_receipt = load_json(merge_receipt_path)
        result = validate_merge_lineage(merge_receipt, line_dir)
        source_authority = merge_receipt.get("source_authority", {})
        require(
            source_authority.get("status")
            == "PASS__EXACT_NORMALIZED_PARMA_80BIN_FRAGMENT",
            "model-b merge lacks exact normalized PARMA 80-bin validation",
        )
        require(
            source_authority.get("canonical_fragment_sha256")
            == "fc386a44b096d33d12d4a096532a3a57da5743681d93e779e653ae1349f776e6",
            "model-b merge PARMA fragment authority differs",
        )
        selection = merge_receipt.get("selection_authority", {})
        require(float(selection.get("active_veto_threshold_keV", -1.0)) == 50.0,
                "model-b merged active-veto threshold differs")
        require(selection.get("windows_keV", {}).get(FINAL_WINDOW) == [510.58, 511.42],
                "model-b merged final window differs")
        require(selection.get("stage_bits") == STAGE_BITS,
                "model-b merged response-stage bits differ")
        expected.update({
            "incident_photons": int(result["incident_photons"]),
            "jobs": int(result["jobs"]),
            "detector_positive_events": int(result["detector_positive_events"]),
            "final_selected": int(result["w2_final_selected_events"]),
        })
    summary = load_json(summary_path)
    require(summary.get("status") == "COMPLETE__MONO_LINE_COMMON_RESPONSE",
            f"model-{model} line summary status differs")
    require(summary.get("model") == model, f"model-{model} line summary model differs")
    geometry = str(summary.get("geometry_setup", ""))
    require(Path(geometry).name == expected["geometry_basename"],
            f"model-{model} line geometry basename differs: {geometry}")
    require(expected["geometry_path_fragment"] in geometry,
            f"model-{model} line geometry authority differs: {geometry}")
    for key in ("incident_photons", "jobs", "detector_positive_events"):
        require(int(summary[key]) == int(expected[key]),
                f"model-{model} line {key} differs")
    exposure = float(summary["physical_exposure_s"])
    require(math.isfinite(exposure) and exposure > 0.0,
            f"model-{model} line exposure is invalid")
    expected_weight = 1.0 / exposure
    close(
        float(summary["event_weight_cps"]),
        expected_weight,
        f"model-{model} line event weight=1/exposure",
        rtol=2e-15,
        atol=0.0,
    )

    required_arrays = {
        "event_id",
        "measured_total_keV",
        "broad_flags",
        "w2_flags",
        "source_bin80",
        "event_job_index",
        "base_event_weight_cps",
    }
    with np.load(catalog_path, allow_pickle=False) as data:
        missing = sorted(required_arrays - set(data.files))
        require(not missing, f"model-{model} line catalog missing arrays: {missing}")
        event_id = np.asarray(data["event_id"])
        measured = np.asarray(data["measured_total_keV"], dtype=np.float64)
        broad_flags = np.asarray(data["broad_flags"])
        w2_flags = np.asarray(data["w2_flags"])
        bins = np.asarray(data["source_bin80"])
        job_index = np.asarray(data["event_job_index"])
        weights = np.asarray(data["base_event_weight_cps"])
    count = int(expected["detector_positive_events"])
    for name, array in (
        ("event_id", event_id),
        ("measured_total_keV", measured),
        ("broad_flags", broad_flags),
        ("w2_flags", w2_flags),
        ("source_bin80", bins),
        ("event_job_index", job_index),
        ("base_event_weight_cps", weights),
    ):
        require(array.ndim == 1 and len(array) == count,
                f"model-{model} line array length differs: {name}")
    require(weights.dtype == np.dtype("float64"),
            f"model-{model} line weights are not float64")
    require(np.all(np.isfinite(weights)) and np.all(weights > 0.0),
            f"model-{model} line weights are not finite positive")
    require(np.all(weights == weights[0]), f"model-{model} line weights are not constant")
    close(float(weights[0]), expected_weight, f"model-{model} line catalog weight",
          rtol=2e-15, atol=0.0)
    require(bins.dtype == np.dtype("uint8") and np.all(bins < 80),
            f"model-{model} line source_bin80 is invalid")
    require(set(np.unique(bins).tolist()) == set(range(80)),
            f"model-{model} line catalog does not span 80 bins")
    require(np.all((broad_flags.astype(np.uint64) & np.uint64(0xE0)) == 0),
            f"model-{model} broad flags use unknown bits")
    require(np.all((w2_flags.astype(np.uint64) & np.uint64(0xE0)) == 0),
            f"model-{model} W2 flags use unknown bits")
    require(set(np.unique(job_index).tolist()) == set(range(int(expected["jobs"]))),
            f"model-{model} line job-index coverage differs")

    for flags, window in ((broad_flags, "broad"), (w2_flags, "W2")):
        previous = np.ones(count, dtype=bool)
        for stage in STAGES:
            current = (flags & STAGE_BITS[stage]) != 0
            require(np.all(~current | previous),
                    f"model-{model} {window} flags are not cumulative at {stage}")
            previous = current
    pre_w2 = (w2_flags & STAGE_BITS["pre_veto"]) != 0
    require(np.all((measured[pre_w2] >= 510.58) & (measured[pre_w2] < 511.42)),
            f"model-{model} W2 pre-veto response contains out-of-window energy")

    cutflow = read_csv(cutflow_path)
    require_columns(
        cutflow,
        (
            "model",
            "window_id",
            "stage",
            "selected_events",
            "event_weight_cps",
            "weighted_rate_cps",
            "weighted_mc_sigma_cps",
            "effective_selected_events",
        ),
        f"model-{model} line cutflow",
    )
    require(len(cutflow) == len(WINDOW_FIELDS) * len(STAGES),
            f"model-{model} line cutflow row count differs")
    cutflow_keys: set[tuple[str, str]] = set()
    for row in cutflow:
        require(row["model"] == model, f"model-{model} cutflow model differs")
        window = row["window_id"]
        stage = row["stage"]
        require(window in WINDOW_FIELDS and stage in STAGE_BITS,
                f"model-{model} cutflow key differs: {(window, stage)}")
        require((window, stage) not in cutflow_keys,
                f"model-{model} duplicate cutflow key {(window, stage)}")
        cutflow_keys.add((window, stage))
        flags = broad_flags if WINDOW_FIELDS[window] == "broad_flags" else w2_flags
        mask = (flags & STAGE_BITS[stage]) != 0
        selected = int(np.count_nonzero(mask))
        weighted = stats(weights[mask], f"model-{model} {window}/{stage}")
        require(as_int(row, "selected_events") == selected,
                f"model-{model} cutflow selected differs at {(window, stage)}")
        close(as_float(row, "event_weight_cps"), expected_weight,
              f"model-{model} cutflow event weight")
        close(as_float(row, "weighted_rate_cps"), float(weighted["sumw"]),
              f"model-{model} cutflow rate")
        close(as_float(row, "weighted_mc_sigma_cps"), float(weighted["sigma"]),
              f"model-{model} cutflow sigma")
        close(as_float(row, "effective_selected_events"),
              float(weighted["effective_sample_size"]),
              f"model-{model} cutflow ESS")

    final_mask = (w2_flags & FINAL_STAGE_BIT) != 0
    selected_bins = bins[final_mask].astype(np.int64, copy=True)
    selected_weights = weights[final_mask].astype(np.float64, copy=True)
    final_stats = stats(selected_weights, f"model-{model} final line response")
    require(int(final_stats["selected_raw"]) == int(expected["final_selected"]),
            f"model-{model} final selected count differs")
    for key, actual in (
        ("w2_final_selected_events", int(final_stats["selected_raw"])),
        ("w2_final_effective_sample_size", float(final_stats["effective_sample_size"])),
        ("w2_final_rate_cps", float(final_stats["sumw"])),
        ("w2_final_mc_sigma_cps", float(final_stats["sigma"])),
    ):
        if isinstance(actual, int):
            require(int(summary[key]) == actual, f"model-{model} summary {key} differs")
        else:
            close(float(summary[key]), actual, f"model-{model} summary {key}")
    close(
        float(summary["w2_final_relative_mc_sigma"]),
        float(final_stats["sigma"]) / float(final_stats["sumw"]),
        f"model-{model} final relative line sigma",
    )
    close(
        float(summary["detector_positive_rate_cps"]),
        count * expected_weight,
        f"model-{model} detector-positive rate",
    )

    by_bin = read_csv(by_bin_path)
    require_columns(by_bin, ("source_bin80", "selected_events", "weighted_rate_cps"),
                    f"model-{model} final by-bin response")
    require(len(by_bin) == 80, f"model-{model} final by-bin response is not 80 rows")
    check_axis(by_bin, "source_bin80", range(80), f"model-{model} line by-bin")
    observed_counts = np.bincount(selected_bins, minlength=80)
    for source_bin, row in enumerate(by_bin):
        require(as_int(row, "selected_events") == int(observed_counts[source_bin]),
                f"model-{model} selected line bin {source_bin} differs")
        close(
            as_float(row, "weighted_rate_cps"),
            float(observed_counts[source_bin]) * expected_weight,
            f"model-{model} weighted line bin {source_bin}",
        )

    report = {
        "status": "PASS__FIXED_GEOMETRY_INCIDENT_RESPONSE_AND_FINAL_SELECTION",
        "model": model,
        "geometry_setup": geometry,
        "incident_photons": int(expected["incident_photons"]),
        "jobs": int(expected["jobs"]),
        "detector_positive_events": count,
        "physical_exposure_s": exposure,
        "event_weight_cps": expected_weight,
        "final_selected_events": int(final_stats["selected_raw"]),
        "final_rate_cps": float(final_stats["sumw"]),
        "final_sumw2_cps2": float(final_stats["sumw2"]),
        "final_mc_sigma_cps": float(final_stats["sigma"]),
        "final_effective_sample_size": float(final_stats["effective_sample_size"]),
        "response_definition": {
            "window_keV": "[510.58, 511.42)",
            "final_stage": FINAL_STAGE,
            "flag_bit": FINAL_STAGE_BIT,
            "cutflow_rows_recomputed": len(cutflow),
        },
        "hashes": {
            "summary.json": sha256_file(summary_path),
            "mono_line_event_catalog.npz": sha256_file(catalog_path),
            "mono_line_cutflow.csv": sha256_file(cutflow_path),
            "mono_line_final_by_source_bin80.csv": sha256_file(by_bin_path),
            **(
                {"MERGE_RECEIPT.json": sha256_file(merge_receipt_path)}
                if merge_receipt is not None else {}
            ),
        },
    }
    return LineData(
        report=report,
        incident_photons=int(expected["incident_photons"]),
        detector_positive_events=count,
        event_weight_cps=expected_weight,
        all_bins=bins.astype(np.int64, copy=True),
        all_weights=weights.astype(np.float64, copy=True),
        all_w2_flags=w2_flags.astype(np.uint8, copy=True),
        selected_bins=selected_bins,
        selected_weights=selected_weights,
    )


def validate_catalog(
    model: str,
    catalog_dir: Path,
    source_dir: Path,
    line: LineData,
) -> CatalogData:
    summary_path = catalog_dir / "summary.json"
    audit_path = catalog_dir / "audit.json"
    category_path = catalog_dir / "category_registry.json"
    component_path = catalog_dir / "component_registry.json"
    catalog_path = catalog_dir / "combined_event_catalog.npz"
    summary = load_json(summary_path)
    audit = load_json(audit_path)
    category_registry = load_json(category_path)
    component_registry = load_json(component_path)
    require(
        summary.get("status") == "COMPLETE__POSITIVE_FLUXCLOSED_EVENT_CATALOG",
        f"model-{model} catalog summary is not complete",
    )
    require(summary.get("model") == model, f"model-{model} catalog summary model differs")
    require(
        audit.get("status") == "PASS__FLUXCLOSED_CATALOG_AUDIT",
        f"model-{model} catalog audit is not PASS",
    )
    require(audit.get("model") == model, f"model-{model} catalog audit model differs")
    source_audit = audit.get("source_closure", {})
    require(
        source_audit.get("manifest_sha256")
        == sha256_file(source_dir / "source_closure.json"),
        f"model-{model} catalog was not built from the current source manifest",
    )
    require(
        source_audit.get("bins_sha256")
        == sha256_file(source_dir / "coarse_line_decomposition_20bins.csv"),
        f"model-{model} catalog was not built from the current de-line table",
    )
    mono_validation = source_audit.get("mono_target_validation", {})
    require(
        mono_validation.get("sha256")
        == sha256_file(source_dir / "mono511_target_81x80.csv"),
        f"model-{model} catalog was not built from the current mono target",
    )
    day15_identity = mono_validation.get("day15_identity", {})
    require(
        int(day15_identity.get("time_bin_id", -1)) == MONO_DAY15_NODE,
        f"model-{model} catalog lacks the node60 mono identity audit",
    )
    close(
        float(day15_identity.get("target_flux_ph_cm2_s", math.nan)),
        MONO_DAY15_FLUX_PH_CM2_S,
        f"model-{model} catalog node60 mono target flux",
        atol=2e-15,
    )
    require(
        category_registry.get("weight_authority")
        == "combined_event_catalog.npz:event_base_weight_cps",
        f"model-{model} catalog weight authority differs",
    )

    registered_components = sorted(
        component_registry.get("components", []),
        key=lambda row: int(row["component_id"]),
    )
    require(
        [int(row["component_id"]) for row in registered_components] == [0, 1, 2],
        f"model-{model} component registry IDs differ",
    )
    require(
        [component_name(row["component"]) for row in registered_components]
        == list(COMPONENTS),
        f"model-{model} component registry labels differ",
    )
    require(
        int(component_registry.get("source_bin80_not_applicable", -1)) == 255,
        f"model-{model} source_bin80 sentinel differs",
    )

    needed = {
        "event_category",
        "event_base_weight_cps",
        "event_component",
        "source_bin80",
        "continuum_importance_weight",
        "w2_flags",
        "hit_start",
        "hit_count",
        "hit_code",
    }
    with np.load(catalog_path, allow_pickle=False) as data:
        missing = sorted(needed - set(data.files))
        require(not missing, f"model-{model} combined catalog missing arrays: {missing}")
        event_category = np.asarray(data["event_category"])
        base = np.asarray(data["event_base_weight_cps"])
        component = np.asarray(data["event_component"])
        source_bin = np.asarray(data["source_bin80"])
        importance = np.asarray(data["continuum_importance_weight"])
        w2_flags = np.asarray(data["w2_flags"])
        hit_start = np.asarray(data["hit_start"])
        hit_count = np.asarray(data["hit_count"])
        hit_code = np.asarray(data["hit_code"])
    n_events = len(event_category)
    n_hits = len(hit_code)
    require(n_events > 0, f"model-{model} combined catalog is empty")
    for name, array in (
        ("event_base_weight_cps", base),
        ("event_component", component),
        ("source_bin80", source_bin),
        ("continuum_importance_weight", importance),
        ("w2_flags", w2_flags),
        ("hit_start", hit_start),
        ("hit_count", hit_count),
    ):
        require(array.ndim == 1 and len(array) == n_events,
                f"model-{model} event array length differs: {name}")
    require(base.dtype == np.dtype("float64"),
            f"model-{model} event_base_weight_cps is not float64")
    require(component.dtype == np.dtype("uint8"),
            f"model-{model} event_component is not uint8")
    require(source_bin.dtype == np.dtype("uint8"),
            f"model-{model} source_bin80 is not uint8")
    require(np.issubdtype(importance.dtype, np.floating),
            f"model-{model} continuum importance is not floating")
    require(np.all(np.isfinite(base)) and np.all(base > 0.0),
            f"model-{model} catalog base weights are not finite positive")
    require(np.all(np.isfinite(importance)) and np.all(importance > 0.0),
            f"model-{model} catalog importance weights are not finite positive")
    require(np.all(component <= 2), f"model-{model} catalog has invalid component code")
    require(np.all((w2_flags.astype(np.uint64) & np.uint64(0xE0)) == 0),
            f"model-{model} catalog W2 flags use unknown bits")

    line_mask = component == COMPONENT_CODES["atm511"]
    continuum_mask = component == COMPONENT_CODES["gamma_continuum"]
    other_mask = component == COMPONENT_CODES["other"]
    require(np.any(line_mask), f"model-{model} catalog has no atm511 events")
    require(np.any(continuum_mask), f"model-{model} catalog has no continuum events")
    require(np.any(other_mask), f"model-{model} catalog has no retained other events")
    require(np.all(source_bin[line_mask] < 80),
            f"model-{model} line source bins are outside 0..79")
    require(set(np.unique(source_bin[line_mask]).tolist()) == set(range(80)),
            f"model-{model} line events do not cover 80 source bins")
    require(np.all(source_bin[~line_mask] == 255),
            f"model-{model} non-line events do not use source_bin80=255")
    require(np.all(importance[continuum_mask] <= 1.0),
            f"model-{model} continuum importance exceeds one")
    require(np.all(importance[~continuum_mask] == 1.0),
            f"model-{model} other/line importance must be exactly one")

    hit_start64 = hit_start.astype(np.int64, copy=False)
    hit_count64 = hit_count.astype(np.int64, copy=False)
    hit_end = hit_start64 + hit_count64
    require(np.all(hit_start64 >= 0) and np.all(hit_count64 >= 0),
            f"model-{model} catalog has negative hit ranges")
    require(np.all(hit_end <= n_hits), f"model-{model} hit ranges exceed hit arrays")
    require(int(hit_start64[0]) == 0, f"model-{model} first hit_start is not zero")
    require(np.all(hit_start64[1:] == hit_end[:-1]),
            f"model-{model} packed hit ranges are not contiguous")
    require(int(hit_end[-1]) == n_hits,
            f"model-{model} packed hit ranges do not span hit arrays")

    categories = sorted(
        category_registry.get("categories", []),
        key=lambda row: int(row["category_id"]),
    )
    require(categories, f"model-{model} category registry is empty")
    require(
        [int(row["category_id"]) for row in categories] == list(range(len(categories))),
        f"model-{model} category IDs are not contiguous",
    )
    expected_start = 0
    line_category_count = 0
    continuum_category_count = 0
    category_reports: list[dict[str, Any]] = []
    for category_id, row in enumerate(categories):
        start = int(row["event_start"])
        count = int(row["event_count"])
        stop = start + count
        require(start == expected_start and count > 0 and stop <= n_events,
                f"model-{model} category {category_id} range differs")
        require(np.all(event_category[start:stop] == category_id),
                f"model-{model} event_category differs in category {category_id}")
        name = component_name(row["component"])
        code = COMPONENT_CODES[name]
        require(np.all(component[start:stop] == code),
                f"model-{model} event_component differs in category {category_id}")
        category_weights = base[start:stop]
        moments = stats(category_weights, f"model-{model} category {category_id}")
        close(
            float(row["sum_event_base_weight_cps"]),
            float(moments["sumw"]),
            f"model-{model} category {category_id} sumw",
        )
        close(
            float(row["sum_event_base_weight2_cps2"]),
            float(moments["sumw2"]),
            f"model-{model} category {category_id} sumw2",
        )
        close(
            float(row["effective_sample_size"]),
            float(moments["effective_sample_size"]),
            f"model-{model} category {category_id} ESS",
        )
        if name == "gamma_continuum":
            continuum_category_count += 1
            require(row.get("stream") == "prompt" and row.get("family") == "gamma",
                    f"model-{model} continuum registry identity differs")
            require(row.get("weight_policy") == "per_event_catalog_array",
                    f"model-{model} continuum weight policy differs")
            proposal = float(row["proposal_event_weight_cps"])
            require(math.isfinite(proposal) and proposal > 0.0,
                    f"model-{model} continuum proposal weight is invalid")
            tolerance = max(2e-18, proposal * 2e-15)
            require(
                np.allclose(
                    category_weights,
                    proposal * importance[start:stop],
                    rtol=2e-12,
                    atol=tolerance,
                ),
                (
                    f"model-{model} continuum category {category_id} violates "
                    "event_base_weight=proposal_weight*(Jcont/Jtotal)"
                ),
            )
        elif name == "atm511":
            line_category_count += 1
            require(row.get("stream") == "prompt" and row.get("family") == "atm511",
                    f"model-{model} line registry identity differs")
            require(
                row.get("weight_policy")
                == "constant_transport_weight_with_bin80_timeline_importance",
                f"model-{model} line weight policy differs",
            )
            target_record = str(row.get("mono511_target_81x80", ""))
            require(target_record.endswith(
                "67_m05_mono511_flux_closure_20260823/outputs/"
                "00_source_closure/mono511_target_81x80.csv"
            ), f"model-{model} line category target authority differs")
        else:
            require(row.get("weight_policy") == "constant_category_weight",
                    f"model-{model} retained category weight policy differs")
            require(np.all(category_weights == category_weights[0]),
                    f"model-{model} retained category {category_id} weight is not constant")
        category_reports.append({
            "category_id": category_id,
            "stream": row.get("stream"),
            "family": row.get("family"),
            "component": name,
            "events": count,
            "sumw_cps": float(moments["sumw"]),
            "sumw2_cps2": float(moments["sumw2"]),
            "effective_sample_size": float(moments["effective_sample_size"]),
        })
        expected_start = stop
    require(expected_start == n_events,
            f"model-{model} category registry does not cover all events")
    require(line_category_count == 1, f"model-{model} must have exactly one line category")
    require(continuum_category_count == 1,
            f"model-{model} must have exactly one continuum category")

    component_reports: dict[str, dict[str, Any]] = {}
    for name in COMPONENTS:
        mask = component == COMPONENT_CODES[name]
        moments = stats(base[mask], f"model-{model} component {name}")
        component_reports[name] = {
            "events": int(moments["selected_raw"]),
            "sumw_cps": float(moments["sumw"]),
            "sumw2_cps2": float(moments["sumw2"]),
            "effective_sample_size": float(moments["effective_sample_size"]),
        }
        for authority_name, authority in (
            ("summary", summary.get("components", {})),
            ("audit", audit.get("components", {})),
        ):
            require(name in authority,
                    f"model-{model} {authority_name} lacks component {name}")
            recorded = authority[name]
            require(int(recorded["events"]) == int(moments["selected_raw"]),
                    f"model-{model} {authority_name} {name} events differ")
            for field, actual in (
                ("sumw_cps", float(moments["sumw"])),
                ("sumw2_cps2", float(moments["sumw2"])),
                ("effective_sample_size", float(moments["effective_sample_size"])),
            ):
                close(float(recorded[field]), actual,
                      f"model-{model} {authority_name} {name} {field}")

    require(int(summary["events"]) == n_events,
            f"model-{model} catalog summary event count differs")
    require(int(summary["hits"]) == n_hits,
            f"model-{model} catalog summary hit count differs")
    require(int(summary["categories"]) == len(categories),
            f"model-{model} catalog summary category count differs")
    require(
        audit.get("source_closure", {}).get("manifest_sha256")
        == sha256_file(source_dir / "source_closure.json"),
        f"model-{model} catalog/source manifest hash differs",
    )
    line_audit = audit.get("line", {})
    for key, actual in (
        ("incident_photons", line.incident_photons),
        ("detector_positive_events", line.detector_positive_events),
    ):
        require(int(line_audit[key]) == actual,
                f"model-{model} catalog line audit {key} differs")
    close(float(line_audit["event_weight_cps"]), line.event_weight_cps,
          f"model-{model} catalog line audit weight")

    line_positions = np.flatnonzero(line_mask)
    require(len(line_positions) == line.detector_positive_events,
            f"model-{model} catalog line event count differs from response")
    require(np.array_equal(source_bin[line_positions].astype(np.int64), line.all_bins),
            f"model-{model} copied line source bins differ")
    require(np.array_equal(base[line_positions], line.all_weights),
            f"model-{model} copied line weights differ")
    require(np.array_equal(w2_flags[line_positions].astype(np.uint8), line.all_w2_flags),
            f"model-{model} copied line response flags differ")
    selected_positions = line_positions[
        (w2_flags[line_positions] & FINAL_STAGE_BIT) != 0
    ]
    selected_bins = source_bin[selected_positions].astype(np.int64, copy=True)
    selected_weights = base[selected_positions].astype(np.float64, copy=True)
    require(np.array_equal(selected_bins, line.selected_bins),
            f"model-{model} selected line bins differ from response")
    require(np.array_equal(selected_weights, line.selected_weights),
            f"model-{model} selected line weights differ from response")

    summary_line = stats(base[line_mask], f"model-{model} all catalog line events")
    for field, actual in (
        ("line_detector_positive_events", int(summary_line["selected_raw"])),
        ("line_sumw_cps", float(summary_line["sumw"])),
        ("line_sumw2_cps2", float(summary_line["sumw2"])),
        ("line_effective_sample_size", float(summary_line["effective_sample_size"])),
    ):
        if isinstance(actual, int):
            require(int(summary[field]) == actual,
                    f"model-{model} catalog summary {field} differs")
        else:
            close(float(summary[field]), actual,
                  f"model-{model} catalog summary {field}")

    report = {
        "status": "PASS__CATALOG_SCHEMA_POSITIVE_WEIGHTS_SUMW2_ESS",
        "model": model,
        "events": n_events,
        "hits": n_hits,
        "categories": len(categories),
        "component_moments": component_reports,
        "categories_audited": category_reports,
        "continuum_weight_formula": (
            "event_base_weight_cps = proposal_event_weight_cps * "
            "continuum_importance_weight; downstream must use event_base_weight_cps "
            "without multiplying Jcont/Jtotal again"
        ),
        "minimum_continuum_importance_weight": float(np.min(importance[continuum_mask])),
        "maximum_continuum_importance_weight": float(np.max(importance[continuum_mask])),
        "line_final_selected_events": int(len(selected_weights)),
        "line_final_base_sumw_cps": float(np.sum(selected_weights, dtype=np.float64)),
        "line_final_base_sumw2_cps2": float(
            np.sum(selected_weights * selected_weights, dtype=np.float64)
        ),
        "hashes": {
            "summary.json": sha256_file(summary_path),
            "audit.json": sha256_file(audit_path),
            "category_registry.json": sha256_file(category_path),
            "component_registry.json": sha256_file(component_path),
            "combined_event_catalog.npz": sha256_file(catalog_path),
        },
    }
    return CatalogData(
        report=report,
        selected_line_bins=selected_bins,
        selected_line_weights=selected_weights,
    )


def trapezoid(y: np.ndarray, x: np.ndarray) -> float:
    values = np.asarray(y, dtype=np.float64)
    axis = np.asarray(x, dtype=np.float64)
    require(values.shape == axis.shape and values.ndim == 1,
            "trapezoid arrays have incompatible shapes")
    require(len(values) >= 2 and np.all(np.diff(axis) > 0.0),
            "trapezoid axis is invalid")
    return float(
        np.sum(
            0.5 * (values[:-1] + values[1:]) * np.diff(axis),
            dtype=np.float64,
        )
    )


def keyed_rows(
    rows: Sequence[Mapping[str, Any]],
    keys: Sequence[str],
    label: str,
) -> dict[tuple[Any, ...], Mapping[str, Any]]:
    output: dict[tuple[Any, ...], Mapping[str, Any]] = {}
    for row in rows:
        key: list[Any] = []
        for field in keys:
            if field in {"time_bin_id", "source_bin80"}:
                key.append(as_int(row, field))
            else:
                key.append(row[field])
        composite = tuple(key)
        require(composite not in output, f"{label} has duplicate key {composite}")
        output[composite] = row
    return output


def validate_paper_reference() -> dict[str, Any]:
    path = Path(PAPER_REFERENCE["path"])
    text = path.read_text(encoding="utf-8")
    required_fragments = (
        "86806.00",
        "15551.68",
        "5.406\\pm0.401",
        "5.415\\times10^{-5}",
        "2.229\\pm0.209",
        "2.238\\times10^{-5}",
    )
    missing = [fragment for fragment in required_fragments if fragment not in text]
    require(not missing, f"paper reference precision strings changed/missing: {missing}")
    return {
        "status": "PASS__PAPER_EFFECTIVE_DIGITS_LOCATED",
        "path": str(path),
        "sha256": sha256_file(path),
        "background_display_step_counts": float(
            PAPER_REFERENCE["background_display_step_counts"]
        ),
        "fmin_display_step_ph_cm2_s": float(
            PAPER_REFERENCE["fmin_display_step_ph_cm2_s"]
        ),
        "models": PAPER_REFERENCE["models"],
        "role": (
            "pre-flux-closure manuscript values are precision comparators only; "
            "they are not numerical authorities for the new flux-closed central values"
        ),
    }


def fmin_uncertainty_closure(
    *,
    background: float,
    kernel: float,
    background_sigma: float,
    signal_relative_sigma: float,
) -> dict[str, dict[str, float]]:
    values = fmin_values(background, kernel)
    output: dict[str, dict[str, float]] = {}
    for z in (3, 5):
        gaussian_key = f"Fmin_{z}sigma_gaussian_ph_cm2_s"
        gaussian = values[gaussian_key]
        gaussian_relative = math.hypot(
            0.5 * background_sigma / background,
            signal_relative_sigma,
        )
        output[gaussian_key] = {
            "value": gaussian,
            "standard_error": gaussian * gaussian_relative,
            "relative_standard_error": gaussian_relative,
        }
        asimov_key = f"Fmin_{z}sigma_poisson_asimov_ph_cm2_s"
        asimov = values[asimov_key]
        signal = asimov_required_signal(background, float(z))
        logarithm = math.log1p(signal / background)
        derivative = (signal / background - logarithm) / logarithm
        sigma = math.hypot(
            derivative * background_sigma / kernel,
            asimov * signal_relative_sigma,
        )
        output[asimov_key] = {
            "value": asimov,
            "standard_error": sigma,
            "relative_standard_error": sigma / asimov,
        }
    return output


def line_fmin_contributions(
    *,
    background: float,
    kernel: float,
    line_background_sigma: float,
) -> dict[str, dict[str, float]]:
    values = fmin_values(background, kernel)
    output: dict[str, dict[str, float]] = {}
    for z in (3, 5):
        gaussian_key = f"Fmin_{z}sigma_gaussian_ph_cm2_s"
        gaussian = values[gaussian_key]
        gaussian_sigma = gaussian * 0.5 * line_background_sigma / background
        output[gaussian_key] = {
            "line_MC_standard_error_contribution_ph_cm2_s": gaussian_sigma,
            "line_MC_relative_sigma_on_Fmin": gaussian_sigma / gaussian,
        }
        asimov_key = f"Fmin_{z}sigma_poisson_asimov_ph_cm2_s"
        asimov = values[asimov_key]
        signal = asimov_required_signal(background, float(z))
        logarithm = math.log1p(signal / background)
        derivative = (signal / background - logarithm) / logarithm
        asimov_sigma = derivative * line_background_sigma / kernel
        output[asimov_key] = {
            "line_MC_standard_error_contribution_ph_cm2_s": asimov_sigma,
            "line_MC_relative_sigma_on_Fmin": asimov_sigma / asimov,
        }
    return output


def precision_gate(
    *,
    total_standard_error: float,
    line_standard_error: float,
    display_step: float,
) -> dict[str, Any]:
    require(total_standard_error > 0.0 and display_step > 0.0,
            "precision gate received non-positive error/step")
    tolerance = max(2e-18, total_standard_error * 2e-12)
    require(
        line_standard_error <= total_standard_error + tolerance,
        "line error contribution exceeds existing total error",
    )
    without = math.sqrt(
        max(total_standard_error * total_standard_error
            - line_standard_error * line_standard_error, 0.0)
    )

    def rounded_index(value: float) -> int:
        return int(math.floor(value / display_step + 0.5))

    no_line_index = rounded_index(without)
    total_index = rounded_index(total_standard_error)
    rounded_without = no_line_index * display_step
    upper = (no_line_index + 0.5) * display_step
    allowed_line = math.sqrt(max(upper * upper - without * without, 0.0))
    same_digit = total_index == no_line_index
    return {
        "status": "INFORMATIONAL__LEGACY_LAST_DIGIT_DIAGNOSTIC",
        "decision_authority": False,
        "display_step_ph_cm2_s": display_step,
        "existing_total_standard_error_ph_cm2_s": total_standard_error,
        "line_standard_error_contribution_ph_cm2_s": line_standard_error,
        "standard_error_without_line_MC_ph_cm2_s": without,
        "rounded_existing_total_standard_error_ph_cm2_s": total_index * display_step,
        "rounded_standard_error_without_line_MC_ph_cm2_s": rounded_without,
        "same_reported_last_digit_with_and_without_line_MC": same_digit,
        "maximum_line_standard_error_for_same_reported_last_digit_ph_cm2_s": (
            allowed_line
        ),
        "passes": same_digit,
        "caveat": (
            "the 1e-8 step is inherited from an old TeX mantissa and must not "
            "force a transport top-up"
        ),
    }


def publication_topup_gate(
    *,
    fmin_value: float,
    total_standard_error: float,
    line_standard_error: float,
    current_incident: int,
) -> dict[str, Any]:
    """Apply the publication-level total-RSE and line-nondominance gates."""
    require(fmin_value > 0.0, "publication gate Fmin is not positive")
    require(total_standard_error > 0.0, "publication gate total error is not positive")
    require(line_standard_error >= 0.0, "publication gate line error is negative")
    require(current_incident > 0, "publication gate incident count is not positive")
    tolerance = max(2e-18, total_standard_error * 3e-11)
    require(
        line_standard_error <= total_standard_error + tolerance,
        "publication gate line error exceeds total error",
    )
    rest_standard_error = math.sqrt(
        max(
            total_standard_error * total_standard_error
            - line_standard_error * line_standard_error,
            0.0,
        )
    )
    total_rse = total_standard_error / fmin_value
    rest_rse = rest_standard_error / fmin_value
    total_variance = total_standard_error * total_standard_error
    line_variance_fraction = (
        line_standard_error * line_standard_error / total_variance
    )
    line_to_rest = (
        line_standard_error / rest_standard_error
        if rest_standard_error > 0.0
        else math.inf
    )
    rse_limit = PUBLICATION_TOTAL_MC_RSE_MAX
    fraction_limit = PUBLICATION_LINE_FMIN_VARIANCE_FRACTION_MAX
    require(0.0 < fraction_limit < 1.0, "line variance-fraction gate is invalid")
    rse_budget = rse_limit * fmin_value
    allowed_by_rse = math.sqrt(
        max(
            rse_budget * rse_budget
            - rest_standard_error * rest_standard_error,
            0.0,
        )
    )
    allowed_by_nondominance = rest_standard_error * math.sqrt(
        fraction_limit / (1.0 - fraction_limit)
    )
    allowed_simultaneous = min(allowed_by_rse, allowed_by_nondominance)
    numeric_tolerance = 3e-12
    passes_total_rse = total_rse <= rse_limit * (1.0 + numeric_tolerance)
    passes_line_fraction = (
        line_variance_fraction
        <= fraction_limit * (1.0 + numeric_tolerance)
    )
    passes_line_to_rest = (
        line_standard_error
        <= rest_standard_error * (1.0 + numeric_tolerance)
    )
    passes_current = (
        passes_total_rse and passes_line_fraction and passes_line_to_rest
    )

    if passes_current:
        decision = "NO_TOPUP"
        feasible = True
        required_incident: int | None = current_incident
        reason = (
            "current total Gaussian 3-sigma Fmin MC RSE is at most 10% and "
            "the line contributes at most half of Fmin variance"
        )
    elif rest_rse >= rse_limit * (1.0 - numeric_tolerance):
        decision = "LINE_TOPUP_NOT_BENEFICIAL"
        feasible = False
        required_incident = None
        reason = (
            "the non-line remainder alone reaches or exceeds the 10% total-MC "
            "RSE budget; reducing line variance cannot satisfy the publication gate"
        )
    elif allowed_simultaneous <= 0.0:
        decision = "LINE_TOPUP_NOT_BENEFICIAL"
        feasible = False
        required_incident = None
        reason = (
            "no positive line-error budget remains after the non-line remainder; "
            "no finite line top-up can satisfy both gates"
        )
    else:
        decision = "TOPUP_REQUIRED"
        feasible = True
        multiplier = (line_standard_error / allowed_simultaneous) ** 2
        required_incident = int(
            math.ceil(current_incident * multiplier * (1.0 + 2e-12))
        )
        required_incident = max(required_incident, current_incident + 1)
        reason = (
            "the incremental line variance is reducible and a finite line top-up "
            "can satisfy both publication gates"
        )

    if required_incident is None:
        projected: dict[str, float | None] = {
            "incident_scale": None,
            "line_standard_error_ph_cm2_s": None,
            "total_standard_error_ph_cm2_s": None,
            "total_MC_relative_standard_error": None,
            "line_Fmin_variance_fraction": None,
            "line_sigma_to_rest_sigma": None,
        }
    else:
        scale = required_incident / current_incident
        projected_line = line_standard_error / math.sqrt(scale)
        projected_total = math.hypot(rest_standard_error, projected_line)
        projected = {
            "incident_scale": scale,
            "line_standard_error_ph_cm2_s": projected_line,
            "total_standard_error_ph_cm2_s": projected_total,
            "total_MC_relative_standard_error": projected_total / fmin_value,
            "line_Fmin_variance_fraction": (
                projected_line * projected_line
                / (projected_total * projected_total)
            ),
            "line_sigma_to_rest_sigma": (
                projected_line / rest_standard_error
                if rest_standard_error > 0.0
                else None
            ),
        }
    return {
        "status": decision,
        "decision": decision,
        "decision_authority": True,
        "publication_metric": "Fmin_3sigma_gaussian_ph_cm2_s",
        "thresholds": {
            "total_MC_relative_standard_error_max": rse_limit,
            "line_Fmin_variance_fraction_max": fraction_limit,
            "line_sigma_to_rest_sigma_max": 1.0,
        },
        "current": {
            "Fmin_ph_cm2_s": fmin_value,
            "total_standard_error_ph_cm2_s": total_standard_error,
            "total_MC_relative_standard_error": total_rse,
            "line_standard_error_ph_cm2_s": line_standard_error,
            "rest_standard_error_ph_cm2_s": rest_standard_error,
            "rest_MC_relative_standard_error": rest_rse,
            "line_Fmin_variance_fraction": line_variance_fraction,
            "line_sigma_to_rest_sigma": (
                line_to_rest if math.isfinite(line_to_rest) else None
            ),
            "passes_total_MC_RSE": passes_total_rse,
            "passes_line_variance_fraction": passes_line_fraction,
            "passes_line_sigma_not_greater_than_rest": passes_line_to_rest,
            "passes_both_publication_gates": passes_current,
        },
        "line_error_budgets_ph_cm2_s": {
            "maximum_from_total_MC_RSE": allowed_by_rse,
            "maximum_from_variance_nondominance": allowed_by_nondominance,
            "maximum_simultaneously_allowed": allowed_simultaneous,
        },
        "line_topup_can_satisfy_both_gates": feasible,
        "required_total_incident_photons": required_incident,
        "projected_at_required_incident": projected,
        "reason": reason,
        "formulas": {
            "rest_error": (
                "sigma_F_rest = sqrt(sigma_F_total^2 - sigma_F_line^2)"
            ),
            "total_RSE": "RSE_total = sigma_F_total / Fmin",
            "line_variance_fraction": (
                "f_line = sigma_F_line^2 / "
                "(sigma_F_rest^2 + sigma_F_line^2)"
            ),
            "allowed_line_from_RSE": (
                "sqrt((0.10*Fmin)^2 - sigma_F_rest^2)"
            ),
            "allowed_line_from_nondominance": (
                "sigma_F_rest*sqrt(0.50/(1-0.50)) = sigma_F_rest"
            ),
            "required_incident": (
                "ceil(N_current * "
                "(sigma_F_line_current/min(allowed_RSE,allowed_nondominance))^2)"
            ),
        },
    }


def topup_from_timeline(
    *,
    model: str,
    line: LineData,
    integrated_line: Mapping[str, Any],
    background: float,
    kernel: float,
    uncertainty: Mapping[str, Any],
) -> dict[str, Any]:
    line_sigma_counts = float(integrated_line["sigma"])
    require(background > 0.0 and kernel > 0.0, f"model-{model} final B/K invalid")
    contributions = line_fmin_contributions(
        background=background,
        kernel=kernel,
        line_background_sigma=line_sigma_counts,
    )
    existing_fmin = uncertainty["Fmin"]
    for key, item in contributions.items():
        require(key in existing_fmin, f"model-{model} uncertainty lacks {key}")
        existing_sigma = float(existing_fmin[key]["standard_error"])
        line_sigma = float(item["line_MC_standard_error_contribution_ph_cm2_s"])
        require(line_sigma <= existing_sigma * (1.0 + 3e-11),
                f"model-{model} line contribution exceeds total for {key}")
        item["existing_total_standard_error_ph_cm2_s"] = existing_sigma
        item["fraction_of_existing_total_standard_error"] = (
            line_sigma / existing_sigma
        )
        item["standard_error_without_line_MC_ph_cm2_s"] = math.sqrt(
            max(existing_sigma * existing_sigma - line_sigma * line_sigma, 0.0)
        )

    gate_key = "Fmin_3sigma_gaussian_ph_cm2_s"
    legacy_diagnostic = precision_gate(
        total_standard_error=float(existing_fmin[gate_key]["standard_error"]),
        line_standard_error=float(
            contributions[gate_key][
                "line_MC_standard_error_contribution_ph_cm2_s"
            ]
        ),
        display_step=float(PAPER_REFERENCE["fmin_display_step_ph_cm2_s"]),
    )
    current_incident = int(line.incident_photons)
    current_selected = int(len(line.selected_weights))
    current_ess = float(integrated_line["effective_sample_size"])
    current_line_fmin_sigma = float(
        contributions[gate_key][
            "line_MC_standard_error_contribution_ph_cm2_s"
        ]
    )
    publication_gate = publication_topup_gate(
        fmin_value=float(existing_fmin[gate_key]["value"]),
        total_standard_error=float(existing_fmin[gate_key]["standard_error"]),
        line_standard_error=current_line_fmin_sigma,
        current_incident=current_incident,
    )
    decision = str(publication_gate["decision"])
    required_value = publication_gate["required_total_incident_photons"]
    required_incident = int(required_value) if required_value is not None else None
    if required_incident is None:
        additional: int | None = None
        projected_selected: float | None = None
        projected_ess: float | None = None
    else:
        scale = required_incident / current_incident
        additional = required_incident - current_incident
        projected_selected = current_selected * scale
        projected_ess = current_ess * scale
    return {
        "model": model,
        "decision": decision,
        "line_incident_photons": current_incident,
        "line_detector_positive_events": line.detector_positive_events,
        "line_final_selected_events": current_selected,
        "integrated_line_background_counts": float(integrated_line["sumw"]),
        "integrated_line_sumw2_counts2": float(integrated_line["sumw2"]),
        "integrated_line_MC_sigma_counts": line_sigma_counts,
        "integrated_line_effective_sample_size": current_ess,
        "line_MC_relative_sigma_on_line_background": (
            line_sigma_counts / float(integrated_line["sumw"])
        ),
        "line_MC_relative_sigma_on_total_B": line_sigma_counts / background,
        "line_MC_fraction_of_total_background_transport_variance": (
            float(integrated_line["sumw2"])
            / float(uncertainty["background_transport_MC_sigma_counts"]) ** 2
        ),
        "Fmin_line_MC_contributions": contributions,
        "publication_precision_gate": publication_gate,
        "legacy_last_digit_diagnostic": legacy_diagnostic,
        "required_total_incident_photons": required_incident,
        "additional_incident_photons": additional,
        "projected_final_selected_events": projected_selected,
        "projected_integrated_line_effective_sample_size": projected_ess,
        "scaling_assumption": (
            "fixed proposal angular distribution, geometry, response, and physical "
            "mean; line transport variance scales as 1/Nincident and selected/ESS "
            "scale linearly with Nincident"
        ),
        "background_count_display_comparison": {
            "paper_value_counts": float(
                PAPER_REFERENCE["models"][model]["background_counts"]
            ),
            "paper_display_step_counts": float(
                PAPER_REFERENCE["background_display_step_counts"]
            ),
            "fluxclosed_value_counts": background,
            "topup_gate_applies": False,
            "reason": (
                "the manuscript prints no uncertainty beside B; MC variance does "
                "not define a deterministic central-value rounding gate"
            ),
        },
        "paper_Fmin_error_comparison": {
            "pre_fluxclosure_paper_standard_error_ph_cm2_s": float(
                PAPER_REFERENCE["models"][model][
                    "Fmin_3sigma_gaussian_standard_error_ph_cm2_s"
                ]
            ),
            "fluxclosed_existing_total_standard_error_ph_cm2_s": float(
                existing_fmin[gate_key]["standard_error"]
            ),
            "ratio_fluxclosed_to_paper": float(
                existing_fmin[gate_key]["standard_error"]
            )
            / float(
                PAPER_REFERENCE["models"][model][
                    "Fmin_3sigma_gaussian_standard_error_ph_cm2_s"
                ]
            ),
        },
    }


def validate_day15_products(
    *,
    model: str,
    timeline_dir: Path,
    summary: Mapping[str, Any],
    anchor_rate_map: Mapping[tuple[Any, ...], Mapping[str, Any]],
    anchor_component_map: Mapping[tuple[Any, ...], Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate schema-2 day-15 products and all additive closures."""
    require(int(summary.get("schema_version", -1)) == 2,
            f"model-{model} timeline summary is not schema 2")
    product_schema = summary.get("day15_product_schema", {})
    require(int(product_schema.get("schema_version", -1)) == 2,
            f"model-{model} day-15 product schema is not version 2")
    require(
        product_schema.get("closure_status")
        == "PASS__DAY15_PRODUCTS_ADDITIVE_CUTFLOW_CLOSED",
        f"model-{model} day-15 product closure status differs",
    )

    def validate_common_row(
        row: Mapping[str, Any], label: str, *, with_ess: bool
    ) -> tuple[int, float, float]:
        require(as_int(row, "time_bin_id") == 60,
                f"{label} time_bin_id is not 60")
        close(as_float(row, "day_mid"), 15.0, f"{label} day_mid")
        selected = as_int(row, "selected_raw")
        sumw = as_float(row, "sumw_cps")
        sumw2 = as_float(row, "sumw2_cps2")
        require(selected >= 0 and sumw >= 0.0 and sumw2 >= 0.0,
                f"{label} contains a negative moment")
        close(as_float(row, "sqrt_sumw2_cps"), math.sqrt(sumw2),
              f"{label} sqrt(sumw2)")
        if with_ess:
            if sumw2 > 0.0:
                close(
                    as_float(row, "effective_sample_size"),
                    sumw * sumw / sumw2,
                    f"{label} ESS",
                )
            else:
                require(str(row["effective_sample_size"]).strip() == "",
                        f"{label} zero-variance ESS should be blank")
        return selected, sumw, sumw2

    cutflow_path = timeline_dir / "direct_cutflow_day15.csv"
    cutflow = read_csv(cutflow_path)
    require_columns(
        cutflow,
        (
            "time_bin_id",
            "day_mid",
            "stream",
            "family",
            "component",
            "window_id",
            "stage",
            "selected_raw",
            "sumw_cps",
            "sumw2_cps2",
            "sqrt_sumw2_cps",
            "effective_sample_size",
        ),
        f"model-{model} schema-2 day15 cutflow",
    )
    cutflow_seen: set[tuple[str, str, str, str, str]] = set()
    cutflow_component: dict[
        tuple[str, str, str], list[float | int]
    ] = {}
    for row in cutflow:
        stream = str(row["stream"])
        family = str(row["family"])
        component = str(row["component"])
        window = str(row["window_id"])
        stage = str(row["stage"])
        require(stream in {"prompt", "delayed"},
                f"model-{model} cutflow stream differs: {stream}")
        require(bool(family), f"model-{model} cutflow family is empty")
        require(component in COMPONENTS,
                f"model-{model} cutflow component differs: {component}")
        require(window in WINDOW_FIELDS and stage in STAGES,
                f"model-{model} cutflow window/stage differs")
        key = (stream, family, component, window, stage)
        require(key not in cutflow_seen,
                f"model-{model} duplicate cutflow key {key}")
        cutflow_seen.add(key)
        selected, sumw, sumw2 = validate_common_row(
            row, f"model-{model} cutflow {key}", with_ess=True
        )
        target = cutflow_component.setdefault(
            (window, stage, component), [0, 0.0, 0.0]
        )
        target[0] = int(target[0]) + selected
        target[1] = float(target[1]) + sumw
        target[2] = float(target[2]) + sumw2
    require(cutflow_seen, f"model-{model} day15 cutflow is empty")
    for window in WINDOW_FIELDS:
        for stage in STAGES:
            for component in COMPONENTS:
                key = (window, stage, component)
                require(key in cutflow_component,
                        f"model-{model} cutflow lacks {key}")
                actual = cutflow_component[key]
                anchor = anchor_component_map[(60, window, stage, component)]
                require(int(actual[0]) == as_int(anchor, "selected_raw"),
                        f"model-{model} cutflow {key} selected closure differs")
                close(float(actual[1]), as_float(anchor, "direct_rate_cps"),
                      f"model-{model} cutflow {key} sumw closure")
                close(
                    float(actual[2]),
                    as_float(anchor, "direct_sum_W_i2_cps2"),
                    f"model-{model} cutflow {key} sumw2 closure",
                )

    spectrum_path = timeline_dir / "direct_measured_energy_day15_0p25keV.csv"
    spectrum = read_csv(spectrum_path)
    require_columns(
        spectrum,
        (
            "time_bin_id",
            "day_mid",
            "stage",
            "stream",
            "component",
            "energy_low_keV",
            "energy_high_keV",
            "selected_raw",
            "sumw_cps",
            "sumw2_cps2",
            "sqrt_sumw2_cps",
        ),
        f"model-{model} schema-2 day15 spectrum",
    )
    expected_spectrum_rows = (
        len(SPECTRUM_STAGES) * len(STREAM_LABELS)
        * len(COMPONENT_LABELS) * 280
    )
    require(len(spectrum) == expected_spectrum_rows == 10_080,
            f"model-{model} spectrum row count is {len(spectrum)}, not 10080")
    spectrum_map: dict[
        tuple[str, str, str, int], tuple[int, float, float]
    ] = {}
    for row in spectrum:
        stage = str(row["stage"])
        stream = str(row["stream"])
        component = str(row["component"])
        require(stage in SPECTRUM_STAGES,
                f"model-{model} spectrum stage differs: {stage}")
        require(stream in STREAM_LABELS,
                f"model-{model} spectrum stream differs: {stream}")
        require(component in COMPONENT_LABELS,
                f"model-{model} spectrum component differs: {component}")
        low = as_float(row, "energy_low_keV")
        high = as_float(row, "energy_high_keV")
        energy_index = int(round((low - 480.0) / 0.25))
        require(0 <= energy_index < 280,
                f"model-{model} spectrum energy bin is outside 480--550 keV")
        close(low, 480.0 + 0.25 * energy_index,
              f"model-{model} spectrum low edge")
        close(high, low + 0.25, f"model-{model} spectrum high edge")
        key = (stage, stream, component, energy_index)
        require(key not in spectrum_map,
                f"model-{model} duplicate spectrum key {key}")
        spectrum_map[key] = validate_common_row(
            row, f"model-{model} spectrum {key}", with_ess=False
        )
    require(len(spectrum_map) == expected_spectrum_rows,
            f"model-{model} spectrum key grid is incomplete")
    for stage in SPECTRUM_STAGES:
        for energy_index in range(280):
            for moment_index, moment_name in enumerate(
                ("selected_raw", "sumw", "sumw2")
            ):
                all_value = spectrum_map[
                    (stage, "all", "all", energy_index)
                ][moment_index]
                stream_sum = sum(
                    spectrum_map[(stage, stream, "all", energy_index)][
                        moment_index
                    ]
                    for stream in ("prompt", "delayed")
                )
                component_sum = sum(
                    spectrum_map[(stage, "all", component, energy_index)][
                        moment_index
                    ]
                    for component in COMPONENTS
                )
                if moment_index == 0:
                    require(int(all_value) == int(stream_sum) == int(component_sum),
                            f"model-{model} spectrum {stage}/{energy_index} "
                            f"{moment_name} all closure differs")
                else:
                    close(float(all_value), float(stream_sum),
                          f"model-{model} spectrum stream {moment_name} closure")
                    close(float(all_value), float(component_sum),
                          f"model-{model} spectrum component {moment_name} closure")
                for component in COMPONENTS:
                    component_all = spectrum_map[
                        (stage, "all", component, energy_index)
                    ][moment_index]
                    component_stream_sum = sum(
                        spectrum_map[
                            (stage, stream, component, energy_index)
                        ][moment_index]
                        for stream in ("prompt", "delayed")
                    )
                    if moment_index == 0:
                        require(int(component_all) == int(component_stream_sum),
                                f"model-{model} spectrum {component} stream "
                                f"{moment_name} closure differs")
                    else:
                        close(
                            float(component_all),
                            float(component_stream_sum),
                            f"model-{model} spectrum {component} stream "
                            f"{moment_name} closure",
                        )
        for component in COMPONENT_LABELS:
            totals = [
                sum(
                    spectrum_map[(stage, "all", component, index)][moment]
                    for index in range(280)
                )
                for moment in range(3)
            ]
            if component == "all":
                anchor = anchor_rate_map[(60, "broad_480_550", stage)]
                expected = (
                    as_int(anchor, "direct_selected_raw"),
                    as_float(anchor, "direct_no_coincidence_rate_cps"),
                    as_float(anchor, "direct_sum_W_i2_cps2"),
                )
            else:
                anchor = anchor_component_map[
                    (60, "broad_480_550", stage, component)
                ]
                expected = (
                    as_int(anchor, "selected_raw"),
                    as_float(anchor, "direct_rate_cps"),
                    as_float(anchor, "direct_sum_W_i2_cps2"),
                )
            require(int(totals[0]) == int(expected[0]),
                    f"model-{model} spectrum {stage}/{component} selected "
                    "does not close to cutflow")
            close(float(totals[1]), float(expected[1]),
                  f"model-{model} spectrum {stage}/{component} sumw cutflow closure")
            close(float(totals[2]), float(expected[2]),
                  f"model-{model} spectrum {stage}/{component} sumw2 cutflow closure")

    multiplicity_path = timeline_dir / "direct_hit_multiplicity_day15.csv"
    multiplicity = read_csv(multiplicity_path)
    require_columns(
        multiplicity,
        (
            "time_bin_id",
            "day_mid",
            "window_id",
            "stage",
            "component",
            "hit_multiplicity",
            "selected_raw",
            "sumw_cps",
            "sumw2_cps2",
            "sqrt_sumw2_cps",
        ),
        f"model-{model} schema-2 day15 multiplicity",
    )
    multiplicity_map: dict[
        tuple[str, str, str, int], tuple[int, float, float]
    ] = {}
    values_by_window: dict[str, set[int]] = {
        window: set() for window in WINDOW_FIELDS
    }
    for row in multiplicity:
        window = str(row["window_id"])
        stage = str(row["stage"])
        component = str(row["component"])
        value = as_int(row, "hit_multiplicity")
        require(window in WINDOW_FIELDS and stage in STAGES,
                f"model-{model} multiplicity window/stage differs")
        require(component in COMPONENT_LABELS,
                f"model-{model} multiplicity component differs")
        require(value >= 0, f"model-{model} multiplicity value is negative")
        key = (window, stage, component, value)
        require(key not in multiplicity_map,
                f"model-{model} duplicate multiplicity key {key}")
        multiplicity_map[key] = validate_common_row(
            row, f"model-{model} multiplicity {key}", with_ess=False
        )
        values_by_window[window].add(value)
    require(multiplicity_map, f"model-{model} multiplicity table is empty")
    expected_multiplicity_rows = 0
    for window, retained_values in values_by_window.items():
        require(retained_values, f"model-{model} multiplicity lacks window {window}")
        expected_multiplicity_rows += (
            len(STAGES) * len(COMPONENT_LABELS) * len(retained_values)
        )
        for stage in STAGES:
            for component in COMPONENT_LABELS:
                present_values = {
                    key[3]
                    for key in multiplicity_map
                    if key[:3] == (window, stage, component)
                }
                require(present_values == retained_values,
                        f"model-{model} multiplicity rectangular grain differs "
                        f"for {(window, stage, component)}")
            for value in retained_values:
                for moment_index, moment_name in enumerate(
                    ("selected_raw", "sumw", "sumw2")
                ):
                    all_value = multiplicity_map[
                        (window, stage, "all", value)
                    ][moment_index]
                    component_sum = sum(
                        multiplicity_map[
                            (window, stage, component, value)
                        ][moment_index]
                        for component in COMPONENTS
                    )
                    if moment_index == 0:
                        require(int(all_value) == int(component_sum),
                                f"model-{model} multiplicity component "
                                f"{moment_name} closure differs")
                    else:
                        close(
                            float(all_value),
                            float(component_sum),
                            f"model-{model} multiplicity component "
                            f"{moment_name} closure",
                        )
            for component in COMPONENT_LABELS:
                totals = [
                    sum(
                        multiplicity_map[
                            (window, stage, component, value)
                        ][moment]
                        for value in retained_values
                    )
                    for moment in range(3)
                ]
                if component == "all":
                    anchor = anchor_rate_map[(60, window, stage)]
                    expected = (
                        as_int(anchor, "direct_selected_raw"),
                        as_float(anchor, "direct_no_coincidence_rate_cps"),
                        as_float(anchor, "direct_sum_W_i2_cps2"),
                    )
                else:
                    anchor = anchor_component_map[
                        (60, window, stage, component)
                    ]
                    expected = (
                        as_int(anchor, "selected_raw"),
                        as_float(anchor, "direct_rate_cps"),
                        as_float(anchor, "direct_sum_W_i2_cps2"),
                    )
                require(int(totals[0]) == int(expected[0]),
                        f"model-{model} multiplicity {window}/{stage}/"
                        f"{component} selected cutflow closure differs")
                close(float(totals[1]), float(expected[1]),
                      f"model-{model} multiplicity sumw cutflow closure")
                close(float(totals[2]), float(expected[2]),
                      f"model-{model} multiplicity sumw2 cutflow closure")
    require(len(multiplicity) == expected_multiplicity_rows,
            f"model-{model} multiplicity row count/grain differs")

    spectrum_schema = product_schema.get(
        "direct_measured_energy_day15_0p25keV.csv", {}
    )
    multiplicity_schema = product_schema.get(
        "direct_hit_multiplicity_day15.csv", {}
    )
    cutflow_schema = product_schema.get("direct_cutflow_day15.csv", {})
    require(int(spectrum_schema.get("rows", -1)) == len(spectrum),
            f"model-{model} recorded spectrum row count differs")
    require(int(multiplicity_schema.get("rows", -1)) == len(multiplicity),
            f"model-{model} recorded multiplicity row count differs")
    require(
        spectrum_schema.get("grain")
        == "stage x stream x component x 0.25-keV energy bin"
        and spectrum_schema.get("energy_range_keV") == [480.0, 550.0]
        and math.isclose(
            float(spectrum_schema.get("energy_bin_width_keV", -1.0)),
            0.25,
            rel_tol=0.0,
            abs_tol=1e-15,
        )
        and cutflow_schema.get("grain")
        == "stream x family x component x window_id x stage"
        and multiplicity_schema.get("grain")
        == "window_id x stage x component x retained hit_multiplicity",
        f"model-{model} recorded day15 product grains differ",
    )
    require(
        spectrum_schema.get("stages") == list(SPECTRUM_STAGES)
        and spectrum_schema.get("streams") == list(STREAM_LABELS)
        and spectrum_schema.get("components") == list(COMPONENT_LABELS),
        f"model-{model} recorded spectrum axes differ",
    )
    require(
        cutflow_schema.get("windows") == list(WINDOW_FIELDS)
        and cutflow_schema.get("stages") == list(STAGES),
        f"model-{model} recorded cutflow axes differ",
    )
    require(
        multiplicity_schema.get("windows") == list(WINDOW_FIELDS)
        and multiplicity_schema.get("stages") == list(STAGES)
        and multiplicity_schema.get("components") == list(COMPONENT_LABELS),
        f"model-{model} recorded multiplicity axes differ",
    )

    day15_components = summary.get("day15_W2_final_component_rates", {})
    require(set(day15_components) == {*COMPONENTS, "total"},
            f"model-{model} day15 component summary labels differ")
    for component in (*COMPONENTS, "total"):
        recorded = day15_components[component]
        if component == "total":
            anchor = anchor_rate_map[(60, FINAL_WINDOW, FINAL_STAGE)]
            expected = {
                "selected_raw": as_int(anchor, "direct_selected_raw"),
                "rate_cps": as_float(
                    anchor, "direct_no_coincidence_rate_cps"
                ),
                "sum_wi2_cps2": as_float(
                    anchor, "direct_sum_W_i2_cps2"
                ),
            }
        else:
            anchor = anchor_component_map[
                (60, FINAL_WINDOW, FINAL_STAGE, component)
            ]
            expected = {
                "selected_raw": as_int(anchor, "selected_raw"),
                "rate_cps": as_float(anchor, "direct_rate_cps"),
                "sum_wi2_cps2": as_float(
                    anchor, "direct_sum_W_i2_cps2"
                ),
            }
        require(int(recorded["selected_raw"]) == expected["selected_raw"],
                f"model-{model} day15 summary {component} selected differs")
        close(float(recorded["rate_cps"]), expected["rate_cps"],
              f"model-{model} day15 summary {component} rate")
        close(float(recorded["sum_wi2_cps2"]), expected["sum_wi2_cps2"],
              f"model-{model} day15 summary {component} sumw2")
        close(float(recorded["transport_sigma_cps"]),
              math.sqrt(expected["sum_wi2_cps2"]),
              f"model-{model} day15 summary {component} sigma")
        if expected["sum_wi2_cps2"] > 0.0:
            close(
                float(recorded["effective_sample_size"]),
                expected["rate_cps"] ** 2 / expected["sum_wi2_cps2"],
                f"model-{model} day15 summary {component} ESS",
            )
    return {
        "status": "PASS__SCHEMA2_DAY15_PRODUCTS_ADDITIVE_CLOSED",
        "schema_version": 2,
        "cutflow_rows": len(cutflow),
        "spectrum_rows": len(spectrum),
        "multiplicity_rows": len(multiplicity),
        "spectrum_expected_rows": expected_spectrum_rows,
        "cutflow_grain": (
            "stream x family x component x window_id x stage"
        ),
        "spectrum_grain": (
            "stage x stream x component x 0.25-keV energy bin"
        ),
        "multiplicity_grain": (
            "window_id x stage x component x retained hit_multiplicity"
        ),
    }


def validate_timeline(
    model: str,
    timeline_dir: Path,
    source: SourceData,
    catalog: CatalogData,
    line: LineData,
) -> tuple[dict[str, Any], dict[str, Any]]:
    summary_path = timeline_dir / "summary.json"
    anchor_rate_path = timeline_dir / "anchor_timeline_rates.csv"
    anchor_component_path = timeline_dir / "anchor_transport_components.csv"
    mission_path = timeline_dir / "mission_timeline_81nodes.csv"
    mission_component_path = timeline_dir / "mission_transport_components.csv"
    summary = load_json(summary_path)
    require(
        summary.get("status") == "PASS__M05_FLUXCLOSED_COMMON_TIME_TIMELINE",
        f"model-{model} timeline status is not PASS",
    )
    require(summary.get("model") == model, f"model-{model} timeline summary model differs")
    require(set(summary.get("outputs", [])) == set(TIMELINE_FILES),
            f"model-{model} timeline output manifest differs")

    anchor_rates = read_csv(anchor_rate_path)
    require_columns(
        anchor_rates,
        (
            "time_bin_id",
            "day_mid",
            "window_id",
            "stage",
            "direct_no_coincidence_rate_cps",
            "direct_sum_W_i2_cps2",
            "direct_transport_sigma_cps",
            "direct_transport_effective_sample_size",
            "direct_selected_raw",
            "timeline_counts",
            "timeline_rate_cps",
            "timeline_rate_standard_error_cps",
            "timeline_to_direct_ratio",
            "signal_accidental_survival",
            "signal_survival_standard_error",
        ),
        f"model-{model} anchor timeline rates",
    )
    require(len(anchor_rates) == 5 * 2 * 5,
            f"model-{model} anchor rate row count differs")
    anchor_rate_map = keyed_rows(
        anchor_rates,
        ("time_bin_id", "window_id", "stage"),
        f"model-{model} anchor rate table",
    )
    expected_anchor_keys = {
        (node, window, stage)
        for node in ANCHOR_NODES
        for window in WINDOW_FIELDS
        for stage in STAGES
    }
    require(set(anchor_rate_map) == expected_anchor_keys,
            f"model-{model} anchor rate key coverage differs")

    anchor_components = read_csv(anchor_component_path)
    require_columns(
        anchor_components,
        (
            "time_bin_id",
            "day_mid",
            "window_id",
            "stage",
            "component",
            "selected_raw",
            "direct_rate_cps",
            "direct_sum_W_i2_cps2",
            "direct_transport_sigma_cps",
            "direct_transport_effective_sample_size",
        ),
        f"model-{model} anchor transport components",
    )
    require(len(anchor_components) == 5 * 2 * 5 * 3,
            f"model-{model} anchor component row count differs")
    anchor_component_map = keyed_rows(
        anchor_components,
        ("time_bin_id", "window_id", "stage", "component"),
        f"model-{model} anchor component table",
    )
    expected_component_keys = {
        (node, window, stage, component_name_value)
        for node in ANCHOR_NODES
        for window in WINDOW_FIELDS
        for stage in STAGES
        for component_name_value in COMPONENTS
    }
    require(set(anchor_component_map) == expected_component_keys,
            f"model-{model} anchor component key coverage differs")

    anchor_ratio = np.empty(5, dtype=np.float64)
    anchor_ratio_error = np.empty(5, dtype=np.float64)
    anchor_survival = np.empty(5, dtype=np.float64)
    anchor_survival_error = np.empty(5, dtype=np.float64)
    summary_anchors = summary.get("anchors", {})
    require(set(summary_anchors) == {str(node) for node in ANCHOR_NODES},
            f"model-{model} summary anchor keys differ")
    for index, node in enumerate(ANCHOR_NODES):
        row = anchor_rate_map[(node, FINAL_WINDOW, FINAL_STAGE)]
        direct = as_float(row, "direct_no_coincidence_rate_cps")
        direct_variance = as_float(row, "direct_sum_W_i2_cps2")
        close(as_float(row, "direct_transport_sigma_cps"), math.sqrt(direct_variance),
              f"model-{model} anchor {node} direct sigma")
        close(
            as_float(row, "direct_transport_effective_sample_size"),
            direct * direct / direct_variance,
            f"model-{model} anchor {node} direct ESS",
        )
        timeline_count = as_int(row, "timeline_counts")
        timeline_rate = as_float(row, "timeline_rate_cps")
        timeline_rate_error = as_float(row, "timeline_rate_standard_error_cps")
        require(timeline_count > 0 and timeline_rate > 0.0 and direct > 0.0,
                f"model-{model} anchor {node} final rate is non-positive")
        ratio = as_float(row, "timeline_to_direct_ratio")
        close(ratio, timeline_rate / direct,
              f"model-{model} anchor {node} timeline/direct ratio")
        ratio_error = timeline_rate_error / direct
        anchor_ratio[index] = ratio
        anchor_ratio_error[index] = ratio_error
        anchor_survival[index] = as_float(row, "signal_accidental_survival")
        anchor_survival_error[index] = as_float(
            row, "signal_survival_standard_error"
        )
        recorded = summary_anchors[str(node)]
        close(float(recorded["timeline_to_direct_ratio"]), ratio,
              f"model-{model} summary anchor {node} ratio")
        close(
            float(recorded["timeline_to_direct_ratio_standard_error"]),
            ratio_error,
            f"model-{model} summary anchor {node} ratio error",
        )
        close(
            float(recorded["signal_probe"][
                "conditional_signal_accidental_survival"
            ]),
            anchor_survival[index],
            f"model-{model} summary anchor {node} survival",
        )
        close(
            float(recorded["signal_probe"]["binomial_standard_error"]),
            anchor_survival_error[index],
            f"model-{model} summary anchor {node} survival error",
        )
        component_rate = 0.0
        component_variance = 0.0
        component_selected = 0
        for name in COMPONENTS:
            component_row = anchor_component_map[
                (node, FINAL_WINDOW, FINAL_STAGE, name)
            ]
            value = as_float(component_row, "direct_rate_cps")
            variance = as_float(component_row, "direct_sum_W_i2_cps2")
            selected = as_int(component_row, "selected_raw")
            close(
                as_float(component_row, "direct_transport_sigma_cps"),
                math.sqrt(variance),
                f"model-{model} anchor {node} {name} sigma",
            )
            if variance > 0.0:
                close(
                    as_float(
                        component_row,
                        "direct_transport_effective_sample_size",
                    ),
                    value * value / variance,
                    f"model-{model} anchor {node} {name} ESS",
                )
            component_rate += value
            component_variance += variance
            component_selected += selected
        close(component_rate, direct, f"model-{model} anchor {node} component rate sum")
        close(
            component_variance,
            direct_variance,
            f"model-{model} anchor {node} component variance sum",
        )
        require(component_selected == as_int(row, "direct_selected_raw"),
                f"model-{model} anchor {node} component selected sum differs")

    day15_product_report = validate_day15_products(
        model=model,
        timeline_dir=timeline_dir,
        summary=summary,
        anchor_rate_map=anchor_rate_map,
        anchor_component_map=anchor_component_map,
    )

    mission = read_csv(mission_path)
    require_columns(
        mission,
        (
            "time_bin_id",
            "day_mid",
            "direct_W2_final_no_coincidence_cps",
            "direct_sum_W_i2_cps2",
            "direct_transport_sigma_cps",
            "direct_transport_effective_sample_size",
            "interpolated_background_timeline_ratio",
            "mature_background_W2_final_cps",
            "mature_background_sum_W_i2_cps2",
            "conditional_signal_accidental_survival",
            "T_atm_511_slant45",
            "conditional_signal_Aeff_cm2",
            "conditional_signal_kernel_cm2",
            "cumulative_background_counts",
            "cumulative_signal_counts_per_unit_flux",
            "cumulative_transport_sum_W_i2_counts2",
            "cumulative_transport_sigma_counts",
            "cumulative_transport_effective_sample_size",
            "direct_atm511_cps",
            "direct_atm511_sum_W_i2_cps2",
            "cumulative_atm511_background_counts",
            "cumulative_atm511_sum_W_i2_counts2",
        ),
        f"model-{model} mission timeline",
    )
    require(len(mission) == 81, f"model-{model} mission timeline is not 81 rows")
    check_axis(mission, "time_bin_id", range(81), f"model-{model} mission timeline")
    days = np.asarray([as_float(row, "day_mid") for row in mission], dtype=np.float64)
    require(np.allclose(days, source.days, rtol=0.0, atol=2e-14),
            f"model-{model} mission/source day axes differ")
    require(days[0] == 0.0 and days[-1] == 20.0 and np.all(np.diff(days) > 0.0),
            f"model-{model} mission day axis is invalid")
    ratio_by_node = np.interp(
        np.arange(81, dtype=np.float64),
        np.asarray(ANCHOR_NODES, dtype=np.float64),
        anchor_ratio,
    )
    survival_by_node = np.interp(
        np.arange(81, dtype=np.float64),
        np.asarray(ANCHOR_NODES, dtype=np.float64),
        anchor_survival,
    )

    selected_bins = catalog.selected_line_bins
    selected_base = catalog.selected_line_weights
    require(np.array_equal(selected_bins, line.selected_bins)
            and np.array_equal(selected_base, line.selected_weights),
            f"model-{model} catalog/line selected templates differ")
    line_coefficients = np.zeros(80, dtype=np.float64)
    cumulative_background = 0.0
    cumulative_kernel = 0.0
    previous_background_rate = 0.0
    previous_kernel = 0.0
    per_node_line: list[dict[str, Any]] = []
    direct_by_node = np.empty(81, dtype=np.float64)
    direct_variance_by_node = np.empty(81, dtype=np.float64)
    transmission = np.empty(81, dtype=np.float64)
    aeff_by_node = np.empty(81, dtype=np.float64)
    line_integrated: dict[str, Any] | None = None
    for node, row in enumerate(mission):
        ratio = as_float(row, "interpolated_background_timeline_ratio")
        survival = as_float(row, "conditional_signal_accidental_survival")
        close(ratio, float(ratio_by_node[node]),
              f"model-{model} interpolated ratio node {node}")
        close(survival, float(survival_by_node[node]),
              f"model-{model} interpolated survival node {node}")
        direct = as_float(row, "direct_W2_final_no_coincidence_cps")
        direct_variance = as_float(row, "direct_sum_W_i2_cps2")
        direct_by_node[node] = direct
        direct_variance_by_node[node] = direct_variance
        require(direct > 0.0 and direct_variance > 0.0,
                f"model-{model} direct rate/variance non-positive node {node}")
        close(as_float(row, "direct_transport_sigma_cps"), math.sqrt(direct_variance),
              f"model-{model} direct sigma node {node}")
        close(
            as_float(row, "direct_transport_effective_sample_size"),
            direct * direct / direct_variance,
            f"model-{model} direct ESS node {node}",
        )
        component_rate = math.fsum(
            as_float(row, f"direct_{name}_cps") for name in COMPONENTS
        )
        component_variance = math.fsum(
            as_float(row, f"direct_{name}_sum_W_i2_cps2")
            for name in COMPONENTS
        )
        close(component_rate, direct, f"model-{model} direct component rate node {node}")
        close(
            component_variance,
            direct_variance,
            f"model-{model} direct component variance node {node}",
        )

        node_line_weights = (
            selected_base * source.line_ratio[node, selected_bins]
        )
        node_line = stats(node_line_weights, f"model-{model} line node {node}")
        close(as_float(row, "direct_atm511_cps"), float(node_line["sumw"]),
              f"model-{model} direct line sumw node {node}")
        close(
            as_float(row, "direct_atm511_sum_W_i2_cps2"),
            float(node_line["sumw2"]),
            f"model-{model} direct line sumw2 node {node}",
        )
        if node in ANCHOR_NODES:
            component_row = anchor_component_map[
                (node, FINAL_WINDOW, FINAL_STAGE, "atm511")
            ]
            require(
                as_int(component_row, "selected_raw")
                == int(node_line["selected_raw"]),
                f"model-{model} anchor line selected differs node {node}",
            )
            close(
                as_float(component_row, "direct_rate_cps"),
                float(node_line["sumw"]),
                f"model-{model} anchor line sumw node {node}",
            )
            close(
                as_float(component_row, "direct_sum_W_i2_cps2"),
                float(node_line["sumw2"]),
                f"model-{model} anchor line sumw2 node {node}",
            )

        background_rate = direct * ratio
        close(as_float(row, "mature_background_W2_final_cps"), background_rate,
              f"model-{model} mature background rate node {node}")
        close(
            as_float(row, "mature_background_sum_W_i2_cps2"),
            direct_variance * ratio * ratio,
            f"model-{model} mature background variance node {node}",
        )
        transmission[node] = as_float(row, "T_atm_511_slant45")
        aeff_by_node[node] = as_float(row, "conditional_signal_Aeff_cm2")
        kernel = as_float(row, "conditional_signal_kernel_cm2")
        require(transmission[node] > 0.0 and aeff_by_node[node] > 0.0,
                f"model-{model} signal transmission/Aeff non-positive node {node}")
        close(
            kernel,
            aeff_by_node[node] * transmission[node] * survival,
            f"model-{model} instantaneous signal kernel node {node}",
        )
        if node > 0:
            dt = (days[node] - days[node - 1]) * SECONDS_PER_DAY
            cumulative_background += 0.5 * (
                previous_background_rate + background_rate
            ) * dt
            cumulative_kernel += 0.5 * (previous_kernel + kernel) * dt
            line_coefficients += 0.5 * (
                source.line_ratio[node - 1] * ratio_by_node[node - 1]
                + source.line_ratio[node] * ratio_by_node[node]
            ) * dt
        previous_background_rate = background_rate
        previous_kernel = kernel
        close(
            as_float(row, "cumulative_background_counts"),
            cumulative_background,
            f"model-{model} cumulative B node {node}",
            atol=2e-6,
        )
        close(
            as_float(row, "cumulative_signal_counts_per_unit_flux"),
            cumulative_kernel,
            f"model-{model} cumulative K node {node}",
            atol=2e-6,
        )

        integrated_weights = selected_base * line_coefficients[selected_bins]
        line_integrated = stats(
            integrated_weights,
            f"model-{model} integrated line node {node}",
        )
        close(
            as_float(row, "cumulative_atm511_background_counts"),
            float(line_integrated["sumw"]),
            f"model-{model} cumulative line B node {node}",
            atol=2e-6,
        )
        close(
            as_float(row, "cumulative_atm511_sum_W_i2_counts2"),
            float(line_integrated["sumw2"]),
            f"model-{model} cumulative line sumw2 node {node}",
            atol=2e-6,
        )
        cumulative_component_rate = math.fsum(
            as_float(row, f"cumulative_{name}_background_counts")
            for name in COMPONENTS
        )
        cumulative_component_variance = math.fsum(
            as_float(row, f"cumulative_{name}_sum_W_i2_counts2")
            for name in COMPONENTS
        )
        total_transport_variance = as_float(
            row, "cumulative_transport_sum_W_i2_counts2"
        )
        close(
            cumulative_component_rate,
            cumulative_background,
            f"model-{model} cumulative component B sum node {node}",
            atol=2e-6,
        )
        close(
            cumulative_component_variance,
            total_transport_variance,
            f"model-{model} cumulative component variance sum node {node}",
            atol=2e-6,
        )
        close(
            as_float(row, "cumulative_transport_sigma_counts"),
            math.sqrt(total_transport_variance),
            f"model-{model} cumulative transport sigma node {node}",
            atol=2e-8,
        )
        if total_transport_variance > 0.0:
            close(
                as_float(row, "cumulative_transport_effective_sample_size"),
                cumulative_background * cumulative_background
                / total_transport_variance,
                f"model-{model} cumulative transport ESS node {node}",
            )
        if cumulative_kernel > 0.0:
            expected_fmin = fmin_values(cumulative_background, cumulative_kernel)
            for key, value in expected_fmin.items():
                close(as_float(row, key), value,
                      f"model-{model} {key} node {node}", atol=2e-13)
        else:
            for key in (
                "Fmin_3sigma_gaussian_ph_cm2_s",
                "Fmin_5sigma_gaussian_ph_cm2_s",
                "Fmin_3sigma_poisson_asimov_ph_cm2_s",
                "Fmin_5sigma_poisson_asimov_ph_cm2_s",
            ):
                require(str(row[key]).strip() == "",
                        f"model-{model} node-zero {key} should be blank")
        per_node_line.append({
            "time_bin_id": node,
            "day_mid": float(days[node]),
            "selected_raw": int(node_line["selected_raw"]),
            "sumw_cps": float(node_line["sumw"]),
            "sumw2_cps2": float(node_line["sumw2"]),
            "MC_sigma_cps": float(node_line["sigma"]),
            "effective_sample_size": float(node_line["effective_sample_size"]),
        })
    require(line_integrated is not None, f"model-{model} integrated line is absent")
    require(np.all(aeff_by_node == aeff_by_node[0]),
            f"model-{model} conditional signal Aeff changes by node")

    mission_components = read_csv(mission_component_path)
    require_columns(
        mission_components,
        (
            "model",
            "component",
            "mission_day",
            "selected_raw",
            "integrated_background_counts",
            "sum_W_i2_counts2",
            "transport_sigma_counts",
            "transport_effective_sample_size",
        ),
        f"model-{model} mission transport components",
    )
    require(len(mission_components) == 4,
            f"model-{model} mission component table is not four rows")
    mission_component_map = {row["component"]: row for row in mission_components}
    require(set(mission_component_map) == {*COMPONENTS, "total"},
            f"model-{model} mission component labels differ")
    final_row = mission[-1]
    for name in (*COMPONENTS, "total"):
        row = mission_component_map[name]
        require(row["model"] == model, f"model-{model} mission component model differs")
        close(as_float(row, "mission_day"), 20.0,
              f"model-{model} mission component day")
        if name == "total":
            count = as_float(final_row, "cumulative_background_counts")
            variance = as_float(final_row, "cumulative_transport_sum_W_i2_counts2")
        else:
            count = as_float(final_row, f"cumulative_{name}_background_counts")
            variance = as_float(
                final_row, f"cumulative_{name}_sum_W_i2_counts2"
            )
        close(as_float(row, "integrated_background_counts"), count,
              f"model-{model} mission component {name} B", atol=2e-6)
        close(as_float(row, "sum_W_i2_counts2"), variance,
              f"model-{model} mission component {name} variance", atol=2e-6)
        close(as_float(row, "transport_sigma_counts"), math.sqrt(variance),
              f"model-{model} mission component {name} sigma", atol=2e-8)
        if variance > 0.0:
            close(
                as_float(row, "transport_effective_sample_size"),
                count * count / variance,
                f"model-{model} mission component {name} ESS",
            )
    line_component_row = mission_component_map["atm511"]
    require(as_int(line_component_row, "selected_raw") == len(selected_base),
            f"model-{model} integrated line selected count differs")
    close(
        as_float(line_component_row, "integrated_background_counts"),
        float(line_integrated["sumw"]),
        f"model-{model} integrated line table sumw",
        atol=2e-6,
    )
    close(
        as_float(line_component_row, "sum_W_i2_counts2"),
        float(line_integrated["sumw2"]),
        f"model-{model} integrated line table sumw2",
        atol=2e-6,
    )

    summary_final = summary["mission_final_20day"]
    for key in final_row:
        if key in summary_final and str(final_row[key]).strip() != "":
            close(float(summary_final[key]), as_float(final_row, key),
                  f"model-{model} summary final {key}", atol=2e-6)
    summary_components = summary["mission_transport_components"]
    for name, row in mission_component_map.items():
        require(name in summary_components,
                f"model-{model} summary lacks mission component {name}")
        for key in (
            "selected_raw",
            "integrated_background_counts",
            "sum_W_i2_counts2",
            "transport_sigma_counts",
            "transport_effective_sample_size",
        ):
            if key == "selected_raw":
                require(int(summary_components[name][key]) == as_int(row, key),
                        f"model-{model} summary component {name} selected differs")
            else:
                close(float(summary_components[name][key]), as_float(row, key),
                      f"model-{model} summary component {name} {key}", atol=2e-6)

    node_axis = np.arange(81, dtype=np.float64)
    anchor_axis = np.asarray(ANCHOR_NODES, dtype=np.float64)
    ratio_coefficients = np.empty(5, dtype=np.float64)
    survival_coefficients = np.empty(5, dtype=np.float64)
    aeff = float(aeff_by_node[0])
    for index in range(5):
        basis = np.zeros(5, dtype=np.float64)
        basis[index] = 1.0
        interpolated = np.interp(node_axis, anchor_axis, basis)
        ratio_coefficients[index] = (
            trapezoid(direct_by_node * interpolated, days) * SECONDS_PER_DAY
        )
        survival_coefficients[index] = (
            trapezoid(aeff * transmission * interpolated, days)
            * SECONDS_PER_DAY
        )
    timeline_sigma = float(
        np.sqrt(np.sum((ratio_coefficients * anchor_ratio_error) ** 2))
    )
    signal_probe_sigma = float(
        np.sqrt(
            np.sum((survival_coefficients * anchor_survival_error) ** 2)
        )
    )
    final_background = as_float(final_row, "cumulative_background_counts")
    final_kernel = as_float(final_row, "cumulative_signal_counts_per_unit_flux")
    final_transport_variance = as_float(
        final_row, "cumulative_transport_sum_W_i2_counts2"
    )
    transport_sigma = math.sqrt(final_transport_variance)
    background_sigma = math.hypot(transport_sigma, timeline_sigma)
    uncertainty = summary["statistical_uncertainty"]
    close(float(uncertainty["background_transport_MC_sigma_counts"]),
          transport_sigma, f"model-{model} background transport sigma", atol=2e-8)
    close(float(uncertainty["background_timeline_replay_sigma_counts"]),
          timeline_sigma, f"model-{model} background timeline sigma", atol=2e-8)
    close(float(uncertainty["background_combined_sigma_counts"]),
          background_sigma, f"model-{model} combined background sigma", atol=2e-8)
    close(
        float(uncertainty["background_combined_relative_sigma"]),
        background_sigma / final_background,
        f"model-{model} combined background relative sigma",
    )
    aeff_sigma = float(uncertainty["signal_Aeff_sigma_cm2"])
    close(float(uncertainty["signal_Aeff_relative_sigma"]), aeff_sigma / aeff,
          f"model-{model} signal Aeff relative sigma")
    close(
        float(uncertainty["signal_accidental_probe_sigma_counts_per_unit_flux"]),
        signal_probe_sigma,
        f"model-{model} signal probe sigma",
        atol=2e-8,
    )
    signal_probe_relative = signal_probe_sigma / final_kernel
    close(
        float(uncertainty["signal_accidental_probe_relative_sigma"]),
        signal_probe_relative,
        f"model-{model} signal probe relative sigma",
    )
    signal_relative = math.hypot(aeff_sigma / aeff, signal_probe_relative)
    close(float(uncertainty["signal_combined_relative_sigma"]), signal_relative,
          f"model-{model} combined signal relative sigma")
    expected_errors = fmin_uncertainty_closure(
        background=final_background,
        kernel=final_kernel,
        background_sigma=background_sigma,
        signal_relative_sigma=signal_relative,
    )
    for key, expected in expected_errors.items():
        require(key in uncertainty["Fmin"],
                f"model-{model} uncertainty lacks {key}")
        recorded = uncertainty["Fmin"][key]
        for field in ("value", "standard_error", "relative_standard_error"):
            close(float(recorded[field]), float(expected[field]),
                  f"model-{model} {key} {field}", atol=2e-13)

    topup = topup_from_timeline(
        model=model,
        line=line,
        integrated_line=line_integrated,
        background=final_background,
        kernel=final_kernel,
        uncertainty=uncertainty,
    )
    report = {
        "status": "PASS__FIVE_ANCHORS_81_NODES_BK_FMIN_ERROR_CLOSURE",
        "model": model,
        "anchors": list(ANCHOR_NODES),
        "mission_nodes": 81,
        "mission_day_range": [float(days[0]), float(days[-1])],
        "final_background_counts": final_background,
        "final_signal_counts_per_unit_flux": final_kernel,
        "final_transport_sumw2_counts2": final_transport_variance,
        "background_transport_MC_sigma_counts": transport_sigma,
        "background_timeline_replay_sigma_counts": timeline_sigma,
        "background_combined_sigma_counts": background_sigma,
        "signal_combined_relative_sigma": signal_relative,
        "Fmin": uncertainty["Fmin"],
        "day15_products": day15_product_report,
        "line_per_node": per_node_line,
        "line_integrated": {
            "selected_raw": int(line_integrated["selected_raw"]),
            "sumw_counts": float(line_integrated["sumw"]),
            "sumw2_counts2": float(line_integrated["sumw2"]),
            "MC_sigma_counts": float(line_integrated["sigma"]),
            "effective_sample_size": float(
                line_integrated["effective_sample_size"]
            ),
            "correlation_model": (
                "each finite transported line event is one common template over "
                "all 81 nodes; its node coefficients are trapezoid-integrated "
                "before squaring"
            ),
        },
        "hashes": {
            name: sha256_file(timeline_dir / name) for name in TIMELINE_FILES
        },
    }
    return report, topup


def resolve_inside_package(path_text: str | None, default: Path) -> Path:
    path = default if path_text is None else Path(path_text)
    if not path.is_absolute():
        path = PACKAGE / path
    path = path.resolve()
    require(path.is_relative_to(PACKAGE.resolve()),
            f"path must remain inside package {PACKAGE}: {path}")
    return path


def required_groups(paths: Mapping[str, Path]) -> dict[str, list[Path]]:
    return {
        "source_closure": [
            paths["source_dir"] / name for name in SOURCE_FILES
        ],
        "line_response_a": [
            paths["line_a_dir"] / name for name in LINE_FILES
        ],
        "line_response_b": [
            paths["line_b_dir"] / name for name in LINE_FILES
        ],
        "fluxclosed_catalog_a": [
            paths["catalog_a_dir"] / name for name in CATALOG_FILES
        ],
        "fluxclosed_catalog_b": [
            paths["catalog_b_dir"] / name for name in CATALOG_FILES
        ],
        "fluxclosed_timeline_a": [
            paths["timeline_a_dir"] / name for name in TIMELINE_FILES
        ],
        "fluxclosed_timeline_b": [
            paths["timeline_b_dir"] / name for name in TIMELINE_FILES
        ],
    }


def input_inventory(paths: Mapping[str, Path]) -> dict[str, Any]:
    groups: dict[str, Any] = {}
    all_missing: list[str] = []
    for group_name, required in required_groups(paths).items():
        present = [str(path) for path in required if path.is_file()]
        missing = [str(path) for path in required if not path.is_file()]
        all_missing.extend(missing)
        status_values: dict[str, Any] = {}
        for path in required:
            if path.name not in {"summary.json", "audit.json", "source_closure.json"}:
                continue
            if not path.is_file():
                continue
            try:
                content = load_json(path)
                status_values[path.name] = content.get("status")
            except (OSError, ValueError, TypeError) as error:
                status_values[path.name] = f"UNREADABLE: {error}"
        groups[group_name] = {
            "directory": str(required[0].parent),
            "required_file_count": len(required),
            "present_file_count": len(present),
            "complete": not missing,
            "present": present,
            "missing": missing,
            "recorded_status": status_values,
        }
    staging = sorted(
        str(path)
        for path in OUTPUTS.glob(".02_fluxclosed_catalog_*.staging-*")
        if path.is_dir()
    )
    ready = not all_missing
    return {
        "status": (
            "PASS__ALL_VALIDATION_INPUTS_PRESENT"
            if ready
            else "WAITING__DOWNSTREAM_CATALOG_OR_TIMELINE_OUTPUTS_MISSING"
        ),
        "mode": "check-inputs",
        "ready_for_full_validation": ready,
        "no_outputs_written": True,
        "groups": groups,
        "missing_required_paths": all_missing,
        "partial_catalog_staging_directories": staging,
        "next_action": (
            "run validator without --check-inputs"
            if ready
            else (
                "wait for the existing catalog/timeline producers; this validator "
                "must not start or resume them"
            )
        ),
    }


def run_self_test() -> dict[str, Any]:
    moments = stats(np.asarray([1.0, 2.0], dtype=np.float64), "synthetic")
    close(float(moments["sumw"]), 3.0, "self-test sumw")
    close(float(moments["sumw2"]), 5.0, "self-test sumw2")
    close(float(moments["effective_sample_size"]), 1.8, "self-test ESS")
    background = 100.0
    target = 3.0
    signal = asimov_required_signal(background, target)
    significance = math.sqrt(
        2.0
        * (
            (signal + background) * math.log1p(signal / background)
            - signal
        )
    )
    close(significance, target, "self-test Asimov inversion", atol=2e-14)
    fmins = fmin_values(background, 1000.0)
    close(
        fmins["Fmin_3sigma_gaussian_ph_cm2_s"],
        0.03,
        "self-test Gaussian Fmin",
    )
    uncertainty = fmin_uncertainty_closure(
        background=background,
        kernel=1000.0,
        background_sigma=10.0,
        signal_relative_sigma=0.02,
    )
    require(
        all(
            item["value"] > 0.0
            and item["standard_error"] > 0.0
            and item["relative_standard_error"] > 0.0
            for item in uncertainty.values()
        ),
        "self-test uncertainty is invalid",
    )
    legacy_gate = precision_gate(
        total_standard_error=4.01e-6,
        line_standard_error=1.00e-6,
        display_step=1.0e-8,
    )
    require(
        legacy_gate[
            "maximum_line_standard_error_for_same_reported_last_digit_ph_cm2_s"
        ]
        > 0.0,
        "self-test legacy precision allowance is not positive",
    )
    require(
        legacy_gate["decision_authority"] is False,
        "legacy last-digit diagnostic became a decision gate",
    )
    publication_no_topup = publication_topup_gate(
        fmin_value=1.0,
        total_standard_error=math.hypot(0.06, 0.04),
        line_standard_error=0.04,
        current_incident=100,
    )
    require(
        publication_no_topup["decision"] == "NO_TOPUP",
        "publication no-topup self-test failed",
    )
    publication_topup = publication_topup_gate(
        fmin_value=1.0,
        total_standard_error=math.hypot(0.06, 0.09),
        line_standard_error=0.09,
        current_incident=100,
    )
    require(
        publication_topup["decision"] == "TOPUP_REQUIRED"
        and int(publication_topup["required_total_incident_photons"]) > 100,
        "publication finite-topup self-test failed",
    )
    require(
        float(
            publication_topup["projected_at_required_incident"][
                "total_MC_relative_standard_error"
            ]
        )
        <= PUBLICATION_TOTAL_MC_RSE_MAX * (1.0 + 3e-12)
        and float(
            publication_topup["projected_at_required_incident"][
                "line_Fmin_variance_fraction"
            ]
        )
        <= PUBLICATION_LINE_FMIN_VARIANCE_FRACTION_MAX * (1.0 + 3e-12),
        "publication projected-topup thresholds do not close",
    )
    publication_not_beneficial = publication_topup_gate(
        fmin_value=1.0,
        total_standard_error=math.hypot(0.11, 0.02),
        line_standard_error=0.02,
        current_incident=100,
    )
    require(
        publication_not_beneficial["decision"]
        == "LINE_TOPUP_NOT_BENEFICIAL"
        and publication_not_beneficial["required_total_incident_photons"] is None,
        "publication non-beneficial self-test failed",
    )
    proposal = 2.0
    importance = np.asarray([1.0, 0.5, 0.25], dtype=np.float64)
    base = proposal * importance
    require(
        not np.array_equal(base, base * importance),
        "self-test cannot detect double continuum weighting",
    )
    return {
        "status": "PASS__STATIC_VALIDATOR_SELF_TEST",
        "raw_SIM_files_opened": 0,
        "transport_started": False,
        "synthetic_Asimov_signal_for_B100_Z3": signal,
        "publication_gate_cases_exercised": [
            "NO_TOPUP",
            "TOPUP_REQUIRED",
            "LINE_TOPUP_NOT_BENEFICIAL",
        ],
        "legacy_last_digit_diagnostic_exercised": True,
        "continuum_fold_once_guard_exercised": True,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the package-67 positive flux-closed A/B chain and make an "
            "auditable mono-line transport top-up decision.  This script never "
            "runs transport."
        )
    )
    parser.add_argument("--source-dir")
    parser.add_argument("--line-a-dir")
    parser.add_argument("--line-b-dir")
    parser.add_argument("--catalog-a-dir")
    parser.add_argument("--catalog-b-dir")
    parser.add_argument("--timeline-a-dir")
    parser.add_argument("--timeline-b-dir")
    parser.add_argument(
        "--output",
        help=(
            "JSON output inside this package (default: "
            "outputs/04_validation/topup_decision.json)"
        ),
    )
    parser.add_argument(
        "--check-inputs",
        action="store_true",
        help="inventory required inputs, print missing paths, and write nothing",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run only synthetic formula tests; inspect no result directories",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing validator JSON only",
    )
    return parser.parse_args()


def resolved_paths(args: argparse.Namespace) -> dict[str, Path]:
    return {
        "source_dir": resolve_inside_package(
            args.source_dir, OUTPUTS / "00_source_closure"
        ),
        "line_a_dir": resolve_inside_package(
            args.line_a_dir, OUTPUTS / "01_line_response_a"
        ),
        "line_b_dir": resolve_inside_package(
            args.line_b_dir, OUTPUTS / "01_line_response_b60"
        ),
        "catalog_a_dir": resolve_inside_package(
            args.catalog_a_dir, OUTPUTS / "02_fluxclosed_catalog_a"
        ),
        "catalog_b_dir": resolve_inside_package(
            args.catalog_b_dir, OUTPUTS / "02_fluxclosed_catalog_b"
        ),
        "timeline_a_dir": resolve_inside_package(
            args.timeline_a_dir, OUTPUTS / "03_fluxclosed_timeline_a"
        ),
        "timeline_b_dir": resolve_inside_package(
            args.timeline_b_dir, OUTPUTS / "03_fluxclosed_timeline_b"
        ),
        "output": resolve_inside_package(
            args.output, OUTPUTS / "04_validation/topup_decision.json"
        ),
    }


def full_validation(paths: Mapping[str, Path]) -> dict[str, Any]:
    inventory = input_inventory(paths)
    require(
        bool(inventory["ready_for_full_validation"]),
        "full validation inputs are incomplete:\n  "
        + "\n  ".join(inventory["missing_required_paths"]),
    )
    paper = validate_paper_reference()
    source = validate_source(paths["source_dir"])
    lines = {
        "a": validate_line_response("a", paths["line_a_dir"]),
        "b": validate_line_response("b", paths["line_b_dir"]),
    }
    catalogs = {
        "a": validate_catalog(
            "a", paths["catalog_a_dir"], paths["source_dir"], lines["a"]
        ),
        "b": validate_catalog(
            "b", paths["catalog_b_dir"], paths["source_dir"], lines["b"]
        ),
    }
    timeline_reports: dict[str, Any] = {}
    topups: dict[str, Any] = {}
    for model in ("a", "b"):
        timeline_report, topup = validate_timeline(
            model,
            paths[f"timeline_{model}_dir"],
            source,
            catalogs[model],
            lines[model],
        )
        timeline_reports[model] = timeline_report
        topups[model] = topup
    model_decision_values = {
        str(item["decision"]) for item in topups.values()
    }
    if "LINE_TOPUP_NOT_BENEFICIAL" in model_decision_values:
        global_decision = "LINE_TOPUP_NOT_BENEFICIAL"
    elif "TOPUP_REQUIRED" in model_decision_values:
        global_decision = "TOPUP_REQUIRED"
    else:
        global_decision = "NO_TOPUP"
    return {
        "schema_version": 1,
        "status": (
            "PASS__FLUXCLOSED_RESULTS_VALIDATED__" + global_decision
        ),
        "decision": global_decision,
        "model_decisions": topups,
        "validation": {
            "source_closure": source.report,
            "line_response": {
                model: lines[model].report for model in ("a", "b")
            },
            "catalogs": {
                model: catalogs[model].report for model in ("a", "b")
            },
            "timelines": timeline_reports,
            "paper_effective_digits": paper,
        },
        "topup_gate_definition": {
            "gated_metric": "Gaussian 3-sigma Fmin total MC uncertainty",
            "formal_publication_gates": {
                "total_MC_relative_standard_error_max": (
                    PUBLICATION_TOTAL_MC_RSE_MAX
                ),
                "line_Fmin_variance_fraction_max": (
                    PUBLICATION_LINE_FMIN_VARIANCE_FRACTION_MAX
                ),
                "equivalent_line_nondominance": (
                    "sigma_F_line <= sigma_F_rest"
                ),
                "rationale": (
                    "the existing manuscript A/B total MC errors are about "
                    "7--9%; 10% is a no-degradation publication target, and "
                    "the line finite-MC term may not dominate the remaining "
                    "statistical variance"
                ),
            },
            "background_count_precision_is_diagnostic_not_gate": True,
            "Asimov_and_5sigma_line_contributions_are_reported_not_gated": True,
            "legacy_last_digit_diagnostic": {
                "status": "INFORMATIONAL_ONLY",
                "display_step_ph_cm2_s": float(
                    PAPER_REFERENCE["fmin_display_step_ph_cm2_s"]
                ),
                "decision_authority": False,
                "reason": (
                    "old TeX mantissa precision must not force a no-benefit top-up"
                ),
            },
            "not_beneficial_rule": (
                "if sigma_F_rest/Fmin >= 0.10, no finite reduction of the "
                "incremental line variance can satisfy total RSE <=10%; report "
                "LINE_TOPUP_NOT_BENEFICIAL"
            ),
            "required_incident_formula": (
                "ceil(N_current * "
                "(sigma_F_line_current/min("
                "sqrt((0.10*Fmin)^2-sigma_F_rest^2),sigma_F_rest))^2)"
            ),
        },
        "uncertainty_scope": {
            "included": (
                "finite transport-template sumw2 with each template fully "
                "correlated across mission nodes; independent five-anchor replay "
                "Poisson terms; signal Aeff and accidental-probe binomial terms"
            ),
            "excluded": {
                "physical_PARMA_flux_systematic": {
                    "status": "EXCLUDED",
                    "reason": (
                        "transport top-up reduces finite-MC response variance but "
                        "cannot reduce physical source-model/atmospheric flux "
                        "systematics"
                    ),
                },
                "other_systematics": (
                    "geometry, detector-response model, activation/source model, "
                    "atmosphere, and cross-component transport systematics"
                ),
            },
        },
        "authority_caveat": (
            "The physical mono target and transported angular proposal share "
            "the frozen W=114.6/g=0.15 day-15 state; node 60 is an 80-bin "
            "identity. The continuum is separately de-lined at W=118.3/g=0/"
            "Rc=11.6/X=3.84535 and then uses the retained W=114.6 trajectory "
            "scale. This explicit hybrid does not claim one common atmospheric "
            "state, and the old broadband total is intentionally not preserved."
        ),
        "validator": {
            "path": str(HERE),
            "sha256": sha256_file(HERE),
            "raw_SIM_files_opened": 0,
            "transport_started": False,
        },
    }


def main() -> int:
    args = parse_args()
    try:
        if args.self_test:
            print(json.dumps(run_self_test(), indent=2, sort_keys=True))
            return 0
        paths = resolved_paths(args)
        if args.check_inputs:
            print(json.dumps(input_inventory(paths), indent=2, sort_keys=True))
            return 0
        result = full_validation(paths)
        write_json(paths["output"], result, force=args.force)
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "decision": result["decision"],
                    "output": str(paths["output"]),
                    "models": {
                        model: {
                            "decision": result["model_decisions"][model][
                                "decision"
                            ],
                            "incident": result["model_decisions"][model][
                                "line_incident_photons"
                            ],
                            "selected": result["model_decisions"][model][
                                "line_final_selected_events"
                            ],
                            "additional_incident": result[
                                "model_decisions"
                            ][model]["additional_incident_photons"],
                        }
                        for model in ("a", "b")
                    },
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    except (ValidationError, FileNotFoundError, KeyError, ValueError) as error:
        print(
            json.dumps(
                {
                    "status": "FAIL__FLUXCLOSED_VALIDATION",
                    "error_type": type(error).__name__,
                    "error": str(error),
                    "transport_started": False,
                },
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
