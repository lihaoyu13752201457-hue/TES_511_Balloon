# Phase 1 gate verdict

Role: Gatekeeper for the Balloon511 NIM A revision harness.

Date: 2026-06-23 (local).

Inputs consumed:

- `core_md/balloon511_nima_latex_drafts/balloon511_nima_revision_harness_20260622.md`
- `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/review_inventory.md`
- `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/phase1_delta.md`
- `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/phase1_audit.md`
- `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/phase1_project_audit.md`
- `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/remaining_backlog.md`
- `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/pass_1.diff`
- current `core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.tex`
- current `core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.md`

`PHASE1_DONE = true`

## Predicate rationale

| Predicate | Verdict | Rationale |
|---|---|---|
| `COVERAGE_OK` | PASS | `review_inventory.md` records `COVERAGE_OK = true`; every external-review item is mapped to a Section 3 ID or explicit omit/reject. |
| Every Section 3A-3D item terminal | PASS | `phase1_delta.md` lists terminal statuses for N1-N7, D1-D4, W1-W7, F1-F5, and C1cite. `ledger.md` now records only Section 6 terminal status values: `APPLIED` or `SOFTENED` for Phase 1. |
| `latexmk` builds | PASS | Executor artifact records `latexmk -g -xelatex -interaction=nonstopmode -halt-on-error balloon511_nima_draft_en.tex`: PASS. |
| Debug grep clean | PASS | `phase1_audit.md`, `phase1_project_audit.md`, and executor local checks report no forbidden internal/debug-token hits over current `.tex` and `.md`. N7 Markdown `\inW_{511}` spacing is fixed. |
| No figure/table after bibliography in built PDF | PASS | Review audit reports all figure/table source locations before the final `\FloatBarrier` and bibliography; executor local `pdftotext` check found no Table/Figure title after References. |
| Project auditor reports no altered sim output or invented value | PASS | `PROJECT_AUDIT_VERDICT = PASS`. The project auditor found no simulation authority output changes, no invented blocking manuscript number, and no project-data hygiene blocker. |
| N1 and N2 consistent with project record | PASS | N1 is traced to Step08/mission-fold project counts (`total_background_counts=67953.7748377242`, rounded to about `6.8e4`). N2 uses the corrected physical effective exposure `20000 / 0.4256743799573773` for the zero-event upper rate, not the stale archived Cosima-time upper-limit value, and propagates to about `0.16%`. |

## Warning disposition

`phase1_audit.md` ends with `REVIEW_AUDIT_VERDICT = WARN`, but the warning is
non-blocking for Phase 1 closure. The remaining review-side warnings are F2
figure redraw/visual QA and C1cite final citation metadata. Both are non-P0
carryovers and are recorded in the Phase 2 backlog, not unresolved Phase 1 gate
items.

For literal Section 6 closure, the ledger status column uses terminal statuses
only. Therefore:

- F2 is terminalized as `APPLIED`; its heavier figure-redraw/visual-QA work is
  carried by backlog item `Bfig`.
- C1cite is terminalized as `APPLIED`; final published metadata checks for
  arXiv/new references remain an author/backlog metadata task.

## Project-audit disposition

`phase1_project_audit.md` records `PROJECT_AUDIT_VERDICT = PASS`. It confirms
that N1, N2, N3, and N6 are traceable to the project record and that no
simulation output or project authority file was altered by the Phase 1
manuscript pass. The N2 correction is explicitly the corrected physical
effective-exposure calculation; the archived Step11 Cosima-time upper-limit
note is stale and is not used for manuscript-facing text.

Explicit remaining backlog path:
`core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/remaining_backlog.md`
