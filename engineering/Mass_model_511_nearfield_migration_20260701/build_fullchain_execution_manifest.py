#!/usr/bin/env python3
"""Build Mass_model_511 full-chain execution preflight artifacts.

This script records the executable state after preparing full-stat prompt and
buildup runner manifests. It does not run Cosima and it does not edit source
authority cards.
"""

from __future__ import annotations

import csv
import gzip
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "engineering/Mass_model_511_nearfield_migration_20260701"
OUT = PKG / "07_fullchain_execution_20260702"
RUN_ROOT = ROOT / "runs/Mass_model_511_nearfield_migration_20260701"
SOURCE_DIR = PKG / "03_source_migration/source_dirs/Mass_model_511"
SMOKE_ROOT = RUN_ROOT
LABEL = "candidate_Mass_model_511_fullstat_v1"
BRANCH = "candidate_Mass_model_511"
MEGALIB_ENV = "/home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh"
GEOMETRY = (
    "outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
FORBIDDEN = (
    "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
MODES = ("instant", "buildup")


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def run_dir(mode: str) -> Path:
    return RUN_ROOT / f"step02_{mode}_{LABEL}"


def smoke_dir(mode: str) -> Path:
    return SMOKE_ROOT / f"step02_{mode}_{BRANCH}_smoke"


def source_card_audit() -> dict[str, Any]:
    rows = []
    for path in sorted(SOURCE_DIR.glob("Background_*_fullsphere20.source")):
        text = path.read_text(encoding="utf-8", errors="replace")
        geometry_lines = [line.strip() for line in text.splitlines() if line.strip().startswith("Geometry ")]
        rows.append(
            {
                "path": rel(path),
                "geometry_lines": geometry_lines,
                "contains_mass_model_geometry": GEOMETRY in text,
                "contains_forbidden_fix5_geometry": FORBIDDEN in text,
                "status": "PASS"
                if len(geometry_lines) == 1 and geometry_lines[0] == f"Geometry {GEOMETRY}" and FORBIDDEN not in text
                else "FAIL",
            }
        )
    return {
        "source_dir": rel(SOURCE_DIR),
        "cards": len(rows),
        "rows": rows,
        "status": "PASS" if rows and all(row["status"] == "PASS" for row in rows) else "FAIL",
    }


def inspect_header(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": rel(path), "exists": False, "contains_mass_model_geometry": False}
    lines = []
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
        for _, line in zip(range(180), fh):
            lines.append(line)
    text = "".join(lines)
    return {
        "path": rel(path),
        "exists": True,
        "contains_mass_model_geometry": GEOMETRY in text,
        "contains_forbidden_fix5_geometry": FORBIDDEN in text,
    }


def by_particle(rows: list[dict[str, str]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        out[row["particle"]] = out.get(row["particle"], 0) + int(row["events"])
    return dict(sorted(out.items()))


def estimate_from_mass_smoke(mode: str, full_rows: list[dict[str, str]]) -> dict[str, Any]:
    smoke_summary = smoke_dir(mode) / "run_summary.csv"
    if not smoke_summary.exists():
        return {"status": "NO_MASS_MODEL_SMOKE_SUMMARY", "path": rel(smoke_summary)}
    smoke_rows = read_csv(smoke_summary)
    rates: dict[str, dict[str, float]] = {}
    for row in smoke_rows:
        events = int(row["events"])
        if events <= 0:
            continue
        item = rates.setdefault(row["particle"], {"events": 0.0, "cpu_s": 0.0, "bytes": 0.0})
        item["events"] += events
        item["cpu_s"] += float(row.get("cpu_s") or 0.0)
        item["bytes"] += float(row.get("sim_size_bytes") or 0.0) + float(row.get("dat_size_bytes") or 0.0)
    full_by_particle = by_particle(full_rows)
    out_by_particle = {}
    total_cpu_s = 0.0
    total_bytes = 0.0
    for particle, events in full_by_particle.items():
        base = rates.get(particle)
        if not base or base["events"] <= 0.0:
            out_by_particle[particle] = {"events": events, "status": "NO_SMOKE_RATE"}
            continue
        cpu_s = base["cpu_s"] / base["events"] * events
        bytes_ = base["bytes"] / base["events"] * events
        total_cpu_s += cpu_s
        total_bytes += bytes_
        out_by_particle[particle] = {
            "events": events,
            "estimated_cpu_s": cpu_s,
            "estimated_output_bytes": bytes_,
            "scale_vs_smoke_events": events / base["events"],
        }
    return {
        "status": "ESTIMATED_FROM_MASS_MODEL_SMOKE",
        "smoke_summary": rel(smoke_summary),
        "estimated_cpu_s": total_cpu_s,
        "estimated_cpu_days_serial": total_cpu_s / 86400.0,
        "estimated_output_gb": total_bytes / 1.0e9,
        "by_particle": out_by_particle,
        "caveat": "Linear extrapolation from smoke transport summaries; use for planning, not as a resource guarantee.",
    }


def mode_preflight(mode: str) -> dict[str, Any]:
    d = run_dir(mode)
    manifest = d / "run_manifest.csv"
    norm_path = d / "normalization.json"
    summary_path = d / "run_summary.json"
    rows = read_csv(manifest) if manifest.exists() else []
    norm = read_json(norm_path) if norm_path.exists() else {}
    summary_rows = read_json(summary_path) if summary_path.exists() else []
    summary_fail = sum(1 for row in summary_rows if row.get("status") == "FAIL")
    summary_pass_or_skip = sum(1 for row in summary_rows if row.get("status") in ("PASS", "SKIP"))
    job_sources = [Path(row["temp_source"]) for row in rows]
    source_hits = 0
    forbidden_hits = 0
    for path in job_sources:
        text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        source_hits += 1 if GEOMETRY in text else 0
        forbidden_hits += 1 if FORBIDDEN in text else 0
    expected_sim = [Path(row["sim_path"]) for row in rows]
    expected_dat = [Path(row["dat_path"]) for row in rows]
    existing_sim = [path for path in expected_sim if path.exists()]
    existing_dat = [path for path in expected_dat if path.exists()]
    headers = [inspect_header(path) for path in existing_sim[:3]]
    preflight_pass = (
        len(rows) == 68
        and len(job_sources) == 68
        and all(path.exists() for path in job_sources)
        and source_hits == 68
        and forbidden_hits == 0
        and int(norm.get("gamma_events", 0)) == 10_000_000
        and int(norm.get("gamma_splits", 0)) == 12
        and int(norm.get("non_gamma_replicas", 0)) == 8
    )
    if existing_sim and len(existing_sim) == 68 and len(existing_dat) == 68 and summary_fail == 0:
        status = "PASS_STAGE1_TRANSPORT_OUTPUTS_PRESENT"
    elif summary_fail:
        status = "FAILED_TRANSPORT_ATTEMPT_PREFLIGHT_STILL_READY"
    elif preflight_pass:
        status = "PASS_PREFLIGHT_RUNNER_PREPARED"
    else:
        status = "FAIL_PREFLIGHT_RUNNER_PREPARED"
    return {
        "mode": mode,
        "status": status,
        "run_dir": rel(d),
        "run_manifest": rel(manifest),
        "normalization": rel(norm_path),
        "run_summary": rel(summary_path) if summary_path.exists() else None,
        "run_summary_rows": len(summary_rows),
        "run_summary_pass_or_skip": summary_pass_or_skip,
        "run_summary_fail": summary_fail,
        "job_sources_dir": rel(d / "job_sources"),
        "jobs": len(rows),
        "job_sources_existing": sum(1 for path in job_sources if path.exists()),
        "job_sources_with_mass_model_geometry": source_hits,
        "job_sources_with_forbidden_fix5_geometry": forbidden_hits,
        "expected_sim_outputs": len(expected_sim),
        "expected_dat_outputs": len(expected_dat),
        "existing_sim_outputs": len(existing_sim),
        "existing_dat_outputs": len(existing_dat),
        "events_requested_total": sum(int(row["events"]) for row in rows),
        "events_requested_by_particle": by_particle(rows),
        "statistics_profile": {
            "gamma_events": norm.get("gamma_events"),
            "gamma_splits": norm.get("gamma_splits"),
            "non_gamma_replicas": norm.get("non_gamma_replicas"),
            "farfield_radius_cm": norm.get("farfield_radius_cm"),
            "prompt_time_s": norm.get("gamma_prompt_time_s_with_farfield_area"),
        },
        "planning_estimate": estimate_from_mass_smoke(mode, rows),
        "sample_existing_headers": headers,
    }


def command(mode: str, prepare_only: bool = False) -> str:
    tail = "--prepare-sources-only" if prepare_only else "--allow-heavy-run"
    return (
        "python3 code/tools/run_equiv2602_pipeline_NEW_GEO.py "
        f"--mode {mode} "
        "--source-dir engineering/Mass_model_511_nearfield_migration_20260701/03_source_migration/source_dirs/Mass_model_511 "
        f"--outdir runs/Mass_model_511_nearfield_migration_20260701/step02_{mode}_{LABEL} "
        "--gamma-events 10000000 --gamma-splits 12 --non-gamma-replicas 8 "
        "--farfield-radius-cm 60 --workers 8 --keep-sources "
        f"{tail}"
    )


def todo_rows(mode_records: dict[str, Any]) -> list[dict[str, Any]]:
    ready_statuses = {
        "PASS_PREFLIGHT_RUNNER_PREPARED",
        "FAILED_TRANSPORT_ATTEMPT_PREFLIGHT_STILL_READY",
        "PASS_STAGE1_TRANSPORT_OUTPUTS_PRESENT",
    }
    stage1_ready = all(row["status"] in ready_statuses for row in mode_records.values())
    transport_done = all(row["existing_sim_outputs"] == 68 and row["existing_dat_outputs"] == 68 for row in mode_records.values())
    failed_attempt = any(int(row.get("run_summary_fail", 0)) > 0 for row in mode_records.values())
    if transport_done:
        detector_background_status = "STAGE1_TRANSPORT_OUTPUTS_PRESENT_DELAYED_NOT_PREPARED"
        detector_background_notes = (
            "Prompt/buildup Stage-1 full-stat Cosima transport outputs are present. "
            "Delayed full-stat is not prepared."
        )
    elif failed_attempt:
        detector_background_status = "FAILED_STAGE1_TRANSPORT_ATTEMPT_PREFLIGHT_READY"
        detector_background_notes = (
            "Prompt/buildup runner/job sources are prepared, but a Stage-1 transport attempt failed. "
            "Missing SIM/DAT outputs can be rerun with the Stage-1 runner."
        )
    elif stage1_ready:
        detector_background_status = "PARTIAL_PRE_MC_READY_STAGE1_NOT_RUN_TRANSPORT"
        detector_background_notes = (
            "Prompt/buildup runner/job sources prepared. Heavy Cosima transport is not complete; "
            "delayed full-stat is not prepared."
        )
    else:
        detector_background_status = "NOT_RUN"
        detector_background_notes = "Prompt/buildup Stage-1 preflight is not ready."
    return [
        {
            "target": "full_stat_detector_background",
            "status": detector_background_status,
            "preflight_status": "PASS" if stage1_ready else "BLOCKED",
            "evidence_path": f"{mode_records['instant']['run_manifest']}; {mode_records['buildup']['run_manifest']}",
            "command": "see RUN_FULLSTAT_TRANSPORT_STAGE1.sh",
            "notes": detector_background_notes,
        },
        {
            "target": "full_stat_step05_detector_response",
            "status": "BLOCKED",
            "preflight_status": "NOT_READY",
            "evidence_path": "engineering/Mass_model_511_nearfield_migration_20260701/06_smoke_closure/mass_model_511_smoke_closure.json",
            "command": "no safe full-stat command released yet",
            "notes": "Requires completed full-stat prompt, buildup, delayed source/transport, then a full-stat retarget of the Step05 smoke parser.",
        },
        {
            "target": "no_material_effect_or_replacement_release",
            "status": "BLOCKED",
            "preflight_status": "NOT_READY",
            "evidence_path": "core_md/README.md; historical fix5 gate bundle removed from cleaned checkout",
            "command": "no safe pass/fail command released yet",
            "notes": "Requires full-stat Step05 candidate rates and comparison against current fix5 paper authority.",
        },
        {
            "target": "step06_step08_mission_axis_regeneration",
            "status": "BLOCKED",
            "preflight_status": "NOT_READY",
            "evidence_path": "stepwise_maintenance/step06_mission_time_variation; stepwise_maintenance/step07_source_cases; stepwise_maintenance/step08_significance",
            "command": "no safe Mass_model_511 command released yet",
            "notes": "Existing Step06-Step08 scripts are fix5-label authority outputs; Mass_model_511 retarget waits for full-stat Step05 rates.",
        },
        {
            "target": "p1_p2_p3_replay_on_mass_model_511",
            "status": "BLOCKED",
            "preflight_status": "NOT_READY",
            "evidence_path": "engineering/paper_review_p1_p2_p3_data_check_20260702/outputs",
            "command": "no safe replay command released yet",
            "notes": "Requires Mass_model_511 full-stat Step05/Step08 products before line-width, atmospheric 511, and geometry-framing replay.",
        },
        {
            "target": "transport_outputs_present",
            "status": "PASS" if transport_done else "NOT_RUN",
            "preflight_status": "PASS" if stage1_ready else "BLOCKED",
            "evidence_path": f"{mode_records['instant']['run_dir']}; {mode_records['buildup']['run_dir']}",
            "command": "see RUN_FULLSTAT_TRANSPORT_STAGE1.sh",
            "notes": "This row is PASS only after all 136 SIM and 136 DAT outputs exist.",
        },
    ]


def write_runner(path: Path) -> None:
    text = "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "",
            "# Stage 1 only: full-stat Mass_model_511 candidate prompt and buildup transport.",
            "# This script intentionally stops before delayed source construction and Step05.",
            "# Continue only after checking disk/runtime and confirming no other agent owns these run dirs.",
            f"MEGALIB_ENV={MEGALIB_ENV!r}",
            "if [[ ! -f \"$MEGALIB_ENV\" ]]; then",
            "  echo \"missing MEGAlib environment: $MEGALIB_ENV\" >&2",
            "  exit 127",
            "fi",
            "source \"$MEGALIB_ENV\"",
            "",
            command("instant", prepare_only=False),
            command("buildup", prepare_only=False),
            "",
            "python3 engineering/Mass_model_511_nearfield_migration_20260701/build_fullchain_execution_manifest.py",
            "",
        ]
    )
    path.write_text(text, encoding="utf-8")


def build_markdown(payload: dict[str, Any], todos: list[dict[str, Any]]) -> str:
    transport_done = all(
        row["status"] == "PASS_STAGE1_TRANSPORT_OUTPUTS_PRESENT" for row in payload["mode_records"].values()
    )
    transport_line = (
        "- Stage-1 prompt and buildup full-stat Cosima transport outputs are present."
        if transport_done
        else "- Cosima full-stat transport was not completed."
    )
    lines = [
        "# Mass_model_511 Full-Chain Execution Status",
        "",
        f"generated_at_utc: `{payload['generated_at_utc']}`",
        f"overall_status: `{payload['overall_status']}`",
        "",
        "## What Was Prepared And Run",
        "",
        "- Full-stat candidate prompt and buildup run manifests/job source cards were prepared with existing `code/tools/run_equiv2602_pipeline_NEW_GEO.py`.",
        transport_line,
        "- Source authority cards and paper files were not edited.",
        "",
        "## Mode Preflight",
        "",
        "| mode | status | jobs | events | existing SIM | existing DAT | estimate CPU-days | estimate GB |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for mode, row in payload["mode_records"].items():
        estimate = row["planning_estimate"]
        lines.append(
            f"| `{mode}` | `{row['status']}` | {row['jobs']} | {row['events_requested_total']} | "
            f"{row['existing_sim_outputs']}/68 | {row['existing_dat_outputs']}/68 | "
            f"{float(estimate.get('estimated_cpu_days_serial', 0.0)):.3f} | "
            f"{float(estimate.get('estimated_output_gb', 0.0)):.3f} |"
        )
    lines.extend(
        [
            "",
            "## TODO Status",
            "",
            "| target | status | evidence | notes |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in todos:
        lines.append(f"| `{row['target']}` | `{row['status']}` | `{row['evidence_path']}` | {row['notes']} |")
    lines.extend(
        [
            "",
            "## Runnable Entry",
            "",
            f"- Stage-1 transport runner: `{payload['artifacts']['stage1_runner']}`",
            f"- Full manifest: `{payload['artifacts']['manifest_json']}`",
            f"- TODO CSV: `{payload['artifacts']['todo_csv']}`",
            "",
            "Downstream delayed/Step05/Step06-Step08/P1-P3 remain blocked until delayed full-stat and full-stat detector-response products exist.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    source_audit = source_card_audit()
    mode_records = {mode: mode_preflight(mode) for mode in MODES}
    todos = todo_rows(mode_records)
    runner_path = OUT / "RUN_FULLSTAT_TRANSPORT_STAGE1.sh"
    write_runner(runner_path)
    artifacts = {
        "manifest_json": rel(OUT / "fullchain_execution_manifest.json"),
        "status_md": rel(OUT / "FULLCHAIN_EXECUTION_STATUS.md"),
        "todo_csv": rel(OUT / "todo_status.csv"),
        "stage1_runner": rel(runner_path),
    }
    mode_statuses = {row["status"] for row in mode_records.values()}
    stage1_ready = source_audit["status"] == "PASS" and all(
        status
        in {
            "PASS_PREFLIGHT_RUNNER_PREPARED",
            "FAILED_TRANSPORT_ATTEMPT_PREFLIGHT_STILL_READY",
            "PASS_STAGE1_TRANSPORT_OUTPUTS_PRESENT",
        }
        for status in mode_statuses
    )
    transport_done = source_audit["status"] == "PASS" and mode_statuses == {"PASS_STAGE1_TRANSPORT_OUTPUTS_PRESENT"}
    if transport_done:
        overall = "PASS_STAGE1_TRANSPORT_OUTPUTS_PRESENT_DELAYED_NOT_PREPARED"
    elif stage1_ready:
        overall = "PASS_STAGE1_PREFLIGHT_NOT_RUN"
    else:
        overall = "BLOCKED_STAGE1_PREFLIGHT"
    payload = {
        "document_type": "mass_model_511_fullchain_execution_preflight",
        "label": LABEL,
        "generated_by": rel(Path(__file__)),
        "generated_at_utc": now_utc(),
        "overall_status": overall,
        "claim_boundary": (
            "Stage-1 prompt/buildup transport output presence only. "
            "No delayed full-stat, no full-stat detector-rate, no replacement, no manuscript-readiness claim."
        ),
        "source_authority_edited": False,
        "paper_body_edited": False,
        "old_nearfield_engineering_edited": False,
        "megalib_environment": MEGALIB_ENV,
        "source_card_audit": source_audit,
        "mode_records": mode_records,
        "commands_run_this_turn": [
            command("instant", prepare_only=True),
            command("buildup", prepare_only=True),
            "python3 engineering/Mass_model_511_nearfield_migration_20260701/build_fullchain_execution_manifest.py",
        ],
        "commands_not_started": [command("instant", prepare_only=False), command("buildup", prepare_only=False)],
        "todo_status": todos,
        "artifacts": artifacts,
    }
    write_csv(OUT / "todo_status.csv", todos)
    write_json(OUT / "fullchain_execution_manifest.json", payload)
    (OUT / "FULLCHAIN_EXECUTION_STATUS.md").write_text(build_markdown(payload, todos), encoding="utf-8")
    print(json.dumps({"status": overall, "manifest": artifacts["manifest_json"], "status_md": artifacts["status_md"]}, indent=2))
    return 0 if overall.startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
