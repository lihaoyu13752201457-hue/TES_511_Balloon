#!/usr/bin/env python3
"""Completion audit for the HARNESS_20260624 engineering endpoint."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
ENG = Path(__file__).resolve().parents[1]
OUT = ENG / "08_completion_audit"


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except Exception:
        return str(path)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load(path: str) -> Any:
    return json.loads((ENG / path).read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def git_status() -> list[str]:
    proc = subprocess.run(["git", "status", "--short"], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return proc.stdout.splitlines()


def status_item(requirement: str, evidence: str, passed: bool, note: str = "") -> dict[str, Any]:
    return {
        "requirement": requirement,
        "evidence": evidence,
        "status": "PASS" if passed else "FAIL",
        "note": note,
    }


def build() -> dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    g0 = load("00_manifest/baseline_authority_manifest.json")
    g1 = load("01_prompt_source_audit/prompt_normalization_audit.json")
    g2 = load("02_prompt_eplus_provenance/eplus_survivor_provenance.json")
    g3 = load("03_delayed_convergence/delayed_selected_rate_convergence.json")
    g4 = load("04_bgo_variant/bgo_geometry_manifest.json")
    g5 = load("05_matched_runs_resource_guard/summary.json")
    g8 = load("07_manuscript_support/summary.json")
    final_status = (ENG / "FINAL_STATUS.md").read_text(encoding="utf-8")
    support_md = (ENG / "07_manuscript_support/background_validation_necessity_and_paper_impact_final.md").read_text(encoding="utf-8")
    git_lines = git_status()

    tracked_or_authority_mods = [
        line
        for line in git_lines
        if not line.startswith("?? engineering/")
        and not line.startswith("?? core_md/balloon511_nima_latex_drafts/revision_harness_runs/HARNESS_20260624/")
    ]
    required_wp07_sections = [
        "## 1. Current Paper Claim Boundary",
        "## 2. Veto Authority",
        "## 3. Prompt Normalization Audit",
        "## 4. eplus Survivor Physical Source",
        "## 5. Delayed Convergence and Leading Isotope/Volume",
        "## 6. CsI-BGO Comparison Status",
        "## 7. Methods/Results/Discussion Help",
        "## 8. Candidate English Insertion",
        "## 9. Claims Not Supported",
        "## 10. Provenance Table",
    ]
    failure_keys = {"evidence", "affected_claim", "minimal_next_action", "requires_user_decision", "unexecuted_phases"}
    checks = [
        status_item("G0 authority manifest exists and passes", "00_manifest/baseline_authority_manifest.json", g0.get("status") == "PASS"),
        status_item("G1 prompt normalization passes", "01_prompt_source_audit/prompt_normalization_audit.json", g1.get("status") == "PASS"),
        status_item(
            "G2 eplus provenance classifies at least 80% or reports insufficient trace",
            "02_prompt_eplus_provenance/eplus_survivor_provenance.json",
            g2.get("status") == "PASS_EPLUS_PROVENANCE"
            and float(g2["classification"]["a_to_c_event_fraction"]) >= 0.8,
        ),
        status_item(
            "G3 delayed convergence meets 100 events and <=10% relative uncertainty",
            "03_delayed_convergence/delayed_selected_rate_convergence.json",
            g3.get("status") == "DELAYED_CONVERGED"
            and int(g3["combined"]["selected_events"]) >= 100
            and float(g3["combined"]["relative_uncertainty"]) <= 0.1,
        ),
        status_item(
            "G4 BGO geometry is material-only and overlap checked",
            "04_bgo_variant/bgo_geometry_manifest.json",
            g4.get("status") == "PASS_BGO_SAME_ENVELOPE_GEOMETRY"
            and int(g4["geometry_diff"]["non_whitelisted_diff_count"]) == 0
            and g4["overlap_check"]["status"] == "PASS",
        ),
        status_item(
            "G5/G6 resource guard stops matched production with required failure fields",
            "05_matched_runs_resource_guard/summary.json",
            g5.get("status") == "BLOCKED_RESOURCE_APPROVAL"
            and failure_keys.issubset(set(g5.get("failure_contract", {})))
            and bool(g5["failure_contract"]["requires_user_decision"]),
        ),
        status_item(
            "WP07 final support markdown includes all required sections",
            "07_manuscript_support/background_validation_necessity_and_paper_impact_final.md",
            all(section in support_md for section in required_wp07_sections),
        ),
        status_item(
            "FINAL_STATUS records allowed terminal status",
            "FINAL_STATUS.md",
            "terminal_status: BLOCKED_RESOURCE_APPROVAL" in final_status
            and "G5/G6 matched runs | BLOCKED_RESOURCE_APPROVAL" in final_status,
        ),
        status_item(
            "Authority/manuscript tracked files were not modified",
            "git status --short",
            len(tracked_or_authority_mods) == 0,
            "Allowed untracked entries are the HARNESS input directory and engineering output root.",
        ),
        status_item(
            "No CsI threshold optimization artifacts are present in engineering output",
            "engineering/background_validation_20260624",
            not any(token in path.name for path in ENG.rglob("*") for token in ("40keV", "60keV", "90keV", "threshold_scan")),
        ),
    ]
    passed = all(item["status"] == "PASS" for item in checks)
    payload = {
        "artifact_type": "wp08_completion_audit",
        "created_utc": now_utc(),
        "status": "PASS_COMPLETION_AUDIT" if passed else "FAIL_COMPLETION_AUDIT",
        "terminal_status": "BLOCKED_RESOURCE_APPROVAL",
        "checks": checks,
        "git_status_short": git_lines,
        "tracked_or_authority_modifications": tracked_or_authority_mods,
        "outputs": {
            "json": rel(OUT / "completion_audit.json"),
            "markdown": rel(OUT / "completion_audit.md"),
        },
    }
    write_json(OUT / "completion_audit.json", payload)
    (OUT / "completion_audit.md").write_text(markdown(payload), encoding="utf-8")
    write_json(OUT / "summary.json", payload)
    return payload


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# WP08 Completion Audit",
        "",
        f"Status: `{payload['status']}`.",
        f"Terminal status: `{payload['terminal_status']}`.",
        "",
        "| requirement | status | evidence |",
        "|---|---|---|",
    ]
    for item in payload["checks"]:
        lines.append(f"| {item['requirement']} | {item['status']} | `{item['evidence']}` |")
    return "\n".join(lines) + "\n"


def main() -> int:
    payload = build()
    print(json.dumps({"status": payload["status"], "out": payload["outputs"]["json"]}, indent=2, ensure_ascii=False))
    return 0 if payload["status"] == "PASS_COMPLETION_AUDIT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
