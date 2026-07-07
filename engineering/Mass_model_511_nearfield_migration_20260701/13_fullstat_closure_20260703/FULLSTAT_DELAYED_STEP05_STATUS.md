# Mass_model_511 Full-Stat Delayed + Step05 Status - 2026-07-03

Status: `PASS_FULLSTAT_STEP08_CURRENT_GEOMETRY_NOT_REPLACEMENT`

Claim boundary: this records the current-geometry Mass_model_511 full-stat
delayed transport, Step05 selected-rate extraction, and Step06--Step08
rate-level 20-day significance. It is not a manuscript update. The formal
replacement review and Mass_model_511 P1/P2/P3 replay are tracked separately
below.

## Statistics Match Gate

The Mass_model_511 delayed source/transport was run with the same exact-position
/ M-sampling (`M**2` working shorthand) statistics as the fix5 publication
authority:

| Quantity | fix5 authority | Mass_model_511 current run | Status |
| --- | ---: | ---: | --- |
| exact-position point-source blocks `M` | 50000 | 50000 | `PASS` |
| sampling seed | 260613 | 260613 | `PASS` |
| delayed transport generated decays `SE/ID` | 1000000 / 1000000 | 1000000 / 1000000 | `PASS` |

Reference fix5 label:
`fix5_fullstat_v2_exactpos_m50000_s260613`.

Current delayed source:
`runs/Mass_model_511_nearfield_migration_20260701/step02_delay_exactpos_candidate_Mass_model_511_fullstat_v1/activation_decay_day15_groundstate_fixed_exactpos.source`

Current delayed transport:
`runs/Mass_model_511_nearfield_migration_20260701/step02_delayed_transport_candidate_Mass_model_511_fullstat_v1/DelayedDecayMassModel511CandidateFullstatV1.inc1.id1.sim.gz`

Header check: the delayed SIM header points to the current Mass_model_511
geometry:
`outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`.

## Delayed Source And Transport

Source summary:
`engineering/Mass_model_511_nearfield_migration_20260701/03_detector_transport/delayed/candidate_Mass_model_511/fullstat_v1/F1/delayed_source_exactpos_summary.json`

Transport campaign manifest:
`engineering/Mass_model_511_nearfield_migration_20260701/03_detector_transport/delayed_transport_campaign_manifest_candidate_Mass_model_511_fullstat_v1.json`

Key values:

| Quantity | Value |
| --- | ---: |
| status | `PASS_MASS_MODEL_511_CANDIDATE_MASS_MODEL_511_FULLSTAT_V1_EXACTPOS_DELAYED_TRANSPORT` |
| fixed day-15 activity | `141.83343806308812 Bq` |
| RPIP lines seen | `389344` |
| eligible RPIP rows | `380872` |
| point-source blocks | `50000` |
| flux per point source | `0.0028366687612617625 Bq` |
| delayed transport `TE` | `7027.052893 s` |

## Step05 Detector Response

Step05 output:
`stepwise_maintenance/step05_veto_time_axis/outputs_Mass_model_511_fullstat_v1_l1/step05_Mass_model_511_fullstat_v1_l1_response_summary.md`

Status:
`PASS_MASS_MODEL_511_STEP05_SIDE_ENTRY_COMPTON_TIME_AXIS_L1_FULLSTAT_V1_NOT_REPLACEMENT`

For W2 (`510.58--511.42 keV`) after active veto plus side-entry Compton/FoV
selection:

| Component | Rate |
| --- | ---: |
| prompt | `0.0440889480718 cps` |
| delayed | `0.00398460071759 cps` |
| total background | `0.04807354878939 cps` |
| signal at reference flux | `0.00118476 cps` |
| direct `Z20d = S/sqrt(B)` | `7.1031` |
| direct 20 d 3-sigma flux | `4.22351e-05 ph cm^-2 s^-1` |

Background composition in W2:

| Component | Fraction |
| --- | ---: |
| prompt | `91.7114%` |
| delayed | `8.2886%` |

For the broad 480--550 keV diagnostic window:

| Component | Rate |
| --- | ---: |
| prompt | `0.0624010820015 cps` |
| delayed | `0.00611920824487 cps` |
| total background | `0.06852029024637 cps` |
| direct 20 d 3-sigma flux | `5.03468e-05 ph cm^-2 s^-1` |

## Step06--Step08 Time-Dependent Fold

Step06:
`stepwise_maintenance/step06_mission_time_variation/outputs_Mass_model_511_fullstat_v1/step06_Mass_model_511_fullstat_v1_summary.json`

Step07:
`stepwise_maintenance/step07_source_cases/outputs_Mass_model_511_fullstat_v1/source_case_summary.json`

Step08:
`stepwise_maintenance/step08_significance/outputs_Mass_model_511_fullstat_v1/step08_Mass_model_511_fullstat_v1_time_dependent_summary.json`

Step08 report:
`stepwise_maintenance/step08_significance/outputs_Mass_model_511_fullstat_v1/step08_Mass_model_511_fullstat_v1_time_dependent.md`

Key W2 time-dependent result at reference flux `1e-4 ph cm^-2 s^-1`:

| Quantity | Value |
| --- | ---: |
| time-dependent `Z20d` | `7.038367535725279` |
| `T3` | `3.272692839458616 day` |
| `T5` | `10.081784420495984 day` |
| 20 d 3-sigma flux | `4.2623520081505106e-05 ph cm^-2 s^-1` |
| source counts | `2030.6901082742322` |
| background counts | `83242.17586787479` |
| accidental loss range | `0.0009841865--0.0010778132` |

Layer distinction: `4.22351e-05` is the Step05 direct constant-rate selected
rate estimate, while `4.2623520081505106e-05` is the Step08 time-dependent
20-day fold with analytic accidental live factor.

## Read-Only Reconstruction Checks

Claude/Revan outputs were read only; no Revan rerun was launched in this pass.

- `engineering/revan_compton_crosscheck_smoke_20260702/README.md`
- `engineering/fullrecon_firstpass_20260702/README.md`

## Replacement Review And P1/P2/P3 Replay

Replacement review:
`engineering/Mass_model_511_nearfield_migration_20260701/14_replacement_review_20260703/MASS_MODEL_511_REPLACEMENT_REVIEW.md`

Decision:
`USER_REVIEW_REQUIRED_MASS_MODEL_511_NOT_AUTO_REPLACEMENT`.

Key reason: the current geometry is fully closed with fix5-matched statistics
(`M=50000`, `seed=260613`, `SE=ID=1000000`), but W2 background is higher than
fix5 and the Step08 20-day F3 is worse (`4.2623520081505106e-05` vs
`3.8464002588077305e-05 ph cm^-2 s^-1`).

Mass_model_511 P1/P2/P3 replay:
`engineering/Mass_model_511_nearfield_migration_20260701/15_p1_p2_p3_replay_20260703/README.md`

P2 current-geometry mono-511 transfer was rerun with 3,000,000 generated events:
W2 transfer `0.381079 cps / (ph cm^-2 s^-1)`, Harris Rc~11--13 GV added
background `0.00887975 cps`, and P2-included `F3=4.63933e-05 ph cm^-2 s^-1`.
These replay outputs have not been applied to manuscript `.tex`.

## Still Open

1. User decision on whether Mass_model_511 should replace the paper-facing fix5
   authority despite the non-automatic replacement review result.
2. Manuscript application of any accepted Mass_model_511 replacement/P1/P2/P3
   numbers.
