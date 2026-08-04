# Reference baseline background breakdown

Status: `PASS_REFERENCE_BASELINE_BACKGROUND_BREAKDOWN`

This is an engineering provenance report. Manuscript text must use descriptive configuration names.

## Selected W2 background

- Prompt: `0.0440889481 cps` from `65` weighted events.
- Delayed: `0.00398460072 cps` from `28` weighted events.
- Total: `0.0480735488 +/- 0.00552 cps` (MC counting, 1 sigma).
- Prompt fraction: `91.711%`.

## Prompt particles after the full selection

| particle | events | rate (cps) | fraction of prompt |
| --- | ---: | ---: | ---: |
| eplus | 45 | 0.030529918 | 0.692 |
| n | 18 | 0.0122099294 | 0.277 |
| muplus | 2 | 0.00134910072 | 0.031 |

## Delayed inventory versus selected survivors

The day-15 corrected inventory is `141.833 Bq`. Its leading sampled inventory entries are iodine-128 in CsI shield volumes, followed by aluminium-28 and copper-64 entries. The final selected W2 survivors are different:

| nuclide | events | rate (cps) | fraction of delayed |
| --- | ---: | ---: | ---: |
| Cu-64 | 25 | 0.00355767921 | 0.893 |
| Cu-61 | 2 | 0.000284614337 | 0.071 |
| Cu-62 | 1 | 0.000142307168 | 0.036 |

All 28 delayed W2 survivors trace to copper-bearing cold-stage structures; 25 are Cu-64. The distinction between total activity and selected background is therefore mandatory.

## Mission fold

- 20-day Z at 1e-4 ph cm^-2 s^-1: `7.038368`.
- 20-day 3-sigma flux threshold: `4.262352e-05 ph cm^-2 s^-1`.

## Provenance

- step05_summary: `stepwise_maintenance/step05_veto_time_axis/outputs_Mass_model_511_fullstat_v1_l1/step05_Mass_model_511_fullstat_v1_l1_response_summary.json`
- event_catalog: `stepwise_maintenance/step05_veto_time_axis/outputs_Mass_model_511_fullstat_v1_l1/work/event_catalog.pkl`
- step08_summary: `stepwise_maintenance/step08_significance/outputs_Mass_model_511_fullstat_v1/step08_Mass_model_511_fullstat_v1_time_dependent_summary.json`
- delayed_source_summary: `engineering/Mass_model_511_nearfield_migration_20260701/03_detector_transport/delayed/candidate_Mass_model_511/fullstat_v1/F1/delayed_source_exactpos_summary.json`
- delayed_selected_event_authority: `engineering/Mass_model_511_nearfield_migration_20260701/14_replacement_review_20260703/mass_model_511_w_activation_selected_w2_events.csv`
