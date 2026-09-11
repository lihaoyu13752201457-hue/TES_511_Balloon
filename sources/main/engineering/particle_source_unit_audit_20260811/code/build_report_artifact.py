#!/usr/bin/env python3
"""Build the canonical report artifact from reviewed unit-audit outputs."""

from __future__ import annotations

import csv
import base64
import json
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
DATA = PACKAGE / "data"
REPORT = PACKAGE / "report"
ARTIFACT = REPORT / "artifact.json"
GENERATED_AT = "2026-08-11T12:00:00+08:00"
TITLE = "TES-511 粒子源单位实证审计"

FAMILY_LABELS = {
    "alpha": "α",
    "eminus": "e⁻",
    "eplus": "e⁺",
    "gamma": "γ",
    "muminus": "μ⁻",
    "muplus": "μ⁺",
    "n": "n",
    "p": "p",
}

PACKAGE_LABELS = {
    "Mass_model_511": "Mass_model_511",
    "S3c_package32": "S3c（package 32）",
    "S3d_O8_package43": "S3d/O8（package 43）",
}


def read_csv(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def source(
    source_id: str,
    label: str,
    path: str,
    engine: str,
    code: str,
    description: str,
    tables_used: list[str],
    filters: list[str],
    metric_definitions: list[str],
) -> dict[str, object]:
    return {
        "id": source_id,
        "label": label,
        "path": path,
        "query": {
            "engine": engine,
            "sql": code,
            "description": description,
            "executed_at": GENERATED_AT,
            "tables_used": tables_used,
            "filters": filters,
            "metric_definitions": metric_definitions,
        },
    }


def main() -> int:
    summary = json.loads((DATA / "audit_summary.json").read_text(encoding="utf-8"))
    family_raw = read_csv("spectrum_family_audit.csv")
    package_raw = read_csv("source_package_reference_audit.csv")
    hash_raw = read_csv("evidence_hashes.csv")
    hashes = {row["source"]: row["sha256"] for row in hash_raw}
    query_text = (REPORT / "queries/evidence.sql").read_text(encoding="utf-8")
    chart_png = REPORT / "assets/energy_error_by_family.png"
    if not chart_png.is_file():
        raise RuntimeError(
            "missing static chart; run code/render_family_chart.py before building the artifact"
        )
    chart_data_uri = "data:image/png;base64," + base64.b64encode(
        chart_png.read_bytes()
    ).decode("ascii")

    gamma_scan = summary["retained_gamma_sim_corroboration"]
    eventlist = summary["eventlist"]
    parma = summary["parma_mono_line"]

    headline = [{
        "affected_families": len(family_raw),
        "bad_references": sum(int(row["legacy_2602unit_references"]) for row in package_raw),
        "energy_error_factor": 1000,
        "gamma_events_below_1keV": int(gamma_scan["events_below_1_keV"]),
        "gamma_records": int(gamma_scan["records"]),
    }]

    family_chart: list[dict[str, object]] = []
    family_table: list[dict[str, object]] = []
    for row in family_raw:
        family = row["family"]
        raw_unit = "MeV/n" if family == "alpha" else "MeV"
        family_chart.append({
            "family": family,
            "family_label": FAMILY_LABELS[family],
            "spectrum_files": int(row["spectrum_files"]),
            "dp_rows": int(row["dp_rows"]),
            "energy_error_factor": float(row["energy_error_factor"]),
            "legacy_over_correct": float(row["x_legacy_over_correct_max"]),
            "raw_energy_scale_to_total_keV": float(row["raw_energy_scale_to_total_keV"]),
            "raw_to_correct_energy_max_abs_delta_keV": float(row["raw_to_correct_energy_max_abs_delta_keV"]),
            "raw_to_correct_pdf_max_relative_delta": float(row["raw_to_correct_pdf_max_relative_delta"]),
            "correct_x_min_keV": float(row["correct_x_min_keV"]),
            "correct_x_max_keV": float(row["correct_x_max_keV"]),
            "legacy_x_min_interpreted_keV": float(row["legacy_x_min_interpreted_keV"]),
            "legacy_x_max_interpreted_keV": float(row["legacy_x_max_interpreted_keV"]),
            "card_flux_relative_delta": float(row["card_flux_relative_delta"]),
            "fullsphere_to_main_flux_ratio": float(row["fullsphere_to_main_flux_ratio"]),
            "energy_axis_verdict": row["energy_axis_verdict"],
            "flux_bookkeeping_verdict": row["flux_bookkeeping_verdict"],
        })
        family_table.append({
            "family_label": FAMILY_LABELS[family],
            "raw_unit": raw_unit,
            "required_scale": "×4000" if family == "alpha" else "×1000",
            "coverage": f"{int(row['spectrum_files'])} 文件 / {int(row['dp_rows']):,} 节点",
            "correct_rebuild": (
                "PASS；PDF最大相对差 "
                f"{float(row['raw_to_correct_pdf_max_relative_delta']):.3e}"
            ),
            "legacy_relation": "x = 0.001 × correct；y 完全相同",
            "verdict": "FAIL：实际能量 /1000",
        })

    package_table = [{
        "package": PACKAGE_LABELS[row["package"]],
        "coverage": f"{int(row['source_cards'])} 源卡 / {int(row['angular_bins'])} 角箱",
        "legacy_references": (
            f"{int(row['legacy_2602unit_references'])} / "
            f"{int(row['spectrum_references'])}"
        ),
        "correct_references": str(int(row["correct_keV_references"])),
        "verdict": "FAIL：160/160 指向 legacy",
    } for row in package_raw]

    unit_verdicts = [
        {
            "component": "八类 EXPACS/PARMA 连续谱能量",
            "expected": "DP x = 总动能 keV",
            "observed": "active x = correct x × 0.001",
            "result": "FAIL｜prompt、活化库存与 delayed 物理率失效",
        },
        {
            "component": "正确 DP 目录的 raw 转换",
            "expected": "MeV×1000；α 为 MeV/n×4×1000",
            "observed": "160/160 文件逐点闭合",
            "result": "PASS｜可作为修复输入；不等于旧输运已修复",
        },
        {
            "component": "显式 FarField Flux",
            "expected": "每角箱已积分 particles cm⁻² s⁻¹",
            "observed": "卡片和 manifest 相对差 ≤3.1×10⁻¹⁶",
            "result": "PASS｜修复能量时不要把 Flux 再乘/除1000",
        },
        {
            "component": "角度、立体角与 R=60 cm 面积",
            "expected": "deg；20箱总和4π；A=πR²",
            "observed": "源卡及 runner 算术闭合",
            "result": "PASS｜只证明归一化结构，不证明谱物理正确",
        },
        {
            "component": "独立 PARMA 大气 511-keV 单线",
            "expected": "0.51099895 MeV→510.99895 keV",
            "observed": "×1000；20/40/80箱 flux 闭合",
            "result": "PASS｜仅 source-level；不替代探测器响应闭环",
        },
        {
            "component": "Optics EventList",
            "expected": "15列；s、cm、keV",
            "observed": f"{eventlist['rows']:,} 行均15列、511 keV",
            "result": "PASS（格式）｜1 ns 时间仅排序；从 Be 窗注入",
        },
        {
            "component": "Delayed PointSource / Bq 账目",
            "expected": "cm、s⁻¹(Bq)、TT与NUBASE审计",
            "observed": "局部单位及守恒检查存在",
            "result": "条件 PASS｜上游库存由错误初级能谱生成，物理权威 FAIL",
        },
    ]

    authority_table = [
        {
            "product": "几何与材料定义本身",
            "unit_result": "不依赖该谱能量轴",
            "authority": "可保留为结构输入",
            "required_action": "不要把旧性能排序一并视为有效",
        },
        {
            "product": "三套八族 prompt 输运",
            "unit_result": "能量整体 /1000",
            "authority": "不可作为物理率/响应权威",
            "required_action": "八族全部重跑",
        },
        {
            "product": "活化 buildup / isotope inventory",
            "unit_result": "上游反应阈值与截面采样错误",
            "authority": "不可作为生产库存权威",
            "required_action": "用修复 prompt 重新生产",
        },
        {
            "product": "Delayed source 与 delayed transport",
            "unit_result": "局部 Bq/cm/TT 可闭合，上游库存错误",
            "authority": "局部账目可参考，物理结果不可发布",
            "required_action": "库存重建后重新生成并输运",
        },
        {
            "product": "PARMA 511-keV mono 模块",
            "unit_result": "source-level PASS",
            "authority": "可独立保留，响应闭环仍需完成",
            "required_action": "保持与 broadband 修复分离",
        },
        {
            "product": "Optics EventList 桥",
            "unit_result": "格式 PASS；人工时钟非曝光",
            "authority": "仅 Be-plane 注入范围有效",
            "required_action": "物理权重继续用 flux×Aeff×T",
        },
    ]

    locator_specs = [
        (
            "官方手册",
            "Spectrum File 的 x 是 keV，y 是每keV形状；Flux定绝对率",
            "MEGAlib/doc/Cosima.pdf，PDF p.27",
            "MEGAlib/doc/Cosima.pdf",
        ),
        (
            "MEGAlib 源码",
            "File谱 x 乘 keV；采样值直送 ParticleGun",
            "MEGAlib/src/cosima/src/MCSource.cc:1909-1918,2727-2729,2775-2778",
            "MEGAlib/src/cosima/src/MCSource.cc",
        ),
        (
            "采样源码",
            "累计积分归一化，统一 y 比例不会改变显式 Flux",
            "MEGAlib/src/global/misc/src/MFunction.cxx:791-813",
            "MEGAlib/src/global/misc/src/MFunction.cxx",
        ),
        (
            "参数解析源码",
            "FarField Flux 为 cm⁻²s⁻¹、角度为 deg、PointSource为cm",
            "MEGAlib/src/cosima/src/MCParameterFile.cc:1326-1334,1463-1469,2834-2846",
            "MEGAlib/src/cosima/src/MCParameterFile.cc",
        ),
        (
            "原始 γ 谱",
            "header 明示 MeV 与每MeV每sr",
            "expacs_fullsphere_20bin_sources/raw_expacs/spectrum_gamma_bin00_theta18.19_BHNo.dat:8-11",
            "expacs_fullsphere_20bin_sources/raw_expacs/spectrum_gamma_bin00_theta18.19_BHNo.dat",
        ),
        (
            "原始 α 谱",
            "header 明示 MeV/n；需转总 α 动能",
            "expacs_fullsphere_20bin_sources/raw_expacs/spectrum_alpha_bin00_theta18.19_BHNo.dat:8-11",
            "expacs_fullsphere_20bin_sources/raw_expacs/spectrum_alpha_bin00_theta18.19_BHNo.dat",
        ),
        (
            "正确 DP",
            "γ 首节点 0.011294 MeV→11.294 keV",
            "expacs_fullsphere_20bin_sources/cosima_spectra_dp/gamma_bin00_theta18.19_pdf.dat:1-4",
            "expacs_fullsphere_20bin_sources/cosima_spectra_dp/gamma_bin00_theta18.19_pdf.dat",
        ),
        (
            "错误 DP",
            "文件头自述把 archived keV 除以1000；首节点变0.011294",
            "expacs_fullsphere_20bin_sources/cosima_spectra_dp_2602units/gamma_bin00_theta18.19_pdf.dat:1-6",
            "expacs_fullsphere_20bin_sources/cosima_spectra_dp_2602units/gamma_bin00_theta18.19_pdf.dat",
        ),
        (
            "active 源卡",
            "Beam(deg)、legacy Spectrum、独立 Flux 同时可见",
            "engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/config/full_prompt_all8/source_cards/Background_gamma_fullsphere20.source:47-55",
            "engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/config/full_prompt_all8/source_cards/Background_gamma_fullsphere20.source",
        ),
        (
            "归一化 runner",
            "从卡片求 Flux，并用 t=N/(FπR²)",
            "code/tools/run_equiv2602_pipeline_NEW_GEO.py:354-380,433-447",
            "code/tools/run_equiv2602_pipeline_NEW_GEO.py",
        ),
        (
            "事件级 γ 审计",
            "1000万 IA INIT，线节点按 /1000 实际输运",
            "engineering/m04_validation_geometry_handoff_20260810/02_parma_atm511_repair_20260810/data/o8_prompt_gamma_line_dedup_audit.json",
            "engineering/m04_validation_geometry_handoff_20260810/02_parma_atm511_repair_20260810/data/o8_prompt_gamma_line_dedup_audit.json",
        ),
        (
            "旧结论冲突",
            "旧文称七个非γ族不受影响；本次穷举证明相反",
            "engineering/m04_validation_geometry_handoff_20260810/00_review/FROZEN_PREFIX_CORRECTION_PROPOSAL.md:164-180",
            "",
        ),
    ]
    evidence_locators = [{
        "layer": layer,
        "fact": fact,
        "locator": locator,
        "sha256_prefix": hashes.get(hash_key, "")[:12] if hash_key else "—",
    } for layer, fact, locator, hash_key in locator_specs]

    audit_source = source(
        "audit_sql",
        "全八族单位审计数据与查询",
        "queries/evidence.sql",
        "DuckDB + Python 3",
        query_text,
        "只读 Python 审计生成 CSV/JSON；该 SQL 从已复核 CSV 提取报告行和闭合计数。",
        [
            "data/spectrum_family_audit.csv",
            "data/source_package_reference_audit.csv",
            "data/source_card_family_audit.csv",
            "data/audit_summary.json",
        ],
        [
            "8 families: alpha, eminus, eplus, gamma, muminus, muplus, n, p",
            "20 angular bins per family",
            "three retained source packages only",
            "no retained input was modified",
        ],
        [
            "energy_error_factor = mean(correct_x / legacy_x); all rows equal 1000 within floating-point representation",
            "bad_references = sum of Spectrum File references naming the cosima_spectra_dp_2602units directory",
            "raw conversion uses B=1000 except alpha B=4000; p_keV=f_raw/(trapz(f_raw,E_raw)*B)",
            "Flux closure compares the sum of 20 card Flux values with manifest flux for the same family",
        ],
    )
    megalib_source = source(
        "megalib_contract",
        "MEGAlib 4.02.00 手册与源代码契约",
        "evidence/MEGALIB_CONTRACT.md",
        "local filesystem review",
        "sha256sum MEGAlib/doc/Cosima.pdf MEGAlib/src/cosima/src/MCSource.cc MEGAlib/src/cosima/src/MCParameterFile.cc",
        "核对本机安装的官方 Cosima/Geomega 手册与实现源代码，并记录页码、行号和 SHA-256。",
        [
            "MEGAlib/doc/Cosima.pdf",
            "MEGAlib/doc/Geomega.pdf",
            "MEGAlib/src/cosima/src/MCSource.cc",
            "MEGAlib/src/cosima/src/MCParameterFile.cc",
            "MEGAlib/src/global/misc/src/MFunction.cxx",
        ],
        ["installed MEGAlib 4.02.00", "manual and code read locally"],
        [
            "Spectrum File DP x is a numerical keV value",
            "far-field Flux is particles cm^-2 s^-1; near-field Flux is particles s^-1",
            "EventList time/position/energy are seconds/cm/keV",
        ],
    )
    project_source = source(
        "project_chain",
        "项目源卡、生成代码与输运证据链",
        "evidence/PROJECT_SOURCE_CHAIN.md",
        "Python 3 + filesystem review",
        "python3 engineering/particle_source_unit_audit_20260811/code/audit_particle_source_units.py",
        "穷举 raw、correct DP、legacy DP、三套 source cards，并读取保留的事件级与归一化审计。",
        [
            "expacs_fullsphere_20bin_sources/raw_expacs/*.dat",
            "expacs_fullsphere_20bin_sources/cosima_spectra_dp/*.dat",
            "expacs_fullsphere_20bin_sources/cosima_spectra_dp_2602units/*.dat",
            "24 retained Background_*_fullsphere20.source cards",
            "retained 10M-event gamma IA INIT audit",
        ],
        ["all files, all DP nodes, no random subsampling"],
        [
            "480 bad references = 3 packages × 8 families × 20 bins",
            "transport corroboration = retained IA INIT energies in 10,000,000 gamma events",
            "local bookkeeping pass never overrides an upstream energy-axis failure",
        ],
    )

    manifest_sources = [
        {"id": item["id"], "label": item["label"], "path": item["path"]}
        for item in (audit_source, megalib_source, project_source)
    ]

    artifact = {
        "surface": "report",
        "manifest": {
            "version": 1,
            "surface": "report",
            "title": TITLE,
            "description": "MEGAlib 手册、实现源码、项目 raw/DP/source cards 与保留 SIM 事件的可复核单位审计。审计日期：2026-08-11；本机版本：MEGAlib 4.02.00。",
            "generatedAt": GENERATED_AT,
            "cards": [
                {
                    "id": "affected_families",
                    "description": "八类连续谱全部受同一个 legacy 横轴错误影响（8/8）。",
                    "dataset": "headline",
                    "sourceId": "audit_sql",
                    "metrics": [{"label": "受影响粒子族", "field": "affected_families", "format": "number"}],
                },
                {
                    "id": "bad_references",
                    "description": "三套保留包合计 480/480 个 Spectrum File 引用指向 legacy 目录。",
                    "dataset": "headline",
                    "sourceId": "audit_sql",
                    "metrics": [{"label": "错误谱引用", "field": "bad_references", "format": "number"}],
                },
                {
                    "id": "energy_error_factor",
                    "description": "实际送入 Cosima 的总动能是正确值的 1/1000。",
                    "dataset": "headline",
                    "sourceId": "audit_sql",
                    "metrics": [{"label": "能量缩小因子", "field": "energy_error_factor", "format": "number", "unit": "×"}],
                },
                {
                    "id": "gamma_below_1kev",
                    "description": "保留的 1000 万 γ 主粒子 IA INIT 扫描中的 <1 keV 事件数。",
                    "dataset": "headline",
                    "sourceId": "audit_sql",
                    "metrics": [
                        {"label": "γ事件 <1 keV", "field": "gamma_events_below_1keV", "format": "number"},
                        {"label": "扫描总事件", "field": "gamma_records", "format": "number"},
                    ],
                },
            ],
            "charts": [
                {
                    "id": "energy_error_by_family",
                    "title": "八类连续谱的能量误差完全一致",
                    "subtitle": "柱高 = 应有总动能 / 实际载入动能；八类均为 1000。",
                    "headerMarkdown": "这是对全部 **160 个 DP 文件、12,800 个谱节点** 的穷举结果，不是抽样。",
                    "type": "bar",
                    "dataset": "family_chart",
                    "sourceId": "audit_sql",
                    "encodings": {
                        "x": {"field": "family_label", "type": "nominal", "label": "粒子族"},
                        "y": {"field": "energy_error_factor", "type": "quantitative", "label": "能量缩小因子", "format": "number"},
                        "tooltip": [
                            {"field": "spectrum_files", "type": "quantitative", "label": "谱文件数", "format": "number"},
                            {"field": "dp_rows", "type": "quantitative", "label": "DP节点数", "format": "number"},
                            {"field": "raw_energy_scale_to_total_keV", "type": "quantitative", "label": "raw→总keV倍率", "format": "number"},
                            {"field": "raw_to_correct_pdf_max_relative_delta", "type": "quantitative", "label": "correct DP重建最大相对差"},
                            {"field": "card_flux_relative_delta", "type": "quantitative", "label": "卡片Flux相对差"},
                        ],
                    },
                    "yAxisTitle": "应有能量 / 实际载入能量",
                    "valueFormat": "number",
                    "layout": "full",
                }
            ],
            "tables": [
                {
                    "id": "unit_verdicts",
                    "title": "单位判定总表",
                    "subtitle": "PASS 只在本行所列范围内成立；不会抵消上游能量轴 FAIL。",
                    "dataset": "unit_verdicts",
                    "sourceId": "audit_sql",
                    "defaultSort": {"field": "component", "direction": "asc"},
                    "density": "spacious",
                    "layout": "full",
                    "columns": [
                        {"field": "component", "label": "组件", "type": "text"},
                        {"field": "expected", "label": "MEGAlib/物理期望", "type": "text"},
                        {"field": "observed", "label": "实测", "type": "text"},
                        {"field": "result", "label": "判定与边界", "type": "text"},
                    ],
                },
                {
                    "id": "family_detail",
                    "title": "全八族 raw→correct→legacy 对照",
                    "subtitle": "correct DP 先由 raw 独立重建；再与 active legacy DP 逐点比较。",
                    "dataset": "family_table",
                    "sourceId": "audit_sql",
                    "defaultSort": {"field": "family_label", "direction": "asc"},
                    "density": "spacious",
                    "layout": "full",
                    "columns": [
                        {"field": "family_label", "label": "族", "type": "text"},
                        {"field": "raw_unit", "label": "raw单位", "type": "text"},
                        {"field": "required_scale", "label": "转总keV", "type": "text"},
                        {"field": "coverage", "label": "穷举覆盖", "type": "text"},
                        {"field": "correct_rebuild", "label": "raw→correct 重建", "type": "text"},
                        {"field": "legacy_relation", "label": "active legacy 关系", "type": "text"},
                        {"field": "verdict", "label": "active判定", "type": "text"},
                    ],
                },
                {
                    "id": "package_references",
                    "title": "三套保留源包的引用覆盖",
                    "subtitle": "每套包均包含八族、每族20个角箱。",
                    "dataset": "package_table",
                    "sourceId": "audit_sql",
                    "defaultSort": {"field": "package", "direction": "asc"},
                    "density": "spacious",
                    "layout": "full",
                    "columns": [
                        {"field": "package", "label": "保留包", "type": "text"},
                        {"field": "coverage", "label": "覆盖", "type": "text"},
                        {"field": "legacy_references", "label": "legacy / 全部引用", "type": "text"},
                        {"field": "correct_references", "label": "正确目录引用", "type": "text"},
                        {"field": "verdict", "label": "判定", "type": "text"},
                    ],
                },
                {
                    "id": "authority_impact",
                    "title": "对现有项目产品的权威性影响",
                    "subtitle": "区分“文件可复现/局部账目闭合”和“物理输入正确”。",
                    "dataset": "authority_table",
                    "sourceId": "audit_sql",
                    "defaultSort": {"field": "product", "direction": "asc"},
                    "density": "spacious",
                    "layout": "full",
                    "columns": [
                        {"field": "product", "label": "产品", "type": "text"},
                        {"field": "unit_result", "label": "单位链", "type": "text"},
                        {"field": "authority", "label": "当前权威性", "type": "text"},
                        {"field": "required_action", "label": "必要动作", "type": "text"},
                    ],
                },
                {
                    "id": "evidence_locators",
                    "title": "核心实质证据定位",
                    "subtitle": "完整 525 项 SHA-256 清单见 data/evidence_hashes.csv。",
                    "dataset": "evidence_locators",
                    "sourceId": "audit_sql",
                    "defaultSort": {"field": "layer", "direction": "asc"},
                    "density": "spacious",
                    "layout": "full",
                    "columns": [
                        {"field": "layer", "label": "证据层", "type": "text"},
                        {"field": "fact", "label": "证明事项", "type": "text"},
                        {"field": "locator", "label": "路径/页码/行号", "type": "text"},
                        {"field": "sha256_prefix", "label": "SHA-256前缀", "type": "text"},
                    ],
                },
            ],
            "sources": manifest_sources,
            "blocks": [
                {"id": "title", "type": "markdown", "body": f"# {TITLE}"},
                {
                    "id": "technical_summary",
                    "type": "markdown",
                    "sourceId": "project_chain",
                    "body": (
                        "## 技术摘要\n\n"
                        "**结论：当前三套保留的八族连续谱输入单位不正确。** "
                        "Cosima 的 `Spectrum File` 把 DP 横轴直接当作总动能 keV；项目 active 源卡却全部引用 "
                        "`cosima_spectra_dp_2602units/`。该目录的每个 x 都是正确值的 0.001，y 完全不变。"
                        "因此 α、e⁻、e⁺、γ、μ⁻、μ⁺、n、p 的实际入射总动能均低 **1000 倍**，并非只有 γ。\n\n"
                        "这会使 prompt 响应、活化反应阈值与截面采样、同位素库存、delayed 源以及基于它们的几何优选/灵敏度结论失去物理权威。"
                        "显式 Flux、角箱、R=60 cm 面积和局部 delayed Bq/TT 账目本身可以闭合，但这些局部 PASS 不能修复错误的入射能量。"
                        "独立 PARMA 511-keV mono 源及 Optics EventList 的单位格式通过，其适用范围在报告中单独限定。"
                    ),
                },
                {"id": "headline_metrics", "type": "metric-strip", "cardIds": ["affected_families", "bad_references", "energy_error_factor", "gamma_below_1kev"]},
                {
                    "id": "verdict_boundary",
                    "type": "markdown",
                    "body": (
                        "## 关键结论与判定边界\n\n"
                        "本审计把“语法/算术闭合”和“物理输入正确”分开。"
                        "源卡能够被 Cosima 解析、hash 完全匹配、Flux 总和闭合，都只说明同一输入被稳定复现；"
                        "不能证明该输入使用了正确的物理单位。"
                    ),
                },
                {"id": "unit_verdict_table", "type": "table", "tableId": "unit_verdicts", "layout": "full"},
                {
                    "id": "megalib_contract_section",
                    "type": "markdown",
                    "sourceId": "megalib_contract",
                    "body": (
                        "## MEGAlib 官方契约：Cosima 实际读取什么\n\n"
                        "本机安装为 **MEGAlib 4.02.00**。Cosima 手册 PDF 第27页明确规定：`Spectrum File` 的第一个 DP 数是 **keV**，第二个数是 **每 keV 的微分形状**；"
                        "形状的整体归一化任意，绝对率由 `.Flux` 给出。源码与手册一致："
                        "`MCSource::SetEnergy` 对 x 执行 `ScaleX(keV)`，随机抽样得到的 x 随后直接进入 Geant4 粒子枪。\n\n"
                        "由此得到两个硬约束：\n\n"
                        "- 非 α 原始 MeV 谱必须写成 `E_total_keV = E_raw × 1000`。\n"
                        "- α 原始谱是 MeV/n，而粒子枪需要整颗 α 的动能，所以必须写成 `E_total_keV = E_raw × 4 × 1000`。\n\n"
                        "`MFunction::GetRandom()` 用累计积分抽样，统一乘在 y 上的常数会在归一化时消掉。"
                        "所以错误 legacy DP 的 y 虽未除以1000，也**不能**据此把卡片 `.Flux` 再乘或除1000。"
                    ),
                },
                {
                    "id": "methodology",
                    "type": "markdown",
                    "sourceId": "audit_sql",
                    "body": (
                        "## 审计方法与可复现定义\n\n"
                        "审计只读遍历 8 族 × 20 角箱的 160 组 raw/correct/legacy 文件，并遍历三套保留包的24张源卡。"
                        "原始谱在 raw 坐标上的梯形积分记为 `I`，变量变换倍率记为 `B`：非 α 为1000，α 为4000。\n\n"
                        "```text\n"
                        "raw EXPACS/PARMA:  E_raw, f(E_raw)\n"
                        "        │  B=1000（α: 4×1000）\n"
                        "        ▼\n"
                        "correct DP: x = B·E_raw,  p(x) = f(E_raw)/(I·B),  ∫p dx = 1\n"
                        "        │  legacy 又把 x 除1000，y不变\n"
                        "        ▼\n"
                        "active source card → Cosima把x当keV → ParticleGun总动能低1000倍\n"
                        "```\n\n"
                        "raw→correct 的全部节点重建最大能量残差为 **3.638×10⁻¹² keV**，最大 PDF 相对差为 **8.543×10⁻¹¹**，"
                        "与文本科学计数法舍入一致。随后 correct→legacy 的全部节点满足 x 比例0.001且 y 最大绝对差0。"
                    ),
                },
                {
                    "id": "all_family_evidence",
                    "type": "markdown",
                    "body": (
                        "## 全八族的直接数值证据\n\n"
                        "下图不是由文件夹名称推断，而是先从 raw 文件独立重建正确 DP，再逐点比较 active legacy DP。"
                    ),
                },
                {
                    "id": "family_static_chart",
                    "type": "html",
                    "body": (
                        '<figure style="margin:0;text-align:center">'
                        f'<img src="{chart_data_uri}" alt="八类连续谱的应有总动能与实际载入总动能之比均为1000" '
                        'style="display:block;width:100%;height:270px;object-fit:contain">'
                        '<figcaption style="margin-top:8px;color:#5d5d5d;font-size:12px;line-height:1.45;text-align:left">'
                        '图1｜应有总动能/实际载入总动能。对数轴上的正确基线为1；八类实测均为1000。'
                        '来源：全160个DP文件、12,800个节点的穷举审计。'
                        '</figcaption></figure>'
                    ),
                },
                {"id": "family_chart_block", "type": "chart", "chartId": "energy_error_by_family", "layout": "full"},
                {
                    "id": "chart_interpretation",
                    "type": "markdown",
                    "sourceId": "audit_sql",
                    "body": (
                        "### 图的解释\n\n"
                        "八根柱都等于1000，说明同一错误横跨所有粒子族。"
                        "α 的正确 raw→total-keV 倍率为4000，但 legacy 目录是在已经正确换算后的 keV 横轴上再除1000，"
                        "所以 α 的最终错误仍然也是精确的1000倍。中子有2,800个节点，其余各1,600个，合计12,800个节点。"
                    ),
                },
                {"id": "family_table_block", "type": "table", "tableId": "family_detail", "layout": "full"},
                {
                    "id": "package_coverage",
                    "type": "markdown",
                    "body": (
                        "## 三套保留源包的覆盖范围\n\n"
                        "Mass_model_511、S3c package 32 和 S3d/O8 package 43 均为八族全覆盖。"
                        "某些 runner 对 legacy 目录和树 hash 的强制检查，只证明错误输入被稳定锁定；它不是单位验证器。"
                    ),
                },
                {"id": "package_table_block", "type": "table", "tableId": "package_references", "layout": "full"},
                {
                    "id": "transport_corroboration",
                    "type": "markdown",
                    "sourceId": "project_chain",
                    "body": (
                        "## 输运文件的事件级反证\n\n"
                        f"保留的 γ `IA INIT` 审计扫描了 **{int(gamma_scan['records']):,}** 个主粒子，其中 **{int(gamma_scan['events_below_1_keV']):,}** 个低于1 keV。"
                        "正确 DP 的 449.65、566.08、712.64 keV 节点在实际输运中对应为 0.44965、0.56608、0.71264 keV。"
                        "这把“卡片引用错误”与“Geant4 实际收到低1000倍能量”连接起来。\n\n"
                        "完整 raw SIM 扫描目前只对 γ 保留；其余七族的结论来自更直接的源级穷举：它们的 active 卡片引用、legacy/correct DP 节点关系和 Cosima 读取语义均完全相同。"
                    ),
                },
                {
                    "id": "passing_units",
                    "type": "markdown",
                    "sourceId": "project_chain",
                    "body": (
                        "## 哪些单位确实正确\n\n"
                        "**Flux 与角度。** 每族20个 `.Flux` 的和与 manifest 至多相差3.1×10⁻¹⁶（相对），20个 equal-μ 角箱总立体角为4π；"
                        "theta/phi 在源卡中按度输入。FarField 的粒子数换算使用 `N=t·πR²·F`，R=60 cm 的 runner 算术正确。\n\n"
                        f"**PARMA 511 mono。** `{parma['energy_MeV']}` MeV 正确转换为 `{parma['energy_keV_cosima']}` keV，20/40/80箱 flux 都闭合；"
                        "判定为独立 source-level PASS。\n\n"
                        f"**EventList。** 保留文件有 {eventlist['rows']:,} 行，全部15列，能量均为 {eventlist['energy_min_keV']:.0f} keV，"
                        f"时间范围 {eventlist['time_min_s']:.1f}–{eventlist['time_max_s']:.6g} s。"
                        "代码把 optics mm×0.1 转 cm。这里的1 ns步进只是事件排序，不能拿37.193 μs当气球曝光；物理权重仍应来自 flux×Aeff×T。\n\n"
                        "**Delayed 局部账目。** PointSource cm、Bq(=s⁻¹)、NUBASE ground-state、TT 除法与 trigger 计数的实现链条局部合理。"
                        "但是这些源的库存来自错误的初级能量，局部守恒不等于物理正确。"
                    ),
                },
                {
                    "id": "authority_section",
                    "type": "markdown",
                    "body": (
                        "## 对项目权威性的影响\n\n"
                        "最重要的边界是：**几何文件仍可作为结构定义保留，但用错误能谱得到的性能排序不能随几何一起保留为物理结论。**"
                    ),
                },
                {"id": "authority_table_block", "type": "table", "tableId": "authority_impact", "layout": "full"},
                {
                    "id": "repair_plan",
                    "type": "markdown",
                    "sourceId": "project_chain",
                    "body": (
                        "## 修复与重跑要求\n\n"
                        "1. 在新的日期目录建立修复包；不要覆盖现有保留产品。把八族全部源卡改指向已验证的 `cosima_spectra_dp/`。\n"
                        "2. **保持现有 `.Flux` 数值不变。** 错误只在 DP x；y形状的整体尺度会在抽样中归一化。\n"
                        "3. 在启动输运前执行静态 gate：检查 raw 单位、α×4、MeV→keV、DP积分、20箱 flux/4π闭合、几何头与 source card geometry 一致。\n"
                        "4. 每族先做小型 IA INIT smoke，直接验证写入 SIM 的主粒子能量范围，再运行全量 prompt。\n"
                        "5. 由修复后的 prompt 重新做 isotope production、buildup、NUBASE/TT guarded delayed source 和 delayed transport；旧 inventory 不可复用。\n"
                        "6. 最后重做探测器响应、Step05/选区闭环、S3c-LW1 与参考几何的性能比较及任务期折叠。"
                    ),
                },
                {
                    "id": "limitations",
                    "type": "markdown",
                    "sourceId": "project_chain",
                    "body": (
                        "## 局限性与稳健性\n\n"
                        "- 本审计为只读单位与证据审计，没有发起新的 Geant4 transport；因此它确认输入错误与权威边界，不给出修复后计数率。\n"
                        "- 仓库中未找到最初 raw→DP 生成器，也未找到 `_2602units` 生成器。legacy 文件头指向的旧外部路径当前不存在；这是 provenance gap。"
                        "不过 raw→correct 和 correct→legacy 均已在全部文件、全部节点上独立数值闭合。\n"
                        "- 事件级 1000 万条全扫描仅有 γ 保留；全八族结论依赖更强的源级穷举与同一 MEGAlib 读取代码。\n"
                        "- 现有 M04 文本称“七个非光子族不受影响”，与本次 480/480 引用和全八族 DP 比较的实证冲突，应视为已被本报告推翻。"
                    ),
                },
                {
                    "id": "evidence_section",
                    "type": "markdown",
                    "body": (
                        "## 证据定位与可复核材料\n\n"
                        "下表给出最关键的手册页码、源码行号、项目路径和内容哈希前缀。"
                        "完整审计脚本、CSV、JSON及525项 SHA-256 清单随 PDF 一起保存在同一工程包中。"
                    ),
                },
                {"id": "evidence_table_block", "type": "table", "tableId": "evidence_locators", "layout": "full"},
                {
                    "id": "further_questions",
                    "type": "markdown",
                    "body": (
                        "## 后续问题\n\n"
                        "- `_2602units` 是在哪一次外部迁移中生成、为何在正确 keV 转换后再次除1000？是否还能找回原始生成脚本和审阅记录？\n"
                        "- 修复重跑应以 S3c-LW1 与 S3c-C0 为最小比较集，还是同步重算 S3d/O8 全链？\n"
                        "- 在修复 transport 完成前，哪些对外文档、图表或表格引用了旧 prompt/delayed 率，需要统一撤销或加 blocker？"
                    ),
                },
            ],
        },
        "snapshot": {
            "version": 1,
            "generatedAt": GENERATED_AT,
            "status": "ready",
            "datasets": {
                "headline": headline,
                "family_chart": family_chart,
                "family_table": family_table,
                "package_table": package_table,
                "unit_verdicts": unit_verdicts,
                "authority_table": authority_table,
                "evidence_locators": evidence_locators,
            },
        },
        "sources": [audit_source, megalib_source, project_source],
        "package_info": {
            "root": "engineering/particle_source_unit_audit_20260811/report",
            "manifestPath": "artifact.json",
            "snapshotPath": "artifact.json",
        },
    }

    REPORT.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {ARTIFACT}")
    print(f"blocks={len(artifact['manifest']['blocks'])}")
    print(f"datasets={len(artifact['snapshot']['datasets'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
