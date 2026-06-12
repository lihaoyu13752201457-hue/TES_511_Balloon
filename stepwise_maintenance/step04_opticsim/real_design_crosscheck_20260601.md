# Route-A Real Laue Design Cross-Check (2026-06-01)

This is the design-stage gate for the real Ge(111) B-FULL lens. It stops before detector full-chain integration.

## Gate Summary

| check | value | pass |
| --- | ---: | :---: |
| Bragg radius max residual | 0.000000e+00 mm | True |
| min z surface clearance | not_run mm | True |
| min azimuthal edge gap | 0.521654 mm | True |
| XOP/CRYSTAL map missing rings | [] | True |
| XOP/CRYSTAL map energy mismatches | [] | True |
| diffracted focal r99 | 0.29141 cm | True |
| Be radius | 1.898 cm | - |
| exact 511-keV A_eff | 15.2993 cm2 | - |
| A_eff target residual vs 16 cm2 | 0.043795 | True |
| natural passband FWHM | 500.994-521.006 keV | - |
| sampled line-band A_eff sum | 15.2993 cm2 | - |
| emergent - analytic | -0.00538123 | True |
| strict 0.01 residual diagnostic | 0.00538123 | True |

## Notes

- The optical design is 511-centered: `[511.0]` keV rings are used for the line core/wings; 480-550 keV remains the detector analysis window.
- The external XOP/CRYSTAL map is required for the 511-keV ring ids `[0]` and covers `[0]`.
- The B-FULL run used rocking backend `external_per_ring_csv_map` with map `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step04_opticsim/ge111_balloon511_f9m_511keV_xop_map.csv`.
- Package-level validation summary anchor: `/home/ubuntu/cross_check_laue/laue511_validation/reports/laue511_crosscheck_summary.md`.
- Ring ids for A_eff are reconstructed by joining `focal_crossings.csv` to `optics_history.csv` on `event_id`; unmatched diffracted rows = `0`.
- `phase_space.csv` is not used for science handoff or A_eff.

## Per-Energy A_eff

| ring | E keV | area cm2 | primaries | within-Be rows | efficiency | A_eff cm2 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 511 | 60.75 | 50000 | 12592 | 0.25184 | 15.2993 |
