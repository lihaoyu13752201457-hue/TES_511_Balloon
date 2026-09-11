# Step09 Optics EventList Bridge

Status: `PASS_EVENTLIST_BRIDGE_FULL_TRANSPORTED`.

The retained bridge is:

- summary: `outputs_f10m_a1_v3p5/step09_optics_bridge_summary.json`
- EventList: `outputs_f10m_a1_v3p5/eventlists/Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat`
- full source: `outputs_f10m_a1_v3p5/run_configs/Opticsim_laue_f10m_a1_v3p5_centerfinger.source`
- smoke source: `outputs_f10m_a1_v3p5/run_configs/Opticsim_laue_f10m_a1_v3p5_centerfinger_smoke1000.source`
- detector-coupled response: `outputs_f10m_a1_v3p5/detector_coupled_focus_response.json`

This bridge provides the f10m A1 focused EventList and side-entry disk geometry
used by the current Mass_model_511 and geo-opt detector-response wrappers. It
does not add optics hardware mass activation.
