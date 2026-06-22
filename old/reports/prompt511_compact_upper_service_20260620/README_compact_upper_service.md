# Prompt-511 Compact Upper-Service Candidate

Status: geometry/source-card smoke candidate, not an authority result.

Hypothesis:

- Current prompt-e+ is partly driven by exposed non-active upper OVC/service material outside the old-like active shield topology.
- Removing or truncating that upper source zone should reduce prompt without adding high-activation W/CsI mass.

Geometry policy:

- z cap for upper service source zone: `5.2 cm`.
- Preserve side-window axis, side-hole radii, window foils, and W sleeve bore.
- Do not add new active material and do not use ROI/spot cuts.
- removed original mass estimate from fully removed components: `7.0038 kg`.

Outputs:

- geometry setup: `outputs/reports/prompt511_compact_upper_service_20260620/geometry_compact_upper_service/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_compact_upper_service_zcap5p2.geo.setup`
- source cards: `outputs/reports/prompt511_compact_upper_service_20260620/source_cards_compact_upper_service`
- overlap source: `outputs/reports/prompt511_compact_upper_service_20260620/overlap_compact_upper_service.source`

Required gates before promotion:

- Cosima overlap pass.
- prompt-only e+, n, mu+ smoke with `--disable-isotope-store`.
- activation-only buildup isotope recording from the same geometry.
- no claim of new sensitivity authority until delayed/signal/time-axis closure is rebuilt.
