# S3d-O8 近场本底与边缘像素切选分析

## 结论先行

这份结果只针对 **S3d-O8**，不是 Mass_model_511。几何沿 InstrumentFrame 相对 World 的 (+45^\circ) Y 旋转保持不变；近场图使用原生 Cosima/Geant4 CSG mesh 在 (y'=0) 的真实相交线。

1. **FACT — 近场确实主导当前 delayed W2。** full delayed W2 为 0.0544797522 cps；其中 Copper、Nb、MuMetal 分别占 66.77%、16.89%、14.25%。最大单体是 MXC 50 mK Cu plate，占 full delayed W2 的 30.78%。这些是“产生率 × 精确位置到 TES 的耦合”后的 detector-selected W2 份额，不是材料质量或活度份额，也不能直接当作减材收益。
2. **FACT — 软件级边缘事件切选能降低当前中心最小可分辨通量。** 采用能量加权的固定 TES 像素中心，绕 focused axis ((y',z')=(0,-5.2\ \mathrm{cm})) 作 (r\le1.35\) cm 的 event-level centroid gate，可保留 (f_S=0.986896) 的 focused signal，同时保留 (f_B=0.576014) 的匹配 20 天背景。中心 (F_{3\sigma}) 从 (6.92375\times10^{-5}) 降到 (5.32459\times10^{-5}\ \mathrm{ph\ cm^{-2}\ s^{-1}})，改善 23.10%。
3. **INFERENCE — 一级建议是保留所有像素读出，只在分析中先用 (r\le1.35) cm centroid gate。** 这比关掉边缘通道更可逆，也不改变 W2 能量和多像素拓扑。若完全不给“删掉 prompt root”任何信用，仍得到 (6.14864\times10^{-5})，比 baseline 改善 11.20%。
4. **UNKNOWN — 不能把更激进的低半径最小值当成物理晋级。** baseline prompt 只有两个等权 root；它们在 (r=1.096) 和 1.404 cm 形成离散台阶。(r=1.05) cm 的表观 (3.58170\times10^{-5}) 主要利用 prompt 2→0 的量子悬崖，尚无稳定统计支持。任何已审计切选都没有达到 (3\times10^{-5}) 目标。

## 图与可复核数据

- [S3d-O8 近场真实剖面与活化点（PNG）](figures/s3d_o8_nearfield_activation_detail.png)
- [S3d-O8 近场真实剖面与活化点（SVG）](figures/s3d_o8_nearfield_activation_detail.svg)
- [边缘像素灵敏度曲线（PNG）](figures/s3d_o8_edge_pixel_sensitivity.png)
- [边缘像素灵敏度曲线（SVG）](figures/s3d_o8_edge_pixel_sensitivity.svg)
- [本底来源汇总 CSV](data/agent_background_source_summary.csv)
- [边缘切选合并扫描 CSV](data/edge_pixel_fiducial_scan.csv)
- [边缘切选验证 JSON](audit/edge_pixel_fiducial_validation.json)

近场图左侧的几何线是 (y'=0) 的真实切面；66 个活化点则保持 ledger 的精确三维 decay-source 坐标，再正交投影到 (x'-z')。每个主要标签同时给出真实 (y') 偏移，因此投影点不应被误读为“核素就在切面内”。黑边点至少存在一个精确 production-origin link；白边点的直接生产粒子/过程仍未扫描或未链接。prompt 折线来自已记录 IA/CC 顶点，不是完整 Geant4 step path。

## 本底主要来源

### 总体 W2

| 流 | W2 率 [cps] | 合计份额 | 事件行 | 事件 Neff | 证据 |
|---|---:|---:|---:|---:|---|
| delayed full | 0.0544797522 | 61.68% | 420 | 28.754 | FACT |
| prompt official Step05 | 0.0338429281 | 38.32% | 2 | 2.000 | FACT；强量子化 |
| 合计 | 0.0883226804 | 100% | 422 | — | FACT |

### delayed：按精确材料

| 材料 | selected W2 [cps] | full delayed W2 份额 | 行数 | Neff | 解释 |
|---|---:|---:|---:|---:|---|
| Copper | 0.0363761284 | 66.77% | 373 | 22.458 | 60 个 exact-Copper 几何体的 detector-selected 贡献 |
| Nb | 0.00920149 | 16.89% | 25 | 3.764 | 主要来自 inner magnetic shield |
| MuMetal | 0.00776545 | 14.25% | 20 | 2.934 | 主要来自 outer magnetic shield |
| SilverSinterProxy | 0.00112166 | 2.06% | 1 | 1.000 | 单事件量子 |
| CuNi | 0.0000150194 | 0.03% | 1 | 1.000 | 很小 |

权威 `.Material` 中的全 Copper ground-state inventory 为 161.957683 Bq。旧的 112.251 Bq 是 name-prefix 的近芯 scope，并非全 Copper material total。

### delayed：按局部几何体

| 排名 | source volume | selected W2 [cps] | full delayed W2 份额 | 行数 | Neff/警告 |
|---:|---|---:|---:|---:|---|
| 1 | `ColdPlate_MXC_50mK_SD_anchor` | 0.016771 | 30.78% | 57 | Neff 8.733 |
| 2 | `Nb_MagShield_Inner_Cylinder_2mm` | 0.007809 | 14.33% | 24 | Neff 2.967 |
| 3 | `MuMetal_MagShield_Outer_Cylinder_2mm` | 0.007765 | 14.25% | 20 | Neff 2.934 |
| 4 | `Cu_SubstrateSupport_SolidDisk_L0_deepest` | 0.005850 | 10.74% | 93 | Neff 4.409 |
| 5 | `Cu_50mK_StillLike_Can_bottom_cap_2mm` | 0.004016 | 7.37% | 11 | Neff 3.137 |
| 6 | `Cu_SubstrateSupport_OpenRing_L5_ZM_panel` | 0.003050 | 5.60% | 1 | 单事件量子 |
| 7 | `Cu_SubstrateSupport_OpenRing_L4_ZP_panel` | 0.001742 | 3.20% | 116 | 很多小权重行 |
| 8 | `Cu_SubstrateSupport_OpenRing_L2_ZP_panel` | 0.001393 | 2.56% | 1 | 单事件量子 |
| 9 | `Nb_MagShield_Inner_Back_ColdFingerCap_2mm` | 0.001393 | 2.56% | 1 | 单事件量子 |
| 10 | `ColdPlate_CP_100mK_intercept` | 0.001323 | 2.43% | 20 | Neff 1.386 |

### delayed：按 TES 实际探测到的母核素

| 核素 | selected W2 [cps] | full delayed W2 份额 | 行数 | Neff/警告 |
|---|---:|---:|---:|---|
| Cu-62 | 0.015590 | 28.62% | 278 | Neff 10.922 |
| Cu-64 | 0.012420 | 22.80% | 18 | Neff 7.166 |
| Cu-61 | 0.006988 | 12.83% | 77 | Neff 3.699 |
| Fe-53 | 0.003050 | 5.60% | 1 | 单个 p-family 事件 |
| V-46 | 0.003050 | 5.60% | 1 | 单个 p-family 事件 |
| Y-85 | 0.003050 | 5.60% | 1 | 单个 p-family 事件 |
| Zr-85 | 0.003050 | 5.60% | 1 | 单个 p-family 事件 |

Cu-61/62/64 合计占 full delayed W2 的 64.73%。Fe-53、V-46、Y-85、Zr-85 的相同 5.60% 不是四条稳定、精确的物理比例，而是同一类高权重单事件量子化的表现。

### prompt：两条 Step05 链

| root | pair host | annihilation host | W2 [cps] | 证据 |
|---|---|---|---:|---|
| 3883 | `Nb_MagShield_Inner_Cylinder_2mm` | `MuMetal_MagShield_Outer_Cylinder_2mm` | 0.0169214641 | FACT；nearest recorded CC host |
| 19932 | `DR_MixingChamber_Cu` | `DR_MixingChamber_Cu` | 0.0169214641 | FACT；nearest recorded CC host |

“nearest recorded CC host”不是完整 transport path；它足以标定观测到的 pair/annihilation 拓扑，但不足以证明移除该 host 后事件会消失，因为 pair host 可能迁移到相邻 Nb/Cu/Ag/MXC 几何体。

### 直接生产粒子/过程的证据边界

- **FACT：** 420/420 delayed 行都可连接到 event/source/material/inventory 和精确 decay 坐标。
- **FACT：** 只有 25/420（5.95%）拥有精确的 production projectile / interacting particle / process link；覆盖 22/66 source points、20/49 family×volume×isotope keys。
- **UNKNOWN：** 其余 395 行的直接制核粒子与反应过程。`incident_family` 是 activation inventory/lineage 的入射主粒子 family 分支，不能自动等同于直接制造该核素的 interacting particle。
- **INFERENCE：** “MXC plate 占 30.78%”说明它是生产与近场耦合共同作用后的重要候选，不证明减掉 30.78% 质量即可降低 30.78% delayed W2。

## 抛弃边缘像素是否提高可分辨通量

背景主导、同一显著性定义下：

\[
\frac{F_{3\sigma,\mathrm{cut}}}{F_{3\sigma,\mathrm{base}}}
=\frac{\sqrt{B_{20,\mathrm{cut}}/B_{20,\mathrm{base}}}}
{S_{20,\mathrm{cut}}/S_{20,\mathrm{base}}}
=\frac{\sqrt{f_B}}{f_S}.
\]

因此，切选只有在 (f_S>\sqrt{f_B}) 时才改善灵敏度。不能用保留像素数量或面积直接代替 (f_B)。这里 baseline 为 (S_{20}=1645.38775)、(B_{20}=144203.84209)、(F_{3\sigma}=6.92375\times10^{-5}\)。

| 策略 | 半径 [cm] | 物理像素数（仅语境） | (f_S) | (f_B) | B20 Neff | central (F_{3\sigma}) | 中心改善 | 不给 prompt 切除信用 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **一级建议：event centroid** | **1.35** | 1446/2256 | 0.986896 | 0.576014 | 7.376 | **5.32459e-5** | **23.10%** | 6.14864e-5（改善 11.20%） |
| centroid 敏感性支线 | 1.20 | 1110/2256 | 0.949991 | 0.420126 | 4.269 | 4.72402e-5 | 31.77% | 5.70260e-5（改善 17.64%） |
| centroid 表观最小附近 | 1.05 | 870/2256 | 0.879411 | 0.206957 | 10.214 | 3.58170e-5 | 48.27% | 6.05327e-5（改善 12.57%） |
| 所有 hit pixels 均在圆内 | 1.35 | 1446/2256 | 0.966577 | 0.493884 | 5.667 | 5.03405e-5 | 27.29% | 5.93277e-5（改善 14.31%） |
| 历史联合 cut：centroid + deepest≤L3 | 1.35 | 964/2256 有效层像素 | 0.906049 | 0.453264 | 4.827 | 5.14476e-5 | 25.69% | 6.13885e-5（改善 11.34%） |

注意：1446/2256 表示半径内的物理像素数；event-centroid 策略并没有关闭其余通道。历史联合 cut 同时删除 L4/L5，因此它的收益不能全部归给“边缘像素”。

## 一级实施建议与最小验证门

### 一级建议

**保留全部 TES 像素和读出；在分析层预注册能量加权 fixed-pixel-centroid (r\le1.35\) cm gate，不叠加 layer cut。**

理由：它几乎不损失 focused signal、中心值与“零 prompt 信用”两种口径都改善，并且不依赖 (r<1.10) cm 的 2→0 prompt 量子悬崖。(r=1.20) cm 只作为敏感性支线；(r=1.05) cm 不作为推荐。

### 不建议现在就做的事

不要直接把边缘通道关闭或从事件中逐像素删能量。这样会改变总能量、multiplicity、W2 和 Step05 side-Compton/topology。当前 `all_pixels_inside` 背景曲线只重算了 W2，没有完整重跑 Step05，所以是 **diagnostic**，不是决策权威。

### 最小验证序列

1. **坐标冻结门：** fixed pixel centre、focused axis ((0,-5.2)\) cm、能量加权 centroid、(r=1.35\) cm 和边界包含规则全部写入机器可读配置；用当前 420 delayed + 2 prompt 精确重放，必须得到 delayed 249 行、prompt 1 行。
2. **信号门：** 用候选自己的 focused stage04 replay；要求 (f_S\ge0.98)。当前为 0.986896，(S_{20}=1623.82730)。若外层几何改变，还必须补 full-envelope focused transmission，不能把 post-Be 注入当作 BPE/plastic 透射。
3. **背景改善门：** matched prompt+delayed 的中心门为 (f_B<f_S^2)；稳健 go 门建议使用“不给 prompt 切除信用”仍满足 (F_\mathrm{cut}/F_\mathrm{base}\le0.95)。当前该比值为 0.88805。
4. **统计门：** 扩大 prompt 样本，使 cut 后有效支持不再由 0/1/2 roots 决定；建议至少 30 个等效 surviving roots，并报告 weighted Neff 与置信区间。在此之前不能选择 (r=1.05) 的表观最小。
5. **硬晋级门：** final candidate 必须用自己的 (S_{20}) 与 matched (B_{20}) 得到 central (F_{3\sigma}\le3\times10^{-5}\)。当前一级 cut 为 (5.32459\times10^{-5})，所以状态仍是 **ENGINEERING-CONDITIONAL ANALYSIS OPTIMUM**，不是 PHYSICS PROMOTED。

## 证据分级总结

- **FACT：** 几何切面、66 个 decay-source 三维坐标、420 delayed W2 行、两条 prompt raw ledger、固定像素中心 signal/background replay、20 天轨迹折算和上述中心数值。
- **INFERENCE：** (r=1.35) cm 是当前最稳健、可逆的一级分析切选；近场 Cu/Nb/Mu 是优先工程审查对象。
- **HYPOTHESIS：** 真正关闭边缘通道可能比 centroid gate 进一步降低本底，但也可能因能量重构和 topology migration 损失信号或重新放入事件。
- **UNKNOWN：** 395/420 delayed 行的直接制核过程；literal disabled-channel 的完整 Step05 响应；高统计 prompt 半径分布；任何改几何候选自身的 full-envelope (S_{20}) 与 matched (B_{20})。
