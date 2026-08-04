# S3b Dominant Background Summary

Status: `PASS_S3B_DOMINANT_BACKGROUNDS`

- Geometry: `engineering/geometry_optimization_20260704/28_geoopt_s3b_w2mm_al3mm_shell_20260709/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- Prompt run: `runs/geometry_optimization_20260704/s3b_w2mm_al3mm_shell_eqstats_prompt_eplus_n_20260709`
- ATM511 run: `runs/geometry_optimization_20260704/s3b_w2mm_al3mm_shell_atm511_sidecar_3m_20260709`
- Active veto: `CsI/BGO active scintillator, ActiveShield, CEBR3, and GeoOpt_S2B_CryoShell_Plastic*; W/Al mechanical shell excluded`

## W2 Results

| component | stage | S3b events | S3 events | S3b cps | S3 cps | S3b/S3 |
|---|---|---:|---:|---:|---:|---:|
| eplus | raw | 20 | 29 | 0.0135751 | 0.0196897 | 0.689453 +/- 0.2 |
| eplus | active_veto_pass | 11 | 15 | 0.00746632 | 0.0101843 | 0.733119 +/- 0.291 |
| eplus | side_compton_fov_pass | 10 | 14 | 0.00678757 | 0.00950537 | 0.714077 +/- 0.296 |
| n | raw | 43 | 56 | 0.029187 | 0.0379975 | 0.76813 +/- 0.156 |
| n | active_veto_pass | 3 | 1 | 0.0020363 | 0.000678527 | 3.00106 +/- 3.47 |
| n | side_compton_fov_pass | 3 | 1 | 0.0020363 | 0.000678527 | 3.00106 +/- 3.47 |
| atm511 | raw | 50 | 60 | 0.00970717 | 0.0116605 | 0.832482 +/- 0.159 |
| atm511 | active_veto_pass | 50 | 60 | 0.00970717 | 0.0116605 | 0.832482 +/- 0.159 |
| atm511 | side_compton_fov_pass | 48 | 56 | 0.00931889 | 0.0108831 | 0.856268 +/- 0.168 |

## Geometry Evidence

- Source cards checked: `25`, pass: `True`.
- SIM headers checked: `17`, pass: `True`.
- Expected Geometry: `engineering/geometry_optimization_20260704/28_geoopt_s3b_w2mm_al3mm_shell_20260709/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`.
- Normalized expected Geometry: `engineering/geometry_optimization_20260704/28_geoopt_s3b_w2mm_al3mm_shell_20260709/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`.

## Run Gates

- Prompt run status counts: `{'PASS': 16}`.
- ATM511 status: `PASS_S3B_ATM511_4PI_SIDECAR_REPLAY`.
- No gamma/alpha/eminus/muon/proton/delayed/focused/Step05-08 promotion was run in this S3b package.
