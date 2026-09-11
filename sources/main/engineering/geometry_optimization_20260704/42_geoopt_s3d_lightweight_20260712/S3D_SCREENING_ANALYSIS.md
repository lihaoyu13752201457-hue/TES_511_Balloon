# S3c-C0 versus S3d-O9 Screening Analysis

Status: `FAIL_S3D_SCREENING_PROMOTION_GATES`

This package is a matched screening comparison. It is not the complete eight-family prompt + full delayed Step05-Step08 performance closure.

## Pending inputs

- neutron_only_delayed: waiting for S3d-O9 exact-position delayed summary: engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/fullchain/delayed_source/delayed_source_exactpos_summary.json

## Promotion gates

Decision so far: `FAIL_AT_LEAST_ONE_COMPLETED_GATE`

The O9 candidate is ineligible for promotion and its full-chain production is not authorized. The pending delayed diagnostic cannot reverse a failed mandatory gate.

| gate | S3d result | limit | state |
|---|---:|---:|---:|
| final W2 dominant subset | 0.00621054222 cps | 0.0052 cps | `FAIL` |
| matched focused-signal loss | -0.400633% | 2.00% | `PASS` |
| neutron-only day-15 activity | pending | 57.8243 Bq | `PENDING` |

## Section status

| section | status |
|---|---|
| prompt | `PASS_S3D_PROMPT_EPLUS_N_ANALYZED` |
| atm511 | `PASS_S3D_ATM511_4PI_SIDECAR_REPLAY` |
| signal | `PASS_MATCHED_S3C_C0_S3D_SIGNAL_REPLAY_ANALYZED` |
| neutron_only_delayed | `PENDING` |

## Frozen selection

- W2: `510.58 <= TES energy < 511.42 keV`.
- Active-veto acceptance: summed matched active energy `< 50 keV`; BGO/CsI/ActiveShield/CEBR3 and retained plastic active volumes included; W/Al excluded.
- Side-entry Compton/FoV: retained Step05 `side_keep_from_hits`, reject policy `keep`.
- The literal Knob0 S0/S1-retain rule is not used.

## Counting intervals

Component rate intervals are exact two-sided 95% Garwood intervals. Component rate-ratio intervals use the exact conditional Poisson construction. Signal acceptances use Wilson 95% intervals; its ratio interval uses the Katz approximation and the JSON also records the paired pass/loss table.

Generated files: `data/s3d_screening_analysis.json`, `data/s3d_screening_comparison.csv`, `data/s3d_atm511_replay_summary.json`, and `data/s3d_signal_replay_summary.json`.
