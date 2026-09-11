#!/usr/bin/env python3
"""Flux-closed common-time timeline for M05 mass models A and B.

This program intentionally consumes only the future, merged flux-closed event
catalog for one model.  The broadband gamma continuum and the standalone
monoenergetic atmospheric-511 proposal are mutually exclusive components of
that catalog.  Event marks are sampled from their *event-level* physical
weights; a category-uniform approximation is never used for weighted
continuum events.

The five-anchor replay is resumable through immutable per-anchor receipts.
Final CSV/JSON products are written exclusively and are never overwritten.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
import os
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np


HERE = Path(__file__).resolve()
PACKAGE = HERE.parents[1]
ROOT = PACKAGE.parents[2]

P58_CODE = (
    ROOT
    / "engineering/geometry_optimization_20260815"
    / "58_sg3b_m05_common_time_response_20260817/code/analyze_sg3b_common_time.py"
)
A_TIMELINE_CONFIG = (
    ROOT
    / "engineering/geometry_optimization_20260815"
    / "62_sg3b_mature_poisson_timeline_20260818/analysis_inputs.json"
)
A_CATALOG_CODE = (
    ROOT
    / "engineering/geometry_optimization_20260815"
    / "62_sg3b_mature_poisson_timeline_20260818/code/build_event_catalog.py"
)
A_CANDIDATE_TIMELINE_CODE = (
    ROOT
    / "engineering/geometry_optimization_20260815"
    / "63_m05new_sg3b_signal_statistics_20260820/code/run_candidate_timeline.py"
)
A_CANDIDATE_TIMELINE_SUMMARY = (
    ROOT
    / "engineering/geometry_optimization_20260815"
    / "63_m05new_sg3b_signal_statistics_20260820/outputs/04_candidate_timeline/summary.json"
)
A_SIGNAL_SUMMARY = (
    ROOT
    / "engineering/geometry_optimization_20260815"
    / "63_m05new_sg3b_signal_statistics_20260820/outputs/01_signal/summary.json"
)
B_TIMELINE_CONFIG = ROOT / "DEEPSEEK_CODE/modified/analysis_inputs_optv3_B.json"
B_CATALOG_CODE = ROOT / "DEEPSEEK_CODE/modified/build_event_catalog_sh3_step05.py"
B_TIMELINE_CODE = ROOT / "DEEPSEEK_CODE/modified/run_mature_timeline_sh3_optv3_B.py"
B_TIMELINE_SUMMARY = ROOT / "DEEPSEEK_CODE/outputs/05_mature_timeline_m05_fixed_20260820/summary.json"
A_PROMPT_ADAPTER = (
    ROOT
    / "engineering/particle_source_unit_repair_20260811"
    / "m05_corrected_reanalysis_20260813/code/run_prompt_analysis.py"
)
A_CORRECTED_CORE = (
    ROOT
    / "engineering/particle_source_unit_repair_20260811"
    / "composite_partial_postprocess_20260812/code/analyze_composite_partial.py"
)
A_STEP05_CODE = ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"
A_STEP09_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5"
    / "step09_optics_bridge_summary.json"
)
B_STEP05_CODE = ROOT / "DEEPSEEK_CODE/modified/step05_side_compton.py"

SECONDS_PER_DAY = 86_400.0
ANCHOR_NODES = (0, 20, 40, 60, 80)
DAY15_NODE = 60
WINDOWS = {
    "broad_480_550": (480.0, 550.0),
    "w2_510p58_511p42": (510.58, 511.42),
}
STAGES = (
    "pre_veto",
    "plastic_positron_veto",
    "bgo_active_scintillator_veto",
    "combined_active_veto",
    "compton_trajectory_veto",
)
STAGE_BITS = {stage: 1 << index for index, stage in enumerate(STAGES)}
FINAL_WINDOW = "w2_510p58_511p42"
FINAL_STAGE = "compton_trajectory_veto"
COMPONENT_NAMES = ("other", "gamma_continuum", "atm511")
COMPONENT_CODES = {name: index for index, name in enumerate(COMPONENT_NAMES)}
STREAM_NAMES = ("prompt", "delayed")
STREAM_LABELS = ("all",) + STREAM_NAMES
COMPONENT_LABELS = ("all",) + COMPONENT_NAMES
WINDOW_FLAG_FIELDS = {
    "broad_480_550": "broad_flags",
    "w2_510p58_511p42": "w2_flags",
}
DAY15_PRODUCT_SCHEMA_VERSION = 2
FINAL_FILENAMES = (
    "anchor_timeline_rates.csv",
    "anchor_transport_components.csv",
    "mission_timeline_81nodes.csv",
    "mission_transport_components.csv",
    "direct_cutflow_day15.csv",
    "direct_measured_energy_day15_0p25keV.csv",
    "direct_hit_multiplicity_day15.csv",
    "summary.json",
)

EVENT_FIELDS = (
    "plastic_keV",
    "bgo_keV",
    "measured_total_keV",
    "broad_flags",
    "w2_flags",
    "hit_start",
    "hit_count",
    "event_category",
    "event_base_weight_cps",
    "event_component",
    "source_bin80",
    "continuum_importance_weight",
)
HIT_FIELDS = (
    "hit_code",
    "hit_layer",
    "hit_energy_keV",
    "hit_x_cm",
    "hit_y_cm",
    "hit_z_cm",
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def resolve_root(path_text: str | Path) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def atomic_exclusive_bytes(path: Path, payload: bytes) -> None:
    """Atomically publish bytes without replacing an existing path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp"
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            raise RuntimeError(f"refusing to overwrite existing output: {path}") from error
    finally:
        temporary.unlink(missing_ok=True)


def write_json_exclusive(path: Path, value: Any) -> None:
    payload = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    atomic_exclusive_bytes(path, payload)


def write_csv_exclusive(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty CSV: {path}")
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    atomic_exclusive_bytes(path, handle.getvalue().encode("utf-8"))


def in_window(value: float, bounds: tuple[float, float]) -> bool:
    return bounds[0] <= value < bounds[1]


def asimov_required_signal(background: float, target_z: float) -> float:
    """Invert the Cowan counting-experiment Asimov significance."""
    if background <= 0.0:
        return 0.5 * target_z * target_z
    low = 0.0
    high = max(target_z * math.sqrt(background), 1.0)

    def significance(signal: float) -> float:
        return math.sqrt(
            2.0 * ((signal + background) * math.log1p(signal / background) - signal)
        )

    while significance(high) < target_z:
        high *= 2.0
    for _ in range(80):
        middle = 0.5 * (low + high)
        if significance(middle) < target_z:
            low = middle
        else:
            high = middle
    return high


def fmin_values(background: float, kernel: float) -> dict[str, float | str]:
    if kernel <= 0.0:
        return {
            "Fmin_3sigma_gaussian_ph_cm2_s": "",
            "Fmin_5sigma_gaussian_ph_cm2_s": "",
            "Fmin_3sigma_poisson_asimov_ph_cm2_s": "",
            "Fmin_5sigma_poisson_asimov_ph_cm2_s": "",
        }
    return {
        "Fmin_3sigma_gaussian_ph_cm2_s": 3.0 * math.sqrt(max(background, 0.0)) / kernel,
        "Fmin_5sigma_gaussian_ph_cm2_s": 5.0 * math.sqrt(max(background, 0.0)) / kernel,
        "Fmin_3sigma_poisson_asimov_ph_cm2_s": asimov_required_signal(background, 3.0) / kernel,
        "Fmin_5sigma_poisson_asimov_ph_cm2_s": asimov_required_signal(background, 5.0) / kernel,
    }


def effective_sample_size(sum_weight: float, sum_weight2: float) -> float | str:
    return sum_weight * sum_weight / sum_weight2 if sum_weight2 > 0.0 else ""


def continuum_reference_weight(event_base_weight_cps: np.ndarray) -> np.ndarray:
    """Return the already importance-folded continuum reference weight."""
    return np.asarray(event_base_weight_cps, dtype=np.float64)


def assert_continuum_fold_once_contract() -> None:
    """Static guard against accidentally applying Jcont/Jtotal twice."""
    proposal = 2.0
    importance = np.asarray([1.0, 0.5, 0.25], dtype=np.float64)
    event_base = proposal * importance
    physical = continuum_reference_weight(event_base)
    double_weighted = event_base * importance
    if not np.array_equal(physical, event_base):
        raise RuntimeError("continuum reference-weight helper changed event_base_weight")
    if math.isclose(
        float(np.sum(physical)),
        float(np.sum(double_weighted)),
        rel_tol=0.0,
        abs_tol=1e-15,
    ):
        raise RuntimeError("continuum fold-once self-test cannot distinguish double weighting")


def _require_closure_equal(
    actual: Any, expected: Any, label: str, *, exact: bool
) -> None:
    actual_array = np.asarray(actual)
    expected_array = np.asarray(expected)
    if actual_array.shape != expected_array.shape:
        raise RuntimeError(
            f"{label} closure shape mismatch: {actual_array.shape} != {expected_array.shape}"
        )
    if exact:
        matches = np.array_equal(actual_array, expected_array)
    else:
        matches = np.allclose(
            actual_array,
            expected_array,
            rtol=5e-12,
            atol=2e-18,
            equal_nan=False,
        )
    if not matches:
        maximum = float(np.max(np.abs(actual_array - expected_array)))
        raise RuntimeError(f"{label} additive closure failed; max_abs_diff={maximum:.17g}")


def _accumulate_stream_component_histogram(
    target: np.ndarray,
    stage_index: int,
    stream_index: int,
    component_index: int,
    values: np.ndarray,
) -> None:
    for target_stream, target_component in (
        (0, 0),
        (0, component_index),
        (stream_index, 0),
        (stream_index, component_index),
    ):
        target[stage_index, target_stream, target_component] += values


def assert_spectrum_stream_component_closure(
    raw: np.ndarray, sumw: np.ndarray, sumw2: np.ndarray
) -> None:
    expected_prefix = (len(STREAM_LABELS), len(COMPONENT_LABELS))
    if raw.ndim != 4 or raw.shape[1:3] != expected_prefix:
        raise RuntimeError(
            "spectrum schema must be stage x stream x component x energy_bin"
        )
    if sumw.shape != raw.shape or sumw2.shape != raw.shape:
        raise RuntimeError("spectrum raw/sumw/sumw2 shapes differ")
    for name, values, exact in (
        ("selected_raw", raw, True),
        ("sumw", sumw, False),
        ("sumw2", sumw2, False),
    ):
        if np.any(~np.isfinite(values)) or np.any(values < 0):
            raise RuntimeError(f"spectrum {name} contains invalid values")
        _require_closure_equal(
            values[:, 0, 0, :],
            np.sum(values[:, 1:, 0, :], axis=1),
            f"spectrum {name}: prompt+delayed=all",
            exact=exact,
        )
        _require_closure_equal(
            values[:, :, 0, :],
            np.sum(values[:, :, 1:, :], axis=2),
            f"spectrum {name}: named components=all",
            exact=exact,
        )
        _require_closure_equal(
            values[:, 0, 1:, :],
            np.sum(values[:, 1:, 1:, :], axis=1),
            f"spectrum {name}: component streams=all",
            exact=exact,
        )


def assert_multiplicity_component_closure(
    raw: np.ndarray, sumw: np.ndarray, sumw2: np.ndarray
) -> None:
    if raw.ndim != 4 or raw.shape[2] != len(COMPONENT_LABELS):
        raise RuntimeError(
            "multiplicity schema must be window x stage x component x multiplicity"
        )
    if sumw.shape != raw.shape or sumw2.shape != raw.shape:
        raise RuntimeError("multiplicity raw/sumw/sumw2 shapes differ")
    for name, values, exact in (
        ("selected_raw", raw, True),
        ("sumw", sumw, False),
        ("sumw2", sumw2, False),
    ):
        if np.any(~np.isfinite(values)) or np.any(values < 0):
            raise RuntimeError(f"multiplicity {name} contains invalid values")
        _require_closure_equal(
            values[:, :, 0, :],
            np.sum(values[:, :, 1:, :], axis=2),
            f"multiplicity {name}: named components=all",
            exact=exact,
        )


def _assert_histogram_cutflow_closure(
    raw: np.ndarray,
    sumw: np.ndarray,
    sumw2: np.ndarray,
    expected: dict[str, Any],
    label: str,
) -> None:
    _require_closure_equal(
        np.asarray(int(np.sum(raw))),
        np.asarray(int(expected["selected_raw"])),
        f"{label} selected_raw=cutflow",
        exact=True,
    )
    _require_closure_equal(
        np.asarray(float(np.sum(sumw))),
        np.asarray(float(expected["rate_cps"])),
        f"{label} sumw=cutflow",
        exact=False,
    )
    _require_closure_equal(
        np.asarray(float(np.sum(sumw2))),
        np.asarray(float(expected["sum_wi2_cps2"])),
        f"{label} sumw2=cutflow",
        exact=False,
    )


def assert_day15_product_schema_contract() -> None:
    """Synthetic pass/fail guard for the day-15 additive output schemas."""
    spectrum_raw = np.zeros((1, 3, 4, 2), dtype=np.int64)
    spectrum_sum = np.zeros_like(spectrum_raw, dtype=np.float64)
    spectrum_sum2 = np.zeros_like(spectrum_raw, dtype=np.float64)
    for stream_index, component_index, raw, weights in (
        (1, 2, np.asarray([2, 1]), np.asarray([0.4, 0.2])),
        (1, 3, np.asarray([1, 3]), np.asarray([0.1, 0.6])),
        (2, 1, np.asarray([4, 2]), np.asarray([0.8, 0.4])),
    ):
        _accumulate_stream_component_histogram(
            spectrum_raw, 0, stream_index, component_index, raw
        )
        _accumulate_stream_component_histogram(
            spectrum_sum, 0, stream_index, component_index, weights
        )
        _accumulate_stream_component_histogram(
            spectrum_sum2, 0, stream_index, component_index, weights * weights
        )
    assert_spectrum_stream_component_closure(
        spectrum_raw, spectrum_sum, spectrum_sum2
    )
    broken_spectrum = spectrum_raw.copy()
    broken_spectrum[0, 0, 0, 0] += 1
    try:
        assert_spectrum_stream_component_closure(
            broken_spectrum, spectrum_sum, spectrum_sum2
        )
    except RuntimeError:
        pass
    else:
        raise RuntimeError("spectrum synthetic fail-closed self-test did not fail")

    multiplicity_raw = np.zeros((2, 1, 4, 3), dtype=np.int64)
    multiplicity_sum = np.zeros_like(multiplicity_raw, dtype=np.float64)
    multiplicity_sum2 = np.zeros_like(multiplicity_raw, dtype=np.float64)
    for window_index in range(2):
        for component_index, raw, weights in (
            (1, np.asarray([1, 2, 0]), np.asarray([0.1, 0.2, 0.0])),
            (2, np.asarray([0, 1, 1]), np.asarray([0.0, 0.3, 0.4])),
            (3, np.asarray([2, 0, 1]), np.asarray([0.5, 0.0, 0.2])),
        ):
            multiplicity_raw[window_index, 0, 0] += raw
            multiplicity_raw[window_index, 0, component_index] += raw
            multiplicity_sum[window_index, 0, 0] += weights
            multiplicity_sum[window_index, 0, component_index] += weights
            multiplicity_sum2[window_index, 0, 0] += weights * weights
            multiplicity_sum2[window_index, 0, component_index] += weights * weights
    assert_multiplicity_component_closure(
        multiplicity_raw, multiplicity_sum, multiplicity_sum2
    )
    synthetic_cutflow = {
        "selected_raw": int(np.sum(multiplicity_raw[0, 0, 0])),
        "rate_cps": float(np.sum(multiplicity_sum[0, 0, 0])),
        "sum_wi2_cps2": float(np.sum(multiplicity_sum2[0, 0, 0])),
    }
    _assert_histogram_cutflow_closure(
        multiplicity_raw[0, 0, 0],
        multiplicity_sum[0, 0, 0],
        multiplicity_sum2[0, 0, 0],
        synthetic_cutflow,
        "synthetic multiplicity",
    )
    broken_cutflow = dict(synthetic_cutflow)
    broken_cutflow["sum_wi2_cps2"] += 1.0
    try:
        _assert_histogram_cutflow_closure(
            multiplicity_raw[0, 0, 0],
            multiplicity_sum[0, 0, 0],
            multiplicity_sum2[0, 0, 0],
            broken_cutflow,
            "synthetic multiplicity broken cutflow",
        )
    except RuntimeError:
        pass
    else:
        raise RuntimeError("cutflow synthetic fail-closed self-test did not fail")
    broken_multiplicity = multiplicity_sum2.copy()
    broken_multiplicity[0, 0, 0, 0] += 1.0
    try:
        assert_multiplicity_component_closure(
            multiplicity_raw, multiplicity_sum, broken_multiplicity
        )
    except RuntimeError:
        pass
    else:
        raise RuntimeError("multiplicity synthetic fail-closed self-test did not fail")


def normalized_component(value: Any) -> tuple[int, str]:
    if isinstance(value, int) and 0 <= value <= 2:
        return value, COMPONENT_NAMES[value]
    text = str(value).strip().lower()
    aliases = {
        "other": 0,
        "other_prompt_delayed": 0,
        "prompt_delayed": 0,
        "gamma_continuum": 1,
        "continuum": 1,
        "atm511": 2,
        "atmospheric_511": 2,
        "mono511": 2,
    }
    if text not in aliases:
        raise RuntimeError(f"unknown category component: {value!r}")
    code = aliases[text]
    return code, COMPONENT_NAMES[code]


@dataclass
class Aggregate:
    count: int
    sum_q: float = 0.0
    sum_q2: float = 0.0
    bin_sum_q: np.ndarray | None = None
    bin_sum_q2: np.ndarray | None = None


@dataclass
class Authority:
    model: str
    candidate: str
    config: dict[str, Any]
    mission: dict[str, Any]
    timeline: dict[str, Any]
    activation_path: Path
    signal: dict[str, Any]
    authority_files: list[Path]


def model_authority(model: str) -> Authority:
    if model == "a":
        timeline_config = load_json(A_TIMELINE_CONFIG)
        p58_config_path = resolve_root(timeline_config["package58_config"])
        p58_config = load_json(p58_config_path)
        signal_summary = load_json(A_SIGNAL_SUMMARY)
        if signal_summary.get("status") != "PASS":
            raise RuntimeError("model-A candidate-own signal summary is not PASS")
        signal_cell = signal_summary["effective_area"][FINAL_WINDOW][FINAL_STAGE]
        signal = {
            "authority": relative(A_SIGNAL_SUMMARY),
            "input_rays": int(signal_summary["events"]),
            "stage_count": int(signal_cell["count"]),
            "optical_aperture_cm2": float(signal_summary["optical_aperture_cm2"]),
            "aeff_cm2": float(signal_cell["Aeff_cm2"]),
            "aeff_sigma_cm2": float(signal_cell["Aeff_binomial_sigma_cm2"]),
            "scope": "package63 SG3B candidate-own 37,194-ray signal",
        }
        if not math.isclose(signal["aeff_cm2"], 15.12324, rel_tol=0.0, abs_tol=5e-12):
            raise RuntimeError("model-A signal Aeff differs from package63 authority")
        return Authority(
            model=model,
            candidate="SG3B",
            config=timeline_config,
            mission=p58_config["mission"],
            timeline=timeline_config["timeline"],
            activation_path=Path(p58_config["activation_manifest"]),
            signal=signal,
            authority_files=[
                A_TIMELINE_CONFIG,
                p58_config_path,
                A_CATALOG_CODE,
                A_CANDIDATE_TIMELINE_CODE,
                A_CANDIDATE_TIMELINE_SUMMARY,
                A_SIGNAL_SUMMARY,
                P58_CODE,
                A_PROMPT_ADAPTER,
                A_CORRECTED_CORE,
                A_STEP05_CODE,
                A_STEP09_SUMMARY,
            ],
        )

    config = load_json(B_TIMELINE_CONFIG)
    baseline = load_json(B_TIMELINE_SUMMARY)
    signal_block = baseline["signal_aeff"]
    n_input = int(signal_block["input_rays"])
    n_selected = int(signal_block["stage_counts"][FINAL_WINDOW][FINAL_STAGE])
    aperture = float(signal_block["optical_aperture_cm2"])
    probability = n_selected / n_input
    sigma = aperture * math.sqrt(probability * (1.0 - probability) / n_input)
    signal = {
        "authority": relative(B_TIMELINE_SUMMARY),
        "input_rays": n_input,
        "stage_count": n_selected,
        "optical_aperture_cm2": aperture,
        "aeff_cm2": float(signal_block["aeff_cm2"][FINAL_WINDOW][FINAL_STAGE]),
        "aeff_sigma_cm2": sigma,
        "scope": "current SH3 OptV3-B focal-z=-2.8 37,194-ray signal",
    }
    if not math.isclose(signal["aeff_cm2"], 15.08544, rel_tol=0.0, abs_tol=5e-12):
        raise RuntimeError("model-B signal Aeff differs from current OptV3-B authority")
    return Authority(
        model=model,
        candidate=str(config["candidate"]),
        config=config,
        mission=config["mission"],
        timeline=config["timeline"],
        activation_path=Path(config["campaigns"]["activation_manifest"]),
        signal=signal,
        authority_files=[
            B_TIMELINE_CONFIG,
            B_CATALOG_CODE,
            B_TIMELINE_CODE,
            B_TIMELINE_SUMMARY,
            P58_CODE,
            B_STEP05_CODE,
        ],
    )


class Replay:
    def __init__(
        self,
        model: str,
        catalog_dir: Path,
        source_dir: Path,
        exposure_s: float,
        signal_trials: int,
        chunk_events: int,
        seed: int,
    ) -> None:
        self.model = model
        self.catalog_dir = catalog_dir
        self.source_dir = source_dir
        self.exposure_s = exposure_s
        self.signal_trials = signal_trials
        self.chunk_events = chunk_events
        self.seed = seed
        assert_continuum_fold_once_contract()
        assert_day15_product_schema_contract()
        self.authority = model_authority(model)
        configured_anchors = tuple(
            int(value) for value in self.authority.timeline["anchor_time_bin_ids"]
        )
        if configured_anchors != ANCHOR_NODES:
            raise RuntimeError(
                f"mature anchor contract changed: {configured_anchors} != {ANCHOR_NODES}"
            )
        if not math.isclose(
            float(self.authority.timeline["coincidence_window_s"]),
            1.0e-6,
            rel_tol=0.0,
            abs_tol=1e-18,
        ):
            raise RuntimeError("mature coincidence window is not 1 microsecond")
        if not math.isclose(
            float(self.authority.mission["source_elevation_deg"]),
            45.0,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise RuntimeError("mature mission source elevation is not 45 degrees")
        self.p58 = load_module(f"fluxclosed_p58_{model}", P58_CODE)
        self._load_mission_axes()
        self._load_inventory()
        self._load_catalog()
        self._load_response()
        self.fingerprint_payload = self._build_fingerprint()
        self.fingerprint_sha256 = canonical_digest(self.fingerprint_payload)

    def _load_mission_axes(self) -> None:
        scales_path = resolve_root(self.authority.mission["family_scales"])
        atmosphere_path = resolve_root(self.authority.mission["atmospheric_transmission"])
        component_path = self.source_dir / "trajectory_component_scales_81nodes.csv"
        line_path = self.source_dir / "mono511_target_81x80.csv"
        source_closure_path = self.source_dir / "source_closure.json"
        for path in (
            scales_path,
            atmosphere_path,
            component_path,
            line_path,
            source_closure_path,
        ):
            if not path.is_file():
                raise FileNotFoundError(path)
        self.scales_path = scales_path
        self.atmosphere_path = atmosphere_path
        self.component_path = component_path
        self.line_path = line_path
        self.source_closure_path = source_closure_path
        source_closure = load_json(source_closure_path)
        if not str(source_closure.get("status", "")).startswith("COMPLETE__"):
            raise RuntimeError("source_closure.json is not complete")
        line_energy_mev = float(
            source_closure["mono511_target"]["line_energy_MeV"]
        )
        if not math.isclose(line_energy_mev, 0.51099895, rel_tol=0.0, abs_tol=5e-13):
            raise RuntimeError(
                f"mono511 source energy is {line_energy_mev} MeV, not 0.51099895 MeV"
            )
        self.scales = sorted(read_csv(scales_path), key=lambda row: int(row["time_bin_id"]))
        self.atmosphere = sorted(read_csv(atmosphere_path), key=lambda row: int(row["time_bin_id"]))
        components = sorted(read_csv(component_path), key=lambda row: int(row["time_bin_id"]))
        if len(self.scales) != 81 or len(self.atmosphere) != 81 or len(components) != 81:
            raise RuntimeError("mission/source component axes must each contain 81 nodes")
        self.days = np.empty(81, dtype=np.float64)
        self.gamma_scale = np.empty(81, dtype=np.float64)
        for node, (scale, atmosphere, component) in enumerate(
            zip(self.scales, self.atmosphere, components)
        ):
            ids = (
                int(scale["time_bin_id"]),
                int(atmosphere["time_bin_id"]),
                int(component["time_bin_id"]),
            )
            if ids != (node, node, node):
                raise RuntimeError(f"mission time_bin_id mismatch at node {node}: {ids}")
            days = (
                float(scale["day_mid"]),
                float(atmosphere["day_mid"]),
                float(component["day_mid"]),
            )
            if not (
                math.isclose(days[0], days[1], rel_tol=0.0, abs_tol=1e-12)
                and math.isclose(days[0], days[2], rel_tol=0.0, abs_tol=1e-12)
            ):
                raise RuntimeError(f"mission day_mid mismatch at node {node}: {days}")
            gamma_existing = float(scale["scale_gamma_to_parma_reference"])
            gamma_component = float(component["gamma_continuum_scale_to_reference"])
            if not math.isclose(gamma_existing, gamma_component, rel_tol=2e-13, abs_tol=2e-15):
                raise RuntimeError(f"continuum gamma scale mismatch at node {node}")
            self.days[node] = days[0]
            self.gamma_scale[node] = gamma_component
        if not math.isclose(self.days[-1], float(self.authority.mission["duration_days"]), abs_tol=1e-12):
            raise RuntimeError("mission time axis does not end at configured duration")
        if not math.isclose(self.days[DAY15_NODE], 15.0, abs_tol=1e-12):
            raise RuntimeError("time_bin_id 60 is not day 15")

        required_columns = {
            "time_bin_id",
            "day_mid",
            "source_bin80",
            "target_flux_ph_cm2_s",
            "proposal_flux_ph_cm2_s",
            "importance_ratio",
        }
        line_rows = read_csv(line_path)
        if len(line_rows) != 81 * 80:
            raise RuntimeError(f"mono511 importance table has {len(line_rows)} rows, expected 6480")
        if not line_rows or not required_columns <= set(line_rows[0]):
            raise RuntimeError("mono511 importance table is missing fixed-schema columns")
        self.line_ratio = np.full((81, 80), np.nan, dtype=np.float64)
        self.line_target_flux = np.full((81, 80), np.nan, dtype=np.float64)
        self.line_proposal_flux = np.full((81, 80), np.nan, dtype=np.float64)
        for row in line_rows:
            node = int(row["time_bin_id"])
            source_bin = int(row["source_bin80"])
            if not (0 <= node < 81 and 0 <= source_bin < 80):
                raise RuntimeError(f"invalid mono511 node/bin: {(node, source_bin)}")
            if math.isfinite(self.line_ratio[node, source_bin]):
                raise RuntimeError(f"duplicate mono511 node/bin: {(node, source_bin)}")
            day = float(row["day_mid"])
            if not math.isclose(day, self.days[node], rel_tol=0.0, abs_tol=1e-12):
                raise RuntimeError(f"mono511 day mismatch at node {node}")
            target = float(row["target_flux_ph_cm2_s"])
            proposal = float(row["proposal_flux_ph_cm2_s"])
            ratio = float(row["importance_ratio"])
            if not (math.isfinite(target) and target >= 0.0):
                raise RuntimeError(f"invalid target mono511 flux at {(node, source_bin)}")
            if not (math.isfinite(proposal) and proposal > 0.0):
                raise RuntimeError(f"invalid proposal mono511 flux at {(node, source_bin)}")
            if not (math.isfinite(ratio) and ratio >= 0.0):
                raise RuntimeError(f"invalid mono511 importance ratio at {(node, source_bin)}")
            if not math.isclose(target / proposal, ratio, rel_tol=2e-12, abs_tol=2e-15):
                raise RuntimeError(f"mono511 target/proposal ratio mismatch at {(node, source_bin)}")
            self.line_target_flux[node, source_bin] = target
            self.line_proposal_flux[node, source_bin] = proposal
            self.line_ratio[node, source_bin] = ratio
        if not np.all(np.isfinite(self.line_ratio)):
            raise RuntimeError("mono511 importance table does not cover every 81x80 cell")
        for node, component in enumerate(components):
            target_total = float(component["target_mono511_flux_ph_cm2_s"])
            weighted_proposal = float(
                np.dot(self.line_proposal_flux[node], self.line_ratio[node])
            )
            if not math.isclose(
                float(np.sum(self.line_target_flux[node])),
                target_total,
                rel_tol=2e-12,
                abs_tol=2e-12,
            ):
                raise RuntimeError(f"mono511 target-flux closure mismatch at node {node}")
            if not math.isclose(weighted_proposal, target_total, rel_tol=2e-12, abs_tol=2e-12):
                raise RuntimeError(f"mono511 proposal reweight closure mismatch at node {node}")

    def _load_inventory(self) -> None:
        if not self.authority.activation_path.is_file():
            raise FileNotFoundError(self.authority.activation_path)
        activation = load_json(self.authority.activation_path)
        self.inventory = self.p58.inventory_authority(activation)
        curves = self.p58.activity_curves(self.inventory, self.scales)
        self.curves = {
            key: np.asarray(value, dtype=np.float64) for key, value in curves.items()
        }
        if any(len(value) != 81 for value in self.curves.values()):
            raise RuntimeError("delayed isotope activity curve is not 81 nodes")

    def _load_catalog(self) -> None:
        catalog_path = self.catalog_dir / "combined_event_catalog.npz"
        registry_path = self.catalog_dir / "category_registry.json"
        audit_path = self.catalog_dir / "audit.json"
        if not catalog_path.is_file():
            raise FileNotFoundError(catalog_path)
        if not registry_path.is_file():
            raise FileNotFoundError(registry_path)
        if not audit_path.is_file():
            raise FileNotFoundError(audit_path)
        self.catalog_path = catalog_path
        self.registry_path = registry_path
        self.catalog_audit_path = audit_path
        with np.load(catalog_path, allow_pickle=False) as data:
            missing = sorted((set(EVENT_FIELDS) | set(HIT_FIELDS)) - set(data.files))
            if missing:
                raise RuntimeError(f"combined catalog missing arrays: {missing}")
            self.a = {key: data[key] for key in data.files}
        n_events = len(self.a["event_category"])
        if n_events <= 0:
            raise RuntimeError("combined catalog is empty")
        for field in EVENT_FIELDS:
            if self.a[field].ndim != 1 or len(self.a[field]) != n_events:
                raise RuntimeError(f"event array length mismatch: {field}")
        n_hits = len(self.a["hit_code"])
        for field in HIT_FIELDS:
            if self.a[field].ndim != 1 or len(self.a[field]) != n_hits:
                raise RuntimeError(f"hit array length mismatch: {field}")
        if self.a["event_base_weight_cps"].dtype != np.dtype("float64"):
            raise RuntimeError("event_base_weight_cps must be float64")
        if self.a["event_component"].dtype != np.dtype("uint8"):
            raise RuntimeError("event_component must be uint8")
        if self.a["source_bin80"].dtype != np.dtype("uint8"):
            raise RuntimeError("source_bin80 must be uint8")
        if not np.issubdtype(self.a["continuum_importance_weight"].dtype, np.floating):
            raise RuntimeError("continuum_importance_weight must be floating point")
        base = self.a["event_base_weight_cps"]
        if not np.all(np.isfinite(base)) or np.any(base <= 0.0):
            raise RuntimeError("event_base_weight_cps must be finite and strictly positive")
        if np.any(self.a["event_component"] > 2):
            raise RuntimeError("event_component contains codes outside 0/1/2")
        continuum_mask = self.a["event_component"] == COMPONENT_CODES["gamma_continuum"]
        continuum_importance = self.a["continuum_importance_weight"][continuum_mask]
        if (
            len(continuum_importance) == 0
            or np.any(~np.isfinite(continuum_importance))
            or np.any(continuum_importance <= 0.0)
            or np.any(continuum_importance > 1.0)
        ):
            raise RuntimeError("gamma-continuum importance weights must satisfy 0 < w <= 1")
        line_mask = self.a["event_component"] == COMPONENT_CODES["atm511"]
        if not np.any(line_mask):
            raise RuntimeError("flux-closed catalog contains no atmospheric-511 component")
        if np.any(self.a["source_bin80"][line_mask] >= 80):
            raise RuntimeError("atmospheric-511 events must have source_bin80 in 0..79")
        if np.any(self.a["source_bin80"][~line_mask] != 255):
            raise RuntimeError("non-line events must have source_bin80=255")
        if set(np.unique(self.a["source_bin80"][line_mask]).tolist()) != set(range(80)):
            raise RuntimeError("atmospheric-511 catalog does not cover all 80 source bins")
        if not np.any(continuum_mask):
            raise RuntimeError("flux-closed catalog contains no gamma-continuum component")
        hit_end = self.a["hit_start"].astype(np.int64) + self.a["hit_count"].astype(np.int64)
        if (
            np.any(self.a["hit_start"] < 0)
            or np.any(hit_end < self.a["hit_start"])
            or np.any(hit_end > n_hits)
        ):
            raise RuntimeError("event hit ranges exceed hit arrays")
        if (
            int(self.a["hit_start"][0]) != 0
            or np.any(self.a["hit_start"][1:] != hit_end[:-1])
            or int(hit_end[-1]) != n_hits
        ):
            raise RuntimeError("event hit ranges are not one contiguous packed hit catalog")

        registry = load_json(registry_path)
        if not isinstance(registry, dict) or not isinstance(registry.get("categories"), list):
            raise RuntimeError("category_registry.json must contain a categories list")
        if registry.get("weight_authority") != (
            "combined_event_catalog.npz:event_base_weight_cps"
        ):
            raise RuntimeError(
                "category registry does not declare event_base_weight_cps as authority"
            )
        categories = sorted(registry["categories"], key=lambda row: int(row["category_id"]))
        if [int(row["category_id"]) for row in categories] != list(range(len(categories))):
            raise RuntimeError("category IDs must be contiguous from zero")
        self.categories = categories
        self.n_categories = len(categories)
        self.starts = np.empty(self.n_categories, dtype=np.int64)
        self.counts = np.empty(self.n_categories, dtype=np.int64)
        self.cat_components = np.empty(self.n_categories, dtype=np.uint8)
        self.cat_component_names: list[str] = []
        self.streams: list[str] = []
        self.families: list[str] = []
        self.zas = np.full(self.n_categories, -1, dtype=np.int64)
        expected_start = 0
        for category_id, row in enumerate(categories):
            for key in ("event_start", "event_count", "stream", "family", "component"):
                if key not in row:
                    raise RuntimeError(f"category {category_id} missing {key}")
            start = int(row["event_start"])
            count = int(row["event_count"])
            if start != expected_start or count <= 0:
                raise RuntimeError(
                    f"category {category_id} range is not positive contiguous coverage"
                )
            stop = start + count
            if stop > n_events:
                raise RuntimeError(f"category {category_id} exceeds event catalog")
            if not np.all(self.a["event_category"][start:stop] == category_id):
                raise RuntimeError(f"event_category disagrees with registry category {category_id}")
            code, name = normalized_component(row["component"])
            if not np.all(self.a["event_component"][start:stop] == code):
                raise RuntimeError(f"event_component disagrees with category {category_id}")
            stream = str(row["stream"])
            family = str(row["family"])
            if stream not in {"prompt", "delayed"}:
                raise RuntimeError(f"category {category_id} has unknown stream {stream!r}")
            if code in (1, 2) and stream != "prompt":
                raise RuntimeError(f"weighted continuum/line category {category_id} is not prompt")
            if code == 1 and family != "gamma":
                raise RuntimeError(f"continuum category {category_id} is not gamma family")
            if code == 1:
                if row.get("weight_policy") != "per_event_catalog_array":
                    raise RuntimeError(
                        f"continuum category {category_id} lacks per-event weight authority"
                    )
                if row.get("proposal_event_weight_cps") is None:
                    raise RuntimeError(
                        f"continuum category {category_id} lacks proposal_event_weight_cps"
                    )
                proposal_weight = float(row["proposal_event_weight_cps"])
                importance = self.a["continuum_importance_weight"][start:stop]
                actual_weight = self.a["event_base_weight_cps"][start:stop]
                absolute_tolerance = max(2e-18, abs(proposal_weight) * 2e-15)
                for offset in range(0, count, 1_000_000):
                    chunk = slice(offset, min(offset + 1_000_000, count))
                    if not np.allclose(
                        actual_weight[chunk],
                        proposal_weight * importance[chunk],
                        rtol=2e-12,
                        atol=absolute_tolerance,
                    ):
                        raise RuntimeError(
                            f"continuum category {category_id} violates "
                            "event_base_weight=proposal_weight*importance; refusing "
                            "an ambiguous or double-weighted catalog"
                        )
            if code == 2:
                recorded_target = row.get("mono511_target_81x80")
                if recorded_target is None or resolve_root(recorded_target).resolve() != (
                    self.line_path.resolve()
                ):
                    raise RuntimeError(
                        f"line category {category_id} does not bind the selected "
                        "mono511_target_81x80.csv"
                    )
            if code == 0 and stream == "prompt" and family == "gamma":
                raise RuntimeError(
                    f"prompt gamma category {category_id} is not tagged gamma_continuum"
                )
            if stream == "delayed":
                if "source_parent_ZA" not in row:
                    raise RuntimeError(f"delayed category {category_id} lacks source_parent_ZA")
                za = int(row["source_parent_ZA"])
                key = (family, za)
                if key not in self.inventory:
                    raise RuntimeError(f"delayed category absent from isotope inventory: {key}")
                if float(self.inventory[key]["day15_activity_Bq"]) <= 0.0:
                    raise RuntimeError(f"delayed category has nonpositive day15 activity: {key}")
                self.zas[category_id] = za
            self.starts[category_id] = start
            self.counts[category_id] = count
            self.cat_components[category_id] = code
            self.cat_component_names.append(name)
            self.streams.append(stream)
            self.families.append(family)
            expected_start = stop
        if expected_start != n_events:
            raise RuntimeError("category registry does not cover every event")
        catalog_audit = load_json(audit_path)
        if (
            catalog_audit.get("status") != "PASS__FLUXCLOSED_CATALOG_AUDIT"
            or catalog_audit.get("model") != self.model
        ):
            raise RuntimeError("flux-closed catalog audit is not PASS for this model")
        expected_mature_input = (
            "engineering/geometry_optimization_20260815/"
            "62_sg3b_mature_poisson_timeline_20260818/outputs/01_event_catalog"
            if self.model == "a"
            else "DEEPSEEK_CODE/outputs/04_event_catalog_step05_m05_fixed_20260820"
        )
        if catalog_audit.get("mature_input") != expected_mature_input:
            raise RuntimeError(
                f"catalog mature input is not current model-{self.model} authority"
            )
        source_audit = catalog_audit.get("source_closure", {})
        if source_audit.get("manifest_sha256") != sha256_file(
            self.source_closure_path
        ):
            raise RuntimeError("catalog/source-closure manifest hash mismatch")
        gamma_authority = catalog_audit.get("gamma_authority", {})
        if self.model == "a" and gamma_authority.get("supplement_summary") != (
            "engineering/geometry_optimization_20260815/"
            "63_m05new_sg3b_signal_statistics_20260820/outputs/03_expanded_catalog/"
            "summary.json"
        ):
            raise RuntimeError("model-A catalog does not include package63 gamma supplement")
        if self.model == "b" and gamma_authority.get("mature_summary") != (
            "DEEPSEEK_CODE/outputs/04_event_catalog_step05_m05_fixed_20260820/"
            "summary.json"
        ):
            raise RuntimeError("model-B catalog does not use current SH3 OptV3-B gamma")
        expected_line_summary = (
            "engineering/geometry_optimization_20260815/"
            "67_m05_mono511_flux_closure_20260823/outputs/"
            + (
                "01_line_response_a/summary.json"
                if self.model == "a"
                else "01_line_response_b60/summary.json"
            )
        )
        if catalog_audit.get("line", {}).get("summary") != expected_line_summary:
            raise RuntimeError(
                f"catalog line response is not the current model-{self.model} authority"
            )
        summary_path = self.catalog_dir / "summary.json"
        if summary_path.is_file():
            catalog_summary = load_json(summary_path)
            if not str(catalog_summary.get("status", "")).startswith("COMPLETE__"):
                raise RuntimeError("flux-closed catalog summary is not complete")
            if catalog_summary.get("model") != self.model:
                raise RuntimeError("flux-closed catalog summary model mismatch")

        self.total_aggregates: list[Aggregate] = []
        self.selection_aggregates: dict[tuple[int, str, str], Aggregate] = {}
        self.continuum_qmax = np.zeros(self.n_categories, dtype=np.float64)
        self.continuum_acceptance = np.ones(self.n_categories, dtype=np.float64)
        self.line_indices: dict[int, list[np.ndarray]] = {}
        self.common_factor = np.ones((81, self.n_categories), dtype=np.float64)
        self._precompute_category_factors()
        self._precompute_aggregates()
        self.category_rate_matrix = np.empty((81, self.n_categories), dtype=np.float64)
        for node in range(81):
            for category_id in range(self.n_categories):
                self.category_rate_matrix[node, category_id] = self._aggregate_value(
                    self.total_aggregates[category_id], category_id, node
                )[0]
        if np.any(~np.isfinite(self.category_rate_matrix)) or np.any(self.category_rate_matrix < 0):
            raise RuntimeError("category-rate matrix contains invalid values")
        if np.any(np.sum(self.category_rate_matrix, axis=1) <= 0.0):
            raise RuntimeError("catalog total rate is nonpositive on the mission axis")

    def _precompute_category_factors(self) -> None:
        for category_id in range(self.n_categories):
            code = int(self.cat_components[category_id])
            if code == COMPONENT_CODES["atm511"]:
                self.common_factor[:, category_id] = np.nan
                continue
            if code == COMPONENT_CODES["gamma_continuum"]:
                self.common_factor[:, category_id] = self.gamma_scale
                continue
            family = self.families[category_id]
            if self.streams[category_id] == "prompt":
                self.common_factor[:, category_id] = np.asarray(
                    [
                        float(row[f"scale_{family}_to_parma_reference"])
                        for row in self.scales
                    ],
                    dtype=np.float64,
                )
            else:
                key = (family, int(self.zas[category_id]))
                day15 = float(self.inventory[key]["day15_activity_Bq"])
                self.common_factor[:, category_id] = self.curves[key] / day15

    @staticmethod
    def _constant(values: np.ndarray, label: str) -> None:
        minimum = float(np.min(values))
        maximum = float(np.max(values))
        tolerance = max(2e-18, abs(maximum) * 2e-12)
        if maximum - minimum > tolerance:
            raise RuntimeError(f"{label} is not constant within its exact-sampling stratum")

    def _precompute_aggregates(self) -> None:
        line_bin_seen = np.zeros(80, dtype=np.int64)
        for category_id in range(self.n_categories):
            start = int(self.starts[category_id])
            stop = start + int(self.counts[category_id])
            base = self.a["event_base_weight_cps"][start:stop]
            code = int(self.cat_components[category_id])
            line_bins: np.ndarray | None = None
            q: np.ndarray | None = None
            if code == COMPONENT_CODES["other"]:
                self._constant(base, f"category {category_id} event_base_weight_cps")
                q = continuum_reference_weight(base)
            elif code == COMPONENT_CODES["gamma_continuum"]:
                # The catalog builder has already folded this audit importance
                # into event_base_weight_cps.  q=base is the physical reference
                # weight; multiplying by importance here would incorrectly use
                # Jcont/Jtotal twice.
                q = base
                qmax = float(np.max(q))
                if qmax <= 0.0:
                    raise RuntimeError(f"continuum category {category_id} has zero proposal bound")
                self.continuum_qmax[category_id] = qmax
                self.continuum_acceptance[category_id] = float(np.sum(q)) / (
                    len(q) * qmax
                )
            else:
                line_bins = self.a["source_bin80"][start:stop].astype(np.int64, copy=False)
                index_by_bin: list[np.ndarray] = []
                for source_bin in range(80):
                    local = np.flatnonzero(line_bins == source_bin)
                    absolute = local.astype(np.int64, copy=False) + start
                    index_by_bin.append(absolute)
                    if len(local):
                        self._constant(
                            base[local],
                            f"line category {category_id} source_bin80={source_bin} base weight",
                        )
                        line_bin_seen[source_bin] += len(local)
                self.line_indices[category_id] = index_by_bin
            total_aggregate = self._aggregate_local(base, q, line_bins, None)
            self.total_aggregates.append(total_aggregate)
            actual_sum = (
                float(np.sum(total_aggregate.bin_sum_q))
                if total_aggregate.bin_sum_q is not None
                else total_aggregate.sum_q
            )
            actual_sum2 = (
                float(np.sum(total_aggregate.bin_sum_q2))
                if total_aggregate.bin_sum_q2 is not None
                else total_aggregate.sum_q2
            )
            row = self.categories[category_id]
            for field, actual in (
                ("sum_event_base_weight_cps", actual_sum),
                ("sum_event_base_weight2_cps2", actual_sum2),
            ):
                if field not in row or not math.isclose(
                    actual,
                    float(row[field]),
                    rel_tol=3e-12,
                    abs_tol=max(2e-18, abs(actual) * 2e-15),
                ):
                    raise RuntimeError(
                        f"category {category_id} {field} does not close to "
                        "event_base_weight_cps"
                    )
            for window, field in (
                ("broad_480_550", "broad_flags"),
                ("w2_510p58_511p42", "w2_flags"),
            ):
                flags = self.a[field][start:stop]
                for stage, bit in STAGE_BITS.items():
                    mask = (flags & bit) != 0
                    self.selection_aggregates[(category_id, window, stage)] = (
                        self._aggregate_local(base, q, line_bins, mask)
                    )
        if np.any(line_bin_seen == 0):
            missing = np.flatnonzero(line_bin_seen == 0).tolist()
            raise RuntimeError(f"line event catalog lacks source bins: {missing}")

    @staticmethod
    def _aggregate_local(
        base: np.ndarray,
        q: np.ndarray | None,
        line_bins: np.ndarray | None,
        mask: np.ndarray | None,
    ) -> Aggregate:
        if mask is None:
            count = len(base)
            selected_base = base
            selected_q = q
            selected_bins = line_bins
        else:
            count = int(np.count_nonzero(mask))
            selected_base = base[mask]
            selected_q = q[mask] if q is not None else None
            selected_bins = line_bins[mask] if line_bins is not None else None
        if line_bins is None:
            if selected_q is None:
                raise RuntimeError("internal aggregate error: missing scalar q")
            return Aggregate(
                count=count,
                sum_q=float(np.sum(selected_q, dtype=np.float64)),
                sum_q2=float(np.dot(selected_q, selected_q)),
            )
        return Aggregate(
            count=count,
            bin_sum_q=np.bincount(
                selected_bins, weights=selected_base, minlength=80
            ).astype(np.float64),
            bin_sum_q2=np.bincount(
                selected_bins, weights=selected_base * selected_base, minlength=80
            ).astype(np.float64),
        )

    def _load_response(self) -> None:
        if self.model == "a":
            self.response_code = load_module("fluxclosed_response_a", A_CATALOG_CODE)
            self.parser, self.response_core, self.step05, self.side_disk = self.p58.runtime()
            self.reject_policy = ""
            self.sigma_keV = float(self.response_core.SIGMA_KEV)
            self.pixel_threshold_keV = float(self.response_core.PIXEL_THRESHOLD_KEV)
        else:
            module_dir = str(B_CATALOG_CODE.parent)
            if module_dir not in sys.path:
                sys.path.insert(0, module_dir)
            self.response_code = load_module("fluxclosed_response_b", B_CATALOG_CODE)
            side = self.authority.config["side_entry_disk"]
            self.side_disk = self.response_code.side_entry_disk(
                tuple(float(value) for value in side["local_center_cm"]),
                float(side["radius_cm"]),
                float(side["rotation_y_deg"]),
            )
            self.reject_policy = str(side.get("reject_policy", "keep"))
            self.sigma_keV = float(self.response_code.SIGMA_KEV)
            self.pixel_threshold_keV = float(self.response_code.PIXEL_THRESHOLD_KEV)
        plastic_threshold = float(self.authority.timeline["plastic_threshold_keV"])
        bgo_threshold = float(self.authority.timeline["bgo_threshold_keV"])
        if not math.isclose(plastic_threshold, bgo_threshold, rel_tol=0.0, abs_tol=1e-15):
            raise RuntimeError("mature response helper requires identical plastic/BGO thresholds")
        self.veto_threshold_keV = plastic_threshold
        if tuple(self.response_code.STAGE_BITS) != STAGES:
            raise RuntimeError("response stage ordering differs from mature five-stage contract")
        if dict(self.response_code.WINDOWS) != WINDOWS:
            raise RuntimeError("response windows differ from mature W2/broad contract")

    def _build_fingerprint(self) -> dict[str, Any]:
        catalog_stat = self.catalog_path.stat()
        files = list(self.authority.authority_files) + [
            self.registry_path,
            self.catalog_audit_path,
            self.line_path,
            self.component_path,
            self.source_closure_path,
            self.scales_path,
            self.atmosphere_path,
            self.authority.activation_path,
            HERE,
        ]
        summary_path = self.catalog_dir / "summary.json"
        if summary_path.is_file():
            files.append(summary_path)
        file_hashes = {}
        for path in files:
            if not path.is_file():
                raise FileNotFoundError(path)
            file_hashes[relative(path)] = sha256_file(path)
        schema = {
            key: {"shape": list(self.a[key].shape), "dtype": str(self.a[key].dtype)}
            for key in sorted(self.a)
        }
        return {
            "schema_version": 1,
            "model": self.model,
            "candidate": self.authority.candidate,
            "catalog_npz": {
                "path": relative(self.catalog_path),
                "bytes": catalog_stat.st_size,
                "mtime_ns": catalog_stat.st_mtime_ns,
                "arrays": schema,
            },
            "catalog_events": int(len(self.a["event_category"])),
            "catalog_hits": int(len(self.a["hit_code"])),
            "catalog_categories": self.n_categories,
            "component_event_counts": {
                name: int(np.count_nonzero(self.a["event_component"] == code))
                for code, name in enumerate(COMPONENT_NAMES)
            },
            "continuum_weight_contract": (
                "PASS__event_base_weight_equals_proposal_times_importance__"
                "importance_not_applied_again"
            ),
            "file_sha256": file_hashes,
            "parameters": {
                "anchor_time_bin_ids": list(ANCHOR_NODES),
                "exposure_s_per_anchor": self.exposure_s,
                "signal_probe_trials_per_anchor": self.signal_trials,
                "chunk_events": self.chunk_events,
                "seed": self.seed,
                "coincidence_window_s": float(
                    self.authority.timeline["coincidence_window_s"]
                ),
            },
        }

    def _aggregate_value(
        self, aggregate: Aggregate, category_id: int, node: int
    ) -> tuple[float, float]:
        if int(self.cat_components[category_id]) == COMPONENT_CODES["atm511"]:
            if aggregate.bin_sum_q is None or aggregate.bin_sum_q2 is None:
                raise RuntimeError("internal line aggregate missing bin arrays")
            ratios = self.line_ratio[node]
            return (
                float(np.dot(aggregate.bin_sum_q, ratios)),
                float(np.dot(aggregate.bin_sum_q2, ratios * ratios)),
            )
        factor = float(self.common_factor[node, category_id])
        return aggregate.sum_q * factor, aggregate.sum_q2 * factor * factor

    def category_rates(self, node: int) -> np.ndarray:
        return self.category_rate_matrix[node].copy()

    def direct_stats(self, node: int, window: str, stage: str) -> dict[str, Any]:
        components = {
            name: {"rate_cps": 0.0, "sum_wi2_cps2": 0.0, "selected_raw": 0}
            for name in COMPONENT_NAMES
        }
        for category_id in range(self.n_categories):
            aggregate = self.selection_aggregates[(category_id, window, stage)]
            rate, variance = self._aggregate_value(aggregate, category_id, node)
            target = components[self.cat_component_names[category_id]]
            target["rate_cps"] += rate
            target["sum_wi2_cps2"] += variance
            target["selected_raw"] += aggregate.count
        total_rate = math.fsum(float(item["rate_cps"]) for item in components.values())
        total_variance = math.fsum(
            float(item["sum_wi2_cps2"]) for item in components.values()
        )
        return {
            "rate_cps": total_rate,
            "sum_wi2_cps2": total_variance,
            "transport_sigma_cps": math.sqrt(total_variance),
            "effective_sample_size": effective_sample_size(total_rate, total_variance),
            "selected_raw": sum(int(item["selected_raw"]) for item in components.values()),
            "components": components,
        }

    def event_weights_for_category(self, category_id: int, node: int) -> np.ndarray:
        start = int(self.starts[category_id])
        stop = start + int(self.counts[category_id])
        base = self.a["event_base_weight_cps"][start:stop]
        code = int(self.cat_components[category_id])
        if code == COMPONENT_CODES["gamma_continuum"]:
            return continuum_reference_weight(base) * self.gamma_scale[node]
        if code == COMPONENT_CODES["atm511"]:
            bins = self.a["source_bin80"][start:stop].astype(np.int64, copy=False)
            return base * self.line_ratio[node, bins]
        return base * self.common_factor[node, category_id]

    def _sample_continuum(
        self, rng: np.random.Generator, category_id: int, count: int
    ) -> np.ndarray:
        start = int(self.starts[category_id])
        size = int(self.counts[category_id])
        qmax = float(self.continuum_qmax[category_id])
        acceptance = float(self.continuum_acceptance[category_id])
        output = np.empty(count, dtype=np.int64)
        filled = 0
        while filled < count:
            needed = count - filled
            proposal_count = int(math.ceil(1.05 * needed / max(acceptance, 1e-8)))
            proposal_count = max(min(proposal_count, 2_000_000), min(needed, 2_000_000))
            local = rng.integers(0, size, size=proposal_count, dtype=np.int64)
            absolute = start + local
            # event_base_weight_cps already equals proposal*importance.
            score = continuum_reference_weight(
                self.a["event_base_weight_cps"][absolute]
            )
            accepted = absolute[rng.random(proposal_count) * qmax < score]
            take = min(len(accepted), needed)
            if take:
                output[filled : filled + take] = accepted[:take]
                filled += take
        return output

    def _sample_line(
        self, rng: np.random.Generator, category_id: int, node: int, count: int
    ) -> np.ndarray:
        aggregate = self.total_aggregates[category_id]
        if aggregate.bin_sum_q is None:
            raise RuntimeError("internal line sampling aggregate is absent")
        masses = aggregate.bin_sum_q * self.line_ratio[node]
        total = float(np.sum(masses))
        if total <= 0.0:
            raise RuntimeError(f"cannot sample zero-rate line category {category_id}")
        cumulative = np.cumsum(masses / total)
        cumulative[-1] = 1.0
        bins = np.searchsorted(cumulative, rng.random(count), side="right")
        output = np.empty(count, dtype=np.int64)
        for source_bin in np.unique(bins):
            positions = np.flatnonzero(bins == source_bin)
            candidates = self.line_indices[category_id][int(source_bin)]
            if len(candidates) == 0:
                raise RuntimeError("line bin sampler selected an empty source bin")
            offsets = rng.integers(0, len(candidates), size=len(positions), dtype=np.int64)
            output[positions] = candidates[offsets]
        return output

    def sample_marks(
        self,
        rng: np.random.Generator,
        count: int,
        node: int,
        category_rates: np.ndarray,
    ) -> np.ndarray:
        if count <= 0:
            return np.empty(0, dtype=np.int64)
        total = float(np.sum(category_rates))
        if total <= 0.0:
            raise RuntimeError("cannot sample a zero-rate event catalog")
        cumulative = np.cumsum(category_rates / total)
        cumulative[-1] = 1.0
        categories = np.searchsorted(cumulative, rng.random(count), side="right")
        output = np.empty(count, dtype=np.int64)
        components = self.cat_components[categories]

        # The ordinary categories dominate category cardinality.  They all have
        # a validated constant within-category weight, so sample their varying
        # category sizes in one vectorized pass rather than scanning a
        # million-mark chunk once per isotope category.
        ordinary_positions = np.flatnonzero(
            components == COMPONENT_CODES["other"]
        )
        if len(ordinary_positions):
            ordinary_categories = categories[ordinary_positions]
            offsets = np.floor(
                rng.random(len(ordinary_positions))
                * self.counts[ordinary_categories]
            ).astype(np.int64)
            output[ordinary_positions] = (
                self.starts[ordinary_categories] + offsets
            )

        continuum_positions = np.flatnonzero(
            components == COMPONENT_CODES["gamma_continuum"]
        )
        if len(continuum_positions):
            selected_categories = categories[continuum_positions]
            for category_id in np.unique(selected_categories):
                local_positions = np.flatnonzero(selected_categories == category_id)
                positions = continuum_positions[local_positions]
                output[positions] = self._sample_continuum(
                    rng, int(category_id), len(positions)
                )

        line_positions = np.flatnonzero(components == COMPONENT_CODES["atm511"])
        if len(line_positions):
            selected_categories = categories[line_positions]
            for category_id in np.unique(selected_categories):
                local_positions = np.flatnonzero(selected_categories == category_id)
                positions = line_positions[local_positions]
                output[positions] = self._sample_line(
                    rng, int(category_id), node, len(positions)
                )
        return output

    def combined_flags(
        self, event_indices: np.ndarray, node: int, serial: int
    ) -> tuple[int, int]:
        plastic = float(np.sum(self.a["plastic_keV"][event_indices], dtype=np.float64))
        bgo = float(np.sum(self.a["bgo_keV"][event_indices], dtype=np.float64))
        pixels: dict[int, dict[str, float | int]] = {}
        for event_index in event_indices:
            start = int(self.a["hit_start"][event_index])
            stop = start + int(self.a["hit_count"][event_index])
            for hit_index in range(start, stop):
                code = int(self.a["hit_code"][hit_index])
                energy = float(self.a["hit_energy_keV"][hit_index])
                if energy <= 0.0:
                    continue
                target = pixels.setdefault(
                    code,
                    {
                        "e": 0.0,
                        "wx": 0.0,
                        "wy": 0.0,
                        "wz": 0.0,
                        "layer": int(self.a["hit_layer"][hit_index]),
                    },
                )
                target["e"] = float(target["e"]) + energy
                target["wx"] = float(target["wx"]) + energy * float(
                    self.a["hit_x_cm"][hit_index]
                )
                target["wy"] = float(target["wy"]) + energy * float(
                    self.a["hit_y_cm"][hit_index]
                )
                target["wz"] = float(target["wz"]) + energy * float(
                    self.a["hit_z_cm"][hit_index]
                )
        measured_hits: list[Any] = []
        for code, record in sorted(pixels.items()):
            energy = float(record["e"])
            if energy <= 0.0:
                continue
            layer = int(record["layer"])
            pixel = code - layer * 100_000
            uid = f"TP_L{layer}_{pixel}"
            if self.model == "a":
                noise = self.response_core.keyed_standard_normal(
                    "sg3b", "mature_timeline", self.seed, node, serial, uid
                )
            else:
                noise = self.response_code.keyed_standard_normal(
                    "sh3_optv3", "mature_timeline", self.seed, serial, code
                )
            measured = energy + self.sigma_keV * noise
            if measured < self.pixel_threshold_keV:
                continue
            measured_hits.append(
                SimpleNamespace(
                    e=measured,
                    x=float(record["wx"]) / energy,
                    y=float(record["wy"]) / energy,
                    z=float(record["wz"]) / energy,
                    pixel_uid=uid,
                    layer=layer,
                )
            )
        measured_total = math.fsum(hit.e for hit in measured_hits)
        if self.model == "a":
            return self.response_code.flags_for_event(
                measured_hits,
                measured_total,
                plastic,
                bgo,
                self.veto_threshold_keV,
                self.p58,
                self.step05,
                self.side_disk,
            )
        return self.response_code.flags_for_event(
            measured_hits,
            measured_total,
            plastic,
            bgo,
            self.veto_threshold_keV,
            self.side_disk,
            self.reject_policy,
        )

    def process_groups(
        self,
        event_indices: np.ndarray,
        starts: np.ndarray,
        ends: np.ndarray,
        node: int,
        state: dict[str, Any],
    ) -> None:
        if len(starts) == 0:
            return
        sizes = ends - starts
        state["groups"] += int(len(starts))
        singles = event_indices[starts[sizes == 1]]
        for window, field in (
            ("broad_480_550", "broad_flags"),
            ("w2_510p58_511p42", "w2_flags"),
        ):
            flags = self.a[field][singles]
            for stage, bit in STAGE_BITS.items():
                state["counts"][(window, stage)] += int(np.count_nonzero(flags & bit))
        multi_mask = sizes > 1
        if not np.any(multi_mask):
            return
        multi_starts = starts[multi_mask]
        multi_ends = ends[multi_mask]
        state["multi_groups"] += int(len(multi_starts))
        tes = (self.a["hit_count"][event_indices] > 0).astype(np.int16)
        cumulative_tes = np.empty(len(tes) + 1, dtype=np.int64)
        cumulative_tes[0] = 0
        np.cumsum(tes, dtype=np.int64, out=cumulative_tes[1:])
        for start, end in zip(multi_starts, multi_ends):
            if cumulative_tes[end] - cumulative_tes[start] <= 0:
                continue
            state["multi_groups_with_raw_tes"] += 1
            selected = event_indices[start:end]
            broad, w2 = self.combined_flags(selected, node, int(state["multi_serial"]))
            state["multi_serial"] += 1
            for window, flags in (
                ("broad_480_550", broad),
                ("w2_510p58_511p42", w2),
            ):
                for stage, bit in STAGE_BITS.items():
                    if flags & bit:
                        state["counts"][(window, stage)] += 1
            streams = {
                self.streams[int(category)]
                for category in self.a["event_category"][selected]
            }
            components = set(int(value) for value in self.a["event_component"][selected])
            if len(streams) > 1:
                state["mixed_stream_groups_with_raw_tes"] += 1
            if len(components) > 1:
                state["mixed_component_groups_with_raw_tes"] += 1

    def timeline(
        self, node: int, category_rates: np.ndarray, rng: np.random.Generator
    ) -> dict[str, Any]:
        total_rate = float(np.sum(category_rates))
        tau = float(self.authority.timeline["coincidence_window_s"])
        state: dict[str, Any] = {
            "groups": 0,
            "multi_groups": 0,
            "multi_groups_with_raw_tes": 0,
            "mixed_stream_groups_with_raw_tes": 0,
            "mixed_component_groups_with_raw_tes": 0,
            "multi_serial": 0,
            "counts": defaultdict(int),
        }
        pending = np.empty(0, dtype=np.int64)
        current_time = 0.0
        generated = 0
        finished = False
        while not finished:
            gaps = rng.exponential(1.0 / total_rate, size=self.chunk_events)
            times = current_time + np.cumsum(gaps)
            accepted = int(np.searchsorted(times, self.exposure_s, side="right"))
            if accepted < self.chunk_events:
                gaps = gaps[:accepted]
                finished = True
            marks = self.sample_marks(rng, len(gaps), node, category_rates)
            generated += len(marks)
            if len(marks):
                current_time = float(times[len(marks) - 1])
            if len(pending):
                combined = np.concatenate((pending, marks))
                boundaries = np.zeros(len(combined), dtype=bool)
                boundaries[0] = True
                if len(marks):
                    offset = len(pending)
                    boundaries[offset] = gaps[0] > tau
                    if len(marks) > 1:
                        boundaries[offset + 1 :] = gaps[1:] > tau
            else:
                combined = marks
                boundaries = np.zeros(len(combined), dtype=bool)
                if len(combined):
                    boundaries[0] = True
                    if len(combined) > 1:
                        boundaries[1:] = gaps[1:] > tau
            group_starts = np.flatnonzero(boundaries)
            if finished:
                group_ends = np.r_[group_starts[1:], len(combined)].astype(np.int64)
                self.process_groups(combined, group_starts, group_ends, node, state)
                pending = np.empty(0, dtype=np.int64)
            elif len(group_starts):
                self.process_groups(
                    combined, group_starts[:-1], group_starts[1:], node, state
                )
                pending = combined[group_starts[-1] :].copy()
        return {
            "node": node,
            "day_mid": float(self.days[node]),
            "exposure_s": self.exposure_s,
            "total_detector_positive_rate_cps": total_rate,
            "event_instances": generated,
            "expected_event_instances": total_rate * self.exposure_s,
            "groups": int(state["groups"]),
            "multi_groups": int(state["multi_groups"]),
            "multi_groups_with_raw_tes": int(state["multi_groups_with_raw_tes"]),
            "mixed_stream_groups_with_raw_tes": int(
                state["mixed_stream_groups_with_raw_tes"]
            ),
            "mixed_component_groups_with_raw_tes": int(
                state["mixed_component_groups_with_raw_tes"]
            ),
            "counts": {
                f"{window}__{stage}": int(state["counts"][(window, stage)])
                for window in WINDOWS
                for stage in STAGES
            },
        }

    def signal_probe(
        self, node: int, category_rates: np.ndarray, rng: np.random.Generator
    ) -> dict[str, Any]:
        total_rate = float(np.sum(category_rates))
        tau = float(self.authority.timeline["coincidence_window_s"])
        stop_probability = math.exp(-total_rate * tau)
        plastic = np.zeros(self.signal_trials, dtype=np.float32)
        bgo = np.zeros(self.signal_trials, dtype=np.float32)
        tes_contaminated = np.zeros(self.signal_trials, dtype=bool)
        neighbors_total = 0
        for _side in ("left", "right"):
            counts = rng.geometric(stop_probability, size=self.signal_trials) - 1
            trial_index = np.repeat(np.arange(self.signal_trials, dtype=np.int64), counts)
            marks = self.sample_marks(rng, len(trial_index), node, category_rates)
            neighbors_total += len(marks)
            if len(marks):
                plastic += np.bincount(
                    trial_index,
                    weights=self.a["plastic_keV"][marks],
                    minlength=self.signal_trials,
                ).astype(np.float32)
                bgo += np.bincount(
                    trial_index,
                    weights=self.a["bgo_keV"][marks],
                    minlength=self.signal_trials,
                ).astype(np.float32)
                contaminated = np.bincount(
                    trial_index,
                    weights=(self.a["hit_count"][marks] > 0).astype(np.uint8),
                    minlength=self.signal_trials,
                )
                tes_contaminated |= contaminated > 0
        keep = (
            (~tes_contaminated)
            & (plastic < self.veto_threshold_keV)
            & (bgo < self.veto_threshold_keV)
        )
        passed = int(np.count_nonzero(keep))
        survival = passed / self.signal_trials
        return {
            "node": node,
            "day_mid": float(self.days[node]),
            "trials": self.signal_trials,
            "passed": passed,
            "conditional_signal_accidental_survival": survival,
            "binomial_standard_error": math.sqrt(
                survival * (1.0 - survival) / self.signal_trials
            ),
            "total_background_rate_cps": total_rate,
            "one_sided_exp_minus_Rtau": stop_probability,
            "two_sided_isolation_exp_minus_2Rtau": stop_probability**2,
            "sampled_neighbor_event_instances": neighbors_total,
            "proxy_boundary": (
                "W2-selected signal is lost by any coincident raw-TES deposit; "
                "active-only deposits from both transitive side chains are summed"
            ),
        }

    def anchor_receipt(self, node: int, ordinal: int, receipt_path: Path) -> dict[str, Any]:
        if receipt_path.is_file():
            receipt = load_json(receipt_path)
            expected = (
                receipt.get("status") == "PASS__FLUXCLOSED_ANCHOR_COMPLETE"
                and receipt.get("model") == self.model
                and int(receipt.get("time_bin_id", -1)) == node
                and receipt.get("input_fingerprint_sha256") == self.fingerprint_sha256
            )
            if not expected:
                raise RuntimeError(f"existing anchor receipt is incompatible: {receipt_path}")
            return receipt
        category_rates = self.category_rates(node)
        direct = {
            f"{window}__{stage}": self.direct_stats(node, window, stage)
            for window in WINDOWS
            for stage in STAGES
        }
        timeline = self.timeline(
            node,
            category_rates,
            np.random.default_rng(np.random.SeedSequence([self.seed, ordinal, 1])),
        )
        signal = self.signal_probe(
            node,
            category_rates,
            np.random.default_rng(np.random.SeedSequence([self.seed, ordinal, 2])),
        )
        final_key = f"{FINAL_WINDOW}__{FINAL_STAGE}"
        final_direct = float(direct[final_key]["rate_cps"])
        final_count = int(timeline["counts"][final_key])
        if final_direct <= 0.0 or final_count <= 0:
            raise RuntimeError(
                f"anchor {node} has nonpositive direct rate or zero final timeline counts"
            )
        timeline_rate = final_count / self.exposure_s
        receipt = {
            "schema_version": 1,
            "status": "PASS__FLUXCLOSED_ANCHOR_COMPLETE",
            "model": self.model,
            "candidate": self.authority.candidate,
            "time_bin_id": node,
            "day_mid": float(self.days[node]),
            "input_fingerprint_sha256": self.fingerprint_sha256,
            "direct": direct,
            "timeline": timeline,
            "signal_probe": signal,
            "final_timeline_to_direct_ratio": timeline_rate / final_direct,
            "final_timeline_to_direct_ratio_standard_error": (
                math.sqrt(final_count) / self.exposure_s / final_direct
            ),
        }
        write_json_exclusive(receipt_path, receipt)
        return receipt

    def day15_products(
        self,
    ) -> tuple[
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
        dict[str, Any],
        dict[str, Any],
    ]:
        node = DAY15_NODE
        cutflow_accumulator: dict[
            tuple[str, str, str, str, str], dict[str, float | int]
        ] = {}
        for category_id in range(self.n_categories):
            metadata = (
                self.streams[category_id],
                self.families[category_id],
                self.cat_component_names[category_id],
            )
            for window in WINDOWS:
                for stage in STAGES:
                    key = (*metadata, window, stage)
                    target = cutflow_accumulator.setdefault(
                        key, {"selected_raw": 0, "sumw": 0.0, "sumw2": 0.0}
                    )
                    aggregate = self.selection_aggregates[
                        (category_id, window, stage)
                    ]
                    sumw, sumw2 = self._aggregate_value(aggregate, category_id, node)
                    target["selected_raw"] = int(target["selected_raw"]) + aggregate.count
                    target["sumw"] = float(target["sumw"]) + sumw
                    target["sumw2"] = float(target["sumw2"]) + sumw2
        cutflow_rows = []
        for key in sorted(cutflow_accumulator):
            stream, family, component, window, stage = key
            item = cutflow_accumulator[key]
            sumw = float(item["sumw"])
            sumw2 = float(item["sumw2"])
            cutflow_rows.append(
                {
                    "time_bin_id": node,
                    "day_mid": float(self.days[node]),
                    "stream": stream,
                    "family": family,
                    "component": component,
                    "window_id": window,
                    "stage": stage,
                    "selected_raw": int(item["selected_raw"]),
                    "sumw_cps": sumw,
                    "sumw2_cps2": sumw2,
                    "sqrt_sumw2_cps": math.sqrt(sumw2),
                    "effective_sample_size": effective_sample_size(sumw, sumw2),
                }
            )

        cutflow_totals = {
            (window, stage): {
                "selected_raw": 0,
                "rate_cps": 0.0,
                "sum_wi2_cps2": 0.0,
            }
            for window in WINDOWS
            for stage in STAGES
        }
        for row in cutflow_rows:
            target = cutflow_totals[(str(row["window_id"]), str(row["stage"]))]
            target["selected_raw"] = int(target["selected_raw"]) + int(
                row["selected_raw"]
            )
            target["rate_cps"] = float(target["rate_cps"]) + float(row["sumw_cps"])
            target["sum_wi2_cps2"] = float(target["sum_wi2_cps2"]) + float(
                row["sumw2_cps2"]
            )
        for (window, stage), totals in cutflow_totals.items():
            direct = self.direct_stats(node, window, stage)
            _require_closure_equal(
                np.asarray(int(totals["selected_raw"])),
                np.asarray(int(direct["selected_raw"])),
                f"day15 cutflow {window}/{stage} selected_raw=direct",
                exact=True,
            )
            _require_closure_equal(
                np.asarray(float(totals["rate_cps"])),
                np.asarray(float(direct["rate_cps"])),
                f"day15 cutflow {window}/{stage} sumw=direct",
                exact=False,
            )
            _require_closure_equal(
                np.asarray(float(totals["sum_wi2_cps2"])),
                np.asarray(float(direct["sum_wi2_cps2"])),
                f"day15 cutflow {window}/{stage} sumw2=direct",
                exact=False,
            )

        energy_edges = np.arange(480.0, 550.0 + 0.125, 0.25, dtype=np.float64)
        spectrum_stages = (
            "pre_veto",
            "combined_active_veto",
            "compton_trajectory_veto",
        )
        spectrum_raw = np.zeros(
            (
                len(spectrum_stages),
                len(STREAM_LABELS),
                len(COMPONENT_LABELS),
                len(energy_edges) - 1,
            ),
            dtype=np.int64,
        )
        spectrum_sum = np.zeros_like(spectrum_raw, dtype=np.float64)
        spectrum_sum2 = np.zeros_like(spectrum_raw, dtype=np.float64)
        stream_indices = {
            stream: 1 + index for index, stream in enumerate(STREAM_NAMES)
        }
        for category_id in range(self.n_categories):
            start = int(self.starts[category_id])
            stop = start + int(self.counts[category_id])
            energies = self.a["measured_total_keV"][start:stop]
            flags = self.a["broad_flags"][start:stop]
            weights = self.event_weights_for_category(category_id, node)
            stream_index = stream_indices[self.streams[category_id]]
            component_index = 1 + int(self.cat_components[category_id])
            for stage_index, stage in enumerate(spectrum_stages):
                mask = (flags & STAGE_BITS[stage]) != 0
                raw, _ = np.histogram(energies[mask], bins=energy_edges)
                sumw, _ = np.histogram(
                    energies[mask], bins=energy_edges, weights=weights[mask]
                )
                sumw2, _ = np.histogram(
                    energies[mask], bins=energy_edges, weights=weights[mask] ** 2
                )
                _accumulate_stream_component_histogram(
                    spectrum_raw,
                    stage_index,
                    stream_index,
                    component_index,
                    raw,
                )
                _accumulate_stream_component_histogram(
                    spectrum_sum,
                    stage_index,
                    stream_index,
                    component_index,
                    sumw,
                )
                _accumulate_stream_component_histogram(
                    spectrum_sum2,
                    stage_index,
                    stream_index,
                    component_index,
                    sumw2,
                )
        assert_spectrum_stream_component_closure(
            spectrum_raw, spectrum_sum, spectrum_sum2
        )
        for stage_index, stage in enumerate(spectrum_stages):
            _assert_histogram_cutflow_closure(
                spectrum_raw[stage_index, 0, 0],
                spectrum_sum[stage_index, 0, 0],
                spectrum_sum2[stage_index, 0, 0],
                cutflow_totals[("broad_480_550", stage)],
                f"day15 spectrum broad_480_550/{stage}",
            )
        spectrum_rows = []
        for stage_index, stage in enumerate(spectrum_stages):
            for stream_index, stream in enumerate(STREAM_LABELS):
                for component_index, component in enumerate(COMPONENT_LABELS):
                    for energy_index in range(len(energy_edges) - 1):
                        sumw = float(
                            spectrum_sum[
                                stage_index, stream_index, component_index, energy_index
                            ]
                        )
                        sumw2 = float(
                            spectrum_sum2[
                                stage_index, stream_index, component_index, energy_index
                            ]
                        )
                        spectrum_rows.append(
                            {
                                "time_bin_id": node,
                                "day_mid": float(self.days[node]),
                                "stage": stage,
                                "stream": stream,
                                "component": component,
                                "energy_low_keV": float(energy_edges[energy_index]),
                                "energy_high_keV": float(
                                    energy_edges[energy_index + 1]
                                ),
                                "selected_raw": int(
                                    spectrum_raw[
                                        stage_index,
                                        stream_index,
                                        component_index,
                                        energy_index,
                                    ]
                                ),
                                "sumw_cps": sumw,
                                "sumw2_cps2": sumw2,
                                "sqrt_sumw2_cps": math.sqrt(sumw2),
                            }
                        )

        selected_for_multiplicity = np.zeros(
            len(self.a["hit_count"]), dtype=np.bool_
        )
        for flag_field in WINDOW_FLAG_FIELDS.values():
            selected_for_multiplicity |= self.a[flag_field] != 0
        max_multiplicity = (
            int(np.max(self.a["hit_count"][selected_for_multiplicity]))
            if np.any(selected_for_multiplicity)
            else 0
        )
        multiplicity_raw = np.zeros(
            (
                len(WINDOW_FLAG_FIELDS),
                len(STAGES),
                len(COMPONENT_LABELS),
                max_multiplicity + 1,
            ),
            dtype=np.int64,
        )
        multiplicity_sum = np.zeros_like(multiplicity_raw, dtype=np.float64)
        multiplicity_sum2 = np.zeros_like(multiplicity_raw, dtype=np.float64)
        for category_id in range(self.n_categories):
            start = int(self.starts[category_id])
            stop = start + int(self.counts[category_id])
            multiplicity = self.a["hit_count"][start:stop].astype(np.int64, copy=False)
            weights = self.event_weights_for_category(category_id, node)
            component_index = 1 + int(self.cat_components[category_id])
            for window_index, (window, flag_field) in enumerate(
                WINDOW_FLAG_FIELDS.items()
            ):
                flags = self.a[flag_field][start:stop]
                for stage_index, stage in enumerate(STAGES):
                    mask = (flags & STAGE_BITS[stage]) != 0
                    raw = np.bincount(
                        multiplicity[mask], minlength=max_multiplicity + 1
                    )
                    sumw = np.bincount(
                        multiplicity[mask],
                        weights=weights[mask],
                        minlength=max_multiplicity + 1,
                    )
                    sumw2 = np.bincount(
                        multiplicity[mask],
                        weights=weights[mask] ** 2,
                        minlength=max_multiplicity + 1,
                    )
                    for target_index in (0, component_index):
                        multiplicity_raw[
                            window_index, stage_index, target_index
                        ] += raw
                        multiplicity_sum[
                            window_index, stage_index, target_index
                        ] += sumw
                        multiplicity_sum2[
                            window_index, stage_index, target_index
                        ] += sumw2
        assert_multiplicity_component_closure(
            multiplicity_raw, multiplicity_sum, multiplicity_sum2
        )
        for window_index, window in enumerate(WINDOW_FLAG_FIELDS):
            for stage_index, stage in enumerate(STAGES):
                _assert_histogram_cutflow_closure(
                    multiplicity_raw[window_index, stage_index, 0],
                    multiplicity_sum[window_index, stage_index, 0],
                    multiplicity_sum2[window_index, stage_index, 0],
                    cutflow_totals[(window, stage)],
                    f"day15 multiplicity {window}/{stage}",
                )
        multiplicity_rows = []
        for window_index, window in enumerate(WINDOW_FLAG_FIELDS):
            retained_multiplicities = [
                value
                for value in range(max_multiplicity + 1)
                if np.any(multiplicity_raw[window_index, :, 0, value] > 0)
            ]
            for stage_index, stage in enumerate(STAGES):
                for component_index, component in enumerate(COMPONENT_LABELS):
                    for multiplicity_value in retained_multiplicities:
                        sumw = float(
                            multiplicity_sum[
                                window_index,
                                stage_index,
                                component_index,
                                multiplicity_value,
                            ]
                        )
                        sumw2 = float(
                            multiplicity_sum2[
                                window_index,
                                stage_index,
                                component_index,
                                multiplicity_value,
                            ]
                        )
                        multiplicity_rows.append(
                            {
                                "time_bin_id": node,
                                "day_mid": float(self.days[node]),
                                "window_id": window,
                                "stage": stage,
                                "component": component,
                                "hit_multiplicity": multiplicity_value,
                                "selected_raw": int(
                                    multiplicity_raw[
                                        window_index,
                                        stage_index,
                                        component_index,
                                        multiplicity_value,
                                    ]
                                ),
                                "sumw_cps": sumw,
                                "sumw2_cps2": sumw2,
                                "sqrt_sumw2_cps": math.sqrt(sumw2),
                            }
                        )

        final_stats = self.direct_stats(node, FINAL_WINDOW, FINAL_STAGE)
        component_summary = {
            name: {
                **item,
                "transport_sigma_cps": math.sqrt(float(item["sum_wi2_cps2"])),
                "effective_sample_size": effective_sample_size(
                    float(item["rate_cps"]), float(item["sum_wi2_cps2"])
                ),
            }
            for name, item in final_stats["components"].items()
        }
        component_summary["total"] = {
            key: final_stats[key]
            for key in (
                "rate_cps",
                "sum_wi2_cps2",
                "transport_sigma_cps",
                "effective_sample_size",
                "selected_raw",
            )
        }
        product_schema = {
            "schema_version": DAY15_PRODUCT_SCHEMA_VERSION,
            "closure_status": "PASS__DAY15_PRODUCTS_ADDITIVE_CUTFLOW_CLOSED",
            "direct_cutflow_day15.csv": {
                "grain": "stream x family x component x window_id x stage",
                "windows": list(WINDOWS),
                "stages": list(STAGES),
            },
            "direct_measured_energy_day15_0p25keV.csv": {
                "grain": "stage x stream x component x 0.25-keV energy bin",
                "energy_range_keV": [480.0, 550.0],
                "energy_bin_width_keV": 0.25,
                "stages": list(spectrum_stages),
                "streams": list(STREAM_LABELS),
                "components": list(COMPONENT_LABELS),
                "rows": len(spectrum_rows),
            },
            "direct_hit_multiplicity_day15.csv": {
                "grain": "window_id x stage x component x retained hit_multiplicity",
                "windows": list(WINDOW_FLAG_FIELDS),
                "stages": list(STAGES),
                "components": list(COMPONENT_LABELS),
                "rows": len(multiplicity_rows),
            },
            "closure_checks": [
                "direct cutflow component rows=direct stats for selected_raw/sumw/sumw2",
                "spectrum prompt+delayed=all for selected_raw/sumw/sumw2",
                "spectrum named components=all for selected_raw/sumw/sumw2",
                "spectrum broad histogram totals=direct cutflow",
                "multiplicity named components=all for selected_raw/sumw/sumw2",
                "multiplicity broad/W2 histogram totals=direct cutflow",
            ],
        }
        return (
            cutflow_rows,
            spectrum_rows,
            multiplicity_rows,
            component_summary,
            product_schema,
        )

    def transport_from_coefficients(
        self,
        scalar_coefficients: np.ndarray,
        line_coefficients: dict[int, np.ndarray],
    ) -> dict[str, Any]:
        components = {
            name: {"counts": 0.0, "sum_W_i2_counts2": 0.0, "selected_raw": 0}
            for name in COMPONENT_NAMES
        }
        for category_id in range(self.n_categories):
            aggregate = self.selection_aggregates[
                (category_id, FINAL_WINDOW, FINAL_STAGE)
            ]
            if int(self.cat_components[category_id]) == COMPONENT_CODES["atm511"]:
                coefficients = line_coefficients[category_id]
                if aggregate.bin_sum_q is None or aggregate.bin_sum_q2 is None:
                    raise RuntimeError("internal line mission aggregate missing")
                counts = float(np.dot(aggregate.bin_sum_q, coefficients))
                variance = float(
                    np.dot(aggregate.bin_sum_q2, coefficients * coefficients)
                )
            else:
                coefficient = float(scalar_coefficients[category_id])
                counts = aggregate.sum_q * coefficient
                variance = aggregate.sum_q2 * coefficient * coefficient
            target = components[self.cat_component_names[category_id]]
            target["counts"] += counts
            target["sum_W_i2_counts2"] += variance
            target["selected_raw"] += aggregate.count
        total_counts = math.fsum(float(item["counts"]) for item in components.values())
        total_variance = math.fsum(
            float(item["sum_W_i2_counts2"]) for item in components.values()
        )
        return {
            "counts": total_counts,
            "sum_W_i2_counts2": total_variance,
            "sigma_counts": math.sqrt(total_variance),
            "effective_sample_size": effective_sample_size(
                total_counts, total_variance
            ),
            "selected_raw": sum(int(item["selected_raw"]) for item in components.values()),
            "components": components,
        }


def anchor_rows(
    replay: Replay, receipts: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rates: list[dict[str, Any]] = []
    components: list[dict[str, Any]] = []
    for receipt in receipts:
        node = int(receipt["time_bin_id"])
        timeline = receipt["timeline"]
        signal = receipt["signal_probe"]
        for window in WINDOWS:
            for stage in STAGES:
                key = f"{window}__{stage}"
                direct = receipt["direct"][key]
                count = int(timeline["counts"][key])
                timeline_rate = count / replay.exposure_s
                direct_rate = float(direct["rate_cps"])
                ratio: float | str = (
                    timeline_rate / direct_rate if direct_rate > 0.0 else ""
                )
                rates.append(
                    {
                        "time_bin_id": node,
                        "day_mid": float(receipt["day_mid"]),
                        "window_id": window,
                        "stage": stage,
                        "direct_no_coincidence_rate_cps": direct_rate,
                        "direct_sum_W_i2_cps2": float(direct["sum_wi2_cps2"]),
                        "direct_transport_sigma_cps": float(
                            direct["transport_sigma_cps"]
                        ),
                        "direct_transport_effective_sample_size": direct[
                            "effective_sample_size"
                        ],
                        "direct_selected_raw": int(direct["selected_raw"]),
                        "timeline_counts": count,
                        "timeline_rate_cps": timeline_rate,
                        "timeline_rate_standard_error_cps": math.sqrt(count)
                        / replay.exposure_s,
                        "timeline_to_direct_ratio": ratio,
                        "signal_accidental_survival": float(
                            signal["conditional_signal_accidental_survival"]
                        ),
                        "signal_survival_standard_error": float(
                            signal["binomial_standard_error"]
                        ),
                    }
                )
                for component in COMPONENT_NAMES:
                    item = direct["components"][component]
                    rate = float(item["rate_cps"])
                    variance = float(item["sum_wi2_cps2"])
                    components.append(
                        {
                            "time_bin_id": node,
                            "day_mid": float(receipt["day_mid"]),
                            "window_id": window,
                            "stage": stage,
                            "component": component,
                            "selected_raw": int(item["selected_raw"]),
                            "direct_rate_cps": rate,
                            "direct_sum_W_i2_cps2": variance,
                            "direct_transport_sigma_cps": math.sqrt(variance),
                            "direct_transport_effective_sample_size": effective_sample_size(
                                rate, variance
                            ),
                        }
                    )
    return rates, components


def build_mission(
    replay: Replay, receipts: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    receipt_by_node = {int(item["time_bin_id"]): item for item in receipts}
    ratios = np.asarray(
        [float(receipt_by_node[node]["final_timeline_to_direct_ratio"]) for node in ANCHOR_NODES],
        dtype=np.float64,
    )
    ratio_errors = np.asarray(
        [
            float(
                receipt_by_node[node][
                    "final_timeline_to_direct_ratio_standard_error"
                ]
            )
            for node in ANCHOR_NODES
        ],
        dtype=np.float64,
    )
    survivals = np.asarray(
        [
            float(
                receipt_by_node[node]["signal_probe"][
                    "conditional_signal_accidental_survival"
                ]
            )
            for node in ANCHOR_NODES
        ],
        dtype=np.float64,
    )
    survival_errors = np.asarray(
        [
            float(receipt_by_node[node]["signal_probe"]["binomial_standard_error"])
            for node in ANCHOR_NODES
        ],
        dtype=np.float64,
    )
    anchor_axis = np.asarray(ANCHOR_NODES, dtype=np.float64)
    node_axis = np.arange(81, dtype=np.float64)
    ratio_by_node = np.interp(node_axis, anchor_axis, ratios)
    survival_by_node = np.interp(node_axis, anchor_axis, survivals)
    slant = 1.0 / math.sin(
        math.radians(float(replay.authority.mission["source_elevation_deg"]))
    )
    transmission = np.asarray(
        [float(row["T_atm_511"]) ** slant for row in replay.atmosphere],
        dtype=np.float64,
    )
    aeff = float(replay.authority.signal["aeff_cm2"])
    kernel_by_node = aeff * transmission * survival_by_node
    direct_by_node = np.empty(81, dtype=np.float64)
    direct_variance_by_node = np.empty(81, dtype=np.float64)
    direct_components_by_node: list[dict[str, Any]] = []
    for node in range(81):
        direct = replay.direct_stats(node, FINAL_WINDOW, FINAL_STAGE)
        direct_by_node[node] = float(direct["rate_cps"])
        direct_variance_by_node[node] = float(direct["sum_wi2_cps2"])
        direct_components_by_node.append(direct["components"])

    scalar_coefficients = np.zeros(replay.n_categories, dtype=np.float64)
    line_coefficients = {
        category_id: np.zeros(80, dtype=np.float64)
        for category_id in range(replay.n_categories)
        if int(replay.cat_components[category_id]) == COMPONENT_CODES["atm511"]
    }
    cumulative_background = 0.0
    cumulative_kernel = 0.0
    mission_rows: list[dict[str, Any]] = []
    final_transport: dict[str, Any] | None = None
    for node in range(81):
        background_rate = direct_by_node[node] * ratio_by_node[node]
        if node > 0:
            dt = (replay.days[node] - replay.days[node - 1]) * SECONDS_PER_DAY
            previous_background = direct_by_node[node - 1] * ratio_by_node[node - 1]
            cumulative_background += 0.5 * (
                previous_background + background_rate
            ) * dt
            cumulative_kernel += 0.5 * (
                kernel_by_node[node - 1] + kernel_by_node[node]
            ) * dt
            for category_id in range(replay.n_categories):
                if int(replay.cat_components[category_id]) == COMPONENT_CODES["atm511"]:
                    line_coefficients[category_id] += 0.5 * (
                        replay.line_ratio[node - 1] * ratio_by_node[node - 1]
                        + replay.line_ratio[node] * ratio_by_node[node]
                    ) * dt
                else:
                    scalar_coefficients[category_id] += 0.5 * (
                        replay.common_factor[node - 1, category_id]
                        * ratio_by_node[node - 1]
                        + replay.common_factor[node, category_id] * ratio_by_node[node]
                    ) * dt
        transport = replay.transport_from_coefficients(
            scalar_coefficients, line_coefficients
        )
        final_transport = transport
        if not math.isclose(
            float(transport["counts"]),
            cumulative_background,
            rel_tol=3e-12,
            abs_tol=2e-6,
        ):
            raise RuntimeError(
                f"event-level mission weight closure differs at node {node}: "
                f"{transport['counts']} vs {cumulative_background}"
            )
        row: dict[str, Any] = {
            "time_bin_id": node,
            "day_mid": float(replay.days[node]),
            "direct_W2_final_no_coincidence_cps": float(direct_by_node[node]),
            "direct_sum_W_i2_cps2": float(direct_variance_by_node[node]),
            "direct_transport_sigma_cps": math.sqrt(
                float(direct_variance_by_node[node])
            ),
            "direct_transport_effective_sample_size": effective_sample_size(
                float(direct_by_node[node]), float(direct_variance_by_node[node])
            ),
            "interpolated_background_timeline_ratio": float(ratio_by_node[node]),
            "mature_background_W2_final_cps": float(background_rate),
            "mature_background_sum_W_i2_cps2": float(
                direct_variance_by_node[node] * ratio_by_node[node] ** 2
            ),
            "conditional_signal_accidental_survival": float(
                survival_by_node[node]
            ),
            "T_atm_511_slant45": float(transmission[node]),
            "conditional_signal_Aeff_cm2": aeff,
            "conditional_signal_kernel_cm2": float(kernel_by_node[node]),
            "cumulative_background_counts": cumulative_background,
            "cumulative_signal_counts_per_unit_flux": cumulative_kernel,
            "cumulative_transport_sum_W_i2_counts2": float(
                transport["sum_W_i2_counts2"]
            ),
            "cumulative_transport_sigma_counts": float(transport["sigma_counts"]),
            "cumulative_transport_effective_sample_size": transport[
                "effective_sample_size"
            ],
        }
        for component in COMPONENT_NAMES:
            instantaneous = direct_components_by_node[node][component]
            integrated = transport["components"][component]
            row[f"direct_{component}_cps"] = float(instantaneous["rate_cps"])
            row[f"direct_{component}_sum_W_i2_cps2"] = float(
                instantaneous["sum_wi2_cps2"]
            )
            row[f"cumulative_{component}_background_counts"] = float(
                integrated["counts"]
            )
            row[f"cumulative_{component}_sum_W_i2_counts2"] = float(
                integrated["sum_W_i2_counts2"]
            )
        row.update(fmin_values(cumulative_background, cumulative_kernel))
        mission_rows.append(row)
    if final_transport is None:
        raise RuntimeError("mission fold produced no nodes")

    component_rows = []
    for component in COMPONENT_NAMES:
        item = final_transport["components"][component]
        counts = float(item["counts"])
        variance = float(item["sum_W_i2_counts2"])
        component_rows.append(
            {
                "model": replay.model,
                "component": component,
                "mission_day": float(replay.days[-1]),
                "selected_raw": int(item["selected_raw"]),
                "integrated_background_counts": counts,
                "sum_W_i2_counts2": variance,
                "transport_sigma_counts": math.sqrt(variance),
                "transport_effective_sample_size": effective_sample_size(
                    counts, variance
                ),
            }
        )
    component_rows.append(
        {
            "model": replay.model,
            "component": "total",
            "mission_day": float(replay.days[-1]),
            "selected_raw": int(final_transport["selected_raw"]),
            "integrated_background_counts": float(final_transport["counts"]),
            "sum_W_i2_counts2": float(final_transport["sum_W_i2_counts2"]),
            "transport_sigma_counts": float(final_transport["sigma_counts"]),
            "transport_effective_sample_size": final_transport[
                "effective_sample_size"
            ],
        }
    )

    trapz = getattr(np, "trapezoid", None) or np.trapz
    ratio_coefficients = np.empty(len(ANCHOR_NODES), dtype=np.float64)
    survival_coefficients = np.empty(len(ANCHOR_NODES), dtype=np.float64)
    for index in range(len(ANCHOR_NODES)):
        basis = np.zeros(len(ANCHOR_NODES), dtype=np.float64)
        basis[index] = 1.0
        interpolated = np.interp(node_axis, anchor_axis, basis)
        ratio_coefficients[index] = (
            float(trapz(direct_by_node * interpolated, replay.days))
            * SECONDS_PER_DAY
        )
        survival_coefficients[index] = (
            float(trapz(aeff * transmission * interpolated, replay.days))
            * SECONDS_PER_DAY
        )
    timeline_sigma = float(
        np.sqrt(np.sum((ratio_coefficients * ratio_errors) ** 2))
    )
    signal_probe_sigma = float(
        np.sqrt(np.sum((survival_coefficients * survival_errors) ** 2))
    )
    transport_sigma = float(final_transport["sigma_counts"])
    background_sigma = math.hypot(transport_sigma, timeline_sigma)
    final_background = float(mission_rows[-1]["cumulative_background_counts"])
    final_kernel = float(mission_rows[-1]["cumulative_signal_counts_per_unit_flux"])
    background_relative = background_sigma / final_background
    aeff_sigma = float(replay.authority.signal["aeff_sigma_cm2"])
    aeff_relative = aeff_sigma / aeff
    probe_relative = signal_probe_sigma / final_kernel
    signal_relative = math.hypot(aeff_relative, probe_relative)
    fmins = fmin_values(final_background, final_kernel)
    fmin_errors: dict[str, Any] = {}
    for z in (3.0, 5.0):
        gaussian_key = f"Fmin_{int(z)}sigma_gaussian_ph_cm2_s"
        gaussian_value = float(fmins[gaussian_key])
        gaussian_relative = math.hypot(0.5 * background_relative, signal_relative)
        fmin_errors[gaussian_key] = {
            "value": gaussian_value,
            "standard_error": gaussian_value * gaussian_relative,
            "relative_standard_error": gaussian_relative,
        }
        asimov_key = f"Fmin_{int(z)}sigma_poisson_asimov_ph_cm2_s"
        asimov_value = float(fmins[asimov_key])
        required_signal = asimov_required_signal(final_background, z)
        logarithm = math.log1p(required_signal / final_background)
        derivative = (
            required_signal / final_background - logarithm
        ) / logarithm
        asimov_sigma = math.hypot(
            derivative * background_sigma / final_kernel,
            asimov_value * signal_relative,
        )
        fmin_errors[asimov_key] = {
            "value": asimov_value,
            "standard_error": asimov_sigma,
            "relative_standard_error": asimov_sigma / asimov_value,
        }
    uncertainty = {
        "background_transport_MC_sigma_counts": transport_sigma,
        "background_timeline_replay_sigma_counts": timeline_sigma,
        "background_combined_sigma_counts": background_sigma,
        "background_combined_relative_sigma": background_relative,
        "signal_Aeff_sigma_cm2": aeff_sigma,
        "signal_Aeff_relative_sigma": aeff_relative,
        "signal_accidental_probe_sigma_counts_per_unit_flux": signal_probe_sigma,
        "signal_accidental_probe_relative_sigma": probe_relative,
        "signal_combined_relative_sigma": signal_relative,
        "Fmin": fmin_errors,
        "model": (
            "event-level finite-template sum(W_i^2), independent anchor replay "
            "Poisson terms, signal-Aeff binomial term, and accidental-probe "
            "binomial terms; each transport template is fully correlated over "
            "the 81 mission nodes"
        ),
    }
    return mission_rows, component_rows, uncertainty


def input_check_report(replay: Replay) -> dict[str, Any]:
    anchors = {}
    for node in ANCHOR_NODES:
        final = replay.direct_stats(node, FINAL_WINDOW, FINAL_STAGE)
        anchors[str(node)] = {
            "day_mid": float(replay.days[node]),
            "total_detector_positive_rate_cps": float(
                np.sum(replay.category_rate_matrix[node])
            ),
            "direct_W2_final_cps": float(final["rate_cps"]),
            "direct_W2_final_sum_W_i2_cps2": float(final["sum_wi2_cps2"]),
        }
    return {
        "status": "PASS__FLUXCLOSED_TIMELINE_INPUTS_VALID",
        "model": replay.model,
        "candidate": replay.authority.candidate,
        "catalog": relative(replay.catalog_path),
        "events": int(len(replay.a["event_category"])),
        "hits": int(len(replay.a["hit_code"])),
        "categories": replay.n_categories,
        "component_event_counts": replay.fingerprint_payload[
            "component_event_counts"
        ],
        "source_importance_shape": list(replay.line_ratio.shape),
        "continuum_weight_contract": replay.fingerprint_payload[
            "continuum_weight_contract"
        ],
        "input_fingerprint_sha256": replay.fingerprint_sha256,
        "anchors": anchors,
        "signal_proxy": replay.authority.signal,
        "planned_outputs": list(FINAL_FILENAMES),
        "day15_product_schema_version": DAY15_PRODUCT_SCHEMA_VERSION,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the flux-closed five-anchor common-time timeline and 81-node "
            "mission fold for M05 mass model A (SG3B) or B (SH3 OptV3)."
        )
    )
    parser.add_argument("--model", choices=("a", "b"), required=True)
    parser.add_argument(
        "--catalog-dir",
        help=(
            "combined catalog directory, relative to repository ROOT unless "
            "absolute (default: package outputs/02_fluxclosed_catalog_MODEL)"
        ),
    )
    parser.add_argument(
        "--source-dir",
        help=(
            "source-closure directory, relative to repository ROOT unless "
            "absolute (default: package outputs/00_source_closure)"
        ),
    )
    parser.add_argument(
        "--output-dir",
        help=(
            "non-overwriting output directory, relative to repository ROOT "
            "unless absolute (default: package outputs/03_fluxclosed_timeline_MODEL)"
        ),
    )
    parser.add_argument(
        "--exposure-s",
        type=float,
        help="exposure per anchor (default: current mature model-specific value)",
    )
    parser.add_argument(
        "--signal-trials",
        type=int,
        help="accidental signal-proxy trials per anchor (default: mature value)",
    )
    parser.add_argument(
        "--chunk-events",
        type=int,
        help="bounded chronological-arrival chunk size (default: mature value)",
    )
    parser.add_argument(
        "--seed", type=int, help="base seed (default: current mature model-specific seed)"
    )
    parser.add_argument(
        "--fast-check",
        action="store_true",
        help=(
            "use 1000 s and 200,000 signal trials unless explicitly overridden; "
            "the default output gains a _fastcheck suffix"
        ),
    )
    parser.add_argument(
        "--check-inputs",
        action="store_true",
        help="validate all fixed schemas and authorities, print a report, and do not write",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    authority = model_authority(args.model)
    catalog_dir = (
        resolve_root(args.catalog_dir)
        if args.catalog_dir
        else PACKAGE / f"outputs/02_fluxclosed_catalog_{args.model}"
    )
    source_dir = (
        resolve_root(args.source_dir)
        if args.source_dir
        else PACKAGE / "outputs/00_source_closure"
    )
    default_output_name = f"03_fluxclosed_timeline_{args.model}"
    if args.fast_check:
        default_output_name += "_fastcheck"
    output_dir = (
        resolve_root(args.output_dir)
        if args.output_dir
        else PACKAGE / "outputs" / default_output_name
    )
    exposure_s = float(
        args.exposure_s
        if args.exposure_s is not None
        else (1000.0 if args.fast_check else authority.timeline["exposure_s_per_anchor"])
    )
    signal_trials = int(
        args.signal_trials
        if args.signal_trials is not None
        else (
            200_000
            if args.fast_check
            else authority.timeline["signal_probe_trials_per_anchor"]
        )
    )
    chunk_events = int(
        args.chunk_events
        if args.chunk_events is not None
        else authority.timeline["chunk_events"]
    )
    seed = int(args.seed if args.seed is not None else authority.timeline["seed"])
    if not math.isfinite(exposure_s) or exposure_s <= 0.0:
        raise RuntimeError("--exposure-s must be positive and finite")
    if signal_trials <= 0 or chunk_events <= 0:
        raise RuntimeError("--signal-trials and --chunk-events must be positive")
    if not args.check_inputs:
        existing = [output_dir / name for name in FINAL_FILENAMES if (output_dir / name).exists()]
        if existing:
            raise RuntimeError(
                "refusing to overwrite existing final outputs:\n  "
                + "\n  ".join(str(path) for path in existing)
            )

    replay = Replay(
        args.model,
        catalog_dir,
        source_dir,
        exposure_s,
        signal_trials,
        chunk_events,
        seed,
    )
    if args.check_inputs:
        print(json.dumps(input_check_report(replay), indent=2, sort_keys=True))
        return 0

    started = time.time()
    receipts: list[dict[str, Any]] = []
    for ordinal, node in enumerate(ANCHOR_NODES):
        receipt_path = output_dir / "receipts" / f"anchor_{node:03d}.json"
        receipt = replay.anchor_receipt(node, ordinal, receipt_path)
        receipts.append(receipt)
        final_count = int(
            receipt["timeline"]["counts"][f"{FINAL_WINDOW}__{FINAL_STAGE}"]
        )
        print(
            json.dumps(
                {
                    "model": args.model,
                    "time_bin_id": node,
                    "day_mid": receipt["day_mid"],
                    "event_instances": receipt["timeline"]["event_instances"],
                    "W2_final_counts": final_count,
                    "timeline_to_direct_ratio": receipt[
                        "final_timeline_to_direct_ratio"
                    ],
                    "signal_survival": receipt["signal_probe"][
                        "conditional_signal_accidental_survival"
                    ],
                    "receipt": relative(receipt_path),
                },
                sort_keys=True,
            ),
            flush=True,
        )

    rate_rows, anchor_component_rows = anchor_rows(replay, receipts)
    mission_rows, mission_component_rows, uncertainty = build_mission(
        replay, receipts
    )
    (
        cutflow_rows,
        spectrum_rows,
        multiplicity_rows,
        day15_components,
        day15_product_schema,
    ) = replay.day15_products()
    final = mission_rows[-1]
    summary = {
        "schema_version": 2,
        "status": "PASS__M05_FLUXCLOSED_COMMON_TIME_TIMELINE",
        "model": replay.model,
        "candidate": replay.authority.candidate,
        "input_fingerprint_sha256": replay.fingerprint_sha256,
        "input_fingerprint": replay.fingerprint_payload,
        "run_parameters": replay.fingerprint_payload["parameters"],
        "method": {
            "arrival_process": (
                "chronological exponential inter-arrivals at the exact summed "
                "event-level physical rate"
            ),
            "grouping": (
                "adjacent gaps <=1 microsecond form transitive groups; raw TES "
                "pixels, plastic, and BGO are combined before response/veto/Compton"
            ),
            "event_mark_law": (
                "event_base_weight_cps times component/node scale: ordinary "
                "categories are uniform only after constant-weight validation; "
                "continuum uses exact uniform-proposal rejection on "
                "event_base_weight_cps (the catalog has already folded in its "
                "audit-only continuum_importance_weight); mono511 chooses source_bin80 "
                "by summed proposal weight*importance_ratio then samples uniformly "
                "inside a validated constant-base bin"
            ),
            "continuum_scale": (
                "trajectory_component_scales_81nodes.csv "
                "gamma_continuum_scale_to_reference, verified node-by-node equal "
                "to scale_gamma_to_parma_reference"
            ),
            "mono511_scale": (
                "mono511_target_81x80.csv target/proposal importance_ratio for "
                "the event's source_bin80"
            ),
            "delayed_scale": (
                "exact isotope-resolved activity curve divided by its day15 "
                "activity, using the retained NUBASE-corrected activation manifest"
            ),
            "transport_uncertainty": (
                "true event-level sum(W_i^2); mission weights for each finite "
                "transport template are integrated before squaring"
            ),
        },
        "signal_proxy": replay.authority.signal,
        "day15_W2_final_component_rates": day15_components,
        "day15_product_schema": day15_product_schema,
        "anchors": {
            str(int(receipt["time_bin_id"])): {
                "receipt": relative(
                    output_dir
                    / "receipts"
                    / f"anchor_{int(receipt['time_bin_id']):03d}.json"
                ),
                "timeline_to_direct_ratio": receipt[
                    "final_timeline_to_direct_ratio"
                ],
                "timeline_to_direct_ratio_standard_error": receipt[
                    "final_timeline_to_direct_ratio_standard_error"
                ],
                "signal_probe": receipt["signal_probe"],
            }
            for receipt in receipts
        },
        "mission_final_20day": final,
        "mission_transport_components": {
            row["component"]: row for row in mission_component_rows
        },
        "statistical_uncertainty": uncertainty,
        "authority_boundary": {
            "background": (
                "single flux-closed continuum-plus-mono511 environment catalog; "
                "no scalar additive mono sidecar"
            ),
            "model_A_timeline": relative(A_CANDIDATE_TIMELINE_CODE),
            "model_A_signal": relative(A_SIGNAL_SUMMARY),
            "model_B_timeline": relative(B_TIMELINE_CODE),
            "model_B_signal": relative(B_TIMELINE_SUMMARY),
            "systematics_excluded": (
                "geometry, response-model, source-model, atmospheric, and "
                "cross-component transport systematics"
            ),
        },
        "outputs": list(FINAL_FILENAMES),
        "elapsed_s": time.time() - started,
    }
    write_csv_exclusive(output_dir / "anchor_timeline_rates.csv", rate_rows)
    write_csv_exclusive(
        output_dir / "anchor_transport_components.csv", anchor_component_rows
    )
    write_csv_exclusive(output_dir / "mission_timeline_81nodes.csv", mission_rows)
    write_csv_exclusive(
        output_dir / "mission_transport_components.csv", mission_component_rows
    )
    write_csv_exclusive(output_dir / "direct_cutflow_day15.csv", cutflow_rows)
    write_csv_exclusive(
        output_dir / "direct_measured_energy_day15_0p25keV.csv", spectrum_rows
    )
    write_csv_exclusive(
        output_dir / "direct_hit_multiplicity_day15.csv", multiplicity_rows
    )
    write_json_exclusive(output_dir / "summary.json", summary)
    print(
        json.dumps(
            {
                "status": summary["status"],
                "model": replay.model,
                "mission_final_20day": final,
                "output_dir": relative(output_dir),
            },
            indent=2,
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
