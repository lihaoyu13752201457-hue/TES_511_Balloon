#!/usr/bin/env python3
"""Rebuild the constant-reference prompt reweighting validation products."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV = ROOT / "statistics" / "nextphase_511" / "time_variable_day1_day20" / "environment_grid" / "env_grid.csv"
DEFAULT_SUMMARY = ROOT / "statistics" / "day15_complete_report" / "complete_day15_summary.json"
DEFAULT_OUT = ROOT / "statistics" / "nextphase_511" / "time_variable_day1_day20" / "prompt_reweight"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def env_days(env_grid: Path) -> list[tuple[float, float, float]]:
    seen: dict[tuple[float, float], float] = {}
    for row in read_csv(env_grid):
        day = float(row["day"])
        time_s = float(row["time_s"])
        scale = float(row.get("scale_to_ref") or 1.0)
        seen[(day, time_s)] = scale
    return [(day, time_s, seen[(day, time_s)]) for day, time_s in sorted(seen)]


def rebuild(env_grid: Path, summary_json: Path, outdir: Path) -> dict[str, Any]:
    summary = json.loads(summary_json.read_text(encoding="utf-8"))
    prompt_rates = summary["expectation_rates_by_stream_cps"]["prompt"]
    rows = []
    scale_rows = []
    scales = []
    for day, time_s, scale in env_days(env_grid):
        scales.append(scale)
        scale_rows.append({
            "time_s": time_s,
            "day": day,
            "prompt_scale_to_ref": scale,
        })
        rows.append({
            "time_s": time_s,
            "day": day,
            "prompt_scale_to_ref": scale,
            "prompt_raw_cps": float(prompt_rates["raw"]) * scale,
            "prompt_bgo_cps": float(prompt_rates["bgo"]) * scale,
            "prompt_final_cps": float(prompt_rates["final"]) * scale,
        })

    write_csv(outdir / "prompt_scale_by_time.csv", scale_rows, ["time_s", "day", "prompt_scale_to_ref"])
    write_csv(outdir / "prompt_rate_ledger.csv", rows, [
        "time_s", "day", "prompt_scale_to_ref", "prompt_raw_cps", "prompt_bgo_cps", "prompt_final_cps",
    ])

    result = {
        "status": "PASS",
        "mode": "constant_prompt_reweight",
        "env_grid": rel(env_grid),
        "summary_json": rel(summary_json),
        "reference_prompt_rates_cps": {
            "raw": float(prompt_rates["raw"]),
            "bgo": float(prompt_rates["bgo"]),
            "final": float(prompt_rates["final"]),
        },
        "scale_min": min(scales) if scales else 1.0,
        "scale_max": max(scales) if scales else 1.0,
        "outputs": [
            "prompt_scale_by_time.csv",
            "prompt_rate_ledger.csv",
        ],
        "caveat": "Constant reference only; particle/angle/energy-resolved prompt reweighting still requires real environment spectra.",
    }
    (outdir / "prompt_reweight_summary.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-grid", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    print(json.dumps(rebuild(args.env_grid, args.summary, args.out), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
