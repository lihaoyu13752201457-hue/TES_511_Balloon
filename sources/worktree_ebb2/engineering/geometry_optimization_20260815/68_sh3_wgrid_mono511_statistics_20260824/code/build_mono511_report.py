#!/usr/bin/env python3
"""Build an auditable SH3-open versus W-grid PARMA mono-511 report.

The script intentionally does not run transport and does not combine this
monoenergetic component with broadband or activation backgrounds.  It consumes
already-reviewed comparison/cut-flow/bin-80 files and emits one static,
two-panel comparison figure (PNG + PDF), a Chinese technical Markdown report,
and machine-readable audit tables/receipts.

Only the Python standard library, NumPy, and Matplotlib are required.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import datetime as dt
import hashlib
import io
import json
import math
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


# Keep Matplotlib from attempting to write under a read-only home directory.
_mpl_cache = Path(tempfile.gettempdir()) / "mplconfig_sh3_wgrid_mono511"
_mpl_cache.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_mpl_cache))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import font_manager  # noqa: E402


SCRIPT_VERSION = "1.0.0"

CANONICAL_ENERGY_KEV = 510.99895
CANONICAL_PARMA_FLUX = 0.16651547160226118
CANONICAL_EQUAL_MU_COMPONENTS = 80
MAX_EXPOSURE_RELATIVE_DIFFERENCE = 0.002
DEFAULT_WINDOW_ID = "w2_510p58_511p42"
DEFAULT_WINDOW_KEV = (510.58, 511.42)

STAGES: tuple[tuple[str, str], ...] = (
    ("pre_veto", "能窗内（主动 veto 前）"),
    ("plastic_positron_veto", "塑料/正电子 veto 后"),
    ("bgo_active_scintillator_veto", "BGO veto 后"),
    ("combined_active_veto", "联合主动 veto 后"),
    ("compton_trajectory_veto", "Compton 轨迹 veto 后"),
)

OPEN_TOKENS = {
    "open",
    "open_frame",
    "open-frame",
    "sh3",
    "sh3_open",
    "baseline",
    "reference",
}
GRID_TOKENS = {
    "grid",
    "wgrid",
    "w_grid",
    "w-grid",
    "network_collimator",
    "collimator",
}


class InputContractError(RuntimeError):
    """Raised when an input violates the paired-comparison contract."""


@dataclasses.dataclass(frozen=True)
class ModelMetrics:
    role: str
    label: str
    geometry_id: str
    incident_photons: int
    physical_exposure_s: float
    selected_events: int
    effective_selected_events: float
    rate_cps: float
    sigma_cps: float


@dataclasses.dataclass(frozen=True)
class CutflowRow:
    stage: str
    selected_events: int
    effective_selected_events: float
    rate_cps: float
    sigma_cps: float


@dataclasses.dataclass(frozen=True)
class BinRow:
    source_bin80: int
    selected_events: int
    rate_cps: float


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    _atomic_write_text(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def _atomic_write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> None:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    _atomic_write_text(path, buffer.getvalue())


def _norm_token(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "_")


def _first(mapping: Mapping[str, Any], names: Sequence[str], *, required: bool = True) -> Any:
    for name in names:
        if name in mapping and mapping[name] not in (None, ""):
            return mapping[name]
    if required:
        raise InputContractError(f"missing required field; accepted aliases: {', '.join(names)}")
    return None


def _as_float(value: Any, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise InputContractError(f"{field} must be numeric, got {value!r}") from exc
    if not math.isfinite(result):
        raise InputContractError(f"{field} must be finite, got {value!r}")
    return result


def _as_int(value: Any, field: str) -> int:
    numeric = _as_float(value, field)
    rounded = round(numeric)
    if not math.isclose(numeric, rounded, rel_tol=0.0, abs_tol=1e-9):
        raise InputContractError(f"{field} must be an integer, got {value!r}")
    return int(rounded)


def _as_bool(value: Any, field: str) -> bool:
    if isinstance(value, bool):
        return value
    token = _norm_token(value)
    if token in {"1", "true", "yes", "y", "pass"}:
        return True
    if token in {"0", "false", "no", "n", "fail"}:
        return False
    raise InputContractError(f"{field} must be boolean, got {value!r}")


def _merge_nested_model(value: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for nested_name in ("summary", "metrics", "final"):
        nested = value.get(nested_name)
        if isinstance(nested, Mapping):
            merged.update(nested)
    merged.update(value)
    return merged


def _model_from_mapping(role: str, value: Mapping[str, Any]) -> ModelMetrics:
    item = _merge_nested_model(value)
    default_label = "SH3 开放框" if role == "open_frame" else "SH3 + W-grid"
    label = str(_first(item, ("label", "display_label", "name"), required=False) or default_label)
    geometry_id = str(
        _first(item, ("geometry_id", "geometry", "geometry_setup", "geometry_sha256"), required=False)
        or "not_provided"
    )
    selected = _as_int(
        _first(item, ("selected_events", "final_selected_events", "w2_final_selected_events")),
        f"{role}.selected_events",
    )
    neff_value = _first(
        item,
        (
            "effective_selected_events",
            "final_effective_sample_size",
            "w2_final_effective_sample_size",
        ),
        required=False,
    )
    neff = float(selected) if neff_value is None else _as_float(neff_value, f"{role}.effective_selected_events")
    model = ModelMetrics(
        role=role,
        label=label,
        geometry_id=geometry_id,
        incident_photons=_as_int(
            _first(item, ("incident_photons", "n_incident", "events_generated")),
            f"{role}.incident_photons",
        ),
        physical_exposure_s=_as_float(
            _first(item, ("physical_exposure_s", "exposure_s", "observation_time_s")),
            f"{role}.physical_exposure_s",
        ),
        selected_events=selected,
        effective_selected_events=neff,
        rate_cps=_as_float(
            _first(item, ("rate_cps", "final_rate_cps", "w2_final_rate_cps")),
            f"{role}.rate_cps",
        ),
        sigma_cps=_as_float(
            _first(item, ("sigma_cps", "final_sigma_cps", "w2_final_mc_sigma_cps")),
            f"{role}.sigma_cps",
        ),
    )
    if model.incident_photons <= 0 or model.physical_exposure_s <= 0:
        raise InputContractError(f"{role}: incident photons and exposure must be positive")
    if model.selected_events < 0 or model.effective_selected_events < 0:
        raise InputContractError(f"{role}: selected counts and N_eff must be non-negative")
    if model.rate_cps < 0 or model.sigma_cps < 0:
        raise InputContractError(f"{role}: rate and sigma must be non-negative")
    return model


def _extract_json_models(payload: Mapping[str, Any]) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    direct_open = next((payload[key] for key in ("open_frame", "open", "sh3_open") if isinstance(payload.get(key), Mapping)), None)
    direct_grid = next((payload[key] for key in ("w_grid", "wgrid", "grid") if isinstance(payload.get(key), Mapping)), None)
    if direct_open is not None and direct_grid is not None:
        return direct_open, direct_grid

    models = payload.get("models")
    if isinstance(models, Sequence) and not isinstance(models, (str, bytes)):
        open_row: Mapping[str, Any] | None = None
        grid_row: Mapping[str, Any] | None = None
        for row in models:
            if not isinstance(row, Mapping):
                continue
            token = _norm_token(_first(row, ("role", "variant", "id", "model"), required=False) or "")
            if token in OPEN_TOKENS:
                open_row = row
            elif token in GRID_TOKENS:
                grid_row = row
        if open_row is not None and grid_row is not None:
            return open_row, grid_row
    raise InputContractError("comparison JSON must identify one open_frame and one w_grid model")


def _metadata_containers(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    result: list[Mapping[str, Any]] = []
    for key in ("metadata", "scope", "comparison_contract"):
        candidate = payload.get(key)
        if isinstance(candidate, Mapping):
            result.append(candidate)
    result.append(payload)
    return result


def _metadata_first(containers: Sequence[Mapping[str, Any]], names: Sequence[str]) -> Any:
    for container in containers:
        value = _first(container, names, required=False)
        if value not in (None, ""):
            return value
    return None


def _canonical_metadata(
    containers: Sequence[Mapping[str, Any]], *, allow_defaults: bool
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []

    def get(names: Sequence[str], default: Any, label: str) -> Any:
        value = _metadata_first(containers, names)
        if value is not None:
            return value
        if allow_defaults:
            warnings.append(f"{label} missing; canonical default inserted by explicit option")
            return default
        raise InputContractError(f"comparison metadata missing {label}; aliases: {', '.join(names)}")

    energy = _as_float(
        get(("line_energy_keV", "energy_keV", "mono_energy_keV"), CANONICAL_ENERGY_KEV, "line_energy_keV"),
        "line_energy_keV",
    )
    flux = _as_float(
        get(
            (
                "parma_day15_full_space_flux_ph_cm2_s",
                "parma_flux_ph_cm2_s",
                "line_flux_ph_cm2_s",
            ),
            CANONICAL_PARMA_FLUX,
            "PARMA day-15 full-space flux",
        ),
        "parma_day15_full_space_flux_ph_cm2_s",
    )
    n_mu = _as_int(
        get(("angular_components_equal_mu", "equal_mu_components", "n_mu_components"), CANONICAL_EQUAL_MU_COMPONENTS, "equal-mu component count"),
        "angular_components_equal_mu",
    )
    common_source = _as_bool(
        get(("common_parma_source", "same_parma_source"), True, "common_parma_source"),
        "common_parma_source",
    )
    common_chain = _as_bool(
        get(
            ("common_response_selection_time", "same_response_selection_time", "paired_analysis_contract"),
            True,
            "common_response_selection_time",
        ),
        "common_response_selection_time",
    )
    independent = _as_bool(
        get(("independent_mc_samples", "independent_samples"), True, "independent_mc_samples"),
        "independent_mc_samples",
    )
    data_status = str(get(("data_status",), "actual", "data_status")).strip().lower()
    if data_status not in {"actual", "synthetic"}:
        raise InputContractError("data_status must be 'actual' or 'synthetic'")

    window_id = str(_metadata_first(containers, ("window_id",)) or DEFAULT_WINDOW_ID)
    source_fragment_sha = _metadata_first(containers, ("source_fragment_sha256", "parma_fragment_sha256"))
    source_contract_sha = _metadata_first(containers, ("source_contract_sha256",))
    line_transport_contract_sha = _metadata_first(containers, ("line_transport_contract_sha256",))
    response_contract = _metadata_first(containers, ("response_selection_contract", "selection_contract"))

    return (
        {
            "data_status": data_status,
            "line_energy_keV": energy,
            "parma_day15_full_space_flux_ph_cm2_s": flux,
            "angular_components_equal_mu": n_mu,
            "common_parma_source": common_source,
            "common_response_selection_time": common_chain,
            "independent_mc_samples": independent,
            "window_id": window_id,
            "window_keV": list(DEFAULT_WINDOW_KEV),
            "source_fragment_sha256": source_fragment_sha,
            "source_contract_sha256": source_contract_sha,
            "line_transport_contract_sha256": line_transport_contract_sha,
            "response_selection_contract": response_contract,
        },
        warnings,
    )


def load_comparison(path: Path, *, allow_metadata_defaults: bool) -> tuple[dict[str, Any], ModelMetrics, ModelMetrics, list[str]]:
    if not path.is_file():
        raise InputContractError(f"comparison file not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise InputContractError("comparison JSON root must be an object")
        open_value, grid_value = _extract_json_models(payload)
        metadata, warnings = _canonical_metadata(
            _metadata_containers(payload), allow_defaults=allow_metadata_defaults
        )
        return metadata, _model_from_mapping("open_frame", open_value), _model_from_mapping("w_grid", grid_value), warnings

    if suffix == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            raise InputContractError("comparison CSV is empty")
        open_value: Mapping[str, Any] | None = None
        grid_value: Mapping[str, Any] | None = None
        for row in rows:
            token = _norm_token(_first(row, ("role", "variant", "id", "model"), required=False) or "")
            if token in OPEN_TOKENS:
                open_value = row
            elif token in GRID_TOKENS:
                grid_value = row
        if open_value is None or grid_value is None:
            raise InputContractError("comparison CSV requires role/variant rows for open_frame and w_grid")
        metadata, warnings = _canonical_metadata(rows, allow_defaults=allow_metadata_defaults)
        return metadata, _model_from_mapping("open_frame", open_value), _model_from_mapping("w_grid", grid_value), warnings

    raise InputContractError("comparison must be .json or .csv")


def load_cutflow(path: Path, *, window_id: str) -> list[CutflowRow]:
    if not path.is_file():
        raise InputContractError(f"cut-flow file not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_stage: dict[str, CutflowRow] = {}
    for row in rows:
        if "window_id" in row and row.get("window_id") != window_id:
            continue
        stage = str(_first(row, ("stage", "selection_stage")))
        if stage not in {name for name, _ in STAGES}:
            continue
        selected = _as_int(_first(row, ("selected_events", "events")), f"{path.name}:{stage}:selected_events")
        neff_value = _first(row, ("effective_selected_events", "n_eff"), required=False)
        neff = float(selected) if neff_value is None else _as_float(neff_value, f"{path.name}:{stage}:n_eff")
        parsed = CutflowRow(
            stage=stage,
            selected_events=selected,
            effective_selected_events=neff,
            rate_cps=_as_float(
                _first(row, ("weighted_rate_cps", "rate_cps")),
                f"{path.name}:{stage}:rate_cps",
            ),
            sigma_cps=_as_float(
                _first(row, ("weighted_mc_sigma_cps", "sigma_cps")),
                f"{path.name}:{stage}:sigma_cps",
            ),
        )
        if stage in by_stage:
            raise InputContractError(f"{path.name}: duplicate stage {stage!r} in window {window_id!r}")
        by_stage[stage] = parsed

    missing = [name for name, _ in STAGES if name not in by_stage]
    if missing:
        raise InputContractError(f"{path.name}: missing stages for {window_id}: {', '.join(missing)}")
    return [by_stage[name] for name, _ in STAGES]


def load_bins(path: Path) -> list[BinRow]:
    if not path.is_file():
        raise InputContractError(f"80-bin file not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    parsed: list[BinRow] = []
    seen: set[int] = set()
    for row in rows:
        bin_id = _as_int(_first(row, ("source_bin80", "bin80", "mu_bin")), f"{path.name}:source_bin80")
        if bin_id in seen:
            raise InputContractError(f"{path.name}: duplicate source_bin80={bin_id}")
        seen.add(bin_id)
        parsed.append(
            BinRow(
                source_bin80=bin_id,
                selected_events=_as_int(
                    _first(row, ("selected_events", "events")),
                    f"{path.name}:bin{bin_id}:selected_events",
                ),
                rate_cps=_as_float(
                    _first(row, ("weighted_rate_cps", "rate_cps")),
                    f"{path.name}:bin{bin_id}:rate_cps",
                ),
            )
        )
    expected = set(range(CANONICAL_EQUAL_MU_COMPONENTS))
    if seen != expected:
        missing = sorted(expected - seen)
        extra = sorted(seen - expected)
        raise InputContractError(f"{path.name}: bins must be exactly 0..79; missing={missing}, extra={extra}")
    return sorted(parsed, key=lambda row: row.source_bin80)


def _close(a: float, b: float, rtol: float) -> bool:
    return math.isclose(a, b, rel_tol=rtol, abs_tol=max(1e-14, rtol * 1e-6))


def validate_contract(
    metadata: Mapping[str, Any],
    open_model: ModelMetrics,
    grid_model: ModelMetrics,
    open_cutflow: Sequence[CutflowRow],
    grid_cutflow: Sequence[CutflowRow],
    open_bins: Sequence[BinRow],
    grid_bins: Sequence[BinRow],
    *,
    rtol: float,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "status": "PASS" if passed else "FAIL", "detail": detail})

    check(
        "canonical_line_energy",
        math.isclose(float(metadata["line_energy_keV"]), CANONICAL_ENERGY_KEV, rel_tol=0.0, abs_tol=1e-9),
        f"{metadata['line_energy_keV']} keV",
    )
    check(
        "canonical_parma_flux",
        math.isclose(float(metadata["parma_day15_full_space_flux_ph_cm2_s"]), CANONICAL_PARMA_FLUX, rel_tol=0.0, abs_tol=1e-14),
        f"{metadata['parma_day15_full_space_flux_ph_cm2_s']} ph cm^-2 s^-1",
    )
    check(
        "equal_mu_components",
        int(metadata["angular_components_equal_mu"]) == CANONICAL_EQUAL_MU_COMPONENTS,
        str(metadata["angular_components_equal_mu"]),
    )
    check("common_parma_source", bool(metadata["common_parma_source"]), str(metadata["common_parma_source"]))
    check(
        "common_response_selection_time",
        bool(metadata["common_response_selection_time"]),
        str(metadata["common_response_selection_time"]),
    )
    check(
        "independent_mc_samples",
        bool(metadata["independent_mc_samples"]),
        "required for the reported quadrature uncertainty",
    )
    check(
        "matched_incident_photons",
        open_model.incident_photons == grid_model.incident_photons,
        f"open={open_model.incident_photons}, grid={grid_model.incident_photons}",
    )
    check(
        "matched_source_exposure_realizations",
        abs(grid_model.physical_exposure_s / open_model.physical_exposure_s - 1.0)
        <= MAX_EXPOSURE_RELATIVE_DIFFERENCE,
        (
            f"open={open_model.physical_exposure_s:.12g} s, "
            f"grid={grid_model.physical_exposure_s:.12g} s; each independent run uses its own 1/sum(T)"
        ),
    )

    for role, model, cutflow, bins in (
        ("open", open_model, open_cutflow, open_bins),
        ("grid", grid_model, grid_cutflow, grid_bins),
    ):
        final = cutflow[-1]
        check(
            f"{role}_comparison_cutflow_rate",
            _close(model.rate_cps, final.rate_cps, rtol),
            f"comparison={model.rate_cps:.16g}, cutflow={final.rate_cps:.16g}",
        )
        check(
            f"{role}_comparison_cutflow_sigma",
            _close(model.sigma_cps, final.sigma_cps, rtol),
            f"comparison={model.sigma_cps:.16g}, cutflow={final.sigma_cps:.16g}",
        )
        check(
            f"{role}_comparison_cutflow_selected",
            model.selected_events == final.selected_events,
            f"comparison={model.selected_events}, cutflow={final.selected_events}",
        )
        bin_rate = math.fsum(row.rate_cps for row in bins)
        bin_selected = sum(row.selected_events for row in bins)
        check(
            f"{role}_bin80_rate_closure",
            _close(bin_rate, final.rate_cps, rtol),
            f"bin_sum={bin_rate:.16g}, final={final.rate_cps:.16g}",
        )
        check(
            f"{role}_bin80_count_closure",
            bin_selected == final.selected_events,
            f"bin_sum={bin_selected}, final={final.selected_events}",
        )
        monotone = all(cutflow[index + 1].selected_events <= cutflow[index].selected_events for index in range(len(cutflow) - 1))
        check(f"{role}_cutflow_monotone", monotone, "selected counts cannot increase after a cut")

    failures = [item for item in checks if item["status"] != "PASS"]
    if failures:
        details = "; ".join(f"{item['name']}: {item['detail']}" for item in failures)
        raise InputContractError(f"paired comparison contract failed: {details}")
    return checks


def _ratio_and_sigma(numerator: float, sigma_numerator: float, denominator: float, sigma_denominator: float) -> tuple[float, float]:
    if denominator <= 0:
        raise InputContractError("cannot compute grid/open ratio because open-frame rate is non-positive")
    ratio = numerator / denominator
    variance = (sigma_numerator / denominator) ** 2 + (
        numerator * sigma_denominator / (denominator**2)
    ) ** 2
    return ratio, math.sqrt(max(0.0, variance))


def derive_metrics(
    open_model: ModelMetrics,
    grid_model: ModelMetrics,
    open_cutflow: Sequence[CutflowRow],
    grid_cutflow: Sequence[CutflowRow],
    open_bins: Sequence[BinRow],
    grid_bins: Sequence[BinRow],
) -> dict[str, Any]:
    ratio, ratio_sigma = _ratio_and_sigma(
        grid_model.rate_cps,
        grid_model.sigma_cps,
        open_model.rate_cps,
        open_model.sigma_cps,
    )
    delta = grid_model.rate_cps - open_model.rate_cps
    delta_sigma = math.hypot(grid_model.sigma_cps, open_model.sigma_cps)
    delta_z = delta / delta_sigma if delta_sigma > 0 else None

    stage_rows: list[dict[str, Any]] = []
    stage_label = dict(STAGES)
    for open_row, grid_row in zip(open_cutflow, grid_cutflow):
        if open_row.stage != grid_row.stage:
            raise InputContractError("cut-flow stage ordering mismatch")
        stage_ratio, stage_sigma = _ratio_and_sigma(
            grid_row.rate_cps,
            grid_row.sigma_cps,
            open_row.rate_cps,
            open_row.sigma_cps,
        )
        stage_rows.append(
            {
                "stage": open_row.stage,
                "stage_label_zh": stage_label[open_row.stage],
                "open_selected_events": open_row.selected_events,
                "grid_selected_events": grid_row.selected_events,
                "open_rate_cps": open_row.rate_cps,
                "open_sigma_cps": open_row.sigma_cps,
                "grid_rate_cps": grid_row.rate_cps,
                "grid_sigma_cps": grid_row.sigma_cps,
                "grid_over_open_ratio": stage_ratio,
                "ratio_sigma": stage_sigma,
            }
        )

    open_rate_bins = np.asarray([row.rate_cps for row in open_bins], dtype=float)
    grid_rate_bins = np.asarray([row.rate_cps for row in grid_bins], dtype=float)
    open_shape = open_rate_bins / open_rate_bins.sum()
    grid_shape = grid_rate_bins / grid_rate_bins.sum()
    total_variation = 0.5 * float(np.abs(open_shape - grid_shape).sum())
    signed_diff = grid_rate_bins - open_rate_bins
    max_index = int(np.argmax(np.abs(signed_diff)))

    return {
        "final": {
            "grid_over_open_ratio": ratio,
            "ratio_sigma": ratio_sigma,
            "suppression_fraction": 1.0 - ratio,
            "suppression_sigma": ratio_sigma,
            "grid_minus_open_cps": delta,
            "difference_sigma_cps": delta_sigma,
            "difference_z_independent_mc": delta_z,
        },
        "stage_ratios": stage_rows,
        "bin80_diagnostic": {
            "open_occupied_bins": sum(row.selected_events > 0 for row in open_bins),
            "grid_occupied_bins": sum(row.selected_events > 0 for row in grid_bins),
            "normalized_shape_total_variation": total_variation,
            "largest_absolute_rate_difference_bin": max_index,
            "largest_signed_grid_minus_open_rate_cps": float(signed_diff[max_index]),
            "interpretation": "descriptive only; sparse selected counts make binwise inference underpowered",
        },
    }


def _select_cjk_font() -> str:
    preferred = (
        "Noto Sans CJK SC",
        "Noto Sans CJK JP",
        "AR PL UMing CN",
        "AR PL SungtiL GB",
        "Droid Sans Fallback",
        "DejaVu Sans",
    )
    available = {item.name for item in font_manager.fontManager.ttflist}
    for name in preferred:
        if name in available:
            return name
    return "DejaVu Sans"


def render_figure(
    png_path: Path,
    pdf_path: Path,
    metadata: Mapping[str, Any],
    open_model: ModelMetrics,
    grid_model: ModelMetrics,
    derived: Mapping[str, Any],
) -> str:
    font_name = _select_cjk_font()
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [font_name, "DejaVu Sans"],
            "axes.unicode_minus": False,
            # Type 3 avoids a fontTools 4.x subsetting failure on multi-face
            # Noto CJK TTC collections in the older Matplotlib 3.5 runtime.
            "pdf.fonttype": 3,
            "ps.fonttype": 42,
            "font.size": 10.5,
            "axes.titlesize": 12.0,
            "axes.labelsize": 10.5,
            "xtick.labelsize": 9.4,
            "ytick.labelsize": 9.4,
        }
    )

    blue = "#2D6FA3"
    gold = "#C28A1A"
    ink = "#25313C"
    grey = "#D8DEE5"
    mid_grey = "#68737D"

    fig = plt.figure(figsize=(13.2, 7.4), facecolor="white")
    grid_spec = fig.add_gridspec(1, 2, width_ratios=(0.90, 1.45), wspace=0.38)
    ax_rate = fig.add_subplot(grid_spec[0, 0])
    ax_ratio = fig.add_subplot(grid_spec[0, 1])

    rate_y = np.asarray([1.0, 0.0])
    rates = np.asarray([open_model.rate_cps, grid_model.rate_cps])
    sigmas = np.asarray([open_model.sigma_cps, grid_model.sigma_cps])
    ax_rate.errorbar(
        rates[0],
        rate_y[0],
        xerr=sigmas[0],
        fmt="o",
        ms=9,
        mfc="white",
        mec=blue,
        mew=2,
        ecolor=blue,
        elinewidth=1.8,
        capsize=4,
        zorder=3,
    )
    ax_rate.errorbar(
        rates[1],
        rate_y[1],
        xerr=sigmas[1],
        fmt="s",
        ms=8,
        mfc=gold,
        mec="#76540F",
        mew=1.1,
        ecolor=gold,
        elinewidth=1.8,
        capsize=4,
        zorder=3,
    )
    xmax = max(float((rates + sigmas).max()) * 1.58, 0.001)
    ax_rate.set_xlim(0.0, xmax)
    ax_rate.set_ylim(-0.65, 1.65)
    ax_rate.set_yticks(rate_y, [open_model.label, grid_model.label])
    ax_rate.set_xlabel("最终选后线率（cps）")
    ax_rate.set_title("a   最终线率及 1σ MC 不确定度", loc="left", color=ink, pad=13)
    for y, rate, sigma, selected in zip(
        rate_y,
        rates,
        sigmas,
        (open_model.selected_events, grid_model.selected_events),
    ):
        ax_rate.text(
            rate + sigma + xmax * 0.025,
            y,
            f"{rate:.5f} ± {sigma:.5f}\nNsel={selected}",
            va="center",
            ha="left",
            color=ink,
            fontsize=9.1,
        )
    ax_rate.grid(axis="x", color=grey, linewidth=0.8, alpha=0.75)
    ax_rate.set_axisbelow(True)

    stage_rows = list(derived["stage_ratios"])
    ratio_y = np.arange(len(stage_rows))[::-1]
    ratio_values = np.asarray([row["grid_over_open_ratio"] for row in stage_rows], dtype=float)
    ratio_sigmas = np.asarray([row["ratio_sigma"] for row in stage_rows], dtype=float)
    ax_ratio.axvline(1.0, color=mid_grey, linewidth=1.25, linestyle=(0, (4, 3)), zorder=1)
    ax_ratio.errorbar(
        ratio_values,
        ratio_y,
        xerr=ratio_sigmas,
        fmt="s",
        ms=6.8,
        mfc=gold,
        mec="#76540F",
        mew=1.0,
        ecolor=gold,
        elinewidth=1.7,
        capsize=3.5,
        zorder=3,
    )
    ratio_xmax = max(1.18, float((ratio_values + ratio_sigmas).max()) * 1.26)
    ax_ratio.set_xlim(0.0, ratio_xmax)
    ax_ratio.set_ylim(-0.7, len(stage_rows) - 0.3)
    ax_ratio.set_yticks(ratio_y, [row["stage_label_zh"] for row in stage_rows])
    ax_ratio.set_xlabel("线率比（W-grid / 开放框）")
    ax_ratio.set_title("b   各选择阶段的配对线率比", loc="left", color=ink, pad=13)
    ax_ratio.grid(axis="x", color=grey, linewidth=0.8, alpha=0.75)
    ax_ratio.set_axisbelow(True)
    for y, ratio, sigma in zip(ratio_y, ratio_values, ratio_sigmas):
        ax_ratio.text(
            min(ratio + sigma + ratio_xmax * 0.018, ratio_xmax * 0.94),
            y,
            f"{ratio:.3f} ± {sigma:.3f}",
            va="center",
            ha="left",
            color=ink,
            fontsize=8.9,
        )
    ax_ratio.text(
        1.0,
        len(stage_rows) - 0.32,
        "无变化",
        color=mid_grey,
        ha="center",
        va="bottom",
        fontsize=8.6,
    )

    for axis in (ax_rate, ax_ratio):
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
        axis.spines["left"].set_color("#A7B0B9")
        axis.spines["bottom"].set_color("#A7B0B9")
        axis.tick_params(colors=ink)

    fig.suptitle(
        "PARMA 单能 511 keV 响应比较",
        x=0.065,
        y=0.978,
        ha="left",
        va="top",
        fontsize=18,
        color=ink,
        fontweight="semibold",
    )
    fig.text(
        0.065,
        0.925,
        (
            f"{metadata['line_energy_keV']:.5f} keV；day-15 PARMA 全空间通量 "
            f"{metadata['parma_day15_full_space_flux_ph_cm2_s']:.15g} ph cm^-2 s^-1；"
            "80 个等 μ 分量；同一响应、选择与时间归一"
        ),
        ha="left",
        va="top",
        fontsize=10.0,
        color=mid_grey,
    )
    fig.text(
        0.065,
        0.030,
        "误差条均为独立蒙特卡洛样本的 1σ 统计误差。本图仅比较单能线响应，不代表宽带总本底或 Fmin。",
        ha="left",
        va="bottom",
        fontsize=9.1,
        color=mid_grey,
    )
    if metadata["data_status"] == "synthetic":
        fig.text(
            0.5,
            0.53,
            "SYNTHETIC FIXTURE · 非物理结果",
            ha="center",
            va="center",
            rotation=18,
            fontsize=25,
            color="#7C8791",
            alpha=0.18,
            fontweight="bold",
        )

    fig.subplots_adjust(left=0.13, right=0.975, bottom=0.14, top=0.82)
    png_tmp = png_path.with_name(png_path.name + ".tmp")
    pdf_tmp = pdf_path.with_name(pdf_path.name + ".tmp")
    fig.savefig(png_tmp, format="png", dpi=190, facecolor="white", bbox_inches="tight")
    fig.savefig(pdf_tmp, format="pdf", facecolor="white", bbox_inches="tight")
    plt.close(fig)
    os.replace(png_tmp, png_path)
    os.replace(pdf_tmp, pdf_path)
    return font_name


def _fmt_rate(value: float) -> str:
    return f"{value:.9f}"


def _fmt_pct(value: float) -> str:
    return f"{100.0 * value:.1f}%"


def build_report_markdown(
    figure_name: str,
    metadata: Mapping[str, Any],
    open_model: ModelMetrics,
    grid_model: ModelMetrics,
    derived: Mapping[str, Any],
    warnings: Sequence[str],
) -> str:
    final = derived["final"]
    ratio = final["grid_over_open_ratio"]
    ratio_sigma = final["ratio_sigma"]
    suppression = final["suppression_fraction"]
    z_value = final["difference_z_independent_mc"]
    status_line = "**这是合成自测数据，不是物理结论。**\n\n" if metadata["data_status"] == "synthetic" else ""
    source_hash_bits = []
    for label, key in (
        ("PARMA 线源片段", "source_fragment_sha256"),
        ("源归一合同", "source_contract_sha256"),
        ("线输运合同", "line_transport_contract_sha256"),
    ):
        if metadata.get(key):
            source_hash_bits.append(f"- {label} SHA-256：`{metadata[key]}`")
    hash_text = "\n".join(source_hash_bits) if source_hash_bits else "- 输入未提供可显示的源合同哈希；文件级哈希保存在 `qa_receipt.json`。"

    warning_text = ""
    if warnings:
        warning_text = "\n".join(f"- {item}" for item in warnings)
    else:
        warning_text = "- 未使用元数据默认值；比较口径由输入文件显式给出。"

    stage_lines = []
    for row in derived["stage_ratios"]:
        stage_lines.append(
            "| {label} | {orate:.9f} ± {osig:.9f} | {grate:.9f} ± {gsig:.9f} | {ratio:.3f} ± {rsig:.3f} | {on:d} / {gn:d} |".format(
                label=row["stage_label_zh"],
                orate=row["open_rate_cps"],
                osig=row["open_sigma_cps"],
                grate=row["grid_rate_cps"],
                gsig=row["grid_sigma_cps"],
                ratio=row["grid_over_open_ratio"],
                rsig=row["ratio_sigma"],
                on=row["open_selected_events"],
                gn=row["grid_selected_events"],
            )
        )
    stage_table = "\n".join(stage_lines)

    bin_diag = derived["bin80_diagnostic"]
    return f"""# SH3 开放框与 W-grid 的 PARMA 单能 511 keV 响应比较

{status_line}## 技术摘要

在完全匹配的 PARMA 单能线源、响应、选择和时间归一口径下，W-grid 的最终选后线率为 **{_fmt_rate(grid_model.rate_cps)} ± {_fmt_rate(grid_model.sigma_cps)} cps**，开放框为 **{_fmt_rate(open_model.rate_cps)} ± {_fmt_rate(open_model.sigma_cps)} cps**。二者比值为 **{ratio:.4f} ± {ratio_sigma:.4f}**；等价的线响应降低比例为 **{_fmt_pct(suppression)} ± {_fmt_pct(ratio_sigma)}**。独立 MC 统计误差下，差值为 {final['grid_minus_open_cps']:.9f} ± {final['difference_sigma_cps']:.9f} cps（{z_value:.2f}σ）。

这一定量结论只描述 510.99895 keV 的 PARMA 大气湮没线响应。它**不是**宽带总本底、累计本底或 Fmin 的更新结果，也不能直接替代后续的通量守恒合成。

## 关键结果由最终线率和逐阶段比率共同支持

下图左侧给出两个几何的最终选后线率及 1σ MC 误差；右侧给出每个共同选择阶段的 W-grid/开放框线率比。比率在某一阶段开始明显偏离 1，可用于定位几何效应进入响应链的位置；它本身不证明因果机制。

![PARMA 单能 511 keV 响应比较](./{figure_name})

| 共同选择阶段 | 开放框线率（cps） | W-grid 线率（cps） | W-grid/开放框 | 选后数（开放/网格） |
|---|---:|---:|---:|---:|
{stage_table}

最终选后样本数为开放框 {open_model.selected_events}、W-grid {grid_model.selected_events}；对应有效样本量分别为 {open_model.effective_selected_events:.3f} 和 {grid_model.effective_selected_events:.3f}。这些数值决定了当前线率误差的统计下限。

## 比较口径、数据范围与指标定义

- 线能量：{metadata['line_energy_keV']:.5f} keV。
- day-15 PARMA 全空间积分通量：{metadata['parma_day15_full_space_flux_ph_cm2_s']:.17g} ph cm⁻² s⁻¹。
- 角分布：{metadata['angular_components_equal_mu']} 个等 μ 分量；归一和角分布均来自同一大气状态下的 PARMA 专用线参数化。
- 入射光子数：两个几何均为 {open_model.incident_photons:,}。
- Cosima 物理曝光：开放框 {open_model.physical_exposure_s:.8f} s，W-grid {grid_model.physical_exposure_s:.8f} s。二者来自相同 PARMA 通量与源球，但属于独立随机时间实现；各自按自己的 `1/sum(T)` 归一。
- 最终能窗：[{DEFAULT_WINDOW_KEV[0]:.2f}, {DEFAULT_WINDOW_KEV[1]:.2f}) keV。
- 线率定义：所有通过选择的事件按共同事件权重求和；1σ MC 误差按 `sqrt(sum(w_i^2))` 计算。
- 有效样本量定义：`N_eff = (sum(w_i))^2 / sum(w_i^2)`。
- 比率误差：开放框和 W-grid 使用独立随机样本，按一阶误差传播合并两侧 MC 方差。

## 方法与数值闭合检查

本报告直接读取两个几何的最终比较摘要、共同能窗的五级 cut-flow，以及各自 80 个等 μ 源分量的最终选后贡献。生成器在绘图前强制检查：PARMA 能量与通量常数、80 分量完整性、共同源/响应/选择/时间定义、相同入射数、独立曝光的相容性、cut-flow 单调性、比较摘要与最终 cut-flow 一致性、以及 80 分量对最终线率和选后数的求和闭合。任一检查失败即停止，不生成报告。

80 分量的选后占据数为开放框 {bin_diag['open_occupied_bins']} 个、W-grid {bin_diag['grid_occupied_bins']} 个。两者归一化角分布的描述性总变差距离为 {bin_diag['normalized_shape_total_variation']:.3f}；最大绝对线率差位于分量 {bin_diag['largest_absolute_rate_difference_bin']}。由于单分量计数稀疏，该角分布量只作闭合诊断，不能单独用于显著性结论。

源与输运合同审计信息：

{hash_text}

生成时的元数据处理：

{warning_text}

## 限制、不确定度与稳健性边界

- 当前误差只含独立 MC 统计误差，不含 PARMA 参数化、质量模型、材料、几何装配、能量响应或选择阈值的系统误差。
- 80 分量诊断存在稀疏计数，不能把单个 μ 分量的起伏解释为稳定的角响应结构。
- 本报告没有执行宽带粗能箱线面积扣除、单能线回加、五时间锚点折叠、占空率、累计本底、Gaussian/Asimov 显著度或 Fmin 计算。
- 因而，本报告可以回答“仅增加 W-grid 后，PARMA 单能 511 keV 选后响应改变多少”，但不能回答“完整任务灵敏度改善多少”。

## 建议的下一步由当前有效样本量决定

1. 先用 W-grid 的最终 `N_eff` 和相对 MC 误差判断当前精度是否满足论文报告位数；只有不足时才补最小增量统计。
2. 若精度足够，再按通量守恒形式把该线响应并入完整本底：宽带总量减去同一粗能箱内已含的线面积，再加匹配的单能线响应。
3. 完整本底闭合前，不从本报告外推总本底或 Fmin。

## 仍需回答的问题

- 当前 W-grid 最终 `N_eff` 是否足以支持预定的小数位和误差报告？
- 80 个等 μ 分量中的差异在增量统计后是否仍保持同一角向结构？
- 在通量守恒合成并折叠共同任务时间轴后，线项变化对总本底与 Fmin 的净影响是多少？
"""


def _write_stage_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    fields = (
        "stage",
        "stage_label_zh",
        "open_selected_events",
        "grid_selected_events",
        "open_rate_cps",
        "open_sigma_cps",
        "grid_rate_cps",
        "grid_sigma_cps",
        "grid_over_open_ratio",
        "ratio_sigma",
    )
    _atomic_write_csv(path, fields, rows)


def _allocate_counts(total: int, weights: np.ndarray) -> np.ndarray:
    scaled = total * weights / weights.sum()
    counts = np.floor(scaled).astype(int)
    remainder = total - int(counts.sum())
    if remainder:
        order = np.argsort(-(scaled - counts))
        counts[order[:remainder]] += 1
    return counts


def make_synthetic_fixture(directory: Path) -> dict[str, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    targets = {
        "comparison": directory / "comparison.synthetic.json",
        "open_cutflow": directory / "open_cutflow.synthetic.csv",
        "grid_cutflow": directory / "grid_cutflow.synthetic.csv",
        "open_bins": directory / "open_bin80.synthetic.csv",
        "grid_bins": directory / "grid_bin80.synthetic.csv",
    }
    existing = [str(path) for path in targets.values() if path.exists()]
    if existing:
        raise InputContractError("synthetic fixture refuses to overwrite existing files: " + ", ".join(existing))

    common_weight = 0.00011985193855860365
    open_counts = [196, 196, 196, 196, 186]
    grid_counts = [82, 82, 80, 80, 72]

    def cut_rows(model: str, counts: Sequence[int]) -> list[dict[str, Any]]:
        rows = []
        for (stage, _), count in zip(STAGES, counts):
            rows.append(
                {
                    "model": model,
                    "window_id": DEFAULT_WINDOW_ID,
                    "stage": stage,
                    "selected_events": count,
                    "event_weight_cps": common_weight,
                    "weighted_rate_cps": count * common_weight,
                    "weighted_mc_sigma_cps": math.sqrt(count) * common_weight,
                    "effective_selected_events": count,
                }
            )
        return rows

    cut_fields = (
        "model",
        "window_id",
        "stage",
        "selected_events",
        "event_weight_cps",
        "weighted_rate_cps",
        "weighted_mc_sigma_cps",
        "effective_selected_events",
    )
    _atomic_write_csv(targets["open_cutflow"], cut_fields, cut_rows("open", open_counts))
    _atomic_write_csv(targets["grid_cutflow"], cut_fields, cut_rows("wgrid", grid_counts))

    centers = (np.arange(80, dtype=float) + 0.5) / 80.0
    open_bin_counts = _allocate_counts(open_counts[-1], 0.20 + np.sin(np.pi * centers) ** 1.4)
    grid_bin_counts = _allocate_counts(grid_counts[-1], 0.08 + np.sin(np.pi * centers) ** 3.0)
    bin_fields = ("source_bin80", "selected_events", "weighted_rate_cps")
    _atomic_write_csv(
        targets["open_bins"],
        bin_fields,
        (
            {
                "source_bin80": index,
                "selected_events": int(count),
                "weighted_rate_cps": float(count) * common_weight,
            }
            for index, count in enumerate(open_bin_counts)
        ),
    )
    _atomic_write_csv(
        targets["grid_bins"],
        bin_fields,
        (
            {
                "source_bin80": index,
                "selected_events": int(count),
                "weighted_rate_cps": float(count) * common_weight,
            }
            for index, count in enumerate(grid_bin_counts)
        ),
    )

    exposure = 8343.62808
    incident = 15_709_417
    comparison = {
        "schema_version": 1,
        "metadata": {
            "data_status": "synthetic",
            "comparison_scope": "PARMA monoenergetic atmospheric 511-keV line only",
            "line_energy_keV": CANONICAL_ENERGY_KEV,
            "parma_day15_full_space_flux_ph_cm2_s": CANONICAL_PARMA_FLUX,
            "angular_components_equal_mu": CANONICAL_EQUAL_MU_COMPONENTS,
            "common_parma_source": True,
            "common_response_selection_time": True,
            "independent_mc_samples": True,
            "window_id": DEFAULT_WINDOW_ID,
            "source_fragment_sha256": "synthetic_fixture_not_an_authority",
            "source_contract_sha256": "synthetic_fixture_not_an_authority",
            "line_transport_contract_sha256": "synthetic_fixture_not_an_authority",
            "response_selection_contract": {
                "energy_resolution_fwhm_keV": 0.420,
                "post_noise_pixel_threshold_keV": 0.3,
                "bgo_veto_threshold_keV": 50.0,
                "final_window_keV": list(DEFAULT_WINDOW_KEV),
            },
        },
        "open_frame": {
            "label": "SH3 开放框",
            "geometry_id": "synthetic_open_geometry",
            "incident_photons": incident,
            "physical_exposure_s": exposure,
            "selected_events": open_counts[-1],
            "effective_selected_events": open_counts[-1],
            "rate_cps": open_counts[-1] * common_weight,
            "sigma_cps": math.sqrt(open_counts[-1]) * common_weight,
        },
        "w_grid": {
            "label": "SH3 + W-grid",
            "geometry_id": "synthetic_grid_geometry",
            "incident_photons": incident,
            "physical_exposure_s": exposure,
            "selected_events": grid_counts[-1],
            "effective_selected_events": grid_counts[-1],
            "rate_cps": grid_counts[-1] * common_weight,
            "sigma_cps": math.sqrt(grid_counts[-1]) * common_weight,
        },
    }
    _atomic_write_json(targets["comparison"], comparison)
    return targets


def build(args: argparse.Namespace) -> dict[str, Path]:
    comparison_path = Path(args.comparison).resolve()
    open_cutflow_path = Path(args.open_cutflow).resolve()
    grid_cutflow_path = Path(args.grid_cutflow).resolve()
    open_bins_path = Path(args.open_bins).resolve()
    grid_bins_path = Path(args.grid_bins).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if Path(args.figure_stem).name != args.figure_stem:
        raise InputContractError("--figure-stem must be a filename stem, not a path")
    outputs = {
        "png": output_dir / f"{args.figure_stem}.png",
        "pdf": output_dir / f"{args.figure_stem}.pdf",
        "report": output_dir / "mono511_technical_report_zh.md",
        "data": output_dir / "mono511_report_data.json",
        "stage_csv": output_dir / "mono511_stage_ratios.csv",
        "qa": output_dir / "qa_receipt.json",
    }
    existing = [str(path) for path in outputs.values() if path.exists()]
    if existing:
        raise InputContractError("refusing to overwrite generated outputs: " + ", ".join(existing))

    metadata, open_model, grid_model, warnings = load_comparison(
        comparison_path,
        allow_metadata_defaults=args.allow_metadata_defaults,
    )
    if args.window_id:
        if metadata["window_id"] != args.window_id:
            raise InputContractError(
                f"window mismatch: comparison metadata={metadata['window_id']!r}, CLI={args.window_id!r}"
            )
        window_id = args.window_id
    else:
        window_id = str(metadata["window_id"])

    open_cutflow = load_cutflow(open_cutflow_path, window_id=window_id)
    grid_cutflow = load_cutflow(grid_cutflow_path, window_id=window_id)
    open_bins = load_bins(open_bins_path)
    grid_bins = load_bins(grid_bins_path)
    checks = validate_contract(
        metadata,
        open_model,
        grid_model,
        open_cutflow,
        grid_cutflow,
        open_bins,
        grid_bins,
        rtol=args.consistency_rtol,
    )
    derived = derive_metrics(open_model, grid_model, open_cutflow, grid_cutflow, open_bins, grid_bins)

    report_data = {
        "schema_version": 1,
        "script_version": SCRIPT_VERSION,
        "scope": "PARMA monoenergetic atmospheric 511-keV line response only",
        "metadata": metadata,
        "open_frame": dataclasses.asdict(open_model),
        "w_grid": dataclasses.asdict(grid_model),
        "derived": derived,
        "contract_checks": checks,
        "warnings": warnings,
    }
    _atomic_write_json(outputs["data"], report_data)
    _write_stage_csv(outputs["stage_csv"], derived["stage_ratios"])
    font_name = render_figure(outputs["png"], outputs["pdf"], metadata, open_model, grid_model, derived)
    report_text = build_report_markdown(
        outputs["png"].name,
        metadata,
        open_model,
        grid_model,
        derived,
        warnings,
    )
    _atomic_write_text(outputs["report"], report_text)

    image = plt.imread(outputs["png"])
    pdf_header = outputs["pdf"].read_bytes()[:5]
    if image.ndim not in (2, 3) or min(image.shape[:2]) < 500:
        raise InputContractError(f"rendered PNG failed dimension QA: {image.shape}")
    if pdf_header != b"%PDF-":
        raise InputContractError("rendered PDF failed header QA")

    source_paths = {
        "comparison": comparison_path,
        "open_cutflow": open_cutflow_path,
        "grid_cutflow": grid_cutflow_path,
        "open_bin80": open_bins_path,
        "grid_bin80": grid_bins_path,
    }
    receipt = {
        "status": "PASS__MONO511_STATIC_REPORT",
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "script_version": SCRIPT_VERSION,
        "script_sha256": _sha256(Path(__file__).resolve()),
        "data_status": metadata["data_status"],
        "scope_guard": {
            "mono511_only": True,
            "broadband_total_updated": False,
            "activation_updated": False,
            "fmin_updated": False,
        },
        "input_files": {
            key: {"path": str(path), "sha256": _sha256(path), "bytes": path.stat().st_size}
            for key, path in source_paths.items()
        },
        "contract_checks": checks,
        "warnings": warnings,
        "chart_contract": {
            "analytical_question": "How does adding only the W-grid change the matched PARMA mono-511 selected response relative to open SH3?",
            "family": "Uncertainty & Benchmark",
            "variant": "two-panel dot-and-interval plus ordered stage-ratio intervals",
            "renderer": "Matplotlib static PNG/PDF",
            "palette_policy": "hard two-root cap: blue=open, gold=W-grid; marker fill also distinguishes variants",
            "bin80_policy": "used for numerical closure and sparse angular diagnostic, not promoted to a main chart",
        },
        "render_qa": {
            "font": font_name,
            "png_shape": list(image.shape),
            "pdf_magic": pdf_header.decode("ascii"),
            "matplotlib_version": matplotlib.__version__,
            "numpy_version": np.__version__,
        },
        "outputs": {
            key: {"path": str(path), "sha256": _sha256(path), "bytes": path.stat().st_size}
            for key, path in outputs.items()
            if key != "qa"
        },
    }
    _atomic_write_json(outputs["qa"], receipt)
    return outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a strict, line-only SH3 open/W-grid PARMA mono-511 comparison report."
    )
    parser.add_argument("--comparison", help="comparison.json or comparison.csv")
    parser.add_argument("--open-cutflow", help="open-frame cut-flow CSV")
    parser.add_argument("--grid-cutflow", help="W-grid cut-flow CSV")
    parser.add_argument("--open-bins", help="open-frame 80-bin final contribution CSV")
    parser.add_argument("--grid-bins", help="W-grid 80-bin final contribution CSV")
    parser.add_argument("--output-dir", help="new/non-overwriting report output directory")
    parser.add_argument(
        "--make-synthetic-fixture",
        metavar="DIR",
        help="create a clearly marked synthetic fixture there; missing input arguments are filled from it",
    )
    parser.add_argument("--window-id", default=DEFAULT_WINDOW_ID)
    parser.add_argument("--figure-stem", default="mono511_open_vs_wgrid")
    parser.add_argument("--consistency-rtol", type=float, default=1e-7)
    parser.add_argument(
        "--allow-metadata-defaults",
        action="store_true",
        help="explicitly insert canonical PARMA constants for missing metadata; recorded as warnings",
    )
    args = parser.parse_args(argv)

    if args.make_synthetic_fixture:
        fixture_paths = make_synthetic_fixture(Path(args.make_synthetic_fixture).resolve())
        args.comparison = args.comparison or str(fixture_paths["comparison"])
        args.open_cutflow = args.open_cutflow or str(fixture_paths["open_cutflow"])
        args.grid_cutflow = args.grid_cutflow or str(fixture_paths["grid_cutflow"])
        args.open_bins = args.open_bins or str(fixture_paths["open_bins"])
        args.grid_bins = args.grid_bins or str(fixture_paths["grid_bins"])
        args.output_dir = args.output_dir or str(Path(args.make_synthetic_fixture).resolve() / "output")

    required = ("comparison", "open_cutflow", "grid_cutflow", "open_bins", "grid_bins", "output_dir")
    missing = [f"--{name.replace('_', '-')}" for name in required if not getattr(args, name)]
    if missing:
        parser.error("missing required arguments: " + ", ".join(missing))
    if args.consistency_rtol <= 0 or args.consistency_rtol > 1e-3:
        parser.error("--consistency-rtol must be in (0, 1e-3]")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        outputs = build(args)
    except (InputContractError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    payload = {
        "status": "PASS__MONO511_STATIC_REPORT",
        "outputs": {key: str(path) for key, path in outputs.items()},
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
