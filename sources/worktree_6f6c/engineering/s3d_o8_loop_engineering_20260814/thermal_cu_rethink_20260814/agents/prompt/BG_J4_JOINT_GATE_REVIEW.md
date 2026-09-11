# BG-J4 联合门独立核算与物理审查

## 判决

**联合门的纯算术复算正确，但把 prompt-only 的 `BG-TAU5` 修改成统一 `BG-J4` 候选，物理上已经被 actual-IA sibling 分支证伪。`BG-J4` 作为联合系统候选：`KILL`。**

`BG-J4` 的定义是：保留 cold-core Cu、冷盘和 Nb/Mu baseline，不领取近场改动收益；只把现有同一 BGO detector/readout channel 做成全周最小新增 chord `4 cm`，真实保留全部 service relief。若 delayed 方案还需要外置 BPE，则顺序必须是 `cold core -> BGO -> BPE`，BPE 对 prompt 领取零收益。

这里的 4 cm 与几何团队的 full-wrap mass scale 一致：side 向外径增厚、top/bottom 向外轴向增厚，新增 active material 位于冻结的 cold-core/passive stack 之后。若把 BGO 内表面移到 Cu/Ni/Nb/Mu/Ag 之前，那是另一个近场 active topology，会与 R=15--17.5 cm 冷盘/服务件竞争空间，必须重新过 signal、热和结构门，不能沿用本报告的质量或耦合式。

`BG-J4` 的反事实公式要求至少 `91.6767%` 的 delayed mission counts 有效到达新增 BGO。完整 actual-IA 分支却显示，只有 `8.4393%` mission counts 存在 `>50 keV` escape gamma，只有 `10.5925%` 有 `>=50 keV` gamma 到达 current-BGO/outer-region proxy，IA 点进入 active 的只有 `2.2190%`。这不是“尚未证明 91.7%”，而是同一 baseline selected-W2 分母上的直接机制反证。

因此不要启动 `BG-J4` 联合 transport。4 cm BGO 仍可保留为 prompt-only optical-depth sensitivity；若必须给一个物理定义的条件拓扑，仍只能回到 `BG-TAU5 + BPE-O`：BGO 对 prompt，候选自己的外置 BPE/activation fold 对 delayed。它仍不是 flight-admissible，且 BGO 不得领取全 delayed 的 sibling-veto 收益。

预算上这也解释了为何 4 cm 不能取代 prompt-only 厚度：BG-J4 的 prompt proxy 只压到 `0.33154`，要求另一个 delayed mechanism 独立给 `89.8938%` suppression；BG-TAU5 把 prompt 压到 `0.20` 后，独立 delayed suppression 门为 `81.6878%`。二者都必须由候选自身证明，但后者没有把已被反证的 sibling escape 当主杠杆。

因此当前分级为：

| level | verdict |
|---|---|
| joint-budget arithmetic | **formula verified, premise falsified** |
| BG-J4 prompt-only mechanism | **KEEP as attenuation sensitivity only** |
| BG-J4 delayed coupling | **KILL: actual branch reach 8.44--10.59%, required 91.68%** |
| BG-J4 unified topology | **KILL; do not run** |
| BG-TAU5 + BPE-O | **physics-defined conditional only; not flight-admissible** |

## 1. 联合门复算

采用父预算给定的

\[
P=55398.97943402516,\quad D=88804.86265187593,\quad
G=27341.9247428634\ \mathrm{counts},
\]

以及仅作标度的 `mu_P=0.276 cm^-1`、`mu_D=0.985 cm^-1`：

\[
R(L)=P e^{-0.276L}+D e^{-0.985L}.
\]

数值根为

\[
L_*=3.137574918\ \mathrm{cm}.
\]

所以 `3.138 cm` 的反事实全耦合式确实只是零余量根；任何 relief、BGO 新 activation、低于阈值的沉积或 secondary leakage 都会使它失败。后文 actual branch 证据还表明，full-delayed 全耦合这个前提本身不成立。

在 `L=4 cm`：

- prompt proxy：`18367.102776 counts`；
- delayed proxy：`1727.096039 counts`；
- 合计：`20094.198815 counts`；
- 相对联合门余量：`7247.725928 counts`。

若从此前 `P_any(3 cm)=0.94807734` 反推 `mu_D=0.986 cm^-1`，则根为 `3.13636 cm`、4-cm 合计 `20087.30 counts`。这个差异远小于物理系统误差；报告沿用提问中的 `0.985`，不把第三位小数当成 transport 精度。

## 2. 反事实全耦合模型中的 relief / bypass 容限

必须分别保留 prompt 与 delayed 的 mission-weighted bypass 分母。令 `f_P`、`f_D` 分别为绕过新增 BGO、因而恢复 baseline contribution 的权重分数。零新 activation 时，4-cm 门为

\[
(P e^{-1.104}+D e^{-3.94})+
P(1-e^{-1.104})f_P+D(1-e^{-3.94})f_D\le G.
\]

即

\[
37031.876658 f_P+87077.766613 f_D\le7247.725928.
\]

由此：

- 若两类具有同一 bypass fraction，`f_P=f_D=f`，则 `f<=5.83978%`；
- 若 bypass 全在 delayed，`f_D<=8.32328%`；
- 若 bypass 全在 prompt，`f_P<=19.57159%`。

若强行压成一个 baseline-count 加权指标

\[
f_{mw}=(P f_P+D f_D)/(P+D),
\]

则容限依 bypass composition 而变：delayed-heavy 的安全上限是 `5.12571%`，prompt-only 的数学上限是 `7.51884%`。若未来某个不同几何真的先证明了全耦合，工程门应采用保守的 `f_mw<=5.13%`，且正式统计仍须报告 `f_P,f_D`。对当前 BG-J4，这些 bypass 数字不能挽救方案，因为约 89% delayed mission weight 已在到新增外层 BGO 之前失去可 veto sibling。

若新增 BGO 产生 `A_new` 个 selected-W2 mission counts，右侧余量改为 `7247.725928-A_new`；所以在零 bypass 下也必须有 `A_new<7247.725928 counts`。任何 BPE production benefit只能用候选自己的 BUILDUP×exact-decay fold 加入，不能先从 bypass 分母中扣除。

## 3. actual IA 已证伪 delayed 全耦合项

已有完整分母不是 3 条 survivor，而是 `420` 条 selected delayed lineage：

- `418/420` 唯一追到 anti-TES annihilation sibling，覆盖 `99.9672%` mission counts；
- baseline CSG 中到任一现有 BGO 的 straight-ray opportunity 为 `86.2844%`；填同一 top gap 后，418 条的几何 opportunity 可到 `100%`；
- 但只有 `45.708%` full-delayed mission counts 的直线在主动面之前不穿命名的 Cu cold plate。

后两项不是矛盾：射线可以先穿 Cu 冷盘、再在无限延长的几何线上穿 BGO。所用 `e^{-0.985L}` 只描述**已经到达**新增 BGO 的 511-keV photon 在 BGO 内保持未相互作用的标度；它没有包括到达 BGO 之前的 passive survival，也没有证明相互作用沉积超过 50 keV。

现在已有 actual branch 闭合，而不再只靠直线：

- sibling 首个能量改变为 `COMP` 的 mission weight 是 `94.2360%`，`PHOT` 是 `5.6047%`；
- 首交互材料按 mission weight 聚合约为 Cu `41.34%`、Al `21.59%`、Nb `14.10%`、Mu-metal `11.35%`、NbTi `5.79%`、W `5.29%`；
- `>50 keV` escape gamma：`18/420` 行、`7494.4793 counts = 8.4393%`，`Neff=1.88`；
- `>=50 keV` gamma 到达 current-BGO/outer-region proxy：`21/420` 行、`9406.6131 counts = 10.5925%`，`Neff=2.65`；
- sibling IA 点进入任一 active：`1970.5449 counts = 2.2190%`，`Neff=1.12`。

这些比例低 Neff，不能当精密效率；但它们足以证伪需要 `91.6767%` 的全局耦合。甚至把 outer-region `10.5925%` 全部赋予 4-cm 指数收益，联合 residual 仍为 `97948.3 counts`；把这部分**完美删除**的绝对乐观下限仍为 `97765.4 counts`，远高于 `27341.9` gate。

令 `q` 为 full-delayed mission counts 中真正获得 4-cm BGO veto factor 的有效耦合分数，则

\[
R(4,q)=P e^{-1.104}+D[(1-q)+q e^{-3.94}].
\]

过联合门要求

\[
q\ge0.916767205.
\]

作必要性对照：

- 把当前 `86.2844%` straight-ray opportunity 错当成完美有效耦合，仍得 `32037.5 counts`，比门高 `4695.5`；
- 只给无命名冷盘 chord 的 `45.708%` 完美耦合，得约 `67370.2 counts`，明确失败；
- 仅将两条无法唯一追踪的 lineage 当 bypass，理想值为 `20122.8 counts`，仍有余量，但这不能处理其余 418 条的 passive absorption。

因此 `100% relief geometric coverage` 是必要条件但不是 delayed 指数项成立的充分条件；actual-IA 已经触发 P0 falsifier。若只保留 4-cm prompt attenuation，剩余 delayed survival 必须 `<=10.1062%`，即另一个被独立证明的 delayed mechanism 要给至少 `89.8938%` suppression；把实测 outer-reach BGO 收益也计入，仍需约 `88.7224%` 独立 delayed suppression。现有数据没有这个证明。

## 4. 最小 focused prove/falsify

`BG-J4` 已在 P0 KILL，不生成该联合 transport 几何。若工程团队仍想把 4 cm 作为 prompt-only sensitivity，cold core、Cu/Ni、冷盘、Nb/Mu、source position 必须冻结；全周现有 BGO channel 的**每条相关 primary gamma 射线最小新增 chord**为 4 cm，并保留所有真实 relief。结果不得外推为 delayed suppression。

已触发的 P0 条件：

1. complete corrected-gamma denominator 中，baseline-mission-weighted `f_P` 与全部 420 delayed lineage 的 `f_D` 代入上述线性门后已超余量；
2. actual sibling branch 显示可到达新增外层 BGO 的 `>=50 keV` proxy 仅 `10.5925% << 91.6767%`；
3. 或 frozen signal EventList 获得新增 active chord；
4. 或工程 authority 不允许约 4-cm full-wrap BGO envelope / existing-channel readout load。

只有独立 delayed topology 先证明 `>=88.72%` suppression 后，才有理由把 4-cm prompt sensitivity 与它合并成对测试：

- corrected gamma baseline/candidate 同 histories，输出 `E x direction x added-active-grammage x relief class` 的 INIT 分母、BGO deposit、`>=50 keV` veto、first-pair/ANNI/TES ancestry；
- 420 个 exact-position delayed lineages 的 baseline/candidate paired decay仍需逐行输出 sibling 到达新增 BGO、deposit、threshold veto，但不能期待它承担主 delayed 抑制；
- candidate-own n/p/alpha BUILDUP 与 BGO parent-ZA × source-volume 的 W2/Bq fold，量化 `A_new`；
- 最后直接对联合 residual 做置信门，不能把两个指数代理当结果。

此前“若零 bypass，至少 35 个有效独立成功”的统计设计现在已经失去适用性：实际分支不是零 bypass，而是绝大多数在 passive 中先相互作用。不能靠增加同一错误机制的统计把约 10.6% 变成 91.7%。

## 最终 KEEP / MODIFY / KILL

- `BG-J4` 联合 prompt+delayed：**KILL**；全 delayed 指数项被 actual IA 反证；
- `BG-J4` prompt-only sensitivity：**MODIFY / optional diagnostic**，不可领取 delayed credit；
- `BG-TAU5 + BPE-O`：**唯一 physics-defined conditional topology 保留**，但 delayed 必须由 candidate-own BPE BUILDUP×decay fold证明，且整机约 0.61-t BGO 路线仍非 flight-admissible；
- 在现有证据与 flight boundary 下：**NO ADMISSIBLE UNIFIED CANDIDATE**。

机读复算见 `bg_j4_joint_gate_audit.csv`；actual-IA 聚合与材料分解见
`bg_j4_actual_branch_falsifier.csv`。
