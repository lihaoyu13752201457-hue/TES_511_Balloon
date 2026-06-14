# NEW_GEO_RE Workflow

This directory is the DEMO2/v3p5 `new_geo_re` workflow root. As of the
2026-06-12 R1/R2 reviews and the 2026-06-14 exactpos convergence closure, the
current in-repo rate-level authority is the v3p5 full-stat exact-position
`fullstat_v2_exactpos` branch. `fullstat_v2` remains the conservative
radial-profile baseline cross-check. Older DEMO2 `equiv2602_aligned` and
`XZTES_ADR_v4c_mkflange_cm` paths are legacy pre-fix provenance only unless a
paragraph explicitly says it is current v3p5 authority.

Current v3p5 anchors:

- Geometry bounds: `geo_refer/DEMO2_DR_v3p5_minpatch_centerfinger_bounds.json`.
- MEGAlib proxy setup: `outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`.
- Step05 full-stat response: `stepwise_maintenance/step05_veto_time_axis/outputs_v3p5_centerfinger_fullstat_v2_l1/step05_v3p5_centerfinger_l1_response_summary.json`.
- Step08 full-stat time fold: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2/step08_v3p5_centerfinger_time_dependent_summary.json`.
- Full-stat W2 closure: `outputs/reports/v3p5_fullstat_performance_w2_closure_20260612/v3p5_fullstat_performance_w2_closure_report.md`.
- Full-stat exact-position W2 closure: `outputs/reports/v3p5_fullstat_performance_w2_closure_fullstat_v2_exactpos_20260613/v3p5_fullstat_performance_w2_closure_report.md`.
- Full-stat exact-position convergence closure: `outputs/reports/v3p5_exactpos_convergence_20260614/v3p5_exactpos_convergence_report.md`.
- Full-stat `spot_r90` sidecar: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2_spatial/v3p5_spatial_line_proxy.md`.
- Full-stat boundary-closure sidecars: `outputs/reports/v3p5_boundary_closure_20260613/v3p5_boundary_closure_report.md`.
- f10m A1 optics authority with repo-local per-seed CSVs: `stepwise_maintenance/step04_opticsim/optics_aeff_authority_f10m_a1.json`.
- R2 CsI I-128 chain anchor: `stepwise_maintenance/step03_delay_source/outputs/i128_anchor_r2_20260612.md`.
- R2 validator: `code/tools/validate_v3p5_fullstat_r2.py`.
- Archived NUBASE2020 table for ground-state correction audit: `inputs/nubase/nubase_2020.txt`.

Report rule: reports must use `fullstat_v2_exactpos` for current rate-level
claims after the convergence closure, with `fullstat_v2` retained as the
conservative radial-profile baseline cross-check. DEMO2 `equiv2602_aligned`
paths may be cited only as legacy pre-fix comparison/provenance.

Detector-trigger rule: the `.det` authority contains a formal TES main trigger plus 20 native CsI veto triggers. Current production SIM files predate those native triggers, so quantitative veto numbers still come from the Step05 post-processing model.

## 2026-06-12 v3p5 Center-Finger DR Branch

This branch is separate from the old DEMO2 ADR mainline paths above and should
be labeled explicitly in reports.

The `1of10` low-stat label is retained for path/status compatibility. Its
actual split is gamma prompt exposure about `1/10`, non-gamma prompt exposure
about `1/80`, and generated particle count about `1/21.2`; use full-stat v2
for rate-level comparisons.

- Geometry bounds: `geo_refer/DEMO2_DR_v3p5_minpatch_centerfinger_bounds.json`.
- MEGAlib setup: `outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`.
- Pointing: `InstrumentFrame.Rotation 0 45 0`; side window looks `45 deg` upward.
- Far-field/setup sphere: `60 cm`.
- W side collimator: `2 cm` thick square-bore sleeve; not a 376-hole pixel collimator.
- Step00 output: `stepwise_maintenance/step00_geometry/outputs/v3p5_centerfinger/`.
- Step02 1/10 output: `stepwise_maintenance/step02_raw_background_simulation/outputs_v3p5_centerfinger_1of10/`.
- Step02 1/10 status: `PASS_1OF10_TRANSPORT_CLOSURE`.
- Prompt/buildup: each `19/19` jobs passed, `1,190,129` generated particles.
- Fixed delayed source: `786` blocks, `86.382997 Bq`.
- Delayed transport: `SE=100,000`, `ID=100,000`, `TE=1140.447373 s`.
- Step09 focused optics bridge: `PASS_EVENTLIST_BRIDGE_FULL_TRANSPORTED`,
  `37,194/37,194` EventList rows stored in the full detector transport.
- Step05 L1 detector response:
  `PASS_V3P5_STEP05_SIDE_ENTRY_COMPTON_TIME_AXIS_L1`, with side-entry
  Compton/FoV against the tilted Be disk and one common Poisson time-axis draw.
  W2 direct side-Compton/FoV rates are prompt `0 cps`, delayed `0.0157833 cps`,
  and focused signal `0.795747` per unit EventList injection rate; the
  common-time-axis W2 side-Compton/FoV rate is `0.800563 cps` under unit
  signal-rate normalization.
- Step05 physical reference scaling: f10m A1 `A_eff(511)=20.08476 cm2`,
  inherited `T_atm=0.739042`, and injection-plane rate `0.00148435 s^-1` at
  `1e-4 ph cm^-2 s^-1`.
  The inherited `T_atm` is a scalar reference, not an absolute 45 deg
  side-entry line-of-sight transmission. In a plane-parallel atmosphere the
  45 deg slant column is already larger by `sec(45 deg)=1.414`, so final
  absolute flux claims need a dedicated atmospheric LOS recomputation.
- Step06 mission-axis fold:
  `PASS_V3P5_STEP06_TIME_AXIS_1OF10`, output
  `stepwise_maintenance/step06_mission_time_variation/outputs_v3p5_centerfinger_1of10/`.
  W2 mission-mean background/signal are `0.0155714/0.00117281 cps`.
- Step07 source-case ledger:
  `PASS_V3P5_STEP07_SOURCE_CASES_1OF10`, output
  `stepwise_maintenance/step07_source_cases/outputs_v3p5_centerfinger_1of10/`.
  W2 response is `11.8117 cps/(ph cm^-2 s^-1)`.
- Step08 time-dependent significance:
  `PASS_V3P5_STEP08_TIME_DEPENDENT_1OF10`, output
  `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_1of10/`.
  W2 reference `1e-4 ph cm^-2 s^-1`: `Z20d=12.3501`, `T3=0.9428 day`,
  20-day 3-sigma flux `2.429e-5 ph cm^-2 s^-1`. Treat this as low-stat
  closure only because W2 uses `18` final selected background events.
- Unified closure report:
  `outputs/reports/v3p5_centerfinger_1of10_closure/v3p5_centerfinger_1of10_closure_report.md`,
  status `PASS_V3P5_1OF10_TRANSPORT_CLOSURE`.
- Full-stat v2 closure report:
  `outputs/reports/v3p5_fullstat_performance_w2_closure_20260612/report.html`
  and
  `outputs/reports/v3p5_fullstat_performance_w2_closure_20260612/v3p5_fullstat_performance_w2_closure_report.md`,
  status `PASS_V3P5_FULLSTAT_PERFORMANCE_W2_CLOSURE`.
- Full-stat v2 Step02:
  `PASS_FULLSTAT_V2_TRANSPORT_CLOSURE`, output
  `stepwise_maintenance/step02_raw_background_simulation/outputs_v3p5_centerfinger_fullstat_v2/`.
  Prompt/buildup each generated `25,210,216` particles; delayed transport has
  `SE=1,000,000`, `ID=1,000,000`, `TE=11531.59846 s`.
- Full-stat v2 Step05/06/07/08:
  `PASS_V3P5_STEP05_SIDE_ENTRY_COMPTON_TIME_AXIS_L1_FULLSTAT_V2`,
  `PASS_V3P5_STEP06_TIME_AXIS_FULLSTAT_V2`,
  `PASS_V3P5_STEP07_SOURCE_CASES_FULLSTAT_V2`, and
  `PASS_V3P5_STEP08_TIME_DEPENDENT_FULLSTAT_V2`.
  W2 background/signal at Step05 is `0.0729576/0.00118117 cps`;
  Step08 W2 gives `Z20d=5.70221`, `T3=5.46687 day`, and 20-day 3-sigma
  flux `5.26111e-5 ph cm^-2 s^-1`.
- Full-stat v2 W2 background breakdown:
  `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2/w2_background_source_breakdown/`.
  The main W2 background component is prompt `eplus` (`80` events,
  `0.0543377 cps`, `74.5%` of the W2 final background). Delayed W2 activation
  totals `0.0138749 cps` and is led by `Cu64`.
- R2 sidecar repairs:
  `outputs/reports/compare_511_narrow_1Ms_20260612/compare_511_narrow_1Ms.md`
  now labels the old `2.99e-5` TES point as delayed-only aspiration and lists
  the conservative v3p5 fullstat_v2 W2 `6.82301e-5` row. Decay-source normalization
  audits are backfilled in
  `runs/step02_decay_source_v3p5_centerfinger_fullstat_v2/normalization_audit_day15.json`
  and
  `runs/step02_delay_fix_v3p5_centerfinger_fullstat_v2/normalization_audit_groundstate_fix.json`.

Rebuild v3p5 Step02 1/10 summary:

```bash
python3 stepwise_maintenance/step02_raw_background_simulation/code/build_v3p5_centerfinger_1of10_summary.py
```

Rebuild v3p5 low-stat transport closure report:

```bash
python3 code/tools/build_v3p5_centerfinger_1of10_closure_report.py
```

Rebuild v3p5 Step05 L1 response:

```bash
python3 code/tools/build_v3p5_centerfinger_step05_l1_response.py --workers 8
```

Rebuild v3p5 Step06/07/08 low-stat mission fold:

```bash
python3 stepwise_maintenance/step06_mission_time_variation/code/build_v3p5_centerfinger_step06_time_axis.py
python3 stepwise_maintenance/step07_source_cases/code/build_v3p5_centerfinger_step07_source_cases.py
python3 stepwise_maintenance/step08_significance/code/build_v3p5_centerfinger_l1_significance.py
python3 stepwise_maintenance/step08_significance/code/build_v3p5_centerfinger_step08_time_dependent.py
python3 stepwise_maintenance/step08_significance/code/build_performance_curve_comparison_1Ms.py
```

Rebuild v3p5 full-stat v2 summaries and closure products after the raw
transport exists:

```bash
python3 stepwise_maintenance/step02_raw_background_simulation/code/build_v3p5_centerfinger_1of10_summary.py --label fullstat_v2
python3 code/tools/build_v3p5_centerfinger_step05_l1_response.py --label fullstat_v2 --workers 8 --rebuild-cache
python3 stepwise_maintenance/step06_mission_time_variation/code/build_v3p5_centerfinger_step06_time_axis.py --label fullstat_v2
python3 stepwise_maintenance/step07_source_cases/code/build_v3p5_centerfinger_step07_source_cases.py --label fullstat_v2
python3 stepwise_maintenance/step08_significance/code/build_v3p5_centerfinger_step08_time_dependent.py --label fullstat_v2
python3 stepwise_maintenance/step08_significance/code/build_performance_curve_comparison_1Ms.py --v3p5-label fullstat_v2
python3 stepwise_maintenance/step08_significance/code/build_v3p5_w2_background_source_breakdown.py --label fullstat_v2
python3 stepwise_maintenance/step09_optics_bridge/code/build_detector_coupled_focus_response.py --profile v3p5_fullstat_v2
python3 stepwise_maintenance/step08_significance/code/build_v3p5_spatial_line_proxy.py
python3 code/tools/build_v3p5_fullstat_performance_w2_closure_report.py
```

Current exact-position delayed-source rate authority is available as
`fullstat_v2_exactpos`:

```bash
python3 code/tools/build_v3p5_exactpos_delayed_source.py build --source-mode sampled --n-decays 5000 --triggers 1000000 --seed 260613 --workers 8
cosima -s 260613 runs/step02_delay_fix_v3p5_centerfinger_fullstat_v2_exactpos/activation_decay_day15_groundstate_fixed.source
python3 code/tools/build_v3p5_exactpos_delayed_source.py summarize-transport
python3 code/tools/build_v3p5_centerfinger_step05_l1_response.py --label fullstat_v2_exactpos --workers 8
python3 stepwise_maintenance/step06_mission_time_variation/code/build_v3p5_centerfinger_step06_time_axis.py --label fullstat_v2_exactpos
python3 stepwise_maintenance/step07_source_cases/code/build_v3p5_centerfinger_step07_source_cases.py --label fullstat_v2_exactpos
python3 stepwise_maintenance/step08_significance/code/build_v3p5_centerfinger_step08_time_dependent.py --label fullstat_v2_exactpos
python3 stepwise_maintenance/step08_significance/code/build_v3p5_w2_background_source_breakdown.py --label fullstat_v2_exactpos
python3 stepwise_maintenance/step08_significance/code/build_performance_curve_comparison_1Ms.py --v3p5-label fullstat_v2_exactpos
python3 code/tools/build_v3p5_boundary_closure_report.py --label fullstat_v2_exactpos
python3 code/tools/build_v3p5_fullstat_performance_w2_closure_report.py --label fullstat_v2_exactpos
python3 code/tools/build_v3p5_exactpos_convergence_report.py --labels fullstat_v2_exactpos fullstat_v2_exactpos_m05000_s260614 fullstat_v2_exactpos_m20000_s260613 fullstat_v2_exactpos_m50000_s260613
python3 code/tools/validate_v3p5_exactpos_closure.py --label fullstat_v2_exactpos
```

The exactpos run uses 5000 sampled `PointSource` support blocks, stores
`SE=1,000,000`, `ID=1,000,000`, and `TE=11530.473845 s`, and contains no
`RadialProfileBeam` blocks. The M/seed convergence report is
`PASS_EXACTPOS_TRANSPORT_CONVERGENCE` using four transport-backed cases across
`M=5000`, `M=20000`, and `M=50000`; it promotes `fullstat_v2_exactpos` to the
current rate authority. `fullstat_v2` remains the conservative radial-profile
baseline cross-check. Remaining engineering work is optional source-parsing
optimization or a full weighted-table one-block-per-RPIP stress test. The
focused `spot_r90` W2 spatial sidecar is available at
`stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2_spatial/v3p5_spatial_line_proxy.md`
(`Z20d=8.17566`, 20-day 3-sigma flux `3.66943e-5 ph cm-2 s-1`). Boundary
sidecars are now available at
`outputs/reports/v3p5_boundary_closure_20260613/v3p5_boundary_closure_report.md`:
the 45 deg LOS sidecar gives W2 `Z20d=5.02544` and `spot_r90`
`Z20d=7.20533`, while the fixed-template multi-annulus spatial-likelihood
sidecar gives `Z20d=8.45804`. The exactpos boundary package is
`outputs/reports/v3p5_boundary_closure_fullstat_v2_exactpos_20260613/`.

## 2026-05-31 DEMO2 Mainline (Legacy Pre-Fix Review Hold)

2026-06-12 review hold: this DEMO2/mainline chain is retained for provenance
only. Its fixed delayed source is reproduced as over-normalized by `x8.0116`
for I-128 due to multi-rep buildup normalization. Do not quote the rates or
significance values in this section as current authority until a div-corrected
mainline source and downstream Step05+ chain are rerun.

- Fixed delayed activity: `624.27109184 Bq`.
- Delayed transport observation time: `1584.61 s`.
- Current active veto authority: `CsI_Active_Shield`; compatibility token matching still accepts `BGO`, `ACTIVE_SHIELD`, and `CEBR3`.
- Complete day-15 final `480-550 keV` timeline rate: `2.35011 cps`.
- Complete day-15 final `480-550 keV` direct expectation: `2.36821 cps`.
- Prompt/delayed final direct expectations: `0.05357 / 2.31224 cps`.
- Science final direct expectation at `1e-4 ph cm^-2 s^-1`: `0.002399 cps`.
- Half-life audit: `74` prefix-year rows match archived NUBASE line references; W-180 is reduced to `5.09e-21 Bq` and absent from the fixed source.
- CsI activation baseline: CsI active-shield activity is `561.13 Bq` (`89.89%` of fixed source activity); I-128 is `533.28 Bq` (`85.42%` of total). This is not a BGO control simulation.
- BGO control geometry scaffold: `20` BGO active segments, `20` BGO native veto triggers, Cosima overlap `PASS`, BGO active mass `102.57 kg`; source/transport/significance status `NOT_RUN`.

## Half-Life/NUBASE Audit

- Rebuild: `python3 code/tools/audit_groundstate_half_life_units.py`.
- Output: `outputs/reports/half_life_unit_audit/half_life_unit_audit.md`.
- The audit checks `Ey/Gy/My/Ty/ky` rows in `groundstate_activity_corrections.csv`, self-tests `ky/My/Gy/Ty/Py/Ey`, and verifies the fixed source contains no `74180/74183` source blocks.

## CsI Activation Baseline

- Rebuild: `python3 code/tools/audit_csi_activation_baseline.py`.
- Output: `outputs/reports/csi_activation_baseline/csi_activation_baseline.md`.
- The report quantifies the current CsI active-shield activation burden and explicitly records `BGO_control_status=NOT_RUN`.
- A real CsI-vs-BGO conclusion still requires an alternate BGO geometry/source/transport chain through the same Step02-Step08 gates.

## BGO Control Geometry Scaffold

- Rebuild: `python3 code/tools/build_bgo_control_geometry.py`.
- Output: `outputs/geometry/XZTES_ADR_v4c_mkflange_bgo_control/bgo_control_geometry.md`.
- This creates a same-shape DEMO2 control geometry with BGO active-shield material/names, BGO native veto triggers, mass-budget update, and Cosima overlap smoke evidence.
- It is an input scaffold only; BGO delayed source, delayed transport, Step05 selection, and Step08 significance are still not run.

## Step08 Detectability

- Broad `480-550 keV` time-dependent result: `1e-4 ph cm^-2 s^-1` gives `Z20d = 2.0466`.
- That reference source does not reach 3 sigma within the 20-day mission.
- The reported `42.97 day` 3-sigma time is a constant-profile extrapolation beyond the mission duration.
- The broad-window 20-day 3-sigma flux proxy is `1.46e-4 ph cm^-2 s^-1`.

Line-window sidecar:

- Rebuild: `python3 stepwise_maintenance/step08_significance/code/build_line_window_sensitivity.py`.
- Output: `stepwise_maintenance/step08_significance/outputs/line_window_sensitivity.md`.
- `511 +/- 3 sigma_TES` with `sigma_TES = 0.14 keV` gives background `0.18435 cps`, `Z20d = 7.31`, and `T3 = 3.37 day` for the `1e-4` reference source.

Focused-spot spatial proxy:

- Rebuild: `python3 stepwise_maintenance/step08_significance/code/build_spatial_line_proxy.py`.
- Output: `stepwise_maintenance/step08_significance/outputs/spatial_line_proxy.md`.
- For the 511-keV line, the proxy uses only the `995`-row 511-keV Step09 EventList subset, not the full five-energy comb.
- The robust `spot_r90 = 0.1718 cm` cut keeps `0.8995` of the 511-keV signal sample, reduces line-window background to `0.01632 cps`, and gives `Z20d = 22.10`.
- This is an L1 proxy only; it is not a detector-coupled optics PSF transport rerun.

## Rebuild Commands

Validation:

```bash
python3 code/tools/audit_groundstate_half_life_units.py
python3 code/tools/audit_csi_activation_baseline.py
python3 code/tools/build_bgo_control_geometry.py
python3 code/tools/build_review_20260531_closure.py
python3 code/tools/validate_new_geo_re.py
```

Step08:

```bash
python3 stepwise_maintenance/step08_significance/code/build_step08_significance.py
python3 stepwise_maintenance/step08_significance/code/build_line_window_sensitivity.py
python3 stepwise_maintenance/step08_significance/code/build_spatial_line_proxy.py
```

Complete day-15 report from existing summary/figures:

```bash
python3 code/tools/make_complete_day15_report_ADR.py --refresh-from-summary
```

## Legacy Warning

Older records below `MEMORY.md` or old step snapshots may mention the pre-DEMO2 CeBr3 path, `110 Bq` delayed activity, `9003.74 s` delayed observation time, `0.3996 cps` final background, `Z20d=4.886`, or `T3=6.78 day`. Those are historical comparison numbers, not the current DEMO2 mainline.

## 2026-05-31 DEMO2 complete day-15 report update

- Formal report workflow now requires science, prompt, and fixed day-15 delayed streams to be placed on one Poisson time axis before BGO/Compton veto. Direct event-weight spectra are retained only as expectation cross-checks.
- Latest complete PDF: `outputs/reports/day15_complete_report/cosmosray_bg_NEW_GEO_RE_ADR_complete_day15_report.pdf`.
