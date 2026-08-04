# S3 Plastic20 / Legacy50 Prompt All-Particle Replay

- Plastic skin veto threshold: `20 keV`.
- CsI / legacy active veto threshold: `50 keV`.
- S3-only output for later Mass_511 comparison.

| component | stage | events | cps |
|---|---|---:|---:|
| gamma | raw | 0 | 0 |
| gamma | active_veto_pass | 0 | 0 |
| gamma | side_compton_fov_pass | 0 | 0 |
| eminus | raw | 0 | 0 |
| eminus | active_veto_pass | 0 | 0 |
| eminus | side_compton_fov_pass | 0 | 0 |
| eplus | raw | 29 | 0.0196897 |
| eplus | active_veto_pass | 12 | 0.00814746 |
| eplus | side_compton_fov_pass | 11 | 0.00746851 |
| n | raw | 56 | 0.0379975 |
| n | active_veto_pass | 1 | 0.000678527 |
| n | side_compton_fov_pass | 1 | 0.000678527 |
| p | raw | 2 | 0.00135847 |
| p | active_veto_pass | 0 | 0 |
| p | side_compton_fov_pass | 0 | 0 |
| alpha | raw | 0 | 0 |
| alpha | active_veto_pass | 0 | 0 |
| alpha | side_compton_fov_pass | 0 | 0 |
| muminus | raw | 5 | 0.00340477 |
| muminus | active_veto_pass | 0 | 0 |
| muminus | side_compton_fov_pass | 0 | 0 |
| muplus | raw | 9 | 0.00611738 |
| muplus | active_veto_pass | 0 | 0 |
| muplus | side_compton_fov_pass | 0 | 0 |
| atm511 | raw | 60 | 0.0116605 |
| atm511 | active_veto_pass | 60 | 0.0116605 |
| atm511 | side_compton_fov_pass | 56 | 0.0108831 |

## Diagnostics

| component | raw | active pass | final | plastic20 veto | legacy50 veto | Compton/FoV | final plastic bins |
|---|---:|---:|---:|---:|---:|---:|---|
| gamma | 0 | 0 | 0 | 0 | 0 | 0 | `{}` |
| eminus | 0 | 0 | 0 | 0 | 0 | 0 | `{}` |
| eplus | 29 | 12 | 11 | 17 | 0 | 1 | `{'gt0_lt20': 3, 'zero': 8}` |
| n | 56 | 1 | 1 | 11 | 44 | 0 | `{'gt0_lt20': 1}` |
| p | 2 | 0 | 0 | 2 | 0 | 0 | `{}` |
| alpha | 0 | 0 | 0 | 0 | 0 | 0 | `{}` |
| muminus | 5 | 0 | 0 | 5 | 0 | 0 | `{}` |
| muplus | 9 | 0 | 0 | 9 | 0 | 0 | `{}` |
| atm511 | 60 | 60 | 56 | 0 | 0 | 4 | `{'zero': 56}` |
