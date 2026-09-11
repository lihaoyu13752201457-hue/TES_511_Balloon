#!/usr/bin/env python3
"""Render plain-language white figures used by the revised slide deck."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-mass511-s3-plain")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager


ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
ASSETS = WORK / "assets"
SUMMARY = WORK / "deck_evidence_summary.json"

INK = "#172033"
MUTED = "#5F6B7A"
GRID = "#DCE3EA"
MASS = "#64748B"
S1 = "#0F766E"
S3 = "#1D4ED8"
ORANGE = "#EA6A47"
PURPLE = "#7C3AED"
AMBER = "#E6A93F"


def setup() -> None:
    font_path = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
    if font_path.exists():
        font_manager.fontManager.addfont(str(font_path))
        family = font_manager.FontProperties(fname=str(font_path)).get_name()
    else:
        family = "DejaVu Sans"
    plt.rcParams.update(
        {
            "font.family": family,
            "font.size": 12,
            "axes.titlesize": 17,
            "axes.titleweight": "bold",
            "axes.labelcolor": INK,
            "axes.edgecolor": GRID,
            "axes.linewidth": 0.8,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "text.color": INK,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def clean(ax) -> None:
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)


def performance(data: dict) -> None:
    evo = data["evolution"]
    names = ["Mass_511", "第一轮屏蔽", "S3"]
    colors = [MASS, S1, S3]
    background = np.asarray(evo["background_cps"], dtype=float)
    threshold = np.asarray(evo["f3"], dtype=float) * 1e5

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.8, 5.8))
    bars = ax1.bar(names, background, color=colors, width=0.62)
    ax1.set_title("511 keV 线窗本底")
    ax1.set_ylabel("计数率 (次/秒)")
    clean(ax1)
    ax1.set_ylim(0, background.max() * 1.26)
    for bar, value in zip(bars, background):
        ax1.text(bar.get_x() + bar.get_width() / 2, value + background.max() * 0.025, f"{value:.4f}", ha="center", fontweight="bold")
    ax1.text(1.0, background.max() * 1.14, "Mass_511 → S3：-70.0%", ha="center", color=S3, fontsize=14, fontweight="bold")

    bars = ax2.bar(names, threshold, color=colors, width=0.62)
    ax2.set_title("20 天、3σ 可探测线通量")
    ax2.set_ylabel("10^-5 ph cm^-2 s^-1")
    clean(ax2)
    ax2.set_ylim(0, threshold.max() * 1.26)
    for bar, value in zip(bars, threshold):
        ax2.text(bar.get_x() + bar.get_width() / 2, value + threshold.max() * 0.025, f"{value:.2f}", ha="center", fontweight="bold")
    ax2.text(1.0, threshold.max() * 1.14, "越低越好：改善 45.6%", ha="center", color=S3, fontsize=14, fontweight="bold")

    fig.suptitle("相同大气 511 keV 线假设下的性能演化", fontsize=19, fontweight="bold", y=0.99)
    fig.text(0.01, 0.012, "线窗：510.58–511.42 keV；包含瞬发本底、活化衰变和名义大气 511 keV 线。", color=MUTED, fontsize=9.5)
    fig.tight_layout(rect=(0, 0.05, 1, 0.94))
    fig.savefig(ASSETS / "plain_performance.png", dpi=190)
    plt.close(fig)


def composition(data: dict) -> None:
    rates = data["event_rates_cps"]
    total = float(data["matched_total_background_cps"])
    labels = ["大气 511 keV 线", "正电子", "中子", "活化衰变"]
    values = np.asarray([rates["atm511"], rates["eplus"], rates["n"], rates["activation"]], dtype=float)
    colors = [PURPLE, ORANGE, S3, AMBER]
    order = np.arange(len(labels))

    fig, ax = plt.subplots(figsize=(10.2, 6.2))
    bars = ax.barh(order, values, color=colors, height=0.6)
    ax.set_yticks(order, labels)
    ax.invert_yaxis()
    ax.set_xlabel("线窗本底计数率 (次/秒)")
    ax.set_title("S3 剩余本底由什么组成")
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.set_xlim(0, values.max() * 1.42)
    for bar, value in zip(bars, values):
        pct = 100.0 * value / total
        ax.text(value + values.max() * 0.025, bar.get_y() + bar.get_height() / 2, f"{value:.5f}/s  ·  {pct:.1f}%", va="center", fontweight="bold")
    fig.text(0.01, 0.012, f"总本底 {total:.5f}/s。最大两项是大气 511 keV 线与正电子。", color=MUTED, fontsize=10)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(ASSETS / "plain_s3_composition.png", dpi=190)
    plt.close(fig)


def directions(data: dict) -> None:
    counts = data["direction_share"]["external_entry_counts"]
    families = ["正电子\n12 个", "中子\n3 个", "大气 511 keV\n56 个"]
    keys = ["eplus", "n", "atm511"]
    surfaces = [("侧面", "side", "#299E95"), ("底部", "bottom", ORANGE), ("未命中外包络", "miss", "#A4ACB8")]
    x = np.arange(len(keys))
    bottoms = np.zeros(len(keys))

    fig, ax = plt.subplots(figsize=(10.6, 6.0))
    for label, surface, color in surfaces:
        vals = []
        for key in keys:
            total = sum(counts[key].values())
            vals.append(100.0 * counts[key].get(surface, 0) / total)
        ax.bar(x, vals, bottom=bottoms, color=color, width=0.62, label=label)
        for i, (value, bottom) in enumerate(zip(vals, bottoms)):
            if value >= 7:
                ax.text(i, bottom + value / 2, f"{value:.0f}%", ha="center", va="center", color="white", fontweight="bold")
        bottoms += np.asarray(vals)
    ax.set_xticks(x, families)
    ax.set_ylim(0, 100)
    ax.set_ylabel("各类最终事件占比")
    ax.set_title("最终幸存事件主要从侧面进入")
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    fig.text(0.01, 0.012, "这是从真实初始方向投影到有限外包络的入口代理；中子只有 3 个最终事件，只作诊断。", color=MUTED, fontsize=9.5)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(ASSETS / "plain_entry_directions.png", dpi=190)
    plt.close(fig)


def variants(data: dict) -> None:
    screen = data["s3abc_screening"]
    names = screen["versions"]
    totals = np.asarray(screen["totals_cps"], dtype=float)
    threshold = np.asarray(screen["estimated_f3"], dtype=float) * 1e5
    colors = [MASS, "#5867D8", "#4E9CBD", PURPLE]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.8, 5.8))
    bars = ax1.bar(names, totals, color=colors, width=0.62)
    ax1.set_title("三类主导本底的筛选结果")
    ax1.set_ylabel("计数率 (次/秒)")
    clean(ax1)
    ax1.set_ylim(0, totals.max() * 1.27)
    for bar, value in zip(bars, totals):
        ax1.text(bar.get_x() + bar.get_width() / 2, value + totals.max() * 0.025, f"{value:.4f}", ha="center", fontweight="bold")

    bars = ax2.bar(names, threshold, color=colors, width=0.62)
    ax2.set_title("20 天、3σ 阈值估算")
    ax2.set_ylabel("10^-5 ph cm^-2 s^-1")
    clean(ax2)
    ax2.set_ylim(0, threshold.max() * 1.27)
    for bar, value in zip(bars, threshold):
        ax2.text(bar.get_x() + bar.get_width() / 2, value + threshold.max() * 0.025, f"{value:.2f}", ha="center", fontweight="bold")
    fig.suptitle("派生方案：换主动晶体比只加钨更有效", fontsize=19, fontweight="bold", y=0.99)
    fig.text(0.01, 0.012, "同统计量快速筛选；仅含正电子、中子和大气 511 keV 主导项，尚不是完整任务链结论。", color=MUTED, fontsize=9.5)
    fig.tight_layout(rect=(0, 0.05, 1, 0.94))
    fig.savefig(ASSETS / "plain_s3abc_screening.png", dpi=190)
    plt.close(fig)


def main() -> None:
    setup()
    ASSETS.mkdir(parents=True, exist_ok=True)
    data = json.loads(SUMMARY.read_text(encoding="utf-8"))
    performance(data)
    composition(data)
    directions(data)
    variants(data)
    for name in ("plain_performance.png", "plain_s3_composition.png", "plain_entry_directions.png", "plain_s3abc_screening.png"):
        path = ASSETS / name
        if not path.exists() or path.stat().st_size == 0:
            raise RuntimeError(path)
    print("PASS plain deck figures")


if __name__ == "__main__":
    main()
