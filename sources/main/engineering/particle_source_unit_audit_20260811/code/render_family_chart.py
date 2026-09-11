#!/usr/bin/env python3
"""Render the reviewed all-family energy-axis result as a static PNG."""

from __future__ import annotations

import csv
import os
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
os.environ.setdefault(
    "MPLCONFIGDIR", "/tmp/tes511_particle_source_unit_audit_matplotlib_cache_20260811"
)

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402


LABELS = {
    "alpha": "α",
    "eminus": "e−",
    "eplus": "e+",
    "gamma": "γ",
    "muminus": "μ−",
    "muplus": "μ+",
    "n": "n",
    "p": "p",
}


def main() -> int:
    source = PACKAGE / "data/spectrum_family_audit.csv"
    output = PACKAGE / "report/assets/energy_error_by_family.png"
    with source.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    labels = [LABELS[row["family"]] for row in rows]
    factors = [float(row["energy_error_factor"]) for row in rows]

    font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    if not Path(font_path).is_file():
        matches = font_manager.findSystemFonts(fontpaths=None, fontext="ttf")
        font_path = next((path for path in matches if "NotoSansCJK" in path), matches[0])
    font = font_manager.FontProperties(fname=font_path)

    fig, axis = plt.subplots(figsize=(9.2, 4.35), dpi=180)
    fig.patch.set_facecolor("white")
    axis.set_facecolor("white")

    y_positions = list(range(len(labels)))
    axis.hlines(y_positions, 1, factors, color="#e5e7eb", linewidth=2.2, zorder=1)
    axis.scatter(factors, y_positions, s=82, color="#b42318", zorder=3)
    axis.axvline(1, color="#667085", linewidth=1.4, linestyle="--", zorder=2)

    for y_position, factor in zip(y_positions, factors):
        axis.annotate(
            f"{factor:,.0f}×",
            (factor, y_position),
            xytext=(8, 0),
            textcoords="offset points",
            va="center",
            fontsize=10,
            color="#7a271a",
            fontproperties=font,
        )

    axis.set_xscale("log")
    axis.set_xlim(0.75, 1900)
    axis.set_xticks([1, 10, 100, 1000], labels=["1", "10", "100", "1,000"])
    axis.set_yticks(y_positions, labels=labels, fontproperties=font, fontsize=11)
    axis.invert_yaxis()
    axis.grid(axis="x", which="major", color="#eaecf0", linewidth=0.9)
    axis.tick_params(axis="both", which="both", length=0, colors="#475467")
    axis.set_xlabel(
        "应有总动能 / 实际载入总动能（对数刻度）",
        color="#344054",
        labelpad=10,
        fontproperties=font,
        fontsize=10,
    )
    axis.set_title(
        "八类连续谱的能量横轴均缩小 1,000 倍",
        loc="left",
        pad=14,
        color="#101828",
        fontproperties=font,
        fontsize=15,
        weight="semibold",
    )
    for spine in axis.spines.values():
        spine.set_visible(False)
    fig.tight_layout(pad=1.2)

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
