#!/usr/bin/env python3
"""Build a prompt-511 spatial ROI smoke report.

The smoke quantifies how much prompt 511 background is removed by applying
detector-coordinate focused-spot cuts, anchored to the current M=50000
exact-position Step05/06/08 authority.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
LABEL = "fullstat_v2_exactpos_m50000_s260613"
W2 = "w2_510p58_511p42"
REFERENCE_FLUX = 1.0e-4
SECONDS_PER_DAY = 86400.0

SPATIAL_CUTS = (
    ROOT
    / "stepwise_maintenance"
    / "step09_optics_bridge"
    / "outputs_f10m_a1_v3p5"
    / "detector_coupled_spatial_line_cuts.csv"
)
STEP05 = (
    ROOT
    / "stepwise_maintenance"
    / "step05_veto_time_axis"
    / f"outputs_v3p5_centerfinger_{LABEL}_l1"
    / "step05_v3p5_centerfinger_l1_response_summary.json"
)
STEP06_BG = (
    ROOT
    / "stepwise_maintenance"
    / "step06_mission_time_variation"
    / f"outputs_v3p5_centerfinger_{LABEL}"
    / "background_time_variation.csv"
)
STEP08 = (
    ROOT
    / "stepwise_maintenance"
    / "step08_significance"
    / f"outputs_v3p5_centerfinger_{LABEL}"
    / "step08_v3p5_centerfinger_time_dependent_summary.json"
)
CLAUDE_REVIEW = ROOT / "core_md" / "CLAUDE_PROMPT511_SIDEPORT_FIX_REVIEW_20260617.md"
BOUNDARY = (
    ROOT
    / "outputs"
    / "reports"
    / f"v3p5_boundary_closure_{LABEL}_20260613"
    / "v3p5_boundary_closure_summary.json"
)

CUT_ORDER = [
    "spot_r50",
    "spot_r68",
    "spot_r90",
    "spot_r95",
    "spot_r99",
    "spot_rmax",
    "full_aperture_1p8",
]


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def f(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = row.get(key, default)
    if value in ("", None):
        return default
    return float(value)


def fmt(value: Any, ndigits: int = 6) -> str:
    if value in ("", None):
        return ""
    x = float(value)
    if not math.isfinite(x):
        return "nan"
    if x == 0.0:
        return "0"
    if abs(x) < 1.0e-3 or abs(x) >= 1.0e5:
        return f"{x:.{ndigits}e}"
    return f"{x:.{ndigits}g}"


def crossing_time(days: list[float], values: list[float], threshold: float) -> float | None:
    for idx, value in enumerate(values):
        if value < threshold:
            continue
        if idx == 0:
            return days[0]
        prev_v = values[idx - 1]
        prev_d = days[idx - 1]
        denom = value - prev_v
        if denom <= 0.0:
            return days[idx]
        return prev_d + (threshold - prev_v) * (days[idx] - prev_d) / denom
    return None


def extrapolated_time(final_day: float, final_z: float, threshold: float) -> float:
    if final_z <= 0.0:
        return math.inf
    return final_day * (threshold / final_z) ** 2


def asimov_poisson_z(source_counts: list[float], background_counts: list[float]) -> float:
    q = 0.0
    for source, background in zip(source_counts, background_counts):
        if source <= 0.0:
            continue
        if background <= 0.0:
            background = 1.0e-300
        q += 2.0 * ((source + background) * math.log1p(source / background) - source)
    return math.sqrt(max(q, 0.0))


def fold_rates(
    signal_cps: float,
    prompt_cps: float,
    delayed_cps: float,
    bg_rows: list[dict[str, str]],
    tau_s: float,
) -> dict[str, Any]:
    cumulative_source = 0.0
    cumulative_prompt = 0.0
    cumulative_delayed = 0.0
    cumulative_background = 0.0
    elapsed = 0.0
    days: list[float] = []
    zvals: list[float] = []
    for row in bg_rows:
        dt_s = f(row, "dt_s")
        live = math.exp(-(f(row, "prompt_event_rate_hz") + f(row, "delayed_event_rate_hz")) * tau_s)
        source = signal_cps * f(row, "science_atm_scale_to_day15") * live
        prompt = prompt_cps * f(row, "prompt_scale_to_day15") * live
        delayed = delayed_cps * f(row, "delayed_activity_scale_to_day15") * live
        cumulative_source += source * dt_s
        cumulative_prompt += prompt * dt_s
        cumulative_delayed += delayed * dt_s
        cumulative_background += (prompt + delayed) * dt_s
        elapsed += dt_s
        z = cumulative_source / math.sqrt(cumulative_background) if cumulative_background > 0.0 else 0.0
        days.append(elapsed / SECONDS_PER_DAY)
        zvals.append(z)
    final_day = days[-1] if days else 0.0
    final_z = zvals[-1] if zvals else 0.0
    t3 = crossing_time(days, zvals, 3.0)
    t5 = crossing_time(days, zvals, 5.0)
    return {
        "Z20d_time_dependent": final_z,
        "T3_day_time_dependent": t3 if t3 is not None else extrapolated_time(final_day, final_z, 3.0),
        "T5_day_time_dependent": t5 if t5 is not None else extrapolated_time(final_day, final_z, 5.0),
        "T3_status": "mission_internal_crossing" if t3 is not None else "extrapolated_beyond_20d",
        "T5_status": "mission_internal_crossing" if t5 is not None else "extrapolated_beyond_20d",
        "F3_20d_ph_cm2_s": REFERENCE_FLUX * 3.0 / final_z if final_z > 0.0 else math.inf,
        "source_counts_20d": cumulative_source,
        "prompt_counts_20d": cumulative_prompt,
        "delayed_counts_20d": cumulative_delayed,
        "background_counts_20d": cumulative_background,
    }


def build() -> dict[str, Any]:
    step05 = load_json(STEP05)
    step08 = load_json(STEP08)
    spatial_rows = {row["cut_id"]: row for row in read_csv(SPATIAL_CUTS)}
    bg_rows = [row for row in read_csv(STEP06_BG) if row["selection_id"] == W2]
    bg_rows.sort(key=lambda row: int(row["time_bin_id"]))
    w2 = step05["windows"][W2]["physical_reference_flux"]
    tau_s = float(step05["normalization"]["coincidence_window_s"])
    hard_signal = float(w2["signal_cps_at_reference_flux"])
    hard_prompt = float(w2["prompt_background_cps"])
    hard_delayed = float(w2["delayed_background_cps"])
    hard_background = float(w2["background_cps"])
    full = spatial_rows["full_aperture_1p8"]
    prompt_scale = hard_prompt / f(full, "prompt_cps")
    delayed_scale = hard_delayed / f(full, "delayed_cps")

    hard_fold = fold_rates(hard_signal, hard_prompt, hard_delayed, bg_rows, tau_s)
    hard_z_authority = float(step08["checks"]["A_reference_w2_Z20d_time_dependent"])
    hard_f3_authority = float(step08["checks"]["A_reference_w2_flux_3sigma_20d_ph_cm2_s"])

    cut_rows: list[dict[str, Any]] = []
    for cut_id in CUT_ORDER:
        row = spatial_rows[cut_id]
        prompt_cps = f(row, "prompt_cps") * prompt_scale
        delayed_cps = f(row, "delayed_cps") * delayed_scale
        signal_cps = f(row, "signal_cps_at_reference_flux")
        background_cps = prompt_cps + delayed_cps
        folded = fold_rates(signal_cps, prompt_cps, delayed_cps, bg_rows, tau_s)
        cut_rows.append(
            {
                "cut_id": cut_id,
                "radius_cm": f(row, "radius_cm"),
                "signal_psf_fraction_vs_spatial_full": f(row, "signal_psf_fraction"),
                "signal_cps_at_reference_flux": signal_cps,
                "signal_keep_vs_current_hard_window": signal_cps / hard_signal,
                "prompt_cps_scaled_to_current": prompt_cps,
                "prompt_keep_vs_current_hard_window": prompt_cps / hard_prompt,
                "prompt_reduction_factor_vs_current_hard_window": hard_prompt / prompt_cps if prompt_cps > 0.0 else math.inf,
                "delayed_cps_scaled_to_current": delayed_cps,
                "delayed_keep_vs_current_hard_window": delayed_cps / hard_delayed,
                "background_cps_scaled_to_current": background_cps,
                "background_keep_vs_current_hard_window": background_cps / hard_background,
                **folded,
                "Z_gain_vs_current_hard_window": folded["Z20d_time_dependent"] / hard_fold["Z20d_time_dependent"],
                "F3_improvement_vs_current_hard_window": hard_fold["F3_20d_ph_cm2_s"] / folded["F3_20d_ph_cm2_s"],
            }
        )

    best_counting = max([row for row in cut_rows if row["cut_id"] != "full_aperture_1p8"], key=lambda row: row["Z20d_time_dependent"])
    spot_r90 = next(row for row in cut_rows if row["cut_id"] == "spot_r90")

    annuli: list[dict[str, Any]] = []
    previous: dict[str, Any] | None = None
    for row in [spatial_rows[cut] for cut in ["spot_r50", "spot_r68", "spot_r90", "spot_r95", "spot_r99", "full_aperture_1p8"]]:
        if previous is None:
            inner = 0.0
            prev_signal = prev_prompt = prev_delayed = 0.0
        else:
            inner = f(previous, "radius_cm")
            prev_signal = f(previous, "signal_cps_at_reference_flux")
            prev_prompt = f(previous, "prompt_cps") * prompt_scale
            prev_delayed = f(previous, "delayed_cps") * delayed_scale
        signal_cps = max(0.0, f(row, "signal_cps_at_reference_flux") - prev_signal)
        prompt_cps = max(0.0, f(row, "prompt_cps") * prompt_scale - prev_prompt)
        delayed_cps = max(0.0, f(row, "delayed_cps") * delayed_scale - prev_delayed)
        folded = fold_rates(signal_cps, prompt_cps, delayed_cps, bg_rows, tau_s)
        annuli.append(
            {
                "annulus_id": f"{inner:.6g}_{f(row, 'radius_cm'):.6g}",
                "outer_cut_id": row["cut_id"],
                "r_inner_cm": inner,
                "r_outer_cm": f(row, "radius_cm"),
                "signal_cps_at_reference_flux": signal_cps,
                "prompt_cps_scaled_to_current": prompt_cps,
                "delayed_cps_scaled_to_current": delayed_cps,
                "background_cps_scaled_to_current": prompt_cps + delayed_cps,
                **folded,
                "s_over_sqrt_b_annulus": folded["source_counts_20d"] / math.sqrt(folded["background_counts_20d"]) if folded["background_counts_20d"] > 0.0 else 0.0,
            }
        )
        previous = row

    annular_z = asimov_poisson_z(
        [float(row["source_counts_20d"]) for row in annuli],
        [float(row["background_counts_20d"]) for row in annuli],
    )
    annular_f3 = REFERENCE_FLUX * 3.0 / annular_z if annular_z > 0.0 else math.inf

    out_csv = OUT / "prompt511_spatial_roi_smoke_cuts.csv"
    out_annuli = OUT / "prompt511_spatial_roi_smoke_annuli.csv"
    out_json = OUT / "prompt511_spatial_roi_smoke_summary.json"
    out_md = OUT / "prompt511_spatial_roi_smoke_report.md"
    write_csv(out_csv, cut_rows)
    write_csv(out_annuli, annuli)

    payload = {
        "status": "PASS_PROMPT511_SPATIAL_ROI_DIAGNOSTIC_WITHDRAWN_AS_STRATEGY",
        "label": LABEL,
        "scope": "Post-processing detector-coordinate spatial ROI diagnostic only; withdrawn as the prompt-suppression strategy.",
        "inputs": {
            "step05_summary": rel(STEP05),
            "step06_background_time_variation": rel(STEP06_BG),
            "step08_summary": rel(STEP08),
            "spatial_cuts_csv": rel(SPATIAL_CUTS),
            "claude_fix_review": rel(CLAUDE_REVIEW),
            "current_boundary_closure_summary": rel(BOUNDARY),
        },
        "normalization": {
            "hard_window_signal_cps_at_reference_flux": hard_signal,
            "hard_window_prompt_cps": hard_prompt,
            "hard_window_delayed_cps": hard_delayed,
            "hard_window_background_cps": hard_background,
            "spatial_full_aperture_prompt_cps_before_scaling": f(full, "prompt_cps"),
            "spatial_full_aperture_delayed_cps_before_scaling": f(full, "delayed_cps"),
            "spatial_full_aperture_signal_cps": f(full, "signal_cps_at_reference_flux"),
            "prompt_scale_to_current_hard_window": prompt_scale,
            "delayed_scale_to_current_hard_window": delayed_scale,
        },
        "hard_window_validation": {
            "folded_Z20d": hard_fold["Z20d_time_dependent"],
            "authority_Z20d": hard_z_authority,
            "relative_Z20d_difference": (hard_fold["Z20d_time_dependent"] - hard_z_authority) / hard_z_authority,
            "folded_F3_20d_ph_cm2_s": hard_fold["F3_20d_ph_cm2_s"],
            "authority_F3_20d_ph_cm2_s": hard_f3_authority,
        },
        "headline": {
            "best_counting_cut_id": best_counting["cut_id"],
            "best_counting_radius_cm": best_counting["radius_cm"],
            "best_counting_Z20d": best_counting["Z20d_time_dependent"],
            "best_counting_F3_20d_ph_cm2_s": best_counting["F3_20d_ph_cm2_s"],
            "best_counting_prompt_reduction_factor": best_counting["prompt_reduction_factor_vs_current_hard_window"],
            "spot_r90_prompt_cps_scaled_to_current": spot_r90["prompt_cps_scaled_to_current"],
            "spot_r90_prompt_reduction_factor": spot_r90["prompt_reduction_factor_vs_current_hard_window"],
            "spot_r90_signal_keep_vs_current_hard_window": spot_r90["signal_keep_vs_current_hard_window"],
            "spot_r90_signal_psf_fraction_vs_spatial_full": spot_r90["signal_psf_fraction_vs_spatial_full"],
            "spot_r90_background_cps_scaled_to_current": spot_r90["background_cps_scaled_to_current"],
            "spot_r90_Z20d": spot_r90["Z20d_time_dependent"],
            "spot_r90_F3_20d_ph_cm2_s": spot_r90["F3_20d_ph_cm2_s"],
            "annular_likelihood_Z20d_rescaled_delayed": annular_z,
            "annular_likelihood_F3_20d_ph_cm2_s_rescaled_delayed": annular_f3,
            "annular_likelihood_gain_vs_spot_r90": annular_z / spot_r90["Z20d_time_dependent"],
        },
        "outputs": {
            "summary_json": rel(out_json),
            "report_md": rel(out_md),
            "cut_csv": rel(out_csv),
            "annuli_csv": rel(out_annuli),
        },
        "limitations": [
            "This is a post-processing sidecar; it does not replace the hard-window rate authority.",
            "Prompt spatial fractions come from the existing detector-coupled spatial table and are scaled to current M=50000 hard-window prompt normalization.",
            "Delayed spatial fractions are rescaled to current exact-position delayed normalization, but a selection-consistent exactpos delayed spatial table is still a stronger future check.",
            "No new passive material or W activation penalty is introduced, but this also means the side-port/side-wall prompt source is not physically fixed.",
            "The annular likelihood is fixed-template only; no nuisance-profile or publication-analysis claim is made.",
            "After the old/current prompt-entry audit, do not promote ROI as the prompt-suppression strategy; use it only as a spatial diagnostic.",
        ],
    }
    write_json(out_json, payload)

    lines = [
        "# Prompt 511 Spatial ROI Smoke",
        "",
        "Status: `PASS_PROMPT511_SPATIAL_ROI_DIAGNOSTIC_WITHDRAWN_AS_STRATEGY`.",
        "",
        "This report records a detector-coordinate spatial ROI diagnostic around the focused 511 keV spot. It is withdrawn as a prompt-suppression strategy: the old/current prompt-entry audit shows the root issue is the current side-port/side-wall geometry and source-surface normalization, not the absence of an ROI.",
        "",
        "## Headline",
        "",
        f"- Current hard-window authority: `{LABEL}`; W2 prompt/delayed/signal = `{fmt(hard_prompt)}` / `{fmt(hard_delayed)}` / `{fmt(hard_signal)}` cps.",
        f"- Best counting ROI in this scan: `{best_counting['cut_id']}` at `{fmt(best_counting['radius_cm'])}` cm.",
        f"- The scan rows are spatial-table ROI rows; `full_aperture_1p8` is not identical to the hard-window authority because its signal support is `{fmt(f(full, 'signal_cps_at_reference_flux') / hard_signal)}` of the current hard-window W2 signal.",
        f"- `spot_r90` prompt falls to `{fmt(spot_r90['prompt_cps_scaled_to_current'])}` cps, a `{fmt(spot_r90['prompt_reduction_factor_vs_current_hard_window'])}x` prompt reduction versus the current hard window.",
        f"- `spot_r90` keeps `{fmt(spot_r90['signal_psf_fraction_vs_spatial_full'])}` of the spatial-table focused spot, or `{fmt(spot_r90['signal_keep_vs_current_hard_window'])}` of the current hard-window W2 signal.",
        f"- With current exactpos delayed normalization rescaled by spatial fraction, `spot_r90` gives B=`{fmt(spot_r90['background_cps_scaled_to_current'])}` cps, Z20d=`{fmt(spot_r90['Z20d_time_dependent'])}`, F3(20d)=`{fmt(spot_r90['F3_20d_ph_cm2_s'])}`.",
        f"- Fixed-template annular likelihood with the same rescaled delayed normalization gives Z20d=`{fmt(annular_z)}`, F3(20d)=`{fmt(annular_f3)}`; this is an analysis sidecar, not a prompt-rate cut.",
        "",
        "## Cut Scan",
        "",
        "| cut | radius cm | prompt cps | prompt keep | signal keep vs hard W2 | B cps | Z20d | F3(20d) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in cut_rows:
        lines.append(
            f"| {row['cut_id']} | {fmt(row['radius_cm'])} | {fmt(row['prompt_cps_scaled_to_current'])} | "
            f"{fmt(row['prompt_keep_vs_current_hard_window'])} | {fmt(row['signal_keep_vs_current_hard_window'])} | "
            f"{fmt(row['background_cps_scaled_to_current'])} | {fmt(row['Z20d_time_dependent'])} | "
            f"{fmt(row['F3_20d_ph_cm2_s'])} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `spot_r90` remains useful as a diagnostic showing that surviving prompt is more spatially diffuse than the focused signal.",
            "- Tighter cuts such as `spot_r50` lower prompt further, but they give worse total significance because signal loss outruns the extra prompt rejection.",
            "- The outer annuli are prompt-rich and signal-poor; annular likelihood can use this information, but that is an analysis diagnostic rather than a hardware prompt fix.",
            "- Do not use this report to recommend ROI before hardware shielding. The prompt-fix direction is local side-port/side-wall geometry closure, with MC/CAD validation and delayed-activation cost accounting.",
            "",
            "## Boundary",
            "",
            "- This smoke does not modify the current hard-window authority or manuscript headline.",
            "- This smoke is withdrawn as a prompt-suppression strategy; it is retained only for diagnostic traceability.",
            "- `full_aperture_1p8` in the cut table is the spatial-table support aperture, not a synonym for the hard-window authority.",
            "- Delayed spatial fractions are inherited from the existing spatial cut table and rescaled to the current exactpos delayed total. A fully selection-consistent exactpos spatial table would be the next stronger check.",
            "- The current authority hard-window fold is reproduced by this script within the validation tolerance recorded in the summary JSON.",
            "",
            "## Outputs",
            "",
            f"- summary JSON: `{rel(out_json)}`",
            f"- cut CSV: `{rel(out_csv)}`",
            f"- annuli CSV: `{rel(out_annuli)}`",
        ]
    )
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    payload = build()
    print(json.dumps({"status": payload["status"], "headline": payload["headline"]}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
