# S3d-O8 prompt LOOP：保留热学 Cu 后的骨架冷芯与同通道 top catcher

> **SUPERSEDED / KILL（2026-08-14 新机械边界）：** 用户随后限定冷盘外径最多缩小 25%、厚度最多减少 10%、仅允许少量 M4 孔。本文定义的 TC-SK1 skeletal cold plates 因此失效，不得实施或进入 transport。替代的单一 prompt 候选与复算见 `COLD_PLATE_CONSTRAINED_PROMPT_ADDENDUM.md`；本文只保留为被证伪路线的审计记录。

## 技术结论

在“近场 Cu/Ni 必须保留、Nb/Mu 不改、允许增加屏蔽质量”的新边界下，唯一值得进入 focused transport 的 prompt 拓扑是：

> **TC-SK1：四重周期、非事件定向的 Cu 冷芯骨架（薄 Cu skin + 宏观热辐条 + 各温级外环；L0 和 can bottom 开框/薄 skin；Cu/Ni/SS 服务载荷并入同一组宏观脊柱）+ 现有 BGO 同一读出通道的 top catcher（中心内半径不大于 4 cm，保留真实服务 relief，反 TES 直线上的 BGO chord 不小于 3 cm）。**

所有 Cu 材质及每温级需要的总质量/导热截面保留，质量从 TES 高固体角面移到外环和热辐条；不把 Cu 换成 Al，不改 Nb/Mu，不新增 scorer、读出或 active channel，也不在 TES 附近放 W/Pb。四重周期方向由真实热/承载接口冻结，**不得按 3883/19932/8081 的方位旋转或逐射线打孔**。

判决是 **`MODIFY -> KEEP FOR FOCUSED FALSIFICATION`**，不是性能 PASS。唯一 prompt 阻断证据是：在真实 TC-SK1 CSG 中计入固定 Ag、Nb/Mu、Al/BPE 和服务金属后，matched candidate/baseline 的最终 prompt survival 一侧 95% 上限是否 `<= 0.20`。若不能形成连续服务通道，或该统计门失败，则直接 `KILL TC-SK1`；不能再用事后 sector 或平滑热图补救。

先前的 48-volume Cu→Al / Nb-Mu 变薄 / inner-BPE / top-catch 组合（下文称 `AF1-48`）在新边界下为 **`KILL`**。它移除了热学所需 Cu、改变冻结的 Nb/Mu，并且其 focused 结果不能证明保留 Cu 后的 prompt 机制。

## 关键发现

1. 完整 gamma 分母是 `3,207,738` histories、`TT=59.0965413 s`。只有 3 条 active-veto leak，最终 Step05 只有 3883 与 19932；每条等权 `0.0169214641 cps`，当前 gamma prompt 为 `0.0338429281 cps`。三条非零 `E x direction x active-grammage` 格各只有一个 survivor，不能据此选外部 BGO sector。
2. 三条入射 primary 都先无碰撞穿过真实 active material：BGO chord `3.148/5.290/4.044 cm`，plastic chord `1.049/1.323/1.011 cm`，active edep 均严格为零；随后分别在 `Nb/Cu/Nb` 首次 pair。它们不是 seam 或阈值漏事件。
3. 三条 anti-TES 511 在到 active shield 前的 Cu chord 是 `2.906/3.946/1.844 cm`。以 511 keV Cu 总衰减 `mu_Cu≈0.749 cm^-1` 只作标度，Cu-only 未碰撞 survival 仅 `0.113/0.052/0.251`。若想让 Cu 自身 survival 达到 0.8，**整条路径上所有 Cu chord 的总和**必须 `<=0.298 cm`（约 `2.67 g cm^-2`），不是把某一块盘减到 3 mm。
4. 19932 是 top escape，但 top BGO 单独收口无效：基线直线除 `3.946 cm Cu` 外还含约 `4.768 cm SS`、`2.029 cm BPE` 和 `1.217 cm Al`。近似真实 L2 像元的几何扫描 ray `c0106` 在预定冷盘之外仍命中 6 个服务结构、合计约 `7.42 cm`。所以 TC-SK1 必须把宏观开域贯穿服务栈；只把冷盘开孔是假 sightline。
5. 3883 与 8081 若不在内部被吸收，已有 side BGO chord 分别为 `7.099` 和 `6.130 cm`；511-keV any-interaction 标度约 `0.9991/0.9976`，不需要为这两条再加 side BGO。真正问题是 3883 的 `1.483 cm Ag-sinter proxy` 与 8081 的各 `0.387 cm Nb/Mu`，这些固定材料使 Cu 骨架的收益不能等同于 veto 效率。
6. 七条独立 `Mass_model_511` 最终链的 pair host 是混合的（Nb、Cu、Al、SS）；四条 anti-TES partner 首先在 Cu 相互作用，一条在 CsI 只给出低阈下 deposit，两条逃逸。选中样本中，三条 `+z_IF` Mass partner 的直线均看不到 active volume，而四条 `-z_IF` partner 都有 bottom-CsI chord。该几何同构支持 top catcher，但 7 条是 survivor 条件样本，不是方向分母。

本报告不画平滑方向热图：三个 S3d 非零格的 `Neff=1`。保留逐事件表和有分母的 cell 统计比视觉插值更诚实。

## 范围、数据与定义

### 只读来源

- 上一轮低 grammage 结论：`/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/s3d_o8_low_grammage_core_20260814/REPORT.md`
- LG1 screening：`/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/s3d_o8_lg1_screening_20260813/REPORT.md`
- LG1 smoke diagnostic：`/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/s3d_o8_lg1_screening_20260813/LG1_SMOKE_DIAGNOSTIC.md`
- 完整 gamma 分母：`engineering/s3d_o8_loop_engineering_20260814/agents/prompt/denominator/gamma_denominator_summary.json` 与 `incident_gamma_E_mux_az_active_grammage.csv`
- 三条 prompt interaction/chord：`engineering/s3d_o8_loop_engineering_20260814/agents/prompt/prompt_leak_interaction_points.csv`、`prompt_leak_material_chords.csv`
- 十条 anti-TES lineage 与真实 CSG straight rays：`engineering/s3d_o8_loop_engineering_20260814/reconsideration_20260814/agents/prompt/annihilation_partner_paths.csv`、`partner_straight_ray_segments.csv`、`partner_straight_ray_summary.csv`
- 本轮 event19932 reverse-TES 几何扫描：`engineering/s3d_o8_loop_engineering_20260814/thermal_cu_rethink_20260814/agents/geometry/escape_chimney_scan.csv`

### 统计与坐标定义

InstrumentFrame 变换为

`x_IF=(x_world-z_world)/sqrt(2), y_IF=y_world, z_IF=(x_world+z_world)/sqrt(2)`。

“partner”指与进入 TES 的 annihilation 511 同一次 `ANNI`、方向相反的 sibling。`pre-active chord` 是从 ANNI 点沿 sibling 初始方向到第一个 active volume 的真实 CSG 直线弦；它是 sightline 诊断，不包含 transport 后散射路径。

所有指数式仅是单光子、未碰撞标度：

`T=exp(-mu L)`。

它既不是 veto efficiency，也不是 pair-host rate，更不是 full-chain performance。特别是 passive 中发生 Compton 后，photon 仍可能进入 BGO；相反，active 中发生一次相互作用也未必超过 50 keV gate。

## LOOP 1 — Localize：分母与真实路径

### Incident primary

| Event | E (MeV) | entry | BGO chord (cm) | plastic chord (cm) | active grammage (g cm^-2) | first pair | Step05 |
|---|---:|---|---:|---:|---:|---|---|
| 3883 | 4.148 | bottom | 3.148 | 1.049 | 23.434 | Nb inner cylinder | pass |
| 19932 | 5.769 | side | 5.290 | 1.323 | 38.923 | DR mixing Cu | pass |
| 8081 | 6.346 | side | 4.044 | 1.011 | 29.754 | Nb inner cylinder | fail |

对应有分母的非零格分别是 `1/71`、`1/94`、`1/92`；三个格的 95% 单侧上限约 `6.51%/4.95%/5.05%`。去掉 grammage 轴后分母增到 `867/702/633`，但仍只有一个 numerator，仍不能冻结 sector。

### Anti-TES 511

| Event | `z_IF` direction | first passive interaction | Cu chord (cm) | other decisive passive | straight active chord |
|---|---:|---|---:|---|---|
| 3883 | +0.826 | Ag proxy | 2.906 | Ag 1.483 cm; Mu 0.198 cm | side BGO 7.099 cm |
| 19932 | +0.986 | Still Cu | 3.946 | SS 4.768 cm; BPE 2.029 cm; Al 1.217 cm | BGO 0; top plastic 1.014 cm |
| 8081 | +0.753 | MXC Cu | 1.844 | Nb 0.387 cm; Mu 0.387 cm | side BGO 6.130 cm |

三条实际 sibling branch 的 active edep 都是零。完整十条选择样本在 `selected_partner_topology.csv`；逐 volume 弦以原始 `partner_straight_ray_segments.csv` 为准。

## LOOP 2 — Origin：为什么“薄盘”与“top BGO”必须耦合

### 冷盘是 partner absorber，但不是唯一 absorber

三条 sibling 在 InstrumentFrame 的 polar angle（相对 `+z`）为 `34.32/9.69/41.13 deg`。它们不是一根共轴射线。若用一个同轴圆孔仅包住这三条已观察射线在每块盘上的交点，最小半径是：

| plate (`z_IF`) | plate radius (cm) | max observed-ray radius (cm) | removed disk area fraction |
|---|---:|---:|---:|
| MXC (0) | 15.0 | 6.407 | 18.24% |
| CP (5) | 15.0 | 10.483 | 48.84% |
| Still (11) | 15.0 | 9.829 | 42.94% |
| 4K (20) | 17.5 | 15.959 | 83.16% |

这些百分比只是 `(r_max/R_plate)^2`，是 post-selected 三射线的下界，不是全天角接受域。它同时破坏大量热截面，且还留下 Ag、Nb/Mu 与服务金属，所以 **同轴宏孔 `KILL`**。

TC-SK1 改成全局、周期性的薄 skin/热辐条/外环，是为了让“是否命中 Cu spine”成为一个预先冻结的几何接受问题，而不是按三条 ray 打孔。Cu 总质量向外环移动也会降低近 TES 的 delayed solid-angle coupling；这一点需由 delayed 审阅独立验证。

### 19932 证明 top hole，但也证伪 top catcher alone

19932 的 sibling 在 CP/Still/4K 平面中心约位于 `r=2.53/3.47/4.94 cm`，最终沿 top central opening 离开，top 局部半径约 `9.31 cm`，基线 BGO chord 为零。将现有 top BGO 的内半径收至 `<=4 cm` 确实覆盖这条几何。

但该直线还穿过 XS400 Cu/SS 服务栈。只把 top BGO 收口、保留实心冷盘和服务壳，511 在到 BGO 前已被吸收；因此 **top catcher alone `KILL`**。TC-SK1 的必要条件是 CSG 上从近芯到 top catcher 的开域连续，不允许把服务结构从 chord 账中漏掉。

### Pair host 会迁移

把冷盘骨架化会降低 4--8 MeV primary 在 Cu 中的 pair opacity，也会提高 primary 到达 DR/Ag/Nb/Mu 的概率。19932 的 primary 与 sibling 在 CP 附近并不完全分离；全局 thin-skin 会同时改变两条路径。因此必须分别输出：

- primary 到 cold-core boundary 前无 IA 的概率；
- first-pair host 的 Cu/Nb/Mu/Ag/Al/SS 分布；
- positron stop/ANNI host；
- 对每个 TES-producing ANNI，sibling 的 active deposit 与 gate pass。

不能把 partner sightline 改善直接当成净 prompt 改善。

## LOOP 3 — Optimize：候选规格与 BGO 对照

### TC-SK1 的 prompt 几何规格

1. **Cu 骨架**：MXC/CP/Still/4K 与相关 L0/can-bottom 采用不超过约 0.5 mm 的连续 Cu skin、四条宏观热辐条和厚外环；四重方向由热接口冻结。质量与热载流截面移到外环/辐条，不换材质。
2. **路径门**：对预先冻结的 reverse-TES cassette，所有 Cu skin、stem、clamp、flange、thermal tab 的总 chord 必须 `<=0.30 cm`。单件满足而总和超标仍算失败。
3. **服务门**：Cu/Ni/SS 服务与承载结构合并到同一组宏观 spine；19932 类 top 开域中不得残留连续 service-can chord。Nb/Mu 闭合体保持基线，不打孔、不减薄。
4. **Ag 边界**：Ag-sinter proxy 原样保留，直到实物 BOM/孔隙率/有效密度闭合。3883 是否仍被 Ag 吸收是首要 falsifier。
5. **active catcher**：只扩展现有 BGO channel，top inner radius `<=4 cm`，保留 12 个真实服务 relief；所有预登记 top reverse rays 的 BGO chord `>=3 cm`。不增加 detector/readout/scorer。
6. **BPE**：不在 cold core 与 BGO 之间新增 BPE 作为 prompt 挡板。若 delayed 需要 BPE，只能先放在 BGO 外侧并单独计算 capture gamma/activation，不能让它先于 BGO 散射 sibling。

`0.5 mm` 是从 `L_Cu,total<=0.30 cm` 反推的几何起点，不是热学结论。若四块倾斜 skin 都被穿过，0.5 mm/块已经消耗约 `0.20--0.27 cm` 的总 chord，留给 stem/flange 的余量很小。

### Cu grammage requirement

取 `mu_Cu≈0.749 cm^-1`、`rho_Cu=8.954 g cm^-3`：

| desired Cu-only survival | max total Cu chord (cm) | max Cu grammage (g cm^-2) |
|---:|---:|---:|
| 0.90 | 0.141 | 1.26 |
| 0.80 | 0.298 | 2.67 |
| 0.70 | 0.476 | 4.26 |
| 0.50 | 0.925 | 8.29 |

这只是 Cu 自身未碰撞 survival。3883 的 Ag、8081 的 Nb/Mu、19932 的 Al/BPE/服务栈会继续降低直达 BGO 的比例；所以 `L_Cu<=0.30 cm` 是必要设计门，不是充分性能门。机读表在 `cu_grammage_scaling.csv`。

### BGO optical-depth comparison

在 5.77 MeV 取 `mu_BGO≈0.276 cm^-1`。若把新增 active optical depth 对 primary 的 factor 写成 `T_primary=exp(-0.276 DeltaL)`，把 partner veto probability 写成 `q_partner`，非常简化的乘积尺度是

`T_total ≈ T_primary * (1-q_partner)`。

为满足预登记 prompt survival `<=0.20`：

| additional BGO path `DeltaL` (cm) | primary factor | required `q_partner` |
|---:|---:|---:|
| 0 | 1.000 | 0.800 |
| 1 | 0.759 | 0.736 |
| 2 | 0.576 | 0.653 |
| 3 | 0.437 | 0.542 |
| 4 | 0.332 | 0.397 |
| 5 | 0.252 | 0.205 |
| 5.83 | 0.200 | approximately 0 |

因此单靠全周 BGO 需要约 `+5.8 cm` optical path 才有 0.2 的未碰撞标度；`+1--2 cm` 不能独自承担目标。它质量很大，还需重算 BGO 自身次级和 activation，所以不作为与 TC-SK1 并行的首选。

对 511 keV，取 `mu_BGO≈0.986 cm^-1`，top catcher 的 `1.174/3/4 cm` any-interaction 标度为 `0.686/0.948/0.981`。旧 top proxy 的约 1.17 cm chord 太薄，本轮把 `>=3 cm` 写成候选规格；真实 `>=50 keV` veto efficiency 仍必须 transport 测量。完整标度在 `bgo_partner_tradeoff.csv`。

## 对 H1 / H3 / H5 与 AF1-48 的独立复核

| 前 session 假说 | 本轮判决 | 独立理由 |
|---|---|---|
| H1：降低 BGO 内表面至 TES 的高固体角 grammage | **MODIFY / KEEP** | 三条 sibling 的大 Cu chord 与 7 条 Mass 链的 Cu first-interaction 支持降低近场视线 grammage；但均匀删 Cu、同轴孔和事件定向孔均被证伪。只保留周期 skeletal Cu、质量/热截面外移。 |
| H3：保持现有 active channel | **KEEP** | LG1 新 mK BGO/scorer 被硬约束排除；top catcher 必须沿用现有 BGO channel。三条 primary 方向无重复分母，因此外部 sector KILL。 |
| H5：材料替代逐件判断 | **KEEP，且更严格** | 热学 Cu/Ni 不允许 wholesale substitute；Ag proxy 有效密度仍未知；Nb/Mu 冻结。优化自由度改成同材质拓扑，不是假定 Al 更优。 |
| AF1-48：48 cold-core Cu→Al + Nb/Mu 0.5 mm + inner BPE + top catch | **KILL** | 违反 Cu 热功能与 Nb/Mu 冻结；inner BPE 会改变 sibling-to-BGO 顺序；已有 signal/mechanism smoke 不能转移成新边界下的 prompt proof。 |

LG1 的 `5/5`（4.15-MeV 条件样本）和 `0/2`（5.77-MeV 条件样本）只能说明其局部几何覆盖不均；它新增 mK active volume/readout，因此不进入本候选。旧 LC1 `8192`-event root19932 结果中 baseline/LC1Cu/LC1CuNb 的 W2+veto survivors 为 `1/2/1`、pair 总数近似不变，说明简单减 Cu 会 host-migrate；这正是 TC-SK1 必须测 first-pair host、不能用 Cu 质量缩放冒充 rate 的原因。

## LOOP 4 — Prove/Falsify：最小 focused test

本报告不运行 transport。候选几何冻结后，按以下顺序串行运行：

### P0：纯几何门（任何一项失败即 KILL）

- 三条原始 S3d sibling ray 与预登记 reverse-TES cassette 的 `L_Cu,total<=0.30 cm`；
- 3883/8081 保留 side-BGO chord `>=6 cm`；19932 类 top ray 的 top-BGO chord `>=3 cm`；
- 19932 top ray 不再穿连续 Cu/Ni/SS service can；
- source/SIM header 指向同一候选；Nb/Mu 与 Ag 和基线完全相同；
- 现有 signal EventList 到 InstrumentFrame 的光路仍为零 BGO/plastic intersection。

### P1：三 cell matched mechanism cassette

用 3883/19932/8081 各自冻结的 INIT phase-space cell，baseline/candidate 用独立 seed、相同 histories。逐 cell 输出：

- incident denominator、`P(primary reaches cold core without IA)`；
- first-pair 与 ANNI host；
- `TES 480--550 keV`、multiplicity、frozen spatial/layer selection；
- sibling 在 BGO/plastic 的 deposit distribution、`>=50 keV` pass；
- 单事件权重和 Neff，不画平滑图。

机制晋级条件不是“看见更多 BGO hit”，而是每 cell 不出现新的高权重 host-migration 热点，且合并后的 exact one-sided 95% candidate/baseline final-survival ratio `<=0.20`。若 candidate 为零、baseline/candidate 等 exposure 且 final events 等权，baseline 至少需 `17` 个 final survivor；此时零 candidate 的一侧上限约 `0.193`。非零或不等权时必须用准确 rate-ratio interval，不能套 `17`。

### P2：完整 corrected-gamma confirmation

P1 通过后才运行完整 pair-capable corrected gamma，保持 `geometry x mode x family` 的 TT/weight 边界。以当前 exposure 线性估计，若 candidate 仍为零，约需 `8.5x` 当前统计，即约 `27.27M histories`、`TT≈502.3 s` 才能把 survival 上界压到 0.20；这是计划尺度，不是提前宣称精度。

P2 必须按预登记 `E x equal-solid-angle direction x exact active grammage` 给 denominator、numerator、Neff，并独立报告单事件高权重。最后再进入 full-chain prompt+delayed+signal；机制未闭合前不做全链。

## 局限性与唯一 KILL 条件

- 3 条 S3d 和 7 条 Mass 链都是 selected survivors；只有 incident gamma 有完整分母。它们能定位机制，不能给 partner 方向效率。
- Cu/Ag/Al/BGO 的指数式只给 optical-depth 尺度；没有阈值 response、二次粒子和散射回流。
- Ag-sinter 仍是 `rho=5 g cm^-3` proxy。3883 的 1.483-cm chord 可能被实物孔隙率改变，也可能继续完全控制该链。
- “保留热截面”必须由每温级真实热流、界面 conductance、振动/承载和 cooldown FEM/试验确认；Cu 总质量守恒不等于热性能守恒。

**唯一 prompt KILL 条件**：在 P0 已证明连续 sightline、且热/结构约束满足后，P1/P2 对 TC-SK1 得到的最终 prompt survival 一侧 95% 上限仍 `>0.20`，或优势被 Ag/Nb/Mu/SS host migration 抵消。达到该条件就 KILL；不再给事件定向 sector、inner-BPE 或 AF1-48 作为并列逃生路线。

## 机读产物

- `cu_grammage_scaling.csv`：三条基线 Cu chord 与统一 511-keV Cu grammage target。
- `bgo_partner_tradeoff.csv`：高能 primary BGO optical-depth 与所需 partner veto 的标度。
- `selected_partner_topology.csv`：3 条 S3d + 7 条 Mass anti-TES partner 的 IF 方向、first interaction、active chord 与主要 passive chord。
- `s3d_partner_plate_intercepts.csv`：三条 S3d sibling 对四块冷盘平面的 IF 投影、forward/finite-disk 判定与同轴孔下界使用标志。
- `tc_sk1_prompt_gates.csv`：唯一候选的几何、机制和完整 gamma 统计门。
