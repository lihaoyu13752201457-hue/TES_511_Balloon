# Prompt-511 Upper CsI Wall Smoke

Status: geometry/source-card candidate for prompt mechanism testing.

Purpose:

- Test the old-like upper side-wall material-column route without the repack inner collar.
- Intercept incoming side/top-side e+ before they reach the OVC upper side wall, where current selected prompt events cluster.
- Keep the side signal port unchanged; the added CsI starts above the present outer top annulus.

Geometry change:

- base setup: `outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- candidate setup: `outputs/reports/prompt511_upper_csi_wall_20260620/geometry_upper_csi_wall/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_upper_csi_wall_z5p55_13p35.geo.setup`
- added active CsI envelope: r `13.6..18 cm`, z `5.55..13.35 cm`, full 360 deg in 8 segments.
- estimated added CsI mass: `15.366 kg`.

Claim boundary:

- This is not an authority geometry, delayed-source result, Step06/07/08 result, or final sensitivity.
- The active-veto behavior is currently tested through added low-threshold `.det` sensitive-volume entries plus the Step05-like proxy volume-name matcher; authority trigger wiring still needs a separate implementation if this route survives.
- Added CsI mass may create activation risk; activation/isotope smoke is required before promotion.
