# S3d-O8 delayed top-five source volumes: DECA to TES audit

The five volumes cover 205/420 selected events and 0.042210754475/0.0544797522273 cps (77.48%) of delayed W2 rate.
They were ranked by W2 rate, not row count.

|rank|source volume|material|events|W2 rate (cps)|Neff|exact DECA ancestry rate coverage|exact TES-entry rate coverage|
|---:|---|---|---:|---:|---:|---:|---:|
|1|ColdPlate_MXC_50mK_SD_anchor|Copper|57|0.0167714959|8.733|100.00%|100.00%|
|2|Nb_MagShield_Inner_Cylinder_2mm|Nb|24|0.00780860401|2.967|100.00%|100.00%|
|3|MuMetal_MagShield_Outer_Cylinder_2mm|MuMetal|20|0.00776545392|2.934|100.00%|100.00%|
|4|Cu_SubstrateSupport_SolidDisk_L0_deepest|Copper|93|0.00584950669|4.409|100.00%|100.00%|
|5|Cu_50mK_StillLike_Can_bottom_cap_2mm|Copper|11|0.00401569391|3.137|100.00%|100.00%|

`incident_activation_family` is the atmospheric particle family that produced the isotope; it is not the delayed particle entering TES.
The event CSV freezes exact DECA emissions, matched HTsim contributor chains, first saved TES-interaction mother particles, and TP-pixel CC deposit particles.
Any contributor without a complete IA-origin path to DECA or without a saved detector-type-2 interaction is explicitly marked UNKNOWN/PARTIAL.
CC HIT records are energy-deposit samples, not complete boundary-crossing Geant4 steps.

## 加权物理结论

这 5 个体积合计覆盖 delayed W2 的 `0.0422107545 cps`，即全体
`0.0544797522 cps` 的 `77.48%`。在这 205 个已选 W2 事件内，保存下来的
IA/HTsim ancestry 给出同一条主链，且按率覆盖为 100%：

`母核素 DECA -> e+ + neutrino(code 12) + daughter ion -> e+ ANNI -> 511 keV gamma -> TES COMP/PHOT -> secondary e- deposits`

这里的 100% 只描述**已经落入 510.58--511.42 keV W2 的选择样本**，不是母核素
所有衰变分支的 branching ratio。W2 本身会强烈选择 beta+ annihilation 链，不能据此
声称这些核素没有 beta-、EC 或其他 gamma 分支。

按 selected W2 rate 加权，前五体积中的 activation-producing incident family 为：

- neutron `49.50%`；
- proton `43.36%`；
- alpha `2.66%`；
- positron `2.46%`；
- gamma `1.32%`；
- electron `0.72%`。

因此 ledger 中大量 e+/e- 行不能按行数解释为主导 activation 机制；高权重 n/p 事件
合计承担 `92.85%` 的这部分 W2 率。

TES 的第一条已保存 detector-type-2 interaction 的 mother particle 在 205/205 事件中
都是 `gamma`。这给出很强的“annihilation gamma 是入射载体”证据；但 SIM 没有保存
完整 boundary-step，因此严格的“跨 TES 边界粒子”仍不宣称为直接观测 FACT。TP-pixel
CC deposit 能量再按事件 W2 权重折算后，`e-` deposit 占
`96.98%`，gamma-labelled CC deposit 占 `3.02%`。这两句话不矛盾：进入 TES 的是
annihilation gamma，实际热化能量主要由光电/Compton 产生的次级电子沉积。

## 各体积主要母核素与链

|source volume|主要母核素（体积 W2 率占比）|主要 activation family（体积 W2 率占比）|TES 入射 / 沉积|
|---|---|---|---|
|ColdPlate_MXC_50mK_SD_anchor|Cu-62 47.72%; Cu-61 35.38%; Cu-64 8.59%; Zn-63 8.31%|n 58.14%; p 36.37%|gamma 100%; e- deposit 97.22%|
|Nb_MagShield_Inner_Cylinder_2mm|Zr-85 39.06%; Y-85 39.06%; Nb-89 17.84%; Nb-90 4.04%|p 78.12%; n 17.84%|gamma 100%; e- deposit 97.53%|
|MuMetal_MagShield_Outer_Cylinder_2mm|Fe-53 39.28%; V-46 39.28%; Co-54 17.94%; Co-55 2.10%; Ni-57 1.40%|p 78.56%; n 17.94%|gamma 100%; e- deposit 97.25%|
|Cu_SubstrateSupport_SolidDisk_L0_deepest|Cu-62 52.38%; Cu-64 47.62%|n 95.25%|gamma 100%; e- deposit 96.02%|
|Cu_50mK_StillLike_Can_bottom_cap_2mm|Cu-64 62.70%; Cu-62 34.69%; Cu-61 2.62%|n 69.37%; alpha 27.93%|gamma 100%; e- deposit 95.77%|

## 活度不是近场危险度：空间耦合差异近 40 倍

|volume|full-volume day-15 activity [Bq]|selected W2 [cps]|W2/activity proxy [cps/Bq]|
|---|---:|---:|---:|
|MXC 50 mK plate|20.2809|0.0167715|8.27e-4|
|Nb inner cylinder|1.01631|0.00780860|7.68e-3|
|MuMetal outer cylinder|1.15215|0.00776545|6.74e-3|
|L0 Cu support disk|0.244888|0.00584951|2.389e-2|
|50 mK can bottom|6.77797|0.00401569|5.92e-4|

L0 Cu disk 的 full activity 最低之一，却因贴近 TES，effective selected-W2 coupling
约为 MXC plate 的 29 倍、can bottom 的 40 倍。这一比值混合了衰变谱、几何和响应，
只是本次 W2 coupling proxy，不是材料常数；但它明确否定了“按 Bq、质量或减材比例
线性估算本底收益”。

## 谁真正制造了核素：primary family 与生产顶点必须分开

`incident_activation_family` 是外部 activation primary 分支；真正位于残余核生产顶点的
粒子可能是这个 primary，也可能是其级联产生的 neutron、gamma 或 pion。前五体积中仅
22/205 个 selected event 有 retained exact-coordinate production-origin link，但它们承载
前五 W2 率的 95.51%。以下只能作为 **exact-linked selected-event FACT**，不能解释为全
inventory 的稳定 branching fraction。

全 420 行的 exact-origin 行覆盖是 25/420=5.95%，但 W2-rate 加权覆盖为 84.22%。这说明
已链接的正是高权重 n/p/alpha 量子；报告只写 5.95% 而不写加权覆盖会低估当前机制证据，
反过来把 84.22% 当高统计精度也同样错误。

|volume/material|主要 exact-linked 生产顶点|
|---|---|
|MXC 50 mK plate / Copper|n-primary → n `neutronInelastic` → Cu-61/62/64；p-primary → p `protonInelastic` → Cu-61；p-primary → secondary gamma `photonNuclear` → Cu-62；n-primary → secondary p `protonInelastic` → Zn-63|
|Nb inner cylinder / pure Nb|p-primary → p `protonInelastic` → Y-85；p-primary → secondary π+ `pi+Inelastic` → Zr-85；n-primary → secondary π− `pi-Inelastic` → Nb-89|
|MuMetal outer cylinder / model Ni:Fe=4:1|p-primary → secondary n `neutronInelastic` → Fe-53；p-primary → secondary π+ `pi+Inelastic` → V-46；n-primary → secondary π+ `pi+Inelastic` → Co-54|
|L0 substrate-support disk / Copper|n-primary → n `neutronInelastic` → Cu-62；n-primary → n `nCapture` → Cu-64|
|50 mK can bottom / Copper|n-primary → n `neutronInelastic` → Cu-62；n-primary → n `nCapture` → Cu-64；alpha-primary → secondary n `nCapture` → Cu-64|

因此“alpha 激活出的 Cu-64”并不是 alpha 直接打在 Cu 上的证据；这个 exact event 中真正
制核的是 alpha cascade 产生的 secondary neutron capture。同理，Nb/MuMetal 的高权重
残余核含有 pion-driven cascade，20 mm 级外层 BPE 不能被假定为能关闭这些高能级联。

机器可读表：

- `data/delayed_top5_chain_summary.csv`
- `data/delayed_top5_isotope_family_matrix.csv`
- `data/delayed_top5_exact_production_mechanisms.csv`
- `audit/delayed_top5_chain_validation.json`

## 与 prompt 的统一终端机制

Delayed 与 prompt 的**前半段不同，终端完全收敛**：

- delayed：`n/p/cascade 激活 → beta+ 母核 DECA → e+`；
- prompt：`4.15--6.35 MeV external gamma → internal passive PAIR → e+`；
- 共通终端：`e+ slows/stops → ANNI → 510.999-keV gamma → TES COMP/PHOT → e- heat`。

官方 prompt Step05 两条分别为：

1. 4148.290-keV gamma：Nb inner cylinder PAIR → MuMetal outer cylinder ANNI → 单一 L2 pixel；
2. 5768.820-keV gamma：DR mixing-chamber Cu PAIR/ANNI → 单一 L2 pixel。

第三条 pre-Step05 机制样本为 6345.940-keV gamma：Nb PAIR → e+ 跨 Nb cold-finger cap
迁移 → L0 Cu disk ANNI → 两个 L5 pixels；它因 TES Compton/FoV topology 被 Step05 拒绝，
不是 active-veto 拒绝。三条 BGO/plastic raw deposit 都为零。

这意味着单纯删除某一个 pair/annihilation host 不保证 prompt 消失：e+ 可以停到下一个
Nb/Cu/Mu/Ag/MXC host 后再湮灭。Delayed 则因为 beta+ 母核本身就在 active guard 内侧，
向内发出的 annihilation gamma 天然可能不经过外层 veto。

## UNKNOWN 边界

- 前五体积内：DECA-to-TES contributor ancestry 和首个保存的 TES interaction 都是
  `205/205` events、`100%` W2-rate coverage；该覆盖内没有 UNKNOWN。
- 前五体积外仍有 `22.52%` delayed W2 rate，本审计没有解析，必须记作本次审计的
  out-of-scope，而不能外推上述 100% 链组成。
- `CC HIT` 是能量沉积采样，不是完整的 Geant4 boundary-step 轨迹；因此这里可以验证
  TES interaction mother particle 和 deposit particle，但不宣称恢复了每一段边界穿越。
