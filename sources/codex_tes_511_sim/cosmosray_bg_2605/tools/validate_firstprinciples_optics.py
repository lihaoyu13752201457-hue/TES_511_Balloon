#!/usr/bin/env python3
"""Validate uncalibrated first-principles channeling optics outputs."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "optics" / "channeling_fp" / "out" / "first_principles_fast"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def add(rows: list[dict[str, Any]], check: str, status: str, details: str, **extra: Any) -> None:
    row = {"check": check, "status": status, "details": details}
    row.update(extra)
    rows.append(row)


def bool_field(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def geometric_open_area_cm2(config: dict[str, Any]) -> float:
    open_fraction = float(config["multilayer"]["channel_gap_nm"]) / float(config["multilayer"]["period_nm"])
    area_mm2 = sum(2.0 * math.pi * float(r["radius_mm"]) * float(r["segment_thickness_mm"]) for r in config["rings"])
    return area_mm2 * open_fraction / 100.0


def validate_run(label: str, run_dir: Path, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    summary_path = run_dir / "summary.json"
    samples_path = run_dir / "bent_channel_samples.csv"
    if not summary_path.exists() or not samples_path.exists():
        add(rows, f"{label}_outputs_present", "FAIL", f"missing {summary_path} or {samples_path}")
        return None

    data = load_json(summary_path)
    config = data["config"]
    summary = data["summary"]
    samples = read_csv(samples_path)
    transport = config.get("transport", {})
    weights = [float(row["transport_weight"]) for row in samples]
    area_terms = [float(row["effective_area_term_mm2"]) for row in samples]
    aeff = float(summary["estimated_effective_area_cm2"])
    geom_open = geometric_open_area_cm2(config)

    checks = [
        ("no_effective_lookup_used", summary.get("weight_model") != "effective_lookup" and not bool(transport.get("use_effective_lookup", False))),
        ("no_exit_angle_supplement", float(summary.get("radial_exit_sigma_mrad", 1.0)) == 0.0 and float(summary.get("tangential_exit_sigma_mrad", 1.0)) == 0.0),
        ("cam511_calibration_flag_false", summary.get("cam511_calibration_used") is False and transport.get("cam511_calibration_used") is False),
        ("weights_nonnegative", all(w >= 0.0 for w in weights)),
        ("weights_le_one", all(w <= 1.0 + 1.0e-12 for w in weights)),
        ("area_terms_nonnegative", all(w >= 0.0 for w in area_terms)),
        ("aeff_below_geometric_open_area", aeff <= geom_open * (1.0 + 1.0e-9)),
        ("finite_spot", math.isfinite(float(summary["weighted_r95_mm"])) and float(summary["weighted_r95_mm"]) > 0.0),
        ("enough_rays", int(summary.get("n_rays", len(samples))) >= 20000),
    ]
    for check, ok in checks:
        add(
            rows,
            f"{label}_{check}",
            "PASS" if ok else "FAIL",
            f"weight_model={summary.get('weight_model')} aeff={aeff:.6g} geom_open={geom_open:.6g} n={len(samples)}",
        )
    return {"config": config, "summary": summary, "samples": samples, "geometric_open_area_cm2": geom_open}


def validate_parratt_table(rows: list[dict[str, Any]]) -> None:
    path = OUT / "reflectivity_wsi_parratt.csv"
    if not path.exists():
        add(rows, "parratt_table_present", "FAIL", "missing reflectivity_wsi_parratt.csv")
        return
    table = read_csv(path)
    refl = [float(row["R_multilayer"]) for row in table]
    finite = all(math.isfinite(v) for v in refl)
    bounded = all(0.0 <= v <= 1.0 for v in refl)
    uncal = all(not bool_field(row.get("cam511_calibration_used", "false")) for row in table)
    add(
        rows,
        "parratt_table_sanity",
        "PASS" if table and finite and bounded and uncal else "FAIL",
        f"rows={len(table)} finite={finite} bounded={bounded} uncalibrated={uncal}",
    )


def validate(results: list[dict[str, Any]]) -> None:
    validate_run("L1_surface", OUT / "L1_surface_onaxis", results)
    validate_parratt_table(results)
    validate_run("L2_parratt", OUT / "L2_parratt_onaxis", results)
    write_csv(OUT / "first_principles_sanity_checks.csv", results)
    (OUT / "first_principles_sanity_checks.json").write_text(
        json.dumps({"results": results}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    results: list[dict[str, Any]] = []
    validate(results)
    for row in results:
        print(f"{row['status']:5} {row['check']}: {row['details']}")
    return 1 if any(row["status"] == "FAIL" for row in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
