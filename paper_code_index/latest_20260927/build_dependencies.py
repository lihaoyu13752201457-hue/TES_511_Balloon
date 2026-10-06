#!/usr/bin/env python3
"""Record hand-checked direct code edges with literal-source line evidence."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
P = OUT.parents[1]
W = P / "paper_review_workspace_20260920"
R = W / "outputs/00_parent"
A = R / "activation_correction_20260924"
F = A / "production_repair_20260925"
G = P / "engineering/geometry_optimization_20260815"
E = Path("/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute")
V = R / "revision_20260921_AA_continuous/code"
O = R / "final_manuscript_20260926_activation/code"
S = W / "outputs/02_sources_response_compton/corrected_optics_signal_20260920/code"
EDGES = [
    (O / "update_figures.py", V / "retained_figure_styles.py", "retained_figure_styles.py", "最终图表沿用已审定样式"),
    (O / "update_figures.py", R / "revision_20260921_pro_figures_markers/code/draw_figures.py", "draw_figures.py", "图10保留已审定功能几何，只更新来源标记"),
    (O / "build_environment_figure.py", G / "71_m05_sh3_environment_screening_20260830/code/build_environment_screening.py", "build_environment_screening.py", "最终图17使用同一环境模型"),
    (G / "71_m05_sh3_environment_screening_20260830/code/build_environment_screening.py", G / "65_sh3_complete_l2_solar_activity_20260820/code/build_complete_l2_solar.py", "build_complete_l2_solar.py", "动态装载完整L2模型"),
    (G / "65_sh3_complete_l2_solar_activity_20260820/code/build_complete_l2_solar.py", G / "64_sh3_l2_environment_projection_20260820/code/build_sh3_environment_projection.py", "build_sh3_environment_projection.py", "环境谱模型继承"),
    (A / "code/common.py", V / "common.py", "code/common.py", "修正响应适配器继承原响应定义"),
    (V / "common.py", V / "pixel_geometry_compton.py", "from pixel_geometry_compton", "像素中心/顶点及实际几何判选"),
    (V / "common.py", V / "continuous_disk.py", "from continuous_disk", "连续圆锥和光学spot相交核"),
    (V / "common.py", P / "engineering/particle_source_unit_repair_20260811/seven_family_tes_activation_postprocess_20260812/code/analyze_seven_family_tes_activation.py", "analyze_seven_family_tes_activation.py", "只提取固定响应命名空间和带键随机数函数，不采用旧结果"),
    (V / "pixel_geometry_compton.py", V / "legacy_side_compton.py", "legacy_side_compton.py", "固定康普顿运动学核"),
    (S / "pixel_geometry_compton.py", S / "legacy_side_compton.py", "legacy_side_compton.py", "信号响应的固定运动学核"),
    (F / "code/build_runtime.py", A / "code/targeted_environment.py", "from targeted_environment", "逐核态响应程序的构建环境和父包源码"),
    (F / "code/build_production_runtime.py", A / "code/targeted_environment.py", "from targeted_environment", "普通生产模式仅修复时间索引"),
    (F / "code/analyze_production.py", A / "code/decay_kernel.py", "decay_kernel", "核态、寿命及生成—衰变核"),
    (R / "AA_run_20260921_v1/code/aa_common.py", E / "run.py", "EXEC/'run.py'", "工作副本8633的规范执行器"),
    (R / "AA_run_20260921_v1/code/aa_common.py", E / "prepare.py", "EXEC/'prepare.py'", "规范源卡构建和种子登记"),
    (R / "AA_run_20260921_v1/code/aa_common.py", E / "common.py", "import common as C", "执行器共用安全门和原子写入"),
    (R / "AA_run_20260921_v1/code/aa_common.py", G / "68_sg3_minimal_sd_prompt_supplement_20260823/code/build_minimal_alpha_pilot.py", "build_minimal_alpha_pilot.py", "只复用敏感体定义构建函数，不切换最终AA物理几何"),
]


def main():
    indexed = {r["source_path"] for r in json.loads((OUT / "INDEX.json").read_text())["files"]}
    edges = []
    for consumer, provider, needle, why in EDGES:
        assert str(consumer) in indexed and str(provider) in indexed, (consumer, provider)
        matches = [i for i, line in enumerate(consumer.read_text().splitlines(), 1) if needle in line]
        assert matches, (consumer, needle)
        edges.append({"consumer": str(consumer), "provider": str(provider), "evidence_lines": matches, "literal_evidence": needle, "reason_zh": why})
    result = {
        "scope": "Hand-checked core edges, not exhaustive runtime dependency discovery",
        "code_edges": edges,
        "numeric_authority": str(F / "final/data/RESULTS.json"),
        "manuscript_numeric_consumer": str(O / "build_manuscript.py"),
        "figure_data_inputs": [str(R / "activation_manuscript_proposal_20260926/FIG10_NEW_POSITIONS_a.csv"), str(R / "activation_manuscript_proposal_20260926/FIG10_NEW_POSITIONS_b.csv"), str(W / "outputs/04_results_environments_conclusions/numeric_sync_20260920/data/parent_nuclide_figure_data.json")],
        "data_preservation_warning": "Code backup does not replace raw data, corrected input spectra, seed/receipt ledgers or third-party installations. No deletion is authorized by this index.",
    }
    (OUT / "DEPENDENCIES.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print("Verified literal evidence for", len(edges), "core code edges")


if __name__ == "__main__":
    main()
