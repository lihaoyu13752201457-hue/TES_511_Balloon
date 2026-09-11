#!/usr/bin/env python3
"""Validate the compact S3d-O8 source-driven optimization package.

This validator is intentionally light-weight: it reads compact CSV/JSON/notebook
artifacts only.  It does not open raw SIM files and it does not run Cosima.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
WORKSPACE = Path(__file__).resolve().parents[4]
MISSION = WORKSPACE / (
    "engineering/particle_source_unit_repair_20260811/"
    "m05_corrected_reanalysis_20260813/outputs/06_mission"
)
SUMMARY = DATA / "source_driven_optimization_summary.json"
OUTPUT = DATA / "source_driven_analysis_validation.json"
NOTEBOOK = ROOT / "analysis" / "s3d_o8_source_driven_optimization.ipynb"
FIGURE = ROOT / "figures" / "source_budget_and_candidate_gate.png"
REPORT = ROOT / "REPORT.md"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def close(actual: float, expected: float, *, atol: float = 1e-12) -> None:
    require(math.isclose(actual, expected, rel_tol=0.0, abs_tol=atol),
            f"value mismatch: {actual!r} != {expected!r}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def csv_rows(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as stream:
        return sum(1 for _ in csv.DictReader(stream))


def read_delayed_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as stream:
        return [
            {
                "family": row["family"],
                "parent": row["source_parent_ZA"],
                "weight": float(row["event_weight_cps"]),
            }
            for row in csv.DictReader(stream)
        ]


def fold_frozen_delayed_20d(rows: list[dict]) -> float:
    with (MISSION / "mission_timeline.csv").open(newline="", encoding="utf-8") as stream:
        timeline = [row for row in csv.DictReader(stream) if row["geometry"] == "S3d_O8"]
    time_ids = {row["time_bin_id"] for row in timeline}
    selected = {(row["family"], row["parent"]) for row in rows}
    scales = {}
    with (MISSION / "family_parent_activity_by_time.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        for row in csv.DictReader(stream):
            key = (row["incident_family"], row["source_parent_ZA"])
            if (row["geometry"] == "S3d_O8" and row["time_bin_id"] in time_ids
                    and key in selected):
                scales[(row["time_bin_id"], *key)] = float(
                    row["activity_scale_to_constant_environment_day15_inventory"]
                )
    folded = 0.0
    for time in timeline:
        live_weight = (float(time["accidental_live_factor"])
                       * float(time["trajectory_quadrature_weight_s"]))
        rate = sum(
            row["weight"]
            * scales.get((time["time_bin_id"], row["family"], row["parent"]), 0.0)
            for row in rows
        )
        folded += rate * live_weight
    return folded


def atomic_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + f".partial.{os.getpid()}")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                         encoding="utf-8")
    os.replace(temporary, path)


def main() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    require(summary["status"] ==
            "SOURCE_DIAGNOSIS_AND_SCREENING_COMPLETE__NO_GEOMETRY_PROMOTION_AUTHORITY",
            "summary status is not the expected screening-only status")

    prompt_csv = DATA / "prompt_w2_event_summary.csv"
    ray_csv = DATA / "prompt_veto_leak_ray_paths.csv"
    delayed_csv = DATA / "frozen_delayed_source_coordinates.csv"
    require(csv_rows(prompt_csv) == 261, "prompt W2 row count is not 261")
    require(csv_rows(ray_csv) == 3, "prompt leak-ray row count is not 3")
    require(csv_rows(delayed_csv) == 135, "frozen delayed row count is not 135")
    require(summary["prompt_origin"]["veto50_rejected"] == 258,
            "prompt veto rejection count is not 258")
    require(len(summary["prompt_origin"]["veto50_survivors"]) == 3,
            "prompt veto survivor count is not 3")
    with prompt_csv.open(newline="", encoding="utf-8") as stream:
        prompt_rows = list(csv.DictReader(stream))
    prompt_veto_survivors = sum(
        row["pass_veto50"].lower() in {"1", "true", "yes"}
        for row in prompt_rows
    )
    require(prompt_veto_survivors == 3,
            "durable prompt CSV does not contain three veto survivors")

    frozen = summary["frozen_selection"]
    close(frozen["prompt_cps"], 0.016921464065444387)
    close(frozen["delayed_cps"], 0.023205673996914644)
    close(frozen["total_cps"], 0.04012713806235903)
    close(frozen["mission_f3"], 5.14899369e-5, atol=1e-13)
    delayed_rows = read_delayed_rows(delayed_csv)
    delayed_rate = sum(row["weight"] for row in delayed_rows)
    delayed_sigma = math.sqrt(sum(row["weight"] ** 2 for row in delayed_rows))
    delayed_neff = delayed_rate ** 2 / delayed_sigma ** 2
    close(delayed_rate, frozen["delayed_cps"])
    close(delayed_sigma, frozen["delayed_mc_sigma_cps"])
    close(delayed_neff, 12.041680816153212, atol=1e-10)
    folded_frozen_delayed = fold_frozen_delayed_20d(delayed_rows)

    gate = summary["mission_gate"]
    close(gate["signal_counts_20d"], 1490.8022298287442, atol=1e-9)
    close(gate["target_background_counts_20d"], 22224.91288462356,
          atol=1e-8)
    proxies = gate["proxies"]
    frozen_mission = proxies["frozen_reference"]
    close(folded_frozen_delayed, frozen_mission["delayed_counts_20d"], atol=1e-8)
    close(frozen_mission["total_counts_20d_if_current_prompt"],
          65469.99034596817, atol=1e-8)
    close(frozen_mission["f3_if_current_prompt"], 5.148993688652013e-5,
          atol=1e-13)

    lc2_coordinate = proxies["LC2_CuNb_MXC3mm_event_coordinate_excision"]
    close(lc2_coordinate["delayed_counts_20d"], 23280.144704619026,
          atol=1e-8)
    close(lc2_coordinate["f3_if_current_prompt"], 4.548387019702025e-5,
          atol=1e-13)
    require(not lc2_coordinate["target_feasible_by_prompt_suppression_only"],
            "coordinate-excision proxy unexpectedly crosses target")
    require(lc2_coordinate["required_prompt_suppression_fraction_for_target"] is None,
            "prompt suppression should be undefined when delayed alone exceeds target")
    close(lc2_coordinate[
        "additional_delayed_reduction_required_fraction_if_zero_prompt"
    ], 0.04532754557088708, atol=1e-12)

    lc2_mass = proxies["LC2_CuNb_MXC3mm_uniform_activity_mass"]
    close(lc2_mass["delayed_counts_20d"], 15885.526787946941,
          atol=1e-8)
    close(lc2_mass["f3_if_current_prompt"], 4.2063483917887465e-5,
          atol=1e-13)
    close(lc2_mass["required_prompt_suppression_fraction_for_target"],
          0.7720226572153055, atol=1e-12)
    require(lc2_mass["target_feasible_by_prompt_suppression_only"],
            "uniform-activity proxy should be feasible at its allowed prompt budget")

    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    require(nb.get("nbformat") == 4, "notebook is not nbformat 4")
    code_cells = [cell for cell in nb["cells"] if cell.get("cell_type") == "code"]
    require(code_cells, "notebook has no code cells")
    require(all(cell.get("execution_count") is not None for cell in code_cells),
            "notebook contains an unexecuted code cell")
    errors = [output for cell in code_cells for output in cell.get("outputs", [])
              if output.get("output_type") == "error"]
    require(not errors, "notebook contains execution errors")
    require(FIGURE.is_file() and FIGURE.stat().st_size > 1000,
            "summary figure is missing or empty")
    report_text = REPORT.read_text(encoding="utf-8")
    for phrase in (
        "不能宣称已经达标",
        "mK BGO、读出铜或复杂局部 guard：不在本路线内",
        "prompt 必须至少降 77.2%",
    ):
        require(phrase in report_text, f"report claim boundary missing: {phrase}")

    geometry_validation_path = DATA / "lc1_geometry_validation.json"
    geometry_validation = json.loads(
        geometry_validation_path.read_text(encoding="utf-8"))
    require(geometry_validation["status"] ==
            "PASS_LC1_STATIC_GEOMETRY_VALIDATION__COSIMA_NOT_RUN",
            "static geometry validation did not pass")
    require(len(geometry_validation["checks"]) == 3,
            "expected three candidate geometry checks")
    require(all(row["exact_declared_delta"] for row in
                geometry_validation["checks"]),
            "a candidate failed exact geometry-delta validation")

    payload = {
        "schema_version": 1,
        "status": "PASS_SOURCE_DRIVEN_ANALYSIS_VALIDATION",
        "claim_boundary": (
            "Compact analysis consistency only; candidate rates are screening "
            "proxies and do not replace new BUILDUP, delayed transport, common "
            "response, thermal, structural, or magnetic validation."
        ),
        "checks": {
            "prompt_w2_rows": 261,
            "prompt_veto_leak_rows": 3,
            "frozen_delayed_rows": 135,
            "frozen_delayed_rate_cps_reaggregated": delayed_rate,
            "frozen_delayed_mc_sigma_cps_reaggregated": delayed_sigma,
            "frozen_delayed_mc_neff_reaggregated": delayed_neff,
            "frozen_delayed_counts_20d_refolded": folded_frozen_delayed,
            "notebook_code_cells_executed": len(code_cells),
            "notebook_errors": 0,
            "candidate_static_geometry_variants": 3,
        },
        "artifacts": {
            "summary": {"path": str(SUMMARY), "sha256": sha256(SUMMARY)},
            "report": {"path": str(REPORT), "sha256": sha256(REPORT)},
            "notebook": {"path": str(NOTEBOOK), "sha256": sha256(NOTEBOOK)},
            "figure": {"path": str(FIGURE), "sha256": sha256(FIGURE)},
            "prompt_w2_csv": {"path": str(prompt_csv), "sha256": sha256(prompt_csv)},
            "prompt_ray_csv": {"path": str(ray_csv), "sha256": sha256(ray_csv)},
            "delayed_csv": {"path": str(delayed_csv), "sha256": sha256(delayed_csv)},
            "geometry_validation": {
                "path": str(geometry_validation_path),
                "sha256": sha256(geometry_validation_path),
            },
        },
    }
    atomic_json(OUTPUT, payload)
    print(payload["status"])


if __name__ == "__main__":
    main()
