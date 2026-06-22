# Bgo_sample Step02 1of10 Exact-Position Delayed Source

Status: `PASS_BGO_SAMPLE_1OF10_EXACTPOS_DELAYED_TRANSPORT`.

- source: `runs/step02_bgo_sample_1of10_exactpos_delay_source/activation_decay_day15_groundstate_fixed_exactpos.source`
- manifest: `runs/step02_bgo_sample_1of10_exactpos_delay_source/bgo_sample_1of10_exactpos_manifest.json`
- geometry: `Bgo_sample/Bgo_sample.geo.setup`
- instant generated: `1190129` / `1190129`
- buildup generated: `1190129` / `1190129`
- fixed day-15 activity: `24.791139 Bq`
- fixed source blocks: `489`
- RPIP lines/keys: `662` / `185`
- PointSource blocks: `568`
- flux conservation abs delta: `4.32448e-09 Bq`
- delayed sim: `runs/step02_bgo_sample_1of10_exactpos_delayed_transport/DelayedDecayBgoSample1of10Exactpos.inc1.id1.sim.gz`
- SE/ID/TS: `100000/100000/1`
- TE: `3730.929734` s

Boundary:
- Bgo_sample 1of10 exact-position delayed source/transport uses low-stat prompt/buildup production, not full-stat production.
- Activity is day-15 ground-state-fixed and conserved over true RPIP PointSource blocks.
- Delayed transport passed for this low-stat sample.
- Supersession note: full-stat v2 exact-position BGO delayed transport, Step05 detector response, Step06--Step08 mission-time significance, and the BGO-vs-CsI exact-position material-control comparison have since passed for the production bgo_sample_fullstat_v2_exactpos label. This file remains only the low-stat exact-position provenance record.
