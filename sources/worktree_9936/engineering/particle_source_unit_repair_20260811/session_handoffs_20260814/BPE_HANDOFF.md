# S3d-O8 BPE 净收益：冻结证据与第三 session 交接

更新时间：2026-08-14  
范围：只讨论当前 S3d-O8 的 20 mm、约 5 wt% natural-B BPE；不启动新 transport，不把边界代理外推成最终 F3。

## 技术摘要与当前单一判决

**当前判决：REMOVE，但只作为 `ENGINEERING-CONDITIONAL / analytic prior`，置信度至多中等；尚未 physics-promoted。** 精确定义是删除三个 BPE 实体、冻结 plastic/BGO/Al/Kapton/Cu/Nb/Mu/TES 与全部开口。解析质量变化为 **−33.6056166 kg（relief 扣除前）**；约 −33.16 kg 只是不确定的 Boolean-capacity 净体诊断，不能当 BOM。

REMOVE 的正当理由不是“BPE 对中子无效”。现有 20 mm 壳会显著抑制软中子，并使 Cu-61/62 的边界 reaction-current proxy 下降；但证据只到 **BPE 内边界输运与 ≤100 MeV 的直接 Cu 截面折叠**。目前没有冻结其他几何的 0 mm 对照，因此没有证明实际 Cu/Nb/Mu activation、selected delayed W2、总 B20 或 mission F3 改善。

**关键 signal 纠偏已经闭合到几何卡层面：** 当前 geometry card 中 focused ray 的确穿过约 2 cm BPE 和 1 cm plastic，因为这两层没有 signal-window subtraction；但是官方 stage04 的 37,194 条 signal EventList 在它们之后注入，所以 `Aeff=15.04170 cm²` 和 `S20=1645.388` **完全不包含外包络 BPE/plastic 透射**。因此 `T511=0.83069` 只能称“2 cm 实体面板、法向窄束、无碰撞代理”，不能称现有 stage04 Aeff 或真实 flight S20 的实测比例。

若真实飞行 BPE 另有未进入代理卡的 optical aperture，则上述信号代价消失，REMOVE 必须撤回为 `UNRESOLVED`；若权威卡就是 as-built coverage，则 REMOVE 仍是当前解析首选，但 10 mm 和沿 focused cone 开 BPE 窗的 REDISTRIBUTE 尚未被因果淘汰。最终最优需要 candidate-specific S20 与 B20，而不是沿用 post-Be Aeff。

## 1. 权威 BPE：材料、实体、层序、开口和质量

材料卡定义 `Density=0.95 g cm⁻³`、原子计量 `C:H:B=1000:2000:68`，对应约 C 81.364 wt%、H 13.656 wt%、**natural B 4.980 wt%**；没有 B-10 enrichment 或 B4C。20 mm 法向面密度为 1.900 g cm⁻²，其中 natural B 约 0.0946 g cm⁻²。权威入口是 [Materials_DEMO2_DR_v3p5.geo](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/Materials_DEMO2_DR_v3p5.geo:78)。

三个实体均在随 world 绕 y 轴 45° 旋转的 `InstrumentFrame` 中；以下坐标均为 frame-local：

|实体|真实覆盖|解析质量（pre-relief）|
|---|---|---:|
|side shell|`r=27–29 cm, z=-24.5–46.0 cm, φ=0–360°`|23.5657148 kg|
|bottom solid cap|`r=0–29 cm, z=-26.5–-24.5 cm`|5.0199509 kg|
|top solid cap|`r=0–29 cm, z=46–48 cm`|5.0199509 kg|
|合计|三实体闭合壳，除 NF2 rod/mount relief|**33.6056166 kg**|

几何 authority 分别为 [side](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo:16366)、[bottom](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo:16432)、[top](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo:16498)；pre-relief 质量说明见 [S2B README](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/16_geoopt_s2b_cryo_shell_45deg_20260708/README.md:22)。

侧壁从外到内为：

```text
active plastic r=29–30
  -> passive BPE r=27–29
  -> 1.0 cm vacuum
  -> outer Al r=25.7–26.0
  -> gap / Kapton r=25.37–25.40 / 0.17 cm gap
  -> active BGO r=21.2–25.2
  -> vacuum-jacket / Cu-Nb-Mu / TES
```

BPE 和 plastic 只扣 NF2 支撑 relief，**没有** BGO/Al 已有的 `3.796×3.796 cm²` rectangular signal-window cut，也没有 BGO pump-line cut；上下 BPE cap 是实心盘而非环。故“外屏蔽已有光学开口”不能自动推到 BPE：真实 CSG 需要逐层审计。

## 2. Focused 511：三种口径必须分开

|口径|已知事实|允许的用途|
|---|---|---|
|实体面板窄束代理|NIST XCOM `μ/ρ≈0.09763 cm² g⁻¹`；2 cm、ρ=0.95 给 `exp(-μρx)=0.83069`|材料先验和条件 break-even；不是真实 Aeff|
|当前 geometry 的物理外部光路|local `+x` focused bundle 在负 x 侧依次穿 plastic `x≈-30…-29`、BPE `x≈-29…-27`；BGO/Al 窗已开|说明代理卡 as-written 遮挡光路；真实散射、veto、边缘和 as-built aperture 仍待核对|
|官方 stage04 detector-plane Aeff|EventList 在 local `x=-13.1 cm, (y,z)=(0,-5.2)` 注入；当前 Be 卡在 `x=-20.35 cm`，故注入面在 Be 后 7.25 cm，也在 BPE/plastic 后|只度量 post-Be detector acceptance；不得比较 BPE 厚度|

共享 EventList 的 `rmax=1.55356 cm`，方向接近 local `+x`。把 37,194 条 ray 解析反投影到外侧圆柱后，全部落在 BPE/plastic 实体而非 NF2 relief；BPE 弦长约 `2.0000–2.0026 cm`，plastic 约 `1.0000–1.0012 cm`。这证明 **card-as-written** 的 ray/CSG 交线，不证明真实飞行件没有另开的窗。

证据链：实际 [O8 signal source](/home/ubuntu/TES_511_Balloon/runs/geometry_optimization_20260704/s3d_o8_f10m_a1_signal_replay_37194_20260712/Opticsim_laue_f10m_a1_s3d_o8_signal37194.source:14)、[EventList bridge summary](/home/ubuntu/TES_511_Balloon/stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/step09_optics_bridge_summary.json:12)、当前 [Be card](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo:12538)，以及明确声明 post-Be scope 的 [stage04 code](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/code/build_common_response.py:152)。bridge 所用旧 bounds 把 Be 写在 `x=-13.1 cm`，与当前 S3d Be 卡不一致；这进一步确认现有 replay 是内侧注入，而不是 full-envelope signal transport。

## 3. “BPE 正收益”目前只到 boundary-current

|证据层|冻结状态|严格结论|
|---|---|---|
|20 mm 内 first-passage / moderation|SUPPORTED（条件样本）|34,031 个首次接触者中 22,988 到内表面，67.550%；不是 0/20 对照|
|Cu reaction-current fold|PARTIAL|Cu-61/62 proxy 下降；Cu-64 与 1 相容；只含若干直接 n 道且 `E≤100 MeV`|
|volume×isotope day-15 activation A/B|UNRESOLVED|当前只有 20 mm inventory；没有 no-BPE production 对照|
|selected delayed W2 A/B|UNRESOLVED|当前 17 个 n survivor/0.0236791 cps 只能定位耦合，不给 BPE 因果收益|
|prompt/capture-secondary/veto A/B|UNRESOLVED|已有 capture-line-window guard；没有 0 mm cutflow|
|candidate-specific S20、B20、mission F3|UNRESOLVED|官方 stage04/stage06 只描述现有 post-Be 主线，不能归因 BPE|

接受的 boundary run 是 100,000 corrected-neutron histories、8 个独立 shard。所有 generated histories 才是 incident denominator；仅 34.031% 首次接触名义 BPE 外面。按首次接触者：

|incident E|entry→inner|条件通过率|
|---|---:|---:|
|≤0.5 eV|685→11|1.61%|
|0.5 eV–100 keV|5735→1595|27.81%|
|0.1–1 MeV|4818→2888|59.94%|
|1–10 MeV|8751→6659|76.09%|
|10–39 MeV|3976→3224|81.09%|
|≥39 MeV|10066→8611|85.55%|

方向同样重要：local inward `μ=0–0.2` 的条件通过率约 25.4%，`μ=0.8–1` 约 75.4%。这说明软/掠入射压低最强；它不说明哪一方向最终贡献最多 W2。crossing tally 中 inner 50,032 > outer 46,673，是 secondary/recrossing 混入，不是传输率大于 1；未见 surviving-primary EXIT 也不能直接标成吸收。

天然 Cu 的边界 current indices 为 Cu-61 `0.8848±0.0127`、Cu-62 `0.8421±0.0103`、Cu-64 `0.8966±0.0971`。它们支持“20 mm 对部分直接 Cu 快中子道有 modest favorable effect”，**不构成物理上界，也不能线性反演 W2**。

## 4. activation、coupling 与 capture-secondary 物理账本

当前 20 mm geometry 的 full delayed W2 为 0.05447975 cps，其中 incident-family `n` 为 0.02367911 cps（43.46%），只有 17 个等权 selected rows；full delayed `Neff≈28.75`，冻结诊断 `Neff≈12.04`。Cu-61/62/64 占 n-selected rows 的 13/17；主要耦合热点在 MXC Cu plate、Nb inner cylinder、Mu-metal outer cylinder、L0 Cu disk 和 50 mK can bottom。

必须把两栏分开：

```text
production: incident family -> secondary projectile/channel -> material/volume -> isotope -> day-15 Bq
coupling:   isotope/source position -> decay -> shielding/veto -> selected W2 -> mission-time fold
```

现有 lineage 只保证 production family、product ZA、volume 与下游 selected event；`family=n` 不保证真正生产反应的 projectile 仍是 n。Cu fold 仅覆盖 `63/65Cu` 的若干直接 `(n,xn)/(n,γ)` 道且截断在 100 MeV；Y-85、Nb-89/90、Co-54 的 target/projectile/channel，以及 >100 MeV cascade 和 secondary-p 路径仍是 UNKNOWN。尤其不能声称真实 Cu-64 inventory 已由边界 `63Cu(n,γ)` 主导。

BPE watched volume 的 inward track-first-exit 能窗计数中有 3,876 条约 478 keV、109 条约 2.223 MeV / 100,000 source n。它们只是 **非 process-pure、非 unique-capture 的 capture-line-window guard**：478 keV 单光子不能 pair 或直接落入 511 W2，但可造成 Compton/veto/dead-time 或同事件求和；2.223 MeV 可 Compton 到 W2，也可在高 Z 中 pair，但若在 active BGO 中沉积通常有利于 veto。没有 creator/parent ancestry、unique-capture denominator 和 veto cutflow，符号不能预设。当前 BPE 自身 day-15 inventory 约 34.37 Bq、selected lineage 零 survivor，也只能写 `ZERO_MC_SURVIVOR_NOT_ZERO_PHYSICAL_RATE`。

## 5. 判决、盈亏线和条件分支

通用判据必须使用候选自己的信号：

\[
\frac{F_{3,20}}{F_{3,0}}
=\frac{\sqrt{B_{20}/B_0}}{S_{20}/S_0};\qquad
20\ \mathrm{mm\ beneficial}\iff
\frac{B_{20}}{B_0}<\left(\frac{S_{20}}{S_0}\right)^2 .
\]

- **条件 A：真实 BPE 覆盖 focused cone。** 若暂用法向窄束代理 `S20/S0=0.83069`，20 mm 必须把总 B 降至 `<0.69005 B0`（至少 −31.0%）；等价地，REMOVE 在 `B0/B20<1.449` 时胜出。这个门是解析筛选，不是正式 F3。
- **条件 B：真实 BPE 已有未建模 aperture。** 则 BPE-specific `S20/S0≈1`，0.83069 和 31% 门失效；现有 boundary evidence 不能决定 REMOVE/THIN/KEEP/REDISTRIBUTE，必须撤回 signal 驱动的 REMOVE。

冻结的候选层级为：**REMOVE 是当前唯一 actionable analytic prior**；KEEP 只有 boundary proxy；THIN 10 mm 和 focused-window REDISTRIBUTE 是未测的 challenger，不能称已淘汰；THICKEN 没有收益证据并增加质量/capture 风险，30 mm 还侵入冻结 clearance。0 vs 20 若支持 REMOVE，也只淘汰 KEEP-20，不自动证明 0 优于 10 mm 或局部开窗。

因此第三 session 不应继承“REMOVE 已由 17% 实测信号损失证明”，而应继承：**card-as-written 支持 REMOVE 先验；flight aperture 是关键 UNKNOWN；最终判决由 candidate-specific signal × total-background 比决定。**

## 6. 必须独立复核与最小 matched 验证

先做两个零/低成本 gate：

1. 用 flight CAD/BOM 或签字 geometry contract 确认 BPE/plastic 是否在 `|y|≤1.898 cm, |z+5.2|≤1.898 cm` 的 focused cone 有真实开口；同时修正 bridge 的 `x=-13.1` 旧 bounds 与当前 Be `x=-20.35` 不一致。
2. 从 fixed plastic 外侧用同一 37,194-ray bank 做解析 ray/极小 matched replay，得到 0/20 各自真实 `S20`；记录 BPE/plastic path、散射回收和 plastic veto，禁止沿用 stage04 Aeff。

随后只做 **0 mm vs 20 mm** 的 matched corrected-neutron falsifier，其他几何冻结：

1. 共享 primary source bank，fresh independent transport seeds，按 `geometry×mode×family` 独立 TT 归一。
2. 所有 generated n 进入 `E×global direction×surface×z×φ×μ` 分母；互斥输出未接触、primary transmission、moderation、backscatter、relief/bypass、secondary n、capture-secondary。
3. BUILDUP 直接比较每个 Cu/Nb/Mu/BGO/BPE volume 的 Cu-61/62/64、Y-85、Nb-89/90、Co-54 production/day-15 Bq，并保留真实 projectile/channel ancestry。
4. 同时做 n-prompt/capture guard：478/2223 creator、BGO/plastic energy、W2 pre-veto→veto→Step05 cutflow。若 activation 不稳定下降、capture/prompt 反噬或单历史主导，停止。
5. 只有通过前述 gate 的候选才做 exact-position delayed→common response 和自己的 20-day mission fold。最终再补 10 mm/光学窗候选，避免把“0 胜 20”误写成全局最优。

REMOVE 的直接 falsifier 是：用候选真实 `S0/S20` 计算后，`B0/B20` 的预注册单侧上界跨过 `(S0/S20)^2`；或近端 Cu/Nb/Mu activation、capture-secondary/prompt 出现稳定反噬。独立工程门还有 plastic 支撑、重心、振动、热/装配接口，不能由 transport 代替。

## 7. 关键图、表与权威产物

几何与 signal：

- [S3d-O8 geometry card](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo)
- [material card](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/Materials_DEMO2_DR_v3p5.geo)
- [raw focused EventList](/home/ubuntu/TES_511_Balloon/stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/eventlists/Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat)
- [stage04 signal acceptance](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/outputs/04_common_response/signal_acceptance_effective_area.csv)
- [stage04 summary](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/outputs/04_common_response/summary.json)

中子边界与截面 fold：

- [accepted boundary report](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/bpe_neutron_boundary_20260813/REPORT.md)
- [boundary spectrum](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/bpe_neutron_boundary_20260813/outputs/boundary_spectrum.csv)
- [Cu reaction fold](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/bpe_neutron_boundary_20260813/outputs/cu_reaction_fold.csv)
- [E×direction denominator figure](/home/ubuntu/.codex/worktrees/9936/TES_511_Balloon/engineering/s3d_o8_bpe_net_benefit_20260814/figures/bpe_energy_direction_denominators.png)
- [primary transport ledger](/home/ubuntu/.codex/worktrees/9936/TES_511_Balloon/engineering/s3d_o8_bpe_net_benefit_20260814/figures/bpe_primary_transport_ledger.png)

activation、coupling 与 mission：

- [day-15 inventory](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/outputs/02_activation/day15_inventory.csv)
- [selected W2 lineage](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/outputs/04_common_response/selected_background_w2_lineage.csv)
- [production Bq vs coupling figure](/home/ubuntu/.codex/worktrees/9936/TES_511_Balloon/engineering/s3d_o8_bpe_net_benefit_20260814/figures/activation_production_vs_coupling.png)
- [incident→selected W2 flow](/home/ubuntu/.codex/worktrees/9936/TES_511_Balloon/engineering/s3d_o8_bpe_net_benefit_20260814/figures/incident_to_selected_w2_flow.png)
- [official mission summary](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/outputs/06_mission/summary.json)

本文件优先于早先 [BPE analysis report](/home/ubuntu/.codex/worktrees/9936/TES_511_Balloon/engineering/s3d_o8_bpe_net_benefit_20260814/REPORT.md) 中把 `0.83069` 直接解释为实际 selected-signal 损失的表述；其 boundary、activation/coupling 和图表产物仍可使用。
