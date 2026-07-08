# Step01 Plastic Threshold Scan

Status: `PASS_STEP01_POSTPROCESS_PLASTIC_THRESHOLD_SCAN`

Scope: W2 post-processing replay for current geo-opt S1/BPE/W5. This does not
change geometry or rerun transport.

## Rules

- Scanned plastic threshold: `50, 20, 10, 5, 2, 1 keV`.
- Plastic veto: `GeoOpt_S1_PlasticFullWrap* plastic_skin_keV >= threshold`.
- Non-plastic active veto remains fixed at `50 keV`.
- Side Compton/FoV classification is unchanged.
- Science signal check uses the Step05 event catalog: all W2 science raw events
  have `bgo_total_keV = 0`, so this scan creates no W2 active false-veto for
  signal down to `1 keV`.

## Key Result

| threshold keV | e+ final | neutron final | atm511 final | delayed final | signal final |
|---:|---:|---:|---:|---:|---:|
| 50 | 35 | 13 | 107 | 26 | 29684 |
| 20 | 31 | 13 | 107 | 26 | 29684 |
| 10 | 24 | 12 | 107 | 26 | 29684 |
| 5 | 22 | 12 | 107 | 26 | 29684 |
| 2 | 20 | 11 | 107 | 26 | 29684 |
| 1 | 18 | 11 | 107 | 26 | 29684 |

## Approximate Total W2 Budget

This uses the 2026-07-08 4pi atm511 sidecar budget and assumes signal acceptance
is unchanged, as verified by the zero-active signal W2 catalog in this replay.

| threshold keV | total background cps | approx F3(20d) ph cm^-2 s^-1 |
|---:|---:|---:|
| 50 | 0.0561719296626 | 4.62986036016e-05 |
| 20 | 0.053455776496 | 4.51653668561e-05 |
| 10 | 0.0480239788281 | 4.28092175804e-05 |
| 5 | 0.0466659022448 | 4.21995727909e-05 |
| 2 | 0.0446292960352 | 4.12684577565e-05 |
| 1 | 0.043271219452 | 4.0635703999e-05 |

## Interpretation

The scan supports testing a lower plastic readout threshold before changing
geometry. A `10 keV` threshold reduces e+ W2 final candidates from `35` to `24`;
`5 keV` gives `22`. The existing W2 science signal catalog shows zero active
deposit, so no W2 signal active false-veto appears in this replay. Atmospheric
511 is unchanged, so this step is an e+/small-neutron lever rather than the
side-wall gamma solution.

## Outputs

- `step01_plastic_threshold_scan_w2_summary.csv`
- `step01_plastic_threshold_scan_compact.csv`
- `step01_plastic_threshold_scan_total_budget.csv`
- `step01_plastic_threshold_scan_summary.json`
