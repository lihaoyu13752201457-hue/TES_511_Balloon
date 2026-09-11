# 已废止：不得执行

本文件错误地把任务定义成“重新写一篇论文”，与用户要求不符。不得再将本文件作为任务
入口。正确入口是同目录：

`M05_TEMPLATE_DATA_REPLACEMENT_HANDOFF_20260821.md`

以下内容仅保留为错误交接审计记录。

# M05NEW 新论文 Session 交接文件

日期：2026-08-21  
工作区：`/home/ubuntu/TES_511_Balloon`  
执行模型：`gpt-5.6-sol`，reasoning effort=`ultra`

## 1. 本 Session 的唯一目标

在不删除、不覆盖原 M05 论文的前提下，使用已经闭合的当前数据，撰写一份新的、面向
Experimental Astronomy 投稿的英文论文。新论文应由审稿人仅凭论文中的物理定义、几何、
方法、图表和引用即可理解，不要求审稿人知道项目目录、脚本或内部变量。

原论文必须保留：

`core_md/balloon511_ea_latex_drafts/m05_atm511_source_revision_20260811/`

所有新稿和新生成的论文图表只能写入：

`core_md/balloon511_ea_latex_drafts/M05NEW/`

建议新稿主文件：

`core_md/balloon511_ea_latex_drafts/M05NEW/balloon511_ea_m05new_en.tex`

## 2. 开始写作前必须按顺序复习

1. 仓库根目录 `AGENTS.md`。
2. `core_md/balloon511_ea_latex_drafts/M05NEW/README.md`。
3. `core_md/balloon511_ea_latex_drafts/M05NEW/M05_PAPER_DATA_TABLE.csv`。
4. `core_md/balloon511_ea_latex_drafts/M05NEW/REFERENCES.md`。
5. `core_md/balloon511_ea_latex_drafts/M05NEW/M05NEW_VALIDATION.json`。
6. `core_md/balloon511_ea_latex_drafts/M05NEW/SG3B_OPTV3_COMPARISON.json`。
7. `core_md/balloon511_ea_latex_drafts/M05NEW/MXC_BPE_PLASTIC_REVIEW.md`。
8. 原 M05 英文稿：
   `core_md/balloon511_ea_latex_drafts/m05_atm511_source_revision_20260811/balloon511_ea_draft_en_m05_atm511_source_revision_20260811.tex`。
9. `engineering/particle_source_unit_repair_20260811/README.md`、
   `data/source_contract_manifest.json` 和 `data/static_validation.json`。
10. `engineering/geometry_optimization_20260815/66_m05new_mxc_bpe_veto_review_20260821/README.md`
    与 `outputs/assessment.json`。

以上文件复习完成后，先在自己的 commentary 中用不超过十条说明论文主线、当前物理权威、
必须删除的旧叙述和准备采用的章节结构，然后立即开始写稿，不等待用户再次确认。

## 3. 必须理解的项目主线

原 M05 是以 `Mass_model_511` 与 S3d 早期口径为基础的论文，包含旧参考质量模型、旧分级
屏蔽结构、独立大气单能 511 keV 分量以及后来确认不再成立的若干数值。旧的保留稿只作为
文章结构、固定仪器背景和既有文献入口，不能直接沿用其物理结果。

当前物理权威来自修复后的八类大气粒子源、当前探测器响应、共时间轴 prompt/activation/
delayed 链和当前任务积分。宽带 gamma 源已经包含大气湮没隆起，论文中不得再建立一条独立
的单能大气 511 keV 背景流。

当前优化不是通过增加 BPE 或塑料正电子否决层实现的。最终设计的核心是：

- 把 TES 焦平面从 MXC 和分级冷盘的正下方横向移入侧向烟囱；
- 保持聚焦光路和有效面积；
- 用围绕烟囱的 BGO 主动屏蔽降低进入科学窗的本底；
- 通过同一粒子源、同一响应、同一选择和同一任务时间轴，与参考几何进行匹配比较。

精确 delayed-source 回连显示，冷盘/MXC 相关贡献在参考几何中占 `32.18%`，在烟囱几何中
降至 `3.92%`。烟囱几何保留参考几何 `99.75%` 的有效面积，把 day-15 成熟本底降至
参考几何的 `18.10%`，把 20 d、3 sigma 最小可分辨通量改善约 `2.43` 倍。

## 4. 新论文应保留的逻辑

正文采用以下紧凑因果链：

1. 说明气球平台 511 keV 窄线观测为什么由 prompt 与 activation 本底限制。
2. 给出参考探测器—低温系统几何和统一的信号、本底、响应与选择定义。
3. 用参考几何的 selected-event 来源分析定位冷盘、MXC 和 TES 邻近材料的空间耦合。
4. 引入侧向烟囱几何，解释它如何使 TES 脱离上方冷盘投影，同时保持聚焦光路。
5. 在完全匹配的源合同、响应、选择和 20 d 时间轴下比较参考几何与烟囱几何。
6. 报告有效面积、本底、显著度、最小可分辨通量和统计误差。
7. 讨论结果适用范围，不扩展成新的屏蔽材料优化研究。

参考几何承担因果诊断和定量基线；烟囱几何承担论文主结果。不要把两者写成两篇并列论文。

## 5. 论文数值权威

论文数据替换只以 `M05_PAPER_DATA_TABLE.csv` 为入口，并按 `REFERENCES.md` 回到来源文件。
当前表有 100 个唯一槽位、零空单元、全部旧稿表图均有映射，验证状态为
`21/21 PASS__M05NEW_ALL_REQUIRED_DATA_CLOSED`。

主结果必须保持：

- 烟囱几何最终有效面积：`15.08544 +/- 0.04503 cm2`。
- day-15 成熟最终本底：`9.280e-3 cps`。
- 参考通量 `1e-4 ph cm^-2 s^-1` 下的 day-15 信号率：`9.7904e-4 cps`。
- 20 d Gaussian 3 sigma 最小可分辨通量：
  `(2.2294 +/- 0.2086)e-5 ph cm^-2 s^-1`。
- 20 d Asimov 3 sigma 值：`2.2383e-5 ph cm^-2 s^-1`。
- 参考几何最终有效面积：`15.12324 +/- 0.04492 cm2`。
- 参考几何 day-15 成熟本底：`5.128019e-2 cps`。
- 参考几何 20 d Gaussian 3 sigma 最小可分辨通量：
  `(5.4058 +/- 0.4014)e-5 ph cm^-2 s^-1`。

表中 `READY` 可直接写入。`DERIVABLE` 表示已有全部物理数据，只需制图或制表，不得因此
启动新的输运。`REMOVE_OLD_MODEL` 必须从新论文删除。`OPTIONAL_REMOVE` 默认删除。

## 6. BPE 与塑料层的处理

BPE 和塑料正电子否决层只属于内部设计历史，不是新论文的优化主线。正文应直接、正面描述
最终采用的烟囱和 BGO 结构，不写被放弃结构的变更日志。

除非某处必须解释参考几何差异，否则正文不要讨论 BPE 或塑料层。即使必须讨论，也只允许
一句物理范围说明，不能把它写成新结果。当前数据已经表明：源初正电子没有 prompt-final
残余；中子诱发 delayed 只占 direct-final 的约 `8.00%`，不足以把最小可分辨通量从
`2.229e-5` 推到 `1.5e-5`。不要为 BPE 或塑料层再跑模拟。

## 7. 禁止 SOL 风格的多余注解

论文只陈述最终科学内容，不写内部修改痕迹。以下做法禁止：

- 不写“最终设计没有 BPE”“BGO-only”“删除了独立 mono-511”等变更日志式表述；直接写
  最终设计包含什么、源模型如何定义。
- 不写“与旧版本不同”“修复后”“此前错误”“未采用某方案”，除非这一历史事实是理解
  当前物理定义不可缺少的。
- 不在标题、表题、图注或正文中加入解释作者工作过程的括号。
- 不把未采用的备选方案列在最终几何表中。
- 不把内部审计结论、PASS 字符串、路径、哈希、seed、round、batch、package 编号写进正文。
- 不使用项目内部变量名作为审稿人必须理解的术语，例如 `M05NEW`、
  `SH3_OPTV3_60cm`、`W2`、`Step05`、`R21`、`direct_final_no_coincidence`。应改写为
  “optimized chimney geometry”“510.58--511.42 keV science window”
  “final topology selection”等审稿人可直接理解的物理表述。
- 不增加与文章主结论无关的百科式解释、额外方案、额外验证或 future-work 清单。

交接文件、数据引用表和内部构建记录可以保留内部名称；投稿论文正文、表题和图注不能依赖
这些名称。

## 8. HASHI/hash 验证约束

除非能在执行前清楚说明某项 hash 验证将发现什么具体风险、该风险如何影响论文结论，并且
现有 validation/manifest 不能回答，否则不要做新的 HASHI/hash 验证。不得为了显示严谨而
重复计算文件哈希、扩展哈希清单或编写新的哈希审计工具。

当前引用完整性、关键输入哈希和统计闭合已有记录。新 Session 的主要工作是论文写作、
派生制图、数值替换和 LaTeX 验证，不是再做一轮数据取证。

## 9. 运行与安全边界

- 不运行 Cosima/Geant4，不打开大型 SIM payload，不新建输运 campaign。
- 生成图时优先读取现有 CSV/JSON；必须读取 NPZ 时只加载所需数组并先检查内存。
- 不删除、改名或覆盖原 M05 目录及其中任何文件。
- 不改动保留的工程包；新脚本、图、表、TeX 和 PDF 写入 `M05NEW`。
- 不恢复旧 factor-1000 结果，不恢复独立单能大气 511 keV 分量。
- 不为了形式完整增加不影响 EA 主结论的模拟、敏感性扫描或材料研究。

## 10. 必须完成的论文产物

1. 新的英文 LaTeX 主稿 `M05NEW/balloon511_ea_m05new_en.tex`。
2. 使用当前数据替换摘要、方法、结果、讨论和结论中的全部旧数值与旧源定义。
3. 论文所保留的表格全部使用当前数据。
4. 论文所保留的图全部更新；可以合并或删除不能服务主线的旧图，但不得留下旧数据图。
5. 使用已经生成的 MXC/冷盘—TES 同尺度二维剖面作为几何因果图，或将其内容整合进更简洁
   的最终几何图。
6. 完成 LaTeX 编译并生成 PDF；解决正文、图表、交叉引用和参考文献错误。
7. 最终检查正文中没有旧 mono-511 分支、旧数值、内部路径、内部变量名和多余变更注解。

新论文必须保持 EA 论文所需的紧凑程度。只要已有数据能够支撑结论，就直接完成论文；只有
在一个缺口会改变主要数值或主结论时才向用户请求决定。

## 11. 完成判据

只有同时满足以下条件才算完成：

- 原 M05 文件零修改、零删除。
- 新英文稿和 PDF 位于 `M05NEW`。
- 参考几何到烟囱几何的物理因果链清楚。
- 主要数值与数据表和 validation 一致。
- 所有保留图表均为当前数据。
- 论文不依赖代码知识即可理解。
- 没有 HASHI/hash 式重复审计、没有新输运、没有多余方案和多余注解。
