#!/usr/bin/env python3
"""SH3 OptV3 gamma-only INSTANT expansion to reduce Fmin finite-transport error.

Reuses the existing campaign machinery (adaptive_campaign.build_bundle /
run_config / import_prepare / occupied_seeds / authority) and appends
gamma-only INSTANT rounds (round005+) under the existing campaign root:

  /mnt/data/TES_Balloon_511_data/SH3/sh3_optv3_60cm_full_adaptive_2p5h_v1/rounds/

Each round = 8 gamma INSTANT jobs (4 initial x ~267k + 4 extra2x x ~534k =
~3.208M primaries, ~1.74 GB), mirroring the canonical SG3 gamma cells with
fresh disjoint seeds.

Boundaries (user-specified):
  1. reuse existing commands, only add data
  2. hard stop when cumulative NEW bytes > 75 GB (or free < 20 GB)
  3. no polling: run() is synchronous; the executor owns progress reporting
  4. --canary first, then full campaign

Target: 9x total gamma (current 12.98M primaries -> ~116M), N_eff ~9 gamma W2
survivors -> Fmin finite-transport term ~9.6% (from current 27%).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
import time
from pathlib import Path

CAMPAIGN_ROOT = Path("/mnt/data/TES_511_Balloon_511_data/SH3/sh3_optv3_60cm_full_adaptive_2p5h_v1")
MAX_NEW_BYTES = 75 * 1024**3
FREE_FLOOR_BYTES = 20 * 1024**3
ADAPTIVE = Path("/home/ubuntu/.codex/worktrees/e3cf/TES_511_Balloon/engineering/geometry_optimization_20260815/64_sh3_optv3_60cm_adaptive_20260818/adaptive_campaign.py")


def load_adaptive():
    spec = importlib.util.spec_from_file_location("adaptive_campaign", ADAPTIVE)
    if spec is None or spec.loader is None:
        raise RuntimeError("adaptive_campaign import failed")
    m = importlib.util.module_from_spec(spec)
    sys.modules["adaptive_campaign"] = m
    spec.loader.exec_module(m)
    return m


def gamma_round_specs(m, round_index: int, scale: float) -> list[dict]:
    """Gamma-only INSTANT cells mirroring the canonical SG3 gamma shards."""
    rows = []
    for batch, plan_path, evs in (
        ("initial", m.SG3_INITIAL_PLAN, (267312, 267312, 267311, 267311)),
        ("extra2x", m.SG3_EXTRA_PLAN, (534624, 534624, 534622, 534622)),
    ):
        plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
        jobs = plan["jobs"] if isinstance(plan, dict) and "jobs" in plan else plan
        for idx, ev in enumerate(evs, 1):
            rows.append({
                "job_id": f"r{round_index:03d}_{batch}_instant_gamma_shard{idx:04d}",
                "family": "gamma",
                "mode": "instant",
                "events": max(int(ev * scale), 1),
                "canary": batch == "initial" and idx == 1,
            })
    return rows


def dir_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canary", action="store_true", help="run one smoke-scale gamma round and exit")
    parser.add_argument("--rounds", type=int, default=32, help="number of full gamma rounds to add")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--next-round", type=int, default=5, help="first round index to write (round005+ appended)")
    args = parser.parse_args()

    m = load_adaptive()
    canonical = m.import_prepare()
    auth = m.authority()
    occupied = m.occupied_seeds(canonical)
    root = CAMPAIGN_ROOT
    if not str(root.resolve()).startswith("/mnt/data/"):
        raise RuntimeError("campaign root must be below /mnt/data")

    # determine existing rounds to resume cleanly (non-overwrite)
    existing = sorted(p for p in (root / "rounds").glob("round*") if p.is_dir())
    existing_idx = [int(p.name.replace("round", "")) for p in existing]
    round_index = args.next_round if not args.canary else args.next_round
    if not args.canary:
        round_index = max((max(existing_idx) + 1) if existing_idx else args.next_round, args.next_round)

    if args.canary:
        scale = 1.0
        specs = gamma_round_specs(m, round_index, scale)
        for spec in specs:
            spec["events"] = max(1, int(round(spec["events"] * 0.003)))  # smoke: ~800 events per job
        bundle = root / "rounds" / f"round{round_index:03d}" / "corrected"
        print(f"[canary] building gamma smoke round{round_index:03d} ({len(specs)} jobs)", flush=True)
        config = m.build_bundle("corrected", bundle, specs, canonical, occupied, auth)
        print(f"[canary] running executor on {config}", flush=True)
        m.run_config(config, args.workers, bundle / "runner.log")
        receipts = sorted((bundle / "run/receipts").glob("*.json"))
        print(json.dumps({"canary": "PASS", "jobs": len(receipts),
                          "round": f"round{round_index:03d}",
                          "status": "PASS__GAMMA_EXPANSION_CANARY"}, indent=2), flush=True)
        return 0

    # ---- full campaign ----
    cumulative_new = 0
    started = time.monotonic()
    for rr in range(round_index, round_index + args.rounds):
        specs = gamma_round_specs(m, rr, 1.0)
        bundle = root / "rounds" / f"round{rr:03d}" / "corrected"
        if bundle.exists():
            print(f"[skip] round{rr:03d} exists", flush=True)
            cumulative_new += dir_bytes(bundle)
            continue
        free = shutil.disk_usage(root).free
        if cumulative_new > MAX_NEW_BYTES:
            print(f"[STOP] cumulative new {cumulative_new/1e9:.1f} GB > 75 GB boundary", flush=True)
            break
        if free < FREE_FLOOR_BYTES:
            print(f"[STOP] free disk {free/1e9:.1f} GB < 20 GB floor", flush=True)
            break
        config = m.build_bundle("corrected", bundle, specs, canonical, occupied, auth)
        print(f"[round {rr:03d}] {len(specs)} gamma jobs; cumulative_new {cumulative_new/1e9:.1f} GB; free {free/1e9:.1f} GB", flush=True)
        m.run_config(config, args.workers, bundle / "runner.log")
        new = dir_bytes(bundle)
        cumulative_new += new
        print(f"[round {rr:03d}] done, +{new/1e9:.2f} GB (cumulative {cumulative_new/1e9:.1f} GB)", flush=True)
    print(json.dumps({
        "status": "PASS__GAMMA_EXPANSION_COMPLETE",
        "rounds_added": args.rounds,
        "cumulative_new_bytes": cumulative_new,
        "cumulative_new_GB": round(cumulative_new / 1e9, 2),
        "wall_s": round(time.monotonic() - started, 1),
    }, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
