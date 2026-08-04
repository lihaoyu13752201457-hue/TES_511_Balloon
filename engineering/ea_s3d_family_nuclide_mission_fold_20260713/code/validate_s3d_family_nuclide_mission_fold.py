#!/usr/bin/env python3
"""Fail-closed validation of the existing-data S3d mission-fold closure."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parents[1]
SUMMARY = PACKAGE / "data/s3d_family_nuclide_mission_summary.json"
SELECTED = PACKAGE / "data/selected_delayed_nuclides_primary_seed.json"
SCALES = PACKAGE / "data/live_parma_all8_scales_81bins.csv"
TIMELINE = PACKAGE / "outputs/w2_family_nuclide_mission_timeline.csv"
ACTIVITY = PACKAGE / "outputs/nuclide_activity_by_time.csv"
RESPONSE = (
    ROOT
    / "engineering/ea_detector_response_closure_20260713/data/"
    "o8_energy_response_closure_summary.json"
)

PROMPT_TAGS = {
    "alpha",
    "eminus",
    "eplus",
    "gamma",
    "muminus",
    "muplus",
    "n",
    "p",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def close(actual: float, expected: float, label: str, problems: list[str], atol=1e-12):
    if not math.isclose(actual, expected, rel_tol=1e-10, abs_tol=atol):
        problems.append(f"{label}: {actual:.17g} != {expected:.17g}")


def main() -> int:
    required = [SUMMARY, SELECTED, SCALES, TIMELINE, ACTIVITY, RESPONSE]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise SystemExit(f"missing files: {missing}")

    problems: list[str] = []
    summary = load_json(SUMMARY)
    selected = load_json(SELECTED)
    response = load_json(RESPONSE)
    scales = load_csv(SCALES)
    timeline = load_csv(TIMELINE)
    activity = load_csv(ACTIVITY)
    mission = summary["mission"]

    if summary.get("status") != "PASS_S3D_EXISTING_DATA_FAMILY_NUCLIDE_MISSION_CLOSURE":
        problems.append(f"summary status={summary.get('status')!r}")
    if mission.get("status") != "PASS_S3D_W2_FAMILY_NUCLIDE_MISSION_FOLD":
        problems.append(f"mission status={mission.get('status')!r}")
    if selected.get("status") != "PASS_PRIMARY_SEED_DELAYED_NUCLIDE_LINEAGE":
        problems.append(f"delayed-lineage status={selected.get('status')!r}")
    if summary["scope"].get("new_monte_carlo_transport") is not False:
        problems.append("closure is not marked as existing-data-only")
    if summary["scope"].get("day15_response_changed") is not False:
        problems.append("closure incorrectly marks the day-15 response as changed")

    if len(scales) != 81 or len(timeline) != 81:
        problems.append(f"row counts: scales={len(scales)}, timeline={len(timeline)}")
    if not scales or not timeline:
        problems.append("empty trajectory outputs")
    else:
        required_scale_fields = {
            *(f"scale_{tag}" for tag in PROMPT_TAGS),
            *(f"flux_{tag}" for tag in PROMPT_TAGS),
        }
        if not required_scale_fields <= set(scales[0]):
            problems.append("all-eight PARMA scale fields are incomplete")
        for scale, row in zip(scales, timeline):
            if scale["time_bin_id"] != row["time_bin_id"]:
                problems.append("trajectory row ordering differs")
                break

    day15 = next((row for row in timeline if math.isclose(float(row["day_mid"]), 15.0)), None)
    if day15 is None:
        problems.append("day-15 row is absent")
    else:
        rates = mission["day15_selected_rates_cps"]
        close(float(day15["prompt_final_cps_noacc"]), float(rates["prompt"]), "day15 prompt", problems)
        close(float(day15["delayed_final_cps_noacc"]), float(rates["delayed"]), "day15 delayed", problems)
        close(float(day15["atm511_final_cps_noacc"]), float(rates["atm511"]), "day15 atmospheric", problems)
        close(float(day15["signal_final_cps_noacc"]), float(rates["signal"]), "day15 signal", problems)
        for tag in PROMPT_TAGS:
            close(float(day15[f"prompt_scale_{tag}"]), 1.0, f"day15 {tag} scale", problems)

    last = timeline[-1]
    close(float(last["cumulative_source_counts"]), float(mission["source_counts_20d"]), "source counts", problems)
    close(float(last["cumulative_background_counts"]), float(mission["background_counts_20d"]), "background counts", problems)
    z = float(last["cumulative_source_counts"]) / math.sqrt(float(last["cumulative_background_counts"]))
    zc = float(last["cumulative_source_lower95_counts"]) / math.sqrt(
        float(last["cumulative_background_upper95_counts"])
    )
    close(z, float(mission["Z20d"]), "central Z20", problems)
    close(zc, float(mission["Z20d_conservative95"]), "conservative Z20", problems)
    close(1.0e-4 * 3.0 / z, float(mission["flux_3sigma_20d_ph_cm2_s"]), "central flux", problems, 1e-15)
    close(
        1.0e-4 * 3.0 / zc,
        float(mission["flux_3sigma_20d_conservative95_ph_cm2_s"]),
        "conservative flux",
        problems,
        1e-15,
    )

    old_scale_equal = all(
        math.isclose(
            float(row["prompt_family_response_scale"]),
            float(row["prompt_old_scalar"]),
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        for row in timeline
    )
    if old_scale_equal:
        problems.append("family-resolved prompt curve collapsed back to the retired scalar")

    event_ids = [int(value) for value in selected["selected_event_ids"]]
    if len(event_ids) != 29 or len(set(event_ids)) != 29:
        problems.append("selected delayed event IDs are not 29 unique events")
    lineage = Counter(int(value) for value in selected["initial_za_by_event_id"].values())
    declared = {
        int(row["ZA"]): int(row["selected_events"])
        for row in selected["by_nuclide"]
    }
    if dict(lineage) != declared:
        problems.append(f"delayed lineage counts differ: {dict(lineage)} vs {declared}")
    if declared != {29064: 24, 29062: 5}:
        problems.append(f"unexpected selected delayed composition={declared}")
    selected_rate = sum(float(row["day15_selected_rate_cps"]) for row in selected["by_nuclide"])
    close(
        selected_rate,
        float(selected["selected_summary"]["rate_cps"]),
        "selected delayed rate sum",
        problems,
    )

    day15_activity = [row for row in activity if math.isclose(float(row["day_mid"]), 15.0)]
    if len(day15_activity) != int(summary["delayed_nuclide_response"]["nuclides_in_inventory"]):
        problems.append("day-15 activity row count differs from inventory count")
    total_activity = sum(float(row["activity_Bq"]) for row in day15_activity)
    close(
        total_activity,
        float(summary["delayed_nuclide_response"]["day15_total_activity_Bq"]),
        "day15 total activity",
        problems,
        1e-10,
    )

    response_rates = response["primary_authority"]["mission_fold"]["day15_selected_rates_cps"]
    for key in ("prompt", "delayed", "atm511", "background", "signal"):
        close(
            float(mission["day15_selected_rates_cps"][key]),
            float(response_rates[key]),
            f"unchanged day15 {key}",
            problems,
        )

    payload = {
        "status": "PASS_S3D_FAMILY_NUCLIDE_MISSION_VALIDATION" if not problems else "FAIL",
        "checks": {
            "existing_data_only": not summary["scope"]["new_monte_carlo_transport"],
            "trajectory_bins": len(timeline),
            "all_eight_prompt_families": sorted(PROMPT_TAGS),
            "selected_delayed_composition": declared,
            "day15_total_activity_Bq": total_activity,
            "day15_rates_unchanged": not any("unchanged day15" in item for item in problems),
            "retired_scalar_replaced": not old_scale_equal,
            "Z20_recomputed": z,
            "Z20_conservative_recomputed": zc,
        },
        "problems": problems,
    }
    out = PACKAGE / "data/s3d_family_nuclide_mission_validation.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if not problems else 2


if __name__ == "__main__":
    raise SystemExit(main())
