# Geant4 Darwin/Guan Sensitivity Check

This is a small sanity check for the compiled 02 implementation. It does not claim to reproduce the full Guan/Reiazi benchmark matrix; it checks whether the local online Darwin-Hamilton backend responds to physical crystal parameters.

## Result Table

| case | mosaic FWHM arcsec | crystallite um | diffraction | absorption | transmission | spot D90 cm | delta diffraction vs nominal |
|---|---:|---:|---:|---:|---:|---:|---:|
| nominal | 30.0 | 5.0 | 0.24420 | 0.35615 | 0.39965 | 0.21777 | +0.00000 |
| mosaic_narrow | 15.0 | 5.0 | 0.30165 | 0.35745 | 0.34090 | 0.11018 | +0.05745 |
| mosaic_wide | 60.0 | 5.0 | 0.16935 | 0.35700 | 0.47365 | 0.44234 | -0.07485 |
| crystallite_thin | 30.0 | 2.5 | 0.24790 | 0.35910 | 0.39300 | 0.22214 | +0.00370 |
| crystallite_thick | 30.0 | 20.0 | 0.24325 | 0.35940 | 0.39735 | 0.22197 | -0.00095 |

## Interpretation

- Nominal case: mosaic `30.0` arcsec, crystallite `5.0` um, diffraction `0.24420`.
- Narrower mosaic case changes diffraction by `+0.05745` relative to nominal.
- Wider mosaic case changes diffraction by `-0.07485` relative to nominal.
- Crystallite-thickness endpoints change diffraction by `0.00465` across the scanned range.
- All cases report `uses_external_efficiency_table_for_physics=false`, so this is a runtime check of the online 02 backend rather than the 01 probability CSV.

## Boundary

This is a local fixed-lens sensitivity check. A paper-level Reiazi reproduction would still require XOP benchmarks over perfect/mosaic crystals, materials, energies, mosaicity, absorption, and crystallite direction/thickness.
