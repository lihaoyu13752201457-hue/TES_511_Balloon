# BGO Same-Envelope Step09 Focused EventList Transport

Status: `PASS_BGO_ENGINEERING_STEP09_FOCUS_TRANSPORT`.

- source: `engineering/background_validation_20260624/06_bgo_matched_runs/p2/step09_focus/run/Opticsim_laue_f10m_a1_bgo_same_envelope_p2_focus.source`
- geometry: `engineering/background_validation_20260624/04_bgo_variant/geometry_bgo_same_envelope/DEMO2_DR_v3p5_minpatch_centerfinger_bgo_same_envelope_megalib_proxy.geo.setup`
- EventList: `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/eventlists/Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat`
- outfile prefix: `engineering/background_validation_20260624/06_bgo_matched_runs/p2/step09_focus/run/Opticsim_laue_f10m_a1_bgo_same_envelope_p2_focus`
- triggers: `37194`
- seed: `260617`
- base Step09 status: `PASS_EVENTLIST_BRIDGE_FULL_TRANSPORTED`
- focused sim: `engineering/background_validation_20260624/06_bgo_matched_runs/p2/step09_focus/run/Opticsim_laue_f10m_a1_bgo_same_envelope_p2_focus.inc1.id1.sim.gz`
- SE/ID/TS: `37194/37194/1`
- TE: `3.7e-05` s
- SIM geometry: `  /home/ubuntu/TES_511_Balloon/engineering/background_validation_20260624/04_bgo_variant/geometry_bgo_same_envelope/DEMO2_DR_v3p5_minpatch_centerfinger_bgo_same_envelope_megalib_proxy.geo.setup`

Boundary:
- Focused EventList transport through BGO same-envelope geometry passed.
- Step05 detector response must consume this BGO signal SIM together with BGO prompt and delayed SIMs before quoting signal keep or sensitivity.
