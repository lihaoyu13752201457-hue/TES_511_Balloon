# 11 Gatekeeper Verdict

ROLE = Final Gatekeeper
INDEPENDENCE = SINGLE_SESSION_DEGRADED

## Status

AUDIT_COMPLETE_NO_BUG_FOUND

One-sentence conclusion: 本轮 harness 完成了本地 rate/normalization 审计和外部文献 sanity check；旧 `new_geo_re` 与当前 fix5 的 delayed 构成差异主要来自窗口/筛选/normalization 未对齐和物理模型/活化库存差异，当前 fix5 delayed 链条未发现满足修复门槛的可复现 bug。

## Gate Inputs

- PASS: required Local Data Auditor artifacts exist and report `INDEPENDENCE = SUBAGENT`. Evidence: `03_current_vs_new_geo_re_rate_matrix.md:3`, `04_delay_normalization_audit.md:3`, `05_discrepancy_hypotheses.md:3`.
- PASS: required Literature Auditor artifact exists and reports public literature access with `INDEPENDENCE = SUBAGENT`. Evidence: `06_literature_background_matrix.md:3`, `06_literature_background_matrix.md:4`, `06_literature_background_matrix.md:5`.
- PASS: Pre-Fix Gatekeeper set `ENTER_FIX = false`, so the no-fix path is the only authorized path. Evidence: `07_pre_fix_verdict.md:8`, `07_pre_fix_verdict.md:14`, `08_fix_execution_log.md:6`, `08_fix_execution_log.md:8`.
- PASS_WITH_WARNINGS: Review and Project Auditors accepted the harness outcome with explicit caveats, not blocking failures. Evidence: `09_review_auditor_report.md:8`, `09_review_auditor_report.md:81`, `10_project_auditor_report.md:8`, `10_project_auditor_report.md:60`.

## Apples-To-Apples Rate Summary

| Comparison | old `new_geo_re` | current fix5 | Interpretation |
|---|---:|---:|---|
| W2 `510.58--511.42 keV` final/both total | `0.18434717748640367 cps` | `0.0392162265186315 cps` | Current is lower, but old benchmark remains report-only because alignment is `NOT_ALIGNED`. Evidence: `03_current_vs_new_geo_re_rate_matrix.md:17`, `03_current_vs_new_geo_re_rate_matrix.md:9`. |
| W2 prompt | `0.03223400479533992 cps` | `0.036641023029691425 cps` | Same order; current/old `1.1367`. Evidence: `03_current_vs_new_geo_re_rate_matrix.md:18`. |
| W2 delayed | `0.15211317269106375 cps` | `0.0025752034889400762 cps` | Old/current delayed `59.07x`; old delayed fraction `82.5%`, current `6.57%`. Evidence: `03_current_vs_new_geo_re_rate_matrix.md:19`. |
| Broad `480--550 keV` final delayed | `2.31224086683797 cps` | `0.003176084303026095 cps` | Old/current delayed `728x`; this broad-window value must not be used as W2. Evidence: `03_current_vs_new_geo_re_rate_matrix.md:22`, `05_discrepancy_hypotheses.md:15`. |
| `100--10000 keV` | old table available | current `NOT_AVAILABLE` | No forced comparison. Evidence: `03_current_vs_new_geo_re_rate_matrix.md:23`, `03_current_vs_new_geo_re_rate_matrix.md:24`. |

## Delayed Difference: Ranked Causes

1. PHYSICAL_MODEL_DIFFERENCE: old delayed inventory is much larger and CsI/I-128 dominated; current fix5 fixed activity is much smaller and W/collimator selected W2 contribution is zero. Evidence: `04_delay_normalization_audit.md:20`, `04_delay_normalization_audit.md:22`, `04_delay_normalization_audit.md:28`, `04_delay_normalization_audit.md:30`, `04_delay_normalization_audit.md:13`.
2. DEFINITION_ONLY: old broad `480--550 keV` final rates are not W2 line-window rates, and source-surface/normalization definitions differ. Evidence: `05_discrepancy_hypotheses.md:15`, `05_discrepancy_hypotheses.md:17`.
3. STALE_OR_PROVENANCE_RISK: old `new_geo_re` selection/normalization alignment is explicitly unverified for fix5 gates. Evidence: `03_current_vs_new_geo_re_rate_matrix.md:9`, `05_discrepancy_hypotheses.md:35`.
4. STATISTICAL_LIMITATION: current single-seed W2 delayed has 30 selected events, improved to 103 combined selected events in PI-02 convergence. Evidence: `05_discrepancy_hypotheses.md:29`, `04_delay_normalization_audit.md:14`.
5. PROBABLE_BUG: not supported. Evidence: `05_discrepancy_hypotheses.md:39`, `05_discrepancy_hypotheses.md:41`, `05_discrepancy_hypotheses.md:43`, `05_discrepancy_hypotheses.md:45`, `05_discrepancy_hypotheses.md:47`, `05_discrepancy_hypotheses.md:55`.

## Normalization And Provenance Verdict

- PASS: current fix5 geometry provenance is clean for source cards, job sources, prompt/buildup SIM headers, delayed SIM header, and signal SIM header. Evidence: `04_delay_normalization_audit.md:9`.
- PASS: current prompt normalization follows `1/sum(TT)`. Evidence: `04_delay_normalization_audit.md:10`.
- PASS: current delayed ground-state correction and per-family TT division guard pass. Evidence: `04_delay_normalization_audit.md:11`.
- PASS: current exact-position M-sampling inventory passes. Evidence: `04_delay_normalization_audit.md:12`.
- PASS: current W/collimator activation was audited and is not a selected W2 component. Evidence: `04_delay_normalization_audit.md:13`.
- NO_BUG: current delayed cps dimension error is not supported. Evidence: `04_delay_normalization_audit.md:15`, `05_discrepancy_hypotheses.md:47`.

## Literature Sanity Check

PASS_WITH_CAVEATS: public literature supports both sides of the sanity check: activation/delayed backgrounds can dominate Ge wide-field line instruments, while pointed shielded narrow-window TES-Laue selection can plausibly have a much smaller final delayed component if local audits pass. Evidence: `06_literature_background_matrix.md:47`, `06_literature_background_matrix.md:48`, `06_literature_background_matrix.md:49`, `06_literature_background_matrix.md:50`, `06_literature_background_matrix.md:51`, `06_literature_background_matrix.md:52`, `06_literature_background_matrix.md:67`, `06_literature_background_matrix.md:69`.

WARN: do not transfer absolute rates or delayed fractions directly from X/XL-Calibur, SPI, or COSI to this project. Evidence: `06_literature_background_matrix.md:49`, `06_literature_background_matrix.md:50`, `06_literature_background_matrix.md:54`, `06_literature_background_matrix.md:58`.

## Modification Verdict

NO_FIX_EXECUTED: no project code, geometry, source card, current fix5/v3p5 authority output, or old `new_geo_re` output should be considered modified by this harness. Evidence: `07_pre_fix_verdict.md:29`, `07_pre_fix_verdict.md:31`, `08_fix_execution_log.md:6`, `08_fix_execution_log.md:10`.

## Paper Guidance

Should write into paper/supporting material:

- Current fix5 W2 selected background composition: total `0.039216 cps`, prompt `0.036641 cps`, delayed `0.002575 cps`, with delayed low-count caveat and PI-02 convergence support. Evidence: `03_current_vs_new_geo_re_rate_matrix.md:17`, `03_current_vs_new_geo_re_rate_matrix.md:18`, `03_current_vs_new_geo_re_rate_matrix.md:19`, `04_delay_normalization_audit.md:14`.
- Delayed normalization audit trail: geometry provenance, `1/sum(TT)` prompt rule, ground-state/per-family division guard, exact-position M-sampling, W/collimator selected-W2 audit. Evidence: `04_delay_normalization_audit.md:9`, `04_delay_normalization_audit.md:10`, `04_delay_normalization_audit.md:11`, `04_delay_normalization_audit.md:12`, `04_delay_normalization_audit.md:13`.
- Literature caveat: SPI/COSI activation dominance is relevant sanity context, but not transferable as an absolute-rate constraint for this pointed TES-Laue final selection. Evidence: `06_literature_background_matrix.md:49`, `06_literature_background_matrix.md:69`.

Should not write into paper as a current claim:

- Old broad `480--550 keV` delayed `2.31224 cps` as if it were current W2 delayed. Evidence: `03_current_vs_new_geo_re_rate_matrix.md:22`, `05_discrepancy_hypotheses.md:15`.
- Old `new_geo_re` prompt/delayed values as fix5 pass/fail gates while benchmark alignment is `NOT_ALIGNED`. Evidence: `03_current_vs_new_geo_re_rate_matrix.md:9`, `05_discrepancy_hypotheses.md:35`.
- `100--10000 keV` current apples-to-apples comparison, because current authority marks it `NOT_AVAILABLE`. Evidence: `03_current_vs_new_geo_re_rate_matrix.md:23`, `03_current_vs_new_geo_re_rate_matrix.md:24`.

## Final State

AUDIT_COMPLETE_NO_BUG_FOUND. The harness should be closed as an audit/no-fix run, with warnings retained for `100--10000 keV` unavailability, old/current benchmark non-alignment, and low-count delayed statistics.
