# Literature Notes

These notes summarize the local guidance files read on 2026-05-17.

- 511-CAM uses channel optics ray tracing plus MEGAlib/Geant4 detector
  simulation rather than a public full Geant4 channel-optics boundary process.
- The 511-CAM channel benchmark parameters are 12 m focal length, four rings
  at 2.25/3.0/3.75/4.5 cm, W/Si 30/150 nm multilayers, about 3.5-3.6 cm
  focused beam diameter, about 80% transmissivity, and about 50.89 cm2
  effective area.
- Laue lens work can be implemented in Geant4 as a custom process following
  the Barhoum-style `GetMeanFreePath`/`PostStepDoIt` pattern, then upgraded
  with Bragg/Darwin/XOP-derived tables.
- Geant4 `G4XrayReflection` is useful as a software pattern for boundary
  reflection, but its default data/model are not a direct 511 keV W/Si
  multilayer solution.
- Rechecked public literature pages during the 2026-05-17/18 geometry push:
  the 511-CAM arXiv page identifies 511-CAM as a 511 keV focusing optics plus
  TES microcalorimeter concept with 390 eV-class detector resolution, and the
  OSTI/JATIS page for the soft gamma-ray concentrator explicitly describes the
  modeling chain as IMD multilayer optical properties + IDL ray tracing +
  MEGAlib focal-plane detector simulation. The Geant4 11.4 Physics Reference
  Manual page for `G4XrayReflection` keeps it in the X-ray range and notes that
  multilayer cases should use user-provided models. These checks support the
  current project boundary: custom table-driven boundary physics is required
  for 511 keV W/Si channel optics.
- Downloaded the OSTI accepted manuscript for Shirazi et al. 2020 from
  `https://www.osti.gov/servlets/purl/1716823` and extracted the text locally
  for geometry clues. The paper's ray-tracing section says the number of
  reflections for a parallel beam varies from 17 to 38 depending on ring length
  and radius. This is not the 511-CAM four-ring configuration, but it is the
  same Shirazi/Bloser channel-optics lineage and strongly supports the current
  conclusion that a 1-3 bounce effective bookkeeping model cannot be promoted
  directly to final wall-by-wall Geant4 geometry.
- Added `analysis/reconcile_channel_bounce_path.py` to keep that literature
  clue in the diagnostic record without overusing it as a direct 511-CAM input.
  The script compares 1-3 effective bounces, the 6-13 calibrated-theta estimate,
  and the 17-38 lineage bracket, then writes a CSV/summary/plot for review.
