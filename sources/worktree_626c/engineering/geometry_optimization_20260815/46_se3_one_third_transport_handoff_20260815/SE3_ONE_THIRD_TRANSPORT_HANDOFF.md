# SE3 约 1/3 统计量输运与 S3d-O8 对比交接

状态：`方案已按用户澄清的拆分规则修正；尚未启动物理输运；当前资源可做有余量监控的 Plan 1`

这是新 session 的唯一执行入口。先完整读完本文件，再实施；不要先运行仓库里历史 fix5、旧 Step05 或旧 compact campaign。

## 0. 新 session 的第一步

本任务由用户明确开启，独立于仓库 `AGENTS.md` 的 fix5 simulation-closure 主线。目标是用已经冻结的 SE3 几何完成一个可审计的统计筛查：

1. 用 corrected-keV 八粒子族源，分别做 prompt/instant 与 activation/buildup；
2. 从 SE3 自己的 buildup 结果建立 day-15 inventory 和 exact-position delayed sources；
3. 做八族 delayed transport；
4. 用同一个全包络 focused-ray bank 成对跑 S3d-O8 与 SE3 信号；
5. 对 prompt、delayed、signal 使用同一响应和选择；
6. 做同一 20 d、81 节点 mission fold，给出中心值和保守代理的最小可分辨通量；
7. 与冻结的 S3d-O8 权威作同口径比较。

不要重新设计 SE3，不要覆盖 S3d-O8/M05/fix5 权威，不要把筛查结果称为 publication-level/full-stat closure。

启动前只做以下资源检查，不做全盘或大型 SIM 的重复哈希：

```bash
free -h
df -h /home/ubuntu
nproc
```

资源门 `R0`：修正后的全链 rich-SIM 点估约 **20.18 GB**。开跑前要求承载 run root 的文件系统至少有 **30 GB 可用空间**，且调度器按实际已生成 bytes 动态预测，始终保留至少 **8 GiB**。本交接复核时 `/home/ubuntu` 约有 **33.16 GB** 可用，能够进入 Plan 1，但余量不宽；任一时刻若预测完成后低于 8 GiB，立即停止发新任务并保留现有结果。

## 1. 已冻结的几何与基线

### SE3

- 唯一 setup：`/home/ubuntu/.codex/worktrees/626c/TES_511_Balloon/engineering/geometry_optimization_20260815/44_geoopt_se3_minimal_20260815/geometry/DEMO2_DR_v3p5_SE3.geo.setup`
- 几何说明：`/home/ubuntu/.codex/worktrees/626c/TES_511_Balloon/engineering/geometry_optimization_20260815/44_geoopt_se3_minimal_20260815/README.md`
- 状态：几何/load/overlap/navigator/mass/visual 均已 PASS，physics 仍 UNKNOWN。
- 五个冷盘每盘 48 个等面积孔，共 240 个 Vacuum placements；20 mm BPE 只开 focused port；10 mm plastic scintillator 完整不开孔。
- `InstrumentFrame.Rotation 0 45 0` 保持不变；world `+Z` 是 sky/up，入射 focused photons 沿 `+x'`。

所有 SE3 background/delayed/signal source 的 `Geometry` 行及 SIM header 都必须指向上面的 SE3 setup；唯一例外是 paired full-envelope S3d control，它必须指向下列 S3d setup。不要改名为 MASS511，不要倒置 45° 方向。

### S3d-O8 比较权威

- 冻结统计包：`/home/ubuntu/.codex/worktrees/626c/TES_511_Balloon/engineering/geometry_optimization_20260815/45_s3d_o8_particle_statistics_20260815`
- 当前 corrected M05 链：`/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813`
- 当前 source contract：`/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/data/source_contract_manifest.json`
- S3d setup：`/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`

不得混入旧 package-43 Step05 prompt 数字、旧 frozen pixel/L3 diagnostic、旧 neutron-only delayed campaign 或旧 fix5 论文数字。

## 2. 项目流程的简明复习

论文流程的物理含义是：

```text
冻结质量模型
  ├─ corrected atmospheric sources ─ prompt transport ───────────────┐
  └─ corrected atmospheric sources ─ buildup/RP ─ day-15 inventory  │
                                      └─ exact-position decays ─ delayed transport

Laue optics ─ full-envelope focused replay ──────────────────────────┤
                                                                     ↓
                       common detector response and selection
                                                                     ↓
                     81-node / 20-day fold → S, B, Z, F3
```

边界必须记清：

- geometry 只定义质量、材料和坐标，不产生 rate；
- instant 给 direct prompt background；
- buildup 给 radionuclide production histories，不等于 delayed detector cps；
- day-15 inventory 经 production-position sampling 后，才成为 delayed source；
- signal 是独立 focused gamma，不是第九个 atmospheric family，也不能给 broadband gamma 再叠加 mono-511；
- prompt、delayed、signal 必须通过同一能量响应、veto、Step05；
- mission fold 才把 selected rates 变为 20 d counts、显著性和通量阈值。

论文流程图只用于复习流程，不采用其中历史数值：

- `/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/core_md/balloon511_ea_latex_drafts/paper_source_figure_table/fig_simulation_workflow_corrected_zh_20260810.png`
- `/home/ubuntu/.codex/worktrees/626c/TES_511_Balloon/core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.tex` 的 `Simulation workflow` 小节。

当前 M05 的正式后处理顺序是：`00 input audit → 01 prompt → 02 activation → 03 delayed → 04 common response → 05 matched comparison → 06 mission`。SE3 复用算法和 schema，但必须做 candidate-own adapters，不能直接执行原脚本的默认输出。

## 3. Plan 1 的统计合同

“S3d-O8 的约 1/3”定义为：对每一个 `mode × family` 单元使用

```text
N_target = ceil(N_S3d-O8 / 3)
```

用户对“不要拆太小”的准确含义是：先确定上面的整族目标；若 `N_target ≤ 100000`，整族只跑一个任务，即使该任务少于 100k；只有 `N_target > 100000` 才允许拆分，并要求每个子任务都不小于 100k。不得把 100k 错当成每族最低统计量。这样 instant+buildup 总量是旧 S3d-O8 的约 1/3，而不是此前误读后的 47.25%。

### 3.1 Instant 与 buildup：21 个 Cosima jobs

| family | S3d instant | SE3 instant jobs | S3d buildup | SE3 buildup jobs |
|---|---:|---|---:|---|
| p | 25,448 | `8483` | 25,448 | `8483` |
| n | 232,991 | `77664` | 232,991 | `77664` |
| alpha | 5,958 | `1986` | 4,343 | `1448` |
| gamma | 3,207,738 | `267312 + 267312 + 267311 + 267311 = 1069246` | 2,356,499 | `261834 + 261833 + 261833 = 785500` |
| eminus | 295,341 | `98447` | 295,341 | `98447` |
| eplus | 60,184 | `20062` | 60,184 | `20062` |
| muminus | 10,443 | `3481` | 67,690 | `22564` |
| muplus | 3,972 | `1324` | 3,972 | `1324` |
| **合计** | **3,842,075** | **1,280,693 / 11 jobs** | **3,046,468** | **1,015,492 / 10 jobs** |

Gamma 只拆 4+3 个中等任务，用来限制失败后的重算损失；不得再拆成历史 campaign 那样的大量小 shard。其他单元各一个 job。

### 3.2 Delayed：8 个 Cosima jobs

SE3 自己的 day-15 transported-ground inventory 建成后，每族一个 source、一个 job、`83334` triggers；总计 `666672` triggers / 8 jobs，略高于 S3d 每族 250k 的精确 1/3，且不再拆分。

若某族经正确 buildup 后没有可输运 ground-state activity，保留显式 zero-source row，不伪造 decay source，也不借用 S3d inventory。该分支用有限 upper limit 表示。

### 3.3 Focused signal：保留真实 37,194-ray bank，做两个成对 Cosima jobs

旧 S3d signal 是 `37194 → 27855` 的 **post-Be-window** replay。37194 本身低于 100k，所以按用户澄清无需扩大，也禁止循环、重复或 bootstrap。问题只在注入面看不到 BPE/plastic，因此必须用同一真实 ray bank构造 full-envelope paired replay。

Plan 1 的信号步骤：

1. 读取冻结的 37,194-row、511 keV EventList，不改变 ray ID、能量、方向或权重。
2. 按各自方向把每条 ray 从 post-Be 平面确定性反向传播到 `-x'` 一侧、刚好位于外层 BPE 之外的共同注入面。
3. 用 navigator 抽查注入面：ray 尚未进入外壳；S3d 首先面对完整 BPE，SE3 首先面对 focused BPE port；两者仍穿过完整 plastic。
4. 同一 37,194-ray bank、同一行序和预注册 transport seed，分别跑 1 个 S3d-O8 control 和 1 个 SE3 job。按 ray ID 输出 paired selected/failure 分类。

每支 full-envelope signal 的归一化固定为

```text
Aeff_selected = 20.08476 cm^2 × N_selected / 37194
```

Clopper-Pearson acceptance 区间同样乘 `20.08476 cm²`。同时记录每条 ray 的 first-interaction material、BPE/plastic/BGO deposit 和最终 W2/Step05 状态，使 throughput 差异能定位到物理层，而不是只剩一个总 acceptance 数。

Optics 入口：

- 冻结 EventList：`/home/ubuntu/TES_511_Balloon/stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/eventlists/Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat`
- bridge：`/home/ubuntu/TES_511_Balloon/stepwise_maintenance/step09_optics_bridge/code/build_step09_optics_bridge.py`
- Cosima source 模板逻辑：`/home/ubuntu/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/code/prepare_o8_signal_replay.py`

本方案不重跑 optics。正常总任务数为 `21 prompt/buildup + 8 delayed + 2 signal = 31`。相比 S3d 的 488 个 instant/buildup jobs，任务数已大幅压缩。

## 4. Source 与 transport 实施合同

八个 corrected base cards：

`/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/config/source_cards/s3d_o8/Background_{p,n,alpha,gamma,eminus,eplus,muminus,muplus}_fullsphere20.source`

每张 package-local source 只允许精确修改：

- `Geometry` → SE3 setup；
- run name、output prefix、isotope prefix；
- event count 和唯一 seed；
- instant 删除 `DecayMode ActivationBuildUp`；buildup 保留它。

必须保持：20 equal-mu full-sphere bins、R=60 cm、corrected total-kinetic-keV spectra、原 flux、`QGSP_BIC_HP + LivermorePol`、`StoreSimulationInfo all`、`StoreIsotopes true`。Alpha 仍是 `MeV/nucleon × 4 × 1000` 转 total keV；gamma 是 `unit_only_total_gamma` broadband，禁止 additive mono-511。

复用精确 patch 逻辑，不直接运行历史 campaign：

- `/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_16h_90gb_campaign_batch0006_20260812/code/validate_m05_campaign_batch0006.py::patch_source_exact`
- runner/scheduler 只作参考：`/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_16h_90gb_campaign_batch0006_20260812/code/run_m05_16h_campaign_batch0006.py`

新 session 应在 fresh adapter package 中实现：

```text
analysis_inputs.json
data/job_plan.csv
data/seed_registry.csv
code/build_se3_sources.py
code/run_se3_plan1.py
code/validate_se3_receipts.py
outputs/00_input_audit ... outputs/06_mission
```

run root 通过 campaign-specific 变量传入；不要把 `$HOME` 或仓库根当临时清理目标。每个 job 使用独立、不可覆盖的 attempt 目录。

实际命令核心是：

```bash
source /home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh
/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima -s <seed> <patched.source>
```

每个 job 的 PASS receipt 至少记录：`family/mode/events/seed/source path/setup path/start/end/rc/SIM path/SIM bytes/generated events/TT/RP count/terminal marker`。验证 source 和 SIM header、generated count、正 TT、buildup 的 zero-RP TT 保留。只对小型 source/plan/receipt 做一次 provenance digest；不要在每个 stage 重开或重哈希几十 GB 的 `.sim.gz`。

Partial output 隔离，不计入统计；retry 使用同一 source、seed、event count，最多两次。已有 PASS receipt 的 job 断点续跑时跳过。

## 5. 多进程与容量调度

本机 24 CPU；根据用户的既有运行经验，本轮 CPU 预算为 6–8 个单核 Cosima workers，但先做一个计入正式统计的单任务资源金丝雀：

- 先单独运行第一个 `gamma instant 267312`；它本身就是 production canary，PASS 后计入结果，不另跑无意义的小 smoke；
- canary 完成并记录 peak RSS、wall time、bytes/event 后，设置 `cpu_budget=6`；资源稳定时可升到 8，不超过 8；
- scheduler 不是盲目的 `max_workers=8`：按 canary 和历史 family RSS 做 admission，使已运行进程的 RSS 预算加新任务预算不超过当时 `MemAvailable` 的安全部分；轻任务可占满 6–8 核，重任务阶段可暂时低于 6；
- postprocessing compact catalogs 使用 6 workers，内存稳定时可用 8；
- 调度器每次 launch 前检查 `MemAvailable`、当前 worker 数和 projected output；预测最终余量小于 8 GiB 时停止发新任务；
- Cosima 只能 job 级续跑：partial 隔离，失败用同 seed 整 job 重跑，不能把 partial 计入结果。

按当前 S3d rich-SIM 的实际压缩 bytes/event，Plan 1 背景输运估算如下（GB 为十进制近似）：

| family | instant GB | buildup GB |
|---|---:|---:|
| p | 1.769 | 1.661 |
| n | 1.724 | 1.533 |
| alpha | 1.186 | 0.787 |
| gamma | 3.121 | 2.414 |
| eminus | 1.034 | 1.025 |
| eplus | 1.430 | 1.239 |
| muminus | 0.045 | 0.290 |
| muplus | 0.017 | 0.016 |
| **合计** | **10.326** | **8.966** |

占用复核：当前 corrected M05 实际选中的 488 个 S3d-O8 prompt+buildup `.sim.gz` 经逐文件 `stat` 合计 **57.873 GB**；selected delayed 为 **2.516 GB**，selected signal 为 **24.18 MB**，三者合计约 **60.413 GB**。整个 particle-source 历史根经 `du` 约 **87.95 GiB**，包含另一几何、旧 attempt、smoke、recovery 和 partial。

修正后的 Plan 1 prompt+buildup 点估为 `19.291 GB`；八族 delayed `8 × 83334` 约 `0.839 GB`；两支 37,194-ray signal 合计约 `0.048 GB`。全链 raw 点估约 **20.18 GB**，不含小型 logs/DAT/catalog 和失败 partial。这个估算按当前 S3d family×mode 压缩 bytes/event 线性规划；SE3 几何会略改事件记录量，所以每完成一波就用真实 bytes/event 更新余量门。

此前 `184.711 GB` 的数字来自错误地把 100k 当成每个 family×mode 的最低统计量；该解释会把 alpha 两模式错误放大到 200k events。用户已明确否定该解释，旧 185/255 GB 规划不再适用。

资源估计依据：`/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/small_batch_resource_optimization_review_20260812/family_resource.csv` 与当前 S3d selected receipts。

不要启用 `/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_complete_compact_smoke_20260812` 的历史 compact transport 路径；它明确是 withdrawn/not transport-authorized。若未来要用流式 compact 输出，必须另做物理语义等价验证并获得明确批准，不能在 Plan 1 中自行替换 rich-SIM 合同。

## 6. 推荐执行波次

1. `W0 — read-only/preparation`：确认 R0；生成 job plan、seed registry、source cards 和 source-level audit；不发 transport。
2. `W1 — production canary`：单独完成第一个 gamma instant 子任务并审计 RSS、I/O、bytes/event；该任务计入正式统计。
3. `W2 — remaining prompt/buildup`：canary PASS 后按 6 核 CPU 预算持续调度，资源稳定时最多 8 核；轻任务可占满预算，重任务按 RSS admission 降低并发，完成剩余 20 个任务。
4. `W3 — activation/source`：所有 buildup PASS 后，构建 corrected buildup catalog、day-15 inventory、exact-position sources；检查 zero-RP denominator、state holdout、source-mixture closure。
5. `W4 — delayed`：八族各 83,334 triggers，用 6–8 workers；完成后做 raw semantic catalogs。
6. `W5 — signal`：对冻结 37,194-ray bank 做 full-envelope back-projection audit，再成对运行 S3d/SE3 signal。
7. `W6 — postprocess`：按 00→06 顺序执行 common response、比较、mission/F3；最后生成一份 S3d/SE3 汇总。

W3 必须等所有 buildup PASS；W4 必须等 SE3 自有 inventory/source 完成。W5 可与 W1/W2 并行准备，但不得改动冻结 ray 内容。

## 7. Activation 与 delayed 的必要步骤

可复用算法入口：

- buildup catalog：`/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_paper_closure_topup_batch0007_3h_20260813/delayed_phase02/code/build_corrected_buildup_catalog.py`
- state-aware exact-position source：`/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_paper_closure_topup_batch0007_3h_20260813/delayed_phase02/code/prepare_state_aware_delayed_phase02.py`
- M05 stage template：`/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/code/build_activation_stage.py`
- delayed transport template：`/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/code/run_delayed_remaining9.py`
- delayed analysis template：`/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/code/analyze_delayed_stage.py`

归一化不可混用：

- prompt，每个 `geometry × family`：`w = 1 / sum(TT_f)`，`rate = N_selected × w`；TT 不跨 family 池化，也不用 requested histories 作分母；
- activation，每个 `geometry × family × volume × ZA × state`：`q = sum(RP) / sum(TT_f)`，zero-RP DAT 的 TT 必须进分母；
- 常照射 day 15：`A15 = q × [1 - exp(-ln(2) × 15 d / t_half)]`；
- delayed，每族：`w = transported_ground_A15 / N_triggers`；不是 buildup TT；
- 非零激发态和未解析 NUBASE rows 作为 holdout，fail closed；
- 50k production-position blocks 若按 stride-5 取 10k，保留 block flux ×5 并闭合总 Bq；position-mixture uncertainty 与 MC counting error 分开。

## 8. 后处理适配：不要直接运行原默认脚本

模板目录：`/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/code`

必须建立 write-once SE3 adapters，因为当前脚本硬编码 Mass/S3d 名称、路径和 post-Be signal。一个已知静默错误是 `run_prompt_analysis.py::evaluate_event` 用 `geometry != "S3d_O8"` 决定是否启用 plastic veto；若只是把名称改为 `SE3`，会错误地跳过 plastic veto。改为显式策略表，并让 SE3 使用与 S3d-O8 相同的 6 个 active-veto volumes；plastic 几何本来就保持不变。

后处理顺序和目标输出：

1. `00_input_audit`：source contract、geometry/header、8 families、唯一 SIM、positive TT、完成事件数、seed/receipt；
2. `01_prompt`：input manifest、cell coverage、cutflow、occupancy、summary；
3. `02_activation`：activation cells、day15 inventory、delayed source index、state/holdout summary；
4. `03_delayed`：input manifest、cell coverage、source-mix QA、raw compact catalog、summary；
5. `04_common_response`：prompt/delayed/full-envelope signal 的统一 response/cutflow/lineage/occupancy/signal acceptance；
6. `05_matched_comparison`：SE3 与冻结 S3d-O8 的 family/parent/material/volume/day15 表；
7. `06_mission`：family-parent activity by time、81-node timeline、mission comparison、F3 summary。

模板命令形式：

```bash
python3 -B <SE3_ADAPTER>/code/check_inputs.py --config <SE3_ADAPTER>/analysis_inputs.json --write
python3 -B <SE3_ADAPTER>/code/run_prompt_analysis.py --config <SE3_ADAPTER>/analysis_inputs.json --output <fresh-01> --workers 6
python3 -B <SE3_ADAPTER>/code/build_activation_stage.py --output <fresh-02>
python3 -B <SE3_ADAPTER>/code/analyze_delayed_stage.py --output <fresh-03> --workers 6
python3 -B <SE3_ADAPTER>/code/build_common_response.py --output <fresh-04> --workers 6
python3 -B <SE3_ADAPTER>/code/build_matched_comparison.py
python3 -B <SE3_ADAPTER>/code/build_mission_stage.py
```

这是接口目标，不是让新 session 直接运行 M05 原文件；现有 matched/mission 甚至没有路径 CLI，必须先参数化并在 fresh output 上执行。已有 M05 outputs 永不覆盖。

冻结分析条件：

- measured response FWHM `0.42 keV`；
- measured-pixel threshold `0.3 keV`；
- active veto threshold `50 keV`；
- W2 = `510.58–511.42 keV`；
- retained Step05 side-Compton/FoV reject policy；
- gamma 仍为 corrected broadband、无额外 mono-511。

同一 81 节点 family-scale 和 atmosphere authority 可直接读取，不需要重跑 PARMA：

- `/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/data/parma_energy_integrated_family_scales_81bins.csv`
- `/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/fullchain/step06/atmosphere_transmission_511_by_time.csv`

## 9. 统计量、误差与最小可分辨通量

Weighted background：

```text
rate = sum(w_i)
sigma_MC = sqrt(sum(w_i^2))
Neff = sum(w_i)^2 / sum(w_i^2)
```

零 survivor 绝不能写成物理零。与冻结 S3d family 表比较时使用双侧 Garwood 95%；`N=0` 上界为 `3.688879 × w`。若引用一侧 95% 晋级门，则 `N=0` 上界为 `2.995732 × w`，必须明确 sidedness。Fixed-N signal 用 Clopper-Pearson；同 ray bank 的 S3d/SE3 另给 paired ratio 和其下界。

Mission 沿用 M05 的 20 d、81 节点、zero day-0 inventory、family-scalar fold。参考通量：

```text
F_ref = 1.0e-4 ph cm^-2 s^-1 at top of atmosphere
```

中心值：

```text
Z20 = S20 / sqrt(B20)
F3  = F_ref * 3 / Z20
    = F_ref * 3 * sqrt(B20) / S20
```

保守 componentwise endpoint proxy：

```text
Z20_proxy = S20_lower95 / sqrt(B20_upper95_proxy)
F3_proxy  = F_ref * 3 / Z20_proxy
```

其中 `B20_upper95_proxy` 由逐族 prompt Garwood upper 与 delayed parent/activity-mixture upper 构成，`S20_lower95` 来自 signal CP lower。它不是联合 95% coverage，必须写作 proxy。

若检查 `F3 ≤ 3e-5` 目标，在 `F_ref=1e-4` 下等价于 `Z20 ≥ 10`：

```text
B20_max = (S20 / 10)^2
```

公平几何比较使用同一 full-envelope signal bank：

```text
F3_SE3 / F3_S3d = [sqrt(B_SE3)/S_SE3] / [sqrt(B_S3d)/S_S3d]
```

静态 `Aeff/sqrt(background_cps)` 只作 detector-plane diagnostic，不能代替 mission F3。

## 10. 必须保留的 S3d-O8 对照数字

冻结 S3d-O8 当前值：

| quantity | S3d-O8 |
|---|---:|
| day-15 prompt W2 | `0.0338429281309 ± 0.0239305639766 cps`；仅 2 个 survivor |
| day-15 delayed W2 | `0.0544797522273 ± 0.0101598793116 cps`；420 rows，`Neff=28.7537` |
| day-15 total | `0.0883226803582 cps` |
| 20 d prompt counts | `55398.9794340` |
| 20 d delayed counts | `88804.8626519` |
| `B20` | `144203.8420859` |
| post-Be `S20` | `1645.3877531` |
| post-Be `Z20` | `4.3329117594` |
| post-Be `F3` | `6.9237505092e-5 ph cm^-2 s^-1` |
| post-Be proxy `Z20` | `1.4633741512` |
| post-Be proxy `F3` | `2.0500567114e-4 ph cm^-2 s^-1` |

这里的 `S20/Z/F3` 是旧 **post-Be conditional** 信号范围。最终报告必须同时分开列：

1. 上表的 published/current post-Be reference，仅用于 continuity；
2. 新 37,194-ray full-envelope S3d control；
3. 新 37,194-ray full-envelope SE3 candidate。

只有第 2 与第 3 能用于 BPE port/plastic 的公平几何比值。用 full-envelope S3d 新 Aeff 和冻结 S3d background 重新做 S3d mission control，再与 SE3 mission 比；禁止把 SE3 full-envelope signal 直接除以上表 post-Be signal。

## 11. 最终比较表与完成门

最终至少输出：

```text
data/se3_plan1_job_plan.csv
data/se3_plan1_seed_registry.csv
outputs/00_input_audit/...
outputs/01_prompt/prompt_cutflow.csv
outputs/02_activation/{activation_cells.csv,day15_inventory.csv,delayed_source_index.csv}
outputs/03_delayed/{delayed_input_manifest.csv,delayed_source_mix.csv,summary.json}
outputs/04_common_response/{common_cutflow.csv,selected_background_w2_lineage.csv,signal_acceptance_effective_area.csv}
outputs/05_matched_comparison/s3d_o8_vs_se3_day15.csv
outputs/06_mission/{mission_timeline.csv,s3d_o8_vs_se3_mission.csv,summary.json}
audit/se3_plan1_transport_receipts.json
audit/se3_plan1_statistics_validation.json
REPORT.md
```

S3d/SE3 主表至少含：setup/header identity；family/mode/jobs/histories/sumTT/seeds；prompt `N/rate/sigma/Garwood`；activation `RP/TT/q/volume/material/ZA/state/A15/holdout`；delayed `blocks/triggers/mix-TV/N/rate/sumw2/Neff/UL`；response/W2/veto/Step05；signal injection plane/trials/selected/CP/Aeff/paired ratio；day15 P/D/B；20 d family P/D、S/B/Z/F3 central+proxy；known exclusions。

完成门：

- `R0`：开跑前空间 ≥30 GB，运行中预测 reserve ≥8 GiB；
- `G1`：计划内所有 job 都有 PASS receipt；整族目标≤100k时只跑一个任务，整族目标>100k时每个拆分子任务≥100k；
- `G2`：所有 SE3 source/SIM header 指向唯一 SE3 setup，family/mode/seed/event count 与 plan 一致；
- `G3`：prompt TT、activation RP/TT、delayed A15/triggers 三种归一化分别闭合；
- `G4`：SE3 plastic veto 显式启用；三流共用冻结 response/W2/veto/Step05；
- `G5`：冻结 37,194-ray bank 无重复/重采样；S3d/SE3 使用同一 bank、同一 injection plane，可按 ray ID 配对；
- `G6`：同时报告 F3 central 和 proxy，并与 S3d full-envelope control 比；
- `G7`：零/低计数保留有限区间；不以 central delta-method ratio 作 promotion；
- `G8`：输出标为 `PLAN1_APPROX_ONE_THIRD_PHYSICS_SCREEN`，不自动晋级几何、不声称 full-stat。

若资源门、full-envelope signal bank、plastic veto adapter 或任一归一化门未完成，最终状态必须是 `BLOCKED/NO-GO`，不能退回使用旧 post-Be signal 或旧 S3d inventory 填补 SE3。

## 12. 已知 scenario 边界

最终报告继续保留 M05 的边界：81 节点为 synthetic trajectory；day 0 inventory=0，因此无 pre-flight/ground activation；family-scalar fold 固定族内能谱、角分布、response、activation yield；PARMA driver `W=114.6` 与 source contract `W=118.3` 的已知差异只用于相对 family ratio；source-position mixture、activation physics/yield、optics systematic、source visibility/duty 和大气系统学未形成联合误差。

## 13. 给新 session 的直接提示词

```text
请立即执行 SE3 Plan 1，不要只回复“已读”。唯一入口：
/home/ubuntu/.codex/worktrees/626c/TES_511_Balloon/engineering/geometry_optimization_20260815/46_se3_one_third_transport_handoff_20260815/SE3_ONE_THIRD_TRANSPORT_HANDOFF.md

先完整阅读交接和其中列出的 M05 README/论文流程图，简明复述你理解的 prompt→activation→delayed→common-response→mission/F3 链，然后直接检查磁盘/内存并建立 fresh adapter package。不要做大型 SIM 的额外哈希扫描。严格执行“每族/模式先取S3d-O8的ceil(1/3)；目标≤100k不拆，目标>100k才拆且每子任务≥100k”。先单独完成一个计入统计的gamma production canary；审计RSS/bytes后以6核为CPU预算、资源稳定时最多8核，重任务仍按RSS admission降低并发。SE3 自有 activation/delayed；冻结37194-ray bank的full-envelope paired signal；S3d-O8 同口径比较。全链raw点估约20.18GB，开跑前空间门30GB、动态reserve门8GiB。持续推进到完成或真实阻塞，并在最终回复给出绝对路径、job receipts、后处理结果、F3 central/proxy 与 S3d 比值。
```
