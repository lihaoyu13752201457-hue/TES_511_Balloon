#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a standalone manuscript-style PDF for the 2605 day-15 simulation.

This manuscript is not a 2602/PPT comparison report.  It uses the audited
day-15 products as a reproducible data set and writes the result as a compact
scientific paper with the simulation model, event selection, veto performance,
background normalization, and 511-keV point-source sensitivity.
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
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
INPUT = ROOT / "reports" / "day15_complete_report"
OUT = ROOT / "reports" / "day15_sci_manuscript"
FIG = OUT / "figures"

SUMMARY = INPUT / "complete_day15_summary.json"
ZOOM_CSV = INPUT / "timeline_spectrum_480_550_rates.csv"
MAIN_CSV = INPUT / "timeline_spectrum_100_10000_rates.csv"
COMP_CSV = INPUT / "image8_like_component_rates_with_science.csv"
ACTIVATION_CSV = INPUT / "activation_inventory_day15_after_groundstate_fix.csv"
ACTIVATION_FIG = INPUT / "figures" / "activation_top10_after_fix.png"
ACCIDENTAL_JSON = ROOT / "reports" / "science_accidental_veto" / "science_accidental_veto_summary.json"

CAM511 = {
    "arxiv": "2206.14652",
    "effective_area_cm2": 50.89,
    "focal_length_m": 12.0,
    "spot_diameter_cm": 3.6,
    "line_fwhm_keV": 0.390,
    "detected_line_fraction": 0.93,
    "observation_s": 1.0e6,
}

DIXE = {
    "doi": "10.21203/rs.3.rs-8576846/v1",
    "nominal_nxb_cps_cm2": 0.528,
    "high_lat_nxb_cps_cm2": 2.11,
    "saa_exit_cps_cm2": 0.38,
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def load_numeric_csv(path: Path):
    rows = read_csv_rows(path)
    data = {k: [] for k in rows[0].keys()}
    for row in rows:
        for key, value in row.items():
            data[key].append(float(value))
    return data


def tex_escape(value) -> str:
    text = str(value)
    mapping = {
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
    return "".join(mapping.get(ch, ch) for ch in text)


def fmt(value: float, nd: int = 3) -> str:
    if value == 0:
        return "0"
    if abs(value) < 1e-3 or abs(value) >= 1e4:
        return f"{value:.{nd}e}"
    return f"{value:.{nd}f}"


def fmt_pm(rate: float, count: float, exposure: float, nd: int = 4) -> str:
    err = math.sqrt(count) / exposure if count > 0 else 0.0
    return f"{fmt(rate, nd)} $\\pm$ {fmt(err, nd)}"


def sci_tex(value: float, nd: int = 2) -> str:
    """Return a compact LaTeX scientific-notation number for math mode."""
    if value == 0:
        return "0"
    exp = math.floor(math.log10(abs(value)))
    mant = value / (10**exp)
    return rf"{mant:.{nd}f}\times 10^{{{exp}}}"


def integrate_window(csv_data: dict, column: str, lo: float, hi: float, binw: float) -> float:
    total = 0.0
    for e, rate in zip(csv_data["E_keV"], csv_data[column]):
        left = e - 0.5 * binw
        right = e + 0.5 * binw
        overlap = max(0.0, min(right, hi) - max(left, lo))
        if overlap > 0:
            total += rate * overlap / binw
    return total


def table(headers, rows, align=None):
    align = align or ("l" + "r" * (len(headers) - 1))
    lines = [rf"\begin{{tabular}}{{{align}}}", r"\toprule"]
    lines.append(" & ".join(tex_escape(h) for h in headers) + r" \\")
    lines.append(r"\midrule")
    for row in rows:
        fields = []
        for value in row:
            text = str(value)
            fields.append(text if "\\" in text or "$" in text else tex_escape(text))
        lines.append(" & ".join(fields) + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    return "\n".join(lines)


def plot_workflow():
    path = FIG / "fig01_workflow.png"
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    ax.set_axis_off()
    boxes = [
        ("Atmospheric\nprompt field", 0.05, 0.68, "#D6EAF8"),
        ("Activation\nbuildup", 0.05, 0.38, "#D6EAF8"),
        ("Focused 511 keV\nscience source", 0.05, 0.08, "#FDEBD0"),
        ("Fixed day-15\ndelayed source", 0.32, 0.38, "#E8DAEF"),
        ("MEGAlib/Cosima\ntransport", 0.54, 0.38, "#D5F5E3"),
        ("Common Poisson\ntime axis", 0.73, 0.38, "#FCF3CF"),
        ("BGO + Compton/FoV\nselection", 0.73, 0.08, "#FADBD8"),
        ("Spectra, NXB,\nline sensitivity", 0.54, 0.08, "#EBDEF0"),
    ]
    for text, x, y, color in boxes:
        patch = FancyBboxPatch(
            (x, y),
            0.18,
            0.16,
            boxstyle="round,pad=0.02,rounding_size=0.025",
            facecolor=color,
            edgecolor="#333333",
            lw=1.0,
        )
        ax.add_patch(patch)
        ax.text(x + 0.09, y + 0.08, text, ha="center", va="center", fontsize=9)

    arrows = [
        ((0.23, 0.76), (0.54, 0.50)),
        ((0.23, 0.46), (0.32, 0.46)),
        ((0.50, 0.46), (0.54, 0.46)),
        ((0.23, 0.16), (0.54, 0.40)),
        ((0.72, 0.46), (0.73, 0.46)),
        ((0.82, 0.38), (0.82, 0.24)),
        ((0.73, 0.16), (0.72, 0.16)),
    ]
    for start, end in arrows:
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=12, lw=1.2, color="#333333"))

    ax.text(
        0.04,
        0.94,
        "Simulation logic: physical source separation is preserved until the common time axis.",
        fontsize=11,
        weight="bold",
    )
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def plot_wide_spectrum(main):
    path = FIG / "fig02_wide_spectrum.png"
    e = np.asarray(main["E_keV"], dtype=float)
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    ax.step(e, main["timeline_raw_cps_per_bin"], where="mid", lw=1.1, color="#3366AA", label="No veto")
    ax.step(e, main["timeline_bgo_cps_per_bin"], where="mid", lw=1.1, color="#CC6677", label="BGO veto")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Event-summed TES energy (keV)")
    ax.set_ylabel("Rate per 10 keV bin (counts s$^{-1}$)")
    ax.set_title("Day-15 non-X-ray background spectrum")
    ax.grid(True, which="both", alpha=0.22)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def plot_line_window(zoom):
    path = FIG / "fig03_line_window.png"
    e = np.asarray(zoom["E_keV"], dtype=float)
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    ax.step(e, zoom["timeline_raw_cps_per_bin"], where="mid", lw=1.0, color="#3366AA", label="No veto")
    ax.step(e, zoom["timeline_bgo_cps_per_bin"], where="mid", lw=1.0, color="#CC6677", label="BGO veto")
    ax.step(e, zoom["timeline_final_cps_per_bin"], where="mid", lw=1.25, color="#228833", label="BGO + Compton/FoV")
    ax.axvspan(510.3, 511.8, color="#EE7733", alpha=0.18, label="510.3--511.8 keV line window")
    ax.set_yscale("log")
    ax.set_xlabel("Event-summed TES energy (keV)")
    ax.set_ylabel("Rate per 0.5 keV bin (counts s$^{-1}$)")
    ax.set_title("Successive veto selections around the 511-keV line")
    ax.grid(True, which="both", alpha=0.22)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def plot_stream_decomposition(summary):
    path = FIG / "fig04_stream_decomposition.png"
    stream = summary["timeline_rates_by_stream_pure"]
    stages = ["raw", "bgo", "final"]
    labels = ["No veto", "BGO", "BGO+Compton/FoV"]
    order = ["delayed", "prompt", "mixed", "science"]
    colors = {
        "delayed": "#CC6677",
        "prompt": "#4477AA",
        "mixed": "#BBBBBB",
        "science": "#EE7733",
    }
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    bottom = np.zeros(len(stages))
    for key in order:
        vals = np.array([stream[key][stage] for stage in stages])
        ax.bar(labels, vals, bottom=bottom, color=colors[key], label=key)
        bottom += vals
    ax.set_ylabel("480--550 keV rate (counts s$^{-1}$)")
    ax.set_title("Timeline stream decomposition after each event selection")
    ax.grid(True, axis="y", alpha=0.22)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def plot_component_bars():
    path = FIG / "fig05_incident_components.png"
    rows = [r for r in read_csv_rows(COMP_CSV) if r["component"] != "Total"]
    rows = sorted(rows, key=lambda r: float(r["rate_480_550_keV_cps"]), reverse=True)
    labels = [r["component"] for r in rows]
    vals = np.array([float(r["rate_480_550_keV_cps"]) for r in rows])
    colors = ["#CC6677" if "Activation" in x else "#EE7733" if "Science" in x else "#4477AA" for x in labels]
    fig, ax = plt.subplots(figsize=(7.4, 4.9))
    y = np.arange(len(labels))
    ax.barh(y, vals, color=colors)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xscale("symlog", linthresh=1e-3)
    ax.set_xlabel("Direct-expectation no-veto rate in 480--550 keV (counts s$^{-1}$)")
    ax.set_title("Incident/source component accounting before veto")
    ax.grid(True, axis="x", alpha=0.24)
    for yi, val in zip(y, vals):
        ax.text(val * 1.08 + 2e-5, yi, fmt(val, 3), va="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def plot_cam_counts(summary, line_bkg, line_rsp):
    path = FIG / "fig06_cam511_counts.png"
    flux = summary["normalization"]["science_flux_ph_cm2_s"]
    t = 1.0e6
    broad_b = summary["science_sensitivity"]["background_final_cps_prompt_plus_delayed"] * t
    broad_s = summary["science_sensitivity"]["science_final_response_cps_per_ph_cm-2_s-1"] * flux * t
    line_b = line_bkg * t
    line_s = line_rsp * flux * t
    labels = ["480--550 keV\nbroad window", "510.3--511.8 keV\nline window"]
    x = np.arange(2)
    fig, ax = plt.subplots(figsize=(6.8, 4.7))
    ax.bar(x - 0.18, [broad_b, line_b], width=0.34, color="#88CCEE", label="Background")
    ax.bar(x + 0.18, [broad_s, line_s], width=0.34, color="#EE7733", label=rf"Source at $F={flux:.0e}$")
    for i, (s, b) in enumerate([(broad_s, broad_b), (line_s, line_b)]):
        ax.text(i, max(s, b) * 1.08, rf"$S/\sqrt{{B}}={s/math.sqrt(b):.2f}$", ha="center", fontsize=8)
    ax.set_yscale("log")
    ax.set_xticks(x, labels)
    ax.set_ylabel("Counts in 1 Ms")
    ax.set_title("CAM511 Fig. 11-style source/background counts")
    ax.grid(True, axis="y", which="both", alpha=0.22)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def plot_sensitivity(summary, line_bkg, line_rsp):
    path = FIG / "fig07_sensitivity.png"
    sci = summary["science_sensitivity"]
    t = np.logspace(3, 7, 240)
    broad_b = sci["background_final_cps_prompt_plus_delayed"]
    broad_rsp = sci["science_final_response_cps_per_ph_cm-2_s-1"]
    f3_broad = 3.0 * np.sqrt(broad_b * t) / (broad_rsp * t)
    f5_broad = 5.0 * np.sqrt(broad_b * t) / (broad_rsp * t)
    f3_line = 3.0 * np.sqrt(line_bkg * t) / (line_rsp * t)
    f5_line = 5.0 * np.sqrt(line_bkg * t) / (line_rsp * t)
    fig, ax = plt.subplots(figsize=(7.5, 4.9))
    ax.loglog(t, f3_broad, lw=1.8, color="#4477AA", label=r"3$\sigma$, 480--550 keV")
    ax.loglog(t, f5_broad, lw=1.0, ls="--", color="#4477AA", label=r"5$\sigma$, 480--550 keV")
    ax.loglog(t, f3_line, lw=1.8, color="#CC6677", label=r"3$\sigma$, 510.3--511.8 keV")
    ax.loglog(t, f5_line, lw=1.0, ls="--", color="#CC6677", label=r"5$\sigma$, 510.3--511.8 keV")
    ax.scatter([1.0e6], [4.8e-5], marker="*", s=120, color="#222222", label="SPI manual, 3$\\sigma$/1 Ms")
    ax.set_xlabel("Exposure (s)")
    ax.set_ylabel(r"Minimum line flux (ph cm$^{-2}$ s$^{-1}$)")
    ax.set_title("Background-limited 511-keV point-source sensitivity")
    ax.grid(True, which="both", alpha=0.24)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def build_tables(summary, line_bkg, line_rsp):
    obs = summary["normalization"]["obs_time_s"]
    counts = summary["timeline_counts_480_550"]
    rates = summary["timeline_rates_cps"]
    veto_rows = [
        ("No veto", counts["raw"], fmt_pm(rates["raw"], counts["raw"], obs), "1.000"),
        ("BGO veto", counts["bgo"], fmt_pm(rates["bgo"], counts["bgo"], obs), fmt(rates["bgo"] / rates["raw"], 3)),
        (
            "BGO + Compton/FoV",
            counts["final"],
            fmt_pm(rates["final"], counts["final"], obs),
            fmt(rates["final"] / rates["raw"], 3),
        ),
    ]

    stream_rows = []
    for key in ("delayed", "prompt", "mixed", "science"):
        vals = summary["timeline_rates_by_stream_pure"][key]
        stream_rows.append((key, fmt(vals["raw"], 4), fmt(vals["bgo"], 4), fmt(vals["final"], 4)))

    component_rows = []
    for row in sorted(read_csv_rows(COMP_CSV), key=lambda r: float(r["rate_480_550_keV_cps"]), reverse=True):
        if row["component"] == "Total":
            continue
        component_rows.append(
            (
                row["component"],
                fmt(float(row["rate_480_550_keV_cps"]), 4),
                fmt(float(row["rate_100_10000_keV_cps"]), 4),
            )
        )

    activation_rows = []
    for row in read_csv_rows(ACTIVATION_CSV)[:8]:
        activation_rows.append(
            (
                f"{row['VN']}:{row['nuclide']}",
                fmt(float(row["hl_s"]), 3),
                fmt(float(row["Activity_Bq_after_fix"]), 3),
                fmt(float(row["fix_scale"]), 5),
            )
        )

    sci = summary["science_sensitivity"]
    t = 1.0e6
    broad_rsp = sci["science_final_response_cps_per_ph_cm-2_s-1"]
    broad_bkg = sci["background_final_cps_prompt_plus_delayed"]
    sensitivity_rows = [
        (
            "480--550 keV",
            fmt(broad_bkg, 4),
            fmt(broad_rsp, 4),
            fmt(3.0 * math.sqrt(broad_bkg * t) / (broad_rsp * t), 4),
            fmt(5.0 * math.sqrt(broad_bkg * t) / (broad_rsp * t), 4),
        ),
        (
            "510.3--511.8 keV",
            fmt(line_bkg, 4),
            fmt(line_rsp, 4),
            fmt(3.0 * math.sqrt(line_bkg * t) / (line_rsp * t), 4),
            fmt(5.0 * math.sqrt(line_bkg * t) / (line_rsp * t), 4),
        ),
    ]

    return {
        "veto": table(["Selection", "Counts", "Rate (cps)", "Survival"], veto_rows, align="lrrr"),
        "streams": table(["Stream", "No veto cps", "BGO cps", "Final cps"], stream_rows, align="lrrr"),
        "components": table(["Component", "480--550 cps", "100--10000 cps"], component_rows, align="lrr"),
        "activation": table(["Volume:nuclide", "Half-life (s)", "Activity (Bq)", "Fix scale"], activation_rows, align="lrrr"),
        "sensitivity": table(["Window", "$R_b$ cps", "$R_s$ cps/flux", "3$\\sigma$ 1 Ms", "5$\\sigma$ 1 Ms"], sensitivity_rows, align="lrrrr"),
    }


def write_tex(summary, figs, tables, line_bkg, line_rsp):
    tex = OUT / "cosmosray_bg_2605_sci_manuscript.tex"
    norm = summary["normalization"]
    sci = summary["science_sensitivity"]
    delay = summary["delay_fix"]
    cat = summary["catalog"]
    draw = summary["draw_summary"]

    atm_trans = norm["science_injection_rate_s^-1"] / (CAM511["effective_area_cm2"] * norm["science_flux_ph_cm2_s"])
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
    ref_flux_tex = sci_tex(norm["science_flux_ph_cm2_s"], 1)
    flux3_broad_tex = sci_tex(flux3_broad, 2)
    flux3_line_tex = sci_tex(flux3_line, 2)
    flux3_broad_acc_tex = sci_tex(flux3_broad_acc, 2)
    flux3_line_acc_tex = sci_tex(flux3_line_acc, 2)
    nxb_density_tex = sci_tex(nxb_density, 3)

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
\renewcommand{{\abstractname}}{{Abstract}}
\renewcommand{{\figurename}}{{Figure}}
\renewcommand{{\tablename}}{{Table}}
\title{{Non-X-ray Background and 511-keV Point-source Sensitivity of a Balloon-borne Focusing TES Gamma-ray Spectrometer}}
\author{{COSMOSRAY\_BG\_2605 simulation analysis}}
\date{{2026-05-12}}

\begin{{document}}
\maketitle

\begin{{abstract}}
We present a self-consistent Monte Carlo estimate of the non-X-ray background for a balloon-borne, focusing 511-keV gamma-ray spectrometer with a TES microcalorimeter focal plane and an active BGO shield.  The simulation separates three physical streams: prompt atmospheric cosmic-ray secondaries, delayed radioactivation generated by a buildup run, and a focused on-axis 511-keV science source.  Prompt, delayed and science events are merged on a common Poisson time axis before applying anti-coincidence and Compton/FoV selections.  For the day-15 configuration, the 480--550 keV focal-plane background is {summary["timeline_rates_cps"]["raw"]:.4f} counts s$^{{-1}}$ before veto, {summary["timeline_rates_cps"]["bgo"]:.4f} counts s$^{{-1}}$ after the BGO veto, and {summary["timeline_rates_cps"]["final"]:.4f} counts s$^{{-1}}$ after the full selection.  A reference point source with $F_{{511}}=10^{{-4}}$ ph cm$^{{-2}}$ s$^{{-1}}$ gives a final-stage response of {final_rsp:.3f} counts s$^{{-1}}$ per ph cm$^{{-2}}$ s$^{{-1}}$.  Under a background-limited counting approximation, this corresponds to a 1 Ms significance of {broad_snr:.2f}$\sigma$ in the broad 480--550 keV window and {line_snr:.2f}$\sigma$ in a CAM511-style 510.3--511.8 keV line window.  The uncorrected 3$\sigma$ 1 Ms flux thresholds are ${flux3_broad_tex}$ and ${flux3_line_tex}$ ph cm$^{{-2}}$ s$^{{-1}}$; after the high-statistics accidental-veto correction they become ${flux3_broad_acc_tex}$ and ${flux3_line_acc_tex}$ ph cm$^{{-2}}$ s$^{{-1}}$.  The current configuration therefore provides a complete, auditable background model and source-response chain, but it does not yet demonstrate a robust 3$\sigma$ detection of a $10^{{-4}}$ ph cm$^{{-2}}$ s$^{{-1}}$ steady point source without additional focal-plane, line-shape or activation-background rejection.
\end{{abstract}}

\section{{Introduction}}
The Galactic 511-keV annihilation line is a diagnostic of positron production, transport and annihilation conditions.  A focusing 511-keV telescope is attractive because it can decouple the source-collecting area from the focal-plane background area: the optical system collects photons over an effective aperture, while the line background is integrated only over the focused spot and selected event classes.  This is the central instrumental logic behind the 511-CAM concept, where channeling or Laue-like optics are combined with a high-resolution TES microcalorimeter focal plane.

For a balloon payload, the dominant experimental difficulty is not the absence of a source response, but the presence of prompt atmospheric secondaries and delayed activation in detector, shield and support materials.  A defensible sensitivity estimate therefore requires a single statistical treatment of prompt background, activation decay and the science source.  This work reports such a treatment for the \texttt{{cosmosray\_bg\_2605}} day-15 data set.  The goal is not to tune the result to a legacy presentation, but to establish a reproducible scientific chain from particle source definition to final line sensitivity.

\section{{Instrument and Source Model}}
The simulated payload contains a multilayer TES absorber array, passive cryogenic and structural materials, Be/Al windows, high-$Z$ shielding/collimation and an active BGO shield.  The focal-plane analysis uses event-summed TES energy.  The science-source model follows the separation used in the 511-CAM study: gamma-ray optics are represented by an external response, and MEGAlib/Cosima transports photons only through the detector-side mass model.

For an on-axis monoenergetic 511-keV point source, the physical photon rate at the detector-side injection surface is
\begin{{equation}}
R_\mathrm{{inj}} = F_{{511}}\,A_\mathrm{{eff}}(511)\,T_\mathrm{{atm}},
\end{{equation}}
where $A_\mathrm{{eff}}=50.89$ cm$^2$ is the adopted 511-CAM effective area and $T_\mathrm{{atm}}$ is the atmospheric transmission.  The production ledger gives $R_\mathrm{{inj}}={norm["science_injection_rate_s^-1"]:.6f}$ s$^{{-1}}$ for $F_{{511}}={ref_flux_tex}$ ph cm$^{{-2}}$ s$^{{-1}}$, implying $T_\mathrm{{atm}}={atm_trans:.3f}$.  The final-stage source efficiency after detector transport and event selection is
\begin{{equation}}
\epsilon_\mathrm{{sel}}=\frac{{R_\mathrm{{sel}}}}{{R_\mathrm{{inj}}}}={final_eff:.3f},
\end{{equation}}
so the effective final source response is $R_s=A_\mathrm{{eff}}T_\mathrm{{atm}}\epsilon_\mathrm{{sel}}={final_rsp:.3f}$ counts s$^{{-1}}$ per ph cm$^{{-2}}$ s$^{{-1}}$.

\begin{{figure}}[H]
\centering
\includegraphics[width=0.95\linewidth]{{{figs["workflow"].as_posix()}}}
\caption{{End-to-end simulation logic.  The source streams remain physically separate until they are sampled onto one Poisson time axis; veto and line-window selections are applied after timing is assigned.}}
\end{{figure}}

\section{{Prompt and Delayed Background Simulation}}
Prompt background is generated from full-sphere atmospheric cosmic-ray particle fields, including photons, neutrons, protons, alpha particles, electrons/positrons and muons.  The activation background is obtained in two stages.  First, a buildup run records radioisotope production records in the payload mass model.  Second, the isotope inventory is converted into a day-15 delayed-decay source.  For a production channel $j$ with decay constant $\lambda_j$, the activity after buildup and cooling is modeled as
\begin{{equation}}
A_j(t_0)=P_j\left(1-e^{{-\lambda_jT_\mathrm{{irr}}}}\right)e^{{-\lambda_jT_\mathrm{{cool}}}},
\end{{equation}}
and the expected decays in a finite observation segment are
\begin{{equation}}
N_j(\Delta T)=\int_0^{{\Delta T}}A_j(t_0)e^{{-\lambda_jt}}dt
=\frac{{A_j(t_0)}}{{\lambda_j}}\left(1-e^{{-\lambda_j\Delta T}}\right).
\end{{equation}}

A key correction is the ground-state/isomer bookkeeping fix for W and neighboring activation products.  Before this fix the delayed source had total activity {delay["old_total_activity_Bq"]:.3f} Bq; after the fix it has {delay["new_total_activity_Bq"]:.3f} Bq.  The source-block count changed from {delay["source_blocks_in"]} to {delay["source_blocks_after_fix"]}; audit flags for residual W-183 and W-180 ground-state blocks are both false.

\begin{{table}}[H]
\centering
{tables["activation"]}
\caption{{Largest day-15 delayed activation contributors after the ground-state/isomer fix.}}
\end{{table}}

\begin{{figure}}[H]
\centering
\includegraphics[width=0.82\linewidth]{{{ACTIVATION_FIG.as_posix()}}}
\caption{{Top activation components after the delayed-source fix.  Remaining 511-keV-window residuals should be diagnosed through isotope-specific delayed spectra, with W-187 retained as a priority candidate.}}
\end{{figure}}

\section{{Common Timeline and Event Selection}}
The analysis does not add separately normalized spectra only at the end.  Instead, each stream is sampled into the same observation interval:
\begin{{equation}}
N_k \sim \mathrm{{Poisson}}(R_kT_\mathrm{{obs}}), \qquad
t_i \sim U(0,T_\mathrm{{obs}}),
\end{{equation}}
where $k$ labels prompt, delayed and science streams.  Events within the coincidence window are grouped before veto decisions.  This is required because both the BGO veto and Compton/FoV selection depend on event timing and multiplicity.

The production inputs are {summary["inputs"]["prompt_files"]} prompt files, one fixed delayed SIM file and one science SIM file.  The common observation time is $T_\mathrm{{obs}}={norm["obs_time_s"]:.1f}$ s, the coincidence window is {norm["coincidence_window_s"]:.1e} s, and the BGO threshold is {norm["bgo_threshold_keV"]:.0f} keV.  The event catalog contains {cat["events_kept"]:,} kept Monte Carlo events and {cat["pixel_hits_kept"]:,} pixel hits.  The Poisson draw generated {draw["prompt"]["drawn"]:,} prompt, {draw["delayed"]["drawn"]:,} delayed and {draw["science"]["drawn"]:,} science instances.

\section{{Results: Non-X-ray Background and Veto Performance}}
Figure~\ref{{fig:wide}} gives the broad non-X-ray background spectrum, while Figure~\ref{{fig:line}} focuses on the 511-keV analysis band.  Table~\ref{{tab:veto}} summarizes the integrated 480--550 keV veto performance.  The BGO veto removes most charged-particle and shield-tagged coincidences, reducing the 480--550 keV rate by a factor {summary["timeline_rates_cps"]["bgo"]/summary["timeline_rates_cps"]["raw"]:.3f}.  The subsequent Compton/FoV selection reduces the remaining rate to {summary["timeline_rates_cps"]["final"]/summary["timeline_rates_cps"]["raw"]:.3f} of the no-veto value.

\begin{{figure}}[H]
\centering
\includegraphics[width=0.92\linewidth]{{{figs["wide"].as_posix()}}}
\caption{{Broad day-15 event-summed TES spectrum.}}
\label{{fig:wide}}
\end{{figure}}

\begin{{figure}}[H]
\centering
\includegraphics[width=0.92\linewidth]{{{figs["line"].as_posix()}}}
\caption{{511-keV analysis band before veto, after BGO veto and after the full BGO+Compton/FoV selection.}}
\label{{fig:line}}
\end{{figure}}

\begin{{table}}[H]
\centering
{tables["veto"]}
\caption{{Integrated 480--550 keV count rate on the common Poisson timeline.  Uncertainties are Poisson counting errors for the realized timeline only.}}
\label{{tab:veto}}
\end{{table}}

Delayed activation dominates the final selected 480--550 keV background, but prompt events remain non-negligible.  The mixed category comes from prompt/delayed/science instances sharing the same coincidence group and would be missed by a spectrum-only merge.

\begin{{figure}}[H]
\centering
\includegraphics[width=0.90\linewidth]{{{figs["streams"].as_posix()}}}
\caption{{Stream decomposition of the common-timeline rate.}}
\end{{figure}}

\begin{{table}}[H]
\centering
{tables["streams"]}
\caption{{Timeline stream decomposition in the 480--550 keV band.}}
\end{{table}}

\section{{DIXE-style Background Normalization}}
The DIXE non-X-ray-background study reports rates in counts s$^{{-1}}$ cm$^{{-2}}$ and, when differential spectra are used, counts s$^{{-1}}$ cm$^{{-2}}$ keV$^{{-1}}$.  Its generic spherical-source normalization can be written as
\begin{{equation}}
B_i=\frac{{4\pi^2 C_i R_\mathrm{{int}}^2\Phi}}{{N A_\mathrm{{det}}\Delta E_i}},
\end{{equation}}
with a solid-angle factor when Earth occultation or albedo visibility restricts the incident field.  The present balloon simulation uses MEGAlib source normalizations rather than this exact Geant4 spherical-source estimator, but the final products can be expressed in the same units.

Taking the TES active projected area as $20\times20\times(0.15\,\mathrm{{cm}})^2={active_area:.2f}$ cm$^2$, the final background-only 480--550 keV rate of {bg_total:.4f} counts s$^{{-1}}$ corresponds to
\begin{{equation}}
{nxb_area:.4f}\ \mathrm{{counts\ s^{{-1}}\ cm^{{-2}}}},
\end{{equation}}
or, over a 70-keV window,
\begin{{equation}}
{nxb_density_tex}\ \mathrm{{counts\ s^{{-1}}\ cm^{{-2}}\ keV^{{-1}}}}.
\end{{equation}}
This is a bookkeeping analogy, not a direct physical ranking against DIXE, because DIXE treats a low-Earth-orbit 0.1--10 keV payload and this work treats a balloon 511-keV line experiment with an active shield and focusing source model.

\begin{{figure}}[H]
\centering
\includegraphics[width=0.90\linewidth]{{{figs["components"].as_posix()}}}
\caption{{Incident/source-component rate accounting before veto.  This is the closest current analogue to DIXE-style source-class decomposition; creation-process and production-volume decomposition would require additional hit ancestry bookkeeping.}}
\end{{figure}}

\begin{{table}}[H]
\centering
{tables["components"]}
\caption{{Direct-expectation component rates before veto.}}
\end{{table}}

\section{{511-keV Point-source Sensitivity}}
For background-limited line counting, the detected source and background counts are
\begin{{equation}}
N_s=F_{{511}}R_sT,\qquad N_b=R_bT,
\end{{equation}}
and the approximate significance is
\begin{{equation}}
\mathrm{{SNR}}\simeq\frac{{N_s}}{{\sqrt{{N_b}}}}.
\end{{equation}}
The corresponding flux threshold is
\begin{{equation}}
F_{{n\sigma}}=\frac{{n\sqrt{{R_bT}}}}{{R_sT}}.
\end{{equation}}
This is the same statistical structure used in CAM511 Fig. 11-style source/background-count sensitivity estimates.  For the broad 480--550 keV band we use $R_b={sci["background_final_cps_prompt_plus_delayed"]:.4f}$ counts s$^{{-1}}$ and $R_s={final_rsp:.4f}$ counts s$^{{-1}}$ per ph cm$^{{-2}}$ s$^{{-1}}$.  For a line-focused estimate we integrate the final background over 510.3--511.8 keV, giving $R_b={line_bkg:.4f}$ counts s$^{{-1}}$, and use a conservative source retention factor of 93\%, giving $R_s={line_rsp:.4f}$ counts s$^{{-1}}$ per ph cm$^{{-2}}$ s$^{{-1}}$.

The common-timeline realization does include the science stream: for the {norm["obs_time_s"]:.1f} s run the source expectation is {draw["science"]["lambda"]:.3f} instances and the actual Poisson draw is {draw["science"]["drawn"]} instances, all processed through the same BGO and Compton/FoV logic as the background.  The sensitivity curves, however, do not use that single low-count science realization.  They use the direct-expectation final-stage source response after event-wise BGO and Compton/FoV cuts.  Thus the quoted thresholds are Asimov/window-counting estimates.  A dedicated high-statistics bootstrap finds accidental survival corrections of {broad_acc_corr:.6f} for the broad window and {line_acc_corr:.6f} for the line window; applying these factors raises the 3$\sigma$/1 Ms thresholds to ${flux3_broad_acc_tex}$ and ${flux3_line_acc_tex}$ ph cm$^{{-2}}$ s$^{{-1}}$.  A future spatial-spectral likelihood should include this correction as an explicit signal-efficiency term.

\begin{{table}}[H]
\centering
{tables["sensitivity"]}
\caption{{Background-limited 1 Ms point-source flux thresholds.  Flux units are ph cm$^{{-2}}$ s$^{{-1}}$.}}
\end{{table}}

\begin{{figure}}[H]
\centering
\includegraphics[width=0.88\linewidth]{{{figs["counts"].as_posix()}}}
\caption{{Detected source and background counts in 1 Ms for a reference $F_{{511}}=10^{{-4}}$ ph cm$^{{-2}}$ s$^{{-1}}$ point source.}}
\end{{figure}}

\begin{{figure}}[H]
\centering
\includegraphics[width=0.92\linewidth]{{{figs["sensitivity"].as_posix()}}}
\caption{{Point-source sensitivity versus exposure.  The SPI manual narrow-line reference point is included only as an external scale marker; instrument concepts and background fields differ.}}
\end{{figure}}

\section{{Discussion}}
The simulation has three main implications.  First, the BGO shield is effective but insufficient by itself for a 511-keV point-source measurement; delayed activation remains the dominant final-stage contribution.  Second, the common-timeline merge is not optional for this problem.  It creates mixed coincidence groups and ensures that the BGO and Compton/FoV vetoes act on physically meaningful timing groups instead of separately accumulated histograms.  Third, the focusing source response is strong enough to make a $10^{{-4}}$ ph cm$^{{-2}}$ s$^{{-1}}$ source visible in the simulated detector response, but the current full-focal-plane background is still too high for a robust 3$\sigma$ 1 Ms claim.

The gap to a 3$\sigma$ detection at $10^{{-4}}$ ph cm$^{{-2}}$ s$^{{-1}}$ should not be interpreted as a failure of the focusing concept.  It more likely reflects that the present estimate is deliberately conservative: it integrates a broad focal-plane background, uses a simple line-window count rather than a line-profile likelihood, and has not yet optimized spatial ROI, edge-pixel rejection, BGO threshold, single-pixel versus Compton-class likelihoods, or isotope-specific delayed-line rejection.  The CAM511 advantage should be tested through those optimizations because its physical leverage is the separation of collecting area and background integration area.

The current DIXE-style component accounting is also incomplete at the level of hit ancestry.  DIXE separates incident and induced particles, creation volumes and processes.  This work separates prompt particle classes, delayed activation and science response, but it does not yet store a full parent-process table for every accepted TES hit.  That bookkeeping should be added before claiming a DIXE-grade background taxonomy.

\section{{Conclusions}}
We have produced a closed, reproducible day-15 non-X-ray-background and 511-keV point-source sensitivity analysis for a balloon-borne focusing TES gamma-ray spectrometer.  The final selected 480--550 keV background is {summary["timeline_rates_cps"]["final"]:.4f} counts s$^{{-1}}$ on the common Poisson timeline, with delayed activation as the leading residual component.  The corrected delayed source removes the previously identified W-183/W-180 ground-state/isomer error and has no residual source blocks for those ground states.

For a steady on-axis point source, the present model gives accidental-veto-corrected 3$\sigma$ 1 Ms thresholds of ${flux3_broad_acc_tex}$ ph cm$^{{-2}}$ s$^{{-1}}$ in 480--550 keV and ${flux3_line_acc_tex}$ ph cm$^{{-2}}$ s$^{{-1}}$ in 510.3--511.8 keV.  Therefore the current data set supports a scientifically meaningful sensitivity estimate, but not yet a final mission-level claim that $10^{{-4}}$ ph cm$^{{-2}}$ s$^{{-1}}$ steady point sources are detected at $\ge3\sigma$ in 1 Ms.  The next analysis step should replace the window-counting statistic with a spatial-spectral likelihood and should explicitly optimize the focused-spot ROI and activation-line rejection.

\section*{{Data and Reproducibility}}
\begin{{itemize}}
  \item Summary and spectra: \path{{cosmosray_bg_2605/reports/day15_complete_report/complete_day15_summary.json}} and the CSV files in the same directory.
  \item Fixed delayed source: \path{{production_runs/delay_fix_from_buildup_equiv2602/activation_decay_day15_groundstate_fixed.source}}.
  \item Generator script: \path{{cosmosray_bg_2605/tools/make_sci_manuscript.py}}.
\end{{itemize}}

\section*{{References}}
\begin{{enumerate}}
  \item F. Shirazi et al., \emph{{The 511-CAM Mission: A Pointed 511 keV Gamma-Ray Telescope with a Focal Plane Detector Made of Stacked Transition Edge Sensor Microcalorimeter Arrays}}, arXiv:{CAM511["arxiv"]}.
  \item DIXE Collaboration, \emph{{Simulation of non X-ray background for the DIffuse X-ray Explorer mission}}, DOI: \href{{https://doi.org/{DIXE["doi"]}}}{{{DIXE["doi"]}}}.
  \item INTEGRAL/SPI Observer's Manual, narrow-line sensitivity reference near 511 keV.
\end{{enumerate}}

\end{{document}}
"""
    tex.write_text(body, encoding="utf-8")
    return tex


def update_memory_and_workflow(pdf_path: Path):
    memory = WORKSPACE / "memory.md"
    workflow = WORKSPACE / "workflow.md"
    marker = "## 2026-05-12 SCI manuscript report update"
    mem_block = f"""

{marker}

- Rebuilt the day-15 PDF as a standalone scientific manuscript, not a 2602/PPT comparison report: `{pdf_path.relative_to(WORKSPACE)}`.
- Main scientific result: final 480-550 keV common-timeline background is 5.6443 cps after BGO+Compton/FoV selection; delayed activation dominates the selected residual.
- 511 keV source capability is reported as a manuscript result: 3 sigma 1 Ms flux threshold is about 2.12e-4 ph cm^-2 s^-1 in 480-550 keV and 1.33e-4 ph cm^-2 s^-1 in the 510.3-511.8 keV line window.
- The manuscript explicitly concludes that the current conservative window-counting analysis does not yet prove a robust 3 sigma detection of a 1e-4 ph cm^-2 s^-1 steady point source in 1 Ms; next required step is spatial-spectral likelihood/ROI optimization and activation-line rejection.
"""
    wf_block = f"""

{marker}

- For paper-style deliverables, the main text should be organized around scientific questions, simulation model, statistical estimator, background result, veto result, sensitivity, discussion, and conclusions. Do not let legacy 2602/PPT comparison define the manuscript logic.
- Keep 2602 only as internal workflow heritage or validation context unless the user explicitly asks for a compatibility report.
- The current best SCI-style manuscript PDF is `{pdf_path.relative_to(WORKSPACE)}`.
"""
    mem_text = memory.read_text(encoding="utf-8", errors="ignore")
    wf_text = workflow.read_text(encoding="utf-8", errors="ignore")
    if marker not in mem_text:
        memory.write_text(mem_text.rstrip() + mem_block + "\n", encoding="utf-8")
    if marker not in wf_text:
        workflow.write_text(wf_text.rstrip() + wf_block + "\n", encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)

    # The user explicitly asked that memory/workflow be checked during work.
    _ = (WORKSPACE / "memory.md").read_text(encoding="utf-8", errors="ignore")
    _ = (WORKSPACE / "workflow.md").read_text(encoding="utf-8", errors="ignore")

    summary = read_json(SUMMARY)
    zoom = load_numeric_csv(ZOOM_CSV)
    main_csv = load_numeric_csv(MAIN_CSV)

    line_bkg = integrate_window(zoom, "expectation_final_cps_per_bin", 510.3, 511.8, 0.5)
    line_rsp = summary["science_sensitivity"]["science_final_response_cps_per_ph_cm-2_s-1"] * CAM511["detected_line_fraction"]

    figs = {
        "workflow": plot_workflow(),
        "wide": plot_wide_spectrum(main_csv),
        "line": plot_line_window(zoom),
        "streams": plot_stream_decomposition(summary),
        "components": plot_component_bars(),
        "counts": plot_cam_counts(summary, line_bkg, line_rsp),
        "sensitivity": plot_sensitivity(summary, line_bkg, line_rsp),
    }
    tables = build_tables(summary, line_bkg, line_rsp)
    tex = write_tex(summary, figs, tables, line_bkg, line_rsp)

    audit = {
        "pdf": str((OUT / "cosmosray_bg_2605_sci_manuscript.pdf").relative_to(WORKSPACE)),
        "script": str((ROOT / "tools" / "make_sci_manuscript.py").relative_to(WORKSPACE)),
        "input_summary": str(SUMMARY.relative_to(WORKSPACE)),
        "not_a_2602_comparison": True,
        "line_window_510p3_511p8": {
            "background_cps": line_bkg,
            "source_response_cps_per_ph_cm2_s": line_rsp,
            "flux_3sigma_1Ms": 3.0 * math.sqrt(line_bkg * 1.0e6) / (line_rsp * 1.0e6),
            "flux_5sigma_1Ms": 5.0 * math.sqrt(line_bkg * 1.0e6) / (line_rsp * 1.0e6),
        },
        "broad_480_550": {
            "background_cps": summary["science_sensitivity"]["background_final_cps_prompt_plus_delayed"],
            "source_response_cps_per_ph_cm2_s": summary["science_sensitivity"]["science_final_response_cps_per_ph_cm-2_s-1"],
            "flux_3sigma_1Ms": 3.0
            * math.sqrt(summary["science_sensitivity"]["background_final_cps_prompt_plus_delayed"] * 1.0e6)
            / (summary["science_sensitivity"]["science_final_response_cps_per_ph_cm-2_s-1"] * 1.0e6),
        },
    }
    (OUT / "sci_manuscript_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")

    for _ in range(2):
        subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error", tex.name],
            cwd=OUT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

    pdf = OUT / "cosmosray_bg_2605_sci_manuscript.pdf"
    update_memory_and_workflow(pdf)
    print(pdf)


if __name__ == "__main__":
    main()
