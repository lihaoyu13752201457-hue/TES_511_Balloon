#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a Chinese translation of the 2605 SCI-style manuscript."""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

import make_sci_manuscript as base


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
INPUT = ROOT / "reports" / "day15_complete_report"
OUT = ROOT / "reports" / "day15_sci_manuscript_zh"
FIG = OUT / "figures"
ACCIDENTAL_JSON = ROOT / "reports" / "science_accidental_veto" / "science_accidental_veto_summary.json"


def zh_table(headers, rows, align=None):
    return base.table(headers, rows, align=align)


def build_tables_zh(summary, line_bkg, line_rsp):
    obs = summary["normalization"]["obs_time_s"]
    counts = summary["timeline_counts_480_550"]
    rates = summary["timeline_rates_cps"]
    veto_rows = [
        ("无 VETO", counts["raw"], base.fmt_pm(rates["raw"], counts["raw"], obs), "1.000"),
        ("BGO VETO 后", counts["bgo"], base.fmt_pm(rates["bgo"], counts["bgo"], obs), base.fmt(rates["bgo"] / rates["raw"], 3)),
        (
            "BGO + Compton/FoV 后",
            counts["final"],
            base.fmt_pm(rates["final"], counts["final"], obs),
            base.fmt(rates["final"] / rates["raw"], 3),
        ),
    ]

    stream_name = {
        "delayed": "延迟活化",
        "prompt": "瞬时宇宙线",
        "mixed": "时间混合",
        "science": "科学源",
    }
    stream_rows = []
    for key in ("delayed", "prompt", "mixed", "science"):
        vals = summary["timeline_rates_by_stream_pure"][key]
        stream_rows.append((stream_name[key], base.fmt(vals["raw"], 4), base.fmt(vals["bgo"], 4), base.fmt(vals["final"], 4)))

    component_rows = []
    for row in sorted(base.read_csv_rows(base.COMP_CSV), key=lambda r: float(r["rate_480_550_keV_cps"]), reverse=True):
        if row["component"] == "Total":
            continue
        component_rows.append(
            (
                row["component"],
                base.fmt(float(row["rate_480_550_keV_cps"]), 4),
                base.fmt(float(row["rate_100_10000_keV_cps"]), 4),
            )
        )

    activation_rows = []
    for row in base.read_csv_rows(base.ACTIVATION_CSV)[:8]:
        activation_rows.append(
            (
                f"{row['VN']}:{row['nuclide']}",
                base.fmt(float(row["hl_s"]), 3),
                base.fmt(float(row["Activity_Bq_after_fix"]), 3),
                base.fmt(float(row["fix_scale"]), 5),
            )
        )

    sci = summary["science_sensitivity"]
    t = 1.0e6
    broad_rsp = sci["science_final_response_cps_per_ph_cm-2_s-1"]
    broad_bkg = sci["background_final_cps_prompt_plus_delayed"]
    sensitivity_rows = [
        (
            "480--550 keV",
            base.fmt(broad_bkg, 4),
            base.fmt(broad_rsp, 4),
            base.fmt(3.0 * math.sqrt(broad_bkg * t) / (broad_rsp * t), 4),
            base.fmt(5.0 * math.sqrt(broad_bkg * t) / (broad_rsp * t), 4),
        ),
        (
            "510.3--511.8 keV",
            base.fmt(line_bkg, 4),
            base.fmt(line_rsp, 4),
            base.fmt(3.0 * math.sqrt(line_bkg * t) / (line_rsp * t), 4),
            base.fmt(5.0 * math.sqrt(line_bkg * t) / (line_rsp * t), 4),
        ),
    ]

    return {
        "veto": zh_table(["筛选阶段", "计数", "率 (cps)", "保留比例"], veto_rows, align="lrrr"),
        "streams": zh_table(["事件流", "无 VETO cps", "BGO 后 cps", "最终 cps"], stream_rows, align="lrrr"),
        "components": zh_table(["成分", "480--550 cps", "100--10000 cps"], component_rows, align="lrr"),
        "activation": zh_table(["体积:核素", "半衰期 (s)", "活度 (Bq)", "修正因子"], activation_rows, align="lrrr"),
        "sensitivity": zh_table(["能窗", "$R_b$ cps", "$R_s$ cps/flux", "3$\\sigma$ 1 Ms", "5$\\sigma$ 1 Ms"], sensitivity_rows, align="lrrrr"),
    }


def write_tex_zh(summary, figs, tables, line_bkg, line_rsp):
    tex = OUT / "cosmosray_bg_2605_sci_manuscript_zh.tex"
    norm = summary["normalization"]
    sci = summary["science_sensitivity"]
    delay = summary["delay_fix"]
    cat = summary["catalog"]
    draw = summary["draw_summary"]

    atm_trans = norm["science_injection_rate_s^-1"] / (base.CAM511["effective_area_cm2"] * norm["science_flux_ph_cm2_s"])
    final_eff = sci["science_reference_final_cps"] / norm["science_injection_rate_s^-1"]
    final_rsp = sci["science_final_response_cps_per_ph_cm-2_s-1"]
    bg_total = summary["timeline_rates_by_kind"]["background_only"]["final"]
    active_area = 20 * 20 * 0.15 * 0.15
    nxb_area = bg_total / active_area
    nxb_density = nxb_area / 70.0
    broad_snr = final_rsp * norm["science_flux_ph_cm2_s"] * 1.0e6 / math.sqrt(sci["background_final_cps_prompt_plus_delayed"] * 1.0e6)
    line_snr = line_rsp * norm["science_flux_ph_cm2_s"] * 1.0e6 / math.sqrt(line_bkg * 1.0e6)
    flux3_line = 3.0 * math.sqrt(line_bkg * 1.0e6) / (line_rsp * 1.0e6)
    flux3_broad = 3.0 * math.sqrt(sci["background_final_cps_prompt_plus_delayed"] * 1.0e6) / (final_rsp * 1.0e6)
    accidental = json.loads(ACCIDENTAL_JSON.read_text(encoding="utf-8")) if ACCIDENTAL_JSON.exists() else None
    broad_acc_corr = accidental["windows"]["broad_480_550"]["accidental_survival_correction"] if accidental else 1.0
    line_acc_corr = accidental["windows"]["line_510p3_511p8"]["accidental_survival_correction"] if accidental else 1.0
    flux3_broad_acc = flux3_broad / broad_acc_corr
    flux3_line_acc = flux3_line / line_acc_corr
    ref_flux_tex = base.sci_tex(norm["science_flux_ph_cm2_s"], 1)
    flux3_broad_tex = base.sci_tex(flux3_broad, 2)
    flux3_line_tex = base.sci_tex(flux3_line, 2)
    flux3_broad_acc_tex = base.sci_tex(flux3_broad_acc, 2)
    flux3_line_acc_tex = base.sci_tex(flux3_line_acc, 2)
    nxb_density_tex = base.sci_tex(nxb_density, 3)

    body = rf"""
\documentclass[11pt,a4paper]{{ctexart}}
\usepackage[a4paper,margin=2.05cm]{{geometry}}
\usepackage{{fontspec,amsmath,amssymb,booktabs,graphicx,float,caption,xurl,hyperref,xcolor}}
\usepackage{{enumitem}}
\setCJKmainfont{{Noto Serif CJK SC}}
\setCJKsansfont{{Noto Sans CJK SC}}
\setmainfont{{TeX Gyre Termes}}
\setsansfont{{TeX Gyre Heros}}
\hypersetup{{colorlinks=true,linkcolor=blue!50!black,urlcolor=blue!50!black,citecolor=blue!50!black}}
\captionsetup{{font=small,labelfont=bf}}
\setlist{{nosep,leftmargin=2em}}
\renewcommand{{\figurename}}{{图}}
\renewcommand{{\tablename}}{{表}}
\title{{气球载聚焦 TES 伽马谱仪的非 X 射线本底与 511 keV 点源灵敏度}}
\author{{COSMOSRAY\_BG\_2605 模拟分析}}
\date{{2026-05-12}}

\begin{{document}}
\maketitle

\begin{{abstract}}
本文给出一个自洽的蒙特卡洛估计，用于评估气球载、聚焦型 511 keV 伽马谱仪的非 X 射线本底。该仪器概念包含 TES 微量热计焦平面和主动 BGO 屏蔽。模拟把物理来源分为三类：大气宇宙线次级粒子形成的瞬时本底、buildup 运行生成的延迟放射性活化本底，以及经外部聚焦光学注入的轴上 511 keV 科学源。瞬时、延迟和科学源事件先被合并到同一个泊松时间轴上，再执行反符合和 Compton/FoV 筛选。对第15天构型，480--550 keV 焦平面本底在无 VETO 时为 {summary["timeline_rates_cps"]["raw"]:.4f} counts s$^{{-1}}$，BGO VETO 后为 {summary["timeline_rates_cps"]["bgo"]:.4f} counts s$^{{-1}}$，完整筛选后为 {summary["timeline_rates_cps"]["final"]:.4f} counts s$^{{-1}}$。参考点源 $F_{{511}}=10^{{-4}}$ ph cm$^{{-2}}$ s$^{{-1}}$ 的最终响应为 {final_rsp:.3f} counts s$^{{-1}}$ per ph cm$^{{-2}}$ s$^{{-1}}$。在本底受限的简单计数近似下，1 Ms 内宽能窗 480--550 keV 的显著性为 {broad_snr:.2f}$\sigma$，CAM511 风格 510.3--511.8 keV 线窗的显著性为 {line_snr:.2f}$\sigma$。未校正的 3$\sigma$、1 Ms 流量阈值分别为 ${flux3_broad_tex}$ 和 ${flux3_line_tex}$ ph cm$^{{-2}}$ s$^{{-1}}$；引入高统计 accidental-veto 校正后分别为 ${flux3_broad_acc_tex}$ 和 ${flux3_line_acc_tex}$ ph cm$^{{-2}}$ s$^{{-1}}$。因此，当前构型已经形成完整可审计的本底与源响应链，但在不进一步优化焦平面 ROI、线型似然或活化线抑制之前，还不能声称对 $10^{{-4}}$ ph cm$^{{-2}}$ s$^{{-1}}$ 的稳态点源达到稳健的 3$\sigma$ 探测。
\end{{abstract}}

\section{{引言}}
银河 511 keV 湮灭线是研究正电子产生、传播和湮灭环境的重要探针。聚焦型 511 keV 望远镜的吸引力在于，它可以把源光子的收集面积与焦平面本底积分面积解耦：光学系统在较大的有效孔径上收集光子，而线本底只在焦斑和被选中的事件类别上积分。这正是 511-CAM 概念的核心仪器逻辑，即把 channeling/Laue 类伽马光学与高能量分辨率 TES 微量热计焦平面结合起来。

对气球载荷而言，主要困难不是科学源没有响应，而是瞬时大气次级粒子和探测器、屏蔽、支撑材料中的延迟活化本底。因此，一个可信的灵敏度估计必须在同一个统计框架中同时处理瞬时本底、活化衰变和科学源。本文报告 \texttt{{cosmosray\_bg\_2605}} 第15天数据集的这一完整处理链。本文目的不是把结果调到某个旧报告数值，而是建立从粒子源定义到最终 511 keV 线灵敏度的可复现科学链条。

\section{{仪器与源模型}}
模拟载荷包含多层 TES 吸收体阵列、低温和结构材料、Be/Al 窗、高 $Z$ 屏蔽/准直结构，以及主动 BGO 屏蔽。焦平面分析使用 TES 中的 event-summed energy。科学源模型遵循 511-CAM 研究中的分工：伽马聚焦光学作为外部响应处理，MEGAlib/Cosima 只负责探测器侧质量模型中的输运。

对轴上单能 511 keV 点源，探测器侧注入面的物理光子率为
\begin{{equation}}
R_\mathrm{{inj}} = F_{{511}}\,A_\mathrm{{eff}}(511)\,T_\mathrm{{atm}},
\end{{equation}}
其中采用的 511-CAM 有效面积为 $A_\mathrm{{eff}}=50.89$ cm$^2$，$T_\mathrm{{atm}}$ 是大气透过率。生产账本给出，当 $F_{{511}}={ref_flux_tex}$ ph cm$^{{-2}}$ s$^{{-1}}$ 时，$R_\mathrm{{inj}}={norm["science_injection_rate_s^-1"]:.6f}$ s$^{{-1}}$，对应 $T_\mathrm{{atm}}={atm_trans:.3f}$。探测器输运和事件筛选后的最终源效率为
\begin{{equation}}
\epsilon_\mathrm{{sel}}=\frac{{R_\mathrm{{sel}}}}{{R_\mathrm{{inj}}}}={final_eff:.3f},
\end{{equation}}
因此最终源响应为 $R_s=A_\mathrm{{eff}}T_\mathrm{{atm}}\epsilon_\mathrm{{sel}}={final_rsp:.3f}$ counts s$^{{-1}}$ per ph cm$^{{-2}}$ s$^{{-1}}$。

\begin{{figure}}[H]
\centering
\includegraphics[width=0.95\linewidth]{{{figs["workflow"].as_posix()}}}
\caption{{端到端模拟逻辑。各物理源流在赋予时间之前保持分离；泊松时间轴合并之后再执行 VETO 和线窗筛选。}}
\end{{figure}}

\section{{瞬时与延迟本底模拟}}
瞬时本底由全空间大气宇宙线粒子场生成，包括光子、中子、质子、$\alpha$ 粒子、电子/正电子和 $\mu^\pm$。活化本底分两步得到：首先，buildup 运行在载荷质量模型中记录放射性同位素产生记录；其次，将同位素清单转换为第15天的延迟衰变源。对产生通道 $j$，若衰变常数为 $\lambda_j$，buildup 和冷却后的活度写为
\begin{{equation}}
A_j(t_0)=P_j\left(1-e^{{-\lambda_jT_\mathrm{{irr}}}}\right)e^{{-\lambda_jT_\mathrm{{cool}}}},
\end{{equation}}
有限观测段中的期望衰变数为
\begin{{equation}}
N_j(\Delta T)=\int_0^{{\Delta T}}A_j(t_0)e^{{-\lambda_jt}}dt
=\frac{{A_j(t_0)}}{{\lambda_j}}\left(1-e^{{-\lambda_j\Delta T}}\right).
\end{{equation}}

关键修正是 W 及邻近活化产物的基态/同核异能态 bookkeeping。修正前 delayed source 总活度为 {delay["old_total_activity_Bq"]:.3f} Bq；修正后为 {delay["new_total_activity_Bq"]:.3f} Bq。source block 数从 {delay["source_blocks_in"]} 降至 {delay["source_blocks_after_fix"]}；审计显示 W-183 和 W-180 基态残留标志均为 false。

\begin{{table}}[H]
\centering
{tables["activation"]}
\caption{{ground-state/isomer 修正后，第15天最大的延迟活化贡献项。}}
\end{{table}}

\begin{{figure}}[H]
\centering
\includegraphics[width=0.82\linewidth]{{{base.ACTIVATION_FIG.as_posix()}}}
\caption{{delayed source 修正后的主要活化成分。511 keV 窗口的剩余残差需要通过核素分解的 delayed 谱继续诊断，其中 W-187 应保留为优先候选。}}
\end{{figure}}

\section{{统一时间轴与事件筛选}}
本分析不是在最后简单相加几个分别归一化的能谱，而是把每个事件流采样到同一个观测时间段：
\begin{{equation}}
N_k \sim \mathrm{{Poisson}}(R_kT_\mathrm{{obs}}), \qquad
t_i \sim U(0,T_\mathrm{{obs}}),
\end{{equation}}
其中 $k$ 表示瞬时、延迟和科学源事件流。位于符合时间窗内的事件先被合并为同一候选组，然后再进行 VETO 判定。这一点是必要的，因为 BGO VETO 和 Compton/FoV 筛选都依赖事件时间与多重性。

本次生产输入包含 {summary["inputs"]["prompt_files"]} 个 prompt 文件、一个 fixed delayed SIM 文件和一个 science SIM 文件。共同观测时间为 $T_\mathrm{{obs}}={norm["obs_time_s"]:.1f}$ s，符合时间窗为 {norm["coincidence_window_s"]:.1e} s，BGO 阈值为 {norm["bgo_threshold_keV"]:.0f} keV。事件目录包含 {cat["events_kept"]:,} 个保留的蒙特卡洛事件和 {cat["pixel_hits_kept"]:,} 个像素 hit。泊松抽样得到 {draw["prompt"]["drawn"]:,} 个 prompt 实例、{draw["delayed"]["drawn"]:,} 个 delayed 实例和 {draw["science"]["drawn"]:,} 个 science 实例。

\section{{结果：非 X 射线本底与 VETO 效果}}
图~\ref{{fig:wide}} 给出宽能段非 X 射线本底谱，图~\ref{{fig:line}} 聚焦 511 keV 分析能段。表~\ref{{tab:veto}} 总结 480--550 keV 积分率的 VETO 效果。BGO VETO 去除了大部分带电粒子和屏蔽符合事件，使 480--550 keV 率降至无 VETO 的 {summary["timeline_rates_cps"]["bgo"]/summary["timeline_rates_cps"]["raw"]:.3f}。进一步的 Compton/FoV 筛选使剩余率降至无 VETO 的 {summary["timeline_rates_cps"]["final"]/summary["timeline_rates_cps"]["raw"]:.3f}。

\begin{{figure}}[H]
\centering
\includegraphics[width=0.92\linewidth]{{{figs["wide"].as_posix()}}}
\caption{{第15天 event-summed TES 宽能段谱。}}
\label{{fig:wide}}
\end{{figure}}

\begin{{figure}}[H]
\centering
\includegraphics[width=0.92\linewidth]{{{figs["line"].as_posix()}}}
\caption{{511 keV 分析能段：无 VETO、BGO VETO 后和完整 BGO+Compton/FoV 筛选后的谱。}}
\label{{fig:line}}
\end{{figure}}

\begin{{table}}[H]
\centering
{tables["veto"]}
\caption{{统一泊松时间轴上 480--550 keV 积分计数率。误差仅为该 realization 的泊松计数误差，不含系统误差。}}
\label{{tab:veto}}
\end{{table}}

在最终筛选后的 480--550 keV 本底中，延迟活化占主导，但瞬时成分仍不可忽略。mixed 类别来自同一符合组内同时包含 prompt/delayed/science 实例的事件；如果只做能谱级相加，这部分会被遗漏。

\begin{{figure}}[H]
\centering
\includegraphics[width=0.90\linewidth]{{{figs["streams"].as_posix()}}}
\caption{{统一时间轴上各事件流在不同筛选阶段的贡献。}}
\end{{figure}}

\begin{{table}}[H]
\centering
{tables["streams"]}
\caption{{480--550 keV 能段中的时间轴事件流分解。}}
\end{{table}}

\section{{DIXE 风格的本底归一化}}
DIXE 非 X 射线本底论文使用 counts s$^{{-1}}$ cm$^{{-2}}$，以及在微分谱中使用 counts s$^{{-1}}$ cm$^{{-2}}$ keV$^{{-1}}$。其球面源归一化可写为
\begin{{equation}}
B_i=\frac{{4\pi^2 C_i R_\mathrm{{int}}^2\Phi}}{{N A_\mathrm{{det}}\Delta E_i}},
\end{{equation}}
当地球遮挡或反照可见性限制入射场时，还需要引入固角因子。本项目使用 MEGAlib 源归一化，而不是 DIXE 中完全相同的 Geant4 球面源估计器；但最终结果可以写成相同单位，便于比较统计量定义。

若 TES 主动投影面积取 $20\times20\times(0.15\,\mathrm{{cm}})^2={active_area:.2f}$ cm$^2$，则最终 background-only 的 480--550 keV 率 {bg_total:.4f} counts s$^{{-1}}$ 对应
\begin{{equation}}
{nxb_area:.4f}\ \mathrm{{counts\ s^{{-1}}\ cm^{{-2}}}},
\end{{equation}}
在 70 keV 窗口内等效为
\begin{{equation}}
{nxb_density_tex}\ \mathrm{{counts\ s^{{-1}}\ cm^{{-2}}\ keV^{{-1}}}}.
\end{{equation}}
这只是统计口径上的类比，而不是与 DIXE 做直接物理排序。DIXE 研究的是低地球轨道 0.1--10 keV 载荷；本文研究的是气球 511 keV 线实验，并包含主动屏蔽和聚焦源模型。

\begin{{figure}}[H]
\centering
\includegraphics[width=0.90\linewidth]{{{figs["components"].as_posix()}}}
\caption{{VETO 前的入射/源成分计数率账本。这是当前最接近 DIXE 式源类别分解的结果；若要进一步分解产生过程和产生体积，需要额外保存 hit ancestry。}}
\end{{figure}}

\begin{{table}}[H]
\centering
{tables["components"]}
\caption{{VETO 前的 direct-expectation 成分计数率。}}
\end{{table}}

\section{{511 keV 点源灵敏度}}
在本底受限的线计数近似下，探测到的源计数和本底计数为
\begin{{equation}}
N_s=F_{{511}}R_sT,\qquad N_b=R_bT,
\end{{equation}}
近似显著性为
\begin{{equation}}
\mathrm{{SNR}}\simeq\frac{{N_s}}{{\sqrt{{N_b}}}}.
\end{{equation}}
对应的流量阈值为
\begin{{equation}}
F_{{n\sigma}}=\frac{{n\sqrt{{R_bT}}}}{{R_sT}}.
\end{{equation}}
这与 CAM511 Fig. 11 风格的 source/background count 灵敏度估计具有相同统计结构。对宽能窗 480--550 keV，取 $R_b={sci["background_final_cps_prompt_plus_delayed"]:.4f}$ counts s$^{{-1}}$，$R_s={final_rsp:.4f}$ counts s$^{{-1}}$ per ph cm$^{{-2}}$ s$^{{-1}}$。对线窗估计，将最终本底在 510.3--511.8 keV 中积分，得到 $R_b={line_bkg:.4f}$ counts s$^{{-1}}$，并保守采用 93\% 的源保留率，得到 $R_s={line_rsp:.4f}$ counts s$^{{-1}}$ per ph cm$^{{-2}}$ s$^{{-1}}$。

统一时间轴 realization 中确实包含 science stream：在 {norm["obs_time_s"]:.1f} s 的运行中，科学源期望实例数为 {draw["science"]["lambda"]:.3f}，实际泊松抽样得到 {draw["science"]["drawn"]} 个实例，并且这些实例与本底一起经过同一套 BGO 和 Compton/FoV 逻辑。可是，灵敏度曲线没有使用这一次低计数 science realization；它使用的是 event-wise BGO 和 Compton/FoV 筛选后的 direct-expectation 源响应。因此，本文给出的阈值应理解为 Asimov/window-counting 估计。专门的高统计 bootstrap 给出宽窗 accidental survival correction {broad_acc_corr:.6f}、线窗 {line_acc_corr:.6f}；应用该校正后，3$\sigma$/1 Ms 阈值上调为 ${flux3_broad_acc_tex}$ 和 ${flux3_line_acc_tex}$ ph cm$^{{-2}}$ s$^{{-1}}$。下一步 spatial-spectral likelihood 应把该项作为显式 signal-efficiency correction。

\begin{{table}}[H]
\centering
{tables["sensitivity"]}
\caption{{本底受限近似下 1 Ms 点源流量阈值。流量单位为 ph cm$^{{-2}}$ s$^{{-1}}$。}}
\end{{table}}

\begin{{figure}}[H]
\centering
\includegraphics[width=0.88\linewidth]{{{figs["counts"].as_posix()}}}
\caption{{参考点源 $F_{{511}}=10^{{-4}}$ ph cm$^{{-2}}$ s$^{{-1}}$ 在 1 Ms 内的源计数和本底计数。}}
\end{{figure}}

\begin{{figure}}[H]
\centering
\includegraphics[width=0.92\linewidth]{{{figs["sensitivity"].as_posix()}}}
\caption{{点源灵敏度随曝光时间的变化。SPI manual 的窄线参考点只作为外部尺度标记；不同仪器概念和本底环境不能直接等同。}}
\end{{figure}}

\section{{讨论}}
模拟给出三个主要结论。第一，BGO 屏蔽有效，但单独依靠 BGO 还不足以完成 511 keV 点源测量；延迟活化仍是最终筛选后的主导残余成分。第二，统一时间轴合并不是可选步骤。它产生 mixed coincidence groups，并保证 BGO 与 Compton/FoV VETO 作用在有物理意义的时间组上，而不是作用在分别累积的直方图上。第三，聚焦源响应已经足以让 $10^{{-4}}$ ph cm$^{{-2}}$ s$^{{-1}}$ 量级的源在模拟探测器响应中显现，但当前使用整个焦平面和简单线窗计数时，本底仍然过高，尚不足以在 1 Ms 内给出稳健的 3$\sigma$ 声称。

达不到 $10^{{-4}}$ ph cm$^{{-2}}$ s$^{{-1}}$、3$\sigma$ 探测并不意味着聚焦概念失败。更合理的解释是，当前估计刻意保守：它积分了较宽的焦平面本底，使用简单线窗计数而不是线型似然，也尚未优化空间 ROI、边缘像素剔除、BGO 阈值、单像素/Compton 类别似然，以及核素特异的 delayed-line 抑制。CAM511 的优势应通过这些优化来检验，因为其物理杠杆正是收集面积与本底积分面积的分离。

当前 DIXE 风格成分账本在 hit ancestry 层面也还不完整。DIXE 区分 incident/induced particles、产生体积和产生过程。本文区分了瞬时粒子类别、延迟活化和科学源响应，但尚未为每个被接受的 TES hit 保存完整 parent-process 表。在声称达到 DIXE 级本底分类之前，应补上这部分 bookkeeping。

\section{{结论}}
本文给出一个闭合、可复现的第15天非 X 射线本底与 511 keV 点源灵敏度分析，适用于气球载聚焦 TES 伽马谱仪。统一泊松时间轴上，最终筛选后的 480--550 keV 本底为 {summary["timeline_rates_cps"]["final"]:.4f} counts s$^{{-1}}$，其中延迟活化是主导残余成分。修正后的 delayed source 移除了此前识别出的 W-183/W-180 基态/同核异能态错误，并且不再含有这些基态残留 source blocks。

对稳态轴上点源，当前模型给出的 accidental-veto 校正后 3$\sigma$、1 Ms 阈值为：480--550 keV 宽窗 ${flux3_broad_acc_tex}$ ph cm$^{{-2}}$ s$^{{-1}}$，510.3--511.8 keV 线窗 ${flux3_line_acc_tex}$ ph cm$^{{-2}}$ s$^{{-1}}$。因此，当前数据集已经支持一个有科学意义的灵敏度估计，但还不能作为最终 mission-level 结论来声称 $10^{{-4}}$ ph cm$^{{-2}}$ s$^{{-1}}$ 稳态点源可在 1 Ms 内以 $\ge3\sigma$ 被探测。下一步应把窗口计数替换为空间-能谱联合似然，并显式优化焦斑 ROI 与活化线抑制。

\section*{{数据与可复现性}}
\begin{{itemize}}
  \item 摘要和能谱：\path{{cosmosray_bg_2605/reports/day15_complete_report/complete_day15_summary.json}} 及同目录 CSV 文件。
  \item 修正后的 delayed source：\path{{production_runs/delay_fix_from_buildup_equiv2602/activation_decay_day15_groundstate_fixed.source}}。
  \item 中文稿生成脚本：\path{{cosmosray_bg_2605/tools/make_sci_manuscript_zh.py}}。
\end{{itemize}}

\section*{{参考文献}}
\begin{{enumerate}}
  \item F. Shirazi et al., \emph{{The 511-CAM Mission: A Pointed 511 keV Gamma-Ray Telescope with a Focal Plane Detector Made of Stacked Transition Edge Sensor Microcalorimeter Arrays}}, arXiv:{base.CAM511["arxiv"]}.
  \item DIXE Collaboration, \emph{{Simulation of non X-ray background for the DIffuse X-ray Explorer mission}}, DOI: \href{{https://doi.org/{base.DIXE["doi"]}}}{{{base.DIXE["doi"]}}}.
  \item INTEGRAL/SPI Observer's Manual, 511 keV 附近窄线灵敏度参考。
\end{{enumerate}}

\end{{document}}
"""
    tex.write_text(body, encoding="utf-8")
    return tex


def update_memory_and_workflow(pdf_path: Path):
    marker = "## 2026-05-12 SCI manuscript Chinese translation update"
    mem_block = f"""

{marker}

- Added Chinese translation PDF for the SCI-style day-15 manuscript: `{pdf_path.relative_to(WORKSPACE)}`.
- The Chinese version keeps the same audited values as the English manuscript: final 480-550 keV rate 5.6443 cps, 3 sigma 1 Ms thresholds about 2.12e-4 and 1.33e-4 ph cm^-2 s^-1 for broad and line windows.
"""
    wf_block = f"""

{marker}

- Keep English and Chinese SCI manuscript PDFs in parallel: English under `day15_sci_manuscript/`, Chinese under `day15_sci_manuscript_zh/`.
- When updating one language, regenerate the other from the same summary/audit inputs to avoid numerical drift.
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
    FIG.mkdir(parents=True, exist_ok=True)
    _ = (WORKSPACE / "memory.md").read_text(encoding="utf-8", errors="ignore")
    _ = (WORKSPACE / "workflow.md").read_text(encoding="utf-8", errors="ignore")

    base.OUT = OUT
    base.FIG = FIG
    summary = base.read_json(base.SUMMARY)
    zoom = base.load_numeric_csv(base.ZOOM_CSV)
    main_csv = base.load_numeric_csv(base.MAIN_CSV)
    line_bkg = base.integrate_window(zoom, "expectation_final_cps_per_bin", 510.3, 511.8, 0.5)
    line_rsp = summary["science_sensitivity"]["science_final_response_cps_per_ph_cm-2_s-1"] * base.CAM511["detected_line_fraction"]

    figs = {
        "workflow": base.plot_workflow(),
        "wide": base.plot_wide_spectrum(main_csv),
        "line": base.plot_line_window(zoom),
        "streams": base.plot_stream_decomposition(summary),
        "components": base.plot_component_bars(),
        "counts": base.plot_cam_counts(summary, line_bkg, line_rsp),
        "sensitivity": base.plot_sensitivity(summary, line_bkg, line_rsp),
    }
    tables = build_tables_zh(summary, line_bkg, line_rsp)
    tex = write_tex_zh(summary, figs, tables, line_bkg, line_rsp)

    audit = {
        "pdf": str((OUT / "cosmosray_bg_2605_sci_manuscript_zh.pdf").relative_to(WORKSPACE)),
        "script": str((ROOT / "tools" / "make_sci_manuscript_zh.py").relative_to(WORKSPACE)),
        "source_language_pdf": str((ROOT / "reports" / "day15_sci_manuscript" / "cosmosray_bg_2605_sci_manuscript.pdf").relative_to(WORKSPACE)),
        "input_summary": str(base.SUMMARY.relative_to(WORKSPACE)),
        "translation": "Chinese translation with same audited numerical inputs as the English SCI manuscript.",
        "line_window_510p3_511p8": {
            "background_cps": line_bkg,
            "source_response_cps_per_ph_cm2_s": line_rsp,
            "flux_3sigma_1Ms": 3.0 * math.sqrt(line_bkg * 1.0e6) / (line_rsp * 1.0e6),
            "flux_5sigma_1Ms": 5.0 * math.sqrt(line_bkg * 1.0e6) / (line_rsp * 1.0e6),
        },
    }
    (OUT / "sci_manuscript_zh_audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")

    for _ in range(2):
        subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error", tex.name],
            cwd=OUT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

    pdf = OUT / "cosmosray_bg_2605_sci_manuscript_zh.pdf"
    update_memory_and_workflow(pdf)
    print(pdf)


if __name__ == "__main__":
    main()
