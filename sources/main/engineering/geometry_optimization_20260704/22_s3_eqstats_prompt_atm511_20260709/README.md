# S3 Equal-Stat Prompt + ATM511 vs S2b

Status: `PASS_S3_VS_S2B_EQSTATS_BACKGROUND_COMPARISON`

Equal-statistics geometry comparison of S3 CsI full-wrap barrel against S2b
cryo shell. Same pipelines and event counts as the S2b package
`17_s2b_eqstats_prompt_atm511_20260708`.

## Geometry

- S3: `engineering/geometry_optimization_20260704/21_geoopt_s3_csi_barrel_20260709/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- S2b: `engineering/geometry_optimization_20260704/16_geoopt_s2b_cryo_shell_45deg_20260708/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`

S3 keeps S2b BPE + plastic skins and replaces local CsI/Kapton/Al with the
full-wrap CsI package.

## Runs

| Component | Stats match to S2b | Run dir |
|-----------|--------------------|---------|
| e+, n prompt | 8 replicas, farfield R=60 cm, center (5,0,9) | `runs/geometry_optimization_20260704/s3_csi_barrel_eqstats_prompt_eplus_n_20260709/` |
| atm511 | 3e6 events, same 4π sidecar flux model, seed 26070917 | `runs/geometry_optimization_20260704/s3_csi_barrel_atm511_sidecar_3m_20260709/` |

## Active veto

- Threshold: 50 keV
- Volumes: `CsI*` (incl. `CsI_S3_*`) / BGO / ActiveShield + `GeoOpt_S2B_CryoShell_Plastic*`

## Comparison outputs

- `s3_vs_s2b_eqstats_background_comparison.md`
- `s3_vs_s2b_eqstats_background_comparison.csv`
- `s3_vs_s2b_eqstats_background_comparison_summary.json`
- `s3_atm511_sidecar_3m_summary.json` / `.md`

## Boundary

Prompt e+/n + atm511 geometry comparison only. Not delayed activation, not
focused signal throughput, not Step05–08 promotion.
