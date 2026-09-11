#!/usr/bin/env python3
"""Build three clean, public-facing figures for the short presentation."""

from __future__ import annotations

import csv
import json
import math
import os
import platform
import tempfile
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "tes511_public_figures_mpl"))
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from build_response_projection import FAMILY_COLOR, SourceModels, configure_plotting, read_csv, write_csv


PACKAGE = Path(__file__).resolve().parents[1]
SOURCE_TABLES = PACKAGE / "outputs/simple/tables"
PUBLIC = PACKAGE / "outputs/public"
FIGURES = PUBLIC / "figures"
TABLES = PUBLIC / "tables"

ENVIRONMENTS = ("balloon_38km", "leo530_quiet_proxy", "lunar_surface_proxy")
ENV_LABEL = {
    "balloon_38km": "38 km 大气",
    "leo530_quiet_proxy": "530 km LEO",
    "lunar_surface_proxy": "月面",
}
ENV_SHORT = {
    "balloon_38km": "大气",
    "leo530_quiet_proxy": "LEO",
    "lunar_surface_proxy": "月面",
}
ENV_COLOR = {
    "balloon_38km": "#2D4052",
    "leo530_quiet_proxy": "#D97706",
    "lunar_surface_proxy": "#16858C",
}
ENV_STYLE = {
    "balloon_38km": "-",
    "leo530_quiet_proxy": "--",
    "lunar_surface_proxy": ":",
}

SOURCE_REFERENCES = (
    {
        "id": 1,
        "environment": "balloon_38km",
        "short": "EXPACS/PARMA",
        "citation": (
            "Sato, T. (2015), Analytical Model for Estimating Terrestrial Cosmic Ray Fluxes "
            "Nearly Anytime and Anywhere in the World: Extension of PARMA/EXPACS, PLOS ONE "
            "10, e0144679."
        ),
        "doi": "10.1371/journal.pone.0144679",
        "url": "https://doi.org/10.1371/journal.pone.0144679",
        "angular_citation": (
            "Sato, T. (2016), Analytical Model for Estimating the Zenith Angle Dependence "
            "of Terrestrial Cosmic Ray Fluxes, PLOS ONE 11, e0160390."
        ),
        "angular_doi": "10.1371/journal.pone.0160390",
        "angular_url": "https://doi.org/10.1371/journal.pone.0160390",
    },
    {
        "id": 2,
        "environment": "leo530_quiet_proxy",
        "short": "COSI DC4",
        "citation": (
            "Gallego et al. (2026), Preflight Background Estimates for COSI, "
            "The Astrophysical Journal 997, 284."
        ),
        "doi": "10.3847/1538-4357/ae32f4",
        "url": "https://doi.org/10.3847/1538-4357/ae32f4",
        "data_url": (
            "https://github.com/cositools/cosi-sim/tree/"
            "eec0dbf1aaabc79fea2706946434e30f7060a59a/"
            "cosi_sim/Source_Library/DC4/backgrounds"
        ),
        "pinned_commit": "eec0dbf1aaabc79fea2706946434e30f7060a59a",
    },
    {
        "id": 3,
        "environment": "lunar_surface_proxy",
        "short": "REDMoon",
        "citation": (
            "Dobynde, M. I. & Guo, J. (2021), Radiation Environment at the Surface and "
            "Subsurface of the Moon: Model Development and Validation, JGR: Planets 126, "
            "e2021JE006930."
        ),
        "doi": "10.1029/2021JE006930",
        "url": "https://doi.org/10.1029/2021JE006930",
        "data_doi": "10.5281/zenodo.5561427",
        "data_url": "https://doi.org/10.5281/zenodo.5561427",
        "note": "Lunar gamma additionally includes a 2pi COSI cosmic-sky proxy.",
    },
)

SUPPORTING_REFERENCES = (
    {
        "role": "official_software_entry",
        "citation": "JAEA/PHITS, EXPACS official distribution and documentation.",
        "url": "https://phits.jaea.go.jp/expacs/",
    },
    {
        "role": "leo_environment_model",
        "citation": (
            "Cumani, P. et al. (2019), Background for a gamma-ray satellite on a "
            "low-Earth orbit, Experimental Astronomy 47, 273–302."
        ),
        "doi": "10.1007/s10686-019-09624-0",
        "url": "https://doi.org/10.1007/s10686-019-09624-0",
    },
)


def save(fig: plt.Figure, stem: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / f"{stem}.png", dpi=220, bbox_inches="tight", facecolor="white")
    fig.savefig(FIGURES / f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def write_reference_audit() -> None:
    """Write the human- and machine-readable source citation record used on Fig. 2."""
    PUBLIC.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "checked_on": "2026-08-13",
        "status": "PASS__PRIMARY_PUBLICATION_AND_PINNED_DATA_LINKS_CROSS_CHECKED",
        "figure": "02_full_spectrum_comparison",
        "references": list(SOURCE_REFERENCES),
        "supporting_references": list(SUPPORTING_REFERENCES),
        "pinned_input_checks": {
            "redmoon_fig5_sha256": "82d72b510ead4d136a289de0f32091bab5446418447c53168af32a3822f0c1f5",
            "cosi_albedo_source_sha256": "6055789674d633f9050f2889cab46cc9172c59fa42ac3e8f385e902c476ee616",
        },
        "angular_scope": {
            "quantity": "native-angular-support integrated E*dF/dE",
            "balloon_38km": "strict 4pi sum of 20 equal-mu bins",
            "leo530_quiet_proxy": "sum over each component's native support; not one common direction",
            "lunar_surface_proxy": (
                "regolith-up 2pi components; gamma also includes a sky-down 2pi proxy; "
                "some charged-particle proxy components do not define a strict common 4pi field"
            ),
        },
    }
    (PUBLIC / "source_reference_audit.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    lines = [
        "# 图 2 数据来源与角域",
        "",
        "下列编号与 `02_full_spectrum_comparison` 图内编号一致。引用已于 "
        "2026-08-13 对照期刊/DOI 页面、固定代码提交和数据 DOI。",
        "",
    ]
    for ref in SOURCE_REFERENCES:
        lines.append(f"{ref['id']}. {ref['citation']} [{ref['doi']}]({ref['url']})")
        if ref.get("data_url"):
            label = "固定数据/代码" if ref["id"] == 2 else "公开数据集"
            lines.append(f"   - {label}: {ref['data_url']}")
        if ref.get("angular_citation"):
            lines.append(
                f"   - 角分布：{ref['angular_citation']} "
                f"[{ref['angular_doi']}]({ref['angular_url']})"
            )
        if ref.get("note"):
            lines.append(f"   - 注：{ref['note']}")
    lines.extend(["", "## 支撑模型引用", ""])
    for ref in SUPPORTING_REFERENCES:
        if ref.get("doi"):
            lines.append(f"- {ref['citation']} [{ref['doi']}]({ref['url']})")
        else:
            lines.append(f"- {ref['citation']} {ref['url']}")
    lines.extend(
        [
            "",
            "固定输入抽查：REDMoon `fig5.txt` SHA-256 = "
            "`82d72b510ead4d136a289de0f32091bab5446418447c53168af32a3822f0c1f5`；",
            "COSI `AlbedoPhotons.source` SHA-256 = "
            "`6055789674d633f9050f2889cab46cc9172c59fa42ac3e8f385e902c476ee616`。",
        ]
    )
    lines.extend(
        [
            "",
            "## 角域解释",
            "",
            "图中纵轴是各源物理角域积分后的 `E dF/dE [cm^-2 s^-1]`，不是某个方向的 "
            "`sr^-1` 强度，也不是三套谱都统一到 4π。",
            "",
            "- 大气：20 个等 μ 角箱求和，严格为 4π。",
            "- LEO：各 primary/albedo/secondary 分量在自身角域积分后求和。",
            "- 月面：月壤上行半球为 2π；γ 另加天空下行 2π 代理。",
            "",
            "因此曲线适合做源级环境对照，但不能直接解释成共同方向的强度比。",
            "",
        ]
    )
    (PUBLIC / "REFERENCES.md").write_text("\n".join(lines), encoding="utf-8")


def public_band_label(row: dict[str, str]) -> str:
    family = row["family"]
    lo = float(row["energy_lo_MeV_total"])
    hi = float(row["energy_hi_MeV_total"])
    share = 100.0 * float(row["s3do8_w2_fraction"])
    if family == "gamma":
        energy = f"{lo:.2f}–{hi:.2f} MeV"
    elif family == "eplus":
        energy = f"{lo / 1e3:.2f}–{hi / 1e3:.1f} GeV"
    elif family in ("p", "alpha"):
        energy = f"{lo / 1e3:.1f}–{hi / 1e3:.0f} GeV"
    else:
        energy = f"{lo:.1f} MeV–{hi / 1e3:.0f} GeV"
    return f"{energy}  ·  贡献 {share:.0f}%"


def plot_clean_response_bands(models: SourceModels, bands: list[dict[str, str]]) -> None:
    configure_plotting()
    plt.rcParams.update({"font.size": 9.2, "axes.titlesize": 11.4})
    layout = [
        ("gamma", "γ 光子", (0.1, 1e3)),
        ("eplus", "正电子", (1.0, 1e5)),
        ("p", "质子", (1e2, 3e5)),
        ("alpha", "α 粒子", (1e3, 5e5)),
        ("n", "中子", (1e-2, 1e6)),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(14.3, 7.8))
    axes = axes.ravel()
    for ax, (family, title, xlim) in zip(axes[:5], layout):
        band = next(row for row in bands if row["family"] == family)
        grid = np.logspace(math.log10(xlim[0]), math.log10(xlim[1]), 650)
        positive_curves: list[np.ndarray] = []
        for environment in ENVIRONMENTS:
            y = grid * np.asarray(models.target_flux(environment, family, grid * 1000.0)) * 1000.0
            mask = y > 0
            if np.any(mask):
                positive_curves.append(y[mask])
                ax.plot(
                    grid[mask], y[mask], color=ENV_COLOR[environment], ls=ENV_STYLE[environment],
                    lw=1.9, label=ENV_LABEL[environment],
                )
        lo, hi = float(band["energy_lo_MeV_total"]), float(band["energy_hi_MeV_total"])
        ax.axvspan(lo, hi, color=FAMILY_COLOR[family], alpha=0.17, lw=0)
        ax.axvline(lo, color=FAMILY_COLOR[family], lw=0.9, alpha=0.75)
        ax.axvline(hi, color=FAMILY_COLOR[family], lw=0.9, alpha=0.75)
        if family == "gamma":
            ax.axvline(0.511, color="#59636D", lw=0.85, ls="--")
            ax.text(0.511, 0.04, "511 keV", rotation=90, transform=ax.get_xaxis_transform(),
                    va="bottom", ha="right", fontsize=7.2, color="#59636D")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(*xlim)
        if positive_curves:
            values = np.concatenate(positive_curves)
            ax.set_ylim(max(float(values.min()) / 3.0, 1e-8), float(values.max()) * 3.0)
        ax.set_title(title, loc="left", color=FAMILY_COLOR[family], fontweight="bold")
        ax.text(
            0.03, 0.95, public_band_label(band), transform=ax.transAxes, va="top", ha="left",
            fontsize=8.2, color=FAMILY_COLOR[family],
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.84, "pad": 1.6},
        )
        ax.set_xlabel("初级粒子总动能 [MeV]")
        ax.set_ylabel(r"角域积分 $E\,dF/dE$  [cm$^{-2}$ s$^{-1}$]")

    key = axes[5]
    key.axis("off")
    handles = [
        Line2D([0], [0], color=ENV_COLOR[e], ls=ENV_STYLE[e], lw=2.5, label=ENV_LABEL[e])
        for e in ENVIRONMENTS
    ]
    handles.append(
        Patch(facecolor="#71889B", alpha=0.20, edgecolor="none",
              label="主要本底贡献能区（响应加权 10–90%）")
    )
    key.legend(handles=handles, loc="upper left", frameon=False, fontsize=10.4, handlelength=3.2)
    key.text(0.0, 0.45, "阴影颜色随粒子种类变化", transform=key.transAxes,
             fontsize=9.7, color="#4F5963")

    fig.suptitle("三种环境入射谱与主要本底能区", x=0.055, ha="left",
                 fontsize=15.2, fontweight="bold")
    fig.text(0.055, 0.94, "每格一种粒子；线型表示环境；彩色阴影表示响应加权 10–90% 主要本底能区。",
             fontsize=9.5, color="#59636E")
    fig.subplots_adjust(left=0.075, right=0.985, bottom=0.08, top=0.89, wspace=0.28, hspace=0.34)
    save(fig, "01_background_energy_bands")


def plot_clean_full_spectra(models: SourceModels) -> None:
    configure_plotting()
    families = ("gamma", "eminus", "eplus", "p", "alpha", "n")
    labels = {
        "gamma": "γ", "eminus": r"$e^-$", "eplus": r"$e^+$",
        "p": "p", "alpha": "α", "n": "n",
    }
    styles = {
        "gamma": "-", "eminus": "--", "eplus": "-.",
        "p": "-", "alpha": ":", "n": "--",
    }
    widths = {family: 1.65 for family in families}
    widths["gamma"] = 2.1
    grid = np.logspace(-1, 5, 850)

    citation_number = {ref["environment"]: ref["id"] for ref in SOURCE_REFERENCES}
    fig, axes = plt.subplots(1, 3, figsize=(15.0, 5.65), sharex=True, sharey=True)
    for ax, environment in zip(axes, ENVIRONMENTS):
        for family in families:
            y = grid * np.asarray(models.target_flux(environment, family, grid * 1000.0)) * 1000.0
            mask = y > 0
            ax.plot(grid[mask], y[mask], color=FAMILY_COLOR[family], ls=styles[family],
                    lw=widths[family], label=labels[family])
        ax.axvline(0.511, color="#7A838C", lw=0.7, ls=":")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(0.1, 1e5)
        ax.set_ylim(1e-7, 3e2)
        ax.set_title(f"{ENV_LABEL[environment]}  [{citation_number[environment]}]", fontweight="bold")
        ax.set_xlabel("初级粒子总动能 [MeV]")
    axes[0].set_ylabel(r"角域积分 $E\,dF/dE$  [cm$^{-2}$ s$^{-1}$]")

    legend = [
        Line2D([0], [0], color=FAMILY_COLOR[f], ls=styles[f], lw=widths[f], label=labels[f])
        for f in families
    ]
    legend.append(Line2D([0], [0], color="#7A838C", ls=":", lw=1.0, label="511 keV 位置"))
    fig.legend(handles=legend, loc="lower center", ncol=7, frameon=False,
               bbox_to_anchor=(0.5, 0.185), handlelength=2.6, columnspacing=1.8)
    fig.suptitle("大气、LEO 与月面主要连续入射粒子谱对比", x=0.055, ha="left",
                 fontsize=15.2, fontweight="bold")
    fig.text(0.055, 0.91, "单位一致；曲线为各分量物理入射角域上的积分通量，积分角域并不完全相同。",
             fontsize=9.4, color="#59636E")
    fig.text(
        0.055, 0.115,
        "角域：大气 = 4π；LEO = 各分量原生角域求和；月面 = 月壤上行 2π，γ 另加天空下行 2π 代理。独立 δ-511 与 μ 未画。",
        fontsize=7.8, color="#4E5862",
    )
    fig.text(
        0.055, 0.075,
        "[1] EXPACS/PARMA: Sato (2015/2016), doi:10.1371/journal.pone.0144679; "
        "10.1371/journal.pone.0160390",
        fontsize=7.1, color="#59636E",
    )
    fig.text(
        0.055, 0.045,
        "[2] COSI DC4 @ eec0dbf: Cumani et al. (2019), doi:10.1007/s10686-019-09624-0; "
        "Gallego et al. (2026), doi:10.3847/1538-4357/ae32f4",
        fontsize=7.1, color="#59636E",
    )
    fig.text(
        0.055, 0.015,
        "[3] REDMoon: Dobynde & Guo (2021), doi:10.1029/2021JE006930; data:10.5281/zenodo.5561427.  "
        "月面 γ 的天空项沿用 COSI 代理。",
        fontsize=7.1, color="#59636E",
    )
    fig.subplots_adjust(left=0.075, right=0.985, bottom=0.295, top=0.83, wspace=0.10)
    save(fig, "02_full_spectrum_comparison")


def plot_normalized_sensitivity() -> list[dict[str, object]]:
    source = read_csv(SOURCE_TABLES / "s3do8_environment_relative_ratios.csv")
    selected = {row["environment"]: row for row in source if row["row_key"] == "f3_proxy"}
    rows: list[dict[str, object]] = []
    for environment in ENVIRONMENTS:
        rows.append(
            {
                "environment": environment,
                "display_label": ENV_SHORT[environment],
                "normalized_minimum_detectable_flux": float(selected[environment]["relative_to_balloon_s3do8"]),
                "absolute_proxy_ph_cm2_s": float(selected[environment]["s3do8_absolute_value"]),
                "normalization": "balloon_38km=1",
            }
        )

    configure_plotting()
    fig, ax = plt.subplots(figsize=(8.4, 5.2))
    x = np.arange(len(rows))
    values = np.asarray([float(row["normalized_minimum_detectable_flux"]) for row in rows])
    colors = [ENV_COLOR[row["environment"]] for row in rows]
    bars = ax.bar(x, values, width=0.58, color=colors, edgecolor="white", lw=1.0)
    ax.axhline(1.0, color="#555E67", lw=1.0, ls="--")
    ax.text(2.46, 1.04, "大气 = 1", ha="right", va="bottom", fontsize=8.5, color="#555E67")
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.08, f"{value:.2f}",
                ha="center", va="bottom", fontsize=12, fontweight="bold", color="#20262C")
    ax.set_xticks(x, [row["display_label"] for row in rows])
    ax.set_ylim(0, 4.0)
    ax.set_ylabel("相对最小可分辨通量")
    ax.grid(axis="y", color="#D8DDE2", ls=":", alpha=0.8)
    ax.grid(False, axis="x")
    handles = [
        Patch(facecolor=ENV_COLOR[row["environment"]], edgecolor="none", label=row["display_label"])
        for row in rows
    ]
    handles.append(Line2D([0], [0], color="#555E67", lw=1.0, ls="--", label="大气基准 = 1"))
    ax.legend(handles=handles, title="环境", loc="upper left", ncol=4, frameon=False,
              handlelength=1.2, columnspacing=1.3, borderaxespad=0.4)
    fig.suptitle("三种环境下的相对最小可分辨通量（估算）", x=0.13, ha="left",
                 fontsize=15, fontweight="bold")
    fig.text(0.13, 0.91, "大气环境归一化为 1；数值越低表示灵敏度越好。",
             fontsize=9.5, color="#59636E")
    fig.subplots_adjust(left=0.13, right=0.97, bottom=0.15, top=0.83)
    save(fig, "03_normalized_minimum_detectable_flux")
    return rows


def main() -> int:
    FIGURES.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)
    models = SourceModels()
    bands = read_csv(SOURCE_TABLES / "s3do8_response_energy_bands.csv")
    plot_clean_response_bands(models, bands)
    plot_clean_full_spectra(models)
    normalized = plot_normalized_sensitivity()
    write_reference_audit()
    write_csv(
        TABLES / "normalized_minimum_detectable_flux.csv", normalized,
        ["environment", "display_label", "normalized_minimum_detectable_flux", "absolute_proxy_ph_cm2_s", "normalization"],
    )
    manifest = {
        "schema_version": 2,
        "status": "PUBLIC_FIGURES_BUILT__METHOD_BOUNDARIES_RETAINED_IN_PARENT_PACKAGE",
        "figures": [
            "01_background_energy_bands",
            "02_full_spectrum_comparison",
            "03_normalized_minimum_detectable_flux",
        ],
        "normalization": "balloon_38km=1",
        "generator": "code/build_public_figures.py",
        "python_version": platform.python_version(),
        "matplotlib_version": matplotlib.__version__,
        "source_reference_audit": "source_reference_audit.json",
        "angular_quantity": "native-angular-support integrated E*dF/dE, not a single-direction intensity",
        "visible_wording_policy": "project-internal geometry and response-stage labels omitted",
    }
    (PUBLIC / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote three public figures under {PUBLIC}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
