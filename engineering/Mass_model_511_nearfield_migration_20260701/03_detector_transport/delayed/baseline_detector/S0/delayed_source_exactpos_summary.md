# Mass_model_511_baseline_detector_S0_smoke Exact-Position Delayed Source

Status: `PASS_MASS_MODEL_511_BASELINE_DETECTOR_S0_SMOKE_EXACTPOS_DELAYED_TRANSPORT`.

- source: `runs/Mass_model_511_nearfield_migration_20260701/step02_delay_exactpos_baseline_detector_S0_smoke/activation_decay_day15_groundstate_fixed_exactpos_S0.source`
- manifest: `runs/Mass_model_511_nearfield_migration_20260701/step02_delay_exactpos_baseline_detector_S0_smoke/baseline_detector_S0_exactpos_delayed_source_manifest.json`
- weighted table: `runs/Mass_model_511_nearfield_migration_20260701/step02_delay_exactpos_baseline_detector_S0_smoke/exactpos_weighted_rpip_table_S0.csv`
- geometry: `outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- instant generated: `2521032` / `2521032`
- buildup generated: `2521032` / `2521032`
- fixed day-15 activity: `82.782502 Bq`
- fixed source blocks: `3989`
- RPIP lines/keys: `25809` / `467`
- eligible RPIP rows: `24654`
- PointSource blocks: `50000`
- seed: `260613`
- flux per PointSource: `0.00165565 Bq`
- flux conservation abs delta: `0 Bq`
- source text flux abs delta: `4.00505e-08 Bq`
- W element activity: `0.87336558 Bq`
- W/collimator-volume activity: `0.87336558 Bq`
- sampling audit: `PASS`
- delayed sim: `runs/Mass_model_511_nearfield_migration_20260701/step02_delayed_transport_baseline_detector_S0_smoke/DelayedDecayMassModel511BaselineS0.inc1.id1.sim.gz`
- SE/ID/TS: `100000/100000/1`
- TE: `1211.50624` s

Boundary:
- Mass_model_511_baseline_detector_S0_smoke exact-position delayed source/transport uses matched fix5 buildup production.
- Delayed transport passed only as a transport artifact; delayed rate claims require Step05 detector response, Step06--Step08 propagation, W/collimator checks, and Verifier approval.
