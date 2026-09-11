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
from laue511.probabilities import darwin_q_ge111_cm_inv, mosaic_weight_rad_inv
from laue511.rings import RingSpec, load_ring_config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", default="/tmp/opticsim-bfull-build/laue_multiring_bfull_demo")
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260529)
    parser.add_argument("--offsets-arcmin", default="-5,-3,-1,0,1,3,5")
    parser.add_argument("--out-dir", default=str(ROOT / "reports/bfull_offaxis_scan"))
    parser.add_argument("--ring-config", default=str(ROOT / "data/laue/ge111_480_550keV_multiring_darwin_config.csv"))
    parser.add_argument("--xop-curve", default=str(ROOT / "benchmarks/xop_crystal/ge111_511keV_rocking_curve.csv"))
    parser.add_argument("--keep-runs", action="store_true")
    args = parser.parse_args()

    exe = Path(args.exe)
    if not exe.exists():
        raise FileNotFoundError(f"B-FULL executable not found: {exe}")
    rings = load_ring_config(args.ring_config)
    offsets = [float(x) for x in args.offsets_arcmin.split(",") if x.strip()]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    xop_curve = _load_xop_curve(Path(args.xop_curve))

    run_root_obj = tempfile.TemporaryDirectory(prefix="laue_bfull_offaxis_scan_")
    run_root = Path(run_root_obj.name)
    rows: list[dict[str, object]] = []
    try:
        expected_ring_counts = _expected_primary_counts_by_ring(rings, args.n)
        for offset in offsets:
            run_dir = run_root / _offset_name(offset)
            cmd = [
                str(exe),
                "--n",
                str(args.n),
                "--seed",
                str(args.seed),
                "--offaxis-x-arcmin",
                f"{offset:g}",
                "--out",
                str(run_dir),
            ]
            completed = subprocess.run(cmd, cwd="/home/ubuntu/opticsim", text=True, capture_output=True, check=False)
            if completed.returncode != 0:
                raise RuntimeError(
                    f"B-FULL run failed for offset {offset:g} arcmin\n"
                    f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
                )
            summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
            per_ring = _read_per_ring(run_dir / "per_ring_summary.csv")
            transmitted_rows = _count_csv_rows(run_dir / "transmitted_space.csv")
            predicted = _predict_scan_point(rings, args.n, offset, xop_curve)
            ring2 = per_ring.get(2, {})
            ring2_expected_primaries = expected_ring_counts.get(2, 0)
            ring2_observed_interactions = int(ring2.get("n_diffracted", 0))
            rows.append(
                {
                    "offset_x_arcmin": offset,
                    "n_primaries": int(summary["n_primaries"]),
                    "registered_in_geant4_em_category": bool(summary.get("registered_in_geant4_em_category")),
                    "geant4_process_base_class": str(summary.get("geant4_process_base_class", "")),
                    "observed_laue_interaction_fraction": float(summary["laue_interaction_fraction"]),
                    "observed_focal_crossing_fraction": float(summary["focal_crossings"]) / float(summary["n_primaries"]),
                    "observed_diffracted_focal_crossing_fraction": float(summary["laue_diffracted_focal_crossings"])
                    / float(summary["n_primaries"]),
                    "transmitted_space_rows": transmitted_rows,
                    "transmitted_space_rows_match_summary": transmitted_rows == int(summary.get("transmitted_space_rows", -1)),
                    "focal_crossing_spot_d90_cm": float(summary["focal_crossing_spot_d90_cm"]),
                    "predicted_full_lens_diffraction_only_fraction": predicted["full_lens_diffraction_only_fraction"],
                    "predicted_full_lens_mean_delta_abs_urad": predicted["full_lens_mean_delta_abs_urad"],
                    "ring2_n_primaries": ring2_expected_primaries,
                    "ring2_observed_laue_interactions": ring2_observed_interactions,
                    "ring2_observed_laue_interaction_fraction": (
                        ring2_observed_interactions / ring2_expected_primaries if ring2_expected_primaries else 0.0
                    ),
                    "ring2_predicted_diffraction_only_fraction": predicted["ring2_diffraction_only_fraction"],
                    "ring2_xop_mean_reflectivity": predicted["ring2_xop_mean_reflectivity"],
                    "ring2_mean_delta_abs_urad": predicted["ring2_mean_delta_abs_urad"],
                    "run_stdout_tail": completed.stdout.strip().splitlines()[-1] if completed.stdout.strip() else "",
                }
            )

        _write_csv(out_dir / "scan.csv", rows)
        summary = _build_summary(args, exe, rows, xop_curve, run_root if args.keep_runs else None)
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


def _offset_name(offset: float) -> str:
    sign = "p" if offset >= 0 else "m"
    return f"offaxis_{sign}{abs(offset):g}arcmin".replace(".", "p")


def _read_per_ring(path: Path) -> dict[int, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {int(row["ring_id"]): row for row in csv.DictReader(handle)}


def _count_csv_rows(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def _expected_primary_counts_by_ring(rings: list[RingSpec], n_events: int) -> dict[int, int]:
    counts = {ring.ring_id: 0 for ring in rings}
    total_tiles = sum(r.n_tiles for r in rings)
    for event_id in range(n_events):
        idx = event_id % total_tiles
        for ring in rings:
            if idx < ring.n_tiles:
                counts[ring.ring_id] += 1
                break
            idx -= ring.n_tiles
    return counts


def _load_xop_curve(path: Path) -> list[tuple[float, float]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [(float(row["delta_theta_rad"]), float(row["reflectivity"])) for row in csv.DictReader(handle)]
    return sorted(rows)


def _predict_scan_point(
    rings: list[RingSpec],
    n_events: int,
    offset_x_arcmin: float,
    xop_curve: list[tuple[float, float]],
) -> dict[str, float]:
    totals = {"all_p": 0.0, "all_abs_delta": 0.0, "all_n": 0, "r2_p": 0.0, "r2_xop": 0.0, "r2_abs_delta": 0.0, "r2_n": 0}
    total_tiles = sum(r.n_tiles for r in rings)
    for event_id in range(n_events):
        idx = event_id % total_tiles
        ring = rings[-1]
        tile_id = rings[-1].n_tiles - 1
        for candidate in rings:
            if idx < candidate.n_tiles:
                ring = candidate
                tile_id = idx
                break
            idx -= candidate.n_tiles
        delta = _delta_theta_for_tile(ring, tile_id, offset_x_arcmin)
        p = _diffraction_only_probability(ring, delta)
        totals["all_p"] += p
        totals["all_abs_delta"] += abs(delta)
        totals["all_n"] += 1
        if ring.ring_id == 2:
            totals["r2_p"] += p
            totals["r2_xop"] += _interp_curve(xop_curve, delta)
            totals["r2_abs_delta"] += abs(delta)
            totals["r2_n"] += 1
    all_n = max(1, int(totals["all_n"]))
    r2_n = max(1, int(totals["r2_n"]))
    return {
        "full_lens_diffraction_only_fraction": totals["all_p"] / all_n,
        "full_lens_mean_delta_abs_urad": totals["all_abs_delta"] / all_n * 1.0e6,
        "ring2_diffraction_only_fraction": totals["r2_p"] / r2_n,
        "ring2_xop_mean_reflectivity": totals["r2_xop"] / r2_n,
        "ring2_mean_delta_abs_urad": totals["r2_abs_delta"] / r2_n * 1.0e6,
    }


def _delta_theta_for_tile(ring: RingSpec, tile_id: int, offset_x_arcmin: float) -> float:
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
    off = math.radians(offset_x_arcmin / 60.0)
    incoming = _unit((math.tan(off), 0.0, 1.0))
    theta_local = math.asin(abs(_dot(incoming, plane_normal)))
    return theta_local - bragg_angle_rad(ring.design_energy_keV, ring.d_spacing_A)


def _diffraction_only_probability(ring: RingSpec, delta_theta_rad: float) -> float:
    q_cm_inv = darwin_q_ge111_cm_inv(ring.design_energy_keV, ring.d_spacing_A, 5.0)
    sigma_cm_inv = q_cm_inv * mosaic_weight_rad_inv(delta_theta_rad, 30.0)
    thickness_cm = ring.thickness_mm / 10.0
    return 0.5 * (1.0 - math.exp(-2.0 * sigma_cm_inv * thickness_cm))


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
    xop_curve: list[tuple[float, float]],
    raw_runs: Path | None,
) -> dict[str, object]:
    observed_peak = max(float(row["observed_laue_interaction_fraction"]) for row in rows)
    observed_min = min(float(row["observed_laue_interaction_fraction"]) for row in rows)
    ring2_peak = max(float(row["ring2_observed_laue_interaction_fraction"]) for row in rows)
    ring2_min = min(float(row["ring2_observed_laue_interaction_fraction"]) for row in rows)
    xop_peak = max(float(row["ring2_xop_mean_reflectivity"]) for row in rows)
    xop_min = min(float(row["ring2_xop_mean_reflectivity"]) for row in rows)
    all_em_category = all(bool(row["registered_in_geant4_em_category"]) for row in rows)
    all_g4vemprocess = all(row["geant4_process_base_class"] == "G4VEmProcess" for row in rows)
    all_transmitted_rows_match = all(bool(row["transmitted_space_rows_match_summary"]) for row in rows)
    return {
        "ok": (
            observed_peak > observed_min
            and ring2_peak > ring2_min
            and xop_peak > xop_min
            and all_em_category
            and all_g4vemprocess
            and all_transmitted_rows_match
            and (observed_peak / observed_min if observed_min else 0.0) > 5.0
            and (ring2_peak / ring2_min if ring2_min else 0.0) > 5.0
        ),
        "bfull_executable": str(exe),
        "n_per_offset": args.n,
        "seed": args.seed,
        "offsets_arcmin": [float(row["offset_x_arcmin"]) for row in rows],
        "observed_peak_interaction_fraction": observed_peak,
        "observed_min_interaction_fraction": observed_min,
        "observed_peak_to_min_ratio": observed_peak / observed_min if observed_min else None,
        "ring2_observed_peak_to_min_ratio": ring2_peak / ring2_min if ring2_min else None,
        "ring2_xop_peak_to_min_ratio": xop_peak / xop_min if xop_min else None,
        "all_registered_in_geant4_em_category": all_em_category,
        "all_process_base_g4vemprocess": all_g4vemprocess,
        "all_transmitted_space_rows_match_summary": all_transmitted_rows_match,
        "xop_curve_points": len(xop_curve),
        "raw_runs": str(raw_runs) if raw_runs else "temporary_deleted",
        "note": (
            "Observed B-FULL interaction fractions include Geant4 standard EM competition. "
            "Predicted diffraction-only fractions are the local finite-MFP backend without EM competition. "
            "Ring 2 XOP values are 511 keV CRYSTAL rocking-curve interpolations averaged over the same tile sequence."
        ),
    }


def _write_markdown(path: Path, summary: dict[str, object], rows: list[dict[str, object]]) -> None:
    lines = [
        "# B-FULL Off-Axis Scan",
        "",
        f"- ok: `{summary['ok']}`",
        f"- executable: `{summary['bfull_executable']}`",
        f"- events per offset: `{summary['n_per_offset']}`",
        f"- all runs registered in Geant4 EM category: `{summary['all_registered_in_geant4_em_category']}`",
        f"- all runs use G4VEmProcess base: `{summary['all_process_base_g4vemprocess']}`",
        f"- transmitted_space rows match summary: `{summary['all_transmitted_space_rows_match_summary']}`",
        f"- observed peak/min interaction ratio: `{summary['observed_peak_to_min_ratio']}`",
        f"- ring 2 observed peak/min ratio: `{summary['ring2_observed_peak_to_min_ratio']}`",
        f"- ring 2 XOP peak/min ratio: `{summary['ring2_xop_peak_to_min_ratio']}`",
        "",
        "| offset arcmin | obs Laue frac | pred full no-EM | ring2 obs | ring2 XOP | ring2 |delta| urad |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {offset_x_arcmin:g} | {observed_laue_interaction_fraction:.6g} | "
            "{predicted_full_lens_diffraction_only_fraction:.6g} | "
            "{ring2_observed_laue_interaction_fraction:.6g} | {ring2_xop_mean_reflectivity:.6g} | "
            "{ring2_mean_delta_abs_urad:.6g} |".format(**row)
        )
    lines.extend(["", str(summary["note"]), ""])
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
