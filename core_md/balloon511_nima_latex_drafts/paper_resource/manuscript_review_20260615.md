# Manuscript Fill-and-Review Log

Date: 2026-06-15.

Scope: current English and Chinese LaTeX drafts in
`core_md/balloon511_nima_latex_drafts/`.

## What Was Checked

- Current rate authority:
  `outputs/reports/v3p5_fullstat_performance_w2_closure_fullstat_v2_exactpos_20260613/v3p5_fullstat_performance_w2_closure_summary.json`.
- Exact-position convergence:
  `outputs/reports/v3p5_exactpos_convergence_20260614/v3p5_exactpos_convergence_summary.json`.
- Exact-position boundary sidecars:
  `outputs/reports/v3p5_boundary_closure_fullstat_v2_exactpos_20260613/v3p5_boundary_closure_summary.json`.
- Current project map:
  `core_md/README.md`, `core_md/workflow.md`, and `core_md/Project_Memory.md`.
- Current BGO sample boundary:
  `Bgo_sample/bgo_sample_summary.json` and
  `Bgo_sample/step02_smoke_summary.json`, plus the delayed-smoke boundary in
  `Bgo_sample/delayed_smoke_summary.json`, and the low-stat exact-position
  day-15 closure in `Bgo_sample/step02_1of10_exactpos_summary.json`.

## Review Findings

- The manuscript headline should remain the v3p5 full-stat exact-position CsI
  chain. The supporting closure summary reports Step05 W2
  `B/S=0.0624651/0.00118117 cps`, Step08 `Z20d=6.15522`,
  `T3=4.73758 d`, and `F3(20d)=4.87391e-5 ph cm-2 s-1`.
- The exact-position delayed source is transport-backed, not only a source-card
  smoke test: four cases cover `M=5000` at two seeds plus `M=20000` and
  `M=50000`; the final W2 background relative range is 1.119%, and the
  `Z20d` relative range is 0.551%.
- The sidecar rows in the headline table are boundary tests. The 45 deg LOS
  rows apply a mission-time atmospheric slant-column model; the annular row is
  a fixed-template post-processing likelihood. They should not be described as
  independent Step05 transported rate rows.
- The BGO equal-attenuation sample is closed at Step01 geometry/control level
  and has a small all-particle Step02 prompt/buildup smoke transport:
  `PASS_BGO_SAMPLE_STEP02_ALLPARTICLE_SMOKE_TRANSPORT` for all eight
  source-card particle classes with 596 generated events in each mode. This
  now also has an activation-probe delayed-source/transport smoke:
  `PASS_BGO_SAMPLE_DELAYED_TRANSPORT_SMOKE`, with 30 true-RPIP
  `PointSource` blocks, `SE=ID=200`, and `TE=5.664515 s`. A later low-stat
  `1of10` exact-position day-15 closure passed with 1,190,129 generated events
  per instant/buildup mode, fixed activity `24.791139 Bq`, 568 true-RPIP
  `PointSource` blocks, `SE=ID=100000`, and `TE=3730.929734 s`. These BGO runs
  still are not a full-statistics Step02, full-statistics day-15 delayed-rate,
  Step05, or Step08 BGO sensitivity chain.

## Edits Made In This Pass

- Added table notes in both English and Chinese drafts explaining why selected
  sidecar `B/S` columns remain dashes.
- Added an explicit limitation in both drafts stating that the BGO
  equal-attenuation control is not part of the current CsI Step02--Step08
  sensitivity chain.
- Updated the BGO limitation wording in both drafts after the BGO sample
  gained all-particle prompt/buildup smoke connectivity. The manuscript now
  says the BGO sample has smoke-scale connectivity only and no full BGO
  background-rate or sensitivity result.
- Added a step-by-step audit-framework paragraph to the workflow section in
  both drafts. This separates Step00--01 geometry closure, Step02 production
  transport, Step03 delayed inventory/source transport, Step04 optics-only
  authority, Step09 optics-to-detector replay, Step05 common selection,
  Step06--08 rate/significance propagation, and Step10 robustness sidecars.
- Tightened the `opticsim_full` wording. The manuscript now says raw B-FULL
  runs come from the external `opticsim_full` environment, while the
  paper-facing optical authority is the repo-copied Step04 authority files and
  Step09 bridge summaries.
- Updated the BGO limitation wording again after the activation-probe
  delayed-source transport smoke passed. The manuscript now separates
  smoke-scale BGO connectivity from production BGO rate authority.
- Updated the BGO limitation wording after the low-stat `1of10`
  exact-position day-15 delayed-source/transport closure passed. The
  manuscript now records the 568-PointSource, 100000-event delayed transport
  as connectivity evidence while keeping it out of the CsI headline
  sensitivity authority.

## External Checks Added On 2026-06-15

- NASA Science still lists COSI as a future mission with launch `2027`.
- HEASARC lists COSI Ge detector energy range `0.2--5 MeV`, angular resolution
  `4.1 deg at 511 keV`, and energy resolution `6.0 keV at 511 keV`.
- arXiv records were found for the four newer bibliography entries checked in
  this pass: Yoneda et al. 2025 (`2509.01066`), Gallego et al. 2025
  (`2510.25304`), Karwin et al. 2023 (`2310.12206`), and Shirazi et al. 2022
  (`2206.14652`).

## Verification Added On 2026-06-15

- `git diff --check` passed after the workflow edits.
- English and Chinese LaTeX drafts compiled successfully with
  `TEXINPUTS=/tmp/elsarticle_ctan/elsarticle//:`.
- Current render outputs: English draft PDF has 19 pages; Chinese draft PDF has
  18 pages.
- Remaining LaTeX issues are layout warnings, mainly overfull result/workflow
  tables and existing long numerical paragraphs. They are not build blockers,
  but should be handled in a later layout pass.

## Still Open

- Replace placeholder author, affiliation, CRediT, acknowledgments, and archive
  identifiers.
- Decide whether to convert the existing SVG requirements chain or create a
  separate workflow figure asset for the current Figure 1 placeholder.
- Verify every external literature reference against primary sources before a
  submission-facing draft.
- Keep BGO material-comparison results out of the manuscript until
  full-statistics all-particle Step02, full-statistics day-15 delayed
  source/rate transport, and downstream Step05--Step08 BGO response are run.
