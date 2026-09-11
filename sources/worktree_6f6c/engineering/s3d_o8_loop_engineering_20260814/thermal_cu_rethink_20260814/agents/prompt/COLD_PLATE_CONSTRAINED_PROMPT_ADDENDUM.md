# S3d-O8 prompt addendum：冷盘受限后的唯一候选 BG-TAU5

> **FINAL STATUS NOTE:** 后续真实包络审查又证伪了 `DR Cu/Ag + Nb/Mu standoff + 1--3 cm BGO`。冻结的最终 prompt 判决、standoff 尺度、BPE 顺序和 relief 分母门见 `FINAL_PROMPT_VERDICT.md`。本文件的 BG-TAU5 optical-depth 结论仍有效。

## 结论

新机械边界立即 **KILL TC-SK1 skeletal cold plates**：冷盘外径最多缩小 25%，厚度最多减少 10%，仅允许少量 M4 孔。即使把所有允许改动取到最激进端，最终 prompt 根 19932 的 anti-TES 511 仍需穿过几乎全部冷盘与服务 Cu；因此冷盘不再是可承担主要 prompt suppression 的自由度。

唯一可精确定义、非三事件定向的 prompt 候选改为：

> **BG-TAU5：保持冷盘、L0、can、service、Nb/Mu 和 Ag 基线不变；只在现有 BGO detector/readout channel 上增加连续 side/bottom/top active BGO，使每条不穿不可避免 service relief 的 4--8 MeV 入射直线满足新增 optical depth `Delta tau_BGO >= ln(5)=1.609438`。top annulus 在真实服务 relief 外尽量关闭中央开口；不新增 detector、scorer 或读出。**

这是 `ENGINEERING-CONDITIONAL PROMPT OPTIMUM`，不是已经证明的飞行方案。选择保持近场件基线是有意的：L0/can/service 的改动可以因 delayed/热结构需要另行进入统一候选，但现有 prompt 证据不能给它们分配可靠 suppression；Nb/Mu 改动还会产生 pair-host migration。为了让本轮只有一个可证伪拓扑，不能把未知近场收益加到 BGO 账上。

若 payload/结构无法承受新增 BGO，或 paired transport 的 prompt survival 单侧 95% 上限仍大于 0.20，则 **KILL BG-TAU5**。在当前硬约束内没有第二个已被分母支持的 prompt 拓扑；不能退回 Cu→Al、mK guard、事件定向 sector 或近 TES W/Pb。

## 1. 受限冷盘能做多少：逐射线最大收益

用真实 partner CSG chord，把每块被穿冷盘的厚度减到 90%，并把外径减到 75%。外径缩小只使 3883 绕开 4K plate；19932 与 8081 在它们所穿冷盘平面仍位于缩径后的盘内。

| event | baseline Cu chord (cm) | most aggressive allowed Cu chord (cm) | Cu-only survival baseline | allowed-limit survival | gain |
|---|---:|---:|---:|---:|---:|
| 3883 | 2.906 | 1.962 | 0.113 | 0.230 | 2.03x |
| 19932 | 3.946 | 3.763 | 0.052 | 0.0597 | 1.15x |
| 8081 | 1.844 | 1.685 | 0.251 | 0.283 | 1.13x |

这里仍只用了 `T_Cu=exp(-0.749 L_Cu)` 的 511-keV 未碰撞标度。3883 还有 `1.483 cm Ag proxy`，19932 还有约 `4.768 cm SS + 2.029 cm BPE + 1.217 cm Al`，8081 还有固定 Nb/Mu。真实 sibling-to-BGO coupling 只能更复杂。

最终 prompt 是 3883 与 19932 两条等权链。即便允许改动能完美杀掉 3883、而 19932 完全不变，rate survival 仍为 0.5，远高于预登记 0.20。因此：

- 冷盘 10% 减薄：`KILL AS PRIMARY LEVER`；
- 冷盘 25% 缩径：`KILL AS PRIMARY LEVER`；
- 少量 M4 孔：`KILL AS RATE CLAIM`，因为三条 leak 分属三个 `Neff=1` 的方向/能量/grammage 格，按事例打孔没有分母支持。

机读复算在 `cold_plate_constraint_scaling.csv`。

## 2. 为什么主杠杆只能回到现有 active BGO optical depth

三条 primary 并没有绕开 BGO；它们无碰撞穿过 `3.148/5.290/4.044 cm` BGO 与约 1 cm plastic，active edep 严格为零，然后在 Nb/Cu/Nb pair。降低阈值、内层 BPE、移动少量 L0/can mass 都不能改变这段无碰撞尾。

完整 gamma 分母为 `3,207,738` histories；三个 leak cell 是 `1/71`、`1/94`、`1/92`，没有可重复 incident sector。因而只允许两种逻辑：

1. 全方向提高现有 active channel 的 optical depth；或
2. 承认在当前机械/active-channel约束内没有 prompt solution。

BG-TAU5 选择第一种，并把失败条件写死。

以 5.7688 MeV 的 `mu_BGO≈0.276 cm^-1` 作参考，条件于已经出现的 uncollided primary leak，新增 BGO 的标度为

`T_primary,new / T_primary,baseline = exp(-mu_BGO Delta L)`。

要使该比值为 0.20，需要

`Delta L = ln(5)/0.276 = 5.831 cm`。

但 4--8 MeV 的系数随能量变化，且 oblique path 与 relief 不同，所以候选不以“所有地方机械地加 5.831 cm”为最终定义，而以 `min Delta tau >= ln(5)` 为几何门。`5.831 cm` 只是 5.77-MeV 尺度。

该机制不依赖三条 survivor 的方位。它也不依赖 cold-core pair host 是 Cu、Nb、Mu、Ag 或 SS：primary 在进入这些体积前先由同一 active channel 截获。

## 3. 候选几何边界

- **Side**：现有 4-cm BGO side shell 向允许的温级/外侧增加材料，使所有非 relief side rays 的新增 optical depth 达门。
- **Bottom**：现有 3-cm bottom cap 同样增加 optical depth。
- **Top**：现有 1-cm top annulus 保持同一 channel，在真实 service relief 之外关闭中央大开口并增加 optical depth。不可把服务孔虚构成实心 BGO；所有 relief 必须有单独 incident denominator。
- **Cold core**：所有 cold plates、L0、can、service、Nb/Mu、Ag 在首个 prompt paired run 中保持 baseline。这消除了 host-migration 与热边界混入 BGO 因果检验。
- **Signal**：候选必须对冻结 focused signal EventList 保持新增 active chord 为零；否则 KILL。
- **No new channel**：新增 BGO 必须归入现有 detector/readout logical channel。若现有光收集和动态范围不能接受增加体积，则工程 KILL，而不是添加新通道。

### 质量尺度，不冒充 BOM

当前几何注释给出 pre-relief BGO 质量约：side `250.69 kg`、bottom `42.67 kg`、top `4.44 kg`，合计约 `297.8 kg`。

若最简单地把 5.77-MeV 参考厚度 `5.831 cm` 全部向 side 外侧增加、bottom 轴向增加，并把 top 内半径从 `20.9 cm` 收到 `4 cm` 后增加同样轴向厚度，解析 PCON/圆盘尺度给出：

- side 增量约 `441 kg`；
- bottom 增量约 `82.6 kg`；
- top 增量约 `89.9 kg`；
- 总增量约 `614 kg`，新 BGO 总量约 `910 kg`。

这些数忽略 subtraction relief、支撑、封装和光收集，只说明量级。它们直接暴露 BG-TAU5 的唯一工程风险：对 balloon payload 很可能过重。允许增加质量不等于质量无限；payload/结构门失败即 KILL。

实际工程可把一部分 BGO 向内靠近以降低外半径的面积代价，但不得进入 mK stage、遮挡 signal、与 cryostat/service overlap，且仍须满足逐射线 `Delta tau` 门。没有真实 CAD 前不声称 614 kg 是最终质量。

## 4. L0 / can / service / NbMu 的判决

| component | prompt verdict | reason |
|---|---|---|
| L0 disk / can bottom | `KEEP BASELINE IN PAIRED PROMPT TEST` | 它们影响 8081/Mass sibling 与 delayed coupling，但不解决最终 19932 primary uncollided tail；同时改动会破坏 BG-TAU5 的单因子因果检验。 |
| Cu/Ni/SS service | `KEEP BASELINE IN PAIRED PROMPT TEST` | 清理服务 sightline 可帮助 top partner，却仍被受限 cold plates 阻挡；没有 partner 方向分母可给 rate。 |
| Nb/Mu | `KEEP BASELINE` | 两条 S3d 在 Nb pair；减薄/开孔会迁移到 Cu/Ag/Al，且有磁功能约束。 |
| inner BPE | `KILL FOR PROMPT` | 对 4--8 MeV primary 光学深度太小，并可能先于 BGO 散射 sibling。 |
| low-Z liner | `KILL AS SOLE PROMPT LEVER` | 增加低 Z 不会移除既有 pair hosts，也不能提供 active veto。 |

这不禁止 delayed 团队以后在同一个全局候选里修改 L0/can/service；只是 prompt 预算不得预先领取其未测收益。若全局候选包含这些改动，必须再做四态因果矩阵：baseline、BGO-only、nearfield-only、combined。最终仍只晋级 combined 一个方案。

## 5. 最小证伪测试

### G0：geometry-only

1. 对完整 incident gamma denominator 的 INIT rays 追踪新增 BGO chord，并按 `E x equal-solid-angle direction x active grammage x relief/non-relief` 输出 `Delta tau`。
2. 非 relief support 的最小 `Delta tau >= ln(5)`；relief 分母单列，不能丢弃。
3. 三条原始 leak ray 都必须增加真实 BGO chord；不是只把体积名改成 BGO。
4. frozen signal EventList 的新增 active chord 必须为零。
5. ROOT overlap、existing-channel scorer mapping、payload mass estimate全部 PASS。

### P1：三 cell paired mechanism

保持 cold core 完全相同，只比较 baseline 与 BG-TAU5。逐 cell 输出：

- primary 在新增 BGO 的 first interaction、deposit 与 `>=50 keV` veto；
- BGO 内 pair/Compton 后逃出的 gamma/electron/neutron；
- cold-core first-pair host、ANNI host 与 TES ancestry；
- final selection、event weight 与 Neff。

候选不是以 any-interaction proxy 过门，而是 final prompt candidate/baseline exact one-sided 95% upper `<=0.20`。若 candidate 为零、equal exposure/equal weight，baseline 至少需 17 个 final survivor；否则用准确 rate-ratio interval。

### P2：完整 corrected gamma

P1 通过后才做完整 gamma support，保持 `geometry x mode x family` normalization。按旧 exposure 尺度，零 candidate 时约需 `27.27M histories`、`TT≈502.3 s` 才能将 ratio upper 压至约 0.193。必须保留 relief denominator 与单事件高权重。

### Delayed / engineering veto

BGO 增量会增加 Bi/Ge/O 生产、hadronic secondaries、光学/readout 负担和结构质量。即使 prompt P2 通过，只要 BGO 自身 production Bq × W2/Bq coupling 使联合 mission gate 失败，或 payload/结构不允许，BG-TAU5 仍为 KILL。

## 最终 KEEP / KILL

| topology | verdict |
|---|---|
| TC-SK1 cold-plate skeletal | `KILL — violates new mechanical boundary` |
| max-allowed 25% OD / 10% thickness cold-plate change alone | `KILL — 19932 survival scale improves only ~15%` |
| M4 holes chosen from three survivors | `KILL — no directional denominator` |
| L0/can/service-only | `KILL AS PROMPT SOLUTION` |
| Nb/Mu thinning/opening | `KILL` |
| Cu→Al or mK active guard | `KILL BY USER CONSTRAINT` |
| **BG-TAU5 existing-channel full optical-depth increase** | **`KEEP — ENGINEERING-CONDITIONAL, FOCUSED FALSIFICATION ONLY`** |

唯一阻断证据不再是 cold-core sightline，而是：**能否在 payload、service relief、signal 和 BGO activation 边界内实现 `Delta tau>=ln(5)`，并使完整 corrected-gamma prompt ratio 的单侧 95% 上限 `<=0.20`。**
