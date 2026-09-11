#!/usr/bin/env python3
"""Replay W2 veto response with plastic skin at 20 keV and legacy active at 50 keV."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
BASE_DIR = ROOT / "engineering/geometry_optimization_20260704/17_s2b_eqstats_prompt_atm511_20260708"
EVENT_CSV = BASE_DIR / "w2_veto_failure_fast_events.csv"
BASELINE_JSON = BASE_DIR / "s2b_eqstats_background_comparison_summary.json"

PLASTIC_THRESHOLD_KEV = 20.0
LEGACY_ACTIVE_THRESHOLD_KEV = 50.0


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def as_float(value: str) -> float:
    return float(value) if value else 0.0


def as_bool(value: str) -> bool:
    return value == "True"


def load_rate_weights() -> dict[tuple[str, str], dict[str, float]]:
    baseline = json.loads(BASELINE_JSON.read_text(encoding="utf-8"))
    out: dict[tuple[str, str], dict[str, float]] = {}
    for row in baseline["comparison_rows"]:
        if row["stage"] != "raw":
            continue
        particle = row["component"]
        for geometry in ("s1", "s2b"):
            events = int(row[f"{geometry}_events"])
            rate = float(row[f"{geometry}_rate_cps"])
            out[(geometry.upper() if geometry == "s1" else "S2b", particle)] = {
                "raw_events": events,
                "raw_rate_cps": rate,
                "rate_per_raw_event_cps": rate / events if events else 0.0,
            }
    return out


def poisson_ratio_sigma(num_events: int, den_events: int, value: float | None) -> float | None:
    if value is None or num_events <= 0 or den_events <= 0:
        return None
    return value * math.sqrt(1.0 / num_events + 1.0 / den_events)


def summarize() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows = read_csv(EVENT_CSV)
    weights = load_rate_weights()
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["geometry"], row["particle"])].append(row)

    summary_rows: list[dict[str, Any]] = []
    final_event_rows: list[dict[str, Any]] = []
    by_case: dict[str, Any] = {}

    for key in sorted(grouped):
        geometry, particle = key
        case_rows = grouped[key]
        weight = weights[key]["rate_per_raw_event_cps"]

        active_pass = []
        final_pass = []
        veto_reasons = Counter()
        class_counts = Counter()
        final_class_counts = Counter()
        final_tes_hits = Counter()
        final_plastic_bins = Counter()
        final_legacy_bins = Counter()

        for row in case_rows:
            legacy = as_float(row["legacy_active_keV"])
            plastic = as_float(row["plastic_skin_keV"])
            legacy_veto = legacy >= LEGACY_ACTIVE_THRESHOLD_KEV
            plastic_veto = plastic >= PLASTIC_THRESHOLD_KEV
            active_veto = legacy_veto or plastic_veto
            compton_veto = as_bool(row["compton_fov_veto"])
            cls = row["side_compton_class"]
            class_counts[cls] += 1

            if plastic_veto:
                veto_reasons["plastic20_veto"] += 1
                continue
            if legacy_veto:
                veto_reasons["legacy50_veto_no_plastic20"] += 1
                continue
            active_pass.append(row)
            if compton_veto:
                veto_reasons["compton_fov_veto_after_active_pass"] += 1
                continue

            veto_reasons["final_pass"] += 1
            final_pass.append(row)
            final_class_counts[cls] += 1
            final_tes_hits[int(row["tes_hit_count"])] += 1
            if plastic == 0.0:
                final_plastic_bins["zero"] += 1
            elif plastic < PLASTIC_THRESHOLD_KEV:
                final_plastic_bins["gt0_lt20"] += 1
            else:
                final_plastic_bins["ge20"] += 1
            if legacy == 0.0:
                final_legacy_bins["zero"] += 1
            elif legacy < LEGACY_ACTIVE_THRESHOLD_KEV:
                final_legacy_bins["gt0_lt50"] += 1
            else:
                final_legacy_bins["ge50"] += 1

            out = dict(row)
            out["plastic_threshold_keV"] = PLASTIC_THRESHOLD_KEV
            out["legacy_active_threshold_keV"] = LEGACY_ACTIVE_THRESHOLD_KEV
            out["replayed_final_rate_cps"] = weight
            final_event_rows.append(out)

        summary = {
            "geometry": geometry,
            "particle": particle,
            "raw_events": len(case_rows),
            "active_pass_events": len(active_pass),
            "final_pass_events": len(final_pass),
            "raw_rate_cps": len(case_rows) * weight,
            "active_pass_rate_cps": len(active_pass) * weight,
            "final_pass_rate_cps": len(final_pass) * weight,
            "plastic20_veto_events": veto_reasons["plastic20_veto"],
            "legacy50_veto_no_plastic20_events": veto_reasons["legacy50_veto_no_plastic20"],
            "compton_fov_veto_after_active_pass_events": veto_reasons["compton_fov_veto_after_active_pass"],
            "raw_side_compton_class_counts": dict(sorted(class_counts.items())),
            "final_side_compton_class_counts": dict(sorted(final_class_counts.items())),
            "final_tes_hit_count_counts": dict(sorted(final_tes_hits.items())),
            "final_plastic_bins": dict(sorted(final_plastic_bins.items())),
            "final_legacy_bins": dict(sorted(final_legacy_bins.items())),
        }
        by_case[f"{geometry}_{particle}"] = summary
        summary_rows.append(summary)

    compare_rows = []
    for particle in ("eplus", "n", "atm511"):
        s1 = by_case.get(f"S1_{particle}")
        s2b = by_case.get(f"S2b_{particle}")
        if not s1 or not s2b:
            continue
        for stage, events_key, rate_key in (
            ("raw", "raw_events", "raw_rate_cps"),
            ("active_veto_pass", "active_pass_events", "active_pass_rate_cps"),
            ("side_compton_fov_pass", "final_pass_events", "final_pass_rate_cps"),
        ):
            s1_events = int(s1[events_key])
            s2b_events = int(s2b[events_key])
            s1_rate = float(s1[rate_key])
            s2b_rate = float(s2b[rate_key])
            ratio = s2b_rate / s1_rate if s1_rate > 0.0 else None
            compare_rows.append(
                {
                    "component": particle,
                    "stage": stage,
                    "s1_events": s1_events,
                    "s2b_events": s2b_events,
                    "s1_rate_cps": s1_rate,
                    "s2b_rate_cps": s2b_rate,
                    "s2b_over_s1_ratio": "" if ratio is None else ratio,
                    "counting_only_1sigma": "" if ratio is None else poisson_ratio_sigma(s2b_events, s1_events, ratio),
                }
            )

    payload = {
        "status": "PASS_PLASTIC20_LEGACY50_W2_REPLAY",
        "inputs": {
            "event_csv": str(EVENT_CSV.relative_to(ROOT)),
            "baseline_json": str(BASELINE_JSON.relative_to(ROOT)),
        },
        "thresholds": {
            "plastic_skin_keV": PLASTIC_THRESHOLD_KEV,
            "legacy_active_keV": LEGACY_ACTIVE_THRESHOLD_KEV,
            "active_veto_rule": "plastic_skin_keV >= 20 OR legacy_active_keV >= 50",
            "compton_fov_rule": "unchanged from existing side_compton_class; veto only class == veto",
        },
        "case_summaries": by_case,
        "comparison_rows": compare_rows,
    }
    return summary_rows, compare_rows, payload


def main() -> None:
    summary_rows, compare_rows, payload = summarize()
    summary_fields = [
        "geometry",
        "particle",
        "raw_events",
        "active_pass_events",
        "final_pass_events",
        "raw_rate_cps",
        "active_pass_rate_cps",
        "final_pass_rate_cps",
        "plastic20_veto_events",
        "legacy50_veto_no_plastic20_events",
        "compton_fov_veto_after_active_pass_events",
        "raw_side_compton_class_counts",
        "final_side_compton_class_counts",
        "final_tes_hit_count_counts",
        "final_plastic_bins",
        "final_legacy_bins",
    ]
    compare_fields = [
        "component",
        "stage",
        "s1_events",
        "s2b_events",
        "s1_rate_cps",
        "s2b_rate_cps",
        "s2b_over_s1_ratio",
        "counting_only_1sigma",
    ]
    write_csv(WORK / "plastic20_legacy50_w2_case_summary.csv", summary_rows, summary_fields)
    write_csv(WORK / "plastic20_legacy50_w2_comparison.csv", compare_rows, compare_fields)
    (WORK / "plastic20_legacy50_w2_summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Plastic20 Legacy50 W2 Replay",
        "",
        f"- Plastic skin veto threshold: `{PLASTIC_THRESHOLD_KEV:g} keV`.",
        f"- Legacy active/CsI/BGO threshold: `{LEGACY_ACTIVE_THRESHOLD_KEV:g} keV`.",
        "- Transport and Compton/FoV classification are unchanged; this is a W2 event-level replay.",
        "",
        "| component | stage | S1 events | S2b events | S1 cps | S2b cps | S2b/S1 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in compare_rows:
        ratio = row["s2b_over_s1_ratio"]
        ratio_s = "" if ratio == "" else f"{float(ratio):.6g}"
        lines.append(
            f"| {row['component']} | {row['stage']} | {row['s1_events']} | {row['s2b_events']} | "
            f"{float(row['s1_rate_cps']):.8g} | {float(row['s2b_rate_cps']):.8g} | {ratio_s} |"
        )
    lines.extend(
        [
            "",
            "## S2b Final-Pass Diagnostics",
            "",
            "| particle | raw | active pass | final | plastic20 veto | legacy50 veto | Compton/FoV veto | final plastic bins |",
            "|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for particle in ("eplus", "n", "atm511"):
        rec = payload["case_summaries"][f"S2b_{particle}"]
        lines.append(
            f"| {particle} | {rec['raw_events']} | {rec['active_pass_events']} | {rec['final_pass_events']} | "
            f"{rec['plastic20_veto_events']} | {rec['legacy50_veto_no_plastic20_events']} | "
            f"{rec['compton_fov_veto_after_active_pass_events']} | `{rec['final_plastic_bins']}` |"
        )
    (WORK / "plastic20_legacy50_w2_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "outputs": [p.name for p in WORK.iterdir()]}, indent=2))


if __name__ == "__main__":
    main()
