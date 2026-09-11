#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from external_baseline.channel_raytrace_py.geometry import load_channel_config
from external_baseline.channel_raytrace_py.parratt_reflectivity import (
    MultilayerSpec,
    compute_reflectivity_rows,
    geometric_theta_grid,
    write_reflectivity_csv,
)
from external_baseline.channel_raytrace_py.reflectivity_table import ReflectivityTable
from external_baseline.channel_raytrace_py.wallbywall_channel import (
    WallByWallOptions,
    simulate_wallbywall_channel,
    summarize_wallbywall,
    summarize_wallbywall_by_ring,
)


def safe_name(value: float) -> str:
    return str(value).replace(".", "p").replace("-", "m")


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, math.ceil(q * len(ordered)) - 1))
    return ordered[idx]


def histogram(values: list[float], bins: int, low: float, high: float) -> list[dict[str, float | int]]:
    if bins <= 0:
        raise ValueError("bins must be positive")
    width = (high - low) / bins
    counts = [0 for _ in range(bins)]
    for value in values:
        if value < low or value > high:
            continue
        idx = min(bins - 1, max(0, int((value - low) / width)))
        counts[idx] += 1
    total = sum(counts)
    return [
        {
            "bin_low_rad": low + i * width,
            "bin_high_rad": low + (i + 1) * width,
            "count": count,
            "fraction": count / total if total else 0.0,
        }
        for i, count in enumerate(counts)
    ]


def reflectivity_metrics(history) -> dict[str, float | int]:
    bounce_rows = [row for row in history if row.stage == "BOUNCE"]
    all_wall_rows = [row for row in history if row.stage in {"BOUNCE", "ABSORB", "LEAK"} and row.surface_id.startswith("wall_")]
    by_event: dict[int, list[float]] = defaultdict(list)
    for row in bounce_rows:
        by_event[row.event_id].append(row.p_reflect)
    event_mean_r = [mean(values) for values in by_event.values()]
    theta = [row.grazing_angle_rad for row in bounce_rows]
    return {
        "n_bounce_rows": len(bounce_rows),
        "n_wall_decision_rows": len(all_wall_rows),
        "bounce_weighted_mean_reflectivity": mean([row.p_reflect for row in bounce_rows]),
        "event_weighted_mean_reflectivity": mean(event_mean_r),
        "event_weighted_p10_reflectivity": quantile(event_mean_r, 0.10),
        "event_weighted_p50_reflectivity": quantile(event_mean_r, 0.50),
        "event_weighted_p90_reflectivity": quantile(event_mean_r, 0.90),
        "grazing_angle_mean_rad": mean(theta),
        "grazing_angle_p50_rad": quantile(theta, 0.50),
        "grazing_angle_p90_rad": quantile(theta, 0.90),
        "grazing_angle_p99_rad": quantile(theta, 0.99),
        "grazing_angle_max_rad": max(theta) if theta else 0.0,
    }


def write_dict_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run public-geometry channel wall-by-wall roughness sweep.")
    parser.add_argument("--config", default="config/cam511_channel_baseline.yaml")
    parser.add_argument("--n", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=20260524)
    parser.add_argument("--roughness-nm", default="0,0.2,0.5,1,2,5,10")
    parser.add_argument("--theta-min", type=float, default=1.0e-8)
    parser.add_argument("--theta-max", type=float, default=5.0e-3)
    parser.add_argument("--n-theta", type=int, default=3101)
    parser.add_argument("--hist-bins", type=int, default=40)
    parser.add_argument("--out-dir", default="records/2026-05-24_optics_evidence_gap_closure/channel")
    parser.add_argument("--run-dir", default="runs/channel_wallbywall_roughness_sweep")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    run_dir = Path(args.run_dir)
    table_dir = run_dir / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    table_dir.mkdir(parents=True, exist_ok=True)
    cfg = load_channel_config(args.config)
    theta_grid = geometric_theta_grid(args.theta_min, args.theta_max, args.n_theta)
    roughness_values = [float(item) for item in args.roughness_nm.split(",") if item.strip()]

    summary_rows: list[dict[str, object]] = []
    ring_rows: list[dict[str, object]] = []
    hist_rows: list[dict[str, object]] = []
    summaries: dict[str, object] = {}

    for index, roughness in enumerate(roughness_values):
        label = safe_name(roughness)
        spec = MultilayerSpec(roughness_nm=roughness)
        table_path = table_dir / f"WSi_511keV_roughness_{label}nm.csv"
        write_reflectivity_csv(table_path, compute_reflectivity_rows(spec, E_keV=cfg.energy_keV, theta_rad=theta_grid))
        table = ReflectivityTable.from_csv(table_path)
        options = WallByWallOptions(seed=args.seed + index, include_si_path_absorption=True, stack_id=spec.stack_id)
        events, history = simulate_wallbywall_channel(cfg, args.n, table, options)
        summary = summarize_wallbywall(cfg, events, history, options, str(table_path))
        metrics = reflectivity_metrics(history)
        rough_summary = {
            "roughness_nm": roughness,
            "table_path": str(table_path),
            **summary,
            **metrics,
        }
        summaries[label] = rough_summary
        (run_dir / f"summary_roughness_{label}nm.json").write_text(
            json.dumps(rough_summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        summary_rows.append(
            {
                "roughness_nm": roughness,
                "n_primaries": summary["n_primaries"],
                "transmissivity": summary["transmissivity"],
                "effective_area_cm2": summary["effective_area_cm2"],
                "spot_d90_cm": summary["spot_d90_cm"],
                "n_survived": summary["n_survived"],
                "n_absorbed": summary["n_absorbed"],
                "n_leaked": summary["n_leaked"],
                "n_entry_blocked": summary["n_entry_blocked"],
                "mean_bounces_per_survivor": summary["mean_bounces_per_survivor"],
                "event_weighted_mean_reflectivity": metrics["event_weighted_mean_reflectivity"],
                "bounce_weighted_mean_reflectivity": metrics["bounce_weighted_mean_reflectivity"],
                "grazing_angle_p50_rad": metrics["grazing_angle_p50_rad"],
                "grazing_angle_p90_rad": metrics["grazing_angle_p90_rad"],
                "grazing_angle_p99_rad": metrics["grazing_angle_p99_rad"],
                "schema_version": summary["schema_version"],
                "model_class": summary["model_class"],
                "is_first_principles_80pct_closure": summary["is_first_principles_80pct_closure"],
            }
        )
        for per_ring in summarize_wallbywall_by_ring(events):
            ring_rows.append({"roughness_nm": roughness, **per_ring})
        theta_values = [row.grazing_angle_rad for row in history if row.stage == "BOUNCE"]
        high = max(theta_values) if theta_values else 2.0e-4
        for bin_row in histogram(theta_values, args.hist_bins, 0.0, high):
            hist_rows.append({"roughness_nm": roughness, **bin_row})

    summary_csv = out_dir / "channel_wallbywall_roughness_sweep_summary.csv"
    ring_csv = out_dir / "channel_wallbywall_roughness_sweep_per_ring.csv"
    hist_csv = out_dir / "channel_wallbywall_roughness_sweep_grazing_hist.csv"
    json_path = out_dir / "channel_wallbywall_roughness_sweep.json"
    md_path = out_dir / "channel_wallbywall_roughness_sweep.md"
    write_dict_csv(summary_csv, summary_rows)
    write_dict_csv(ring_csv, ring_rows)
    write_dict_csv(hist_csv, hist_rows)
    json_path.write_text(
        json.dumps(
            {
                "config": args.config,
                "n_per_roughness": args.n,
                "seed_base": args.seed,
                "theta_grid": {"min": args.theta_min, "max": args.theta_max, "n": args.n_theta},
                "roughness_nm": roughness_values,
                "run_dir": str(run_dir),
                "summaries": summaries,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Channel wall-by-wall roughness systematic sweep",
        "",
        f"- config: `{args.config}`",
        f"- n_per_roughness: {args.n}",
        f"- roughness_nm: `{roughness_values}`",
        f"- run_dir: `{run_dir}`",
        f"- summary_csv: `{summary_csv}`",
        f"- per_ring_csv: `{ring_csv}`",
        f"- grazing_hist_csv: `{hist_csv}`",
        f"- summary_json: `{json_path}`",
        "",
        "## Summary",
        "",
        "| roughness_nm | T | Aeff_cm2 | spot_d90_cm | event-weighted R | bounce-weighted R | theta_p90_rad | schema | first-principles 80% |",
        "|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['roughness_nm']} | {row['transmissivity']:.6g} | {row['effective_area_cm2']:.6g} | "
            f"{row['spot_d90_cm']:.6g} | {row['event_weighted_mean_reflectivity']:.6g} | "
            f"{row['bounce_weighted_mean_reflectivity']:.6g} | {row['grazing_angle_p90_rad']:.6g} | "
            f"`{row['model_class']}` | `{row['is_first_principles_80pct_closure']}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This sweep changes W/Si roughness in the public-geometry wall-by-wall line and reports the resulting detector-handoff observables.",
            "- It is not calibrated against the 0.80 handoff line and does not tune transmission toward 0.80.",
            "- `event-weighted R` is the mean per-event bounce-reflectivity average for events with at least one reflected bounce; `bounce-weighted R` is the mean over all bounce rows.",
            "- Grazing-angle histograms are in the companion CSV and use per-roughness fixed-width bins from 0 to that run's maximum bounce grazing angle.",
            "- External IMD/DarpanX/CXRO/Henke provenance remains open; this uses the local xraydb/manual-Parratt backend.",
            "",
        ]
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
