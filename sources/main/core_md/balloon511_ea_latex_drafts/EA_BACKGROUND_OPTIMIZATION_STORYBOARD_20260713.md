# EA background-and-optimization storyboard (2026-07-13)

## Purpose

This note fixes the narrative and figure contracts for the English and Chinese
manuscripts before prose is rewritten.  The public paper describes one final
optimized geometry (the internally retained S3d configuration).  It does not
present the internal geometry sequence, a mass-reduction exercise, or a gate-by-
gate experiment log.

## Papers read before the rewrite

1. Gallego et al., *A Complete Background Model for the COSI Balloon-Borne
   Gamma-Ray Telescope* (2025), arXiv:2503.02493 and ApJ 988, 156.
   <https://arxiv.org/abs/2503.02493>
2. Kierans et al., *The 2016 Super Pressure Balloon Flight of the Compton
   Spectrometer and Imager* (2017), arXiv:1701.05558.
   <https://arxiv.org/abs/1701.05558>
3. Tian et al., *Simulation of non-X-ray background for the DIffuse X-ray
   Explorer (DIXE) mission* (2026), arXiv:2604.13569.
   <https://arxiv.org/abs/2604.13569>
4. Representative *Experimental Astronomy* instrument simulation paper:
   *Simulation study of a compact gamma-ray burst monitor based on a LaBr3(Ce)
   and SiPM array* (2021).
   <https://link.springer.com/article/10.1007/s10686-021-09779-9>

The shared pattern is: show the transported mass model first; identify which
particle, material, or direction produces the useful-band background; connect
that evidence to an instrument choice; then show the final response or mission
performance.  Caveats belong in one compact boundary paragraph after the main
result, not in every result paragraph.

## One-sentence paper story

An end-to-end, detector-coupled simulation shows that the narrow 511 keV
background is set mainly by side-entering prompt positrons/neutrons and by
copper activation near the TES, which motivates a directionally graded BGO
shield and, after the stated 420 eV FWHM pixel response, leads to a final
selected background of \(5.8495\times10^{-3}\ \mathrm{s^{-1}}\) and a central
20-day counting significance of 18.56 for the reference source.

## Figure contracts

### Figure 1 — the geometry that was actually transported

- Question: what detector/cryostat geometry receives the signal and background?
- Source: generated Mass_model_511 semantic OBJ/MTL, not a hand-drawn legacy
  schematic.
- Panels: full instrument view and detector-bay cutaway/detail.
- Required visual elements: TES location, cold structures, cryostat shields,
  active shield, side window/collimator, and side-entry 511 keV path.

### Background-origin figure — what reaches the science window?

- Left: selected reference rates by particle family.  Positrons and neutrons
  contribute 88.91% of the total selected background (96.94% of prompt).
- Right: selected delayed records by isotope: 25 Cu-64, 2 Cu-61, and 1 Cu-62;
  all are produced in cold copper structures.
- Reader takeaway: the line-window background has a prompt directional problem
  and a local copper-activation problem.

### Optimized-shield figure — how did that map shape the final geometry?

- Left: final directionally graded BGO geometry: 40 mm side, 30 mm bottom,
  10 mm top annulus, retained side aperture and 3 mm aluminium/Kapton shell,
  with no external tungsten layer.
- Right: response-convolved final selected background: prompt
  \(3.3930\times10^{-3}\ \mathrm{s^{-1}}\) (58.01%), atmospheric 511 keV
  photons \(1.5553\times10^{-3}\ \mathrm{s^{-1}}\) (26.59%), and delayed
  activation \(9.0123\times10^{-4}\ \mathrm{s^{-1}}\) (15.41%).
- Reader takeaway: strong side coverage addresses the measured entry pattern;
  thinner end coverage preserves the open optical path and completes the
  detector-scale background design.

### Mission-performance figure — what does the final design deliver?

- Plot central and finite-Monte-Carlo conservative cumulative counting
  significance versus elapsed flight time for the reference
  \(10^{-4}\ \mathrm{ph\,cm^{-2}\,s^{-1}}\) source.
- Mark 3 sigma and 5 sigma; report 20-day values 18.56 and 6.50.
- Reader takeaway: the final geometry reaches 5 sigma in 1.11 days centrally;
  the finite-count conservative curve reaches it in 11.53 days.

## Section logic

1. **Geometry and detector response.**  Describe the generated Mass_model_511
   and the final graded shield in physical language.
2. **Simulation and statistics.**  Explain the pixel-level 420 eV FWHM energy
   response, common energy window, active veto, topology selection, rate
   normalization, exact count intervals, response-seed audit, and trajectory
   fold in the order an event experiences them.
3. **Where the background comes from.**  Present particle and material origins
   before discussing optimization.
4. **Final optimized geometry.**  State the evidence-to-design connection and
   give one final-geometry table; do not narrate internal variants.
5. **Full-chain result.**  Give the cut flow, final component budget, and
   finite-count precision.
6. **Mission performance.**  Present the central and conservative time curves.
7. **Discussion and conclusion.**  Lead with the physical lesson and achieved
   performance.  Put model boundaries in one short paragraph and future work in
   one short paragraph.

## Numerical authorities

- Actual baseline geometry:
  `outputs/reports/Mass_model_511_stage_diam_300_300_300_350_350_400_20260701/`
- Final geometry manifest:
  `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/data/s3d_o8_geometry_manifest.json`
- Final response-convolved day-15 rates, exact finite-count bounds, 64-seed
  response audit, and 20-day trajectory statistics:
  `engineering/ea_detector_response_closure_20260713/data/o8_energy_response_closure_summary.json`
- Response-convolved mission timeline:
  `engineering/ea_detector_response_closure_20260713/outputs/w2_energy_response_timeline.csv`
- The retained S3d Step05/Step08 products remain the response-off reproduction
  authorities checked by the closure package; they are not the headline paper
  values after the stated TES energy response is applied.
