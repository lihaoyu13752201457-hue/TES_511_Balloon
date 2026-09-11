# Step05 Mass_model_511 Full-Stat V1 L1 Detector Response

Status: `PASS_MASS_MODEL_511_STEP05_SIDE_ENTRY_COMPTON_TIME_AXIS_L1_FULLSTAT_V1_NOT_REPLACEMENT`

Claim level: current-geometry Mass_model_511 full-stat prompt, exact-position delayed, and focused EventList detector-response extraction. This is not a no-effect/replacement decision and does not replace Step06--Step08.

Inputs:
- prompt: `runs/Mass_model_511_nearfield_migration_20260701/step02_instant_candidate_Mass_model_511_fullstat_v1`
- delayed: `runs/Mass_model_511_nearfield_migration_20260701/step02_delayed_transport_candidate_Mass_model_511_fullstat_v1/DelayedDecayMassModel511CandidateFullstatV1.inc1.id1.sim.gz`
- focused signal: `runs/Mass_model_511_nearfield_migration_20260701/step09_focus_candidate_Mass_model_511_Mass_model_511_smoke/Opticsim_laue_f10m_a1_candidate_Mass_model_511_Mass_model_511_signal_smoke.inc1.id1.sim.gz`
- side-entry bridge source: `stepwise_maintenance/step09_optics_bridge/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/step09_focus_summary.json`

Normalization:
- prompt time: `184.220098 s`
- delayed observation time: `7027.05289 s`
- active-veto threshold: `50 keV`
- reject policy: `keep`

## broad_480_550

| stream | raw rate | active-veto rate | side Compton/FoV rate | final events |
| --- | ---: | ---: | ---: | ---: |
| prompt | 0.22992 | 0.0732555 | 0.0624011 | 92 |
| delayed | 0.0105307 | 0.00640382 | 0.00611921 | 43 |
| science | 0.816368 | 0.816368 | 0.799376 | 29732 |

- background: `0.0685203 cps`; signal at reference flux: `0.00118655 cps`
- Z20d direct S/sqrt(B): `5.95867`; 20-day 3-sigma flux: `5.03468e-05 ph cm^-2 s^-1`
- low-stat final background events: `135`

## w2_510p58_511p42

| stream | raw rate | active-veto rate | side Compton/FoV rate | final events |
| --- | ---: | ---: | ---: | ---: |
| prompt | 0.118016 | 0.0481601 | 0.0440889 | 65 |
| delayed | 0.00611921 | 0.0039846 | 0.0039846 | 28 |
| science | 0.814782 | 0.814782 | 0.798166 | 29687 |

- background: `0.0480735 cps`; signal at reference flux: `0.00118476 cps`
- Z20d direct S/sqrt(B): `7.1031`; 20-day 3-sigma flux: `4.22351e-05 ph cm^-2 s^-1`
- low-stat final background events: `93`

Downstream status:
- Step06--Step08 products were generated separately from this Step05 output.
- Replacement review was completed separately and requires user review; it is not an automatic fix5 replacement.
- Mass_model_511 P1/P2/P3 replay was completed separately and is not paper-applied here.

CSV: `stepwise_maintenance/step05_veto_time_axis/outputs_Mass_model_511_fullstat_v1_l1/step05_Mass_model_511_fullstat_v1_l1_rates.csv`
Timeline CSV: `stepwise_maintenance/step05_veto_time_axis/outputs_Mass_model_511_fullstat_v1_l1/step05_Mass_model_511_fullstat_v1_l1_timeline_rates.csv`
