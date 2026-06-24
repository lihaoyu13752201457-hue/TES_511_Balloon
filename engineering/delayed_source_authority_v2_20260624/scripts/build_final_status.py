#!/usr/bin/env python3
"""Build a compact Phase-2 FINAL_STATUS page from completed WP summaries."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


PHASE_DIR = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def git_output(args: list[str]) -> str:
    try:
        return subprocess.check_output(args, cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def load_summary(path: Path) -> dict:
    if not path.exists():
        return {
            "status": "NOT_RUN",
            "outputs": [],
            "findings": [],
            "next_gate": "",
            "user_decision_required": False,
        }
    return json.loads(path.read_text(encoding="utf-8"))


def is_blocking_status(status: str) -> bool:
    return (
        status.startswith("BLOCKED")
        or status.startswith("FAIL")
        or status.startswith("UNRESOLVED")
        or status in {"NO_RATE_AUTHORITY"}
    )


def main() -> None:
    wp00 = load_summary(PHASE_DIR / "00_manifest/summary.json")
    wp01 = load_summary(PHASE_DIR / "01_raw_inventory/summary.json")
    rows = [
        ("G0", "Phase-1 authority locked", wp00),
        ("G1", "Raw state-resolved inventory", wp01),
        ("G2", "RPIP alignment", load_summary(PHASE_DIR / "02_rpip_alignment/summary.json")),
        ("G3", "Source semantics", load_summary(PHASE_DIR / "03_source_semantics/summary.json")),
        ("G4", "Custom source v2", load_summary(PHASE_DIR / "04_custom_source_v2/summary.json")),
        ("G5", "Native activation", load_summary(PHASE_DIR / "05_native_activation/summary.json")),
        ("G6", "DetectorTimeConstant", load_summary(PHASE_DIR / "06_time_constant/summary.json")),
        ("G7", "Pilot transport", load_summary(PHASE_DIR / "07_transport/summary.json")),
        ("G8", "Promotion", load_summary(PHASE_DIR / "08_promotion/summary.json")),
        ("G9", "Downstream", load_summary(PHASE_DIR / "09_downstream/summary.json")),
        ("G10", "Manuscript support", load_summary(PHASE_DIR / "10_manuscript_support/summary.json")),
    ]
    git_status = "dirty" if git_output(["git", "status", "--short"]) else "clean"
    lines = [
        "# FINAL_STATUS",
        "",
        f"updated_at: {datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')}",
        f"git_head: {git_output(['git', 'rev-parse', 'HEAD'])}",
        f"git_branch: {git_output(['git', 'branch', '--show-current'])}",
        f"git_status: {git_status}",
        "harness_version: 2.0",
        "claim_boundary: reference-exposure unresolved-line selected-rate estimate",
        "",
        "| Gate | Status | Evidence | Blocking? | Next action |",
        "|---|---|---|---:|---|",
    ]
    for gate, label, summary in rows:
        status = summary.get("status", "NOT_RUN")
        outputs = summary.get("outputs", [])
        evidence = outputs[0] if outputs else ""
        blocking = "yes" if is_blocking_status(status) else "no"
        next_gate = summary.get("next_gate", "")
        lines.append(f"| {gate} {label} | `{status}` | `{evidence}` | {blocking} | {next_gate} |")
    created: list[str] = []
    for _, _, summary in rows:
        created.extend(summary.get("outputs", []))
    lines.extend(
        [
            "",
            "## Files Created",
            *(f"- `{path}`" for path in created),
            "",
            "## Files Intentionally Not Modified",
            "- baseline/fix5 geometry",
            "- prompt source cards",
            "- `runs/` authority outputs",
            "- `outputs/` authority reports",
            "- `stepwise_maintenance/` outputs",
            "- manuscript source",
            "",
            "## Resource Approvals Requested",
            "- none for physics transport",
            "",
            "## Numerical Promotions Made",
            "- none",
            "",
            "## Manuscript Changes Applied",
            "- none",
        ]
    )
    text = "\n".join(lines) + "\n"
    root_status = PHASE_DIR / "FINAL_STATUS.md"
    manifest_status = PHASE_DIR / "00_manifest/FINAL_STATUS.md"
    root_status.write_text(text, encoding="utf-8")
    manifest_status.write_text(text, encoding="utf-8")
    print(f"wrote {rel(root_status)}")
    print(f"wrote {rel(manifest_status)}")


if __name__ == "__main__":
    main()
