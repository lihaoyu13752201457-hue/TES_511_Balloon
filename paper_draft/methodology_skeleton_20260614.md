# TES 511 keV Balloon Paper Methodology Skeleton

Status: draft methodology skeleton for a first manuscript outline.
Last updated: 2026-06-14.

This file is a paper-facing rewrite of the project workflow in `core_md/`.
It is not yet a full manuscript. It fixes the methods story, the evidence map,
and the tables/figures that should be drafted next.

## Current Paper Claim

The current in-repo rate-level authority is the v3p5 center-finger DR branch
with exact-position delayed-source transport:
`fullstat_v2_exactpos`.

Primary W2 hard-window result:

- W2 window: `510.58-511.42 keV`.
- Step05 W2 background/signal at `1e-4 ph cm^-2 s^-1`:
  `0.0624651/0.00118117 cps`.
- Step06 mission-mean W2 background/signal:
  `0.0626835/0.00117281 cps`.
- Step08 time-dependent result:
  `Z20d=6.15522`, `T3=4.73758 day`,
  `F_3sigma(20d)=4.87391e-5 ph cm^-2 s^-1`.
- 1 Ms comparison:
  `F_3sigma(1Ms)=6.32564e-5 ph cm^-2 s^-1`.

Conservative comparison baseline:
`fullstat_v2` remains the radial-profile delayed-source cross-check, with
`F_3sigma(1Ms)=6.82301e-5 ph cm^-2 s^-1`.

## Evidence Map

- Current authority index:
  `core_md/README.md`, `core_md/workflow.md`, `core_md/Project_Memory.md`.
- Exact-position W2 closure:
  `outputs/reports/v3p5_fullstat_performance_w2_closure_fullstat_v2_exactpos_20260613/v3p5_fullstat_performance_w2_closure_summary.json`.
- M/seed convergence:
  `outputs/reports/v3p5_exactpos_convergence_20260614/v3p5_exactpos_convergence_summary.json`.
- Conservative radial-profile baseline:
  `outputs/reports/v3p5_fullstat_performance_w2_closure_20260612/v3p5_fullstat_performance_w2_closure_summary.json`.
- Boundary sidecars:
  `outputs/reports/v3p5_boundary_closure_20260613/` and
  `outputs/reports/v3p5_boundary_closure_fullstat_v2_exactpos_20260613/`.
- Validation gates:
  `code/tools/validate_v3p5_exactpos_closure.py` and
  `code/tools/validate_v3p5_fullstat_r2.py`.

## Manuscript Skeleton

### Title Candidates

1. Background and 511 keV line sensitivity of a balloon-borne TES Laue-lens telescope
2. Full-chain Geant4 background model for a 511 keV balloon TES spectrometer
3. Exact-position delayed-activation modeling for a balloon 511 keV TES telescope

### Abstract Skeleton

- Motivation: a balloon-borne narrow-line 511 keV instrument needs a
  background model coupled to detector geometry, activation, veto logic,
  focused optics response, and mission time variation.
- Methods: describe the v3p5 DEMO2 center-finger geometry, prompt/buildup
  particle transport, fixed-inventory delayed activation, exact-position
  `PointSource` delayed transport, Step05 detector-response selection, Step06
  mission-time fold, Step07 source-case ledger, and Step08 significance.
- Results: report the exactpos W2 background, signal response, 20-day
  significance, 20-day flux sensitivity, 1 Ms flux sensitivity, and M/seed
  convergence ranges.
- Conclusion: the exact-position delayed-source chain is closed at current
  full-stat scale and gives the present rate-level sensitivity authority;
  sidecars quantify atmospheric and spatial-analysis boundaries.

### Introduction Skeleton

- Paragraph 1: scientific motivation for high-resolution 511 keV line
  measurements from a balloon platform.
- Paragraph 2: background challenge: activation, prompt charged-particle
  backgrounds, side-entry geometry, and narrow-line detector response must be
  modeled together; legacy broad-window or homogeneous-beam numbers are not
  adequate.
- Paragraph 3: study objective: build and validate a full-chain v3p5
  background and sensitivity workflow for the 511 keV TES balloon concept, with
  exact-position delayed activation and mission-time significance.

### Methods Skeleton

#### Step 00-01. Geometry and Detector Model

- Use the DEMO2/v3p5 center-finger detector branch.
- Geometry authority:
  `geo_refer/DEMO2_DR_v3p5_minpatch_centerfinger_bounds.json`.
- MEGAlib proxy setup:
  `outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`.
- Detector concept: TES array with CsI active shield, staged Al windows,
  passive Cu/W shielding, ADR/passive-mass proxies.
- Pointing: local side window points `45 deg` upward via
  `InstrumentFrame.Rotation 0 45 0`.
- Far-field/setup sphere: `60 cm`.
- W side collimator: `2 cm` thick square-bore sleeve.
- Important boundary: native CsI veto trigger blocks exist in the `.det`
  authority, but production SIM files predate those native triggers; quantitative
  active-veto authority is the Step05 post-processing veto model.

Paper wording: this step defines the mass model, detector volumes, injection
plane, and local coordinate system. It is not yet a rate calculation.

#### Step 02. Prompt and Buildup Background Transport

- Use the full-stat v2 prompt and buildup budgets as the background backbone.
- Prompt instant transport: `25,210,216` generated particles.
- Activation buildup transport: `25,210,216` generated particles.
- R2 repair: prompt normalization uses per-tag `1/sum(TT_tag)`, not stale
  one-file or mixed low-stat normalization.
- Keep legacy DEMO2/mainline `equiv2602_aligned` numbers under review hold due
  to the reproduced I-128 `x8.0116` over-normalization.

Paper wording: this step gives the prompt and buildup exposure base. It should
also state that the low-stat `1of10` branch is a closure/debug branch, not the
paper-facing statistics.

#### Step 03. Fixed Delayed Activation Inventory

- Fixed delayed inventory activity for current v3p5 chain:
  `85.636696 Bq`.
- Ground-state and half-life corrections are taken from the R2 source audit
  path with the archived NUBASE2020 table.
- Exact-position source mode:
  sampled equal-flux `PointSource` blocks from weighted RPIP rows.
- Current baseline exactpos source:
  `M=5000`, `seed=260613`, no `RadialProfileBeam` blocks.
- Baseline exactpos delayed transport:
  `SE=1,000,000`, `ID=1,000,000`, `TE=11530.473845 s`.

Paper wording: this step converts activation products into a fixed day-15
delayed source and preserves the activity budget. The main novelty is replacing
the radial-profile compression with sampled exact-position `PointSource`
support.

#### Step 04. B-FULL Laue Optics Simulation

- Use f10m A1 optics authority for focused EventList injection.
- `opticsim_full` / B-FULL model:
  Ge(111) 511 keV Laue lens with standard Geant4 EM competing against a finite
  mean-free-path Laue diffraction process.
- External XOP/CRYSTAL rocking-curve maps provide the diffraction response.
- Current f10m A1 authority:
  `A_eff(511)=20.08476 cm2`, focal length `10000 mm`, `25` tiles,
  `18 mm` tile size, `30 arcsec` mosaicity, and active Ge mass `0.44063 kg`.
- Three-seed B-FULL focal-crossing aggregate:
  `37194` within-Be focal rows, within-Be fraction `0.998336`,
  `r90=1.02853 cm`, `r99=1.24527 cm`.

Paper wording: this step is the physical optics calculation. It supplies
effective area and focused phase space; it does not simulate detector
backgrounds by itself.

#### Step 09. Optics-to-Detector EventList Bridge

- Step09 converts Step04 tracked `focal_crossings.csv` rows into a MEGAlib
  EventList source at the active detector injection plane.
- It uses tracked focal crossings, not the analytic `phase_space.csv`
  projection, to avoid overcounting focused flux.
- f10m A1 v3p5 bridge status:
  `PASS_EVENTLIST_BRIDGE_FULL_TRANSPORTED`.
- Rows written and fully transported:
  `37194/37194`.
- Bridge coordinate policy:
  v3p5 side-entry local frame with `InstrumentFrame` 45 deg tilt,
  Be radius `1.898 cm`, and `0.1 cm` per opticsim mm.
- The Step05 physical reference flux is `1e-4 ph cm^-2 s^-1`.
- Signal response at Step05 W2 hard window:
  `0.00118117 cps` at the reference flux.
- Step07 response:
  `11.8117 cps/(ph cm^-2 s^-1)`.
- The local detector frame must be used for focused-spot spatial cuts; do not
  compute spot radii around the global origin.

Paper wording: Step04 and Step09 are best introduced together in the paper:
Step04 makes the optical signal phase space, and Step09 replays that phase
space through the detector.

#### Step 05. Detector Response and Event Selection

- Step05 parses prompt, delayed, and focused-science detector outputs.
- Selection includes active-veto, side-entry Compton/FoV logic, and W2
  hard-window energy cut.
- W2 hard window: `510.58-511.42 keV`.
- Current exactpos Step05 W2 stream split:
  prompt `0.0590827 cps`, delayed `0.00338234 cps`.
- Top current W2 background component:
  prompt `eplus`, `0.0543377 cps`, `86.99%` of W2 background in the exactpos
  closure summary.
- Delayed W2 top nuclide:
  `Cu64`, `0.00251507 cps`, `74.36%` of delayed W2 events.

Paper wording: this is the step where prompt, delayed, and focused signal are
put under the same detector-response and event-selection definition.

#### Step 06. Mission-Time Folding

- Step06 folds Step05 rates through the mission time axis, including prompt,
  delayed-activity, science-atmosphere scaling, and analytic accidental-veto
  live factors.
- Current exactpos Step06 W2 mission-mean background/signal:
  `0.0626835/0.00117281 cps`.

Paper wording: Step06 is an analytic rate/time fold, not a full atmospheric
particle-transport rerun at every mission time.

#### Step 07. Source-Case Response Ledger

- Step07 builds the source-case response ledger used by Step08.
- Current W2 response:
  `11.8117 cps/(ph cm^-2 s^-1)`.

Paper wording: this step maps detector response to source-case flux units and
keeps the reference flux convention explicit.

#### Step 08. Time-Dependent Significance and Sensitivity

- Step08 computes cumulative counting significance with Gaussian
  `S/sqrt(B)=3` flux-limit scaling for comparison consistency.
- Primary W2 result:
  `Z20d=6.15522`, `T3=4.73758 day`,
  `F_3sigma(20d)=4.87391e-5 ph cm^-2 s^-1`,
  `F_3sigma(1Ms)=6.32564e-5 ph cm^-2 s^-1`.

Paper wording: this is the headline sensitivity step. The main text should
quote Step08 exactpos values and use `fullstat_v2` only as a conservative
radial-profile baseline.

#### Step 10. Exact-Position M/Seed Robustness

The paper should present convergence at the downstream physics level, not only
at source sampling level.

Transport-backed convergence cases:

| label | M | seed | W2 background cps | Z20d | F3 20d |
| --- | ---: | ---: | ---: | ---: | ---: |
| `fullstat_v2_exactpos` | 5000 | 260613 | 0.0624651 | 6.15522 | 4.87391e-5 |
| `fullstat_v2_exactpos_m05000_s260614` | 5000 | 260614 | 0.0631683 | 6.12141 | 4.90083e-5 |
| `fullstat_v2_exactpos_m20000_s260613` | 20000 | 260613 | 0.0627261 | 6.14261 | 4.88392e-5 |
| `fullstat_v2_exactpos_m50000_s260613` | 50000 | 260613 | 0.0629804 | 6.13039 | 4.89365e-5 |

Convergence criteria and results:

- Minimum transport-backed cases: required `>=3`, actual `4`.
- Minimum support sizes: required `>=2`, actual `5000/20000/50000`.
- Repeated seed support: required at least one, actual `M=5000` with
  `260613/260614`.
- W2 delayed cps relative range: `0.187413`, threshold `0.20`.
- W2 background cps relative range: `0.0111915`, threshold `0.05`.
- `Z20d` relative range: `0.00550844`, threshold `0.05`.

Interpretation for the manuscript: the delayed subcomponent has visible Monte
Carlo variation, but the total W2 background and the final significance are
stable enough to promote exactpos to current rate authority.

#### Boundary Sidecars

These should be reported as sidecars, not as the primary hard-window authority.

- 45 deg LOS atmosphere sidecar for `fullstat_v2`:
  W2 `Z20d=5.02544`, `F3_20d=5.96962e-5`.
- Focused `spot_r90` sidecar:
  `spot_r90=1.05164 cm`, keeps `0.9000` of focused W2 signal, background
  `0.0232510 cps`, `Z20d=8.17566`, `F3_20d=3.66943e-5`.
- Fixed-template multi-annulus spatial-likelihood sidecar:
  `Z20d=8.45804`, `F3_20d=3.54692e-5`.
- Boundary language: this is not yet a nuisance-profile publication likelihood.

#### Validation and Reproducibility Gates

- `validate_v3p5_exactpos_closure.py --label fullstat_v2_exactpos` must pass.
- `validate_v3p5_fullstat_r2.py` must pass.
- Reports must distinguish:
  exactpos current rate authority vs radial-profile conservative baseline.
- Legacy DEMO2/mainline rates remain provenance only until div-corrected
  mainline transport and Step05+ chain are rerun.

### Results Skeleton

#### Result 1: Full-Chain Exactpos Sensitivity

Report primary W2 hard-window sensitivity:

- W2 background/signal:
  `0.0624651/0.00118117 cps`.
- `Z20d=6.15522`.
- `F_3sigma(20d)=4.87391e-5 ph cm^-2 s^-1`.
- `F_3sigma(1Ms)=6.32564e-5 ph cm^-2 s^-1`.

#### Result 2: Exactpos M/Seed Robustness

Use the convergence table above and explicitly state that final W2 background
and `Z20d` vary only `1.119%` and `0.551%`, respectively, across the
transport-backed M/seed sweep.

#### Result 3: Background Composition

Report that prompt `eplus` dominates W2 selected events in the exactpos closure
summary; delayed activation is smaller, with `Cu64` the leading delayed nuclide.

#### Result 4: Boundary and Spatial Sidecars

Present 45 deg LOS, `spot_r90`, and fixed-template annular likelihood as
sidecar improvements or boundary checks. Do not mix them into the primary W2
hard-window sensitivity unless the manuscript clearly defines a secondary
analysis.

#### Result 5: Comparison to External Benchmarks

Use the existing performance-curve report as the local data source, but verify
external references and normalize definitions before final paper text. The
current repo already tracks 511-CAM, SPI, and COSI comparison markers, but the
paper needs explicit citation verification before submission.

### Discussion Skeleton

- Main finding: exact-position delayed activation can be carried through the
  full current workflow and is stable at the final W2 sensitivity level.
- Methodological contribution: the workflow couples prompt/buildup transport,
  fixed-inventory activation, exact-position delayed transport, focused optics
  response, active veto, mission-time variation, and convergence validation.
- Conservative comparison: radial-profile compression gives a slightly weaker
  1 Ms sensitivity (`6.82301e-5`) and remains a useful baseline cross-check.
- Boundary interpretation: spatial and LOS sidecars show potential analysis
  gains and atmospheric sensitivity but are not yet a final nuisance-profile
  likelihood.
- Limitations:
  current production detector response uses Step05 post-processing veto rather
  than native-trigger production SIM; external benchmark comparisons need
  publication-grade harmonization; optics self-activation/scattering is not
  included; BGO control remains a geometry scaffold, not a full physics result.

## Table and Figure Plan

### Main Text Tables

- Table 1: Simulation chain and authority products.
- Table 2: Exactpos M/seed convergence cases and final W2 quantities.
- Table 3: Primary W2 sensitivity and conservative radial-profile baseline.
- Table 4: Background composition by prompt/delayed stream and leading nuclides.

### Main Text Figures

- Figure 1: Full-chain workflow diagram from geometry to significance.
- Figure 2: Detector/geometry schematic for v3p5 center-finger side-entry setup.
- Figure 3: W2 background composition plot.
- Figure 4: M/seed convergence plot for W2 background and `Z20d`.
- Figure 5: 1 Ms sensitivity comparison curve.

### Supplementary Material

- Supplement S1: R2 normalization repair and legacy DEMO2 review hold.
- Supplement S2: NUBASE/half-life and ground-state correction audit.
- Supplement S3: Exactpos source builder and sampling audit.
- Supplement S4: Validator outputs and reproducibility commands.
- Supplement S5: Boundary sidecars for 45 deg LOS, `spot_r90`, and annular
  likelihood.

## Commands to Cite as Reproducibility Hooks

```bash
python3 code/tools/build_v3p5_exactpos_delayed_source.py build --source-mode sampled --n-decays 5000 --triggers 1000000 --seed 260613 --workers 8
cosima -s 260613 runs/step02_delay_fix_v3p5_centerfinger_fullstat_v2_exactpos/activation_decay_day15_groundstate_fixed.source
python3 code/tools/build_v3p5_exactpos_delayed_source.py summarize-transport
python3 code/tools/build_v3p5_centerfinger_step05_l1_response.py --label fullstat_v2_exactpos --workers 8
python3 stepwise_maintenance/step06_mission_time_variation/code/build_v3p5_centerfinger_step06_time_axis.py --label fullstat_v2_exactpos
python3 stepwise_maintenance/step07_source_cases/code/build_v3p5_centerfinger_step07_source_cases.py --label fullstat_v2_exactpos
python3 stepwise_maintenance/step08_significance/code/build_v3p5_centerfinger_step08_time_dependent.py --label fullstat_v2_exactpos
python3 code/tools/build_v3p5_exactpos_convergence_report.py --labels fullstat_v2_exactpos fullstat_v2_exactpos_m05000_s260614 fullstat_v2_exactpos_m20000_s260613 fullstat_v2_exactpos_m50000_s260613
python3 code/tools/validate_v3p5_exactpos_closure.py --label fullstat_v2_exactpos
python3 code/tools/validate_v3p5_fullstat_r2.py
```

## Do Not Misquote

- Do not quote legacy DEMO2/mainline delayed-activation sensitivities as
  current authority.
- Do not describe `fullstat_v2_exactpos` as provisional after the 2026-06-14
  convergence closure.
- Do not claim the sidecar annular likelihood is a nuisance-profile
  publication likelihood.
- Do not claim native-trigger production SIM rates; current veto authority is
  the Step05 post-processing selection.
- Do not reuse BGO scaffold numbers as a completed CsI-vs-BGO physics result.

## Next Drafting Steps

1. Convert the Methods Skeleton into `sections/02_methods.md`.
2. Convert the Results Skeleton into `sections/03_results.md`, using the table
   and figure plan above.
3. Build a literature matrix for external benchmark instruments and 511 keV
   balloon context before writing Introduction and Discussion.
4. Decide target journal and word limits before turning this into a full
   manuscript.
