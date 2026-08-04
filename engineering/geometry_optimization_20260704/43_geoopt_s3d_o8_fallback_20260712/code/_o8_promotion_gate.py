#!/usr/bin/env python3
"""Fail-closed promotion gate shared by the O8 full-chain harnesses.

Only the final, package-local matched screening analysis can promote O8 into
the expensive all-eight-family and delayed-production campaign.  Missing or
partially evaluated screening remains PENDING; a failed gate remains FAIL.
Historical O9 results are never accepted as a substitute.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _o8_replay_common import DATA, rel, sha256


SCREENING_JSON = DATA / "s3d_o8_screening_analysis.json"
EXPECTED_STATUS = "PASS_O8_SCREENING_PROMOTION_GATES"
EXPECTED_GATE_NAMES = ("dominant_subset", "signal")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_screening_promotion() -> dict[str, Any]:
    """Return PASS, PENDING_SCREENING_GATE, or FAIL_SCREENING_GATE evidence."""
    if not SCREENING_JSON.is_file():
        return {
            "status": "PENDING_SCREENING_GATE",
            "authority": rel(SCREENING_JSON),
            "authority_exists": False,
            "expected_status": EXPECTED_STATUS,
            "problems": [],
            "pending": ["final O8 screening JSON is absent"],
            "historical_substitution_allowed": False,
        }

    try:
        payload = _load_json(SCREENING_JSON)
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "FAIL_SCREENING_GATE",
            "authority": rel(SCREENING_JSON),
            "authority_exists": True,
            "expected_status": EXPECTED_STATUS,
            "problems": [f"unreadable screening JSON: {exc}"],
            "pending": [],
            "historical_substitution_allowed": False,
        }

    authority_status = str(payload.get("status", ""))
    gates = payload.get("promotion_gates")
    problems: list[str] = []
    pending: list[str] = []
    if not isinstance(gates, dict):
        problems.append("promotion_gates is absent or not an object")
        gates = {}

    gate_evidence: dict[str, Any] = {}
    for name in EXPECTED_GATE_NAMES:
        row = gates.get(name)
        if not isinstance(row, dict):
            problems.append(f"missing required promotion gate: {name}")
            gate_evidence[name] = {"evaluation_status": None}
            continue
        evaluation = str(row.get("evaluation_status", ""))
        gate_pass = row.get("promotion_gate_pass")
        gate_evidence[name] = {
            "evaluation_status": evaluation,
            "promotion_gate_pass": gate_pass,
        }
        if evaluation == "FAIL" or gate_pass is False:
            problems.append(f"{name} promotion gate failed")
        elif evaluation != "PASS" or gate_pass is not True:
            pending.append(
                f"{name} gate is not fully PASS "
                f"(evaluation_status={evaluation!r}, promotion_gate_pass={gate_pass!r})"
            )

    if gates.get("any_evaluated_gate_failed") is True:
        problems.append("screening records at least one failed evaluated gate")
    if gates.get("all_required_gates_evaluated") is not True:
        pending.append(
            "screening does not record all_required_gates_evaluated=true"
        )
    if gates.get("decision_so_far") != "PASS_ALL_COMPLETED_GATES":
        if "FAIL" in str(gates.get("decision_so_far", "")):
            problems.append(
                f"screening decision={gates.get('decision_so_far')}"
            )
        else:
            pending.append(
                f"screening decision={gates.get('decision_so_far')}"
            )
    if payload.get("audit_failures"):
        problems.append(f"screening audit_failures={payload.get('audit_failures')}")
    if payload.get("pending_inputs"):
        pending.append(f"screening pending_inputs={payload.get('pending_inputs')}")

    if authority_status.startswith("FAIL"):
        problems.append(f"screening status={authority_status}")
    elif authority_status != EXPECTED_STATUS:
        pending.append(
            f"screening status={authority_status!r}; expected {EXPECTED_STATUS}"
        )

    status = (
        "FAIL_SCREENING_GATE"
        if problems
        else "PENDING_SCREENING_GATE"
        if pending
        else "PASS_SCREENING_PROMOTION_GATE"
    )
    return {
        "status": status,
        "authority": rel(SCREENING_JSON),
        "authority_exists": True,
        "authority_sha256": sha256(SCREENING_JSON),
        "authority_status": authority_status,
        "expected_status": EXPECTED_STATUS,
        "gate_evidence": gate_evidence,
        "all_required_gates_evaluated": gates.get(
            "all_required_gates_evaluated"
        ),
        "any_evaluated_gate_failed": gates.get("any_evaluated_gate_failed"),
        "decision_so_far": gates.get("decision_so_far"),
        "problems": problems,
        "pending": pending,
        "historical_substitution_allowed": False,
    }


def require_screening_promotion() -> dict[str, Any]:
    evidence = audit_screening_promotion()
    if evidence["status"] != "PASS_SCREENING_PROMOTION_GATE":
        details = evidence["problems"] or evidence["pending"]
        raise RuntimeError(
            f"{evidence['status']}: " + "; ".join(str(item) for item in details)
        )
    return evidence
