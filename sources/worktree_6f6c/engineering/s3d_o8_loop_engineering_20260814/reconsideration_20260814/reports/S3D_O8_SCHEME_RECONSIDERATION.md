# S3d-O8 方案再审：AF1-48 条件最优

日期：2026-08-14  
判决：**ENGINEERING-CONDITIONAL OPTIMUM / KEEP FOR FOCUSED FALSIFICATION**  
性能状态：**focused signal 已通过；candidate-own background 尚未闭合；不得宣称 central F3 已达标。**

## 结论先行

上一轮“约束内没有可行方案”的结论应撤回。它正确地杀掉了 Nb-only、MXC-only、Cu-only 和方向扇区补屏，却把这些“独立删除上限”误扩展成了对所有耦合拓扑的否定。prompt pair/annihilation、delayed activation 和现有 BGO veto 不是彼此独立的桶：降低冷芯高/中 Z 宿主，既会改变首次 pair 与母核生产，也会改变 anti-TES 511 在到达现有 BGO 前被动吸收的概率。

重新执行 Localize → Origin → Optimize → Prove/Falsify 后，唯一保留方案是 **AF1-48**：

1. 只把精确白名单内 48 个非读出冷芯被动 Cu 体积同形换成现有元素 `Aluminium`；12 个 XS400/service/remote Cu 体积保持 Copper；
2. Nb 与 MuMetal 主套筒及后盖保持内表面、孔径和长度不变，厚度从 2.0 mm 减到 0.5 mm；
3. 保留原 outer BPE，在 `r=20.65..21.15 cm` 新增 5 mm inner BPE liner，并复制 signal/pump/NF2 relief；
4. 不增加 detector/channel，把同一个 top-BGO sensitive volume 从 `Rin=20.9 cm` 收到 `Rin=4 cm`，保留中央孔、12 个真实 service holes 与 6 个 NF2 relief。

权威代理 setup：

`engineering/s3d_o8_loop_engineering_20260814/reconsideration_20260814/agents/geometry/candidate_proxy/S3D_O8_unified_Al_mag05_innerBPE_topcatch_proxy.geo.setup`

它满足几何与质量代理门，也通过 candidate 自己的 37,194-event focused signal replay；但背景抑制仍只是条件预算。以尚未实测的 `sPrompt=0.80`、`sCu,net=0.95`、`sNbMu,eff=0.75`、`Delta_new=0` 代入时，残余为 `22,890.854 counts`，对应条件算术 `F3=2.74497e-5 photon cm^-2 s^-1`。**这不是 candidate central F3 结果**，因为 prompt suppression、near-TES Al activation、BPE/Nb/Mu 新耦合都尚未由候选自身 transport 测量。

唯一 promotion blocker 是一份 **candidate-own joint background-transfer closure**：在同一 mission-count 方程中，测出 prompt host migration/partner-veto survival，以及 48 个近 TES 元素 Al 位置连同 BPE、Nb、Mu 的 `production Bq × exact-position W2/Bq`。其中当前最强 delayed 子阻断证据是近 TES Al inventory-to-W2 coupling 完全未知；当前 prompt 子证据则统计上远不足以过门。

## 1. Localize：热点在哪里

### 1.1 Prompt：不是孔洞射线，而是厚 active 层中的零相互作用尾部

完整 corrected-gamma authority 含 `3,207,738` 个 IA INIT、`TT=59.0965413 s`。只有 3 条通过 50 keV active veto，其中 2 条再通过 Step05。三条都穿过厚 BGO/plastic，并非几何开口：

| event | 初级 gamma | IF 方向 `(theta, azimuth)` | active / passive grammage | 首次 PAIR → e+ ANNI | TES | Step05 |
|---:|---:|---:|---:|---|---:|---|
| 3883 | 4.148 MeV | `(82.22°, 74.10°)` | `23.434 / 20.271 g cm^-2` | Nb inner → Mu outer | 510.999 keV | PASS |
| 19932 | 5.769 MeV | `(135.23°, 291.68°)` | `38.923 / 32.674 g cm^-2` | DR mixing Cu → DR mixing Cu | 510.999 keV | PASS |
| 8081 | 6.346 MeV | `(144.80°, 14.70°)` | `29.754 / 18.123 g cm^-2` | Nb inner → L0 Cu disk | 69.584 + 441.415 keV | FAIL |

三条 active energy deposit 都是精确的 0。物理图像是：4–6 MeV gamma 从外部穿过 3.15–5.29 cm BGO 和约 1 cm plastic 的随机零相互作用尾部，进入低温被动件后首次关键相互作用即 pair；一条 511 进入 TES，反向 sibling 在 Ag/Cu/Mu 等内件被吸收或从顶孔逃逸，所以没有 active veto。

加入能量、等立体角方向和真实 active grammage 后，三条所在格分别只有 `k/N=1/71, 1/94, 1/92`，每格 survivor `Neff=1`。因此它们能定位机制，不能外推全天角漏率，也不能用来选择 BGO 扇区。

![Prompt 三视图、真实 grammage 与有分母漏率](../../figures/prompt_threeview_denominator_leakage.png)

### 1.2 Delayed：Cu 是聚合主项，但低 Neff 热点决定了不确定度

official delayed fold 有 420 条 W2、`0.0544797522 cps`，event `Neff=28.754`；66 个 source positions，position `Neff=24.928`。材料聚合中 Copper 占观测 delayed rate 的 66.80%，但 Cu 自身只有 event `Neff=22.48`、position `Neff=17.74`。MXC、Nb、Mu、L0 等单部件的 position `Neff` 均低于 8；L5、L2、Ag 各只有一个 source point。任何平滑 bubble/heatmap 都必须同时显示这些单事件权重。

母核并非简单的低能 direct p/alpha 反应。Cu-61/62/64 在 p/alpha family 中大多由 16–42 GeV primary cascade 产生的 secondary neutrons经 `nCapture/nInel` 形成；n family 的 Cu-64 primary median 约 0.216 GeV，Cu-61/62 约 1–1.36 GeV。完整分母为：

| family | IA INIT | TT | 主要物理图像 |
|---|---:|---:|---|
| n | 232,991 | 44.5657 s | 亚 GeV–GeV n 直接/级联后 capture 与 inelastic |
| p | 25,448 | 20.0382 s | 十几 GeV p shower，secondary-n 主导 Cu parent |
| alpha | 4,343 | 33.6720 s | 数十 GeV alpha shower，secondary-n 主导 Cu parent |

production 定义为同一 `geometry × mode × family` 内 `sum(RP)/sum(TT)`，包含零 RP DAT；coupling 定义为 realized exact source 的 selected W2/decay，不能用 `observed rate / full Bq` 冒充。0 selected 只给上限，0 realized trigger 则是 UNKNOWN。

![Delayed source-position bubble 与 production-to-W2 flow](../../figures/delayed_space_production_w2_flow.png)

## 2. Origin：为什么原来的“无解证明”过强

baseline mission counts 为：

| 项 | counts |
|---|---:|
| prompt `P20` | 55,398.979 |
| delayed `D20` | 88,804.863 |
| total `B20` | 144,203.842 |
| baseline signal `S20` | 1,645.388 |
| baseline count gate `(S20/10)^2` | 27,073.009 |

所以 prompt 即使归零，delayed 仍必须下降约 69.6%；这正确地 KILL 了 prompt-only 修补。另一方面，完美删除单个部件/材料也不足：MXC-only、Nb-only、Nb+Mu-only、甚至把旧 Cu selected term 归零的 central residual 都高于旧 gate。这正确地 KILL 了单旋钮方案。

错误发生在下一步：component-deletion ceiling 固定了 parent production、decay host、partner absorption、active-veto coupling 和 host migration，因而只能证明“独立删除这个桶不够”，不能证明“一个同时改变这些 transfer terms 的拓扑不存在”。AF1-48 采用的正是这个遗漏的共享杠杆：

- Cu→Al 和 Nb/Mu 减薄，降低冷芯 pair opacity 与 incumbent activation host；
- anti-TES 511 不再那么容易在 Cu/Nb/Mu 内部停止，更可能继续到现有 side/top BGO；
- inner BPE 改变到达冷芯的 neutron spectrum；
- top BGO 关闭已由 sibling 路径证实的顶部 active gap，同时保持原 detector/channel。

这不保证净改善；它只是使“无解”不再成立，并给出了一个简单、可证伪且质量闭合的候选。

## 3. Optimize：唯一 AF1-48 拓扑

### 3.1 几何、质量与硬约束

| 子系统 | baseline → AF1-48 | proxy mass change |
|---|---|---:|
| exact 48 cold-core volumes | Cu 20.273281 kg → elemental Al 6.113230 kg，同形同位 | −14.160051 kg |
| Nb/Mu sleeves + caps | 2.0 mm → 0.5 mm；内表面、孔径、长度不动 | −0.703210 kg |
| inner BPE | 保留 outer BPE；新增 5 mm relieved liner | +3.744416 kg |
| same-channel top BGO | `Rin 20.9→4 cm`，厚 1.15684119 cm，12 service + 6 NF2 relief | +11.118845 kg |

changed scope 的 fixed-seed CSG 名义账为 `25.557648730 → 25.557648934 kg`。ROOT Boolean `Capacity()` 是 Monte-Carlo 体积，正确声明是**质量守恒到数克**，不能把名义 `+0.204 mg` 当作 BOM 精度。

最终 ROOT checker 扫描 3,106 volumes，`overlap_ok=1`；`.det` byte-identical。没有新增 active guard、读出 channel、mK scintillator、readout Cu、复杂微加工或近 TES W/Pb。solid top 版本与 12 根真实 300 K top pipe 相撞，已在最终候选中用实际 service relief 修正。

唯一工程硬门是组合资格包：元素 Al 冷盘/罐/支撑在 50 mK–4 K 的热导、接触、承载与循环稳定性，以及 0.5 mm Nb/Mu 的残余场、seam、field-cool 与 flux-trapping 性能。proxy overlap 不能替代这项资格。

### 3.2 为什么必须是统一方案

| 简单拓扑 | LOOP verdict | 理由 |
|---|---|---|
| 只按 3 条 survivor 加方向 sector | KILL | 每个方向/能量/grammage 格只有 1 条 survivor，无全天角证据 |
| Nb-only / Nb+Mu-only | KILL | 理想删除仍不过预算；pair/activation 会迁移到 Cu/Ag/Al |
| MXC-only / Cu-only | KILL | 理想 central ceiling 仍高于 gate；不解决 Nb host 与 top escape |
| top-BGO-only | KILL | 只补 active gap，不降低内部 pair/partner absorption 或 delayed production |
| 60-volume blanket Cu→Al | KILL | 多改 12 个无 observed delayed credit 的 service/interface Cu，只增加新 Al 风险 |
| 无 service holes 的 solid top | KILL | 与真实 top pipes overlap |
| “6061”无精确 alloy card | KILL | 元素/杂质 activation 不可审计 |
| **AF1-48 unified** | **KEEP / MODIFY** | 唯一同时作用于 Cu/Nb host、partner absorption、neutron spectrum 与 top active escape 的质量闭合拓扑 |

## 4. Prove/Falsify：已经测到了什么

### 4.1 Candidate-own focused signal：PASS

同一份 37,194-event post-Be EventList：baseline 选中 27,855，candidate 选中 27,993；retention `1.004954`，candidate `Aeff=15.11622 cm^2`、`S20=1653.539378`。候选自己的 exact count gate 因此是：

`Gcandidate = (1653.539378 / 10)^2 = 27341.924743 counts`。

真实 CSG ray audit 对 37,194 条信号线给出新增 BGO/plastic 几何冲突 `0/37194`。边界是 post-Be focused injection，不覆盖外包络光学传输。

### 4.2 Prompt P1 repeat64：方向对，但统计上不通过

P1 没有重放 3 条 survivor，而是从完整分母选择对应三个 `E × direction × active-grammage` cell 的全部 257 个 primary states，分别 `71/94/92`，每个 state 均匀重复 64 次；baseline/candidate 各 16,448 events。

结果：

| observable | baseline | AF1-48 | central ratio | one-sided exact upper95 | required survival |
|---|---:|---:|---:|---:|---:|
| pair_any | 7,325 | 7,334 | 1.001 | — | 机制诊断，不是门 |
| first-pair 且 BGO/plastic 都 <50 keV | 160 | 104 | 0.650 | 0.8051 | ≤0.28035 |
| final W2 + veto50 + Step05 | 1 | 0 | 0 | 19.0 | ≤0.28035 |

clean-pair central 数从 160 降到 104，说明内部 host/veto 机制方向正确；其 host 也从 Cu `70→24`。但 Al `29→28`、SS `20→18`、W `13→12` 等迁移仍存在。`0.8051` 的上限远高于所需 `0.28035`；final 只有 `1→0`，完全不可用来证明速率。结论是 **MODIFY / mechanism trend only**，不是 prompt PASS，也不值得立即跑 broadband/full-chain。

### 4.3 Delayed：旧 Cu 项被命中，但 replacement transfer 未知

baseline exact 48-volume Cu scope 包含全部 observed Copper selected rows，对应 `59,252.576 mission counts`、production `161.530 s^-1`、day-15 activity `110.079 Bq`。若把这项理想归零，残余仍是 `29,552.286 counts`，比旧 gate 高 9.16%。但残余 47 条 selected rows 的 event `Neff=7.339`，最大单事件为 5,017 counts；超门差值只有该低-Neff权重尺度的 0.227 倍。因此这是 central FAIL screen，不是可靠 KILL。

现有 far/outer 元素 Al 给出 production `189.076 s^-1`、day-15 activity `105.670 Bq`、85,615 realized decays、0 selected W2。它不能转移到 former-Cu near-TES positions；familywise zero-event rate upper diagnostic 合计 `0.019342 cps`，反而远大于 AF1-48 的 replacement allowance。

在条件锚点 `sPrompt=.80`、`sCu,net=.95`、`sNbMu,eff=.75` 下，replacement Al + remaining Cu 只允许 `2,962.629 counts = 0.00175194 cps`。若 candidate Al 约 100 Bq，rate-equivalent coupling proxy 必须低于约 `1.75e-5 cps/Bq`。这不是预测，而是 D1 exact-position decay 的直接 falsifier。

### 4.4 联合预算：只是一条条件边界

统一用 suppression `s`：

`B20 = P(1-sPrompt) + C(1-sCu,net) + M(1-sNbMu,eff) + O + Delta_new`

其中 `P=55398.979434`、`C=59252.576459`、`M=27605.141950`、`O=1947.144243`。在候选 signal gate 下，若取尚未实测的 `.80/.95/.75/0`：

`B20 = 11079.795887 + 2962.628823 + 6901.285488 + 1947.144243 = 22890.854440 counts`。

margin 为 `4451.070303 counts`，gate ratio `0.837207`，条件算术

`F3 = 3e-5 × sqrt(22890.854440 / 27341.924743) = 2.74497e-5 photon cm^-2 s^-1`。

在 `sPrompt=.80`、`sNbMu=.75` 固定时，允许的最低 `sCu,net=0.874880`。反过来，在 `sCu=.95`、`sNbMu=.75` 下，prompt 至少要 `sPrompt=0.719654`，即 survival `≤0.280346`。这些只是为 focused test 预登记的可证伪坐标，不能写成候选背景测量。

![AF1-48 联合预算边界与 P1 pair-host 迁移](../figures/af1_48_decision_evidence.png)

## 5. 唯一下一步与停止规则

不再并行优化几何，也不跑全八族盲链。候选几何冻结，只执行一个 AF1-48 joint background-transfer campaign：

1. **D1 isolated 48-Al BUILDUP + exact-position decay**：用 n/p/alpha 完整 INIT 分母和 family-specific TT，给出每个 `family × parent × volume/position` 的 production、day-15 Bq、realized triggers、W2/Bq、mission counts、event/position Neff 和最大单事件份额。replacement Al + remaining Cu 的一侧上界若超过 2,962.629 counts，按预登记点直接 KILL。
2. **P3 denominator-complete gamma confirmation**：只有 D1 存活才扩展 prompt；保持 `E × direction × active grammage` 分母，逐 history 输出 first interaction/pair、e+ stop/ANNI、anti-TES sibling 的 BGO/plastic edep、W2/veto/Step05，并将 Ag/SS/retained-Cu migration 计入。要求 prompt survival 的一侧上界 `≤0.280346`，目标 `≤0.20`。
3. **Unified affected-material closeout**：只在前两项过门后，将 inner-BPE capture/cascade、thinned Nb/Mu 和 candidate-own signal 一起代入同一 81-node mission fold；每条 >10% 路径要求 `Neff≥30` 且单 history <10%，或其预登记上限已低于剩余预算。

最终 promotion 判据不是某个平滑热图或 central subtraction，而是 candidate-own central 与预登记置信上界都满足自身 `Gcandidate`，从而给出真实 `F3≤3e-5 photon cm^-2 s^-1`。任一步失败，AF1-48 KILL；在当前硬约束内不保留第二个平行推荐。

## 6. 证据边界与可复现来源

- corrected gamma 已含 annihilation bump；本审查未叠加 mono-511。
- prompt 三事件、P1 三格和 delayed bubbles 都显式保留分母/Neff；未从少数 survivor 外推方向率。
- signal 已测；所有背景 suppression 与 `Delta_new=0` 均未测。
- CSG setup 是 transport proxy，不是 as-built CAD；工程资格独立于物理门。
- 没有复制 GB 级源缓存；focused transport 串行，产物在本 dated engineering 目录与对应 `runs/` 目录。

主要机读来源：

- prompt interaction/chords/denominator：`engineering/s3d_o8_loop_engineering_20260814/agents/prompt/`
- delayed bubbles/flow/material summary：`engineering/s3d_o8_loop_engineering_20260814/agents/delayed/`
- candidate setup、白名单、质量与 overlap：`reconsideration_20260814/agents/geometry/`
- candidate signal：`reconsideration_20260814/focused_signal/candidate_signal_result.json`
- prompt P1 repeat64：`reconsideration_20260814/focused_prompt_repeat64/three_cell_mechanism_result_repeat64.json`
- corrected joint gate：`reconsideration_20260814/agents/prompt/prompt_budget_gate.json`
- delayed audit/budget：`reconsideration_20260814/agents/delayed/audit_summary.json`、`TC_AF1_budget_audit.csv`
- decision data/figure：`reconsideration_20260814/data/`、`reconsideration_20260814/figures/af1_48_decision_evidence.png`

