#!/usr/bin/env python3
"""WP00 baseline authority lock for HARNESS_20260624.

This script only reads current authority files and writes derived manifests under
engineering/background_validation_20260624.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
ENG = Path(__file__).resolve().parents[1]
OUT = ENG / "00_manifest"
PACKETS = ENG / "work_packets"
HARNESS = ROOT / "core_md/balloon511_nima_latex_drafts/revision_harness_runs/HARNESS_20260624/HARNESS_ENGINEERING_TES511_BACKGROUND_VALIDATION.md"

FIX5_SETUP = ROOT / "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
FIX5_GEO = ROOT / "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo"
FIX5_DET = ROOT / "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det"
SOURCE_DIR = ROOT / "config/megalib_sources_fullsphere20_fix5_tilt45"
PROMPT_RUN = ROOT / "runs/step02_instant_fix5_fullstat_v2"
BUILDUP_RUN = ROOT / "runs/step02_buildup_fix5_fullstat_v2"
DECAY_SOURCE_RUN = ROOT / "runs/step02_decay_source_fix5_fullstat_v2"
DELAY_FIX_RUN = ROOT / "runs/step02_delay_fix_fix5_fullstat_v2"
STEP05_DIR = ROOT / "stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1"
FINAL_REPORT_DIR = ROOT / "outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613"
STEP05_CODE = ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"
MANUSCRIPT = ROOT / "core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.tex"


def run_text(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except Exception:
        return str(path)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def file_info(path: Path, role: str = "authority") -> dict[str, Any]:
    st = path.stat()
    return {
        "path": rel(path),
        "role": role,
        "sha256": sha256(path),
        "size_bytes": st.st_size,
        "mtime_utc": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
        "in_old_tree": any(part == "old" for part in path.parts),
        "exists": True,
    }


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_setup(path: Path) -> dict[str, Any]:
    includes: list[str] = []
    surrounding: list[float] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith("Include "):
            includes.append(stripped.split(maxsplit=1)[1])
        elif stripped.startswith("SurroundingSphere "):
            nums = []
            for item in stripped.split()[1:]:
                try:
                    nums.append(float(item))
                except ValueError:
                    pass
            surrounding = nums
    radius_candidates = sorted({x for x in surrounding if abs(x - 60.0) < 1e-9})
    return {
        "includes": includes,
        "surrounding_sphere_values": surrounding,
        "surrounding_sphere_cm": radius_candidates[0] if radius_candidates else None,
    }


def prompt_sources() -> list[dict[str, Any]]:
    rows = []
    for path in sorted(SOURCE_DIR.glob("Background_*_fullsphere20.source")):
        text = path.read_text(encoding="utf-8", errors="replace")
        particle = path.name.removeprefix("Background_").removesuffix("_fullsphere20.source")
        flux = sum(float(m.group(1)) for m in re.finditer(r"\.Flux\s+([-+0-9.eE]+)\s*$", text, re.MULTILINE))
        farfield = None
        m = re.search(r"^#\s*farfield_radius_cm\s*=\s*([-+0-9.eE]+)\s*$", text, re.MULTILINE)
        if m:
            farfield = float(m.group(1))
        geom_line = next((line.split(maxsplit=1)[1] for line in text.splitlines() if line.startswith("Geometry ")), "")
        rows.append(
            {
                "particle": particle,
                "path": rel(path),
                "sha256": sha256(path),
                "total_flux_cm2_s": flux,
                "farfield_radius_cm_comment": farfield,
                "geometry_line": geom_line,
            }
        )
    return rows


def run_summary(run_dir: Path) -> dict[str, Any]:
    norm_path = run_dir / "normalization.json"
    manifest_path = run_dir / "run_manifest.csv"
    summary_path = run_dir / "run_summary.csv"
    norm = load_json(norm_path)
    rows = []
    if summary_path.exists():
        with summary_path.open("r", encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
    manifest_rows = []
    if manifest_path.exists():
        with manifest_path.open("r", encoding="utf-8", newline="") as fh:
            manifest_rows = list(csv.DictReader(fh))
    status_counts: dict[str, int] = {}
    for row in rows:
        status_counts[row.get("status", "")] = status_counts.get(row.get("status", ""), 0) + 1
    seeds = [row.get("seed") for row in manifest_rows if row.get("seed")]
    return {
        "manifest": rel(manifest_path),
        "manifest_sha256": sha256(manifest_path) if manifest_path.exists() else None,
        "normalization": rel(norm_path),
        "normalization_sha256": sha256(norm_path) if norm_path.exists() else None,
        "summary": rel(summary_path),
        "summary_sha256": sha256(summary_path) if summary_path.exists() else None,
        "command": (
            "RECONSTRUCTED: python3 code/tools/run_equiv2602_pipeline_NEW_GEO.py "
            f"--mode {norm['mode']} --source-dir {norm['source_dir']} --outdir {norm['outdir']} "
            f"--gamma-events {norm['gamma_events']} --gamma-splits {norm['gamma_splits']} "
            f"--non-gamma-replicas {norm['non_gamma_replicas']} "
            f"--farfield-radius-cm {norm['farfield_radius_cm']} --allow-heavy-run"
        ),
        "command_status": "RECONSTRUCTED_FROM_NORMALIZATION_AND_RUN_MANIFEST",
        "jobs": norm.get("jobs"),
        "status_counts": status_counts,
        "farfield_radius_cm": norm.get("farfield_radius_cm"),
        "farfield_area_cm2": norm.get("farfield_area_cm2"),
        "gamma_splits": norm.get("gamma_splits"),
        "non_gamma_replicas": norm.get("non_gamma_replicas"),
        "selected_particles": norm.get("selected_particles"),
        "unique_seed_count": len(set(seeds)),
        "seed_count": len(seeds),
    }


def collect_hash_files() -> list[Path]:
    files: list[Path] = [
        HARNESS,
        FIX5_SETUP,
        FIX5_GEO,
        FIX5_DET,
        ROOT / "outputs/reports/user_redesign_multiholeW_fix5_20260621/USER_CYLMAG_REDESIGN_MULTIHOLEW_FIX5_SUMMARY.md",
        ROOT / "outputs/reports/user_redesign_multiholeW_fix5_20260621/side_window_material_path_audit_fix5.json",
        ROOT / "outputs/reports/user_redesign_multiholeW_fix5_20260621/geometry_det_reference_check.json",
        SOURCE_DIR / "source_migration_manifest.json",
        ROOT / "code/tools/run_equiv2602_pipeline_NEW_GEO.py",
        PROMPT_RUN / "normalization.json",
        PROMPT_RUN / "run_manifest.csv",
        PROMPT_RUN / "run_summary.csv",
        BUILDUP_RUN / "normalization.json",
        BUILDUP_RUN / "run_manifest.csv",
        BUILDUP_RUN / "run_summary.csv",
        DECAY_SOURCE_RUN / "activation_decay_day15.source",
        DECAY_SOURCE_RUN / "activation_inventory_day15.csv",
        DECAY_SOURCE_RUN / "normalization_audit_day15.json",
        DELAY_FIX_RUN / "activation_decay_day15_groundstate_fixed.source",
        DELAY_FIX_RUN / "activation_decay_day15_groundstate_fixed_exactpos_m50000_s260613.source",
        DELAY_FIX_RUN / "normalization_audit_groundstate_fix.json",
        DELAY_FIX_RUN / "source_fix_summary.json",
        DELAY_FIX_RUN / "fix5_fullstat_v2_exactpos_m50000_s260613_delayed_source_manifest.json",
        DELAY_FIX_RUN / "exactpos_weighted_rpip_table_m50000_s260613.csv",
        STEP05_CODE,
        STEP05_DIR / "step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_response_summary.json",
        STEP05_DIR / "step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_rates.csv",
        STEP05_DIR / "prompt_normalization_audit.json",
        STEP05_DIR / "work/event_catalog.pkl",
        FINAL_REPORT_DIR / "fix5_promotion_decision.json",
        FINAL_REPORT_DIR / "fix5_final_closure_report.json",
        FINAL_REPORT_DIR / "fix5_delayed_source_exactpos_summary.json",
        FINAL_REPORT_DIR / "fix5_w_activation_selected_w2_audit.json",
        MANUSCRIPT,
        ROOT / "core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.md",
        ROOT / "core_md/balloon511_nima_latex_drafts/paper_evidence_manifest_20260623.json",
        ROOT / "core_md/balloon511_nima_latex_drafts/source_normalization_audit_20260623.json",
        ROOT / "core_md/balloon511_nima_latex_drafts/simulation_config_authority_20260623.json",
        ROOT / "core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260623_delay_processing_reaudit_3agent/11_fix5_w2_prompt_delayed_energy_band_stats.md",
    ]
    files.extend(sorted(SOURCE_DIR.glob("Background_*_fullsphere20.source")))
    files.extend(sorted((PROMPT_RUN / "job_sources").glob("*.source")))
    files.extend(sorted((BUILDUP_RUN / "job_sources").glob("*.source")))
    return [p for p in files if p.exists()]


def write_work_packets() -> None:
    PACKETS.mkdir(parents=True, exist_ok=True)
    (PACKETS / "WP00_baseline_authority_lock.md").write_text(
        """# WP00 Baseline Authority Lock

## Goal
Lock current fix5/CsI baseline geometry, source, run, delayed, Step05, and manuscript authority without modifying authority outputs.

## Allowed inputs
- outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/
- config/megalib_sources_fullsphere20_fix5_tilt45/
- runs/step02_instant_fix5_fullstat_v2/
- runs/step02_buildup_fix5_fullstat_v2/
- runs/step02_decay_source_fix5_fullstat_v2/
- runs/step02_delay_fix_fix5_fullstat_v2/
- stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/
- outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/
- core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.tex

## Forbidden reads/writes
- Do not write outside engineering/background_validation_20260624/.
- Do not modify outputs/, runs/, stepwise_maintenance/, config/, old/, or manuscript source.

## Required outputs
- 00_manifest/baseline_authority_manifest.json
- 00_manifest/baseline_authority_manifest.md
- 00_manifest/file_hashes.sha256
- 00_manifest/execution_environment.json
- 00_manifest/decision_log.md

## Acceptance criteria
- Current authority paths are unique and all required hashes are present.

## Stop states
- PASS
- BLOCKED_AMBIGUOUS_AUTHORITY

## Max attempts
2 implementation attempts, 1 deterministic validation-fix retry.
""",
        encoding="utf-8",
    )
    (PACKETS / "WP01_prompt_source_audit.md").write_text(
        """# WP01 Prompt Source Normalization Audit

## Goal
Audit current fix5 prompt source units, angular bins, far-field radius, area, splits, replicas, seeds, and selected-rate closure.

## Allowed inputs
- config/megalib_sources_fullsphere20_fix5_tilt45/
- runs/step02_instant_fix5_fullstat_v2/
- stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/
- old/code/tools/build_v3p5_centerfinger_step05_l1_response.py
- /home/ubuntu/MEGAlib_Install/megalib-main/src/cosima/src/MCSource.cc

## Forbidden reads/writes
- Do not write outside engineering/background_validation_20260624/01_prompt_source_audit/.
- Do not modify source cards, Step05 outputs, manuscript source, or authority reports.

## Required outputs
- summary.json
- summary.md
- source_card_inventory.csv
- source_flux_bin_audit.csv
- prompt_normalization_audit.json
- prompt_normalization_audit.md
- prompt_weight_closure.csv
- farfield_geometry_audit.json
- farfield_geometry_audit.md

## Acceptance criteria
- Radius authority unique.
- Source flux bin sum relative closure <= 1e-8.
- Generated counts, replicas, and seeds complete.
- Independent selected-rate reconstruction relative difference <= 1e-6.
- Area/projected-area handling has local code evidence.
- All rates carry sum_w2.

## Stop states
- PASS
- WARN
- BLOCKED_SOURCE_SEMANTICS
- BLOCKED_RADIUS_MISMATCH
- FAIL_NORMALIZATION

## Max attempts
2 implementation attempts, 1 deterministic validation-fix retry.
""",
        encoding="utf-8",
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    write_work_packets()

    git_head = run_text(["git", "rev-parse", "HEAD"])
    git_status_short = run_text(["git", "status", "--short"])
    git_status_label = "clean" if not git_status_short else "dirty"
    started = datetime.now(timezone.utc).isoformat()

    decision_log = OUT / "decision_log.md"
    decision_log.write_text(
        "\n".join(
            [
                f"started_at: {started}",
                f"git_head: {git_head}",
                f"git_status: {git_status_label}",
                f"harness: {rel(HARNESS)}",
                "",
                "# Decision Log",
                "",
                "- WP00 started: authority discovery and hashing only.",
                "- No baseline authority outputs, run outputs, Step05 outputs, config source cards, or manuscript sources were modified.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    setup = parse_setup(FIX5_SETUP)
    src_manifest = load_json(SOURCE_DIR / "source_migration_manifest.json")
    step05 = load_json(STEP05_DIR / "step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_response_summary.json")
    delayed_summary = load_json(FINAL_REPORT_DIR / "fix5_delayed_source_exactpos_summary.json")
    promotion = load_json(FINAL_REPORT_DIR / "fix5_promotion_decision.json")

    required = [
        FIX5_SETUP,
        FIX5_GEO,
        FIX5_DET,
        SOURCE_DIR / "source_migration_manifest.json",
        PROMPT_RUN / "normalization.json",
        PROMPT_RUN / "run_manifest.csv",
        PROMPT_RUN / "run_summary.csv",
        BUILDUP_RUN / "normalization.json",
        BUILDUP_RUN / "run_manifest.csv",
        BUILDUP_RUN / "run_summary.csv",
        DELAY_FIX_RUN / "normalization_audit_groundstate_fix.json",
        STEP05_CODE,
        STEP05_DIR / "step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_response_summary.json",
        STEP05_DIR / "step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_rates.csv",
        STEP05_DIR / "work/event_catalog.pkl",
        MANUSCRIPT,
    ]
    missing = [rel(p) for p in required if not p.exists()]

    warnings: list[str] = []
    if src_manifest.get("label") == "fix5_1of10":
        warnings.append("source_migration_manifest label is fix5_1of10 although the same source directory is reused by fullstat runs; run normalization files carry fullstat labels.")
    if git_status_short:
        warnings.append("worktree is dirty; manifest records current file hashes as authority for this harness run.")

    stale_artifacts = [
        {
            "path": "old/",
            "authority_status": "ARCHIVED_SUPPORT",
            "reason": "Harness and fix5 contract allow old/ only for code archaeology/provenance unless a current manifest explicitly points there.",
        },
        {
            "path": "outputs/reports/fix5_1of10/",
            "authority_status": "COMPARISON_ONLY",
            "reason": "1/10 screen is superseded for current paper-facing full-stat values by fix5_fullstat_v2_exactpos_m50000_s260613.",
        },
    ]

    files = collect_hash_files()
    hash_lines = [f"{sha256(p)}  {rel(p)}" for p in files]
    (OUT / "file_hashes.sha256").write_text("\n".join(hash_lines) + "\n", encoding="utf-8")

    env = {
        "created_utc": started,
        "git_head": git_head,
        "git_status": git_status_label,
        "git_status_short": git_status_short.splitlines(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "hostname": platform.node(),
        "cwd": str(ROOT),
    }
    (OUT / "execution_environment.json").write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    status = "PASS" if not missing else "BLOCKED_AMBIGUOUS_AUTHORITY"
    manifest = {
        "artifact_type": "baseline_authority_manifest",
        "harness": rel(HARNESS),
        "created_utc": started,
        "status": status,
        "warnings": warnings,
        "missing_required_files": missing,
        "git": {"head": git_head, "status": git_status_label, "status_short": git_status_short.splitlines()},
        "geometry": file_info(FIX5_GEO),
        "detector_map": file_info(FIX5_DET),
        "setup": {**file_info(FIX5_SETUP), **setup},
        "geometry_audits": {
            "side_window_material_path_audit": file_info(ROOT / "outputs/reports/user_redesign_multiholeW_fix5_20260621/side_window_material_path_audit_fix5.json"),
            "det_reference_check": file_info(ROOT / "outputs/reports/user_redesign_multiholeW_fix5_20260621/geometry_det_reference_check.json"),
            "overlap_log": rel(ROOT / "outputs/reports/user_redesign_multiholeW_fix5_20260621/cosima_overlap_fix5_20260621.log"),
        },
        "prompt_sources": prompt_sources(),
        "prompt_source_manifest": file_info(SOURCE_DIR / "source_migration_manifest.json"),
        "prompt_run": run_summary(PROMPT_RUN),
        "buildup_run": run_summary(BUILDUP_RUN),
        "delayed_source": {
            "path": rel(DELAY_FIX_RUN / "activation_decay_day15_groundstate_fixed_exactpos_m50000_s260613.source"),
            "activity_Bq": delayed_summary.get("fixed_total_activity_Bq") or delayed_summary.get("source_total_activity_Bq"),
            "sha256": sha256(DELAY_FIX_RUN / "activation_decay_day15_groundstate_fixed_exactpos_m50000_s260613.source"),
            "manifest": rel(DELAY_FIX_RUN / "fix5_fullstat_v2_exactpos_m50000_s260613_delayed_source_manifest.json"),
            "weighted_rpip_table": rel(DELAY_FIX_RUN / "exactpos_weighted_rpip_table_m50000_s260613.csv"),
            "normalization_audit": rel(DELAY_FIX_RUN / "normalization_audit_groundstate_fix.json"),
        },
        "step05": {
            "code": rel(STEP05_CODE),
            "code_sha256": sha256(STEP05_CODE),
            "outputs": [
                rel(STEP05_DIR / "step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_response_summary.json"),
                rel(STEP05_DIR / "step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_rates.csv"),
                rel(STEP05_DIR / "prompt_normalization_audit.json"),
                rel(STEP05_DIR / "work/event_catalog.pkl"),
            ],
            "inputs": step05.get("inputs", {}),
            "active_veto_threshold_keV": step05.get("normalization", {}).get("active_veto_threshold_keV"),
            "coincidence_window_s": step05.get("normalization", {}).get("coincidence_window_s"),
        },
        "promotion_authority": {
            "path": rel(FINAL_REPORT_DIR / "fix5_promotion_decision.json"),
            "sha256": sha256(FINAL_REPORT_DIR / "fix5_promotion_decision.json"),
            "decision": promotion.get("decision"),
            "B_cps": promotion.get("B_cps"),
            "prompt_cps": promotion.get("prompt_cps"),
            "delayed_cps": promotion.get("delayed_cps"),
        },
        "manuscript": {
            "path": rel(MANUSCRIPT),
            "sha256": sha256(MANUSCRIPT),
            "authority_basis": "balloon511_nima_revision_harness_20260622.md states balloon511_nima_draft_en.tex is the sole writable source of truth; derived markdown is review output.",
        },
        "manuscript_alternates": [
            {"path": rel(ROOT / "core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.md"), "role": "generated_review_artifact"},
            {"path": rel(ROOT / "core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_zh.tex"), "role": "out_of_scope_translation_for_this_harness"},
        ],
        "stale_artifacts": stale_artifacts,
        "hash_inventory": {
            "path": rel(OUT / "file_hashes.sha256"),
            "files_hashed": len(files),
        },
    }
    (OUT / "baseline_authority_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    md = [
        "# Baseline Authority Manifest",
        "",
        f"- status: `{status}`",
        f"- git head: `{git_head}`",
        f"- git status: `{git_status_label}`",
        f"- fix5 setup: `{rel(FIX5_SETUP)}`",
        f"- source dir: `{rel(SOURCE_DIR)}`",
        f"- prompt run: `{rel(PROMPT_RUN)}`",
        f"- buildup run: `{rel(BUILDUP_RUN)}`",
        f"- delayed source: `{manifest['delayed_source']['path']}`",
        f"- Step05 summary: `{rel(STEP05_DIR / 'step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_response_summary.json')}`",
        f"- manuscript source: `{rel(MANUSCRIPT)}`",
        "",
        "## Warnings",
    ]
    md.extend([f"- {w}" for w in warnings] or ["- none"])
    md.extend(
        [
            "",
            "## Gate G0",
            "",
            "G0 is PASS if `missing_required_files` is empty. Candidate historical outputs under `old/` are marked archived support, not current authority.",
        ]
    )
    (OUT / "baseline_authority_manifest.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps({"status": status, "manifest": rel(OUT / "baseline_authority_manifest.json"), "files_hashed": len(files)}, indent=2))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
