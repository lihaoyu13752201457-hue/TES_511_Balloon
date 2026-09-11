# Source and QA notes

- Audience: technical.
- Delivery mode: portable HTML fallback because no MCP artifact validator/renderer tool is callable in this runtime.
- Production SIM access: forbidden; opened inputs are corrected source spectra and retained small CSV/JSON/PKL artifacts only.
- Requested but unavailable metric: exact >1.022 MeV gamma crossing count/rate/spectrum at TES-nearfield surfaces. Required follow-up: paired lightweight stepping scorer.
- Report sections map the technical specification as follows: title; technical summary; three visual-evidence findings; scope/definitions; methodology; limitations/robustness; recommended next steps; further questions.

## Chart map

1. Source-spectrum finding — bar — energy band vs flux; supports the source-level high-energy boundary, not a nearfield claim. Palette: single blue root.
2. Final delayed lineage — horizontal bar — source volume vs final-rate share; supports directional shielding priority. Palette: single blue root.
3. Shield trade-off — two-series line with 0.75 reference — W thickness vs ideal F3 ratio; supports full-sleeve versus umbrella screening. Palette: blue/orange with dashed neutral target.

## Modeling assumptions

- Full sleeve external source share: 0.782970; coverage factor 0.90.
- Umbrella target source share: 0.711389; view/coverage factor 0.66.
- Main curves set signal survival to 1 and new pair/activation background to zero.
- Diffuse transmission is a Lambert-flux-weighted slab model; normal-incidence transmission is retained in the CSV as a sensitivity reference.
- New-511 cps budgets assume the new component follows the same 20-day temporal normalization only for compact screening; final decisions require explicit mission folding.

## External physics sources

- NIST XCOM: https://physics.nist.gov/PhysRefData/Xcom/html/xcom1.html
- NIST pair thresholds/high-energy notes: https://www.physics.nist.gov/PhysRefData/FFast/Text2000/sec08.html
- Geant4 gamma conversion model: https://geant4.web.cern.ch/documentation/pipelines/master/prm_html/PhysicsReferenceManual/electromagnetic/gamma_incident/gammaconversion/conv.html
