# s3b_w2mm_al3mm_shell_neutron_delay_m50000_clean_20260710_exactpos_m50000_s260613 Exact-Position Delayed Source

Status: `PASS_S3B_W2MM_AL3MM_SHELL_NEUTRON_DELAY_M50000_CLEAN_20260710_EXACTPOS_M50000_S260613_EXACTPOS_DELAYED_TRANSPORT`.

- source: `runs/geometry_optimization_20260704/step02_delay_exactpos_s3b_w2mm_al3mm_shell_neutron_delay_m50000_clean_20260710/activation_decay_day15_groundstate_fixed_exactpos_m50000.source`
- manifest: `runs/geometry_optimization_20260704/step02_delay_exactpos_s3b_w2mm_al3mm_shell_neutron_delay_m50000_clean_20260710/s3b_w2mm_al3mm_shell_neutron_delay_m50000_clean_20260710_exactpos_m50000_s260613_delayed_source_manifest.json`
- weighted table: `runs/geometry_optimization_20260704/step02_delay_exactpos_s3b_w2mm_al3mm_shell_neutron_delay_m50000_clean_20260710/exactpos_weighted_rpip_table_m50000_s260613.csv`
- geometry: `engineering/geometry_optimization_20260704/28_geoopt_s3b_w2mm_al3mm_shell_20260709/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- instant generated: `7704528` / `7704528`
- buildup generated: `7704528` / `7704528`
- fixed day-15 activity: `99.894831 Bq`
- fixed source blocks: `7721`
- RPIP lines/keys: `334512` / `1586`
- eligible RPIP rows: `293108`
- PointSource blocks: `50000`
- seed: `260613`
- flux per PointSource: `0.0019978966 Bq`
- flux conservation abs delta: `0 Bq`
- source text flux abs delta: `2.22894e-07 Bq`
- W element activity: `22.354359 Bq`
- W/collimator-volume activity: `22.691699 Bq`
- sampling audit: `PASS`
- delayed sim: `runs/geometry_optimization_20260704/step02_delayed_transport_s3b_w2mm_al3mm_shell_neutron_delay_m50000_clean_20260710/DelayedDecayS3bW2mmAl3mmShellNeutronDelayM50000.inc1.id1.sim.gz`
- SE/ID/TS: `1000000/1000000/1`
- TE: `9378.899689` s

Boundary:
- s3b_w2mm_al3mm_shell_neutron_delay_m50000_clean_20260710_exactpos_m50000_s260613 exact-position delayed source/transport uses matched fix5 buildup production.
- Delayed transport passed only as a transport artifact; delayed rate claims require Step05 detector response, Step06--Step08 propagation, W/collimator checks, and Verifier approval.
