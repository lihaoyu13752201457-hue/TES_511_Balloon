# Bgo_sample Extended Closure Summary

Status: `PASS_BGO_SAMPLE_EXTENDED_CLOSURE`.

This tracked summary closes the BGO sidecar boundaries that were previously left as optional: detector-coupled spatial cuts, fixed-template annular likelihood, detector-threshold replay scan, and the BGO material attenuation design scan.

## Hard-Window Authority

- Step08 W2 Z20d: `6.43474787077`
- Step08 W2 T3: `4.21622404524` d
- Step08 W2 F3(20d): `4.6621873308e-05` ph cm^-2 s^-1

## Spatial Sidecars

- `spot_r90` time-dependent Z20d: `9.1588487945`
- `spot_r90` F3(20d): `3.27552082943e-05` ph cm^-2 s^-1
- fixed-template annular likelihood Z20d: `9.27695946834`
- fixed-template annular likelihood F3(20d): `3.23381816018e-05` ph cm^-2 s^-1
- annular likelihood gain vs hard-window Step08: `1.441697`

## Threshold Replay Scan

- status: `PASS_BGO_THRESHOLD_REPLAY_SCAN`
- authority 70 keV replay Z relative error: `0.000e+00`
- best threshold by F3 in scan: `50` keV

| threshold keV | background cps | signal cps | Z20d | F3(20d) |
| ---: | ---: | ---: | ---: | ---: |
| 50 | 0.0578203172714 | 0.00118595462408 | 6.43606904373 | 4.66123029386e-05 |
| 60 | 0.0578455354964 | 0.00118595462408 | 6.43474787077 | 4.6621873308e-05 |
| 70 | 0.0578455354964 | 0.00118595462408 | 6.43474787077 | 4.6621873308e-05 |
| 80 | 0.0578455354964 | 0.00118595462408 | 6.43474787077 | 4.6621873308e-05 |
| 100 | 0.0585242825023 | 0.00118595462408 | 6.39715269253 | 4.68958635848e-05 |

## Material Attenuation Scan

- status: `PASS_BGO_MATERIAL_ATTENUATION_SCAN`
- max absolute relative total-interaction efficiency difference: `0.07311829`
- tolerance: `0.1`

Boundary:
- The hard-window Step08 result remains the paper-facing counting sensitivity authority.
- The spatial numbers are detector-coupled sidecars: fixed cuts and fixed-template annular Poisson likelihood, not a nuisance-profile publication likelihood.
- The threshold scan replays the same transported event catalog; it closes detector-threshold robustness without new Cosima transport.
- The material scan is the tracked Geant4/MEGAlib total-cross-section attenuation design scan for the BGO equal-attenuation substitution.
