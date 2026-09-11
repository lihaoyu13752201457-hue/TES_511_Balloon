from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/opticsim_mpl")

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
EXE = Path("/tmp/opticsim-build/channel_single_curved_demo")
REFLECTIVITY_TABLE = "data/reflectivity/WSi_511keV_parratt_grid.csv"


def run_command(cmd: list[str]) -> str:
    completed = subprocess.run(
        cmd,
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return completed.stdout


def load_json(path: Path) -> dict[str, Any]:
    with path.open() as f:
        return json.load(f)


def run_case(
    *,
    out_dir: Path,
    n: int,
    bend_angle_rad: float,
    segments: int,
    table_mode: bool,
    seed: int,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(EXE),
        "--n",
        str(n),
        "--segments",
        str(segments),
        "--bend-angle-rad",
        f"{bend_angle_rad:.12g}",
        "--out",
        str(out_dir),
        "--seed",
        str(seed),
    ]
    if table_mode:
        cmd.extend(["--reflectivity-table", REFLECTIVITY_TABLE])
    else:
        cmd.extend(["--R", "1", "--A", "0", "--T", "0"])
    stdout = run_command(cmd)
    summary = load_json(out_dir / "summary.json")
    summary["stdout_tail"] = stdout.strip().splitlines()[-1] if stdout.strip() else ""
    summary["mode"] = "table" if table_mode else "constant"
    return summary


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fields = [
        "mode",
        "bend_angle_rad",
        "segments",
        "n_primaries",
        "n_boundary",
        "n_reflect",
        "n_absorb",
        "n_leak",
        "n_survived",
        "survival_fraction",
        "mean_grazing_angle_rad",
        "max_boundary_per_event",
        "spot_d90_cm",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fields})


def plot(rows: list[dict[str, Any]], out_dir: Path) -> None:
    table = [row for row in rows if row["mode"] == "table"]
    const = [row for row in rows if row["mode"] == "constant"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), dpi=140)

    ax = axes[0]
    for seg in sorted({row["segments"] for row in const}):
      seg_rows = sorted((row for row in const if row["segments"] == seg), key=lambda r: r["bend_angle_rad"])
      ax.plot(
          [row["bend_angle_rad"] for row in seg_rows],
          [row["mean_grazing_angle_rad"] for row in seg_rows],
          marker="o",
          label=f"R=1 seg={seg}",
      )
    ax.axhline(1.5e-4, color="#dc2626", linestyle="--", linewidth=1.2, label="~1.5e-4 rad")
    ax.axvline(46.0 / 12000.0, color="#7c3aed", linestyle=":", linewidth=1.2, label="46mm/12m")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("bend angle [rad]")
    ax.set_ylabel("mean grazing angle [rad]")
    ax.set_title("curved-channel grazing diagnostic")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7)

    ax = axes[1]
    table_rows = sorted(table, key=lambda r: r["bend_angle_rad"])
    ax.plot(
        [row["bend_angle_rad"] for row in table_rows],
        [row["survival_fraction"] for row in table_rows],
        marker="o",
        color="#2563eb",
    )
    ax.axvline(46.0 / 12000.0, color="#7c3aed", linestyle=":", linewidth=1.2, label="46mm/12m")
    ax.set_xscale("log")
    ax.set_xlabel("bend angle [rad]")
    ax.set_ylabel("W/Si table survival fraction")
    ax.set_ylim(-0.03, 1.03)
    ax.set_title("table-driven survival")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7)

    fig.tight_layout()
    fig.savefig(out_dir / "single_curved_scan.png")
    plt.close(fig)


def build_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    table = [row for row in rows if row["mode"] == "table"]
    table_with_boundary = [row for row in table if row["n_boundary"] > 0]
    const = [row for row in rows if row["mode"] == "constant" and row["segments"] == 64]
    closest_theta = min(const, key=lambda row: abs(row["mean_grazing_angle_rad"] - 1.5e-4))
    bend_12m = 46.0 / 12000.0
    closest_12m = min(const, key=lambda row: abs(row["bend_angle_rad"] - bend_12m))
    best_table = max(table, key=lambda row: row["survival_fraction"])
    best_table_with_boundary = max(table_with_boundary, key=lambda row: row["survival_fraction"])
    return {
        "system": "geant4_channel_single_curved_scan",
        "warning": "Diagnostic scan only; it exposes geometry/angle tension and is not a final focusing channel design.",
        "n_rows": len(rows),
        "target_grazing_rad": 1.5e-4,
        "bend_angle_46mm_to_12m_rad": bend_12m,
        "closest_to_target_theta": {
            "bend_angle_rad": closest_theta["bend_angle_rad"],
            "segments": closest_theta["segments"],
            "mean_grazing_angle_rad": closest_theta["mean_grazing_angle_rad"],
            "spot_d90_cm": closest_theta["spot_d90_cm"],
        },
        "closest_to_12m_bend": {
            "bend_angle_rad": closest_12m["bend_angle_rad"],
            "segments": closest_12m["segments"],
            "mean_grazing_angle_rad": closest_12m["mean_grazing_angle_rad"],
            "spot_d90_cm": closest_12m["spot_d90_cm"],
        },
        "best_table_survival": {
            "bend_angle_rad": best_table["bend_angle_rad"],
            "survival_fraction": best_table["survival_fraction"],
            "mean_grazing_angle_rad": best_table["mean_grazing_angle_rad"],
            "n_boundary": best_table["n_boundary"],
        },
        "best_table_survival_with_boundary": {
            "bend_angle_rad": best_table_with_boundary["bend_angle_rad"],
            "survival_fraction": best_table_with_boundary["survival_fraction"],
            "mean_grazing_angle_rad": best_table_with_boundary["mean_grazing_angle_rad"],
            "n_boundary": best_table_with_boundary["n_boundary"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan single-curved channel bend angle and segment diagnostics.")
    parser.add_argument("--out", default="runs/geant4_channel_single_curved_scan")
    parser.add_argument("--seed", type=int, default=20260517)
    parser.add_argument("--n-constant", type=int, default=20)
    parser.add_argument("--n-table", type=int, default=200)
    args = parser.parse_args()

    if not EXE.exists():
        raise SystemExit(f"missing executable: {EXE}")

    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    bend_angles = [1.0e-4, 1.5e-4, 2.0e-4, 3.0e-4, 5.0e-4, 1.0e-3, 2.0e-3, 46.0 / 12000.0]
    rows: list[dict[str, Any]] = []
    for bend in bend_angles:
        for segments in [32, 64, 128]:
            rows.append(
                run_case(
                    out_dir=out / f"constant_b{bend:.6g}_seg{segments}",
                    n=args.n_constant,
                    bend_angle_rad=bend,
                    segments=segments,
                    table_mode=False,
                    seed=args.seed,
                )
            )
        rows.append(
            run_case(
                out_dir=out / f"table_b{bend:.6g}_seg64",
                n=args.n_table,
                bend_angle_rad=bend,
                segments=64,
                table_mode=True,
                seed=args.seed,
            )
        )

    write_csv(rows, out / "single_curved_scan.csv")
    summary = build_summary(rows)
    with (out / "summary.json").open("w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
        f.write("\n")
    plot(rows, out)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
