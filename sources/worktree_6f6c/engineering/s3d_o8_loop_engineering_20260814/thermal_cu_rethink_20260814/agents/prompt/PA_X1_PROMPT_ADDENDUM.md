# S3d-O8 PA-X1 prompt addendum：近场被动角选择

日期：2026-08-14  
范围：完整 focused 511 EventList、完整 S3d-O8 gamma INIT 分母、三条已知 prompt
链与真实近场包络；只读复算，不跑 transport。

## 判决

**角分离机制 `KEEP`；`PA-X1` 近场五面被动实现 `KILL`；不要启动 focused
transport。**

signal 与背景的角相空间确实不同：37,194 条 focused 511 ray 全部沿 `+x_IF`，最大偏轴
`0.459802 deg`。完整 4--8 MeV prompt 分母中，直线瞄准 TES box 的 273 条里有
`253/273 = 92.674%` 从非 signal 面进入。但后一数字只是 primary straight-ray 几何机会，
**不是** pair -> positron stop -> annihilation/scatter -> TES 的 leakage efficiency。

真正的硬反证是光学厚度与包络同时不闭合。沿用 Cu-preserving 的
`G20=27073.008579 counts`，即使先给外层 `+4 cm BGO` 一个尚未由 paired transport
证明的 prompt 标度，PA-X1 对被拒方向仍需至少 `3.140091 cm` 均匀 Cu chord。真实 Nb
内半径只有 4.0 cm；保留 Si/support 方形半开口 1.85 cm 后，面中心最多 2.15 cm，方角
只有 1.383705 cm，背面最多 0.41 cm。五面最小 chord 因此不可能达到门槛。即使采用更
强的 BG-TAU5 prompt planning term，所需 `2.308064 cm` 仍大于 2.15/1.384/0.41 cm 的
真实最小包络。

新增低 Z 不能补救：同一乐观 511 任意交互标度需要约 `10.29 cm Al` 或
`19.03 cm BPE-like`。把 Cu 塞近 TES 虽可缩短到约 3.14 cm，却会让 5.77 MeV gamma
产生约 `25.3%` 的 pair 机会和 `58.3%` 的任意交互机会，等价于新增一个近端 pair host；
同时它还是未计入 candidate BUILDUP 的 Cu/Ni activation source。因此这不是“尚缺一点
统计”，而是在现有机械/材料边界内没有可定义的单一 topology。

## Localize：signal 与 prompt 的有分母角图像

坐标变换为

```text
x_IF = (x_W - z_W)/sqrt(2)
y_IF = y_W
z_IF = (x_W + z_W)/sqrt(2).
```

### Focused 511 signal

- EventList：`37194/37194` 行，全部 511 keV。
- `theta(+x_IF)`：`0.393140--0.459802 deg`。
- 在整个 `x_IF=[-4.35125,+2.30] cm` 直线路径上，包住全部 ray 的数学最小中心方孔
  半宽为 `1.437378 cm`；`h=1.45 cm` 给 `37194/37194` 的几何接受。
- 这不是 flight aperture：只有 `0.126 mm` ray margin，且没有 alignment、散射或
  transported effective-area 余量。保持现有 Si/substrate/support 接受域需 `h=1.85 cm`；
  它同样保留全部 ray，但也保留更多 background 开口。

### 完整 prompt primary 分母

流式读取 132 个 S3d-O8 gamma raw SIM shard，共 `3,207,738/3,207,738` 个 INIT；没有
复制 raw SIM。4--8 MeV 子分母为 `111,410`：

| TES-box entry | histories | fraction of all incident | fraction of 273 direct aims |
|---|---:|---:|---:|
| signal face `front_-x` | 20 | 0.01795% | 7.326% |
| all side/back faces | 253 | 0.22709% | 92.674% |
| total straight TES aim | 273 | 0.24504% | 100% |

这只支持“入射 primary 并不沿 signal 光路”这一方向性事实。3 条 leak 是高权重稀有
branch，不能用 `253/273` 直接乘 baseline prompt，也不能从 2 条同面 leak 定扇区。

## Origin：三条 leak 与新增 Cu host

| event | INIT E | first pair | annihilation | TES-bound 511 entry |
|---|---:|---|---|---|
| 3883 | 4148.29 keV | Nb | MuMetal | `side_z+`，直达 |
| 19932 | 5768.82 keV | Cu | Cu | `side_z+`，直达 |
| 8081 | 6345.94 keV | Nb | Cu | 初始 511 直达 L5，随后在 TES 内 COMP |

3883 与 19932 是 Step05 prompt 两条；8081 是 veto survivor 但不在最终 Step05。两条
Step05 链恰好同为 `side_z+`，样本量仍只有 2，故不能据此设计 sector。

PA-X1 若用 Cu/Ni 作为 absorber，会把 primary interaction 从既有 Nb/Mu/Cu 迁移到更贴近
TES 的 shadow。用现有 MEGAlib/Geant4 material response 仅作标度，在 5.77 MeV：

```text
mu_total(Cu) = 0.27846 cm^-1
mu_pair (Cu) = 0.09308 cm^-1
t = 3.140091 cm
P(any interaction) = 58.29%
P(pair)            = 25.34%.
```

所以“挡住 primary”不能自动记作 prompt suppression：新的 pair 发生在 TES 外几厘米，
positron stop/annihilation 的一个 511 可向内进入 TES，另一个是否被 active veto 必须由真实
lineage 证明。8081 会先穿 `0.6583 cm` L0 Cu 后直达 L5；它说明删 L0 会提高同一直达
路径的透明度，而不是提供一个已证明的 suppression。

数据质量更正：本轮初版使用的 `TES_BOX x_IF<=1.95 cm` 只覆盖到 L4，曾把 8081 误标
为 straight miss。完整六层 CSG 与 raw IA9/IA23 已证实上述 L5 直达；初版标签不得引用。
该更正不改变 PA-X1 uniform-chord 几何 KILL。

activation 同样不能由密度缩放代替。baseline structural-Cu delayed term 为
`59252.576459 counts/20 d`；这不是可外推到新 shadow 的 per-kg 系数，却足以说明
Cu production 不是可忽略项。新/迁移 Cu/Ni 的 `family x position` production Bq 与 W2/Bq
均为 `UNKNOWN`，不能先给零。

## Optimize：为什么 PA-X1 的最乐观门仍失败

使用当前 Cu-preserving 联合口径：

```text
P20 = 55398.979434
D20 = 88804.862652
G20 = 27073.008579
P4  = P20 exp(-0.276*4) = 18367.102776
D allowed = G20 - P4 = 8705.905803 counts.
```

`G20=27341.924743` 属于旧 AF1-Al candidate measured gate，不能借给本候选；旧
`3.098/3.2 cm` 门因此作废。

若只让 ray-footprint 和两条 direction-UNKNOWN 穿孔，理想 bypass 为
`0.314835% D20`。再把每一次 Cu interaction 都乐观视为从 W2 删除，以
`mu_511(Cu)=0.749 cm^-1` 解门，仍得

```text
t_Cu >= 3.140091 cm.
```

若 aperture 保持现有 `+/-1.85 cm` Si/support clear opening，则 observed `x-` face 加
UNKNOWN 已占 `7.76747% D20`；同一算式把被拒方向的 Cu 门抬到约 `5.09 cm`。因此
3.140091 cm 已是对 PA-X1 极端有利的下界，不是设计厚度。

真实包络反证：

| location | continuous passive clearance | comparison |
|---|---:|---|
| Nb R=4.0 到方孔面中心 | 2.150 cm | < 3.140 cm |
| Nb R=4.0 到方孔角点 | 1.383705 cm | < 3.140 cm |
| `x+` L5/L0/cold-finger envelope | <=0.410 cm | < 3.140 cm |
| `z+` Mu 到 MXC | 0.450 cm | 不能外扩连续层 |
| `z-` Mu 到 50 mK can | 0.050 cm | 不能外扩连续层 |

独立几何复核还故意把 Nb bore 的可用区**零间隙填满 Cu**，并把 L0 与 can-bottom
过度计为新增 chord；对 418 条 delayed ray 仍只得到 `62.7748%` 的乐观 suppression
ceiling。对应 delayed residual `0.0202802 cps`，在 prompt 被不可能地设为零时仍高于
baseline-S20 gate-equivalent `0.01600955 cps`。这条反证不依赖三条 prompt leak，也不依赖
选哪个 Cu sector。

冷盘只许 OD -25%、厚度 -10% 与少量 M4；这些约束不打开上述五面间隙。将 shell 移到
Nb/Mu 外又会切过 MXC/can/service，不再是允许的 L0/can/support 小重排。把大量现有
Cu/Ni 从热路径迁入该 shell 也没有 thermal authorization；额外添加只允许低 Z，而低 Z
所需 10--19 cm 更不可能。

## Prove/Falsify 与最终 KEEP/MODIFY/KILL

| hypothesis/topology | verdict | falsifier |
|---|---|---|
| focused signal 与 TES-bound background 可角分 | **KEEP mechanism** | 37,194 signal 与完整背景分母支持 |
| 按两条 `side_z+` leak 做 sector | **KILL** | 只有两条最终 leak，无 leakage direction denominator |
| ray-fit `h=1.45 cm` 五面 mask | **KILL flight implementation** | 无装调/transport margin；且最小 Cu chord仍放不下 |
| PA-X1：保 Cu/Ni、五面 Cu shadow | **KILL system** | 3.140 cm 乐观门 > 2.15/1.384/0.41 cm 净空 |
| PA-X1：Al/BPE-like shadow | **KILL** | 同一门需 10.29/19.03 cm |
| PA-X1 focused transport | **DO NOT RUN** | P0 解析几何/材料门已经失败 |

因此没有遗落一个满足硬约束的近场被动准直候选。角分离可作为未来架构级 redesign 的
物理事实保留，但在本轮允许边界中不是 `ENGINEERING-CONDITIONAL OPTIMUM`；它已由单一
明确证据——**五面最小光学 chord 无法装入真实包络**——证伪。

## 可追溯产物

- `passive_collimator_signal_acceptance.csv`：37,194 signal ray aperture 分母。
- `passive_collimator_prompt_denominator.csv`：3,207,738 INIT 的 E x entry-face 分母。
- `passive_collimator_prompt_leaks.csv`：三链 TES-bound 511 entry class。
- `passive_collimator_delayed_faces.csv`：420-row delayed face/Neff 概览。
- `PA_X1_PROMPT_GATES.csv`：本报告全部数值门与 FACT/SCALING 标签。
- `audit_nearfield_passive_collimator.py`：只读复算脚本。
- `../geometry/PA_X1_LOCAL_COLLIMATOR_ADDENDUM.md` 与
  `../geometry/PA_X1_FIVE_FACE_GEOMETRY_GATES.csv`：独立几何硬门。
