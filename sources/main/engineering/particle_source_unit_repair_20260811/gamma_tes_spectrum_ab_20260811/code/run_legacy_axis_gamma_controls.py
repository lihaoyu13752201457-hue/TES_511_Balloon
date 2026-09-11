#!/usr/bin/env python3
"""Run isolated legacy-axis gamma controls for a TES spectrum A/B diagnostic.

The corrected-keV arm is the already validated batch0001 instant gamma sample.
This script creates only the historical factor-1000 control arm.  The control
is deliberately diagnostic-only and can never be credited to a production or
merge ledger.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def find_root(path: Path) -> Path:
    for candidate in (path, *path.parents):
        if (candidate / ".git").exists() and (candidate / "AGENTS.md").is_file():
            return candidate
    raise RuntimeError("repository root not found")


THIS_FILE = Path(__file__).resolve()
ROOT = find_root(THIS_FILE.parent)
REPAIR = ROOT / "engineering/particle_source_unit_repair_20260811"
COMMON_CODE = REPAIR / "code"
if str(COMMON_CODE) not in sys.path:
    sys.path.insert(0, str(COMMON_CODE))

import run_mergeable_two_geometry_smoke as smoke  # noqa: E402
import validate_mergeable_two_geometry_smoke as dynamic  # noqa: E402


AUTHORITY = "DIAGNOSTIC_ONLY__LEGACY_AXIS__NON_MERGEABLE"
DIAGNOSTIC_ID = "prompt_gamma_tes_axis_ab_legacy_control_20260811_v1"
GAMMA_EVENTS = 100_000
SPLITS = 4
EVENTS_PER_SPLIT = GAMMA_EVENTS // SPLITS
SEED_BASE = 85_100_003
SEED_STRIDE = 7_919
EXPECTED_SEEDS = [SEED_BASE + part * SEED_STRIDE for part in range(1, SPLITS + 1)]
LEGACY_SPECTRUM_ROOT = ROOT / "expacs_fullsphere_20bin_sources/cosima_spectra_dp_2602units"
CORRECTED_SPECTRUM_ROOT = REPAIR / "spectra/correct_keV_total"
CURRENT_LEDGER = ROOT / "runs/particle_source_unit_repair_20260811/seven_family_batch0001_v1_ledger.json"
RUN_ROOT = ROOT / "runs/particle_source_unit_repair_20260811/gamma_tes_spectrum_ab_20260811"
CONTRACT = RUN_ROOT / "legacy_axis_gamma_control_contract.json"
VALIDATION = RUN_ROOT / "legacy_axis_gamma_control_validation.json"
SUMMARY = RUN_ROOT / "legacy_axis_gamma_control_run_summary.json"
COSIMA_DEFAULT = Path("/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima")
DISK_RESERVE_BYTES = 20_000_000_000
PLANNED_OUTPUT_BYTES = 100_000_000

GEOMETRIES = {
    "mass_model_511": {
        "current_dir": ROOT
        / "runs/particle_source_unit_repair_20260811/mass_model_511/instant_seven_family_batch0001_v1",
        "legacy_parent": ROOT
        / "engineering/Mass_model_511_nearfield_migration_20260701/03_source_migration/source_dirs/Mass_model_511/Background_gamma_fullsphere20.source",
    },
    "s3d_o8": {
        "current_dir": ROOT
        / "runs/particle_source_unit_repair_20260811/s3d_o8/instant_seven_family_batch0001_v1",
        "legacy_parent": ROOT
        / "engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/config/full_prompt_all8/source_cards/Background_gamma_fullsphere20.source",
    },
}

GENERATED_RE = re.compile(r"Total number of generated particles:\s+(\d+)")
CPU_RE = re.compile(r"Total CPU time spent in run:\s+([-+0-9.eE]+) sec")
OBS_RE = re.compile(r"Observation time:\s+([-+0-9.eE]+) sec")
SPECTRUM_RE = re.compile(r"^(\S+\.Spectrum\s+File)\s+(\S+)\s*$")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def dp_rows(path: Path) -> list[tuple[float, float]]:
    rows: list[tuple[float, float]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[0] == "DP":
            rows.append((float(fields[1]), float(fields[2])))
    if len(rows) < 2:
        raise SystemExit(f"no usable DP spectrum in {rel(path)}")
    return rows


def spectrum_refs(path: Path) -> list[Path]:
    refs: list[Path] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = SPECTRUM_RE.match(raw.strip())
        if match:
            value = Path(match.group(2))
            refs.append(value.resolve() if value.is_absolute() else (ROOT / value).resolve())
    return refs


def line_value(path: Path, prefix: str) -> str:
    matches = [
        line.strip().split(maxsplit=1)[1]
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip().startswith(prefix + " ")
    ]
    if len(matches) != 1:
        raise SystemExit(f"{rel(path)}: expected one {prefix!r} line, found {len(matches)}")
    return matches[0]


def current_gamma_jobs(ledger: dict[str, Any], geometry: str) -> list[dict[str, Any]]:
    campaigns = [
        item
        for item in ledger.get("campaigns", [])
        if item.get("geometry") == geometry and item.get("mode") == "instant"
    ]
    if len(campaigns) != 1:
        raise SystemExit(f"current ledger has {len(campaigns)} instant campaigns for {geometry}")
    jobs = [item for item in campaigns[0].get("jobs", []) if item.get("family") == "gamma"]
    jobs.sort(key=lambda item: item["job_name"])
    if len(jobs) != SPLITS or sum(int(item["events"]) for item in jobs) != GAMMA_EVENTS:
        raise SystemExit(f"{geometry}: corrected gamma reference is not 4 x 25,000")
    return jobs


def validate_axis_pair() -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for corrected in sorted(CORRECTED_SPECTRUM_ROOT.glob("gamma_bin*.spectrum")):
        legacy = LEGACY_SPECTRUM_ROOT / corrected.name.replace(".spectrum", ".dat")
        if not legacy.is_file():
            raise SystemExit(f"missing legacy spectrum {rel(legacy)}")
        new_rows = dp_rows(corrected)
        old_rows = dp_rows(legacy)
        if len(new_rows) != len(old_rows):
            raise SystemExit(f"DP length mismatch: {rel(corrected)} vs {rel(legacy)}")
        max_x_error = 0.0
        max_y_error = 0.0
        for (new_x, new_y), (old_x, old_y) in zip(new_rows, old_rows, strict=True):
            max_x_error = max(max_x_error, abs(new_x - 1000.0 * old_x))
            max_y_error = max(max_y_error, abs(new_y - old_y))
        x_scale = max(abs(row[0]) for row in new_rows)
        y_scale = max(abs(row[1]) for row in new_rows)
        if max_x_error > max(1.0e-9, 1.0e-11 * x_scale):
            raise SystemExit(f"energy-axis ratio is not 1000 for {corrected.name}")
        # The packaged corrected spectra were regenerated from the frozen raw
        # tables at higher precision; the legacy ordinates agree to about
        # 5e-11 relative, so keep a still-strict 1e-9 numerical tolerance.
        if max_y_error > max(1.0e-15, 1.0e-9 * y_scale):
            raise SystemExit(f"relative PDF ordinates changed for {corrected.name}")
        records.append(
            {
                "bin": corrected.stem,
                "corrected": rel(corrected),
                "corrected_sha256": sha256(corrected),
                "legacy": rel(legacy),
                "legacy_sha256": sha256(legacy),
                "points": len(new_rows),
                "max_abs_x_new_minus_1000x_old_keV": max_x_error,
                "max_abs_y_difference": max_y_error,
                "legacy_support_keV": [old_rows[0][0], old_rows[-1][0]],
                "corrected_support_keV": [new_rows[0][0], new_rows[-1][0]],
            }
        )
    if len(records) != 20:
        raise SystemExit(f"expected 20 gamma angle-bin spectra, found {len(records)}")
    return {"status": "PASS", "bins": records}


def semantic_lines(path: Path) -> dict[str, list[str]]:
    groups = {key: [] for key in ("geometry", "physics", "beam", "flux", "particle")}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line.startswith("Geometry "):
            groups["geometry"].append(line)
        elif line.startswith(("PhysicsListHD ", "PhysicsListEM ", "StoreSimulationInfo ", "StoreIsotopes ", "DetectorTimeConstant ")):
            groups["physics"].append(line)
        elif ".Beam " in line:
            groups["beam"].append(line)
        elif ".Flux " in line:
            groups["flux"].append(line)
        elif ".ParticleType " in line:
            groups["particle"].append(line)
    return groups


def preflight(cosima: Path, workers: int) -> tuple[dict[str, Any], dict[str, str], dict[str, Any]]:
    if not CURRENT_LEDGER.is_file():
        raise SystemExit(f"missing corrected authority ledger: {rel(CURRENT_LEDGER)}")
    ledger = json.loads(CURRENT_LEDGER.read_text(encoding="utf-8"))
    if ledger.get("status") != "PASS__BATCH0001_MERGE_ELIGIBLE" or ledger.get("errors"):
        raise SystemExit("corrected batch0001 ledger is not PASS")
    axis = validate_axis_pair()
    corrected_inputs: dict[str, Any] = {}
    legacy_parents: dict[str, Any] = {}
    current_seed_set: set[int] = set()
    for geometry, info in GEOMETRIES.items():
        jobs = current_gamma_jobs(ledger, geometry)
        job_records: list[dict[str, Any]] = []
        for job in jobs:
            if int(job["events"]) != EVENTS_PER_SPLIT:
                raise SystemExit(f"{geometry}/{job['job_name']}: corrected split is not 25,000")
            current_seed_set.add(int(job["seed"]))
            for key, hash_key in (
                ("sim", "sim_sha256"),
                ("job_source", "job_source_sha256"),
                ("log", "log_sha256"),
                ("isotope_dat", "isotope_dat_sha256"),
            ):
                path = ROOT / job[key]
                if not path.is_file() or sha256(path) != job[hash_key]:
                    raise SystemExit(f"corrected authority artifact drift: {job[key]}")
            card = ROOT / job["job_source"]
            refs = spectrum_refs(card)
            if len(refs) != 20 or any(path.parent != CORRECTED_SPECTRUM_ROOT.resolve() for path in refs):
                raise SystemExit(f"{rel(card)}: corrected gamma references are not canonical")
            job_records.append(
                {
                    "job_name": job["job_name"],
                    "events": int(job["events"]),
                    "seed": int(job["seed"]),
                    "job_source": rel(card),
                    "job_source_sha256": sha256(card),
                    "sim": job["sim"],
                    "sim_sha256": job["sim_sha256"],
                    "log": job["log"],
                    "log_sha256": job["log_sha256"],
                    "isotope_dat": job["isotope_dat"],
                    "isotope_dat_sha256": job["isotope_dat_sha256"],
                }
            )
        corrected_inputs[geometry] = {
            "events": sum(item["events"] for item in job_records),
            "jobs": job_records,
        }
        legacy_parent = Path(info["legacy_parent"])
        if not legacy_parent.is_file():
            raise SystemExit(f"missing legacy parent card: {rel(legacy_parent)}")
        parent_refs = spectrum_refs(legacy_parent)
        if len(parent_refs) != 20 or any(path.parent != LEGACY_SPECTRUM_ROOT.resolve() for path in parent_refs):
            raise SystemExit(f"{rel(legacy_parent)}: legacy gamma references are not canonical")
        reference_card = ROOT / jobs[0]["job_source"]
        if semantic_lines(legacy_parent) != semantic_lines(reference_card):
            raise SystemExit(f"{geometry}: legacy/corrected source semantics differ outside spectrum axis")
        legacy_parents[geometry] = {
            "path": rel(legacy_parent),
            "sha256": sha256(legacy_parent),
            "geometry": line_value(legacy_parent, "Geometry"),
            "spectrum_references": len(parent_refs),
        }
    if current_seed_set & set(EXPECTED_SEEDS):
        raise SystemExit("diagnostic seed namespace overlaps the corrected reference")
    # A literal workspace scan is conservative: a planned diagnostic seed must
    # not already appear in any source/csv/json/log ledger before this run.
    for seed in EXPECTED_SEEDS:
        result = subprocess.run(
            ["rg", "-l", str(seed), "runs", "engineering"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        hits = [line for line in result.stdout.splitlines() if line.strip()]
        if hits:
            raise SystemExit(f"planned diagnostic seed {seed} already exists in workspace: {hits[:3]}")

    usage = shutil.disk_usage(ROOT)
    required = DISK_RESERVE_BYTES + 2 * PLANNED_OUTPUT_BYTES
    if usage.free < required:
        raise SystemExit(f"insufficient disk: free={usage.free}, required={required}")
    environment, env_descriptor = smoke.resolve_transport_environment(cosima)
    transport = smoke.build_transport_fingerprint(cosima, environment, env_descriptor)
    if transport != ledger.get("transport"):
        raise SystemExit("live Cosima/MEGAlib/Geant4 transport fingerprint differs from corrected batch0001")
    geometry_bundles: dict[str, Any] = {}
    for geometry in GEOMETRIES:
        bundle = smoke.build_geometry_bundle(geometry, environment)
        if bundle != ledger.get("geometry_bundles", {}).get(geometry):
            raise SystemExit(f"{geometry}: live transitive geometry bundle differs from corrected batch0001")
        geometry_bundles[geometry] = bundle
    plan = {
        "schema_version": 1,
        "status": "PREFLIGHT_PASS__NOT_YET_TRANSPORTED",
        "authority": AUTHORITY,
        "merge_eligible": False,
        "physics_authority": False,
        "diagnostic_id": DIAGNOSTIC_ID,
        "comparison_question": (
            "At fixed geometry, angular source, flux, physics list, and 100,000 gamma primaries, "
            "how does the historical factor-1000 energy axis change the TES deposited-energy spectrum?"
        ),
        "corrected_reference": {
            "ledger": rel(CURRENT_LEDGER),
            "ledger_sha256": sha256(CURRENT_LEDGER),
            "ledger_status": ledger["status"],
            "geometries": corrected_inputs,
        },
        "legacy_parent_cards": legacy_parents,
        "axis_contract": axis,
        "statistics": {
            "events_per_geometry": GAMMA_EVENTS,
            "splits": SPLITS,
            "events_per_split": EVENTS_PER_SPLIT,
            "diagnostic_seed_base": SEED_BASE,
            "seed_stride": SEED_STRIDE,
            "seeds": EXPECTED_SEEDS,
            "seed_policy": (
                "same legacy-control seeds across geometries for a geometry-matched diagnostic; "
                "disjoint from all corrected/production ledgers; never merge"
            ),
        },
        "transport": transport,
        "geometry_bundles": geometry_bundles,
        "resource_gate": {
            "planned_output_bytes": PLANNED_OUTPUT_BYTES,
            "safety_factor": 2.0,
            "reserve_bytes": DISK_RESERVE_BYTES,
            "required_free_bytes": required,
            "observed_free_bytes": usage.free,
            "workers": workers,
            "status": "PASS",
        },
        "toolchain": {
            "harness": rel(THIS_FILE),
            "harness_sha256": sha256(THIS_FILE),
            "common_transport_helper": rel(Path(smoke.__file__)),
            "common_transport_helper_sha256": sha256(Path(smoke.__file__)),
            "dynamic_validator_helper": rel(Path(dynamic.__file__)),
            "dynamic_validator_helper_sha256": sha256(Path(dynamic.__file__)),
        },
        "gamma_model_boundary": (
            "unit-only total-gamma profile; the total spectrum already contains the historical broad-bin "
            "annihilation bump, so no mono-511 source is added"
        ),
    }
    return plan, environment, transport


def frozen_input_problems(
    plan: dict[str, Any], environment: dict[str, str], cosima: Path
) -> list[str]:
    """Revalidate every causal A/B input against the frozen pre-run plan."""
    problems: list[str] = []

    try:
        live_environment, live_descriptor = smoke.resolve_transport_environment(cosima)
        live_transport = smoke.build_transport_fingerprint(
            cosima,
            live_environment,
            live_descriptor,
        )
        if live_transport != plan["transport"]:
            problems.append("transport fingerprint changed after preflight")
    except Exception as exc:  # fail closed and preserve the reason in validation
        problems.append(f"transport fingerprint recheck failed: {exc}")
        live_environment = environment

    for geometry in GEOMETRIES:
        try:
            live_bundle = smoke.build_geometry_bundle(geometry, live_environment)
            if live_bundle != plan["geometry_bundles"][geometry]:
                problems.append(f"{geometry}: transitive geometry bundle changed")
        except Exception as exc:
            problems.append(f"{geometry}: geometry bundle recheck failed: {exc}")

    for record in plan["axis_contract"]["bins"]:
        for key, hash_key in (("legacy", "legacy_sha256"), ("corrected", "corrected_sha256")):
            path = ROOT / record[key]
            if not path.is_file() or sha256(path) != record[hash_key]:
                problems.append(f"spectrum drift: {record[key]}")

    for geometry, record in plan["legacy_parent_cards"].items():
        path = ROOT / record["path"]
        if not path.is_file() or sha256(path) != record["sha256"]:
            problems.append(f"{geometry}: legacy parent card drift")

    for geometry, record in plan["corrected_reference"]["geometries"].items():
        for job in record["jobs"]:
            for path_key, hash_key in (
                ("job_source", "job_source_sha256"),
                ("sim", "sim_sha256"),
                ("log", "log_sha256"),
                ("isotope_dat", "isotope_dat_sha256"),
            ):
                path = ROOT / job[path_key]
                if not path.is_file() or sha256(path) != job[hash_key]:
                    problems.append(f"corrected reference drift: {job[path_key]}")

    for job in plan.get("legacy_jobs", []):
        path = ROOT / job["source"]
        if not path.is_file() or sha256(path) != job["source_sha256"]:
            problems.append(f"prepared legacy card drift: {job['source']}")
    return sorted(set(problems))


def legacy_output_dir(geometry: str) -> Path:
    return RUN_ROOT / geometry / "instant_legacy_axis_gamma_100k_v1"


def prepare_job(plan: dict[str, Any], geometry: str, part: int) -> dict[str, Any]:
    corrected = plan["corrected_reference"]["geometries"][geometry]["jobs"][part - 1]
    parent = ROOT / corrected["job_source"]
    outdir = legacy_output_dir(geometry)
    job_name = f"Background_gamma_fullsphere20_rep01_part{part:02d}"
    prefix = outdir / job_name
    card = outdir / "job_sources" / f"{job_name}.source"
    log = outdir / "logs" / f"{job_name}.log"
    seed = EXPECTED_SEEDS[part - 1]
    lines: list[str] = []
    ref_changes = 0
    for raw in parent.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw
        if raw.startswith("# spectrum_dir="):
            line = f"# spectrum_dir={rel(LEGACY_SPECTRUM_ROOT)}"
        elif raw.startswith("Seed "):
            line = f"Seed {seed}"
        elif ".FileName " in raw:
            name = raw.split(".FileName", 1)[0].strip()
            line = f"{name}.FileName {prefix}"
        elif ".IsotopeProductionFile " in raw:
            name = raw.split(".IsotopeProductionFile", 1)[0].strip()
            line = f"{name}.IsotopeProductionFile {prefix}.dat"
        else:
            match = SPECTRUM_RE.match(raw.strip())
            if match:
                corrected_ref = Path(match.group(2))
                legacy = LEGACY_SPECTRUM_ROOT / corrected_ref.name.replace(".spectrum", ".dat")
                line = f"{match.group(1)} {rel(legacy)}"
                ref_changes += 1
        lines.append(line)
    if ref_changes != 20:
        raise SystemExit(f"{geometry}/{job_name}: expected 20 spectrum replacements, got {ref_changes}")
    lines[1:1] = [
        f"# authority={AUTHORITY}",
        f"# diagnostic_id={DIAGNOSTIC_ID}",
        f"# parent_corrected_job_source={rel(parent)}",
        "# merge_eligible=false; never credit events, TT, or seeds to a production ledger",
    ]
    card.parent.mkdir(parents=True, exist_ok=True)
    log.parent.mkdir(parents=True, exist_ok=True)
    card.write_text("\n".join(lines) + "\n", encoding="utf-8")
    refs = spectrum_refs(card)
    if len(refs) != 20 or any(path.parent != LEGACY_SPECTRUM_ROOT.resolve() for path in refs):
        raise SystemExit(f"{geometry}/{job_name}: prepared card is not purely legacy-axis")
    if semantic_lines(card) != semantic_lines(parent):
        raise SystemExit(f"{geometry}/{job_name}: prepared card changed transport semantics")
    return {
        "geometry": geometry,
        "part": part,
        "job_name": job_name,
        "events": EVENTS_PER_SPLIT,
        "seed": seed,
        "source": rel(card),
        "source_sha256": sha256(card),
        "parent_corrected_source": rel(parent),
        "parent_corrected_source_sha256": sha256(parent),
        "sim": rel(Path(f"{prefix}.inc1.id1.sim.gz")),
        "isotope_dat": rel(Path(f"{prefix}.dat.inc1.dat")),
        "log": rel(log),
        "geometry_setup": line_value(card, "Geometry"),
        "legacy_spectrum_references": 20,
        "corrected_spectrum_references": 0,
    }


def run_one(job: dict[str, Any], cosima: Path, environment: dict[str, str]) -> dict[str, Any]:
    source = ROOT / job["source"]
    log = ROOT / job["log"]
    started = time.perf_counter()
    with log.open("w", encoding="utf-8") as handle:
        handle.write(f"authority={AUTHORITY}\n")
        handle.write(f"diagnostic_id={DIAGNOSTIC_ID}\n")
        handle.write(f"geometry={job['geometry']} part={job['part']} events={job['events']} seed={job['seed']}\n")
        handle.write(f"source={job['source']}\n")
        handle.write("-" * 72 + "\n")
        result = subprocess.run(
            [str(cosima), "-s", str(job["seed"]), str(source)],
            cwd=ROOT,
            env=environment,
            stdout=handle,
            stderr=subprocess.STDOUT,
            check=False,
        )
        wall = time.perf_counter() - started
        handle.write("\n" + "-" * 72 + "\n")
        handle.write(f"returncode={result.returncode}\nwall_s={wall:.6f}\n")
    text = log.read_text(encoding="utf-8", errors="replace")
    generated = GENERATED_RE.search(text)
    cpu = CPU_RE.search(text)
    observation = OBS_RE.search(text)
    return {
        **job,
        "returncode": result.returncode,
        "wall_s": wall,
        "generated_particles": int(generated.group(1)) if generated else None,
        "run_phase_elapsed_s": float(cpu.group(1)) if cpu else None,
        "observation_time_s": float(observation.group(1)) if observation else None,
    }


def support_by_bin() -> dict[int, tuple[float, float]]:
    support: dict[int, tuple[float, float]] = {}
    for path in sorted(LEGACY_SPECTRUM_ROOT.glob("gamma_bin*.dat")):
        match = re.search(r"gamma_bin(\d{2})_", path.name)
        if not match:
            continue
        rows = dp_rows(path)
        support[int(match.group(1))] = (rows[0][0], rows[-1][0])
    if set(support) != set(range(20)):
        raise SystemExit("legacy gamma support does not contain bins 00..19")
    return support


def validate_results(
    plan: dict[str, Any], rows: list[dict[str, Any]], frozen_problems: list[str] | None = None
) -> dict[str, Any]:
    problems: list[str] = list(frozen_problems or [])
    validated: list[dict[str, Any]] = []
    support = support_by_bin()
    if len(rows) != 8:
        problems.append(f"job count={len(rows)}, expected 8")
    for row in sorted(rows, key=lambda item: (item["geometry"], item["part"])):
        sim = ROOT / row["sim"]
        dat = ROOT / row["isotope_dat"]
        log = ROOT / row["log"]
        if row["returncode"] != 0:
            problems.append(f"{row['geometry']}/{row['job_name']}: returncode={row['returncode']}")
        if row["generated_particles"] != EVENTS_PER_SPLIT:
            problems.append(f"{row['geometry']}/{row['job_name']}: generated={row['generated_particles']}")
        for path, label in ((sim, "SIM"), (dat, "DAT"), (log, "log")):
            if not path.is_file() or path.stat().st_size <= 0:
                problems.append(f"{row['geometry']}/{row['job_name']}: missing/empty {label}")
        if not sim.is_file() or not dat.is_file():
            continue
        expected_geometry = Path(row["geometry_setup"])
        expected_geometry = expected_geometry if expected_geometry.is_absolute() else ROOT / expected_geometry
        scan = dynamic.scan_sim(
            sim,
            "gamma",
            EVENTS_PER_SPLIT,
            int(row["seed"]),
            expected_geometry,
            support,
        )
        isotope = dynamic.parse_isotope_dat(dat)
        if scan["problems"]:
            problems.extend(f"{row['geometry']}/{row['job_name']}: {item}" for item in scan["problems"])
        if isotope["problems"] or isotope["TT_s"] is None or isotope["TT_s"] <= 0:
            problems.append(f"{row['geometry']}/{row['job_name']}: invalid isotope DAT TT")
        if row["observation_time_s"] is None or not math.isclose(
            float(row["observation_time_s"]), float(isotope["TT_s"]), rel_tol=0.0, abs_tol=5.0e-7
        ):
            problems.append(f"{row['geometry']}/{row['job_name']}: log/DAT TT mismatch")
        validated.append(
            {
                **row,
                "source_sha256": sha256(ROOT / row["source"]),
                "sim_sha256": sha256(sim),
                "sim_size_bytes": sim.stat().st_size,
                "isotope_dat_sha256": sha256(dat),
                "isotope_dat_size_bytes": dat.stat().st_size,
                "log_sha256": sha256(log),
                "log_size_bytes": log.stat().st_size,
                "sim_scan": scan,
                "isotope_store": isotope,
            }
        )
    by_geometry = {
        geometry: {
            "events_requested": sum(item["events"] for item in validated if item["geometry"] == geometry),
            "events_generated": sum(
                int(item["generated_particles"] or 0) for item in validated if item["geometry"] == geometry
            ),
            "run_phase_elapsed_s": math.fsum(
                float(item["run_phase_elapsed_s"] or 0.0) for item in validated if item["geometry"] == geometry
            ),
            "subprocess_wall_s_sum": math.fsum(
                float(item["wall_s"]) for item in validated if item["geometry"] == geometry
            ),
            "sim_size_bytes": sum(item["sim_size_bytes"] for item in validated if item["geometry"] == geometry),
        }
        for geometry in GEOMETRIES
    }
    return {
        "schema_version": 1,
        "status": "PASS__LEGACY_AXIS_DIAGNOSTIC_ONLY__NON_MERGEABLE" if not problems else "FAIL",
        "authority": AUTHORITY,
        "merge_eligible": False,
        "physics_authority": False,
        "diagnostic_id": DIAGNOSTIC_ID,
        "contract": rel(CONTRACT),
        "contract_sha256": sha256(CONTRACT),
        "errors": problems,
        "jobs": validated,
        "by_geometry": by_geometry,
        "interpretation_boundary": (
            "PASS validates an intentionally wrong historical-axis control for an A/B diagnostic only; "
            "it does not rehabilitate the legacy source or authorize event/TT/seed reuse"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--cosima", type=Path, default=COSIMA_DEFAULT)
    parser.add_argument("--print-plan", action="store_true")
    args = parser.parse_args()
    if args.workers <= 0:
        raise SystemExit("--workers must be positive")
    cosima = smoke.resolve_cosima(str(args.cosima))
    plan, environment, _transport = preflight(cosima, args.workers)
    if args.print_plan:
        print(
            json.dumps(
                {
                    "status": plan["status"],
                    "authority": plan["authority"],
                    "events_per_geometry": plan["statistics"]["events_per_geometry"],
                    "splits": plan["statistics"]["splits"],
                    "seeds": plan["statistics"]["seeds"],
                    "axis_bins": len(plan["axis_contract"]["bins"]),
                    "axis_status": plan["axis_contract"]["status"],
                    "transport_cosima_sha256": plan["transport"]["cosima_sha256"],
                    "geometry_bundle_sha256": {
                        geometry: record["bundle_sha256"]
                        for geometry, record in plan["geometry_bundles"].items()
                    },
                    "resource_gate": plan["resource_gate"],
                    "would_create": rel(RUN_ROOT),
                },
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    if RUN_ROOT.exists():
        raise SystemExit(f"write-once diagnostic output already exists: {rel(RUN_ROOT)}")
    RUN_ROOT.mkdir(parents=True, exist_ok=False)
    plan["created_utc"] = datetime.now(timezone.utc).isoformat()
    jobs = [prepare_job(plan, geometry, part) for geometry in GEOMETRIES for part in range(1, SPLITS + 1)]
    plan["status"] = "FROZEN_BEFORE_TRANSPORT__DYNAMIC_VALIDATION_REQUIRED"
    plan["legacy_jobs"] = jobs
    atomic_json(CONTRACT, plan)

    input_problems = frozen_input_problems(plan, environment, cosima)
    if input_problems:
        raise SystemExit("frozen-input gate failed before transport: " + "; ".join(input_problems[:10]))

    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_one, job, cosima, environment): job for job in jobs}
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            print(
                f"{row['geometry']}/{row['job_name']}: rc={row['returncode']} "
                f"generated={row['generated_particles']} wall={row['wall_s']:.2f}s",
                flush=True,
            )
    rows.sort(key=lambda item: (item["geometry"], item["part"]))
    atomic_json(
        SUMMARY,
        {
            "status": "TRANSPORT_COMPLETE__VALIDATION_PENDING",
            "authority": AUTHORITY,
            "merge_eligible": False,
            "contract": rel(CONTRACT),
            "contract_sha256": sha256(CONTRACT),
            "jobs": rows,
        },
    )
    postrun_frozen_problems = frozen_input_problems(plan, environment, cosima)
    validation = validate_results(plan, rows, postrun_frozen_problems)
    atomic_json(VALIDATION, validation)
    if validation["status"].startswith("PASS"):
        summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
        summary["status"] = "PASS__LEGACY_AXIS_DIAGNOSTIC_ONLY__NON_MERGEABLE"
        summary["validation"] = rel(VALIDATION)
        summary["validation_sha256"] = sha256(VALIDATION)
        summary["by_geometry"] = validation["by_geometry"]
        atomic_json(SUMMARY, summary)
        print(f"PASS validation={rel(VALIDATION)}")
        return 0
    print(json.dumps(validation["errors"][:20], indent=2, ensure_ascii=False), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
