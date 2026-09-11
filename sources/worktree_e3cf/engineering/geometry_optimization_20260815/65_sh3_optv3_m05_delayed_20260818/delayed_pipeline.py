#!/usr/bin/env python3
"""Wait for OptV3 BUILDUP closure, then prepare and run M05 delayed transport.

The scientific implementation is reused from the accepted SG3B adapter and
its retained SF3/M05 activation primitives.  This adapter changes only the
input receipt discovery, geometry/candidate identities, globally fresh seeds,
and non-overwriting output roots.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


PACKAGE = Path(__file__).resolve().parent
REPO = PACKAGE.parents[2]
ADAPTIVE_ROOT = Path("/mnt/data/TES_Balloon_511_data/SH3/sh3_optv3_60cm_full_adaptive_2p5h_v1")
DATA_ROOT = Path("/mnt/data/TES_Balloon_511_data/SH3")
BASE_TARGET = DATA_ROOT / "sh3_optv3_m05_delayed_activation_v1"
TARGET = DATA_ROOT / "sh3_optv3_m05_delayed_8m_v1"
STATE_PATH = DATA_ROOT / "sh3_optv3_m05_delayed_8m_v1.pipeline_state.json"
GEOMETRY = REPO / "engineering/geometry_optimization_20260815/sh3/assembly_opt_v3/geometry/SH3_Assembly_OptV3_60cm.geo.setup"
GEO = REPO / "engineering/geometry_optimization_20260815/sh3/assembly_opt_v3/geometry/SH3_Assembly_OptV3.geo"
DET = REPO / "engineering/geometry_optimization_20260815/sh3/assembly_opt_v3/geometry/SH3_Assembly_OptV3.det"
SURFACE_RECEIPT = REPO / "engineering/geometry_optimization_20260815/64_sh3_optv3_60cm_adaptive_20260818/audit/source_surface_60cm_validation.json"
SG3B_BASE = REPO / "engineering/geometry_optimization_20260815/56_sg3b_m05_delayed_20260817/prepare_sg3b_m05_delayed.py"
SG3B_SHARD = REPO / "engineering/geometry_optimization_20260815/56_sg3b_m05_delayed_20260817/prepare_sharded_v2.py"
M05_PRIMITIVES = Path("/home/ubuntu/.codex/worktrees/ddb4/TES_511_Balloon/engineering/geometry_optimization_20260815/49_sf3_plan1_transport_20260816/code/build_sf3_activation.py")
EXECUTOR = Path("/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute/run.py")
PROGRESS = Path("/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute/progress.py")
PROFILE_BASE = "SH3_OPTV3_M05_DAY15_DELAYED_ACTIVATION_20260818_V1"
PROFILE_RUN = "SH3_OPTV3_M05_DAY15_DELAYED_8M_20260818_V1"
CANDIDATE = "SH3_OptV3_60cm"
FAMILIES = ("p", "n", "alpha", "gamma", "eminus", "eplus", "muminus", "muplus")
FORBIDDEN_TOKEN = "cosima_spectra_dp_2602units"
CORRECTED_TOKEN = "engineering/particle_source_unit_repair_20260811/spectra/correct_keV_total/"
BASE_ACTIVATION_PASS = "PASS__SH3_OPTV3_M05_DAY15_ACTIVATION_AND_DELAYED_SOURCES_READY"
BASE_PREFLIGHT_PASS = "PASS__SH3_OPTV3_M05_DELAYED_PREFLIGHT"
BASE_SOURCE_PASS = "PASS__SH3_OPTV3_M05_EXACT_POSITION_DELAYED_SOURCES"
RUN_PREFLIGHT_PASS = "PASS__SH3_OPTV3_M05_SHARDED_DELAYED_PREFLIGHT"
RUN_SOURCE_PASS = "PASS__SH3_OPTV3_M05_SHARDED_DELAYED_SOURCES"
RUN_SHARD_PASS = "PASS__SH3_OPTV3_M05_8M_SHARD_AND_SEED_CLOSURE"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.{os.getpid()}.partial")
    partial.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(partial, path)


def update_state(status: str, **fields: Any) -> None:
    state = load_json(STATE_PATH) if STATE_PATH.is_file() else {"schema_version": 1, "started_at": utc_now()}
    state.update(status=status, updated_at=utc_now(), **fields)
    atomic_json(STATE_PATH, state)


def import_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def import_transformed_module(path: Path, name: str, replacements: tuple[tuple[str, str], ...]):
    """Load retained adapter code with small, declared identity substitutions."""
    source = path.read_text(encoding="utf-8")
    for old, new in replacements:
        if old not in source:
            raise RuntimeError(f"expected retained-adapter token is missing: {old}")
        source = source.replace(old, new)
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = ""
    sys.modules[name] = module
    exec(compile(source, str(path), "exec"), module.__dict__)
    return module


def recursive_seeds(value: Any) -> Iterable[int]:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "seed" and isinstance(item, int) and item > 0:
                yield item
            yield from recursive_seeds(item)
    elif isinstance(value, list):
        for item in value:
            yield from recursive_seeds(item)


def global_seed_authorities() -> tuple[set[int], list[dict[str, Any]]]:
    paths: set[Path] = set()
    data = Path("/mnt/data/TES_Balloon_511_data")
    if data.is_dir():
        paths.update(data.glob("**/seed_registry.json"))
        paths.update(data.glob("**/receipts/*.json"))
    for root in (Path("/home/ubuntu/TES_511_Balloon"), Path("/home/ubuntu/.codex/worktrees")):
        if root.is_dir():
            paths.update(root.glob("**/*seed_registry*.json"))
            paths.update(root.glob("**/*seed_registry*.csv"))
    occupied: set[int] = set()
    records: list[dict[str, Any]] = []
    for path in sorted(paths):
        try:
            before = len(occupied)
            if path.suffix == ".json":
                occupied.update(recursive_seeds(json.loads(path.read_text(encoding="utf-8"))))
            else:
                with path.open(newline="", encoding="utf-8") as handle:
                    for row in csv.DictReader(handle):
                        raw = row.get("seed")
                        if raw and int(raw) > 0:
                            occupied.add(int(raw))
            records.append({"path": str(path.resolve()), "sha256": sha256(path), "new_unique_seeds": len(occupied) - before})
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    return occupied, records


def validate_background() -> list[tuple[str, str, Path]] | None:
    state_path = ADAPTIVE_ROOT / "adaptive_state.json"
    if not state_path.is_file():
        raise RuntimeError("adaptive state is missing")
    state = load_json(state_path)
    if state.get("status") == "RUNNING":
        return None
    if state.get("status") != "COMPLETE_TIME_BUDGET_DRAINED" or state.get("errors"):
        raise RuntimeError(f"adaptive campaign is not successful: {state.get('status')} {state.get('errors')}")
    rounds = state.get("rounds") or []
    if int(state.get("rounds_completed", -1)) != len(rounds) or not rounds:
        raise RuntimeError("adaptive round closure mismatch")
    inputs: list[tuple[str, str, Path]] = []
    for row in rounds:
        index = int(row["round"])
        round_root = ADAPTIVE_ROOT / "rounds" / f"round{index:03d}"
        activation = load_json(round_root / "corrected/ACTIVATION_POSITION_VALIDATION.json")
        if activation.get("status") != "PASS__BUILDUP_CC_IP_RP_MATCHES_DAT":
            raise RuntimeError(f"round {index} activation-position validation is not PASS")
        corrected_controller = load_json(round_root / "corrected/run/controller_state.json")
        parma_controller = load_json(round_root / "parma511/run/controller_state.json")
        if corrected_controller.get("status") != "COMPLETE" or int(corrected_controller.get("completed_count", -1)) != 41:
            raise RuntimeError(f"round {index} corrected controller is incomplete")
        if parma_controller.get("status") != "COMPLETE" or int(parma_controller.get("completed_count", -1)) != 13:
            raise RuntimeError(f"round {index} PARMA controller is incomplete")
        config = load_json(round_root / "corrected/config.json")
        receipts = [load_json(path) for path in sorted((round_root / "corrected/run/receipts").glob("*.json"))]
        buildup = [receipt for receipt in receipts if receipt.get("mode") == "buildup"]
        if len(receipts) != 41 or len(buildup) != 19 or any(receipt.get("status") != "PASS" for receipt in receipts):
            raise RuntimeError(f"round {index} corrected receipt closure differs from 41/19 PASS")
        inputs.append((f"round{index:03d}", str(config["profile_id"]), round_root / "corrected/run"))
    return inputs


def normalize_generated_metadata() -> None:
    base_activation = BASE_TARGET / "generated/activation/manifest.json"
    payload = load_json(base_activation)
    payload["status"] = BASE_ACTIVATION_PASS
    payload["candidate"] = CANDIDATE
    payload["geometry"] = str(GEOMETRY)
    payload["adapter_note"] = "OptV3 identity normalization after direct reuse of the accepted SG3B adapter."
    atomic_json(base_activation, payload)

    path = BASE_TARGET / "generated/preflight.json"
    payload = load_json(path); payload["status"] = BASE_PREFLIGHT_PASS; atomic_json(path, payload)
    path = BASE_TARGET / "generated/source_manifest.json"
    payload = load_json(path); payload["status"] = BASE_SOURCE_PASS; atomic_json(path, payload)
    path = BASE_TARGET / "config.json"
    payload = load_json(path)
    payload.update(preflight_pass_status=BASE_PREFLIGHT_PASS, source_manifest_pass_status=BASE_SOURCE_PASS, source_policy="m05_exact_position_delayed_optv3")
    atomic_json(path, payload)

    path = TARGET / "generated/preflight.json"
    payload = load_json(path); payload["status"] = RUN_PREFLIGHT_PASS; atomic_json(path, payload)
    path = TARGET / "generated/source_manifest.json"
    payload = load_json(path); payload["status"] = RUN_SOURCE_PASS; atomic_json(path, payload)
    path = TARGET / "generated/sharding_manifest.json"
    payload = load_json(path)
    payload["status"] = RUN_SHARD_PASS
    payload["candidate"] = CANDIDATE
    payload["geometry"] = str(GEOMETRY)
    payload["merge_boundary"] = "ONLY_WITHIN_IDENTICAL_SH3_OPTV3_60CM_GEOMETRY_DELAYED_MODE_AND_INCIDENT_FAMILY"
    payload["base_activation_manifest"] = {"path": str(base_activation), "sha256": sha256(base_activation)}
    atomic_json(path, payload)
    path = TARGET / "config.json"
    payload = load_json(path)
    payload.update(preflight_pass_status=RUN_PREFLIGHT_PASS, source_manifest_pass_status=RUN_SOURCE_PASS, source_policy="m05_exact_position_delayed_sharded_optv3")
    atomic_json(path, payload)


def validate_preparation(inputs: list[tuple[str, str, Path]]) -> dict[str, Any]:
    jobs = load_json(TARGET / "generated/job_plan.json")["jobs"]
    if len(jobs) != 33 or sum(int(job["events"]) for job in jobs) != 8_000_000:
        raise RuntimeError("delayed job/event closure differs from 33/8,000,000")
    if len({int(job["seed"]) for job in jobs}) != 33:
        raise RuntimeError("delayed transport seeds are not unique")
    for job in jobs:
        source = Path(job["source_path"])
        text = source.read_text(encoding="utf-8")
        required = (
            f"Geometry {GEOMETRY}", f"Seed {job['seed']}",
            f"DecayRun.Triggers {job['events']}", f"DecayRun.FileName {job['output_prefix']}",
        )
        if any(text.count(token) != 1 for token in required) or FORBIDDEN_TOKEN in text:
            raise RuntimeError(f"delayed source binding failed: {job['job_id']}")
    receipt = {
        "schema_version": 1,
        "status": "PASS__SH3_OPTV3_M05_DELAYED_33JOB_8M_PREPARATION",
        "created_at": utc_now(),
        "candidate": CANDIDATE,
        "geometry": {"setup": str(GEOMETRY), "setup_sha256": sha256(GEOMETRY), "geo_sha256": sha256(GEO), "det_sha256": sha256(DET)},
        "source_surface_receipt": {"path": str(SURFACE_RECEIPT), "sha256": sha256(SURFACE_RECEIPT)},
        "adaptive_authority": {"root": str(ADAPTIVE_ROOT), "state_sha256": sha256(ADAPTIVE_ROOT / "adaptive_state.json"), "rounds": len(inputs)},
        "buildup_inputs": [{"namespace": namespace, "profile_id": profile, "run_root": str(root)} for namespace, profile, root in inputs],
        "normalization": "sum(RP)/sum(TT) per incident family across every completed OptV3 BUILDUP round; zero-RP DAT TT retained",
        "state_policy": "NUBASE-2020 ground-state correction; excited/unresolved states fail closed; positive ground states require exact RPIP closure",
        "position_policy": "50,000 deterministic activity-weighted exact-position draws per family; stride 5 to 10,000 blocks; flux x5",
        "jobs": 33,
        "triggers": 8_000_000,
        "workers": 8,
        "reused_implementations": [
            {"path": str(SG3B_BASE), "sha256": sha256(SG3B_BASE)},
            {"path": str(SG3B_SHARD), "sha256": sha256(SG3B_SHARD)},
            {"path": str(M05_PRIMITIVES), "sha256": sha256(M05_PRIMITIVES)},
            {"path": str(EXECUTOR), "sha256": sha256(EXECUTOR)},
        ],
    }
    atomic_json(TARGET / "PREPARATION_RECEIPT.json", receipt)
    return receipt


def prepare(inputs: list[tuple[str, str, Path]]) -> Path:
    if BASE_TARGET.exists() or TARGET.exists():
        raise RuntimeError("non-overwrite delayed target already exists")
    required = (GEOMETRY, GEO, DET, SURFACE_RECEIPT, SG3B_BASE, SG3B_SHARD, M05_PRIMITIVES, EXECUTOR, PROGRESS)
    if any(not path.is_file() for path in required):
        raise RuntimeError("delayed prerequisite file is missing")
    surface = load_json(SURFACE_RECEIPT)
    if surface.get("status") != "PASS__SH3_OPTV3_SG3B_60CM_SURFACE_ENCLOSES_MATERIAL":
        raise RuntimeError("60 cm surface receipt is not PASS")

    base = import_transformed_module(SG3B_BASE, "optv3_reused_sg3b_delayed_base", (
        ("sg3b_delayed_", "optv3_delayed_"),
        ("PASS__SG3B_M05_DAY15_ACTIVATION_AND_DELAYED_SOURCES_READY", BASE_ACTIVATION_PASS),
        ("PASS__SG3B_M05_EXACT_POSITION_DELAYED_SOURCES", BASE_SOURCE_PASS),
        ("PASS__SG3B_M05_DELAYED_PREFLIGHT", BASE_PREFLIGHT_PASS),
    ))
    base.PROFILE_ID = PROFILE_BASE
    base.CANDIDATE = CANDIDATE
    base.GEOMETRY = GEOMETRY
    base.TARGET = BASE_TARGET
    base.GENERATED = BASE_TARGET / "generated"
    base.RUN_ROOT = BASE_TARGET / "run"
    base.INPUTS = tuple(inputs)
    base.REUSED_BUILDER = M05_PRIMITIVES
    original_load = base.load_reused_primitives
    original_collect = base.collect_inputs

    def adapted_load():
        core = original_load()
        renderer = core["render_delayed_source"]

        def render(*args: Any, **kwargs: Any):
            text, closure = renderer(*args, **kwargs)
            text = text.replace("Candidate-owned SF3", "Candidate-owned SH3 OptV3")
            text = text.replace("validated SF3 BUILDUP", "validated SH3 OptV3 BUILDUP")
            return text, closure

        core["render_delayed_source"] = render
        return core

    def adapted_collect(core: dict[str, Any]):
        grouped, authorities, occupied = original_collect(core)
        global_occupied, _ = global_seed_authorities()
        occupied.update(global_occupied)
        return grouped, authorities, occupied

    base.load_reused_primitives = adapted_load
    base.collect_inputs = adapted_collect
    base.prepare()

    shard = import_transformed_module(SG3B_SHARD, "optv3_reused_sg3b_delayed_sharder", (
        ("sg3b_delayed_", "optv3_delayed_"),
        ("PASS__SG3B_M05_DAY15_ACTIVATION_AND_DELAYED_SOURCES_READY", BASE_ACTIVATION_PASS),
        ("PASS__SG3B_M05_SHARDED_DELAYED_PREFLIGHT", RUN_PREFLIGHT_PASS),
        ("PASS__SG3B_M05_SHARDED_DELAYED_SOURCES", RUN_SOURCE_PASS),
        ("PASS__SG3B_M05_8M_SHARD_AND_SEED_CLOSURE", RUN_SHARD_PASS),
        ("ONLY_WITHIN_IDENTICAL_SG3B_GEOMETRY_DELAYED_MODE_AND_INCIDENT_FAMILY", "ONLY_WITHIN_IDENTICAL_SH3_OPTV3_60CM_GEOMETRY_DELAYED_MODE_AND_INCIDENT_FAMILY"),
    ))
    shard.PROFILE_ID = PROFILE_RUN
    shard.CANDIDATE = CANDIDATE
    shard.GEOMETRY = GEOMETRY
    shard.BASE = BASE_TARGET
    shard.TARGET = TARGET
    shard.GENERATED = TARGET / "generated"
    shard.RUN_ROOT = TARGET / "run"

    def adapted_seed_authorities():
        return global_seed_authorities()

    shard.seed_authorities = adapted_seed_authorities
    shard.prepare()
    normalize_generated_metadata()
    validate_preparation(inputs)
    return TARGET / "config.json"


def run_transport(config: Path) -> None:
    update_state("RUNNING_DELAYED_TRANSPORT", config=str(config), controller_state=str(TARGET / "run/controller_state.json"))
    result = subprocess.run([sys.executable, "-B", str(EXECUTOR), "--config", str(config), "--workers", "8"], check=False)
    if result.returncode != 0:
        raise RuntimeError(f"canonical delayed runner failed with return code {result.returncode}")
    controller = load_json(TARGET / "run/controller_state.json")
    receipts = [load_json(path) for path in sorted((TARGET / "run/receipts").glob("*.json"))]
    if controller.get("status") != "COMPLETE" or len(receipts) != 33 or any(row.get("status") != "PASS" for row in receipts):
        raise RuntimeError("delayed controller/receipt closure failed")
    if sum(int(row["events"]) for row in receipts) != 8_000_000:
        raise RuntimeError("accepted delayed triggers differ from 8,000,000")
    final = {
        "schema_version": 1,
        "status": "PASS__SH3_OPTV3_M05_DELAYED_33_OF_33_8M",
        "completed_at": utc_now(),
        "jobs": len(receipts),
        "triggers": sum(int(row["events"]) for row in receipts),
        "artifact_bytes": sum(int(row["artifact_bytes"]) for row in receipts),
        "families": {family: sum(int(row["events"]) for row in receipts if row["family"] == family) for family in FAMILIES},
    }
    atomic_json(TARGET / "FINAL_VALIDATION.json", final)
    update_state("COMPLETE", final_validation=str(TARGET / "FINAL_VALIDATION.json"), jobs=33, triggers=8_000_000)


def main() -> int:
    if STATE_PATH.exists() or BASE_TARGET.exists() or TARGET.exists():
        raise RuntimeError("write-once pipeline state or output target already exists")
    update_state("WAITING_FOR_ADAPTIVE_ROUND_DRAIN", adaptive_root=str(ADAPTIVE_ROOT), base_target=str(BASE_TARGET), target=str(TARGET))
    try:
        inputs = validate_background()
        while inputs is None:
            time.sleep(10.0)
            inputs = validate_background()
        update_state("PREPARING_M05_ACTIVATION", completed_rounds=len(inputs))
        config = prepare(inputs)
        update_state("PREPARATION_PASS", config=str(config), preparation_receipt=str(TARGET / "PREPARATION_RECEIPT.json"))
        run_transport(config)
        return 0
    except Exception as exc:
        update_state("FAILED", error=f"{type(exc).__name__}: {exc}")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
