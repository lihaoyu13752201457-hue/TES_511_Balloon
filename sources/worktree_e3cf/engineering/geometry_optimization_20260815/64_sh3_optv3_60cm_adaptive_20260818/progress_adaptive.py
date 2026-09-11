#!/usr/bin/env python3
"""Terminal progress display for an adaptive campaign."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()
    state_path = args.root / "adaptive_state.json"
    while True:
        if not state_path.is_file():
            print("waiting for adaptive_state.json", flush=True); time.sleep(args.interval); continue
        try: state = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception: time.sleep(args.interval); continue
        target = float(state.get("duration_target_s", 1))
        started = datetime.fromisoformat(state["started_at"])
        elapsed = max(0.0, (datetime.now(started.tzinfo) - started).total_seconds())
        fraction = min(1.0, elapsed / target)
        width = 44; fill = round(width * fraction)
        bar = "█" * fill + "░" * (width - fill)
        print("\033[2J\033[H", end="")
        print("SH3 OptV3 60 cm adaptive full transport — 6 corrected + 2 PARMA511 workers")
        print(f"[{bar}] {100*fraction:6.2f}%  elapsed={elapsed/60:7.2f} min  target={target/60:.1f} min")
        print(f"state={state.get('status')}  updated={state.get('updated_at')}")
        for name, profile in state.get("profiles", {}).items():
            active = ""
            config = profile.get("current_cycle_config")
            if config:
                controller = Path(config).parent / "run/controller_state.json"
                if controller.is_file():
                    try:
                        c = json.loads(controller.read_text(encoding="utf-8"))
                        active = f" controller={c.get('status')} {c.get('completed_count',0)}/{c.get('planned_jobs',0)} active={len(c.get('active',{}))}"
                    except Exception: pass
            print(f"{name:10s} {profile.get('status'):30s} cycles={profile.get('cycles_completed',state.get('rounds_completed',0)):3d} jobs={profile.get('jobs_completed',0):4d} events={profile.get('events_completed',0):12,d} size={profile.get('artifact_bytes',0)/1024**3:8.2f} GiB{active}")
        if state.get("status") in {"COMPLETE_TIME_BUDGET_DRAINED", "FAILED"}:
            return 0 if state.get("status") != "FAILED" else 1
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
