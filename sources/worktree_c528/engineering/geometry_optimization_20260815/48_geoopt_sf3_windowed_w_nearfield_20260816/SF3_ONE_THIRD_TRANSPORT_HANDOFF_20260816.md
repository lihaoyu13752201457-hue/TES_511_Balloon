# SF3 约 1/3 统计输运、SE3 对照与条件式 full-stat 补量交接

状态：`SF3 几何已生成并通过静态/mesh/Geant4 overlap/native navigator；物理输运尚未启动`

这是新 session 的唯一执行入口。先完整读完本文件和列出的项目权威，再开始；不要只回复“已读”，不要在本 geometry package 内直接写 transport outputs，也不要重跑 SE3/S3d。

## 0. 任务目标

SF3 的物理问题只有一个：在忠实保留 SE3 的前提下，新增一个近 TES 的开窗被动 W 壳，重新计算大气宇宙线环境中的 prompt、activation、actual-position delayed、主动 veto、Step05、81-node/20-day mission fold，判断

```text
R_F3 = F3_SF3 / F3_SE3
```

是否 `<= 0.75`。若且仅若一阶段中央值达到该门，继续把 SF3 prompt/buildup 统计补到冻结 S3d-O8 full-stat 量级，并按本交接的 delayed 重建门处理。达到门只授权补统计，不等于几何晋级或 publication-level closure。

## 1. 新 session 先复习项目

按顺序完整阅读：

1. 本文件；
2. SF3 说明：`/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/geometry_optimization_20260815/48_geoopt_sf3_windowed_w_nearfield_20260816/README.md`；
3. 原 SE3 Plan-1 交接：`/home/ubuntu/.codex/worktrees/626c/TES_511_Balloon/engineering/geometry_optimization_20260815/46_se3_one_third_transport_handoff_20260815/SE3_ONE_THIRD_TRANSPORT_HANDOFF.md`；
4. 原 SE3 geometry：`/home/ubuntu/.codex/worktrees/626c/TES_511_Balloon/engineering/geometry_optimization_20260815/44_geoopt_se3_minimal_20260815/README.md`；
5. 已完成 SE3 Plan-1：`/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/geometry_optimization_20260815/47_se3_plan1_transport_20260815/outputs/07_final_audit/FINAL_REPORT.md` 与同目录 `final_audit.json`；
6. corrected-keV 项目：`/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/README.md`、`data/source_contract_manifest.json`、`data/static_validation.json`；
7. M05 后处理：`/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/README.md`；
8. 论文流程图：`/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/core_md/balloon511_ea_latex_drafts/paper_source_figure_table/fig_simulation_workflow_corrected_zh_20260810.png`，以及 `/home/ubuntu/.codex/worktrees/626c/TES_511_Balloon/core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.tex` 的 `Simulation workflow` 小节。

开始工作前，用一段简短文字复述以下链，而后直接行动：

```text
corrected atmospheric sources
  ├─ instant → prompt detector background ───────────────────────────┐
  └─ buildup/RP → SF3 自有 day-15 inventory                         │
                   → actual production-position source              │
                   → delayed transport ──────────────────────────────┤
                                                                     │
frozen 37,194-ray full-envelope optics bank → SF3 signal ────────────┤
                                                                     ↓
                  common measured response + BGO/plastic veto
                  + W2 + retained Step05 side-Compton/FoV
                                                                     ↓
                81-node / 20-day fold → S20, B20, Z20, F3
                                                                     ↓
                      frozen SE3 vs fresh SF3
```

geometry 只给材料/质量/坐标；buildup/RP 不是 delayed cps；SF3 必须建立自己的 inventory 和真实生产位置源；signal 不是第九个大气粒子族；三流必须用同一响应和选择；mission fold 后才能比较 F3。

## 2. 冻结 SF3 几何

唯一 setup：

`/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/geometry_optimization_20260815/48_geoopt_sf3_windowed_w_nearfield_20260816/geometry/DEMO2_DR_v3p5_SF3.geo.setup`

SF3 是 hash-pinned SE3 的严格 add-only child：去掉唯一 `BEGIN/END SF3` 块并把 setup identity 还原后，必须逐字节重构 SE3。`intro`、`materials`、`.det` 与 SE3 byte-identical；物理 delta 只有三个 `InstrumentFrame` daughters：

| volume | x-prime extent cm | radial/aperture contract |
|---|---:|---|
| `SF3_W_NearField_FrontWindowPlate_2p9mm` | `[-4.6475,-4.3575]` | outer `4.495`; square half-window `1.900` |
| `SF3_W_NearField_SideSleeve_2p9mm` | `[-4.3575,4.305]` | `r=4.205..4.495` |
| `SF3_W_NearField_RearColdFingerAnnulus_2p9mm` | `[4.305,4.595]` | `r=1.85..4.495` |

每个体积：`Material W`、`Position 0 0 -5.2`、`Rotation 0 90 0`、`Mother InstrumentFrame`。W 总体积 `98.17138542336635 cm3`、质量 `1.8947077386709705 kg`。

为什么选 W 而不是 Pb：W 已在冻结 materials 中以 `19.3 g cm-3` 定义，Pb 不存在；选 W 可保持 materials/intro/det 原样，只新增物理壳。这个选择绝不表示 W 没有 pair production 或 activation；它们正是新全链必须测的量。

不要把厚度改成 3.0 mm：同心 3.0 mm 版本与已有 Cu 50 mK bottom cap 重叠约 0.5 mm。2.9 mm 版本在最近继承结构之间保留 0.005 cm。

### 2.1 45 度光轴不可改

`InstrumentFrame.Rotation 0 45 0` 保持 exact-once。世界 `+Z` 是 sky/up；sky-facing optical axis 是 `-xprime = (-0.7071,0,+0.7071)`，即 45 度斜向上；来自天空的 focused photons 沿 `+xprime` 向仪器内部传播。W 体积的 `0 90 0` 只把 PCON 局部轴对准 x-prime；不得再给它们施加一次全局 45 度。

### 2.2 几何硬门

开 transport 前重新运行只读检查：

```bash
python3 -B /home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/geometry_optimization_20260815/48_geoopt_sf3_windowed_w_nearfield_20260816/code/build_sf3_geometry.py --check
python3 -B /home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/geometry_optimization_20260815/48_geoopt_sf3_windowed_w_nearfield_20260816/code/validate_sf3_mesh_clearance.py --check
```

并读取、核对以下已生成 authority 都为 PASS 且 hash 与当前 setup 相符：

- `audit/sf3_geometry_validation.json`；
- `audit/sf3_mesh_clearance_prefilter.json`；
- `audit/sf3_overlap_validation.json`；
- `audit/sf3_native_navigation_audit.json`。

冻结 37,194 rays 必须保持：front window 最小净空 `0.5058448649 cm`、side 最小净空 `2.5284468615 cm`、rear aperture 最小净空 `0.1713803305 cm`；SE3/SF3 全路径各材料弦长逐 ray 相等；新增 W chord 为零；三条 W witness 各给 `0.29 cm`。

W 是 passive-only：不得加入 `.det`，不得加入 active-veto volume lists。`StoreIsotopes true` 会记录 passive W 的 activation；后处理 material/volume lineage 必须单列它。

## 3. Fresh adapter 与禁止项

在新 session 自己的 writable worktree 建立非覆盖包，例如：

```text
engineering/geometry_optimization_20260815/49_sf3_plan1_transport_20260816/
  analysis_inputs.json
  code/
  config/
  data/
  audit/
  outputs/00_input_audit ... outputs/07_final_audit
```

run root 使用 campaign-specific 新路径，例如：

```text
runs/geometry_optimization_20260816/sf3_plan1_one_third_transport_v1/
```

复用 `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/geometry_optimization_20260815/47_se3_plan1_transport_20260815/code/` 的 runner、receipt、dashboard、stage01–07 代码，但复制为 fresh SF3 adapters 并参数化；绝不修改或直接覆写 47 的 config、run root、receipts、outputs。

必须替换和审计：

- identity/setup/header：`SE3` → `SF3`，setup 指向唯一 SF3 entry；
- job/source/run/output names：`se3_*` → `sf3_*`；
- fresh unique seed registry；不复用 47 的 registered seeds；
- comparison geometry：frozen `SE3` versus fresh `SF3`；
- signal scope：fresh SF3 full-envelope + frozen SE3 full-envelope small-table authority；不要求 fresh SE3/S3d receipt；
- stage04 volume roles：六个原有 BGO/plastic active-veto volumes保持不变，三块 `SF3_W_*` 只能是 passive W；
- stage02/03：SF3 自有 W activation、inventory、position mixture 和 delayed sources；
- stage05/06：用 frozen SE3 small tables，重新计算 SF3 mission 并输出中央/代理比值；
- finalizer：只接受所有 effective SF3 receipts，不允许以 SE3 SIM 或 inventory 填空。

禁止：

- 重跑 SE3 或 S3d；
- 重开/重哈希大型历史 SIM；
- 使用旧 post-Be signal 作分母；
- 把 SE3 的 muplus zero-A15 状态复制到 SF3；
- 把 W deposit 当主动 veto；
- 给 corrected broadband gamma 叠加 mono-511；
- 任何包含 `cosima_spectra_dp_2602units` 的 legacy source；
- 在 48 geometry package 内写 transport outputs。

## 4. Source 合同与 Cosima cwd

八个 corrected base cards来自：

`/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/config/source_cards/s3d_o8/Background_{p,n,alpha,gamma,eminus,eplus,muminus,muplus}_fullsphere20.source`

使用 47 已闭合的 exact patch/builder 逻辑，生成 package-local cards。只允许有意修改 Geometry、run/source-scoped name、output/isotope prefix、event count、seed；instant 删除 activation buildup，buildup保留。20 equal-mu bins、R=60 cm、corrected total-kinetic-keV spectra、flux、`QGSP_BIC_HP + LivermorePol`、`StoreSimulationInfo all`、`StoreIsotopes true` 不变。

这些 base cards 的 20 个 Spectrum File 是 repo-relative；Cosima transport 的 cwd 必须是：

`/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon`

而 SF3 Geometry 和 output prefix 使用绝对路径。

每个 PASS receipt 至少绑定：geometry/family/mode/events/seed/source/setup/header/start/end/return code/SIM path and bytes/generated count/TT/RP count/terminal marker/peak RSS。partial 隔离，retry 同 seed、同 source、同 events，最多两次；已有 canonical PASS 跳过。

## 5. 一阶段统计合同：与 SE3 完全相同

权威小表：`data/sf3_plan1_statistics_contract.csv`。

先对每个 `mode × family` 取 `ceil(N_S3d/3)`。若单元目标 `<=100000`，只跑一个任务；只有目标 `>100000` 才拆，且每个 shard `>=100000`。

| family | instant jobs | buildup jobs | delayed registered target |
|---|---:|---:|---:|
| p | `8483` | `8483` | `83334` |
| n | `77664` | `77664` | `83334` |
| alpha | `1986` | `1448` | `83334` |
| gamma | `267312+267312+267311+267311` | `261834+261833+261833` | `83334` |
| eminus | `98447` | `98447` | `83334` |
| eplus | `20062` | `20062` | `83334` |
| muminus | `3481` | `22564` | `83334` |
| muplus | `1324` | `1324` | `83334` |
| total | `1,280,693 / 11 jobs` | `1,015,492 / 10 jobs` | 最多 `666,672 / 8 jobs` |

所有八个 delayed cells 都注册。某族只有在 SF3 自己的 transported-ground A15 精确为零时才 `SKIP_ZERO_A15`，保留 finite two-sided Garwood upper；不伪造 source/receipt。

signal：复用冻结、真实 `37,194`-row full-envelope EventList，注入面 `xprime=-30.0001 cm`，ray ID/行序/能量/方向/权重不变，不循环、不 bootstrap。只跑一个 fresh SF3 signal job，用 fresh seed。SE3 signal 从 47 的 stage04 小表读取；不重跑 SE3。

正常一阶段最多 `21 background + 8 delayed + 1 signal = 30` jobs；zero-A15 可动态减少 effective jobs。

## 6. 资源与自适应多核

启动前只做：

```bash
free -h
df -h <SF3 run filesystem>
nproc
```

不要做全盘或大型 SIM 的额外哈希。

一阶段门：

- launch 前可用磁盘至少 `30 GB`；
- 每次 admission 用实际 bytes/event 动态预测，完成后 reserve 始终 `>=8 GiB`；
- 单独先跑正式 `sf3_instant_gamma_shard0001 / 267312` canary；PASS 后计入统计；
- `cpu_budget=6`，自适应尽量维持至少 4 workers，稳定时到 6；
- `MemAvailable` launch floor `1.5 GiB`；
- `SwapFree` floor `8 GiB`；
- PSI memory `some avg10<10`、`full avg10<2`，连续换页阈值 `2048 pages/s`；
- slot 5/6 使用 live RSS empirical admission；任何 floor/thrash/disk gate失败就降并发，而不是硬凑核数；
- postprocess 用 6 workers，仍受内存门约束。

复用并改名 47 的 `watch_se3_plan1.py`，提供 2 秒刷新终端 dashboard：stage、receipt、active event/log progress、CPU、RSS、RAM floor、swap、磁盘投影、ETA。不要从 SIM size 推断 event progress，使用 Cosima log/event marker。

## 7. Activation 与 actual-position delayed

W3 必须等全部 buildup PASS。归一化不混用：

```text
prompt:     w = 1 / sum(TT_family)
activation: q(volume,ZA,state) = sum(RP) / sum(TT_family)
A15:        q × [1-exp(-ln2×15d/t_half)]
delayed:    w = transported_ground_A15 / N_triggers
```

zero-RP DAT 的 TT 进入分母；NUBASE ground-state/holdout fail-closed。按 47 的 M sampling：每个正族先保留 50,000 actual production-position blocks，再 stride-5 得到 10,000 transport source blocks，block flux ×5，original/transport total Bq 两次闭合。INIT `parts[15]` 是 transported daughter ZA，不强制等于 source parent ZA；母核 lineage 权威是 provenance-bound exact-position KD-tree unique match，mismatch只作诊断。

SF3 的 W 壳必须出现在 activation/day15/material/volume lineage 中；它不在 detector active-veto roles 中。

## 8. Common response、veto 与 mission

冻结选择：

- measured response FWHM `0.42 keV`；
- measured-pixel threshold `0.3 keV`；
- active BGO/plastic veto threshold `50 keV`；
- W2 `510.58–511.42 keV`；
- retained Step05 side-Compton/FoV reject policy；
- 同一 81-node family-scale、atmosphere transmission、20-day fold；
- zero day-0 inventory。

三块 W 不参与 active veto。必须另外报告：W-first-interaction、W pair/annihilation、W isotope production、W parent/volume delayed survivors；这用于 tradeoff 诊断，不改变 selection。

输出顺序：

```text
00_input_audit
01_prompt
02_activation
03_delayed
04_common_response
05_se3_vs_sf3_matched_comparison
06_mission
07_final_audit
```

mission 必须输出 `F3_SF3`, `F3_SE3`, `R_F3` central 和 componentwise endpoint proxy，另列 signal Aeff/CP、background prompt/delayed components、W-specific lineage。proxy 不是联合95% coverage。

## 9. 冻结 SE3 对照与 25% 门

只读冻结基线：

| quantity | SE3 Plan-1 |
|---|---:|
| prompt W2 central | `0 cps`（零 MC survivor，不是物理零） |
| delayed W2 | `0.06011336205846697 cps` |
| signal selected | `21657 / 37194` |
| Aeff | `11.69478 cm2` |
| S20 | `1279.2886580217926` |
| B20 | `98257.66904712601` |
| F3 central | `7.350822463201115e-05 ph cm-2 s-1` |
| F3 proxy | `4.4813103398753603e-04 ph cm-2 s-1` |

公平比值：

```text
R_F3 = sqrt(B20_SF3/B20_SE3) × (S20_SE3/S20_SF3)
```

用户指定的补统计触发条件：

```text
R_F3 <= 0.75
```

等价于：

```text
F3_SF3 <= 5.513116847400837e-05 ph cm-2 s-1
```

以 central 作为触发值；proxy、区间和零计数上界必须同时报告，但不要擅自把 proxy 变成额外触发门。触发前还必须满足 geometry/header/receipt/TT/RP/actual-position/veto/signal/mission 全部闭合，且改善不是错误使用 SE3 prompt=0 或旧 post-Be signal 得到。

若 `R_F3 > 0.75`，停止在一阶段，给出完整结果和不补量理由。若 `R_F3 <=0.75`，进入第10节；这仍不是自动几何 promotion。

## 10. 条件触发后的 S3d full-stat 补量

权威表：`data/sf3_fullstat_topup_contract.csv`。保留一阶段全部 canonical PASS receipts，用 fresh seeds 只跑 prompt/buildup 差额：

| family | instant increment | buildup increment |
|---|---:|---:|
| p | `16965` | `16965` |
| n | `155327` | `155327` |
| alpha | `3972` | `2895` |
| gamma | `4×267312 + 4×267311 = 2138492` | `261834 + 5×261833 = 1570999` |
| eminus | `196894` | `196894` |
| eplus | `40122` | `40122` |
| muminus | `6962` | `45126` |
| muplus | `2648` | `2648` |
| total | `2,561,382 / 15 jobs` | `2,030,976 / 13 jobs` |

增量 job 仍遵守：remaining target `<=100000` 不拆；`>100000` 只有在每个 shard 都 `>=100000` 时才拆。所有 top-up seeds 新注册。

### 10.1 Delayed 不能盲目追加

full buildup 会改变 isotope/volume/position mixture。默认、安全路径是：聚合 full buildup RP/TT，重新建 full-stat inventory 和 exact-position sources，然后对每个正族重新跑完整 `250000` delayed triggers；一阶段 `83334` 只保留为 screening authority。

只有实现并通过 source-support inclusion、importance reweight、original/transport Bq、mixture TV、ESS、lineage closure 后，才允许把旧 `83334` 与新 `166666` 合并。zero-source 族在 full buildup 后重新判定：仍 zero则 skip；变 positive则跑完整 `250000`。signal bank仍为37,194，不补量。

### 10.2 Full-stat 资源门

进入补量前重新根据 SF3 实测 bytes/event 和 RSS 做 admission；不要沿用固定30 GB：

```text
free_bytes >= projected_remaining_bytes × 1.02 + auxiliary_overhead + 8 GiB
```

若不满足就真实阻塞并报告，不删除/覆盖已完成的一阶段 authority。

## 11. 完成门与最终交付

- `G0`：四个 SF3 geometry authorities PASS；
- `G1`：计划、拆分和 history totals 精确闭合；
- `G2`：所有 SF3 source/SIM header 指向唯一 SF3 setup；
- `G3`：corrected-keV、20 bins、flux、physics/store settings无漂移；
- `G4`：prompt TT、activation RP/TT、delayed A15/triggers分母分离；
- `G5`：actual-position M sampling和parent lineage闭合；
- `G6`：W passive-only，六个 active-veto volumes与SE3一致；
- `G7`：37,194 bank不重复，full-envelope scope一致；
- `G8`：common response/W2/veto/Step05一致；
- `G9`：81-node mission中央/代理和SE3比值完整；
- `G10`：只有 central `R_F3<=0.75` 才进入full-stat补量；
- `G11`：所有输出 write-once，canonical receipts完整，不重开/重哈希大型SIM。

最终回复给出：fresh adapter和run root绝对路径、有效job receipts/统计量、SF3 W activation/delayed lineage、prompt/delayed/Aeff、S20/B20/Z20/F3 central+proxy、`F3_SF3/F3_SE3`、是否触发补量、若触发则full-stat receipts和重建后的结果。

## 12. 给新 session 的直接提示词

```text
请立即执行 SF3 Plan 1，不要只回复“已读”。唯一入口：
/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/geometry_optimization_20260815/48_geoopt_sf3_windowed_w_nearfield_20260816/SF3_ONE_THIRD_TRANSPORT_HANDOFF_20260816.md

先完整阅读交接列出的 SE3、M05 README 与论文流程图，简明复述 prompt→activation→actual-position delayed→common response/veto→81-node mission/F3 链，然后直接检查 SF3 四个几何 authority、磁盘/内存并建立 fresh SF3 adapter/run package。不要重跑SE3/S3d，不要扫描或哈希大型历史SIM。SF3统计严格与SE3 Plan-1相同：每族/模式取S3d-O8的ceil(1/3)，目标≤100k不拆，目标>100k才拆且每子任务≥100k；先单独完成计入统计的gamma 267312 production canary。使用6核CPU预算、自适应尽量4–6 workers，保留1.5GiB MemAvailable floor、8GiB SwapFree floor和8GiB动态磁盘reserve。SF3必须做自己的buildup→inventory→actual-position delayed；三块W永远是passive，不加入BGO/plastic veto。复用冻结37194-ray full-envelope bank和47的后处理算法，比较fresh SF3与frozen SE3的20d F3 central/proxy。若且仅若central F3_SF3/F3_SE3≤0.75，按交接第10节补prompt/buildup到S3d full-stat，并在重建full inventory后按delayed mixture硬门决定完整250k重跑或合规增量；否则停止补量并完整报告。持续推进到完成或真实资源/物理阻塞。
```
