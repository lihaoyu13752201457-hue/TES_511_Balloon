#!/usr/bin/env python3
"""Debug no-direct-scaling effective-area transport terms by ring."""

from __future__ import annotations

import argparse
import csv
import json
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


def weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    total = float(np.sum(weights))
    if total <= 0.0:
        return float(np.mean(values))
    return float(np.sum(values * weights) / total)


def per_bounce_weight(total_weight: np.ndarray, bounce_count: np.ndarray) -> np.ndarray:
    out = np.ones_like(total_weight, dtype=float)
    positive = bounce_count > 0
    out[positive] = np.power(np.clip(total_weight[positive], 0.0, 1.0), 1.0 / bounce_count[positive])
    out[~positive] = np.clip(total_weight[~positive], 0.0, 1.0)
    return out


def build_debug(config: Path, samples: Path, outdir: Path) -> dict[str, Any]:
    tables = outdir / "tables"
    figures = outdir / "figures"
    notes = outdir / "notes"
    for d in (tables, figures, notes):
        d.mkdir(parents=True, exist_ok=True)
    cfg = json.loads(config.read_text(encoding="utf-8"))
    open_fraction = float(cfg["multilayer"]["channel_gap_nm"]) / float(cfg["multilayer"]["period_nm"])
    rows = read_csv(samples)
    by_ring: dict[int | str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_ring[int(float(row["ring_id"]))].append(row)
        by_ring["TOTAL"].append(row)

    out_rows: list[dict[str, Any]] = []
    for ring_id in sorted([k for k in by_ring if isinstance(k, int)]) + ["TOTAL"]:
        subset = by_ring[ring_id]
        entrance = np.asarray([float(r["entrance_area_mm2"]) for r in subset], dtype=float)
        eff = np.asarray([float(r["effective_area_term_mm2"]) for r in subset], dtype=float)
        tw = np.asarray([float(r["transport_weight"]) for r in subset], dtype=float)
        bounce = np.asarray([float(r["bounce_count"]) for r in subset], dtype=float)
        alpha = np.asarray([float(r["last_alpha_mrad"]) for r in subset], dtype=float)
        mean_alpha = np.asarray([float(r["mean_alpha_mrad"]) for r in subset], dtype=float)
        per_bounce = per_bounce_weight(tw, bounce)
        out_rows.append(
            {
                "ring_id": ring_id,
                "n_samples": len(subset),
                "entrance_geometric_area_cm2": float(np.sum(entrance) / 100.0),
                "open_fraction": open_fraction,
                "open_geometric_area_cm2": float(np.sum(entrance) * open_fraction / 100.0),
                "Aeff_cm2": float(np.sum(eff) / 100.0),
                "Aeff_over_open_geometric": float(np.sum(eff) / (np.sum(entrance) * open_fraction)) if np.sum(entrance) > 0 else float("nan"),
                "mean_total_reflectivity_product": float(np.mean(tw)),
                "median_total_reflectivity_product": float(np.median(tw)),
                "mean_reflectivity_per_bounce": float(np.mean(per_bounce)),
                "median_reflectivity_per_bounce": float(np.median(per_bounce)),
                "mean_bounce_count": float(np.mean(bounce)),
                "median_bounce_count": float(np.median(bounce)),
                "p95_bounce_count": float(np.quantile(bounce, 0.95)),
                "mean_last_alpha_mrad": float(np.mean(alpha)),
                "p05_last_alpha_mrad": float(np.quantile(alpha, 0.05)),
                "p95_last_alpha_mrad": float(np.quantile(alpha, 0.95)),
                "weighted_mean_alpha_mrad": weighted_mean(mean_alpha, np.maximum(eff, 1.0e-30)),
                "used_for_tuning": False,
            }
        )
    write_csv(tables / "aeff_transport_debug.csv", out_rows)

    note = """# Effective-Area Transport Debug Notes

This table decomposes the current L2 effective area into entrance area, open
fraction, transport-weight product, bounce count, and grazing-angle terms.

No direct multiplication to a CAM511 target is used. If Aeff changes later, it
must come from angle convention, reflectivity physics, absorption/open fraction,
packing, or bounce-count modeling changes.
"""
    (notes / "aeff_debug_notes.md").write_text(note, encoding="utf-8")

    ring_rows = [r for r in out_rows if r["ring_id"] != "TOTAL"]
    labels = [f"R{r['ring_id']}" for r in ring_rows]
    aeff = [float(r["Aeff_cm2"]) for r in ring_rows]
    open_area = [float(r["open_geometric_area_cm2"]) for r in ring_rows]
    bounce = [float(r["mean_bounce_count"]) for r in ring_rows]
    fig, ax1 = plt.subplots(figsize=(7.2, 4.8), constrained_layout=True)
    x = np.arange(len(labels))
    ax1.bar(x - 0.18, open_area, width=0.36, label="open geometric", color="#94a3b8")
    ax1.bar(x + 0.18, aeff, width=0.36, label="Aeff", color="#2563eb")
    ax1.set_xticks(x, labels)
    ax1.set_ylabel("area [cm2]")
    ax2 = ax1.twinx()
    ax2.plot(x, bounce, marker="o", color="#f59e0b", label="mean bounce")
    ax2.set_ylabel("mean bounce count")
    ax1.set_title("Aeff by ring and bounce count, no direct scaling")
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
    fig.savefig(figures / "aeff_by_ring_and_bounce.png", dpi=180)
    plt.close(fig)

    total = out_rows[-1]
    return {
        "status": "PASS_AEFF_TRANSPORT_DEBUG",
        "Aeff_cm2": total["Aeff_cm2"],
        "open_geometric_area_cm2": total["open_geometric_area_cm2"],
        "Aeff_over_open_geometric": total["Aeff_over_open_geometric"],
        "mean_bounce_count": total["mean_bounce_count"],
        "used_for_tuning": False,
    }


def main() -> int:
    args = parse_args()
    outdir = Path(args.outdir)
    if not outdir.is_absolute():
        outdir = ROOT / outdir
    summary = build_debug(Path(args.config), Path(args.samples), outdir)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
