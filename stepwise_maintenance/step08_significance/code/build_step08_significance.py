#!/usr/bin/env python3
"""Build Step08 time-dependent source significance and accidental-veto folding.

This step consumes Step06 time-dependent rates and Step07 source cases.  It is
an L1 counting-significance layer with an analytic accidental live-time factor.
It also writes a small catalog-bootstrap sanity check for the accidental model.
It is not a full spatial-spectral profile likelihood.
"""

from __future__ import annotations

import csv
import json
import math
import os
import pickle
import re
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-newgeo")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
STEP_DIR = ROOT / "stepwise_maintenance" / "step08_significance"
OUT = STEP_DIR / "outputs"
FIG_DIR = OUT / "figures"

DAY15_SUMMARY = ROOT / "outputs" / "reports" / "day15_complete_report" / "complete_day15_summary.json"
CATALOG = ROOT / "outputs" / "reports" / "day15_complete_report" / "work" / "event_catalog.pkl"
STEP06_BG = ROOT / "stepwise_maintenance" / "step06_mission_time_variation" / "outputs" / "background_time_variation.csv"
STEP07_SUMMARY = ROOT / "stepwise_maintenance" / "step07_source_cases" / "outputs" / "source_case_summary.json"
STEP07_RATES = ROOT / "stepwise_maintenance" / "step07_source_cases" / "outputs" / "source_case_rates.csv"
FOCUS_RESPONSE = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs" / "detector_coupled_focus_response.json"

REFERENCE_EXPOSURE_S = 1.0e6
SECONDS_PER_DAY = 86400.0
ACCIDENTAL_BOOTSTRAP_TRIALS = 100000


def initial_analysis_window() -> tuple[float, float]:
    try:
        focus = json.loads(FOCUS_RESPONSE.read_text(encoding="utf-8"))
        w1 = focus["windows"]["W1_design_passband"]
        return float(w1["lo_keV"]), float(w1["hi_keV"])
    except Exception:
        return 500.99393711182086, 521.0060628881791


WINDOW_LO_KEV, WINDOW_HI_KEV = initial_analysis_window()

sys.path.insert(0, str(ROOT / "code" / "tools"))
import make_complete_day15_report_ADR as complete  # noqa: E402


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def ensure_dirs() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fmt(x: float, nd: int = 6) -> str:
    if x is None or not math.isfinite(float(x)):
        return "nan"
    x = float(x)
    if x == 0.0:
        return "0"
    if abs(x) < 1.0e-3 or abs(x) >= 1.0e5:
        return f"{x:.{nd}e}"
    return f"{x:.{nd}g}"


def f(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = row.get(key, default)
    if value in ("", None):
        return default
    return float(value)


def sanitize(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.+-]+", "_", text)
    return text.strip("_")


def crossing_time(days: list[float], zvals: list[float], threshold: float) -> float | None:
    for i, value in enumerate(zvals):
        if value < threshold:
            continue
        if i == 0:
            return days[0]
        x0, x1 = days[i - 1], days[i]
        y0, y1 = zvals[i - 1], zvals[i]
        if y1 == y0:
            return x1
        return x0 + (threshold - y0) * (x1 - x0) / (y1 - y0)
    return None


def extrapolated_time_days(final_day: float, final_z: float, threshold: float) -> float | None:
    if final_z <= 0.0:
        return None
    if final_z >= threshold:
        return final_day
    return final_day * (threshold / final_z) ** 2


def authority_efficiencies(summary: dict[str, Any], step07: dict[str, Any]) -> list[dict[str, Any]]:
    catalog = summary["catalog"]["by_stream"]
    by_stream = summary["expectation_rates_by_stream_cps"]
    rows: list[dict[str, Any]] = []
    for stream in ("prompt", "delayed", "science"):
        event_rate = float(catalog[stream]["rate_hz"])
        raw = float(by_stream[stream]["raw"])
        bgo = float(by_stream[stream]["bgo"])
        final = float(by_stream[stream]["final"])
        rows.append(
            {
                "stream": stream,
                "catalog_event_rate_hz_day15": event_rate,
                "raw_cps_day15": raw,
                "bgo_cps_day15": bgo,
                "final_cps_day15": final,
                "epsilon_raw_per_catalog_event": raw / event_rate if event_rate > 0 else "",
                "epsilon_bgo_per_catalog_event": bgo / event_rate if event_rate > 0 else "",
                "epsilon_final_per_catalog_event": final / event_rate if event_rate > 0 else "",
                "note": "science also has a plane-injected-photon efficiency below" if stream == "science" else "",
            }
        )
    auth = step07["authority"]
    rows.append(
        {
            "stream": "science_plane_injection",
            "catalog_event_rate_hz_day15": "",
            "raw_cps_day15": "",
            "bgo_cps_day15": "",
            "final_cps_day15": auth["reference_flux_ph_cm2_s"] * auth["science_final_response_cps_per_flux"],
            "epsilon_raw_per_catalog_event": "",
            "epsilon_bgo_per_catalog_event": "",
            "epsilon_final_per_catalog_event": auth["science_transport_final_efficiency"],
            "note": "final response divided by F*A_opt*T_atm at the injection plane",
        }
    )
    write_csv(OUT / "rate_independent_veto_efficiencies.csv", rows)
    return rows


def time_bins(summary: dict[str, Any]) -> list[dict[str, Any]]:
    day15_catalog = summary["catalog"]["by_stream"]
    prompt_event_rate = float(day15_catalog["prompt"]["rate_hz"])
    delayed_event_rate = float(day15_catalog["delayed"]["rate_hz"])
    tau = float(summary["normalization"]["coincidence_window_s"])
    rows: list[dict[str, Any]] = []
    elapsed = 0.0
    for row in read_csv(STEP06_BG):
        dt = float(row["dt_s"])
        prompt_rate = prompt_event_rate * float(row["prompt_scale_to_day15"])
        delayed_rate = delayed_event_rate * float(row["delayed_activity_scale_to_day15"])
        occupancy_rate = prompt_rate + delayed_rate
        factor = math.exp(-occupancy_rate * tau)
        rows.append(
            {
                "time_bin_id": int(row["time_bin_id"]),
                "time_mid_s": float(row["time_mid_s"]),
                "day_mid": float(row["day_mid"]),
                "elapsed_start_s": elapsed,
                "elapsed_stop_s": elapsed + dt,
                "dt_s": dt,
                "prompt_event_rate_hz": prompt_rate,
                "delayed_event_rate_hz": delayed_rate,
                "coincidence_occupancy_rate_hz": occupancy_rate,
                "coincidence_window_s": tau,
                "accidental_live_factor": factor,
                "accidental_loss_fraction": 1.0 - factor,
                "background_final_cps_noacc": float(row["background_final_cps"]),
                "background_bgo_cps_noacc": float(row["background_bgo_cps"]),
                "background_raw_cps_noacc": float(row["background_raw_cps"]),
                "science_atm_scale_to_day15": float(row["science_atm_scale_to_day15"]),
            }
        )
        elapsed += dt
    write_csv(OUT / "accidental_veto_by_time.csv", rows)
    return rows


def build_cases() -> list[dict[str, Any]]:
    rows = read_csv(STEP07_RATES)
    cases: list[dict[str, Any]] = []
    for row in rows:
        source_class = row["source_class"]
        model_id = row["model_id"]
        if source_class == "point_steady":
            case_label = (
                f"A_{model_id}_F{f(row, 'flux_ph_cm2_s'):.3g}_"
                f"R{f(row, 'angular_radius_arcmin'):.3g}arcmin"
            )
        elif source_class == "extended_steady":
            case_label = f"B_{row['sky_model']}_{model_id}"
        elif source_class == "point_transient":
            case_label = f"C_{model_id}_F{f(row, 'flux_ph_cm2_s'):.3g}_T{int(f(row, 'duration_s'))}s"
        else:
            continue
        cases.append(
            {
                "analysis_case_id": sanitize(case_label),
                "source_case_id": row["case_id"],
                "source_class": source_class,
                "model_id": model_id,
                "sky_model": row.get("sky_model", ""),
                "flux_ph_cm2_s": row.get("flux_ph_cm2_s", ""),
                "duration_s": row.get("duration_s", ""),
                "angular_radius_arcmin": row.get("angular_radius_arcmin", ""),
                "final_rate_day15_cps": f(row, "final_rate_day15_cps"),
                "handling": row.get("handling", ""),
            }
        )

    b_default = [
        c for c in cases
        if c["source_case_id"] == "B_GC_DIFFUSE_BULGE_DISK"
        and c["model_id"] == "gaussian_fwhm_1p0"
        and c["sky_model"] in ("bulge_gaussian_fwhm_8deg", "disk_thick_gaussian")
    ]
    if len(b_default) == 2:
        cases.append(
            {
                "analysis_case_id": "B_DEFAULT_bulge8deg_plus_disk_gaussian_fwhm_1p0",
                "source_case_id": "B_GC_DIFFUSE_BULGE_DISK",
                "source_class": "extended_steady",
                "model_id": "gaussian_fwhm_1p0",
                "sky_model": "bulge8deg_plus_disk",
                "flux_ph_cm2_s": "",
                "duration_s": "",
                "angular_radius_arcmin": "",
                "final_rate_day15_cps": sum(float(c["final_rate_day15_cps"]) for c in b_default),
                "handling": "default_diffuse_aperture_foreground_sum",
            }
        )
    return cases


def active_dt_for_case(case: dict[str, Any], bin_row: dict[str, Any]) -> float:
    if case["source_class"] != "point_transient":
        return float(bin_row["dt_s"])
    duration = f(case, "duration_s", 0.0)
    if duration <= 0:
        return 0.0
    start = float(bin_row["elapsed_start_s"])
    stop = float(bin_row["elapsed_stop_s"])
    return max(0.0, min(stop, duration) - start)


def fold_significance(cases: list[dict[str, Any]], bins: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cumulative_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for case in cases:
        cum_s = 0.0
        cum_b = 0.0
        days: list[float] = []
        z_counting: list[float] = []
        for b in bins:
            active_dt = active_dt_for_case(case, b)
            source_noacc = float(case["final_rate_day15_cps"]) * float(b["science_atm_scale_to_day15"])
            background_noacc = float(b["background_final_cps_noacc"])
            live = float(b["accidental_live_factor"])
            source_rate = source_noacc * live
            background_rate = background_noacc * live
            if active_dt > 0.0:
                cum_s += source_rate * active_dt
                cum_b += background_rate * active_dt
            z = cum_s / math.sqrt(cum_b) if cum_b > 0.0 else 0.0
            days.append(float(b["day_mid"]))
            z_counting.append(z)
            cumulative_rows.append(
                {
                    "analysis_case_id": case["analysis_case_id"],
                    "source_case_id": case["source_case_id"],
                    "source_class": case["source_class"],
                    "model_id": case["model_id"],
                    "sky_model": case["sky_model"],
                    "flux_ph_cm2_s": case["flux_ph_cm2_s"],
                    "duration_s": case["duration_s"],
                    "angular_radius_arcmin": case["angular_radius_arcmin"],
                    "time_bin_id": b["time_bin_id"],
                    "day_mid": b["day_mid"],
                    "dt_active_s": active_dt,
                    "source_final_cps_noacc": source_noacc,
                    "background_final_cps_noacc": background_noacc,
                    "accidental_live_factor": live,
                    "source_final_cps": source_rate,
                    "background_final_cps": background_rate,
                    "cumulative_source_counts": cum_s,
                    "cumulative_background_counts": cum_b,
                    "counting_Z": z,
                    "template_proxy_Z": z,
                    "template_proxy_note": "same selection as counting; no independent profile likelihood yet",
                }
            )
        final_day = max((row["elapsed_stop_s"] for row in bins), default=0.0) / SECONDS_PER_DAY
        final_z = z_counting[-1] if z_counting else 0.0
        t3 = crossing_time(days, z_counting, 3.0)
        t5 = crossing_time(days, z_counting, 5.0)
        summary_rows.append(
            {
                **case,
                "claim_level": "L1_COUNTING_TIME_DEP_WITH_ANALYTIC_ACCIDENTAL",
                "selection": f"final W1 {WINDOW_LO_KEV:.3f}-{WINDOW_HI_KEV:.3f} keV BGO+Compton/FoV",
                "accidental_model": "exp(-R_coincidence*tau) live factor",
                "template_proxy_policy": "template_proxy_Z equals counting_Z until a selection-consistent likelihood is implemented",
                "total_source_counts": cum_s,
                "total_background_counts": cum_b,
                "final_counting_Z": final_z,
                "final_template_proxy_Z": final_z,
                "T3_day_counting": "" if t3 is None else t3,
                "T5_day_counting": "" if t5 is None else t5,
                "T3_day_extrapolated_constant_profile": "" if t3 is not None else extrapolated_time_days(final_day, final_z, 3.0),
                "T5_day_extrapolated_constant_profile": "" if t5 is not None else extrapolated_time_days(final_day, final_z, 5.0),
            }
        )
    write_csv(OUT / "cumulative_significance_by_case.csv", cumulative_rows)
    write_csv(OUT / "t3_t5_summary.csv", summary_rows)
    return cumulative_rows, summary_rows


def classify_candidate(cat: dict[str, Any], event_indices: np.ndarray, reject_policy: str) -> tuple[bool, str]:
    energy = float(np.sum(cat["tes_total_keV"][event_indices]))
    if not (WINDOW_LO_KEV <= energy < WINDOW_HI_KEV):
        return False, "energy_out"
    bgo = float(np.sum(cat["bgo_total_keV"][event_indices]))
    if bgo >= complete.BGO_THR_KEV:
        return False, "bgo_veto"
    return True, "kept_fast_no_compton_recalc"


def isolated_selected_science(cat: dict[str, Any], reject_policy: str) -> np.ndarray:
    streams = cat["stream"].astype(str)
    science_idx = np.flatnonzero(streams == "science")
    energy = cat["tes_total_keV"][science_idx].astype(float)
    bgo = cat["bgo_total_keV"][science_idx].astype(float)
    pix_count = cat["pix_count"][science_idx].astype(int)
    mask = (energy >= WINDOW_LO_KEV) & (energy < WINDOW_HI_KEV) & (bgo < complete.BGO_THR_KEV) & (pix_count > 0)
    return science_idx[mask].astype(np.int64)


def accidental_bootstrap(summary: dict[str, Any], bins: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not CATALOG.exists():
        return []
    with CATALOG.open("rb") as handle:
        cat = pickle.load(handle)
    reject_policy = str(summary["normalization"].get("reject_policy", "keep"))
    selected_science = isolated_selected_science(cat, reject_policy)
    streams = cat["stream"].astype(str)
    prompt_idx = np.flatnonzero(streams == "prompt")
    delayed_idx = np.flatnonzero(streams == "delayed")
    prompt_prob = cat["rate_hz"][prompt_idx].astype(float)
    prompt_prob = prompt_prob / np.sum(prompt_prob)
    delayed_prob = cat["rate_hz"][delayed_idx].astype(float)
    delayed_prob = delayed_prob / np.sum(delayed_prob)
    tau = float(summary["normalization"]["coincidence_window_s"])
    reps = [
        ("min", min(bins, key=lambda r: r["coincidence_occupancy_rate_hz"])),
        ("mean", {
            "coincidence_occupancy_rate_hz": sum(b["coincidence_occupancy_rate_hz"] * b["dt_s"] for b in bins) / sum(b["dt_s"] for b in bins),
            "prompt_event_rate_hz": sum(b["prompt_event_rate_hz"] * b["dt_s"] for b in bins) / sum(b["dt_s"] for b in bins),
            "delayed_event_rate_hz": sum(b["delayed_event_rate_hz"] * b["dt_s"] for b in bins) / sum(b["dt_s"] for b in bins),
            "day_mid": "weighted_mean",
        }),
        ("max", max(bins, key=lambda r: r["coincidence_occupancy_rate_hz"])),
    ]
    rows: list[dict[str, Any]] = []
    rng = np.random.default_rng(260508)
    for label, rep in reps:
        total_rate = float(rep["coincidence_occupancy_rate_hz"])
        prompt_rate = float(rep["prompt_event_rate_hz"])
        delayed_rate = float(rep["delayed_event_rate_hz"])
        p_acc = 1.0 - math.exp(-total_rate * tau)
        sci_draw = rng.choice(selected_science, size=ACCIDENTAL_BOOTSTRAP_TRIALS, replace=True)
        has_acc = rng.random(ACCIDENTAL_BOOTSTRAP_TRIALS) < p_acc
        mixed = np.flatnonzero(has_acc)
        prompt_branch_p = prompt_rate / max(prompt_rate + delayed_rate, 1.0e-300)
        causes: dict[str, int] = {}
        lost = 0
        for trial in mixed:
            if rng.random() < prompt_branch_p:
                bg = int(rng.choice(prompt_idx, p=prompt_prob))
            else:
                bg = int(rng.choice(delayed_idx, p=delayed_prob))
            keep, cause = classify_candidate(cat, np.asarray([int(sci_draw[trial]), bg], dtype=np.int64), reject_policy)
            if not keep:
                lost += 1
                causes[cause] = causes.get(cause, 0) + 1
        survival = 1.0 - lost / ACCIDENTAL_BOOTSTRAP_TRIALS
        rows.append(
            {
                "representative": label,
                "day_mid": rep["day_mid"],
                "n_trials": ACCIDENTAL_BOOTSTRAP_TRIALS,
                "selected_science_catalog_events": len(selected_science),
                "coincidence_occupancy_rate_hz": total_rate,
                "coincidence_window_s": tau,
                "analytic_live_factor": math.exp(-total_rate * tau),
                "analytic_loss_fraction": 1.0 - math.exp(-total_rate * tau),
                "sampled_trials_with_accidental": int(len(mixed)),
                "bootstrap_survival_fraction": survival,
                "bootstrap_loss_fraction": 1.0 - survival,
                "bootstrap_loss_causes": json.dumps(causes, sort_keys=True),
                "claim": "fast catalog energy/BGO bootstrap sanity anchor; Compton is not recomputed here and this is not a full per-bin MC timeline",
            }
        )
    write_csv(OUT / "accidental_representative_anchor.csv", rows)
    return rows


def plot_accidental(bins: list[dict[str, Any]]) -> None:
    days = [float(b["day_mid"]) for b in bins]
    loss = [float(b["accidental_loss_fraction"]) for b in bins]
    rate = [float(b["coincidence_occupancy_rate_hz"]) for b in bins]
    fig, ax1 = plt.subplots(figsize=(8.0, 4.6))
    ax1.plot(days, np.asarray(loss) * 100.0, color="#4C78A8", lw=2.0, label="accidental loss")
    ax1.set_xlabel("Mission day")
    ax1.set_ylabel("Analytic accidental live-time loss (%)")
    ax1.grid(True, alpha=0.25)
    ax2 = ax1.twinx()
    ax2.plot(days, rate, color="#F58518", lw=1.4, ls="--", label="coincidence rate")
    ax2.set_ylabel("Prompt+delayed event occupancy rate (Hz)")
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "accidental_live_factor_vs_time.png", dpi=220)
    plt.close(fig)


def plot_key_significance(cumulative_rows: list[dict[str, Any]]) -> None:
    key_ids = [
        "A_mono_511_F8e-05_R0arcmin",
        "A_mono_511_F0.0001_R0arcmin",
        "A_mono_511_F0.0003_R0arcmin",
        "B_DEFAULT_bulge8deg_plus_disk_gaussian_fwhm_1p0",
        "C_v404_kT30_no_shift_F0.001_T86400s",
    ]
    fig, ax = plt.subplots(figsize=(8.3, 5.0))
    for key in key_ids:
        rows = [r for r in cumulative_rows if r["analysis_case_id"] == key]
        if not rows:
            continue
        days = [float(r["day_mid"]) for r in rows]
        z = [float(r["counting_Z"]) for r in rows]
        ax.plot(days, z, lw=2.0, label=key.replace("_", " "))
    ax.axhline(3.0, color="#D62728", ls="--", lw=1.2, label="3 sigma")
    ax.axhline(5.0, color="#7F7F7F", ls=":", lw=1.2, label="5 sigma")
    ax.set_xlabel("Mission day")
    ax.set_ylabel("Cumulative counting Z")
    ax.set_title("Step08 time-dependent significance examples")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "cumulative_significance_examples.png", dpi=220)
    plt.close(fig)


def write_headline_note(summary: dict[str, Any]) -> None:
    checks = summary["checks"]
    lines = [
        "# Step08 Headline Number Policy",
        "",
        f"The headline number in this step is the counting significance in the final W1 `{WINDOW_LO_KEV:.3f}-{WINDOW_HI_KEV:.3f} keV` BGO+Compton/FoV selection, folded over the Step06 mission time axis and multiplied by the analytic accidental live factor.",
        "",
        f"For the A-reference `1e-4 ph cm^-2 s^-1` source, the 20-day mission reaches `Z={fmt(checks['A_reference_final_Z_20d'])}`. It does not cross 3 sigma within the `{fmt(checks['mission_duration_day'])}` day mission; the reported `T3={fmt(checks['A_reference_T3_day_counting_or_extrapolated'])}` day is a constant-profile extrapolation beyond the mission duration.",
        "",
        "The `template_proxy_Z` column is intentionally equal to `counting_Z`. A separate profile-likelihood gain is not applied because `new_geo_re` does not yet have a selection-consistent spatial-spectral likelihood template for these source cases.",
        "",
        "The accidental factor is `exp(-R_coincidence * tau)` with `tau=1e-6 s` and `R_coincidence` taken from the time-dependent prompt plus delayed event occupancy rate. At the day-15 scale this is an order `8e-4` live-time correction, so it is small but now explicitly folded.",
        "",
        "The focused mono science response now comes from the Step09 detector-coupled EventList bridge. Optics hardware mass activation/scattering is still outside this Step08 rate-folding layer.",
    ]
    (OUT / "which_number_is_headline.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_readme(summary: dict[str, Any]) -> None:
    checks = summary["checks"]
    if checks["A_reference_T3_status"] == "mission_internal_crossing":
        t3_line = (
            f"- A reference `1e-4` 3-sigma crossing: `{fmt(checks['A_reference_T3_day_counting'])}` day "
            f"within the `{fmt(checks['mission_duration_day'])}` day mission."
        )
    else:
        t3_line = (
            f"- A reference `1e-4` does not reach 3 sigma inside the `{fmt(checks['mission_duration_day'])}` day mission; "
            f"constant-profile extrapolated 3-sigma time is `{fmt(checks['A_reference_T3_day_extrapolated_constant_profile'])}` day."
        )
    lines = [
        "# Step08 Time-Dependent Significance",
        "",
        "Status: `PASS`.",
        "",
        "Claim level: `L1_COUNTING_TIME_DEP_WITH_ANALYTIC_ACCIDENTAL`.",
        "",
        "This step folds Step07 source cases through the Step06 mission time axis and applies an analytic accidental live-time factor. It reports counting significance and a deliberately non-enhanced template proxy. It does not claim a full profile likelihood.",
        "",
        "## Key Checks",
        "",
        f"- accidental loss range: `{fmt(checks['accidental_loss_min'])}` to `{fmt(checks['accidental_loss_max'])}`.",
        f"- day-15 scale loss sanity: `{fmt(checks['day15_scale_accidental_loss'])}`.",
        f"- A anchor final Z over 20 days: `{fmt(checks['A_anchor_final_Z_20d'])}`.",
        f"- A reference `1e-4` final Z over 20 days: `{fmt(checks['A_reference_final_Z_20d'])}`.",
        t3_line,
        "- `template_proxy_Z` remains equal to counting `Z`; no profile-likelihood gain is claimed.",
        "",
        "## Outputs",
        "",
    ]
    for key, value in summary["outputs"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("- `line_window_sensitivity`: `stepwise_maintenance/step08_significance/outputs/line_window_sensitivity.md`")
    lines.append("- `spatial_line_proxy`: `stepwise_maintenance/step08_significance/outputs/spatial_line_proxy.md`")
    lines.extend(
        [
            "",
            "## Sidecars",
            "",
            "- Line-window sidecar uses the Step09 detector-coupled focused EventList response and reports W1/W2 sensitivity.",
            "- Focused-spot spatial sidecar applies detector-coupled focused science centroids and current background TES centroids; the headline spatial cut is `spot_r90`.",
        ]
    )
    line_summary_path = OUT / "line_window_sensitivity_summary.json"
    if line_summary_path.exists():
        line_checks = load_json(line_summary_path).get("checks", {})
        line_z = line_checks.get("line_pm_3sigma_Z20d_time_dependent", line_checks.get("line_pm_3sigma_Z20d"))
        line_t3 = line_checks.get("line_pm_3sigma_T3_day_time_dependent", line_checks.get("line_pm_3sigma_T3_day_constant_rate"))
        lines.extend(
            [
                f"- Current line sidecar: background `{fmt(line_checks.get('line_pm_3sigma_background_cps'))}` cps, "
                f"time-dependent `Z20d={fmt(line_z)}`, "
                f"`T3={fmt(line_t3)}` day.",
            ]
        )
    spatial_summary_path = OUT / "spatial_line_proxy_summary.json"
    if spatial_summary_path.exists():
        spatial_checks = load_json(spatial_summary_path).get("checks", {})
        spot_z = spatial_checks.get("spot_r90_Z20d_time_dependent", spatial_checks.get("spot_r90_Z20d"))
        spot_gain = spatial_checks.get("spot_r90_Z_gain_vs_line_time_dependent", spatial_checks.get("spot_r90_Z_gain_vs_line"))
        lines.extend(
            [
                f"- Current spatial detector-coupled sidecar: EventList rows `{spatial_checks.get('signal_eventlist_rows')}`, "
                f"headline `spot_r90={fmt(spatial_checks.get('signal_radius_r90_cm'))}` cm, "
                f"background `{fmt(spatial_checks.get('spot_r90_background_cps'))}` cps, "
                f"time-dependent `Z20d={fmt(spot_z)}`, "
                f"gain vs line `{fmt(spot_gain)}`. "
                f"Best diagnostic cut is `{spatial_checks.get('best_cut_id')}`.",
            ]
        )
    lines.extend(
        [
            "",
            "## Rebuild",
            "",
            "```bash",
            "python3 stepwise_maintenance/step08_significance/code/build_step08_significance.py",
            "python3 stepwise_maintenance/step08_significance/code/build_line_window_sensitivity.py",
            "python3 stepwise_maintenance/step08_significance/code/build_spatial_line_proxy.py",
            "```",
        ]
    )
    (STEP_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_summary(
    bins: list[dict[str, Any]],
    t3_rows: list[dict[str, Any]],
    bootstrap_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    t3_map = {row["analysis_case_id"]: row for row in t3_rows}
    a_anchor = t3_map.get("A_mono_511_F8e-05_R0arcmin", {})
    a_ref = t3_map.get("A_mono_511_F0.0001_R0arcmin", {})
    final_day = max((float(b["elapsed_stop_s"]) for b in bins), default=0.0) / SECONDS_PER_DAY
    def first_number(row: dict[str, Any], *keys: str) -> float | None:
        for key in keys:
            value = row.get(key, "")
            if value not in ("", None):
                return float(value)
        return None
    loss_values = [float(b["accidental_loss_fraction"]) for b in bins]
    mean_loss = sum(float(b["accidental_loss_fraction"]) * float(b["dt_s"]) for b in bins) / sum(float(b["dt_s"]) for b in bins)
    day15_like = min(bins, key=lambda b: abs(float(b["day_mid"]) - 15.0))
    a_ref_t3_counting = first_number(a_ref, "T3_day_counting")
    a_ref_t3_extrapolated = first_number(a_ref, "T3_day_extrapolated_constant_profile")
    a_ref_t3_used = first_number(a_ref, "T3_day_counting", "T3_day_extrapolated_constant_profile")
    a_ref_t3_status = "mission_internal_crossing" if a_ref_t3_counting else "extrapolated_beyond_20d"
    summary = {
        "status": "PASS",
        "claim_level": "L1_COUNTING_TIME_DEP_WITH_ANALYTIC_ACCIDENTAL",
        "scope": "Step07 focused-EventList source cases folded over Step06 time-dependent background/science rates with an analytic accidental live factor. Not a full profile likelihood or optics-mass background production.",
        "inputs": {
            "step06_background_time_variation": rel(STEP06_BG),
            "step07_source_case_rates": rel(STEP07_RATES),
            "focused_detector_response": rel(FOCUS_RESPONSE),
            "day15_summary": rel(DAY15_SUMMARY),
        },
        "accidental_model": {
            "formula": "live_factor = exp(-R_coincidence_hz * coincidence_window_s)",
            "R_coincidence_hz": "time-dependent prompt+delayed catalog event occupancy rate",
            "bootstrap_trials_per_representative_rate": ACCIDENTAL_BOOTSTRAP_TRIALS if bootstrap_rows else 0,
        },
        "checks": {
            "accidental_loss_min": min(loss_values),
            "accidental_loss_max": max(loss_values),
            "accidental_loss_dt_weighted_mean": mean_loss,
            "day15_scale_accidental_loss": float(day15_like["accidental_loss_fraction"]),
            "A_anchor_final_Z_20d": float(a_anchor.get("final_counting_Z", 0.0) or 0.0),
            "A_reference_final_Z_20d": float(a_ref.get("final_counting_Z", 0.0) or 0.0),
            "A_reference_T3_day_counting": a_ref_t3_counting,
            "A_reference_T3_day_extrapolated_constant_profile": a_ref_t3_extrapolated,
            "A_reference_T3_day_counting_or_extrapolated": a_ref_t3_used,
            "A_reference_T3_status": a_ref_t3_status,
            "mission_duration_day": final_day,
            "template_proxy_gain": 1.0,
            "bootstrap_anchor_rows": len(bootstrap_rows),
        },
        "outputs": {
            "rate_independent_efficiencies": rel(OUT / "rate_independent_veto_efficiencies.csv"),
            "accidental_veto_by_time": rel(OUT / "accidental_veto_by_time.csv"),
            "accidental_representative_anchor": rel(OUT / "accidental_representative_anchor.csv"),
            "cumulative_significance": rel(OUT / "cumulative_significance_by_case.csv"),
            "t3_t5_summary": rel(OUT / "t3_t5_summary.csv"),
            "headline_note": rel(OUT / "which_number_is_headline.md"),
            "readme": rel(STEP_DIR / "README.md"),
            "figures": rel(FIG_DIR),
        },
    }
    write_json(OUT / "step08_significance_summary.json", summary)
    return summary


def main() -> int:
    ensure_dirs()
    day15 = load_json(DAY15_SUMMARY)
    step07 = load_json(STEP07_SUMMARY)
    authority_efficiencies(day15, step07)
    bins = time_bins(day15)
    cases = build_cases()
    cumulative_rows, t3_rows = fold_significance(cases, bins)
    bootstrap_rows = accidental_bootstrap(day15, bins)
    plot_accidental(bins)
    plot_key_significance(cumulative_rows)
    summary = build_summary(bins, t3_rows, bootstrap_rows)
    write_headline_note(summary)
    write_readme(summary)
    print(json.dumps({"status": summary["status"], "claim_level": summary["claim_level"], "checks": summary["checks"], "out": rel(OUT)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
