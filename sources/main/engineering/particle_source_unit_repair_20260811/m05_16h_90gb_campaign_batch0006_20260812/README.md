# M05 corrected-keV：16 小时 / 90 GB 非覆盖式执行方案

状态：`PLAN_ONLY__NO_TRANSPORT_LAUNCHED`

本目录只给下一终端提供执行合同。它不修改旧代码、旧 runs 或 M05/M06 论文，也没有启动任何 Cosima 任务。新实现只能写入本工程目录；新模拟产物只能写入：

`runs/particle_source_unit_repair_20260811/m05_16h_90gb_campaign_batch0006_v1/`

## 结论先行

按真实墙钟固定为 `2 h smoke + 10 h 七族 + 4 h proton`。2 小时 smoke 从一开始就按可合并生产合同运行，因此通过后可计入最终统计；若 compact 候选在前 20 分钟内不能获得独立、write-once 的 transport authorization，则本批不等待它，自动运行 corrected-keV rich-SIM 基线 `F` 臂。这样 smoke 不会白跑，后续 14 小时也不会被一个尚未就绪的优化实现拖住。

本轮允许的“边跑边优化”只有：分片大小、任务顺序、并发数、压缩/写盘路径，以及 smoke 已验证并全局选定的输出表示。禁止在 16 小时中途改物理清单、CUT、源谱、VETO 阈值、事件选择或核素删选；这些变化会产生不可直接合并的混合物理样本。

基于现有小样本点估，2 小时 F/C smoke 两臂合计约 1.14 GB，10 小时七族约 29.67 GB，4 小时 proton 约 10.54 GB，总 rich-equivalent 约 41.35 GB。质子有强重尾，所有数值是规划点，不是容量上界。磁盘采用动态硬门和 2 倍规划门。

## 1. 不可变物理合同

- source contract：`engineering/particle_source_unit_repair_20260811/data/source_contract_manifest.json`
- source contract SHA-256：`5424eeca35b20affb153c0e07c31a6582e575f511922bf55f40a5a0f77ab4326`
- 只允许 corrected-keV source；任何 `Spectrum File` 含 `cosima_spectra_dp_2602units` 立即失败。
- `unit_only_total_gamma` 已含 annihilation bump；不得叠加独立 mono-511。
- 几何：Mass_model_511 与 S3d-O8，各自 source card 与 SIM header 必须指向正确 geometry。
- 物理：`QGSP_BIC_HP + LivermorePol`；本批不改变现有 production cuts、材料或 detector definitions。
- mode：`instant` 与 `BUILDUP` 分开；禁止跨 geometry、mode 或 family pool。
- 旧 source、旧 runner、旧 ledger、旧 runs、论文全部只读。不得 `git reset`、`git checkout` 或“清理”现有 dirty worktree。

开跑前只读静态门：

```bash
python3 engineering/particle_source_unit_repair_20260811/code/validate_corrected_source_package.py --check
```

必须得到 160 spectra、24 cards、480 corrected references、0 legacy references。

## 2. 新目录与写入边界

新工程根：

`engineering/particle_source_unit_repair_20260811/m05_16h_90gb_campaign_batch0006_20260812/`

新运行根：

`runs/particle_source_unit_repair_20260811/m05_16h_90gb_campaign_batch0006_v1/`

运行根至少包含：

```text
global_contract.json
execution_state.json
seed_registry.json
stage00_mergeable_smoke/
stage10_seven_family/
stage20_proton/
job_receipts/
checkpoint_authority/
failed_attempts/
final_validation.json
final_ledger.json
```

所有 canonical 文件 write-once、临时文件用 `.partial`、最终原子 rename；失败或中断输出进入 `failed_attempts/`，不得删除后伪装成未发生。现有低层 runner 只能作为只读逻辑参考；其默认日志覆盖和临时 source 删除行为不适合作为本 campaign 控制器。

## 3. 16 小时硬时钟

`T0` 是新 campaign controller 启动时刻，静态复核也计入 16 小时。

| 墙钟区间 | 阶段 | 任务 |
|---|---|---|
| T+00:00–00:20 | preflight | 冻结合约、磁盘、seed、静态源门；判断 compact 是否有独立授权 |
| T+00:20–01:35 | smoke launch | F-only，或已授权的 matched F/C；生产型小样本 |
| T+01:35–02:00 | smoke drain/validate | 停止新发射、隔离未完成任务、写 `smoke_decision.json` |
| T+02:00–11:35 | seven-family launch | 按预注册比例推进七族；动态分片与 family-aware 调度 |
| T+11:35–12:00 | seven-family drain/validate | 停止新发射、验证完整 shard、发布 prefix ledger |
| T+12:00–15:30 | proton launch | 四个 cell 轮转小段；512→1024→2048，自适应但不改物理 |
| T+15:30–16:00 | proton drain/finalize | 隔离未完成任务，发布 final validation/ledger/umbrella |

阶段边界前不再发射新任务。到硬边界仍未完整结束的任务应优雅终止并隔离，不能计入统计，也不能侵占下一阶段。以后若重试，必须使用同一 seed、同一 source 和同一事件数；不得因为某 seed 特别慢或文件特别大而换 seed，这会系统性删除重尾事件。

## 4. 90 GB 磁盘合同

“90 GB”按十进制 `90,000,000,000 B` 解释，但同时必须保留 `20 GiB` 文件系统安全余量。开跑时计算：

```text
campaign_cap = min(90,000,000,000, free_bytes_at_T0 - 20*1024^3)
```

2026-08-12 本次只读测量 `free=106,437,652,480 B`，故当时安全上限只有 `84,962,816,000 B`；若要真正得到完整 90 GB 输出额度，需在开跑前额外提供约 `5.04 GB` 空间，且不得删除旧数据。控制器必须以 T0 实测值为准。

内部保留：

- smoke hard cap：8 GB；
- T<12 h 时为 proton 保留 15 GB；
- 全程另保留 5 GB campaign emergency，不纳入计划输出；
- seven-family 发射门：`campaign_bytes + active_declared_caps <= campaign_cap - 20 GB`；
- proton 发射门：`campaign_bytes + active_declared_caps <= campaign_cap - 5 GB`；
- 每次 launch 前还要求文件系统 `free >= 20 GiB + active_declared_caps`。

初始单任务 declared cap：七族 1.5 GB，proton 2.0 GB；只有完成 shard 的实测尾部允许提高，不得用删除数据来处理超限。预计总量约 41.35 GB，2 倍规划量约 82.7 GB，刚好落在当前动态安全上限内，但 proton 重尾使这不是保证。

## 5. 0–2 h：可计入生产的 smoke

### 5.1 两条合法路径

路径 A，默认且总能执行：新 batch0006 的 corrected-keV rich-SIM `F` 臂。其通过动态验证后全部写入正式 ledger。

路径 B，仅在前 20 分钟内存在独立 write-once authorization 时：在新目录运行 matched `F/C`。禁止复用或改名现有 `m05_complete_compact_smoke_20260812`；它仍是 `NON_MERGEABLE_BENCHMARK`、`transport_authorized=false`、0 transport。

F/C 使用相同 EventList tape、相同 transport seed、相同 source/geometry/physics/CUT。预注册全局选择，不能按 cell 或物理结果挑臂：

1. C 对完整 32-cell smoke（七族 28 cell + proton 4 cell）通过全部物理、表示、资源和 consumer 门，则 C 的所有 shard 进入正式 ledger，F 全部标成 paired duplicate evidence；
2. C 任一门失败或授权缺失，而 F 全部通过，则 F 进入正式 ledger，C 隔离；
3. F 失败，则停止 14 小时生产，不允许 C 单独自证晋级；
4. 同一个 primary 的 F/C 永远只计一个臂。

### 5.2 smoke 统计矩阵

每个 geometry×mode cell 的事件数：

| family | events/cell | shards/cell |
|---|---:|---:|
| gamma | 10,000 | 3 |
| neutron | 2,000 | 3 |
| eplus | 500 | 3 |
| eminus | 500 | 3 |
| alpha | 100 | 3 |
| muplus | 250 | 3 |
| muminus | 250 | 3 |
| proton | 256 | 4×64 |

一个被选臂共 55,424 个可计数 primaries、100 个 shard；若 F/C 都运行则总 transport invocations 为 110,848，但正式统计仍只计 55,424。三 subshard 是 paired performance interval 的最低门；proton 保持四个 64-event 小片以暴露重尾。

### 5.3 compact 晋级门

所有门都必须通过：

- generated tuple、顺序、seed、IA INIT、root identity 严格闭合；requested = generated = `IA INIT`；aborted count = 0；
- prompt：TES 每 pixel 能量/位置/POST time/多重性、Mass 24 CsI、O8 3 BGO+3 plastic 的逐 block 能量/时间、480–550 keV/W2/VETO50/70/80 flags 与 F 一致；
- 仍保存所有 raw-TES-positive 的完整 native truth、所有 RP 的完整生产证据、以及每 geometry×mode×family×subshard 至少一个 outcome-independent TES-zero control；
- BUILDUP：所有 TT（包括 zero-RP）、RP 的 Z/A/state、material、physical/logical/touchable volume、exact position、time、track/root/ancestry 与 F 闭合；
- compact truth 可被真实 `MFileEventsSim`/Revan 读取，或有 hash-bound materializer 并通过 round-trip；
- 整数和字符串 exact；浮点默认 `abs <= 1e-6 keV or rel <= 1e-9`；
- C/F published bytes reduction 的分层 95% 下界至少 3×，且 paired end-to-end wall ratio 的 95% 上界不超过 1.05；否则本批选择 F；
- C peak process-group RSS 不高于 F 的 1.2 倍；全 campaign 磁盘上界满足动态 cap；
- validation 为 `PASS`、errors 为空，再原子发布 `PASS__BATCH0006_STAGE00_MERGE_ELIGIBLE`。

这里验证的是端到端输出路径，不宣称 Geant4 stepping 本身变快。现有 compact 的 N0/P12/P13 未闭合，因此没有独立授权时必须走 F-only。

## 6. 2–12 h：七族 10 小时

采用现有 accepted cell rate 的 r1 剩余工作比例。下表是 10 个累计 Cosima run-phase 小时的首轮点目标；阶段硬停止仍按 10 小时真实墙钟。并发、初始化和 I/O 会让实际完成数上下波动，未完成 cell 必须写成 `missing/partial`，不能写成零。

| family | 新 primaries 点目标 | run-phase 分额 | rich SIM 点估 |
|---|---:|---:|---:|
| gamma | 5,086,475 | 3.737 h | 10.762 GB |
| neutron | 518,725 | 2.413 h | 6.946 GB |
| eplus | 131,257 | 1.709 h | 5.413 GB |
| alpha | 13,441 | 1.525 h | 4.484 GB |
| eminus | 242,617 | 0.592 h | 1.984 GB |
| muplus | 6,248 | 0.016 h | 0.054 GB |
| muminus | 2,889 | 0.007 h | 0.027 GB |
| **合计** | **6,001,652** | **10.000 h** | **29.669 GB** |

cell 级目标见 `seven_family_allocation.csv`。其原则是对每个 cell 的 r1 剩余量乘同一个 `10/66.84` 因子，而不是把 family 总数随意均分。两几何保持相同 source measure 和成对 ordinal，但各 cell 单独 TT 归一。

初始 shard：gamma 25k、neutron 5k、eplus/eminus 2.5–5k、alpha 250、muon 1k；末尾使用精确 remainder。以后只按已完成 shard 的成本调整：

```text
N_next = N_prev * 480 s / median(last_3_completed_wall_s)
```

单次变化限制在 `[0.5, 2.0]×`，目标 5–10 分钟/job。调整只适用于未来 seed；不能改变已开始或失败 seed。若首轮点目标提前完成，启动一个新的、同样比例的预注册轮次；不得根据“哪个 family 恰好给出更好结果”临时追样。

## 7. 12–16 h：proton 小段滚动生产

近期目标是 `1M-gamma-equivalent` screening，而不是严格 proton r1。每个 geometry×mode 的目标是 23,400 primaries。旧 batch0000 已有 23/cell；本次被选 smoke 再贡献 256/cell，因此 stage20 目标为：

```text
23,400 - 23 - 256 = 23,121 primaries/cell
4 cells total = 92,484 new stage20 primaries
```

按 N=256 resource diagnostic 线性点估，stage20 约 4.01 run-phase h、10.54 GB；质子重尾使它不是置信上界。严格 r1 仍需约 234,000/cell，不能把本阶段写成完整 proton 收敛。

四个 cell 采用固定 round-robin：Mass instant → O8 instant → Mass BUILDUP → O8 BUILDUP。每 cell 的计划 shard 序列为：

```text
512, 1024, 10 × 2048, 1105
```

实际未来 shard 可按同一 5–10 分钟公式在 512–2048 内调节，但四 cell 必须按轮次公平推进。每完成一轮记录 wall、BeamOn、bytes、peak process-group RSS、free disk、TT、RP 和 validator 状态。

本阶段禁止：截断高能 proton 尾、删除 `<480 keV` secondary、换 physics list、抬全局 CUT、按 TES/VETO 结果跳过 seed、启用尚未闭合权重的 Geant4 track-level biasing。允许收集能量×角度×成本诊断，为下一批 full-support 分层设计服务；本批正式 estimator 仍是 corrected full-spectrum analogue。

## 8. 并发与重尾调度

本机约 11 GiB RAM；已观察单 job 峰值约 4.98 GB，swap 已大量使用。初始最多 2 个独立进程，并保持“最多 1 个 heavy O8 job”规则。只有至少 8 个相同 arm 的完整 signed receipts 后，且：

```text
sum(p95_RSS_upper_of_active_classes) + 2 GiB < MemAvailable
```

才允许升到 3 个进程；绝不默认 4–6 heavy workers。proton 初始 1 worker；达到上述门后最多 2 workers。调度器应 work-stealing，但不能跨 seed 拆弃重尾。

## 9. 每 shard 验证与合并

每个正式 shard 至少检查并记录：

- global contract SHA、job source SHA、seed、geometry/mode/family/stage/ordinal；
- requested/generated/IA INIT 数量；corrected energy support；source/geometry header；
- return code、watchdog reason、wall、BeamOn、peak process-group RSS；
- SIM/DAT/log/source/sidecar bytes 与 SHA-256；
- DAT TT、log observation time、RP count；zero-RP 仍有正 TT；
- free disk、MemAvailable、active declared cap；
- seed 与 batch0000–0005、冻结未运行 seed、本 campaign registry 均不冲突。

合并公式：prompt 在相同 geometry×mode×family 内用 `sum(selected)/sum(TT)`；BUILDUP 在相同 geometry×mode×family×volume×isotope-state 内用 `sum(RP)/sum(TT)`。禁止 hard-coded replica divisor，禁止跨 geometry/mode/family pool。

## 10. 终止条件与最终交付

任一条件触发 stop-launch：

- 到达阶段 stop-launch 时间；
- 动态磁盘门、20 GiB reserve、active-attempt cap 或 RSS 门失败；
- corrected source、geometry header、seed registry、event count、TT/RP 或 hash 门失败；
- F smoke 失败；
- 同一 seed 的精确重试连续失败，无法在不跳过重尾的前提下继续该 cell。

最终必须发布：

- `global_contract.json`
- `seed_registry.json`
- `smoke_decision.json`
- 每 shard receipt 与 resource JSONL
- `seven_family_validation.json` / `seven_family_ledger.json`
- `proton_validation.json` / `proton_ledger.json`
- `final_validation.json` / `final_ledger.json`
- `final_umbrella.json`

`final_umbrella.json` 可以 hash-bind 旧 immutable ledgers，但不得改它们。必须报告实际 wall/BeamOn/events/TT/RP/RSS/bytes、每个 partial/missing cell、smoke 选择臂、是否闭合 1M-equivalent proton checkpoint，以及所有 authority 边界。

这 16 小时产品定位为 corrected-keV mergeable screening / partial-production authority。它不自动恢复 M05 的完整 eight-family delayed response、mission sensitivity 或 geometry promotion。

