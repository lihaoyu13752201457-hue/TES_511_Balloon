#!/usr/bin/env python3
"""Mark the preserved recovery-v2 remnants as explicitly stopped by the user."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


STATE = Path("/mnt/data/TES_Balloon_511_data/SH3/sh3_optv3_m05_delayed_8m_recovery_v2.pipeline_state.json")
BASE = Path("/mnt/data/TES_Balloon_511_data/SH3/sh3_optv3_m05_delayed_activation_recovery_v2")
V1 = Path("/mnt/data/TES_Balloon_511_data/SH3/sh3_optv3_m05_delayed_8m_v1")


def write(path: Path, payload: dict) -> None:
    partial = path.with_name(f".{path.name}.{os.getpid()}.partial")
    partial.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, path)


def main() -> int:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    previous = state.get("status")
    if previous != "PREPARING_M05_ACTIVATION":
        raise RuntimeError(f"unexpected recovery-v2 state before stop receipt: {previous}")
    now = datetime.now(timezone.utc).isoformat()
    files = [path for path in BASE.rglob("*") if path.is_file()]
    state.update({
        "status": "STOPPED_BY_USER__V1_DELAYED_RUNNING",
        "previous_status": previous,
        "stopped_at": now,
        "updated_at": now,
        "stop_reason": "Redundant recovery-v2 stopped after the original v1 completed preparation and entered valid delayed transport.",
        "remnants_preserved": True,
        "active_authority": str(V1),
    })
    write(STATE, state)
    write(BASE / "STOP_RECEIPT.json", {
        "schema_version": 1,
        "status": "PASS__RECOVERY_V2_STOPPED_AND_REMNANTS_PRESERVED",
        "stopped_at": now,
        "previous_status": previous,
        "state_path": str(STATE),
        "preserved_root": str(BASE),
        "preserved_files": len(files),
        "preserved_bytes": sum(path.stat().st_size for path in files),
        "active_v1_delayed_root": str(V1),
        "deletion_or_move_performed": False,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
