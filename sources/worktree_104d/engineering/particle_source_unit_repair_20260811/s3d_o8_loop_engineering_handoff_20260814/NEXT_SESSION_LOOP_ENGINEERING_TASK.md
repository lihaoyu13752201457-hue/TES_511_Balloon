# 下一 session 任务书：S3d-O8 LOOP ENGINEERING

## 0. 任务目标

你是独立第三方，不是上一 session 结论的执行者。先读：

1. [`HANDOFF_A_PROJECT_MAINLINE.md`](HANDOFF_A_PROJECT_MAINLINE.md)；
2. [`HANDOFF_B_THIRD_PARTY_PHYSICS_REVIEW.md`](HANDOFF_B_THIRD_PARTY_PHYSICS_REVIEW.md)；
3. 然后执行本任务书。

你的目标是以直观的粒子—材料—几何物理图像审阅 S3d-O8 本底，反复做 **LOOP = Localize -> Origin -> Optimize -> Prove/Falsify**，最后给出一个单一、最优且工程上尽量简单的优化方案。

任务门为 20 天 central：

```text
F3 = 1e-4 × 3 × sqrt(B20) / S20 <= 3e-5 photon cm^-2 s^-1
B20_max = (S20 / 10)^2
```

候选必须用自己的 focused-signal `S20` 重算 `B20_max`，不能固定沿用旧候选预算。

## 1. 硬约束

### 禁止

- 新增任何反符合探测器、局部 active guard 或新读出通道；
- mK 闪烁体、把 Cu 读出化、复杂微加工；
- 在 TES 附近新增 W/Pb 等高 Z 被动 pair target；
- 用无谓哈希、文件清单、脚手架或大规模盲跑代替物理热点解释；
- 在机制未闭合前做全八族 full-chain；
- 把上一 session 的热点、LC1/LC2 尺寸或“近端低 grammage”直接当正确答案。

### 允许的工程旋钮

- 现有 BGO/BPE/plastic 的厚度、距离、覆盖、质量重新分配，但不增加读出通道；
- Cu 冷盘、罐底、支撑、DR 部件的厚度、半径、简单孔/辐条/环形承载、位置与可行材料替代；
- Nb/Mu-metal 的厚度、间距和闭合拓扑，但磁性能是硬门；
- 把不可避免的质量从 TES 大固体角区域移到低耦合区域；
- 简单、可加工、可热/磁/结构验证的几何拓扑。

## 2. 每轮 LOOP 的必需输出

### L — Localize：本底在哪里

分别对 prompt 和 delayed 建立空间热点图，且每张图都带物理分母：

- prompt：incident gamma 的能量、方向、穿过的材料/光程、first pair、annihilation、TES hit、active energy；
- delayed：production family、source material、parent isotope、source position、production Bq、selected W2/Bq coupling；
- 明确区分 pre-veto、veto survivor、Step05 final 和冻结选择；
- 所有单事件高权重热点显式标记，禁止用平滑图掩盖。

每轮必须先用一句话回答：**当前最大、最可信的空间热点是哪一个，为什么？**

### O — Origin：本底如何产生

对最可信热点闭合两条因果链：

```text
prompt:
incident particle/E/direction
  -> material grammage
  -> first key interaction / pair creator
  -> secondary / annihilation
  -> TES deposit
  -> why no active veto

delayed:
incident n/p/alpha E/direction
  -> production material and reaction/product
  -> parent isotope and day-15 activity
  -> source position
  -> decay/transport
  -> selected W2 and W2/Bq coupling
```

无法由当前数据回答的环节必须标为 unknown，并设计最小补证，不准用猜测填空。

### O — Optimize：一次只提出一个可证伪的简单拓扑

每个候选必须明确：

- 精确部件、尺寸、材料、位置与质量变化；
- 它切断哪条 prompt 或 delayed 物理路径；
- pair/activation host 最可能迁到哪里；
- 保留的热、磁、结构、光路和装配功能；
- 一条能直接淘汰它的 falsifier。

每轮只比较少数同类方案，不要把十几个旋钮同时改掉。优先寻找同时压低 prompt pair opacity 与 delayed activation/coupling 的共同热点。

### P — Prove/Falsify：按最小证据阶梯验证

按顺序进行，上一层失败就停止候选：

1. 现有 catalog、lineage、几何射线和解析 grammage/solid-angle；
2. 少量配对 focused signal 与定向 gamma/n/p 机制测试；
3. 候选有明确机制收益后才跑 corrected broadband prompt；
4. 只有最终候选才跑 BUILDUP -> inventory -> delayed -> common response；
5. 最后做 focused signal 与 20 天 mission F3 闭环。

每轮结束必须给候选一个判决：`KEEP`、`MODIFY` 或 `KILL`，并说明哪条物理证据触发该判决。

## 3. 首轮必须独立复核的问题

1. 重新用真实几何切片追踪三条 prompt leakage；验证坐标系、active-volume scoring、光程、first pair 与 annihilation volume。
2. 用完整 incident gamma 分母建立 `E × direction × active grammage` leakage map；不能以 3 个 survivor 当角分布。
3. 分别计算内部 Cu、Nb、Ag proxy、Mu-metal、W 的 `pair opacity × TES solid angle × no-veto probability` 排序，并检查 Mass_model_511 是否支持同一规律。
4. 对 delayed 把 production Bq 与 W2/Bq coupling 分开，重点复核 MXC plate、Nb inner、can bottom；L5/L0/L2/Mu-metal 的单事件热点先判为 unresolved。
5. 追溯生成关键 Cu-61/62/64、Y-85、Nb-89/90、Co-54 的初级 n/p/alpha 能谱、方向和反应道；当前 lineage 不足时做最小 BUILDUP 定向补样。
6. 按真实 BOM/CAD 修正 DR Cu、Ag sinter、Cu plate、Nb/Mu 的质量、孔隙、孔洞、线束和服务包络。

## 4. 必须生成的直观图

1. Mass_model_511 与 S3d-O8 的同视角截面图，标出 active shield、TES、Cu/Nb/Mu/Ag/W；
2. prompt 的三视图射线图和 `E × direction` 分母/漏率图；
3. delayed 轴向-径向或 3D bubble plot：颜色=材料，形状=production family，大小=selected rate，描边=单事件高权重；
4. `family -> material -> isotope -> volume -> W2` flow，并并列 production Bq 与 W2/Bq；
5. 最终候选 before/after 截面及 signal、prompt、delayed、B20、F3 预算图。

图必须帮助判断物理，不要再画一张流程框图充当热点分析。

## 5. 统计和晋级门

- prompt 当前只有 3 个 veto leak，冻结后 1 个；只可验证已观察机制，不能冻结方向率。
- frozen delayed 的 `Neff=12.04`，且 12 条高权重记录贡献 92.28%；`Neff>=30` 只能作为来源排序的最低门，不是最终精度门。
- 任一占比超过 10% 的路径若仍由单个加权事件控制，不得晋级。
- LC-like 候选若使用 frozen signal 预算，必须实证 prompt 至少约 77% 的抑制；不能把算术要求写成已有性能。
- 候选必须保持可接受的 Aeff；任何 Aeff 变化都要用新 `S20` 重算背景门。
- 最终至少报告 central 和预注册的一侧保守统计界；系统学与 MC counting 必须分开。

## 6. 工程淘汰条件

出现以下任一项，候选原则上 `KILL`：

- prompt pair host 只是迁到另一个高 TES 固体角材料；
- 收益由一个历史高权重 event 决定；
- focused signal 损失使重算后的 F3 预算反而恶化；
- 新增或暴露新的近端高 Z pair/activation target；
- Nb/Mu 改动不能保持磁闭合，或场冷/磁噪声门失败；
- 冷盘/支撑改动破坏热接口、温度均匀性、模态/强度或装配；
- 中子吸收层的 capture gamma/增加质量抵消活化收益。

## 7. 资源纪律

- 分析任务可并发，但 transport 串行；先检查内存和磁盘余量。
- 原始 SIM 用流式读取，只抽取目标事件；不要复制 GB 级缓存。
- 每次 transport 都用新 seed、corrected-keV source、匹配 geometry header 和独立输出目录。
- full eight-family 只允许给最终候选，不为淘汰候选消耗资源。

## 8. 最终交付

新 session 必须交付：

1. 经独立复核的 prompt 与 delayed 物理热点图和因果链；
2. 每轮 LOOP 的 `KEEP/MODIFY/KILL` 简表；
3. **一个**单一最优方案：精确几何、材料、质量、预期作用链、host-migration 风险及热/磁/结构门；
4. 与 baseline 同口径的 Aeff、prompt、delayed、B20、F3；
5. 最终状态只能是：`PHYSICS PROMOTED`、`ENGINEERING-CONDITIONAL OPTIMUM` 或 `NO SOLUTION UNDER CONSTRAINTS`。

如果证据尚不足，允许给出 `ENGINEERING-CONDITIONAL OPTIMUM`，但不允许用一长串平行建议逃避选择。

