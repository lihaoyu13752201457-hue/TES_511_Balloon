# S3d-O8 去除磁屏蔽与“铜盒”：真实几何短审查

## 结论先行

真实 S3d `.geo` 中没有名为 `CuBox` 的 volume。“铜盒”有两个合理解释：

1. **最字面的局部外壳**是四件式 `Cu_50mK_StillLike_Can_*`；
2. **TES 近端的方形 Cu enclosure/cage**是 `Cu_SubstrateSupport_*`，其中又必须区分仅一块 `L0_deepest` 背板和完整的 20 块开框 panel + 4 根 edge rod + L0 背板。

按“磁屏蔽盒”=完整 Nb inner cylinder/back cap + Mu outer cylinder/back cap，且全部冷盘保持 baseline：

- `can + mag`：**几何 KEEP / 工程有条件**。删除后不碰撞，TES--L0--cold-finger--MXC 支撑链仍在；但失去 50 mK 辐射/热外壳和全部磁屏蔽，两个局部 Al foil 失去载体。它是三个解释中唯一没有直接切断冷指热/机械链的一个，但还不是可跑的物理候选。
- `L0 enclosure + mag`：**KILL**。无论只删 L0 背板还是删完整 cage，都会切断 TES/support 到四根 cold finger 的唯一建模接口；完整 cage 删除还会使六块 Si/TES stack 在物理上悬空。
- `can + L0 enclosure + mag`：**STRONG KILL**。同时丢失 detector support/thermal link、50 mK enclosure 和磁屏蔽。

## 1. volume、尺寸与 CSG 质量

质量由 baseline setup 的真实 Geomega subtraction 后 CSG 查询得到，不是解析外包络估算。源为：

`/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`

| 解释 / volume scope | 真实尺寸与位置（InstrumentFrame） | volume cm3 | mass kg |
|---|---|---:|---:|
| 50 mK Cu can：4 个 `Cu_50mK_StillLike_Can_*` | z 轴圆筒；`Rout=15.3 cm`、wall/bottom `t=0.2 cm`；`z_IF=-9.9..-0.3 cm`；负 x 侧 `3.796 x 3.796 cm` 窗 | 324.119484387 | **2.902165863** |
| L0 narrow：仅 `Cu_SubstrateSupport_SolidDisk_L0_deepest` | `4.4 x 4.4 x 0.35 cm`，`x_IF=3.245..3.595 cm` | 6.776000000 | **0.060672304** |
| L0 broad enclosure：上述背板 + 20 panels + 4 rods | 五个 `4.4 x 4.4 cm` 外包络开框，轴厚 `0.30 cm`，位于 `x=-2.65..2.15 cm`；四根 `5.885 cm` 长、`0.1414 x 0.1414 cm` 边杆；加 L0 背板 | 14.512800000 | **0.129947611** |
| Nb inner：cylinder + back cap | x 轴；`R=4.0..4.2 cm`，cylinder `x=-3.85..4.10 cm`；cap `x=4.10..4.30 cm`、中心孔 `r=1.85 cm` | 49.893203728 | **0.427584756** |
| Mu outer：cylinder + back cap | x 轴；`R=4.25..4.45 cm`，cylinder `x=-4.35..4.30 cm`；cap `x=4.30..4.50 cm`、中心孔 `r=1.85 cm` | 57.575968562 | **0.500910926** |
| **完整 magnetic box** | 上述 4 个 Nb/Mu volume | 107.469172290 | **0.928495682** |

两块相关的 Al window foil 各为 `3.796 x 3.796 x 0.0025 cm`、`0.097265 g`：`Win_50mK_Al_foil_side` 位于 `x=-15.2 cm`，`Win_MagShield_Al_foil_side` 位于 `x=-4.35125 cm`。它们不计入上表 Cu/Nb/Mu 主质量，但相应壳被删后必须一并删除或明确 rehost；两块合计仅 `0.000194530 kg`。

源行：Si stack `.geo:11374--11425`；L1--L5 panels/L0/rods `.geo:11427--11650`；cold fingers/clamps `.geo:11652--11758`；Nb/Mu/can `.geo:11762--11846`；50 mK foil `.geo:12502--12509`。另有一个远端 `XS400_Group2_Cu_Coarse_ServiceCan_60K300K`（`.geo:12133--12139`，z 约 30.8 cm），不属于这里的 TES 近端“铜盒”，不应被误删。

## 2. 删除后的真实空域与接口

### 2.1 删除 can + magnetic box

这些 volume 的 `.Mother` 都是 `InstrumentFrame`，TES、support 和 cold fingers 不是它们的 child。因此纯 CSG 删除会把原实体变为 vacuum，不会产生新 overlap 或 extrusion，也不会使 Geomega 的 volume tree orphan。

但物理边界会改变：

- can 删除后形成 `R<15.3 cm, z=-9.9..-0.3 cm` 的开放 50 mK core；外侧 Still Al shield 内表面在 `R=15.5 cm`，径向只隔 `0.2 cm`；其 bottom 内表面在 `z=-10.4 cm`，与原 can bottom 外表面相隔 `0.5 cm`。所以 TES/core 直接看见 Still-stage enclosure，而不是保留一个闭合的 50 mK 辐射边界。
- Nb/Mu 删除后，原 `R=4.0..4.45 cm` 的侧壁和 x+ back caps 全部成为 vacuum；front 本来就是 open。TES/Si、L0 cage 和四根 cold finger 仍保持原坐标，没有碰撞，但失去横向/背向磁屏蔽。
- L0 背板仍为 `x=3.245..3.595 cm`；四根 off-axis cold finger 从 `x=3.605 cm` 开始并继续接到 MXC。两者仅有 `0.010 cm` 代理建模间隙，故这条热/机械链在该删除组合中仍闭合于原拓扑。

### 2.2 删除 L0 enclosure + magnetic box

若“L0 铜盒”只指背板，删后 edge rods 终点 `x=3.235 cm` 到 cold fingers 起点 `x=3.605 cm` 之间变成 **0.370 cm 真空断口**。若按完整 enclosure 删除，20 个 layer frames、4 rods 和背板都消失，六块 Si/TES stack 虽因共享 `InstrumentFrame` 仍能被几何加载，却没有任何建模支撑或到 cold fingers 的热接口。这不是 overlap 问题，而是结构/热闭合直接失败。

### 2.3 三者全删

不会因“删实体”产生几何碰撞，但形成上面两类失效的并集：Si/TES 物理悬空，cold fingers 在 `x=3.605 cm` 处无 detector-side collector，同时 50 mK core 对 Still shield 开放且 Nb/Mu 屏蔽消失。冷盘本身坐标和质量完全没变，不能补回这些近端接口。

## 3. 低 Z、非磁、低热导替代是否等价

现有材料表已经定义 G10，`rho=1.85 g cm^-3`。同形替代的几何与质量尺度为：

| same-shape G10 proxy | mass kg | 能保留什么 | 不能保留什么 |
|---|---:|---|---|
| 50 mK can | 0.599621046 | 外包络、窗口载体、机械防护的代理 | 低温等温热沉、低发射率辐射屏蔽；必须另有热化/表面方案 |
| 完整 L0 enclosure | 0.026848680 | 可能保留几何支撑包络 | Cu 的 TES-to-cold-finger 热导；同形绝缘替代不功能等价 |
| Nb+Mu shell/caps | 0.198817969 | 仅能保留壳/foil carrier 包络 | 磁屏蔽；非磁材料按定义不能替代 Nb/Mu 功能 |

因此，不扩展 scope 时不存在一个同时功能等价的“全低 Z、非磁、低热导”替代。对 `can + mag`，同形 G10 can 最多可作为 **机械/窗口 carrier sensitivity**，仍需单独证明辐射热负荷和 TES/SQUID 磁容限；对任何含 L0 删除的方案，若再加 Cu/Al heat strap 才能恢复热链，那已经不是同形非导热替代，也超出了本次简单删除。

## 4. 三个候选的冻结 verdict 与质量

| candidate | 删除的主实体质量 kg | 几何/工程 verdict | 直接 falsifier / 唯一下一门 |
|---|---:|---|---|
| `DEL-CM`: 50 mK can + full Nb/Mu | **3.830661546** | **GEOMETRY KEEP / ENGINEERING-CONDITIONAL** | 无碰撞且 L0/cold-finger 链保留；但必须用真实磁场容限和新增 50 mK 辐射热负荷证明可以放弃两套 shield，并明确 rehost/remove 两块 foil |
| `DEL-LM`: broad L0 enclosure + full Nb/Mu | **1.058443294** | **KILL** | TES/support-to-cold-finger 结构与热接口消失；即便 narrow 只删 L0 背板，质量为 `0.989167986 kg`，仍留下 `0.370 cm` 断口 |
| `DEL-CLM`: can + broad L0 enclosure + full Nb/Mu | **3.960609157** | **STRONG KILL** | 同时触发 detector support/thermal、50 mK radiation enclosure、magnetic shielding 三重失效 |

`DEL-CM` 只是三者中唯一可定义的简单几何 sensitivity，不代表 prompt/delayed 最优或允许直接 transport。若后续生成 proxy，必须同时删/改 `.det` 中所有对应 `_SD.SensitiveVolume/DetectorVolume` block，否则 setup 会因悬空 scorer 引用失效；本轮未生成 proxy、未跑 transport。

## 5. 明确 UNKNOWN

- 源包没有可认证的真实 CAD fastener、window clamp、wire strain relief、接触热阻或机械载荷树；上述“功能”由 volume 名和相邻包络推断。
- 没有 TES/SQUID 允许磁场、50 mK stage 允许辐射热负荷、G10 differential-contraction/FEM 或振动资格数据。
- 所以 `DEL-CM` 的唯一工程 blocker 不是几何空域，而是 **移除 Nb/Mu 与 Cu can 后的磁噪声 + 50 mK 热负荷联合认证**；这两项未证实前只能保持 conditional，不能称为可飞方案。
