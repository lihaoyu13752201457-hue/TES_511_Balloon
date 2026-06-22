# Prompt-511 Collimator Switch Smoke Constraints (2026-06-18)

Purpose: test whether the current `new_geo_re` / v3p5 side-entry W aperture
sleeve-collimator is the decisive prompt-eplus suppressor.

## Authority Boundaries

- Current rate authority remains `fullstat_v2_exactpos_m50000_s260613`.
- This directory is a diagnostic smoke branch only.
- Do not edit the authority geometry under
  `outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/`.
- Do not quote smoke rates as paper sensitivity.

## Switch Definition

- Baseline: current v3p5 geometry.
- Collimator-off variant: copy the current v3p5 MEGAlib proxy geometry and
  change only these four volume materials to `Vacuum`:
  - `W_Side_Aperture_Sleeve_collimator_ZP_panel`
  - `W_Side_Aperture_Sleeve_collimator_ZM_panel`
  - `W_Side_Aperture_Sleeve_collimator_YP_panel`
  - `W_Side_Aperture_Sleeve_collimator_YM_panel`
- Keep all shapes, positions, source cards, far-field radius, and detector
  definitions otherwise unchanged.

## Required Comparison

- Use prompt eplus only.
- Compare raw TES line-window events using
  `510.58 <= TES_total_keV < 511.42`.
- Do not apply active veto, Compton/FoV, spatial, Step06, Step07, or Step08.
- Use the same direct parser convention as the prompt-511 repack smoke.

## Interpretation Rule

- If collimator-off changes the eplus raw TES 511-keV rate by only counting
  noise, the W sleeve is not the decisive suppressor.
- If collimator-off strongly increases the rate, then the side sleeve is a
  decisive blocker and needs a dedicated collimator optimization smoke.
