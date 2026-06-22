# Prompt-511 Active-CsI Collar Candidate

This is a local prompt-511 geometry candidate, not a rate authority.
It reuses the prompt511 repack local collar envelope and replaces
the W liner with active CsI collar volumes.

- setup: `outputs/reports/prompt511_active_csi_collar_20260620/geometry_active_csi_collar/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_active_csi_collar_r4p25_5p95.geo.setup`
- source cards: `outputs/reports/prompt511_active_csi_collar_20260620/source_cards_active_csi_collar`
- collar mass: `2.64163 kg`
- collar r: `[4.25, 5.95]` cm
- z segments: `[[-8.75, -0.65], [0.65, 4.65]]` cm
- signal gap: `[160.0, 200.0]` deg

Boundaries:

- no ROI/source-spot restriction is used;
- prompt-only L1 proxy must pass before n/mu/isotope budget;
- isotope smoke, if run, is not a delayed-rate authority.
