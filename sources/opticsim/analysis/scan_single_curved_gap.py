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


def label_float(value: float) -> str:
    return f"{value:.6g}".replace(".", "p").replace("-", "m")


def run_case(
    *,
    out_dir: Path,
    n: int,
    bend_angle_rad: float,
    half_gap_mm: float,
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
        "--half-gap-mm",
        f"{half_gap_mm:.12g}",
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
        "half_gap_mm",
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
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), dpi=140)
    colors = {46.0 / 12000.0: "#dc2626", 3.0e-4: "#2563eb"}

    ax = axes[0]
    for bend in sorted({float(row["bend_angle_rad"]) for row in rows}):
        constant = sorted(
            (row for row in rows if row["mode"] == "constant" and abs(float(row["bend_angle_rad"]) - bend) < 1e-12),
            key=lambda row: row["half_gap_mm"],
        )
        ax.plot(
            [row["half_gap_mm"] for row in constant],
            [row["mean_grazing_angle_rad"] for row in constant],
            marker="o",
            color=colors.get(bend, "#0f766e"),
            label=f"bend={bend:.3g}",
        )
    ax.axhline(1.5e-4, color="#111827", linestyle="--", linewidth=1.1, label="~1.5e-4 rad")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.invert_xaxis()
    ax.set_xlabel("half gap [mm]")
    ax.set_ylabel("mean grazing angle [rad]")
    ax.set_title("constant R=1 geometry diagnostic")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7)

    ax = axes[1]
    for bend in sorted({float(row["bend_angle_rad"]) for row in rows}):
        table = sorted(
            (row for row in rows if row["mode"] == "table" and abs(float(row["bend_angle_rad"]) - bend) < 1e-12),
            key=lambda row: row["half_gap_mm"],
        )
        ax.plot(
            [row["half_gap_mm"] for row in table],
            [row["survival_fraction"] for row in table],
            marker="o",
            color=colors.get(bend, "#0f766e"),
            label=f"bend={bend:.3g}",
        )
    ax.set_xscale("log")
    ax.invert_xaxis()
    ax.set_xlabel("half gap [mm]")
    ax.set_ylabel("W/Si table survival fraction")
    ax.set_ylim(-0.03, 1.03)
    ax.set_title("table-driven survival")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7)

    fig.tight_layout()
    fig.savefig(out_dir / "single_curved_gap_scan.png")
    plt.close(fig)


def build_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    bend_12m = 46.0 / 12000.0
    low_bend = 3.0e-4
    table_rows = [row for row in rows if row["mode"] == "table"]
    constant_rows = [row for row in rows if row["mode"] == "constant"]
    table_12m = [row for row in table_rows if abs(float(row["bend_angle_rad"]) - bend_12m) < 1e-12]
    table_low = [row for row in table_rows if abs(float(row["bend_angle_rad"]) - low_bend) < 1e-12]
    constant_12m = [row for row in constant_rows if abs(float(row["bend_angle_rad"]) - bend_12m) < 1e-12]
    constant_low = [row for row in constant_rows if abs(float(row["bend_angle_rad"]) - low_bend) < 1e-12]

    best_table_12m = max(table_12m, key=lambda row: row["survival_fraction"])
    best_table_low = max(table_low, key=lambda row: row["survival_fraction"])
    min_theta_12m = min(constant_12m, key=lambda row: row["mean_grazing_angle_rad"])
    min_theta_low = min(constant_low, key=lambda row: row["mean_grazing_angle_rad"])

    return {
        "system": "geant4_channel_single_curved_gap_scan",
        "warning": "Diagnostic gap scan only; it tests whether shrinking the channel gap rescues the simple 12 m curved-wall interpretation.",
        "n_rows": len(rows),
        "target_grazing_rad": 1.5e-4,
        "bend_angle_46mm_to_12m_rad": bend_12m,
        "low_survival_bend_angle_rad": low_bend,
        "best_table_survival_12m_bend": {
            "half_gap_mm": best_table_12m["half_gap_mm"],
            "survival_fraction": best_table_12m["survival_fraction"],
            "mean_grazing_angle_rad": best_table_12m["mean_grazing_angle_rad"],
            "n_boundary": best_table_12m["n_boundary"],
            "n_reflect": best_table_12m["n_reflect"],
            "n_absorb": best_table_12m["n_absorb"],
            "n_leak": best_table_12m["n_leak"],
        },
        "best_table_survival_low_bend": {
            "half_gap_mm": best_table_low["half_gap_mm"],
            "survival_fraction": best_table_low["survival_fraction"],
            "mean_grazing_angle_rad": best_table_low["mean_grazing_angle_rad"],
            "n_boundary": best_table_low["n_boundary"],
            "n_reflect": best_table_low["n_reflect"],
            "n_absorb": best_table_low["n_absorb"],
            "n_leak": best_table_low["n_leak"],
        },
        "min_constant_theta_12m_bend": {
            "half_gap_mm": min_theta_12m["half_gap_mm"],
            "mean_grazing_angle_rad": min_theta_12m["mean_grazing_angle_rad"],
            "max_boundary_per_event": min_theta_12m["max_boundary_per_event"],
            "spot_d90_cm": min_theta_12m["spot_d90_cm"],
        },
        "min_constant_theta_low_bend": {
            "half_gap_mm": min_theta_low["half_gap_mm"],
            "mean_grazing_angle_rad": min_theta_low["mean_grazing_angle_rad"],
            "max_boundary_per_event": min_theta_low["max_boundary_per_event"],
            "spot_d90_cm": min_theta_low["spot_d90_cm"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan half-gap sensitivity for the Geant4 single curved channel.")
    parser.add_argument("--out", default="runs/geant4_channel_single_curved_gap_scan")
    parser.add_argument("--seed", type=int, default=20260517)
    parser.add_argument("--n-constant", type=int, default=20)
    parser.add_argument("--n-table", type=int, default=200)
    parser.add_argument("--segments", type=int, default=128)
    args = parser.parse_args()

    if not EXE.exists():
        raise SystemExit(f"missing executable: {EXE}")

    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    half_gaps = [1.0e-3, 5.0e-4, 2.5e-4, 1.0e-4, 5.0e-5]
    bend_angles = [3.0e-4, 46.0 / 12000.0]
    rows: list[dict[str, Any]] = []
    for bend in bend_angles:
        for half_gap in half_gaps:
            tag = f"b{label_float(bend)}_g{label_float(half_gap)}_seg{args.segments}"
            rows.append(
                run_case(
                    out_dir=out / f"constant_{tag}",
                    n=args.n_constant,
                    bend_angle_rad=bend,
                    half_gap_mm=half_gap,
                    segments=args.segments,
                    table_mode=False,
                    seed=args.seed,
                )
            )
            rows.append(
                run_case(
                    out_dir=out / f"table_{tag}",
                    n=args.n_table,
                    bend_angle_rad=bend,
                    half_gap_mm=half_gap,
                    segments=args.segments,
                    table_mode=True,
                    seed=args.seed,
                )
            )

    write_csv(rows, out / "single_curved_gap_scan.csv")
    summary = build_summary(rows)
    with (out / "summary.json").open("w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
        f.write("\n")
    plot(rows, out)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
