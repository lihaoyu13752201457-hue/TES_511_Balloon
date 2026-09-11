# B-FULL Single-Tile XOP Scan

- ok: `True`
- executable: `/tmp/opticsim-bfull-build/laue_multiring_bfull_demo`
- ring/tile: `2/0`
- events per offset: `5000`
- all runs registered in Geant4 EM category: `True`
- all runs use G4VEmProcess base: `True`
- transmitted_space rows match summary: `True`
- max |recorded p_reflect - XOP|: `6.75896075219562e-11`
- observed peak/min interaction ratio: `None`

| offset arcsec | delta urad | XOP R | observed frac | recorded p_reflect | max p delta | interactions |
|---:|---:|---:|---:|---:|---:|---:|
| -90 | -435.661 | 1.22945e-11 | 0 |  |  | 0 |
| -60 | -290.217 | 9.18779e-06 | 0 |  |  | 0 |
| -30 | -144.773 | 0.0308358 | 0.0234 | 0.0308358 | 6.75896e-11 | 117 |
| -18 | -86.5955 | 0.142154 | 0.118 | 0.142154 | 2.29982e-11 | 590 |
| -12 | -57.5066 | 0.20562 | 0.1658 | 0.20562 | 3.59406e-11 | 829 |
| -6 | -28.4178 | 0.245093 | 0.1994 | 0.245093 | 1.51995e-12 | 997 |
| 0 | 0.671005 | 0.257189 | 0.2128 | 0.257189 | 1.532e-12 | 1064 |
| 6 | 29.7598 | 0.243875 | 0.198 | 0.243875 | 9.68059e-12 | 990 |
| 12 | 58.8486 | 0.203218 | 0.1588 | 0.203218 | 2.46938e-11 | 794 |
| 18 | 87.9375 | 0.139152 | 0.1134 | 0.139152 | 4.80834e-11 | 567 |
| 30 | 146.115 | 0.0293273 | 0.022 | 0.0293273 | 1.31275e-11 | 110 |
| 60 | 291.559 | 7.72238e-06 | 0.0004 | 0.104219 | 1.99454e-11 | 2 |
| 90 | 437.003 | 7.78226e-12 | 0.0002 | 0.247433 | 3.55666e-11 | 1 |

This runs one B-FULL tile with the external XOP/CRYSTAL rocking-curve CSV as the Laue finite-MFP backend. Recorded p_reflect is checked against the interpolated XOP reflectivity at each recorded event delta_theta_model_rad. Observed interaction fractions are lower than XOP reflectivity because standard Geant4 EM processes compete with the Laue process.
