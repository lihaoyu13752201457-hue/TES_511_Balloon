from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path
from textwrap import wrap

os.environ.setdefault("MPLCONFIGDIR", "/tmp/opticsim_mpl")

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "opticsim_progress_report.pdf"
ASSETS = ROOT / "reports" / "assets"

FONT_REG = FontProperties(fname="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
FONT_BOLD = FontProperties(fname="/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")

plt.rcParams["axes.unicode_minus"] = False


def load_json(path: str | Path):
    with (ROOT / path).open() as f:
        return json.load(f)


def cn_text(ax, x, y, text, size=11, bold=False, color="#111827", ha="left", va="top", width=None, line_spacing=1.25):
    font = FONT_BOLD if bold else FONT_REG
    if width:
        lines: list[str] = []
        for para in text.split("\n"):
            if not para:
                lines.append("")
            else:
                lines.extend(wrap(para, width=width))
        text = "\n".join(lines)
    return ax.text(
        x,
        y,
        text,
        transform=ax.transAxes,
        fontproperties=font,
        fontsize=size,
        color=color,
        ha=ha,
        va=va,
        linespacing=line_spacing,
    )


def title(ax, text, subtitle=None):
    ax.set_axis_off()
    cn_text(ax, 0.05, 0.94, text, size=24, bold=True, color="#0f172a")
    if subtitle:
        cn_text(ax, 0.05, 0.885, subtitle, size=12.5, color="#475569")


def metric_box(ax, x, y, w, h, label, value, note="", color="#eff6ff"):
    box = FancyBboxPatch(
        (x, y),
        w,
        h,
        transform=ax.transAxes,
        boxstyle="round,pad=0.014,rounding_size=0.018",
        linewidth=0.8,
        edgecolor="#cbd5e1",
        facecolor=color,
    )
    ax.add_patch(box)
    cn_text(ax, x + 0.03 * w, y + h - 0.23 * h, label, size=9.5, color="#475569")
    cn_text(ax, x + 0.03 * w, y + h - 0.52 * h, value, size=17, bold=True, color="#0f172a")
    if note:
        cn_text(ax, x + 0.03 * w, y + 0.14 * h, note, size=8.5, color="#64748b")


def draw_workflow(ax):
    ax.set_axis_off()
    boxes = [
        (0.05, 0.68, "指导文档\nMD/PDF", "#f8fafc"),
        (0.28, 0.68, "Python channel\nray tracer", "#eff6ff"),
        (0.51, 0.68, "W/Si 反射率表\nxraydb", "#f0fdf4"),
        (0.74, 0.68, "4-ring effective\nmodel", "#fff7ed"),
        (0.28, 0.33, "Laue toy\nBragg geometry", "#fefce8"),
        (0.51, 0.33, "phase_space.csv\n-> detector-only", "#f5f3ff"),
        (0.74, 0.33, "Geant4 two-wall\nboundary demo", "#fdf2f8"),
    ]
    centers = {}
    for x, y, txt, color in boxes:
        w, h = 0.17, 0.15
        patch = FancyBboxPatch(
            (x, y),
            w,
            h,
            transform=ax.transAxes,
            boxstyle="round,pad=0.02,rounding_size=0.02",
            linewidth=1.0,
            edgecolor="#94a3b8",
            facecolor=color,
        )
        ax.add_patch(patch)
        cn_text(ax, x + w / 2, y + h / 2 + 0.025, txt, size=10.5, bold=True, ha="center", va="center")
        centers[txt.split("\n")[0]] = (x + w, y + h / 2)
    arrows = [
        ((0.22, 0.755), (0.28, 0.755)),
        ((0.45, 0.755), (0.51, 0.755)),
        ((0.68, 0.755), (0.74, 0.755)),
        ((0.365, 0.68), (0.58, 0.48)),
        ((0.82, 0.68), (0.82, 0.48)),
        ((0.68, 0.405), (0.74, 0.405)),
        ((0.365, 0.33), (0.51, 0.405)),
    ]
    for a, b in arrows:
        ax.add_patch(FancyArrowPatch(a, b, transform=ax.transAxes, arrowstyle="-|>", mutation_scale=12, color="#64748b", linewidth=1.2))


def add_image(ax, image_path: str | Path, title_text: str):
    ax.set_axis_off()
    path = ROOT / image_path
    if path.exists():
        img = mpimg.imread(path)
        ax.imshow(img)
        ax.set_title(title_text, fontproperties=FONT_BOLD, fontsize=11, pad=8)
    else:
        cn_text(ax, 0.5, 0.5, f"缺少图像：{image_path}", size=11, ha="center", va="center")


def plot_reflectivity(ax):
    rows = []
    with (ROOT / "data/reflectivity/WSi_511keV_parratt_grid.csv").open(newline="") as f:
        for row in csv.DictReader(f):
            rows.append((float(row["theta_rad"]), float(row["R"]), float(row["A"]), float(row["T"])))
    theta = [r[0] for r in rows]
    R = [r[1] for r in rows]
    A = [r[2] for r in rows]
    T = [r[3] for r in rows]
    ax.semilogx(theta, R, label="R 反射", color="#2563eb", linewidth=2)
    ax.semilogx(theta, A, label="A 吸收", color="#dc2626", linewidth=1.4)
    ax.semilogx(theta, T, label="T 泄漏", color="#16a34a", linewidth=1.4)
    ax.axvline(1.496e-4, color="#7c3aed", linestyle="--", linewidth=1.2, label="~1.496e-4 rad")
    ax.set_xlabel("grazing angle [rad]", fontproperties=FONT_REG)
    ax.set_ylabel("probability", fontproperties=FONT_REG)
    ax.set_title("511 keV W/Si 30/150 nm 反射率候选表", fontproperties=FONT_BOLD, fontsize=11)
    ax.grid(True, alpha=0.25)
    ax.legend(prop=FONT_REG, fontsize=8)


def plot_per_ring(ax, per_ring):
    labels = [f"R{row['ring_id']}\n{row['radius_cm']}cm" for row in per_ring]
    values = [row["transmissivity"] for row in per_ring]
    bars = ax.bar(labels, values, color=["#2563eb", "#16a34a", "#f97316", "#7c3aed"], alpha=0.85)
    ax.axhline(0.8, color="#dc2626", linestyle="--", linewidth=1.2, label="目标 0.80")
    ax.set_ylim(0.72, 0.84)
    ax.set_ylabel("transmissivity", fontproperties=FONT_REG)
    ax.set_title("4-ring 每环生存率", fontproperties=FONT_BOLD, fontsize=11)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(prop=FONT_REG, fontsize=8)
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.004,
            f"{value:.3f}",
            ha="center",
            va="bottom",
            fontproperties=FONT_REG,
            fontsize=8,
        )


def plot_ring_contribution(ax, per_ring):
    labels = [f"R{row['ring_id']}" for row in per_ring]
    values = [row["effective_area_contribution_cm2"] for row in per_ring]
    ax.bar(labels, values, color="#0ea5e9", alpha=0.85)
    ax.set_ylabel("cm$^2$")
    ax.set_title("有效面积贡献", fontproperties=FONT_BOLD, fontsize=11)
    ax.grid(axis="y", alpha=0.25)
    for i, v in enumerate(values):
        ax.text(i, v + 0.25, f"{v:.2f}", ha="center", fontproperties=FONT_REG, fontsize=8)


def plot_calibration(ax, calibration):
    labels = [f"R{row['ring_id']}" for row in calibration]
    theta = [row["theta_rad"] * 1e4 for row in calibration]
    ax.plot(labels, theta, marker="o", color="#7c3aed", linewidth=2)
    ax.set_ylabel("theta [1e-4 rad]", fontproperties=FONT_REG)
    ax.set_title("每环校准 grazing angle", fontproperties=FONT_BOLD, fontsize=11)
    ax.grid(True, alpha=0.25)
    for i, v in enumerate(theta):
        ax.text(i, v + 0.002, f"{v:.4f}", ha="center", fontproperties=FONT_REG, fontsize=8)


def draw_table(ax, headers, rows, title_text=None, fontsize=8.5):
    ax.set_axis_off()
    if title_text:
        cn_text(ax, 0.0, 1.0, title_text, size=12, bold=True)
    table = ax.table(cellText=rows, colLabels=headers, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(fontsize)
    table.scale(1, 1.35)
    for _, cell in table.get_celld().items():
        cell.get_text().set_fontproperties(FONT_REG)
        cell.set_edgecolor("#cbd5e1")
    for i in range(len(headers)):
        table[(0, i)].get_text().set_fontproperties(FONT_BOLD)
        table[(0, i)].set_facecolor("#e2e8f0")


def build_pdf():
    channel = load_json("runs/channel_4ring_calibrated_v2/summary.json")
    per_ring = load_json("runs/channel_4ring_calibrated_v2/per_ring_summary.json")
    calibration = load_json("runs/channel_4ring_calibrated_v2/ring_theta_calibration.json")
    detector = load_json("runs/detector_only_4ring_calibrated_v2/summary.json")
    geant_detector = load_json("runs/geant4_detector_only_1k/summary.json")
    io_contract = load_json("runs/io_contract_validation/summary.json")
    geant_io_contract = load_json("runs/io_contract_validation_geant4_detector_1k/summary.json")
    wsi_cross = load_json("runs/wsi_parratt_crosscheck/summary.json")
    geant_laue = load_json("runs/geant4_laue_one_ring/summary.json")
    geant_laue_contract = load_json("runs/io_contract_validation_geant4_laue_one_ring/summary.json")
    geant_channel = load_json("runs/geant4_channel_4ring_effective/summary.json")
    geant_channel_contract = load_json("runs/io_contract_validation_geant4_channel_4ring_effective/summary.json")
    geant_two_wall_table = load_json("runs/geant4_channel_two_wall_table/summary.json")
    geant_single_curved = load_json("runs/geant4_channel_single_curved_bend12m_constant/summary.json")
    geant_single_curved_table = load_json("runs/geant4_channel_single_curved_bend12m_table/summary.json")
    geant_single_curved_scan = load_json("runs/geant4_channel_single_curved_scan/summary.json")
    geant_single_curved_gap_scan = load_json("runs/geant4_channel_single_curved_gap_scan/summary.json")
    channel_geometry_constraints = load_json("runs/channel_geometry_constraints/summary.json")
    channel_bounce_path = load_json("runs/channel_bounce_path_reconciliation/summary.json")
    baseline = load_json("reports/baseline/baseline_metrics.json")
    audit = load_json("reports/project_audit/audit_summary.json")
    laue = load_json("runs/laue_toy/summary.json")
    fixed = load_json("runs/channel_4ring_parratt/summary.json")
    bad_policy = load_json("runs/channel_4ring_ring_bending_per_bounce/summary.json")

    with PdfPages(OUT) as pdf:
        fig = plt.figure(figsize=(11.69, 8.27), dpi=150)
        ax = fig.add_axes([0, 0, 1, 1])
        title(ax, "500-511 keV 聚焦光学模拟阶段报告", "Codex 已完成实现、验证结果与下一步路线")
        cn_text(
            ax,
            0.05,
            0.80,
            "本报告汇总当前 opticsim 工作区已经实现的内容。重点是：先复现可验证的 511-CAM channel optics Python 基线，"
            "引入 W/Si 反射率候选表，完成显式 4-ring effective model，接上 detector-only TES/BGO 后端，"
            "并搭建可编译运行的 Geant4 two-wall table-driven 边界反射 demo。",
            size=12,
            width=58,
        )
        metric_box(ax, 0.05, 0.55, 0.2, 0.16, "4-ring transmissivity", f"{channel['transmissivity']:.5f}", "目标约 0.80")
        metric_box(ax, 0.29, 0.55, 0.2, 0.16, "effective area", f"{channel['effective_area_cm2']:.3f} cm²", "目标 50.89 cm²", "#f0fdf4")
        metric_box(ax, 0.53, 0.55, 0.2, 0.16, "focal spot d90", f"{channel['spot_d90_cm']:.3f} cm", "目标 3.6 cm", "#fff7ed")
        metric_box(ax, 0.77, 0.55, 0.18, 0.16, "tests", "27 OK", "Python + CMake", "#f5f3ff")
        cn_text(
            ax,
            0.05,
            0.40,
            "核心判断：目前的 4-ring 结果是 effective model，不是最终完整 Geant4 4-ring 真实通道几何。"
            "但它已经把文档中的关键验收量压到目标附近，并且明确暴露了一个重要物理约束：不能把总弯曲角直接当作局部 grazing angle 查表。",
            size=11,
            width=72,
        )
        cn_text(
            ax,
            0.05,
            0.22,
            "主要产物：Python ray tracer、W/Si xraydb 反射率表、per-ring 诊断、Laue toy baseline、"
            "detector-only TES/BGO hits/event_summary、分步 IO contract 校验、独立 Parratt cross-check、Geant4 table-driven two-wall channel nucleus、single curved channel v0、gap scan、geometry constraint、bounce/path reconciliation、Geant4 Laue/channel/detector scaffolds、27 项测试、可复现实验输出。",
            size=11,
            width=72,
        )
        cn_text(ax, 0.05, 0.06, f"PDF: {OUT}", size=8.5, color="#64748b")
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        fig = plt.figure(figsize=(11.69, 8.27), dpi=150)
        ax = fig.add_axes([0, 0, 1, 1])
        title(ax, "实现架构", "从指导文档到 Python 基线、物理表、4-ring 诊断与 Geant4 边界过程")
        flow_ax = fig.add_axes([0.04, 0.14, 0.92, 0.66])
        draw_workflow(flow_ax)
        cn_text(
            ax,
            0.06,
            0.10,
            "实现纪律：单位写入变量名；随机数支持 seed；反射率查表禁止静默外推；toy/calibrated 模型在输出中明确标记。",
            size=10.5,
            width=80,
        )
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        fig = plt.figure(figsize=(11.69, 8.27), dpi=150)
        ax = fig.add_axes([0, 0, 1, 1])
        title(ax, "分步模拟接口契约", "不强行拼接 optics 与 TES/BGO mass model，而是用标准表交接")
        cn_text(
            ax,
            0.06,
            0.78,
            "当前路线把聚焦光学和 detector-only 响应拆成独立模拟阶段。"
            "阶段间只共享 phase_space、optics_history、hits、event_summary 这些表，"
            "因此后续可以把 Python optics 替换成 Geant4 optics，或把 Python detector 替换成 Geant4 detector-only，而不需要重写另一端。",
            size=12,
            width=80,
        )
        rows = [
            [
                result["table"],
                "PASS" if result["ok"] else "FAIL",
                f"{result['n_rows']}",
                f"{len(result['extra_columns'])} diagnostic cols" if result["extra_columns"] else "-",
            ]
            for result in io_contract["results"]
        ]
        contract_ax = fig.add_axes([0.06, 0.30, 0.88, 0.34])
        draw_table(contract_ax, ["table", "status", "rows", "extra columns"], rows, fontsize=8.2)
        cn_text(
            ax,
            0.07,
            0.20,
            f"总体状态：{'PASS' if io_contract['ok'] else 'FAIL'}。"
            "event_summary 的 status/x_det/y_det/in_line/selected 等列是向后兼容的诊断扩展；"
            "指导 MD 要求的最小字段仍完整存在。",
            size=10.8,
            width=82,
        )
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        fig = plt.figure(figsize=(11.69, 8.27), dpi=150)
        ax = fig.add_axes([0, 0, 1, 1])
        title(ax, "W/Si Parratt Cross-check", "不再只信任 xraydb multilayer solver，加入本地 Parratt recursion 对照")
        metric_box(ax, 0.06, 0.70, 0.20, 0.14, "rows", f"{wsi_cross['n_rows']}", "theta grid")
        metric_box(ax, 0.30, 0.70, 0.20, 0.14, "max |delta R|", f"{wsi_cross['max_abs_delta_R']:.1e}", "manual vs reference", "#f0fdf4")
        metric_box(ax, 0.54, 0.70, 0.20, 0.14, "status", wsi_cross["status"], "511 keV W/Si", "#fff7ed")
        cross_ax = fig.add_axes([0.12, 0.16, 0.76, 0.46])
        add_image(cross_ax, "runs/wsi_parratt_crosscheck/parratt_crosscheck.png", "W/Si 反射率表交叉验证")
        cn_text(
            ax,
            0.08,
            0.08,
            "说明：manual Parratt recursion 不调用 xraydb.multilayer_reflectivity，只用 xraydb 的材料 optical constants。"
            "这闭合了表生成算法的交叉验证；若要支撑 publication-level 物理声明，下一步仍应加入 IMD/DarpanX 或独立 optical constants provenance。",
            size=10.2,
            width=92,
        )
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        fig = plt.figure(figsize=(11.69, 8.27), dpi=150)
        ax = fig.add_axes([0, 0, 1, 1])
        title(ax, "Geant4 Two-wall Table-driven Channel", "第一块 optics-mainline physics refinement：per-bounce W/Si R/A/T lookup")
        metric_box(ax, 0.05, 0.70, 0.20, 0.14, "theta", f"{geant_two_wall_table['theta_rad']:.2e} rad", "controlled grazing")
        metric_box(ax, 0.29, 0.70, 0.20, 0.14, "R/A/T", f"{geant_two_wall_table['expected_R']:.3f} / {geant_two_wall_table['expected_A']:.3f} / {geant_two_wall_table['expected_T']:.3f}", "W/Si table", "#f0fdf4")
        metric_box(ax, 0.53, 0.70, 0.20, 0.14, "survival", f"{geant_two_wall_table['survival_fraction']:.3f}", "two-bounce scale", "#fff7ed")
        metric_box(ax, 0.77, 0.70, 0.18, 0.14, "boundary rows", f"{geant_two_wall_table['n_boundary']}", "optics_history", "#f5f3ff")
        table_ax = fig.add_axes([0.07, 0.34, 0.48, 0.24])
        tw_rows = [
            ["reflect", f"{geant_two_wall_table['n_reflect']}"],
            ["absorb", f"{geant_two_wall_table['n_absorb']}"],
            ["leak", f"{geant_two_wall_table['n_leak']}"],
            ["survived", f"{geant_two_wall_table['n_survived']}"],
        ]
        draw_table(table_ax, ["action/count", "events or bounces"], tw_rows, "Boundary action accounting", fontsize=8.5)
        base_ax = fig.add_axes([0.61, 0.31, 0.30, 0.28])
        base_rows = [
            ["Python 4-ring T", f"{baseline['channel_python']['transmissivity']:.5f}"],
            ["G4 effective T", f"{baseline['geant4_channel_effective']['transmissivity']:.5f}"],
            ["W/Si xcheck", baseline["wsi_crosscheck"]["status"]],
        ]
        draw_table(base_ax, ["frozen baseline", "value"], base_rows, "Regression guard", fontsize=8.2)
        cn_text(
            ax,
            0.07,
            0.17,
            "这一步不是最终曲面通道，而是把 Geant4 boundary process 从常数 toy 推进到 CSV 反射率表驱动。"
            "每个 boundary hit 都记录 grazing angle、R/A/T、入射/出射方向、位置和 action；下一步应把同一过程放入 segmented curved-wall channel geometry。",
            size=10.5,
            width=92,
        )
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        fig = plt.figure(figsize=(11.69, 8.27), dpi=150)
        ax = fig.add_axes([0, 0, 1, 1])
        title(ax, "Geant4 Single Curved Channel v0", "segmented curved-wall geometry using the same table-driven boundary process")
        metric_box(ax, 0.05, 0.70, 0.20, 0.14, "R=1 survival", f"{geant_single_curved['survival_fraction']:.3f}", "constant reflector")
        metric_box(ax, 0.29, 0.70, 0.20, 0.14, "bounces/event", f"{geant_single_curved['max_boundary_per_event']}", "64 segments, 12 m bend", "#f0fdf4")
        metric_box(ax, 0.53, 0.70, 0.20, 0.14, "mean grazing", f"{geant_single_curved['mean_grazing_angle_rad']:.2e}", "diagnostic", "#fff7ed")
        metric_box(ax, 0.77, 0.70, 0.18, 0.14, "table survival", f"{geant_single_curved_table['survival_fraction']:.3f}", "W/Si table", "#f5f3ff")
        curve_ax = fig.add_axes([0.07, 0.31, 0.48, 0.28])
        curve_rows = [
            ["constant reflect", f"{geant_single_curved['n_reflect']}"],
            ["constant survived", f"{geant_single_curved['n_survived']} / {geant_single_curved['n_primaries']}"],
            ["table absorb", f"{geant_single_curved_table['n_absorb']}"],
            ["table leak", f"{geant_single_curved_table['n_leak']}"],
        ]
        draw_table(curve_ax, ["diagnostic", "value"], curve_rows, "Single curved run", fontsize=8.5)
        risk_ax = fig.add_axes([0.61, 0.31, 0.30, 0.28])
        curve_risk_rows = [
            ["done", "curved segmented volumes + history"],
            ["found", "12 m bend gives large local theta"],
            ["not done", "segment convergence / 4-ring"],
        ]
        draw_table(risk_ax, ["state", "meaning"], curve_risk_rows, "Boundary", fontsize=8.0)
        cn_text(
            ax,
            0.07,
            0.16,
            "结论：单根 curved-wall Geant4 v0 已经能用同一个 GammaChannelReflection 过程记录反射历史。"
            "同时它暴露了下一步必须解决的真实问题：12 m bend 配置下局部 grazing angle 仍偏大，不能直接拿当前 W/Si 表得到有效 throughput。"
            "下一步应做 segment-convergence/debug boundary study，而不是用调参掩盖。",
            size=10.4,
            width=92,
        )
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        fig = plt.figure(figsize=(11.69, 8.27), dpi=150)
        ax = fig.add_axes([0, 0, 1, 1])
        title(ax, "Single Curved Geometry Scan", "bend angle / segment count diagnostic for the Geant4 curved-wall optics path")
        best_boundary = geant_single_curved_scan["best_table_survival_with_boundary"]
        bend_12m = geant_single_curved_scan["closest_to_12m_bend"]
        metric_box(ax, 0.05, 0.70, 0.20, 0.14, "best table survival", f"{best_boundary['survival_fraction']:.3f}", f"bend={best_boundary['bend_angle_rad']:.1e}")
        metric_box(ax, 0.29, 0.70, 0.20, 0.14, "best theta", f"{best_boundary['mean_grazing_angle_rad']:.2e}", "with boundary hit", "#f0fdf4")
        metric_box(ax, 0.53, 0.70, 0.20, 0.14, "12m bend theta", f"{bend_12m['mean_grazing_angle_rad']:.2e}", "46mm / 12m", "#fff7ed")
        metric_box(ax, 0.77, 0.70, 0.18, 0.14, "scan rows", f"{geant_single_curved_scan['n_rows']}", "G4 runs", "#f5f3ff")
        scan_img = fig.add_axes([0.07, 0.24, 0.86, 0.40])
        add_image(scan_img, "runs/geant4_channel_single_curved_scan/single_curved_scan.png", "single curved scan")
        cn_text(
            ax,
            0.07,
            0.11,
            "扫描结论：低 bend angle 可以让局部 grazing angle 落入 W/Si 可反射区，但它对应的焦平面偏转不足；"
            "46 mm / 12 m 的 bend angle 使局部 grazing angle 升到约 3.65e-3 rad，W/Si survival 归零。"
            "下一步需要重新审视 channel curvature / incidence / focusing geometry，而不是继续用 effective survival 校准遮盖。",
            size=10.3,
            width=94,
        )
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        fig = plt.figure(figsize=(11.69, 8.27), dpi=150)
        ax = fig.add_axes([0, 0, 1, 1])
        title(ax, "Single Curved Gap Scan", "half-gap sensitivity test for the simple 46 mm / 12 m curved-channel interpretation")
        best_12m_gap = geant_single_curved_gap_scan["best_table_survival_12m_bend"]
        best_low_gap = geant_single_curved_gap_scan["best_table_survival_low_bend"]
        min_theta_12m = geant_single_curved_gap_scan["min_constant_theta_12m_bend"]
        metric_box(ax, 0.05, 0.70, 0.20, 0.14, "12m best survival", f"{best_12m_gap['survival_fraction']:.3f}", f"gap={best_12m_gap['half_gap_mm']:.1e} mm")
        metric_box(ax, 0.29, 0.70, 0.20, 0.14, "12m min theta", f"{min_theta_12m['mean_grazing_angle_rad']:.2e}", f"gap={min_theta_12m['half_gap_mm']:.1e} mm", "#f0fdf4")
        metric_box(ax, 0.53, 0.70, 0.20, 0.14, "low-bend survival", f"{best_low_gap['survival_fraction']:.3f}", f"bend={geant_single_curved_gap_scan['low_survival_bend_angle_rad']:.1e}", "#fff7ed")
        metric_box(ax, 0.77, 0.70, 0.18, 0.14, "scan rows", f"{geant_single_curved_gap_scan['n_rows']}", "G4 runs", "#f5f3ff")
        gap_img = fig.add_axes([0.07, 0.24, 0.86, 0.40])
        add_image(gap_img, "runs/geant4_channel_single_curved_gap_scan/single_curved_gap_scan.png", "single curved gap scan")
        cn_text(
            ax,
            0.07,
            0.11,
            "结论：半间隙不是可随意调节的救场参数。12 m bend 下把 half-gap 扫到 0.05 um 仍无法把局部 grazing angle 拉回 W/Si 可反射区，"
            "table survival 仍为 0；低 bend 情况下缩小 gap 反而引入额外 bounce 并降低 table survival。",
            size=10.3,
            width=94,
        )
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        fig = plt.figure(figsize=(11.69, 8.27), dpi=150)
        ax = fig.add_axes([0, 0, 1, 1])
        title(ax, "Four-ring Geometry Constraint", "small-angle bounce count implied by configured focusing bends")
        metric_box(ax, 0.05, 0.70, 0.20, 0.14, "max required bounces", f"{channel_geometry_constraints['max_required_bounces_from_config_bend']:.2f}", "at theta~1.5e-4")
        metric_box(ax, 0.29, 0.70, 0.20, 0.14, "max required/effective", f"{channel_geometry_constraints['max_bounce_ratio_config_to_effective']:.2f}", f"worst R{channel_geometry_constraints['worst_ring_id']}", "#f0fdf4")
        metric_box(ax, 0.53, 0.70, 0.20, 0.14, "effective bounces", "1-3", "current bookkeeping", "#fff7ed")
        metric_box(ax, 0.77, 0.70, 0.18, 0.14, "rings", f"{channel_geometry_constraints['n_rings']}", "511-CAM config", "#f5f3ff")
        constraint_img = fig.add_axes([0.07, 0.22, 0.86, 0.42])
        add_image(constraint_img, "runs/channel_geometry_constraints/channel_geometry_constraints.png", "channel geometry constraints")
        cn_text(
            ax,
            0.07,
            0.09,
            "解释：若每次小角镜面反射只提供约 2*theta 的方向改变，那么四个环的总聚焦偏转需要约 6-13 次反射，"
            "明显多于当前 effective 模型中的 1-3 次 bookkeeping。OSTI/JATIS 2020 接受稿的同源 channel ray tracing 还给出 17-38 次反射的量级；"
            "这个估算不是最终几何，但它说明：下一步必须找回原始 IDL/论文中的 channel path/bounce 模型。",
            size=10.2,
            width=94,
        )
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        fig = plt.figure(figsize=(11.69, 8.27), dpi=150)
        ax = fig.add_axes([0, 0, 1, 1])
        title(ax, "Channel Bounce/Path Reconciliation", "把 1-3、6-13 与文献 17-38 reflections 放到同一张诊断表")
        metric_box(
            ax,
            0.05,
            0.70,
            0.20,
            0.14,
            "literature clue",
            f"{channel_bounce_path['literature_reflection_range'][0]}-{channel_bounce_path['literature_reflection_range'][1]}",
            "Shirazi/Bloser lineage",
        )
        metric_box(
            ax,
            0.29,
            0.70,
            0.20,
            0.14,
            "effective bounces",
            f"{channel_bounce_path['effective_model_bounce_range'][0]:.0f}-{channel_bounce_path['effective_model_bounce_range'][1]:.0f}",
            "current bookkeeping",
            "#f0fdf4",
        )
        metric_box(
            ax,
            0.53,
            0.70,
            0.20,
            0.14,
            "needed bounces",
            f"{channel_bounce_path['required_bounce_range_at_calibrated_theta'][0]:.2f}-{channel_bounce_path['required_bounce_range_at_calibrated_theta'][1]:.2f}",
            "at calibrated theta",
            "#fff7ed",
        )
        metric_box(
            ax,
            0.77,
            0.70,
            0.18,
            0.14,
            "theta band",
            f"{channel_bounce_path['theta_range_if_literature_reflections_rad'][0]:.1e}-{channel_bounce_path['theta_range_if_literature_reflections_rad'][1]:.1e}",
            "if 17-38 bounces",
            "#f5f3ff",
        )
        bounce_img = fig.add_axes([0.06, 0.21, 0.88, 0.42])
        add_image(
            bounce_img,
            "runs/channel_bounce_path_reconciliation/channel_bounce_path_reconciliation.png",
            "channel bounce/path reconciliation",
        )
        cn_text(
            ax,
            0.07,
            0.09,
            "解释：这个诊断不把 122 keV soft-gamma concentrator 的 17-38 次反射直接套到 511-CAM。"
            "它只把同源 many-bounce 线索作为量级约束：若 511-CAM 的总偏转也由许多小角反射累积，"
            "局部 grazing angle 会落在 2.5e-5 到 1.13e-4 rad 区间，低于当前 effective 校准角。"
            "因此下一步应查回原始 IDL/channel path，而不是继续调 simple single-curved demo。",
            size=10.2,
            width=94,
        )
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        fig = plt.figure(figsize=(11.69, 8.27), dpi=150)
        ax = fig.add_axes([0, 0, 1, 1])
        title(ax, "4-ring Channel Optics 结果", "W/Si 表驱动 + 每环 effective grazing angle 校准")
        img_ax = fig.add_axes([0.05, 0.16, 0.43, 0.58])
        add_image(img_ax, "runs/channel_4ring_calibrated_v2/focal_spot.png", "4-ring 焦平面光斑")
        bar_ax = fig.add_axes([0.55, 0.48, 0.38, 0.28])
        plot_per_ring(bar_ax, per_ring)
        contrib_ax = fig.add_axes([0.55, 0.16, 0.38, 0.24])
        plot_ring_contribution(contrib_ax, per_ring)
        cn_text(
            ax,
            0.05,
            0.08,
            f"总生存率 {channel['transmissivity']:.5f}，有效面积 {channel['effective_area_cm2']:.3f} cm²，"
            f"90% 包含直径 {channel['spot_d90_cm']:.3f} cm。四个环的生存率都被校准到约 0.8。",
            size=10.5,
            width=90,
        )
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        fig = plt.figure(figsize=(11.69, 8.27), dpi=150)
        ax = fig.add_axes([0, 0, 1, 1])
        title(ax, "W/Si 反射率表与角度诊断", "xraydb multilayer_reflectivity 生成的 511 keV 候选表")
        refl_ax = fig.add_axes([0.06, 0.43, 0.42, 0.34])
        plot_reflectivity(refl_ax)
        scan_ax = fig.add_axes([0.55, 0.43, 0.38, 0.34])
        add_image(scan_ax, "runs/reflectivity_theta_scan_zoom/theta_scan.png", "固定角度扫描")
        cal_ax = fig.add_axes([0.08, 0.13, 0.36, 0.20])
        plot_calibration(cal_ax, calibration)
        table_ax = fig.add_axes([0.52, 0.09, 0.42, 0.26])
        rows = [
            [
                f"R{c['ring_id']}",
                f"{c['n_bounce']}",
                f"{c['theta_rad']:.7e}",
                f"{c['table_R']:.6f}",
                f"{c['expected_transmissivity']:.6f}",
            ]
            for c in calibration
        ]
        draw_table(table_ax, ["ring", "bounce", "theta(rad)", "R", "R^n"], rows, fontsize=7.8)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        fig = plt.figure(figsize=(11.69, 8.27), dpi=150)
        ax = fig.add_axes([0, 0, 1, 1])
        title(ax, "Geant4 4-ring Channel Scaffold", "ring-calibrated effective boundary process, not wall-by-wall geometry")
        metric_box(ax, 0.05, 0.70, 0.20, 0.14, "transmissivity", f"{geant_channel['transmissivity']:.5f}", "target ~0.80")
        metric_box(ax, 0.29, 0.70, 0.20, 0.14, "Aeff", f"{geant_channel['effective_area_cm2']:.2f} cm²", "target 50.89", "#f0fdf4")
        metric_box(ax, 0.53, 0.70, 0.20, 0.14, "spot d90", f"{geant_channel['spot_d90_cm']:.3f} cm", "target 3.6", "#fff7ed")
        metric_box(ax, 0.77, 0.70, 0.18, 0.14, "contract", "PASS" if geant_channel_contract["ok"] else "FAIL", "phase/history", "#f5f3ff")
        ch_ax = fig.add_axes([0.17, 0.18, 0.62, 0.42])
        add_image(ch_ax, "runs/geant4_channel_4ring_effective/focal_spot.png", "Geant4 4-ring effective 焦斑")
        cn_text(
            ax,
            0.08,
            0.08,
            "说明：此 Geant4 channel scaffold 已有四环 tile geometry 和 boundary process，输出标准 phase_space/optics_history。"
            "它闭合了 Geant4 侧 optics handoff，但仍是 effective survival/focus，不是曲面微通道 wall-by-wall 反射模型。",
            size=10.2,
            width=92,
        )
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        fig = plt.figure(figsize=(11.69, 8.27), dpi=150)
        ax = fig.add_axes([0, 0, 1, 1])
        title(ax, "Detector-only TES/BGO 后端", "4-ring phase_space.csv -> Bi 8-layer TES + BGO calibrated response")
        metric_box(
            ax,
            0.05,
            0.70,
            0.20,
            0.14,
            "input photons",
            f"{detector['n_input_photons']}",
            "来自 4-ring phase_space",
        )
        metric_box(
            ax,
            0.29,
            0.70,
            0.20,
            0.14,
            "TES detected",
            f"{detector['tes_detection_fraction_total']:.3f}",
            "相对 optics 出射光子",
            "#f0fdf4",
        )
        metric_box(
            ax,
            0.53,
            0.70,
            0.20,
            0.14,
            "line window",
            f"{detector['line_window_fraction_of_unvetoed_detected']:.3f}",
            "510.3-511.8 keV",
            "#fff7ed",
        )
        metric_box(
            ax,
            0.77,
            0.70,
            0.18,
            0.14,
            "peak FWHM",
            f"{detector['measured_peak_fwhm_eV']:.1f} eV",
            "目标约 390 eV",
            "#f5f3ff",
        )
        spectrum_ax = fig.add_axes([0.05, 0.29, 0.38, 0.32])
        add_image(spectrum_ax, "runs/detector_only_4ring_calibrated_v2/detector_spectrum.png", "TES 重构能谱")
        map_ax = fig.add_axes([0.53, 0.29, 0.34, 0.32])
        add_image(map_ax, "runs/detector_only_4ring_calibrated_v2/detector_pixel_map.png", "TES pixel hit map")
        table_ax = fig.add_axes([0.08, 0.07, 0.84, 0.15])
        det_rows = [
            ["inside active pixel", f"{detector['geometric_acceptance']:.4f}", f"{detector['n_inside_active_pixel']}"],
            ["TES detection given active", f"{detector['tes_detection_given_active']:.4f}", f"{detector['n_tes_detected']}"],
            ["BGO self-veto on TES", f"{detector['bgo_veto_fraction_of_tes_detected']:.4f}", f"{detector['n_tes_detected_bgo_veto']}"],
            ["selected signal total", f"{detector['selected_fraction_total']:.4f}", f"{detector['n_selected_line_window']}"],
        ]
        draw_table(table_ax, ["metric", "fraction", "count"], det_rows, fontsize=8.8)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        fig = plt.figure(figsize=(11.69, 8.27), dpi=150)
        ax = fig.add_axes([0, 0, 1, 1])
        title(ax, "Geant4 Laue One-ring Toy", "constant-probability LaueToyProcess with optics contract output")
        metric_box(ax, 0.05, 0.70, 0.20, 0.14, "events", f"{geant_laue['n_primaries']}", "Ge crystal ring")
        metric_box(ax, 0.29, 0.70, 0.20, 0.14, "diffraction", f"{geant_laue['diffraction_fraction']:.3f}", "p_diff=1", "#f0fdf4")
        metric_box(ax, 0.53, 0.70, 0.20, 0.14, "focus", f"{geant_laue['focal_length_mm']/1000.0:.1f} m", "Ge(111)-scale toy", "#fff7ed")
        metric_box(ax, 0.77, 0.70, 0.18, 0.14, "contract", "PASS" if geant_laue_contract["ok"] else "FAIL", "phase/history", "#f5f3ff")
        laue_g4_ax = fig.add_axes([0.18, 0.18, 0.60, 0.42])
        add_image(laue_g4_ax, "runs/geant4_laue_one_ring/focal_spot.png", "Geant4 Laue one-ring 焦斑")
        cn_text(
            ax,
            0.08,
            0.08,
            "说明：LaueToyProcess 已在 Geant4 boundary 上运行并写出 optics_history。"
            "当前 p_diff/p_abs 为 constant toy，用于验证工程路径；尚未接入 dynamical diffraction efficiency table。",
            size=10.2,
            width=92,
        )
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        fig = plt.figure(figsize=(11.69, 8.27), dpi=150)
        ax = fig.add_axes([0, 0, 1, 1])
        title(ax, "Geant4 Detector-only Scaffold", "phase_space.csv -> minimal Bi TES + BGO raw edep")
        metric_box(
            ax,
            0.05,
            0.70,
            0.20,
            0.14,
            "events",
            f"{geant_detector['n_simulated']}",
            "1k smoke/reference",
        )
        metric_box(
            ax,
            0.29,
            0.70,
            0.20,
            0.14,
            "raw hits",
            f"{geant_detector['n_hits']}",
            "Geant4 edep rows",
            "#f0fdf4",
        )
        metric_box(
            ax,
            0.53,
            0.70,
            0.20,
            0.14,
            "TES detected",
            f"{geant_detector['tes_detection_fraction']:.3f}",
            "raw edep > 0",
            "#fff7ed",
        )
        metric_box(
            ax,
            0.77,
            0.70,
            0.18,
            0.14,
            "contract",
            "PASS" if geant_io_contract["ok"] else "FAIL",
            "6-table check",
            "#f5f3ff",
        )
        gs_ax = fig.add_axes([0.06, 0.27, 0.38, 0.34])
        add_image(gs_ax, "runs/geant4_detector_only_1k/detector_contract_spectrum.png", "Geant4 raw event spectrum")
        gm_ax = fig.add_axes([0.55, 0.27, 0.34, 0.34])
        add_image(gm_ax, "runs/geant4_detector_only_1k/detector_contract_pixel_map.png", "Geant4 TES raw hit map")
        cn_text(
            ax,
            0.07,
            0.12,
            "说明：这是 standalone detector-only Geant4 scaffold，已读取同一 4-ring phase_space，"
            "建立 8-layer Bi 20x20 TES + BGO，并输出 contract-compatible hits/event_summary。"
            "当前用于验证几何、source reader、sensitive detector 和 raw edep bookkeeping；尚不声称完整飞行质量模型或 electronics response。",
            size=10.5,
            width=90,
        )
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        fig = plt.figure(figsize=(11.69, 8.27), dpi=150)
        ax = fig.add_axes([0, 0, 1, 1])
        title(ax, "对照实验与物理诊断", "固定角、错误角度策略、Laue toy 与 Geant4 two-wall")
        comp_ax = fig.add_axes([0.05, 0.48, 0.43, 0.27])
        rows = [
            ["4-ring 固定角", f"{fixed['transmissivity']:.4f}", f"{fixed['effective_area_cm2']:.2f}", f"{fixed['spot_d90_cm']:.3f}"],
            ["4-ring 每环校准", f"{channel['transmissivity']:.4f}", f"{channel['effective_area_cm2']:.2f}", f"{channel['spot_d90_cm']:.3f}"],
            ["bending/bounce 策略", f"{bad_policy['transmissivity']:.4f}", f"{bad_policy['effective_area_cm2']:.2f}", f"{bad_policy['spot_d90_cm']:.3f}"],
            ["Laue toy", f"{laue['diffraction_fraction']:.4f}", "-", f"{laue['spot_d90_cm']:.3f}"],
        ]
        draw_table(comp_ax, ["case", "throughput", "Aeff", "d90"], rows, "关键对照指标", fontsize=8.5)
        laue_ax = fig.add_axes([0.56, 0.44, 0.34, 0.32])
        add_image(laue_ax, "runs/laue_toy/focal_spot.png", "Laue toy 焦斑")
        geant_ax = fig.add_axes([0.08, 0.12, 0.84, 0.22])
        geant_ax.set_axis_off()
        cn_text(geant_ax, 0.0, 1.0, "Geant4 two-wall smoke test", size=12, bold=True)
        geant_text = (
            "R=1,A=0,T=0 -> boundary=2, reflect=2, absorb=0, leak=0\n"
            "R=0,A=1,T=0 -> boundary=1, reflect=0, absorb=1, leak=0\n"
            "R=0,A=0,T=1 -> boundary=1, reflect=0, absorb=0, leak=1\n\n"
            "关键修复：最初直接改变 primary 方向会在 Geant4 10.2 边界处卡住；已改为 kill boundary-primary 并生成反射 secondary。"
        )
        cn_text(geant_ax, 0.02, 0.78, geant_text, size=10.5, width=92)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        fig = plt.figure(figsize=(11.69, 8.27), dpi=150)
        ax = fig.add_axes([0, 0, 1, 1])
        title(ax, "验证状态与下一步", "当前可信边界、残余风险和建议推进顺序")
        left = fig.add_axes([0.06, 0.42, 0.42, 0.36])
        validation_rows = [
            ["Python tests", "27 OK"],
            ["CMake build", "OK"],
            ["channel_two_wall_demo", "OK"],
            ["IO contract", "PASS"],
            ["W/Si Parratt xcheck", "PASS"],
            ["G4 Laue", "2k PASS"],
            ["G4 4-ring channel", "20k PASS"],
            ["G4 detector-only", "1k PASS"],
            ["4-ring calibrated", "0.79942 / 50.8569 cm²"],
            ["gap scan", "12m table survival 0"],
            ["geometry constraints", "6-13 bounces needed"],
            ["bounce/path reconcile", "17-38 clue bracketed"],
            ["detector-only", "39930 line-window events"],
            ["memory.md", "已更新"],
        ]
        draw_table(left, ["项目", "状态"], validation_rows, "已验证", fontsize=7.4)
        right = fig.add_axes([0.54, 0.42, 0.40, 0.36])
        risk_rows = [
            ["channel geometry", "G4 effective scaffold, not wall-by-wall"],
            ["simple 12m curve", "gap scan falsifies current interpretation"],
            ["bounce model", "effective 1-3 vs estimated 6-13"],
            ["path model", "needs original IDL/many-bounce geometry"],
            ["Laue diffraction", "G4 toy process, not dynamical table"],
            ["Detector TES/BGO", "G4 scaffold, not audited flight model"],
            ["optical constants", "needs non-xraydb provenance for publication"],
        ]
        draw_table(right, ["风险/缺口", "说明"], risk_rows, "残余风险", fontsize=7.5)
        cn_text(
            ax,
            0.07,
            0.30,
            "建议下一步：\n"
            "1. 基于 Shirazi/IDL 路线恢复真实 channel path / bounce-count 几何。\n"
            "2. 在几何恢复后再推进 4-ring curved-wall / per-bounce Geant4。\n"
            "3. 将 Laue constant process 替换成 efficiency table / dynamical diffraction。\n"
            "4. 探测器质量模型暂不作为主线，只保留 detector handoff regression。\n"
            "5. 引入 IMD/DarpanX 或独立 optical constants provenance 做 publication-level 交叉。",
            size=10.5,
            width=58,
        )
        cn_text(ax, 0.07, 0.08, "报告生成脚本：reports/build_progress_pdf.py", size=9, color="#64748b")
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        fig = plt.figure(figsize=(11.69, 8.27), dpi=150)
        ax = fig.add_axes([0, 0, 1, 1])
        title(ax, "GPT Pro 审核就绪状态", "项目考核视角：证据链、复现入口和不可过度声称的边界")
        audit_commands = audit.get("commands", [])
        metric_box(ax, 0.05, 0.70, 0.20, 0.14, "project audit", "PASS" if audit.get("ok") else "FAIL", "reports/project_audit", "#f0fdf4")
        metric_box(ax, 0.29, 0.70, 0.20, 0.14, "audit checks", f"{len(audit_commands)}", "unit/build/smoke/contract", "#eff6ff")
        metric_box(ax, 0.53, 0.70, 0.20, 0.14, "Python tests", "27 OK", "unittest discover", "#fff7ed")
        metric_box(ax, 0.77, 0.70, 0.18, 0.14, "review packet", "READY", "gpt_pro_review_packet.md", "#f5f3ff")
        audit_by_name = {row["name"]: bool(row["ok"]) for row in audit_commands}
        audit_groups = [
            ("python_unittest", ["python_unittest"]),
            ("cmake_build", ["cmake_build"]),
            ("baseline freeze/compare", ["baseline_freeze", "baseline_self_compare"]),
            ("two_wall table", ["two_wall_table_reflect", "two_wall_table_absorb", "two_wall_table_leak", "two_wall_table_wsi"]),
            ("single_curved", ["single_curved_constant", "single_curved_table", "single_curved_scan", "single_curved_gap_scan"]),
            ("geometry constraints", ["channel_geometry_constraints", "channel_bounce_path_reconciliation"]),
            ("IO contracts", ["io_contract_python_detector", "io_contract_g4_detector", "io_contract_g4_laue", "io_contract_g4_channel"]),
            ("W/Si crosscheck", ["wsi_parratt_crosscheck"]),
            ("PDF readable", ["pdfinfo_progress_report"]),
        ]
        audit_rows = [
            [label, "PASS" if all(audit_by_name.get(name, False) for name in names) else "FAIL"]
            for label, names in audit_groups
        ]
        cn_text(ax, 0.07, 0.62, "自动项目审计", size=12, bold=True)
        audit_ax = fig.add_axes([0.06, 0.28, 0.50, 0.32])
        draw_table(audit_ax, ["check group", "status"], audit_rows, fontsize=7.8)
        boundary_ax = fig.add_axes([0.61, 0.28, 0.33, 0.30])
        boundary_rows = [
            ["可审核", "staged IO, tests, plots, hashes"],
            ["可相信", "prototype/scaffold engineering readiness"],
            ["不可声称", "publication-grade end-to-end instrument"],
            ["下一阶段", "curved-wall optics with audited tables"],
        ]
        draw_table(boundary_ax, ["层级", "含义"], boundary_rows, "评审边界", fontsize=7.6)
        cn_text(
            ax,
            0.07,
            0.13,
            "给 GPT Pro 的建议入口：先读 reports/gpt_pro_review_packet.md，再核对 reports/project_audit/audit_report.md、"
            "docs/validation_matrix.md、docs/physics_assumptions.md 和本 PDF。审核问题集中在 staged 架构是否合理、"
            "scaffold 边界是否足够清楚，以及下一阶段 physics refinement 的优先级。",
            size=10.5,
            width=94,
        )
        cn_text(ax, 0.07, 0.06, "审核包生成脚本：analysis/build_gpt_pro_review_packet.py", size=9, color="#64748b")
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)


if __name__ == "__main__":
    build_pdf()
    print(OUT)
