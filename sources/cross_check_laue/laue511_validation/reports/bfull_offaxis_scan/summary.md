# B-FULL Off-Axis Scan

- ok: `True`
- executable: `/tmp/opticsim-bfull-build/laue_multiring_bfull_demo`
- events per offset: `1000`
- all runs registered in Geant4 EM category: `True`
- all runs use G4VEmProcess base: `True`
- transmitted_space rows match summary: `True`
- observed peak/min interaction ratio: `23.857142857142858`
- ring 2 observed peak/min ratio: `16.0`
- ring 2 XOP peak/min ratio: `24.71633205758415`

| offset arcmin | obs Laue frac | pred full no-EM | ring2 obs | ring2 XOP | ring2 |delta| urad |
|---:|---:|---:|---:|---:|---:|
| -5 | 0.019 | 0.0153127 | 0.0231481 | 0.0104056 | 925.357 |
| -3 | 0.027 | 0.0266085 | 0.037037 | 0.0177922 | 555.222 |
| -1 | 0.068 | 0.0820631 | 0.0694444 | 0.054959 | 185.086 |
| 0 | 0.334 | 0.383764 | 0.296296 | 0.257189 | 0.671005 |
| 1 | 0.074 | 0.0820632 | 0.0462963 | 0.054959 | 185.086 |
| 3 | 0.02 | 0.0266085 | 0.0185185 | 0.0177922 | 555.222 |
| 5 | 0.014 | 0.0153127 | 0.0231481 | 0.0104056 | 925.357 |

Observed B-FULL interaction fractions include Geant4 standard EM competition. Predicted diffraction-only fractions are the local finite-MFP backend without EM competition. Ring 2 XOP values are 511 keV CRYSTAL rocking-curve interpolations averaged over the same tile sequence.
