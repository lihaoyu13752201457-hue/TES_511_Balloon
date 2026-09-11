# v3p5 W2 Background Source Breakdown

Status: `PASS_V3P5_W2_BACKGROUND_SOURCE_BREAKDOWN`.

Statistics label: `fullstat_v2_exactpos_m50000_s260613`.

Selection: `W2 510.58-511.42 keV, active veto <50 keV, side-entry Compton/FoV keep/reject-kept`.

Total selected W2 final background rate: `0.0629804` cps from `132` catalog events.

## Top Components

| rank | component | events | rate cps | fraction |
| ---: | --- | ---: | ---: | ---: |
| 1 | prompt:eplus | 80 | 0.0543377 | 0.863 |
| 2 | prompt:n | 6 | 0.00407166 | 0.065 |
| 3 | delayed:Cu64:ColdPlate_MXC_50mK_SD_anchor | 20 | 0.00173228 | 0.028 |
| 4 | prompt:muplus | 1 | 0.00067332 | 0.011 |
| 5 | delayed:Cu62:ColdPlate_MXC_50mK_SD_anchor | 4 | 0.000346457 | 0.006 |
| 6 | delayed:Cu64:Cu_SubstrateSupport_SolidDisk_L0_deepest | 4 | 0.000346457 | 0.006 |
| 7 | delayed:Cu64:ColdPlate_CP_100mK_intercept | 3 | 0.000259842 | 0.004 |
| 8 | delayed:Cu64:DR_MixingChamber_Cu | 2 | 0.000173228 | 0.003 |
| 9 | delayed:Cu64:ColdPlate_Still_0p7K | 2 | 0.000173228 | 0.003 |
| 10 | delayed:Cu64:Cu_SubstrateSupport_OpenRing_L4_ZM_panel | 1 | 8.66142e-05 | 0.001 |
| 11 | delayed:Cu64:DR_Still_Pot_Cu | 1 | 8.66142e-05 | 0.001 |
| 12 | delayed:Cu64:ColdPlate_4K | 1 | 8.66142e-05 | 0.001 |
| 13 | delayed:Cu64:DR_Continuous_HEX_CuNi_CP_to_Still | 1 | 8.66142e-05 | 0.001 |
| 14 | delayed:Cu62:DR_Continuous_HEX_CuNi_MXC_to_CP | 1 | 8.66142e-05 | 0.001 |
| 15 | delayed:Cu62:Passive_Cu_Liner_detector_bay_above_side_port | 1 | 8.66142e-05 | 0.001 |

Artifacts:
- component CSV: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2_exactpos_m50000_s260613/w2_background_source_breakdown/w2_background_components.csv`
- stream CSV: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2_exactpos_m50000_s260613/w2_background_source_breakdown/w2_background_streams.csv`
- delayed nuclide CSV: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2_exactpos_m50000_s260613/w2_background_source_breakdown/w2_delayed_nuclides.csv`
- figure: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2_exactpos_m50000_s260613/w2_background_source_breakdown/w2_background_source_breakdown.png`

Notes:
- Prompt components are grouped by atmospheric source particle tag.
- Delayed components are grouped by primary decay nuclide and first primary-volume hit parsed from the delayed SIM.
- The same Step05 side-entry Compton/FoV selection is recomputed here for W2 background events.
