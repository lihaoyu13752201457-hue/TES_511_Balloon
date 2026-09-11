# S3 vs S2b Equal-Stat Background Comparison

Prompt: far-field radius `60 cm`, sphere center `(5,0,9) cm`; gamma uses `1e7` events / 12 splits, non-gamma uses 8 replicas.
ATM511: 4π EXPACS-like sidecar, `3e6` events, same nominal flux model as S1/S2b.
Active-veto threshold: `50 keV`.
Active-veto volumes: `CsI*` (incl. `CsI_S3_*`) / BGO / ActiveShield + `GeoOpt_S2B_CryoShell_Plastic*`.

| component | stage | S2b events | S3 events | S2b cps | S3 cps | S3/S2b |
|---|---|---:|---:|---:|---:|---:|
| gamma | raw | 1 | 0 | 0.00542878 | 0 | 0 |
| gamma | active_veto_pass | 0 | 0 | 0 | 0 |  |
| gamma | side_compton_fov_pass | 0 | 0 | 0 | 0 |  |
| eminus | raw | 0 | 0 | 0 | 0 |  |
| eminus | active_veto_pass | 0 | 0 | 0 | 0 |  |
| eminus | side_compton_fov_pass | 0 | 0 | 0 | 0 |  |
| eplus | raw | 52 | 29 | 0.0352625 | 0.0196897 | 0.558375 +/- 0.129 |
| eplus | active_veto_pass | 28 | 15 | 0.0189875 | 0.0101843 | 0.53637 +/- 0.172 |
| eplus | side_compton_fov_pass | 27 | 14 | 0.0183094 | 0.00950537 | 0.519153 +/- 0.171 |
| n | raw | 42 | 56 | 0.0284927 | 0.0379975 | 1.33359 +/- 0.272 |
| n | active_veto_pass | 5 | 1 | 0.00339198 | 0.000678527 | 0.200039 +/- 0.219 |
| n | side_compton_fov_pass | 5 | 1 | 0.00339198 | 0.000678527 | 0.200039 +/- 0.219 |
| p | raw | 1 | 2 | 0.000679398 | 0.00135847 | 1.99953 +/- 2.45 |
| p | active_veto_pass | 0 | 0 | 0 | 0 |  |
| p | side_compton_fov_pass | 0 | 0 | 0 | 0 |  |
| alpha | raw | 0 | 0 | 0 | 0 |  |
| alpha | active_veto_pass | 0 | 0 | 0 | 0 |  |
| alpha | side_compton_fov_pass | 0 | 0 | 0 | 0 |  |
| muminus | raw | 5 | 5 | 0.00340071 | 0.00340477 | 1.0012 +/- 0.633 |
| muminus | active_veto_pass | 0 | 0 | 0 | 0 |  |
| muminus | side_compton_fov_pass | 0 | 0 | 0 | 0 |  |
| muplus | raw | 10 | 9 | 0.00678961 | 0.00611738 | 0.90099 +/- 0.414 |
| muplus | active_veto_pass | 0 | 0 | 0 | 0 |  |
| muplus | side_compton_fov_pass | 0 | 0 | 0 | 0 |  |
| atm511 | raw | 116 | 60 | 0.0225708 | 0.0116605 | 0.51662 +/- 0.0822 |
| atm511 | active_veto_pass | 116 | 60 | 0.0225708 | 0.0116605 | 0.51662 +/- 0.0822 |
| atm511 | side_compton_fov_pass | 108 | 56 | 0.0210142 | 0.0108831 | 0.517896 +/- 0.0853 |

Input note:

- Prompt particles are assembled from clean per-tag run directories; partial interrupted files from early continuation attempts are not used.

Scope notes:

- Equal-stat geometry comparison only; not Step05–08 sensitivity promotion.
- Delayed activation and focused signal throughput not rerun.
- Uncertainties are selected-event Poisson only.
- S3 geometry: `engineering/geometry_optimization_20260704/21_geoopt_s3_csi_barrel_20260709/`
- S2b geometry: `engineering/geometry_optimization_20260704/16_geoopt_s2b_cryo_shell_45deg_20260708/`
