#!/usr/bin/env python3
"""Run Mass_model_511 candidate prompt/buildup detector transport.

This harness-local runner consumes the package run matrix and already-migrated
source-card copies. It writes only under this Mass_model_511 engineering package
and `runs/Mass_model_511_nearfield_migration_20260701/`.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
import math
import shutil
import sys
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "engineering/Mass_model_511_nearfield_migration_20260701"
TRANSPORT_DIR = PKG / "03_detector_transport"
SOURCE_DIR = PKG / "03_source_migration/source_dirs/Mass_model_511"
SOURCE_MANIFEST = SOURCE_DIR / "source_migration_manifest.json"
SMOKE_MATRIX = PKG / "02_run_plan/smoke_run_matrix.csv"
RUN_ROOT = ROOT / "runs/Mass_model_511_nearfield_migration_20260701"
RUNNER_PATH = ROOT / "code/tools/run_equiv2602_pipeline_NEW_GEO.py"
COSIMA = "/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima"

BRANCH = "candidate_Mass_model_511"
GEOMETRY = (
    "outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
BASELINE_FORBIDDEN = (
    "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
MODES = ("instant", "buildup")


spec = importlib.util.spec_from_file_location("run_equiv2602_pipeline_NEW_GEO", RUNNER_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load runner helper from {RUNNER_PATH}")
runner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def split_events(total: int, pieces: int) -> list[int]:
    pieces = max(1, pieces)
    base = total // pieces
    rem = total % pieces
    return [base + (1 if i < rem else 0) for i in range(pieces)]


def selected(values: tuple[str, ...], requested: str) -> list[str]:
    if requested == "all":
        return list(values)
    return [item.strip() for item in requested.split(",") if item.strip()]


def read_matrix_rows() -> list[dict[str, str]]:
    with SMOKE_MATRIX.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def planned_counts(mode: str) -> dict[str, int]:
    rows = [
        row
        for row in read_matrix_rows()
        if row["branch"] == BRANCH and row["stage"] == mode and row["particle"] != "decay_or_eventlist"
    ]
    if not rows:
        raise SystemExit(f"No {BRANCH} {mode} rows found in {SMOKE_MATRIX}")
    counts: dict[str, int] = {}
    problems: list[str] = []
    for row in rows:
        particle = row["particle"]
        counts[particle] = int(row["total_requested_events"])
        if row["geometry_setup"] != GEOMETRY:
            problems.append(f"{mode}/{particle} geometry={row['geometry_setup']}")
    if problems:
        raise SystemExit("Run matrix geometry mismatch: " + "; ".join(problems))
    return counts


def source_by_particle() -> dict[str, Path]:
    out = {}
    for path in sorted(SOURCE_DIR.glob("Background_*_fullsphere20.source")):
        out[runner.source_tag(path)] = path.resolve()
    if "gamma" not in out:
        raise SystemExit(f"Missing gamma source in {SOURCE_DIR}")
    return out


def audit_source_cards() -> dict[str, Any]:
    manifest = load_json(SOURCE_MANIFEST) if SOURCE_MANIFEST.exists() else {}
    rows = []
    problems: list[str] = []
    for particle, path in source_by_particle().items():
        text = path.read_text(encoding="utf-8", errors="replace")
        geometry_lines = [line.strip() for line in text.splitlines() if line.strip().startswith("Geometry ")]
        comments = [line.strip() for line in text.splitlines() if line.strip().startswith("# geometry_setup=")]
        ok = (
            len(geometry_lines) == 1
            and geometry_lines[0] == f"Geometry {GEOMETRY}"
            and comments
            and comments[0] == f"# geometry_setup={GEOMETRY}"
            and BASELINE_FORBIDDEN not in text
        )
        if not ok:
            problems.append(particle)
        rows.append(
            {
                "particle": particle,
                "source": rel(path),
                "geometry_lines": geometry_lines,
                "geometry_comment": comments[0] if comments else None,
                "contains_forbidden_baseline": BASELINE_FORBIDDEN in text,
                "status": "PASS" if ok else "FAIL",
            }
        )
    return {
        "status": "PASS" if not problems else "FAIL",
        "source_dir": rel(SOURCE_DIR),
        "source_manifest": rel(SOURCE_MANIFEST),
        "source_manifest_status": manifest.get("status"),
        "source_manifest_geometry": manifest.get("geometry_setup"),
        "rows": rows,
        "problems": problems,
    }


def run_dir(mode: str) -> Path:
    return RUN_ROOT / f"step02_{mode}_{BRANCH}_smoke"


def build_jobs(mode: str, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    counts = planned_counts(mode)
    sources = source_by_particle()
    outdir = run_dir(mode).resolve()
    job_source_dir = outdir / "job_sources"
    log_dir = outdir / "logs"

    flux_by_particle = {particle: runner.source_flux(path) for particle, path in sources.items()}
    gamma_flux = flux_by_particle["gamma"]
    gamma_events = counts["gamma"]
    area_cm2 = math.pi * args.farfield_radius_cm * args.farfield_radius_cm
    normalization = {
        "mode": mode,
        "branch": BRANCH,
        "source_dir": rel(SOURCE_DIR),
        "outdir": rel(outdir),
        "geometry_setup": GEOMETRY,
        "count_policy": "exact candidate_Mass_model_511 smoke_run_matrix totals",
        "planned_counts_by_particle_total": counts,
        "gamma_events": gamma_events,
        "gamma_splits": args.gamma_splits,
        "non_gamma_replicas": args.non_gamma_replicas,
        "gamma_flux_cm2_s": gamma_flux,
        "gamma_norm_factor_cm2_s_per_count": gamma_flux / gamma_events,
        "non_gamma_combined_norm_factor_cm2_s_per_count": (gamma_flux / gamma_events) / args.non_gamma_replicas,
        "farfield_radius_cm": args.farfield_radius_cm,
        "farfield_area_cm2": area_cm2,
        "gamma_prompt_time_s_with_farfield_area": gamma_events / (gamma_flux * area_cm2),
        "flux_by_particle_cm2_s": flux_by_particle,
        "selected_particles": sorted(sources),
        "store_isotopes": True,
        "smoke_matrix": rel(SMOKE_MATRIX),
        "seed_rule": "seed = 1000003 + ordinal * 7919; same ordinal policy as paired nearfield workflow",
    }

    jobs: list[dict[str, Any]] = []

    def add_job(tag: str, rep: int, part: int, events: int, ordinal: int) -> None:
        job_name = f"Background_{tag}_fullsphere20_rep{rep:02d}_part{part:02d}"
        sim_prefix = outdir / job_name
        iso_prefix = outdir / f"{job_name}.dat"
        seed = 1000003 + ordinal * 7919
        jobs.append(
            {
                "job_name": job_name,
                "particle": tag,
                "mode": mode,
                "events": int(events),
                "rep": rep,
                "part": part,
                "seed": seed,
                "source": str(sources[tag]),
                "temp_source": str(job_source_dir / f"{job_name}.source"),
                "sim_prefix": str(sim_prefix),
                "iso_prefix": str(iso_prefix),
                "sim_path": str(Path(f"{sim_prefix}.inc1.id1.sim.gz")),
                "dat_path": str(Path(f"{iso_prefix}.inc1.dat")),
                "log": str(log_dir / f"{job_name}.log"),
                "cosima": args.cosima,
                "skip_existing": not args.force,
                "cleanup_source": False,
                "store_isotopes": True,
            }
        )

    ordinal = 0
    for part, events in enumerate(split_events(counts["gamma"], args.gamma_splits), 1):
        ordinal += 1
        add_job("gamma", 1, part, events, ordinal)
    for tag in sorted(p for p in sources if p != "gamma"):
        if tag not in counts:
            continue
        for rep, events in enumerate(split_events(counts[tag], args.non_gamma_replicas), 1):
            if events <= 0:
                continue
            ordinal += 1
            add_job(tag, rep, 1, events, ordinal)

    normalization["jobs"] = len(jobs)
    normalization["events_requested_total"] = sum(job["events"] for job in jobs)
    normalization["events_requested_by_particle"] = {
        tag: sum(job["events"] for job in jobs if job["particle"] == tag)
        for tag in sorted(sources)
    }
    return jobs, normalization


def write_manifest(outdir: Path, jobs: list[dict[str, Any]], normalization: dict[str, Any]) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    estimate = runner.estimate_from_smoke(normalization["mode"], jobs)
    normalization["resource_estimate_from_existing_smoke"] = estimate
    runner.write_manifest(outdir, jobs, normalization)


def load_manifest_jobs(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    jobs = []
    for row in rows:
        row["events"] = int(row["events"])
        row["rep"] = int(row["rep"])
        row["part"] = int(row["part"])
        row["seed"] = int(row["seed"])
        row["skip_existing"] = True
        row["cleanup_source"] = False
        row["store_isotopes"] = row.get("store_isotopes", "True") == "True"
        row["cosima"] = COSIMA
        jobs.append(row)
    return jobs


def inspect_sim_header(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": rel(path), "exists": False, "contains_geometry": False}
    lines = []
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
        for _, line in zip(range(220), fh):
            lines.append(line)
    text = "".join(lines)
    return {"path": rel(path), "exists": True, "contains_geometry": GEOMETRY in text}


def summarize_run_state(mode: str, jobs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    outdir = run_dir(mode).resolve()
    manifest = outdir / "run_manifest.csv"
    if jobs is None and manifest.exists():
        jobs = load_manifest_jobs(manifest)
    jobs = jobs or []
    summary_path = outdir / "run_summary.json"
    rows = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else []
    pass_or_skip = sum(1 for row in rows if row.get("status") in ("PASS", "SKIP"))
    fail = sum(1 for row in rows if row.get("status") == "FAIL")
    sim_headers = [inspect_sim_header(Path(job["sim_path"])) for job in jobs]
    sim_ready = sum(1 for item in sim_headers if item["exists"] and item["contains_geometry"])
    status = "NOT_PREPARED"
    if jobs:
        status = "PREPARED"
    if jobs and len(rows) == len(jobs) and pass_or_skip == len(jobs) and fail == 0 and sim_ready == len(jobs):
        status = "PASS"
    return {
        "branch": BRANCH,
        "mode": mode,
        "run_dir": rel(outdir),
        "run_manifest": rel(manifest),
        "run_summary": rel(summary_path) if summary_path.exists() else None,
        "jobs": len(jobs),
        "summary_rows": len(rows),
        "pass_or_skip": pass_or_skip,
        "fail": fail,
        "events_requested": sum(int(job["events"]) for job in jobs),
        "sim_headers_with_expected_geometry": sim_ready,
        "sim_headers_checked": len(sim_headers),
        "status": status,
    }


def prepare_run(mode: str, args: argparse.Namespace) -> dict[str, Any]:
    jobs, normalization = build_jobs(mode, args)
    outdir = run_dir(mode).resolve()
    write_manifest(outdir, jobs, normalization)
    for job in jobs:
        runner.patch_source(job)
    return summarize_run_state(mode, jobs)


def run_prepared(mode: str, args: argparse.Namespace) -> dict[str, Any]:
    jobs, normalization = build_jobs(mode, args)
    outdir = run_dir(mode).resolve()
    write_manifest(outdir, jobs, normalization)
    estimate = normalization["resource_estimate_from_existing_smoke"]
    if not runner.enforce_resource_guard(args, jobs, estimate):
        return {**summarize_run_state(mode, jobs), "status": "BLOCKED_RESOURCE_GUARD"}
    with Pool(processes=args.workers) as pool:
        rows = list(pool.imap_unordered(runner.run_job, jobs))
    rows.sort(key=lambda row: row["job_name"])
    runner.write_summary(outdir, rows)
    return summarize_run_state(mode, jobs)


def write_campaign_manifest(source_audit: dict[str, Any], run_records: list[dict[str, Any]], args: argparse.Namespace) -> None:
    pass_runs = bool(run_records) and all(row["status"] == "PASS" for row in run_records)
    payload = {
        "document_type": "mass_model_511_g3_g4_prompt_buildup_campaign",
        "generated_at_utc": now_utc(),
        "status": "PASS_PROMPT_BUILDUP_TRANSPORT" if pass_runs else "IN_PROGRESS_OR_PREPARED",
        "claim_boundary": (
            "Transport artifact only. Background-rate/no-effect claims require delayed transport, "
            "Step05 detector response, normalization checks, and downstream verdicts."
        ),
        "source_authority_edited": False,
        "old_nearfield_engineering_edited": False,
        "branch": BRANCH,
        "geometry": GEOMETRY,
        "source_audit": source_audit,
        "run_records": run_records,
        "workers": args.workers,
        "cosima": args.cosima,
    }
    write_json(TRANSPORT_DIR / "prompt_buildup_campaign_manifest.json", payload)
    lines = [
        "# Mass_model_511 Prompt/Buildup Transport",
        "",
        f"- generated_at_utc: `{payload['generated_at_utc']}`",
        f"- status: `{payload['status']}`",
        f"- branch: `{BRANCH}`",
        f"- geometry: `{GEOMETRY}`",
        f"- source_audit: `{source_audit['status']}`",
        "",
        "| Mode | Status | Jobs | Events | Headers with expected geometry | Summary |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in run_records:
        lines.append(
            f"| `{row['mode']}` | `{row['status']}` | {row['jobs']} | {row['events_requested']} | "
            f"{row['sim_headers_with_expected_geometry']}/{row['sim_headers_checked']} | `{row['run_summary']}` |"
        )
    lines.extend(
        [
            "",
            "Boundary: this is not a detector-rate or no-effect claim.",
        ]
    )
    (TRANSPORT_DIR / "prompt_buildup_campaign_manifest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    default_cosima = shutil.which("cosima") or COSIMA
    ap = argparse.ArgumentParser()
    ap.add_argument("--modes", default="all", help="all or comma list: instant,buildup")
    ap.add_argument("--prepare-only", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--gamma-splits", type=int, default=12)
    ap.add_argument("--non-gamma-replicas", type=int, default=8)
    ap.add_argument("--farfield-radius-cm", type=float, default=60.0)
    ap.add_argument("--cosima", default=default_cosima)
    ap.add_argument("--allow-heavy-run", action="store_true")
    ap.add_argument("--max-events-without-confirmation", type=int, default=runner.DEFAULT_EVENT_LIMIT_WITHOUT_CONFIRMATION)
    ap.add_argument("--max-estimated-gb-without-confirmation", type=float, default=runner.DEFAULT_GB_LIMIT_WITHOUT_CONFIRMATION)
    ap.add_argument("--max-estimated-cpu-days-without-confirmation", type=float, default=runner.DEFAULT_CPU_DAY_LIMIT_WITHOUT_CONFIRMATION)
    args = ap.parse_args()
    if not args.prepare_only and not args.run:
        args.prepare_only = True

    modes = selected(MODES, args.modes)
    bad_modes = sorted(set(modes) - set(MODES))
    if bad_modes:
        raise SystemExit(f"Unknown modes: {bad_modes}")

    source_audit = audit_source_cards()
    if source_audit["status"] != "PASS":
        write_campaign_manifest(source_audit, [], args)
        raise SystemExit("Source-card audit failed; refusing to launch transport")

    run_records: list[dict[str, Any]] = []
    for mode in modes:
        run_records.append(run_prepared(mode, args) if args.run else prepare_run(mode, args))
    write_campaign_manifest(source_audit, run_records, args)
    print(json.dumps({"source_audit": source_audit, "run_records": run_records}, indent=2, ensure_ascii=False))
    return 0 if all(record["status"] in ("PASS", "PREPARED") for record in run_records) else 2


if __name__ == "__main__":
    raise SystemExit(main())
