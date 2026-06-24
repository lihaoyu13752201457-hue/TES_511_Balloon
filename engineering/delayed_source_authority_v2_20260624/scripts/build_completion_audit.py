#!/usr/bin/env python3
"""Build a reproducible completion audit for harness_20260624_2."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


PHASE_DIR = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
HARNESS = ROOT / "core_md/balloon511_nima_latex_drafts/revision_harness_runs/harness_20260624_2/HARNESS_ENGINEERING_TES511_DELAYED_SOURCE_AUTHORITY_V2_1_QUICK_CONTEXT.md"
OUT_JSON = PHASE_DIR / "00_manifest/completion_audit.json"
OUT_MD = PHASE_DIR / "00_manifest/completion_audit.md"

FIX5_GEOMETRY_REL = "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
FIX5_GEOMETRY_ABS = str(ROOT / FIX5_GEOMETRY_REL)

SUMMARY_KEYS = [
    "status",
    "inputs",
    "outputs",
    "findings",
    "claim_impact",
    "next_gate",
    "user_decision_required",
]

EXPECTED_TERMINAL_STATUSES = {
    "00_manifest": "PASS",
    "01_raw_inventory": "PASS",
    "02_rpip_alignment": "PASS",
    "03_source_semantics": "PASS",
    "04_custom_source_v2": "PASS",
    "05_native_activation": "EXPLAINED_MODEL_DIFFERENCE",
    "06_time_constant": "TIME_CONSTANT_STABLE",
    "07_transport": "PARTIAL_PILOT_TRANSPORT_SOURCE_V2_NATIVE_SELECTION_DIAGNOSTIC_LEGACY_TIMEOUT_NOT_PROMOTION",
    "08_promotion": "NO_RATE_AUTHORITY",
    "09_downstream": "NO_RATE_AUTHORITY",
    "10_manuscript_support": "NO_RATE_AUTHORITY",
}

FORBIDDEN_PATHS = [
    "outputs",
    "runs",
    "stepwise_maintenance",
    "config/megalib_sources_fullsphere20_fix5_tilt45",
    "old",
    "core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.tex",
    "core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.md",
    "core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_ja.tex",
    "core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_ja.md",
]


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def git_output(args: list[str]) -> str:
    try:
        return subprocess.check_output(args, cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception as exc:
        return f"ERROR: {exc}"


def harness_required_files() -> tuple[int, list[str]]:
    text = HARNESS.read_text(encoding="utf-8")
    start = text.index("# 3. 最终交付物")
    end = text.index("# 4. 输入权威与发现规则")
    section = text[start:end]
    fences: list[list[str]] = []
    in_fence = False
    buf: list[str] = []
    for line in section.splitlines():
        if line.strip().startswith("```"):
            if in_fence:
                fences.append(buf)
                buf = []
                in_fence = False
            else:
                in_fence = True
            continue
        if in_fence:
            buf.append(line.rstrip())
    required: list[Path] = []
    current_dir: str | None = None
    for raw in fences[1]:
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.endswith("/"):
            current_dir = stripped.rstrip("/")
            continue
        if current_dir is not None:
            required.append(PHASE_DIR / current_dir / stripped)
    missing = [rel(path) for path in required if not path.exists()]
    return len(required), missing


def summary_schema_audit() -> dict:
    rows = []
    status_mismatches = []
    for path in sorted(PHASE_DIR.glob("[0-9][0-9]*/summary.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        missing = [key for key in SUMMARY_KEYS if key not in data]
        wp = path.parent.name
        expected = EXPECTED_TERMINAL_STATUSES.get(wp)
        actual = data.get("status")
        if expected and actual != expected:
            status_mismatches.append({"work_package": wp, "expected": expected, "actual": actual})
        rows.append({"path": rel(path), "status": actual, "missing_keys": missing})
    return {
        "checked_count": len(rows),
        "missing_schema": [row for row in rows if row["missing_keys"]],
        "status_mismatches": status_mismatches,
        "statuses": rows,
    }


def json_audit() -> dict:
    errors = []
    paths = sorted(PHASE_DIR.rglob("*.json"))
    for path in paths:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append({"path": rel(path), "error": str(exc)})
    return {"checked_count": len(paths), "errors": errors}


def final_status_audit() -> dict:
    paths = [PHASE_DIR / "FINAL_STATUS.md", PHASE_DIR / "00_manifest/FINAL_STATUS.md"]
    hashes = []
    for path in paths:
        hashes.append(
            {
                "path": rel(path),
                "exists": path.exists(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None,
            }
        )
    present_hashes = {row["sha256"] for row in hashes if row["sha256"]}
    return {"files": hashes, "same_hash": len(present_hashes) == 1 and len(hashes) == len(present_hashes) + 1}


def geometry_audit() -> dict:
    allowed = {FIX5_GEOMETRY_REL, FIX5_GEOMETRY_ABS}
    missing_geometry = []
    bad_geometry = []
    for path in sorted(PHASE_DIR.rglob("*.source")):
        geometries = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if stripped.startswith("Geometry "):
                geometries.append(stripped.split(None, 1)[1])
        if not geometries:
            missing_geometry.append(rel(path))
        bad = [geom for geom in geometries if geom not in allowed]
        if bad:
            bad_geometry.append({"path": rel(path), "bad_geometry": bad})

    bad_sim_headers = []
    sim_header_mentions = 0
    for path in sorted(PHASE_DIR.rglob("*.sim.gz")):
        found = []
        with gzip.open(path, "rt", errors="replace") as handle:
            for line_no, line in enumerate(handle, start=1):
                if line_no > 3000:
                    break
                if "Geometry" in line or ".geo.setup" in line or "DEMO2_DR" in line:
                    found.append(line.strip())
                    if len(found) >= 5:
                        break
        sim_header_mentions += len(found)
        bad = [
            line
            for line in found
            if (".geo.setup" in line or "DEMO2_DR" in line)
            and "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup" not in line
        ]
        if bad:
            bad_sim_headers.append({"path": rel(path), "bad_header_lines": bad})
    return {
        "source_file_count": len(list(PHASE_DIR.rglob("*.source"))),
        "source_geometry_missing": missing_geometry,
        "source_geometry_bad": bad_geometry,
        "sim_file_count": len(list(PHASE_DIR.rglob("*.sim.gz"))),
        "sim_header_geometry_mentions": sim_header_mentions,
        "sim_header_bad": bad_sim_headers,
    }


def forbidden_write_audit() -> dict:
    status = git_output(["git", "status", "--short", "--", *FORBIDDEN_PATHS])
    rows = [line for line in status.splitlines() if line.strip()]
    return {"forbidden_paths": FORBIDDEN_PATHS, "git_status_entries": rows}


def process_audit() -> dict:
    patterns = (
        "cosima",
        "wp07_run_pilot_transport.py",
        "wp08_promotion_decision.py",
        "wp09_downstream_no_rate_authority.py",
        "wp10_manuscript_support_no_rate_authority.py",
    )
    exclude = ("codex-linux-sandbox", "bwrap")
    rows = []
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            cmd = (proc / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace").strip()
        except Exception:
            continue
        if not cmd or int(proc.name) == os.getpid():
            continue
        if any(pattern in cmd for pattern in patterns) and not any(skip in cmd for skip in exclude):
            rows.append({"pid": int(proc.name), "cmd": cmd[:300]})
    return {"matching_processes": rows}


def update_manifest_summary(audit_status: str) -> None:
    path = PHASE_DIR / "00_manifest/summary.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    outputs = data.setdefault("outputs", [])
    for artifact in (OUT_JSON, OUT_MD):
        artifact_rel = rel(artifact)
        if artifact_rel not in outputs:
            outputs.append(artifact_rel)
    findings = data.setdefault("findings", [])
    finding = f"Completion audit status: {audit_status}."
    if finding not in findings:
        findings.append(finding)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    required_count, missing_required = harness_required_files()
    summary = summary_schema_audit()
    json_status = json_audit()
    final_status = final_status_audit()
    geometry = geometry_audit()
    forbidden = forbidden_write_audit()
    processes = process_audit()

    problems = []
    if missing_required:
        problems.append("missing required harness artifacts")
    if summary["missing_schema"] or summary["status_mismatches"]:
        problems.append("summary schema/status mismatch")
    if json_status["errors"]:
        problems.append("invalid JSON files")
    if not all(row["exists"] for row in final_status["files"]) or not final_status["same_hash"]:
        problems.append("FINAL_STATUS copies missing or mismatched")
    if geometry["source_geometry_missing"] or geometry["source_geometry_bad"] or geometry["sim_header_bad"]:
        problems.append("source/SIM geometry mismatch")
    if forbidden["git_status_entries"]:
        problems.append("forbidden path modifications present")
    if processes["matching_processes"]:
        problems.append("active transport/promotion processes present")

    audit = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "harness": rel(HARNESS),
        "git_head": git_output(["git", "rev-parse", "HEAD"]),
        "git_branch": git_output(["git", "branch", "--show-current"]),
        "claim_boundary": "reference-exposure unresolved-line selected-rate estimate",
        "required_artifacts": {"required_count": required_count, "missing": missing_required},
        "summary_schema": summary,
        "json_audit": json_status,
        "final_status": final_status,
        "geometry_audit": geometry,
        "forbidden_write_audit": forbidden,
        "process_audit": processes,
        "legal_terminal_endpoint": "NO_RATE_AUTHORITY",
        "completion_verdict": "COMPLETE_LEGAL_NO_RATE_AUTHORITY_ENDPOINT" if not problems else "INCOMPLETE",
        "status": "PASS" if not problems else "FAIL",
        "problems": problems,
    }
    OUT_JSON.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Completion Audit",
        "",
        f"status: {audit['status']}",
        f"completion_verdict: {audit['completion_verdict']}",
        f"generated_at: {audit['generated_at']}",
        f"harness: `{audit['harness']}`",
        "",
        "## Evidence",
        f"- required artifacts: {required_count} checked, {len(missing_required)} missing",
        f"- summary schemas: {summary['checked_count']} checked, {len(summary['missing_schema'])} missing-schema issues",
        f"- summary status mismatches: {len(summary['status_mismatches'])}",
        f"- JSON parse errors: {len(json_status['errors'])}",
        f"- FINAL_STATUS copies identical: {final_status['same_hash']}",
        f"- source geometry mismatches: {len(geometry['source_geometry_bad'])}",
        f"- SIM header geometry mismatches: {len(geometry['sim_header_bad'])}",
        f"- forbidden path git-status entries: {len(forbidden['git_status_entries'])}",
        f"- active transport/promotion processes: {len(processes['matching_processes'])}",
        "",
        "## Terminal Boundary",
        "This harness run ends at `NO_RATE_AUTHORITY`; no v2 delayed selected-rate number, downstream rate, or manuscript number is promoted.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    update_manifest_summary(audit["status"])
    print(json.dumps({"status": audit["status"], "completion_verdict": audit["completion_verdict"], "problems": problems}, indent=2))


if __name__ == "__main__":
    main()
