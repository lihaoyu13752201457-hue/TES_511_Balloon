#!/usr/bin/env python3
"""Build the full bilingual NIMA manuscript package for COSMOSRAY_BG_260516.

The first 260516 draft was intentionally discarded because it was only a short
summary.  This generator rebuilds the package as a paper project: it reuses the
long 2605 NIMA manuscript backbone, updates the authority to the 260516
workspace, and integrates the 260516 SPI source/time update, Phase12 closure,
first-principles optics requirement input, validation, and claim-control gates.
"""

from __future__ import annotations

import csv
import html
import json
import math
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports_260516" / "nima_paper"
SOURCE_TIME = ROOT / "reports_260516" / "source_time_update"
R2 = ROOT / "reports2.0"
PHASE2 = ROOT / "reports" / "phase2_real_flight_physical_production"


CSS = """
body { font-family: "Noto Serif CJK SC", "Source Han Serif SC", "DejaVu Serif", serif; color: #1d1d1d; line-height: 1.62; max-width: 1120px; margin: 0 auto; padding: 34px 46px 76px; background: #f7f7f5; }
article { background: #fff; padding: 44px 58px; box-shadow: 0 3px 18px rgba(0,0,0,.08); }
h1 { font-size: 29px; line-height: 1.25; margin-bottom: 12px; }
h2 { margin-top: 34px; border-bottom: 2px solid #222; padding-bottom: 6px; font-size: 21px; }
h3 { margin-top: 24px; font-size: 17px; }
p { margin: 11px 0; }
table { width: 100%; border-collapse: collapse; margin: 16px 0 24px; font-size: 12.2px; }
th, td { border: 1px solid #cfcfcf; padding: 6px 8px; vertical-align: top; }
th { background: #edf0f4; }
code { font-family: "DejaVu Sans Mono", Consolas, monospace; }
pre { background: #f4f4f4; padding: 12px; overflow-x: auto; }
figure { margin: 22px 0 28px; break-inside: avoid; }
img { max-width: 100%; display: block; margin: 0 auto; border: 1px solid #ddd; background: white; }
figcaption { font-size: 12.5px; color: #444; margin-top: 8px; }
.equation { text-align: center; font-family: "DejaVu Sans", serif; background: #fafafa; border: 1px solid #e4e4e4; padding: 10px; margin: 14px 0; white-space: pre-wrap; }
@media print { body { background: white; padding: 0; } article { box-shadow: none; padding: 0; } h2 { break-before: page; } figure, table { break-inside: avoid; } }
"""


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def f(row: dict[str, str], key: str, default: float = float("nan")) -> float:
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def fmt(x: float, nd: int = 4) -> str:
    if math.isnan(x):
        return "nan"
    if math.isinf(x):
        return "inf"
    if x == 0:
        return "0"
    if abs(x) < 1.0e-3 or abs(x) >= 1.0e5:
        return f"{x:.{nd}e}"
    return f"{x:.{nd}g}"


def load_values() -> dict[str, Any]:
    source_summary = json.loads((SOURCE_TIME / "source_time_update_summary.json").read_text(encoding="utf-8"))
    metric = json.loads((R2 / "12_FINAL_COMPACT_SOURCE_ANALYSIS" / "metric_closure_final.json").read_text(encoding="utf-8"))
    phase12 = json.loads((R2 / "12_FINAL_COMPACT_SOURCE_ANALYSIS" / "phase12_summary.json").read_text(encoding="utf-8"))
    optics = json.loads((R2 / "12_FINAL_COMPACT_SOURCE_ANALYSIS" / "optics_model_status_final.json").read_text(encoding="utf-8"))
    selection = json.loads((R2 / "12_FINAL_COMPACT_SOURCE_ANALYSIS" / "selection_upgrade_decision_final.json").read_text(encoding="utf-8"))
    fp = json.loads((R2 / "12_FINAL_COMPACT_SOURCE_ANALYSIS" / "first_principles_channeling_optics" / "first_principles_optics_coupling_summary.json").read_text(encoding="utf-8"))
    workspace_validation = json.loads((ROOT / "reports" / "workspace_validation.json").read_text(encoding="utf-8"))

    literature = read_csv(SOURCE_TIME / "literature_anchor_summary.csv")
    diffuse = read_csv(SOURCE_TIME / "spi_diffuse_detectability.csv")
    point = read_csv(SOURCE_TIME / "point_source_flux_scan.csv")
    transient = read_csv(SOURCE_TIME / "transient_point_benchmarks.csv")
    time_point = read_csv(SOURCE_TIME / "time_dependent_point_source_scan.csv")
    time_v404 = read_csv(SOURCE_TIME / "time_dependent_v404_benchmarks.csv")
    bg_time = read_csv(SOURCE_TIME / "background_time_variation.csv")
    measured = read_csv(PHASE2 / "event_catalog_v2_measured" / "true_vs_measured_rates.csv")
    likelihood = read_csv(PHASE2 / "likelihood_profiled" / "asimov_profiled_sensitivity.csv")
    injection = read_csv(PHASE2 / "long_timeline_injection_profiled" / "source_injection_profiled_summary.csv")

    def one(rows: list[dict[str, str]], **criteria: str) -> dict[str, str]:
        hits = [r for r in rows if all(r.get(k) == v for k, v in criteria.items())]
        if not hits:
            raise RuntimeError(f"no row for {criteria}")
        return hits[0]

    default_diffuse_param = one(diffuse, case_id="B_default_bulge8deg_plus_disk", response_id="parametric_CAM511_normalized")
    default_diffuse_fp = one(diffuse, case_id="B_default_bulge8deg_plus_disk", response_id="firstprinciples_L2_scalar_rescale")
    gcs_param = one(point, source_family="SPI_GCS_POINTLIKE_ANCHOR", response_id="parametric_CAM511_normalized_phase12_primary")
    gcs_fp = one(point, source_family="SPI_GCS_POINTLIKE_ANCHOR", response_id="firstprinciples_L2_scalar_rescale_requirement_input")

    generic_param = [
        r for r in point
        if r["source_family"] == "generic_point_source_flux_scan"
        and r["response_id"] == "parametric_CAM511_normalized_phase12_primary"
        and r["flux_ph_cm2_s"] in {"1e-05", "3e-05", "0.0001", "0.0003", "0.001"}
    ]
    generic_fp = [
        r for r in point
        if r["source_family"] == "generic_point_source_flux_scan"
        and r["response_id"] == "firstprinciples_L2_scalar_rescale_requirement_input"
        and r["flux_ph_cm2_s"] in {"1e-05", "3e-05", "0.0001", "0.0003", "0.001"}
    ]

    def measured_rate(window: str) -> dict[str, str]:
        return one(measured, window=window, energy_type="measured")

    def profiled(window: str, model: str) -> dict[str, str]:
        rows = [
            r for r in likelihood
            if r["energy_window"] == window
            and r["model"] == model
            and abs(f(r, "exposure_s") - 1.0e6) < 1.0
        ]
        if not rows:
            raise RuntimeError(f"missing profiled {window} {model}")
        return rows[0]

    def inj(window: str, model: str) -> dict[str, str]:
        rows = [
            r for r in injection
            if r["energy_window"] == window
            and r["model"] == model
            and abs(f(r, "exposure_s") - 1.0e6) < 1.0
            and abs(f(r, "input_flux_ph_cm2_s") - 1.0e-4) < 1.0e-12
        ]
        if not rows:
            raise RuntimeError(f"missing injection {window} {model}")
        return rows[0]

    def ranges(window: str) -> dict[str, tuple[float, float]]:
        sub = [r for r in bg_time if r["window"] == window]
        keys = [
            "altitude_km", "latitude_deg", "longitude_deg", "depth_g_cm2", "activation_driver",
            "total_delayed_activity_Bq", "prompt_final_cps", "delayed_final_cps_level1",
            "total_background_final_cps_level1",
        ]
        return {key: (min(f(r, key) for r in sub), max(f(r, key) for r in sub)) for key in keys}

    primary_metric = [r for r in metric["rows"] if r["metric_id"] == "phase12_baseline_measured_ERL"][0]
    selection_metric = [r for r in metric["rows"] if r["metric_id"] == "phase12_selection_best_measured_ERL"][0]
    warnings = [r for r in workspace_validation if r.get("status") == "WARN"]
    failures = [r for r in workspace_validation if r.get("status") == "FAIL"]

    return {
        "source_summary": source_summary,
        "authority": source_summary["authority"],
        "metric": metric,
        "phase12": phase12,
        "optics": optics,
        "selection": selection,
        "fp": fp,
        "literature": literature,
        "diffuse": diffuse,
        "point": point,
        "transient": transient,
        "time_point": time_point,
        "time_v404": time_v404,
        "bg_time": bg_time,
        "default_diffuse_param": default_diffuse_param,
        "default_diffuse_fp": default_diffuse_fp,
        "gcs_param": gcs_param,
        "gcs_fp": gcs_fp,
        "generic_param": generic_param,
        "generic_fp": generic_fp,
        "measured_broad": measured_rate("broad_480_550"),
        "measured_line": measured_rate("line_510p3_511p8"),
        "broad_window": profiled("broad_480_550", "window_counting_same_events"),
        "broad_erl": profiled("broad_480_550", "energy_radius_layer_template"),
        "line_erl": profiled("line_510p3_511p8", "energy_radius_layer_template"),
        "inj_broad_erl": inj("broad_480_550", "energy_radius_layer_template"),
        "inj_line_erl": inj("line_510p3_511p8", "energy_radius_layer_template"),
        "primary_metric": primary_metric,
        "selection_metric": selection_metric,
        "broad_ranges": ranges("broad_480_550"),
        "line_ranges": ranges("line_510p3_511p8"),
        "validation_warnings": warnings,
        "validation_failures": failures,
    }


def markdown_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]], float_cols: set[str] | None = None) -> str:
    float_cols = float_cols or set()
    out = ["| " + " | ".join(title for _, title in columns) + " |", "|" + "|".join("---:" if key in float_cols else "---" for key, _ in columns) + "|"]
    for row in rows:
        cells = []
        for key, _ in columns:
            val = row.get(key, "")
            if isinstance(val, float):
                cells.append(fmt(val))
            else:
                cells.append(str(val))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def source_anchor_table(v: dict[str, Any]) -> str:
    rows = [
        {
            "anchor": r["anchor_id"],
            "class": r["source_class"],
            "value": r["value_ph_cm2_s"] or "spectrum/benchmark",
            "use": r["use_in_update"],
            "claim": r["claim_note"],
        }
        for r in v["literature"]
    ]
    return markdown_table(rows, [("anchor", "anchor"), ("class", "source class"), ("value", "flux / value"), ("use", "use"), ("claim", "claim note")])


def source_case_table(v: dict[str, Any]) -> str:
    rows = [
        {
            "case": "SPI diffuse B default",
            "response": "parametric",
            "flux": v["default_diffuse_param"]["total_flux_ph_cm2_s"],
            "fov_flux": fmt(f(v["default_diffuse_param"], "fov_flux_ph_cm2_s")),
            "signal": fmt(f(v["default_diffuse_param"], "signal_cps")),
            "t3": f"{fmt(f(v['default_diffuse_param'], 'T3_years'))} yr",
            "claim": "aperture foreground, not focal source",
        },
        {
            "case": "SPI diffuse B default",
            "response": "FP L2 scalar",
            "flux": v["default_diffuse_fp"]["total_flux_ph_cm2_s"],
            "fov_flux": fmt(f(v["default_diffuse_fp"], "fov_flux_ph_cm2_s")),
            "signal": fmt(f(v["default_diffuse_fp"], "signal_cps")),
            "t3": f"{fmt(f(v['default_diffuse_fp'], 'T3_years'))} yr",
            "claim": "requirement input only",
        },
        {
            "case": "SPI central compact anchor",
            "response": "parametric",
            "flux": v["gcs_param"]["flux_ph_cm2_s"],
            "fov_flux": "point source",
            "signal": fmt(f(v["gcs_param"], "signal_cps")),
            "t3": f"{fmt(f(v['gcs_param'], 'T3_days_Asimov'))} d",
            "claim": "model component, not confirmed identity",
        },
        {
            "case": "SPI central compact anchor",
            "response": "FP L2 scalar",
            "flux": v["gcs_fp"]["flux_ph_cm2_s"],
            "fov_flux": "point source",
            "signal": fmt(f(v["gcs_fp"], "signal_cps")),
            "t3": f"{fmt(f(v['gcs_fp'], 'T3_days_Asimov'))} d",
            "claim": "requirement input only",
        },
    ]
    return markdown_table(rows, [("case", "case"), ("response", "response"), ("flux", "total/input flux"), ("fov_flux", "FoV flux"), ("signal", "signal cps"), ("t3", "3 sigma exposure"), ("claim", "claim level")])


def flux_scan_table(v: dict[str, Any]) -> str:
    rows = []
    for r in v["generic_param"]:
        rows.append(
            {
                "flux": r["flux_ph_cm2_s"],
                "signal": fmt(f(r, "signal_cps")),
                "p3": fmt(f(r, "P_ge_3sigma_at_1Ms")),
                "t3": f"{fmt(f(r, 'T3_days_Asimov'))} d",
                "response": "parametric",
            }
        )
    for r in v["generic_fp"]:
        if r["flux_ph_cm2_s"] in {"0.0001", "0.0003"}:
            rows.append(
                {
                    "flux": r["flux_ph_cm2_s"],
                    "signal": fmt(f(r, "signal_cps")),
                    "p3": fmt(f(r, "P_ge_3sigma_at_1Ms")),
                    "t3": f"{fmt(f(r, 'T3_days_Asimov'))} d",
                    "response": "FP L2 scalar",
                }
            )
    return markdown_table(rows, [("response", "response"), ("flux", "flux ph cm^-2 s^-1"), ("signal", "signal cps"), ("p3", "P>=3 sigma at 1 Ms"), ("t3", "Asimov T3")])


def v404_benchmark_table(v: dict[str, Any]) -> str:
    wanted = {
        ("v404_kT30_no_shift", "0.0001"),
        ("v404_kT30_no_shift", "0.001"),
        ("v404_kT30_no_shift", "0.003"),
        ("v404_redshift_z0p10_narrow_proxy", "0.001"),
        ("v404_redshift_z0p10_narrow_proxy", "0.003"),
    }
    rows = []
    for r in v["transient"]:
        if float(r["exposure_s"]) != 86400.0:
            continue
        key = (r["spectrum"], r["input_flux_ph_cm2_s"])
        if key not in wanted:
            continue
        rows.append(
            {
                "spectrum": r["spectrum"],
                "flux": r["input_flux_ph_cm2_s"],
                "aeff": fmt(f(r, "aeff_weighted_fraction")),
                "effective": fmt(f(r, "effective_flux_ph_cm2_s")),
                "sigma_1d": fmt(f(r, "expected_sigma_parametric")),
                "t3": f"{fmt(f(r, 'T3_days_parametric'))} d",
            }
        )
    return markdown_table(rows, [("spectrum", "spectrum"), ("flux", "input flux"), ("aeff", "Aeff fraction"), ("effective", "effective flux"), ("sigma_1d", "1-day sigma"), ("t3", "Asimov T3")])


def time_dependent_point_table(v: dict[str, Any]) -> str:
    wanted = {5e-5, 8e-5, 1e-4, 1.5e-4, 2e-4, 3e-4}
    rows = []
    for r in v["time_point"]:
        if r.get("response_id") != "parametric_CAM511_normalized_phase12_primary":
            continue
        flux = f(r, "input_flux_ph_cm2_s")
        if flux not in wanted:
            continue
        cross = r["T3_days_metric_crossing"] or "not within 20 d"
        rows.append(
            {
                "flux": r["input_flux_ph_cm2_s"],
                "z20": fmt(f(r, "final_Z_metric_scaled")),
                "cross": fmt(float(cross)) + " d" if cross != "not within 20 d" else cross,
                "avg": f"{fmt(f(r, 'T3_days_metric_avg_extrapolated'))} d",
            }
        )
    return markdown_table(rows, [("flux", "flux ph cm^-2 s^-1"), ("z20", "Z at 20 d"), ("cross", "3 sigma crossing"), ("avg", "average extrapolated T3")])


def time_dependent_v404_table(v: dict[str, Any]) -> str:
    wanted = {
        ("v404_kT30_no_shift", 1e-4),
        ("v404_kT30_no_shift", 1e-3),
        ("v404_redshift_z0p10_narrow_proxy", 3e-3),
    }
    rows = []
    for r in v["time_v404"]:
        key = (r["spectrum"], f(r, "input_flux_ph_cm2_s"))
        if key not in wanted:
            continue
        cross = r["T3_days_metric_crossing"] or "not within 20 d"
        rows.append(
            {
                "spectrum": r["spectrum"],
                "flux": r["input_flux_ph_cm2_s"],
                "z20": fmt(f(r, "final_Z_metric_scaled")),
                "cross": fmt(float(cross)) + " d" if cross != "not within 20 d" else cross,
            }
        )
    return markdown_table(rows, [("spectrum", "spectrum"), ("flux", "input flux"), ("z20", "Z at 20 d"), ("cross", "3 sigma crossing")])


def time_range_table(v: dict[str, Any]) -> str:
    rows = []
    labels = {
        "altitude_km": "altitude km",
        "latitude_deg": "latitude deg",
        "longitude_deg": "longitude deg",
        "depth_g_cm2": "atmospheric depth g cm^-2",
        "activation_driver": "activation driver",
        "total_delayed_activity_Bq": "total delayed activity Bq",
        "prompt_final_cps": "prompt final cps",
        "delayed_final_cps_level1": "delayed Level-1 cps",
        "total_background_final_cps_level1": "total final cps",
    }
    for key, label in labels.items():
        bmin, bmax = v["broad_ranges"][key]
        lmin, lmax = v["line_ranges"][key]
        rows.append({"quantity": label, "broad": f"{fmt(bmin)}-{fmt(bmax)}", "line": f"{fmt(lmin)}-{fmt(lmax)}"})
    return markdown_table(rows, [("quantity", "quantity"), ("broad", "480-550 keV"), ("line", "510.3-511.8 keV")])


def metric_table(v: dict[str, Any]) -> str:
    rows = []
    for r in v["metric"]["rows"]:
        rows.append(
            {
                "metric": r["metric_id"],
                "feature": r["feature_space"],
                "selection": r["selection_id"],
                "bg": fmt(float(r["background_cps"])),
                "F3": fmt(float(r["F3_1Ms"])),
                "P3": fmt(float(r["P_ge_3sigma_at_1e-4_1Ms"])),
                "claim": r["claim_level"],
            }
        )
    return markdown_table(rows, [("metric", "metric"), ("feature", "feature space"), ("selection", "selection"), ("bg", "background cps"), ("F3", "F3 1 Ms"), ("P3", "P>=3 sigma at 1e-4"), ("claim", "claim")])


def warning_table(v: dict[str, Any]) -> str:
    rows = [{"check": r["check"], "status": r["status"], "details": r["details"]} for r in v["validation_warnings"]]
    return markdown_table(rows, [("check", "check"), ("status", "status"), ("details", "details")])


def abstract_en(v: dict[str, Any]) -> str:
    a = v["authority"]
    return f"""## Abstract

We present a full MEGAlib/Cosima simulation and manuscript-ready evidence package for a balloon-borne focusing 511 keV gamma-ray spectrometer concept using stacked transition-edge-sensor (TES) microcalorimeter layers and active BGO shielding.  The study consolidates the earlier 2602/2605 prompt, delayed-activation, veto, and detector-response work into the clean `COSMOSRAY_BG_260516` workspace and extends it with SPI-grounded source models and time-dependent background calculations.  The mass model is transported with Cosima; atmospheric prompt sources are generated from full-sphere EXPACS/PARMA particle fields; delayed sources are constructed from RP/IP isotope-production positions after removing the W-183/W-180 ground-state/isomer error; event selections include measured-energy smearing, BGO anticoincidence, and Compton/FoV criteria.  A 20-day, 6 h reference trajectory spanning 33-43 km altitude, 29-39 deg latitude, and 100-112 deg longitude drives prompt reweighting, 511 keV atmospheric transmission, and a Level-1 activation inventory that scales fixed day-15 spatial profiles by time-dependent total activity.

The measured final background rates are {fmt(f(v['measured_broad'], 'final_cps'))} cps in 480-550 keV and {fmt(f(v['measured_line'], 'final_cps'))} cps in 510.3-511.8 keV.  The Phase2 profiled nuisance proxy gives 1 Ms 3 sigma thresholds of {fmt(f(v['broad_window'], 'profiled_flux_3sigma_ph_cm2_s'))} ph cm^-2 s^-1 for broad same-event window counting, {fmt(f(v['broad_erl'], 'profiled_flux_3sigma_ph_cm2_s'))} for broad energy-radius-layer templates, and {fmt(f(v['line_erl'], 'profiled_flux_3sigma_ph_cm2_s'))} for line-window templates.  The final Phase12 measured-template requirement metric gives F3={fmt(a['f3_1ms'])} ph cm^-2 s^-1 at 1 Ms and P(>=3 sigma)={fmt(a['p3_at_1e4_1ms'])} for a 1e-4 ph cm^-2 s^-1 source, but this remains a parametric-optics requirement rather than a production detectability claim.  The first-principles L2 channeling-optics scalar cross-check lowers the response scale to {fmt(a['fp_response_scale'], 6)} of the CAM511-normalized value, giving F3={fmt(a['fp_f3_1ms'])}.

SPI/INTEGRAL diffuse bulge+disk emission is physically present but unsuitable for the current pointed/focused mode: the default diffuse model contributes only {fmt(f(v['default_diffuse_param'], 'signal_cps'))} cps through the small FoV and requires {fmt(f(v['default_diffuse_param'], 'T3_years'))} years for an Asimov 3 sigma detection under the inherited parametric response.  The SPI central compact model component at 8.0e-5 ph cm^-2 s^-1 reaches 3 sigma after {fmt(f(v['gcs_param'], 'T3_days_Asimov'))} days under the same parametric response.  The active benchmark set intentionally excludes white-dwarf/classical-nova source cases and keeps the focus on SPI diffuse/compact and V404 flux-scan tests.  Along the reference trajectory, the broad-window total final background varies from {fmt(v['broad_ranges']['total_background_final_cps_level1'][0])} to {fmt(v['broad_ranges']['total_background_final_cps_level1'][1])} cps.

The final claim level is therefore a NIMA-scope background, response, and requirements study.  It is not a final astrophysical detection forecast because production Aeff(E,theta)/PSF/FoV optics, event-level environmental metadata, audited parent-fed decay branches, per-hit BGO electronics, day-by-day mixed delayed-source transport, and a full profiled Poisson likelihood remain gated."""


def abstract_zh(v: dict[str, Any]) -> str:
    a = v["authority"]
    return f"""## 摘要

本文给出一套面向气球平台聚焦 511 keV 伽马射线 TES 微量热谱仪概念的完整 MEGAlib/Cosima 仿真与论文证据包。研究把 2602/2605 阶段的大气 prompt、delayed activation、veto 和探测器响应工作迁移并收敛到干净的 `COSMOSRAY_BG_260516` 工作目录，同时补充 SPI 文献锚定的源模型和时变本底计算。质量模型由 Cosima 输运；大气 prompt 源来自 EXPACS/PARMA 全天球粒子场；delayed 源由 RP/IP 核素产生位置构造，并移除了 W-183/W-180 ground-state/isomer 错误；事件选择包括 measured-energy smearing、BGO 反符合和 Compton/FoV 条件。20 天、6 小时间隔的参考轨迹覆盖 33-43 km 高度、29-39 度纬度和 100-112 度经度，用于驱动 prompt reweight、511 keV 大气透过率和 Level-1 活化库存；该库存用时变总活度缩放固定 day-15 空间 profile。

当前 measured final background 在 480-550 keV 为 {fmt(f(v['measured_broad'], 'final_cps'))} cps，在 510.3-511.8 keV 为 {fmt(f(v['measured_line'], 'final_cps'))} cps。Phase2 profiled nuisance proxy 给出 1 Ms 3 sigma 阈值：宽能窗 same-event counting 为 {fmt(f(v['broad_window'], 'profiled_flux_3sigma_ph_cm2_s'))} ph cm^-2 s^-1，宽能窗 energy-radius-layer template 为 {fmt(f(v['broad_erl'], 'profiled_flux_3sigma_ph_cm2_s'))}，窄线窗 template 为 {fmt(f(v['line_erl'], 'profiled_flux_3sigma_ph_cm2_s'))}。最终 Phase12 measured-template requirement metric 给出 F3={fmt(a['f3_1ms'])} ph cm^-2 s^-1 at 1 Ms，并给出 1e-4 ph cm^-2 s^-1 点源的 P(>=3 sigma)={fmt(a['p3_at_1e4_1ms'])}；但这仍是参数化光学需求结果，不是 production detectability claim。First-principles L2 channeling optics 标量交叉检查把响应降为 CAM511-normalized 值的 {fmt(a['fp_response_scale'], 6)}，对应 F3={fmt(a['fp_f3_1ms'])}。

SPI/INTEGRAL 弥散 bulge+disk 辐射是真实存在的天体源，但不适合当前 pointed/focused 模式：默认弥散模型通过小 FoV 仅贡献 {fmt(f(v['default_diffuse_param'], 'signal_cps'))} cps，在继承的参数化响应下需要 {fmt(f(v['default_diffuse_param'], 'T3_years'))} 年达到 Asimov 3 sigma。SPI central compact model component 的 8.0e-5 ph cm^-2 s^-1 锚点在同一参数化响应下约 {fmt(f(v['gcs_param'], 'T3_days_Asimov'))} 天达到 3 sigma。当前 active benchmark set 明确排除白矮星/经典新星源，只保留 SPI 弥散/紧致源和 V404 flux scan。参考轨迹下，宽能窗总 final background 在 {fmt(v['broad_ranges']['total_background_final_cps_level1'][0])}-{fmt(v['broad_ranges']['total_background_final_cps_level1'][1])} cps 范围变化。

因此，本文最终口径是 NIMA 范围内的本底、响应与需求研究，而不是最终天体物理检出预报。Production Aeff(E,theta)/PSF/FoV 光学、event-level 环境元数据、经审计 parent-fed decay branches、per-hit BGO electronics、逐日 mixed delayed-source transport 和完整 profiled Poisson likelihood 仍是后续 gate。"""


def base_until_discussion(path: Path, language: str) -> str:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^# .*$", "# A full MEGAlib/Cosima background, source-coupling, and time-variation study for a balloon-borne focusing 511 keV TES spectrometer", text, count=1, flags=re.M)
    if language == "zh":
        text = re.sub(r"^# .*$", "# 基于 MEGAlib/Cosima 的气球平台聚焦 511 keV TES 谱仪本底、源耦合与时变研究：NIMA 完整稿", text, count=1, flags=re.M)
    text = text.replace("`COSMOSRAY_BG_2605`", "`COSMOSRAY_BG_260516`")
    text = re.sub(r"\*\*Date:\*\* .*", "**Date:** 2026-05-16", text)
    text = re.sub(r"\*\*日期：\*\* .*", "**日期：** 2026-05-16", text)
    text = re.sub(
        r"\*\*Validation state:\*\*.*",
        "**Validation state:** `python3 tools/validate_workspace.py` passes all hard checks; retained warnings are explicit claim-control states.",
        text,
    )
    text = re.sub(
        r"\*\*验证状态：\*\*.*",
        "**验证状态：** `python3 tools/validate_workspace.py` 所有 hard checks 通过；保留 WARN 均为显式 claim-control 状态。",
        text,
    )
    cut_token = "## 6. Discussion" if language == "en" else "## 6. 讨论"
    if cut_token not in text:
        raise RuntimeError(f"missing discussion cut token in {path}")
    text = text.split(cut_token)[0].rstrip()
    text = text.replace("(../04_FIGURES/", "(../../reports2.0/04_FIGURES/")
    return text


def replace_abstract(text: str, new_abstract: str, language: str) -> str:
    keyword_marker = "**Keywords:**" if language == "en" else "**关键词：**"
    before, rest = text.split("## Abstract" if language == "en" else "## 摘要", 1)
    old_body, after_keywords = rest.split(keyword_marker, 1)
    keywords_line, tail = after_keywords.split("\n\n", 1)
    return before.rstrip() + "\n\n" + new_abstract.rstrip() + "\n\n" + keyword_marker + keywords_line + "\n\n" + tail.lstrip()


def additions_en(v: dict[str, Any]) -> str:
    return f"""

## 6. Literature-grounded 511 keV source cases

The 260516 update replaces the earlier generic source-only interpretation with a literature-anchored source layer.  This layer is not a new claim of astrophysical detection; it is a response-and-requirements bridge between SPI/INTEGRAL measurements and the current post-optics detector transport.  The key change is that diffuse 511 keV emission is never collapsed into a focal-spot point source.  It is folded through the small pointed FoV as an aperture foreground, while compact hypotheses are handled as point-source response scans.

**Table 7. Literature anchors used by the 260516 source update.**

{source_anchor_table(v)}

The SPI diffuse Milky Way measurement is dominated by extended bulge and disk components.  In the current pointed design the FoV radius is 0.0745 deg, so only a tiny fraction of the SPI diffuse intensity lies inside the optical acceptance.  The default B model combines an 8 deg FWHM bulge proxy and a thick-disk foreground; its FoV-contained line flux is {fmt(f(v['default_diffuse_param'], 'fov_flux_ph_cm2_s'))} ph cm^-2 s^-1, only {fmt(f(v['default_diffuse_param'], 'fov_fraction'))} of the total model flux.  The resulting signal is {fmt(f(v['default_diffuse_param'], 'signal_cps'))} cps under the inherited parametric response and {fmt(f(v['default_diffuse_fp'], 'signal_cps'))} cps under the first-principles L2 scalar response.  The corresponding 3 sigma exposures are {fmt(f(v['default_diffuse_param'], 'T3_years'))} yr and {fmt(f(v['default_diffuse_fp'], 'T3_years'))} yr.  This is the central negative result for diffuse emission: the system can be a pointed compact-source requirement study, but it is not a useful instrument mode for measuring the SPI diffuse sky as a diffuse source.

**Table 8. SPI source cases and exposure requirements.**

{source_case_table(v)}

The SPI central point-like component is treated differently.  Its flux anchor of 8.0e-5 ph cm^-2 s^-1 is a model-fitting component near the Galactic centre, not a confirmed source identity.  Under the parametric Phase12 response, that anchor reaches an Asimov 3 sigma after {fmt(f(v['gcs_param'], 'T3_days_Asimov'))} d; under the first-principles L2 scalar response it requires {fmt(f(v['gcs_fp'], 'T3_days_Asimov'))} d.  White-dwarf/classical-nova rows are not carried in the active benchmark set.

**Table 9. Compact point-source flux scan.**

{flux_scan_table(v)}

![Diffuse exposure requirement](../source_time_update/figures/diffuse_exposure_requirement.png)

**Figure 10.** Diffuse-source exposure requirement.  The plotted failure is physical rather than a software error: most SPI diffuse flux is outside the current pointed FoV.

![Point source flux scan](../source_time_update/figures/point_source_flux_scan.png)

**Figure 11.** Point-source flux scan under parametric and first-principles scalar-response assumptions.

V404 Cyg is now treated as an observed-feature flux benchmark grid, not as a fixed steady narrow-line source.  The 2015 INTEGRAL/SPI result anchors the existence of a transient annihilation feature, while this local workflow scans the input flux and folds each proxy spectrum through the 480-550 keV response.  This makes V404 useful for transient performance scaling and bandpass-risk control without promoting it to a final V404 detectability claim.

**Table 9b. V404 transient benchmark after bandpass folding.**

{v404_benchmark_table(v)}

The fixed-background benchmark is not the final time-dependent result.  The current source/time package also performs a 6 h bin integration using the trajectory-dependent final prompt rate, the Level-1 activation inventory with buildup/decay, and the 511 keV atmospheric transmission and visibility.  The transparent counting result is retained in the CSV files, while Table 9c reports the Phase12 measured-ERL metric-scaled result.  This is still not a full profiled Poisson likelihood, but it is the correct L1 answer to the question "what day does a given benchmark flux reach 3 sigma under the reference flight profile?"

**Table 9c. Time-dependent point-source benchmark.**

{time_dependent_point_table(v)}

**Table 9d. Time-dependent V404 benchmark.**

{time_dependent_v404_table(v)}

![Time-dependent drivers](../source_time_update/figures/time_dependent_background_transmission_drivers.png)

**Figure 11b.** Final background drivers and 511 keV atmospheric transmission used in the time-dependent significance integration.

![Time-dependent cumulative significance](../source_time_update/figures/time_dependent_cumulative_significance.png)

**Figure 11c.** Example cumulative metric-scaled significance curves under the reference flight profile.

## 7. Time-dependent trajectory and activation update

The 260516 time update addresses the specific missing link in the older report: delayed activity should respond indirectly to a time-variable irradiation history.  The implemented Level-1 model integrates a trajectory-driven activity inventory and then scales the fixed day-15 delayed spatial profiles by total activity.  This captures total-activity changes from variable irradiation and decay history, while retaining an explicit caveat that it is not a fresh day-by-day RP/IP spatial transport.

**Table 10. Reference-trajectory and background time ranges.**

{time_range_table(v)}

![Reference trajectory](../source_time_update/figures/trajectory_lat_lon_altitude.png)

**Figure 12.** Reference balloon trajectory in latitude, longitude, and altitude.

![Altitude and atmospheric depth](../source_time_update/figures/altitude_depth_vs_time.png)

**Figure 13.** Altitude and atmospheric-depth drivers used for prompt reweighting and 511 keV transmission.

![Broad background time variation](../source_time_update/figures/background_time_variation_broad.png)

**Figure 14.** Broad-window prompt, delayed, and total background variation.

![Line background time variation](../source_time_update/figures/background_time_variation_line.png)

**Figure 15.** Narrow 510.3-511.8 keV background variation.

![Delayed activity driver](../source_time_update/figures/delayed_activity_driver_time_variation.png)

**Figure 16.** Time-dependent activation driver and total delayed activity.  The early delayed rate starts from zero in this model because the inventory is built up along the reference profile.

## 8. Final metric closure and optics claim boundary

The final compact-source analysis remains Decision C: a requirements-only result under parametric optics.  This is not a rhetorical limitation; it follows from the metric crosswalk and the optics gate.  The primary Phase12 metric is the baseline measured-energy/radius/layer template with F3={fmt(float(v['primary_metric']['F3_1Ms']))} ph cm^-2 s^-1 and P(>=3 sigma)={fmt(float(v['primary_metric']['P_ge_3sigma_at_1e-4_1Ms']))} for 1e-4 ph cm^-2 s^-1 at 1 Ms.  The selection-only best configuration is not upgraded because it does not pass the final reproduction gate.

**Table 11. Final metric crosswalk.**

{metric_table(v)}

The first-principles channeling-optics check is an important improvement because it avoids direct scaling to match CAM511 and instead uses a W/Si Parratt multilayer table.  Its on-axis L2 effective area is {fmt(float(v['fp']['firstprinciples_aeff_cm2']))} cm2, with response scale {fmt(float(v['fp']['response_scale_vs_current_cam511_normalization']), 6)}, HPD diameter {fmt(float(v['fp']['weighted_hpd_diameter_mm']))} mm, and r95 {fmt(float(v['fp']['weighted_r95_mm']))} mm.  However, this is still a scalar requirement input coupled to existing detector templates; it is not a production Aeff(E,theta), PSF, FoV, and focal-plane map.

![Metric closure](../../reports2.0/12_FINAL_COMPACT_SOURCE_ANALYSIS/final_figures/metric_closure_phase9_phase10_phase12.png)

**Figure 17.** Phase9/Phase10/Phase12 metric closure and the reason the final result remains a requirements statement.

![Selection decision](../../reports2.0/12_FINAL_COMPACT_SOURCE_ANALYSIS/final_figures/selection_decision_matrix.png)

**Figure 18.** Selection upgrade decision.  The selection-only best remains a secondary design comparison.

![Optics requirement](../../reports2.0/12_FINAL_COMPACT_SOURCE_ANALYSIS/final_figures/optics_bandpass_or_requirement.png)

**Figure 19.** Optics bandpass/requirement status.  Production optics is explicitly unavailable.

## 9. Validation and paper-readiness audit

All hard validation checks pass after regenerating the 260516 source/time update and this manuscript package.  The retained warnings are not hidden failures; they are the remaining claim-control gates that must be preserved in the paper text.

**Table 12. Retained validation warnings.**

{warning_table(v)}

The NIMA journal scope is appropriate because NIM-A publishes work on scientific instruments, radiation detection and spectrometry, astrophysics instrumentation, simulation tools, and detector-system performance.  The scope warning is equally important: a standard-code simulation without validation can be rejected.  This manuscript therefore emphasizes geometry identity checks, source syntax, event-rate closure, source-placement gates, delayed-source bug correction, measured-energy response, validation output, and explicitly bounded limitations rather than presenting a black-box Geant4 result.

## 10. Discussion

The completed workflow has a coherent result.  The detector/background ledger is strong enough for a NIMA-scope instrumentation paper because it closes the chain from environmental source construction to final selected rates, sensitivity estimators, and validation artifacts.  The strongest quantitative background result is that the selected 480-550 keV residual is several cps and is delayed-activation dominated after vetoes.  This explains why the analysis gains from energy-radius-layer templates: the signal and background are not just scalar counts but have different measured-energy, radius, and layer structure.

The source-coupling result is deliberately split into diffuse and compact regimes.  The SPI diffuse Galactic 511 keV source is real, but the present pointed focusing design accepts only a minute FoV fraction.  The correct conclusion is therefore negative: this design is unsuitable for the SPI diffuse source in its current pointed mode.  Conversely, compact sources near 1e-4 ph cm^-2 s^-1 are close to the parametric requirement boundary, but the first-principles scalar check shows that the optical response assumption dominates the ultimate exposure.  The paper should not claim a final 1e-4 ph cm^-2 s^-1 capability until production optics and full likelihood analysis are available.

The time-dependent update strengthens the report because it no longer treats delayed activation as completely static.  It is still a Level-1 model: total activity follows the reference irradiation history, but spatial profiles are fixed to day 15.  That is a useful intermediate result for a paper because the approximation is explicit and produces a trajectory/background figure set, but it must not be written as full day-by-day activation transport.

## 11. Limitations

The current flight profile is synthetic/reference, not telemetry.  Prompt reweighting remains particle-level because event-level primary energy and direction metadata are not preserved in the final catalog.  Parent-fed decay chains are not numerically active without audited branch ratios.  The delayed time series scales fixed day-15 spatial profiles and therefore cannot replace fresh day-by-day RP/IP transport.  BGO response is an event-total threshold proxy, not a per-hit electronics model.  The profile likelihood is a diagonal-nuisance proxy rather than a full Poisson optimizer.  The first-principles optics result is a scalar requirement input, not a production response matrix validated against an engineering optics model.

## 12. Conclusions

The `COSMOSRAY_BG_260516` workflow now supports a complete NIMA-style manuscript package rather than a short summary.  It demonstrates a reproducible 511 keV TES/BGO simulation chain, corrected delayed-source construction, measured-energy and veto response, Phase2/Phase12 sensitivity metrics, SPI-grounded source coupling, and trajectory-driven time variation.  The final measured broad-window background is {fmt(f(v['measured_broad'], 'final_cps'))} cps, the line-window background is {fmt(f(v['measured_line'], 'final_cps'))} cps, and the primary Phase12 1 Ms requirement metric is F3={fmt(v['authority']['f3_1ms'])} ph cm^-2 s^-1 under parametric optics.

The astrophysical interpretation is constrained.  The current pointed/focused mode is not useful for the SPI diffuse bulge+disk signal, and the central compact anchor is a requirement benchmark rather than a confirmed source claim.  The final claim level remains `PARAMETRIC_OPTICS_REQUIREMENT`.  Production optics, event-level environmental metadata, audited parent feeding, per-hit BGO, mixed delayed transport, and full profile likelihood are the required upgrades before final astrophysical detectability can be claimed.

## Declarations

**Data and code availability:** The generated manuscript, tables, figures, source/time update products, validation logs, and scripts are in `cosmosray_bg_260516`.  Large raw Monte Carlo files are retained in the same workspace and indexed by `migration_bigfile_manifest.tsv`; a curated external archive would be needed before journal submission.

**Competing interests:** None declared in this draft.

**AI-assisted drafting disclosure:** This manuscript package was assembled with AI-assisted coding and writing support.  Numerical values are generated from local scripts and validation artifacts; all text, references, and claims require author review before submission.

## References

{reference_list_en()}
"""


def additions_zh(v: dict[str, Any]) -> str:
    return f"""

## 6. 文献锚定的 511 keV 源模型

260516 更新把早期 generic source-only 口径改成文献锚定的源模型层。这个层不是新的天体物理检出宣称，而是 SPI/INTEGRAL 观测量与当前 post-optics detector transport 之间的 response/requirements 桥接。关键原则是：弥散 511 keV 辐射不能被压成焦斑点源；它只能作为小 FoV aperture foreground 折叠。紧致源假设则作为 point-source response scan 处理。

**表 7. 260516 源更新使用的文献锚点。**

{source_anchor_table(v)}

SPI diffuse Milky Way 测量由扩展的 bulge 和 disk 成分主导。当前 pointed 设计 FoV 半径只有 0.0745 deg，因此只有极小一部分 SPI 弥散强度进入光学接受角。默认 B 模型由 8 deg FWHM bulge proxy 和 thick-disk foreground 组成；FoV 内 line flux 为 {fmt(f(v['default_diffuse_param'], 'fov_flux_ph_cm2_s'))} ph cm^-2 s^-1，只占总模型通量的 {fmt(f(v['default_diffuse_param'], 'fov_fraction'))}。在继承的参数化响应下信号为 {fmt(f(v['default_diffuse_param'], 'signal_cps'))} cps；在 first-principles L2 scalar response 下为 {fmt(f(v['default_diffuse_fp'], 'signal_cps'))} cps。对应 3 sigma 曝光为 {fmt(f(v['default_diffuse_param'], 'T3_years'))} 年和 {fmt(f(v['default_diffuse_fp'], 'T3_years'))} 年。这是弥散源的核心负结果：SPI 弥散源不适合当前 pointed 模式；系统可作为 pointed compact-source requirement study，但不适合测量 SPI diffuse sky。

**表 8. SPI 源模型与曝光需求。**

{source_case_table(v)}

SPI central point-like component 单独处理。其 8.0e-5 ph cm^-2 s^-1 flux anchor 是银河中心附近 model-fitting component，不是 confirmed source identity。在 Phase12 参数化响应下，该 anchor 约 {fmt(f(v['gcs_param'], 'T3_days_Asimov'))} 天达到 Asimov 3 sigma；在 first-principles L2 scalar response 下需要 {fmt(f(v['gcs_fp'], 'T3_days_Asimov'))} 天。白矮星/经典新星行不再放入 active benchmark set。

**表 9. 紧致点源 flux scan。**

{flux_scan_table(v)}

![Diffuse exposure requirement](../source_time_update/figures/diffuse_exposure_requirement.png)

**图 10.** 弥散源曝光需求。这个失败是物理结果而不是软件错误：绝大多数 SPI diffuse flux 位于当前 pointed FoV 之外。

![Point source flux scan](../source_time_update/figures/point_source_flux_scan.png)

**图 11.** 参数化响应和 first-principles scalar response 下的点源 flux scan。

V404 Cyg 现在按 observed-feature flux benchmark grid 处理，而不是固定稳态窄线源。2015 年 INTEGRAL/SPI 结果给出瞬变湮灭特征的观测背景；本地工作流扫描输入 flux，并把每个 proxy spectrum 折进 480-550 keV 响应。这样可以用 V404 讨论瞬变性能标度和 bandpass 风险，但不能升级成最终 V404 detectability claim。

**表 9b. V404 瞬变 benchmark 的带宽折算结果。**

{v404_benchmark_table(v)}

固定本底 benchmark 不是最终时变结果。当前 source/time 包已经新增 6 小时 bin 积分，把随轨迹变化的 prompt final rate、含 buildup/decay 的 Level-1 activation inventory，以及 511 keV 大气透过率和可见性一起放入显著度计算。CSV 中保留了透明的 counting 口径；表 9c 报告与 Phase12 measured-ERL 主指标一致的 metric-scaled 结果。它仍不是完整 profiled Poisson likelihood，但已经是 reference flight profile 下“某个 benchmark flux 第几天到 3 sigma”的 L1 回答。

**表 9c. 时变点源 benchmark。**

{time_dependent_point_table(v)}

**表 9d. 时变 V404 benchmark。**

{time_dependent_v404_table(v)}

![Time-dependent drivers](../source_time_update/figures/time_dependent_background_transmission_drivers.png)

**图 11b.** 时变显著度积分使用的 final background drivers 与 511 keV atmospheric transmission。

![Time-dependent cumulative significance](../source_time_update/figures/time_dependent_cumulative_significance.png)

**图 11c.** reference flight profile 下若干代表性源的 cumulative metric-scaled significance。

## 7. 时变轨迹与活化更新

260516 时变更新补上了旧报告中缺失的一环：delayed activity 应当间接响应时变照射历史。当前 Level-1 模型积分 trajectory-driven activity inventory，然后用总活度缩放固定 day-15 delayed spatial profiles。它捕捉了 variable irradiation 与 decay history 引起的总活度变化，但仍明确 caveat：这不是新的逐日 RP/IP 空间输运。

**表 10. 参考轨迹和本底时变范围。**

{time_range_table(v)}

![Reference trajectory](../source_time_update/figures/trajectory_lat_lon_altitude.png)

**图 12.** 参考气球轨迹的经纬度和高度。

![Altitude and atmospheric depth](../source_time_update/figures/altitude_depth_vs_time.png)

**图 13.** 用于 prompt reweight 和 511 keV transmission 的高度/大气深度驱动量。

![Broad background time variation](../source_time_update/figures/background_time_variation_broad.png)

**图 14.** 宽能窗 prompt、delayed 与 total background 时变。

![Line background time variation](../source_time_update/figures/background_time_variation_line.png)

**图 15.** 510.3-511.8 keV 窄线窗本底时变。

![Delayed activity driver](../source_time_update/figures/delayed_activity_driver_time_variation.png)

**图 16.** 时变活化 driver 和总 delayed activity。早期 delayed rate 从 0 开始，因为库存沿参考剖面积累。

## 8. 最终指标闭合与光学 claim boundary

最终 compact-source analysis 仍是 Decision C：参数化光学下的 requirements-only result。这不是措辞保守，而是由 metric crosswalk 和 optics gate 决定的。Primary Phase12 metric 是 baseline measured-energy/radius/layer template，F3={fmt(float(v['primary_metric']['F3_1Ms']))} ph cm^-2 s^-1，1e-4 ph cm^-2 s^-1、1 Ms 的 P(>=3 sigma)={fmt(float(v['primary_metric']['P_ge_3sigma_at_1e-4_1Ms']))}。Selection-only best 没有升级，因为它没有通过 final reproduction gate。

**表 11. Final metric crosswalk。**

{metric_table(v)}

First-principles channeling-optics check 是重要改进，因为它没有直接把结果缩放去贴 CAM511，而是使用 W/Si Parratt multilayer table。L2 on-axis effective area 为 {fmt(float(v['fp']['firstprinciples_aeff_cm2']))} cm2，response scale 为 {fmt(float(v['fp']['response_scale_vs_current_cam511_normalization']), 6)}，HPD diameter 为 {fmt(float(v['fp']['weighted_hpd_diameter_mm']))} mm，r95 为 {fmt(float(v['fp']['weighted_r95_mm']))} mm。但这仍只是耦合到现有 detector template 的 scalar requirement input，不是 production Aeff(E,theta)、PSF、FoV 和 focal-plane map。

![Metric closure](../../reports2.0/12_FINAL_COMPACT_SOURCE_ANALYSIS/final_figures/metric_closure_phase9_phase10_phase12.png)

**图 17.** Phase9/Phase10/Phase12 metric closure，并说明为什么最终结果只能是 requirements statement。

![Selection decision](../../reports2.0/12_FINAL_COMPACT_SOURCE_ANALYSIS/final_figures/selection_decision_matrix.png)

**图 18.** Selection upgrade decision。Selection-only best 保持为次级设计比较。

![Optics requirement](../../reports2.0/12_FINAL_COMPACT_SOURCE_ANALYSIS/final_figures/optics_bandpass_or_requirement.png)

**图 19.** Optics bandpass/requirement 状态。Production optics 明确不可用。

## 9. Validation 和论文就绪度审计

重新生成 260516 source/time update 和本文包后，所有 hard validation checks 通过。保留 warnings 不是隐藏失败，而是论文必须保留的 claim-control gates。

**表 12. 保留 validation warnings。**

{warning_table(v)}

NIMA 期刊范围是合适的，因为 NIM-A 接收科学仪器、辐射探测与谱学、天体物理仪器、仿真工具和 detector-system performance 相关论文。但 scope warning 同样重要：如果只是黑箱使用标准 Geant4 代码而缺少 validation，容易被拒。因此本文必须强调 geometry identity checks、source syntax、event-rate closure、source-placement gates、delayed-source bug correction、measured-energy response、validation output 和显式 bounded limitations，而不是把结果写成黑箱仿真。

## 10. 讨论

完整工作流现在有一个自洽结论。Detector/background ledger 已经足够支撑 NIMA 范围的 instrumentation paper，因为它闭合了从环境源构造到 final selected rates、sensitivity estimators 和 validation artifacts 的链条。最强的本底结论是：480-550 keV selected residual 为数 cps，且 veto 后由 delayed activation 主导。这也解释了为什么 energy-radius-layer templates 有效：信号和本底不是简单标量计数，而是在 measured energy、radius 和 layer 上有不同结构。

源耦合结论必须分成弥散和紧致两个 regime。SPI diffuse Galactic 511 keV 源是真实源，但当前 pointed focusing design 只接受极小 FoV fraction。因此正确结论是负的：该设计不适合以当前 pointed mode 测量 SPI diffuse source。相反，约 1e-4 ph cm^-2 s^-1 的紧致源接近参数化需求边界，但 first-principles scalar check 说明光学响应假设主导最终曝光；在 production optics 和 full likelihood analysis 完成前，不能声称最终 1e-4 ph cm^-2 s^-1 能力。

时变更新增强了报告可信度，因为 delayed activation 不再被完全静态处理。它仍是 Level-1 模型：总活度跟随参考照射历史，但空间 profile 固定为 day 15。这是可写入论文的有用中间结果，因为近似是显式的，并且产生了 trajectory/background figure set；但它不能写成完整 day-by-day activation transport。

## 11. 局限性

当前 flight profile 是 synthetic/reference，不是 telemetry。Prompt reweighting 仍是 particle-level，因为 final catalog 没有保存 event-level primary energy/direction metadata。没有经审计 branch ratios 时，parent-fed decay chains 不数值生效。Delayed time series 只缩放固定 day-15 spatial profiles，不能替代新的逐日 RP/IP transport。BGO response 是 event-total threshold proxy，不是 per-hit electronics model。Profile likelihood 是 diagonal-nuisance proxy，不是 full Poisson optimizer。First-principles optics 结果是 scalar requirement input，不是已由工程光学模型验证的 production response matrix。

## 12. 结论

`COSMOSRAY_BG_260516` workflow 现在支持完整 NIMA-style manuscript package，而不是短摘要。它展示了可复现的 511 keV TES/BGO 仿真链、修正后的 delayed-source construction、measured-energy/veto response、Phase2/Phase12 sensitivity metrics、SPI-grounded source coupling 和 trajectory-driven time variation。最终 measured broad-window background 为 {fmt(f(v['measured_broad'], 'final_cps'))} cps，line-window background 为 {fmt(f(v['measured_line'], 'final_cps'))} cps，参数化光学下 primary Phase12 1 Ms requirement metric 为 F3={fmt(v['authority']['f3_1ms'])} ph cm^-2 s^-1。

天体物理解释必须受限。当前 pointed/focused mode 不适合 SPI diffuse bulge+disk signal；central compact anchor 是 requirements benchmark 而非 confirmed source claim。最终 claim level 仍为 `PARAMETRIC_OPTICS_REQUIREMENT`。Production optics、event-level environmental metadata、audited parent feeding、per-hit BGO、mixed delayed transport 和 full profile likelihood 是最终天体物理 detectability claim 前的必要升级。

## 声明

**数据与代码可用性：** 生成的 manuscript、tables、figures、source/time update products、validation logs 和 scripts 均位于 `cosmosray_bg_260516`。大型 Monte Carlo 原始文件保留在同一工作区，并由 `migration_bigfile_manifest.tsv` 索引；正式投稿前需要整理外部分发归档。

**利益冲突：** 本草稿暂无声明。

**AI 辅助写作披露：** 本 manuscript package 使用 AI-assisted coding and writing support 组装。数值来自本地脚本和 validation artifacts；所有文字、参考文献和 claims 在投稿前必须由作者复核。

## 参考文献

{reference_list_en()}
"""


def reference_list_en() -> str:
    refs = [
        "S. Agostinelli et al., GEANT4: A simulation toolkit, Nucl. Instrum. Methods Phys. Res. A 506 (2003) 250-303.",
        "A. Zoglauer et al., MEGAlib: simulation and data analysis for low-to-medium-energy gamma-ray telescopes, Proc. SPIE 7011 (2008) 70113F.",
        "A. Zoglauer et al., Cosima: The cosmic simulator of MEGAlib, IEEE NSS/MIC Conference Record (2009).",
        "T. Sato, Analytical model for estimating terrestrial cosmic ray fluxes nearly anytime and anywhere in the world: Extension of PARMA/EXPACS, PLOS ONE 10 (2015) e0144679.",
        "T. Sato, Analytical model for estimating the zenith angle dependence of terrestrial cosmic ray fluxes, PLOS ONE 11 (2016) e0160390.",
        "F. Shirazi et al., The 511-CAM mission: a pointed 511 keV gamma-ray telescope with stacked transition edge sensor microcalorimeter arrays, JATIS 9 (2023) 024006.",
        "J. A. Tomsick et al., The Compton Spectrometer and Imager, Proc. Sci. ICRC2023 (2023) 745; arXiv:2308.12362.",
        "A. Ciabattoni et al., Benchmarking of Geant4 simulations for the COSI Anticoincidence System, Exp. Astron. 60 (2025) 9.",
        "R. Tian et al., Simulation of non X-ray background for the DIffuse X-ray Explorer mission, Research Square preprint (2026).",
        "J. Knodlseder et al., The all-sky distribution of 511 keV electron-positron annihilation emission, A&A 441 (2005) 513-532.",
        "E. Churazov et al., Positron annihilation spectrum from the Galactic Centre region observed by SPI/INTEGRAL, MNRAS 357 (2005) 1377-1386.",
        "P. Jean et al., Spectral analysis of the Galactic e+e- annihilation emission, A&A 445 (2006) 579-589.",
        "N. Prantzos et al., The 511 keV emission from positron annihilation in the Galaxy, Rev. Mod. Phys. 83 (2011) 1001-1056.",
        "T. Siegert et al., Gamma-ray spectroscopy of positron annihilation in the Milky Way, A&A 586 (2016) A84; arXiv:1512.00325.",
        "G. Weidenspointner et al., An asymmetric distribution of positrons in the Galactic disk revealed by gamma-rays, Nature 451 (2008) 159-162.",
        "F. G. Kondev et al., The NUBASE2020 evaluation of nuclear physics properties, Chin. Phys. C 45 (2021) 030001.",
        "National Nuclear Data Center, Evaluated Nuclear Structure Data File (ENSDF), Brookhaven National Laboratory.",
        "R. M. T. Damayanthi et al., Observation of very fast response signals from Pb absorber coupled transition edge sensor gamma-ray microcalorimeter, NIM A 691 (2012) 30-33.",
        "T. Siegert et al., Positron annihilation signatures associated with the outburst of the microquasar V404 Cygni, Nature 531 (2016) 341-343; arXiv:1603.01169.",
        "H. Yoneda, T. Siegert and S. Mittal, Imaging the positron annihilation line with 20 years of INTEGRAL/SPI observations, A&A 702 (2025) A220; arXiv:2509.01066.",
        "T. Siegert et al., Gamma-ray lines in astronomy, Space Sci. Rev. 222 (2026) 34.",
        "Nuclear Instruments and Methods in Physics Research Section A, Aims and scope, ScienceDirect journal page, accessed 2026-05-16.",
    ]
    return "\n".join(f"[{i + 1}] {ref}" for i, ref in enumerate(refs))


def references_bib() -> str:
    entries = [
        "@article{Agostinelli2003Geant4, title={GEANT4: A simulation toolkit}, journal={Nuclear Instruments and Methods in Physics Research Section A}, volume={506}, pages={250--303}, year={2003}}",
        "@inproceedings{Zoglauer2008MEGAlib, title={MEGAlib: simulation and data analysis for low-to-medium-energy gamma-ray telescopes}, booktitle={Proc. SPIE}, volume={7011}, pages={70113F}, year={2008}}",
        "@inproceedings{Zoglauer2009Cosima, title={Cosima: the cosmic simulator of MEGAlib}, booktitle={IEEE NSS/MIC}, year={2009}}",
        "@article{Sato2015PARMA, title={Analytical model for estimating terrestrial cosmic ray fluxes nearly anytime and anywhere in the world: Extension of PARMA/EXPACS}, journal={PLOS ONE}, volume={10}, pages={e0144679}, year={2015}}",
        "@article{Sato2016PARMA, title={Analytical model for estimating the zenith angle dependence of terrestrial cosmic ray fluxes}, journal={PLOS ONE}, volume={11}, pages={e0160390}, year={2016}}",
        "@article{Shirazi2023CAM511, title={The 511-CAM mission}, journal={Journal of Astronomical Telescopes, Instruments, and Systems}, volume={9}, pages={024006}, year={2023}}",
        "@misc{Tomsick2023COSI, title={The Compton Spectrometer and Imager}, howpublished={arXiv:2308.12362}, year={2023}}",
        "@article{Ciabattoni2025COSIACS, title={Benchmarking of Geant4 simulations for the COSI Anticoincidence System}, journal={Experimental Astronomy}, volume={60}, pages={9}, year={2025}}",
        "@misc{Tian2026DIXE, title={Simulation of non X-ray background for the DIffuse X-ray Explorer mission}, author={Tian, R. and Mao, J. and Liu, J. and Jin, H. and Cui, W.}, howpublished={Research Square preprint}, year={2026}}",
        "@article{Knodlseder2005SPI511, title={The all-sky distribution of 511 keV electron-positron annihilation emission}, journal={Astronomy and Astrophysics}, volume={441}, pages={513--532}, year={2005}}",
        "@article{Churazov2005SPI511, title={Positron annihilation spectrum from the Galactic Centre region observed by SPI/INTEGRAL}, journal={Monthly Notices of the Royal Astronomical Society}, volume={357}, pages={1377--1386}, year={2005}}",
        "@article{Jean2006SPI511, title={Spectral analysis of the Galactic e+e- annihilation emission}, journal={Astronomy and Astrophysics}, volume={445}, pages={579--589}, year={2006}}",
        "@article{Prantzos2011RMP, title={The 511 keV emission from positron annihilation in the Galaxy}, journal={Reviews of Modern Physics}, volume={83}, pages={1001--1056}, year={2011}}",
        "@article{Siegert2016AandA, title={Gamma-ray spectroscopy of positron annihilation in the Milky Way}, journal={Astronomy and Astrophysics}, volume={586}, pages={A84}, year={2016}}",
        "@article{Weidenspointner2008Nature, title={An asymmetric distribution of positrons in the Galactic disk revealed by gamma-rays}, journal={Nature}, volume={451}, pages={159--162}, year={2008}}",
        "@article{Kondev2021NUBASE, title={The NUBASE2020 evaluation of nuclear physics properties}, journal={Chinese Physics C}, volume={45}, pages={030001}, year={2021}}",
        "@misc{NNDCENSDF, title={Evaluated Nuclear Structure Data File (ENSDF)}, author={{National Nuclear Data Center}}, howpublished={Brookhaven National Laboratory}}",
        "@article{Damayanthi2012TES, title={Observation of very fast response signals from Pb absorber coupled transition edge sensor gamma-ray microcalorimeter}, journal={Nuclear Instruments and Methods in Physics Research Section A}, volume={691}, pages={30--33}, year={2012}}",
        "@article{Siegert2016V404, title={Positron annihilation signatures associated with the outburst of the microquasar V404 Cygni}, journal={Nature}, volume={531}, pages={341--343}, year={2016}}",
        "@article{Yoneda2025SPI20yr, title={Imaging the positron annihilation line with 20 years of INTEGRAL/SPI observations}, journal={Astronomy and Astrophysics}, volume={702}, pages={A220}, year={2025}}",
        "@article{Siegert2026GammaLines, title={Gamma-ray lines in astronomy}, author={Siegert, T. and others}, journal={Space Science Reviews}, volume={222}, pages={34}, year={2026}}",
        "@misc{NIMA2026Scope, title={Nuclear Instruments and Methods in Physics Research Section A: Aims and scope}, howpublished={ScienceDirect journal page}, year={2026}}",
    ]
    return "\n\n".join(entries) + "\n"


def literature_matrix(v: dict[str, Any]) -> list[dict[str, str]]:
    rows = []
    for ref in reference_list_en().splitlines():
        idx = ref.split("]", 1)[0].strip("[")
        body = ref.split("] ", 1)[1]
        rows.append({"id": idx, "reference": body, "role_in_manuscript": "background, method, source anchor, or claim-control support"})
    for row in v["literature"]:
        rows.append({"id": row["anchor_id"], "reference": row["reference"], "role_in_manuscript": row["claim_note"]})
    return rows


def latex_to_plain(expr: str) -> str:
    text = expr
    replacements = {
        r"\times": "x",
        r"\simeq": "approx.",
        r"\ge": ">=",
        r"\le": "<=",
        r"\sigma": "sigma",
        r"\gamma": "gamma",
        r"\lambda": "lambda",
        r"\to": "->",
        r"\sum": "sum",
        r"\theta": "theta",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    text = re.sub(r"\\mathrm\{([^{}]+)\}", r"\1", text)
    text = re.sub(r"\\text\{([^{}]+)\}", r"\1", text)
    text = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"(\1)/(\2)", text)
    text = re.sub(r"\^\{([^{}]+)\}", r"^\1", text)
    text = re.sub(r"_\{([^{}]+)\}", r"_\1", text)
    text = re.sub(r"\\([A-Za-z]+)", r"\1", text)
    return text.replace("{", "").replace("}", "")


def inline_markup(text: str) -> str:
    text = re.sub(r"\\\((.*?)\\\)", lambda m: latex_to_plain(m.group(1)), text)
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return escaped


def parse_table(lines: list[str]) -> str:
    parsed: list[list[str]] = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and all(set(cell) <= {"-", ":"} for cell in cells):
            continue
        parsed.append(cells)
    if not parsed:
        return ""
    head = "".join(f"<th>{inline_markup(cell)}</th>" for cell in parsed[0])
    body = []
    for row in parsed[1:]:
        body.append("<tr>" + "".join(f"<td>{inline_markup(cell)}</td>" for cell in row) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def flush_paragraph(out: list[str], para: list[str]) -> None:
    if para:
        out.append(f"<p>{inline_markup(' '.join(line.strip() for line in para))}</p>")
        para.clear()


def markdown_to_html(markdown: str, lang: str, title: str) -> str:
    lines = markdown.splitlines()
    out: list[str] = []
    para: list[str] = []
    i = 0
    in_code = False
    code_lines: list[str] = []
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_code:
                out.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
                code_lines.clear()
                in_code = False
            else:
                flush_paragraph(out, para)
                in_code = True
            i += 1
            continue
        if in_code:
            code_lines.append(line)
            i += 1
            continue
        if not stripped:
            flush_paragraph(out, para)
            i += 1
            continue
        if stripped == r"\[":
            flush_paragraph(out, para)
            eq: list[str] = []
            i += 1
            while i < len(lines) and lines[i].strip() != r"\]":
                eq.append(lines[i])
                i += 1
            out.append("<div class=\"equation\">" + html.escape(latex_to_plain("\n".join(eq))) + "</div>")
            i += 1
            continue
        if stripped.startswith("|"):
            flush_paragraph(out, para)
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            out.append(parse_table(table_lines))
            continue
        image = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", stripped)
        if image:
            flush_paragraph(out, para)
            alt, src = image.groups()
            out.append(f"<figure><img src=\"{html.escape(src)}\" alt=\"{html.escape(alt)}\"><figcaption>{html.escape(alt)}</figcaption></figure>")
            i += 1
            continue
        if stripped.startswith("# "):
            flush_paragraph(out, para)
            out.append(f"<h1>{inline_markup(stripped[2:])}</h1>")
        elif stripped.startswith("## "):
            flush_paragraph(out, para)
            out.append(f"<h2>{inline_markup(stripped[3:])}</h2>")
        elif stripped.startswith("### "):
            flush_paragraph(out, para)
            out.append(f"<h3>{inline_markup(stripped[4:])}</h3>")
        else:
            para.append(line)
        i += 1
    flush_paragraph(out, para)
    return f"<!doctype html><html lang=\"{html.escape(lang)}\"><head><meta charset=\"utf-8\"><title>{html.escape(title)}</title><style>{CSS}</style></head><body><article>{''.join(out)}</article></body></html>"


def write_scaffold(en: str, zh: str, v: dict[str, Any]) -> None:
    for subdir in ["00_literature", "sections", "tables", "figures", "submissions/v1_nima"]:
        (OUT / subdir).mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "literature_matrix.csv", literature_matrix(v))
    (OUT / "references.bib").write_text(references_bib(), encoding="utf-8")
    (OUT / "00_literature" / "search_strategy.md").write_text(
        """# Literature Search Strategy

Primary anchors were checked from local papers plus current online records on 2026-05-16:

- NIM-A journal scope and simulation-validation warning from ScienceDirect.
- SPI Milky Way 511 keV spectroscopy and flux components from Siegert et al. 2016.
- V404 transient annihilation benchmark from Siegert et al. 2016 Nature/arXiv.
- White-dwarf/classical-nova source cases are intentionally excluded from the active benchmark set.
- 20-year SPI image context from Yoneda, Siegert & Mittal 2025.

The manuscript uses these records only as anchors for source modelling and claim control; numerical simulation outputs are loaded from local CSV/JSON products.
""",
        encoding="utf-8",
    )
    (OUT / "00_literature" / "literature_matrix.md").write_text(
        "# Literature Matrix\n\n" + markdown_table(literature_matrix(v), [("id", "id"), ("reference", "reference"), ("role_in_manuscript", "role")]),
        encoding="utf-8",
    )
    outline = """# Manuscript Outline

1. Abstract and keywords.
2. Introduction: 511 keV science motivation, NIM-A instrumentation scope, and conservative claim boundary.
3. Instrument and source model: mass model, prompt sources, activation source, science source, and optics-background addendum.
4. Event merging, veto, and sensitivity estimators.
5. Results: production closure, day-15 background, measured-energy windows, activation contributors, sensitivity, and convergence gates.
6. Figures.
7. Literature-grounded SPI source cases.
8. Time-dependent trajectory and activation update.
9. Final metric closure and optics claim boundary.
10. Validation and paper-readiness audit.
11. Discussion, limitations, conclusions, declarations, references.
"""
    (OUT / "01_outline.md").write_text(outline, encoding="utf-8")
    (OUT / "sections" / "english_compiled_source.md").write_text(en, encoding="utf-8")
    (OUT / "sections" / "chinese_compiled_source.md").write_text(zh, encoding="utf-8")
    (OUT / "tables" / "table_source_cases.md").write_text(source_case_table(v), encoding="utf-8")
    (OUT / "tables" / "table_time_ranges.md").write_text(time_range_table(v), encoding="utf-8")
    (OUT / "tables" / "table_metric_crosswalk.md").write_text(metric_table(v), encoding="utf-8")
    figure_rows = [
        {"figure": "10", "path": "../source_time_update/figures/diffuse_exposure_requirement.png", "role": "diffuse-source negative result"},
        {"figure": "11", "path": "../source_time_update/figures/point_source_flux_scan.png", "role": "compact flux scan"},
        {"figure": "12", "path": "../source_time_update/figures/trajectory_lat_lon_altitude.png", "role": "reference trajectory"},
        {"figure": "14", "path": "../source_time_update/figures/background_time_variation_broad.png", "role": "broad background time variation"},
        {"figure": "17", "path": "../../reports2.0/12_FINAL_COMPACT_SOURCE_ANALYSIS/final_figures/metric_closure_phase9_phase10_phase12.png", "role": "final metric closure"},
    ]
    write_csv(OUT / "figures" / "figure_manifest.csv", figure_rows)
    quality = f"""# NIMA Full Draft Quality Checklist

| Item | Status | Note |
|---|---|---|
| Previous short draft deleted | PASS | `reports_260516/nima_paper` was removed and rebuilt |
| IMRAD-style structure | PASS | Introduction, methods/model, results, source/time update, discussion, limitations, conclusions |
| 2605 detailed backbone retained | PASS | Long 2605 NIMA manuscript used through its methods/results/figures core |
| 260516 source update integrated | PASS | SPI diffuse, compact, and V404 benchmarks included; WD/nova excluded |
| Time variation integrated | PASS | Trajectory, altitude/depth, prompt/delayed/total background figures included |
| Claim control | PASS | Diffuse not collapsed to point source; central compact not confirmed identity; production optics not claimed |
| Numbers from machine products | PASS | Values loaded from JSON/CSV by `tools/make_260516_nima_paper.py` |
| Validation status | PASS | Workspace hard checks pass; retained warnings are listed in manuscript |
| Submission readiness | DRAFT | Author list, affiliations, journal formatting, cover letter, and human author review still required |
"""
    (OUT / "quality_checklist.md").write_text(quality, encoding="utf-8")
    (OUT / "submissions" / "v1_nima" / "cover_letter_draft.md").write_text(
        """# Cover Letter Draft

Dear Editors,

We submit a NIM-A instrumentation manuscript describing a validated MEGAlib/Cosima workflow for a balloon-borne focusing 511 keV TES/BGO spectrometer concept. The work emphasizes detector-system simulation, background closure, source coupling, time variation, and explicit claim-control gates rather than an unsupported final astrophysical detection claim.

This draft still requires author names, affiliations, conflict-of-interest declarations, and final journal formatting before submission.
""",
        encoding="utf-8",
    )
    (OUT / "submissions" / "v1_nima" / "title_page_template.md").write_text(
        """# Title Page Template

Title: A full MEGAlib/Cosima background, source-coupling, and time-variation study for a balloon-borne focusing 511 keV TES spectrometer

Authors: TBD

Affiliations: TBD

Corresponding author: TBD
""",
        encoding="utf-8",
    )


def build_papers(v: dict[str, Any]) -> tuple[str, str]:
    en_base = base_until_discussion(R2 / "07_NIMA_MANUSCRIPT" / "tes511_balloon_background_nima_en.md", "en")
    zh_base = base_until_discussion(R2 / "07_NIMA_MANUSCRIPT" / "tes511_balloon_background_nima_zh.md", "zh")
    en = replace_abstract(en_base, abstract_en(v), "en") + additions_en(v)
    zh = replace_abstract(zh_base, abstract_zh(v), "zh") + additions_zh(v)
    return en, zh


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    values = load_values()
    en, zh = build_papers(values)
    (OUT / "tes511_balloon_background_260516_nima_en.md").write_text(en, encoding="utf-8")
    (OUT / "tes511_balloon_background_260516_nima_zh.md").write_text(zh, encoding="utf-8")
    (OUT / "tes511_balloon_background_260516_nima_en.html").write_text(
        markdown_to_html(en, "en", "TES 511 keV Balloon Background 260516 Full NIMA Draft"),
        encoding="utf-8",
    )
    (OUT / "tes511_balloon_background_260516_nima_zh.html").write_text(
        markdown_to_html(zh, "zh-CN", "511 keV TES 气球本底 260516 NIMA 完整稿"),
        encoding="utf-8",
    )
    write_scaffold(en, zh, values)
    readme = """# 260516 Full NIMA Manuscript Package

This directory replaces the discarded short draft.  It is a full bilingual NIMA-style manuscript project built from the detailed 2605 NIMA backbone plus the 260516 SPI source/time update, Phase12 closure, first-principles optics requirement input, validation state, and claim-control gates.

Main files:

- `tes511_balloon_background_260516_nima_en.md`
- `tes511_balloon_background_260516_nima_zh.md`
- `tes511_balloon_background_260516_nima_en.html`
- `tes511_balloon_background_260516_nima_zh.html`
- `references.bib`
- `literature_matrix.csv`
- `quality_checklist.md`
- `00_literature/`, `sections/`, `tables/`, `figures/`, `submissions/`

PDFs are rendered from the HTML files using the existing WeasyPrint environment from the old 2605 tree.
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")
    summary = {
        "status": "PASS_DRAFT_GENERATED",
        "draft_class": "FULL_NIMA_MANUSCRIPT_PROJECT",
        "english_md": "reports_260516/nima_paper/tes511_balloon_background_260516_nima_en.md",
        "chinese_md": "reports_260516/nima_paper/tes511_balloon_background_260516_nima_zh.md",
        "english_lines": len(en.splitlines()),
        "chinese_lines": len(zh.splitlines()),
        "source_time_summary": "reports_260516/source_time_update/source_time_update_summary.json",
        "validation_dependency": "python3 tools/validate_workspace.py",
        "claim_level": "NIMA_FULL_DRAFT_REQUIREMENTS_AND_BACKGROUND_SIMULATION_NOT_FINAL_ASTROPHYSICAL_DETECTABILITY",
        "validation_failures": len(values["validation_failures"]),
        "validation_warnings": [r["check"] for r in values["validation_warnings"]],
    }
    (OUT / "nima_paper_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
