# S2b Zero-Plastic Eplus Trace

These are S2b W2 e+ final-pass events with `plastic_skin_keV = 0`, `legacy_active_keV = 0`, and no Compton/FoV veto.

- Candidate events: `8`
- Classification counts: `{'passive_annihilation_gamma_to_TES': 8}`

| local id | class | TES hits | side class | annihilation xyz cm | annihilation rxy cm | PM lines |
|---:|---|---:|---|---|---:|---|
| 134175 | passive_annihilation_gamma_to_TES | 1 | single | 26.56, 43.12, 39.75 | 50.64 | `PM Aluminium   13.43875` |
| 141050 | passive_annihilation_gamma_to_TES | 2 | keep | -37.63, -10.59, 39.75 | 39.09 | `PM Aluminium   71.89522` |
| 58569 | passive_annihilation_gamma_to_TES | 2 | keep | 5.58, 43.25, -14.45 | 43.61 | `PM G10   17.42986` |
| 134659 | passive_annihilation_gamma_to_TES | 1 | single | -5.28, 43.20, 40.24 | 43.53 | `PM Aluminium  181.80918` |
| 196637 | passive_annihilation_gamma_to_TES | 1 | single | 40.12, -22.22, -8.49 | 45.86 | `PM G10    5.12334` |
| 216984 | passive_annihilation_gamma_to_TES | 1 | single | -41.30, -8.24, -23.50 | 42.12 | `PM Aluminium   43.04541` |
| 140660 | passive_annihilation_gamma_to_TES | 1 | single | 26.70, -43.70, 39.91 | 51.20 | `PM Aluminium  467.76375` |
| 155182 | passive_annihilation_gamma_to_TES | 1 | single | 3.75, -41.17, 17.42 | 41.34 | `PM G10   42.23705` |

## Interpretation

All listed events are consistent with the primary positron annihilating in passive material, followed by a 511 keV annihilation gamma depositing W2 energy in TES. Because the charged positron did not deposit energy in `GeoOpt_S2B_CryoShell_Plastic*` or legacy active volumes, lowering the plastic threshold cannot veto these events.
