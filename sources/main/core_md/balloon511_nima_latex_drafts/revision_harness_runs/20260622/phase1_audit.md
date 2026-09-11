# Phase 1 review-conformance audit

Role: independent Review Checker for the Phase 1 Balloon511 NIM A revision harness.

Files read first:

- `core_md/balloon511_nima_latex_drafts/balloon511_nima_revision_harness_20260622.md`
- `core_md/balloon511_nima_latex_drafts/balloon511_nima_review_en_20260622.md`
- `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/review_inventory.md`
- `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/ledger.md`
- `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/phase1_delta.md`
- `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/pass_1.diff`
- `core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.tex`
- `core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.md`

Audit scope: review-conformance only. I did not edit the manuscript, figures, exporter, ledger, or project data. I did not rerun `latexmk`; I used the existing pass-1 PDF plus the current `.tex` source.

## Summary

Mandatory Phase 1 P0 manuscript items are addressed in the `.tex` source. The manuscript no longer exposes the requested internal/debug terms. The remaining review-side issues are non-blocking warnings: F2 is only a partial format/restyle pass rather than a full figure redraw/visual QA, and C1cite still has final-publication metadata caveats for some new references.

## Forbidden-token check

Command-equivalent check over `balloon511_nima_draft_en.tex` and `balloon511_nima_draft_en.md` returned no hits for:

`fix5`, `v3p5`, `exact-position`, `exactpos`, `seed 260613`, `smoke test`, `full-statistics`, `manuscript-facing`, uppercase `PASS`, `source text flux closure`, `current sampled-position`, `headline hard-window`, `hard-window`, `Compton/FoV`, `FoV-pass`, `detection time`, `mission sensitivity`.

Separate N7 check found the generated-Markdown spacing artifact fixed:

- `core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.md:320`: `E_{TES}^{(c)}\in W_{511}`

## Item audit

| ID | Class | Evidence |
|---|---|---|
| N1 | PASS | Review C10.1 asks to replace the inconsistent `1.09e5` count. `.tex:533-535` now says folded counts are about `$6.8\times10^4$ background counts and $2.0\times10^3$ signal counts`. |
| N2 | PASS | Review C10.2 asks for the 95% zero-event limit and propagated fraction. `.tex:629-631` gives `$6.38\times10^{-5}\cps$` and `about $0.16\%$`. |
| N3 | PASS | Review C10.3 asks to report `S/F0` as area. `.tex:232` now states `selected effective area ... $11.9\,\mathrm{cm^2}$`. |
| N4 | PASS | Review C10.4 asks photon thresholds to include `ph`. `.tex:23` defines `\phcms`; `.tex:40`, `.tex:198`, `.tex:232`, `.tex:550`, `.tex:560`, and `.tex:578` use it for photon flux/threshold claims. Particle source-plane fluxes remain particle units at `.tex:253`. |
| N5 | PASS | Review C10.6 asks for reduced precision. Main interpretive rates/thresholds are now rounded: `.tex:550-560` uses `3.92e-2`, `1.19e-3`, `7.80`, `2.51 d`, and `3.85e-5`; `.tex:575` gives delayed activation as `2.6(5)e-3`. Precise integers/constants that remain are source construction inputs rather than headline sensitivity claims. |
| N6 | PASS | Review C6/C10.6 asks not to overstate delayed precision. `.tex:575` reports `2.6(5)\times10^{-3}\cps` with `Statistical scale from 30 selected delayed events`; `.tex:585-589` says source-sampling/model systematics are not included; `.tex:605-606` repeats the 30-event precision limit. |
| N7 | PASS | The `.tex` source uses `.tex:344` `E_{\mathrm{TES}}^{(c)}\in\wii`, and the regenerated `.md` now renders `E_{TES}^{(c)}\in W_{511}` at `balloon511_nima_draft_en.md:320`. No `\inW` hit remains in `.tex` or `.md`. |
| D1 | PASS | Old `exact-position` wording is replaced by production-position language: `.tex:106` says `production-position-sampled delayed decays`; `.tex:117` uses `Production-position`; `.tex:276` captions the production-position source distribution. Forbidden-token grep had no `exact-position`/`exactpos` hit. |
| D2 | PASS | Debug/process phrases were neutralized. Examples: `.tex:136` states the primary rate calculation in publication terms; `.tex:481-486` says `Implementation checks` and `reproduces the mission-fold summary`, not smoke/full-statistics closure language. Forbidden-token grep had no requested D2 hits. |
| D3 | PASS | Seed/PASS/source-card inventory language is out of the main claim path. `.tex:611-620` describes source normalization checks and explicitly says they are not selected-rate convergence. `.tex:666-676` only places `random seeds` in future archive availability. No `seed 260613` or uppercase `PASS` hits. |
| D4 | PASS | Closure grep for the requested debug/project terms over current `.tex` and `.md` returned no hits. Remaining phrases such as `field-of-view` and `line-window` are publication-facing physics wording, not the flagged `FoV-pass`/`hard-window` tokens. |
| W1 | PASS | Review C1 asks to replace elapsed/mission claims with reference exposure. `.tex:40` states `synthetic 20 d trajectory and continuous on-source exposure`; `.tex:560` says `net ... on-source exposure`; `.tex:577` says `Not elapsed flight time`. No `detection time` or `mission sensitivity` hits. |
| W2 | PASS | Review C2 asks to scope the headline as unresolved-line and state smearing. `.tex:34` titles the paper as `unresolved-line sensitivity`; `.tex:333-334` says broader source lines require convolution/re-optimization; `.tex:160` and `.tex:187` state a single Gaussian event-energy proxy and no independent per-pixel smearing. |
| W3 | PASS | Review C3 asks for proxy/full-payload limitations. `.tex:156` says the model is not final flight CAD and excludes `full gondola, optical bench, lens support structure... diffuse celestial fields`; `.tex:650` frames the detector/cryostat model as an immediate boundary. |
| W4 | PASS | Review C7 asks for baseline event classes and no `FoV-pass` label for unreconstructed events. `.tex:355-358` defines single-site, valid reconstructed multi-site, and unreconstructed classes; `.tex:374` defines the multi-hit residual index; `.tex:379-381` says unreconstructed events are retained but `not called field-of-view passing`. |
| W5 | PASS | Review C8 asks to keep `S/sqrt(B)` diagnostic and caveat systematics. `.tex:526-532` calls it a diagnostic metric and states 1% background normalization would reduce significance from about 7.8 to about 2.8; `.tex:576` says no background nuisance parameters; `.tex:652` calls for profile-likelihood practice. |
| W6 | PASS | Review C5 asks for an idealized-response caveat. `.tex:160` states the model omits gain drift, tails, pile-up, saturation, and response scans; `.tex:187` records no independent per-pixel smearing. This is the intended Phase 1 soften, not a full detector-effects model. |
| W7 | PASS | The title was retitled as requested under scope option (b): `.tex:34` `Detector-coupled Monte Carlo estimate of background and unresolved-line sensitivity...`. |
| F1 | PASS | Review Section 6 asks for no tables/figures after references. Source order has all figures at `.tex:108`, `.tex:166`, `.tex:214`, `.tex:221`, `.tex:246`, `.tex:273`, `.tex:291`, `.tex:408`; all tables at `.tex:84`, `.tex:176`, `.tex:308`, `.tex:562`; final `\FloatBarrier` at `.tex:678`; bibliography starts at `.tex:679`. Existing PDF text shows Tables 3-4 on pages 31-32 and `References` starting on page 33. |
| F2 | WARN | Several cheap formatting fixes are present: hidden links at `.tex:17`, shortened captions such as `.tex:217`, and `x_{\rm fp},y_{\rm fp}` at `.tex:224`; `data-constrained` is gone. I did not verify image-pixel label sizes or full vector redraws, and Phase 1 did not complete the heavier figure-redraw requests. Non-blocking P1/Phase 2 carryover. |
| F3 | PASS | Review asks to remove/merge workflow tables and move inventory/PASS table. `.tex:82` says detailed workflow tables are outside main text; `.tex:84-99` keeps one compact traceability table; `.tex:611-620` replaces the old source-inventory table with prose that says checks are not convergence. |
| F4 | PASS | The toy Compton/FoV figure is removed. Current `includegraphics` entries stop at the mass, optics, EXPACS, delayed-position, and selection figures; there is no `fig_compton_fov` or `Compton/FoV` hit. `.tex:404-418` now references only the selection/time-axis figure. |
| F5 | PASS | Tables 5/6 are merged/softened into the primary results table. `.tex:562-578` contains one table with selected rates, prompt/delayed composition, diagnostic Z, net exposure, and unresolved-line threshold. |
| C1cite | WARN | Most cheap citations are added: Jean at `.tex:684`, Siegert 2019 at `.tex:690`, De Cesare at `.tex:705`, Roques at `.tex:708`, Sato 2016 at `.tex:738`, Allison 2016 at `.tex:750`, COSI refs at `.tex:762`, `.tex:768`, `.tex:771`, `.tex:774`, and Cowan at `.tex:777`. Remaining warning: `.tex:693` still cites Yoneda 2025 as arXiv-only, and new COSI metadata at `.tex:762`/`.tex:765` remains arXiv-style rather than final checked publisher metadata. |

## Phase 2 deferral check

The manuscript now scopes claims rather than trying to satisfy simulation-heavy review requests in Phase 1:

- C1/B1 trajectory and duty-cycle work is deferred by `.tex:40`, `.tex:96`, and `.tex:425-430`, which identify a synthetic reference profile and continuous exposure.
- C2/B2 broad-line cases are deferred by `.tex:333-334`, which states broader lines require convolution and re-optimization.
- C3/B3 full-payload/diffuse fields are scoped out of the current model by `.tex:156` and `.tex:654`.
- C6/B6 delayed selected-rate convergence is explicitly not claimed: `.tex:618-620` says source checks are not a substitute for larger delayed-decay statistics; `.tex:646` says higher-statistics convergence remains required.
- C8/B8 likelihood/nuisance treatment is deferred by `.tex:526-532` and `.tex:652`.

These are proper Phase 2/backlog deferrals under the harness and are not review-check failures for Phase 1.

## Verdict

Mandatory Phase 1 P0 review-facing fixes are satisfied in the `.tex` source, and N7 is now fixed in the generated Markdown. The audit remains WARN because non-P0 presentation/citation items remain warning-level.

REVIEW_AUDIT_VERDICT = WARN
