# Prompt-511 Active-CsI Collar Focused EventList Smoke

Status: `PASS_PROMPT511_ACTIVE_CSI_COLLAR_FOCUS_SMOKE`.

- source: `outputs/reports/prompt511_active_csi_collar_20260620/runs/active_csi_collar_focus_smoke/Opticsim_laue_f10m_a1_prompt511_active_csi_collar.source`
- geometry: `outputs/reports/prompt511_active_csi_collar_20260620/geometry_active_csi_collar/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_active_csi_collar_r4p25_5p95.geo.setup`
- EventList: `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/eventlists/Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat`
- outfile prefix: `outputs/reports/prompt511_active_csi_collar_20260620/runs/active_csi_collar_focus_smoke/Opticsim_laue_f10m_a1_prompt511_active_csi_collar`
- triggers: `37194`
- seed: `260620`
- base Step09 status: `PASS_EVENTLIST_BRIDGE_FULL_TRANSPORTED`
- focused sim: `outputs/reports/prompt511_active_csi_collar_20260620/runs/active_csi_collar_focus_smoke/Opticsim_laue_f10m_a1_prompt511_active_csi_collar.inc1.id1.sim.gz`
- SE/ID/TS: `37194/37194/1`
- TE: `3.7e-05` s

Step05-like focused-signal proxy:

| case | generated | TES kept | W2 raw | active pass | side-Compton/FoV pass |
|---|---:|---:|---:|---:|---:|
| current_baseline | 37194 | 35707 | 30234 | 30234 | 29597 |
| active_csi_collar | 37194 | 35761 | 30303 | 30303 | 29706 |

- active/current W2 raw event ratio: `1.00228`.
- active/current active-veto-pass ratio: `1.00228`.
- active/current side-Compton/FoV-pass ratio: `1.00368`.

Boundary:
- Focused EventList transport through active-CsI-collar geometry passed.
- The signal-retention proxy uses the same W2 line window, 50 keV active-veto threshold, and side-Compton/FoV function as the prompt diagnostics.
- This is not a Step05/06/07/08 authority because prompt, delayed, and signal are not rebuilt together on a common chain.
