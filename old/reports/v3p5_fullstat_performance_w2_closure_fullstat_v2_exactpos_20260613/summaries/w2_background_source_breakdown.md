# v3p5 W2 Background Source Breakdown

Status: `PASS_V3P5_W2_BACKGROUND_SOURCE_BREAKDOWN`.

Statistics label: `fullstat_v2_exactpos`.

Selection: `W2 510.58-511.42 keV, active veto <50 keV, side-entry Compton/FoV keep/reject-kept`.

Total selected W2 final background rate: `0.0624651` cps from `126` catalog events.

## Top Components

| rank | component | events | rate cps | fraction |
| ---: | --- | ---: | ---: | ---: |
| 1 | prompt:eplus | 80 | 0.0543377 | 0.870 |
| 2 | prompt:n | 6 | 0.00407166 | 0.065 |
| 3 | delayed:Cu64:Cu_SubstrateSupport_SolidDisk_L0_deepest | 10 | 0.000867267 | 0.014 |
| 4 | delayed:Cu62:ColdPlate_MXC_50mK_SD_anchor | 9 | 0.00078054 | 0.012 |
| 5 | delayed:Cu64:ColdPlate_MXC_50mK_SD_anchor | 8 | 0.000693814 | 0.011 |
| 6 | prompt:muplus | 1 | 0.00067332 | 0.011 |
| 7 | delayed:Cu64:DR_MixingChamber_Cu | 4 | 0.000346907 | 0.006 |
| 8 | delayed:Cu64:Cu_SubstrateSupport_OpenRing_L3_ZP_panel | 4 | 0.000346907 | 0.006 |
| 9 | delayed:Cu64:ColdPlate_CP_100mK_intercept | 1 | 8.67267e-05 | 0.001 |
| 10 | delayed:Cu61:ColdPlate_CP_100mK_intercept | 1 | 8.67267e-05 | 0.001 |
| 11 | delayed:Cu64:ColdPlate_4K | 1 | 8.67267e-05 | 0.001 |
| 12 | delayed:Cu64:Cu_SubstrateSupport_OpenRing_L4_ZP_panel | 1 | 8.67267e-05 | 0.001 |

Artifacts:
- component CSV: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2_exactpos/w2_background_source_breakdown/w2_background_components.csv`
- stream CSV: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2_exactpos/w2_background_source_breakdown/w2_background_streams.csv`
- delayed nuclide CSV: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2_exactpos/w2_background_source_breakdown/w2_delayed_nuclides.csv`
- figure: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2_exactpos/w2_background_source_breakdown/w2_background_source_breakdown.png`

Notes:
- Prompt components are grouped by atmospheric source particle tag.
- Delayed components are grouped by primary decay nuclide and first primary-volume hit parsed from the delayed SIM.
- The same Step05 side-entry Compton/FoV selection is recomputed here for W2 background events.
