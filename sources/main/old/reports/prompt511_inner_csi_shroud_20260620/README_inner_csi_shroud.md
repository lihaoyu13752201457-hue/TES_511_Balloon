# Prompt-511 Inner Active-CsI Shroud Candidate

Status: geometry/source-card candidate for prompt mechanism testing.

Purpose:

- Restore an old-like active material column in the non-signal side-port solid angle.
- Avoid the large W-only mass/neutron/activation risk of the upper-W-shadow diagnostic.
- Keep the physical side signal port open; no ROI or focal-spot cut is introduced.

Geometry change:

- base setup: `outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- candidate setup: `outputs/reports/prompt511_inner_csi_shroud_20260620/geometry_inner_csi_shroud/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_inner_csi_shroud_r11p6_12p8.geo.setup`
- active CsI shroud: r `11.6..12.8 cm`, z `-13..13.35 cm`.
- open signal port: phi `171..189 deg`, z `-7.2..-3.2 cm`.
- estimated added CsI mass: `10.8485 kg`.

Claim boundary:

- This is not an authority geometry, delayed-source result, Step06/07/08 result, or final sensitivity.
- Added active CsI has native `.det` entries, but prompt suppression must be demonstrated by MC.
- Activation/isotope recording is required if prompt e+/n/mu gates pass.
