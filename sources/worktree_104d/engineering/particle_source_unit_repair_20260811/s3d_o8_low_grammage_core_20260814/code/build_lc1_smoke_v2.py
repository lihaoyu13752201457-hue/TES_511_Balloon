#!/usr/bin/env python3
"""Freeze the non-overwriting v2 LC1 smoke after the v1 CLI-seed failure."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
OLD_PLAN = PACKAGE / "data/lc1_smoke_plan.json"
NEW_PLAN = PACKAGE / "data/lc1_smoke_plan_v2.json"
NEW_INPUTS = PACKAGE / "smoke_inputs_v2/sources"
OLD_RUN = "s3d_o8_low_grammage_core_smoke_20260814_v1"
NEW_RUN = "s3d_o8_low_grammage_core_smoke_20260814_v2"
SEED_MAP = {
    2130000003: 2110000003,
    2130007922: 2110007922,
    2130015841: 2110015841,
    2130023760: 2110023760,
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    if NEW_PLAN.exists() or NEW_INPUTS.parent.exists():
        raise RuntimeError("v2 plan/inputs already exist; builder is write-once")
    old = json.loads(OLD_PLAN.read_text(encoding="utf-8"))
    new_run_root = Path(old["run_root"].replace(OLD_RUN, NEW_RUN))
    jobs = []
    for job in old["jobs"]:
        old_source = Path(job["source"])
        new_source = NEW_INPUTS / job["geometry_key"] / old_source.name
        new_source.parent.mkdir(parents=True, exist_ok=True)
        new_seed = SEED_MAP[job["seed"]]
        text = old_source.read_text(encoding="utf-8")
        if text.count(str(job["seed"])) != 1 or text.count(OLD_RUN) != 1:
            raise RuntimeError(f"unexpected v1 source contract: {old_source}")
        text = text.replace(str(job["seed"]), str(new_seed), 1).replace(OLD_RUN, NEW_RUN, 1)
        new_source.write_text(text, encoding="utf-8")
        record = dict(job)
        record["seed"] = new_seed
        record["source"] = str(new_source.resolve())
        record["source_sha256"] = sha256(new_source)
        record["partial_dir"] = job["partial_dir"].replace(OLD_RUN, NEW_RUN)
        record["final_dir"] = job["final_dir"].replace(OLD_RUN, NEW_RUN)
        jobs.append(record)
    plan = dict(old)
    plan["status"] = "FROZEN_V2_AFTER_V1_CLI_SEED_FAILURE__TRANSPORT_NOT_RUN"
    plan["confirmation_token"] = "S3D_O8_LC1_MECHANISM_SMOKE_V2"
    plan["run_root"] = str(new_run_root)
    plan["jobs"] = jobs
    plan["v1_failure_provenance"] = {
        "failed_plan": str(OLD_PLAN.resolve()),
        "failed_run_root": old["run_root"],
        "reason": "runner omitted Cosima -s; source-card Seed is not a Cosima runtime seed",
        "failed_partial_preserved": True,
        "v2_fix": "runner passes -s explicitly and validates the SIM header before atomic promotion",
    }
    NEW_PLAN.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(NEW_PLAN)


if __name__ == "__main__":
    main()
