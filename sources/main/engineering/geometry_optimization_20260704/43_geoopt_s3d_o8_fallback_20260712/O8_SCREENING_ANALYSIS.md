# O8 Fallback Screening Analysis

Status: `PASS_O8_SCREENING_PROMOTION_GATES`

This is a matched screening result, not the complete eight-family prompt plus delayed mission closure.

## Preregistered gates

Decision so far: `PASS_ALL_COMPLETED_GATES`

| gate | O8 result | limit | state |
|---|---:|---:|---:|
| final W2 e+/n/atm subset | 0.00446379121 cps | 0.0052 cps | `PASS` |
| matched focused-signal loss | 0.353500% | 2.00% | `PASS` |

## Frozen selection

- Primary line window: `510.58 <= TES energy < 511.42 keV`.
- Active-veto acceptance: summed matched active energy `< 50 keV`.
- Side-entry Compton/FoV: retained `side_keep_from_hits(..., reject_policy='keep')`.
- Signal gate: central matched acceptance loss `<= 2%`.
- Dominant-background gate: central e+/n/atmospheric sum `<= 0.0052 cps`.

Atmospheric output additionally records the IA INIT entry-surface proxy for every final selected event in both branches.

Generated files: `data/s3d_o8_screening_analysis.json`, `data/s3d_o8_screening_comparison.csv`, `data/s3d_o8_atm511_replay_summary.json`, and `data/s3d_o8_signal_replay_summary.json`.
