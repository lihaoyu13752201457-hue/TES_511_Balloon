# S3d–O8 综合物理仲裁与可实施优化方案

日期：2026-08-14  
角色：第三个独立综合审阅 session  
判决状态：**ENGINEERING-CONDITIONAL OPTIMUM — NOT PHYSICS PROMOTED**

## 0. 结论先行

### 一级推荐：`PORT-20`

**INFERENCE — 当前唯一一级推荐**：保留 S3d–O8 的现有主动屏蔽与冷芯拓扑，只修正 focused 光路与外包络的几何冲突：

1. **BPE：REDISTRIBUTE，而非整圈 REMOVE/THIN/THICKEN。**
   - 侧 BPE 其余区域保持 `20 mm`；上下盖保持 `20 mm`。
   - 仅在 InstrumentFrame 负 x focused sightline 上切出 `3.796 × 3.796 cm²` 方口，中心 `(y,z)=(0,-5.2 cm)`，与既有 BGO/Al/Be 窗共注册。
2. **Plastic：保持现有 `10 mm`，但在同一 sightline 切同尺寸方口。**
   - 不新增读出、不新增 guard；原 plastic 通道和其余覆盖保持。
3. **BGO：完全保持。**
   - side `40 mm`、bottom `30 mm`、top `10 mm`；不靠近、不减薄、不增厚、不做质量重分配。
4. **MXC plate、50 mK can bottom、DR mixing Cu、L0–L5 Cu supports：完全保持现有简单拓扑和厚度。**
5. **Nb/Mu：闭合圆筒与 back cap 全部保持；任何改变先过磁学硬门，本候选不领取磁屏蔽减材 credit。**
6. **材料替代：一级候选中没有。**

模型净减重为 `0.042251 kg`：BPE `0.027399 kg`，plastic `0.014852 kg`。如果真实 flight CAD 已有该口，则实际硬件净变化为 `0`，需要修正的是 proxy geometry 与 signal authority。

### 为什么不是 KEEP-20 或 REMOVE

- **FACT**：现行卡中的 37,194 条 focused ray 全部穿过实体 BPE 与 plastic；官方 stage04 却在 Be window 之后注入，所以官方 `Aeff=15.04170 cm²` 与 `S20=1645.388` 没有计入这两层的信号代价。
- **FACT**：BPE 的 Cu-61/62/64 boundary-current index 约 `0.885/0.842/0.897`，只支持 `<=100 MeV` 直接 natural-Cu neutron current 的小幅机制收益，不是 0/20 total-background、selected W2 或 F3。
- **UNKNOWN**：当前没有 matched 0/20 的 `P20+D20`，也没有 candidate-specific full-envelope `S20`。
- **INFERENCE**：整圈 KEEP-20 保留一个已知的 signal-denominator 错配；整圈 REMOVE 又放弃当前唯一已展示的 BPE 机制收益。PORT-20 同时消除已知 focused-ray 交叠并保留 `99.9185%` BPE 质量，是更强的可证伪工程先验。

### 这不是达标方案

- **FACT**：官方 mission 基线 `S20=1645.387753`、`P20=55398.979434`、`D20=88804.862652`，故 `B20=144203.842086`、`B20,max=27073.008579`、central `F3=6.92375e-5`。固定信号时需把总背景降低 `81.2259%`。
- **FACT**：即使 prompt 理想归零，delayed 仍需降低 `69.514%`；即使不现实地消除全部 n-family delayed，p/alpha/other 仍约 `50524.4 counts > 27073.0`。
- **FACT**：PORT-20 没有已展示的 prompt 或 delayed 大幅降低机制；三条已知 prompt gamma leak 都不经过该 focused 口。
- **UNKNOWN**：PORT-20 自身的 `S20/P20/D20` 尚未生成。

因此本报告只把 PORT-20 判为 **ENGINEERING-CONDITIONAL OPTIMUM**：它是当前证据下最干净、最少假设、最容易证伪的参考配置，不是已经满足 `F3<=3e-5` 的物理方案。

---

## 1. 证据标签

|标签|含义|
|---|---|
|**FACT**|可由权威卡、CSV、代码或 raw SIM 独立复算。|
|**INFERENCE**|由多项 FACT 支持的工程/物理判断，但不是直接测量。|
|**HYPOTHESIS**|有机制动机、尚无候选 transport 或工程验证。|
|**UNKNOWN**|现有资料不能决定，必须以指定测量或模拟闭合。|

关键数字及来源的逐条审计见 [evidence_ledger.csv](evidence_ledger.csv)。

---

## 2. 首轮“冲突与共同点”审计

### 2.1 可以合并的结论

|状态|共同结论|仲裁用途|
|---|---|---|
|**FACT**|现行侧 BPE 是 `r=27..29 cm` 的完整 20 mm 环壳，侧 plastic 是 `r=29..30 cm` 的完整 10 mm active 环壳；两者都没有 focused window。|确认 card-as-written 的真实光路交叠。|
|**FACT**|现有 BGO/Al 窗是 `3.796 × 3.796 cm²`，中心 `(y,z)=(0,-5.2 cm)`。|定义共注册外包络 port。|
|**FACT**|37,194/37,194 sampled focused rays 穿 BPE/plastic，又全部落在既有 BGO/Al 窗内。|排除“多数 ray 本来走已有 relief”的解释。|
|**FACT**|官方 stage04 是 post-Be-window detector acceptance，不是 full-envelope transmission。|禁止把官方 S20 当 BPE/plastic 实测。|
|**FACT**|BPE current index 只是小幅 direct-n mechanism evidence。|可保留 BPE 作为先验，但不能领取 mission credit。|
|**FACT**|BPE proxy 没闭合 `>100 MeV` cascade、bypass、p/alpha 内生 secondary-n、exact-position coupling。|最终门必须追踪完整生产链。|
|**FACT**|prompt 三条漏事件是 active zero-deposit 后在内部 Cu/Nb PAIR，再由 ANNI 511 到 TES。|保留 active shield；警惕 cold-core host substitution。|
|**FACT**|delayed 由 `n/p/alpha→Cu/Nb/Mu→核素→exact position→W2` 共同决定，Bq 不能单独排序。|禁止把 activity 或 mass 线性当 detector rate。|
|**FACT**|当前统计稀疏：prompt veto survivor 只有 3，frozen delayed `Neff=12.04` 且 top12 占 `92.28%`。|不冻结方向 sector，不用单事件决定减材。|
|**FACT**|没有任何候选自身的 full-envelope S20 与完整 P20+D20。|两份 handoff 都不能 PHYSICS PROMOTE。|

### 2.2 明确冲突及决定它的缺失物理量

|冲突|LOOP handoff|BPE handoff|仲裁|决定性缺口|
|---|---|---|---|---|
|20 mm BPE 的默认动作|baseline+20 mm 是唯一未证伪 optimum|REMOVE 是 analytic prior|两者都不是一级结论；改为 PORT-20|flight CAD/BOM、candidate full-envelope S20、matched 0/20 total B|
|`0.83069` 的含义|未作为主信号实测|早期 REPORT 曾误称实测损失，最终 handoff 已纠正|**早期表述作废**；只可称 2 cm 法向窄束无碰撞 proxy|真实散射回收、plastic veto、完整包络|
|BPE 的 delayed 收益|以 20 mm 为最安全未证伪基线|认为收益只属小幅机制|合并为“保留机制、不给性能 credit”|matched production Bq × exact-position coupling|
|冷芯减材|多个 Cu/Nb/Mu proxy 均不足或被约束|BPE 审计不直接决定|一级配置冻结冷芯|prompt host migration、低 Neff、热/磁/结构合格性|

**INFERENCE — 仲裁原则**：分歧由不同、缺失的分母造成，而不是两个 session 的结论票数。PORT-20 是新的一阶支配候选：它保留 KEEP-20 唯一被支持的机制，又移除 REMOVE 唯一可靠的 signal 动机所指向的局部材料。

**UNKNOWN**：真实 flight 是否已存在未进入 proxy card 的 BPE/plastic port。若存在，当前任务首先是修 authority；若不存在，PORT-20 必须过 light-tight、plastic 光收集、机械支撑、环境背景泄漏与指向公差门。

---

## 3. 共同物理图

![S3d-O8 prompt、BPE neutron、inner activation/coupling 与 focused signal 的统一截面](figures/unified_physics_cross_section.png)

可编辑矢量源：[unified_physics_cross_section.svg](figures/unified_physics_cross_section.svg)。

图中四条链的证据状态：

1. **FACT — focused signal**：sampled ray bank 最大离轴角 `0.459802°`；在最外 `r=30 cm` 处 footprint 为 `y=-1.34826..1.34390 cm`、`z=-6.48826..-3.88195 cm`，距 `±1.898 cm` 方口边界最小约 `5.50 mm`。
2. **FACT — prompt gamma**：三条 4.14829/5.76882/6.34594 MeV gamma 穿过非 relief 的 BGO/plastic，active raw deposit 均为 0；INIT 后第一个记录物理 IA 为 PAIR，TES ancestry 为 `ANNI←PAIR←INIT`。
3. **FACT — external-n/BPE**：100k incident-n diagnostic 中 34,031 首次接触外表面，22,988 到内表面；`>=39 MeV` conditional transmission 为 `85.55%`。
4. **FACT — inner activation**：full delayed 的 n/p/alpha family shares 为 `43.464/39.191/8.235%`；Cu-61/62/64 共占 selected delayed `64.241%`。
5. **UNKNOWN — coupling response**：port 对环境 gamma/n 的小固角泄漏，以及 BPE removal/retention 对内层 secondary-n birth、parent production 和 exact-position decay coupling 的净符号。

---

## 4. 独立数值与几何复核

### 4.1 两套 response 口径必须分开

|状态|选择口径|S20|P20|D20|B20|B20,max|central F3|
|---|---|---:|---:|---:|---:|---:|---:|
|**FACT**|官方 stage-06 mission|1645.387753|55398.979434|88804.862652|144203.842086|27073.008579|6.92375e-5|
|**FACT**|frozen pixel/L3 诊断|1490.802230|27807.088280|37662.902066|65469.990346|22224.912885|约 5.1490e-5|

**FACT**：两行使用不同 signal、prompt 和 delayed 选择，不能把一行的 S20 与另一行的 P/D 混算。  
**INFERENCE**：在 project governance 正式替换 mission policy 前，候选 promotion 默认沿用官方 policy；frozen policy 可作为单独诊断，但必须对候选的 S/P/D 全部一致重跑。  
**UNKNOWN**：frozen delayed 135-row CSV 的算术成立，但当前未找到冻结生成脚本与 UID→pixel-center authority；用 measured-hit centroid 重放得到 137 rows/0.0218755 cps，而非 135/0.0232057 cps。该差异必须在 promotion 前补证。

### 4.2 Focused geometry

|状态|对象|独立复核|
|---|---|---|
|**FACT**|BPE|侧壳 `r=27..29 cm, z=-24.5..46 cm`；上下实心盖 `r=0..29 cm`、各 20 mm；pre-relief 总质量 `33.6056166 kg`。|
|**FACT**|Plastic|侧壳 `r=29..30 cm, z=-26.5..48 cm`；上下盖各 10 mm；pre-relief 总质量 `20.0476494 kg`。|
|**FACT**|BGO|side 40 mm、bottom 30 mm、top 10 mm；BGO transport-density pre-relief 总质量约 `296.55 kg`。|
|**FACT**|Ray bank|37,194 条全部穿 BPE/plastic；BPE chord `2.000000..2.002611 cm`，plastic `1.000000..1.001176 cm`。|
|**FACT**|Injection|EventList local `x=-13.1 cm`；实际 Be window local `x=-20.35 cm`，故注入点在其下游 7.25 cm。|
|**FACT**|官方 Aeff|`20.08476 × 27855/37194 = 15.04170 cm²`；代码明确写为 post-Be scope。|
|**INFERENCE**|PORT-20|用既有 `±1.898 cm` 方口向外连续延伸，可避免给当前 sampled signal 增加 BPE/plastic interaction。|
|**UNKNOWN**|真实信号|scatter recovery、alignment tail、flight aperture 与 full-envelope selected S20。|

### 4.3 Prompt gamma chain

|状态|审计项|结果|
|---|---|---|
|**FACT**|Cutflow|261 pre-veto W2 rows → 258 reject / 3 survive → 2 Step05 → 1 frozen。|
|**FACT**|事件 3883|4.14829 MeV；plastic/BPE/Al/BGO/W chord `1.049/2.099/0.315/3.148/0.199 cm`；PAIR@Nb → ANNI@Mu；Step05 pass、frozen radius reject。|
|**FACT**|事件 19932|5.76882 MeV；chord `1.323/2.645/0.397/5.290/0 cm`；PAIR+ANNI@DR mixing Cu；唯一 frozen pass。|
|**FACT**|事件 8081|6.34594 MeV；chord `1.011/2.022/0.303/4.044/0 cm`；PAIR@Nb → ANNI@L0 Cu；Step05 reject，且到 L5。|
|**FACT**|Active deposit|六个 exact active volumes 的 raw CC deposit 逐体为 0；同 SIM 可记录远低于 trigger 的 BGO deposit，故不是 80 keV trigger 抹除。|
|**FACT**|Aperture alias|三条 ray 均不在已建模 BGO window、pump relief 或 NF2 relief；模型没有 seam。|
|**INFERENCE**|严谨表述|“no prior recorded physics interaction through non-relief modeled active material”，不是绝对 microscopic uncollided。|
|**UNKNOWN**|现实装配|真实 seam、搭接、未建模低能过程。|

**FACT**：三条已知 leak 都不经过 PORT-20 的 focused aperture，因此 PORT-20 不切断任何已知 prompt chain。  
**HYPOTHESIS**：移除该小固角的 BPE/plastic 会沿既有 BGO/Al/Be window 增加一部分环境 gamma/n 或 charged-secondary 入射。  
**UNKNOWN**：净 prompt 变化；没有 candidate broadband gamma transport。

### 4.4 BPE neutron chain

|状态|量|独立结果|不能代表什么|
|---|---|---|---|
|**FACT**|outer→inner unique primary|34031→22988，conditional 67.55%|全仪器 coverage 或 selected W2|
|**FACT**|`>=39 MeV`|10066→8611，85.55%|高能 cascade 屏蔽闭合|
|**FACT**|Cu-61 current index|0.884755±0.012707|0/20 D20 比|
|**FACT**|Cu-62 current index|0.842146±0.010264|mission F3|
|**FACT**|Cu-64 current index|0.896560±0.097060|显著 Cu-64 收益；区间兼容接近中性|
|**FACT**|fold scope|只含 `0<E<=100 MeV` natural-Cu channel current|>100 MeV、spallation 或 exact volume production|
|**FACT**|source scope|incident-n；crossing analyzer 只保留 neutron|p/alpha 内层 cascade secondary-n|

**FACT**：primary outer crossings 中 `18.128%` 高于 100 MeV，而 cross-section fold 在 100 MeV 以上置零。  
**FACT**：p/alpha→Cu-64 的审计 RP 中，分别有 115/118 与 74/77 由 secondary-neutron capture/inelastic 产生。  
**INFERENCE**：外层 BPE 可以影响部分外来低/中能 n，但对 GeV primary cascade 和已在内层出生的 secondary n 覆盖不足。  
**UNKNOWN**：secondary-n birth radius、是否曾穿 BPE、port 所在方向的 n illumination 分母。

### 4.5 Delayed production × coupling

#### Exact material 口径

|状态|Material|rows|observed W2 cps|share|day-15 Bq|supported W2/Bq|
|---|---|---:|---:|---:|---:|---:|
|**FACT**|Copper|373|0.0363761284|66.7700%|161.957683|2.65381e-4|
|**FACT**|Nb|25|0.00920149266|16.8897%|1.164130|9.44037e-3|
|**FACT**|MuMetal|20|0.00776545392|14.2538%|1.361424|6.21351e-3|
|**FACT**|SilverSinterProxy|1|0.00112165785|2.0589%|4.561510|2.25513e-4|
|**FACT**|CuNi|1|0.0000150194|0.0276%|1.726465|1.54843e-5|

**FACT**：权威 geometry 有 60 个 `.Material Copper` volumes。LOOP handoff 的 `112.251 Bq` “Copper”数来自名字前缀 bucket：它混入一条 CuNi，又漏掉多组真实 Copper inventory。该数只可称具名近芯 Cu screen，不可称 all-Copper。  
**FACT**：BGO `1031.944 Bq`、BPE `34.3729 Bq` 各有零 observed selected survivor。  
**UNKNOWN**：零 MC survivor 不等于物理 rate 为零，必须报告有限一侧上界。

#### Spatial/coupling sparsity

|状态|量|结果|
|---|---|---|
|**FACT**|full delayed|420 rows、0.0544797522 cps、event Neff 28.754|
|**FACT**|dominant parents|Cu-62/Cu-64/Cu-61 合计 64.2409%|
|**FACT**|largest volumes|MXC 30.7848%、Nb inner 14.3330%、Mu outer 14.2538%、L0 10.7370%、can bottom 7.3710%|
|**FACT**|position support|66 positions、position Neff 24.93；单个大组件的 position Neff 均 <8|
|**FACT**|frozen subset|135 rows、0.0232056740 cps、event Neff 12.0417、top12 92.28445%|
|**INFERENCE**|Nb/Mu coupling|近场 Nb/Mu 的 observed supported W2/Bq 较高，但不是可移植材料常数。|
|**UNKNOWN**|减材结果|生产会迁移，solid angle 与吸收会变，低 Neff 不能支撑线性外推。|

正确链路是：

\[
q_k=\frac{\sum RP_k}{\sum TT_{family}},\quad
A_k=q_k\times\text{day-15 evolution},\quad
\hat r_k=A_k\,\epsilon_{family,volume,ZA,position}.
\]

**FACT**：family TT 必须分别除；zero-RP TT 也必须保留。  
**FACT**：candidate comparison 的 coupling key 必须至少是 `family × exact material × volume × parent ZA × exact position`。  
**UNKNOWN**：PORT-20/W0 对 key-level production 与 coupling 的 matched 比值。

---

## 5. 候选决策矩阵

完整矩阵见 [decision_matrix.csv](decision_matrix.csv)。下表是仲裁摘要：

|候选|Prompt|Delayed|Signal|工程|统计/迁移|判决|
|---|---|---|---|---|---|---|
|full-panel KEEP-20|无已知改善|只有 direct-n 小幅先验|官方 S20 不含面板代价|基线简单|无 matched total B|不是一级；分母错配|
|REMOVE-0|符号未知|可能丢失 BPE 收益|若面板真实覆盖则恢复部分信号；plastic 仍在|减约 33.6 kg，需重做外壳|activation/capture 可内迁|只作 matched falsifier|
|THIN-10|符号未知|不能线性插值|可能部分恢复|结构需重验|无候选数据|只作灵敏度，不是同级方案|
|**PORT-20**|小固角泄漏未知；不切断三条已知 leak|保留几乎全部 BPE 先验|当前 sampled rays 全清空|仅 42.25 g，简单方口|cold-core host 不动|**一级 ENGINEERING-CONDITIONAL**|
|BPE thick/sector|capture 反作用未知|无方向分母|需保留 port|加质量|3 个 prompt leak 不足定 sector|淘汰|
|BGO/plastic 移动/加重|可能改善 veto，也可制造 pair secondary|高 activity、mass 大|易影响 Aeff|读出/载荷风险|零 survivor 非零 rate|保持现状|
|cold Cu 减材|host substitution 已展示|legal plate proxy 仅 10.22% D、Neff 5.58|散射未知|热/结构硬风险|低 Neff、迁移|一级冻结|
|Nb/Mu 减薄/重排|Nb→Cu/Mu/L0 host migration|高 coupling 但极稀疏|名义中性|磁学硬门|未闭合|一级冻结|

### 已物理/工程淘汰的路线

- **FACT**：理想删除所有 observed exact-Copper delayed rows 后的 residual delayed 仍约 `29552 counts > 27073 counts`，而 prompt 尚未计入；这只是过度乐观 ceiling。
- **FACT**：已知 Cu/Nb/Mu boxes 的 observed prompt-chain ideal ceiling 约 50%；`P20/2≈27699.5` 已高于官方总背景门，即使 delayed=0 也不够。
- **FACT**：legal MXC plate envelope 的 exact-position proxy 只覆盖 delayed `9078 counts`（10.22%）、Neff 5.58；不足以闭合 81.2% mission gap。
- **FACT**：全包 BGO 增厚候选需要数百 kg，已有 reach proxy 约 10.6% 且低 Neff，不接近所需耦合。
- **FACT**：近场 passive Cu shadow 需要约 2.31–3.14 cm 连续路径，实际几何余量不足，且 optimistic residual 仍超门。
- **PROHIBITED**：TES 近端 W/Pb、新 active detector/guard/readout、mK scintillator、读出 Cu 或复杂微加工。

---

## 6. 一级配置的精确定义

### 6.1 BPE / plastic / BGO

#### BPE side subtraction

- **INFERENCE — candidate geometry**：Boolean BRIK 半尺寸 `(14.5001, 1.898, 1.898) cm`。
- **INFERENCE — placement**：side-shell local placement `(-14.5, 0, -15.95) cm`；换算到 InstrumentFrame 后窗口绝对中心 `(y,z)=(0,-5.2 cm)`，只切负 x 壳面。
- **FACT — retained**：side shell 其余位置 `r=27..29 cm`；bottom/top caps 20 mm，全部 NF2 relief 保持。

#### Plastic side subtraction

- **INFERENCE — candidate geometry**：Boolean BRIK 半尺寸 `(15.0001, 1.898, 1.898) cm`。
- **INFERENCE — placement**：side-shell local placement `(-15.0, 0, -15.95) cm`；同一绝对窗口中心。
- **FACT — retained**：side shell 其余位置 `r=29..30 cm`、10 mm；上下盖及原 active channel/readout 保持。

#### BGO

- **FACT — retained**：side 40 mm、bottom 30 mm、top 10 mm、现有 3.796 cm 方口和所有 relief 原样保留。
- **INFERENCE**：不向内移动 BPE，不用 BGO 替换 BPE，不把 removed port mass 加到 BGO。

#### Port tolerance

- **FACT**：当前 ray bank 最小 sampled clearance 约 5.50 mm。
- **HYPOTHESIS — engineering guard**：经完整 optics/alignment tolerance stack 后仍要求最小几何 clearance `>=5.0 mm`；否则增大共注册口，而不是让材料侵入 focused cone。
- **UNKNOWN**：真实 pointing/alignment tail；37,194 sampled rays 不是公差完整证明。

### 6.2 Cold Cu：全部保持

|状态|组件|一级 topology / thickness|
|---|---|---|
|**FACT — retained**|MXC cold plate|PCON `r=0..15 cm`、`z=-0.3..+0.3 cm`，总厚 `6 mm`。|
|**FACT — retained**|50 mK can bottom|PCON `r=0..15.3 cm`、`z=-0.1..+0.1 cm`，总厚 `2 mm`，现有位置不变。|
|**FACT — retained**|DR mixing chamber Cu|PCON `r=0..2.2 cm`、`z=-0.9..+0.9 cm`，总厚 `18 mm`，现有位置不变。|
|**FACT — retained**|L0 support|实体 Cu 方盘 `4.4 × 4.4 cm²`、沿局部 x 厚 `3.5 mm`。|
|**FACT — retained**|L1–L5 supports|五层四边开口 Cu ring；每 panel 沿 x 厚 `3 mm`，横向 rail 厚 `3.5 mm`、长度 `3.46 cm`，原中心与层间距不变。|
|**FACT — retained**|其他必要 Cu|edge rods、cold fingers、clamps、热接口不变。|

**INFERENCE**：冻结不是说这些部件无背景，而是现有数据无法证明减材后 `prompt host migration + delayed production/coupling + thermal/structural` 的净收益。  
**HYPOTHESIS — later branch only**：只有非热接口、非磁功能、非主承载 Cu 在实物功能签字后才可进入 Al/低活化材料 A/B；不属于本一级候选。

### 6.3 Nb / Mu：全部保持并设置磁学硬门

|状态|组件|一级 topology|
|---|---|---|
|**FACT — retained**|Nb inner|闭合 2 mm cylinder：PCON axis `-3.85..+4.1 cm`、`r=4.0..4.2 cm`，现有 `Rotation 0 90 0`、中心与 back cap 不变。|
|**FACT — retained**|MuMetal outer|闭合 2 mm cylinder：axis `-4.35..+4.3 cm`、`r=4.25..4.45 cm`，现有 rotation、中心与 back cap 不变。|

未来任何减薄、开槽、远移或开口重排都必须先同时通过：

1. DC residual field at TES/SQUID；
2. AC attenuation 与扫描/姿态变化；
3. cool-through-`Tc` field 与 trapped flux；
4. seam/overlap/opening 的 3-D 磁模型；
5. TES/SQUID noise 与稳定性；
6. 冷缩、支撑和振动。

未满足任一项即 **NO-GO**，不得用 delayed proxy 抵消磁学失败。

### 6.4 质量与功能清单

|状态|变化|体积|质量|说明|
|---|---|---:|---:|---|
|**FACT**|BPE port|28.84138 cm³|-0.027399 kg|占 BPE pre-relief mass 约 0.0815%|
|**FACT**|Plastic port|14.41958 cm³|-0.014852 kg|占 plastic pre-relief mass 约 0.0741%|
|**FACT**|Cold Cu/Nb/Mu/BGO|0|0|全部冻结|
|**FACT**|模型合计|43.26096 cm³|-0.042251 kg|解析圆柱交集，不是方柱近似|
|**UNKNOWN**|flight-as-built|—|0 或 -0.042251 kg|若 flight 已有 port，则硬件 Δmass=0，模型需修正|

若结构要求把 27.4 g BPE 放回非 relief、非 sightline 区域，可以做质量守恒，但该回填不得领取额外 background credit，且必须保持同一个候选 ID/BOM。

### 6.5 预期打击的链与最可能反作用

|标签|对象|一级候选的真实作用|
|---|---|---|
|**FACT**|focused 511 signal|消除当前 proxy card 中 sampled focused rays 的 BPE/plastic chord；这是候选最确定的作用。|
|**INFERENCE**|external n→Cu-61/62/64|窗口外 20 mm BPE 继续提供已观察的 modest direct-n current reduction。|
|**FACT**|prompt gamma→PAIR@Cu/Nb→ANNI→TES|已知三条不经过 port；本候选没有展示抑制。|
|**FACT**|p/alpha→inner secondary n→Cu/Nb/Mu activation|外层 port/BPE 不能充分覆盖；本候选不领取收益。|
|**HYPOTHESIS**|最可能反作用|沿既有 BGO/Al/Be window 增加环境 gamma/n、小固角 charged-secondary；plastic veto coverage 在该口消失。|
|**HYPOTHESIS**|次要反作用|BPE capture/activation 减少与内层 Cu/Nb/Mu activation 增加之间发生 host migration。|
|**UNKNOWN**|净 F3|取决于 candidate own S20 与 matched P20+D20，方向不能从面积或 0.83069 推断。|

---

## 7. 最小证伪矩阵与数字门

机器可读版本见 [validation_gates.csv](validation_gates.csv)。运输必须串行；开始前再次检查 RAM/磁盘。本审阅开始时约有 7.4 GiB 可用内存、32 GiB 可用磁盘，磁盘已用 89%，因此禁止复制 GB 级 SIM。

### V0 — Flight CAD/BOM authority

- **目标**：确定真实 BPE/plastic 是否已有 port；冻结 material、density、thickness、support、alignment tolerance。
- **GO**：只有一个签字 authority，PORT-20 可制造，完整 tolerance stack 后 focused clearance `>=5.0 mm`。
- **NO-GO**：CAD/BOM 冲突、port 不能支撑/light-tight/装配，或必须侵入 5 mm clearance。

### V1 — Deterministic geometry navigator

- **范围**：仅 PORT-20，不跑 transport。
- **GO**：37,194/37,194 从 plastic 外侧回放时 BPE/plastic chord 均为 0；没有 overlap/void/Boolean alias；最小 clearance `>=5.0 mm`。
- **NO-GO**：任一 ray clipping、材料 membership 错误或 header 不指向 candidate setup。

### V2 — Candidate-specific full-envelope signal

最小三臂只为控制变量，不是三套同级方案：

1. `FULL-20`：现行 full-panel card reference；
2. `PORT-20`：一级候选；
3. `PORT-0`：同一 plastic port、整套 BPE=0 mm 的 matched falsifier。

全部使用同一 37,194 ray bank，从 plastic 外侧开始，输出 first interaction、scatter recovery、plastic/BGO deposit、selected W2。

- **HYPOTHESIS — pre-registered signal guard**：`L95(S_PORT20/S_PORT0) >= 0.98`。
- **GO**：报告绝对 `S20,PORT20`，随后只用它计算 `B20,max=(S20/10)^2`。
- **NO-GO**：复用 post-Be S20、unexpected plastic/BGO veto loss，或 lower bound `<0.98`。

### V3 — Small paired prompt falsifier

- **范围**：PORT-20 vs PORT-0；corrected gamma 已含 annihilation bump，禁止另加 mono-511。
- **记录**：完整 incident denominator、raw active deposit、first pair/ann host、TES ancestry、W2、response selection。
- **GO**：一侧 95% 上界 `P_PORT20/P_PORT0 <= 1.10`，且没有新稳定 aperture cell。
- **统计最低门**：post-veto prompt source-ranking effective survivors `>=30`，或精确加权区间已把上述 1.10 门判定；`Neff>=30` 仍不是最终精度证明。
- **NO-GO**：upper bound >1.10、first-pair host 向 Ag/Mu/MXC/其他 Cu 稳定增长、或任何 >10% pathway 仍由单事件控制。

### V4 — Matched activation/coupling screen

- **顺序**：先 n，再 p，再 alpha；分析可并发，transport 串行。
- **链路**：`primary → secondary-n birth radius/energy → BPE crossings → exact material/volume/ZA/position production → day-15 activity → selected W2 coupling`。
- **必须纳入**：Cu-61/62/64、Y-85、Nb-89/90、Co-54，以及 Al/Ni/SS/BGO/BPE 的新 host；family TT 独立，zero-RP TT 保留。
- **GO mechanism gate**：combined target activity 的 central `PORT20/PORT0 <=0.90` 且一侧 95% 上界 `<1.0`；任一 key isotope/host ratio 不得 `>1.20`。
- **统计门**：可能贡献 candidate D20 >10% 的 production path，history Neff `>=30`、最大单 history `<10%`；exact-position event 与 position Neff 均 `>=30`，任一 event/position `<10%`。零 survivor 用有限一侧 95% 上界，不得置零。
- **NO-GO**：>100 MeV 或 p/alpha ancestry 未记录、上界跨 1、key host 上升 >20%、或稀疏门失败。

### V5 — 决定 KEEP-outside-port 是否优于 REMOVE 的 matched 0/20 门

这里的 0/20 不再混入 focused signal panel penalty：两臂有相同 plastic port，唯一变量是窗口外 BPE `0` 或 `20 mm`。

\[
\boxed{
\left(\frac{B_{PORT20}}{B_{PORT0}}\right)^{U95}
<
\left[
\left(\frac{S_{PORT20}}{S_{PORT0}}\right)^{L95}
\right]^2
}
\]

- **GO**：上述不等式严格成立，且 `B=P+D` 的所有 source family 均被纳入，或缺失 family 有预注册保守上界。
- **NO-GO**：不等式失败；这时 PORT-20 一级候选被证伪，但不自动把 REMOVE 晋级，必须先审计失效链和工程 BOM。
- **FACT**：旧 `0.83069²=0.69005` 只是 full-panel 窄束 proxy 的解析阈值；一旦两臂共用 optical port，该 proxy 不再是正式判据。

为同时遵守“只给最终候选做 full eight-family”和“必须有 matched 0/20 total B”，PORT-0 只作为 PORT-20 的配对实验控制，不建立第二套 promotion package；完整源 header、normalization 与 response 审计只对 PORT-20 形成最终候选 authority。任何不能给 PORT-0 总 B 一侧保守界的 family 都会令 V5 保持 UNKNOWN，而不是被当成 0。

### V6 — 唯一 promotion 门

只在 V0–V5 通过后对 PORT-20 做完整 eight-family closure：

\[
B_{20,c}=P_{20,c}+D_{20,c},\qquad
B_{20,max,c}=\left(\frac{S_{20,c}}{10}\right)^2.
\]

同时满足才可 PHYSICS PROMOTE：

1. **central**：`B20,c <= (S20,c/10)^2`；
2. **central**：`F3,c <= 3e-5 photon cm^-2 s^-1`；
3. **conservative**：`P20,c^U95 + D20,c^U95 <= (S20,c^L95/10)^2`；
4. 所有 source/SIM header 指向唯一 candidate setup；
5. activation/source normalization、NUBASE ground state、per-family TT、M-sampling inventory 和 exact-position coupling 全部可审计；
6. 任一 >10% pathway 不由单事件控制；系统学与 MC counting interval 分开报告。

任一失败即 **NO-GO**。full-stat 结果覆盖所有解析 proxy 和小样本 screen。

---

## 8. 灵敏度支线（不是同级推荐）

1. **PORT-0 matched control**：唯一必须保留的 falsifier，用于 V2–V5；不预先晋级为 REMOVE 方案。
2. **uniform 10 mm BPE**：只在 PORT-20 被 V5 证伪且机制显示 0/20 的 background–mass 曲线需要中间点时才运行；不得由线性插值替代。
3. **legal MXC OD−25% / thickness−10%**：只在 PORT-20 完成 production×coupling 且热/结构模型给出明确余量后作为二阶段支线；现有 10.22% delayed proxy 与 Neff 5.58 不足以触发 transport。

上述支线都不是本报告的一级配置。

---

## 9. 质量与可复现性审计缺口

|状态|缺口|处理|
|---|---|---|
|**FACT**|LOOP “Copper 112.251 Bq”是名字前缀 bucket，不是 exact Material。|最终 BOM/率改用 60-volume Copper=161.957683 Bq；CuNi 分开。|
|**UNKNOWN**|frozen 135-row policy 缺 generator 与 pixel-center map。|在任何 frozen-policy promotion 前交付代码、UID→pixel-center authority 与 420→135 exact diff。|
|**FACT**|LC1 `pair_host_target_hit_any` 实际是目标 volume 任意 deposit，不是 first-pair host。|候选分析显式解析 first `cproc=conv` 与 ANNI host。|
|**FACT**|部分 ray length CSV 是脚本硬编码，不是 candidate geometry navigator 输出。|每个 geometry variant 重算 material chords，不复用旧列。|
|**UNKNOWN**|BGO/BPE 零 survivor 的真实上界。|按 realized decay/source exposure 报一侧 95% 上界，禁止写零 rate。|
|**UNKNOWN**|真实 flight port/BOM。|V0 为 transport 前硬门。|

---

## 10. 最终仲裁语句

**FACT**：当前没有任何合法配置在自己的 full-envelope `S20` 下，以 matched total `P20+D20` 证明 central `F3<=3e-5`。  
**INFERENCE**：PORT-20 是当前证据下的一级工程条件最优：它只修改已确定的 signal-path 几何冲突，保留外层 BPE 的有限机制收益，并避免在低 Neff、host migration、热/磁/结构未闭合时改动 cold core。  
**HYPOTHESIS**：它可能比 full-panel KEEP-20 提高真实 signal，同时比 full REMOVE 保持更低 activation background。  
**UNKNOWN**：这一支配关系以及 mission target 是否成立，只能由 V0–V6 的 candidate-specific S20 与 matched 0/20 total-background 判定。

因此：**一级推荐 PORT-20；状态 ENGINEERING-CONDITIONAL OPTIMUM；禁止写 PHYSICS PROMOTED。**

---

## 11. 审阅来源

按要求完整、顺序阅读：

1. [HANDOFF_A_PROJECT_MAINLINE.md](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/s3d_o8_loop_engineering_handoff_20260814/HANDOFF_A_PROJECT_MAINLINE.md)
2. [HANDOFF_B_THIRD_PARTY_PHYSICS_REVIEW.md](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/s3d_o8_loop_engineering_handoff_20260814/HANDOFF_B_THIRD_PARTY_PHYSICS_REVIEW.md)
3. [NEXT_SESSION_LOOP_ENGINEERING_TASK.md](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/s3d_o8_loop_engineering_handoff_20260814/NEXT_SESSION_LOOP_ENGINEERING_TASK.md)
4. [LOOP_ENGINEERING_HANDOFF.md](/home/ubuntu/.codex/worktrees/6f6c/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/session_handoffs_20260814/LOOP_ENGINEERING_HANDOFF.md)
5. [BPE_HANDOFF.md](/home/ubuntu/.codex/worktrees/9936/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/session_handoffs_20260814/BPE_HANDOFF.md)

主要独立复核 authority：

- [S3d–O8 geometry](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo)
- [Mission summary](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/outputs/06_mission/summary.json)
- [Signal acceptance](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/outputs/04_common_response/signal_acceptance_effective_area.csv)
- [Prompt event summary](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/s3d_o8_low_grammage_core_20260814/data/prompt_w2_event_summary.csv)
- [Full selected lineage](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/outputs/04_common_response/selected_background_w2_lineage.csv)
- [Day-15 inventory](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/outputs/02_activation/day15_inventory.csv)
- [BPE boundary summary](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/bpe_neutron_boundary_20260813/outputs/summary.json)
- [Frozen delayed coordinates](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/s3d_o8_low_grammage_core_20260814/data/frozen_delayed_source_coordinates.csv)
