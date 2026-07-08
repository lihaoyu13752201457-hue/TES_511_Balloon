# 新会话提示词：本底构成差异审计 harness（v1）

用途：把本文档整段交给一个新的 Codex/GPT 工程会话。目标是解释为什么旧 `new_geo_re` 与当前 `/home/ubuntu/TES_511_Balloon` 项目的本底构成差异极大，尤其是 delayed/activation 本底；同时结合 X-Calibur/511-CAM、SPI、COSI 等公开项目的本底构成经验做 sanity check。**本轮默认只检查和审计，不修改。只有在发现当前项目 delayed 链条存在明确、可复现、可定位的项目错误时，才允许做最小修复。**

请用中文向用户汇报。项目产物可用中文或英文，但关键 verdict 必须清楚。

---

## 0. 总目标

完成一个多角色 harness/loop engineering 审计：

1. 对齐旧 `new_geo_re` 与当前 fix5/v3p5 项目的本底口径，解释为什么构成悬殊，尤其是 delayed 本底为什么从旧项目主导变成当前选后很小。
2. 对照 X-Calibur/511-CAM、SPI、COSI 等公开文献中的 prompt/activation/delayed 本底构成，判断当前项目构成是否物理上异常。
3. 让新 session 完整复习项目、读懂 fix5 simulation closure 方法和当前论文/项目证据链。
4. 先检查，不上来修改；若 delayed 链条有明确错误，再用最小作用域修复，并用独立审计闭环。

**本轮不是：**

- 不是重新优化几何。
- 不是重新写论文正文。
- 不是用旧 `new_geo_re` 的数字直接替代当前项目。
- 不是为了让 delayed/prompt 构成符合某个预期而调参。
- 不是泛泛文献综述；文献只用于判断当前本底构成是否合理。

---

## 1. 起始观察，必须重新核验

以下只是用户发现的问题和上一轮快速读数，**不是权威结论**。新 session 必须从文件重新核验：

- 旧 `new_geo_re` Step09 W2 窄窗 `W2_511_pm_420eV`、`both` stage：
  - total `~0.184347 cps`
  - prompt `~0.032234 cps`
  - delayed `~0.152113 cps`
  - delayed fraction `~82.5%`
- 旧 `new_geo_re` day15 480--550 keV final：
  - prompt `~0.05357 cps`
  - delayed `~2.31224 cps`
  - delayed fraction `~97.7%`
- 当前 fix5 selected W511 final：
  - prompt `~0.036641 cps`
  - delayed `~0.002575 cps`
  - delayed fraction `~6.6%`

这三个数字看起来不在同一个物理/选择口径上。本 harness 的核心任务就是把这个差异拆清楚：哪些是口径差异，哪些是几何/材料/选择差异，哪些可能是 normalization 或代码错误。

---

## 2. 必读文件，按顺序读

先读项目入口和 fix5 simulation closure 方法：

1. `AGENTS.md` 或当前会话自动注入的 AGENTS 指令。
2. `core_md/METHOD_FIX5_SIM_CLOSURE.md`
3. `core_md/GUIDE_FIX5_SIM_CLOSURE_FOR_CODEX_20260621.md`
4. `core_md/CONSTRAINTS_FIX5_SIM_CLOSURE.md`
5. `core_md/PRE_PROMPT_FIX5_SIM_CLOSURE_20260621.md`
6. `core_md/fix5_benchmarks.json`

再读当前论文/项目证据链：

7. `core_md/balloon511_nima_latex_drafts/paper_evidence_manifest_20260623.json`
8. `core_md/balloon511_nima_latex_drafts/source_normalization_audit_20260623.json`
9. `core_md/balloon511_nima_latex_drafts/simulation_config_authority_20260623.json`
10. `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_promotion_decision.json`
11. `outputs/reports/fix5_immediate_fixes_20260623/delayed_selected_rate_convergence.json`，若存在。
12. 当前 Step05 response summary：
    `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_response_summary.json`
13. 当前 Step05 rates CSV：
    `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_rates.csv`

再读旧 `new_geo_re` 权威/历史文件：

14. `/home/ubuntu/codex_tes_511_sim/new_geo_re/Project_Memory.md`
15. `/home/ubuntu/codex_tes_511_sim/new_geo_re/CC48_REVIEW_LOG.md`
16. `/home/ubuntu/codex_tes_511_sim/new_geo_re/CODEX_A_SERIES_EXECUTION_REPORT_20260611.md`
17. `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/day15_complete_report/complete_day15_summary.json`
18. `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/day15_complete_report/image8_like_component_rates_with_science.csv`
19. `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/day15_complete_report/timeline_spectrum_480_550_rates.csv`
20. `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/day15_complete_report/timeline_spectrum_100_10000_rates.csv`
21. `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/day15_complete_report/activation_inventory_day15_after_groundstate_fix.csv`
22. `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step09_optics_bridge/outputs/non_xray_background_w1_w2_veto_table.csv`

只在需要核对论文 claim 是否受影响时读：

23. `core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.tex`
24. `core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_zh.tex`

要求：

- `core_md/fix5_benchmarks.json` 是本仓库中 old `new_geo_re` 和 current v3p5/fix5 benchmark 的机器可读权威。若 prose 与 JSON 冲突，先信 JSON，再追溯生成报告。
- 不得仅凭目录名、记忆或上一轮回答做结论。
- 如果 `.pkl` 因 `numpy` 版本无法读取，不要强行修环境；优先使用 JSON/CSV authority，并把 `.pkl` 读取失败记为非阻断 caveat。

---

## 3. 外部文献要求

必须使用公开文献/项目资料来做 sanity check。若环境可联网，必须搜索并引用来源；若环境不可联网，写 `LITERATURE_ACCESS_BLOCKED` 并只列待查问题，不得凭记忆造数。

优先使用：

- X-Calibur / XL-Calibur balloon polarimeter background papers or technical papers。
- 511-CAM 相关论文或技术报告，特别是它如何用 X-Calibur 本底结果做质量/本底替换估计。
- INTEGRAL/SPI background/instrument papers，尤其是 activation/delayed/internal background 对 511 keV 分析的影响。
- COSI balloon/satellite background、activation、instrument response、anticoincidence papers。
- 如用户写 `cois`，按 `COSI` 处理，但在报告中标注这是拼写归一。

文献矩阵必须区分：

- prompt cosmic/instrumental continuum
- atmospheric gamma/neutron/charged-particle prompt
- activation/delayed radioactive decay
- anticoincidence/veto 后残留
- line-window versus broad-band/spectrum
- all-sky diffuse mapping instrument versus pointed focusing instrument

禁止：

- 不得把 SPI/COSI 的在轨/气球本底绝对率直接套到本项目。
- 不得把 X-Calibur 的硬 X-ray polarimeter 本底直接当作 511 keV TES-Laue 本底。
- 不得忽略质量、材料、能窗、轨道/气球高度、探测器类型、反符合定义的差异。

---

## 4. 产物目录

新建并只写入本轮产物：

`core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260623_background_composition_audit/`

必须产物：

- `00_startup_reading_log.md`
- `00_git_baseline.txt`
- `01_local_inventory_map.md`
- `02_apples_to_apples_plan.md`
- `03_current_vs_new_geo_re_rate_matrix.md`
- `03_current_vs_new_geo_re_rate_matrix.json`
- `04_delay_normalization_audit.md`
- `04_delay_normalization_audit.json`
- `05_discrepancy_hypotheses.md`
- `06_literature_background_matrix.md`
- `06_literature_background_matrix.json`
- `07_pre_fix_verdict.md`
- `08_fix_execution_log.md`，仅当进入修复阶段时创建；否则写一行 `NO_FIX_EXECUTED`。
- `09_review_auditor_report.md`
- `10_project_auditor_report.md`
- `11_gatekeeper_verdict.md`
- `12_user_summary.md`

若发现明确 bug 并修复，项目侧新产物必须写入新目录，不能覆盖旧 authority。例如：

- `outputs/reports/background_composition_audit_20260623/`
- `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_background_audit_20260623/`

---

## 5. 角色分工与独立性

如果环境支持 subagent/multi-agent，优先使用真实 subagents。若没有，就在主会话中顺序模拟角色，但每个角色开始时必须只重读自己允许的 artifacts，不得凭前一角色的推理审自己。

所有 verdict 必须带 `INDEPENDENCE = SUBAGENT` 或 `INDEPENDENCE = SINGLE_SESSION_DEGRADED`。

**quote rule：** 任何 `PASS/WARN/FAIL/BUG/NO_BUG` 判定必须附源文件路径 + 行号，或 JSON pointer/CSV 行 + 值。没有引用的判定无效。

| 角色 | 写 | 只许读 | 禁止 |
|---|---|---|---|
| Orchestrator | 00/01/02/12 | 必读文件、git status、产物目录 | 不裁定物理结论；不做修复 |
| Local Data Auditor | 03/04/05 | 当前 fix5/v3p5 输出、旧 `new_geo_re` 输出、脚本只读 | 不修改任何代码/数据 |
| Literature Auditor | 06 | 公开文献、项目论文引用、用户给定项目名 | 不用记忆造数；不直接套用外部率 |
| Pre-Fix Gatekeeper | 07 | 03/04/05/06 | 只判定是否进入修复；不写代码 |
| Fix Executor | 08 + 新修复产物 | 07 明确列出的 bug 和允许修改路径 | 无 07 放行不得修改；不得改几何；不得覆盖 authority |
| Review Auditor | 09 | 03--08、外部文献矩阵 | 不修改产物；审计是否回答用户目标 |
| Project Auditor | 10 | 03--08、`fix5_benchmarks.json`、源 JSON/CSV/脚本 | 不修改产物；审计是否与项目约束冲突 |
| Final Gatekeeper | 11 | 03--10 | 纯函数裁定最终状态 |

---

## 6. 执行协议

### Phase 0：启动和冻结

1. 建产物目录。
2. 保存 `00_git_baseline.txt`：`git status --porcelain`、关键输入文件 hash、关键输出目录 mtime/hash 摘要。
3. 按 §2 读文件，写 `00_startup_reading_log.md`。
4. 写 `01_local_inventory_map.md`：列出旧 `new_geo_re` 和当前项目的所有相关本底清单、rate table、activation inventory、normalization artifacts。
5. 写 `02_apples_to_apples_plan.md`：定义要比较的口径矩阵：
   - energy: all / 100--10000 / 480--550 / W1 / W2 `510.58--511.42 keV`
   - stage: raw / active-veto or scintillator / Compton-FoV / both/final
   - stream: prompt / delayed / science / mixed
   - value: cps / selected events / effective N / relative uncertainty
   - normalization: prompt exposure/TT, delayed activity/decay sampling, source surface/solid angle

Phase 0 只允许写 harness 文档，不得修改代码或运行新 MC。

### Phase 1：本地数据重建

Local Data Auditor 重建 `03_current_vs_new_geo_re_rate_matrix.*`：

- 从旧 `new_geo_re` day15 complete report 重建 broad-band 和 480--550 表。
- 从旧 `new_geo_re` Step09 表重建 W1/W2 line-window 表。
- 从当前 fix5 Step05 summary/rates 重建同样口径的表。
- 若当前项目没有同一口径，标 `NOT_AVAILABLE`，不得拿不同口径硬比。
- 对每个数字写 source path、JSON pointer 或 CSV 行。

同时写 `04_delay_normalization_audit.*`：

- old `new_geo_re` delayed activity total、dominant nuclides、dominant volumes、source blocks、ground-state fix。
- current fix5 delayed activity/source activity、selected events、M-sampling/position sampling、NUBASE correction、per-family TT division guard。
- prompt normalization 的 `sum(TT)` / source surface / far-field 设置。
- delayed cps 的计算链：activity Bq -> simulated decays -> selected events/weights -> cps。
- 检查是否有明显量纲错误，例如把 `TE_s` 当 exposure、把 `1e6` decays 当 seconds、重复乘/除 source activity、错用旧 geometry/source header、错用 broad window 当 line window。

再写 `05_discrepancy_hypotheses.md`，把差异归类：

- `DEFINITION_ONLY`：能窗/筛选/stage/source normalization 不同。
- `PHYSICAL_MODEL_DIFFERENCE`：材料、活化体积、veto 设计、几何质量、source-position 分布导致。
- `STATISTICAL_LIMITATION`：selected events 太少或 uncertainty 太大。
- `STALE_OR_PROVENANCE_RISK`：旧报告或当前报告 provenance 不足。
- `PROBABLE_BUG`：有具体文件、字段、公式、代码行支持的错误。

### Phase 2：外部项目 sanity check

Literature Auditor 写 `06_literature_background_matrix.*`：

- 每个项目至少记录：instrument type、energy band/window、environment、detector/shield material、activation/delayed 是否重要、prompt 是否重要、veto/anticoincidence、是否可与本项目比较。
- 对 X-Calibur/511-CAM，特别检查“用 X-Calibur 本底结果按质量替换估计”的上下文：它估计的是 prompt、activation、总本底，还是某个能段/材料的 proxy。
- 对 SPI/COSI，重点看 511 keV 附近 activation/instrumental lines 与 delayed/internal background 对 line analysis 的影响，但必须说明这些是宽视场/编码孔/Compton 仪器，不能直接给本项目绝对率。
- 给出一节 `What literature would make suspicious`：哪些文献事实会让当前 delayed 很小显得异常；哪些事实会让旧 `new_geo_re` delayed 主导显得合理。

### Phase 3：修复前裁定

Pre-Fix Gatekeeper 写 `07_pre_fix_verdict.md`。

默认结论应为 `NO_FIX_YET`，除非满足全部条件：

```
ENTER_FIX =
  至少两个独立角色指出同一个 PROBABLE_BUG
  ∧ bug 有明确文件/字段/代码行/公式证据
  ∧ bug 会显著影响 current delayed 或 prompt/delayed composition
  ∧ 修复作用域可控，不需要重新设计几何
  ∧ 可以写入新输出目录，不覆盖 authority
```

若 `ENTER_FIX = false`：

- `08_fix_execution_log.md` 写 `NO_FIX_EXECUTED`。
- 继续 Phase 5 审计和最终报告。

若 `ENTER_FIX = true`：

- `07_pre_fix_verdict.md` 必须列出允许修改的 exact files、允许新建的 exact output dirs、禁止触碰的 frozen paths、验证命令。
- Fix Executor 只执行这些修改。

### Phase 4：条件修复

仅当 §Phase 3 放行时执行。

Fix Executor 要求：

- 用最小补丁修正具体错误。
- 不改几何。
- 不覆盖旧 `new_geo_re`、current v3p5、fix5 authority outputs。
- 新输出目录必须带 `background_composition_audit_20260623` 或同等清楚 tag。
- 修复后重新生成受影响的 JSON/CSV summary。
- 写 `08_fix_execution_log.md`：改了什么、为什么、命令、前后数字、验证结果、仍不确定项。

如果修复需要昂贵 full-stat MC，先做最小 reproducer 或 1/10 screen，并在 `08` 标 `BLOCKED_NEEDS_MC`；不要伪造 full-stat 结论。

### Phase 5：独立审计

Review Auditor 写 `09_review_auditor_report.md`：

- 是否回答了用户的四个目标。
- 是否真正解释 delayed 悬殊，而不是只列数字。
- 是否合理结合 X-Calibur/511-CAM、SPI、COSI。
- 是否遵守“先检查，不上来修改”。
- 如果进入修复，修复是否确实由明确 bug 触发。

Project Auditor 写 `10_project_auditor_report.md`：

- 是否遵守 `fix5_benchmarks.json` 和 fix5 closure contract。
- 是否混淆 old `new_geo_re` coarse screen 与 current v3p5/fix5 promotion bar。
- 是否把不同 window/stage/source normalization 硬比。
- 是否触碰冻结 authority outputs。
- 如果修复，source/SIM header/geometry/provenance 是否正确。

### Phase 6：最终 gate

Final Gatekeeper 写 `11_gatekeeper_verdict.md`，状态只能取：

- `AUDIT_COMPLETE_NO_BUG_FOUND`
- `AUDIT_COMPLETE_BUG_SUSPECTED_NO_FIX`
- `AUDIT_COMPLETE_BUG_FIXED_WITH_NEW_OUTPUTS`
- `BLOCKED_LITERATURE_ACCESS`
- `BLOCKED_MISSING_LOCAL_AUTHORITY`
- `FAIL_HARNESS_VIOLATION`

Gatekeeper 必须给出：

- 一句话结论。
- old `new_geo_re` vs current 项目的 apples-to-apples rate matrix 摘要。
- delayed 差异的主因排序。
- 外部文献 sanity check 的结论。
- 是否修改了项目；若修改，列 exact files 和验证。
- 哪些内容应该/不应该写入论文。

Orchestrator 最后根据 `11` 写 `12_user_summary.md`，并向用户中文汇报。

---

## 7. 判定标准

### 可接受解释

可以判为“差异合理/主要是口径或物理模型差异”的情况包括：

- 旧 `new_geo_re` 数字来自 broad 480--550 或 Step09 W2，但当前数字来自不同 line window/stage。
- 旧 `new_geo_re` delayed 由 CsI active shield 的 I-128 等活化主导，而当前几何/材料/selection 显著减少这些 delayed selected events。
- 当前 final selection 对 delayed 有强 rejection，而 prompt 511-line-like events 更容易留在 W511。
- 旧 `new_geo_re` 的 source-surface/far-field normalization 与当前 fix5 不 aligned，因此只能作为历史参考。

### 必须标红的问题

以下任一情况必须标 `PROBABLE_BUG` 或 `STALE_OR_PROVENANCE_RISK`：

- 当前 delayed source card 或 SIM header 指向错误几何。
- delayed source activity 与 source manifest/summary 不一致，且不能由 decay sampling 解释。
- cps 计算中重复乘或漏乘 activity、exposure、TT、decay count。
- `1e6` decays、`TE_s`、`TS/SE` 被误当成物理 exposure。
- broad window 的 delayed rate 被拿来和 W511 line-window prompt 比。
- old `new_geo_re` stale report 被当作当前 authority。
- 论文-facing 文件使用未审计旧数字。

---

## 8. 开始时对用户说的话

新 session 开始执行时，先对用户说：

“我将按 background-composition audit harness 执行：先冻结当前状态并读取 fix5 方法、当前 Step05/Step08/PI-02 证据、旧 `new_geo_re` day15/Step09 清单；然后做 apples-to-apples rate matrix、delayed normalization audit 和 X-Calibur/511-CAM/SPI/COSI 文献 sanity check。默认不改项目；只有独立审计确认当前 delayed 链条存在明确 bug 时，才进入最小修复阶段。”

