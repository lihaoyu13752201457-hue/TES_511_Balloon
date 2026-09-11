#!/usr/bin/env python3
"""Audited recovery for the batch0006 SIM-ID validator defect.

The first controller accepted only a one-field ``ID`` record although Cosima
writes ``ID <event> <trigger>``.  It therefore isolated two physically complete
same-seed attempts before stopping the campaign.  This recovery preserves all
of that evidence, selects the chronologically first attempt by a rule fixed
without looking at physics outcomes, revalidates it with the established
batch0000 parser contract, and resumes the original frozen plan and clock.

No frozen authority is overwritten.  Recovery publications use explicit
``recovery0001`` names and are hash-bound by a write-once amendment.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import re
import signal
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import run_m05_16h_campaign_batch0006 as campaign
from validate_m05_campaign_batch0006 import verify_source_patch_exact


RECOVERY_ID = "batch0006_recovery0001_sim_id_parser"
FROZEN_CONTROLLER_SHA256 = "edd6b32e28eeee6e4d44aa2e052926d9a646b26108d948ef86c1f0d24814416f"
FROZEN_GLOBAL_CONTRACT_SHA256 = "4586fb62a16c0145401a997f70a878bfaebd94529fe04c45da51a1abcf102275"
OLD_ID_PATTERN = r"^ID\s+(\d+)\s*$"
CORRECT_ID_PATTERN = r"^ID\s+(\d+)(?:\s|$)"
STRICT_ID_PAIR_RE = re.compile(r"^ID\s+(\d+)\s+(\d+)\s*$")

RECOVERY_AUTHORITY = campaign.RUN_ROOT / "recovery0001_authority.json"
RECOVERY_SMOKE_DECISION = campaign.RUN_ROOT / "smoke_decision.recovery0001.json"
RECOVERY_FINAL_VALIDATION = campaign.RUN_ROOT / "final_validation.recovery0001.json"
RECOVERY_FINAL_LEDGER = campaign.RUN_ROOT / "final_ledger.recovery0001.json"
RECOVERY_FINAL_UMBRELLA = campaign.RUN_ROOT / "final_umbrella.recovery0001.json"

RECOVERY_STAGE_PATHS = {
    "stage00_mergeable_smoke": (
        campaign.RUN_ROOT / "checkpoint_authority/smoke_validation.recovery0001.json",
        campaign.RUN_ROOT / "checkpoint_authority/smoke_ledger.recovery0001.json",
    ),
    "stage10_seven_family": (
        campaign.RUN_ROOT / "seven_family_validation.recovery0001.json",
        campaign.RUN_ROOT / "seven_family_ledger.recovery0001.json",
    ),
    "stage20_proton": (
        campaign.RUN_ROOT / "proton_validation.recovery0001.json",
        campaign.RUN_ROOT / "proton_ledger.recovery0001.json",
    ),
}


def recovery_stage_paths(stage: str) -> tuple[Path, Path]:
    return RECOVERY_STAGE_PATHS[stage]


def frozen_contract() -> dict[str, Any]:
    if not campaign.GLOBAL_CONTRACT.is_file():
        raise RuntimeError("batch0006 frozen global contract is missing")
    if campaign.sha256(campaign.GLOBAL_CONTRACT) != FROZEN_GLOBAL_CONTRACT_SHA256:
        raise RuntimeError("batch0006 frozen global contract SHA-256 differs")
    contract = campaign.load_json(campaign.GLOBAL_CONTRACT)
    if contract.get("controller", {}).get("sha256") != FROZEN_CONTROLLER_SHA256:
        raise RuntimeError("frozen contract does not name the failed controller SHA-256")
    if campaign.sha256(campaign.THIS_FILE) != FROZEN_CONTROLLER_SHA256:
        raise RuntimeError("failed controller file changed after global-contract freeze")
    return contract


def failed_validation_paths() -> list[Path]:
    root = (
        campaign.RUN_ROOT
        / "failed_attempts/s00_gamma_instant_Mass_model_511_shard0001"
    )
    return [root / "attempt01/validation.json", root / "attempt02/validation.json"]


def authority_payload() -> dict[str, Any]:
    failures = failed_validation_paths()
    if not all(path.is_file() for path in failures):
        raise RuntimeError("the two parser-failed attempts are not both preserved")
    records = []
    for path in failures:
        payload = campaign.load_json(path)
        errors = list(payload.get("errors", []))
        if not errors or set(errors) != {"IA INIT outside event"}:
            raise RuntimeError(f"unexpected first-controller failure class: {campaign.rel(path)}")
        if payload.get("returncode") != 0 or payload.get("watchdog_reason") != "completed":
            raise RuntimeError(f"transport itself did not complete cleanly: {campaign.rel(path)}")
        records.append(
            {
                "path": campaign.rel(path),
                "sha256": campaign.sha256(path),
                "returncode": payload["returncode"],
                "watchdog_reason": payload["watchdog_reason"],
                "generated": payload.get("log", {}).get("generated"),
                "TT_s": payload.get("isotope_dat", {}).get("TT_s"),
            }
        )
    return {
        "schema_version": 1,
        "recovery_id": RECOVERY_ID,
        "status": "PASS__NON_PHYSICS_VALIDATOR_AMENDMENT__RESUME_AUTHORIZED",
        "batch_id": campaign.BATCH_ID,
        "global_contract": campaign.rel(campaign.GLOBAL_CONTRACT),
        "global_contract_sha256": FROZEN_GLOBAL_CONTRACT_SHA256,
        "frozen_controller": {
            "path": campaign.rel(campaign.THIS_FILE),
            "sha256": FROZEN_CONTROLLER_SHA256,
        },
        "recovery_controller": {
            "path": campaign.rel(Path(__file__).resolve()),
            "sha256": campaign.sha256(Path(__file__).resolve()),
        },
        "defect": {
            "scope": "SIM validator only; transport/source/geometry/physics unchanged",
            "old_pattern": OLD_ID_PATTERN,
            "corrected_pattern": CORRECT_ID_PATTERN,
            "cosima_record_example": "ID 1 1",
            "established_reference": campaign.rel(
                campaign.PACKAGE_ROOT / "code/validate_mergeable_two_geometry_smoke.py"
            ),
        },
        "preserved_failed_validations": records,
        "selection_rule": (
            "select attempt01, the chronologically first complete same-seed transport; "
            "do not inspect or select on physics outcome"
        ),
        "selected_for_revalidation": records[0],
        "transport_changes": [],
        "physics_changes": [],
        "source_changes": [],
        "seed_changes": [],
        "plan_changes": [],
        "clock_policy": "retain the original global-contract T0 and all hard boundaries",
        "superseded_failed_publications": {
            name: {
                "path": campaign.rel(campaign.RUN_ROOT / name),
                "sha256": campaign.sha256(campaign.RUN_ROOT / name),
            }
            for name in (
                "smoke_decision.json",
                "final_validation.json",
                "final_ledger.json",
                "final_umbrella.json",
            )
            if (campaign.RUN_ROOT / name).is_file()
        },
        "recovery_publications": {
            "smoke_decision": campaign.rel(RECOVERY_SMOKE_DECISION),
            "final_validation": campaign.rel(RECOVERY_FINAL_VALIDATION),
            "final_ledger": campaign.rel(RECOVERY_FINAL_LEDGER),
            "final_umbrella": campaign.rel(RECOVERY_FINAL_UMBRELLA),
        },
    }


def input_hash_gate(job: dict[str, Any], contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    base = campaign.source_card(str(job["geometry"]), str(job["family"]))
    frozen_source = contract["static_gate"]["sources"][f"{job['geometry']}/{job['family']}"]
    if campaign.sha256(base) != frozen_source["sha256"]:
        errors.append("base source SHA-256 drift")
    bundle = contract["static_gate"]["geometry_bundles"][str(job["geometry"])]
    for record in bundle["files"]:
        path = campaign.ROOT / record["path"]
        if not path.is_file() or campaign.sha256(path) != record["sha256"]:
            errors.append(f"geometry bundle drift: {record['path']}")
    cosima = Path(contract["static_gate"]["transport"]["cosima"])
    if not cosima.is_file() or campaign.sha256(cosima) != contract["static_gate"]["transport"]["cosima_sha256"]:
        errors.append("Cosima binary SHA-256 drift")
    return errors


def strict_log_scan(text: str, expected_events: int) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    generated_match = campaign.GENERATED_RE.search(text)
    cpu_match = campaign.CPU_RE.search(text)
    observation_match = campaign.OBS_RE.search(text)
    result = {
        "generated": int(generated_match.group(1)) if generated_match else None,
        "beam_on_cpu_s": float(cpu_match.group(1)) if cpu_match else None,
        "observation_time_s": float(observation_match.group(1)) if observation_match else None,
        "megalib_banner": "This program is part of MEGAlib version" in text,
        "qgsp_bic_hp": "QGSP_BIC_HP" in text,
        "livermore_polarized": "G4EmLivermorePolarizedPhysics" in text,
        "error_marker": (
            "***  Error" in text
            or "Segmentation fault" in text
            or "Unable to parse" in text
        ),
    }
    if result["generated"] != expected_events:
        errors.append("log generated count differs")
    if not result["megalib_banner"]:
        errors.append("MEGAlib banner missing")
    if not result["qgsp_bic_hp"] or not result["livermore_polarized"]:
        errors.append("physics-list banner mismatch")
    if result["error_marker"]:
        errors.append("log error marker present")
    if result["observation_time_s"] is None or result["observation_time_s"] <= 0:
        errors.append("log observation time is not positive")
    return result, errors


def strict_sim_framing(path: Path, expected_events: int) -> tuple[dict[str, Any], list[str]]:
    """Read through gzip EOF and close both Cosima ID columns and footer."""
    errors: list[str] = []
    first_ids: list[int] = []
    second_ids: list[int] = []
    se_count = 0
    en_count = 0
    ts_values: list[int] = []
    te_values: list[float] = []
    # A truncated gzip member raises EOFError/BadGzipFile while this loop drains.
    with gzip.open(path, "rt", encoding="utf-8", errors="strict") as handle:
        for raw in handle:
            line = raw.strip()
            if line == "SE":
                se_count += 1
            elif match := STRICT_ID_PAIR_RE.match(line):
                first_ids.append(int(match.group(1)))
                second_ids.append(int(match.group(2)))
            elif line == "EN":
                en_count += 1
            elif line.startswith("TS "):
                try:
                    ts_values.append(int(line.split()[1]))
                except (IndexError, ValueError):
                    errors.append("malformed SIM TS footer")
            elif line.startswith("TE "):
                try:
                    te_values.append(float(line.split()[1]))
                except (IndexError, ValueError):
                    errors.append("malformed SIM TE footer")
    expected = list(range(1, expected_events + 1))
    if first_ids != expected:
        errors.append("SIM first ID column is not exactly 1..N")
    if second_ids != expected or second_ids != first_ids:
        errors.append("SIM second ID column is not exactly equal to first 1..N column")
    if se_count != expected_events:
        errors.append(f"SIM SE count={se_count}, expected {expected_events}")
    if en_count != 1:
        errors.append(f"SIM EN count={en_count}, expected 1")
    if ts_values != [expected_events]:
        errors.append(f"SIM TS footer={ts_values}, expected [{expected_events}]")
    if len(te_values) != 1 or not math.isfinite(te_values[0]) or te_values[0] <= 0:
        errors.append("SIM TE footer is not unique positive finite")
    return {
        "gzip_eof": True,
        "ID_first_count": len(first_ids),
        "ID_second_count": len(second_ids),
        "ID_columns_equal": first_ids == second_ids,
        "SE_count": se_count,
        "EN_count": en_count,
        "TS": ts_values[0] if len(ts_values) == 1 else None,
        "TE_s": te_values[0] if len(te_values) == 1 else None,
    }, errors


def revalidate_first_attempt(
    job: dict[str, Any], contract: dict[str, Any], recovery_sha256: str
) -> dict[str, Any]:
    failed_dir = failed_validation_paths()[0].parent
    prior_path = failed_dir / "validation.json"
    prior = campaign.load_json(prior_path)
    if prior.get("job") != job:
        raise RuntimeError("selected failed attempt job identity differs from frozen plan")
    name = str(job["job_id"])
    base = campaign.source_card(str(job["geometry"]), str(job["family"]))
    source = failed_dir / f"{name}.source"
    sim = failed_dir / f"{name}.inc1.id1.sim.gz"
    dat = failed_dir / f"{name}.dat.inc1.dat"
    log = failed_dir / f"{name}.log"
    errors = input_hash_gate(job, contract)
    for path in (source, sim, dat, log):
        if not path.is_file() or path.stat().st_size <= 0:
            errors.append(f"missing/empty preserved artifact: {path.name}")
    runtime_dir = campaign.canonical_attempt_dir(job, 1).with_name(".attempt01.partial")
    try:
        verify_source_patch_exact(
            base.read_text(encoding="utf-8"),
            source.read_text(encoding="utf-8"),
            seed=int(job["seed"]),
            events=int(job["events"]),
            sim_prefix=str(runtime_dir / name),
            isotope_prefix=str(runtime_dir / f"{name}.dat"),
            mode=str(job["mode"]),
        )
    except Exception as exc:
        errors.append(f"source exact-transform gate: {exc}")
    log_scan, log_errors = strict_log_scan(
        log.read_text(encoding="utf-8", errors="replace"), int(job["events"])
    )
    errors.extend(log_errors)
    try:
        sim_scan = campaign.scan_sim(
            sim,
            job,
            campaign.source_geometry(base),
            campaign.source_supports(base),
        )
        errors.extend(sim_scan["errors"])
        framing, framing_errors = strict_sim_framing(sim, int(job["events"]))
        sim_scan["strict_framing"] = framing
        errors.extend(framing_errors)
    except Exception as exc:
        sim_scan = {}
        errors.append(f"SIM scan exception: {exc}")
    isotope = campaign.parse_isotope_dat(dat)
    errors.extend(isotope["errors"])
    tt = isotope.get("TT_s")
    observation = log_scan.get("observation_time_s")
    if tt is not None and observation is not None and not math.isclose(
        float(tt), float(observation), rel_tol=2e-3, abs_tol=2e-6
    ):
        errors.append("DAT TT differs from log observation time")
    artifacts = {
        label: {"name": path.name, "bytes": path.stat().st_size, "sha256": campaign.sha256(path)}
        for label, path in (("source", source), ("sim", sim), ("dat", dat), ("log", log))
        if path.is_file()
    }
    result = {
        "schema_version": 2,
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "global_contract_sha256": FROZEN_GLOBAL_CONTRACT_SHA256,
        "recovery_authority_sha256": recovery_sha256,
        "recovery_revalidation": {
            "recovery_id": RECOVERY_ID,
            "source_failed_validation": campaign.rel(prior_path),
            "source_failed_validation_sha256": campaign.sha256(prior_path),
            "selection_rule": "chronologically first complete attempt",
            "new_transport_launched": False,
        },
        "job": job,
        "source": {
            "base_source": campaign.rel(base),
            "base_source_sha256": campaign.sha256(base),
            "patched_source_sha256": campaign.sha256(source),
            "corrected_references": source.read_text(encoding="utf-8").count(campaign.CORRECTED_SPECTRUM_ROOT),
            "legacy_references": source.read_text(encoding="utf-8").count(campaign.FORBIDDEN_SPECTRUM),
        },
        "log": log_scan,
        "sim": sim_scan,
        "isotope_dat": isotope,
        "returncode": int(prior["returncode"]),
        "watchdog_reason": str(prior["watchdog_reason"]),
        "wall_s": float(prior["wall_s"]),
        "peak_process_group_rss_bytes": int(prior["peak_process_group_rss_bytes"]),
        "artifacts": artifacts,
        "selected_attempt": 1,
        "attempt_dir": campaign.rel(failed_dir),
        "campaign_bytes_after_attempt": campaign.campaign_bytes(),
        "free_disk_bytes_after_attempt": __import__("shutil").disk_usage(campaign.RUN_ROOT).free,
        "mem_available_bytes_after_attempt": campaign.mem_available_bytes(),
    }
    if result["status"] != "PASS":
        raise RuntimeError("recovery revalidation failed: " + "; ".join(errors[:20]))
    return result


_ORIGINAL_VALIDATE_ATTEMPT = campaign.validate_attempt


def strict_validate_attempt(*args: Any, **kwargs: Any) -> dict[str, Any]:
    result = _ORIGINAL_VALIDATE_ATTEMPT(*args, **kwargs)
    job = args[0]
    attempt_dir = args[1]
    contract = args[6]
    errors = list(result.get("errors", []))
    errors.extend(input_hash_gate(job, contract))
    log_path = attempt_dir / f"{job['job_id']}.log"
    if log_path.is_file():
        strict_log, strict_errors = strict_log_scan(
            log_path.read_text(encoding="utf-8", errors="replace"), int(job["events"])
        )
        result["log"].update(strict_log)
        errors.extend(strict_errors)
    sim_path = attempt_dir / f"{job['job_id']}.inc1.id1.sim.gz"
    if sim_path.is_file():
        try:
            framing, framing_errors = strict_sim_framing(sim_path, int(job["events"]))
            result["sim"]["strict_framing"] = framing
            errors.extend(framing_errors)
        except Exception as exc:
            errors.append(f"strict SIM framing/EOF gate: {exc}")
    result["errors"] = list(dict.fromkeys(errors))[:100]
    result["status"] = "PASS" if not result["errors"] else "FAIL"
    result["recovery_authority_sha256"] = campaign.sha256(RECOVERY_AUTHORITY)
    return result


def strict_ensure_job(
    job: dict[str, Any],
    contract: dict[str, Any],
    environment: dict[str, str],
    hard_deadline: datetime,
) -> dict[str, Any]:
    receipt = campaign.receipt_path(job)
    if receipt.is_file():
        payload = campaign.load_json(receipt)
        if not campaign.receipt_hashes_valid(payload):
            raise RuntimeError(f"immutable PASS receipt failed hash revalidation: {job['job_id']}")
        return payload
    failures = campaign.RUN_ROOT / "failed_attempts" / str(job["job_id"])
    used = {
        int(match.group(1))
        for path in failures.glob("attempt*/validation.json")
        if (match := re.match(r"attempt(\d+)$", path.parent.name))
    }
    for attempt in range(1, campaign.MAX_ATTEMPTS + 1):
        if attempt in used:
            continue
        if datetime.now(timezone.utc) >= hard_deadline:
            raise RuntimeError("stage hard deadline before attempt")
        pre_errors = input_hash_gate(job, contract)
        if pre_errors:
            raise RuntimeError("pre-attempt input hash gate: " + "; ".join(pre_errors))
        result = campaign.run_attempt(job, attempt, contract, environment, hard_deadline)
        if result["status"] == "PASS":
            return result
    raise RuntimeError(f"{job['job_id']} exhausted two exact same-seed attempts")


def scheduled_jobs(stage: str, plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [row for row in plan if row["stage"] == stage]
    if stage != "stage10_seven_family":
        return rows
    queues: dict[str, deque[dict[str, Any]]] = defaultdict(deque)
    family_order: list[str] = []
    for row in rows:
        family = str(row["family"])
        if family not in queues:
            family_order.append(family)
        queues[family].append(row)
    totals = {family: len(queue) for family, queue in queues.items()}
    emitted = {family: 0 for family in family_order}
    ordered: list[dict[str, Any]] = []
    while any(queues.values()):
        available = [family for family in family_order if queues[family]]
        family = min(
            available,
            key=lambda name: (emitted[name] / totals[name], family_order.index(name)),
        )
        ordered.append(queues[family].popleft())
        emitted[family] += 1
    if {row["job_id"] for row in ordered} != {row["job_id"] for row in rows}:
        raise RuntimeError("family-aware schedule changed the frozen job set")
    return ordered


def bind_stage(stage: str, validation: dict[str, Any], ledger: dict[str, Any]) -> None:
    validation_path, ledger_path = recovery_stage_paths(stage)
    binding = campaign.RUN_ROOT / "checkpoint_authority" / f"{stage}.recovery0001.binding.json"
    campaign.atomic_write_once_json(
        binding,
        {
            "schema_version": 1,
            "recovery_id": RECOVERY_ID,
            "status": "PASS__HASH_BOUND_RECOVERY_PUBLICATION",
            "recovery_authority_sha256": campaign.sha256(RECOVERY_AUTHORITY),
            "validation": campaign.rel(validation_path),
            "validation_sha256": campaign.sha256(validation_path),
            "ledger": campaign.rel(ledger_path),
            "ledger_sha256": campaign.sha256(ledger_path),
            "validation_status": validation["status"],
            "ledger_status": ledger["status"],
        },
    )


def run_stage(
    stage: str,
    plan: list[dict[str, Any]],
    contract: dict[str, Any],
    environment: dict[str, str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    timing = campaign.STAGES[stage]
    t0 = datetime.fromisoformat(contract["wall_clock"]["t0"])
    start = t0 + __import__("datetime").timedelta(seconds=int(timing["start_s"]))
    stop_launch = t0 + __import__("datetime").timedelta(seconds=int(timing["stop_launch_s"]))
    hard_end = t0 + __import__("datetime").timedelta(seconds=int(timing["hard_end_s"]))
    campaign.wait_until(start, contract, stage, plan)
    failure: str | None = None
    for job in scheduled_jobs(stage, plan):
        receipt = campaign.receipt_path(job)
        if receipt.is_file():
            if not campaign.receipt_hashes_valid(campaign.load_json(receipt)):
                failure = f"receipt revalidation failed: {job['job_id']}"
                break
            continue
        if campaign._STOP_REQUESTED or datetime.now(timezone.utc) >= stop_launch:
            break
        disk = campaign.disk_launch_gate(contract, stage)
        if disk["status"] != "PASS":
            failure = "disk stop-launch gate: " + ",".join(disk["errors"])
            break
        if campaign.mem_available_bytes() <= campaign.RSS_SCALE_HEADROOM_BYTES:
            failure = "RSS/MemAvailable stop-launch gate"
            break
        try:
            strict_ensure_job(job, contract, environment, hard_end)
        except Exception as exc:
            failure = str(exc)
            break
    validation, ledger = campaign.publish_stage(stage, plan, contract, failure)
    bind_stage(stage, validation, ledger)
    if stage == "stage00_mergeable_smoke":
        campaign.atomic_write_once_json(
            RECOVERY_SMOKE_DECISION,
            {
                "schema_version": 1,
                "batch_id": campaign.BATCH_ID,
                "recovery_id": RECOVERY_ID,
                "recovery_authority_sha256": campaign.sha256(RECOVERY_AUTHORITY),
                "selected_arm": "F_RICH_BASELINE",
                "compact_transport_authorized": False,
                "status": ledger["status"],
                "F_validation": campaign.rel(recovery_stage_paths(stage)[0]),
                "F_validation_sha256": campaign.sha256(recovery_stage_paths(stage)[0]),
                "production_may_continue": ledger["status"]
                == "PASS__BATCH0006_STAGE00_MERGE_ELIGIBLE",
            },
        )
    return validation, ledger


def publish_final(
    plan: list[dict[str, Any]], contract: dict[str, Any], fatal: str | None = None
) -> None:
    stages: dict[str, Any] = {}
    for stage, (validation, ledger) in RECOVERY_STAGE_PATHS.items():
        stages[stage] = {
            "validation": campaign.rel(validation) if validation.exists() else None,
            "validation_sha256": campaign.sha256(validation) if validation.exists() else None,
            "ledger": campaign.rel(ledger) if ledger.exists() else None,
            "ledger_sha256": campaign.sha256(ledger) if ledger.exists() else None,
        }
    receipts = [
        campaign.load_json(campaign.receipt_path(job))
        for job in plan
        if campaign.receipt_path(job).is_file()
    ]
    missing = [job["job_id"] for job in plan if not campaign.receipt_path(job).is_file()]
    validation = {
        "schema_version": 2,
        "batch_id": campaign.BATCH_ID,
        "recovery_id": RECOVERY_ID,
        "status": "PASS__VALIDATED_CAMPAIGN_PREFIX" if receipts else "FAIL__NO_VALIDATED_SHARDS",
        "errors": [fatal] if fatal else [],
        "authority_boundary": "CORRECTED_KEV_MERGEABLE_SCREENING_AND_PARTIAL_PRODUCTION_ONLY",
        "global_contract_sha256": FROZEN_GLOBAL_CONTRACT_SHA256,
        "recovery_authority_sha256": campaign.sha256(RECOVERY_AUTHORITY),
        "stages": stages,
        "validated_jobs": len(receipts),
        "validated_events": sum(int(row["job"]["events"]) for row in receipts),
        "missing_jobs": missing,
        "campaign_bytes": campaign.campaign_bytes(),
        "actual": {
            "wall_s": math.fsum(float(row["wall_s"]) for row in receipts),
            "beam_on_cpu_s": math.fsum(float(row["log"].get("beam_on_cpu_s") or 0) for row in receipts),
            "TT_s": math.fsum(float(row["isotope_dat"]["TT_s"]) for row in receipts),
            "RP_count": sum(int(row["isotope_dat"]["RP_record_count"]) for row in receipts),
            "peak_process_group_rss_bytes": max(
                (int(row["peak_process_group_rss_bytes"]) for row in receipts), default=0
            ),
        },
    }
    campaign.atomic_write_once_json(RECOVERY_FINAL_VALIDATION, validation)
    ledger = {
        "schema_version": 2,
        "batch_id": campaign.BATCH_ID,
        "recovery_id": RECOVERY_ID,
        "status": validation["status"],
        "validation": campaign.rel(RECOVERY_FINAL_VALIDATION),
        "validation_sha256": campaign.sha256(RECOVERY_FINAL_VALIDATION),
        "global_contract_sha256": FROZEN_GLOBAL_CONTRACT_SHA256,
        "recovery_authority_sha256": campaign.sha256(RECOVERY_AUTHORITY),
        "stages": stages,
        "selected_receipts": [
            {
                "path": campaign.rel(campaign.receipt_path(row["job"])),
                "sha256": campaign.sha256(campaign.receipt_path(row["job"])),
            }
            for row in receipts
        ],
        "missing_jobs": missing,
        "errors": validation["errors"],
    }
    campaign.atomic_write_once_json(RECOVERY_FINAL_LEDGER, ledger)
    campaign.atomic_write_once_json(
        RECOVERY_FINAL_UMBRELLA,
        {
            "schema_version": 2,
            "batch_id": campaign.BATCH_ID,
            "recovery_id": RECOVERY_ID,
            "status": validation["status"],
            "global_contract": campaign.rel(campaign.GLOBAL_CONTRACT),
            "global_contract_sha256": FROZEN_GLOBAL_CONTRACT_SHA256,
            "recovery_authority": campaign.rel(RECOVERY_AUTHORITY),
            "recovery_authority_sha256": campaign.sha256(RECOVERY_AUTHORITY),
            "seed_registry": campaign.rel(campaign.SEED_REGISTRY),
            "seed_registry_sha256": campaign.sha256(campaign.SEED_REGISTRY),
            "final_validation": campaign.rel(RECOVERY_FINAL_VALIDATION),
            "final_validation_sha256": campaign.sha256(RECOVERY_FINAL_VALIDATION),
            "final_ledger": campaign.rel(RECOVERY_FINAL_LEDGER),
            "final_ledger_sha256": campaign.sha256(RECOVERY_FINAL_LEDGER),
            "supersedes_only_the_parser-failed_publication_set": [
                "smoke_decision.json",
                "final_validation.json",
                "final_ledger.json",
                "final_umbrella.json",
            ],
            "authority_exclusions": [
                "full eight-family delayed response",
                "mission sensitivity",
                "geometry promotion",
                "strict proton r1 convergence",
            ],
        },
    )


def run_campaign(
    plan: list[dict[str, Any]], contract: dict[str, Any], environment: dict[str, str]
) -> int:
    fatal: str | None = None
    try:
        _validation, smoke = run_stage(
            "stage00_mergeable_smoke", plan, contract, environment
        )
        if smoke["status"] != "PASS__BATCH0006_STAGE00_MERGE_ELIGIBLE":
            raise RuntimeError("F smoke failed/incomplete after parser recovery; production forbidden")
        run_stage("stage10_seven_family", plan, contract, environment)
        run_stage("stage20_proton", plan, contract, environment)
    except Exception as exc:
        fatal = str(exc)
    finally:
        publish_final(plan, contract, fatal)
        completed = sum(campaign.receipt_path(job).is_file() for job in plan)
        campaign.update_state(
            contract,
            status="FINALIZED_RECOVERY0001" if fatal is None else "FINALIZED_RECOVERY0001_WITH_ERROR",
            stage="final",
            completed_jobs=completed,
            last_error=fatal,
        )
    if fatal:
        raise SystemExit(fatal)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-recovery-plan", action="store_true")
    parser.add_argument("--cosima", type=Path, default=campaign.COSIMA_DEFAULT)
    args = parser.parse_args()
    contract = frozen_contract()
    plan = campaign.build_plan()
    if contract.get("planned_jobs_sha256") != campaign.json_sha256(plan):
        raise RuntimeError("recovery plan differs from the frozen job registry")
    campaign.ID_RE = re.compile(CORRECT_ID_PATTERN)
    authority = authority_payload()
    first_job = next(row for row in plan if row["job_id"] == "s00_gamma_instant_Mass_model_511_shard0001")
    if args.print_recovery_plan:
        result = revalidate_first_attempt(first_job, contract, "READ_ONLY_NOT_YET_PUBLISHED")
        print(
            json.dumps(
                {
                    "status": "PASS__READ_ONLY_RECOVERY_PLAN",
                    "recovery_id": RECOVERY_ID,
                    "global_contract_sha256": FROZEN_GLOBAL_CONTRACT_SHA256,
                    "frozen_t0": contract["wall_clock"]["t0"],
                    "frozen_deadline": contract["wall_clock"]["deadline"],
                    "selected_attempt_status": result["status"],
                    "selected_attempt_events": result["sim"].get("events"),
                    "selected_attempt_IA_INIT": result["sim"].get("IA_INIT"),
                    "selected_attempt_TT_s": result["isotope_dat"].get("TT_s"),
                    "recovery_controller_sha256": authority["recovery_controller"]["sha256"],
                    "transport_launched": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    lock = campaign.acquire_lock()
    previous: dict[int, Any] = {}
    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.getsignal(signum)
            signal.signal(signum, campaign._signal_handler)
        campaign.atomic_write_once_json(RECOVERY_AUTHORITY, authority)
        recovery_sha = campaign.sha256(RECOVERY_AUTHORITY)
        receipt = campaign.receipt_path(first_job)
        if not receipt.exists():
            campaign.atomic_write_once_json(
                receipt, revalidate_first_attempt(first_job, contract, recovery_sha)
            )
        if not campaign.receipt_hashes_valid(campaign.load_json(receipt)):
            raise RuntimeError("recovery receipt hash revalidation failed")
        campaign.stage_paths = recovery_stage_paths
        campaign.SMOKE_DECISION = RECOVERY_SMOKE_DECISION
        campaign.validate_attempt = strict_validate_attempt
        campaign.ensure_job = strict_ensure_job
        loaded_contract, environment = campaign.create_or_load(
            plan, args.cosima.resolve(), datetime.now(timezone.utc)
        )
        campaign.update_state(
            loaded_contract,
            status="RUNNING__RECOVERY0001__PARSER_FIXED",
            stage="stage00_mergeable_smoke",
            completed_jobs=1,
        )
        return run_campaign(plan, loaded_contract, environment)
    finally:
        if campaign._ACTIVE_PROCESS is not None:
            campaign.terminate_group(campaign._ACTIVE_PROCESS)
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        __import__("fcntl").flock(lock.fileno(), __import__("fcntl").LOCK_UN)
        lock.close()


if __name__ == "__main__":
    raise SystemExit(main())
