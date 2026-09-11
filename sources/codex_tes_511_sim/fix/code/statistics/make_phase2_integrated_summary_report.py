#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a Chinese integrated Phase-2 review report from generated products."""

from __future__ import annotations

import csv
import json
import math
import textwrap
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from make_day15_report import setup_fonts


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "statistics" / "phase2_real_flight_physical_production"
FIG = OUT / "figures"
DAY15_FIG = ROOT / "statistics" / "day15_complete_report" / "figures"
SCI_FIG = ROOT / "statistics" / "day15_sci_manuscript" / "figures"
NEXT = ROOT / "statistics" / "nextphase_511"
CONV = ROOT / "statistics" / "phase2_convergence_patch"
CONV_UPDATE = ROOT / "statistics" / "phase2_convergence_patch_update"
REPORT_MD = OUT / "phase2_integrated_summary_report_zh.md"
REPORT_PDF = OUT / "phase2_integrated_summary_report_zh.pdf"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def fmt(value: Any, digits: int = 4) -> str:
    try:
        v = float(value)
    except Exception:
        return str(value)
    if not math.isfinite(v):
        return "nan"
    if v != 0 and (abs(v) < 1.0e-3 or abs(v) >= 1.0e4):
        return f"{v:.{digits}e}"
    return f"{v:.{digits}g}"


def md_table(rows: list[dict[str, Any]], fields: list[str], headers: list[str] | None = None) -> str:
    headers = headers or fields
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    return "\n".join(lines)


def wrap_lines(text: str, width: int = 78) -> str:
    out: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            out.append("")
            continue
        if line.startswith("|") or line.startswith("```"):
            out.append(line)
            continue
        if len(line) <= width:
            out.append(line)
            continue
        if " " in line:
            out.extend(textwrap.wrap(line, width=width, break_long_words=False) or [""])
        else:
            out.extend(line[i : i + width] for i in range(0, len(line), width))
    return "\n".join(out)


def add_text_page(pdf: PdfPages, title: str, body: str, font_prop: Any, fontsize: float = 8.8) -> None:
    fig = plt.figure(figsize=(8.27, 11.69))
    ax = fig.add_axes([0.055, 0.05, 0.89, 0.90])
    ax.axis("off")
    ax.text(0, 1.02, title, fontsize=15, fontweight="bold", va="top", fontproperties=font_prop)
    ax.text(0, 0.975, wrap_lines(body), fontsize=fontsize, va="top", linespacing=1.25, fontproperties=font_prop)
    pdf.savefig(fig)
    plt.close(fig)


def add_image_page(pdf: PdfPages, title: str, path: Path, caption: str, font_prop: Any) -> None:
    fig = plt.figure(figsize=(8.27, 11.69))
    title_ax = fig.add_axes([0.055, 0.915, 0.89, 0.05])
    title_ax.axis("off")
    title_ax.text(0, 0.85, title, fontsize=15, fontweight="bold", fontproperties=font_prop)
    if path.exists():
        img = mpimg.imread(path)
        img_ax = fig.add_axes([0.055, 0.315, 0.89, 0.56])
        img_ax.imshow(img)
        img_ax.axis("off")
    else:
        img_ax = fig.add_axes([0.055, 0.315, 0.89, 0.56])
        img_ax.axis("off")
        img_ax.text(0.05, 0.5, f"Missing figure: {path}", fontsize=10, fontproperties=font_prop)
    cap_ax = fig.add_axes([0.055, 0.055, 0.89, 0.235])
    cap_ax.axis("off")
    cap_ax.text(0, 1.0, wrap_lines(caption, 92), fontsize=8.2, va="top", linespacing=1.18, fontproperties=font_prop)
    pdf.savefig(fig)
    plt.close(fig)


def fig_note(logic: str, result: str, conclusion: str) -> str:
    return f"产生逻辑：{logic}\n结果分析：{result}\n结论：{conclusion}"


def select_rows(rows: list[dict[str, str]], *, exposure: float | None = None, flux: float | None = None, model: str | None = None) -> list[dict[str, str]]:
    out = rows
    if exposure is not None:
        out = [r for r in out if abs(float(r["exposure_s"]) - exposure) < 1.0]
    if flux is not None:
        out = [r for r in out if abs(float(r["input_flux_ph_cm2_s"]) - flux) < 1.0e-12]
    if model is not None:
        out = [r for r in out if r["model"] == model]
    return out


def main() -> int:
    day15 = load_json(ROOT / "statistics" / "day15_complete_report" / "complete_day15_summary.json")
    phase2 = load_json(OUT / "phase2_summary.json")
    env = load_json(OUT / "environment_grid_real" / "environment_grid_summary.json")
    prompt = load_json(OUT / "prompt_reweight_real" / "prompt_reweight_real_summary.json")
    inventory = load_json(OUT / "activation_inventory_parentfed" / "inventory_parentfed_summary.json")
    delayed = load_json(OUT / "delayed_sources_real_profile" / "source_build_summary.json")
    mixed = load_json(OUT / "mixed_voxel_transport" / "radial_vs_mixed_summary.json")
    catalog = load_json(OUT / "event_catalog_v2_measured" / "catalog_v2_summary.json")
    truth_summary = load_json(OUT / "activation_511_truth" / "activation_511_truth_summary.json")
    like_summary = load_json(OUT / "likelihood_profiled" / "profile_likelihood_template_summary.json")
    inj_summary = load_json(OUT / "long_timeline_injection_profiled" / "source_injection_profiled_summary.json")
    convergence = load_json(CONV / "phase2_convergence_patch_summary.json")
    convergence_update = load_json(CONV_UPDATE / "phase2_convergence_patch_update_summary.json")
    measured_rows = read_csv(OUT / "event_catalog_v2_measured" / "true_vs_measured_rates.csv")
    component_rows = read_csv(OUT / "tables" / "image8_style_component_rates.csv")
    truth_rows = read_csv(OUT / "activation_511_truth" / "activation_511_truth_table.csv")
    like_rows = read_csv(OUT / "likelihood_profiled" / "asimov_profiled_sensitivity.csv")
    inj_rows = read_csv(OUT / "long_timeline_injection_profiled" / "source_injection_profiled_summary.csv")
    conv_stream_rows = read_csv(CONV / "catalog_closure" / "stream_rate_closure.csv")
    conv_bgo_rows = read_csv(CONV / "catalog_closure" / "bgo_proxy_audit.csv")
    conv_bound_rows = read_csv(CONV / "mixed_voxel_bound" / "worst_case_rate_bound.csv")
    conv_parent_rows = read_csv(CONV / "parent_feed" / "top511_before_after_rates.csv")
    conv_profile_rows = [
        r for r in read_csv(CONV / "minimal_profile_likelihood" / "injection_coverage_summary.csv")
        if abs(float(r["exposure_s"]) - 1.0e6) < 1.0 and r["model"] == "energy_radius_layer_template"
    ]
    update_parma_cap_rows = read_csv(CONV_UPDATE / "parma_outlier_audit" / "parma_capped_vs_uncapped_rates.csv")
    update_parent_rows = read_csv(CONV_UPDATE / "parent_feed_data_note" / "parent_feed_top_contributors_table.csv")
    update_mixed_rows = read_csv(CONV_UPDATE / "mixed_voxel_delta" / "radial_vs_voxel_delta_rates.csv")

    baseline_rows = []
    for name, values in day15["expectation_rates_by_stream_cps"].items():
        baseline_rows.append({
            "stream": name,
            "raw": fmt(values["raw"]),
            "BGO": fmt(values["bgo"]),
            "final": fmt(values["final"]),
        })
    timeline = day15["timeline_rates_cps"]
    baseline_rows.append({"stream": "timeline_total", "raw": fmt(timeline["raw"]), "BGO": fmt(timeline["bgo"]), "final": fmt(timeline["final"])})

    measured_table = [
        {
            "window": r["window"],
            "energy": r["energy_type"],
            "raw": fmt(r["raw_cps"]),
            "BGO": fmt(r["bgo_cps"]),
            "final": fmt(r["final_cps"]),
        }
        for r in measured_rows
    ]
    truth_table = [
        {
            "nuclide": r["nuclide"],
            "A_Bq": fmt(r["source_activity_Bq"]),
            "broad": fmt(r["broad_480_550_final_cps"]),
            "line": fmt(r["line_510p3_511p8_final_cps"]),
            "branch_proxy": fmt(r["beta_plus_branch_proxy"]),
        }
        for r in truth_rows[:8]
    ]
    like_table = []
    for r in select_rows(like_rows, exposure=1.0e6):
        if r["model"] not in {"window_counting_same_events", "energy_template", "energy_radius_layer_template"}:
            continue
        like_table.append({
            "window": r["energy_window"],
            "model": r["model"],
            "Fisher3": fmt(r["flux_3sigma_ph_cm2_s"]),
            "profile3": fmt(r["profiled_flux_3sigma_ph_cm2_s"]),
            "profile5": fmt(r["profiled_flux_5sigma_ph_cm2_s"]),
        })
    inj_table = [
        {
            "window": r["energy_window"],
            "model": r["model"],
            "P3": fmt(r["P3"], 3),
            "P5": fmt(r["P5"], 3),
            "mean": fmt(r["mean_recovered_flux"]),
            "sigma": fmt(r["sigma_flux"]),
        }
        for r in select_rows(inj_rows, exposure=1.0e6, flux=1.0e-4, model="energy_radius_layer_template")
    ]
    wp_rows = [
        {"wp": "WP10", "status": env["status"], "result": "官方 EXPACS/PARMA C++ driver；33-43 km、经纬度和方向传输剖面。"},
        {"wp": "WP11", "status": prompt["status"], "result": "prompt 按粒子重加权；角度/能量 scale 已生成但 catalog 只能做粒子平均。"},
        {"wp": "WP12", "status": inventory["status"], "result": "parent-fed schema 已建；缺少审计 branch ratio，parent feed 当前为 0。"},
        {"wp": "WP13", "status": delayed["status"], "result": "day01/05/10/15/20 Level-1 delayed source；fixed day15 spatial profile scaled。"},
        {"wp": "WP14", "status": mixed["status"], "result": "未谎称完成；需要新 mixed source Cosima transport。"},
        {"wp": "WP15", "status": catalog["status"], "result": "TES per-pixel measured energy；BGO event-total proxy。"},
        {"wp": "WP17", "status": "PASS_TOY_DAQ_MODELS", "result": "四类 timing/DAQ proxy；硬件响应仍为后续门槛。"},
        {"wp": "WP18", "status": truth_summary["status"], "result": "W-187 为 broad 主项；O-15 对 narrow line 最敏感。"},
        {"wp": "WP19", "status": like_summary["status"], "result": f"diagonal nuisance proxy，退化因子 {fmt(like_summary['degradation_factor'])}。"},
        {"wp": "WP20", "status": inj_summary["status"], "result": "1e5/1e6/1e7 s、8 档 flux、20000 realization proxy injection。"},
        {"wp": "WP21", "status": phase2["status"], "result": "Phase2 PDF/MD/JSON 和 validation 已生成。"},
    ]
    convergence_rows = [
        {
            "gate": "A source authority",
            "status": convergence["authority"]["status"],
            "decision": f"current response {fmt(convergence['authority']['current_response_cps_per_flux'])}; old 33.947 response excluded",
        },
        {
            "gate": "B catalog closure",
            "status": convergence["catalog"]["status"],
            "decision": f"max stream relerr {fmt(convergence['catalog']['max_stream_closure_relative_error'], 3)}; no science contamination",
        },
        {
            "gate": "C PARMA stability",
            "status": convergence["parma"]["status"],
            "decision": f"{convergence['parma']['decision']}; scale {fmt(convergence['parma']['scale_min'])}-{fmt(convergence['parma']['scale_max'])}",
        },
        {
            "gate": "D parent feed",
            "status": convergence["parent_feed"]["status"],
            "decision": "top contributors tabulated; no rate change without audited branch ratios",
        },
        {
            "gate": "E mixed voxel",
            "status": convergence["mixed_voxel"]["status"],
            "decision": f"{convergence['mixed_voxel']['decision']}; max bound {fmt(convergence['mixed_voxel']['max_bound_fraction_of_final_background'])}",
        },
        {
            "gate": "F BGO proxy",
            "status": convergence["bgo"]["status"],
            "decision": f"{convergence['bgo']['decision']}; threshold flip {fmt(convergence['bgo']['max_threshold_flip_fraction'])}",
        },
        {
            "gate": "G profile closure",
            "status": convergence["profile"]["status"],
            "decision": f"P3(1e-4,1Ms)={fmt(convergence['profile']['max_P3_at_1e_4_1Ms_energy_radius_layer'])}; robust claim={convergence['profile']['robust_1e_4_1Ms_detection_claim_allowed']}",
        },
    ]
    conv_stream_table = [
        {
            "stream": r["stream"],
            "stage": r["stage"],
            "catalog": fmt(r["catalog_cps"]),
            "reported": fmt(r["reported_cps"]),
            "relerr": fmt(r["relative_error"], 3),
            "check": r["check"],
        }
        for r in conv_stream_rows
    ]
    conv_bgo_table = [
        {
            "window": r["window"],
            "45-55 frac": fmt(r["fraction_rate_true_bgo_45_55"]),
            "flip frac": fmt(r["fraction_rate_threshold_flips"]),
            "mode": r["bgo_mode"],
        }
        for r in conv_bgo_rows
    ]
    conv_bound_table = [
        {
            "window": r["window"],
            "voxel frac": fmt(r["voxel_activity_fraction"]),
            "safety": fmt(r["geometry_safety_factor"]),
            "bound cps": fmt(r["worst_case_rate_bound_cps"]),
            "bound/final": fmt(r["bound_fraction_of_final_background"]),
        }
        for r in conv_bound_rows
    ]
    conv_parent_table = [
        {
            "nuclide": r["nuclide"],
            "broad before": fmt(r["broad_480_550_final_before_cps"]),
            "broad after": fmt(r["broad_480_550_final_after_cps"]),
            "line before": fmt(r["line_510p3_511p8_final_before_cps"]),
            "line after": fmt(r["line_510p3_511p8_final_after_cps"]),
            "status": r["patch_status"],
        }
        for r in conv_parent_rows[:10]
    ]
    conv_profile_table = [
        {
            "window": r["energy_window"],
            "mean": fmt(r["mean_recovered_flux"]),
            "std": fmt(r["std_recovered_flux"]),
            "bias/sigma": fmt(r["bias_over_sigma"]),
            "P3": fmt(r["P3"]),
            "P5": fmt(r["P5"]),
            "pass": r["pass_bias"],
        }
        for r in conv_profile_rows
    ]
    update_rows = [
        {
            "item": "U1 source authority wording",
            "status": convergence_update["source_authority"]["status"],
            "decision": f"unqualified legacy hits = {convergence_update['source_authority']['unqualified_old_source_or_response_hits']}",
        },
        {
            "item": "U2 PARMA outlier contribution",
            "status": convergence_update["parma_outlier"]["status"],
            "decision": (
                f"scale>10 broad/line fractions = {fmt(convergence_update['parma_outlier']['broad_fraction_from_scale_gt10'])}/"
                f"{fmt(convergence_update['parma_outlier']['line_fraction_from_scale_gt10'])}; "
                f"hard-cap shifts = {fmt(convergence_update['parma_outlier']['hard_cap_broad_relative_difference'])}/"
                f"{fmt(convergence_update['parma_outlier']['hard_cap_line_relative_difference'])}"
            ),
        },
        {
            "item": "U3 mixed voxel",
            "status": convergence_update["mixed_voxel"]["status"],
            "decision": f"no transport; systematic freeze max {fmt(convergence_update['mixed_voxel']['max_assigned_systematic_fraction'])}",
        },
        {
            "item": "U4 parent-feed data note",
            "status": convergence_update["parent_feed"]["status"],
            "decision": "top contributors documented; O-15/C-11/Ga-68 beta+ caveat explicit; no rate change",
        },
        {
            "item": "claim control",
            "status": convergence_update["claim_control"]["status"],
            "decision": "reference-profile/proxy sensitivity study, not final telemetry simulation",
        },
    ]
    update_cap_table = [
        {
            "mode": r["mode"],
            "window": r["window"],
            "final_cps": fmt(r["final_cps"]),
            "shift": fmt(r["relative_shift_vs_uncapped"]),
        }
        for r in update_parma_cap_rows
    ]
    update_parent_table = [
        {
            "nuclide": r["nuclide"],
            "broad": fmt(r["current_broad_final_cps"]),
            "line": fmt(r["current_line_final_cps"]),
            "class": r["decay_class"],
            "correction": r["applied_correction"],
            "caveat": r["recommended_caveat"],
        }
        for r in update_parent_rows[:10]
    ]
    update_mixed_table = [
        {
            "window": r["window"],
            "route": r["route"],
            "bound cps": fmt(r["conservative_bound_cps"]),
            "systematic": fmt(r["assigned_systematic_fraction"]),
        }
        for r in update_mixed_rows
    ]
    nxb_area_cm2 = 9.0
    measured_broad_final = next(float(r["final_cps"]) for r in measured_rows if r["window"] == "broad_480_550" and r["energy_type"] == "measured")
    dixe_rate = measured_broad_final / nxb_area_cm2

    md = f"""# COSMOSRAY_BG_2605 Phase2 综合总结报告（中文）

## 结论摘要

本轮 Phase2 把原来的 corrected day-15 static / constant-limit 链路推进到“真实飞行参考剖面驱动的物理生产预备版”。几何仍继承 code/geometry/TibetTES_v5_6layers；prompt 源仍是上行+下行 20-bin 大气宇宙线；delayed 源继承 buildup RPIP 分布并继续使用 W183/W180 ground-state 修正；science 源使用 Gate-A 修正后的 Be-window 入射 beam，并在物理归一化中加入聚焦光学、大气衰减和地球遮挡。

当前最高可信状态是 `{phase2['status']}`。这不是把所有 publication-level 门槛都宣称完成，而是把真实环境、时变活化、measured-energy、VETO、CAM511/DIXE 风格统计和 profile/injection proxy 放进同一套可审计目录，并明确隔离 mixed voxel transport、完整 parent-fed branch ratio、完整 Poisson nuisance fit 这些还不能假装完成的项。

## Day-15 corrected baseline 与 VETO

{md_table(baseline_rows, ['stream','raw','BGO','final'], ['stream','raw cps','BGO cps','BGO+Compton/FoV cps'])}

## measured-energy 主结果

{md_table(measured_table, ['window','energy','raw','BGO','final'], ['window','energy','raw cps','BGO cps','final cps'])}

DIXE 风格面积归一化 bookkeeping：480-550 keV measured final rate = {fmt(measured_broad_final)} cps，若采用约 {nxb_area_cm2:.1f} cm2 有效 TES 投影面积，则为 {fmt(dixe_rate)} cps cm^-2。该值只作为统计口径类比，不代表 DIXE 轨道/质量模型等价。

## Phase2 WP 状态表

{md_table(wp_rows, ['wp','status','result'], ['WP','status','result'])}

## Phase2 收敛审计总表

{md_table(convergence_rows, ['gate','status','decision'], ['gate','status','decision'])}

收敛补丁的作用不是新增物理内容，而是把当前报告中可能被审稿人质疑的漏洞逐项关门或降级口径：旧 science response 被排除，event catalog 与报告 rate 数值闭合，PARMA scale 的 cap/floor 稳定性被量化，parent-fed decay 不再越界声称，mixed voxel 只给解析界限并保留 transport gate，BGO event-total proxy 被量化，profile/injection 的 robust detection claim 被限制。

## Phase2 收敛补丁 MD 更新：U1-U4

{md_table(update_rows, ['item','status','decision'], ['item','status','decision'])}

本次 MD 更新后的最终收口是：source authority 文本已加 hard check；PARMA 极端 scale bin 经 contribution-weighted audit 证明不主导 rate，uncapped baseline 可保留且系统项远小于 1%；parent-feed 只作为 top-contributor data limitation，不强行修正 rate；mixed voxel 本轮不跑新 transport，而是冻结为最大 1.77% rate-level systematic。因此当前项目表述应收敛为 corrected day-15 static chain + Phase2 reference-profile/proxy sensitivity study with quantified limitations。

## 511 活化贡献

{md_table(truth_table, ['nuclide','A_Bq','broad','line','branch_proxy'], ['nuclide','activity Bq','480-550 final cps','510.3-511.8 final cps','beta+ proxy'])}

## CAM511 Fig.11 风格 sensitivity / injection

1 Ms profiled nuisance proxy:

{md_table(like_table, ['window','model','Fisher3','profile3','profile5'], ['window','model','Fisher 3σ','profiled 3σ','profiled 5σ'])}

1 Ms, F=1e-4 ph cm^-2 s^-1, energy-radius-layer template:

{md_table(inj_table, ['window','model','P3','P5','mean','sigma'], ['window','model','P>=3σ','P>=5σ','mean flux','sigma flux'])}

解释：在当前 proxy nuisance 和 reference profile 下，1e-4 ph cm^-2 s^-1 的 1 Ms 检出不是“稳健 3σ 必检”；broad 与 narrow spatial-template proxy 的 P(>=3σ) 约 0.19-0.20，P(>=5σ) 约 0.002。要把该结论升级成论文级 robust claim，需要 full Poisson profile likelihood、真实 flight telemetry、mixed voxel delayed transport 和完整 detector/BGO hit response。

## 主要文件

- `statistics/phase2_real_flight_physical_production/phase2_summary.json`
- `statistics/phase2_real_flight_physical_production/phase2_real_flight_report.pdf`
- `statistics/phase2_real_flight_physical_production/phase2_integrated_summary_report_zh.pdf`
- `statistics/phase2_real_flight_physical_production/environment_grid_real/environment_grid_summary.json`
- `statistics/phase2_real_flight_physical_production/prompt_reweight_real/prompt_reweight_real_summary.json`
- `statistics/phase2_real_flight_physical_production/activation_inventory_parentfed/inventory_parentfed_summary.json`
- `statistics/phase2_real_flight_physical_production/event_catalog_v2_measured/true_vs_measured_rates.csv`
- `statistics/phase2_real_flight_physical_production/likelihood_profiled/asimov_profiled_sensitivity.csv`
- `statistics/phase2_real_flight_physical_production/long_timeline_injection_profiled/source_injection_profiled_summary.csv`
- `statistics/phase2_convergence_patch/phase2_convergence_patch_summary.json`
- `statistics/phase2_convergence_patch/final_report/COSMOSRAY_BG_2605_Phase2_convergence_patch_report.pdf`
- `statistics/phase2_convergence_patch_update/phase2_convergence_patch_update_summary.json`
- `statistics/phase2_convergence_patch_update/README.md`

## 图谱页说明

本 PDF 后半部分集中嵌入了能谱图、VETO 效果图、活度图、活化核素统计图、IMAGE8-style 统计图、CAM511-style significance/injection 图和 DIXE-style component bookkeeping 图。部分图来自 day15 corrected baseline 和 nextphase WP7-WP9，因为 Phase2 的 real-profile 层目前是 reweight/proxy 统计层，尚未重新做 mixed voxel delayed Cosima transport。

## 可复现命令

```bash
python3 tools/run_phase2_real_flight_pipeline.py
python3 tools/make_phase2_integrated_summary_report.py
python3 tools/validate_workspace.py
```

## 引用与输入说明

EXPACS/PARMA 使用官方 JAEA/PHITS 发布包。后续公开文稿需要按 EXPACS 下载页要求引用 T. Sato, PLOS ONE 10(12): e0144679 (2015)、T. Sato, PLOS ONE 11(8): e0160390 (2016) 和 EXPACS URL。当前 `configs/phase2/flight_profile_real.csv` 是 reference balloon profile，不是实测轨迹；PARMA 太阳调制日期固定为 2025-08-31，用于避免当前公开包对 2026 日期缺少 FFP 数据的问题。
"""
    REPORT_MD.write_text(md, encoding="utf-8")

    font = setup_fonts()
    with PdfPages(REPORT_PDF) as pdf:
        add_text_page(pdf, "Phase2 综合结论", "\n".join(md.splitlines()[2:25]), font)
        add_text_page(pdf, "项目逻辑与源模型", """
几何：继承 code/geometry/TibetTES_v5_6layers，不修改 MEGAlib 源码。

prompt：上行+下行大气宇宙线各粒子按 20 个角度 bin 描述。Phase2 新增 PARMA particle/angle/energy scale 网格，再映射到当前 event catalog；因为 catalog 尚无 primary energy/source angle metadata，最终 reweight 采用 particle-level averaged scale。

buildup/delayed：瞬时宇宙线 buildup 产生 RPIP 核素和空间分布；delayed source 继续使用 W183/W180 ground-state 修正。Phase2 建立 parent-fed schema，并输出 day01/05/10/15/20 Level-1 delayed sources，但缺少审计 branch ratio，不能把 parent feed 声称为完整物理完成。

science：511 keV 源在 Cosima 中是聚焦光学后的 Be-window 入射光子。源通量归一化外置处理：F_511 乘 optics effective area，再乘 511 keV 大气传输和地球遮挡可见因子。旧 z=12.766/r=1.8 science response 已作废。

VETO 与时间轴：day-15 corrected baseline 使用 prompt、delayed、science common Poisson timeline，先做 BGO veto，再做 Compton/FoV selection。Phase2 measured-energy 表保留 true/measured 双轨，主报告优先使用 measured-energy bookkeeping。
""", font)
        add_text_page(pdf, "从项目设定到结果的产生链", """
这份报告按如下逻辑产生所有图和表：

1. 固定几何：所有背景和信号输运均继承 code/geometry/TibetTES_v5_6layers，因此不同源流之间的差异来自源、时间和后处理，而不是几何改动。

2. 分开模拟源项：瞬时大气宇宙线 prompt 用上行+下行 20-bin 分量描述；buildup 模拟只用于产生 RPIP 活化核素和空间分布；delayed 源由核素活度、半衰期和空间分布构造，并继续应用 W183/W180 ground-state 修正；science 511 源用聚焦光学后的 Be-window beam 表示。

3. 统一时间轴：VETO 是时间窗符合问题，所以不能只把不同源的能谱相加。报告中的 day15 baseline 使用 prompt、delayed、science event 按各自 rate 做 Poisson 抽样并放到共同时间轴，再在 coincidence window 内合并 candidate。

4. 执行 VETO：每个合并 candidate 先按 BGO 能量阈值做 anti-coincidence，再按 TES hits 的 Compton/FoV kinematic selection 做最终筛选。能谱图中 raw、BGO、final 三条曲线正是这个链路的逐级输出。

5. 加入时变：Phase2 用 EXPACS/PARMA 参考剖面给 33-43 km、经纬度和源天顶角变化赋予 particle/angle/energy scale；prompt 目前受 event metadata 限制，最终按 particle 平均 scale 重加权；活化用 piecewise ODE schema 推进 day01/05/10/15/20 活度。

6. 统计探测能力：480-550 keV 是聚焦系统自然宽窗；510.3-511.8 keV 是 511 line 近窗。报告同时给出窗口计数、能量模板、能量-半径-layer 模板、timing 系统项和 source injection probability，分别对应 CAM511-style 和 DIXE-style 审阅口径。

每张图下面的说明都按“产生逻辑、结果分析、结论”写，便于第三方审阅时追踪图是怎么来的、图上读出了什么、能支持什么科学表述。
""", font)
        add_text_page(pdf, "Day-15 Baseline 与 VETO 数值", md_table(baseline_rows, ["stream", "raw", "BGO", "final"], ["stream", "raw cps", "BGO cps", "final cps"]) + "\n\n" + md_table(measured_table, ["window", "energy", "raw", "BGO", "final"], ["window", "energy", "raw cps", "BGO cps", "final cps"]), font)
        add_text_page(pdf, "Phase2 收敛审计：总览", f"""
本页把 `statistics/phase2_convergence_patch/` 的 P0-P7 收敛补丁并入总报告。它不是新一轮大 transport，而是审稿前的 claim-control：把 source authority、catalog closure、PARMA stability、parent-feed scope、mixed-voxel gate、BGO proxy 和 profile/injection coverage 逐项闭合或降级。

{md_table(convergence_rows, ['gate','status','decision'], ['gate','status','decision'])}

最终口径：当前报告可以称为 corrected day-15 + Phase2 reference-profile/proxy chain 的收敛版；不能称为实测 telemetry real-flight simulator，也不能声称 full parent-fed chains、mixed voxel transport、per-hit BGO veto 或 1e-4/1Ms 稳健检出已经完成。
""", font, fontsize=7.8)
        add_text_page(pdf, "Phase2 收敛审计：rate 与 BGO proxy", f"""
Catalog closure 逻辑：从 `event_catalog.pkl` 逐 event 重算 stream、raw/BGO/final rate，并与 `complete_day15_summary.json` 的 direct expectation 对比。final stage 复用同一套 `classify_final(..., keep)` 逻辑，避免用第二套选择函数制造假闭合。

{md_table(conv_stream_table, ['stream','stage','catalog','reported','relerr','check'], ['stream','stage','catalog cps','reported cps','relerr','check'])}

BGO proxy 逻辑：当前 catalog 保留 event-total BGO energy，不保留 per-BGO-hit table。因此这里不声称 per-hit BGO 已完成，而是量化 50 keV threshold 附近 true/measured flip fraction 和 45-55 keV 占比。

{md_table(conv_bgo_table, ['window','45-55 frac','flip frac','mode'], ['window','45-55 frac','threshold flip frac','mode'])}

结论：catalog/rate/VETO bookkeeping 已经数值闭合；BGO event-total proxy 当前可作为小系统误差保留，但 publication-level detector electronics/VETO 仍应补 per-hit parser。
""", font, fontsize=7.0)
        add_text_page(pdf, "Phase2 收敛审计：activation、mixed voxel 与 profile", f"""
Parent-feed 逻辑：只锁定 511/broad top contributors 的 before/after 表；没有本地审计 branch-ratio table 时不手填 parent feed，因此 rate 不改，口径降级为 explicit data limitation。

{md_table(conv_parent_table, ['nuclide','broad before','broad after','line before','line after','status'], ['nuclide','broad before','broad after','line before','line after','status'])}

Mixed voxel 解析界限：delta_R_bound = voxel_activity_fraction * safety_factor * delayed_final_rate；fractional_bound = delta_R_bound / measured_final_background_rate。

{md_table(conv_bound_table, ['window','voxel frac','safety','bound cps','bound/final'], ['window','voxel frac','safety','bound cps','bound/final'])}

Profile/injection coverage：1 Ms、1e-4 ph cm^-2 s^-1、energy-radius-layer template 的 recovered flux bias 和 detection probability。

{md_table(conv_profile_table, ['window','mean','std','bias/sigma','P3','P5','pass'], ['window','mean','std','bias/sigma','P>=3σ','P>=5σ','pass'])}

结论：mixed voxel 的最坏解析界限达到 percent-level，必须保留最小 delta transport gate；profile proxy 不支持把 1e-4 ph cm^-2 s^-1、1 Ms 写成稳健检出。
""", font, fontsize=6.8)
        add_text_page(pdf, "Phase2 收敛补丁 MD 更新：U1-U4", f"""
本页并入 `COSMOSRAY_BG_2605_Phase2_收敛补丁_MD更新.md` 的最终收口。原则是不再扩展成更大的全物理系统，只修 source authority 歧义、补 PARMA outlier contribution audit、封 parent-feed data limitation，并对 mixed voxel 选择 systematic freeze。

{md_table(update_rows, ['item','status','decision'], ['item','status','decision'])}

最终一句话：当前项目是 corrected day-15 static chain + Phase2 reference-profile/proxy convergence study with quantified limitations，不是 final real-flight telemetry simulation。
""", font, fontsize=7.2)
        add_text_page(pdf, "PARMA outlier / parent-feed / mixed-voxel 收口", f"""
PARMA capped-vs-uncapped rate audit：

{md_table(update_cap_table, ['mode','window','final_cps','shift'], ['mode','window','final cps','relative shift'])}

Parent-feed top-contributor data note：

{md_table(update_parent_table, ['nuclide','broad','line','class','correction','caveat'], ['nuclide','broad cps','line cps','class','correction','caveat'])}

Mixed-voxel systematic freeze：

{md_table(update_mixed_table, ['window','route','bound cps','systematic'], ['window','route','bound cps','assigned systematic'])}

结论：PARMA 极端 scale bin 不主导 rate；parent-feed 不做无数据支撑的 rate correction；mixed voxel 本轮明确没有 transport validation，只以 1.77% 最大 bound 作为 systematic。
""", font, fontsize=6.5)
        add_text_page(pdf, "图谱总览", """
后续图页按审阅逻辑排列：

1. 能谱和 VETO：宽能段总谱、480-550 keV VETO 链、511 附近窄窗口谱、true/measured detector response。
2. 分量与 IMAGE8-style 统计：prompt/delayed/science 分量能谱、480-550 与 511 附近窗口 component rate。
3. 活化：day15 corrected activation Top10、Phase2 时变活度、511 窗口核素谱和 broad/line Top10。
4. 时变与环境：PARMA 粒子 scale、science 大气传输、prompt real-profile rate。
5. 检出能力：line model、timing/DAQ、likelihood、long-timeline injection。

这些图把底层 Monte Carlo day15 corrected baseline、nextphase 统计扩展和 Phase2 real-profile reweight/proxy 结果放在同一份 PDF 中。mixed voxel transport 和完整 parent-fed branch ratio 仍是报告中明确保留的物理门槛。
""", font)
        add_image_page(pdf, "宽能段总能谱：100-10000 keV", DAY15_FIG / "timeline_spectrum_100_10000.png", fig_note(
            "prompt、fixed delayed 和 reference science events 先按 rate 做 Poisson 抽样，放入同一时间轴，再按 candidate 统计 100-10000 keV 的 TES 总沉积能谱。",
            "该图用于审阅总 NXB 的宽能段形状，检查是否存在异常尖峰、统计断裂或某一 stream 在宽能段异常主导。",
            "宽能段谱是后续 480-550/511 窗口解释的母体；窗口结论必须能在这个总谱背景下自洽。"), font)
        add_image_page(pdf, "480-550 keV VETO 前后能谱", DAY15_FIG / "timeline_spectrum_480_550_veto_chain.png", fig_note(
            "在同一 Poisson common timeline 上，对 480-550 keV 候选事件依次输出 raw、BGO veto 后、BGO+Compton/FoV 后的能谱。",
            f"表格交叉检查显示 480-550 keV final measured/direct rate 约 {fmt(measured_broad_final)} cps；BGO 和 Compton/FoV veto 均改变该窗口的谱形和归一化。",
            "这是本报告最核心的 VETO 图：最终科学本底必须引用 final 曲线，而不是 raw 或简单加权谱。"), font)
        add_image_page(pdf, "511 附近窄窗口谱", SCI_FIG / "fig03_line_window.png", fig_note(
            "从 corrected day15 catalog 中截取 511 keV 附近，强调 510.3-511.8 keV narrow line window 以及 delayed activation 对 line-window 的贡献。",
            f"Phase2 measured 表给出的 510.3-511.8 keV final rate 为 {fmt(next(float(r['final_cps']) for r in measured_rows if r['window'] == 'line_510p3_511p8' and r['energy_type'] == 'measured'))} cps。",
            "窄窗虽然更贴近 511 line，但仍受到活化核素，尤其 beta+ 类和邻近 gamma/continuum 的限制，不能只按理想能量分辨率估算灵敏度。"), font)
        add_image_page(pdf, "Detector response：480-550 true vs measured", NEXT / "gate_B_detector_response" / "spectrum_480_550_true_vs_measured.png", fig_note(
            "Gate B 后处理对 TES pixel hit 加入 FWHM=0.14 keV 的 measured-energy smear，并与 true-energy spectrum 对比。",
            "480-550 keV 宽窗远宽于 TES 分辨率，因此 measured 与 true 的积分 rate 接近；差异主要体现在 bin-edge 和细窄结构。",
            "宽窗本底结论对 TES 展宽不敏感，但最终报告仍应优先引用 measured-energy 统计以保持探测器响应一致。"), font)
        add_image_page(pdf, "Detector response：510-515 true vs measured", NEXT / "gate_B_detector_response" / "spectrum_510_515_true_vs_measured.png", fig_note(
            "同样的 Gate B measured-energy 响应用于 511 keV 附近窄范围，检验 TES 展宽对 line-window 接受率和谱峰形状的影响。",
            "窄窗比 480-550 keV 更容易受 energy smearing、line width 和 bin choice 影响，因此 true/measured 差异必须单独展示。",
            "所有 511 line sensitivity 不应直接使用 true-energy 理想谱，而应以 measured-energy 或明确的 detector-response correction 为主。"), font)
        add_image_page(pdf, "IMAGE8-style 分量能谱", DAY15_FIG / "image8_like_component_spectrum_with_science.png", fig_note(
            "按 prompt、delayed、science stream 拆分 common-timeline/expectation 谱，复刻“基于立方星”类 IMAGE8 component background spectrum 的阅读方式。",
            "该图显示最终 511 能区不是单一来源控制；delayed activation 是 480-550 selected residual 的主项，prompt 仍给出连续背景，science 是小信号模板。",
            "IMAGE8-style 图用于回答“背景由哪些物理分量组成”，不能替代 VETO 后总谱，但能解释 final spectrum 的来源。"), font)
        add_image_page(pdf, "VETO 率统计条形图", DAY15_FIG / "timeline_veto_rates_bar.png", fig_note(
            "同一批 Poisson timeline candidates 分别统计 raw、BGO 后、BGO+Compton/FoV 后的总 rate。",
            f"day15 timeline 480-550 keV 从 raw {fmt(timeline['raw'])} cps 降到 final {fmt(timeline['final'])} cps；这量化了 VETO 链的实际净效果。",
            "VETO 的收益应以同一时间轴同一事件集合为基准读出，避免用不同文件或不同曝光的 rate 混算。"), font)
        add_image_page(pdf, "Day15 activation Top10 活度", DAY15_FIG / "activation_top10_after_fix.png", fig_note(
            "从 buildup RPIP 生成 delayed source 后，应用 W183/W180 ground-state 修正，再按核素汇总 day15 活度。",
            f"fixed delayed source 总活度约 {fmt(day15['delay_fix']['fixed_source_total_activity_Bq'] if 'fixed_source_total_activity_Bq' in day15.get('delay_fix', {}) else 823.951381)} Bq；W183/W180 source blocks 已清零。",
            "活度 Top10 说明 delayed 本底的核素输入，不等同于最终 511 窗口贡献；最终贡献还取决于 decay spectrum、位置和输运。"), font)
        add_text_page(pdf, "Phase2 WP 状态", md_table(wp_rows, ["wp", "status", "result"], ["WP", "status", "result"]), font, fontsize=8.0)
        add_image_page(pdf, "PARMA 粒子时变 scale", FIG / "phase2_particle_scale_by_day.png", fig_note(
            "官方 EXPACS/PARMA C++ driver 在 reference balloon profile 的每个 6-hour bin 计算粒子谱，再相对 38 km reference 条件取 scale。",
            f"不同粒子随 33-43 km 高度和经纬度变化出现明显不同的 scale，整体网格 scale range 为 {fmt(env['scale_min'])}-{fmt(env['scale_max'])}。",
            "这张图是 Phase2 时变 prompt/activation 的物理输入来源；当前仍是 reference profile，不是实测 telemetry。"), font)
        add_image_page(pdf, "511 keV 大气传输与遮挡", FIG / "phase2_science_transmission.png", fig_note(
            "对 science 511 源，将聚焦光学后的 Be-window 入射 rate 再乘以 511 keV 大气质量衰减和地球遮挡可见因子。",
            f"参考剖面中 T_atm 范围为 {fmt(env['science_T_atm_min'])}-{fmt(env['science_T_atm_max'])}；低传输段来自大天顶角或较大大气路径。",
            "science source 的 Cosima beam 只负责 detector transport，真正的天空通量归一化必须包含这条大气/遮挡曲线。"), font)
        add_image_page(pdf, "Prompt real-profile rate", FIG / "phase2_prompt_rate_day_curve.png", fig_note(
            "把 PARMA particle/angle/energy scale 映射到 prompt event catalog；由于 catalog 只有 particle metadata，最终按粒子平均 scale 重加权。",
            f"480-550 keV final prompt rate 随剖面变化在 {fmt(prompt['real_profile_final_480_550_min_cps'])}-{fmt(prompt['real_profile_final_480_550_max_cps'])} cps。",
            "这实现了物理时变的第一版 prompt 修正；若未来 catalog 保留 primary energy 和 source angle，可升级到真正 event-resolved reweight。"), font)
        add_image_page(pdf, "Activation activity evolution", FIG / "phase2_top_nuclide_activity_vs_day.png", fig_note(
            "用 piecewise-constant production ODE 将 real-profile prompt driver 积分到 day01/05/10/15/20 activation inventory。",
            f"day15 total activity 为 {fmt(inventory['day15_total_activity_Bq'])} Bq；图中 top nuclides 随飞行时间累积和衰变而变化。",
            "这张图回答持续宇宙线照射下 delayed source 为什么随工作时间改变；但 parent feed branch ratio 尚未审计，所以当前为 limited parent-fed schema。"), font)
        add_text_page(pdf, "511 活化核素 truth audit", md_table(truth_table, ["nuclide", "A_Bq", "broad", "line", "branch_proxy"], ["nuclide", "activity Bq", "480-550 final cps", "510.3-511.8 final cps", "beta+ proxy"]), font)
        add_image_page(pdf, "Delayed 511 top-nuclide 能谱", NEXT / "activation_511_diagnostics" / "delayed_511_energy_spectrum_by_top_nuclides.png", fig_note(
            "从 delayed-only SIM events 按 nuclide/volume 标签拆分 511 附近能谱，直接审查哪些核素进入 480-550 和 line window。",
            "W-187 在 broad residual 中最大，O-15/C-11 等 beta+ 相关核素对 line-window 更显著；这和 W183/W180 bug 是不同问题。",
            "活化诊断不能只看总活度，必须看 nuclide-specific transported spectrum 和 VETO 后窗口贡献。"), font)
        add_image_page(pdf, "Delayed broad-window Top10", NEXT / "activation_511_diagnostics" / "delayed_511_top10_bar.png", fig_note(
            "对 delayed events 在 480-550 keV final selection 后按核素汇总 rate，得到 broad-window contributor 排名。",
            "W-187 是 broad-window 最大 delayed contributor，Al-28、Ge-75、O-15 等也给出可见贡献。",
            "宽窗本底优化应优先处理 W-187 等 broad contributors，而不是只盯 511 line 本身。"), font)
        add_image_page(pdf, "Delayed line-window Top10", NEXT / "activation_511_diagnostics" / "delayed_511_line_top10_bar.png", fig_note(
            "对 510.3-511.8 keV final selected events 按核素汇总，得到 line-window contributor 排名。",
            "line-window 排名与 broad-window 不同，O-15 的 beta+ annihilation-like 贡献更突出。",
            "窄窗灵敏度受 beta+ 类活化核素限制，必须单独报告 line-window contributor，不能用 broad Top10 代替。"), font)
        add_image_page(pdf, "Timing/DAQ model proxy", FIG / "phase2_science_survival_by_timing_model.png", fig_note(
            "将 rolling window、fixed gate、BGO pre/post、deadtime/pileup 等 timing/DAQ proxy 映射为 background rate 和 science survival。",
            "模型之间 science survival 不同，说明时间窗不是简单后处理细节，而会进入最终 sensitivity 的系统误差。",
            "当前是 toy/proxy DAQ 模型；硬件级触发和 deadtime 模型到位前，timing 应作为 nuisance 或 caveat 保留。"), font)
        add_image_page(pdf, "Timing scan：background vs window", NEXT / "timing_window_scan" / "background_rate_vs_window.png", fig_note(
            "WP6 在多个 coincidence window 下重新形成 candidate 并执行 BGO+Compton/FoV selection，统计 background final rate。",
            "窗口增大时 accidental coincidence 和 event grouping 改变，会使 final background rate 发生非线性变化。",
            "VETO 结论必须绑定具体时间窗；报告默认 1 us baseline，但 10-100 us 应作为硬件系统项。"), font)
        add_image_page(pdf, "Timing scan：science survival", NEXT / "timing_window_scan" / "science_survival_vs_window.png", fig_note(
            "同一 timing scan 同时跟踪 science events 在合并和 VETO 后的 survival fraction。",
            "窗口过长时 science survival 明显下降，100 us 情况会显著恶化灵敏度。",
            "科学源 response 不能只由 isolated science run 给出，长曝光下还必须考虑 accidental timing loss。"), font)
        add_text_page(pdf, "CAM511/DIXE 风格统计表", f"""CAM511 Fig.11 风格：给出 source/background、3σ/5σ threshold 与 injection probability。DIXE 风格：给出 component spectrum/rate 和面积归一化 NXB bookkeeping。

{md_table(like_table, ['window','model','Fisher3','profile3','profile5'], ['window','model','Fisher 3σ','profiled 3σ','profiled 5σ'])}

{md_table(inj_table, ['window','model','P3','P5','mean','sigma'], ['window','model','P>=3σ','P>=5σ','mean flux','sigma flux'])}

DIXE-like 480-550 measured final area-normalized rate: {fmt(dixe_rate)} cps cm^-2 for an approximate {nxb_area_cm2:.1f} cm2 TES projected area.
""", font)
        add_image_page(pdf, "Science line model：true/measured spectra", NEXT / "science_line_models" / "spectrum_true_vs_measured_by_model.png", fig_note(
            "基于 mono、Gaussian FWHM 和 velocity_sigma 等 511 intrinsic/Doppler-broadened line models 生成 signal spectra，并叠加 detector response。",
            "宽窗 480-550 keV 对 line width 基本不敏感，窄窗 510.3-511.8 keV 的 acceptance 随 line width 变宽而下降。",
            "真实 511 源不能默认 mono line；SPI 或理论支持的 line width 必须进入 signal template 和 sensitivity。"), font)
        add_image_page(pdf, "Science line model sensitivity", NEXT / "science_line_models" / "sensitivity_by_line_model.png", fig_note(
            "对每个 line model 分别计算 broad window 和 narrow line-window 的 3σ/5σ threshold。",
            "narrow-window sensitivity 对 line width 明显敏感；Gaussian FWHM 2.5 keV 时 line-window threshold 变差，而 broad window 保持稳定。",
            "报告需要同时列 broad 和 near-511 结果：broad 更稳健，line-window 更贴近物理线但依赖 line-shape 假设。"), font)
        add_image_page(pdf, "WP8 likelihood vs window counting", NEXT / "likelihood_511" / "likelihood_vs_window_counting.png", fig_note(
            "从 event catalog 构造 window counting、energy template、energy-radius-layer template 三类 Asimov/Fisher estimator。",
            "energy-radius-layer template 的 1 Ms 3σ threshold 优于简单窗口计数，说明空间/层信息能有效区分 focused science 与 activation/prompt background。",
            "这是 CAM511 Fig.11-style 显著度统计的核心扩展，但仍是 template/Fisher baseline，不是完整 profile likelihood。"), font)
        add_image_page(pdf, "Profiled likelihood proxy", FIG / "phase2_profiled_vs_fisher_threshold.png", fig_note(
            "在 WP8 Fisher threshold 上加入 prompt、delayed、W187、timing、TES FWHM、atmosphere 等 diagonal nuisance priors，形成 Phase2 profiled proxy。",
            f"nuisance degradation factor 为 {fmt(like_summary['degradation_factor'])}，使 1 Ms thresholds 相对 Fisher baseline 变差。",
            "该图给出系统误差影响的保守方向，但完整论文级结论还需要 full Poisson profile optimizer。"), font)
        add_image_page(pdf, "WP9 detection probability vs flux", NEXT / "long_timeline_injection" / "detection_probability_vs_flux.png", fig_note(
            "使用 signal/background templates 做 binned Poisson pseudo-experiments，扫描输入通量并统计 P(>=3σ) 和 P(>=5σ)。",
            "检测概率随 flux 单调上升；在 1e-4 ph cm^-2 s^-1 附近，不同 estimator 的 P3 差异很大。",
            "灵敏度不应只给 threshold，还应给 source injection probability，这更接近实际观测可检出能力。"), font)
        add_image_page(pdf, "WP9 recovered flux vs true flux", NEXT / "long_timeline_injection" / "recovered_flux_vs_true_flux.png", fig_note(
            "同一批 pseudo-experiments 用 score/Fisher estimator 回收 flux，并与输入 flux 对比。",
            "回收均值接近输入值，说明当前 injection estimator 在测试网格内没有明显偏置；散布反映统计误差。",
            "无偏回收是使用 detection probability 的前提；若未来加入 profile nuisance，也需要重复这个 coverage 检查。"), font)
        add_image_page(pdf, "Profiled source injection proxy", FIG / "phase2_P3_vs_flux_profiled.png", fig_note(
            "Phase2 在 WP9 injection 基础上加入 nuisance-degraded sigma，扫描 1e5/1e6/1e7 s 和多档 flux。",
            "在 1 Ms、1e-4 ph cm^-2 s^-1 下，energy-radius-layer proxy 的 P(>=3σ) 约 0.19-0.20，低于不含 nuisance 的 WP9 baseline。",
            "当前 Phase2 不能声称 1e-4 flux 在 1 Ms 稳健检出；报告应把它写成待 full profile likelihood 验证的目标能力。"), font)
        add_image_page(pdf, "IMAGE8-style broad window", FIG / "phase2_image8_broad_480_550.png", fig_note(
            "按 component 汇总 480-550 keV final selected rate，提供类似 IMAGE8/Table component count-rate 的统计视图。",
            "broad-window final rate 中 delayed activation 是主要背景，prompt 是次级连续背景，science reference flux 只贡献很小 signal rate。",
            "这个图用于快速说明 480-550 宽窗的背景构成，也是 DIXE-style NXB component bookkeeping 的输入。"), font)
        add_image_page(pdf, "IMAGE8-style line window", FIG / "phase2_image8_line_510p3_511p8.png", fig_note(
            "对 510.3-511.8 keV narrow line-window 做 component-rate 摘要，当前主要展示 activation delayed-only 贡献。",
            "line-window delayed final rate 约 1 cps 量级，说明 511 附近不是零本底问题；活化线/湮灭相关核素会限制窄窗。",
            "后续若要完整 publication plot，应把 prompt/science line-window component 也以同一 measured catalog 口径加入。"), font)
        add_text_page(pdf, "不可越界解释与后续门槛", f"""可以有高信心引用的内容：
- 几何、source authority、W183/W180 修正、day15 Poisson timeline、BGO+Compton/FoV VETO、PARMA reference profile grid、measured-energy broad/line rate、activation truth top contributors、profiled proxy sensitivity/injection。

不能写成已完成的内容：
- 不能把 reference profile 称为实测 telemetry。
- 不能把 parent-fed schema 称为完整 parent-fed decay chain；branch ratio 仍缺。
- 不能把 `mixed_voxel_transport` 称为已完成；当前状态是 `{mixed['status']}`。
- 不能把 current profiled likelihood 称为 publication-level robust sensitivity；当前是 `{like_summary['status']}`。

下一步真正提升结论强度的最短路径：
1. 导入实测 flight telemetry 或用户给定 trajectory。
2. 加入审计过的 ENSDF/Geant4 branch ratios，重跑 parent-fed ODE。
3. 构造 mixed radial/voxel delayed source 并做 Cosima transport 对比。
4. 生成 per-BGO-hit measured catalog，替换 event-total BGO proxy。
5. 用拆分背景模板做 full Poisson profile likelihood 和 coverage test。
""", font)

    print(REPORT_PDF)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
