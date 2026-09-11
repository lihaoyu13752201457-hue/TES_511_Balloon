# P0 几何优化项目总交接：M05 主线与 SE3/SF3 动态账本

**优先级：P0 / 以后新 session 的唯一第一入口**  
**状态日期：2026-08-16（Asia/Shanghai）**  
**当前状态：SE3、SF3 Plan-1 均已完成；SF3 未晋级且不得补 full-stat；尚未找到最终最优几何。**

本文件取代旧的“逐份 README 复习法”，但不取代底层生成型 authority。新 session 应先完整阅读本文件并目视下方流程图；只有在核对数字、追溯争议或实施新候选时，才打开第 4 节列出的原始报告。旧 SE3/SF3 开跑前 handoff 只保留为 provenance，不能再当作待执行任务。

Authority 冲突时按以下顺序处理：

1. 当前候选的生成型小表、receipt、stage summary/manifest 与 final audit；
2. 完成后的 FINAL_REPORT；
3. 本文件的压缩摘要；
4. 开跑前 handoff、历史讨论和旧论文数值。

严禁为了“复习项目”扫描、打开、统计或哈希大型历史 SIM，也不要启动 transport。

---

## 1. 绝对保留：以 M05 流程图为纲的项目主线

这一节是项目方法合同。几何更换时不得随意改写；只有源模型、响应或 mission 的上位 authority 被明确替换时，才允许建立新版本并说明迁移理由。

![M05 corrected simulation workflow](assets/fig_simulation_workflow_corrected_zh_20260810.png)

随本交接冻结的图文件：

- PNG SHA256：`825f48a33a6ef9a5ce83c2c5a6b72e22bed7048c204a8604ec268af04a2e0dff`
- 可编辑 TeX SHA256：`0b47d025bb9a6e66f73485dd0847a99dacc6170d6b3d00886af65461fde777d6`

### 1.1 必须先覆盖图中的历史 mono-511 支路

图是概念流程纲要，不是当前源数值 authority。当前 corrected-keV profile 是 `unit_only_total_gamma`；broadband gamma 已包含 annihilation bump。因此当前只有三条物理目录流：focused signal、broadband instant prompt、actual-position delayed。**禁止再叠加独立 atmospheric mono-511。**

若未来确需 `continuum_plus_mono`，必须建立独立、单一环境、显式 line subtraction 且逐 bin flux-closed 的新源包；不能在当前源上直接相加。

### 1.2 永久流程链

```text
corrected-keV 八族大气源
  ├─ INSTANT
  │    → prompt detector-event catalog ────────────────────────────┐
  │                                                                │
  └─ BUILDUP
       → RP/TT 核素产生率
       → NUBASE state-aware inventory
       → actual production-position delayed source
       → delayed transport/event catalog ──────────────────────────┤
                                                                   │
511 keV science point source                                       │
  → Laue optics                                                    │
  → frozen full-envelope focal-plane EventList                     │
  → current geometry fresh signal transport/event catalog ─────────┤
                                                                   ↓
              common keyed measured detector response
          + geometry-pinned exact active-veto policy
          + W2 + retained Step05 Compton/FoV
                                                                   ↓
          selected signal rate + component background rates
             + family/parent/material/volume lineage
                                                                   ↓
               81-node / 20-day analytic mission fold
                     → S20, B20, Z20, F3
                                                                   ↓
                 matched geometry comparison
                   → 下一轮几何反馈
```

必须能用一句话复述：**prompt 是直接输运；delayed 必须由候选几何自己的 buildup/RP、inventory 和真实产生位置重建；focused signal 是独立的 37,194-ray 光学银行；三流经过同一响应/veto/Step05，再进行 81 节点、20 天任务折叠和几何比较。**

### 1.3 各层解释边界

- Geometry 只定义材料、质量、坐标、母女体和 active/passive 身份；静态几何本身不产生 cps。
- INSTANT 才是 prompt detector histories。BUILDUP/RP 不是 delayed cps。
- Inventory 的 Bq 是 delayed source strength，不是 detector-selected background。
- 每个候选必须独立完成 `buildup → inventory → actual-position source → delayed transport`；禁止借用前代几何 inventory 或轴对称重分布。
- Actual-position source 的 parent ZA/volume 由 provenance-bound position match 决定；transport 中的 INIT/daughter ZA 只是输运证据，不能替代 source-parent lineage。
- Frozen focused EventList 只属于 signal，不是第九个 atmospheric family；每个几何仍须 fresh signal transport。
- Stage 03 delayed catalog 是 response-neutral；Stage 04 才是 prompt、delayed、signal 的共同 selected-rate authority。
- Day-15 detector-plane rate 是诊断，不是 mission sensitivity，也不能单独决定几何晋级。
- 81-node mission 是 analytic family-scalar synthetic scenario，不是 81 次独立 transport，也不是实际飞行 telemetry。

### 1.4 永久归一化合同

Prompt 对每个 `geometry × family` 独立归一化：

\[
r^{\rm prompt}_{g,f}=\frac{N^{\rm selected}_{g,f}}{\sum TT_{g,f}}.
\]

Activation 对每个 `geometry × family × volume × ZA × state`：

\[
q_{g,f,v,Z,A,s}=\frac{\sum RP_{g,f,v,Z,A,s}}{\sum TT_{g,f}}.
\]

zero-RP job 的 TT 仍必须进入分母；NUBASE 非零激发态、未解析 state 和 holdout 必须 fail closed，不能静默并入 ground state。恒定照射 day-15 活度为

\[
A_{15}=q\left[1-\exp\!\left(-\ln2\,\frac{15\,\mathrm d}{t_{1/2}}\right)\right].
\]

Delayed 每个 family 的事件权重为

\[
w^{\rm delayed}_{g,f}=\frac{A^{\rm transported\ ground}_{15,g,f}}{N^{\rm triggers}_{g,f}},
\]

所有 trigger 都进入分母，包括没有 `IA DECA` 的记录。SF3/SE3 Plan-1 的 exact-position mixture 是筛选 authority；不能把 counting MC 与 position-mixture uncertainty 混作一项。

禁止跨 geometry、mode 或 family 混池 TT、RP、事件或权重。

### 1.5 Corrected source 与共同响应

- 只允许 corrected total-kinetic-energy keV 源。任何 source/card/header 出现 `cosima_spectra_dp_2602units` 都 fail。
- 八族为 `alpha, eminus, eplus, gamma, muminus, muplus, n, p`；20 个 equal-μ full-sphere bins，FarField 半径 60 cm。
- 非 alpha 能轴为 `MeV × 1000`；alpha 为 `MeV/nucleon × 4 × 1000`。Geometry、source card 与 SIM header 身份必须完全一致。
- 三流共同使用 keyed measured response：`FWHM=0.42 keV`、measured-pixel threshold `0.3 keV`、`W2=[510.58, 511.42] keV`、retained Step05 `side_keep_from_hits / reject_policy=keep`。
- SE3/SF3 active veto exact whitelist 是 3 个 BGO + 3 个 plastic。BGO 对应阈值为 `50/70/80 keV`，plastic 为 `50 keV`；它们是离线逐事件主动体积沉积和阈值，不是 native/hardware trigger。
- 被动 W、Cu、Nb 等永远不能因产生沉积而自动加入 veto。`passive` 只表示不产生 veto 信号，不表示它不会散射、成对产生或活化。
- 零 survivor 不是物理零，必须保留 finite Garwood upper。Componentwise proxy 只作保守端点报告，不是 joint 95% coverage。

### 1.6 Frozen signal 与 mission/F3

- Frozen full-envelope signal bank 恰为 37,194 条 511-keV rays；不改 ray ID、顺序、能量、方向或权重，不循环、不 bootstrap。
- 公共注入面 `xprime=-30.0001 cm`，输入光学面积 `20.08476 cm²`；每个候选用 fresh seed 重放，`Aeff_selected=20.08476×Nselected/37194`。
- Mission：81 synthetic trajectory nodes、20 d、TOA `F_ref=1e-4 ph cm^-2 s^-1`、source elevation 45°、day-0 inventory=0、节点间线性生产率的精确衰变卷积、81 点梯形积分、coincidence window `1e-6 s`；不得 day-15 reanchor。
- `Z20=S20/sqrt(B20)`；`F3=F_ref×3/Z20`。
- optics、atmosphere、trajectory、source-position、activation-yield systematics 尚未联合传播；任何 proxy 或 Plan-1 central 值都不能自动等同于 publication-level promotion。

### 1.7 永久安全与方法规则

- 新输出 write-once，使用 fresh、全局不重复 seeds；任何 receipt/header/source/geometry 不一致即无效。
- 不重跑已冻结 SE3/S3d 来“方便比较”，不扫描或哈希大型历史 SIM；只读取固定、命名的小型 authority，除非用户明确授权新的 transport/analysis。
- 511-keV focused-ray clearance 只证明 signal 光路不碰新材料，**不能证明高能大气 gamma 不会到达该材料。**
- 任何放在 active veto 内侧、靠近 TES 的高 Z 候选，在完整 transport 前必须先有 `Eγ>1.022 MeV` boundary-crossing、pair-vertex 和到 TES 后代路线 scorer；不能再以几何直觉或 focused-ray bank 代替背景暴露测量。
- Static geometry PASS、day-15 central 改善、低统计零计数或单个 proxy 都不能单独晋级几何；必须闭合候选自己的完整流程链。

---

## 2. 几何更新：可动态更新的优化账本

本节允许随新候选更新，因为项目尚未找到最优几何。更新本节时必须保留第 1 节，保留旧候选的 dated authority 和结论；可以更新“当前基线、当前候选、下一步”，但不能覆盖原始生成型结果。

### 2.1 截至 2026-08-16 的状态锁定

| 几何 | 角色 | 当前结论 |
|---|---|---|
| S3d-O8 | 冻结历史背景参照 | 提供统计目标和部分小表；历史 post-Be signal 不是 fair full-envelope denominator。 |
| SE3 | 当前冻结比较基线 | 有 corrected-keV central background 改善证据；尚无 fair S3d full-envelope F3 ratio，因此不是已证明的最终最优。 |
| SF3 | `SE3 + 三块近场 passive W` 严格加法试验 | central F3 比 SE3 差 `1.907343×`；`STOP__NO_FULLSTAT_TOPUP`，不晋级。 |
| V2A/V2B/V2C | 尚未完成的新方向 | 优先减/移 TES 近场 Cu、打断冷板投影视线；尚无 transport authority。 |

### 2.2 SE3 的几何与结果摘要

SE3 是冻结 S3d-O8 的受控 whitelist patch：五块冷板各用 48 个等效面积大孔（共 240 个物理孔）；保留 20 mm BPE 且只开 focused port；10 mm plastic 连续不打孔；`InstrumentFrame.Rotation 0 45 0` 冻结。相对 S3d-O8，五块板减重 `9.396009 kg`，全部 touched components 合计减重 `10.217192 kg`。

SE3 Plan-1 是 S3d-O8 每族/模式统计量的 `ceil(1/3)`，29 个有效 receipts：21 background、7 delayed、1 signal；μ+ transported-ground A15 为零，按 finite upper 的 `SKIP_ZERO_A15` 处理。

| SE3 指标 | 值 |
|---|---:|
| day-15 prompt W2 | 0 MC survivor，central `0 cps`；绝非物理零 |
| day-15 delayed W2 | 47 events，`0.0601133621 cps` |
| transported A15 | `1348.141992 Bq` |
| signal | `21657/37194`，Aeff `11.69478 cm²` |
| S20 / B20 / Z20 | `1279.288658 / 98257.66905 / 4.08117597` |
| central F3 | `7.35082246e-5 ph cm^-2 s^-1` |
| componentwise proxy F3 | `4.48131034e-4` |

相对 frozen S3d 小表，SE3 的 day-15 total central ratio 为 `0.680610709`、B20 ratio 为 `0.681380382`；但缺少同注入面、同 full-envelope 的 S3d signal denominator，所以 fair SE3/S3d F3 ratio 仍为 unavailable。SE3 是“当前比较基线”，不是“最终完成 promotion”。

### 2.3 SF3 与 SE3 的唯一几何差异

SF3 静态 authority 为 `PASS__SF3_STRICT_ADDITIVE_GEOMETRY_DELTA`。它没有删除或修改任何 SE3 既有 physical volume，只新增：

1. `SF3_W_NearField_FrontWindowPlate_2p9mm`
2. `SF3_W_NearField_SideSleeve_2p9mm`
3. `SF3_W_NearField_RearColdFingerAnnulus_2p9mm`

三者材料均为 W、nominal 厚度 `0.29 cm`、总质量 `1.89470774 kg`，都是 `InstrumentFrame` daughters 且全部 passive。SF3 `.det`、materials、intro 与 SE3 字节相同；setup 只做 identity/include 改名；删除唯一 SF3 插入块即可逐字节恢复 SE3。3 BGO + 3 plastic active veto 完全不变。37,194 条 focused rays 对新增 W 的 chord 全为零。

因此答案是确定的：**SE3 与 SF3 的物理几何差异仅为这三块近场被动 W；独立 transport seeds 带来的抽样涨落不是几何差异。**

### 2.4 SF3 完成结果与停止门

SF3 使用与 SE3 完全相同的 Plan-1 per-family/per-mode 目标，但 fresh、互不重复 seeds；比较同统计规模而非逐事件 paired histories。

| 指标 | SE3 | SF3 | SF3/SE3 |
|---|---:|---:|---:|
| day-15 prompt W2 | 0 events, `0 cps` | 3 events, `0.152255127 cps` | 分母为零，不定义 |
| day-15 delayed W2 | 47 events, `0.0601133621 cps` | 53 events, `0.0686044841 cps` | `1.14125182` |
| transported A15 | `1348.141992 Bq` | `1360.938957 Bq` | `1.00949` |
| signal selected | 21657/37194 | 21785/37194 | — |
| Aeff | `11.69478 cm²` | `11.76390 cm²` | `1.00591033` |
| S20 | `1279.288658` | `1286.832682` | `1.00589705` |
| B20 | `98257.66905` | `361685.5527` | `3.68099057` |
| Z20 | `4.08117597` | `2.13971781` | `0.52428952` |
| central F3 | `7.35082246e-5` | `1.40205404e-4` | `1.90734309` |
| componentwise proxy F3 | `4.48131034e-4` | `4.72534058e-4` | `1.05445511` |

唯一 full-stat gate 是 central `F3_SF3/F3_SE3 ≤ 0.75`；proxy 不控门。实际 `1.907343085 > 0.75`，所以结论固定为 `STOP__NO_FULLSTAT_TOPUP`：没有启动 full-stat prompt、buildup、inventory 或 delayed，SF3 不替代 SE3。

统计边界：SF3 prompt 只有 3 条、delayed 只有 53 条；SE3/SF3 又使用独立 seeds，所以幅度包含明显 MC 波动。不能把 `1.907×` 当成精确材料效应系数；但下面的逐历史 pair 顶点是直接机制证据。

### 2.5 为什么三块 passive W 没有优化：已确认路线机制

SF3 的 3 条 prompt W2 survivors 全部来自 incident gamma，父能量约为 `4.289、13.628、21.734 MeV`，六个 active veto 体积中的能量沉积均为零：

- 2 条的 first pair vertex 直接位于新增 `SideSleeve` W，随后近场湮没，511-keV daughter 到达 TES；
- 第 3 条的 pair vertex 在新增 W 外，但其 511-keV daughter 后续在 front W Rayleigh scattering 后到达 TES。

严格结论只能写成“2/3 的 pair 顶点在新增 W 中；第 3 条是 W 参与后续路径”，不能把三条都说成 W 内 pair。机制是：罕见高能中性 gamma 可以穿过 BGO/plastic/BPE 而在主动体积中恰好零沉积，然后在 active-veto 内侧的被动高 Z W 中转换；W 离 TES 很近，却不能发 veto，于是生成局部 511 背景。Focused 511-ray bank 没碰 W 与此完全不矛盾，因为它测试的是单一 science-ray corridor，不是全空间、多 MeV atmospheric gamma。

旧 Stage01/04 passive-W 表中的 W deposit/pair 为 0 是通用 parser 的 telemetry/volume-mapping 限制，不能推翻路线诊断。后来的 targeted route diagnostic 用 IA 坐标与精确 W geometry membership 定位 pair 顶点。**Stage04/06 仍负责 rate；route JSON 只负责机制/位置，不重新定率。**

Delayed 方面，53 条最终 selected delayed survivors 的 source positions 全在新增 W 外；完整 mixture 中有 7,174 个 W-source triggers，但本轮没有 selected W-sourced event。不能据此宣称 W 不会活化，也不能用低统计 `+14.1%` 稳健归因材料效应。

### 2.6 当前优先候选与 promotion gates

SE3 residual selected delayed rate 中 Cu-61/Cu-62/Cu-64 合计约占 `92.9946%`。当前优先方向：

1. **V2A**：50 mK Cu can 底盖改环形盖/径向热桥；L0 Cu 实心盘改 open-ring/spoke；热带移出 TES 直视固角。目标覆盖约 `38.985%` 当前 delayed central。
2. **V2B**：在 V2A 上重排 MXC 开孔，并错开多冷板投影直通道；累计目标覆盖约 `64.1%`。
3. **V2C 只作筛选**：V2A/B 不足时，在不侵入 `37.96 mm` optical corridor 的非-FoV 固角测试 segmented shadow cup/graded liner。任何新增材料仍须走 fresh corrected chain。

下一候选 promotion gates：

- delayed W2 `<0.042 cps`，且不确定性区间支持改善；
- Cu-61/62/64 A15 相对 SE3 至少降低 30%；
- prompt W2 upper 不劣于 SE3/current S3d control；
- matched full-envelope Aeff 首轮损失 `≤2%`，绝对门 `≤5%`；
- thermal、magnetic、structural、mass、overlap/navigation 全部 PASS。

### 2.7 动态更新格式

每新增候选，只在本节追加一个 dated ledger entry，并至少记录：

```text
candidate / parent geometry / exact geometry delta
static geometry + overlap + navigation + signal-clearance authority
high-energy boundary/pair scorer authority（若新增近场高 Z）
corrected source/profile and fresh seed registry
instant + buildup statistics
candidate-own inventory and actual-position delayed authority
common response/veto/Step05 identity
37194-ray signal result
day15 diagnostics and 81-node mission S20/B20/Z20/F3
central/proxy uncertainty boundary
promotion gate decision and next baseline
```

在有新候选完整闭环之前，当前一句话状态必须保持：**SE3 是冻结比较基线但不是最终最优；SF3 是失败的近场 passive-W 负面样本；下一轮优先处理近场 Cu 与冷板投影视线。**

---

## 3. 新 session 的最小复习协议

新 session 首先只做以下动作：

1. 完整阅读本文件并目视第 1 节流程图；
2. 用 5–8 句话复述三流、共同响应/veto、81-node mission 和当前 SE3/SF3 状态；
3. 明确说出图中 mono-511 支路当前禁用、passive W 不属于 veto、SF3 已停止且没有 full-stat；
4. 在用户指定下一项工作前，不启动 transport、不改几何、不递归重读全部历史、不扫描/哈希大型 SIM；
5. 只有出现具体数字争议或需要实施新候选时，按第 4 节打开对应小型 authority。

推荐给新 session 的唯一首条提示：

> 请完整阅读并目视 `engineering/geometry_optimization_20260815/50_geometry_project_master_handoff_20260816/P0_GEOMETRY_PROJECT_MASTER_HANDOFF_20260816.md`。先只做项目复习：用 5–8 句话复述 corrected prompt→candidate-own activation/inventory→actual-position delayed、独立 37,194-ray signal、共同 response/veto/Step05、81-node/20-day F3，以及当前 SE3/SF3 动态结论。明确 mono-511 禁用、SF3 不补 full-stat、尚无最终最优几何。不要启动 transport，不要扫描或哈希大型 SIM，等待下一条任务。

---

## 4. 最小 provenance 索引：只在需要时打开

以下路径均相对 repo root；外部冻结 worktree 路径按绝对路径给出。

### 4.1 永久方法与 source authority

- `engineering/particle_source_unit_repair_20260811/README.md`
- `engineering/particle_source_unit_repair_20260811/data/source_contract_manifest.json`
- `engineering/particle_source_unit_repair_20260811/data/static_validation.json`
- `engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/README.md`
- `engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/NEXT_SESSION_REVIEW_OUTLINE.md`
- `core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.tex` 的 `Simulation workflow`
- 本包 `assets/fig_simulation_workflow_corrected_zh_20260810.{png,tex}`

### 4.2 SE3 完成 authority

- `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/geometry_optimization_20260815/47_se3_plan1_transport_20260815/outputs/07_final_audit/FINAL_REPORT.md`
- `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/geometry_optimization_20260815/47_se3_plan1_transport_20260815/outputs/06_mission/summary.json`
- `/home/ubuntu/.codex/worktrees/626c/TES_511_Balloon/engineering/geometry_optimization_20260815/44_geoopt_se3_minimal_20260815/audit/se3_geometry_validation.json`

### 4.3 SF3 完成与机制 authority

- `engineering/geometry_optimization_20260815/49_sf3_plan1_transport_20260816/outputs/07_final_audit/FINAL_REPORT.md`
- `engineering/geometry_optimization_20260815/49_sf3_plan1_transport_20260816/outputs/06_mission/summary.json`
- `engineering/geometry_optimization_20260815/49_sf3_plan1_transport_20260816/outputs/05_se3_vs_sf3_matched_comparison/summary.json`
- `engineering/geometry_optimization_20260815/49_sf3_plan1_transport_20260816/diagnostics/sf3_background_routes_2d/sf3_background_routes_2d.json`
- `engineering/geometry_optimization_20260815/49_sf3_plan1_transport_20260816/diagnostics/sf3_background_routes_2d/sf3_background_routes_axial_radius.png`
- `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/geometry_optimization_20260815/48_geoopt_sf3_windowed_w_nearfield_20260816/audit/sf3_geometry_validation.json`

### 4.4 下一轮动态优化

- `engineering/geometry_optimization_20260815/48_se3_background_optimization_review_20260816/SE3_BACKGROUND_OPTIMIZATION_REVIEW_20260816.html`
- `engineering/geometry_optimization_20260815/48_se3_background_optimization_review_20260816/data/analysis_summary.json`
- `engineering/geometry_optimization_20260815/48_se3_background_optimization_review_20260816/data/report_candidate_actions.csv`
- `engineering/geometry_optimization_20260815/48_se3_background_optimization_review_20260816/data/report_promotion_gates.csv`

---

## 5. 本文件的维护边界

- 第 1 节“绝对保留”是方法主线，不随候选几何改写。
- 第 2 节是动态 ledger；新候选完成后可更新当前状态，并追加 dated authority。
- 底层报告、receipts、source manifests、几何 audit 和历史结论永不覆盖。
- 更新本文件时先复核命名小型 authority；不要为了更新摘要触碰大型 SIM。
- 若未来方法主线确需改变，必须新建更高日期版本并在首页列出相对本文件的 P0 变更，不能静默编辑物理合同。

---

## 6. 2026-08-16 追加：为什么建立 SG3B，以及候选自有模拟计划

### 6.1 SG3B 的角色与建立理由

`SG3B` 冻结为当前 SG3 系列的**工程几何输入候选**，但在完成候选自有物理闭环前，不得称为最终物理最优或已晋级几何。其逻辑起点是 SF3 的负面机制证据：SF3 在 active-veto 内侧加入 `1.894708 kg` passive W 后，三条最终 prompt W2 survivors 中有两条的 first pair vertex 位于新增 W，第三条也有 W 中 Rayleigh 路径；这些近场高能中性事件在 3 BGO + 3 plastic 中恰好零沉积，因此 W 本身不能替事件提供 veto。与此同时，SE3 residual delayed W2 又主要受近场 Cu-61/62/64 支配，所以后续设计不能继续简单堆叠近场高 Z，而应同时减少近场 Cu 活化质量/直视固角，并把必要的 511-keV 被动遮挡限制在 MXC→TES 的有效阴影区。

SG3→SG3A→SG3B 采用了受控的小步修改：L0 TES 接触的 Cu 实心盘改为方形开口热沉环，保留至少 `1.00 cm` 的 TES 衬底投影接触宽度、至少 `1.00 cm` 的外伸宽度及四条既有偏轴 Cu cold-finger 链；四片 2 mm 50 mK Still-like Cu can 保持形状和位置不变，仅由 Cu 改为 Al，质量由 `2.900728 kg` 降至 `0.873779 kg`；五段 homogeneous NbTi harness proxy 保持形状和位置不变，仅改为 Al proxy，质量由 `567.698 g` 降至 `235.726 g`。NbTi→Al 是对现有过重、均匀化代理的 activation/material ablation，不等于已经证明真实飞行线束可以全部使用铝；真实线束的导电、超导、热漏、机械和磁学合同仍须另行闭合。

SG3B 删除 SF3 的三块 W，也不保留 SG3A 的平面 Bi 伞，而采用嵌套在既有 x′ 轴 2 mm Al 近场圆筒内的 passive Bi 上半圆筒：径向厚度 `4.796 mm`，质量 `410.304 g`，下半圆筒删除，在 L0 Cu 热沉环处留轴向间隙，且**不加前/后半端盖**。该形状把保留的 MXC-origin→TES-pixel 直线几何覆盖从平面伞的 `21.84%` 提高到 `87.33%`，同时 37,194 条 focused rays 对 Bi 的交点为零，最小径向余量为 `1.841 cm`。实心半端盖会截断约一半 focused rays；带孔前盖只能带来约十个百分点的 proxy 覆盖和很小的条件 F3 改善，却增加约 `88 g` 近场 Bi，后盖收益近乎为零，因此冻结版不加端盖。

SG3B 的确定性反向重建和 10,000-sample/placement Geant4 overlap 构造审计均为 PASS。静态条件估计的 central F3 为 `5.2172e-5 ph cm^-2 s^-1`，工程范围约 `5.09e-5`–`5.51e-5`；这个估计假设 signal 不变且没有新增 accepted prompt，尚未计入 `410.304 g` 近场 passive Bi 的 pair-production 代价或新 Al inventory，因此只用于决定值得开候选自有 Plan-1，不构成性能 authority。Bi 仍是高 Z 被动物质，永远不属于 active-veto whitelist。

当前 SG3B 生成型 authority 位于：

- `/home/ubuntu/.codex/worktrees/4f50/TES_511_Balloon/engineering/geometry_optimization_20260815/55_geoopt_sg3b_bi_halfcylinder_al_harness_20260816/geometry/DEMO2_DR_v3p5_SG3B.geo.setup`
- 同包 `audit/sg3b_geometry_validation.json`、`audit/sg3b_overlap_validation.json`
- 同包 `data/sg3b_mass_delta.json`、`data/sg3b_static_and_f3_estimate.json`

### 6.2 SG3B Plan-1：与 SF3 同统计、同方法的候选自有闭环

新建非覆盖包 `engineering/geometry_optimization_20260815/56_sg3b_plan1_transport_20260816/`，以 `49_sf3_plan1_transport_20260816/` 的代码和配置为模板；不得修改 SF3 包，不得把 SF3 的 source cards、seeds、receipts、RP、inventory、delayed sources、SIM 或 selected catalogs 当作 SG3B 数据。启动前先把冻结 SG3B geometry authority 固定到新包/manifest，要求 source card、setup、SIM header 与 candidate identity 全部为 SG3B。

SG3B Plan-1 完全继承 SF3 的约三分之一统计合同：

- 21 个 background jobs：8 族 corrected-keV INSTANT 合计 `1,280,693` histories；8 族 BUILDUP 合计 `1,015,492` histories；各 family/mode target 与 SF3 `ceil(S3d/3)` 合同逐格相同；
- 由 SG3B BUILDUP 的 RP/TT 独立重建 NUBASE state-aware day-15 inventory 和 actual-production-position delayed sources；登记 8 个 family cells，每个 `83,334` triggers，只有 `A15>0` 的 family 执行，零活度 family 以 `SKIP_ZERO_A15` fail-closed 记录；
- 独立重放冻结的 37,194-ray focused EventList，公共注入面仍为 `xprime=-30.0001 cm`，输入光学面积仍为 `20.08476 cm²`，使用 fresh SG3B seed；
- 30-row job plan 和 seed registry 全部使用新的 `sg3b_*` identity 与全局未注册 fresh seeds；不允许 paired-seed exception，也不允许复用 SF3 seeds；
- gamma profile 保持 `unit_only_total_gamma`，`additive_mono511=false`；任何 card/header 出现 `cosima_spectra_dp_2602units` 立即失败。

输出阶段沿用 SF3 的 00–07 结构：

1. `00_input_audit`：锁定 SG3B geometry/setup、corrected source、30-row plan、fresh seed registry、磁盘/内存预算和候选身份；
2. `01_prompt`：建立 response-neutral prompt catalog 和 per-family TT 归一化；同时对 `Eγ>1.022 MeV` 记录进入近场 Bi 边界、Bi 内 pair vertex、511 daughters 到 TES 的逐历史路线；
3. `02_activation`：由 SG3B 自己的 BUILDUP 生成 RP/TT、state-aware inventory、day-15 A15 和 exact-position delayed source manifests；
4. `03_delayed`：输运 SG3B 自己的 delayed sources，生成 response-neutral raw catalog；
5. `04_common_response`：prompt、delayed、signal 共同使用 measured response `FWHM=0.42 keV`、pixel threshold `0.3 keV`、`W2=[510.58,511.42] keV`、3 BGO 阈值 `50/70/80 keV`、3 plastic 阈值 `50 keV` 及 retained Step05 `side_keep_from_hits/reject_policy=keep`；Bi、Al can、Al harness proxy 和所有 Cu 均保持 passive，不得加入 veto；
6. `05_se3_vs_sg3b_matched_comparison`：只读取冻结 SE3 小表作 denominator，不重跑 SE3，不用 SF3 full-stat 补样，并附 family/parent/isotope/material/volume lineage；
7. `06_mission`：使用同一 81-node/20-day analytic fold，计算 S20、B20、Z20、F3 和 componentwise proxy；
8. `07_final_audit`：闭合 geometry/source/header/seed/receipt/TT/RP/inventory/position/response/veto/mission 全链并给出唯一 gate 决策。

Plan-1 的 sole full-stat top-up gate 与 SF3 保持一致：

\[
R_{F3}=F3_{\rm SG3B}/F3_{\rm frozen\ SE3}\le 0.75,
\]

即 central `F3_SG3B <= 5.5131168474e-5 ph cm^-2 s^-1`。proxy 只报告、不控门；若失败，立即 `STOP__NO_FULLSTAT_TOPUP`。若通过，才允许复用 SF3 的 full-stat top-up 框架，把 INSTANT/BUILDUP 补到冻结 full target，并**重新**建立完整 SG3B inventory；每个正活度 delayed family 使用 fresh `250,000` triggers。即使通过 Plan-1 gate，也仍需满足第 2.6 节的 delayed、Cu inventory、prompt upper、Aeff、thermal/magnetic/structural/mass/navigation gates，才能讨论晋级。

资源层不照搬 SF3 曾触发 systemd-oomd 的 6-worker 起点。复用其 pressure guard、whole-job retry、write-once receipt 和磁盘 reserve 逻辑，但默认以 4 个并发 workers 开始；中断的 partial attempt 不进入统计，重试必须从 event zero 使用该 job 已登记的 seed。该资源调整不改变任何物理统计合同。

### 6.3 SF3 代码复用与必须替换的参数

应复制代码到新 SG3B 包后修改，不能对 `49_sf3_plan1_transport_20260816/` 原地 search/replace：

| SF3 模板 | SG3B 修改 |
|---|---|
| `analysis_inputs.json` | `candidate/profile_id/package_root/run_root/outputs` 改为 SG3B；`sf3_setup` 改为冻结 SG3B setup；加入 SG3B geometry/overlap audit；passive-W 表改为 passive-Bi/Al 诊断表；其余 response/mission/source 常量不变。 |
| `sf3_plan1_common.py` | 复制为 `sg3b_plan1_common.py`；修改 package roots、candidate identity、job/status 前缀和体积映射，去掉三块 SF3 W 的硬编码断言。 |
| `build_sf3_sources.py` | 复制为 `build_sg3b_sources.py`；只更换 geometry/setup、`sg3b_*` job/card/output identity 和 fresh seeds；八族谱、FarField、corrected-keV 与 no-mono 合同不变。 |
| `run_sf3_plan1.py`、`run_sf3_plan1_followup.py`、`validate_sf3_receipts.py` | 改 SG3B run root、receipt schema/status、controller/guard 标签；统计目标不变，默认并发改为 4。 |
| `build_sf3_activation.py` | 改为 SG3B geometry/volume/material provenance；所有 RP/TT、inventory、position mixture 与 delayed cards 必须新建，不能继承 SF3。 |
| `prepare_full_envelope_signal.py` | 改 SG3B setup、job ID、backprojected EventList 输出和 static audit identity；冻结 37,194-ray 输入、注入面与面积不变。 |
| `run_prompt_analysis.py`、`analyze_delayed_stage.py` | 保持归一化和 response-neutral catalog 算法；更换候选名称、SG3B material/volume lineage，并加入 Bi pair/boundary route scorer。 |
| `build_common_response.py` | 响应、W2、3 BGO + 3 plastic whitelist 和 Step05 参数不变；删除 SF3 W volume 假设，明确所有 SG3B Bi/Al/Cu 为 passive。 |
| `build_matched_comparison.py`、`build_mission_stage.py` | 比较标签改为 frozen SE3 vs SG3B；81-node/20-day 数值合同不变。 |
| `finalize_sf3_plan1.py` | 复制为 `finalize_sg3b_plan1.py`；改 30-row identity、stage status、SG3B audits、Bi scorer closure 和 gate 名称；不得保留“SF3 三块 W 必须存在”等候选专属断言。 |
| `build_sf3_background_routes_2d.py` | 改为 SG3B prompt/activation/delayed 的 Bi/Al/Cu 路线图；SF3 历史轨迹只能作为对照，不得冒充 SG3B 事件。 |
| `*_fullstat_*` | 只预置为 gate 后模板；Plan-1 final audit 未 PASS 且 central gate 未通过前不得执行。 |

代码迁移完成后的第一项工作是静态 preflight 和生成 30-row plan/source manifests；只有 geometry identity、corrected source、fresh seeds、passive/active volume mapping、37,194-ray bank 和资源 reserve 全部 PASS 后，才可由用户另行授权启动 transport。本次追加只定义计划，没有启动任何 SG3B transport，也没有扫描或哈希大型 SIM。

### 6.4 统一 Cosima 执行入口（2026-08-16 用户批准）

后续项目 Cosima transport 的进程执行统一使用：

- `/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute/run.py`
- 同目录 `common.py`、`progress.py` 和 `HANDOFF.md`

不得再为 prompt、activation、delayed 或 signal 复制新的多进程 runner 或进度监视器。各物理阶段仍可保留自己的 source/job-plan builder，但必须生成与统一 executor 兼容的 `job_plan.json`、seed registry、source manifest 和 preflight，再把 Cosima 启动、production canary、并发、资源门、whole-job retry、attempt 隔离、write-once receipt 和终端进度交给上述代码。这个决定只统一执行机制，不改变 candidate-own activation/inventory、actual-position delayed、独立 focused signal、共同 response/veto/Step05 和 81-node/20-day mission fold 的物理合同。

统一 executor 的恢复判定必须把 PASS receipt 绑定到当前 profile/candidate/job/mode/family/events/seed/source/setup、SIM-header 几何与 seed 证据以及仍存在的 attempt artifacts；旧候选 receipt、身份漂移或已删除的产物一律 fail-closed。启动前必须轻量互锁 job plan、seed registry、source manifest 和 preflight，并核对统计总量、seed 唯一性、输出目录及 corrected-keV/no-mono 合同；不以大型 SIM 全扫描或 digest 作为执行 gate。资源准入除磁盘、MemAvailable 和 SwapFree 外，还必须计入 per-worker reservation、aggregate worker RSS 和 memory full-PSI；默认/最大并发保持 4，不得提高。

当前 `prepare.py`/`config.json` 只实现 21 个 SG3B Plan-1 corrected-keV INSTANT/BUILDUP background jobs；后续 delayed/signal builder 尚未因此自动完成。首个 SG3B production canary 已首尝试 PASS：`267,312/267,312` events、return code 0、DAT TT/EN 闭合、SIM header 的 SG3B setup/seed 一致，且只做 header-only 检查；随后已实跑 4-worker 扇出。该 canary 单进程峰值 RSS 约 `3.62 GB`，因此 4 workers 是上限而非可继续放大的目标。正在运行的 controller 启动于本次代码加固之前，继续使用其已加载的旧进程镜像；本次文件修改不改变或中断当前 transport，后续 restart/new profile 才使用加固后的统一 executor。
