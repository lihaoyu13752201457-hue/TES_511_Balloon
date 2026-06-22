# fix5 Full-Stat Simulation Closure

- Status: `PASS_FIX5_FULLSTAT_CLOSURE`
- Final decision: `PASS_FIX5_REPLACES_V3P5`
- Geometry: `outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- Contract authority: `core_md/fix5_benchmarks.json`
- Old `new_geo_re` policy: `REPORT_ONLY_UNTIL_BENCHMARK_ALIGNMENT_IS_ALIGNED`
- Clean full-stat policy: `Clean full-stat fix5 closure; no append/merge promotion was used.`

## Decision

All automatic promotion thresholds are satisfied, including selected W2 delayed W/collimator-origin decomposition.

## Required Artifacts

- Source manifest: `outputs/reports/fix5_fullstat_v2/fix5_source_manifest.json`
- Benchmark alignment: `outputs/reports/fix5_fullstat_v2/fix5_benchmark_alignment.json` (`NOT_ALIGNED`)
- Verification verdict: `outputs/reports/fix5_fullstat_v2/fix5_verification_verdict.json` (`PASS_FIX5_PROMOTION`)
- Promotion decision: `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_promotion_decision.json` (`PASS_FIX5_REPLACES_V3P5`)
- W activation selected-rate audit: `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_w_activation_selected_w2_audit.json` (`PASS_FIX5_SELECTED_W_ACTIVATION_W2_AUDIT`)

## Comparison Table

| Metric | fix5 | sigma | v3p5 reference | fix5/v3p5 | old new_geo_re | Status |
|---|---:|---:|---:|---:|---:|---|
| W2 total selected background cps | 0.0392162265186 | 0.00500832932165 | 0.0629803618399 | 0.622673883938 |  | PASS_DECISIVE_VS_V3P5 |
| W2 prompt selected cps | 0.0366410230297 | 0.00498621167091 | 0.0590827246325 | 0.620164747946 | 0.0323247092031 | PASS_VS_V3P5_REPORT_ONLY_VS_OLD_NEW_GEO_RE |
| W2 delayed selected cps | 0.00257520348894 | 0.000470165680353 | 0.00389763720735 | 0.660708873593 | 0.151456825339 | PASS_VS_V3P5_REPORT_ONLY_VS_OLD_NEW_GEO_RE |
| W/collimator-origin W2 delayed selected cps | 0 |  |  |  |  | PASS_NOT_DOMINANT |
| W/collimator source activity Bq | 0.986079828757 |  |  |  |  | AUDITED_SOURCE_LEVEL_CONTEXT |
| Reference-flux signal cps | 0.0011858748075 |  | 0.0011811656294 | 1.00398689056 |  | PASS_SIGNAL_KEEP |
| Z20d | 7.79950030715 |  | 6.13039468758 | 1.27226723639 |  | PASS |
| F3(20d) ph cm^-2 s^-1 | 3.84640025881e-05 |  | 4.89364902732e-05 | 0.78599839043 |  | PASS |
| Old new_geo_re benchmark alignment | NOT_ALIGNED |  |  |  | ALIGNED required before old-new_geo_re gating | REPORT_ONLY |

## Key Checks

- W2 background: `0.0392162265186 +/- 0.00500832932165` cps.
- Prompt/delayed: `0.0366410230297` / `0.00257520348894` cps.
- W/collimator selected W2 delayed: `0` cps, fraction `0`.
- Signal keep vs v3p5: `1.00398689056`.
- Z20d / F3(20d): `7.79950030715` / `3.84640025881e-05`.

## Notes

- Full-stat results override the 1/10 screen.
- The historical old `new_geo_re` prompt/delayed values remain report-only because benchmark alignment is `NOT_ALIGNED`.
- This report does not overwrite current v3p5, BGO, or old `new_geo_re` authority outputs.
