#!/usr/bin/env python3
"""WP00 authority lock for delayed-source authority v2.

This script only records current evidence. It does not launch transport and it
does not modify any Phase-1 authority outputs.
"""

from __future__ import annotations

import csv
import glob
import hashlib
import json
import os
import platform
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PHASE_DIR = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
OUT = PHASE_DIR / "00_manifest"

FIX5_SETUP = (
    "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
BASELINE_SETUP = (
    "outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)


ALLOWLIST: list[dict[str, Any]] = [
    {"path": "AGENTS.md", "role": "contract"},
    {"path": "core_md/fix5_benchmarks.json", "role": "numeric_authority"},
    {"path": "core_md/METHOD_FIX5_SIM_CLOSURE.md", "role": "method_contract"},
    {
        "path": "core_md/balloon511_nima_latex_drafts/revision_harness_runs/harness_20260624_2/HARNESS_ENGINEERING_TES511_DELAYED_SOURCE_AUTHORITY_V2_1_QUICK_CONTEXT.md",
        "role": "phase2_harness",
    },
    {"path": FIX5_SETUP, "role": "geometry_authority"},
    {
        "path": "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo",
        "role": "geometry_authority",
    },
    {
        "path": "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det",
        "role": "detector_map_authority",
    },
    {
        "path": "outputs/reports/user_redesign_multiholeW_fix5_20260621/USER_CYLMAG_REDESIGN_MULTIHOLEW_FIX5_SUMMARY.md",
        "role": "geometry_audit",
    },
    {
        "path": "outputs/reports/user_redesign_multiholeW_fix5_20260621/side_window_material_path_audit_fix5.json",
        "role": "geometry_audit",
    },
    {
        "path": "outputs/reports/user_redesign_multiholeW_fix5_20260621/geometry_det_reference_check.json",
        "role": "geometry_audit",
    },
    {
        "path": "outputs/reports/user_redesign_multiholeW_fix5_20260621/cosima_overlap_fix5_20260621.log",
        "role": "geometry_audit",
    },
    {"path": "config/megalib_sources_fullsphere20_fix5_tilt45/source_migration_manifest.json", "role": "prompt_source_authority"},
    {"glob": "config/megalib_sources_fullsphere20_fix5_tilt45/Background_*_fullsphere20.source", "role": "prompt_source_card"},
    {"path": "code/tools/run_equiv2602_pipeline_NEW_GEO.py", "role": "transport_runner"},
    {"path": "runs/step02_instant_fix5_fullstat_v2/normalization.json", "role": "prompt_run_authority"},
    {"path": "runs/step02_instant_fix5_fullstat_v2/run_manifest.csv", "role": "prompt_run_authority"},
    {"path": "runs/step02_instant_fix5_fullstat_v2/run_summary.csv", "role": "prompt_run_authority"},
    {"path": "runs/step02_buildup_fix5_fullstat_v2/normalization.json", "role": "buildup_run_authority"},
    {"path": "runs/step02_buildup_fix5_fullstat_v2/run_manifest.csv", "role": "buildup_run_authority"},
    {"path": "runs/step02_buildup_fix5_fullstat_v2/run_summary.csv", "role": "buildup_run_authority"},
    {"glob": "runs/step02_buildup_fix5_fullstat_v2/*.dat.inc1.dat", "role": "raw_activation_dat"},
    {"glob": "runs/step02_buildup_fix5_fullstat_v2/*.sim.gz", "role": "raw_activation_sim"},
    {"path": "inputs/nubase/nubase_2020.txt", "role": "nuclear_data_authority"},
    {"path": "engineering/background_validation_20260624/00_manifest/baseline_authority_manifest.json", "role": "phase1_frozen_manifest"},
    {"path": "engineering/background_validation_20260624/01_prompt_source_audit/prompt_normalization_audit.json", "role": "phase1_prompt_audit"},
    {"path": "engineering/background_validation_20260624/01_prompt_source_audit/source_flux_bin_audit.csv", "role": "phase1_prompt_audit"},
    {"path": "code/tools/build_fixed_delay_source.py", "role": "legacy_delayed_builder_comparator"},
    {"path": "code/tools/build_fix5_1of10_exactpos_delayed_source.py", "role": "legacy_exactpos_builder_comparator"},
    {"path": "code/tools/makedecaysourcewithplot_rpip.py", "role": "legacy_radial_builder_comparator"},
    {"path": "runs/step02_decay_source_fix5_fullstat_v2/activation_decay_day15.source", "role": "legacy_delayed_comparator"},
    {"path": "runs/step02_decay_source_fix5_fullstat_v2/activation_inventory_day15.csv", "role": "legacy_delayed_comparator"},
    {"path": "runs/step02_decay_source_fix5_fullstat_v2/normalization_audit_day15.json", "role": "legacy_delayed_comparator"},
    {"path": "runs/step02_delay_fix_fix5_fullstat_v2/activation_decay_day15_groundstate_fixed.source", "role": "legacy_delayed_comparator"},
    {"path": "runs/step02_delay_fix_fix5_fullstat_v2/normalization_audit_groundstate_fix.json", "role": "legacy_delayed_comparator"},
    {"path": "runs/step02_delay_fix_fix5_fullstat_v2/source_fix_summary.json", "role": "legacy_delayed_comparator"},
    {"path": "runs/step02_delay_fix_fix5_fullstat_v2/fix5_fullstat_v2_exactpos_m50000_s260613_delayed_source_manifest.json", "role": "legacy_delayed_comparator"},
    {"path": "runs/step02_delay_fix_fix5_fullstat_v2/exactpos_weighted_rpip_table_m50000_s260613.csv", "role": "legacy_delayed_comparator"},
    {"path": "stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_rates.csv", "role": "step05_current_fix5"},
    {"path": "stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_response_summary.json", "role": "step05_current_fix5"},
    {"path": "outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_w_activation_selected_w2_audit.json", "role": "legacy_selected_decomposition"},
    {"path": "outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_promotion_decision.json", "role": "legacy_promotion_comparator"},
    {"path": "/home/ubuntu/MEGAlib_Install/megalib-main/doc/Cosima.pdf", "role": "installed_megalib_reference", "required": False},
]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_output(args: list[str]) -> str:
    try:
        return subprocess.check_output(args, cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def utc_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat()


def expand_item(item: dict[str, Any]) -> list[Path]:
    if "glob" in item:
        return [Path(p) for p in sorted(glob.glob(str(ROOT / item["glob"])))]
    path = Path(item["path"])
    if not path.is_absolute():
        path = ROOT / path
    return [path]


def file_record(path: Path, role: str, required: bool) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "path": rel(path),
        "role": role,
        "required": required,
        "exists": path.exists(),
        "in_old_tree": rel(path).startswith("old/"),
    }
    if not path.exists():
        return rec
    if path.is_dir():
        files = [p for p in path.rglob("*") if p.is_file()]
        rec.update(
            {
                "type": "directory",
                "file_count": len(files),
                "size_bytes": sum(p.stat().st_size for p in files),
                "mtime_utc": utc_mtime(path),
                "sha256": None,
            }
        )
        return rec
    rec.update(
        {
            "type": "file",
            "size_bytes": path.stat().st_size,
            "mtime_utc": utc_mtime(path),
            "sha256": sha256_file(path),
        }
    )
    return rec


def load_json_rel(path: str) -> Any:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def parse_setup(path: Path) -> dict[str, Any]:
    includes: list[str] = []
    surrounding: list[float] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        bits = raw.split()
        if not bits:
            continue
        if bits[0] == "Include" and len(bits) >= 2:
            includes.append(bits[1])
        if bits[0] == "SurroundingSphere":
            surrounding = [float(x) for x in bits[1:]]
    return {
        "includes": includes,
        "surrounding_sphere_values": surrounding,
        "surrounding_sphere_cm": surrounding[0] if surrounding else None,
    }


def source_card_inventory(paths: list[Path]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    geometry_re = re.compile(r"^\s*Geometry\s+(.+?)\s*$")
    flux_re = re.compile(r"\.Flux\s+([-+0-9.eE]+)")
    radius_re = re.compile(r"farfield[_ -]?radius[_ -]?cm\s*[:=]\s*([-+0-9.eE]+)", re.I)
    for path in sorted(paths):
        txt = path.read_text(encoding="utf-8", errors="ignore")
        geometry_lines = [m.group(1).strip() for m in map(geometry_re.match, txt.splitlines()) if m]
        fluxes = [float(m.group(1)) for m in flux_re.finditer(txt)]
        radius_values = [float(m.group(1)) for m in radius_re.finditer(txt)]
        out.append(
            {
                "path": rel(path),
                "sha256": sha256_file(path),
                "geometry_lines": geometry_lines,
                "contains_fix5_setup": FIX5_SETUP in txt,
                "contains_baseline_setup": BASELINE_SETUP in txt,
                "total_flux_cm2_s": sum(fluxes),
                "farfield_radius_cm_comment_values": sorted(set(radius_values)),
            }
        )
    return out


def count_csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return max(0, sum(1 for _ in csv.reader(handle)) - 1)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    missing: list[str] = []
    for item in ALLOWLIST:
        paths = expand_item(item)
        required = bool(item.get("required", True))
        if not paths:
            rec = {
                "path": item.get("glob") or item.get("path"),
                "role": item["role"],
                "required": required,
                "exists": False,
                "matched_count": 0,
            }
            records.append(rec)
            if required:
                missing.append(str(rec["path"]))
            continue
        for path in paths:
            rec = file_record(path, item["role"], required)
            records.append(rec)
            if required and not rec["exists"]:
                missing.append(str(rec["path"]))

    hashes = sorted(
        (rec["sha256"], rec["path"])
        for rec in records
        if rec.get("exists") and rec.get("sha256")
    )
    (OUT / "file_hashes.sha256").write_text(
        "".join(f"{sha}  {path}\n" for sha, path in hashes),
        encoding="utf-8",
    )

    setup_info = parse_setup(ROOT / FIX5_SETUP)
    source_paths = expand_item({"glob": "config/megalib_sources_fullsphere20_fix5_tilt45/Background_*_fullsphere20.source"})
    source_cards = source_card_inventory(source_paths)

    prompt_audit = load_json_rel("engineering/background_validation_20260624/01_prompt_source_audit/prompt_normalization_audit.json")
    source_manifest = load_json_rel("config/megalib_sources_fullsphere20_fix5_tilt45/source_migration_manifest.json")
    side_audit = load_json_rel("outputs/reports/user_redesign_multiholeW_fix5_20260621/side_window_material_path_audit_fix5.json")
    det_check = load_json_rel("outputs/reports/user_redesign_multiholeW_fix5_20260621/geometry_det_reference_check.json")
    buildup_norm = load_json_rel("runs/step02_buildup_fix5_fullstat_v2/normalization.json")
    instant_norm = load_json_rel("runs/step02_instant_fix5_fullstat_v2/normalization.json")
    legacy_promotion = load_json_rel("outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_promotion_decision.json")

    dat_files = sorted((ROOT / "runs/step02_buildup_fix5_fullstat_v2").glob("*.dat.inc1.dat"))
    sim_files = sorted((ROOT / "runs/step02_buildup_fix5_fullstat_v2").glob("*.sim.gz"))
    raw_missing = []
    if len(dat_files) != 68:
        raw_missing.append(f"expected 68 buildup .dat files, found {len(dat_files)}")
    if len(sim_files) != 68:
        raw_missing.append(f"expected 68 buildup .sim.gz files, found {len(sim_files)}")

    status = "PASS"
    problems: list[str] = []
    if missing:
        status = "BLOCKED_AMBIGUOUS_AUTHORITY"
        problems.append("missing required authority files")
    if raw_missing:
        status = "BLOCKED_RAW_ACTIVATION_PRODUCTS_MISSING"
        problems.extend(raw_missing)
    if prompt_audit.get("status") != "PASS":
        status = "BLOCKED_AMBIGUOUS_AUTHORITY"
        problems.append("Phase-1 prompt audit is not PASS")
    if not side_audit.get("overall_pass") or not det_check.get("pass"):
        status = "BLOCKED_AMBIGUOUS_AUTHORITY"
        problems.append("fix5 geometry audit is not PASS")
    if any(not row["contains_fix5_setup"] or row["contains_baseline_setup"] for row in source_cards):
        status = "BLOCKED_AMBIGUOUS_AUTHORITY"
        problems.append("one or more prompt source cards fails fix5 geometry provenance")

    git_status_short = git_output(["git", "status", "--short"]).splitlines()
    manifest = {
        "artifact_type": "phase2_authority_manifest",
        "harness": "core_md/balloon511_nima_latex_drafts/revision_harness_runs/harness_20260624_2/HARNESS_ENGINEERING_TES511_DELAYED_SOURCE_AUTHORITY_V2_1_QUICK_CONTEXT.md",
        "created_utc": now_utc(),
        "status": status,
        "problems": problems,
        "missing_required_files": missing,
        "git": {
            "head": git_output(["git", "rev-parse", "HEAD"]),
            "branch": git_output(["git", "branch", "--show-current"]),
            "status": "dirty" if git_status_short else "clean",
            "status_short": git_status_short,
        },
        "claim_boundary": "reference-exposure unresolved-line selected-rate estimate",
        "geometry": {
            "setup": FIX5_SETUP,
            "baseline_setup_forbidden_for_new_v2_outputs": BASELINE_SETUP,
            **setup_info,
            "side_window_material_path_audit_overall_pass": bool(side_audit.get("overall_pass")),
            "det_reference_pass": bool(det_check.get("pass")),
        },
        "source_cards": source_cards,
        "prompt_audit_status": prompt_audit.get("status"),
        "prompt_farfield": prompt_audit.get("farfield", {}),
        "source_migration_manifest_status": source_manifest.get("status"),
        "instant_run": {
            "normalization": "runs/step02_instant_fix5_fullstat_v2/normalization.json",
            "farfield_radius_cm": instant_norm.get("farfield_radius_cm"),
            "jobs": instant_norm.get("jobs"),
            "gamma_splits": instant_norm.get("gamma_splits"),
            "non_gamma_replicas": instant_norm.get("non_gamma_replicas"),
        },
        "buildup_run": {
            "normalization": "runs/step02_buildup_fix5_fullstat_v2/normalization.json",
            "farfield_radius_cm": buildup_norm.get("farfield_radius_cm"),
            "jobs": buildup_norm.get("jobs"),
            "gamma_splits": buildup_norm.get("gamma_splits"),
            "non_gamma_replicas": buildup_norm.get("non_gamma_replicas"),
            "dat_file_count": len(dat_files),
            "sim_gz_file_count": len(sim_files),
            "dat_total_bytes": sum(p.stat().st_size for p in dat_files),
            "sim_gz_total_bytes": sum(p.stat().st_size for p in sim_files),
            "run_manifest_rows": count_csv_rows(ROOT / "runs/step02_buildup_fix5_fullstat_v2/run_manifest.csv"),
        },
        "legacy_delayed_comparator": {
            "status": "CURRENT_LEGACY_METHOD_NOT_V2_AUTHORITY",
            "activity_Bq": 85.44920253876245,
            "normalization_audit": "runs/step02_delay_fix_fix5_fullstat_v2/normalization_audit_groundstate_fix.json",
            "source_manifest": "runs/step02_delay_fix_fix5_fullstat_v2/fix5_fullstat_v2_exactpos_m50000_s260613_delayed_source_manifest.json",
            "promotion_decision": legacy_promotion.get("decision"),
            "prompt_cps": legacy_promotion.get("prompt_cps"),
            "delayed_cps": legacy_promotion.get("delayed_cps"),
        },
        "records": records,
    }
    write_json(OUT / "phase2_authority_manifest.json", manifest)

    previous = {
        "status": status,
        "frozen_as_read_only": [
            "fix5 geometry",
            "prompt source cards",
            "prompt/buildup run manifests",
            "Phase-1 prompt normalization audit",
            "legacy delayed source outputs",
            "legacy fix5 Step05-Step08/Step09 reports",
        ],
        "not_v2_authority": [
            "runs/step02_decay_source_fix5_fullstat_v2/activation_inventory_day15.csv",
            "runs/step02_delay_fix_fix5_fullstat_v2/activation_decay_day15_groundstate_fixed.source",
            "runs/step02_delay_fix_fix5_fullstat_v2/activation_decay_day15_groundstate_fixed_exactpos_m50000_s260613.source",
        ],
    }
    write_json(OUT / "previous_phase_frozen_artifacts.json", previous)

    env = {
        "created_utc": now_utc(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cwd": str(ROOT),
        "phase_dir": rel(PHASE_DIR),
        "git_head": manifest["git"]["head"],
        "git_branch": manifest["git"]["branch"],
        "git_status": manifest["git"]["status"],
    }
    write_json(OUT / "execution_environment.json", env)

    summary = {
        "status": status,
        "inputs": [rec["path"] for rec in records if rec.get("exists")],
        "outputs": [
            rel(OUT / "phase2_authority_manifest.json"),
            rel(OUT / "phase2_authority_manifest.md"),
            rel(OUT / "previous_phase_frozen_artifacts.json"),
            rel(OUT / "file_hashes.sha256"),
            rel(OUT / "execution_environment.json"),
            rel(OUT / "decision_log.md"),
        ],
        "findings": [
            f"raw buildup products: {len(dat_files)} dat files, {len(sim_files)} sim.gz files",
            f"Phase-1 prompt audit status: {prompt_audit.get('status')}",
            f"legacy promotion decision retained as comparator: {legacy_promotion.get('decision')}",
        ],
        "claim_impact": [
            "No v2 delayed source has been promoted.",
            "Legacy delayed source remains CURRENT_LEGACY_METHOD comparator only.",
        ],
        "next_gate": "G1 raw state-resolved inventory closure",
        "user_decision_required": False,
    }
    write_json(OUT / "summary.json", summary)

    md = [
        "# WP00 Phase-1 Authority Lock",
        "",
        f"status: `{status}`",
        f"created_utc: `{manifest['created_utc']}`",
        f"git: `{manifest['git']['branch']}` @ `{manifest['git']['head']}` ({manifest['git']['status']})",
        "",
        "## Findings",
        f"- Fix5 setup: `{FIX5_SETUP}`",
        f"- Source cards with fix5 setup: `{sum(1 for row in source_cards if row['contains_fix5_setup'])}/{len(source_cards)}`",
        f"- Raw buildup products: `{len(dat_files)}` `.dat`, `{len(sim_files)}` `.sim.gz`",
        f"- Phase-1 prompt audit: `{prompt_audit.get('status')}`",
        f"- Legacy fix5 delayed comparator: delayed `{legacy_promotion.get('delayed_cps')}` cps, not v2 authority",
        "",
        "## Problems",
    ]
    md.extend(f"- {p}" for p in problems) if problems else md.append("- none")
    (OUT / "phase2_authority_manifest.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (OUT / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (OUT / "decision_log.md").write_text(
        "\n".join(
            [
                f"started_at: {manifest['created_utc']}",
                f"git_head: {manifest['git']['head']}",
                f"git_branch: {manifest['git']['branch']}",
                f"git_status: {manifest['git']['status']}",
                "harness: HARNESS_ENGINEERING_TES511_DELAYED_SOURCE_AUTHORITY_V2_1_QUICK_CONTEXT.md",
                "phase1_harness: HARNESS_ENGINEERING_TES511_BACKGROUND_VALIDATION.md",
                "claim_boundary: reference-exposure unresolved-line selected-rate estimate",
                f"WP00: {status}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"WP00 {status}: wrote {rel(OUT / 'phase2_authority_manifest.json')}")


if __name__ == "__main__":
    main()
