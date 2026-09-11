#!/usr/bin/env python3
"""Independent validator for the geometry-corrected Knob0 test package."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
DATA = PACKAGE / "data"
SUMMARY = DATA / "geometry_corrected_knob0_test_summary.json"
MASS_AUDIT = DATA / "mass_model_511_w2_event_audit.csv"
S3C_AUDIT = DATA / "s3c_atm511_w2_event_audit.csv"
POLICY_YIELDS = DATA / "policy_yields.csv"
SIGNIFICANCE = DATA / "mass_model_511_significance_proxy.csv"
STRATA = DATA / "geometry_current_strata.csv"
TRANSITIONS = DATA / "policy_transitions.csv"
TAGGED = DATA / "tagged_event_audit.csv"
RESULT = DATA / "validation_result.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def close(a: float, b: float, tolerance: float = 1.0e-12) -> bool:
    return math.isclose(float(a), float(b), rel_tol=tolerance, abs_tol=tolerance)


def main() -> int:
    required = [SUMMARY, MASS_AUDIT, S3C_AUDIT, POLICY_YIELDS, SIGNIFICANCE, STRATA, TRANSITIONS, TAGGED]
    problems = [f"missing output: {path}" for path in required if not path.exists()]
    if problems:
        print("\n".join(problems))
        return 1

    summary = load_json(SUMMARY)
    mass = load_csv(MASS_AUDIT)
    s3c = load_csv(S3C_AUDIT)
    all_rows = mass + s3c
    yields = load_csv(POLICY_YIELDS)
    significance = load_csv(SIGNIFICANCE)
    strata = load_csv(STRATA)

    def check(condition: bool, message: str) -> None:
        if not condition:
            problems.append(message)

    check(summary.get("status") == "PASS_GEOMETRY_CORRECTED_KNOB0_ALGORITHM_TEST", "bad summary status")
    check(len(mass) == 30404, f"Mass audit row count {len(mass)} != 30404")
    check(len(s3c) == 8, f"S3c audit row count {len(s3c)} != 8")
    mass_keys = [(row["stream"], row["source_file"], row["event_id"]) for row in mass]
    check(len(mass_keys) == len(set(mass_keys)), "duplicate Mass audit composite event keys")
    check(len({row["event_id"] for row in s3c}) == len(s3c), "duplicate S3c event IDs")

    for label, expected_hash in summary["inputs"]["sha256"].items():
        path_key = {
            "mass_catalog": "mass_catalog",
            "mass_geometry": None,
            "s3c_truth": "s3c_truth",
            "s3c_geometry": None,
        }[label]
        if path_key is not None:
            source = ROOT / summary["inputs"][path_key]
        else:
            geometry_key = "Mass_model_511" if label == "mass_geometry" else "S3c"
            source = ROOT / summary["geometry"][geometry_key]["geometry"]
        check(source.exists(), f"missing hashed input {source}")
        if source.exists():
            check(sha256(source) == expected_hash, f"input hash mismatch: {label}")

    policy_names = [row["policy"] for row in significance]
    check(len(policy_names) == len(set(policy_names)) == 9, "policy list is not nine unique policies")
    candidate_names = [name for name in policy_names if name not in ("legacy_current", "geometry_current")]
    for row in all_rows:
        for policy in candidate_names:
            check(
                not (row["keep__geometry_current"] == "0" and row[f"keep__{policy}"] == "1"),
                f"non-monotonic resurrection {row['dataset']} {row['stream']} {row['event_id']} {policy}",
            )
        if int(row["merge_count"]) > 0:
            check(int(row["cleaned_hit_count"]) < int(row["hit_count"]), f"merge did not reduce hit count: {row['event_id']}")

    yield_lookup = {(row["dataset"], row["stream"], row["policy"]): row for row in yields}
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in all_rows:
        grouped[(row["dataset"], row["stream"])].append(row)
    for (dataset, stream), group in grouped.items():
        for policy in policy_names:
            key = (dataset, stream, policy)
            check(key in yield_lookup, f"missing policy yield {key}")
            if key not in yield_lookup:
                continue
            selected = [row for row in group if row[f"keep__{policy}"] == "1"]
            count = len(selected)
            rate = sum(float(row["rate_hz"]) for row in selected)
            check(count == int(yield_lookup[key]["selected_events"]), f"yield count mismatch {key}")
            check(close(rate, float(yield_lookup[key]["selected_rate_hz"]), 1.0e-11), f"yield rate mismatch {key}")

    expected_legacy = {"prompt": 65, "delayed": 28, "science": 29687}
    expected_geometry = {"prompt": 63, "delayed": 27, "science": 29186}
    for stream, expected in expected_legacy.items():
        check(
            int(yield_lookup[("Mass_model_511", stream, "legacy_current")]["selected_events"]) == expected,
            f"legacy reproduction mismatch for {stream}",
        )
    for stream, expected in expected_geometry.items():
        check(
            int(yield_lookup[("Mass_model_511", stream, "geometry_current")]["selected_events"]) == expected,
            f"geometry-current yield mismatch for {stream}",
        )

    significance_lookup = {row["policy"]: row for row in significance}
    base_s = float(yield_lookup[("Mass_model_511", "science", "geometry_current")]["selected_rate_hz"])
    base_b = sum(
        float(yield_lookup[("Mass_model_511", stream, "geometry_current")]["selected_rate_hz"])
        for stream in ("prompt", "delayed")
    )
    base_z = base_s / math.sqrt(base_b)
    for policy in policy_names:
        signal = float(yield_lookup[("Mass_model_511", "science", policy)]["selected_rate_hz"])
        background = sum(
            float(yield_lookup[("Mass_model_511", stream, policy)]["selected_rate_hz"])
            for stream in ("prompt", "delayed")
        )
        z_proxy = signal / math.sqrt(background)
        row = significance_lookup[policy]
        check(close(signal, float(row["signal_rate_hz"]), 1.0e-11), f"signal mismatch {policy}")
        check(close(background, float(row["prompt_plus_delayed_rate_hz"]), 1.0e-11), f"background mismatch {policy}")
        check(close(z_proxy / base_z, float(row["relative_z_vs_geometry_current"]), 1.0e-11), f"relative Z mismatch {policy}")

    stratum_lookup = {
        (row["dataset"], row["stream"], row["stratum"]): int(row["events"])
        for row in strata
    }
    check(stratum_lookup[("Mass_model_511", "prompt", "S3_long_ge20mm")] == 0, "prompt has unexpected long survivor")
    check(stratum_lookup[("Mass_model_511", "delayed", "S3_long_ge20mm")] == 0, "delayed has unexpected long survivor")
    check(stratum_lookup[("Mass_model_511", "science", "S3_long_ge20mm")] == 934, "signal long survivor count mismatch")

    merge_background_rejections = sum(
        int(yield_lookup[("Mass_model_511", stream, "geometry_fluorescence_merge")]["geometry_current_to_rejected"])
        for stream in ("prompt", "delayed")
    )
    merge_signal_rejections = int(
        yield_lookup[("Mass_model_511", "science", "geometry_fluorescence_merge")]["geometry_current_to_rejected"]
    )
    tight_background_rejections = sum(
        int(yield_lookup[("Mass_model_511", stream, "geometry_tight_k2")]["geometry_current_to_rejected"])
        for stream in ("prompt", "delayed")
    )
    tight_signal_rejections = int(
        yield_lookup[("Mass_model_511", "science", "geometry_tight_k2")]["geometry_current_to_rejected"]
    )
    check((merge_background_rejections, merge_signal_rejections) == (0, 43), "fluorescence mechanism result mismatch")
    check((tight_background_rejections, tight_signal_rejections) == (0, 5), "tight k2 mechanism result mismatch")
    check(
        all(
            int(yield_lookup[("S3c_atm511_3M", "atm511", policy)]["selected_events"]) == 7
            for policy in candidate_names
        ),
        "S3c candidate yield is not uniformly seven",
    )

    s3c_by_id = {int(row["event_id"]): row for row in s3c}
    check(s3c_by_id[30621]["geometry_transition"] == "0->1", "event 30621 geometry transition mismatch")
    check(s3c_by_id[2547196]["merge_count"] == "1", "event 2547196 fluorescence merge missing")
    check(s3c_by_id[426168]["long_arm"] == "1", "event 426168 is not long-arm")

    decision = summary["decision"]
    check(decision["outcome"] == "NO_OBSERVED_KNOB0_ALGORITHM_BENEFIT", "bad decision outcome")
    check(decision["promotion"].startswith("DO_NOT_PROMOTE"), "bad promotion decision")
    check(bool(decision["best_candidate_is_noop"]), "best candidate is not marked no-op")
    check(
        max(float(significance_lookup[name]["relative_z_vs_geometry_current"]) for name in candidate_names) <= 1.0 + 1.0e-12,
        "a candidate unexpectedly improves relative Z",
    )

    result = {
        "status": "PASS_GEOMETRY_CORRECTED_KNOB0_TEST_VALIDATION" if not problems else "FAIL_GEOMETRY_CORRECTED_KNOB0_TEST_VALIDATION",
        "checks": {
            "mass_audit_rows": len(mass),
            "s3c_audit_rows": len(s3c),
            "input_hashes": not any("hash mismatch" in problem for problem in problems),
            "monotonic": not any("resurrection" in problem for problem in problems),
            "legacy_reproduction": not any("legacy reproduction" in problem for problem in problems),
            "policy_reaggregation": not any("yield" in problem and "mismatch" in problem for problem in problems),
            "mechanism_result": (merge_background_rejections, merge_signal_rejections, tight_background_rejections, tight_signal_rejections),
            "decision": decision["outcome"],
        },
        "problems": problems,
    }
    RESULT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
