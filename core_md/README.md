# NEW_GEO_RE

`new_geo_re` is the current DEMO2 detector-background workflow for the 511 keV balloon concept.  The active mainline is no longer the old CeBr3 result: the current detector authority is the DEMO2 CsI active-shield geometry with ADR/passive-mass proxies.

> 2026-06-12 review hold: the 2026-05-31 DEMO2/mainline delayed-activation
> source is now reproduced as over-normalized by `x8.0116` for I-128
> (`533.28 Bq` source vs `66.56/s` Geant4 buildup production). The DEMO2
> numbers in the legacy sections below are kept for provenance only and must
> not be quoted as current sensitivity authority until a div-corrected
> mainline source and downstream Step05+ chain are rerun. The current closed
> rate-level branch authority is v3p5 full-stat exact-position
> `fullstat_v2_exactpos`; `fullstat_v2` remains the conservative
> radial-profile baseline cross-check. R2 on 2026-06-12 also
> repaired the v3p5 fullstat_v2 Step05 prompt normalization: prompt rates now
> use per-tag `1/sum(TT_tag)`, with audit files in the Step05 fullstat output.

## Current Authority

The current in-repo rate-level authority is the v3p5 center-finger DR branch.
Older DEMO2/mainline paths below are legacy provenance under review hold unless
they are explicitly listed in this v3p5 authority block.

- Bounds authority: `geo_refer/DEMO2_DR_v3p5_minpatch_centerfinger_bounds.json`
- MEGAlib proxy setup: `outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- Step00 closure: `stepwise_maintenance/step00_geometry/outputs/v3p5_centerfinger/step00_v3p5_centerfinger_closure.json`
- Step02 1/10 closure: `stepwise_maintenance/step02_raw_background_simulation/outputs_v3p5_centerfinger_1of10/step02_v3p5_centerfinger_1of10_summary.md`
- Step09 full focused EventList transport: `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/step09_optics_bridge_summary.json`
- Step05 L1 raw + active-veto response: `stepwise_maintenance/step05_veto_time_axis/outputs_v3p5_centerfinger_l1/step05_v3p5_centerfinger_l1_response_summary.md`
- Step06 1/10 mission-axis fold: `stepwise_maintenance/step06_mission_time_variation/outputs_v3p5_centerfinger_1of10/README.md`
- Step07 1/10 source-case ledger: `stepwise_maintenance/step07_source_cases/outputs_v3p5_centerfinger_1of10/README.md`
- Step08 1/10 time-dependent significance: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_1of10/step08_v3p5_centerfinger_time_dependent.md`
- Step08 L1 direct significance sidecar: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_1of10/step08_v3p5_centerfinger_l1_significance.md`
- Step08 1 Ms performance-curve comparison sidecar: `stepwise_maintenance/step08_significance/outputs/performance_curve_comparison_1Ms/performance_curve_comparison_1Ms.md`
- 511 narrow-line comparison sidecar: `outputs/reports/compare_511_narrow_1Ms_20260612/compare_511_narrow_1Ms.md`
- Unified 1/10 transport closure report: `outputs/reports/v3p5_centerfinger_1of10_closure/v3p5_centerfinger_1of10_closure_report.md`
- Full-stat v2 performance/W2 closure report: `outputs/reports/v3p5_fullstat_performance_w2_closure_20260612/v3p5_fullstat_performance_w2_closure_report.md`
- Full-stat exact-position performance/W2 closure report: `outputs/reports/v3p5_fullstat_performance_w2_closure_fullstat_v2_exactpos_20260613/v3p5_fullstat_performance_w2_closure_report.md`
- Full-stat exact-position M/seed convergence report: `outputs/reports/v3p5_exactpos_convergence_20260614/v3p5_exactpos_convergence_report.md`
- Full-stat v2 Step05 prompt normalization audit: `stepwise_maintenance/step05_veto_time_axis/outputs_v3p5_centerfinger_fullstat_v2_l1/prompt_normalization_audit.json`
- Full-stat v2 detector-coupled focused response: `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/detector_coupled_focus_response.json`
- Full-stat v2 focused-spot W2 spatial sidecar: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2_spatial/v3p5_spatial_line_proxy.md`
- Full-stat v2 boundary-closure sidecars: `outputs/reports/v3p5_boundary_closure_20260613/v3p5_boundary_closure_report.md`
- R2 CsI I-128 chain anchor: `stepwise_maintenance/step03_delay_source/outputs/i128_anchor_r2_20260612.md`
- Full-stat v2 decay-source audits:
  `runs/step02_decay_source_v3p5_centerfinger_fullstat_v2/normalization_audit_day15.json`
  and
  `runs/step02_delay_fix_v3p5_centerfinger_fullstat_v2/normalization_audit_groundstate_fix.json`

Conservative radial-profile full-stat v2 W2 baseline after the R2
prompt-normalization repair:
Step05 background/signal `0.0729576/0.00118117 cps`, Step08
`Z20d=5.70221`, 20-day 3-sigma flux `5.26111e-5 ph cm^-2 s^-1`, and
1 Ms 3-sigma flux `6.82301e-5 ph cm^-2 s^-1`.

Current v3p5 full-stat focused-spot W2 sidecar: side-entry detector centroids
are measured in the local side-window frame, not around the global origin.
`spot_r90=1.05164 cm` keeps `0.9000` of the focused W2 signal, reduces W2
background to `0.0232510 cps`, and gives time-dependent
`Z20d=8.17566` with 20-day 3-sigma flux
`3.66943e-5 ph cm^-2 s^-1`. This is a detector-coupled spatial sidecar, not a
profile-likelihood gain and not a replacement for the hard-window W2 authority.

Current v3p5 boundary-closure sidecars: applying the same Step06 Beer-Lambert
depth model to a 45 deg side-entry slant column gives `T_ref=0.652034`, W2
`Z20d=5.02544` and 20-day 3-sigma flux
`5.96962e-5 ph cm^-2 s^-1`; the corresponding `spot_r90` sidecar gives
`Z20d=7.20533` and `4.16358e-5 ph cm^-2 s^-1`. A fixed-template
multi-annulus W2 spatial-likelihood sidecar gives `Z20d=8.45804` and
`3.54692e-5 ph cm^-2 s^-1`. These sidecars close the scalar-`T_atm` and
single-spatial-cut analysis boundaries for the `fullstat_v2` baseline.

Current v3p5 exact-position delayed-source rate authority:
`fullstat_v2_exactpos` promotes the smoke-validated exact-RPIP `PointSource`
path to the fixed inventory, runs `1,000,000` delayed triggers, and closes
through Step05-08 plus the W2/performance/boundary packaging at
`outputs/reports/v3p5_fullstat_performance_w2_closure_fullstat_v2_exactpos_20260613/`.
The exact-position Step02 delayed transport has `SE=1,000,000`,
`ID=1,000,000`, `TE=11530.473845 s`, and 5000 sampled `PointSource` support
blocks with no `RadialProfileBeam` blocks. Its W2 headline is
Step05 background/signal `0.0624651/0.00118117 cps`, Step08 `Z20d=6.15522`,
20-day 3-sigma flux `4.87391e-5 ph cm^-2 s^-1`, and 1 Ms 3-sigma flux
`6.32564e-5 ph cm^-2 s^-1`. The M/seed convergence report
`outputs/reports/v3p5_exactpos_convergence_20260614/` is
`PASS_EXACTPOS_TRANSPORT_CONVERGENCE` and recommends
`PROMOTE_EXACTPOS_TO_CURRENT_RATE_AUTHORITY`: four transport-backed cases cover
`M=5000` at seeds `260613/260614`, `M=20000` at seed `260613`, and `M=50000`
at seed `260613`; W2 delayed cps relative range is `0.187413`, W2 background
cps relative range is `0.0111915`, and `Z20d` relative range is `0.00550844`.
`fullstat_v2` remains the conservative radial-profile baseline cross-check.
The remaining engineering work is optional source-parsing optimization or a
full weighted-table one-block-per-RPIP stress test, not an authority blocker.

Low-stat `1of10` remains a directory/status compatibility label only. Its
actual v3p5 prompt exposure split is gamma about `1/10`, non-gamma about
`1/80`, and generated particle count about `1/21.2`; use the full-stat v2
branch for rate-level comparisons.

The path names still contain old `v4c`/`cmfix` tokens for compatibility with existing source cards and scripts.  The file contents are DEMO2 (`ADR_v6_demo2_adrpassive_csi`): CsI active shield, staged Al thermal windows, Cu/W passive shield, Cryoperm/ADR proxies, and the current DEMO2 bounds.

## Legacy DEMO2 Results (Pre-Fix Review Hold)

The following DEMO2/mainline values are legacy pre-fix records. They are not
current sensitivity authority after the reproduced `x8.0116` delayed-source
normalization issue.

Step02 production is event-count aligned to the old balloon simulation budget:

- prompt `instant`: `60/60` jobs passed, `25,210,216` generated particles;
- activation `buildup`: `60/60` jobs passed, `25,210,216` generated particles;
- fixed delayed source: `5968` source blocks, activity `624.27109184 Bq`;
- delayed transport: `1,000,000` generated/stored events, `TE = 1584.61 s`;
- legacy homogeneous-beam science 511 run: `100,000` triggers/stored events, retained only for baseline history.
- current Route-A science source: Step09 focused EventList source, `12,592` optics rows, full focused detector transport parsed in `stepwise_maintenance/step09_optics_bridge/outputs/detector_coupled_focus_response.json`.

Day-15 legacy broad-window final selection (`480-550 keV`, active shield + Compton/FoV):

- timeline rates: raw `3.85899 cps`, active-shield pass `3.34720 cps`, final `2.35011 cps`;
- direct-expectation rates: raw `3.86466 cps`, active-shield pass `3.37085 cps`, final `2.36821 cps`;
- final background decomposition: prompt `0.05357 cps`, delayed activation `2.31224 cps`;
- legacy homogeneous-beam science final rate at `1e-4 ph cm^-2 s^-1`: `0.002399 cps`.

Current focused Route-A optics/science authority:

- optics design: `balloon511_f9m_ge111_511line`;
- A_eff(511): `15.29928 cm2`, within the 15% tolerance around the `16 cm2` design target;
- W1 design passband: `500.993937-521.006063 keV`;
- W2 line window: `510.58-511.42 keV`;
- focused W1 final response: `9.00989 cps/(ph cm^-2 s^-1)`;
- focused W2 final response: `8.98288 cps/(ph cm^-2 s^-1)`.

Step08 focused W1 mission-axis significance:

- `1e-4 ph cm^-2 s^-1` reaches `Z20d = 0.7686` in the W1 time-axis fold;
- it does not reach 3 sigma inside the 20-day mission;
- constant-profile extrapolated 3-sigma time is `304.7 day`.

Line-window sidecar (`W2 = 511 +/- 420 eV`, `sigma_TES = 0.14 keV`) from `stepwise_maintenance/step08_significance/outputs/line_window_sensitivity.md`:

- final background `0.18435 cps`;
- `1e-4 ph cm^-2 s^-1` reaches `Z20d = 2.750`;
- 3-sigma time is `23.80 day`;
- 20-day 3-sigma flux is `1.09e-4 ph cm^-2 s^-1`.

Focused-spot detector-coupled spatial sidecar from `stepwise_maintenance/step08_significance/outputs/spatial_line_proxy.md`:

- signal centroids come from the full non-smoke Step09 focused EventList detector transport;
- detector-coupled signal sample: `10,031` W2 events;
- detector-coupled signal radii: `r90 = 0.5237 cm`, `r99 = 1.2168 cm`, `rmax = 1.6966 cm`;
- headline cut is `spot_r90`, not `spot_rmax`: signal fraction `0.9000`, background `0.05510 cps`, `Z20d = 4.527`;
- 20-day 3-sigma flux with spot_r90 is `6.63e-5 ph cm^-2 s^-1`.

The focused line-window and spatial results are detector-coupled EventList direct-expectation results.  A full spatial-spectral likelihood is still a separate analysis upgrade.

Ground-state half-life audit:

- NUBASE2020 ASCII input is archived at `inputs/nubase/nubase_2020.txt`, SHA256 `1585a5eea86c5e17e90307c7e6e786d060049c4039e392a261ff6db977df9859`;
- `outputs/reports/half_life_unit_audit/half_life_unit_audit_summary.json` verifies `74` prefix-year rows (`Ey/Gy/My/Ty/ky`) against the archived NUBASE line references with zero relative mismatch;
- unit self-tests cover `ky/My/Gy/Ty/Py/Ey`;
- W-180 is reduced from `0.28452 Bq` raw-source activity to `5.09e-21 Bq` and no `74180/74183` source blocks remain in the fixed delayed source.

Legacy CsI activation baseline:

- `outputs/reports/csi_activation_baseline/csi_activation_baseline_summary.json` is a legacy DEMO2/mainline pre-fix activity budget and is not current authority;
- CsI active-shield volumes contributed `561.13 Bq`, or `89.89%` of that legacy fixed source activity;
- I-128 contributed `533.28 Bq`, or `85.42%` of that legacy total fixed source activity, all in CsI volumes;
- current v3p5 R2 I-128 authority is `stepwise_maintenance/step03_delay_source/outputs/i128_anchor_r2_20260612.md`: `66.0018 Bq` over `62.8337 kg`, or `1.05042 Bq/kg`.

BGO control geometry scaffold:

- `outputs/geometry/XZTES_ADR_v4c_mkflange_bgo_control/` is a same-shape DEMO2 active-shield material substitution scaffold;
- the scaffold has `20` BGO active-shield detector segments, `20` native veto triggers, and a Cosima overlap check status `PASS`;
- using local MEGAlib `BGO.Density 7.1`, the same active-shield volume gives `102.57 kg` BGO active mass versus `65.15 kg` CsI active mass;
- transport/source/significance status remains `NOT_RUN`; this is an input geometry authority, not a CsI-vs-BGO physics result.

v3p5 center-finger DR branch checkpoint:

- geometry points the local side window `45 deg` upward with `InstrumentFrame.Rotation 0 45 0`;
- adaptive far-field/setup sphere is `60 cm`;
- W side collimator is a `2 cm` thick square-bore sleeve, not a 376-hole pixel collimator;
- Step00 status is `STEP00_PASS`;
- Step02 1/10 status is `PASS_1OF10_TRANSPORT_CLOSURE`;
- instant/buildup each generated `1,190,129` particles over `19/19` passing jobs;
- fixed delayed source has `786` blocks and `86.382997 Bq`;
- delayed transport stores `100,000` events with `TE=1140.447373 s`.
- Step09 focused optics bridge status is `PASS_EVENTLIST_BRIDGE_FULL_TRANSPORTED`;
  `37,194/37,194` EventList rows are stored in the full detector transport SIM.
- Step05 L1 side-entry Compton/FoV + time-axis response is
  `PASS_V3P5_STEP05_SIDE_ENTRY_COMPTON_TIME_AXIS_L1`; W2 direct side-Compton/FoV
  rates are prompt `0 cps`, delayed `0.0157833 cps`, and focused signal
  `0.795747` per unit EventList injection rate. The common-time-axis W2
  side-Compton/FoV rate is `0.800563 cps` under unit signal-rate normalization.
- Step05 physical reference scaling uses f10m A1 `A_eff(511)=20.08476 cm2`,
  inherited `T_atm=0.739042`, and injection-plane rate `0.00148435 s^-1` at
  `1e-4 ph cm^-2 s^-1`.
  The inherited `T_atm` is a scalar mainline reference for normalization, not
  an absolute 45 deg side-entry line-of-sight transmission. In a
  plane-parallel atmosphere the 45 deg slant column is already larger by
  `sec(45 deg)=1.414`. The dedicated LOS sidecar is now recorded in
  `outputs/reports/v3p5_boundary_closure_20260613/`.
- Step06 v3p5 mission-axis fold is `PASS_V3P5_STEP06_TIME_AXIS_1OF10`; W2
  mission-mean background/signal are `0.0155714/0.00117281 cps`.
- Step07 v3p5 source-case ledger is `PASS_V3P5_STEP07_SOURCE_CASES_1OF10`;
  W2 response is `11.8117 cps/(ph cm^-2 s^-1)`.
- Step08 v3p5 time-dependent significance is
  `PASS_V3P5_STEP08_TIME_DEPENDENT_1OF10`; W2 reference
  `1e-4 ph cm^-2 s^-1` reaches `Z20d=12.3501`, `T3=0.9428 day`, and
  20-day 3-sigma flux `2.429e-5 ph cm^-2 s^-1`.
  The direct sidecar remains as a constant-rate cross-check:
  `Z20d=12.359`.
  Low-stat warning: W2 background uses only `18` final selected background
  events.
- Step08 1 Ms performance-curve sidecar is
  `PASS_PERFORMANCE_CURVE_COMPARISON_1MS`; `1 Ms = 1,000,000 s`. Best
  checkpoint curve is v3p5 W2 with
  `F_3sigma(1 Ms)=3.13482e-5 ph cm^-2 s^-1`, compared with documented DEMO2
  current spot_r90 `8.74842e-5 ph cm^-2 s^-1`.
- Unified transport closure status is `PASS_V3P5_1OF10_TRANSPORT_CLOSURE`;
  this is now a low-stat closure through Step00/02/05/06/07/08/09, not
  paper-facing statistics.

## Layout

- `code/geometry/`: geometry generator.
- `code/tools/`: report, validation, and detector helper scripts.
- `config/`: Cosima source templates and science-rate metadata.
- `inputs/nubase/`: archived NUBASE2020 ASCII input used by the half-life audit.
- `outputs/geometry/`: generated geometry outputs; current v3p5 authority is the
  center-finger proxy listed in the Current Authority block above.
- `outputs/geometry/XZTES_ADR_v4c_mkflange_bgo_control/`: BGO active-shield control geometry scaffold.
- `outputs/reports/csi_activation_baseline/`: legacy DEMO2 CsI active-shield activation baseline outputs under review hold.
- `outputs/reports/day15_complete_report/`: legacy DEMO2 day-15 catalog/report outputs under review hold.
- `outputs/reports/half_life_unit_audit/`: legacy DEMO2 prefix-year half-life unit audit outputs.
- `outputs/reports/review_20260531_closure/`: legacy priority-ordered closure matrix for `review_20260531.html`.
- `outputs/reports/experiment_report_20260601/`: Route-A full-chain focused EventList report.
- `records/00_geometry/`: geometry record and schematic.
- `runs/step02_*_equiv2602_aligned/`: legacy pre-fix DEMO2 prompt, buildup, delay-fix, and delayed-transport products.
- `runs/science_511_onaxis_source/`: legacy 100k on-axis 511 keV science run.
- `stepwise_maintenance/step01_geo/` through `stepwise_maintenance/step09_optics_bridge/`: stepwise audit products.
- `tests/`: lightweight validation helpers.

## Rebuild/Validate

Core validation:

```bash
python3 code/tools/audit_groundstate_half_life_units.py
python3 code/tools/audit_csi_activation_baseline.py
python3 code/tools/build_bgo_control_geometry.py
python3 code/tools/build_review_20260531_closure.py
python3 code/tools/build_experiment_report_20260601.py
python3 code/tools/validate_new_geo_re.py
```

Regenerate the current focused Route-A chain:

```bash
python3 stepwise_maintenance/step09_optics_bridge/code/build_detector_coupled_focus_response.py
python3 stepwise_maintenance/step07_source_cases/code/build_step07_source_cases.py
python3 stepwise_maintenance/step08_significance/code/build_step08_significance.py
python3 stepwise_maintenance/step08_significance/code/build_line_window_sensitivity.py
python3 stepwise_maintenance/step08_significance/code/build_spatial_line_proxy.py
python3 code/tools/build_review_20260531_closure.py
python3 code/tools/build_experiment_report_20260601.py
```

Regenerate the complete day-15 report from the existing event catalog and summary:

```bash
python3 code/tools/make_complete_day15_report_ADR.py --refresh-from-summary
```

## Paper-Facing Caveats

- W1 is the design natural passband; W2 is the narrow 511-line counting window.
- Route A is now detector-coupled through the Step09 focused EventList; Route B diffuse emission remains aperture/rate folded until a diffuse-sky optics focal-map projection is implemented.
- Route B has a physical diffuse-source supplement in `ROUTE_B_DIFFUSE_SUPPLEMENT_20260602.md`: literature bulge/disk flux -> FoV solid angle -> atmospheric transmission -> W2 Route-A comparison.
- Optics hardware activation and scattering are not in the main background transport.
- Native MEGAlib CsI Trigger/Veto blocks are present in the `.det` file and checked by `native_csi_veto_trigger` in `VALIDATION.md`; the quantitative active-shield veto authority remains the Step05 post-processing layer because it models the 1 us summed-coincidence veto.
- The BGO control geometry scaffold is now available and overlap-clean, but a paper-facing CsI-vs-BGO claim still requires the BGO source/transport/selection/significance chain through the same Step02-Step08 gates.
