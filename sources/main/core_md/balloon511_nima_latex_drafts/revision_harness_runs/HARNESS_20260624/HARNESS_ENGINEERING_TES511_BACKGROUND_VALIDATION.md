---
document_type: harness_engineering
project: TES_511_BALLOON
workstream: background-validation-and-shield-material-comparison
version: 1.0
status: ready-for-codex
execution_style: bounded-evidence-first
primary_language: zh-CN
---

# 0. Codex 执行合同

你是该工程任务的 **orchestrator**。目标不是自由探索，也不是重构整个项目，而是在严格边界内完成以下工作：

1. 闭合当前 CsI baseline 的 prompt 源构建、单位、面积、far-field radius、角分箱和权重；
2. 分析 final W2 prompt `eplus` survivor 的物理来源；
3. 提高 delayed selected-rate 的统计可信度并给出收敛/不确定度；
4. 构建一个与 CsI 几何完全同包络、仅主动屏蔽材料替换为 BGO 的派生版本；
5. 用相同 source、统计策略和后处理流程比较 CsI 与 BGO；
6. 更新/生成一份面向论文的中文技术说明文档，解释上述工作的必要性、结果和对 NIM A 论文的帮助。

本任务必须是**有限状态、证据优先、可停止**的工程流程。异常结果不得触发自动调参或无限重跑。

# 1. 最终交付物

工程根目录建议为：

```text
engineering/background_validation_YYYYMMDD/
```

必须产生：

```text
00_manifest/
  baseline_authority_manifest.json
  baseline_authority_manifest.md
  file_hashes.sha256
  execution_environment.json
  decision_log.md

01_prompt_source_audit/
  source_card_inventory.csv
  source_flux_bin_audit.csv
  prompt_normalization_audit.json
  prompt_normalization_audit.md
  prompt_weight_closure.csv
  farfield_geometry_audit.json
  farfield_geometry_audit.md

02_prompt_eplus_provenance/
  eplus_survivor_events.csv
  eplus_survivor_process_summary.csv
  eplus_survivor_volume_summary.csv
  eplus_survivor_provenance.json
  eplus_survivor_provenance.md

03_delayed_convergence/
  delayed_run_manifest.csv
  delayed_selected_rate_convergence.csv
  delayed_selected_rate_convergence.json
  delayed_selected_rate_convergence.md
  delayed_selected_decomposition.csv

04_bgo_variant/
  geometry_diff_whitelist.json
  geometry_diff_whitelist.md
  bgo_geometry_manifest.json
  overlap_check.log
  shield_volume_map.csv
  bgo_material_resolution.md

05_matched_runs/
  csi/
  bgo/
  matched_run_matrix.csv
  matched_run_status.json

06_comparison/
  csi_bgo_rate_comparison.csv
  csi_bgo_rate_comparison.json
  csi_bgo_rate_comparison.md
  csi_bgo_energy_band_comparison.csv
  csi_bgo_isotope_comparison.csv
  csi_bgo_figures/

07_manuscript_support/
  background_validation_necessity_and_paper_impact_final.md
  manuscript_insertions_en.md
  manuscript_claim_boundary.md
  manuscript_numbers_manifest.json
  supplement_tables.md
```

不得覆盖现有 baseline 输出；所有新运行进入新的 run directory。

# 2. 非协商性权威规则

## 2.1 Veto 权威

定量主动屏蔽选择由 Step05 后处理定义：

```text
shield_total_keV < 50 keV
coincidence_window = 1 us
```

现有字段可能叫 `bgo_total_keV`，但语义是通用主动屏蔽总沉积能量。

强制规则：

- 不执行 CsI 40/60/90 keV detector-threshold 单元测试；
- 不将 `.det` trigger/noise threshold 当作 rate authority；
- 不修改 50 keV 或 1 us 以追求更好结果；
- CsI 与 BGO 必须调用同一份 Step05 选择代码或同一 hash 的不可变副本；
- 如必须泛化变量名，只允许增加兼容 alias，不允许改变选择数学定义。

## 2.2 论文 claim 边界

当前论文只声称：

> 当前 detector/cryostat proxy mass model 下，针对不可分辨 511 keV 窄线的 reference-exposure selected-rate statistical estimate。

本任务不得自动扩展到 flight-performance forecast。

## 2.3 Baseline 不可变

以下类型文件视为 read-only authority：

- 当前 fix5 geometry/setup/det；
- 当前 prompt/activation source cards；
- 当前 Step05 authority outputs；
- 当前 delayed fixed-source authority；
- 当前 manuscript source；
- 已 promotion 的 evidence reports。

任何变更必须写入派生目录。禁止原地编辑、覆盖或“顺手清理”。

# 3. 输入发现与权威优先级

## 3.1 文件发现原则

仓库中可能存在同名旧文件、`old/` 目录和 stale artifacts。不得仅凭 basename 选择输入。

每个候选输入必须记录：

- absolute/relative path；
- modification time；
- SHA256；
- git commit/hash（若可用）；
- 是否位于 `old/`、archive 或 current output；
- 被哪个当前 report/manifest 引用；
- authority status：`CURRENT`、`ARCHIVED_SUPPORT`、`STALE`、`UNKNOWN`。

优先级：

1. 当前 paper-evidence manifest 明确指向的文件；
2. 当前 promoted report 指向的文件；
3. 当前 run directory 中的 manifest/normalization；
4. manuscript 中明确引用的路径；
5. `old/` 只作为代码考古，不作为数值权威。

若有两个候选均可能是 authority，状态设为 `BLOCKED_AMBIGUOUS_AUTHORITY`，停止该 work package，不得猜测。

## 3.2 已知参考文件名

orchestrator 应在仓库内定位下列 basename 或其当前替代版本：

```text
balloon511_nima_draft_en.{tex,md,pdf}
project_internal_fix_queue.md
11_fix5_w2_prompt_delayed_energy_band_stats.md
run_equiv2602_pipeline_NEW_GEO.py
build_fix5_1of10_exactpos_delayed_source.py
build_fixed_delay_source.py
makedecaysourcewithplot_rpip.py
DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.{geo,det,geo.setup}
side_window_material_path_audit_fix5.json
USER_CYLMAG_REDESIGN_MULTIHOLEW_FIX5_SUMMARY.md
build_v3p5_centerfinger_step05_l1_response.py
```

路径不同不构成错误；必须通过 manifest 和 hash 确认。

# 4. Agent 架构与上下文隔离

## 4.1 Agent 层级

仅允许两层：

```text
orchestrator
  ├── provenance_agent
  ├── prompt_audit_agent
  ├── prompt_provenance_agent
  ├── delayed_agent
  ├── bgo_geometry_agent
  ├── run_agent
  ├── comparison_agent
  └── manuscript_support_agent
```

子 agent 不得再创建子 agent。

## 4.2 Context packet

orchestrator 为每个 agent 生成独立 work packet：

```text
work_packets/WPxx_<name>.md
```

每个 packet 只能包含：

1. 单一任务目标；
2. 输入 allowlist；
3. 禁止读取/修改列表；
4. 输出 schema；
5. acceptance criteria；
6. 最大迭代次数；
7. stop/failure 状态。

不得把整个对话、完整 manuscript、全部 raw outputs 同时塞给每个 agent。

## 4.3 Agent 间通信

agent 只能通过其输出目录中的：

- `summary.json`；
- `summary.md`；
- 明确定义的 CSV/manifest；

向 orchestrator 传递信息。

orchestrator 默认只读取每个 agent 的结构化 summary，不读取大型 raw files。只有 validation fail 时，才允许针对单一问题打开最小必要文件。

## 4.4 文件写入隔离

每个 agent 只能写自己的工作目录。禁止两个 agent 同时编辑：

- baseline geometry；
- selection code；
- manuscript；
- shared manifest。

最终合并只由 orchestrator 完成。

# 5. 有限状态机

```text
S0 DISCOVER_BASELINE
  -> G0 AUTHORITY_LOCKED
S1 AUDIT_PROMPT_SOURCE
  -> G1 PROMPT_NORMALIZATION_PASS | WARN | BLOCKED
S2 TRACE_EPLUS_SURVIVORS
  -> G2 EPLUS_PROVENANCE_PASS | INSUFFICIENT_TRACE
S3 CONVERGE_DELAYED
  -> G3 DELAYED_CONVERGED | DELAYED_STAT_LIMITED
S4 BUILD_BGO_VARIANT
  -> G4 BGO_GEOMETRY_EQUIVALENT | BLOCKED_MATERIAL
S5 RUN_MATCHED_PILOT
  -> G5 PILOT_PASS | PILOT_FAIL
S6 RUN_MATCHED_FULLSTAT
  -> G6 RUNS_COMPLETE | RESOURCE_BLOCKED
S7 COMPARE_AND_INTERPRET
  -> G7 COMPARISON_COMPLETE
S8 BUILD_PAPER_SUPPORT
  -> DONE
```

任何 `BLOCKED_*` 都是合法终点。不得为消除 BLOCKED 状态而无限搜索或自行改变科学定义。

# 6. 循环与重试限制

- 每个 work package 最多 2 次实现尝试；
- 每个 validation failure 最多允许 1 次确定性修复后重试；
- 物理结果“不符合预期”不属于可重试错误；
- 统计不足只能进入预先批准的下一统计级别一次；
- 不允许自动改变 threshold、energy window、geometry thickness、source flux 或 selection；
- 不允许为了让 CsI/BGO 差异显著而持续加统计；
- 达到 stop condition 后必须输出状态报告并结束。

# 7. Work Package 00：Baseline authority lock

## 7.1 目标

固化当前 CsI baseline 的全部输入、运行命令和结果 authority。

## 7.2 操作

1. 定位当前 fix5 geometry、det、setup；
2. 定位 prompt source directory 和 source migration manifest；
3. 定位 instant/buildup run manifests、normalization、commands 和 seeds；
4. 定位 fixed delayed source、weighted RPIP table 和 exact-position manifest；
5. 定位 Step05 parser/selection code及 authority outputs；
6. 定位 manuscript 当前 source；
7. 生成 SHA256 和 git status；
8. 标记旧的/stale 结果，特别是旧 zero-event upper limit 或旧 geometry。

## 7.3 输出 contract

`baseline_authority_manifest.json` 至少包含：

```json
{
  "status": "PASS|BLOCKED_AMBIGUOUS_AUTHORITY",
  "geometry": {"path": "", "sha256": ""},
  "detector_map": {"path": "", "sha256": ""},
  "setup": {"path": "", "sha256": "", "surrounding_sphere_cm": null},
  "prompt_sources": [{"particle": "", "path": "", "sha256": ""}],
  "prompt_run": {"manifest": "", "normalization": "", "command": ""},
  "buildup_run": {"manifest": "", "normalization": "", "command": ""},
  "delayed_source": {"path": "", "activity_Bq": null, "sha256": ""},
  "step05": {"code": "", "code_sha256": "", "outputs": []},
  "manuscript": {"path": "", "sha256": ""},
  "stale_artifacts": []
}
```

## 7.4 Gate G0

只有 authority 唯一且 hashes 完整时才进入后续阶段。

# 8. Work Package 01：Prompt source normalization audit

## 8.1 目标

证明或否定当前 prompt source 构建在 units、solid angle、source area、far-field radius、oversampling 和 selected-rate weighting 上的正确性。

## 8.2 必须回答的问题

### A. EXPACS/PARMA 到 source card

- 原始表的单位是什么；
- 能量积分如何完成；
- equal-\(\mu\) 20 bins 是否满足：

\[
\Delta\Omega=2\pi\Delta\mu=0.6283185307\;{\rm sr};
\]

- source card 中每个 bin 的 flux 是 differential 还是 bin-integrated；
- 20 bins 之和是否重现每个粒子族的积分通量；
- up-going/down-going 是否各计一次且无 overlap；
- azimuth 是否已在 bin flux 中积分，还是由 source type 采样。

### B. Cosima far-field source 语义

- source type 的面积约定是圆盘 \(\pi R^2\)、球面 \(4\pi R^2\) 还是内部自动 geometry factor；
- projected-area factor 由 EXPACS 积分、source generator 或 Cosima 哪一层处理；
- 禁止在两层重复乘 \(|\cos\theta|\)。

优先依据本地 Cosima manual、实际 source card 和现有 source builder。无法确定时输出 `BLOCKED_SOURCE_SEMANTICS`，不得猜测。

### C. Radius 和面积

交叉比较：

- `.geo.setup` 的 `SurroundingSphere`；
- source-card radius；
- source migration manifest；
- runner `--farfield-radius-cm` 实际 CLI；
- `normalization.json`；
- geometry 的最小 enclosing radius 和 margin。

特别检查：runner 默认 `35.0 cm` 与当前 fix5 setup 的 `60 cm` 是否被实际命令覆盖。

要求：

```text
all_authoritative_radii_equal within 1e-9 cm
area_cm2 == pi * radius_cm**2 within 1e-12 relative
```

### D. Splits、replicas 和 weights

验证：

- gamma total events = splits 之和；
- non-gamma base events 按 flux ratio 计算；
- 每个 replica 使用唯一 seed；
- total non-gamma weight 除以 replica count 一次且仅一次；
- no missing/duplicate run files；
- source tag 与 Step05 stream/tag 一致。

### E. Selected-rate closure

对每个 particle family 建立：

\[
w_j=\frac{F_j\pi R^2}{N_{j,\rm total}},
\qquad
R_{j,\rm sel}=\sum_{e\in j,\rm sel}w_e,
\qquad
\sigma^2_{j,\rm MC}=\sum_{e\in j,\rm sel}w_e^2.
\]

将独立重建值与 Step05 rate 比较。

## 8.3 解析 sanity checks

在 60 cm 和当前积分通量下，报告但不硬编码为 acceptance authority：

- far-field area 约 11309.7336 cm²；
- gamma physical source-plane rate 约 5.43×10⁴ s⁻¹；
- 10⁷ gamma 约对应 184.2 s；
- positron physical source-plane rate约 1.32×10³ s⁻¹。

这些只用于识别数量级错误。

## 8.4 可选最小 toy validation

只有在本地 manual/source semantics 无法闭合时，允许构建一个解析可计算的空几何/平面 crossing harness。该 test 只验证 source generator convention，不进入论文结果。

## 8.5 Acceptance G1

`PASS` 必须同时满足：

- radius authority 唯一；
- source flux bin sum relative closure ≤ 1e-8；
- per-family generated counts/replicas/seeds 完整；
- independent selected-rate reconstruction relative difference ≤ 1e-6；
- area/projected-area 处理有明确、可引用的代码/manual 证据；
- 所有 rate 都有 `sum_w2`。

若发现错误，输出 `FAIL_NORMALIZATION`，列出修复方案；不得自动重跑 full-stat，必须先由 orchestrator 生成 change request。

# 9. Work Package 02：Prompt `eplus` survivor provenance

## 9.1 目标

确定 final W2 prompt `eplus` 事例的真实生成和传播路径。

## 9.2 首选数据源

优先使用当前 SIM/Step05 event catalog 中已有：

- event ID；
- primary tag；
- IA/HT/CC records；
- parent/track IDs；
- process names；
- interaction/production volume；
- positions and directions；
- TES/shield hit mapping。

不得一开始就重跑 full-stat。

## 9.3 输出分类

每个 survivor 至少分类为：

```text
A aperture-coupled annihilation photon
B annihilation/secondary photon generated in nearby passive material
C direct charged-particle TES deposition
D neutron/other mis-tag impossible under current stream logic
E incomplete trace information
F parser/event-link inconsistency
```

同时输出：

- annihilation vertex distribution；
- creator process distribution；
- production volume distribution；
- entry-path distribution；
- single/multi-pixel breakdown；
- first TES interaction distribution。

## 9.4 Targeted trace run 条件

仅当现有数据中 `E incomplete trace information` 超过 20% 时，允许进行小规模 targeted trace run：

- 只跑 `eplus`；
- 使用相同 source card/radius；
- 启用必要的 track/interaction storage；
- 先 10³–10⁴ events smoke；
- 不超过一次统计升级；
- 不把 targeted trace rate 当作 rate authority。

## 9.5 Acceptance G2

- 至少 80% survivor 能归入 A–C；或
- 明确输出 `INSUFFICIENT_TRACE` 并说明缺失字段。

不要求结果符合某个预期物理路径。

# 10. Work Package 03：Delayed selected-rate convergence

## 10.1 目标

将当前 30-event delayed W2 结果升级为带明确 MC uncertainty 和 sampling variance 的结果。

## 10.2 两类方差必须分开

### A. Decay transport variance

固定同一 weighted production-position source，改变 decay transport seed。

### B. Production-position sampling variance

改变 production-position sample seed，保持总活度、M 和 transport strategy 一致。

## 10.3 分级统计方案

agent 首先根据当前效率、CPU、输出量估算达到下列目标所需资源：

- 最低目标：final W2 selected events ≥ 100；
- 优选目标：pooled selected events ≥ 300；
- 目标相对 MC uncertainty：≤ 10%；
- 不以达到 5% 为强制要求。

建议但不强制的结构：

```text
3 independent decay seeds × N decays
3 independent production-position seeds × reduced/pilot N decays
```

不得在没有 resource estimate 的情况下直接发起 10⁷ 级运行。

## 10.4 每个 run 必须记录

```text
source_activity_Bq
M
position_sampling_seed
decay_transport_seed
generated_decays
selected_events
sum_w
sum_w2
selected_rate_cps
mc_sigma_cps
geometry_hash
source_hash
selection_code_hash
```

## 10.5 Decomposition

至少输出：

- isotope；
- source volume/material；
- production particle family（若可追踪）；
- energy band；
- final selected rate。

重点检查 Cu-64、Cu-62、I-128、W-187 等 current leading inventory/selected isotopes。

## 10.6 Acceptance G3

`DELAYED_CONVERGED`：

- pooled W2 relative MC uncertainty ≤ 10%；
- run-to-run scatter 与 `sum_w2` 统计相容，或被单独量化；
- 未发现 activity loss/duplication；
- isotope/volume fractions 无单 seed 极端支配。

若受资源限制未达到，输出 `DELAYED_STAT_LIMITED`，保留已完成结果并停止；不得无限加统计。

# 11. Work Package 04：BGO same-envelope derived geometry

## 11.1 科学定义

BGO variant 是：

> 与当前 CsI baseline 完全相同的几何包络、分段、开孔、位置和后处理，仅将主动屏蔽体积的材料由 CsI 替换为 BGO。

它不是等质量比较，也不是厚度优化。

## 11.2 最小变更策略

第一版必须保留现有 shield volume identifiers 和 detector mapping，以隔离材料变化并复用 Step05 parser。允许在 manifest/report 中将其标记为 `legacy_volume_name_with_BGO_material=true`。

只允许以下变更：

```text
<whitelisted active-shield volume>.Material CsI
    ->
<same volume>.Material BGO
```

以及派生 setup 名称、输出路径、注释和 manifest。

禁止变更：

- Shape；
- Shape parameters；
- Position/Rotation；
- Mother；
- segmentation；
- aperture cuts；
- detector volume mapping；
- TES/passive materials；
- source radius；
- Step05 selection。

## 11.3 Shield volume allowlist

从 baseline geometry 和 `.det` 自动提取所有属于主动 CsI shield 的 volumes，生成 `shield_volume_map.csv`。不要手工维护不完整列表。

需覆盖：

- side segments；
- side-port above/below pieces；
- Boolean window-band pieces；
- bottom quadrants；
- top annulus segments；
- 任何当前 Step05 shield sum 所包含的附加 shield volumes。

## 11.4 BGO material resolution

顺序：

1. 检查当前 MEGAlib/Geomega material database 是否已有 `BGO`；
2. 通过 geometry parse/smoke 验证可解析；
3. 记录实际 composition/density authority；
4. 如不存在，不得自行凭记忆创建材料。输出 `BLOCKED_MATERIAL`，列出需要用户批准的 material definition。

## 11.5 Geometry validation

必须执行：

- normalized geometry diff；
- whitelist checker；
- detector-reference check；
- side-window path audit；
- overlap check；
- shield volume count/mapping equality；
- setup surrounding sphere equality。

## 11.6 Acceptance G4

- 所有非材料几何字段 hash-equivalent；
- whitelist 外 diff count = 0；
- overlap check PASS；
- detector references PASS；
- source sphere unchanged；
- BGO material successfully resolved。

# 12. Work Package 05：Matched CsI/BGO simulations

## 12.1 必须运行的链

对 CsI 与 BGO 使用同一 run matrix：

1. prompt instant transport；
2. activation buildup transport；
3. fixed day-15 inventory construction；
4. production-position-sampled delayed source；
5. delayed decay transport；
6. focused science replay；
7. identical Step05 selection；
8. energy-band and W2 summaries。

## 12.2 Common-random-number policy

在可行时保持：

- source cards 相同；
- event counts 相同；
- gamma splits 相同；
- non-gamma replicas 相同；
- per-job seeds 相同；
- position-sampling seeds 相同；
- decay transport seeds 相同。

材料变化会导致轨迹分叉，因此不能假设完全配对方差抵消；但一致 seeds 有助于审计和部分相关比较。

## 12.3 Staged execution

### Stage P0：syntax/geometry smoke

- 每粒子族极小统计；
- 检查解析、输出、isotope store、Step05 ingest。

### Stage P1：pilot

- 建议 1/100–1/10 baseline statistics；
- 检查 event rate、activity、selected counts 和资源估算；
- 不做材料优劣结论。

### Stage P2：matched production

只有 P1 通过且 resource guard 允许时运行。

## 12.4 Resource guard

沿用或强化当前 runner 的 guard：

```text
max events without explicit approval: 5,000,000 per launch batch
max estimated output without approval: 100 GB
max estimated CPU without approval: 7 CPU-days
```

若完整 matched runs 超限，生成：

```text
RESOURCE_APPROVAL_REQUIRED.md
```

并停止。不得自行绕过 `--allow-heavy-run`。

## 12.5 Run parity acceptance G5/G6

每个 CsI/BGO pair 必须满足：

- same source hash；
- same flux table；
- same radius；
- same event counts；
- same seeds；
- same selection code hash；
- only geometry material hash differs；
- run complete and no parser errors；
- normalization closure passes independently。

# 13. Work Package 06：CsI–BGO 比较

## 13.1 必须比较的量

### Geometry/material

- shield volume；
- density/material authority；
- shield mass（若工具可可靠计算）；
- geometry equality status。

### Prompt

- raw / active-veto / final W2 rates；
- prompt tag decomposition；
- `eplus` 和 neutron survival；
- broader energy-band spectra；
- selected event multiplicity。

### Delayed

- total day-15 activity；
- isotope inventory；
- material/volume activity；
- W2 raw/final delayed rate；
- Cu-64/Cu-62、I/Ge/Bi-related isotope contributions；
- broader energy bands。

### Signal

- W2 selected signal rate；
- active-veto survival；
- topology survival；
- selected effective area。

### Derived

- total background；
- prompt/delayed fractions；
- rate ratios；
- uncertainty on difference/ratio；
- diagnostic sensitivity only if both variants statistics adequate。

## 13.2 Statistics

对独立加权 samples：

\[
\sigma^2_R=\sum_i w_i^2.
\]

差值：

\[
\sigma^2_{R_B-R_C}=\sigma_B^2+\sigma_C^2
\]

若使用配对/common-random-number covariance，必须从 event pairing 实际估计，不得假设。

材料优劣判据：

- 差异 < 2σ：只写“未分辨差异”；
- 差异 ≥ 2σ 但 < 3σ：写“suggestive”；
- 差异 ≥ 3σ 且所有 normalization/geometry gates 通过：才可写“statistically resolved in the present simulation”。

不得把低统计百分比变化写成确定设计结论。

## 13.3 Interpretation matrix

comparison agent 必须按以下顺序解释：

1. 是否 normalization-equivalent；
2. 是否 geometry-equivalent；
3. inventory 是否改变；
4. selected delayed 是否改变；
5. prompt veto/secondary 是否改变；
6. signal acceptance 是否改变；
7. 总体 W2 是否由 prompt 还是 delayed 驱动。

# 14. Work Package 07：论文支持文档

## 14.1 目标

根据实际 PASS/WARN/BLOCKED 结果，生成：

```text
07_manuscript_support/background_validation_necessity_and_paper_impact_final.md
```

该文档必须更新初始技术说明，而不是简单复制预设结论。

## 14.2 文档结构

1. 当前论文 claim boundary；
2. veto authority；
3. prompt normalization audit 结果；
4. `eplus` survivor 物理来源；
5. delayed convergence 和主导 isotope/volume；
6. CsI–BGO 对比；
7. 对论文 Methods/Results/Discussion 的具体帮助；
8. 可写入论文的英文段落；
9. 不应声称的内容；
10. provenance 表。

## 14.3 Manuscript 修改权限

默认只生成 insertion suggestions，不直接修改 manuscript。

只有用户显式设置：

```text
APPLY_MANUSCRIPT_CHANGES=true
```

orchestrator 才可创建 manuscript 派生副本。即便如此：

- 不覆盖原稿；
- 不改变 headline 数字，除非新 authority manifest 明确 promotion；
- 每个变化生成 unified diff；
- 不把内部路径、seed/debug 语言写入正文。

# 15. 失败状态定义

允许的终止状态：

```text
PASS
WARN_STAT_LIMITED
WARN_TRACE_INCOMPLETE
BLOCKED_AMBIGUOUS_AUTHORITY
BLOCKED_SOURCE_SEMANTICS
BLOCKED_RADIUS_MISMATCH
BLOCKED_MATERIAL
BLOCKED_RESOURCE_APPROVAL
FAIL_NORMALIZATION
FAIL_GEOMETRY_DIFF
FAIL_RUN
FAIL_SELECTION_PARITY
```

每个失败状态必须包含：

- evidence；
- affected claim；
- minimal next action；
- 是否需要用户决策；
- 未执行的后续 phases。

不得把失败状态自动转成“继续搜索直到通过”。

# 16. Change-control 规则

任何代码或配置修改必须：

1. 在新 branch/worktree 或派生目录；
2. 有单一目的；
3. 有 before/after hash；
4. 有 test；
5. 有 rollback；
6. 不混合 physics change 与 refactor；
7. 不在同一 commit 中同时改 source normalization、geometry 和 selection。

推荐 commit 划分：

```text
chore: lock baseline authority and hashes
feat: add prompt normalization audit harness
feat: add eplus survivor provenance report
feat: add delayed convergence runner/report
feat: derive BGO material-only geometry variant
feat: add matched CsI/BGO run matrix
feat: add CsI/BGO comparison report
 docs: add manuscript support package
```

# 17. 测试策略

## 17.1 快速静态测试

- source-card parser tests；
- units tests for area/weight equations；
- unique seed test；
- geometry diff whitelist；
- shield volume extraction test；
- result schema validation；
- no-overwrite test。

## 17.2 Smoke tests

- geometry parse；
- one/few event source parse；
- Step05 ingest；
- isotope store existence；
- BGO material resolution。

## 17.3 不做的测试

- CsI detector-threshold 40/60/90 keV 单元测试；
- 在线 trigger threshold calibration；
- full TES electronics response；
- threshold optimization。

# 18. 质量门摘要

| Gate | 必须条件 | 失败后动作 |
|---|---|---|
| G0 Authority | 输入唯一、hash 完整 | BLOCKED，用户决策 |
| G1 Prompt normalization | units/radius/area/weights/rates 闭合 | 修复审计或 FAIL；不跑 BGO full-stat |
| G2 eplus provenance | ≥80% 可分类或明确 trace 缺失 | 输出 WARN；不调物理参数 |
| G3 Delayed convergence | ≤10% 或统计受限结论 | 输出 PASS/WARN；最多一次升级 |
| G4 BGO geometry | material-only diff、overlap PASS | 修复一次，否则 BLOCKED |
| G5 Pilot | run/selection parity | 修复一次，否则停止 |
| G6 Full matched runs | 资源许可、全部 manifest 完整 | 资源超限则申请批准 |
| G7 Comparison | uncertainty、rate ratio、claim boundary | 只报可支持结论 |
| G8 Paper support | 所有数字可追溯 | 不直接覆盖 manuscript |

# 19. Orchestrator 最终检查清单

- [ ] 没有修改 baseline authority files；
- [ ] 没有执行 CsI threshold 单元测试；
- [ ] 50 keV/1 us 后处理在两个材料版本中完全一致；
- [ ] radius 的实际运行值来自 CLI/manifest，而非代码默认猜测；
- [ ] \(\pi R^2\)、solid angle 和 projected-area 没有双计；
- [ ] replicas 只去权重一次；
- [ ] Step05 rate 可从 event weights 重建；
- [ ] prompt `eplus` survivor 有物理 provenance 或明确缺失状态；
- [ ] delayed 结果有 `sum_w2` 和 seed variance；
- [ ] BGO variant 只有 material whitelist diff；
- [ ] CsI/BGO 使用相同 source、seeds、selection 和统计策略；
- [ ] 所有比较都带 uncertainty；
- [ ] 不显著差异没有被写成设计优劣；
- [ ] 所有新数字进入 manuscript_numbers_manifest；
- [ ] agent 未递归产生 subagent；
- [ ] 每个 work package 未超过重试限制；
- [ ] 未触发无限运行或自动优化。

# 20. Codex 启动指令

执行时遵循以下顺序，不得跳过 G0/G1：

```text
1. Read this harness only.
2. Create the engineering root and decision log.
3. Run WP00 and stop if authority is ambiguous.
4. Run WP01; do not start BGO production unless prompt normalization is PASS.
5. Run WP02 and WP03 independently using isolated work packets.
6. Build BGO material-only geometry under WP04.
7. Run smoke and pilot before any heavy matched production.
8. Respect resource guard; emit approval request rather than bypassing it.
9. Complete comparison with explicit MC uncertainties.
10. Generate the final paper-support Markdown and insertion suggestions.
11. Do not edit the manuscript unless APPLY_MANUSCRIPT_CHANGES=true.
12. Finish with a one-page FINAL_STATUS.md listing PASS/WARN/BLOCKED per gate.
```

本工程的成功标准不是“所有结果都符合预期”，而是：**每个结论都有唯一 authority、单位和权重闭合、统计误差明确、材料比较受控、且流程能在遇到不确定性时可靠停止。**

# 21. 新对话接手指南

本节是给新 Codex/GPT Pro 对话的启动层。新对话不应只读一段聊天记录后
直接运行模拟；必须先把当前项目的 authority、边界和已有证据锁住。

## 21.1 新对话第一条提示词

建议在新对话中直接粘贴以下提示词：

```text
你正在接手 `/home/ubuntu/TES_511_Balloon` 的
TES_511_BALLOON background-validation-and-shield-material-comparison 工程。

先阅读：
1. `core_md/balloon511_nima_latex_drafts/revision_harness_runs/HARNESS_20260624/HARNESS_ENGINEERING_TES511_BACKGROUND_VALIDATION.md`
2. `core_md/balloon511_nima_latex_drafts/revision_harness_runs/HARNESS_20260624/TES_511_background_validation_necessity_and_paper_impact.md`
3. `AGENTS.md`
4. `README.md`
5. `core_md/METHOD_FIX5_SIM_CLOSURE.md`
6. `core_md/fix5_benchmarks.json`
7. `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260623_delay_processing_reaudit_3agent/11_fix5_w2_prompt_delayed_energy_band_stats.md`

目标不是重构全项目，也不是优化几何。目标是在新派生目录
`engineering/background_validation_YYYYMMDD/` 下执行该 harness：
先锁定 baseline authority，再审计 prompt source normalization，再追踪
final W2 prompt eplus survivor，再提高 delayed selected-rate 统计可信度，
最后才构建 same-envelope BGO 材料替换版本和 matched comparison。

非协商边界：
- 不覆盖现有 fix5/v3p5/BGO/new_geo_re authority outputs。
- 不改 Step05 的 50 keV active-shield veto 和 1 us coincidence window。
- 不把 `.det` trigger/noise threshold 当作论文 rate authority。
- 不自动调几何、厚度、阈值、energy window 或 source flux。
- 不在 G0/G1 通过前运行 BGO full-stat 或 heavy matched production。
- 任何 BLOCKED/WARN/FAIL 都是合法终点，必须输出证据和最小下一步。

请先执行 WP00 authority lock，只生成 manifest/hash/decision log；
如果 authority 不唯一，停止并报告 `BLOCKED_AMBIGUOUS_AUTHORITY`。
```

## 21.2 新对话必须掌握的项目地图

当前仓库定位：

```text
repo root:
  /home/ubuntu/TES_511_Balloon

current fix5 geometry authority:
  outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/

current fix5 Step05 authority:
  stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/

current fix5 final reports:
  outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/

current prompt source cards:
  config/megalib_sources_fullsphere20_fix5_tilt45/

current delayed source build outputs:
  runs/step02_decay_source_fix5_fullstat_v2/
  runs/step02_delay_fix_fix5_fullstat_v2/

current focused signal replay:
  stepwise_maintenance/step09_optics_bridge/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/

manuscript tree:
  core_md/balloon511_nima_latex_drafts/

new engineering outputs must go under:
  engineering/background_validation_YYYYMMDD/
```

`old/` 是历史代码和历史结果集合。除非某个当前 manifest 明确引用，`old/`
只能作为代码考古，不可作为当前数值 authority。

## 21.3 当前最小 authority allowlist

WP00 可以从以下文件开始定位；实际使用前仍必须记录 SHA256、mtime 和
authority status。

Geometry:

```text
outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup
outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo
outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det
outputs/reports/user_redesign_multiholeW_fix5_20260621/USER_CYLMAG_REDESIGN_MULTIHOLEW_FIX5_SUMMARY.md
outputs/reports/user_redesign_multiholeW_fix5_20260621/side_window_material_path_audit_fix5.json
```

Prompt and buildup:

```text
config/megalib_sources_fullsphere20_fix5_tilt45/
code/tools/run_equiv2602_pipeline_NEW_GEO.py
runs/step02_instant_fix5_fullstat_v2/normalization.json
runs/step02_instant_fix5_fullstat_v2/run_summary.csv
runs/step02_buildup_fix5_fullstat_v2/normalization.json
runs/step02_buildup_fix5_fullstat_v2/run_summary.csv
```

Delayed:

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
```

Step05 and analysis:

```text
old/code/tools/build_v3p5_centerfinger_step05_l1_response.py
stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_rates.csv
stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_response_summary.json
stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/work/event_catalog.pkl
outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_w_activation_selected_w2_audit.json
outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_w_activation_selected_w2_events.csv
```

Manuscript and context:

```text
core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.tex
core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.md
core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260623_delay_processing_reaudit_3agent/11_fix5_w2_prompt_delayed_energy_band_stats.md
```

`upload_20260623/` 是给外部 GPT review 的 compact package。它可作人类/GPT
上下文包，但不是新的 simulation authority；其中的文件是拷贝。

# 22. 工程实现骨架

## 22.1 推荐目录初始化

新对话执行第一步应创建：

```text
engineering/background_validation_YYYYMMDD/
  00_manifest/
  work_packets/
  scripts/
  logs/
```

`YYYYMMDD` 使用当前日期。若目录已存在，不覆盖；创建
`engineering/background_validation_YYYYMMDD_runNN/`。

`00_manifest/decision_log.md` 第一行必须记录：

```text
started_at: <ISO8601>
git_head: <hash>
git_status: <clean|dirty>
harness: HARNESS_ENGINEERING_TES511_BACKGROUND_VALIDATION.md
```

## 22.2 禁止直接修改的路径

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

例外：允许读取这些路径；允许在 `engineering/background_validation_*` 下写
derived scripts、reports、copied manifests 和 lightweight derived data。
任何需要新 Cosima transport 的阶段必须写入新的 `runs/background_validation_*`
或 harness 专属 run directory，并先进入 decision log。

## 22.3 WP00 可执行骨架

WP00 不运行 Cosima，只做发现、hash、manifest。建议生成一个本地脚本：

```text
engineering/background_validation_YYYYMMDD/scripts/wp00_lock_authority.py
```

脚本职责：

1. 解析本节 allowlist；
2. 对每个存在文件计算 SHA256、size、mtime；
3. 标记 `old/`、`upload_20260623/`、archive/stale 候选；
4. 读取 `.geo.setup` 并解析 `Include` 和 `SurroundingSphere`；
5. 读取 run `normalization.json` 的 `farfield_radius_cm`；
6. 读取 Step05 summary 的 input paths；
7. 输出 `baseline_authority_manifest.json/md` 和 `file_hashes.sha256`。

WP00 不应把 `upload_20260623/` 中的拷贝当 authority。

## 22.4 WP01 可执行骨架

WP01 可以先写纯审计脚本，不做重跑：

```text
engineering/background_validation_YYYYMMDD/scripts/wp01_prompt_source_audit.py
```

脚本最小职责：

1. 解析 `Background_*_fullsphere20.source` 中每个 `.Flux`；
2. 汇总每个 particle 的总 source-card flux；
3. 对照 `source_migration_manifest.json`；
4. 读取 `runs/step02_instant_fix5_fullstat_v2/normalization.json`；
5. 确认实际 `farfield_radius_cm`，不得使用 runner 默认值猜测；
6. 计算 `area_cm2 = pi * radius_cm**2`；
7. 从 `run_summary.csv` 检查 splits/replicas、generated counts 和 seeds；
8. 从 Step05 event catalog 或 Step05 summary 独立重建 selected rates；
9. 输出 `prompt_weight_closure.csv`，包含 `sum_w` 和 `sum_w2`。

WP01 若无法确认 Cosima source-surface semantics，应输出
`BLOCKED_SOURCE_SEMANTICS`，而不是推断。

## 22.5 WP02 可执行骨架

WP02 先用现有 delayed/prompt SIM 和 event catalog，不重跑：

```text
engineering/background_validation_YYYYMMDD/scripts/wp02_trace_eplus_survivors.py
```

最小实现顺序：

1. 从 Step05 event catalog 复现 final W2 prompt `eplus` survivor index；
2. 取 `source_file` 和 `local_id`；
3. 打开对应 prompt eplus `.sim.gz`；
4. 按 `ID/local_id` 抽出该 event 的 `IA`、`CC HIT`、`HTsim` blocks；
5. 解析 `sec`、`prim`、`par`、`sproc`、`cproc`、`volume`、position、energy；
6. 用规则分类 A-F；
7. 输出 event CSV 和 process/volume summary。

如果 SIM 中没有足够 parent/track 信息，输出 `INSUFFICIENT_TRACE`；只有在
该状态下才考虑 targeted trace smoke。

## 22.6 WP03 可执行骨架

WP03 先做资源估算：

```text
engineering/background_validation_YYYYMMDD/scripts/wp03_delayed_resource_estimate.py
```

估算必须基于当前：

- delayed transport generated events；
- W2 final selected events；
- SIM/log size；
- wall/CPU time（若 log 可解析）；
- 目标 selected events 100/300 所需 decays。

只有估算低于 resource guard，才生成 run plan；否则输出
`RESOURCE_APPROVAL_REQUIRED.md`。

## 22.7 WP04 可执行骨架

BGO 几何脚本必须是 material-only derivation：

```text
engineering/background_validation_YYYYMMDD/scripts/wp04_build_bgo_same_envelope.py
```

最小顺序：

1. 从 `.det` 和 Step05 active-shield matching 逻辑提取 shield volumes；
2. 在 `.geo` 中定位这些 volume 的 `.Material CsI` 行；
3. 生成 whitelist；
4. 派生新 geometry directory；
5. 只替换 whitelist 行为 `Material BGO`；
6. 运行 parse/smoke/overlap 前先检查 BGO material 是否存在；
7. 输出 geometry diff whitelist 和 BGO geometry manifest。

找不到 BGO material 时必须停在 `BLOCKED_MATERIAL`。

# 23. Work Packet 模板

每个 agent packet 使用以下模板；orchestrator 不应把完整仓库上下文塞给所有
agent。

```text
# WPxx <name>

## Goal
<one task only>

## Allowed inputs
- <path>
- <path>

## Forbidden reads/writes
- do not write outside engineering/background_validation_YYYYMMDD/<wp_dir>
- do not modify baseline outputs/runs/stepwise_maintenance

## Required outputs
- summary.json
- summary.md
- <specific csv/json>

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
All rates must carry units and uncertainty. Physical surprise is not a retry
condition.
```

# 24. 当前已知物理事实，供新对话校准

这些是当前 evidence，不是新的 gate：

1. fix5 final W2 prompt rate `0.0366410230297 cps`，delayed rate
   `0.00257520348894 cps`。
2. final W2 prompt 中 `eplus` 为 `0.0318897456148 cps`，约占 prompt `87%`。
3. W2 delayed fraction 从 raw `3.76%` 上升到 final `6.57%`，所以不能说
   active veto/FoV preferentially suppresses delayed。
4. final W2 delayed selected events 当前为 30 个，全部来自 Cu-64/Cu-62，
   W/collimator selected contribution 为 0。
5. `1500-3000 keV` final delayed fraction 接近 `48.85%`，所以不能写
   activation negligible。
6. 当前最优先的解释缺口是 prompt `eplus` survivor 的实际产生体积/过程和
   source normalization/far-field semantics，而不是继续假设 delayed 混入 prompt。

若新运行发现这些数字变化，必须说明是新 authority 取代旧结果，还是统计/路径
选择不同造成的差异。

# 25. 新对话最终状态页

任一新对话结束前必须生成：

```text
engineering/background_validation_YYYYMMDD/FINAL_STATUS.md
```

最小内容：

```text
# FINAL_STATUS

git_head:
git_status:
harness_version:

| Gate | Status | Evidence | Blocking? | Next action |
|---|---|---|---:|---|
| G0 | ... | ... | ... | ... |
| G1 | ... | ... | ... | ... |
...

Files created:
- ...

Files intentionally not modified:
- baseline geometry
- baseline source cards
- Step05 authority outputs
- manuscript source

Resource approvals requested:
- none / ...
```

如果只完成 WP00/WP01，也必须写 FINAL_STATUS；不要让新对话结束在“正在分析”
而没有状态页。
