# bgo_p1_exactpos_m5000_s260613 Exact-Position Delayed Source

Status: `PASS_BGO_P1_EXACTPOS_M5000_S260613_EXACTPOS_DELAYED_TRANSPORT`.

- source: `engineering/background_validation_20260624/06_bgo_matched_runs/p1/delay_fix/activation_decay_day15_groundstate_fixed_exactpos_bgo_p1_exactpos_m5000_s260613.source`
- manifest: `engineering/background_validation_20260624/06_bgo_matched_runs/p1/delay_fix/bgo_p1_exactpos_m5000_s260613_delayed_source_manifest.json`
- weighted table: `engineering/background_validation_20260624/06_bgo_matched_runs/p1/delay_fix/exactpos_weighted_rpip_table_bgo_p1_exactpos_m5000_s260613.csv`
- geometry: `engineering/background_validation_20260624/04_bgo_variant/geometry_bgo_same_envelope/DEMO2_DR_v3p5_minpatch_centerfinger_bgo_same_envelope_megalib_proxy.geo.setup`
- instant generated: `1190129` / `1190129`
- buildup generated: `1190129` / `1190129`
- fixed day-15 activity: `31.413646 Bq`
- fixed source blocks: `654`
- RPIP lines/keys: `780` / `213`
- eligible RPIP rows: `721`
- PointSource blocks: `5000`
- seed: `260613`
- flux per PointSource: `0.0062827292 Bq`
- flux conservation abs delta: `0 Bq`
- source text flux abs delta: `8.17883e-09 Bq`
- W element activity: `2.8441218 Bq`
- W/collimator-volume activity: `2.8441218 Bq`
- sampling audit: `PASS`
- delayed sim: `engineering/background_validation_20260624/06_bgo_matched_runs/p1/delayed_transport_exactpos/DelayedDecayBgoP1ExactposM5000S260613.inc1.id1.sim.gz`
- SE/ID/TS: `100000/100000/1`
- TE: `3011.07953` s

Boundary:
- bgo_p1_exactpos_m5000_s260613 exact-position delayed source/transport uses matched fix5 buildup production.
- Delayed transport passed only as a transport artifact; delayed rate claims require Step05 detector response, Step06--Step08 propagation, W/collimator checks, and Verifier approval.
