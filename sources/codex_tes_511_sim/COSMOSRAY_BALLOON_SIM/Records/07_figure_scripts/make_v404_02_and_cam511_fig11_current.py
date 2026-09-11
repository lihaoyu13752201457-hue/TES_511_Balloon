#!/usr/bin/env python3
"""Build V404 five-point linear plots and a CAM511 Fig. 11-style comparison.

The script is intentionally read-only with respect to the simulation products:
it only consumes the current source-significance CSV files and writes derived
figures/tables under Records.
"""

from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-codex")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
DATE = "20260522"
REFERENCE_FLUX = 6.5e-3
REFERENCE_FLUX_UNC = 1.6e-3
REFERENCE_SPECTRUM = "v404_kT170_no_shift"
REFERENCE_SCALES = [0.2, 0.5, 1.0, 2.0, 5.0]
POINT_SOURCE_REFERENCE_FLUX = 1.0e-4
ONE_MS = 1.0e6
CAM511_FIG11_APPROX_F3 = 3.0e-6
SPI_511_NARROW_LINE_F3 = 4.8e-5
WINDOWS = [
    ("broad_480_550", "480-550 keV", "#4C78A8"),
    ("line_510p3_511p8", "510.3-511.8 keV", "#F58518"),
]
ROUTES = [
    {
        "route_id": "laue_f17p5",
        "label": "Current Laue",
        "outdir": ROOT / "Records/05_laue_current_mainline/source_significance_time_dependent_20260522",
    },
    {
        "route_id": "channel_wallbywall",
        "label": "Current Channel",
        "outdir": ROOT / "Records/06_channel_current_mainline/source_significance_time_dependent_20260522",
    },
]
FIG11_OUT = ROOT / f"Records/09_cam511_fig11_comparison_{DATE}"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"No rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def f(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    if value == "" or value.lower() == "inf":
        return float("inf")
    return float(value)


def fmt_days(days: float) -> str:
    if not math.isfinite(days):
        return "inf"
    if days >= 1000:
        return f"{days:.0f} d"
    if days >= 10:
        return f"{days:.1f} d"
    return f"{days:.2f} d"


def fmt_flux(value: float) -> str:
    return f"{value:.3g}"


def v404_scaled_rows(route: dict[str, Any]) -> list[dict[str, Any]]:
    rows = read_csv(route["outdir"] / "v404_literature_anchor_scaled_flux_points.csv")
    keep: list[dict[str, Any]] = []
    for row in rows:
        if row["spectrum"] != REFERENCE_SPECTRUM:
            continue
        scale_text = row.get("v404_reference_scale_factor", "")
        if scale_text == "":
            continue
        scale = float(scale_text)
        if not any(math.isclose(scale, s, rel_tol=1e-9, abs_tol=1e-12) for s in REFERENCE_SCALES):
            continue
        out = dict(row)
        out["scale_factor"] = scale
        out["T3_days"] = f(row, "T3_days_reported")
        keep.append(out)
    return sorted(keep, key=lambda r: (r["window"], float(r["scale_factor"])))


def make_v404_02(route: dict[str, Any]) -> None:
    rows = v404_scaled_rows(route)
    out_csv = route["outdir"] / "v404_flux_scan_time_dependent_02_five_scaled_linear.csv"
    slim_rows = [
        {
            "route_id": route["route_id"],
            "spectrum": row["spectrum"],
            "window": row["window"],
            "scale_factor_vs_orbit1555_flux": row["scale_factor"],
            "input_flux_top_atm_ph_cm2_s": row["input_flux_top_atm_ph_cm2_s"],
            "source_factor": row["source_factor"],
            "effective_flux_factor_applied": row["effective_flux_factor_applied"],
            "T3_days_reported": row["T3_days_reported"],
            "T3_report_method": row["T3_report_method"],
            "paper_flux_ph_cm2_s": REFERENCE_FLUX,
            "paper_flux_unc_ph_cm2_s": REFERENCE_FLUX_UNC,
        }
        for row in rows
    ]
    write_csv(out_csv, slim_rows)

    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.9))
    for ax, (window, window_label, color) in zip(axes, WINDOWS):
        sub = [row for row in rows if row["window"] == window]
        xs = [float(row["scale_factor"]) for row in sub]
        ys = [float(row["T3_days"]) for row in sub]
        fluxes = [float(row["input_flux_top_atm_ph_cm2_s"]) for row in sub]
        ax.plot(xs, ys, marker="o", ms=6, lw=1.8, color=color)
        ax.axvline(1.0, color="#222222", ls="--", lw=1.0, label="paper flux")
        ax.set_xlim(0.0, 5.35)
        ymax = max(ys) * 1.22 if ys else 1.0
        ax.set_ylim(0.0, ymax)
        ax.set_xlabel(r"scale factor $F/F_0$ (linear)")
        ax.set_ylabel("3-sigma exposure (days)")
        ax.set_title(window_label)
        ax.grid(True, alpha=0.25)
        for x, y, flux in zip(xs, ys, fluxes):
            label = f"{fmt_days(y)}\nF={fmt_flux(flux)}"
            ha = "center"
            if window == "line_510p3_511p8" and y > 0.55 * ymax:
                xytext = (8, -34) if x < 0.35 else (0, -34)
                va = "top"
            else:
                xytext = (8, 10) if x < 0.35 else (0, 10)
                va = "bottom"
            if x < 0.35:
                ha = "left"
            ax.annotate(
                label,
                xy=(x, y),
                xytext=xytext,
                textcoords="offset points",
                ha=ha,
                va=va,
                fontsize=7.5,
                arrowprops={"arrowstyle": "-", "lw": 0.5, "color": "#555555"},
            )
    fig.suptitle(
        f"V404 five scaled flux points, {REFERENCE_SPECTRUM}, {route['route_id']}\n"
        r"$F_0=6.5\times10^{-3}\ \mathrm{ph\,cm^{-2}\,s^{-1}}$"
        " (Siegert+2016 orbit 1555)",
        fontsize=11,
    )
    fig.tight_layout()
    fig.savefig(route["outdir"] / "v404_flux_scan_time_dependent_02_five_scaled_linear.png", dpi=220)
    plt.close(fig)


def point_reference_rows(route: dict[str, Any]) -> list[dict[str, str]]:
    rows = read_csv(route["outdir"] / "point_source_flux_scan_time_dependent.csv")
    return [
        row
        for row in rows
        if math.isclose(float(row["input_flux_top_atm_ph_cm2_s"]), POINT_SOURCE_REFERENCE_FLUX, rel_tol=1e-12)
    ]


def fig11_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for route in ROUTES:
        for row in point_reference_rows(route):
            live_s = f(row, "live_s")
            avg_source_cps = f(row, "cumulative_signal_counts") / live_s
            avg_background_cps = f(row, "cumulative_background_counts") / live_s
            source_counts_1ms = avg_source_cps * ONE_MS
            background_counts_1ms = avg_background_cps * ONE_MS
            z_1ms = source_counts_1ms / math.sqrt(background_counts_1ms)
            f3_1ms = POINT_SOURCE_REFERENCE_FLUX * 3.0 / z_1ms
            rows.append(
                {
                    "route_id": route["route_id"],
                    "route_label": route["label"],
                    "window": row["window"],
                    "window_label": row["window_label"],
                    "reference_flux_top_atm_ph_cm2_s": POINT_SOURCE_REFERENCE_FLUX,
                    "time_weighted_T_atm_511": row["time_weighted_T_atm_511"],
                    "avg_source_cps_20day_profile": avg_source_cps,
                    "avg_background_cps_20day_profile": avg_background_cps,
                    "source_counts_1Ms_at_reference_flux": source_counts_1ms,
                    "background_counts_1Ms": background_counts_1ms,
                    "Z_1Ms_at_reference_flux": z_1ms,
                    "F3_1Ms_top_atm_ph_cm2_s": f3_1ms,
                    "F3_1Ms_relation": "F3 = 3*sqrt(B*T)/(R*T); evaluated with 20-day averaged atmosphere/background profile",
                }
            )
    return rows


def make_fig11_style() -> None:
    rows = fig11_rows()
    FIG11_OUT.mkdir(parents=True, exist_ok=True)
    write_csv(FIG11_OUT / "current_system_fig11_style_counts_and_sensitivity.csv", rows)

    line_rows = [row for row in rows if row["window"] == "line_510p3_511p8"]
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.2))

    ax = axes[0]
    labels = [row["route_label"].replace("Current ", "") for row in line_rows]
    x = np.arange(len(line_rows))
    width = 0.34
    source = [float(row["source_counts_1Ms_at_reference_flux"]) for row in line_rows]
    background = [float(row["background_counts_1Ms"]) for row in line_rows]
    bars_s = ax.bar(x - width / 2, source, width, label=rf"source, $F={POINT_SOURCE_REFERENCE_FLUX:.0e}$", color="#4C78A8")
    bars_b = ax.bar(x + width / 2, background, width, label="background", color="#F58518")
    ax.set_yscale("log")
    ax.set_xticks(x, labels)
    ax.set_ylabel("1 Ms counts")
    ax.set_title("Current system 1 Ms line-window counts")
    ax.grid(True, axis="y", which="both", alpha=0.25)
    ax.legend(fontsize=8)
    ymax_counts = max(background) * 1.75
    ax.set_ylim(top=ymax_counts)
    for i, row in enumerate(line_rows):
        z = float(row["Z_1Ms_at_reference_flux"])
        ax.text(i, max(source[i], background[i]) * 1.32, rf"$S/\sqrt{{B}}={z:.2f}$", ha="center", fontsize=8)
    ax.bar_label(bars_s, labels=[f"{v:.0f}" for v in source], fontsize=7, padding=2)

    ax = axes[1]
    comp_labels = ["511-CAM\nFig.11 approx", "SPI\nmanual", *labels]
    comp_values = [
        CAM511_FIG11_APPROX_F3,
        SPI_511_NARROW_LINE_F3,
        *[float(row["F3_1Ms_top_atm_ph_cm2_s"]) for row in line_rows],
    ]
    colors = ["#222222", "#7F7F7F", "#4C78A8", "#54A24B"]
    xpos = np.arange(len(comp_labels))
    ax.scatter(xpos, comp_values, s=[72, 72, 88, 88], color=colors[: len(comp_labels)], zorder=3)
    ax.plot(xpos, comp_values, color="#BBBBBB", lw=0.8, zorder=1)
    ax.set_yscale("log")
    ax.set_xticks(xpos, comp_labels)
    ax.set_ylabel(r"3$\sigma$ line sensitivity in 1 Ms (ph cm$^{-2}$ s$^{-1}$)")
    ax.set_title("Fig.11-style line sensitivity comparison")
    ax.grid(True, axis="y", which="both", alpha=0.25)
    for xval, yval in zip(xpos, comp_values):
        ax.annotate(f"{yval:.2g}", (xval, yval), xytext=(0, 9), textcoords="offset points", ha="center", fontsize=8)
    fig.suptitle("CAM511 Fig. 11-style current-system overlay", fontsize=12)
    fig.tight_layout()
    fig.savefig(FIG11_OUT / "current_system_fig11_style_counts_and_sensitivity.png", dpi=220)
    plt.close(fig)

    readme = f"""# CAM511 Fig. 11-style Current-System Comparison

Generated: {DATE}

This directory places the current Laue and Channel routes into the same
counting-sensitivity structure used in the 511-CAM Fig. 11 discussion:

```text
N_s = F * R_s * T
N_b = R_b * T
Z ~= N_s / sqrt(N_b)
F_3sigma = 3 * sqrt(R_b * T) / (R_s * T)
```

For the current-system points, `R_s` and `R_b` are evaluated from
`point_source_flux_scan_time_dependent.csv` at `F = {POINT_SOURCE_REFERENCE_FLUX:.1e}
ph cm^-2 s^-1`, using the 20-day averaged atmospheric transmission and Level-1
prompt+activation background profile.

Reference markers:

- 511-CAM paper Fig. 11 approximate 3sigma line sensitivity: `{CAM511_FIG11_APPROX_F3:.1e} ph cm^-2 s^-1`.
  Source: Shirazi et al. 2023, arXiv: https://arxiv.org/abs/2206.14652 .
- INTEGRAL/SPI Observer's Manual 511 keV narrow-line 3sigma / 1 Ms sensitivity: `{SPI_511_NARROW_LINE_F3:.1e} ph cm^-2 s^-1`.
  Source: ESA INTEGRAL SPI Observer's Manual / performance page,
  https://integral.esac.esa.int/AO12/AO12_SPI_ObsMan.pdf and
  https://integral.esac.esa.int/integ_spectr_para.html .

Primary outputs:

- `current_system_fig11_style_counts_and_sensitivity.png`
- `current_system_fig11_style_counts_and_sensitivity.csv`

Claim boundary: this is a current workflow counting-sensitivity overlay, not a
profile-likelihood or final mission sensitivity.
"""
    (FIG11_OUT / "README.md").write_text(readme, encoding="utf-8")

    summary = {
        "date": DATE,
        "source": "current source_significance_time_dependent outputs",
        "cam511_fig11_approx_f3_ph_cm2_s": CAM511_FIG11_APPROX_F3,
        "spi_511_narrow_line_f3_1Ms_ph_cm2_s": SPI_511_NARROW_LINE_F3,
        "current_rows": rows,
        "formula": "F3 = 3*sqrt(R_b*T)/(R_s*T)",
        "claim_boundary": "counting sensitivity overlay; not final profile likelihood",
    }
    (FIG11_OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main() -> int:
    for route in ROUTES:
        make_v404_02(route)
    make_fig11_style()
    print("Wrote V404 02 figures and CAM511 Fig.11-style comparison.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
