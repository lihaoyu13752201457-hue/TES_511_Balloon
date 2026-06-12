#!/usr/bin/env python3
"""Run the 2605 full-sphere production with 2602-equivalent statistics.

Default statistics match the February workflow convention:

- gamma defines the Monte Carlo exposure with 10,000,000 generated particles;
- gamma is split into four independent jobs;
- each non-gamma particle is generated with events = gamma_events *
  particle_flux / gamma_flux;
- non-gamma particles use eight independent replicas and therefore get a
  combined analysis weight divided by eight.

The runner patches every temporary source with a unique deterministic seed.
This avoids the hidden failure mode where split jobs or replicas repeat the
same random sequence.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import shutil
import subprocess
import time
from multiprocessing import Pool
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCE_RE = re.compile(r"Background_(?P<tag>.+?)_fullsphere20\.source$")
FLUX_RE = re.compile(r"\.Flux\s+([-+0-9.eE]+)\s*$")
GENERATED_RE = re.compile(r"Total number of generated particles:\s+(\d+)")
CPU_RE = re.compile(r"Total CPU time spent in run:\s+([-+0-9.eE]+) sec")
OBS_RE = re.compile(r"Observation time:\s+([-+0-9.eE]+) sec")
DEFAULT_EVENT_LIMIT_WITHOUT_CONFIRMATION = 5_000_000
DEFAULT_GB_LIMIT_WITHOUT_CONFIRMATION = 100.0
DEFAULT_CPU_DAY_LIMIT_WITHOUT_CONFIRMATION = 7.0


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def split_events(total: int, pieces: int) -> list[int]:
    pieces = max(1, pieces)
    base = total // pieces
    rem = total % pieces
    return [base + (1 if i < rem else 0) for i in range(pieces)]


def source_tag(path: Path) -> str:
    m = SOURCE_RE.match(path.name)
    if not m:
        raise ValueError(f"Unexpected source filename: {path.name}")
    return m.group("tag")


def source_flux(path: Path) -> float:
    total = 0.0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = FLUX_RE.search(line)
        if m:
            total += float(m.group(1))
    return total


def parse_log(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "log_exists": False,
            "has_error": True,
            "generated_particles": None,
            "cpu_s": None,
            "observation_time_s": None,
        }
    text = path.read_text(encoding="utf-8", errors="replace")
    generated = GENERATED_RE.search(text)
    cpu = CPU_RE.search(text)
    obs = OBS_RE.search(text)
    return {
        "log_exists": True,
        "has_error": "***  Error" in text or "Unable to parse" in text or "Segmentation fault" in text,
        "generated_particles": int(generated.group(1)) if generated else None,
        "cpu_s": float(cpu.group(1)) if cpu else None,
        "observation_time_s": float(obs.group(1)) if obs else None,
    }


def estimate_from_smoke(mode: str, jobs: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = (
        ["smoke_buildup_100_2602units", "smoke_buildup_100"]
        if mode == "buildup"
        else ["smoke_instant_1k_2602units", "smoke_instant_1k"]
    )
    smoke_dir = next(
        (ROOT / "runs" / name for name in candidates if (ROOT / "runs" / name / "run_summary.csv").exists()),
        ROOT / "runs" / candidates[-1],
    )
    summary = smoke_dir / "run_summary.csv"
    rates: dict[str, dict[str, float]] = {}
    if summary.exists():
        with summary.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                events = int(row["events"])
                if events <= 0:
                    continue
                particle = row["particle"]
                rates[particle] = {
                    "cpu_s_per_event": float(row["cpu_s"] or 0.0) / events,
                    "sim_bytes_per_event": float(row["sim_size_bytes"] or 0.0) / events,
                    "dat_bytes_per_event": float(row["dat_size_bytes"] or 0.0) / events,
                }

    by_particle: dict[str, dict[str, float]] = {}
    for job in jobs:
        particle = job["particle"]
        events = float(job["events"])
        row = by_particle.setdefault(
            particle,
            {
                "events": 0.0,
                "estimated_cpu_s": 0.0,
                "estimated_sim_bytes": 0.0,
                "estimated_dat_bytes": 0.0,
                "has_smoke_rate": 0.0,
            },
        )
        row["events"] += events
        if particle in rates:
            row["has_smoke_rate"] = 1.0
            row["estimated_cpu_s"] += rates[particle]["cpu_s_per_event"] * events
            row["estimated_sim_bytes"] += rates[particle]["sim_bytes_per_event"] * events
            row["estimated_dat_bytes"] += rates[particle]["dat_bytes_per_event"] * events

    totals = {
        "source": rel(summary),
        "total_events": sum(float(j["events"]) for j in jobs),
        "estimated_cpu_s": sum(v["estimated_cpu_s"] for v in by_particle.values()),
        "estimated_sim_bytes": sum(v["estimated_sim_bytes"] for v in by_particle.values()),
        "estimated_dat_bytes": sum(v["estimated_dat_bytes"] for v in by_particle.values()),
        "by_particle": by_particle,
    }
    totals["estimated_cpu_days"] = totals["estimated_cpu_s"] / 86400.0
    totals["estimated_sim_gb"] = totals["estimated_sim_bytes"] / 1e9
    totals["estimated_dat_gb"] = totals["estimated_dat_bytes"] / 1e9
    totals["estimated_total_gb"] = (totals["estimated_sim_bytes"] + totals["estimated_dat_bytes"]) / 1e9
    return totals


def enforce_resource_guard(args: argparse.Namespace, jobs: list[dict[str, Any]], estimate: dict[str, Any]) -> bool:
    total_events = int(estimate["total_events"])
    reasons = []
    if total_events > args.max_events_without_confirmation:
        reasons.append(f"events={total_events:,} > {args.max_events_without_confirmation:,}")
    if estimate["estimated_total_gb"] > args.max_estimated_gb_without_confirmation:
        reasons.append(
            f"estimated_output={estimate['estimated_total_gb']:.1f} GB > "
            f"{args.max_estimated_gb_without_confirmation:.1f} GB"
        )
    if estimate["estimated_cpu_days"] > args.max_estimated_cpu_days_without_confirmation:
        reasons.append(
            f"estimated_cpu={estimate['estimated_cpu_days']:.1f} CPU-days > "
            f"{args.max_estimated_cpu_days_without_confirmation:.1f} CPU-days"
        )
    if not reasons or args.allow_heavy_run:
        return True

    print("Resource guard stopped execution before launching Cosima jobs.")
    print("Manifest and normalization were still written for inspection.")
    print("Reasons:")
    for reason in reasons:
        print(f"- {reason}")
    print(
        "Re-run with --allow-heavy-run only after checking disk, runtime, and "
        "whether StoreSimulationInfo all is really needed for the selected particles."
    )
    print("Largest estimated particles:")
    heavy = sorted(
        estimate["by_particle"].items(),
        key=lambda item: item[1]["estimated_sim_bytes"] + item[1]["estimated_dat_bytes"],
        reverse=True,
    )
    for particle, row in heavy[:5]:
        print(
            f"- {particle}: events={int(row['events']):,}, "
            f"cpu_days={row['estimated_cpu_s'] / 86400.0:.1f}, "
            f"output_gb={(row['estimated_sim_bytes'] + row['estimated_dat_bytes']) / 1e9:.1f}"
        )
    return False


def patch_source(job: dict[str, Any]) -> None:
    source = Path(job["source"])
    target = Path(job["temp_source"])
    target.parent.mkdir(parents=True, exist_ok=True)

    mode = job["mode"]
    run_name = None
    seen_seed = False
    seen_store = False
    seen_decay = False
    seen_iso = False

    out_lines: list[str] = []
    for line in source.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith("Run "):
            toks = stripped.split()
            if len(toks) >= 2:
                run_name = toks[1]
            out_lines.append(line)
            continue
        if stripped.startswith("Seed "):
            seen_seed = True
            out_lines.append(f"Seed {job['seed']}")
            continue
        if stripped.startswith("StoreIsotopes"):
            seen_store = True
            out_lines.append("StoreIsotopes true")
            continue
        if stripped.startswith("DecayMode"):
            seen_decay = True
            if mode == "buildup":
                out_lines.append("DecayMode ActivationBuildUp")
            continue
        if ".Events" in line:
            prefix = line.split(".Events", 1)[0].strip()
            out_lines.append(f"{prefix}.Events {int(job['events'])}")
            continue
        if ".FileName" in line:
            prefix = line.split(".FileName", 1)[0].strip()
            out_lines.append(f"{prefix}.FileName {job['sim_prefix']}")
            continue
        if ".IsotopeProductionFile" in line:
            seen_iso = True
            prefix = line.split(".IsotopeProductionFile", 1)[0].strip()
            out_lines.append(f"{prefix}.IsotopeProductionFile {job['iso_prefix']}")
            continue
        out_lines.append(line)

    insert_at = 0
    for i, line in enumerate(out_lines):
        if line.strip().startswith("Geometry "):
            insert_at = i + 1
            break
    additions: list[str] = []
    if not seen_seed:
        additions.append(f"Seed {job['seed']}")
    if not seen_store:
        additions.append("StoreIsotopes true")
    if mode == "buildup" and not seen_decay:
        additions.append("DecayMode ActivationBuildUp")
    if additions:
        out_lines[insert_at:insert_at] = additions
    if not seen_iso and run_name:
        out_lines.append(f"{run_name}.IsotopeProductionFile {job['iso_prefix']}")

    target.write_text("\n".join(out_lines) + "\n", encoding="utf-8")


def run_job(job: dict[str, Any]) -> dict[str, Any]:
    sim_path = Path(job["sim_path"])
    dat_path = Path(job["dat_path"])
    log_path = Path(job["log"])

    if job["skip_existing"] and sim_path.exists() and dat_path.exists():
        log = parse_log(log_path)
        return {**job, "status": "SKIP", "returncode": 0, **log}

    patch_source(job)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    started = time.time()
    with log_path.open("w", encoding="utf-8") as logf:
        logf.write(f"job_name={job['job_name']}\n")
        logf.write(f"mode={job['mode']} particle={job['particle']} events={job['events']} seed={job['seed']}\n")
        logf.write(f"source={job['source']}\n")
        logf.write(f"temp_source={job['temp_source']}\n")
        logf.write("-" * 72 + "\n")
        proc = subprocess.run(
            [job["cosima"], job["temp_source"]],
            cwd=str(ROOT),
            stdout=logf,
            stderr=subprocess.STDOUT,
            check=False,
        )
        logf.write("-" * 72 + "\n")
        logf.write(f"returncode={proc.returncode}\n")
        logf.write(f"wall_s={time.time() - started:.3f}\n")

    if job["cleanup_source"]:
        try:
            Path(job["temp_source"]).unlink()
        except FileNotFoundError:
            pass

    log = parse_log(log_path)
    status = "PASS"
    details = []
    if proc.returncode != 0:
        status = "FAIL"
        details.append(f"returncode={proc.returncode}")
    if log["has_error"]:
        status = "FAIL"
        details.append("log_error")
    if log["generated_particles"] != job["events"]:
        status = "FAIL"
        details.append(f"generated={log['generated_particles']} expected={job['events']}")
    if not sim_path.exists():
        status = "FAIL"
        details.append("missing_sim")
    if not dat_path.exists():
        status = "FAIL"
        details.append("missing_dat")

    return {
        **job,
        "status": status,
        "details": "; ".join(details) if details else "completed",
        "returncode": proc.returncode,
        "sim_exists": sim_path.exists(),
        "dat_exists": dat_path.exists(),
        "sim_size_bytes": sim_path.stat().st_size if sim_path.exists() else 0,
        "dat_size_bytes": dat_path.stat().st_size if dat_path.exists() else 0,
        **log,
    }


def build_jobs(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source_dir = args.source_dir
    sources = sorted(source_dir.glob("Background_*_fullsphere20.source"))
    if not sources:
        raise SystemExit(f"No per-particle sources found in {source_dir}")
    source_manifest_path = source_dir / "source_migration_manifest.json"
    source_manifest: dict[str, Any] | None = None
    if source_manifest_path.exists():
        source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))

    flux_by_tag: dict[str, float] = {}
    source_by_tag: dict[str, Path] = {}
    for src in sources:
        tag = source_tag(src)
        source_by_tag[tag] = src.resolve()
        flux_by_tag[tag] = source_flux(src)
    if "gamma" not in flux_by_tag or flux_by_tag["gamma"] <= 0.0:
        raise SystemExit("Missing positive gamma source flux")

    selected = set(source_by_tag)
    if args.particles:
        selected = {p.strip() for p in args.particles.split(",") if p.strip()}
        missing = selected - set(source_by_tag)
        if missing:
            raise SystemExit(f"Unknown selected particles: {sorted(missing)}")

    gamma_flux = flux_by_tag["gamma"]
    gamma_factor = gamma_flux / args.gamma_events
    non_gamma_factor = gamma_factor / args.non_gamma_replicas
    area_cm2 = math.pi * args.farfield_radius_cm * args.farfield_radius_cm
    prompt_time_s = args.gamma_events / (gamma_flux * area_cm2)

    base_events: dict[str, int] = {"gamma": args.gamma_events}
    for tag, flux in flux_by_tag.items():
        if tag == "gamma":
            continue
        base_events[tag] = int(round((flux / gamma_flux) * args.gamma_events)) if flux > 0 else 0

    jobs: list[dict[str, Any]] = []
    outdir = args.outdir.resolve()
    job_source_dir = outdir / "job_sources"
    log_dir = outdir / "logs"

    def add_job(tag: str, rep: int, part: int, events: int, ordinal: int) -> None:
        job_name = f"Background_{tag}_fullsphere20_rep{rep:02d}_part{part:02d}"
        sim_prefix = outdir / job_name
        iso_prefix = outdir / f"{job_name}.dat"
        seed = 1000003 + ordinal * 7919
        jobs.append(
            {
                "job_name": job_name,
                "particle": tag,
                "mode": args.mode,
                "events": int(events),
                "rep": rep,
                "part": part,
                "seed": seed,
                "source": str(source_by_tag[tag]),
                "temp_source": str(job_source_dir / f"{job_name}.source"),
                "sim_prefix": str(sim_prefix),
                "iso_prefix": str(iso_prefix),
                "sim_path": str(Path(f"{sim_prefix}.inc1.id1.sim.gz")),
                "dat_path": str(Path(f"{iso_prefix}.inc1.dat")),
                "log": str(log_dir / f"{job_name}.log"),
                "cosima": args.cosima,
                "skip_existing": not args.force,
                "cleanup_source": not args.keep_sources,
            }
        )

    ordinal = 0
    if "gamma" in selected:
        for part, events in enumerate(split_events(args.gamma_events, args.gamma_splits), 1):
            ordinal += 1
            add_job("gamma", 1, part, events, ordinal)
    for tag in sorted(source_by_tag):
        if tag == "gamma" or tag not in selected:
            continue
        events = base_events[tag]
        if events <= 0:
            continue
        for rep in range(1, args.non_gamma_replicas + 1):
            ordinal += 1
            add_job(tag, rep, 1, events, ordinal)

    if args.max_jobs is not None:
        jobs = jobs[: args.max_jobs]

    normalization = {
        "mode": args.mode,
        "source_dir": rel(source_dir.resolve()),
        "outdir": rel(outdir),
        "gamma_events": args.gamma_events,
        "gamma_splits": args.gamma_splits,
        "non_gamma_replicas": args.non_gamma_replicas,
        "gamma_flux_cm2_s": gamma_flux,
        "gamma_norm_factor_cm2_s_per_count": gamma_factor,
        "non_gamma_combined_norm_factor_cm2_s_per_count": non_gamma_factor,
        "farfield_radius_cm": args.farfield_radius_cm,
        "farfield_area_cm2": area_cm2,
        "gamma_prompt_time_s_with_farfield_area": prompt_time_s,
        "flux_by_particle_cm2_s": flux_by_tag,
        "base_events_by_particle": base_events,
        "selected_particles": sorted(selected),
        "jobs": len(jobs),
    }
    if source_manifest is not None:
        normalization["source_migration_manifest"] = {
            "path": rel(source_manifest_path),
            "status": source_manifest.get("status"),
            "geometry_setup": source_manifest.get("geometry_setup"),
            "geometry_status": source_manifest.get("geometry_status"),
            "farfield_radius_cm": source_manifest.get("farfield_radius_cm"),
            "pointing_policy": source_manifest.get("pointing_policy"),
        }
        manifest_radius = source_manifest.get("farfield_radius_cm")
        if manifest_radius is not None and abs(float(manifest_radius) - args.farfield_radius_cm) > 1.0e-9:
            normalization["farfield_radius_warning"] = (
                f"CLI farfield radius {args.farfield_radius_cm} cm differs from "
                f"source manifest recommendation {manifest_radius} cm"
            )
    return jobs, normalization


def write_manifest(outdir: Path, jobs: list[dict[str, Any]], normalization: dict[str, Any]) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "normalization.json").write_text(json.dumps(normalization, indent=2) + "\n", encoding="utf-8")
    fields = [
        "job_name",
        "particle",
        "mode",
        "events",
        "rep",
        "part",
        "seed",
        "source",
        "temp_source",
        "sim_path",
        "dat_path",
        "log",
    ]
    with (outdir / "run_manifest.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for job in jobs:
            writer.writerow({k: job[k] for k in fields})


def write_summary(outdir: Path, rows: list[dict[str, Any]]) -> None:
    slim_rows = []
    for row in rows:
        slim_rows.append(
            {
                "job_name": row["job_name"],
                "particle": row["particle"],
                "status": row["status"],
                "details": row.get("details", ""),
                "events": row["events"],
                "generated_particles": row.get("generated_particles"),
                "cpu_s": row.get("cpu_s"),
                "observation_time_s": row.get("observation_time_s"),
                "sim_exists": row.get("sim_exists", False),
                "dat_exists": row.get("dat_exists", False),
                "sim_size_bytes": row.get("sim_size_bytes", 0),
                "dat_size_bytes": row.get("dat_size_bytes", 0),
                "log": rel(Path(row["log"])),
                "sim_path": rel(Path(row["sim_path"])),
                "dat_path": rel(Path(row["dat_path"])),
            }
        )
    (outdir / "run_summary.json").write_text(json.dumps(slim_rows, indent=2) + "\n", encoding="utf-8")
    with (outdir / "run_summary.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(slim_rows[0]) if slim_rows else ["job_name"])
        writer.writeheader()
        writer.writerows(slim_rows)

    totals: dict[str, Any] = {
        "jobs": len(slim_rows),
        "pass": sum(1 for r in slim_rows if r["status"] in ("PASS", "SKIP")),
        "fail": sum(1 for r in slim_rows if r["status"] == "FAIL"),
        "events_requested": sum(int(r["events"]) for r in slim_rows),
        "events_generated": sum(int(r["generated_particles"] or 0) for r in slim_rows),
        "cpu_s": sum(float(r["cpu_s"] or 0.0) for r in slim_rows),
    }
    lines = [
        "# 2605 Equivalent-Statistics Run Summary",
        "",
        f"- jobs: {totals['jobs']}",
        f"- pass_or_skip: {totals['pass']}",
        f"- fail: {totals['fail']}",
        f"- events_requested: {totals['events_requested']}",
        f"- events_generated: {totals['events_generated']}",
        f"- cpu_s: {totals['cpu_s']:.3f}",
    ]
    (outdir / "run_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    default_cosima = shutil.which("cosima") or "/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima"
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["instant", "buildup"], required=True)
    ap.add_argument("--source-dir", type=Path, default=ROOT / "config" / "megalib_sources_fullsphere20")
    ap.add_argument("--outdir", type=Path, default=None)
    ap.add_argument("--gamma-events", type=int, default=10_000_000)
    ap.add_argument("--gamma-splits", type=int, default=4)
    ap.add_argument("--non-gamma-replicas", type=int, default=8)
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--particles", default="")
    ap.add_argument("--max-jobs", type=int, default=None)
    ap.add_argument("--farfield-radius-cm", type=float, default=35.0)
    ap.add_argument("--cosima", default=default_cosima)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--keep-sources", action="store_true")
    ap.add_argument("--allow-heavy-run", action="store_true")
    ap.add_argument("--max-events-without-confirmation", type=int, default=DEFAULT_EVENT_LIMIT_WITHOUT_CONFIRMATION)
    ap.add_argument("--max-estimated-gb-without-confirmation", type=float, default=DEFAULT_GB_LIMIT_WITHOUT_CONFIRMATION)
    ap.add_argument("--max-estimated-cpu-days-without-confirmation", type=float, default=DEFAULT_CPU_DAY_LIMIT_WITHOUT_CONFIRMATION)
    args = ap.parse_args()

    if args.outdir is None:
        args.outdir = ROOT / "runs" / f"{args.mode}_equiv2602"
    args.source_dir = args.source_dir.resolve()
    args.outdir = args.outdir.resolve()

    jobs, normalization = build_jobs(args)
    estimate = estimate_from_smoke(args.mode, jobs)
    normalization["resource_estimate_from_smoke"] = estimate
    write_manifest(args.outdir, jobs, normalization)

    print(f"mode={args.mode} outdir={rel(args.outdir)} jobs={len(jobs)} workers={args.workers}")
    print(f"gamma_flux={normalization['gamma_flux_cm2_s']:.12e}")
    print(f"gamma_events={args.gamma_events:,} prompt_time_s={normalization['gamma_prompt_time_s_with_farfield_area']:.6f}")
    for tag, events in sorted(normalization["base_events_by_particle"].items()):
        if tag == "gamma":
            print(f"{tag:8s} events={events:,} splits={args.gamma_splits}")
        else:
            print(f"{tag:8s} events_per_rep={events:,} replicas={args.non_gamma_replicas}")

    if args.dry_run:
        print(f"dry_run wrote {rel(args.outdir / 'run_manifest.csv')}")
        return 0
    if not jobs:
        print("No jobs selected")
        return 0
    if not enforce_resource_guard(args, jobs, estimate):
        return 2

    with Pool(processes=args.workers) as pool:
        rows = list(pool.imap_unordered(run_job, jobs))

    rows.sort(key=lambda r: r["job_name"])
    write_summary(args.outdir, rows)
    failures = [r for r in rows if r["status"] == "FAIL"]
    print(f"completed jobs={len(rows)} failures={len(failures)} summary={rel(args.outdir / 'run_summary.md')}")
    for row in failures[:20]:
        print(f"FAIL {row['job_name']}: {row.get('details', '')}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
