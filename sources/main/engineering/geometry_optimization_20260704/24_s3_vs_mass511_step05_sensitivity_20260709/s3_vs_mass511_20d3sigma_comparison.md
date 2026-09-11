# S3 vs Mass_model_511 20d 3sigma Flux Comparison

Status: `PASS_S3_VS_MASS511_STEP05_20D3SIGMA_COMPARISON`

| window | S3 F3 20d | Mass_511 F3 20d | Mass/S3 ratio | S3 reduction | S3 B cps | Mass B cps | S3 Z20d | Mass Z20d |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| w2_510p58_511p42 | 2.03844e-05 | 4.22351e-05 | 2.07193 | 51.736% | 0.0113513 | 0.0480735 | 14.7172 | 7.1031 |
| broad_480_550 | 2.64038e-05 | 5.03468e-05 | 1.9068 | 47.556% | 0.0191088 | 0.0685203 | 11.362 | 5.95867 |

Best S3 window: `w2_510p58_511p42`

Notes:
- S3 uses the completed 68-file buildup prompt payload because the S3 instant directory is an audit assembly without SIM payloads.
- Delayed S3 source is exact-position M=50000 with NUBASE ground-state fix and SE/ID=1000000 transport.
- This is the standard Step05 single active-veto threshold comparison; it is not the separate plastic-20-keV replay.
