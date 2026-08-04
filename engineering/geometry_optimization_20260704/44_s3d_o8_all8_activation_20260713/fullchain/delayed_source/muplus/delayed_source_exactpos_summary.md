# s3d_o8_muplus_activation_20260713_exactpos_m50000_s260613 Exact-Position Delayed Source

Status: `PASS_S3D_O8_MUPLUS_ACTIVATION_20260713_EXACTPOS_M50000_S260613_EXACTPOS_DELAYED_TRANSPORT`.

- source: `runs/geometry_optimization_20260704/step02_delay_exactpos_s3d_o8_all8_activation_m50000_20260713/muplus/activation_decay_day15_groundstate_fixed_exactpos_m50000.source`
- manifest: `runs/geometry_optimization_20260704/step02_delay_exactpos_s3d_o8_all8_activation_m50000_20260713/muplus/s3d_o8_muplus_exactpos_m50000_s260613_manifest.json`
- weighted table: `runs/geometry_optimization_20260704/step02_delay_exactpos_s3d_o8_all8_activation_m50000_20260713/muplus/exactpos_weighted_rpip_table_m50000_s260613.csv`
- geometry: `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- instant generated: `92840` / `92840`
- buildup generated: `92840` / `92840`
- fixed day-15 activity: `0.00055193915 Bq`
- fixed source blocks: `8`
- RPIP lines/keys: `8` / `3`
- eligible RPIP rows: `8`
- PointSource blocks: `50000`
- seed: `260613`
- flux per PointSource: `1.1038783e-08 Bq`
- flux conservation abs delta: `0 Bq`
- source text flux abs delta: `1.33199e-13 Bq`
- W element activity: `0 Bq`
- W/collimator-volume activity: `0 Bq`
- sampling audit: `PASS`
- delayed sim: `runs/geometry_optimization_20260704/step02_delayed_transport_s3d_o8_all8_activation_m50000_20260713/muplus/DelayedDecayS3dO8MuPlusM50000.inc1.id1.sim.gz`
- SE/ID/TS: `1000000/1000000/1`
- TE: `1258991152.384783` s

Boundary:
- s3d_o8_muplus_activation_20260713_exactpos_m50000_s260613 exact-position delayed source/transport uses matched fix5 buildup production.
- Delayed transport passed only as a transport artifact; delayed rate claims require Step05 detector response, Step06--Step08 propagation, W/collimator checks, and Verifier approval.
