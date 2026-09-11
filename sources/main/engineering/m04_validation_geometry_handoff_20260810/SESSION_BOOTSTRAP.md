# M04 数据模型校验与优化几何入稿交接

- 日期：2026-08-10
- 状态：`HANDOFF_READY__EXECUTION_NOT_STARTED`
- 适用仓库：`/home/ubuntu/TES_511_Balloon`
- 本文档的作用：供下一次独立会话直接接手，完成项目/论文复核、有限 M 抽样合理性校验、PARMA 大气 511 keV 线重建、优化几何证据闭合，以及后续双语论文增补。
- 本次交接没有启动新模拟，也没有修改 M04 论文或现有图件。

## 1. 一句话任务

在不触碰当前 M04 中英文稿、其第 3 节及此前文案和图片的前提下，先把延迟源的有限 M 抽样误差和大气 511 keV 线模型闭合，再用修正后的统一源模型验证最终优化几何；数据通过后，只在新复制的后继稿中新增一节“屏蔽几何优化”，系统说明外层带电粒子敏感塑料闪烁体、近全包络主动闪烁体和含硼聚乙烯层的设计动机、几何定义与实测效果。

## 2. 新会话启动提示词

在新会话中粘贴以下内容：

```text
你正在接手 `/home/ubuntu/TES_511_Balloon` 的 M04 数据模型校验与优化几何入稿工作。

唯一会话执行合同：
`engineering/m04_validation_geometry_handoff_20260810/SESSION_BOOTSTRAP.md`

请先只读执行该文档第 4 节的阅读顺序，并完成第 3 节冻结检查。不要依赖聊天压缩摘要作为权威。

硬约束：
1. 不得修改、覆盖或重新编译到当前 M04 的中英文 .tex/.pdf。
2. 不得修改 M04 第 3 节及此前的任何文案或图片，尤其不得修改或重画当前图 2。
3. 不得覆盖 retained Mass_model_511、S3c 或 S3d-O8 产品；所有新运行和报告必须落入新的日期目录。
4. 不得把 2026-07-07 的“EXPACS 511 line gap”结论继续当作物理依据；它已被官方 PARMA 源码和本地原始表复核推翻。
5. 在 M 抽样、PARMA 511 线和最终几何 A/B 门槛通过前，不得把新数值写入论文。
6. 论文阶段必须先复制 M04 为后继版本，再编辑副本；中英文同步，不得只改一份。

先报告：工作树状态、冻结校验、所读权威文件、准备执行的首个最小验证。随后按 WP0→WP4 推进。
```

## 3. 不可变边界与冻结校验

### 3.1 当前 M04 源稿是用户指定的只读基线

本任务中，以下文件均禁止原地修改、覆盖或用构建命令重新生成。两份 `.tex` 是当前内容基线；两份同名 PDF 仅作为冻结历史产物，不能代表当前源稿：

| 角色 | 路径 | SHA-256（2026-08-10） |
| --- | --- | --- |
| 英文源稿 | `core_md/balloon511_ea_latex_drafts/balloon511_ea_draft_en_m04_atm511_revision_20260804.tex` | `3eb0c1edccd7af7b198ab397371d633392c6a316a4ee3fbdf258057f54c7c53e` |
| 中文源稿 | `core_md/balloon511_ea_latex_drafts/balloon511_ea_draft_zh_m04_atm511_revision_20260804.tex` | `66df5babd3ecf5107c6f15e0eab525b25aaaea4fe5a641879962cd753524ba19` |
| 英文旧 PDF（不可作为当前 review 稿） | `core_md/balloon511_ea_latex_drafts/balloon511_ea_draft_en_m04_atm511_revision_20260804.pdf` | `9217af3b62fe0bd4a48c0db81d5a7770d2df20a78989a57fca972a5a41879694` |
| 中文旧 PDF（不可作为当前 review 稿） | `core_md/balloon511_ea_latex_drafts/balloon511_ea_draft_zh_m04_atm511_revision_20260804.pdf` | `5acce4670bed2d6366242276b878891fe48c7f51039991b6fe840a35f54ff56f` |

仓库 README 仍把根目录 EN/ZH 稿称为日常工作源，但本任务有明确的用户指定版本，因此这里以 M04 文件为审稿与复制源。不得把根目录稿或 `recovered_compile_ready/` 反向覆盖 M04。

版本审计确认：M04 EN/ZH `.tex` 的修改时间为 2026-08-10 18:10，而同名 PDF 是 17:42；两份 PDF 分别与 `*_pre_framework_rewrite_20260810.pdf` 逐字节相同。图 2 的当前 `.tex` 源也晚于同名 PDF，且同名 PDF 与 `*_pre_framework_rewrite_20260810.pdf` 相同。因此：

- 当前 M04 PDF 没有包含最终重写后的第 3 节，不能用于论文 review；
- 不得为修复此问题而覆盖 M04 PDF 或当前图 2 PDF；
- 后续应复制到隔离的 M05 目录，在副本中把图 2 源编译为副本目录内的同名 PDF，再用新的 jobname 编译 EN/ZH review PDF；
- 这样既保留冻结前缀中的图像引用字符串，又不触碰 M04 本体或原图件。

### 3.2 第 3 节及其以前必须保持逐字节不变

M04 中从文件开头到现有 Results/结果节之前的全部内容均冻结：

| 稿件 | 冻结范围 | 冻结前缀 SHA-256 |
| --- | --- | --- |
| 英文 | 原 M04 第 1--1199 行，即 `\section{Results}` 之前 | `c72137b78a66e45add8c4d5c25dfd07261a873862b7c202916b73d0c125f5e50` |
| 中文 | 原 M04 第 1--669 行，即 `\section{结果}` 之前 | `1b11acad70efd5f10df6adba63a993462466954d052a2bab12f441f70276fc47` |

这里的冻结包括引言、探测器与低温系统质量模型、第 3 节模拟框架、公式、表格、图注和图像引用。后续新节默认插在这一冻结前缀之后、现有 Results/结果节之前。若任何科学修复必须改动冻结内容，只能先形成“拟修改文本 + 理由 + 数据影响”供用户决策，不得自动落稿。

前缀复核命令：

```bash
awk '/^\\section\{Results\}/{exit} {print}' \
  core_md/balloon511_ea_latex_drafts/balloon511_ea_draft_en_m04_atm511_revision_20260804.tex | sha256sum
awk '/^\\section\{结果\}/{exit} {print}' \
  core_md/balloon511_ea_latex_drafts/balloon511_ea_draft_zh_m04_atm511_revision_20260804.tex | sha256sum
```

### 3.3 当前图 2 与所有前置图片冻结

尤其禁止修改、替换、重画或覆盖当前双语图 2：

| 图件 | SHA-256 |
| --- | --- |
| `core_md/balloon511_ea_latex_drafts/paper_source_figure_table/fig_simulation_workflow_m04_en_20260810.pdf` | `f739b3af1a6f3eb194f26596e1cc2b1bbfcebd14a68ab2c2b9a86a8f323ff2b2` |
| `core_md/balloon511_ea_latex_drafts/paper_source_figure_table/fig_simulation_workflow_m04_zh_20260810.pdf` | `41a3b31f4ea79c0aab3d9e0616bec5fbd76a9377e3a2f061db739db17558edea` |
| `core_md/balloon511_ea_latex_drafts/paper_source_figure_table/fig_simulation_workflow_m04_en_20260810.png` | `e96eaebe3457b97670c554a216441a8649cceaf6352b0c9d37ffbf98c9fafa37` |
| `core_md/balloon511_ea_latex_drafts/paper_source_figure_table/fig_simulation_workflow_m04_zh_20260810.png` | `7dab74ce43c5824a16b0aaa756f00b30ebe07cda8f6fa7f725799393acd41d94` |
| `core_md/balloon511_ea_latex_drafts/paper_source_figure_table/fig_simulation_workflow_m04_en_20260810.tex` | `4406b062ac676c60a878eecd85bc60bbc424ccaed442720180af0bde8976dbc1` |
| `core_md/balloon511_ea_latex_drafts/paper_source_figure_table/fig_simulation_workflow_m04_zh_20260810.tex` | `1d04e0e9e21c4d26d9ec053f05154de2f2da6d1459a775b81bd7c73821d7f39d` |

第 3 节及以前引用的其他图也不得覆盖：

| 图件 | SHA-256 |
| --- | --- |
| `fig_reference_detector_cryostat_geometry.png` | `f019c227cb283e9259ef1751804e15d536363302d78ff8251f079b0de7801b83` |
| `fig_expacs_fullsphere_flux.png` | `be9467ec956498a281d7d530a1ae0f6ddc48e2949b74c4f179622d479b1fa704` |
| `fig_s33_poisson_normalization.png` | `d9b71f7daa63f8e1de1f55d99031313a1ceda80630107a28b932ab4aa20ccb7e` |
| `fig_s33_spectrum_normalized.png` | `fad0233857e407248cd6a3ac30ee28f0d0d72109fa8c47e4f58bdd9647a604fa` |
| `fig_s33_spectrum_anticoincidence.png` | `f9229f77ace674a7eec7e0e24fd0e0248814c42118b260e5d7e11867f8ca0558` |
| `fig_s33_compton_multiplicity.png` | `3130fe8a7a43b5341c9e1528f2e0a133dcc87116e83e12cb4fe83598de401dfc` |

### 3.4 工作树安全

当前工作树已有大量用户修改和未跟踪的论文产物。禁止执行 `git reset --hard`、`git clean`、覆盖式 checkout 或任何清理操作。每次运行前后都记录 `git status --short`；判断本任务改动范围时使用新目录清单和受保护文件 SHA，而不是假定工作树原本干净。

## 4. 必读顺序：先复习项目，再复习论文

### 4.1 仓库与质量模型入口

1. 根目录 `AGENTS.md` 或用户在会话中给出的同名指令。
2. `engineering/Mass_model_511_nearfield_migration_20260701/SESSION_BOOTSTRAP.md`
3. `engineering/Mass_model_511_nearfield_migration_20260701/README.md`
4. `engineering/Mass_model_511_nearfield_migration_20260701/11_manuscript_support/claim_boundary.md`

必须保留的边界：光学几何迁移是平行记录，不等于已经纳入探测器背景输运；不得把 optics hardware background 写成已闭合。

### 4.2 几何优化主线

1. `engineering/geometry_optimization_20260704/40_s3c_mainline_lightweight_review_20260710/README.md`
2. `engineering/geometry_optimization_20260704/40_s3c_mainline_lightweight_review_20260710/data/s3c_mainline_analysis_summary.json`
3. `engineering/geometry_optimization_20260704/40_s3c_mainline_lightweight_review_20260710/CLEANUP_MANIFEST.md`
4. `engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/README.md`
5. `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/README.md`
6. `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/FULLCHAIN_DATA_VALIDATION.md`
7. `engineering/geometry_optimization_20260704/44_s3d_o8_all8_activation_20260713/README.md`
8. `engineering/geometry_optimization_20260704/44_s3d_o8_all8_activation_20260713/data/s3d_o8_all8_activation_campaign.json`
9. `engineering/geometry_optimization_20260704/44_s3d_o8_all8_activation_20260713/fullchain/step05/step05_s3d_o8_all8_activation_l1_response_summary.json`

不得恢复已删除的 S3/S3a/S3b 模拟产品。历史比较只能使用 retained conclusion snapshots；新比较运行必须放入新日期目录。

### 4.3 优化构型的形成过程

1. `engineering/geometry_optimization_20260704/09_gpt_complement_ingress_veto_bpe_20260707/01_README_GPT_PARSE.md`
2. `engineering/geometry_optimization_20260704/13_step01_plastic_threshold_scan_20260708/README.md`
3. `engineering/geometry_optimization_20260704/16_geoopt_s2b_cryo_shell_45deg_20260708/README.md`
4. `engineering/geometry_optimization_20260704/17_s2b_eqstats_prompt_atm511_20260708/s2b_eqstats_background_comparison.md`
5. `engineering/geometry_optimization_20260704/20_s2b_zero_plastic_eplus_trace_20260708/s2b_zero_plastic_eplus_trace_summary.md`
6. `engineering/geometry_optimization_20260704/21_geoopt_s3_csi_barrel_20260709/README.md`
7. `engineering/geometry_optimization_20260704/27_geoopt_s3a_bgo_barrel_20260709/README.md`
8. `engineering/geometry_optimization_20260704/29_geoopt_s3c_bgo_w2mm_al3mm_shell_20260709/README.md`
9. `engineering/geometry_optimization_20260704/39_mass511_to_s3_html_presentation_20260710/deck_evidence_summary.json`

这些历史结果用于解释优化路径，不自动成为最终论文数值。尤其是涉及旧大气 511 sidecar 的比较，必须在 PARMA 单计数修复后重算或清楚标为历史筛选。

### 4.4 M 抽样权威入口

1. 构建器：`code/tools/build_fix5_1of10_exactpos_delayed_source.py`
2. 最终 all-eight 包：`engineering/geometry_optimization_20260704/44_s3d_o8_all8_activation_20260713/README.md`
3. 中子源审计：`engineering/geometry_optimization_20260704/44_s3d_o8_all8_activation_20260713/fullchain/delayed_source/n/delayed_source_exactpos_summary.json`
4. 最终七个正活度族的抽样表：`runs/geometry_optimization_20260704/step02_delay_exactpos_s3d_o8_all8_activation_m50000_20260713/<family>/exactpos_weighted_rpip_table_m50000_s260613.csv`
5. 历史输运收敛诊断：`old/reports/v3p5_exactpos_convergence_20260614/v3p5_exactpos_convergence_report.md`
6. package-44 activation runner：`engineering/geometry_optimization_20260704/44_s3d_o8_all8_activation_20260713/code/run_s3d_o8_all8_activation.py`
7. Step05 parser/selection：`engineering/geometry_optimization_20260704/44_s3d_o8_all8_activation_20260713/code/run_s3d_o8_all8_step05.py`
8. 64-seed 420 eV response：`engineering/ea_s3d_o8_all8_detector_response_closure_20260713/data/s3d_o8_all8_energy_response_summary.json`
9. BUILDUP provenance：`runs/geometry_optimization_20260704/step02_buildup_s3d_o8_all8_activation_m50000_20260713/run_manifest.csv` 与 `normalization.json`

### 4.5 大气 511 keV 线材料

1. 本地 EXPACS 原始表：`expacs_fullsphere_20bin_sources/raw_expacs/`
2. 当前 Cosima 光子 PDF：`expacs_fullsphere_20bin_sources/cosima_spectra_dp_2602units/`
3. 本地工作簿：`expacs_fullsphere_20bin_sources/_workbook/EXPACS-eng.xlsx`
4. 当前 sidecar 生成器：`engineering/geometry_optimization_20260704/32_s3c_dominant_backgrounds_20260709/build_s3c_atm511_sidecar.py`
5. 当前 O8 sidecar 及全链：`engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/`

`engineering/geometry_optimization_20260704/11_expacs_atm511_line_gap_20260707/README.md` 只能作为“历史误判是怎样发生的”来读。其“EXPACS/PARMA 不含 511 线、因此应另加完整单能线”的结论已经失效，禁止继续作为模型依据。

### 4.6 当前论文

先并排阅读第 3.1 节所列 M04 EN/ZH 源稿与 PDF，至少完成以下检查：

- EN/ZH 的节、子节、公式、表、图和引用是否一一对应；
- 每个定量结论对应哪个 JSON/CSV/SIM/几何清单；
- 第 3 节的 M 抽样描述是否与构建器实际键值和 Cosima 运行语义一致；
- 大气线文字、表 1、Results、Discussion、Abstract 中哪些数字依赖旧 sidecar；
- 当前论文只写了 BGO 方向分级，哪些位置遗漏了塑料闪烁体和含硼聚乙烯；
- 任何新几何结果是否会使摘要和结论中的 headline numbers 失效。

将复核结果写入本工作包未来的 `00_review/PROJECT_AND_M04_REVIEW.md`，只记录问题，不改论文。

## 5. 当前已确认事实与尚未闭合项

| 主题 | 已确认事实 | 尚未闭合 | 论文影响 |
| --- | --- | --- | --- |
| M 抽样定义 | 按活度权重有放回抽取产生位置，每个被抽点赋相同通量 A/M；对固定的有限 RPIP 表，源层期望无偏 | 最终 O8 的选后率没有多 seed、多个 M 或全行直接加权的收敛证明 | 可以解释公式，不能声称 M=50,000 已充分收敛 |
| M 的物理含义 | M 是延迟源空间支持的重采样规模，不是“尽量抽到 TES 本底”的重要性抽样 | 稀有但高探测效率位置是否影响 W511 率 | 必须用探测器后选率验证，不能以漏抽活度比例替代 |
| 源匹配键 | 当前构建器把活度按 `(VN, ZA)` 分配到 RPIP 坐标；`exc_keV` 被记录，但不在该分配键中 | 是否需要在未来构建器中加入激发态维度 | 当前 Methods 若称按体积、核素和激发态匹配，与实现不完全一致 |
| `1e6` 的含义 | 源卡设置的是 Cosima `Triggers`/预触发记录；SIM 的 `TE` 用于率归一，不是物理气球曝光 | 各族提前终止/保留事件数的语义应逐一核对 | 不应直接写成“输运 (10^6) 个物理延迟衰变” |
| PARMA 大气线 | PARMA 光子模型和官方程序本身含 511 keV 湮没线；官方生成器可发射 0.51099895 MeV 光子 | 必须在固定版本和固定飞行元数据下重新生成 | 现有“PARMA 只有连续谱插值”的说法不可继续作为物理事实 |
| 旧 prompt 与 sidecar | 本地旧 EXPACS 表在约 566 keV 的宽箱中已含被摊平的 511 线；再加入完整 sidecar 会重复同一物理分量 | 对最终 W511 和任务灵敏度的净影响尚未以修正源重跑 | 现有大气线率和所有依赖它的总本底/显著度是条件式旧结果 |
| 优化几何 | 最终 O8 保留外层塑料闪烁体与 5 wt% 含硼聚乙烯，并使用 40/30/10 mm 方向分级 BGO | 各层在最终几何中的单因素贡献尚未完全 A/B 闭合 | 新节可列几何和动机，效果必须区分“组合效果”和“单因素效果” |

## 6. WP0：项目和论文复核

### 6.1 输出

新建但不得覆盖：

```text
engineering/m04_validation_geometry_handoff_20260810/00_review/
├── PROJECT_AND_M04_REVIEW.md
├── manuscript_claim_to_source_matrix.csv
├── protected_file_hashes.sha256
└── review_manifest.json
```

### 6.2 必须完成的复核

1. 记录工作树状态和所有受保护文件校验值。
2. 明确记录“当前 `.tex` 新于同名 PDF，现有 PDF 不可 review”的版本错位，不把旧 PDF 的可见内容当作当前源稿证据。
3. 对 M04 每个 headline number 建立“稿件位置 → 生成文件 → 生成代码 → 几何 → 源模型 → 选择定义”的链路。
4. 明确哪些数字来自旧 atmospheric-511 sidecar，哪些来自 M=50,000 单 seed 延迟源。
5. 明确当前最终几何中塑料、BPE、BGO、Al/Kapton 和保留开口的实际尺寸。
6. 任何路径缺失、哈希不匹配、几何头错误或归一化不清楚时，先标红为 blocker，不推断补齐。

### 6.3 WP0 通过条件

- 受保护 M04 和图件哈希全部匹配；
- 中英文结构对应关系有记录；
- 当前论文数字的来源覆盖率为 100%，无法追溯的数字明确列为 blocker；
- 后续运行使用的 O8 `.geo.setup`、`.geo`、`.det` 与 retained manifest 哈希一致。

## 7. WP1：M 抽样数合理性校验

### 7.1 先把问题定义准确

设固定的、经 NUBASE ground-state 修正和 per-family TT 除数审计后的 RPIP 产生表有行 j，其目标活度权重为 w_j，总活度 A 见下式。当前方法按

\[
A=\sum_j w_j,\qquad
p_j=\frac{w_j}{A}
\]

有放回抽取 M 个位置，每个 PointSource 赋通量 A/M。因此

\[
\mathbb{E}\left[N_j\frac{A}{M}\right]=w_j
\]

只证明“给定有限产生表时，源层估计无偏”，并不证明探测器后 W511 率已经收敛。最终率还取决于每个位置的探测概率 q_j，包括局部衰减、BGO/塑料 veto 和拓扑选择。

当前中子源的审计事实：

- eligible RPIP rows：58,672；
- M=50,000，seed=260613；
- 未被抽中的 `(VN,ZA)` 组对应约 0.1574 Bq、占总活度约 0.515%；
- 该 0.515% 不是 W511 选后率误差上限；
- 源审计文件自身明确声明，源层 PASS 不能替代 transport-backed M/seed convergence。

[MGGPOD](https://arxiv.org/abs/astro-ph/0408399) 和近期 [COSI balloon background study](https://arxiv.org/html/2503.02493v2) 支持按核素、材料体积或产生位置处理活化，但它们不证明本项目的 exact-RPIP 重采样实现，也不提供 M=50,000 的通用收敛结论。因此 M 的选择必须由本项目最终几何和最终 selection 下的数值实验决定。

### 7.2 必须分开的三类不确定性

1. **有限 BUILDUP 产额不确定性**：产生表中反应通道和核素产额的有限统计；多 M seed 不能修复。
2. **有限 M 重采样不确定性**：从既有 RPIP 表抽有限空间支持造成；这是本 WP 的主要目标。
3. **延迟衰变输运计数不确定性**：给定源以后，最终通过 W511/veto/topology 的有限事件数；增加 transport statistics 才能降低。

报告中不得把三者合并成一个“Monte Carlo error”，也不得用其中一个替代另两个。

### 7.3 推荐的两阶段验证

现有 package-44 把 `M_BLOCKS=50000`、`RAW_TRIGGERS=1000000` 和 `SEED=260613` 固定在 runner 中，而且 `--force` 路径会先删除已有 SIM。严禁在 package-44 上执行 `prepare-delay --force` 或 `run-delay --force`。新实验必须使用新的 dated sibling 和新的 `runs/` 前缀，复用只读输入但完全隔离输出。

#### 阶段 A：源层低成本扫描

- 最小主矩阵先固定中子族 BUILDUP/活度，取 M=50,000 和 100,000，source seeds=`260613,260614,260615,260617`，共 8 个 source realizations。
- 每个 realization 必须输出 source、完整 weighted table、manifest、source hash、活动闭合、unique coordinates、未抽中 `(VN,ZA)` 活度和 support diagnostics。
- 对七个正活度族补做 source-only 组成检查；M=25,000 仅在主矩阵失败时作为趋势诊断，M=200,000 仅在 50k→100k 尚未收敛时增加。
- 比较总活度闭合、正权重 `(VN,ZA)` 组覆盖、材料/体积/核素份额、r/z 加权空间分布和 top-contributor 稳定性。
- 阶段 A 只能筛选明显不足的 M，不能单独证明 W511 率合理。

#### 阶段 B：探测器后选率验证

首选参考是“全 RPIP 行直接加权源”：每个有效行保留自己的通量，不再进行有限 M 重采样。实施前先用两个不等通量 PointSource 做 Cosima smoke test，验证源调度、总通量和 `TE` 归一语义。smoke 未通过时不得运行大任务。

最低可执行的 transport-backed 矩阵为 8 个独立中子运行：

| M | source seeds | transport seeds | requested triggers/run |
| ---: | --- | --- | ---: |
| 50,000 | 260613, 260614, 260615, 260617 | 360613, 360614, 360615, 360617 | 2,000,000 |
| 100,000 | 260613, 260614, 260615, 260617 | 460613, 460614, 460615, 460617 | 2,000,000 |

source seed 与 transport seed 必须分开写入 provenance。当前基线曾把同一 seed 同时用于抽样和 `cosima -s`，新实验不得继续混用。当前中子 1M triggers 在 420 eV W2 下约产生 60 个最终事件；上述矩阵预计每个 M 合计约 480 个事件，合并计数 RSE 约 4.6%。8 个 2M SIM 粗估约需 15 GB，启动前必须做磁盘、运行时间和文件数 preflight。

主验证优先级：

1. 中子族：完成上表 M50/M100 配对矩阵；全行直接加权参考在不等通量 smoke 通过后作为优先 gold standard。若 M50/M100 未收敛，再增加 M200，而不是用更多 transport 噪声掩盖趋势。
2. 对最终延迟率贡献达到 5% 的其他族执行相同检查；低于 5% 的族至少完成源层扫描和一个全行/抽样输运交叉检查。
3. 所有条件使用同一 O8 几何、同一核素清单、同一 detector response、同一 50 keV 离线主动 veto 和同一 Compton topology 定义。
4. 每个主条件累计至少 400 个最终 W511 选后事件，或继续运行到该条件的纯计数相对标准误差不大于 5%。
5. 每个 transport catalog 使用同一组 64 个 detector-response seeds 做 420 eV FWHM analysis-only ensemble；这些 replicas 不能计作 64 倍独立 transport statistics。

### 7.4 必报指标

- 最终 510.58–511.42 keV 率；
- active-veto survival 与 topology survival；
- 按入射族、母核素、材料类别、具体体积和产生位置区域分解的最终率；
- 每个 M 档的 seed-to-seed 方差；
- 抽样条件与全行直接加权参考的差；
- transport counting interval 与 M-sampling interval 分开报告；
- BUILDUP 产额不确定性单列为未被本实验覆盖的系统学。

### 7.5 `PASS_M_SAMPLING` 门槛

只有同时满足下列条件，才可在论文中称 M=50,000 对“固定 BUILDUP 表条件下的、由中子主导的总延迟率”足够：

1. 每个 M 的独立 W511 selected events 合计至少 400，合并 transport RSE 不大于 5%；
2. 用已知的每 run transport variance 做 random-effects/REML 分解，M50 的 source-resampling CV 点估计不大于 5%，其 95% upper bound 不大于 10%；不能把 4 个总率的普通样本标准差全部称为 M 方差；
3. `|mean(R100)-mean(R50)|/mean(R100)` 不大于 5%，且 paired difference 的 95% CI 落在 ±10% 等效区间内；
4. broad window 与 W511 的结论不冲突，M50/M100 的 veto survival 绝对差不大于 2 percentage points；
5. 选后率前 90% 的 `(VN,ZA)` 贡献集合 overlap 至少 80%，组成 Jensen–Shannon divergence 不大于 0.10；
6. 64-response-seed mean 的分析数值 SE 小于 delayed rate 的 1%，并且所有 M 使用完全相同的 response-seed set；
7. NUBASE、每族 TT 除数、源/清单 provenance、几何头、source seed、transport seed、`SE/ID/TS/TE` 归一均 PASS。

若不通过：先判断应增加 transport statistics、source seeds 还是 M。4 seeds 后若 source-CV upper bound 仍大于 10%，扩至 8 seeds；8 seeds 后若 source CV 仍大于 5% 或 M50/M100 差异仍大于 5%，增加同 seed 的 M200。仍不通过时采用更大 M、全行直接加权源或按 `(family,VN,ZA)` 分层抽样。不得仅凭“漏抽活度只有 0.515%”放行。

本 WP 的最终状态只能写成：`PASS_M50000_CONDITIONAL_ON_FIXED_BUILDUP`、`FAIL_M50000_PROMOTE_LARGER_M_OR_STRATIFY` 或 `INCONCLUSIVE_MORE_TRANSPORT_OR_SEEDS_REQUIRED`。即便通过，也不等于 BUILDUP 产额和核反应截面系统学已经闭合。

### 7.6 输出目录

```text
engineering/m04_validation_geometry_handoff_20260810/01_m_sampling_validation_YYYYMMDD/
├── README.md
├── config/
├── source_only/
├── unequal_flux_smoke/
├── transport/
├── response/
├── data/m_sampling_convergence_summary.json
├── data/m_sampling_convergence_by_family.csv
└── M_SAMPLING_CONCLUSION.md
```

## 8. WP2：从 PARMA 模型重新给出大气 511 keV 线

### 8.1 必须纠正的模型认识

PARMA 的光子模型本身含 511 keV 湮没线。Sato 的 PARMA 3.0 模型在光子谱表达式中显式包含 E_a=0.511 MeV 的线项；官方程序把线积分通量加入包含 511 keV 的能箱，事件生成器则可生成 0.51099895 MeV 光子。

当前旧输入的实际问题不是“完全漏掉了线”，而是：

1. 离散线在旧宽能箱中被摊成箱平均值；
2. Cosima 线性插值又把该凸起在更宽能区连续化；
3. 项目随后又添加了完整独立 sidecar；
4. 因而同一物理湮没分量在总归一上被重复加入，同时旧分量的谱形又被错误展宽。

本地例证：`raw_expacs/spectrum_gamma_bin00_theta18.19_BHNo.dat` 在 449.65、566.08、712.64 keV 的值分别约为 0.01042、0.01153、0.002037；566.08 keV 的凸起与“纯连续谱 + 官方线通量/箱宽”一致。下一会话必须重新计算并把复现脚本、版本和校验值保存在新目录，不能只引用这段交接结论。

### 8.2 唯一允许的基线分解

基线源定义必须写成

\[
J_\gamma(E,\Omega)=J_{\mathrm{cont}}(E,\Omega)
+\Phi_{511}(\Omega)\,\delta(E-0.51099895\,\mathrm{MeV}),
\]

其中：

- J_cont 由 PARMA 的纯连续谱函数生成，明确不含 line term；
- Phi_511 由同一固定版本 PARMA 的 511-line 函数和角分布生成；
- 两者只能各出现一次；
- 不再把 Peterson/Harris 参数化 sidecar 与完整 PARMA line 同时作为 nominal；历史观测只能作为替代模型或系统学对照。

### 8.3 固定版本与元数据 gate

1. 从 EXPACS 官方下载页获取明确版本的 PARMA 源码，复制到本工作包的 `vendor/`，记录下载 URL、日期、版本 banner 和 SHA-256。不得把 `/tmp` 中的临时副本当作权威。
2. 保存未修改源码；若需要 wrapper，另建文件，不直接改 vendor 源。
3. 固定 day-15 输入的日期/太阳调制 W、截止刚度 Rc、残余柱深 X、经纬度、高度和角度约定。
4. 当前资料中存在三套潜在冲突的 day-15 元数据，必须逐一登记：
   - `stepwise_maintenance/step06_mission_time_variation/outputs_geo_opt_s1_bpe_w5_fullstat_v1/trajectory_profile.csv` 第 62 个物理行：Rc=11.0 GV、X=3.4614689720143224 g cm^-2；
   - `expacs_fullsphere_20bin_sources/manifest.csv` 第 2 行：W=118.3、Rc=11.6 GV、38 km；
   - `/home/ubuntu/codex_tes_511_sim/COSMOSRAY_BALLOON_SIM/reports/phase2_real_flight_physical_production/phase2_summary.json` 的 `pieces.environment.reference_condition`：2025-08-31、W=114.6、Rc=11.6 GV、38 km 时 X=3.86509853156 g cm^-2。
5. 不得混用三套数。建议让同一次官方 driver 调用生成全部环境量。对论文 day-15 的 38.75 km 条件，复现 checksum 应为 `META,114.6,11.6,3.46146897201`；对应 line flux checksum 为 `0.166515472 ph cm^-2 s^-1`。这些值仍须由冻结源码和 authority JSON 自行重算，不能从本交接硬抄为生产结果。

现有只读官方源码镜像位于 `/home/ubuntu/codex_tes_511_sim/COSMOSRAY_BALLOON_SIM/external/expacs_parma/parma_cpp/`。其关键文件在 2026-08-10 与官方下载快照一致：

| 文件 | SHA-256 |
| --- | --- |
| `subroutines.cpp` | `620cab2b58bac6bf996dcc0ad9a33b7bc113a4d768eb2f17b97788a500010c1b` |
| `main.cpp` | `ac7da5a9d7b1b0a0951e277bd0246dcd95d995a247d761642e7f6e0b032c665b` |
| `main-generator.cpp` | `5e0f127880b048e4a5dcb204757004aea96d9982417ac7bb7baed378e3896fdb` |
| `input/elemag/flux511keV.inp` | `30b57b1aba9d62c956ed323ec49f8d7d36a8d1ae9fa7eb149708f9c412fc59c0` |

新工作包仍应复制并重新核对这些文件，不能把仓库外路径作为永久论文 provenance。

### 8.4 实施步骤

1. **官方程序复现**：编译未修改 PARMA，并复现官方示例或工作簿的连续谱和 line-bin 行为。wrapper 只调用官方 `getSpecCpp(33,...)`、`getSpecAngFinalCpp(6,...)` 和 `get511fluxCpp(...)`；运行工作目录必须能正确读取官方 `input/` 数据库。
2. **纯连续谱生成**：只用 `getSpecCpp()` 的 continuum 路径和能量相关角分布生成输入，排除 511 line term。PARMA 每 MeV 的输出转换为 Cosima 每 keV PDF 时除以 1000；每个 PDF 数值积分必须为 1，`.Flux` 写该角箱连续谱积分。
3. **离散线生成**：`get511fluxCpp()` 返回全立体角积分 line flux，不能再除以 4π。PARMA 没有独立 line-only angular function；应明确采用 PARMA 在 510.99895 keV 处的 photon angular distribution，把总 line flux 积分分配到各角箱。Cosima 能量单位为 keV，因此 source card 写 `Spectrum Mono 510.99895`。
4. **能格与角度离散化**：连续谱能格至少显式包含 480、500、510.58、510.99895、511.42、520、550 keV。至少生成 20、40、80 个等 μ 分箱；每个角箱必须积分 angular PDF，不能用箱中心值乘 ΔΩ。另做上下半球各一个单光子 smoke，确认 Cosima 的方向标签。
5. **源级闭合**：纯连续谱加离散线必须重现官方标准输出中 line 所在宽箱的积分；连续谱中不得残留第二份 line bump。
6. **探测器输运**：在 retained O8 几何中分别输运 continuum 与 line；所有源卡和 SIM header 必须指向同一正确几何。
7. **线形系统学**：nominal 使用 PARMA 的单能实现；另以 Mahoney 等测得的 511.07 ± 0.10 keV、2.29 ± 0.30 keV FWHM 作为轨道测量约束的敏感性包络，而不是宣称它就是球载真实线宽。
8. **文献对照**：Peterson 的约 3.6 g cm^-2 实测归一和 Harris 的刚度/太阳活动趋势只作为 alternate/systematic scenario，清楚标注从特定测量条件迁移到本任务的假设。
9. **任务轨迹折叠**：保留每个角箱的 detector response coefficient，再逐时间箱用该箱的 PARMA line flux 折叠。若事件目录没有可靠保留 source-bin ID，则按角箱分开输运；不能把 day-15 聚合 line rate只乘一个总通量比例。
10. **旧模型影响核算**：同统计量比较“旧 prompt + 旧 sidecar”和“新 pure continuum + PARMA line”，给出 W511、总本底、任务 Z、F3σ 及几何排名的变化。

### 8.5 `PASS_PARMA_511` 门槛

- vendor 版本、源码哈希、编译器和 wrapper 均可追溯；
- day-15 元数据只有一个 authority，连续谱、line 和 trajectory 无字段冲突；
- 每个连续谱 PDF 数值积分误差小于 1e-6；line 角分箱求和满足 `abs(sum(L_i)/F511-1)<1e-8`；
- “纯连续谱 + 单独 line”与独立官方总光子通量闭合到 0.2%，并在加密能格后进一步收紧；
- 检查确认 line 只加入一次；
- 新 continuum 在 0.56608 MeV 不再保留旧 line bump，source manifest 显式写 `continuum_line_terms=0`、`discrete_line_families=1`；
- 推荐 day-15 条件的高分辨率角积分 checksum 为：μ<0 份额约 0.823219842、μ>0 份额约 0.176780094、半球比约 0.214742266；须先确认 μ 与 up/down 约定再比较；
- 40 与 80 个角箱的最终 W511 单位通量响应相对差不大于 2%，且该比较的合并计数误差小于 1.5%；20 箱仅作为较粗诊断；
- 每个 nominal/主要系统学条件累计至少 400 个最终 W511 事件，或纯计数相对标准误差不大于 5%；
- 单能、有限线宽、角分布和归一化效应分别报告；
- 新旧模型差异已传播到 day-15 background 和 20 d 性能。

线宽响应还应通过两个解析 checksum：PARMA mono line 加 420 eV FWHM 后，W2 接受率约 0.98147；2.29 keV intrinsic FWHM 再与 420 eV detector response 卷积后，W2 接受率约 0.32824。420 eV detector response 只能施加一次，不能在源宽和后处理中双重卷积。

### 8.6 主要文献和官方入口

- [EXPACS official updates](https://phits.jaea.go.jp/expacs/top-eng.htm)
- [EXPACS official downloads](https://phits.jaea.go.jp/expacs/download-eng.htm)
- [Sato 2015, PARMA 3.0 photon model](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0144679)
- [Peterson et al. 1973 atmospheric 511-keV measurement](https://agupubs.onlinelibrary.wiley.com/doi/abs/10.1029/JA078i034p07942)
- [Harris et al. 2003 rigidity/solar dependence](https://arxiv.org/abs/physics/0308082)
- [Mahoney et al. 1981 line centroid and width](https://agupubs.onlinelibrary.wiley.com/doi/abs/10.1029/JA086iA13p11098)

### 8.7 输出目录

```text
engineering/m04_validation_geometry_handoff_20260810/02_parma_atm511_repair_YYYYMMDD/
├── README.md
├── vendor/
├── config/day15_environment_authority.json
├── code/
├── continuum/
├── line/
├── transport/
├── response/
├── data/parma_line_closure.json
├── data/angular_convergence.csv
├── data/line_shape_systematics.csv
└── PARMA_ATM511_CONCLUSION.md
```

## 9. WP3：最终优化几何的证据闭合

### 9.1 论文应说明的实际层级

最终 O8 不是只有 40/30/10 mm BGO。它继承并保留了以下屏蔽层：

| 层/部件 | 最终几何定义 | 主要设计目的 | 当前证据边界 |
| --- | --- | --- | --- |
| 外层塑料闪烁体 | 10 mm side skin + 10 mm top/bottom caps，沿 45° 仪器轴包络，并为支撑结构作 relief | 标记入射带电粒子，尤其是会在被动材料中湮没并向 TES 送入 511 keV 光子的正电子 | 对 S1/S2b 有 veto replay；最终 O8 仍需同一事件链的 on/off 复核。它不是“只对正电子敏感”的专用探测器 |
| 5 wt% 含硼聚乙烯 | 20 mm side shell + 20 mm top/bottom caps，位于塑料层内侧 | 慢化中子并提高含硼俘获概率，减少内部中子相互作用和后续活化 | 现有 -24.9% 活度变化来自整个 shield stack，不是 BPE-only 因果证据；必须做匹配 no-BPE A/B |
| 近全包络主动 BGO | side 40 mm、bottom 30 mm、top annulus 10 mm；保留光学侧孔、顶部服务开口和机械 relief | 对进入线窗且伴随屏蔽沉积的 prompt/delayed 事例作主动反符合，并按主要入射方向分配质量 | O8 geometry/overlap/screening/full-chain 已有历史 PASS，但 atmospheric line 模型修复后需重新核算最终效果 |
| 外包络 | 3 mm Al 与 Kapton；去除连续 outer W2 shell | 提供轻质机械包络，避免额外高 Z 活化与质量负担 | 只支持 transport geometry 和 pre-relief bookkeeping，不等于结构鉴定 |

最终事件选择的 active-veto mask 实际同时包含 BGO 与外层塑料闪烁体。因此论文中的 “BGO offline anticoincidence” 或 “active BGO volumes” 不是完整实现说明；新节应使用 “combined scintillator anticoincidence / 组合闪烁体反符合”，并分别列出 BGO 与 plastic 的体积集合和统一的 50 keV 离线沉积能判据。由于相关旧表述位于冻结区，只能先在新节和问题清单中澄清，不能原地改 M04。

几何权威：

`engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`

已冻结几何哈希：

- `.geo.setup`: `86a9e56e54dc86834dfe2a9b03a5f71373fb40f2ef24e3889fa66f216058fbec`
- `.geo`: `ff4e8402df702501e0112fe377d837a74c39100317146b09e9569b7bd615c37c`
- `.det`: `dd2c1d68cd474f8b0c7489f2cbbfc924eb69beb14d3ce360d9437c319a33d6cb`

### 9.2 为什么重点优化这三方面

1. **正电子路径**：参考构型中正电子是主要 prompt W511 来源之一。塑料层可对带电初级粒子提供先验标记；但完全未在塑料中沉积的残余事例可来自外部被动材料中的湮没光子，因此必须同时减少几何缝隙和被动湮没路径。
2. **主动闪烁体覆盖**：残余事例以侧向进入为主，局部分段屏蔽会留下长侧壁、底部或服务区域的泄漏路径。近全包络 BGO 提供高密度主动覆盖；方向分级保留侧面 40 mm，同时减薄底/顶以控制质量。
3. **中子与活化**：中子既可形成 prompt 事例，也可在近场铜、铝、钨等材料中产生活化。含硼聚乙烯用于先慢化/俘获中子；主动 BGO 再抑制带伴随沉积的二次辐射。两者针对不同阶段，不能用一个总活度数字替代各自作用。

### 9.3 可作为历史动机、但不能直接作为最终因果结论的数值

- S1 同一输运的塑料 veto on/off 后处理：W2 background 从 0.0484939 降到 0.0353806 cps，下降 27.0%；19 个 W2 prompt-e+ 事例只在塑料参与 veto 时被剔除，对应 0.0129017 cps。
- S1 shield-stack 相对 Mass_model_511 的 ground-state-corrected day-15 总活度从 141.833 降到 106.482 Bq，下降 24.9%；这是塑料+BPE+局部 W 等组合变化，不是 BPE-only 结果。
- S2b 相对 S1 的 matched e+/n 结果支持加厚/扩展包络的筛选价值，但几何同时变化，不能只归因于厚度。
- O8 的 40/30/10 mm BGO、无 outer W2 组合通过了当时的 screening 和 full-chain gate；其中 atmospheric-511 使用旧 sidecar，修复前不得把其总本底和灵敏度继续当作最终发表值。

### 9.4 新模型下必须补做的最小 A/B

所有 A/B 都用修正后的 pure-PARMA continuum + single PARMA 511 line：

1. **Plastic veto contribution**：同一最终 O8 SIM，塑料能量计入/不计入离线 veto；这只隔离 veto 信息价值，不隔离塑料材料的输运作用。
2. **BPE contribution**：除移除 BPE 外完全相同的 O8/no-BPE 几何，至少重跑 prompt neutron、activation BUILDUP、delayed transport；源半径、seed 计划、统计量和选择必须匹配。
3. **Active full-wrap contribution**：用可审计的 reference/segmented-active 与 O8 full-wrap 对照，保持 radiation field、statistics、response 和 source normalization 一致。
4. **Directional grading**：O8 40/30/10 与 matched 40/40/40 control 比较；不能用已删除 legacy 产品，也不能混用旧 atmospheric sidecar。
5. **Signal guardrail**：每个候选都用 retained f10m A1 EventList bridge，最终 W511 signal acceptance 相对 control 损失不大于 2%。
6. **Activation guardrail**：NUBASE correction、per-family TT division、exact-position provenance 和新的 M-sampling gate 必须全部 PASS。

信号适用范围必须单列：现有 focused EventList 在 Be 窗选择面注入，因此信号保留结果没有检验光子从外部穿过完整 plastic/BPE 包络的衰减。若真实光路绕过这些外层，需用几何明确证明；否则补做上游信号输运，不能把当前 EventList acceptance 当作完整外层屏蔽的光学透过率。

### 9.5 几何效果的报告规则

- 把“几何事实”“设计动机”“组合方案的观测效果”“单层的因果效果”分四栏报告。
- 使用 event counts、cps、相对变化及区间，不只报百分比。
- 低统计分量不排序，不把 1--10 个 survivor 的中央值写成确定的物理层级。
- 大气线、prompt、delayed、signal 使用同一 response 和选择定义。
- 50 keV 是逐事例汇总主动体积能量沉积后的离线 veto；不得写成已经验证的硬件原生触发阈值。
- “full wrap”必须同时说明侧光学孔、顶部服务开口和 relief，不得写成无缝 4π 密封。

### 9.6 `PASS_GEOMETRY_MANUSCRIPT_EVIDENCE` 门槛

- WP1 与 WP2 已 PASS；
- final/control 所有 source card 和 SIM header 的几何路径正确；
- plastic、BPE、full-wrap BGO 和 directional grading 至少具有上述最小 A/B；
- 主要 background 条件达到不大于 5% 的计数相对误差，或明确给出精确计数区间并降低结论强度；
- signal acceptance loss 不大于 2%；
- 几何质量仅称 pre-relief analytic bookkeeping，不作结构鉴定；
- 新结果已传播到 day-15 与 20 d 任务指标。

## 10. WP4：新建“屏蔽几何优化”章节并双语同步

### 10.1 只能编辑后继副本

数据 gate 全部通过后，使用 `cp -a` 建立隔离的版本目录，例如 `core_md/balloon511_ea_latex_drafts/m05_validation_geometry_YYYYMMDD/`。至少复制 M04 EN/ZH 源稿和 `paper_source_figure_table/`，在副本目录内编译图 2 和主稿。不得修改 M04 本体，不得让 `latexmk -jobname` 指向 M04 PDF 名，也不得让副本编译回写父目录的现有图片。

当前同名 M04 PDF 和图 2 PDF 均落后于源文件。因此创建 M05 后的第一项构建验证应是：不改任何源文案，只在隔离副本内重编图 2 与 EN/ZH 主稿，确认 PDF 展示的是当前第 3 节；随后才允许新增优化章节。

默认插入位置：当前冻结第 3 节结束之后、现有 `\section{Results}` / `\section{结果}` 之前。不得为插入新节而改写第 3 节末段、图 2、前置交叉引用或图注。

### 10.2 建议节结构

英文：

```latex
\section{Shield-geometry optimization}
\subsection{Background-driven optimization targets}
\subsection{Charged-particle-sensitive plastic and borated-polyethylene enclosure}
\subsection{Full-wrap active scintillator and directional grading}
\subsection{Matched optimization results and final configuration}
```

中文：

```latex
\section{屏蔽几何优化}
\subsection{由本底来源确定的优化目标}
\subsection{带电粒子敏感塑料层与含硼聚乙烯包络}
\subsection{近全包络主动闪烁体与方向分级}
\subsection{同口径优化结果与最终构型}
```

这里的 “charged-particle-sensitive” 比“positron detector”准确：塑料闪烁体并不具备正电子专属性，只是本项目特别利用它识别入射正电子及其他带电粒子。

### 10.3 新节必须回答的四个问题

1. 参考几何的哪些选后事例特征促使优化塑料层、主动闪烁体覆盖和 BPE？
2. 每个优化阶段具体改变了什么尺寸、材料、开口和质量？
3. 每项改变希望压制哪类 prompt/delayed background，可能付出什么 signal/mass/activation 代价？
4. 在统一且修正后的源模型下，最终几何相对匹配 control 的效果是多少，统计和系统学边界是什么？

### 10.4 建议表图

- **一张优化阶段表**：reference、plastic/BPE enclosure、full-wrap CsI/BGO 候选、heavy control、O9、final O8；列 geometry delta、目标本底、状态和证据等级。
- **一张最终分层几何图**：新文件名，显示 TES/cryostat、BGO、BPE、plastic、开口与 45° 轴；不得覆盖现有图 1、图 2 或其源文件。
- **一张匹配 A/B 效果图或表**：plastic veto、BPE、full-wrap BGO、directional grading 对 prompt/delayed/atm511/signal 的影响和区间。
- 图表数据必须由新 workpackage 中的 CSV/JSON 生成，脚本和数据哈希写入 manifest。

### 10.5 学术行文规则

- 不使用内部运行标签（S1、S2b、S3c、O8）作为论文主叙事；正文使用描述性几何名称，内部标签只在 provenance 表或补充材料中映射。
- 不写“证明了”“完全消除”“最优”等超出 A/B 和统计支持的词。
- Results 只报事实和区间；设计动机与物理解释分开。
- 所有厚度、材料、阈值、率和百分比在 EN/ZH 中完全一致。
- 文献只支持物理原则或外部测量；项目效果必须引用本项目的表/图，不用外部论文替代。
- 新引用须核验实在性并保持 EN/ZH bibliography 顺序一致。

### 10.6 冻结内容与科学一致性的潜在冲突

当前冻结第 3 节中含有“所用 PARMA 表只有连续谱插值、没有离散线”的表述，以及有限 M 源的现有描述。WP1/WP2 很可能确认这些文字需要科学修正；同时新的 background 数值也可能使冻结区内的摘要失效。

处理原则：

1. 不修改 M04；
2. 在数据结论中列出精确冲突位置和建议文本；
3. 若用户没有解除“第 3 节及以前内容冻结”，后继稿只能作为审阅中的增补稿，不能标记为 submission-ready；
4. 不得在后文用含糊句子掩盖前文的明确错误，也不得让同一稿件出现相互矛盾的两种源定义；
5. 最终提交前必须由用户明确决定：允许在后继副本中修正冻结区，或指定一个能够无歧义更正方法定义的位置。

## 11. 推荐执行顺序与并行关系

```text
WP0 项目/论文/哈希复核
        |
        +---- WP1 M-sampling convergence --------+
        |                                         |
        +---- WP2 PARMA continuum + 511 line -----+--> WP3 matched geometry A/B
                                                        |
                                                        +--> WP4 M05 双语新增章节
```

WP1 与 WP2 可并行。WP3 必须使用 WP1/WP2 通过后的源与不确定性定义。WP4 不得在 WP3 之前写入数值。

## 12. 总验收清单

- [ ] 当前 M04 EN/ZH/PDF 哈希不变。
- [ ] 当前图 2 及第 3 节以前图片哈希不变。
- [ ] 工作树原有用户改动未被清理或覆盖。
- [ ] 项目和 M04 claim-to-source matrix 完成。
- [ ] M=50,000 通过 transport-backed 多 seed/多 M/全行参考校验，或被明确替换。
- [ ] BUILDUP、M 抽样和 transport counting 三类不确定性分开。
- [ ] PARMA 版本、源码、day-15 元数据和角度约定冻结。
- [ ] pure continuum 与 discrete 511 line 只各出现一次。
- [ ] 大气线通量、角分箱、线宽和探测器后率通过验收。
- [ ] final geometry 的 plastic、BPE、full-wrap active shield 和 grading 有匹配证据。
- [ ] 所有 headline background/significance 数字由新模型重新传播。
- [ ] 论文只编辑 M04 的后继副本，并以新文件名构建。
- [ ] 新增优化几何节 EN/ZH 结构、数字、表图和参考文献同步。
- [ ] 冻结区若与校验结果冲突，已向用户提交明确修正提案，不静默改稿。

## 13. 停止条件

出现以下任一情况时停止生产并报告，不得靠假设继续：

- 受保护文件哈希变化；
- 源卡或 SIM header 指向错误几何；
- PARMA 版本或 day-15 元数据无法唯一确定；
- continuum 中仍残留 line，同时又加入单独 line；
- Cosima 不等通量源的归一语义未通过 smoke；
- NUBASE ground-state correction、per-family TT division 或 source/inventory provenance 失败；
- M 或角分箱收敛未达到门槛；
- 几何 A/B 同时改变多个未记录因素；
- 新结果需要改动冻结区，但用户尚未解除冻结。

## 14. 本交接的结论边界

本文件定义下一阶段如何取得可发表证据，不宣称现有 M=50,000、旧 atmospheric-511 sidecar 或当前 headline sensitivity 已经最终有效。当前能够高置信度保留的结论只有：有限 M 抽样公式在固定产生表条件下无偏；PARMA 原生包含大气 511 keV 线；现有旧 prompt 与完整 sidecar 存在重复计入风险；最终 O8 几何确实含塑料闪烁体、5 wt% 含硼聚乙烯和方向分级 BGO。所有定量发表结论仍须通过上述 gate。
