# PA-X1 局部五面被动准直几何附录

## 判决

**`PA-X1 = KILL；不生成 geometry proxy，不启动 transport。`**

这不是因为 focused signal 没有可保留的孔，而是因为真实 TES 方形阵列、
Cu support、Nb 内孔、L0/cold-finger 和 50 mK can/MXC 共同留下的连续
Cu 厚度小于 PA-X1 自己的两个必要门：

- 配现有通道 `+4 cm BGO` 时，每条被拒绝射线要求连续 Cu chord
  `>=3.140091 cm`；
- 配 `BG-TAU5 = 5.8314 cm BGO` 时，即使不留 self-activation margin，仍要求
  `>=2.308064 cm`。

较松的 `2.308064 cm` 档已经被真实内孔 KILL，因此不存在可冻结的单一局部
准直候选。

这两条 chord 门使用 baseline `S20` gate `27073.008579 counts`；
本附录没有借用已 KILL 的 AF1-Al candidate signal gate。

## 1. Signal 孔不是猜测：37,194 条真实 focused rays 的包络

使用冻结的 post-Be EventList
`Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat`，把 world 坐标变到
InstrumentFrame，考察能包住六层 TES/support 的轴向区间
`x_IF=[-3.80, 3.235] cm`。结果为：

| quantity | value |
|---|---:|
| retained focused rays | `37,194` |
| `max |y_IF|` | `1.443448 cm` |
| `max |z_IF+5.2|` | `1.361239 cm` |
| square clear half-width used | `1.850000 cm` |
| ray clearance in y / z | `0.406552 / 0.488761 cm` |
| rays intersecting that square boundary | `0 / 37,194` |

`1.85 cm` 不是按光线事后缩出的孔：Si substrate 的真实半宽是
`1.80 cm`，现有 Cu open-ring support 的内面正好在 `1.85 cm`。因此不能
为了增加屏蔽厚度而把孔缩到只包住 37,194 条射线；那会直接穿 Si/support
实体，并且 EventList 只从 post-Be 面开始，不能认证上游装调包络。

## 2. Nb 内孔给出的横向绝对上限

Nb cylinder 的真实内半径是 `R=4.0 cm`。对上述方孔：

| slice | maximum available radial Cu thickness |
|---|---:|
| square-face centre | `4.0 - 1.85 = 2.150000 cm` |
| square corner | `4.0 - sqrt(2)*1.85 = 1.383705 cm` |

所以：

- face centre 已经小于 `2.308064 cm`；
- corner 更只有 `1.3837 cm`，分别比 `2.308064/3.140091 cm` 少
  `0.9244/1.7564 cm`；
- 任一斜入射/grazing ray 只会使 uniform-minimum 更差，不能把 corner
  数字当平均厚度来放宽。

把所需厚度从方孔角点向外量，最小外半径分别是：

| gate | required Cu chord | minimum outer radius | exceeds Nb bore by | ideal side-Cu mass lower bound* |
|---|---:|---:|---:|---:|
| `BG-TAU5` | `2.308064 cm` | `4.924359 cm` | `0.924359 cm` | `3.4442 kg` |
| `+4 cm BGO` | `3.140091 cm` | `5.756386 cm` | `1.756386 cm` | `5.2028 kg` |

\* 仅按 `x_IF=-3.80--3.235 cm`、圆形理想壳和 `rho_Cu=8.954 g cm^-3`
计算，尚未加 x+ back wall、连接、装配间隙或服务 relief；它是低估质量，
不是可制造 BOM。

作为反证，若把 Nb 内孔中方孔以外的空间 **零间隙全部填满 Cu**，其体积
也只有 `257.3085 cm3`、总质量 `2.30394 kg`；替掉现有 20 个 open-ring
panel 加 4 根 edge rod 的 `0.06928 kg` 后仍需净增 `2.23467 kg`。这个
不可能装配的上限在 corner 仍只有 `1.3837 cm`，所以增加质量本身不能通过
uniform-chord 门。

## 3. 五个非信号面的真实硬冲突

`x-` 是唯一保留的 focused-signal 开口。其余五面必须同时闭合；任一面
失败都足以 KILL：

| face | real limiting envelope | maximum / conflict | verdict vs `2.308064 / 3.140091 cm` |
|---|---|---:|---|
| `y+`, `y-` | square support 到 Nb inner bore | face `2.15`, corner `1.3837 cm` | fail / fail |
| `z+` | Mu outer top 到 MXC lower face | only `0.45 cm` outside Mu; inner corner still `1.3837 cm` | fail / fail |
| `z-` | Mu outer bottom 到 50 mK can top | only `0.05 cm` outside Mu; inner corner still `1.3837 cm` | fail / fail |
| `x+` | L0 between L5 and four cold fingers | L0 `0.35 cm`; zero-clearance limit `0.41 cm` | fail / fail |

x+ 的数值来自真实实体边界：L5 Si rear face `x=3.195 cm`，L0 为
`x=3.245--3.595 cm`，四根 off-axis cold finger 从 `x=3.605 cm` 开始。
即使吃掉前 `0.05 cm` 和后 `0.01 cm` 的全部装配间隙，连续 back-wall Cu
也只有 `0.41 cm`。Nb/Mu back caps 不能补这个缺口：它们的中央
`r<1.85 cm` 正是四根 cold-finger 的功能孔，不是可填的真空。

z+ 方向，Mu outer edge 到 MXC lower face 只有 `0.45 cm`；z- 方向，
Mu outer edge 到 can-bottom top 只有 `0.05 cm`。在 Nb/Mu 外再套一个连续
Cu 五面壳会直接穿 MXC 或 can bottom。把 Nb/Mu 整体外移到 R=8--10 cm
已经在主报告中被同一包络 KILL。

用户允许的 cold-plate `OD <= -25%`、`t <= -10%` 和少量 M4 都不改变
`R_Nb,in=4.0 cm`、方形阵列角点、L0/cold-finger 或 Mu-to-can/MXC 间隙，
因此不能解除上述任一硬界。

## 4. 有分母的 delayed 几何反事实（只作交叉检查）

420 条 selected-W2 中 418 条有唯一 TES-annihilation 511 方向，覆盖
`99.9672%` mission counts。对一个简单四板 square-bore Cu tube
（`x=-3.80--3.235 cm`、内半宽 `1.85 cm`、外半宽 `2.75 cm`）作纯直线
切片：

- `0/37,194` focused rays 被遮；
- 300 条 positive-chord W2 rays，占 traceable mission weight
  `78.7238%`，`Neff=20.82`；
- Cu gross mass `1.04314 kg`，替换现有 support 后净增 `0.97386 kg`；
- conditional weighted mean Cu chord `1.11087 cm`；
- 用主报告同一 `exp(-0.749 L_Cu)` 且把“任一首次相互作用”都乐观算作删除，
  aggregate delayed suppression scale 也只有 `42.0948%`。

进一步采用不可能装配的 `R=4.0 cm` 零间隙全填充，并额外把 L0 全厚
`0.41 cm`、can bottom 全厚 `0.75 cm` 都当作新增 Cu（明显过度给 credit），
aggregate scale 仍只有 `62.7625%`。再把两条未闭合 lineage 假设为 100%
删除，all-420 上限为 `62.7748%`；delayed residual 为
`0.0202802 cps`，即使把 prompt 完全设为零也仍高于 central
baseline-S20 门 `27073.008579 counts`（同 exposure 约 `0.0160095493 cps`）。

这不是 transport 预测，而是偏向候选的必要性上限：真实 Compton 分支、
新增 Cu 自身 pair/activation、热负载和装调间隙只会使结果更差。三条 prompt
survivor 没有被用于全天角外推。

## 5. 最终 KEEP / MODIFY / KILL

| topology | verdict | direct falsifier |
|---|---|---|
| PA-X1 + `+4 cm BGO` | **KILL** | corner `1.3837 < 3.140091 cm`; x+ `0.41 cm` |
| PA-X1 + `BG-TAU5` | **KILL** | face `2.15 < 2.308064 cm`; corner `1.3837 cm`; x+ `0.41 cm` |
| narrower post-selected signal hole | **KILL** | intersects real `1.8 cm` Si / `1.85 cm` support envelope |
| outside-Nb five-face Cu shell | **KILL** | z+ `0.45 cm` to MXC, z- `0.05 cm` to can; no continuous shell |

**最终没有局部 passive angular-selector candidate；主报告的
`NO_ADMISSIBLE_CANDIDATE` 不变。** 未生成 PA-X1 proxy，也未运行 transport。

## 可追溯源

- baseline `.geo`：TES/Si/support/L0/cold finger 行 `11374--11758`；
  Nb/Mu/can/MXC 行 `11762--11854`。
- focused EventList audit：
  `reconsideration_20260814/agents/prompt/focused_eventlist_geometry_audit.json`。
- delayed 418-ray denominator：
  `thermal_cu_rethink_20260814/agents/delayed/delayed_annihilation_sibling_events.csv`。
- 机读门表：`PA_X1_FIVE_FACE_GEOMETRY_GATES.csv`。
