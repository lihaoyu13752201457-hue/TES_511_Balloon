#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", default="/tmp/opticsim-bfull-build/laue_multiring_bfull_demo")
    parser.add_argument("--n", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20260529)
    parser.add_argument("--offsets-arcmin", default="-5,-3,-1,0,1,3,5")
    parser.add_argument("--out-dir", default=str(ROOT / "reports/bfull_full_lens_xop_map_scan"))
    parser.add_argument(
        "--map-csv",
        default=str(ROOT / "reports/bfull_rocking_curve_map_status/available_rocking_curve_map.csv"),
    )
    parser.add_argument("--keep-runs", action="store_true")
    args = parser.parse_args()

    exe = Path(args.exe)
    if not exe.exists():
        raise FileNotFoundError(f"B-FULL executable not found: {exe}")
    map_csv = Path(args.map_csv)
    curve_map = _load_curve_map(map_csv)
    offsets = [float(x) for x in args.offsets_arcmin.split(",") if x.strip()]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    run_root_obj = tempfile.TemporaryDirectory(prefix="laue_bfull_xop_map_full_lens_")
    run_root = Path(run_root_obj.name)
    rows: list[dict[str, object]] = []
    try:
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
                "--rocking-curve-map",
                str(map_csv.resolve()),
                "--require-rocking-curve-map",
                "--out",
                str(run_dir),
            ]
            completed = subprocess.run(cmd, cwd="/home/ubuntu/opticsim", text=True, capture_output=True, check=False)
            if completed.returncode != 0:
                raise RuntimeError(
                    f"B-FULL full-lens XOP-map run failed for offset {offset:g} arcmin\n"
                    f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
                )
            summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
            per_ring = _read_per_ring(run_dir / "per_ring_summary.csv")
            history = _history_map_check(run_dir / "optics_history.csv", curve_map)
            transmitted_rows = _count_csv_rows(run_dir / "transmitted_space.csv")
            rows.append(
                {
                    "offset_x_arcmin": offset,
                    "n_primaries": int(summary["n_primaries"]),
                    "rocking_curve_backend": summary["rocking_curve_backend"],
                    "rocking_curve_map_required": bool(summary["rocking_curve_map_required"]),
                    "registered_in_geant4_em_category": bool(summary.get("registered_in_geant4_em_category")),
                    "geant4_process_base_class": str(summary.get("geant4_process_base_class", "")),
                    "covered_ring_ids": ";".join(str(x) for x in summary["rocking_curve_map_covered_ring_ids"]),
                    "all_per_ring_sources_external": all(
                        row.get("rocking_curve_source") == "external_rocking_curve_map_csv" for row in per_ring
                    ),
                    "observed_laue_interaction_fraction": float(summary["laue_interaction_fraction"]),
                    "n_laue_interactions": int(summary["n_laue_interactions"]),
                    "laue_diffracted_focal_crossings": int(summary["laue_diffracted_focal_crossings"]),
                    "transmitted_space_rows": transmitted_rows,
                    "transmitted_space_rows_match_summary": transmitted_rows == int(summary.get("transmitted_space_rows", -1)),
                    "focal_crossing_spot_d90_cm": float(summary["focal_crossing_spot_d90_cm"]),
                    "history_rows": history["n_rows"],
                    "max_recorded_p_reflect_minus_xop_map": history["max_abs_p_reflect_delta"],
                    "mean_recorded_p_reflect": history["mean_recorded_p_reflect"],
                    "run_stdout_tail": completed.stdout.strip().splitlines()[-1] if completed.stdout.strip() else "",
                }
            )

        _write_csv(out_dir / "scan.csv", rows)
        summary = _build_summary(args, exe, map_csv, rows, run_root if args.keep_runs else None)
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


def _load_curve_map(path: Path) -> dict[int, list[tuple[float, float]]]:
    out: dict[int, list[tuple[float, float]]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            curve_path = Path(row["curve_csv"])
            if not curve_path.is_absolute():
                curve_path = path.parent / curve_path
            out[int(row["ring_id"])] = _load_curve(curve_path)
    return out


def _load_curve(path: Path) -> list[tuple[float, float]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [(float(row["delta_theta_rad"]), float(row["reflectivity"])) for row in csv.DictReader(handle)]
    return sorted(rows)


def _read_per_ring(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _count_csv_rows(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def _history_map_check(path: Path, curve_map: dict[int, list[tuple[float, float]]]) -> dict[str, object]:
    deltas: list[float] = []
    p_reflect: list[float] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            ring_id = int(row["ring_id"])
            recorded = float(row["p_reflect"])
            expected = _interp_curve(curve_map[ring_id], float(row["delta_theta_model_rad"]))
            deltas.append(abs(recorded - expected))
            p_reflect.append(recorded)
    return {
        "n_rows": len(deltas),
        "max_abs_p_reflect_delta": max(deltas) if deltas else None,
        "mean_recorded_p_reflect": sum(p_reflect) / len(p_reflect) if p_reflect else None,
    }


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
    map_csv: Path,
    rows: list[dict[str, object]],
    raw_runs: Path | None,
) -> dict[str, object]:
    observed_peak = max(float(row["observed_laue_interaction_fraction"]) for row in rows)
    observed_min = min(float(row["observed_laue_interaction_fraction"]) for row in rows)
    min_nonzero = min(
        (float(row["observed_laue_interaction_fraction"]) for row in rows if float(row["observed_laue_interaction_fraction"]) > 0.0),
        default=None,
    )
    max_recorded_delta = max(
        float(row["max_recorded_p_reflect_minus_xop_map"])
        for row in rows
        if row["max_recorded_p_reflect_minus_xop_map"] is not None
    )
    all_sources_external = all(bool(row["all_per_ring_sources_external"]) for row in rows)
    all_backend_map = all(row["rocking_curve_backend"] == "external_per_ring_csv_map" for row in rows)
    all_required = all(bool(row["rocking_curve_map_required"]) for row in rows)
    all_em_category = all(bool(row["registered_in_geant4_em_category"]) for row in rows)
    all_g4vemprocess = all(row["geant4_process_base_class"] == "G4VEmProcess" for row in rows)
    all_transmitted_rows_match = all(bool(row["transmitted_space_rows_match_summary"]) for row in rows)
    return {
        "ok": (
            all_sources_external
            and all_backend_map
            and all_required
            and all_em_category
            and all_g4vemprocess
            and all_transmitted_rows_match
            and max_recorded_delta <= 5.0e-4
            and observed_peak > observed_min
            and ((observed_peak / observed_min) if observed_min else float("inf")) > 5.0
        ),
        "bfull_executable": str(exe),
        "map_csv": str(map_csv),
        "n_per_offset": args.n,
        "seed": args.seed,
        "offsets_arcmin": [float(row["offset_x_arcmin"]) for row in rows],
        "observed_peak_interaction_fraction": observed_peak,
        "observed_min_interaction_fraction": observed_min,
        "observed_peak_to_min_ratio": observed_peak / observed_min if observed_min else None,
        "observed_peak_to_min_nonzero_ratio": observed_peak / min_nonzero if min_nonzero else None,
        "all_per_ring_sources_external": all_sources_external,
        "all_backend_external_per_ring_map": all_backend_map,
        "all_runs_required_complete_map": all_required,
        "all_registered_in_geant4_em_category": all_em_category,
        "all_process_base_g4vemprocess": all_g4vemprocess,
        "all_transmitted_space_rows_match_summary": all_transmitted_rows_match,
        "max_recorded_p_reflect_minus_xop_map": max_recorded_delta,
        "raw_runs": str(raw_runs) if raw_runs else "temporary_deleted",
        "note": (
            "Full-lens B-FULL run using a custom G4VEmProcess with --rocking-curve-map "
            "and --require-rocking-curve-map. "
            "Each recorded Laue interaction p_reflect is checked against the ring-specific XOP/CRYSTAL curve."
        ),
    }


def _write_markdown(path: Path, summary: dict[str, object], rows: list[dict[str, object]]) -> None:
    lines = [
        "# B-FULL Full-Lens XOP Map Scan",
        "",
        f"- ok: `{summary['ok']}`",
        f"- executable: `{summary['bfull_executable']}`",
        f"- map CSV: `{summary['map_csv']}`",
        f"- events per offset: `{summary['n_per_offset']}`",
        f"- all runs registered in Geant4 EM category: `{summary['all_registered_in_geant4_em_category']}`",
        f"- all runs use G4VEmProcess base: `{summary['all_process_base_g4vemprocess']}`",
        f"- transmitted_space rows match summary: `{summary['all_transmitted_space_rows_match_summary']}`",
        f"- observed peak/min interaction ratio: `{summary['observed_peak_to_min_ratio']}`",
        f"- max |recorded p_reflect - XOP map|: `{summary['max_recorded_p_reflect_minus_xop_map']}`",
        "",
        "| offset arcmin | obs Laue frac | interactions | focal d90 cm | history rows | mean p_reflect | max p delta |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {offset_x_arcmin:g} | {observed_laue_interaction_fraction:.6g} | "
            "{n_laue_interactions} | {focal_crossing_spot_d90_cm:.6g} | {history_rows} | "
            "{mean_recorded_p_reflect:.6g} | {max_recorded_p_reflect_minus_xop_map:.6g} |".format(**row)
        )
    lines.extend(["", str(summary["note"]), ""])
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
