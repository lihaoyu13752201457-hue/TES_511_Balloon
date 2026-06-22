# Step08 v3p5 Center-Finger L1 Direct Significance

Status: `PASS_V3P5_STEP08_L1_DIRECT_EXPECTATION_1OF10`.

Claim level: L1 direct constant-rate expectation from v3p5 Step05 physical reference-flux rates; not a full Step06 mission-axis fold.

This sidecar turns the v3p5 Step05 direct expectation into a low-statistics significance checkpoint. It is intentionally conservative in scope: no Step06 time-dependent scaling, no accidental-live fold, and no profile-likelihood gain are claimed here.

Normalization:
- reference flux: `1.000000e-04 ph cm^-2 s^-1`
- optics: `balloon511_f10m_ge111_511line_a1`
- A_eff(511): `20.0848 cm2`
- T_atm: `0.739042`
- injection-plane rate: `0.00148435 s^-1`

Headline:
- window: `w2_510p58_511p42`
- background: `0.0157833 cps`; signal: `0.00118117 cps`
- 20-day direct Z: `12.359`
- constant-rate T3/T5: `1.17843` / `3.27342` day
- 20-day 3-sigma flux: `2.427377e-05 ph cm^-2 s^-1`
- low-stat selected background events: `18`

| window | background cps | signal cps | Z20d direct | T3 day | flux 3sigma 20d | low-stat B events |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| broad_480_550 | 0.0727785 | 0.00118328 | 5.76578 | 5.41447 | 5.203110e-05 | 83 |
| w2_510p58_511p42 | 0.0157833 | 0.00118117 | 12.359 | 1.17843 | 2.427377e-05 | 18 |

Warnings:
- headline W2 background is based on fewer than 50 selected background events.

Pending:
- Regenerate full v3p5 Step06 mission-time variation and accidental-live fold.
- Increase v3p5 background statistics; the W2 low-stat background here has only 18 final selected events.
- Replace axisymmetric delayed-source RadialProfileBeam compression with exact-position delayed-source sampling before paper-facing numbers.

JSON: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_1of10/step08_v3p5_centerfinger_l1_significance_summary.json`
CSV: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_1of10/step08_v3p5_centerfinger_l1_windows.csv`
