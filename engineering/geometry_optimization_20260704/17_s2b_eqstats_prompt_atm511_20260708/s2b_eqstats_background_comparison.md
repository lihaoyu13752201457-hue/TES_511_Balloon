# S2b Equal-Stat Background Comparison

Prompt source radius: `60 cm`, source sphere center: `(5, 0, 9) cm` in S2b `.geo.setup`.
Active-veto threshold: `50 keV`.
Active-veto volumes include legacy active volumes plus `GeoOpt_S1_PlasticFullWrap*` and `GeoOpt_S2B_CryoShell_Plastic*`.

| component | stage | S1 events | S2b events | S1 cps | S2b cps | S2b/S1 |
|---|---|---:|---:|---:|---:|---:|
| eplus | raw | 62 | 52 | 0.0421004 | 0.0352625 | 0.837582 +/- 0.158 |
| eplus | active_veto_pass | 40 | 28 | 0.0271615 | 0.0189875 | 0.699059 +/- 0.172 |
| eplus | side_compton_fov_pass | 35 | 27 | 0.0237663 | 0.0183094 | 0.770391 +/- 0.197 |
| n | raw | 60 | 42 | 0.0407118 | 0.0284927 | 0.699863 +/- 0.141 |
| n | active_veto_pass | 13 | 5 | 0.00882089 | 0.00339198 | 0.38454 +/- 0.202 |
| n | side_compton_fov_pass | 13 | 5 | 0.00882089 | 0.00339198 | 0.38454 +/- 0.202 |
| atm511 | raw | 114 | 116 | 0.0221515 | 0.0225708 | 1.01893 +/- 0.134 |
| atm511 | active_veto_pass | 114 | 116 | 0.0221515 | 0.0225708 | 1.01893 +/- 0.134 |
| atm511 | side_compton_fov_pass | 107 | 108 | 0.0207913 | 0.0210142 | 1.01072 +/- 0.138 |

Scope notes:

- This is a prompt e+/n plus atmospheric-511 geometry comparison, not a full Step05/06/08 sensitivity promotion.
- Delayed activation and signal throughput are not rerun in this package.
- Counting uncertainties above are simple selected-event Poisson errors only.
