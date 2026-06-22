# Delayed Distribution Invariance Smoke

Status: `PASS_PARTICLE_FAMILY_REWEIGHTING_SMOKE`.

This is a particle-family reweighting smoke test for the mission-time delayed-activation approximation. It uses local PARMA trajectory probes and the existing full-stat activation-buildup isotope store; it does not rerun Geant4 activation transport.

## Main Metrics

- max activity-distribution TV after particle-family reweighting: `0.00572033`
- max PARMA particle-family TV: `0.000676445`
- max PARMA particle-energy-bin TV: `0.00904579`
- ground-state activity matched to parsed DAT yields: `0.99289844`

## Probe Results

### low_altitude

- day `3.75`, altitude `36.25 km`, latitude `34.1559 deg`, longitude `99.75 deg`.
- particle-family TV: `0.000676445`.
- particle-angle/direction TV: `0.0418489`.
- particle-energy-bin TV: `0.00810313`.
- nuclide TV after particle reweighting: `0.00478306`.
- volume-class TV after particle reweighting: `0.00435057`.
- nuclide-volume TV after particle reweighting: `0.00481374`.
- total activity scale from particle-family reweighting: `1.22638`.

### day15_reference

- day `15`, altitude `38.75 km`, latitude `34 deg`, longitude `100 deg`.
- particle-family TV: `0`.
- particle-angle/direction TV: `0`.
- particle-energy-bin TV: `0`.
- nuclide TV after particle reweighting: `0`.
- volume-class TV after particle reweighting: `0`.
- nuclide-volume TV after particle reweighting: `0`.
- total activity scale from particle-family reweighting: `1`.

### high_altitude

- day `1.25`, altitude `41.25 km`, latitude `34.0556 deg`, longitude `100.043 deg`.
- particle-family TV: `0.000537328`.
- particle-angle/direction TV: `0.0423658`.
- particle-energy-bin TV: `0.00904579`.
- nuclide TV after particle reweighting: `0.00549396`.
- volume-class TV after particle reweighting: `0.00499597`.
- nuclide-volume TV after particle reweighting: `0.00552853`.
- total activity scale from particle-family reweighting: `0.840718`.

## Boundary

This smoke supports only the particle-family reweighting layer of the distribution-invariance assumption. It does not test same-particle energy/angle-dependent activation cross sections or transport-position shifts; a stronger proof requires low/high/reference Geant4 activation-production reruns with generated PARMA source cards.

This means the scalar delayed-production fold is smoke-tested at the particle-family remixing layer only. The result should not be worded as a full physical proof that isotope/material/position distributions are invariant under all altitude and geomagnetic changes.
