# Stepwise Maintenance

Current retained stepwise material is scoped to Mass_model_511 and the latest
geo-opt branch.

## Retained Outputs

- `step04_opticsim/`: f10m A1 optics authority and effective-area material.
- `step05_veto_time_axis/outputs_Mass_model_511_fullstat_v1_l1/`
- `step05_veto_time_axis/outputs_geo_opt_s1_bpe_w5_fullstat_v1_l1/`
- `step06_mission_time_variation/outputs_Mass_model_511_fullstat_v1/`
- `step06_mission_time_variation/outputs_geo_opt_s1_bpe_w5_fullstat_v1/`
- `step07_source_cases/outputs_Mass_model_511_fullstat_v1/`
- `step07_source_cases/outputs_geo_opt_s1_bpe_w5_fullstat_v1/`
- `step08_significance/outputs_Mass_model_511_fullstat_v1/`
- `step08_significance/outputs_geo_opt_s1_bpe_w5_fullstat_v1/`
- `step09_optics_bridge/outputs_f10m_a1_v3p5/`: shared EventList/side-entry
  bridge used by the current Mass_model_511 and geo-opt Step05 wrappers.

Historical v3p5/BGO/fix5 stepwise outputs are no longer active in this cleaned
checkout. `old/` remains available for helper code and static ledgers still used
by the retained wrappers.
