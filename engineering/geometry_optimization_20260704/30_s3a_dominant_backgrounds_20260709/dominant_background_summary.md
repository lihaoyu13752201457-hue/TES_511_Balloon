# S3a Dominant Background Summary

Status: `PASS_S3A_DOMINANT_BACKGROUND_SUMMARY`

- Geometry: `engineering/geometry_optimization_20260704/27_geoopt_s3a_bgo_barrel_20260709/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- Scope: prompt `eplus`, prompt `n`, and 4pi atmospheric 511-keV sidecar only.
- Active veto: BGO/CsI active scintillator, ActiveShield, CEBR3, and `GeoOpt_S2B_CryoShell_Plastic*`; mechanical shells are excluded.
- Comparison: counting-only S3a/S3 ratios using S3 baseline summaries from `22_s3_eqstats_prompt_atm511_20260709`.

| component | stage | S3 events | S3a events | S3 cps | S3a cps | S3a/S3 |
|---|---|---:|---:|---:|---:|---:|
| eplus | raw | 29 | 2 | 0.0196897 | 0.00135691 | 0.0689146 +/- 0.0504 |
| eplus | active_veto_pass | 15 | 1 | 0.0101843 | 0.000678454 | 0.0666175 +/- 0.0688 |
| eplus | side_compton_fov_pass | 14 | 1 | 0.00950537 | 0.000678454 | 0.0713758 +/- 0.0739 |
| n | raw | 56 | 33 | 0.0379975 | 0.0223885 | 0.589211 +/- 0.129 |
| n | active_veto_pass | 1 | 5 | 0.000678527 | 0.0033922 | 4.99936 +/- 5.48 |
| n | side_compton_fov_pass | 1 | 4 | 0.000678527 | 0.00271376 | 3.99949 +/- 4.47 |
| atm511 | raw | 60 | 10 | 0.0116605 | 0.00194248 | 0.166586 +/- 0.0569 |
| atm511 | active_veto_pass | 60 | 10 | 0.0116605 | 0.00194248 | 0.166586 +/- 0.0569 |
| atm511 | side_compton_fov_pass | 56 | 9 | 0.0108831 | 0.00174823 | 0.160636 +/- 0.0577 |

## Geometry Evidence

- Source cards all S3a: `True`.
- Prompt generated source cards all S3a: `True`.
- Prompt SIM headers all S3a: `True`.
- ATM511 source/SIM header S3a: `True` / `True`.

No gamma/alpha/eminus/muon/proton/delayed/focused/Step05--08 promotion was run by this S3a package.
