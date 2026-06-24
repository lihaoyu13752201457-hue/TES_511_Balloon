---
document_type: harness_engineering
project: TES_511_BALLOON
workstream: delayed-source-authority-reconstruction
version: 2.0
status: ready-for-codex
execution_style: bounded-evidence-first
primary_language: zh-CN
supersedes: null
predecessor: HARNESS_ENGINEERING_TES511_BACKGROUND_VALIDATION.md
phase: post-background-validation-phase2
created: 2026-06-24
codex_session_quickstart: true
repo_root_hint: /home/ubuntu/TES_511_Balloon
phase1_context_harness: HARNESS_ENGINEERING_TES511_BACKGROUND_VALIDATION.md
companion_rationale: TES_511_delayed_source_modification_requirements_and_paper_impact_v2.md
claim_boundary: reference-exposure unresolved-line selected-rate estimate, not flight-performance forecast
context_packet_policy: minimal-allowlist-per-agent; no full-chat-history dumps
default_flags:
  APPLY_MANUSCRIPT_CHANGES: false
  ALLOW_HEAVY_RUN: false
  ACTIVATE_PHASE2_REPO_POINTER: false
  ALLOW_MEGALIB_PATCH: false
quick_context_sections:
  - new_session_prompt
  - project_map
  - authority_allowlist
  - implementation_skeleton
  - work_packet_template
  - known_physics_facts
  - final_status_page
---
# 0. Codex 执行合同

你是本阶段的 **orchestrator**。上一阶段的 prompt 归一化审计、prompt 事件来源追踪、delayed 统计收敛和 CsI–BGO 受控比较已由用户完成；本阶段不得重复执行这些任务，也不得以“结果不符合直觉”为理由重新优化几何、源强、veto 或能窗。

本阶段唯一主目标是：

> 从原始 activation-production `.dat` 与 `CC IP RP` 记录重新建立一个可审计、保留粒子族、原始逻辑体、核素和激发态的 day-15 delayed-source authority，并用 MEGAlib/Cosima 原生 activation 路径和 detector-level 结果进行受控交叉验证。

必须完成以下闭环：

1. 不依赖旧 radial source，从原始 `.dat` 直接构建完整 inventory authority；
2. 使用完整物理键 `(production_tag, raw_volume, ZA, excitation_state)`；
3. 用每个粒子族的总物理曝光时间统一处理 gamma splits 和 non-gamma replicas；
4. 审计旧链中的核素遗漏、激发态折叠、source-name 冲突和体积 canonicalization；
5. 构建 state-aware、tag-aware、production-position-sampled delayed source v2；
6. 与 Cosima `Activator`/`ActivationSource` 原生流程比较 inventory 和 delayed transport；
7. 审计 `DetectorTimeConstant` 对 prompt/delayed 分离和核退激发级联的影响；
8. 在方法通过质量门后，重算 delayed selected rates，并只重建真正受影响的 Step05–Step08/BGO 依赖；
9. 生成论文修改建议、贡献说明和数值 promotion manifest。

本任务必须是**有限状态、证据优先、可停止**的工程流程。异常结果不是失败；无法证明的语义必须进入 `BLOCKED_*`，不得猜测或循环搜索直到“看起来合理”。

# 1. 上一阶段结果的冻结规则

## 1.1 视为已完成且只读的工作

以下成果只作为输入证据，不在本阶段重跑：

- prompt EXPACS/PARMA source-card flux closure；
- 60 cm far-field radius 与 \(\pi R^2\) 面积闭合；
- gamma split、non-gamma replica、unique-seed 和 Step05 selected-rate closure；
- prompt `eplus` survivor provenance；
- 旧 delayed selected-rate convergence；
- same-envelope CsI–BGO prompt/signal comparison；
- 当前 manuscript、fix5 geometry 和 Step05 veto 定义。

上一阶段 prompt audit 已证明当前 prompt source-card、60 cm radius、面积和 Step05 权重链内部闭合。本阶段不得修改 prompt source cards、far-field radius 或 prompt normalization code。

## 1.2 可能因本阶段失效的旧结果

以下结果在 delayed-source v2 promotion 前保留为 `CURRENT_LEGACY_METHOD`，但不得继续当作最终 delayed authority：

- 85.449203 Bq fixed delayed inventory；
- 旧 exact-position source card；
- 旧 delayed W2 rate 和同位素/体积分解；
- 使用同一旧 builder 的 BGO delayed inventory/rate；
- 由旧 delayed rate 传播得到的 Step05–Step08 总本底与灵敏度。

只有当新旧 delayed 结果满足本 harness 的 promotion gate 时，才能决定这些数字是继续有效、需要更新，还是仅作为历史对照。

# 2. 非协商性科学边界

## 2.1 Veto 权威不变

定量主动屏蔽选择仍由 Step05 后处理定义：

```text
shield_total_keV < 50 keV
coincidence_window = 1 us
```

本阶段不进行 CsI detector-threshold 单元测试，不修改 50 keV、1 us、W2 能窗或 topology/FoV 选择。

`DetectorTimeConstant` 是 activation prompt/delayed 分离参数，不是 CsI veto threshold。两者不得混为一谈。

## 2.2 几何和 prompt 不可变

禁止修改：

- fix5 `.geo/.det/.geo.setup`；
- side-window aperture；
- TES、Cu/W、CsI/BGO 材料或尺寸；
- atmospheric prompt source cards；
- signal optics replay；
- Step05 event selection；
- synthetic trajectory 和 significance 定义。

## 2.3 论文 claim 边界

论文仍只声称：

> 当前 detector/cryostat proxy mass model 下，对不可分辨 511 keV 窄线的 reference-exposure selected-rate statistical estimate。

本阶段不扩展到完整飞行预测、完整吊舱、真实轨迹或最终 TES 电子学响应。

## 2.4 物理键规则

用于 inventory、activity 和位置匹配的 authority key 必须是：

```text
(production_tag, raw_logical_volume, ZA, excitation_state_id)
```

强制规则：

- `raw_logical_volume` 用于物理匹配；
- `canonical_volume` 只可用于绘图和汇总，不得用于分配活度；
- `production_tag` 必须保留到 source manifest 和最终分解；
- excitation state 不得折叠到 ground state；
- 浮点 excitation energy 必须通过审计后的 state-ID 规则匹配，不得直接用未经验证的 binary float equality。

# 3. 最终交付物

工程根目录：

```text
engineering/delayed_source_authority_v2_YYYYMMDD/
```

必须产生：

```text
00_manifest/
  phase2_authority_manifest.json
  phase2_authority_manifest.md
  previous_phase_frozen_artifacts.json
  file_hashes.sha256
  execution_environment.json
  decision_log.md
  FINAL_STATUS.md

01_raw_inventory/
  dat_file_manifest.csv
  dat_exposure_by_tag.csv
  raw_inventory_all_states.csv
  raw_inventory_summary.json
  raw_inventory_summary.md
  activity_omission_ledger.csv
  duplicate_state_audit.csv
  inventory_closure.json

02_rpip_alignment/
  rpip_file_manifest.csv
  rpip_state_catalog.csv
  dat_rpip_key_join.csv
  dat_rpip_count_closure.csv
  volume_identity_audit.csv
  state_identity_audit.csv
  rpip_coverage_summary.json
  rpip_coverage_summary.md

03_source_semantics/
  installed_megalib_activation_semantics.md
  excited_ion_source_syntax_test.source
  excited_ion_source_syntax_test.log
  source_semantics_verdict.json
  decay_chain_semantics.md
  detector_time_constant_authority.md

04_custom_source_v2/
  delayed_inventory_v2.csv
  delayed_position_weights_v2.csv
  delayed_source_v2.source
  delayed_source_v2_manifest.json
  delayed_source_v2_audit.json
  delayed_source_v2_audit.md
  source_name_collision_audit.csv

05_native_activation/
  native_input_policy.md
  native_activation_run_manifest.csv
  native_activation_inventory.csv
  native_activation_inventory.json
  custom_native_inventory_comparison.csv
  custom_native_inventory_comparison.md
  native_volume_delayed_source_manifest.json

06_time_constant/
  time_constant_state_risk.csv
  time_constant_pilot_matrix.csv
  time_constant_pilot_results.csv
  time_constant_verdict.json
  time_constant_verdict.md

07_transport/
  pilot_run_manifest.csv
  pilot_rate_comparison.csv
  pilot_verdict.json
  fullstat_run_manifest.csv
  delayed_selected_rate_v2.csv
  delayed_selected_rate_v2.json
  delayed_selected_decomposition_v2.csv
  delayed_energy_band_comparison.csv
  delayed_mc_uncertainty.md

08_promotion/
  legacy_v2_comparison.csv
  legacy_v2_comparison.md
  affected_artifacts_manifest.json
  stale_artifacts_manifest.md
  promotion_decision.json
  promotion_decision.md
  manuscript_numbers_manifest.json

09_downstream/
  step05_rebuild_manifest.json
  step06_step08_rebuild_manifest.json
  bgo_delayed_dependency_verdict.json
  downstream_consistency_check.json

10_manuscript_support/
  TES_511_delayed_source_modification_requirements_and_paper_impact_final.md
  manuscript_insertions_en.md
  manuscript_changes_required.md
  manuscript_claim_boundary.md
  supplement_tables.md
  source_method_figure_spec.md
```

不得覆盖既有 `runs/`、`outputs/` 或上一阶段 engineering 目录。所有新 source、run 和 report 必须进入带 v2 标签的新目录。

# 4. 输入权威与发现规则

## 4.1 优先级

输入选择优先级：

1. 当前 `core_md/fix5_benchmarks.json` 和 promoted fix5 report；
2. 上一阶段 `engineering/background_validation_*` 中 PASS manifest；
3. 当前 full-stat buildup `.dat`、`.sim.gz`、`run_manifest` 和 `normalization.json`；
4. 当前 exact-position source manifest，仅作为 legacy comparator；
5. `old/` 仅用于代码考古，不作为数值 authority。

如果两个输入均可能是当前 authority，输出 `BLOCKED_AMBIGUOUS_AUTHORITY` 并停止，不得按修改时间猜测。

## 4.2 必须定位的输入

```text
core_md/fix5_benchmarks.json
core_md/METHOD_FIX5_SIM_CLOSURE.md
AGENTS.md
runs/step02_buildup_fix5_fullstat_v2/*.dat
runs/step02_buildup_fix5_fullstat_v2/*.sim.gz
runs/step02_buildup_fix5_fullstat_v2/run_manifest.*
runs/step02_buildup_fix5_fullstat_v2/normalization.json
code/tools/build_fixed_delay_source.py
code/tools/build_fix5_1of10_exactpos_delayed_source.py
旧 makedecaysourcewithplot_rpip*.py
当前 delayed source/manifest/weighted table
当前 Step05 event catalog 和 rate table
上一阶段 prompt audit、eplus provenance、BGO comparison 和 delayed convergence reports
本地 NUBASE2020
本地 MEGAlib/Cosima manual、source code 和 activation examples
```

若 raw `.dat` 或 `.sim.gz` 因 Git ignore 不存在于当前工作机，输出 `BLOCKED_RAW_ACTIVATION_PRODUCTS_MISSING`，列出精确缺失路径，不得从旧 summary 反推 raw inventory。

# 5. Agent 架构与上下文隔离

## 5.1 仅允许两层

```text
orchestrator
  ├── authority_agent
  ├── inventory_agent
  ├── rpip_agent
  ├── source_semantics_agent
  ├── source_builder_agent
  ├── native_activation_agent
  ├── timing_agent
  ├── transport_agent
  ├── promotion_agent
  └── manuscript_agent
```

子 agent 不得创建子 agent。

## 5.2 Context packet

orchestrator 为每个 agent 创建：

```text
work_packets/WPxx_<name>.md
```

每个 packet 只能包含：

1. 一个明确任务；
2. 输入 allowlist；
3. 禁止读取/修改列表；
4. 公式和字段 schema；
5. acceptance gate；
6. 最大尝试次数；
7. 合法终止状态。

禁止把以下内容同时提供给一个子 agent：

- 完整对话；
- 完整 manuscript；
- 全部 raw SIM/DAT；
- 上一阶段全部 engineering 输出；
- 所有旧代码版本。

原始大文件应由脚本流式读取，不能复制进 prompt/context。

## 5.3 通信格式

每个 agent 只通过以下文件向 orchestrator 汇报：

```text
summary.json
summary.md
明确 schema 的 CSV/JSON
```

`summary.json` 必须包含：

```json
{
  "status": "PASS|WARN|BLOCKED|FAIL",
  "inputs": [],
  "outputs": [],
  "findings": [],
  "claim_impact": [],
  "next_gate": "",
  "user_decision_required": false
}
```

orchestrator 默认只读取 summary；只有 gate fail 时才打开最小必要 raw evidence。

## 5.4 写入隔离

每个 agent 只能写自己的目录。禁止并行编辑：

- shared manifest；
- source writer；
- manuscript；
- Step05 code；
- baseline files。

最终合并与 promotion 只由 orchestrator 完成。

# 6. 有限状态机

```text
S0 FREEZE_PREVIOUS_PHASE
  -> G0 PREVIOUS_AUTHORITY_LOCKED
S1 BUILD_RAW_INVENTORY
  -> G1 RAW_INVENTORY_CLOSED | BLOCKED_RAW_PRODUCTS
S2 ALIGN_RPIP_AND_STATES
  -> G2 RPIP_ALIGNMENT_PASS | RPIP_COVERAGE_BLOCKED
S3 PROVE_SOURCE_SEMANTICS
  -> G3 EXCITED_SOURCE_SUPPORTED | NATIVE_OR_HYBRID_REQUIRED | BLOCKED_SEMANTICS
S4 BUILD_CUSTOM_SOURCE_V2
  -> G4 CUSTOM_SOURCE_CLOSED | BUILD_FAIL
S5 RUN_NATIVE_CROSSCHECK
  -> G5 INVENTORY_MATCH | EXPLAINED_MODEL_DIFFERENCE | UNRESOLVED_DIFFERENCE
S6 AUDIT_TIME_CONSTANT
  -> G6 TIMING_AUTHORITY_SELECTED | TIMING_SENSITIVITY_UNRESOLVED
S7 RUN_PILOT_TRANSPORT
  -> G7 PILOT_PASS | PILOT_FAIL | RESOURCE_BLOCKED
S8 RUN_FULLSTAT_AND_COMPARE
  -> G8 V2_PROMOTED | LEGACY_RETAINED | NO_RATE_AUTHORITY
S9 REBUILD_AFFECTED_DOWNSTREAM
  -> G9 DOWNSTREAM_CLOSED | DOWNSTREAM_BLOCKED
S10 BUILD_MANUSCRIPT_SUPPORT
  -> DONE
```

任何 `BLOCKED_*`、`UNRESOLVED_*` 和 `NO_RATE_AUTHORITY` 都是合法终点。

# 7. 循环、重试和资源限制

- 每个 work package 最多 2 次实现尝试；
- 每个 syntax/parser failure 最多 1 次确定性修复；
- native activation 最多 1 次配置修复后重试；
- `DetectorTimeConstant` 最多评估 3 个预定义值，不允许自动细扫；
- full-stat delayed transport 最多升级统计一次；
- 不允许因结果“太高/太低”而修改源、几何、阈值或能窗；
- 不允许为了使 custom/native 一致而手工缩放 activity；
- 不允许在线查询并自动填补 half-life；只使用已锁定的本地核数据 authority；
- 不得直接发起超过 100 GB 或 7 CPU-day 的新运行，需生成资源申请并停止；
- 达到 acceptance 或合法 BLOCKED 状态后立即结束该 WP。

# 8. WP00：冻结上一阶段 authority

## 8.1 目标

证明本阶段使用的是已完成工程链的唯一 current baseline，并建立 dependency graph。

## 8.2 操作

1. 固化 fix5 geometry、prompt sources、buildup runs、legacy delayed source、Step05 code 和 manuscript hashes；
2. 固化上一阶段 prompt audit/BGO/convergence reports；
3. 标记 legacy delayed builder 的代码 hash；
4. 建立哪些 downstream 数字依赖该 builder；
5. 不执行任何物理运行。

## 8.3 Gate G0

必须满足：

- baseline authority 唯一；
- previous phase artifacts 可定位；
- legacy delayed builder hash 唯一；
- raw buildup products 路径已记录；
- dependency graph 完整。

否则 `BLOCKED_AMBIGUOUS_AUTHORITY`。

# 9. WP01：从原始 `.dat` 建立全状态 inventory authority

## 9.1 核心原则

禁止从旧 radial source 或 fixed source 反推 inventory。直接读取所有 full-stat activation-production `.dat`。

对每个 production tag \(g\) 定义：

\[
T_g = \sum_{f\in g} TT_f,
\]

对每个完整状态键 \(k=(VN_{raw},ZA,E_{exc})\)：

\[
P_{gk}=\frac{\sum_{f\in g}N_{fgk}}{T_g}.
\]

该公式同时正确处理：

- gamma split：文件共同组成一次总曝光；
- non-gamma replicas：多个相同物理曝光的独立 MC 样本。

不得再用“先除以文件数、再除以 mean TT”的隐式逻辑作为新 authority；旧公式只用于数值对照。

对独立直接生成模型：

\[
A^{\rm direct}_{gk}(t)=P_{gk}\left(1-e^{-\lambda_k t}\right).
\]

若母女核 feeding 尚未证明，字段必须写为 `activity_model=direct_production_only`，不得简称为完整 inventory。

## 9.2 必须保留的字段

```text
production_tag
source_file
raw_volume
canonical_volume_for_reporting_only
ZA
nuclide
exc_raw_token
exc_keV_decimal
state_id
production_count_raw
TT_file_s
TT_tag_sum_s
production_rate_s-1
half_life_s
half_life_authority
activity_day15_direct_Bq
state_class
```

## 9.3 State-ID 规则

- 保存原始 excitation token；
- 使用 `Decimal` 或等价无二进制漂移表示；
- 先统计所有 excitation values 的最小间隔；
- 再选择有文档依据的 quantization；
- 若两个不同状态会在 quantization 后碰撞，立即 `BLOCKED_AMBIGUOUS_EXCITATION_STATE`；
- ground state 必须显式为 state ID，不用隐式缺省。

## 9.4 Omission ledger

每一条 `.dat` RP 记录必须进入且仅进入一个分类：

```text
EMITTED_CANDIDATE
STABLE
UNKNOWN_HALF_LIFE
ZERO_OR_NEGATIVE_YIELD
BELOW_DECLARED_NUMERIC_FLOOR
MISSING_RPIP_SUPPORT
AMBIGUOUS_STATE
UNRESOLVED_VOLUME
OTHER_BLOCKING_REASON
```

禁止因 `min_points`、profile 构造失败、source-name 冲突或 unknown half-life 静默消失。

## 9.5 Acceptance G1

- 所有 `.dat` files 和 TT 记录被计入；
- `sum production_count` 可回溯到每个文件；
- 每个 raw RP row 在 omission ledger 中恰好出现一次；
- 重复状态键、state collision 和未分类条目为 0；
- direct activity 总和可由 CSV 独立重建，relative closure ≤ \(10^{-10}\)；
- legacy 85.449203 Bq 仅作为 comparator，不作为 gate target。

# 10. WP02：RPIP、原始体积和状态对齐

## 10.1 目标

证明每个 inventory key 的空间支持来自相同 `production_tag/raw_volume/ZA/state`，而不是从 canonicalized pool 重分配。

## 10.2 禁止的旧行为

新链不得：

- 用 `(canonical_volume, ZA)` 聚合 activity；
- 丢弃 `production_tag`；
- 丢弃 excitation state；
- 给 gamma points 统一乘 `1/n_split` 后直接与 non-gamma points 混合；
- 依赖旧 source 中已有的 activity keys；
- 以 `min_points >= 15` 作为 exact-position source 的存在条件。

## 10.3 正确的空间估计

对每个 tag \(g\) 和状态键 \(k\)，RPIP 点集为 \(p\in(g,k)\)。其生产率密度估计为：

\[
\rho_{gk}(\mathbf{x})
=\frac{1}{T_g}\sum_{p\in(g,k)}\delta(\mathbf{x}-\mathbf{x}_p).
\]

实际 source 分配使用 `.dat` activity 做归一化：

\[
q_{gkp}=\frac{u_{gkp}}{\sum_{p\in(g,k)}u_{gkp}},
\qquad
A_{gkp}=A_{gk}\,q_{gkp},
\]

其中 \(u_{gkp}\) 必须由与 `.dat` 相同的曝光语义导出。不得用未经证明的 `1/file_count` 作为跨 tag 混合权重。

## 10.4 必须输出的审计

- `.dat` production count 与 RPIP row count per full key；
- RPIP coverage fraction；
- raw volume 与 canonical volume 的 many-to-one map；
- 旧 canonicalization 会重新分配多少 Bq；
- 每个 key 的 point count 和 effective sample size：

\[
N_{\rm eff}=\frac{(\sum w)^2}{\sum w^2};
\]

- activity without RPIP；
- RPIP without positive activity；
- 同坐标不同 state/tag 的歧义。

## 10.5 Missing-RPIP policy

任何正活度 key 没有 RPIP 时，不得静默丢弃。

优先顺序：

1. 证明 hook/解析遗漏并修复；
2. 使用 native volume-based ActivationSource 单独输运该部分；
3. 若无法输运，输出 `BLOCKED_UNREPRESENTED_ACTIVITY`。

仅当未表示活度占比低于预先声明的数值门限，且不包含 β+、511 keV 近邻线、TES/近焦平面材料中的核素时，才允许作为明确的 residual omission；默认门限为 total activity 的 \(10^{-3}\)，不得在看到结果后放宽。

## 10.6 Acceptance G2

- physics join 使用 raw volume；
- every positive-activity key represented or explicitly blocked；
- tag/state/volume coverage 表完整；
- activity redistributed by canonicalization = 0 in v2；
- RPIP activity sum relative closure ≤ \(10^{-10}\)。

# 11. WP03：证明 excited-ion 与 native activation 语义

## 11.1 目标

确认当前安装的 MEGAlib/Cosima 如何表达 excited ions、如何读取 activation files，以及 `DetectorTimeConstant`/decay chain 的真实语义。

## 11.2 证据优先级

1. 当前安装版本源代码；
2. 当前安装版本 manual/example；
3. 最小 parser/transport test；
4. 上游 GitHub 当前代码仅作辅助；
5. 不接受凭记忆写 source syntax。

## 11.3 Excited-ion 最小测试

构建包含两个相同 ZA、不同 excitation state 的极小 source：

- source names 必须不同；
- parser 必须读取为两个不同 state；
- transport/log 必须证明 state 未被 ground-state 替代；
- 输出不得依赖 detector geometry 的复杂效应。

允许的 verdict：

```text
EXPLICIT_ION_POINTSOURCE_SUPPORTED
ACTIVATION_SOURCE_ONLY
HYBRID_REQUIRED
BLOCKED_EXCITED_ION_SEMANTICS
```

如果 regular PointSource 不支持 excitation state，首选方案不是丢弃 state，而是：

- ground-state exact-position custom run；
- metastable/native activation run；
- 在 rate 层合并，并保持独立 uncertainty。

## 11.4 Native activation 语义

必须确认：

- `ActivationBuildUp -> Activator -> ActivationSource` 的文件格式；
- output 是否按 isotope、excitation state、volume 分开；
- 多个 split/replica production files 应如何合并；
- native Activator 是否包含 parent-to-daughter feeding；
- 三步是否要求相同 `DetectorTimeConstant`。

若 parent feeding 不能从代码或受控测试证明，状态为 `DECAY_CHAIN_SEMANTICS_UNKNOWN`，论文不得声称完整 Bateman-chain inventory。

## 11.5 Acceptance G3

必须得到一个明确可执行的 source strategy；不能以“将 excitation 设为 0”通过。

# 12. WP04：构建 delayed source v2

## 12.1 设计

推荐 source construction：

1. 以 raw inventory 的 \(A_{gk}\) 为唯一 activity authority；
2. 以 RPIP full-key point distribution 为空间 authority；
3. 从全局 point-level activity distribution 抽样；
4. 每个抽中 point source 赋相同 activity \(A_{total}/M\)，或采用显式 weighted source；
5. source block 必须携带正确 state；
6. manifest 保留 production tag、raw volume、state 和坐标映射。

## 12.2 Source name

source name 必须稳定且全局唯一，例如：

```text
RP2_<tag>_<volume_hash>_<ZA>_<state_id>_<sample_index>
```

写文件前执行 uniqueness hard gate：

```text
registered_source_names == defined_source_names
unique_source_names == defined_source_names
duplicate_count == 0
```

## 12.3 Canonicalization

`canonical_volume` 只能出现在 report table，不能进入：

- activity key；
- position normalization；
- source-name identity；
- native comparison join。

## 12.4 Source-level closure

必须证明：

- total source flux = v2 inventory total activity；
- per tag/volume/nuclide/state source flux = inventory；
- ground vs metastable fractions preserved；
- no omitted positive activity；
- M-sampling deviation 与 multinomial expectation 相容；
- source text round-trip parser 重建同一 inventory。

## 12.5 Acceptance G4

- total relative flux closure ≤ \(10^{-8}\)；
- per major key（activity fraction ≥ \(10^{-3}\)）relative closure ≤ \(10^{-6}\)；
- duplicate source names = 0；
- state substitution = 0；
- unsupported activity = 0，或进入明确 hybrid/native stream。

# 13. WP05：Cosima native activation 交叉验证

## 13.1 Native input policy

必须区分：

- gamma splits：合起来代表一次物理曝光；
- non-gamma replicas：代表同一物理曝光的独立 MC 估计，不得当成 8 倍实际照射。

native agent 必须先证明其合并策略，允许：

- gamma 合并 counts 与 TT；
- non-gamma per-replica activator 后平均；
- 或构建经解析验证的 merged production file。

禁止简单把所有 `.dat` 交给一个 Activator 后相加。

## 13.2 Inventory comparison

比较维度：

```text
total Bq
production tag
raw volume
ZA
excitation state
ground/metastable fraction
top-20 nuclides
top-20 volumes
beta-plus-relevant inventory
511-near-line inventory
```

差异必须分类：

```text
SERIALIZATION
HALF_LIFE_DATA
EXCITATION_STATE
PARENT_DAUGHTER_FEEDING
VOLUME_MAPPING
SPLIT_REPLICA_NORMALIZATION
NUMERIC_PRECISION
UNKNOWN
```

不得以全局缩放因子强行对齐。

## 13.3 Native delayed transport

native `ActivationSource` 使用 volume-level distribution，与 exact-position custom source不是相同空间模型。其 detector-level rate用于：

- inventory/decay-physics交叉验证；
- 量化 exact-position 与 volume-based approximation 的差异；
- 不是要求 selected rate 必须完全一致。

## 13.4 Gate G5

允许：

- `INVENTORY_MATCH`：total 和 major keys 在预设容差内；
- `EXPLAINED_MODEL_DIFFERENCE`：差异可明确归因且选择了一个 promotion authority；
- `UNRESOLVED_DIFFERENCE`：停止 rate promotion。

建议容差：

- serialization closure：\(10^{-8}\)；
- custom/native total Bq：1%；
- activity fraction ≥1% 的 major key：5%。

超过容差并不自动失败，但必须得到物理解释和用户批准。

# 14. WP06：`DetectorTimeConstant` 和 decay-chain 风险

## 14.1 静态风险筛查

先从 raw states 统计寿命位于以下区间的激发态活度：

```text
1 ns – 100 ns
100 ns – 1 us
1 us – 5 us
> 5 us
```

并标记它们是否：

- 位于 TES/近焦平面材料；
- 可能产生 511 keV 附近或高强度级联；
- 在 legacy source 中被折叠。

## 14.2 有界 pilot

默认只比较：

```text
legacy: 1 ns
analysis-aligned candidate: 1 us
manual/reference candidate: 5 us
```

若静态风险低，可省略 1 us/5 us full transport，只保留 source-level comparison。若差异显著，不允许继续细扫；必须依据 detector event-building policy 选择 authority，而不是选择给出最低本底的值。

三步 activation 流程必须使用同一 `DetectorTimeConstant`。

## 14.3 Decay chain

- 优先用 native Activator semantics 证明是否有 feeding；
- 若 native 为 direct-only，仅对影响 total activity、W2 或 major energy bands 的候选链实现受控 Bateman calculation；
- 不实现无边界的全核素网络；
- 所有未覆盖链进入 uncertainty/limitation ledger。

## 14.4 Gate G6

输出唯一 timing authority 或 `TIMING_SENSITIVITY_UNRESOLVED`。不得让多个 timing 版本同时进入 headline numbers。

# 15. WP07：Pilot、full-stat 和 selected-rate 重算

## 15.1 Pilot matrix

至少比较：

```text
L0 legacy custom source
V2 custom source
NATIVE volume-based source
```

如需 hybrid，则增加：

```text
V2 ground exact-position
V2 metastable/native
V2 combined
```

固定：geometry、selection、W2、veto、event-building 和 detector response。

## 15.2 Pilot acceptance

Pilot 只回答：

- source 可运行；
- state 和 decay stream 可追踪；
- rate 数量级合理；
- 无重复/丢失 source；
- 资源估计可靠。

Pilot 不用于论文 rate。

## 15.3 Full-stat 目标

在 v2 logic promotion 后：

- pooled final W2 selected events ≥300，或 relative MC uncertainty ≤10%；
- 至少 3 个 position-sampling seeds；
- 至少 3 个 decay-transport seeds，资源不足时允许正交缩减但必须说明；
- 每个 run 记录 `sum_w`、`sum_w2` 和 between-seed variance；
- 不再以 source-card flux closure 代替 selected-rate convergence。

## 15.4 必须输出的能段

```text
TES > 0 diagnostic
100–300 keV
300–480 keV
480–550 keV
W2 510.58–511.42 keV
550–800 keV
800–1500 keV
1500–3000 keV
3000–10000 keV
```

`TES > 0` 只能称为 diagnostic integral，不得称为全谱物理率。

## 15.5 分解

至少按以下维度输出 final selected rate：

- production tag；
- nuclide/state；
- raw source volume；
- material；
- decay mode/positron ancestry（可获得时）；
- energy band；
- single/multi-pixel。

# 16. WP08：Promotion 和 downstream dependency

## 16.1 新旧差异判据

对 legacy 与 v2 比较：

```text
total day-15 activity
W2 raw/final delayed rate
energy-band rates
top isotope/state/volume
prompt/delayed fraction
total background and sensitivity
```

若 v2 W2 delayed 与 legacy 差异满足任一条件：

```text
absolute difference > 2 * combined MC sigma
relative difference > 10%
major-isotope identity changes
```

则旧 delayed rate 及依赖它的 Step05–Step08 数字标记为 stale，并进行下游重建。

若差异未超过门限，仍将 v2 source 设为方法 authority，但可以保留 headline 数字，经适当舍入和误差更新。

## 16.2 BGO 依赖

检查上一阶段 BGO delayed 结果使用的 builder hash：

- 若与 legacy builder 相同，在 v2 promotion 后标记 `STALE_METHOD_DEPENDENCY`；
- 只重跑 BGO activation/delayed chain；
- BGO prompt、signal 和 geometry comparison 不重跑；
- 若论文不再使用 BGO delayed comparison，可排除该结果并记录，不强制消耗计算资源。

## 16.3 Downstream 重建

只有受 delayed 数字影响的层需要重建：

- Step05 delayed stream 和 combined background；
- Step06 delayed mission-time fold；
- Step07 source-case ledger；
- Step08 significance；
- manuscript tables/figures。

Prompt、signal、optics和 geometry authority保持不变。

## 16.4 Promotion gate G8/G9

promotion manifest 必须列出：

- promoted source hash；
- inventory model；
- timing authority；
- native comparison status；
- selected-rate uncertainty；
- replaced numbers；
- retained numbers；
- stale artifacts；
- unresolved limitations。

# 17. WP09：论文支持

## 17.1 默认权限

默认只生成修改建议，不直接覆盖 manuscript。只有：

```text
APPLY_MANUSCRIPT_CHANGES=true
```

时，才创建派生稿件和 unified diff。

## 17.2 必须生成的内容

1. delayed source v2 的 Methods 描述；
2. inventory closure 和 native cross-check；
3. excitation-state、raw-volume 和 production-tag 保留说明；
4. timing/decay-chain边界；
5. W2 与宽能段结果；
6. 新旧 rate 与 sensitivity 的更新表；
7. 对 activation 方法贡献的说明；
8. 不应声称的内容；
9. supplementary reproducibility tables。

## 17.3 论文语言规则

正文不得出现：

- `PASS`、`smoke test`、seed 编号；
- 内部路径和 builder 名称；
- “exact”而无统计限定；
- 未证明的“full decay-chain”或“all activation products”；
- 过多有效数字。

建议术语：

```text
state-resolved production-position-sampled delayed source
raw-volume-preserving activation inventory
tag-aware exposure normalization
native volume-based activation cross-check
```

# 18. 失败状态

```text
PASS
WARN_STAT_LIMITED
WARN_NATIVE_VOLUME_APPROXIMATION
WARN_DECAY_CHAIN_INCOMPLETE
BLOCKED_AMBIGUOUS_AUTHORITY
BLOCKED_RAW_ACTIVATION_PRODUCTS_MISSING
BLOCKED_AMBIGUOUS_EXCITATION_STATE
BLOCKED_UNREPRESENTED_ACTIVITY
BLOCKED_EXCITED_ION_SEMANTICS
BLOCKED_RESOURCE_APPROVAL
FAIL_INVENTORY_CLOSURE
FAIL_RPIP_ALIGNMENT
FAIL_SOURCE_NAME_COLLISION
FAIL_NATIVE_COMPARISON
FAIL_TIMING_AUTHORITY
FAIL_TRANSPORT
NO_RATE_AUTHORITY
```

每个非 PASS 状态必须包含：evidence、受影响 claim、最小下一步、是否需要用户决策，以及未执行的后续阶段。

# 19. 测试策略

## 19.1 必须的 synthetic unit tests

1. **Gamma split test**：两个文件各 \(T/2\)，验证 \(P=\sum N/\sum TT\)；
2. **Non-gamma replica test**：三个文件各 \(T\)，验证不会得到 3 倍 production rate；
3. **Mixed-tag test**：gamma split 与 neutron replicas 对同一 nuclide/volume 的贡献按 rate 正确混合；
4. **Excitation collision test**：相同 ZA、不同 excitation 必须保留两行和两个 source；
5. **Raw-volume collision test**：两个会被旧 `canon_vn` 合并的 raw volumes 在 v2 中保持独立；
6. **Duplicate source-name test**：重复立即 hard fail；
7. **Missing-RPIP test**：正活度无 RPIP 不得静默输出 PASS；
8. **Round-trip test**：source text 解析后重建同一 per-key activity；
9. **No-overwrite test**：baseline path 写入尝试必须失败。

## 19.2 Smoke tests

- native Activator parse；
- native ActivationSource parse；
- explicit excited-ion source parse；
- one-state/one-point delayed transport；
- hybrid stream combine；
- Step05 ingest。

## 19.3 不做的测试

- CsI threshold scan；
- prompt source-area重新审计；
- BGO geometry重新优化；
- full payload；
- TES electronics engine；
- 以降低本底为目标的 timing/half-life调参。

# 20. Change control

任何修改必须：

1. 在新 branch/worktree；
2. 单一目的；
3. before/after hash；
4. 有 test；
5. 有 rollback；
6. 不混合 source-physics change 与代码重构；
7. 不与 geometry/prompt/selection change 同 commit。

推荐 commits：

```text
chore: lock delayed-source v2 authorities
feat: build raw state-resolved activation inventory
feat: add raw-volume and tag-aware RPIP alignment
feat: add excited-ion source semantics tests
feat: build state-aware exact-position delayed source v2
feat: add native Activator and ActivationSource cross-check
feat: audit activation detector time constant
feat: run delayed v2 pilot and full-stat convergence
chore: promote delayed v2 and invalidate dependent artifacts
docs: add manuscript support for delayed source v2
```

# 21. 质量门总表

| Gate | 必须条件 | 失败动作 |
|---|---|---|
| G0 | 上一阶段 authority、legacy builder、raw products 唯一 | BLOCKED，不猜测 |
| G1 | raw `.dat` 全状态 inventory closure | 修复一次，否则 FAIL |
| G2 | tag/raw-volume/state RPIP 对齐，无静默遗漏 | BLOCKED 或 hybrid |
| G3 | excited-ion/native semantics 明确 | 选择 custom/native/hybrid；不降为 ground |
| G4 | source v2 per-key activity closure，无重名 | 修复一次，否则 FAIL |
| G5 | native inventory match 或差异可解释 | unresolved 则停止 rate promotion |
| G6 | timing authority 唯一 | unresolved 则不生成 headline rate |
| G7 | pilot 可运行、资源可控 | 失败一次后停止 |
| G8 | full-stat uncertainty 与新旧 comparison 完整 | PASS/WARN，不无限加统计 |
| G9 | downstream dependency 完整重建 | BLOCKED 时不更新论文数字 |
| G10 | manuscript numbers 可追溯 | 不覆盖原稿 |

# 22. Orchestrator 最终检查清单

- [ ] 未重跑或修改已 PASS 的 prompt audit；
- [ ] 未修改 geometry、source radius、veto、W2 或 signal；
- [ ] inventory 直接来自 raw `.dat`；
- [ ] 物理 key 包含 tag、raw volume、ZA、state；
- [ ] canonical volume 仅用于 report；
- [ ] gamma split/non-gamma replica 使用 \(\sum N/\sum TT\)；
- [ ] 每个 `.dat` key 被分类一次；
- [ ] 无 `min_points` 静默遗漏；
- [ ] excitation states 未折叠；
- [ ] source names 全局唯一；
- [ ] missing RPIP activity 被显式处理；
- [ ] native activation comparison 完成或明确 BLOCKED；
- [ ] parent/daughter semantics 有证据或明确 limitation；
- [ ] `DetectorTimeConstant` 与三步 activation 一致；
- [ ] selected rates 有 `sum_w2` 和 seed variance；
- [ ] BGO 只重跑受旧 delayed builder 影响的链；
- [ ] 所有 stale outputs 已列出；
- [ ] manuscript 数字只来自 promotion manifest；
- [ ] agent 未递归创建 subagent；
- [ ] 每个 WP 未超过重试和资源限制。

# 23. Codex 启动指令

```text
1. Read this harness and the current AGENTS.md only.
2. Create a new branch/worktree and engineering/delayed_source_authority_v2_YYYYMMDD/.
3. Run WP00. Do not start physics work if raw authority is ambiguous or missing.
4. Build the raw full-state inventory directly from .dat; do not read activity from the legacy source.
5. Complete raw-volume/tag/state RPIP alignment before writing any new source.
6. Prove excited-ion/native activation semantics with the installed MEGAlib version.
7. Build and audit source v2; no positive activity may disappear silently.
8. Run native inventory cross-check and bounded DetectorTimeConstant audit.
9. Run pilot before full-stat; obey resource guard.
10. Promote only after inventory, source, native, timing and selected-rate gates pass.
11. Rebuild only delayed-dependent Step05–Step08 and BGO artifacts.
12. Generate manuscript support and FINAL_STATUS.md; do not overwrite the manuscript unless explicitly authorized.
```

本阶段的成功标准不是“让 delayed 变高”，而是：

> **无论 delayed 最终高或低，能够证明每个放射性状态从生成计数、物理曝光、活度、空间位置、衰变源、detector selection 到论文数字均具有唯一、可复核且不会静默丢失信息的 authority。**

# 24. 新 Codex Session 接手字段

本节移植并改写自 Phase-1 harness 的“新对话接手指南/项目地图/authority allowlist/工程骨架/FINAL_STATUS”字段。目的不是增加科学任务，而是让新的 Codex session 在最少上下文下快速进入正确边界，避免读取整段聊天记录后被旧结果、旧路径或用户直觉污染。

新 session 必须把本节当作启动层：先锁定 authority，再执行 WP；不得直接重跑模拟或修改论文。

## 24.1 新对话第一条提示词

建议在新 Codex/GPT Pro 对话中直接粘贴以下提示词：

```text
你正在接手 `/home/ubuntu/TES_511_Balloon` 的 TES_511_BALLOON
Phase-2 delayed-source-authority-reconstruction 工程。

先阅读并只读：
1. `core_md/balloon511_nima_latex_drafts/revision_harness_runs/HARNESS_20260624/HARNESS_ENGINEERING_TES511_DELAYED_SOURCE_AUTHORITY_V2_1_QUICK_CONTEXT.md`
2. `core_md/balloon511_nima_latex_drafts/revision_harness_runs/HARNESS_20260624/TES_511_delayed_source_modification_requirements_and_paper_impact_v2.md`
3. `AGENTS.md`
4. `README.md`
5. `core_md/METHOD_FIX5_SIM_CLOSURE.md`
6. `core_md/fix5_benchmarks.json`
7. `engineering/background_validation_20260624/01_prompt_source_audit/prompt_normalization_audit.json`
8. `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260623_delay_processing_reaudit_3agent/11_fix5_w2_prompt_delayed_energy_band_stats.md`
9. `upload_20260624_source_construction_core/01_README_SOURCE_CONSTRUCTION_CORE.md` 或仓库中的同等 source-construction core bundle。

目标不是重构全项目、优化几何、修 prompt、重做 BGO，也不是让 delayed 本底变大。
目标是在新派生目录 `engineering/delayed_source_authority_v2_YYYYMMDD/` 下执行该 harness：
先锁定 Phase-1 authority，再从原始 activation-production `.dat` 与 `CC IP RP` 记录建立完整 delayed inventory ledger，保留 `(production_tag, raw_logical_volume, ZA, excitation_state)`，修复/验证 state-aware source backend 和 tag-aware spatial weighting，再与 Cosima native activation oracle 进行受控比较，最后只在通过质量门后重算受影响的 delayed selected rate 和论文数字。

非协商边界：
- 不覆盖现有 fix5 geometry、prompt source cards、Step05 authority outputs、legacy delayed outputs 或 manuscript source。
- 不改 Step05 的 50 keV active-shield veto、1 us coincidence window、W2 line window 或 topology/FoV selection。
- 不重做 prompt normalization、prompt eplus provenance、CsI--BGO same-envelope comparison 或 Phase-1 delayed convergence；这些只作为 read-only evidence。
- 不自动调几何、厚度、threshold、source flux、far-field radius 或 signal normalization。
- `DetectorTimeConstant` 只作为 activation prompt/delayed partition 参数审计，不得与 CsI veto threshold 混淆。
- 任何 `BLOCKED_*` / `WARN_*` / `FAIL_*` 都是合法终点；必须输出证据和最小下一步，不得无限搜索或自造解释。

请先执行 WP00 authority lock，只生成 manifest/hash/decision log；如果 authority 不唯一，停止并报告 `BLOCKED_AMBIGUOUS_AUTHORITY`。
```

## 24.2 新对话必须掌握的项目地图

当前仓库定位：

```text
repo root:
  /home/ubuntu/TES_511_Balloon

current fix5 geometry authority:
  outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/

current prompt source cards and Phase-1 prompt audit:
  config/megalib_sources_fullsphere20_fix5_tilt45/
  engineering/background_validation_20260624/01_prompt_source_audit/

current prompt/buildup run directories:
  runs/step02_instant_fix5_fullstat_v2/
  runs/step02_buildup_fix5_fullstat_v2/

legacy delayed source build outputs; comparator only, not v2 upstream authority:
  runs/step02_decay_source_fix5_fullstat_v2/
  runs/step02_delay_fix_fix5_fullstat_v2/
  runs/step02_delayed_transport_fix5_fullstat_v2_exactpos_m50000_s260613/

current fix5 Step05 authority:
  stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/

current final reports:
  outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/

manuscript tree:
  core_md/balloon511_nima_latex_drafts/

new Phase-2 engineering outputs must go under:
  engineering/delayed_source_authority_v2_YYYYMMDD/
```

`old/` 是历史代码和历史结果集合。除非某个当前 manifest 明确引用，`old/` 只能作为代码考古，不可作为当前数值 authority。`upload_*` 或 compact bundle 可作 GPT/Codex 上下文包，但不是新的 simulation authority；其中的文件通常是拷贝。

## 24.3 当前最小 authority allowlist

WP00 可以从以下文件开始定位；实际使用前仍必须记录 SHA256、mtime、size、git status 和 authority status。

### Geometry

```text
outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup
outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo
outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det
outputs/reports/user_redesign_multiholeW_fix5_20260621/USER_CYLMAG_REDESIGN_MULTIHOLEW_FIX5_SUMMARY.md
outputs/reports/user_redesign_multiholeW_fix5_20260621/side_window_material_path_audit_fix5.json
```

### Prompt and buildup, read-only Phase-1 authority

```text
config/megalib_sources_fullsphere20_fix5_tilt45/source_migration_manifest.json
config/megalib_sources_fullsphere20_fix5_tilt45/Background_*_fullsphere20.source
code/tools/run_equiv2602_pipeline_NEW_GEO.py
runs/step02_instant_fix5_fullstat_v2/normalization.json
runs/step02_instant_fix5_fullstat_v2/run_manifest.csv
runs/step02_instant_fix5_fullstat_v2/run_summary.csv
runs/step02_buildup_fix5_fullstat_v2/normalization.json
runs/step02_buildup_fix5_fullstat_v2/run_manifest.csv
runs/step02_buildup_fix5_fullstat_v2/run_summary.csv
engineering/background_validation_20260624/01_prompt_source_audit/prompt_normalization_audit.json
engineering/background_validation_20260624/01_prompt_source_audit/source_flux_bin_audit.csv
```

### Legacy delayed comparator, not v2 upstream authority

```text
code/tools/makedecaysourcewithplot_rpip.py
code/tools/build_fixed_delay_source.py
code/tools/build_fix5_1of10_exactpos_delayed_source.py
code/tools/audit_fix5_groundstate_half_life_units.py
runs/step02_decay_source_fix5_fullstat_v2/activation_decay_day15.source
runs/step02_decay_source_fix5_fullstat_v2/activation_inventory_day15.csv
runs/step02_decay_source_fix5_fullstat_v2/normalization_audit_day15.json
runs/step02_delay_fix_fix5_fullstat_v2/activation_decay_day15_groundstate_fixed.source
runs/step02_delay_fix_fix5_fullstat_v2/normalization_audit_groundstate_fix.json
runs/step02_delay_fix_fix5_fullstat_v2/source_fix_summary.json
runs/step02_delay_fix_fix5_fullstat_v2/fix5_fullstat_v2_exactpos_m50000_s260613_delayed_source_manifest.json
runs/step02_delay_fix_fix5_fullstat_v2/exactpos_weighted_rpip_table_m50000_s260613.csv
runs/step02_delayed_transport_fix5_fullstat_v2_exactpos_m50000_s260613/
```

### New v2 raw inventory inputs

```text
runs/step02_buildup_fix5_fullstat_v2/*.dat
runs/step02_buildup_fix5_fullstat_v2/*.sim.gz
inputs/nubase/nubase_2020.txt
/home/ubuntu/MEGAlib_Install/megalib-main/doc/Cosima.pdf
/home/ubuntu/MEGAlib_Install/megalib-main/src/cosima/src/
```

如果 raw `.dat` 或 `.sim.gz` 没有提交在仓库中，允许状态为 `BLOCKED_RAW_TRANSPORT_NOT_AVAILABLE`；不得从 compact upload bundle 或旧 delayed source 反推完整 v2 inventory。

### Step05 and analysis

```text
old/code/tools/build_v3p5_centerfinger_step05_l1_response.py
stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_rates.csv
stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_response_summary.json
stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/work/event_catalog.pkl
outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_w_activation_selected_w2_audit.json
outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_w_activation_selected_w2_events.csv
```

### Manuscript and context

```text
core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.tex
core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.md
core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260623_delay_processing_reaudit_3agent/11_fix5_w2_prompt_delayed_energy_band_stats.md
core_md/fix5_benchmarks.json
core_md/METHOD_FIX5_SIM_CLOSURE.md
```

## 24.4 当前已完成 Phase-1 事实，供新对话校准

这些事实是 read-only evidence，不是 v2 结论。若 v2 结果不同，必须说明是新 authority 取代旧结果，还是路径/统计差异造成。

1. Phase-1 prompt source-card、60 cm far-field radius、\(\pi R^2\) 面积和 Step05 selected-rate 权重链已闭合。
2. `fix5_fullstat_v2_exactpos_m50000_s260613` legacy final W2 prompt rate 为 `0.0366410230297 cps`，delayed rate 为 `0.00257520348894 cps`。
3. legacy final W2 prompt 中 `eplus` 贡献约 `0.0318897456148 cps`，约占 prompt `87%`。
4. legacy W2 delayed fraction 从 raw `3.76%` 上升到 final `6.57%`；因此不能说 active veto/FoV preferentially suppresses delayed。
5. legacy final W2 delayed selected events 为 30 个，全部来自 Cu-64/Cu-62；W/collimator selected contribution 为 0。
6. legacy `1500-3000 keV` final delayed fraction 接近 `48.85%`；因此不能写 activation negligible。
7. 旧 delayed source 的 `85.449203 Bq` 目前只应视为 `CURRENT_LEGACY_METHOD`，直到 raw `.dat` ledger 证明其完整性或给出修正。
8. 已确认的结构性风险包括：状态折叠到 `(VN, ZA)`、source naming 不含 excitation、可能存在 radial builder omission、RPIP 空间混合未按 job exposure estimator、独立 buildup 缺少 Bateman feeding/native oracle 对比、`DetectorTimeConstant=1 ns` 未完成 activation partition 边界验证。

# 25. 工程实现骨架

## 25.1 推荐目录初始化

新对话执行第一步应创建：

```text
engineering/delayed_source_authority_v2_YYYYMMDD/
  00_manifest/
  work_packets/
  scripts/
  logs/
  tests/
```

`YYYYMMDD` 使用当前日期。若目录已存在，不覆盖；创建：

```text
engineering/delayed_source_authority_v2_YYYYMMDD_runNN/
```

`00_manifest/decision_log.md` 第一行必须记录：

```text
started_at: <ISO8601>
git_head: <hash>
git_status: <clean|dirty>
harness: HARNESS_ENGINEERING_TES511_DELAYED_SOURCE_AUTHORITY_V2_1_QUICK_CONTEXT.md
phase1_harness: HARNESS_ENGINEERING_TES511_BACKGROUND_VALIDATION.md
claim_boundary: reference-exposure unresolved-line selected-rate estimate
```

## 25.2 禁止直接修改的路径

除非用户明确要求并更新本 harness，所有 WP 默认禁止写入：

```text
outputs/
runs/
stepwise_maintenance/
core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_*.tex
core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_*.md
config/megalib_sources_fullsphere20_fix5_tilt45/
old/
```

允许读取这些路径；允许在 `engineering/delayed_source_authority_v2_*` 下写 derived scripts、reports、copied manifests、lightweight derived data 和 microtest artifacts。任何需要新 Cosima transport 的阶段必须写入新的 harness 专属 run directory，并先记录在 decision log。

## 25.3 WP00 可执行骨架：Phase-1 authority lock

WP00 不运行 Cosima，只做发现、hash、manifest。

建议脚本：

```text
engineering/delayed_source_authority_v2_YYYYMMDD/scripts/wp00_lock_phase1_authority.py
```

最小职责：

1. 解析本节 allowlist；
2. 对每个存在文件计算 SHA256、size、mtime；
3. 标记 `old/`、`upload_*`、archive/stale 候选；
4. 读取 `.geo.setup` 并解析 `Include` 和 `SurroundingSphere`；
5. 读取 prompt/buildup run `normalization.json` 的 `farfield_radius_cm`；
6. 读取 Phase-1 prompt audit JSON，确认 status 为 PASS；
7. 读取 legacy delayed manifest，但标记为 `LEGACY_COMPARATOR`；
8. 输出 `phase1_authority_manifest.json/md`、`file_hashes.sha256` 和 `decision_log.md`。

若同一 basename 存在多个可能 authority 且无法根据 manifest 决定，输出 `BLOCKED_AMBIGUOUS_AUTHORITY`。

## 25.4 WP01 可执行骨架：Raw `.dat` inventory ledger

建议脚本：

```text
engineering/delayed_source_authority_v2_YYYYMMDD/scripts/wp01_build_raw_inventory_ledger.py
```

最小职责：

1. 枚举 buildup `.dat` 文件并按 job/source tag 解析 `VN/RP/TT`；
2. 保留 key：`(production_tag, raw_logical_volume, ZA, excitation_state_id)`；
3. 不使用 canonical volume 进行物理合并；
4. 用每个 job 的 `TT` 和 source/run manifest 建立 exposure estimator；
5. 输出 production count、production rate、half-life、day-15 activity；
6. 所有无法处理条目写入 omission ledger，并给出 reason；
7. 输出 raw-to-emitted closure：`calculable + explicitly_omitted = raw_seen`。

不可从 legacy fixed source 或 legacy exact-position source 反推 inventory。

## 25.5 WP02 可执行骨架：RPIP identity 与 coverage

建议脚本：

```text
engineering/delayed_source_authority_v2_YYYYMMDD/scripts/wp02_join_rpip_identity.py
```

最小职责：

1. 解析 buildup `.sim.gz` 中的 `CC IP RP`；
2. 保留 `production_tag, raw_logical_volume, canonical_volume, ZA, excitation_state_id, x,y,z,t, process, parent/track metadata if available`；
3. 使用与 WP01 相同的 state-ID 规则；
4. 输出每个 raw state key 的 RPIP coverage；
5. 对缺少 RPIP 的 active states，按本 harness 的 `MISSING_RPIP_SUPPORT_ONLY` 或 `BLOCKED_MISSING_SELECTED_RPIP` 规则处理；
6. 输出 canonicalization audit，但不得把 canonical volume 用于活度分配。

## 25.6 WP03 可执行骨架：Stateful source backend microtest

建议脚本/目录：

```text
engineering/delayed_source_authority_v2_YYYYMMDD/scripts/wp03_test_radioactive_ion_backend.py
engineering/delayed_source_authority_v2_YYYYMMDD/tests/radioactive_ion_backend/
```

最小职责：

1. 建立 ground-state radioactive ion microtest；
2. 建立 excited/metastable-state radioactive ion microtest；
3. 验证 source card 语法、Cosima transport、decay products 和状态是否符合预期；
4. 若 MEGAlib 当前版本无法可靠发射 excited states，输出 `BLOCKED_EXCITED_ION_BACKEND`，不得静默折叠到 ground state。

## 25.7 WP04 可执行骨架：Exposure-aware spatial weighting

建议脚本：

```text
engineering/delayed_source_authority_v2_YYYYMMDD/scripts/wp04_build_exposure_aware_spatial_weights.py
```

最小职责：

1. 对每个 raw state key 先确定物理活度；
2. 在同一 key 内使用 RPIP 点构造空间采样分布；
3. 空间权重必须来自 job exposure estimator，不得使用统一 `1/div` 混合 gamma split 和 non-gamma replicas；
4. 输出 split/replica invariance tests；
5. 对旧 legacy weighting 输出差异审计。

## 25.8 WP05 可执行骨架：Cosima native activation oracle

建议脚本：

```text
engineering/delayed_source_authority_v2_YYYYMMDD/scripts/wp05_native_activation_oracle.py
```

最小职责：

1. 生成或定位原生 `Activator`/`ActivationSource` 输入；
2. 运行轻量 native inventory oracle；
3. 比较 total Bq、top isotope、top volume、excitation-state inventory、parent-daughter feeding 迹象；
4. 如 native oracle 只能到 volume-level，明确写出该边界；
5. 输出 `native_vs_custom_inventory_comparison.csv/json/md`。

## 25.9 WP06 可执行骨架：DetectorTimeConstant boundary

建议脚本：

```text
engineering/delayed_source_authority_v2_YYYYMMDD/scripts/wp06_detector_time_constant_boundary.py
```

预注册值：

```text
1 ns, 100 ns, 1 us, 5 us
```

最小职责：

1. 静态确认当前 source/activation 使用的 `DetectorTimeConstant`；
2. 对 pilot source 或 native oracle 做有限扫描；
3. 比较 prompt+delayed 总量守恒、line/window rate、cascade timing；
4. 输出 `TIME_CONSTANT_STABLE`、`TIME_CONSTANT_SELECT_BASELINE_CHANGED` 或 `TIME_CONSTANT_UNSTABLE_BLOCKED`。

## 25.10 WP07/WP08 可执行骨架：source v2 与 selected-rate

建议脚本：

```text
engineering/delayed_source_authority_v2_YYYYMMDD/scripts/wp07_build_delayed_source_v2.py
engineering/delayed_source_authority_v2_YYYYMMDD/scripts/wp08_run_selected_rate_v2.py
```

最小职责：

1. 构建 label 唯一的 v2 source；
2. 每个 source name 包含 safe hash，避免 collision；
3. source manifest 写入 source-level closure；
4. pilot transport 先通过；
5. full-stat escalation 受资源门控制；
6. Step05 使用同一 code hash；
7. 输出 energy-band rates、W2 rate、isotope/volume/tag/state decomposition、`sum_w/sum_w2` 和 seed variance。

# 26. Work Packet 模板

每个 agent packet 使用以下模板；orchestrator 不应把完整仓库上下文塞给所有 agent。

```text
# WPxx <name>

## Goal
<one task only>

## Allowed inputs
- <path>
- <path>

## Forbidden reads/writes
- do not write outside engineering/delayed_source_authority_v2_YYYYMMDD/<wp_dir>
- do not modify baseline outputs/runs/stepwise_maintenance/config/source cards/manuscript
- do not read unrelated raw outputs unless listed in allowlist

## Required outputs
- summary.json
- summary.md
- <specific csv/json/md>

## Acceptance criteria
- <gate condition>

## Stop states
- PASS
- WARN_...
- BLOCKED_...
- FAIL_...

## Max attempts
2 implementation attempts, 1 deterministic validation-fix retry.

## Notes
All rates must carry units and uncertainty. Physical surprise is not a retry condition. Results that make delayed smaller, larger, or unchanged are all valid.
```

# 27. 当前已知物理事实，供新对话校准

这些是当前 evidence，不是 v2 source 的结论：

1. Prompt source-card 与 selected-rate closure 已 PASS；不要把 Phase-2 问题回退成 prompt radius/area 猜测。
2. Source-layer prompt 总初级率远高于 delayed decay rate；因此 prompt > delayed 在数值上可能合理。
3. Legacy W2 delayed 低已经发生在 raw detector-coupled stage；最终 cut 没有 preferentially suppress delayed。
4. Legacy W2 delayed 由 Cu-64/Cu-62 selected events 主导，总活度由 CsI/I-128 主导；活度分解不能替代 selected-rate 分解。
5. Delayed 在高能带可接近 prompt；论文禁止写 activation negligible。
6. Phase-2 真正问题是 source-construction integrity：raw inventory completeness、excitation-state retention、source-name collision、RPIP join、tag-aware spatial weighting、native activation oracle 和 DetectorTimeConstant boundary。
7. 任何 v2 数字进入论文前都必须通过 promotion manifest，列出旧值、新值、差异原因、统计误差和受影响的 downstream 表/图。

# 28. 新对话最终状态页

任一新对话结束前必须生成：

```text
engineering/delayed_source_authority_v2_YYYYMMDD/FINAL_STATUS.md
```

最小内容：

```text
# FINAL_STATUS

git_head:
git_status:
harness_version:
claim_boundary:

| Gate | Status | Evidence | Blocking? | Next action |
|---|---|---|---:|---|
| G0 | ... | ... | ... | ... |
| G1 | ... | ... | ... | ... |
...

Files created:
- ...

Files intentionally not modified:
- baseline geometry
- prompt source cards
- Step05 authority outputs
- legacy delayed authority outputs
- manuscript source

Resource approvals requested:
- none / ...

Numerical promotions made:
- none / ...

Manuscript changes applied:
- none unless APPLY_MANUSCRIPT_CHANGES=true
```

如果只完成 WP00/WP01，也必须写 FINAL_STATUS；不要让新对话结束在“正在分析”而没有状态页。
