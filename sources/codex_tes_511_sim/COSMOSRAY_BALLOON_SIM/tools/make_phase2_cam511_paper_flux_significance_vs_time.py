#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple CAM511 Fig. 11 3-sigma source significance time curve."""

from __future__ import annotations

import csv
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PHASE2 = ROOT / "reports" / "phase2_real_flight_physical_production"
R2 = ROOT / "reports2.0"

PROMPT = PHASE2 / "prompt_reweight_real" / "prompt_final_rate_by_time_window.csv"
SCI_TRANS = PHASE2 / "environment_grid_real" / "science_atmospheric_transmission.csv"
DAY15_RATES = PHASE2 / "tables" / "image8_style_component_rates.csv"
DELAYED_ACTIVITY = R2 / "04_FIGURES" / "phase2" / "phase2_total_delayed_activity_time_series.csv"
SCIENCE_MARKER = R2 / "04_FIGURES" / "day15" / "timeline_spectrum_480_550_with_science_marker.csv"

OUT_FIG = R2 / "04_FIGURES" / "phase2" / "phase2_CAM511_fig11_3sigma_flux_line_veto_significance_vs_time.png"
OUT_CSV = R2 / "04_FIGURES" / "phase2" / "phase2_CAM511_fig11_3sigma_flux_line_veto_significance_vs_time.csv"

WINDOW = "line_510p3_511p8"
SCIENCE_T_REF = 0.7390423888027
REFERENCE_FLUX = 1.0e-4
CAM511_FIG11_3SIGMA_FLUX = 3.0e-6
DAY15 = 15.0
STAGES = [
    ("raw", "No veto", "#4C78A8"),
    ("bgo", "BGO veto", "#F58518"),
    ("final", "BGO+Compton/FoV", "#54A24B"),
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def crossing_time(days: np.ndarray, z: np.ndarray, threshold: float = 3.0) -> float | None:
    above = np.flatnonzero(z >= threshold)
    if len(above) == 0:
        return None
    i = int(above[0])
    if i == 0:
        return float(days[0])
    x0, x1 = float(days[i - 1]), float(days[i])
    y0, y1 = float(z[i - 1]), float(z[i])
    return x0 + (threshold - y0) * (x1 - x0) / (y1 - y0)


def science_line_rates() -> dict[str, float]:
    rows = [r for r in read_csv(SCIENCE_MARKER) if 510.3 <= float(r["E_keV"]) <= 511.8]
    return {
        "raw": sum(float(r["reference_511_source_raw_expectation_cps_per_bin"]) for r in rows),
        "bgo": sum(float(r["reference_511_source_bgo_expectation_cps_per_bin"]) for r in rows),
        "final": sum(float(r["reference_511_source_final_expectation_cps_per_bin"]) for r in rows),
    }


def main() -> int:
    prompt_rows = [
        r for r in read_csv(PROMPT)
        if r["window"] == WINDOW and r["particle"] == "TOTAL"
    ]
    trans_by_bin = {int(r["time_bin_id"]): r for r in read_csv(SCI_TRANS)}
    day15_rows = [r for r in read_csv(DAY15_RATES) if r["window"] == WINDOW]
    day15_by_component = {r["component"]: r for r in day15_rows}
    delayed_day15 = day15_by_component["activation_delayed_only"]
    science_reference = science_line_rates()
    delayed_activity = {
        round(float(r["day"]), 6): float(r["total_delayed_activity_Bq"])
        for r in read_csv(DELAYED_ACTIVITY)
    }
    day15_activity = delayed_activity[DAY15]

    flux_scale = CAM511_FIG11_3SIGMA_FLUX / REFERENCE_FLUX

    rows: list[dict[str, object]] = []
    cum_s = {stage: 0.0 for stage, _, _ in STAGES}
    cum_b = {stage: 0.0 for stage, _, _ in STAGES}
    prev_t = 0.0
    for r in prompt_rows:
        ibin = int(r["time_bin_id"])
        tr = trans_by_bin[ibin]
        t = float(tr["time_mid_s"])
        dt = max(t - prev_t, 0.0)
        prev_t = t
        day = float(r["day_mid"])
        t_atm = float(tr["T_atm_511"]) * float(tr["earth_occultation_factor"])
        source_time_scale = t_atm / SCIENCE_T_REF
        delayed_scale = delayed_activity.get(round(day, 6), 0.0) / day15_activity

        out: dict[str, object] = {
            "time_bin_id": ibin,
            "day": day,
            "dt_s": dt,
            "T_atm_511": t_atm,
            "source_flux_ph_cm2_s": CAM511_FIG11_3SIGMA_FLUX,
            "source_flux_scale_vs_project_reference": flux_scale,
        }
        for stage, _, _ in STAGES:
            prompt_rate = float(r[f"{stage}_cps"])
            delayed_rate = float(delayed_day15[f"{stage}_cps"]) * delayed_scale
            source_rate = science_reference[stage] * flux_scale * source_time_scale
            background_rate = prompt_rate + delayed_rate
            cum_s[stage] += source_rate * dt
            cum_b[stage] += background_rate * dt
            z = cum_s[stage] / math.sqrt(cum_b[stage]) if cum_b[stage] > 0 else 0.0
            out[f"{stage}_source_cps"] = source_rate
            out[f"{stage}_background_cps"] = background_rate
            out[f"{stage}_cumulative_Z"] = z
        rows.append(out)

    write_csv(OUT_CSV, rows)

    days = np.asarray([float(r["day"]) for r in rows])
    fig, ax = plt.subplots(figsize=(8.4, 5.0))
    for stage, label, color in STAGES:
        z = np.asarray([float(r[f"{stage}_cumulative_Z"]) for r in rows])
        ax.plot(days, z, lw=2.4, color=color, label=label)
        cross = crossing_time(days, z)
        if cross is not None:
            ax.plot(cross, 3.0, "o", ms=4, color=color)

    ax.axhline(3.0, color="#D62728", ls="--", lw=1.4, label="3 sigma")
    ax.set_xlim(0, float(days[-1]))
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Time (day)")
    ax.set_ylabel("Cumulative Z")
    ax.set_title("CAM511 Fig.11 3-sigma flux, line window")
    ax.grid(True, alpha=0.25)
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    OUT_FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_FIG, dpi=220)
    plt.close(fig)

    print(OUT_FIG)
    print(OUT_CSV)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
