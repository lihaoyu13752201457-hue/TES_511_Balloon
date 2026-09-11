#!/usr/bin/env python3
"""Non-overwriting recovery launcher for the interrupted delayed v1 prepare."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


PACKAGE = Path(__file__).resolve().parent
PIPELINE = PACKAGE / "delayed_pipeline.py"
V1_STATE = Path("/mnt/data/TES_Balloon_511_data/SH3/sh3_optv3_m05_delayed_8m_v1.pipeline_state.json")
V1_BASE = Path("/mnt/data/TES_Balloon_511_data/SH3/sh3_optv3_m05_delayed_activation_v1")
V1_TARGET = Path("/mnt/data/TES_Balloon_511_data/SH3/sh3_optv3_m05_delayed_8m_v1")
V2_BASE = Path("/mnt/data/TES_Balloon_511_data/SH3/sh3_optv3_m05_delayed_activation_recovery_v2")
V2_TARGET = Path("/mnt/data/TES_Balloon_511_data/SH3/sh3_optv3_m05_delayed_8m_recovery_v2")
V2_STATE = Path("/mnt/data/TES_Balloon_511_data/SH3/sh3_optv3_m05_delayed_8m_recovery_v2.pipeline_state.json")


def load_pipeline():
    spec = importlib.util.spec_from_file_location("optv3_delayed_pipeline_recovery_v2", PIPELINE)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import retained delayed pipeline")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def seed_from_source(path: Path) -> int:
    matches = [int(line.split()[1]) for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("Seed ")]
    if len(matches) != 1:
        raise RuntimeError(f"interrupted source does not have exactly one seed: {path}")
    return matches[0]


def main() -> int:
    if not V1_STATE.is_file() or not V1_BASE.is_dir() or V1_TARGET.exists():
        raise RuntimeError("v1 interrupted-state boundary differs from expected PREPARING/no-final-target layout")
    v1_state = json.loads(V1_STATE.read_text(encoding="utf-8"))
    if v1_state.get("status") != "PREPARING_M05_ACTIVATION":
        raise RuntimeError(f"v1 state is not the retained interrupted PREPARING state: {v1_state.get('status')}")
    if V2_STATE.exists() or V2_BASE.exists() or V2_TARGET.exists():
        raise RuntimeError("non-overwrite recovery-v2 target already exists")

    pipeline = load_pipeline()
    pipeline.BASE_TARGET = V2_BASE
    pipeline.TARGET = V2_TARGET
    pipeline.STATE_PATH = V2_STATE
    pipeline.PROFILE_BASE = "SH3_OPTV3_M05_DAY15_DELAYED_ACTIVATION_RECOVERY_20260818_V2"
    pipeline.PROFILE_RUN = "SH3_OPTV3_M05_DAY15_DELAYED_8M_RECOVERY_20260818_V2"

    v1_sources = sorted((V1_BASE / "generated/sources").glob("*.source"))
    retained_seeds = {seed_from_source(path) for path in v1_sources}
    original_seed_authorities = pipeline.global_seed_authorities

    def recovery_seed_authorities():
        occupied, authorities = original_seed_authorities()
        before = len(occupied)
        occupied.update(retained_seeds)
        authorities.append({
            "path": str((V1_BASE / "generated/sources").resolve()),
            "sha256": None,
            "new_unique_seeds": len(occupied) - before,
            "policy": "INTERRUPTED_V1_SOURCE_SEEDS_RESERVED_WITHOUT_REUSING_PARTIAL_PRODUCTS",
            "seeds": sorted(retained_seeds),
        })
        return occupied, authorities

    pipeline.global_seed_authorities = recovery_seed_authorities
    original_prepare = pipeline.prepare

    def recovery_prepare(inputs: list[tuple[str, str, Path]]) -> Path:
        config = original_prepare(inputs)
        remnants: list[dict[str, Any]] = []
        for path in sorted(V1_BASE.rglob("*")):
            if path.is_file():
                remnants.append({"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": pipeline.sha256(path)})
        pipeline.atomic_json(V2_TARGET / "RECOVERY_PROVENANCE.json", {
            "schema_version": 1,
            "status": "PASS__NON_OVERWRITING_RECOVERY_V2_PREPARED",
            "created_at": pipeline.utc_now(),
            "interrupted_v1": {
                "pipeline_state": {"path": str(V1_STATE), "sha256": pipeline.sha256(V1_STATE), "status": v1_state.get("status")},
                "base_root": str(V1_BASE),
                "final_target_absent": str(V1_TARGET),
                "remnants": remnants,
                "reserved_sampling_seeds": sorted(retained_seeds),
            },
            "recovery_v2": {"base_root": str(V2_BASE), "target": str(V2_TARGET), "state": str(V2_STATE)},
            "policy": "V1 remnants retained read-only; V2 rebuilt from authoritative completed BUILDUP receipts; no V1 partial source or sample is consumed.",
        })
        return config

    pipeline.prepare = recovery_prepare
    return pipeline.main()


if __name__ == "__main__":
    raise SystemExit(main())
