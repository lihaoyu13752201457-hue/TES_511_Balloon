from __future__ import annotations

import csv
import json
import math
import shutil
from pathlib import Path

from .metrics import weighted_containment_diameter_mm

REQUIRED_COLUMNS = ("scope", "metric", "value", "unit", "source_tool", "source_version")
REQUIRED_LENS_METRICS = ("diffracted_area_cm2", "spot_d90_cm")
DEFAULT_AGREEMENT_THRESHOLDS = {
    "max_abs_diffracted_area_delta_cm2": 0.05,
    "max_abs_spot_d90_delta_cm": 0.05,
}


def import_external_lens_observables(
    input_path: str | Path,
    out_dir: str | Path,
    *,
    current_observables_path: str | Path,
    python_reference_path: str | Path,
    output_name: str = "external_lens_observables.csv",
) -> dict[str, object]:
    input_path = Path(input_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / output_name
    shutil.copyfile(input_path, output_path)
    summary = summarize_external_lens_observables(
        output_path,
        current_observables_path=current_observables_path,
        python_reference_path=python_reference_path,
    )
    summary["observables_csv"] = str(output_path)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def import_external_lens_hits(
    input_path: str | Path,
    out_dir: str | Path,
    *,
    current_observables_path: str | Path,
    python_reference_path: str | Path,
    geometric_area_cm2: float,
    incident_weight: float,
    position_unit: str = "cm",
    x_column: str = "x_cm",
    y_column: str = "y_cm",
    weight_column: str = "weight",
    source_tool: str = "external-hit-table",
    source_version: str = "unspecified",
) -> dict[str, object]:
    input_path = Path(input_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    hits_path = out_dir / "external_lens_hits.csv"
    observables_path = out_dir / "external_lens_observables.csv"
    shutil.copyfile(input_path, hits_path)

    hit_summary = summarize_external_lens_hits(
        hits_path,
        geometric_area_cm2=geometric_area_cm2,
        incident_weight=incident_weight,
        position_unit=position_unit,
        x_column=x_column,
        y_column=y_column,
        weight_column=weight_column,
    )
    if not hit_summary["ok"]:
        summary = {
            "ok": False,
            "errors": hit_summary["errors"],
            "hit_summary": hit_summary,
            "input_hits_csv": str(hits_path),
        }
    else:
        _write_lens_observables_csv(
            observables_path,
            hit_summary["lens_metrics"],
            source_tool=source_tool,
            source_version=source_version,
        )
        summary = summarize_external_lens_observables(
            observables_path,
            current_observables_path=current_observables_path,
            python_reference_path=python_reference_path,
        )
        summary["hit_summary"] = hit_summary
        summary["input_hits_csv"] = str(hits_path)
        summary["observables_csv"] = str(observables_path)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def summarize_external_lens_observables(
    path: str | Path,
    *,
    current_observables_path: str | Path,
    python_reference_path: str | Path,
) -> dict[str, object]:
    rows = _read_rows(path)
    errors = _validate_rows(rows)
    source_tools = sorted({row["source_tool"] for row in rows if row.get("source_tool")}) if rows else []
    source_versions = sorted({row["source_version"] for row in rows if row.get("source_version")}) if rows else []
    if errors:
        return {
            "ok": False,
            "n_rows": len(rows),
            "errors": errors,
            "source_tools": source_tools,
            "source_versions": source_versions,
        }

    lens = _lens_metrics(rows)
    current = json.loads(Path(current_observables_path).read_text(encoding="utf-8"))
    python_ref = json.loads(Path(python_reference_path).read_text(encoding="utf-8"))
    comparison = {
        "diffracted_area_minus_current_observed_cm2": lens["diffracted_area_cm2"]
        - float(current["observed_diffracted_area_cm2"]),
        "diffracted_area_minus_python_reference_cm2": lens["diffracted_area_cm2"]
        - float(python_ref["diffracted_area_reference_cm2"]),
        "spot_d90_minus_current_observed_cm": lens["spot_d90_cm"] - float(current["spot_d90_cm"]),
    }
    agreement_checks = _agreement_checks(comparison)
    agreement_errors = [
        name for name, ok in agreement_checks.items() if not ok
    ]
    return {
        "ok": not agreement_errors,
        "n_rows": len(rows),
        "errors": agreement_errors,
        "source_tools": source_tools,
        "source_versions": source_versions,
        "lens_metrics": lens,
        "comparison": comparison,
        "agreement_checks": agreement_checks,
        "agreement_thresholds": DEFAULT_AGREEMENT_THRESHOLDS,
        "note": (
            "Imported external full-lens observables are compared with the current "
            "opticsim sampled observables and the Python-only full-lens reference. "
            "The thresholds are deliberately broad; failures indicate a convention or "
            "physics mismatch that needs review."
        ),
    }


def summarize_external_lens_hits(
    path: str | Path,
    *,
    geometric_area_cm2: float,
    incident_weight: float,
    position_unit: str = "cm",
    x_column: str = "x_cm",
    y_column: str = "y_cm",
    weight_column: str = "weight",
) -> dict[str, object]:
    rows = _read_rows(path)
    errors = _validate_hit_rows(
        rows,
        geometric_area_cm2=geometric_area_cm2,
        incident_weight=incident_weight,
        position_unit=position_unit,
        x_column=x_column,
        y_column=y_column,
        weight_column=weight_column,
    )
    if errors:
        return {"ok": False, "n_hits": len(rows), "errors": errors}

    unit_scale_to_mm = 10.0 if position_unit == "cm" else 1.0
    points_mm = []
    weights = []
    for row in rows:
        points_mm.append((float(row[x_column]) * unit_scale_to_mm, float(row[y_column]) * unit_scale_to_mm))
        weights.append(float(row[weight_column]) if weight_column in row and row[weight_column] else 1.0)

    diffracted_weight = sum(weights)
    lens_metrics = {
        "diffracted_area_cm2": geometric_area_cm2 * diffracted_weight / incident_weight,
        "spot_d90_cm": weighted_containment_diameter_mm(points_mm, weights, 0.9) / 10.0,
    }
    return {
        "ok": True,
        "n_hits": len(rows),
        "errors": [],
        "lens_metrics": lens_metrics,
        "geometric_area_cm2": geometric_area_cm2,
        "incident_weight": incident_weight,
        "diffracted_weight": diffracted_weight,
        "position_unit": position_unit,
        "x_column": x_column,
        "y_column": y_column,
        "weight_column": weight_column,
        "note": (
            "Effective area is geometric_area_cm2 * sum(hit weights) / incident_weight; "
            "spot_d90_cm is the weighted 90% containment diameter in the detector plane."
        ),
    }


def _read_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(newline="") as handle:
        return list(csv.DictReader(handle))


def _validate_rows(rows: list[dict[str, str]]) -> list[str]:
    if not rows:
        return ["empty external lens observables file"]
    missing = [name for name in REQUIRED_COLUMNS if name not in rows[0]]
    if missing:
        return ["missing columns: " + ",".join(missing)]
    errors = []
    lens_metrics: set[str] = set()
    for idx, row in enumerate(rows):
        if row["scope"] == "lens":
            lens_metrics.add(row["metric"])
        try:
            value = float(row["value"])
        except ValueError:
            errors.append(f"row {idx}: non-numeric value")
            continue
        if not math.isfinite(value):
            errors.append(f"row {idx}: non-finite value")
    missing_metrics = [metric for metric in REQUIRED_LENS_METRICS if metric not in lens_metrics]
    if missing_metrics:
        errors.append("missing lens metrics: " + ",".join(missing_metrics))
    return errors


def _validate_hit_rows(
    rows: list[dict[str, str]],
    *,
    geometric_area_cm2: float,
    incident_weight: float,
    position_unit: str,
    x_column: str,
    y_column: str,
    weight_column: str,
) -> list[str]:
    if not rows:
        return ["empty external lens hit file"]
    if position_unit not in {"cm", "mm"}:
        return ["position_unit must be cm or mm"]
    if geometric_area_cm2 <= 0.0 or incident_weight <= 0.0:
        return ["geometric_area_cm2 and incident_weight must be positive"]
    missing = [name for name in (x_column, y_column) if name not in rows[0]]
    if missing:
        return ["missing columns: " + ",".join(missing)]
    errors = []
    for idx, row in enumerate(rows):
        for column in (x_column, y_column):
            try:
                value = float(row[column])
            except ValueError:
                errors.append(f"row {idx}: non-numeric {column}")
                continue
            if not math.isfinite(value):
                errors.append(f"row {idx}: non-finite {column}")
        weight_text = row.get(weight_column)
        if weight_text:
            try:
                weight = float(weight_text)
            except ValueError:
                errors.append(f"row {idx}: non-numeric {weight_column}")
                continue
            if not math.isfinite(weight) or weight < 0.0:
                errors.append(f"row {idx}: invalid {weight_column}")
    return errors


def _lens_metrics(rows: list[dict[str, str]]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for row in rows:
        if row["scope"] == "lens":
            metrics[row["metric"]] = float(row["value"])
    return metrics


def _agreement_checks(comparison: dict[str, float]) -> dict[str, bool]:
    area_limit = DEFAULT_AGREEMENT_THRESHOLDS["max_abs_diffracted_area_delta_cm2"]
    spot_limit = DEFAULT_AGREEMENT_THRESHOLDS["max_abs_spot_d90_delta_cm"]
    return {
        "diffracted_area_vs_current": abs(comparison["diffracted_area_minus_current_observed_cm2"]) <= area_limit,
        "diffracted_area_vs_python_reference": abs(comparison["diffracted_area_minus_python_reference_cm2"]) <= area_limit,
        "spot_d90_vs_current": abs(comparison["spot_d90_minus_current_observed_cm"]) <= spot_limit,
    }


def _write_lens_observables_csv(
    path: Path,
    lens_metrics: object,
    *,
    source_tool: str,
    source_version: str,
) -> None:
    metrics = dict(lens_metrics)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        writer.writerow(
            {
                "scope": "lens",
                "metric": "diffracted_area_cm2",
                "value": str(metrics["diffracted_area_cm2"]),
                "unit": "cm2",
                "source_tool": source_tool,
                "source_version": source_version,
            }
        )
        writer.writerow(
            {
                "scope": "lens",
                "metric": "spot_d90_cm",
                "value": str(metrics["spot_d90_cm"]),
                "unit": "cm",
                "source_tool": source_tool,
                "source_version": source_version,
            }
        )
