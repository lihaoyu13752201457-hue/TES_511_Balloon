# Claude R2 Execution Report: TES_511_Balloon

Date: 2026-06-12

Scope: execute the actionable items in `CLAUDE_REVIEW_TES511_BALLOON_20260612_R2.md`
against the local `TES_511_Balloon` checkout.

## Status

`PASS_R2_V3P5_FULLSTAT_REPAIR_AND_SPATIAL_SIDECAR`

The new R2 P0 was fixed and rerun through the full rate-level chain:
Step05 -> Step06 -> Step07 -> Step08 -> 1 Ms comparison -> W2 closure.
The R2 high-value `spot_r90` analysis upgrade was also migrated as a v3p5
fullstat detector-coupled sidecar.

## Fixed Items

- Step05 prompt normalization now uses per-tag `1/sum(TT_tag)` instead of a
  single prompt time for all prompt particles.
- Step05 writes `prompt_normalization_audit.csv/json` and fails if any prompt
  tag has missing/multiple TT lines, wrong expected file count, or
  `rate * sum(TT_tag) != 1`.
- The cached Step05 event catalog prompt rates are refreshed from the per-tag
  audit when needed.
- Fullstat claim labels now carry `FULLSTAT_V2`, not stale `1OF10`.
- `compare_511_narrow_1Ms_20260612` was regenerated: the old `2.99e-5` TES
  point is explicitly `TES_511_Balloon_delayed_only_aspiration`, and the
  current v3p5 fullstat W2 point is `6.823006741638457e-05`.
- Source-builder audits now count TT lines as well as TT-bearing files; a
  concatenated dat file with multiple TT lines fails validation.
- v3p5 decay-source normalization audits were backfilled for both `1of10` and
  `fullstat_v2` raw/fixed source directories.
- README/Memory/workflow/current-progress docs now state that `1of10` is a
  compatibility label: gamma exposure about `1/10`, non-gamma about `1/80`,
  and generated particle count about `1/21.2`.
- Docs now state that v3p5 science normalization inherits scalar mainline
  `T_atm=0.739042`; the absolute 45 deg side-entry atmospheric line of sight
  has not been recomputed.
- The detector-coupled focus response builder now supports the v3p5 fullstat
  profile and measures side-entry spatial radii in the local side-window frame,
  not around the global origin.
- v3p5 fullstat `spot_r90` W2 spatial sidecar was built and folded over the
  Step06 time axis: `Z20d=8.175664736254516`, 20-day 3-sigma flux
  `3.669426397460591e-05 ph cm^-2 s^-1`.
- The root CubeSat Compton-telescope draft was moved to `old_md/templates/`.
- Git was initialized and the first controlled commit was prepared with large
  run products ignored.

## Current Fullstat Authority

| quantity | value |
| --- | ---: |
| Step05 W2 background | `0.07295764410312272 cps` |
| Step05 W2 signal at `1e-4 ph cm^-2 s^-1` | `0.0011811656293957314 cps` |
| Step06 W2 mission-mean background | `0.07304283195081326 cps` |
| Step08 W2 `Z20d` | `5.702213417976891` |
| Step08 W2 `T3` | `5.466869922289813 day` |
| Step08 W2 20-day 3-sigma flux | `5.261114904156606e-05 ph cm^-2 s^-1` |
| 1 Ms v3p5 W2 3-sigma flux | `6.823006741638457e-05 ph cm^-2 s^-1` |
| W2 leading background component | prompt `eplus`, `80` events, `0.0543377 cps`, `74.5%` |
| Spatial sidecar `spot_r90` radius | `1.0516422148529696 cm` |
| Spatial sidecar `spot_r90` background | `0.023251049574647638 cps` |
| Spatial sidecar `spot_r90` `Z20d` | `8.175664736254516` |
| Spatial sidecar `spot_r90` 20-day 3-sigma flux | `3.669426397460591e-05 ph cm^-2 s^-1` |

Do not quote the superseded R2-bad fullstat values:
`0.486136 cps`, `Z20d=2.20208`, `1.36235e-4`, `1.76837e-4`, or `89.3% eplus`.
They remain only in the `Project_Memory` misquote guardrail.

## Key Artifacts

- Step05 summary:
  `stepwise_maintenance/step05_veto_time_axis/outputs_v3p5_centerfinger_fullstat_v2_l1/step05_v3p5_centerfinger_l1_response_summary.json`
- Step05 prompt audit:
  `stepwise_maintenance/step05_veto_time_axis/outputs_v3p5_centerfinger_fullstat_v2_l1/prompt_normalization_audit.json`
- Step08 summary:
  `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2/step08_v3p5_centerfinger_time_dependent_summary.json`
- 1 Ms comparison:
  `stepwise_maintenance/step08_significance/outputs/performance_curve_comparison_1Ms/performance_curve_comparison_1Ms_summary.json`
- W2 closure:
  `outputs/reports/v3p5_fullstat_performance_w2_closure_20260612/v3p5_fullstat_performance_w2_closure_report.md`
- Narrow-line comparison:
  `outputs/reports/compare_511_narrow_1Ms_20260612/compare_511_narrow_1Ms.md`
- v3p5 detector-coupled focus response:
  `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/detector_coupled_focus_response.json`
- v3p5 fullstat spatial sidecar:
  `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2_spatial/v3p5_spatial_line_proxy.md`
- v3p5 R2 validator:
  `code/tools/validate_v3p5_fullstat_r2.py`

## Commands Run

```bash
python3 code/tools/build_v3p5_centerfinger_step05_l1_response.py --label fullstat_v2 --workers 8 --rebuild-cache
python3 stepwise_maintenance/step06_mission_time_variation/code/build_v3p5_centerfinger_step06_time_axis.py --label fullstat_v2
python3 stepwise_maintenance/step08_significance/code/build_v3p5_w2_background_source_breakdown.py --label fullstat_v2
python3 stepwise_maintenance/step07_source_cases/code/build_v3p5_centerfinger_step07_source_cases.py --label fullstat_v2
python3 stepwise_maintenance/step08_significance/code/build_v3p5_centerfinger_step08_time_dependent.py --label fullstat_v2
python3 stepwise_maintenance/step08_significance/code/build_performance_curve_comparison_1Ms.py --v3p5-label fullstat_v2
python3 code/tools/build_compare_511_narrow_1Ms.py
python3 code/tools/build_v3p5_fullstat_performance_w2_closure_report.py
python3 code/tools/backfill_v3p5_decay_source_audits.py
python3 stepwise_maintenance/step09_optics_bridge/code/build_detector_coupled_focus_response.py --profile v3p5_fullstat_v2
python3 stepwise_maintenance/step08_significance/code/build_v3p5_spatial_line_proxy.py
python3 code/tools/validate_v3p5_fullstat_r2.py
```

## Verification

- `python3 code/tools/validate_v3p5_fullstat_r2.py`:
  `PASS_V3P5_FULLSTAT_R2_VALIDATION`, `problems=[]`.
- `python3 -m py_compile` passed for the changed Step05, Step06, Step08,
  compare, backfill, source-builder, detector-response, spatial-sidecar, and
  validator scripts.
- Manual multi-TT guard smoke test passed for both
  `makedecaysourcewithplot_rpip.py` and `build_fixed_delay_source.py`: two
  files with three TT lines produced
  `tag=n has 3 TT lines across 2 files; expected exactly one TT per file`.
- Stale `1OF10` labels are absent from the fullstat Step06/Step08/closure
  authority products.
- R2-bad fullstat values are absent from current authority outputs; they remain
  only in the explicit `What Not To Misquote` guardrail.
- v3p5 spatial sidecar is included in `validate_v3p5_fullstat_r2.py`; the
  validator checks the local side-entry spatial frame, `spot_r90` radius,
  background, time-dependent `Z20d`, and 20-day flux.

## Remaining Boundary

- `spot_r90` is now migrated as a v3p5 fullstat detector-coupled sidecar. It
  is not yet a profile-likelihood analysis and does not replace the current
  hard-window W2 authority.
- Exact-position delayed-source sampling is still pending; current v3p5 delayed
  source uses legacy axisymmetric `RadialProfileBeam` compression.
- The old broad `validate_new_geo_re.py` remains a legacy validator. The new
  R2-specific validator covers the v3p5 fullstat invariants introduced here.
