# fix5_fullstat_v2_exactpos_m50000_s260613 Exact-Position Delayed Source

Status: `PASS_FIX5_FULLSTAT_V2_EXACTPOS_M50000_S260613_EXACTPOS_DELAYED_TRANSPORT`.

- source: `runs/step02_delay_fix_fix5_fullstat_v2/activation_decay_day15_groundstate_fixed_exactpos_m50000_s260613.source`
- manifest: `runs/step02_delay_fix_fix5_fullstat_v2/fix5_fullstat_v2_exactpos_m50000_s260613_delayed_source_manifest.json`
- weighted table: `runs/step02_delay_fix_fix5_fullstat_v2/exactpos_weighted_rpip_table_m50000_s260613.csv`
- geometry: `outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- instant generated: `25210216` / `25210216`
- buildup generated: `25210216` / `25210216`
- fixed day-15 activity: `85.449203 Bq`
- fixed source blocks: `9334`
- RPIP lines/keys: `257309` / `1497`
- eligible RPIP rows: `251681`
- PointSource blocks: `50000`
- seed: `260613`
- flux per PointSource: `0.0017089841 Bq`
- flux conservation abs delta: `0 Bq`
- source text flux abs delta: `3.87625e-08 Bq`
- W element activity: `0.98607983 Bq`
- W/collimator-volume activity: `0.98607983 Bq`
- sampling audit: `PASS`
- delayed sim: `runs/step02_delayed_transport_fix5_fullstat_v2_exactpos_m50000_s260613/DelayedDecayFix5FullstatV2ExactposM50000S260613.inc1.id1.sim.gz`
- SE/ID/TS: `1000000/1000000/1`
- TE: `11649.564832` s

Boundary:
- fix5_fullstat_v2_exactpos_m50000_s260613 exact-position delayed source/transport uses matched fix5 buildup production.
- Delayed transport passed only as a transport artifact; delayed rate claims require Step05 detector response, Step06--Step08 propagation, W/collimator checks, and Verifier approval.
