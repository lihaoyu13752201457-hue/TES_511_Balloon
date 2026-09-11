# S3d-O8 统一几何候选：独立工程审查

日期：2026-08-14  
审查范围：真实 S3d-O8 Geomega setup、体积/材料/质量、孔洞与功能边界；未跑 transport  
判决：**ENGINEERING-CONDITIONAL KEEP — 唯一候选进入 focused S20 证伪，尚非性能 PASS**

## 结论先行

唯一冻结候选是：

`S3D_O8_unified_Al_mag05_innerBPE_topcatch_proxy`

权威 setup：

`engineering/s3d_o8_loop_engineering_20260814/reconsideration_20260814/agents/geometry/candidate_proxy/S3D_O8_unified_Al_mag05_innerBPE_topcatch_proxy.geo.setup`

它是一项**单一系统拓扑**，不是四个可拆选项：同形替换 48 个非读出冷芯
Cu 为现有元素 Al，Nb/Mu 套筒与后盖保持内表面不动而减薄至 0.5 mm，
在真空罐与侧 BGO 间加入 5 mm BPE 内衬，并用同一 top-BGO volume/channel
收小顶孔、保留所有真实服务孔。释放的 Cu/Nb/Mu 质量全部重排为 BPE/BGO；
按当前 CSG 固定种子账本，25.55765 kg changed scope 名义差为
`+0.000000203 kg`，但布尔体积本身只有 gram-level 数值分辨率，所以正确工程
表述是“质量守恒到数克”，不是亚毫克精度。

这个候选在允许边界内具有可能性，但没有现有数据证明它能把 central background
从 `0.08832268` 降到 `<=0.01658181 cps`；这要求至少削减
`0.07174087 cps`，即 `81.2259%`。是否满足 central
`F3 <= 3e-5 photon cm^-2 s^-1` 只能由候选自己的 focused prompt、
BUILDUP/decay 与 signal S20 回答。

唯一工程 blocker 是一份**冷芯功能资格包**：元素 Al 同形冷盘/罐/支撑在
50 mK--4 K 的热导、接触与冷却稳定性，0.5 mm Nb/Mu 在地磁/循环后的残余场与
磁通俘获，以及组合件的发射载荷/连接完整性必须一起通过。没有这份证据，本代理
可跑物理但不能发图加工。这里没有用“缺 CAD”逃避定义候选；几何 delta 已完全
冻结。

## 1. 基线权威与真实度边界

只读基线是：

`/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`

基线文件本身是 MEGAlib/Geomega **proxy**，不是 production CAD。源包 README
明确把质量账定义为 pre-relief shield-package bookkeeping、非整机/非结构资格，
并把 support/manufacturing closure 留在 transport model 之外（README
94--104、122--131 行）。在整个源工作树中未找到 STEP/STP/IGES/FreeCAD 或可认证
BOM；因此下面能证明的是 proxy 内可实现、无重叠与质量闭合，不能证明壁厚公差、
装配顺序、光学耦合或热/磁/结构性能。

还存在一个应显式保留的账本差异：源 README 的解析 BGO 账使用
`7.13 g cm^-3` 且为 pre-relief；实际 runtime material 查询是
`BGO=7.1`、`Copper=8.954`、`Aluminium=2.7`、`Nb=8.57`、
`MuMetal=8.7`、`BPE5=0.95 g cm^-3`。本报告和 `MASS_CLOSURE.csv`
使用实际 setup/runtime material 与 relief 后 CSG，不使用源注释中的
`4.44026391 kg` top-BGO pre-relief 数字。

## 2. 冻结的唯一几何 delta

| 子系统 | 精确改动 | proxy 质量：baseline -> candidate | 保留功能/边界 |
|---|---|---:|---|
| 48-volume cold core | 20 open-ring panels、1 solid disk、4 edge rods、4 off-axis fingers、4 stems、4 clamps、4 个 50 mK can 体积、MXC/100 mK/Still/4 K 四冷盘、DR mixing chamber/still pot/4 K condenser；形状与位置不动，`Copper -> Aluminium` | `20.273281 -> 6.113230 kg`；释放 `14.160051 kg` | 不改 signal aperture、不新建 volume/channel；名称中的 `Cu` 仅为兼容保留，实际 material 为 Al |
| Nb/Mu 磁屏蔽 | 主套筒与 back cap 从 2.0 mm 减到 0.5 mm；所有内半径、内端面与中心开口不动 | `0.928496 -> 0.225286 kg`；释放 `0.703210 kg` | 几何视场不变；磁性能是工程 blocker，不能由 overlap 代替 |
| inboard BPE | 新增 `Candidate_Inner_BPE5_Liner_5mm`；`r=20.65..21.15 cm`，`z=-19.4..40.9 cm`；复制 signal/pump/NF2 relief | `0 -> 3.744416 kg` | 现有 outer BPE `r=27..29 cm` **保留不动**；这是释放质量新增的同材料内衬，不是把外层拆走 |
| active top BGO | 同一 `BGO_S3D_O8_FullWrap_TopAnnulus_10mm` volume/channel；内表面固定 `z=40.9 cm`，外表面 `z=42.05684119 cm`；`r=4..25.2 cm`；中央 `r<4 cm` 与 12 个服务孔、6 个 NF2 relief 保留 | `4.355872 -> 15.474717 kg`；增加 `11.118845 kg` | `.det` 与基线 byte-identical；没有新增 guard、scorer 或 readout channel |

48 个材料替换名由 `CU_TO_AL_WHITELIST.txt` 唯一限定。候选明确保留 11 个
XS400 4 K--300 K/service/manifold Cu proxies 与
`PreCool_FlexLink_Cu_remote_interface`，共 12 个 excluded volumes。这样既不把
未知接口功能并入冷芯替换，也避免给没有 observed delayed credit 的额外 Al
activation host。候选输出在首末白名单体积上均可见 `Material Aluminium`
（candidate geo 11429--12612 行）；源几何对应 cold-support/can/plate/DR Cu
位于 11428--11881、12556--12617 行。

元素 `Aluminium` 是此 transport proxy 的唯一材料定义，不把它冒充 6061。
若工程最终只能接受 6061，必须先建立含 Mg/Si/Cu/Cr/Fe 的准确 alloy card，再将
它视为新的 activation comparator；不能沿用本候选的元素 Al 结论。

### 2.1 磁屏蔽的确切表面

- Nb sleeve：`rinner=4.00 cm` 不变，`router 4.20 -> 4.05 cm`，local
  `x=-3.85..4.10 cm` 不变。
- Mu sleeve：`rinner=4.25 cm` 不变，`router 4.45 -> 4.30 cm`，local
  `x=-4.35..4.30 cm` 不变。
- Nb cap：central opening `r=1.85 cm` 不变，outer `r 4.20 -> 4.05 cm`，
  local `x=4.10..4.15 cm`。
- Mu cap：central opening `r=1.85 cm` 不变，outer `r 4.45 -> 4.30 cm`，
  local `x=4.30..4.35 cm`。

候选 shape 定义见 candidate geo 11765、11774、11826、11835 行；源 2 mm
定义见 baseline geo 11765、11774、11826、11835 行。volume 名称中的 `2mm`
为 detector-reference 兼容而保留，不代表候选厚度。

### 2.2 BPE 内衬为何在这里

基线真空 jacket 外半径为 `20.6 cm`（baseline geo 12375--12464 行），侧 BGO
内半径为 `21.2 cm`，所以 proxy 有 6 mm 径向空隙。候选使用
`20.65..21.15 cm`，两侧各留 `0.05 cm` proxy clearance。其 37.96 mm
signal relief 使用 `BRIK` 半宽 `y=z=1.898 cm`，中心仍在 TES side-window
轴 `z=-5.2 cm`；另复制 pump 和六根 NF2 relief（candidate geo
17348--17410 行）。

现有 outer BPE 位于 `r=27..29 cm`（baseline geo 16360--16561 行），能先处理
外进入射中子，但 BGO 内产生并向冷芯走的次级中子、以及已经穿过外层的低/超热
中子，不会再走回 outer BPE。新增内衬把 `0.475 g cm^-2` 的 BPE 放在冷芯前的
最后一道被动层，目的是降低它们在 Nb/Mu/Al 冷端的 activation；它不声称能阻止
GeV neutron。直接 downside 是 B-10 capture 后 478 keV gamma 与 cascade/方向
重分配，必须在统一 BUILDUP/decay 中单列 Bq 与 W2/Bq。

### 2.3 top BGO 的真实服务孔

原始“把 top annulus 直接收至 `Rin=4 cm`、只留中央孔”的版本与真实顶管重叠，
已经 KILL。最终候选减去：

- GasReturn A：中心 `(5.0, 3.2) cm`，relief `r=1.95 cm`；
- PumpFill B：`(7.4, -2.8) cm`，`r=1.69 cm`；
- Vacuum C：`(-4.5, 6.5) cm`，`r=1.29 cm`；
- 9 根 micro conduits：中心
  `(-2.4,8.8), (-0.2,8.9), (2.0,8.8), (4.2,8.6), (6.4,8.3),`
  `(-1.3,10.9), (0.9,11.1), (3.1,10.9), (5.3,10.5) cm`，每孔
  `r=0.95 cm`。

基线真实管 envelope 在 geo 15934--16190 行；最终 relief 在 candidate geo
17265--17337 行。micro tube 主段只有 `r=0.64 cm`，但候选顶面进入其
`r=0.9 cm` top-sleeve axial envelope，故最终孔径使用 0.95 cm，而不是早期会
重叠的 0.69 cm。顶 BGO 外表面仍比现有 top wrapper 下表面低约 3.013 cm。

## 3. 质量闭合：正确精度

`MASS_CLOSURE.csv` 的 fixed-seed CSG 账如下：

| changed scope | baseline kg | candidate kg | delta kg |
|---|---:|---:|---:|
| 48 cold-core Cu/Al | 20.273280620 | 6.113229582 | -14.160051038 |
| Nb/Mu sleeves + caps | 0.928495682 | 0.225285914 | -0.703209768 |
| top BGO | 4.355872428 | 15.474717079 | +11.118844651 |
| inner BPE | 0 | 3.744416359 | +3.744416359 |
| **total** | **25.557648730** | **25.557648934** | **+0.000000203** |

这个 `+0.204 mg` 只是固定随机种子的名义数。MEGAlib
`MDShapeSubtraction::GetVolume()` 对 ROOT `Capacity()` 做 16 次平均，源码还明确
说明单次准确度只有约 1%（`MDShapeSubtraction.cxx` 172--183 行）。改变查询顺序
的独立审查曾得到 `-1.342 g`，其他 seed/order 也会有数克摆动。因此质量声明为
`25.558 kg` changed scope 上守恒到 `~few g`（约 `1.4e-4` 相对量级）。最终 CAD
solid 或实物称量可用约 1--3 micrometre 的 top-BGO 厚度修整消掉这一级残差；
这不改变 topology，也不应被写成物理证据。

## 4. 几何与功能验证

### 4.1 overlap 与 reference integrity

最终 setup 在 2026-08-14 重跑 Geomega/ROOT checker：

```
overlap_ok=1
No extrusions or overlaps detected with ROOT (ROOT claims to be able to detect 95% of them)
```

checker 扫描 3106 volumes 并返回 0；记录见 `OVERLAP_CHECK.txt`。这证明 proxy
CSG 没有发现 overlap，不等于 as-built 公差资格。

候选 `.det` 与 baseline `.det` byte-identical。top BGO 保留原 sensitive volume
名，原 detector block 仍直接绑定它，trigger threshold 仍为 80 keV（candidate det
1177--1183 行）。BPE 没有 detector/scorer；没有新增 active guard 或 readout。

### 4.2 信号光路

几何上信号视场保持：

1. 48-volume Cu->Al 只换材料，所有固体表面不动；
2. Nb/Mu 只向外表面减薄，inner surfaces 与 `r<1.85 cm` cap opening 不动；
3. BPE 精确复制 37.96 mm side-window relief；
4. top-BGO 变化位于顶面而不是负 local-x 的 side signal path。

独立 prompt 审查对 37,194 条 post-Be focused EventList 做真实 candidate CSG
射线，`0/37194` 与新增 BGO 相交、`0/37194` 与 plastic 相交；注入点 radial range
`13.100..13.168 cm`，已在 BPE 内半径 20.65 cm 之内。这个结果只证明没有几何
vignetting，不能替代 candidate 自己的 Aeff/S20 replay。

### 4.3 prompt partner 与 host migration

已知三条 baseline anti-TES annihilation partner 都先被内部被动材料吸收，首次
pair host 为 `Nb, Cu, Nb`。最终候选真实 CSG 给它们新增/保留 BGO chord：
`7.099 cm side`、`1.174 cm top`、`6.130 cm side`。这支持“减少冷端 partner
吸收 + 用现有 active BGO 接住”的几何机制，其中 top 事件原先在 local
`r≈9.31 cm` 穿旧中央开口。

但是这不是 veto 证明。`DR_MXC_Sinter_HEX_AgProxy` 不变；关键路径在原 DR Cu
后仍可穿约 `0.991 cm`、`rho=5 g cm^-3` 的 Ag proxy，另有 SS、保留 XS400 Cu、
candidate Al 与残余 Nb/Mu。候选必须在每条 history 中报告 first interaction/
first pair host、e+ stop/ANNI host、anti-TES sibling 在 BGO 的真实 edep 与
`>=50 keV` coupling。若 selected weight 迁到 Ag/SS/保留 Cu 或服务孔且仍无 veto，
直接 KILL；不得用 Al/Cu pair 系数比代替 transport。

### 4.4 delayed host migration

基线 exact-Copper 的 373 条 selected rows、59252.576459 mission counts 全部落在
本 48-volume scope；多改的 12 个 Cu volume 没有 observed credit。几何替换因此
命中已观测 cold hotspot，但候选会新建约 6.113 kg near-TES elemental-Al host。
focused BUILDUP/decay 必须分开给 n/p/alpha 的 production rate、day-15 Bq、
exact-position `W2/Bq`、mission counts、event/position Neff 与最大单事件份额。
Al activation、BPE capture gamma 或残余 Nb/Mu coupling 任一吃完联合预算即 KILL。

## 5. KEEP / MODIFY / KILL 收敛

这些是同一个候选的审查处置，不是平行菜单：

| 处置 | 对象 | 原因 |
|---|---|---|
| **KEEP** | 最终 48-volume + mag0.5 + inner-BPE + relieved top-catch 的统一 proxy | 唯一同时作用于已知 Cu/Nb pair/activation hosts、被动 partner absorption 与 top active escape 的简单质量闭合拓扑 |
| **MODIFY 已完成** | raw `Rin=4 cm` solid top catch | 加入 3 大 + 9 micro + 6 NF2 真实 relief，避免顶管 overlap |
| **MODIFY 已完成** | 60-volume blanket Cu->Al | 收缩为 exact 48 whitelist；12 个无 observed delayed credit 的 service/interface Cu 保留 |
| **KILL** | 无服务孔 top disk、旧 60-volume prototype、改 signal side-window、增加 channel/guard、把元素 Al 叫 6061 | 分别违反真实几何、增加 activation/接口风险、损害光路或越过硬约束 |

## 6. 下一步唯一 focused 证伪链

此工程审查未跑 transport。候选只应按下列顺序推进：

1. paired prompt mechanism test：使用有分母的 gamma INIT states，逐 history 查
   primary transmission、pair/ANNI host、Ag/SS/remaining-Cu migration、partner
   BGO `>=50 keV`；不得从 3 个 survivor 外推全天角；
2. 48-volume elemental-Al isolated BUILDUP + exact-position decay，再跑统一候选
   affected-material n/p/alpha；保持 geometry x mode x family TT 边界，分别报告
   production Bq 与 W2/Bq，并显式标记低 Neff/单事件权重；
3. 同一 37,194 focused EventList 的 baseline/candidate signal replay，重算候选
   `S20` 与自己的 background gate；
4. 只有前三项通过，才做 corrected-gamma confirmation；corrected gamma 已含
   annihilation bump，不另加 mono-511，也不先跑全八族盲链。

物理 promotion 的唯一联合问题是：把 new-Al activation、Ag/SS/remaining-Cu
host migration、inner-BPE secondary/capture gamma 与真实 partner-BGO threshold
coupling 一起计入后，candidate 的置信上界是否仍满足其自身 S20 gate，并达到
central `F3 <= 3e-5 photon cm^-2 s^-1`。若否，本候选 KILL；约束内没有第二个
平行工程推荐。

## 7. 可复现产物

- `build_unified_candidate_proxy.py`：从只读 S3d-O8 基线生成唯一 proxy；强制
  48-volume material scope、0.5 mm shields、服务孔 top BGO 与 inner BPE。
- `CU_TO_AL_WHITELIST.txt`：精确 48-volume 白名单。
- `MASS_CLOSURE.csv`：fixed-seed CSG 质量账与数值精度警告。
- `query_volume_mass.cc`：每 volume stable seed，避免命令行顺序改变名义结果。
- `check_geometry_overlaps.cc`、`OVERLAP_CHECK.txt`：最终 CSG overlap 证据。
- `candidate_proxy/`：唯一 setup/geo/det/material/intro；未复制任何 GB 级缓存。

