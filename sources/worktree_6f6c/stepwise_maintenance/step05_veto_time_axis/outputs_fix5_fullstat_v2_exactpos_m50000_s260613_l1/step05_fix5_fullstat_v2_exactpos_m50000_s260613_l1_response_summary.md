# Step05 fix5 Full-Stat L1 Detector Response

Status: `PASS_FIX5_STEP05_SIDE_ENTRY_COMPTON_TIME_AXIS_L1_FULLSTAT_V2_EXACTPOS_NOT_PROMOTION`.

Claim level: fix5 full-stat prompt, exact-position delayed, and fix5 focused-signal detector-response extraction; not a promotion decision until Step06--Step08 and the promotion artifact close. Statistics label: `fix5_fullstat_v2_exactpos_m50000_s260613`.

Inputs:
- prompt: `runs/step02_instant_fix5_fullstat_v2`
- delayed: `runs/step02_delayed_transport_fix5_fullstat_v2_exactpos_m50000_s260613/DelayedDecayFix5FullstatV2ExactposM50000S260613.inc1.id1.sim.gz`
- focused signal: `runs/step09_focus_fix5_fullstat_v2_exactpos_m50000_s260613/Opticsim_laue_f10m_a1_fix5_fullstat_v2_exactpos_m50000_s260613.inc1.id1.sim.gz`

Normalization:
- prompt time: `184.220098 s`
- prompt rate normalization: per-tag `1/sum(TT_tag)` from `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/prompt_normalization_audit.csv`
- delayed observation time: `11649.5648 s`
- focused signal direct rates are first normalized to a unit EventList injection rate (`1 injected focused photon/s`).
- physical reference flux: `0.0001 ph cm^-2 s^-1`
- f10m A1 A_eff(511): `20.08476 cm2`
- inherited T_atm: `0.73904239`
- active-veto threshold: `50 keV`
- T_atm boundary: scalar mainline reference transmission is inherited here; the dedicated 45 deg side-entry LOS atmosphere sidecar is `outputs/reports/v3p5_boundary_closure_fullstat_v2_exactpos_20260613/v3p5_boundary_closure_summary.json`.
- reference injection-plane rate: `0.0014843489 s^-1`

## broad_480_550

| stream | raw rate | active-veto rate | side Compton/FoV rate | final/active |
| --- | ---: | ---: | ---: | ---: |
| prompt | 0.247042 | 0.0732855 | 0.0631059 | 0.861097 |
| delayed | 0.00738225 | 0.00369113 | 0.00317608 | 0.860465 |
| science | 0.816879 | 0.816879 | 0.800317 | 0.979726 |

Physical reference direct expectation:
- background: `0.066282 cps`; signal at reference flux: `0.00118795 cps`
- 20-day counts: S `2052.78`, B `114535`
- Z20d direct S/sqrt(B): `6.06558`; T3 constant-rate direct: `4.89247 day`; 20-day 3-sigma flux: `4.94594e-05 ph cm^-2 s^-1`
- low-stat final background events: `123`; approximate relative Poisson sigma `0.090167`

## w2_510p58_511p42

| stream | raw rate | active-veto rate | side Compton/FoV rate | final/active |
| --- | ---: | ---: | ---: | ---: |
| prompt | 0.118771 | 0.0407123 | 0.036641 | 0.899999 |
| delayed | 0.00463537 | 0.00283272 | 0.0025752 | 0.909091 |
| science | 0.815266 | 0.815266 | 0.798919 | 0.979949 |

Physical reference direct expectation:
- background: `0.0392162 cps`; signal at reference flux: `0.00118587 cps`
- 20-day counts: S `2049.19`, B `67765.6`
- Z20d direct S/sqrt(B): `7.87187`; T3 constant-rate direct: `2.9048 day`; 20-day 3-sigma flux: `3.81104e-05 ph cm^-2 s^-1`
- low-stat final background events: `84`; approximate relative Poisson sigma `0.109109`

## Common Poisson Time Axis

- observation time: `11649.5648 s`
- event instances drawn: `8724801`
- candidates: `8718306` total, `74354` with TES energy, `1134` mixed-stream

| window | raw cps | active-veto cps | side Compton/FoV cps |
| --- | ---: | ---: | ---: |
| broad_480_550 | 1.07772 | 0.898145 | 0.873423 |
| w2_510p58_511p42 | 0.942782 | 0.862521 | 0.842864 |

Pending before fix5 promotion:
- Regenerate Step06--Step08 from this full-stat Step05 output before any final rate, significance, or promotion decision.
- Fix5 focused-signal replay is consumed by this Step05 run; downstream Step07/Step08 and promotion artifacts must be regenerated before any final signal-keep, Z20d, F3(20d), or sensitivity claim.
- Old new_geo_re prompt/delayed numbers remain blocked as pass/fail gates while benchmark alignment is NOT_ALIGNED.
- Append/merge remains blocked unless a PASS merge verdict is produced.

CSV: `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_rates.csv`
Timeline CSV: `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_timeline_rates.csv`
