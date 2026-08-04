# S3 Equal-Stat Prompt All-Particle Summary

S3-only table for later Mass_511 comparison.
Prompt: gamma `1e7` events / 12 splits; non-gamma 8 replicas; farfield radius `60 cm`.
ATM511: existing S3 4pi sidecar, `3e6` events.

| component | stage | events | cps |
|---|---|---:|---:|
| gamma | raw | 0 | 0 |
| gamma | active_veto_pass | 0 | 0 |
| gamma | side_compton_fov_pass | 0 | 0 |
| eminus | raw | 0 | 0 |
| eminus | active_veto_pass | 0 | 0 |
| eminus | side_compton_fov_pass | 0 | 0 |
| eplus | raw | 29 | 0.0196897 |
| eplus | active_veto_pass | 15 | 0.0101843 |
| eplus | side_compton_fov_pass | 14 | 0.00950537 |
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

Input note:

- S3 `alpha` and `gamma` use the clean completed jobs in `s3_csi_barrel_eqstats_prompt_other_20260709`.
- S3 `eminus/muminus/muplus/p` use the clean completed continuation directory `s3_csi_barrel_eqstats_prompt_other_emup_20260709`.
- Partial interrupted jobs in the first continuation directory are not used for those particles.
