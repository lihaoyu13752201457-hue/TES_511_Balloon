# S3d-O8 source-driven low-grammage screening

本目录记录 2026-08-14 的 S3d-O8 本底来源诊断和简单低面密度候选筛选。核心结论与工程路线见 [REPORT.md](REPORT.md)。

本包的权威边界是：

- 使用 corrected-keV M05 common-response 与 detector-selected lineage；
- prompt 追踪到 261 个 measured-W2 veto 前事件和 3 个主动层零沉积漏事件；
- delayed 追踪到冻结选择后的 135 行来源坐标；
- LC1/LC2 结果只用于来源驱动筛选，没有几何晋级权威；
- 没有把 mK scintillator、读出铜或复杂局部 guard 作为优化方案；
- 完整物理结论仍需新 BUILDUP、inventory、delayed transport、common response，以及热/结构/磁验证。

入口：

- `REPORT.md`：中文结论、来源机制、候选路线、文献与 stop/go 门；
- `analysis/s3d_o8_source_driven_optimization.ipynb`：已执行的可复算紧凑分析；
- `data/source_driven_optimization_summary.json`：机器可读汇总；
- `data/source_driven_analysis_validation.json`：一致性验证；
- `figures/source_budget_and_candidate_gate.png`：来源预算与 20 天任务门；
- `geometry/`：LC1/LC2 screening-only 几何；
- `code/`：构建、分析和验证脚本。

当前状态：`SOURCE_DIAGNOSIS_AND_SCREENING_COMPLETE__NO_GEOMETRY_PROMOTION_AUTHORITY`。
