# S3d-O8 独立 LOOP ENGINEERING 物理审阅与优化结论

日期：2026-08-14  
最终状态：**NO SOLUTION UNDER CONSTRAINTS**  
transport：**0 条新 history**；全部结论来自只读流式复核、真实 CSG 查询、现有完整分母与必要性上界。

## 0. 决策先行

本轮没有一个候选进入 focused transport，更没有进入 full chain。原因不是工作未完成，而是所有可被当前工程证据精确定义的简单候选都在任务书规定的第 1 层证据门就被证伪：即使给它们比物理现实更有利的“100% 去除、零 host migration、零 signal 损失”上界，仍不能达到目标。

官方同口径基线为

```text
prompt P0 = 0.0338429281309 cps
delayed D0 = 0.0544797522273 cps
total   B0 = 0.0883226803582 cps
S20        = 1645.387753 counts
F3         = 6.923750509e-5 photon cm^-2 s^-1
```

官方 81-node mission 积分为

```text
P20 =  55,398.979434 counts
D20 =  88,804.862652 counts
B20 = 144,203.842086 counts
B20,max = (S20/10)^2 = 27,073.008579 counts
required total reduction = 117,130.833507 counts = 81.2259%
```

`0.0165818098083 cps` 是在保持 baseline mission shape 与 `S20` 不变时对应的 constant-environment day-15 速率简写；最终判决同时用上面的 exact 20-day counts 复核，不把 day-15 component fraction 当作 mission time profile。

两个机制必须同时显著下降：即使 delayed 完全为零，prompt 仍超预算 2.04 倍；即使 prompt 完全为零，delayed 仍超预算 3.29 倍。

最有利的具名部件中央值组合是同时把 `MXC plate + Nb inner + Mu outer + L0 Cu` 的 delayed 贡献全部置零，并把所有 prompt 也置零。day-15 等效为 `B=0.0162846916592 cps`；按 exact parent half-life 与 81-node mission 积分为 `B20=26,387.036791 counts`、baseline-live `F3=2.96175e-5`。这要求四个独立热、磁、结构系统的贡献 100% 消失；baseline-live 下 `S20` 只下降约 1.28% 就会重新失败。它是必要性证明，不是候选。

唯一上游工程阻断项是：

> **缺少一份逐真实部件映射到 S3d-O8 transport volume、受配置控制的 as-built CAD/BOM/interface authority。**

该单一 authority 必须同时给出 post-machining 质量、允许增删区、真实 signal/service 与 BGO 读出孔洞、冷端热/承载接口、以及 Nb/Mu 材料、接缝和最低磁性能。现有 `.geo` 是 transport proxy，不能据此把跨四个功能系统的理想清零包装成“一个简单、质量守恒、功能保留”的工程拓扑。

## 1. 证据边界与归一化

### 1.1 Authority

- 唯一 S3d-O8 setup：`DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`，由 M05 `analysis_inputs.json` 选定。
- prompt 采用 corrected-keV gamma source；该 source 已包含 annihilation bump，未另加 mono-511。
- prompt denominator 是 `S3d_O8 × instant × gamma` 的全部 132 个 SIM、`3,207,738` 个 `IA INIT`、`TT=59.0965413 s`。132 个 source/SIM geometry header 全部闭合到同一 setup。
- delayed production 始终在 `S3d_O8 × BUILDUP × family` 内计算 `sum(RP)/sum(TT_family)`；每个 family 的 zero-RP DAT TT 已保留，family 从不合并作分母。
- delayed coupling 定义为 exact `family × volume × parent-ZA` key 的 `selected rows / realized decay triggers`；不是把 observed cps 粗暴除以 full-inventory Bq。
- 每个 delayed family 有 250,000 个 realized decay triggers。source-mix screen 仅在对应 key 有 realized denominator 时使用 `A_k(15d) × epsilon_k`；零 selected 是有限样本零观测，零 realized trigger 才是 UNKNOWN。
- 所有结果保持 geometry × mode × family 边界；没有把 frozen selection 的 `0.01692146 cps` prompt 与官方 common-response 的 `0.03384293 cps` 混在同一个 gate 中。

### 1.2 资源纪律

- 原始 SIM 从 `/home/ubuntu/TES_511_Balloon/runs/...` 流式只读；raw files copied = 0。
- 没有复制 GB 缓存，没有跑八族盲链，没有运行 transport。
- 当前 durable 包约为 MB 量级，只包含 CSV/JSON、审阅报告、查询/绘图脚本和三张静态图。

## 2. LOOP 1 — prompt：Localize -> Origin

### 2.1 一句话热点判断

**最大且最可信的 prompt “热点”不是一个方向或单一部件，而是“厚 active 层的随机零相互作用尾 -> 高 TES 固体角的内侧被动件 pair/停留/annihilation”这一机制拓扑。**

Nb、Cu、Mu、Al、SS 中没有一个获得了可外推的独立空间排名。S3d 只有两个 Step05 prompt 事件；Mass_model 的独立对照把 pair host 扩展到 Al/Nb/Cu/SS。任何从三条 survivor 选 sector、或从 2 个 Nb pair 点宣称全天角 Nb 主导，都会把 numerator 当 denominator。

### 2.2 三条真实粒子链

| event | primary / IF direction | active / passive grammage to PAIR | first key interaction | positron stop / annihilation | TES | active veto | Step05 |
|---|---|---:|---|---|---|---|---|
| 3883 | gamma 4.14829 MeV; theta 82.22 deg, phi 74.10 deg | 23.4341 / 20.2713 g cm^-2 | first IA after INIT is PAIR in Nb inner sleeve | Mu-metal outer sleeve | L2 one pixel, 510.99891 keV | six active scorers all 0 | pass |
| 19932 | gamma 5.76882 MeV; theta 135.23 deg, phi 291.68 deg | 38.9233 / 32.6738 g cm^-2 | PAIR in DR mixing Cu | local DR Cu | L2 one pixel, 510.99891 keV | all 0 | pass |
| 8081 | gamma 6.34594 MeV; theta 144.80 deg, phi 14.70 deg | 29.7540 / 18.1229 g cm^-2 | PAIR in Nb inner sleeve | L0 Cu support | L5 two pixels, 69.58439 + 441.41452 keV | all 0 | fail |

三条 primary 在 PAIR 前均无 COMP/PHOT/RAYL；PAIR 点对 INIT 射线的垂距只有 `1.84–2.82 micrometre`，与 SIM 五位小数打印精度一致。三条都穿过真实 active CSG：

- 3883：1.0494 cm plastic + 3.1483 cm BGO；
- 19932：1.3226 cm plastic + 5.2903 cm BGO；
- 8081：1.0110 cm plastic + 4.0440 cm BGO。

因此“active 几何孔漏/低 active grammage corridor”对这三条事件已被 **KILL**。它们没有 veto，不是因为 50 keV 阈值别名或 scorer 漏记，而是六个 active volume 中确实没有任何 `CC HIT`：这是穿过 3.15–5.29 cm BGO 后恰好未发生相互作用的稀有随机尾。

### 2.3 有分母的能量、方向和 grammage

完整 gamma denominator 给出：

```text
all histories: 3,207,738
veto survivors: 3, p = 9.3524e-7/history
one-sided exact 95% upper: 2.4172e-6/history
central veto-leak rate: 0.0507644 cps
Step05 survivors: 2, central 0.03384293 cps
Step05 one-sided 95% upper rate: 0.106534 cps
```

三个非零 `E × equal-solid-angle direction × active grammage` cell 为：

| event | E bin | mu_x bin | azimuth | G_active bin | N incident | k | one-sided 95% k/N upper |
|---|---|---|---|---|---:|---:|---:|
| 3883 | 4–5 MeV | 0–0.25 | 45–90 deg | 15–25 g cm^-2 | 71 | 1 | 6.51% |
| 19932 | 5–6 MeV | -0.75–-0.5 | 270–315 deg | 35–50 g cm^-2 | 94 | 1 | 4.95% |
| 8081 | 6–8 MeV | -1–-0.75 | 0–45 deg | 25–35 g cm^-2 | 92 | 1 | 5.05% |

每个 cell 的 leakage `Neff=1`。去掉 grammage 轴后，三个 joint E×direction cell 的 N 也只有 867、702、633，各仍只有一个 survivor。`1,924,489` 条来向半射线的 active grammage 约为零，但其中 pre-W2 为零；三条 leak 都在 15–50 g cm^-2 厚层。零 grammage population 中很多只是没有进入内侧 causal envelope，所以不能用它估算效率；但足以排除把已观察 leak 归入 aperture population。

### 2.4 pair-opacity × TES-solid-angle × no-veto 排名

可验证的共同因子是

```text
inner passive pair opacity
  × positron stop/annihilation probability
  × TES solid angle / transport escape
  × active no-hit probability.
```

当前数据不能给 Cu/Nb/Ag/Mu/W 一个诚实的全天角数值排名：

- S3d 的两个 Step05 event 等权，一条源于 Nb->Mu，一条源于 DR Cu->Cu；第三条 Nb->L0 Cu 因两像素被 Step05 拒绝。
- Mass_model 的六条 final gamma 分别首次 pair 于 4 K Al cap、Nb、MXC Cu、SS rod、L0 Cu、50 mK Cu can；另一个 e+ 事件为 BREM -> Nb cap PAIR -> Nb cylinder ANNI。
- 没有 final pair host 在 CsI/BGO 或 W；一个 Mass gamma 在 CsI 只有 31.79 keV，低于 50 keV veto，其余 active 为零。

所以保留的是“内侧被动件共同机制”，而不是 `Nb > Cu > Mu > Ag > W` 之类由三个 numerator 拼出的伪排名。W bottom 距 TES 更远且三条 S3d 中只有一条在 PAIR 前穿过它，但这只是几何先验，不是 W2 leakage 概率。Ag 当前没有 prompt survivor；这同样不是零 coupling。

## 3. LOOP 1 — delayed：Localize -> Origin

### 3.1 一句话热点判断

**MXC 50 mK Cu plate 是唯一可保留的第一定位靶：它是 official observed 与 full-inventory source-mix screen 中最大的具名 aggregate，并有 21 个 source positions；但 position Neff 只有 7.77，因此它仍只是 localization，不是可晋级的几何收益。**

完整 delayed 为 420 selected rows、`0.0544797522273 cps`；event `Neff=28.754`，66 个独立 source positions，position `Neff=24.928`。所有具名 component 的 position Neff 都低于 8。

### 3.2 production Bq 与 W2/decay coupling 分开

| component | production s^-1 | day-15 Bq | official W2 cps | source-mix screen cps | supported W2/Bq | Bq coverage | position Neff |
|---|---:|---:|---:|---:|---:|---:|---:|
| MXC 50 mK plate | 28.51245 | 20.28089 | 0.01677150 | 0.01878838 | 9.757e-4 | 94.95% | 7.773 |
| Nb inner sleeve | 4.31151 | 1.01631 | 0.00780860 | 0.00756042 | 9.630e-3 | 77.25% | 2.953 |
| Mu outer sleeve | 4.70608 | 1.15215 | 0.00776545 | 0.00548405 | 7.570e-3 | 62.88% | 2.930 |
| L0 Cu support | 0.37160 | 0.24489 | 0.00584951 | 0.00748044 | 4.407e-2 | 69.32% | 2.194 |
| 50 mK can bottom | 9.85412 | 6.77797 | 0.00401569 | 0.00434965 | 7.078e-4 | 90.67% | 3.133 |
| L5 Cu support | 0.07960 | 0.04990 | 0.00305015 | 0.00099809 | 2.000e-2 | ~100% | 1.000 |
| L2 Cu support | 0.12225 | 0.07236 | 0.00139289 | 0.00131993 | 5.882e-2 | 31.01% | 1.000 |
| Ag proxy | 4.63560 | 4.56151 | 0.00112166 | 0.00096842 | 2.255e-4 | 94.14% | 1.000 |

`DR_MixingChamber_Cu` 的 full flow 为 production `1.93979 s^-1`、day-15 `1.41346 Bq`；当前 realized fold 中 selected rows 为零，因此其 delayed coupling 是 **UNKNOWN**，不是零。

七个独立 proton-family source positions 各自权重都是 `0.003050154 cps`，每个单点占全天 delayed 5.60%：MXC Cu-61、MXC Cu-62、L5 Cu-64、Mu V-46、Mu Fe-53、Nb Y-85、Nb Zr-85。图中全部以红边显示，禁止被平滑热图掩盖。

MXC 的 21 个 official source positions 中：

- local radius `<3 cm` 占 MXC selected rate 51.99%；
- `<7.62 cm` 只占 62.15%，外侧仍占 37.85%；
- negative local-z face 占 73.04%。

这证伪了“全部 MXC hotspot 都在 r<7.62 cm”的绝对说法；由于 exact-position realized denominator 不存在，它也不能反向证明裁外圈有确定收益。

### 3.3 n/p/alpha production origin

现有 rich BUILDUP SIM 内同一 history ID 同时有 `IA INIT` 与 `CC IP RP`。只读扫描保留 577 条目标 RP，与 inventory key 零 mismatch：

| family | all INIT denominator | sum TT |
|---|---:|---:|
| n | 232,991 | 44.5656746 s |
| p | 25,448 | 20.0382191 s |
| alpha | 4,343 | 33.6719935 s |

每个 family 单独建立 primary energy decade × IF theta 30 deg × azimuth 45 deg 全 INIT denominator。对 Cu-61/62/64 的 RP-conditioned primary 分布：

| family | parent | RP | primary median E | theta range | dominant creator mechanism |
|---|---|---:|---:|---|---|
| n | Cu-61 | 15 | 1.009 GeV | 31.3–149.2 deg | 9 neutronInelastic，少量 p/pi secondary |
| n | Cu-62 | 55 | 1.361 GeV | 8.9–168.3 deg | 51 neutronInelastic |
| n | Cu-64 | 161 | 0.216 GeV | 9.9–175.2 deg | 111 nCapture + 46 neutronInelastic |
| p | Cu-61 | 24 | 16.201 GeV | 11.1–126.9 deg | 14 neutronInelastic + 6 protonInelastic |
| p | Cu-62 | 55 | 17.024 GeV | 5.6–132.1 deg | 44 neutronInelastic |
| p | Cu-64 | 118 | 18.672 GeV | 8.3–138.0 deg | 84 nCapture + 31 neutronInelastic |
| alpha | Cu-61 | 13 | 31.800 GeV | 36.9–127.5 deg | 8 neutronInelastic |
| alpha | Cu-62 | 37 | 41.594 GeV | 21.4–169.8 deg | 32 neutronInelastic |
| alpha | Cu-64 | 77 | 36.334 GeV | 7.6–135.1 deg | 52 nCapture + 22 neutronInelastic |

直观图像是：高能 primary p/alpha 在装置中形成级联，关键 Cu parents 多数由 secondary neutron capture/inelastic 产生，而不是 primary p/alpha 直接打到 Cu 后简单线性活化。方向范围很宽，因此没有证据支持一个窄 BPE sector。

稀疏的磁屏蔽链同样不能被隐藏：

- `p -> Y-85 @ Nb`：2 RP、0.0998093 Bq；一条 24.295 GeV direct pInel，一条 88.445 GeV pi-minus capture；decay transport 1/39，official 0.00305015 cps。
- `n -> Nb-89 @ Nb`：2 RP、0.0448776 Bq；35.045 GeV secondary-p 与 345.051 GeV pi-minus；1/34，0.00139289 cps。
- `n -> Co-54 @ Mu`：1 RP、0.0224388 Bq；2.551 GeV n primary 产生 secondary pi-plus inelastic；1/19，0.00139289 cps。
- p/alpha 的若干 Nb-89/Nb-90 key 目前 0 selected，但 one-sided 95% coupling upper 为 4.57–7.39%，不能称作零。

## 4. LOOP 2/3 — Optimize -> Prove/Falsify

候选必须先过解析必要性门；上一层失败即停止。下表中的“100% removal”故意把全部 prompt 同时设为零、把指定 delayed 贡献完全设为零、假设无 host migration 且 `S20` 不变，因此比任何真实几何更有利。

| round / topology | precise scope or hypothesis | day-15-equivalent residual / exact B20 | exact baseline-live F3 | verdict | falsifying evidence |
|---|---|---:|---:|---|---|
| P0 aperture/sector fix | 从三条 leak 选择 BGO donor/receiver sector、关闭 top/relief | not assigned | — | **KILL** | 三条均穿厚 active；E×dir×G cells 各 Neff=1；没有一条走 top annulus/relief；无 named-face denominator |
| C1 `G-Nb-S1` | Nb sleeve r=4.0..4.2 -> 4.0..4.1 cm；轴长、2 mm back cap、全部 Mu/Cu/BGO/BPE/TES/W 不变；Nb system 0.427585->0.249930 kg | 0.04667115 cps / 76,007.824 counts | 5.02669e-5 | **KILL** | 完美去除仍超过 B20,max 2.81 倍；即使 accidental live=1 仍为 2.75 倍；真实 2->1 mm 只能更弱，且 DR Cu/Mu/Ag/MXC migration 活跃 |
| C2 MXC-only | 任意只改变 MXC plate 的 pocket/radius/thickness，甚至假设整个 MXC contribution 消失 | 0.03770826 cps / 61,374.930 counts | 4.51698e-5 | **KILL** | 完美去除仍超过 B20,max 2.27 倍；即使 live=1 仍为 2.22 倍；MXC position Neff=7.77；37.85% contribution 在 r>7.62 cm |
| C3 all-Cu class ceiling | 假设所有 observed Cu delayed 与全部 prompt 同时消失 | 0.01808860 cps / 29,528.548 counts | 3.13310e-5 | **MODIFY / not sufficient** | exact central 仍超 B20,max 9.07%；即使 live=1 仍超 6.80%；source-mix screen 的表面 pass 小于低-Neff fluctuation scale，且接近删除整个热/结构材料类 |
| C4 Nb+Mu class ceiling | 假设全部 Nb+Mu delayed 与全部 prompt 同时消失 | 0.03751281 cps / 61,199.721 counts | 4.51053e-5 | **KILL** | 完美去除仍失败；同时破坏两套磁屏蔽功能 |
| C5 minimum named crossing | MXC + Nb inner + Mu outer + L0 全部 delayed 置零且 prompt=0 | 0.01628469 cps / 26,387.037 counts | 2.96175e-5 | **KILL / NON-ADMISSIBLE** | 至少四个独立功能系统需近乎 100% 清零；position Neff=15.68；baseline-live 下 1.28% signal loss 即失败；现有 CAD/BOM 无法定义功能保留拓扑 |

Exact B20 复核不是把 day-15 rate 乘 20 天：每条 420-row selected lineage 按 exact `family × parent-ZA` 接到 `family_parent_activity_by_time.csv` 的 81-node activity scale，再乘对应 quadrature weight 与 baseline accidental-live factor。各 component 回和到 `D20=88,804.862652 counts`。另外把 live factor 取到物理最大值 1，并用 no-accident `S20=1680.955736` 重算最有利门；G-Nb、MXC 与 all-Cu 仍分别超门 2.75、2.22、1.068 倍。因此它们的 KILL/不充分结论不是 day-15 half-life proxy 造成的。

历史 LC1 的 8192 个 root-19932 定向 gamma 只给出 baseline/Cu-only/Cu+Nb 的 raw `W2+veto50 = 1/2/1`，同时显示 pair host 迁到 Ag、Mu、MXC；它没有证明 prompt 降低。LC2 event-coordinate excision 与 uniform-activity mass scaling 不是物理上下界，也没有候选自己的 S20/INSTANT/BUILDUP/delayed/common-response closure，因此没有被当作答案维护。

### 4.1 为什么不运行 focused S20

任务书要求证据阶梯：解析门失败就停止候选。C1/C2/C3/C4 即使 `S20` 完全不损、全部 prompt 清零、目标 component delayed 100% 清零仍失败；为它们跑 signal 或 transport 不会改变这个必要性结论，只会消耗资源。

C5 虽在纯算术中央值上擦线，但不是一个工程允许的几何：MXC、Nb、Mu、L0 分别承担 50 mK 热化/载荷、超导磁屏蔽、高磁导屏蔽和 TES 支撑/热路；将四者贡献设零不等于一个可加工 topology。没有 exact candidate geometry，就不存在可合法计算的 candidate-own `S20`。因此本轮正确动作是停在 gate，而不是把 baseline S20 冒充 candidate S20。

### 4.2 外层 BGO/BPE 为什么也不能成为“唯一候选”

- transport proxy 的 BGO side/bottom/top pre-relief mass 为 296.5499 kg，BPE 为 33.6056 kg；当前 **certified reallocatable mass=0 kg**。
- ledger 使用不同 BGO 密度且自称 pre-relief bookkeeping；不是整机或结构质量 authority。
- BGO、W grid、Cu can、Nb/Mu open end 共享约 37.96 mm corridor，但 BPE/plastic 在 proxy 中是没有对应 side window 的 full annulus。真实 signal/service/BGO readout aperture 不能由该 proxy 推断。
- prompt 三条方向不重复；delayed n/p/alpha product directions 很宽。把未出现 numerator 的 sector 当 donor 会创建未量化的新 low-grammage path。

所以当前 BGO 4 cm side / 3 cm bottom / 1 cm top-annulus 作为 prompt reference **KEEP**；由三条 survivor 选择定向重分配 **KILL**。这不表示未来任何 BGO/BPE 重分配都无效，只表示当前没有一个 denominator-supported、质量和光路可认证的 topology 可冻结。

## 5. 最终工程判断

### 5.1 当前允许集内的唯一最优选择

没有满足目标的 admissible modification。工程上应保留 baseline，而不是实施一个已被预算证伪或无法定义接口的改动。baseline 本身不满足 `F3<=3e-5`，所以最终状态不是 `ENGINEERING-CONDITIONAL OPTIMUM`，而是 **NO SOLUTION UNDER CONSTRAINTS**。

这不是并列建议列表：

```text
single decision = do not modify/fabricate from the transport proxy;
status          = NO SOLUTION UNDER CONSTRAINTS;
single unblocker= configuration-controlled as-built CAD/BOM/interface authority.
```

### 5.2 取得唯一 authority 后的直接 falsifier

一旦该 authority 能定义一个真实、单一、功能保留的 cold-core 或 shield topology，仍需按同一顺序证明：

1. matched prompt denominator 下总 pair->ANNI->TES rate 必须下降，且 host 不迁到 DR Cu/Mu/Ag/MXC/Al/SS/W；
2. 只对受影响的 n/p/alpha denominator cells 重算 production，任何 >10% path 要 production-history Neff>=30 且单 history<10%；
3. exact candidate source mix 的 selected event/position Neff>=30，或 one-sided upper 已低于分配预算；
4. candidate-own focused `S20` 与 20-day common response 给出 central `F3<=3e-5`，并另报预注册 one-sided conservative bound。

这些是未来唯一候选的 falsifier，不是本轮并行候选。

## 6. 关键图与 durable artifacts

### Prompt 三视图、真实切片与完整 denominator

`../figures/prompt_threeview_denominator_leakage.png`

图中：真实 IF 三投影、active/BPE/BGO/core proxy 截面、三条 INIT->PAIR 射线、PAIR/ANNI/TES 点、active/passive grammage、全能量 denominator，以及离散 equal-solid-angle direction k/N；无平滑。

更细的 `E × direction × active grammage` CSV：

`../agents/prompt/denominator/incident_gamma_E_mux_az_active_grammage.csv`

### Delayed 空间 bubble 与 production->W2 flow

`../figures/delayed_space_production_w2_flow.png`

图中：66 个离散 source positions；颜色=材料、形状=incident family、面积=observed selected W2、红边=单事件高权重；右上为 family->material->parent isotope->volume->W2 flow；右下将 day-15 inventory Bq 与 supported W2/decay 分开。

### 候选 exact 20-day mission 严格乐观上界

`../figures/candidate_mission_count_gate.png`

420-row lineage 按 exact family×parent-ZA half-life 接到 81-node mission；每个候选 scope 同时获得不可能的 `prompt=0` 优惠。只有非工程允许的四功能系统 100% 清零柱低于 `B20,max`。

day-15 等效交叉检查：

`../figures/candidate_optimistic_ceiling_gate.png`

所有 component/material case 都先把 prompt 设零；位于绿色门线上方的 case 在任何真实 host migration、signal loss、统计不确定性之前已经失败。
该图采用 day-15 constant-environment 等效速率便于直观比较；第 4 节的 exact 81-node `B20`/F3 表是 mission 判决 authority。

主要机读产物：

- `../data/candidate_budget_screen.csv`
- `../agents/delayed/mission_component_necessity.csv`
- `../agents/prompt/prompt_leak_interaction_points.csv`
- `../agents/prompt/prompt_leak_material_chords.csv`
- `../agents/prompt/denominator/incident_gamma_E_mux_az_denominator.csv`
- `../agents/prompt/denominator/incident_gamma_E_mux_az_active_grammage.csv`
- `../agents/delayed/delayed_position_bubbles.csv`
- `../agents/delayed/delayed_production_to_w2_flow_compact.csv`
- `../agents/delayed/delayed_key_flow.csv`
- `../agents/delayed/target_production_origin_events.csv`
- `../agents/delayed/incident_primary_energy_direction_denominators.csv`
- `../agents/geometry/candidate_mass_calcs.csv`

独立子审阅：

- `../agents/prompt/PROMPT_PHYSICS_AUDIT.md`
- `../agents/prompt/PROMPT_CANDIDATE_NECESSITY.md`
- `../agents/delayed/FACT_UNKNOWN.md`
- `../agents/delayed/DELAYED_CANDIDATE_NECESSITY.md`
- `../agents/delayed/MISSION_COMPONENT_NECESSITY.md`
- `../agents/geometry/GEOMETRY_BOM_ENGINEERING_REVIEW.md`
- `../agents/geometry/FINAL_CANDIDATE_NECESSITY.md`
