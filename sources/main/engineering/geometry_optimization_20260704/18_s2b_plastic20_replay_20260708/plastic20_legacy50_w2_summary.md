# Plastic20 Legacy50 W2 Replay

- Plastic skin veto threshold: `20 keV`.
- Legacy active/CsI/BGO threshold: `50 keV`.
- Transport and Compton/FoV classification are unchanged; this is a W2 event-level replay.

| component | stage | S1 events | S2b events | S1 cps | S2b cps | S2b/S1 |
|---|---:|---:|---:|---:|---:|---:|
| eplus | raw | 62 | 52 | 0.042100374 | 0.035262509 | 0.837582 |
| eplus | active_veto_pass | 36 | 18 | 0.024445378 | 0.012206253 | 0.499328 |
| eplus | side_compton_fov_pass | 31 | 17 | 0.021050187 | 0.011528128 | 0.54765 |
| n | raw | 60 | 42 | 0.040711778 | 0.028492657 | 0.699863 |
| n | active_veto_pass | 13 | 5 | 0.0088208851 | 0.003391983 | 0.38454 |
| n | side_compton_fov_pass | 13 | 5 | 0.0088208851 | 0.003391983 | 0.38454 |
| atm511 | raw | 114 | 116 | 0.022151493 | 0.022570772 | 1.01893 |
| atm511 | active_veto_pass | 114 | 116 | 0.022151493 | 0.022570772 | 1.01893 |
| atm511 | side_compton_fov_pass | 107 | 108 | 0.020791314 | 0.021014167 | 1.01072 |

## S2b Final-Pass Diagnostics

| particle | raw | active pass | final | plastic20 veto | legacy50 veto | Compton/FoV veto | final plastic bins |
|---|---:|---:|---:|---:|---:|---:|---|
| eplus | 52 | 18 | 17 | 34 | 0 | 1 | `{'gt0_lt20': 9, 'zero': 8}` |
| n | 42 | 5 | 5 | 16 | 21 | 0 | `{'gt0_lt20': 1, 'zero': 4}` |
| atm511 | 116 | 116 | 108 | 0 | 0 | 8 | `{'zero': 108}` |
