# s3d_o8_alpha_activation_20260713_exactpos_m50000_s260613 Exact-Position Delayed Source

Status: `PASS_S3D_O8_ALPHA_ACTIVATION_20260713_EXACTPOS_M50000_S260613_EXACTPOS_DELAYED_TRANSPORT`.

- source: `runs/geometry_optimization_20260704/step02_delay_exactpos_s3d_o8_all8_activation_m50000_20260713/alpha/activation_decay_day15_groundstate_fixed_exactpos_m50000.source`
- manifest: `runs/geometry_optimization_20260704/step02_delay_exactpos_s3d_o8_all8_activation_m50000_20260713/alpha/s3d_o8_alpha_exactpos_m50000_s260613_manifest.json`
- weighted table: `runs/geometry_optimization_20260704/step02_delay_exactpos_s3d_o8_all8_activation_m50000_20260713/alpha/exactpos_weighted_rpip_table_m50000_s260613.csv`
- geometry: `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- instant generated: `191464` / `191464`
- buildup generated: `191464` / `191464`
- fixed day-15 activity: `0.2515905 Bq`
- fixed source blocks: `513`
- RPIP lines/keys: `571` / `226`
- eligible RPIP rows: `560`
- PointSource blocks: `50000`
- seed: `260613`
- flux per PointSource: `5.03181e-06 Bq`
- flux conservation abs delta: `0 Bq`
- source text flux abs delta: `2.23531e-10 Bq`
- W element activity: `0.0022921285 Bq`
- W/collimator-volume activity: `0.0022921285 Bq`
- sampling audit: `PASS`
- delayed sim: `runs/geometry_optimization_20260704/step02_delayed_transport_s3d_o8_all8_activation_m50000_20260713/alpha/DelayedDecayS3dO8AlphaM50000.inc1.id1.sim.gz`
- SE/ID/TS: `1000000/1000000/1`
- TE: `2872055.496907` s

Boundary:
- s3d_o8_alpha_activation_20260713_exactpos_m50000_s260613 exact-position delayed source/transport uses matched fix5 buildup production.
- Delayed transport passed only as a transport artifact; delayed rate claims require Step05 detector response, Step06--Step08 propagation, W/collimator checks, and Verifier approval.
