#!/usr/bin/env python3
"""Apply environment scale factors to the prompt reference rates.

The current constant-reference grid has scale_to_ref = 1.0.  This script keeps
the prompt reweighting interface explicit and verifies that the constant limit
reproduces the corrected day-15 prompt expectation.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_GRID = ROOT / "reports" / "nextphase_511" / "time_variable_day1_day20" / "environment_grid" / "env_grid.csv"
DEFAULT_SUMMARY = ROOT / "reports" / "day15_complete_report" / "complete_day15_summary.json"
DEFAULT_OUT = ROOT / "reports" / "nextphase_511" / "time_variable_day1_day20" / "prompt_reweight"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def reweight_prompt(env_grid: Path, summary_json: Path, outdir: Path) -> dict[str, object]:
    outdir.mkdir(parents=True, exist_ok=True)
    env_rows = read_csv(env_grid)
    summary = json.loads(summary_json.read_text(encoding="utf-8"))
    prompt_ref = summary["expectation_rates_by_stream_cps"]["prompt"]

    scale_by_time: dict[tuple[float, float], list[float]] = defaultdict(list)
    for row in env_rows:
        try:
            time_s = float(row["time_s"])
            day = float(row["day"])
            scale = float(row["scale_to_ref"])
        except (KeyError, ValueError):
            continue
        scale_by_time[(time_s, day)].append(scale)

    ledger_rows: list[dict[str, object]] = []
    scale_rows: list[dict[str, object]] = []
    for (time_s, day), scales in sorted(scale_by_time.items()):
        scale = sum(scales) / len(scales) if scales else 1.0
        scale_rows.append({"time_s": time_s, "day": day, "prompt_scale_to_ref": scale, "n_grid_rows": len(scales)})
        ledger_rows.append({
            "time_s": time_s,
            "day": day,
            "prompt_scale_to_ref": scale,
            "prompt_raw_cps": prompt_ref["raw"] * scale,
            "prompt_bgo_cps": prompt_ref["bgo"] * scale,
            "prompt_final_cps": prompt_ref["final"] * scale,
        })

    write_csv(outdir / "prompt_scale_by_time.csv", scale_rows, ["time_s", "day", "prompt_scale_to_ref", "n_grid_rows"])
    write_csv(outdir / "prompt_rate_ledger.csv", ledger_rows, [
        "time_s", "day", "prompt_scale_to_ref", "prompt_raw_cps", "prompt_bgo_cps", "prompt_final_cps",
    ])

    scales = [float(r["prompt_scale_to_ref"]) for r in scale_rows] or [1.0]
    passed = min(scales) == 1.0 and max(scales) == 1.0
    result = {
        "status": "PASS" if passed else "FAIL",
        "mode": "constant_prompt_reweight",
        "env_grid": str(env_grid.relative_to(ROOT) if env_grid.is_relative_to(ROOT) else env_grid),
        "summary_json": str(summary_json.relative_to(ROOT) if summary_json.is_relative_to(ROOT) else summary_json),
        "reference_prompt_rates_cps": prompt_ref,
        "scale_min": min(scales),
        "scale_max": max(scales),
        "outputs": ["prompt_scale_by_time.csv", "prompt_rate_ledger.csv"],
        "caveat": "Constant reference only; particle/angle/energy-resolved prompt reweighting still requires real environment spectra.",
    }
    (outdir / "prompt_reweight_summary.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment-grid", type=Path, default=DEFAULT_ENV_GRID)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    print(json.dumps(reweight_prompt(args.environment_grid, args.summary, args.out), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
