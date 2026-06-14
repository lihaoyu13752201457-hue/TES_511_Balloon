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
  `Bgo_sample/step02_smoke_summary.json`.

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
  and has a small Step02 prompt/buildup smoke transport:
  `PASS_BGO_SAMPLE_STEP02_SMOKE_TRANSPORT` for gamma and proton cards with 512
  generated events in each mode. This still is not a full all-particle Step02
  production, delayed-source, Step05, or Step08 BGO sensitivity chain.

## Edits Made In This Pass

- Added table notes in both English and Chinese drafts explaining why selected
  sidecar `B/S` columns remain dashes.
- Added an explicit limitation in both drafts stating that the BGO
  equal-attenuation control is not part of the current CsI Step02--Step08
  sensitivity chain.
- Updated the BGO limitation wording in both drafts after the BGO sample
  gained a prompt/buildup smoke test: the manuscript now says the BGO sample
  has only gamma/proton smoke connectivity and no full BGO background-rate or
  sensitivity result.

## Still Open

- Replace placeholder author, affiliation, CRediT, acknowledgments, and archive
  identifiers.
- Decide whether to convert the existing SVG requirements chain or create a
  separate workflow figure asset for the current Figure 1 placeholder.
- Verify every external literature reference against primary sources before a
  submission-facing draft.
- Keep BGO material-comparison results out of the manuscript until full
  all-particle Step02, delayed-source construction/transport, and downstream
  Step05--Step08 BGO response are run.
