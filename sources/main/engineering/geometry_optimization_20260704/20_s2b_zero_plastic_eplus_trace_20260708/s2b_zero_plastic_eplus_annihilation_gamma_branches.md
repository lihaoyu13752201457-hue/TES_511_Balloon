# S2b Zero-Plastic Eplus Annihilation Gamma Branches

Each zero-plastic e+ event produces two 511 keV annihilation-gamma branches. This table follows those branches using IA parentage and CC HIT ancestry.

- Events: `8`
- Gamma branches: `16`
- Branch terminal counts: `{'escape': 8, 'tes_interaction': 8}`
- Branches with plastic or legacy-active energy: `0`

| event | branch | terminal | event TES keV | event plastic keV | event legacy active keV | first TES IA | side class | process chain |
|---:|---:|---|---:|---:|---:|---|---|---|
| 134175 | 2 | escape | 510.999 | 0.000 | 0.000 |  | single | `ESCP` |
| 134175 | 3 | tes_interaction | 510.999 | 0.000 | 0.000 | PHOT (-4.18, 0.67, -3.19) | single | `PHOT -> PHOT -> PHOT` |
| 134659 | 2 | tes_interaction | 510.999 | 0.000 | 0.000 | PHOT (-5.84, 1.27, -1.52) | single | `PHOT -> PHOT -> PHOT` |
| 134659 | 3 | escape | 510.999 | 0.000 | 0.000 |  | single | `ESCP` |
| 140660 | 2 | escape | 510.999 | 0.000 | 0.000 |  | single | `ESCP` |
| 140660 | 3 | tes_interaction | 510.999 | 0.000 | 0.000 | PHOT (-1.34, -1.26, -5.39) | single | `PHOT -> PHOT -> PHOT` |
| 141050 | 2 | tes_interaction | 510.999 | 0.000 | 0.000 | COMP (-2.29, -0.65, -3.07) | keep | `RAYL -> COMP -> PHOT -> BREM -> PHOT` |
| 141050 | 3 | escape | 510.999 | 0.000 | 0.000 |  | keep | `ESCP` |
| 155182 | 2 | tes_interaction | 510.999 | 0.000 | 0.000 | PHOT (-2.95, -0.01, -2.20) | single | `PHOT -> PHOT -> PHOT -> BREM -> PHOT -> PHOT -> PHOT` |
| 155182 | 3 | escape | 510.999 | 0.000 | 0.000 |  | single | `ESCP` |
| 196637 | 2 | escape | 510.999 | 0.000 | 0.000 |  | single | `ESCP` |
| 196637 | 3 | tes_interaction | 510.999 | 0.000 | 0.000 | PHOT (-1.44, 0.17, -5.58) | single | `PHOT -> PHOT -> PHOT -> PHOT -> PHOT -> PHOT` |
| 216984 | 2 | escape | 510.999 | 0.000 | 0.000 |  | single | `ESCP` |
| 216984 | 3 | tes_interaction | 510.999 | 0.000 | 0.000 | PHOT (-0.90, 0.10, -5.10) | single | `PHOT -> PHOT -> PHOT` |
| 58569 | 2 | escape | 510.999 | 0.000 | 0.000 |  | keep | `ESCP` |
| 58569 | 3 | tes_interaction | 510.999 | 0.000 | 0.000 | PHOT (-1.23, 0.09, -5.67) | keep | `PHOT -> PHOT -> PHOT -> PHOT -> PHOT -> BREM -> PHOT` |

## Veto Interpretation

- Active-veto failure: all 16 annihilation-gamma branches have `plastic_edep_keV = 0` and `legacy_active_edep_keV = 0`; active veto has no energy deposit to threshold on.
- Gamma physics: these are neutral 511 keV photons. A plastic charged-particle skin does not record a crossing photon unless the photon Compton scatters or photoabsorbs in it.
- Compton/FoV failure: six events are single-TES-hit and are kept by design; the two multi-hit events are `keep` because their reconstructed side-entry Compton/FoV solution remains compatible with the allowed aperture.
