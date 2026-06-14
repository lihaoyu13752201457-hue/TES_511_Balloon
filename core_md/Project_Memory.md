# Project Memory: NEW_GEO_RE 511 keV Balloon Full Chain

Last reviewed: 2026-06-13

This file is the fast re-entry map for the project. Read this first when
returning to the repository, then open the authority files named below only if
you need implementation details or exact tables.

File map (sections, in order):

1. `Current State` -- what this repo is + current headline numbers.
2. `Review Verdict (2026-06-10)` -- full-chain audit result + publication gaps.
3. `The 11-Step Conceptual Chain` -- per-step status, key numbers, authority files.
4. `Branch Memory: BGO Equal-Attenuation Control` -- sibling branch state.
5. `Route B Diffuse Memory` -- diffuse foreground comparison.
6. `Pending Fix Reference` -- numbered to-do items (#1-#7); cited throughout.
7. `What Not To Misquote` -- hard guardrails for quoting numbers.
8. `Fast Authority Map` -- topic -> primary file table.
9. `Recommended Session Start` -- how to begin a session.

Convention: headline counting numbers are the Step06 time-dependent folds
(since 2026-06-04); constant-rate day-15 values are the secondary variant kept
in the same summaries. Never mix the two in one comparison.

## Current State

`new_geo_re` is the CsI DEMO2 mainline for the balloon 511 keV concept:
detector/cryostat mass model, EXPACS atmospheric prompt and buildup
activation, delayed-source transport, focused 511 keV Laue source handoff,
active-shield veto, custom Compton/FoV veto, Poisson time-axis merge, mission
time variation, and counting significance.

Authority hygiene after the 2026-06-12 R1/R2 reviews: the current in-repo
rate-level authority is the v3p5 full-stat v2 chain. Older DEMO2/CsI mainline
paths and headline numbers below are retained as legacy/provenance context
under the delayed-source review hold unless a paragraph explicitly marks them
as current v3p5 authority. Do not treat missing migrated legacy paths as current
inputs.

The current science authority is not the old homogeneous-beam baseline. It is
the Step09 detector-coupled focused EventList chain using the B-FULL Ge(111)
511 keV Laue lens source. CsI mainline headline:

- Optics: `balloon511_f9m_ge111_511line`, `A_eff(511)=15.29928 cm2`.
- W1 design passband: `500.993937-521.006063 keV`.
- W2 line window: `510.58-511.42 keV` (`511 +/- 420 eV`).
- CsI W2 final background: `0.184347 cps`.
- CsI W2 Step06 time-fold headline: `Z20d=2.73543` at `1e-4 ph cm-2 s-1`,
  `T3=24.06 day`, 20-day 3-sigma flux `1.09672e-4 ph cm-2 s-1`
  (constant-rate variant: `Z20d=2.75023`, `T3=23.80 day`).
- CsI detector-coupled `spot_r90` headline (Step06 time fold): background
  `0.0551005 cps`, `Z20d=4.50779`, `T3=8.179 day`, 20-day 3-sigma flux
  `6.655e-5 ph cm-2 s-1` (constant-rate variant: `Z20d=4.52748`,
  flux `6.626e-5`).

Headline convention: the validator and `CURRENT_PROGRESS_STEP_BREAKDOWN.md`
prefer the `*_time_dependent` keys (see File map convention above).

Current A-series documentation/data fixes completed 2026-06-11:

- Route B mainline disk now uses Siegert `sigma_l=60 deg`, `sigma_b=10.5 deg`
  (`fwhm=141.289/24.726 deg`); default Route B FoV flux is now
  `6.26238e-7 ph cm-2 s-1`, W2 `Z20d=0.017223`.
- Step05 `science_rate_ledger.csv` now uses `A_opt_cm2=15.299280`; the
  broad-window Step05 science reference at `1e-4` is `0.000721307 cps`.
- Headline MC statistical uncertainties are available: W2
  `B=0.184347 +/- 0.010339 cps`, `Z20d=2.73543 +/- 0.07671`; `spot_r90`
  `B=0.0551005 +/- 0.0059597 cps`, `Z20d=4.50779 +/- 0.2438`.

Current v3p5 center-finger DR branch checkpoint completed 2026-06-12:

- Geometry authority: `geo_refer/DEMO2_DR_v3p5_minpatch_centerfinger_bounds.json`;
  MEGAlib proxy setup:
  `outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`.
- Pointing/source policy: `InstrumentFrame.Rotation 0 45 0`; local side
  window `-x` looks `45 deg` upward in the zenith-frame source coordinates;
  adaptive far-field/setup sphere is `60 cm`.
- Detector core remains `6 x 376 = 2256` TES pixel copies. The side W
  collimator is a `2 cm` thick square-bore sleeve, not a 376-hole pixel
  collimator.
- Step00 geometry closure status: `STEP00_PASS`; WRL and 2D schematic are in
  `stepwise_maintenance/step00_geometry/outputs/v3p5_centerfinger/`.
- Step02 1/10-statistics closure status:
  `PASS_1OF10_TRANSPORT_CLOSURE`.
  Instant/buildup each passed `19/19` jobs with `1,190,129` generated
  particles. Fixed delayed source has `786` source blocks and
  `86.382997 Bq`. Delayed transport has `SE=100,000`, `ID=100,000`,
  `TE=1140.447373 s`.
- The `1of10` label is historical/path-compatible, not a single exposure
  factor: gamma prompt exposure is about `1/10`, non-gamma prompt exposure is
  about `1/80`, and total generated particle count is about `1/21.2`. Treat
  the branch as low-stat closure only.
- Step02 report:
  `stepwise_maintenance/step02_raw_background_simulation/outputs_v3p5_centerfinger_1of10/step02_v3p5_centerfinger_1of10_summary.md`.
- Step09 v3p5 focused optics bridge now runs the full EventList detector
  transport, not only the smoke source: `37,194/37,194` EventList rows are
  stored in
  `runs/step09_optics_bridge/Opticsim_laue_f10m_a1_v3p5_centerfinger.inc1.id1.sim.gz`;
  bridge status is `PASS_EVENTLIST_BRIDGE_FULL_TRANSPORTED`.
- Unified v3p5 low-stat transport closure report:
  `outputs/reports/v3p5_centerfinger_1of10_closure/v3p5_centerfinger_1of10_closure_report.md`;
  status `PASS_V3P5_1OF10_TRANSPORT_CLOSURE`. Claim level is low-stat v3p5
  closure through Step00/02/05/06/07/08/09, not paper-facing statistics.
- Step05 v3p5 L1 detector response now parses the v3p5 1/10 prompt, day-15
  delayed, and full focused EventList SIMs with v3p5 CsI active-veto matching
  and a side-entry Compton/FoV cone test against the tilted Be disk:
  `PASS_V3P5_STEP05_SIDE_ENTRY_COMPTON_TIME_AXIS_L1`. W2 direct side-Compton/FoV
  rates are prompt `0 cps`, delayed `0.0157833 cps`, and focused signal
  `0.795747` per unit EventList injection rate. The common Poisson time-axis
  W2 side-Compton/FoV rate is `0.800563 cps` under the same unit signal-rate
  normalization.
- Step05 physical reference scaling now uses f10m A1
  `A_eff(511)=20.08476 cm2`, inherited `T_atm=0.739042`, and injection-plane
  rate `0.00148435 s^-1` at `1e-4 ph cm^-2 s^-1`.
  This inherited `T_atm` is a scalar reference, not a recomputed absolute
  45 deg side-entry atmospheric line-of-sight transmission.
- Step06 v3p5 mission-axis fold is `PASS_V3P5_STEP06_TIME_AXIS_1OF10`:
  `stepwise_maintenance/step06_mission_time_variation/outputs_v3p5_centerfinger_1of10/`.
  W2 mission-mean background/signal are `0.0155714/0.00117281 cps`.
- Step07 v3p5 source-case ledger is `PASS_V3P5_STEP07_SOURCE_CASES_1OF10`:
  `stepwise_maintenance/step07_source_cases/outputs_v3p5_centerfinger_1of10/`.
  W2 response is `11.8117 cps/(ph cm^-2 s^-1)`.
- Step08 v3p5 time-dependent significance is
  `PASS_V3P5_STEP08_TIME_DEPENDENT_1OF10`:
  `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_1of10/step08_v3p5_centerfinger_time_dependent.md`.
  W2 reference `1e-4 ph cm^-2 s^-1` gives `Z20d=12.3501`, `T3=0.9428 day`,
  and 20-day 3-sigma flux `2.429e-5 ph cm^-2 s^-1`. Direct constant-rate
  sidecar remains as a cross-check with `Z20d=12.359`.
- Step08 1 Ms performance-curve comparison is
  `PASS_PERFORMANCE_CURVE_COMPARISON_1MS`:
  `stepwise_maintenance/step08_significance/outputs/performance_curve_comparison_1Ms/performance_curve_comparison_1Ms.md`.
  Here `1 Ms = 1,000,000 s`; the best checkpoint case is v3p5 W2 with
  `F_3sigma(1 Ms)=3.13482e-5 ph cm^-2 s^-1`, versus documented current DEMO2
  spot_r90 `8.74842e-5 ph cm^-2 s^-1`.
- Low-stat warning: W2 background uses only `18` final selected background
  events, so this is closure evidence only, not a paper-facing v3p5
  sensitivity.
- Full-stat v2 v3p5 closure completed 2026-06-12 and supersedes the 1/10
  checkpoint for v3p5 rate-level comparisons:
  `outputs/reports/v3p5_fullstat_performance_w2_closure_20260612/`;
  status `PASS_V3P5_FULLSTAT_PERFORMANCE_W2_CLOSURE`.
  Step02 full-stat instant/buildup each passed `68/68` jobs with
  `25,210,216` generated particles. Fixed delayed activity is
  `85.636696 Bq`; delayed transport is gzip-valid with `SE=1,000,000`,
  `ID=1,000,000`, `TE=11531.59846 s`.
- Conservative radial-profile full-stat v2 W2 L1/mission significance baseline:
  Step05 W2 background/signal at `1e-4 ph cm-2 s-1` is
  `0.0729576/0.00118117 cps`; Step06 mission-mean background/signal is
  `0.0730428/0.00117281 cps`; Step08 time-dependent W2 gives
  `Z20d=5.70221`, `T3=5.46687 day`, and 20-day 3-sigma flux
  `5.26111e-5 ph cm-2 s-1`. The 1 Ms comparison gives v3p5 W2
  `F_3sigma(1 Ms)=6.82301e-5 ph cm-2 s-1`.
- Full-stat v2 focused-spot W2 spatial sidecar:
  `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2_spatial/v3p5_spatial_line_proxy.md`.
  Detector-coupled TES centroids are measured in the v3p5 side-window local
  frame, not around the global origin. `spot_r90=1.05164 cm` keeps `0.9000`
  of the focused W2 signal, reduces background to `0.0232510 cps`, and gives
  time-dependent `Z20d=8.17566`, `T3=2.23643 day`, and 20-day 3-sigma flux
  `3.66943e-5 ph cm-2 s-1`. This is a post-processing spatial sidecar; no
  profile-likelihood gain is claimed.
- Boundary-closure sidecars completed 2026-06-13:
  `outputs/reports/v3p5_boundary_closure_20260613/`. The 45 deg side-entry
  LOS sidecar applies the Step06 Beer-Lambert depth model with
  `sec(45 deg)` and gives W2 `Z20d=5.02544`,
  `F3_20d=5.96962e-5`, and `spot_r90` `Z20d=7.20533`,
  `F3_20d=4.16358e-5`. The fixed-template multi-annulus W2 spatial-likelihood
  sidecar gives `Z20d=8.45804` and `F3_20d=3.54692e-5`. These close the
  scalar-`T_atm` and single-cut spatial-analysis boundaries as sidecars; they
  are still not a nuisance-profile publication likelihood.
- Current exact-position delayed-source rate authority completed 2026-06-14 as
  `fullstat_v2_exactpos`:
  `outputs/reports/v3p5_fullstat_performance_w2_closure_fullstat_v2_exactpos_20260613/`.
  The fixed-inventory exact-RPIP `PointSource` source uses 5000 sampled support
  blocks, no `RadialProfileBeam` blocks, and preserves the fixed activity
  `85.636696 Bq`. Cosima delayed transport stored `SE=1,000,000`,
  `ID=1,000,000`, `TE=11530.473845 s`. Step05 exactpos W2
  background/signal is `0.0624651/0.00118117 cps`; Step08 gives
  `Z20d=6.15522`, `T3=4.73758 day`, and 20-day 3-sigma flux
  `4.87391e-5 ph cm-2 s-1`. The 1 Ms comparison gives v3p5 W2
  `F_3sigma(1 Ms)=6.32564e-5 ph cm-2 s-1`. The convergence package
  `outputs/reports/v3p5_exactpos_convergence_20260614/` is
  `PASS_EXACTPOS_TRANSPORT_CONVERGENCE` and recommends
  `PROMOTE_EXACTPOS_TO_CURRENT_RATE_AUTHORITY`. It uses four transport-backed
  cases over `M=5000` seeds `260613/260614`, `M=20000` seed `260613`, and
  `M=50000` seed `260613`; W2 background relative range is `1.119%` and
  `Z20d` relative range is `0.551%`. `fullstat_v2` remains the conservative
  radial-profile baseline cross-check.
- Full-stat v2 W2 background source breakdown:
  `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2/w2_background_source_breakdown/`.
  The selected W2 background is dominated by prompt `eplus`: `80` events,
  `0.0543377 cps`, `74.5%` of the W2 final background. Delayed activation is
  `0.0138749 cps` total; within delayed-only W2 events,
  `Cu64` is the largest nuclide (`52.5%` of delayed events), mainly from
  `ColdPlate_MXC_50mK_SD_anchor` and `Cu_SubstrateSupport_SolidDisk_L0_deepest`.
- Full-stat v2 decay-source normalization audits were backfilled with the
  current TT-line guard:
  `runs/step02_decay_source_v3p5_centerfinger_fullstat_v2/normalization_audit_day15.json`
  and
  `runs/step02_delay_fix_v3p5_centerfinger_fullstat_v2/normalization_audit_groundstate_fix.json`.
  The 1of10 equivalents are also present under the matching `1of10` run
  directories.
- Limitation to keep explicit: `fullstat_v2_exactpos` now replaces the legacy
  axisymmetric delayed-source compression as the current rate authority, but it
  uses sampled equal-flux `PointSource` support rather than the full weighted
  RPIP table as one block per row. The M/seed convergence closure makes this
  adequate for the current W2 rate claim; a full one-block-per-RPIP stress test
  is an optional engineering upgrade, not a current authority blocker.

`../new_geo_re_2` is the BGO equal-attenuation control branch (`70 keV` veto
threshold, equal-stopping material control only). Its state, including the
2026-06-04 native-trigger repair and which of its products are still stale, is
consolidated in `Branch Memory: BGO Equal-Attenuation Control` below.

## Review Verdict (2026-06-10 Full-Chain Review)

Reviewer: Claude (Fable 5). Scope: all 11 steps, the central analysis script,
the Step08 time folds, the delayed-source correction tests, and every numeric
claim in this file checked against the on-disk authority files.

### Overall verdict

- The main chain is structurally sound. No chain-breaking bug was found.
  Validator: 20/20 PASS on the current working tree.
- Physics core audited and found consistent with the documentation: Poisson
  superposition timeline draw; `1 us` chained coincidence grouping;
  summed-shield `50 keV` veto; standard Compton kinematics in the custom
  classifier (kinematic cos-theta, QF sequence selection, cone-vs-Be-window
  test, both orders for 2-hit); per-nuclide activity ODEs; EXPACS/PARMA
  anchoring of Step06. The Step08 time-dependent folds reproduce bit-exactly
  when independently recomputed from the Step06 CSV.
- The "honest downgrade" trajectory is correct, not a regression: replacing
  the placeholder `A_opt=50.89 cm2` with the real Laue `15.30 cm2` and the
  ideal optical focal spot with the detector-coupled Compton-broadened spot
  moved `Z20d` from `~22` to `~4.5`. The paper should present these as the
  real physics numbers and name detector Compton broadening as the main limit
  on focal-spot spatial cuts.
- Findings from this review were addressed by A-series current-data fixes on
  2026-06-11: Step05 science ledger regenerated at `15.29928 cm2` with Step05
  rerun and Step08 refresh; mainline Route B disk corrected to Siegert sigma;
  `experiment_report_20260601` regenerated on time-dependent headline keys.

### Publication readiness (target: NIMA-A)

Scope and genre fit NIMA (new instrument concept + end-to-end background and
sensitivity chain); the chain's rigor is above average for this genre. The
defensible headline claim: balloon Ge(111) Laue lens (`A_eff(511)~15.3 cm2`,
`f=9 m`) plus Ta-absorber TES reaches a 20-day 3-sigma point-source
sensitivity of `~6.7e-5 ph cm-2 s-1` at 511 keV (spot_r90 + W2 selection).

Referee-risk list, ordered. Items 1-2 are submission-blocking; 3-6 are strong
recommendations; 7 is acceptable as stated limitations.

1. Statistical uncertainties on headline backgrounds are quantified as of
   2026-06-11 (A4). W2: `B=0.184347 +/- 0.010339 cps`, `N_eff=317.9`,
   `Z20d=2.73543 +/- 0.07671`; `spot_r90`: `B=0.0551005 +/- 0.0059597 cps`,
   `N_eff=85.5`, `Z20d=4.50779 +/- 0.2438`. Remaining option: extend delayed
   transport statistics beyond 1M events to reduce MC uncertainty.
2. TES performance assumptions at 511 keV need a literature or measured basis:
   `sigma=0.14 keV` (FWHM `0.33 keV`) on a Ta absorber, quantum efficiency,
   saturation, and pile-up at `~1 kHz` total detector rates under multiplexed
   readout (currently only the analytic accidental live factor).
3. Custom Compton/FoV veto: run at least a Revan cross-check on the multi-hit
   subset (Pending Fix #6); referees will ask why not Revan/Mimrec.
4. Delayed-source grid compression: complete the exact-position production
   rebuild (Pending Fix #3). Once done, the grid-vs-exact comparison becomes a
   methods strength instead of a weakness.
5. The current v3p5 activation chain now has an R2 `I-128` CsI anchor:
   `66.0018 Bq` over `62.8337 kg`, or `1.05042 Bq/kg`, in
   `stepwise_maintenance/step03_delay_source/outputs/i128_anchor_r2_20260612.md`.
   The old 2026-06-11 `8.185` vs `6.323 Bq/kg` analytic anchor is retired
   provenance because it used pre-R2 activation products and a no-self-shielding
   two-group reference.
6. ADR vs DR: either rerun on the DR geometry (Pending Fix #2) before quoting
   final numbers, or frame the paper consistently as a representative-cryostat
   concept study.
7. Acceptable as stated limitations: optics hardware self-background
   (`~1e-7 cps` bound, chain section 2), Step06 being a rate-level fold, and
   the Route B aperture treatment of diffuse emission.

## The 11-Step Conceptual Chain

### 1. Detector And Cryocooler Mass Model

Status: legacy DEMO2 detector/ADR/passive-mass provenance. Current in-repo
rate-level authority is the v3p5 center-finger DR branch.

The installed DEMO2 authority was generated by
`tmp_mass_model_review_bundle/DEMO2/build_demo2_mass_model.py` and then copied
into the legacy compatibility path used by the old simulation chain:
`outputs/geometry/XZTES_ADR_v4c_mkflange_cm/TibetTES_ADR_v4c_mkflange_cm.geo.setup`.
That path is pre-R2 provenance only. Current v3p5 geometry authority is
`outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
with bounds in `geo_refer/DEMO2_DR_v3p5_minpatch_centerfinger_bounds.json`.

Authority and checks:

- current v3p5 closure: `stepwise_maintenance/step00_geometry/outputs/v3p5_centerfinger/step00_v3p5_centerfinger_closure.json`
- current R2 validator: `code/tools/validate_v3p5_fullstat_r2.py`
- legacy DEMO2 references: `stepwise_maintenance/step01_geo/README.md`,
  `outputs/geometry/XZTES_ADR_v4c_mkflange_cm/bounds.json`,
  `outputs/geometry/XZTES_ADR_v4c_mkflange_cm/mass_budget.json`

Geometry interpretation, reviewed 2026-06-03:

- `code/geometry/GenerateGeo_ADR_v4c_mkflange.py` is still a legacy v4c
  generator/provenance file, not the source to run for regenerating the current
  DEMO2 authority until it is explicitly reconciled with the installed DEMO2
  bounds.
- DEMO2 is the detector-layout reference, but the current `.geo` is an
  engineering Geant4/Cosima background mass model rather than a final DEMO2 CAD
  reproduction.
- The 2D schematic at `records/00_geometry/geo.png` and its stepwise copies now
  label the ADR/passive proxy masses from `bounds.json`: `Cryoperm_Inner_Mag_Shield`,
  `ADR_Magnet_Coil_Cu`, `ADR_Magnet_Yoke_Fe`, `ADR_SaltPill_Proxy`,
  `ADR_SaltPill_Cu_Can`, `Thermal_Bus_Cu`,
  `ADR_HeatSwitch_Stainless_Link`, `PulseTube_ColdHead_Interface_Cu`, and the
  Cu/W passive liners/shields.
- Current active shield authority is `CsI_Active_Shield` (`mat=CsI`). Historical
  `CeBr3` labels are not current science authority.
- The full A4K/Cryoperm magnetic-shield stack is not modeled. The current
  geometry includes one simplified `Cryoperm_Inner_Mag_Shield` proxy around the
  Nb detector can.
- Reference basis recorded for the mass model: Danaher/HPD Model 103 Rainier
  ADR public information, the 511-CAM mission paper, Kurt J. Lesker aluminum
  chamber material guidance, Oxford Instruments Be-window thickness guidance,
  and the existing `fix` Be-window/aperture convention.

Important boundary: this is the detector/cryostat/background mass model. It
does not include Laue lens mechanical mass as a background-producing object.

### 2. Focusing Optics Model

Status: optical mass/design model and detector-source handoff are present.
The only absent term is the optional upstream optics self-background term.

The current optics handoff is the B-FULL Ge(111) 511 keV line-focused Laue
lens. It uses an external XOP/CRYSTAL rocking-curve map, focal length
`9000 mm`, one ring at 511 keV, `27` tiles, `15 mm` tile size, and
`30 arcsec` mosaicity. Step04 records the optical computation and Be-window
focal crossings.

There are three different meanings that are easy to mix:

- Done: the Laue optical geometry/design package exists: ring radius, tile
  count, tile size, crystal thickness, active Ge crystal mass estimate, A_eff,
  rocking-curve map, and focal-crossing products.
- Done: the optics are simulated as Ge crystals inside the B-FULL opticsim
  Geant4 run for the 511 keV signal photons.
- Done: Step09 records the focal-plane particles that pass the Be-window gate
  and injects them as a MEGAlib EventList source into the detector system
  geometry. This is the current detector-coupled signal authority.
- Not included by design: after the signal-source handoff is complete, the
  upstream lens hardware is not separately treated as an extra EXPACS
  self-background/activation source in Step02/03. That optional term would mean
  cosmic rays hitting the Ge tiles or support structure and producing secondary
  or delayed background unrelated to the focused 511 signal.

Authority:

- `stepwise_maintenance/step04_opticsim/README.md`
- `stepwise_maintenance/step04_opticsim/optics_aeff_authority.json`
- `stepwise_maintenance/step04_opticsim/outputs/step04_opticsim_audit.json`
- `LAUE_LENS_DESIGN_SPEC_20260601.md`
- `FOCUSING_LENS_SCIENCE_RATIONALE_20260601.md`

So "聚焦光学质量模型已经做了" is the correct project-level statement. The only
missing term is a separate, likely second-order self-background term from the
optics hardware. For the current paper scope this can be stated as an
intentional limitation rather than a blocker.

Paper-scope note to remember: if reviewers ask about optics self-background,
state that the current chain transports focused particles produced by the
physical optics model into the detector, but it does not run a separate EXPACS
prompt/buildup activation simulation of the upstream lens hardware itself. The
expected coupling to the detector is small because the lens active Ge mass is
sub-kg and the lens is about 9 m upstream, but this has not been promoted to a
full transport result unless a dedicated optics-background source is generated.

Back-of-envelope check recorded on 2026-06-03: there is no production
activation `.dat` for the current f=9 m Ge(111) lens in `new_geo_re`.
`/home/ubuntu/opticsim` contains an optics activation scaffold, but the
`day15_from_2k_inventory` run has no radioactive candidates and the
`synthetic_al28_day15` run is an interface test, not a physics rate. A rough
scale from `../new_geo_re_2` BGO activation gives about `2.47 Bq` of Ge
nuclides in `~8.23 kg` of Ge content; scaling to the current lens active Ge
mass `0.330 kg` gives `~0.10 Bq`. The Be-window solid angle seen from 9 m is
`pi*(1.898 cm)^2 / (4*pi*(900 cm)^2) ~ 1.1e-6`, so even a one-photon-per-decay,
perfect-detection upper bound is `~1e-7 cps` through the Be aperture. That is
many orders below the current W2 instrumental background (`0.184 cps` for CsI,
`0.0695 cps` for BGO). This supports treating optics self-activation as a small
limitation term for the current paper, not as a required headline correction.

### 3. EXPACS Prompt, Buildup Activation, And Reference 511 Sources

Status: present, split across Step02 and Step07.

EXPACS-derived atmospheric source cards live in
`config/megalib_sources_fullsphere20/Background_*_fullsphere20.source`.
Step02 runs two native COSIMA streams:

- `instant`: prompt atmospheric transport;
- `buildup`: isotope-production transport for delayed activation.

Current CsI event-count-aligned production:

- prompt `instant`: `60/60` jobs, `25,210,216` generated particles;
- activation `buildup`: `60/60` jobs, `25,210,216` generated particles;
- raw delayed source: `6008` source blocks, `624.55914 Bq`;
- ground-state-fixed source: `5968` source blocks, `624.27109 Bq`;
- delayed transport: `1,000,000` stored events, `TE=1584.60761 s`.

Delayed-source spatial representation, reviewed 2026-06-03:

- The Step03 source builder reads true `CC IP RP <VN> x y z ZA exc_keV t`
  production positions, but it does not keep every XYZ point in the final Cosima
  source. To avoid a very large source file, it compresses production positions
  into per-volume/per-nuclide z-bin plus radial-profile `RadialProfileBeam`
  blocks. The current aligned source was generated with `--z-bins 10 --r-bins
  20`; `phi` is therefore regenerated by the radial beam.
- `stepwise_maintenance/step03_delay_source/outputs/delay_source_2d_schematic.png`
  is a sampled delayed-source representation after that z/r compression.
  `stepwise_maintenance/step03_delay_source/outputs/rpip_production_map.png` is
  the raw delayed-relevant RPIP production-position map before compression. Do
  not compare these two images as if they were the same diagnostic.
- Production-map audit: scanning the aligned buildup SIMs found `723,576` total
  `CC IP` lines and `708,537` delayed-relevant RPIP production points; the
  output CSV keeps a deterministic `50,000` point reservoir sample.
- W1 decay-line histogram caution: do not rank W1/511 contributors by total
  isotope activity alone. `I-128` dominates total delayed activity, but its 511
  contribution is only from a very small beta-plus branch; the corrected
  production-map panel uses local Geant4 branch/de-excitation yields and sorts
  by emitted W1 photons/s. In that corrected view `I-128` is not a top W1 line
  contributor.
- Important future check: test whether the current `10 x 20` z/r mesh density is
  sufficient. Compare raw RPIP production maps against sampled
  `RadialProfileBeam` maps, and rerun finer z/r meshes if morphology or detector
  response is sensitive to the compression.

BGO-specific Step03 repair (2026-06-04): native `.det` trigger/veto lines had
filtered BGO buildup SIM storage; details and post-repair numbers are
consolidated in `Branch Memory: BGO Equal-Attenuation Control` below.

Compression-method assessment (2026-06-03 review, condensed; the implemented
upgrade lives in Pending Fix #3 and `tests/realpos_delayed_smoke/README.md`):

- The (r,z)-bin + phi-uniform scheme is a `RadialProfileBeam`
  cylindrical-shell sampling. The dominant delayed-source volumes are
  themselves axisymmetric shells, so it is a natural primitive, not a crude
  approximation. Code defaults are `60 x 100`; the CsI aligned source used
  coarse `10 x 20`. Beta-plus emitters (O-15) used the bounds-uniform fallback
  (8 z-bins, uniform radial inside `r_in -> r_out`, cavity respected).
- Verdict on accuracy: conservative for the 511/O-15 conclusion. For thin
  walls (much thinner than the `~22 cm` nuclear interaction length) production
  is near-uniform across the wall, and uniform-radial OVER-estimates O-15
  escape, so real O-15 is even smaller than reported. The coarse fallback
  z-bins are the real bottleneck for tall side walls; phi-uniform smearing is
  minor for O-15.
- One NON-conservative mechanism to watch: there is no material-containment
  check, so PCON cone/transition segments approximated by one bounding annulus
  can leak decays into adjacent gaps (candidate explanation for the
  `bgo_edep=0` BGO-origin O-15 leak). The exact-position method in Pending
  Fix #3 eliminates this class of error entirely.
- Bottom line: grid compression does not undermine current conclusions, but
  beta-plus emitters deserve exact-position sampling for a referee-proof line
  background. The exact-position method is smoke-validated; see Pending Fix #3
  for the remaining production-rebuild steps.

The simple on-axis 511 science source is in
`config/run_configs/Science_511_onaxis_ADR_cm_local.source` and summarized at
`outputs/reports/science_511_ADR_100k/science_511_100k_summary.json`. V404 is
not a separate full EventList transport for every spectral model; it is a
Step07 transient benchmark/rate-folding source case.

Authority:

- `stepwise_maintenance/step02_raw_background_simulation/README.md`
- `runs/step02_instant_equiv2602_aligned/run_summary.json`
- `runs/step02_buildup_equiv2602_aligned/run_summary.json`
- `stepwise_maintenance/step03_delay_source/README.md`
- `stepwise_maintenance/step07_source_cases/outputs/configs/source_cases_511_ABC.yaml`

### 4. Feed Source Into Focusing Optics And Record Focal-Plane Crossings

Status: present.

Step04 runs opticsim and records tracked diffracted focal crossings. Step09
then converts the accepted `source_tag=laue_bfull_diffracted` focal crossings
inside the Be window into a MEGAlib EventList source at the detector entrance
plane.

Key numbers:

- B-FULL run: `50,000` primaries.
- Diffracted focal crossings: `12,605`.
- Within-Be focused rows: `12,592`.
- Be radius: `1.898 cm`.
- Step09 injection plane: `z=16.051 cm`.
- Max injected radius: `1.45767 cm`.

Authority:

- `stepwise_maintenance/step04_opticsim/README.md`
- `stepwise_maintenance/step09_optics_bridge/README.md`
- `stepwise_maintenance/step09_optics_bridge/outputs/eventlists/Opticsim_laue_new_geo_re.eventlist.dat`
- `stepwise_maintenance/step09_optics_bridge/outputs/run_configs/Opticsim_laue_new_geo_re.source`

Do not use the old analytic `phase_space.csv` projection as the signal
authority; Step09 explicitly rejects it because it overcounts focused flux.

### 5. Inject Focused Source, Prompt Background, And Delayed Source Into The Detector Mass Model

Status: present.

The three physical streams are:

- focused/science stream:
  `runs/step09_optics_bridge/Opticsim_laue_new_geo_re.inc1.id1.sim.gz`;
- prompt atmospheric stream:
  `runs/step02_instant_equiv2602_aligned/*.sim.gz`;
- delayed activation stream:
  `runs/step02_delayed_transport_equiv2602_aligned/DelayedDecayRPIPGroundStateFixed.inc1.id1.sim.gz`.

Step05 parses these products into the common event catalog
`outputs/reports/day15_complete_report/work/event_catalog.pkl`. Step09 also
parses the focused source through detector selections in
`stepwise_maintenance/step09_optics_bridge/outputs/detector_coupled_focus_response.json`.

Authority:

- `code/tools/make_complete_day15_report_ADR.py`
- `stepwise_maintenance/step05_veto_time_axis/README.md`
- `stepwise_maintenance/step09_optics_bridge/code/build_detector_coupled_focus_response.py`

### 6. Use Day 15 As The Baseline Simulation Point

Status: present.

The baseline delayed source is day-15 continuous-exposure buildup with
ground-state half-life correction. Step05 uses the day-15 prompt/delayed/science
streams as the common detector-response reference.

CsI day-15 broad `480-550 keV` baseline:

- timeline raw: `3.85710 cps`;
- timeline active-shield pass: `3.34530 cps`;
- timeline final: `2.34821 cps`;
- direct-expectation final: `2.36653 cps`;
- direct final decomposition: prompt `0.05357 cps`, delayed `2.31224 cps`,
  science at `1e-4` `0.000721307 cps`.

A-series fix completed 2026-06-11: the Step05 `science` stream and the day-15
`science_sensitivity` block now use
`config/science_511_onaxis_source/metadata/science_rate_ledger.csv` with
`A_opt_cm2=15.299280` and preserved `T_atm=7.390423888027e-01`. The event
catalog cache stores per-event science weights, so `make_complete_day15_report_ADR.py`
now refreshes cached science `rate_hz` from the current ledger before computing
Step05 outputs. Old pre-A-series reports normalized to `50.89 cm2` remain wrong
to quote. The broad `480-550 keV` Step05 science reference is still a simple
on-axis/broad-window diagnostic, not the current focused W2/spot paper
headline.

Authority:

- `outputs/reports/day15_complete_report/complete_day15_summary.json`
- `outputs/reports/day15_complete_report/audit.md`
- `stepwise_maintenance/step05_veto_time_axis/README.md`

Remember: broad `480-550 keV` is not the paper headline once focused W2 and
spot cuts are available.

### 7. Scintillator Active-Shield Anti-Coincidence

Status: present.

The active-shield veto is applied after grouping candidate event instances in
a `1.0e-6 s` coincidence window. For the CsI mainline the production baseline
threshold is `50 keV`. The native MEGAlib `.det` `Trigger/Veto` block was
removed on 2026-06-04 (it filtered activation-buildup event storage; see the
repair note in `Branch Memory` below); the validator now asserts its absence
(`csi_det_no_native_trigger_block`). The quantitative veto authority is the
Step05 post-processing layer.

Implementation details:

- active veto volume authority: `CsI_Active_Shield`;
- compatibility match tokens in code: `BGO`, `ACTIVE_SHIELD`, `CEBR3`;
- candidate passes active shield if summed shield energy is below threshold.

Authority:

- current v3p5 response: `stepwise_maintenance/step05_veto_time_axis/outputs_v3p5_centerfinger_fullstat_v2_l1/step05_v3p5_centerfinger_l1_response_summary.json`
- current R2 validator: `code/tools/validate_v3p5_fullstat_r2.py`
- legacy DEMO2 implementation: `code/tools/make_complete_day15_report_ADR.py`
  and `outputs/geometry/XZTES_ADR_v4c_mkflange_cm/TibetTES_ADR_v4c_mkflange_cm.det`

For `../new_geo_re_2`, the BGO equal-attenuation branch uses `70 keV`.

### 8. Custom Compton/FoV Veto

Status: present as a custom post-processing veto, not a full Revan analysis.

The detector is not a clean scatterer/absorber stack, so the project uses a
custom TES-hit Compton/FoV classifier:

- one-hit events are kept;
- two-hit events test both possible first-scatter orders;
- three to six hits enumerate all hit orders, choose the best CSR/QF sequence,
  then test the first Compton cone;
- events with no valid reconstruction are handled by `reject_policy=keep`;
- the back-projected cone is tested against the Be-window disk, currently used
  as the FoV/source acceptance proxy.

Authority:

- `code/tools/make_day15_report_ADR.py`
- `code/tools/make_complete_day15_report_ADR.py`
- `tests/compton_fov_geometry.py`
- `stepwise_maintenance/step09_optics_bridge/code/build_detector_coupled_focus_response.py`

Important boundary: this is a geometry/HT/CC-hit post-processing estimate. A
paper-grade Revan cross-check is still a separate validation upgrade.

### 9. Put Different Event Streams On A Common Time Axis

Status: present.

Step05 draws prompt, delayed, and science event instances according to their
rates, assigns random times over the observation interval, sorts by time, and
groups adjacent instances with `COINCIDENCE_WINDOW_S = 1.0e-6`. Mixed-stream
candidates are therefore naturally handled before active-shield and
Compton/FoV cuts are applied.

Authority:

- `code/tools/make_complete_day15_report_ADR.py`
- `outputs/reports/day15_complete_report/complete_day15_summary.json`
- `stepwise_maintenance/step05_veto_time_axis/README.md`

The same report keeps direct-expectation spectra as a cross-check, but the
formal workflow is the shared Poisson time axis.

### 10. Analytic Trajectory/Time Corrections For Time-Dependent Background And Signal

Status: present as a rate-level fold, now EXPACS/PARMA-anchored
(`L0_expacs_parma_prompt_driver_rate_reweighting_no_new_transport`).

Step06 adds a synthetic/reference trajectory and rate-level time variation
without new Cosima transport. Since 2026-06-04 the prompt and
delayed-production environmental drivers call the official EXPACS/PARMA C++
driver at each of the 81 trajectory bins (scale ranges: prompt detector
`0.8685-1.1683`, delayed production `0.8521-1.1935`). It folds:

- altitude-dependent atmospheric 511 keV transmission;
- EXPACS/PARMA particle-weighted prompt/delayed driver scaling (falls back to
  the analytic depth/cutoff proxy if the PARMA executable is absent);
- delayed activity ODEs per inventory nuclide/volume row;
- Step05 day-15 detector-response closure.

Statistical caveat on the prompt driver weights: the particle weights
(`e+ 0.496 / gamma 0.276 / n 0.228`) are rate-weighted over only `176`
surviving 480-550 keV final prompt events (`e+ 115`, `n 53`, `gamma 8`);
zero-weight particles (`e-`, `p`, `alpha`, `mu`) have zero surviving events by
construction, not by physics. Counts are recorded in
`expacs_prompt_driver_weights.csv` and the driver summary JSON.

Current CsI closure:

- mission bins: `81`, day `0` to `20`, `0.25 day` spacing;
- `T_ref = 0.739042388803`;
- day-15 atmospheric transmission closure error about `3e-13`;
- day-15 final-rate closure below numerical tolerance.

Authority:

- `stepwise_maintenance/step06_mission_time_variation/README.md`
- `stepwise_maintenance/step06_mission_time_variation/outputs/step06_mission_time_variation_summary.json`
- `stepwise_maintenance/step06_mission_time_variation/outputs/background_time_variation.csv`

Caveat: the drivers are EXPACS/PARMA-anchored at rate level, but no time bin
reruns Cosima detector transport and there is no per-nuclide
detector-response matrix. It is a closure-preserving rate-reweighting layer.

### 11. Evaluate Point-Source Performance And Time To 3 Sigma

Status: present.

Step07 defines source cases and folds them through the detector-coupled Step09
science response. Step08 folds the source/background rates over Step06 and
applies an analytic accidental live-time factor. Sidecars provide W2
line-window and focused-spot spatial sensitivity.

CsI current headline (Step06 time-dependent folds, since 2026-06-04):

- W1 mission-axis reference `1e-4`: `Z20d=0.7669`, does not reach 3 sigma in
  20 days; extrapolated T3 is `306.0 day`.
- W2 detector-coupled line window: background `0.184347 cps`,
  time-fold `Z20d=2.735`, T3 `24.06 day`, 20-day 3-sigma flux `1.097e-4`
  (constant-rate variant: `Z20d=2.750`, T3 `23.80 day`).
- Focused `spot_r90`: signal fraction `0.9000`, background `0.0551005 cps`,
  time-fold `Z20d=4.508`, T3 `8.18 day`, 20-day 3-sigma flux `6.66e-5`
  (constant-rate variant: `Z20d=4.527`, flux `6.63e-5`).

Authority:

- `stepwise_maintenance/step07_source_cases/README.md`
- `stepwise_maintenance/step08_significance/README.md`
- `stepwise_maintenance/step08_significance/outputs/line_window_sensitivity.md`
- `stepwise_maintenance/step08_significance/outputs/spatial_line_proxy.md`
- `outputs/reports/experiment_report_20260601/experiment_report.md`

## Branch Memory: BGO Equal-Attenuation Control

`../new_geo_re_2` is the BGO-vs-CsI control branch created from this mainline.
Its execution spec is
`../new_geo_re_2/EXECUTE_NEW_GEO_RE_2_BGO_CSI_FULLCHAIN_20260602.md`.

Stable geometry facts (valid across the repair):

- Geometry: equal-attenuation BGO, side `2.137 cm`, bottom `4.459 cm`,
  top `1.041 cm`, veto threshold `70 keV`.
- Active mass: `47.0739 kg`, `0.722493` of CsI active mass.
- Attenuation check: max abs relative difference `0.0896603`, PASS under
  10% tolerance.
- Step02 prompt and buildup: both `25,210,216` generated particles.

2026-06-04 native-trigger repair (the authoritative BGO source state):

- Cause: native MEGAlib `Trigger/Veto` blocks in the transport `.det` filtered
  buildup SIM storage to triggered/veto-passing events only, under-recording
  true `CC IP RP` production positions (representative neutron rep01 stored
  only `~2,071` events before the fix). The blocks were removed from BOTH the
  CsI and BGO `.det` files; the mainline validator now asserts absence.
- Full-store buildup rerun:
  `../new_geo_re_2/runs/step02_bgo_buildup_equiv2602_fullstore_20260604`,
  `60/60` jobs, `25,210,216` generated events, `~6.039 GB` SIM output. Stored
  populations are now full (e.g. neutron rep01 `ID=963,066`, gamma part01
  `ID=2,500,000`).
- BGO Step03 rebuilt from the full store: `123,630` total `CC IP` lines,
  `99,386` delayed-relevant RPIP points (vs the old `7,520`-point map),
  `50,000`-point deterministic sample.
- Post-repair delayed source: raw `16,084` blocks `17.2369743619 Bq`; fixed
  `15,947` blocks `17.2376533918 Bq`.
- 2026-06-12 source-normalization audit from this checkout:
  `runs/step02_bgo_delay_fix_div8_review_20260612/` reread the external
  full-store BGO buildup dat/source with file-count guards. Non-gamma tags have
  `8` files and `division=8`; gamma has `4` files and `division=4` (`auto`).
  Raw source activity is `17.2369743619 Bq`; mean-TT/auto-gamma ground-state
  fixed activity is `17.1837179460 Bq`. This rules out a source-level `x8`
  inflation in the repaired BGO source, but does not refresh downstream
  Step06/07/08 or the comparison report.
- Delayed transport, Step05, and Step09 were rerun after the repair.

STALE -- do not quote until Pending Fix #5 rerun completes. These 2026-06-03
pre-repair values are superseded upstream (Step06/07/08, Route B, validator,
and the BGO-vs-CsI report have not been rerun against the repaired source):

- fixed delayed source `13,800` blocks / `17.128648 Bq` (superseded by the
  post-repair source above);
- delayed transport `TE=329111.439246 s`;
- BGO W2 background `0.0694972 cps`, `Z20d=4.46775`;
- BGO `spot_r90` background `0.0116677 cps`, `Z20d=9.81403`,
  20-day 3-sigma flux `3.05685e-5 ph cm-2 s-1`;
- the "final validator/report PASS" status.

BGO authority files:

- `../new_geo_re_2/PROJECT_MEMORY.md`
- `../new_geo_re_2/project_state.json`
- `../new_geo_re_2/outputs/reports/experiment_report_20260602/experiment_report.md`
- `../new_geo_re_2/outputs/reports/validation_new_geo_re_2/validation_new_geo_re.json`

Interpretation boundary: this result says that equal-stopping BGO performs
better than the current CsI authority in this chain. It does not prove BGO is
mass-optimal, same-envelope-optimal, or mechanically optimal.

## Route B Diffuse Memory

Route B is an aperture/rate-folded diffuse foreground comparison, not a focal
spot Cosima source. The default bulge/disk flux is folded through the Be-window
FoV solid angle, Step06 atmospheric transmission, and current detector response.

CsI default Route B result:

- default 8-deg bulge plus disk FoV flux: about `6.262e-7 ph cm-2 s-1`;
- W2 `Z20d=0.017223`;
- diffuse signal remains a null/foreground comparison.

Critical caveat for future edits: the disk model must use Siegert sigma fields
`sigma_l_deg=60`, `sigma_b_deg=10.5`, or equivalent FWHM `141.29/24.73 deg`.
Do not repeat the old bug of treating `60/10.5` as FWHM and dividing by 2.355.
Mainline Route B was FWHM-narrowed until 2026-06-11; it is now sigma-correct and
matches the BGO branch sky-model fields for the disk row. The old narrowed
proxy overestimated disk FoV flux but did not change the null conclusion.

Authority:

- `ROUTE_B_DIFFUSE_SUPPLEMENT_20260602.md`
- `outputs/reports/route_b_diffuse_supplement_20260602/route_b_diffuse_summary.json`
- `stepwise_maintenance/step07_source_cases/outputs/diffuse_aperture_foreground.csv`

## Pending Fix Reference

This section is a quick "待修参考" list. Items here are not current science
authority until the named modeling and rerun work is done.

1. `laue.png` lens-reference cleanup.

   Treat the image values as a design/reference target, not as a replacement for
   the current Step04 optics authority. In particular, `Focus area = 100 cm2`
   should be treated as focal-plane/imaging area unless a separate 511 keV
   effective-area table says otherwise; do not quote it as `A_eff=100 cm2`.

   For Ge(111), 511 keV, and `f=10 m`, the 511 keV Bragg ring radius is about
   `7.43 cm` (`diameter ~14.9 cm`). The 450-550 keV range maps to radii about
   `8.43-6.90 cm`. A single 511 keV ring with current-like mosaicity can support
   the narrow 511 line / W1-style response, but it does not by itself satisfy a
   full `450-550 keV` broadband requirement plus `5 arcmin` off-axis FoV. A real
   `laue.png` replacement needs an explicit ring/tile/mosaic/thickness/off-axis
   optics model and a rerun of Step04/Step09/Step07/Step08.

   Useful current-scale estimates to avoid future confusion:

   - Current B-FULL authority: `A_eff(511)=15.29928 cm2`.
   - Ge(111), `f=10 m`, Bragg-annulus estimate: `A_eff ~18 cm2`,
     `F3_1Ms(spot_r90) ~7.5e-5 ph cm-2 s-1`.
   - If a 511-tuned lens is designed to `A_eff=20 cm2`, it is only a modest
     upgrade: `F3_1Ms(spot_r90) ~6.7e-5 ph cm-2 s-1`. A current-efficiency
     sketch is about `80 cm2` of crystal face area, roughly `35` tiles of
     `15 mm x 15 mm` equivalent area, on a `~15-18 cm` active ring.
   - If `100 cm2` is only imaging/focal-plane area, it does not increase signal
     effective area. If it were instead a 511-tuned crystal-geometry what-if,
     current-efficiency scaling would give `A_eff ~25 cm2` and
     `F3_1Ms(spot_r90) ~5.3e-5 ph cm-2 s-1`.
   - Do not use the full `40 cm` diameter support/aperture as 511 keV effective
     area. For simple Ge(111), 511 keV at 10 m lives on the `~14.9 cm` diameter
     Bragg ring; the outer diameter is not automatically 511 keV collecting
     area.

2. Final cooler architecture should be DR, not ADR.

   The current DEMO2 mass model is an ADR/passive-background proxy. If the final
   instrument concept is a dilution refrigerator / mini-DR system, the detector
   geometry and mass model must be rebuilt before quoting final backgrounds or
   sensitivities. At minimum remove or replace ADR-specific structures such as
   `ADR_Magnet_Coil_Cu`, `ADR_Magnet_Yoke_Fe`, `ADR_SaltPill_Proxy`,
   `ADR_SaltPill_Cu_Can`, and `ADR_HeatSwitch_Stainless_Link`. Do not blindly
   delete generic cold-stage structures such as TES can/shields, thermal buses,
   cold plates, or pulse-tube interfaces; decide which remain in the DR layout
   and which become DR-specific mixing-chamber/still/heat-exchanger/plumbing
   proxies.

   Required rerun after DR geometry replacement:

   - regenerate geometry, bounds, mass budget, schematic, `.geo.setup`, `.det`,
     and overlap validation;
   - rerun Step02 prompt and activation buildup;
   - rebuild Step03 delayed source, RPIP maps, and source audits;
   - rerun delayed transport, Step05 time-axis/veto catalog, Step06 time
     variation, Step07 source cases, Step08 significance, and Step09
     detector-coupled focus response;
   - refresh validator, final Route-A report, and any BGO/CsI comparison if the
     comparison is still needed.

   Until that rerun exists, current ADR-derived background and 3-sigma numbers
   are a detector/cryostat mass-model proxy, not the final DR instrument result.

3. Delayed-source spatial sampling upgrade.

   The CsI source still uses coarse `10 x 20` z/r compression. The BGO repair
   uses finer `60 x 100` true-RPIP rows plus fallback rows, but mesh sensitivity
   is still not closed.

   Progress 2026-06-09/10 (`tests/realpos_delayed_smoke/`): the exact-RPIP
   point resampling method recommended above is now **validated feasible**.
   Cosima parsed and ran 2000 exact-position `PointSource` decay blocks in
   ~2.1 s, emitted positions match the exact input cloud at 99.05% (rest is
   3-decimal rounding) -- zero radial smearing. `fidelity_vs_grid.csv`
   quantifies the grid's thin-wall failure (verified against
   `makedecaysourcewithplot_rpip.py`: radial bins really run
   `linspace(0, r_max_99.5pct)` per volume/nuclide): `Passive_W_Outer_Liner`
   0.6 mm wall vs 5.0 mm grid bin = 0.12 bins across the wall.
   `reparse_full_rpip_table.py` rebuilt the complete 723,576-row weighted RPIP
   table (~99 MB, gitignored) fixing the 50k reservoir gaps (992 low-activity
   species, 0.76% activity) and carrying per-point `wfile` plus
   `in_fixed_inventory`.

   Remaining for a production rebuild (see the tests README "Filter semantics"
   section): use ground-state-fixed activities (not raw), keep `(VN, ZA, exc)`
   granularity, sample with the `in_fixed_inventory` filter (708,370 rows;
   the raw-inventory filter gives 708,537 -- difference is exactly 167 points
   of species removed by the ground-state fix), use per-point `wfile` within
   species, and set `M` = full trigger budget (e.g. 1e6). After the rebuild,
   rerun delayed transport and Step05+ downstream.

4. Optics hardware self-background.

   The current chain transports focused photons from the physical optics model
   into the detector, but it does not run a separate EXPACS prompt/buildup
   activation simulation of the upstream lens hardware itself. Keep this as a
   paper limitation unless a dedicated optics-background source is generated.

5. BGO branch stale-after-refresh work.

   In `../new_geo_re_2`, the 2026-06-04 full-store BGO repair reran delayed
   transport, Step05, and Step09, but Step06, Step07, Step08, Route B, validator,
   and the BGO-vs-CsI report remain stale until rerun against the refreshed
   Step05 authority. The 2026-06-12 source-level audit in this checkout rules
   out a repaired-source `x8` normalization inflation (`17.2369743619 Bq` raw,
   `17.1837179460 Bq` mean-TT/auto-gamma fixed), so the remaining blocker is
   downstream rerun, not source activity scale. Also update `project_state.json`;
   it still contains older canonical values.

6. Analysis validation upgrades.

   Step06 remains a rate-level fold, not per-time-bin Cosima transport; a future
   upgrade is a per-nuclide detector-response matrix or selected time-bin
   transport checks. The custom Compton/FoV veto is not a full Revan/Mimrec
   reconstruction; a paper-grade cross-check for the multi-hit subset remains a
   separate validation upgrade.

7. Items found in the 2026-06-10 full review (A-series status).

   - DONE 2026-06-11: Step05 science ledger regenerated with
     `A_opt_cm2=15.299280`, Step05 rerun, and Step08 refreshed. Outputs:
     `config/science_511_onaxis_source/metadata/science_rate_ledger.csv` and
     `outputs/reports/day15_complete_report/complete_day15_summary.json`.
   - DONE 2026-06-11: mainline Route B disk now treats Siegert `60/10.5` as
     sigma and records equivalent FWHM `141.289/24.726 deg`. Outputs:
     `outputs/reports/route_b_diffuse_supplement_20260602/` and
     `ROUTE_B_DIFFUSE_SUPPLEMENT_20260602.md`.
   - DONE 2026-06-11: `experiment_report_20260601` regenerated with
     time-dependent headline keys and labeled constant-rate variants. Output:
     `outputs/reports/experiment_report_20260601/experiment_report.md`.

## What Not To Misquote

- Do not quote the 2026-05-31 DEMO2/mainline delayed-activation numbers
  (`fixed_activity=624.27109184 Bq`, W2 background `0.184347 cps`,
  `spot_r90` background `0.0551005 cps`, or derived `Z20d`/flux headlines)
  as current authority. The 2026-06-12 Claude review was reproduced in this
  checkout: mainline I-128 is `533.28 Bq` while the Geant4 production rate is
  `66.56/s`, i.e. a `x8.0116` normalization inflation from multi-rep buildup
  source construction. Treat those DEMO2 values as legacy pre-fix references
  until a div-corrected mainline source and downstream Step05+ chain are run.
- Do not quote the pre-R2 v3p5 fullstat_v2 prompt-normalization headlines:
  W2 background `0.486136 cps`, Step08 `Z20d=2.20208`, 20-day 3-sigma flux
  `1.36235e-4 ph cm-2 s-1`, 1 Ms flux `1.76837e-4 ph cm-2 s-1`, or prompt
  `eplus` fraction `89.3%`. The 2026-06-12 R2 review found and fixed the
  Step05 prompt override missing the non-gamma multi-rep exposure normalization.
  Conservative radial-profile fullstat_v2 W2 baseline is `0.0729576 cps`,
  `Z20d=5.70221`, `F_3sigma(20d)=5.26111e-5`, and
  `F_3sigma(1Ms)=6.82301e-5`.
- Do not describe `fullstat_v2_exactpos` as provisional after the 2026-06-14
  convergence closure. It is now the current exact-position rate authority:
  W2 background `0.0624651 cps`, `Z20d=6.15522`, and
  `F_3sigma(1Ms)=6.32564e-5`. Keep `fullstat_v2` as the conservative
  radial-profile baseline cross-check.
- Do not compute v3p5 side-entry focused-spot radii around the global origin.
  The correct sidecar uses the local side-window frame and gives
  `spot_r90=1.05164 cm`, not the invalid global-origin `~6 cm` scale.
- Do not quote historical CeBr3, old homogeneous-beam, or broad-window-only
  numbers as the current focused Route-A authority.
- Do not use broad `480-550 keV` day-15 final rates as W2 or spot-cut results.
- Do not claim optics hardware activation/scattering is included.
- Do not claim Route B receives point-source spot-cut gains.
- Do not reuse CsI detector-coupled EventLists as BGO results. The repaired BGO
  delayed source passed a 2026-06-12 div=8/gamma-auto source-level audit, but
  external-branch Step06/07/08, Route B, validator, and the BGO-vs-CsI report
  remain stale until rerun against the refreshed BGO Step05 authority.
- Do not treat Step06 as a full atmospheric transport rerun; it is an analytic
  trajectory/time proxy closed to Step05.
- Do not treat custom Compton/FoV veto as a full Revan reconstruction.
- Do not confuse the Step03 delayed-source sampling plot with the raw RPIP
  production-position plot; the former includes z/r `RadialProfileBeam`
  compression and regenerated azimuth.
- Do not quote the Step05 broad-window science decomposition or its
  `science_sensitivity` flux limits as the focused-optics science response.
  The ledger was fixed on 2026-06-11 to the B-FULL `15.29928 cm2` lens, but
  Step05 remains a broad-window/simple on-axis diagnostic; old pre-A-series
  reports and archives normalized to `50.89 cm2` are wrong to quote.
- `outputs/reports/experiment_report_20260601/experiment_report.md` was
  regenerated on 2026-06-11 with time-dependent headlines and labeled
  constant-rate variants. Do not quote old copies or
  `outputs/reports/experiment_report_20260601_pre_a_series_20260611/`.

## Fast Authority Map

| Topic | Primary file |
| --- | --- |
| Current repo overview | `README.md` |
| Step status | `stepwise_maintenance/CURRENT_PROGRESS_STEP_BREAKDOWN.md` |
| R2/v3p5 validator | `code/tools/validate_v3p5_fullstat_r2.py` |
| v3p5 detector geometry | `outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup` |
| v3p5 bounds | `geo_refer/DEMO2_DR_v3p5_minpatch_centerfinger_bounds.json` |
| v3p5 geometry closure | `stepwise_maintenance/step00_geometry/outputs/v3p5_centerfinger/step00_v3p5_centerfinger_closure.json` |
| v3p5 prompt/buildup runner | `code/tools/run_equiv2602_pipeline_NEW_GEO.py` |
| v3p5 full-stat Step02 summary | `stepwise_maintenance/step02_raw_background_simulation/outputs_v3p5_centerfinger_fullstat_v2/step02_v3p5_centerfinger_fullstat_v2_summary.json` |
| v3p5 full-stat Step05 response | `stepwise_maintenance/step05_veto_time_axis/outputs_v3p5_centerfinger_fullstat_v2_l1/step05_v3p5_centerfinger_l1_response_summary.json` |
| v3p5 prompt normalization audit | `stepwise_maintenance/step05_veto_time_axis/outputs_v3p5_centerfinger_fullstat_v2_l1/prompt_normalization_audit.json` |
| v3p5 full-stat Step06 time variation | `stepwise_maintenance/step06_mission_time_variation/outputs_v3p5_centerfinger_fullstat_v2/step06_v3p5_centerfinger_fullstat_v2_summary.json` |
| v3p5 full-stat Step07 source cases | `stepwise_maintenance/step07_source_cases/outputs_v3p5_centerfinger_fullstat_v2/source_case_summary.json` |
| v3p5 full-stat Step08 significance | `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2/step08_v3p5_centerfinger_time_dependent_summary.json` |
| v3p5 full-stat W2 closure | `outputs/reports/v3p5_fullstat_performance_w2_closure_20260612/v3p5_fullstat_performance_w2_closure_report.md` |
| v3p5 full-stat `spot_r90` sidecar | `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2_spatial/v3p5_spatial_line_proxy.md` |
| v3p5 boundary-closure sidecars | `outputs/reports/v3p5_boundary_closure_20260613/v3p5_boundary_closure_report.md` |
| f10m A1 optics authority | `stepwise_maintenance/step04_opticsim/optics_aeff_authority_f10m_a1.json` |
| v3p5 EventList bridge | `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/step09_optics_bridge_summary.json` |
| v3p5 detector-coupled focus response | `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/detector_coupled_focus_response.json` |
| CsI activation R2 I-128 anchor | `stepwise_maintenance/step03_delay_source/outputs/i128_anchor_r2_20260612.md` |
| Final Route-A report | `outputs/reports/experiment_report_20260601/experiment_report.md` |
| Delayed-source exact-position upgrade | `tests/realpos_delayed_smoke/README.md` |
| Stepwise figure pack | `stepwise_maintenance/figure_pack/build_stepwise_figure_pack.py` |
| Migration contract for a new branch | `Project_List.md` |
| BGO branch memory | `../new_geo_re_2/PROJECT_MEMORY.md` |

## Recommended Session Start

1. Read this file through `Current State`, `Review Verdict`, and
   `What Not To Misquote`; open chain sections only as needed.
2. Before quoting or changing any number, check `Pending Fix Reference` for an
   open item touching it.
3. If working on CsI mainline, open `README.md`,
   `stepwise_maintenance/CURRENT_PROGRESS_STEP_BREAKDOWN.md`, and the validator
   JSON.
4. If working on BGO/CsI comparison, switch to `../new_geo_re_2` and read
   `PROJECT_MEMORY.md` plus `project_state.json` (note: `project_state.json`
   still holds pre-repair values; see Pending Fix #5).
5. If migrating to a new directory/mass model, follow `Project_List.md`.
6. Before editing, check `git status --short`; the repo may already contain
   user changes.
