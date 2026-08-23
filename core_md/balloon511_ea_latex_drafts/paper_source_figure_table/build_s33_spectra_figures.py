#!/usr/bin/env python3
"""Section 3.3 stage-wise spectra + multiplicity figures.

Data source: engineering/ea_detector_response_closure_20260713/data/.  The
Mass_model_511_fullstat_v1 catalogue is evaluated with the paper's 420 eV FWHM
per-pixel response and 0.3 keV measured-hit threshold before the retained
window/anticoincidence/Compton-FoV classification.

Produces:
  fig_s33_spectrum_normalized.png      (for 3.3.1: normalized three-stream spectrum)
  fig_s33_spectrum_anticoincidence.png (for 3.3.2: raw vs post-anticoincidence)
  fig_s33_compton_multiplicity.png     (for 3.3.3: raw/anti/Compton + hit multiplicity)
"""
from __future__ import annotations
import csv, json, os
from pathlib import Path
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-tes511")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[2] / "engineering/ea_detector_response_closure_20260713/data"
SPEC = DATA / "reference_response_spectra_480_550.csv"
MULT = DATA / "reference_response_multiplicity.json"

INK, BLUE, RED, GREEN, ORANGE, GRAY = "#1b1b1b", "#1f6f8b", "#c0392b", "#27803a", "#e08a1e", "#7a7a7a"
FLOOR = 3e-5  # cps/keV floor for log axis


def load_spectra():
    rows = list(csv.DictReader(open(SPEC)))
    lo = np.array([float(r["energy_lo_keV"]) for r in rows])
    hi = np.array([float(r["energy_hi_keV"]) for r in rows])
    col = lambda name: np.array([float(r[name]) for r in rows])
    return lo, hi, col


def step_spec(ax, lo, hi, y, color, label, lw=1.6, ls="-", fill=False):
    edges = np.concatenate([lo, [hi[-1]]])
    yv = np.concatenate([np.maximum(y, FLOOR), [FLOOR]])
    ax.step(edges, yv, where="post", color=color, lw=lw, ls=ls, label=label)
    if fill:
        ax.fill_between(edges, FLOOR, yv, step="post", color=color, alpha=0.18)


def fig_normalized(lo, hi, col):
    fig, ax = plt.subplots(figsize=(6.6, 3.7))
    step_spec(ax, lo, hi, col("science_raw_cps_per_keV"), RED, "focused signal")
    step_spec(ax, lo, hi, col("prompt_raw_cps_per_keV"), BLUE, "prompt background")
    step_spec(ax, lo, hi, col("delayed_raw_cps_per_keV"), GREEN, "delayed activation")
    ax.axvspan(510.58, 511.42, color=ORANGE, alpha=0.18, zorder=0, label=r"$W_{511}$ line window")
    ax.set_yscale("log")
    ax.set_xlim(480, 550)
    ax.set_ylim(FLOOR * 0.7, 2.0)
    ax.set_xlabel("measured summed TES energy [keV]")
    ax.set_ylabel(r"rate density [cps keV$^{-1}$]")
    ax.set_title("Response-convolved three-stream spectrum on the common axis", fontsize=9.5)
    ax.legend(fontsize=7.6, loc="upper left", framealpha=0.9)
    fig.tight_layout()
    out = HERE / "fig_s33_spectrum_normalized.png"
    fig.savefig(out, dpi=200); fig.savefig(out.with_suffix(".svg")); plt.close(fig)
    print("wrote", out.name)


def fig_anticoincidence(lo, hi, col):
    bg_raw = col("prompt_raw_cps_per_keV") + col("delayed_raw_cps_per_keV")
    bg_act = col("prompt_active_cps_per_keV") + col("delayed_active_cps_per_keV")
    fig, ax = plt.subplots(figsize=(6.6, 3.7))
    step_spec(ax, lo, hi, bg_raw, GRAY, "raw (in-window, pre-veto)", lw=1.8)
    step_spec(ax, lo, hi, bg_act, BLUE, "after CsI anticoincidence", lw=1.8, fill=True)
    ax.axvspan(510.58, 511.42, color=ORANGE, alpha=0.16, zorder=0)
    ax.set_yscale("log")
    ax.set_xlim(480, 550)
    ax.set_ylim(FLOOR * 0.7, 0.6)
    ax.set_xlabel("measured summed TES energy [keV]")
    ax.set_ylabel(r"rate density [cps keV$^{-1}$]")
    ax.set_title("Prompt+delayed background: anticoincidence effect", fontsize=9.5)
    ax.legend(fontsize=7.8, loc="upper left", framealpha=0.9)
    mult = json.load(open(MULT))["streams"]
    raw_prompt = mult["prompt"]["stages"]["raw"]["total"]
    raw_delayed = mult["delayed"]["stages"]["raw"]["total"]
    active_prompt = mult["prompt"]["stages"]["active"]["total"]
    active_delayed = mult["delayed"]["stages"]["active"]["total"]
    ax.text(0.97, 0.92, f"broad-band events\n{raw_prompt}+{raw_delayed} raw $\\to$ {active_prompt}+{active_delayed} after veto",
            transform=ax.transAxes, ha="right", va="top", fontsize=7.4,
            bbox=dict(boxstyle="round", fc="white", ec="0.7"))
    fig.tight_layout()
    out = HERE / "fig_s33_spectrum_anticoincidence.png"
    fig.savefig(out, dpi=200); fig.savefig(out.with_suffix(".svg")); plt.close(fig)
    print("wrote", out.name)


def fig_compton_multiplicity(lo, hi, col):
    mult = json.load(open(MULT))["streams"]
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 3.9))

    # (a) raw / active / compton background spectrum
    ax = axes[0]
    bg = lambda st: col(f"prompt_{st}_cps_per_keV") + col(f"delayed_{st}_cps_per_keV")
    step_spec(ax, lo, hi, bg("raw"), GRAY, "raw", lw=1.7)
    step_spec(ax, lo, hi, bg("active"), BLUE, "after anticoincidence", lw=1.7)
    step_spec(ax, lo, hi, bg("compton"), RED, "after anti + Compton/FoV", lw=1.7, fill=True)
    ax.axvspan(510.58, 511.42, color=ORANGE, alpha=0.16, zorder=0)
    ax.set_yscale("log"); ax.set_xlim(480, 550); ax.set_ylim(FLOOR * 0.7, 0.6)
    ax.set_xlabel("measured summed TES energy [keV]")
    ax.set_ylabel(r"rate density [cps keV$^{-1}$]")
    ax.set_title("(a) background spectrum through the two veto layers", fontsize=9.3)
    ax.legend(fontsize=7.4, loc="upper left", framealpha=0.9)

    # (b) hit-multiplicity of candidate groups (compton stage) per stream
    ax = axes[1]
    streams = ["prompt", "delayed", "science"]
    buckets = ["n1", "n2", "n3plus"]
    blabels = ["single", "2-hit", "$\\geq$3-hit"]
    bcolors = [GRAY, BLUE, RED]
    x = np.arange(len(streams)); w = 0.26
    for i, (b, lab, c) in enumerate(zip(buckets, blabels, bcolors)):
        vals = [mult[s]["stages"]["compton"][b] for s in streams]
        bars = ax.bar(x + (i - 1) * w, np.maximum(vals, 0.5), w, color=c, label=lab)
        for xi, v in zip(x + (i - 1) * w, vals):
            ax.text(xi, max(v, 0.5) * 1.15, str(v), ha="center", va="bottom", fontsize=6.6)
    ax.set_yscale("log"); ax.set_ylim(0.5, 1e5)
    ax.set_xticks(x); ax.set_xticklabels(["prompt", "delayed", "signal"])
    ax.set_ylabel("selected candidate groups")
    ax.set_title("(b) hit multiplicity of selected groups", fontsize=9.3)
    ax.legend(fontsize=7.6, ncol=3, loc="upper left", framealpha=0.9)
    fig.tight_layout()
    out = HERE / "fig_s33_compton_multiplicity.png"
    fig.savefig(out, dpi=200); fig.savefig(out.with_suffix(".svg")); plt.close(fig)
    print("wrote", out.name)


def main():
    lo, hi, col = load_spectra()
    fig_normalized(lo, hi, col)
    fig_anticoincidence(lo, hi, col)
    fig_compton_multiplicity(lo, hi, col)


if __name__ == "__main__":
    main()
