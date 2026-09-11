# M05 SG3/SH3 当前 Session 总交接

- 日期：2026-08-25
- 状态：`CURRENT_ENTRY__SG3_SH3_CONSOLIDATED`
- 指定模型：`gpt-5.6-sol`，reasoning effort=`ultra`

## 0. 唯一入口与绝对路径

后续 Session 以本文件为唯一当前入口：

`/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/core_md/balloon511_ea_latex_drafts/M05NEW/M05_CURRENT_SESSION_HANDOFF_20260823.md`

当前 `M05NEW` 不是一个可整体视为“未跟踪”的目录：其中既有已跟踪但尚未提交的修改，也有
本轮新增的未跟踪图件、脚本和小型数据摘要。新 Session 不得执行 clean、reset、checkout 或用
另一工作树覆盖这些状态。即使新 Session 运行在 `/home/ubuntu/TES_511_Balloon` 或另一个 Codex
工作树，也必须按本文件给出的 `ebb2` 绝对路径读取和继续当前稿件；不得因为自己的相对路径中
缺少文件，就改读主项目中的旧稿或同名历史文件。

本文件已经合并项目总览、M05 方法流程和当前论文交接，只保留 SG3 与 SH3 两个质量模型。
后续 Session 不需要再从历史交接拼接项目主线。第 7--10 节记录了已经完成的单能 511 keV
补充任务；该任务不再是待执行工作。

## 1. 合并范围与当前两个质量模型

本文件吸收了以下两份历史入口中仍适用于当前工作的内容：

- `engineering/m04_validation_geometry_handoff_20260810/SESSION_BOOTSTRAP.md` 提供的“先复习项目、
  再复习论文”、证据链和接手顺序；
- `engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/NEXT_SESSION_REVIEW_OUTLINE.md`
  提供的 M05 三分支流程、统一后处理和本底来源驱动优化思路。

这两份历史文件不再是新 Session 的执行合同，其中的旧几何、旧数值、旧源处理状态和旧优化方向
不得带入当前工作。当前几何范围只有：

1. **SG3 / 质量模型 A**：参考几何。六层 TES 位于混合室和多级冷盘下方，用于建立信号、本底、
   活化来源和任务灵敏度基线，并识别邻近冷端质量对选后本底的耦合。
2. **SH3 / 质量模型 B**：由 SG3 来源分析提出的侧烟囱几何。六层 TES 横向移入侧烟囱，保留
   相同探测器核心、Laue 光学输入、源定义、响应和事例选择，以评价几何重组能否降低本底并保留
   聚焦信号接受度。

`M05_TEMPLATE_DATA_REPLACEMENT_HANDOFF_20260821.md` 只记录母版原有的 10 个图位、7 个表位和替换
边界；当前稿件已在此基础上扩展为 12 幅图、7 张表，复制与替换已经完成，不得重做。
`NEW_PAPER_SESSION_HANDOFF_20260821.md` 是已废止的错误
交接，不得执行其新写论文、建立 scaffold 或重建参考文献库的指令。

严禁读取或复用错误任务 `01a02314-a50b-78d2-bb8c-b43ffa350704` 的产物。

### 1.1 项目主线

本项目研究一台用于球载窄线观测的 511 keV Laue 聚焦谱仪：Laue 透镜把天区 511 keV 光子
聚焦到六层 TES 微量热计阵列，探测器与小型稀释制冷机、多级冷盘、屏蔽和支撑结构组成完整
探测器--低温系统质量模型。项目的核心任务不是只计算一个静态探测效率，而是在同一物理口径下
同时计算聚焦信号、瞬发大气本底和材料活化后的延迟本底，经过共同探测器响应与事例选择，再沿
飞行时间和参考轨迹折叠，得到累计计数、未分辨 511 keV 线灵敏度及其统计误差。

论文采用两阶段几何论证。质量模型 A 是参考几何（工程记录中的 SG3），用于识别 TES 邻近冷盘、
混合室及其上方结构对选后本底的贡献；依据来源分解提出质量模型 B（工程记录中的 SH3），把 TES
布置到侧烟囱并重新组织主动 BGO 与局部屏蔽。两模型保持相同的 Laue 光学输入、TES 定义、源场、
响应和筛选口径，比较其有效面积、本底组成、任务累计计数和最小可分辨通量。论文的主要论证链是：

`质量模型 A -> 本底来源与几何耦合分析 -> 质量模型 B -> 同口径信号/本底比较 -> 任务灵敏度评价`

这里的几何优化目标是降低会进入 TES 活跃区并通过最终选择的本底，同时尽量保留聚焦接受度。
当前论文不再扩展第三种质量模型或另一条屏蔽优化主线。

### 1.2 图 2 是项目的流程地图

新 Session 在阅读全文前应先查看当前论文图 2：

- 中文流程图：`/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/core_md/balloon511_ea_latex_drafts/M05NEW/figures/fig02_workflow_zh.pdf`
- 英文流程图：`/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/core_md/balloon511_ea_latex_drafts/M05NEW/figures/fig02_workflow_en.pdf`

图 2 按三条物理分支组织整个项目：

1. 聚焦信号：511 keV 参考点源经过独立 Laue 光学质量模型，形成焦平面光子相空间，再进入
   探测器侧完整质量模型。
2. 瞬发大气本底：EXPACS/PARMA 宽带连续谱与粒子场形成宽带瞬发事例目录；PARMA 给出的
   511 keV 线积分通量和角分布形成独立单能线事例目录。
3. 延迟活化本底：同一大气粒子场经过 BUILDUP 活化产生输运，记录核素产额、材料体积和产生
   位置，经飞行时间积累形成核素清单和延迟衰变源，再输运为延迟活化事例目录。

三条分支最终产生四类探测器侧事例目录。四类目录统一经过探测器响应、主动 veto 和 Compton
拓扑检验，得到选后信号率和分量本底率；一条分析支路按粒子族、母核素和产生体积分解本底以指导
质量模型 B，另一条沿任务时间--轨迹折叠并计算累计计数和未分辨线灵敏度。图末端的几何优化节点
表示结果对方案评价的反馈，不表示质量模型 B 在其自身输运和任务折叠之后才被定义。

### 1.3 当前共同模拟与分析合同

SG3 与 SH3 的比较必须保持以下口径一致：

1. 聚焦信号使用同一组 37,194 条 Laue 焦平面光子相空间记录；信号侧使用相同的大气透射、
   探测器响应、科学窗和偶然符合处理。
2. 瞬发与活化产生均使用八族大气粒子场：质子、中子、α、γ、电子、正电子、负 μ 子和正 μ 子。
   宽带能量轴采用总动能 keV 约定；α 输入按每核子能量转换为总动能。
3. 大气 γ 源采用“宽带总量减去粗能箱内的线贡献，再加入同一 PARMA 大气状态下的
   510.99895 keV 单能线”。宽带与单能线各计数一次。
4. 瞬发分量按各粒子族自己的输运曝光归一；延迟分量按入射粒子族、母核素、材料体积和模拟记录
   的产生位置建立飞行时间核素清单，再输运衰变事例。
5. 四类事例目录统一施加预估的 420 eV FWHM TES 响应、像素阈值、
   `510.58 <= E_TES < 511.42 keV` 科学窗、主动反符合和 Compton 拓扑选择；不能跨几何混合事例，
   也不能让 SG3 与 SH3 使用不同的 TES 响应或拓扑定义。420 eV 是器件响应假设，不是把
   `sigma` 设为 420 eV，也不是已经实测的硬件指标。
6. 任务计算使用五个公共时间锚点和 81 个任务节点，分别得到 day-15 率、20 d 累计信号与本底、
   Gaussian/Asimov 最小可分辨通量及统计误差。

当前主动反符合的精确定义如下，后续不得从图面标签反推或自行简化：公共时间轴按相邻到达时刻
不超过 `1 us` 的传递链接规则形成符合候选组；每组内全部 BGO 体的沉积统一求和。质量模型 A
还将全部塑料闪烁体沉积另行求和，并要求 `E_BGO < 50 keV` 且 `E_plastic < 50 keV`；质量模型 B
没有塑料通道，仅要求 `E_BGO < 50 keV`。等于阈值时拒绝。阈值针对整个候选组内各探测器类别的
总沉积，不是逐 hit、逐 volume 判断，也不是把 BGO 与塑料先相加为一个量。相同门控用于四类
事例目录；聚焦信号作为条件探针加入相应本底时间轴，以测量偶然符合存活率。

理解顺序应始终是：先核对源与几何，再核对四类事例目录和共同选择，最后读取任务折叠与灵敏度；
不能从最终 Fmin 反推中间步骤已经正确。

上述合同是论文比较目标。当前响应和统计链已经同口径，但 SG3/SH3 的物理入口与 W 准直结构仍有
第 5.6 节所述差异，因此质量模型 B 的新 Fmin 暂按条件结果处理。

## 2. 当前论文成品

唯一当前英文稿：

- `/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/core_md/balloon511_ea_latex_drafts/M05NEW/balloon511_ea_draft_en_sg3_sh3_revision_20260821.tex`
- `/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/core_md/balloon511_ea_latex_drafts/M05NEW/balloon511_ea_draft_en_sg3_sh3_revision_20260821.pdf`

唯一当前中文稿：

- `/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/core_md/balloon511_ea_latex_drafts/M05NEW/balloon511_ea_draft_zh_sg3_sh3_revision_20260821.tex`
- `/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/core_md/balloon511_ea_latex_drafts/M05NEW/balloon511_ea_draft_zh_sg3_sh3_revision_20260821.pdf`

2026-08-25 最新编译成品为英文 28 页、中文 28 页，均为 A4；两版各有 12 幅图、7 张表。
最新 TeX/PDF 的唯一绝对路径即上列四个文件。双语稿已通过 XeLaTeX/latexmk 编译、引用检查和
相关页面目视检查：没有未定义引用、重复 label、Overfull 或致命错误。图均在
`M05NEW/figures/`。这四个文件已经完成 SG3/SH3 数据替换和本轮方法重排，不再执行一次
“复制母版再替换”的流程。

当前第 3 节结构是：3.1 Laue 光学与探测器耦合信号输运；3.2 源构建，其中 3.2.1 瞬发大气源、
3.2.2 大气 511 keV 线源、3.2.3 延迟活化源、3.2.4 参考点源构建；3.3 探测器响应、事例选择与
veto 定义，其中 3.3.1 时间轴与率归一、3.3.2 探测器响应/科学窗/带权率、3.3.3 主动反符合门、
3.3.4 Compton 拓扑与视场一致性；3.4 任务时间轨迹与解析率折叠。主动 veto 的数值 cut-flow 与
BGO 抑制图已移到第 4.3 节“全链本底与统计支撑”，方法部分只保留定义和实现约定。

本轮已经落实的内容不得在新 Session 中恢复为旧稿：

- 3.2.2 只保留粗网格线扣除、独立 `510.99895 keV` 单能线、80 个等 `mu` 远场分量和实际
  重权/独立输运方法；已删除与论文论证无关的混合模板自我辩护句。
- 3.2.3 说明通过 Geant4 `SteppingAction` 保存模拟产生坐标，再按材料体积、核素、激发态和
  坐标与 day-15 清单匹配并按活度抽样。每个入射族输运 `10^6` 个延迟衰变，因此每个质量模型
  均为 `8 x 10^6` 个延迟触发；科学窗、主动反符合和 Compton 拓扑后 A/B 分别保留 394/111 条。
  A 的 day-15 活度以 p=724.2736、n=330.0210、alpha=287.5411 Bq 为主；B 以 p=105.5262、
  n=68.5316、alpha=34.2836 Bq 为主。A 的 511 keV 邻近延迟来源包括 L2 铜支撑环和 50 mK
  混合室板中的 `62Cu`；B 以 L5 铜环和 TES 热沉环中的 `62Cu` 为主。逻辑图 4 位于本小节。
- 3.3.1 先解释为什么在轨迹参考点可用独立齐次泊松过程，再把不同物理率的目录映射到公共时间轴；
  五个参考点为 day 0/5/10/15/20，后续 20 d 轨迹以 6 h 间隔形成 81 节点。公式化的 `rho/eta`
  展开已从叙述主线中省去，但本底时间重叠修正和聚焦信号偶然符合存活仍进入任务折叠。
- 3.3.2 将 420 eV 明确为预估 FWHM 响应，并使用左闭右开的
  `[510.58, 511.42) keV` 科学窗；内禀宽度不可忽略的源线必须与响应卷积并重新优化窗宽。
- 3.3.3 使用第 1.3 节记录的探测器类别总和门；方法只写定义，第 4.3 节报告 day-15 direct、
  no-coincidence cut-flow。A 为 2391 条/5.77556 cps 到 456 条/0.0688770 cps；B 为
  6657 条/2.29831 cps 到 330 条/0.0328175 cps。孤立科学窗聚焦信号 A/B 的 28,612/28,434 条
  均通过主动门；公共时间轴上的偶然损失另由任务折叠处理。

当前逻辑图号必须按 LaTeX label 识别，不能由资产文件名中的旧编号推断：

1. `fig:mass_model`：质量模型 A 总览，资产 `fig01_mass_model_a_{zh,en}.pdf`；
2. `fig:workflow`：端到端流程地图，资产 `fig02_workflow_{zh,en}.pdf`；
3. `fig:expacs_fullsphere_flux`：大气粒子场；
4. `fig:activation_source_positions_zh` / `fig:activation_source_positions`：A/B 活化产生位置及科学窗相关母核素；
5. `fig:poisson_time_axis_schematic`：泊松公共时间轴示意；
6. `fig:s33_spec_norm`：主动 veto 前带权能谱；
7. `fig:s33_compton_mult`：A/B 最终 TES 命中多重度；
8. `fig:common_time_anchors`：五个公共时间锚点；
9. `fig:background_origin_story_zh` / `fig:background_origin_story`：选后本底来源；
10. `fig:optimized_shield_background_zh` / `fig:optimized_shield_background`：质量模型 B 烟囱几何与选后本底；
11. `fig:s33_spec_anti`：质量模型 B 主动 BGO 抑制，位于结果第 4.3 节；
12. `fig:optimized_mission_significance_zh` / `fig:optimized_mission_significance`：81 节点任务性能。

图 11 的正文位置和图注已经修正，但现有 `fig06_bgo_veto_spectrum.pdf` 图面仍残留内部 `W2`、
`Plastic`、重复的 active-veto stage 和 `no hardware-efficiency claim` 等旧标签。它是当前明确的待清理图件，
不得把这些图面残留解释为质量模型 B 存在塑料通道；重绘前先获得用户授权，并沿用现有小型数据，
不要为此重跑输运。

四个 2026-08-10 `pre_framework_rewrite` 母版仍是结构和成熟文字来源，必须只读：

- `core_md/balloon511_ea_latex_drafts/balloon511_ea_draft_en_m04_atm511_revision_20260804_pre_framework_rewrite_20260810.tex/.pdf`
- `core_md/balloon511_ea_latex_drafts/balloon511_ea_draft_zh_m04_atm511_revision_20260804_pre_framework_rewrite_20260810.tex/.pdf`

不得修改或删除母版。不得把当前稿重新压缩成短论文，不建新 scaffold，不重建参考文献库。

## 3. 新 Session 的强制阅读顺序

### 第一层：任务边界和全文

1. 仓库根目录 `AGENTS.md`。
2. 本文件全文；先理解第 1.1 节项目主线。
3. 查看第 1.2 节列出的中英文图 2，把它作为后续论文、代码和数据路径的总地图。
4. `/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/core_md/balloon511_ea_latex_drafts/M05NEW/M05_TEMPLATE_DATA_REPLACEMENT_HANDOFF_20260821.md`，
   只用于理解母版与替换边界，不重做已完成步骤。
5. 当前英文 TeX 和 28 页 PDF，必须完整阅读。
6. 当前中文 TeX 和 28 页 PDF，必须完整阅读；检查物理含义和内部说明口吻是否与英文一致。

### 第二层：当前数据与几何口径

7. `/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/core_md/balloon511_ea_latex_drafts/M05NEW/README.md`：
   了解当前 SG3/SH3 发布状态和质量模型 B 的准直接受度争议；其中编译 `PENDING` 是数据包生成时
   状态，当前稿件状态以本文件第 2 节为准。
8. `/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/core_md/balloon511_ea_latex_drafts/M05NEW/M05_PAPER_DATA_TABLE.csv`：
   论文槽位数值入口。
9. `/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/core_md/balloon511_ea_latex_drafts/M05NEW/REFERENCES.md`：
   槽位到来源文件的索引。
10. `/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/core_md/balloon511_ea_latex_drafts/M05NEW/M05NEW_VALIDATION.json`
    和 `/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/core_md/balloon511_ea_latex_drafts/M05NEW/SG3B_OPTV3_COMPARISON.json`：
    内部数值一致性。
11. `/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/engineering/geometry_optimization_20260815/63_m05new_sg3b_signal_statistics_20260820/README.md`：
    SG3 自有信号、扩统计背景和匹配任务结果。
12. `/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/engineering/geometry_optimization_20260815/sh3/assembly_opt_v3/README.md`：
    SH3 几何、机械边界和 detector declarations。
13. `/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/engineering/geometry_optimization_20260815/67_m05_mono511_flux_closure_20260823/outputs/06_publication_values/publication_values.json`：
    SG3/SH3 追加结果的数值入口。
14. `/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/engineering/geometry_optimization_20260815/67_m05_mono511_flux_closure_20260823/outputs/04_validation/topup_decision.json`：
    单能线统计量 `NO_TOPUP` 裁决。

### 第三层：只针对争议点深化

15. 当前源合同：
    - `/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/README.md`
    - `/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/data/source_contract_manifest.json`
    - `/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/data/static_validation.json`
16. SH3 事件和时间线只先读摘要与小表：
    - `/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/DEEPSEEK_CODE/outputs/04_event_catalog_step05_m05_fixed_20260820/summary.json`
    - `/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/DEEPSEEK_CODE/outputs/04_event_catalog_step05_m05_fixed_20260820/direct_cutflow_totals.csv`
    - `/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/DEEPSEEK_CODE/outputs/05_mature_timeline_m05_fixed_20260820/summary.json`
    - `/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/DEEPSEEK_CODE/outputs/05_mature_timeline_m05_fixed_20260820/mission_timeline_81nodes.csv`
17. Laue 外部/独立验证边界：
    - `/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/engineering/ea_peer_review_m08_laue_validation_20260715/README.md`
    - `/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/engineering/ea_peer_review_m08_laue_validation_20260715/reports/M08_VALIDATION_REPORT_ZH.md`
18. 只有在追查 OpenCode 执行问题时，才读取
    `/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/DEEPSEEK_CODE/OPENCODE_SESSION_M05_AUDIT_20260820.md`；
    其中旧结果由本文件第 4.1、7 和 8 节覆盖。

初次复习禁止递归打开全部 job catalog、大型 SIM、完整 NPZ 或哈希清单。只有一个具体物理
问题无法从摘要、CSV 和正文回答时，才读取对应的最小数组或事件记录。

## 4. 历史工程结果与当前论文权威值

以下数值来自单能 511 keV 源级重组前的匹配分析，只用于追溯工程演化，不得重新写回当前论文
的总本底、累计本底或 Fmin。源级通量闭合后的第 4.1 节数值已经取代这些旧总率和旧灵敏度；
“保留旧结果”只表示不删除工程记录，不表示新旧两套结果应在投稿正文并列：

- SG3 最终有效面积：`15.12324 +/- 0.04492 cm2`。
- SH3 最终有效面积：`15.08544 +/- 0.04503 cm2`，为 SG3 的 `99.75%`。
- SG3 day-15 最终本底：`0.05128019 cps`。
- SH3 day-15 最终本底：`0.009280 cps`，为 SG3 的约 `18.10%`。
- SG3 20 d Gaussian 3 sigma Fmin：`(5.4058 +/- 0.4014)e-5 ph cm^-2 s^-1`。
- SH3 20 d Gaussian 3 sigma Fmin：`(2.2294 +/- 0.2086)e-5 ph cm^-2 s^-1`。
- 当前匹配口径下 Fmin 改善约 `2.43` 倍。
- selected delayed 中 `DR/MXC + staged cold plates` 占比由 `32.18%` 降至 `3.92%`。该来源分解
  不依赖大气单能线是否并入瞬发总率，仍可用于当前几何解释。
- 当前内部数据检查为 `21/21 PASS`；它证明表、源文件、事件目录和时间线之间按既定合同
  一致，不证明源模型、光学、BGO 硬件或整机本底已被外部实验验证。

### 4.1 当前论文权威值：单能 511 keV 源级重组后

下列通量闭合结果是当前中英文论文正文、表格和任务性能图使用的唯一总率与灵敏度口径；它们
取代上一段的旧总本底和旧 Fmin，但不删除其工程历史：

- 质量模型 A：day-15 最终本底 `0.060595953980508585 cps`，20 d 累计本底
  `99923.14165545377 counts`，20 d Gaussian 3 sigma Fmin
  `(5.79993 +/- 0.39118)e-5 ph cm^-2 s^-1`。
- 质量模型 B：day-15 最终本底 `0.03122834776990912 cps`，20 d 累计本底
  `54805.970088911905 counts`，20 d Gaussian 3 sigma Fmin
  `(4.18516 +/- 0.15629)e-5 ph cm^-2 s^-1`（暂时有异议）。
- 该追加口径中的 Gaussian 3 sigma Fmin 比值为 `A/B = 1.3858322146`。
- 单能线统计量判断已经完成；质量模型 A 与 B 均为 `NO_TOPUP`。

论文主线仍是：SG3 参考几何定位冷盘/MXC 邻近本底耦合，SH3 把 TES 横向移入侧烟囱并以
BGO 主动反符合降低科学窗本底。当前比较只包含这两个质量模型。

## 5. 当前不能宣称“完全物理闭合”的问题

独立只读审稿任务 `01a024de-763a-70e1-a0ae-72a594959892` 完整阅读了四份成品，裁决为
`NOT CLOSED / Major revision`。这是审稿意见，不自动取代项目数据；后续 Session 应逐条判定
“确实需补证”“只需收窄表述”或“已有本地证据可部分回答”。主要问题如下。

### 5.1 整机范围与遗漏本底

当前本底质量模型主要覆盖探测器和低温系统。Laue 晶体/支撑、吊舱/平台以及视场内天体或
弥散光子未完整进入总本底，却在标题、摘要和结论中被外推为整台球载 Laue 望远镜的绝对
灵敏度。最小处理可以是把结论明确限定为“探测器—低温系统预算下的条件式/理想下限”；
只有坚持整机绝对灵敏度时，才需要补入遗漏本底的约束。

### 5.2 银河中心目标与固定 45 度参考轨迹

稿件使用纬度约 `+34 deg`、固定 `45 deg` 仰角并持续在源的参考折叠。银河中心赤纬约
`-28.9 deg`，在该纬度最大仰角仅约 `27 deg`。当前数值可作为抽象的 45 度轴上窄线参考，
不能直接称为真实银河中心 20 d 指向预测。该问题通常只需收窄科学声明，或重做可见性、
大气透过和在源时间折叠，不必重跑探测器输运。

### 5.3 零计数高权重分量的总不确定度

Table 6 有多个最终零计数分量，单分量 Garwood 上限较大；当前
`sqrt(sum w_i^2)` 对零条记录给出零观测方差。应检查总本底区间是否需要联合 Poisson/似然
或明确的保守上限，而不是仅报告中心值的 delta-method 误差。只有联合区间仍不可用时，才
考虑对少数高权重分量增加定向统计。

### 5.4 主动反符合的 50/80 keV 接口

当前分析对 SG3 和 SH3 都使用 `50 keV` 的离线 Cosima 沉积能量门；两个质量模型的 BGO
detector declaration 都给出 `80 keV` native trigger 参考。50 keV 结果因此是理想的离线门控
假设，必须说明 TES 触发时 BGO 是否连续读出或被强制同步读出，从而保留 50--80 keV 沉积。
质量模型 A 的塑料闪烁体与 BGO 分别求和、分别过门；质量模型 B 没有塑料通道。

旧交接曾记录 70/80 keV 阈值重放的百分比变化，但本轮在交接列出的项目内小型摘要、CSV/JSON
和论文上下文中没有找到可直接追溯这些精确数字的来源。因此这些百分比暂不作为当前论文权威，
也不得在新 Session 中直接引用；若要恢复，必须先补入明确的项目内来源。当前可以可靠陈述的
边界只有：论文报告 50 keV 理想离线门，硬件 50--80 keV 读出映射仍需校准或定义。

### 5.5 Laue 光学只部分闭合

M08 验证状态为 `PARTIAL_PASS`：反射率 `R` 在 65/65 点通过，步长收敛通过；完整 R/T/A
只有 29/65 点通过，最大 T/A 系统差约 3.75 个百分点。更重要的是，当前 production 等价
`gaussian_plane` 点源 `d90=0.406226 cm`，比 HEART 参考宽 `51.93%`；经验证的
`gaussian_outgoing` 得到 `d90=0.265752 cm`，与解析和 HEART 均在约 1% 内。

18 mm footprint 的 Be 门通过率变化很小，所以当前有效面积中心值预计变化不大；但 PSF
不能宣称闭合。当前 SG3/SH3 信号源仍追溯到保留的 Step09 EventList：

`stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/eventlists/Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat`

完成 production 出射角修正并重建 EventList 前，Aeff 可称部分验证，PSF 不可称最终验证。

### 5.6 大气 511 keV 源已闭合；当前争议是 SG3/SH3 几何可比性

源级重组已经完成：从 PARMA 宽带总量中扣除粗能箱内的湮没线贡献，再以同一大气状态给出的
积分通量和角分布加入 `510.99895 keV` 单能线。SG3 与 SH3 的单能线响应、五个时间锚点、
81 节点折叠和统计量判断均已完成，两者均为 `NO_TOPUP`。不得再把这一项写成待执行任务，也
不得把单能线直接叠加到仍含同一线面积的宽带输入。

质量模型 B 的 `4.18516e-5 ph cm^-2 s^-1` 标记为“暂时有异议”，原因不是单能线统计量不足，
而是当前 SG3 与 SH3 的入口和 W 准直结构并非严格匹配：SG3 使用较小入口包络及多孔准直结构，
SH3 使用半径 2.70 cm 的窗口和开放四边 W 框。因此该值是当前 SH3 完整设计的条件结果，尚不能
单独归因于 TES 移入侧烟囱。后续若处理这一异议，应在“把 SH3 作为整体替代设计”与“建立匹配
准直接受度的 SH3”两种论文口径中选择；不需要重复已经完成的单能线统计补跑。

该异议尚未在当前论文正文中完全落实：正文仍有“相同入口/仅改变烟囱结构/受控单变量比较”一类
偏强表述。新 Session 在用户授权继续修改时，应优先把这些句子收窄为“同一分析合同下两个完整
设计的条件比较”，或在确有匹配准直接受度证据后再恢复更强因果表述；不得把
`4.18516e-5 ph cm^-2 s^-1` 无条件归因于侧烟囱本身。

### 5.7 活化与 TES 的外部验证等级

- exact-position lineage、NUBASE 基态半衰期处理和同时间轴递推是内部验证；它们不等于绝对
  核素产额/活度的实验验证。稿件还应明确初始库存 `N(0)`、地面预活化和上升段边界，尤其
  是在报告 `0.724 d` 早期 3 sigma 时间时。
- `0.420 keV` TES FWHM 与 511-CAM 的约 `0.390 keV` 设计目标数量级相容，但尚未在本文
  的 `1.5 x 1.5 x 3 mm` absorber/TES 堆栈上实测。它应标为响应假设，不能写成已验证硬件
  指标。未来最直接的实验闭合是 `22Na` 的 511 keV 标定和 `133Ba` 增益转移。

### 5.8 当前仍待用户决定的论文编排和图面问题

- 图 4 同时显示全部活化产生位置（源构建信息）和彩色的科学窗选后母核素（结果信息），目前
  放在 3.2.3；图 6--8 及部分 cut-flow 也仍位于方法章节。它们是否继续留作方法示意，还是移到
  第 4 节，应由用户结合论文叙事决定，不得由新 Session 批量搬移。
- 图 11 的数值、正文位置和图注已按当前结果修正，但图面仍含内部 `W2`、无作用的 `Plastic`
  阶段、重复的 active-veto 阶段和 `no hardware-efficiency claim` 防御性标注。后续只需重绘图面，
  不应因此改变数据或重跑模拟。
- 后续引用图号时使用 LaTeX label 和 `.aux` 的当前逻辑编号，不要按 `fig04`、`fig06` 等历史
  资产文件名猜测图号。

## 6. “粉红大象”与人类论文口吻

独立审稿定位了以下高优先模式。后续若获授权修改，只做局部删除或改成直接肯定陈述，不得
因此重写整篇论文。

1. 反复写 `corrected/repaired total-kinetic-energy`，把旧能量轴错误和修复史召回正文。
   科学正文只需定义输入是 keV 总动能，alpha 表是 MeV/n。
2. 源方法只需直接说明“宽带中扣除粗能箱线贡献，再加入同一 PARMA 状态下的单能线”；不要
   反复解释旧模型做错了什么，也不要把已经完成的源级重组写成未来任务。
3. `all 480 references resolve`、十二位小数归一范围、路径/包/审计状态属于内部 QA，不应在
   投稿正文作为物理证据。
4. `retained/current/auditable/source contract/closure/closed` 等词把多版本管理带入论文；
   改成普通科学术语，如 reference geometry、input spectrum、validation comparison。
5. `rather than a reduced detector cartoon`、`not a flat, infinite absorber plate`、
   `not a visual comparison`、`no fitted empirical correction` 会引入读者原本不会假定的前提。
6. Laue 章节解释“process class 只处理 transport interface”属于代码职责，不是物理方法。
7. Data availability 中仍有 `Before publication... should provide` 和
   `To be completed before journal submission`，这是作者内部 TODO，应在投稿前变成最终声明。

双语还需注意：中文图 1 把 cylinder axis 写成“烟囱轴”；中文“按实际产生位置抽样”比英文
recorded production position 更强，应改成“按模拟记录的核素产生位置抽样”。

## 7. 2026-08-23 已完成的单能 511 keV 补充

大气单能 511 keV 数值补充已经完成，不再是待执行任务。实际源级组合为

`broadband total - coarse-bin line contribution + monoenergetic line`

质量模型 A/B 均已完成匹配的单能线响应目录、宽带去线重权、五个公共时间锚点、81 节点任务
折叠、累计本底、Gaussian/Asimov Fmin 与误差传播。第 4.1 节的通量闭合结果是当前论文权威值；
第 4 节开头的旧总率和旧 Fmin 只保留为工程历史，不得重新并列写入投稿正文。

当前工程入口为：

- `/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/engineering/geometry_optimization_20260815/67_m05_mono511_flux_closure_20260823/`
- 发表值：`outputs/06_publication_values/publication_values.json`
- 统计量裁决：`outputs/04_validation/topup_decision.json`

统计量裁决为质量模型 A/B 均 `NO_TOPUP`。质量模型 A 使用 3,000,000 个入射单能光子并有
12 个最终选后事例；质量模型 B 使用 15,709,417 个入射单能光子并有 186 个最终选后事例。
除非用户明确提出新的统计精度目标或发现具体实现错误，新 Session 不得重复补跑或追加统计量。

历史包 57/58 只用于追溯单能线尚未合入旧宽带结果的阶段；新 Session 不得再以它们为当前状态，
也不得把旧 sidecar 直接叠加到含同一线面积的宽带结果。

## 8. 单能 511 keV 已完成项与复习要求

以下工作已经完成：

1. 宽带粗能箱线贡献扣除与 510.99895 keV 单能线恢复。
2. 质量模型 A/B 的匹配响应、共同 TES 响应、科学窗、BGO 反符合和拓扑选择。
3. 五个公共时间锚点与 81 节点任务折叠。
4. day-15 本底、20 d 累计本底、Gaussian/Asimov Fmin 与误差传播。
5. 单能线对总本底及 Fmin 方差的贡献评估；A/B 均裁决为 `NO_TOPUP`。
6. 当前中英文稿、结果表与图件已经回填并重新编译；两版均为 28 页、12 幅图、7 张表，最新
   稿件只使用第 2 节的绝对路径。

新 Session 应复习上述结果和来源，不得把这些条目重新列为待办。质量模型 B 的
`4.18516e-5 ph cm^-2 s^-1` 当前标记为“暂时有异议”，不得在未处理该异议前把它提升为无条件
最终值；同时不得把第 4 节开头的历史总率和旧 Fmin 恢复进当前论文正文。

## 9. 执行和论文边界

- `ebb2/M05NEW` 当前含用户保留的未提交修改与新增资产。不得执行 `git clean`、`git reset`、
  `git checkout --` 或从其他工作树覆盖文件；新 Session 开始时只做最小 `git status` 和目标文件
  检查，不做全目录 manifest。
- 单能 511 keV 的 Cosima/Geant4、探测器响应、81 节点折叠和统计量判断均已完成；除非用户明确
  重新授权，不得重复运行、继续 top-up 或重建同一统计链，也不得扩展到 SG3/SH3 之外的几何。
- RAM/磁盘安全优先：先检查可用内存和磁盘；流式读取大目录；一次只处理一个几何或一个阶段；
  不把完整 SIM/NPZ 同时载入内存；采用非覆盖、可续跑的 dated 输出目录；每轮开始前估算峰值空间，
  每轮结束后写最小 receipt。若预计资源超过本机安全余量，先给出量化需求和缩减方案。
- 不做无明确收益的 hash、manifest 扩展或二进制一致性审计。只有能说明它将解决哪一个物理或
  可复现性问题时，才做最小 HASHI/hash 验证。
- 不恢复 factor-1000 历史结果，不读取错误任务
  `01a02314-a50b-78d2-bb8c-b43ffa350704` 的任何产物。
- 不删除或修改 M05/M04 母版，不新建论文 scaffold 或参考文献库，不把当前成熟稿改写成另一篇论文。
- 投稿正文只使用审稿人可理解的物理名称。`SG3`、`SH3`、sidecar、step 编号、内部目录名和
  `PASS/authority/closure` 等仅可出现在工程记录中；正文继续使用“质量模型 A/B”。
- 禁止多余注解：删掉一个不采用的方案后，不在正文写“未采用该方案”；不加入项目版本史、代码
  职责、内部审计状态或无助于论证的括号说明。
- 保留仍适用的粉红标注，并在分页变化后迁移；已经被正文修正的旧批注不应制造新的旁注提醒。

## 10. 可直接交给 GPT-5.6 SOL Ultra 新 Session 的启动提示

```text
请完整阅读并严格执行：
/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/core_md/balloon511_ea_latex_drafts/M05NEW/M05_CURRENT_SESSION_HANDOFF_20260823.md

这是当前 M05 SG3/SH3 论文的唯一入口。先完整理解第 1.1--1.3 节并查看中英文图 2，把图 2 作为
端到端流程地图；再严格按第 3 节的分层顺序完整阅读当前 28 页英文稿和 28 页中文稿，以及列出的
最小 README、CSV、JSON 摘要。不要递归扫描大型 SIM、NPZ、完整 job catalog、历史输出或哈希
清单。当前项目只比较 SG3（质量模型 A）与 SH3（质量模型 B），论文逻辑是“SG3 基线 -> 本底
来源与几何耦合分析 -> SH3 侧烟囱 -> 同口径任务灵敏度比较”；不要带入其他质量模型、旧优化
方向或旧源口径。

当前双语稿均为 28 页、12 幅图、7 张表。3.2.2 已独立构建大气 511 keV 线；3.2.3 已写入精确
位置活化源、A/B 分族活度和 511 keV 邻近母核素；3.3.1--3.3.3 已重排为泊松公共时间轴、TES
响应/科学窗和详细主动反符合方法，主动 veto 的数值结果与图 11 已移至 4.3。先核对这些当前内容，
不得按旧图号或旧章节结构回退。

大气单能 511 keV 的源级重组、A/B 匹配响应、五个公共时间锚点、81 节点折叠和统计量判断已经
完成，A/B 均为 NO_TOPUP。第 4.1 节的通量闭合值是当前论文唯一的总率和灵敏度权威；旧总率和
旧 Fmin 只保留为工程历史，不得恢复进投稿正文。质量模型 B 的
4.18516e-5 ph cm^-2 s^-1 因 SG3/SH3 当前入口和 W 准直结构不完全匹配而暂时有异议，原因不是
单能线统计量不足；在解决几何可比性前，只能作为完整 SH3 设计的条件结果。

主动反符合以 1 us 公共时间分组为单位累计能量：质量模型 A 的 BGO 与塑料分别求和且分别要求
小于 50 keV；质量模型 B 无塑料，只要求 BGO 总沉积小于 50 keV。50 keV 是理想离线门，两个
模型的 BGO detector declaration 均有 80 keV native trigger 参考，硬件读出映射仍是待处理边界。
图 11 现有图面仍含 W2、Plastic、重复 active-veto stage 和内部 QA 标注；若用户要求修图，只清理
图面并复用现有数据，不重跑输运。

完成只读复习后，先向用户紧凑报告你对项目主线、当前稿件状态、条件结论和真正未解决问题的
理解；在收到新的具体论文修改指令前不要改论文、代码或数据，不要启动模拟。不要重写成熟论文，
不要删除 M05，不做无收益的 HASHI，不读取或复用错误任务
01a02314-a50b-78d2-bb8c-b43ffa350704 的任何产物，并保护 ebb2 工作树中的现有未提交修改。
```

## 11. 当前保护边界

当前允许修改的论文文件仅为本交接第 2 节列出的中英文 TeX/PDF、其直接图件、数据表与引用索引。
M05/M04 母版和历史稿只读。所有新模拟与派生数据必须进入新的 dated 目录，不覆盖既有工程结果。
