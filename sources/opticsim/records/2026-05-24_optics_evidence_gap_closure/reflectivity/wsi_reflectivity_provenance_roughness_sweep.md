# W/Si reflectivity provenance and roughness sweep

- energy_keV: 511.0
- theta_grid_rad: `1e-08..0.005`, n=220
- roughness_nm: `[0.0, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0]`
- xraydb_version: `4.5.8`
- detail_csv: `records/2026-05-24_optics_evidence_gap_closure/reflectivity/wsi_reflectivity_roughness_sweep.csv`
- summary_json: `records/2026-05-24_optics_evidence_gap_closure/reflectivity/wsi_reflectivity_provenance_roughness_sweep.json`
- backend_crosscheck_status: **PASS**

## Optical Constants

| material | density_g_cm3 | delta | beta | mu_cm_inv | attenuation_length_cm |
|---|---:|---:|---:|---:|---:|
| W | 19.3 | 1.22215e-08 | 1.94962e-11 | 2.58248 | 0.399663 |
| Si | 2.33 | 1.8442e-09 | 6.14545e-15 | 0.201933 | 4.93091 |

## Roughness Sweep

| roughness_nm | max_R | theta_at_max_R_rad | theta_R_ge_0p5_max_rad | R_at_theta_min | R_at_theta_max | max_abs_delta_manual_vs_xraydb |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 1 | 1e-08 | 0.000380184 | 1 | 1.55513e-07 | 0 |
| 0.2 | 1 | 1e-08 | 0.000380184 | 1 | 3.53103e-19 | 0 |
| 0.5 | 1 | 1e-08 | 0.000185234 | 1 | 2.61586e-80 | 0 |
| 1 | 1 | 1e-08 | 0.000185234 | 1 | 1.24498e-298 | 0 |
| 2 | 1 | 1e-08 | 0.000154758 | 1 | 0 | 0 |
| 5 | 0.999999 | 1e-08 | 0.000154758 | 0.999999 | 0 | 0 |
| 10 | 0.999996 | 1e-08 | 0.000154758 | 0.999996 | 0 | 0 |

## Interpretation

- This is an independent code-path provenance check: `xraydb.multilayer_reflectivity` is compared with the repository's manual s-polarization Parratt recursion using the same xraydb optical constants.
- It is not an IMD/IDL source recovery. It closes the local implementation/provenance gap, not the unpublished 511-CAM production-table gap.
- The sweep is a roughness systematic: it reports how W/Si reflectivity changes across the roughness values without tuning public wall-by-wall transmission toward 0.80.
