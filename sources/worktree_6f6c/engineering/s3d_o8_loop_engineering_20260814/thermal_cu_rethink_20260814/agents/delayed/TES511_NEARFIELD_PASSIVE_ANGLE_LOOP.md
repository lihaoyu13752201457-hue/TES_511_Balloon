# S3d-O8：TES-bound 511 近场被动角选择 LOOP

日期：2026-08-14  
范围：37,194 条真实 signal EventList 射线与官方 420 条 selected delayed lineage；只读
重建，没有 transport，也没有把 annihilation partner 或外层 BGO 几何机会当作本轮分母。

## 判决

“delayed TES-bound 511 与真实 511 signal 没有角/入射面分离”这一假说被
**FALSIFY**。在同一 InstrumentFrame 中，signal 是窄的 `+x_IF` 束，最大偏轴仅
`0.459802 deg`；418 条可唯一追踪的 delayed TES photon 没有一条位于 `10 deg` 内。
按 TES envelope 的真实入射面与 signal footprint 再切，只有 `250.4275` 个 traceable
mission counts 落在相同的 `x-` 面、相同 footprint；把两条方向 UNKNOWN 全部悲观算成
可通过，完整 420 行上的理想几何泄漏仍只有
`279.5890 / 88804.8627 = 0.314835%`。

因此角选择**机制 KEEP**，但 `PA-X1` 五面近场被动实现已被真实包络
**KILL / DO NOT RUN**。它原本要求冷盘完全冻结、只以 L0/can-bottom/support Cu/Ni 在
TES 外形成五面 shadow，并保留 upstream `x-` signal 开口；然而较松的 BG-TAU5 case
也要求每条被拒 ray 有 `>=2.308064 cm` 连续 Cu chord。真实 Nb bore 在方孔面/角只有
`2.15/1.383705 cm`，`x+` L0/cold-finger 连续空间最多 `0.41 cm`，z+/z- 外间隙仅
`0.45/0.05 cm`，任一面都足以证伪。

独立几何还把 Nb bore 可用区零间隙填 Cu，并过度计入 L0/can-bottom，all-420 乐观
suppression ceiling 仍只有 `62.7748%`；即使 prompt=0，残余 `0.0202802 cps` 也高于
baseline-gate-equivalent `0.01600955 cps`。所以本轮最终状态是：角分离为未来架构事实，
当前允许边界内没有 conditional candidate；`NO_ADMISSIBLE_SINGLE_TOPOLOGY` 不变。

## 1. 坐标定义与 4-row 分歧

EventList 方向约为 WorldFrame

```text
u_signal,W = (+1/sqrt(2), 0, -1/sqrt(2)).
```

本项目 WorldFrame 到 InstrumentFrame 的旋转为

```text
x_IF = (x_W - z_W)/sqrt(2)
y_IF = y_W
z_IF = (x_W + z_W)/sqrt(2),
```

所以同一 signal 轴在 IF 中严格为 `u_signal,IF=(+1,0,0)`。本报告对 delayed 使用

```text
theta = acos(tes_511_IF_dx / |tes_511_IF|).
```

等价的独立复算是在 WorldFrame 用
`acos[u_signal,W dot tes_511_world / |tes_511_world|]`；两者都得到
`theta<=10 deg: 0/418, 0 counts`。

把 WorldFrame 的 `(0.7071,0,-0.7071)` 直接与 `tes_511_IF_*` 点积会混用两个坐标系；
该错误可精确复现 `4 rows / 98.3361 counts`。CSV 特意保留一行 `INVALID mixed-frame`
作为审计陷阱，不能用于物理结论。

## 2. Localize：完整分母、方向与入射面

### Signal 分母

- EventList 共 `37194/37194` 条，均为 511 keV；全部从 TES envelope 的 `x-` 面进入。
- `theta(+x_IF)`：min/median/p95/p99/max =
  `0.393140 / 0.425598 / 0.437255 / 0.441953 / 0.459802 deg`。
- 在 `x_IF=-3.15 cm` 的完整射线 footprint bounding box 为
  `y=[-1.217325,+1.401995] cm`、`z=[-6.512157,-3.928334] cm`。这个矩形是保持全部
  37194 条实际 signal 射线的几何开口分母，不是任意设定的窄孔。

### Delayed 分母

- official selected delayed：`420` 行、`88804.862652` 个 20-day counts，
  `Neff=28.6867`，最大单事件占 `5.650%`。
- 其中 `418/420` 可唯一连接 ANNI 到 TES-bound 511，覆盖
  `88775.701126 counts = 99.9672%`；其方向分母 `Neff=28.6680`。两条 multi-ANNI
  共 `29.161526 counts` 保留 UNKNOWN。
- 方向锥不是由少数 survivor 外推：`<=10 deg` 为 0；`<=15 deg` 首次出现 1 条
  n/can-bottom 高权重事件，`2289.1304 counts`、`Neff=1`；`<=30/45/60/90 deg`
  分别占 traceable counts 的 `2.965/3.800/9.674/35.025%`。

TES envelope 三维 slab intersection 给出的入射面为：

| entry face | rows | 20-day counts | traceable fraction | Neff | dominant event |
|---|---:|---:|---:|---:|---:|
| `z+` | 161 | 33852.5994 | 38.133% | 10.580 | 14.82% |
| `y+` | 77 | 19121.3868 | 21.539% | 4.544 | 26.24% |
| `x+` | 101 | 16225.8664 | 18.277% | 7.513 | 14.11% |
| `z-` | 36 | 12024.7371 | 13.545% | 3.897 | 40.31% |
| `x-`（signal 面） | 20 | 6868.7320 | 7.737% | 3.378 | 33.33% |
| `y-` | 23 | 682.3795 | 0.769% | 17.330 | 7.79% |

也就是说，`92.263%` 的 observed traceable delayed counts 从与 signal 不同的面进入。
同面 20 条再按完整 signal footprint 切，只余 11 条、`250.427454 counts`；这 11 条仍在
`41.85--70.93 deg`，`Neff=10.376`，最大单事件占 9.82%。三个同面高权重热点全部在
signal footprint 外：

- n / outer Mu：`2289.1451 counts`，entry `(y,z)=(0.555,-6.993) cm`；
- n / can bottom：`2289.1304 counts`，entry `(1.290,-6.749) cm`；
- alpha / CP cold plate：`1863.9427 counts`，entry `(-1.394,-5.693) cm`。

这正是角选择可分离度的 observed 上限；它不是材料衰减率。

## 3. Origin：为什么理想 mask 不能直接成为背景预测

420 行是**条件于 baseline 几何已产生 TES hit 且未 veto**的 selected 尾。把一个新 Cu/Ni
shadow 放到 TES 附近会产生当前分母里没有的三类路径：

1. shadow 自身由 n/p/alpha 产生 Cu-61/62/64、Ni/Co 等母核；在墙内或 TES 一侧衰变的
   511 不具有完整 `3.2 cm` 外向 chord；
2. 重新布置的 L0、can bottom、support/stem/thermal contact 若位于 mask 内部或穿过开口，
   其 positron annihilation photon 可直接从内部进入 TES；冷盘受硬约束冻结，不能把这些
   热路径假定为已移走；
3. Compton 后的低能 gamma 可由墙体散射进开口。当前直线 face/footprint 统计没有传播或
   能量阈值，因此也不是 veto/coupling。

所以 `0.314835%` 是“若所有被拒方向都由完美吸收边界处理”的 point-estimate floor，绝非
候选 `W2/Bq`。低统计也很关键：方向分母只有 `Neff=28.668`。对零观测 `<=10 deg` 粗用
`1-0.05^(1/Neff)` 只得到 95% proxy 上界 `9.9223%`；这是启发式而非严格 weighted
confidence interval，已经几乎吃满 delayed 预算。

## 4. Optimize：PA-X1 的理想预算反算

PA-X1 没有自己的 signal replay，只有 straight-ray signal geometry。它不能借用已测
AF1-Al candidate 的 `S20=1653.53937791` 与 `G=27341.9247429`；那组门对 PA-X1 标记为
**STALE/INVALID**。在获得 PA-X1 replay 前，同口径且乐观的 authority 必须回到 baseline
`S20=1645.387753` 与 formal gate `G=27073.008579`。

仅为给 focused test 设门，先取 `L_BGO=4 cm` 联合 planning proxy：

```text
P20 = 55398.979434 counts
D20 = 88804.862652 counts
G   = 27073.008579 counts  [baseline formal gate]
P_after(+4 cm BGO) = P20 exp(-0.276*4) = 18367.102776 counts
D_allowed = G - P_after = 8705.905803 counts
f_open = (250.427454 + 29.161526)/D20 = 0.003148352
```

若被拒方向都得到均匀 Cu chord `t`，且暂时忽略新 host production/散射，则

```text
D_proxy(t) = D20 [ f_open + (1-f_open) exp(-0.749 t) ].
```

解 `P_after + D_proxy(t) <= G` 得

```text
exp(-0.749 t) <= 0.0951854
t >= 3.140091 cm Cu.
```

因此 `3.1 cm` 已经 FAIL：总数 `27329.8741`，超门 `256.8655 counts`；
`3.2 cm` 为 `26703.2632`、余 `369.7454 counts`，仍没有覆盖 low-Neff、缝隙、散射或
自活化。若把上述零观测的 Neff-95% proxy `9.9223%` 当开放泄漏，而不是 observed
`0.3148%`，它已经高于本 case 全部 delayed allowance `9.8034%`；此启发式口径下即使
Cu chord 无穷大也不能过门。故不能用平滑角图或点估计宣布 PASS。

同一 baseline formal gate 下，若用 `BG-TAU5 L_BGO=5.8314 cm`，则
`P_after=11079.480255`、`D_allowed=15993.528324`，observed point-estimate 所需 Cu chord
降为 `2.308064 cm`；`2.3 cm` 仍 FAIL 95.1981 counts，`2.4 cm` 余 1045.6483 counts。
此处 Neff-95% proxy 对应 `3.218105 cm`。这些都是 PA-X1 signal replay 前的 optimistic
planning 数，不是 candidate-own PASS。

这里的 `+4 cm BGO` 只承担先前 prompt planning term；本轮没有重新把 delayed sibling
送往外 BGO，也没有复活已被 actual-branch 路径证伪的 `D exp(-0.985 L)` 假说。

## 5. Prove/Falsify：解析几何门已完成

无需 focused BUILDUP、decay 或 transport；候选在 P0 几何必要条件已经失败：

| face/envelope | available continuous chord | required best case | verdict |
|---|---:|---:|---|
| y/z 方孔 face | 2.150000 cm | 2.308064 cm | KILL |
| y/z 方孔 corner | 1.383705 cm | 2.308064 cm | KILL |
| x+ L0/cold-finger | <=0.410000 cm | 2.308064 cm | KILL |
| z+ / z- outside Mu | 0.45 / 0.05 cm | continuous five-face shell | KILL |

`+4 cm BGO` 的 `3.140091 cm` 门更严格，也同步 KILL。不要用窄到只贴合 post-Be
EventList 的孔逃避：真实 Si 半宽 1.8 cm、support clear half-width 1.85 cm，且还需装调
余量。不要生成 PA-X1 proxy 或启动 focused transport。

独立证据在 `../geometry/PA_X1_LOCAL_COLLIMATOR_ADDENDUM.md`、
`../geometry/PA_X1_FIVE_FACE_GEOMETRY_GATES.csv` 与
`../prompt/PA_X1_PROMPT_ADDENDUM.md`。

## 产物

- `tes511_nearfield_angular_separation.csv`：signal、420-row 分母、锥角、六入射面、理想
  footprint 与预算反算；包含合法 World/IF cross-check 和明确标记的 INVALID mixed-frame。
- `tes511_nearfield_same_face_events.csv`：20 条同 `x-` 面事件，逐事件权重、Neff 所需字段、
  入射点与是否落入 signal footprint。
- `analyze_tes511_nearfield_angular_selection.py`：从 EventList 与本目录 lineage CSV 可复算。
