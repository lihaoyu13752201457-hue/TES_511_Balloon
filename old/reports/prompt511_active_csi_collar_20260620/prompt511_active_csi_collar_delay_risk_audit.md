# Active-CsI Collar Delay-Risk Audit

Status: `PASS_ACTIVE_CSI_COLLAR_DELAY_RISK_AUDIT_SMOKE_ONLY`

This is an activity/decay-line audit of the existing isotope-store smoke. It is not a delayed-source rebuild, delayed transport, day-20 rate, or sensitivity authority.

## Added Collar Activity Estimate

- added raw RP value: `198` / all-volume `6638` (`2.983%`)
- day-15 added-collar activity estimate: `2.33674 Bq`
- current v3p5 fullstat ground-state fixed source total: `85.6367 Bq`
- ratio to current total source activity: `2.729%`
- ratio to current CsI source activity: `3.372%`

## Added Nuclides

| ZA | nuclide | scaled yield | day-15 Bq est. | half-life | W1 photons/decay | W1 line Bq-equiv | decay modes |
|---:|---|---:|---:|---:|---:|---:|---|
| 53128 | I-128 | 41 | 2.21256 | 24.99 m | 4.9678e-05 | 0.000109915 | B-=93.1 8;B+=6.9 8 |
| 55134 | Cs-134 | 55.5 | 0.0409842 | 2.0650 y | 0 | 0 | B-=100;EC=0.00030 12 |
| 53121 | I-121 | 0.5 | 0.0269697 | 2.12 h | 0.211847 | 0.00571345 | B+=100 |
| 55127 | Cs-127 | 0.5 | 0.0269697 | 6.25 h | 0.0613208 | 0.0016538 | B+=100 |
| 51119 | Sb-119 | 0.5 | 0.0269305 | 38.19 h | 0 | 0 | EC=100 |
| 50113 | Sn-113 | 0.5 | 0.00232982 | 115.08 d | 0 | 0 | B+=100 |
| 52123 | Te-123 | 0.5 | 0 | stbl | 0 | 0 | IS=0.89 3;EC=100 |

## Interpretation

- The added collar activity estimate is small relative to the current v3p5 fixed source in this smoke normalization.
- The added inventory is dominated by Cs/I activation products, while the existing W2 delayed 511 table is Cu64/Cu62/Cu61 dominated.
- This supports carrying the active-CsI collar as a low-delay-risk prompt-repair candidate, but it still does not prove a final delayed rate.
