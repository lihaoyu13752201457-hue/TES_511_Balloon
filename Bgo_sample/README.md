# Bgo_sample

Status: `PASS`.

This package is a current-v3p5 BGO equal-attenuation geometry sample for TES_511_Balloon. The Step01 geometry/control closure is complete, a small all-particle Step02 prompt/buildup smoke transport has been run, an activation-probe delayed-source/transport smoke has been run, a low-statistics `1of10` exact-position day-15 delayed-source/transport closure has passed, the full-statistics v2 prompt/buildup plus exact-position day-15 delayed-source/transport gate has passed, the f10m A1 focused Step09 EventList has been transported through the BGO geometry, Step05 L1 detector response has consumed the BGO prompt, exact-position delayed, and focused-signal SIMs, Step06--Step08 mission-time significance has been rebuilt, and a matched BGO-vs-CsI exact-position comparison has passed. These runs close the BGO material branch through the same Step05--Step08 W2 counting-significance gates used by the CsI exact-position authority. The extended sidecar closure also covers detector-coupled spatial cuts, a fixed-template annular likelihood, detector-threshold replay, and the BGO material attenuation design scan.

| quantity | value |
| --- | --- |
| Source CsI thickness side/bottom/top | {'side': 4.0, 'bottom': 5.999999999999998, 'top': 3.0} |
| BGO thickness side/bottom/top | {'side': 2.137, 'bottom': 3.287, 'top': 1.582} |
| BGO veto threshold | 70.0 keV |
| Attenuation max abs relative diff | 0.0731183 |
| BGO active mass | 45.0259 kg |
| Source CsI active mass | 62.8337 kg |
| Active mass ratio BGO/CsI | 0.716589 |
| Logical active segments | 20 |
| BGO proxy detectors at 70 keV | 24 |
| BGO proxy energy-resolution low anchors at 70 keV | 24 |
| Cosima overlap | PASS |
| Step02 prompt/buildup smoke | PASS_BGO_SAMPLE_STEP02_ALLPARTICLE_SMOKE_TRANSPORT |
| Activation-probe RPIP PointSource blocks | 30 |
| Delayed-source/transport smoke | PASS_BGO_SAMPLE_DELAYED_TRANSPORT_SMOKE |
| Delayed smoke SE/ID/TE | 200/200/5.664515 s |
| Step02 `1of10` instant/buildup production | 11/11 + 11/11 jobs, 1,190,129 generated per mode |
| `1of10` fixed day-15 activity | 24.791139 Bq |
| `1of10` exact-position PointSource blocks | 568 |
| `1of10` exact-position delayed transport | PASS_BGO_SAMPLE_1OF10_EXACTPOS_DELAYED_TRANSPORT |
| `1of10` delayed SE/ID/TE | 100000/100000/3730.929734 s |
| Fullstat v2 instant/buildup production | 68/68 + 68/68 jobs, 25,210,216 generated per mode |
| Fullstat v2 raw/fixed day-15 activity | 23.591674 / 23.570474 Bq |
| Fullstat v2 fixed source blocks | 8412 |
| Fullstat v2 eligible RPIP rows | 43,043 |
| Fullstat v2 exact-position PointSource blocks | 5000 |
| Fullstat v2 exact-position sampling | seed 260613, sampling audit PASS |
| Fullstat v2 exact-position delayed transport | PASS_BGO_SAMPLE_FULLSTAT_V2_EXACTPOS_DELAYED_TRANSPORT |
| Fullstat v2 delayed SE/ID/TS/TE | 1000000/1000000/1/39653.861364 s |
| Step09 focused EventList transport | PASS_BGO_SAMPLE_STEP09_FOCUS_TRANSPORT |
| Step09 focused SE/ID/TS/TE | 37194/37194/1/3.7e-05 s |
| Step05 L1 detector response | PASS_BGO_SAMPLE_STEP05_SIDE_ENTRY_COMPTON_TIME_AXIS_L1_FULLSTAT_V2_EXACTPOS |
| Step05 catalog events/pixel hits kept | 1,003,340 / 81,320 |
| Step05 catalog stream events | prompt 675,533; delayed 291,221; science 36,586 |
| Step05 W2 direct B/S at 1e-4 ph cm^-2 s^-1 | 0.0578455 / 0.00118595 cps |
| Step05 W2 direct Z20d/T3/F3 | 6.48194 / 4.28413 d / 4.62824e-05 ph cm^-2 s^-1 |
| Step06 W2 mission-mean B/S at 1e-4 ph cm^-2 s^-1 | 0.0578330 / 0.00117756 cps |
| Step08 W2 time-dependent Z20d/T3/F3 | 6.43475 / 4.21622 d / 4.66219e-05 ph cm^-2 s^-1 |
| BGO-vs-CsI exactpos comparison | PASS_BGO_SAMPLE_VS_CSI_EXACTPOS_COMPARISON |
| BGO/CsI mission-mean background ratio | 0.922619 (-7.738%) |
| BGO/CsI Z20d ratio | 1.04541 (+4.541%) |
| BGO/CsI F3(20d) ratio | 0.956560 (-4.344%; lower is better) |
| Extended closure | PASS_BGO_SAMPLE_EXTENDED_CLOSURE |
| BGO spatial `spot_r90` sidecar Z20d/F3 | 9.15885 / 3.27552e-05 ph cm^-2 s^-1 |
| BGO fixed-template annular likelihood Z20d/F3 | 9.27696 / 3.23382e-05 ph cm^-2 s^-1 |
| BGO threshold replay scan | PASS, 70 keV replay relative error 0 |
| BGO material attenuation scan | PASS, max abs relative diff 0.0731183 < 0.1 |

## Files

- `Bgo_sample.geo`
- `Bgo_sample.det`
- `Bgo_sample.geo.setup`
- `bounds.json`
- `mass_budget.json` / `mass_budget.csv`
- `attenuation_verification.json` / `attenuation_verification.csv`
- `cosima_overlap.log`
- `step02_smoke_summary.json` / `STEP02_SMOKE.md`
- `delayed_smoke_summary.json` / `DELAYED_SMOKE.md`
- `step02_1of10_exactpos_summary.json` / `STEP02_1OF10_EXACTPOS.md`
- `step02_fullstat_v2_exactpos_summary.json` / `STEP02_FULLSTAT_V2_EXACTPOS.md`
- `step09_focus_summary.json` / `STEP09_FOCUS.md`
- `closure_summary.json` / `CLOSURE_SUMMARY.md` (tracked GitHub-facing Step05--Step08/comparison digest)
- `extended_closure_summary.json` / `EXTENDED_CLOSURE_SUMMARY.md` (tracked spatial, threshold-replay, and material-attenuation sidecar closure)
- `extended_closure_threshold_scan.csv`
- `extended_closure_spatial_sidecar.csv`

Local regenerated outputs (ignored by Git because they can be rebuilt):

- `../stepwise_maintenance/step05_veto_time_axis/outputs_bgo_sample_fullstat_v2_exactpos_l1/step05_bgo_sample_l1_response_summary.json`
- `../stepwise_maintenance/step05_veto_time_axis/outputs_bgo_sample_fullstat_v2_exactpos_l1/step05_bgo_sample_l1_response_summary.md`
- `../stepwise_maintenance/step06_mission_time_variation/outputs_bgo_sample_fullstat_v2_exactpos/step06_bgo_sample_fullstat_v2_exactpos_summary.json`
- `../stepwise_maintenance/step07_source_cases/outputs_bgo_sample_fullstat_v2_exactpos/source_case_summary.json`
- `../stepwise_maintenance/step08_significance/outputs_bgo_sample_fullstat_v2_exactpos/step08_bgo_sample_time_dependent_summary.json`
- `../stepwise_maintenance/step09_optics_bridge/outputs_bgo_sample_fullstat_v2_exactpos/detector_coupled_focus_response.json`
- `../stepwise_maintenance/step09_optics_bridge/outputs_bgo_sample_fullstat_v2_exactpos/detector_coupled_spatial_line_cuts.csv`
- `../outputs/reports/bgo_sample_csi_comparison_20260615/bgo_vs_csi_summary.json`
- `../outputs/reports/bgo_sample_csi_comparison_20260615/bgo_vs_csi_report.md`

Code:

- related code: `code/tools/build_bgo_sample_fullstat_exactpos.py`
- related code: `code/tools/build_bgo_sample_step09_focus.py`
- related code: `code/tools/build_v3p5_centerfinger_step05_l1_response.py --label bgo_sample_fullstat_v2_exactpos`
- related code: `stepwise_maintenance/step06_mission_time_variation/code/build_v3p5_centerfinger_step06_time_axis.py --label bgo_sample_fullstat_v2_exactpos`
- related code: `stepwise_maintenance/step07_source_cases/code/build_v3p5_centerfinger_step07_source_cases.py --label bgo_sample_fullstat_v2_exactpos`
- related code: `stepwise_maintenance/step08_significance/code/build_v3p5_centerfinger_step08_time_dependent.py --label bgo_sample_fullstat_v2_exactpos`
- related code: `code/tools/build_bgo_sample_csi_comparison.py`
- related code: `stepwise_maintenance/step09_optics_bridge/code/build_detector_coupled_focus_response.py --profile bgo_sample_fullstat_v2_exactpos`
- related code: `code/tools/build_bgo_sample_extended_closure.py`

## Boundary

- Inner detector-head geometry and side-entry pointing are inherited from the current v3p5 center-finger bounds.
- BGO thicknesses are recomputed against the current v3p5 CsI side/bottom/top thicknesses, not copied from the older `new_geo_re_2` branch.
- The active package and outer Al shell follow the new BGO active-envelope by preserving the original radial and z offsets.
- Step02 smoke has run all eight source-card particle classes (`alpha, eminus, eplus, gamma, muminus, muplus, n, p`) in both prompt and activation-build-up modes at 596 generated particles per mode.
- The delayed-source smoke is built from the p,n activation probe at 50k gamma-equivalent statistics. It uses 30 true RPIP positions, 22 volume-isotope keys, 30 exact-position `PointSource` blocks, and 200 delayed-transport triggers. Its fluxes are DAT-count/probe-time smoke proxies, not day-15 BGO activities.
- The `1of10` exact-position closure uses low-stat prompt and buildup production, a day-15 ground-state-fixed inventory, 568 true-RPIP `PointSource` blocks, and 100000 delayed-transport triggers. Its fixed activity is conserved to `4.32448e-09 Bq`.
- The fullstat v2 exact-position closure uses full-stat prompt/buildup production, a day-15 ground-state-fixed inventory, 43,043 eligible true-RPIP rows, 5000 equal-flux `PointSource` blocks, and 1000000 delayed-transport triggers. Its fixed activity is conserved exactly at the source-card level.
- The Step09 focused transport replays the current f10m A1 v3p5 EventList through `Bgo_sample.geo.setup` and stores `SE=ID=37194`. It is a BGO focused-signal SIM, not a selected detector-response rate.
- Step05 L1 detector response now consumes the BGO prompt, exact-position delayed, and focused SIMs with a 70 keV BGO active-veto threshold. Its W2 direct detector-response expectation is `B/S=0.0578455/0.00118595 cps` at `1e-4 ph cm^-2 s^-1`.
- Step05 direct `Z20d/T3/F3` is a constant-rate detector-response diagnostic only. The material-comparison sensitivity authority is Step08 time-dependent: W2 `Z20d=6.43475`, `T3=4.21622 d`, and `F3(20d)=4.66219e-05 ph cm^-2 s^-1`.
- The matched CsI exact-position comparison gives BGO `F3(20d)` lower by 4.344% and `Z20d` higher by 4.541%. This is the hard-window counting authority.
- The extended sidecar closure gives detector-coupled `spot_r90` spatial `Z20d=9.15885`, fixed-template annular-likelihood `Z20d=9.27696`, a threshold replay scan with exact 70 keV Step08 reproduction, and a material attenuation design scan with max absolute relative difference `0.0731183 < 0.1`. The annular result is a fixed-template sidecar, not a nuisance-profile publication likelihood.
