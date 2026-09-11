#!/usr/bin/env python3
"""Trace the 418 denominator-closed delayed annihilation siblings in BG-J4.

This is a straight-ray geometry calculation, not particle transport and not a
veto-efficiency estimate.  It preserves every selected event weight, exposes
relief rays explicitly, and reports low-Neff/high-weight rows individually.
"""

from __future__ import annotations

import argparse
import csv
import math
import subprocess
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
EVENTS = (
    HERE.parent
    / "delayed"
    / "delayed_annihilation_sibling_events.csv"
)
TRACER = (
    REPO
    / "engineering/s3d_o8_loop_engineering_20260814/agents/prompt/"
    "trace_true_geometry_rays"
)
DEFAULT_SETUP = (
    HERE
    / "bg_j4_proxy"
    / "S3D_O8_BG_J4_fullwrap_BGO4cm_proxy.geo.setup"
)

SIDE_BGO = "BGO_S3C_FullWrap_SideShell_WindowCut_40mm"
BOTTOM_BGO = "BGO_S3D_O8_FullWrap_BottomCap_30mm"
TOP_BGO = "BGO_S3D_O8_FullWrap_TopAnnulus_10mm"
BGO = {SIDE_BGO, BOTTOM_BGO, TOP_BGO}
PLASTIC = {
    "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm",
    "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm",
    "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm",
}


def read_events() -> list[dict[str, str]]:
    with EVENTS.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    traceable = [row for row in rows if int(row["traceable_sibling"])]
    if len(rows) != 420 or len(traceable) != 418:
        raise RuntimeError(f"unexpected delayed denominator: all={len(rows)} traceable={len(traceable)}")
    return traceable


def trace(setup: Path, events: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    by_id: dict[str, dict[str, str]] = {}
    feed: list[str] = []
    for index, event in enumerate(events):
        ray_id = f"r{index:04d}"
        by_id[ray_id] = event
        feed.append(
            " ".join(
                [
                    ray_id,
                    event["annihilation_world_x_cm"],
                    event["annihilation_world_y_cm"],
                    event["annihilation_world_z_cm"],
                    event["sibling_world_dx"],
                    event["sibling_world_dy"],
                    event["sibling_world_dz"],
                    "60",
                    "0.01",
                ]
            )
        )
    proc = subprocess.run(
        [str(TRACER), str(setup)],
        input="\n".join(feed) + "\n",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    header: list[str] | None = None
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for line in proc.stdout.splitlines():
        if line.startswith("ray_id,"):
            header = next(csv.reader([line]))
        elif line.startswith("r") and header is not None:
            values = next(csv.reader([line]))
            segment = dict(zip(header, values))
            grouped[segment["ray_id"]].append(segment)
    if set(grouped) != set(by_id):
        raise RuntimeError(f"ray closure failed: traced={len(grouped)} expected={len(by_id)}")
    return grouped


def effective_n(weights: list[float]) -> float:
    if not weights:
        return 0.0
    numerator = sum(weights) ** 2
    denominator = sum(weight * weight for weight in weights)
    return numerator / denominator if denominator else 0.0


def summarize(label: str, selected: list[dict[str, object]], all_rows: list[dict[str, object]]) -> dict[str, object]:
    static = [float(row["event_weight_cps"]) for row in selected]
    mission = [float(row["mission_counts_20d_baseline_live"]) for row in selected]
    all_static = sum(float(row["event_weight_cps"]) for row in all_rows)
    all_mission = sum(float(row["mission_counts_20d_baseline_live"]) for row in all_rows)
    mission_sum = sum(mission)
    return {
        "metric": label,
        "denominator_rows": len(all_rows),
        "numerator_rows": len(selected),
        "row_fraction": len(selected) / len(all_rows),
        "denominator_static_cps": all_static,
        "numerator_static_cps": sum(static),
        "static_cps_fraction": sum(static) / all_static,
        "denominator_mission_counts_20d": all_mission,
        "numerator_mission_counts_20d": mission_sum,
        "mission_count_fraction": mission_sum / all_mission,
        "numerator_mission_Neff": effective_n(mission),
        "dominant_event_fraction_of_numerator_mission_counts": (
            max(mission) / mission_sum if mission_sum else 0.0
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--setup", type=Path, default=DEFAULT_SETUP)
    parser.add_argument("--output-dir", type=Path, default=HERE)
    args = parser.parse_args()

    events = read_events()
    grouped = trace(args.setup, events)
    results: list[dict[str, object]] = []
    for index, event in enumerate(events):
        ray_id = f"r{index:04d}"
        segments = sorted(grouped[ray_id], key=lambda row: int(row["segment_index"]))
        chords: dict[str, float] = defaultdict(float)
        for segment in segments:
            chords[segment["deepest_volume"]] += float(segment["path_cm"])
        candidate_side = chords[SIDE_BGO]
        candidate_bottom = chords[BOTTOM_BGO]
        candidate_top = chords[TOP_BGO]
        candidate_total = candidate_side + candidate_bottom + candidate_top
        baseline_side = float(event["ray_side_BGO_chord_cm"])
        baseline_bottom = float(event["ray_bottom_BGO_chord_cm"])
        baseline_top = float(event["ray_top_BGO_chord_cm"])
        baseline_total = baseline_side + baseline_bottom + baseline_top
        added = candidate_total - baseline_total
        first_active = next(
            (segment["deepest_volume"] for segment in segments if segment["deepest_volume"] in BGO | PLASTIC),
            "NONE",
        )
        bgo_volumes = [volume for volume in (SIDE_BGO, BOTTOM_BGO, TOP_BGO) if chords[volume] > 1e-8]
        result: dict[str, object] = {
            "ray_id": ray_id,
            "family": event["family"],
            "local_event_id": event["local_event_id"],
            "source_parent_ZA": event["source_parent_ZA"],
            "source_volume": event["source_volume"],
            "source_component_group": event["source_component_group"],
            "event_weight_cps": event["event_weight_cps"],
            "mission_counts_20d_baseline_live": event["mission_counts_20d_baseline_live"],
            "annihilation_world_x_cm": event["annihilation_world_x_cm"],
            "annihilation_world_y_cm": event["annihilation_world_y_cm"],
            "annihilation_world_z_cm": event["annihilation_world_z_cm"],
            "sibling_world_dx": event["sibling_world_dx"],
            "sibling_world_dy": event["sibling_world_dy"],
            "sibling_world_dz": event["sibling_world_dz"],
            "baseline_BGO_chord_cm": baseline_total,
            "candidate_side_BGO_chord_cm": candidate_side,
            "candidate_bottom_BGO_chord_cm": candidate_bottom,
            "candidate_top_BGO_chord_cm": candidate_top,
            "candidate_total_BGO_chord_cm": candidate_total,
            "added_BGO_chord_cm": added,
            "meets_added_4cm": int(added >= 3.999),
            "relief_or_aperture_added_lt4cm": int(added < 3.999),
            "candidate_first_active_volume": first_active,
            "candidate_BGO_volumes": "|".join(bgo_volumes) if bgo_volumes else "NONE",
        }
        results.append(result)

    if any(float(row["added_BGO_chord_cm"]) < -1e-5 for row in results):
        raise RuntimeError("candidate unexpectedly removes baseline BGO chord")

    covered = [row for row in results if int(row["meets_added_4cm"])]
    relief = [row for row in results if int(row["relief_or_aperture_added_lt4cm"])]
    candidate_any = [row for row in results if float(row["candidate_total_BGO_chord_cm"]) > 1e-8]
    baseline_any = [row for row in results if float(row["baseline_BGO_chord_cm"]) > 1e-8]
    summaries = [
        summarize("baseline_any_BGO_chord / traceable418", baseline_any, results),
        summarize("BG_J4_any_BGO_chord / traceable418", candidate_any, results),
        summarize("BG_J4_added_BGO_chord_ge4cm / traceable418", covered, results),
        summarize("BG_J4_relief_or_aperture_added_lt4cm / traceable418", relief, results),
    ]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    event_path = args.output_dir / "BG_J4_DELAYED_SIBLING_CHORDS.csv"
    with event_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    summary_path = args.output_dir / "BG_J4_DELAYED_RELIEF_DENOMINATOR.csv"
    with summary_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    hotspot_path = args.output_dir / "BG_J4_DELAYED_RELIEF_HOTSPOTS.csv"
    relief_sorted = sorted(
        relief,
        key=lambda row: float(row["mission_counts_20d_baseline_live"]),
        reverse=True,
    )
    with hotspot_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(relief_sorted)
    relief_segment_path = args.output_dir / "BG_J4_DELAYED_RELIEF_SEGMENTS.csv"
    relief_ids = {str(row["ray_id"]) for row in relief}
    relief_segments: list[dict[str, object]] = []
    result_by_id = {str(row["ray_id"]): row for row in results}
    for ray_id in sorted(relief_ids):
        for segment in sorted(grouped[ray_id], key=lambda row: int(row["segment_index"])):
            item: dict[str, object] = {
                "family": result_by_id[ray_id]["family"],
                "local_event_id": result_by_id[ray_id]["local_event_id"],
                "mission_counts_20d_baseline_live": result_by_id[ray_id]["mission_counts_20d_baseline_live"],
            }
            item.update(segment)
            relief_segments.append(item)
    with relief_segment_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(relief_segments[0]))
        writer.writeheader()
        writer.writerows(relief_segments)

    print(f"traceable_rows={len(results)}")
    print(f"covered_added_ge4cm_rows={len(covered)}")
    print(f"relief_added_lt4cm_rows={len(relief)}")
    print(f"minimum_added_BGO_chord_cm={min(float(row['added_BGO_chord_cm']) for row in results):.12g}")
    print(f"event_output={event_path}")
    print(f"summary_output={summary_path}")
    print(f"hotspot_output={hotspot_path}")
    print(f"relief_segment_output={relief_segment_path}")


if __name__ == "__main__":
    main()
