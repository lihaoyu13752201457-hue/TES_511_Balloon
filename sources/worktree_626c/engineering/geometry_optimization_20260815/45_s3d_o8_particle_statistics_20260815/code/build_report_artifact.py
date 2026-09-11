#!/usr/bin/env python3
"""Build the bounded MCP report artifact for the S3d-O8 statistics record."""

from __future__ import annotations

import csv
import json
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
DATA = PACKAGE / "data"
OUTPUT = PACKAGE / "report_artifact.json"


def read_csv(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(newline="") as handle:
        return list(csv.DictReader(handle))


def number(value: str):
    if value == "True":
        return True
    if value == "False":
        return False
    try:
        if value.strip() and all(c not in value.lower() for c in (".", "e")):
            return int(value)
        return float(value)
    except (ValueError, AttributeError):
        return value


def main() -> None:
    raw_family = read_csv("s3d_o8_particle_family_statistics.csv")
    raw_mission = read_csv("s3d_o8_mission20_counts_by_family.csv")
    raw_signal = read_csv("s3d_o8_focused_511_signal_statistics.csv")
    summary = json.loads((DATA / "s3d_o8_particle_statistics_summary.json").read_text())
    validation = json.loads(
        (PACKAGE / "audit/s3d_o8_particle_statistics_validation.json").read_text()
    )

    family_rows = [{k: number(v) for k, v in row.items()} for row in raw_family]
    mission_rows = [{k: number(v) for k, v in row.items()} for row in raw_mission]
    signal_rows = [{k: number(v) for k, v in row.items()} for row in raw_signal]
    rank_order = ("gamma", "n", "p", "alpha", "eplus", "eminus", "muminus", "muplus")
    rank = {family: idx + 1 for idx, family in enumerate(rank_order)}

    w2_rates = []
    for row in family_rows:
        for stream in ("prompt", "delayed"):
            w2_rates.append(
                {
                    "family": row["family"],
                    "particle_label": row["particle_label"],
                    "family_rank": rank[row["family"]],
                    "stream": stream,
                    "stream_label": "Prompt" if stream == "prompt" else "Delayed",
                    "selected_events": row[f"{stream}_w2_final_events"],
                    "rate_cps": row[f"{stream}_w2_final_rate_cps"],
                    "stat_sigma_cps": row[f"{stream}_w2_final_stat_sigma_cps"],
                    "lower95_cps": row[f"{stream}_w2_final_lower95_cps"],
                    "upper95_cps": row[f"{stream}_w2_final_upper95_cps"],
                    "support_flag": row[f"{stream}_support_flag"],
                }
            )
    w2_rates.sort(key=lambda row: (row["family_rank"], 0 if row["stream"] == "prompt" else 1))

    totals = summary["totals"]
    authority_count = len(summary["source_authorities"])
    mission_exclusions = summary["mission_known_exclusions"]
    delayed_np_share = sum(
        row["delayed_fraction_of_stream"]
        for row in family_rows
        if row["family"] in {"n", "p"}
    )

    sources = [
        {
            "id": "current_record",
            "label": "S3d-O8 current all-particle statistics summary",
            "path": "data/s3d_o8_particle_statistics_summary.json",
            "query": {
                "engine": "filesystem-python",
                "language": "python",
                "description": "Hash-pinned deterministic extraction from the 2026-08-13 corrected-keV M05 authority.",
                "executed_at": "2026-08-15T00:00:00+08:00",
                "tables_used": [
                    "data/s3d_o8_particle_statistics_summary.json",
                    "audit/s3d_o8_particle_statistics_validation.json",
                ],
                "metric_definitions": [
                    "W2 final means measured 0.42-keV FWHM response, pixel threshold 0.3 keV, 50-keV active veto, and retained Step05 side-Compton/FoV pass.",
                    "Prompt is normalized within family as N_selected/sum(instant TT); activation as sum(RP)/sum(buildup TT); delayed as N_selected x day-15 ground activity/250000 triggers.",
                ],
            },
        },
        {
            "id": "family_table",
            "label": "Eight-family input, activation, response, and mission statistics",
            "path": "data/s3d_o8_particle_family_statistics.csv",
            "query": {
                "engine": "csv-snapshot",
                "language": "sql",
                "sql": "SELECT * FROM s3d_o8_particle_family_statistics ORDER BY family",
                "description": "Exact eight-row current S3d-O8 particle-family record.",
                "executed_at": "2026-08-15T00:00:00+08:00",
                "tables_used": ["data/s3d_o8_particle_family_statistics.csv"],
                "filters": ["model_identity=S3d-O8", "authority=M05 corrected-keV 2026-08-13"],
                "metric_definitions": [
                    "Prompt and delayed rates are central weighted Monte Carlo rates in cps.",
                    "Garwood 95% bounds are componentwise count intervals; zero-survivor upper limits are not physical-zero claims.",
                ],
            },
        },
        {
            "id": "mission_table",
            "label": "S3d-O8 20-day family-scalar mission counts",
            "path": "data/s3d_o8_mission20_counts_by_family.csv",
            "query": {
                "engine": "csv-snapshot",
                "language": "sql",
                "sql": "SELECT * FROM s3d_o8_mission20_counts_by_family ORDER BY total_background_counts_20d DESC",
                "description": "Per-family integration of each timeline rate times accidental live factor and quadrature weight over 81 bins.",
                "executed_at": "2026-08-15T00:00:00+08:00",
                "tables_used": ["data/s3d_o8_mission20_counts_by_family.csv"],
                "metric_definitions": [
                    "20-day family counts are forward-analytic family-scalar integrals, not independent re-transports at every timeline point.",
                    "No reliable per-family cumulative Monte Carlo variance was propagated.",
                ],
            },
        },
        {
            "id": "signal_table",
            "label": "Focused 511-keV signal acceptance",
            "path": "data/s3d_o8_focused_511_signal_statistics.csv",
            "query": {
                "engine": "csv-snapshot",
                "language": "sql",
                "sql": "SELECT * FROM s3d_o8_focused_511_signal_statistics",
                "description": "Post-Be-window focused gamma EventList acceptance and mission signal, kept separate from broadband atmospheric gamma background.",
                "executed_at": "2026-08-15T00:00:00+08:00",
                "tables_used": ["data/s3d_o8_focused_511_signal_statistics.csv"],
                "metric_definitions": [
                    "Acceptance=selected_events/trials after measured W2, veto50, and retained Step05.",
                    "Selected effective area=input optics effective area x acceptance.",
                ],
            },
        },
        {
            "id": "authority_ledger",
            "label": "Pinned upstream authority ledger",
            "path": "data/s3d_o8_authority_sources.csv",
            "query": {
                "engine": "csv-snapshot",
                "language": "sql",
                "sql": "SELECT id, path, sha256, size_bytes FROM s3d_o8_authority_sources ORDER BY id",
                "description": "Absolute paths, SHA256 hashes, and sizes checked before extraction.",
                "executed_at": "2026-08-15T00:00:00+08:00",
                "tables_used": ["data/s3d_o8_authority_sources.csv"],
            },
        },
    ]

    title = "S3d-O8 当前八粒子统计基线"
    manifest = {
        "version": 1,
        "surface": "report",
        "title": title,
        "description": "2026-08-13 corrected-keV M05 全八族输入、活化、W2 response 与 20 日任务积分的可复核记录。",
        "generatedAt": "2026-08-15T00:00:00+08:00",
        "sources": sources,
        "cards": [],
        "charts": [
            {
                "id": "w2_rate_by_family_stream",
                "title": "S3d-O8 W2 最终率（按入射粒子族与流）",
                "subtitle": f"Prompt 仅 gamma 有 2 个 survivor；delayed 的 n+p 占 {delayed_np_share:.2%}。零 survivor 仍保留 95% 上限。",
                "type": "bar",
                "dataset": "w2_rates",
                "sourceId": "family_table",
                "encodings": {
                    "x": {
                        "field": "particle_label",
                        "type": "ordinal",
                        "label": "Incident particle family",
                    },
                    "y": {
                        "field": "rate_cps",
                        "type": "quantitative",
                        "label": "Final W2 rate (cps)",
                        "format": ".6g",
                    },
                    "color": {
                        "field": "stream_label",
                        "type": "nominal",
                        "label": "Stream",
                    },
                },
                "yAxisTitle": "Final W2 rate (cps)",
                "valueFormat": ".6g",
                "layout": "full",
            }
        ],
        "tables": [
            {
                "id": "w2_family_exact",
                "title": "逐粒子族 W2 最终统计与 95% 区间",
                "dataset": "family_stats",
                "sourceId": "family_table",
                "defaultSort": {"field": "delayed_w2_final_rate_cps", "direction": "desc"},
                "columns": [
                    {"field": "particle_label", "label": "Particle", "type": "text"},
                    {"field": "prompt_w2_final_events", "label": "Prompt N", "format": ".0f"},
                    {"field": "prompt_w2_final_rate_cps", "label": "Prompt cps", "format": ".8g"},
                    {"field": "prompt_w2_final_stat_sigma_cps", "label": "Prompt sigma", "format": ".8g"},
                    {"field": "prompt_w2_final_upper95_cps", "label": "Prompt upper95", "format": ".8g"},
                    {"field": "delayed_w2_final_events", "label": "Delayed N", "format": ".0f"},
                    {"field": "delayed_w2_final_rate_cps", "label": "Delayed cps", "format": ".8g"},
                    {"field": "delayed_w2_final_stat_sigma_cps", "label": "Delayed sigma", "format": ".8g"},
                    {"field": "delayed_w2_final_lower95_cps", "label": "Delayed lower95", "format": ".8g"},
                    {"field": "delayed_w2_final_upper95_cps", "label": "Delayed upper95", "format": ".8g"},
                    {"field": "delayed_support_flag", "label": "Delayed support", "type": "text"},
                ],
            },
            {
                "id": "input_activation_exact",
                "title": "逐粒子族输入与活化统计",
                "dataset": "family_stats",
                "sourceId": "family_table",
                "defaultSort": {"field": "prompt_histories", "direction": "desc"},
                "columns": [
                    {"field": "particle_label", "label": "Particle", "type": "text"},
                    {"field": "source_flux_sum_cm_2_s_1", "label": "Source flux", "format": ".8g"},
                    {"field": "prompt_jobs", "label": "Instant jobs", "format": ".0f"},
                    {"field": "prompt_histories", "label": "Instant histories", "format": ".0f"},
                    {"field": "prompt_TT_s", "label": "Instant TT (s)", "format": ".8g"},
                    {"field": "activation_jobs", "label": "Buildup files", "format": ".0f"},
                    {"field": "activation_histories", "label": "Buildup histories", "format": ".0f"},
                    {"field": "activation_RP", "label": "RP", "format": ".0f"},
                    {"field": "day15_ground_activity_Bq", "label": "Day-15 ground Bq", "format": ".9g"},
                    {"field": "transported_ground_unique_ZA", "label": "Unique ground ZA", "format": ".0f"},
                    {"field": "delayed_transport_triggers", "label": "Delayed triggers", "format": ".0f"},
                    {"field": "delayed_source_sampling_seed", "label": "Source seed", "format": ".0f"},
                    {"field": "delayed_transport_seed", "label": "Transport seed", "format": ".0f"},
                ],
            },
            {
                "id": "mission_counts_exact",
                "title": "逐粒子族 20 日任务积分 counts",
                "dataset": "mission_counts",
                "sourceId": "mission_table",
                "defaultSort": {"field": "total_background_counts_20d", "direction": "desc"},
                "columns": [
                    {"field": "particle_label", "label": "Particle", "type": "text"},
                    {"field": "prompt_counts_20d", "label": "Prompt counts", "format": ".9g"},
                    {"field": "delayed_counts_20d", "label": "Delayed counts", "format": ".9g"},
                    {"field": "total_background_counts_20d", "label": "Total B counts", "format": ".9g"},
                    {"field": "uncertainty_status", "label": "Uncertainty status", "type": "text"},
                ],
            },
            {
                "id": "signal_exact",
                "title": "Focused 511-keV signal（独立于背景 gamma）",
                "dataset": "signal_stats",
                "sourceId": "signal_table",
                "defaultSort": {"field": "component", "direction": "asc"},
                "columns": [
                    {"field": "component", "label": "Component", "type": "text"},
                    {"field": "trials", "label": "Trials", "format": ".0f"},
                    {"field": "selected_events", "label": "Selected", "format": ".0f"},
                    {"field": "acceptance", "label": "Acceptance", "format": "percent"},
                    {"field": "acceptance_lower95", "label": "Acceptance lower95", "format": "percent"},
                    {"field": "acceptance_upper95", "label": "Acceptance upper95", "format": "percent"},
                    {"field": "selected_effective_area_cm2", "label": "Aeff (cm2)", "format": ".8g"},
                    {"field": "mission20_signal_counts", "label": "20d signal counts", "format": ".9g"},
                    {"field": "mission20_signal_lower95_counts", "label": "20d signal lower95", "format": ".9g"},
                    {"field": "scope", "label": "Scope", "type": "text"},
                ],
            },
        ],
        "blocks": [
            {"id": "title", "type": "markdown", "body": f"# {title}"},
            {
                "id": "technical_summary_heading",
                "type": "markdown",
                "body": "## 技术摘要",
            },
            {
                "id": "technical_summary",
                "type": "markdown",
                "sourceId": "current_record",
                "body": (
                    f"当前权威是 **2026-08-13 corrected-keV M05**。W2 最终 prompt 为 **2 events / {totals['prompt_w2_final_rate_cps']:.12g} ± {totals['prompt_w2_final_stat_sigma_cps']:.12g} cps**，且两条都属于 gamma；delayed 为 **420 events / {totals['delayed_w2_final_rate_cps']:.12g} ± {totals['delayed_w2_final_stat_sigma_cps']:.12g} cps**。常环境 day-15 总背景为 **{totals['day15_constant_environment_total_background_cps']:.12g} cps**。"
                ),
            },
            {
                "id": "key_findings_heading",
                "type": "markdown",
                "body": "## 关键结果与可视证据",
            },
            {"id": "w2_chart_block", "type": "chart", "chartId": "w2_rate_by_family_stream", "layout": "full"},
            {
                "id": "w2_table_heading",
                "type": "markdown",
                "body": "## W2 最终逐族统计",
            },
            {"id": "w2_table_block", "type": "table", "tableId": "w2_family_exact", "layout": "full"},
            {
                "id": "scope_heading",
                "type": "markdown",
                "body": "## 范围、定义与输入统计",
            },
            {
                "id": "scope_text",
                "type": "markdown",
                "sourceId": "current_record",
                "body": (
                    "W2 定义为 510.58–511.42 keV；measured response 使用 0.42-keV FWHM、0.3-keV pixel threshold、50-keV active veto，最终执行 retained Step05 side-Compton/FoV。Prompt 在每族内用 `N_selected/sum(instant TT)`；activation 用 `sum(RP)/sum(buildup TT)`；delayed 用 `N_selected × day-15 ground Bq/250000 triggers`。禁止跨族合并 TT。"
                ),
            },
            {"id": "input_table_block", "type": "table", "tableId": "input_activation_exact", "layout": "full"},
            {
                "id": "mission_heading",
                "type": "markdown",
                "body": "## 20 日任务积分",
            },
            {
                "id": "mission_text",
                "type": "markdown",
                "sourceId": "current_record",
                "body": (
                    f"20 日、81-node forward-analytic family-scalar fold 给出 prompt **{totals['mission20_prompt_counts']:.9f}**、delayed **{totals['mission20_delayed_counts']:.9f}**、总背景 **{totals['mission20_total_background_counts']:.9f}** counts；signal 为 **{totals['mission20_signal_counts']:.9f}** counts。Signal 使用 post-Be-window Aeff、45° slant transmission 和 top-of-atmosphere 1e-4 ph cm^-2 s^-1；day 0 inventory=0，排除 pre-flight/ground activation。背景 gamma 为 `unit_only_total_gamma`，无 additive mono-511。"
                ),
            },
            {"id": "mission_table_block", "type": "table", "tableId": "mission_counts_exact", "layout": "full"},
            {
                "id": "signal_heading",
                "type": "markdown",
                "body": "## Focused 511-keV signal（单列，不混入八族背景）",
            },
            {"id": "signal_table_block", "type": "table", "tableId": "signal_exact", "layout": "full"},
            {
                "id": "method_heading",
                "type": "markdown",
                "body": "## 方法与复现",
            },
            {
                "id": "method_text",
                "type": "markdown",
                "sourceId": "authority_ledger",
                "body": f"生成器在提取前逐一核对 {authority_count} 个上游文件的 SHA256，并对输入规模、活度、双 seed、cutflow、budget、focused signal、81-bin 积分、mission exclusions 及总量执行 {len(validation['checks'])} 个闭合门。它只读取已有产物，不启动 transport。",
            },
            {
                "id": "limitations_heading",
                "type": "markdown",
                "body": "## 限制与稳健性",
            },
            {
                "id": "limitations_text",
                "type": "markdown",
                "sourceId": "current_record",
                "body": (
                    "Prompt 只有 2 个 gamma survivor，统计支持很低；所有零 survivor 必须解释为带 95% 上限的未观测，而不是物理零。Delayed 区间仅覆盖 transport counting。20 日逐族 counts 没有可靠累计 MC 方差传播。大型 SIM 未在本次记录中重新逐字节哈希，而是继承 terminal ledger/receipt 声明。旧 package-43 结果和 frozen pixel/L3 diagnostic 与当前口径不同，禁止混算。\n\n**Mission authority 的完整 known exclusions：**\n\n"
                    + "\n".join(f"- {item}" for item in mission_exclusions)
                ),
            },
            {
                "id": "next_heading",
                "type": "markdown",
                "body": "## 建议的下一步",
            },
            {
                "id": "next_text",
                "type": "markdown",
                "body": "把这份 corrected M05 八族表作为后续 S3d-O8 与 SE3 的同口径基线；任何 SE3 统计都应复用相同粒子源合同、W2 response、逐族 TT 归一和 family-resolved 上限规则。",
            },
            {
                "id": "questions_heading",
                "type": "markdown",
                "body": "## 后续待回答问题",
            },
            {
                "id": "questions_text",
                "type": "markdown",
                "body": "SE3 是否需要对 prompt gamma、delayed p/n/alpha 三个低统计分量追加等精度 transport？source-position mixture 与 buildup-yield 系统学如何纳入统一区间？这些属于下一阶段统计设计，不在本次只读记录范围。",
            },
        ],
    }

    artifact = {
        "surface": "report",
        "manifest": manifest,
        "snapshot": {
            "version": 1,
            "generatedAt": "2026-08-15T00:00:00+08:00",
            "status": "ready",
            "datasets": {
                "family_stats": family_rows,
                "w2_rates": w2_rates,
                "mission_counts": mission_rows,
                "signal_stats": signal_rows,
            },
        },
        "sources": sources,
        "package_info": {
            "model_identity": "S3d-O8",
            "record_status": summary["status"],
            "local_package": str(PACKAGE),
        },
    }
    OUTPUT.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "BUILT", "path": str(OUTPUT), "rows": {"family_stats": 8, "w2_rates": 16, "mission_counts": 8, "signal_stats": 1}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
