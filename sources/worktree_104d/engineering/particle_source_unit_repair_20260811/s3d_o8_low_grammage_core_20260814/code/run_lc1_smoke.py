#!/usr/bin/env python3
"""Preflight and serially run the frozen LC1 mechanism smoke."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
PLAN_PATH = PACKAGE / "data/lc1_smoke_plan_v2.json"
LEDGER_PATH = PACKAGE / "data/lc1_smoke_ledger_v2.json"
COSIMA = Path("/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima")
ENV = Path("/home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def mem_available_kib() -> int:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1])
    raise RuntimeError("MemAvailable is absent")


def existing_ancestor(path: Path) -> Path:
    candidate = path
    while not candidate.exists():
        candidate = candidate.parent
    return candidate


def atomic_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def scan_sim_seed_collisions(selected: set[int], run_root: Path) -> list[dict]:
    hits = []
    seen_paths: set[Path] = set()
    for base in (ROOT, Path("/home/ubuntu/TES_511_Balloon")):
        for path in base.rglob("*.sim.gz"):
            absolute = path.resolve()
            if absolute in seen_paths or run_root == absolute or run_root in absolute.parents:
                continue
            seen_paths.add(absolute)
            try:
                with gzip.open(path, "rt", encoding="utf-8", errors="strict") as f:
                    seed = None
                    for i, line in enumerate(f):
                        if line.startswith("Seed"):
                            seed = int(line.split()[1])
                            break
                        if i >= 127:
                            break
                if seed in selected:
                    hits.append({"path": str(absolute), "seed": seed})
            except (OSError, EOFError, UnicodeError, ValueError):
                # Frozen preflight is fail-closed on an unreadable candidate
                # header because it prevents a complete seed audit.
                raise RuntimeError(f"cannot audit SIM header: {absolute}")
    return hits


def validate_sim(path: Path, job: dict, cap: int) -> dict:
    if path.stat().st_size > cap:
        raise RuntimeError(f"SIM exceeds cap: {path}")
    geometry = None
    seed = None
    ids = []
    trailer_en = False
    ts = None
    with gzip.open(path, "rt", encoding="utf-8", errors="strict") as f:
        for line in f:
            if line.startswith("Geometry") and geometry is None:
                geometry = line.split(None, 1)[1].strip()
            elif line.startswith("Seed") and seed is None:
                seed = int(line.split()[1])
            elif line.startswith("ID "):
                ids.append(int(line.split()[1]))
            elif line.strip() == "EN":
                trailer_en = True
            elif line.startswith("TS "):
                ts = int(line.split()[1])
    if geometry != job["geometry_setup"]:
        raise RuntimeError(f"geometry header mismatch: {path}: {geometry!r}")
    if seed != job["seed"]:
        raise RuntimeError(f"seed header mismatch: {path}: {seed!r}")
    if len(ids) != job["n_events"] or ids != list(range(1, job["n_events"] + 1)):
        raise RuntimeError(f"event IDs are incomplete/non-contiguous: {path}")
    if not trailer_en or ts != job["n_events"]:
        raise RuntimeError(f"SIM trailer incomplete: {path}")
    return {
        "path": str(path.resolve()),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "events": len(ids),
        "geometry": geometry,
        "seed": seed,
        "trailer_en": trailer_en,
        "ts": ts,
    }


def preflight(plan: dict, *, scan_seeds: bool) -> dict:
    run_root = Path(plan["run_root"])
    if not COSIMA.is_file() or not ENV.is_file():
        raise RuntimeError("Cosima runtime is unavailable")
    for job in plan["jobs"]:
        for key in ("source", "eventlist", "geometry_setup"):
            if not Path(job[key]).is_file():
                raise RuntimeError(f"missing {key}: {job[key]}")
        if sha256(Path(job["source"])) != job["source_sha256"]:
            raise RuntimeError(f"source hash mismatch: {job['job_id']}")
        if sha256(Path(job["eventlist"])) != job["eventlist_sha256"]:
            raise RuntimeError(f"eventlist hash mismatch: {job['job_id']}")
    selected = {int(j["seed"]) for j in plan["jobs"]}
    collisions = scan_sim_seed_collisions(selected, run_root) if scan_seeds else []
    if collisions:
        raise RuntimeError(f"registered SIM seed collision(s): {collisions[:20]}")
    disk = shutil.disk_usage(existing_ancestor(run_root))
    if disk.free < plan["memory_policy"]["minimum_free_disk_bytes"]:
        raise RuntimeError(f"free disk below gate: {disk.free}")
    return {
        "status": "PASS",
        "sim_seed_scan_complete": scan_seeds,
        "selected_seeds": sorted(selected),
        "mem_available_kib": mem_available_kib(),
        "free_disk_bytes": disk.free,
    }


def run(plan: dict, *, plan_path: Path, ledger_path: Path) -> None:
    gate = preflight(plan, scan_seeds=True)
    run_root = Path(plan["run_root"])
    run_root.mkdir(parents=True, exist_ok=True)
    ledger = {
        "schema_version": 1,
        "status": "RUNNING",
        "plan_sha256": sha256(plan_path),
        "preflight": gate,
        "jobs": [],
    }
    atomic_json(ledger_path, ledger)
    policy = plan["memory_policy"]
    for index, job in enumerate(plan["jobs"], start=1):
        final_dir = Path(job["final_dir"])
        partial_dir = Path(job["partial_dir"])
        if final_dir.exists() or partial_dir.exists():
            raise RuntimeError(f"refusing to overwrite existing attempt: {job['job_id']}")
        waits = 0
        while mem_available_kib() < policy["minimum_mem_available_kib"]:
            if waits >= 30:
                raise RuntimeError("memory gate did not recover within 5 minutes")
            print(f"WAIT_MEMORY {job['job_id']} MemAvailableKiB={mem_available_kib()}", flush=True)
            time.sleep(10)
            waits += 1
        free = shutil.disk_usage(existing_ancestor(run_root)).free
        if free < policy["minimum_free_disk_bytes"]:
            raise RuntimeError(f"disk gate failed before {job['job_id']}: {free}")
        partial_dir.mkdir(parents=True)
        print(
            f"START {index}/{len(plan['jobs'])} {job['job_id']} "
            f"MemAvailableKiB={mem_available_kib()} free={free}",
            flush=True,
        )
        started = time.monotonic()
        proc = subprocess.run(
            [
                "bash", "-lc",
                'source "$1"\nexec "$2" -s "$3" "$4"',
                "bash", str(ENV), str(COSIMA), str(job["seed"]), job["source"],
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        elapsed = time.monotonic() - started
        (partial_dir / "cosima.log").write_text(proc.stdout, encoding="utf-8")
        if proc.returncode != 0:
            raise RuntimeError(f"Cosima failed for {job['job_id']} rc={proc.returncode}")
        sims = list(partial_dir.glob("*.sim.gz"))
        if len(sims) != 1:
            raise RuntimeError(f"expected one SIM for {job['job_id']}, found {len(sims)}")
        sim = validate_sim(sims[0], job, policy["sim_file_cap_bytes"])
        os.replace(partial_dir, final_dir)
        sim["path"] = str((final_dir / Path(sim["path"]).name).resolve())
        record = {
            "job_id": job["job_id"],
            "cell_id": job["cell_id"],
            "geometry_key": job["geometry_key"],
            "elapsed_s": elapsed,
            "sim": sim,
        }
        ledger["jobs"].append(record)
        atomic_json(ledger_path, ledger)
        print(f"PASS {job['job_id']} elapsed={elapsed:.2f}s bytes={sim['bytes']}", flush=True)
    ledger["status"] = "PASS_LC1_SERIAL_SMOKE_TRANSPORT"
    ledger["total_events"] = sum(j["sim"]["events"] for j in ledger["jobs"])
    ledger["total_bytes"] = sum(j["sim"]["bytes"] for j in ledger["jobs"])
    atomic_json(ledger_path, ledger)
    print(ledger["status"], flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--launch", metavar="TOKEN")
    parser.add_argument("--plan-path", type=Path, default=PLAN_PATH)
    parser.add_argument("--ledger-path", type=Path, default=LEDGER_PATH)
    args = parser.parse_args()
    plan = json.loads(args.plan_path.read_text(encoding="utf-8"))
    if args.preflight:
        print(json.dumps(preflight(plan, scan_seeds=True), indent=2, sort_keys=True))
        return
    if args.launch != plan["confirmation_token"]:
        raise RuntimeError("exact confirmation token is required")
    run(plan, plan_path=args.plan_path, ledger_path=args.ledger_path)


if __name__ == "__main__":
    main()
