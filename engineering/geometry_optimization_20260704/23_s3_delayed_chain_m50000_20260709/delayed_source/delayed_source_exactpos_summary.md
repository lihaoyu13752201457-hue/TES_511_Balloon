# s3_csi_barrel_fullstat_v1_20260709_exactpos_m50000_s260613 Exact-Position Delayed Source

Status: `PASS_S3_CSI_BARREL_FULLSTAT_V1_20260709_EXACTPOS_M50000_S260613_EXACTPOS_DELAYED_TRANSPORT`.

- source: `runs/geometry_optimization_20260704/step02_delay_exactpos_s3_csi_barrel_fullstat_v1_20260709/activation_decay_day15_groundstate_fixed_exactpos_m50000.source`
- manifest: `runs/geometry_optimization_20260704/step02_delay_exactpos_s3_csi_barrel_fullstat_v1_20260709/s3_csi_barrel_fullstat_v1_20260709_exactpos_m50000_s260613_delayed_source_manifest.json`
- weighted table: `runs/geometry_optimization_20260704/step02_delay_exactpos_s3_csi_barrel_fullstat_v1_20260709/exactpos_weighted_rpip_table_m50000_s260613.csv`
- geometry: `engineering/geometry_optimization_20260704/21_geoopt_s3_csi_barrel_20260709/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- instant generated: `25210216` / `25210216`
- buildup generated: `25210216` / `25210216`
- fixed day-15 activity: `96.958176 Bq`
- fixed source blocks: `8950`
- RPIP lines/keys: `326281` / `1620`
- eligible RPIP rows: `320947`
- PointSource blocks: `50000`
- seed: `260613`
- flux per PointSource: `0.0019391635 Bq`
- flux conservation abs delta: `0 Bq`
- source text flux abs delta: `1.84951e-07 Bq`
- W element activity: `0.83161429 Bq`
- W/collimator-volume activity: `1.2360674 Bq`
- sampling audit: `PASS`
- delayed sim: `runs/geometry_optimization_20260704/step02_delayed_transport_s3_csi_barrel_fullstat_v1_20260709/DelayedDecayS3CsiBarrelFullstatV1M50000.inc1.id1.sim.gz`
- SE/ID/TS: `1000000/1000000/1`
- TE: `10227.143927` s

Boundary:
- s3_csi_barrel_fullstat_v1_20260709_exactpos_m50000_s260613 exact-position delayed source/transport uses matched fix5 buildup production.
- Delayed transport passed only as a transport artifact; delayed rate claims require Step05 detector response, Step06--Step08 propagation, W/collimator checks, and Verifier approval.
