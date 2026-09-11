#!/usr/bin/env python3
"""Read-only revalidation of epsilon formal partial recovery0002.

The original controller required every event to contain ``IA DECA``.  That is
too strict for a delayed radioactive-ion transport: a small number of valid
epsilon-initialized triggers can have no recorded decay interaction.  This
append-only review retains every old PASS/FAIL receipt and attempt directory,
then independently streams all six SIM files to gzip EOF.

Scientific gate used here:

* exactly 250,000 sequential SE/ID events and one EN;
* every event has exactly one IA INIT, with epsilon-compatible printed kinetic
  energy and zero 2-MeV default-spectrum artifacts;
* geometry, fresh matched seed, and explicit ``SpectralType Mono 1e-06`` pass;
* Cosima return code was zero and the retained log has no parser/energy error;
* IA DECA coverage is positive, reported as a coverage statistic, and is not
  required to be 100 percent.

Passing this gate establishes corrected delayed partial-screening transport
compatibility for p/n/alpha in two geometries only.  It does not establish a
full delayed response, mission sensitivity, paper closure, or geometry rank.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


THIS_FILE = Path(__file__).resolve()
ROOT = THIS_FILE.parents[5]
RECOVERY_ENTRY = THIS_FILE.with_name("run_epsilon_formal_partial_recovery0002.py")
PACKAGE_ROOT = (
    ROOT
    / "runs/particle_source_unit_repair_20260811"
    / "m05_paper_closure_topup_batch0007_3h_v1"
    / "delayed_phase02/state_aware_exactpos_v1"
)
RECOVERY_ROOT = PACKAGE_ROOT / "spectrum_epsilon_formal_partial_recovery0002"
PLAN = RECOVERY_ROOT / "formal_partial_jobs.json"
ORIGINAL_SUMMARY = RECOVERY_ROOT / "formal_partial_validation.json"
OUTPUT_ROOT = RECOVERY_ROOT / "revalidation0001"
OUTPUT = OUTPUT_ROOT / "formal_partial_revalidation.json"

EXPECTED_EVENTS = 250_000
EPSILON_KEV = 1.0e-6
EPSILON_PRINT_TOLERANCE_KEV = 0.0005001
GEOMETRIES = ("Mass_model_511", "S3d_O8")
FAMILIES = ("p", "n", "alpha")


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R2 = load_module(RECOVERY_ENTRY, "epsilon_formal_partial_recovery0002_for_revalidation")
IMPL = R2.IMPL
SMOKE = IMPL.SMOKE


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json_once(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"write-once target exists: {path}")
    partial = path.with_name(f".{path.name}.partial.{os.getpid()}")
    with partial.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(partial, path)


def terminal_authority() -> dict[str, Any]:
    if not ORIGINAL_SUMMARY.is_file():
        raise RuntimeError(
            "original controller has not published its terminal summary; wait for it to terminate"
        )
    payload = load_json(ORIGINAL_SUMMARY)
    if payload.get("status") != "FAIL__EPSILON_FORMAL_PARTIAL_SCREENING":
        raise RuntimeError(f"unexpected original terminal status: {payload.get('status')}")
    if int(payload.get("expected_jobs", -1)) != 6 or len(payload.get("jobs", [])) != 6:
        raise RuntimeError("original terminal summary does not cover six jobs")
    return {
        "path": rel(ORIGINAL_SUMMARY),
        "sha256": sha256(ORIGINAL_SUMMARY),
        "status": payload["status"],
        "old_gate": "events_with_IA_DECA_must_equal_250000",
        "old_gate_disposition": "SUPERSEDED_FOR_READ_ONLY_PARTIAL_SCREENING_REVALIDATION_ONLY",
    }


def path_snapshot(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": rel(path),
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "inode": stat.st_ino,
    }


def directory_snapshot(path: Path) -> dict[str, Any]:
    rows = []
    if path.is_dir():
        for item in sorted(path.iterdir()):
            if item.is_file():
                stat = item.stat()
                rows.append({
                    "name": item.name,
                    "size_bytes": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                    "inode": stat.st_ino,
                })
    return {"path": rel(path), "exists": path.is_dir(), "files": rows}


def locate_artifact(job: dict[str, Any]) -> dict[str, Any]:
    final_sim = ROOT / job["published_sim"]
    partial_sim = ROOT / job["expected_sim"]
    candidates = [
        ("PUBLISHED_ATTEMPT01", final_sim),
        ("RETAINED_FAIL_PARTIAL_ATTEMPT01", partial_sim),
    ]
    existing = [(state, path) for state, path in candidates if path.is_file()]
    if len(existing) != 1:
        raise RuntimeError(
            f"expected exactly one final-or-partial SIM for {job['job_id']}: "
            f"{[(state, str(path), path.exists()) for state, path in candidates]}"
        )
    state, sim = existing[0]
    attempt_dir = sim.parent
    receipt = attempt_dir / "receipt.json"
    log = attempt_dir / "cosima.log"
    if not receipt.is_file() or not log.is_file():
        raise RuntimeError(f"artifact lacks retained receipt/log: {attempt_dir}")
    receipt_payload = load_json(receipt)
    if int(receipt_payload.get("returncode", -1)) != 0:
        raise RuntimeError(f"nonzero retained returncode: {job['job_id']}")
    return {
        "artifact_state": state,
        "sim": sim,
        "attempt_dir": attempt_dir,
        "receipt": receipt,
        "receipt_payload": receipt_payload,
        "log": log,
    }


def validate_sim(
    path: Path,
    *,
    expected_geometry: Path,
    expected_seed: int,
    expected_events: int = EXPECTED_EVENTS,
) -> dict[str, Any]:
    before = path_snapshot(path)
    geometry = ""
    seed: int | None = None
    spectral_lines: list[str] = []
    se = ids = en = 0
    id_sequence = True
    id_column_count = True
    init_lines = 0
    init_events = 0
    init_duplicate_events = 0
    init_missing_events = 0
    init_energy_min: float | None = None
    init_energy_max: float | None = None
    init_energy_outside_epsilon_tolerance = 0
    init_2mev_artifacts = 0
    deca_lines = 0
    deca_events = 0
    current_event = 0
    current_init_count = 0
    current_has_deca = False

    def finish_event() -> None:
        nonlocal init_events, init_duplicate_events, init_missing_events, deca_events
        if current_event <= 0:
            return
        if current_init_count == 0:
            init_missing_events += 1
        else:
            init_events += 1
            if current_init_count != 1:
                init_duplicate_events += 1
        if current_has_deca:
            deca_events += 1

    try:
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                stripped = raw.strip()
                if not stripped:
                    continue
                fields = stripped.split()
                tag = fields[0]
                if tag == "Geometry" and not geometry:
                    geometry = " ".join(fields[1:])
                elif tag == "Seed" and seed is None:
                    seed = int(fields[1])
                elif tag == "SpectralType":
                    spectral_lines.append(stripped)
                elif stripped == "SE":
                    finish_event()
                    se += 1
                    current_event = se
                    current_init_count = 0
                    current_has_deca = False
                elif tag == "ID":
                    ids += 1
                    if len(fields) != 3:
                        id_column_count = False
                        id_sequence = False
                    else:
                        try:
                            if int(fields[1]) != ids or int(fields[2]) != ids:
                                id_sequence = False
                        except ValueError:
                            id_sequence = False
                elif stripped == "EN":
                    finish_event()
                    current_event = 0
                    current_init_count = 0
                    current_has_deca = False
                    en += 1
                elif stripped.startswith("IA INIT"):
                    init_lines += 1
                    current_init_count += 1
                    value = float(stripped.rsplit(";", 1)[1].strip())
                    init_energy_min = value if init_energy_min is None else min(init_energy_min, value)
                    init_energy_max = value if init_energy_max is None else max(init_energy_max, value)
                    if abs(value) > EPSILON_PRINT_TOLERANCE_KEV:
                        init_energy_outside_epsilon_tolerance += 1
                    if abs(value - 2000.0) <= 0.0005:
                        init_2mev_artifacts += 1
                elif stripped.startswith("IA DECA"):
                    deca_lines += 1
                    current_has_deca = True
        finish_event()
    except (OSError, EOFError, ValueError) as exc:
        return {
            "status": "FAIL",
            "problem": f"gzip_or_parse_error:{exc}",
            "path": rel(path),
            "gzip_eof_reached": False,
        }

    after = path_snapshot(path)
    stable = before == after
    expected_spectral = f"SpectralType Mono {EPSILON_KEV:g}"
    problems = []
    if se != expected_events or ids != expected_events or en != 1:
        problems.append("SE_ID_EN_count")
    if not id_column_count or not id_sequence:
        problems.append("ID_two_columns_or_sequence")
    if Path(geometry).resolve() != expected_geometry.resolve():
        problems.append("geometry")
    if seed != int(expected_seed):
        problems.append("seed")
    if not spectral_lines or any(row != expected_spectral for row in spectral_lines):
        problems.append("SpectralType")
    if init_lines != expected_events or init_events != expected_events:
        problems.append("IA_INIT_event_coverage")
    if init_missing_events or init_duplicate_events:
        problems.append("IA_INIT_missing_or_duplicate")
    if init_energy_outside_epsilon_tolerance or init_2mev_artifacts:
        problems.append("IA_INIT_energy_or_2MeV_artifact")
    if deca_events <= 0 or deca_lines <= 0:
        problems.append("no_IA_DECA_evidence")
    if not stable:
        problems.append("artifact_changed_during_scan")
    no_deca_events = expected_events - deca_events
    return {
        "status": "PASS" if not problems else "FAIL",
        "problem": None if not problems else ";".join(problems),
        "path": rel(path),
        "path_binding_before": before,
        "path_binding_after": after,
        "stable_during_full_stream_scan": stable,
        "gzip_eof_reached": True,
        "SE": se,
        "ID": ids,
        "EN": en,
        "ID_exactly_two_integer_columns": id_column_count,
        "ID_both_columns_sequential_1_to_N": id_sequence,
        "geometry": str(Path(geometry).resolve()),
        "expected_geometry": str(expected_geometry.resolve()),
        "seed": seed,
        "expected_seed": int(expected_seed),
        "spectral_lines": spectral_lines,
        "expected_spectral_line": expected_spectral,
        "IA_INIT_lines": init_lines,
        "events_with_exactly_one_IA_INIT": init_events - init_duplicate_events,
        "events_missing_IA_INIT": init_missing_events,
        "events_with_duplicate_IA_INIT": init_duplicate_events,
        "IA_INIT_energy_min_keV": init_energy_min,
        "IA_INIT_energy_max_keV": init_energy_max,
        "IA_INIT_energy_outside_epsilon_print_tolerance": init_energy_outside_epsilon_tolerance,
        "IA_INIT_2MeV_artifact_count": init_2mev_artifacts,
        "IA_DECA_lines": deca_lines,
        "events_with_IA_DECA": deca_events,
        "events_without_IA_DECA": no_deca_events,
        "IA_DECA_event_coverage_fraction": deca_events / expected_events,
        "no_IA_DECA_event_fraction": no_deca_events / expected_events,
        "DECA_gate": "overall_positive_and_report_coverage__not_100_percent_required",
    }


def validate_job(job: dict[str, Any]) -> dict[str, Any]:
    located = locate_artifact(job)
    before_dir = directory_snapshot(located["attempt_dir"])
    source = ROOT / job["source"]
    source_sha = sha256(source)
    source_ok = source_sha == job["source_sha256"]
    closure = dict(job.get("sum_flux_closure", {}))
    closure_ok = closure.get("status") == "PASS" and abs(float(closure.get("relative_difference", 1))) <= 1.0e-10
    sim = validate_sim(
        located["sim"],
        expected_geometry=Path(job["expected_geometry"]),
        expected_seed=int(job["seed"]),
    )
    log = SMOKE.validate_log(located["log"])
    receipt_payload = located["receipt_payload"]
    after_dir = directory_snapshot(located["attempt_dir"])
    directory_stable = before_dir == after_dir
    problems = []
    if sim["status"] != "PASS": problems.append("SIM")
    if log["status"] != "PASS": problems.append("log")
    if int(receipt_payload.get("returncode", -1)) != 0: problems.append("returncode")
    if not source_ok: problems.append("source_hash")
    if not closure_ok: problems.append("sum_flux_closure")
    if not directory_stable: problems.append("attempt_directory_changed")
    return {
        "status": "PASS" if not problems else "FAIL",
        "problem": None if not problems else ";".join(problems),
        "job_id": job["job_id"],
        "geometry": job["geometry"],
        "family": job["family"],
        "seed": job["seed"],
        "artifact_state": located["artifact_state"],
        "valid_artifact_path": rel(located["sim"]),
        "artifact_binding": (
            "PATH_SIZE_MTIME_INODE_PLUS_FULL_GZIP_EOF_SEMANTIC_SCAN__"
            "NO_SECOND_LARGE_FILE_HASH_PASS"
        ),
        "source": rel(source),
        "source_sha256": source_sha,
        "source_sha256_matches_plan": source_ok,
        "sum_flux_closure": closure,
        "sum_flux_closure_pass": closure_ok,
        "old_receipt": rel(located["receipt"]),
        "old_receipt_sha256": sha256(located["receipt"]),
        "old_receipt_status": receipt_payload.get("status"),
        "old_receipt_returncode": receipt_payload.get("returncode"),
        "old_receipt_problem": receipt_payload.get("sim_validation", {}).get("problem"),
        "old_receipt_preserved": True,
        "sim_revalidation": sim,
        "log_revalidation": log,
        "attempt_directory_snapshot_before": before_dir,
        "attempt_directory_snapshot_after": after_dir,
        "attempt_directory_stable": directory_stable,
    }


def run() -> dict[str, Any]:
    if OUTPUT.exists():
        raise FileExistsError(f"write-once revalidation exists: {OUTPUT}")
    terminal = terminal_authority()
    plan_payload = load_json(PLAN)
    jobs = list(plan_payload.get("jobs", []))
    if len(jobs) != 6:
        raise RuntimeError("recovery0002 plan does not contain six jobs")
    observed_keys = {(row["geometry"], row["family"]) for row in jobs}
    expected_keys = {(geometry, family) for family in FAMILIES for geometry in GEOMETRIES}
    if observed_keys != expected_keys:
        raise RuntimeError(f"six-cell matrix mismatch: {observed_keys}")
    results = [validate_job(job) for job in jobs]
    passed = len(results) == 6 and all(row["status"] == "PASS" for row in results)
    total_events = sum(row["sim_revalidation"].get("SE", 0) for row in results)
    total_deca = sum(row["sim_revalidation"].get("events_with_IA_DECA", 0) for row in results)
    total_no_deca = sum(row["sim_revalidation"].get("events_without_IA_DECA", 0) for row in results)
    payload = {
        "schema_version": 1,
        "status": (
            "PASS__REVALIDATION0001_SIX_CELL_DELAYED_PARTIAL_SCREENING_COMPATIBLE"
            if passed else "FAIL__REVALIDATION0001"
        ),
        "created_utc": now_utc(),
        "controller": rel(THIS_FILE),
        "controller_sha256": sha256(THIS_FILE),
        "recovery_plan": rel(PLAN),
        "recovery_plan_sha256": sha256(PLAN),
        "original_terminal_authority": terminal,
        "revalidation_policy": {
            "required": [
                "returncode_zero", "gzip_EOF", "SE_ID_250000_and_ID_1_to_N", "EN_1",
                "geometry", "matched_seed", "explicit_SpectralType_Mono_1e-06",
                "every_event_exactly_one_IA_INIT", "zero_2MeV_primary_artifacts",
                "overall_IA_DECA_evidence_positive", "clean_log", "sum_flux_closure",
            ],
            "reported_not_required_100_percent": "IA_DECA_event_coverage",
            "reason": (
                "No-IA-DECA triggers remain valid initialized denominator events; requiring every "
                "trigger to emit a recorded decay interaction is not a transport-integrity gate."
            ),
        },
        "jobs": results,
        "passed_jobs": sum(row["status"] == "PASS" for row in results),
        "expected_jobs": 6,
        "total_events": total_events,
        "total_events_with_IA_DECA": total_deca,
        "total_events_without_IA_DECA": total_no_deca,
        "aggregate_IA_DECA_coverage_fraction": total_deca / total_events if total_events else None,
        "aggregate_no_IA_DECA_fraction": total_no_deca / total_events if total_events else None,
        "old_attempts_or_receipts_moved_renamed_or_overwritten": False,
        "valid_artifacts_may_remain_in_FAIL_partial_directories": True,
        "coverage_status": "PARTIAL_SCREENING__P_N_ALPHA_ONLY__TWO_GEOMETRIES",
        "paper_closure_claimed": False,
        "authority_boundary": (
            "CORRECTED_EPSILON_DELAYED_TRANSPORT_AND_ANALYSIS_PIPELINE_PARTIAL_SCREENING_ONLY__"
            "NO_FULL_FAMILY_DELAYED_RESPONSE_MISSION_SENSITIVITY_PAPER_CLOSURE_OR_GEOMETRY_PROMOTION"
        ),
        "output": rel(OUTPUT),
    }
    atomic_json_once(OUTPUT, payload)
    if not passed:
        raise RuntimeError(f"revalidation failed; see {OUTPUT}")
    return payload


def self_test() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="epsilon_revalidation0001_") as value:
        temp = Path(value)
        geometry = temp / "synthetic.geo.setup"
        geometry.write_text("Version 1\n", encoding="utf-8")
        sim = temp / "synthetic.sim.gz"
        events = 20
        with gzip.open(sim, "wt", encoding="utf-8") as handle:
            handle.write(f"Geometry   {geometry}\nSeed       123456\nSpectralType Mono 1e-06\n")
            for index in range(1, events + 1):
                handle.write(f"SE\nID {index} {index}\nIA INIT 1;0;0;0.000\n")
                if index <= 17:
                    handle.write("IA DECA 2;1;4;0.0\n")
            handle.write("EN\n")
        result = validate_sim(
            sim, expected_geometry=geometry, expected_seed=123456, expected_events=events
        )
        assert result["status"] == "PASS"
        assert result["events_with_IA_DECA"] == 17
        assert result["events_without_IA_DECA"] == 3
        assert result["events_with_exactly_one_IA_INIT"] == events
        assert result["IA_INIT_2MeV_artifact_count"] == 0
    return {
        "status": "PASS__REVALIDATION0001_STATIC_SELF_TEST",
        "tests": 12,
        "synthetic_events": events,
        "synthetic_events_with_DECA": 17,
        "synthetic_events_without_DECA": 3,
        "partial_DECA_coverage_accepted": True,
        "every_event_INIT_required": True,
        "transport_launched": False,
        "campaign_files_written": False,
    }


def print_plan() -> dict[str, Any]:
    terminal_available = ORIGINAL_SUMMARY.is_file()
    return {
        "status": "READY_TO_REVALIDATE" if terminal_available and not OUTPUT.exists() else (
            "REVALIDATION_EXISTS" if OUTPUT.exists() else "WAITING_FOR_ORIGINAL_CONTROLLER_TERMINAL_SUMMARY"
        ),
        "controller": rel(THIS_FILE),
        "input_recovery": rel(RECOVERY_ROOT),
        "original_terminal_summary_available": terminal_available,
        "jobs": 6,
        "expected_events_per_job": EXPECTED_EVENTS,
        "mode": "read_only_full_gzip_stream_revalidation",
        "DECA_gate": "overall_positive_report_fraction_not_100_percent",
        "output": rel(OUTPUT),
        "transport_launched": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--print-plan", action="store_true")
    actions.add_argument("--self-test", action="store_true")
    actions.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if args.print_plan:
        payload = print_plan()
    elif args.self_test:
        payload = self_test()
    else:
        payload = run()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
