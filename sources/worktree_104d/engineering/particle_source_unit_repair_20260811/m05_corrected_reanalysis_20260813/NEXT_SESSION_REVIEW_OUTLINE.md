# 新会话复习提纲：Mass511 / S3d-O8 本底来源与优化

这是一份简短入口。目标是让新会话直接进入两件事：**瞬发本底粒子路径分析**与**活化本底降低**，不必重新梳理全部项目历史。

## 1. 两个几何模型

- **Mass_model_511**：详细质量模型与参考基线。保留 Ta/TES 焦平面、低温系统及分段 CsI 主动屏蔽，用来回答“原始完整仪器的本底在哪里”。
- **S3d-O8**：在同一 TES/低温核心上形成的屏蔽修改版。主要特征是侧/底/顶约 **40/30/10 mm BGO**、**20 mm 5 wt% BPE** 和 **10 mm 塑料闪烁体正电子 veto 层**。它是与 Mass 做匹配比较的当前优化几何。
- 两个模型采用同一 corrected-keV 粒子场、响应和选择逻辑比较；几何差异应通过事件路径和来源分解解释，而不是只比较总率。

## 2. 模拟思路

项目沿用 M05 的三条物理分支：

```text
511 keV 点源 -> Laue 光学/EventList -> 探测器信号重放

八族大气粒子 -> INSTANT -> 瞬发本底事例

八族大气粒子 -> BUILDUP -> 核素/体积/位置清单
                         -> day-15 活度与精确位置衰变源
                         -> delayed transport -> 活化本底事例
```

八族为 `p, n, alpha, gamma, e-, e+, mu-, mu+`。现有 corrected 主数据约为 **7.68M instant histories、6.09M buildup histories**；延迟输运为 15 个正活度单元、共 **3.75M decay triggers**。

M05 流程图可作为方法地图：

![M05 端到端模拟与分析流程](../../../core_md/balloon511_ea_latex_drafts/paper_source_figure_table/fig_simulation_workflow_corrected_zh_20260810.png)

只需记住一个版本变化：当前 broadband-total gamma 已包含湮没隆起，不再叠加流程图中的独立大气 mono-511 分支。

## 3. 后处理思路

1. 原始 SIM 流式整理为事件级/像素级 compact catalog。
2. 信号、瞬发和 delayed 使用同一 TES 响应：420 eV FWHM、0.3 keV 像素阈值。
3. 应用精确主动 veto：Mass 用 CsI；S3d 用 BGO 与塑闪；再运行 Step05 Compton/FoV 轨迹约束。
4. 同时保留 480–550 keV 宽窗与 `W2 = 510.58–511.42 keV` 窄窗。
5. 瞬发按粒子族归一；delayed 按入射族、母核素、产生体积和材料回溯。优化判断应基于**选后本底及其耦合路径**，而不只看总活度。

## 4. 当前结果的导航线索

- W2 选后总本底：Mass 约 **0.2313 cps**，S3d-O8 约 **0.0883 cps**；S3d 的中心值明显更低。
- S3d 瞬发残余目前来自少量高能 gamma：穿过外部主动层后，在内部 Nb/Cu 等被动质量中产生正负电子对，湮没 511 keV 光子再进入 TES。这是下一步应扩展统计的工作假设。
- S3d delayed 选后本底主要耦合到 TES 附近的 Cu/Nb/MuMetal 结构；Cu-61/62/64 和若干冷盘、磁屏蔽、近 TES 支撑件值得优先研究。
- Laue 光学有效面积仍是 **20.08476 cm²**；约 15 cm² 是经过 TES 能量沉积、W2 和拓扑选择后的系统选后有效面积，两者不是同一个量。
- BPE 的 2 cm 边界诊断显示对直接 Cu 快中子活化有一定正收益；是否加厚应同时考虑内部活化、BPE 自身 C-11、质量和信号通道，适合作为后续独立参数扫描。

## 5. 新会话的两条主线

### A. 瞬发本底来源

- 建立 `粒子族 -> 入射能量/方向 -> 首次关键相互作用体积与过程 -> 次级粒子 -> TES 命中 -> veto/Compton 结果` 的事件路径表。
- 先分析所有 W2 pre-veto、veto survivor 和最终 survivor，再扩展到 480–550 keV，避免只盯最终个位数事件。
- 对比 Mass 与 S3d 的体积、过程和入射方向预算，找出是外屏蔽穿透、几何开口，还是内部被动质量造成残余。
- 根据路径再决定最小 matched 模拟：内部质量 knockout/替材/移位、局部 active guard、屏蔽厚度或焦斑 ROI。

### B. 活化本底降低

- 从 detector-selected delayed lineage 出发，按 `incident family × parent isotope × source volume/material` 排名。
- 同时看产生活度和进入 TES 的耦合效率（可用 selected cps/Bq 辅助），优先处理“活度不一定最大、但离 TES 近且耦合强”的质量。
- 首批候选：MXC Cu 冷盘、L0 近 TES 铜支撑盘、Nb 内磁屏蔽、MuMetal 外磁屏蔽和铜罐底部。
- 先用现有 catalog 做来源图和可移除质量清单，再选择少量几何变体复用现有 BUILDUP -> inventory -> delayed -> common-response 链验证。

## 6. 最短入口

- 总入口：[README.md](README.md)
- 共同合同：[analysis_inputs.json](analysis_inputs.json)
- 瞬发 cutflow：[outputs/01_prompt/prompt_cutflow.csv](outputs/01_prompt/prompt_cutflow.csv)
- 最终 W2 事件 lineage：[outputs/04_common_response/selected_background_w2_lineage.csv](outputs/04_common_response/selected_background_w2_lineage.csv)
- day-15 inventory：[outputs/02_activation/day15_inventory.csv](outputs/02_activation/day15_inventory.csv)
- delayed 体积分解：[outputs/05_matched_comparison/w2_delayed_volume_breakdown.csv](outputs/05_matched_comparison/w2_delayed_volume_breakdown.csv)
- delayed 母核素分解：[outputs/05_matched_comparison/w2_delayed_parent_breakdown.csv](outputs/05_matched_comparison/w2_delayed_parent_breakdown.csv)
- BPE 边界诊断：[../bpe_neutron_boundary_20260813/REPORT.md](../bpe_neutron_boundary_20260813/REPORT.md)
- M05 中英文稿：[`core_md/balloon511_ea_latex_drafts/m05_atm511_source_revision_20260811/`](../../../core_md/balloon511_ea_latex_drafts/m05_atm511_source_revision_20260811/)

## 建议的新会话开场语

> 请先读 `engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/NEXT_SESSION_REVIEW_OUTLINE.md`。复用现有代码和 corrected 数据，先做 Mass 与 S3d-O8 的瞬发本底事件路径/来源分解，再按 detector-selected delayed lineage 分析活化本底集中在哪些核素和结构质量上，并提出最小、可配对验证的降本底几何修改；暂时不要从头重建模拟链。
