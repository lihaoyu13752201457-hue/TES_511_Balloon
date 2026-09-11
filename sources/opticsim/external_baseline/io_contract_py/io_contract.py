from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set


PHASE_SPACE_FIELDS = [
    "event_id",
    "E_keV",
    "x_mm",
    "y_mm",
    "z_mm",
    "ux",
    "uy",
    "uz",
    "weight",
    "source_tag",
]

OPTICS_HISTORY_FIELDS = [
    "event_id",
    "track_id",
    "optics_kind",
    "stage",
    "ring_id",
    "tile_id",
    "surface_id",
    "E_keV",
    "x_mm",
    "y_mm",
    "z_mm",
    "ux_in",
    "uy_in",
    "uz_in",
    "ux_out",
    "uy_out",
    "uz_out",
    "grazing_angle_rad",
    "p_reflect",
    "p_absorb",
    "p_transmit",
    "n_bounce",
    "weight",
]

HITS_FIELDS = [
    "event_id",
    "track_id",
    "detector_kind",
    "layer_id",
    "pixel_i",
    "pixel_j",
    "pixel_uid",
    "x_mm",
    "y_mm",
    "z_mm",
    "edep_keV",
    "process_name",
    "time_ns",
]

EVENT_SUMMARY_FIELDS = [
    "event_id",
    "total_tes_edep_keV",
    "n_tes_pixel_hits",
    "is_singlehit",
    "is_multihit",
    "bgo_edep_keV",
    "bgo_veto",
    "reco_energy_keV",
    "weight",
]

ALLOWED_OPTICS_KINDS = {"CHANNEL", "LAUE"}
ALLOWED_OPTICS_STAGES = {"ENTRY", "BOUNCE", "DIFFRACT", "ABSORB", "LEAK", "TRANSMIT", "EXIT"}
ALLOWED_DETECTOR_KINDS = {"TES_PIXEL", "BGO", "WINDOW", "PASSIVE"}


@dataclass(frozen=True)
class ValidationResult:
    table: str
    path: str
    ok: bool
    n_rows: int
    errors: List[str]
    warnings: List[str]
    extra_columns: List[str]

    def as_dict(self) -> Dict[str, object]:
        return {
            "table": self.table,
            "path": self.path,
            "ok": self.ok,
            "n_rows": self.n_rows,
            "errors": self.errors,
            "warnings": self.warnings,
            "extra_columns": self.extra_columns,
        }


def _read_rows(path: str | Path) -> tuple[List[str], List[Dict[str, str]]]:
    with Path(path).open(newline="") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        return fields, list(reader)


def _missing_fields(actual_fields: Sequence[str], required_fields: Sequence[str]) -> List[str]:
    actual = set(actual_fields)
    return [field for field in required_fields if field not in actual]


def _extra_fields(actual_fields: Sequence[str], required_fields: Sequence[str]) -> List[str]:
    required = set(required_fields)
    return [field for field in actual_fields if field not in required]


def _parse_float(row: Dict[str, str], field: str, row_index: int, errors: List[str], allow_blank: bool = False) -> Optional[float]:
    value = row.get(field, "")
    if allow_blank and value == "":
        return None
    try:
        parsed = float(value)
    except ValueError:
        errors.append(f"row {row_index}: {field} is not a float: {value!r}")
        return None
    if not math.isfinite(parsed):
        errors.append(f"row {row_index}: {field} is not finite")
        return None
    return parsed


def _parse_int(row: Dict[str, str], field: str, row_index: int, errors: List[str]) -> Optional[int]:
    value = row.get(field, "")
    try:
        return int(value)
    except ValueError:
        errors.append(f"row {row_index}: {field} is not an int: {value!r}")
        return None


def _check_probability(value: Optional[float], field: str, row_index: int, errors: List[str]) -> None:
    if value is not None and not (0.0 <= value <= 1.0):
        errors.append(f"row {row_index}: {field} must be within [0, 1]")


def _truncate(messages: List[str], limit: int = 25) -> List[str]:
    if len(messages) <= limit:
        return messages
    return messages[:limit] + [f"... {len(messages) - limit} more"]


def validate_phase_space(path: str | Path, direction_tolerance: float = 1.0e-6) -> ValidationResult:
    fields, rows = _read_rows(path)
    errors = [f"missing required column: {field}" for field in _missing_fields(fields, PHASE_SPACE_FIELDS)]
    warnings: List[str] = []
    event_ids: Set[int] = set()
    for idx, row in enumerate(rows, start=2):
        event_id = _parse_int(row, "event_id", idx, errors)
        if event_id is not None:
            if event_id in event_ids:
                errors.append(f"row {idx}: duplicate event_id {event_id}")
            event_ids.add(event_id)
        energy = _parse_float(row, "E_keV", idx, errors)
        if energy is not None and energy <= 0.0:
            errors.append(f"row {idx}: E_keV must be positive")
        for field in ("x_mm", "y_mm", "z_mm"):
            _parse_float(row, field, idx, errors)
        ux = _parse_float(row, "ux", idx, errors)
        uy = _parse_float(row, "uy", idx, errors)
        uz = _parse_float(row, "uz", idx, errors)
        if ux is not None and uy is not None and uz is not None:
            norm = math.sqrt(ux * ux + uy * uy + uz * uz)
            if abs(norm - 1.0) > direction_tolerance:
                errors.append(f"row {idx}: direction norm {norm:.9g} is outside tolerance")
        weight = _parse_float(row, "weight", idx, errors)
        if weight is not None and weight < 0.0:
            errors.append(f"row {idx}: weight must be non-negative")
        if not row.get("source_tag", ""):
            warnings.append(f"row {idx}: source_tag is blank")
    if not rows:
        errors.append("table has no rows")
    return ValidationResult(
        table="phase_space",
        path=str(path),
        ok=not errors,
        n_rows=len(rows),
        errors=_truncate(errors),
        warnings=_truncate(warnings),
        extra_columns=_extra_fields(fields, PHASE_SPACE_FIELDS),
    )


def validate_optics_history(path: str | Path) -> ValidationResult:
    fields, rows = _read_rows(path)
    errors = [f"missing required column: {field}" for field in _missing_fields(fields, OPTICS_HISTORY_FIELDS)]
    warnings: List[str] = []
    for idx, row in enumerate(rows, start=2):
        _parse_int(row, "event_id", idx, errors)
        _parse_int(row, "track_id", idx, errors)
        if row.get("optics_kind") not in ALLOWED_OPTICS_KINDS:
            errors.append(f"row {idx}: invalid optics_kind {row.get('optics_kind')!r}")
        if row.get("stage") not in ALLOWED_OPTICS_STAGES:
            errors.append(f"row {idx}: invalid stage {row.get('stage')!r}")
        for field in ("ring_id", "tile_id", "n_bounce"):
            value = _parse_int(row, field, idx, errors)
            if field == "n_bounce" and value is not None and value < 0:
                errors.append(f"row {idx}: n_bounce must be non-negative")
        energy = _parse_float(row, "E_keV", idx, errors)
        if energy is not None and energy <= 0.0:
            errors.append(f"row {idx}: E_keV must be positive")
        for field in ("x_mm", "y_mm", "z_mm", "ux_in", "uy_in", "uz_in", "ux_out", "uy_out", "uz_out"):
            _parse_float(row, field, idx, errors)
        _parse_float(row, "grazing_angle_rad", idx, errors, allow_blank=True)
        for field in ("p_reflect", "p_absorb", "p_transmit"):
            _check_probability(_parse_float(row, field, idx, errors, allow_blank=True), field, idx, errors)
        weight = _parse_float(row, "weight", idx, errors)
        if weight is not None and weight < 0.0:
            errors.append(f"row {idx}: weight must be non-negative")
        if not row.get("surface_id", ""):
            warnings.append(f"row {idx}: surface_id is blank")
    if not rows:
        errors.append("table has no rows")
    return ValidationResult(
        table="optics_history",
        path=str(path),
        ok=not errors,
        n_rows=len(rows),
        errors=_truncate(errors),
        warnings=_truncate(warnings),
        extra_columns=_extra_fields(fields, OPTICS_HISTORY_FIELDS),
    )


def validate_hits(path: str | Path) -> ValidationResult:
    fields, rows = _read_rows(path)
    errors = [f"missing required column: {field}" for field in _missing_fields(fields, HITS_FIELDS)]
    warnings: List[str] = []
    for idx, row in enumerate(rows, start=2):
        _parse_int(row, "event_id", idx, errors)
        _parse_int(row, "track_id", idx, errors)
        if row.get("detector_kind") not in ALLOWED_DETECTOR_KINDS:
            errors.append(f"row {idx}: invalid detector_kind {row.get('detector_kind')!r}")
        for field in ("layer_id", "pixel_i", "pixel_j"):
            _parse_int(row, field, idx, errors)
        for field in ("x_mm", "y_mm", "z_mm", "time_ns"):
            _parse_float(row, field, idx, errors)
        edep = _parse_float(row, "edep_keV", idx, errors)
        if edep is not None and edep < 0.0:
            errors.append(f"row {idx}: edep_keV must be non-negative")
        if not row.get("pixel_uid", ""):
            warnings.append(f"row {idx}: pixel_uid is blank")
        if not row.get("process_name", ""):
            warnings.append(f"row {idx}: process_name is blank")
    return ValidationResult(
        table="hits",
        path=str(path),
        ok=not errors,
        n_rows=len(rows),
        errors=_truncate(errors),
        warnings=_truncate(warnings),
        extra_columns=_extra_fields(fields, HITS_FIELDS),
    )


def validate_event_summary(path: str | Path) -> ValidationResult:
    fields, rows = _read_rows(path)
    errors = [f"missing required column: {field}" for field in _missing_fields(fields, EVENT_SUMMARY_FIELDS)]
    warnings: List[str] = []
    event_ids: Set[int] = set()
    for idx, row in enumerate(rows, start=2):
        event_id = _parse_int(row, "event_id", idx, errors)
        if event_id is not None:
            if event_id in event_ids:
                errors.append(f"row {idx}: duplicate event_id {event_id}")
            event_ids.add(event_id)
        for field in ("n_tes_pixel_hits", "is_singlehit", "is_multihit", "bgo_veto"):
            value = _parse_int(row, field, idx, errors)
            if field in {"is_singlehit", "is_multihit", "bgo_veto"} and value is not None and value not in {0, 1}:
                errors.append(f"row {idx}: {field} must be 0 or 1")
            if field == "n_tes_pixel_hits" and value is not None and value < 0:
                errors.append(f"row {idx}: n_tes_pixel_hits must be non-negative")
        for field in ("total_tes_edep_keV", "bgo_edep_keV", "reco_energy_keV", "weight"):
            value = _parse_float(row, field, idx, errors)
            if value is not None and value < 0.0:
                errors.append(f"row {idx}: {field} must be non-negative")
        single = row.get("is_singlehit")
        multi = row.get("is_multihit")
        if single == "1" and multi == "1":
            errors.append(f"row {idx}: event cannot be both singlehit and multihit")
    if not rows:
        errors.append("table has no rows")
    return ValidationResult(
        table="event_summary",
        path=str(path),
        ok=not errors,
        n_rows=len(rows),
        errors=_truncate(errors),
        warnings=_truncate(warnings),
        extra_columns=_extra_fields(fields, EVENT_SUMMARY_FIELDS),
    )


def validate_detector_crosslinks(hits_path: str | Path, event_summary_path: str | Path) -> ValidationResult:
    _, hit_rows = _read_rows(hits_path)
    _, event_rows = _read_rows(event_summary_path)
    errors: List[str] = []
    warnings: List[str] = []
    event_ids = {int(row["event_id"]) for row in event_rows}
    tes_pixel_counts: Dict[int, Set[str]] = {}
    tes_edep_by_event: Dict[int, float] = {}
    bgo_edep_by_event: Dict[int, float] = {}
    for idx, row in enumerate(hit_rows, start=2):
        try:
            event_id = int(row["event_id"])
        except ValueError:
            continue
        if event_id not in event_ids:
            errors.append(f"hits row {idx}: event_id {event_id} absent from event_summary")
        if row.get("detector_kind") == "TES_PIXEL":
            tes_pixel_counts.setdefault(event_id, set()).add(row.get("pixel_uid", ""))
            try:
                tes_edep_by_event[event_id] = tes_edep_by_event.get(event_id, 0.0) + float(row["edep_keV"])
            except ValueError:
                pass
        if row.get("detector_kind") == "BGO":
            try:
                bgo_edep_by_event[event_id] = bgo_edep_by_event.get(event_id, 0.0) + float(row["edep_keV"])
            except ValueError:
                pass
    for idx, row in enumerate(event_rows, start=2):
        event_id = int(row["event_id"])
        expected_n = len(tes_pixel_counts.get(event_id, set()))
        actual_n = int(row["n_tes_pixel_hits"])
        if actual_n != expected_n:
            errors.append(f"event_summary row {idx}: n_tes_pixel_hits={actual_n}, hits unique TES pixels={expected_n}")
        tes_sum = tes_edep_by_event.get(event_id, 0.0)
        tes_summary = float(row["total_tes_edep_keV"])
        if abs(tes_sum - tes_summary) > 1.0e-6:
            errors.append(f"event_summary row {idx}: total_tes_edep_keV={tes_summary}, TES hit sum={tes_sum}")
        bgo_sum = bgo_edep_by_event.get(event_id, 0.0)
        bgo_summary = float(row["bgo_edep_keV"])
        if abs(bgo_sum - bgo_summary) > 1.0e-6:
            errors.append(f"event_summary row {idx}: bgo_edep_keV={bgo_summary}, BGO hit sum={bgo_sum}")
    return ValidationResult(
        table="detector_crosslinks",
        path=f"{hits_path} + {event_summary_path}",
        ok=not errors,
        n_rows=len(event_rows),
        errors=_truncate(errors),
        warnings=_truncate(warnings),
        extra_columns=[],
    )


def validate_source_detector_event_ids(phase_space_path: str | Path, event_summary_path: str | Path) -> ValidationResult:
    _, phase_rows = _read_rows(phase_space_path)
    _, event_rows = _read_rows(event_summary_path)
    errors: List[str] = []
    warnings: List[str] = []
    phase_ids = {int(row["event_id"]) for row in phase_rows}
    for idx, row in enumerate(event_rows, start=2):
        event_id = int(row["event_id"])
        if event_id not in phase_ids:
            errors.append(f"event_summary row {idx}: event_id {event_id} absent from phase_space source")
    if len(event_rows) < len(phase_rows):
        warnings.append(
            f"event_summary has {len(event_rows)} rows for {len(phase_rows)} phase-space photons; treating as an allowed subset run"
        )
    return ValidationResult(
        table="source_detector_event_ids",
        path=f"{phase_space_path} + {event_summary_path}",
        ok=not errors,
        n_rows=len(event_rows),
        errors=_truncate(errors),
        warnings=_truncate(warnings),
        extra_columns=[],
    )


def validate_run_contract(
    phase_space: Optional[str | Path] = None,
    optics_history: Optional[str | Path] = None,
    hits: Optional[str | Path] = None,
    event_summary: Optional[str | Path] = None,
) -> Dict[str, object]:
    results: List[ValidationResult] = []
    if phase_space is not None:
        results.append(validate_phase_space(phase_space))
    if optics_history is not None:
        results.append(validate_optics_history(optics_history))
    if hits is not None:
        results.append(validate_hits(hits))
    if event_summary is not None:
        results.append(validate_event_summary(event_summary))
    if hits is not None and event_summary is not None:
        results.append(validate_detector_crosslinks(hits, event_summary))
    if phase_space is not None and event_summary is not None:
        results.append(validate_source_detector_event_ids(phase_space, event_summary))
    return {
        "ok": all(result.ok for result in results),
        "n_tables": len(results),
        "results": [result.as_dict() for result in results],
    }


def write_validation_report(report: Dict[str, object], out_json: str | Path, out_markdown: str | Path) -> None:
    out_json_path = Path(out_json)
    out_json_path.parent.mkdir(parents=True, exist_ok=True)
    with out_json_path.open("w") as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write("\n")
    lines = ["# IO Contract Validation", "", f"Overall status: {'PASS' if report['ok'] else 'FAIL'}", ""]
    for result in report["results"]:
        lines.append(f"## {result['table']}")
        lines.append(f"- Path: `{result['path']}`")
        lines.append(f"- Rows: `{result['n_rows']}`")
        lines.append(f"- Status: `{'PASS' if result['ok'] else 'FAIL'}`")
        if result["extra_columns"]:
            lines.append(f"- Extra columns: `{', '.join(result['extra_columns'])}`")
        if result["errors"]:
            lines.append("- Errors:")
            lines.extend(f"  - {err}" for err in result["errors"])
        if result["warnings"]:
            lines.append("- Warnings:")
            lines.extend(f"  - {warning}" for warning in result["warnings"])
        lines.append("")
    Path(out_markdown).write_text("\n".join(lines), encoding="utf-8")
