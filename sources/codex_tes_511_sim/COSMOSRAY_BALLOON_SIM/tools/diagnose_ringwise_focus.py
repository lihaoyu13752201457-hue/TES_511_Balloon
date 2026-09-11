#!/usr/bin/env python3
"""Build ring-wise no-direct-scaling focus diagnostics."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/codex_tes_511_matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PHASE12 = ROOT / "reports2.0" / "12_FINAL_COMPACT_SOURCE_ANALYSIS"
DEFAULT_OUT = PHASE12 / "no_direct_scaling_optics_alignment"
DEFAULT_CONFIG = ROOT / "optics" / "channeling_fp" / "configs" / "cam511_channeling_fp_firstprinciples_L2_parratt.json"
DEFAULT_SAMPLES = ROOT / "optics" / "channeling_fp" / "out" / "first_principles_fast" / "L2_parratt_onaxis" / "bent_channel_samples.csv"


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--samples", default=str(DEFAULT_SAMPLES))
    ap.add_argument("--outdir", default=str(DEFAULT_OUT))
    return ap.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    order = np.argsort(values)
    v = values[order]
    w = weights[order]
    cdf = np.cumsum(w)
    if len(v) == 0:
        return float("nan")
    if cdf[-1] <= 0.0:
        return float(np.quantile(values, q))
    idx = int(np.searchsorted(cdf, q * cdf[-1], side="left"))
    return float(v[min(idx, len(v) - 1)])


def centroid(values: np.ndarray, weights: np.ndarray) -> float:
    total = float(np.sum(weights))
    if total <= 0.0:
        return float(np.mean(values))
    return float(np.sum(values * weights) / total)


def build_ringwise(config: Path, samples: Path, outdir: Path) -> dict[str, Any]:
    tables = outdir / "tables"
    figures = outdir / "figures"
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    cfg = json.loads(config.read_text(encoding="utf-8"))
    rows = read_csv(samples)
    by_ring: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_ring[int(float(row["ring_id"]))].append(row)

    f_mm = float(cfg["focus_length_m"]) * 1000.0
    ring_cfg = {int(r["id"]): r for r in cfg["rings"]}
    out_rows: list[dict[str, Any]] = []
    for ring_id in sorted(by_ring):
        subset = by_ring[ring_id]
        x = np.asarray([float(r["x_fp_mm"]) for r in subset], dtype=float)
        y = np.asarray([float(r["y_fp_mm"]) for r in subset], dtype=float)
        w = np.asarray([float(r["effective_area_term_mm2"]) for r in subset], dtype=float)
        bounce = np.asarray([float(r["bounce_count"]) for r in subset], dtype=float)
        alpha = np.asarray([float(r["last_alpha_mrad"]) for r in subset], dtype=float)
        transport = np.asarray([float(r["transport_weight"]) for r in subset], dtype=float)
        cx = centroid(x, w)
        cy = centroid(y, w)
        rr = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        cfg_r = ring_cfg[ring_id]
        bend_mrad = math.radians(float(cfg_r["bending_angle_deg"])) * 1000.0
        r_over_f_mrad = float(cfg_r["radius_mm"]) / f_mm * 1000.0
        out_rows.append(
            {
                "ring_id": ring_id,
                "radius_mm": float(cfg_r["radius_mm"]),
                "bend_angle_deg": float(cfg_r["bending_angle_deg"]),
                "bend_mrad": bend_mrad,
                "r_over_f_mrad": r_over_f_mrad,
                "bend_over_r_over_f": bend_mrad / r_over_f_mrad,
                "segment_length_mm": float(cfg_r["segment_length_mm"]),
                "n_samples": len(subset),
                "focal_centroid_x_mm": cx,
                "focal_centroid_y_mm": cy,
                "focal_centroid_radius_mm": math.hypot(cx, cy),
                "ring_D50_mm": 2.0 * weighted_quantile(rr, w, 0.50),
                "ring_D95_mm": 2.0 * weighted_quantile(rr, w, 0.95),
                "ring_Aeff_cm2": float(np.sum(w) / 100.0),
                "mean_bounce_count_weighted": centroid(bounce, np.maximum(w, 1.0e-30)),
                "median_bounce_count": float(np.median(bounce)),
                "mean_last_alpha_mrad": float(np.mean(alpha)),
                "p95_last_alpha_mrad": float(np.quantile(alpha, 0.95)),
                "mean_transport_weight": float(np.mean(transport)),
                "used_for_tuning": False,
            }
        )
    write_csv(tables / "ringwise_focus_diagnostics.csv", out_rows)

    current_lengths = [float(ring_cfg[i]["segment_length_mm"]) for i in sorted(ring_cfg)]
    reversed_lengths = list(reversed(current_lengths))
    geometry_rows = [
        {
            "variant_id": "prose_order_current",
            "radii_cm": "2.25/3.0/3.75/4.5",
            "lengths_cm": "/".join(f"{v / 10.0:g}" for v in current_lengths),
            "run_status": "current_run_available",
            "selection_reason": "paper prose interpretation and existing first-principles run; not selected by matching CAM511 spot",
            "needs_followup": False,
        },
        {
            "variant_id": "table_reverse_order_hypothesis",
            "radii_cm": "2.25/3.0/3.75/4.5",
            "lengths_cm": "/".join(f"{v / 10.0:g}" for v in reversed_lengths),
            "run_status": "not_run_in_this_fast_diagnostic",
            "selection_reason": "listed as possible table-order ambiguity; should be tested only by geometric consistency, not target matching",
            "needs_followup": True,
        },
    ]
    write_csv(tables / "geometry_sanity_variants.csv", geometry_rows)

    fig, ax = plt.subplots(figsize=(5.8, 5.2), constrained_layout=True)
    xs = [float(r["focal_centroid_x_mm"]) for r in out_rows]
    ys = [float(r["focal_centroid_y_mm"]) for r in out_rows]
    sizes = [60.0 + 20.0 * float(r["ring_Aeff_cm2"]) for r in out_rows]
    ax.scatter(xs, ys, s=sizes, c=[int(r["ring_id"]) for r in out_rows], cmap="viridis", edgecolors="black")
    for r in out_rows:
        ax.text(float(r["focal_centroid_x_mm"]), float(r["focal_centroid_y_mm"]), f"R{r['ring_id']}", ha="center", va="center", fontsize=8)
    ax.axhline(0.0, color="#94a3b8", lw=0.8)
    ax.axvline(0.0, color="#94a3b8", lw=0.8)
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_xlabel("weighted centroid x [mm]")
    ax.set_ylabel("weighted centroid y [mm]")
    ax.set_title("Ring-wise focal centroids, no direct scaling")
    fig.savefig(figures / "ringwise_centroid_map.png", dpi=180)
    plt.close(fig)

    return {
        "status": "PASS_RINGWISE_FOCUS_DIAGNOSTICS",
        "rings": len(out_rows),
        "max_centroid_radius_mm": max(float(r["focal_centroid_radius_mm"]) for r in out_rows),
        "max_bend_ratio_deviation": max(abs(float(r["bend_over_r_over_f"]) - 1.0) for r in out_rows),
        "used_for_tuning": False,
    }


def main() -> int:
    args = parse_args()
    outdir = Path(args.outdir)
    if not outdir.is_absolute():
        outdir = ROOT / outdir
    summary = build_ringwise(Path(args.config), Path(args.samples), outdir)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
