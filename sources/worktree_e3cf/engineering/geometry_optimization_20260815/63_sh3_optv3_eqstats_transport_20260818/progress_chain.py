#!/usr/bin/env python3
"""Display the canonical progress bar across two sequential profiles."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


EXECUTOR = Path("/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute")
sys.path.insert(0, str(EXECUTOR))

import progress  # noqa: E402
from common import load_config, load_plan  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current-config", required=True)
    parser.add_argument("--next-config", required=True)
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()
    profiles = [load_config(args.current_config), load_config(args.next_config)]
    for index, config in enumerate(profiles):
        plan = load_plan(config)
        rates = progress.Rates()
        while True:
            snap = progress.snapshot(config, plan, rates)
            print("\033[2J\033[H", end="")
            print(f"Sequential profile {index + 1}/2\n")
            print(progress.render(config, plan, snap), flush=True)
            status = snap["state"].get("status")
            if status == "FAILED":
                return 1
            if status == "COMPLETE":
                break
            time.sleep(args.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
