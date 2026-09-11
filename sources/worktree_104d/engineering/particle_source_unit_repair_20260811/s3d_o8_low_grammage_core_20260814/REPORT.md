# S3d-O8 本底来源诊断与低面密度优化路线

日期：2026-08-14  
状态：**来源诊断与筛选完成；没有几何晋级或达到任务指标的物理权威**

## 结论先行

S3d-O8 当前应走的主路线不是在 mK 级增加闪烁体，也不是把铜读出化。本方案明确排除这两项。来源证据支持的是：

1. **保留现有外部 4 cm 侧壁 / 3 cm 底部 BGO 作为基准。** 对当前三个已选 W2+veto50 漏事件，解析射线路径均未识别已建模 aperture、seam 或 relief；它们是 4.15--6.35 MeV 入射 gamma 穿过现有主动层却没有发生相互作用，随后在近 TES 的 Cu/Nb 中成对产生。因此降低 veto 阈值无效，局部补缝也不对症；但不能由三例外推全天角 prompt leakage。
2. **把近 TES 的 Cu/Nb/Mu-metal 视为一个共同的高面密度转换与活化核心，而不是逐件孤立优化。** 延迟本底在冻结选择后有 73.70% 来自铜、19.73% 来自 Nb；Cu-61/62/64 合计占 73.76%。单独削某个 Cu 件时，瞬发 pair host 会迁移到剩余 Ag proxy、Mu-metal 或其他 Cu/Nb。
3. **工程首选是简单的低面密度冷端：** 盘径只缩到真实服务包络外，MXC 铜盘先试 3 mm、50 mK can bottom 先试 1 mm、非承载 Cu support 减薄、mixing-chamber Cu puck 减小；所有热接口、安装 boss、光学窗口和线束通道冻结。Nb 减薄必须独立成支线，先做 1 mm 工程候选，0.5 mm 只作为应力测试，不可绕过磁场 FEM、过渡温度场冷与冷态噪声验证。
4. **外部主屏蔽只保留两个后续旋钮：** 若分母完整的 gamma 角分布确认一个稳定象限，可在常温/外部 BGO 做方向化加厚；或在冷端减径后研究让同厚 BGO 更紧凑地靠近探测器。当前只有三个漏事件，不能据此直接冻结象限 sector。
5. **达到 `3e-5` 必须同时压瞬发和延迟。** 条件于候选仍保持冻结信号 `S20=1490.802`（Aeff 13.62852 cm2）且“当前 prompt”仍使用既有 27807.088 counts 标量，LC2 的“均匀活度质量代理”要求 prompt 至少降低 77.2%；事件坐标切除代理即使令 prompt 为零，delayed 仍需再降 4.53%。这是算术预算而非已展示性能；候选尚无 focused-signal 或 common-response 闭环，所以只能晋级到定向验证，不能宣称已经达标。

## 同一口径的起点与目标

|情景|Aeff (cm2)|prompt (cps)|delayed (cps)|20 天任务 F3|
|---|---:|---:|---:|---:|
|S3d-O8 common-response 基线|15.04170|0.0338429|0.0544798|`6.9238e-5`|
|冻结像素中心 + deepest layer <= L3|13.62852|0.0169215|0.0232057|`5.1490e-5`|

冻结情景的 20 天信号是 1490.802 counts，因此 `F3 <= 3e-5` 对应的中央背景门为 22224.913 counts。旧的 `0.0136124 cps` 只是保持原本时间形状时的近似换算；一旦 prompt/delayed 构成改变，应以 20 天逐时间折叠为准。

## 瞬发本底：从哪里来，为什么没被挡住

### 事件级结论

测量 W2、veto 前共有 261 个事件，258 个被现有主动层拒绝。三个漏过 veto 的事件全部是入射 gamma，且精确 BGO 与 plastic 能量均为 0：

|事件|初能 (MeV)|InstrumentFrame 入射方向|实穿 BGO|首次关键转换|冻结选择后|
|---|---:|---|---:|---|---|
|3883|4.148|底部斜入射|3.148 cm|Nb 内磁屏蔽筒 pair|被像素半径门拒绝|
|19932|5.769|`+x/+z` 斜侧入射|5.290 cm|DR mixing-chamber Cu pair|唯一保留 prompt|
|8081|6.346|`+x/-y` 斜侧入射|4.044 cm|Nb 内磁屏蔽筒 pair|被 Step05 拒绝|

三条射线都实穿 plastic、BPE、Al 机械壳和 BGO；对这三例，路径未经过已建模的矩形光学开口、搭接缝或 relief。证据只能说明主动材料中**没有能量沉积**，并非阈值不够低。随后在内侧被动 Cu/Nb 发生 `gamma -> e+e- -> annihilation -> 511 gamma -> TES`，这才形成 W2。

在 261 个 **W2 veto 前样本**中，252 个有完整的 pair/annihilation/TES ancestry，另 3 个有正电子湮没 ancestry、6 个因 shower/track 前代缺口未闭合。这说明 veto 前 W2 的主拓扑是“高能粒子先制造正电子，单个 511 keV gamma 再被 TES 全吸收”；最终主动 veto 漏过机制仍只有上述三例，不足以给出可靠的全天角方向预算。

### 对主屏蔽的含义

按 NIST XCOM 类型的单相互作用衰减估算，5.77 MeV gamma 在 BGO 中的线性衰减系数约为 `0.276 cm-1`，平均自由程约 3.62 cm。现有 5.29 cm 斜射光程仍有约 23% 的无相互作用概率；额外 2 cm 只把这部分降低约 42%，要单靠 BGO 把它降低 77% 需要约 5.4 cm 额外光程。这只是衰减代理，不含二次粒子和 veto response，但足以说明“全周再加 1--2 cm”难以独自承担目标。

现有 4/3 cm BGO 已处在 XL-Calibur 飞行工程采用的 4 cm 侧壁、3 cm 顶/底厚度族。XL-Calibur 的设计与 Monte-Carlo 研究发现：继续把阈值降至 100 keV 以下作用有限，`>10 MeV` albedo gamma/neutron 是其漏过主动层的主要成分，额外被动 W 没有显著收益；飞行测到了 `<100 keV` veto 阈值和约 0.5 Hz 的 20--40 keV 背景。其整套 BGO 约 42 kg。这里的能谱与 S3d-O8 的 4--6 MeV 漏事例不同，只把该经验作为定性机制和工程边界，不作定量外推。[XL-Calibur shield paper](https://arxiv.org/abs/2212.04139)，[NASA XL-Calibur engineering paper](https://ntrs.nasa.gov/api/citations/20205009210/downloads/Okajima_XL-Calibur_paper.pdf)

因此主屏蔽优化顺序应为：先降低内侧 pair target grammage；再用分母完整的方向统计决定是否做外部常温 BGO sector；最后才评估全周加厚。不要增加单独的 W/Pb 高 Z 内衬，因为它可能成为新的 pair/activation 靶。INTEGRAL/SPI 的工程经验同样指出，BGO 质量过高会增加中子次级；宇宙线在被动航天器材料中的相互作用或活化可产生 511 keV photon，并形成未被 ACS 拒绝的 shield-leakage 分量。[ESA SPI AO20 Observer's Manual](https://integral.esac.esa.int/AO20/SPI_ObsMan.pdf)，[ESA SPI AO5 Observer's Manual](https://integral.esac.esa.int/AO5/AO5_SPI_om.pdf)，[NIST XCOM](https://www.nist.gov/pml/xcom-photon-cross-sections-database)

## 活化本底：由什么粒子、什么材料产生

冻结选择后的 delayed 样本为 135 行、`0.0232057 cps`；由 retained event weights 的平方和得到的 MC 1-sigma proxy 为 `0.0066873 cps`，加权有效样本量只有 12.04。它不是物理系统误差或置信区间；冻结 prompt 更只有一个加权事件。因此以下是来源排序，不是高精度材料常数或候选性能预测。

### 入射粒子族

|生产入射族|选后 delayed (cps)|占比|选后行数|
|---|---:|---:|---:|
|neutron|0.0111431|48.02%|8|
|proton|0.00915046|39.43%|3|
|positron|0.00151696|6.54%|101|
|alpha|0.00112166|4.83%|1|
|其余 gamma/e-/mu-|0.00027349|1.18%|22|

这说明优化对象首先是由中子和质子驱动、且与 TES 强耦合的近端活化，而不是按原始 Bq 大小简单排序。完整 inventory 中 Cu 活化生产约由 proton 贡献一半、neutron 贡献约四分之一到三成、alpha 贡献约两成；经过 detector selection 后，少量高权重 neutron/proton 路径占据预算。

### 材料、核素和位置

|分组|选后 delayed (cps)|占比|
|---|---:|---:|
|Copper|0.0171029|73.70%|
|Nb|0.00457822|19.73%|
|Mu-metal|0.00150955|6.51%|

Cu-64、Cu-61、Cu-62 分别贡献 0.00839866、0.00492630、0.00379294 cps，合计 73.76%。主要位置为 MXC 50 mK 铜盘 32.56%、Nb 内筒 19.73%、L5-ZM Cu support 13.14%、50 mK can bottom 11.11%、Mu-metal 外筒 6.51%、L0 Cu disk 6.04%、L2-ZP support 6.00%。其中若干排名由单个高权重事件决定，因此不能把一个 support 的 13% 直接外推成确定收益。

物理解释是双重的：这些件既接受 n/p/alpha 产生 Cu/Nb/Co 等放射性母核，又离 TES 很近，衰变出的正电子或 gamma 容易形成一个被 TES 全吸收而没有外 veto 的 511 keV photon。因此减少**近端质量与固体角耦合**比只减少远端总活度更有价值。

## 候选路线与已经得到的筛选结果

### LC1/LC2 只做简单尺寸旋钮

- `LC1_Cu`：MXC 盘半径 15 -> 12 cm（厚 6 mm 不变）；can bottom 2 -> 1 mm；DR Cu 半径 2.2 -> 1.8 cm、厚 18 -> 6 mm；L0 3.5 -> 1.5 mm；20 个 Cu open-ring panel 3 -> 1.5 mm。
- `LC1_CuNb`：在 LC1_Cu 上把 Nb 筒/后盖 2 -> 0.5 mm。该 0.5 mm 只用于应力测试，不是工程推荐厚度。
- `LC2_CuNb_MXC3mm`：在 LC1_CuNb 上把 MXC 盘 6 -> 3 mm，保留下表面和接口位置。

只计上述命名 Cu/Nb 子集，质量由当前 5.917 kg 降至 LC1_Cu 3.632 kg、LC1_CuNb 3.308 kg、LC2 2.092 kg；这些不是整机质量。

### 机制证伪比“漂亮点估计”更重要

对唯一冻结 prompt root 19932 做 8192 个配对定向 gamma：baseline、LC1_Cu、LC1_CuNb 的 raw TES W2+active-veto50 幸存数为 `1/2/1`（raw W2 为 `3/4/3`）。这不是冻结空间/层深/Step05/common-response rate。DR Cu hit 从 405 降到 53/43，说明减材确实改变了局部相互作用；但 pair host 迁移到剩余 Ag-sinter proxy、Mu-metal 或 MXC plate。计数太低，**没有 prompt 降低证据**。

延迟端目前只有两种 unchanged-transport 代理：

|LC2 代理|delayed 20 天 counts|保留当前 prompt 时 F3|假设 prompt=0 时 F3|目标判断|
|---|---:|---:|---:|---|
|事件坐标切除|23280.1|`4.5484e-5`|`3.0704e-5`|延迟仍需再降 4.53%|
|均匀活度质量缩放|15885.5|`4.2063e-5`|`2.5363e-5`|prompt 必须至少降 77.2%|

两者都不是物理上下界或置信区间：前者将被切除历史源点贡献置零，后者假定活化均匀且耦合不变；均未重跑 BUILDUP、inventory、delayed transport 和 response。表中 F3 还条件于候选 focused signal 保持冻结的 `S20=1490.802`，并把 27807.088 prompt counts 原样带入。尤其 LC2 坐标代理的改善完全由一个高权重 `n -> Cu-62` 事件控制。

## 建议的工程执行顺序

1. **真实 BOM/CAD 对账。** 先确认近 TES 的实际 Cu、Nb、Mu-metal、Ag 质量、密度、孔洞、热带、紧固件和线束。当前 `DR_MXC_Sinter_HEX_AgProxy` 使用 5 g/cm3 的实体代理；银烧结的热性能取决于比表面积、孔隙率、颗粒颈联结和基板接触。因此在未用实物 BOM、有效密度和换热/热化模型复核前，不能把几何体积线性削除并假定热性能不变。[Cryogenics silver-sinter study](https://www.sciencedirect.com/science/article/pii/S001122751930061X)
2. **Cu-only 工程候选。** 在保留热接口/安装 boss/服务包络的条件下，先冻结 3 mm MXC 盘、1 mm can bottom、薄 Cu support 和小 DR puck；完成稳态/瞬态热阻、温度均匀性、首阶模态、发射/着陆载荷与装配检查。2016 年 Athena X-IFU FPA 初步方案也把 50 mK 热隔离、机械支承和多种屏蔽作为联合约束，而非单纯减重；它并不为本项目的 3/1 mm 尺寸背书。[NASA Athena X-IFU FPA](https://ntrs.nasa.gov/citations/20170005823)
3. **Nb 独立分支。** 先比较 2 mm、1 mm，再把 0.5 mm 留作敏感性极限。门槛包括静/动态磁 FEM、几何连续性、开口与接缝、Nb 超导材料参数、过 Tc 场冷与磁通俘获、TES/SQUID 冷态场图和噪声；高磁导层还需实测低温磁导率。NASA 地面 TES 平台与 Bergen 空间导向原型均采用 mu-metal/低温高磁导材料/Nb 的多层体系，性能受几何、接缝和场冷影响，不能按 Nb 质量线性推断。[NASA TES shielding](https://ntrs.nasa.gov/citations/20190027013)，[Bergen et al. validation](https://ris.utwente.nl/ws/files/42063245/design.pdf)
4. **prompt 定向验证。** 用分母完整的 4--10 MeV gamma 角/能量 cassette 和 corrected-keV broadband gamma 验证两件事：低面密度核心能否阻止 pair-host 迁移；是否存在可重复的外部入射象限。只有后者成立才做常温 BGO sector 或紧凑化主屏蔽。
5. **activation 定向闭环。** 对 n/p/alpha 增加有效统计量，重新执行 BUILDUP -> day-15 inventory -> delayed -> common response。全局加权有效样本量 30 只能作为来源排序/路径诊断的最低门，且任何 >10% 的路径不能只靠一个事件；它绝不是最终 promotion 的精度门。
6. **最终任务门。** 必须用候选实测的 focused signal 重算 `B20_max=(S20/10)^2`，而不是固定沿用 22224.913。中央预算可先取 `B20 <= 0.96 B20_max`，再按预先注册的加权 Poisson/compound-MC 区间要求一侧统计上界 `<= B20_max`；prompt 候选/当前比值的一侧 95% 上界建议小于 0.20。4% 余量非常苛刻：若粗略使用 `sigma/B=1/sqrt(Neff)`，单为满足一侧 95% 门就需 `Neff` 约 1558，而不是 30。实际生产统计量应由选定区间算法和各独立链权重反推。Aeff 可另设工程下限，但改变 Aeff 时必须同步改变背景门。

## 暂不晋级的方向

- mK BGO、读出铜或复杂局部 guard：不在本路线内。
- 降 veto 阈值：三个关键漏事件在主动层精确为零能量，无法修复。
- 全周 BGO 盲目增厚：质量大、单独衰减不足，还可能增加中子次级与自身活化。
- 内加 W/Pb 或把低能 graded-Z 经验直接搬到 4--6 MeV：可能制造新的 pair/511 靶。
- 大幅增加 BPE：当前 20 mm BPE 对 Cu-61/62/64 只显示约 10--16% 的中子电流代理改善，且未闭合绕行、级联、活化和 detector coupling；XL-Calibur 也发现额外聚乙烯的收益受质量约束。仅在中子方向与净活化收益闭合后再研究局部 H/B 屏蔽。
- 直接削 Mu-metal 或随意给 Nb 开槽：磁屏蔽功能和制造接缝风险高于现有统计证据。

## 可复算产物与边界

- [可执行分析 notebook](analysis/s3d_o8_source_driven_optimization.ipynb)
- [紧凑来源与任务门汇总](data/source_driven_optimization_summary.json)
- [prompt W2 261 事件紧凑表](data/prompt_w2_event_summary.csv)
- [三个 prompt 漏事件射线路径](data/prompt_veto_leak_ray_paths.csv)
- [frozen delayed 135 行来源坐标](data/frozen_delayed_source_coordinates.csv)
- [来源预算与候选任务门图](figures/source_budget_and_candidate_gate.png)
- [分析一致性验证](data/source_driven_analysis_validation.json)
- [候选几何静态验证](data/lc1_geometry_validation.json)

紧凑分析验证为 `PASS_SOURCE_DRIVEN_ANALYSIS_VALIDATION`。它从 durable delayed CSV 重新聚合 rate/MC proxy/Neff，并用 family×ZA×time 输入重新折叠 frozen delayed 20 天 counts，同时检查选定 summary 常数、prompt CSV 行数、notebook 状态和静态几何 delta；候选 LC1/LC2 的 retention proxy 仍不是独立物理重模拟。该验证不替代完整的新输运、活化、热、结构或磁验证。
