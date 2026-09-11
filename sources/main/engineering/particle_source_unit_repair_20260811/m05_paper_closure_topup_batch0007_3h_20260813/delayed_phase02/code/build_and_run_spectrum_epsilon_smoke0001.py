#!/usr/bin/env python3
"""Fail-closed two-geometry smoke for the delayed-ion Spectrum repair.

The prepared delayed PointSource cards omitted ``<source>.Spectrum``.  In the
installed MCSource implementation an invalid spectral type falls through to a
2 MeV primary kinetic energy.  Thus the interrupted attempt01 files are
physics-rejected even if gzip/event/seed/geometry checks pass.

This tool does *not* recover or launch any formal delayed transport.  It builds
one tiny exact-position neutron source per geometry, keeps the first 32 exact
RP blocks, adds an explicit positive near-zero ``Spectrum Mono 1e-6`` keV to
every included RP, and can run a 1,000-event-per-geometry smoke behind a
separate gate.  PASS requires the SIM header to say ``SpectralType Mono 1e-6``,
every event to have IA INIT with printed kinetic energy compatible with this
epsilon (the SIM field is millikeV-rounded), radioactive DECA evidence, and no
2 MeV primary artifact.  A PASS
only validates the source-language repair; a new formal campaign still needs
separate planning and authority.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


THIS_FILE = Path(__file__).resolve()
ROOT = THIS_FILE.parents[5]
BASE_FILE = THIS_FILE.with_name("prepare_state_aware_delayed_phase02.py")
RUN_ROOT = (
    ROOT
    / "runs/particle_source_unit_repair_20260811"
    / "m05_paper_closure_topup_batch0007_3h_v1"
)
PACKAGE_ROOT = RUN_ROOT / "delayed_phase02/state_aware_exactpos_v1"
ORIGINAL_PLAN = PACKAGE_ROOT / "transport_jobs.json"
SMOKE_ROOT = PACKAGE_ROOT / "spectrum_epsilon_repair_smoke0001"
SMOKE_PLAN = SMOKE_ROOT / "smoke_plan.json"
SMOKE_SUMMARY = SMOKE_ROOT / "smoke_validation.json"
COSIMA = Path("/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima")
MC_SOURCE_CC = Path("/home/ubuntu/MEGAlib_Install/megalib-main/src/cosima/src/MCSource.cc")
MC_PARAMETER_CC = Path("/home/ubuntu/MEGAlib_Install/megalib-main/src/cosima/src/MCParameterFile.cc")

GEOMETRIES = ("Mass_model_511", "S3d_O8")
FAMILY = "n"
SMOKE_RP_BLOCKS = 32
EPSILON_KEV = 1.0e-6
SMOKE_TRIGGERS = 1_000
MATCHED_SMOKE_SEED = 2_068_410_001
WORKERS = 2
RESERVE_BYTES = 20 * 1024**3
JOB_CAP_BYTES = 100_000_000
REJECTED_COMPLETE_JOB_ID = "delayed02_n_Mass_model_511"


def _load_base() -> Any:
    spec = importlib.util.spec_from_file_location("delayed_phase02_retained", BASE_FILE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load retained controller: {BASE_FILE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = _load_base()


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_text_once(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"write-once target exists: {path}")
    partial = path.with_name(f".{path.name}.partial.{os.getpid()}")
    with partial.open("x", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(partial, path)


def atomic_json_once(path: Path, payload: Any) -> None:
    atomic_text_once(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def original_neutron_jobs() -> list[dict[str, Any]]:
    jobs = [
        dict(row) for row in load_json(ORIGINAL_PLAN)["jobs"]
        if row["family"] == FAMILY and row["geometry"] in GEOMETRIES
    ]
    by_geometry = {row["geometry"]: row for row in jobs}
    if set(by_geometry) != set(GEOMETRIES) or len(jobs) != 2:
        raise RuntimeError("prepared plan lacks the exact two-geometry neutron pair")
    return [by_geometry[geometry] for geometry in GEOMETRIES]


def parse_prepared_source(path: Path) -> dict[str, Any]:
    geometry = None
    triggers = None
    definitions: dict[str, dict[str, str]] = {}
    source_registrations = 0
    spectrum_lines = 0
    text = path.read_text(encoding="utf-8", errors="strict")
    for raw in text.splitlines():
        fields = raw.split(maxsplit=1)
        if not fields:
            continue
        if fields[0] == "Geometry" and len(fields) == 2:
            geometry = fields[1].strip()
        elif fields[0] == "DecayRun.Triggers" and len(fields) == 2:
            triggers = int(fields[1])
        elif fields[0] == "DecayRun.Source" and len(fields) == 2:
            source_registrations += 1
        elif fields[0].endswith(".Spectrum"):
            spectrum_lines += 1
        if fields[0].startswith("RP_") and "." in fields[0]:
            name, key = fields[0].split(".", 1)
            try:
                index = int(name.split("_", 1)[1])
            except ValueError:
                continue
            if index < SMOKE_RP_BLOCKS:
                definitions.setdefault(name, {})[key] = raw
    required = {"ParticleType", "Beam", "Flux"}
    incomplete = {name: sorted(set(values) ^ required) for name, values in definitions.items() if set(values) != required}
    if not geometry or triggers != 1_000_000 or len(definitions) != SMOKE_RP_BLOCKS or incomplete:
        raise RuntimeError(
            f"unexpected prepared source structure {path}: geometry={geometry}, "
            f"triggers={triggers}, blocks={len(definitions)}, incomplete={incomplete}"
        )
    if spectrum_lines != 0 or source_registrations != 50_000:
        raise RuntimeError(
            f"expected 50,000 RP registrations and zero Spectrum lines in {path}; "
            f"observed {source_registrations}, {spectrum_lines}"
        )
    return {
        "path": path,
        "sha256": hashlib.sha256(text.encode()).hexdigest(),
        "geometry": str(Path(geometry).resolve()),
        "definitions": definitions,
        "source_registrations": source_registrations,
        "spectrum_lines": spectrum_lines,
    }


def first_invalid_primary_evidence(path: Path) -> dict[str, Any]:
    spectral_header = None
    init_energy = None
    init_line = None
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            stripped = raw.strip()
            if stripped.startswith("SpectralType") and spectral_header is None:
                spectral_header = stripped
            elif stripped.startswith("IA INIT"):
                init_line = stripped
                init_energy = float(stripped.rsplit(";", 1)[1].strip())
                break
    if spectral_header != "SpectralType" or init_energy is None or abs(init_energy - 2000.0) > 0.0005:
        raise RuntimeError(
            f"old 2-MeV failure signature was not reproduced: "
            f"SpectralType={spectral_header!r}, IA_INIT={init_energy}"
        )
    return {
        "sim": rel(path),
        "sim_size_bytes": path.stat().st_size,
        "spectral_header": spectral_header,
        "first_IA_INIT_kinetic_energy_keV": init_energy,
        "first_IA_INIT_line": init_line,
        "read_scope": "header_through_first_IA_INIT_only",
    }


def old_attempt_snapshots() -> list[dict[str, Any]]:
    snapshots = []
    transport = PACKAGE_ROOT / "transport"
    for geometry in GEOMETRIES:
        for family in ("p", "n", "alpha"):
            path = transport / geometry / family / ".attempt01.partial"
            files = []
            if path.is_dir():
                for item in sorted(path.iterdir()):
                    if item.is_file():
                        stat = item.stat()
                        files.append({"name": item.name, "size_bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns})
            snapshots.append({"geometry": geometry, "family": family, "path": rel(path), "exists": path.exists(), "files": files})
    return snapshots


def source_code_contract() -> dict[str, Any]:
    source_text = MC_SOURCE_CC.read_text(encoding="utf-8", errors="replace")
    parameter_text = MC_PARAMETER_CC.read_text(encoding="utf-8", errors="replace")
    required_source = [
        "if (m_EnergyParam1 <= 0)",
        "m_Energy = 2.0*MeV;",
        'SetEnergyDisType("Mono")',
    ]
    required_parser = [
        'Type == "mono"',
        "T->GetTokenAtAsDouble(3)*keV",
    ]
    if not all(token in source_text for token in required_source):
        raise RuntimeError("installed MCSource no longer matches the audited energy contract")
    if not all(token in parameter_text for token in required_parser):
        raise RuntimeError("installed MCParameterFile no longer matches the audited Mono-keV parser")
    return {
        "MCSource_cc": str(MC_SOURCE_CC),
        "MCSource_cc_sha256": sha256(MC_SOURCE_CC),
        "MCParameterFile_cc": str(MC_PARAMETER_CC),
        "MCParameterFile_cc_sha256": sha256(MC_PARAMETER_CC),
        "findings": [
            "Spectrum Mono argument is parsed as keV.",
            "Mono energy must be strictly positive.",
            "Invalid/unimplemented spectral type falls through to a 2.0 MeV primary.",
        ],
        "epsilon_keV": EPSILON_KEV,
        "epsilon_reason": (
            "strictly_positive_for_MCSource; IA_INIT prints 0.000 keV at millikeV "
            "precision, so the gate accepts that rounded value while rejecting 2 MeV"
        ),
    }


def make_smoke_source(parsed: dict[str, Any], output_prefix: Path) -> str:
    lines = [
        "Version 1",
        f"Geometry {parsed['geometry']}",
        "",
        "PhysicsListHD qgsp-bic-hp",
        "PhysicsListEM LivermorePol",
        "PhysicsListRadioactiveDecay true",
        "DecayMode ActivationDelayedDecay",
        "StoreSimulationInfo all",
        "StoreIsotopes true",
        "DetectorTimeConstant 1e-9",
        "",
        "Run DecayRun",
        f"DecayRun.FileName {output_prefix.resolve()}",
        f"DecayRun.Triggers {SMOKE_TRIGGERS}",
    ]
    names = [f"RP_{index:07d}" for index in range(SMOKE_RP_BLOCKS)]
    lines.extend(f"DecayRun.Source {name}" for name in names)
    lines.extend(("", "# 32 exact prepared RPs; explicit positive near-zero kinetic spectrum."))
    for name in names:
        values = parsed["definitions"][name]
        particle = values["ParticleType"].split(maxsplit=1)[1]
        beam = values["Beam"].split(maxsplit=1)[1]
        flux = values["Flux"].split(maxsplit=1)[1]
        lines.extend((
            f"{name}.ParticleType {particle}",
            f"{name}.Beam {beam}",
            f"{name}.Spectrum Mono {EPSILON_KEV:.9g}",
            f"{name}.Flux {flux}",
            "",
        ))
    return "\n".join(lines)


def build_job(staging: Path, original: dict[str, Any]) -> dict[str, Any]:
    geometry = original["geometry"]
    parsed = parse_prepared_source(ROOT / original["source"])
    partial = SMOKE_ROOT / "transport" / geometry / ".attempt01.partial"
    final = partial.parent / "attempt01"
    prefix_name = f"EpsilonMonoSmoke_{geometry}_n"
    prefix = partial / prefix_name
    source_name = f"epsilon_mono_smoke_{geometry}_n.source"
    staged_source = staging / "source_cards" / geometry / source_name
    staged_source.parent.mkdir(parents=True, exist_ok=False)
    text = make_smoke_source(parsed, prefix)
    with staged_source.open("x", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    if text.count(f".Spectrum Mono {EPSILON_KEV:.9g}") != SMOKE_RP_BLOCKS:
        raise RuntimeError("smoke source lacks 32 explicit epsilon Spectra")
    if text.count(".ParticleType ") != text.count(".Spectrum Mono "):
        raise RuntimeError("not every smoke RP has an explicit Spectrum")
    return {
        "job_id": f"epsilon_smoke_n_{geometry}",
        "geometry": geometry,
        "family": FAMILY,
        "seed": MATCHED_SMOKE_SEED,
        "matched_geometry_seed_key": "spectrum_epsilon_smoke0001|n",
        "triggers": SMOKE_TRIGGERS,
        "epsilon_keV": EPSILON_KEV,
        "source": rel(SMOKE_ROOT / "source_cards" / geometry / source_name),
        "source_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "prepared_source": str(original["source"]),
        "prepared_source_sha256": parsed["sha256"],
        "prepared_RP_names": [f"RP_{index:07d}" for index in range(SMOKE_RP_BLOCKS)],
        "prepared_RP_blocks": SMOKE_RP_BLOCKS,
        "expected_geometry": parsed["geometry"],
        "attempt_partial_dir": rel(partial),
        "attempt_final_dir": rel(final),
        "expected_sim": rel(prefix.with_suffix(".inc1.id1.sim.gz")),
        "published_sim": rel((final / prefix_name).with_suffix(".inc1.id1.sim.gz")),
        "declared_cap_bytes": JOB_CAP_BYTES,
    }


def prepare() -> dict[str, Any]:
    if SMOKE_ROOT.exists():
        manifest = SMOKE_ROOT / "manifest.json"
        if not manifest.is_file():
            raise RuntimeError(f"smoke namespace exists without manifest: {SMOKE_ROOT}")
        return load_json(manifest)
    jobs = original_neutron_jobs()
    snapshots_before = old_attempt_snapshots()
    complete = next(row for row in jobs if row["job_id"] == REJECTED_COMPLETE_JOB_ID)
    complete_sim = ROOT / complete["expected_sim"]
    rejection_signature = first_invalid_primary_evidence(complete_sim)
    installed_contract = source_code_contract()
    staging = SMOKE_ROOT.with_name(f".{SMOKE_ROOT.name}.partial.{os.getpid()}")
    if staging.exists():
        raise FileExistsError(f"staging exists: {staging}")
    staging.mkdir(parents=True)
    smoke_jobs = [build_job(staging, row) for row in jobs]
    if len({row["seed"] for row in smoke_jobs}) != 1:
        raise RuntimeError("smoke geometry pair does not share one fresh seed")
    snapshots_after = old_attempt_snapshots()
    if snapshots_before != snapshots_after:
        raise RuntimeError("old attempt01 evidence changed during smoke preparation")
    rejection = {
        "schema_version": 1,
        "status": "REJECTED__MISSING_SPECTRUM_DEFAULT_2MEV_PRIMARY_KINETIC_ENERGY",
        "created_utc": now_utc(),
        "rejected_scope": "ALL_STATE_AWARE_EXACTPOS_V1_ATTEMPT01_TRANSPORTS_USING_SPECTRUMLESS_RP_SOURCES",
        "complete_example": rejection_signature,
        "prepared_source_findings": [
            {
                "geometry": row["geometry"],
                "source": row["source"],
                "source_sha256": parse_prepared_source(ROOT / row["source"])["sha256"],
                "RP_registrations": 50_000,
                "Spectrum_lines": 0,
            }
            for row in jobs
        ],
        "installed_code_contract": installed_contract,
        "attempt01_snapshots_before": snapshots_before,
        "attempt01_snapshots_after": snapshots_after,
        "attempt01_mutated": False,
        "salvage_allowed": False,
        "physics_reason": (
            "The radioactive ion was injected with 2000 keV kinetic energy before decay; "
            "event-count, gzip, geometry, and seed validity cannot repair this primary-energy contamination."
        ),
    }
    atomic_json_once(staging / "rejected_attempt01_evidence.json", rejection)
    plan = {
        "schema_version": 1,
        "status": "READY__TWO_GEOMETRY_EPSILON_MONO_SMOKE_NOT_LAUNCHED",
        "created_utc": now_utc(),
        "workers": WORKERS,
        "jobs": smoke_jobs,
        "matched_seed": MATCHED_SMOKE_SEED,
        "epsilon_keV": EPSILON_KEV,
        "triggers_per_geometry": SMOKE_TRIGGERS,
        "filesystem_reserve_bytes": RESERVE_BYTES,
        "declared_job_cap_bytes": JOB_CAP_BYTES,
        "formal_transport_authorized": False,
    }
    atomic_json_once(staging / "smoke_plan.json", plan)
    manifest = {
        "schema_version": 1,
        "status": "PASS__SPECTRUM_EPSILON_SMOKE_PREPARED__NOT_LAUNCHED",
        "created_utc": now_utc(),
        "controller": rel(THIS_FILE),
        "controller_sha256": sha256(THIS_FILE),
        "retained_source_builder": rel(BASE_FILE),
        "retained_source_builder_sha256": sha256(BASE_FILE),
        "original_transport_plan": rel(ORIGINAL_PLAN),
        "original_transport_plan_sha256": sha256(ORIGINAL_PLAN),
        "rejected_attempt01_evidence": rel(SMOKE_ROOT / "rejected_attempt01_evidence.json"),
        "smoke_plan": rel(SMOKE_PLAN),
        "old_attempt01_policy": "REJECTED_READ_ONLY_PRESERVE_NO_MOVE_NO_DELETE_NO_SALVAGE",
        "smoke_pass_gate": [
            "two geometry jobs return zero",
            f"all {SMOKE_RP_BLOCKS} RP blocks have Spectrum Mono {EPSILON_KEV:.9g} keV",
            f"SIM SpectralType lines are Mono {EPSILON_KEV:.9g}",
            f"all {SMOKE_TRIGGERS} events have IA INIT compatible with millikeV-rounded epsilon and radioactive DECA evidence",
            "zero IA INIT primaries near 2000 keV",
            "gzip EOF, SE/ID/EN, geometry, and matched seed pass",
        ],
        "transport_launched": False,
        "formal_transport_authorized": False,
        "authority_boundary": (
            "SOURCE_LANGUAGE_AND_PRIMARY_KINETIC_ENERGY_TINY_SMOKE_ONLY__"
            "NO_DELAYED_RATE_RESPONSE_MISSION_SENSITIVITY_OR_PAPER_CLOSURE"
        ),
    }
    atomic_json_once(staging / "manifest.json", manifest)
    SMOKE_ROOT.parent.mkdir(parents=True, exist_ok=True)
    os.replace(staging, SMOKE_ROOT)
    return manifest


def tree_bytes(path: Path) -> int:
    return int(BASE.tree_bytes(path))


def validate_smoke_sim(path: Path, job: dict[str, Any]) -> dict[str, Any]:
    if not path.is_file():
        return {"status": "FAIL", "problem": "missing_sim", "path": rel(path)}
    geometry = ""
    seed = None
    spectral_lines: list[str] = []
    se = ids = en = 0
    init_energies: list[float] = []
    deca_events: set[int] = set()
    current_event = 0
    id_sequence = True
    try:
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                stripped = raw.strip()
                fields = stripped.split()
                if not fields:
                    continue
                if fields[0] == "Geometry" and not geometry:
                    geometry = " ".join(fields[1:])
                elif fields[0] == "Seed" and seed is None:
                    seed = int(fields[1])
                elif fields[0] == "SpectralType":
                    spectral_lines.append(stripped)
                elif stripped == "SE":
                    se += 1
                    current_event = se
                elif fields[0] == "ID":
                    ids += 1
                    if len(fields) != 3 or int(fields[1]) != ids or int(fields[2]) != ids:
                        id_sequence = False
                elif stripped == "EN":
                    en += 1
                elif stripped.startswith("IA INIT"):
                    init_energies.append(float(stripped.rsplit(";", 1)[1].strip()))
                elif stripped.startswith("IA DECA"):
                    deca_events.add(current_event)
    except (OSError, EOFError, ValueError) as exc:
        return {"status": "FAIL", "problem": f"gzip_or_parse:{exc}", "path": rel(path), "gzip_eof": False}
    expected_spectral = f"SpectralType Mono {EPSILON_KEV:g}"
    epsilon_ok = (
        len(init_energies) == SMOKE_TRIGGERS
        and all(abs(value - EPSILON_KEV) <= 0.0005001 for value in init_energies)
    )
    two_mev = sum(abs(value - 2000.0) <= 0.0005 for value in init_energies)
    problems = []
    if se != SMOKE_TRIGGERS or ids != SMOKE_TRIGGERS or en != 1 or not id_sequence:
        problems.append("event_or_ID_contract_failed")
    if Path(geometry).resolve() != Path(job["expected_geometry"]).resolve():
        problems.append("geometry_mismatch")
    if seed != int(job["seed"]):
        problems.append("seed_mismatch")
    if not spectral_lines or any(line != expected_spectral for line in spectral_lines):
        problems.append("SpectralType_not_explicit_expected_Mono_epsilon")
    if not epsilon_ok:
        problems.append("IA_INIT_not_epsilon")
    if two_mev:
        problems.append("2MeV_primary_artifact_present")
    if not deca_events:
        problems.append("no_radioactive_DECA_evidence")
    return {
        "status": "PASS" if not problems else "FAIL",
        "problem": None if not problems else ";".join(problems),
        "path": rel(path),
        "gzip_eof": True,
        "SE": se, "ID": ids, "EN": en, "ID_sequence_1_to_N": id_sequence,
        "geometry": str(Path(geometry).resolve()), "seed": seed,
        "spectral_lines": spectral_lines,
        "expected_spectral_line": expected_spectral,
        "IA_INIT_count": len(init_energies),
        "IA_INIT_energy_min_keV": min(init_energies) if init_energies else None,
        "IA_INIT_energy_max_keV": max(init_energies) if init_energies else None,
        "IA_INIT_all_epsilon_within_0.0005_keV": epsilon_ok,
        "IA_INIT_2MeV_artifact_count": two_mev,
        "events_with_IA_DECA": len(deca_events),
    }


def validate_log(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"status": "FAIL", "problem": "missing_log", "path": rel(path)}
    forbidden = (
        "Energy type not yet implemented",
        "Cannot parse token Spectrum",
        "Cannot parse token",
        "The energy must be larger than 0",
        "***  ERROR  ***",
    )
    matches = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for lineno, raw in enumerate(handle, 1):
            if any(token in raw for token in forbidden):
                matches.append({"line": lineno, "text": raw.strip()[:240]})
                if len(matches) >= 20:
                    break
    return {
        "status": "PASS" if not matches else "FAIL",
        "path": rel(path),
        "invalid_or_spectrum_error_matches": matches,
        "forbidden_signatures": list(forbidden),
    }


def run_smoke() -> dict[str, Any]:
    if not SMOKE_PLAN.is_file():
        raise RuntimeError("run --prepare before --run-smoke")
    if SMOKE_SUMMARY.exists():
        raise FileExistsError(f"write-once smoke summary exists: {SMOKE_SUMMARY}")
    plan = load_json(SMOKE_PLAN)
    jobs = list(plan["jobs"])
    if len(jobs) != 2 or len({row["seed"] for row in jobs}) != 1:
        raise RuntimeError("smoke plan lost two-geometry matched-seed contract")
    required_free = RESERVE_BYTES + len(jobs) * JOB_CAP_BYTES
    if shutil.disk_usage(ROOT).free < required_free:
        raise RuntimeError(f"smoke cannot preserve 20-GiB reserve: required_free={required_free}")
    for job in jobs:
        partial = ROOT / job["attempt_partial_dir"]
        final = ROOT / job["attempt_final_dir"]
        if partial.exists() or final.exists():
            raise RuntimeError(f"write-once smoke attempt exists: {partial} or {final}")
    environment, environment_provenance = BASE.clean_cosima_env()
    active = []
    for job in jobs:
        partial = ROOT / job["attempt_partial_dir"]
        partial.mkdir(parents=True, exist_ok=False)
        log_handle = (partial / "cosima.log").open("x", encoding="utf-8")
        process = subprocess.Popen(
            [str(COSIMA), "-s", str(job["seed"]), str(ROOT / job["source"])],
            cwd=ROOT, stdout=log_handle, stderr=subprocess.STDOUT,
            start_new_session=True, env=environment,
        )
        active.append({"job": job, "process": process, "log": log_handle, "started": time.monotonic()})
    receipts = []
    for item in active:
        code = item["process"].wait()
        item["log"].close()
        job = item["job"]
        partial = ROOT / job["attempt_partial_dir"]
        final = ROOT / job["attempt_final_dir"]
        check = validate_smoke_sim(ROOT / job["expected_sim"], job)
        log_check = validate_log(partial / "cosima.log")
        observed = tree_bytes(partial)
        status = (
            "PASS" if code == 0 and check["status"] == "PASS"
            and log_check["status"] == "PASS" and observed <= JOB_CAP_BYTES else "FAIL"
        )
        receipt = {
            "schema_version": 1, "status": status, "job": job,
            "returncode": code, "wall_s": time.monotonic() - item["started"],
            "observed_output_bytes": observed, "declared_cap_bytes": JOB_CAP_BYTES,
            "sim_validation": check, "log_validation": log_check,
            "runtime_environment": environment_provenance,
        }
        atomic_json_once(partial / "receipt.json", receipt)
        if status == "PASS":
            os.replace(partial, final)
        receipts.append(receipt)
    passed = len(receipts) == 2 and all(row["status"] == "PASS" for row in receipts)
    summary = {
        "schema_version": 1,
        "status": "PASS__EPSILON_MONO_TWO_GEOMETRY_SMOKE" if passed else "FAIL__EPSILON_MONO_SMOKE",
        "created_utc": now_utc(),
        "jobs": receipts,
        "passed_jobs": sum(row["status"] == "PASS" for row in receipts),
        "expected_jobs": 2,
        "epsilon_keV": EPSILON_KEV,
        "matched_seed": MATCHED_SMOKE_SEED,
        "old_attempt01_rejected": True,
        "formal_transport_authorized": False,
        "next_gate": (
            "Smoke PASS permits separate review/design of corrected formal sources; "
            "it does not automatically authorize or claim formal transport."
        ),
        "authority_boundary": "SOURCE_LANGUAGE_AND_PRIMARY_KINETIC_ENERGY_TINY_SMOKE_ONLY",
    }
    atomic_json_once(SMOKE_SUMMARY, summary)
    if not passed:
        raise RuntimeError(f"epsilon Mono smoke failed: {summary}")
    return summary


def print_plan() -> dict[str, Any]:
    return {
        "status": "READY_TO_PREPARE" if not SMOKE_ROOT.exists() else "SMOKE_NAMESPACE_EXISTS",
        "controller": rel(THIS_FILE),
        "output": rel(SMOKE_ROOT),
        "geometries": list(GEOMETRIES),
        "family": FAMILY,
        "exact_RP_per_geometry": SMOKE_RP_BLOCKS,
        "explicit_Spectrum_per_RP": True,
        "spectrum": f"Mono {EPSILON_KEV:.9g} keV",
        "triggers_per_geometry": SMOKE_TRIGGERS,
        "matched_seed": MATCHED_SMOKE_SEED,
        "old_attempt01_action": "REJECT_READ_ONLY_PRESERVE",
        "formal_transport_launched": False,
    }


def self_test() -> dict[str, Any]:
    jobs = original_neutron_jobs()
    assert len(jobs) == 2
    parsed = [parse_prepared_source(ROOT / row["source"]) for row in jobs]
    assert all(row["spectrum_lines"] == 0 and row["source_registrations"] == 50_000 for row in parsed)
    contract = source_code_contract()
    with tempfile.TemporaryDirectory(prefix="epsilon_mono_smoke_selftest_") as value:
        temp = Path(value)
        text = make_smoke_source(parsed[0], temp / "output")
        assert text.count(".ParticleType ") == SMOKE_RP_BLOCKS
        assert text.count(f".Spectrum Mono {EPSILON_KEV:.9g}") == SMOKE_RP_BLOCKS
        assert f"DecayRun.Triggers {SMOKE_TRIGGERS}" in text
        sim = temp / "synthetic.sim.gz"
        geometry = parsed[0]["geometry"]
        with gzip.open(sim, "wt", encoding="utf-8") as handle:
            handle.write(f"Geometry   {geometry}\nSeed       {MATCHED_SMOKE_SEED}\n")
            handle.write(f"SpectralType Mono {EPSILON_KEV:g}\n")
            for index in range(1, SMOKE_TRIGGERS + 1):
                handle.write(f"SE\nID {index} {index}\nIA INIT 1;0;0;{EPSILON_KEV:.3f}\nIA DECA 2;1;4;0.0\n")
            handle.write("EN\n")
        job = {"expected_geometry": geometry, "seed": MATCHED_SMOKE_SEED}
        check = validate_smoke_sim(sim, job)
        assert check["status"] == "PASS" and check["IA_INIT_2MeV_artifact_count"] == 0
    return {
        "status": "PASS__EPSILON_MONO_SMOKE_STATIC_SELF_TEST",
        "tests": 15,
        "prepared_sources_checked": 2,
        "prepared_RP_registrations_checked": 100_000,
        "prepared_Spectrum_lines": 0,
        "installed_code_contract": contract,
        "epsilon_keV": EPSILON_KEV,
        "synthetic_SIM_gate_passed": True,
        "campaign_files_written": False,
        "transport_launched": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--print-plan", action="store_true")
    actions.add_argument("--self-test", action="store_true")
    actions.add_argument("--prepare", action="store_true")
    actions.add_argument("--run-smoke", action="store_true")
    parser.add_argument("--execute-smoke", action="store_true", help="second gate for --run-smoke")
    args = parser.parse_args()
    if args.execute_smoke and not args.run_smoke:
        parser.error("--execute-smoke is only valid with --run-smoke")
    if args.print_plan:
        payload = print_plan()
    elif args.self_test:
        payload = self_test()
    elif args.prepare:
        payload = prepare()
    else:
        if not args.execute_smoke:
            raise SystemExit("--run-smoke requires --execute-smoke")
        payload = run_smoke()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
