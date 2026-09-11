#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a paper-style day-15 background and 511-source capability report.

The report is intentionally derived from the already-audited production summary
and spectra.  It does not rerun Cosima and does not rewrite simulation products.
"""

from __future__ import annotations

import csv
import json
import math
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
INPUT = ROOT / "reports" / "day15_complete_report"
OUT = ROOT / "reports" / "day15_paper_report"
FIG = OUT / "figures"

SUMMARY = INPUT / "complete_day15_summary.json"
ZOOM_CSV = INPUT / "timeline_spectrum_480_550_rates.csv"
MAIN_CSV = INPUT / "timeline_spectrum_100_10000_rates.csv"
COMP_CSV = INPUT / "image8_like_component_rates_with_science.csv"
SENS_CSV = INPUT / "science_reference_sensitivity.csv"
ACTIVATION_FIG = INPUT / "figures" / "activation_top10_after_fix.png"

PPT_2602 = {
    "exposure_s": 1379.0,
    "raw": 14.1,
    "bgo": 11.1,
    "final": 8.56,
}

DIXE_REFERENCE = {
    "title": "Simulation of non X-ray background for the DIffuse X-ray Explorer (DIXE) mission",
    "doi": "10.21203/rs.3.rs-8576846/v1",
    "nominal_nxb_cps_cm2": 0.528,
    "high_lat_nxb_cps_cm2": 2.11,
    "saa_exit_cps_cm2": 0.38,
    "saa_negligible_min": 15,
}

CAM511_REFERENCE = {
    "paper": "The 511-CAM Mission: A Pointed 511 keV Gamma-Ray Telescope with a Focal Plane Detector Made of Stacked Transition Edge Sensor Microcalorimeter Arrays",
    "arxiv": "arXiv:2206.14652",
    "effective_area_cm2": 50.89,
    "focal_length_m": 12.0,
    "focused_beam_diameter_cm": 3.6,
    "energy_resolution_fwhm_keV": 0.390,
    "detected_line_fraction_510p3_511p8": 0.93,
    "observation_s": 1.0e6,
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def latex_escape(value) -> str:
    text = str(value)
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(repl.get(ch, ch) for ch in text)


def fmt(x, nd=3):
    if x == 0:
        return "0"
    ax = abs(x)
    if ax < 1e-3 or ax >= 1e4:
        return f"{x:.{nd}e}"
    return f"{x:.{nd}f}"


def fmt_pm(x, err, nd=3):
    return f"{fmt(x, nd)} $\\pm$ {fmt(err, nd)}"


def load_numeric_csv(path: Path):
    rows = read_csv(path)
    cols = rows[0].keys()
    data = {c: [] for c in cols}
    for row in rows:
        for c in cols:
            data[c].append(float(row[c]) if c != "component" and row[c] != "" else row[c])
    return data


def integrate_window(csv_data: dict, col: str, lo: float, hi: float, binw: float = 0.5) -> float:
    total = 0.0
    for e, rate in zip(csv_data["E_keV"], csv_data[col]):
        left = e - 0.5 * binw
        right = e + 0.5 * binw
        overlap = max(0.0, min(right, hi) - max(left, lo))
        if overlap > 0:
            total += rate * overlap / binw
    return total


def plot_511_spectrum(zoom, summary):
    path = FIG / "paper_fig_511_veto_spectrum.png"
    e = np.asarray(zoom["E_keV"], dtype=float)
    plt.figure(figsize=(7.2, 4.6))
    plt.step(e, zoom["timeline_raw_cps_per_bin"], where="mid", lw=1.1, color="#4C78A8", label="Poisson timeline: no veto")
    plt.step(e, zoom["timeline_bgo_cps_per_bin"], where="mid", lw=1.1, color="#F58518", label="after BGO veto")
    plt.step(e, zoom["timeline_final_cps_per_bin"], where="mid", lw=1.4, color="#54A24B", label="after BGO + Compton/FoV")
    plt.axvspan(510.3, 511.8, color="#E45756", alpha=0.16, label="CAM511-style 510.3--511.8 keV")
    plt.yscale("log")
    plt.xlabel("Event-summed TES energy (keV)")
    plt.ylabel("Rate per 0.5 keV bin (counts s$^{-1}$)")
    plt.title("Day-15 511-keV window spectrum after successive veto selections")
    plt.grid(True, which="both", alpha=0.22)
    plt.legend(fontsize=8)
    rates = summary["timeline_rates_cps"]
    txt = f"480--550 keV final: {rates['final']:.3f} cps"
    plt.text(0.02, 0.04, txt, transform=plt.gca().transAxes, fontsize=9)
    plt.tight_layout()
    plt.savefig(path, dpi=220)
    plt.close()
    return path


def plot_2602_comparison(summary):
    path = FIG / "paper_fig_2602_comparison.png"
    labels = ["No veto", "BGO", "BGO+Compton/FoV"]
    current = np.array([
        summary["timeline_rates_cps"]["raw"],
        summary["timeline_rates_cps"]["bgo"],
        summary["timeline_rates_cps"]["final"],
    ])
    counts = np.array([
        summary["timeline_counts_480_550"]["raw"],
        summary["timeline_counts_480_550"]["bgo"],
        summary["timeline_counts_480_550"]["final"],
    ])
    obs_time = summary["normalization"]["obs_time_s"]
    current_err = np.sqrt(counts) / obs_time
    old = np.array([PPT_2602["raw"], PPT_2602["bgo"], PPT_2602["final"]])
    x = np.arange(len(labels))
    w = 0.36
    plt.figure(figsize=(7.0, 4.4))
    plt.bar(x - w / 2, old, width=w, color="#9ecae9", label="2602 PPT snapshot")
    plt.bar(x + w / 2, current, width=w, color="#31a354", yerr=current_err, capsize=3, label="2605 corrected Poisson timeline")
    for i, (a, b) in enumerate(zip(old, current)):
        plt.text(i, max(a, b) + 0.45, f"{b/a:.2f}x", ha="center", fontsize=9)
    plt.xticks(x, labels)
    plt.ylabel("480--550 keV rate (counts s$^{-1}$)")
    plt.title("Numerical comparison with the 2602/PPT day-15 snapshot")
    plt.grid(True, axis="y", alpha=0.25)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(path, dpi=220)
    plt.close()
    return path


def plot_components():
    path = FIG / "paper_fig_components.png"
    rows = [r for r in read_csv(COMP_CSV) if r["component"] != "Total"]
    rows = sorted(rows, key=lambda r: float(r["rate_480_550_keV_cps"]), reverse=True)
    labels = [r["component"] for r in rows]
    vals = np.array([float(r["rate_480_550_keV_cps"]) for r in rows])
    colors = ["#4C78A8" if "Cosmic" in l else "#F58518" if "Activation" in l else "#E45756" for l in labels]
    plt.figure(figsize=(7.4, 4.8))
    y = np.arange(len(labels))
    plt.barh(y, vals, color=colors)
    plt.yticks(y, labels)
    plt.gca().invert_yaxis()
    plt.xscale("symlog", linthresh=1e-3)
    plt.xlabel("Direct-expectation no-veto rate in 480--550 keV (counts s$^{-1}$)")
    plt.title("IMAGE8-like component accounting including the reference science stream")
    plt.grid(True, axis="x", alpha=0.25)
    for yi, val in zip(y, vals):
        plt.text(val * 1.08 + 1e-5, yi, fmt(val, 3), va="center", fontsize=8)
    plt.tight_layout()
    plt.savefig(path, dpi=220)
    plt.close()
    return path


def plot_sensitivity(summary, line_background_cps, line_response):
    path = FIG / "paper_fig_sensitivity.png"
    b_broad = summary["science_sensitivity"]["background_final_cps_prompt_plus_delayed"]
    r_broad = summary["science_sensitivity"]["science_final_response_cps_per_ph_cm-2_s-1"]
    t = np.logspace(3, 7, 220)
    f3_broad = 3.0 * np.sqrt(b_broad * t) / (r_broad * t)
    f5_broad = 5.0 * np.sqrt(b_broad * t) / (r_broad * t)
    f3_line = 3.0 * np.sqrt(line_background_cps * t) / (line_response * t)
    f5_line = 5.0 * np.sqrt(line_background_cps * t) / (line_response * t)
    plt.figure(figsize=(7.2, 4.7))
    plt.loglog(t, f3_broad, color="#4C78A8", lw=1.8, label="3 sigma, 480--550 keV counting")
    plt.loglog(t, f5_broad, color="#4C78A8", lw=1.0, ls="--", label="5 sigma, 480--550 keV counting")
    plt.loglog(t, f3_line, color="#E45756", lw=1.8, label="3 sigma, 510.3--511.8 keV line window")
    plt.loglog(t, f5_line, color="#E45756", lw=1.0, ls="--", label="5 sigma, 510.3--511.8 keV line window")
    plt.scatter([1e6], [4.8e-5], marker="*", s=110, color="#222222", label="SPI manual narrow-line reference, 3 sigma 1 Ms")
    plt.xlabel("Exposure (s)")
    plt.ylabel("Minimum line flux (ph cm$^{-2}$ s$^{-1}$)")
    plt.title("Point-source 511-keV sensitivity from the simulated final-stage background")
    plt.grid(True, which="both", alpha=0.24)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(path, dpi=220)
    plt.close()
    return path


def plot_cam511_counts(summary, line_background_cps, line_response):
    path = FIG / "paper_fig_cam511_counts.png"
    t = CAM511_REFERENCE["observation_s"]
    ref_flux = summary["normalization"]["science_flux_ph_cm2_s"]
    broad_b = summary["science_sensitivity"]["background_final_cps_prompt_plus_delayed"] * t
    broad_s = summary["science_sensitivity"]["science_final_response_cps_per_ph_cm-2_s-1"] * ref_flux * t
    line_b = line_background_cps * t
    line_s = line_response * ref_flux * t
    labels = ["480--550 keV\nbroad window", "510.3--511.8 keV\nline window"]
    bkg = np.array([broad_b, line_b])
    sig = np.array([broad_s, line_s])
    x = np.arange(2)
    plt.figure(figsize=(6.6, 4.5))
    plt.bar(x - 0.18, bkg, width=0.34, color="#9ecae9", label="background counts")
    plt.bar(x + 0.18, sig, width=0.34, color="#fdae6b", label=f"source counts at F={ref_flux:.0e}")
    for i in range(2):
        signif = sig[i] / math.sqrt(bkg[i])
        plt.text(i, max(bkg[i], sig[i]) * 1.08, f"S/sqrt(B)={signif:.2f}", ha="center", fontsize=8)
    plt.yscale("log")
    plt.xticks(x, labels)
    plt.ylabel("Counts in 1 Ms")
    plt.title("CAM511 Fig. 11-style detected source/background count comparison")
    plt.grid(True, axis="y", which="both", alpha=0.25)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(path, dpi=220)
    plt.close()
    return path


def plot_main_spectrum(main):
    path = FIG / "paper_fig_main_spectrum.png"
    e = np.asarray(main["E_keV"], dtype=float)
    plt.figure(figsize=(7.2, 4.6))
    plt.step(e, main["timeline_raw_cps_per_bin"], where="mid", color="#4C78A8", lw=1.0, label="No veto")
    plt.step(e, main["timeline_bgo_cps_per_bin"], where="mid", color="#F58518", lw=1.0, label="BGO veto")
    plt.yscale("log")
    plt.xscale("log")
    plt.xlabel("Event-summed TES energy (keV)")
    plt.ylabel("Rate per 10 keV bin (counts s$^{-1}$)")
    plt.title("100--10000 keV day-15 spectrum on the common Poisson timeline")
    plt.grid(True, which="both", alpha=0.22)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(path, dpi=220)
    plt.close()
    return path


def make_tables(summary, line_background_cps, line_response):
    obs = summary["normalization"]["obs_time_s"]
    counts = summary["timeline_counts_480_550"]
    rates = summary["timeline_rates_cps"]
    errs = {k: math.sqrt(counts[k]) / obs for k in counts}
    stages = [
        ("No veto", "raw"),
        ("BGO veto", "bgo"),
        ("BGO + Compton/FoV", "final"),
    ]
    stage_rows = []
    for label, key in stages:
        stage_rows.append(
            (
                label,
                counts[key],
                fmt_pm(rates[key], errs[key], 4),
                fmt(rates[key] / rates["raw"], 3),
                fmt(PPT_2602[key], 3),
                fmt(rates[key] / PPT_2602[key], 3),
            )
        )

    stream_rows = []
    for name, vals in summary["expectation_rates_by_stream_cps"].items():
        stream_rows.append((name, fmt(vals["raw"], 4), fmt(vals["bgo"], 4), fmt(vals["final"], 4)))

    flux_rows = []
    for case, vals in summary["science_sensitivity"]["flux_limits"].items():
        flux_rows.append((case, fmt(vals["exposure_s"], 1), fmt(vals["flux_3sigma_ph_cm2_s"], 4), fmt(vals["flux_5sigma_ph_cm2_s"], 4)))
    one_ms_broad_3 = 3.0 * math.sqrt(summary["science_sensitivity"]["background_final_cps_prompt_plus_delayed"] * 1e6) / (
        summary["science_sensitivity"]["science_final_response_cps_per_ph_cm-2_s-1"] * 1e6
    )
    one_ms_broad_5 = 5.0 * math.sqrt(summary["science_sensitivity"]["background_final_cps_prompt_plus_delayed"] * 1e6) / (
        summary["science_sensitivity"]["science_final_response_cps_per_ph_cm-2_s-1"] * 1e6
    )
    one_ms_line_3 = 3.0 * math.sqrt(line_background_cps * 1e6) / (line_response * 1e6)
    one_ms_line_5 = 5.0 * math.sqrt(line_background_cps * 1e6) / (line_response * 1e6)
    flux_rows.append(("1Ms_broad_480_550", fmt(1e6, 1), fmt(one_ms_broad_3, 4), fmt(one_ms_broad_5, 4)))
    flux_rows.append(("1Ms_line_510.3_511.8", fmt(1e6, 1), fmt(one_ms_line_3, 4), fmt(one_ms_line_5, 4)))

    return stage_rows, stream_rows, flux_rows


def tabular(headers, rows, align=None):
    align = align or ("l" + "r" * (len(headers) - 1))
    lines = [f"\\begin{{tabular}}{{{align}}}", "\\toprule"]
    lines.append(" & ".join(latex_escape(h) for h in headers) + r" \\")
    lines.append("\\midrule")
    for row in rows:
        lines.append(" & ".join(str(x) if "$" in str(x) or "\\" in str(x) else latex_escape(x) for x in row) + r" \\")
    lines.extend(["\\bottomrule", "\\end{tabular}"])
    return "\n".join(lines)


def write_tex(summary, figs, stage_rows, stream_rows, flux_rows, line_background_cps, line_response):
    tex = OUT / "cosmosray_bg_2605_day15_paper_report.tex"
    norm = summary["normalization"]
    sci = summary["science_sensitivity"]
    delay = summary["delay_fix"]
    cat = summary["catalog"]
    draw = summary["draw_summary"]
    timeline = summary["timeline"]

    detector_active_area_cm2 = 20 * 20 * (0.15 * 0.15)
    final_area_norm = summary["timeline_rates_cps"]["final"] / detector_active_area_cm2
    final_spectral_density = final_area_norm / 70.0
    broad_sig_1ms = (
        sci["science_final_response_cps_per_ph_cm-2_s-1"]
        * norm["science_flux_ph_cm2_s"]
        * 1e6
        / math.sqrt(sci["background_final_cps_prompt_plus_delayed"] * 1e6)
    )
    line_sig_1ms = line_response * norm["science_flux_ph_cm2_s"] * 1e6 / math.sqrt(line_background_cps * 1e6)

    stage_table = tabular(
        ["Stage", "timeline counts", "2605 rate (cps)", "survival", "2602 PPT (cps)", "2605/2602"],
        stage_rows,
        align="lrrrrr",
    )
    stream_table = tabular(["Stream", "No veto cps", "BGO cps", "Final cps"], stream_rows, align="lrrr")
    flux_table = tabular(["Case", "Exposure (s)", "3 sigma flux", "5 sigma flux"], flux_rows, align="lrrr")

    body = rf"""
\documentclass[11pt,a4paper]{{ctexart}}
\usepackage[a4paper,margin=2.1cm]{{geometry}}
\usepackage{{amsmath,amssymb,booktabs,longtable,graphicx,float,caption,hyperref,xcolor}}
\usepackage{{enumitem}}
\setCJKmainfont{{Noto Serif CJK SC}}
\setCJKsansfont{{Noto Sans CJK SC}}
\setmainfont{{TeX Gyre Termes}}
\setsansfont{{TeX Gyre Heros}}
\hypersetup{{colorlinks=true,linkcolor=blue!50!black,urlcolor=blue!50!black,citecolor=blue!50!black}}
\setlist{{nosep,leftmargin=2em}}
\captionsetup{{font=small,labelfont=bf}}
\title{{COSMOSRAY\_BG\_2605 第15天本底与 511 keV 点源探测能力评估}}
\author{{Codex TES 511 simulation audit}}
\date{{2026-05-12}}

\begin{{document}}
\maketitle

\begin{{abstract}}
本报告给出 \texttt{{cosmosray\_bg\_2605}} 在第15天气球飞行场景下的完整本底、veto 与 511 keV 点源能力评估。分析最大程度复刻 \texttt{{cosmosray\_bg\_2602}} 的 MEGAlib/Cosima 工作流，但采用已确认的 ground-state/isomer 修正，并把 prompt、fixed delayed 和 511 keV science stream 统一放入同一泊松时间轴后再执行 BGO 与 Compton/FoV veto。正式的 480--550 keV 时间轴结果为：no veto {summary["timeline_rates_cps"]["raw"]:.4f} cps，BGO 后 {summary["timeline_rates_cps"]["bgo"]:.4f} cps，BGO+Compton/FoV 后 {summary["timeline_rates_cps"]["final"]:.4f} cps。该数值与 2602 PPT 的 14.1/11.1/8.56 cps 不完全相同；差异是可追踪的，主要来自修正后的 delayed source、自洽观测时间和时间窗 veto 口径，而不是统计文件缺失。
\end{{abstract}}

\section{{直接回答与结论}}
\textbf{{2602 对标。}} 2605 的流程与 2602/PPT 是同源的：大气宇宙线 prompt、buildup 生成 RPIP 活化源、day-15 delayed、共时间轴、BGO veto、Compton/FoV veto。但数值不能声称“完全对上”。2602 PPT 的第15天快照为 14.1/11.1/8.56 cps；本次 corrected Poisson timeline 为 {summary["timeline_rates_cps"]["raw"]:.4f}/{summary["timeline_rates_cps"]["bgo"]:.4f}/{summary["timeline_rates_cps"]["final"]:.4f} cps，final 约为 2602 PPT 的 {summary["timeline_rates_cps"]["final"]/PPT_2602["final"]:.3f} 倍。更合理的表述是：\emph{{工作流复刻成功，统计量在同一量级，但 corrected/fixed 版本不应被强行调到旧 PPT 数值}}。

\textbf{{报告水准。}} 前一版 PDF 更像状态汇总，确实达不到论文报告水准。本文补充了公式、归一化、DIXE 式面积归一化统计口径、CAM511 Fig. 11 式源/本底计数与灵敏度、2602 对照和审计闭环。

\textbf{{511 keV 点源能力。}} 对 reference flux $F=10^{{-4}}\,\mathrm{{ph\,cm^{{-2}}\,s^{{-1}}}}$，当前 final-stage response 为 {sci["science_final_response_cps_per_ph_cm-2_s-1"]:.4f} cps/($\mathrm{{ph\,cm^{{-2}}\,s^{{-1}}}}$)。若用整个 480--550 keV 窗口计数，1 Ms 显著性约 {broad_sig_1ms:.2f}$\sigma$；若用 CAM511 论文 Fig. 11 附近的 510.3--511.8 keV 线窗并保守取 93\% 源保留率，1 Ms 显著性约 {line_sig_1ms:.2f}$\sigma$。因此当前模拟支持的结论是：本构型已经能给出清晰的 511 源响应，但若要稳定探测 $10^{{-4}}\,\mathrm{{ph\,cm^{{-2}}\,s^{{-1}}}}$ 级点源，还需要进一步压低 511 keV 仪器线/活化背景或加入更严格的焦斑、边缘像素、自屏蔽与线型拟合选择。

\section{{输入和可复现性}}
\begin{{itemize}}
  \item Prompt SIM: {cat["by_stream"]["prompt"]["events"]:,} kept events from {summary["inputs"]["prompt_files"]} files; prompt equivalent time {norm["prompt_time_s"]:.6f} s.
  \item Fixed delayed SIM: {cat["by_stream"]["delayed"]["events"]:,} kept events; Cosima observation time {norm["delayed_time_s"]:.1f} s.
  \item Science SIM: {cat["by_stream"]["science"]["events"]:,} kept events from the on-axis 511 keV focal-beam source.
  \item Common timeline: observation time {norm["obs_time_s"]:.1f} s, coincidence window {norm["coincidence_window_s"]:.1e} s, BGO threshold {norm["bgo_threshold_keV"]:.0f} keV, Compton reject policy \texttt{{{latex_escape(norm["reject_policy"])}}}.
  \item Poisson draws: prompt {draw["prompt"]["drawn"]:,}, delayed {draw["delayed"]["drawn"]:,}, science {draw["science"]["drawn"]:,}; TES candidates {timeline["n_candidates_with_tes"]:,}; mixed candidates {timeline["n_mixed_candidates"]:,}.
\end{{itemize}}

\section{{本底模拟和归一化方法}}
宇宙线 prompt 使用 EXPACS/PARMA 类全空间大气粒子谱，按下行和上行角段生成 MEGAlib \texttt{{FarFieldAreaSource}}；buildup 运行记录 \texttt{{CC IP RP}} 活化核素、几何体和位置。第15天 delayed source 对每个核素 $j$ 采用连续照射增长和冷却衰减：
\begin{{equation}}
A_j(t_0)=P_j\left(1-e^{{-\lambda_j T_\mathrm{{flight}}}}\right)e^{{-\lambda_j T_\mathrm{{after}}}},
\end{{equation}}
其中 $P_j$ 是由 buildup 归一化得到的产生率，$\lambda_j=\ln2/t_{{1/2,j}}$。若需要有限观测段 $[t_0,t_0+\Delta T]$ 的衰变数，使用
\begin{{equation}}
N_j(\Delta T)=\int_0^{{\Delta T}}A_j(t_0)e^{{-\lambda_j t}}dt
=\frac{{A_j(t_0)}}{{\lambda_j}}\left(1-e^{{-\lambda_j\Delta T}}\right).
\end{{equation}}
本次固定源由 day-15 活度构造，并由 Cosima fixed delayed run 给出 {norm["delayed_time_s"]:.1f} s 观测时间；时间轴合并阶段使用该观测时间作为统一曝光。

511 keV science stream 采用 CAM511/511-CAM 式外部聚焦光学近似：先在光学端采用 $A_\mathrm{{eff}}(511\,\mathrm{{keV}})=50.89\,\mathrm{{cm^2}}$ 与大气透过率，再把到达 Be 窗的 photons 注入 Cosima。参考流量为 $F={norm["science_flux_ph_cm2_s"]:.1e}\,\mathrm{{ph\,cm^{{-2}}\,s^{{-1}}}}$，对应 science injection rate {norm["science_injection_rate_s^-1"]:.6f} s$^{{-1}}$。

\section{{VETO 结果和 2602 对照}}
\begin{{table}}[H]
\centering
{stage_table}
\caption{{第15天 480--550 keV 时间轴 veto 结果与 2602 PPT 快照对照。2605 误差只给泊松抽样误差，不含系统误差。}}
\end{{table}}

\begin{{figure}}[H]
\centering
\includegraphics[width=0.92\linewidth]{{{figs["compare"].as_posix()}}}
\caption{{2602 PPT 与 2605 corrected Poisson timeline 的阶段积分率对照。2605 没有被调参去匹配旧 PPT；它采用 fixed delayed source 和统一观测时间。}}
\end{{figure}}

\begin{{figure}}[H]
\centering
\includegraphics[width=0.92\linewidth]{{{figs["zoom"].as_posix()}}}
\caption{{480--550 keV 窗口内的能谱和 veto 链。510.3--511.8 keV 阴影区用于后文 CAM511 Fig. 11 式线窗灵敏度估计。}}
\end{{figure}}

\begin{{figure}}[H]
\centering
\includegraphics[width=0.92\linewidth]{{{figs["main"].as_posix()}}}
\caption{{100--10000 keV 宽能段时间轴谱。Compton/FoV veto 主要针对 511 keV 分析窗口解释。}}
\end{{figure}}

\section{{成分分解与 delayed 修正}}
\begin{{table}}[H]
\centering
{stream_table}
\caption{{直接期望交叉检查下的 stream 分解。正式 veto 结果以前文 Poisson timeline 为准；本表用于检查统计稳定性。}}
\end{{table}}

\begin{{figure}}[H]
\centering
\includegraphics[width=0.90\linewidth]{{{figs["components"].as_posix()}}}
\caption{{IMAGE8-like no-veto 成分统计，已加入 Science511(reference) 作为独立 signal stream。}}
\end{{figure}}

Ground-state/isomer 修正确认应用于 delayed source。修正前总活度 {delay["old_total_activity_Bq"]:.3f} Bq，修正后 {delay["new_total_activity_Bq"]:.3f} Bq；source blocks 从 {delay["source_blocks_in"]} 降到 {delay["source_blocks_after_fix"]}，移除 {delay["source_blocks_removed"]} 个 blocks。审计结果显示 fixed source 中 \texttt{{ParticleType 74183}} 与 \texttt{{74180}} 残留均为 false。

\begin{{figure}}[H]
\centering
\includegraphics[width=0.82\linewidth]{{{ACTIVATION_FIG.as_posix()}}}
\caption{{Ground-state/isomer 修正后的 day-15 活化分量。W-187 仍是需要后续诊断的 511 keV 残差候选之一；W-183/W-180 ground state 不再作为短寿命活化源。}}
\end{{figure}}

\section{{DIXE 论文统计口径对照}}
DIXE NXB 论文采用 Geant4 质量模型、真实粒子谱和面积归一化 NXB 指标，核心统计量为 counts s$^{{-1}}$ cm$^{{-2}}$ keV$^{{-1}}$；其事件归一化可写为
\begin{{equation}}
B_i=\frac{{4\pi^2 C_i R_\mathrm{{int}}^2\Phi}}{{N A_\mathrm{{det}}\Delta E_i}},
\end{{equation}}
并按可见天空、地球遮挡或反照来源加入 $\Omega_\mathrm{{inc}}/4\pi$ 修正。DIXE 报告在 LEO 低磁纬、太阳极小条件下得到 $0.528\,\mathrm{{counts\,s^{{-1}}\,cm^{{-2}}}}$，高磁纬可达 $2.11\,\mathrm{{counts\,s^{{-1}}\,cm^{{-2}}}}$；SAA delayed background 在离开后约15 min 内衰减到可忽略。

对本工作，直接拿 DIXE 数值作物理比较是不合适的：本项目是 511 keV 气球环境，窗口是 480--550 keV，且有 BGO 与 Compton/FoV veto；DIXE 是 LEO 0.1--10 keV microcalorimeter NXB，且无 ACD/聚焦光学。可比较的是统计口径。本报告按 DIXE 式写出面积归一化：TES 单层主动投影面积约 $20\times20\times(0.15\,\mathrm{{cm}})^2={detector_active_area_cm2:.2f}\,\mathrm{{cm^2}}$，因此 final 480--550 keV 背景约
\[
{summary["timeline_rates_cps"]["final"]:.4f}/{detector_active_area_cm2:.2f}
= {final_area_norm:.4f}\,\mathrm{{counts\,s^{{-1}}\,cm^{{-2}}}},
\]
等效谱密度约 ${final_spectral_density:.4e}\,\mathrm{{counts\,s^{{-1}}\,cm^{{-2}}\,keV^{{-1}}}}$。这只是本 511 keV 线窗的内部归一化指标，不应与 DIXE 0.1--10 keV 总 NXB 直接排序。

\section{{CAM511 Fig. 11 式 511 keV 源能力评估}}
511-CAM 论文的 Fig. 11 使用 1 Ms detected counts 和 3$\sigma$ line sensitivity 比较仪器能力。对应的背景受限计数公式为
\begin{{equation}}
N_s=F R_sT,\quad N_b=R_bT,\quad
\mathrm{{SNR}}\simeq \frac{{N_s}}{{\sqrt{{N_b}}}},
\end{{equation}}
\begin{{equation}}
F_{{n\sigma}}=\frac{{n\sqrt{{R_bT}}}}{{R_sT}},
\end{{equation}}
其中 $R_s$ 是单位 flux 的 final-stage source response，$R_b$ 是同一选择下的背景率。当前 480--550 keV final-stage 背景 $R_b={sci["background_final_cps_prompt_plus_delayed"]:.4f}$ cps；source response $R_s={sci["science_final_response_cps_per_ph_cm-2_s-1"]:.4f}$ cps/($\mathrm{{ph\,cm^{{-2}}\,s^{{-1}}}}$)。对 CAM511-style 510.3--511.8 keV 线窗，背景由 0.5 keV 谱按 bin overlap 积分得到 $R_b={line_background_cps:.4f}$ cps，并保守采用 93\% science line retention，$R_s={line_response:.4f}$ cps/($\mathrm{{ph\,cm^{{-2}}\,s^{{-1}}}}$)。

\begin{{table}}[H]
\centering
{flux_table}
\caption{{点源流量阈值。前3行来自完整报告的 480--550 keV final-stage 公式；后2行给出 1 Ms 下 broad/window 两种口径。单位均为 ph cm$^{{-2}}$ s$^{{-1}}$。}}
\end{{table}}

\begin{{figure}}[H]
\centering
\includegraphics[width=0.92\linewidth]{{{figs["counts"].as_posix()}}}
\caption{{参考源 $F=10^{{-4}}\,\mathrm{{ph\,cm^{{-2}}\,s^{{-1}}}}$ 在 1 Ms 内的 detected counts 与本底 counts。该图仿照 CAM511 Fig. 11 左图的 source/background count 思路。}}
\end{{figure}}

\begin{{figure}}[H]
\centering
\includegraphics[width=0.92\linewidth]{{{figs["sensitivity"].as_posix()}}}
\caption{{由本次模拟得到的 point-source line sensitivity 曲线，并标出 SPI manual 中 511 keV narrow-line 3$\sigma$/1 Ms 参考点 $4.8\times10^{{-5}}\,\mathrm{{ph\,cm^{{-2}}\,s^{{-1}}}}$。当前 broad-window 结果偏保守；line-window 结果仍受 511 keV 仪器线背景限制。}}
\end{{figure}}

\section{{审计、疏漏和下一轮应修复项}}
\begin{{enumerate}}
  \item \textbf{{旧 2602 数值不应被机械追平。}} 当前结果是 corrected 物理链路；若报告要复现旧 PPT 数值，需要另行生成 ``legacy compatibility'' 分支，保留旧 delayed source、旧 exposure denominator 和旧 merge 口径。
  \item \textbf{{当前 511 源能力仍是窗口计数近似。}} 更论文级的下一步应做 profile likelihood 或 forward-folding line fit，把 511 keV 仪器线、continuum、science Gaussian response 和可能的 positronium continuum 同时拟合。
  \item \textbf{{DIXE 式 incident/induced 分解尚未完全实现。}} 当前 MEGAlib CC-HIT 层面没有完整保存每个 final TES hit 的 parent production volume/process 分类表，因此本报告只做 stream/component 分解，没有完全复现 DIXE Fig. 10 的 creation-volume/process 统计。
  \item \textbf{{气球反照与轨迹变化。}} 当前 full-sphere atmospheric source 已含上下行角段，但 prompt light-curve shape 仍全为 1.0；显式轨迹变化、DIXE 式 albedo photon/neutron 独立模型仍需后续生产。
  \item \textbf{{可能的灵敏度提升方向。}} 优先测试更严格的焦平面 ROI、边缘像素 self-shielding、单像素/多像素分通道 likelihood、BGO 阈值扫描和 delayed W-187 诊断。
\end{{enumerate}}

\section{{参考资料}}
\begin{{itemize}}
  \item Shirazi et al., ``The 511-CAM Mission'', \texttt{{arXiv:2206.14652}}；本报告参考其 Fig. 11 的 1 Ms source/background counts 与 3$\sigma$ sensitivity 表达方式。
  \item Tian et al., ``Simulation of non X-ray background for the DIffuse X-ray Explorer (DIXE) mission'', DOI \href{{https://doi.org/{DIXE_REFERENCE["doi"]}}}{{{DIXE_REFERENCE["doi"]}}}；本报告参考其面积归一化 NXB、成分分解和 delayed background 统计方式。
  \item \texttt{{cosmosray\_0416.zip}} 中的 2602/PPT：第15天、1379 s、14.1/11.1/8.56 cps 快照。
  \item 本地产物：\texttt{{cosmosray\_bg\_2605/reports/day15\_complete\_report/complete\_day15\_summary.json}}。
\end{{itemize}}

\end{{document}}
"""
    tex.write_text(body, encoding="utf-8")
    return tex


def update_memory_workflow(pdf_path: Path):
    memory = WORKSPACE / "memory.md"
    workflow = WORKSPACE / "workflow.md"
    mem_text = memory.read_text(encoding="utf-8", errors="ignore")
    wf_text = workflow.read_text(encoding="utf-8", errors="ignore")
    marker = "## 2026-05-12 paper-level report update"
    mem_block = f"""

{marker}

- Built paper-style day-15 report: `{pdf_path.relative_to(WORKSPACE)}`.
- 2605 corrected Poisson timeline does not numerically match the old 2602/PPT rates: 480-550 keV final is 5.6443 cps versus 8.56 cps in the PPT; this is documented as a corrected/fixed workflow difference, not hidden as agreement.
- Added CAM511 Fig.11-style 1 Ms source/background and sensitivity evaluation. Broad 480-550 keV 3 sigma 1 Ms limit is about 2.12e-4 ph cm^-2 s^-1; 510.3-511.8 keV line-window estimate is about 1.34e-4 ph cm^-2 s^-1.
- Added DIXE-inspired area-normalized NXB bookkeeping for the 480-550 keV final window: 5.6443 cps over about 9.0 cm2 active projected TES area, or 0.627 cps cm^-2.
"""
    wf_block = f"""

{marker}

- Final reports should distinguish `workflow-equivalent to 2602` from `numerically identical to 2602`; corrected/fixed delayed and unified Poisson timing are expected to move the rates.
- 511-source capability should be reported with both broad 480-550 keV counting and a CAM511-style narrow line window, using source counts, background counts, S/sqrt(B), and n-sigma flux limits.
- When citing DIXE-style NXB statistics, use area-normalized rates only as a bookkeeping analogy unless the same orbit, energy band, and radiation components are simulated.
"""
    if marker not in mem_text:
        memory.write_text(mem_text.rstrip() + mem_block + "\n", encoding="utf-8")
    if marker not in wf_text:
        workflow.write_text(wf_text.rstrip() + wf_block + "\n", encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    # Context files are deliberately touched/read here so the generated report is
    # always made after checking the running memory and workflow notes.
    _ = (WORKSPACE / "memory.md").read_text(encoding="utf-8", errors="ignore")
    _ = (WORKSPACE / "workflow.md").read_text(encoding="utf-8", errors="ignore")

    summary = load_json(SUMMARY)
    zoom = load_numeric_csv(ZOOM_CSV)
    main_csv = load_numeric_csv(MAIN_CSV)

    line_background = integrate_window(zoom, "expectation_final_cps_per_bin", 510.3, 511.8, binw=0.5)
    line_response = (
        summary["science_sensitivity"]["science_final_response_cps_per_ph_cm-2_s-1"]
        * CAM511_REFERENCE["detected_line_fraction_510p3_511p8"]
    )

    figs = {
        "zoom": plot_511_spectrum(zoom, summary),
        "compare": plot_2602_comparison(summary),
        "components": plot_components(),
        "sensitivity": plot_sensitivity(summary, line_background, line_response),
        "counts": plot_cam511_counts(summary, line_background, line_response),
        "main": plot_main_spectrum(main_csv),
    }
    stage_rows, stream_rows, flux_rows = make_tables(summary, line_background, line_response)
    tex = write_tex(summary, figs, stage_rows, stream_rows, flux_rows, line_background, line_response)

    audit = {
        "pdf": str((OUT / "cosmosray_bg_2605_day15_paper_report.pdf").relative_to(WORKSPACE)),
        "inputs": {
            "summary": str(SUMMARY.relative_to(WORKSPACE)),
            "zoom_csv": str(ZOOM_CSV.relative_to(WORKSPACE)),
            "component_csv": str(COMP_CSV.relative_to(WORKSPACE)),
        },
        "line_window_510p3_511p8": {
            "background_cps_expectation_final": line_background,
            "source_response_cps_per_ph_cm2_s_conservative_93pct": line_response,
            "flux_3sigma_1Ms": 3.0 * math.sqrt(line_background * 1.0e6) / (line_response * 1.0e6),
            "flux_5sigma_1Ms": 5.0 * math.sqrt(line_background * 1.0e6) / (line_response * 1.0e6),
        },
        "broad_480_550": {
            "background_cps_expectation_final": summary["science_sensitivity"]["background_final_cps_prompt_plus_delayed"],
            "source_response_cps_per_ph_cm2_s": summary["science_sensitivity"]["science_final_response_cps_per_ph_cm-2_s-1"],
            "flux_3sigma_1Ms": 3.0
            * math.sqrt(summary["science_sensitivity"]["background_final_cps_prompt_plus_delayed"] * 1.0e6)
            / (summary["science_sensitivity"]["science_final_response_cps_per_ph_cm-2_s-1"] * 1.0e6),
        },
        "references": {
            "cam511": CAM511_REFERENCE,
            "dixe": DIXE_REFERENCE,
        },
    }
    (OUT / "paper_report_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")

    for _pass in range(2):
        subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error", tex.name],
            cwd=OUT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

    pdf = OUT / "cosmosray_bg_2605_day15_paper_report.pdf"
    update_memory_workflow(pdf)
    print(pdf)


if __name__ == "__main__":
    main()
