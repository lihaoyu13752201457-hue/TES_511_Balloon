#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Summarize opticsim Laue off-axis focal-plane scan runs."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def read_phase(path: Path) -> tuple[np.ndarray, np.ndarray]:
    xs: list[float] = []
    ys: list[float] = []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            xs.append(float(row["x_mm"]))
            ys.append(float(row["y_mm"]))
    return np.asarray(xs), np.asarray(ys)


def parse_case(text: str) -> tuple[float, float, Path]:
    x_s, y_s, path_s = text.split(":", 2)
    return float(x_s), float(y_s), Path(path_s)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", action="append", required=True, help="x_arcmin:y_arcmin:/path/to/run_dir")
    ap.add_argument("--outdir", type=Path, required=True)
    ap.add_argument("--focal-mm", type=float, default=8300.0)
    args = ap.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    rows = []
    for case in args.case:
        offx, offy, run_dir = parse_case(case)
        summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
        xs, ys = read_phase(run_dir / "phase_space.csv")
        expected_x = args.focal_mm * math.tan(offx / 60.0 * math.pi / 180.0)
        expected_y = args.focal_mm * math.tan(offy / 60.0 * math.pi / 180.0)
        rows.append({
            "offaxis_x_arcmin": offx,
            "offaxis_y_arcmin": offy,
            "run_dir": str(run_dir),
            "n_primaries": int(summary["n_primaries"]),
            "n_diffracted": int(summary["n_diffracted"]),
            "diffraction_fraction": float(summary["diffraction_fraction"]),
            "spot_d90_cm": float(summary["spot_d90_cm"]),
            "centroid_x_mm": float(np.mean(xs)) if len(xs) else float("nan"),
            "centroid_y_mm": float(np.mean(ys)) if len(ys) else float("nan"),
            "expected_x_mm": expected_x,
            "expected_y_mm": expected_y,
            "centroid_dx_mm": float(np.mean(xs) - expected_x) if len(xs) else float("nan"),
            "centroid_dy_mm": float(np.mean(ys) - expected_y) if len(ys) else float("nan"),
        })

    fields = list(rows[0].keys())
    with (args.outdir / "laue_offaxis_scan_summary.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    fig, ax = plt.subplots(figsize=(5.2, 5.0))
    ax.scatter([r["expected_x_mm"] for r in rows], [r["expected_y_mm"] for r in rows], marker="x", s=80, label="expected f tan(theta)")
    ax.scatter([r["centroid_x_mm"] for r in rows], [r["centroid_y_mm"] for r in rows], marker="o", s=45, label="simulated centroid")
    for r in rows:
        ax.plot([r["expected_x_mm"], r["centroid_x_mm"]], [r["expected_y_mm"], r["centroid_y_mm"]], color="#6b7280", lw=0.8)
    ax.set_xlabel("focal-plane x (mm)")
    ax.set_ylabel("focal-plane y (mm)")
    ax.set_title("Laue off-axis focal-map smoke")
    ax.grid(True, alpha=0.25)
    ax.axis("equal")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(args.outdir / "laue_offaxis_centroids.png", dpi=220)
    plt.close(fig)

    max_abs_error = max(
        max(abs(float(r["centroid_dx_mm"])), abs(float(r["centroid_dy_mm"])))
        for r in rows
    )
    summary = {
        "status": "PASS" if max_abs_error < 0.25 else "CHECK",
        "n_cases": len(rows),
        "focal_mm": args.focal_mm,
        "max_abs_centroid_error_mm": max_abs_error,
        "csv": str(args.outdir / "laue_offaxis_scan_summary.csv"),
        "figure": str(args.outdir / "laue_offaxis_centroids.png"),
        "claim_level": "OFFAXIS_FOCAL_MAP_SMOKE_FOR_DIFFUSE_SCAFFOLD",
    }
    (args.outdir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
