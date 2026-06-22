# Fix5 1/10 Exact-Position Delayed Source

Status: `PASS_FIX5_1OF10_EXACTPOS_DELAYED_TRANSPORT`.

- source: `runs/step02_delay_fix_fix5_1of10/activation_decay_day15_groundstate_fixed_exactpos.source`
- manifest: `runs/step02_delay_fix_fix5_1of10/fix5_1of10_exactpos_delayed_source_manifest.json`
- weighted table: `runs/step02_delay_fix_fix5_1of10/exactpos_weighted_rpip_table.csv`
- geometry: `outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- instant generated: `1190129` / `1190129`
- buildup generated: `1190129` / `1190129`
- fixed day-15 activity: `75.446536 Bq`
- fixed source blocks: `1541`
- RPIP lines/keys: `3214` / `188`
- eligible RPIP rows: `2874`
- PointSource blocks: `5000`
- seed: `260613`
- flux per PointSource: `0.015089307 Bq`
- flux conservation abs delta: `0 Bq`
- source text flux abs delta: `1.28455e-07 Bq`
- W element activity: `0.92368128 Bq`
- W/collimator-volume activity: `0.92368128 Bq`
- sampling audit: `PASS`
- delayed sim: `runs/step02_delayed_transport_fix5_1of10/DelayedDecayFix5Exactpos.inc1.id1.sim.gz`
- SE/ID/TS: `100000/100000/1`
- TE: `1317.366549` s

Boundary:
- Fix5 1/10 exact-position delayed source/transport uses fix5 1/10 buildup production.
- Delayed transport passed only as a transport artifact; delayed rate claims require Step05 detector response, Step06--Step08 propagation, W/collimator checks, and Verifier approval.
