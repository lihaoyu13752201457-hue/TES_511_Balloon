# 交接文件 B：供第三方审阅的 S3d-O8 本底物理假说

更新时间：2026-08-14  
定位：**本文不是答案，而是一组要求新 session 独立证实、修正或否定的工作假说。** 不要因为它来自上一 session 就默认正确。

## B0. 审阅规则：先分清四种陈述

新 session 应把每项结论标为：

- **FACT**：可由当前 corrected-keV SIM、compact catalog 或几何直接复算；
- **INFERENCE**：由多个 FACT 支持的物理解读，但仍可能有替代解释；
- **HYPOTHESIS**：为设计优化提出、尚未闭环验证的机制；
- **FALSIFIER**：若出现什么结果，就必须放弃该假说。

不要用文件哈希、框架搭建或大批量盲跑来代替物理判断。真正要回答的是：什么粒子从哪里来，在什么材料第一次发生关键反应，为什么没有被 veto，之后如何把 511 keV 光子耦合进 TES。

![S3d-O8 瞬发与延迟本底的当前直观物理图](assets/s3d_o8_background_physical_picture.png)

这张图只画出当前最简物理解释。下一 session 必须用真实几何切片和事件坐标替换示意图，而不是把示意图当作证据。

## B1. 瞬发本底：目前真正观察到了什么

### FACT：W2 条件样本和三个主动层漏事件

- measured W2、active veto 前有 261 个事件，加权约 5.1558 cps；258 个在现有 BGO/plastic 中留下足够能量而被拒绝。
- veto50 后只剩 3 个事件、0.0507644 cps；三者都是 4.15--6.35 MeV primary gamma，精确 BGO 和 plastic 沉积均为零。
- Step05 后剩 2 个；再施加冻结的 pixel-center/deepest-layer 选择后只剩 event 19932。
- 261 个 W2 veto 前事件中，252 个可由 track ancestry 闭合为 `pair/conv -> e+ -> annihilation -> 511 gamma -> TES`；另 3 个有正电子/湮没 ancestry，6 个因 shower 前代缺口未闭合。这个结论属于 **W2 veto 前条件样本**，不是三条最终 leakage 的方向分布。

|event|初能|当前解析的入射侧|BGO 内路径|首次 pair host|最终命运|
|---:|---:|---|---:|---|---|
|3883|4.148 MeV|底部斜入射|3.148 cm|Nb inner cylinder|过 veto；被冻结空间门拒绝|
|19932|5.769 MeV|`+x/+z` 斜侧|5.290 cm|DR mixing-chamber Cu|唯一冻结 prompt|
|8081|6.346 MeV|`+x/-y` 斜侧|4.044 cm|Nb inner cylinder|过 veto；被 Step05 拒绝|

对这三条已选射线，已有解析没有识别到已建模 aperture、seam 或 relief；射线实穿 plastic、BPE、机械壳和 BGO，然后在内部被动材料 pair。三条路径的 BGO 光程来自既有 membership audit，**新 session 仍须独立复算坐标变换、入/出点和每个相交体积**。

### INFERENCE：为什么没有被屏蔽

当前最简解释不是“veto 阈值太高”，而是高能 gamma 在主动层中没有发生相互作用；主动层没有能量可供触发。危险链为：

```text
4--6 MeV gamma
  -> 无碰撞穿过当前 active shield
  -> 在高 TES 固体角的 Cu/Nb 中 pair conversion
  -> positron annihilation
  -> 一个 511 gamma 被 TES 全吸收，另一个逃逸/落在别处
  -> 外部 active shield 仍为零能量
```

在全部 261 个 W2 veto 前样本中，pair host 按加权贡献首先是 BGO side/bottom；这些事件几乎都能被 veto。真正危险的是“首次显著相互作用从主动 BGO 推迟到其内侧的 Cu/Nb/Ag/W”。因此一个直观设计指标是：

```text
内部件危险度 ~ pair opacity × 对 TES 的有效固体角 × 无 active-veto 概率
```

这只是物理排序指标，不是经过验证的闭式公式。

### 不能由现有数据推出的事情

- 三例不能给全天角 leakage map；4--10 MeV 的 W2 条件样本也只有 10 例、漏 3 例，而且不是 incident gamma 分母。
- 不能断言不存在所有未建模的服务孔、线束通道或 CAD/代理差异。
- 不能仅凭降低某个 pair host 的命中数宣称 prompt rate 下降。
- LC1 对 root19932 的 8192 个定向 gamma 中，baseline / Cu-only / Cu+Nb 的 raw `W2+veto50` 幸存为 `1/2/1`，raw W2 为 `3/4/3`。它证明 DR Cu hit 从 405 降到 53/43 且 host 会迁移，**没有证明 prompt 被压低**。

### 第三方必须重新回答

1. 三条 gamma 在 active BGO 中真的无相互作用，还是 scorer/volume alias 有遗漏？
2. 每条射线的 creator pair volume、positron 停止/annihilation volume 和 TES hit ancestry 是否分别闭合？
3. 用全体 incident gamma 作分母后，`energy × direction × active grammage` 的真实漏率是什么？
4. Mass_model_511 与 S3d-O8 是否显示相同的内侧 pair-host 规律？
5. 削 Cu/Nb 后，关键转换是否迁到 Ag proxy、Mu-metal、W 或剩余冷质量？

**FALSIFIER：** 若独立几何追迹显示漏事件实际通过稳定开口/缝隙，或 active scorer 漏记了真实沉积，则“主要是无碰撞穿透并在内部 pair”的设计主线必须重写。

## B2. 延迟活化：完整主线与冻结诊断必须分开

### FACT：官方 common-response 全样本

S3d-O8 的 day-15 delayed W2 为 420 个 selected lineage rows、0.05447975 cps。按入射生产族：n 43.46%、p 39.19%、alpha 8.24%、e+ 7.03%，其余约 2.1%。Cu-62、Cu-64、Cu-61 合计约 64.24%。主要源体积为：MXC 50 mK plate 30.78%、Nb inner cylinder 14.33%、Mu-metal outer cylinder 14.25%、L0 Cu disk 10.74%、50 mK can bottom 7.37%。

### FACT：冻结选择后的诊断子样本

冻结 pixel-center/deepest-layer 选择后为 135 rows、0.02320567 cps；由 retained weights 得到的 `Neff=12.04`。这个子样本用于研究“剩余可见热点”，不能覆盖上面的官方 day-15 rate。

|分类|冻结选择贡献|当前物理含义|
|---|---:|---|
|neutron|48.02%|少数高权重 n 路径控制|
|proton|39.43%|3 个 p survivor 已贡献 39.43%|
|Copper|73.70%|主要为 Cu-61/62/64|
|Nb|19.73%|以 `p -> Y-85`、`n -> Nb-89` 及少量 Nb-90 为主|
|Mu-metal|6.51%|当前主要由单个 `n -> Co-54` 路径控制|

Cu-64/Cu-61/Cu-62 合计占冻结 delayed 73.76%。名义体积排序为 MXC plate 32.56%、Nb inner 19.73%、L5 Cu support 13.14%、can bottom 11.11%、Mu-metal 6.51%、L0 6.04%、L2 6.00%。

但是 3 条 p、8 条 n、1 条 alpha 高权重记录已经贡献 `0.0214152 / 0.0232057 = 92.28%`。p 记录各有同一大权重，n 记录也各有同一大权重，所以 L5/L0/L2/Mu-metal 等若干“百分比热点”本质上是单事件量子化，不能直接解释成按同百分比减材就会得到同百分比收益。

### INFERENCE：目前最可信的空间物理图像

`生产活度 × 衰变分支 × 输运逃逸 × 对 TES 的空间耦合` 共同决定最终 W2；原始总 Bq 不能给优化顺序。近 TES 的 Cu/Nb/Mu-metal 同时具备两种危险性：

1. n/p/alpha 可在其中生产 β+ 或伴随 511/近 511 链的母核；
2. 它们离 TES 近、占据大固体角，衰变次级更容易在 TES 形成单个 W2 而不触发外 veto。

当前最值得先复核的部件不是按名义百分比机械排序，而是：

1. **MXC Cu plate**：prompt pair 与 delayed 的共同热点；多条 n/p/Cu-61/62/64 路径共同贡献。高权重源点位于约 `r < 7.62 cm`，所以只裁 `R=15 -> 12 cm` 没有直接切到核心热点，厚度/中心承载拓扑更值得研究。
2. **Nb inner cylinder**：三条 prompt 漏事件中两条在此 pair，并承担显著 delayed；但磁闭合是硬约束。
3. **50 mK can bottom**：既是 veto 前内部 pair host，也有 n/alpha -> Cu-64 delayed。
4. **DR mixing Cu 与 Ag-sinter proxy**：唯一冻结 prompt 在 DR Cu；减 DR Cu 后已观察到 host 迁移。真实 Ag 孔隙率、质量和位置尚需 BOM 对账。
5. **L5/L0/L2 supports 与 Mu-metal**：当前排序多由单个高权重事件决定，先验证、后优化。
6. **W bottom**：在 veto 前承担若干 pair 链但当前均被 veto；改变内部拓扑后必须检查它是否变成新 leakage host。

### 当前数据仍缺什么

- delayed lineage 给出生产入射 family、母核、衰变源坐标和材料，但没有完整保存导致该母核生产的 primary n/p 能量、入射方向和具体反应道。
- source realization 与 full inventory 的 joint mix 有可见偏差；细路径不能只看当前抽样。
- 需要分别画出每个部件的 production Bq 与 `selected W2 / Bq` coupling，否则无法区分“产得多”和“离 TES 太近”。

**FALSIFIER：** 若增加独立 n/p 生产统计后，MXC/Nb/can 的稳定贡献消失，或主要 W2/Bq coupling 转移到远端材料，则“近端低 grammage 是主路线”的假说应降级。

## B3. 优化假说：允许研究，但不预设为答案

以下只定义物理方向。新 session 必须比较少数简单方案并独立给出最终选择。

### H1：降低 BGO 内表面至 TES 之间的高固体角 grammage

- 对 Cu 冷盘/罐底/支撑，比较均匀减厚、保留中心接口 boss 的简单辐条或环形承载、以及把非必要质量移到 TES 小固体角区域。
- 不要先冻结“3 mm MXC 最优”；真实热流、承载、线束与装配决定最低可用质量。
- 不要用更多近端高 Z 材料去挡 proton/gamma；它可能成为新的 pair/activation host。

### H2：Nb 只作为受磁约束的独立候选

- 先比较闭合 2 mm 与 1 mm 壳；0.5 mm 只能是敏感性极限，不是工程推荐。
- 必须同时验证静/动态磁场、开口/接缝、过 Tc 场冷、磁通俘获与 TES/SQUID 噪声。
- 如果磁功能不允许减薄，则优化应转向 Nb 的轴向位置、开口长径比或其外侧质量拓扑，而不是破坏闭合面。

### H3：保持现有主动屏蔽通道，不增加新符合探测器

- 保留现有 BGO/plastic 读出架构。
- 只有有分母的方向统计证明稳定象限，才研究**现有 BGO 质量的重新分配、局部外侧加厚或整体靠近**；不能由三例冻结 sector。
- 全周盲目增厚不是首选：质量大，4--6 MeV 无碰撞尾仍存在，还可能增加中子次级或自身活化。

### H4：中子屏蔽必须在生产能谱/方向闭合后决定

- 若 n 明确主导近端 Cu/Nb 活化，再比较外层 BPE 的位置/厚度重新分配，以及 B4C 或含 ^6Li 的含氢俘获材料。
- 必须同时计算俘获 gamma、绕行、级联和增加质量；不能把旧边界电流 fold 当净 W2 结论。

### H5：材料替代要按功能逐件判断

- 非热接口、非磁功能、非高强度承载的 Cu 才能进入低 Z/低活化材料替代候选。
- 不能把“Cu 是热点”简化成全换 Al；Al 的热、电、结构、表面、放气与自身活化都要逐件闭合。
- Ag-sinter proxy 必须先用实物 BOM、孔隙率和有效密度修正，不能把实体代理直接线性减掉。

## B4. 当前预算说明了什么、没有说明什么

|口径|当前 F3|到 `3e-5` 的含义|
|---|---:|---|
|官方 S3d stage-06 central|`6.9238e-5`|若信号不变，20 天背景约需降 81.2%|
|冻结选择诊断|`5.1490e-5`|若信号不变，背景约需降 66.1%|

LC2 的 event-coordinate excision 与 uniform-activity mass scaling 只是 unchanged-transport 代理，不是物理上下界。前者即使把 prompt 设为零仍略高于目标；后者只有在 prompt 至少降低约 77.2% 时才有预算过线。两者都没有候选 focused signal、完整 INSTANT、BUILDUP -> inventory -> delayed 和 common-response 闭环。

所以这里没有“上一 session 已经找到最优方案”的结论。正确状态是：**共同热点假说较强，具体尺寸和最优拓扑尚未确定。**

![当前来源预算与候选任务门；只用于预算，不是空间热点图](../s3d_o8_low_grammage_core_20260814/figures/source_budget_and_candidate_gate.png)

## B5. 新 session 必须制作的物理图，而不是更多流程图

1. **prompt 几何图**：同一 InstrumentFrame 的 `x-z`、`y-z` 和横截面，叠加全部已选漏射线、active BGO 边界、每段材料光程、first pair、annihilation 与 TES hit。再给 `incident E × direction` 分母图。
2. **delayed 空间图**：按独立 source position 聚合的轴向-径向或 3D scatter；颜色=材料，形状=n/p/alpha，点大小=selected rate；单事件高权重点必须特别描边，禁止用平滑 heatmap 掩盖离散性。
3. **生产到探测的 Sankey/flow**：`incident family -> material -> parent isotope -> volume -> selected W2`，并把 production Bq 与 W2/Bq coupling 分两栏。
4. **候选前后图**：同一截面叠加被删/移/替换的材料，以及 prompt pair-opacity/TES-solid-angle 和 delayed source/coupling 的预计变化。

## B6. 给第三方的判决模板

对每个热点和每个候选，最终只允许三种判决：

- **SUPPORTED**：独立事实与小规模配对验证共同支持；
- **REFUTED**：出现明确反例或 host migration，淘汰；
- **UNRESOLVED**：统计或工程约束不足，不得包装成最优方案。

最后必须选择一个单一主方案；如果当前证据不足，也应明确写成“工程条件最优”并列出唯一阻断证据，而不是堆一长串平行方案。

## B7. 核心复核入口

- 上一 session 的待审报告：[`../s3d_o8_low_grammage_core_20260814/REPORT.md`](../s3d_o8_low_grammage_core_20260814/REPORT.md)
- prompt 261 事件：[`../s3d_o8_low_grammage_core_20260814/data/prompt_w2_event_summary.csv`](../s3d_o8_low_grammage_core_20260814/data/prompt_w2_event_summary.csv)
- 三条 prompt 射线：[`../s3d_o8_low_grammage_core_20260814/data/prompt_veto_leak_ray_paths.csv`](../s3d_o8_low_grammage_core_20260814/data/prompt_veto_leak_ray_paths.csv)
- frozen delayed 坐标：[`../s3d_o8_low_grammage_core_20260814/data/frozen_delayed_source_coordinates.csv`](../s3d_o8_low_grammage_core_20260814/data/frozen_delayed_source_coordinates.csv)
- 官方 full lineage：[`../m05_corrected_reanalysis_20260813/outputs/04_common_response/selected_background_w2_lineage.csv`](../m05_corrected_reanalysis_20260813/outputs/04_common_response/selected_background_w2_lineage.csv)
- inventory：[`../m05_corrected_reanalysis_20260813/outputs/02_activation/day15_inventory.csv`](../m05_corrected_reanalysis_20260813/outputs/02_activation/day15_inventory.csv)
