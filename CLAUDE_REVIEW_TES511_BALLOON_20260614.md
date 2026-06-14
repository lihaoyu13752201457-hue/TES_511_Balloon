# Claude Review R3: TES_511_Balloon 修复后复审报告

Date: 2026-06-14 (第三轮)
Reviewer: Claude (Opus 4.8)
Scope: 对照 `CLAUDE_REVIEW_TES511_BALLOON_20260612_R2.md` (R2) 与
`outputs/reports/claude_review_r2_execution_20260612/` 执行报告, 逐项核实 R2 修复;
并对 R2 之后新立/新增的两个分支 (`fullstat_v2` 修复版 + 2026-06-13 `fullstat_v2_exactpos`
精确位延迟源闭包 + boundary/spatial sidecar) 做独立数值复审。
Mode: 只读评审。本报告是唯一新增文件。所有关键数字均直接从盘上产物重算, 附录 A 给出复现命令。

---

## 0. 一句话总结

**R2 的 P0 (Step05 prompt non-gamma ×8) 修复执行质量高, 数值逐位复核通过,
且本轮未发现第四起 ×8/等效时间家族 bug —— 这是两轮以来第一次"新权威"里没有归一化炸弹。**
但本轮发现三个需要处置的问题, 都不是计数错误而是**权威治理/物理模型依赖/溯源**问题:

1. **(P1) 权威双轨**: 仓库同时存在两套互相打架的"current"W2 头条数字 ——
   `fullstat_v2` (B=**0.0729576 cps**, Z20d=**5.70221**, 1Ms=**6.82301e-5**) 与
   `fullstat_v2_exactpos` (B=**0.0624651 cps**, Z20d=**6.15522**, 1Ms=**6.32564e-5**)。
   `Project_Memory` 第 947 行明确写 `fullstat_v2` 是 "Current authority", 但 2026-06-13
   那份**最新、最完整**的闭包报告把自己标成 "the full-stat closure" 并用 exactpos
   的更优数字。新会话读到哪个文件, 答案就差 ~14% (B) / ~8% (1Ms)。

2. **(P1) exactpos 的全部增益来自一次未验证收敛的延迟源换模**: Z20d 5.70→6.16 的提升
   **100% 来自延迟本底从 0.0138749→0.003382 cps (4.1× 下降, 延迟 W2 事件 160→39)**;
   prompt 与 signal 与 `fullstat_v2` 逐位相同。下降的物理机制是把 `RadialProfileBeam`
   的**方位角抹平**换成真实 3D 位置 —— 方向上是对的 (项目自己在 Memory L964-966 承认
   RadialProfileBeam "regenerated azimuth", 提交基线 pending 也写 "replace the
   axisymmetric delayed-source compression ... before paper-facing numbers")。但
   exactpos 只用 **5000 个有放回抽样点 + 单一 seed** 代表 253770 行真位表, 4× 的**幅度**
   未做 support-size 收敛检验。即: 被定为 "authority" 的 `fullstat_v2` 延迟方位角是人造的,
   而更正确的 exactpos 又欠采样 —— 当前任何一个单独引用都不稳。

3. **(P1) 版本控制没有兜住头条**: `git init` 已做 (3 commits, ×8 修复确实在基线提交里),
   但**最新权威 exactpos 的全部代码与报告未提交**: 3 个新工具未跟踪 + 6 个核心文件
   working-tree 已改未提交; 且 `.gitignore` 把 `outputs/reports/` 整个忽略, 导致**当前
   头条产物目录 `..._fullstat_v2_exactpos_20260613/` 是 git-ignored**, 而被它取代的
   `..._20260612` 反而被 force-add 跟踪。两起 ×8 都是靠 .dat 考古定位的, 现在恰恰是
   "换权威"这一步没进版本库。

其余为 P2 长尾 (悬空指针仍 ~40 处未清, sidecar 基线混用, TE 记账小差)。

---

## 1. R2 修复项核实 (逐项)

| R2 事项 | 状态 | 本轮核实 (盘上重算) |
| --- | --- | --- |
| **P0 Step05 prompt 权重修复** | **DONE ✓ 逐位通过** | `prompt_normalization_audit.json`: 每 tag `rate_hz_per_event = 1/ΣTT_tag`, 8 个 non-gamma tag 各 8 文件 ΣTT≈1470-1485 s, gamma 12 文件 ΣTT=184.26 s, 每行 `rate_times_tt_sum=1.0`。eplus 80 事件 × 1/1472.273 = **0.0543377 cps** 与产物逐位吻合; prompt 合计 80/1472.273+6/1473.602+1/1485.177 = **0.0590827 cps** = `w2_stream_split` prompt 率。与 R2 预测 0.059083 一致。 |
| P0 per-tag `weight×ΣTT≈1` 断言 | **DONE ✓** | `build_v3p5_centerfinger_step05_l1_response.py:229` 对每 tag 校验 `|rate×ΣTT−1|>1e-12 即 FAIL`; 另加 TT 行数=文件数、每文件恰 1 条 TT、文件数=normalization 期望 三道护栏 (L191-219)。与 Step02 构建器同构。 |
| P0 修复在版本库 | **部分** | `git show HEAD:` 证实修复在基线提交 e92a572 (L209 `1.0/tt_sum`)。但其后 exactpos 改动未提交 (见 §3)。 |
| P0 `git init` | **DONE ✓** | 3 commits (e92a572 / 6913772 / 443397e), 387 文件跟踪。R2 最高工程风险项已落地 —— 但闭环不完整 (§3)。 |
| P0 重跑 Step05-08/closure/1Ms + 四处 headline 同步 | **DONE ✓ (但引入双轨)** | `fullstat_v2` 全链已用修复后 prompt 率重跑, headline 在 README/Memory/closure/compare 同步。实现正确, 但随后又叠了 exactpos, 造成 §2 的双轨。 |
| P0 Misquote 加 fullstat_v2 prompt ×8 条目 | **DONE ✓** | `Project_Memory.md:942-945` 列 "Do not quote ... 0.486136 / Z20d=2.20208 / 1.36235e-4 / 1.76837e-4 / 89.3% eplus"。 |
| P1 spot_r90 等价切割移植到 v3p5 | **DONE ✓ 方法学正确** | `outputs_v3p5_centerfinger_fullstat_v2_spatial/v3p5_spatial_line_proxy.md`: 在**侧窗局部坐标系**测质心, `spot_r90=1.05164 cm` 同时作用于信号 (留 0.900) 与本底 (0.0729576→0.0232510, 留 ~32%, prompt 0.0189662 + delayed 0.00428481), Z20d=8.17566。信号/本底同坐标系同切割, 自洽; 报告明确"非 profile-likelihood gain"。 |
| P1 compare_511 重打标签 | **DONE ✓** | 旧 2.99e-5 改标 `TES_511_Balloon_delayed_only_aspiration`; 现 v3p5 行 6.823007e-5。但仍是 `fullstat_v2` 口径 (见 §2.3)。 |
| P1 解析锚重算 (R1 遗留) | **DONE ✓** | I-128 锚 (`i128_anchor_r2_20260612.md`) 66.00180110381 Bq: 我对 fixed source ΣFlux(ZA53128) 重算 = **66.00180110306 Bq** (比值 1−1.1e-11), 全核素合计 85.63669586528 Bq 与 manifest 逐位吻合。旧 8.185 vs 6.323 无自屏蔽锚已退役。 |
| P1 validator 在本仓库跑通 | **DONE ✓** | `validate_v3p5_fullstat_r2.py` → `PASS_V3P5_FULLSTAT_R2_VALIDATION, problems=[]`; `validate_v3p5_exactpos_closure.py --label fullstat_v2_exactpos` → `PASS, problems=[]`。我本轮实跑两者均 PASS。 |
| P1 README/Memory 悬空指针清理 | **未做 (R1+R2 三轮遗留)** | 见 §4.1: README/Project_Memory/workflow 仍 ~40 处死链 (含 `XZTES_ADR_v4c_mkflange_cm/*`、`day15_complete_report/*`、`equiv2602_aligned`、`../new_geo_re_2/*` 等)。 |
| P2 "1/10"→分流标注 | **DONE ✓** | README:81-84 "gamma about 1/10, non-gamma about 1/80, generated particle count about 1/21.2"。 |
| P2 T_atm 45° LOS 论证 | **DONE ✓ (sidecar)** | `sec(45°)=1.414` 斜程作 Beer-Lambert sidecar (T_ref 0.739→0.652), 见 boundary closure; 明确仍以 scalar-T_atm 硬窗为主口径。 |
| P2 decay source 审计 backfill | **DONE ✓** | `backfill_v3p5_decay_source_audits.py` 已落 `normalization_audit_*.json`。 |
| P2 per-seed 光学 CSV / 根目录模板 | **DONE ✓** | per-seed CSV 入库并被 validator 计数; 根目录 CubeSat 模板移入 `old_md/templates/`。 |
| P3 审计多 TT 行防护 | **DONE ✓** | 构建器与 Step05 审计均"每文件恰 1 条 TT, 否则 FAIL"; 执行报告附 smoke 测试 (3 TT/2 文件 → FAIL)。 |

> 小结: R2 的全部 P0 + 大部分 P1/P2/P3 **真实做到且数值经得起重算**; 唯一明确"声称之外仍欠"的是
> 悬空指针 (本就未在执行报告中声称已修)。R2 当时预测的修正后 `fullstat_v2` ≈ 0.073 / 5.7 / 6.9e-5,
> 实测 0.0729576 / 5.70221 / 6.82301e-5 —— **预测与实现几乎完全吻合**, 反向佐证 R2 诊断与修复都对。

---

## 2. 本轮焦点 P1: `fullstat_v2` 与 `fullstat_v2_exactpos` 权威双轨 + 延迟源模型依赖

### 2.1 两套数字的来源与差异 (全部本次重算)

prompt + buildup + signal 在两个分支**逐位相同** (exactpos Step05 在代码里 `prompt_label =
"fullstat_v2"`, 复用同一 instant/buildup run; 见 working-tree diff)。**唯一变量是延迟输运。**

| 量 | `fullstat_v2` (RadialProfileBeam) | `fullstat_v2_exactpos` (PointSource×5000) |
| --- | ---: | ---: |
| W2 总本底 | 0.0729576 cps (247 事件) | 0.0624651 cps (126 事件) |
| ├ prompt | 0.0590827 cps (87 事件) | 0.0590827 cps (87 事件) ← 相同 |
| └ delayed | **0.0138749 cps (160 事件)** | **0.003382 cps (39 事件)** ← 4.1× ↓ |
| eplus 占比 | 74.5% | 87.0% (因总本底变小) |
| Step08 Z20d@1e-4 | 5.70221 | 6.15522 |
| 20d 3σ flux | 5.26111e-5 | 4.87391e-5 |
| 1Ms 3σ flux | 6.82301e-5 | 6.32564e-5 |
| 延迟 TE | 11531.598 s | 11530.474 s |

**Z 提升 100% 来自 B 下降, 无其它来源**: 信号不变 0.00118117 cps, 按计数 Z∝S/√B →
5.70221×√(0.0729576/0.0624651) = **6.163**, 实测 6.15522 (差 0.13%, 来自任务时间折叠的非线性);
1Ms 同理 6.82301×√(...)=6.379 vs 6.32564。**Step06/07/08 传播链自洽, 无新 bug。**

### 2.2 4.1× 延迟下降的机制: 方位角抹平 vs 真位欠采样

- **旧 `fullstat_v2` 延迟源** = 4653 个 `RadialProfileBeam` 块, 每块在轴上 `(0,0,z_slice)`
  按 `radial_z*.dat` 发射 (见 `runs/step02_delay_fix_v3p5_centerfinger_fullstat_v2/activation_decay_day15_groundstate_fixed.source`)。
  它保 (r,z) 但**把方位角抹平/再生成** (Memory L964-966 自述 "regenerated azimuth")。统计支撑充分
  (1e6 触发直接采连续径向廓)。
- **新 `exactpos` 延迟源** = 5000 个 `PointSource` 块, 坐标取自真实 `CC IP RP` 产生位置,
  从 253770 行权重表里**有放回抽样**, 每点等通量 0.0171273 Bq (×5000=85.6367 Bq 精确)。
  真 3D 方位, 但**支撑只有 5000 点 + 单 seed (260613)**。

在**单侧 45° 倾斜窗**的 center-finger 几何里, 方位角是强各向异性的: RadialProfileBeam 把活度
均匀铺满方位 → 总有一份"对着窗", 系统性**高估**延迟 511 进 TES; 真位则把活度按实际分布
(主要在 CsI 体内自吸收) 摆放, 看到的就少。所以 **4× 下降方向上是真物理修正**, 与项目自己
"paper 前必须换掉 axisymmetric 压缩"的判断一致。

但**幅度不可信**, 因为:
1. exactpos 延迟只剩 **39 个 W2 事件**, Poisson 本身 ~16%;
2. 5000 点有放回抽样对**稀疏但高产**的近窗体素 (rare-but-high-yield) 命中概率低, 易系统性
   **低估**延迟 → 4× 可能含一部分欠采样人造下降;
3. 构建器的"金标"模式 `weighted-table` (253770 块一点一源) 因 Cosima 解析不现实而被放弃,
   退化成 5000 抽样 (代码 `write_sampled_source`)。即理想态根本没跑过。

**结论**: `fullstat_v2` 延迟 = 方位人造、统计足; `exactpos` 延迟 = 方位真、支撑欠。两者把
真值**夹在中间**: B∈[0.0625, 0.0730], Z20d∈[5.70, 6.16], 1Ms∈[6.33e-5, 6.82e-5]。
现状是把"更不正确但更稳"的定成 authority, 把"更正确但欠采样"的藏成带软 caveat 的 sidecar ——
物理上拧巴, 统计上可理解。

### 2.3 双轨不一致清单 (同一仓库, 自相矛盾的 "current")

| 文件 / 位置 | 引用的是哪套 | 措辞 |
| --- | --- | --- |
| `Project_Memory.md:947` | fullstat_v2 (0.0729576 / 5.70221 / 6.82301e-5) | "**Current** fullstat_v2 W2 authority is ..." |
| `Project_Memory.md:146-152` | fullstat_v2 | "Full-stat v2 W2 ... **headline**" |
| `Project_Memory.md:170-182` | exactpos | "Exact-position ... **closure** completed 2026-06-13" (+ support-size caveat) |
| `README.md:45-48` | fullstat_v2 | "**Current** full-stat v2 W2 headline" |
| `README.md:67-79` | exactpos | "**Current** v3p5 exact-position delayed-source closure" |
| `workflow.md:98-99,109` | **只有** fullstat_v2 | — |
| `compare_511_narrow_1Ms.md:16` | **只有** fullstat_v2 (6.823007e-5) | "current v3p5 fullstat W2" |
| `claude_review_r2_execution_report.md:62-84` | **只有** fullstat_v2 | "**Current Fullstat Authority**" 表 |
| `..._w2_closure_fullstat_v2_exactpos_20260613/` (最新报告) | **只有** exactpos (0.0624651 / 6.15522 / 6.32564e-5) | 标题 "v3p5 Full-Stat Performance and W2 Background **Closure**", "Full-stat label is fullstat_v2_exactpos" |

→ 一个新会话问"当前 W2 本底/1Ms 灵敏度是多少", 读 Memory/workflow/compare/exec 得
0.0729576 / 6.82e-5, 读最新闭包报告/README 后半段得 0.0624651 / 6.33e-5。两者都自称 "current/closure"。

### 2.4 建议 (P1)

1. **做一次显式 authority 裁决, 全仓库一致**: 选定 `fullstat_v2` 或 `exactpos` 为唯一头条,
   另一个统一降级为 "sidecar / bound", 并在 **所有** 上述文件里同步措辞 (尤其消掉两处 "current"
   并存)。在收敛检验前, 建议对外/paper 口径用**保守的 `fullstat_v2`**, 同时显式声明延迟分量
   有 [0.0034, 0.0139] cps 的模型不确定区间。
2. **跑 support-size 收敛检验**判断 4× 是物理还是欠采样: 同 seed 下 5000 → 20k → 50k 抽样点
   重建 exactpos 延迟源各重跑一次延迟输运, 看延迟 W2 率是否收敛; 再换 2-3 个 seed 看方差。
   若稳定 → exactpos 升为唯一 authority, fullstat_v2 降为 "方位抹平的保守上界"; 若不稳 → 延迟
   分量按区间引用, 不得单引 6.33e-5。
3. **给 exactpos 延迟也加一条断言** (×8 家族第三次预防): 校验 ΣFlux(5000 点)=fixed_total_activity
   且每 (VN,ZA) 抽样数期望 ∝ 活度 (multinomial χ² 或至少 top-N 偏差阈值), 落盘进 manifest。
4. compare_511_narrow 与最新 performance 对比图二选一对齐到裁决后的 authority, 避免两张 1Ms 图打架。

---

## 3. 本轮焦点 P1: 版本控制没有兜住"换权威"这一步

`git init` 已做且 ×8 修复确在基线提交 —— 这点值得肯定。但溯源闭环没合上:

- **未跟踪的新工具 (3)**: `code/tools/build_v3p5_exactpos_delayed_source.py`、
  `code/tools/build_v3p5_boundary_closure_report.py`、`code/tools/validate_v3p5_exactpos_closure.py`
  —— 即产出当前更优数字的全部代码都不在版本库。
- **已改未提交 (16 文件)**: 含 `build_v3p5_centerfinger_step05_l1_response.py` (exactpos 标签分流)、
  `validate_v3p5_fullstat_r2.py`、`Project_Memory.md`/`README.md`/`workflow.md`、
  `build_v3p5_centerfinger_step08_time_dependent.py` 等。
- **最致命**: `.gitignore` 第 6 行 `outputs/reports/` 把整个报告树忽略。被取代的
  `..._w2_closure_20260612/` 是早先 `git add -f` 进去的 (TRACKED), 但**当前头条
  `..._w2_closure_fullstat_v2_exactpos_20260613/` 与 `..._boundary_closure_fullstat_v2_exactpos_20260613/`
  全部 git-ignored**, 普通 `git add -A` 都加不进去。

后果: `git HEAD` 反映的是 `fullstat_v2`(0.073) 世界, 当前实际头条 exactpos(0.0625) 既无代码也无
产物在库。两起 ×8 都靠 .dat 考古, 这次恰恰是 authority 迁移没留 diff。

**建议 (P1)**: 提交 3 个新工具 + 16 个改动; 对 exactpos 报告目录 `git add -f` (与 20260612 同等
待遇), 或改 `.gitignore` 为"忽略大产物 (`*.sim.gz`/`*.dat`/`*.pkl`/png) 但保留 `*_summary.json` /
`*_report.md` / `*.csv`", 让所有 authority 的轻量产物默认入库; 提交信息点名 "fullstat_v2_exactpos
延迟换模, 延迟 0.0139→0.0034, Z20d 5.70→6.16, support-size 待收敛"。

---

## 4. 其他发现 (P2/P3)

### 4.1 悬空指针仍 ~40 处 (P1→实际仍 P2 级长尾, R1+R2+本轮三连)

对 README/Project_Memory/workflow 里所有反引号路径做存在性扫描 (附录 A4), 排除 `1/10`、`66.56/s`
等非路径比值后, 仍有约 40 处真死链, 典型:

- **README** L125 `step08.../line_window_sensitivity.md`、L132 `step08.../spatial_line_proxy.md`
  (实际在 `outputs_v3p5_centerfinger_fullstat_v2_spatial/` 下, 路径漏了后缀目录)、
  L218-225 整个 Layout 块 (`csi_activation_baseline`、`day15_complete_report`、`half_life_unit_audit`、
  `review_20260531_closure`、`experiment_report_20260601`、`runs/science_511_onaxis_source`)。
- **Project_Memory** 大量: `XZTES_ADR_v4c_mkflange_cm/*.setup/.det/bounds.json/mass_budget.json`、
  `day15_complete_report/{work/event_catalog.pkl,complete_day15_summary.json,audit.md}`、
  `runs/step02_*_equiv2602_aligned/*`、`route_b_diffuse_supplement_20260602/*`、
  `science_511_ADR_100k/*`、`step06.../outputs/step06_..._summary.json` (旧无后缀路径)。
- **跨仓库** `../new_geo_re_2/*` 共 6 处 (PROJECT_MEMORY/project_state.json/experiment_report/validation
  等), 应按 `old_md/MIGRATION_DIRECTORY.md` 规则改旧仓库绝对路径 + 标 superseded。
- `VALIDATION.md:16,22` 与 `Project_List.md` 仍把 `XZTES_ADR_v4c_mkflange_cm/...det` 和
  `day15_complete_report/*` 当 PASS 行/现状列出 (虽在 legacy 语境, 但路径死、未标退役)。

横幅缓解了误引用风险, 但"current/PASS 字样 + 死链"组合对新会话仍是陷阱。建议一次性
sed 批量改指旧仓库绝对路径并加 `(superseded, see ...)`, 或删除已无意义的条目。

### 4.2 sidecar 基线混用 (P2)

`spot_r90` spatial sidecar (Z20d=8.17566) 与 compare_511 都建在 **`fullstat_v2` 基线**
(B=0.0730, delayed 0.00428), 但被打包进 `..._exactpos_20260613/` 闭包的 boundary 段
与 README exactpos 节附近; boundary 报告里 45° LOS 的 `spot_r90`/annular 又是另算。读者很难分清
某个 Z20d (5.42 / 6.16 / 7.21 / 8.18 / 8.46) 到底压在 0.0625 还是 0.0730 上。建议每个
sidecar 行显式标注 `base=fullstat_v2|exactpos`。

### 4.3 延迟 TE 记账小差 (P3, 非阻塞)

两延迟 run 的 TE≈11530-11532 s, 但 1e6 触发 ÷ 85.6367 Bq = 11677.6 s, 差 ~1.3%
(隐含有效活度 86.73 Bq)。两 run 同向同幅, 比较是 apples-to-apples; 差值最可能来自子核
(daughter) 在窗内也衰变抬高了总衰变率。建议在 step02 summary 里记一句 TE 的来源 (Cosima
实测 live-time, 含子核) 以免被误当归一化误差。

### 4.4 annular-likelihood Z 偏乐观 (P2, 已自标 sidecar)

6-环固定模板 Poisson 似然把 full-aperture 计数 Z20d 5.13 抬到 8.46 (×1.65)。固定模板似然在
"本底空间模板被当作完全已知"时会系统性乐观。报告已标 "fixed-template, not a nuisance-profile
publication likelihood", 措辞合格; 仅提醒别在对外语境单引 8.46 / 3.55e-5。

---

## 5. 复核通过项 (credit, 全部本轮重算/实跑验证)

- ✓ Step05 prompt 修复**逐位正确**且在版本库基线; per-tag `1/ΣTT` + `rate×ΣTT≈1` 断言到位。
- ✓ **未发现第三起 ×8/等效时间家族 bug**: prompt 走 per-tag 1/ΣTT, delayed 走 events/TE
  (单 run 无 replicas), exactpos ΣFlux=85.6367 精确, Step08 Z∝S/√B 完全自洽。这是两轮以来
  "新权威"首次干净。
- ✓ 两个 validator 实跑均 `PASS, problems=[]`。
- ✓ I-128 锚 66.0018 Bq 重算逐位吻合; 全核素 85.6367 Bq 吻合。
- ✓ spot_r90 方法学正确 (信号/本底同局部坐标系同切割, 自标非 profile-likelihood)。
- ✓ "1/10" 分流标注、T_atm 45° LOS sidecar、decay-source 审计 backfill、per-seed 光学 CSV、
  根目录模板归档、多 TT 行防护 —— R2 的 P1/P2/P3 均落地。
- ✓ R2 预测的修正后 `fullstat_v2` 数字 (≈0.073/5.7/6.9e-5) 与实测逐项吻合, 闭环成立。

---

## 6. 优先级清单 (R3)

| 级别 | 事项 |
| --- | --- |
| **P1** | **authority 裁决并全仓库去双轨**: 选定 fullstat_v2 或 exactpos 为唯一头条, 另一个统一标 sidecar/bound; 消掉 Memory L947 与 README 两处并存的 "current"; 对外口径在收敛前用保守 fullstat_v2 + 显式延迟区间 [0.0034,0.0139] cps (§2.3-2.4) |
| **P1** | **exactpos 延迟 support-size 收敛检验** (5000→20k→50k + 多 seed), 判断 4× 是物理还是欠采样; 给 exactpos 延迟源加 ΣFlux/抽样比例断言 (§2.2-2.4) |
| **P1** | **提交 exactpos 全套** (3 新工具 + 16 改动) + 让 authority 报告产物进版本库 (`git add -f` 或改 .gitignore 放行 `*_summary.json`/`*_report.md`/`*.csv`); 提交信息记录换模与数字迁移 (§3) |
| P2 | 悬空指针一次性清理 (~40 处, 含 `XZTES_ADR_v4c_mkflange_cm/*`、`day15_complete_report/*`、`../new_geo_re_2/*`、`equiv2602_aligned`); VALIDATION.md/Project_List.md 死链标退役 (§4.1) |
| P2 | sidecar 行显式标 `base=fullstat_v2|exactpos`; compare_511 与 performance 对比图对齐到裁决后 authority (§4.2) |
| P2 | annular-likelihood Z 对外加"固定模板/上界"标注 (§4.4) |
| P3 | step02 summary 记 TE 来源 (Cosima live-time 含子核, 解释 11530 vs 11677) (§4.3) |

---

## 附录 A: 关键数字复现命令

### A1. Step05 prompt 修复逐位闭环 (per-tag 1/ΣTT)
```bash
python3 - <<'EOF'
import json
a=json.load(open("stepwise_maintenance/step05_veto_time_axis/outputs_v3p5_centerfinger_fullstat_v2_l1/prompt_normalization_audit.json"))
r={x["tag"]:x for x in a["rows"]}
print("eplus ΣTT", r["eplus"]["tt_sum_s"], "rate/ev", r["eplus"]["rate_hz_per_event"])
print("eplus 80 ev =", 80*r["eplus"]["rate_hz_per_event"], "(产物 0.0543377)")
print("prompt 合计 =", 80*r["eplus"]["rate_hz_per_event"]+6*r["n"]["rate_hz_per_event"]+1*r["muplus"]["rate_hz_per_event"])
print("每行 rate*ΣTT:", {k:v["rate_times_tt_sum"] for k,v in r.items()})
EOF
```

### A2. 两分支差异 = 仅延迟 (prompt/signal 相同, Z∝S/√B)
```bash
for L in fullstat_v2 fullstat_v2_exactpos; do
  echo "== $L"; python3 -c "import json;d=json.load(open('outputs/reports/v3p5_fullstat_performance_w2_closure_${L/fullstat_v2/}'.rstrip('_')+'...'))" 2>/dev/null
done
# 直接读两份 closure summary:
python3 - <<'EOF'
import json
v2=json.load(open("outputs/reports/v3p5_fullstat_performance_w2_closure_20260612/v3p5_fullstat_performance_w2_closure_summary.json"))["headline"]
ex=json.load(open("outputs/reports/v3p5_fullstat_performance_w2_closure_fullstat_v2_exactpos_20260613/v3p5_fullstat_performance_w2_closure_summary.json"))["headline"]
import math
print("B v2/ex:", v2["w2_step05_background_cps"], ex["w2_step05_background_cps"])
print("delayed v2:", float([s for s in v2["w2_stream_split"] if s["stream"]=="delayed"][0]["rate_hz"]))
print("delayed ex:", float([s for s in ex["w2_stream_split"] if s["stream"]=="delayed"][0]["rate_hz"]))
print("Z check 5.70221*sqrt(Bv2/Bex)=", 5.70221*math.sqrt(v2["w2_step05_background_cps"]/ex["w2_step05_background_cps"]), "vs", ex["w2_step08_Z20d_at_1e_4"])
EOF
```

### A3. 延迟源模型对照 (RadialProfileBeam vs PointSource)
```bash
grep -hoE "Beam +[A-Za-z]+" runs/step02_delay_fix_v3p5_centerfinger_fullstat_v2/activation_decay_day15_groundstate_fixed.source | sort | uniq -c        # 4653 RadialProfileBeam
grep -hoE "Beam +[A-Za-z]+" runs/step02_delay_fix_v3p5_centerfinger_fullstat_v2_exactpos/activation_decay_day15_groundstate_fixed.source | sort | uniq -c # 5000 PointSource
cat runs/step02_delay_fix_v3p5_centerfinger_fullstat_v2_exactpos/exactpos_delayed_source_manifest.json | python3 -c "import json,sys;d=json.load(sys.stdin);print('blocks',d['n_pointsource_blocks'],'seed',d['seed'],'sampling_rows',d['sampling_rows'],'sum_flux',d['sum_flux_check_Bq'])"
```

### A4. 双轨 + 悬空指针 + git 跟踪
```bash
# 双轨:
grep -rn -E "0\.0729576|0\.0624651|5\.70221|6\.15522|6\.82301|6\.32564" core_md outputs/reports | grep -iE "current|authority|headline|closure"
# 悬空指针扫描: 见本报告 §4.1 (脚本枚举 core_md/*.md 反引号路径并测 os.path.exists)
# 当前头条是否进版本库:
git check-ignore outputs/reports/v3p5_fullstat_performance_w2_closure_fullstat_v2_exactpos_20260613/v3p5_fullstat_performance_w2_closure_summary.json   # -> ignored
git ls-files --error-unmatch code/tools/build_v3p5_exactpos_delayed_source.py 2>&1   # -> 未跟踪
git status --short | wc -l
```

### A5. I-128 锚重算
```bash
python3 - <<'EOF'
import re
src="runs/step02_delay_fix_v3p5_centerfinger_fullstat_v2/activation_decay_day15_groundstate_fixed.source"
i128=set(); flux={}
for s in open(src,errors='ignore'):
    s=s.strip()
    m=re.match(r'^(S_\S+)\.ParticleType\s+(\d+)',s);
    if m and m.group(2)=='53128': i128.add(m.group(1))
    m=re.match(r'^(S_\S+)\.Flux\s+([-+0-9.eE]+)',s)
    if m: flux[m.group(1)]=float(m.group(2))
print("I-128 Bq:", sum(v for n,v in flux.items() if n in i128), "(锚 66.00180110381)")
print("ALL  Bq:", sum(flux.values()), "(manifest 85.63669586528)")
EOF
```

### A6. validator 实跑
```bash
python3 code/tools/validate_v3p5_fullstat_r2.py
python3 code/tools/validate_v3p5_exactpos_closure.py --label fullstat_v2_exactpos
```
