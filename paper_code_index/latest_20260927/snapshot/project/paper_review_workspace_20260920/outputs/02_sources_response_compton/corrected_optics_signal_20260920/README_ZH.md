# 新光学样本的信号输运与数字同步

计算、A源面专项闭合及本路稿件同步完成。物理结果为A 21,303/37,175、B 28,001/37,175；未运行本底生产、η或时间积分。

- [数值交接](/home/ubuntu/TES_511_Balloon/paper_review_workspace_20260920/outputs/02_sources_response_compton/corrected_optics_signal_20260920/NUMERIC_SYNC_HANDOFF_ZH.md) / [JSON](/home/ubuntu/TES_511_Balloon/paper_review_workspace_20260920/outputs/02_sources_response_compton/corrected_optics_signal_20260920/NUMERIC_SYNC_HANDOFF.json)：各阶段计数、保留率和MC误差、共用光学样本协方差、逐事件接口。
- [A源面闭合](/home/ubuntu/TES_511_Balloon/paper_review_workspace_20260920/outputs/02_sources_response_compton/corrected_optics_signal_20260920/validation/A_SOURCE_CLOSURE_ZH.md)：新样本旧内部注入对照为27,701条，单独保存、不混池；外部注入穿过实际前置材料。
- [最新论文入口](/home/ubuntu/TES_511_Balloon/paper_review_workspace_20260920/outputs/02_sources_response_compton/integrated_pixel_retention_20260920/README_ZH.md)：在既有中英文、截取及累计稿路径更新，仅替换3块中的数字。
- [最终验证](/home/ubuntu/TES_511_Balloon/paper_review_workspace_20260920/outputs/02_sources_response_compton/corrected_optics_signal_20260920/validation/FINAL_VALIDATION.json)。

源码依次为build_inputs.py、run_transport.py、analyze_signal.py、finalize_numeric.py；单独的内部诊断由build_internal_diagnostic.py构建，validate_source_closure.py完成射线/材料检查与对照。sync_manuscript_numbers.py记录已应用的纯数字更新。输运文件及注册种子均已使用，不得原地覆盖或重复并入统计。运行环境为现有MEGAlib/Cosima；原项目与其他fork目录均只读。
