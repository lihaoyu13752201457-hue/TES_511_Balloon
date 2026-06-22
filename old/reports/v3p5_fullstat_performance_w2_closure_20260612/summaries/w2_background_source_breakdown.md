# v3p5 W2 Background Source Breakdown

Status: `PASS_V3P5_W2_BACKGROUND_SOURCE_BREAKDOWN`.

Statistics label: `fullstat_v2`.

Selection: `W2 510.58-511.42 keV, active veto <50 keV, side-entry Compton/FoV keep/reject-kept`.

Total selected W2 final background rate: `0.0729576` cps from `247` catalog events.

## Top Components

| rank | component | events | rate cps | fraction |
| ---: | --- | ---: | ---: | ---: |
| 1 | prompt:eplus | 80 | 0.0543377 | 0.745 |
| 2 | prompt:n | 6 | 0.00407166 | 0.056 |
| 3 | delayed:Cu64:ColdPlate_MXC_50mK_SD_anchor | 29 | 0.00251483 | 0.034 |
| 4 | delayed:Cu64:Cu_SubstrateSupport_SolidDisk_L0_deepest | 19 | 0.00164765 | 0.023 |
| 5 | delayed:Cu64:DR_MixingChamber_Cu | 15 | 0.00130077 | 0.018 |
| 6 | delayed:Cu64:ColdPlate_CP_100mK_intercept | 10 | 0.000867182 | 0.012 |
| 7 | prompt:muplus | 1 | 0.00067332 | 0.009 |
| 8 | delayed:I122:Cu_SubstrateSupport_SolidDisk_L0_deepest | 7 | 0.000607028 | 0.008 |
| 9 | delayed:Cu62:ColdPlate_MXC_50mK_SD_anchor | 7 | 0.000607028 | 0.008 |
| 10 | delayed:I128:ColdPlate_MXC_50mK_SD_anchor | 6 | 0.000520309 | 0.007 |
| 11 | delayed:Cu64:Still_Shield_Al_side_window_side_wall_above_side_port | 4 | 0.000346873 | 0.005 |
| 12 | delayed:Cs130:Cu_SubstrateSupport_SolidDisk_L0_deepest | 4 | 0.000346873 | 0.005 |
| 13 | delayed:Cs126:Cu_SubstrateSupport_SolidDisk_L0_deepest | 3 | 0.000260155 | 0.004 |
| 14 | delayed:F18:Cu_SubstrateSupport_SolidDisk_L0_deepest | 3 | 0.000260155 | 0.004 |
| 15 | delayed:Cu64:Shield_4K_Al_side_window_side_wall_above_side_port | 3 | 0.000260155 | 0.004 |

Artifacts:
- component CSV: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2/w2_background_source_breakdown/w2_background_components.csv`
- stream CSV: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2/w2_background_source_breakdown/w2_background_streams.csv`
- delayed nuclide CSV: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2/w2_background_source_breakdown/w2_delayed_nuclides.csv`
- figure: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2/w2_background_source_breakdown/w2_background_source_breakdown.png`

Notes:
- Prompt components are grouped by atmospheric source particle tag.
- Delayed components are grouped by primary decay nuclide and first primary-volume hit parsed from the delayed SIM.
- The same Step05 side-entry Compton/FoV selection is recomputed here for W2 background events.
