# TES_511_Balloon

Detector-coupled simulation workspace for the 511 keV TES balloon concept.

This checkout has been cleaned to keep only the active Mass_model_511 branch and
the latest geometry-optimization work.

## Current Retained Work

- `engineering/Mass_model_511_nearfield_migration_20260701/`
- `engineering/geometry_optimization_20260704/`

## Current Generated Products

- `outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy/`
- `outputs/reports/Mass_model_511_stage_diam_300_300_300_350_350_400_20260701/`
- `runs/Mass_model_511_nearfield_migration_20260701/`
- `runs/geometry_optimization_20260704/`

## Stepwise Products

The retained stepwise products are the Mass_model_511 and geo-opt outputs under
`stepwise_maintenance/`, plus the shared f10m A1 Step09 EventList bridge:

- `stepwise_maintenance/step05_veto_time_axis/outputs_Mass_model_511_fullstat_v1_l1/`
- `stepwise_maintenance/step05_veto_time_axis/outputs_geo_opt_s1_bpe_w5_fullstat_v1_l1/`
- `stepwise_maintenance/step06_mission_time_variation/outputs_Mass_model_511_fullstat_v1/`
- `stepwise_maintenance/step06_mission_time_variation/outputs_geo_opt_s1_bpe_w5_fullstat_v1/`
- `stepwise_maintenance/step07_source_cases/outputs_Mass_model_511_fullstat_v1/`
- `stepwise_maintenance/step07_source_cases/outputs_geo_opt_s1_bpe_w5_fullstat_v1/`
- `stepwise_maintenance/step08_significance/outputs_Mass_model_511_fullstat_v1/`
- `stepwise_maintenance/step08_significance/outputs_geo_opt_s1_bpe_w5_fullstat_v1/`
- `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/`

## Notes

- `old/` is intentionally retained because current Mass/geo-opt wrappers still
  import the Step05 parser and science-rate ledger from it.
- Historical fix5 strings can still appear inside retained comparison artifacts,
  but fix5 is no longer a top-level active branch or authority in this checkout.
- New outputs should go into new dated directories and must not overwrite the
  retained Mass_model_511 or geometry-optimization products.
