#!/usr/bin/env python3
"""Join the audited S3d-O8 signal/background edge-cut scans.

This script does not rerun transport.  It combines two independently replayed
authorities on the same fixed TES pixel-centre radius:

* the official post-Be-window stage04 focused-signal bank; and
* matched prompt Step05 + delayed W2 events folded over the official 20-day
  mission trajectory.

The decision quantity is Fmin(cut)/Fmin(base) = sqrt(fB20)/fS20.  Pixel count
or detector area is retained only as geometry context and is never substituted
for the measured background retention.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
AUDIT = ROOT / "audit"
FIGURES = ROOT / "figures"

BASELINE_S20 = 1645.3877530659986
BASELINE_B20 = 144203.8420859011
PROMPT_QUANTUM_20D = 27699.48971701258
BASELINE_PROMPT_ROOTS = 2
BASELINE_F3 = 3.0e-4 * math.sqrt(BASELINE_B20) / BASELINE_S20


def signal_columns(policy: str) -> tuple[str, str]:
    return {
        "centroid_radius": ("centroid_gate_events", "centroid_gate_fS"),
        "all_pixels_inside": ("all_measured_pixels_inside_events", "all_measured_pixels_inside_fS"),
        "centroid_radius_and_L3": (
            "centroid_and_max_layer_le3_events",
            "centroid_and_max_layer_le3_fS",
        ),
    }[policy]


def background_rows(background: pd.DataFrame, policy: str) -> pd.DataFrame:
    if policy == "centroid_radius":
        mask = (background["cut_semantics"] == "fixed_centroid") & (
            background["scan_family"] == "pure_radial"
        )
    elif policy == "all_pixels_inside":
        mask = (background["cut_semantics"] == "all_fixed_pixels") & (
            background["scan_family"] == "pure_radial"
        )
    elif policy == "centroid_radius_and_L3":
        mask = (
            (background["cut_semantics"] == "fixed_centroid")
            & (background["scan_family"] == "joint_radius_layer")
            & (background["deepest_layer_max"] == 3)
        )
    else:
        raise ValueError(policy)
    return background.loc[mask].copy()


def build_scan() -> pd.DataFrame:
    signal = pd.read_csv(DATA / "agent_signal_edge_cut.csv")
    background = pd.read_csv(DATA / "agent_background_edge_cut.csv")
    rows: list[dict[str, object]] = []

    for policy in ("centroid_radius", "all_pixels_inside", "centroid_radius_and_L3"):
        event_col, fs_col = signal_columns(policy)
        bkg = background_rows(background, policy)
        merged = signal.merge(
            bkg,
            left_on="radius_cm",
            right_on="radius_cut_cm",
            how="inner",
            validate="one_to_one",
        )
        merged = merged[merged["radius_cm"].between(0.45, 1.80)].copy()
        for row in merged.itertuples(index=False):
            fs = float(getattr(row, fs_col))
            fb = float(row.background_counts_20d_retention_fB)
            fmin_ratio = math.sqrt(fb) / fs
            delayed_counts = float(row.background_counts_20d) - int(row.prompt_events) * PROMPT_QUANTUM_20D
            no_prompt_credit_counts = delayed_counts + BASELINE_PROMPT_ROOTS * PROMPT_QUANTUM_20D
            no_prompt_credit_fb = no_prompt_credit_counts / BASELINE_B20
            no_prompt_credit_ratio = math.sqrt(no_prompt_credit_fb) / fs
            rows.append(
                {
                    "policy": policy,
                    "radius_cm": float(row.radius_cm),
                    "physical_TES_pixels_inside": int(row.physical_TES_pixels_inside),
                    "physical_TES_pixel_fraction": float(row.physical_TES_pixel_fraction),
                    "signal_events": int(getattr(row, event_col)),
                    "signal_retention_fS": fs,
                    "signal_S20": BASELINE_S20 * fs,
                    "prompt_events": int(row.prompt_events),
                    "prompt_rate_cps": float(row.prompt_rate_cps),
                    "delayed_events": int(row.delayed_events),
                    "delayed_rate_cps": float(row.delayed_rate_cps),
                    "background_counts_20d": float(row.background_counts_20d),
                    "background_counts_20d_neff": float(row.background_counts_20d_neff),
                    "background_retention_fB": fb,
                    "background_retention_sigma_quantum_proxy": float(
                        row.background_counts_20d_retention_sigma_proxy
                    ),
                    "minimum_signal_retention_for_improvement": math.sqrt(fb),
                    "passes_central_improvement_gate": bool(fs > math.sqrt(fb)),
                    "central_F3": BASELINE_F3 * fmin_ratio,
                    "central_F3_ratio": fmin_ratio,
                    "central_improvement_percent": 100.0 * (1.0 - fmin_ratio),
                    "no_prompt_reduction_credit_background_counts_20d": no_prompt_credit_counts,
                    "no_prompt_reduction_credit_fB": no_prompt_credit_fb,
                    "no_prompt_reduction_credit_F3": BASELINE_F3 * no_prompt_credit_ratio,
                    "no_prompt_reduction_credit_F3_ratio": no_prompt_credit_ratio,
                    "scope": (
                        "post-Be-window stage04 signal; matched 20-day prompt Step05 + delayed W2 background"
                    ),
                }
            )
    scan = pd.DataFrame(rows).sort_values(["policy", "radius_cm"]).reset_index(drop=True)
    return scan


def selected_record(scan: pd.DataFrame, policy: str, radius: float) -> dict[str, object]:
    row = scan[(scan["policy"] == policy) & np.isclose(scan["radius_cm"], radius)]
    if len(row) != 1:
        raise AssertionError((policy, radius, len(row)))
    return row.iloc[0].to_dict()


def plot_scan(scan: pd.DataFrame) -> None:
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9.2,
            "axes.titlesize": 11.2,
            "axes.labelsize": 9.5,
            "axes.edgecolor": "#7d8992",
            "axes.linewidth": 0.7,
            "grid.color": "#dce2e7",
            "grid.linewidth": 0.6,
        }
    )
    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(14.6, 6.8), gridspec_kw={"wspace": 0.28})
    fig.subplots_adjust(left=0.065, right=0.985, top=0.80, bottom=0.19)
    fig.suptitle(
        "S3d-O8 edge-pixel fiducialization: signal retention versus matched 20-day background",
        x=0.03,
        ha="left",
        fontsize=16.2,
        fontweight="bold",
        color="#172531",
    )
    fig.text(
        0.03,
        0.865,
        "Fixed TES pixel centres in InstrumentFrame about the focused axis (y', z') = (0, -5.2 cm). "
        "Central curves use only two prompt roots; dashed robustness curves give zero credit for removing either root.",
        ha="left",
        fontsize=8.8,
        color="#455663",
    )

    centroid = scan[scan["policy"] == "centroid_radius"].sort_values("radius_cm")
    strict = scan[scan["policy"] == "all_pixels_inside"].sort_values("radius_cm")
    joint = scan[scan["policy"] == "centroid_radius_and_L3"].sort_values("radius_cm")

    x = centroid["radius_cm"].to_numpy()
    fs = centroid["signal_retention_fS"].to_numpy()
    fb = centroid["background_retention_fB"].to_numpy()
    sigma = centroid["background_retention_sigma_quantum_proxy"].to_numpy()
    pix = centroid["physical_TES_pixel_fraction"].to_numpy()
    ax0.plot(x, fs, "o-", color="#1f70b7", lw=2.0, ms=4.5, label="focused signal $f_S$")
    ax0.plot(x, fb, "s-", color="#cc4f3d", lw=2.0, ms=4.1, label="matched 20-day background $f_B$")
    ax0.fill_between(x, np.clip(fb - sigma, 0, 1), np.clip(fb + sigma, 0, 1), color="#cc4f3d", alpha=0.12, label="MC-quantum proxy")
    ax0.plot(x, pix, "^-", color="#7a838a", lw=1.25, ms=4.0, alpha=0.85, label="physical pixel-count fraction")
    ax0.set_title("a  Retention is measured; pixel count is context only", loc="left", fontweight="bold")
    ax0.set_xlabel("radial fiducial cut $r$ [cm]")
    ax0.set_ylabel("retained fraction of baseline")
    ax0.set_xlim(0.40, 1.85)
    ax0.set_ylim(0, 1.08)
    ax0.grid(True)
    ax0.legend(loc="upper left", frameon=True, framealpha=0.94, fontsize=8.1)

    ax1.plot(
        centroid["radius_cm"],
        1.0e5 * centroid["central_F3"],
        "o-",
        color="#1f70b7",
        lw=2.0,
        ms=4.5,
        label="centroid radius only (central)",
    )
    ax1.plot(
        strict["radius_cm"],
        1.0e5 * strict["central_F3"],
        "D-",
        color="#6b45a4",
        lw=1.45,
        ms=3.8,
        label="all hit pixels inside (diagnostic)",
    )
    ax1.plot(
        joint["radius_cm"],
        1.0e5 * joint["central_F3"],
        "s-",
        color="#298b65",
        lw=1.45,
        ms=3.8,
        label="centroid radius + deepest<=L3",
    )
    ax1.plot(
        centroid["radius_cm"],
        1.0e5 * centroid["no_prompt_reduction_credit_F3"],
        "--",
        color="#32424d",
        lw=1.65,
        label="centroid; zero prompt-removal credit",
    )
    ax1.axhline(1.0e5 * BASELINE_F3, color="#a83b2c", lw=1.0, ls=":", label="baseline 6.924e-5")
    ax1.axhline(3.0, color="#111820", lw=1.0, ls="--", label="mission target 3e-5")
    ax1.axvline(1.35, color="#c78918", lw=1.0, ls="--")
    ax1.axvspan(0.40, 1.10, color="#d66354", alpha=0.065)
    ax1.text(
        0.43,
        3.13,
        "apparent low-r dip:\nprompt 2 -> 0 quantum cliff",
        color="#8c3b31",
        fontsize=7.6,
        va="bottom",
    )
    r135 = selected_record(scan, "centroid_radius", 1.35)
    ax1.annotate(
        f"primary analysis cut r=1.35 cm\nF3={r135['central_F3']:.3g}  ({r135['central_improvement_percent']:.1f}% lower)",
        (1.35, 1.0e5 * float(r135["central_F3"])),
        xytext=(1.41, 5.78),
        textcoords="data",
        fontsize=7.8,
        color="#263640",
        arrowprops={"arrowstyle": "-", "lw": 0.7, "color": "#806217"},
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "#c9a441", "alpha": 0.94},
    )
    ax1.set_title("b  Minimum resolvable flux; lower is better", loc="left", fontweight="bold")
    ax1.set_xlabel("radial fiducial cut $r$ [cm]")
    ax1.set_ylabel(r"central $F_{3\sigma}$ [$10^{-5}$ ph cm$^{-2}$ s$^{-1}$]")
    ax1.set_xlim(0.40, 1.85)
    ax1.set_ylim(2.7, 7.65)
    ax1.grid(True)
    ax1.legend(loc="upper right", frameon=True, framealpha=0.95, fontsize=7.55)

    fig.text(
        0.03,
        0.075,
        "FACT: Fcut/Fbase = sqrt(fB20)/fS20.  The r=1.35 centroid cut retains 98.69% of signal and 57.60% of matched B20.\n"
        "UNKNOWN: a literal disabled-channel response and a statistically stable prompt survival fraction require new matched replay; "
        "the purple background curve is W2-only diagnostic.",
        fontsize=8.0,
        color="#41515d",
    )
    FIGURES.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "svg", "pdf"):
        fig.savefig(FIGURES / f"s3d_o8_edge_pixel_sensitivity.{suffix}", dpi=260 if suffix == "png" else None)
    plt.close(fig)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    AUDIT.mkdir(parents=True, exist_ok=True)
    scan = build_scan()
    scan.to_csv(DATA / "edge_pixel_fiducial_scan.csv", index=False)

    primary = selected_record(scan, "centroid_radius", 1.35)
    strict = selected_record(scan, "all_pixels_inside", 1.35)
    joint = selected_record(scan, "centroid_radius_and_L3", 1.35)
    branch = selected_record(scan, "centroid_radius", 1.20)
    checks = {
        "baseline_F3_formula": math.isclose(BASELINE_F3, 6.923750509150676e-5, rel_tol=0, abs_tol=1e-15),
        "primary_signal_retention": math.isclose(float(primary["signal_retention_fS"]), 0.9868964279303536, abs_tol=1e-14),
        "primary_background_retention": math.isclose(float(primary["background_retention_fB"]), 0.5760144003534774, abs_tol=1e-14),
        "primary_signal_beats_sqrt_background": bool(primary["passes_central_improvement_gate"]),
        "joint_F3": math.isclose(float(joint["central_F3"]), 5.144760816932151e-5, abs_tol=1e-14),
        "all_scan_values_finite": bool(np.isfinite(scan.select_dtypes(include=[np.number]).to_numpy()).all()),
    }
    audit = {
        "status": "PASS_EDGE_PIXEL_FIDUCIAL_JOIN" if all(checks.values()) else "FAIL_EDGE_PIXEL_FIDUCIAL_JOIN",
        "checks": checks,
        "scope": "S3d-O8 post-Be stage04 signal and matched prompt Step05 + delayed W2 20-day trajectory",
        "formula": "F3(cut)/F3(base) = sqrt(B20(cut)/B20(base)) / (S20(cut)/S20(base))",
        "baseline": {"S20": BASELINE_S20, "B20": BASELINE_B20, "central_F3": BASELINE_F3},
        "primary_analysis_candidate_r135_centroid": primary,
        "r135_all_pixels_inside_diagnostic": strict,
        "r135_centroid_and_L3_historical_joint": joint,
        "r120_centroid_sensitivity_branch": branch,
        "statistics_warning": (
            "Prompt baseline has only two equal-weight roots; background B20 Neff is small after cuts. "
            "Central minima are MC-quantized and are not promotion evidence."
        ),
        "scope_warning": (
            "Literal edge-channel disabling changes reconstructed energy/topology. The all-pixels-inside background "
            "curve only reapplies W2 and does not rerun Step05; it is diagnostic."
        ),
    }
    with (AUDIT / "edge_pixel_fiducial_validation.json").open("w") as handle:
        json.dump(audit, handle, indent=2, sort_keys=True)
        handle.write("\n")
    if not all(checks.values()):
        raise SystemExit(json.dumps(checks, indent=2))
    plot_scan(scan)


if __name__ == "__main__":
    main()
