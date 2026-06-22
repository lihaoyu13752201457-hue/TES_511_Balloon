# fix5 Step09 Focused EventList Transport

Status: `PASS_FIX5_STEP09_FOCUS_TRANSPORT`.

- source: `runs/step09_focus_fix5_fullstat_v2_exactpos_m50000_s260613/Opticsim_laue_f10m_a1_fix5_fullstat_v2_exactpos_m50000_s260613.source`
- geometry: `outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- EventList: `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/eventlists/Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat`
- outfile prefix: `runs/step09_focus_fix5_fullstat_v2_exactpos_m50000_s260613/Opticsim_laue_f10m_a1_fix5_fullstat_v2_exactpos_m50000_s260613`
- triggers: `37194`
- seed: `260616`
- base Step09 status: `PASS_EVENTLIST_BRIDGE_FULL_TRANSPORTED`
- focused sim: `runs/step09_focus_fix5_fullstat_v2_exactpos_m50000_s260613/Opticsim_laue_f10m_a1_fix5_fullstat_v2_exactpos_m50000_s260613.inc1.id1.sim.gz`
- SE/ID/TS: `37194/37194/1`
- TE: `3.7e-05` s
- SIM geometry: `  /home/ubuntu/TES_511_Balloon/outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`

Boundary:
- Focused EventList transport through fix5 geometry passed.
- Step05 detector response must consume this fix5 signal SIM together with fix5 prompt and delayed SIMs before quoting signal keep or sensitivity.
