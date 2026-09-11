# S3d-O8 all-eight-family detector-response closure

Status: `PASS_S3D_O8_ALL8_EVENT_LEVEL_420EV_FWHM_ENERGY_RESPONSE_CLOSURE`

This package applies the 420 eV FWHM Gaussian TES response per aggregated pixel,
then the 0.3 keV measured-hit threshold and the frozen W2/active-veto/side-entry
selection, to the package-44 all-eight-family catalogue.

## Primary W2 day-15 result

- Response seed: `26071301`.
- Prompt: `0.00339303151412` cps.
- Delayed (all incident families): `0.00201657067387` cps.
- Atmospheric 511: `0.00155526135195` cps.
- Total background: `0.00696486353994` cps.
- Reference-flux signal: `0.00111783117476` cps.
- Positive transported delayed families: `alpha, eplus, gamma, muminus, muplus, n, p`.
- Finite-buildup zero-observation families: `eminus`.

The zero-observation label is not a physical-zero claim. Its central delayed
estimate is zero and no fictitious transport exposure is assigned. The conditional
componentwise transport-counting endpoint is not full 95% coverage and excludes
buildup-yield, M-sampling, zero-family, and nuclide-mixture uncertainty.

## Validation

- Unsmeared Step05 reproduction: `PASS_EXACT_ALL8_UNSMEARED_STEP05_REPRODUCTION`.
- Retained neutron/raw-SIM regression: `PASS_S3D_O8_ALL8_RETAINED_NEUTRON_RESPONSE_REGRESSION`.
- Response ensemble: `PASS_RESPONSE_SEED_ENSEMBLE` across `64` seeds.
- Independent response validator: `PASS_S3D_O8_ALL8_ENERGY_RESPONSE_VALIDATION`.
- Final mission numbers are intentionally deferred to the family-by-nuclide 81-bin fold.
