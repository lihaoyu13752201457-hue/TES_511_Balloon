from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("MPLCONFIGDIR", "/tmp/opticsim_mpl")
import matplotlib.pyplot as plt

from external_baseline.channel_raytrace_py.parratt_reflectivity import (  # noqa: E402
    MultilayerSpec,
    compute_manual_parratt_rows,
)


def read_table(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def main() -> int:
    parser = argparse.ArgumentParser(description="Cross-check W/Si reflectivity table with an independent Parratt recursion.")
    parser.add_argument("--reference", default="data/reflectivity/WSi_511keV_parratt_grid.csv")
    parser.add_argument("--out", default="runs/wsi_parratt_crosscheck")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = read_table(Path(args.reference))
    theta = [float(row["theta_rad"]) for row in rows]
    ref_R = [float(row["R"]) for row in rows]
    ref_A = [float(row["A"]) for row in rows]
    ref_T = [float(row["T"]) for row in rows]
    energy = float(rows[0]["E_keV"]) if rows else 511.0
    manual = compute_manual_parratt_rows(MultilayerSpec(), E_keV=energy, theta_rad=theta)

    comparison_rows = []
    for row, m, r_ref, a_ref, t_ref in zip(rows, manual, ref_R, ref_A, ref_T):
        comparison_rows.append(
            {
                "theta_rad": row["theta_rad"],
                "R_reference": r_ref,
                "R_manual": m.R,
                "delta_R": m.R - r_ref,
                "A_reference": a_ref,
                "A_manual": m.A,
                "T_reference": t_ref,
                "T_manual": m.T,
            }
        )
    with (out / "parratt_crosscheck.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(comparison_rows[0].keys()))
        writer.writeheader()
        writer.writerows(comparison_rows)

    abs_delta = [abs(row["delta_R"]) for row in comparison_rows]
    summary = {
        "reference_table": args.reference,
        "n_rows": len(comparison_rows),
        "energy_keV": energy,
        "max_abs_delta_R": max(abs_delta) if abs_delta else 0.0,
        "mean_abs_delta_R": sum(abs_delta) / len(abs_delta) if abs_delta else 0.0,
        "manual_source": manual[0].source if manual else "",
        "reference_source": rows[0].get("source", "") if rows else "",
        "status": "PASS" if abs_delta and max(abs_delta) < 1.0e-10 else "CHECK",
    }
    with (out / "summary.json").open("w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
        f.write("\n")

    fig, axes = plt.subplots(2, 1, figsize=(6.8, 7.0), dpi=140, sharex=True)
    axes[0].loglog(theta, ref_R, label="xraydb multilayer", color="#2563eb", linewidth=2.0)
    axes[0].loglog(theta, [row.R for row in manual], "--", label="manual Parratt", color="#dc2626", linewidth=1.5)
    axes[0].set_ylim(1.0e-8, 1.2)
    axes[0].set_ylabel("R")
    axes[0].set_title("W/Si 511 keV reflectivity cross-check")
    axes[0].grid(True, alpha=0.25)
    axes[0].legend()
    axes[1].semilogx(theta, abs_delta, color="#7c3aed", linewidth=1.5)
    axes[1].set_xlabel("grazing angle [rad]")
    axes[1].set_ylabel("|delta R|")
    axes[1].grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(out / "parratt_crosscheck.png")
    plt.close(fig)

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
