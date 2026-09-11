#!/usr/bin/env python3
"""Build fix5 full-stat pre-MC release artifacts.

This is intentionally narrow: it turns already prepared runner manifests and
job source cards into the machine-readable artifacts required before launching
clean full-stat fix5 prompt/buildup transport.  It does not run Cosima.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "config" / "megalib_sources_fullsphere20_fix5_tilt45"
TEMPLATE_SOURCE_DIR = ROOT / "config" / "megalib_sources_fullsphere20_v3p5_centerfinger_tilt45"
FIX5_GEO = (
    "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
BASELINE_GEO = (
    "outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
FIX5_REPORT_1OF10 = ROOT / "outputs" / "reports" / "fix5_1of10"
SOURCE_RE = re.compile(r"Background_(?P<tag>.+?)_fullsphere20\.source$")
FLUX_RE = re.compile(r"\.Flux\s+([-+0-9.eE]+)\s*$")
EVENTS_RE = re.compile(r"\.Events\s+([0-9]+)\s*$")
SEED_RE = re.compile(r"^Seed\s+([0-9]+)\s*$")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def source_tag(path: Path) -> str:
    match = SOURCE_RE.match(path.name)
    if not match:
        raise ValueError(f"Unexpected source filename: {path}")
    return match.group("tag")


def parse_source_card(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    flux = 0.0
    events: int | None = None
    seed: int | None = None
    geometry_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("Geometry "):
            geometry_lines.append(stripped)
        flux_match = FLUX_RE.search(line)
        if flux_match:
            flux += float(flux_match.group(1))
        events_match = EVENTS_RE.search(line)
        if events_match and events is None:
            events = int(events_match.group(1))
        seed_match = SEED_RE.match(stripped)
        if seed_match:
            seed = int(seed_match.group(1))
    geometry = geometry_lines[0].split(maxsplit=1)[1] if geometry_lines else None
    tag = source_tag(path)
    return {
        "path": rel(path),
        "template": rel(TEMPLATE_SOURCE_DIR / path.name),
        "source_family": tag,
        "geometry_setup": geometry,
        "events_in_base_card": events,
        "seed_in_base_card": seed,
        "total_flux_cm2_s": flux,
        "contains_fix5_geometry": FIX5_GEO in text,
        "contains_forbidden_baseline_geometry": BASELINE_GEO in text,
    }


def read_run_manifest(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def events_by_particle(rows: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        out[row["particle"]] = out.get(row["particle"], 0) + int(row["events"])
    return dict(sorted(out.items()))


def mode_summary(mode: str, run_dir: Path) -> dict[str, Any]:
    normalization_path = run_dir / "normalization.json"
    manifest_path = run_dir / "run_manifest.csv"
    normalization = load_json(normalization_path)
    rows = read_run_manifest(manifest_path)
    expected_sim = [Path(row["sim_path"]) for row in rows]
    expected_dat = [Path(row["dat_path"]) for row in rows]
    job_sources = [Path(row["temp_source"]) for row in rows]
    existing_outputs = [
        rel(path)
        for path in [*expected_sim, *expected_dat]
        if path.exists()
    ]
    return {
        "run_dir": rel(run_dir),
        "normalization_json": rel(normalization_path),
        "run_manifest_csv": rel(manifest_path),
        "job_source_dir": rel(run_dir / "job_sources"),
        "jobs": len(rows),
        "job_sources": [rel(path) for path in job_sources],
        "events_requested_by_particle": events_by_particle(rows),
        "events_requested_total": sum(int(row["events"]) for row in rows),
        "gamma_events": normalization["gamma_events"],
        "gamma_splits": normalization["gamma_splits"],
        "non_gamma_replicas": normalization["non_gamma_replicas"],
        "farfield_radius_cm": normalization["farfield_radius_cm"],
        "farfield_area_cm2": normalization["farfield_area_cm2"],
        "gamma_prompt_time_s_with_farfield_area": normalization["gamma_prompt_time_s_with_farfield_area"],
        "seed_map": [
            {
                "job_name": row["job_name"],
                "particle": row["particle"],
                "seed": int(row["seed"]),
            }
            for row in rows
        ],
        "expected_sim_outputs": [rel(path) for path in expected_sim],
        "expected_dat_outputs": [rel(path) for path in expected_dat],
        "mc_outputs_existing_now": existing_outputs,
        "resource_estimate_from_smoke": normalization.get("resource_estimate_from_smoke", {}),
    }


def compare_with_v3p5_fullstat(mode: str, fix5_events: dict[str, int]) -> dict[str, Any]:
    base_dir = ROOT / "runs" / f"step02_{mode}_v3p5_centerfinger_fullstat_v2"
    manifest = base_dir / "run_manifest.csv"
    if not manifest.exists():
        return {"status": "V3P5_FULLSTAT_MANIFEST_NOT_FOUND", "path": rel(manifest)}
    base_events = events_by_particle(read_run_manifest(manifest))
    ratios: dict[str, Any] = {}
    for particle, fix_events in fix5_events.items():
        base = base_events.get(particle)
        ratios[particle] = {
            "fix5_requested_events": fix_events,
            "v3p5_fullstat_v2_requested_events": base,
            "ratio_vs_v3p5_fullstat_v2": (fix_events / base) if base else None,
        }
    return {"status": "COMPARED_TO_V3P5_FULLSTAT_V2", "ratios": ratios}


def count_text_hits(paths: list[Path], needle: str) -> int:
    count = 0
    for path in paths:
        if needle in path.read_text(encoding="utf-8", errors="replace"):
            count += 1
    return count


def build_artifacts(label: str) -> None:
    report_dir = ROOT / "outputs" / "reports" / label
    instant_dir = ROOT / "runs" / "step02_instant_fix5_fullstat_v2"
    buildup_dir = ROOT / "runs" / "step02_buildup_fix5_fullstat_v2"
    source_migration = load_json(SOURCE_DIR / "source_migration_manifest.json")
    source_cards = [parse_source_card(path) for path in sorted(SOURCE_DIR.glob("Background_*_fullsphere20.source"))]
    modes = {
        "instant": mode_summary("instant", instant_dir),
        "buildup": mode_summary("buildup", buildup_dir),
    }
    generated_at = now_utc()
    particles = [card["source_family"] for card in source_cards]
    flux_by_particle = {
        card["source_family"]: card["total_flux_cm2_s"]
        for card in source_cards
    }
    all_expected_sim = [
        path
        for mode in modes.values()
        for path in mode["expected_sim_outputs"]
    ]
    all_expected_dat = [
        path
        for mode in modes.values()
        for path in mode["expected_dat_outputs"]
    ]

    source_manifest = {
        "label": label,
        "status": "PRE_MC_FULLSTAT_SOURCE_PROVENANCE_READY",
        "generated_by": "code/tools/build_fix5_fullstat_release.py",
        "generated_at_utc": generated_at,
        "geometry_setup": FIX5_GEO,
        "forbidden_baseline_geometry_setup": BASELINE_GEO,
        "source_cards": source_cards,
        "source_family": {
            "name": "EXPACS/PARMA fullsphere20 atmospheric source cards",
            "particles": particles,
            "template_directory": rel(TEMPLATE_SOURCE_DIR),
            "fix5_directory": rel(SOURCE_DIR),
            "use_for": [
                "full-stat prompt instant transport source templates",
                "full-stat activation buildup transport source templates",
            ],
        },
        "far_field_or_surrounding_sphere": {
            "source_surface": source_migration.get("source_surface", "FarFieldAreaSource"),
            "radius_cm": source_migration.get("farfield_radius_cm", modes["instant"]["farfield_radius_cm"]),
            "area_cm2": math.pi * float(source_migration.get("farfield_radius_cm", modes["instant"]["farfield_radius_cm"])) ** 2,
            "theta_phi_binning": "20 equal-mu theta bins covering 0-180 deg; phi 0-360 deg for every bin",
            "coordinate_frame": "global zenith frame, unchanged from v3p5 centerfinger tilt45 templates",
            "pointing_policy": source_migration.get("pointing_policy"),
        },
        "normalization_constants": {
            "flux_units": "cm^-2 s^-1 per FarFieldAreaSource bin",
            "total_flux_cm2_s_by_particle": flux_by_particle,
            "gamma_norm_factor_cm2_s_per_count": load_json(instant_dir / "normalization.json")[
                "gamma_norm_factor_cm2_s_per_count"
            ],
            "non_gamma_combined_norm_factor_cm2_s_per_count": load_json(instant_dir / "normalization.json")[
                "non_gamma_combined_norm_factor_cm2_s_per_count"
            ],
            "source_card_flux_and_farfield_policy": "Unchanged from v3p5 centerfinger tilt45 templates; only geometry setup path was changed.",
            "prompt_rate_normalization_expected_downstream": "Step05 must use 1/sum(TT) from fix5 full-stat prompt SIM TimeTags.",
            "delayed_rate_normalization_expected_downstream": "Delayed source must be rebuilt from fix5 full-stat activation buildup with NUBASE ground-state correction, per-family TT division guard, and exact-position M-sampling inventory audit.",
        },
        "event_or_exposure_ratio": {
            "planned_label": label,
            "runner_preflight_manifest": rel(report_dir / "fix5_runner_preflight_manifest.json"),
            "actual_runner_event_counts": {
                mode: modes[mode]["events_requested_by_particle"]
                for mode in modes
            },
            "comparison_vs_v3p5_fullstat_v2": {
                mode: compare_with_v3p5_fullstat(mode, modes[mode]["events_requested_by_particle"])
                for mode in modes
            },
            "summary": "Clean full-stat profile: gamma_events=10,000,000, gamma_splits=12, non_gamma_replicas=8, farfield_radius_cm=60.",
        },
        "random_seed_policy": {
            "runner_rule": "seed = 1000003 + ordinal * 7919 within each mode; the seed map is recorded in the preflight manifest.",
            "instant_and_buildup_seed_maps": {
                mode: modes[mode]["seed_map"]
                for mode in modes
            },
        },
        "expected_sim_outputs": all_expected_sim,
        "expected_dat_outputs": all_expected_dat,
        "mode_run_dirs": {
            mode: modes[mode]["run_dir"]
            for mode in modes
        },
    }
    write_json(report_dir / "fix5_source_manifest.json", source_manifest)

    preflight = {
        "label": label,
        "status": "PRE_MC_FULLSTAT_RUN_MANIFESTS_AND_JOB_SOURCES_PREPARED_NO_MC",
        "generated_at_utc": generated_at,
        "source_manifest": rel(report_dir / "fix5_source_manifest.json"),
        "fix5_source_dir": rel(SOURCE_DIR),
        "modes": modes,
    }
    write_json(report_dir / "fix5_runner_preflight_manifest.json", preflight)

    benchmark_alignment = {
        "label": label,
        "status": "OLD_NEW_GEO_RE_REPORT_ONLY_FOR_FULLSTAT_RELEASE",
        "generated_at_utc": generated_at,
        "new_geo_re_source_or_report_paths": [
            "core_md/fix5_benchmarks.json",
            "core_md/HANDOFF_20260617.md",
        ],
        "line_window_definition": "NOT_ALIGNED_FOR_OLD_NEW_GEO_RE",
        "active_shield_thresholds": "NOT_ALIGNED_FOR_OLD_NEW_GEO_RE",
        "compton_fov_definition": "NOT_ALIGNED_FOR_OLD_NEW_GEO_RE",
        "source_surface_or_far_field_normalization": "NOT_ALIGNED_FOR_OLD_NEW_GEO_RE; fix5 uses FarFieldAreaSource radius_cm=60.",
        "rate_units_and_time_normalization": "Fix5 Step05 will use 1/sum(TT) prompt and delayed SIM TE; old new_geo_re selection/normalization remains unverified.",
        "selection_equivalence_status": "UNVERIFIED",
        "normalization_equivalence_status": "UNVERIFIED",
        "decision": "NOT_ALIGNED",
        "gate_consequence": "Old new_geo_re prompt_total_cps and delayed_total_cps may be reported as historical context only, not used as pass/fail gates.",
    }
    write_json(report_dir / "fix5_benchmark_alignment.json", benchmark_alignment)

    source_paths = [ROOT / card["path"] for card in source_cards]
    job_source_paths = [
        ROOT / path
        for mode in modes.values()
        for path in mode["job_sources"]
    ]
    source_fix5_hits = count_text_hits(source_paths, FIX5_GEO)
    source_baseline_hits = count_text_hits(source_paths, BASELINE_GEO)
    job_fix5_hits = count_text_hits(job_source_paths, FIX5_GEO)
    job_baseline_hits = count_text_hits(job_source_paths, BASELINE_GEO)
    one_tenth_summary = FIX5_REPORT_1OF10 / "fix5_step05_screen_summary.json"
    one_tenth = load_json(one_tenth_summary)
    one_tenth_gate = one_tenth.get("gate_interpretation", {})
    existing_mc_outputs = [
        path
        for mode in modes.values()
        for path in [*mode["expected_sim_outputs"], *mode["expected_dat_outputs"]]
        if (ROOT / path).exists()
    ]
    rows = [
        {
            "check": "fullstat_source_cards_geometry",
            "status": "PASS" if source_fix5_hits == len(source_paths) and source_baseline_hits == 0 else "FAIL",
            "evidence_path": rel(SOURCE_DIR),
            "blocking": True,
            "details": {
                "source_cards": len(source_paths),
                "contains_fix5_geometry": source_fix5_hits,
                "contains_forbidden_baseline_geometry": source_baseline_hits,
            },
        },
        {
            "check": "fullstat_job_sources_geometry",
            "status": "PASS" if job_fix5_hits == len(job_source_paths) and job_baseline_hits == 0 else "FAIL",
            "evidence_path": f"{modes['instant']['job_source_dir']}; {modes['buildup']['job_source_dir']}",
            "blocking": True,
            "details": {
                "job_sources": len(job_source_paths),
                "contains_fix5_geometry": job_fix5_hits,
                "contains_forbidden_baseline_geometry": job_baseline_hits,
            },
        },
        {
            "check": "fullstat_run_manifests_prepared",
            "status": "PASS" if modes["instant"]["jobs"] == 68 and modes["buildup"]["jobs"] == 68 else "FAIL",
            "evidence_path": f"{modes['instant']['run_manifest_csv']}; {modes['buildup']['run_manifest_csv']}",
            "blocking": True,
            "details": {
                "instant_jobs": modes["instant"]["jobs"],
                "buildup_jobs": modes["buildup"]["jobs"],
                "instant_events": modes["instant"]["events_requested_total"],
                "buildup_events": modes["buildup"]["events_requested_total"],
                "gamma_events": modes["instant"]["gamma_events"],
                "gamma_splits": modes["instant"]["gamma_splits"],
                "non_gamma_replicas": modes["instant"]["non_gamma_replicas"],
            },
        },
        {
            "check": "statistics_escalation_basis_from_1of10",
            "status": "PASS"
            if one_tenth_gate.get("rate_gate_decision") == "INCONCLUSIVE_LOW_STAT_ZERO_SELECTED_EVENTS_NOT_FINAL_PASS"
            and one_tenth_gate.get("hard_fail_status") == "NO_HARD_FAIL_OBSERVED"
            else "FAIL",
            "evidence_path": rel(one_tenth_summary),
            "blocking": True,
            "details": {
                "rate_gate_decision": one_tenth_gate.get("rate_gate_decision"),
                "hard_fail_status": one_tenth_gate.get("hard_fail_status"),
                "promotion_status": one_tenth_gate.get("promotion_status"),
            },
        },
        {
            "check": "no_fullstat_mc_outputs_existing_before_clean_release",
            "status": "PASS" if not existing_mc_outputs else "FAIL",
            "evidence_path": f"{modes['instant']['run_dir']}; {modes['buildup']['run_dir']}",
            "blocking": True,
            "details": {
                "existing_expected_mc_outputs": existing_mc_outputs,
            },
        },
        {
            "check": "benchmark_alignment_blocks_old_new_geo_re_gate",
            "status": "NOT_ALIGNED_REPORT_ONLY",
            "evidence_path": rel(report_dir / "fix5_benchmark_alignment.json"),
            "blocking": False,
            "details": {
                "decision": "NOT_ALIGNED",
                "old_new_geo_re_gate_allowed": False,
            },
        },
    ]
    blocking_failures = [
        row for row in rows
        if row["blocking"] and row["status"] != "PASS"
    ]
    verifier = {
        "label": label,
        "role": "Verifier-preflight",
        "phase": "Full-stat clean transport release preflight",
        "generated_at_utc": generated_at,
        "contract_authority": "core_md/fix5_benchmarks.json",
        "overall_status": "PASS_FULLSTAT_PRE_MC_SOURCE_AND_ESCALATION_RELEASE" if not blocking_failures else "FAIL_FULLSTAT_PRE_MC_SOURCE_AND_ESCALATION_RELEASE",
        "source_provenance_status": "PASS" if not blocking_failures else "CHECK_ROWS",
        "old_new_geo_re_gate_allowed": False,
        "fullstat_transport_release_allowed": not blocking_failures,
        "mc_or_transport_started_by_verifier": False,
        "rows": rows,
    }
    write_json(report_dir / "fix5_verification_verdict.json", verifier)

    release = {
        "label": label,
        "role": "Orchestrator",
        "phase": "Clean full-stat prompt and buildup transport release after inconclusive 1/10 screen",
        "generated_at_utc": generated_at,
        "inputs": {
            "source_manifest": rel(report_dir / "fix5_source_manifest.json"),
            "runner_preflight_manifest": rel(report_dir / "fix5_runner_preflight_manifest.json"),
            "benchmark_alignment": rel(report_dir / "fix5_benchmark_alignment.json"),
            "verification_verdict": rel(report_dir / "fix5_verification_verdict.json"),
            "one_tenth_step05_screen": rel(one_tenth_summary),
        },
        "release": {
            "decision": "RELEASE_CLEAN_FULLSTAT_INSTANT_AND_BUILDUP_TRANSPORT"
            if not blocking_failures
            else "BLOCK_FULLSTAT_TRANSPORT_PENDING_FIXES",
            "scope": [
                "runs/step02_instant_fix5_fullstat_v2",
                "runs/step02_buildup_fix5_fullstat_v2",
            ],
            "basis": "1/10 W2 selected count was zero/inconclusive with no hard fail; C2 stop rule says escalate statistics rather than pass/fail.",
            "not_released": [
                "old new_geo_re pass/fail gate",
                "delayed source construction from full-stat buildup",
                "delayed transport",
                "Step05--Step08 full-stat closure",
                "fix5 signal replay",
                "append/merge",
            ],
            "append_merge_policy": "No append/merge. Clean full-stat fix5 transport only.",
        },
        "commands_released": [
            "bash -lc 'source /home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh >/tmp/fix5_megalib_env.log && python3 code/tools/run_equiv2602_pipeline_NEW_GEO.py --mode instant --source-dir config/megalib_sources_fullsphere20_fix5_tilt45 --outdir runs/step02_instant_fix5_fullstat_v2 --gamma-events 10000000 --gamma-splits 12 --non-gamma-replicas 8 --farfield-radius-cm 60 --workers 8 --keep-sources --allow-heavy-run'",
            "bash -lc 'source /home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh >/tmp/fix5_megalib_env.log && python3 code/tools/run_equiv2602_pipeline_NEW_GEO.py --mode buildup --source-dir config/megalib_sources_fullsphere20_fix5_tilt45 --outdir runs/step02_buildup_fix5_fullstat_v2 --gamma-events 10000000 --gamma-splits 12 --non-gamma-replicas 8 --farfield-radius-cm 60 --workers 8 --keep-sources --allow-heavy-run'",
        ],
        "blocking_failures": blocking_failures,
    }
    write_json(report_dir / "fix5_fullstat_transport_release.json", release)

    print(f"wrote {rel(report_dir / 'fix5_source_manifest.json')}")
    print(f"wrote {rel(report_dir / 'fix5_runner_preflight_manifest.json')}")
    print(f"wrote {rel(report_dir / 'fix5_benchmark_alignment.json')}")
    print(f"wrote {rel(report_dir / 'fix5_verification_verdict.json')}")
    print(f"wrote {rel(report_dir / 'fix5_fullstat_transport_release.json')}")
    print(verifier["overall_status"])


def inspect_sim_headers(rows: list[dict[str, Any]]) -> dict[str, Any]:
    fix_hits = 0
    baseline_hits = 0
    missing = 0
    bad: list[str] = []
    for row in rows:
        path = Path(row["sim_path"])
        if not path.exists():
            missing += 1
            bad.append(rel(path))
            continue
        header_lines: list[str] = []
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
            for _, line in zip(range(160), fh):
                header_lines.append(line)
        header = "".join(header_lines)
        has_fix = FIX5_GEO in header
        has_base = BASELINE_GEO in header
        if has_fix:
            fix_hits += 1
        if has_base:
            baseline_hits += 1
        if not has_fix or has_base:
            bad.append(rel(path))
    return {
        "sim_headers_checked": len(rows),
        "sim_headers_with_fix5_geometry": fix_hits,
        "sim_headers_with_forbidden_baseline_geometry": baseline_hits,
        "missing_sim_files": missing,
        "bad_sim_headers": bad,
        "status": "PASS" if fix_hits == len(rows) and baseline_hits == 0 and missing == 0 else "FAIL",
    }


def summarize_completed_mode(mode: str, run_dir: Path) -> dict[str, Any]:
    rows = load_json(run_dir / "run_summary.json")
    manifest_rows = read_run_manifest(run_dir / "run_manifest.csv")
    header = inspect_sim_headers(manifest_rows)
    by_particle: dict[str, dict[str, Any]] = {}
    for row in rows:
        particle = row["particle"]
        item = by_particle.setdefault(
            particle,
            {
                "jobs": 0,
                "pass_or_skip": 0,
                "fail": 0,
                "events_requested": 0,
                "events_generated": 0,
                "cpu_s": 0.0,
                "sim_size_bytes": 0,
                "dat_size_bytes": 0,
            },
        )
        item["jobs"] += 1
        if row["status"] in ("PASS", "SKIP"):
            item["pass_or_skip"] += 1
        if row["status"] == "FAIL":
            item["fail"] += 1
        item["events_requested"] += int(row["events"])
        item["events_generated"] += int(row["generated_particles"] or 0)
        item["cpu_s"] += float(row["cpu_s"] or 0.0)
        item["sim_size_bytes"] += int(row["sim_size_bytes"] or 0)
        item["dat_size_bytes"] += int(row["dat_size_bytes"] or 0)
    return {
        "mode": mode,
        "run_dir": rel(run_dir),
        "run_summary_json": rel(run_dir / "run_summary.json"),
        "run_summary_md": rel(run_dir / "run_summary.md"),
        "jobs": len(rows),
        "pass_or_skip": sum(1 for row in rows if row["status"] in ("PASS", "SKIP")),
        "fail": sum(1 for row in rows if row["status"] == "FAIL"),
        "events_requested": sum(int(row["events"]) for row in rows),
        "events_generated": sum(int(row["generated_particles"] or 0) for row in rows),
        "sim_files": sum(1 for row in rows if row.get("sim_exists")),
        "dat_files": sum(1 for row in rows if row.get("dat_exists")),
        "sim_size_bytes": sum(int(row["sim_size_bytes"] or 0) for row in rows),
        "dat_size_bytes": sum(int(row["dat_size_bytes"] or 0) for row in rows),
        "cpu_s": sum(float(row["cpu_s"] or 0.0) for row in rows),
        "headers": header,
        "by_particle": dict(sorted(by_particle.items())),
    }


def summarize_transport(label: str) -> None:
    report_dir = ROOT / "outputs" / "reports" / label
    instant = summarize_completed_mode("instant", ROOT / "runs" / "step02_instant_fix5_fullstat_v2")
    buildup = summarize_completed_mode("buildup", ROOT / "runs" / "step02_buildup_fix5_fullstat_v2")
    total_headers = {
        "sim_headers_checked": instant["headers"]["sim_headers_checked"] + buildup["headers"]["sim_headers_checked"],
        "sim_headers_with_fix5_geometry": instant["headers"]["sim_headers_with_fix5_geometry"]
        + buildup["headers"]["sim_headers_with_fix5_geometry"],
        "sim_headers_with_forbidden_baseline_geometry": instant["headers"]["sim_headers_with_forbidden_baseline_geometry"]
        + buildup["headers"]["sim_headers_with_forbidden_baseline_geometry"],
        "missing_sim_files": instant["headers"]["missing_sim_files"] + buildup["headers"]["missing_sim_files"],
        "bad_sim_headers": instant["headers"]["bad_sim_headers"] + buildup["headers"]["bad_sim_headers"],
    }
    pass_transport = (
        instant["jobs"] == 68
        and buildup["jobs"] == 68
        and instant["pass_or_skip"] == 68
        and buildup["pass_or_skip"] == 68
        and instant["fail"] == 0
        and buildup["fail"] == 0
        and instant["sim_files"] == 68
        and instant["dat_files"] == 68
        and buildup["sim_files"] == 68
        and buildup["dat_files"] == 68
        and total_headers["sim_headers_checked"] == 136
        and total_headers["sim_headers_with_fix5_geometry"] == 136
        and total_headers["sim_headers_with_forbidden_baseline_geometry"] == 0
        and total_headers["missing_sim_files"] == 0
        and not total_headers["bad_sim_headers"]
    )
    generated_at = now_utc()
    summary = {
        "label": label,
        "status": "PASS_FULLSTAT_INSTANT_AND_BUILDUP_TRANSPORT_VERIFIED" if pass_transport else "FAIL_FULLSTAT_INSTANT_AND_BUILDUP_TRANSPORT_VERIFIED",
        "generated_at_utc": generated_at,
        "geometry_setup": FIX5_GEO,
        "forbidden_baseline_geometry_setup": BASELINE_GEO,
        "instant": instant,
        "buildup": buildup,
        "combined": {
            "jobs": instant["jobs"] + buildup["jobs"],
            "pass_or_skip": instant["pass_or_skip"] + buildup["pass_or_skip"],
            "fail": instant["fail"] + buildup["fail"],
            "events_generated": instant["events_generated"] + buildup["events_generated"],
            "sim_files": instant["sim_files"] + buildup["sim_files"],
            "dat_files": instant["dat_files"] + buildup["dat_files"],
            "sim_headers": total_headers,
            "old_new_geo_re_gate": "BLOCKED_NOT_ALIGNED",
            "next_step": "Build full-stat delayed source from fix5 buildup activation with NUBASE ground-state correction, per-family TT division guard, and exact-position M-sampling audit.",
        },
    }
    summary_path = report_dir / "fix5_fullstat_transport_summary.json"
    write_json(summary_path, summary)

    release_path = report_dir / "fix5_fullstat_transport_release.json"
    release = load_json(release_path)
    release["post_transport_result"] = {
        "status": summary["status"],
        "summary_artifact": rel(summary_path),
        "instant_run_dir": instant["run_dir"],
        "buildup_run_dir": buildup["run_dir"],
        "combined_sim_gz_outputs": instant["sim_files"] + buildup["sim_files"],
        "combined_dat_inc1_outputs": instant["dat_files"] + buildup["dat_files"],
        "sim_headers_checked": total_headers["sim_headers_checked"],
        "sim_headers_with_fix5_geometry": total_headers["sim_headers_with_fix5_geometry"],
        "sim_headers_with_forbidden_baseline_geometry": total_headers["sim_headers_with_forbidden_baseline_geometry"],
        "old_new_geo_re_gate": "BLOCKED_NOT_ALIGNED",
        "delayed_source_construction": "PENDING_FULLSTAT_FIX5_BUILDUP_ACTIVATION_AUDIT",
    }
    write_json(release_path, release)

    verifier_path = report_dir / "fix5_verification_verdict.json"
    verifier = load_json(verifier_path)
    verifier["phase_fullstat_transport_status"] = summary["status"]
    verifier["overall_status"] = summary["status"] if pass_transport else "FAIL_FULLSTAT_TRANSPORT"
    verifier["fullstat_transport_summary"] = rel(summary_path)
    verifier["fullstat_transport_release_allowed"] = False
    verifier["delayed_source_release_allowed"] = pass_transport
    verifier["rows"].extend(
        [
            {
                "check": "fullstat_instant_transport_summary",
                "status": "PASS" if instant["pass_or_skip"] == 68 and instant["fail"] == 0 else "FAIL",
                "evidence_path": instant["run_summary_json"],
                "blocking": True,
                "details": {
                    "jobs": instant["jobs"],
                    "pass_or_skip": instant["pass_or_skip"],
                    "fail": instant["fail"],
                    "events_generated": instant["events_generated"],
                    "sim_files": instant["sim_files"],
                    "dat_files": instant["dat_files"],
                },
            },
            {
                "check": "fullstat_buildup_transport_summary",
                "status": "PASS" if buildup["pass_or_skip"] == 68 and buildup["fail"] == 0 else "FAIL",
                "evidence_path": buildup["run_summary_json"],
                "blocking": True,
                "details": {
                    "jobs": buildup["jobs"],
                    "pass_or_skip": buildup["pass_or_skip"],
                    "fail": buildup["fail"],
                    "events_generated": buildup["events_generated"],
                    "sim_files": buildup["sim_files"],
                    "dat_files": buildup["dat_files"],
                },
            },
            {
                "check": "fullstat_sim_header_geometry",
                "status": "PASS" if total_headers["sim_headers_with_fix5_geometry"] == 136 and total_headers["sim_headers_with_forbidden_baseline_geometry"] == 0 else "FAIL",
                "evidence_path": rel(summary_path),
                "blocking": True,
                "details": total_headers,
            },
        ]
    )
    write_json(verifier_path, verifier)

    print(f"wrote {rel(summary_path)}")
    print(f"updated {rel(release_path)}")
    print(f"updated {rel(verifier_path)}")
    print(summary["status"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="fix5_fullstat_v2")
    parser.add_argument("--summarize-transport", action="store_true")
    args = parser.parse_args()
    if args.summarize_transport:
        summarize_transport(args.label)
    else:
        build_artifacts(args.label)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
