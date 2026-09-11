#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from laue511.bragg import bragg_angle_rad
from laue511.rings import find_ring, load_ring_config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", default="/tmp/opticsim-bfull-build/laue_multiring_bfull_demo")
    parser.add_argument("--n", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20260529)
    parser.add_argument("--ring-id", type=int, default=2)
    parser.add_argument("--tile-id", type=int, default=0)
    parser.add_argument("--offsets-arcsec", default="-90,-60,-30,-18,-12,-6,0,6,12,18,30,60,90")
    parser.add_argument("--out-dir", default=str(ROOT / "reports/bfull_single_tile_xop_scan"))
    parser.add_argument("--ring-config", default=str(ROOT / "data/laue/ge111_480_550keV_multiring_darwin_config.csv"))
    parser.add_argument("--xop-curve", default=str(ROOT / "benchmarks/xop_crystal/ge111_511keV_rocking_curve.csv"))
    parser.add_argument("--keep-runs", action="store_true")
    args = parser.parse_args()

    exe = Path(args.exe)
    if not exe.exists():
        raise FileNotFoundError(f"B-FULL executable not found: {exe}")
    rings = load_ring_config(args.ring_config)
    ring = find_ring(rings, args.ring_id)
    offsets_arcsec = [float(x) for x in args.offsets_arcsec.split(",") if x.strip()]
    xop_curve = _load_xop_curve(Path(args.xop_curve))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    run_root_obj = tempfile.TemporaryDirectory(prefix="laue_bfull_single_tile_xop_")
    run_root = Path(run_root_obj.name)
    rows: list[dict[str, object]] = []
    try:
        for offset_arcsec in offsets_arcsec:
            offset_arcmin = offset_arcsec / 60.0
            run_dir = run_root / _offset_name(offset_arcsec)
            cmd = [
                str(exe),
                "--n",
                str(args.n),
                "--seed",
                str(args.seed),
                "--only-ring-id",
                str(args.ring_id),
                "--only-tile-id",
                str(args.tile_id),
                "--offaxis-x-arcmin",
                f"{offset_arcmin:.12g}",
                "--rocking-curve-csv",
                str(Path(args.xop_curve).resolve()),
                "--out",
                str(run_dir),
            ]
            completed = subprocess.run(cmd, cwd="/home/ubuntu/opticsim", text=True, capture_output=True, check=False)
            if completed.returncode != 0:
                raise RuntimeError(
                    f"B-FULL single-tile run failed for offset {offset_arcsec:g} arcsec\n"
                    f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
                )
            summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
            history = _history_stats(run_dir / "optics_history.csv", xop_curve)
            transmitted_rows = _count_csv_rows(run_dir / "transmitted_space.csv")
            delta_theta_rad = _delta_theta_for_tile(ring, args.tile_id, offset_arcsec)
            xop_reflectivity = _interp_curve(xop_curve, delta_theta_rad)
            rows.append(
                {
                    "offset_x_arcsec": offset_arcsec,
                    "delta_theta_rad": delta_theta_rad,
                    "delta_theta_urad": delta_theta_rad * 1.0e6,
                    "xop_reflectivity": xop_reflectivity,
                    "n_primaries": int(summary["n_primaries"]),
                    "registered_in_geant4_em_category": bool(summary.get("registered_in_geant4_em_category")),
                    "geant4_process_base_class": str(summary.get("geant4_process_base_class", "")),
                    "transmitted_space_rows": transmitted_rows,
                    "transmitted_space_rows_match_summary": transmitted_rows == int(summary.get("transmitted_space_rows", -1)),
                    "n_laue_interactions": int(summary["n_laue_interactions"]),
                    "observed_laue_interaction_fraction": float(summary["laue_interaction_fraction"]),
                    "mean_recorded_p_reflect": history["mean_p_reflect"],
                    "mean_recorded_delta_theta_urad": history["mean_delta_theta_urad"],
                    "max_recorded_p_reflect_minus_xop": history["max_abs_p_reflect_delta"],
                    "laue_diffracted_focal_crossings": int(summary["laue_diffracted_focal_crossings"]),
                    "focal_crossing_spot_d90_cm": float(summary["focal_crossing_spot_d90_cm"]),
                    "run_stdout_tail": completed.stdout.strip().splitlines()[-1] if completed.stdout.strip() else "",
                }
            )
        _write_csv(out_dir / "scan.csv", rows)
        summary = _build_summary(args, exe, rows, run_root if args.keep_runs else None)
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _write_markdown(out_dir / "summary.md", summary, rows)
        if args.keep_runs:
            kept = out_dir / "raw_runs"
            if kept.exists():
                shutil.rmtree(kept)
            shutil.copytree(run_root, kept)
            summary["raw_runs"] = str(kept)
            (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"out_dir": str(out_dir), "n_offsets": len(rows), "ok": summary["ok"]}, indent=2, sort_keys=True))
    finally:
        if not args.keep_runs:
            run_root_obj.cleanup()
    return 0


def _offset_name(offset_arcsec: float) -> str:
    sign = "p" if offset_arcsec >= 0 else "m"
    return f"offaxis_{sign}{abs(offset_arcsec):g}arcsec".replace(".", "p")


def _count_csv_rows(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def _load_xop_curve(path: Path) -> list[tuple[float, float]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [(float(row["delta_theta_rad"]), float(row["reflectivity"])) for row in csv.DictReader(handle)]
    return sorted(rows)


def _history_stats(path: Path, xop_curve: list[tuple[float, float]]) -> dict[str, float | int | None]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return {"n_rows": 0, "mean_p_reflect": None, "mean_delta_theta_urad": None, "max_abs_p_reflect_delta": None}
    deltas = []
    for row in rows:
        recorded_delta = float(row["delta_theta_model_rad"])
        recorded_p = float(row["p_reflect"])
        deltas.append(abs(recorded_p - _interp_curve(xop_curve, recorded_delta)))
    return {
        "n_rows": len(rows),
        "mean_p_reflect": sum(float(row["p_reflect"]) for row in rows) / len(rows),
        "mean_delta_theta_urad": sum(float(row["delta_theta_model_rad"]) for row in rows) / len(rows) * 1.0e6,
        "max_abs_p_reflect_delta": max(deltas),
    }


def _delta_theta_for_tile(ring: object, tile_id: int, offset_x_arcsec: float) -> float:
    phi = 2.0 * math.pi * tile_id / ring.n_tiles
    center = (ring.radius_mm * math.cos(phi), ring.radius_mm * math.sin(phi), 0.0)
    nominal_in = (0.0, 0.0, 1.0)
    nominal_out = _unit((-center[0], -center[1], 8300.0 - center[2]))
    plane_normal = _unit(
        (
            nominal_in[0] - nominal_out[0],
            nominal_in[1] - nominal_out[1],
            nominal_in[2] - nominal_out[2],
        )
    )
    off = math.radians(offset_x_arcsec / 3600.0)
    incoming = _unit((math.tan(off), 0.0, 1.0))
    theta_local = math.asin(abs(_dot(incoming, plane_normal)))
    return theta_local - bragg_angle_rad(ring.design_energy_keV, ring.d_spacing_A)


def _interp_curve(curve: list[tuple[float, float]], x: float) -> float:
    if x <= curve[0][0]:
        return curve[0][1]
    if x >= curve[-1][0]:
        return curve[-1][1]
    lo = 0
    hi = len(curve) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if curve[mid][0] <= x:
            lo = mid
        else:
            hi = mid
    x0, y0 = curve[lo]
    x1, y1 = curve[hi]
    if x1 == x0:
        return y0
    f = (x - x0) / (x1 - x0)
    return y0 + f * (y1 - y0)


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _unit(v: tuple[float, float, float]) -> tuple[float, float, float]:
    mag = math.sqrt(_dot(v, v))
    return (v[0] / mag, v[1] / mag, v[2] / mag)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _build_summary(
    args: argparse.Namespace,
    exe: Path,
    rows: list[dict[str, object]],
    raw_runs: Path | None,
) -> dict[str, object]:
    peak = max(rows, key=lambda row: float(row["xop_reflectivity"]))
    far = min(rows, key=lambda row: abs(float(row["offset_x_arcsec"])))
    observed_peak = max(float(row["observed_laue_interaction_fraction"]) for row in rows)
    observed_min = min(float(row["observed_laue_interaction_fraction"]) for row in rows)
    recorded_deltas = [row["max_recorded_p_reflect_minus_xop"] for row in rows if row["max_recorded_p_reflect_minus_xop"] is not None]
    max_recorded_delta = (
        max(float(delta) for delta in recorded_deltas) if recorded_deltas else None
    )
    all_em_category = all(bool(row["registered_in_geant4_em_category"]) for row in rows)
    all_g4vemprocess = all(row["geant4_process_base_class"] == "G4VEmProcess" for row in rows)
    all_transmitted_rows_match = all(bool(row["transmitted_space_rows_match_summary"]) for row in rows)
    return {
        "ok": bool(recorded_deltas)
        and max_recorded_delta is not None
        and max_recorded_delta <= 5.0e-4
        and all_em_category
        and all_g4vemprocess
        and all_transmitted_rows_match
        and observed_peak > observed_min,
        "bfull_executable": str(exe),
        "n_per_offset": args.n,
        "seed": args.seed,
        "ring_id": args.ring_id,
        "tile_id": args.tile_id,
        "xop_peak_reflectivity_in_scan": float(peak["xop_reflectivity"]),
        "nearest_zero_offset_arcsec": float(far["offset_x_arcsec"]),
        "observed_peak_interaction_fraction": observed_peak,
        "observed_min_interaction_fraction": observed_min,
        "observed_peak_to_min_ratio": observed_peak / observed_min if observed_min else None,
        "max_recorded_p_reflect_minus_xop": max_recorded_delta,
        "all_registered_in_geant4_em_category": all_em_category,
        "all_process_base_g4vemprocess": all_g4vemprocess,
        "all_transmitted_space_rows_match_summary": all_transmitted_rows_match,
        "raw_runs": str(raw_runs) if raw_runs else "temporary_deleted",
        "note": (
            "This runs one B-FULL tile with the external XOP/CRYSTAL rocking-curve CSV as the Laue finite-MFP backend. "
            "Recorded p_reflect is checked against the interpolated XOP reflectivity at each recorded event delta_theta_model_rad. "
            "Observed interaction fractions are lower than XOP reflectivity because standard Geant4 EM processes compete with the Laue process."
        ),
    }


def _write_markdown(path: Path, summary: dict[str, object], rows: list[dict[str, object]]) -> None:
    lines = [
        "# B-FULL Single-Tile XOP Scan",
        "",
        f"- ok: `{summary['ok']}`",
        f"- executable: `{summary['bfull_executable']}`",
        f"- ring/tile: `{summary['ring_id']}/{summary['tile_id']}`",
        f"- events per offset: `{summary['n_per_offset']}`",
        f"- all runs registered in Geant4 EM category: `{summary['all_registered_in_geant4_em_category']}`",
        f"- all runs use G4VEmProcess base: `{summary['all_process_base_g4vemprocess']}`",
        f"- transmitted_space rows match summary: `{summary['all_transmitted_space_rows_match_summary']}`",
        f"- max |recorded p_reflect - XOP|: `{summary['max_recorded_p_reflect_minus_xop']}`",
        f"- observed peak/min interaction ratio: `{summary['observed_peak_to_min_ratio']}`",
        "",
        "| offset arcsec | delta urad | XOP R | observed frac | recorded p_reflect | max p delta | interactions |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        recorded = row["mean_recorded_p_reflect"]
        lines.append(
            "| {offset_x_arcsec:g} | {delta_theta_urad:.6g} | {xop_reflectivity:.6g} | "
            "{observed_laue_interaction_fraction:.6g} | {recorded} | {max_delta} | {n_laue_interactions} |".format(
                recorded="" if recorded is None else f"{float(recorded):.6g}",
                max_delta=""
                if row["max_recorded_p_reflect_minus_xop"] is None
                else f"{float(row['max_recorded_p_reflect_minus_xop']):.6g}",
                **row,
            )
        )
    lines.extend(["", str(summary["note"]), ""])
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
