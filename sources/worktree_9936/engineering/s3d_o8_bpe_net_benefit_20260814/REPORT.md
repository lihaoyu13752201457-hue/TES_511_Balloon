# S3d‑O8 20 mm BPE 净收益与拓扑优化：首轮物理判决

## 技术摘要与单一判决

**判决：REMOVE。** 这是当前证据下的**工程条件最优方案**，不是已经通过完整 0/20 mm 因果链的 physics-promotion 结论。

精确定义是：只删除 `InstrumentFrame` 中的三个 5 wt% natural‑B BPE 实体，其他几何全部冻结：

- 侧壳：`r=27–29 cm, z=-24.5–46.0 cm, φ=0–360°`；
- 下实心盖：`r=0–29 cm, z=-26.5–-24.5 cm`；
- 上实心盖：`r=0–29 cm, z=46–48 cm`；
- 10 mm active plastic、BGO、Al/Kapton、Cu/Nb/Mu、TES、所有 relief 和开口位置均不改。

质量变化按可复算的卡片解析 authority 为 **−33.6056166 kg**（relief 扣除前，含约 −1.674 kg natural B）；MEGAlib Boolean-capacity 的净体诊断约为 **−33.16 kg**，但它不是精确 BOM。不能把 33.6056 kg 伪称 relief 后精确质量。

REMOVE 的物理依据不是“BPE 没有效果”，而是净收益的门槛：20 mm BPE 对法向窄 511 keV 线的无碰撞透射为 `0.83069`，即 BPE 自身损失约 **17.0%** 的 focused signal。由于

\[
F_3\propto \frac{\sqrt{B_{20}}}{S_{20}},
\]

20 mm BPE 必须把**总** 20-day background 相对 0 mm 降到 `<0.69005`，即至少降低 **31.0%**，才抵消信号损失。现有最有利的 Cu 边界 proxy 映射到总 W2 时只对应约 **3.0%** 的背景量级改善；即便把全部 n-delayed 都按最强的 Cu‑62 指数缩放，也只有约 5% 的总背景量级。因此当前证据的数量级明显偏向 REMOVE。

唯一阻断证据是一项固定其余几何的 **matched corrected-keV 0 mm vs 20 mm 因果闭环**：同一配对必须同时给出 volume×isotope day‑15 Bq、capture/prompt+BGO-veto guard、exact-position selected W2，以及从固定 plastic/BPE 外侧发射的各自 focused S20。没有这项对照，REMOVE 不能升格为最终飞行构型；但也没有理由继续把 33.6 kg 的 20 mm 壳当作已证明的净正收益。

![信号—本底破平衡图](/home/ubuntu/.codex/worktrees/9936/TES_511_Balloon/engineering/s3d_o8_bpe_net_benefit_20260814/figures/bpe_signal_background_break_even.png)

## 现有“正收益”证据究竟在哪一级

|证据层|现状|可支持的表述|不能支持的表述|
|---|---|---|---|
|权威 geometry/material|支持|真实组成、位置、覆盖、层序、解析质量|实际飞行 BOM 或结构承载|
|20 mm 内边界慢化/传输|支持|BPE 会强烈压低软/掠入射 neutron，67.55% 首次接触者到达内表面|20 mm 优于 0 mm 的最终本底|
|Cu reaction-current fold|部分支持|Cu‑61/62 的直接反应电流 proxy 下降；Cu‑64 不显著|真实 Cu/Nb/Mu 活化、位置分布或 W2|
|材料×同位素 day‑15 Bq A/B|**未测**|无|10–16% 边界指数就是活化下降|
|selected delayed W2 A/B|**未测**|无|BPE 使 delayed W2 下降 10–16%|
|prompt / capture-secondary / veto A/B|**未测**|当前 20 mm 壳确实产生可见 capture-line guard|prompt gamma 基本中性或有利|
|focused S20 A/B|解析 fold，未全几何验证|20 mm 的 511 signal penalty 不可忽略|沿用 post-Be S20 比较候选|
|总 B20 / 最终 F3 A/B|**未测**|当前官方值只能描述现有主线|把当前 F3 归功于 BPE|

所以对首轮问题的直接回答是：**现有 20 mm BPE 的正收益证据只到边界慢化与直接 Cu 电流 proxy，尚未到材料活化，更未到 selected delayed W2 或最终 F3。** 机器可读审计见 [evidence_level_matrix.csv](/home/ubuntu/.codex/worktrees/9936/TES_511_Balloon/engineering/s3d_o8_bpe_net_benefit_20260814/data/evidence_level_matrix.csv)。

## 权威几何、材料与信号开口

### 材料

材料 authority 在 [Materials_DEMO2_DR_v3p5.geo](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/Materials_DEMO2_DR_v3p5.geo:78)：

- `Density = 0.95 g cm⁻³`；
- 原子计量 `C:H:B = 1000:2000:68`；
- 按标准原子量复算：C 81.3638 wt%、H 13.6561 wt%、natural B 4.9801 wt%；没有 B‑10 enrichment 或 B4C 定义；
- 20 mm 法向面密度 `1.900 g cm⁻²`，其中 natural B 约 `0.09462 g cm⁻²`。

MEGAlib parser 对元素名使用天然同位素组成。因此“5 wt%”是近似标签，真实卡片是约 4.980 wt% natural B。

### 位置、覆盖和层序

三个实体来自同一权威 geometry card：侧壳 [L16366](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo:16366)、下盖 [L16432](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo:16432)、上盖 [L16498](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo:16498)。整体随 `InstrumentFrame` 绕 y 轴旋转 45°。

BPE 不是“一块 20 mm 板”，而是侧筒加两个实心盘盖的闭合外壳。每个 primitive 都扣除了 NF2 mount/rod relief；但 **BPE 没有** BGO/Al 的矩形 signal-window cut、pump-line cut 或顶部 service opening。外侧 10 mm active plastic 同样连续覆盖；BGO side 和外 Al 才有 signal aperture。一般侧壁从外到内为：

`active plastic r=29–30 → BPE r=27–29 → 1 cm void → Al r=25.7–26 → gap → Kapton r=25.37–25.40 → gap → BGO r=21.2–25.2 → cryostat/TES`。

![权威层序与 focused 路径](/home/ubuntu/.codex/worktrees/9936/TES_511_Balloon/engineering/s3d_o8_bpe_net_benefit_20260814/figures/bpe_authoritative_layer_cross_section.png)

当前 focused signal 从 post‑Be plane 注入，[handoff authority](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/s3d_o8_loop_engineering_handoff_20260814/HANDOFF_A_PROJECT_MAINLINE.md:72) 已明确它不含完整 BPE/plastic 外包络。因此 `Aeff=15.04170 cm²` 与 `S20=1645.388` 不能证明 BPE 对 signal 中性。

机器可读几何账见 [geometry_material_ledger.csv](/home/ubuntu/.codex/worktrees/9936/TES_511_Balloon/engineering/s3d_o8_bpe_net_benefit_20260814/data/geometry_material_ledger.csv)。

## 中子能量、方向和 20 mm 壳内输运

接受的 watched-volume run 是 8 个独立 shard、100,000 个 corrected neutron histories；旧 attempt03 因重复 seed 作废。原始 SIM 只从 `/home/ubuntu/TES_511_Balloon/runs/.../production_attempt04` 流式只读，未复制缓存。

### 有分母的 E×direction 图

![入射分母与接触概率](/home/ubuntu/.codex/worktrees/9936/TES_511_Balloon/engineering/s3d_o8_bpe_net_benefit_20260814/figures/bpe_energy_direction_denominators.png)

- 所有 100,000 个 source histories 是真正 incident denominator；只有 34,031 个首次接触名义 BPE 外表面，占 34.031%。其余 65,969 个不是“被 BPE 吸收”，而是未接触、绕行或走 relief/open geometry。
- 首次接触者 22,988 个到达任一名义内表面，条件率 `67.5502%`；95% Wilson CI `67.0508–68.0456%`。名义统计精度高，但它不是 0 mm A/B。
- 首次接触面：side 24,196、bottom 6,810、top 3,025。对应条件通过率为 69.00%、65.46%、60.63%。
- 首次接触能量中位数为 4.086 MeV；corrected source mixture 中位数约 3.019 MeV。旧“约 3 keV”是 factor‑1000 错轴，已排除。

按首次接触能量的 `entry → reach inner`：

|能量|entry|reach|条件通过率|
|---:|---:|---:|---:|
|≤0.5 eV|685|11|1.61%|
|0.5 eV–100 keV|5,735|1,595|27.81%|
|0.1–1 MeV|4,818|2,888|59.94%|
|1–10 MeV|8,751|6,659|76.09%|
|10–20 MeV|1,946|1,573|80.83%|
|20–39 MeV|2,030|1,651|81.33%|
|≥39 MeV|10,066|8,611|85.55%|

这张表说明 20 mm BPE 的优势集中在已软化或较低能 neutron；对主导穿透风险的 tens–hundreds MeV 成分很薄。`≥39 MeV` 的旧大箱还混入 `>100 MeV`，而 Cu fold 明确截断在 100 MeV，因此不能用 fold 处理高能 cascade。

### moderation、backscatter、leakage 与 capture-secondary 分栏

对 34,031 个 first-contact histories 的互斥首次通过账本为：

- 22,988 个到达内表面：15,265 个能量未变、1,242 个损失 <10%、3,640 个损失 10–90%、2,839 个损失 >90%，另有 2 个能量增加；
- 6,251 个返回名义外表面；
- 800 个从 relief/edge 离开 watched BPE；
- 3,992 个没有 surviving-primary watched-volume EXIT。最后一类包括 capture/inelastic/termination，但缺完整 ancestry，**不能标成纯 absorption**。

![20 mm BPE 主中子输运账本](/home/ubuntu/.codex/worktrees/9936/TES_511_Balloon/engineering/s3d_o8_bpe_net_benefit_20260814/figures/bpe_primary_transport_ledger.png)

所有 crossing 谱中 inner neutron crossing 多于 outer 并不表示传输率 >100%；它混入 secondary 与 recrossing。我们的事件级 first-passage 与 crossing-current 分开保存，见 [contact_event_outcomes.csv](/home/ubuntu/.codex/worktrees/9936/TES_511_Balloon/engineering/s3d_o8_bpe_net_benefit_20260814/data/contact_event_outcomes.csv) 和 [inner_emergent_secondaries.csv](/home/ubuntu/.codex/worktrees/9936/TES_511_Balloon/engineering/s3d_o8_bpe_net_benefit_20260814/data/inner_emergent_secondaries.csv)。

20 mm watched volume 内向产生了明显 photon guard：每 100,000 source n 中有 3,876 条约 478 keV、109 条约 2.223 MeV 的“track first seen exiting BPE inward”记录。它们是能线窗口而非 process-pure ancestry，但足以否决“prompt gamma 可默认中性”的假设。

![二次中子与 photon guard](/home/ubuntu/.codex/worktrees/9936/TES_511_Balloon/engineering/s3d_o8_bpe_net_benefit_20260814/figures/bpe_inner_emergent_secondaries.png)

按 [TUNL B‑10 evaluation](https://nucldata.tunl.duke.edu/nucldata/HTML/A%3D11/11B_2012.shtml)，热 `¹⁰B(n,α)⁷Li` 截面约 3837 b，约 94% 发出 478 keV γ；[H capture evaluation](https://nucldata.tunl.duke.edu/nucldata/TNC/02H.shtml) 给出 **2223.248 keV** γ。当前组成下，已热化且走满 2 cm 的 neutron 直线吸收估算约 98.3%，其中约 98.7% 归于 ¹⁰B。真正短板不是吸收已热化 neutron，而是 2 cm 能否先慢化 MeV–100 MeV 成分，以及 capture γ 是否被 BGO veto 或反而制造 prompt/pair-host 路径。

## activation production 与 detector coupling 必须分栏

当前 20 mm 几何的 day‑15 inventory 是 `1404.231 Bq`，其中 incident n 为 `348.222 Bq`；当前 selected delayed W2 为 `0.05447975 cps`，其中 n 为 `0.02367911 cps`（43.46%）。这些是同一现有几何的下游列，**没有 0 mm 对照**。

![入射到 selected W2 的因果缺口](/home/ubuntu/.codex/worktrees/9936/TES_511_Balloon/engineering/s3d_o8_bpe_net_benefit_20260814/figures/incident_to_selected_w2_flow.png)

最能说明耦合问题的是：n-induced inventory 的 69.8% 在 active scintillator，但当前 n-selected W2 在那里没有 survivor；相反，cold plates 只占约 7.0% n-Bq，却贡献约 41.2% n-W2，near‑TES other-internal 贡献约 52.9%。所以“把进入内部的 neutron current 降低 10–16%”不能直接变成 W2 收益。

![production Bq 与 selected W2 coupling](/home/ubuntu/.codex/worktrees/9936/TES_511_Balloon/engineering/s3d_o8_bpe_net_benefit_20260814/figures/activation_production_vs_coupling.png)

当前关键 n-induced 路径为：

|同位素|day‑15 Bq|selected W2 (cps)|support|当前热点/解释|
|---|---:|---:|---:|---|
|Cu‑61|3.2087|0.0027858|2 rows, Neff 2|MXC cold-plate anchor；边界 fold 稳，但位置 A/B 未测|
|Cu‑62|10.7482|0.0083573|6, Neff 6|MXC、L0 Cu disk、50 mK can；当前 n 主项|
|Cu‑64|23.0446|0.0069644|5, Neff 5|近端 Cu；边界 fold 仅 1.1σ，capture 权重大|
|Y‑85|0.04488|0|0|存在 inventory；零 survivor 不是零 coupling|
|Nb‑89|0.06732|0.0013929|1, Neff 1|Nb inner cylinder；单高权重事件|
|Nb‑90|0.06732|0|0|存在 inventory；未获 selected support|
|Co‑54|0.06732|0.0013929|1, Neff 1|MuMetal outer cylinder；单高权重事件|

完整表见 [priority_neutron_isotope_ledger.csv](/home/ubuntu/.codex/worktrees/9936/TES_511_Balloon/engineering/s3d_o8_bpe_net_benefit_20260814/data/priority_neutron_isotope_ledger.csv)。BPE 自身 day‑15 inventory 为 `34.373 Bq`（约总 inventory 2.45%），当前 selected lineage 零 BPE survivor；但 delayed source mix 中实际有大量 BPE-trigger sampling，所以只能写 `ZERO_SURVIVOR_NOT_ZERO_PHYSICAL_RATE`。

full delayed 的总 Neff 约 28.75；冻结诊断 Neff 只有 12.04，top 12 rows 占 92.28%。空间热点图只能说明 near‑TES inventory 的高 coupling，不足以用少数 survivor 反推 incident direction。

![selected W2 空间热点](/home/ubuntu/.codex/worktrees/9936/TES_511_Balloon/engineering/s3d_o8_bpe_net_benefit_20260814/figures/selected_w2_hotspot_map.png)

## Cu fold 复核：它支持什么

共同 `0<E≤100 MeV`、8-shard jackknife 的 inward-current indices 为：

- Cu‑61 `0.884755 ± 0.012707`：在这个 estimator 内约 9.1σ 低于 1；
- Cu‑62 `0.842146 ± 0.010264`：约 15.4σ；
- Cu‑64 `0.896560 ± 0.097060`：约 1.1σ，不显著；其中 `⁶³Cu(n,γ)` 为 `0.9021±0.1063`，`⁶⁵Cu(n,2n)` 为 `0.8369±0.0082`。

Cu‑64 inner fold Neff 约 98，top‑10 crossing 权重约 25.8%；8 个 shard 的局部统计误差不覆盖缺失的 >100 MeV cascade、绕行、path length、材料数密度、activation position、delayed transport 和 veto response。

当前 17 条 n-delayed survivor 中 13 条为 Cu‑61/62/64。按 2/6/5 条加权 fold 得约 `0.8696`，它只是用当前 survivor 做的机制插值。作为**非预测性数量级场景**，把三种 Cu W2 分别除以 index，会使 no-BPE 总 W2 从 `0.0883227` 增到 `0.0910556 cps`，仅 +3.09%；对应 `F3_REMOVE/F3_20mm≈0.843`，即 REMOVE 约改善 15.7%。这个数字不能作为最终率，但它显示现有正收益规模离 31% break-even 很远。

## prompt、focused signal 与任务 F3 账本

### Prompt

- 2 cm 低 Z BPE 对已有数 MeV incident γ 的直接 attenuation/pair-host 改变预计较小，但“较小”不能替代数据；
- 当前 n-prompt 在 active veto 后零 W2 survivor，但 95% upper 仍约 `0.0826 cps`，没有 0 mm comparator；
- 最终 prompt W2 只有 2 个 γ survivor，统计非常稀疏；另有 3 条条件 leakage ray 只证明那三条在 BPE 中未相互作用；
- 478 keV 不能 pair 或直接形成 511 line，却能加 prompt Compton/veto load；2.223 MeV 高于 1.022 MeV，可在内侧高 Z BGO/Cu/Nb 中产生 pair 与 annihilation 511。

因此首轮 0/20 screen 必须同时记录 BGO/plastic veto 前后 capture-secondary，不能只看 delayed activation。

### Focused signal

[NIST XCOM](https://www.nist.gov/pml/xcom-photon-cross-sections-database) 在 0.511 MeV 给当前 BPE mixture `μ/ρ=0.09763 cm² g⁻¹`，几乎全是 Compton；固定 plastic 的 [polystyrene value](https://physics.nist.gov/PhysRefData/XrayMassCoef/ComTab/polystyrene.html) 约 `0.09293 cm² g⁻¹`。法向窄线一阶 fold 为：

|BPE|raw/pre-relief mass|BPE-only T511|含固定 plastic T511|`B20max` 相对 0 mm|工程状态|
|---:|---:|---:|---:|---:|---|
|0 mm|0|1.0000|0.9087|1.0000|**REMOVE 判决**|
|10 mm|17.0132 kg|0.9114|0.8282|0.8307|需总 B 降 >16.9%，无证据，淘汰|
|20 mm|33.6056 kg|0.8307|0.7549|0.6900|需总 B 降 >31.0%，现有 proxy 远不足，淘汰|
|30 mm|49.7772 kg|0.7571|0.6880|0.5732|还会与冻结的 cap Al/Kapton 重叠，工程淘汰|

10/30 mm 的质量按“plastic 外接口固定、BPE 向内生长/收缩”解析；30 mm side 会耗尽全部 1 cm clearance，caps 已穿入 Al/Kapton，不能在其余几何冻结条件下成立。

按现有 post‑Be S20 作纯解析外包络 fold，20 mm 与 0 mm 的 estimated full-envelope S20 分别约 1242 与 1495 counts；若背景相等，对应 F3 screen 约 `9.17e-5` 与 `7.62e-5`。这些不是新的官方任务率，只用于说明被遗漏的外包络不是小修正。最终必须从外包络之外重放 focused ray，包含真实角分布与散射回收。

## 为什么不是 THIN / KEEP / THICKEN / REDISTRIBUTE

它们不是同级候选；在本轮已被判定为不优于 REMOVE：

- **THIN 10 mm**：仍付出 8.86% signal penalty、约 17.0 kg 质量，必须得到 >16.9% 的总 B 降幅；没有该量级证据。
- **KEEP 20 mm**：只有边界/Cu proxy，未跨到 activation/W2/F3，而且 31.0% break-even 远高于 proxy 数量级。
- **THICKEN**：signal、质量和 capture γ 风险同时恶化；30 mm 又违反冻结几何 clearance。
- **REDISTRIBUTE**：side 24 个 `z×φ` 区域各有 621–1375 个 incident contacts，条件通过率约 63.1–72.4%，说明几何/谱混合有变化；但没有 region-specific 0/20 activation 或 selected-W2 coupling。强度分母不能替代“该方向最终产生多少 TES W2”。PoGO+ 的局部增厚经验只说明有已验证 gap 时局部方案可能优于全局方案，不能把其厚度照搬。

### 文献可迁移边界

- [XL‑Calibur mission study](https://doi.org/10.1016/j.astropartphys.2020.102529)：5–8 cm PE 仅把 15–80 keV 模拟背景由约 0.51 降到 0.44 Hz，却增加至少 30 kg，未采用；说明强 BGO veto 下 PE 的质量收益可很小。
- [XL‑Calibur shield study](https://doi.org/10.1016/j.nima.2022.167975)：3 cm HDPE 只有 marginal improvement，漏过主体是 >10 MeV albedo γ/n；支持 prompt/veto 联合账，不支持照搬厚度。
- [PoGO+](https://doi.org/10.1016/j.astropartphys.2016.06.005)：在确认 side-bottom gap 后，局部 10 cm/+16.8 kg 得到约 12% n-rate 改善，而更重的全底/顶方案未选；只迁移“先有方向分母再局部优化”的方法。
- [MEGANE 5 wt% boron PVT](https://link.springer.com/article/10.1186/s40645-025-00763-x) 的强性能主要来自 active prompt→capture 时序 veto；本任务禁止新增 readout，因此不能迁移其主动收益。

## 统计可信度与工程风险

### 可信度

- **边界 first-passage：高（仅条件统计）**。100,000 histories；67.5502%，Wilson 95% 半宽约 0.50 percentage point。
- **Cu‑61/62 proxy：中高（仅 estimator 内）**；Cu‑64：低。systematic scope gap 大于所报 jackknife error。
- **current selected delayed attribution：低到中**。full Neff≈28.75、frozen Neff≈12.04；Nb‑89/Co‑54 各由一个 n survivor 支持。
- **511 attenuation screen：中高的解析先验**。XCOM coefficient 的不确定性不是主项；主项是 full-geometry angle/scatter recovery，当前未测。
- **最终 REMOVE physics confidence：不足以 promotion；工程筛选置信度为中等偏高**。关键理由是 signal break-even 与现有 background mechanism 之间有约一个数量级的余量，但 0 mm 内部 activation rebound 尚未直接测量。

### 工程风险

1. 去掉 BPE 后，低能/热 neutron 可更直接到达 BGO、Cu/Nb/Mu；这正是唯一因果对照要排除的 physics risk。
2. BPE card 是被动体而非 sensitive detector，但 geometry 文件不证明它不承载 plastic 或 mount；移除前必须核对 plastic support、重心、ballast、振动与真空/热接口。
3. −33.6 kg 会显著改变吊舱质量分配；这是价值也是重心/结构风险。
4. 0 mm 会留下更大 void，但不改变固定 plastic/BGO clearance；不得用新主动 guard、mK scintillator、readout copper 或复杂微加工补偿。

## 最小配对验证：只做能推翻 REMOVE 的实验

第一轮不做 0/10/20/30 大扫描，只做精确的 **0 vs 20 mm**：

1. 冻结 plastic、BGO、Al/Kapton、Cu/Nb/Mu、TES、开口和 source surface；0 mm 仅删除上述三个 BPE volume。
2. 用同一保存的 corrected-neutron primary bank 配对，两个 geometry 使用 fresh、独立 transport seeds；保持 `geometry×mode×family` 独立 TT normalization。建议先做 8×12,500 histories/geometry 的小 pilot，和现有边界统计同量级。
3. 每个 generated history 都进入 incident denominator；输出 `E×global direction×surface×local z×φ×μ`，并互斥分栏 primary transmission、moderation、backscatter、relief/bypass、no-primary-exit、secondary neutron、478/2223-keV ancestry。
4. BUILDUP 直接比较 Cu‑61/62/64、Y‑85、Nb‑89/90、Co‑54 在每个 volume 的 production/day‑15 Bq；同时做 n-prompt capture guard 和最小 incident γ guard，保留 BGO/plastic veto 前后结果。
5. 如果 REMOVE 没有出现大幅近端 activation rebound、prompt/capture 反噬或单历史支配，再为 **REMOVE 一个候选**做 exact-position delayed→common response；最后补 full eight-family 与 mission fold。
6. focused signal 必须从固定 plastic 的外侧发射 matched rays，为 0/20 各得自己的 S20。预注册判据：

\[
\frac{F_{3,0}}{F_{3,20}}=
\frac{\sqrt{B_0/B_{20}}}{S_0/S_{20}}<1,
\]

且 compound/weighted-MC 的单侧置信上界也要 <1；不能只用中心值。若外包络 replay 给 `S0/S20≈1/0.83069=1.204`，则背景 break-even 是 `B0/B20<1.449`。

直接淘汰条件：结果由单个高权重历史控制；selected W2/Bq 不改善；capture-secondary/prompt 抵消；或 REMOVE 的总 `B0/B20` 上界跨过自己的 signal-squared 门。

## 可复现产物

- 边界重折脚本：[analyze_existing_bpe_boundary.py](/home/ubuntu/.codex/worktrees/9936/TES_511_Balloon/engineering/s3d_o8_bpe_net_benefit_20260814/code/analyze_existing_bpe_boundary.py)
- activation/coupling 与 break-even 脚本：[build_physics_ledger.py](/home/ubuntu/.codex/worktrees/9936/TES_511_Balloon/engineering/s3d_o8_bpe_net_benefit_20260814/code/build_physics_ledger.py)
- 总结 JSON：[physics_ledger_summary.json](/home/ubuntu/.codex/worktrees/9936/TES_511_Balloon/engineering/s3d_o8_bpe_net_benefit_20260814/data/physics_ledger_summary.json)
- candidate screen：[bpe_candidate_analytic_screen.csv](/home/ubuntu/.codex/worktrees/9936/TES_511_Balloon/engineering/s3d_o8_bpe_net_benefit_20260814/data/bpe_candidate_analytic_screen.csv)
- activation×coupling 明细：[activation_coupling_by_path.csv](/home/ubuntu/.codex/worktrees/9936/TES_511_Balloon/engineering/s3d_o8_bpe_net_benefit_20260814/data/activation_coupling_by_path.csv)
- 来源登记：[source_register.csv](/home/ubuntu/.codex/worktrees/9936/TES_511_Balloon/engineering/s3d_o8_bpe_net_benefit_20260814/data/source_register.csv)

本轮只做只读物理分析与小型流式重折，没有启动新的 transport 或大模拟，也没有覆盖源包。
