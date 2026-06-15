#!/usr/bin/env python3
"""Build v3p5 center-finger 1/10 Step08 time-dependent significance."""

from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-newgeo")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "stepwise_maintenance" / "step08_significance" / "outputs_v3p5_centerfinger_1of10"
FIG = OUT / "figures"
STEP05 = ROOT / "stepwise_maintenance" / "step05_veto_time_axis" / "outputs_v3p5_centerfinger_l1" / "step05_v3p5_centerfinger_l1_response_summary.json"
STEP06 = ROOT / "stepwise_maintenance" / "step06_mission_time_variation" / "outputs_v3p5_centerfinger_1of10" / "step06_v3p5_centerfinger_1of10_summary.json"
STEP06_BG = ROOT / "stepwise_maintenance" / "step06_mission_time_variation" / "outputs_v3p5_centerfinger_1of10" / "background_time_variation.csv"
STEP07 = ROOT / "stepwise_maintenance" / "step07_source_cases" / "outputs_v3p5_centerfinger_1of10" / "source_case_summary.json"
STEP07_RATES = ROOT / "stepwise_maintenance" / "step07_source_cases" / "outputs_v3p5_centerfinger_1of10" / "source_case_rates.csv"

SECONDS_PER_DAY = 86400.0


def is_exactpos_label(label: str) -> bool:
    return label.startswith("fullstat_v2_exactpos")


def is_bgo_sample_label(label: str) -> bool:
    return label == "bgo_sample_fullstat_v2_exactpos"


def output_prefix(label: str) -> str:
    return "bgo_sample" if is_bgo_sample_label(label) else "v3p5_centerfinger"


def step06_summary_filename(label: str) -> str:
    if is_bgo_sample_label(label):
        return "step06_bgo_sample_fullstat_v2_exactpos_summary.json"
    return f"step06_{output_prefix(label)}_{label}_summary.json"


def configure_paths(label: str) -> None:
    global OUT, FIG, STEP05, STEP06, STEP06_BG, STEP07, STEP07_RATES

    if is_bgo_sample_label(label):
        OUT = ROOT / "stepwise_maintenance" / "step08_significance" / f"outputs_{label}"
        FIG = OUT / "figures"
        STEP05 = (
            ROOT
            / "stepwise_maintenance"
            / "step05_veto_time_axis"
            / "outputs_bgo_sample_fullstat_v2_exactpos_l1"
            / "step05_bgo_sample_l1_response_summary.json"
        )
        STEP06 = (
            ROOT
            / "stepwise_maintenance"
            / "step06_mission_time_variation"
            / f"outputs_{label}"
            / step06_summary_filename(label)
        )
        STEP06_BG = ROOT / "stepwise_maintenance" / "step06_mission_time_variation" / f"outputs_{label}" / "background_time_variation.csv"
        STEP07 = ROOT / "stepwise_maintenance" / "step07_source_cases" / f"outputs_{label}" / "source_case_summary.json"
        STEP07_RATES = ROOT / "stepwise_maintenance" / "step07_source_cases" / f"outputs_{label}" / "source_case_rates.csv"
        return

    OUT = ROOT / "stepwise_maintenance" / "step08_significance" / f"outputs_v3p5_centerfinger_{label}"
    FIG = OUT / "figures"
    if label == "1of10":
        STEP05 = ROOT / "stepwise_maintenance" / "step05_veto_time_axis" / "outputs_v3p5_centerfinger_l1" / "step05_v3p5_centerfinger_l1_response_summary.json"
    else:
        STEP05 = ROOT / "stepwise_maintenance" / "step05_veto_time_axis" / f"outputs_v3p5_centerfinger_{label}_l1" / "step05_v3p5_centerfinger_l1_response_summary.json"
    STEP06 = (
        ROOT
        / "stepwise_maintenance"
        / "step06_mission_time_variation"
        / f"outputs_v3p5_centerfinger_{label}"
        / f"step06_v3p5_centerfinger_{label}_summary.json"
    )
    STEP06_BG = ROOT / "stepwise_maintenance" / "step06_mission_time_variation" / f"outputs_v3p5_centerfinger_{label}" / "background_time_variation.csv"
    STEP07 = ROOT / "stepwise_maintenance" / "step07_source_cases" / f"outputs_v3p5_centerfinger_{label}" / "source_case_summary.json"
    STEP07_RATES = ROOT / "stepwise_maintenance" / "step07_source_cases" / f"outputs_v3p5_centerfinger_{label}" / "source_case_rates.csv"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def fmt(x: Any, ndigits: int = 6) -> str:
    if x in ("", None):
        return ""
    value = float(x)
    if not math.isfinite(value):
        return "nan"
    if value == 0.0:
        return "0"
    if abs(value) < 1.0e-3 or abs(value) >= 1.0e5:
        return f"{value:.{ndigits}e}"
    return f"{value:.{ndigits}g}"


def f(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = row.get(key, default)
    if value in ("", None):
        return default
    return float(value)


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


def active_dt_for_case(case: dict[str, str], elapsed_start_s: float, dt_s: float) -> float:
    if case["source_class"] != "point_transient":
        return dt_s
    duration = f(case, "duration_s", 0.0)
    if duration <= 0.0:
        return 0.0
    elapsed_stop_s = elapsed_start_s + dt_s
    return max(0.0, min(elapsed_stop_s, duration) - elapsed_start_s)


def build_accidental_rows(bg_rows: list[dict[str, str]], tau: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in bg_rows:
        rate = f(row, "prompt_event_rate_hz") + f(row, "delayed_event_rate_hz")
        live = math.exp(-rate * tau)
        rows.append(
            {
                "selection_id": row["selection_id"],
                "time_bin_id": row["time_bin_id"],
                "day_mid": row["day_mid"],
                "dt_s": row["dt_s"],
                "prompt_event_rate_hz": row["prompt_event_rate_hz"],
                "delayed_event_rate_hz": row["delayed_event_rate_hz"],
                "coincidence_occupancy_rate_hz": rate,
                "coincidence_window_s": tau,
                "accidental_live_factor": live,
                "accidental_loss_fraction": 1.0 - live,
            }
        )
    return rows


def fold_cases(cases: list[dict[str, str]], bg_rows: list[dict[str, str]], tau: float, label: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_selection: dict[str, list[dict[str, str]]] = {}
    for row in bg_rows:
        by_selection.setdefault(row["selection_id"], []).append(row)
    for rows in by_selection.values():
        rows.sort(key=lambda row: int(row["time_bin_id"]))

    cumulative: list[dict[str, Any]] = []
    summary: list[dict[str, Any]] = []
    for case in cases:
        selection = case["selection_id"]
        rows = by_selection[selection]
        elapsed = 0.0
        cum_s = 0.0
        cum_b = 0.0
        days: list[float] = []
        zvals: list[float] = []
        for row in rows:
            dt_s = f(row, "dt_s")
            active_dt = active_dt_for_case(case, elapsed, dt_s)
            occupancy = f(row, "prompt_event_rate_hz") + f(row, "delayed_event_rate_hz")
            live = math.exp(-occupancy * tau)
            source_noacc = f(case, "final_rate_day15_cps") * f(row, "science_atm_scale_to_day15")
            background_noacc = f(row, "background_final_cps")
            source = source_noacc * live
            background = background_noacc * live
            if active_dt > 0.0:
                cum_s += source * active_dt
                cum_b += background * active_dt
            elapsed_stop_day = (elapsed + dt_s) / SECONDS_PER_DAY
            z = cum_s / math.sqrt(cum_b) if cum_b > 0.0 else 0.0
            days.append(elapsed_stop_day)
            zvals.append(z)
            cumulative.append(
                {
                    "analysis_case_id": case["analysis_case_id"],
                    "source_case_id": case["source_case_id"],
                    "source_class": case["source_class"],
                    "model_id": case["model_id"],
                    "selection_id": selection,
                    "flux_ph_cm2_s": case["flux_ph_cm2_s"],
                    "duration_s": case["duration_s"],
                    "time_bin_id": row["time_bin_id"],
                    "day_mid": row["day_mid"],
                    "elapsed_stop_day": elapsed_stop_day,
                    "dt_s": dt_s,
                    "dt_active_s": active_dt,
                    "source_final_cps_noacc": source_noacc,
                    "background_final_cps_noacc": background_noacc,
                    "accidental_live_factor": live,
                    "source_final_cps": source,
                    "background_final_cps": background,
                    "cumulative_source_counts": cum_s,
                    "cumulative_background_counts": cum_b,
                    "counting_Z": z,
                    "template_proxy_Z": z,
                    "template_proxy_note": "same count selection; no profile likelihood gain claimed",
                }
            )
            elapsed += dt_s
        final_day = days[-1] if days else 0.0
        final_z = zvals[-1] if zvals else 0.0
        t3 = crossing_time(days, zvals, 3.0)
        t5 = crossing_time(days, zvals, 5.0)
        claim_level = (
            "BGO_SAMPLE_L1_COUNTING_TIME_DEP_WITH_ANALYTIC_ACCIDENTAL_FULLSTAT_V2_EXACTPOS"
            if is_bgo_sample_label(label)
            else f"V3P5_L1_COUNTING_TIME_DEP_WITH_ANALYTIC_ACCIDENTAL_{label.upper()}"
        )
        summary.append(
            {
                **case,
                "claim_level": claim_level,
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
    return cumulative, summary


def plot_examples(cumulative: list[dict[str, Any]]) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    wanted = [
        "A_point_w2_510p58_511p42_F0.0001",
        "A_point_w2_510p58_511p42_F5e-05",
        "A_point_broad_480_550_F0.0001",
        "B_diffuse_proxy_w2_510p58_511p42",
    ]
    plt.figure(figsize=(8, 4.8))
    for case_id in wanted:
        rows = [row for row in cumulative if row["analysis_case_id"] == case_id]
        if not rows:
            continue
        plt.plot([float(row["elapsed_stop_day"]) for row in rows], [float(row["counting_Z"]) for row in rows], label=case_id)
    plt.axhline(3.0, color="tab:red", ls="--", lw=1)
    plt.axhline(5.0, color="0.4", ls=":", lw=1)
    plt.xlabel("Mission day")
    plt.ylabel("Cumulative counting Z")
    plt.title("v3p5 Step08 low-stat time-dependent examples")
    plt.grid(alpha=0.25)
    plt.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(FIG / "v3p5_step08_cumulative_significance.png", dpi=180)
    plt.close()


def markdown(summary: dict[str, Any]) -> str:
    c = summary["checks"]
    title = "# Step08 Bgo_sample Time-Dependent Significance" if is_bgo_sample_label(summary["statistics_label"]) else "# Step08 v3p5 Center-Finger Time-Dependent Significance"
    intro = (
        f"This folds Bgo_sample Step07 source cases through the Bgo_sample Step06 mission time axis and applies an analytic accidental live factor. Statistics label: `{summary['statistics_label']}`. It does not claim a profile-likelihood gain."
        if is_bgo_sample_label(summary["statistics_label"])
        else f"This folds v3p5 Step07 source cases through the v3p5 Step06 mission time axis and applies an analytic accidental live factor. Statistics label: `{summary['statistics_label']}`. It does not claim a profile-likelihood gain."
    )
    return "\n".join(
        [
            title,
            "",
            f"Status: `{summary['status']}`.",
            "",
            f"Claim level: {summary['claim_level']}.",
            "",
            intro,
            "",
            "Headline:",
            f"- A reference W2 `1e-4 ph cm^-2 s^-1`: `Z20d={c['A_reference_w2_Z20d_time_dependent']:.6g}`.",
            f"- T3/T5: `{fmt(c['A_reference_w2_T3_day'])}` / `{fmt(c['A_reference_w2_T5_day'])}` day.",
            f"- 20-day 3-sigma flux: `{c['A_reference_w2_flux_3sigma_20d_ph_cm2_s']:.6g} ph cm^-2 s^-1`.",
            f"- accidental loss range: `{c['accidental_loss_min']:.6g}` to `{c['accidental_loss_max']:.6g}`.",
            f"- W2 low-stat selected background events: `{c['w2_low_stat_background_events']}`.",
            "",
            "Outputs:",
            f"- cumulative significance: `{summary['outputs']['cumulative_significance']}`",
            f"- T3/T5 summary: `{summary['outputs']['t3_t5_summary']}`",
            f"- accidental live factors: `{summary['outputs']['accidental_veto_by_time']}`",
            f"- summary JSON: `{summary['outputs']['summary_json']}`",
            "",
            "Limitations:",
            *[f"- {item}" for item in summary.get("pending", [])],
            "",
        ]
    )


def build_summary(
    step05: dict[str, Any],
    step06: dict[str, Any],
    step07: dict[str, Any],
    accidentals: list[dict[str, Any]],
    t3_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    label = step05.get("statistics_label", "1of10")
    row_map = {row["analysis_case_id"]: row for row in t3_rows}
    a_ref = row_map["A_point_w2_510p58_511p42_F0.0001"]
    z = float(a_ref["final_counting_Z"])
    flux_ref = float(a_ref["flux_ph_cm2_s"])
    t3 = a_ref["T3_day_counting"] or a_ref["T3_day_extrapolated_constant_profile"]
    t5 = a_ref["T5_day_counting"] or a_ref["T5_day_extrapolated_constant_profile"]
    loss_values = [float(row["accidental_loss_fraction"]) for row in accidentals]
    w2_phys = step05["windows"]["w2_510p58_511p42"]["physical_reference_flux"]
    if is_bgo_sample_label(label):
        pending = [
            "The matched BGO-vs-CsI hard-window comparison is closed for this label.",
            "Optional: run BGO spatial/profile-likelihood sidecars before claiming spatial-analysis gains.",
            "Optional: add BGO material-uncertainty or detector-threshold sensitivity scans before claiming robustness against those choices.",
        ]
    elif is_exactpos_label(label):
        pending = [
            "exact-position delayed source uses sampled PointSource support; support-size stability remains a robustness check",
            "no spatial/profile likelihood gain is applied",
        ]
    else:
        pending = [
            "delayed source is still RadialProfileBeam-compressed",
            "Exact-position delayed-source sampling",
            "Selection-consistent spatial/profile likelihood",
        ]
    status = (
        "PASS_BGO_SAMPLE_STEP08_TIME_DEPENDENT_FULLSTAT_V2_EXACTPOS"
        if is_bgo_sample_label(label)
        else f"PASS_V3P5_STEP08_TIME_DEPENDENT_{label.upper()}"
    )
    claim_level = (
        "BGO_SAMPLE_L1_COUNTING_TIME_DEP_WITH_ANALYTIC_ACCIDENTAL_FULLSTAT_V2_EXACTPOS"
        if is_bgo_sample_label(label)
        else f"V3P5_L1_COUNTING_TIME_DEP_WITH_ANALYTIC_ACCIDENTAL_{label.upper()}"
    )
    return {
        "status": status,
        "statistics_label": label,
        "claim_level": claim_level,
        "inputs": {
            "step05_summary": rel(STEP05),
            "step06_summary": rel(STEP06),
            "step06_background_time_variation": rel(STEP06_BG),
            "step07_summary": rel(STEP07),
            "step07_source_case_rates": rel(STEP07_RATES),
        },
        "checks": {
            "A_reference_w2_Z20d_time_dependent": z,
            "A_reference_w2_T3_day": float(t3) if t3 != "" else None,
            "A_reference_w2_T5_day": float(t5) if t5 != "" else None,
            "A_reference_w2_flux_3sigma_20d_ph_cm2_s": flux_ref * 3.0 / z if z > 0 else math.inf,
            "A_reference_w2_source_counts": float(a_ref["total_source_counts"]),
            "A_reference_w2_background_counts": float(a_ref["total_background_counts"]),
            "accidental_loss_min": min(loss_values),
            "accidental_loss_max": max(loss_values),
            "w2_low_stat_background_events": w2_phys["low_stat_final_background_events"],
            "step06_status": step06["status"],
            "step07_status": step07["status"],
        },
        "outputs": {
            "summary_json": rel(OUT / ("step08_bgo_sample_time_dependent_summary.json" if is_bgo_sample_label(label) else "step08_v3p5_centerfinger_time_dependent_summary.json")),
            "readme": rel(OUT / ("step08_bgo_sample_time_dependent.md" if is_bgo_sample_label(label) else "step08_v3p5_centerfinger_time_dependent.md")),
            "cumulative_significance": rel(OUT / "cumulative_significance_by_case.csv"),
            "t3_t5_summary": rel(OUT / "t3_t5_summary.csv"),
            "accidental_veto_by_time": rel(OUT / "accidental_veto_by_time.csv"),
            "figures": rel(FIG),
        },
        "pending": pending,
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="1of10", help="Run/output label, e.g. 1of10 or fullstat_v2")
    args = ap.parse_args()

    configure_paths(args.label)
    OUT.mkdir(parents=True, exist_ok=True)
    step05 = load_json(STEP05)
    step06 = load_json(STEP06)
    step07 = load_json(STEP07)
    bg_rows = read_csv(STEP06_BG)
    cases = read_csv(STEP07_RATES)
    tau = float(step05["normalization"]["coincidence_window_s"])
    accidentals = build_accidental_rows(bg_rows, tau)
    cumulative, t3_rows = fold_cases(cases, bg_rows, tau, args.label)
    write_csv(OUT / "accidental_veto_by_time.csv", accidentals)
    write_csv(OUT / "cumulative_significance_by_case.csv", cumulative)
    write_csv(OUT / "t3_t5_summary.csv", t3_rows)
    plot_examples(cumulative)
    summary = build_summary(step05, step06, step07, accidentals, t3_rows)
    summary_path = OUT / ("step08_bgo_sample_time_dependent_summary.json" if is_bgo_sample_label(args.label) else "step08_v3p5_centerfinger_time_dependent_summary.json")
    report_path = OUT / ("step08_bgo_sample_time_dependent.md" if is_bgo_sample_label(args.label) else "step08_v3p5_centerfinger_time_dependent.md")
    write_json(summary_path, summary)
    report_path.write_text(markdown(summary), encoding="utf-8")
    print(json.dumps({"status": summary["status"], "summary": summary["outputs"]["summary_json"], "report": summary["outputs"]["readme"]}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
