# Prompt-511 Active BGO Collar Delayed Smoke

Status: `PASS_PROMPT511_ACTIVE_COLLAR_BGO_DELAYED_SMOKE`.

This is a delayed activation and Step05-like W2 smoke for the local
active BGO collar. It is not a final Step06--Step08 mission authority.

## Inputs

- active delayed SIM: `outputs/reports/prompt511_repack_smoke_20260617/runs/active_collar_bgo_delayed_transport_smoke_g1m_r2/DelayedDecayRPIPActiveCollarBgoSmokeGroundStateFixed.inc1.id1.sim.gz`
- active activity CSV: `outputs/reports/prompt511_repack_smoke_20260617/runs/active_collar_bgo_delay_fix_smoke_g1m_r2/groundstate_activity_corrections.csv`
- current Step05 reference: `stepwise_maintenance/step05_veto_time_axis/outputs_v3p5_centerfinger_fullstat_v2_exactpos_m50000_s260613_l1/step05_v3p5_centerfinger_l1_response_summary.json`
- current activity CSV: `runs/step02_delay_fix_v3p5_centerfinger_fullstat_v2_exactpos_m50000_s260613/groundstate_activity_corrections.csv`

## Active Delayed Transport

- SE/ID: `100000 / 100000`
- TE: `1150.02964 s`
- rate per delayed event: `0.000869542808 cps`
- geometry: `/home/ubuntu/TES_511_Balloon/outputs/reports/prompt511_repack_smoke_20260617/geometry_active_collar_bgo/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_active_bgo_collar_r4p25_5p95.geo.setup`

| W2 stage | events | cps | counting 1sigma cps |
|---|---:|---:|---:|
| raw line window | 23 | 0.0199995 | 0.00417018 |
| active-veto pass | 19 | 0.0165213 | 0.00379025 |
| side-Compton/FoV pass | 18 | 0.0156518 | 0.00368916 |

Current authority delayed W2 is `0.00389764 cps`; this smoke gives `0.0156518 cps`, ratio `4.01571`.

## Activation Inventory

Active-collar source-fix total activity: `85.4354165 Bq`; current fullstat source-fix total activity: `85.6366959 Bq`.

Active-collar smoke activity by material category:

| category | activity Bq | fraction |
|---|---:|---:|
| CsI | 68.2392 | 0.798723 |
| Cu | 8.77455 | 0.102704 |
| Al | 4.53033 | 0.0530263 |
| W | 2.77216 | 0.0324474 |
| Other | 0.978156 | 0.0114491 |
| BGO_collar | 0.141019 | 0.0016506 |

Current fullstat activity by material category:

| category | activity Bq | fraction |
|---|---:|---:|
| CsI | 69.3059 | 0.809301 |
| Cu | 8.69474 | 0.101531 |
| Al | 4.24786 | 0.0496033 |
| W | 2.5034 | 0.0292327 |
| Other | 0.884827 | 0.0103323 |

BGO collar self-activation in this smoke: `0.141019 Bq`, `0.0016506` of total.
Top BGO-collar nuclides: Ge-75 0.0542844 Bq, Ge-71 0.0324258 Bq, Bi-201 0.0271422 Bq, Tl-197 0.0271422 Bq, Bi-207 2.47366e-05 Bq, C-14 1.35549e-07 Bq.
Top active-smoke nuclides: I-128 65.1413 Bq, Cu-64 4.64113 Bq, Al-28 4.58703 Bq, W-187 2.55129 Bq, Mg-27 2.27634 Bq, Cs-134 1.14449 Bq.

Selected delayed W2 final-event diagnostics:

- primary nuclides by event: `{'Cu64': 13, 'Sb118': 2, 'Na24': 2, 'I122': 1}`
- first non-TES volumes: `{'ColdPlate_MXC_50mK_SD_anchor': 7, 'Cu_SubstrateSupport_SolidDisk_L0_deepest': 7, 'DR_MixingChamber_Cu': 2, 'ColdPlate_CP_100mK_intercept': 2}`
- top non-TES energy volumes: `{'ColdPlate_MXC_50mK_SD_anchor': 7, 'Cu_SubstrateSupport_SolidDisk_L0_deepest': 7, 'DR_MixingChamber_Cu': 2, 'ColdPlate_CP_100mK_intercept': 2}`
- top non-TES material categories: `{'Cu': 18}`

Selected Cu-volume activity cross-check:

- active selected volumes, selected nuclides: `0.949977 Bq`; current selected volumes, selected nuclides: `0.932133 Bq`.
- active selected volumes, all nuclides: `1.30756 Bq`; current selected volumes, all nuclides: `1.21173 Bq`.

## Combined Design-Smoke Read

| quantity | cps |
|---|---:|
| active-collar prompt projection | 0.0257845 |
| active-collar delayed W2 smoke | 0.0156518 |
| active prompt + delayed smoke | 0.0414363 |
| current authority background | 0.0629804 |
| old new_geo_re prompt total | 0.0323247 |

Interpretation: the active collar still looks promising for prompt suppression, but this delayed smoke does not close the mature-design case. The BGO collar self-activity is small, yet the delayed W2 central value is about 4x the current delayed authority and raises prompt+delayed to above the old new_geo_re prompt total. This may be a smoke-statistics/source sampling issue, but it is a decision-changing risk until a higher-stat delayed closure is done.

Boundary:

- The delayed transport uses the active-collar rebuilt activation source, not an old-inventory replay.
- The delayed W2 rate is normalized by 1 / TE_s from the delayed SIM, matching the current Step05 delayed-rate rule.
- The active-collar delayed transport is a 100k-trigger smoke from a g1m/r2 buildup inventory; the W2 event count is low.
- The delayed W2 central value is high enough to block an old-like combined background claim until a higher-stat delayed closure is done.
- Prompt projection, delayed smoke, and focused-signal smoke are not yet a common Step06-Step08 mission authority.
