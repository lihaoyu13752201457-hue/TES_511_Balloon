---
title: TES_511_BALLOON 本底验证实施必要性与论文贡献说明
project: TES_511_BALLOON
status: implementation-rationale-v1
scope_date: 2026-06-23
language: zh-CN
---

# 1. 文档目的

本文档基于当前 NIM A 稿件、fix5 几何、prompt/activation 运行脚本、production-position-sampled delayed-source 构建代码，以及 Step05 的 W2 统计结果，回答三个问题：

1. 为什么仍需对 prompt 与 delayed 本底链进行有边界的工程验证；
2. 哪些实现最能提高论文可信度，而不把工作扩展成完整飞行任务预报；
3. CsI–BGO 对比与 prompt 源归一化审计应如何服务论文，而不是演变成无休止的仪器优化。

当前论文的合理定位是：**在当前探测器/低温系统代理质量模型中，对不可分辨 511 keV 窄线给出 detector-coupled、reference-exposure selected-rate estimate。** 本文档不要求完整吊舱、真实轨迹、最终电子学或完整飞行本底闭合。

# 2. 已确认的分析权威与边界

## 2.1 主动屏蔽 veto 的权威定义

本项目的定量 veto 由 Step05 后处理统一实现，而不是由 `.det` 中的在线触发阈值定义。当前权威选择为：

\[
E_{\rm shield}<50\;{\rm keV},\qquad \tau=1\;\mu{\rm s},
\]

其中 `shield_total_keV`（现有表中沿用字段名 `bgo_total_keV`）是候选事例时间组内所有主动屏蔽体积的沉积能量和。

因此，本轮工作：

- **不进行 CsI 40/60/90 keV 单元测试；**
- **不把 `.det` 中的 trigger/noise threshold 当作论文 rate authority；**
- **不调整 veto threshold 来优化结果；**
- CsI 与 BGO 比较必须使用完全相同的 Step05 后处理阈值、时间窗和拓扑选择。

## 2.2 当前不要求完成的内容

本轮明确不扩展到：

- 完整吊舱、光学梁、电子学和压力容器质量模型；
- 真实目标星历、任务占空比和斜程大气任务预报；
- 全套 TES 电子学响应；
- 大规模几何优化或 BGO 厚度优化；
- 弥散天空前景与最终 astrophysical likelihood；
- 通过改变阈值或切选“调出”更好灵敏度。

# 3. 当前证据基线

## 3.1 W2 最终本底组成

当前 W2 能窗为 510.58–511.42 keV。Step05 结果为：

| 流 | raw rate | final rate | final MC events |
|---|---:|---:|---:|
| Prompt | 0.118771 s⁻¹ | 0.0366410 s⁻¹ | 54 |
| Delayed | 0.00463537 s⁻¹ | 0.00257520 s⁻¹ | 30 |

Delayed 占比由 raw 阶段的 3.76% 上升到 final 阶段的 6.57%。这说明：

> 当前 delayed 偏低并不是因为主动 veto 或 FoV/拓扑选择对 delayed 进行了异常强的抑制；相反，最终选择对 prompt 的抑制更强。

因此，“delayed 低”首先是**源库存、衰变通道、材料位置和窄能窗耦合**的问题，而不是切选逻辑直接造成的问题。

## 3.2 Prompt 的异常集中性

最终 prompt W2 中：

| prompt tag | final events | final rate | prompt fraction |
|---|---:|---:|---:|
| `eplus` | 47 | 0.0318897 s⁻¹ | 87.0% |
| `n` | 7 | 0.00475128 s⁻¹ | 13.0% |

47 个 `eplus` survivor 的主动屏蔽能量均为零，其中 33 个为单像素，14 个为可保留多像素事例。这表明 `eplus` 是初级源类别标签，最终 TES 事例很可能由该初级流产生的 511 keV 光子或近孔径次级过程形成，而不能简单解释成“正电子直接穿过屏蔽进入 TES”。

这也是当前最需要追踪的 prompt 物理机制。

## 3.3 Delayed 的库存与最终 W2 贡献并不对应

当前 fixed delayed source 总活度约为 85.449 Bq，其中：

- I-128：65.533 Bq，约 76.7%；
- Cu-64：4.669 Bq，约 5.46%；
- Cu-62：0.0977 Bq，约 0.11%。

但最终 30 个 W2 delayed 事例全部来自：

- Cu-64：24 个，80%；
- Cu-62：6 个，20%。

并集中在焦平面附近的 Cu 冷板、支撑盘和低温容器结构。由此可见：

> 总活度由 CsI/I-128 主导，并不意味着最终窄 511 keV 选后率也由 CsI/I-128 主导。源活度和 selected rate 必须分别报告。

在 1500–3000 keV 能带，delayed 最终占比达到约 48.9%，进一步证明不能把 W2 的 6.57%推广为“活化本底普遍可忽略”。

## 3.4 当前源归一化链中的关键审计点

当前 `.geo.setup` 使用 `SurroundingSphere 60 ... 60`。对于半径 60 cm 的 far-field 圆盘约定：

\[
A_{\rm ff}=\pi R^2=1.13097\times10^4\;{\rm cm^2}.
\]

运行脚本中的核心关系为：

\[
A_{\rm ff}=\pi R^2,
\qquad
T_\gamma=\frac{N_\gamma}{F_\gamma A_{\rm ff}},
\]

并按 gamma flux 设定其他粒子生成数，再对非 gamma replicas 去权重。以当前积分通量为例，若确实采用 60 cm：

- gamma 源面物理率约为 \(4.79966\times\pi60^2\approx5.43\times10^4\;{\rm s^{-1}}\)；
- \(10^7\) 个 gamma 对应约 184.2 s 物理曝光；
- positron 源面物理率约为 \(0.116981\times\pi60^2\approx1.32\times10^3\;{\rm s^{-1}}\)。

按 8 个 positron replicas 和当前生成数，47 个 survivor 可重建约 0.0319 s⁻¹，与 Step05 结果相符。这说明现有结果没有显现一个明显的整体面积倍数错误。

但代码默认参数仍出现 `--farfield-radius-cm 35.0`，而 fix5 setup 为 60 cm。实际结果可能由命令行或 manifest 覆盖为 60 cm；在缺少最终运行 manifest 的情况下，**不能靠猜测闭合这一点**。这正是 source-normalization audit 的首要价值。

# 4. 必须实施的工作及其必要性

## 4.1 Prompt 源构建与归一化审计

### 实施内容

建立一个单位完整、可机器复核的审计链，逐项确认：

1. EXPACS/PARMA 输出到 20 个 equal-\(\mu\) 角分箱的积分过程；
2. 每个分箱和每个粒子族 source card 的通量单位；
3. Cosima far-field area source 对投影面积和角分布的约定；
4. `SurroundingSphere`、source-card radius、source manifest 和运行 CLI radius 的一致性；
5. \(\pi R^2\) 是否只使用一次，既不遗漏也不重复；
6. gamma splits、非 gamma replicas 和唯一随机种子的权重闭合；
7. Step05 selected rate 能否由逐事例权重 \(\sum_i w_i\) 独立重建；
8. MC 方差是否由 \(\sum_i w_i^2\) 给出。

### 必要性

Prompt 占最终 W2 的约 93%，其中 `eplus` 占 prompt 的约 87%。任何 source-area、立体角、projected-area 或 replica 权重错误都会直接改变论文 headline background 和灵敏度。

### 对论文的帮助

完成后可在 Methods 中给出清晰的单位链和解析闭合测试，并在补充材料中提供 source manifest。这样 reviewer 面对“为什么 prompt 如此高”时，论文能够区分：

- 归一化错误；
- 真实的侧孔/结构耦合；
- 有限 MC 统计涨落。

如果审计通过，prompt 高值将从“可疑数字”转化为“可解释且可复现的工程结果”。

## 4.2 Prompt `eplus` survivor 的物理来源追踪

### 实施内容

对最终 W2 `eplus` survivor 建立事件级 provenance：

- primary track 和能量/方向；
- positron 停止或 annihilation vertex；
- 511 keV photon 的 creator process、parent ID 和生成体积；
- 进入侧窗的位置和方向；
- TES 首次相互作用体积、像素多重度和能量沉积分配；
- 是否通过孔径、窗口、W/Cu/Al 附近生成或散射。

优先利用现有 SIM 的 CC/IA/track 信息；只有现有记录不足时才进行小规模 trace run。

### 必要性

当前 47 个 survivor 全部没有主动屏蔽沉积，且 82.5% 的 raw `eplus` W2 事例存活到 final。这种高度集中的结果需要明确物理路径，否则 reviewer 会怀疑源分类、粒子追踪或侧孔接受存在问题。

### 对论文的帮助

可将“prompt dominated”进一步写成具体物理结论，例如：

- aperture-coupled annihilation photons；
- nearby-material positron annihilation；
- direct charged-particle leakage；
- 或某一明确的 source/geometry 缺陷。

这会显著增强 Discussion 的工程可信度，并直接指向未来屏蔽或准直设计。

## 4.3 Delayed selected-rate 收敛与误差

### 实施内容

增加 delayed replay 统计，并分离两个方差来源：

1. 固定 production-position sample 下的 decay-transport seed 方差；
2. 不同 production-position sampling seed 下的空间抽样方差。

输出每个 run 的：

- 总活度；
- 生成衰变数；
- selected events；
- selected rate；
- `sum_w`、`sum_w2`；
- 同位素和体积分解；
- seed 间离散度。

### 必要性

当前 final delayed 只由 30 个事例支撑，简单泊松相对误差约 18%。该精度不足以支撑过多有效数字，也不足以判断 CsI 与 BGO 的 delayed 差异。

### 对论文的帮助

收敛后可以：

- 给出可信的 MC uncertainty；
- 证明 production-position sampling 对最终 selected rate 的稳定性；
- 将 Cu-64/Cu-62 主导结论从偶然的 30-event 现象提升为统计支持的结果；
- 使 activation 方法成为论文真正的技术贡献，而不是只展示 source-card closure。

## 4.4 CsI 与同几何 BGO 的受控对比

### 实施内容

构建一个**只改变主动屏蔽材料**的 BGO 派生版本：

- 保持所有 shield volume 的形状、位置、分段、开孔、mother、周围结构完全不变；
- 第一版保留现有 volume identifier，以避免同时改动 parser 和选择逻辑；
- 仅将允许清单中的 `.Material CsI` 改为 `BGO`；
- 使用相同 prompt source cards、同样的 gamma splits、replicas、seeds、far-field radius 和 Step05 后处理；
- 分别运行 prompt、activation buildup、fixed day-15 inventory、production-position delayed replay 和 focused signal；
- 同时比较 W2 与较宽能带，避免只看一个窄窗。

这是**same-envelope material substitution**，不是等质量比较，也不是 BGO 厚度优化。

### 必要性

当前总活度由 CsI/I-128 主导，而最终 W2 delayed 由 Cu 激活主导。BGO 比较能够回答两个不同问题：

1. 更换材料是否显著降低 shield activation inventory；
2. 即使 delayed 降低，prompt `eplus` 侧孔分量是否仍占主导。

如果 BGO 只降低总活度而不改变 W2，说明当前瓶颈是 aperture-coupled prompt；如果 BGO 同时改变 prompt veto survival，则说明材料的 stopping/secondary production 也重要。

### 对论文的帮助

在统计充分时，该结果可形成一个紧凑的 design-sensitivity subsection 或补充材料，展示论文不仅计算一个固定设计，也能解释材料选择的物理后果。即使 BGO 没有改善，负结果同样有价值：它能够说明 CsI/I-128 inventory 并非当前 W2 灵敏度的主要限制。

# 5. 建议的论文落点

## 5.1 Methods

建议增加：

- source-card 到 selected-rate 的单位链；
- far-field radius、圆盘面积和 replica 权重定义；
- `R_sel=\sum w_i` 与 `\sigma^2_{MC}=\sum w_i^2`；
- 主动屏蔽选择明确写为统一后处理定义；
- CsI/BGO 对比若完成，应明确为相同几何包络、仅材料替换。

## 5.2 Results

建议增加一张紧凑表：

| 项目 | Prompt | Delayed |
|---|---:|---:|
| final W2 rate | 含 MC uncertainty | 含 MC uncertainty |
| dominant family/isotope | `eplus`, `n` | Cu-64, Cu-62 |
| selected events | N | N |
| dominant volume/process | 事件追踪结果 | 近焦平面 Cu |

BGO 比较应报告 rate ratio 及其不确定度，而不是只报百分比变化。

## 5.3 Discussion

应明确区分：

- activation inventory；
- detector-coupled raw spectrum；
- final W2 selected rate。

建议核心表述为：

> The small delayed fraction in the final W2 sample is selection- and energy-window-specific. It is not caused by preferential rejection of delayed events and does not imply negligible activation outside the 511 keV analysis window.

若 prompt 审计通过，可进一步说明其主要物理路径。若 BGO 比较完成，可讨论材料替换对 inventory、selected delayed 和 prompt veto survival 的不同影响。

## 5.4 Supplement / reproducibility archive

适合放入补充材料的内容：

- source-card inventory 和单位审计；
- radius/area closure；
- 每粒子族权重与 `sum_w2`；
- delayed seed/M 收敛；
- BGO 几何 diff whitelist；
- 详细同位素、体积和能带分解；
- 运行命令、软件配置和 SHA256。

# 6. 结果判读矩阵

| 结果 | 科学解释 | 论文处理 |
|---|---|---|
| Prompt 归一化审计通过，`eplus` 路径可追踪 | Prompt 高值主要是当前孔径/几何的真实响应 | 强化 Results/Discussion；作为主要工程结论 |
| 审计发现 radius/area/solid-angle 错误 | 当前 headline rate 需重算 | 修复后重跑；旧结果标记 stale，不做物理解读 |
| Delayed 收敛后仍约 0.002–0.003 s⁻¹ | W2 delayed 确实较小，且由近焦平面 Cu 主导 | 可较有把握地保留约 6% 结论并给误差 |
| Delayed 收敛后明显上移 | 30-event 结果受统计或 sampling 影响 | 更新本底预算和灵敏度，不隐瞒变化 |
| BGO 显著降低 inventory，但 W2 基本不变 | I-128 不是 W2 主限制，prompt/aperture 更关键 | 作为很有价值的设计解释 |
| BGO 显著降低 W2 delayed | 屏蔽材料活化是可优化项 | 可加入 design-sensitivity 结果 |
| BGO 改变 prompt 更多于 delayed | stopping、secondary production 或 veto coupling 重要 | 需要按 process/tag 分解，不只谈 activation |
| BGO–CsI 差异小于 MC uncertainty | 当前统计不足或材料影响较小 | 报为 exploratory，不宣称优劣 |

# 7. 最小闭合标准

在不扩大论文范围的前提下，建议达到以下最小标准：

1. Prompt source radius、面积、角分箱、units、replica 和 event weights 全部机器闭合；
2. Step05 rate 可由逐事例权重独立重建，relative difference 不超过预设数值容差；
3. `eplus` survivor 至少能够按主要生成过程和生成体积分组；
4. Delayed final W2 的相对 MC uncertainty 降至约 10% 或更低，或明确报告未达到该目标；
5. CsI/BGO 对比只在几何 diff whitelist、相同源和相同后处理通过后解释；
6. 所有新数字带 provenance、run manifest、seed、geometry/source hash 和 uncertainty；
7. 任何失败均形成有限、可审计的 BLOCKED/WARN 结论，而不是自动反复重跑。

# 8. 推荐实施顺序

1. 固化当前 CsI baseline 的 hashes、命令和 authority outputs；
2. 完成 prompt source-normalization audit；
3. 追踪 prompt `eplus` survivor；
4. 完成 delayed convergence；
5. 构建并验证 BGO same-envelope geometry；
6. 先做 BGO smoke/pilot，再决定是否进入 matched full-stat runs；
7. 生成 CsI–BGO 对比和论文支持表格；
8. 最后才更新 manuscript-facing 数字和措辞。

该顺序能先排除归一化错误，再解释物理机制，最后进行材料比较，避免在基础权重尚未闭合时消耗大量计算资源。
