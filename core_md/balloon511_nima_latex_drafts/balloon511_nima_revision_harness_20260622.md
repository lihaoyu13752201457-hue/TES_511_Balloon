# Balloon511 NIM A revision harness, 2026-06-22 (v3.1)

Execution contract for revising `balloon511_nima_draft_en.tex` against the external review. **Executor: a GPT/Codex agent.** This document is the steering layer; it does the deciding so the executor does not.

*v3.1 closes the pre-run gaps found in review: a Phase-0 coverage gate, a separate Project Auditor, a corrected loop order (apply→build→audit), `.md` decoupled from the loop, an explicit scope default, and tightened N2/N6 (propagate the derived %, never invent the delayed error bar).*

## Operating principle (read first)

Two facts define this run:

1. **The review is deliberately maximal-strictness.** It was written as the harshest possible NIM A referee. Not every demand is worth honoring for this paper.
2. **The simulation/main text is intentionally incomplete.** Many of the review's Priority-0 demands require *new simulation* and cannot be met by editing prose.

Therefore the harness does **not** try to satisfy every review item. It does two bounded things:

- **Phase 1 — Apply everything cheap and doable now**, without touching project data/simulation: numerical-error fixes, unit fixes, precision reduction, debug-language purge, claim scoping, citations, and LaTeX/figure *formatting*.
- **Phase 2 — Emit a judgment-ranked backlog** of what remains, with each item explicitly marked **HONOR** (real, do/plan it), **SOFTEN** (legitimate concern, but the full ask is over-strict — discharge it now with a caveat/label and defer the heavy version), or **OMIT** (over-strict engineering detail, legitimately skipped for this paper's scope, with a one-line rationale).

The triage in §3 is **authoritative and pre-decided**. The executor applies it; it does not re-rank items or re-judge over-strictness. This is the main anti-drift mechanism: the executor cannot inherit the review's over-strictness because the judgment is already fixed here.

## 1. Hard constraints (non-negotiable)

- **`balloon511_nima_draft_en.tex` is the sole writable source of truth.** All loop agents read the `.tex` plus the diff, never the generated copies. The per-pass **build gate is `latexmk`→PDF only** (reproducible). The `.md` is **not** in the loop; regenerate it **once at the end** with the pinned exporter:
  `python3 tools/export_balloon511_tex_to_md.py --input balloon511_nima_draft_en.tex --output balloon511_nima_draft_en.md`
- **Do not touch project data, simulation code, benchmark files, or any figure's underlying values.** The project record (`fix5_benchmarks.json`, `METHOD_FIX5_SIM_CLOSURE.md`, `CONSTRAINTS_FIX5_SIM_CLOSURE.md`, generated reports) is **read-only**.
- **Figure FORMAT may change; figure DATA may not.** Allowed: float placement, sizing, caption length, axis/legend/colorbar labels and units, renaming axes (`x_fp`,`y_fp`), removing a toy diagram, restyling a plot script (fonts/labels) and re-exporting **without changing the numbers it reads**. Forbidden: regenerating or altering any figure's physical content/values.
- **Never invent.** Do not fabricate experimental detail, software versions, uncertainties, or numbers. A quantity the executor does not have goes to the backlog as a stub for the author to fill — not a guessed value.
- **Primary simulation outputs are frozen.** Phase 1 may (a) *round* an over-precise value and (b) *recompute* a quantity that is arithmetically derivable from other quoted numbers (e.g. counts = rate × time). It may **not** change a primary simulation result (e.g. `3.92×10⁻²` cps, `1.19×10⁻³` cps, `Z=7.80`).
- **No Phase-1 attempt on SIM items.** Anything classed `S` in §3 is for the backlog only.
- **`balloon511_nima_draft_zh.tex` is out of scope.** Sync it in a separate pass after Phase 1 closes.

## 2. Artifacts and shared state

Working dir: `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/`

- `review_inventory.md` — Phase-0 coverage map: every external-review item → a §3 ID, or an explicit `omitted/rejected` with reason (see Phase 0).
- `ledger.md` — the §3 triage table, with a live `status` column per item (`OPEN→APPLIED/SOFTENED/BACKLOG/OMITTED/REJECTED`). The only shared state; built once, never re-inventoried.
- `phase1_delta.md` — executor's change log (per item: action taken, exact `.tex` location, before/after snippet).
- `phase1_audit.md` — review-conformance checker's verdicts (see §5).
- `phase1_project_audit.md` — project-consistency auditor's verdicts (see §5).
- `remaining_backlog.md` — the Phase-2 deliverable: the ranked backlog + a short response-to-reviewer paragraph per deferred/omitted item.
- `pass_N.diff` — `git diff` of the manuscript for Phase-1 pass `N` only (not cumulative).

## Phase 0 — review-coverage gate (run once, before Phase 1)

The §3 triage is authoritative, but it was hand-built and could silently miss a review item. Before Phase 1, one pass builds `review_inventory.md`: enumerate **every** comment in `balloon511_nima_review_en_20260622.md` (C1–C10, the C10 numbered bugs, the §5.1/§5.2/§5.3 lists, the §6 figure/table notes, §7 references, §8 priorities) and map each to a §3 ID, or mark it `omitted`/`rejected` with a one-line reason.

`COVERAGE_OK ⇔ every review item maps to a §3 ID or an explicit omit/reject`. Phase 1 does not start until `COVERAGE_OK`. An unmapped item is added to §3 as a new row before proceeding — the only sanctioned edit to the triage.

## 3. Authoritative triage (the core of this harness)

Priority key: **P0** submission-blocking · **P1** strong-paper · **P2** polish · **OPT** optional/over-strict.
Judgment key: **HONOR** do it · **SOFTEN** cheap honest action now + defer heavy version · **OMIT** legitimately skip for this scope.

### 3A — Phase 1, mandatory numerical / unit / precision fixes (all HONOR, P0 unless noted)

| ID | Fix | `.tex` anchor | Note |
|---|---|---|---|
| N1 | `1.09×10⁵` background counts is inconsistent with the quoted rate and `Z`. Recompute `B·T = 0.0393546×20×86400 ≈ 6.80×10⁴` and make the count, `Z`, and threshold mutually consistent. | line 534 | Pure arithmetic from the paper's own rate; do **not** re-simulate. |
| N2 | Zero-event 95% upper rate `1.25×10⁻⁴` → `6.38×10⁻⁵ s⁻¹` (`−ln0.05/(20000/0.425674)`, verified `6.376×10⁻⁵`); current value is ~99.7% CL. **Propagate:** the derived "about 0.32%" at line 646 → **~0.16%** (`6.38e-5/0.0392162`). That same sentence also carries N5 over-precision (`0.0392162`) and D2 debug wording (`current sampled-position`) — fix all three together. | lines 645–647 (src 642) | Arithmetic only. |
| N3 | `S/F₀` has units of area → report as selected effective area `A_sel = 11.86 cm²`, not `s⁻¹/(ph cm⁻² s⁻¹)`. | line 216 | |
| N4 | Photon flux thresholds need `ph`: `ph cm⁻² s⁻¹`. Keep *particle* source-plane fluxes (γ,n,e…) as `cm⁻² s⁻¹`. | `\cms` macro line 20; uses incl. lines 37, 216, 237, 560 | Targeted, not blanket. |
| N5 | Reduce 5–8 sig figs to 2–3 + attach statistical/MC uncertainty. | 37, 216, 251, 282, 560, 592, 618, 630–632 | See N6 for the delayed rate specifically. |
| N6 | `B_delayed = 0.00257520 cps` is over-precise. **The "~30 selected events" is the *review's* back-calculation — it is not stated in the manuscript, so it must not be written as the paper's own.** Action: reduce precision (→ `≈2.6×10⁻³ cps`). For the error bar, the **Project Auditor** traces the actual selected delayed count / `Σw,Σw²` from the delayed-MC output: **if traceable**, attach Poisson `1/√N` or weighted-MC `√Σw²/Σw`; **if not traceable**, quote the rounded value only and move the explicit error to backlog **B6**. Never import the ~30 estimate. | 592, 607 | C6 credibility crux. |
| N7 (P2) | `\inW_{511}` spacing issue exists only in the `.md` export (the `.tex` uses `\wii`). Fix the exporter, not the `.tex`. | macro line 22 | Trivial; export artifact. |

### 3B — Phase 1, debug-language purge (HONOR, P0)

| ID | Action |
|---|---|
| D1 | Rename `exact-position` / `Exact-position` → "production-position-sampled delayed source" throughout (≈15 sites: 48,68,88,99,118,120,127,162,260,266,277,282,284,303,308,393). |
| D2 | Neutralize narrative debug phrasing: `current sampled-position chain`, `full-statistics`, `manuscript-facing`, `headline hard-window result`, loose `closure`/`smoke test` (79,118,140,216,462,485,488,550,648,679). |
| D3 | Move random seeds (`seed 260613`), `M`-sampling serialization, and source-card inventory `PASS` checks (Table 7) to a reproducibility appendix or the repo; strip them from main prose (284,303,308,630,632). |
| D4 (closure check) | A grep for `exact-position|seed 260613|smoke test|full-statistics|manuscript-facing|\bPASS\b|side component` over the `.tex` must return only legitimate, rephrased physics usages (checker confirms each, see §6). |

### 3C — Phase 1, claim scoping & wording (mostly HONOR/SOFTEN, P0–P1)

| ID | Review | Action | Judgment |
|---|---|---|---|
| W1 | C1 | Relabel "3σ **detection time** 2.51 d" → "net on-source **exposure**"; "mission sensitivity" → "reference-exposure statistical sensitivity"; state the synthetic-trajectory + continuous-exposure assumption in abstract & conclusions. | HONOR (P0) |
| W2 | C2 | State explicitly that the headline is an **unresolved-line** sensitivity; state whether Gaussian smearing is per-pixel or per-event. | HONOR (P0) |
| W3 | C3 | Strengthen the existing limitation (lines 666–672): detector/cryostat **proxy only**; lens supports, full payload, and diffuse sky **not** included. Apply the scope decision (§4). | HONOR (P0) |
| W4 | C7 | Define baseline event classes (single-site / valid reconstructed multi-site / unreconstructed) and **stop calling unreconstructed events "FoV-pass"**; state the two-hit assumptions and the multi-hit residual index range. | HONOR (P0) |
| W5 | C8 | Keep `S/√B` explicitly **as a diagnostic only**; add the caveat that a ~1% background-normalization systematic alone drops `Z`≈7.8→~2.8; sketch the in-flight background-estimation strategy qualitatively. | HONOR (P0) |
| W6 | C5 | State σ=0.14 keV is an idealized response; add a one-line response-uncertainty-envelope caveat. | SOFTEN (P1) |
| W7 | title | Optionally retitle toward "Detector-coupled Monte Carlo estimate of background and unresolved-line sensitivity…" per the scope decision. | SOFTEN (P1) |

### 3D — Phase 1, figures/tables/citations (formatting only)

| ID | Action | Judgment |
|---|---|---|
| F1 | Fix float placement so no table/figure renders after `\bibliography` (`\FloatBarrier`/placement; source order is already correct). | HONOR (P0) |
| F2 | Shorten captions; fix tiny labels via restyle; rename focal-plane axes `x_fp`,`y_fp`; replace "data-constrained"→"simulation-derived"; remove visible hyperlink boxes (hyperref styling). | HONOR (P1) |
| F3 | Move Tables 1 & 2 (requirements/workflow) to supplement or merge into one short table; rename Table 7 to an inventory/serialization check and move to supplement. | HONOR (P1) |
| F4 | Remove the toy Compton/FoV event diagram (Fig 9) from the main text. | HONOR (P1) |
| F5 | Merge Tables 5 & 6 into one results table. | SOFTEN (P2) |
| C1cite | Add cheap, uncontroversial citations: Sato 2016 (PARMA4.0), Allison 2016 (Geant4 NIMA), Cowan 2011 (likelihood), Jean 2006, Siegert 2019, De Cesare 2011, Roques 2015, final Yoneda 2025, COSI refs (Gallego/Beechert/Ciabattoni/Sleator). | HONOR (P1) |

### 3E — Phase 2 backlog (SIM-required or heavy; ranked, do NOT attempt in Phase 1)

| ID | Review | Item | Priority | Judgment | Rationale |
|---|---|---|---|---|---|
| B6 | C6 | Increase delayed statistics; multiple `M` and seeds; weighted variance; convergence at the **selected-rate** level. | **P0** | HONOR | Genuinely needed and cheap to run more decays; current 6-s.f. precision on ~30 events is indefensible. Not omittable. |
| B3 | C3 | Full-payload + lens-support mass model and prompt self-background. | P0/P1 | HONOR | Real gap. P0 if any flight-background language is kept; **SCOPED_OUT** if §4 reframes to a subassembly study. |
| B8 | C8 | Profile likelihood with prompt/delayed nuisance params + energy-scale/transmission/`A_eff` uncertainties; median 3σ/5σ + ULs + trials. | P1 | HONOR | The correct final method; the W5 diagnostic+caveat is an acceptable interim for an estimate paper. |
| B1 | C1 | Representative/measured trajectory + slant-column transmission `T(45°)≈0.652` + duty cycle. | P1 | SOFTEN | A representative trajectory + slant-column note suffices; full ephemeris/occultation/repointing budget is over-strict for a sim concept study. |
| B4 | C4 | Source-weight Eq.(1) with units + projected-area handling; archive EXPACS I/O; analytic-geometry benchmark; fine-binned 511 spectrum. | P1 | SOFTEN | The units-complete equation is the real need; full archive/validation is partly over-strict → OPT. |
| B9 | C9 | Simulation-configuration table (versions, physics list, cuts, decay data, seed policy). | P1 | HONOR | Expected for NIM A reproducibility; author-held metadata, not new sim. Codex stubs the table; **author fills values** (no invented versions). |
| B6d | C6 | Decompose selected delayed background by isotope/material/production particle; validate dominant channels. | P1 | HONOR | Strengthens the activation story; modest cost. |
| B2 | C2 | Sensitivities for 1.3 / 2.43 / 5.4 keV FWHM + centroid offsets + multiplicity convolution. | P1→OPT | SOFTEN | Once W2 restricts the headline to "unresolved line," 1–2 representative broad-line cases suffice; the full grid is optional. |
| B5 | C5 | Full detector-effects engine (gain drift, cross-talk, pile-up, saturation, non-linearity, tails). | OPT | OMIT | Heavily over-strict for a Monte Carlo *estimate* with a declared Gaussian response; W6 envelope sentence discharges it; full model is a separate detector-characterization effort. |
| B7 | C7 | Revan/Mimrec cross-validation + uncertainty-weighted ARM + confusion matrix. | OPT | SOFTEN | Over-strict for a first estimate; W4 defines the baseline now, validation is future work. |
| B3d | C3 | Galactic/extragalactic/diffuse-511 sky fields. | OPT | OMIT | An astrophysical foreground, out of scope for a detector instrumental-background study; one sentence in limitations. |
| BCsI | C6 | CsI-vs-alternative-shield trade study (¹²⁸I dominance). | OPT | OMIT | A separate study; add **one sentence** noting ¹²⁸I dominance + flag as future, no trade study. |
| Bfig | §6 | Vector redraws of Figs 2/3–4/5/6/8 with `A_eff(E)`/PSF/encircled-energy, MC error bars, cut-flow split. | P1/P2 | SOFTEN | Legibility restyle is Phase-1 (F2); full physics redraws are real work, lower priority. |

## 4. Scope decision (one human sign-off, before Phase 1)

The single highest-leverage choice; it determines how items W3/B3/B1/B2 resolve. Record the choice at the top of `remaining_backlog.md`:

- **(a)** Keep flight-performance framing → B3/B1 stay P0; heaviest path.
- **(b) [recommended]** Reframe to "reference-exposure statistical sensitivity, unresolved line" (+ retitle W7) → C1/C2/C8 largely discharged by wording; B-items become honest future work.
- **(c)** Downscope to "detector/cryostat subassembly background study" → B3/B3d become out-of-scope, not deferred.

**Default = (b).** If no human choice is recorded in `remaining_backlog.md`, the executor proceeds under (b), flags the assumption prominently for confirmation, and must not silently pick (a) or (c). This is the only item the executor may not decide on its own merits.

## 5. Roles (separate contexts; artifact-only handoff)

Three audit perspectives are kept in separate contexts so no agent certifies its own work (the original three-agent intent: revise / check-against-review / check-against-project).

- **Executor** (write `.tex` + `phase1_delta.md`): applies §3A–3D and the SOFTEN *text actions* of §3C, strictly per the triage. Reads: `.tex`, the review, the ledger, and a **named** project file only if a specific item requires confirming wording (cite the item). Never edits sim data; never attempts §3E.
- **Review checker** (write `phase1_audit.md` only): audits each applied item against its triage row — was the review concern actually *addressed*, not just reworded. Must **quote the `.tex` line changed** and the review clause. Confirms the D4 debug-grep is clean. A verdict without quotes is void.
- **Project auditor** (write `phase1_project_audit.md` only): the independent project-consistency check (restores original Agent C). Reads the **read-only** project record (`fix5_benchmarks.json`, method/constraint files, cited reports) plus the diff. Confirms: no primary sim output was altered; **N1's recomputed background count matches the project's actual background-count *definition*** — do not accept `6.80e4` until the meaning of `1.09e5` is pinned against the record (it may be a different band/stage); N2's propagated `0.16%` is consistent; **N6's error bar is either traced to a real selected count or omitted** (no invented uncertainty); no reworded claim now contradicts a benchmark or report. Quotes the project-source line per verdict.
- **Backlog compiler** (write `remaining_backlog.md` only): emits §3E as a ranked list with the §4 decision and a one-paragraph response per deferred/omitted item. One pass.
- **Gatekeeper** (pure function; writes only the ledger `status` + the pass verdict): consumes `phase1_audit.md` **and** `phase1_project_audit.md`; updates `ledger.md`; evaluates closure (§6). The executor may never author the checker's, auditor's, or gatekeeper's files.

In single-session fallback, run the roles sequentially but **reset context between roles** and pass only the artifacts; the quote rule and the pure-function gatekeeper are what keep it honest.

## 6. Loop protocol and closure (bounded — cannot run forever)

**Phase 0** runs first → `review_inventory.md`; Phase 1 does not start until `COVERAGE_OK`.

**Phase 1** runs as at most **3** passes, in this order — *apply precedes build* so every auditor reads a freshly built manuscript (this is the corrected order):

1. **Snapshot** `git status --short`.
2. **Executor applies** the still-`OPEN` Phase-1 items.
3. **Build** `latexmk`→PDF. If it breaks, the executor fixes LaTeX before any auditor runs.
4. **Diff** since the previous pass → `pass_N.diff`.
5. **Review checker** audits (quote-grounded) → `phase1_audit.md`.
6. **Project auditor** audits against the read-only project record → `phase1_project_audit.md`.
7. **Gatekeeper** updates status and tests the predicate.

```
PHASE1_DONE ⇔ COVERAGE_OK
           ∧ every §3A–3D item ∈ {APPLIED, SOFTENED, OMITTED, REJECTED}
           ∧ latexmk builds this pass
           ∧ D4 debug-grep returns no unrephrased hit
           ∧ no figure/table renders after \bibliography in the built PDF
           ∧ project auditor reports no altered sim output and no invented value
           ∧ N1 count and N2 percentage are consistent with the project record (not merely self-consistent)
```

If `PHASE1_DONE` is false after 3 passes, **stop and escalate** the still-open items (do not loop further). When `PHASE1_DONE`: regenerate the `.md` reading copy once (author's pinned exporter), then run the Backlog compiler once → `remaining_backlog.md`. The harness is then complete.

There is no convergence loop over the review: Phase 0 is one pass, Phase 1 is a finite ≤3-pass checklist, Phase 2 is one-shot. The §3E backlog is a deliverable, **not** a set of gates to drive to zero. This is what makes the harness terminate and keeps the executor from over-honoring an intentionally over-strict review.

## 7. Machine-readable skeleton

```json
{
  "harness": "balloon511_nima_revision",
  "version": 3.1,
  "model": "two_phase_judgment_weighted",
  "roles": ["executor", "review_checker", "project_auditor", "backlog_compiler", "gatekeeper"],
  "executor": "gpt_codex",
  "source_of_truth": "balloon511_nima_draft_en.tex",
  "hard_constraints": [
    "no_edit_project_data_or_sim_code",
    "figure_format_yes_figure_data_no",
    "no_invented_values_or_versions",
    "freeze_primary_sim_outputs_round_or_recompute_only",
    "no_phase1_attempt_on_S_items",
    "zh_tex_out_of_scope"
  ],
  "phase0": {
    "deliverable": "review_inventory.md",
    "gate": "COVERAGE_OK: every review item maps to a section-3 ID or explicit omit/reject",
    "blocks_phase1_until_ok": true
  },
  "phase1": {
    "buckets": ["3A_numeric", "3B_debug_purge", "3C_scoping", "3D_format_cite"],
    "pass_order": ["snapshot", "apply", "build_latexmk_pdf", "diff", "review_check", "project_audit", "gate"],
    "build_gate": "latexmk_pdf_only (md_export_unpinned: regenerate once at end)",
    "max_passes": 3,
    "done_predicate": "COVERAGE_OK AND all_phase1_items_terminal AND builds AND debug_grep_clean AND no_float_after_bib AND no_altered_sim_output AND N1_count_and_N2_pct_consistent_with_project_record",
    "on_fail": "escalate_open_items_to_human"
  },
  "phase2": {
    "deliverable": "remaining_backlog.md",
    "ranked": ["P0", "P1", "P2", "OPT"],
    "judgment": ["HONOR", "SOFTEN", "OMIT"],
    "one_shot": true
  },
  "scope_decision": {"options": ["a_keep_flight", "b_reference_exposure_recommended", "c_subassembly"], "default": "b", "human_signed": true, "executor_proceeds_under_default_flagged": true},
  "anti_drift": "triage in section 3 is authoritative and pre-decided; executor applies, does not re-rank"
}
```
