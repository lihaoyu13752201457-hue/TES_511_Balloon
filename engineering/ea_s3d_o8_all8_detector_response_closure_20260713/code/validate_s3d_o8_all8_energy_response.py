#!/usr/bin/env python3
"""Independently validate the S3d-O8 all8 64-seed response authority."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parents[1]
DATA = PACKAGE / "data"
SUMMARY = DATA / "s3d_o8_all8_energy_response_summary.json"
REPLICAS = DATA / "s3d_o8_all8_energy_response_replicas.csv"
VALIDATION = DATA / "s3d_o8_all8_energy_response_validation.json"
COMPONENTS = (
    ROOT
    / "engineering/geometry_optimization_20260704"
    / "44_s3d_o8_all8_activation_20260713/data/s3d_o8_all8_delayed_components.json"
)

FAMILIES = ("alpha", "eminus", "eplus", "gamma", "muminus", "muplus", "n", "p")
ZERO_STATUSES = {"PASS_ZERO_PRODUCTION", "PASS_ZERO_ACTIVITY"}
PRIMARY_SEED = 26_071_301
SEED_STRIDE = 7_919
RESPONSE_PASS = "PASS_S3D_O8_ALL8_EVENT_LEVEL_420EV_FWHM_ENERGY_RESPONSE_CLOSURE"
VALIDATION_PASS = "PASS_S3D_O8_ALL8_ENERGY_RESPONSE_VALIDATION"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path | str) -> str:
    value = Path(path)
    try:
        return value.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(value.resolve())


def resolve_path(value: Path | str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def close(actual: Any, expected: Any, label: str, problems: list[str], *, atol: float = 1.0e-15) -> None:
    try:
        observed = float(actual)
        wanted = float(expected)
    except (TypeError, ValueError):
        problems.append(f"{label}: nonnumeric value")
        return
    if not math.isclose(observed, wanted, rel_tol=1.0e-10, abs_tol=atol):
        problems.append(f"{label}: {observed:.17g} != {wanted:.17g}")


def scalar_stats(values: np.ndarray) -> dict[str, Any]:
    half = len(values) // 2
    mean = float(np.mean(values))
    sd = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
    primary = float(values[0])
    standardized = abs(primary - mean) / sd if sd > 0.0 else (0.0 if primary == mean else math.inf)
    half_delta = (
        abs(float(np.mean(values[:half])) - float(np.mean(values[half:]))) / abs(mean)
        if mean
        else 0.0
    )
    q02p5 = float(np.quantile(values, 0.025))
    q97p5 = float(np.quantile(values, 0.975))
    return {
        "mean": mean,
        "sample_sd": sd,
        "mean_standard_error": sd / math.sqrt(len(values)) if len(values) > 1 else 0.0,
        "q02p5": q02p5,
        "q16": float(np.quantile(values, 0.16)),
        "median": float(np.median(values)),
        "q84": float(np.quantile(values, 0.84)),
        "q97p5": q97p5,
        "primary_value": primary,
        "primary_relative_deviation_from_mean": abs(primary - mean) / abs(mean) if mean else 0.0,
        "primary_standardized_deviation": standardized,
        "half_mean_relative_difference": half_delta,
        "primary_within_q02p5_q97p5": bool(q02p5 <= primary <= q97p5),
    }


def compare_mapping(actual: dict[str, Any], expected: dict[str, Any], label: str, problems: list[str]) -> None:
    for key, wanted in expected.items():
        if key not in actual:
            problems.append(f"{label}/{key}: absent")
        elif isinstance(wanted, bool) or wanted is None or isinstance(wanted, str):
            if actual[key] != wanted:
                problems.append(f"{label}/{key}: {actual[key]!r} != {wanted!r}")
        elif isinstance(wanted, (int, float)):
            close(actual[key], wanted, f"{label}/{key}", problems)


def family_stats(
    family: str,
    rows: list[dict[str, str]],
    component: dict[str, Any],
    problems: list[str],
) -> dict[str, Any]:
    counts = np.asarray([int(row[f"delayed_{family}_final_events"]) for row in rows], dtype=np.int64)
    rates = np.asarray([float(row[f"delayed_{family}_final_cps"]) for row in rows], dtype=np.float64)
    local: list[str] = []
    if np.any(counts < 0):
        local.append("negative_count")
    if np.any(~np.isfinite(rates)) or np.any(rates < 0.0):
        local.append("nonfinite_or_negative_rate")
    status = str(component.get("status"))
    if status in ZERO_STATUSES:
        if np.any(counts != 0) or np.any(rates != 0.0):
            local.append("finite_buildup_zero_family_has_selected_response")
        result = {
            "status": "PASS_FINITE_BUILDUP_ZERO_NO_TRANSPORT_RESPONSE_REPLICAS" if not local else "FAIL_FINITE_BUILDUP_ZERO_RESPONSE_REPLICAS",
            "component_status": status,
            "branch": "FINITE_BUILDUP_ZERO_OBSERVATION_NO_TRANSPORT_EXPOSURE",
            "replicas": len(rows),
            "event_weight_cps": None,
            "primary_events": int(counts[0]),
            "primary_rate_cps": float(rates[0]),
            "all_replicas_exact_zero": bool(np.all(counts == 0) and np.all(rates == 0.0)),
            "problems": local,
        }
    elif status == "PASS":
        weight = float(component.get("event_weight_hz") or 0.0)
        if not math.isfinite(weight) or weight <= 0.0:
            local.append("invalid_event_weight")
        closure = np.allclose(rates, counts.astype(np.float64) * weight, rtol=0.0, atol=1.0e-15)
        if not closure:
            local.append("count_weight_rate_closure")
        mean = float(np.mean(counts))
        sd = float(np.std(counts, ddof=1))
        primary = int(counts[0])
        zero_fraction = float(np.mean(counts == 0))
        half = len(counts) // 2
        first = float(np.mean(counts[:half]))
        second = float(np.mean(counts[half:]))
        half_delta = abs(first - second) / abs(mean) if mean else 0.0
        relative = abs(primary - mean) / abs(mean) if mean else 0.0
        standardized = abs(primary - mean) / sd if sd > 0.0 else (0.0 if primary == mean else math.inf)
        q02p5 = float(np.quantile(counts, 0.025))
        q97p5 = float(np.quantile(counts, 0.975))
        in_quantiles = bool(q02p5 <= primary <= q97p5)
        if np.all(counts == 0):
            branch = "ALL_ZERO_SELECTED_RESPONSE_REPLICAS"
        elif mean < 5.0 or zero_fraction > 0.25:
            branch = "SPARSE_SELECTED_RESPONSE_REPLICAS"
        else:
            branch = "REGULAR_SELECTED_RESPONSE_REPLICAS"
            if standardized > 3.0:
                local.append("primary_gt_3sd_from_mean")
            if relative > 0.20:
                local.append("primary_gt_20pct_from_mean")
            if half_delta > 0.10:
                local.append("half_mean_gt_10pct")
            if not in_quantiles:
                local.append("primary_outside_empirical_q02p5_q97p5")
        result = {
            "status": "PASS_FAMILY_RESPONSE_SEED_GATE" if not local else "FAIL_FAMILY_RESPONSE_SEED_GATE",
            "component_status": status,
            "branch": branch,
            "replicas": len(rows),
            "event_weight_cps": weight,
            "primary_events": primary,
            "primary_rate_cps": float(rates[0]),
            "mean_events": mean,
            "sample_sd_events": sd,
            "mean_rate_cps": float(np.mean(rates)),
            "sample_sd_rate_cps": float(np.std(rates, ddof=1)),
            "q02p5_events": q02p5,
            "q16_events": float(np.quantile(counts, 0.16)),
            "median_events": float(np.median(counts)),
            "q84_events": float(np.quantile(counts, 0.84)),
            "q97p5_events": q97p5,
            "zero_replica_fraction": zero_fraction,
            "first_half_mean_events": first,
            "second_half_mean_events": second,
            "half_mean_relative_difference": half_delta,
            "primary_relative_deviation_from_mean": relative,
            "primary_standardized_deviation": standardized,
            "primary_within_q02p5_q97p5": in_quantiles,
            "count_weight_rate_closure_all_replicas": bool(closure),
            "problems": local,
        }
    else:
        local.append(f"unsupported_component_status={status}")
        result = {"status": "FAIL_FAMILY_RESPONSE_SEED_GATE", "component_status": status, "branch": "UNSUPPORTED_COMPONENT_STATUS", "problems": local}
    if local:
        problems.append(f"delayed family {family}: {local}")
    return result


def self_test() -> dict[str, Any]:
    rows: list[dict[str, str]] = []
    for index in range(64):
        row: dict[str, str] = {}
        for family in FAMILIES:
            count = (
                8 + (index % 3)
                if family == "n"
                else 1 if family == "eplus" and index % 16 == 0
                else 0
            )
            weight = 0.25 if family in {"n", "eplus", "gamma"} else 0.0
            row[f"delayed_{family}_final_events"] = str(count)
            row[f"delayed_{family}_final_cps"] = str(count * weight)
        rows.append(row)
    components = {
        family: {
            "family": family,
            "status": "PASS" if family in {"n", "eplus", "gamma"} else "PASS_ZERO_PRODUCTION",
            "event_weight_hz": 0.25 if family in {"n", "eplus", "gamma"} else None,
        }
        for family in FAMILIES
    }
    problems: list[str] = []
    observed = {
        family: family_stats(family, rows, components[family], problems)
        for family in FAMILIES
    }
    expected = {
        "n": "REGULAR_SELECTED_RESPONSE_REPLICAS",
        "eplus": "SPARSE_SELECTED_RESPONSE_REPLICAS",
        "gamma": "ALL_ZERO_SELECTED_RESPONSE_REPLICAS",
        "alpha": "FINITE_BUILDUP_ZERO_OBSERVATION_NO_TRANSPORT_EXPOSURE",
    }
    for family, branch in expected.items():
        if observed[family].get("branch") != branch:
            problems.append(f"self-test {family} branch={observed[family].get('branch')}")
    if problems:
        raise RuntimeError(f"independent response-validator self-test failed: {problems}")
    return {
        "status": "PASS_INDEPENDENT_RESPONSE_VALIDATOR_BRANCH_SELF_TEST",
        "branches": {family: observed[family]["branch"] for family in expected},
        "replicas": len(rows),
    }


def validate() -> dict[str, Any]:
    problems: list[str] = []
    branch_self_test = self_test()
    required = (SUMMARY, REPLICAS, COMPONENTS, Path(__file__))
    missing = [rel(path) for path in required if not path.is_file()]
    if missing:
        problems.append(f"missing={missing}")
        summary: dict[str, Any] = {}
        rows: list[dict[str, str]] = []
        components: dict[str, Any] = {}
    else:
        summary = read_json(SUMMARY)
        rows = read_rows(REPLICAS)
        components = read_json(COMPONENTS)
    if summary.get("status") != RESPONSE_PASS:
        problems.append(f"summary status={summary.get('status')}")

    authorities = summary.get("input_authorities") or {}
    for key, value in authorities.items():
        if key.endswith("_sha256") or not isinstance(value, str):
            continue
        hash_key = f"{key}_sha256"
        path = resolve_path(value)
        if hash_key not in authorities:
            problems.append(f"input authority {key} lacks {hash_key}")
        elif not path.is_file():
            problems.append(f"input authority {key} is absent")
        elif authorities[hash_key] != sha256(path):
            problems.append(f"input authority {key} hash is stale")

    outputs = summary.get("outputs") or {}
    if outputs.get("replicas") != rel(REPLICAS):
        problems.append("summary points to a different replicas CSV")
    if REPLICAS.is_file():
        if int(outputs.get("replicas_size_bytes") or -1) != REPLICAS.stat().st_size:
            problems.append("replicas CSV size binding is stale")
        if outputs.get("replicas_sha256") != sha256(REPLICAS):
            problems.append("replicas CSV hash binding is stale")
    if authorities.get("response_validator") != rel(Path(__file__)) or authorities.get("response_validator_sha256") != sha256(Path(__file__)):
        problems.append("summary does not bind the current independent validator")

    if len(rows) != 64:
        problems.append(f"replica rows={len(rows)} expected=64")
    for index, row in enumerate(rows):
        if int(row.get("replica_index", -1)) != index:
            problems.append(f"replica index mismatch at row {index}")
        if int(row.get("response_seed", -1)) != PRIMARY_SEED + index * SEED_STRIDE:
            problems.append(f"response seed/stride mismatch at row {index}")

    ensemble = summary.get("response_seed_ensemble") or {}
    metric_names = (
        "prompt_final_cps", "delayed_final_cps", "atm511_final_cps",
        "science_unit_acceptance", "day15_background_cps", "day15_signal_cps",
    )
    recomputed_metrics: dict[str, Any] = {}
    if len(rows) == 64:
        for metric in metric_names:
            recomputed = scalar_stats(np.asarray([float(row[metric]) for row in rows], dtype=np.float64))
            recomputed_metrics[metric] = recomputed
            compare_mapping(recomputed, (ensemble.get("metrics") or {}).get(metric, {}), f"ensemble/{metric}", problems)

    component_by_family = {str(row.get("family")): row for row in components.get("components", [])}
    if set(component_by_family) != set(FAMILIES):
        problems.append("component family set is not exactly all eight")
    recomputed_families: dict[str, Any] = {}
    if len(rows) == 64 and set(component_by_family) == set(FAMILIES):
        stored_families = ensemble.get("delayed_family_metrics") or {}
        for family in FAMILIES:
            recomputed = family_stats(family, rows, component_by_family[family], problems)
            recomputed_families[family] = recomputed
            compare_mapping(recomputed, stored_families.get(family, {}), f"ensemble/delayed/{family}", problems)
            if recomputed.get("problems") != (stored_families.get(family) or {}).get("problems"):
                problems.append(f"ensemble/delayed/{family}/problems differs")

    if rows and summary.get("primary_authority"):
        primary = summary["primary_authority"]["step05"]
        w2 = primary["windows"]["w2_510p58_511p42"]
        physical = w2["physical_reference_flux"]
        stream = w2["by_stream"]
        row0 = rows[0]
        for name, actual, expected in (
            ("prompt events", row0["prompt_final_events"], stream["prompt"]["side_compton_fov_pass_events"]),
            ("prompt cps", row0["prompt_final_cps"], physical["prompt_background_cps"]),
            ("delayed events", row0["delayed_final_events"], stream["delayed"]["side_compton_fov_pass_events"]),
            ("delayed cps", row0["delayed_final_cps"], physical["delayed_background_cps"]),
            ("atm events", row0["atm511_final_events"], stream["atm511_sidecar"]["side_compton_fov_pass_events"]),
            ("atm cps", row0["atm511_final_cps"], physical["atm511_background_cps"]),
            ("science events", row0["science_final_events"], stream["science"]["side_compton_fov_pass_events"]),
            ("science acceptance", row0["science_unit_acceptance"], physical["science_unit_acceptance"]),
            ("background cps", row0["day15_background_cps"], physical["background_cps"]),
            ("signal cps", row0["day15_signal_cps"], physical["signal_cps_at_reference_flux"]),
        ):
            close(actual, expected, f"primary/{name}", problems)
        delayed = physical["uncertainty_95"]["delayed_components_by_incident_family"]
        for family in FAMILIES:
            close(row0[f"delayed_{family}_final_events"], delayed[family]["events"], f"primary/{family}/events", problems, atol=0.0)
            close(row0[f"delayed_{family}_final_cps"], delayed[family]["rate_cps"], f"primary/{family}/rate", problems)

    payload = {
        "status": VALIDATION_PASS if not problems else "FAIL_S3D_O8_ALL8_ENERGY_RESPONSE_VALIDATION",
        "generated_at_utc": now_utc(),
        "validator": rel(Path(__file__)),
        "validator_sha256": sha256(Path(__file__)),
        "summary": rel(SUMMARY),
        "summary_sha256": sha256(SUMMARY) if SUMMARY.is_file() else None,
        "replicas": rel(REPLICAS),
        "replicas_size_bytes": REPLICAS.stat().st_size if REPLICAS.is_file() else None,
        "replicas_sha256": sha256(REPLICAS) if REPLICAS.is_file() else None,
        "components": rel(COMPONENTS),
        "components_sha256": sha256(COMPONENTS) if COMPONENTS.is_file() else None,
        "replica_rows": len(rows),
        "primary_seed": PRIMARY_SEED,
        "seed_stride": SEED_STRIDE,
        "branch_self_test": branch_self_test,
        "recomputed_metrics": recomputed_metrics,
        "recomputed_delayed_family_metrics": recomputed_families,
        "problems": problems,
    }
    VALIDATION.parent.mkdir(parents=True, exist_ok=True)
    VALIDATION.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    payload = validate()
    print(json.dumps({"status": payload["status"], "problems": payload["problems"]}, indent=2))
    return 0 if payload["status"] == VALIDATION_PASS else 2


if __name__ == "__main__":
    raise SystemExit(main())
