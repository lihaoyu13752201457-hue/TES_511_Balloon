# Execution Plan

Role: Orchestrator.

This plan fixes scope and handoff structure only. PI claimed status belongs to Executor in `03_executor_log.md`; terminal status belongs to Gatekeeper in `06_gatekeeper_verdict.md`.

## Preconditions For Executor Start

- Required reading log exists: `00_startup_reading_log.md`.
- Frozen paths resolved: `00_resolved_frozen_paths.txt` with `UNRESOLVED_FROZEN_PATH_SPECS = NONE`.
- Start baseline exists: `00_git_baseline.txt`.
- Initial inventory exists: `01_initial_state_inventory.md`.
- Coverage map exists: `02_coverage_map.md`.
- Scope is fixed to PI-01..PI-05.

## Pass Structure

Maximum passes: 3.

Pass 1:

1. PI-02a long-tail ignition: search existing delayed replay/convergence tooling and evidence. If a new selected-rate convergence run is safe and necessary, start it only in a new run/report directory and record command, PID/session, log, expected outputs, and recovery instructions in `03_executor_log.md`.
2. PI-01 evidence manifest and stale quarantine.
3. PI-03 units-complete source normalization audit.
4. PI-04 simulation configuration authority table and JSON.
5. PI-05 figure/data pipeline audit.
6. PI-02e collection: gather current or newly produced selected-rate convergence evidence. If >=2 sampling and >=100 selected events cannot be produced in-session, record `BLOCKED_WITH_EVIDENCE`, not `DONE`.
7. Executor runs G1-G5 machine checks and writes a pass-specific diff snapshot.

Pass 2:

Only fix Review Auditor or Project Auditor `FAIL` items that are feasible without changing manuscript text, geometry, or frozen authority outputs.

Pass 3:

Only fix remaining gate-affecting issues. If the only blocker is compute-bound PI-02 with a documented active run or documented inability to safely launch one, stop after recording evidence.

## PI-02 Guardrail

The `DONE` predicate is the harness predicate, not a weaker project-memory predicate:

- each run reports generated decays, selected events, selected rate, uncertainty method, source activity, sampling ID/seed, geometry path, source card path, SIM header geometry path, command, and output path;
- >=2 production-position samplings are compared;
- combined selected events >=100;
- combined relative uncertainty <=0.10;
- every run has source-card and SIM-header geometry provenance.

Anything less is `BLOCKED_WITH_EVIDENCE` or `FAIL`.

## Role Handoff

- Executor subagent writes `03_executor_log.md` and project-side artifacts.
- Review Auditor subagent writes `04_review_auditor_report.md` from `03`, review reports, fix queues, and cited source lines.
- Project Auditor subagent writes `05_project_auditor_report.md` from `03`, fix5 constraints, JSON/CSV outputs, scripts, and git diff evidence.
- Figure Auditor is optional; if used, it writes `05b_figure_auditor_report.md`.
- Gatekeeper subagent writes `06_gatekeeper_verdict.md`, reruns G1-G5, and decides terminal PI status.

## Safety Rules

- Do not edit `balloon511_nima_draft_en.tex`, `balloon511_nima_draft_zh.tex`, or `balloon511_nima_draft_en.md`.
- Do not edit `core_md/fix5_benchmarks.json`.
- Do not edit geometry files or any path in `00_resolved_frozen_paths.txt`.
- Do not overwrite existing `fix5_1of10`, `fix5_fullstat_v2`, `fix5_fullstat_v2_exactpos_m50000_s260613`, old `new_geo_re`, current v3p5, or BGO outputs.
- Unknown configuration or provenance values must be literal `UNKNOWN` or `TO_RECOVER`.
