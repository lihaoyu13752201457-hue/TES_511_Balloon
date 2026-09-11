#!/usr/bin/env python3
"""Build the bounded, source-backed SE3 review report artifact.

This script only packages reviewed tables and calculations.  It does not run
transport, mutate retained simulation products, or compute large-file hashes.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path("/home/ubuntu/TES_511_Balloon")
PACKAGE = ROOT / (
    "engineering/geometry_optimization_20260815/"
    "48_se3_background_optimization_review_20260816"
)
DATA = PACKAGE / "data"
ARTIFACT = PACKAGE / "artifact.json"
GENERATED_AT = "2026-08-16T00:00:00+08:00"
TITLE = "SE3 本底归因与几何优化复习"


def read_csv(name: str) -> list[dict[str, str]]:
    with (DATA / name).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, Any]]) -> None:
    path = DATA / name
    if not rows:
        raise ValueError(f"refusing to write empty report dataset: {name}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def number(row: dict[str, str], key: str) -> float:
    return float(row[key])


def source(
    source_id: str,
    label: str,
    csv_name: str,
    description: str,
    tables_used: list[str],
    metric_definitions: dict[str, str],
    filters: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": source_id,
        "label": label,
        "path": f"data/{csv_name}",
        "query": {
            "engine": "duckdb",
            "language": "sql",
            "sql": f"SELECT * FROM read_csv_auto('data/{csv_name}', header = true)",
            "description": description,
            "tables_used": tables_used,
            "filters": filters or [],
            "metric_definitions": metric_definitions,
            "executed_at": GENERATED_AT,
        },
    }


def main() -> None:
    summary = json.loads((DATA / "analysis_summary.json").read_text(encoding="utf-8"))
    material_raw = read_csv("activation_origin_by_material.csv")
    volume_raw = read_csv("activation_origin_by_volume.csv")
    parent_raw = read_csv("activation_origin_by_parent.csv")
    incident_raw = read_csv("activation_origin_by_incident_family.csv")
    sensitivity_raw = read_csv("optimization_sensitivity_scenarios.csv")

    material_labels = {
        "active_scintillator": "BGO 主动闪烁体",
        "passive_w_or_collimator": "W / 准直器",
        "window": "窗口材料",
        "outer_mechanics": "外部机械结构",
        "cold_plates": "冷板",
        "other_internal": "其他内部件",
        "bpe_neutron_shield": "BPE",
        "plastic_positron_veto": "塑闪",
        "tes": "TES",
    }
    volume_labels = {
        "ColdPlate_MXC_50mK_SD_anchor": "MXC 50 mK Cu 冷板",
        "Cu_50mK_StillLike_Can_bottom_cap_2mm": "50 mK Cu can 底盖",
        "ColdPlate_4K": "4 K Cu 冷板",
        "Cu_SubstrateSupport_SolidDisk_L0_deepest": "L0 深层 Cu 实心盘",
        "ColdPlate_CP_100mK_intercept": "100 mK Cu 冷板",
        "NbTi_Bundle_Still_4K": "Still–4 K NbTi 线束",
        "Cu_SubstrateSupport_OpenRing_L3_ZM_panel": "L3 Cu 开口环",
    }

    headline = [{
        "selected_delayed_rate_cps": summary["activation"]["selected_delayed_W2_rate_cps"],
        "selected_delayed_sigma_cps": 0.020032,
        "prompt_pre_veto_rate_cps": summary["prompt"]["windows"]["w2_510p58_511p42"]["pre_veto_rate_cps"],
        "prompt_post_veto_rate_cps": summary["prompt"]["windows"]["w2_510p58_511p42"]["after_veto50_rate_cps"],
        "selected_cu_parent_share": 0.9299463264463577,
        "day15_activity_Bq": summary["activation"]["transported_day15_activity_Bq"],
        "baseline_F3_e5": summary["sensitivity"]["baseline"]["F3_ph_cm2_s"] * 1e5,
        "baseline_Z20": summary["sensitivity"]["baseline"]["Z20"],
        "selected_delayed_events": summary["activation"]["selected_delayed_W2_events"],
    }]
    write_csv("report_headline_metrics.csv", headline)

    geometry_rows = [
        {
            "design": "Mass_model_511",
            "near_tes_structure": "6 层 TES；厚 Cu 冷板、Cu can、Nb + MuMetal；W 多孔准直器",
            "active_veto": "CsI：侧 40 mm、底 60 mm、顶 30 mm；离线 50 keV event-sum",
            "role": "完整质量模型基线与方法来源",
            "current_authority": "几何权威；旧 broadband 率仅历史经验",
        },
        {
            "design": "S3d-O8",
            "near_tes_structure": "保留近场 Cu/Nb/MuMetal；去 3 个 outer-W2；轻量化外壳",
            "active_veto": "侧 BGO 40 mm、底 30 mm、顶 10 mm；塑闪 + BPE",
            "role": "corrected-keV 匹配比较基准",
            "current_authority": "prompt/delayed/common-response 为当前对照",
        },
        {
            "design": "SE3 Plan1",
            "near_tes_structure": "五块冷板 6→4 mm 并各开 48 孔；Nb→Al；移除 MuMetal",
            "active_veto": "沿用 S3d-O8 BGO；BPE 仅开光学口；10 mm 塑闪连续",
            "role": "近场减质候选；触及质量 −10.217 kg",
            "current_authority": "1/3 corrected-keV screen，stage00–07 PASS",
        },
    ]
    write_csv("report_geometry_progression.csv", geometry_rows)

    prompt_ingress = [
        {
            "surface": "侧面",
            "pre_veto_events": 95,
            "pre_veto_rate_cps": 6.382411696538332,
            "rate_share": 0.8420030568650594,
            "post_veto_rate_cps": 0.0,
            "classification": "IA INIT ray × instrument-local outer envelope",
            "first_active_crosscheck": "首主动体加权率约 85.9% 为 side",
        },
        {
            "surface": "底部",
            "pre_veto_events": 21,
            "pre_veto_rate_cps": 0.9455231386202443,
            "rate_share": 0.1247386428372671,
            "post_veto_rate_cps": 0.0,
            "classification": "IA INIT ray × instrument-local outer envelope",
            "first_active_crosscheck": "首主动体加权率约 12.3% 为 bottom",
        },
        {
            "surface": "顶部",
            "pre_veto_events": 4,
            "pre_veto_rate_cps": 0.25209904298586633,
            "rate_share": 0.033258300297673474,
            "post_veto_rate_cps": 0.0,
            "classification": "IA INIT ray × instrument-local outer envelope",
            "first_active_crosscheck": "首主动体加权率约 1.8% 为 top",
        },
    ]
    write_csv("report_prompt_ingress.csv", prompt_ingress)

    prompt_veto = [
        {
            "veto_route": "plastic ≥ 50 keV",
            "events": 94,
            "rate_cps": 6.25992,
            "rate_share": 0.8258,
            "post_route_survivors": 0,
        },
        {
            "veto_route": "BGO-only ≥ 50 keV",
            "events": 26,
            "rate_cps": 1.32011,
            "rate_share": 0.1742,
            "post_route_survivors": 0,
        },
    ]
    write_csv("report_prompt_veto.csv", prompt_veto)

    material_rows: list[dict[str, Any]] = []
    for row in material_raw:
        material_rows.append({
            "material": material_labels.get(row["material_category"], row["material_category"]),
            "activity_Bq": number(row, "transported_day15_activity_Bq"),
            "activity_share": number(row, "activity_share"),
            "selected_events": int(row["selected_W2_events"]),
            "selected_rate_milli_cps": number(row, "selected_W2_rate_cps") * 1000.0,
            "selected_rate_share": number(row, "selected_rate_share"),
            "selected_Neff": number(row, "selected_W2_Neff"),
            "material_category": row["material_category"],
        })
    write_csv("report_activation_material.csv", material_rows)

    chosen_volumes = []
    for row in volume_raw:
        if row["source_volume"] not in volume_labels:
            continue
        chosen_volumes.append({
            "volume": volume_labels[row["source_volume"]],
            "source_volume": row["source_volume"],
            "material": "Cu" if row["source_volume"].startswith(("ColdPlate", "Cu_")) else "NbTi",
            "activity_Bq": number(row, "transported_day15_activity_Bq"),
            "selected_events": int(row["selected_W2_events"]),
            "selected_rate_milli_cps": number(row, "selected_W2_rate_cps") * 1000.0,
            "selected_sigma_milli_cps": number(row, "selected_W2_stat_sigma_cps") * 1000.0,
            "selected_rate_share": number(row, "selected_rate_share"),
            "selected_Neff": number(row, "selected_W2_Neff"),
            "local_x_cm": number(row, "selected_production_local_x_weighted_cm"),
            "local_y_cm": number(row, "selected_production_local_y_weighted_cm"),
            "local_z_cm": number(row, "selected_production_local_z_weighted_cm"),
        })
    chosen_volumes.sort(key=lambda row: row["selected_rate_milli_cps"], reverse=True)
    write_csv("report_delayed_volume.csv", chosen_volumes)

    parent_labels = {"29062": "Cu-62", "29064": "Cu-64", "29061": "Cu-61", "19038": "K-38"}
    parent_rows = []
    for row in parent_raw:
        if row["source_parent_ZA"] not in parent_labels:
            continue
        parent_rows.append({
            "parent": parent_labels[row["source_parent_ZA"]],
            "activity_Bq": number(row, "transported_day15_activity_Bq"),
            "selected_events": int(row["selected_W2_events"]),
            "selected_rate_milli_cps": number(row, "selected_W2_rate_cps") * 1000.0,
            "selected_rate_share": number(row, "selected_rate_share"),
            "selected_Neff": number(row, "selected_W2_Neff"),
        })
    parent_rows.sort(key=lambda row: row["selected_rate_milli_cps"], reverse=True)
    write_csv("report_delayed_parent.csv", parent_rows)

    incident_labels = {
        "p": "proton",
        "n": "neutron",
        "alpha": "alpha",
        "gamma": "gamma",
        "eplus": "positron",
        "eminus": "electron",
        "muminus": "muon−",
    }
    incident_rows = []
    for row in incident_raw:
        incident_rows.append({
            "incident_family": incident_labels.get(row["incident_family"], row["incident_family"]),
            "family_code": row["incident_family"],
            "activity_Bq": number(row, "transported_day15_activity_Bq"),
            "activity_share": number(row, "activity_share"),
            "selected_events": int(row["selected_W2_events"]),
            "selected_rate_milli_cps": number(row, "selected_W2_rate_cps") * 1000.0,
            "selected_rate_share": number(row, "selected_rate_share"),
            "selected_Neff": number(row, "selected_W2_Neff"),
        })
    incident_rows.sort(key=lambda row: row["selected_rate_milli_cps"], reverse=True)
    write_csv("report_delayed_incident_family.csv", incident_rows)

    comparison_rows = [
        {"metric": "总 A15", "unit": "Bq", "s3d": 1404.131069, "se3": 1348.141992, "se3_change": -0.03987, "interpretation": "总源项小幅下降"},
        {"metric": "冷板 A15", "unit": "Bq", "s3d": 94.1144, "se3": 45.39497, "se3_change": -0.51767, "interpretation": "减薄 + 开孔明确降低冷板活化"},
        {"metric": "Cu-62 A15", "unit": "Bq", "s3d": 41.6066, "se3": 28.71763, "se3_change": -0.30978, "interpretation": "铜源项下降"},
        {"metric": "Cu-64 A15", "unit": "Bq", "s3d": 80.2465, "se3": 55.35178, "se3_change": -0.31023, "interpretation": "铜源项下降"},
        {"metric": "delayed W2", "unit": "cps", "s3d": 0.05447975, "se3": 0.06011336, "se3_change": 0.10341, "interpretation": "中央值上浮但仅约 0.25σ，不构成退化证据"},
        {"metric": "prompt W2", "unit": "cps", "s3d": 0.03384293, "se3": 0.0, "se3_change": -1.0, "interpretation": "SE3 样本中未观测 final survivor"},
    ]
    write_csv("report_se3_s3d_comparison.csv", comparison_rows)

    sensitivity_rows = []
    for row in sensitivity_raw:
        if abs(float(row["signal_Aeff_retention_fraction"]) - 0.98) > 1e-9:
            continue
        sensitivity_rows.append({
            "background_reduction_fraction": float(row["background_reduction_fraction"]),
            "signal_Aeff_retention_fraction": float(row["signal_Aeff_retention_fraction"]),
            "B20_counts": float(row["B20_counts"]),
            "S20_counts": float(row["S20_counts"]),
            "Z20": float(row["Z20"]),
            "F3_e5": float(row["F3_ph_cm2_s"]) * 1e5,
            "F3_ph_cm2_s": float(row["F3_ph_cm2_s"]),
            "F3_ratio_to_SE3": float(row["F3_ratio_to_SE3"]),
            "scenario_type": "份额敏感性，不是 transport 预测",
        })
    write_csv("report_sensitivity_98pct_signal.csv", sensitivity_rows)

    actions = [
        {
            "variant": "V2A",
            "geometry_action": "50 mK Cu can 底盖改环形盖 + 径向热桥；L0 实心盘改 open-ring/spoke；热带移出 TES 直视固角",
            "targeted_current_share": 0.38985,
            "risk": "低到中；需热设计与导航复核",
            "why": "两件合计约 39.0% delayed 中央率，且 full-envelope 首击 Cu 的信号本就全部失败",
        },
        {
            "variant": "V2B",
            "geometry_action": "在 V2A 上重排 MXC 开孔到 TES 投影方向，并错开各冷板孔位，消除多板投影直通道",
            "targeted_current_share": 0.64100,
            "risk": "中；需同源响应重放 + fresh BUILDUP",
            "why": "加入 MXC 后覆盖约 64.1% delayed 中央率；错孔可近似质量中性地降耦合",
        },
        {
            "variant": "V2C（仅筛选）",
            "geometry_action": "保留 37.96 mm 光学走廊，在非视场固角试验分段 shadow cup / graded liner",
            "targeted_current_share": 0.78831,
            "risk": "中到高；候选材料必须自有 corrected-keV 活化链",
            "why": "只在 V2A/B 仍不足时，用最小被动质量截断 4 K / can / MXC 到 TES 的视线",
        },
    ]
    write_csv("report_candidate_actions.csv", actions)

    gates = [
        {"gate": "delayed W2", "promotion_threshold": "< 0.042 cps，且区间支持改善", "reason": "对应约 ≥30% 当前中央率降低；避免只看点估计"},
        {"gate": "Cu-61/62/64 A15", "promotion_threshold": "相对 SE3 再降 ≥30%", "reason": "三个铜母核占 final delayed 约 93%"},
        {"gate": "prompt W2", "promotion_threshold": "上限不劣于当前 / S3d control", "reason": "不得破坏已证明有效的侧 BGO + 连续塑闪"},
        {"gate": "full-envelope Aeff", "promotion_threshold": "同一 ray bank 损失 ≤2%（首轮）；≤5% 绝对门", "reason": "当前 SE3 与历史 S3d 注入面不同，必须 matched"},
        {"gate": "工程", "promotion_threshold": "质量节省保留；热、磁、结构、overlap/navigation 全 PASS", "reason": "几何收益必须能落地"},
    ]
    write_csv("report_promotion_gates.csv", gates)

    sources = [
        source(
            "src_headline",
            "SE3 headline metrics",
            "report_headline_metrics.csv",
            "Packages the reviewed SE3 prompt, delayed, activity, and mission headline values.",
            [
                "engineering/geometry_optimization_20260815/47_se3_plan1_transport_20260815/outputs/07_final_audit/FINAL_REPORT.md",
                "data/analysis_summary.json",
            ],
            {
                "selected delayed W2 rate": "Sum of final delayed event weights after 420 eV FWHM response, 0.3 keV pixel threshold, 50 keV active veto, W2, and Step05.",
                "selected Cu parent share": "Final selected W2 rate from Cu-61, Cu-62, and Cu-64 divided by total final delayed W2 rate.",
                "F3": "Reference flux multiplied by 3/Z20 for the 20-day central mission fold.",
            },
        ),
        source(
            "src_geometry",
            "M05, Mass, S3d, and SE3 geometry review",
            "report_geometry_progression.csv",
            "Synthesizes the exact geometry changes and the authority boundary of each design generation.",
            [
                "core_md/balloon511_ea_latex_drafts/m05_atm511_source_revision_20260811/balloon511_ea_draft_zh_m05_atm511_source_revision_20260811.tex",
                "outputs/reports/Mass_model_511_stage_diam_300_300_300_350_350_400_20260701/MASS_MODEL_511_STAGE_DIAM_300_300_300_350_350_400_FINAL_REVIEW.md",
                "engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/outputs/05_matched_comparison/REPORT.md",
                "engineering/geometry_optimization_20260815/44_geoopt_se3_minimal_20260815/README.md",
            ],
            {"touched mass delta": "SE3 exact after-minus-before mass over the whitelist-touched solids only."},
        ),
        source(
            "src_prompt_ingress",
            "SE3 prompt W2 ingress rescan",
            "report_prompt_ingress.csv",
            "Classifies all 120 measured pre-veto W2 histories by the intersection of the IA INIT ray with the instrument-local outer envelope, using physical event weights.",
            [
                "engineering/geometry_optimization_20260815/47_se3_plan1_transport_20260815/outputs/01_prompt/catalog/SE3",
                "engineering/geometry_optimization_20260704/40_s3c_mainline_lightweight_review_20260710/code/build_s3c_lightweight_analysis.py",
                "data/prompt_entry_events.csv",
            ],
            {
                "rate share": "Sum of family-local prompt event weights for the surface divided by the 7.5800339 cps pre-veto W2 total.",
                "post-veto rate": "Prompt W2 rate remaining after event-summed BGO plus plastic energy is compared with 50 keV.",
            },
            ["Measured TES energy in 510.58–511.42 keV before active veto", "Corrected-keV prompt jobs only"],
        ),
        source(
            "src_prompt_veto",
            "SE3 prompt veto-route decomposition",
            "report_prompt_veto.csv",
            "Separates the 120 prompt W2 histories by the active subsystem that rejects them at 50 keV.",
            [
                "engineering/geometry_optimization_20260815/47_se3_plan1_transport_20260815/outputs/04_common_response/background_prompt_delayed_cutflow.csv",
                "data/prompt_entry_events.csv",
            ],
            {"veto route share": "Weighted prompt W2 rate rejected by the named subsystem divided by total pre-veto W2 rate."},
        ),
        source(
            "src_material",
            "SE3 activation by material",
            "report_activation_material.csv",
            "Joins day-15 transported ground-state activity to final delayed W2 lineage by material category.",
            [
                "engineering/geometry_optimization_20260815/47_se3_plan1_transport_20260815/outputs/02_activation/day15_inventory.csv",
                "engineering/geometry_optimization_20260815/47_se3_plan1_transport_20260815/outputs/04_common_response/selected_background_w2_lineage.csv",
                "data/activation_origin_by_material.csv",
            ],
            {
                "activity share": "Material day-15 transported ground-state activity divided by 1348.141992 Bq.",
                "selected rate share": "Final selected delayed W2 rate from the material divided by 0.0601133621 cps.",
            },
        ),
        source(
            "src_volume",
            "SE3 selected delayed W2 by production volume",
            "report_delayed_volume.csv",
            "Ranks the dominant final delayed W2 production volumes with rate, MC sigma, effective support, activity, and local position.",
            [
                "data/activation_origin_by_volume.csv",
                "data/selected_delayed_event_origins.csv",
            ],
            {
                "selected rate": "Sum of final event weights by exact production volume.",
                "Neff": "(sum w)^2 / sum(w^2) within the volume.",
            },
            ["Seven dominant observed final delayed W2 volumes"],
        ),
        source(
            "src_parent",
            "SE3 selected delayed W2 by radioactive parent",
            "report_delayed_parent.csv",
            "Ranks Cu-61, Cu-62, Cu-64, and K-38 by selected delayed W2 rate.",
            ["data/activation_origin_by_parent.csv"],
            {"parent selected rate": "Sum of final delayed event weights keyed by the radioactive source parent, not the stable daughter."},
        ),
        source(
            "src_incident",
            "SE3 activation and selected delayed W2 by inducing family",
            "report_delayed_incident_family.csv",
            "Compares each incident family's share of day-15 activity with its share of final selected delayed W2 rate.",
            ["data/activation_origin_by_incident_family.csv"],
            {
                "family activity": "Day-15 transported ground-state activity attributed to the corrected-keV incident family.",
                "family selected rate": "Sum of final delayed W2 event weights attributed to the incident family that produced the parent.",
            },
        ),
        source(
            "src_comparison",
            "Matched S3d–SE3 source and response comparison",
            "report_se3_s3d_comparison.csv",
            "Compares corrected-keV S3d-O8 with the SE3 one-third screen while preserving the statistical and signal-scope boundaries.",
            [
                "engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/outputs/05_matched_comparison/REPORT.md",
                "engineering/geometry_optimization_20260815/47_se3_plan1_transport_20260815/outputs/07_final_audit/FINAL_REPORT.md",
            ],
            {"SE3 change": "SE3/S3d minus 1 for comparable source or response metrics."},
        ),
        source(
            "src_sensitivity",
            "SE3 mission sensitivity screen",
            "report_sensitivity_98pct_signal.csv",
            "Recomputes B20, S20, Z20, and F3 under transparent background-reduction scenarios at 98% signal Aeff retention.",
            ["data/optimization_sensitivity_scenarios.csv"],
            {
                "Z20": "S20 / sqrt(B20).",
                "F3": "1e-4 ph cm^-2 s^-1 multiplied by 3/Z20.",
                "scenario": "Background is scaled uniformly; signal counts are scaled to 98% of SE3. This is a target sensitivity, not a transport prediction.",
            },
            ["signal_Aeff_retention_fraction = 0.98"],
        ),
        source(
            "src_actions",
            "SE3-v2 candidate definition",
            "report_candidate_actions.csv",
            "Maps the observed near-field source shares to nested geometry actions and engineering risks.",
            [
                "data/report_delayed_volume.csv",
                "engineering/geometry_optimization_20260815/44_geoopt_se3_minimal_20260815/geometry/DEMO2_DR_v3p5_SE3.geo",
            ],
            {"targeted current share": "Sum of the current central selected delayed W2 shares of the components directly addressed by the variant."},
        ),
        source(
            "src_gates",
            "SE3-v2 promotion gates",
            "report_promotion_gates.csv",
            "Defines physics and engineering acceptance gates for the matched candidate rerun.",
            ["data/report_headline_metrics.csv", "data/report_candidate_actions.csv"],
            {"promotion threshold": "A design-screen acceptance condition; not an achieved result."},
        ),
    ]

    blocks = [
        {"id": "title", "type": "markdown", "body": f"# {TITLE}"},
        {
            "id": "technical_summary",
            "type": "markdown",
            "sourceId": "src_headline",
            "body": (
                "## 技术摘要\n\n"
                "- **优化主靶点是 TES 近场 Cu，而不是 BGO。** SE3 day-15 总活度为 1348.14 Bq，但最终 delayed W2 的约 93.0% 来自 Cu-61/62/64；BGO 占总活度约 77%，最终 W2 却没有观测 survivor。\n"
                "- **瞬时本底已由现有主动屏蔽解决。** 120 个 pre-veto W2 事件、7.5800 cps 全部带 pair/annihilation 链并在 50 keV active veto 后归零；IA INIT 射线与 instrument-local 外包络相交后，按权重约 84.20% 从侧面进入。\n"
                "- **SE3 的源项优化有效，但 final-rate 胜负未定。** 冷板活度较 S3d 降约 51.8%，Cu-62/64 各降约 31%；然而 delayed 仅 47 个加权 survivor，SE3 与 S3d 的 delayed 中央值差约 0.25σ。\n"
                "- **推荐 SE3-v2：先减影，再错孔，最后才考虑局部 liner。** 首轮目标是把 50 mK Cu can 底盖、L0 实心 Cu 盘和 MXC 视线耦合压低；预期筛选区间为 delayed 下降约 32–45%，对应 F3 约 5.45–6.15 ×10⁻⁵（Aeff 不变），必须由 matched transport 验证。"
            ),
        },
        {"id": "headline_strip", "type": "metric-strip", "cardIds": ["card_delayed", "card_prompt", "card_cu", "card_f3"]},
        {
            "id": "definitions",
            "type": "markdown",
            "body": (
                "## 判读口径\n\n"
                "本报告把 **W2** 定义为测量能量 510.58–511.42 keV；所有三流共享 420 eV FWHM、0.3 keV pixel threshold、BGO+plastic event-summed 50 keV veto 与 frozen Step05。"
                "“总活度”指 day-15 transported ground-state inventory；“最终本底”指响应、veto、W2 与 Step05 后的加权率。二者必须分开看。当前八族 gamma 已包含湮没隆起，因此不再叠加独立 mono-511。"
            ),
        },
        {
            "id": "geometry_flow",
            "type": "markdown",
            "body": (
                "## M05 的流程主干仍正确，但当前必须换成 corrected-keV 合同\n\n"
                "1. **聚焦信号：** 511 keV 远场点源先进入独立 Laue 质量模型，衍射后的焦平面位置/方向写成 EventList，再从 detector-side 注入同一探测器质量模型。\n"
                "2. **prompt：** corrected EXPACS/PARMA 的 γ、n、e−、e+、p、α、μ−、μ+ 八族按 family-local exposure 直接输运；当前 total-gamma 已含湮没隆起，不再加 mono-511。\n"
                "3. **activation：** 同一八族跑 BUILDUP，记录核素态、logical volume、exact production xyz 与 family；按 geometry × family 的 `sum(RP)/sum(TT)` 和 NUBASE ground-state 构建 inventory。\n"
                "4. **delayed：** inventory 按 exact position 采样 decay source；transport trigger time 只是衰变记录，不是 balloon exposure。\n"
                "5. **共同响应：** 三类 catalogue 都经过 per-pixel 420 eV FWHM、0.3 keV threshold、event-summed BGO+plastic 50 keV veto、W2 与 frozen Step05。single-pixel 固定保留，因此 Step05 不是 SE3 delayed 的主旋钮。\n"
                "6. **任务折叠：** 对 fixed geometry 用 81 个 0.25-day 节点折叠 0–20 d 的 signal transmission、prompt family response、inventory recurrence 与 delayed response，最后计算 S、B、Z 与 F3。\n\n"
                "### 三个几何的关键细节\n\n"
                "**Mass_model_511** 有 6 层、2256 个 Ta TES pixel，层后 Si substrate；近场含 Cu rings/深层实心盘、Nb 与 MuMetal、2 mm 50 mK Cu can，六块 6 mm 冷盘/盖，8 mm/624-bar W 多孔准直器。主动 CsI 为侧 40 mm、底 60 mm、顶 30 mm；总质量约 180.509 kg（含 CsI）。\n\n"
                "**S3d-O8** 把主动层冻结为侧 40 mm、底 30 mm、顶 10 mm，并去掉三件 outer W2；corrected-keV 对照得到 prompt 0.03384、delayed 0.05448、总 0.08832 cps。旧 O9 把侧 BGO 降到 30 mm 后出现明显侧入射恶化，所以该旋钮不应在 SE3 重开。\n\n"
                "**SE3 Plan1** 将五块冷板 6→4 mm 并各开 48 孔，Nb→Al、移除 MuMetal，BPE 只开光学口而 10 mm plastic 连续；白名单触及质量减少 10.217 kg。full-envelope signal 的主要前置损失来自 plastic 与 W collimator，BPE port 没有观测到 ray path/deposit，但仍缺同注入面的 S3d control。\n\n"
                "结构流程和几何事实可复用；M05 的旧 broadband 数率、独立 mono-511 叠加，以及把 unit-EventList 约 0.987/s 当物理 signal occupancy 的写法不可沿用。"
            ),
        },
        {"id": "geometry_table_block", "type": "table", "tableId": "geometry_table"},
        {
            "id": "prompt_finding",
            "type": "markdown",
            "sourceId": "src_prompt_ingress",
            "body": (
                "## 瞬时本底主要从侧面入射，但当前已被主动层截净\n\n"
                "W2 pre-veto 的 7.5800 cps 中，IA INIT 射线与 instrument-local 外包络相交后约 84.20% 从侧面、12.47% 从底部、3.33% 从顶部进入；这是方向代理，不是首相互作用面。120/120 事件均出现 pair + annihilation，说明到达 W2 的主链不是带电粒子直接沉积，而是高能初级粒子产生正电子后湮没。"
                "现有 10 mm 连续塑闪拒绝约 82.58% 的加权率，余下约 17.42% 由 BGO-only 拒绝，post-veto W2 为零。含义很直接：保留侧 BGO 40 mm 和连续塑闪；不要用开侧窗、降阈值或更紧 Step05 换取并不存在的当前收益。"
            ),
        },
        {"id": "prompt_chart_block", "type": "chart", "chartId": "prompt_ingress_chart"},
        {"id": "prompt_veto_table_block", "type": "table", "tableId": "prompt_veto_table"},
        {
            "id": "activation_finding",
            "type": "markdown",
            "sourceId": "src_material",
            "body": (
                "## 总活度在 BGO，选后本底却在近场 Cu\n\n"
                "BGO 主动闪烁体贡献 1037.86 Bq、约 76.99% 的 day-15 活度，却没有最终 W2 survivor；cold plates 只有 45.39 Bq、other internal 只有 28.23 Bq，却分别贡献约 46.87% 和 53.00% 的最终 delayed 率。"
                "这说明本底控制量不是 Bq 本身，而是 **产生活度 × 到 TES 的传输/选择耦合**。按体积看，MXC Cu 板、50 mK Cu can 底盖、4 K Cu 板和 L0 实心 Cu 盘合计约 78.83% 的 final delayed 中央率。"
            ),
        },
        {"id": "volume_chart_block", "type": "chart", "chartId": "delayed_volume_chart"},
        {"id": "material_table_block", "type": "table", "tableId": "material_table"},
        {
            "id": "activation_chain",
            "type": "markdown",
            "body": (
                "## delayed 的主链是 p/n 激发近场 Cu-62/64/61\n\n"
                "proton、neutron、alpha 合计产生约 99.18% 的 day-15 总活度；到了 final W2，proton 与 neutron 分别占约 58.79% 和 28.02%，alpha 约 9.98%。"
                "按 radioactive parent，Cu-62、Cu-64、Cu-61 分别贡献约 59.18%、28.71%、5.11%，三者合计约 93.0%。"
                "因此最有效的策略是同时降低近场 Cu 的产生量和到 TES 的可见固角；单纯加厚 BPE 只能部分调节 neutron，不会按比例消掉 proton-driven 分量。"
            ),
        },
        {"id": "parent_table_block", "type": "table", "tableId": "parent_table"},
        {"id": "incident_table_block", "type": "table", "tableId": "incident_table"},
        {
            "id": "comparison_finding",
            "type": "markdown",
            "sourceId": "src_comparison",
            "body": (
                "## SE3 已降低源项，但尚未证明 final delayed 优于 S3d\n\n"
                "SE3 将 cold-plate A15 降低约 51.8%，Cu-62/64 A15 各降低约 31%，并移除了 S3d 中磁屏蔽的主要 selected delayed 中央贡献。"
                "但 SE3 delayed 为 0.06011 ± 0.02003 cps，S3d 为 0.05448 ± 0.01016 cps，差异只有约 0.25σ；当前样本每族约 83,334 次 delayed trigger，分体积 Neff 很低。"
                "因此可据来源构成确定优化方向，不能据 0.0601/0.0545 的点估计宣布 SE3 退化或晋级。"
            ),
        },
        {"id": "comparison_table_block", "type": "table", "tableId": "comparison_table"},
        {
            "id": "optimization_design",
            "type": "markdown",
            "sourceId": "src_actions",
            "body": (
                "## 推荐方案：SE3-v2“近场 Cu 减影 + 冷板错孔”\n\n"
                "先做两个嵌套、可归因的几何变体。**V2A** 把 50 mK Cu can 底盖改为环形盖加少量径向热桥，把 L0 实心盘改为 open-ring/spoke，并把热带和锚点移出 TES 直视固角。"
                "**V2B** 在 V2A 上重排 MXC 开孔到 TES 投影方向，同时错开五块冷板的 48 孔图案，消除当前 16 组两板投影重合通道。BGO、塑闪、BPE port 与 W/FoV 全部冻结。"
                "只有 V2A/B 仍不足时，才在 37.96 mm 光学走廊之外试验分段 shadow cup / graded liner；任何 Ta/W/Pb/Al 替材都必须有候选自有 BUILDUP，不能把被动衰减收益与新增活化拆开估。"
            ),
        },
        {"id": "actions_table_block", "type": "table", "tableId": "actions_table"},
        {
            "id": "expected_result",
            "type": "markdown",
            "sourceId": "src_sensitivity",
            "body": (
                "## 预期：32–45% delayed 降幅是首轮合理区间\n\n"
                "V2A 直接覆盖当前约 39.0% 的 delayed 中央率；V2B 加上 MXC 后覆盖约 64.1%。若它们对目标部件实现 50–70% 抑制，则总 delayed 的透明筛选预期约下降 32–45%，即约 0.033–0.042 cps。"
                "在 signal Aeff 保留 98% 的统一缩放情景下，背景下降 40%、50%、60%、65% 时，F3 分别约为 5.81、5.30、4.74、4.44 ×10⁻⁵。"
                "这些值是份额敏感性和晋级尺，不是未经 transport 的物理预言。"
            ),
        },
        {"id": "sensitivity_chart_block", "type": "chart", "chartId": "sensitivity_chart"},
        {"id": "gates_table_block", "type": "table", "tableId": "gates_table"},
        {
            "id": "methodology",
            "type": "markdown",
            "body": (
                "## 方法与复用代码\n\n"
                "本次只读复用 corrected SE3 response/catalogue、S3d 的 `scan_target_inits/classify_entry` 与 selected-lineage 反查方法；只扫描 10 个含目标事件的 prompt SIM 文件，没有启动 transport，也没有做额外大文件哈希。"
                "activation 以 geometry × family 内 `sum(RP)/sum(TT)`、NUBASE ground-state、exact-position parent/volume 为合同；prompt 与 delayed 均在同一响应、veto、W2 和 Step05 下比较。"
                "下一轮先做现有 exact-position source 的 response-only shadowing replay，再为入围几何跑 fresh corrected BUILDUP→inventory→delayed，最后用同一 37,194 条 full-envelope ray bank 做 signal 与 prompt canary。"
            ),
        },
        {
            "id": "limitations",
            "type": "markdown",
            "body": (
                "## 不确定性与稳健性边界\n\n"
                "- final delayed 只有 47 个加权事件，若干体积的 Neff≈1；分体积点估计适合定方向，不适合精排。\n"
                "- SE3 full-envelope Aeff=11.6948 cm² 与历史 S3d post-Be Aeff=15.0417 cm² 的注入面不同，不能直接形成公平比值。\n"
                "- current total-gamma 已包含湮没隆起；若未来重建 continuum+mono，必须先显式减线并做 flux closure。\n"
                "- 几何减影优先于材料替换；材料替换会改变自身活化，不能只做衰减响应重放后就晋级。"
            ),
        },
        {
            "id": "next_steps",
            "type": "markdown",
            "body": (
                "## 建议的下一轮执行顺序\n\n"
                "1. 建 V2A/V2B 两个嵌套几何，并做质量、热路、磁需求、overlap/navigation 审核。\n"
                "2. 用现有 exact-position delayed source 做 response-only 视线筛选，定位几何耦合收益。\n"
                "3. 对入围者跑 fresh corrected-keV BUILDUP→inventory→delayed；对 Cu-61/62/64 × cap/MXC/L0/4K 做分层 importance sampling。\n"
                "4. 用同一 full-envelope signal ray bank 和 paired prompt seeds 做 matched closure；按下表 gate 晋级。"
            ),
        },
        {
            "id": "further_questions",
            "type": "markdown",
            "body": (
                "## 仍需工程侧回答的问题\n\n"
                "- 50 mK can 底盖和 L0 盘允许保留的最小热导、刚度与磁屏蔽边界是多少？\n"
                "- 五块冷板的 48 孔是否有不可移动的线束、支撑或热带 keep-out？\n"
                "- 若 V2A/B 不足，局部 shadow cup 的候选材料、最大质量和可接受自身活化上限是什么？\n"
                "- 能否补一个同注入面的 S3d full-envelope signal control，以关闭 Aeff 比较缺口？"
            ),
        },
    ]

    manifest = {
        "version": 1,
        "surface": "report",
        "title": TITLE,
        "generatedAt": GENERATED_AT,
        "blocks": blocks,
        "cards": [
            {
                "id": "card_delayed",
                "dataset": "headline",
                "sourceId": "src_headline",
                "description": "day-15 final delayed W2；后续指标为同一 MC 估计的统计支持。",
                "metrics": [
                    {"label": "delayed W2", "field": "selected_delayed_rate_cps", "format": "number", "unit": "cps"},
                    {"label": "MC σ", "field": "selected_delayed_sigma_cps", "format": "number", "unit": "cps"},
                    {"label": "survivors", "field": "selected_delayed_events", "format": "number"},
                ],
            },
            {
                "id": "card_prompt",
                "dataset": "headline",
                "sourceId": "src_headline",
                "description": "SE3 W2 prompt 在 50 keV active veto 后的观测中央率。",
                "metrics": [
                    {"label": "prompt post-veto", "field": "prompt_post_veto_rate_cps", "format": "number", "unit": "cps"},
                    {"label": "pre-veto", "field": "prompt_pre_veto_rate_cps", "format": "number", "unit": "cps"},
                ],
            },
            {
                "id": "card_cu",
                "dataset": "headline",
                "sourceId": "src_headline",
                "description": "Cu-61、Cu-62、Cu-64 占最终 delayed W2 的加权率份额。",
                "metrics": [
                    {"label": "Cu parents", "field": "selected_cu_parent_share", "format": "percent"},
                ],
            },
            {
                "id": "card_f3",
                "dataset": "headline",
                "sourceId": "src_headline",
                "description": "SE3 central 20-day mission fold；显示值单位为 ×10⁻⁵ ph cm⁻² s⁻¹。",
                "metrics": [
                    {"label": "F3", "field": "baseline_F3_e5", "format": "number", "unit": "×10⁻⁵"},
                    {"label": "Z20", "field": "baseline_Z20", "format": "number"},
                ],
            },
        ],
        "charts": [
            {
                "id": "prompt_ingress_chart",
                "title": "SE3 prompt W2 的 local-envelope 入射面",
                "subtitle": "120 个 pre-veto W2；IA INIT 方向代理、family-weighted rate share，post-veto 全为零",
                "type": "horizontalBar",
                "dataset": "prompt_ingress",
                "sourceId": "src_prompt_ingress",
                "valueFormat": "percent",
                "encodings": {
                    "x": {"field": "surface", "type": "nominal"},
                    "y": {"field": "rate_share", "type": "quantitative", "format": "percent"},
                },
            },
            {
                "id": "delayed_volume_chart",
                "title": "SE3 final delayed W2 生产体积",
                "subtitle": "七个观测主导体积；单位 10⁻³ cps，误差与 Neff 见数据详情",
                "type": "horizontalBar",
                "dataset": "delayed_volume",
                "sourceId": "src_volume",
                "valueFormat": "number",
                "encodings": {
                    "x": {"field": "volume", "type": "nominal"},
                    "y": {"field": "selected_rate_milli_cps", "type": "quantitative", "unit": "10⁻³ cps"},
                },
            },
            {
                "id": "sensitivity_chart",
                "title": "背景降低对 20-day F3 的敏感性",
                "subtitle": "signal Aeff 固定保留 98%；为筛选目标，不是 candidate transport 预测",
                "type": "line",
                "dataset": "sensitivity",
                "sourceId": "src_sensitivity",
                "valueFormat": "number",
                "encodings": {
                    "x": {"field": "background_reduction_fraction", "type": "quantitative", "format": "percent"},
                    "y": {"field": "F3_e5", "type": "quantitative", "unit": "×10⁻⁵ ph cm⁻² s⁻¹"},
                },
            },
        ],
        "tables": [
            {
                "id": "geometry_table",
                "title": "Mass → S3d-O8 → SE3 的设计演化",
                "subtitle": "几何事实与当前物理 authority 分列，避免把历史率带入现行比较",
                "dataset": "geometry",
                "sourceId": "src_geometry",
                "defaultSort": {"field": "design", "direction": "asc"},
                "columns": [
                    {"field": "design", "label": "设计"},
                    {"field": "near_tes_structure", "label": "近 TES / 低温结构"},
                    {"field": "active_veto", "label": "主动屏蔽"},
                    {"field": "role", "label": "本项目角色"},
                    {"field": "current_authority", "label": "当前 authority"},
                ],
            },
            {
                "id": "prompt_veto_table",
                "title": "SE3 prompt W2 的 veto 分工",
                "subtitle": "两条主动 veto 路径互补，合计覆盖 100% pre-veto W2 加权率",
                "dataset": "prompt_veto",
                "sourceId": "src_prompt_veto",
                "defaultSort": {"field": "rate_cps", "direction": "desc"},
                "columns": [
                    {"field": "veto_route", "label": "拒绝路径"},
                    {"field": "events", "label": "事件数", "format": "number"},
                    {"field": "rate_cps", "label": "加权率", "format": "number", "unit": "cps"},
                    {"field": "rate_share", "label": "率份额", "format": "percent"},
                    {"field": "post_route_survivors", "label": "剩余", "format": "number"},
                ],
            },
            {
                "id": "material_table",
                "title": "day-15 活度与 final delayed W2 的材料错位",
                "subtitle": "activity 与 selected rate 使用同一 SE3 inventory/lineage，但物理含义不同",
                "dataset": "material",
                "sourceId": "src_material",
                "defaultSort": {"field": "selected_rate_milli_cps", "direction": "desc"},
                "columns": [
                    {"field": "material", "label": "材料组"},
                    {"field": "activity_Bq", "label": "A15", "format": "number", "unit": "Bq"},
                    {"field": "activity_share", "label": "活度份额", "format": "percent"},
                    {"field": "selected_events", "label": "final 事件", "format": "number"},
                    {"field": "selected_rate_milli_cps", "label": "final 率", "format": "number", "unit": "10⁻³ cps"},
                    {"field": "selected_rate_share", "label": "final 率份额", "format": "percent"},
                    {"field": "selected_Neff", "label": "Neff", "format": "number"},
                ],
            },
            {
                "id": "comparison_table",
                "title": "S3d-O8 与 SE3 的 corrected-keV 对照",
                "subtitle": "源项改善清楚；final rate 受 1/3 delayed 统计限制",
                "dataset": "comparison",
                "sourceId": "src_comparison",
                "defaultSort": {"field": "metric", "direction": "asc"},
                "columns": [
                    {"field": "metric", "label": "指标"},
                    {"field": "unit", "label": "单位"},
                    {"field": "s3d", "label": "S3d-O8", "format": "number"},
                    {"field": "se3", "label": "SE3", "format": "number"},
                    {"field": "se3_change", "label": "SE3 变化", "format": "percent", "movement": True},
                    {"field": "interpretation", "label": "解释"},
                ],
            },
            {
                "id": "parent_table",
                "title": "final delayed W2 的 radioactive parent",
                "subtitle": "Cu-61/62/64 合计约 93.0% 加权率；K-38 为单个高权重事件",
                "dataset": "delayed_parent",
                "sourceId": "src_parent",
                "defaultSort": {"field": "selected_rate_milli_cps", "direction": "desc"},
                "columns": [
                    {"field": "parent", "label": "母核"},
                    {"field": "activity_Bq", "label": "A15", "format": "number", "unit": "Bq"},
                    {"field": "selected_events", "label": "final 事件", "format": "number"},
                    {"field": "selected_rate_milli_cps", "label": "final 率", "format": "number", "unit": "10⁻³ cps"},
                    {"field": "selected_rate_share", "label": "率份额", "format": "percent"},
                    {"field": "selected_Neff", "label": "Neff", "format": "number"},
                ],
            },
            {
                "id": "incident_table",
                "title": "活化入射族：总活度与 final delayed W2",
                "subtitle": "总活度由 p/n/alpha 主导；final W2 中 p+n 约占 86.8%",
                "dataset": "incident",
                "sourceId": "src_incident",
                "defaultSort": {"field": "selected_rate_milli_cps", "direction": "desc"},
                "columns": [
                    {"field": "incident_family", "label": "入射族"},
                    {"field": "activity_Bq", "label": "A15", "format": "number", "unit": "Bq"},
                    {"field": "activity_share", "label": "活度份额", "format": "percent"},
                    {"field": "selected_events", "label": "final 事件", "format": "number"},
                    {"field": "selected_rate_milli_cps", "label": "final 率", "format": "number", "unit": "10⁻³ cps"},
                    {"field": "selected_rate_share", "label": "率份额", "format": "percent"},
                ],
            },
            {
                "id": "actions_table",
                "title": "SE3-v2 嵌套变体",
                "subtitle": "先做可归因的 Cu 减影与错孔，局部 liner 只作为不足时的第三步",
                "dataset": "actions",
                "sourceId": "src_actions",
                "defaultSort": {"field": "variant", "direction": "asc"},
                "columns": [
                    {"field": "variant", "label": "变体"},
                    {"field": "geometry_action", "label": "几何动作"},
                    {"field": "targeted_current_share", "label": "覆盖当前中央率份额", "format": "percent"},
                    {"field": "risk", "label": "风险"},
                    {"field": "why", "label": "证据依据"},
                ],
            },
            {
                "id": "gates_table",
                "title": "candidate 晋级门",
                "subtitle": "中心值、区间、signal 与工程约束必须同时满足",
                "dataset": "gates",
                "sourceId": "src_gates",
                "defaultSort": {"field": "gate", "direction": "asc"},
                "columns": [
                    {"field": "gate", "label": "门"},
                    {"field": "promotion_threshold", "label": "阈值"},
                    {"field": "reason", "label": "原因"},
                ],
            },
        ],
        "sources": sources,
    }

    snapshot = {
        "version": 1,
        "generatedAt": GENERATED_AT,
        "status": "ready",
        "datasets": {
            "headline": headline,
            "geometry": geometry_rows,
            "prompt_ingress": prompt_ingress,
            "prompt_veto": prompt_veto,
            "material": material_rows,
            "delayed_volume": chosen_volumes,
            "delayed_parent": parent_rows,
            "incident": incident_rows,
            "comparison": comparison_rows,
            "sensitivity": sensitivity_rows,
            "actions": actions,
            "gates": gates,
        },
    }
    payload = {
        "surface": "report",
        "manifest": manifest,
        "snapshot": snapshot,
        "sources": sources,
    }
    ARTIFACT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "PASS",
        "artifact": str(ARTIFACT),
        "datasets": {key: len(rows) for key, rows in snapshot["datasets"].items()},
        "large_payload_hashes_computed": 0,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
