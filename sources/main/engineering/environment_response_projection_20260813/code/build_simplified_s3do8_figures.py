#!/usr/bin/env python3
"""Build two simplified S3d-O8-first figures requested for presentation."""

from __future__ import annotations

import csv
import math
import os
import tempfile
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "tes511_simplified_s3do8_mpl"))
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

from build_response_projection import (
    FAMILY_COLOR,
    FAMILY_LABEL,
    SourceModels,
    configure_plotting,
    read_csv,
    write_csv,
)


PACKAGE = Path(__file__).resolve().parents[1]
TABLES = PACKAGE / "outputs/tables"
SIMPLE = PACKAGE / "outputs/simple"
SIMPLE_FIGURES = SIMPLE / "figures"
SIMPLE_TABLES = SIMPLE / "tables"

ENVIRONMENTS = ("balloon_38km", "leo530_quiet_proxy", "lunar_surface_proxy")
ENV_LABEL = {
    "balloon_38km": "38 km 气球",
    "leo530_quiet_proxy": "530 km LEO",
    "lunar_surface_proxy": "月面",
}
ENV_COLOR = {
    "balloon_38km": "#273746",
    "leo530_quiet_proxy": "#D97706",
    "lunar_surface_proxy": "#007C83",
}
ENV_STYLE = {
    "balloon_38km": "-",
    "leo530_quiet_proxy": "--",
    "lunar_surface_proxy": ":",
}


def save(fig: plt.Figure, stem: str) -> None:
    SIMPLE_FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(SIMPLE_FIGURES / f"{stem}.png", dpi=220, bbox_inches="tight", facecolor="white")
    fig.savefig(SIMPLE_FIGURES / f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def source_energy_bands() -> list[dict[str, object]]:
    intervals = read_csv(TABLES / "w2_primary_energy_intervals.csv")
    f3 = read_csv(TABLES / "f3_projection.csv")
    total = float(next(
        row["total_rate_cps"] for row in f3
        if row["environment"] == "balloon_38km" and row["geometry"] == "S3d_O8"
    ))

    bands: list[dict[str, object]] = []
    for family in ("gamma", "eplus", "p", "alpha", "n"):
        row = next(
            item for item in intervals
            if item["geometry"] == "S3d_O8" and item["family"] == family
        )
        lo = float(row["primary_energy_p10_MeV"])
        hi = float(row["primary_energy_p90_MeV"])
        median = float(row["primary_energy_p50_MeV"])
        rate = float(row["response_weighted_rate_cps"])
        share = 100.0 * rate / total
        if family == "gamma":
            label = f"γ：{lo:.2f}–{hi:.2f} MeV · W2 {share:.1f}%"
        elif family == "eplus":
            label = f"e+：{lo / 1e3:.3f}–{hi / 1e3:.1f} GeV · W2 {share:.1f}%"
        elif family == "p":
            label = f"p：{lo / 1e3:.1f}–{hi / 1e3:.1f} GeV · W2 {share:.1f}%"
        elif family == "alpha":
            label = (
                f"α：{lo / 1e3:.1f}–{hi / 1e3:.0f} GeV 总能 · W2 {share:.1f}%"
                f"（{lo / 4e3:.1f}–{hi / 4e3:.1f} GeV/n）"
            )
        else:
            label = f"n：{lo:.1f} MeV–{hi / 1e3:.0f} GeV · W2 {share:.1f}%"
        bands.append(
            {
                "family": family,
                "energy_lo_MeV_total": lo,
                "energy_hi_MeV_total": hi,
                "exact_energy_MeV_total": "",
                "energy_p50_MeV_total": median,
                "s3do8_w2_rate_cps": rate,
                "s3do8_w2_fraction": share / 100.0,
                "semantics": "S3d-O8 prompt-plus-delayed response-weighted q10-q90 primary-energy interval",
                "display_label": label,
            }
        )
    return bands


def plot_response_band_spectra(models: SourceModels, bands: list[dict[str, object]]) -> None:
    configure_plotting()
    plt.rcParams.update({"font.size": 9.2, "axes.titlesize": 11.2})

    layout = [
        ("gamma", (0.1, 1e3)),
        ("eplus", (1.0, 1e5)),
        ("p", (1e2, 3e5)),
        ("alpha", (1e3, 5e5)),
        ("n", (1e-2, 1e6)),
    ]
    titles = {
        "gamma": "gamma 本底（以瞬时为主）",
        "eplus": "正电子本底（延迟）",
        "p": "质子引起的活化",
        "alpha": "alpha 引起的活化",
        "n": "中子引起的活化",
    }
    fig, axes = plt.subplots(2, 3, figsize=(14.4, 8.0))
    axes = axes.ravel()

    for ax, (family, xlim) in zip(axes[:5], layout):
        band = next(item for item in bands if item["family"] == family)
        grid = np.logspace(math.log10(xlim[0]), math.log10(xlim[1]), 650)
        plotted: list[np.ndarray] = []
        for environment in ENVIRONMENTS:
            flux_per_mev = np.asarray(models.target_flux(environment, family, grid * 1000.0)) * 1000.0
            y = grid * flux_per_mev
            mask = y > 0
            if np.any(mask):
                plotted.append(y[mask])
                ax.plot(
                    grid[mask], y[mask],
                    color=ENV_COLOR[environment], ls=ENV_STYLE[environment], lw=1.9,
                    label=ENV_LABEL[environment],
                )

        lo = float(band["energy_lo_MeV_total"])
        hi = float(band["energy_hi_MeV_total"])
        ax.axvspan(lo, hi, color=FAMILY_COLOR[family], alpha=0.18, lw=0, zorder=0)
        ax.axvline(lo, color=FAMILY_COLOR[family], alpha=0.8, lw=0.9)
        ax.axvline(hi, color=FAMILY_COLOR[family], alpha=0.8, lw=0.9)
        if family == "gamma":
            ax.axvline(0.511, color="#3C4248", ls="--", lw=0.9)
            ax.text(0.511, 0.04, "目标环境原生 511\n未映射", rotation=90,
                    transform=ax.get_xaxis_transform(), ha="right", va="bottom", fontsize=7.0, color="#4B5563")

        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(*xlim)
        if plotted:
            positive = np.concatenate(plotted)
            ax.set_ylim(max(float(np.min(positive)) / 3.0, 1e-8), float(np.max(positive)) * 3.0)
        ax.set_title(titles[family], loc="left", fontweight="bold", color=FAMILY_COLOR[family])
        ax.text(
            0.03, 0.95, str(band["display_label"]),
            transform=ax.transAxes, va="top", ha="left", fontsize=8.0,
            color=FAMILY_COLOR[family],
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.82, "pad": 1.8},
        )
        ax.set_xlabel("初级粒子总动能 [MeV]")
        ax.set_ylabel(r"$E\,dF/dE$  [cm$^{-2}$ s$^{-1}$]")

    legend_ax = axes[5]
    legend_ax.axis("off")
    line_handles = [
        Line2D([0], [0], color=ENV_COLOR[e], ls=ENV_STYLE[e], lw=2.3, label=ENV_LABEL[e])
        for e in ENVIRONMENTS
    ]
    legend_ax.legend(handles=line_handles, loc="upper left", frameon=False, fontsize=10.2, handlelength=3.2)
    legend_ax.text(0.0, 0.60, "彩色阴影 = 与 S3d-O8 W2 本底相关的\n初级粒子能区",
                   transform=legend_ax.transAxes, fontsize=10.2, fontweight="bold", va="top")
    for idx, family in enumerate(("gamma", "eplus", "p", "alpha", "n")):
        legend_ax.add_patch(Rectangle((0.0, 0.46 - idx * 0.075), 0.08, 0.040,
                                      transform=legend_ax.transAxes, facecolor=FAMILY_COLOR[family], alpha=0.23,
                                      edgecolor=FAMILY_COLOR[family]))
        legend_ax.text(0.11, 0.48 - idx * 0.075, FAMILY_LABEL[family],
                       transform=legend_ax.transAxes, va="center", fontsize=9.4)
    legend_ax.text(
        0.0, 0.03,
        "五族覆盖当前 S3d-O8 W2 本底约 99.6%。\n阴影为响应加权 10–90% 初能区，不是硬阈值；\nLEO 中子和月面 alpha/e± 仍是源模型代理。",
        transform=legend_ax.transAxes, fontsize=8.2, color="#5C6670", va="bottom",
    )

    fig.suptitle("S3d-O8 本底贡献能区与三种环境入射谱",
                 x=0.055, ha="left", fontsize=15.2, fontweight="bold")
    fig.text(
        0.055, 0.942,
        "每格一种粒子；线型表示环境；彩色阴影是 S3d-O8 W2 本底的响应加权初能 10–90% 区间。",
        fontsize=9.5, color="#58636E",
    )
    fig.subplots_adjust(left=0.075, right=0.985, bottom=0.08, top=0.89, wspace=0.28, hspace=0.34)
    save(fig, "01_s3do8_response_bands_on_spectra")


def build_relative_rows() -> list[dict[str, object]]:
    components = read_csv(TABLES / "projected_background_components.csv")
    f3 = read_csv(TABLES / "f3_projection.csv")

    component_rate: dict[tuple[str, str, str], float] = {}
    for row in components:
        if row["geometry"] != "S3d_O8":
            continue
        component_rate[(row["environment"], row["stream"], row["family"])] = float(row["projected_rate_cps"])

    definitions = [
        ("prompt_gamma", "瞬时 γ", "prompt", "gamma", "background_component"),
        ("prompt_eplus", r"瞬时 $e^+$", "prompt", "eplus", "zero_survivor_na"),
        ("delayed_p", "延迟 p", "delayed", "p", "background_component"),
        ("delayed_alpha", "延迟 α", "delayed", "alpha", "background_component"),
        ("delayed_n", "延迟 n", "delayed", "n", "background_component"),
    ]
    result: list[dict[str, object]] = []
    for key, label, stream, family, metric in definitions:
        baseline = component_rate[("balloon_38km", stream, family)]
        for environment in ENVIRONMENTS:
            value = component_rate[(environment, stream, family)]
            ratio = value / baseline if baseline > 0 else math.nan
            result.append(
                {
                    "row_key": key,
                    "display_label": label,
                    "metric": metric,
                    "stream": stream,
                    "family": family,
                    "environment": environment,
                    "s3do8_absolute_value": value,
                    "balloon_s3do8_baseline": baseline,
                    "relative_to_balloon_s3do8": ratio,
                    "status": "MAPPED_CENTRAL" if math.isfinite(ratio) else "NA__S3D_O8_ZERO_PROMPT_SURVIVOR",
                }
            )

    f3_by_env = {row["environment"]: row for row in f3 if row["geometry"] == "S3d_O8"}
    for key, label, field, metric in [
        ("total_w2_background", "W2 总本底", "total_rate_cps", "total_background"),
        ("f3_proxy", r"$F_{3\sigma}$ proxy", "F3_mapped_continuum_plus_activation_proxy_ph_cm2_s", "f3_proxy"),
    ]:
        baseline = float(f3_by_env["balloon_38km"][field])
        for environment in ENVIRONMENTS:
            value = float(f3_by_env[environment][field])
            result.append(
                {
                    "row_key": key,
                    "display_label": label,
                    "metric": metric,
                    "stream": "all",
                    "family": "all",
                    "environment": environment,
                    "s3do8_absolute_value": value,
                    "balloon_s3do8_baseline": baseline,
                    "relative_to_balloon_s3do8": value / baseline,
                    "status": "MAPPED_CENTRAL",
                }
            )
    return result


def plot_relative_dotplot(relative_rows: list[dict[str, object]]) -> None:
    configure_plotting()
    total_rows = {
        row["environment"]: row for row in relative_rows if row["row_key"] == "total_w2_background"
    }
    f3_rows = {row["environment"]: row for row in relative_rows if row["row_key"] == "f3_proxy"}
    y_positions = {"balloon_38km": 2, "leo530_quiet_proxy": 1, "lunar_surface_proxy": 0}

    fig, ax = plt.subplots(figsize=(10.0, 5.4))
    ax.axvspan(0.35, 1.0, color="#2369BD", alpha=0.055, lw=0)
    ax.axvspan(1.0, 16.0, color="#D97706", alpha=0.050, lw=0)
    ax.axvline(1.0, color="#333A40", lw=1.25, ls="--", zorder=1)

    for environment in ENVIRONMENTS:
        y = y_positions[environment]
        b_ratio = float(total_rows[environment]["relative_to_balloon_s3do8"])
        f_ratio = float(f3_rows[environment]["relative_to_balloon_s3do8"])
        ax.plot([b_ratio, f_ratio], [y + 0.12, y - 0.12], color="#A9B0B7", lw=1.0, zorder=2)
        ax.scatter(b_ratio, y + 0.12, s=82, marker="o", color="#2369BD", edgecolor="white", lw=0.9, zorder=3)
        ax.scatter(f_ratio, y - 0.12, s=82, marker="D", facecolor="white", edgecolor="#D97706", lw=2.0, zorder=3)

        for value, yy in ((b_ratio, y + 0.12), (f_ratio, y - 0.12)):
            if value > 8:
                xpos, align = value / 1.08, "right"
            else:
                xpos, align = value * 1.08, "left"
            ax.text(xpos, yy, f"{value:.3f}×" if value < 10 else f"{value:.2f}×",
                    ha=align, va="center", fontsize=9.5, fontweight="bold", color="#252B31")

    ax.set_xscale("log")
    ax.set_xlim(0.35, 16.0)
    ticks = [0.5, 1.0, 2.0, 5.0, 10.0]
    ax.set_xticks(ticks, [f"{tick:g}×" for tick in ticks])
    ax.set_ylim(-0.55, 2.55)
    ax.set_yticks([2, 1, 0], ["气球（基准）", "530 km LEO", "月面"])
    ax.set_xlabel("相对 S3d-O8 气球静态参考的倍数")
    ax.grid(axis="x", which="both", color="#D6DBE0", ls=":", alpha=0.85)
    ax.grid(False, axis="y")
    ax.text(0.39, 2.42, "< 1：低于气球", fontsize=8.2, color="#2369BD", va="top")
    ax.text(15.2, 2.42, "> 1：高于气球", fontsize=8.2, color="#B76000", va="top", ha="right")

    handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor="#2369BD", markeredgecolor="white",
               markersize=8.5, label="W2 总本底率"),
        Line2D([0], [0], marker="D", color="none", markerfacecolor="white", markeredgecolor="#D97706",
               markeredgewidth=1.8, markersize=7.8, label=r"$F_{3\sigma}$ 代理"),
    ]
    ax.legend(handles=handles, loc="lower right", frameon=False, fontsize=9.2)

    foot = "  |  ".join(
        f"{ENV_LABEL[e]}：B={float(total_rows[e]['s3do8_absolute_value']):.4g} cps，"
        f"F3={float(f3_rows[e]['s3do8_absolute_value']):.3g}"
        for e in ENVIRONMENTS
    )
    fig.suptitle("S3d-O8：三环境相对本底与最小可分辨通量", x=0.08, ha="left",
                 fontsize=15.0, fontweight="bold")
    fig.text(
        0.08, 0.905,
        "气球静态代理 = 1；只比较已映射连续谱 + 活化。相同 Aeff 下，F3 倍数约等于本底倍数的平方根。",
        fontsize=9.2, color="#59636E",
    )
    fig.text(0.08, 0.050, foot, fontsize=7.7, color="#4F5963")
    fig.text(
        0.08, 0.020,
        "LEO/月面完整总量仍为 NA：未含原生 511、零幸存族上限、SAA/trapped、SEP 与基地材料。",
        fontsize=7.7, color="#68727D",
    )
    fig.subplots_adjust(left=0.20, right=0.97, bottom=0.19, top=0.82)
    save(fig, "02_s3do8_environment_relative_ratios")


def main() -> int:
    SIMPLE_TABLES.mkdir(parents=True, exist_ok=True)
    bands = source_energy_bands()
    fields = [
        "family", "energy_lo_MeV_total", "energy_hi_MeV_total", "exact_energy_MeV_total",
        "energy_p50_MeV_total", "s3do8_w2_rate_cps", "s3do8_w2_fraction",
        "semantics", "display_label",
    ]
    normalized_bands = [{field: row.get(field, "") for field in fields} for row in bands]
    write_csv(SIMPLE_TABLES / "s3do8_response_energy_bands.csv", normalized_bands, fields)

    models = SourceModels()
    plot_response_band_spectra(models, bands)

    relative = build_relative_rows()
    relative_fields = list(relative[0].keys())
    write_csv(SIMPLE_TABLES / "s3do8_environment_relative_ratios.csv", relative, relative_fields)
    plot_relative_dotplot(relative)
    print(f"Wrote simplified figures and tables under {SIMPLE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
