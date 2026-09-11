# S3d-O8 thermal-Cu rethink：最终几何与必要性审查

## 最终结论

**最终判决：`NO_ADMISSIBLE_CANDIDATE`。不要冻结任何现有 proxy 为统一候选，也不要启动 transport。**

几何上，`BG-J4` 可以被精确定义、保持全部 cold-core Cu/Ni/Nb/Mu 不动，并通过 ROOT overlap；但它作为 prompt+delayed 统一方案已被同一 420-row selected-W2 分母上的 actual-IA 分支直接证伪。`Cu65-48` 也能加载且质量守恒，但 delayed 守恒审查已 KILL isotope-only 机制。因此，“proxy 可加载”不等于“物理候选可晋级”。

唯一统一 blocker 是：**绝大多数 delayed 511 sibling 在冻结的 cold core 内已经被吸收或降能，只有 `10.5925%` mission weight 的 `>=50 keV` gamma 到达 current-BGO/outer-region proxy，而 BG-J4 联合门需要 `91.6767%` 有效耦合。** 外层 BGO 再厚也不能把已经消失的 sibling 变成 veto；允许范围内又没有一个通过守恒审查的 cold-core production 材料替代。

本报告把证据分成三类：真实 `.geo`/CSG/ROOT 结果为 `FACT`；418 条 straight-ray chord 为 `GEOMETRY OPPORTUNITY CEILING`；actual IA、selected-W2 mission weights 与联合预算为 `PHYSICS FALSIFIER`。没有把 3 条 prompt survivor 或低 Neff delayed 热点外推到全天角。

## 1. 冻结 cold core 后的局部拓扑结论

19932-class anti-TES 直线在 CP、Still、4K 冷盘上的交点半径为 `2.528/3.467/4.940 cm`。冷盘允许的最小半径仍为 `11.25/11.25/13.125 cm`，所以 OD 缩小 25% 不会移除这些中央交点。厚度最多减小 10% 后，三盘仍给出：

| quantity | value |
|---|---:|
| CP+Still+4K Cu chord | `1.643462 cm` |
| Cu grammage | `14.7156 g cm^-2` |
| `exp(-0.749 L_Cu)` 仅标度 | `0.2920` |
| 再计 DR-Cu exit chord | `2.286788 cm` |
| 对应仅标度 | `0.1804` |

这些数还没有计入约 `4.768 cm` SS service stack。少量 M4 孔若按三条历史射线布置，只会成为 post-selected event hole，不能定义有分母的接受域。

当前闭合 Nb/Mu 壳中心 `z_IF=-5.2 cm`、Mu 外半径 `4.45 cm`。其上缘到 MXC 盘只有 `0.45 cm`，下缘到 50 mK can bottom 只有 `0.05 cm`。同心扩大到 R=8--10 cm 会直接穿 MXC；向下避开 MXC 又会穿 can bottom、多温级 caps 与现有 W bottom plate。因此 DR/Nb/Mu standoff 8--10 cm 是真实包络 `KILL`，不是因缺 FEM 暂缓。

L0 开框、can-bottom 薄 skin 等局部 Cu topology 在解析几何上可做，但它们不解除上述中央冷盘 blocker，不能成为平行候选。

## 2. BG-J4：精确 proxy 与工程闭合

### 2.1 冻结定义

`BG-J4` 只改现有外层，cold core、全部 60 个 natural-Copper volume、CuNi、Ag、Nb/Mu、W、冷盘尺寸和 source positions 均为 baseline：

- BGO side：`R=21.2--25.2` 改为 `21.2--29.2 cm`，内表面和轴向 cavity 不动；
- BGO bottom：内表面保持 `z_IF=-19.4 cm`，改为 `R_out=29.2 cm`、厚 `7 cm`，外表面到 `-26.4 cm`；
- BGO top：内表面保持 `z_IF=40.9 cm`，改为 `R_out=29.2 cm`、厚 `5 cm`、基础 `R_in=0`；旧大孔关闭，只扣 12 个真实 service envelope 和 6 个 NF2 relief；
- 12 个 top-service relief 按候选所穿的最大 tube/sleeve 半径加 0.5 mm：GasReturn/PumpFill/Vacuum 为 `2.45/2.15/1.69 cm`，9 个 micro-conduit 为 `0.95 cm`；
- Kapton/Al/BPE/plastic 侧壳径向外移 4 cm，侧壳半高同步增加 4 cm，端盖轴向外移 4 cm，保持各自厚度、volume 名和 detector/scorer mapping；最终外半径 `34 cm`；
- frozen side optical aperture 贯穿 BGO/Kapton/Al/BPE/plastic；既有 pump 与 6 根 NF2 rod relief 保留，新增 NF2 mount-annulus relief 只用于消除实际 support overlap。

这样 side 与 bottom/top 在 oblique corner 处是闭合 PCON，而不是在角点留下零新增 chord 的 L 形裂缝。

### 2.2 ROOT overlap 与现有通道

候选 setup：

`agents/geometry/bg_j4_proxy/S3D_O8_BG_J4_fullwrap_BGO4cm_proxy.geo.setup`

Geomega 全部 12 stages 通过；ROOT 检查 3105 volumes，最终 `overlap_ok=1`、无 extrusion/overlap。BGO 和 plastic 沿用原 volume 名及原 `.det` scorer，没有新增 detector、guard、channel 或 readout。

第一版检查曾准确找出外移 3 mm Al caps 与 NF2 base/top mount annuli 的 `0.453245/0.084871 cm` overlap；加入对应真实 mount relief 后才得到最终 PASS。进一步把外层 side half-height 同步延长 4 cm，消除了 overlap 工具本身不会报警的轴向 4 cm 壳断口。

### 2.3 稳定 CSG 质量账

| volume group | baseline kg | BG-J4 kg | delta kg |
|---|---:|---:|---:|
| BGO side | 249.195918 | 543.495521 | +294.299602 |
| BGO bottom | 42.426628 | 131.776765 | +89.350137 |
| BGO top | 4.355872 | 90.409902 | +86.054030 |
| **BGO total** | **295.978418** | **765.682188** | **+469.703769** |
| shifted Kapton/Al/BPE/plastic total | 64.574301 | 82.500946 | +17.926645 |
| **all modified outer layers** | **360.552719** | **848.183134** | **+487.630415** |

这是真实 subtraction 后的 CSG 查询，不是先前忽略 corner fill/relief 的简化质量标度。它不包含 support reinforcement、光收集或 payload 结构增量。

## 3. 418 条 delayed sibling 的 chord/relief 分母

从 420 条 selected delayed lineage 中，418 条具有唯一 TES-annihilation sibling，覆盖 `99.9672%` mission counts。对这 418 条原点和方向，用 BG-J4 自己的 setup 做 straight-ray trace：

| metric / traceable418 | rows | mission fraction | Neff | dominant-event fraction |
|---|---:|---:|---:|---:|
| baseline any BGO chord | 388 | 86.2844% | 24.88 | 6.55% |
| BG-J4 any BGO chord | 418 | 100.0000% | 28.67 | 5.65% |
| BG-J4 added BGO chord >=4 cm | 413 | 99.8617% | 28.59 | 5.66% |
| explicit relief/aperture, added chord <4 cm | 5 | 0.1383% | 5.00 | 20.02% |

五条 relief rows 没有被热图平滑掉：

| family:event | mission counts | added BGO chord cm |
|---|---:|---:|
| eplus:78728 | 24.584013 | 3.440067 |
| eplus:92410 | 24.584013 | 0.750863 |
| eplus:93577 | 24.584013 | 0.000000 |
| eplus:230478 | 24.584013 | 0.324222 |
| eplus:30501 | 24.453350 | 3.714324 |

这些结果只证明“若一条 511 仍存在并沿初始方向无散射飞出，它会遇到多少 BGO”。它们不是 veto efficiency，也不能给已经在 cold core 中发生 COMP/PHOT/降能的分支套 `exp(-mu L)`。

机读输出：`BG_J4_DELAYED_SIBLING_CHORDS.csv`、`BG_J4_DELAYED_RELIEF_DENOMINATOR.csv`、`BG_J4_DELAYED_RELIEF_HOTSPOTS.csv`、`BG_J4_DELAYED_RELIEF_SEGMENTS.csv`。

## 4. BG-J4 unified KILL 的直接物理证据

BG-J4 反事实联合式要求至少 `q=91.6767%` delayed mission counts 有效耦合到新增 BGO。baseline selected-W2 的 actual IA 分支却给出：

| actual branch predicate / all420 | mission fraction | Neff |
|---|---:|---:|
| `>50 keV` escape gamma exists | 8.4393% | 1.88 |
| `>=50 keV` gamma reaches current-BGO/outer-region proxy | 10.5925% | 2.65 |
| IA point enters active | 2.2190% | low |

这些比例因 Neff 低不能当精密效率，但 `10.5925% << 91.6767%` 足以证伪所需机制。甚至把所有 outer-reach rows **完美删除**，联合 residual 仍为 `97765.4 counts`，远高于 `27341.9` gate。

因此：

- `BG-J4` geometry：`PASS / retained as a geometry-only sensitivity artifact`；
- `BG-J4` prompt-only +4 cm sensitivity：可选诊断，但不是统一候选；
- `BG-J4` delayed exponential credit：`KILL`；
- `BG-J4` unified topology：**`KILL; DO NOT RUN`**。

## 5. Cu65-48：几何 PASS，材料机制 KILL

在 delayed KILL 通知到达前已生成最小 geometry-only proxy：

`agents/geometry/cu65_48_proxy/S3D_O8_coldcore48_Cu65_same_density_proxy.geo.setup`

它只把冻结 whitelist 的 48 行 `.Material Copper` 改为 `Copper65`；其余 12 个 natural-Copper volume、CuNi、所有尺寸/位置和 scorer 均不变。材料定义为密度 `8.954 g cm^-3`、`ComponentByAtoms 65 29 1`。检查结果：

- source/candidate `.geo` 恰有 48 个不同 material-reference 行；
- candidate 仍有 12 个 `.Material Copper`，有 48 个 `.Material Copper65`；
- paired CSG query：48-volume volume `2264.159104 cm3`，baseline 与 candidate 均为 `20.273280620 kg`；
- Geomega load 与 ROOT overlap PASS。

但 delayed 独立守恒审查给出：known 63Cu capture 的最大 credit 仅约 `14.86% D`，65Cu channels 同时放大；known-channel proxy 净收益只约 `3.70% D`，并有未闭合的多中子/Cu-66 风险。故 `Cu65 isotope-only = KILL`，没有启动 Cosima/BUILDUP transport。

另外，MEGAlib numeric component 确实设 `HasNaturalComposition=false` 并在 Cosima 中构造 `G4Element(Z,A)`；它没有显式构造 `G4Isotope`。在专门的 isotope-target 单元测试前，不应把 Geomega load PASS 冒充 activation target 语义认证。这一点现在不再是决策 blocker，因为守恒审查已经先行 KILL 该路线。

## 6. 最终 KEEP / MODIFY / KILL

| topology | verdict | direct falsifier |
|---|---|---|
| 48 cold-core Cu -> Al | KILL | 用户冻结 Cu/Ni 热/结构功能；旧 proxy 仅保留 provenance |
| cold-plate skeletal/spoke | KILL | 违反 OD<=25%、t<=10%、少量 M4 边界 |
| event-directed M4/chimney | KILL | post-selected 三射线，无全天角分母 |
| DR/Nb/Mu R8--10 cm standoff | KILL | 穿 MXC/caps/W，或超 R15/service envelope |
| L0/can/service + local top catch | KILL AS SYSTEM | 19932-class 中央冷盘 chord 不变 |
| BG-J4 +4 cm full-wrap BGO | KILL AS UNIFIED | actual outer-reach 10.59%，需要 91.68% |
| Cu65-48 isotope-only | KILL | known-channel 净 delayed credit 3.70% D，65Cu/unknown channels 风险 |
| >=ln5 existing-channel BGO + outer BPE | NOT A PROVEN UNIFIED CANDIDATE | 可作为 prompt 条件拓扑，但 BGO 不得领取已证伪的全 delayed coupling；仍缺独立 delayed suppression |

## 7. 所有生成 proxy 的冻结状态

1. `reconsideration_20260814/agents/geometry/candidate_proxy/S3D_O8_unified_Al_mag05_innerBPE_topcatch_proxy.geo.setup`  
   `STALE / KILL`：48 Cu->Al 违反后续 thermal-Cu 冻结边界。
2. `thermal_cu_rethink_20260814/agents/geometry/bg_j4_proxy/S3D_O8_BG_J4_fullwrap_BGO4cm_proxy.geo.setup`  
   `GEOMETRY PASS, UNIFIED KILL`：可复现 mass/relief 审查，不得用于统一 transport。
3. `thermal_cu_rethink_20260814/agents/geometry/cu65_48_proxy/S3D_O8_coldcore48_Cu65_same_density_proxy.geo.setup`  
   `GEOMETRY PASS, PHYSICS KILL`：在停止通知前生成，仅作审计，不得运行。

没有生成 cold-plate skeletal proxy；它在概念阶段即被新机械边界 KILL。

## 8. 可追溯源

- 真实 S3d baseline：`geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`。
- TES/L0/support：源 `.geo` 行 11374--11758；Nb/Mu、50 mK can、冷盘：11762--11898。
- DR Cu/Ag/CuNi/NbTi/G10：12557--12742；top service：15934--16190；BPE/BGO/plastic：16366--17270。
- BG-J4 联合物理反证：`agents/prompt/BG_J4_JOINT_GATE_REVIEW.md`、`bg_j4_actual_branch_falsifier.csv`、`bg_j4_joint_gate_audit.csv`。
- 生成器：`build_bg_j4_proxy.py`、`trace_bg_j4_delayed.py`、`build_cu65_48_proxy.py`。

## 9. PA-X1 五面局部被动准直：追加硬 KILL

聚焦 signal 轴可保留一个真实方孔：37,194 条 post-Be rays 在
`x_IF=-3.80--3.235 cm` 内有 `max|y|=1.44345 cm`、
`max|z_IF+5.2|=1.36124 cm`，而 Si/support 实体要求方孔半宽不小于
`1.85 cm`。但 Nb 内半径只有 `4.0 cm`：方孔面中心最大 Cu 厚度
`2.15 cm`，方形角点只有 `1.3837 cm`。因此无论是 `+4 cm BGO`
在 baseline-S20 gate 下所需 `3.140091 cm`，还是 `BG-TAU5` 所需
`2.308064 cm` uniform rejected-ray
Cu chord 都不能实现。

x+ 面 L0 厚 `0.35 cm`；吃掉 L5--L0 的 `0.05 cm` 和
L0--cold-finger 的 `0.01 cm` 全部间隙也只有 `0.41 cm`。z+ 的
Mu--MXC 间隙仅 `0.45 cm`，z- 的 Mu--can 间隙仅 `0.05 cm`。
冷盘 OD/t 取用户允许极限不改变这些内孔硬界。即使把 Nb 内孔方孔
以外零间隙全填 Cu，并严重过度给 L0/can credit，delayed 乐观抑制
上限仍只有 `62.7748%` all-420，留下 `0.0202802 cps`；就算 prompt
完全归零也高于 baseline-S20 门 `27073.008579 counts`（同 exposure
约 `0.0160095493 cps`）。

所以 `PA-X1 = KILL`，未生成 proxy、未跑 transport。完整切片、质量下限和
机读门表见 `PA_X1_LOCAL_COLLIMATOR_ADDENDUM.md` 与
`PA_X1_FIVE_FACE_GEOMETRY_GATES.csv`。
