#!/usr/bin/env python3
"""Audit DetectorTimeConstant and static short-half-life risk for source v2."""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any


getcontext().prec = 80

PHASE_DIR = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
OUT = PHASE_DIR / "06_time_constant"

INVENTORY = PHASE_DIR / "01_raw_inventory/raw_inventory_all_states.csv"
WP04_SOURCE = PHASE_DIR / "04_custom_source_v2/source_v2_eventlist.source"
WP05_NATIVE_SOURCE = PHASE_DIR / "05_native_activation/native_activation_sources_probe.source"
WP05_SYN_SOURCE = PHASE_DIR / "05_native_activation/synthetic_activator.source"
WP05_SUMMARY = PHASE_DIR / "05_native_activation/summary.json"

DTC_AUDIT = OUT / "detector_time_constant_audit.json"
RISK_CSV = OUT / "static_lifetime_risk.csv"
RISK_SUMMARY = OUT / "static_lifetime_risk_summary.json"
AUTH_JSON = OUT / "timing_authority.json"
AUTH_MD = OUT / "timing_authority.md"
SUMMARY_JSON = OUT / "summary.json"
SUMMARY_MD = OUT / "summary.md"

BETA_PLUS_HEURISTIC = {
    "C-11",
    "N-13",
    "O-14",
    "O-15",
    "F-18",
    "Na-22",
    "Al-26",
    "Sc-44",
    "V-48",
    "Mn-52",
    "Co-56",
    "Cu-64",
    "Ga-68",
}


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def dec(text: str | Decimal | None) -> Decimal:
    if isinstance(text, Decimal):
        return text
    if text is None or text == "":
        return Decimal(0)
    return Decimal(str(text))


def fmt_dec(value: Decimal) -> str:
    return format(value.normalize(), "f") if value else "0"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_dtc(path: Path) -> list[str]:
    if not path.exists():
        return []
    values: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"\s*DetectorTimeConstant\s+(\S+)", line)
        if m:
            values.append(m.group(1))
    return values


def half_life_bin(hl: Decimal) -> str:
    if hl <= 0:
        return "unknown_or_zero"
    if hl < Decimal("1e-9"):
        return "lt_1ns"
    if hl < Decimal("1e-7"):
        return "1ns_100ns"
    if hl < Decimal("1e-6"):
        return "100ns_1us"
    if hl < Decimal("5e-6"):
        return "1us_5us"
    return "gt_5us"


def is_near_focal(volume: str) -> bool:
    markers = [
        "TES",
        "Pixel",
        "Si_Substrate",
        "ColdPlate_4K",
        "detector_bay",
        "Detector",
    ]
    return any(marker in volume for marker in markers)


def build_static_risk() -> dict[str, Any]:
    rows_out: list[dict[str, str]] = []
    activity_by_bin: dict[str, Decimal] = defaultdict(Decimal)
    keys_by_bin: dict[str, int] = defaultdict(int)
    near_focal_by_bin: dict[str, Decimal] = defaultdict(Decimal)
    beta_plus_by_bin: dict[str, Decimal] = defaultdict(Decimal)
    total = Decimal(0)
    with INVENTORY.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            activity = dec(row["activity_day15_direct_Bq"])
            if activity <= 0:
                continue
            hl = dec(row["half_life_s"])
            b = half_life_bin(hl)
            volume = row["raw_volume"]
            near = is_near_focal(volume)
            beta = row["nuclide"] in BETA_PLUS_HEURISTIC
            total += activity
            activity_by_bin[b] += activity
            keys_by_bin[b] += 1
            if near:
                near_focal_by_bin[b] += activity
            if beta:
                beta_plus_by_bin[b] += activity
            rows_out.append(
                {
                    "production_tag": row["production_tag"],
                    "raw_volume": volume,
                    "canonical_volume_for_reporting_only": row["canonical_volume_for_reporting_only"],
                    "ZA": row["ZA"],
                    "nuclide": row["nuclide"],
                    "exc_keV_decimal": row["exc_keV_decimal"],
                    "state_id": row["state_id"],
                    "activity_day15_direct_Bq": fmt_dec(activity),
                    "half_life_s": fmt_dec(hl),
                    "half_life_bin": b,
                    "near_focal_plane_heuristic": str(near),
                    "beta_plus_relevant_heuristic": str(beta),
                    "line_or_cascade_risk_status": "BETA_PLUS_HEURISTIC" if beta else "UNASSESSED_NATIVE_DECAY_TABLE_REQUIRED",
                }
            )
    with RISK_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "production_tag",
                "raw_volume",
                "canonical_volume_for_reporting_only",
                "ZA",
                "nuclide",
                "exc_keV_decimal",
                "state_id",
                "activity_day15_direct_Bq",
                "half_life_s",
                "half_life_bin",
                "near_focal_plane_heuristic",
                "beta_plus_relevant_heuristic",
                "line_or_cascade_risk_status",
            ],
        )
        writer.writeheader()
        writer.writerows(rows_out)
    short_bins = ["1ns_100ns", "100ns_1us", "1us_5us"]
    short_activity = sum((activity_by_bin[b] for b in short_bins), Decimal(0))
    payload = {
        "status": "PASS" if short_activity == 0 else "WARN_TIMING_SENSITIVE",
        "positive_key_count": len(rows_out),
        "total_activity_Bq": fmt_dec(total),
        "activity_by_half_life_bin_Bq": {k: fmt_dec(v) for k, v in sorted(activity_by_bin.items())},
        "keys_by_half_life_bin": dict(sorted(keys_by_bin.items())),
        "near_focal_activity_by_half_life_bin_Bq": {k: fmt_dec(v) for k, v in sorted(near_focal_by_bin.items())},
        "beta_plus_heuristic_activity_by_half_life_bin_Bq": {k: fmt_dec(v) for k, v in sorted(beta_plus_by_bin.items())},
        "short_1ns_to_5us_activity_Bq": fmt_dec(short_activity),
        "risk_csv": rel(RISK_CSV),
        "line_or_cascade_boundary": "heuristic only; full cascade/511 risk requires native decay-table or transport evidence",
    }
    write_json(RISK_SUMMARY, payload)
    return payload


def audit_dtc() -> dict[str, Any]:
    cards = [WP04_SOURCE, WP05_NATIVE_SOURCE, WP05_SYN_SOURCE]
    card_values = {rel(path): parse_dtc(path) for path in cards}
    all_values = [value for values in card_values.values() for value in values]
    unique = sorted(set(all_values))
    payload = {
        "status": "PASS" if unique == ["1e-9"] and all(len(v) == 1 for v in card_values.values()) else "FAIL_TIMING_AUTHORITY",
        "expected_detector_time_constant_s": "1e-9",
        "source_card_values": card_values,
        "unique_values": unique,
    }
    write_json(DTC_AUDIT, payload)
    return payload


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    wp05 = json.loads(WP05_SUMMARY.read_text(encoding="utf-8"))
    dtc = audit_dtc()
    risk = build_static_risk()
    status = "TIME_CONSTANT_STABLE"
    problems: list[str] = []
    if dtc["status"] != "PASS":
        status = "FAIL_TIMING_AUTHORITY"
        problems.append("detector_time_constant_mismatch")
    if risk["status"] != "PASS":
        status = "TIMING_SENSITIVITY_UNRESOLVED"
        problems.append("short_half_life_activity_present")

    authority = {
        "status": status,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "timing_authority_s": "1e-9" if status == "TIME_CONSTANT_STABLE" else "",
        "detector_time_constant_audit": rel(DTC_AUDIT),
        "static_lifetime_risk_summary": rel(RISK_SUMMARY),
        "wp05_native_oracle_status": wp05.get("status"),
        "decay_chain_boundary": "WP05 tag-aware native oracle shows an explained model difference; no headline rate promotion from G6 alone",
        "problems": problems,
    }
    write_json(AUTH_JSON, authority)
    AUTH_MD.write_text(
        "\n".join(
            [
                "# Timing Authority",
                "",
                f"status: `{status}`",
                "",
                f"- timing authority: `{authority['timing_authority_s'] or 'unresolved'}` seconds",
                f"- source cards audited: `{len(dtc['source_card_values'])}`",
                f"- unique DetectorTimeConstant values: `{', '.join(dtc['unique_values'])}`",
                f"- positive activity in 1 ns--5 us bins: `{risk['short_1ns_to_5us_activity_Bq']}` Bq",
                f"- WP05 native oracle status: `{wp05.get('status')}`",
                "",
                "Boundary:",
                "- This is a source-level timing stability decision.",
                "- WP05 tag-aware native Activator shows an explained model difference; transport and Step05 ingestion remain required for rates.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    summary = {
        "status": status,
        "outputs": [
            rel(AUTH_JSON),
            rel(AUTH_MD),
            rel(DTC_AUDIT),
            rel(RISK_SUMMARY),
            rel(RISK_CSV),
            rel(SUMMARY_MD),
        ],
        "findings": [
            f"Unique DetectorTimeConstant values: {', '.join(dtc['unique_values'])}.",
            f"Positive activity in 1 ns--5 us bins: {risk['short_1ns_to_5us_activity_Bq']} Bq.",
            f"WP05 native oracle status remains {wp05.get('status')}.",
        ],
        "next_gate": "G7 pilot transport/resource plan; no promotion until native limitation is resolved or accepted",
        "user_decision_required": False,
    }
    write_json(SUMMARY_JSON, summary)
    SUMMARY_MD.write_text(
        "\n".join(
            [
                "# WP06 DetectorTimeConstant Summary",
                "",
                f"status: `{status}`",
                "",
                f"- timing authority: `{authority['timing_authority_s'] or 'unresolved'}` seconds",
                f"- short 1 ns--5 us activity Bq: `{risk['short_1ns_to_5us_activity_Bq']}`",
                f"- positive keys: `{risk['positive_key_count']}`",
                f"- WP05 native oracle: `{wp05.get('status')}`",
                "",
                f"Timing authority file: `{rel(AUTH_JSON)}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"WP06 {status}")
    print(json.dumps(authority, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
