# B-FULL Full-Lens XOP Map Scan

- ok: `True`
- executable: `/tmp/opticsim-bfull-build/laue_multiring_bfull_demo`
- map CSV: `/home/ubuntu/cross_check_laue/laue511_validation/reports/bfull_rocking_curve_map_status/available_rocking_curve_map.csv`
- events per offset: `5000`
- all runs registered in Geant4 EM category: `True`
- all runs use G4VEmProcess base: `True`
- transmitted_space rows match summary: `True`
- observed peak/min interaction ratio: `27.333333333333336`
- max |recorded p_reflect - XOP map|: `7.272712987393959e-11`

| offset arcmin | obs Laue frac | interactions | focal d90 cm | history rows | mean p_reflect | max p delta |
|---:|---:|---:|---:|---:|---:|---:|
| -5 | 0.0082 | 41 | 2.44898 | 41 | 0.189819 | 7.27271e-11 |
| -3 | 0.0138 | 69 | 1.50728 | 69 | 0.181707 | 5.24673e-11 |
| -1 | 0.0428 | 214 | 0.618082 | 214 | 0.191054 | 6.92774e-11 |
| 0 | 0.2132 | 1066 | 0.332732 | 1066 | 0.256496 | 3.47389e-11 |
| 1 | 0.045 | 225 | 0.593859 | 225 | 0.185882 | 6.92774e-11 |
| 3 | 0.0132 | 66 | 1.5033 | 66 | 0.183646 | 5.24673e-11 |
| 5 | 0.0078 | 39 | 2.4435 | 39 | 0.205918 | 5.99519e-11 |

Full-lens B-FULL run using a custom G4VEmProcess with --rocking-curve-map and --require-rocking-curve-map. Each recorded Laue interaction p_reflect is checked against the ring-specific XOP/CRYSTAL curve.
