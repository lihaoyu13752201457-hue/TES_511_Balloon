# Mass_model_511 Completion Audit - 2026-07-04

Status: `PASS_AGENT_WORK_COMPLETE_USER_DECISION_REMAINS`

This audit closes the requested engineering work after the Mass_model_511
current-geometry full-stat completion pass. It does not modify manuscript
`.tex` files and does not declare Mass_model_511 an automatic replacement for
the paper-facing fix5 authority.

## Requirements Checked

| Requirement | Evidence | Result |
| --- | --- | --- |
| Current-geometry full-stat delayed chain present | `13_fullstat_closure_20260703/FULLSTAT_DELAYED_STEP05_STATUS.json` | `PASS` |
| Delayed exact-position / M-sampling (`M**2`) statistics match fix5 | `M=50000`, `seed=260613`, `SE=ID=1000000` in `FULLSTAT_DELAYED_STEP05_STATUS.json` | `PASS` |
| Delayed SIM header uses current Mass_model_511 geometry | `CURRENT_GEOMETRY_SIM_GZ_LOCATOR_20260703_ADDENDUM_AFTER_DELAYED.md` and direct SIM header check | `PASS` |
| Step05 selected-rate extraction present | `stepwise_maintenance/step05_veto_time_axis/outputs_Mass_model_511_fullstat_v1_l1/step05_Mass_model_511_fullstat_v1_l1_response_summary.json` | `PASS` |
| Step06--Step08 time-dependent fold present | `stepwise_maintenance/step08_significance/outputs_Mass_model_511_fullstat_v1/step08_Mass_model_511_fullstat_v1_time_dependent_summary.json` | `PASS` |
| Replacement/no-effect review completed | `14_replacement_review_20260703/mass_model_511_replacement_review.json` | `USER_REVIEW_REQUIRED_MASS_MODEL_511_NOT_AUTO_REPLACEMENT` |
| W/collimator selected W2 delayed contribution checked | `14_replacement_review_20260703/mass_model_511_replacement_review.json` | `0 cps` |
| Mass_model_511 P1/P2/P3 replay completed | `15_p1_p2_p3_replay_20260703/README.md` | `PASS_MASS_MODEL_511_P1_P2_P3_REPLAY_NOT_PAPER_APPLIED` |
| P2 atmospheric 511 current-geometry 3M run present | `15_p1_p2_p3_replay_20260703/p2_mass_model_511_atm511_transfer_summary.json` | `PASS`; `3000000` generated events |
| Old pending text for completed items removed | `rg` scan over Mass_model_511 engineering package and Step05 output | `PASS_NO_STALE_COMPLETED_ITEM_PENDING_TEXT` |
| No relevant background task still running | `ps -eo pid,comm,args` filtered for cosima, P1/P2/P3 builder, and Mass_model_511 gzip reads | `PASS_NO_MATCHES` |

## Final Engineering Numbers

Mass_model_511 W2 Step08 time-dependent 20-day result:

- `Z20d = 7.038367535725279` at `1e-4 ph cm^-2 s^-1`
- `F3 = 4.2623520081505106e-05 ph cm^-2 s^-1`

Mass_model_511 vs fix5 replacement review:

- decision: `USER_REVIEW_REQUIRED_MASS_MODEL_511_NOT_AUTO_REPLACEMENT`
- Mass_model_511/fix5 F3 ratio: `1.108140526558646`
- Mass_model_511/fix5 Z20d ratio: `0.9024126236999214`
- W/collimator selected delayed W2 rate: `0 cps`

Mass_model_511 P2 atmospheric 511 replay:

- W2 transfer: `0.38107886823349196 cps / (ph cm^-2 s^-1)`
- Harris Rc~11--13 GV added background: `0.008879747356029538 cps`
- Harris-included 20-day F3: `4.639334147498458e-05 ph cm^-2 s^-1`

## Remaining Boundary

The remaining items are not unfinished simulation/engineering work in this pass:

1. User decision on whether to replace the paper-facing fix5 authority with the
   Mass_model_511 branch despite the non-automatic replacement review result.
2. Manuscript application of any accepted Mass_model_511 replacement/P1/P2/P3
   values.

