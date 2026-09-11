#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a detailed Chinese review packet for GPT Pro inspection."""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
OUT = ROOT / "reports" / "gptpro_review_packet"

SUMMARY = ROOT / "reports" / "day15_complete_report" / "complete_day15_summary.json"
ACCIDENTAL = ROOT / "reports" / "science_accidental_veto" / "science_accidental_veto_summary.json"
SCI_EN = ROOT / "reports" / "day15_sci_manuscript" / "cosmosray_bg_2605_sci_manuscript.pdf"
SCI_ZH = ROOT / "reports" / "day15_sci_manuscript_zh" / "cosmosray_bg_2605_sci_manuscript_zh.pdf"

FIG_WORKFLOW = ROOT / "reports" / "day15_sci_manuscript_zh" / "figures" / "fig01_workflow.png"
FIG_LINE = ROOT / "reports" / "day15_sci_manuscript_zh" / "figures" / "fig03_line_window.png"
FIG_STREAMS = ROOT / "reports" / "day15_sci_manuscript_zh" / "figures" / "fig04_stream_decomposition.png"
FIG_SENS = ROOT / "reports" / "day15_sci_manuscript_zh" / "figures" / "fig07_sensitivity.png"
FIG_ACC = ROOT / "reports" / "science_accidental_veto" / "science_accidental_veto_loss.png"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sci_tex(value: float, nd: int = 3) -> str:
    if value == 0:
        return "0"
    exp = math.floor(math.log10(abs(value)))
    mant = value / (10**exp)
    return rf"{mant:.{nd}f}\times10^{{{exp}}}"


def table(headers, rows, align=None):
    align = align or ("l" + "r" * (len(headers) - 1))
    lines = [rf"\begin{{tabular}}{{{align}}}", r"\toprule"]
    lines.append(" & ".join(headers) + r" \\")
    lines.append(r"\midrule")
    for row in rows:
        lines.append(" & ".join(str(x) for x in row) + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    return "\n".join(lines)


def write_tex(summary: dict, acc: dict):
    tex = OUT / "cosmosray_bg_2605_gptpro_review_packet.tex"
    norm = summary["normalization"]
    rates = summary["timeline_rates_cps"]
    counts = summary["timeline_counts_480_550"]
    exp = summary["expectation_rates_by_stream_cps"]
    sci = summary["science_sensitivity"]
    delay = summary["delay_fix"]
    draw = summary["draw_summary"]

    broad_corr = acc["windows"]["broad_480_550"]["accidental_survival_correction"]
    line_corr = acc["windows"]["line_510p3_511p8"]["accidental_survival_correction"]
    broad_uncorr_3 = 3.0 * math.sqrt(sci["background_final_cps_prompt_plus_delayed"] * 1.0e6) / (
        sci["science_final_response_cps_per_ph_cm-2_s-1"] * 1.0e6
    )
    broad_uncorr_5 = 5.0 * math.sqrt(sci["background_final_cps_prompt_plus_delayed"] * 1.0e6) / (
        sci["science_final_response_cps_per_ph_cm-2_s-1"] * 1.0e6
    )
    line_b = acc["windows"]["line_510p3_511p8"]["energy_window_keV"]
    line_background = acc["windows"]["line_510p3_511p8"].get("line_background_cps")
    # The accidental file intentionally stores only the correction.  The line
    # uncorrected sensitivity is read from the established manuscript audit.
    manuscript_audit = load_json(ROOT / "reports" / "day15_sci_manuscript" / "sci_manuscript_audit.json")
    line_uncorr_3 = manuscript_audit["line_window_510p3_511p8"]["flux_3sigma_1Ms"]
    line_uncorr_5 = manuscript_audit["line_window_510p3_511p8"]["flux_5sigma_1Ms"]
    broad_corr_3 = broad_uncorr_3 / broad_corr
    broad_corr_5 = broad_uncorr_5 / broad_corr
    line_corr_3 = line_uncorr_3 / line_corr
    line_corr_5 = line_uncorr_5 / line_corr

    veto_table = table(
        ["阶段", "计数", "率 cps", "相对无VETO"],
        [
            ["无 VETO", counts["raw"], f"{rates['raw']:.6f}", "1.000"],
            ["BGO 后", counts["bgo"], f"{rates['bgo']:.6f}", f"{rates['bgo']/rates['raw']:.3f}"],
            ["BGO+Compton/FoV 后", counts["final"], f"{rates['final']:.6f}", f"{rates['final']/rates['raw']:.3f}"],
        ],
        "lrrr",
    )
    stream_table = table(
        ["流", "raw cps", "BGO cps", "final cps"],
        [
            ["prompt", f"{exp['prompt']['raw']:.5f}", f"{exp['prompt']['bgo']:.5f}", f"{exp['prompt']['final']:.5f}"],
            ["delayed", f"{exp['delayed']['raw']:.5f}", f"{exp['delayed']['bgo']:.5f}", f"{exp['delayed']['final']:.5f}"],
            ["science", f"{exp['science']['raw']:.7f}", f"{exp['science']['bgo']:.7f}", f"{exp['science']['final']:.7f}"],
        ],
        "lrrr",
    )
    acc_rows = []
    for label, key in [("480--550 keV", "broad_480_550"), ("510.3--511.8 keV", "line_510p3_511p8")]:
        w = acc["windows"][key]
        causes = w["loss_causes"]
        acc_rows.append(
            [
                label,
                f"{w['accidental_loss_fraction_all_selected']*100:.4f}\\%",
                f"{w['accidental_survival_correction']:.6f}",
                f"{w['conditional_loss_given_accidental_bg']*100:.2f}\\%",
                f"BGO {causes.get('bgo_veto',0)}, E {causes.get('energy_out',0)}, C {causes.get('compton_veto',0)}",
            ]
        )
    acc_table = table(["能窗", "总误损失", "校正因子", "有偶然本底时损失", "损失原因计数"], acc_rows, "lrrrr")
    sens_table = table(
        ["能窗", "未校正 3σ", "校正后 3σ", "未校正 5σ", "校正后 5σ"],
        [
            ["480--550 keV", f"${sci_tex(broad_uncorr_3)}$", f"${sci_tex(broad_corr_3)}$", f"${sci_tex(broad_uncorr_5)}$", f"${sci_tex(broad_corr_5)}$"],
            ["510.3--511.8 keV", f"${sci_tex(line_uncorr_3)}$", f"${sci_tex(line_corr_3)}$", f"${sci_tex(line_uncorr_5)}$", f"${sci_tex(line_corr_5)}$"],
        ],
        "lrrrr",
    )

    body = rf"""
\documentclass[11pt,a4paper]{{ctexart}}
\usepackage[a4paper,margin=2.05cm]{{geometry}}
\usepackage{{fontspec,amsmath,amssymb,booktabs,graphicx,float,caption,xurl,hyperref,xcolor}}
\usepackage{{enumitem}}
\setCJKmainfont{{Noto Serif CJK SC}}
\setCJKsansfont{{Noto Sans CJK SC}}
\setmainfont{{TeX Gyre Termes}}
\setsansfont{{TeX Gyre Heros}}
\hypersetup{{colorlinks=true,linkcolor=blue!50!black,urlcolor=blue!50!black}}
\captionsetup{{font=small,labelfont=bf}}
\setlist{{nosep,leftmargin=2em}}
\renewcommand{{\figurename}}{{图}}
\renewcommand{{\tablename}}{{表}}
\title{{COSMOSRAY\_BG\_2605 第15天 511 keV 本底与科学源 VETO 审阅包}}
\author{{Codex TES 511 simulation audit}}
\date{{2026-05-12}}
\begin{{document}}
\maketitle

\begin{{abstract}}
本文是给 GPT Pro 复核用的完整审阅包，记录当前 \texttt{{cosmosray\_bg\_2605}} 第15天模拟的逻辑、实现细节、关键数值、漏洞修复和最终结论。当前正式链路为：瞬时大气宇宙线 prompt、buildup 生成并修正后的 delayed activation、外置聚焦光学归一化的 511 keV science source 三者分别进入 MEGAlib/Cosima 探测器输运；后处理阶段把三类事件放到共同泊松时间轴，再执行 BGO 和 Compton/FoV VETO。新增的 100 万 science trial 高统计 bootstrap 表明，无关本底偶然符合会使已通过孤立筛选的 science 事件损失约 1.642\%，主要原因是 BGO 偶然触发。将该效应折入后，1 Ms、3$\sigma$ 点源阈值从 $2.123\times10^{{-4}}$ 和 $1.333\times10^{{-4}}$ ph cm$^{{-2}}$ s$^{{-1}}$ 上调到约 ${sci_tex(broad_corr_3)}$ 和 ${sci_tex(line_corr_3)}$ ph cm$^{{-2}}$ s$^{{-1}}$。
\end{{abstract}}

\section{{一页结论}}
\begin{{itemize}}
  \item 当前模拟链路是闭合的：prompt、delayed、science 三流均有独立归一化、共同时间轴和同一 VETO 逻辑。
  \item 第15天 480--550 keV 时间轴结果为：无 VETO {rates['raw']:.4f} cps，BGO 后 {rates['bgo']:.4f} cps，BGO+Compton/FoV 后 {rates['final']:.4f} cps。
  \item delayed source 已应用 W-183/W-180 基态/同核异能态修正；fixed source 中 W183/W180 残留标志均为 false。
  \item science source 在 1094.2 s realization 中确实泊松抽样，期望 {draw['science']['lambda']:.3f} 个，实际 {draw['science']['drawn']} 个，并经过同一 VETO；灵敏度曲线使用 direct-expectation/Asimov 响应以避免低计数 realization 噪声。
  \item 新增 accidental-veto 校正显示：科学源被无关本底误损失约 1.642\%，应把 science response 乘以约 0.9836，灵敏度阈值相应上调约 1.67\%。
  \item 当前仍不能声称 $10^{{-4}}$ ph cm$^{{-2}}$ s$^{{-1}}$ 稳态点源在 1 Ms 内达到稳健 3$\sigma$；当前校正后窄线窗 3$\sigma$ 阈值约 ${sci_tex(line_corr_3)}$ ph cm$^{{-2}}$ s$^{{-1}}$。
\end{{itemize}}

\section{{数据谱系与输入}}
\begin{{itemize}}
  \item Prompt SIM: \path{{cosmosray_bg_2605/production_runs/instant_equiv2602/}}，60 个 SIM 文件。
  \item Delayed SIM: \path{{production_runs/delay_fix_from_buildup_equiv2602/DelayedDecayRPIPGroundStateFixed.inc1.id1.sim.gz}}。
  \item Science SIM: \path{{science_511_onaxis_source/Science_511_onaxis_focalbeam_gateAfix.inc1.id1.sim.gz}}。
  \item 事件目录: \path{{cosmosray_bg_2605/reports/day15_complete_report/work/event_catalog.pkl}}。
  \item 主 summary: \path{{cosmosray_bg_2605/reports/day15_complete_report/complete_day15_summary.json}}。
  \item Accidental-veto summary: \path{{cosmosray_bg_2605/reports/science_accidental_veto/science_accidental_veto_summary.json}}。
\end{{itemize}}

\section{{模拟逻辑}}
\begin{{figure}}[H]
\centering
\includegraphics[width=0.95\linewidth]{{{FIG_WORKFLOW.as_posix()}}}
\caption{{当前正式工作流。外置聚焦光学只给 science source 的有效面积、焦斑和大气透过率；MEGAlib/Cosima 负责探测器和屏蔽输运。}}
\end{{figure}}

prompt 本底来自全空间大气次级粒子源；buildup 运行记录 RPIP 活化核素；第15天 delayed source 由
\[
A_j(t_0)=P_j\left(1-e^{{-\lambda_jT_\mathrm{{irr}}}}\right)e^{{-\lambda_jT_\mathrm{{cool}}}}
\]
归一化，并对有限观测段使用
\[
N_j(\Delta T)=\frac{{A_j(t_0)}}{{\lambda_j}}\left(1-e^{{-\lambda_j\Delta T}}\right).
\]
science source 使用 $R_\mathrm{{inj}}=F_{{511}}A_\mathrm{{eff}}T_\mathrm{{atm}}$，其中 $A_\mathrm{{eff}}=50.89$ cm$^2$，本次账本给出 $T_\mathrm{{atm}}\simeq0.739$。

\section{{共同时间轴与 VETO}}
每个流按 $N_k\sim\mathrm{{Poisson}}(R_kT_\mathrm{{obs}})$ 抽样，并在 $T_\mathrm{{obs}}={norm['obs_time_s']:.1f}$ s 内均匀赋时。时间差小于 {norm['coincidence_window_s']:.1e} s 的事件被合并为候选组。候选组先按总 TES 能量进入 480--550 keV 或 511 keV 线窗，再按候选组总 BGO 能量与 Compton/FoV 几何判据筛选。BGO 阈值为 {norm['bgo_threshold_keV']:.0f} keV，Compton reject policy 为 \texttt{{{norm['reject_policy']}}}。

\begin{{table}}[H]
\centering
{veto_table}
\caption{{第15天 480--550 keV 时间轴 VETO 效果。}}
\end{{table}}

\begin{{figure}}[H]
\centering
\includegraphics[width=0.92\linewidth]{{{FIG_LINE.as_posix()}}}
\caption{{511 keV 窗口 VETO 前后能谱。}}
\end{{figure}}

\begin{{table}}[H]
\centering
{stream_table}
\caption{{direct-expectation 交叉检查中的 stream 分解。}}
\end{{table}}

\begin{{figure}}[H]
\centering
\includegraphics[width=0.88\linewidth]{{{FIG_STREAMS.as_posix()}}}
\caption{{共同时间轴中的 stream 分解；mixed 类别来自同一符合组中多个物理流重叠。}}
\end{{figure}}

\section{{Science accidental-veto 高统计校正}}
此前报告中的 science 灵敏度使用 direct-expectation/Asimov source response，已经包含 science 事件自身在探测器中产生的 BGO/Compton 损失，但没有包含长曝光中无关背景偶然落入同一符合窗导致的 science 误损失。为估计该项，本文使用已有 event catalog 进行 100 万 science trial bootstrap：
\begin{{itemize}}
  \item science 事件按 science catalog 的物理权重抽样；
  \item prompt+delayed 本底按总率 {acc['background_total_rate_hz']:.3f} Hz 的泊松过程抽样；
  \item 使用同一个 1 $\mu$s rolling coincidence-window 规则向 science 事件左右连接偶然本底；
  \item 对混合候选重新执行能窗、BGO 和 Compton/FoV 判定。
\end{{itemize}}

偶然连接至少一个背景事件的概率为 {acc['background_cluster']['p_any_background_model']*100:.3f}\%。在有偶然背景的 science 事件中，约 53\% 会被损失；折算到全部已通过孤立筛选的 science 事件，误损失约 1.642\%。

\begin{{table}}[H]
\centering
{acc_table}
\caption{{100 万 science trial 得到的 accidental-veto 校正。BGO 为主因，energy-out 次之，Compton/FoV 误损失很小。}}
\end{{table}}

\begin{{figure}}[H]
\centering
\includegraphics[width=0.82\linewidth]{{{FIG_ACC.as_posix()}}}
\caption{{科学源 accidental-veto 误损失分解。}}
\end{{figure}}

\section{{灵敏度：校正前后}}
未校正公式为
\[
F_{{n\sigma}}=\frac{{n\sqrt{{R_bT}}}}{{R_sT}}.
\]
accidental-veto 校正把 $R_s$ 乘以 survival correction $c_\mathrm{{acc}}$，因此
\[
F_{{n\sigma}}^\mathrm{{corr}}=\frac{{F_{{n\sigma}}^\mathrm{{uncorr}}}}{{c_\mathrm{{acc}}}}.
\]

\begin{{table}}[H]
\centering
{sens_table}
\caption{{1 Ms 点源灵敏度阈值。单位均为 ph cm$^{{-2}}$ s$^{{-1}}$。}}
\end{{table}}

\begin{{figure}}[H]
\centering
\includegraphics[width=0.90\linewidth]{{{FIG_SENS.as_posix()}}}
\caption{{原始 Asimov 灵敏度曲线；表中给出 accidental-veto 后数值校正。}}
\end{{figure}}

\section{{已修复的问题与仍不能过度声称的点}}
\begin{{enumerate}}
  \item W-183/W-180 基态误当同核异能态的问题已经通过 fixed delayed source 修复；修正前活度 {delay['old_total_activity_Bq']:.3f} Bq，修正后 {delay['new_total_activity_Bq']:.3f} Bq。
  \item science stream 已进入泊松时间轴；之前的潜在漏洞是灵敏度曲线未显式包含偶然本底误 VETO。本文已用 100 万 trial 给出数值校正。
  \item 当前阈值仍是窗口计数近似，不是最终 spatial-spectral likelihood。下一步应对焦斑 ROI、单像素/多像素通道、活化线模型和本底连续谱做联合似然。
  \item DIXE 风格的产生体积/产生过程 ancestry 尚未完整保存到每个 accepted TES hit；当前只做到 incident/source stream 分解。
  \item prompt light-curve shape 当前仍为 1.0，应视为可运行基础设施，不应声称已完成真实轨迹时间变化。
\end{{enumerate}}

\section{{给 GPT Pro 的重点复核问题}}
\begin{{enumerate}}
  \item accidental-veto bootstrap 的 rolling-window 几何模型是否足以代表生产 timeline 的候选组合逻辑？
  \item 1.64\% science response 校正是否应只乘到 signal response，还是还应在 profile likelihood 中作为 nuisance parameter？
  \item 510.3--511.8 keV 线窗是否应继续使用 93\% 源保留率，还是改为从 science SIM 的实际能量响应直接积分？
  \item 当前 W-187/活化线残余是否需要优先做核素级 line template，而不是继续调全局 veto？
  \item 后续 likelihood 应如何同时处理聚焦 spot ROI、本底活化线、Compton/FoV 类别和 accidental coincidence？
\end{{enumerate}}

\section{{最终结论}}
当前最可信的表述是：\textbf{{工作流已闭合，science 源已纳入共同时间轴并经过 VETO；新增 accidental-veto 校正显示 science response 需下调约 1.64\%，这只会把点源阈值上调约 1.67\%。}} 校正后，1 Ms、3$\sigma$ 的 511 keV 点源阈值约为宽窗 ${sci_tex(broad_corr_3)}$、窄线窗 ${sci_tex(line_corr_3)}$ ph cm$^{{-2}}$ s$^{{-1}}$。因此，当前模拟仍不支持“$10^{{-4}}$ ph cm$^{{-2}}$ s$^{{-1}}$ 稳态点源 1 Ms 稳健 3$\sigma$ 探测”的最终声称，但已给出可审计、可复现、并经过 accidental-veto 修正的保守科学能力估计。

\section*{{输出文件}}
\begin{{itemize}}
  \item 英文 SCI manuscript: \path{{{SCI_EN.relative_to(WORKSPACE).as_posix()}}}
  \item 中文 SCI manuscript: \path{{{SCI_ZH.relative_to(WORKSPACE).as_posix()}}}
  \item 本审阅包: \path{{cosmosray_bg_2605/reports/gptpro_review_packet/cosmosray_bg_2605_gptpro_review_packet.pdf}}
  \item accidental-veto JSON: \path{{cosmosray_bg_2605/reports/science_accidental_veto/science_accidental_veto_summary.json}}
\end{{itemize}}

\section*{{参考资料}}
\begin{{enumerate}}
  \item 511-CAM: \href{{https://arxiv.org/abs/2206.14652}}{{arXiv:2206.14652}}。
  \item DIXE NXB: \href{{https://doi.org/10.21203/rs.3.rs-8576846/v1}}{{10.21203/rs.3.rs-8576846/v1}}。
  \item INTEGRAL/SPI Observer's Manual: 511 keV 窄线灵敏度外部尺度参考。
\end{{enumerate}}

\end{{document}}
"""
    tex.write_text(body, encoding="utf-8")
    return tex


def update_memory_workflow(pdf: Path, audit: Path):
    marker = "## 2026-05-12 GPT Pro review packet"
    mem_block = f"""

{marker}

- Built GPT Pro review packet PDF with full logic, implementation details, results, accidental-veto correction, corrected sensitivity and remaining caveats: `{pdf.relative_to(WORKSPACE)}`.
- Review packet audit JSON: `{audit.relative_to(WORKSPACE)}`.
- Corrected 1 Ms 3 sigma thresholds after science accidental-veto correction: broad 480-550 about 2.16e-4 ph cm^-2 s^-1; line 510.3-511.8 about 1.36e-4 ph cm^-2 s^-1.
"""
    wf_block = f"""

{marker}

- Use `{pdf.relative_to(WORKSPACE)}` as the current top-level review document for external/GPT Pro inspection.
- Any future report should carry forward the science accidental-veto correction unless a more complete likelihood/timeline signal-injection study supersedes it.
"""
    memory = WORKSPACE / "memory.md"
    workflow = WORKSPACE / "workflow.md"
    mem_text = memory.read_text(encoding="utf-8", errors="ignore")
    wf_text = workflow.read_text(encoding="utf-8", errors="ignore")
    if marker not in mem_text:
        memory.write_text(mem_text.rstrip() + mem_block + "\n", encoding="utf-8")
    if marker not in wf_text:
        workflow.write_text(wf_text.rstrip() + wf_block + "\n", encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    _ = (WORKSPACE / "memory.md").read_text(encoding="utf-8", errors="ignore")
    _ = (WORKSPACE / "workflow.md").read_text(encoding="utf-8", errors="ignore")
    summary = load_json(SUMMARY)
    acc = load_json(ACCIDENTAL)
    tex = write_tex(summary, acc)
    for _ in range(2):
        subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error", tex.name],
            cwd=OUT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    pdf = OUT / "cosmosray_bg_2605_gptpro_review_packet.pdf"
    audit = OUT / "gptpro_review_packet_audit.json"
    broad_corr = acc["windows"]["broad_480_550"]["accidental_survival_correction"]
    line_corr = acc["windows"]["line_510p3_511p8"]["accidental_survival_correction"]
    manuscript_audit = load_json(ROOT / "reports" / "day15_sci_manuscript" / "sci_manuscript_audit.json")
    broad_uncorr_3 = manuscript_audit["broad_480_550"]["flux_3sigma_1Ms"]
    line_uncorr_3 = manuscript_audit["line_window_510p3_511p8"]["flux_3sigma_1Ms"]
    audit.write_text(
        json.dumps(
            {
                "pdf": str(pdf.relative_to(WORKSPACE)),
                "summary": str(SUMMARY.relative_to(WORKSPACE)),
                "accidental_veto": str(ACCIDENTAL.relative_to(WORKSPACE)),
                "broad_correction": broad_corr,
                "line_correction": line_corr,
                "broad_3sigma_1Ms_corrected": broad_uncorr_3 / broad_corr,
                "line_3sigma_1Ms_corrected": line_uncorr_3 / line_corr,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    update_memory_workflow(pdf, audit)
    print(pdf)


if __name__ == "__main__":
    main()
