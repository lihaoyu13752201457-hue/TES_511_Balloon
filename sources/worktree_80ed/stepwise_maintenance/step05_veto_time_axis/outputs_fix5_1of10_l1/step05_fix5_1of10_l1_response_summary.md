# Step05 fix5 1/10 L1 Detector Response

Status: `PASS_FIX5_STEP05_SIDE_ENTRY_COMPTON_TIME_AXIS_L1_1OF10_NOT_PROMOTION`.

Claim level: fix5 1/10 prompt/delayed detector-response screen; not a promotion authority and not an old new_geo_re gate. Statistics label: `fix5_1of10`.

Inputs:
- prompt: `runs/step02_instant_fix5_1of10`
- delayed: `runs/step02_delayed_transport_fix5_1of10/DelayedDecayFix5Exactpos.inc1.id1.sim.gz`
- focused signal: `runs/step09_optics_bridge/Opticsim_laue_f10m_a1_v3p5_centerfinger.inc1.id1.sim.gz`

Normalization:
- prompt time: `18.4220098 s`
- prompt rate normalization: per-tag `1/sum(TT_tag)` from `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_1of10_l1/prompt_normalization_audit.csv`
- delayed observation time: `1317.36655 s`
- focused signal direct rates are first normalized to a unit EventList injection rate (`1 injected focused photon/s`).
- physical reference flux: `0.0001 ph cm^-2 s^-1`
- f10m A1 A_eff(511): `20.08476 cm2`
- inherited T_atm: `0.73904239`
- active-veto threshold: `50 keV`
- T_atm boundary: scalar mainline reference transmission is inherited here; the dedicated 45 deg side-entry LOS atmosphere sidecar is `outputs/reports/v3p5_boundary_closure_fullstat_v2_exactpos_20260613/v3p5_boundary_closure_summary.json`.
- reference injection-plane rate: `0.0014843489 s^-1`

## broad_480_550

| stream | raw rate | active-veto rate | side Compton/FoV rate | final/active |
| --- | ---: | ---: | ---: | ---: |
| prompt | 0.217343 | 0 | 0 |  |
| delayed | 0.00075909 | 0.00075909 | 0.00075909 | 1 |
| science | 0.81454 | 0.81454 | 0.797172 | 0.978677 |

Physical reference direct expectation:
- background: `0.00075909 cps`; signal at reference flux: `0.00118328 cps`
- 20-day counts: S `2044.71`, B `1311.71`
- Z20d direct S/sqrt(B): `56.4564`; T3 constant-rate direct: `0.0564737 day`; 20-day 3-sigma flux: `5.31384e-06 ph cm^-2 s^-1`
- low-stat final background events: `1`; approximate relative Poisson sigma `1`

## w2_510p58_511p42

| stream | raw rate | active-veto rate | side Compton/FoV rate | final/active |
| --- | ---: | ---: | ---: | ---: |
| prompt | 0.108671 | 0 | 0 |  |
| delayed | 0 | 0 | 0 |  |
| science | 0.812873 | 0.812873 | 0.795747 | 0.978931 |

Physical reference direct expectation:
- background: `0 cps`; signal at reference flux: `0.00118117 cps`
- 20-day counts: S `2041.05`, B `0`
- Z20d direct S/sqrt(B): `NA`; T3 constant-rate direct: `NA day`; 20-day 3-sigma flux: `NA ph cm^-2 s^-1`
- low-stat final background events: `0`; approximate relative Poisson sigma `NA`

## Common Poisson Time Axis

- observation time: `1317.36655 s`
- event instances drawn: `967496`
- candidates: `966784` total, `8154` with TES energy, `123` mixed-stream

| window | raw cps | active-veto cps | side Compton/FoV cps |
| --- | ---: | ---: | ---: |
| broad_480_550 | 0.998963 | 0.781863 | 0.762886 |
| w2_510p58_511p42 | 0.895726 | 0.781104 | 0.762127 |

Pending before fix5 promotion:
- Verifier must approve Step05 prompt/delayed selected-rate extraction before any gate decision.
- Old new_geo_re prompt/delayed numbers remain blocked as pass/fail gates while benchmark alignment is NOT_ALIGNED.
- Run a fix5 focused-signal replay before any signal-keep, Z20d, F3(20d), or promotion claim.
- Full-stat production is not released by this 1/10 Step05 screen.

CSV: `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_1of10_l1/step05_fix5_1of10_l1_rates.csv`
Timeline CSV: `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_1of10_l1/step05_fix5_1of10_l1_timeline_rates.csv`
