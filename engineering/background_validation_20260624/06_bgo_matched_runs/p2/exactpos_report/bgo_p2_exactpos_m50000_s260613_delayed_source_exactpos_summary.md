# bgo_p2_exactpos_m50000_s260613 Exact-Position Delayed Source

Status: `PASS_BGO_P2_EXACTPOS_M50000_S260613_EXACTPOS_DELAYED_TRANSPORT`.

- source: `engineering/background_validation_20260624/06_bgo_matched_runs/p2/delay_fix/activation_decay_day15_groundstate_fixed_exactpos_bgo_p2_exactpos_m50000_s260613.source`
- manifest: `engineering/background_validation_20260624/06_bgo_matched_runs/p2/delay_fix/bgo_p2_exactpos_m50000_s260613_delayed_source_manifest.json`
- weighted table: `engineering/background_validation_20260624/06_bgo_matched_runs/p2/delay_fix/exactpos_weighted_rpip_table_bgo_p2_exactpos_m50000_s260613.csv`
- geometry: `engineering/background_validation_20260624/04_bgo_variant/geometry_bgo_same_envelope/DEMO2_DR_v3p5_minpatch_centerfinger_bgo_same_envelope_megalib_proxy.geo.setup`
- instant generated: `25210216` / `25210216`
- buildup generated: `25210216` / `25210216`
- fixed day-15 activity: `29.18519 Bq`
- fixed source blocks: `13231`
- RPIP lines/keys: `58811` / `1969`
- eligible RPIP rows: `54740`
- PointSource blocks: `50000`
- seed: `260613`
- flux per PointSource: `0.00058370379 Bq`
- flux conservation abs delta: `0 Bq`
- source text flux abs delta: `7.29012e-09 Bq`
- W element activity: `2.1733368 Bq`
- W/collimator-volume activity: `2.1875322 Bq`
- sampling audit: `PASS`
- delayed sim: `engineering/background_validation_20260624/06_bgo_matched_runs/p2/delayed_transport_exactpos/DelayedDecayBgoP2ExactposM50000S260613.inc1.id1.sim.gz`
- SE/ID/TS: `1000000/1000000/1`
- TE: `32318.644709` s

Boundary:
- bgo_p2_exactpos_m50000_s260613 exact-position delayed source/transport uses matched fix5 buildup production.
- Delayed transport passed only as a transport artifact; delayed rate claims require Step05 detector response, Step06--Step08 propagation, W/collimator checks, and Verifier approval.
