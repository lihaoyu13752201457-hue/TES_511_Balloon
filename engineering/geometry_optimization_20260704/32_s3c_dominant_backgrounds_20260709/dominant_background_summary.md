# S3c Dominant Background Summary

Status: `PASS_S3C_DOMINANT_BACKGROUNDS_EPLUS_N_ATM511`

Scope: S3c geometry, prompt `eplus`, prompt `n`, and atmospheric 511-keV 4pi sidecar only.
Active veto: BGO/CsI active scintillator, ActiveShield/CEBR3, and `GeoOpt_S2B_CryoShell_Plastic*`; W/Al mechanical shell excluded.

## W2 510.58-511.42 keV

| component | stage | S3c events | S3c cps | S3 events | S3 cps | S3c/S3 |
|---|---|---:|---:|---:|---:|---:|
| eplus | raw | 6 | 0.00407992 | 29 | 0.0196897 | 0.207211 +/- 0.0929 |
| eplus | active_veto_pass | 2 | 0.00135997 | 15 | 0.0101843 | 0.133536 +/- 0.101 |
| eplus | side_compton_fov_pass | 2 | 0.00135997 | 14 | 0.00950537 | 0.143074 +/- 0.108 |
| n | raw | 28 | 0.0189938 | 56 | 0.0379975 | 0.49987 +/- 0.116 |
| n | active_veto_pass | 2 | 0.0013567 | 1 | 0.000678527 | 1.99948 +/- 2.45 |
| n | side_compton_fov_pass | 2 | 0.0013567 | 1 | 0.000678527 | 1.99948 +/- 2.45 |
| atm511 | raw | 8 | 0.00155585 | 60 | 0.0116605 | 0.133428 +/- 0.0502 |
| atm511 | active_veto_pass | 8 | 0.00155585 | 60 | 0.0116605 | 0.133428 +/- 0.0502 |
| atm511 | side_compton_fov_pass | 6 | 0.00116688 | 56 | 0.0108831 | 0.107219 +/- 0.0461 |

## Geometry Evidence

- Expected geometry: `engineering/geometry_optimization_20260704/29_geoopt_s3c_bgo_w2mm_al3mm_shell_20260709/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- Source cards Geometry match: `True` (8 files)
- Prompt temp source Geometry match: `True` (16 files)
- Prompt SIM header Geometry match: `True` (16 files)
- ATM511 source/SIM Geometry match: `True`

## Inputs

- Prompt run: `runs/geometry_optimization_20260704/s3c_bgo_w2mm_al3mm_shell_eqstats_prompt_eplus_n_20260709`
- ATM511 run: `runs/geometry_optimization_20260704/s3c_bgo_w2mm_al3mm_shell_atm511_sidecar_3m_20260709`
- S3 prompt baseline: `engineering/geometry_optimization_20260704/22_s3_eqstats_prompt_atm511_20260709/s3_eqstats_prompt_all_summary.json`
- S3 ATM511 baseline: `engineering/geometry_optimization_20260704/22_s3_eqstats_prompt_atm511_20260709/s3_atm511_sidecar_3m_summary.json`
