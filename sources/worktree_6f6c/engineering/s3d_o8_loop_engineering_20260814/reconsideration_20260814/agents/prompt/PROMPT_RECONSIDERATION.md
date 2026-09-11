# S3d-O8 统一候选的 prompt 逆向物理审查

日期：2026-08-14  
审查对象：`S3D_O8_unified_Al_mag05_innerBPE_topcatch_proxy`  
结论等级：`KEEP — FOCUSED FALSIFICATION ONLY`

## Technical summary

唯一首选保留为这一个统一拓扑，而不是单独的 `Cu -> Al`：48 个非读出冷芯 Cu 体积同包络换 Al，Nb/Mu 主套筒和后盖由 2 mm 减到 0.5 mm，保留原有 outer BPE 并在半径 20.65--21.15 cm 加 5 mm BPE 内衬，再把同一 top-BGO 读出体积从 `Rin=20.9 cm` 收到 `Rin=4 cm`、保留 12 个真实服务孔和 6 个 NF2 relief。候选 setup 是：

`engineering/s3d_o8_loop_engineering_20260814/reconsideration_20260814/agents/geometry/candidate_proxy/S3D_O8_unified_Al_mag05_innerBPE_topcatch_proxy.geo.setup`

判决是 **KEEP 进入小规模 paired gamma 证伪，不是 prompt 性能晋级**。原因有两面：

- FACT：三条 S3d anti-TES 511 在 baseline 都先被内部被动材料截住；候选真实 CSG 直线把它们分别接到 `7.099 / 1.174 / 6.130 cm` BGO。原先没有 top-BGO chord 的事件 19932 现在有 1.174 cm；37,194 条 post-Be focused ray 没有一条与新增 BGO 或 plastic 相交，随后 candidate 自己的 paired signal replay 也通过。
- FACT：三条 S3d 首次 pair host 是 `Nb, Cu, Nb`，而 Mass_model_511 的 7 条最终链又给出 Cu/Nb/Al/SS 混合 host；所以 `Cu -> Al` 单独不能封闭机制。
- SCALE：5.769 MeV 下，同包络 Al/Cu 的 Geant4 Livermore pair 线性系数比约 `0.145`，但事件 19932 的完整中心穿越在 Cu 后紧接 `0.991 cm`、密度 `5 g cm^-3` 的 Ag proxy。把 Ag 纳入后，解析 pair 概率只缩到 baseline 的 `0.34--0.43`，不是 `0.145`。
- UNKNOWN：partner 在 Al/Ag/SS/BPE 中 Compton 后是否仍向 BGO 留下 `>=50 keV`，以及 pair 是否迁到 Ag/SS/保留的 XS400 Cu，只能由 candidate transport 回答。它是当前唯一阻断证据。

用 candidate 自己已测得的 focused `S20=1653.539378`，mission gate 是 `27341.924743 counts`。统一定义 `s` 为 suppression，在当前联合预算锚点 `sCu=0.95`、`sNbMu=0.75`、新材料增量 `Delta_new=0` 下，prompt 只需满足 `sPrompt >= 0.719654`（survival `<=0.280346`）。预登记的 `sPrompt=0.80` 会给总残余 `22890.854440 counts`，比 gate 低 `4451.070303 counts`。此前写的 `93.0875%/95.5789%` 是低 Nb/Mu suppression (`0.25/0.20`) 且使用旧 signal gate 的敏感性点，被误写成当前候选要求；现已更正。

## Key findings

| 物理项 | 已证实的 baseline 图像 | 候选的直接作用 | 判定 |
|---|---|---|---|
| primary uncollided | 3 条 leak 都穿过 23.43--38.92 g cm^-2 active grammage，但 active edep 都为 0 | top-BGO 收口会主动截住一部分 top primary；Cu->Al 本身反而提高 primary 到内芯的未碰撞透射 | `UNKNOWN NET`，必须单独计 `T_primary` |
| first pair host | S3d 为 Nb/Cu/Nb；Mass 7 条为 Nb×2、Cu×3、Al×1、SS×1 | Cu 与 Nb/Mu 局部 pair opacity 下降 | `SUPPORTED MECHANISM`，但有 Ag/SS migration |
| anti-TES 511 | 3883：Ag->Cu->Mu；19932：Still Cu；8081：MXC Cu->Mu->can bottom；均无 active hit | 三条初始 partner ray 都获得 BGO chord | `SUPPORTED GEOMETRY`，不是阈值 veto 效率 |
| focused signal | retained EventList 从 post-Be 面注入 | 0/37,194 几何 ray 碰 active；candidate transport 选中 27,993 vs baseline 27,855 | `PASS`：`S20=1653.539378`，retention `1.004954` |

候选 partner 射线的逐材料机读表在 `candidate_partner_ray_chords.csv`。最关键的三行是：

| event | candidate 中主要的 active 前材料 | BGO chord | 500 keV 任意相互作用标度上限 |
|---:|---|---:|---:|
| 3883 | Al 4.859 cm + Ag proxy 1.483 cm | 7.099 cm side | 0.9991 |
| 19932 | Al 3.687 cm + 保留 Cu 1.476 cm + SS 4.768 cm | 1.174 cm top | 0.6858 |
| 8081 | Al 3.996 cm + Nb/Mu 各 0.0967 cm | 6.130 cm side | 0.9976 |

最后一列只是用 500 keV NIST 总衰减系数得到的“发生任意相互作用”宽松标度；真实 `>=50 keV` veto 概率要由 transport 给出，不能把这列当效率。尤其 19932 的 1.174 cm top BGO 没有很大裕量。

## Scope and definitions

本审查严格保持 `geometry x mode x family` 归一边界，只审 S3d-O8 corrected INSTANT gamma 与已有 Mass 最终链，不加入 mono-511。当前 gamma authority 为：

- `N_incident = 3,207,738`
- `TT = 59.0965413 s`
- pre-W2 120、veto leak 3、Step05 final 2
- 两个 final event（3883、19932）各重 `0.0169214641 cps`，合计 `0.0338429281 cps`
- mission prompt `P20 = 55,398.979434 counts`

全分母的三个 leak cell 分别只有 `k/N = 1/71, 1/94, 1/92`，每格 survivor `Neff=1`。所以它们只能证实机制，不能决定全天角扇区。新增 top-BGO 不是根据三条 primary 方位挑 sector，而是关闭一个已经由 anti-TES sibling 证实、且原来 `BGO chord=0` 的全环形 partner escape topology。

本报告区分：

- `FACT`：原始 SIM IA/CC、真实 MEGAlib CSG 射线、完整 IA INIT 分母直接给出；
- `SCALE`：XCOM/EPDL 指数衰减，只用于判断数量级；
- `UNKNOWN`：需要 transport 才能回答的 pair migration、散射后 BGO 阈值能量与最终 W2。

## Candidate geometry and mass accounting

48 个 Cu->Al 体积包括 20 个 open-ring panel、L0 solid disk、4 edge rods、4 off-axis fingers、4 stems、4 clamps、4 个 50 mK can 体积、MXC/CP/Still/4K 四冷盘，以及 DR mixing chamber、still pot、4K condenser。11 个 XS400 service Cu 和 remote flex link 不在替换范围，因而 19932 partner 路径中仍有 1.476 cm Cu。

固定每个 volume 随机种子的同一 Geomega 查询给出的名义质量为：

- 48-volume scope：Cu `20.273281 kg` -> Al `6.113230 kg`；
- 四个 Nb/Mu shell+cap：`0.928496 kg` -> `0.225286 kg`；
- top BGO：`4.355872 kg` -> `15.474717 kg`；
- 新 inner BPE：`3.744416 kg`。

布尔 CSG 的 `MDShapeSubtraction::GetVolume()` 使用 ROOT Monte-Carlo `Capacity()`。修正为 per-volume fixed seed 后，changed-scope 名义值为 baseline `25.5576487300 kg`、candidate `25.5576489335 kg`，差 `+0.204 mg`；但修正前仅改变查询顺序就曾得到 `-1.342 g`。后者暴露了 `Capacity()` 的 gram-level 数值分辨率，所以这里只能说在约 25.56 kg changed scope 上工程质量守恒到 `~few g`，绝不能把 `+0.204 mg` 当真实 BOM 精度。

## Prompt origin decomposition

### Joint-budget notation correction

这里所有 `s` 都是**抑制比例**，不是 survival。采用 exact 48-volume delayed 分解：

`B20 = P(1-sPrompt) + C(1-sCu) + M(1-sNbMu) + O + Delta_new <= G_candidate`

其中 `P=55398.979434`、`C=59252.576459`、`M=27605.141950`、`O=1947.144243`、`G_candidate=(1653.539378/10)^2=27341.924743`。因此在 `sCu=0.95`、`sNbMu=0.75`、`Delta_new=0` 下：

`sPrompt_min = 1 - [G_candidate - C(1-0.95) - M(1-0.75) - O]/P = 0.719654290594`。

`sPrompt=0.80` 时四项依次为 `11079.795887 + 2962.628823 + 6901.285488 + 1947.144243 = 22890.854440 counts`。这里 `0.95/0.75/0.80` 都尚是待 transport 验证的联合假设；`Delta_new=0` 也只是筛选预算，不是 Al/BPE activation 已被证明为零。

### 1. Primary uncollided transmission

候选不能把“更少 Cu 相互作用”直接叫作 prompt 下降。在 5--6 MeV，同体积 Al 的总线性衰减约为 Cu 的四分之一量级，因此更多 primary 会未碰撞进入 Ag/Nb/SS 邻近体积。这是潜在的 host migration 增益项，而不是免费收益。

必须在 paired run 中分别输出：

`T_primary(E, direction, active grammage) = N(reach cold-core boundary with no IA) / N_incident`。

top BGO 则是相反的外层作用：在 active volume 内发生 pair/Compton 会产生 veto。两项不能合并成一个“总透射率”。

### 2. Pair-host opacity and migration

本地 Geant4 G4EMLOW 8.4 的 EPDL/Livermore nuclear-pair + triplet 表给出，在 5.76882 MeV：

- Al：`mu_pair = 0.0135266 cm^-1`
- Cu：`mu_pair = 0.0931467 cm^-1`
- Ag proxy（rho=5）：`mu_pair = 0.0794896 cm^-1`

所以单一 Cu 体积换 Al 的线性 pair scale 是 `0.1452`。但 19932 的真实 primary 直线越过 DR 后立刻穿 `0.990985 cm` Ag proxy，之后再穿 MXC plate。按完整中心 crossing 的 Al/Cu/Ag chord 做指数标度：

- baseline 任一 Al/Cu/Ag pair 概率：`0.4149`
- candidate：`0.1773`
- ratio：`0.4274`，即只降 `57.3%`

若只取 Still+CP+DR+Ag+MXC 近芯段，ratio 仍为 `0.3432`，只降 `65.7%`。这不是 transport 预测，但足以证伪“pair 一定按 0.145 缩放”的说法。对应机读量在 `prompt_component_scaling.csv`。

两条 Nb host 的全弦 pair 标度约降 `69.5--74.6%`，也不是 100%；变薄后 primary 可继续进入 Al/Ag/remaining service metal。

### 3. Partner-photon veto

原始 IA parentage 的事实是：

- 3883 的 anti-TES 511 首次 COMP 在 Ag proxy，随后进 MXC Cu 和 Mu；
- 19932 首次 COMP/最终 PHOT 在 Still Cu；
- 8081 首次 COMP 在 MXC Cu，随后到 Mu back cap 和 can bottom；
- 三条 branch 的 BGO/plastic edep 都精确为 0。

候选真实 CSG ray 把 19932 从 `BGO=0` 改为 `BGO=1.1736 cm`，同时保留 side 两条 6--7 cm chord。这证明候选切中了 sibling escape topology。

但是 partner 在到 BGO 前仍需穿过大量 Al，3883 还保留 1.483 cm Ag，19932 还保留 1.476 cm Cu 和 4.768 cm SS。用 NIST 500 keV 总衰减只算 Al/Cu/Ag，三条 uncollided transmission 的宽松上标度也仅 `0.166 / 0.143 / 0.402`；实际 Compton 后仍可能到 BGO，因此这不是 veto 下限或上限。正确结论只有一个：**几何 sightline 已打开，阈值 veto coupling 仍完全 unknown。**

Mass_model_511 的 7 条最终链提供独立的同构检查：4/7 anti-TES partner 首次在 Cu 相互作用，1/7 在 CsI 只沉积 31.79 keV，2/7 直接逃逸；pair host 同时包含 Cu、Nb、Al、SS。这支持“降低内芯吸收 + 补 active coverage”作为共享杠杆，也直接反驳 Cu-only 材料定律。

### 4. Signal geometry

对完整 37,194-event focused EventList，从每个 post-Be 注入点追到 InstrumentFrame 最近点：baseline 和 candidate 都是 `0` 条 BGO chord、`0` 条 plastic chord。EventList 注入点的 InstrumentFrame radial range 为 `13.100--13.168 cm`，已经在 20.65 cm BPE liner 内侧。

所以新增 top BGO 不会几何遮住当前 retained signal phase space。candidate 自己的 paired replay 已给出 27,993/37,194 selected、`Aeff=15.11622 cm^2`、`S20=1653.539378`；baseline 是 27,855 selected，signal retention `1.004954`，状态为 `PASS__CANDIDATE_OWN_FOCUSED_SIGNAL_COMMON_RESPONSE`。数据分别在 `focused_eventlist_geometry_audit.json` 与 `focused_signal/candidate_signal_result.json`。边界仍仅是 post-Be focused injection，不代表 full-envelope optics。

## KEEP / MODIFY / KILL

| 假说 | 判决 | 触发证据 |
|---|---|---|
| 只做 48 Cu->Al，外 active topology 不变 | `KILL` | S3d 有 2/3 Nb pair；Mass host 混合；partner 仍可从 top hole/SS service 逃逸；Ag migration 保留 |
| 只收小 top-BGO 中央孔 | `KILL AS SOLE TOPOLOGY` | 只直接覆盖 19932 的 top escape；3883/8081 已各有 6--7 cm side-BGO chord，真正缺的是内部 partner absorption 与 Nb/Cu pair host 同时下降 |
| 按三条 primary 方位把 BGO 质量搬到少数 sector | `KILL` | 三个分母格各只有一个 survivor，不能外推方向率 |
| 只把 Nb/Mu 变薄 | `KILL` | primary 会迁往 Cu/Ag/Al，且不解决 partner 被动吸收或 top active hole |
| 当前统一候选 | `KEEP — FOCUSED FALSIFICATION ONLY` | 它是唯一同时作用于 Cu/Nb pair host、内部 partner absorption 和 top active coverage 的单一质量闭合拓扑 |

没有更简单的单一 prompt 杠杆同时覆盖三项。把非接口 Cu 直接开 web/移成 vacuum 在纯 prompt 上可能比 Al 更强，但它仍不解决 Nb host 和 top hole，而且新增一个未验证的热/结构设计自由度；因此不作为并行候选。元素 Al 是当前 proxy 中唯一已经定义并进入 delayed 审计的同形低-Z替代；6061 没有准确 alloy card，更低-Z bulk 替代也没有候选位置的 activation/冷端功能账，因此都不能在本轮冒充“更优材料”并行晋级。

## Minimal paired-run proof/falsifier

### Stage P1：小型机制 paired run，先跑

从完整分母中取三个已观测 cell 的全部 IA INIT 状态，共 `71+94+92=257` 条，不只取 3 个 survivor。baseline/candidate 用相同 INIT 列表、匹配 shard，transport seed 独立且预登记；重复直到 baseline 在每种机制至少获得 30 条 pair-chain，而不是按三条历史事件外推。

逐 history 必须写出：

1. 是否未碰撞到 cold-core boundary；
2. first interaction 与 first pair 的 volume/material；
3. e+ stop 与 ANNI volume；
4. TES photon 和 anti-TES sibling 的 IA parentage；
5. sibling 在 BGO/plastic 的实际 edep，特别是 `>=50 keV`；
6. W2、veto、Step05 和 event weight。

立即 `KILL` 的机制 falsifier：candidate 的 selected/no-veto 权重迁到未改的 Ag/SS/XS400 Cu，且 top/side BGO 对该迁移链仍无 `>=50 keV`；这意味着当前 topology 内没有剩余可调杠杆。

### Stage P2：candidate 自己的 focused signal — 已完成

同一份 37,194-event post-Be EventList 的 baseline/candidate paired signal transport 已完成：candidate `S20=1653.539378`，`B20_max=(S20/10)^2=27341.924743 counts`，相对 baseline retention `1.004954`。这关闭了当前 focused-signal 门，但不外推到注入面上游。

### Stage P3：gamma rate confirmation

只有 P1、P2 通过后，才用 corrected gamma 的完整 pair-capable support 做 matched、独立 seed 的 baseline/candidate confirmation，并保持每个 gamma cell 自己的 TT/weight。预登记输出必须仍按 `E x direction x active grammage` 给分母和 Neff。

若 candidate 为 0 个 Step05 event，在 equal exposure、equal-weight sampling、独立 Poisson rate 的一侧 95% exact conditional 比率门下：

- 要证明当前联合预算门 survival `<=0.2803457`，baseline 至少要观测 `13` 个 event，约当前 `6.5x` exposure（约 20.85M histories、384.13 s TT）；此时 exact upper ratio 为 `0.2592`；
- 要证明预登记的 `sPrompt>=0.80`，即 survival `<=0.20`，baseline 至少要观测 `17` 个 event，约当前 `8.5x` exposure（约 27.27M histories、502.32 s TT）；此时 exact upper ratio 为 `0.1927`。

若 candidate 非零，必须用预登记的 exact rate-ratio upper limit，不能继续用“0-event 公式”；若 history 权重不等，也不能直接套 count-only 公式。任一占 prompt 权重超过 10% 的 cell 若仍由单事件控制，不能晋级。

## Limitations and robustness

- 三条 S3d 与七条 Mass 链是 conditioned final events，只能给机制混合，不能给全天角占比；本报告保留逐事件表而不画平滑热图，以免掩盖 `Neff=1` 的热点。
- 直线 ray 是 ANNI 后初始 sibling 方向；实际 Compton 轨迹会偏折。它证明 CSG sightline，不证明阈值 veto。
- XCOM/EPDL 指数标度忽略 pair 产物角分布、e+ range、Compton 返入、能量逃逸与 Step05；所有乘法只用于检查数量级。
- candidate 新 BPE 可能把 511 Compton 出 BGO sightline，也可能降低 neutron activation；prompt 净号未知。
- Al 在 mK 温区的热导、超导/接触、Nb/Mu 0.5 mm 的磁闭合不属于本 prompt 审查，仍是独立工程硬门。
- CSG mass query 是 MC capacity，gram-level 数字不应当作精确 BOM。

## Next step

**现在值得立即跑 P1 的 257-state paired gamma 机制测试；P2 focused signal 已通过，不值得直接跑 full eight-family。**

最终状态保持 `ENGINEERING-CONDITIONAL OPTIMUM`。唯一阻断证据是：在真实候选中，把 Ag/remaining service-metal host migration 与 `>=50 keV` partner-BGO coupling 一起计入后，candidate 的 prompt survival 一侧上限是否低于当前联合门 `0.2803457`（预登记目标 `0.20`）。

## Further questions

如果 P1 失败，只需回答一个问题再决定是否彻底 KILL：失败权重是否集中在不可移除的 Ag proxy/真实服务孔。若是，则约束内 prompt topology 已耗尽；若不是，则说明候选几何实现或 scorer 有可定位错误，而不是再开启一串平行材料方案。

## Sources

- S3d prompt interaction points：`engineering/s3d_o8_loop_engineering_20260814/agents/prompt/prompt_leak_interaction_points.csv`
- 完整 gamma 分母：`engineering/s3d_o8_loop_engineering_20260814/agents/prompt/denominator/gamma_denominator_summary.json`
- Mass 7-chain 对照：`engineering/s3d_o8_loop_engineering_20260814/agents/prompt/mass_model_final_prompt_pair_hosts.csv`
- partner IA/CC：`annihilation_partner_paths.csv`
- candidate exact ray：`candidate_partner_ray_chords.csv`
- pair/预算标度：`prompt_component_scaling.csv`
- corrected prompt gate：`prompt_budget_gate.json`
- candidate focused signal：`engineering/s3d_o8_loop_engineering_20260814/reconsideration_20260814/focused_signal/candidate_signal_result.json`
- Geant4 Livermore pair tables：`/home/ubuntu/geant4-data/G4EMLOW8.4/livermore/pairdata/pp-pair-cs-{13,29,41,47}.dat` 与 `tripdata/`
- NIST XCOM 说明：[XCOM photon cross sections database](https://www.nist.gov/pml/xcom-photon-cross-sections-database)
- NIST 元素总质量衰减系数：[Al](https://physics.nist.gov/PhysRefData/XrayMassCoef/ElemTab/z13.html)、[Cu](https://physics.nist.gov/PhysRefData/XrayMassCoef/ElemTab/z29.html)、[Ag](https://physics.nist.gov/PhysRefData/XrayMassCoef/ElemTab/z47.html)、[O](https://physics.nist.gov/PhysRefData/XrayMassCoef/ElemTab/z08.html)、[Ge](https://physics.nist.gov/PhysRefData/XrayMassCoef/ElemTab/z32.html)、[Bi](https://physics.nist.gov/PhysRefData/XrayMassCoef/ElemTab/z83.html)
