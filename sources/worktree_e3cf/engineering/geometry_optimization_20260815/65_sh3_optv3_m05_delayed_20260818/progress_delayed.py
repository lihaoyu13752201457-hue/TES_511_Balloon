#!/usr/bin/env python3
"""Terminal progress view for the queued OptV3 M05 delayed pipeline."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


STATE = Path("/mnt/data/TES_Balloon_511_data/SH3/sh3_optv3_m05_delayed_8m_v1.pipeline_state.json")
CONTROLLER = Path("/mnt/data/TES_Balloon_511_data/SH3/sh3_optv3_m05_delayed_8m_v1/run/controller_state.json")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, default=STATE)
    parser.add_argument("--controller", type=Path, default=CONTROLLER)
    args = parser.parse_args()
    while True:
        print("\033[2J\033[H", end="")
        if not args.state.is_file():
            print("SH3 OptV3 M05 delayed: waiting for pipeline state")
            time.sleep(2.0)
            continue
        state = load(args.state)
        status = str(state.get("status"))
        print("SH3 OptV3 60 cm M05 delayed — 33 jobs / 8,000,000 triggers / 8 workers")
        print(f"pipeline={status}  updated={state.get('updated_at')}")
        if args.controller.is_file():
            try:
                controller = load(args.controller)
                done = int(controller.get("completed_count", 0)); total = int(controller.get("planned_jobs", 33))
                width = 44; fill = round(width * done / max(total, 1))
                bar = "█" * fill + "░" * (width - fill)
                print(f"[{bar}] {done:2d}/{total:2d}  active={len(controller.get('active', {}))}  pending={len(controller.get('pending_jobs', []))}")
                print(f"controller={controller.get('status')}  error={controller.get('error')}")
            except Exception:
                pass
        if status in {"COMPLETE", "FAILED"}:
            return 0 if status == "COMPLETE" else 1
        time.sleep(2.0)


if __name__ == "__main__":
    raise SystemExit(main())
