# Prompt-511 Upper W Shadow Candidate

Status: geometry/source-card candidate for prompt mechanism testing.

Purpose:

- Test whether the VariantB failure is primarily finite-z coverage of the upper OVC/service leakage paths.
- Keep the current side signal-port aperture open; do not use ROI or focal-spot cuts.
- Treat this as a diagnostic candidate because added W mass can raise neutron prompt and activation.

Geometry change:

- candidate setup: `outputs/reports/prompt511_upper_w_shadow_20260620/geometry_upper_w_shadow/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_upper_w_shadow_r12p35_12p8.geo.setup`
- W radial envelope: `12.35..12.8 cm`.
- lower non-port/port-fill range: z `-13..1 cm`, with signal gap phi `171..189` and z `-7.2..-3.2` left open.
- upper notched range: z `1.05..28 cm`, phi `5..355`; the small +x notch avoids the DR pump-line proxy.
- estimated added W mass: `27.4494 kg`.

Selected-current-event ray proxy:

- caught selected events: `77/80`.
- caught selected rate: `0.0523001 cps`.
- missed selected rate: `0.00203767 cps`.
- path-length proxy residual estimates: `{"0.0918": {"mu_rho_cm2_g": 0.0918, "normal_incidence_511_transmission": 0.45055145090899174, "path_weighted_residual_estimate_s-1": 0.02083235888356931}, "0.137": {"mu_rho_cm2_g": 0.137, "normal_incidence_511_transmission": 0.30426842201728027, "path_weighted_residual_estimate_s-1": 0.013656078554988113}}`.

Claim boundary:

- This is not a total-background or sensitivity result.
- The ray proxy ignores new W self-emission, Compton refill, neutron/muon prompt, delayed activation, and signal transport.
- A prompt-only e+ smoke is required before spending n/mu and isotope-record budget.
