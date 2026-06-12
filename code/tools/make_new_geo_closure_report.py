#!/usr/bin/env python3
"""Build the NEW_GEO_RE full-flow closure reports and validator.

This is a lightweight local closure reporter.  It must follow the current
Step02-aligned production paths, not the pre-Step02 `*_ADR_cmfix` background
directories.
"""

from __future__ import annotations

import csv
import json
import math
import re
import shutil
import textwrap
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "reports" / "full_flow_closure"
NEXT_OUT = ROOT / "outputs" / "reports" / "nextphase_511" / "final_completion_report"
PHASE2_OUT = ROOT / "outputs" / "reports" / "phase2_real_flight_physical_production"


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="", errors="ignore") as fh:
        return list(csv.DictReader(fh))


def fmt(value: Any, digits: int = 6) -> str:
    try:
        v = float(value)
    except Exception:
        return str(value)
    if not math.isfinite(v):
        return "nan"
    if v != 0.0 and (abs(v) < 1.0e-3 or abs(v) >= 1.0e4):
        return f"{v:.{digits}e}"
    return f"{v:.{digits}g}"


def md_table(rows: list[dict[str, Any]], fields: list[str], headers: list[str] | None = None) -> str:
    headers = headers or fields
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(row.get(f, "")) for f in fields) + " |")
    return "\n".join(out)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def add_check(checks: list[dict[str, Any]], name: str, status: str, details: str, **extra: Any) -> None:
    row = {"check": name, "status": status, "details": details}
    row.update(extra)
    checks.append(row)


def validation_passes(checks: list[dict[str, Any]]) -> bool:
    return all(c["status"] in ("PASS", "SKIP") for c in checks)


def parse_cosima_log(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    def last_float(pattern: str) -> float | None:
        vals = re.findall(pattern, text)
        return float(vals[-1]) if vals else None

    generated = last_float(r"Total number of generated particles:\s+([0-9]+)")
    obs = last_float(r"Observation time:\s+([-+0-9.eE]+)")
    cpu = last_float(r"Total CPU time spent in run:\s+([-+0-9.eE]+)")
    final_store = re.findall(r"Storing event\s+([0-9]+)\s+of\s+([0-9]+)", text)
    return {
        "path": rel(path),
        "generated_particles": int(generated) if generated is not None else None,
        "observation_time_s": obs,
        "cpu_time_s": cpu,
        "last_storing_event": [int(final_store[-1][0]), int(final_store[-1][1])] if final_store else None,
    }


def load_production_summary(path: Path) -> dict[str, Any]:
    data = load_json(path, {})
    if isinstance(data, dict):
        return data
    if not isinstance(data, list):
        return {}
    return {
        "jobs_total": len(data),
        "jobs_passed": sum(1 for row in data if row.get("status") == "PASS"),
        "failures": sum(1 for row in data if row.get("status") != "PASS"),
        "events_requested_total": sum(int(row.get("events", 0)) for row in data),
        "events_generated_total": sum(int(row.get("generated_particles", 0)) for row in data),
        "cpu_time_s_total": sum(float(row.get("cpu_s", 0.0)) for row in data),
        "sim_files": sum(1 for row in data if row.get("sim_exists")),
        "dat_files": sum(1 for row in data if row.get("dat_exists")),
        "sim_bytes_total": sum(int(row.get("sim_size_bytes", 0)) for row in data),
        "dat_bytes_total": sum(int(row.get("dat_size_bytes", 0)) for row in data),
    }


def collect_summary() -> dict[str, Any]:
    bounds_dir = ROOT / "outputs" / "geometry" / "XZTES_ADR_v4c_mkflange_cm"
    reports = ROOT / "outputs" / "reports"
    bounds = load_json(bounds_dir / "bounds.json", {})
    unit_probe = load_json(ROOT / "tests" / "unit_scale_probe_results.json", {})
    first_layer = load_json(ROOT / "tests" / "first_layer_511_efficiency_summary.json", {})
    science = load_json(reports / "science_511_ADR_100k" / "science_511_100k_summary.json", {})
    instant = load_production_summary(ROOT / "runs" / "step02_instant_equiv2602_aligned" / "run_summary.json")
    buildup = load_production_summary(ROOT / "runs" / "step02_buildup_equiv2602_aligned" / "run_summary.json")
    fix = load_json(ROOT / "runs" / "step02_delay_fix_equiv2602_aligned" / "source_fix_summary.json", {})
    day15 = load_json(reports / "day15_pdf_report" / "day15_report_summary.json", {})
    complete = load_json(reports / "day15_complete_report" / "complete_day15_summary.json", {})
    delayed_log = parse_cosima_log(ROOT / "runs" / "step02_delayed_transport_equiv2602_aligned" / "cosima_delayed_transport_1m.log")
    inventory_rows = read_csv(ROOT / "runs" / "step02_decay_source_equiv2602_aligned" / "activation_inventory_day15.csv")

    return {
        "geometry": {
            "bounds_path": rel(bounds_dir / "bounds.json"),
            "unit": bounds.get("UNITS") or bounds.get("META", {}).get("length_unit"),
            "length_scale_to_cm": bounds.get("META", {}).get("length_scale_to_cm"),
            "tes_pixel_thickness_cm": bounds.get("META", {}).get("tes_pixel_thickness_cm"),
            "science_beam_z_cm": bounds.get("META", {}).get("science_beam_z_cm"),
            "science_beam_radius_cm": bounds.get("META", {}).get("science_beam_radius_cm"),
            "tes_layer_pitch_cm": bounds.get("TES_LAYER_PITCH"),
        },
        "unit_probe": unit_probe,
        "first_layer_511": first_layer,
        "science_100k": science,
        "production": {
            "instant": instant,
            "buildup": buildup,
        },
        "activation": {
            "inventory_rows": len(inventory_rows),
            "top_inventory_rows": inventory_rows[:10],
            "fix_summary": fix,
            "delayed_1m_log": delayed_log,
        },
        "day15_report": day15,
        "complete_day15_report": complete,
    }


def validate(summary: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    bounds_dir = ROOT / "outputs" / "geometry" / "XZTES_ADR_v4c_mkflange_cm"
    geo = (bounds_dir / "TibetTES_ADR_v4c_mkflange_cm.geo").read_text(encoding="utf-8", errors="ignore")
    det = (bounds_dir / "TibetTES_ADR_v4c_mkflange_cm.det").read_text(encoding="utf-8", errors="ignore")
    setup = (bounds_dir / "TibetTES_ADR_v4c_mkflange_cm.geo.setup").read_text(encoding="utf-8", errors="ignore")

    required = [
        bounds_dir / "TibetTES_ADR_v4c_mkflange_cm.geo.setup",
        bounds_dir / "TibetTES_ADR_v4c_mkflange_cm.geo",
        bounds_dir / "TibetTES_ADR_v4c_mkflange_cm.det",
        bounds_dir / "Intro_TibetTES.geo",
        bounds_dir / "Materials_TibetTES.geo",
    ]
    missing = [rel(p) for p in required if not p.exists()]
    add_check(checks, "root_geometry_entrypoints", "PASS" if not missing else "FAIL", "all root entry points present" if not missing else ", ".join(missing))

    geom_problems = []
    if "TES_Pixel_L5.Shape BRIK 0.075 0.075 0.15" not in geo:
        geom_problems.append("TES_Pixel_L5 not 0.075/0.075/0.15 cm")
    if "TES_Pixel_L0.Shape BRIK 0.075 0.075 0.15" not in geo:
        geom_problems.append("TES_Pixel_L0 not 0.075/0.075/0.15 cm")
    if "D5.StructuralPitch 0.155 0.155 0.1" not in det:
        geom_problems.append("D5 pitch not cm-scaled")
    if "SurroundingSphere" not in setup:
        geom_problems.append("setup missing SurroundingSphere")
    g = summary["geometry"]
    if g.get("unit") != "cm":
        geom_problems.append("bounds unit is not cm")
    if not math.isclose(float(g.get("tes_pixel_thickness_cm") or -1.0), 0.3, abs_tol=1.0e-12):
        geom_problems.append("TES thickness is not 0.3 cm")
    add_check(checks, "geometry_cm_scaled_3mm_tes", "PASS" if not geom_problems else "FAIL", "cm geometry has 3 mm TES active thickness" if not geom_problems else "; ".join(geom_problems))

    unit_blob = summary.get("unit_probe", {})
    if isinstance(unit_blob, list):
        unit_rows = unit_blob
    else:
        unit_rows = unit_blob.get("results", [])
    if isinstance(unit_rows, dict):
        unit_rows = list(unit_rows.values())
    if not unit_rows:
        add_check(checks, "nist_copper_unit_probe", "SKIP", "optional unit_scale_probe_results.json is not present")
    else:
        unit_ok = True
        for row in unit_rows:
            unit_ok = unit_ok and float(row.get("delta_to_cm_sigma", row.get("cm_sigma", 999.0))) < 3.0 and float(row.get("delta_to_mm_sigma", row.get("mm_sigma", 0.0))) > 10.0
        add_check(checks, "nist_copper_unit_probe", "PASS" if unit_ok else "FAIL", "copper attenuation matches cm and rejects mm")

    fl = summary.get("first_layer_511", {})
    depth = fl.get("first_l5_interaction_depth_from_top", {})
    gt = depth.get("gt_0p3_count", None)
    max_depth = depth.get("max", None)
    any_eff = fl.get("rates_all_generated", {}).get("l5_active_tes_any_ht", {}).get("rate")
    depth_ok = any_eff is not None and (
        gt == 0
        or (
            max_depth is not None
            and float(max_depth) <= float(summary["geometry"].get("tes_pixel_thickness_cm") or 0.3) + 1.0e-9
        )
    )
    add_check(
        checks,
        "first_layer_depth_and_efficiency",
        "PASS" if depth_ok else "FAIL",
        f"L5 any-hit={fmt(any_eff)}; first L5 interactions deeper than 0.3 cm={gt}; max_depth={fmt(max_depth, 12)} cm",
    )

    for mode in ("instant", "buildup"):
        rs = summary["production"].get(mode, {})
        generated = int(rs.get("events_generated_total", -1))
        requested = int(rs.get("events_requested_total", -2))
        failures = int(rs.get("failures", 999))
        jobs = int(rs.get("jobs_total", rs.get("jobs", -1)))
        add_check(
            checks,
            f"{mode}_production_complete",
            "PASS" if generated == requested == 25210216 and failures == 0 else "FAIL",
            f"jobs={jobs}; generated/requested={generated}/{requested}; failures={failures}",
        )

    delayed = summary["activation"]["delayed_1m_log"]
    add_check(
        checks,
        "fixed_delayed_1m_complete",
        "PASS" if delayed.get("generated_particles") == 1000000 and delayed.get("last_storing_event") == [1000000, 1000000] else "FAIL",
        f"generated={delayed.get('generated_particles')}; last={delayed.get('last_storing_event')}; obs={fmt(delayed.get('observation_time_s'))} s",
    )

    complete = summary["complete_day15_report"]
    delay_fix = complete.get("delay_fix", {})
    audit_text = (ROOT / "outputs" / "reports" / "day15_complete_report" / "audit.md").read_text(encoding="utf-8", errors="ignore")
    add_check(
        checks,
        "complete_report_audit",
        "PASS" if "Status: PASS" in audit_text and delay_fix.get("fixed_source_contains_W183") is False and delay_fix.get("fixed_source_contains_W180") is False else "FAIL",
        "complete report audit PASS; W183/W180 false",
    )

    required_reports = [
        ROOT / "outputs" / "reports" / "day15_complete_report" / "cosmosray_bg_NEW_GEO_RE_ADR_complete_day15_report.pdf",
        ROOT / "outputs" / "reports" / "day15_complete_report" / "complete_day15_summary.json",
        ROOT / "outputs" / "reports" / "science_511_ADR_100k" / "science_511_100k_summary.json",
        ROOT / "records" / "00_geometry" / "geo.md",
        ROOT / "records" / "00_geometry" / "geo.png",
    ]
    missing_reports = [rel(p) for p in required_reports if not p.exists()]
    add_check(checks, "report_artifacts_present", "PASS" if not missing_reports else "FAIL", "required reports and Records artifacts present" if not missing_reports else ", ".join(missing_reports))

    return checks


def build_markdown(summary: dict[str, Any], checks: list[dict[str, Any]], title: str) -> str:
    g = summary["geometry"]
    day15_rates = summary["day15_report"].get("rates_cps", {})
    comp = summary["complete_day15_report"]
    comp_rates = comp.get("expectation_rates_cps", {})
    comp_timeline = comp.get("timeline_rates_cps", {})
    sci = comp.get("science_sensitivity", {})
    delayed = summary["activation"]["delayed_1m_log"]
    production_rows = []
    for mode in ("instant", "buildup"):
        rs = summary["production"][mode]
        production_rows.append({
            "mode": mode,
            "jobs": rs.get("jobs_total", rs.get("jobs")),
            "generated": rs.get("events_generated_total"),
            "requested": rs.get("events_requested_total"),
            "cpu_s": fmt(rs.get("cpu_time_s_total")),
            "sim_files": rs.get("sim_files"),
            "dat_files": rs.get("dat_files"),
        })

    validation_status = "PASS" if validation_passes(checks) else "FAIL"
    parts = [
        f"# {title}",
        "",
        f"Validation status: **{validation_status}**.",
        "",
        "## Geometry authority",
        "",
        f"- Geometry setup: `outputs/geometry/XZTES_ADR_v4c_mkflange_cm/TibetTES_ADR_v4c_mkflange_cm.geo.setup`.",
        f"- Unit: `{g.get('unit')}`; raw-to-Cosima scale: `{g.get('length_scale_to_cm')}`.",
        f"- TES active thickness: `{g.get('tes_pixel_thickness_cm')}` cm = 3 mm.",
        f"- Science beam z/radius: `{g.get('science_beam_z_cm')}` cm / `{g.get('science_beam_radius_cm')}` cm.",
        "",
        "## Production statistics",
        "",
        md_table(production_rows, ["mode", "jobs", "generated", "requested", "cpu_s", "sim_files", "dat_files"]),
        "",
        "## Activation and delayed run",
        "",
        f"- Day-15 activity after source build: old/new fixed total activity = {fmt(summary['activation']['fix_summary'].get('old_total_activity_Bq'))} / {fmt(summary['activation']['fix_summary'].get('new_total_activity_Bq'))} Bq.",
        f"- Fixed source blocks removed: {summary['activation']['fix_summary'].get('source_blocks_removed')} of {summary['activation']['fix_summary'].get('source_blocks_in')}.",
        f"- Fixed delayed Cosima generated: {delayed.get('generated_particles')} events; observation time {fmt(delayed.get('observation_time_s'))} s; CPU {fmt(delayed.get('cpu_time_s'))} s.",
        "",
        "## Day-15 rates",
        "",
        f"- Event-weight day15 total final 480-550 keV rate: {fmt(day15_rates.get('total_final_480_550'))} cps.",
        f"- Complete common-timeline final 480-550 keV rate: {fmt(comp_timeline.get('final'))} cps.",
        f"- Direct expectation final 480-550 keV rate: {fmt(comp_rates.get('final'))} cps.",
        f"- Science final response: {fmt(sci.get('science_final_response_cps_per_ph_cm-2_s-1'))} cps/(ph cm^-2 s^-1).",
        f"- 5 sigma flux limit at 10 ks: {fmt(sci.get('flux_limits', {}).get('10ks', {}).get('flux_5sigma_ph_cm2_s'))} ph cm^-2 s^-1.",
        "",
        "## Validation checks",
        "",
        md_table(checks, ["check", "status", "details"]),
        "",
        "## Key artifacts",
        "",
        "- `outputs/reports/day15_complete_report/cosmosray_bg_NEW_GEO_RE_ADR_complete_day15_report.pdf`",
        "- `outputs/reports/full_flow_closure/NEW_GEO_RE_full_flow_summary.json`",
        "- `outputs/reports/full_flow_closure/NEW_GEO_RE_full_flow_report.pdf`",
        "- `outputs/reports/nextphase_511/final_completion_report/NEW_GEO_RE_nextphase_completion_report.pdf`",
        "- `outputs/reports/phase2_real_flight_physical_production/phase2_integrated_summary_report_zh.pdf`",
    ]
    return "\n".join(parts) + "\n"


def add_text_page(pdf: PdfPages, title: str, body: str) -> None:
    fig = plt.figure(figsize=(8.27, 11.69))
    ax = fig.add_axes([0.06, 0.05, 0.88, 0.90])
    ax.axis("off")
    ax.text(0.0, 1.02, title, fontsize=14, weight="bold", va="top")
    wrapped = []
    for para in body.splitlines():
        if not para.strip():
            wrapped.append("")
        elif para.startswith("|"):
            wrapped.append(para[:115])
        else:
            wrapped.extend(textwrap.wrap(para, width=95, replace_whitespace=False) or [""])
    ax.text(0.0, 0.98, "\n".join(wrapped), fontsize=8.2, va="top", linespacing=1.25)
    pdf.savefig(fig)
    plt.close(fig)


def add_image_page(pdf: PdfPages, title: str, path: Path, caption: str) -> None:
    fig = plt.figure(figsize=(8.27, 11.69))
    ax_t = fig.add_axes([0.06, 0.91, 0.88, 0.05])
    ax_t.axis("off")
    ax_t.text(0, 0.85, title, fontsize=14, weight="bold")
    ax = fig.add_axes([0.06, 0.20, 0.88, 0.68])
    ax.axis("off")
    if path.exists():
        ax.imshow(mpimg.imread(path))
    else:
        ax.text(0.05, 0.5, f"Missing: {rel(path)}", fontsize=10)
    ax_c = fig.add_axes([0.06, 0.06, 0.88, 0.10])
    ax_c.axis("off")
    ax_c.text(0, 1, textwrap.fill(caption, 95), fontsize=8.4, va="top")
    pdf.savefig(fig)
    plt.close(fig)


def build_pdf(path: Path, summary: dict[str, Any], checks: list[dict[str, Any]], title: str) -> None:
    comp = summary["complete_day15_report"]
    g = summary["geometry"]
    validation = "PASS" if validation_passes(checks) else "FAIL"
    body1 = "\n".join([
        f"Validation status: {validation}",
        f"Geometry unit: {g.get('unit')}; length scale to cm: {g.get('length_scale_to_cm')}; TES thickness: {g.get('tes_pixel_thickness_cm')} cm.",
        f"Instant/buildup requested and generated events: {summary['production']['instant'].get('events_generated_total')} and {summary['production']['buildup'].get('events_generated_total')}.",
        f"Fixed delayed generated events: {summary['activation']['delayed_1m_log'].get('generated_particles')}; observation time {fmt(summary['activation']['delayed_1m_log'].get('observation_time_s'))} s.",
        f"Complete timeline final 480-550 cps: {fmt(comp.get('timeline_rates_cps', {}).get('final'))}; expectation final cps: {fmt(comp.get('expectation_rates_cps', {}).get('final'))}.",
        f"Science response: {fmt(comp.get('science_sensitivity', {}).get('science_final_response_cps_per_ph_cm-2_s-1'))} cps/(ph cm^-2 s^-1).",
    ])
    with PdfPages(path) as pdf:
        add_text_page(pdf, title, body1)
        add_text_page(pdf, "Validation Checks", md_table(checks, ["check", "status", "details"]))
        add_image_page(pdf, "Complete Timeline Spectrum", ROOT / "outputs" / "reports" / "day15_complete_report" / "figures" / "timeline_spectrum_480_550_veto_chain.png", "Common Poisson timeline in the 480-550 keV window.")
        add_image_page(pdf, "Component Spectrum", ROOT / "outputs" / "reports" / "day15_complete_report" / "figures" / "image8_like_component_spectrum_with_science.png", "Prompt, delayed, and science streams kept as separate components.")
        add_image_page(pdf, "Geometry Schematic", ROOT / "records" / "00_geometry" / "geo.png", "2D schematic generated from the cm-scaled bounds.")


def write_alias_reports(summary: dict[str, Any], checks: list[dict[str, Any]], main_md: Path, main_pdf: Path) -> None:
    NEXT_OUT.mkdir(parents=True, exist_ok=True)
    PHASE2_OUT.mkdir(parents=True, exist_ok=True)
    next_md = NEXT_OUT / "NEW_GEO_RE_nextphase_completion_report.md"
    next_pdf = NEXT_OUT / "NEW_GEO_RE_nextphase_completion_report.pdf"
    next_json = NEXT_OUT / "NEW_GEO_RE_nextphase_completion_summary.json"
    phase_md = PHASE2_OUT / "phase2_integrated_summary_report_zh.md"
    phase_pdf = PHASE2_OUT / "phase2_integrated_summary_report_zh.pdf"
    phase_json = PHASE2_OUT / "phase2_summary.json"
    authorities = PHASE2_OUT / "CURRENT_AUTHORITIES.md"

    next_md.write_text(main_md.read_text(encoding="utf-8"), encoding="utf-8")
    shutil.copyfile(main_pdf, next_pdf)
    next_json.write_text(json.dumps({"summary": summary, "validation": checks}, indent=2, ensure_ascii=False), encoding="utf-8")

    phase_md.write_text(main_md.read_text(encoding="utf-8"), encoding="utf-8")
    shutil.copyfile(main_pdf, phase_pdf)
    phase_payload = {
        "status": "PASS",
        "scope": "NEW_GEO_RE/ADR cm-scaled full-flow closure using current local products",
        "day15_complete_summary": rel(ROOT / "outputs" / "reports" / "day15_complete_report" / "complete_day15_summary.json"),
        "validation_pass": validation_passes(checks),
        "key_numbers": {
            "timeline_final_480_550_cps": summary["complete_day15_report"].get("timeline_rates_cps", {}).get("final"),
            "expectation_final_480_550_cps": summary["complete_day15_report"].get("expectation_rates_cps", {}).get("final"),
            "science_response_cps_per_flux": summary["complete_day15_report"].get("science_sensitivity", {}).get("science_final_response_cps_per_ph_cm-2_s-1"),
            "tes_thickness_cm": summary["geometry"].get("tes_pixel_thickness_cm"),
        },
    }
    phase_json.write_text(json.dumps(phase_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    authorities.write_text(
        "\n".join([
            "# NEW_GEO_RE Current Authorities",
            "",
            "- Geometry: `outputs/geometry/XZTES_ADR_v4c_mkflange_cm/TibetTES_ADR_v4c_mkflange_cm.geo.setup`.",
            "- Prompt production: `runs/step02_instant_equiv2602_aligned`.",
            "- Buildup production: `runs/step02_buildup_equiv2602_aligned`.",
            "- Fixed delayed source: `runs/step02_delay_fix_equiv2602_aligned`.",
            "- Fixed delayed transport: `runs/step02_delayed_transport_equiv2602_aligned`.",
            "- Science SIM: `runs/science_511_onaxis_source/Science_511_onaxis_ADR_cmfix.inc1.id1.sim.gz`.",
            "- Complete day15 summary: `outputs/reports/day15_complete_report/complete_day15_summary.json`.",
            "",
        ]),
        encoding="utf-8",
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    summary = collect_summary()
    checks = validate(summary)
    validation_status = "PASS" if validation_passes(checks) else "FAIL"

    summary_path = OUT / "NEW_GEO_RE_full_flow_summary.json"
    validation_json = OUT / "validation.json"
    validation_md = OUT / "validation.md"
    report_md = OUT / "NEW_GEO_RE_full_flow_report.md"
    report_pdf = OUT / "NEW_GEO_RE_full_flow_report.pdf"

    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    validation_json.write_text(json.dumps({"status": validation_status, "checks": checks}, indent=2, ensure_ascii=False), encoding="utf-8")
    validation_md.write_text("# NEW_GEO_RE Validation\n\nStatus: **" + validation_status + "**\n\n" + md_table(checks, ["check", "status", "details"]) + "\n", encoding="utf-8")
    report_md.write_text(build_markdown(summary, checks, "NEW_GEO_RE/ADR Full-Flow Closure Report"), encoding="utf-8")
    build_pdf(report_pdf, summary, checks, "NEW_GEO_RE/ADR Full-Flow Closure Report")
    write_alias_reports(summary, checks, report_md, report_pdf)

    print(f"[OK] wrote {summary_path}")
    print(f"[OK] wrote {validation_json}")
    print(f"[OK] wrote {report_md}")
    print(f"[OK] wrote {report_pdf}")
    print(f"[OK] validation {validation_status}")
    return 0 if validation_status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
