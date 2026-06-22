# Prompt-511 passive shadow-shell smoke audit (2026-06-17)

Scope: check whether the Claude-proposed areal W shadow shell can be turned into
a minimal, non-authority geometry change that is both overlap-clean and strong
enough to significantly reduce prompt-eplus 511 background.

## Inputs

- Base geometry: `outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- Source template: `config/megalib_sources_fullsphere20_v3p5_centerfinger_tilt45/Background_eplus_fullsphere20.source`
- Builder: `outputs/reports/prompt511_entry_audit_20260617/build_prompt511_shadow_smoke.py`
- Manifest: `outputs/reports/prompt511_shadow_smoke_20260617/prompt511_shadow_smoke_manifest.json`
- Analytic screen basis: the 80 selected prompt-eplus records in
  `outputs/reports/prompt511_entry_audit_20260617/current_eplus_prompt_final_records.json`

## Candidates Checked

### 1. Broad outer-gap shell, initial naive trial

- Geometry: `w_shadow_gap_r8p34_8p48`, W shell `r=[8.34,8.48] cm`, `z=[-12,6] cm`,
  open signal sector `phi=[160,200] deg`.
- Analytic upper bound: residual `0.043678 cps`, suppression `1.244x`.
- Overlap result: invalid. It overlaps existing cold shield bottom caps:
  - `Still_Shield_Al_side_window_bottom_cap`, at least `379.261 um`
  - `Shield_4K_Al_side_window_bottom_cap`, at least `152.742 um`

Conclusion: even a thin outer shell cannot be a continuous long cylinder; it must
be z-segmented around existing caps/plates.

### 2. CAD-safer outer-gap shell

- Geometry: `w_shadow_gap_safe_r8p39_8p48_zm10p3_z5p3`, W shell `r=[8.39,8.48] cm`,
  `z=[-10.3,5.3] cm`, open signal sector `phi=[160,200] deg`.
- Reason for dimensions: inner radius is moved outside the local 50 mK can corner,
  and z is trimmed to avoid the Still/4K bottom caps and the support-ring planes.
- Overlap result: clean except the expected no-trigger warning in the overlap
  source. No `GeomVol1002` overlap was reported.
- Analytic upper bound from the 80 selected prompt-eplus records:
  - baseline: `0.054338 cps`
  - residual: `0.047401 cps`
  - fraction: `0.872`
  - suppression: `1.146x`
  - events intersecting the liner: `58/80`

Conclusion: this is the kind of shell that can plausibly fit without CAD surgery,
but it is too thin/too far out to be a significant prompt-background fix.

### 3. More aggressive trimmed shell

- Geometry: `w_shadow_mid_r7p85_8p48_zm10p3_z5p3`, W shell `r=[7.85,8.48] cm`,
  `z=[-10.3,5.3] cm`, open signal sector `phi=[160,200] deg`.
- Analytic upper bound:
  - residual: `0.024522 cps`
  - fraction: `0.451`
  - suppression: `2.216x`
  - events intersecting the liner: `60/80`
- Overlap result: invalid. It overlaps the local 50 mK can:
  - `Al_50mK_Local_Can_side_entry_YP_panel`, at least `304.963 um`
  - `Al_50mK_Local_Can_side_entry_YM_panel`, at least `148.043 um`

Conclusion: moving the W shell inward makes it useful, but it immediately becomes
a CAD redesign problem. The stronger Claude-style `r~4-7 cm` liner is therefore
not a minimal patch to the current geometry.

## Decision

Adding "a passive shielding shell" is not sufficient as stated.

The useful passive shield is not a generic shell; it must be a near-detector,
areal high-Z shadow liner that covers most non-signal azimuth while leaving the
signal sector open. In the current geometry, the version that fits without
overlap gives only about `1.15x` analytic suppression before W add-back and
activation are included. The versions that begin to matter overlap existing
50 mK can/support geometry and require CAD changes.

I did not run a low-stat prompt-eplus transport for the CAD-safe shell, because
the analytic result is already an upper bound and only predicts a `13%` residual
reduction. A `200k` eplus MC would have too few final W2 events to distinguish
that from Poisson scatter, and W self-emission can only reduce the net benefit.

Practical path:

1. Keep the existing `spot_r90`/spatial selection as the main no-hardware
   prompt suppressor.
2. If hardware is needed, redesign the local 50 mK can/support region to reserve
   a real high-Z shadow volume, then rerun full prompt MC plus W delayed
   activation. Treat the current `~5x` Claude number as a geometry-screen upper
   bound, not an implemented design result.
