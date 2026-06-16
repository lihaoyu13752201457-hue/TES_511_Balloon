# Bgo_sample vs CsI Exact-Position Comparison

Status: `PASS_BGO_SAMPLE_VS_CSI_EXACTPOS_M50000_COMPARISON`.

Scope: equal-attenuation BGO active shield sample against the current CsI exact-position M=50000 rate authority, using matched Step05--Step08 W2 outputs. No spatial/profile-likelihood gain is applied. The comparison uses the material-specific active-veto thresholds adopted by the two branches: CsI 50 keV and BGO 70 keV.

| metric | CsI exactpos | BGO sample | BGO/CsI | relative change |
| --- | ---: | ---: | ---: | ---: |
| Step05 W2 background (cps) | 0.0629804 | 0.0578455 | 0.918469 | -8.153% |
| Step05 W2 signal at 1e-4 (cps) | 0.00118117 | 0.00118595 | 1.00405 | 0.405% |
| Step06 mission-mean background (cps) | 0.0631923 | 0.057833 | 0.915191 | -8.481% |
| Step06 mission-mean signal at 1e-4 (cps) | 0.00117281 | 0.00117756 | 1.00405 | 0.405% |
| Step08 Z20d | 6.13039 | 6.43475 | 1.04965 | 4.965% |
| Step08 T3 (day) | 4.77766 | 4.21622 | 0.882488 | -11.751% |
| Step08 F3 20d (ph cm^-2 s^-1) | 4.893649e-05 | 4.662187e-05 | 0.952702 | -4.730% |

Interpretation:
- BGO W2 mission-mean background is `-8.481%` relative to CsI.
- BGO W2 20-day significance is `4.965%` relative to CsI.
- BGO W2 20-day 3-sigma flux threshold is `-4.730%` relative to CsI; lower is better.
- BGO active mass is `45.0259 kg` versus the source CsI active mass `62.8337 kg`, ratio `0.716589`.
- Equal-attenuation check max absolute relative difference: `0.0731183`.
- Active-veto thresholds are material-specific: CsI `50 keV`, BGO `70 keV`; this is not a same-threshold veto scan.

Authority files:
- CsI label: `fullstat_v2_exactpos_m50000_s260613`
- CsI Step07: `stepwise_maintenance/step07_source_cases/outputs_v3p5_centerfinger_fullstat_v2_exactpos_m50000_s260613/source_case_summary.json`
- CsI Step08: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2_exactpos_m50000_s260613/step08_v3p5_centerfinger_time_dependent_summary.json`
- BGO Step07: `stepwise_maintenance/step07_source_cases/outputs_bgo_sample_fullstat_v2_exactpos/source_case_summary.json`
- BGO Step08: `stepwise_maintenance/step08_significance/outputs_bgo_sample_fullstat_v2_exactpos/step08_bgo_sample_time_dependent_summary.json`
