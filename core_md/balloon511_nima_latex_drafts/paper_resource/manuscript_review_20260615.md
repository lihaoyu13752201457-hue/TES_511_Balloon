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
  day-15 closure in `Bgo_sample/step02_1of10_exactpos_summary.json`, plus the
  full-stat v2 exact-position source/transport closure in
  `Bgo_sample/step02_fullstat_v2_exactpos_summary.json`, plus the BGO focused
  EventList transport in `Bgo_sample/step09_focus_summary.json`, plus the BGO
  Step05 L1 detector-response summary in
  `stepwise_maintenance/step05_veto_time_axis/outputs_bgo_sample_fullstat_v2_exactpos_l1/step05_bgo_sample_l1_response_summary.json`.

## Review Findings

- The manuscript headline should remain the v3p5 full-stat exact-position CsI
  chain. The supporting closure summary reports Step05 W2
  `B/S=0.0624651/0.00118117 cps`, Step08 `Z20d=6.15522`,
  `T3=4.73758 d`, and `F3(20d)=4.87391e-5 ph cm-2 s-1`.
- The manuscript must keep the numerical hierarchy explicit. Step05
  `physical_reference_flux` gives the day-15 selected rates after the unit
  EventList stream is scaled to the f10m A1 effective area and reference
  atmospheric transmission; Step06 gives mission-mean rates; Step08 gives the
  headline significance and flux thresholds. Unit-injection bookkeeping rates
  from intermediate convergence summaries should not be quoted as physical
  point-source signal rates.
- The exact-position delayed source is transport-backed, not only a source-card
  smoke test: four cases cover `M=5000` at two seeds plus `M=20000` and
  `M=50000`; the final W2 background relative range is 1.119%, and the
  `Z20d` relative range is 0.551%.
- The sidecar rows in the headline table are boundary tests. The 45 deg LOS
  rows apply a mission-time atmospheric slant-column model; the annular row is
  a fixed-template post-processing likelihood. They should not be described as
  independent Step05 transported rate rows.
- The BGO equal-attenuation sample is closed at Step01 geometry/control level
  and now has a full-stat v2 exact-position delayed-source/transport gate:
  instant and buildup each generated 25,210,216 events, fixed day-15 activity
  is `23.570474 Bq`, the source uses 5000 equal-flux true-RPIP `PointSource`
  blocks drawn from 43,043 eligible RPIP rows, and delayed transport passed
  with `SE=ID=1000000` and `TE=39653.861364 s`. Earlier smoke and low-stat
  `1of10` closures remain useful provenance. The same branch has a focused
  f10m A1 EventList transport through `Bgo_sample.geo.setup`, with
  `SE=ID=37194`, and now passes Step05 L1 detector response after consuming
  the BGO prompt, exact-position delayed, and focused-signal SIMs together.
  The Step05 W2 direct detector-response expectation is
  `B/S=0.0578455/0.00118595 cps` at `1e-4 ph cm-2 s-1` with a 70 keV BGO
  active-veto threshold. The same label now passes Step06--Step08 mission-time
  folding and source-case propagation: W2 mission-mean `B/S` is
  `0.0578330/0.00117756 cps`, Step08 gives `Z20d=6.43475`,
  `T3=4.21622 d`, and `F3(20d)=4.66219e-05 ph cm-2 s-1`, and the matched
  BGO-vs-CsI exact-position comparison passes. This is now a valid
  hard-window material-comparison result, and the tracked extended closure adds
  BGO detector-coupled spatial cuts, fixed-template annular likelihood,
  detector-threshold replay, and the material attenuation design scan.

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
- Replaced the Figure 1 placeholder in both English and Chinese drafts with a
  manuscript-native step-flow figure covering Step00--01, Step02, Step03,
  Step04, Step09, Step05, and Step06--08.
- Updated the BGO limitation wording after the full-stat v2 exact-position
  delayed-source/transport gate passed. The manuscript now records the
  25,210,216-event prompt/buildup productions, 23.570474 Bq fixed day-15
  activity, 5000 true-RPIP `PointSource` blocks, and `SE=ID=1000000`,
  `TE=39653.861364 s` delayed transport while keeping BGO outside the CsI
  headline sensitivity authority.
- Added an explicit numerical-authority paragraph to the workflow section in
  both drafts. It separates Step05 day-15 selected rates, Step06 mission-mean
  rates, Step08 significance/flux thresholds, and exact-position M/seed
  support claims.
- Expanded the detector/mass-model section in both drafts with the `6 x 376 =
  2256` TES copy count, the engineering nature of the 2 cm W square-bore
  side-entry sleeve, the CsI `50 keV` post-processing veto threshold, and the
  `1 us` coincidence window.
- Expanded the optics, background, and selection method text in both drafts:
  Step09 is now explicitly described as a signal-only EventList handoff with no
  optics-hardware self-background; Step02 prompt normalization is described as
  per-tag `1/sum(TT_tag)` over 68 SIM/DAT products; exact-position source
  construction now states the `253,770` CsI sampling rows; and the conservative
  reconstruction-failure keep policy is stated in the selection section.
- Updated the BGO limitation wording after BGO focused Step09 EventList
  transport passed. The drafts now state that 37,194 focused EventList events
  were generated/stored through BGO geometry. At that pass Step05 was still
  the next required gate; this was superseded by the Step05 PASS entry below.
- Updated the BGO limitation wording after BGO Step05 L1 detector response
  passed. The drafts now state that Step05 consumed the BGO prompt,
  exact-position delayed, and focused-signal SIMs with a 70 keV BGO veto and
  produced direct W2 `B/S=0.0578455/0.00118595 cps` at the reference flux,
  while keeping final BGO sensitivity blocked on Step06--Step08 and the
  BGO-vs-CsI comparison.

## External Checks Added On 2026-06-15

- NASA Science still lists COSI as a future mission with launch `2027`.
- HEASARC lists COSI Ge detector energy range `0.2--5 MeV`, angular resolution
  `4.1 deg at 511 keV`, and energy resolution `6.0 keV at 511 keV`.
- arXiv records were found for the four newer bibliography entries checked in
  this pass: Yoneda et al. 2025 (`2509.01066`), Gallego et al. 2025
  (`2510.25304`), Karwin et al. 2023 (`2310.12206`), and Shirazi et al. 2022
  (`2206.14652`).

## Verification Added On 2026-06-15

- `git diff --check` passed after the workflow and method-fill edits.
- English and Chinese LaTeX drafts compiled successfully with
  `TEXINPUTS=/tmp/elsarticle_ctan/elsarticle//:`.
- Current render outputs after the BGO Step05 limitation update: English draft
  PDF has 20 pages; Chinese draft PDF has 19 pages.
- `python3 -m py_compile code/tools/build_v3p5_centerfinger_step05_l1_response.py
  code/tools/build_bgo_sample_fullstat_exactpos.py
  code/tools/build_bgo_sample_step09_focus.py` passed.
- `python3 code/tools/build_v3p5_centerfinger_step05_l1_response.py --label
  bgo_sample_fullstat_v2_exactpos --workers 8` passed from the cached catalog
  with `PASS_BGO_SAMPLE_STEP05_SIDE_ENTRY_COMPTON_TIME_AXIS_L1_FULLSTAT_V2_EXACTPOS`.
- The BGO Step05 summary records `prompt_files=68`, BGO delayed transport
  `TE=39653.861364 s`, BGO active-veto threshold `70 keV`, catalog stream
  events `675533/291221/36586` for prompt/delayed/science, and W2 direct
  `B/S=0.0578455/0.00118595 cps` at the reference flux.
- `python3 stepwise_maintenance/step06_mission_time_variation/code/build_v3p5_centerfinger_step06_time_axis.py
  --label bgo_sample_fullstat_v2_exactpos` passed with
  `PASS_BGO_SAMPLE_STEP06_TIME_AXIS_FULLSTAT_V2_EXACTPOS`; W2 mission-mean
  `B/S=0.0578330/0.00117756 cps`.
- `python3 stepwise_maintenance/step07_source_cases/code/build_v3p5_centerfinger_step07_source_cases.py
  --label bgo_sample_fullstat_v2_exactpos` passed with
  `PASS_BGO_SAMPLE_STEP07_SOURCE_CASES_FULLSTAT_V2_EXACTPOS`.
- `python3 stepwise_maintenance/step08_significance/code/build_v3p5_centerfinger_step08_time_dependent.py
  --label bgo_sample_fullstat_v2_exactpos` passed with
  `PASS_BGO_SAMPLE_STEP08_TIME_DEPENDENT_FULLSTAT_V2_EXACTPOS`; W2
  `Z20d=6.43475`, `T3=4.21622 d`, and
  `F3(20d)=4.66219e-05 ph cm-2 s-1`.
- `python3 code/tools/build_bgo_sample_csi_comparison.py` passed with
  `PASS_BGO_SAMPLE_VS_CSI_EXACTPOS_COMPARISON`; BGO lowers the matched W2
  mission-mean background by 7.738%, raises `Z20d` by 4.541%, and lowers
  `F3(20d)` by 4.344% relative to the CsI exact-position authority.
- Added a Results subsection/table for the equal-attenuation BGO active-shield
  control in both English and Chinese drafts. The Discussion now references
  that subsection for the material-comparison boundary instead of carrying the
  BGO results as a long limitation paragraph.
- `python3 -m py_compile code/tools/build_bgo_sample_fullstat_exactpos.py`
  passed.
- `python3 code/tools/build_bgo_sample_fullstat_exactpos.py summarize-transport`
  passed with `PASS_BGO_SAMPLE_FULLSTAT_V2_EXACTPOS_DELAYED_TRANSPORT`.
- `python3 -m py_compile code/tools/build_bgo_sample_step09_focus.py` passed.
- `python3 code/tools/build_bgo_sample_step09_focus.py summarize-transport`
  passed with `PASS_BGO_SAMPLE_STEP09_FOCUS_TRANSPORT`,
  `SE=ID=37194`, and BGO geometry confirmed in the SIM header.
- Remaining LaTeX issues are layout warnings, mainly overfull result/workflow
  tables and existing long numerical paragraphs. They are not build blockers,
  but should be handled in a later layout pass.

## Still Open

- Replace placeholder author, affiliation, CRediT, acknowledgments, and archive
  identifiers.
- Optionally replace the manuscript-native Figure 1 step-flow with a polished
  publication figure asset during the layout pass.
- Verify every external literature reference against primary sources before a
  submission-facing draft.
- BGO material-comparison hard-window results are now available and included
  as a limitation/comparison paragraph, but they should not replace the CsI
  exact-position chain as the manuscript headline unless the paper scope is
  deliberately changed.
