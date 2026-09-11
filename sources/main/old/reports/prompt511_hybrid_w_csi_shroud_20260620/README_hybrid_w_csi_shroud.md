# Prompt-511 Hybrid Thin-W + Active-CsI Shroud Candidate

Status: geometry/source-card candidate for prompt mechanism testing.

Purpose:

- Use a thin inner W shadow only through the upper-z leakage region that VariantB missed.
- Add old-like active CsI above the current top annulus for veto/material continuity.
- Keep the physical side signal port open; no ROI or focal-spot cut is introduced.

Geometry change:

- base setup: `outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- candidate setup: `outputs/reports/prompt511_hybrid_w_csi_shroud_20260620/geometry_hybrid_w_csi_shroud/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_hybrid_w_csi_shroud.geo.setup`
- thin W: r `12.35..12.8 cm`, z `-13..13.35 cm`, with true side signal gap open.
- active CsI upper shroud: r `13.6..18 cm`, z `5.55..15.35 cm`, 8 native sensitive segments.
- estimated added W mass: `17.6757 kg`; CsI mass: `19.306 kg`; total: `36.9816 kg`.

Claim boundary:

- This is not an authority geometry, delayed-source result, Step06/07/08 result, or final sensitivity.
- Prompt-only e+ must pass before n/mu/isotope budget is spent.
- Added W and CsI activation must be inspected separately if prompt gates pass.
