# Bgo_sample Closure Summary

Status: `PASS_BGO_SAMPLE_MATERIAL_CHAIN_CLOSED`.

This tracked summary preserves the BGO Step05--Step08 hard-window material-comparison authority in Git, while the full regenerated Step05--Step08 output directories remain ignored.

| item | value |
| --- | ---: |
| BGO active-veto threshold | 70 keV |
| Equal-attenuation max abs relative diff | 0.07311829 |
| BGO active mass | 45.02592 kg |
| Source CsI active mass | 62.8337 kg |
| Active mass ratio BGO/CsI | 0.7165888 |
| Outer shell radius | 16.737 cm |
| Step05 status | `PASS_BGO_SAMPLE_STEP05_SIDE_ENTRY_COMPTON_TIME_AXIS_L1_FULLSTAT_V2_EXACTPOS` |
| Step06 status | `PASS_BGO_SAMPLE_STEP06_TIME_AXIS_FULLSTAT_V2_EXACTPOS` |
| Step07 status | `PASS_BGO_SAMPLE_STEP07_SOURCE_CASES_FULLSTAT_V2_EXACTPOS` |
| Step08 status | `PASS_BGO_SAMPLE_STEP08_TIME_DEPENDENT_FULLSTAT_V2_EXACTPOS` |
| Step06 W2 mission-mean background | 0.0578329983466 cps |
| Step06 W2 mission-mean signal at 1e-4 | 0.0011775623785 cps |
| Step08 W2 Z20d | 6.43474787077 |
| Step08 W2 T3 | 4.21622404524 d |
| Step08 W2 F3(20d) | 4.6621873308e-05 ph cm^-2 s^-1 |
| BGO/CsI mission-mean background delta | -7.738% |
| BGO/CsI Z20d delta | 4.541% |
| BGO/CsI F3(20d) delta | -4.344% |

Boundary:
- This is a hard-window counting material comparison only.
- No BGO spatial/profile-likelihood gain is applied to this hard-window comparison.
- BGO spatial, detector-threshold replay, and material attenuation sidecars are tracked separately in `Bgo_sample/EXTENDED_CLOSURE_SUMMARY.md`.
- The detailed regenerated Step05--Step08 outputs are local ignored artifacts; this tracked digest is the GitHub-facing closure record.

Regeneration:
- Step05: `python3 code/tools/build_v3p5_centerfinger_step05_l1_response.py --label bgo_sample_fullstat_v2_exactpos --workers 8`
- Step06: `python3 stepwise_maintenance/step06_mission_time_variation/code/build_v3p5_centerfinger_step06_time_axis.py --label bgo_sample_fullstat_v2_exactpos`
- Step07: `python3 stepwise_maintenance/step07_source_cases/code/build_v3p5_centerfinger_step07_source_cases.py --label bgo_sample_fullstat_v2_exactpos`
- Step08: `python3 stepwise_maintenance/step08_significance/code/build_v3p5_centerfinger_step08_time_dependent.py --label bgo_sample_fullstat_v2_exactpos`
- Comparison: `python3 code/tools/build_bgo_sample_csi_comparison.py`
