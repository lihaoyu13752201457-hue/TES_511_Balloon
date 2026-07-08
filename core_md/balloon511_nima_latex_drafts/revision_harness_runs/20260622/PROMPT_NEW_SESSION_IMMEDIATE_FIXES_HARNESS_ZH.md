# 新会话提示词：完成"立即做"的项目侧修复（v2.1）

用途：把下面整段内容复制到一个新 Codex/GPT 工程会话中。目标是让新会话以 harness/loop engineering 的方式完成当前 Balloon511 NIM A 项目中"立即做"的项目侧修复，并通过**真正独立**的相互监督减少上下文污染、过度扩展和无证据造数。

> 版本说明（v2.1 相对 v2 的修正；v1 归档见同目录 `PROMPT_NEW_SESSION_IMMEDIATE_FIXES_HARNESS_ZH_v1.md`，已归档，勿粘贴）：
> 1. **拆分 Orchestrator 与 Gatekeeper**：Gatekeeper 恢复为纯函数，不得作者化 plan/状态，杜绝"自己给自己定的计划打分"。
> 2. **审计边界强制冷上下文**：审计与终判角色必须用 fresh subagent；无 subagent 时强制"角色间重置上下文"并在 verdict 上标 `INDEPENDENCE` 降级标记。
> 3. **恢复 quote rule 与 per-pass diff**：每条审计 verdict 必须引用源文件行；每 pass 留非累计变更快照。
> 4. **PI-02 的 `DONE` 量化为"刻画达标 + 最低信息量"**，避免旧 30 selected events 低统计结果被误判为完成；同时拆成早期点火 + 末期回收两步，符合长尾调度。
> 5. **新增每-pass 机器门**：JSON 可解析 + 必需键齐 + 防覆盖实跑 + 论文正文本轮冻结（按本轮起点哈希，而不是 HEAD diff）。
> 6. **状态单一归属**：Executor 自报 claimed 状态，Gatekeeper 裁定 terminal 状态，Orchestrator 不碰状态。
> 7. **补齐机器可检查性**：冻结清单先解析到 exact paths；JSON 产物 schema 明确；末尾新增机器可读骨架。

---

你现在接手 `/home/ubuntu/TES_511_Balloon` 项目的 Balloon511 NIM A 论文项目侧修复工作。请使用中文向用户汇报，但项目产物可以按文件既有语言使用英文或中英混合。你的任务不是继续改论文正文，而是完成项目内部待修复清单中标为"立即做"的项目侧闭环。

## 0. 总目标

完成以下"立即做"项目侧修复，并用多角色 harness 审核闭环：

1. **PI-01：证据溯源 manifest 与旧文件隔离**
2. **PI-02：延迟本底 selected-rate 高统计收敛**
3. **PI-03：source normalization 完整审计**
4. **PI-04：Geant4/MEGAlib 配置权威表**
5. **PI-05：最终图件与数据管线重建的最低闭环**

注意：PI-05 的本轮最低闭环是"图件源数据和生成链可追溯 + 当前图件 QA + 明确哪些需要后续美化重画"。如果可以安全重画图件则重画；如果重画会改变物理数据或需要额外未确认输入，则不要硬做，写入 figure audit。

本轮不要做（这些是审稿/清单的上限项，不是本轮 scope；执行器不得自行扩展）：

- 不要重新优化几何。
- 不要把论文 claim 扩展为最终 flight performance。
- 不要做 CsI 替代材料大 trade study。
- 不要做 diffuse sky/foreground 模型。
- 不要做全 CAD 替换。
- 不要做完整 TES/CsI 电子学模拟。
- 不要改写论文正文来"掩盖"项目侧未闭合问题（本轮论文 `.tex/.md` 应保持冻结，见机器门 G5）。

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

- `fix5_benchmarks.json` 是机器可读权威来源，**凌驾于本提示词中写死的任何数值之上**。若 markdown（或本提示词）里的数值和它冲突，先信 JSON，再查生成报告。
- 若要做任何 fix5 prompt/delayed/signal 模拟，必须先确认 `.geo.setup`、source card、SIM header 都指向当前 fix5 几何，且不得覆盖当前 authority outputs。
- 任何无 provenance 的数值不得写入最终报告，只能写为 `UNKNOWN` 或 `TO_RECOVER`。

## 2. 工作目录和产物目录

新建本轮 harness 目录：

`core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260623_immediate_fixes/`

所有 harness 角色产物都写入该目录。文件与单一作者（见 §3 归属表）：

- `00_startup_reading_log.md`（Orchestrator）
- `00_git_baseline.txt`（Orchestrator；本轮起点快照，供机器门 diff）
- `01_initial_state_inventory.md`（Orchestrator）
- `02_execution_plan.md`（Orchestrator）
- `02_coverage_map.md`（Orchestrator；"立即做"项 → PI 的覆盖映射）
- `03_executor_log.md`（Executor；含 claimed 状态表）
- `04_review_auditor_report.md`（Review Auditor）
- `05_project_auditor_report.md`（Project Auditor）
- `05b_figure_auditor_report.md`（可选 Figure Auditor）
- `06_gatekeeper_verdict.md`（Gatekeeper；含 terminal 状态表 + 机器门结果）
- `07_final_summary.md`（Orchestrator，依据 06 撰写）

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

**冻结清单语义规格（FROZEN_PATH_SPECS，本轮绝不可覆盖/修改，机器门 G3/G5 会实跑核对）：**

- exact paths：
  - `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/`
  - `stepwise_maintenance/step08_significance/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/`
  - `core_md/fix5_benchmarks.json`
  - `core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.tex`
  - `core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_zh.tex`
  - `core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.md`（若存在；本轮论文正文冻结）
- semantic specs（Phase 0 必须解析为 exact paths）：
  - 任何旧 `new_geo_re` authority output（从 `fix5_benchmarks.json`、revision reports、`rg -n "new_geo_re|authority"` 解析）
  - 任何当前 v3p5/BGO authority output（从 `fix5_benchmarks.json`、closure reports、Step02--Step08 outputs、`rg -n "v3p5|BGO|authority"` 解析）

Phase 0 必须写 `00_resolved_frozen_paths.txt`，包含 `EXACT_PATHS`、`RESOLVED_SEMANTIC_PATHS`、`UNRESOLVED_FROZEN_PATH_SPECS` 三节。G3 只允许检查已解析的 exact paths，但 `UNRESOLVED_FROZEN_PATH_SPECS` 非空时 `PHASE0_OK = false`，除非用户明确确认该语义规格本轮无法解析且允许继续。

## 3. 角色与独立性

**独立性是这个 harness 的全部价值来源。** 没有真正的独立，多角色就退化成自说自话。因此：

- **若环境有 multi-agent/subagent 工具：** Executor 用一个 agent；**Review Auditor、Project Auditor、Gatekeeper 必须各用一个 fresh（冷上下文）subagent**，只接收其允许读取的 artifacts 与源文件，不继承 Executor 的推理。Orchestrator 可作为驱动 agent。
- **若没有 subagent（单会话回退）：** 顺序扮演角色，但**每次切换角色前必须重置上下文**——只重读该角色"允许读取"的文件，并在该角色产物开头显式写一行：`我现在作为 <角色>，放弃此前作为其他角色的推理，只依据 artifacts 审计。` 同时本轮所有 verdict 必须带标记 `INDEPENDENCE = SINGLE_SESSION_DEGRADED`，提示用户独立性是降级的。有 subagent 时标 `INDEPENDENCE = SUBAGENT`。

**quote rule（贯穿所有审计/终判角色）：** 任何 `PASS/WARN/FAIL/DONE/...` 判定都必须附 `源文件:行 + 原文摘录`（或 JSON 字段路径 + 值）。**没有引用的 verdict 视为无效。**

### 角色与读写边界（artifact-only handoff）

| 角色 | 写 | 只许读 | 禁止 |
|---|---|---|---|
| A Orchestrator（仅启动/收尾） | 00/01/02/02_coverage/07、git baseline | 必读文件、源记录 | 不得维护或裁定状态；不得打 gate |
| B Executor | 03 + 所有项目侧产物 | 必读文件、明确允许的源/脚本/数据 | 不得覆盖 `00_resolved_frozen_paths.txt` 中的冻结路径；不得 invent；不得改几何/论文正文；不得审自己 |
| C Review Auditor | 04 | 03、review 报告、fix queue、被引源行 | 不得改产物；不得依赖 D 的判断 |
| D Project Auditor | 05 | 03、`fix5_benchmarks.json`、method/constraint、被引报告、JSON/CSV、git diff | 不得改产物；不得依赖 C 的判断 |
| E Figure Auditor（可选） | 05b | 03、figures_audit、图件源数据/脚本 | 同上 |
| F Gatekeeper（纯函数） | 06 + terminal 状态表 | 03/04/05/05b、新建项目侧产物、必要时源 JSON/CSV/脚本实跑核对 | **不得**作者化 plan/计划/执行；不得自行放宽 gate；不凭上下文记忆 |

### 各角色职责要点

- **A Orchestrator**：建目录；解析冻结清单并写 `00_resolved_frozen_paths.txt`；存 `00_git_baseline.txt`（`git status --porcelain` + resolved frozen paths 的文件列表/mtime/hash 清单）；读必读文件；固定 scope 为 PI-01..05；写 `02_execution_plan.md` 与 `02_coverage_map.md`。收尾时依据 06 写 `07_final_summary.md`。**不碰状态、不打 gate。**
- **B Executor**：实现 PI-01..05；创建 manifest/audit/配置表/图件 audit；对 PI-02 按 §4 的"点火/回收"两步执行；在 `03_executor_log.md` 自报 claimed 状态、动作、命令、产物路径、证据来源、未解决风险。
- **C Review Auditor**：依据 `balloon511_nima_review_*_20260622.md` 与 `project_internal_fix_queue_zh.md`，逐项核对 PI-01..05 是否真正解决"立即做"的 review/project concern；查是否有内部 debug 语言/旧数值/旧文件名污染 manuscript-facing 资源；查是否用文字搪塞应做的 simulation/provenance 工作。给 `PASS/WARN/FAIL`，quote-grounded。
- **D Project Auditor**：独立核对运行输出、source cards、geometry paths、SIM headers、JSON/CSV 与新产物；确认不与 `fix5_benchmarks.json` 和已有 closure reports 冲突；确认 PI-02 若称完成确是 selected-rate 层面收敛而非 inventory/serialization 闭合；确认上游 Ge-proxy 旧 `1.2534e-4 s^-1` 被明确标 stale；确认论文主数值 `3.92e-2 cps`、`1.19e-3 cps`、`3.85e-5 ph cm^-2 s^-1` 未被无意修改。quote-grounded。
- **E Figure Auditor（可选）**：仅审 PI-05；确认每张图有 source data/脚本/输出路径/hash 或可复现命令；确认重画未改物理数据；区分哪些图只完成 provenance、哪些完成视觉 QA、哪些仍需后续重画。
- **F Gatekeeper**：纯函数。先跑机器门（§4 Phase 1），再读 03/04/05(/05b)，按 §4 的 gate 谓词裁定，写 `06_gatekeeper_verdict.md`，给出 terminal 状态表。

## 4. Loop engineering 协议

本轮不是开放式无限循环。Phase 0 一次；Phase 1 至多 **3 pass**；Phase 2/3 随 pass 走。**backlog 是交付物，不是要驱动到零的 gate**——本轮只闭"立即做"，不把审稿上限项刷成全做。

### Phase 0：启动、基线、覆盖检查

1. Orchestrator 建目录。
2. 解析 `FROZEN_PATH_SPECS`，写 `00_resolved_frozen_paths.txt`，并确认 `UNRESOLVED_FROZEN_PATH_SPECS` 为空；若不为空，先停下向用户报告，不得静默跳过。
3. 存 `00_git_baseline.txt` 作为机器门 diff 基线：`git status --porcelain`（全仓）+ `00_resolved_frozen_paths.txt` 中各路径的文件列表、mtime、hash + **三个论文正文文件的内容哈希**（`git hash-object core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.tex core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_zh.tex`；对未跟踪的 `core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.md` 用 `sha256sum`）。注意：论文 `.tex` 在上一轮文本修订后已是 dirty 状态、`.md` 未跟踪，所以"正文冻结"只能按本轮起点哈希比对，不能用 `git diff` 对 HEAD。
4. 读必读文件，写 `00_startup_reading_log.md`（已读文件、当前 scope、"立即做"定义）。
5. 写 `01_initial_state_inventory.md`：当前 git status 摘要、现有关键报告路径、当前 manuscript-facing 文件、旧/stale 风险、能找到的 delayed/source/figure/config 脚本。
6. 写 `02_coverage_map.md`：把 fix queue 中所有"立即做"concern 逐条映射到 PI-01..05，或显式标 `defer/out-of-scope` 并给一句理由（防止某"立即做"项被静默漏掉）。

Phase 0 gate：

```
PHASE0_OK = 已读必读文件
          ∧ 已写 startup log + inventory + git baseline
          ∧ 已写 resolved frozen paths 且无未解析冻结语义规格
          ∧ 已固定 scope 为 PI-01..05
          ∧ 每个"立即做"concern 在 coverage map 中都有 PI 或显式 defer
```

Phase 0 不通过不得执行修复。

### Phase 1：执行（每 pass 的固定流水线）

执行顺序（依赖：PI-02 报告需引用 PI-01/03/04 产物）：

1. **PI-02a｜长尾点火**：先查找现有 delayed replay 脚本/报告；若能安全跑高统计或补统计，**立刻在后台启动**新 run（新 run 目录），记录命令、PID/session、log 路径、预计产物、恢复方式。这一步在最前面，让模拟在做文档时并行跑。
2. PI-01 evidence manifest / stale quarantine
3. PI-03 source normalization audit
4. PI-04 simulation config authority
5. PI-05 figure/data pipeline audit
6. **PI-02e｜回收**：轮询/收集 PI-02a 的产物，写 selected-rate convergence 报告（引用 PI-01/03/04 产物）。若到本 pass 末仍未取得可比统计，按 PI-02 特别规则记 `BLOCKED_WITH_EVIDENCE`。

Executor 每完成一项，在 `03_executor_log.md` 更新 claimed 状态表：

| PI | claimed 状态 | 产物 | 命令 | 证据来源（文件:行/字段） | 风险 |
|---|---|---|---|---|---|

claimed/terminal 状态词表（仅此六值，禁"基本完成""应该可以"）：

`DONE` · `DONE_WITH_WARN` · `BLOCKED_WITH_EVIDENCE` · `NOT_STARTED` · `IN_PROGRESS`（仅 PI-02a 点火后未回收时可用）· `FAIL`（审计后回流待修）

每 pass 末尾，Executor 触发：

- **机器门**（脚本化；Executor 运行并把结果记入自己的 `03`，Gatekeeper 在 Phase 3 独立复跑 `[machine]` 项并把权威结果记入 `06`；任一 FAIL 则本 pass 不得闭合）：

```
G1 json_parse   : 所有新建 *.json 可被 json.load 解析。
G2 schema_keys  : 每个产物的必需键齐全；缺失项的值必须字面为 "UNKNOWN"/"TO_RECOVER"，否则 FAIL。必需键见下表。
G3 no_overwrite : git status + 00_resolved_frozen_paths.txt 中 exact paths 的 mtime/hash 对比 00_git_baseline.txt，确认冻结输出未变。
G4 provenance   : evidence manifest 每一行 source 字段非空，或显式 UNKNOWN/TO_RECOVER（把"每个数都有 provenance"落成逐行可勾）。
G5 ms_frozen    : 三个论文正文文件的内容哈希与 00_git_baseline.txt 记录一致（本轮论文正文冻结；用哈希而非 git diff，因正文已 dirty 且 .md 未跟踪）。
```

G2 的最低 schema：

| JSON 产物 | 必需顶层键 | 必需子键 |
|---|---|---|
| `paper_evidence_manifest_20260623.json` | `artifact_type`, `created_utc`, `scope`, `entries` | 每个 `entries[]` 必含 `id`, `value`, `units`, `source_path`, `source_locator`（或 `json_pointer`）, `status`, `used_by_manuscript`, `notes`；`status` 只能为 `current` / `archived` / `stale` / `UNKNOWN` / `TO_RECOVER` |
| `source_normalization_audit_20260623.json` | `artifact_type`, `created_utc`, `source_classes`, `equations`, `unit_checks`, `source_plane`, `parma_expacs_inputs`, `megalib_cards`, `sanity_checks`, `linked_manuscript_quantities` | 缺项必须写 `UNKNOWN` 或 `TO_RECOVER`，不得省略 |
| `simulation_config_authority_20260623.json` | `artifact_type`, `created_utc`, `components` | 每个 `components[]` 必含 `name`, `value`, `source`, `source_locator`, `status` |
| `delayed_selected_rate_convergence.json` | `artifact_type`, `created_utc`, `runs`, `combined`, `between_sampling_check`, `verdict` | 每个 `runs[]` 必含 `run_id`, `generated_decays`, `selected_events`, `selected_rate_cps`, `uncertainty_cps`, `relative_uncertainty`, `source_activity_Bq`, `sampling_id`, `seed_or_tag`, `geometry_path`, `source_card_path`, `sim_header_geometry_path`, `command`, `output_path` |
| `figures_audit_20260623.json`（若创建） | `artifact_type`, `created_utc`, `figures` | 每个 `figures[]` 必含 `figure_path`, `source_data_path`, `generation_script`, `command`, `reproduced_this_run`, `visual_qa_status`, `physical_data_changed`, `remaining_action` |

- **per-pass diff**：`git diff`（或新文件的 `git status --porcelain` 快照）→ `pass_N.diff`（非累计），供审计与 Gatekeeper 读。

### Phase 2：双审计（独立）

Review Auditor 与 Project Auditor 必须独立。有 subagent 则并行各自冷上下文；无则顺序但 Project Auditor 不得依赖 Review Auditor 的判断。两者逐项覆盖 PI-01..05，quote-grounded：

| PI | Verdict | Evidence checked（文件:行/字段 + 摘录） | Problem if any | Required correction |
|---|---|---|---|---|

verdict：`PASS` / `WARN` / `FAIL`。`FAIL` = gate 不通过，回 Phase 1 修；`WARN` = 本轮可闭合但 final summary 必须写明风险/后续。

### Phase 3：Gatekeeper 判定（纯函数）

Gatekeeper 只读 §3 表中允许的输入，先核机器门，再裁 gate 谓词。每条谓词标注 `[machine]`（Gatekeeper 亲自实跑复核）或 `[auditor]`（采信 quote-grounded 审计报告）：

```text
IMMEDIATE_FIXES_DONE =
      [machine]  机器门 G1..G5 全 PASS
  AND [auditor]  PI-01 status ∈ {DONE, DONE_WITH_WARN}
  AND [auditor]  PI-03 status ∈ {DONE, DONE_WITH_WARN}
  AND [auditor]  PI-04 status ∈ {DONE, DONE_WITH_WARN}
  AND [auditor]  PI-05 status ∈ {DONE, DONE_WITH_WARN}
  AND [auditor]  PI-02 status == DONE            # 见下方量化判据
  AND [auditor]  Review Auditor 无 FAIL
  AND [auditor]  Project Auditor 无 FAIL
  AND [machine]  无 resolved frozen paths 被覆盖（G3）
  AND [machine]  论文正文本轮未改（G5）
  AND [auditor]  evidence manifest 每行 provenance 已勾（G4 的人工确认）
```

**PI-02 特别规则（长尾 + 量化 DONE）：**

- `DONE` 的判据是**刻画达标 + 最低信息量达标**：
  1. 报告每个 sampling 的 generated decays / selected events / selected rate；
  2. 报告相对统计不确定度（Poisson `1/√N` 或 weighted-MC `√Σw²/Σw`）并写明方法；
  3. **≥2 个 production-position sampling**（必要时多 seed），且各 sampling 的 selected rate 在合并 `1σ`（或显式 `kσ`）内相互一致；
  4. 每个 run 有 geometry / source card / SIM header 校验通过记录；
  5. 全套 provenance（source activity、sampling ID/seed、命令、输出路径）齐全。
  6. 合并 selected events **≥100** 且合并相对统计不确定度 **≤0.10**。若执行前因算力/物理理由必须采用不同阈值，必须在 `02_execution_plan.md` 中预先写明理由，并由 Gatekeeper 审核；不得在看到结果后临时放宽。
- DONE 不要求达到 publication-level final precision，但必须超过上述最低信息量门槛；低于门槛只能是 `BLOCKED_WITH_EVIDENCE` 或 `FAIL`，不能标 `DONE`。
- 若 sampling 间显著不一致且无法解释（可能意味当前 `2.6(5)e-3 cps` 需修正）→ 记 `DONE_WITH_WARN` 不足以闭合，**升级为向用户报告的发现**，`IMMEDIATE_FIXES_DONE = false`；只报告项目发现，不自动改论文正文。
- 若因算力无法取得 ≥2 sampling 可比统计 → `BLOCKED_WITH_EVIDENCE`（写明已启动命令、session/log、预计产物、已完成检查、下一步），`IMMEDIATE_FIXES_DONE = false`。
- 不接受：只证明 source text flux conservation；只证明 inventory serialization；只重复旧 30 selected events；缺 geometry/source provenance。

**3 pass 与终止：**

- Pass 1：执行所有项（含 PI-02 点火/回收）。
- Pass 2：只修审计 `FAIL`。
- Pass 3：只修仍影响 gate 的项。
- **不要为 compute-bound 的 PI-02 烧 pass**：若唯一未闭合原因是 PI-02 等算力（已 `BLOCKED_WITH_EVIDENCE` 且 run 已启动），不要用 pass 2/3 反复重试它——直接记录并在 3 pass 结束时升级给用户。pass 2/3 留给可在会话内修的审计 FAIL。
- 3 pass 后仍未通过：**停止，向用户报告卡点**，不要继续自循环。

## 5. 每个 PI 的具体验收标准

### PI-01 验收标准

必须有 `paper_evidence_manifest_20260623.md/json` 与 `deprecated_manifest_20260623.md`，明确列出论文主数值来源：

- day-15 selected background `3.92e-2 cps`
- selected signal `1.19e-3 cps`
- `Z20d = 7.80`
- `F3 = 3.85e-5 ph cm^-2 s^-1`
- delayed selected rate `2.6(5)e-3 cps`
- upstream Ge-proxy `0.425674 Bq`、`20000` decays、zero selected、`6.38e-5 cps`

并明确标记旧 `1.2534e-4 s^-1` 为 stale 并说明原因；明确哪些旧 support tables/files 不应再 `\input` 进论文。

### PI-02 验收标准

见 §4 PI-02 特别规则。convergence 报告最低含：每 run generated delayed decays、selected events、selected rate、uncertainty method、source activity、sampling ID/seed、geometry/source card/SIM header 校验、between-sampling comparison（或 rate variance）、合并 selected events、合并相对统计不确定度、最终是否支持当前 manuscript delayed rate。若结果改变论文 delayed rate，只报告项目发现，等待用户确认，不自动改正文。

### PI-03 验收标准

必须有 units-complete source normalization derivation：prompt atmospheric source 权重、delayed activity normalization、focused point-source photon flux normalization、source-plane area/projected-area convention、EXPACS/PARMA 输入摘要或归档位置、analytic sanity checks，以及与当前论文 `A_sel = 11.9 cm^2` 和 `F0 = 1e-4 ph cm^-2 s^-1` 的对应关系。

### PI-04 验收标准

必须有 `simulation_config_authority_20260623.json` 与 `simulation_config_table_20260623.md`，每个字段标来源：`discovered from executable` / `discovered from run log` / `discovered from source/config` / `unknown/to recover`。不接受：凭记忆填软件版本；用网上默认版本替代本机版本；不标来源。

### PI-05 验收标准

必须有 `figures_audit_20260623.md`，当前论文每个 figure 列：figure path、source data path、generation script、command if known、whether reproduced this run、visual QA status、whether physical data changed、remaining action。若重画图件，必须证明只改样式/标签/分辨率，不改物理数据。

## 6. 命令和安全约束

- 优先用 `rg`、`sed`、`git status`、`git diff`、`python` 脚本读取和验证。
- 手工编辑文件必须用 `apply_patch`。
- **后台长跑协议**：PI-02a 用后台进程（如 `nohup ... &` 或环境的 job 机制）启动，立即记录命令 + PID/session + log 路径 + 预计产物 + 恢复/轮询方式到 `03_executor_log.md`。
- 不要用 `rm -rf` 清理旧文件；旧文件隔离以 manifest/deprecated 标记为主。若确需移动或删除，先向用户确认。
- 不要覆盖 `00_resolved_frozen_paths.txt` 中的任何路径；所有新输出用带日期的新目录。
- 如果某命令因 sandbox/network/权限失败，按当前环境规则申请必要权限；不要绕过权限。
- 不要提交 git commit，除非用户明确要求。

## 7. 最终回答格式

完成后用中文向用户报告：

1. 是否完成 `IMMEDIATE_FIXES_DONE`，以及本轮 `INDEPENDENCE`（SUBAGENT / SINGLE_SESSION_DEGRADED）。
2. 每个 PI 的 terminal 状态（PI-01..05）。
3. 关键产物路径。
4. 机器门 G1..G5 结果。
5. 是否有 WARN 或 BLOCKED（尤其 PI-02）。
6. 是否改动了模拟数据或 authority outputs（应为"否"）。
7. 下一步建议。

不要给泛泛总结；必须给文件路径和 gate verdict。

## 8. 抗偏差原则

- **执行者不能给自己打 PASS；Orchestrator 不能给自己定的计划打 gate。** 终判由纯函数 Gatekeeper 做，且 Gatekeeper 不得是 plan/执行/状态的作者。
- 审稿意见是严格上限，不是所有项都要本轮做；本轮只做"立即做"。
- 项目记录优先于上下文记忆；JSON/CSV/脚本输出优先于 prose summary。
- 未知就是未知，不要补脑（写 `UNKNOWN`/`TO_RECOVER`）。
- 没有源行引用的审计 verdict 无效。
- 如果 PI-02 没有真正 selected-rate convergence（或 sampling 间不一致），不要把整个任务标为完成。

开始执行前，先向用户发一句简短状态：

"我将按 immediate-fixes harness v2.1 执行：先读项目约束与修复清单、解析冻结路径并存 git 基线、固定 PI-01 到 PI-05 为本轮 scope，建立 harness 目录；PI-02 模拟先后台点火再回收；审计与终判用独立冷上下文角色，每 pass 过机器门并留 diff。"

然后直接开始。

## 9. 机器可读骨架

```json
{
  "harness": "balloon511_nima_immediate_fixes",
  "version": 2.1,
  "executor": "gpt_codex",
  "report_language": "zh",
  "scope": ["PI-01", "PI-02", "PI-03", "PI-04", "PI-05"],
  "out_of_scope_this_round": ["geometry_reopt", "flight_performance_claim", "CsI_trade_study", "diffuse_foreground", "full_CAD", "full_TES_CsI_electronics", "manuscript_text_edits"],
  "authority_over_prompt_literals": "core_md/fix5_benchmarks.json",
  "roles": {
    "orchestrator": {"writes": ["00", "01", "02", "02_coverage", "07", "git_baseline"], "gates": false, "owns_status": false},
    "executor": {"writes": ["03", "project_artifacts"], "self_reports_status": true},
    "review_auditor": {"writes": ["04"], "cold_context_required": true},
    "project_auditor": {"writes": ["05"], "cold_context_required": true, "independent_of": "review_auditor"},
    "figure_auditor": {"writes": ["05b"], "optional": true},
    "gatekeeper": {"writes": ["06"], "pure_function": true, "not_author_of": ["plan", "execution", "status"], "decides_terminal_status": true}
  },
  "independence": {"prefer": "subagent", "fallback": "single_session_with_context_reset", "verdict_tag": ["SUBAGENT", "SINGLE_SESSION_DEGRADED"]},
  "quote_rule": "every PASS/WARN/FAIL/DONE verdict cites source file:line or json field+value; unquoted verdict is void",
  "frozen_path_specs": {
    "exact_paths": [
      "outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/",
      "stepwise_maintenance/step08_significance/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/",
      "core_md/fix5_benchmarks.json",
      "core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.tex",
      "core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_zh.tex",
      "core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.md"
    ],
    "semantic_specs_to_resolve": [
      "old new_geo_re authority outputs",
      "current v3p5/BGO authority outputs"
    ],
    "resolved_frozen_paths_file": "core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260623_immediate_fixes/00_resolved_frozen_paths.txt",
    "unresolved_specs_block_phase0": true
  },
  "status_vocab": ["DONE", "DONE_WITH_WARN", "BLOCKED_WITH_EVIDENCE", "NOT_STARTED", "IN_PROGRESS", "FAIL"],
  "phase0_gate": "read_required AND startup_log AND inventory AND resolved_frozen_paths AND git_baseline AND scope_fixed AND coverage_map_complete",
  "phase1": {
    "exec_order": ["PI-02a_ignite", "PI-01", "PI-03", "PI-04", "PI-05", "PI-02e_collect"],
    "per_pass_pipeline": ["execute", "machine_gate", "pass_diff", "review_audit", "project_audit", "gatekeeper"],
    "machine_gate": ["G1_json_parse", "G2_schema_keys", "G3_no_overwrite_resolved_frozen_paths", "G4_provenance_rows", "G5_manuscript_frozen"],
    "max_passes": 3,
    "compute_bound_PI02_does_not_burn_passes": true,
    "on_fail_after_3": "stop_and_escalate"
  },
  "pi02_done_predicate": "characterization_met AND minimum_information_met (>=2 samplings consistent within combined sigma, uncertainty method reported, full provenance, aggregate selected_events>=100, aggregate relative_uncertainty<=0.10); inconsistency or compute-block => not done, escalate",
  "done_predicate": "machine_gate_all_pass AND PI01/03/04/05 in {DONE,DONE_WITH_WARN} AND PI02==DONE AND no_auditor_FAIL AND no_frozen_overwrite AND manuscript_unchanged AND provenance_rows_checked",
  "anti_drift": "scope pre-decided to PI-01..05; review is a strict upper bound, not a to-do list; backlog is a deliverable, not gates to drive to zero"
}
```
