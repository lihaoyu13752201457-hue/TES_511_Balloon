# B-FULL Rocking-Curve Map Status

- status: `ready`
- all rings covered: `True`
- covered ring ids: `[0, 1, 2, 3, 4]`
- missing ring ids: `[]`
- map CSV: `/home/ubuntu/cross_check_laue/laue511_validation/reports/bfull_rocking_curve_map_status/available_rocking_curve_map.csv`

| ring | energy keV | status | curve CSV |
|---:|---:|---|---|
| 0 | 480 | covered | ../../benchmarks/xop_crystal/multiring/ge111_480keV_rocking_curve.csv |
| 1 | 500 | covered | ../../benchmarks/xop_crystal/multiring/ge111_500keV_rocking_curve.csv |
| 2 | 511 | covered | ../../benchmarks/xop_crystal/multiring/ge111_511keV_rocking_curve.csv |
| 3 | 530 | covered | ../../benchmarks/xop_crystal/multiring/ge111_530keV_rocking_curve.csv |
| 4 | 550 | covered | ../../benchmarks/xop_crystal/multiring/ge111_550keV_rocking_curve.csv |

Only rings with an energy-matched external XOP/CRYSTAL rocking curve are written to available_rocking_curve_map.csv. Run B-FULL full-lens external-table validation with --require-rocking-curve-map only after all rings are covered.
