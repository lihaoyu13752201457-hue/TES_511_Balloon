from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/opticsim_mpl")
import matplotlib.pyplot as plt


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot a phase-space focal spot CSV.")
    parser.add_argument("csv_path")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    xs = []
    ys = []
    with csv_path.open(newline="") as f:
        for row in csv.DictReader(f):
            xs.append(float(row["x_mm"]) / 10.0)
            ys.append(float(row["y_mm"]) / 10.0)

    fig, ax = plt.subplots(figsize=(5.8, 5.2), dpi=140)
    ax.scatter(xs, ys, s=2.0, alpha=0.35, linewidths=0)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x [cm]")
    ax.set_ylabel("y [cm]")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    out = Path(args.out) if args.out else csv_path.with_suffix(".png")
    fig.savefig(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
