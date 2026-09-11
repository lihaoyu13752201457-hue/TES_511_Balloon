#!/usr/bin/env python3
"""Build the final near-field angular-separation and chord-feasibility figure.

This consumes only the small, reviewed CSV produced by the delayed audit.  It
does not read raw SIM files and does not perform transport.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
ANGULAR = ROOT / "agents/delayed/tes511_nearfield_angular_separation.csv"
OUT_PNG = ROOT / "figures/nearfield_angle_and_chord_falsifier.png"
OUT_SVG = ROOT / "figures/nearfield_angle_and_chord_falsifier.svg"


def load_cones() -> tuple[np.ndarray, np.ndarray]:
    angles: list[float] = []
    fractions: list[float] = []
    with ANGULAR.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["section"] != "delayed_axis_cone":
                continue
            label = row["selection"]
            if "<=" not in label:
                continue
            angle = float(label.split("<=", 1)[1].split("deg", 1)[0].strip())
            angles.append(angle)
            fractions.append(100.0 * float(row["fraction_of_section_denominator"]))
    order = np.argsort(angles)
    return np.asarray(angles)[order], np.asarray(fractions)[order]


def main() -> None:
    angles, fractions = load_cones()
    plt.rcParams.update({
        "font.size": 10.5,
        "axes.titlesize": 12,
        "axes.labelsize": 10.5,
        "figure.dpi": 150,
    })
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.8, 5.5))
    fig.subplots_adjust(left=0.07, right=0.98, bottom=0.18, top=0.82, wspace=0.25)

    ax1.step(angles, fractions, where="post", color="#356a9a", linewidth=2.4)
    ax1.scatter(angles, fractions, color="#356a9a", s=28, zorder=3)
    ax1.axvline(0.459802, color="#d47a1f", linestyle="--", linewidth=1.8,
                label="focused signal maximum: 0.460 deg")
    ax1.axhline(0.314835, color="#7b4f9d", linestyle=":", linewidth=1.8,
                label="ideal same-face + footprint leak: 0.315%")
    ax1.set_xlim(0, 90)
    ax1.set_ylim(-0.5, 38)
    ax1.set_xlabel("half-angle from +x signal axis (deg)")
    ax1.set_ylabel("traceable delayed mission weight inside cone (%)")
    ax1.set_title("Signal and delayed 511 angular separation")
    ax1.grid(axis="y", color="#d9dde2", linewidth=0.7)
    ax1.legend(loc="upper left", frameon=False, fontsize=9)
    ax1.annotate("0 events through 10 deg",
                 xy=(10, 0), xytext=(20, 7),
                 arrowprops={"arrowstyle": "->", "color": "#2f3337"},
                 color="#2f3337")

    labels = ["square-corner\nradial limit", "face-center\nradial limit", "x+ end\nlimit"]
    available = [1.3837, 2.1500, 0.4100]
    y = np.arange(len(labels))
    ax2.barh(y, available, color="#6a8fb7", edgecolor="#294b69", height=0.58)
    ax2.axvline(2.30806, color="#d47a1f", linestyle="--", linewidth=2,
                label="required with BG-TAU5: 2.308 cm")
    ax2.axvline(3.14009, color="#9f2f2f", linestyle="-.", linewidth=2,
                label="required with +4 cm BGO: 3.140 cm")
    for yi, value in zip(y, available):
        ax2.text(value + 0.05, yi, f"{value:.3f} cm", va="center", color="#2f3337")
    ax2.set_yticks(y, labels)
    ax2.invert_yaxis()
    ax2.set_xlim(0, 3.45)
    ax2.set_xlabel("maximum continuous near-field Cu chord (cm)")
    ax2.set_title("Real bore clearance fails the attenuation gate")
    ax2.grid(axis="x", color="#d9dde2", linewidth=0.7)
    ax2.legend(loc="lower right", frameon=False, fontsize=9)

    fig.suptitle("S3d-O8 near-field passive-angle LOOP: mechanism separates, geometry fails",
                 fontsize=15)
    fig.text(0.5, 0.035,
             "Direction fractions use the 418/420 traceable delayed denominator; chord lines are scale gates, not transport predictions.",
             ha="center", fontsize=9.5, color="#555b61")
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, bbox_inches="tight")
    fig.savefig(OUT_SVG, bbox_inches="tight")


if __name__ == "__main__":
    main()
