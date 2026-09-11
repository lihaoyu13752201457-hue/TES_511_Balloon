# Full-Chain Product Locator Addendum - 2026-07-03

Status: `MASS_MODEL_511_FULLCHAIN_PRODUCTS_PRESENT_REPLACEMENT_USER_REVIEW_REQUIRED`

This addendum supersedes only the Mass_model_511 product-presence statements in
`FULLCHAIN_PRODUCT_LOCATOR_20260702.md`. The fix5 publication authority listed
there is unchanged.

New current-geometry products now present:

| Product | Status | Evidence | Boundary |
| --- | --- | --- | --- |
| Full-stat delayed source | `PASS_LOCATED_AND_CERTIFIED` | `engineering/Mass_model_511_nearfield_migration_20260701/03_detector_transport/delayed/candidate_Mass_model_511/fullstat_v1/F1/delayed_source_exactpos_summary.json` | source/transport input only |
| Full-stat delayed transport | `PASS_LOCATED_AND_CERTIFIED` | `runs/Mass_model_511_nearfield_migration_20260701/step02_delayed_transport_candidate_Mass_model_511_fullstat_v1/DelayedDecayMassModel511CandidateFullstatV1.inc1.id1.sim.gz` | detector transport only |
| Full-stat Step05 selected-rate extraction | `PASS_LOCATED_AND_CERTIFIED` | `stepwise_maintenance/step05_veto_time_axis/outputs_Mass_model_511_fullstat_v1_l1/step05_Mass_model_511_fullstat_v1_l1_response_summary.json` | not Step06--Step08, not replacement |
| Step06 mission time fold | `PASS_LOCATED_AND_CERTIFIED` | `stepwise_maintenance/step06_mission_time_variation/outputs_Mass_model_511_fullstat_v1/step06_Mass_model_511_fullstat_v1_summary.json` | rate-level fold, not replacement |
| Step07 source cases | `PASS_LOCATED_AND_CERTIFIED` | `stepwise_maintenance/step07_source_cases/outputs_Mass_model_511_fullstat_v1/source_case_summary.json` | source-case rate fold |
| Step08 20-day significance | `PASS_LOCATED_AND_CERTIFIED` | `stepwise_maintenance/step08_significance/outputs_Mass_model_511_fullstat_v1/step08_Mass_model_511_fullstat_v1_time_dependent_summary.json` | time-dependent counting fold, not profile likelihood |
| Replacement review | `USER_REVIEW_REQUIRED_MASS_MODEL_511_NOT_AUTO_REPLACEMENT` | `engineering/Mass_model_511_nearfield_migration_20260701/14_replacement_review_20260703/mass_model_511_replacement_review.json` | formal review exists; not automatic replacement |
| W/collimator selected W2 audit | `PASS_LOCATED_AND_CERTIFIED` | `engineering/Mass_model_511_nearfield_migration_20260701/14_replacement_review_20260703/mass_model_511_w_activation_selected_w2_audit.json` | W/collimator selected delayed W2 rate is `0 cps` |
| P1/P2/P3 Mass_model_511 replay | `PASS_LOCATED_AND_CERTIFIED_NOT_PAPER_APPLIED` | `engineering/Mass_model_511_nearfield_migration_20260701/15_p1_p2_p3_replay_20260703/README.md` | engineering replay only |
| P2 current-geometry atmospheric 511 SIM | `PASS_LOCATED_AND_CERTIFIED` | `runs/Mass_model_511_nearfield_migration_20260701/p2_atm511_unit_Mass_model_511_fullstat_v1/Atm511LowerUnit3M_MassModel511.inc1.id1.sim.gz` | 3,000,000 generated mono-511 events |
| Completion audit | `PASS_AGENT_WORK_COMPLETE_USER_DECISION_REMAINS` | `engineering/Mass_model_511_nearfield_migration_20260701/16_completion_audit_20260704/COMPLETION_AUDIT.md` | closes this engineering pass; no paper `.tex` update |

Statistics match note: the delayed exact-position / M-sampling (`M**2` working
shorthand) matches the fix5 publication authority in point-source blocks and
seed: `M=50000`, `seed=260613`, with delayed transport `SE=ID=1000000`.

New status evidence:
`engineering/Mass_model_511_nearfield_migration_20260701/13_fullstat_closure_20260703/FULLSTAT_DELAYED_STEP05_STATUS.md`

Current Step08 W2 result:

- `Z20d = 7.038367535725279` at `1e-4 ph cm^-2 s^-1`
- 20-day 3-sigma flux = `4.2623520081505106e-05 ph cm^-2 s^-1`

Replacement review result:

- decision = `USER_REVIEW_REQUIRED_MASS_MODEL_511_NOT_AUTO_REPLACEMENT`
- Mass_model_511 W2 background = `0.0480735487894033 cps`
- fix5 W2 background = `0.0392162265186315 cps`
- Mass_model_511/fix5 F3 ratio = `1.108140526558646`
- W/collimator selected delayed W2 rate = `0 cps`

P2 atmospheric 511 current-geometry replay result:

- W2 transfer = `0.38107886823349196 cps / (ph cm^-2 s^-1)`
- Harris Rc~11--13 GV added background = `0.008879747356029538 cps`
- Harris-included 20-day F3 = `4.639334147498458e-05 ph cm^-2 s^-1`

Remaining Mass_model_511 full-chain gaps:

1. User decision on whether to replace the paper-facing fix5 authority with the
   Mass_model_511 branch despite the non-automatic replacement review result.
2. Manuscript application of any accepted Mass_model_511 replacement/P1/P2/P3
   values. No paper `.tex` file is modified by this addendum.
