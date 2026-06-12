# balloon511_f10m_ge111_511line Aeff Authority Draft

- generated_at_utc: `2026-06-11T16:26:33.809997Z`
- git_hash: `5ee622dc887eb59e5f7a65fe2037b0647ad2197e`
- be_radius_mm: `18.98`

## Runs

| label | variant | kind | N | jitter mm | offaxis x arcmin | Aeff cm2 | stat cm2 | r50 mm | r90 mm | within-Be |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| a1_R1_default_seed12345 | a1 | R1_legacy_jitter | 50000 | 0.3 | 0 | 20.05 | 0.156 | 0.8326 | 2.04 | 0.99879 |
| a1_R1_default_seed24680 | a1 | R1_legacy_jitter | 50000 | 0.3 | 0 | 20.38 | 0.157 | 0.83 | 2.062 | 0.99905 |
| a1_R1_default_seed98765 | a1 | R1_legacy_jitter | 50000 | 0.3 | 0 | 19.97 | 0.156 | 0.848 | 2.049 | 0.99854 |
| a1_R2_tilefoot_seed12345 | a1 | R2_honest_tile_footprint | 50000 | 18 | 0 | 20.26 | 0.157 | 7.089 | 10.29 | 0.99856 |
| a1_R2_tilefoot_seed24680 | a1 | R2_honest_tile_footprint | 50000 | 18 | 0 | 20.23 | 0.157 | 7.166 | 10.24 | 0.99840 |
| a1_R2_tilefoot_seed98765 | a1 | R2_honest_tile_footprint | 50000 | 18 | 0 | 19.77 | 0.156 | 7.218 | 10.34 | 0.99804 |
| a1_R3_offaxis_0p25_seed12345 | a1 | offaxis | 50000 | 18 | 0.25 | 16.93 | 0.147 | 7.149 | 10.34 | 0.99876 |
| a1_R3_offaxis_0p25_seed24680 | a1 | offaxis | 50000 | 18 | 0.25 | 16.65 | 0.146 | 7.162 | 10.37 | 0.99874 |
| a1_R3_offaxis_0p25_seed98765 | a1 | offaxis | 50000 | 18 | 0.25 | 16.56 | 0.146 | 7.207 | 10.41 | 0.99873 |
| a1_R4_offaxis_0p5_seed12345 | a1 | offaxis | 50000 | 18 | 0.5 | 9.722 | 0.118 | 7.151 | 10.65 | 0.99800 |
| a1_R4_offaxis_0p5_seed24680 | a1 | offaxis | 50000 | 18 | 0.5 | 9.864 | 0.118 | 7.167 | 10.6 | 0.99852 |
| a1_R4_offaxis_0p5_seed98765 | a1 | offaxis | 50000 | 18 | 0.5 | 9.793 | 0.118 | 7.237 | 10.64 | 0.99818 |
| a1_R5_offaxis_1p0_seed12345 | a1 | offaxis | 50000 | 18 | 1 | 4.361 | 0.0818 | 7.249 | 11.48 | 0.99889 |
| a1_R5_offaxis_1p0_seed24680 | a1 | offaxis | 50000 | 18 | 1 | 4.419 | 0.0823 | 7.351 | 11.45 | 0.99890 |
| a1_R5_offaxis_1p0_seed98765 | a1 | offaxis | 50000 | 18 | 1 | 4.27 | 0.081 | 7.391 | 11.59 | 0.99811 |
| a1_R6_offaxis_2p5_seed12345 | a1 | offaxis | 50000 | 18 | 2.5 | 1.654 | 0.0512 | 9.572 | 15.43 | 0.99804 |
| a1_R6_offaxis_2p5_seed24680 | a1 | offaxis | 50000 | 18 | 2.5 | 1.677 | 0.0516 | 9.396 | 15.57 | 0.99711 |
| a1_R6_offaxis_2p5_seed98765 | a1 | offaxis | 50000 | 18 | 2.5 | 1.633 | 0.0509 | 9.441 | 15.49 | 0.99703 |
| a2_R1_default_seed12345 | a2 | R1_legacy_jitter | 50000 | 0.3 | 0 | 16.72 | 0.13 | 0.8321 | 2.044 | 0.99855 |
| a2_R1_default_seed24680 | a2 | R1_legacy_jitter | 50000 | 0.3 | 0 | 17.05 | 0.131 | 0.834 | 2.063 | 0.99897 |
| a2_R1_default_seed98765 | a2 | R1_legacy_jitter | 50000 | 0.3 | 0 | 16.56 | 0.13 | 0.8312 | 2.038 | 0.99862 |
| a2_R2_tilefoot_seed12345 | a2 | R2_honest_tile_footprint | 50000 | 15 | 0 | 16.84 | 0.131 | 5.975 | 8.61 | 0.99840 |
| a2_R2_tilefoot_seed24680 | a2 | R2_honest_tile_footprint | 50000 | 15 | 0 | 16.73 | 0.13 | 5.98 | 8.666 | 0.99911 |
| a2_R2_tilefoot_seed98765 | a2 | R2_honest_tile_footprint | 50000 | 15 | 0 | 16.61 | 0.13 | 6.024 | 8.623 | 0.99838 |

## Seed Summary

| group | seeds | mean Aeff cm2 | sd Aeff cm2 | mean r50 mm | mean r90 mm | mean emergent |
|---|---:|---:|---:|---:|---:|---:|
| a1_R1_legacy_jitter_offaxis0_0 | 12345,24680,98765 | 20.13 | 0.181 | 0.8369 | 2.05 | 0.24885 |
| a1_R2_honest_tile_footprint_offaxis0_0 | 12345,24680,98765 | 20.08 | 0.221 | 7.158 | 10.29 | 0.24837 |
| a1_offaxis_offaxis0.25_0 | 12345,24680,98765 | 16.71 | 0.154 | 7.173 | 10.37 | 0.20661 |
| a1_offaxis_offaxis0.5_0 | 12345,24680,98765 | 9.793 | 0.0582 | 7.185 | 10.63 | 0.12111 |
| a1_offaxis_offaxis1_0 | 12345,24680,98765 | 4.35 | 0.0613 | 7.33 | 11.51 | 0.05378 |
| a1_offaxis_offaxis2.5_0 | 12345,24680,98765 | 1.655 | 0.0179 | 9.469 | 15.5 | 0.02048 |
| a2_R1_legacy_jitter_offaxis0_0 | 12345,24680,98765 | 16.78 | 0.204 | 0.8324 | 2.048 | 0.24886 |
| a2_R2_honest_tile_footprint_offaxis0_0 | 12345,24680,98765 | 16.72 | 0.0937 | 5.993 | 8.633 | 0.24808 |

## Off-Axis Retention

| run | offaxis x arcmin | Aeff cm2 | MC retention | local-curve retention |
|---|---:|---:|---:|---:|
| a1_R3_offaxis_0p25_seed12345 | 0.25 | 16.93 | 0.8356 | 0.8322 |
| a1_R3_offaxis_0p25_seed24680 | 0.25 | 16.65 | 0.8234 | 0.8322 |
| a1_R3_offaxis_0p25_seed98765 | 0.25 | 16.56 | 0.8377 | 0.8322 |
| a1_R4_offaxis_0p5_seed12345 | 0.5 | 9.722 | 0.4799 | 0.4862 |
| a1_R4_offaxis_0p5_seed24680 | 0.5 | 9.864 | 0.4877 | 0.4862 |
| a1_R4_offaxis_0p5_seed98765 | 0.5 | 9.793 | 0.4953 | 0.4862 |
| a1_R5_offaxis_1p0_seed12345 | 1 | 4.361 | 0.2153 | 0.2138 |
| a1_R5_offaxis_1p0_seed24680 | 1 | 4.419 | 0.2185 | 0.2138 |
| a1_R5_offaxis_1p0_seed98765 | 1 | 4.27 | 0.2160 | 0.2138 |
| a1_R6_offaxis_2p5_seed12345 | 2.5 | 1.654 | 0.0817 | 0.0829 |
| a1_R6_offaxis_2p5_seed24680 | 2.5 | 1.677 | 0.0829 | 0.0829 |
| a1_R6_offaxis_2p5_seed98765 | 2.5 | 1.633 | 0.0826 | 0.0829 |

## Gates

- within_be_capture_fraction_gt_0.995 [a1_R1_default_seed12345]: PASS value=0.9987892485269191
- a1_aeff_range_cm2 [a1_R1_default_seed12345]: PASS value=20.04588
- diffracted_crossings_ge_12000 [a1_R1_default_seed12345]: PASS value=12389
- within_be_capture_fraction_gt_0.995 [a1_R1_default_seed24680]: PASS value=0.9990472409686384
- a1_aeff_range_cm2 [a1_R1_default_seed24680]: PASS value=20.38446
- diffracted_crossings_ge_12000 [a1_R1_default_seed24680]: PASS value=12595
- within_be_capture_fraction_gt_0.995 [a1_R1_default_seed98765]: PASS value=0.9985416835453294
- a1_aeff_range_cm2 [a1_R1_default_seed98765]: PASS value=19.9665
- diffracted_crossings_ge_12000 [a1_R1_default_seed98765]: PASS value=12343
- within_be_capture_fraction_gt_0.995 [a1_R2_tilefoot_seed12345]: PASS value=0.9985625299472928
- a1_aeff_range_cm2 [a1_R2_tilefoot_seed12345]: PASS value=20.256480000000003
- diffracted_crossings_ge_12000 [a1_R2_tilefoot_seed12345]: PASS value=12522
- a1_r2_r50_7.2_pm_1.0_mm [a1_R2_tilefoot_seed12345]: PASS value=7.089393574837358
- a1_r2_r90_10.5_pm_1.5_mm [a1_R2_tilefoot_seed12345]: PASS value=10.285654234035201
- within_be_capture_fraction_gt_0.995 [a1_R2_tilefoot_seed24680]: PASS value=0.9984006397441023
- a1_aeff_range_cm2 [a1_R2_tilefoot_seed24680]: PASS value=20.2257
- diffracted_crossings_ge_12000 [a1_R2_tilefoot_seed24680]: PASS value=12505
- a1_r2_r50_7.2_pm_1.0_mm [a1_R2_tilefoot_seed24680]: PASS value=7.165503416434568
- a1_r2_r90_10.5_pm_1.5_mm [a1_R2_tilefoot_seed24680]: PASS value=10.238788954691712
- within_be_capture_fraction_gt_0.995 [a1_R2_tilefoot_seed98765]: PASS value=0.9980374519584594
- a1_aeff_range_cm2 [a1_R2_tilefoot_seed98765]: PASS value=19.772100000000002
- diffracted_crossings_ge_12000 [a1_R2_tilefoot_seed98765]: PASS value=12229
- a1_r2_r50_7.2_pm_1.0_mm [a1_R2_tilefoot_seed98765]: PASS value=7.217906499508449
- a1_r2_r90_10.5_pm_1.5_mm [a1_R2_tilefoot_seed98765]: PASS value=10.342580397467533
- within_be_capture_fraction_gt_0.995 [a1_R3_offaxis_0p25_seed12345]: PASS value=0.9987572889781091
- within_be_capture_fraction_gt_0.995 [a1_R3_offaxis_0p25_seed24680]: PASS value=0.9987370057320509
- within_be_capture_fraction_gt_0.995 [a1_R3_offaxis_0p25_seed98765]: PASS value=0.9987300967080199
- within_be_capture_fraction_gt_0.995 [a1_R4_offaxis_0p5_seed12345]: PASS value=0.998004323964743
- within_be_capture_fraction_gt_0.995 [a1_R4_offaxis_0p5_seed24680]: PASS value=0.998524106264349
- within_be_capture_fraction_gt_0.995 [a1_R4_offaxis_0p5_seed98765]: PASS value=0.9981836195508587
- within_be_capture_fraction_gt_0.995 [a1_R5_offaxis_1p0_seed12345]: PASS value=0.9988868274582561
- within_be_capture_fraction_gt_0.995 [a1_R5_offaxis_1p0_seed24680]: PASS value=0.9989015012815818
- within_be_capture_fraction_gt_0.995 [a1_R5_offaxis_1p0_seed98765]: PASS value=0.9981067777357062
- within_be_capture_fraction_gt_0.995 [a1_R6_offaxis_2p5_seed12345]: PASS value=0.9980449657869013
- within_be_capture_fraction_gt_0.995 [a1_R6_offaxis_2p5_seed24680]: PASS value=0.9971098265895953
- within_be_capture_fraction_gt_0.995 [a1_R6_offaxis_2p5_seed98765]: PASS value=0.9970326409495549
- within_be_capture_fraction_gt_0.995 [a2_R1_default_seed12345]: PASS value=0.9985489721886336
- a2_aeff_range_cm2 [a2_R1_default_seed12345]: PASS value=16.72245
- diffracted_crossings_ge_12000 [a2_R1_default_seed12345]: PASS value=12405
- within_be_capture_fraction_gt_0.995 [a2_R1_default_seed24680]: PASS value=0.9989716816959342
- a2_aeff_range_cm2 [a2_R1_default_seed24680]: PASS value=17.04915
- diffracted_crossings_ge_12000 [a2_R1_default_seed24680]: PASS value=12642
- within_be_capture_fraction_gt_0.995 [a2_R1_default_seed98765]: PASS value=0.9986158606090213
- a2_aeff_range_cm2 [a2_R1_default_seed98765]: PASS value=16.55775
- diffracted_crossings_ge_12000 [a2_R1_default_seed98765]: PASS value=12282
- within_be_capture_fraction_gt_0.995 [a2_R2_tilefoot_seed12345]: PASS value=0.9983988471699624
- a2_aeff_range_cm2 [a2_R2_tilefoot_seed12345]: PASS value=16.83585
- diffracted_crossings_ge_12000 [a2_R2_tilefoot_seed12345]: PASS value=12491
- within_be_capture_fraction_gt_0.995 [a2_R2_tilefoot_seed24680]: PASS value=0.9991129032258065
- a2_aeff_range_cm2 [a2_R2_tilefoot_seed24680]: PASS value=16.72515
- diffracted_crossings_ge_12000 [a2_R2_tilefoot_seed24680]: PASS value=12400
- within_be_capture_fraction_gt_0.995 [a2_R2_tilefoot_seed98765]: PASS value=0.9983767551335119
- a2_aeff_range_cm2 [a2_R2_tilefoot_seed98765]: PASS value=16.60635
- diffracted_crossings_ge_12000 [a2_R2_tilefoot_seed98765]: PASS value=12321
- r1_r2_aeff_relative_difference_lt_0.02 [a1_seed12345]: PASS value=0.010505899466623716
- r1_r2_aeff_relative_difference_lt_0.02 [a1_seed24680]: PASS value=0.007788285782404876
- r1_r2_aeff_relative_difference_lt_0.02 [a1_seed98765]: PASS value=0.009736308316429926
- r1_r2_aeff_relative_difference_lt_0.02 [a2_seed12345]: PASS value=0.006781302978929653
- r1_r2_aeff_relative_difference_lt_0.02 [a2_seed24680]: PASS value=0.01900387995882502
- r1_r2_aeff_relative_difference_lt_0.02 [a2_seed98765]: PASS value=0.002935181410517759
- offaxis_retention_matches_local_curve_within_0.03 [a1_R3_offaxis_0p25_seed12345]: PASS value=0.0033295204652992183
- offaxis_retention_matches_local_curve_within_0.03 [a1_R3_offaxis_0p25_seed24680]: PASS value=0.008855030618521997
- offaxis_retention_matches_local_curve_within_0.03 [a1_R3_offaxis_0p25_seed98765]: PASS value=0.005446375230725553
- offaxis_retention_matches_local_curve_within_0.03 [a1_R4_offaxis_0p5_seed12345]: PASS value=0.006264764116085564
- offaxis_retention_matches_local_curve_within_0.03 [a1_R4_offaxis_0p5_seed24680]: PASS value=0.001514058635003368
- offaxis_retention_matches_local_curve_within_0.03 [a1_R4_offaxis_0p5_seed98765]: PASS value=0.009097628398440916
- offaxis_retention_matches_local_curve_within_0.03 [a1_R5_offaxis_1p0_seed12345]: PASS value=0.00145469409881277
- offaxis_retention_matches_local_curve_within_0.03 [a1_R5_offaxis_1p0_seed24680]: PASS value=0.004665789896175304
- offaxis_retention_matches_local_curve_within_0.03 [a1_R5_offaxis_1p0_seed98765]: PASS value=0.0021406458355515967
- offaxis_retention_matches_local_curve_within_0.03 [a1_R6_offaxis_2p5_seed12345]: PASS value=0.0012336294248544571
- offaxis_retention_matches_local_curve_within_0.03 [a1_R6_offaxis_2p5_seed24680]: PASS value=1.1979189039487692e-05
- offaxis_retention_matches_local_curve_within_0.03 [a1_R6_offaxis_2p5_seed98765]: PASS value=0.000298397359500463
- seed_aggregate_emergent_focal_diffraction_fraction_0.252_pm_0.006 [a1_R1_legacy_jitter_offaxis0_0]: PASS value=0.24884666666666666
- seed_aggregate_abs_emergent_minus_analytic_lt_0.01 [a1_R1_legacy_jitter_offaxis0_0]: PASS value=0.008634553333333335
- seed_aggregate_emergent_focal_diffraction_fraction_0.252_pm_0.006 [a1_R2_honest_tile_footprint_offaxis0_0]: PASS value=0.24837333333333333
- seed_aggregate_abs_emergent_minus_analytic_lt_0.01 [a1_R2_honest_tile_footprint_offaxis0_0]: PASS value=0.009107886666666667
- seed_aggregate_emergent_focal_diffraction_fraction_0.252_pm_0.006 [a2_R1_legacy_jitter_offaxis0_0]: PASS value=0.24886
- seed_aggregate_abs_emergent_minus_analytic_lt_0.01 [a2_R1_legacy_jitter_offaxis0_0]: PASS value=0.00862122
- seed_aggregate_emergent_focal_diffraction_fraction_0.252_pm_0.006 [a2_R2_honest_tile_footprint_offaxis0_0]: PASS value=0.24808
- seed_aggregate_abs_emergent_minus_analytic_lt_0.01 [a2_R2_honest_tile_footprint_offaxis0_0]: PASS value=0.00940122
