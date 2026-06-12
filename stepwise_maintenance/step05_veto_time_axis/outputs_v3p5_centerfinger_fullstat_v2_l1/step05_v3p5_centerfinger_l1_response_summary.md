# Step05 v3p5 Center-Finger L1 Detector Response

Status: `PASS_V3P5_STEP05_SIDE_ENTRY_COMPTON_TIME_AXIS_L1_FULLSTAT_V2`.

Claim level: v3p5 side-entry Compton/FoV migrated to the tilted Be disk, plus direct expectation, physical reference-flux scaling, and one common Poisson time-axis draw. Statistics label: `fullstat_v2`.

Inputs:
- prompt: `runs/step02_instant_v3p5_centerfinger_fullstat_v2`
- delayed: `runs/step02_delayed_transport_v3p5_centerfinger_fullstat_v2/DelayedDecayRPIPGroundStateFixed.inc1.id1.sim.gz`
- focused signal: `runs/step09_optics_bridge/Opticsim_laue_f10m_a1_v3p5_centerfinger.inc1.id1.sim.gz`

Normalization:
- prompt time: `184.220098 s`
- prompt rate normalization: per-tag `1/sum(TT_tag)` from `stepwise_maintenance/step05_veto_time_axis/outputs_v3p5_centerfinger_fullstat_v2_l1/prompt_normalization_audit.csv`
- delayed observation time: `11531.5985 s`
- focused signal direct rates are first normalized to a unit EventList injection rate (`1 injected focused photon/s`).
- physical reference flux: `0.0001 ph cm^-2 s^-1`
- f10m A1 A_eff(511): `20.08476 cm2`
- inherited T_atm: `0.73904239`
- T_atm limitation: scalar mainline reference transmission is inherited; the 45 deg side-entry absolute atmospheric path has not been recomputed.
- reference injection-plane rate: `0.0014843489 s^-1`

## broad_480_550

| stream | raw rate | active-veto rate | side Compton/FoV rate | final/active |
| --- | ---: | ---: | ---: | ---: |
| prompt | 0.285688 | 0.0841953 | 0.0740165 | 0.879105 |
| delayed | 0.0933956 | 0.069548 | 0.0590551 | 0.849127 |
| science | 0.81454 | 0.81454 | 0.797172 | 0.978677 |

Physical reference direct expectation:
- background: `0.133072 cps`; signal at reference flux: `0.00118328 cps`
- 20-day counts: S `2044.71`, B `229948`
- Z20d direct S/sqrt(B): `4.264`; T3 constant-rate direct: `9.90008 day`; 20-day 3-sigma flux: `7.03565e-05 ph cm^-2 s^-1`
- low-stat final background events: `790`; approximate relative Poisson sigma `0.0355784`

## w2_510p58_511p42

| stream | raw rate | active-veto rate | side Compton/FoV rate | final/active |
| --- | ---: | ---: | ---: | ---: |
| prompt | 0.164908 | 0.0624788 | 0.0590827 | 0.945644 |
| delayed | 0.0236741 | 0.0157827 | 0.0138749 | 0.879121 |
| science | 0.812873 | 0.812873 | 0.795747 | 0.978931 |

Physical reference direct expectation:
- background: `0.0729576 cps`; signal at reference flux: `0.00118117 cps`
- 20-day counts: S `2041.05`, B `126071`
- Z20d direct S/sqrt(B): `5.7484`; T3 constant-rate direct: `5.44726 day`; 20-day 3-sigma flux: `5.21884e-05 ph cm^-2 s^-1`
- low-stat final background events: `247`; approximate relative Poisson sigma `0.0636285`

## Common Poisson Time Axis

- observation time: `11531.5985 s`
- event instances drawn: `8862059`
- candidates: `8855254` total, `94926` with TES energy, `327` mixed-stream

| window | raw cps | active-veto cps | side Compton/FoV cps |
| --- | ---: | ---: | ---: |
| broad_480_550 | 1.21267 | 0.988241 | 0.950779 |
| w2_510p58_511p42 | 1.01712 | 0.909588 | 0.886694 |

Pending before paper-facing v3p5 statistics:
- replace the axisymmetric delayed-source compression with exact-position sampling before paper-facing numbers.
- add selection-consistent spatial/profile likelihood products.

CSV: `stepwise_maintenance/step05_veto_time_axis/outputs_v3p5_centerfinger_fullstat_v2_l1/step05_v3p5_centerfinger_l1_rates.csv`
Timeline CSV: `stepwise_maintenance/step05_veto_time_axis/outputs_v3p5_centerfinger_fullstat_v2_l1/step05_v3p5_centerfinger_l1_timeline_rates.csv`
