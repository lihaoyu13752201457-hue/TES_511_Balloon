# 交接文件 A：项目主线、双质量模型、模拟链与最终通量口径

更新时间：2026-08-14  
用途：供新 session 先建立共同事实底座。本文只复习当前 corrected-keV 主线，不替任何新几何作晋级结论。

## A0. 最短阅读顺序

1. 本文件；
2. [`../m05_corrected_reanalysis_20260813/NEXT_SESSION_REVIEW_OUTLINE.md`](../m05_corrected_reanalysis_20260813/NEXT_SESSION_REVIEW_OUTLINE.md)；
3. [`../m05_corrected_reanalysis_20260813/README.md`](../m05_corrected_reanalysis_20260813/README.md)；
4. [`../m05_corrected_reanalysis_20260813/analysis_inputs.json`](../m05_corrected_reanalysis_20260813/analysis_inputs.json)；
5. stage 04、05、06 的报告与表；
6. 然后再读交接文件 B，且把 B 当成待审物理假说，不要当成答案。

不要把 `superseded/` 或仍引用 `cosima_spectra_dp_2602units` 的历史 broadband 结果恢复为物理权威。当前 gamma profile 是 `unit_only_total_gamma`，已经包含湮没隆起，不能另加大气 mono-511 分支。

## A1. 两个比较对象

### Mass_model_511

- 角色：详细质量模型和参考基线，用来回答“完整原始仪器中，哪类材料和位置产生本底”。
- 保留共同 TES/Ta 焦平面、低温系统、支撑与磁屏蔽。
- 主动反符合为 24 个精确列名的 CsI 侧壁、底部和顶部体积。
- 当前 setup 入口由 `analysis_inputs.json` 的 `geometries.Mass_model_511.setup` 指定。

### S3d-O8

- 角色：与 Mass 使用相同 corrected 粒子场、信号、响应和选择逻辑的当前屏蔽优化几何。
- 与 Mass 共享 TES/低温核心，但外部主屏蔽改成：约 40 mm 侧壁 BGO、30 mm 底部 BGO、10 mm 顶部 BGO、20 mm 5 wt% BPE、10 mm 塑料闪烁体外层。
- 主动反符合是 3 个 BGO 体积加 3 个塑料体积，共 6 个精确列名体积。
- 当前 setup 入口由 `analysis_inputs.json` 的 `geometries.S3d_O8.setup` 指定。

比较原则：总率只告诉“哪个好”，不能告诉“为什么”。几何差异必须继续拆成入射粒子、方向、首次关键相互作用、次级链、产生材料、离 TES 的空间耦合和选择 cutflow。

## A2. corrected-keV 输入和模拟规模

八个大气粒子族为：

`p, n, alpha, gamma, e-, e+, mu-, mu+`

当前 canonical selection 合并 batch0000--batch0007 及 continuation，边界为 `geometry × mode × family`，不得跨单元混池归一化：

|模式|jobs|primary histories|
|---|---:|---:|
|INSTANT|530|7,684,156|
|BUILDUP|446|6,092,936|
|合计|976|13,777,092|

按几何为：Mass_model_511 6,888,549 histories，S3d-O8 6,888,543 histories。六个 histories 的差异是保留的实际输入，不人为配平。

正式 delayed transport 覆盖 15 个正 ground-state activity 的 geometry-family cells，共 3,750,000 decay triggers；每个正单元实际为 250,000 triggers。Mass/mu+ 是显式零源单元，不是漏输入。

## A3. 三条物理模拟链

```text
focused signal
511 keV 点源 → Laue optics / EventList → post-Be injection → TES signal SIM

prompt background
八族大气粒子 → corrected INSTANT → prompt SIM → compact catalog

delayed activation background
八族大气粒子 → corrected BUILDUP
               → geometry×family×volume×parent ZA/state production
               → day-15 inventory + exact source positions
               → radioactive decay source
               → delayed transport SIM → compact catalog
```

![M05 corrected 端到端流程](../../../core_md/balloon511_ea_latex_drafts/paper_source_figure_table/fig_simulation_workflow_corrected_zh_20260810.png)

### focused signal

- 复用 post-Be-window focused EventList；没有在 stage 04 重跑光学。
- 两个几何共用同一份 37,194-event focused EventList，因此几何比较不含不同光学抽样的混杂。
- Laue optics 几何有效面积是 20.08476 cm²。
- 约 15 cm² 是经过 TES 沉积、能窗与拓扑选择后的 selected effective area；二者不可混用。
- stage 04 的信号 Aeff 条件于 Be-window injection plane，并不包含完整 BPE/plastic 外包络透射系统学。

### prompt / INSTANT

- prompt 率必须在每个 `geometry × family` 单元先做 `selected / sum(TT)`，再跨族相加。
- 不得把不同 family 的 events 或 TT 混在一个总池中。
- stage 01 已扫描 530 jobs / 7.684M histories，并生成位置保持的 compact catalog 与 cutflow。

### BUILDUP → inventory → delayed

- BUILDUP 产额按 `sum(RP)/sum(TT)` 在 `geometry × family × volume × parent state` 内归一；零 RP 的 DAT live time 仍进入分母。
- day-15 inventory 保留 parent ZA/state、产生体积/材料、位置、过程、ancestry、半衰期与 NUBASE ground-state 处理。
- 已知但不能作为 ground-state 输运的 state 不被静默折叠。S3d-O8 仍有 0.0998093 Bq 的已知 excited-state holdout。
- delayed source mix 由精确位置块抽样。位置 mix 的不确定性与最终 event-count MC 误差是两件事。
- stage 03 保持 response-neutral：不 smear、不 veto、不运行 Step05；所有流统一在 stage 04 重放响应。

## A4. 共用后处理链

```text
raw SIM
  ↓ 流式整理
position-preserving compact catalog
  ↓
同一 keyed TES response
  ↓
0.3 keV measured-pixel threshold
  ↓
W2 / 480–550 keV energy window
  ↓
精确 active-volume veto（nominal 50 keV）
  ↓
retained Step05 Compton/FoV topology
  ↓
selected rate / lineage / mission fold
```

共同分析合同：

- TES energy response：0.42 keV FWHM；
- measured-pixel threshold：0.3 keV；
- 窄窗：`W2 = 510.58–511.42 keV`；
- 宽窗：480–550 keV；
- nominal active veto：50 keV；70/80 keV 只保留为 scan；
- Step05 使用保留的 Compton/FoV selector；
- compact catalog 保留 TES pixel UID/能量/位置、精确 shield energy、S3d plastic energy、active occupancy；
- signal、prompt、delayed 使用相同 response 和 stage 顺序。

`selected_background_w2_lineage.csv` 是最终 W2 背景的逐事件谱系入口。prompt 行保存 family/job/seed/event/source 等；delayed 行还保存 source parent、source volume、source excitation、transport daughter 与 parent match。不要把 source parent 和 SIM `IA INIT` daughter 混为一个核素。

## A5. stage 02：day-15 inventory

|geometry|known day-15 activity|transported ground-state activity|
|---|---:|---:|
|Mass_model_511|482.117936 Bq|482.117936 Bq|
|S3d-O8|1404.23088 Bq|1404.13107 Bq|

直观提醒：S3d 的总 Bq 更高，不代表 detector-selected delayed W2 更高。几何耦合、衰变通道、遮挡、离 TES 的距离和固体角会重新排序材料优先级。

## A6. stage 04/05：共同响应后的 day-15 结果

|geometry|prompt W2|delayed W2|total W2|selected signal Aeff|
|---|---:|---:|---:|---:|
|Mass_model_511|0.12341856 cps|0.10785396 cps|0.23127252 cps|15.11676 cm²|
|S3d-O8|0.033842928 cps|0.054479752 cps|0.088322680 cps|15.04170 cm²|

匹配比较的中心值：

- S3d/Mass total background = 0.381899，即中心值降低 61.81%；
- S3d/Mass selected Aeff = 0.995035，即中心值损失约 0.50%；
- detector-plane `Aeff/sqrt(B)` 中心诊断比 = 1.610；
- prompt 的 MC 支撑只有 Mass 7、S3d 2 个 W2 events；不能把精确小数误当成高精度材料定律。

这些是 constant-environment day-15 共同响应结果，不是 20 天任务最终通量。

## A7. stage 06：20 天解析任务场景

场景假设：

- top-of-atmosphere reference flux：`1e-4 photon cm^-2 s^-1`；
- 20 天、81 trajectory nodes；
- source elevation 45°，固定 slant atmospheric transmission；
- inventory 从 mission day 0 的零活度开始，不含 ground/pre-flight activation；
- family flux 用 PARMA 81-node 相对比例变化，但每个 family 内部能谱、角分布、detector response 和 activation yield 固定；
- significance 定义为累计 `S/sqrt(B)`；
- 这是 analytic family-scalar scenario，不是 multipoint transport authority。

|geometry|S20 counts|B20 counts|Z20 central|3σ crossing|F3(20 d) central|conditional proxy F3|
|---|---:|---:|---:|---|---:|---:|
|Mass_model_511|1677.654|383408.450|2.7094|20 d 内未达到；sqrt-time 24.52 d|`1.10726e-4`|`2.24835e-4`|
|S3d-O8|1645.388|144203.842|4.3329|9.3677 d|`6.92375e-5`|`2.05006e-4`|

### “最后的最小可分辨通量”应如何表述

- 当前主线的 central 20-day 3σ flux threshold，即 F3，是：Mass `1.10726e-4`、S3d-O8 `6.92375e-5 photon cm^-2 s^-1`，均指 top-of-atmosphere。
- conditional proxy 使用 prompt componentwise Garwood upper、delayed parent-mixture upper proxy 和 signal Clopper–Pearson lower endpoint；它不是 joint 95% interval。对应 Mass `2.24835e-4`、S3d `2.05006e-4`。
- 因此不能只写一个“最终灵敏度”数字而不标 central/proxy 和场景假设。
- 两个几何的 conditional proxy 在 20 天都未达到 3σ；两个几何在 central 场景下都未在 20 天达到 5σ。

## A8. 后续冻结选择与低面密度分析的位置

`../s3d_o8_low_grammage_core_20260814/` 是 mainline 之后的诊断/筛选包，不是 stage 06 的替代权威。

其中 signal-only 冻结选择采用固定 pixel-center centroid `r <= 1.35 cm` 与 deepest layer `<= L3`：

- Aeff 13.62852 cm²；
- prompt 0.0169215 cps；
- delayed 0.0232057 cps；
- 在保留旧 mission shape 的条件折叠中 F3 约 `5.149e-5`。

这个数只用于研究“选择 + 几何”可能的预算，不应覆盖 stage 06 官方 central F3。候选 LC1/LC2 也只做 screening proxy；没有完成候选 focused signal、full prompt、BUILDUP、delayed 和 common-response 闭环。

## A9. 新 session 必须持续保留的边界

1. corrected broadband gamma 已包含 annihilation bump，不叠加 mono-511；
2. 不跨 geometry/mode/family 混池 TT；
3. inventory Bq 不是 detector-selected W2；
4. source parent 不是 transport daughter；
5. stage 04 day-15 率不是 stage 06 20-day F3；
6. central、MC counting proxy、source-position mix、optics、atmosphere/trajectory 系统学必须分开；
7. prompt 最终事件极少，任何方向或材料“热点”都要同时报告分母和有效统计；
8. 新优化的目标是物理来源闭合后再做少量 matched 验证，而不是重建整条基础链。

历史提醒：修正能轴前的 broadband/activation/F3 以及曾经独立叠加的 mono-511 sidecar 只保留为方法史，不能用来支持当前几何排名或灵敏度。

## A10. 核心数据入口

- 输入与共同合同：[`../m05_corrected_reanalysis_20260813/analysis_inputs.json`](../m05_corrected_reanalysis_20260813/analysis_inputs.json)
- prompt cutflow：[`../m05_corrected_reanalysis_20260813/outputs/01_prompt/prompt_cutflow.csv`](../m05_corrected_reanalysis_20260813/outputs/01_prompt/prompt_cutflow.csv)
- day-15 inventory：[`../m05_corrected_reanalysis_20260813/outputs/02_activation/day15_inventory.csv`](../m05_corrected_reanalysis_20260813/outputs/02_activation/day15_inventory.csv)
- delayed source mix：[`../m05_corrected_reanalysis_20260813/outputs/03_delayed/delayed_source_mix.csv`](../m05_corrected_reanalysis_20260813/outputs/03_delayed/delayed_source_mix.csv)
- common response：[`../m05_corrected_reanalysis_20260813/outputs/04_common_response/REPORT.md`](../m05_corrected_reanalysis_20260813/outputs/04_common_response/REPORT.md)
- final event lineage：[`../m05_corrected_reanalysis_20260813/outputs/04_common_response/selected_background_w2_lineage.csv`](../m05_corrected_reanalysis_20260813/outputs/04_common_response/selected_background_w2_lineage.csv)
- matched source tables：[`../m05_corrected_reanalysis_20260813/outputs/05_matched_comparison/REPORT.md`](../m05_corrected_reanalysis_20260813/outputs/05_matched_comparison/REPORT.md)
- mission result：[`../m05_corrected_reanalysis_20260813/outputs/06_mission/REPORT.md`](../m05_corrected_reanalysis_20260813/outputs/06_mission/REPORT.md)
- machine-readable mission summary：[`../m05_corrected_reanalysis_20260813/outputs/06_mission/summary.json`](../m05_corrected_reanalysis_20260813/outputs/06_mission/summary.json)
