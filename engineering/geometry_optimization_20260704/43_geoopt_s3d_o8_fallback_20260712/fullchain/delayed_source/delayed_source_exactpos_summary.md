# s3d_o8_neutron_delayed_m50000_20260712_exactpos_m50000_s260613 Exact-Position Delayed Source

Status: `PASS_S3D_O8_NEUTRON_DELAYED_M50000_20260712_EXACTPOS_M50000_S260613_EXACTPOS_DELAYED_TRANSPORT`.

- source: `runs/geometry_optimization_20260704/step02_delay_exactpos_s3d_o8_neutron_delayed_m50000_20260712/activation_decay_day15_groundstate_fixed_exactpos_m50000.source`
- manifest: `runs/geometry_optimization_20260704/step02_delay_exactpos_s3d_o8_neutron_delayed_m50000_20260712/s3d_o8_neutron_delayed_m50000_20260712_exactpos_m50000_s260613_delayed_source_manifest.json`
- weighted table: `runs/geometry_optimization_20260704/step02_delay_exactpos_s3d_o8_neutron_delayed_m50000_20260712/exactpos_weighted_rpip_table_m50000_s260613.csv`
- geometry: `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- instant generated: `7704528` / `7704528`
- buildup generated: `7704528` / `7704528`
- fixed day-15 activity: `29.233166 Bq`
- fixed source blocks: `8566`
- RPIP lines/keys: `61611` / `1604`
- eligible RPIP rows: `55021`
- PointSource blocks: `50000`
- seed: `260613`
- flux per PointSource: `0.00058466332 Bq`
- flux conservation abs delta: `0 Bq`
- source text flux abs delta: `4.93284e-09 Bq`
- W element activity: `1.5293962 Bq`
- W/collimator-volume activity: `2.2001212 Bq`
- sampling audit: `PASS`
- delayed sim: `runs/geometry_optimization_20260704/step02_delayed_transport_s3d_o8_neutron_delayed_m50000_20260712/DelayedDecayS3dO8NeutronM50000.inc1.id1.sim.gz`
- SE/ID/TS: `1000000/1000000/1`
- TE: `32178.402129` s

Boundary:
- The exact-position source uses the O8 neutron-only eight-replica buildup and day-15 NUBASE ground-state-corrected activity.
- It is a transport artifact, not a detector-selected rate authority until the dedicated Step05-Step08 closure is complete.
- Sampling uses M=50000, seed=260613, N_SAMPLE=2000000, raw triggers=1000000, and neutron TT division=8.
