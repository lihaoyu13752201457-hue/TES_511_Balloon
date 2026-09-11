# 新会话提示词：完成“立即做”的项目侧修复

用途：把下面整段内容复制到一个新 Codex/GPT 工程会话中。目标是让新会话以 harness/loop engineering 的方式完成当前 Balloon511 NIM A 项目中“立即做”的项目侧修复，并通过相互监督减少上下文污染、过度扩展和无证据造数。

---

你现在接手 `/home/ubuntu/TES_511_Balloon` 项目的 Balloon511 NIM A 论文项目侧修复工作。请使用中文向用户汇报，但项目产物可以按文件既有语言使用英文或中英混合。你的任务不是继续改论文正文，而是完成项目内部待修复清单中标为“立即做”的项目侧闭环。

## 0. 总目标

完成以下“立即做”项目侧修复，并用多角色 harness 审核闭环：

1. **PI-01：证据溯源 manifest 与旧文件隔离**
2. **PI-02：延迟本底 selected-rate 高统计收敛**
3. **PI-03：source normalization 完整审计**
4. **PI-04：Geant4/MEGAlib 配置权威表**
5. **PI-05：最终图件与数据管线重建的最低闭环**

注意：PI-05 的本轮最低闭环是“图件源数据和生成链可追溯 + 当前图件 QA + 明确哪些需要后续美化重画”。如果可以安全重画图件则重画；如果重画会改变物理数据或需要额外未确认输入，则不要硬做，写入 figure audit。

本轮不要做：

- 不要重新优化几何。
- 不要把论文 claim 扩展为最终 flight performance。
- 不要做 CsI 替代材料大 trade study。
- 不要做 diffuse sky/foreground 模型。
- 不要做全 CAD 替换。
- 不要做完整 TES/CsI 电子学模拟。
- 不要改写论文正文来“掩盖”项目侧未闭合问题。

## 1. 必读文件，按顺序读

先读项目入口和当前任务约束：

1. `AGENTS.md` 或本会话自动注入的 AGENTS 指令。
2. `core_md/METHOD_FIX5_SIM_CLOSURE.md`
3. `core_md/GUIDE_FIX5_SIM_CLOSURE_FOR_CODEX_20260621.md`
4. `core_md/CONSTRAINTS_FIX5_SIM_CLOSURE.md`
5. `core_md/PRE_PROMPT_FIX5_SIM_CLOSURE_20260621.md`
6. `core_md/fix5_benchmarks.json`

再读论文 revision/harness 相关文件：

7. `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/project_internal_fix_queue_zh.md`
8. `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/project_internal_fix_queue.md`
9. `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/phase1_project_audit.md`
10. `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/phase1_audit.md`
11. `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/remaining_backlog.md`
12. `core_md/balloon511_nima_latex_drafts/balloon511_nima_review_en_20260622.md`
13. `core_md/balloon511_nima_latex_drafts/balloon511_nima_review_cn_20260622.md`，若存在。

只在需要核对论文当前 claim 时读：

14. `core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.tex`
15. `core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_zh.tex`

必须遵守：

- `fix5_benchmarks.json` 是机器可读权威来源。若 markdown 里的数值和它冲突，先信 JSON，再查生成报告。
- 若要做任何 fix5 prompt/delayed/signal 模拟，必须先确认 `.geo.setup`、source card、SIM header 都指向当前 fix5 几何，且不得覆盖当前 authority outputs。
- 任何无 provenance 的数值不得写入最终报告，只能写为 `UNKNOWN` 或 `TO_RECOVER`。

## 2. 工作目录和产物目录

新建本轮 harness 目录：

`core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260623_immediate_fixes/`

所有 harness 角色产物都写入该目录。建议文件：

- `00_startup_reading_log.md`
- `01_initial_state_inventory.md`
- `02_execution_plan.md`
- `03_executor_log.md`
- `04_review_auditor_report.md`
- `05_project_auditor_report.md`
- `06_gatekeeper_verdict.md`
- `07_final_summary.md`

项目侧权威产物可以写到更合适的位置，但必须在 harness 目录中记录路径和理由。建议产物：

- `core_md/balloon511_nima_latex_drafts/paper_evidence_manifest_20260623.md`
- `core_md/balloon511_nima_latex_drafts/paper_evidence_manifest_20260623.json`
- `core_md/balloon511_nima_latex_drafts/deprecated_manifest_20260623.md`
- `core_md/balloon511_nima_latex_drafts/source_normalization_audit_20260623.md`
- `core_md/balloon511_nima_latex_drafts/source_normalization_audit_20260623.json`
- `core_md/balloon511_nima_latex_drafts/simulation_config_authority_20260623.json`
- `core_md/balloon511_nima_latex_drafts/simulation_config_table_20260623.md`
- `core_md/balloon511_nima_latex_drafts/figures_audit_20260623.md`

PI-02 的 delayed selected-rate convergence 若需要新模拟输出，必须使用新的 run/output 目录，例如：

- `outputs/reports/fix5_immediate_fixes_20260623/delayed_selected_rate_convergence.md`
- `outputs/reports/fix5_immediate_fixes_20260623/delayed_selected_rate_convergence.json`
- `outputs/reports/fix5_immediate_fixes_20260623/delayed_selected_rate_convergence.csv`

不要覆盖：

- `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/`
- `stepwise_maintenance/step08_significance/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/`
- `core_md/fix5_benchmarks.json`
- 任何旧 `new_geo_re` authority output
- 任何当前 v3p5/BGO authority output

## 3. 多角色 harness 设计

如果当前环境有 multi-agent/subagent 工具，优先使用真实 subagents。若没有，就在同一会话中按角色顺序执行，但每个角色只读上一个角色的产物和明确允许的源文件，不凭记忆审自己。

### 角色 A：Orchestrator / Gatekeeper

职责：

- 建立本轮目录。
- 读必读文件。
- 固定本轮 scope：只完成 PI-01 到 PI-05。
- 写 `02_execution_plan.md`。
- 维护状态表。
- 最后根据 gate 条件写 `06_gatekeeper_verdict.md`。

禁止：

- 不得自行放宽 gate。
- 不得把未完成项写成完成。
- 不得因为某项困难就改论文 claim 规避。

### 角色 B：Executor

职责：

- 实际实现 PI-01 到 PI-05。
- 创建 manifest、audit、配置表、图件 audit。
- 对 PI-02，先查找现有 delayed replay 脚本和报告；若能安全运行高统计或补充统计，则运行；若需长时间模拟，启动新 run 并记录命令、状态、输出路径。
- 写 `03_executor_log.md`，逐项说明动作、命令、产物路径和未解决风险。

禁止：

- 不得覆盖已有 authority outputs。
- 不得 invent 软件版本、physics list、uncertainty、selected count。
- 不得把 source inventory/serialization 检查冒充 selected-rate convergence。
- 不得改几何设计。

### 角色 C：Review Auditor

职责：

- 根据 `balloon511_nima_review_en_20260622.md`、`balloon511_nima_review_cn_20260622.md` 和 `project_internal_fix_queue_zh.md` 检查 Executor 是否真正解决“立即做”的 review/project concerns。
- 逐项核对 PI-01 到 PI-05。
- 对每项给 `PASS`、`WARN` 或 `FAIL`。
- 写 `04_review_auditor_report.md`。

检查重点：

- 是否遗漏 GPTPro 审稿意见里的关键 P0/P1 项。
- 是否把应该做的 simulation/provenance 工作只用文字搪塞。
- 是否仍有内部 debug 语言、旧数值、旧文件名污染 manuscript-facing 资源。

### 角色 D：Project Auditor

职责：

- 独立核对项目记录、运行输出、source cards、geometry paths、SIM headers、JSON/CSV 报告和新产物。
- 确认新产物不与 `fix5_benchmarks.json` 和已有 closure reports 冲突。
- 确认 PI-02 的 delayed convergence 如果声称完成，确实是 selected-rate 层面的 convergence，而不是 source text 或 inventory 层面的闭合。
- 写 `05_project_auditor_report.md`。

检查重点：

- 新 run 是否使用正确 fix5 几何。
- 新 run 是否没有覆盖旧 authority。
- 新报告中的所有数值是否可追溯到机器可读来源。
- 上游 Ge-proxy 旧 `1.2534e-4 s^-1` 是否被明确标记 stale。
- 当前论文主数值 `3.92e-2 cps`、`1.19e-3 cps`、`3.85e-5 ph cm^-2 s^-1` 是否没有被无意修改。

### 角色 E：Optional Figure/Artifact Auditor

如果图件管线较复杂，可单独开一个子角色：

- 只审查 PI-05。
- 确认每张图有 source data、脚本、输出路径、hash 或可复现命令。
- 确认没有图件在重画时改变物理数据。
- 报告哪些图只完成 provenance，哪些图完成了视觉 QA，哪些仍需后续重画。

## 4. Loop engineering 协议

本轮不是开放式无限循环。最多 3 pass。

### Phase 0：启动和覆盖检查

1. Orchestrator 建目录。
2. 读必读文件。
3. 写 `00_startup_reading_log.md`，列出已读文件、项目当前 scope、立即做项定义。
4. 写 `01_initial_state_inventory.md`，包括：
   - 当前 git status 摘要；
   - 现有关键报告路径；
   - 当前 manuscript-facing 文件；
   - 旧/stale 风险；
   - 能找到的 delayed/source/figure/config 相关脚本。

Phase 0 gate：

`PHASE0_OK = 已读必读文件 AND 已写 startup log AND 已固定 scope PI-01..PI-05`

Phase 0 不通过不得执行修复。

### Phase 1：执行

Executor 按以下顺序执行：

1. PI-01 evidence manifest / stale quarantine
2. PI-03 source normalization audit
3. PI-04 simulation config authority
4. PI-05 figure/data pipeline audit
5. PI-02 delayed selected-rate convergence

说明：PI-02 是最重要 physics fix，但建议排在 PI-01/03/04 后执行，因为 convergence 报告需要引用 source normalization、config 和 evidence manifest。若 PI-02 脚本和输入已经非常明确，可以并行准备，但最终报告必须引用 PI-01/03/04 的产物。

Phase 1 每完成一项，在 `03_executor_log.md` 中更新：

| PI | 状态 | 产物 | 命令 | 证据来源 | 风险 |
|---|---|---|---|---|---|

状态只能是：

- `DONE`
- `DONE_WITH_WARN`
- `BLOCKED_WITH_EVIDENCE`
- `NOT_STARTED`

不得使用含糊状态如“基本完成”“应该可以”。

### Phase 2：双审计

Review Auditor 和 Project Auditor 必须独立审计。若有真实 subagents，应并行运行；若没有，顺序运行，但 Project Auditor 不应依赖 Review Auditor 的判断。

审计输出必须逐项覆盖 PI-01 到 PI-05：

| PI | Verdict | Evidence checked | Problem if any | Required correction |
|---|---|---|---|---|

审计 verdict：

- `PASS`
- `WARN`
- `FAIL`

`FAIL` 表示 gate 不通过，Executor 必须回到 Phase 1 修。

`WARN` 表示本轮主目标可以闭合，但需要在 final summary 中明确风险或后续项。

### Phase 3：Gatekeeper 判定

Gatekeeper 只读：

- `03_executor_log.md`
- `04_review_auditor_report.md`
- `05_project_auditor_report.md`
- 新建的项目侧产物
- 必要时读取源 JSON/CSV/脚本核对，不凭上下文记忆。

完成条件：

```text
IMMEDIATE_FIXES_DONE =
  PI-01 status in {DONE, DONE_WITH_WARN}
  AND PI-03 status in {DONE, DONE_WITH_WARN}
  AND PI-04 status in {DONE, DONE_WITH_WARN}
  AND PI-05 status in {DONE, DONE_WITH_WARN}
  AND PI-02 status == DONE
  AND Review Auditor has no FAIL
  AND Project Auditor has no FAIL
  AND no new authority output was overwritten
  AND every manuscript-relevant number in new artifacts has provenance
```

PI-02 特别规则：

- 如果 PI-02 只启动了长时间 run 但没有得到 selected-rate convergence 结果，不能标为 `DONE`。
- 如果受计算资源限制无法完成，必须标为 `BLOCKED_WITH_EVIDENCE`，并写明已启动命令、session/log、预计产物、已完成检查和下一步。此时 `IMMEDIATE_FIXES_DONE = false`。

最多 3 pass：

- Pass 1：执行所有项。
- Pass 2：修审计 FAIL。
- Pass 3：只修仍影响 gate 的项。
- 3 pass 后仍未通过，停止并向用户报告卡点，不要继续自循环。

## 5. 每个 PI 的具体验收标准

### PI-01 验收标准

必须有：

- `paper_evidence_manifest_20260623.md/json`
- `deprecated_manifest_20260623.md`
- 明确列出论文主数值的来源，包括：
  - day-15 selected background `3.92e-2 cps`
  - selected signal `1.19e-3 cps`
  - `Z20d=7.80`
  - `F3=3.85e-5 ph cm^-2 s^-1`
  - delayed selected rate `2.6(5)e-3 cps`
  - upstream Ge-proxy `0.425674 Bq`、`20000` decays、zero selected、`6.38e-5 cps`
- 明确标记旧 `1.2534e-4 s^-1` 为 stale，说明为什么 stale。
- 明确哪些旧 support tables/files 不应再 input 进论文。

### PI-02 验收标准

必须有 selected-rate 层面的 convergence 报告，最低包含：

- 每个 run 的 generated delayed decays；
- selected events；
- selected rate；
- uncertainty method；
- source activity；
- sampling ID 或 seed；
- geometry/source card/SIM header 校验；
- rate variance 或 between-sampling comparison；
- 最终是否支持当前 manuscript delayed rate；
- 若结果改变论文 delayed rate，应只报告项目发现，不自动改论文正文，等待用户确认。

不能接受：

- 只证明 source text flux conservation；
- 只证明 inventory serialization；
- 只重复旧 30 selected events；
- 没有 geometry/source provenance。

### PI-03 验收标准

必须有：

- units-complete source normalization derivation；
- prompt atmospheric source 权重；
- delayed activity normalization；
- focused point-source photon flux normalization；
- source-plane area/projected-area convention；
- EXPACS/PARMA 输入摘要或归档位置；
- analytic sanity checks；
- 与当前论文 `A_sel=11.9 cm^2` 和 `F0=1e-4 ph cm^-2 s^-1` 的对应关系。

### PI-04 验收标准

必须有：

- `simulation_config_authority_20260623.json`
- `simulation_config_table_20260623.md`
- 每个字段标记来源：
  - discovered from executable；
  - discovered from run log；
  - discovered from source/config；
  - unknown/to recover。

不能接受：

- 凭记忆填软件版本；
- 用网上默认版本替代本机版本；
- 不标来源。

### PI-05 验收标准

必须有：

- `figures_audit_20260623.md`
- 当前论文每个 figure 的：
  - figure path；
  - source data path；
  - generation script；
  - command if known；
  - whether reproduced this run；
  - visual QA status；
  - whether physical data changed；
  - remaining action。
- 若重画图件，必须证明只改变样式/标签/分辨率，不改变物理数据。

## 6. 命令和安全约束

- 优先用 `rg`、`sed`、`git status`、`git diff`、`python` 脚本读取和验证。
- 手工编辑文件必须用 `apply_patch`。
- 不要用 `rm -rf` 清理旧文件；旧文件隔离以 manifest/deprecated 标记为主。若确需移动或删除，先向用户确认。
- 不要覆盖已有 output；所有新输出用带日期的新目录。
- 长时间 simulation 可以启动，但必须记录 session/log 和如何恢复。
- 如果某命令因 sandbox/network/权限失败，按当前环境规则申请必要权限；不要绕过权限。
- 不要提交 git commit，除非用户明确要求。

## 7. 最终回答格式

完成后用中文向用户报告：

1. 是否完成 `IMMEDIATE_FIXES_DONE`。
2. 每个 PI 的状态：
   - PI-01
   - PI-02
   - PI-03
   - PI-04
   - PI-05
3. 关键产物路径。
4. 是否有 WARN 或 BLOCKED。
5. 是否改动了模拟数据或 authority outputs。
6. 下一步建议。

不要给泛泛总结；必须给文件路径和 gate verdict。

## 8. 抗偏差原则

- 执行者不能给自己打 PASS；必须有独立 Review Auditor 和 Project Auditor。
- 审稿意见是严格上限，不是所有项都要本轮做；本轮只做“立即做”。
- 项目记录优先于上下文记忆。
- JSON/CSV/脚本输出优先于 prose summary。
- 未知就是未知，不要补脑。
- 如果 PI-02 没有真正 selected-rate convergence，不要把整个任务标为完成。

开始执行前，先向用户发一句简短状态：

“我将按 immediate-fixes harness 执行，先读项目约束和修复清单，固定 PI-01 到 PI-05 为本轮 scope，然后建立 harness 目录并启动多角色审计。”

然后直接开始。
