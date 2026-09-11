# S3d-O8 LOOP ENGINEERING 物理交接

日期：2026-08-14  
范围：corrected gamma（已含 annihilation bump，不另加 mono-511）、day-15 activation、20-day mission fold。归一边界始终为 `geometry × mode × family`。本 session 只读流式复核原始 SIM/source/DAT 与既有小表；没有继续 transport、BUILDUP 或 full-chain。

## 核心判决

**当前没有达到 `F3 <= 3e-5 photon cm^-2 s^-1` 的可晋级修改方案。单一判决为：`KEEP S3d-O8 baseline + 现有 20 mm BPE；NO_ADMISSIBLE_MODIFIED_CANDIDATE；不启动 transport`。**

这里把它记为 **ENGINEERING-CONDITIONAL OPTIMUM**：它只是所有已审方案中唯一未被物理上界或热/磁/结构约束直接证伪的硬件状态，不是“已经达标”。现有 20 mm BPE 的 corrected-neutron 边界折叠显示小幅正收益，故不应凭旧的 keV 轴结论删除；但它也远不足以独立闭合预算。

共同 mission 权威量为 `P20=55,398.979434`、`D20=88,804.862652`、`S20=1,645.387753` counts，formal gate `(S20/10)^2=27,073.008579` counts。即使 prompt 理想归零，delayed 仍须降低 `69.51%`。本轮没有 candidate-own `S20/F3`，所以任何 proxy PASS 都不得写成达标。

## 1. 本 session 实际独立复核的 FACT

- 三条 S3d prompt lineage 回接了 `INIT → PAIR → ANNI → TES`，并用真实 CSG 逐材料求 chord/grammage；完整 gamma 分母为 `3,207,738 INIT`、`TT=59.0965413 s`。
- 完整 delayed authority 为 420 条唯一 W2 rows、`0.0544797522273 cps`。mission-weight event `Neff=28.687`，最大单事件 `5,017.164 counts=5.65% D20`；66 个 source positions 的 position `Neff≈24.93`，但具名组件均 `<8`。
- 420/420 delayed 坐标与 compact source catalog 匹配；135/135 frozen component 坐标残差为零。n/p/alpha rich BUILDUP 中 577 个 target RP 与 inventory key 闭合。
- BPE 专项的可接受样本为 corrected-keV neutron、100,000 histories、八个独立 CLI seeds、`TT=19.21636 s`；旧的重复 seed launch 已排除。它是 boundary diagnostic，不是 no-BPE final-background 预测。
- 所有 budget ceiling 都只删除 baseline selected rows 一次；production Bq 没有与已加权 W2 counts 重复相加。

## 2. Prompt：厚 active 的随机零相互作用尾，而非几何孔

| event | 入射方向（IF）/能量 | active / passive grammage | first pair → annihilation | TES / selection |
|---|---|---:|---|---|
| 3883 | `theta_x=82.22°`, `az=74.10°`; 4.148 MeV | 23.434 / 20.271 g cm⁻² | Nb inner → Mu-metal outer | L2, 510.999 keV；PASS |
| 19932 | `135.23°`, `291.68°`; 5.769 MeV | 38.923 / 32.674 | DR mixing-chamber Cu → 同一 Cu | L2, 510.999 keV；PASS |
| 8081 | `144.80°`, `14.70°`; 6.346 MeV | 29.754 / 18.123 | Nb inner → L0 Cu | L5, 69.584+441.415 keV；Step05 FAIL |

三条在 BGO/plastic 的 deposited energy 都为零，但射线实际穿过厚 active grammage；因此是随机无相互作用尾，不是 top/side hole。加入 `energy × equal-solid-angle direction × active-grammage` 后，三个非零 cell 仅为 `k/N=1/71, 1/94, 1/92`，每格 `Neff=1`；不能据此选方位 sector、M4 孔或全天角抑制率。

没有 veto 的直接图像是 anti-TES 511 先被内侧 passive 件处理：3883 经过 `2.906 cm Cu + 1.483 cm Ag + 0.198 cm Mu` 后才见 side BGO；19932 经过 `3.946 cm Cu + 4.768 cm SS + 2.029 cm BPE + 1.217 cm Al`，且没有 top-BGO chord；8081 经过 `1.844 cm Cu + 0.387 cm Nb + 0.387 cm Mu` 后见 side BGO。Mass-model 七条对照的 pair hosts 又分散于 Al/Nb/Cu/SS，证明共同机制是“穿 active 后在内侧 passive pair”，而非唯一 Nb、Mu 或 Cu patch。

**数据更正：**旧 PA-X1 analysis box 只覆盖 L0–L4，曾把 8081 错标为直线 miss。full-six-layer CSG 显示其初始 511 直达 L5，随后才在 TES 内 COMP；到首个 TES pixel 前穿 `0.6583 cm L0 Cu`。旧标签不得再使用。

Host migration 是删盒方案的直接反证：删 Nb 后，3883 原 primary 的下一 Cu 为 `0.630 cm MXC + 0.550 cm DR Cu`；8081 下一段为 `4.101 cm MXC Cu`。19932 的 pair/annihilation 全在保留的 DR Cu，删磁盒还移除 TES-bound 511 原有 `0.4195 cm` Nb/Mu 衰减，uncollided 透射标度约增至 `×1.366`。

## 3. Delayed：family → material → isotope → position → W2

严格定义为：`q_k=ΣRP_k/ΣTT_(S3d-O8, BUILDUP, family)`，包括 zero-RP DAT 的 TT；day-15 `A_k` 是 inventory 衰变/饱和后的 Bq；`epsilon_k=selected W2/realized decays` 只在同一 `family × parent-ZA × exact volume/position` 内成立。`A_k × epsilon_k` 只有在 source mix 代表 inventory 时才可作 screening，不能跨 key 拼接。

物理 origin 不是“低能 neutron 单独激活 Cu”。p/alpha primary 常在几十 GeV 级联中先产生 secondary neutron，再由 nCapture/nInel 形成 Cu-61/62/64；n family 同时含低能 capture 与 GeV cascade。代表性 mission 热链为：

| family → material/parent @ position | W2 mission counts | 限制 |
|---|---:|---|
| n → Cu-62 @ MXC | 6,867.391 | 聚合热点 |
| n → Cu-62/64 @ L0 | 4,578.261 / 4,422.360 | L0 position `Neff` 低 |
| p → Cu-62/61 @ MXC | 5,017.139 / 4,990.996 | 单个高权重 history 主导 |
| p → Cu-64 @ L5 | 4,847.141 | 单一 source point |
| alpha → Cu-64 @ CP / can bottom | 1,863.943 / 1,863.943 | 各为单事件热点 |
| p → Y-85 @ Nb inner | 4,999.792 | 单事件；0.0998 Bq sparse chain |
| n → Nb-89 @ Nb inner | 2,284.710 | sparse coupling |
| n → Co-54 @ Mu outer | 2,289.145 | 单事件 |

材料聚合 screening 为：Cu `112.251 Bq / 0.0363911 cps / 3.81e-4 W2/Bq`；Nb `1.164 Bq / 0.0092015 cps / 9.44e-3 W2/Bq`；Mu-metal `1.361 Bq / 0.0077655 cps / 6.21e-3 W2/Bq`。即 Cu production 最大，而 Nb/Mu 的近场 coupling 每 Bq 高约一个数量级。MXC 是最大聚合组件，但其 position `Neff=7.77`；Nb/Mu/L0/can 约为 `2–3`，L5/L2/Ag 各只有一个位置。任何平滑 bubble 都必须同时标单事件权重。

### BPE 专项合并结论

20 mm、5 wt% BPE 对首次接触外表面的 corrected neutron，`34,031` 条中 `22,988` 条到达内表面，conditional transmission `67.55%`。对 `>=39 MeV` 首次入射仍有 `85.55%` 穿透；它主要抑制慢中子并部分慢化 MeV 群，不能阻止内层 p/alpha cascade。

natural-Cu direct-channel output/input current indices 为 Cu-61 `0.8848±0.0127`、Cu-62 `0.8421±0.0103`、Cu-64 `0.8966±0.0971`；按已观察 Cu W2 share 加权约 `0.870`，即 central 约 13% 有利。Cu-64 capture 的误差尚不能排除 neutral。**这不是 final W2 suppression，也不能外推 BPE 厚度最优值。**唯一闭合测试是同源、同几何仅改 BPE `0 vs 20 mm` 的 matched BUILDUP→inventory→delayed comparison；本 session 未运行，结论为 `UNKNOWN`。

## 4. LOOP 候选冻结判决

| 候选/机制 | 判决 | 直接理由 |
|---|---|---|
| S3d-O8 baseline + 20 mm BPE | **KEEP / ENGINEERING-CONDITIONAL OPTIMUM** | 唯一未被现证据证伪的功能完整状态；不代表达标 |
| 由三条 prompt leak 选 sector、开孔 | **KILL** | cell `Neff=1`；不是几何孔 |
| 合法冷盘：OD最多−25%、厚度−10%、少量M4 | **KEEP only as auxiliary** | delayed 极乐观信用 9,078.066 counts=10.22% D，`Neff=5.58`；prompt 记零 |
| skeletal cold plate / 48-volume Cu→Al | **KILL** | 前者违反冷盘边界；后者破坏核心导热且 Al activation UNKNOWN |
| Nb/Mu-only、R8–10 cm standoff | **KILL** | 预算不足；真实 MXC/can/W/service 包络冲突 |
| 去 Nb/Mu + 50 mK can | **几何可定义；物理 KILL** | 热/磁资格 UNKNOWN；极乐观 residual 仍失败，prompt 可能变坏 |
| 去 Nb/Mu + L0 cage（或再加 can） | **STRONG KILL** | 切断 TES/support→cold-finger 热/机械接口 |
| +4 cm full-wrap BGO（BG-J4） | **KILL as unified** | actual delayed outer-reach `10.59%`，而需 `91.99%`；约增 488 kg |
| 近场角选择 | **KEEP mechanism** | 37,194 signal 最大偏轴 `0.460°`；418 delayed 在 10° 内为 0 |
| PA-X1 五面 Cu shadow | **KILL geometry** | 需连续 Cu `2.308–3.140 cm`；真实 corner/face/x+ 仅 `1.384/2.150/0.410 cm` |
| 65Cu isotope engineering | **KILL** | target isotope 未序列化；known-channel 净信用仅 3.70%，Cu-66 风险 UNKNOWN |
| 额外 BPE-only / 定向 BPE | **KILL as sufficient；MODIFY as matched diagnostic** | 现有直接机制约 10–16%，不能承担约 70% delayed 门；无方向分母支持 sector |

## 5. 即使极乐观也达不到门的方案

- prompt=0 时，baseline delayed `88,804.863` 仍须降到 `27,073.009`。
- 所有 exact Cu selected rows 100% 删除、无 host migration 时，`D=29,552.286 > gate`；尚未加入 prompt。
- 磁屏蔽+can+L0 的旧 rows 100% 删除时，`D=44,992.136 > gate`；加 baseline prompt 后为 `100,391.116`。
- prompt 去磁盒/铜盒的 observed-chain 理想 ceiling 仅 50%；`P20/2=27,699.49 > total gate`，即使 delayed=0 仍失败。
- BG-J4 即使给几何直线 4 cm BGO chord，实际 delayed sibling `>=50 keV` outer-reach proxy 只有 `10.5925% (Neff=2.65)`；把该部分完美删掉，联合 residual 仍约 `97.8k` counts。
- 一个故意过度给 credit 的组合（合法冷盘、L0/can/DR/Ag/CuNi、远置 magnet、+4 cm BGO）再强加 **30% global BPE**，仍为 `38,799.368 > 27,073.009` counts。
- PA-X1 即使零间隙填满并重复领取 L0/can 信用，delayed 最大抑制也仅 `62.7748%`；prompt=0 的 residual `0.0202802 cps` 仍高于 gate-equivalent `0.01600955 cps`。

## 6. 第三个 session 必须特别质疑的假设 / UNKNOWN

1. **BPE boundary index ≠ final W2 suppression。**必须质疑 bypass、`>100 MeV` cascade、secondary hadrons、position migration 和 veto/cut；没有 matched `0 vs 20 mm` 就不能宣称最优厚度。
2. **Perfect deletion ≠ candidate prediction。**删 Cu/Nb/Mu rows 会同时失去 passive grammage、改变 pair/annihilation host，并在替代材料产生新 parents。
3. **低 Neff。**组件 central credit、Cu isotope、outer-reach 和单一 source-position 热点都不是置信界；必须报告 event/position Neff 与最大 history 权重。
4. **真实 CAD/BOM。**当前唯一工程阻断证据是缺少 configuration-controlled as-built thermal/magnetic/service interface authority；没有它，就不能证明一个保留 Cu 导热、Nb/Mu 磁性能和全部 signal rays 的近场 topology。
5. **候选自己的门。**若未来有唯一可制造 topology，先做 paired focused `family × parent-ZA × exact position` production→decay 和完整 gamma denominator，再做 candidate S20；必须把新增/迁移 Cu/Ni/SS/BPE activation 纳入。未过 central `F3<=3e-5` 即 KILL，不得用三条 root replay 或 straight-ray CSG 代替。

## 7. 关键图、表与权威产物

- Prompt 三视图/有分母漏率：[/home/ubuntu/.codex/worktrees/6f6c/TES_511_Balloon/engineering/s3d_o8_loop_engineering_20260814/figures/prompt_threeview_denominator_leakage.png](/home/ubuntu/.codex/worktrees/6f6c/TES_511_Balloon/engineering/s3d_o8_loop_engineering_20260814/figures/prompt_threeview_denominator_leakage.png)
- Prompt 链与 grammage：[/home/ubuntu/.codex/worktrees/6f6c/TES_511_Balloon/engineering/s3d_o8_loop_engineering_20260814/agents/prompt/prompt_leak_event_summary.csv](/home/ubuntu/.codex/worktrees/6f6c/TES_511_Balloon/engineering/s3d_o8_loop_engineering_20260814/agents/prompt/prompt_leak_event_summary.csv)
- Prompt 完整方向分母：[/home/ubuntu/.codex/worktrees/6f6c/TES_511_Balloon/engineering/s3d_o8_loop_engineering_20260814/agents/prompt/denominator/incident_gamma_E_mux_az_denominator.csv](/home/ubuntu/.codex/worktrees/6f6c/TES_511_Balloon/engineering/s3d_o8_loop_engineering_20260814/agents/prompt/denominator/incident_gamma_E_mux_az_denominator.csv)
- Full-six-layer / 去盒 prompt 审查：[/home/ubuntu/.codex/worktrees/6f6c/TES_511_Balloon/engineering/s3d_o8_loop_engineering_20260814/thermal_cu_rethink_20260814/agents/prompt/BOX_REMOVAL_PROMPT_REVIEW.md](/home/ubuntu/.codex/worktrees/6f6c/TES_511_Balloon/engineering/s3d_o8_loop_engineering_20260814/thermal_cu_rethink_20260814/agents/prompt/BOX_REMOVAL_PROMPT_REVIEW.md)
- Delayed bubble / production-to-W2 图：[/home/ubuntu/.codex/worktrees/6f6c/TES_511_Balloon/engineering/s3d_o8_loop_engineering_20260814/figures/delayed_space_production_w2_flow.png](/home/ubuntu/.codex/worktrees/6f6c/TES_511_Balloon/engineering/s3d_o8_loop_engineering_20260814/figures/delayed_space_production_w2_flow.png)
- Delayed flow 表：[/home/ubuntu/.codex/worktrees/6f6c/TES_511_Balloon/engineering/s3d_o8_loop_engineering_20260814/agents/delayed/delayed_production_to_w2_flow.csv](/home/ubuntu/.codex/worktrees/6f6c/TES_511_Balloon/engineering/s3d_o8_loop_engineering_20260814/agents/delayed/delayed_production_to_w2_flow.csv)
- Delayed 主审阅：[/home/ubuntu/.codex/worktrees/6f6c/TES_511_Balloon/engineering/s3d_o8_loop_engineering_20260814/thermal_cu_rethink_20260814/agents/delayed/THERMAL_CU_DELAYED_LOOP.md](/home/ubuntu/.codex/worktrees/6f6c/TES_511_Balloon/engineering/s3d_o8_loop_engineering_20260814/thermal_cu_rethink_20260814/agents/delayed/THERMAL_CU_DELAYED_LOOP.md)
- 近场角分离/弦长 falsifier：[/home/ubuntu/.codex/worktrees/6f6c/TES_511_Balloon/engineering/s3d_o8_loop_engineering_20260814/thermal_cu_rethink_20260814/figures/nearfield_angle_and_chord_falsifier.png](/home/ubuntu/.codex/worktrees/6f6c/TES_511_Balloon/engineering/s3d_o8_loop_engineering_20260814/thermal_cu_rethink_20260814/figures/nearfield_angle_and_chord_falsifier.png)
- BPE 专项报告：[/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/bpe_neutron_boundary_20260813/REPORT.md](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/bpe_neutron_boundary_20260813/REPORT.md)
- BPE spectrum/Cu fold 图：[/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/bpe_neutron_boundary_20260813/outputs/bpe_boundary_spectrum_cu_fold.png](/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/bpe_neutron_boundary_20260813/outputs/bpe_boundary_spectrum_cu_fold.png)
- 最终机器判决：[/home/ubuntu/.codex/worktrees/6f6c/TES_511_Balloon/engineering/s3d_o8_loop_engineering_20260814/thermal_cu_rethink_20260814/data/final_decision.json](/home/ubuntu/.codex/worktrees/6f6c/TES_511_Balloon/engineering/s3d_o8_loop_engineering_20260814/thermal_cu_rethink_20260814/data/final_decision.json)

