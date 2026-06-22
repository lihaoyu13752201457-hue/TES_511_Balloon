# Prompt-511 Minimum Side-Aperture Candidate

Status: geometry/source-card smoke candidate, not an authority result.

Hypothesis:

- Current prompt-e+ survives because the side-port proxy removes too much surrounding passive/active side-wall material.
- Shrinking only the surrounding side-hole proxy to the physical Be/window half-side restores old-like material continuity while keeping the focused channel open.

Geometry policy:

- target side-hole proxy radius: `1.9 cm`.
- physical side-window half-side retained: `1.898 cm`.
- W sleeve bore is unchanged; no material swap, no ROI/spot cut, no new active material.
- modified side-hole components: `11`.

Outputs:

- geometry setup: `outputs/reports/prompt511_min_side_aperture_20260620/geometry_min_side_aperture/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_min_side_aperture_r1p90.geo.setup`
- source cards: `outputs/reports/prompt511_min_side_aperture_20260620/source_cards_min_side_aperture`
- overlap source: `outputs/reports/prompt511_min_side_aperture_20260620/overlap_min_side_aperture.source`

Required gates before promotion:

- Cosima overlap pass.
- prompt-only e+, n, mu+ smoke with `--disable-isotope-store`.
- activation-only buildup isotope recording from the same geometry if prompt passes.
- no claim of new sensitivity authority until delayed/signal/time-axis closure is rebuilt.
