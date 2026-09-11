# Focal Convention Audit

Evaluated Geant4 focal plane: `8300.000000 mm`

## Summary

- ring CSV center-plane focal mean: `8301.499662 mm`
- entry-face Bragg focal range: `8295.911516` to `8296.773552 mm`
- max center-plane radius delta at evaluated focal: `0.0118588 mm`
- max entry-face delta theta: `0.350335 arcsec`
- max absolute p_diff shift from exact-Bragg probability: `4.12974e-05`
- max relative p_diff shift: `0.00017557`

## Interpretation

The ring CSV is internally consistent as a center-plane Bragg-radius table.
The current Geant4 process evaluates interactions at the upstream crystal face and focuses to the configured focal plane.
At `8300 mm`, this creates a small ring-dependent angular offset that is already included in the recorded Geant4 probabilities.

Recommendation for the current cross-check: keep `8300 mm` as the operational Geant4 convention for existing runs, and record the CSV center-plane convention explicitly.

## Per Ring

| ring | E_keV | center focal mm | entry Bragg focal mm | entry delta arcsec | p_diff shift |
|---:|---:|---:|---:|---:|---:|
| 0 | 480.0 | 8301.499683 | 8296.773552 | -0.316817 | -3.35594e-05 |
| 1 | 500.0 | 8301.499674 | 8296.526021 | -0.327469 | -3.59704e-05 |
| 2 | 511.0 | 8301.499679 | 8296.390279 | -0.332935 | -3.72284e-05 |
| 3 | 530.0 | 8301.499635 | 8296.156493 | -0.34178 | -3.92878e-05 |
| 4 | 550.0 | 8301.499641 | 8295.911516 | -0.350335 | -4.12974e-05 |
