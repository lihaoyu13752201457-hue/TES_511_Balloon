# s3d_o8_gamma_activation_20260713_exactpos_m50000_s260613 Exact-Position Delayed Source

Status: `PASS_S3D_O8_GAMMA_ACTIVATION_20260713_EXACTPOS_M50000_S260613_EXACTPOS_DELAYED_TRANSPORT`.

- source: `runs/geometry_optimization_20260704/step02_delay_exactpos_s3d_o8_all8_activation_m50000_20260713/gamma/activation_decay_day15_groundstate_fixed_exactpos_m50000.source`
- manifest: `runs/geometry_optimization_20260704/step02_delay_exactpos_s3d_o8_all8_activation_m50000_20260713/gamma/s3d_o8_gamma_exactpos_m50000_s260613_manifest.json`
- weighted table: `runs/geometry_optimization_20260704/step02_delay_exactpos_s3d_o8_all8_activation_m50000_20260713/gamma/exactpos_weighted_rpip_table_m50000_s260613.csv`
- geometry: `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- instant generated: `10000000` / `10000000`
- buildup generated: `10000000` / `10000000`
- fixed day-15 activity: `0.0054267993 Bq`
- fixed source blocks: `3`
- RPIP lines/keys: `3` / `3`
- eligible RPIP rows: `3`
- PointSource blocks: `50000`
- seed: `260613`
- flux per PointSource: `1.0853599e-07 Bq`
- flux conservation abs delta: `0 Bq`
- source text flux abs delta: `7.16189e-12 Bq`
- W element activity: `0 Bq`
- W/collimator-volume activity: `0 Bq`
- sampling audit: `PASS`
- delayed sim: `runs/geometry_optimization_20260704/step02_delayed_transport_s3d_o8_all8_activation_m50000_20260713/gamma/DelayedDecayS3dO8GammaM50000.inc1.id1.sim.gz`
- SE/ID/TS: `1000000/1000000/1`
- TE: `183019346.724261` s

Boundary:
- s3d_o8_gamma_activation_20260713_exactpos_m50000_s260613 exact-position delayed source/transport uses matched fix5 buildup production.
- Delayed transport passed only as a transport artifact; delayed rate claims require Step05 detector response, Step06--Step08 propagation, W/collimator checks, and Verifier approval.
