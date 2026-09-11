# Prompt 511 Spatial ROI Smoke Constraints

Status: `PROMPT511_SPATIAL_ROI_DIAGNOSTIC_ONLY_WITHDRAWN_AS_STRATEGY`.

This directory records a detector-coordinate spatial ROI diagnostic around the
focused 511 keV spot. After the prompt-entry audit comparing old `new_geo_re`
and current v3p5, this is no longer a recommended prompt-suppression strategy:
old `new_geo_re` had lower hard-window prompt because the corresponding side
region was a solid shield/material column and because the source-surface
normalization differed, not because it used an ROI.

Rules:

- Current hard-window rate authority remains
  `fullstat_v2_exactpos_m50000_s260613`.
- This smoke does not change geometry, source cards, Step02 transport, Step05
  parsing, or manuscript headline authority.
- Prompt spatial leakage is evaluated from the existing detector-coupled W2
  spatial cut table:
  `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/detector_coupled_spatial_line_cuts.csv`.
- Current prompt/delayed/signal normalization is anchored to the M=50000
  exact-position Step05/06/08 products.
- Prompt rates are scaled from the spatial table to the current Step05 prompt
  hard-window rate. Delayed rates are scaled by radial fraction from the same
  spatial table to the current exact-position delayed hard-window rate.
- Signal rates use the detector-coupled spatial table directly and are reported
  both relative to the current hard-window W2 signal and relative to the
  spatial-table full-aperture signal.
- Any annular-likelihood result is a fixed-template sidecar only; it is not a
  nuisance-profile publication analysis.
- The conclusion may not identify ROI as the prompt-suppression route. The
  prompt fix direction is local side-port/side-wall hardware geometry closure,
  with ROI retained only as a diagnostic or future analysis cross-check.
