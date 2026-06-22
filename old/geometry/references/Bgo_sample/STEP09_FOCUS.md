# Bgo_sample Step09 Focused EventList Transport

Status: `PASS_BGO_SAMPLE_STEP09_FOCUS_TRANSPORT`.

- source: `runs/step09_bgo_sample_focus/Opticsim_laue_f10m_a1_bgo_sample.source`
- geometry: `Bgo_sample/Bgo_sample.geo.setup`
- EventList: `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/eventlists/Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat`
- outfile prefix: `runs/step09_bgo_sample_focus/Opticsim_laue_f10m_a1_bgo_sample`
- triggers: `37194`
- seed: `260615`
- base Step09 status: `PASS_EVENTLIST_BRIDGE_FULL_TRANSPORTED`
- focused sim: `runs/step09_bgo_sample_focus/Opticsim_laue_f10m_a1_bgo_sample.inc1.id1.sim.gz`
- SE/ID/TS: `37194/37194/1`
- TE: `3.7e-05` s

Boundary:
- Focused EventList transport through Bgo_sample geometry passed.
- Step05 detector response must consume this BGO signal SIM together with BGO prompt and delayed SIMs before quoting rates.
