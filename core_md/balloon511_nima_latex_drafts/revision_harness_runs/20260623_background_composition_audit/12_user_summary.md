# 12 User Summary

本轮 `background_composition_audit` harness 已完成。最终状态：

`AUDIT_COMPLETE_NO_BUG_FOUND`

## 结论

旧 `new_geo_re` 与当前 fix5 的 delayed 构成差异很大，但本轮没有发现当前 fix5 delayed 链条存在需要修复的、可复现的 normalization/provenance bug。默认 no-fix 路径成立，未修改代码、几何、source card、当前 authority outputs 或旧 `new_geo_re` 输出。

## 数字对齐

- W2 `510.58--511.42 keV` final/both:
  - old `new_geo_re`: total `0.184347 cps`, prompt `0.032234 cps`, delayed `0.152113 cps`, delayed fraction `82.5%`
  - current fix5: total `0.039216 cps`, prompt `0.036641 cps`, delayed `0.002575 cps`, delayed fraction `6.57%`
  - W2 delayed old/current about `59x`
- broad `480--550 keV` final:
  - old delayed `2.31224 cps`
  - current delayed `0.003176 cps`
  - old/current about `728x`
- current fix5 没有本轮指定 authority 中的 `100--10000 keV` apples-to-apples 表，因此标 `NOT_AVAILABLE`，没有硬凑比较。

## 主要原因排序

1. old `new_geo_re` delayed activity 很大，约 `624.27 Bq`，由 CsI active shield 的 I-128 主导；current fix5 fixed delayed activity 是 `85.45 Bq`。
2. old broad `480--550 keV`、old W2、current W2 是不同 window/stage，不能混作一个物理量。
3. old `new_geo_re` 与 current fix5 的 source surface / selection normalization 未对齐；benchmark alignment 是 `NOT_ALIGNED`，所以旧数值只能 report-only。
4. current delayed 单 seed W2 只有 30 个 selected events，但 PI-02 四采样合并达到 103 个 selected events，相对不确定度约 `9.85%`。
5. 当前 evidence 不支持 wrong geometry、per-family delayed over-normalization、activity/source mismatch 或 delayed cps 量纲错误。

## 文献 sanity check

X/XL-Calibur、511-CAM、SPI、COSI 文献支持两个 caveat：activation/delayed 在 SPI/COSI 这类宽视场 Ge 线谱仪中可以很重要；但这些绝对率和 delayed fraction 不能直接套到 pointed TES-Laue 窄线窗 final selection。511-CAM/X-Calibur 的 mass-scaling 是 gross prompt/cosmic/atmospheric background proxy，不是本项目 delayed activation inventory 的替代。

## 论文建议

可以写：current fix5 W2 final composition、delayed normalization audit trail、W/collimator selected-W2 为 0 的审计结果、以及外部文献的非转移性 caveat。

不要写：把 old `480--550 keV` delayed 当 current W2 delayed；把 old `new_geo_re` 当 current fix5 gate；或者给出 current `100--10000 keV` apples-to-apples claim。

## 产物

本轮产物全部位于：

`core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260623_background_composition_audit/`

关键文件：

- `03_current_vs_new_geo_re_rate_matrix.*`
- `04_delay_normalization_audit.*`
- `05_discrepancy_hypotheses.md`
- `06_literature_background_matrix.*`
- `07_pre_fix_verdict.md`
- `08_fix_execution_log.md`
- `09_review_auditor_report.md`
- `10_project_auditor_report.md`
- `11_gatekeeper_verdict.md`
