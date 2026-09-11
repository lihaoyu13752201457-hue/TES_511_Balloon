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

## 7. 2026-08-17 SG3B 输运追加交接

SG3B 新几何的原始输运已经落在新挂载盘：

- 数据根目录：`/mnt/data/TES_Balloon_511_data/SG3/`
- prompt/BUILDUP：41 个 PASS jobs，共 6,887,107 个 accepted primaries；
- M05 day-15 exact-position delayed：33 个 PASS jobs，共 8,000,000 个 decay triggers；
- PARMA atmospheric mono-511 line：13 个 PASS jobs，共 3,000,000 个 photons；
- 总计 87 个 PASS receipts、17,887,107 个输运单位；当前目录占用约 80.82 GiB。

精确状态边界：initial prompt/BUILDUP controller 是 `FAILED`（21 个计划任务中
`sg3b_buildup_alpha_shard0001` 的 1,448 histories 没有 PASS receipt），但其余
20 个 retained jobs 均 PASS；extra-2x controller 才是 21/21 `COMPLETE`。上述
41-job/6,887,107-primary 总数只统计 canonical PASS receipts，不包含缺失的
1,448-history alpha BUILDUP 任务。

这里的三类计数具有不同源定义和归一化，不能当作同一事件池或同一物理曝光直接相加。PARMA511 是独立 line-only response sidecar；repaired `unit_only_total_gamma` 已包含宽箱湮没隆起，因此在建立 flux-closed 去重/重组合同之前，不得把两者直接相加。

详细的路径、分片、种子、几何哈希、失败试跑边界和下一会话只读检查顺序见：

- [`SG3B_SIMULATION_EXECUTION_HANDOFF_20260817.md`](SG3B_SIMULATION_EXECUTION_HANDOFF_20260817.md)

新会话应先读本提纲和上述执行附录，只核对计划、controller state 与 receipts；不要为了“复习”扫描或哈希大型 SIM payload，也不要立即重跑、删除、合并或做论文数值替换。当前只完成 transport，尚未完成 SG3B 的统一 detector-response、Step05/FoV closure、物理率归一化和几何 promotion。

## 8. 2026-08-18 SH3 OptV3 当前质量模型候选与生产前审计

用户提出把六层 TES 从 DR 冷盘投影下方移入独立烟囱，并在烟囱内保留
局部多层壳、40 mm BGO、简单 W 方框和曲折冷指。当前非覆盖候选是：

`engineering/geometry_optimization_20260815/sh3/assembly_opt_v3/`

当前权威文件：

- 几何：`geometry/SH3_Assembly_OptV3.geo`，SHA-256
  `a270ab2caf340a34858b448374b3dad955878ebbb9df9169f97d80df46026934`；
- setup：`geometry/SH3_Assembly_OptV3.geo.setup`，SHA-256
  `52397889d6ac0d08296549942633ff09216cf1494fedb985127c48120d46eaea`；
- detector map：`geometry/SH3_Assembly_OptV3.det`，SHA-256
  `12d3a6831f3d00da6668f48487e5d83f7a0354419fdec75cfec211b28373cae9`；
- 清单：`data/assembly_opt_v3_manifest.json`；
- 静态检查：`audit/assembly_opt_v3_static_validation.json`；
- 完整零输运重叠检查：`audit/assembly_opt_v3_overlap_validation.json`；
- SG3B 最小改动审计：
  `audit/SG3B_MINIMAL_CHANGE_AUDIT_20260818.md` 与
  `audit/sg3b_minimal_change_audit.json`。
- `gpt-5.6-sol / high` 独立复核后的等统计量方案：
  `OPT_V3_EQUAL_SG3B_SIMULATION_PLAN_20260818.md`。

OptV3 的 300 K 外壳不再使用已否决的 OptV2 锥壳/小喷嘴，而是：

```text
((DR side shell UNION DR bottom cap) UNION chimney outer solid)
MINUS chimney bore
MINUS DR main cavity
```

该布尔使 3 mm 烟囱铝壳与 DR 曲面外壳成为同一个鞍形连接实体。烟囱轴和
四层内冷指孔中心在局部 `z'=-2.80 cm`；烟囱最低点 `-13.85 cm`，高于
DR 底面 `-14.10 cm` 0.25 cm。完整 Cosima/Geant4 构建与每 placement
10,000 点、0.0001 cm 容差重叠检查通过；未启动粒子输运。

与已实际模拟的 SG3B 哈希权威比较后，当前结论必须分成两层：

1. **没有发现无法解释的几何删除或共有体积属性漂移。** 168 个共有 declared
   volumes 中，130 个属性块完全相同；37 个 TES/Si/Cu 核心与支撑体统一平移
   `(-35.55, 0, +2.40) cm` 进入烟囱，另 1 个 NF2 顶安装环改成带光轴切口
   的 shape，没有非预期共有体积属性变化。SG3B/OptV3 共有 2,496 个 copy
   placement，placement 块逐字节一致；SG3B 独有的 624 个 copies 全部属于
   已明确移除的旧 W 多孔准直器。69 个 SG3B 独有 declared volumes 已全部
   分类为旧外 BGO/Kapton/机械壳、旧四支冷指、旧窗口壳、旧 W、外塑闪/BPE，
   或近 TES Bi/Al/readout/cable 代理，没有未分类名字。六层 TES、2,256 个
   Ta 像素及继承的 Si/Cu 支撑几何均保留。
2. **但还不能声称“只做必要改动、已经可以等统计量生产”。** 当前审计状态
   是 `REVIEW_REQUIRED__NOT_OPT_V3_PRODUCTION_AUTHORITY`，原因是：
   - SG3B 有 62 个 scorer 指向 OptV3 仍保留的几何，其中 56 个被动质量
     lineage scorer 没进入 OptV3 detector map；
   - SG3B 的 SQUID/readout 盒与五段 Al cable-bundle 代理被移除，尚无烟囱版
     替代，这会影响 prompt/activation 质量闭合；
   - SG3B Bi 半筒与外塑料正电子 veto 未进入 OptV3；这是显式设计差异，
     但必须由用户确认排除或授权烟囱兼容替代，不能当作无关删减；
   - 三个新 BGO volume 名尚未通过成熟 group-summed veto 映射 receipt；46 个
     新增被动材料体（30 Al、11 Cu、4 W、1 Be）尚缺完整 thermal-stage 与
     prompt/activation lineage 所有权；
   - SG3B setup 使用 `SurroundingSphere 60 5 0 9 60`，OptV3 当前使用
     `SurroundingSphere 95 0 0 8 95`。源面面积/位置不同，等 raw histories
     不等于等物理曝光，必须先做包络与源面/TT 合同闭合。
   - 简单 W 方框内半宽恰为 `2.70 cm`，只与声明的 `r=2.70 cm` 光学圆相切，
     解析余量为零。背景生产前必须用冻结的 37,194 条全包络焦面光线建立
     独立 W 截获/通光 receipt；若有任一有效光线触 W，或机械公差要求正余量，
     应先放大开口再冻结几何。

因此 OptV3 目前是**几何审查候选**，不是 corrected-keV 生产权威。任何新模型
只能先提出修复与模拟计划，不得直接运行。用户要求的“与 SG3B 同统计量”应在
上述四项闭合后，至少按 SG3B canonical accepted cell 目标规划：

- INSTANT：22 个 accepted jobs、3,842,079 primaries；
- BUILDUP：19 个 accepted jobs、3,045,028 primaries；
- prompt/BUILDUP 合计：41 个 PASS jobs、6,887,107 primaries；
- day-15 exact-position delayed：33 个 PASS jobs、8,000,000 triggers，八族
  各 1,000,000；
- 独立 PARMA mono-511 sidecar：13 个 PASS jobs、3,000,000 photons；它仍然
  不能直接与已含湮没隆起的 repaired broadband gamma 相加；
- 账面合计 87 个 PASS receipts、17,887,107 个不同归一化的输运单位，不能
  视作一个事件池或一个等效曝光。

“同统计量”必须进一步解释为同 `mode × family × source-cell` accepted target、
独立新种子和新的 OptV3 receipt/geometry hash 绑定；不能只匹配总数，也不能
假设缺失 1,448-history alpha BUILDUP 的 SG3B 初始任务构成完美三倍曝光。
若源面必须变化，仍可匹配 raw histories，但物理 TT/率必须按新源面重新计算，
不得复制 SG3B TT。

完整的 per-family/cell 目标、37,194-ray signal 前置门禁、失败/重试语义、
磁盘下限与 common marked-Poisson 后处理顺序见 OptV3 包内的
`OPT_V3_EQUAL_SG3B_SIMULATION_PLAN_20260818.md`。该文件状态为
`PLAN_ONLY__PRODUCTION_NOT_AUTHORIZED`；当前没有启动任何新输运。

## 建议的新会话开场语

> 请先读 `engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/NEXT_SESSION_REVIEW_OUTLINE.md`，再读同目录的 `SG3B_SIMULATION_EXECUTION_HANDOFF_20260817.md`。先只读复习并回报你理解的源合同、数据状态、禁止事项与下一步缺口；不要启动模拟、删除数据或直接把 SG3B 数值写入论文。复用现有代码和 corrected 数据，后续再做 Mass、S3d-O8 与 SG3B 的事件路径/来源分解和 detector-response closure，暂时不要从头重建模拟链。
