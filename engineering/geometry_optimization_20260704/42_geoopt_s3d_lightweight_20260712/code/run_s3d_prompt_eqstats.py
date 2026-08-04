#!/usr/bin/env python3
"""Preflight or launch the pinned S3d equal-stat e+/neutron production.

Without --launch this is a safe preflight: it prepares the source cards, asks
the shared 2602-equivalent runner to materialize all 16 job cards, and writes a
static validation record.  Production requires both --launch and the explicit
--allow-heavy-run acknowledgement.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712"
PREPARER = PACKAGE / "code/prepare_s3d_prompt_eqstats.py"
SHARED_RUNNER = ROOT / "code/tools/run_equiv2602_pipeline_NEW_GEO.py"
MEGALIB_ENV_SCRIPT = (
    ROOT
    / "engineering/Mass_model_511_nearfield_migration_20260701/"
    "05_optics_migration/megalib_env.sh"
)
SOURCE_DIR = PACKAGE / "config/prompt_eqstats_eplus_n/source_cards"
SOURCE_MANIFEST = SOURCE_DIR / "source_migration_manifest.json"
DATA_AUDIT = PACKAGE / "data/s3d_prompt_eqstats_preflight.json"
RUN_DIR = (
    ROOT
    / "runs/geometry_optimization_20260704/"
    "s3d_lightweight_eqstats_prompt_eplus_n_20260712"
)
TARGET_GEOMETRY = (
    "engineering/geometry_optimization_20260704/"
    "42_geoopt_s3d_lightweight_20260712/geometry/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
BASE_GEOMETRY = (
    "engineering/geometry_optimization_20260704/"
    "29_geoopt_s3c_bgo_w2mm_al3mm_shell_20260709/geometry/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
PINNED_RUNNER_SHA256 = "22d1eb345c9bce3a906b18cf55f72de3c29a0aa47bf9adb955b62532090aa568"
PINNED_MEGALIB_ENV_SHA256 = "0702319ea5d152912b68df65038c1a075cef48b39142d3c7311c7b305944fecd"
EXPECTED_EVENTS_PER_REPLICA = {"eplus": 243_727, "n": 963_066}
GEOMETRY_RE = re.compile(r"^Geometry\s+(\S+)\s*$", re.MULTILINE)


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_checked(command: list[str], *, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command))
    proc = subprocess.run(command, cwd=ROOT, env=env, check=False)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def cosima_environment() -> tuple[dict[str, str], dict[str, Any]]:
    """Load the retained project MEGAlib environment without shell interpolation."""
    if not MEGALIB_ENV_SCRIPT.is_file():
        raise SystemExit(f"Missing MEGAlib environment authority: {rel(MEGALIB_ENV_SCRIPT)}")
    env_hash = sha256_file(MEGALIB_ENV_SCRIPT)
    if env_hash != PINNED_MEGALIB_ENV_SHA256:
        raise SystemExit(
            f"MEGAlib environment script changed: {env_hash} != {PINNED_MEGALIB_ENV_SHA256}"
        )
    proc = subprocess.run(
        ["/bin/bash", "-c", 'source "$1"\nenv -0', "s3d-megalib-env", str(MEGALIB_ENV_SCRIPT)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", errors="replace").strip()
        raise SystemExit(f"Unable to load {rel(MEGALIB_ENV_SCRIPT)}: {detail}")
    env: dict[str, str] = {}
    for item in proc.stdout.split(b"\0"):
        if not item or b"=" not in item:
            continue
        key, value = item.split(b"=", 1)
        env[key.decode("utf-8", errors="strict")] = value.decode("utf-8", errors="strict")

    required_vars = (
        "MEGALIB",
        "G4NEUTRONHPDATA",
        "G4LEDATA",
        "G4LEVELGAMMADATA",
        "G4RADIOACTIVEDATA",
        "G4NEUTRONXSDATA",
        "G4PIIDATA",
        "G4REALSURFACEDATA",
        "G4SAIDXSDATA",
        "G4ABLADATA",
        "G4ENSDFSTATEDATA",
    )
    missing_vars = [key for key in required_vars if not env.get(key)]
    missing_paths = [key for key in required_vars if env.get(key) and not Path(env[key]).exists()]
    cosima = Path(env.get("MEGALIB", "")) / "bin/cosima"
    if missing_vars or missing_paths or not cosima.is_file() or not os.access(cosima, os.X_OK):
        raise SystemExit(
            "Invalid MEGAlib environment: "
            f"missing_vars={missing_vars}, missing_paths={missing_paths}, cosima={cosima}"
        )
    evidence = {
        "script": rel(MEGALIB_ENV_SCRIPT),
        "script_sha256": env_hash,
        "pinned_script_sha256": PINNED_MEGALIB_ENV_SHA256,
        "megalib": env["MEGALIB"],
        "cosima": str(cosima),
        "required_dataset_paths": {key: env[key] for key in required_vars if key != "MEGALIB"},
        "all_required_paths_exist": True,
        "cosima_executable": True,
        "status": "PASS",
    }
    return env, evidence


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


def memory_available_bytes() -> int | None:
    meminfo = Path("/proc/meminfo")
    if not meminfo.is_file():
        return None
    for line in meminfo.read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    return None


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def static_preflight(workers: int) -> dict[str, Any]:
    runner_hash = sha256_file(SHARED_RUNNER)
    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    normalization = json.loads((RUN_DIR / "normalization.json").read_text(encoding="utf-8"))
    jobs = read_csv(RUN_DIR / "run_manifest.csv")

    problems: list[str] = []
    if runner_hash != PINNED_RUNNER_SHA256:
        problems.append(
            f"shared runner hash changed: {runner_hash} != pinned {PINNED_RUNNER_SHA256}"
        )
    if manifest.get("status") != "PASS_S3D_PROMPT_EQSTATS_SOURCE_COPY_PREPARED":
        problems.append("source migration manifest is not PASS")
    if manifest.get("geometry_setup") != TARGET_GEOMETRY:
        problems.append("source migration manifest is not pinned to the S3d setup")
    if normalization.get("selected_particles") != ["eplus", "n"]:
        problems.append(f"selected particle mismatch: {normalization.get('selected_particles')}")
    expected_normalization = {
        "mode": "instant",
        "gamma_events": 10_000_000,
        "gamma_splits": 12,
        "non_gamma_replicas": 8,
        "farfield_radius_cm": 60.0,
        "store_isotopes": True,
        "jobs": 16,
    }
    for key, expected in expected_normalization.items():
        if normalization.get(key) != expected:
            problems.append(f"normalization {key}={normalization.get(key)!r}, expected {expected!r}")
    for particle, events in EXPECTED_EVENTS_PER_REPLICA.items():
        actual = normalization.get("base_events_by_particle", {}).get(particle)
        if actual != events:
            problems.append(f"{particle} events/replica={actual}, expected {events}")

    run_root = RUN_DIR.resolve()
    source_root = SOURCE_DIR.resolve()
    job_audit: list[dict[str, Any]] = []
    seen_seeds: set[int] = set()
    for row in jobs:
        particle = row["particle"]
        source = Path(row["source"]).resolve()
        temp_source = Path(row["temp_source"]).resolve()
        sim_path = Path(row["sim_path"]).resolve()
        dat_path = Path(row["dat_path"]).resolve()
        log_path = Path(row["log"]).resolve()
        seed = int(row["seed"])
        events = int(row["events"])
        rep = int(row["rep"])
        text = temp_source.read_text(encoding="utf-8") if temp_source.is_file() else ""
        geometry_lines = GEOMETRY_RE.findall(text)
        checks = {
            "particle": particle in EXPECTED_EVENTS_PER_REPLICA,
            "replica": 1 <= rep <= 8,
            "events": events == EXPECTED_EVENTS_PER_REPLICA.get(particle),
            "unique_seed": seed not in seen_seeds,
            "source_under_pinned_config": source.is_relative_to(source_root),
            "job_source_under_new_run": temp_source.is_relative_to(run_root),
            "sim_under_new_run": sim_path.is_relative_to(run_root),
            "dat_under_new_run": dat_path.is_relative_to(run_root),
            "log_under_new_run": log_path.is_relative_to(run_root),
            "job_source_exists": temp_source.is_file(),
            "one_s3d_geometry": geometry_lines == [TARGET_GEOMETRY],
            "retired_s3c_geometry_absent": BASE_GEOMETRY not in text,
            "isotope_store_retained": "StoreIsotopes true" in text,
            # The retained card contains ActivationBuildUp, but the shared
            # runner intentionally removes DecayMode in instant mode.  This is
            # the exact retained S3c prompt behavior, not a delayed-chain run.
            "instant_mode_decay_removed": "DecayMode ActivationBuildUp" not in text,
            "store_simulation_info_all": "StoreSimulationInfo all" in text,
            "events_patched": f".Events {events}" in text,
            "seed_patched": f"Seed {seed}" in text,
        }
        seen_seeds.add(seed)
        failed = [key for key, passed in checks.items() if not passed]
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
                "job_source": rel(temp_source),
                "geometry_lines": geometry_lines,
                "checks": checks,
                "status": "PASS" if not failed else "FAIL",
            }
        )

    for particle in EXPECTED_EVENTS_PER_REPLICA:
        reps = sorted(int(row["rep"]) for row in jobs if row["particle"] == particle)
        if reps != list(range(1, 9)):
            problems.append(f"{particle} replicas are {reps}, expected 1..8")
    if len(jobs) != 16:
        problems.append(f"job count={len(jobs)}, expected 16")
    if len(seen_seeds) != 16:
        problems.append(f"unique seed count={len(seen_seeds)}, expected 16")

    total_events = sum(int(row["events"]) for row in jobs)
    if total_events != 9_654_344:
        problems.append(f"total requested events={total_events}, expected 9,654,344")

    _, environment_evidence = cosima_environment()
    disk = shutil.disk_usage(ROOT)
    measured_reference = {
        "reference_run": (
            "runs/geometry_optimization_20260704/"
            "s3c_bgo_w2mm_al3mm_shell_eqstats_prompt_eplus_n_20260709"
        ),
        "same_requested_events": 9_654_344,
        "measured_cpu_s": 8_730.053,
        "measured_sim_bytes": 4_345_478_254,
        "measured_log_and_other_bytes": 1_255_600_127,
        "measured_total_bytes": 5_601_078_381,
        "planning_disk_free_bytes_min": 8_000_000_000,
        "planning_peak_ram_bytes": 12_000_000_000,
        "note": (
            "S3d geometry may change event multiplicity. The retained S3c run is a planning "
            "anchor, not a guaranteed S3d output-size or runtime prediction."
        ),
    }
    audit = {
        "status": "PASS" if not problems else "FAIL",
        "scope": "pre-production source/job-card validation; no Cosima transport claim",
        "production_label": "s3d_lightweight_eqstats_prompt_eplus_n_20260712",
        "run_dir": rel(RUN_DIR),
        "source_dir": rel(SOURCE_DIR),
        "source_manifest": rel(SOURCE_MANIFEST),
        "geometry_setup": TARGET_GEOMETRY,
        "geometry_setup_sha256": sha256_file(ROOT / TARGET_GEOMETRY),
        "shared_runner": rel(SHARED_RUNNER),
        "shared_runner_sha256": runner_hash,
        "pinned_shared_runner_sha256": PINNED_RUNNER_SHA256,
        "transport_environment": environment_evidence,
        "workers_requested": workers,
        "normalization": {
            key: normalization.get(key)
            for key in (
                "mode",
                "gamma_events",
                "gamma_splits",
                "non_gamma_replicas",
                "gamma_flux_cm2_s",
                "gamma_norm_factor_cm2_s_per_count",
                "non_gamma_combined_norm_factor_cm2_s_per_count",
                "farfield_radius_cm",
                "farfield_area_cm2",
                "gamma_prompt_time_s_with_farfield_area",
                "base_events_by_particle",
                "selected_particles",
                "jobs",
                "store_isotopes",
            )
        },
        "total_requested_events": total_events,
        "jobs": job_audit,
        "resource_planning_anchor": measured_reference,
        "host_snapshot": {
            "disk_free_bytes": disk.free,
            "memory_available_bytes": memory_available_bytes(),
            "cpu_count": os.cpu_count(),
        },
        "problems": problems,
    }
    DATA_AUDIT.parent.mkdir(parents=True, exist_ok=True)
    DATA_AUDIT.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    (RUN_DIR / "preflight_validation.json").write_text(
        json.dumps(audit, indent=2) + "\n", encoding="utf-8"
    )
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}")
        raise SystemExit("S3d prompt preflight failed")
    return audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--launch", action="store_true", help="Launch the 16 production jobs after preflight")
    parser.add_argument(
        "--allow-heavy-run",
        action="store_true",
        help="Required with --launch; acknowledges the measured ~5.6 GB S3c planning anchor",
    )
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args()
    if args.workers < 1 or args.workers > 16:
        raise SystemExit("--workers must be in 1..16 for this 16-job harness")
    if args.launch and not args.allow_heavy_run:
        raise SystemExit("Production requires both --launch and --allow-heavy-run")
    if args.allow_heavy_run and not args.launch:
        raise SystemExit("--allow-heavy-run is meaningful only with --launch")

    run_checked([sys.executable, str(PREPARER)])
    if sha256_file(SHARED_RUNNER) != PINNED_RUNNER_SHA256:
        raise SystemExit("Shared runner changed; review and deliberately update the pinned hash")

    # Always materialize and inspect the exact 16 cards before any production.
    run_checked(runner_command(workers=args.workers, prepare_only=True, allow_heavy=False))
    audit = static_preflight(args.workers)
    print(
        f"PASS preflight jobs={len(audit['jobs'])} events={audit['total_requested_events']:,} "
        f"audit={rel(DATA_AUDIT)}"
    )
    if not args.launch:
        print("No Cosima transport launched. Add --launch --allow-heavy-run after reviewing the audit.")
        return 0

    transport_env, _ = cosima_environment()
    run_checked(
        runner_command(workers=args.workers, prepare_only=False, allow_heavy=True),
        env=transport_env,
    )
    print(f"Production runner completed; inspect {rel(RUN_DIR / 'run_summary.md')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
