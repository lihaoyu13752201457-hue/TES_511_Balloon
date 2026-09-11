#!/usr/bin/env python3
"""Validate Phase 11 production optics schema and template-TS scaffold."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import yaml

from make_phase11_metric_crosswalk import CONFIG_DIR, OUT_DEFAULT


ROOT = Path(__file__).resolve().parents[1]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def add(results: list[dict[str, str]], check: str, status: str, details: str) -> None:
    results.append({"check": check, "status": status, "details": details})


def validate(results: list[dict[str, str]]) -> None:
    schema_path = CONFIG_DIR / "optics_response_511_production_schema.yaml"
    copy_path = OUT_DEFAULT / "optics_response_511_production_schema.yaml"
    if not schema_path.exists() or not copy_path.exists():
        add(results, "phase11_optics_schema_guard", "FAIL", "missing production schema or report copy")
        return
    schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    required = {"aeff_cm2", "psf_kernel", "fov", "bandpass", "focal_plane_mapping", "pointing_visibility", "diffuse_sky_projection", "claim_control"}
    status = schema.get("status")
    nonprod_ok = status != "production_validated" and schema.get("can_support_final_detection_claim") is False
    schema_ok = required.issubset(schema.keys())
    b_sources = sorted((ROOT / "run_configs" / "astro_cases").glob("*B_GC_DIFFUSE*.source"))
    b_ok = schema.get("claim_control", {}).get("B_diffuse_must_not_be_focal_spot_source") is True and not b_sources
    production_fields_ok = True
    if status == "production_validated":
        production_fields_ok = all(
            schema[key].get("table_path") if key in {"aeff_cm2", "psf_kernel"} else schema[key]
            for key in ["aeff_cm2", "psf_kernel", "fov", "bandpass", "focal_plane_mapping", "pointing_visibility"]
        )
    add(
        results,
        "phase11_optics_schema_guard",
        "PASS" if nonprod_ok and schema_ok and b_ok and production_fields_ok else "FAIL",
        f"status={status} schema_ok={schema_ok} final_claim={schema.get('can_support_final_detection_claim')} B_sources={len(b_sources)}",
    )

    ts_path = OUT_DEFAULT / "point_diffuse_template_TS_phase11.csv"
    ts_json = OUT_DEFAULT / "point_diffuse_template_TS_phase11.json"
    if not ts_path.exists() or not ts_json.exists():
        add(results, "phase11_point_diffuse_template_ts_scaffold", "FAIL", "missing template TS csv/json")
        return
    rows = read_csv(ts_path)
    summary = read_json(ts_json)
    required_cols = {"case_id", "A_flux_ph_cm2_s", "B_model_id", "optics_id", "exposure_s", "energy_axis", "energy_window", "template_dimension", "background_instr_cps", "B_diffuse_cps", "A_signal_cps", "TS_Asimov", "sigma_Asimov", "P_ge_3sigma", "F3_required", "F5_required", "claim_level", "notes"}
    columns_ok = required_cols.issubset(rows[0].keys()) if rows else False
    h_ok = summary.get("H0") == "instrumental background + B diffuse null model" and summary.get("H1") == "instrumental background + B diffuse foreground + A central compact source"
    claim_ok = all(row.get("claim_level") == "PLACEHOLDER_OPTICS_ONLY" for row in rows) and summary.get("production_ready") is False
    no_b_focal = all(row.get("B_model_id") == "B_default_bulge8_plus_disk_aperture" for row in rows)
    add(
        results,
        "phase11_point_diffuse_template_ts_scaffold",
        "PASS" if rows and columns_ok and h_ok and claim_ok and no_b_focal else "FAIL",
        f"rows={len(rows)} columns_ok={columns_ok} h_ok={h_ok} claim={summary.get('claim_level')}",
    )


def main() -> int:
    results: list[dict[str, str]] = []
    validate(results)
    for row in results:
        print(f"{row['status']:5} {row['check']}: {row['details']}")
    return 1 if any(row["status"] == "FAIL" for row in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
