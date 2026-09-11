# Plastic 20 keV / CsI-legacy 50 keV — S3 vs S2b W2 Replay

- Plastic skin veto threshold: `20 keV` (**only plastic changed**).
- CsI / legacy active veto threshold: `50 keV` (unchanged).
- Transport and Compton/FoV classification unchanged; event-level post-processing only.

| component | stage | S2b events | S3 events | S2b cps | S3 cps | S3/S2b |
|---|---|---:|---:|---:|---:|---:|
| eplus | raw | 52 | 29 | 0.0352625 | 0.0196897 | 0.558375 +/- 0.129 |
| eplus | active_veto_pass | 18 | 12 | 0.0122063 | 0.00814746 | 0.667483 +/- 0.249 |
| eplus | side_compton_fov_pass | 17 | 11 | 0.0115281 | 0.00746851 | 0.647851 +/- 0.251 |
| n | raw | 42 | 56 | 0.0284927 | 0.0379975 | 1.33359 +/- 0.272 |
| n | active_veto_pass | 5 | 1 | 0.00339198 | 0.000678527 | 0.200039 +/- 0.219 |
| n | side_compton_fov_pass | 5 | 1 | 0.00339198 | 0.000678527 | 0.200039 +/- 0.219 |
| atm511 | raw | 116 | 60 | 0.0225708 | 0.0116605 | 0.51662 +/- 0.0822 |
| atm511 | active_veto_pass | 116 | 60 | 0.0225708 | 0.0116605 | 0.51662 +/- 0.0822 |
| atm511 | side_compton_fov_pass | 108 | 56 | 0.0210142 | 0.0108831 | 0.517896 +/- 0.0853 |

## Final-pass diagnostics (plastic20 / legacy50)

| geometry | particle | raw | active pass | final | plastic20 veto | legacy50 veto | Compton/FoV | final plastic bins |
|---|---|---:|---:|---:|---:|---:|---:|---|
| S2b | atm511 | 116 | 116 | 108 | 0 | 0 | 8 | `{'zero': 108}` |
| S2b | eplus | 52 | 18 | 17 | 34 | 0 | 1 | `{'gt0_lt20': 9, 'zero': 8}` |
| S2b | n | 42 | 5 | 5 | 16 | 21 | 0 | `{'gt0_lt20': 1, 'zero': 4}` |
| S3 | atm511 | 60 | 60 | 56 | 0 | 0 | 4 | `{'zero': 56}` |
| S3 | eplus | 29 | 12 | 11 | 17 | 0 | 1 | `{'gt0_lt20': 3, 'zero': 8}` |
| S3 | n | 56 | 1 | 1 | 11 | 44 | 0 | `{'gt0_lt20': 1}` |

## Notes

- Equal-stat SIMs: same as 50 keV baseline comparison package.
- atm511 typically has zero plastic deposit; plastic threshold change does not affect it.
- Not a Step05–08 promotion; delayed/signal not rerun.
