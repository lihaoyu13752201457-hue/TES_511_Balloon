#!/usr/bin/env python3
"""Build the 511-keV narrow-line 1 Ms comparison report.

The historical 2.99e-5 TES marker is retained only as a delayed-only
aspiration. The current TES authority is read from the v3p5 fullstat
performance comparison summary.
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-newgeo")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "reports" / "compare_511_narrow_1Ms_20260612"
PERF_SUMMARY = (
    ROOT
    / "stepwise_maintenance"
    / "step08_significance"
    / "outputs"
    / "performance_curve_comparison_1Ms"
    / "performance_curve_comparison_1Ms_summary.json"
)


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def fmt(value: float) -> str:
    return f"{value:.6e}"


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "rank",
        "case",
        "plot_label",
        "flux_3sigma_1Ms_ph_cm2_s",
        "method",
        "source",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def performance_v3p5_w2() -> dict[str, Any]:
    data = json.loads(PERF_SUMMARY.read_text(encoding="utf-8"))
    row = data["one_Ms"]["v3p5_W2"]
    return {
        "case": "TES_511_Balloon_v3p5_fullstat_W2_current",
        "plot_label": "TES 511\ncurrent W2",
        "flux_3sigma_1Ms_ph_cm2_s": float(row["flux_3sigma_ph_cm2_s"]),
        "method": "current v3p5 fullstat W2 prompt+delayed background, Step08 1 Ms interpolation",
        "source": rel(PERF_SUMMARY),
    }


def build_rows() -> list[dict[str, Any]]:
    rows = [
        {
            "case": "CAM511",
            "plot_label": "511-CAM\nFig.11 approx",
            "flux_3sigma_1Ms_ph_cm2_s": 3.0e-6,
            "method": "Fig.11 approximate 511-keV narrow-line 1 Ms marker",
            "source": "511-CAM Fig.11 style marker; user-corrected value 3e-6",
        },
        {
            "case": "TES_511_Balloon_delayed_only_aspiration",
            "plot_label": "TES 511\ndelayed-only",
            "flux_3sigma_1Ms_ph_cm2_s": 2.9917526839687664e-5,
            "method": "delayed-only aspiration; prompt particle background excluded, not current authority",
            "source": "legacy compare_511_narrow_1Ms marker relabeled after Claude R2 review",
        },
        {
            "case": "SPI",
            "plot_label": "SPI\nmanual",
            "flux_3sigma_1Ms_ph_cm2_s": 5.0e-5,
            "method": "published 3sigma 1e6 s 511-keV narrow-line marker",
            "source": "SPI sensitivity marker used in local comparison table",
        },
        performance_v3p5_w2(),
        {
            "case": "old_geo",
            "plot_label": "old_geo\nW2 spot_r90",
            "flux_3sigma_1Ms_ph_cm2_s": 8.748416439180168e-5,
            "method": "new_geo_re/DEMO2 W2 spot_r90, sqrt-exposure scaled to 1 Ms",
            "source": "stepwise_maintenance Step08 performance_curve_comparison_1Ms",
        },
        {
            "case": "COSI satellite",
            "plot_label": "COSI\nsatellite",
            "flux_3sigma_1Ms_ph_cm2_s": 9.53340904398841e-5,
            "method": "1.2e-5 in 2 yr scaled by sqrt(63115200 / 1e6)",
            "source": "Tomsick et al. 2023 COSI mission paper, arXiv:2308.12362",
        },
        {
            "case": "COSI balloon",
            "plot_label": "COSI\nballoon",
            "flux_3sigma_1Ms_ph_cm2_s": 2.85e-3,
            "method": "3.9e-3 flux at 7.2sigma over 3.08 Ms, scaled to 3sigma and 1 Ms",
            "source": "COSI 511-keV line detection, arXiv:1912.00110",
        },
    ]
    rows.sort(key=lambda row: float(row["flux_3sigma_1Ms_ph_cm2_s"]))
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows


def plot(rows: list[dict[str, Any]]) -> None:
    labels = [row["plot_label"] for row in rows]
    values = [float(row["flux_3sigma_1Ms_ph_cm2_s"]) for row in rows]
    colors = []
    for row in rows:
        case = row["case"]
        if case == "TES_511_Balloon_v3p5_fullstat_W2_current":
            colors.append("#1f77b4")
        elif case == "TES_511_Balloon_delayed_only_aspiration":
            colors.append("#f0b429")
        elif case == "CAM511":
            colors.append("#2ca02c")
        else:
            colors.append("#5c6470")

    fig, ax = plt.subplots(figsize=(9.0, 5.0))
    x = list(range(len(rows)))
    ax.scatter(x, values, s=92, c=colors, edgecolor="white", linewidth=1.1, zorder=3)
    for xi, value in zip(x, values):
        ax.text(xi, value * 1.16, fmt(value).replace("e-0", "e-"), ha="center", va="bottom", fontsize=8)
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("3sigma 1 Ms flux limit (ph cm^-2 s^-1)")
    ax.set_title("511-keV narrow-line 1 Ms sensitivity comparison")
    ax.grid(True, axis="y", which="both", alpha=0.25)
    ax.text(
        0.01,
        0.02,
        "Current TES authority is v3p5 fullstat W2; the delayed-only TES point excludes prompt background.",
        transform=ax.transAxes,
        fontsize=8,
        color="#4b5563",
    )
    fig.tight_layout()
    fig.savefig(OUT / "compare_511_narrow_1Ms.png", dpi=190)
    fig.savefig(OUT / "compare_511_narrow_1Ms.svg")
    fig.savefig(OUT / "compare_511_narrow_1Ms_fig11style.png", dpi=190)
    plt.close(fig)


def markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# 511-keV Narrow-Line Sensitivity Comparison",
        "",
        "All entries are shown as 3-sigma, 1 Ms minimum distinguishable flux in ph cm^-2 s^-1. Lower is better.",
        "",
        "Current TES_511_Balloon authority is the `TES_511_Balloon_v3p5_fullstat_W2_current` row. The old 2.99e-5 row is retained only as a delayed-only aspiration where prompt particle background is excluded.",
        "",
        "![511-keV narrow-line sensitivity comparison](compare_511_narrow_1Ms.png)",
        "",
        "## Data",
        "",
        "| rank | case | flux ph cm^-2 s^-1 | note |",
        "| ---: | --- | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['rank']} | {row['case']} | {fmt(float(row['flux_3sigma_1Ms_ph_cm2_s']))} | {row['method']} |"
        )
    lines.extend(
        [
            "",
            "",
            "## Caveats",
            "",
            "- `TES_511_Balloon_delayed_only_aspiration` is not the current performance claim; it removes prompt particle background and is useful only as an upper-bound design aspiration.",
            "- `TES_511_Balloon_v3p5_fullstat_W2_current` is read from the current Step08/performance fullstat output and includes prompt plus delayed W2 background.",
            "- `old_geo` is the local `new_geo_re`/DEMO2 W2 `spot_r90` marker from the existing 1 Ms comparison table.",
            "- `COSI balloon` is scaled from the reported 511-keV line detection flux/significance/exposure, so it is a 511-line detection-equivalent marker rather than a satellite-style point-source survey requirement.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = build_rows()
    write_csv(OUT / "compare_511_narrow_1Ms_data.csv", rows)
    plot(rows)
    (OUT / "compare_511_narrow_1Ms.md").write_text(markdown(rows), encoding="utf-8")
    summary = {
        "status": "PASS_COMPARE_511_NARROW_1MS_RELABEL_R2",
        "current_tes_case": "TES_511_Balloon_v3p5_fullstat_W2_current",
        "delayed_only_case": "TES_511_Balloon_delayed_only_aspiration",
        "outputs": {
            "csv": rel(OUT / "compare_511_narrow_1Ms_data.csv"),
            "markdown": rel(OUT / "compare_511_narrow_1Ms.md"),
            "figure_png": rel(OUT / "compare_511_narrow_1Ms.png"),
            "figure_svg": rel(OUT / "compare_511_narrow_1Ms.svg"),
        },
    }
    (OUT / "compare_511_narrow_1Ms_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
