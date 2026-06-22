# v3p5 Exactpos M/Seed Convergence Report

Status: `PASS_EXACTPOS_TRANSPORT_CONVERGENCE`.
Authority recommendation: `PROMOTE_EXACTPOS_TO_CURRENT_RATE_AUTHORITY`.

This report separates source-level sampling diagnostics from transport-backed W2 rate convergence. Exactpos authority promotion requires transport-backed Step05/Step08 stability across support size and seed.

## Evaluation

- Transport-backed cases: `4`
- Support sizes with transport: `[5000, 20000, 50000]`
- Seeds by support: `{'5000': [260613, 260614], '20000': [260613], '50000': [260613]}`
- W2 delayed cps relative range: `0.187413`
- W2 background cps relative range: `0.0111915`
- Z20d relative range: `0.00550844`

## Problems

- none

## Cases

| label | M | seed | sampling | transport | W2 delayed cps | W2 bg cps | Z20d | F3 20d |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: |
| fullstat_v2_exactpos | 5000 | 260613 | PASS | PASS | 0.00338234 | 0.0624651 | 6.15522 | 4.873910e-05 |
| fullstat_v2_exactpos_m05000_s260614 | 5000 | 260614 | PASS | PASS | 0.00408556 | 0.0631683 | 6.12141 | 4.900828e-05 |
| fullstat_v2_exactpos_m20000_s260613 | 20000 | 260613 | PASS | PASS | 0.00364341 | 0.0627261 | 6.14261 | 4.883921e-05 |
| fullstat_v2_exactpos_m50000_s260613 | 50000 | 260613 | PASS | PASS | 0.00389764 | 0.0629804 | 6.13039 | 4.893649e-05 |

## Artifacts

- Summary JSON: `outputs/reports/v3p5_exactpos_convergence_20260614/v3p5_exactpos_convergence_summary.json`
- Case table: `outputs/reports/v3p5_exactpos_convergence_20260614/v3p5_exactpos_convergence_cases.csv`
