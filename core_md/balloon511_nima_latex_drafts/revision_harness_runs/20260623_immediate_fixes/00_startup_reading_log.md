# Startup Reading Log

Role: Orchestrator.

Harness: immediate-fixes v2.1.

Independence mode planned: `SUBAGENT`. Tool discovery exposed `multi_agent_v1`, so Executor, Review Auditor, Project Auditor, and Gatekeeper will be separate fresh subagents. This Orchestrator writes only 00/01/02/02_coverage and final 07; it does not own PI status or gate verdicts.

## Required Reading Completed

| Order | File | Evidence |
|---:|---|---|
| 1 | `AGENTS.md` | Lines 10-28 require reading the fix5 method/guide/constraints/checklist first and declare `core_md/fix5_benchmarks.json` the numeric authority. |
| 2 | `core_md/METHOD_FIX5_SIM_CLOSURE.md` | Lines 73-110 define prompt `1/sum(TT)`, delayed NUBASE ground-state correction, per-family TT division guard, and M-sampling audit; lines 112-137 explain why old `new_geo_re` is only a coarse screen and v3p5 is the promotion bar. |
| 3 | `core_md/GUIDE_FIX5_SIM_CLOSURE_FOR_CODEX_20260621.md` | Lines 36-47 name the fix5 geometry artifacts; lines 116-136 define Verifier checks and required structured artifacts. |
| 4 | `core_md/CONSTRAINTS_FIX5_SIM_CLOSURE.md` | Lines 93-107 require source-card/SIM provenance and benchmark alignment; lines 180-192 state stop rules. |
| 5 | `core_md/PRE_PROMPT_FIX5_SIM_CLOSURE_20260621.md` | Lines 24-47 require the checkpoint before MC; lines 80-90 restate fail-closed rules. |
| 6 | `core_md/fix5_benchmarks.json` | JSON `required_artifacts` lines 20-81 and `uncertainty_anchor` lines 116-132 define artifact and rate-gate authority. |
| 7 | `project_internal_fix_queue_zh.md` | Lines 20-26 identify PI-01..PI-05 as immediate/do-now items; lines 447-454 define minimum project-side acceptance. |
| 8 | `project_internal_fix_queue.md` | Lines 26-32 give the English do-now list; lines 574-585 define future acceptance checks. |
| 9 | `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/phase1_project_audit.md` | Lines 35-71 trace current N1 rates/Z/F3; lines 73-111 trace corrected upstream Ge-proxy upper rate; lines 130-161 trace delayed 30-event limitation. |
| 10 | `phase1_audit.md` | Lines 34-59 summarize review conformance; lines 61-71 record proper Phase 2 deferrals. |
| 11 | `remaining_backlog.md` | Lines 11-25 map remaining review concerns to backlog; lines 27-53 provide response-language context. |
| 12 | `balloon511_nima_review_en_20260622.md` | Lines 72-96 require source normalization; lines 116-132 require delayed selected-rate convergence; lines 182-188 require Geant4/MEGAlib config; lines 312-362 define figure/table concerns. |
| 13 | `balloon511_nima_review_cn_20260622.md` | Lines 72-96, 116-132, 182-188, and 312-362 mirror the same Chinese review requirements. |

Current manuscript claim lines were also read because PI-01 requires exact provenance for paper-used values: English `.tex` lines 40, 232, 550-578, 626-631, and 663; Chinese `.tex` lines 41, 227, 497-525, 554-558, and 587.

## Current Scope

In scope for this harness: PI-01 evidence manifest and stale quarantine; PI-02 delayed selected-rate convergence; PI-03 source-normalization audit; PI-04 simulation configuration authority; PI-05 figure/data pipeline audit.

Out of scope this round: geometry redesign, final flight-performance claim, CsI material trade study, diffuse foreground model, full CAD replacement, full TES/CsI electronics simulation, and manuscript text edits.

## Authority Rules

- `core_md/fix5_benchmarks.json` overrides prose numbers.
- No paper number may be promoted without provenance; unknown values must be `UNKNOWN` or `TO_RECOVER`.
- New runs, if any, must use new output directories and must not overwrite paths listed in `00_resolved_frozen_paths.txt`.
- Current manuscript body files are frozen by the hashes recorded in `00_git_baseline.txt`.
