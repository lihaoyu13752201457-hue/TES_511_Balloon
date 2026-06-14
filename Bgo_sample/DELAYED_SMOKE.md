# Bgo_sample Delayed-Source Smoke

Status: `PASS_BGO_SAMPLE_DELAYED_TRANSPORT_SMOKE`.

- source: `runs/step02_bgo_sample_delay_smoke/activation_decay_probe.source`
- manifest: `runs/step02_bgo_sample_delay_smoke/bgo_delayed_smoke_manifest.json`
- probe run: `runs/step02_bgo_sample_activation_probe_buildup_pn50k`
- PointSource blocks: `30`
- triggers requested: `200`
- proxy flux sum: `32.861551 Bq`
- DAT RP count: `30.0`
- RPIP points: `30`
- delayed sim: `runs/step02_bgo_sample_delayed_transport_smoke/DelayedDecayBgoProbe.inc1.id1.sim.gz`
- SE/ID/TS: `200/200/1`
- TE: `5.664515` s

Boundary:
- This is a BGO delayed-source and delayed-transport smoke only.
- The activation probe is p,n only at 50k gamma-equivalent statistics and does not define a BGO background rate.
- A later low-stat `1of10` exact-position day-15 delayed-source/transport closure is recorded in `STEP02_1OF10_EXACTPOS.md`; this note remains only the p,n activation-probe smoke record.
- Full-stat production day-15 BGO delayed-source/rate transport remains not run.
- Step05 response, Step06--Step08 significance, and BGO-vs-CsI comparison remain not run.
