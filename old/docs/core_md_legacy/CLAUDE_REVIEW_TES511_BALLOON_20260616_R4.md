# Claude Review R4: TES_511_Balloon 修复后复审报告

Date: 2026-06-16 (第四轮)
Reviewer: Claude (Opus 4.8)
Scope: 对照 `CLAUDE_REVIEW_TES511_BALLOON_20260614.md` (R3) 的三个 P1, 逐项核实其处置;
并对 R3 之后新立/新增的工作做独立数值复审 ——
(a) `fullstat_v2_exactpos` 的 M/seed 收敛闭包 + 今日 M-sampling 审计;
(b) **全新 BGO 等衰减材料链** (`Bgo_sample/` + Step05–Step08 + BGO-vs-CsI 对比);
(c) **全新 step11 上游光学自本底分支**;
(d) NIMA 论文 (en/zh draft) 的数字一致性。
Mode: **只读评审**。本报告是本轮唯一新增文件 (按用户要求落在 `core_md/`)。
所有关键数字均直接从盘上产物 (summary JSON / source / manifest) 重算, 附录 A 给出复现命令。

> Token 规划说明: 本轮按"风险×是否会被引用"排序, 深查三类新权威 (BGO 链 / exactpos 收敛 /
> 论文数字) 与 R3 三个 P1 的闭环, 对长尾 (悬空指针) 做抽样扫描而非逐条; 大 JSON 用字段抽取
> 而非全文读取以控预算。未做: 重跑任何 Cosima 输运 (评审为只读), step11 `0.25` 产额因子的
> 代码级溯源 (该分量对头条为零, 见 §4)。

---

## 0. 一句话总结

**R3 的两个核心 P1 (权威双轨、exactpos 收敛) 已实质解决且数值经得起重算; 本轮三类"新权威"
(BGO 材料链 / exactpos 收敛 / 论文头条) 全部独立复算自洽, 未发现第四起 ×8/等效时间家族 bug
—— 这是连续第二轮"新权威干净"。** 论文 (NIMA draft) 数字与权威逐项吻合且自觉度高
(头条用 exactpos, 保守 fullstat_v2 仅作明确标注的 cross-check 行, BGO 与 step11 都按边界收口)。

仍需处置的问题集中在治理与少量模型刻画, **均非计数错误**:

1. **(P1, 递归) 版本控制又没兜住最新一波权威**: R3 点名的 exactpos 闭包/收敛目录这次确实
   进了 `.gitignore` 白名单并提交了, 但**紧接着的新一波 (BGO 对比报告、今日 M-sampling 审计、
   整个 step11、论文图表、3 个 step03 新工具、Project_Memory/workflow/论文的 working-tree 改动)
   又全部落在 git 之外**。同一根因 (R3 P1#3) 复发。
2. **(P2) BGO-vs-CsI "matched" 对比的 veto 阈值不对称**: CsI 在 50 keV、BGO 在 70 keV, CsI 未在
   70 keV 重跑。方向上对 BGO-更优的结论是保守的 (阈值越低 veto 越狠、本底越低, CsI@50 已占便宜),
   但"matched"措辞下应显式说明或做对称对照。
3. **(P2, 四连) 悬空指针仍未清**: core_md 反引号路径死链不降反升 (本轮扫描 161 处, 其中含 R3
   点名仍在的 `day15_complete_report/*`、`../new_geo_re_2` 等; 另有相当一部分是 git-ignored
   可再生产物, 需区分对待)。

其余为 P3 刻画/溯源 (exactpos 延迟分量收敛口径、BGO 延迟 TE 溯源、step11 `0.25` 因子)。

---

## 1. R3 三个 P1 的处置核实 (逐项, 盘上重算)

| R3 P1 | 状态 | 本轮核实 (盘上重算) |
| --- | --- | --- |
| **#1 权威双轨 (fullstat_v2 vs exactpos 两套 "current")** | **DONE ✓ 已去双轨** | 全仓库口径已统一: `fullstat_v2_exactpos` = **current rate-level authority**, `fullstat_v2` = **conservative radial-profile baseline cross-check**。一致出现在 `README.md:11-12,19,72-89`、`Project_Memory.md:177-188,991-997`、`workflow.md:4-6,27-29,188`。R3 指出的"两处并存 current"已消除: README 现把 0.0729576 明确置于 fullstat_v2/保守标题下 (`README.md:991` "Conservative radial-profile fullstat_v2 W2 baseline is 0.0729576")。**论文亦同口径** (§5)。 |
| **#2 exactpos support-size 收敛检验 + 抽样断言** | **DONE ✓** | `outputs/reports/v3p5_exactpos_convergence_20260614/`: 4 个 **transport-backed** case (M=5000 两 seed + 20000 + 50000), 状态 `PASS_EXACTPOS_TRANSPORT_CONVERGENCE` → `PROMOTE_EXACTPOS_TO_CURRENT_RATE_AUTHORITY`。我重算: W2 本底相对极差 **1.12%**、Z20d **0.55%** (均 < 5% 门槛)。今日 (`m_sampling_audit_20260616/`) 又补了 R3 要的抽样断言: 每 case `flux rel.delta=0`、`match frac=1.0`、top20 物种 χ² (10.4–22.5)、missed-ZA/activity 记账 (M5000 漏 0.39 Bq=0.46%, M50000 漏 0.057 Bq=0.067%)。**caveat 见 §3**。 |
| **#3 提交 exactpos 全套 + 让 authority 产物入库** | **部分 ✓, 但根因复发 (转入 §6 P1)** | R3 点名项已修: `.gitignore` 现显式 `!` 白名单 `..._w2_closure_fullstat_v2_exactpos_20260613/`、`..._boundary_closure_..._20260613/`、`..._exactpos_convergence_20260614/`; 我实测这三者及 `Bgo_sample/closure_summary.json` 均 **TRACKED**。BGO 链 digest 也已提交 (commits `8a6d7dc`/`f9f6a92`/`04535cd`)。**但新一波又外溢**: `bgo_sample_csi_comparison_20260615/` (对比报告本体) **IGNORED**、`m_sampling_audit_20260616/` **IGNORED**、`step11_upstream_optics_background/` 整目录 **UNTRACKED**、`paper_source_figure_table/` 与 3 个 step03 工具 untracked、`Project_Memory/workflow/`论文 working-tree 改动未提交 (git status 共 21 项)。 |

> 小结: R3 的 **#1 (双轨) 和 #2 (收敛) 真正闭环, 数值复核通过**; #3 是"修了被点名的、又漏了新长出的",
> 属同一治理根因复发, 我把它升回本轮 P1 (§6)。

---

## 2. 本轮重点: 全新 BGO 等衰减材料链独立数值复审 (×8 家族排查)

BGO 链 (`Bgo_sample/` + `outputs_bgo_sample_fullstat_v2_exactpos`) 是 R3 之后**体量最大的新权威**:
把 CsI 探测器换成等衰减 BGO 主动屏 (高 Z/高密 → 更薄壁达到同衰减), 走**与 CsI exactpos 完全
同一条 Step05–Step08 硬窗计数链**做材料对比。复审重点照例是归一化/等效时间。

### 2.1 归一化与活度守恒 (无 ×8)

- **prompt 归一与 CsI 同构**: BGO Step05 `normalization.prompt_rate_rule = "per-tag event rate =
  1 / sum(TT_s ...)"`, `prompt_time_s = 184.220098` (与 CsI 逐位相同), `prompt_normalization_audit
  = PASS, problems=[]`。即 R2 修好的 per-tag `1/ΣTT` 规则被 BGO 分支原样复用, **prompt 无 ×8 风险**。
- **延迟活度精确守恒**: `step02_fullstat_v2_exactpos_summary.json`: `fixed_total_activity_Bq =
  23.5704741821545`, `sum_flux_check_Bq = 23.5704741821545`, `sum_flux_abs_delta_Bq = 0.0`;
  5000 块 × `flux_per_pointsource_Bq 0.0047140948364309` = 23.5704741821545 ✓ (逐位)。
- **活度量级物理自洽**: BGO 23.57 Bq vs CsI 85.64 Bq —— 差异主因是 **BGO 无碘 → 无 I-128**
  (CsI 的 66 Bq 锚来自 I-128); 去碘后剩 ~20 Bq 量级合理。这是一个干净的 sanity check。
- **延迟率走 events/TE (Cosima live-time)**, 单 run 无 replicas, 与 exactpos 同口径。

### 2.2 BGO-vs-CsI 对比的 ratio 全部重算吻合

对比 (`bgo_vs_csi_summary.json`) 两侧均为 **exactpos + Step08 time-dependent mission-mean**,
是 apples-to-apples。我重算三个头条 ratio:

| 量 | BGO | CsI (exactpos) | ratio 重算 | 报告值 | 一致 |
| --- | ---: | ---: | ---: | ---: | :--: |
| Step06 W2 mission-mean 本底 cps | 0.05783299834664 | 0.06268353697712 | **0.922619** | 0.922619 (−7.738%) | ✓ |
| Step08 W2 Z20d | 6.43474787077 | 6.15522221914 | **1.045413** | 1.04541 (+4.541%) | ✓ |
| Step08 W2 F3(20d) | 4.6621873308e-5 | 4.8739101420e-5 | **0.956560** | 0.95656 (−4.344%) | ✓ |

注意分母用的是 CsI **Step06 dt-weighted mission-mean** 0.0626835 (≠ Step05 direct 0.0624651),
所以 −7.738% 才对得上; F3/Z20d 分母用 CsI exactpos Step08 数 (4.8739e-5 / 6.15522), 与论文头条
同源。**对比链内部一致, 无新计数 bug。**

### 2.3 发现: "matched" 对比的 veto 阈值不对称 (P2)

`comparison.rows`: **CsI `active_veto_threshold_keV = 50.0`, BGO = 70.0**。即被称作 "matched
exact-position comparison" 的两材料**用了不同的主动屏 veto 阈值**, 且 CsI 未在 70 keV 重跑。

- 物理上各取本材料设计阈值可辩护 (BGO 光产额低 → 阈值更高); 且 BGO 的 threshold replay
  (extended closure) 显示 50/60/70/80 keV 下 Z20d=6.436/6.435/6.435/6.435 几乎不动, 所以阈值
  对 BGO 侧贡献极小, 7.738% 主要来自材料/衰减差异。
- **方向上对结论保守**: 阈值越低 veto 越狠 → 本底越低, CsI@50 已经占了"更低本底"的便宜;
  若把 CsI 也提到 70 keV, CsI 本底会上升、BGO/CsI 比会更低于 1, BGO 反而显得更优。
- 但"matched"措辞 + 只对 BGO 做了阈值扫描 (CsI 没有), 严格说不是同阈值对照。**建议**: 要么补
  CsI@70 (或 BGO@50) 一行以隔离"阈值 vs 材料", 要么在论文 Table caption 显式写明"各取本材料设计
  veto 阈值 (CsI 50 / BGO 70 keV)"。

### 2.4 BGO 延迟等效时间溯源差比 CsI 大 (P3)

`1e6/TE`: CsI = 86.727 Bq vs fixed 85.637 → **+1.27%**; BGO = 25.218 Bq vs fixed 23.570 → **+6.99%**。
两者同机制 (Cosima live-time 含子核衰变, R3 §4.3 已记), 但 **BGO 差比 ~5.5×**。因延迟率
= events/TE 用的就是 Cosima 实测 TE, 分子分母同含子核 → **率自洽、对比无偏**; 仅是 TE↔fixed-activity
的标签语义差更大。BGO 延迟占总本底比 CsI 更小, 故对头条影响 <1%。**建议**在 step02 summary 记一句
TE 来源 (含子核) 以免 BGO 的 7% 被误当归一化误差。

---

## 3. exactpos 收敛复核与残留 caveat (P3)

收敛检验在**本底/Z 层面**确实通过 (§1 #2)。但需对外/论文显式声明它**不是延迟分量层面的收敛**:

- 延迟分量本身 4-case 相对极差 = **0.187**, 贴着 0.20 门槛; 且**同 seed (260613) 随 M 单调上爬**:
  M=5000→20000→50000 = 0.003382→0.003643→0.003898 cps (**+15.2%**)。即 M=50000 仍可能略欠采样,
  延迟率尚未严格 plateau。
- 之所以不影响头条: 延迟仅占总本底 **5.4%** (0.003382/0.0624651, 论文 L466 也用 5.4%, 我重算吻合),
  故延迟 15–20% 的残差 → 总本底 <1% → Z20d 0.55%。这是"收敛在被稀释后的量上成立"。
- missed-nuclide 审计佐证同一图景: M 越大漏的活度越少 (0.46%→0.067%), 主导漏项是 `n` 家族在
  `CsI active shield` 的稀有高产体素 —— 正是 R3 担心的 rare-but-high-yield, 现已量化且影响可忽略。

**建议 (P3)**: 收敛报告/论文里加一句"收敛系在 W2 总本底与 Z20d 层面成立; 延迟分量自身相对极差
0.187 (近 0.20 门槛) 且随 M 轻微上爬, 因其仅占本底 5.4% 故不改头条"。目前论文 L466 已含
"M=5000 足够 for current hard-window rate claim", 措辞基本到位, 仅缺延迟分量未严格收敛的明示。

---

## 4. step11 上游光学自本底新分支评估 (新, 收口诚实)

这是一条**此前缺失的计算**: 上游 Laue 透镜硬件**自身**产生的 prompt/延迟本底 (区别于 Step04/09
只输运聚焦 511 信号)。`status.json` + `README.md` 状态收口清楚:

- **全粒子 prompt + activation 输运: 已闭** (instant/buildup 各 68/68 jobs 零失败, 各 25,210,216 primaries;
  几何 = 探测器 + 10 m 上游 Ge 等质量代理, 源面 r=1060 cm)。
- **Ge-proxy 延迟 selected-rate: 已闭, 结果为零**: 仅 2 个真位 RPIP 记录 (Ga-70/Ga-73), 日 15 活度
  0.42567 Bq; 20000 触发延迟输运 → **W2 选后 0 事件**; 95% 零计数上限 1.2534e-4 s⁻¹ ≈ 主本底
  0.0624651 的 **0.20%** → 不改头条。
- **prompt 自本底 selected-rate: 仍 OPEN** (合并 prompt SIM 混入了普通探测器/低温恒温器大气 prompt,
  需 provenance 隔离或减除) —— **正确地排除在主预算外**。

评价: 范围界定与上界框定都诚实, Ge proxy 明标"等质量代理, 待换真透镜瓦片/支撑硬件"。**论文已把
它折入** (en.tex L213-215 描述 + limitation #5, §5)。

发现/提醒:
- **(P1 归口 §6) 整目录 UNTRACKED**: 新工具/status/证据均未进 git。
- **(P3) `target_inventory.scaled_production_yield = 0.25` 因子未做代码级溯源**: 在 ×8 历史的项目里,
  任何 1/4 这类裸因子都值得验明出处。**但**: 该分量 W2 贡献为零、即便活度 ×4 (上游 1000 cm、立体角
  极小) 探测器率仍 ~0, 故**对任何头条零影响**; 列 P3 仅作归一化卫生。
- **(note) 延迟清单仅 2 同位素 / 薄 MC**: 因结论是"上限"框定, 鲁棒性不依赖清单完整度。

---

## 5. NIMA 论文 (en/zh draft) 数字一致性核实

论文是本轮最高风险的一致性面 (会被对外引用)。逐项核对均**通过**:

- **头条 = exactpos**: abstract/正文用 `B/S=0.0624651/0.00118117 cps`、`Z20d=6.15522`、`T3=4.73758 d`、
  `F3(20d)=4.87391e-5`、`1Ms=6.32564e-5`、收敛 `1.119%/0.551%`、`Aeff(511)=20.08476 cm²` —— 与权威逐位一致。
- **保守数无双轨泄漏**: `0.0729576/5.70221` 仅出现在 results 表的一行, 标签 "Radial-profile hard
  window … radial-profile", 表 caption 明写"a conservative baseline cross-check" (en.tex L339,346,366)。
  这是 R3 #1 想要的正确呈现 (不是两个 "current" 打架)。
- **BGO 收口为受限子节** (`\subsection{Equal-attenuation BGO active-shield control}`, L412-443 + 表):
  明标 "hard-window material-control result only", limitation #7 "CsI exact-position chain remains the
  primary result"。BGO 70 keV 阈值已写出 (但未点出 CsI 50 vs BGO 70 的不对称, 见 §2.3)。
- **step11 已折入** (L213-215): Ga-70/Ga-73、0.425674 Bq、0 selected W2、95% UL 1.25e-4 = 本底 0.20%、
  prompt 自本底仍 open —— 与盘上 status.json 逐位一致。
- **delayed 5.4%** (L466) 重算吻合 (§3)。
- 项目自带 `manuscript_review_20260615.md` 自觉度高 (BGO 不替头条、sidecar 标 base 分支、annular 标
  fixed-template 非 publication likelihood), 并记录 en/zh 均编译通过 (20/19 页)。

**论文仍开项** (项目自己已列, 我认同, 非本轮新增): 作者/单位/CRediT/致谢/archive id 占位待填;
外部文献需逐条核对原始来源; 若干 overfull 表格 layout。这些是投稿前事项, 不影响物理数字。

---

## 6. 仍未决 / 本轮新发现

### 6.1 (P1, 递归) 版本控制又没兜住最新一波权威

R3 #3 的根因——"换权威这一步没留 git diff"——**模式复发**。已修被点名项, 但新长出的权威产物再次外溢:

| 产物 | 角色 | git 状态 |
| --- | --- | --- |
| `outputs/reports/bgo_sample_csi_comparison_20260615/bgo_vs_csi_{summary.json,report.md}` | BGO 材料对比**本体** | **IGNORED** (仅手抄 digest `Bgo_sample/closure_summary.json` 入库) |
| `outputs/reports/m_sampling_audit_20260616/` | R3 #2 要的抽样断言产物 | **IGNORED** |
| `stepwise_maintenance/step11_upstream_optics_background/` | 全新上游自本底分支 (代码+status+证据) | **UNTRACKED** (整目录) |
| `core_md/balloon511_nima_latex_drafts/paper_source_figure_table/` | 论文图/表源 | UNTRACKED |
| `stepwise_maintenance/step03_delay_source/code/build_{m_sampling_audit,step03_exactpos_distribution_figure,step03_exactpos_sampling_necessity}.py` | 3 新工具 | UNTRACKED |
| `core_md/Project_Memory.md`、`core_md/workflow.md`、`balloon511_nima_draft_{en,zh}.tex` 等 | 本轮权威/论文改动 | 已改未提交 (working tree) |

**建议 (P1)**: (a) 立即提交上述 working-tree 改动 + 3 工具 + step11 + 论文图表; (b) **把 `.gitignore`
从"逐目录 `!` 白名单"改成规则白名单**——忽略大产物 (`*.sim.gz`/`*.dat`/`*.pkl`/png) 但默认放行
`*_summary.json`/`*_report.md`/`*.csv`/`status.json`, 这样下一波 authority 的轻量产物自动入库, 根治复发;
(c) 提交信息点名 "BGO 材料链 (Z20d 6.43 vs CsI 6.16, F3 −4.3%) + step11 Ge-proxy 延迟上限 0.20% +
exactpos M/seed 收敛 promote"。

### 6.2 (P2) BGO/CsI veto 阈值不对称 —— 见 §2.3。

### 6.3 (P2, 四连) 悬空指针仍未清

core_md/*.md 反引号路径存在性扫描 (附录 A4): **161 处死链** (Project_List 79 / Project_Memory 42 /
README 23 / workflow 14 / ROUTE_B 3)。**需分两类看**:
- 一部分是 **git-ignored 可再生产物** (`stepwise_maintenance/step*/outputs/...`、`outputs/reports/...`、
  trailing-slash 目录名如 `profiles/`、`__pycache__/`) —— 干净 checkout 下本就不存在, 文档作"可重建"
  引用, 危害低;
- 另一部分是 **真死链** (R3 点名仍在的 `outputs/reports/day15_complete_report/*`、`../new_geo_re_2`、
  `science_511_ADR_100k/*`、`step03_delay_source/outputs/*` 旧无后缀路径等) —— 对新会话仍是陷阱。

四轮 (R1/R2/R3/R4) carryover。**建议**: 至少对 README/Project_Memory/workflow 三个活跃文档批量改指
旧仓库绝对路径并加 `(superseded/regenerable)`, 或删除已无意义条目; Project_List 作 legacy 可整体标注。

### 6.4 (P3) 三个刻画/溯源点 —— 见 §3 (收敛口径)、§2.4 (BGO TE 溯源)、§4 (step11 0.25 因子)。

---

## 7. 复核通过项 (credit, 全部本轮重算/核实)

- ✓ **未发现第四起 ×8/等效时间家族 bug**: BGO prompt 走 per-tag `1/ΣTT` (audit PASS)、BGO 活度
  Δ=0 守恒、延迟走 events/TE、对比三 ratio 逐位重算吻合、step11 延迟为零无归一化可错——**连续第二轮
  新权威干净**。
- ✓ R3 #1 权威双轨**已去**, 全仓库 + 论文口径统一 (exactpos=authority / fullstat_v2=conservative)。
- ✓ R3 #2 exactpos 收敛**已做**且 PASS (本底 1.12% / Z20d 0.55%), 抽样断言 (χ²/missed-ZA/活度守恒) 已补。
- ✓ BGO 材料链 Step05–Step08 与 CsI **apples-to-apples** (同 exactpos、同 Step08 mission-mean), Z20d
  +4.5% / F3 −4.3% 的对比结论数值自洽。
- ✓ step11 上游自本底分支**范围界定诚实**: 延迟 0.20% 上限不改头条, prompt 自本底正确排除在主预算外。
- ✓ 论文头条数字与权威逐位一致; 保守数无双轨泄漏; BGO/step11 均按边界收口; manuscript_review 自觉度高。

---

## 8. 优先级清单 (R4)

| 级别 | 事项 |
| --- | --- |
| **P1** | **根治 git 外溢 (递归)**: 提交 BGO 对比报告本体 + m_sampling_audit + 整个 step11 + 论文图表 + 3 step03 工具 + working-tree 改动; 把 `.gitignore` 改为"放行 `*_summary.json`/`*_report.md`/`*.csv`/`status.json`"的规则白名单, 使下一波 authority 轻量产物自动入库 (§6.1) |
| P2 | BGO-vs-CsI veto 阈值对称化: 补 CsI@70keV (或 BGO@50keV) 隔离阈值 vs 材料, 或论文表 caption 显式写明"各取本材料设计阈值 (CsI 50 / BGO 70)" (§2.3) |
| P2 | 悬空指针四连清理: README/Project_Memory/workflow 真死链改指/标退役, 区分 git-ignored 可再生 vs 真死 (§6.3) |
| P3 | 收敛口径明示: 声明收敛系在 W2 本底/Z20d 层面成立, 延迟分量自身相对极差 0.187 (近门槛) 且随 M 轻升, 因占本底 5.4% 不改头条 (§3) |
| P3 | BGO 延迟 TE 溯源记一句 (Cosima live-time 含子核, 1e6/TE 比 fixed 高 7.0% vs CsI 1.3%) (§2.4) |
| P3 | 验明 step11 `scaled_production_yield=0.25` 因子出处 (零头条影响, 归一化卫生) (§4) |
| **P2** | **(续审新增) 信号选择 keep-policy 抬高 Z, "conservative" 方向存疑** —— 给出 keep-vs-reject 的 Z 差 (§9.1) |
| **P2** | **(续审新增) 头条 T_atm=0.739(近垂直) 与背景 lat 34°N + 银心高天顶角不自洽** —— 明确头条源天顶角并与地理位置/侧入设计自洽 (§9.2) |
| **P2** | **(续审新增) tracked 收敛 authority `w2_signal_cps_at_1e_4=7.957e-5` 错标** (低 14.84× = 丢 Aeff×T_atm), 改名或填物理值 (§9.3) |
| P3 | (续审新增) f10m optics authority 的 `science_policy` 仍写 "f9m remains the current published headline", 与现状(已 f10m)矛盾, 更新 promote 状态 (§9.4) |
| — | (论文投稿前, 项目已列) 填作者/单位/CRediT 占位 + 逐条核对外部文献 + 修 overfull 表格 (§5) |

---

## 9. 续审 (信号侧深挖): 四轮从未审过的"信号归一化链"

R1–R4 全部聚焦**本底** (×8 家族)。应用户"继续 review 找风险"要求, 本次深挖**信号侧** ——
`signal = flux × Aeff × T_atm × ε_select`。一处错会同比例搬动**所有** F3/Z (相对对比仍对, 故前几轮看不见)。
核心链复核**通过** (见 §9.5 credit), 但挖出 3 个 P2 + 1 个 P3, 均关乎**头条灵敏度是否被高估**。

### 9.1 (P2) 信号选择 "keep policy" 实际**抬高** Z, 论文 "conservative" 措辞方向存疑

头条信号效率来自 Step05 `science` 流的 `side_compton_fov_pass_rate` (W2 ε≈0.7957)。盘上分类计数
(`outputs_v3p5_centerfinger_fullstat_v2_exactpos_l1` step05 summary, broad 480–550 窗):

| 流 | keep(重建模糊,保留) | single(单点,保留) | veto(FoV不符,拒) | keep 占保留比 |
| --- | ---: | ---: | ---: | ---: |
| science(信号) | 12120 | 17530 | 646 | **40.9%** |
| prompt 本底 | 39 | 70 | 15 | 35.8% |
| delayed 本底 | 10 | 34 | 11 | 22.7% |

论文 (en.tex L312, L366 + limitation #4) 说"无有效重建的事件按**保守**策略保留, 故不依赖激进的
reconstruction-failure veto"。但**数字方向相反**: 若真按 limitation #4 设想的激进 veto 拒掉 "keep" 类,
信号掉到 ~59%、本底掉得**更少** (信号 keep 占比 40.9% > prompt 35.8% > delayed 22.7%) → 净 Z
**下降 ~27%** (broad-window proxy `S/√B`: keep 2.857 → reject 2.098, 比 0.734)。**即 keep 是更高 Z
的(乐观侧)选择, 不是 Z 的保守下界。** "conservative" 仅在"不靠激进本底 veto 人为清污"这一轴成立。
**建议**: 论文给出 keep-vs-reject 的 Z 差并明示方向, 避免读者把"conservative selection"误读为"净灵敏度
的保守界"。(选择本身对三流**对称施加**, 自洽无 bug; 这是措辞/口径问题, 非计数错。)

### 9.2 (P2) 头条 T_atm 用近垂直 0.739, 与背景地理位置 + 银心高天顶角不自洽

`science_physical_normalization`: 信号乘 `T_atm = 0.7390424` (近垂直)。boundary closure 的 45° slant
sidecar: `T_slant = 0.6520343`, `signal_scale = 0.88227` → **Z20d 6.155→5.425 (−11.9%)、F3 4.874e-5→
5.530e-5 (+13.4%)**。这是 disclosed sidecar (R3 §4.2)。但本次发现更深一层的**自洽性问题**:

- 背景 EXPACS 环境 (`fig_expacs_fullsphere_flux_summary.json`) 定在 **lat 34°N / lon 100°E** (中国球区)、
  alt 38 km、Rc 11.6 GV。
- 论文科学目标是**银河系 511 / 银心** (dec ≈ −29°)。从 lat 34°N, 银心中天仅 ~**27° 仰角 = ~63° 天顶角**,
  sec(63°)≈2.2 → 真实 T_atm 可能 ~0.51, **比 45° sidecar (0.652) 还低**。
- 而 instrument 恰是 **45° 侧入 (side-entry) 设计** —— 很可能正是为侧看低仰角目标; 那么相关 T_atm 就该是
  slant 而非垂直。**头条用垂直 T 与"侧入看银心"的设计理由自相矛盾。**

**建议**: 论文**显式声明头条假设的源天顶角**, 并使之与 (a) 背景地理位置 lat 34°N、(b) 银心可达仰角、
(c) 45° 侧入设计 三者自洽; 若侧看是常态, 头条应改用 slant T (Z 降 ~12%) 或至少把垂直版明标为"天顶最优上界"。
(注: lat/lon 也可能只是代表性大气环境占位 —— 但正因如此, pointing 假设必须写明。)

### 9.3 (P2) git-tracked 收敛 authority 里 `w2_signal_cps_at_1e_4` 错标 (低 14.84×)

`outputs/reports/v3p5_exactpos_convergence_20260614/v3p5_exactpos_convergence_summary.json` 四个 case 均有
`"w2_signal_cps_at_1e_4": 7.957466258001846e-05` —— 比物理信号 `0.00118117` 低 **14.84×, 恰 = Aeff×T_atm
(20.085×0.739)**。即该字段是 `ε×flux` 的单位面积代理, 丢了光学有效面积与大气透过。**当前未泄漏**
(README/workflow/论文头条都用 0.00118117, 该文件自己的 Z20d/F3 也是用正确信号算的, 互恰); 但:
- 这是 README:38 / workflow:19 **引为 authority** 的 git-tracked 文件里一个**名实不符**的字段;
- `manuscript_review` 已警觉 "unit-injection bookkeeping rates should not be quoted as physical signal rates"
  —— 说明项目知道这个坑, 但字段仍以 `w2_signal_cps_at_1e_4` 之名留存, 任何自动读取该键的新会话/脚本
  会取到低 14.84× 的"信号"或据其算出废 Z。
**建议**: 字段改名 (如 `w2_signal_unit_area_proxy_cps`) 或直接填物理值 0.00118117, 二选一。

### 9.4 (P3) f10m optics authority 的 science_policy 陈旧

`optics_aeff_authority_f10m_a1.json` 的 `science_policy` 仍写 "f9m remains the current published headline
until downstream Step09/Step07/Step08 are rerun"。但下游 Step09/07/08 **已用 f10m 重跑** (exactpos 全链
profile=`f10m_a1_v3p5`)、论文头条**已是 f10m** (Aeff 20.085)。gating 条件已满足, f9m 已被取代 —— 仅文本
未更新。**建议**更新该文件 promote 状态, 以免被引为"f9m 才是 headline"。

### 9.5 信号链复核通过项 (credit)

- ✓ 归一化链 `signal = flux×Aeff×T_atm×ε_select` 因子分解正确、**无重复计数**: Aeff 已含衍射×within-Be,
  ε_select (Step09→Step05) 只算探测器+选择, 二者不重叠。
- ✓ **Aeff = 20.085 重算吻合** = 81 cm²(25 瓦 18mm²) × 0.24837(B-FULL 衍射) × 0.99834(within-Be); 衍射
  效率 24.8% vs analytic 25.7% (略保守, 在 0.01 strict gate 内); 在设计 gate [19.4,21.4] cm² 内; 3 seed
  pstdev 0.221 (1.1%)。
- ✓ 选择对 signal/prompt/delayed **对称施加** (同 keep/single/veto 分类); 信号高效率(不被主动屏 veto,
  survival 1.0) + 本底低效率(prompt veto 后仅存 29.5%, Compton/FoV 再 ×2.58 拒本底) 是**设计目标非 bug**。
- ✓ Z↔F3 **互恰** (F3 = ref_flux×3/Z20d, 逐位); 窄窗信号 ≈ 宽窗信号 (0.00118117 vs 0.0011833, 因 511 线
  极窄 + TES 微量能器分辨, 信号几乎全落窄窗) 物理正确。
- ✓ EXPACS 绝对通量**量级 sanity 合理** (gamma 4.80 / n 0.46 / e⁻ 0.20 / e⁺ 0.12 / p 0.11 cm⁻²s⁻¹;
  down/up 物理; 20×0.6283 sr = 4π 自洽); **但未独立重算** (需 PARMA 模型) —— 这是全链唯一仅靠 sanity
  而非盘上重算的大块, 建议后续补一次 PARMA 独立交叉核对 (非阻塞)。

---

## 附录 A: 关键数字复现命令

### A1. R3 三个 P1 闭环 (权威口径 / 收敛 / git 白名单)
```bash
# 双轨已去: 三文档对 authority 的措辞应一致 (exactpos=authority, fullstat_v2=conservative)
grep -nE "current.*authority|conservative.*(radial|fullstat_v2)|PROMOTE_EXACTPOS" core_md/README.md core_md/Project_Memory.md core_md/workflow.md
# 收敛 PASS + promote:
python3 -c "import json;d=json.load(open('outputs/reports/v3p5_exactpos_convergence_20260614/v3p5_exactpos_convergence_summary.json'))['evaluation'];print(d['status'],d['authority_recommendation'],'bg_range',d['w2_background_cps_relative_range'],'Z_range',d['Z20d_relative_range'],'delayed_range',d['w2_delayed_cps_relative_range'])"
# git 白名单生效但新一波外溢:
git check-ignore outputs/reports/v3p5_exactpos_convergence_20260614/v3p5_exactpos_convergence_summary.json  # 应为空(=已放行/tracked)
git check-ignore outputs/reports/bgo_sample_csi_comparison_20260615/bgo_vs_csi_summary.json  # -> ignored
git status --short stepwise_maintenance/step11_upstream_optics_background | head
```

### A2. BGO 链无 ×8 (prompt 归一 + 活度守恒 + 对比 ratio)
```bash
python3 - <<'EOF'
import json
b5=json.load(open("stepwise_maintenance/step05_veto_time_axis/outputs_bgo_sample_fullstat_v2_exactpos_l1/step05_bgo_sample_l1_response_summary.json"))
print("BGO prompt rule:",b5["normalization"]["prompt_rate_rule"],"| time",b5["normalization"]["prompt_time_s"],"| audit",b5["normalization"]["prompt_normalization_audit"]["status"])
b2=json.load(open("Bgo_sample/step02_fullstat_v2_exactpos_summary.json"))
print("BGO act fixed/sumflux/delta:",b2["fixed_total_activity_Bq"],b2["sum_flux_check_Bq"],b2["sum_flux_abs_delta_Bq"],"| 5000*flux=",5000*b2["flux_per_pointsource_Bq"])
c=json.load(open("outputs/reports/bgo_sample_csi_comparison_20260615/bgo_vs_csi_summary.json"))["comparison"]
for k in ["step06_w2_mission_mean_background_cps","step08_w2_Z20d","step08_w2_F3_20d_ph_cm2_s"]:
    print(k,"ratio",c[k]["ratio_bgo_over_csi"],"reldelta",c[k]["relative_delta"])
EOF
```

### A3. veto 阈值不对称 + TE 溯源差 + 延迟收敛 caveat
```bash
python3 - <<'EOF'
import json
r=json.load(open("outputs/reports/bgo_sample_csi_comparison_20260615/bgo_vs_csi_summary.json"))["rows"]
print("veto keV CsI/BGO:",r["CsI_exactpos"]["active_veto_threshold_keV"],r["BGO"]["active_veto_threshold_keV"])
print("CsI 1e6/TE vs fixed:",1e6/11530.473845,85.63669586527698,"(+%.2f%%)"%(100*(1e6/11530.473845/85.63669586527698-1)))
print("BGO 1e6/TE vs fixed:",1e6/39653.861364,23.5704741821545,"(+%.2f%%)"%(100*(1e6/39653.861364/23.5704741821545-1)))
d=[0.003382341482601921,0.003643411242244815,0.0038976372073461713]  # seed260613 M=5k/20k/50k
print("delayed seed260613 5k->50k +%.1f%% (monotonic)"%(100*(d[2]/d[0]-1)))
EOF
```

### A4. 悬空指针扫描 (core_md/*.md 反引号路径存在性)
```bash
python3 - <<'EOF'
import re,os,glob
pat=re.compile(r'`([^`]+)`'); seen=set(); dead=[]
for d in glob.glob("core_md/*.md"):
  for ln,line in enumerate(open(d,errors='ignore'),1):
    for m in pat.findall(line):
      s=m.strip()
      if '/' not in s or any(c in s for c in ' =$*<>|'): continue
      if s.startswith(('http','python3','cosima','git ')): continue
      c=s.split(':')[0]; k=(d,c)
      if k in seen: continue
      seen.add(k)
      if not os.path.exists(c): dead.append((d,ln,c))
from collections import Counter
print("tested",len(seen),"DEAD",len(dead),"by doc",dict(Counter(os.path.basename(d) for d,_,_ in dead)))
EOF
```

### A5. step11 上游自本底上限
```bash
python3 -c "import json;d=json.load(open('stepwise_maintenance/step11_upstream_optics_background/status.json'));e=d['delayed_ge_proxy_selected_rate_evidence_2026_06_16'];print('Ge act',e['target_inventory']['total_activity_Bq'],'scaled_yield',e['target_inventory']['scaled_production_yield'],'W2 events',e['detector_response']['w2_side_compton_fov_pass_events'],'95% UL',e['detector_response']['zero_count_95_rate_s-1'])"
```

### A6. 信号侧 (§9): 链分解 / keep-vs-reject / T_atm / 错标字段
```bash
# 信号链分解 + Aeff 重算 + 收敛字段错标 14.84x:
python3 - <<'EOF'
import json
d=json.load(open("stepwise_maintenance/step05_veto_time_axis/outputs_v3p5_centerfinger_fullstat_v2_exactpos_l1/step05_v3p5_centerfinger_l1_response_summary.json"))
spn=d["science_physical_normalization"]; aeff=spn["aeff_511_cm2"]; T=spn["atmospheric_transmission"]["T_atm"]
print("signal = flux*Aeff*T*eps =",1e-4*aeff*T*0.7957496,"(headline 0.00118117)")
o=json.load(open("stepwise_maintenance/step04_opticsim/optics_aeff_authority_f10m_a1.json"))
print("Aeff = 81 * %.5f * %.5f = %.4f"%(o["run_summary"]["emergent_focal_diffraction_fraction"],o["focal_stats"]["within_be_fraction"],81*o["run_summary"]["emergent_focal_diffraction_fraction"]*o["focal_stats"]["within_be_fraction"]))
c=json.load(open("outputs/reports/v3p5_exactpos_convergence_20260614/v3p5_exactpos_convergence_summary.json"))["cases"][0]
print("conv field w2_signal_cps_at_1e_4 =",c["w2_signal_cps_at_1e_4"],"| 0.00118117/it =",0.00118117/c["w2_signal_cps_at_1e_4"],"= Aeff*T =",aeff*T)
EOF
# keep-vs-reject Z proxy (broad window class counts):
python3 -c "import math;sig,pr,de=0.7971716,0.07401652,0.0038159750;f=lambda K,S:S/(K+S);zk=sig/math.sqrt(pr+de);zr=(sig*f(12120,17530))/math.sqrt(pr*f(39,70)+de*f(10,34));print('Zkeep',round(zk,3),'Zreject',round(zr,3),'ratio',round(zr/zk,3))"
# 45deg slant 头条优化幅度:
python3 -c "import json;b=json.load(open('outputs/reports/v3p5_boundary_closure_fullstat_v2_exactpos_20260613/v3p5_boundary_closure_summary.json'))['atmosphere_45deg_los']['w2_hard_window'];print('vertical T',b['T_ref_vertical'],'slant T',b['T_ref_slant'],'Z45',b['Z20d'],'(headline 6.15522)','sig_scale',b['day15_signal_scale_slant_vs_vertical'])"
# 背景地理位置 vs 银心天顶角:
python3 -c "import json;e=json.load(open('core_md/balloon511_nima_latex_drafts/paper_source_figure_table/fig_expacs_fullsphere_flux_summary.json'))['environment'];print('lat',e['latitude_deg'],'lon',e['longitude_deg'],'-> GC dec -29 culminates at elev ~',90-abs(34-(-29)),'deg = zenith ~',abs(34-(-29))+ (90-90),'... zenith ~63deg, sec~2.2')"
```

---

## Codex follow-up 复查与处置记录 (2026-06-16)

### 复查结论

Claude R4 的主要技术判断里，以下三项是有效问题，已经按当前论文权威口径处置：

1. **BGO-vs-CsI 对比基准陈旧**：R4 第 2.2 节使用的是旧 CsI `fullstat_v2_exactpos` M=5000 对比值。当前论文主线权威已经是 `fullstat_v2_exactpos_m50000_s260613`，因此已更新 `code/tools/build_bgo_sample_csi_comparison.py`，重新生成 `outputs/reports/bgo_sample_csi_comparison_20260615/` 与 `Bgo_sample/closure_summary.json`/`CLOSURE_SUMMARY.md`。新状态为 `PASS_BGO_SAMPLE_VS_CSI_EXACTPOS_M50000_COMPARISON`。
2. **BGO 与 CsI 主动 veto 阈值不对称**：R4 指出的问题成立。当前不把它改写成“同阈值扫描”，而是明确定义为“材料设计阈值对比”：CsI 50 keV，BGO 70 keV。该边界已写入 BGO 对比报告、`Bgo_sample/README.md`、中英文论文 BGO 表 caption 与 limitations。
3. **M 抽样收敛口径需要收紧**：R4 对“不能把延迟子成分单独宣称严格收敛”的 caveat 成立。论文现在明确写成：延迟子成分相对极差为 0.187；收敛 claim 只限于总硬线窗本底和显著度层面，而不是延迟子成分单独率。

### 当前权威数字

当前 paper-facing CsI exact-position 权威为 M=50000、seed 260613：

- Step05 selected W2 background: `0.06298036183985109 s^-1`
- Step06 mission-mean W2 background: `0.06319228710672735 s^-1`
- Step08 `Z20d`: `6.130394687582996`
- Step08 `F3(20d)`: `4.893649027323553e-05 ph cm^-2 s^-1`

BGO 对当前 CsI M=50000 权威的匹配硬窗对比为：

- Mission-mean W2 background: BGO/CsI `0.915191`, relative `-8.481%`
- `Z20d`: BGO/CsI `1.04965`, relative `+4.965%`
- `F3(20d)`: BGO/CsI `0.952702`, relative `-4.730%`

因此，R4 正文第 2.2 节里的 `0.922619 / +4.541% / -4.344%` 已是历史基准，不应再作为论文口径引用。

M 抽样审计的当前结论为：

- exact-position weighted table activity equals fixed activity to floating-point precision: relative delta `-1.99e-15`
- M=50000 missed nuclide activity: `0.05745012620487438 Bq`, fraction `6.7086e-04`
- transported M/seed sweep: delayed W2 relative range `0.1874127`, total W2 background relative range `0.0111915`, `Z20d` relative range `0.00550844`

### 文件级处置

已更新的 active authority / paper-facing 文件：

- `code/tools/build_bgo_sample_csi_comparison.py`
- `outputs/reports/bgo_sample_csi_comparison_20260615/bgo_vs_csi_summary.json`
- `outputs/reports/bgo_sample_csi_comparison_20260615/bgo_vs_csi_report.md`
- `Bgo_sample/closure_summary.json`
- `Bgo_sample/CLOSURE_SUMMARY.md`
- `Bgo_sample/README.md`
- `core_md/README.md`
- `core_md/Project_Memory.md`
- `core_md/workflow.md`
- `core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.tex`
- `core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_zh.tex`

`.gitignore` 已补充白名单，使以下轻量 authority reports 可被 git 追踪：

- `outputs/reports/bgo_sample_csi_comparison_20260615/**`
- `outputs/reports/m_sampling_audit_20260616/**`

### 校验记录

本次复查后已通过：

- `python3 code/tools/build_bgo_sample_csi_comparison.py`
- `python3 -m py_compile code/tools/build_bgo_sample_csi_comparison.py`
- `git diff --check`
- `git check-ignore -v` 确认 BGO 对比报告和 M 抽样审计报告命中 `.gitignore` 的反向白名单
- active docs/reports 中检索旧 BGO 值 `7.738 / 4.541 / 4.344 / 0.922619 / 1.04541 / 0.956560` 无残留
- 中英文论文均用 `latexmk -g -xelatex -interaction=nonstopmode -halt-on-error` 重新编译通过
- TeX 日志未命中 `LaTeX Error`、`Undefined control sequence`、`Citation undefined`、`Reference undefined`、`Rerun to get cross-references`

### 仍保留的非阻塞项

1. R4 提到的 step11、论文图表、新工具、BGO 对比报告和 M 抽样审计报告已经作为轻量 authority artifacts 纳入本次提交；step11 目录里的原始 `sim.gz` 输运文件仍保持 ignored，不进入 git。
2. R4 提到的 core_md 反引号路径悬空扫描尚未逐条清理；这属于文档治理项，不影响本轮 BGO/M 抽样/论文数值口径。
3. BGO 分支仍未做 CsI/BGO 同一阈值 veto scan；当前论文已把它降格为“材料设计阈值对比”，不再把它表述为同阈值材料对照。
