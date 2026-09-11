# s3d_o8_p_activation_20260713_exactpos_m50000_s260613 Exact-Position Delayed Source

Status: `PASS_S3D_O8_P_ACTIVATION_20260713_EXACTPOS_M50000_S260613_EXACTPOS_DELAYED_TRANSPORT`.

- source: `runs/geometry_optimization_20260704/step02_delay_exactpos_s3d_o8_all8_activation_m50000_20260713/p/activation_decay_day15_groundstate_fixed_exactpos_m50000.source`
- manifest: `runs/geometry_optimization_20260704/step02_delay_exactpos_s3d_o8_all8_activation_m50000_20260713/p/s3d_o8_p_exactpos_m50000_s260613_manifest.json`
- weighted table: `runs/geometry_optimization_20260704/step02_delay_exactpos_s3d_o8_all8_activation_m50000_20260713/p/exactpos_weighted_rpip_table_m50000_s260613.csv`
- geometry: `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- instant generated: `1871808` / `1871808`
- buildup generated: `1871808` / `1871808`
- fixed day-15 activity: `1.6908807 Bq`
- fixed source blocks: `2520`
- RPIP lines/keys: `4328` / `570`
- eligible RPIP rows: `4285`
- PointSource blocks: `50000`
- seed: `260613`
- flux per PointSource: `3.3817613e-05 Bq`
- flux conservation abs delta: `0 Bq`
- source text flux abs delta: `1.10532e-09 Bq`
- W element activity: `0.0037062809 Bq`
- W/collimator-volume activity: `0.010051508 Bq`
- sampling audit: `PASS`
- delayed sim: `runs/geometry_optimization_20260704/step02_delayed_transport_s3d_o8_all8_activation_m50000_20260713/p/DelayedDecayS3dO8PM50000.inc1.id1.sim.gz`
- SE/ID/TS: `1000000/1000000/1`
- TE: `445369.147711` s

Boundary:
- s3d_o8_p_activation_20260713_exactpos_m50000_s260613 exact-position delayed source/transport uses matched fix5 buildup production.
- Delayed transport passed only as a transport artifact; delayed rate claims require Step05 detector response, Step06--Step08 propagation, W/collimator checks, and Verifier approval.
