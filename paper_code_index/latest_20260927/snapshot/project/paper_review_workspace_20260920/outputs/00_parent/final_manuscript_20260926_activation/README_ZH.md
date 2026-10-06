# 最新完整稿：活化修正与已审定文字收尾

完成日期：2026年9月27日。目录沿用9月26日本轮开始时的名称。

- [完整PDF](/home/ubuntu/TES_511_Balloon/paper_review_workspace_20260920/outputs/00_parent/final_manuscript_20260926_activation/paper_clean.pdf)
- [TeX正文](/home/ubuntu/TES_511_Balloon/paper_review_workspace_20260920/outputs/00_parent/final_manuscript_20260926_activation/paper_clean.tex)
- [完整可编译源包](/home/ubuntu/TES_511_Balloon/paper_review_workspace_20260920/outputs/00_parent/final_manuscript_20260926_activation/paper_source.zip)
- [本轮修改标注PDF](/home/ubuntu/TES_511_Balloon/paper_review_workspace_20260920/outputs/00_parent/final_manuscript_20260926_activation/paper_this_edit_marked.pdf)
- [原稿备份包](/home/ubuntu/TES_511_Balloon/paper_review_workspace_20260920/outputs/00_parent/final_manuscript_20260926_activation/original_backup.zip)
- [GPT Pro上传包](/home/ubuntu/TES_511_Balloon/paper_review_workspace_20260920/outputs/00_parent/final_manuscript_20260926_activation/gptpro_review_package.zip)

## 本轮落实

1. 使用9月25日已完成的活化处理与生产记录修复结果，更新方法、正文、7张表和9张结果图。没有新开模拟，没有修改原项目或旧论文。
2. 1 μs处逐字加入用户提供的英文动机句（仅以TeX表示单位），未另加脉冲恢复时间的说明。
3. 核数据说明简化为Er-158未生成有效衰变产物及所用补充数据，明确Ho-158是配套子核能级，未把它误写为另一项已证实的独立衰变失败。
4. 落实8项精简意见：删除摘要统计限定句、重复的不确定度边界、记录数说明、偶然符合保留率结果段、摘要/总结的重复保留率、16.4天换算、L2末尾优先级说明及延迟等效曝光末句。方法中的必要定义保留。
5. 保留原稿有效术语（如inventory、isolated event和经定义的parent nuclide），只统一确有需要的保留率及邻近结构用语。流程图原有Activity buildup涵盖活化累积，保持已有图文表述。
6. 图8/10保持已认可的功能剖视、黑白斜线BGO和核素标记方案；图10只更新来源位置与分类，其他结果图使用新的分量权重、能谱和积分数据。

## 核心结果

| 量 | Under-stage | Lateral-chimney |
| --- | ---: | ---: |
| 第15天选后延迟本底率 / s⁻¹ | 0.037462 | 0.004412 |
| 第15天逐事例总本底率 / s⁻¹ | 0.050240 | 0.012087 |
| 20天累计本底计数 | 83004 | 20534 |
| 20天累计信号计数 | 2974 | 3122 |
| 20天3σ通量 / 10⁻⁵ ph cm⁻² s⁻¹ | 6.97 ± 0.51 | 3.30 ± 0.28 |

通量阈值改善约2.11倍。表4中的时间叠加本底行保留相应模拟计数和率，与逐事例直接率分列。

## 交付检查与独立审阅

完整PDF为36页。全部交叉引用和文献引用有定义，现有数字参考文献按首次引用顺序排列，未出现缺字或排版溢出。已独立从选后位置目录求和核对延迟率和标准误差，并从81节点率重新积分核对累计计数和灵敏度。原稿及图件备份校验通过。

本会话没有直接提交GPT Pro或创建用户侧栏会话的工具。已使用独立审阅代理，调用参数明确指定gpt-6-astra和ultra；这是独立代理审阅，不是GPT Pro或新侧栏会话。审阅已完成：[独立全文审阅报告](/home/ubuntu/TES_511_Balloon/paper_review_workspace_20260920/outputs/00_parent/final_manuscript_20260926_activation/independent_review/REVIEW_ZH.md)。审阅认为主体已具备初次送审所需的文本清晰度，未建议重写或新增模拟。两项引用依据收尾、两项统计表述建议、三处可选词组及期刊样式适配已单列；这些审阅新建议尚未并入正文。另提供可手动上传GPT Pro的简约提示词和论文包，未声称已经上传。

作者其余单位、贡献确认、资助、利益冲突及数据/代码可用性仍保留已知待填标记；本轮没有替作者编造这些信息。

## 追溯

- CHANGES.json记录55处实际文字/表格变更。
- data/包含本轮绘图和数值检查所需的小型结果表；模拟产物仍留在原目录。
- validation/FINAL_CHECKS.json包含检查结果。
- baseline/及original_backup.zip包含修改前完整稿和图件。
- 标注稿正文采用新增蓝线/删除红线；更新图加蓝框，更新表以完整蓝色新版表显示，避免新旧数字挤出页面，旧表可对照备份。
