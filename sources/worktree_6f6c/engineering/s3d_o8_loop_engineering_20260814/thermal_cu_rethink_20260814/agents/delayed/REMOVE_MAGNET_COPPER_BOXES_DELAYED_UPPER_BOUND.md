# S3d-O8：去掉磁屏蔽盒与 Cu 盒子的 delayed 中央上限

日期：2026-08-14  
范围：只读 official 420-row selected delayed lineage、exact mission timeline 与
`delayed_source_mix.csv`；没有运行 transport。这里的“去掉”是把指定 source-volume 的
**observed selected row 各删一次**，不是可制造候选预测。

## 结论

在最乐观 central perfect-removal 口径下，去掉这些盒子确实降低 observed delayed：

- Nb inner 全套 + Mu-metal outer 全套：删 `0.0169669466 cps / 27605.1420 counts`；
- 完整 `50mK_Cu_Can`（A）：删 `0.00414577538 cps / 6752.1756 counts`；
- L0 Cu enclosure（B）：删 `0.00584950669 cps / 9455.4087 counts`；
- A+B（C）：删 `0.00999528207 cps / 16207.5843 counts`；
- 磁屏蔽 + C 全部联合：删 `0.02696222865 cps / 43812.7263 counts`，即 observed D20 的
  `49.3360%`。

但答案不是“删掉即可过门”。保持 baseline prompt 后，最乐观的“磁屏蔽+C 全删”仍为
`P20 + D20,res = 100391.1158 counts = 3.7082 x` formal gate
`27073.008579`。甚至把 prompt 也人为设为零，残余 delayed
`44992.1364 counts` 仍超门 `17919.1278 counts`。而 baseline prompt 本身
`55398.9794 counts` 已高于 formal gate。因此这只能说明这些是 observed coupling 热点，
不能成为独立解；真实移除还会丢失被动 grammage、磁/热功能并产生 replacement-host
activity，净收益只能由候选自己的 BUILDUP + decay + prompt transport 决定。

## 1. 精确定义与去重

磁屏蔽全套显式包含四个 volume：

```text
Nb_MagShield_Inner_Cylinder_2mm
Nb_MagShield_Inner_Back_ColdFingerCap_2mm
MuMetal_MagShield_Outer_Cylinder_2mm
MuMetal_MagShield_Outer_Back_ColdFingerCap_2mm
```

Cu 盒 A 包含四个 `Cu_50mK_StillLike_Can_*` volume（bottom、side below、side above、
rectcut window band）；B 只包含 `Cu_SubstrateSupport_SolidDisk_L0_deepest`；C 是 A 与 B
的集合并集。

官方 420 行以
`family x local_event_id x parent-ZA x source_volume x source_file` 检查为 420 个唯一 UID。
每个 scenario 直接用 volume 集合构造 removed/residual 互斥分区，并验证 cps 与 mission
counts 精确闭合。磁屏蔽、A、B 彼此无 volume 重叠；组合不是把汇总表再次相加。

`production Bq` 没有加入 removed counts。官方 W2 行已经含对应 source activity 与
exact-position response；再把 Bq 加上会重复计算。source-mix 仅作为抽样/位置分母 screen，
也不与 W2 counts 相加。

## 2. Official mission-count perfect-removal ceiling

共同 authority：baseline delayed `0.0544797522273 cps / 88804.862652 counts`；baseline
prompt mission counts `55398.979434`；formal gate `27073.008579`。prompt 在本表冻结不变，
因此这对 delayed removal 是有利但不物理完整的上限。

| perfect-removal scope | removed rows | removed cps | removed D20 | residual D20 | P20 + residual D20 | minus gate | removed Neff |
|---|---:|---:|---:|---:|---:|---:|---:|
| magnet full | 45 | 0.0169669466 | 27605.1420 | 61199.7207 | 116598.7001 | +89525.6916 | 6.609 |
| A: 50 mK Cu can | 18 | 0.00414577538 | 6752.1756 | 82052.6870 | 137451.6665 | +110378.6579 | 3.348 |
| B: L0 Cu enclosure | 93 | 0.00584950669 | 9455.4087 | 79349.4540 | 134748.4334 | +107675.4248 | 4.413 |
| C: A+B | 111 | 0.00999528207 | 16207.5843 | 72597.2784 | 127996.2578 | +100923.2492 | 7.754 |
| magnet+A | 63 | 0.0211127220 | 34357.3176 | 54447.5451 | 109846.5245 | +82773.5159 | 9.157 |
| magnet+B | 138 | 0.0228164533 | 37060.5506 | 51744.3120 | 107143.2914 | +80070.2829 | 10.132 |
| magnet+C | 156 | 0.02696222865 | 43812.7263 | 44992.1364 | 100391.1158 | +73318.1073 | 12.868 |

所有行都是 central observed ceiling；没有统计 promotion 含义。尤其 magnet、A、B 的
event Neff 只有 `6.61 / 3.35 / 4.41`，所以不能把小数点后的 central credit 当确定收益。

## 3. Source-mix screen：少量 source draws，极强 selected coupling

S3d-O8 source-mix 的完整八 family 分母为 `400000 full blocks / 80000 selected blocks /
2000000 realized triggers`。下表中的 trigger fraction 只是 source sampling screen；各 family
的物理权重不同，所以 `removed-W2 fraction / trigger fraction` 不能冒充统一 W2/Bq。

| scope | family-volume-parent keys | realized triggers | trigger fraction | observed D20 fraction removed | event Neff | hottest selected volume |
|---|---:|---:|---:|---:|---:|---|
| magnet full | 73 | 9287 | 0.46435% | 31.0852% | 6.609 | Nb inner cylinder, 12797.0390 |
| A: 50 mK Cu can | 152 | 29803 | 1.49015% | 7.6034% | 3.348 | bottom cap, 6540.3615 |
| B: L0 Cu enclosure | 7 | 2017 | 0.10085% | 10.6474% | 4.413 | L0, 9455.4087 |
| C: A+B | 159 | 31820 | 1.59100% | 18.2508% | 7.754 | L0, 9455.4087 |
| magnet+C | 232 | 41107 | 2.05535% | 49.3360% | 12.868 | Nb inner cylinder, 12797.0390 |

这个反差支持“近场 coupling 优先”的物理图像，但也暴露 low-Neff：

- magnet 的四个约 5000-count proton hotspots 分别位于 Mu cylinder 与 Nb cylinder；最大
  单事件 `5017.1640 counts`，占 magnet credit `18.17%`。Nb back cap 的全部 observed
  `2072.6579 counts` 来自单个 neutron event。
- A 的 `96.86%` credit 来自 bottom cap；其最大单事件 `2289.1304 counts` 占 A 的
  `33.90%`。side-above 的 56.3134 counts 又有 `94.41%` 来自单事件。
- B 只有一个 L0 volume，`Neff=4.413`；n→Cu-62 与 n→Cu-64 两个 parent bucket已占
  `4578.2607 + 4422.3603 counts`。

两个“零 selected”不能 zero-impute：Mu outer back cap 在 source mix 中仍有 250 realized
triggers；can rectcut window band 有 6224 triggers。它们的 official central credit 是零，
但真实 coupling 只有有限统计上限。

## 4. Origin 风险：为什么物理净收益小于 perfect deletion

1. **磁屏蔽移除：**删掉 observed Nb/Mu parents 的同时失去 superconducting/high-mu
   shielding 与 passive grammage。替代 Nb、Ni/Fe alloy 或结构壳会产生新的 Y/Zr/Nb、
   Co/Fe/Ni parents；其 production Bq 与 exact-position W2/Bq 都是 UNKNOWN。
2. **Cu can/L0 移除：**bottom 与 L0 正是近场 Cu-61/62/64 hotspot，但它们也承担热、光/RF
   与机械封闭，并吸收部分 511/prompt cascade。替代 Al/SS/Ni/low-Z support 会迁移
   annihilation host；不能把旧 Cu row 删除量当 replacement 的净收益。
3. **prompt 冻结偏乐观：**去掉壳体可能减少高-Z interaction host，也可能开放原先被 Cu、
   Nb、Mu 吸收的直达路径。baseline prompt 已独自超门，本 delayed screen 对这个符号没有
   证据。
4. **统计边界：**magnet+C 虽覆盖 156 rows，removed `Neff=12.868`，残余仍由单个
   `5017.1393-count` event 控制 11.15%。平滑 component 图不能代替候选 paired sample。

## 5. KEEP / KILL

- `KEEP`：把 magnet cylinder、can bottom、L0 作为 focused BUILDUP/decay 的 named
  hotspots；它们确实有高 selected coupling。
- `KILL`：把“直接去掉 magnetic shield + Cu boxes、其余不变”当成闭合方案。即使给它
  100% old-row deletion、零 replacement activity、prompt 不恶化，联合 residual 仍远超门；
  prompt=0 时 delayed 本身也不过门。

若用户仍要求工程候选，必须先指定满足磁、热、机械功能的**唯一替代 manifest**，再以
`geometry x mode x family` 分母做 focused BUILDUP，并用
`family x parent-ZA x exact position` 做 decay fold。未指定替代材料时，host migration 是
不可消除的 blocker，不能把本表的 perfect-removal ceiling 当预测。

## 产物

- `remove_magnet_copper_boxes_upper_bound.csv`：baseline 与七个互斥/联合 scenario；official
  cps/counts、formal gate、Neff、热点及 source-mix denominator。
- `remove_magnet_copper_boxes_volume_detail.csv`：九个 exact named volumes，含 zero-selected
  source-mix exposure。
- `analyze_remove_magnet_copper_boxes.py`：只读复算脚本。
