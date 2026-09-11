#!/usr/bin/env python3
"""Preflight or explicitly launch the O8 equal-statistics e+/neutron screen.

The default invocation only prepares and audits 16 deterministic job cards.
Cosima production requires both ``--launch`` and an exact confirmation token.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from _o8_replay_common import (
    AuditError,
    DATA,
    PACKAGE,
    ROOT,
    S3D_GEOMETRY_SETUP,
    audit_geometry_authority,
    canonicalize_source,
    cosima_environment,
    rel,
    sha256,
    source_run_name,
    source_scalar,
)


PREPARER = PACKAGE / "code/prepare_o8_prompt_eqstats.py"
SHARED_RUNNER = ROOT / "code/tools/run_equiv2602_pipeline_NEW_GEO.py"
SOURCE_DIR = PACKAGE / "config/prompt_eqstats_eplus_n/source_cards"
SOURCE_MANIFEST = SOURCE_DIR / "source_migration_manifest.json"
PREFLIGHT = DATA / "s3d_o8_prompt_eqstats_preflight.json"
RUN_DIR = (
    ROOT
    / "runs/geometry_optimization_20260704"
    / "s3d_o8_eqstats_prompt_eplus_n_20260712"
)
O9_RUN_DIR = (
    ROOT
    / "runs/geometry_optimization_20260704"
    / "s3d_lightweight_eqstats_prompt_eplus_n_20260712"
)
PINNED_RUNNER_SHA256 = "22d1eb345c9bce3a906b18cf55f72de3c29a0aa47bf9adb955b62532090aa568"
CONFIRMATION = "O8_EQSTATS_EPLUS_N_16JOBS_9654344"
EXPECTED_EVENTS = {"eplus": 243_727, "n": 963_066}
EXPECTED_SEEDS = {
    "eplus": [1_007_922, 1_015_841, 1_023_760, 1_031_679, 1_039_598, 1_047_517, 1_055_436, 1_063_355],
    "n": [1_071_274, 1_079_193, 1_087_112, 1_095_031, 1_102_950, 1_110_869, 1_118_788, 1_126_707],
}
GEOMETRY_RE = re.compile(r"^Geometry\s+(\S+)\s*$", re.M)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def run_checked(command: list[str], *, env: dict[str, str] | None = None) -> None:
    proc = subprocess.run(command, cwd=ROOT, env=env, check=False)
    if proc.returncode != 0:
        raise AuditError(f"command failed with {proc.returncode}: {' '.join(command)}")


def runner_command(*, workers: int, prepare_only: bool, allow_heavy: bool) -> list[str]:
    command = [
        sys.executable,
        str(SHARED_RUNNER),
        "--mode",
        "instant",
        "--source-dir",
        str(SOURCE_DIR),
        "--outdir",
        str(RUN_DIR),
        "--gamma-events",
        "10000000",
        "--gamma-splits",
        "12",
        "--non-gamma-replicas",
        "8",
        "--workers",
        str(workers),
        "--particles",
        "eplus,n",
        "--farfield-radius-cm",
        "60",
        "--keep-sources",
    ]
    if prepare_only:
        command.append("--prepare-sources-only")
    if allow_heavy:
        command.append("--allow-heavy-run")
    return command


def production_artifacts() -> list[str]:
    if not RUN_DIR.exists():
        return []
    found: list[str] = []
    for path in RUN_DIR.rglob("*"):
        if not path.is_file():
            continue
        name = path.name
        if (
            name.endswith((".sim", ".sim.gz", ".dat"))
            or name.startswith("cosima_")
            or path.parent.name == "logs"
        ):
            found.append(rel(path))
    return sorted(found)


def normalized_job_source(path: Path) -> str:
    """Normalize only geometry plus output-file metadata in a job source."""
    text = path.read_text(encoding="utf-8")
    run_name = source_run_name(text)
    geometry = source_scalar(text, "Geometry")
    output_prefix = source_scalar(text, f"{run_name}.FileName")
    canonical = canonicalize_source(
        text,
        run_name=run_name,
        geometry=geometry,
        output_prefix=output_prefix,
    )
    out: list[str] = []
    for line in canonical.splitlines():
        if line.startswith("# geometry_setup="):
            out.append("# geometry_setup=<PINNED_GEOMETRY_SETUP>")
        elif ".IsotopeProductionFile " in line:
            prefix = line.split(".IsotopeProductionFile", 1)[0]
            out.append(f"{prefix}.IsotopeProductionFile <ISOTOPE_OUTPUT_PREFIX>")
        else:
            out.append(line)
    return "\n".join(out) + "\n"


def expected_job_contract() -> dict[tuple[str, int], tuple[int, int]]:
    return {
        (particle, rep): (EXPECTED_EVENTS[particle], seed)
        for particle, seeds in EXPECTED_SEEDS.items()
        for rep, seed in enumerate(seeds, start=1)
    }


def memory_available_bytes() -> int | None:
    path = Path("/proc/meminfo")
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    return None


def static_preflight(workers: int) -> dict[str, Any]:
    audit_geometry_authority()
    for path in (
        SOURCE_MANIFEST,
        RUN_DIR / "normalization.json",
        RUN_DIR / "run_manifest.csv",
        O9_RUN_DIR / "run_manifest.csv",
    ):
        if not path.is_file():
            raise AuditError(f"missing prompt preflight authority: {rel(path)}")
    source_manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    normalization = json.loads((RUN_DIR / "normalization.json").read_text(encoding="utf-8"))
    jobs = read_csv(RUN_DIR / "run_manifest.csv")
    o9_jobs = read_csv(O9_RUN_DIR / "run_manifest.csv")
    o9_by_key = {(row["particle"], int(row["rep"])): row for row in o9_jobs}
    expected = expected_job_contract()
    problems: list[str] = []
    if sha256(SHARED_RUNNER) != PINNED_RUNNER_SHA256:
        problems.append("shared runner SHA-256 differs from the reviewed authority")
    if source_manifest.get("status") != "PASS_O8_PROMPT_EQSTATS_SOURCE_COPY_PREPARED":
        problems.append(f"O8 source manifest status={source_manifest.get('status')!r}")
    expected_norm = {
        "mode": "instant",
        "gamma_events": 10_000_000,
        "gamma_splits": 12,
        "non_gamma_replicas": 8,
        "farfield_radius_cm": 60.0,
        "jobs": 16,
        "store_isotopes": True,
    }
    for key, value in expected_norm.items():
        if normalization.get(key) != value:
            problems.append(f"normalization {key}={normalization.get(key)!r}, expected {value!r}")
    if normalization.get("selected_particles") != ["eplus", "n"]:
        problems.append(f"selected particles={normalization.get('selected_particles')!r}")
    if len(jobs) != 16:
        problems.append(f"job count={len(jobs)}, expected 16")

    run_root = RUN_DIR.resolve()
    source_root = SOURCE_DIR.resolve()
    seen: set[tuple[str, int]] = set()
    seen_seeds: set[int] = set()
    job_audit: list[dict[str, Any]] = []
    for row in jobs:
        particle = row["particle"]
        rep = int(row["rep"])
        key = (particle, rep)
        events = int(row["events"])
        seed = int(row["seed"])
        source = Path(row["source"]).resolve()
        job_source = Path(row["temp_source"]).resolve()
        sim = Path(row["sim_path"]).resolve()
        dat = Path(row["dat_path"]).resolve()
        log = Path(row["log"]).resolve()
        reference = o9_by_key.get(key)
        ref_source = Path(reference["temp_source"]).resolve() if reference else None
        expected_pair = expected.get(key)
        text = job_source.read_text(encoding="utf-8") if job_source.is_file() else ""
        checks = {
            "expected_particle_replica": expected_pair is not None,
            "events_exact": expected_pair is not None and events == expected_pair[0],
            "seed_exact": expected_pair is not None and seed == expected_pair[1],
            "unique_particle_replica": key not in seen,
            "unique_seed": seed not in seen_seeds,
            "source_under_o8_config": source.is_relative_to(source_root),
            "job_source_under_new_run": job_source.is_relative_to(run_root),
            "sim_under_new_run": sim.is_relative_to(run_root),
            "dat_under_new_run": dat.is_relative_to(run_root),
            "log_under_new_run": log.is_relative_to(run_root),
            "job_source_exists": job_source.is_file(),
            "one_o8_geometry": GEOMETRY_RE.findall(text) == [rel(S3D_GEOMETRY_SETUP)],
            "instant_mode": "DecayMode ActivationBuildUp" not in text,
            "store_isotopes": "StoreIsotopes true" in text,
            "store_simulation_info_all": "StoreSimulationInfo all" in text,
            "events_directive_exact": f".Events {events}" in text,
            "seed_directive_exact": f"Seed {seed}" in text,
            "completed_o9_job_exists": bool(ref_source and ref_source.is_file()),
            "canonical_equal_to_completed_o9": bool(
                ref_source
                and ref_source.is_file()
                and job_source.is_file()
                and normalized_job_source(job_source) == normalized_job_source(ref_source)
            ),
        }
        seen.add(key)
        seen_seeds.add(seed)
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            problems.append(f"{row['job_name']}: failed {failed}")
        job_audit.append(
            {
                "job_name": row["job_name"],
                "particle": particle,
                "replica": rep,
                "events": events,
                "seed": seed,
                "source": rel(source),
                "job_source": rel(job_source),
                "completed_o9_job_source": rel(ref_source) if ref_source else None,
                "checks": checks,
                "status": "PASS" if not failed else "FAIL",
            }
        )

    if seen != set(expected):
        problems.append(f"particle/replica set mismatch: {sorted(seen)}")
    if len(seen_seeds) != 16:
        problems.append(f"unique seed count={len(seen_seeds)}, expected 16")
    total = sum(int(row["events"]) for row in jobs)
    if total != 9_654_344:
        problems.append(f"total events={total}, expected 9,654,344")
    if production_artifacts():
        problems.append(f"production artifacts already present: {production_artifacts()}")

    _env, environment = cosima_environment()
    disk = shutil.disk_usage(ROOT)
    payload = {
        "status": "PASS_O8_PROMPT_EQSTATS_PREFLIGHT" if not problems else "FAIL",
        "scope": "job-card/source validation only; no Cosima transport result",
        "run_dir": rel(RUN_DIR),
        "source_dir": rel(SOURCE_DIR),
        "source_manifest": rel(SOURCE_MANIFEST),
        "geometry_setup": rel(S3D_GEOMETRY_SETUP),
        "geometry_setup_sha256": sha256(S3D_GEOMETRY_SETUP),
        "shared_runner": rel(SHARED_RUNNER),
        "shared_runner_sha256": sha256(SHARED_RUNNER),
        "pinned_shared_runner_sha256": PINNED_RUNNER_SHA256,
        "transport_environment": environment,
        "workers_requested": workers,
        "total_requested_events": total,
        "normalization": normalization,
        "jobs": job_audit,
        "host_snapshot": {
            "disk_free_bytes": disk.free,
            "memory_available_bytes": memory_available_bytes(),
            "cpu_count": os.cpu_count(),
        },
        "launch_contract": {
            "confirmation": CONFIRMATION,
            "command": (
                f"python3 {rel(Path(__file__))} --launch --allow-heavy-run "
                f"--confirm {CONFIRMATION} --workers {workers}"
            ),
        },
        "production_launched": False,
        "problems": problems,
    }
    PREFLIGHT.parent.mkdir(parents=True, exist_ok=True)
    PREFLIGHT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (RUN_DIR / "preflight_validation.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if problems:
        raise AuditError("O8 prompt preflight failed: " + "; ".join(problems))
    return payload


def self_test() -> dict[str, Any]:
    expected = expected_job_contract()
    if len(expected) != 16 or sum(value[0] for value in expected.values()) != 9_654_344:
        raise AuditError("internal prompt statistics contract is inconsistent")
    if len({value[1] for value in expected.values()}) != 16:
        raise AuditError("internal prompt seed contract is not unique")
    if PINNED_RUNNER_SHA256 != sha256(SHARED_RUNNER):
        raise AuditError("reviewed shared runner hash changed")
    return {
        "status": "PASS_SELF_TEST",
        "jobs": len(expected),
        "events": sum(value[0] for value in expected.values()),
        "unique_seeds": len({value[1] for value in expected.values()}),
        "production_launched": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--launch", action="store_true")
    parser.add_argument("--allow-heavy-run", action="store_true")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            print(json.dumps(self_test(), indent=2))
            return 0
        if not 1 <= args.workers <= 16:
            raise AuditError("--workers must be in 1..16")
        if args.launch and (not args.allow_heavy_run or args.confirm != CONFIRMATION):
            raise AuditError(
                f"production requires --allow-heavy-run and --confirm {CONFIRMATION}"
            )
        if not args.launch and (args.allow_heavy_run or args.confirm):
            raise AuditError("heavy-run acknowledgement/confirmation is valid only with --launch")
        if production_artifacts():
            raise AuditError(
                "dated O8 prompt directory already contains production artifacts; "
                "refusing to overwrite or append"
            )
        audit_geometry_authority()
        run_checked([sys.executable, str(PREPARER)])
        run_checked(runner_command(workers=args.workers, prepare_only=True, allow_heavy=False))
        audit = static_preflight(args.workers)
        if not args.launch:
            print(
                json.dumps(
                    {
                        "status": audit["status"],
                        "preflight": rel(PREFLIGHT),
                        "jobs": len(audit["jobs"]),
                        "events": audit["total_requested_events"],
                        "production_launched": False,
                    },
                    indent=2,
                )
            )
            return 0
        env, _evidence = cosima_environment()
        run_checked(runner_command(workers=args.workers, prepare_only=False, allow_heavy=True), env=env)
        print(
            json.dumps(
                {
                    "status": "O8_PROMPT_PRODUCTION_RUNNER_RETURNED",
                    "run_dir": rel(RUN_DIR),
                    "production_launched": True,
                    "next": "run the screening analyzer; transport success is not inferred here",
                },
                indent=2,
            )
        )
        return 0
    except (AuditError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
