# SH3 OptV3：与 SG3B 同 canonical 统计量的生产方案

状态：`PLAN_ONLY__PRODUCTION_NOT_AUTHORIZED`

本方案由一个新的 `gpt-5.6-sol / high` 会话在 2026-08-18 独立只读复核后
提出。复核未启动 Cosima、detector response 或大型 SIM 扫描；当前
`/mnt/data/TES_Balloon_511_data/SG3/` 不可读，因此 SG3B 运行计数采用
`SG3B_SIMULATION_EXECUTION_HANDOFF_20260817.md` 的 canonical receipt 交接。

## 1. 当前裁决

OptV3 可以保留为几何审查候选，但当前不能启动背景生产。生产前必须闭合：

1. 168 个共有 declared volumes 的正式属性差分；现已确认 130 个完全相同，
   37 个 TES/Si/Cu 体只共享 `(-35.55, 0, +2.40) cm` 刚性平移，1 个 NF2
   顶安装环只增加授权光轴切口，非预期漂移为 0；
2. SG3B 中仍指向保留几何的 56 个 passive-lineage scorers；
3. SQUID/readout 盒与五段 Al cable-bundle 的恢复、重布或显式排除；
4. Bi 半筒、塑闪正电子 veto 与 BPE 的去留；若不设塑闪，其后处理 stage 必须
   是显式 identity pass，不能复用 SG3B 的 plastic-veto 抑制；
5. 三个新 BGO 名称到成熟 group-summed veto 的映射，以及 native `80 keV`
   记录阈值与下游 `50 keV` veto 的可观测性；
6. 46 个新增被动材料体的 volume/material/thermal-stage/activation-lineage
   所有权：30 Al、11 Cu、4 W、1 Be；
7. W 方框通光余量；其内半宽与声明光学圆半径都为 `2.70 cm`，解析余量为 0；
8. `SurroundingSphere` 与 TT/RP 合同：SG3B 为 `60 5 0 9 60`，OptV3 当前为
   `95 0 0 8 95`，不能复制 SG3B TT。

任何修正都会改变当前 OptV3 哈希。最终 `.geo/.det/.setup`、source manifest、
job plan 与 seed registry 必须一起冻结后才能产生生产 receipt。

## 2. “同统计量”的严格含义

匹配键必须是：

`(mode, family, batch_id, job_id/shard)`

而不是只匹配 17,887,107 的总数。初始批和 extra-2x 允许有人类可读 job 名
重复，canonical key 必须仍能区分 batch。每张 source card 的 20 个 equal-mu
角单元、corrected spectrum、flux、source hash、最终几何哈希和 seed 都要冻结。

### INSTANT：22 jobs / 3,842,079 accepted primaries

| family | initial accepted cell(s) | extra-2x cell(s) | total jobs / primaries |
|---|---:|---:|---:|
| p | 8,483 | 16,966 | 2 / 25,449 |
| n | 77,664 | 155,328 | 2 / 232,992 |
| alpha | 1,986 | 3,972 | 2 / 5,958 |
| gamma | 267,312 + 267,312 + 267,311 + 267,311 | 534,624 + 534,624 + 534,622 + 534,622 | 8 / 3,207,738 |
| e- | 98,447 | 196,894 | 2 / 295,341 |
| e+ | 20,062 | 40,124 | 2 / 60,186 |
| mu- | 3,481 | 6,962 | 2 / 10,443 |
| mu+ | 1,324 | 2,648 | 2 / 3,972 |

### BUILDUP：19 jobs / 3,045,028 accepted primaries

| family | initial accepted cell(s) | extra-2x cell(s) | total jobs / primaries |
|---|---:|---:|---:|
| p | 8,483 | 16,966 | 2 / 25,449 |
| n | 77,664 | 155,328 | 2 / 232,992 |
| alpha | no PASS; missing 1,448 | 2,896 | 1 / 2,896 |
| gamma | 261,834 + 261,833 + 261,833 | 523,668 + 523,666 + 523,666 | 6 / 2,356,500 |
| e- | 98,447 | 196,894 | 2 / 295,341 |
| e+ | 20,062 | 40,124 | 2 / 60,186 |
| mu- | 22,564 | 45,128 | 2 / 67,692 |
| mu+ | 1,324 | 2,648 | 2 / 3,972 |

SG3B 缺失的 `sg3b_buildup_alpha_shard0001` 1,448 histories 不是物理零，也不
进入 matched accepted totals。若以后要恢复完整三倍 alpha 曝光，必须另建
SG3B 与 OptV3 各 1,448 的 matched supplemental receipts，不能只补 OptV3。

### day-15 exact-position delayed：33 jobs / 8,000,000 triggers

- p：50,000 canary + `3 x 250,000` + 200,000，共 5 jobs；
- 其余七族：各 `4 x 250,000`，共 28 jobs；
- 八族各 1,000,000 triggers。

delayed source 必须由 OptV3 自己的 BUILDUP inventory 生成，保留 exact
production position、parent ZA、volume/material、NUBASE ground-state
correction 和 per-family TT guard。不得复用 SG3B inventory 或 delayed cards。

### 独立 PARMA mono-511：13 jobs / 3,000,000 photons

- 50,000 canary + `11 x 250,000` + 200,000；
- line energy `510.99895 keV`；
- 80 equal-mu bins；
- full-sphere line flux `0.16651547160226118 ph cm^-2 s^-1`。

该分支必须标记 `NON_ADDITIVE_SIDECAR`。repaired `unit_only_total_gamma` 已有
宽箱湮没隆起；没有新的 flux-closed 去重/重组合同前，二者不得直接相加。

账面总数为 87 PASS receipts / 17,887,107 个不同归一化的输运单位。其中 common
timeline 的 broadband background 只接受 22 个 INSTANT 与 33 个 delayed
receipts；19 个 BUILDUP 只生成 inventory，13 个 PARMA receipts 保持独立。

## 3. 背景生产之前的信号门禁

必须先运行冻结的 37,194-ray full-envelope signal bank；它不属于上述 87 个
background receipts，也不使用大气 TT。receipt 必须绑定 EventList 与最终几何
哈希，光学归一化仍为 `20.08476 cm2`。

W 方框需同时通过：

- static minimum clearance `> 0.0001 cm`；
- clearance `>= delta_alignment`，其中装调/制造公差必须另有 authority；
- W direct first-hit / geometric clipping 为 `0 / 37,194`；
- 相同注入面、共同 response 下，W2 selected Aeff 相对 matched baseline 首轮
  损失目标不超过 2%，超过 5% 必须停止并改几何。

若要声称相对 SG3B 的灵敏度提升，还应给 SG3B 补同一 ray bank 的 matched signal；
现有 SE3 条件代理不能作为最终比较 authority。

## 4. 分阶段门禁

| stage | action | target | pass authority |
|---|---|---:|---|
| 0 | 冻结 Bi/plastic/BPE、SQUID/cables、BGO、W、46 个新被动体 lineage 与 38 项共有体积差分 | 0 | mass inventory、差分审计、detector-map contract |
| 1 | 最终零输运几何 | 0 physics jobs | static PASS；10,000 samples/placement、0.0001 cm overlap PASS；新哈希 |
| 2 | 最小包络、corrected-keV cards、cell plan、fresh seeds、磁盘/资源预检 | 0 | 无 legacy token；`additive_mono511=false`；seed registry PASS |
| 3 | full-envelope signal | 37,194 rays | W clipping=0、正余量、Aeff/cutflow/common-response receipt |
| 4 | INSTANT + BUILDUP | 22 + 19 jobs | 41 PASS、6,887,107 accepted；逐 cell TT/RP/hash |
| 5 | OptV3 inventory | 0 transport | 八族 inventory、NUBASE、`sum(RP)/sum(TT)`、exact-position lineage |
| 6 | delayed | 33 jobs | 8 x 1,000,000；33 PASS；8,000,000 triggers |
| 7 | PARMA sidecar | 13 jobs | 13 PASS；3,000,000；`NON_ADDITIVE_SIDECAR` |
| 8 | common response | 0 Cosima | 420 eV FWHM、0.3 keV pixel、group-summed active veto 50 keV、W2、Step05 closure |
| 9 | common marked-Poisson timeline | 0 Cosima | M05 成熟指数到达率、1 us transitive grouping、mission anchors 与 uncertainty receipt |
| 10 | promotion review | 0 | candidate-own Aeff、rate、Neff、matched uncertainty 与工程边界 |

## 5. receipt、失败重试与资源边界

- 每个计划 cell 只能有一个 canonical PASS receipt；partial/failed 不得合并。
- 同 seed 重试仍是同一 attempt，不增加曝光。改变 seed、source、event target、
  geometry 或 detector map 必须新 job/receipt，并显式 supersede，不能覆盖。
- 失败的 SG3B alpha seed 也视为已占用；OptV3 seeds 必须与所有历史及 signal
  registry 全局不交。
- 几何哈希一旦改变，旧 signal、INSTANT、BUILDUP、inventory 与 delayed 都不能
  与新版本混用。
- BUILDUP 某 family 失败会阻断该 family 的 inventory/delayed；不能由其他
  family 或其他 geometry 补齐。
- SG3B campaign 为约 80.82 GiB。OptV3 增加 lineage 后，开跑前暂按
  `max(110 GiB free, canary-calibrated full-campaign upper bound + 8 GiB)` 设磁盘
  gate；代表性 canary 后重投影。并发度也必须由 canary 和内存/PSI guard 决定，
  不能直接复用旧 workers 值。

## 6. 允许的下一步

获得用户授权后的最小安全动作是建立一个非覆盖的 production-preflight 修订包，
闭合 stage 0–2 并冻结新哈希；仍不启动大气输运。所有零输运 receipts 通过后，
第一条允许的物理输运是 stage 3 的 37,194-ray signal gate，而不是直接启动
87-receipt 背景 campaign。

