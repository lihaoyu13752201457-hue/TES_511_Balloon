# Balloon511 NIM A revision harness ledger

Run directory: `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/`

Initialized by Phase 0 / Agent B0. Gatekeeper update below records terminal Phase 1 statuses; no manuscript edits are made by the Gatekeeper.

Scope decision: default **(b) Reframe to "reference-exposure statistical sensitivity, unresolved line"** is **ASSUMED** pending human sign-off.

`COVERAGE_OK = true`

## Gatekeeper update

Date: 2026-06-23 (local).

Artifacts consumed: `review_inventory.md`, `phase1_delta.md`,
`phase1_audit.md`, `phase1_project_audit.md`, `remaining_backlog.md`,
`pass_1.diff`, current `balloon511_nima_draft_en.tex`, and current
`balloon511_nima_draft_en.md`.

Gatekeeper verdict: `PHASE1_DONE = true`; see `phase1_gate_verdict.md`.
The review audit remains `WARN` only for non-blocking F2 figure-redraw/visual-QA
and C1cite final-metadata carryovers already recorded in `remaining_backlog.md`.
Because harness Section 6 treats only `APPLIED`, `SOFTENED`, `OMITTED`, and
`REJECTED` as terminal Phase 1 statuses, F2's requested
`APPLIED_WITH_BACKLOG` and C1cite's requested
`APPLIED_WITH_METADATA_BACKLOG` are terminalized below as `APPLIED`, with the
carryover rationale preserved in the gate verdict.

## Phase 1 items

Status key for Phase 1 gate: terminal values are `APPLIED`, `SOFTENED`,
`OMITTED`, and `REJECTED`.

| ID | Bucket | Priority | Judgment | Status |
|---|---|---:|---|---|
| N1 | 3A numerical/unit/precision | P0 | HONOR | APPLIED |
| N2 | 3A numerical/unit/precision | P0 | HONOR | APPLIED |
| N3 | 3A numerical/unit/precision | P0 | HONOR | APPLIED |
| N4 | 3A numerical/unit/precision | P0 | HONOR | APPLIED |
| N5 | 3A numerical/unit/precision | P0 | HONOR | APPLIED |
| N6 | 3A numerical/unit/precision | P0 | HONOR | APPLIED |
| N7 | 3A numerical/unit/precision | P2 | HONOR | APPLIED |
| D1 | 3B debug-language purge | P0 | HONOR | APPLIED |
| D2 | 3B debug-language purge | P0 | HONOR | APPLIED |
| D3 | 3B debug-language purge | P0 | HONOR | APPLIED |
| D4 | 3B debug-language purge | P0 | HONOR | APPLIED |
| W1 | 3C claim scoping/wording | P0 | HONOR | APPLIED |
| W2 | 3C claim scoping/wording | P0 | HONOR | APPLIED |
| W3 | 3C claim scoping/wording | P0 | HONOR | APPLIED |
| W4 | 3C claim scoping/wording | P0 | HONOR | APPLIED |
| W5 | 3C claim scoping/wording | P0 | HONOR | APPLIED |
| W6 | 3C claim scoping/wording | P1 | SOFTEN | SOFTENED |
| W7 | 3C claim scoping/wording | P1 | SOFTEN | SOFTENED |
| F1 | 3D figures/tables/citations | P0 | HONOR | APPLIED |
| F2 | 3D figures/tables/citations | P1 | HONOR | APPLIED |
| F3 | 3D figures/tables/citations | P1 | HONOR | APPLIED |
| F4 | 3D figures/tables/citations | P1 | HONOR | APPLIED |
| F5 | 3D figures/tables/citations | P2 | SOFTEN | SOFTENED |
| C1cite | 3D figures/tables/citations | P1 | HONOR | APPLIED |

## Phase 2 backlog items

Status key for Phase 2 initialization: `BACKLOG`.

| ID | Review | Priority | Judgment | Status |
|---|---|---:|---|---|
| B6 | C6 | P0 | HONOR | BACKLOG |
| B3 | C3 | P0/P1 | HONOR | BACKLOG |
| B8 | C8 | P1 | HONOR | BACKLOG |
| B1 | C1 | P1 | SOFTEN | BACKLOG |
| B4 | C4 | P1 | SOFTEN | BACKLOG |
| B9 | C9 | P1 | HONOR | BACKLOG |
| B6d | C6 | P1 | HONOR | BACKLOG |
| B2 | C2 | P1->OPT | SOFTEN | BACKLOG |
| B5 | C5 | OPT | OMIT | BACKLOG |
| B7 | C7 | OPT | SOFTEN | BACKLOG |
| B3d | C3 | OPT | OMIT | BACKLOG |
| BCsI | C6 | OPT | OMIT | BACKLOG |
| Bfig | Section 6 | P1/P2 | SOFTEN | BACKLOG |
