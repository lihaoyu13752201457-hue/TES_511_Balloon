# Step05 v3p5 Center-Finger L1 Detector Response

Status: `PASS_V3P5_STEP05_SIDE_ENTRY_COMPTON_TIME_AXIS_L1_FULLSTAT_V2_EXACTPOS`.

Claim level: v3p5 side-entry Compton/FoV migrated to the tilted Be disk, plus direct expectation, physical reference-flux scaling, and one common Poisson time-axis draw. Statistics label: `fullstat_v2_exactpos`.

Inputs:
- prompt: `runs/step02_instant_v3p5_centerfinger_fullstat_v2`
- delayed: `runs/step02_delayed_transport_v3p5_centerfinger_fullstat_v2_exactpos/DelayedDecayRPIPGroundStateFixed.inc1.id1.sim.gz`
- focused signal: `runs/step09_optics_bridge/Opticsim_laue_f10m_a1_v3p5_centerfinger.inc1.id1.sim.gz`

Normalization:
- prompt time: `184.220098 s`
- prompt rate normalization: per-tag `1/sum(TT_tag)` from `stepwise_maintenance/step05_veto_time_axis/outputs_v3p5_centerfinger_fullstat_v2_exactpos_l1/prompt_normalization_audit.csv`
- delayed observation time: `11530.4738 s`
- focused signal direct rates are first normalized to a unit EventList injection rate (`1 injected focused photon/s`).
- physical reference flux: `0.0001 ph cm^-2 s^-1`
- f10m A1 A_eff(511): `20.08476 cm2`
- inherited T_atm: `0.73904239`
- T_atm boundary: scalar mainline reference transmission is inherited here; the dedicated 45 deg side-entry LOS atmosphere sidecar is `outputs/reports/v3p5_boundary_closure_fullstat_v2_exactpos_20260613/v3p5_boundary_closure_summary.json`.
- reference injection-plane rate: `0.0014843489 s^-1`

## broad_480_550

| stream | raw rate | active-veto rate | side Compton/FoV rate | final/active |
| --- | ---: | ---: | ---: | ---: |
| prompt | 0.285688 | 0.0841953 | 0.0740165 | 0.879105 |
| delayed | 0.00849922 | 0.00476997 | 0.00381598 | 0.8 |
| science | 0.81454 | 0.81454 | 0.797172 | 0.978677 |

Physical reference direct expectation:
- background: `0.0778325 cps`; signal at reference flux: `0.00118328 cps`
- 20-day counts: S `2044.71`, B `134495`
- Z20d direct S/sqrt(B): `5.57544`; T3 constant-rate direct: `5.79047 day`; 20-day 3-sigma flux: `5.38074e-05 ph cm^-2 s^-1`
- low-stat final background events: `153`; approximate relative Poisson sigma `0.0808452`

## w2_510p58_511p42

| stream | raw rate | active-veto rate | side Compton/FoV rate | final/active |
| --- | ---: | ---: | ---: | ---: |
| prompt | 0.164908 | 0.0624788 | 0.0590827 | 0.945644 |
| delayed | 0.00607087 | 0.00398943 | 0.00338234 | 0.847826 |
| science | 0.812873 | 0.812873 | 0.795747 | 0.978931 |

Physical reference direct expectation:
- background: `0.0624651 cps`; signal at reference flux: `0.00118117 cps`
- 20-day counts: S `2041.05`, B `107940`
- Z20d direct S/sqrt(B): `6.21247`; T3 constant-rate direct: `4.66385 day`; 20-day 3-sigma flux: `4.829e-05 ph cm^-2 s^-1`
- low-stat final background events: `126`; approximate relative Poisson sigma `0.0890871`

## Common Poisson Time Axis

- observation time: `11530.4738 s`
- event instances drawn: `9499237`
- candidates: `9491476` total, `72125` with TES energy, `1225` mixed-stream

| window | raw cps | active-veto cps | side Compton/FoV cps |
| --- | ---: | ---: | ---: |
| broad_480_550 | 1.11054 | 0.908983 | 0.881924 |
| w2_510p58_511p42 | 0.985822 | 0.885566 | 0.865706 |

Pending before paper-facing v3p5 statistics:
- quantify exact-RPIP PointSource support-size stability, or run the full weighted-table source if Cosima parsing is made practical
- add selection-consistent spatial/profile likelihood products

CSV: `stepwise_maintenance/step05_veto_time_axis/outputs_v3p5_centerfinger_fullstat_v2_exactpos_l1/step05_v3p5_centerfinger_l1_rates.csv`
Timeline CSV: `stepwise_maintenance/step05_veto_time_axis/outputs_v3p5_centerfinger_fullstat_v2_exactpos_l1/step05_v3p5_centerfinger_l1_timeline_rates.csv`
