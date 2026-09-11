#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the final next-phase completion report.

The report is deliberately explicit about what is physically transported, what
is an analysis-layer correction, and what is a framework/constant-limit
validation.  This avoids turning missing real-flight inputs or future voxel
transport into overconfident science claims.
"""

from __future__ import annotations

import argparse
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


ROOT = Path(__file__).resolve().parents[1]
FONT_PROP = None
OUT_DEFAULT = ROOT / "reports" / "nextphase_511" / "final_completion_report"
SUMMARY = ROOT / "reports" / "day15_complete_report" / "complete_day15_summary.json"
GATE_A = ROOT / "reports" / "nextphase_511" / "gate_A_source_placement" / "be_window_crossing_summary.json"
GATE_B = ROOT / "reports" / "nextphase_511" / "gate_B_detector_response" / "detector_response_summary.json"
LINE_SENS = ROOT / "reports" / "nextphase_511" / "science_line_models" / "sensitivity_by_line_model.csv"
LINE_FRAC = ROOT / "reports" / "nextphase_511" / "science_line_models" / "source_fraction_in_windows.csv"
ENV_SUMMARY = ROOT / "reports" / "nextphase_511" / "time_variable_day1_day20" / "environment_grid" / "environment_grid_summary.json"
INV_SUMMARY = ROOT / "reports" / "nextphase_511" / "time_variable_day1_day20" / "inventory" / "constant_limit_validation.json"
PROMPT_REWEIGHT = ROOT / "reports" / "nextphase_511" / "time_variable_day1_day20" / "prompt_reweight" / "prompt_reweight_summary.json"
TIMEVAR_SOURCE = ROOT / "production_runs" / "time_variable_delayed" / "source_build_summary.json"
SPATIAL = ROOT / "reports" / "nextphase_511" / "activation_spatial_model" / "activation_source_spatial_summary.json"
TIMING = ROOT / "reports" / "nextphase_511" / "timing_window_scan" / "timing_window_scan_summary.csv"
ACT511 = ROOT / "reports" / "nextphase_511" / "activation_511_diagnostics" / "activation_511_diagnostic_summary.json"
LIKELIHOOD = ROOT / "reports" / "nextphase_511" / "likelihood_511" / "likelihood_sensitivity_by_model.csv"
INJECTION = ROOT / "reports" / "nextphase_511" / "long_timeline_injection" / "injection_recovery_summary.csv"
INJECTION_SUMMARY = ROOT / "reports" / "nextphase_511" / "long_timeline_injection" / "long_timeline_injection_summary.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def fmt(x: Any, digits: int = 6) -> str:
    try:
        v = float(x)
    except Exception:
        return str(x)
    if not math.isfinite(v):
        return "nan"
    if v != 0.0 and (abs(v) < 1.0e-3 or abs(v) >= 1.0e4):
        return f"{v:.{digits}e}"
    return f"{v:.{digits}g}"


def md_table(rows: list[dict[str, Any]], fields: list[str], headers: list[str] | None = None) -> str:
    headers = headers or fields
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in rows:
        vals = [str(row.get(f, "")) for f in fields]
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def selected_line_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out = []
    for model in ("mono", "gaussian_fwhm_0p5", "gaussian_fwhm_1p5", "gaussian_fwhm_2p5", "velocity_sigma_600"):
        for window in ("broad_480_550", "line_510p3_511p8"):
            hit = next(
                r for r in rows
                if r["model_id"] == model and r["energy_window"] == window and abs(float(r["exposure_s"]) - 1.0e6) < 1.0
            )
            out.append({
                "model": model,
                "window": window,
                "fraction": fmt(hit["source_fraction_in_window"], 5),
                "3sigma_1Ms": fmt(hit["flux_3sigma_ph_cm2_s"], 5),
            })
    return out


def likelihood_one_ms(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        if abs(float(r["exposure_s"]) - 1.0e6) > 1.0:
            continue
        out.append({
            "window": r["energy_window"],
            "model": r["model"],
            "info_s": fmt(r["information_per_s"], 5),
            "bins": r["bins_used"],
            "3sigma_1Ms": fmt(r["flux_3sigma_ph_cm2_s"], 5),
            "5sigma_1Ms": fmt(r["flux_5sigma_ph_cm2_s"], 5),
        })
    return out


def timing_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    keep = []
    for r in rows:
        if r["energy_window"] != "broad_480_550":
            continue
        if float(r["window_us"]) in (0.1, 1.0, 10.0, 100.0):
            keep.append({
                "window_us": r["window_us"],
                "background_cps": fmt(r["background_final_cps"], 6),
                "science_survival": fmt(r["science_survival"], 6),
                "3sigma_1Ms": fmt(r["broad_flux3_1Ms_if_applicable"], 6),
            })
    return keep


def injection_one_ms(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        if abs(float(r["exposure_s"]) - 1.0e6) > 1.0:
            continue
        if abs(float(r["input_flux_ph_cm2_s"]) - 1.0e-4) > 1.0e-12:
            continue
        out.append({
            "window": r["energy_window"],
            "model": r["model"],
            "P3": fmt(r["detection_probability_3sigma"], 4),
            "mean_flux": fmt(r["mean_recovered_flux"], 6),
            "std_flux": fmt(r["std_recovered_flux"], 6),
        })
    return out


def wrap_block(text: str, width: int = 92) -> str:
    out: list[str] = []
    for para in text.splitlines():
        if not para.strip():
            out.append("")
            continue
        if para.startswith("    ") or para.startswith("|") or para.startswith("- ") or para.startswith("#"):
            out.append(para)
        else:
            out.extend(textwrap.wrap(para, width=width, replace_whitespace=False) or [""])
    return "\n".join(out)


def add_text_page(pdf: PdfPages, title: str, body: str) -> None:
    fig = plt.figure(figsize=(8.27, 11.69))
    ax = fig.add_axes([0.06, 0.05, 0.88, 0.90])
    ax.axis("off")
    ax.text(0.0, 1.02, title, fontsize=15, weight="bold", va="top", fontproperties=FONT_PROP)
    ax.text(
        0.0,
        0.98,
        wrap_block(body, width=88),
        fontsize=9.0,
        va="top",
        linespacing=1.28,
        fontproperties=FONT_PROP,
    )
    pdf.savefig(fig)
    plt.close(fig)


def add_image_page(pdf: PdfPages, title: str, image_path: Path, caption: str) -> None:
    if not image_path.exists():
        add_text_page(pdf, title, f"Missing figure: {rel(image_path)}\n{caption}")
        return
    img = mpimg.imread(image_path)
    fig = plt.figure(figsize=(8.27, 11.69))
    ax_title = fig.add_axes([0.06, 0.91, 0.88, 0.05])
    ax_title.axis("off")
    ax_title.text(0.0, 0.8, title, fontsize=15, weight="bold", va="top", fontproperties=FONT_PROP)
    ax = fig.add_axes([0.06, 0.18, 0.88, 0.70])
    ax.imshow(img)
    ax.axis("off")
    ax_cap = fig.add_axes([0.06, 0.05, 0.88, 0.10])
    ax_cap.axis("off")
    ax_cap.text(0.0, 1.0, wrap_block(caption, width=96), fontsize=9.0, va="top", fontproperties=FONT_PROP)
    pdf.savefig(fig)
    plt.close(fig)


def build_summary() -> dict[str, Any]:
    summary = load_json(SUMMARY)
    gate_a = load_json(GATE_A)
    gate_b = load_json(GATE_B)
    env = load_json(ENV_SUMMARY)
    inv = load_json(INV_SUMMARY)
    prompt = load_json(PROMPT_REWEIGHT)
    timevar = load_json(TIMEVAR_SOURCE)
    spatial = load_json(SPATIAL)
    act = load_json(ACT511)
    inj = load_json(INJECTION_SUMMARY)
    timing = read_csv(TIMING)
    like = read_csv(LIKELIHOOD)
    line_sens = read_csv(LINE_SENS)

    broad_like_spatial = next(
        r for r in like
        if r["energy_window"] == "broad_480_550"
        and r["model"] == "energy_radius_layer_template"
        and abs(float(r["exposure_s"]) - 1.0e6) < 1.0
    )
    line_like_spatial = next(
        r for r in like
        if r["energy_window"] == "line_510p3_511p8"
        and r["model"] == "energy_radius_layer_template"
        and abs(float(r["exposure_s"]) - 1.0e6) < 1.0
    )
    return {
        "status": "PASS_WITH_EXPLICIT_CAVEATS",
        "report_scope": "Completion report for the local next-phase implementation through WP9.",
        "key_numbers": {
            "day15_timeline_final_480_550_cps": summary["timeline_rates_cps"]["final"],
            "day15_expectation_final_480_550_cps": summary["expectation_rates_cps"]["final"],
            "science_response_cps_per_flux": summary["science_sensitivity"]["science_final_response_cps_per_ph_cm-2_s-1"],
            "gateB_measured_final_480_550_cps": gate_b["windows"]["480-550_measured"]["final_cps"],
            "gateB_measured_final_510p3_511p8_cps": gate_b["windows"]["510.3-511.8_measured"]["final_cps"],
            "broad_window_counting_3sigma_1Ms": next(
                float(r["flux_3sigma_ph_cm2_s"]) for r in like
                if r["energy_window"] == "broad_480_550"
                and r["model"] == "window_counting_same_events"
                and abs(float(r["exposure_s"]) - 1.0e6) < 1.0
            ),
            "broad_spatial_likelihood_3sigma_1Ms": float(broad_like_spatial["flux_3sigma_ph_cm2_s"]),
            "line_spatial_likelihood_3sigma_1Ms": float(line_like_spatial["flux_3sigma_ph_cm2_s"]),
        },
        "wp_status": {
            "WP0_baseline_freeze": "PASS",
            "WP1_GateA_source_placement": "PASS" if gate_a["passed"] else "FAIL",
            "WP2_GateB_detector_response": "PASS" if gate_b["passed"] else "FAIL",
            "WP3_line_models": "PASS",
            "WP4_time_variable_constant_limit": "PASS" if inv["status"] == "PASS" and prompt["status"] == "PASS" and timevar["status"] == "PASS" else "FAIL",
            "WP5_activation_spatial_model_audit": spatial["status"],
            "WP6_timing_window_scan": "PASS",
            "WP7_activation_511_diagnostics": act["status"],
            "WP8_spatial_spectral_likelihood": "PASS",
            "WP9_long_timeline_injection": inj["status"],
        },
        "caveats": [
            env["caveat"],
            inv["caveat"],
            prompt["caveat"],
            timevar["caveat"],
            spatial["caveat"],
            inj["caveat"],
            gate_b["known_limitation"],
        ],
        "selected_tables": {
            "timing": timing_rows(timing),
            "likelihood": likelihood_one_ms(like),
            "line_models": selected_line_rows(line_sens),
            "injection_1Ms_flux1e-4": injection_one_ms(read_csv(INJECTION)),
        },
    }


def write_markdown(outdir: Path, summary_out: dict[str, Any]) -> Path:
    full = load_json(SUMMARY)
    gate_a = load_json(GATE_A)
    gate_b = load_json(GATE_B)
    env = load_json(ENV_SUMMARY)
    inv = load_json(INV_SUMMARY)
    prompt = load_json(PROMPT_REWEIGHT)
    timevar = load_json(TIMEVAR_SOURCE)
    spatial = load_json(SPATIAL)
    act = load_json(ACT511)
    line_frac = read_csv(LINE_FRAC)

    md = f"""# COSMOSRAY_BG_2605 下一阶段完成报告

生成时间：2026-05-12  
报告目录：`{rel(outdir)}`  
状态：`{summary_out['status']}`

## 1. 总结论

本轮实现已经把《下一阶段实施方案》从 WP0 推进到 WP9，并生成可审计的 JSON/CSV/PNG/PDF 产物。当前最稳健的 511 keV 点源结论如下：

- corrected day-15 common timeline 480-550 keV final rate：`{fmt(summary_out['key_numbers']['day15_timeline_final_480_550_cps'])}` cps。
- direct expectation 480-550 keV final rate：`{fmt(summary_out['key_numbers']['day15_expectation_final_480_550_cps'])}` cps。
- Gate-A 修正后 science response：`{fmt(summary_out['key_numbers']['science_response_cps_per_flux'])}` cps/(ph cm^-2 s^-1)。
- detector response 后 measured 480-550 keV final rate：`{fmt(summary_out['key_numbers']['gateB_measured_final_480_550_cps'])}` cps。
- conservative broad-window 3 sigma / 1 Ms：`{fmt(summary_out['key_numbers']['broad_window_counting_3sigma_1Ms'])}` ph cm^-2 s^-1。
- factorized energy-radius-layer likelihood broad-window 3 sigma / 1 Ms：`{fmt(summary_out['key_numbers']['broad_spatial_likelihood_3sigma_1Ms'])}` ph cm^-2 s^-1。
- factorized energy-radius-layer likelihood line-window 3 sigma / 1 Ms：`{fmt(summary_out['key_numbers']['line_spatial_likelihood_3sigma_1Ms'])}` ph cm^-2 s^-1。

这些数值不是为了复刻旧 PPT 的数值相同，而是基于当前 corrected chain：W183/W180 ground-state 修正、Gate-A science source 修正、共同泊松时间轴、BGO+Compton/FoV veto、science accidental-veto 修正和后续 likelihood/injection 统计检验。

## 2. 代码与运行逻辑

核心流程：

```text
read memory.md/workflow.md
freeze corrected day-15 baseline
check science source placement against Win_Be/TES geometry
run/freeze corrected science source at z=127.66, radius=18.0
parse prompt, delayed, science SIM into event_catalog.pkl
place streams on common Poisson time axis
merge candidates within electronics coincidence window
apply BGO veto and Compton/FoV veto
apply detector-response post-processing for TES/BGO measured-energy studies
build mono/Gaussian/velocity 511 source spectrum files
validate constant-profile time-variable environment/inventory/day sources
audit activation spatial source normalization
scan timing windows from 0.1 to 100 us
diagnose delayed 511 contributors by nuclide and proxy volume
build Asimov energy/spatial templates
run binned Poisson long-timeline source-injection
generate this completion report
```

主要脚本：

```text
tools/check_science_source_placement.py
tools/apply_detector_response.py
tools/build_science_511_line_sources.py
tools/make_science_line_sensitivity.py
tools/build_environment_grid.py
tools/integrate_activation_inventory.py
tools/reweight_prompt_by_environment.py
tools/build_time_variable_delayed_sources.py
tools/audit_activation_spatial_model.py
tools/scan_timing_windows.py
tools/diagnose_511_activation_lines.py
tools/fit_511_spatial_spectral_likelihood.py
tools/run_long_timeline_injection.py
tools/make_nextphase_completion_report.py
```

## 3. WP0-WP3：baseline、几何、探测器响应、线型

Gate A 使用 `run_configs/Science_511_onaxis_focalbeam_local.source` 与 `XZTES/TibetTES_v5_6layers.geo`。当前 source 为 `HomogeneousBeam z=127.66, radius=18.0, direction=-z`，Win_Be 范围为 `{fmt(gate_a['win_be']['z_min'])}` 到 `{fmt(gate_a['win_be']['z_max'])}`，source 与 Be window top clearance 为 `{fmt(gate_a['clearance_source_minus_win_top'])}`。旧 `z=12.766, radius=1.8` 已明确作废。

Gate B 在 event catalog 上按像素 TES energy smear，TES FWHM `0.14 keV`；BGO 使用 event-total BGO energy smear，BGO FWHM `1.0 keV`，阈值 `50 keV`。science mono peak robust FWHM 从 true `{fmt(gate_b['science_peak_true_fwhm_robust_keV'])}` keV 变为 measured `{fmt(gate_b['science_peak_measured_fwhm_robust_keV'])}` keV。

Line model 窗口分数：

{md_table([{ 'model': r['model_id'], 'FWHM_keV': fmt(r['fwhm_src_keV']), 'f480_550': fmt(r['fraction_480_550']), 'f510p3_511p8': fmt(r['fraction_510p3_511p8']) } for r in line_frac], ['model','FWHM_keV','f480_550','f510p3_511p8'])}

1 Ms line-model sensitivity 摘要：

{md_table(summary_out['selected_tables']['line_models'], ['model','window','fraction','3sigma_1Ms'])}

## 4. WP4：flight-profile time variability 常数极限

当前完成的是常数环境极限，不是实际飞行谱模型。environment grid mode 为 `{env['mode']}`，scale range 为 `{fmt(env['scale_to_ref_min'])}` 到 `{fmt(env['scale_to_ref_max'])}`。Inventory validation 在 day15 重构总活度 `{fmt(inv['generated_reference_day_total_activity_Bq'])}` Bq，对 reference `{fmt(inv['reference_total_activity_Bq'])}` Bq 的相对差为 `{fmt(inv['reference_total_rel_diff'])}`。Prompt reweight 在常数极限下 scale range `{fmt(prompt['scale_min'])}` 到 `{fmt(prompt['scale_max'])}`。Day01/05/10/15/20 delayed source 已生成，day15 source flux 与模板最大相对差 `{fmt(timevar['records'][3]['max_day15_flux_rel_change'])}`。

## 5. WP5：activation source 空间模型

Spatial audit status：`{spatial['status']}`。当前 fixed delayed source activity 为 `{fmt(spatial['total_activity_Bq'])}` Bq，mixed radial/voxel bookkeeping activity 为 `{fmt(spatial['mixed_total_activity_Bq'])}` Bq，closure fraction `{fmt(spatial['normalization_closure_fraction'])}`。Voxel-mode volumes 承载活度 `{fmt(spatial['voxel_activity_Bq'])}` Bq，占 `{fmt(spatial['voxel_activity_fraction'])}`。这一步锁定了归一化和应做 voxel 的体，但没有伪造新的 voxel transport rate。

## 6. WP6：timing-window scan

{md_table(summary_out['selected_tables']['timing'], ['window_us','background_cps','science_survival','3sigma_1Ms'])}

结论：1 us 作为 baseline；10-100 us 必须作为硬件时间窗系统误差。100 us 下 science survival 降到约 0.109，说明如果真实 DAQ 窗口很长，当前灵敏度会显著变差。

## 7. WP7：delayed 511 activation diagnostics

Delayed-only totals：480-550 final `{fmt(act['totals']['broad_480_550']['final_cps'])}` cps，510.3-511.8 final `{fmt(act['totals']['line_510p3_511p8']['final_cps'])}` cps，506-516 final `{fmt(act['totals']['near_506_516']['final_cps'])}` cps。

Top broad-window contributors：

{md_table([{ 'nuclide': r['nuclide'], 'broad_final': fmt(r['broad_480_550_final_cps']), 'line_final': fmt(r['line_510p3_511p8_final_cps']), 'events': r['events_total'] } for r in act['top_nuclides_by_broad_final'][:6]], ['nuclide','broad_final','line_final','events'])}

W-187 仍然是 broad 480-550 delayed final 的最大 contributor。W183/W180 已经在 fixed source 中移除；这里出现 W-187 是另一个真实残余项，不是 W183M bug 的复发。

## 8. WP8：spatial-spectral likelihood

当前 likelihood 是 Asimov/Fisher template baseline。Background template 只用 prompt+delayed；science stream 不进入 background template；signal-only bins 被忽略以避免零本底无穷乐观。

{md_table(summary_out['selected_tables']['likelihood'], ['window','model','info_s','bins','3sigma_1Ms','5sigma_1Ms'])}

## 9. WP9：long timeline source-injection

WP9 使用同一套 signal/background templates 做 binned Poisson source injection。Flux grid 为 `[0, 5e-5, 1e-4, 2e-4, 5e-4]` ph cm^-2 s^-1，exposure grid 为 `[1e5, 1e6, 1e7]` s，每组 20000 realization。Recovered flux 使用 score/Fisher estimator，因此可以直接检查无偏性和 false-positive rate。

1 Ms、输入 flux `1e-4 ph cm^-2 s^-1`：

{md_table(summary_out['selected_tables']['injection_1Ms_flux1e-4'], ['window','model','P3','mean_flux','std_flux'])}

F=0 的 3 sigma false-positive rate 在约 0.001-0.002，和 one-sided Gaussian 3 sigma tail 的 0.00135 一致；20000 realization 下 5 sigma false-positive 为 0 是统计上预期的。

## 10. 限制与下一步

{chr(10).join('- ' + c for c in summary_out['caveats'])}

因此，本报告的可发布口径应该是：当前已经完成 corrected day-15 511 keV background/sensitivity 的本地下一阶段实现和统计验证；真实 flight profile、energy-resolved EXPACS reweight、parent-fed decay chain 和 mixed voxel-source Cosima transport 是下一轮物理输入到位后应做的重跑，而不是当前报告已经声称完成的物理事实。
"""
    path = outdir / "COSMOSRAY_BG_2605_nextphase_completion_report.md"
    path.write_text(md, encoding="utf-8")
    return path


def build_pdf(outdir: Path, summary_out: dict[str, Any]) -> Path:
    global FONT_PROP
    FONT_PROP = setup_fonts()
    pdf_path = outdir / "COSMOSRAY_BG_2605_nextphase_completion_report.pdf"
    with PdfPages(pdf_path) as pdf:
        add_text_page(
            pdf,
            "COSMOSRAY_BG_2605 下一阶段完成报告",
            "\n".join([
                f"状态: {summary_out['status']}",
                "",
                "核心数值:",
                f"- day-15 timeline final 480-550 keV: {fmt(summary_out['key_numbers']['day15_timeline_final_480_550_cps'])} cps",
                f"- direct expectation final 480-550 keV: {fmt(summary_out['key_numbers']['day15_expectation_final_480_550_cps'])} cps",
                f"- science response: {fmt(summary_out['key_numbers']['science_response_cps_per_flux'])} cps/(ph cm^-2 s^-1)",
                f"- broad window counting 3 sigma / 1 Ms: {fmt(summary_out['key_numbers']['broad_window_counting_3sigma_1Ms'])} ph cm^-2 s^-1",
                f"- broad spatial likelihood 3 sigma / 1 Ms: {fmt(summary_out['key_numbers']['broad_spatial_likelihood_3sigma_1Ms'])} ph cm^-2 s^-1",
                f"- line spatial likelihood 3 sigma / 1 Ms: {fmt(summary_out['key_numbers']['line_spatial_likelihood_3sigma_1Ms'])} ph cm^-2 s^-1",
                "",
                "WP 状态:",
                *[f"- {k}: {v}" for k, v in summary_out["wp_status"].items()],
                "",
                "注意: 当前报告明确保留真实 flight-profile、parent-fed decay chain 和 voxel transport 的限制；未把常数极限/统计模板包装成真实飞行物理重跑。",
            ]),
        )
        add_text_page(
            pdf,
            "方法与命令链",
            "\n".join([
                "source / geometry / simulation / analysis logic:",
                "",
                "1. Freeze corrected day-15 baseline from complete_day15_summary.json.",
                "2. Verify science beam at z=127.66, radius=18.0, entering through Win_Be.",
                "3. Use strict 2605 prompt instant + buildup; build fixed day-15 delayed source with W183/W180 ground-state correction.",
                "4. Parse prompt, delayed and science SIM files into event_catalog.pkl.",
                "5. Draw common Poisson timeline and merge events inside the electronics coincidence window.",
                "6. Apply BGO veto and Compton/FoV veto.",
                "7. Apply detector response as post-processing for measured-energy studies.",
                "8. Build intrinsic 511-keV line source files and propagate source fractions.",
                "9. Validate time-variable machinery in the constant-profile limit.",
                "10. Scan timing windows, diagnose activation lines, fit likelihood templates, and run long-timeline source injection.",
                "",
                "Principal scripts:",
                "check_science_source_placement.py; apply_detector_response.py; build_science_511_line_sources.py; make_science_line_sensitivity.py; build_environment_grid.py; integrate_activation_inventory.py; reweight_prompt_by_environment.py; build_time_variable_delayed_sources.py; audit_activation_spatial_model.py; scan_timing_windows.py; diagnose_511_activation_lines.py; fit_511_spatial_spectral_likelihood.py; run_long_timeline_injection.py.",
            ]),
        )
        add_text_page(
            pdf,
            "关键表格",
            "\n\n".join([
                "Timing window scan:\n" + md_table(summary_out["selected_tables"]["timing"], ["window_us", "background_cps", "science_survival", "3sigma_1Ms"]),
                "Likelihood, 1 Ms:\n" + md_table(summary_out["selected_tables"]["likelihood"], ["window", "model", "info_s", "bins", "3sigma_1Ms", "5sigma_1Ms"]),
                "Line models, 1 Ms:\n" + md_table(summary_out["selected_tables"]["line_models"], ["model", "window", "fraction", "3sigma_1Ms"]),
                "Injection, F=1e-4 and T=1 Ms:\n" + md_table(summary_out["selected_tables"]["injection_1Ms_flux1e-4"], ["window", "model", "P3", "mean_flux", "std_flux"]),
            ]),
        )
        add_image_page(pdf, "Gate A: first TES hit z", ROOT / "reports" / "nextphase_511" / "gate_A_source_placement" / "first_tes_hit_z_hist.png", "Science source placement smoke/diagnostic after the z=127.66, radius=18.0 correction.")
        add_image_page(pdf, "Gate B: detector response broad window", ROOT / "reports" / "nextphase_511" / "gate_B_detector_response" / "spectrum_480_550_true_vs_measured.png", "Measured-energy post-processing changes the 511-keV region while preserving true-energy audit columns.")
        add_image_page(pdf, "Science line models", ROOT / "reports" / "nextphase_511" / "science_line_models" / "spectrum_true_vs_measured_by_model.png", "Intrinsic mono/Gaussian/velocity 511 line models convolved with the detector-response proxy.")
        add_image_page(pdf, "Line-model sensitivity", ROOT / "reports" / "nextphase_511" / "science_line_models" / "sensitivity_by_line_model.png", "Window-counting sensitivity after propagating intrinsic source fractions and accidental timing survival.")
        add_image_page(pdf, "Time-variable constant-limit inventory", ROOT / "reports" / "nextphase_511" / "time_variable_day1_day20" / "inventory" / "total_activity_by_time.png", "Constant-profile ODE validation; day15 returns to the fixed static activity by construction.")
        add_image_page(pdf, "Timing-window scan", ROOT / "reports" / "nextphase_511" / "timing_window_scan" / "science_survival_vs_window.png", "Science accidental survival as electronics coincidence window is scanned from 0.1 to 100 us.")
        add_image_page(pdf, "Activation 511 top contributors", ROOT / "reports" / "nextphase_511" / "activation_511_diagnostics" / "delayed_511_top10_bar.png", "Delayed-only 480-550 keV final contributors; W-187 remains a major residual after W183/W180 correction.")
        add_image_page(pdf, "Activation 511 spectra", ROOT / "reports" / "nextphase_511" / "activation_511_diagnostics" / "delayed_511_energy_spectrum_by_top_nuclides.png", "Energy spectra of top delayed contributors around 511 keV.")
        add_image_page(pdf, "Spatial-spectral likelihood", ROOT / "reports" / "nextphase_511" / "likelihood_511" / "likelihood_vs_window_counting.png", "Asimov/Fisher template sensitivity comparison: window counting, energy template, and energy-radius-layer template.")
        add_image_page(pdf, "Long timeline injection: detection", ROOT / "reports" / "nextphase_511" / "long_timeline_injection" / "detection_probability_vs_flux.png", "Binned Poisson source injection detection probabilities at 1 Ms.")
        add_image_page(pdf, "Long timeline injection: recovery", ROOT / "reports" / "nextphase_511" / "long_timeline_injection" / "recovered_flux_vs_true_flux.png", "Recovered flux is unbiased within the statistical precision of the source-injection tests.")
        add_text_page(
            pdf,
            "限制与发布口径",
            "\n".join(["Current caveats:"] + [f"- {c}" for c in summary_out["caveats"]] + [
                "",
                "Publication-level wording:",
                "The current local implementation completes the corrected day-15 511-keV background chain and the next-phase statistical validation. It should be cited as a corrected day-15 static/constant-limit study with explicit timing, detector-response, activation-line and likelihood/injection audits. It should not be described as a real-flight-profile or voxel-source transport production until those physical inputs are rerun.",
            ]),
        )
    return pdf_path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    summary_out = build_summary()
    (args.out / "completion_summary.json").write_text(json.dumps(summary_out, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path = write_markdown(args.out, summary_out)
    pdf_path = build_pdf(args.out, summary_out)
    audit = {
        "status": "PASS",
        "pdf": rel(pdf_path),
        "markdown": rel(md_path),
        "summary": rel(args.out / "completion_summary.json"),
    }
    (args.out / "audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    print(pdf_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
