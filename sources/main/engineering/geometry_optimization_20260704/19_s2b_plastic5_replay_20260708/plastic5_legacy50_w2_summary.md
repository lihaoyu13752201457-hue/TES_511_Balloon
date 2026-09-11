# Plastic5 Legacy50 W2 Replay

- Plastic skin veto threshold: `5 keV`.
- Legacy active/CsI/BGO threshold: `50 keV`.
- Transport and Compton/FoV classification are unchanged; this is a W2 event-level replay.

| component | stage | S1 events | S2b events | S1 cps | S2b cps | S2b/S1 |
|---|---:|---:|---:|---:|---:|---:|
| eplus | raw | 62 | 52 | 0.042100374 | 0.035262509 | 0.837582 |
| eplus | active_veto_pass | 26 | 12 | 0.017654996 | 0.0081375021 | 0.460918 |
| eplus | side_compton_fov_pass | 22 | 11 | 0.014938842 | 0.0074593769 | 0.499328 |
| n | raw | 60 | 42 | 0.040711778 | 0.028492657 | 0.699863 |
| n | active_veto_pass | 12 | 5 | 0.0081423555 | 0.003391983 | 0.416585 |
| n | side_compton_fov_pass | 12 | 5 | 0.0081423555 | 0.003391983 | 0.416585 |
| atm511 | raw | 114 | 116 | 0.022151493 | 0.022570772 | 1.01893 |
| atm511 | active_veto_pass | 114 | 116 | 0.022151493 | 0.022570772 | 1.01893 |
| atm511 | side_compton_fov_pass | 107 | 108 | 0.020791314 | 0.021014167 | 1.01072 |

## S2b Final-Pass Diagnostics

| particle | raw | active pass | final | plastic5 veto | legacy50 veto | Compton/FoV veto | final plastic bins |
|---|---:|---:|---:|---:|---:|---:|---|
| eplus | 52 | 12 | 11 | 40 | 0 | 1 | `{'gt0_lt5': 3, 'zero': 8}` |
| n | 42 | 5 | 5 | 17 | 20 | 0 | `{'gt0_lt5': 1, 'zero': 4}` |
| atm511 | 116 | 116 | 108 | 0 | 0 | 8 | `{'zero': 108}` |
