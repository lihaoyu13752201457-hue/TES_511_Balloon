# M05 成熟论文数据替换 Session 交接

日期：2026-08-21  
执行模型：`gpt-5.6-sol`，reasoning effort=`ultra`

## 0. 任务性质

这不是“重新写一篇论文”，也不是重新设计论文结构。

任务是以现有、已经非常成熟的中英文论文为母版，只把其中基于旧 `Mass_model_511` 与
S3d 口径的数据、对应图、对应表格以及由这些数据直接决定的局部文字，替换成当前 SG3
参考几何和 SH3 烟囱几何的闭合结果。

母版 PDF：

- `core_md/balloon511_ea_latex_drafts/balloon511_ea_draft_en_m04_atm511_revision_20260804_pre_framework_rewrite_20260810.pdf`
- `core_md/balloon511_ea_latex_drafts/balloon511_ea_draft_zh_m04_atm511_revision_20260804_pre_framework_rewrite_20260810.pdf`

对应的可编辑母版：

- `core_md/balloon511_ea_latex_drafts/balloon511_ea_draft_en_m04_atm511_revision_20260804_pre_framework_rewrite_20260810.tex`
- `core_md/balloon511_ea_latex_drafts/balloon511_ea_draft_zh_m04_atm511_revision_20260804_pre_framework_rewrite_20260810.tex`

英文母版为 28 页，中文母版为 27 页。两者是本任务的文章结构、论证顺序、文本成熟度、
公式、引用、图表位置和版式权威。

## 1. 首要约束

1. 不删除、不覆盖、不修改上述四个母版文件。
2. 先分别复制两份母版 TeX 到 `M05NEW`，再在复制件上修改。
3. 同时产出英文和中文修订稿；二者保持逐节、逐图、逐表对应。
4. 保留原论文标题体系、作者信息、摘要组织、章节顺序、公式体系、讨论深度、引用体系和
   大部分成熟文字。
5. 不创建新的短论文，不把 28/27 页成熟稿压缩成 11 页，不采用新的论文 scaffold。
6. 不重写整段或整节，只要局部替换数字、术语、几何描述、图、表和相关推论即可完成。
7. 不重新设计参考文献库；优先保留母版现有引用和文末参考文献。
8. 不改写 `M05NEW/README.md`、数据表或既有审计文件。
9. 不使用 subagent，不并行委派论文段落或图表，避免不同代理各自改写成熟文本。
10. 不运行任何新输运、活化、探测器响应或大统计模拟。

建议输出文件：

- `core_md/balloon511_ea_latex_drafts/M05NEW/balloon511_ea_draft_en_sg3_sh3_revision_20260821.tex`
- `core_md/balloon511_ea_latex_drafts/M05NEW/balloon511_ea_draft_en_sg3_sh3_revision_20260821.pdf`
- `core_md/balloon511_ea_latex_drafts/M05NEW/balloon511_ea_draft_zh_sg3_sh3_revision_20260821.tex`
- `core_md/balloon511_ea_latex_drafts/M05NEW/balloon511_ea_draft_zh_sg3_sh3_revision_20260821.pdf`

## 2. 必须先复习的项目上下文

按以下顺序阅读；阅读是为了正确替换母版，不是为了重新构思论文：

1. 根目录 `AGENTS.md`。
2. 本交接文件。
3. 上述两份母版 TeX；同时查看两份 PDF 的最终排版和图表位置。
4. `core_md/balloon511_ea_latex_drafts/M05NEW/README.md`。
5. `core_md/balloon511_ea_latex_drafts/M05NEW/M05_PAPER_DATA_TABLE.csv`。
6. `core_md/balloon511_ea_latex_drafts/M05NEW/REFERENCES.md`。
7. `core_md/balloon511_ea_latex_drafts/M05NEW/M05NEW_VALIDATION.json`。
8. `core_md/balloon511_ea_latex_drafts/M05NEW/SG3B_OPTV3_COMPARISON.json`。
9. `core_md/balloon511_ea_latex_drafts/M05NEW/MXC_BPE_PLASTIC_REVIEW.md`。
10. `engineering/particle_source_unit_repair_20260811/README.md`、
    `data/source_contract_manifest.json` 和 `data/static_validation.json`。
11. `engineering/geometry_optimization_20260815/66_m05new_mxc_bpe_veto_review_20260821/README.md`
    与 `outputs/assessment.json`。

复习完成后，在 commentary 中给出“母版槽位 → 新数据/新图表来源”的简短映射，然后直接
在母版复制件上修改。不要提出新提纲，不等待用户重新确认。

## 3. 必须保留的原论文逻辑

保留母版已经成熟的基本因果结构：

1. 511 keV 气球望远镜的科学目标与仪器需求。
2. 参考探测器和低温系统质量模型。
3. 信号、瞬发大气本底、活化产生和延迟衰变的模拟与归一方法。
4. 探测器响应、主动 veto、拓扑/视场选择和任务时间折叠。
5. 从参考几何的 selected-event 本底来源中识别限制因素。
6. 引入优化几何。
7. 用完整 cut-flow、本底组成和任务灵敏度证明优化可行。
8. 讨论、适用范围与结论。

原论文中“参考几何 → 本底分析 → 优化几何 → 性能论证”的逻辑完全保留。只把旧参考和旧
优化数据替换成 SG3 参考几何与 SH3 烟囱几何的当前口径。

## 4. 当前物理替换口径

旧论文建立在 `Mass_model_511` 与 S3d 早期结果上。当前修正的关键不是增加 BPE，也不是
增加塑料正电子否决层，而是把 TES 从 MXC/分级冷盘正下方横向移入侧向烟囱，并使用烟囱
周围的 BGO 主动屏蔽。

新论文仍用参考几何承担本底来源诊断，用 SH3 烟囱几何承担最终优化结果：

- 参考几何：SG3 当前可审计基线。
- 优化几何：SH3 侧向烟囱中的 TES 焦平面和 BGO 主动屏蔽。
- 冷盘/MXC selected delayed 占比：`32.18% -> 3.92%`。
- 有效面积：`15.12324 +/- 0.04492 cm2 -> 15.08544 +/- 0.04503 cm2`。
- day-15 成熟最终本底：`0.05128019 cps -> 0.009280 cps`。
- 20 d Gaussian 3 sigma 最小可分辨通量：
  `(5.4058 +/- 0.4014)e-5 -> (2.2294 +/- 0.2086)e-5 ph cm^-2 s^-1`。
- 优化几何保留参考几何 `99.75%` 的有效面积，本底降至 `18.10%`，Fmin 改善约 `2.43` 倍。

所有具体替换以 `M05_PAPER_DATA_TABLE.csv` 为唯一入口，以 `REFERENCES.md` 回到来源文件。
不得从本交接文件的舍入值反向计算论文表格。

## 5. 源模型的必要局部修正

母版含有独立大气单能 511 keV 背景分支。当前源合同中，宽带 gamma 已经包含大气湮没
隆起，因此不能保留独立 mono-511 流。

这项修正只允许在受影响位置做局部修改：

- workflow 图及其图注；
- Source construction 中对应的小节和直接相关段落；
- background-source table；
- 与第四条 event catalogue、单能线占有率、单独大气线本底直接相关的公式、结果和讨论；
- 摘要和结论中直接引用该分量的句子。

不要借此重写整章模拟框架。保持母版章节顺序和解释风格，把四 catalogue/独立线分支改成
当前闭合的 focused signal、prompt atmospheric field、activation/delayed 三条物理链即可。

## 6. 图与表的逐槽位替换

英文母版含 10 个图位和 7 个表位；中文稿保持对应位置。不得另起一套三图论文。

### 图位

1. `fig:mass_model`：替换为当前 SG3 参考探测器/低温系统几何图。
2. `fig:workflow`：保留原工作流图的功能和位置，更新为当前三条物理链。
3. `fig:expacs_fullsphere_flux`：替换为 corrected-keV 八类全空间源图。
4. `fig:s33_poisson`：用当前共时间轴/归一验证数据重画。
5. `fig:s33_spec_norm`：用当前目录重画 veto 前响应谱。
6. `fig:s33_spec_anti`：用当前目录重画 BGO veto 前后谱。
7. `fig:s33_compton_mult`：用当前命中多重性与最终拓扑选择数据重画。
8. `fig:background_origin_story`：用当前 SG3/SH3 family、nuclide、volume/material 来源重画，
   保持其“本底由什么决定”的论证功能。
9. `fig:optimized_shield_background`：在原槽位替换为 SH3 烟囱几何及其本底结果。已有
   MXC/冷盘—TES 同尺度剖面可以作为主要面板或制图依据，但要与母版该图的论证功能衔接。
10. `fig:optimized_mission_significance`：用当前 81 节点任务数据重画显著度与最小可分辨通量。

### 表位

1. `tab:background_source_model`：当前 corrected-keV 八类源和 activation/delayed 定义。
2. `tab:phase2_cutflow`：SG3 参考几何 cut-flow。
3. `tab:reference_background_budget`：SG3 当前本底组成。
4. `tab:final_geometry`：SH3 烟囱几何尺寸与 BGO 主动屏蔽。
5. `tab:optimized_cutflow`：SH3 当前完整 cut-flow。
6. `tab:optimized_component_precision`：SH3 当前分量统计精度。
7. `tab:primary_sensitivity`：SG3/SH3 当前任务性能和统计误差。

允许根据当前数据调整单个图的面板组成，但不得删除母版图位、改变整篇图表节奏，或把成熟
论文压缩成少量新图。新图必须服务原槽位已有的论证问题。

## 7. 只改数据所必需的文字

允许修改：

- 旧数值及其比较倍数；
- 旧几何名称、材料、尺寸和屏蔽描述；
- 旧 source/cut-flow/统计定义；
- 依赖旧数值的摘要、结果、讨论和结论句子；
- 图注、表题和正文中的交叉引用说明；
- 为使中英文一致所需的对应句子。

禁止修改：

- 与新旧数据无关的科学背景和文献综述；
- 已成熟的 Laue lens、TES、观测目标和仪器需求叙述；
- 不受源合同修正影响的公式推导和方法解释；
- 文章标题体系、章节顺序和整体行文风格；
- 作者、单位、基金、声明和原有参考文献格式。

不要增加新的研究问题、外部对标、投稿指南段落、AI 声明、额外 future work 或材料优化讨论。

## 8. BPE 与塑料层

BPE 和塑料正电子否决层不是当前优化方案。论文应正面描述最终采用的烟囱与 BGO 结构，
而不是写一段方案淘汰史。

不要在标题、摘要、主结果、最终几何表或结论中加入 BPE/塑料讨论。除非母版某个局部句子
无法在不澄清的情况下正确修改，否则正文不提它们。

禁止写成“最终设计没有 BPE”“BGO-only”“移除了塑料层”之类的变更日志。直接描述最终
几何包含的 TES、烟囱、BGO、冷盘和必要支撑结构。

## 9. 禁止内部变量名和多余注解

投稿正文、表题和图注应让审稿人不看代码也能理解。

不得使用 `M05NEW`、`SH3_OPTV3_60cm`、`Step05`、`W2`、`R21`、round、batch、receipt、
PASS 字符串、路径、脚本名或内部字段名。使用物理语言，例如：

- `510.58--511.42 keV science window`
- `reference geometry`
- `optimized chimney geometry`
- `active BGO anticoincidence`
- `final topology and field-of-view selection`

禁止 SOL 风格的多余注解：如果正文已经正确陈述最终设计，就不要再用括号或句尾补充“未
使用某旧设计”“与旧版本不同”“不是某内部方案”。论文不是项目变更日志。

## 10. 禁止复用的错误任务产物

任务 `01a02314-a50b-78d2-bb8c-b43ffa350704` 错误地重新写了一篇 11 页论文。不得读取、
复制、合并或借用该独立 worktree 中的以下产物：

- `balloon511_ea_m05new_en.tex/.pdf`
- `m05new_chimney_tes_bgo_paper.tex`
- `references.bib`
- 它新建的三图论文体系和 figure scripts
- `MANUSCRIPT_BUILD_VALIDATION.md`
- 它重写的 `M05NEW/README.md`

新任务只从本工作区的两份 20260810 `pre_framework_rewrite` 母版和当前 M05NEW 数据权威
开始。

## 11. HASHI/hash、验证和资源边界

- 除非执行前能说明具体收益以及现有 validation 为什么不能回答，否则不做新的 HASHI/hash
  验证，不扩展 hash 清单，不编写 hash 审计工具。
- 不运行新输运。
- 制图优先读取 CSV/JSON；需要 NPZ 时只读所需数组并注意内存。
- 允许的验证只有：数值与主表一致性、双语对应、图表交叉引用、LaTeX 编译、PDF 页面可视
  检查以及原母版零修改确认。
- 不用新建大段 validation 报告；在最终回复简洁说明检查结果即可。

## 12. 执行步骤

1. 只读复习文件，并列出 10 图、7 表和受影响文本位置的替换映射。
2. 复制两份母版 TeX 到建议输出名。
3. 先替换表格和对应数值，再替换图，再局部修订正文。
4. 完成英文后，同步相同改动到中文，保持两版一致，不重新翻译无关段落。
5. 编译两份 TeX，检查引用、交叉引用、图表、公式和页面。
6. 搜索并清除残留旧数值、独立 mono-511 分支、旧 Mass_model/S3d 最终结论和内部变量名。
7. 对照母版确认章节、图表槽位、论证密度和成熟文字均被保留。

## 13. 完成判据

- 四个母版文件没有任何修改或删除。
- `M05NEW` 中产生英文和中文修订 TeX/PDF。
- 文章仍然是原来的成熟论文，而不是新写的短论文。
- 10 个图位和 7 个表位全部由当前口径填充，或在原槽位内完成等价更新。
- 参考几何、本底诊断、SH3 烟囱优化和任务性能的原论文逻辑保持完整。
- SG3/SH3 数值与 `M05_PAPER_DATA_TABLE.csv` 一致。
- 没有独立 mono-511 背景流，没有 BPE/塑料优化叙事。
- 没有内部代码变量、路径或变更日志式多余注解。
- 英文和中文均编译成功，图表与交叉引用正确。
- 没有新输运、没有无收益的 HASHI/hash 验证、没有 subagent。
