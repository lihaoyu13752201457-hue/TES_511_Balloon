# S3d-O8：去掉磁屏蔽盒与铜盒的 prompt 反事实审查

日期：2026-08-14  
范围：三条 S3d-O8 post-veto 链、Mass_model_511 最终七条链、真实 baseline CSG；
不改冷盘，不跑 transport。

## 技术结论

**作为 prompt 优化拓扑，`remove Nb/Mu + Cu box = KILL；不值得启动 focused
candidate test`。**

删除 Nb/Mu 确实会删掉 S3d 3883 的 Nb first-pair 与 MuMetal annihilation host；但最终
另一条等权链 19932 的 `DR_MixingChamber_Cu -> DR_MixingChamber_Cu` 完全不在删除范围。
其 anti-TES partner 仍先在 Still cold plate 相互作用，并继续穿 DR Cu、三块 cold plate
和 4.768 cm SS；其 TES-bound 511 反而失去原有 0.4195 cm Nb/Mu 衰减。按 511-keV
uncollided 标度，删磁屏蔽会把同一路径透射乘约 `1.366`，方向是变坏而非改善。

两种“铜盒”口径都不增加 S3d 最终链的理想删除数：

- `50 mK Cu can`：最终两条的 pair/annihilation host 都不在 can；
- `L0 Cu enclosure`：只命中未通过 Step05 的 8081 annihilation 和 Mass 对照链，不命中
  S3d 最终 3883/19932 的新一条链。

因此，基于观察到的两条 S3d 最终链，所有“磁盒 + 任一/两个铜盒”方案的极端
no-migration ceiling 都只是 `1/2 = 50%`：`0.03384293 -> 0.01692146 cps`。同一 mission
计数口径为 `P20/2 = 27699.49 counts`，已经比**总**门 `27073.01 counts` 高
`626.48 counts`，即使 delayed 被不可能地设为零仍不过门。这只是低统计
`Neff=2` 的 observed-chain ceiling，不是总体效率置信界；真实 suppression 的可保证下界
为零，且可能为负。

## 删除范围与证据分母

本报告把含糊的“盒子”固定成三个互斥 scope：

1. `mag`：`Nb_MagShield_*` 与 `MuMetal_MagShield_*` 的 cylinder/back caps；
2. `can`：全部 `Cu_50mK_StillLike_Can_*` side/bottom volumes；
3. `L0 enclosure`：`Cu_SubstrateSupport_*` solid disk、open rings 与 edge rods。

`L0 enclosure` **不包括** DR mixing chamber Cu、Ag proxy、MXC/cold plates、cold fingers、
clamps、SS support 或 W。这些是删盒后仍在的主要迁移/吸收 host。冷盘完全冻结。

分母为：

- S3d 最终 Step05：2 条等权链，`0.0338429281 cps`、`Neff=2`；另保留 8081 作为
  post-veto、Step05-fail 的机制对照，不能混入最终 rate；
- Mass_model_511 最终：6 gamma + 1 eplus，`0.1234185562 cps`、`Neff=6.934`。

所有 host-tag fraction 都只描述这 2/7 条 selected 尾；没有从它们外推全天角或完整 gamma
分母。

## S3d 三链：删掉的 host 很少，剩余 Cu/Ag/SS 很多

| event | Step05 | 删除的 baseline host/chord | 不动冷盘后仍在的关键路径 | 反事实含义 |
|---|---|---|---|---|
| 3883 | PASS | Nb pair；Mu ann；primary pre-pair `mag 0.572 + can 0.210 + L0 0.308 cm`；partner 仅删 `Mu 0.198 cm` | partner 首次 `COMP Ag`，Ag `1.483 cm`、cold plates `2.906 cm`；删 pair host 后原 primary 下一段为 MXC Cu `0.630 cm` + DR Cu `0.550 cm` | exact baseline host 消失，但 Cu host migration 与 TES-ray 变透明同时存在 |
| 19932 | PASS | **pair/ann/primary/partner 无所删 box chord** | pair/ann 均为 DR Cu；partner 含 DR Cu `0.643`、cold plates `2.435`、SS `4.768 cm`；TES-bound 511 原有 `mag 0.4195 cm` | 主导反例：机制保持，删 mag 只提高同路径透射 |
| 8081 | FAIL | Nb pair；若删 L0 则 L0 ann；primary pre-pair `mag 1.122 + can 0.202 cm`；partner 删 `mag 0.773 + L0 0.018 cm` | partner 首次 `COMP MXC plate`，cold plates `1.593` + cold finger `0.233 cm`；删 mag 后原 primary 紧接 MXC Cu `4.101 cm` | 只作机制对照；不能领取最终 Step05 rate credit |

Cu 下一 host 不是小修正。用现有 Cu macroscopic response 作尺度：

- 3883 的紧邻 `0.630+0.550=1.180 cm Cu` 给约 `29.3%` 任意相互作用、`7.1%`
  pair 机会；
- 8081 的紧邻 `4.101 cm MXC Cu` 给约 `67.8%` 任意相互作用、`34.4%` pair 机会。

这些不是候选预测，只说明“Nb pair 被删除”不能等同“gamma 被删除”；相互作用会迁到仍在
的 Cu。

### 8081 数据质量更正

早先 `passive_collimator_prompt_leaks.csv` 使用的 TES box 只到 L4
(`x_IF<=1.95 cm`)，漏掉 L5，因而把 8081 错标为 `straight_ray_misses_TES_box`。完整六层
CSG 与 raw IA 复核显示：IA9 初始 511 **直达 L5**，在 TES 内 IA23 COMP 后继续沉积；
到首个 TES pixel 前穿 `0.6583 cm L0 Cu`。旧标签不得再用于“需要 TES 前散射”的论证。
这个更正不改变此前 PA-X1 几何 KILL，因为 PA-X1 的 uniform-chord 硬门独立于三条事件。

## Mass 七链：最高 tag ceiling 仍只有 58.85%，同时移除现有衰减

| event | pair -> annihilation | exact host 被哪个 scope 删除 | partner 在删盒后仍见 | TES-bound 511 的反向风险 |
|---|---|---|---|---|
| eplus 1546 | Nb -> Nb | mag | can `0.337` 若不删；W `0.320`、CsI `7.431 cm` | eplus/BREM 多级链，无单一直线迁移；mag removal proxy `x1.178` |
| gamma 5426 | 4K Al -> 4K Al | none | 首次 COMP CsI | can `0.356 cm` 被删后，透射 proxy `x1.301` |
| gamma 20873 | Nb -> L0 disk | mag 或 L0 | W `0.230`、CsI `7.272 cm`；can 是否保留取决 scope | 删 mag 后原 primary 下一 host 是 can Cu `0.214 cm` |
| gamma 8512 | MXC cold plate -> clamp Cu | none | cold plates `2.121 cm` | mag `0.485 cm` 被删，proxy `x1.435` |
| gamma 88 | SS rod -> 4K Al | none | sibling 原本直接逃逸；SS pair host 保留 | mag `0.413 cm` 被删，proxy `x1.360` |
| gamma 20032 | L0 disk -> L0 disk | L0 | cold plate `0.984 cm` | primary 先 COMP 后 PAIR，删 L0 后 next host 不能用直线推断；TES-ray proxy `x1.257` |
| gamma 6232 | can bottom -> can bottom | can | W `0.193`、CsI `6.089 cm` | mag+can 同时删时 TES-ray proxy `x1.525`；原 primary 下一段为 Al/W/CsI |

`xN` 只是把被删 chord 的 `exp(+mu*L)` 反算为同一路径 uncollided-transmission
multiplier；它没有计入 Compton buildup、重生或 veto，因此只用于标出可能恶化的方向。

### Selected-chain 理想删除界

| scenario | S3d final observed-chain ceiling | Mass 7-event ceiling | Mass ideal residual |
|---|---:|---:|---:|
| mag only | 50.00% | 31.41% | 0.084649 cps |
| can only | 0% | 13.72% | 0.106489 cps |
| L0 only | 0% | 27.43% | 0.089559 cps |
| mag + can | 50.00% | 45.13% | 0.067720 cps |
| mag + L0 | 50.00% | 45.13% | 0.067720 cps |
| mag + both Cu boxes | 50.00% | 58.85% | 0.050790 cps |

“ceiling”定义为：若 baseline 链的 pair 或 annihilation host 属于删除 scope，就把该整条链
无条件删除，同时假定没有 host migration、没有新 leak、没有失去 passive attenuation。
它是**故意偏向候选**的 selected-sample tag 账，不是 transport 上界。真实 improvement 的
下界无法由 baseline selected 尾给出；因为 19932、5426、8512、88 等 unaffected-host 链
同时失去 511 attenuation，净变化可以为零甚至变坏。

## 为什么 partner-veto 增益救不了 S3d

Mass 中 can/L0 removal 有一个真实但仅属条件性的好方向：1546/20873 的 anti-TES partner
原先在 can/L0 被动吸收，删掉后直线路径后方有 7.4/7.3 cm CsI，可能转成 veto。然而：

- 同一 host 本身也被删除/迁移，不能保持原 annihilation point 与 partner direction；
- S3d 三条的 actual partner first interaction 分别为 Ag、Still cold plate、MXC cold plate，
  全都保留；所以目标 S3d 没有对应的 box-to-active partner lever；
- 19932 仍沿 top opening topology，partner 的 DR Cu/cold plates/SS blocker 全部不动。

故不能把 Mass 条件反例当成 S3d veto 增益。

## Prove/Falsify 与最终判决

| proposition | verdict | direct evidence |
|---|---|---|
| 删除 Nb/Mu 会移除 3883 baseline host | **FACT / KEEP as mechanism** | Nb pair + Mu ann 均在 scope |
| 删除 50 mK can 能额外压 S3d final prompt | **KILL** | 0/2 final host-tag；三条 partner first interaction 均不在 can |
| 删除 L0 enclosure 能额外压 S3d final prompt | **KILL** | 0/2 final host-tag；只命中 Step05-fail 8081 |
| 磁盒 + 铜盒是可晋级 prompt topology | **KILL** | 19932 完全保留且更透明；sample-ideal 50% 已超总 gate |
| 只跑三 root-state focused repeat | **KILL as decision test** | 无完整 denominator，不能测 host migration 后的新拓扑率 |

不建议生成 removal proxy 或启动 transport。若未来因系统工程原因本来就必须去掉这些盒子，
唯一有效的物理测试将是候选自己的完整 paired gamma S20，加 signal replay、磁性能与热真空
验证；三条 S3d 或七条 Mass root-state replay 最多说明迁移路径，不能 promotion。当前 prompt
证据本身不足以支付这种高代价测试，而且方向偏向 `no benefit / possible worsening`。

## 机读产物

- `box_removal_chain_audit.csv`：十条链的 pair/ann host、primary/partner/TES-ray chords、
  transmission proxies 与 next-host 标签；
- `box_removal_observed_chain_bounds.csv`：六个 scope 组合的 S3d/Mass observed-chain ceilings；
- `box_removal_primary_ray_segments.csv`：九条 gamma original-primary baseline CSG segments；
- `box_removal_tes511_ray_segments.csv`：十条 original TES-bound 511 baseline CSG segments；
- `audit_box_removal_prompt.py`：只读 lineage/CSG 复算脚本。

