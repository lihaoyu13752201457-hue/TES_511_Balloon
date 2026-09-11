# S3d-O8 thermal-Cu constrained LOOP：最终独立物理与工程审阅

日期：2026-08-14  
判定范围：S3d-O8、corrected gamma、day-15 activation / 20-day mission fold；保持
`geometry × mode × family` 归一边界。原始 SIM 与交接数据只读流式使用；没有复制大缓存，
没有运行 full-chain。

## 技术结论

**单一最终决策是：保留 S3d-O8 baseline，当前没有可冻结的修改候选，也不启动 transport。**
这不是把若干建议并列留给以后选择，而是本轮 LOOP 的收敛判决：`KEEP baseline / KILL all
tested redesigns / NO_ADMISSIBLE_MODIFIED_CANDIDATE`。

用户给出的 thermal-Cu 边界已冻结：冷盘外径最多减小 25%，厚度最多减小 10%，只允许少量
M4 孔；M4 孔在没有有分母的角度统计前领取零背景信用。旧的 48-volume Cu→Al 与 cold-plate
skeletal 方案均已 KILL。

最后检验出的新物理机制是近场被动角选择：37,194 条真实 focused 511 signal 是
`+x_IF` 窄束，最大偏轴 0.460°；418/420 条可追踪 delayed TES-bound 511 没有一条在 10°
锥内。理想五面遮挡只留 signal face 与真实 footprint 时，完整 delayed 的几何直通点估计为
0.315%。**但真实 TES/support/Nb/Mu 包络无法提供预算要求的连续吸收弦：**

- 采用 +4 cm 全包 BGO 仅压 prompt 时，baseline-signal gate 要求所有拒绝方向至少
  `3.140 cm` 等效 Cu；
- 即使用 prompt-only `BG-TAU5`（约 +5.83 cm BGO），仍要求 `2.308 cm`；
- 真实净空在方形 TES/support 角点仅 `1.384 cm`，面中心 `2.150 cm`，`x+` 端仅
  `0.410 cm`。

因此角分离机制本身 `KEEP`，其当前实现 `PA-X1` 则由真实几何直接 `KILL`。新增近场 Cu
还会引入自身 activation、墙内出生 511 与 4–8 MeV prompt pair target；这些尚未计入，
所以几何 KILL 已是乐观结论。

**唯一即时重开条件**是一份 configuration-controlled as-built CAD，证明在不改 TES、
不截断任一真实 signal ray、保留 thermal/magnetic/service 功能的前提下，五个拒绝面都能
达到上述最小等效弦。未先过这条几何门，不运行 focused BUILDUP、exact-decay 或 full-chain。
若几何门将来通过，下一且唯一的物理门才是候选自身
`family × parent-ZA × exact position` production-to-decay fold；它必须把新增/迁移 Cu/Ni
自活化算入并给出 central `F3 <= 3e-5 photon cm^-2 s^-1`。

## 预算与口径

本轮使用的 baseline mission 权威量为：

| quantity | value |
|---|---:|
| prompt `P20` | 55,398.979434 counts |
| delayed `D20` | 88,804.862652 counts |
| total background | 144,203.842086 counts |
| baseline signal `S20` | 1,645.387753 |
| formal count gate `(S20/10)^2` | 27,073.008579 counts |
| target | `F3 <= 3e-5 photon cm^-2 s^-1` |

PA-X1 只有几何 signal audit，没有 candidate-own signal replay，因此不能借用已作废 AF1-Al
候选的 `S20=1653.539378` 与 `27,341.924743` gate。所有当前联合门重新回到 baseline
signal 的 `27,073.008579`。这使 +4 cm BGO 的 delayed effective-coupling 要求从旧 planning
值 91.68% 收紧为 91.99%，也使 PA-X1 的 Cu 弦门由 3.098 cm 收紧为 3.140 cm。

即使 prompt 被理想置零，delayed 仍须由 88,804.86 降到 27,073.01，即至少降低 69.51%。
因此任何只处理 prompt 的方案都不可能独立过门。

## Prompt：三条漏不是几何孔，而是厚 active 后的零相互作用尾

完整 gamma 分母为 `3,207,738` 个 INIT、`TT=59.0965413 s`。三个已观察漏事件如下：

| event | primary | active / passive grammage | first pair → annihilation | TES | veto |
|---|---:|---:|---|---|---|
| 3883 | 4.148 MeV | 23.434 / 20.271 g cm⁻² | Nb → Mu-metal | 510.999 keV | active deposit 0 |
| 19932 | 5.769 MeV | 38.923 / 32.674 g cm⁻² | DR Cu → DR Cu | 510.999 keV | active deposit 0 |
| 8081 | 6.346 MeV | 29.754 / 18.123 g cm⁻² | Nb → L0 Cu | 69.584 + 441.415 keV | active deposit 0; Step05 fail |

三个 primary 都穿过真实 BGO/plastic 厚层而随机不相互作用，随后才在内侧 passive 件发生
PAIR；所以它们不是 top/side hole，也不能用来选定一个方位扇区。加入
`energy × equal-solid-angle direction × active grammage` 后，三个非零 cell 分母仅为
`71 / 94 / 92`，每格 `k=1, Neff=1`。Mass-model 的七条对照又把 first-pair host 分散到
Al、Nb、Cu 与 SS，支持的是“active 穿透后在内侧 passive pair”的共同机制，不支持唯一
Nb/Cu patch。

三条 anti-TES partner 在 baseline 分别还穿过：

- 3883：`2.906 cm Cu + 1.483 cm Ag + 0.198 cm Mu` 后到 side BGO；
- 19932：`3.946 cm Cu + 4.768 cm SS + 2.029 cm BPE + 1.217 cm Al`，且无 top BGO；
- 8081：`1.844 cm Cu + 0.387 cm Nb + 0.387 cm Mu` 后到 side BGO。

这解释了为何没有 veto：反向 511 在抵达 active shield 前先被内部被动件截获。按用户允许的
冷盘极限修改，三条 Cu chord 最多只降到 `1.962 / 3.763 / 1.685 cm`；19932-class 中央路径
几乎不变。

## Delayed：production 大的是 Cu，单位 Bq coupling 大的是 Nb/Mu

官方 delayed 为 420 条 W2、`0.0544797522 cps`；20-day mission 为 88,804.862652 counts，
event `Neff=28.754`。66 个 source positions 的 position `Neff≈24.93`，但单个具名组件均低于
8；L5/L2/Ag 各由一个 source position 控制，必须显式看作单事件热点，不能由平滑 bubble
图隐藏。

| material | day-15 activity | selected rate | supported coupling | interpretation |
|---|---:|---:|---:|---|
| Cu | 112.251 Bq | 0.0363911 cps | 3.81e-4 W2/Bq | production 最大，位置 coupling 中等 |
| Nb | 1.164 Bq | 0.0092015 cps | 9.44e-3 W2/Bq | 每 Bq coupling 约 Cu 的 24.8 倍 |
| Mu-metal | 1.361 Bq | 0.0077655 cps | 6.21e-3 W2/Bq | 每 Bq coupling 约 Cu 的 16.3 倍 |

Cu-61/62/64 的 origin 不是单一低能 neutron capture。p/alpha primary 常在高能级联中先产生
secondary neutron，再于 Cu capture/inelastic；n family 同时覆盖 thermal capture 与 GeV
cascade。因而只在外层增加少量 BPE 不能自动消除 p/alpha 近金属级联。

冷盘合法修改的 exact-position 乐观信用只有 `9,078.066 counts = 10.222% D20`，
`Neff=5.58`；它是定位 proxy，不是候选预测。即使理想删除全部 Cu，delayed 仍为
`29,552.286 counts`，已经高于 formal gate，且还没加 prompt。

## 为什么外层 BGO 不能替代近场处理

420-row lineage 中 `418/420` 可唯一找到 TES-bound ANNI 与反向 sibling，覆盖 99.967%
mission counts。纯未散射 CSG 直线看起来有 86.3% 会碰 baseline BGO，+4 cm 的 BG-J4 proxy
更让 413/418 条新增 BGO chord 达到 4 cm；但真实 sibling IA 首相互作用主要发生在：

- Cu 41.36%；
- Al 21.59%；
- Nb 14.10%；
- Mu-metal 11.35%；
- NbTi 5.79%；
- W 5.29%。

首过程 94.18% 为 COMP。只有 8.44% mission counts 有 `>50 keV` escape gamma；把 current
BGO 与 outer-region proxy 都算入也仅 10.5925%，`Neff=2.65`，最大单事件占 53.2%。
baseline-signal 联合门却要求 +4 cm BGO 对 delayed 有效耦合至少 91.9855%。即使完美删除
所有 observed outer-reach rows，残余仍约 97.8k counts，远超门。因此 BG-J4 几何虽
ROOT-overlap PASS，作为 unified candidate 明确 KILL。

BG-J4 的可复现几何代价也不是小修：BGO 质量由约 296 kg 增至约 766 kg，连同随动外层
总增量约 488 kg。它只能保留为 prompt-only sensitivity，不可领取 delayed 指数衰减。

## 近场角选择：物理分离存在，但真实净空不够

![Near-field angular separation and chord falsifier](/home/ubuntu/.codex/worktrees/6f6c/TES_511_Balloon/engineering/s3d_o8_loop_engineering_20260814/thermal_cu_rethink_20260814/figures/nearfield_angle_and_chord_falsifier.png)

EventList 的 WorldFrame 方向约为 `(1/√2,0,-1/√2)`；旋转到 InstrumentFrame 后是
`(+1,0,0)`。把 WorldFrame 轴直接与 `tes_511_IF_*` 点积会错误地产生 4 条/98.336 counts
的 10° 内事件；正确同坐标计算为 `0/418`。

全部 signal 在 `x_IF=-3.15 cm` 的 footprint 为
`y=[-1.217,+1.402] cm, z=[-6.512,-3.928] cm`。delayed 中 92.263% 从其他五个面进入；
同为 `x-` 面且落在完整 signal footprint 的只有 250.427 counts，加两条方向 UNKNOWN 后
为 279.589 counts，即 full-D 的 0.314835%。这使五面 passive shadow 成为本轮唯一真正
由 signal 与 delayed 完整分母共同支持的机制。

但一个 material shadow 不是二元 mask。以 Cu 511-keV removal scale
`mu≈0.749 cm^-1`，只让外层 BGO 处理 prompt 时，拒绝面必须有连续 Cu chord。真实几何
约束为：

| location | maximum available continuous Cu chord | required |
|---|---:|---:|
| square TES/support corner to Nb bore | 1.384 cm | 2.308–3.140 cm |
| face center to Nb bore | 2.150 cm | 2.308–3.140 cm |
| `x+` end, including zero-clearance limits | 0.410 cm | 2.308–3.140 cm |

`z+` 的 Mu 外缘到 MXC 仅 0.45 cm，`z-` 到 can top 仅 0.05 cm；Nb/Mu back caps 的中央
`r<1.85 cm` 是 cold-finger hole。这些是当前真实 proxy 的硬包络，不会因冷盘外径缩 25%
或厚度减 10% 而消失。更强的反事实上限也失败：即使把 Nb 内孔所有可用净空零间隙填满，
并把 L0/can 的吸收重复、过度地算作收益，对全部 420 条 delayed 的最大抑制也只有
`62.7748%`；残余仍为 `0.0202802 cps`，即使 prompt=0 也高于 baseline-S20 对应的
`0.01600955 cps` 门。因此不是把 Cu 由 2.15 cm 再挤厚一点就能救活这个拓扑。故未生成
PA-X1 proxy，也没有把理论角分离冒充候选 F3。

## LOOP 判决收敛

| topology | decision | direct reason |
|---|---|---|
| 48 cold-core Cu→Al | KILL | 违反 thermal-Cu 功能；新 Al activation 未闭合 |
| skeletal / event-directed cold plate | KILL | 违反用户边界或用少数 survivor 选孔 |
| legal cold-plate OD/t/M4 | KEEP as auxiliary only | delayed 乐观信用 10.22%；prompt 记零 |
| Nb/Mu-only 或 R8–10 cm standoff | KILL | 预算不足且真实 MXC/cap/W 包络冲突 |
| +4 cm full-wrap BGO | KILL as unified | actual delayed outer reach 10.59%，所需 91.99% |
| 65Cu isotope-only | KILL | known-channel 净信用仅 3.70%；target isotope 不闭合 |
| PA-X1 five-face nearfield shadow | KILL as geometry | 连续 Cu 弦最大值低于最低门，且未计自活化 |
| **S3d-O8 baseline** | **KEEP** | **唯一没有被现有证据直接证伪的硬件状态** |

65Cu 路线虽保留元素与导热性质，但现有 SIM/RP 不记录 target isotope。严格可识别的
`63Cu(n,gamma)64Cu` 完美删除信用也只有 14.86% D20、7 条、`Neff=4.74`；按自然丰度
放大 conventional 65Cu channel 后，净信用仅 3.70%，且 natural Cu 已有 8.761 Bq Cu-66
零 selected（只有有限上界）。因此没有为同位素 proxy 启动 Cosima。

## 为何没有运行 focused S20

本轮没有修改候选通过 P0 机制与几何门。按资源纪律，机制未闭合前不跑 transport；否则只会
用低统计输出掩盖已知的几何不可能性。故本轮没有 candidate-own central F3，也不声称达到
目标。现有两张初始物理图与本轮新增 falsifier 图均保留：

- [prompt 三视图射线与有分母漏率](/home/ubuntu/.codex/worktrees/6f6c/TES_511_Balloon/engineering/s3d_o8_loop_engineering_20260814/figures/prompt_threeview_denominator_leakage.png)
- [delayed 空间 bubble 与 production-to-W2 flow](/home/ubuntu/.codex/worktrees/6f6c/TES_511_Balloon/engineering/s3d_o8_loop_engineering_20260814/figures/delayed_space_production_w2_flow.png)
- [近场角分离与连续弦几何反证](/home/ubuntu/.codex/worktrees/6f6c/TES_511_Balloon/engineering/s3d_o8_loop_engineering_20260814/thermal_cu_rethink_20260814/figures/nearfield_angle_and_chord_falsifier.png)

机读最终判决在 `data/final_decision.json` 与 `data/final_loop_verdicts.csv`。所有旧 Al、BG-J4
和 Cu65 proxy 只保留作 provenance，不得作为 transport authority。
