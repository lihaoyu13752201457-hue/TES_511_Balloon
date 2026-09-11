# SG3B background transport — 运行态交接 (2026-08-17)

手机 / 新会话读这一份就能接管。**不要新建执行器、不要改统计量、不要扫描或哈希大型 SIM。**

## 一句话现状

v1 以 **20/21 判 FAILED**（`sg3b_buildup_alpha_shard0001` 三次 attempt 全部撞内存天花板）；
chain 闸门按设计 fail-closed 未启动任何东西。**extra-2x 已由用户授权改为直接启动，正在跑**
（pid 106674，4 workers，8–9 小时）。v1 的 alpha 缺口留待 extra-2x 跑完、宿主空闲后处理。

## 正在跑的进程

**extra-2x**：`run.py --config tool/execute/profiles/sg3b_plan1_extra2x_20260816_v1.json --workers 4`
- profile_id `SG3B_PLAN1_BACKGROUND_EXTRA2X_20260816_V1`，独立 generated root 与 run root
- INSTANT 2,561,386 / BUILDUP 2,030,984 = 正好 2× Plan-1，与首轮合计 3×
- 21 个种子与 v1 实测**零重叠**；preflight PASS；约 38.6 GB 产物，磁盘 61 GB 空闲
- 控制器 stdout：`runs/.../sg3b_plan1_background_extra2x_v1/controller_stdout_20260816T1716Z.log`

`chain_after_complete.py` 已退出，**不要再起它** —— extra-2x 已经在跑了，再起会撞文件锁。

## v1 alpha 失败：根因已定案

完整证据记录见
`runs/.../sg3b_plan1_background_v1/alpha_buildup_memory_ceiling_20260816T1716Z.json`。

| attempt | workers | peak RSS | wall | 停在 |
|---|---|---|---|---|
| 01 | 5 | 4.74 GiB | 1054 s | event 786/1448 |
| 02 | 5 | 5.96 GiB | 1030 s | event 786/1448 |
| 03 | **1（独占）** | **7.65 GiB** | 1420 s | event 786/1448 |

三次 watchdog_reason 全是 `runtime_MemAvailable_floor_breached`，登记 seed 1257497726 三次一致，
每次都从 event zero 重启，三个 failed attempt 目录全部保留。

**根因不是泄漏、不是并发压力，是 event 787 这一个事例。** attempt03 日志第 11031 行（全文 11035 行）
停在 `Storing event 786 of 786`，event 787 一行输出都没有就被砍。普通事例 1–40 行日志，event 786
一个就 357 行，单次沉积高到 6.36e+08 keV（636 GeV，落在 `BGO_S3C_FullWrap_SideShell_WindowCut_40mm`）
—— 已经进入 α 谱的极高能区。其余 20 个 job 峰值全在 0.58–3.41 GiB，说明 alpha 的基线正常。

**关键：三次都是"还在往上爬的时候"被砍的，所以真实需求量至今未知。** 宿主 11.68 GiB RAM /
14.31 GiB swap；MemAvailable 看门狗不计 swap，要够到那个上限就必须放宽底线，而底线未被放宽。

## ⚠️ 科学红线：换种子重掷 = 低估本底

反复换 seed 直到 alpha job 跑通，等于**系统性剔除最高能的 α 初级粒子** —— 恰恰是散裂产额最高、
活化最强、次级本底最多的事例。偏差方向是**低估本底 → 抬高 Z 显著度**，对本项目正是最危险的方向。

**任何因内存天花板丢失的事例必须计数上报，绝不允许用"恰好跑通的新样本"静默替换。**
当前缺口：alpha buildup 1448 histories = Plan-1 buildup 的 0.143%（但按物理权重远高于此份额）。

## extra-2x 跑完后的待决项

v1 的 1448 个 alpha buildup histories 怎么补，三个选项（详见上面那份 JSON）：

- **A_SHARD（推荐）**：新 profile 把 alpha buildup 切成 8×181，总量仍是 1448，种子由
  `derive_seed(profile_id, job_id)` 自动派生。收益是**失效隔离** —— 撞上巨型事例只赔 181 个而不是 1448，
  且损失量被精确量化。只需一张小的 job-plan CSV，`prepare.py`/`run.py`/`progress.py` 原样复用。
- **B_RELAX_MEM_FLOOR**：用登记种子独占重跑并放宽 `runtime_mem_floor_bytes` 让它吃 swap。
  唯一零选择偏差的选项，但上限未知、swap 抖动严重、有真实 OOM 风险，成功率估计低。
- **C_ACCEPT_GAP**：接受 20/21，在本底预算里显式报告这个缺口。零偏差，但 α 活化通道留洞。

**注意 extra-2x 自己的 alpha buildup 是另一个种子（773714359）、2896 个事例。它跑成什么样本身就是
一次免费的"换种子实验"，能告诉我们这种巨型事例到底有多常见 —— 决定 A/B/C 之前先看它的结果。**

## 看进度（项目自带，只读）

```bash
cd /home/ubuntu/.codex/worktrees/8633/TES_511_Balloon
python3 tool/execute/progress.py --config tool/execute/profiles/sg3b_plan1_extra2x_20260816_v1.json --once   # extra-2x
python3 tool/execute/progress.py --once                                                                      # v1（已终态 FAILED 20/21）
```

## 接管者须知

- extra-2x 是 `nohup` 起的，**独立于任何 Claude 会话**，会话关掉它照跑。
- `run.py` 失败的 job 会被重新 append 到队列**末尾**（`run.py:694`），且 `raise` 只发生在队列
  排空之后（`run.py:698`）—— 所以 **"alpha 最后跑"是现成行为，不需要改任何东西**，
  alpha 失败也不会拖累其余 20 个 job。
- 不要再起第二个 controller：`run.py` 的文件锁会拒绝，这是设计如此，别去删锁。
- extra-2x 的 `max_attempts` 是 2 且**没有** per-job 覆盖。v1 里 `instant_n` 与 `instant_eplus` 都
  是到 attempt03 才 PASS（诱因是已被关掉的 aggregate RSS cap + 5 workers 争抢，现已 4 workers）。
  若某 job 因此耗尽次数，**先拿证据再决定**是否加 per-job 覆盖，不要预防性放宽。
- 本机 CLI 已于 2026-08-17 从 2.1.197 升到 2.1.224（官方 manifest SHA-256 校验通过，
  支持 `claude-opus-5`）；2.1.197 保留在 `~/.local/share/claude/versions/` 可回退。

## 红线

- 20 张 v1 PASS receipt 与 SG3B 的 SIM 一律不得删除、覆盖或冒充。
- 重试必须用登记 seed 从 event zero 开始，绝不接续部分事例。
- 完成态只允许 executor 的 header-only 校验（最多 80 行解压），不做全 SIM 扫描或摘要。
- 资源违规只砍单个最大 worker，不设 controller 级全局 STOP。
- 因内存天花板丢失的事例必须计数上报，不得静默替换。

## 本轮（2026-08-17 会话）改动清单

- **代码改动：无。** **配置改动：无。** 只是用现成的 `run.py --config` 启动了 extra-2x。
- 新增两个只读证据/文档：`alpha_buildup_memory_ceiling_20260816T1716Z.json` 和本文件的更新。
