#!/usr/bin/env python3
"""Read-only validator for the consolidated S3c mainline and legacy cleanup."""

from __future__ import annotations

import csv
import gzip
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
GEOOPT = ROOT / "engineering/geometry_optimization_20260704"
WORK = Path(__file__).resolve().parents[1]
EXPECTED_GEOMETRY = (
    "engineering/geometry_optimization_20260704/29_geoopt_s3c_bgo_w2mm_al3mm_shell_20260709/"
    "geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
PROMPT = ROOT / "runs/geometry_optimization_20260704/s3c_bgo_w2mm_al3mm_shell_eqstats_prompt_eplus_n_20260709"
ATM = ROOT / "runs/geometry_optimization_20260704/s3c_bgo_w2mm_al3mm_shell_atm511_sidecar_3m_20260709"
ATM_NAME = "Atm511SidecarS3cBgoW2mmAl3mmShell3M"
DOMINANT = GEOOPT / "32_s3c_dominant_backgrounds_20260709/dominant_background_summary.json"
ATM_SUMMARY = GEOOPT / "32_s3c_dominant_backgrounds_20260709/s3c_atm511_sidecar_3m_summary.json"
DELAYED = (
    GEOOPT
    / "38_s3c_neutron_delayed_chain_m50000_clean_20260710"
    / "s3c_bgo_w2mm_al3mm_shell_neutron_delay_m50000_clean_20260710_campaign_manifest.json"
)
ANALYSIS = WORK / "data/s3c_mainline_analysis_summary.json"
REPORT_HTML = WORK / "report/s3c_lightweight_report.html"
REPORT_PAYLOAD = WORK / "report/s3c_lightweight_report_payload.json"
REPORT_QA = WORK / "report/s3c_lightweight_report_qa.json"
CANDIDATES = WORK / "data/s3c_lightweight_candidates.csv"

LEGACY_RUN_NAMES = {
    "s3a_bgo_barrel_atm511_sidecar_3m_20260709",
    "s3a_bgo_barrel_eqstats_prompt_eplus_n_20260709",
    "s3b_w2mm_al3mm_shell_atm511_sidecar_3m_20260709",
    "s3b_w2mm_al3mm_shell_eqstats_prompt_eplus_n_20260709",
    "s3_csi_barrel_atm511_sidecar_3m_20260709",
    "s3_csi_barrel_eqstats_prompt_eplus_n_20260709",
    "s3_csi_barrel_eqstats_prompt_other_20260709",
    "s3_csi_barrel_eqstats_prompt_other_emup_20260709",
    "step02_buildup_s3_csi_barrel_fullstat_v1_20260709",
    "step02_decay_source_s3_csi_barrel_fullstat_v1_20260709",
    "step02_delayed_transport_s3_csi_barrel_fullstat_v1_20260709",
    "step02_delay_exactpos_s3_csi_barrel_fullstat_v1_20260709",
    "step02_delay_fix_s3_csi_barrel_fullstat_v1_20260709",
    "step02_instant_s3_csi_barrel_fullstat_v1_20260709",
    "step09_focus_s3_csi_barrel_fullstat_v1_20260709",
}
LEGACY_ENGINEERING_DIRS = (
    "21_geoopt_s3_csi_barrel_20260709",
    "22_s3_eqstats_prompt_atm511_20260709",
    "23_s3_delayed_chain_m50000_20260709",
    "24_s3_vs_mass511_step05_sensitivity_20260709",
    "25_s3_vs_mass511_with_atm511_20260709",
    "26_s3_mass511_gpt_pro_background_packet_20260709",
    "27_geoopt_s3a_bgo_barrel_20260709",
    "28_geoopt_s3b_w2mm_al3mm_shell_20260709",
    "30_s3a_dominant_backgrounds_20260709",
    "31_s3b_dominant_backgrounds_20260709",
    "36_s3a_neutron_delayed_chain_m50000_clean_20260710",
    "37_s3b_neutron_delayed_chain_m50000_clean_20260710",
)
LEGACY_REMOVED_PATHS = (
    GEOOPT / "33_s3a_neutron_delayed_chain_m50000_20260710",
    GEOOPT / "34_s3b_neutron_delayed_chain_m50000_20260710",
    ROOT / "stepwise_maintenance/step05_veto_time_axis/outputs_s3_csi_barrel_fullstat_v1_20260709_l1",
    GEOOPT / "build_s3abc_full_visuals_20260709.py",
    GEOOPT / "build_s3abc_geometry_variants_20260709.py",
    GEOOPT / "run_s3abc_neutron_delayed_chain_20260710.py",
    GEOOPT / "validate_s3abc_dominant_backgrounds_20260709.py",
    GEOOPT / "validate_s3abc_neutron_delayed_20260710.py",
    GEOOPT / "S3ABC_DOMINANT_BACKGROUND_RUN_PLAN_20260709.md",
    GEOOPT / "S3ABC_NEUTRON_DELAYED_RUN_PLAN_20260710.md",
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def norm(value: str | None) -> str | None:
    if not value:
        return None
    path = Path(str(value).strip())
    if not path.is_absolute():
        path = ROOT / path
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def source_geometry(path: Path) -> str | None:
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line.startswith("Geometry "):
            return line.split(None, 1)[1]
    return None


def sim_geometry(path: Path) -> str | None:
    with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if line.startswith("Geometry "):
                return line.split(None, 1)[1]
            if line == "SE":
                return None
    return None


def main() -> int:
    problems: list[str] = []
    checks: dict[str, Any] = {}

    expected = norm(EXPECTED_GEOMETRY)
    prompt_rows = load_json(PROMPT / "run_summary.json") if (PROMPT / "run_summary.json").exists() else []
    selected = [row for row in prompt_rows if row.get("particle") in {"eplus", "n"}]
    prompt_bad = []
    for row in selected:
        sim = ROOT / row["sim_path"]
        if row.get("status") not in {"PASS", "SKIP"} or not sim.exists() or norm(sim_geometry(sim)) != expected:
            prompt_bad.append(row.get("job_name"))
    if len(selected) != 16 or prompt_bad:
        problems.append(f"prompt jobs/geometry failed: jobs={len(selected)} bad={prompt_bad}")
    checks["prompt"] = {"jobs": len(selected), "bad": prompt_bad}

    atm_source = ATM / f"{ATM_NAME}.source"
    atm_sim = ATM / f"{ATM_NAME}.inc1.id1.sim.gz"
    atm_log = ATM / f"cosima_{ATM_NAME}.log"
    atm_summary = load_json(ATM_SUMMARY)
    atm_ok = (
        atm_source.exists()
        and atm_sim.exists()
        and atm_log.exists()
        and norm(source_geometry(atm_source)) == expected
        and norm(sim_geometry(atm_sim)) == expected
        and atm_summary.get("status") == "PASS_S3C_ATM511_4PI_SIDECAR_REPLAY"
        and (atm_summary.get("transport") or {}).get("status") == "PASS_COSIMA_TRANSPORT_COMPLETE"
    )
    if not atm_ok:
        problems.append("atm511 source/SIM/log/summary gate failed")
    checks["atm511"] = {"ok": atm_ok}

    dominant = load_json(DOMINANT)
    geometry_checks = dominant.get("geometry_verification") or {}
    dominant_ok = (
        dominant.get("status") == "PASS_S3C_DOMINANT_BACKGROUNDS_EPLUS_N_ATM511"
        and (geometry_checks.get("source_cards") or {}).get("all_match") is True
        and (geometry_checks.get("prompt_sim_headers") or {}).get("all_match") is True
        and (geometry_checks.get("atm511") or {}).get("all_match") is True
    )
    if not dominant_ok:
        problems.append("dominant background summary gate failed")
    checks["dominant"] = {"ok": dominant_ok}

    delayed = load_json(DELAYED)
    fixed = delayed.get("fixed_source") or {}
    exact = delayed.get("exactpos_source") or {}
    transport_rows = delayed.get("delayed_transport") or []
    transport = transport_rows[0] if len(transport_rows) == 1 else {}
    audit_path = ROOT / fixed.get("normalization_audit", "")
    audit = load_json(audit_path) if audit_path.exists() else {}
    audit_rows = audit.get("rows") or []
    neutron_audit_ok = (
        len(audit_rows) == 1
        and audit_rows[0].get("tag") == "n"
        and audit_rows[0].get("files") == 8
        and float(audit_rows[0].get("division", 0)) == 8.0
        and audit_rows[0].get("tt_line_count") == 8
    )
    delayed_ok = (
        str(delayed.get("status", "")).startswith("PASS")
        and fixed.get("normalization_status") == "PASS"
        and neutron_audit_ok
        and exact.get("sampling_status") == "PASS"
        and exact.get("n_pointsource_blocks") == 50000
        and transport.get("SE") == 1_000_000
        and transport.get("ID") == 1_000_000
        and norm(transport.get("geometry")) == expected
    )
    if not delayed_ok:
        problems.append("neutron-only delayed normalization/transport gate failed")
    checks["delayed"] = {"ok": delayed_ok, "neutron_audit_ok": neutron_audit_ok}

    analysis = load_json(ANALYSIS)
    analysis_ok = (
        analysis.get("status") == "PASS_S3C_MAINLINE_LIGHTWEIGHT_ANALYSIS"
        and abs(float(analysis["validation"]["activation_flux_sum_delta_bq"])) < 2e-6
    )
    if not analysis_ok:
        problems.append("mainline analysis output gate failed")
    checks["analysis"] = {"ok": analysis_ok}

    report_ok = False
    report_detail: dict[str, Any] = {}
    if REPORT_HTML.exists() and REPORT_PAYLOAD.exists() and REPORT_QA.exists() and CANDIDATES.exists():
        report_html = REPORT_HTML.read_text(encoding="utf-8")
        report_payload = load_json(REPORT_PAYLOAD)
        report_qa = load_json(REPORT_QA)
        with CANDIDATES.open(encoding="utf-8", newline="") as handle:
            candidate_rows = list(csv.DictReader(handle))
        charts = report_payload.get("charts") or []
        chart_by_id = {chart.get("id"): chart for chart in charts}
        background_payload = (
            chart_by_id.get("s3c-background-components", {}).get("dataset", {}).get("data", [])
        )
        activation_payload = (
            chart_by_id.get("s3c-activation-volume-classes", {}).get("dataset", {}).get("data", [])
        )
        mass_payload = chart_by_id.get("s3c-lightweight-mass", {}).get("dataset", {}).get("data", [])
        background_expected = [
            float(row["rate_cps"]) * 1000.0 for row in analysis["background"]["component_rows"]
        ]
        activation_expected = [
            float(row["activity_bq"]) for row in analysis["activation"]["volume_classes"]
        ]
        mass_expected = [float(row["mass_kg_pre_relief"]) for row in candidate_rows]
        background_actual = [float(row["rate_1e3_cps"]) for row in background_payload]
        activation_actual = [float(row["activity_bq"]) for row in activation_payload]
        mass_actual = [float(row["mass_kg"]) for row in mass_payload]
        section_roles = (
            "title",
            "technical-summary",
            "key-findings",
            "scope-data-and-metric-definitions",
            "methodology",
            "limitations-uncertainty-and-robustness-checks",
            "recommended-next-steps",
            "further-questions",
        )
        section_positions = [
            report_html.find(f'data-contract-section="{role}"') for role in section_roles
        ]
        remote_dependencies = re.findall(
            r'<(?:script|link)\b[^>]+(?:src|href)=["\']https?://',
            report_html,
            flags=re.IGNORECASE,
        )
        report_ok = (
            len(charts) == 3
            and len(background_actual) == len(background_expected)
            and len(activation_actual) == len(activation_expected)
            and len(mass_actual) == len(mass_expected)
            and all(abs(a - b) < 1e-12 for a, b in zip(background_actual, background_expected))
            and all(abs(a - b) < 1e-12 for a, b in zip(activation_actual, activation_expected))
            and all(abs(a - b) < 1e-12 for a, b in zip(mass_actual, mass_expected))
            and report_qa.get("status") == "PASS"
            and all(position >= 0 for position in section_positions)
            and section_positions == sorted(section_positions)
            and not remote_dependencies
            and "<!-- DATA_ANALYTICS_HTML_REPORT_RUNTIME -->" not in report_html
        )
        report_detail = {
            "charts": len(charts),
            "qa_status": report_qa.get("status"),
            "section_map_order_ok": section_positions == sorted(section_positions),
            "remote_dependencies": remote_dependencies,
            "payload_matches_analysis": (
                background_actual == background_expected
                and activation_actual == activation_expected
                and mass_actual == mass_expected
            ),
        }
    if not report_ok:
        problems.append("self-contained technical report/payload/render QA gate failed")
    checks["report"] = {"ok": report_ok, **report_detail}

    run_root = ROOT / "runs/geometry_optimization_20260704"
    remaining_legacy_runs = sorted(path.name for path in run_root.iterdir() if path.is_dir() and path.name in LEGACY_RUN_NAMES)
    remaining_legacy_runs.extend(
        sorted(
            path.name
            for path in run_root.iterdir()
            if path.is_dir()
            and any(token in path.name for token in ("s3a", "s3b", "s3_csi"))
            and "s3c" not in path.name
        )
    )
    remaining_legacy_runs = sorted(set(remaining_legacy_runs))
    if remaining_legacy_runs:
        problems.append(f"legacy run directories remain: {remaining_legacy_runs}")
    checks["legacy_runs"] = {"remaining": remaining_legacy_runs}

    non_markdown_legacy_files = []
    retained_markdown = []
    for name in LEGACY_ENGINEERING_DIRS:
        directory = GEOOPT / name
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() == ".md":
                retained_markdown.append(path.relative_to(ROOT).as_posix())
            else:
                non_markdown_legacy_files.append(path.relative_to(ROOT).as_posix())
    if non_markdown_legacy_files:
        problems.append(f"legacy engineering non-document files remain: {len(non_markdown_legacy_files)}")
    if len(retained_markdown) != 27:
        problems.append(f"legacy retained conclusion count changed: {len(retained_markdown)} != 27")
    checks["legacy_engineering"] = {
        "retained_markdown_count": len(retained_markdown),
        "non_markdown_remaining": non_markdown_legacy_files,
    }

    legacy_removed_remaining = [path.relative_to(ROOT).as_posix() for path in LEGACY_REMOVED_PATHS if path.exists()]
    if legacy_removed_remaining:
        problems.append(f"explicit legacy removal targets remain: {legacy_removed_remaining}")
    checks["legacy_explicit_removals"] = {"remaining": legacy_removed_remaining}

    payload = {
        "status": "PASS_S3C_MAINLINE_AND_LEGACY_CLEANUP" if not problems else "FAIL_S3C_MAINLINE_AND_LEGACY_CLEANUP",
        "checks": checks,
        "problems": problems,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if not problems else 2


if __name__ == "__main__":
    raise SystemExit(main())
