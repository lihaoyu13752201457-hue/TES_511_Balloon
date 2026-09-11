#!/usr/bin/env python3
"""Independent read-only validator for the S3c atm511 Knob0 replay."""

from __future__ import annotations

import csv
import gzip
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
WORK = Path(__file__).resolve().parents[1]
DATA = WORK / "data"
REPORT = WORK / "report"
RUN = ROOT / "runs/geometry_optimization_20260704/s3c_bgo_w2mm_al3mm_shell_atm511_sidecar_3m_20260709"
RUN_NAME = "Atm511SidecarS3cBgoW2mmAl3mmShell3M"
SIM = RUN / f"{RUN_NAME}.inc1.id1.sim.gz"
SOURCE = RUN / f"{RUN_NAME}.source"
CURRENT = ROOT / "engineering/geometry_optimization_20260704/32_s3c_dominant_backgrounds_20260709/s3c_atm511_sidecar_3m_summary.json"
EXPECTED_GEOMETRY = ROOT / (
    "engineering/geometry_optimization_20260704/29_geoopt_s3c_bgo_w2mm_al3mm_shell_20260709/geometry/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
BRIEF = ROOT / "engineering/compton_veto_knob0_20260710/KNOB0_FLUORESCENCE_ARM_STRATIFICATION_BRIEF.md"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def norm(value: str | Path | None) -> str | None:
    if value is None:
        return None
    path = Path(str(value).strip())
    if not path.is_absolute():
        path = ROOT / path
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def sim_geometry() -> str | None:
    with gzip.open(SIM, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if line.startswith("Geometry"):
                return line.split(None, 1)[1]
            if line == "SE":
                break
    return None


def source_geometry() -> str | None:
    for raw in SOURCE.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line.startswith("Geometry"):
            return line.split(None, 1)[1]
    return None


def wilson(successes: int, trials: int, z: float = 1.959963984540054) -> tuple[float, float]:
    p = successes / trials
    denom = 1.0 + z * z / trials
    center = (p + z * z / (2.0 * trials)) / denom
    half = z / denom * math.sqrt(p * (1.0 - p) / trials + z * z / (4.0 * trials * trials))
    return max(0.0, center - half), min(1.0, center + half)


def check(condition: bool, message: str, problems: list[str]) -> bool:
    if not condition:
        problems.append(message)
    return condition


def main() -> int:
    problems: list[str] = []
    checks: dict[str, Any] = {}
    required = [
        SIM,
        SOURCE,
        CURRENT,
        DATA / "s3c_atm511_knob0_summary.json",
        DATA / "s3c_atm511_w2_event_truth.json",
        DATA / "s3c_atm511_w2_event_audit.csv",
        DATA / "s3c_atm511_knob0_policy_yields.csv",
        DATA / "s3c_atm511_knob0_transitions.csv",
        DATA / "s3c_atm511_knob0_chart_map.json",
        REPORT / "s3c_atm511_knob0_report.html",
        REPORT / "s3c_atm511_knob0_report_payload.json",
        REPORT / "s3c_atm511_knob0_report_qa.json",
        WORK / "README.md",
        BRIEF,
    ]
    missing = [path.relative_to(ROOT).as_posix() for path in required if not path.exists()]
    check(not missing, f"required artifacts missing: {missing}", problems)
    if missing:
        print(json.dumps({"status": "FAIL", "problems": problems}, indent=2, ensure_ascii=False))
        return 2

    summary = load_json(DATA / "s3c_atm511_knob0_summary.json")
    truth = load_json(DATA / "s3c_atm511_w2_event_truth.json")
    audit = load_csv(DATA / "s3c_atm511_w2_event_audit.csv")
    yields = load_csv(DATA / "s3c_atm511_knob0_policy_yields.csv")
    transitions = load_csv(DATA / "s3c_atm511_knob0_transitions.csv")
    current = load_json(CURRENT)["windows"]["w2_510p58_511p42"]
    expected_geo = norm(EXPECTED_GEOMETRY)

    geometry_ok = norm(sim_geometry()) == expected_geo and norm(source_geometry()) == expected_geo
    check(geometry_ok, "source/SIM geometry does not match retained S3c geometry", problems)
    checks["geometry"] = {"ok": geometry_ok, "expected": expected_geo}

    reproduction_ok = (
        summary.get("status") == "PASS_S3C_ATM511_KNOB0_EVENT_REPLAY"
        and all(summary.get("validation", {}).values())
        and len(audit) == 8
        and len(truth) == 8
        and len({row["event_id"] for row in audit}) == 8
        and sum(int(row["current_keep"]) for row in audit) == 6
        and sorted(int(row["event_id"]) for row in audit if row["current_keep"] == "1")
        == sorted(int(value) for value in current["final_event_ids"])
    )
    check(reproduction_ok, "current W2 event selection was not reproduced exactly", problems)
    checks["current_reproduction"] = {"ok": reproduction_ok, "w2_active": len(audit), "w2_final": 6}

    strata = Counter(row["stratum"] for row in audit)
    strata_expected = {
        "single": 3,
        "S0_fluorescence": 1,
        "S1_short": 2,
        "S2_medium": 1,
        "S3_long": 1,
    }
    strata_ok = dict(strata) == strata_expected
    check(strata_ok, f"unexpected W2 strata: {dict(strata)}", problems)

    tagged = [row for row in audit if row["fluorescence_truth_supported"] == "1"]
    tag_ok = (
        len(tagged) == 1
        and tagged[0]["event_id"] == "2547196"
        and tagged[0]["fluorescence_lines"] == "Kalpha1"
        and abs(float(tagged[0]["truth_k_photon_energies_keV"]) - 57.686) < 0.001
    )
    check(tag_ok, "Ta Kalpha1 tag is not uniquely supported by IA truth", problems)
    checks["g1"] = {"strata_ok": strata_ok, "truth_supported_kalpha1": tag_ok}

    long_rows = [row for row in audit if row["stratum"] == "S3_long"]
    long_ok = (
        len(long_rows) == 1
        and long_rows[0]["event_id"] == "426168"
        and float(long_rows[0]["lever_arm_mm"]) >= 20.0
        and float(long_rows[0]["min_cone_to_window_residual_deg"]) < float(long_rows[0]["delta_k2_deg"])
        and all(long_rows[0][f"monotonic_k{k}_keep"] == "1" for k in ("2", "2.5", "3"))
    )
    check(long_ok, "long-arm event does not pass every frozen tight criterion", problems)
    checks["long_arm"] = {"ok": long_ok, "event_id": long_rows[0]["event_id"] if long_rows else None}

    literal_rows = [row for row in yields if row["policy"] == "literal_brief"]
    monotonic_rows = [row for row in yields if row["policy"] == "monotonic_frozen"]
    literal_ok = len(literal_rows) == 3 and all(
        int(row["new_final_events"]) == 7
        and int(row["current_kept_to_rejected"]) == 0
        and int(row["current_rejected_to_kept"]) == 1
        for row in literal_rows
    )
    monotonic_ok = len(monotonic_rows) == 3 and all(
        int(row["new_final_events"]) == 6
        and int(row["current_kept_to_rejected"]) == 0
        and int(row["current_rejected_to_kept"]) == 0
        for row in monotonic_rows
    )
    resurrected_ids = {
        int(row["event_id"])
        for row in transitions
        if row["policy"] == "literal_brief" and row["transition"] == "0->1"
    }
    transition_ok = resurrected_ids == {30621}
    check(literal_ok, "literal policy does not reproduce 6->7 for all k", problems)
    check(monotonic_ok, "monotonic policy is not exactly 6->6 for all k", problems)
    check(transition_ok, f"literal resurrection is not uniquely event 30621: {resurrected_ids}", problems)

    weight = float(summary["normalization"]["event_rate_weight_cps"])
    rate_ok = all(
        abs(float(row["new_atm511_rate_cps"]) - int(row["new_final_events"]) * weight) < 1e-15
        for row in yields
    )
    interval = wilson(0, 6)
    uncertainty_ok = (
        abs(interval[1] - 0.39033428790216534) < 1e-12
        and summary["decision"]["additional_statistics_if_zero_rejections_persist"][
            "current_final_events_required_for_wilson95_upper_le_10pct"
        ]
        == 35
        and summary["decision"]["additional_statistics_if_zero_rejections_persist"][
            "current_final_events_required_for_wilson95_upper_le_5pct"
        ]
        == 73
    )
    check(rate_ok, "weighted rate does not equal event count / observation time", problems)
    check(uncertainty_ok, "Wilson interval/sample-size calculation mismatch", problems)
    checks["policy"] = {
        "literal_6_to_7": literal_ok,
        "monotonic_6_to_6": monotonic_ok,
        "resurrected_event_30621": transition_ok,
        "rates_ok": rate_ok,
        "uncertainty_ok": uncertainty_ok,
    }

    report_html = (REPORT / "s3c_atm511_knob0_report.html").read_text(encoding="utf-8")
    report_payload = load_json(REPORT / "s3c_atm511_knob0_report_payload.json")
    report_qa = load_json(REPORT / "s3c_atm511_knob0_report_qa.json")
    chart_by_id = {chart["id"]: chart for chart in report_payload.get("charts", [])}
    policy_chart_rows = chart_by_id.get("policy-final-events", {}).get("dataset", {}).get("data", [])
    roles = (
        "title",
        "technical-summary",
        "key-findings",
        "scope-data-and-metric-definitions",
        "methodology",
        "limitations-uncertainty-and-robustness-checks",
        "recommended-next-steps",
        "further-questions",
    )
    positions = [report_html.find(f'data-contract-section="{role}"') for role in roles]
    report_ok = (
        len(report_payload.get("charts", [])) == 2
        and [int(row["final_events"]) for row in policy_chart_rows] == [6, 7, 6]
        and report_qa.get("status") == "PASS"
        and all(position >= 0 for position in positions)
        and positions == sorted(positions)
        and not re.findall(r'<(?:script|link)\b[^>]+(?:src|href)=["\']https?://', report_html, re.I)
        and "<!-- DATA_ANALYTICS_HTML_REPORT_RUNTIME -->" not in report_html
        and "{{" not in (REPORT / "s3c_atm511_knob0_report_shell.html").read_text(encoding="utf-8")
    )
    check(report_ok, "technical report payload/self-containment/render QA failed", problems)
    checks["report"] = {"ok": report_ok, "charts": len(report_payload.get("charts", [])), "qa": report_qa.get("status")}

    brief_text = BRIEF.read_text(encoding="utf-8")
    handoff_ok = (
        "PARTIALLY_TESTED_ATM511_NEGATIVE_PROMPT_DELAYED_UNTESTED" in brief_text
        and "6 → 7" in brief_text
        and "6 → 6" in brief_text
        and "PASS_S3C_ATM511_KNOB0_VALIDATION" in (WORK / "README.md").read_text(encoding="utf-8")
    )
    check(handoff_ok, "brief/README does not preserve the validated atm511 decision", problems)
    checks["handoff"] = {"ok": handoff_ok}

    payload = {
        "status": "PASS_S3C_ATM511_KNOB0_VALIDATION" if not problems else "FAIL_S3C_ATM511_KNOB0_VALIDATION",
        "checks": checks,
        "problems": problems,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if not problems else 2


if __name__ == "__main__":
    raise SystemExit(main())
