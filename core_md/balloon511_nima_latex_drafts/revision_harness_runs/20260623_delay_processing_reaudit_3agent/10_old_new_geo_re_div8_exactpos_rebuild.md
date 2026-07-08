# Old new_geo_re div8 exact-position delayed-source scratch rebuild

Date: 2026-06-23

## Purpose

Test whether the old `new_geo_re` delayed W2 excess is only the missing
non-gamma divide-by-8 normalization, or whether the old axis-collapsed delayed
source placement also inflated the result.

This is a scratch rebuild. It does not overwrite old `new_geo_re`, current v3p5,
BGO, or fix5 authority outputs.

## Inputs

- Corrected fixed source:
  `old/runs/step02_delay_fix_mainline_div8_review_20260612/activation_decay_day15_groundstate_fixed.source`
- Corrected normalization audit:
  `old/runs/step02_delay_fix_mainline_div8_review_20260612/normalization_audit_groundstate_fix.json`
- Old RP/IP buildup source of positions:
  `/home/ubuntu/codex_tes_511_sim/new_geo_re/runs/step02_buildup_equiv2602_aligned`
- Geometry:
  `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/geometry/XZTES_ADR_v4c_mkflange_cm/TibetTES_ADR_v4c_mkflange_cm.geo.setup`

## Source Rebuild Audit

Builder:
`code/tools/build_old_new_geo_re_div8_exactpos_source.py`

100k transport label:
`old_new_geo_re_div8_exactpos_m50000_t100k_s260623`

Source artifact:
`runs/step02_delay_fix_old_new_geo_re_div8_exactpos_m50000_t100k_s260623/activation_decay_day15_groundstate_fixed_exactpos.source`

Manifest:
`runs/step02_delay_fix_old_new_geo_re_div8_exactpos_m50000_t100k_s260623/exactpos_delayed_source_manifest.json`

Key checks:

- Fixed activity: `77.9991130692 Bq`
- PointSource blocks: `50,000`
- Flux per PointSource: `0.00155998226138 Bq`
- Eligible weighted RP/IP rows: `708,319`
- Missing `(VN, ZA)` fixed-source keys: `0`
- Weighted-table activity relative delta: `8.68e-13`
- Activity-weighted mean radius: `11.0597 cm`
- Drawn median radius: `11.8852 cm`
- Drawn fraction with `r < 1 cm`: `0.00234`

This confirms the rebuilt source is no longer the old axis-collapsed `r=0`
delayed source.

## Transport

SIM:
`runs/step02_delayed_transport_old_new_geo_re_div8_exactpos_m50000_t100k_s260623/DelayedDecayOldNewGeoReDiv8Exactpos_old_new_geo_re_div8_exactpos_m50000_t100k_s260623.inc1.id1.sim.gz`

Cosima log:
`runs/step02_delayed_transport_old_new_geo_re_div8_exactpos_m50000_t100k_s260623/cosima_transport_100k.log`

Transport summary:

- Requested triggers: `100,000`
- SIM `SE/ID/TS`: `100000 / 100000 / 1`
- SIM `TE`: `1277.260751 s`
- Primary activity time if no daughters: `1282.065860 s`
- Geometry record: old `new_geo_re` `.geo.setup`, absolute path above

An initial `1,000,000` trigger run under label
`old_new_geo_re_div8_exactpos_m50000_s260623` was intentionally interrupted
after stdout flooding made the PTY the bottleneck. It is not used for any rate
claim.

## W2 Delayed Selection

Analyzer:
`code/tools/analyze_old_new_geo_re_delayed_w2.py`

Selection summary:
`runs/step02_delayed_transport_old_new_geo_re_div8_exactpos_m50000_t100k_s260623/old_new_geo_re_div8_exactpos_w2_delayed_summary.json`

W2 window: `[510.58, 511.42] keV`

Using the old `new_geo_re` Step05 parser, `50 keV` active-shield threshold, and
Compton/FoV final selection:

| Case | W2 delayed final cps | Events | Note |
|---|---:|---:|---|
| Old axis source, uncorrected | `0.152113172691` | n/a | Previous inspection; includes missing non-gamma divide-by-8 and axis-collapsed source |
| Old axis source, scalar div8 | `0.0190141465864` | n/a | Previous inspection divided by 8 |
| Old div8 exact-position, this 100k run | `0.00469755294313` | `6` | `1 sigma = 0.00191777 cps` |
| Current fix5 exact-position full-stat | `0.00257520348894` | `30` | Current fix5 Step05 final delayed W2 |

Ratios:

- Old uncorrected axis / old div8 exact-position: `32.38`
- Old scalar-div8 axis / old div8 exact-position: `4.05`
- Old div8 exact-position / current fix5: `1.82`

## Interpretation

The divide-by-8 normalization was real, but it was not the whole discrepancy.
After applying div8 and rebuilding the old delayed source at exact RP/IP
positions, the W2 delayed rate drops another factor of about `4` relative to a
simple scalar-div8 correction of the old axis source.

The 100k exact-position result is low-statistics (`6` final W2 events), so the
`1.82x` ratio over current fix5 is not a robust separation. It does, however,
remove the previous apparent `~7x` post-div8 gap as a strong claim: most of that
gap was consistent with the old source-placement artifact plus low statistics,
not necessarily current-project underestimation.
