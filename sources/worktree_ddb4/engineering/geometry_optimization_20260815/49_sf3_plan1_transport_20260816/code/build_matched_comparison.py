#!/usr/bin/env python3
"""Compare fresh SF3 Plan-1 small tables with frozen 47/SE3 authorities.

This stage never opens, stats, or hashes a SIM.  It reports the matched day-15
W2 background, transported activity, and fair 37,194-ray full-envelope signal.
The 20-day F3 ratio and the sole <=0.75 top-up decision remain stage-06 work.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from sf3_plan1_common import FAMILIES, PACKAGE_ROOT, PROFILE_ID, utc_now


CONFIG = PACKAGE_ROOT / "analysis_inputs.json"
FINAL_RESPONSE = "measured"
FINAL_STAGE = "side_compton_fov_pass"
FINAL_WINDOW = "w2_510p58_511p42"
SIGNAL_TRIALS = 37_194
MAX_SMALL_BYTES = 64 * 1024**2


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size > MAX_SMALL_BYTES:
        raise RuntimeError(f"missing/non-small JSON authority: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file() or path.stat().st_size > MAX_SMALL_BYTES:
        raise RuntimeError(f"missing/non-small CSV authority: {path}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = fields or (list(rows[0]) if rows else [])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def close(actual: Any, expected: float, *, rel: float = 2.0e-12, abs_: float = 1.0e-14) -> bool:
    try:
        return math.isclose(float(actual), expected, rel_tol=rel, abs_tol=abs_)
    except (TypeError, ValueError):
        return False


def paths(config: dict[str, Any]) -> dict[str, Path]:
    fresh02 = Path(config["outputs"]["stage_02"])
    fresh04 = Path(config["outputs"]["stage_04"])
    frozen = Path(config["frozen_se3"]["plan1_root"])
    return {
        "fresh02_summary": fresh02 / "day15_summary.json",
        "fresh02_inventory": fresh02 / "day15_inventory.csv",
        "fresh02_source_index": fresh02 / "delayed_source_index.csv",
        "fresh04_summary": fresh04 / "summary.json",
        "fresh04_cutflow": fresh04 / "common_cutflow.csv",
        "fresh04_signal": fresh04 / "signal_acceptance_effective_area.csv",
        "fresh04_w": fresh04 / "passive_w_diagnostics.csv",
        "frozen02_summary": frozen / "outputs/02_activation/day15_summary.json",
        "frozen02_inventory": frozen / "outputs/02_activation/day15_inventory.csv",
        "frozen02_source_index": frozen / "outputs/02_activation/delayed_source_index.csv",
        "frozen04_summary": frozen / "outputs/04_common_response/summary.json",
        "frozen04_cutflow": frozen / "outputs/04_common_response/common_cutflow.csv",
        "frozen04_signal": frozen / "outputs/04_common_response/signal_acceptance_effective_area.csv",
        "frozen06_summary": Path(config["frozen_se3"]["mission_summary"]),
        "output": Path(config["outputs"]["stage_05"]),
    }


def final_components(rows: list[dict[str, str]], geometry: str) -> list[dict[str, str]]:
    selected = [
        row for row in rows
        if row.get("geometry") == geometry
        and row.get("response_state") == FINAL_RESPONSE
        and row.get("stage") == FINAL_STAGE
        and row.get("window_id") == FINAL_WINDOW
        and row.get("stream") in ("prompt", "delayed")
    ]
    keys = {(row["stream"], row["family"]) for row in selected}
    expected = {(stream, family) for stream in ("prompt", "delayed") for family in FAMILIES}
    if keys != expected or len(selected) != len(expected):
        raise RuntimeError(f"{geometry} final W2 family/stream closure differs")
    return selected


def background_summary(rows: list[dict[str, str]], geometry: str) -> dict[str, Any]:
    selected = final_components(rows, geometry)
    result: dict[str, Any] = {"geometry": geometry}
    for stream in ("prompt", "delayed"):
        cells = [row for row in selected if row["stream"] == stream]
        result[f"{stream}_selected_events"] = sum(int(row["selected_events"]) for row in cells)
        result[f"{stream}_rate_cps"] = math.fsum(float(row["weighted_value"]) for row in cells)
        result[f"{stream}_stat_sigma_cps"] = math.sqrt(math.fsum(
            float(row["weighted_stat_sigma"]) ** 2 for row in cells
        ))
        result[f"{stream}_componentwise_upper95_cps"] = math.fsum(
            float(row["weighted_upper95"]) for row in cells
        )
    result["background_rate_cps"] = result["prompt_rate_cps"] + result["delayed_rate_cps"]
    result["background_stat_sigma_cps"] = math.hypot(
        result["prompt_stat_sigma_cps"], result["delayed_stat_sigma_cps"]
    )
    result["background_componentwise_upper95_cps"] = (
        result["prompt_componentwise_upper95_cps"]
        + result["delayed_componentwise_upper95_cps"]
    )
    return result


def signal_summary(rows: list[dict[str, str]], geometry: str, scope: str) -> dict[str, Any]:
    selected = [
        row for row in rows
        if row.get("geometry") == geometry
        and row.get("response_state") == FINAL_RESPONSE
        and row.get("stage") == FINAL_STAGE
        and row.get("window_id") == FINAL_WINDOW
    ]
    if len(selected) != 1:
        raise RuntimeError(f"{geometry} full-envelope W2 signal row closure differs")
    row = selected[0]
    if int(row["trials"]) != SIGNAL_TRIALS or row.get("signal_scope") != scope:
        raise RuntimeError(f"{geometry} full-envelope signal contract differs")
    return {
        "geometry": geometry,
        "signal_scope": scope,
        "trials": int(row["trials"]),
        "selected_events": int(row["selected_events"]),
        "acceptance": float(row["acceptance"]),
        "acceptance_lower95": float(row["acceptance_lower95"]),
        "acceptance_upper95": float(row["acceptance_upper95"]),
        "selected_effective_area_cm2": float(row["selected_effective_area_cm2"]),
        "selected_effective_area_lower95_cm2": float(row["selected_effective_area_lower95_cm2"]),
        "selected_effective_area_upper95_cm2": float(row["selected_effective_area_upper95_cm2"]),
    }


def activation_summary(inventory: list[dict[str, str]], source_index: list[dict[str, str]], geometry: str) -> dict[str, Any]:
    rows = [row for row in inventory if row.get("geometry") == geometry]
    if not rows or any(row.get("incident_family") not in FAMILIES for row in rows):
        raise RuntimeError(f"{geometry} activation inventory closure differs")
    by_family = {
        family: math.fsum(
            float(row["day15_activity_Bq"]) for row in rows
            if row["incident_family"] == family
            and row.get("source_disposition") == "transported_ground_state"
        ) for family in FAMILIES
    }
    registered = [row for row in source_index if row.get("geometry") == geometry]
    if {row.get("incident_family") for row in registered} != set(FAMILIES):
        raise RuntimeError(f"{geometry} delayed source registry does not close eight families")
    dispositions = {row["incident_family"]: row["execution_disposition"] for row in registered}
    zero = sorted(family for family, disposition in dispositions.items() if disposition == "SKIP_ZERO_A15")
    for family in zero:
        if by_family[family] != 0.0:
            raise RuntimeError(f"{geometry}/{family} zero-source registry conflicts with inventory")
    return {
        "geometry": geometry,
        "transported_ground_activity_Bq": math.fsum(by_family.values()),
        "day15_activity_Bq_by_family": by_family,
        "execution_disposition_by_family": dispositions,
        "zero_A15_families": zero,
    }


def check_prerequisites() -> dict[str, Any]:
    config = read_json(CONFIG)
    p = paths(config)
    missing = [str(path) for name, path in p.items() if name != "output" and not path.is_file()]
    errors: list[str] = []
    if config.get("profile_id") != PROFILE_ID:
        errors.append("profile id differs")
    if config.get("frozen_se3", {}).get("scope") != "FROZEN_SMALL_TABLES_ONLY__NO_SE3_SIM_OR_RECEIPT_REQUIRED":
        errors.append("frozen SE3 scope differs")
    if not missing:
        try:
            for key in ("fresh02_summary", "fresh04_summary"):
                if not str(read_json(p[key]).get("status", "")).startswith("PASS__SF3"):
                    errors.append(f"{key} is not SF3 PASS")
            for key in ("frozen02_summary", "frozen04_summary", "frozen06_summary"):
                if not str(read_json(p[key]).get("status", "")).startswith("PASS__SE3"):
                    errors.append(f"{key} is not frozen SE3 PASS")
            se3_bg = background_summary(read_csv(p["frozen04_cutflow"]), "SE3")
            se3_sig = signal_summary(
                read_csv(p["frozen04_signal"]), "SE3", "FULL_ENVELOPE_SE3_ONLY"
            )
            anchors = config["frozen_se3"]
            for actual, expected, label in (
                (se3_bg["prompt_rate_cps"], anchors["day15_prompt_cps"], "SE3 prompt"),
                (se3_bg["delayed_rate_cps"], anchors["day15_delayed_cps"], "SE3 delayed"),
                (se3_sig["selected_events"], anchors["signal_selected"], "SE3 signal selected"),
                (se3_sig["selected_effective_area_cm2"], anchors["signal_aeff_cm2"], "SE3 Aeff"),
            ):
                if not close(actual, float(expected)):
                    errors.append(f"{label} frozen anchor differs")
        except Exception as exc:
            errors.append(str(exc))
    ready = not missing and not errors
    if ready:
        status = "PASS__SF3_SE3_COMPARISON_PREREQUISITES_READY"
    elif errors:
        status = "FAIL__SF3_SE3_COMPARISON_AUTHORITY_OR_CONTRACT"
    else:
        status = "WAITING__SF3_SE3_COMPARISON_INPUTS"
    return {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "status": status,
        "ready": ready,
        "missing": missing,
        "errors": errors,
        "sim_access_policy": "NO_SIM_OPEN_STAT_OR_HASH__SMALL_CSV_JSON_ONLY",
    }


def build() -> dict[str, Any]:
    gate = check_prerequisites()
    if not gate["ready"]:
        raise RuntimeError(json.dumps(gate, indent=2, sort_keys=True))
    config = read_json(CONFIG)
    p = paths(config)
    output = p["output"]
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f".{output.name}.work-", dir=output.parent))
    try:
        sf3_bg = background_summary(read_csv(p["fresh04_cutflow"]), "SF3")
        se3_bg = background_summary(read_csv(p["frozen04_cutflow"]), "SE3")
        sf3_sig = signal_summary(read_csv(p["fresh04_signal"]), "SF3", "FULL_ENVELOPE_SF3_ONLY")
        se3_sig = signal_summary(read_csv(p["frozen04_signal"]), "SE3", "FULL_ENVELOPE_SE3_ONLY")
        sf3_act = activation_summary(
            read_csv(p["fresh02_inventory"]), read_csv(p["fresh02_source_index"]), "SF3"
        )
        se3_act = activation_summary(
            read_csv(p["frozen02_inventory"]), read_csv(p["frozen02_source_index"]), "SE3"
        )
        w_rows = read_csv(p["fresh04_w"])
        if {row.get("geometry") for row in w_rows} != {"SF3"}:
            raise RuntimeError("passive-W diagnostics are not SF3-only")
        ratios = {
            "day15_prompt_SF3_over_SE3": None,
            "day15_delayed_SF3_over_SE3": sf3_bg["delayed_rate_cps"] / se3_bg["delayed_rate_cps"],
            "day15_background_SF3_over_SE3": sf3_bg["background_rate_cps"] / se3_bg["background_rate_cps"],
            "transported_activity_SF3_over_SE3": sf3_act["transported_ground_activity_Bq"] / se3_act["transported_ground_activity_Bq"],
            "signal_Aeff_SF3_over_SE3": sf3_sig["selected_effective_area_cm2"] / se3_sig["selected_effective_area_cm2"],
            "signal_Aeff_lower95_SF3_over_SE3": sf3_sig["selected_effective_area_lower95_cm2"] / se3_sig["selected_effective_area_lower95_cm2"],
        }
        summary = {
            "schema_version": 1,
            "profile_id": PROFILE_ID,
            "status": "PASS__SF3_VS_FROZEN_SE3_DAY15_AND_FULL_ENVELOPE_COMPARISON",
            "scope": "fresh SF3 Plan-1 numerator versus frozen 47/SE3 small-table denominator",
            "fresh_sf3": {"background": sf3_bg, "signal": sf3_sig, "activation": sf3_act},
            "frozen_se3": {"background": se3_bg, "signal": se3_sig, "activation": se3_act},
            "ratios": ratios,
            "passive_w": {
                "role": "DIAGNOSTIC_ONLY__NEVER_ACTIVE_VETO",
                "rows": w_rows,
            },
            "f3_gate": {
                "status": "DEFERRED_TO_STAGE06_81NODE_MISSION_FOLD",
                "metric": "central F3_SF3/F3_SE3",
                "threshold": 0.75,
                "proxy_is_not_a_gate": True,
            },
            "sim_access_policy": "NO_SIM_OPEN_STAT_OR_HASH__SMALL_CSV_JSON_ONLY",
            "authority_boundary": "DAY15_AND_FULL_ENVELOPE_SIGNAL_COMPARISON__NOT_F3_GATE",
        }
        write_json(work / "summary.json", summary)
        write_csv(work / "day15_comparison.csv", [se3_bg, sf3_bg])
        write_csv(work / "signal_comparison.csv", [se3_sig, sf3_sig])
        (work / "REPORT.md").write_text(
            "\n".join([
                "# Fresh SF3 versus frozen SE3 matched comparison", "",
                f"Status: `{summary['status']}`", "",
                f"- SF3/SE3 day-15 background: {ratios['day15_background_SF3_over_SE3']:.9g}",
                f"- SF3/SE3 delayed: {ratios['day15_delayed_SF3_over_SE3']:.9g}",
                f"- SF3/SE3 full-envelope Aeff: {ratios['signal_Aeff_SF3_over_SE3']:.9g}",
                "- The 81-node central F3 ratio alone decides the <=0.75 full-stat gate in stage 06.",
            ]) + "\n", encoding="utf-8"
        )
        write_json(work / "manifest.json", {
            "schema_version": 1,
            "status": summary["status"],
            "created_at": utc_now(),
            "small_input_paths": {key: str(value) for key, value in p.items() if key != "output"},
            "SIM_files_opened_statted_or_hashed": 0,
        })
        os.rename(work, output)
        return summary
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise


def self_test() -> dict[str, Any]:
    rows = []
    for stream in ("prompt", "delayed"):
        for family in FAMILIES:
            rows.append({
                "geometry": "SF3", "stream": stream, "family": family,
                "response_state": FINAL_RESPONSE, "stage": FINAL_STAGE,
                "window_id": FINAL_WINDOW, "selected_events": "0",
                "weighted_value": "0", "weighted_stat_sigma": "0",
                "weighted_upper95": "1",
            })
    result = background_summary(rows, "SF3")
    if result["background_rate_cps"] != 0.0 or result["background_componentwise_upper95_cps"] != 16.0:
        raise AssertionError("background aggregation self-test failed")
    return {
        "schema_version": 1,
        "status": "PASS__SF3_SE3_MATCHED_COMPARISON_SELF_TEST",
        "sim_accessed": False,
        "checks": ["eight_family_two_stream_closure", "central_zero_with_finite_componentwise_upper"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check-prerequisites", action="store_true")
    group.add_argument("--build", action="store_true")
    group.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), indent=2, sort_keys=True))
        return 0
    if args.check_prerequisites:
        result = check_prerequisites()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ready"] else 2
    result = build()
    print(json.dumps({"status": result["status"], "output": str(paths(read_json(CONFIG))["output"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
