# geo_opt_s1_bpe_w5_fullstat_v1_exactpos_m50000_s260613 Exact-Position Delayed Source

Status: `PASS_GEO_OPT_S1_BPE_W5_FULLSTAT_V1_EXACTPOS_M50000_S260613_EXACTPOS_DELAYED_TRANSPORT`.

- source: `runs/geometry_optimization_20260704/step02_delay_exactpos_geo_opt_s1_bpe_w5_fullstat_v1/activation_decay_day15_groundstate_fixed_exactpos.source`
- manifest: `runs/geometry_optimization_20260704/step02_delay_exactpos_geo_opt_s1_bpe_w5_fullstat_v1/geo_opt_s1_bpe_w5_fullstat_v1_exactpos_delayed_source_manifest.json`
- weighted table: `runs/geometry_optimization_20260704/step02_delay_exactpos_geo_opt_s1_bpe_w5_fullstat_v1/exactpos_weighted_rpip_table.csv`
- geometry: `engineering/geometry_optimization_20260704/01_geo_opt_s1_bottomw_b4c/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- instant generated: `25210216` / `25210216`
- buildup generated: `25210216` / `25210216`
- fixed day-15 activity: `106.48227 Bq`
- fixed source blocks: `14436`
- RPIP lines/keys: `302644` / `2602`
- eligible RPIP rows: `293753`
- PointSource blocks: `50000`
- seed: `260613`
- flux per PointSource: `0.0021296454 Bq`
- flux conservation abs delta: `0 Bq`
- source text flux abs delta: `1.38147e-07 Bq`
- W element activity: `1.9588238 Bq`
- W/collimator-volume activity: `3.4439668 Bq`
- sampling audit: `PASS`
- delayed sim: `runs/geometry_optimization_20260704/step02_delayed_transport_geo_opt_s1_bpe_w5_fullstat_v1/DelayedDecayGeoOptS1BpeW5FullstatV1.inc1.id1.sim.gz`
- SE/ID/TS: `1000000/1000000/1`
- TE: `9307.684386` s

Boundary:
- geo_opt_s1_bpe_w5_fullstat_v1_exactpos_m50000_s260613 exact-position delayed source/transport uses matched fix5 buildup production.
- Delayed transport passed only as a transport artifact; delayed rate claims require Step05 detector response, Step06--Step08 propagation, W/collimator checks, and Verifier approval.
