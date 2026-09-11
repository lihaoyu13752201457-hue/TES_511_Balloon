# Channel Bounce/Path Reconciliation

This diagnostic turns the current geometry blocker into a table that can be audited before more Geant4 geometry is added.

Literature reflection range used as lineage clue: `17-38`.
Effective model bounce range: `1-3`.
Required bounces at calibrated theta: `6.38-12.87`.

| Ring | effective bounces | needed at calibrated theta | theta if 17 bounces [rad] | theta if 38 bounces [rad] | half-gap band [um] |
| --- | ---: | ---: | ---: | ---: | ---: |
| R0 | 1 | 6.38 | 5.64665e-05 | 2.52613e-05 | 0.00698-0.03488 |
| R1 | 2 | 8.17 | 7.18665e-05 | 3.21508e-05 | 0.01142-0.05707 |
| R2 | 2 | 10.51 | 9.23998e-05 | 4.13367e-05 | 0.01904-0.09512 |
| R3 | 3 | 12.87 | 0.000112933 | 5.05227e-05 | 0.03058-0.1528 |

The next missing physics input is the actual many-bounce channel path. The current 1-3 bounce effective bookkeeping is too shallow, the calibrated-theta deflection estimate needs 6-13 bounces, and the 17-38-reflection literature clue would imply smaller local grazing angles that remain below the current calibrated theta scale. This supports recovering the original IDL/channel geometry before building four-ring wall-by-wall Geant4.
