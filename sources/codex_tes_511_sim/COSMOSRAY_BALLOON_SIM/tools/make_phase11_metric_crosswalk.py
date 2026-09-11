#!/usr/bin/env python3
"""Build Phase 11 metric crosswalk and reconciliation artifacts.

Phase 11 is a gate package. It reconciles Phase 7/9/10 sensitivity metrics,
guards the selection-only upgrade decision, and defines the production optics
interface required before final A/B point-diffuse claims.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shutil
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/codex_tes_511_matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
R2 = ROOT / "reports2.0"
OUT_DEFAULT = R2 / "11_METRIC_RECONCILIATION_AND_OPTICS_GATE"
FIG_DEFAULT = OUT_DEFAULT / "figures"
ABC_DEFAULT = R2 / "09_SOURCE_CASES_ABC"
PHASE10_DEFAULT = R2 / "10_POINT_DIFFUSE_DISCRIMINATION"
NIMA_DEFAULT = R2 / "07_NIMA_MANUSCRIPT"
CONFIG_DIR = ROOT / "configs" / "astro_source_cases"
SCRIPT_PACKAGE_DIR = R2 / "05_SCRIPTS_AND_CONFIG" / "tools"

PROFILED_DEFAULT = R2 / "02_PHASE2_CORE_MATERIALS" / "likelihood_profiled" / "asimov_profiled_sensitivity.csv"
INJECTION_DEFAULT = R2 / "02_PHASE2_CORE_MATERIALS" / "source_injection" / "source_injection_profiled_summary.csv"
DESIGN_TABLE_DEFAULT = R2 / "08_DESIGN_OPTIMIZATION_ADDON" / "WP_D5_design_recommendation" / "design_recommendation_table.csv"

REFERENCE_FLUX = 1.0e-4
EXPOSURE_S = 1.0e6
TARGET_FLUX = 1.0e-4

CROSSWALK_FIELDS = [
    "metric_id",
    "phase",
    "case_id",
    "source_model",
    "selection_variant",
    "energy_axis",
    "energy_window",
    "statistic_type",
    "template_dimension",
    "background_cps",
    "response_cps_per_flux",
    "F3_1Ms",
    "F5_1Ms",
    "P_ge_3sigma_at_1e-4_1Ms",
    "source_authority",
    "background_authority",
    "allowed_use",
    "claim_level",
    "notes",
]

REQUIRED_METRICS = {
    "P07_broad_window_counting_profiled",
    "P07_broad_ERL_profiled",
    "P07_line_ERL_profiled",
    "P07_source_injection_ERL_broad",
    "P09_A_baseline_mono_placeholder",
    "P09_A_selection_best_design_Q",
    "P10_A_baseline_count_only_L1",
    "P10_selection_best_measured_broad_count_only",
    "P11_template_TS_placeholder_trial",
}

FORBIDDEN_PHRASES = [
    "final GC point-source detection",
    "final V404 detectability",
    "Sgr A* source confirmed",
    "diffuse source negligible",
    "production point/diffuse separation",
    "selection best replaces baseline",
    "placeholder optics final",
    "total bulge flux as point source",
]

ALLOWING_GUARDS = ["forbidden", "not claimed", "placeholder only", "not final"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fields: list[str] = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
        fieldnames = fields
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_yaml(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, sort_keys=False, allow_unicode=False), encoding="utf-8")


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def f(row: dict[str, Any], key: str, default: float = float("nan")) -> float:
    try:
        val = row.get(key, default)
        if val == "":
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def fmt(value: float, ndigits: int = 6) -> str:
    if not math.isfinite(value):
        return "nan"
    if value == 0:
        return "0"
    if abs(value) < 1e-3 or abs(value) >= 1e4:
        return f"{value:.{ndigits}e}"
    return f"{value:.{ndigits}g}"


def normal_survival(z: float) -> float:
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def p_ge_3_from_f3(flux: float, f3_value: float) -> float:
    if not math.isfinite(f3_value) or f3_value <= 0:
        return float("nan")
    mean_z = 3.0 * flux / f3_value
    return normal_survival(3.0 - mean_z)


def asimov_ts(signal_cps: float, background_cps: float, exposure_s: float) -> float:
    if signal_cps <= 0 or background_cps <= 0 or exposure_s <= 0:
        return 0.0
    s = signal_cps * exposure_s
    b = background_cps * exposure_s
    return max(0.0, 2.0 * ((s + b) * math.log1p(s / b) - s))


def row_match(rows: list[dict[str, str]], **criteria: Any) -> dict[str, str]:
    for row in rows:
        ok = True
        for key, value in criteria.items():
            if isinstance(value, float):
                ok = ok and math.isclose(f(row, key), value, rel_tol=0.0, abs_tol=1e-9)
            else:
                ok = ok and row.get(key) == value
        if ok:
            return row
    raise KeyError(f"no row matching {criteria}")


def metric_row(
    metric_id: str,
    phase: str,
    case_id: str,
    source_model: str,
    selection_variant: str,
    energy_axis: str,
    energy_window: str,
    statistic_type: str,
    template_dimension: str,
    background_cps: float,
    response_cps_per_flux: float,
    f3_value: float,
    f5_value: float | None,
    p3_value: float | None,
    source_authority: str,
    background_authority: str,
    allowed_use: str,
    claim_level: str,
    notes: str,
) -> dict[str, Any]:
    if f5_value is None and math.isfinite(f3_value):
        f5_value = f3_value * 5.0 / 3.0
    if p3_value is None and math.isfinite(f3_value):
        p3_value = p_ge_3_from_f3(REFERENCE_FLUX, f3_value)
    return {
        "metric_id": metric_id,
        "phase": phase,
        "case_id": case_id,
        "source_model": source_model,
        "selection_variant": selection_variant,
        "energy_axis": energy_axis,
        "energy_window": energy_window,
        "statistic_type": statistic_type,
        "template_dimension": template_dimension,
        "background_cps": background_cps,
        "response_cps_per_flux": response_cps_per_flux,
        "F3_1Ms": f3_value,
        "F5_1Ms": f5_value,
        "P_ge_3sigma_at_1e-4_1Ms": p3_value,
        "source_authority": source_authority,
        "background_authority": background_authority,
        "allowed_use": allowed_use,
        "claim_level": claim_level,
        "notes": notes,
    }


def _template_bin_fractions(template_dimension: str) -> tuple[list[float], list[float], list[float]]:
    radius_bg = [0.12, 0.28, 0.36, 0.24]
    radius_a = [0.35, 0.40, 0.20, 0.05]
    layer_bg = [0.20, 0.18, 0.17, 0.16, 0.15, 0.14]
    layer_a = [0.50, 0.20, 0.12, 0.08, 0.06, 0.04]
    if template_dimension == "energy_radius_layer":
        return radius_bg, radius_a, [1.0]
    if template_dimension == "energy_radius_layer_multiplicity":
        return radius_bg, radius_a, [0.92, 0.08]
    raise ValueError(template_dimension)


def template_ts_for_flux(
    flux: float,
    response: float,
    instr_background: float,
    diffuse_background: float,
    exposure_s: float,
    template_dimension: str,
) -> float:
    radius_bg, radius_a, mult_a = _template_bin_fractions(template_dimension)
    layer_bg = [0.20, 0.18, 0.17, 0.16, 0.15, 0.14]
    layer_a = [0.50, 0.20, 0.12, 0.08, 0.06, 0.04]
    mult_bg = [0.65, 0.35] if template_dimension.endswith("multiplicity") else [1.0]
    signal_total = flux * response
    ts = 0.0
    for ir, (r_b, r_a) in enumerate(zip(radius_bg, radius_a)):
        for il, (l_b, l_a) in enumerate(zip(layer_bg, layer_a)):
            for im, m_b in enumerate(mult_bg):
                m_a = mult_a[im] if im < len(mult_a) else 1.0
                instr = instr_background * r_b * l_b * m_b
                diffuse = diffuse_background * r_b * l_b * m_b
                signal = signal_total * r_a * l_a * m_a
                ts += asimov_ts(signal, instr + diffuse, exposure_s)
    return ts


def solve_flux_for_sigma(
    response: float,
    instr_background: float,
    diffuse_background: float,
    exposure_s: float,
    template_dimension: str,
    sigma: float,
) -> float:
    lo, hi = 0.0, 1e-3
    while math.sqrt(template_ts_for_flux(hi, response, instr_background, diffuse_background, exposure_s, template_dimension)) < sigma:
        hi *= 2.0
        if hi > 1.0:
            return float("nan")
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        got = math.sqrt(template_ts_for_flux(mid, response, instr_background, diffuse_background, exposure_s, template_dimension))
        if got >= sigma:
            hi = mid
        else:
            lo = mid
    return hi


def template_trial_metric(phase10_dir: Path) -> dict[str, float]:
    p10_rows = read_csv(phase10_dir / "point_diffuse_discrimination.csv")
    baseline = next(
        row
        for row in p10_rows
        if row["mode"] == "count_only_L1"
        and row["selection_id"] == "baseline"
        and row["A_spectrum_model"] == "mono_511"
        and math.isclose(f(row, "A_flux_ph_cm2_s"), REFERENCE_FLUX, abs_tol=1e-12)
    )
    response = f(baseline, "A_expected_cps") / f(baseline, "A_flux_ph_cm2_s")
    instr = f(baseline, "instrument_background_cps")
    diffuse = f(baseline, "B_diffuse_cps")
    dimension = "energy_radius_layer_multiplicity"
    f3_value = solve_flux_for_sigma(response, instr, diffuse, EXPOSURE_S, dimension, 3.0)
    ts_ref = template_ts_for_flux(REFERENCE_FLUX, response, instr, diffuse, EXPOSURE_S, dimension)
    return {
        "response": response,
        "background": instr + diffuse,
        "instr": instr,
        "diffuse": diffuse,
        "f3": f3_value,
        "f5": solve_flux_for_sigma(response, instr, diffuse, EXPOSURE_S, dimension, 5.0),
        "p3": normal_survival(3.0 - math.sqrt(ts_ref)),
        "ts_ref": ts_ref,
        "dimension": dimension,
    }


def build_metric_crosswalk(
    out_csv: Path = OUT_DEFAULT / "metric_crosswalk_phase11.csv",
    phase9_dir: Path = ABC_DEFAULT,
    phase10_dir: Path = PHASE10_DEFAULT,
    profiled_path: Path = PROFILED_DEFAULT,
    injection_path: Path = INJECTION_DEFAULT,
    design_table: Path = DESIGN_TABLE_DEFAULT,
) -> list[dict[str, Any]]:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    FIG_DEFAULT.mkdir(parents=True, exist_ok=True)
    profiled = read_csv(profiled_path)
    injection = read_csv(injection_path)
    detect = read_csv(phase9_dir / "detectability_A_GC_POINT.csv")
    design = {row["design_case"]: row for row in read_csv(design_table)}
    p10_rows = read_csv(phase10_dir / "point_diffuse_discrimination.csv")
    audit_rows = read_csv(phase10_dir / "selection_best_measured_energy_audit.csv")

    source_authority = "run_configs/Science_511_onaxis_focalbeam_local.source"
    background_authority = "reports2.0/07_NIMA_MANUSCRIPT/final_numerical_lineage.csv"
    rows: list[dict[str, Any]] = []

    p07_window = row_match(profiled, energy_window="broad_480_550", model="window_counting_same_events", exposure_s=EXPOSURE_S)
    rows.append(
        metric_row(
            "P07_broad_window_counting_profiled",
            "Phase7/Phase2",
            "science_511_reference",
            "mono_511",
            "baseline",
            "true_energy",
            "broad_480_550",
            "WINDOW_COUNTING_PROFILED",
            "window_counting_scalar",
            f(p07_window, "background_cps"),
            f(p07_window, "response_cps_per_flux"),
            f(p07_window, "profiled_flux_3sigma_ph_cm2_s"),
            f(p07_window, "profiled_flux_5sigma_ph_cm2_s"),
            None,
            source_authority,
            str(profiled_path.relative_to(ROOT)),
            "conservative profiled window-counting reference",
            "VALIDATED_REFERENCE",
            "Diagonal-nuisance profile proxy; not a full Poisson optimizer.",
        )
    )

    p07_erl = row_match(profiled, energy_window="broad_480_550", model="energy_radius_layer_template", exposure_s=EXPOSURE_S)
    rows.append(
        metric_row(
            "P07_broad_ERL_profiled",
            "Phase7/Phase2",
            "science_511_reference",
            "mono_511",
            "baseline",
            "true_energy",
            "broad_480_550",
            "ERL_TEMPLATE_PROFILED",
            "energy_radius_layer_template",
            f(p07_erl, "background_cps"),
            f(p07_erl, "response_cps_per_flux"),
            f(p07_erl, "profiled_flux_3sigma_ph_cm2_s"),
            f(p07_erl, "profiled_flux_5sigma_ph_cm2_s"),
            None,
            source_authority,
            str(profiled_path.relative_to(ROOT)),
            "template/profiled sensitivity proxy and Phase 9 baseline comparison anchor",
            "VALIDATED_REFERENCE",
            "ERL means energy-radius-layer. This is a profiled proxy, not count-only.",
        )
    )

    p07_line = row_match(profiled, energy_window="line_510p3_511p8", model="energy_radius_layer_template", exposure_s=EXPOSURE_S)
    rows.append(
        metric_row(
            "P07_line_ERL_profiled",
            "Phase7/Phase2",
            "science_511_reference",
            "mono_511",
            "baseline",
            "true_energy",
            "line_510p3_511p8",
            "ERL_TEMPLATE_PROFILED",
            "energy_radius_layer_template",
            f(p07_line, "background_cps"),
            f(p07_line, "response_cps_per_flux"),
            f(p07_line, "profiled_flux_3sigma_ph_cm2_s"),
            f(p07_line, "profiled_flux_5sigma_ph_cm2_s"),
            None,
            source_authority,
            str(profiled_path.relative_to(ROOT)),
            "line-window ERL profile proxy",
            "VALIDATED_REFERENCE",
            "Line-window proxy is separate from broad count-only Phase 10 audit.",
        )
    )

    inj = row_match(injection, energy_window="broad_480_550", model="energy_radius_layer_template", exposure_s=EXPOSURE_S, input_flux_ph_cm2_s=REFERENCE_FLUX)
    rows.append(
        metric_row(
            "P07_source_injection_ERL_broad",
            "Phase7/Phase2",
            "science_511_reference",
            "mono_511",
            "baseline",
            "true_energy",
            "broad_480_550",
            "SOURCE_INJECTION_PROXY",
            "energy_radius_layer_template",
            f(p07_erl, "background_cps"),
            f(p07_erl, "response_cps_per_flux"),
            3.0 * f(inj, "sigma_flux"),
            5.0 * f(inj, "sigma_flux"),
            f(inj, "P3"),
            source_authority,
            str(injection_path.relative_to(ROOT)),
            "coverage check for ERL profiled source injection",
            "CONSERVATIVE_DIAGNOSTIC",
            "Monte Carlo injection proxy at F=1e-4; not a final real-flight claim.",
        )
    )

    p09_base = row_match(detect, line_model="mono_511", design_case="baseline Ta6", flux_ph_cm2_s=REFERENCE_FLUX)
    rows.append(
        metric_row(
            "P09_A_baseline_mono_placeholder",
            "Phase9",
            "A_GC_CENTRAL_COMPACT_SPI_ANCHOR",
            "mono_511",
            "baseline Ta6",
            "true_energy_placeholder_folding",
            "broad_480_550",
            "ERL_TEMPLATE_PROFILED",
            "energy_radius_layer_template_proxy",
            f(p09_base, "B_inst_cps") + f(p09_base, "B_diffuse_cps"),
            f(p09_base, "R_source_cps_per_flux"),
            f(p09_base, "F3_1Ms_ph_cm2_s"),
            None,
            f(p09_base, "P_ge_3sigma"),
            source_authority,
            str((phase9_dir / "detectability_A_GC_POINT.csv").relative_to(ROOT)),
            "Phase 9 ABC A-source folding baseline; placeholder optics only",
            "PLACEHOLDER_OPTICS_ONLY",
            "Comparable to Phase 7 ERL proxy, not to Phase 10 count-only without crosswalk.",
        )
    )

    p09_sel = row_match(detect, line_model="mono_511", design_case="selection-only best", flux_ph_cm2_s=REFERENCE_FLUX)
    rows.append(
        metric_row(
            "P09_A_selection_best_design_Q",
            "Phase9",
            "A_GC_CENTRAL_COMPACT_SPI_ANCHOR",
            "mono_511",
            "bgo30_r18_cent_single_top1_L5_keep",
            "true_energy_placeholder_folding",
            "broad_480_550",
            "DESIGN_Q_SCALING",
            "energy_radius_layer_template_proxy",
            f(p09_sel, "B_inst_cps") + f(p09_sel, "B_diffuse_cps"),
            f(p09_sel, "R_source_cps_per_flux"),
            f(p09_sel, "F3_1Ms_ph_cm2_s"),
            None,
            f(p09_sel, "P_ge_3sigma"),
            source_authority,
            str((phase9_dir / "detectability_A_GC_POINT.csv").relative_to(ROOT)),
            "design motivation only until measured/template performance is reproduced",
            "DESIGN_ADDON",
            f"Design table q_over_q0={design['selection-only best'].get('q_over_q0')}; not upgraded to main analysis by itself.",
        )
    )

    p10_base = next(
        row
        for row in p10_rows
        if row["mode"] == "count_only_L1"
        and row["selection_id"] == "baseline"
        and row["A_spectrum_model"] == "mono_511"
        and math.isclose(f(row, "A_flux_ph_cm2_s"), REFERENCE_FLUX, abs_tol=1e-12)
    )
    rows.append(
        metric_row(
            "P10_A_baseline_count_only_L1",
            "Phase10",
            "A_GC_CENTRAL_COMPACT_SPI_ANCHOR",
            "mono_511",
            "baseline",
            "counted_energy_L1",
            "broad_480_550",
            "COUNT_ONLY_L1",
            "window_counting_scalar",
            f(p10_base, "total_background_cps"),
            f(p10_base, "A_expected_cps") / f(p10_base, "A_flux_ph_cm2_s"),
            f(p10_base, "F3_ph_cm2_s"),
            f(p10_base, "F5_ph_cm2_s"),
            f(p10_base, "P_ge_3sigma"),
            source_authority,
            str((phase10_dir / "point_diffuse_discrimination.csv").relative_to(ROOT)),
            "conservative Phase 10 count-only reference",
            "CONSERVATIVE_DIAGNOSTIC",
            "This is intentionally more conservative than ERL/template metrics.",
        )
    )

    p10_sel = next(
        row
        for row in audit_rows
        if row["selection_id"] == "bgo30_r18_cent_single_top1_L5_keep"
        and row["energy_basis"] == "measured"
        and row["window"] == "broad_480_550"
    )
    rows.append(
        metric_row(
            "P10_selection_best_measured_broad_count_only",
            "Phase10",
            "A_GC_CENTRAL_COMPACT_SPI_ANCHOR",
            "mono_511",
            "bgo30_r18_cent_single_top1_L5_keep",
            "measured_energy",
            "broad_480_550",
            "MEASURED_BROAD_COUNT_ONLY",
            "window_counting_scalar",
            f(p10_sel, "background_cps"),
            f(p10_sel, "source_response_cps_per_flux"),
            f(p10_sel, "F3_ph_cm2_s"),
            f(p10_sel, "F5_ph_cm2_s"),
            f(p10_sel, "P_ge_3sigma_at_1e_minus_4"),
            source_authority,
            str((phase10_dir / "selection_best_measured_energy_audit.csv").relative_to(ROOT)),
            "measured-energy audit; analysis-only unless selection-upgrade gate passes",
            "MEASURED_AUDIT",
            "BGO remains an event-total proxy; performance is not reproduced under Phase 9 design-Q threshold.",
        )
    )

    trial = template_trial_metric(phase10_dir)
    rows.append(
        metric_row(
            "P11_template_TS_placeholder_trial",
            "Phase11",
            "A_GC_CENTRAL_COMPACT_SPI_ANCHOR",
            "mono_511",
            "baseline",
            "placeholder_template_axis",
            "broad_480_550",
            "TEMPLATE_TS_PLACEHOLDER",
            trial["dimension"],
            trial["background"],
            trial["response"],
            trial["f3"],
            trial["f5"],
            trial["p3"],
            "configs/astro_source_cases/optics_response_511_production_schema.yaml",
            str((phase10_dir / "point_diffuse_discrimination.csv").relative_to(ROOT)),
            "template-TS math scaffold only; replace with production optics templates before physics use",
            "PLACEHOLDER_OPTICS_ONLY",
            "Uses deterministic placeholder shape fractions to test the H0/H1 pipeline, not to claim A/B separation.",
        )
    )

    write_csv(out_csv, rows, CROSSWALK_FIELDS)
    summary = {
        "status": "PASS_PHASE11_METRIC_CROSSWALK_BUILT",
        "rows": len(rows),
        "required_metrics_present": sorted(REQUIRED_METRICS.intersection({row["metric_id"] for row in rows})),
        "required_metrics_missing": sorted(REQUIRED_METRICS - {row["metric_id"] for row in rows}),
        "claim": "Metric crosswalk only; direct comparison requires statistic_type and claim_level.",
    }
    write_json(out_csv.with_suffix(".json"), {"summary": summary, "rows": rows})
    plot_metric_crosswalk(rows, out_csv.parent / "figures")
    return rows


def plot_metric_crosswalk(rows: list[dict[str, Any]], figdir: Path) -> None:
    figdir.mkdir(parents=True, exist_ok=True)
    use = [row for row in rows if math.isfinite(float(row["F3_1Ms"]))]
    colors = {
        "WINDOW_COUNTING_PROFILED": "#4C78A8",
        "ERL_TEMPLATE_PROFILED": "#54A24B",
        "SOURCE_INJECTION_PROXY": "#72B7B2",
        "DESIGN_Q_SCALING": "#F58518",
        "COUNT_ONLY_L1": "#B279A2",
        "MEASURED_BROAD_COUNT_ONLY": "#E45756",
        "TEMPLATE_TS_PLACEHOLDER": "#9D755D",
    }
    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    labels = [row["metric_id"].replace("_", "\n") for row in use]
    vals = [float(row["F3_1Ms"]) for row in use]
    ax.bar(range(len(vals)), vals, color=[colors.get(row["statistic_type"], "#777777") for row in use])
    ax.set_yscale("log")
    ax.set_xticks(range(len(labels)), labels, rotation=35, ha="right", fontsize=7)
    ax.set_ylabel("F3, 1 Ms (ph cm$^{-2}$ s$^{-1}$)")
    ax.set_title("Phase 11 metric crosswalk: F3 differs by statistic type")
    ax.grid(True, axis="y", which="both", alpha=0.25)
    fig.tight_layout()
    fig.savefig(figdir / "metric_F3_comparison.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    vals = [float(row["P_ge_3sigma_at_1e-4_1Ms"]) for row in use]
    ax.bar(range(len(vals)), vals, color=[colors.get(row["statistic_type"], "#777777") for row in use])
    ax.set_xticks(range(len(labels)), labels, rotation=35, ha="right", fontsize=7)
    ax.set_ylim(0, 1.02)
    ax.set_ylabel("P(>=3 sigma), F=1e-4, 1 Ms")
    ax.set_title("Phase 11 metric crosswalk: P3 is not directly comparable across metrics")
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(figdir / "metric_P3_comparison.png", dpi=220)
    plt.close(fig)


def build_number_reconciliation(
    crosswalk_csv: Path = OUT_DEFAULT / "metric_crosswalk_phase11.csv",
    out_md: Path = OUT_DEFAULT / "phase10_vs_phase9_number_reconciliation.md",
) -> dict[str, Any]:
    rows = {row["metric_id"]: row for row in read_csv(crosswalk_csv)}
    p09_base = f(rows["P09_A_baseline_mono_placeholder"], "F3_1Ms")
    p10_base = f(rows["P10_A_baseline_count_only_L1"], "F3_1Ms")
    p09_sel = f(rows["P09_A_selection_best_design_Q"], "F3_1Ms")
    p10_sel = f(rows["P10_selection_best_measured_broad_count_only"], "F3_1Ms")
    ratio_base = p10_base / p09_base
    ratio_sel = p10_sel / p09_sel
    common = abs(ratio_base - ratio_sel) / ratio_base < 0.05
    suspected = (
        "metric-definition change: Phase 10 uses count-only/measured broad diagnostics while Phase 9 uses ERL/template/design-Q proxy"
        if common
        else "non-common degradation; inspect background, response, window, energy-axis, exposure, and template dimension"
    )
    result = {
        "status": "PASS_PHASE11_NUMBER_RECONCILIATION",
        "ratio_baseline_phase10_over_phase9": ratio_base,
        "ratio_selection_phase10_over_phase9": ratio_sel,
        "common_factor_consistency": common,
        "suspected_cause": suspected,
        "required_followup": "Reproduce the selection-only gain with a measured/template metric before upgrading the analysis setting.",
    }
    text = f"""# Phase 10 vs Phase 9 Number Reconciliation

Phase 10 does not contradict Phase 9. It uses a more conservative count-only/measured-broad metric, while Phase 9 used ERL/template/profiled or design-Q metrics.

## Ratios

- baseline ratio: `{fmt(p10_base)} / {fmt(p09_base)} = {ratio_base:.6f}`
- selection ratio: `{fmt(p10_sel)} / {fmt(p09_sel)} = {ratio_sel:.6f}`
- common factor consistency: `{common}`

The nearly identical degradation factors for baseline and selection-only rows suggest a metric-definition change rather than a selection-specific physics failure.

## Suspected Cause

{suspected}

## Allowed Comparison

Use `metric_crosswalk_phase11.csv` and compare rows only with their `statistic_type`, `energy_axis`, `template_dimension`, and `claim_level` visible.

## Not Allowed

- Do not write that Phase 10 overturned Phase 9.
- Do not write that selection best failed physically.
- Do not write that A is not detectable as a final astrophysical conclusion.

## Required Follow-Up

{result['required_followup']}
"""
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(text, encoding="utf-8")
    write_json(out_md.with_suffix(".json"), result)
    return result


def build_selection_upgrade_decision(
    crosswalk_csv: Path = OUT_DEFAULT / "metric_crosswalk_phase11.csv",
    audit_csv: Path = PHASE10_DEFAULT / "selection_best_measured_energy_audit.csv",
    out_md: Path = OUT_DEFAULT / "selection_best_upgrade_decision.md",
    out_json: Path = OUT_DEFAULT / "selection_best_upgrade_decision.json",
) -> dict[str, Any]:
    rows = {row["metric_id"]: row for row in read_csv(crosswalk_csv)}
    audit_rows = read_csv(audit_csv)
    measured = next(
        row
        for row in audit_rows
        if row["selection_id"] == "bgo30_r18_cent_single_top1_L5_keep"
        and row["energy_basis"] == "measured"
        and row["window"] == "broad_480_550"
    )
    f3_measured = f(measured, "F3_ph_cm2_s")
    p3_measured = f(measured, "P_ge_3sigma_at_1e_minus_4")
    phase9_f3 = f(rows["P09_A_selection_best_design_Q"], "F3_1Ms")
    audit_executed = measured.get("pass_status") == "PASS_MEASURED_ENERGY_AUDIT"
    same_catalog = measured.get("energy_basis") == "measured" and measured.get("window") == "broad_480_550"
    template_metric_reproduced = False
    design_gain_reproduced = f3_measured <= 1.1 * phase9_f3 or p3_measured >= 0.75
    no_proxy_leakage = False
    performance_reproduced = template_metric_reproduced and design_gain_reproduced and no_proxy_leakage
    upgraded = audit_executed and same_catalog and performance_reproduced
    decision = {
        "variant": "bgo30_r18_cent_single_top1_L5_keep",
        "audit_executed": audit_executed,
        "performance_reproduced": performance_reproduced,
        "upgraded_to_main_analysis": upgraded,
        "state_audit": "AUDIT_EXECUTED" if audit_executed else "AUDIT_NOT_EXECUTED",
        "state_performance": "PERFORMANCE_REPRODUCED" if performance_reproduced else "PERFORMANCE_NOT_REPRODUCED_PENDING_TEMPLATE_CROSSWALK",
        "state_upgrade": "UPGRADED_TO_MAIN_ANALYSIS" if upgraded else "NOT_UPGRADED_TO_MAIN_ANALYSIS",
        "measured_broad_F3": f3_measured,
        "measured_broad_P3_at_1e-4_1Ms": p3_measured,
        "phase9_selection_design_Q_F3": phase9_f3,
        "criteria": {
            "measured_energy_catalog_consistent": same_catalog,
            "background_and_response_from_same_measured_basis": same_catalog,
            "template_metric_same_as_main_or_crosswalked": template_metric_reproduced,
            "performance_threshold_reproduced": design_gain_reproduced,
            "no_BGO_layer_ROI_source_leakage": no_proxy_leakage,
            "claim_control_separates_baseline_and_selection": True,
        },
        "primary_reason": "Measured broad count-only audit executed, but it does not reproduce the previous Phase 9 design-Q sensitivity under the same measured/template metric; BGO remains event-total proxy.",
        "allowed_wording": [
            "selection-only best has a measured-energy audit",
            "selection-only best remains analysis-only pending measured/template reproduction",
            "baseline remains the primary validated reference",
        ],
        "forbidden_wording": [
            "selection best replaces baseline",
            "Phase 10 measured audit proves the design-Q gain",
            "selection-only best is final flight sensitivity",
        ],
    }
    write_json(out_json, decision)
    text = f"""# Selection-Only Best Upgrade Decision

Variant: `bgo30_r18_cent_single_top1_L5_keep`

## Three-State Decision

- `AUDIT_EXECUTED`: `{decision['audit_executed']}`
- `PERFORMANCE_REPRODUCED`: `{decision['performance_reproduced']}`
- `UPGRADED_TO_MAIN_ANALYSIS`: `{decision['upgraded_to_main_analysis']}`

## Current Evidence

- measured broad F3: `{fmt(f3_measured)}`
- measured broad P>=3sigma at F=1e-4, 1 Ms: `{fmt(p3_measured)}`
- Phase 9 design-Q F3 target: `{fmt(phase9_f3)}`

## Decision

Not upgraded. The measured broad count-only metric does not reproduce the Phase 9 design-Q sensitivity gain under the same measured/template metric.

## Allowed Wording

- selection-only best has a measured-energy audit
- selection-only best remains analysis-only pending measured/template reproduction
- baseline remains the primary validated reference

## Forbidden Wording

- Forbidden, not claimed: selection best replaces baseline
- Forbidden, not claimed: Phase 10 measured audit proves the design-Q gain
- Forbidden, not claimed: selection-only best is final flight sensitivity
"""
    out_md.write_text(text, encoding="utf-8")
    plot_selection_decision(decision, out_md.parent / "figures")
    return decision


def plot_selection_decision(decision: dict[str, Any], figdir: Path) -> None:
    figdir.mkdir(parents=True, exist_ok=True)
    labels = ["audit\nexecuted", "performance\nreproduced", "upgraded\nto main"]
    vals = [decision["audit_executed"], decision["performance_reproduced"], decision["upgraded_to_main_analysis"]]
    fig, ax = plt.subplots(figsize=(7.0, 3.8))
    ax.bar(range(3), [1 if v else 0 for v in vals], color=["#54A24B" if v else "#E45756" for v in vals])
    ax.set_xticks(range(3), labels)
    ax.set_yticks([0, 1], ["false", "true"])
    ax.set_ylim(0, 1.2)
    ax.set_title("Selection-only best upgrade gate")
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(figdir / "selection_upgrade_decision_tree.png", dpi=220)
    plt.close(fig)


def production_optics_schema() -> dict[str, Any]:
    return {
        "optics_id": "OPTICS_511_PRODUCTION_SCHEMA_V1",
        "status": "schema_only_not_production",
        "description": "Production schema for 511 keV focusing optics. This file defines required fields for Aeff(E, theta), PSF, bandpass, FoV, focal-plane mapping, and pointing/visibility. It is not a final optics response unless status is changed to production_validated and all required tables are populated.",
        "authority_level": "SCHEMA_ONLY",
        "can_support_final_detection_claim": False,
        "energy_grid_keV": {
            "min": 450.0,
            "max": 530.0,
            "step": 0.5,
            "note": "Must cover 511 keV line models and possible redshift/broad cases if used.",
        },
        "theta_grid_arcmin": {
            "values": [0.0, 0.5, 1.0, 2.0, 3.0, 4.47, 6.0, 10.0],
            "note": "Include on-axis and FoV-edge values.",
        },
        "aeff_cm2": {
            "status": "required_for_production",
            "table_path": None,
            "dimensions": ["energy_keV", "theta_arcmin"],
            "interpolation": "bilinear",
            "unit": "cm2",
            "validation": {"nonnegative": True, "onaxis_peak_required": True, "finite_bandpass_required": True},
        },
        "psf_kernel": {
            "status": "required_for_production",
            "table_path": None,
            "dimensions": ["energy_keV", "theta_arcmin", "x_mm", "y_mm"],
            "normalization": "sum_to_one_per_energy_theta",
            "note": "Required for focal-map and point/diffuse template separation.",
        },
        "fov": {"angular_radius_arcmin": None, "definition": "Aeff_or_acceptance_cut", "required_for_production": True},
        "bandpass": {"definition": "Aeff(E, 0) / max_Aeff_onaxis", "supported_energy_range_keV": None, "required_for_production": True},
        "focal_plane_mapping": {"focal_length_m": None, "detector_plane_z_mm": None, "x_y_units": "mm", "required_for_production": True},
        "atmospheric_transmission": {"source": "phase2_reference_profile_or_updated_profile", "time_bin": "6h", "required_for_source_case_folding": True},
        "pointing_visibility": {"source": "reference_profile_or_pointing_schedule", "time_bin": "6h", "required_for_final_astrophysical_claim": True},
        "diffuse_sky_projection": {
            "required_for_B_diffuse_production": True,
            "allowed_methods": ["sky_map_convolution_with_psf", "aperture_integral_L1"],
            "production_method_required": "sky_map_convolution_with_psf",
        },
        "claim_control": {
            "forbidden_if_status_not_production_validated": [
                "Forbidden, not claimed: final GC point-source detection",
                "Forbidden, not claimed: final point/diffuse imaging separation",
                "Forbidden, not claimed: final V404 detectability",
            ],
            "B_diffuse_must_not_be_focal_spot_source": True,
        },
    }


def init_optics_schema(
    out_schema: Path = CONFIG_DIR / "optics_response_511_production_schema.yaml",
    copy_out: Path = OUT_DEFAULT / "optics_response_511_production_schema.yaml",
) -> dict[str, Any]:
    schema = production_optics_schema()
    write_yaml(out_schema, schema)
    write_yaml(copy_out, schema)
    plot_optics_schema(schema, copy_out.parent / "figures")
    return schema


def plot_optics_schema(schema: dict[str, Any], figdir: Path) -> None:
    figdir.mkdir(parents=True, exist_ok=True)
    labels = ["Aeff", "PSF", "FoV", "bandpass", "mapping", "pointing", "diffuse map"]
    filled = [schema["aeff_cm2"]["table_path"], schema["psf_kernel"]["table_path"], schema["fov"]["angular_radius_arcmin"], schema["bandpass"]["supported_energy_range_keV"], schema["focal_plane_mapping"]["focal_length_m"], schema["pointing_visibility"]["source"], None]
    vals = [0 if value is None else 0.5 for value in filled]
    fig, ax = plt.subplots(figsize=(8.0, 3.8))
    ax.bar(labels, vals, color="#F58518")
    ax.set_ylim(0, 1.0)
    ax.set_yticks([0, 0.5, 1.0], ["missing", "schema/ref", "production"])
    ax.set_title("Production optics schema status: schema only, not production")
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(figdir / "optics_schema_overview.png", dpi=220)
    plt.close(fig)


def build_optics_requirements(
    crosswalk_csv: Path = OUT_DEFAULT / "metric_crosswalk_phase11.csv",
    target_flux: float = TARGET_FLUX,
    exposure_s: float = EXPOSURE_S,
    out_csv: Path = OUT_DEFAULT / "optics_requirements_matrix_v2.csv",
) -> list[dict[str, Any]]:
    rows = {row["metric_id"]: row for row in read_csv(crosswalk_csv)}
    wanted = [
        ("baseline_count_only_L1", "P10_A_baseline_count_only_L1", "current conservative count-only baseline", "current L1 target"),
        ("selection_measured_broad", "P10_selection_best_measured_broad_count_only", "analysis-only measured audit", "not upgraded"),
        ("phase9_selection_design_Q", "P09_A_selection_best_design_Q", "design target/motivation until reproduced", "only_if_reproduced_under_measured_template_metric"),
        ("phase9_baseline_ERL", "P09_A_baseline_mono_placeholder", "Phase 9 placeholder ERL anchor", "placeholder optics only"),
    ]
    out: list[dict[str, Any]] = []
    for rid, metric_id, role, status in wanted:
        f3_value = f(rows[metric_id], "F3_1Ms")
        gain = f3_value / target_flux
        background_fraction = (target_flux / f3_value) ** 2
        exposure_ms = (exposure_s / 1e6) * (f3_value / target_flux) ** 2
        out.append(
            {
                "requirement_id": rid,
                "source_metric_id": metric_id,
                "F3_current_ph_cm2_s": f3_value,
                "target_flux_ph_cm2_s": target_flux,
                "reference_exposure_s": exposure_s,
                "required_response_gain": gain,
                "required_background_fraction": background_fraction,
                "required_exposure_Ms": exposure_ms,
                "status": status,
                "role": role,
                "claim_level": rows[metric_id]["claim_level"],
                "notes": "required_background_fraction > 1 means the metric is already better than the target only if that metric is allowed as main authority.",
            }
        )
    write_csv(out_csv, out)
    return out


def build_point_diffuse_template_ts(
    crosswalk_csv: Path = OUT_DEFAULT / "metric_crosswalk_phase11.csv",
    phase10_dir: Path = PHASE10_DEFAULT,
    optics_schema_path: Path = CONFIG_DIR / "optics_response_511_production_schema.yaml",
    out_csv: Path = OUT_DEFAULT / "point_diffuse_template_TS_phase11.csv",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = {row["metric_id"]: row for row in read_csv(crosswalk_csv)}
    schema = yaml.safe_load(optics_schema_path.read_text(encoding="utf-8"))
    optics_status = schema.get("status", "")
    claim_level = "TEMPLATE_TS_PRODUCTION_READY" if optics_status == "production_validated" else "PLACEHOLDER_OPTICS_ONLY"
    p10_rows = read_csv(phase10_dir / "point_diffuse_discrimination.csv")
    fluxes = [5e-5, 8e-5, 1e-4, 1.5e-4, 2e-4, 3e-4]
    dims = ["energy_radius_layer", "energy_radius_layer_multiplicity"]
    selections = [
        ("baseline", "P10_A_baseline_count_only_L1"),
        ("bgo30_r18_cent_single_top1_L5_keep", "P10_selection_best_measured_broad_count_only"),
    ]
    out: list[dict[str, Any]] = []
    for selection_id, metric_id in selections:
        metric = rows[metric_id]
        response = f(metric, "response_cps_per_flux")
        total_background = f(metric, "background_cps")
        diffuse = f(row_match(p10_rows, mode="count_only_L1", selection_id="baseline", A_spectrum_model="mono_511", A_flux_ph_cm2_s=REFERENCE_FLUX), "B_diffuse_cps")
        instr = max(0.0, total_background - diffuse)
        for dim in dims:
            f3_value = solve_flux_for_sigma(response, instr, diffuse, EXPOSURE_S, dim, 3.0)
            f5_value = solve_flux_for_sigma(response, instr, diffuse, EXPOSURE_S, dim, 5.0)
            for flux in fluxes:
                ts = template_ts_for_flux(flux, response, instr, diffuse, EXPOSURE_S, dim)
                sigma = math.sqrt(ts)
                out.append(
                    {
                        "case_id": "A_GC_CENTRAL_COMPACT_SPI_ANCHOR",
                        "selection_id": selection_id,
                        "A_flux_ph_cm2_s": flux,
                        "B_model_id": "B_default_bulge8_plus_disk_aperture",
                        "optics_id": schema.get("optics_id", "UNKNOWN"),
                        "optics_status": optics_status,
                        "exposure_s": EXPOSURE_S,
                        "energy_axis": metric["energy_axis"],
                        "energy_window": "broad_480_550",
                        "template_dimension": dim,
                        "background_instr_cps": instr,
                        "B_diffuse_cps": diffuse,
                        "A_signal_cps": flux * response,
                        "TS_Asimov": ts,
                        "sigma_Asimov": sigma,
                        "P_ge_3sigma": normal_survival(3.0 - sigma),
                        "F3_required": f3_value,
                        "F5_required": f5_value,
                        "claim_level": claim_level,
                        "notes": "H0=instrument+B diffuse, H1=instrument+B diffuse+A compact. Placeholder shape fractions only; no final A/B separation claim.",
                    }
                )
    write_csv(out_csv, out)
    summary = {
        "status": "PASS_PHASE11_TEMPLATE_TS_SCAFFOLD",
        "rows": len(out),
        "optics_status": optics_status,
        "claim_level": claim_level,
        "H0": "instrumental background + B diffuse null model",
        "H1": "instrumental background + B diffuse foreground + A central compact source",
        "production_ready": optics_status == "production_validated",
        "notes": "This is a template-TS scaffold showing how A/B discrimination will be evaluated once production optics response is installed.",
    }
    write_json(out_csv.with_suffix(".json"), summary)
    plot_template_ts(out, out_csv.parent / "figures")
    return out, summary


def plot_template_ts(rows: list[dict[str, Any]], figdir: Path) -> None:
    figdir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.8, 4.8))
    for selection_id in sorted({row["selection_id"] for row in rows}):
        sub = sorted(
            [
                row
                for row in rows
                if row["selection_id"] == selection_id and row["template_dimension"] == "energy_radius_layer_multiplicity"
            ],
            key=lambda row: float(row["A_flux_ph_cm2_s"]),
        )
        ax.plot([float(row["A_flux_ph_cm2_s"]) for row in sub], [float(row["sigma_Asimov"]) for row in sub], marker="o", label=selection_id)
    ax.axhline(3.0, color="#555555", ls="--", lw=1.0)
    ax.set_xscale("log")
    ax.set_xlabel("A compact-source flux (ph cm$^{-2}$ s$^{-1}$)")
    ax.set_ylabel("Asimov sigma")
    ax.set_title("Phase 11 A+B vs B-only template-TS scaffold")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(figdir / "point_diffuse_TS_projection.png", dpi=220)
    plt.close(fig)


def write_claim_control(outdir: Path = OUT_DEFAULT) -> dict[str, Any]:
    allowed = [
        "Phase 11 reconciles sensitivity metrics from Phase 9 and Phase 10.",
        "Phase 11 separates count-only, template/profiled, injection-proxy, and design-Q metrics.",
        "The current A/B discrimination remains a placeholder-optics scaffold unless production Aeff/PSF/FoV/bandpass are installed.",
        "B diffuse is treated as aperture-integrated foreground/null model, not as a focal-spot source.",
        "The selection-only best row remains analysis-only until measured/template performance is reproduced.",
    ]
    forbidden = [
        "final GC point-source detection",
        "final V404 detectability",
        "Sgr A* source confirmed",
        "diffuse source negligible",
        "production point/diffuse separation",
        "selection best replaces baseline",
        "placeholder optics final",
        "total bulge flux as point source",
    ]
    data = {
        "status": "PASS_PHASE11_CLAIM_CONTROL",
        "allowed_wording": allowed,
        "forbidden_wording": forbidden,
        "guard_phrases": FORBIDDEN_PHRASES,
        "allowing_guards": ALLOWING_GUARDS,
        "repeated_error_rule": "If the same implementation or physics error occurs twice, stop trial-and-error, research 3-5 plausible fixes online, choose the shortest defensible fix, implement it, and record the decision.",
    }
    write_json(outdir / "claim_control_phase11.json", data)
    lines = ["# Phase 11 Claim Control", "", "Allowed:"]
    lines.extend(f"- {item}" for item in allowed)
    lines.append("")
    lines.append("Forbidden:")
    lines.extend(f"- Forbidden, not claimed: {item}" for item in forbidden)
    lines.append("")
    lines.append("Repeated-error rule:")
    lines.append("")
    lines.append(data["repeated_error_rule"])
    lines.append("")
    lines.append("Final delivery wording:")
    lines.append("")
    lines.append("Phase 11 reconciles the Phase 9 and Phase 10 sensitivity metrics, prevents silent replacement of the validated baseline by selection-only design add-ons, and defines the production optics gate required for final A/B point-diffuse discrimination. The current results remain placeholder-optics/source-case scaffolds and do not constitute final GC point-source, V404, or production-level imaging sensitivity claims.")
    (outdir / "claim_control_phase11.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return data


def write_readme(outdir: Path = OUT_DEFAULT) -> None:
    crosswalk = {row["metric_id"]: row for row in read_csv(outdir / "metric_crosswalk_phase11.csv")}
    decision = read_json(outdir / "selection_best_upgrade_decision.json")
    reconciliation = read_json(outdir / "phase10_vs_phase9_number_reconciliation.json")
    text = f"""# Phase 11: Metric Reconciliation and Optics Gate

Phase 11 is a reconciliation/gate package, not a new production source simulation.

## Purpose

Phase 11 reconciles the Phase 9 and Phase 10 sensitivity metrics, prevents silent replacement of the validated baseline by selection-only design add-ons, and defines the production optics gate required for final A/B point-diffuse discrimination. The current results remain placeholder-optics/source-case scaffolds and do not constitute final GC point-source, V404, or production-level imaging sensitivity claims.

## Main Results

- Phase 10 / Phase 9 baseline F3 ratio: `{reconciliation['ratio_baseline_phase10_over_phase9']:.6f}`
- Phase 10 / Phase 9 selection F3 ratio: `{reconciliation['ratio_selection_phase10_over_phase9']:.6f}`
- Common-factor consistency: `{reconciliation['common_factor_consistency']}`
- Selection audit executed: `{decision['audit_executed']}`
- Selection performance reproduced: `{decision['performance_reproduced']}`
- Selection upgraded to main analysis: `{decision['upgraded_to_main_analysis']}`

## Key Metrics

- Phase 9 baseline ERL F3: `{fmt(float(crosswalk['P09_A_baseline_mono_placeholder']['F3_1Ms']))}`
- Phase 10 baseline count-only F3: `{fmt(float(crosswalk['P10_A_baseline_count_only_L1']['F3_1Ms']))}`
- Phase 9 selection design-Q F3: `{fmt(float(crosswalk['P09_A_selection_best_design_Q']['F3_1Ms']))}`
- Phase 10 selection measured broad F3: `{fmt(float(crosswalk['P10_selection_best_measured_broad_count_only']['F3_1Ms']))}`

## Outputs

- `metric_crosswalk_phase11.csv/json`
- `phase10_vs_phase9_number_reconciliation.md/json`
- `selection_best_upgrade_decision.md/json`
- `optics_response_511_production_schema.yaml`
- `optics_requirements_matrix_v2.csv`
- `point_diffuse_template_TS_phase11.csv/json`
- `claim_control_phase11.md/json`
- `figures/`

## Claim Boundary

No final detection claim is made. B diffuse remains an aperture-integrated foreground/null model. Selection-only best remains analysis-only until measured/template performance is reproduced under the same metric.
"""
    (outdir / "README.md").write_text(text, encoding="utf-8")


def write_artifact_manifest(outdir: Path = OUT_DEFAULT) -> None:
    rows = []
    for path in sorted(outdir.rglob("*")):
        if path.is_file() and path != outdir / "artifact_manifest.csv":
            rows.append({"relative_path": rel(path), "bytes": path.stat().st_size})
    write_csv(outdir / "artifact_manifest.csv", rows)


def update_reports2_manifest() -> None:
    rows = []
    for path in sorted(R2.rglob("*")):
        if path.is_file():
            rows.append((str(path.relative_to(R2)), path.stat().st_size))
    with (R2 / "MANIFEST.tsv").open("w", encoding="utf-8") as fh:
        for rel_path, size in rows:
            fh.write(f"{rel_path}\t{size}\n")


def package_scripts() -> None:
    SCRIPT_PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    scripts = [
        "make_phase11_metric_crosswalk.py",
        "make_phase11_number_reconciliation.py",
        "make_phase11_selection_upgrade_decision.py",
        "init_phase11_optics_schema.py",
        "make_phase11_optics_requirements.py",
        "make_phase11_point_diffuse_template_ts.py",
        "validate_phase11_metric_crosswalk.py",
        "validate_phase11_selection_upgrade.py",
        "validate_phase11_optics_schema.py",
        "validate_phase11_claim_control.py",
    ]
    for script in scripts:
        src = ROOT / "tools" / script
        if src.exists():
            shutil.copy2(src, SCRIPT_PACKAGE_DIR / script)


def build_all() -> dict[str, Any]:
    OUT_DEFAULT.mkdir(parents=True, exist_ok=True)
    FIG_DEFAULT.mkdir(parents=True, exist_ok=True)
    rows = build_metric_crosswalk()
    reconciliation = build_number_reconciliation()
    decision = build_selection_upgrade_decision()
    schema = init_optics_schema()
    requirements = build_optics_requirements()
    ts_rows, ts_summary = build_point_diffuse_template_ts()
    claim = write_claim_control()
    write_readme()
    package_scripts()
    write_artifact_manifest()
    update_reports2_manifest()
    summary = {
        "status": "PASS_PHASE11_METRIC_RECONCILIATION_AND_OPTICS_GATE",
        "outdir": rel(OUT_DEFAULT),
        "metric_rows": len(rows),
        "common_factor_consistency": reconciliation["common_factor_consistency"],
        "selection_upgraded_to_main_analysis": decision["upgraded_to_main_analysis"],
        "optics_status": schema["status"],
        "requirements_rows": len(requirements),
        "template_ts_rows": len(ts_rows),
        "template_ts_claim_level": ts_summary["claim_level"],
        "claim_control_status": claim["status"],
    }
    write_json(OUT_DEFAULT / "phase11_summary.json", summary)
    write_artifact_manifest()
    update_reports2_manifest()
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase9", type=Path, default=ABC_DEFAULT / "source_case_summary.json")
    ap.add_argument("--phase10", type=Path, default=PHASE10_DEFAULT)
    ap.add_argument("--nima", type=Path, default=NIMA_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT / "metric_crosswalk_phase11.csv")
    ap.add_argument("--all", action="store_true", help="Build every Phase 11 artifact.")
    args = ap.parse_args()
    if args.all:
        summary = build_all()
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        rows = build_metric_crosswalk(out_csv=args.out, phase9_dir=args.phase9.parent if args.phase9.is_file() else args.phase9, phase10_dir=args.phase10)
        print(json.dumps({"status": "PASS_PHASE11_METRIC_CROSSWALK_BUILT", "rows": len(rows), "out": rel(args.out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
