# Bgo_sample Step02 Fullstat v2 Exact-Position Delayed Source

Status: `PASS_BGO_SAMPLE_FULLSTAT_V2_EXACTPOS_DELAYED_TRANSPORT`.

- source: `runs/step02_bgo_sample_fullstat_v2_exactpos_delay_source/activation_decay_day15_groundstate_fixed_exactpos.source`
- manifest: `runs/step02_bgo_sample_fullstat_v2_exactpos_delay_source/bgo_sample_fullstat_v2_exactpos_manifest.json`
- weighted table: `runs/step02_bgo_sample_fullstat_v2_exactpos_delay_source/exactpos_weighted_rpip_table.csv`
- geometry: `Bgo_sample/Bgo_sample.geo.setup`
- instant generated: `25210216` / `25210216`
- buildup generated: `25210216` / `25210216`
- fixed day-15 activity: `23.570474 Bq`
- fixed source blocks: `8412`
- RPIP lines/keys: `54979` / `1633`
- eligible RPIP rows: `43043`
- PointSource blocks: `5000`
- seed: `260613`
- flux per PointSource: `0.0047140948 Bq`
- flux conservation abs delta: `0 Bq`
- sampling audit: `PASS`
- delayed sim: `runs/step02_bgo_sample_fullstat_v2_exactpos_delayed_transport/DelayedDecayBgoSampleFullstatV2Exactpos.inc1.id1.sim.gz`
- SE/ID/TS: `1000000/1000000/1`
- TE: `39653.861364` s

Boundary:
- Bgo_sample fullstat_v2 exact-position delayed source/transport uses full-stat prompt/buildup production.
- Delayed transport passed as the Step02/03 authority for this branch.
- Supersession note: downstream Step05 detector response, Step06--Step08 mission-time significance, and the BGO-vs-CsI exact-position material-control comparison have since passed for this same bgo_sample_fullstat_v2_exactpos label. Quote BGO sensitivity from the Step08/comparison reports, not from this transport-only note.
