#!/usr/bin/env python3
"""Build v3p5 boundary-closure sidecars.

This report closes two analysis boundaries that can be closed from current
authority products without new particle transport:

* the inherited scalar T_atm boundary, by recomputing a 45 degree side-entry
  Beer-Lambert line-of-sight sidecar from the Step06 vertical-depth model;
* the "single spatial cut only" boundary, by turning the existing W2 spatial
  cut table into non-overlapping annular templates and evaluating a fixed
  Poisson spatial likelihood sidecar.

For the default ``fullstat_v2`` label it does not claim to close the
exact-position delayed-source transport boundary.  For the
``fullstat_v2_exactpos`` label it records the exact-RPIP PointSource production
transport status from the exact-position Step02 summary.
"""

from __future__ import annotations

import csv
import argparse
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
LABEL = "fullstat_v2"
OUT = ROOT / "outputs" / "reports" / "v3p5_boundary_closure_20260613"

STEP02 = (
    ROOT
    / "stepwise_maintenance"
    / "step02_raw_background_simulation"
    / "outputs_v3p5_centerfinger_fullstat_v2"
    / "step02_v3p5_centerfinger_fullstat_v2_summary.json"
)
STEP05 = (
    ROOT
    / "stepwise_maintenance"
    / "step05_veto_time_axis"
    / "outputs_v3p5_centerfinger_fullstat_v2_l1"
    / "step05_v3p5_centerfinger_l1_response_summary.json"
)
STEP06_BG = (
    ROOT
    / "stepwise_maintenance"
    / "step06_mission_time_variation"
    / "outputs_v3p5_centerfinger_fullstat_v2"
    / "background_time_variation.csv"
)
STEP08 = (
    ROOT
    / "stepwise_maintenance"
    / "step08_significance"
    / "outputs_v3p5_centerfinger_fullstat_v2"
    / "step08_v3p5_centerfinger_time_dependent_summary.json"
)
SPATIAL_CUTS = (
    ROOT
    / "stepwise_maintenance"
    / "step09_optics_bridge"
    / "outputs_f10m_a1_v3p5"
    / "detector_coupled_spatial_line_cuts.csv"
)
SPATIAL_PROXY = (
    ROOT
    / "stepwise_maintenance"
    / "step08_significance"
    / "outputs_v3p5_centerfinger_fullstat_v2_spatial"
    / "v3p5_spatial_line_proxy_summary.json"
)
DECAY_SOURCE = ROOT / "runs" / "step02_decay_source_v3p5_centerfinger_fullstat_v2"
DELAY_FIX = ROOT / "runs" / "step02_delay_fix_v3p5_centerfinger_fullstat_v2"
EXACTPOS_CONVERGENCE = ROOT / "outputs" / "reports" / "v3p5_exactpos_convergence_20260614" / "v3p5_exactpos_convergence_summary.json"

SECONDS_PER_DAY = 86400.0
REFERENCE_FLUX = 1.0e-4
TAU_S = 1.0e-6
W2_SELECTION = "w2_510p58_511p42"
CUT_ORDER = [
    "spot_r50",
    "spot_r68",
    "spot_r90",
    "spot_r95",
    "spot_r99",
    "full_aperture_1p8",
]


def configure_paths(label: str) -> None:
    global LABEL, OUT, STEP02, STEP05, STEP06_BG, STEP08, SPATIAL_PROXY, DECAY_SOURCE, DELAY_FIX

    LABEL = label
    if label == "fullstat_v2":
        OUT = ROOT / "outputs" / "reports" / "v3p5_boundary_closure_20260613"
    else:
        OUT = ROOT / "outputs" / "reports" / f"v3p5_boundary_closure_{label}_20260613"
    STEP02 = (
        ROOT
        / "stepwise_maintenance"
        / "step02_raw_background_simulation"
        / f"outputs_v3p5_centerfinger_{label}"
        / f"step02_v3p5_centerfinger_{label}_summary.json"
    )
    STEP05 = (
        ROOT
        / "stepwise_maintenance"
        / "step05_veto_time_axis"
        / f"outputs_v3p5_centerfinger_{label}_l1"
        / "step05_v3p5_centerfinger_l1_response_summary.json"
    )
    STEP06_BG = (
        ROOT
        / "stepwise_maintenance"
        / "step06_mission_time_variation"
        / f"outputs_v3p5_centerfinger_{label}"
        / "background_time_variation.csv"
    )
    STEP08 = (
        ROOT
        / "stepwise_maintenance"
        / "step08_significance"
        / f"outputs_v3p5_centerfinger_{label}"
        / "step08_v3p5_centerfinger_time_dependent_summary.json"
    )
    spatial_candidate = (
        ROOT
        / "stepwise_maintenance"
        / "step08_significance"
        / f"outputs_v3p5_centerfinger_{label}_spatial"
        / "v3p5_spatial_line_proxy_summary.json"
    )
    SPATIAL_PROXY = (
        spatial_candidate
        if spatial_candidate.exists()
        else ROOT
        / "stepwise_maintenance"
        / "step08_significance"
        / "outputs_v3p5_centerfinger_fullstat_v2_spatial"
        / "v3p5_spatial_line_proxy_summary.json"
    )
    DECAY_SOURCE = ROOT / "runs" / "step02_decay_source_v3p5_centerfinger_fullstat_v2"
    delay_candidate = ROOT / "runs" / f"step02_delay_fix_v3p5_centerfinger_{label}"
    DELAY_FIX = delay_candidate if delay_candidate.exists() else ROOT / "runs" / "step02_delay_fix_v3p5_centerfinger_fullstat_v2"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def exactpos_convergence() -> dict[str, Any] | None:
    if not EXACTPOS_CONVERGENCE.exists():
        return None
    return load_json(EXACTPOS_CONVERGENCE)


def exactpos_promoted() -> bool:
    report = exactpos_convergence()
    evaluation = (report or {}).get("evaluation", {})
    return (
        report is not None
        and report.get("status") == "PASS_EXACTPOS_TRANSPORT_CONVERGENCE"
        and evaluation.get("authority_recommendation") == "PROMOTE_EXACTPOS_TO_CURRENT_RATE_AUTHORITY"
    )


def authority_role() -> str:
    if LABEL.startswith("fullstat_v2_exactpos"):
        if exactpos_promoted():
            return "CURRENT_EXACT_POSITION_RATE_AUTHORITY"
        return "PROVISIONAL_EXACT_POSITION_CLOSURE_SUPPORT_SIZE_PENDING"
    if exactpos_promoted():
        return "CONSERVATIVE_RADIALPROFILE_BASELINE_CROSSCHECK"
    return "CONSERVATIVE_CURRENT_RATE_AUTHORITY"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def f(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = row.get(key, default)
    if value in ("", None):
        return default
    return float(value)


def asimov_poisson_z(source_counts: list[float], background_counts: list[float]) -> float:
    q = 0.0
    for s, b in zip(source_counts, background_counts):
        if s <= 0.0:
            continue
        if b <= 0.0:
            # This project has no zero-background annulus in the current W2 table.
            # Keep the expression finite if a future sparse table creates one.
            b = 1.0e-300
        q += 2.0 * ((s + b) * math.log1p(s / b) - s)
    return math.sqrt(max(q, 0.0))


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


def cut_rows() -> list[dict[str, Any]]:
    rows = {row["cut_id"]: row for row in read_csv(SPATIAL_CUTS)}
    return [rows[cut] for cut in CUT_ORDER]


def annular_templates() -> list[dict[str, Any]]:
    annuli: list[dict[str, Any]] = []
    previous: dict[str, Any] | None = None
    for row in cut_rows():
        if previous is None:
            inner = 0.0
            prev = {"signal_cps_at_reference_flux": 0.0, "prompt_cps": 0.0, "delayed_cps": 0.0}
        else:
            inner = f(previous, "radius_cm")
            prev = previous
        annuli.append(
            {
                "annulus_id": f"{inner:.6g}_{f(row, 'radius_cm'):.6g}",
                "outer_cut_id": row["cut_id"],
                "r_inner_cm": inner,
                "r_outer_cm": f(row, "radius_cm"),
                "signal_cps_at_reference_flux": max(0.0, f(row, "signal_cps_at_reference_flux") - f(prev, "signal_cps_at_reference_flux")),
                "prompt_cps": max(0.0, f(row, "prompt_cps") - f(prev, "prompt_cps")),
                "delayed_cps": max(0.0, f(row, "delayed_cps") - f(prev, "delayed_cps")),
                "background_cps": max(0.0, f(row, "background_cps") - f(prev, "background_cps")),
            }
        )
        previous = row
    return annuli


def fold_counts(
    signal_cps: float,
    prompt_cps: float,
    delayed_cps: float,
    *,
    slant_secant: float = 1.0,
    t_ref_vertical: float | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Fold one response through Step06.

    If slant_secant > 1, signal is re-normalized to an absolute slant LOS:
    T_slant(depth) = T_vertical(depth)**slant_secant.
    """
    rows = [row for row in read_csv(STEP06_BG) if row["selection_id"] == "w2_510p58_511p42"]
    source_total = 0.0
    background_total = 0.0
    elapsed = 0.0
    days: list[float] = []
    zvals: list[float] = []
    curve: list[dict[str, Any]] = []
    if t_ref_vertical is None:
        t_ref_vertical = f(rows[0], "T_atm_511")
    t_ref_slant = t_ref_vertical**slant_secant
    day15_signal_scale = t_ref_slant / t_ref_vertical
    for row in rows:
        dt_s = f(row, "dt_s")
        prompt_scale = f(row, "prompt_scale_to_day15")
        delayed_scale = f(row, "delayed_activity_scale_to_day15")
        t_vert = f(row, "T_atm_511")
        science_scale = (t_vert**slant_secant) / t_ref_slant
        live = math.exp(-(f(row, "prompt_event_rate_hz") + f(row, "delayed_event_rate_hz")) * TAU_S)
        source = signal_cps * day15_signal_scale * science_scale * live
        background = (prompt_cps * prompt_scale + delayed_cps * delayed_scale) * live
        source_total += source * dt_s
        background_total += background * dt_s
        elapsed += dt_s
        z = source_total / math.sqrt(background_total) if background_total > 0.0 else 0.0
        days.append(elapsed / SECONDS_PER_DAY)
        zvals.append(z)
        curve.append(
            {
                "time_bin_id": row["time_bin_id"],
                "day_mid": row["day_mid"],
                "elapsed_stop_day": elapsed / SECONDS_PER_DAY,
                "dt_s": dt_s,
                "T_atm_vertical": t_vert,
                "T_atm_slant": t_vert**slant_secant,
                "science_scale_to_day15": science_scale,
                "accidental_live_factor": live,
                "source_cps": source,
                "background_cps": background,
                "cumulative_source_counts": source_total,
                "cumulative_background_counts": background_total,
                "counting_Z": z,
            }
        )
    final_day = days[-1]
    final_z = zvals[-1]
    t3 = crossing_time(days, zvals, 3.0)
    return (
        {
            "Z20d": final_z,
            "T3_day": t3 if t3 is not None else extrapolated_time(final_day, final_z, 3.0),
            "T3_status": "mission_internal_crossing" if t3 is not None else "extrapolated_beyond_20d",
            "flux_3sigma_20d_ph_cm2_s": REFERENCE_FLUX * 3.0 / final_z if final_z > 0.0 else math.inf,
            "total_source_counts": source_total,
            "total_background_counts": background_total,
            "T_ref_vertical": t_ref_vertical,
            "T_ref_slant": t_ref_slant,
            "day15_signal_scale_slant_vs_vertical": day15_signal_scale,
        },
        curve,
    )


def build_atmosphere_sidecar(step05: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    w2 = step05["windows"][W2_SELECTION]["physical_reference_flux"]
    cuts = {row["cut_id"]: row for row in cut_rows()}
    sec45 = math.sqrt(2.0)
    w2_metrics, w2_curve = fold_counts(
        f(w2, "signal_cps_at_reference_flux"),
        f(w2, "prompt_background_cps"),
        f(w2, "delayed_background_cps"),
        slant_secant=sec45,
        t_ref_vertical=f(w2, "rate_to_v3p5_injection_plane_s-1") / (
            step05["science_physical_normalization"]["aeff_511_cm2"] * REFERENCE_FLUX
        ),
    )
    spot = cuts["spot_r90"]
    spot_metrics, spot_curve = fold_counts(
        f(spot, "signal_cps_at_reference_flux"),
        f(spot, "prompt_cps"),
        f(spot, "delayed_cps"),
        slant_secant=sec45,
        t_ref_vertical=w2_metrics["T_ref_vertical"],
    )
    curve_rows: list[dict[str, Any]] = []
    for case_id, rows in [("w2_hard_window", w2_curve), ("spot_r90", spot_curve)]:
        for row in rows:
            curve_rows.append({"case_id": case_id, **row})
    return (
        {
            "status": "PASS_V3P5_45DEG_LOS_ATMOSPHERE_SIDECAR",
            "base_label": LABEL,
            "claim_level": "L1_ABSOLUTE_LOS_RENORMALIZATION_SIDECAR_NO_NEW_TRANSPORT",
            "method": "T_slant(depth)=T_vertical(depth)**sec(45deg), using the same Step06 Beer-Lambert mu_eff and depth curve.",
            "secant_45deg": sec45,
            "w2_hard_window": w2_metrics,
            "spot_r90": spot_metrics,
            "inputs": {
                "step05": rel(STEP05),
                "step06_background_time_variation": rel(STEP06_BG),
            },
        },
        curve_rows,
    )


def build_spatial_likelihood_sidecar() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    bg_rows = [row for row in read_csv(STEP06_BG) if row["selection_id"] == W2_SELECTION]
    annuli = annular_templates()
    annulus_counts: list[dict[str, Any]] = []
    for annulus in annuli:
        source_total = 0.0
        background_total = 0.0
        prompt_total = 0.0
        delayed_total = 0.0
        for row in bg_rows:
            dt_s = f(row, "dt_s")
            live = math.exp(-(f(row, "prompt_event_rate_hz") + f(row, "delayed_event_rate_hz")) * TAU_S)
            source = f(annulus, "signal_cps_at_reference_flux") * f(row, "science_atm_scale_to_day15") * live
            prompt = f(annulus, "prompt_cps") * f(row, "prompt_scale_to_day15") * live
            delayed = f(annulus, "delayed_cps") * f(row, "delayed_activity_scale_to_day15") * live
            source_total += source * dt_s
            prompt_total += prompt * dt_s
            delayed_total += delayed * dt_s
            background_total += (prompt + delayed) * dt_s
        annulus_counts.append(
            {
                **annulus,
                "source_counts_20d": source_total,
                "prompt_counts_20d": prompt_total,
                "delayed_counts_20d": delayed_total,
                "background_counts_20d": background_total,
                "s_over_sqrt_b_annulus": source_total / math.sqrt(background_total) if background_total > 0.0 else 0.0,
            }
        )
    s_counts = [f(row, "source_counts_20d") for row in annulus_counts]
    b_counts = [f(row, "background_counts_20d") for row in annulus_counts]
    z_like = asimov_poisson_z(s_counts, b_counts)
    total_s = sum(s_counts)
    total_b = sum(b_counts)
    z_count = total_s / math.sqrt(total_b)
    spatial = load_json(SPATIAL_PROXY)["checks"]
    return (
        {
            "status": "PASS_V3P5_SPATIAL_ANNULAR_LIKELIHOOD_SIDECAR",
            "base_label": LABEL,
            "spatial_cuts_base": "detector_coupled_spatial_line_cuts_from_step09_f10m_a1_v3p5",
            "claim_level": "L1_FIXED_TEMPLATE_MULTI_ANNULUS_POISSON_LIKELIHOOD_NO_NUISANCE_PROFILE",
            "method": "Non-overlapping annuli from detector_coupled_spatial_line_cuts.csv; Asimov Poisson likelihood ratio for reference flux.",
            "annulus_count": len(annulus_counts),
            "total_source_counts_20d": total_s,
            "total_background_counts_20d": total_b,
            "counting_Z20d_same_aperture": z_count,
            "annular_likelihood_Z20d": z_like,
            "flux_3sigma_20d_ph_cm2_s": REFERENCE_FLUX * 3.0 / z_like if z_like > 0.0 else math.inf,
            "gain_vs_full_aperture_counting": z_like / z_count if z_count > 0.0 else math.inf,
            "gain_vs_spot_r90_time_dependent": z_like / float(spatial["spot_r90_Z20d_time_dependent"]),
            "inputs": {
                "spatial_cuts_csv": rel(SPATIAL_CUTS),
                "step06_background_time_variation": rel(STEP06_BG),
                "spatial_proxy_summary": rel(SPATIAL_PROXY),
            },
            "boundaries": [
                "This is a fixed-template annular likelihood sidecar, not a nuisance-profile publication analysis.",
                "It uses W2-selected event rates already passed through active-veto and side-entry Compton/FoV selection.",
            ],
        },
        annulus_counts,
    )


def exact_position_status() -> dict[str, Any]:
    raw_audit = load_json(DECAY_SOURCE / "normalization_audit_day15.json")
    fixed_audit = load_json(DELAY_FIX / "normalization_audit_groundstate_fix.json")
    feasibility_evidence = {
        "repo_smoke_readme": "tests/realpos_delayed_smoke/README.md",
        "new_geo_re_smoke_readme": "../codex_tes_511_sim/new_geo_re/tests/realpos_delayed_smoke/README.md",
        "new_geo_re_verify_summary": "../codex_tes_511_sim/new_geo_re/tests/realpos_delayed_smoke/outputs/verify_summary.json",
        "new_geo_re_smoke_events_SE": 2000,
        "new_geo_re_smoke_match_fraction": 0.9905,
    }
    if LABEL.startswith("fullstat_v2_exactpos") and STEP02.exists():
        step02 = load_json(STEP02)
        delayed = step02.get("delayed_transport", {})
        exact = step02.get("exact_position_delayed_source", {})
        if delayed.get("status") == "PASS":
            se = int(delayed.get("SE") or 0)
            ident = int(delayed.get("ID") or 0)
            status = "PASS_EXACT_RPIP_POINTSOURCE_PRODUCTION_TRANSPORT" if se > 0 and se == ident else "FAIL_EXACT_RPIP_POINTSOURCE_TRANSPORT_COUNTS"
            return {
                "status": status,
                "claim_level": "CLOSED_FOR_EXACTPOS_SAMPLE_SUPPORT_RUN",
                "raw_audit_status": raw_audit.get("status"),
                "fixed_audit_status": fixed_audit.get("status"),
                "feasibility_status": "EXACT_RPIP_POINTSOURCE_SMOKE_VALIDATED_AND_PROMOTED_TO_V3P5_RUN",
                "feasibility_evidence": feasibility_evidence,
                "source_mode": exact.get("source_mode"),
                "n_pointsource_blocks": exact.get("n_pointsource_blocks"),
                "triggers_requested": exact.get("triggers_requested"),
                "fixed_total_activity_Bq": exact.get("fixed_total_activity_Bq"),
                "sum_flux_check_Bq": exact.get("sum_flux_check_Bq"),
                "delayed_transport": delayed,
                "convergence": {
                    "status": (exactpos_convergence() or {}).get("status"),
                    "summary_json": rel(EXACTPOS_CONVERGENCE),
                },
                "inputs": {
                    "step02_summary": rel(STEP02),
                    "delay_fix_dir": rel(DELAY_FIX),
                },
                "limitations": [
                    "This exact-position production closure uses the sampled PointSource support recorded in the source manifest, not the full weighted-table one-block-per-RPIP source if source_mode is sampled_equal_flux_pointsource_blocks.",
                    "The source is fixed-inventory and activity-preserving; spatial sampling uncertainty is controlled by the sampled support size recorded above.",
                ],
            }
        return {
            "status": "EXACT_RPIP_POINTSOURCE_SOURCE_READY_TRANSPORT_NOT_SUMMARIZED",
            "claim_level": "NOT_CLOSED_FOR_EXACTPOS_NUMBERS",
            "raw_audit_status": raw_audit.get("status"),
            "fixed_audit_status": fixed_audit.get("status"),
            "feasibility_status": "EXACT_RPIP_POINTSOURCE_SMOKE_VALIDATED_AND_V3P5_SOURCE_READY",
            "feasibility_evidence": feasibility_evidence,
            "source_mode": exact.get("source_mode"),
            "n_pointsource_blocks": exact.get("n_pointsource_blocks"),
            "triggers_requested": exact.get("triggers_requested"),
            "remaining_required_work": ["Finish/summarize the exact-position delayed transport before using this report as a closed exactpos authority."],
            "current_blocker": f"Step02 exactpos delayed_transport status is {delayed.get('status')!r}.",
        }
    return {
        "status": "SOURCE_AUDITS_PASS_TRANSPORT_NOT_RERUN",
        "claim_level": "NOT_CLOSED_FOR_PAPER_NUMBERS",
        "raw_audit_status": raw_audit.get("status"),
        "fixed_audit_status": fixed_audit.get("status"),
        "feasibility_status": "EXACT_RPIP_POINTSOURCE_SMOKE_VALIDATED_NOT_PRODUCTION_RERUN",
        "feasibility_evidence": feasibility_evidence,
        "remaining_required_work": [
            "Promote the smoke-validated exact-RPIP PointSource builder to v3p5 fullstat using ground-state-fixed activities and the in-fixed-inventory RPIP filter.",
            "Run new delayed transport at the production trigger budget.",
            "Rerun Step05/06/07/08 and this closure report from the exact-position delayed transport.",
        ],
        "current_blocker": "The current v3p5 production delayed transport still uses the RadialProfileBeam-compressed source; feasibility is solved, production transport is not rerun.",
    }


def markdown(payload: dict[str, Any]) -> str:
    atm = payload["atmosphere_45deg_los"]
    like = payload["spatial_annular_likelihood"]
    exact = payload["exact_position_delayed_source"]
    if str(exact.get("status", "")).startswith("PASS_EXACT_RPIP"):
        convergence_status = (exact.get("convergence") or {}).get("status")
        convergence_text = (
            f" Convergence status: `{convergence_status}`."
            if convergence_status
            else ""
        )
        exact_text = (
            f"Feasibility: `{exact['feasibility_status']}`. The exact-RPIP `PointSource` path is smoke-validated and this "
            f"`{payload['statistics_label']}` report is built from the summarized exact-position delayed transport. "
            f"Source mode: `{exact.get('source_mode', '')}`, PointSource blocks: `{exact.get('n_pointsource_blocks', '')}`."
            f"{convergence_text}"
        )
    else:
        exact_text = (
            f"Feasibility: `{exact['feasibility_status']}`. The exact-RPIP `PointSource` path is smoke-validated in "
            "`tests/realpos_delayed_smoke/` and `../codex_tes_511_sim/new_geo_re/tests/realpos_delayed_smoke/`, "
            "but this boundary is not paper-closed until the fixed-inventory v3p5 production delayed transport is rerun."
        )
    return "\n".join(
        [
            "# v3p5 Boundary Closure Sidecars",
            "",
            f"Status: `{payload['status']}`.",
            f"Statistics label: `{payload['statistics_label']}`.",
            f"Base label: `{payload['base_label']}`.",
            f"Authority role: `{payload['authority_role']}`.",
            "",
            "## 45 deg Atmosphere LOS Sidecar",
            "",
            "This closes the scalar-inherited `T_atm` ambiguity as a sidecar by applying the Step06 Beer-Lambert depth model to a 45 deg slant column.",
            "",
            "| case | T_ref slant | Z20d | T3 day | 20d 3sigma flux |",
            "| --- | ---: | ---: | ---: | ---: |",
            f"| W2 hard window | {atm['w2_hard_window']['T_ref_slant']:.8g} | {atm['w2_hard_window']['Z20d']:.6g} | {atm['w2_hard_window']['T3_day']:.6g} | {atm['w2_hard_window']['flux_3sigma_20d_ph_cm2_s']:.6e} |",
            f"| spot_r90 | {atm['spot_r90']['T_ref_slant']:.8g} | {atm['spot_r90']['Z20d']:.6g} | {atm['spot_r90']['T3_day']:.6g} | {atm['spot_r90']['flux_3sigma_20d_ph_cm2_s']:.6e} |",
            "",
            "## Spatial Annular Likelihood Sidecar",
            "",
            "This closes the single-cut spatial-analysis boundary as a fixed-template multi-annulus Poisson likelihood sidecar.",
            "",
            f"- annuli: `{like['annulus_count']}`",
            f"- full-aperture counting Z20d: `{like['counting_Z20d_same_aperture']:.6g}`",
            f"- annular likelihood Z20d: `{like['annular_likelihood_Z20d']:.6g}`",
            f"- 20-day 3sigma flux: `{like['flux_3sigma_20d_ph_cm2_s']:.6e}` ph cm^-2 s^-1",
            f"- gain vs spot_r90 time fold: `{like['gain_vs_spot_r90_time_dependent']:.6g}`",
            "",
            "## Exact-Position Delayed Source",
            "",
            f"Status: `{exact['status']}`.",
            "",
            exact_text,
            "",
            "## Outputs",
            "",
            f"- summary JSON: `{payload['outputs']['summary_json']}`",
            f"- 45 deg curve CSV: `{payload['outputs']['atmosphere_45deg_curve_csv']}`",
            f"- annulus CSV: `{payload['outputs']['spatial_annulus_csv']}`",
        ]
    ) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="fullstat_v2", help="Run/output label, e.g. fullstat_v2 or fullstat_v2_exactpos")
    args = ap.parse_args()

    configure_paths(args.label)
    OUT.mkdir(parents=True, exist_ok=True)
    step05 = load_json(STEP05)
    atmosphere, atmosphere_curve = build_atmosphere_sidecar(step05)
    likelihood, annulus_rows = build_spatial_likelihood_sidecar()
    payload = {
        "status": "PASS_V3P5_BOUNDARY_CLOSURE_SIDECARS",
        "statistics_label": LABEL,
        "base_label": LABEL,
        "authority_role": authority_role(),
        "claim_level": "SIDECAR_CLOSURE_FOR_ATMOSPHERE_AND_SPATIAL_LIKELIHOOD",
        "atmosphere_45deg_los": atmosphere,
        "spatial_annular_likelihood": likelihood,
        "exact_position_delayed_source": exact_position_status(),
        "outputs": {
            "summary_json": rel(OUT / "v3p5_boundary_closure_summary.json"),
            "report_md": rel(OUT / "v3p5_boundary_closure_report.md"),
            "atmosphere_45deg_curve_csv": rel(OUT / "v3p5_45deg_los_time_curve.csv"),
            "spatial_annulus_csv": rel(OUT / "v3p5_spatial_annular_likelihood.csv"),
        },
    }
    write_csv(OUT / "v3p5_45deg_los_time_curve.csv", atmosphere_curve)
    write_csv(OUT / "v3p5_spatial_annular_likelihood.csv", annulus_rows)
    write_json(OUT / "v3p5_boundary_closure_summary.json", payload)
    (OUT / "v3p5_boundary_closure_report.md").write_text(markdown(payload), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "summary": payload["outputs"]["summary_json"], "report": payload["outputs"]["report_md"]}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
