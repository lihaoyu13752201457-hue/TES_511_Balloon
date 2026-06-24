---
title: TES_511_BALLOON delayed-source v2 修改需求与论文贡献说明
project: TES_511_BALLOON
status: implementation-rationale-v2
scope_date: 2026-06-24
language: zh-CN
predecessor: TES_511_background_validation_necessity_and_paper_impact.md
---

# 1. 文档目的

上一阶段已经完成 prompt source 归一化、far-field 面积/radius、`eplus` survivor、delayed 统计和 CsI–BGO 受控比较。新的问题不再是“prompt 会不会整体多乘了一个面积”，而是：

> 当前 delayed source 是否完整保留了原始 activation inventory 中的 production tag、原始逻辑体、核素和 excitation state，以及这些状态是否以正确的物理曝光和空间分布进入 detector-level transport。

本文档给出新的修改需求，解释每项修改为什么必要、会如何改变或验证当前结果，以及它对 NIM A 论文的具体贡献。

本阶段不以“把 delayed 调高”为目标。delayed 修复后可能升高、降低或基本不变；工程成功的标准是建立可复核的 source authority。

# 2. 当前可以保留的结论

## 2.1 Prompt 归一化的数量级已经闭合

当前 prompt audit 已确认：

- 8 个粒子族、160 个 equal-\(\mu\) source bins；
- far-field radius 为 60 cm；
- 面积为 \(\pi R^2=11309.7336\;\mathrm{cm^2}\)；
- source-card flux 与 manifest 闭合；
- gamma splits 和 non-gamma replicas 的 selected-rate 权重可独立重建；
- Step05 prompt rate 与逐事例权重和一致。

因此，当前 prompt 高值没有显示出整体 \(4\pi R^2\)、\(\pi R^2\) 或 replica 因子级错误。

按当前源强：

\[
R_{\mathrm{prompt,source}}\simeq6.46\times10^4\;\mathrm{s^{-1}},
\]

而 legacy day-15 delayed source 为：

\[
A_{\mathrm{delayed}}=85.45\;\mathrm{Bq}.
\]

源层面的 prompt/delayed 事例率比约为 756。内部 delayed decay 单次更容易在 TES 中留下能量，并不意味着其总 selected rate 必须高于 prompt。

## 2.2 W2 prompt dominance 在数量级上可能成立

当前 atmospheric positron source-plane rate 约为：

\[
R_{e^+}\simeq1.32\times10^3\;\mathrm{s^{-1}}.
\]

47 个 W2 prompt `eplus` survivor 对应的选择效率约为 \(2.4\times10^{-5}\)，而 legacy delayed 的 30/\(10^6\) 选择效率约为 \(3.0\times10^{-5}\)。两者 detector coupling 相近，主要差异来自源率。因此 W2 中 prompt 大于 delayed 并非自动意味着归一化错误。

## 2.3 “delayed 在全能谱都很小”不成立

当前能段审计显示，final delayed fraction 在 1500–3000 keV 已达到约 48.9%。因此只能说：

> delayed 在当前 510.58–511.42 keV 窄窗中较小；不能推广为 activation background 在整个 MeV 能区可忽略。

该结论应保留，无论 delayed-source v2 最终如何变化。

# 3. 最新代码审计发现的问题

## 3.1 Legacy inventory 不是从 raw `.dat` 直接闭合到最终 source

当前 exact-position builder 先读取一个已经由旧 radial-profile builder 生成并经 ground-state fixer 修正的 source，再从其中提取 `(volume, ZA)` activity。旧 radial builder 会在以下情况下跳过条目：

- RPIP 点少于 `min_points=15`；
- half-life 未解析；
- profile 未成功生成；
- source entry 未写出。

这些条目一旦未进入旧 source，后续 ground-state fixer 和 exact-position builder 无法恢复。

当前 manifest 显示 RPIP keys 约 1497，而 legacy activity keys 约 233。该差异可能包含稳定核素、极短寿命核素和低活度核素，但目前没有完整 omission ledger 证明所有差异均合理。

**风险：**85.45 Bq 证明的是“已写入 legacy source 的活度闭合”，不是“raw activation inventory 的完整闭合”。

## 3.2 Excitation state 在 legacy exact-position chain 中丢失

RPIP 记录包含 `exc_keV`，但当前 exact-position builder：

- activity key 只使用 `(VN, ZA)`；
- position weight key 只使用 `(VN, ZA)`；
- source block 只写 `.ParticleType ZA`；
- source name 不包含 excitation state。

旧 radial builder 虽然按 `(VN, ZA, exc)` 构造 profile，但实际执行的 source writer 同样只使用 ZA，并且 source name 不含 excitation state。相同 `VN/ZA/z-bin` 的不同 state 可能产生重复 source names，被 parser 或 Python dictionary 覆盖。

**风险：**metastable state、isomeric transition、级联 coincidence 和 state-specific half-life 可能被折叠或丢失。

## 3.3 Production tag 在 activity-to-position 映射中丢失

raw `.dat` activity 由不同 incident families 产生。当前 exact-position builder 先把 activity 合并到 `(VN,ZA)`，再把不同 tag 的 RPIP points 混合。它不再知道该 activity 是由 neutron、gamma、proton 或 muon 产生的。

对 gamma splits 和 non-gamma replicas，当前代码依赖 `1/division` point weights。该做法在各 tag 内部可用于平均，但直接跨 tag 混合时没有显式除以各 tag 总物理曝光，可能改变同一 nuclide/volume 的空间混合比例。

**风险：**总 Bq 可以保持闭合，但 activity 可能被分配到错误的坐标区域；对靠近 TES 的小活度分量，selected rate 可能发生因子级变化。

## 3.4 Canonical volume 被用于物理匹配

现有代码将多个 raw logical volumes 合并为 `Window`、`Copper`、`TES_Lx` 等 canonical names。该做法适合绘图，但不适合 activity-to-position authority。

如果两个不同 raw volumes 被合并：

- 每个 volume 的 production rate 被聚合；
- 所有位置被放入同一 pool；
- activity 可在两个真实部件间重新分配。

**风险：**位置仍是真实坐标，但每个真实部件应承担的 activity fraction 不再保持。

## 3.5 Source-name collision 没有成为 hard gate

旧 source name 不包含 excitation state 和 production tag。当前 manifest 主要检查总 flux 和 sample count，没有对 registered/defined/unique source names 做全局一一对应审计。

**风险：**文本总 flux 看似正确，但 Cosima 实际读取的 source definitions 可能少于写出的逻辑条目。

## 3.6 `DetectorTimeConstant=1e-9` 需要独立审计

当前 delayed source 使用 1 ns。Cosima manual 将该参数定义为 activation 模拟中“两个衰变或退激发被视为 coincidence 的时间”，并要求 activation 的三个步骤使用同一值。它不是 Step05 的 1 μs 普通事例 coincidence，也不是 CsI veto threshold。

过短的 time constant 可能把短寿命 metastable de-excitation 分到 prompt 和 delayed 两个无关事例中，产生错误的谱线或级联结构。

**风险：**主要影响 excited states、活化线和宽能谱；对 W2 的影响需通过有界 pilot 确定。

## 3.7 Parent–daughter feeding 尚未证明

当前 custom buildup 逐核素使用：

\[
A_k=P_k(1-e^{-\lambda_k t}),
\]

这是直接生成、相互独立的核素模型。代码中没有显式 Bateman coupling。Cosima native `Activator` 的 parent/daughter semantics 也尚未由当前项目证据证明。

**风险：**由长寿命母核在 15 d 照射期间不断产生的 radioactive daughter 可能被低估。影响大小取决于实际 produced nuclides，不能凭直觉设定。

# 4. 新的修改需求

# MR-01：建立 raw `.dat` 全状态 inventory authority

## 修改内容

新增独立 inventory builder，直接读取 full-stat `.dat`，不读取 legacy source activity。物理键为：

```text
(production_tag, raw_volume, ZA, excitation_state)
```

每个 tag 使用：

\[
P_{gk}=\frac{\sum_fN_{fgk}}{\sum_fTT_f}.
\]

这条公式同时处理 gamma splits 和 non-gamma replicas，无需 `gamma_div`/`non_gamma_div` 的隐式组合技巧。

输出所有状态的 production count、exposure、production rate、half-life、day-15 direct activity 和 classification。

## 必要性

它直接回答 85.45 Bq 是否为完整 inventory，并消除旧 radial source 对 final activity 的前置过滤。

## 对论文的帮助

Methods 可给出清晰、单位完整的 activation normalization；Supplement 可提供完整 omission ledger。Reviewer 不再需要相信一个经过多层 source post-processing 的总 Bq。

## Closure

- every raw RP row classified exactly once；
- total activity 可由 CSV 重建；
- no silent omission；
- legacy 85.45 Bq 只作为 comparison。

# MR-02：保留 excitation state

## 修改内容

- excitation token 使用 `Decimal` 或审计后的 state ID；
- activity、RPIP 和 source 均保留 state；
- ground/metastable 分别统计；
- 对 regular PointSource 的 excited-ion syntax 做最小 parser test；
- 不支持时采用 ground exact-position + metastable native/hybrid 两条独立流。

## 必要性

当前链明确丢失 state。该问题会影响 half-life、IT 级联和 delayed line spectrum。

## 对论文的帮助

可将方法升级为 **state-resolved production-position-sampled delayed source**，这比当前“记录坐标后抽样”更完整，也更符合 NIM A 对活化模拟可复现性的预期。

## Closure

- same ZA/different excitation 不碰撞；
- state substitution count = 0；
- source text round-trip 重建同一 state inventory。

# MR-03：使用 raw logical volume 作为物理 authority

## 修改内容

- 保留 `.dat` 与 RPIP 原始 VN；
- canonical names 只用于 figure/report；
- source activity 在 raw volume 内归一化；
- 输出 raw→canonical many-to-one map 及 legacy redistribution audit。

## 必要性

activation selected rate 对距 TES 的位置高度敏感。将多个窗口、Cu 部件或 TES subvolumes 合并，会在 source level 重新分配 activity。

## 对论文的帮助

能够证明 production-position sampling 真正保留了部件级空间结构，而不仅是保留一组坐标点。

## Closure

- v2 activity redistribution by canonicalization = 0；
- every source point 可回溯到 raw volume。

# MR-04：tag-aware exposure 和 position weighting

## 修改内容

对每个 `(tag, raw_volume, ZA, state)` 先计算 activity，再在相同 full key 的 RPIP 点内分配：

\[
A_{gkp}=A_{gk}\frac{u_{gkp}}{\sum_pu_{gkp}}.
\]

`u` 必须从与 `.dat` 相同的 exposure semantics 导出。禁止先丢弃 tag 再以 `1/file_count` 混合位置。

输出每个 key 的 `.dat` count、RPIP count、coverage 和 \(N_{eff}\)。

## 必要性

不同 incident families 在同一材料中产生核素的位置分布可能不同。总活度闭合不能替代 tag-aware spatial closure。

## 对论文的帮助

可明确说明延迟源同时保留 production-family、material、nuclide 和 coordinate correlations；这是论文最有价值的方法学贡献之一。

## Closure

- gamma split 和 non-gamma replica synthetic tests PASS；
- per-key point weights sum to per-key activity；
- tag fractions 可由 source manifest 重建。

# MR-05：取消 exact-position source 的 `min_points` 静默过滤

## 修改内容

- exact-position source 不以 15 points 作为存在条件；
- sparse keys 仍保留，但报告 point count、\(N_{eff}\) 和 sampling uncertainty；
- 正活度无 RPIP 的 key 必须使用 native volume-based fallback 或进入 BLOCKED；
- 所有 omission 有明确 reason 和 Bq。

## 必要性

稀有 positron-emitting nuclide 即使总 Bq 小，也可能因位置接近 TES 而贡献 W2。按 point count 删除不是物理选择。

## 对论文的帮助

Supplement 可给出“完整 inventory—空间支持”表，并避免 reviewer 发现 source 中存在未说明的统计阈值。

# MR-06：Source name 和 source semantics hard gate

## 修改内容

source name 包含 tag、raw-volume hash、ZA、state 和 sample index。写文件前检查：

```text
registered == defined == unique
duplicate_count == 0
```

对 source parser 做 round-trip test，并验证 excited ion 没有被替换为 ground state。

## 必要性

文本 flux sum 不足以证明 Cosima 实际加载了每个逻辑 source。

## 对论文的帮助

提升可复现性；该审计可放补充材料，不必在正文展示内部 source-name 细节。

# MR-07：与 Cosima native activation 交叉验证

## 修改内容

使用相同 isotope-production inputs 执行：

```text
ActivationBuildUp -> Activator -> ActivationSource
```

但必须正确处理：

- gamma splits 共同组成一次曝光；
- non-gamma replicas 是独立估计，不能相加为 8 倍照射。

比较 custom/native 的 total Bq、tag、raw volume、nuclide、state、ground/metastable fraction 和 major positron emitters。

Native delayed transport采用 volume-level distribution，用于衰变物理和空间近似的边界比较，而不是要求与 exact-position rate 完全相等。

## 必要性

这是对 custom builder 最有说服力的独立交叉验证。它还能暴露 half-life、state、decay chain 和 source semantics 的差异。

## 对论文的帮助

Methods/Discussion 可说明 custom position-resolved chain 与官方 volume-based activation workflow 的一致性或差异，使方法不再是单一自定义代码路径的自洽检查。

# MR-08：确定 `DetectorTimeConstant` authority

## 修改内容

先统计 1 ns–5 μs excited states 的 activity risk，再有界比较：

```text
1 ns legacy
1 us analysis-aligned
5 us manual/reference
```

三步 activation 使用同一值。最终值依据 event-building/decay-cascade 物理选择，不依据哪个值给出最低背景。

## 必要性

该参数决定短寿命核态被分到 prompt 还是 delayed。它直接影响 state-resolved source 的正确性。

## 对论文的帮助

可以在 Methods 中给出 activation-specific coincidence policy，并在 Supplement 报告 bounded timing sensitivity。

# MR-09：审计 parent–daughter feeding

## 修改内容

- 从 native Activator 源代码/受控 test 判断 feeding semantics；
- 列出 raw inventory 中可能产生 radioactive daughters 的 parent candidates；
- 只对影响 total activity、W2 或主要能段的链做 Bateman calculation；
- 未解析链进入 limitation ledger。

## 必要性

独立核素公式不等同于完整 decay network。是否影响当前结果必须用实际 inventory 判断。

## 对论文的帮助

避免不准确地声称“完整 activation buildup”；能够诚实区分 direct-production model 与 decay-chain-aware model。

# MR-10：重算 delayed selected rate 和受影响的 downstream

## 修改内容

v2 source 通过 inventory、RPIP、state、native 和 timing gates 后：

- pilot 比较 legacy/custom-v2/native；
- full-stat W2 目标 relative MC uncertainty ≤10% 或 selected events ≥300；
- 至少多个 position 和 transport seeds；
- 输出相同能段表和 isotope/state/raw-volume 分解；
- 若 W2 delayed 变化超过 2σ 或 10%，更新 Step05–Step08。

## 必要性

修 source 后，旧 30-event rate 即使统计收敛也不再是方法 authority。

## 对论文的帮助

最终 prompt/delayed 比例将同时具备 source completeness 和 detector-level MC uncertainty，而不是只有其中一项。

# MR-11：处理 BGO 结果的方法依赖

## 修改内容

检查已完成 BGO delayed chain 的 builder hash：

- 若使用 legacy delayed builder，v2 promotion 后只重跑 BGO activation/delayed；
- prompt、signal、geometry 不重跑；
- 若 BGO delayed 比较不进入论文，可将其标记 stale 并排除。

## 必要性

新 source 修复是材料无关的方法改变。只修 CsI 而保留旧 BGO delayed 会破坏材料比较的公平性。

## 对论文的帮助

确保 CsI–BGO 对比反映材料差异，而不是 source builder 版本差异。

# 5. 推荐实施优先级

## P0：必须先做，且不需要大规模运行

1. raw `.dat` inventory builder；
2. omission ledger；
3. state-ID audit；
4. raw-volume/tag-aware RPIP join；
5. duplicate source-name audit；
6. native activation semantics 和 source syntax test。

完成 P0 前不要增加 delayed transport 统计。

## P1：方法 promotion 所必需

7. custom source v2；
8. native inventory cross-check；
9. `DetectorTimeConstant` bounded audit；
10. parent–daughter feeding risk assessment；
11. pilot detector transport。

## P2：论文数字更新

12. full-stat delayed convergence；
13. affected Step05–Step08 rebuild；
14. BGO delayed dependency rebuild；
15. manuscript tables/figures and wording。

# 6. 对论文的核心贡献

## 6.1 从“source-card closure”提升到“raw inventory closure”

当前论文的方法亮点是从 production positions 抽样 delayed decays。v2 后可以进一步证明：

- 每个 raw activation state 被分类；
- 每个 activity 可追溯到生产粒子族和曝光；
- 每个 source point 可追溯到原始逻辑体和激发态；
- 没有 source-name、profile threshold 或 canonicalization 导致的静默丢失。

这将形成真正可发表的方法学贡献，而不仅是项目内部 source construction 技巧。

## 6.2 解释“高总活度、低 W2 rate”的物理原因

v2 可以把以下三个层级严格分开：

1. activation inventory；
2. decay transport 后的 TES spectrum；
3. veto/topology/W2 后的 selected rate。

这能够回答：

- CsI/I-128 是否只是主导总 Bq；
- Cu-64/Cu-62 是否仍主导 W2；
- metastable states 和 missing keys 是否改变这一结论；
- prompt dominance 是物理结果还是 source construction artifact。

## 6.3 提供 custom/native 双路径验证

NIM A reviewer 通常会追问自定义 activation chain 如何验证。native Activator/ActivationSource comparison 提供独立路径：

- inventory 一致性检验；
- state/volume 分解检验；
- exact-position 相对于 volume-average 的 detector-level影响。

即使两者不同，只要差异可解释，该结果本身也有方法学价值。

## 6.4 将 `DetectorTimeConstant` 纳入可复现方法

当前 manuscript 只写 1 μs Step05 coincidence，未区分 activation-specific coincidence。v2 可以明确：

- Step05 处理独立 event streams 的普通 coincidence；
- `DetectorTimeConstant` 处理同一核衰变/退激发级联的 prompt/delayed separation。

这会显著提高工程可信度。

## 6.5 提供材料比较的公平基础

如果 CsI/BGO delayed 都使用同一 v2 source method，材料差异才能归因于核素生成和衰变，而不是 builder 版本。该结果可作为补充材料或短小 design-sensitivity subsection。

# 7. 论文具体修改位置

## 7.1 Methods：Prompt/activation source model

需要新增或替换的内容：

- raw `.dat` inventory key；
- \(P=\sum N/\sum TT\)；
- state-resolved day-15 activity；
- direct-production 与 parent-feeding 的边界；
- raw-volume/tag-aware RPIP spatial weighting；
- missing-RPIP policy；
- native activation cross-check；
- activation `DetectorTimeConstant` 与 Step05 coincidence 的区别。

### 可用英文模板

> The activation inventory was reconstructed directly from the isotope-production files before any spatial-source compression. Production rates were evaluated separately for each incident-particle family, raw logical volume, nuclide, and excitation state using the summed physical exposure of the corresponding Monte Carlo files. Recorded production coordinates were then normalized within the same full state key, so that canonicalized material labels used for plotting did not redistribute activity between physical volumes.

> The custom production-position-sampled source was cross-checked against the native Cosima Activator/ActivationSource workflow at the inventory level. Ground and metastable states were retained separately. The activation-specific detector time constant was applied consistently in the buildup, activation, and delayed-decay steps and was treated separately from the detector-level coincidence and anticoincidence selection.

## 7.2 Results：Inventory closure

建议新增表：

| Quantity | Legacy | v2 custom | Native |
|---|---:|---:|---:|
| total day-15 activity |  |  |  |
| ground-state fraction |  |  |  |
| metastable fraction |  |  |  |
| represented RPIP activity |  |  |  |
| missing/fallback activity |  |  |  |
| source-name collisions |  | 0 | n/a |

建议报告：

- raw keys 总数；
- stable/unknown/missing-RPIP 分类；
- top nuclide/state/raw volume；
- native/custom difference。

## 7.3 Results：Selected background

建议合并成一张 compact table：

| Stream | W2 raw | W2 final | MC uncertainty | dominant source |
|---|---:|---:|---:|---|
| prompt | frozen authority | frozen authority |  | `eplus`, n |
| delayed v2 |  |  |  | isotope/state/raw volume |

另给一张 energy-band figure 或 table，明确 delayed fraction 随能量变化。

## 7.4 Discussion

建议核心逻辑：

1. prompt source normalization 已独立闭合；
2. prompt source-plane event rate远大于 total delayed decay rate；
3. delayed 的 W2 fraction 是能窗和位置相关结果；
4. v2 source audit排除了 state/volume/tag 丢失；
5. native comparison量化 volume-based approximation；
6. 当前结论仍受 mass model 和 detector response 限制。

### 可用英文模板

> The comparatively small delayed fraction in the final 511 keV window should not be interpreted as negligible activation. It results from the combination of the day-15 radionuclide inventory, decay branching, source location, shield self-veto, and the narrow analysis window. In the same simulation, delayed events become comparable to the prompt component in higher-energy bands.

> Reconstructing the inventory directly from the isotope-production records prevents profile-generation thresholds, volume canonicalization, or excitation-state merging from silently altering the delayed source. The remaining difference between the production-position-sampled and native volume-based calculations therefore quantifies a spatial-source approximation rather than an inventory-normalization ambiguity.

## 7.5 Abstract 和 Conclusion

只有在 v2 promotion 后更新数值。若 W2 delayed 变化很小，Abstract 只需增加：

> The delayed-source construction was validated against a state-resolved raw production inventory and the native Cosima activation workflow.

若 total background 或 sensitivity 变化超过当前误差，应更新所有 headline 数字，不保留旧值作主结果。

# 8. 结果判读矩阵

| v2 结果 | 解释 | 论文动作 |
|---|---|---|
| total Bq 和 W2 均接近 legacy | 当前低 delayed 获得更强验证 | 保留 headline，更新方法和 uncertainty |
| total Bq 上升但 W2 基本不变 | 旧链漏掉的 activity 与 W2 耦合弱 | 报告完整 inventory；解释窄窗选择性 |
| total Bq 接近但 W2 明显变化 | 主要是 state/volume/tag 空间重分配 | 更新本底和灵敏度；突出位置建模价值 |
| total Bq 和 W2 都明显上升 | legacy source 不完整 | 旧 delayed 数字全部 stale；重建 Step05–08 |
| native/custom inventory 不一致 | half-life、state、feeding 或 normalization 未闭合 | 不 promotion；解决差异后再跑 full-stat |
| native inventory一致、selected rate不同 | exact-position 与 volume-based spatial effect | 作为方法学结果报告 |
| DTC 改变宽谱但 W2稳定 | timing主要影响核级联谱 | 报 bounded systematic，不改变 W2结论 |
| DTC 显著改变 W2 | legacy prompt/delayed separation不可靠 | 选择新 timing authority并重建 |
| BGO delayed变化、prompt不变 | 材料活化结论需更新 | 只重跑 BGO delayed并更新比较 |

# 9. 最小投稿闭合标准

在不扩大为完整 flight prediction 的前提下，建议投稿前至少满足：

1. raw `.dat` inventory 全状态 closure；
2. `(tag, raw volume, ZA, state)` RPIP join 完整；
3. 无静默 `min_points` omission；
4. 无 source-name collision；
5. excited-state source semantics 有实测/源码证据；
6. native Activator inventory comparison 完成；
7. `DetectorTimeConstant` authority 唯一且三步一致；
8. parent-feeding semantics 已证明或明确限制；
9. v2 delayed W2 relative MC uncertainty约 10% 或更低；
10. 所有依赖旧 delayed builder 的论文/BGO数字已更新或明确排除；
11. prompt 和 delayed rates均报告 MC uncertainty，不使用虚假有效数字；
12. manuscript numbers全部来自唯一 promotion manifest。

# 10. 本轮不要求的工作

- 再做 prompt radius/area审计；
- 修改 atmospheric source；
- 调整 CsI/BGO geometry；
- 扫描 veto threshold；
- 完整 payload；
- 真实轨迹；
- 全 TES electronics response；
- 为所有核素实现无限扩展的 decay network；
- 为使 delayed 接近 prompt 而调参。

# 11. 最终建议

这次修改的最重要价值，不是可能把 delayed 从 6.6% 改成某个新百分比，而是把论文中的 activation 方法从：

> “一个总活度闭合、按记录坐标抽样的自定义 source”

提升为：

> **“一个从 raw production records 出发、state-resolved、tag-aware、raw-volume-preserving，并由 native activation 独立交叉验证的 detector-coupled delayed-background workflow。”**

如果 v2 后 delayed 仍然远小于 prompt，这个结果会比现在可信得多；如果 delayed 上升，论文也会因为主动发现并修复 source-construction bias 而更可靠。两种结果都对 NIM A 有价值。
