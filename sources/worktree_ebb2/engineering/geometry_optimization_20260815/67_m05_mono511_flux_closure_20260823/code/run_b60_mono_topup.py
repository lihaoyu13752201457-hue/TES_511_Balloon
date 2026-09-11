#!/usr/bin/env python3
"""Prepare, run, and validate the minimum model-B60 mono-511 top-up.

The transport bundle is created below /mnt/data, never overwrites an existing
bundle, and uses the already reviewed B60 geometry plus the frozen 80-bin
day-15 PARMA source.  The canonical runner's receipts make interrupted runs
resumable.  This script does not merge or analyze detector events.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve()
PACKAGE = HERE.parents[1]
ADAPTIVE_SCRIPT = Path(
    "/home/ubuntu/.codex/worktrees/e3cf/TES_511_Balloon/engineering/"
    "geometry_optimization_20260815/64_sh3_optv3_60cm_adaptive_20260818/"
    "adaptive_campaign.py"
)
DEFAULT_ROOT = Path(
    "/mnt/data/TES_Balloon_511_data/SH3/"
    "sh3_optv3_60cm_mono511_topup_3477841_20260823_v1"
)

BASE_INCIDENT_PHOTONS = 12_140_688
REQUIRED_TOTAL_INCIDENT_PHOTONS = 15_618_529
MINIMUM_ADDITIONAL_INCIDENT_PHOTONS = (
    REQUIRED_TOTAL_INCIDENT_PHOTONS - BASE_INCIDENT_PHOTONS
)
LINE_FLUX_4PI = 0.16651547160226118
LINE_ENERGY_KEV = 510.99895
EXPECTED_SETUP_SHA256 = (
    "36e44e7bc1af3f3ae296e5f3e82ac0388d7ff28182e2897a30abfca6616b5768"
)
EXPECTED_SOURCE_CONTRACT_SHA256 = (
    "5424eeca35b20affb153c0e07c31a6582e575f511922bf55f40a5a0f77ab4326"
)
EXPECTED_LINE_FRAGMENT_SHA256 = (
    "fc386a44b096d33d12d4a096532a3a57da5743681d93e779e653ae1349f776e6"
)
EXPECTED_LINE_CONTRACT_SHA256 = (
    "87e034405d46c0a928f4e4c2aa2c36030f110f7dc8ab4c843436bf195bf9357f"
)
CONTRACT_NAME = "TOPUP_CONTRACT.json"
VALIDATION_NAME = "TOPUP_VALIDATION.json"
SOURCE80_VALIDATION_NAME = "TOPUP_SOURCE80_VALIDATION.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_exclusive_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def load_adaptive() -> Any:
    spec = importlib.util.spec_from_file_location("m05_b60_topup_adaptive", ADAPTIVE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import reviewed B60 generator: {ADAPTIVE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def shard_specs(
    total_events: int,
    minimum_additional: int = MINIMUM_ADDITIONAL_INCIDENT_PHOTONS,
    campaign_tag: str = "topup01",
) -> list[dict[str, Any]]:
    if total_events < minimum_additional:
        raise RuntimeError(
            f"top-up is below the frozen minimum: {total_events} < "
            f"{minimum_additional}"
        )
    if total_events <= 0:
        raise RuntimeError("top-up event count must be positive")
    if not campaign_tag or any(
        not (character.isalnum() or character == "_")
        for character in campaign_tag
    ):
        raise RuntimeError("campaign tag must contain only letters, digits, or underscore")
    events = [min(50_000, total_events)]
    remaining = total_events - events[0]
    while remaining:
        value = min(250_000, remaining)
        if value < 1_000 and len(events) > 1:
            events[-1] += value
            remaining = 0
        else:
            events.append(value)
            remaining -= value
    rows = []
    for ordinal, value in enumerate(events, 1):
        rows.append(
            {
                "job_id": (
                    f"m05fc_b60_{campaign_tag}_parma511_shard{ordinal:04d}"
                ),
                "family": "parma511",
                "mode": "atm511",
                "events": value,
                "canary": ordinal == 1,
            }
        )
    if sum(int(row["events"]) for row in rows) != total_events:
        raise RuntimeError("top-up shard sum does not close")
    return rows


def verify_authority(module: Any, authority: dict[str, Any]) -> None:
    if not math.isclose(float(module.LINE_FLUX_4PI), LINE_FLUX_4PI, rel_tol=0.0, abs_tol=1e-15):
        raise RuntimeError("reviewed generator PARMA flux differs")
    if not math.isclose(float(module.LINE_ENERGY_KEV), LINE_ENERGY_KEV, rel_tol=0.0, abs_tol=1e-12):
        raise RuntimeError("reviewed generator line energy differs")
    if authority.get("setup_sha256") != EXPECTED_SETUP_SHA256:
        raise RuntimeError("B60 geometry setup hash differs")
    if authority.get("source_contract_sha256") != EXPECTED_SOURCE_CONTRACT_SHA256:
        raise RuntimeError("source contract hash differs")
    if sha256(Path(module.LINE_FRAGMENT)) != EXPECTED_LINE_FRAGMENT_SHA256:
        raise RuntimeError("frozen day-15 80-bin PARMA fragment hash differs")
    if sha256(Path(module.LINE_CONTRACT)) != EXPECTED_LINE_CONTRACT_SHA256:
        raise RuntimeError("line-only transport contract hash differs")
    if authority.get("source_surface") != "60 5 0 9 60":
        raise RuntimeError("B60 source surface differs")


def normalized_line_fragment(text: str, run_id: str) -> list[str]:
    """Extract all 80 source bindings/definitions with the run name removed."""
    prefix = f"{run_id}.Source "
    rows: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith(prefix):
            rows.append("PARMA511Day15.Source " + line[len(prefix):])
        elif line.startswith("PARMA511_bin"):
            rows.append(line)
    return rows


def verify_exact_line_fragment(source_text: str, job_id: str, canonical_path: Path) -> str:
    canonical = normalized_line_fragment(
        canonical_path.read_text(encoding="utf-8"), "PARMA511Day15"
    )
    observed = normalized_line_fragment(source_text, job_id)
    if len(canonical) != 400 or observed != canonical:
        raise RuntimeError(f"normalized PARMA 80-bin fragment differs: {job_id}")
    payload = ("\n".join(canonical) + "\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def prepare(
    root: Path,
    total_events: int,
    base_incident_photons: int = BASE_INCIDENT_PHOTONS,
    required_total_incident_photons: int = REQUIRED_TOTAL_INCIDENT_PHOTONS,
    campaign_tag: str = "topup01",
    avoid_seed_roots: list[Path] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    if not str(root).startswith("/mnt/data/"):
        raise RuntimeError("top-up transport root must be below /mnt/data")
    if root.exists():
        raise FileExistsError(f"non-overwrite top-up gate: {root}")
    module = load_adaptive()
    authority = module.authority()
    verify_authority(module, authority)
    canonical = module.import_prepare()
    occupied = module.occupied_seeds(canonical)
    avoided_seed_records: list[dict[str, Any]] = []
    for seed_root in avoid_seed_roots or []:
        resolved_seed_root = seed_root.resolve()
        receipt_paths = sorted((resolved_seed_root / "run/receipts").glob("*.json"))
        if not receipt_paths:
            raise RuntimeError(f"avoid-seed root has no receipts: {resolved_seed_root}")
        seeds = [int(load_json(path)["seed"]) for path in receipt_paths]
        if len(set(seeds)) != len(seeds):
            raise RuntimeError(f"avoid-seed root contains duplicate seeds: {resolved_seed_root}")
        occupied.update(seeds)
        digest = hashlib.sha256()
        for path in receipt_paths:
            digest.update(path.name.encode("utf-8"))
            digest.update(b"\0")
            digest.update(sha256(path).encode("ascii"))
            digest.update(b"\n")
        avoided_seed_records.append(
            {
                "root": str(resolved_seed_root),
                "receipts": len(receipt_paths),
                "unique_seeds": len(set(seeds)),
                "receipts_manifest_sha256": digest.hexdigest(),
            }
        )
    minimum_additional = (
        required_total_incident_photons - base_incident_photons
    )
    if minimum_additional <= 0:
        raise RuntimeError("required total must exceed the existing incident count")
    specs = shard_specs(total_events, minimum_additional, campaign_tag)
    config = module.build_bundle(
        "parma511", root, specs, canonical, occupied, authority
    )
    plan = load_json(root / "generated/job_plan.json")
    if sum(int(row["events"]) for row in plan["jobs"]) != total_events:
        raise RuntimeError("prepared top-up event sum differs")
    if int(plan["totals"]["jobs"]) != len(specs):
        raise RuntimeError("prepared top-up job count differs")
    payload = {
        "schema_version": 1,
        "status": "PASS__B60_MONO511_MINIMUM_TOPUP_PREPARED",
        "root": str(root),
        "campaign_tag": campaign_tag,
        "base_incident_photons": base_incident_photons,
        "required_total_incident_photons": required_total_incident_photons,
        "additional_incident_photons": total_events,
        "planned_total_after_topup": base_incident_photons + total_events,
        "avoided_seed_authorities": avoided_seed_records,
        "jobs": len(specs),
        "line_energy_keV": LINE_ENERGY_KEV,
        "line_flux_4pi_ph_cm2_s": LINE_FLUX_4PI,
        "authority": authority,
        "config": str(config),
        "hashes": {
            "config.json": sha256(config),
            "generated/job_plan.json": sha256(root / "generated/job_plan.json"),
            "generated/seed_registry.json": sha256(root / "generated/seed_registry.json"),
            "generated/source_manifest.json": sha256(root / "generated/source_manifest.json"),
            "day15_parma_80bin_fragment": sha256(Path(module.LINE_FRAGMENT)),
            "line_only_transport_contract": sha256(Path(module.LINE_CONTRACT)),
            "generator": sha256(HERE),
            "reviewed_bundle_generator": sha256(ADAPTIVE_SCRIPT),
        },
        "sim_hash_policy": "PATH_SIZE_HEADER_ONLY__NO_FULL_SIM_DIGEST",
    }
    write_exclusive_json(root / CONTRACT_NAME, payload)
    print(json.dumps(payload, indent=2, sort_keys=True), flush=True)
    return payload


def validate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    contract = load_json(root / CONTRACT_NAME)
    if contract.get("status") != "PASS__B60_MONO511_MINIMUM_TOPUP_PREPARED":
        raise RuntimeError("top-up preparation contract is not PASS")
    module = load_adaptive()
    current_authority = module.authority()
    verify_authority(module, current_authority)
    if current_authority != contract.get("authority"):
        raise RuntimeError("top-up frozen authority differs from preparation contract")
    controller_path = root / "run/controller_state.json"
    controller = load_json(controller_path)
    if controller.get("status") != "COMPLETE" or controller.get("error") is not None:
        raise RuntimeError("top-up controller is not complete")
    receipts_dir = root / "run/receipts"
    receipt_paths = sorted(receipts_dir.glob("*.json"))
    receipts = [load_json(path) for path in receipt_paths]
    expected_jobs = int(contract["jobs"])
    if (
        len(receipts) != expected_jobs
        or int(controller.get("completed_count", -1)) != expected_jobs
    ):
        raise RuntimeError("top-up receipt/controller count differs")
    if any(row.get("status") != "PASS" or row.get("errors") for row in receipts):
        raise RuntimeError("top-up contains a non-PASS receipt")
    seeds = [int(row["seed"]) for row in receipts]
    if len(set(seeds)) != len(seeds):
        raise RuntimeError("top-up seeds are not unique")
    expected_setup = Path(contract["authority"]["setup_path"]).resolve()
    total_events = 0
    total_bytes = 0
    total_exposure = 0.0
    normalized_fragment_sha256: str | None = None
    for row in receipts:
        total_events += int(row["events"])
        total_bytes += int(row["artifact_bytes"])
        total_exposure += float(row["log"]["observation_time_s"])
        if int(row["log"]["generated_events"]) != int(row["events"]):
            raise RuntimeError(f"generated-event mismatch: {row['job_id']}")
        if Path(row["setup_path"]).resolve() != expected_setup:
            raise RuntimeError(f"setup mismatch: {row['job_id']}")
        if Path(row["sim_header"]["geometry"]).resolve() != expected_setup:
            raise RuntimeError(f"SIM header geometry mismatch: {row['job_id']}")
        if int(row["sim_header"]["seed"]) != int(row["seed"]):
            raise RuntimeError(f"SIM header seed mismatch: {row['job_id']}")
        sim = Path(row["sim_path"])
        source = Path(row["source_path"])
        if not sim.is_file() or sim.stat().st_size != int(row["sim_bytes"]):
            raise RuntimeError(f"SIM path/size mismatch: {row['job_id']}")
        if not source.is_file() or sha256(source) != row["source_sha256"]:
            raise RuntimeError(f"source path/hash mismatch: {row['job_id']}")
        text = source.read_text(encoding="utf-8")
        if text.count(".Spectrum Mono 510.99895") != 80 or text.count(".Source ") != 80:
            raise RuntimeError(f"source 80-bin binding differs: {row['job_id']}")
        observed_fragment_sha256 = verify_exact_line_fragment(
            text, str(row["job_id"]), Path(module.LINE_FRAGMENT)
        )
        if normalized_fragment_sha256 is None:
            normalized_fragment_sha256 = observed_fragment_sha256
        elif observed_fragment_sha256 != normalized_fragment_sha256:
            raise RuntimeError("normalized PARMA fragments differ across top-up jobs")
        flux = math.fsum(
            float(line.rsplit(maxsplit=1)[-1])
            for line in text.splitlines()
            if ".Flux " in line and not line.lstrip().startswith("#")
        )
        if not math.isclose(flux, LINE_FLUX_4PI, rel_tol=0.0, abs_tol=2e-15):
            raise RuntimeError(f"source PARMA flux differs: {row['job_id']}")
    requested = int(contract["additional_incident_photons"])
    if total_events != requested:
        raise RuntimeError(f"top-up event total differs: {total_events} vs {requested}")
    receipt_digest = hashlib.sha256()
    for path in receipt_paths:
        receipt_digest.update(path.name.encode("utf-8"))
        receipt_digest.update(b"\0")
        receipt_digest.update(sha256(path).encode("ascii"))
        receipt_digest.update(b"\n")
    payload = {
        "schema_version": 1,
        "status": "PASS__B60_MONO511_MINIMUM_TOPUP_TRANSPORT_COMPLETE",
        "root": str(root),
        "jobs": len(receipts),
        "additional_incident_photons": total_events,
        "combined_incident_photons": (
            int(contract["base_incident_photons"]) + total_events
        ),
        "physical_exposure_s": total_exposure,
        "artifact_bytes": total_bytes,
        "unique_seeds": len(set(seeds)),
        "geometry_setup": str(expected_setup),
        "geometry_setup_sha256": sha256(expected_setup),
        "line_energy_keV": LINE_ENERGY_KEV,
        "line_flux_4pi_ph_cm2_s": LINE_FLUX_4PI,
        "receipts_manifest_sha256": receipt_digest.hexdigest(),
        "sim_hashes_computed": 0,
        "contract_sha256": sha256(root / CONTRACT_NAME),
        "controller_sha256": sha256(controller_path),
    }
    output = root / VALIDATION_NAME
    if output.exists():
        existing = load_json(output)
        if existing != payload:
            raise RuntimeError("existing top-up validation differs; refusing overwrite")
    else:
        write_exclusive_json(output, payload)
    source80_payload = {
        "schema_version": 1,
        "status": "PASS__EXACT_NORMALIZED_PARMA_80BIN_FRAGMENT",
        "root": str(root),
        "jobs_validated": len(receipts),
        "bins_per_job": 80,
        "line_energy_keV": LINE_ENERGY_KEV,
        "line_flux_4pi_ph_cm2_s": LINE_FLUX_4PI,
        "canonical_fragment_sha256": sha256(Path(module.LINE_FRAGMENT)),
        "normalized_fragment_sha256": normalized_fragment_sha256,
        "contract_sha256": sha256(root / CONTRACT_NAME),
        "controller_sha256": sha256(controller_path),
        "receipts_manifest_sha256": receipt_digest.hexdigest(),
    }
    source80_output = root / SOURCE80_VALIDATION_NAME
    if source80_output.exists():
        if load_json(source80_output) != source80_payload:
            raise RuntimeError("existing exact source validation differs; refusing overwrite")
    else:
        write_exclusive_json(source80_output, source80_payload)
    print(json.dumps(payload, indent=2, sort_keys=True), flush=True)
    return payload


def run_transport(root: Path) -> dict[str, Any]:
    root = root.resolve()
    contract = load_json(root / CONTRACT_NAME)
    config = Path(contract["config"])
    controller_path = root / "run/controller_state.json"
    if controller_path.is_file():
        controller = load_json(controller_path)
        if controller.get("status") == "COMPLETE" and controller.get("error") is None:
            return validate(root)
    module = load_adaptive()
    command = [
        sys.executable,
        str(module.RUNNER),
        "--config",
        str(config),
        "--workers",
        "2",
    ]
    log_path = root / "runner.log"
    with log_path.open("a", encoding="utf-8", buffering=1) as handle:
        completed = subprocess.run(
            command,
            cwd=module.REPO,
            stdout=handle,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if completed.returncode != 0:
        raise RuntimeError(f"canonical runner failed with code {completed.returncode}")
    return validate(root)


def self_test() -> dict[str, Any]:
    rows = shard_specs(MINIMUM_ADDITIONAL_INCIDENT_PHOTONS)
    assert sum(int(row["events"]) for row in rows) == MINIMUM_ADDITIONAL_INCIDENT_PHOTONS
    assert rows[0]["events"] == 50_000 and rows[0]["canary"]
    assert sum(bool(row["canary"]) for row in rows) == 1
    assert max(int(row["events"]) for row in rows) <= 250_000
    second_increment = 36_595
    second_rows = shard_specs(second_increment, second_increment, "topup02")
    assert len(second_rows) == 1
    assert second_rows[0]["events"] == second_increment
    assert second_rows[0]["canary"]
    assert "topup02" in second_rows[0]["job_id"]
    module = load_adaptive()
    normalized_fragment_sha256 = verify_exact_line_fragment(
        Path(module.LINE_FRAGMENT).read_text(encoding="utf-8"),
        "PARMA511Day15",
        Path(module.LINE_FRAGMENT),
    )
    assert normalized_fragment_sha256 == (
        "91463c9f6c6be08ec974354860ac6470e4d7e32e97b56ea459dedbc0ed4382a0"
    )
    payload = {
        "status": "PASS__B60_MONO511_TOPUP_SELF_TEST",
        "jobs": len(rows),
        "additional_incident_photons": MINIMUM_ADDITIONAL_INCIDENT_PHOTONS,
        "planned_total_incident_photons": REQUIRED_TOTAL_INCIDENT_PHOTONS,
        "iterative_minimum_topup_supported": second_increment,
        "normalized_parma_80bin_fragment_sha256": normalized_fragment_sha256,
        "transport_started": False,
        "outputs_created": 0,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    prepare_parser.add_argument(
        "--events", type=int, default=MINIMUM_ADDITIONAL_INCIDENT_PHOTONS
    )
    prepare_parser.add_argument(
        "--base-incident-photons", type=int, default=BASE_INCIDENT_PHOTONS
    )
    prepare_parser.add_argument(
        "--required-total-incident-photons",
        type=int,
        default=REQUIRED_TOTAL_INCIDENT_PHOTONS,
    )
    prepare_parser.add_argument("--campaign-tag", default="topup01")
    prepare_parser.add_argument(
        "--avoid-seeds-root", type=Path, action="append", default=[]
    )
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    subparsers.add_parser("self-test")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(
            args.root,
            args.events,
            args.base_incident_photons,
            args.required_total_incident_photons,
            args.campaign_tag,
            args.avoid_seeds_root,
        )
    elif args.command == "run":
        run_transport(args.root)
    elif args.command == "validate":
        validate(args.root)
    else:
        self_test()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
