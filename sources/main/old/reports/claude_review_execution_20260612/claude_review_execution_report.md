# Claude Review Execution Report

Date: 2026-06-12

Status: `P0_SOURCE_NORMALIZATION_REVIEW_EXECUTED`

This report records the local execution of
`CLAUDE_REVIEW_TES511_BALLOON_20260612.md`.

## P0 Finding Reproduced

The old DEMO2/mainline delayed source was confirmed to carry an `x8.0116`
multi-rep normalization inflation for I-128:

| Case | I-128 RP count | TT s | Production rate /s | Fixed-source I-128 Bq | Ratio |
| --- | ---: | ---: | ---: | ---: | ---: |
| old mainline DEMO2 | 288363 | 4332.129 | 66.5638 | 533.28 | 8.0116 |
| v3p5 fullstat_v2 | 97200 | 1473.674 | 65.9576 | 66.0018 | 1.0006 |
| v3p5 1of10 | 1191 | 18.338 | 64.9475 | n/a | n/a |

The physics production rates are consistent at about `66/s`; the old mainline
source activity was not.

## Code Guards Added

- `code/tools/makedecaysourcewithplot_rpip.py`
  - Adds tag/file-count normalization audit.
  - Uses mean TT per particle tag instead of last-file overwrite.
  - Supports `--gamma-div auto`.
  - Fails on file-count/divisor mismatch unless `--allow-div-mismatch` is set.
  - Writes `normalization_audit_dayXX.{csv,json}`.

- `code/tools/build_fixed_delay_source.py`
  - Adds the same normalization audit for the ground-state fixed-source
    post-processor.
  - Writes `normalization_audit_groundstate_fix.{csv,json}`.
  - Fails on mismatch before silently producing a fixed source.

Syntax check passed:

```bash
python3 -m py_compile code/tools/build_fixed_delay_source.py code/tools/makedecaysourcewithplot_rpip.py
```

Intentional failure check passed: one neutron dat file with `--non-gamma-div 8`
now exits with `tag=n has 1 files but division=8`.

## Mainline Div-Corrected Source Check

The old mainline DEMO2 buildup dat files were reread with `--non-gamma-div 8`
and `--gamma-div auto`.

Outputs:

- Raw source:
  `runs/step02_decay_source_mainline_div8_review_20260612/activation_decay_day15.source`
- Ground-state fixed source:
  `runs/step02_delay_fix_mainline_div8_review_20260612/activation_decay_day15_groundstate_fixed.source`
- Raw audit:
  `runs/step02_decay_source_mainline_div8_review_20260612/normalization_audit_day15.csv`
- Fixed-source audit:
  `runs/step02_delay_fix_mainline_div8_review_20260612/normalization_audit_groundstate_fix.csv`

Results:

| Quantity | Value |
| --- | ---: |
| Raw total activity | 78.0351026821 Bq |
| Raw I-128 activity | 66.6294237698 Bq |
| Ground-state fixed total activity | 77.9991130692 Bq |
| Ground-state fixed I-128 activity | 66.6294237694 Bq |

The corrected old-mainline source is therefore close to the v3p5 `~85-86 Bq`
source scale, not the stale `624.27 Bq` scale.

## BGO Source-Level Check

The external repaired BGO full-store source in `../new_geo_re_2` was audited
locally from this checkout with the same fixed-source guard.

Output:

- `runs/step02_bgo_delay_fix_div8_review_20260612/source_fix_summary.json`
- `runs/step02_bgo_delay_fix_div8_review_20260612/normalization_audit_groundstate_fix.csv`

Results:

| Quantity | Value |
| --- | ---: |
| External raw BGO source activity | 17.2369743619 Bq |
| Local mean-TT/auto-gamma fixed activity | 17.1837179460 Bq |

The repaired BGO source does not show a source-level `x8` normalization
inflation. The remaining BGO blocker is downstream: external-branch Step06,
Step07, Step08, Route B, validator, and BGO-vs-CsI report are still stale until
rerun against the refreshed BGO Step05 authority.

## Documentation And Report Updates

Updated documents now mark the old DEMO2/mainline numbers as legacy pre-fix
provenance:

- `core_md/Project_Memory.md`
- `core_md/README.md`
- `core_md/VALIDATION.md`
- `core_md/workflow.md`
- `core_md/ROUTE_B_DIFFUSE_SUPPLEMENT_20260602.md`

The 1 Ms performance comparison now labels DEMO2 curves as legacy pre-fix:

- `stepwise_maintenance/step08_significance/outputs/performance_curve_comparison_1Ms/performance_curve_comparison_1Ms.csv`
- `stepwise_maintenance/step08_significance/outputs/performance_curve_comparison_1Ms/performance_curve_comparison_1Ms_summary.json`
- `stepwise_maintenance/step08_significance/outputs/performance_curve_comparison_1Ms/performance_curve_comparison_1Ms.png`

The v3p5 full-stat closure report was regenerated:

- `outputs/reports/v3p5_fullstat_performance_w2_closure_20260612/v3p5_fullstat_performance_w2_closure_report.md`
- `outputs/reports/v3p5_fullstat_performance_w2_closure_20260612/report.html`
- `outputs/reports/v3p5_fullstat_performance_w2_closure_20260612/v3p5_fullstat_performance_w2_closure_summary.json`

Status from regenerated reports:

- `PASS_PERFORMANCE_CURVE_COMPARISON_1MS`
- `PASS_V3P5_FULLSTAT_PERFORMANCE_W2_CLOSURE`

Key 1 Ms values after relabeling:

| Case | 3 sigma flux ph cm^-2 s^-1 |
| --- | ---: |
| v3p5 W2 fullstat_v2 | 1.7683729998834282e-4 |
| DEMO2 legacy W2 line | 1.441677969479969e-4 |
| DEMO2 legacy W2 spot_r90 | 8.748416439180168e-5 |
| INTEGRAL/SPI | 5.0e-5 |
| COSI scaled to 1 Ms | 9.53340904398841e-5 |
| 511-CAM Fig.11 | 2.7e-6 |

## Remaining Boundaries

- The old mainline Step05+ chain was not rerun; old DEMO2 downstream numbers
  remain frozen as legacy pre-fix records.
- v3p5 fullstat_v2 remains the current closed rate-level baseline in this
  checkout.
- BGO source-level normalization is locally audited, but the external BGO
  downstream comparison remains stale.
- `git init` / first commit and the analytic I-128 self-shielding anchor rebuild
  are still P1 tasks, not completed here.
