# NEW_GEO_RE Current Progress Breakdown

This file records the current DEMO2 mainline state.  Historical pre-DEMO2 numbers are kept in older logs and `MEMORY.md` only as legacy context; do not quote them as current results.

## v3p5 Center-Finger Full-Stat v2 Closure

Status: `PASS_V3P5_FULLSTAT_PERFORMANCE_W2_CLOSURE`.

This is the current v3p5 center-finger rate-level authority. It supersedes the
1/10 checkpoint for v3p5 comparisons, while still remaining an L1
rate-level closure rather than a profile-likelihood or final paper-facing
spatial analysis.

The v3p5 full-stat focused-spot W2 spatial sidecar is now available, but it is
still a detector-coupled counting sidecar rather than a spatial/profile
likelihood result.

The old `1of10` name is a compatibility label: gamma prompt exposure is about
`1/10`, non-gamma prompt exposure is about `1/80`, and total generated particle
count is about `1/21.2`. Treat that branch as low-stat closure only.

Science normalization still inherits the scalar mainline `T_atm=0.739042`
reference; the 45 deg side-entry absolute atmospheric line-of-sight
transmission has not been recomputed.

Authority:

- final report directory:
  `outputs/reports/v3p5_fullstat_performance_w2_closure_20260612/`
- HTML report:
  `outputs/reports/v3p5_fullstat_performance_w2_closure_20260612/report.html`
- Step02 full-stat output:
  `stepwise_maintenance/step02_raw_background_simulation/outputs_v3p5_centerfinger_fullstat_v2/`
- Step05 full-stat L1 response:
  `stepwise_maintenance/step05_veto_time_axis/outputs_v3p5_centerfinger_fullstat_v2_l1/`
- Step06/07/08 full-stat mission products:
  `stepwise_maintenance/step06_mission_time_variation/outputs_v3p5_centerfinger_fullstat_v2/`,
  `stepwise_maintenance/step07_source_cases/outputs_v3p5_centerfinger_fullstat_v2/`,
  `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2/`
- R2 repaired sidecars:
  `outputs/reports/compare_511_narrow_1Ms_20260612/compare_511_narrow_1Ms.md`,
  `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2_spatial/v3p5_spatial_line_proxy.md`,
  `runs/step02_decay_source_v3p5_centerfinger_fullstat_v2/normalization_audit_day15.json`,
  and
  `runs/step02_delay_fix_v3p5_centerfinger_fullstat_v2/normalization_audit_groundstate_fix.json`

Headline full-stat v2 result:

- Step02 prompt/buildup each generated `25,210,216` particles; delayed
  transport has `SE=1,000,000`, `ID=1,000,000`, `TE=11531.59846 s`.
- W2 Step05 background/signal: `0.0729576/0.00118117 cps` at
  `1e-4 ph cm^-2 s^-1`.
- Step08 W2 time-dependent `Z20d=5.70221`, `T3=5.46687 day`, 20-day
  3-sigma flux `5.26111e-5 ph cm^-2 s^-1`.
- 1 Ms v3p5 W2 3-sigma flux: `6.82301e-5 ph cm^-2 s^-1`.
- v3p5 full-stat `spot_r90` sidecar: local side-window radius
  `1.05164 cm`, background `0.0232510 cps`, time-dependent `Z20d=8.17566`,
  `T3=2.23643 day`, and 20-day 3-sigma flux
  `3.66943e-5 ph cm^-2 s^-1`.
- W2 background source driver: prompt `eplus` is still the largest component
  (`80` events, `0.0543377 cps`, `74.5%` of final W2 background); delayed
  activation is `0.0138749 cps` total and is led by `Cu64` within the delayed
  slice.

## v3p5 Center-Finger Low-Stat Checkpoint

Status: `PASS_V3P5_1OF10_TRANSPORT_CLOSURE`.

This is a separate DR/v3p5 branch checkpoint and does not replace the DEMO2
mainline authority below. It closes the current low-statistics branch through
Step00/02/05/06/07/08/09 with a 2 cm W side-entry sleeve, 60 cm adaptive
far-field/setup sphere, and `InstrumentFrame.Rotation 0 45 0` side-window
pointing.

Authority:

- unified report:
  `outputs/reports/v3p5_centerfinger_1of10_closure/v3p5_centerfinger_1of10_closure_report.md`
- Step06 mission-axis output:
  `stepwise_maintenance/step06_mission_time_variation/outputs_v3p5_centerfinger_1of10/`
- Step07 source-case output:
  `stepwise_maintenance/step07_source_cases/outputs_v3p5_centerfinger_1of10/`
- Step08 time-dependent output:
  `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_1of10/step08_v3p5_centerfinger_time_dependent.md`

Headline low-stat v3p5 result:

- W2 mission-axis background/signal: `0.0155714/0.00117281 cps` at
  `1e-4 ph cm^-2 s^-1`.
- Step08 W2 time-dependent `Z20d=12.3501`, `T3=0.9428 day`, 20-day 3-sigma
  flux `2.429e-5 ph cm^-2 s^-1`.
- Low-stat warning: W2 background is based on `18` final selected background
  events, so this is closure evidence only, not a paper-facing sensitivity.

## Current Required Figure Pack

Status: complete.

The three currently requested stepwise figures are now built as compact index
products from the current Step06/08/09 authority files. They follow the
durable-record pattern used in the historical
`/home/ubuntu/codex_tes_511_sim/COSMOSRAY_BALLOON_SIM/Records/` tree, but the
old Records files are style/provenance references only, not the numeric
authority for this DEMO2/B-FULL chain.

Rebuild command:

```bash
python3 stepwise_maintenance/figure_pack/build_stepwise_figure_pack.py
```

Outputs:

| requirement | current figure | authority inputs |
| --- | --- | --- |
| Trajectory time-varying curve | `stepwise_maintenance/outputs/figures/stepwise_trajectory_time_variation.png` | Step06 `trajectory_profile.csv`, `background_time_variation.csv`, and summary JSON |
| Background component breakout | `stepwise_maintenance/outputs/figures/stepwise_background_component_breakout.png` | Step06 `background_time_variation.csv` |
| 3-sigma significance result plot | `stepwise_maintenance/outputs/figures/stepwise_3sigma_headline_results.png` | Step08 W1 mission-axis `t3_t5_summary.csv`, W2 line sidecar, and `spot_r90` spatial sidecar |
| Spectrum with Laue and W2 windows | `stepwise_maintenance/outputs/figures/stepwise_spectrum_laue_w2_windows.png` | Step09 detector-coupled background spectrum and focus-response JSON |

Figure-pack manifest: `stepwise_maintenance/outputs/figures/stepwise_figure_pack_summary.json`.

Historical Records references consulted for organization and plotting style:

- `COSMOSRAY_BALLOON_SIM/Records/03_mission_time_variation/mission_time_variation.md`
  and its balloon altitude/depth plus lat/lon/cutoff figures.
- `COSMOSRAY_BALLOON_SIM/Records/05_laue_current_mainline/source_significance_time_dependent_20260522/README.md`
  and its cumulative-significance/flux-scan figure set.
- `COSMOSRAY_BALLOON_SIM/Records/08_nai_shield_substitution_20260522/README.md`
  as an older example of keeping spectrum and point-source 3-sigma scan outputs
  together in a compact record.

Current figure-pack headline values:

- Trajectory/time axis: `81` bins, day `0-20`, altitude `36.25-41.25 km`,
  `T_atm(511)=0.646123-0.811095`, final background
  `1.93648-2.77142 cps`.
- 3-sigma panel: W1 mission-axis `Z20d=0.766916`, extrapolated
  `T3=306.039 day`, 20-day 3-sigma flux
  `3.91177e-4 ph cm^-2 s^-1`; W2 line window time fold
  `Z20d=2.73543`, `T3=24.0560 day`, 20-day 3-sigma flux
  `1.09672e-4 ph cm^-2 s^-1`; W2 `spot_r90` time fold
  `Z20d=4.50779`, `T3=8.17935 day`, 20-day 3-sigma flux
  `6.65515e-5 ph cm^-2 s^-1`.
- Spectrum panel: Laue/W1 passband `500.993937-521.006063 keV`, W2
  `510.58-511.42 keV`; final non-X-ray backgrounds are `0.783047 cps`
  and `0.184347 cps`, respectively.

Important interpretation: W1 is the Step08 mission-axis time-dependent counting
fold. W2 and `spot_r90` are detector-coupled direct-expectation sidecars from
the Step09 focused EventList response, now folded over the Step06 time axis for
the headline 3-sigma panel. This is the current Project_Memory authority; do
not replace it with old homogeneous-beam or broad-window-only figures.

## Step01 Geometry

Status: complete.

- Authority geometry: `outputs/geometry/XZTES_ADR_v4c_mkflange_cm/TibetTES_ADR_v4c_mkflange_cm.geo.setup`.
- Contents are DEMO2 despite the compatibility path name: CsI active shield, staged Al windows, open Nb can, Cryoperm proxy, ADR/passive service proxies, Cu/W passive shield, and Be aperture.
- The `.det` file contains a formal native MEGAlib TES trigger plus 20 CsI veto triggers at `50 keV`; `native_csi_veto_trigger` validates that this detector-model statement remains true.
- BGO control scaffold: `outputs/geometry/XZTES_ADR_v4c_mkflange_bgo_control/bgo_control_geometry.md`. It keeps the same DEMO2 geometry/segmentation, replaces the active shield with BGO material/names, keeps 20 native veto triggers, and has Cosima overlap status `PASS`.
- BGO control active mass is `102.57 kg` versus `65.15 kg` for the current CsI active shield. BGO source/transport/selection/significance status is `NOT_RUN`.
- Validator check: `geometry_authority` in `VALIDATION.md`.

## Step02 Raw Background Simulation

Status: complete for event-count-aligned DEMO2 production.

- Prompt `instant`: `60/60` jobs passed, `25,210,216` generated particles.
- Activation `buildup`: `60/60` jobs passed, `25,210,216` generated particles.
- Raw delayed source: `6008` source blocks, `624.55914 Bq`.
- Ground-state fixed source: `5968` source blocks, `624.27109 Bq`.
- Delayed transport: `TS 1,000,000`, `SE 1,000,000`, `TE 1584.60761 s`.
- Output summary: `stepwise_maintenance/step02_raw_background_simulation/outputs/step02_event_aligned_summary.md`.

Step02 remains a raw transport checkpoint: no Poisson time-axis merge, active-shield veto, Compton/FoV veto, or sensitivity analysis is part of Step02.

## Step03 Delayed Activation Source

Status: complete as the delay-fix source audit.

- Fixed source: `runs/step02_delay_fix_equiv2602_aligned/activation_decay_day15_groundstate_fixed.source`.
- Fixed activity: `624.27109184 Bq`.
- Removed/rescaled blocks: `40`.
- `W-183` and `W-180` source-block residuals are absent in the fixed source.
- NUBASE2020 ASCII source is archived at `inputs/nubase/nubase_2020.txt`.
- Half-life audit output: `outputs/reports/half_life_unit_audit/half_life_unit_audit.md`.
- The audit checks `74` prefix-year rows (`Ey/Gy/My/Ty/ky`) against archived NUBASE line references with zero relative mismatch and self-tests `ky/My/Gy/Ty/Py/Ey`.
- CsI activation baseline output: `outputs/reports/csi_activation_baseline/csi_activation_baseline.md`.
- Current fixed-source activity is CsI-dominated: CsI active-shield volumes contribute `561.13 Bq` (`89.89%` of total), and I-128 contributes `533.28 Bq` (`85.42%` of total).
- The CsI activation baseline is not a BGO control simulation; the BGO replacement/control chain has status `NOT_RUN`.

The W-180 half-life/unit issue is corrected in the fixed source and now covered by the root validator.

## Step04 Opticsim Laue

Status: complete as the Route-A B-FULL focused-photon handoff.

- Current optics handoff uses the B-FULL Ge(111) 511-keV line lens with an external per-ring XOP/CRYSTAL rocking-curve map.
- Design name: `balloon511_f9m_ge111_511line`.
- Focal length: `9000 mm`; ring radius: `66.8501 mm`; tile count: `27`; tile size: `15 mm`; mosaicity: `30 arcsec`.
- A_eff(511): `15.29928 cm2`, compared with the `16 cm2` design target. The relative residual is `4.38%`, below the `15%` adjustment threshold, so the design was not retuned.
- Natural W1 passband: `500.993937-521.006063 keV`.
- The B-FULL XOP-map run has `50000` primaries, `12605` tracked diffracted focal crossings, and `12592` within-Be focused rows.
- Tracked optics spot: `r95 = 0.2191 cm`, `r99 = 0.2914 cm`, within Be radius `1.898 cm`. A small scattered tail reaches outside Be and is not bridged as focused signal.
- Channel optics is not used. Optics hardware mass is still not included in prompt/delayed background transport.

## Step05 Veto Time Axis

Status: complete for the DEMO2 day-15 common timeline.

- Coincidence window: `1.0e-6 s`.
- Active veto authority: `CsI_Active_Shield`.
- Veto threshold: `50 keV`.
- Reject policy: `keep`.
- Observation time: `1584.61 s`.
- Broad `480-550 keV` timeline rates: raw `3.85899 cps`, active-shield pass `3.34720 cps`, final `2.35011 cps`.
- Broad `480-550 keV` direct-expectation rates: raw `3.86466 cps`, active-shield pass `3.37085 cps`, final `2.36821 cps`.
- Direct final decomposition: prompt `0.05357 cps`, delayed `2.31224 cps`, science at `1e-4` `0.002399 cps`.

Output authority: `outputs/reports/day15_complete_report/complete_day15_summary.json`.

## Step06 Mission Time Variation

Status: complete as `L0_EXPACS_PROMPT_DRIVER_RATE_FOLD_COMPLETE`.

- Mission bins: `81`, day `0` to `20`, `0.25 day` spacing.
- Max trajectory offsets: latitude `0.25 deg`, longitude `0.25 deg`, altitude `2.5 km`.
- Prompt and delayed-production environmental drivers now call the official
  EXPACS/PARMA C++ driver at every one of the `81` trajectory bins.
- The prompt detector-rate scale is particle-weighted by the current
  `480-550 keV` final-prompt composition: `e+`, gamma, and neutron terms
  dominate the retained prompt events.
- The delayed-production scale is particle-weighted by the Step02 buildup
  source particle-rate mix, then propagated through the existing activity ODE.
- No time bin reruns Cosima detector transport; Step06 remains a rate-level
  fold over the existing Step05 response rates.
- EXPACS/PARMA scale ranges: prompt detector `0.868532-1.16828`; delayed
  production `0.852141-1.19352`.
- Atmospheric 511 keV transmission closes to the Step05 ledger at day 15 with absolute error about `3e-13`.
- Day-15 final-rate closure against Step05 is below `1e-13`.

Output authority: `stepwise_maintenance/step06_mission_time_variation/outputs/step06_mission_time_variation_summary.json`.

Figure-pack output:

- `stepwise_maintenance/outputs/figures/stepwise_trajectory_time_variation.png`
  combines the Step06 trajectory, residual atmospheric depth, small lat/lon
  offsets, EXPACS/PARMA prompt and delayed driver scales, final
  prompt/delayed/background rates, and 511 keV atmospheric transmission. The
  comparable historical references are
  `COSMOSRAY_BALLOON_SIM/Records/03_mission_time_variation/05_balloon_altitude_depth_vs_time.png`
  and `06_balloon_lat_lon_cutoff_track.png`, but those old files are not the
  current numeric authority.
- `stepwise_maintenance/outputs/figures/stepwise_background_component_breakout.png`
  splits the Step06 prompt and delayed backgrounds into raw, active-shield pass,
  and final-stage curves, then shows the final prompt/delayed composition.

## Step07 Astrophysical Source Cases

Status: complete as `L1_SOURCE_CASE_FOCUSED_EVENTLIST_RATE_FOLDING`.

- `A_opt = A_eff(511) = 15.29928 cm2`.
- `T_atm_ref = 0.739042`.
- Plane rate per flux: `11.3068 cps/(ph cm^-2 s^-1)`.
- Focused W1 final response: `9.00989 cps/(ph cm^-2 s^-1)`.
- Focused W2 final response: `8.98288 cps/(ph cm^-2 s^-1)`.
- W1 final non-X-ray background: `0.783047 cps`; W2 final non-X-ray background: `0.184347 cps`.
- A compact/on-axis Route-A mono source uses the Step09 focused EventList source. It is no longer the old homogeneous Be-window source.
- Route-B diffuse emission remains aperture/rate folded and is intentionally not emitted as a focal EventList source until a diffuse-sky optics focal-map projection exists.
- Route-B supplement complete: `ROUTE_B_DIFFUSE_SUPPLEMENT_20260602.md` folds literature bulge/disk flux through FoV solid angle, Step06 `T_atm`, and the current W2 detector response; default 8-deg bulge plus disk gives W2 `Z20d = 0.0196`.
- V404 `z=0.10` narrow redshift proxy is clamped to exactly zero response below the `1e-100` tiny-response threshold; this removes numerically meaningless subnormal rates from Step07 outputs.

Output authority: `stepwise_maintenance/step07_source_cases/outputs/source_case_summary.json`.

## Step08 Time-Dependent Significance

Status: complete as `L1_COUNTING_TIME_DEP_WITH_ANALYTIC_ACCIDENTAL`.

W1 design-passband mission-axis selection:

- A compact-GC anchor `8e-5 ph cm^-2 s^-1`: `Z20d = 0.6135`.
- A reference `1e-4 ph cm^-2 s^-1`: `Z20d = 0.7669`.
- The `1e-4` reference does not reach 3 sigma within the 20-day mission.
- Its constant-profile extrapolated 3-sigma time is `306.0 day`.

Line-window sidecar:

- Output: `stepwise_maintenance/step08_significance/outputs/line_window_sensitivity.md`.
- W2 (`511 +/- 420 eV`) with `sigma_TES = 0.14 keV`: day-15 background
  `0.18435 cps`; Step06 time-fold result `Z20d = 2.735`,
  `T3 = 24.06 day`, 20-day 3-sigma flux
  `1.10e-4 ph cm^-2 s^-1`.
- This is a detector-coupled focused EventList direct-expectation sidecar folded
  over the Step06 prompt/delayed/science time scales; it still does not rerun
  time-bin detector transport.

Focused-spot detector-coupled spatial sidecar:

- Output: `stepwise_maintenance/step08_significance/outputs/spatial_line_proxy.md`.
- Signal centroids come from the full non-smoke Step09 focused EventList detector transport.
- Detector-coupled W2 signal events: `10031`.
- Signal radii: `r90 = 0.5237 cm`, `r95 = 0.8523 cm`, `r99 = 1.2168 cm`, `rmax = 1.6966 cm`.
- Headline cut is `spot_r90`, not `spot_rmax`: signal fraction `0.9000`,
  day-15 background `0.05510 cps`; Step06 time-fold result `Z20d = 4.508`,
  20-day 3-sigma flux `6.66e-5 ph cm^-2 s^-1`.
- Best robust diagnostic cut is `spot_r68`, with `Z20d = 5.949`; it is diagnostic only.

Figure-pack output:

- `stepwise_maintenance/outputs/figures/stepwise_3sigma_headline_results.png`
  plots the current headline 3-sigma chain: W1 mission-axis counting fold,
  W2 line-window detector-coupled sidecar, and W2 `spot_r90` spatial sidecar.
  The W1 point is the Project_Memory/Step08 mission-axis value recomputed from
  the 81-bin EXPACS/PARMA Step06 curve, `Z20d=0.766916`, not the direct-rate W1
  check in the line sidecar. The W2 line and `spot_r90` values are now also
  folded over the Step06 time axis: `Z20d=2.73543` and `4.50779`.

## Step09 Opticsim EventList Bridge

Status: complete as `L1_OPTICS_EVENTLIST_BRIDGE`.

- EventList rows written: `12592` tracked diffracted focal crossings inside the Be window.
- Energy range: `511-511 keV`.
- Injection plane: `z = 16.051 cm`.
- Max injected radius: `1.4577 cm`, within Be radius `1.898 cm`.
- Smoke transport: `1000` stored events.
- Full non-smoke focused transport was run and parsed by `stepwise_maintenance/step09_optics_bridge/code/build_detector_coupled_focus_response.py`; the detector-coupled response status is `PASS_DETECTOR_COUPLED_FOCUSED_EVENTLIST`.

Step09 bridges focused Laue phase space into detector transport, but optics hardware activation/scattering remains a future mass-model upgrade.

Figure-pack output:

- `stepwise_maintenance/outputs/figures/stepwise_spectrum_laue_w2_windows.png`
  plots the day-15 non-X-ray background spectrum with the Laue W1 natural
  passband (`500.993937-521.006063 keV`) and W2 line window
  (`510.58-511.42 keV`) shaded. The plotted spectrum is the current Step09
  detector-coupled background after the raw, CsI active-shield, Compton/FoV,
  and combined veto stages; final background rates are `0.783047 cps` in W1
  and `0.184347 cps` in W2.

## Step10 Closure Validator

Status: current closure gate.

Run:

```bash
python3 code/tools/validate_new_geo_re.py
```

Review closure matrix: `outputs/reports/review_20260531_closure/review_20260531_closure.md`.

Current validator scope includes geometry, native CsI veto trigger structure, production paths, fixed source, half-life prefix-unit audit, CsI activation baseline, BGO control geometry scaffold, review 2026-05-31 closure matrix, timeline expectation closure, Compton/FoV sign test, Step06, Step07, Step08, the detector-coupled 511 line-window sidecar, detector-coupled spatial sidecar, Step09 focused response, stale-path checks, and optics B-FULL policy.
