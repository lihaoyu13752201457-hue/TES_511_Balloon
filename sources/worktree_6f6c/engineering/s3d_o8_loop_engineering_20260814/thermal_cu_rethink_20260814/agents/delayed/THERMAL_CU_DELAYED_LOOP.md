# S3d-O8 thermal-Cu rethink：delayed LOOP 最终物理审阅

日期：2026-08-14  
范围：只读复核官方 S3d-O8 day-15 activation、20-day mission fold、420 条 selected
delayed lineage 与现有几何；没有运行 transport，也没有复制原始 SIM。

## 决策先行

**当前硬边界下的最终判决是 `NO_ADMISSIBLE_SINGLE_TOPOLOGY`。** 冷盘保留热功能、外径
最多缩 25%、厚度最多减 10%、仅少量 M4 孔后，之前的 cold-plate wheel/skeletal 方案
KILL。最后一个简单联合候选 `BG-J4/BG-TAU5 + BPE-O` 也不能把 delayed 写成
`D exp(-0.985 L)`：它要求 full-delayed 的条件 BGO 耦合
`q >= 0.916767`，而 baseline actual sibling branch 只有 `0.105925` 的 full-D mission
counts 带着 `>=50 keV` gamma 到达 current-BGO/outer-region proxy，且
`Neff=2.65`、最大单事件占 53.2%。

`BG-J4` 的候选 CSG 确实让 418/418 条**初始未散射直线**有 BGO chord，413 条新增
chord `>=4 cm`，覆盖 99.862% traceable mission counts；这只是几何机会。真实 selected
tail 中 99.9% 的 sibling 先在内层 passive Cu/Al/Nb/Mu/NbTi/W 相互作用，绝大多数不再以
`>=50 keV` gamma 到达外层 BGO。因此 `q=1` 的 20094-count 算术 PASS 是错误物理前提，
不是候选预测。

同位素工程 Cu 也不能救回方案。SIM/RP 没有序列化 target isotope；只能从守恒严格识别
`63Cu(n,gamma)64Cu`，其余通道只能做 conventional reaction-label assignment proxy。
在可闭合的 26 个
`n/p/alpha × volume × Cu-61/62/64` key 中，完美删除已知 63Cu capture 通道的最大观测
信用仅 `13197.887 counts = 14.862% D20`，而且只有 7 条、`Neff=4.74`。按自然丰度将
reaction-label proxy 归给 65Cu 的通道放大到 100% 65Cu 后，净收益只剩
`3289.204 counts = 3.704% D20`；100% 63Cu proxy 反而增加 1467.418 counts。

**唯一即时重开证据**是 candidate-own paired exact-decay test：在完整
`family × parent-ZA × exact position` 分母上证明 conditional coupling 的预注册单侧下限
`q >= 0.916767`。未过即 KILL，不再跑 full-chain。只有 q 先过门，新增约 470 kg BGO 的
自活化与外置 BPE production 才成为下一关；所以“新增 BGO activation 是唯一未闭合项”
这一说法被否定。

## 1. FACT：归一、production 与 coupling

- 官方 selected delayed 为 420 行、`0.05447975222726722 cps`；按 81-node activity 与
  baseline accidental-live factor 折叠为 `88804.86265187593` 个 20-day counts。
  mission `Neff=28.687`，最大单事件占 5.650%。
- `production Bq` 是每个 `S3d_O8 × BUILDUP × incident family` 内分别计算
  `sum(RP)/sum(TT_family)` 后衰变到 day 15；zero-RP DAT 的 TT 保留在该 family 分母。
- `W2/decay coupling` 是 exact `family × source_volume × parent-ZA` 的 selected W2
  除以该 key 的 realized decay triggers。只有同 key 的 activity 才能乘此 coupling；不同
  geometry、mode、family 不合并。
- 20-day component counts 用 exact `family × parent-ZA` 接到 mission activity timeline；
  不是 day-15 rate 乘 20 天。当前 signal-derived planning gate 是
  `B20,max=27341.9247429 counts` 只属于已有 signal replay 的 AF1-Al candidate，不能
  外推到未 replay 的新拓扑。对 PA-X1 等只有 straight-ray 几何的候选，暂用 baseline
  `S20=1645.387753` 的 formal gate `27073.008579 counts`。

production 与 coupling 必须分开看：

| material | day-15 Bq | selected W2 (cps) | supported W2/Bq | 物理含义 |
|---|---:|---:|---:|---|
| Cu | 112.251 | 0.0363911 | 3.81e-4 | production 大，位置 coupling 中等 |
| Nb | 1.164 | 0.00920149 | 9.44e-3 | 每 Bq coupling 约为 Cu 的 24.8 倍 |
| Mu-metal | 1.361 | 0.00776545 | 6.21e-3 | 每 Bq coupling 约为 Cu 的 16.3 倍 |
| existing BGO | 1031.944 | 0 observed | finite upper bound | 零观测不是零真值 |
| existing BPE | 34.373 | 0 observed | finite upper bound | 同上 |

MXC、Nb inner、Mu、L0、can-bottom 的 selected 20-day counts 约为
`27429.9 / 12797.0 / 12735.4 / 9455.4 / 6540.4`。Nb/Mu 的位置 Neff 约 3--4；
L5/L2 等甚至由单事件控制，不能把 perfect-removal 图当确定收益。

## 2. Localize：有分母的 420-row sibling 与真实路径

逐个流式读取 lineage 指向的 7 个 delayed SIM，用 type-2 HTsim origin 沿 IA parentage
回溯 TES-bound ANNI，再找同 parent、同 time 的反向 sibling：

- `418/420` 唯一闭合，覆盖 `88775.7011/88804.8627 = 99.9672%` mission counts；
  两行 multi-ANNI 保留为 UNKNOWN。
- 418 条 sibling 与 TES photon 的方向点积全部 `<-0.999`。InstrumentFrame `+z` 为
  260/418、占 mission 68.458%，所以不能用 3 个 survivor 外推全天角。
- baseline unscattered ray 的现有 BGO 机会为 traceable mission 的 86.284%：side
  60.856%、bottom 25.468%、current top 2.396%；top plastic gap 13.716%。top-only
  current+gap 即使完美也仅 `14303.45 counts=16.11% D20`，故 central/top chimney KILL。
- BG-J4 proxy 使 418/418 有 candidate BGO chord，413/418 新增 `>=4 cm`；5 条 relief
  仅 122.789 mission counts、`Neff≈5`。该分母对“是否画到 BGO”完整，但不包含 gamma
  在内层 passive stack 的实际散射/吸收。

### 初始直线 86.3% 为什么不是 realized coupling

对同 418 条的 actual sibling IA branch 做真实 point-membership：

| first interaction | mission fraction of traceable | Neff | dominant event |
|---|---:|---:|---:|
| Cu | 41.357% | 11.83 | 13.67% |
| Al | 21.594% | 6.79 | 26.17% |
| Nb | 14.104% | 3.96 | 40.07% |
| Mu-metal | 11.354% | 3.05 | 48.09% |
| NbTi proxy | 5.794% | 1.05 | 97.54% |
| W | 5.294% | 2.53 | 48.71% |
| first interaction already in BGO | 0.039% | 1.85 | 70.53% |

首过程为 `COMP 94.184%`、`PHOT 5.579%`、`RAYL 0.138%`、`NONE 0.099%`。所以
straight CSG ray 在到 BGO 前已经被散射、降能或吸收。

- 纯 ESCP gamma `>=50 keV` 只有 18 条、`7494.479 counts=8.442% traceable`，
  `Neff=1.88`。
- 更宽松地把 current BGO、active plastic/BGO wrap、外层 BPE/Al 或 ESCP 任一点都算作
  “到达 current-BGO/outer region”，也只有 21 条、`9406.613 counts=10.596%`
  traceable（full D 为 10.5925%），`Neff=2.65`，最大单事件 53.15%。这是 baseline
  conditional-tail 的机制 proxy，不是候选后严格不变的数学上界。
- 7 条有 sibling IA point 落在 active volume，mission 2.220%、`Neff=1.12`；IA point
  membership 不是 threshold deposit。
- 6 条 event-level active energy 非零但均 `<50 keV`，mission 2.671%、`Neff=1.07`；
  CC track ID 与 IA ID 不同，branch attribution UNKNOWN。selected W2 本来就条件于 veto
  energy `<50 keV`，不能用这 2.671% 估计无条件 BGO 效率。

因此新增 BGO 可以对真正到达它的 conditional tail 再衰减，但不能先假定所有 420 条都
到达。candidate geometry 可能改变散射后的到达率，只有 paired exact-decay 能测 q。

## 3. Origin：冷盘约束与 n/p/alpha production

Cu 冷盘为 MXC/CP/Still 的 `R=15 cm,t=6 mm` 与 4 K 的
`R=17.5 cm,t=6 mm`。合法均匀质量削减上限是
`1-0.75^2×0.90=49.375%`，但 exact source positions 不均匀：

- 完全删除全部 named cold plates 的观测 ceiling 为 `31594.365 counts`，不可用。
- exact-position proxy（`r>0.75R` 置零，保留半径内只给 10% thickness 信用）仅
  `9078.066 counts=10.222% D20`；`Neff=5.58`，最大事件占 25.22%。
- CP 的大信用主要来自 3 个外圈事件。此 proxy 只能定位，不是统计证明，也不能给 prompt
  中央射线信用。

完整 incident-primary 分母显示 Cu-61/62/64 不是单一低能中子图像：

- p/alpha primary 常先产生 secondary neutrons，再在 Cu 发生 capture/inelastic；p→MXC
  Cu-64 capture 的 primary 约 0.363--213 MeV、中位 18.0 MeV、production
  `3.144 s^-1`。
- n family 同时含 thermal/epithermal capture 与高能 cascade；n→Cu-64 capture primary
  跨 `4e-3 keV--890 MeV`。
- Y-85、Nb-89/90、Co-54 的 reaction cells 多为 1--2 RP，只能定位，不能稳定外推截面。
- 外置 BPE 可压进入核心前的 neutron current，但不能自动消除 p/alpha 在金属近处产生的
  secondary cascade。现有 20 mm BPE 只有约 10--16% inward-current proxy，无 bypass、
  cascade 或 coupling 闭合。

## 4. 最后假说：同位素工程 Cu

### FACT

现有 `CC IP RP` 与 IA 只记录 residual ZA、creator process 与 interacting particle，**不记录
target isotope**。因此只有以下第一项是严格 target attribution：

- `63Cu(n,gamma)64Cu`：已支持 `8.227006 Bq`，target 必为 63Cu；
- 把 Cu-64 的 `neutronInelastic/photonNuclear` conventional 地指给 65Cu 时，得到
  `3.364330 Bq`；高能 neutronInelastic 记录本身仍不证明 target，故这是 proxy；
- Cu-61/Cu-62 的 `(n,xn)`、高能 p/pi/alpha 通道可同时来自 63Cu 或 65Cu，target
  attribution UNKNOWN。

26 个 origin-support 与 inventory 完全闭合的 `n/p/alpha × volume × parent` key 共
`18.786255 Bq`，覆盖 `46064.113` selected mission counts。按 exact key 的 activity fraction
乘原 coupling：

| screen | count change | full-D fraction | verdict |
|---|---:|---:|---|
| 完美删除所有已识别 63Cu capture | -13197.887 | -14.862% | 仍不足，且低 Neff |
| 100% 65Cu known-channel balance | -3289.204 | -3.704% | KILL |
| 100% 63Cu known-channel balance | +1467.418 | +1.652% | KILL |

100% 65Cu proxy 使用自然丰度 `f65=0.3085`，因此被 conventional 地指给 65Cu 的通道
放大 `1/f65=3.2415`；
未知通道被刻意固定，已是 screening proxy，不是 enriched material prediction。已识别
63Cu-capture 信用只有 7 个 selected events，`Neff=4.74`，L5 单事件占 36.73%。

自然 Cu inventory 已含 Cu-66 `8.760668 Bq`，当前 selected 为 0 observed，仅能给有限
上界。65Cu enrichment 会改变/放大 `65Cu(n,gamma)66Cu` 与高能 Cu-61/62/64 通道；Cu-66
虽主要 beta-minus，也可通过 gamma/Compton/brems 进入 511 window，不能按“非 beta+”零计。

### 判决

同位素 Cu 保留元素与热功能，工程方向比 Cu→Al 更一致，但**当前物理上 KILL**：target
isotope 缺失使主 Cu-61/62 通道不可重权，known-channel 净收益远低于门。即使把
`13197.887` 的完美 63Cu 信用错误地当作与全部 component credits 无重叠，再给 30% 全局
BPE，联合仍为 `29560.847 > 27341.925 counts`。

## 5. Optimize：BG-J4 与允许组合的预算

令新增 BGO chord `L=4 cm`，取 planning attenuation
`mu_prompt=0.276 cm^-1`、`mu_511=0.985 cm^-1`：

`P_res = P exp(-mu_prompt L) = 18367.103 counts`，

`D_res(q) = D[(1-q)+q exp(-mu_511 L)]`。

要过 gate，必须 `q>=0.916767`。

| q 的来源 | q/full D | total counts | margin to gate | 判决 |
|---|---:|---:|---:|---|
| 假定所有 delayed 都到达 | 1.000000 | 20094.199 | +7247.726 | 错误前提 |
| baseline 现有 BGO straight CSG | 0.862560 | 32062.130 | -4720.205 | FAIL；机会而非耦合 |
| BG-J4 added chord >=4 cm CSG | 0.998289 | 20243.195 | +7098.730 | 只算术 PASS |
| actual `>=50 keV` outer-region proxy | 0.105925 | 97948.294 | -70606.369 | FAIL，低 Neff |

再做一个故意有利的 Cu-preserving composite：合法 cold-plate proxy、L0+can 与
DR/Ag/CuNi 100% 信用、Nb/Mu 固定 inventory 在 10 cm 的 84% `1/r^2` coupling 信用、
actual-outer branch 100% veto，并强行把所有信用视为不重叠。即使如此：

- 16% global BPE：`42885.821 counts`；
- 30% global BPE：`38799.368 counts`；
- 过门需对该残余再有 `69.253%` global BPE suppression，而现有证据只有 10--16%。

这已比真实候选更乐观，因为 L0/can/DR 不可能 100% 消失、Nb/Mu 保磁性能会改变面积与
production、各信用实际重叠。故在保留 thermal Cu/Ni 与冷盘新边界下，没有一个由
“近场非盘 host 减 coupling + BPE + same-channel BGO”组成的证据闭合单拓扑。

此前 `TC-R2` 的 `27016.894` delayed-only 算术点依赖 30% BPE、L0/can/DR 100% 信用与
10-cm magnet `1/r^2`，仅比 strict 69.5% residual target 好 68.6 counts；几何审查已表明
10-cm closed magnet 与冷盘/服务包络冲突。它保留为敏感性，不再是 optimum。

## 6. Prove/Falsify：最小顺序，不跑 full-chain

### P0：唯一即时 blocker——conditional q

做 matched baseline/BG-J4 exact-decay，不改变 cold core。每个 realized decay 记录：

1. exact `family × parent-ZA × source_volume × source_position` denominator；
2. TES-bound ANNI 与 anti-TES sibling actual branch；
3. 到 candidate BGO 前后的 particle、energy、process、active deposit 与 `>=50 keV` veto；
4. relief 与非 relief 分开，高权重事件单列，报告 q 的 one-sided interval 与 Neff。

**PASS：**完整 mission fold 的 conditional q 预注册单侧下限 `>=0.916767`。  
**KILL：**下限未过；不得用 418 条 straight chords 代替。baseline proxy 只有 10.6%，
所以应先做 focused exact-decay，不做 full-chain。

### P1：只有 P0 通过后才做 activation

- 对 n/p/alpha 分别做 matched baseline/candidate BUILDUP，保留完整 INIT energy ×
  InstrumentFrame direction denominator；输出 added BGO、BPE、Cu、Nb/Mu、Ag/SS 的
  production Bq ratio。
- 若复活 isotope-Cu，必须显式定义 isotopic material，并输出 target isotope；至少跟踪
  Cu-60/61/62/64/66 及 capture gamma。不能从 residual ZA 事后猜 target。
- 用 candidate exact positions 做 decay/source-mix fold，加入 candidate signal gate 与 live
  factor。新增 BGO 现有 1031.944 Bq 的零 selected observation只给 finite upper bound，
  更大、更近的 BGO 不能 zero-impute。

## 7. 产物

- `delayed_annihilation_sibling_events.csv`：420-row ANNI/sibling、actual branch、方向、权重。
- `delayed_sibling_ray_segments.csv`：baseline 真几何逐段 chord。
- `delayed_sibling_denominator_summary.csv`：有分母方向/几何机会与 Neff。
- `coldplate_constrained_credit.csv`：冷盘新边界 exact-position proxy。
- `bg_j4_conditional_attenuation_proxy.csv`：q 门、实际 proxy 与联合预算。
- `copper_isotope_engineering_screen.csv`：26 个 family×volume×parent target-channel screen。
- `copper_isotope_engineering_summary.csv`：63Cu/65Cu known-channel mission 汇总。
- `finalize_delayed_candidates.py`：只读消费小 CSV；不打开 raw SIM。
- `focused_BUILDUP_exact_decay_matrix.csv`：最小 focused 证伪矩阵。
- `topology_option_screen.csv`：最终 KEEP/MODIFY/KILL 收敛。

BG-J4 几何 proxy 与 relief 分母由 geometry agent 存在
`agents/geometry/BG_J4_DELAYED_*.csv`；它们只证明 CSG chord，不证明 veto coupling。

## 8. 最后追加 LOOP：TES-bound 511 的近场角选择

完整 37194 条 signal EventList 与 420-row delayed 的独立入射方向/入射面复核见
`TES511_NEARFIELD_PASSIVE_ANGLE_LOOP.md`。它 FALSIFY 了“没有角分离”：signal 在 IF
为 `+x`、最大偏轴 0.459802 deg；418 条可追踪 delayed 中 `<=10 deg` 为 0，且将真实
`x-` signal footprint 与两条方向 UNKNOWN 全算作开放后，observed ideal-mask 泄漏仅
0.314835% full D。先前出现的 4 条/98.336 counts 是把 WorldFrame signal 轴直接与
InstrumentFrame delayed 分量点积造成的坐标混用。

但该结果不产生一个可实现候选。PA-X1 没有 signal replay，故不能借用 AF1-Al 的
27341.925-count gate；用 baseline formal gate 27073.009 后，4 cm BGO case 要求 rejected
directions 至少有 3.140091 cm 均匀 Cu chord，3.1 cm 反而超门 256.866 counts，3.2 cm
只余 369.745 counts。BG-TAU5 `L=5.8314 cm` 的同口径 point-estimate 要求
2.308064 cm。

独立真实包络已经硬 KILL 两档：Nb 内孔到 1.85-cm 方孔的 face/corner 只有
2.15/1.383705 cm，x+ 连续空间最多 0.41 cm，z+/z- 外间隙 0.45/0.05 cm。即使把 Nb
bore 零间隙填 Cu 并过度计 L0/can，all-420 乐观 suppression 也只有 62.7748%，prompt=0
仍不过门。因此角分离机制 KEEP，但 PA-X1 implementation KILL/DO NOT RUN；不再进入
focused BUILDUP 或 transport。详见 `TES511_NEARFIELD_PASSIVE_ANGLE_LOOP.md` 与
`../geometry/PA_X1_LOCAL_COLLIMATOR_ADDENDUM.md`。
