#!/usr/bin/env python3
"""Build the f=10 m Ge(111) 511 keV Aeff authority JSON from focal crossings."""

from __future__ import annotations

import argparse
import csv
import json
import math
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MODEL = "balloon511_f10m_ge111_511line"
BE_RADIUS_MM = 18.98
NATURAL_PASSBAND_KEV = [500.993937, 521.006063]
R1_AEFF_GATES = {"a1": [19.4, 21.4], "a2": [16.2, 17.8]}
HC_KEV_A = 12.398419843320026


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        return json.load(handle)


def git_hash(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except Exception:
        return "unknown"
    return result.stdout.strip()


def resolve_repo_path(root: Path, path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return root / path


def read_ring_config(path: Path) -> dict[str, Any]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"ring config has no rows: {path}")
    if len(rows) != 1:
        raise ValueError(f"f10m authority report expects one ring, got {len(rows)} rows in {path}")
    row = rows[0]
    n_tiles = int(row["n_tiles"])
    tile_size_mm = float(row["tile_size_mm"])
    thickness_mm = float(row["thickness_mm"])
    tile_size_cm = tile_size_mm / 10.0
    return {
        "ring_id": int(row["ring_id"]),
        "design_energy_keV": float(row["design_energy_keV"]),
        "radius_mm": float(row["radius_mm"]),
        "n_tiles": n_tiles,
        "material": row["material"],
        "hkl": [int(row["h"]), int(row["k"]), int(row["l"])],
        "d_spacing_A": float(row["d_spacing_A"]),
        "tile_size_mm": tile_size_mm,
        "thickness_mm": thickness_mm,
        "z_offset_mm": float(row.get("z_offset_mm") or 0.0),
        "geometric_area_cm2": n_tiles * tile_size_cm * tile_size_cm,
    }


def _unit(vec: tuple[float, float, float]) -> tuple[float, float, float]:
    mag = math.sqrt(sum(v * v for v in vec))
    return tuple(v / mag for v in vec)


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return sum(a[i] * b[i] for i in range(3))


def _load_rocking_curve(root: Path, map_path_value: str, ring_id: int) -> list[tuple[float, float]] | None:
    if not map_path_value:
        return None
    map_path = resolve_repo_path(root, map_path_value)
    if not map_path.exists():
        return None
    with map_path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            if int(row["ring_id"]) != ring_id:
                continue
            curve_value = row.get("curve_csv") or row.get("rocking_curve_csv") or row.get("path")
            if not curve_value:
                return None
            curve_path = Path(curve_value)
            if not curve_path.is_absolute():
                curve_path = map_path.parent / curve_path
            with curve_path.open(newline="") as curve_handle:
                points = [
                    (float(curve_row["delta_theta_rad"]), float(curve_row["reflectivity"]))
                    for curve_row in csv.DictReader(curve_handle)
                ]
            return sorted(points)
    return None


def _interp_curve(points: list[tuple[float, float]], delta_theta_rad: float) -> float:
    if delta_theta_rad <= points[0][0]:
        return points[0][1]
    if delta_theta_rad >= points[-1][0]:
        return points[-1][1]
    lo = 0
    hi = len(points) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if points[mid][0] < delta_theta_rad:
            lo = mid
        else:
            hi = mid
    x0, y0 = points[lo]
    x1, y1 = points[hi]
    return y0 + (y1 - y0) * (delta_theta_rad - x0) / (x1 - x0)


def analytic_offaxis_retention_from_curve(root: Path, config: dict[str, Any], map_path_value: str, offaxis_x_arcmin: float, offaxis_y_arcmin: float) -> float | None:
    points = _load_rocking_curve(root, map_path_value, int(config["ring_id"]))
    if not points:
        return None
    theta_b = math.asin((HC_KEV_A / float(config["design_energy_keV"])) / (2.0 * float(config["d_spacing_A"])))

    def average_reflectivity(x_arcmin: float, y_arcmin: float) -> float:
        in_dir = _unit(
            (
                math.tan(x_arcmin / 60.0 * math.pi / 180.0),
                math.tan(y_arcmin / 60.0 * math.pi / 180.0),
                1.0,
            )
        )
        values = []
        for tile_id in range(int(config["n_tiles"])):
            phi = 2.0 * math.pi * tile_id / int(config["n_tiles"])
            cx = float(config["radius_mm"]) * math.cos(phi)
            cy = float(config["radius_mm"]) * math.sin(phi)
            cz = float(config["z_offset_mm"])
            out_dir = _unit((-cx, -cy, float(config.get("focal_length_mm", 10000.0)) - cz))
            plane_normal = _unit((-out_dir[0], -out_dir[1], 1.0 - out_dir[2]))
            theta_local = math.asin(abs(_dot(in_dir, plane_normal)))
            values.append(_interp_curve(points, theta_local - theta_b))
        return sum(values) / len(values)

    on_axis = average_reflectivity(0.0, 0.0)
    if on_axis <= 0.0:
        return None
    return average_reflectivity(offaxis_x_arcmin, offaxis_y_arcmin) / on_axis


def parse_run_arg(value: str) -> tuple[str, Path]:
    if "=" in value:
        label, path = value.split("=", 1)
        return label.strip(), Path(path)
    path = Path(value)
    return path.name, path


def discover_runs(root: Path, run_root_value: str) -> list[tuple[str, Path]]:
    run_root = resolve_repo_path(root, run_root_value)
    if not run_root.exists():
        return []
    runs: list[tuple[str, Path]] = []
    for path in sorted(run_root.iterdir()):
        if (path / "summary.json").exists() and (path / "focal_crossings.csv").exists():
            runs.append((path.name, path))
    return runs


def command_metadata(run_dir: Path) -> dict[str, Any]:
    command_file = run_dir / "run_command.txt"
    meta: dict[str, Any] = {}
    if not command_file.exists():
        return meta
    for line in command_file.read_text().splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        meta[key.lower()] = value
    command_line = meta.get("run_command", "")
    if command_line:
        args = shlex.split(command_line)
        meta["run_command_args"] = args
        for i, arg in enumerate(args[:-1]):
            if arg.startswith("--"):
                meta[arg[2:].replace("-", "_")] = args[i + 1]
    return meta


def quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(math.ceil(q * len(ordered)) - 1)))
    return ordered[idx]


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def pstdev(values: list[float]) -> float | None:
    if not values:
        return None
    avg = sum(values) / len(values)
    return math.sqrt(sum((value - avg) ** 2 for value in values) / len(values))


def focal_metrics(focal_path: Path, be_radius_mm: float) -> dict[str, Any]:
    radii: list[float] = []
    within_be = 0
    with focal_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("source_tag") != "laue_bfull_diffracted":
                continue
            radius = math.hypot(float(row["x_mm"]), float(row["y_mm"]))
            radii.append(radius)
            if radius <= be_radius_mm:
                within_be += 1
    count = len(radii)
    return {
        "diffracted_focal_crossings": count,
        "within_be_diffracted_focal_crossings": within_be,
        "within_be_capture_fraction": (within_be / count) if count else 0.0,
        "r50_mm": quantile(radii, 0.50),
        "r90_mm": quantile(radii, 0.90),
        "r99_mm": quantile(radii, 0.99),
        "max_radius_mm": max(radii) if radii else None,
    }


def infer_variant(label: str, config: dict[str, Any], meta: dict[str, Any]) -> str:
    variant = str(meta.get("variant", "")).lower()
    if variant in {"a1", "a2"}:
        return variant
    if "_a2" in label.lower() or config["tile_size_mm"] == 15.0:
        return "a2"
    return "a1"


def run_kind(label: str, meta: dict[str, Any]) -> str:
    lower = label.lower()
    if "r1" in lower:
        return "R1_legacy_jitter"
    if "r2" in lower:
        return "R2_honest_tile_footprint"
    if "offaxis" in lower or "r3" in lower or "r4" in lower or "r5" in lower or "r6" in lower:
        return "offaxis"
    jitter = float(meta.get("source_jitter_mm", 0.3))
    if jitter > 1.0:
        return "R2_honest_tile_footprint"
    return "R1_legacy_jitter"


def analyze_run(root: Path, label: str, run_dir: Path, be_radius_mm: float) -> dict[str, Any]:
    summary_path = run_dir / "summary.json"
    focal_path = run_dir / "focal_crossings.csv"
    summary = load_json(summary_path)
    meta = command_metadata(run_dir)
    config_path = resolve_repo_path(root, summary["ring_config"])
    config = read_ring_config(config_path)
    metrics = focal_metrics(focal_path, be_radius_mm)
    n_primaries = int(summary["n_primaries"])
    p_within = metrics["within_be_diffracted_focal_crossings"] / n_primaries
    aeff = config["geometric_area_cm2"] * p_within
    stat = config["geometric_area_cm2"] * math.sqrt(p_within * (1.0 - p_within) / n_primaries)
    variant = infer_variant(label, config, meta)
    jitter = float(meta.get("source_jitter_mm", 0.3))
    offaxis_x = float(meta.get("offaxis_x_arcmin", 0.0))
    offaxis_y = float(meta.get("offaxis_y_arcmin", 0.0))
    config["focal_length_mm"] = float(summary.get("focal_length_mm", 10000.0))
    curve_retention = analytic_offaxis_retention_from_curve(root, config, summary.get("rocking_curve_map_csv", ""), offaxis_x, offaxis_y)
    return {
        "label": label,
        "run_dir": str(run_dir),
        "run_kind": run_kind(label, meta),
        "variant": variant,
        "seed": int(meta.get("seed", summary.get("seed", 12345))),
        "source_jitter_mm": jitter,
        "offaxis_x_arcmin": offaxis_x,
        "offaxis_y_arcmin": offaxis_y,
        "analytic_offaxis_retention_from_curve": curve_retention,
        "summary_json": str(summary_path),
        "focal_crossings_csv": str(focal_path),
        "ring_config": str(config_path),
        "rocking_curve_map_csv": summary.get("rocking_curve_map_csv", ""),
        "run_command": meta.get("run_command", ""),
        "n_primaries": n_primaries,
        "focal_length_mm": summary.get("focal_length_mm"),
        "mosaic_fwhm_arcsec": summary.get("mosaic_fwhm_arcsec"),
        "geometry": config,
        "natural_passband_fwhm_keV": NATURAL_PASSBAND_KEV,
        "emergent_focal_diffraction_fraction": summary.get("emergent_focal_diffraction_fraction"),
        "analytic_reference_focal_diffraction_fraction": summary.get("analytic_reference_focal_diffraction_fraction"),
        "emergent_minus_analytic_focal_diffraction": summary.get("emergent_minus_analytic_focal_diffraction"),
        "laue_diffracted_focal_crossings_summary": summary.get("laue_diffracted_focal_crossings"),
        "within_be_radius_mm": be_radius_mm,
        "within_be_diffracted_fraction_of_primaries": p_within,
        "aeff_cm2": aeff,
        "aeff_stat_error_cm2": stat,
        **metrics,
    }


def gate_status(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gates: list[dict[str, Any]] = []
    for run in runs:
        is_on_axis = run["offaxis_x_arcmin"] == 0.0 and run["offaxis_y_arcmin"] == 0.0
        variant = run["variant"]
        aeff_lo, aeff_hi = R1_AEFF_GATES[variant]
        gates.append(
            {
                "run": run["label"],
                "gate": "within_be_capture_fraction_gt_0.995",
                "value": run["within_be_capture_fraction"],
                "pass": float(run["within_be_capture_fraction"]) > 0.995,
            }
        )
        if not is_on_axis:
            continue
        gates.append(
            {
                "run": run["label"],
                "gate": f"{variant}_aeff_range_cm2",
                "expected_range_cm2": [aeff_lo, aeff_hi],
                "value": run["aeff_cm2"],
                "pass": aeff_lo <= float(run["aeff_cm2"]) <= aeff_hi,
            }
        )
        gates.append(
            {
                "run": run["label"],
                "gate": "diffracted_crossings_ge_12000",
                "value": run["diffracted_focal_crossings"],
                "pass": int(run["diffracted_focal_crossings"]) >= 12000,
                "note": "This authority-statistics gate is expected to fail for smoke runs.",
            }
        )
        if run["run_kind"] == "R2_honest_tile_footprint" and variant == "a1":
            gates.append(
                {
                    "run": run["label"],
                    "gate": "a1_r2_r50_7.2_pm_1.0_mm",
                    "value": run["r50_mm"],
                    "pass": run["r50_mm"] is not None and 6.2 <= float(run["r50_mm"]) <= 8.2,
                }
            )
            gates.append(
                {
                    "run": run["label"],
                    "gate": "a1_r2_r90_10.5_pm_1.5_mm",
                    "value": run["r90_mm"],
                    "pass": run["r90_mm"] is not None and 9.0 <= float(run["r90_mm"]) <= 12.0,
                }
            )
    by_variant_seed: dict[tuple[str, int], dict[str, dict[str, Any]]] = {}
    for run in runs:
        if run["offaxis_x_arcmin"] != 0.0 or run["offaxis_y_arcmin"] != 0.0:
            continue
        key = (run["variant"], run["seed"])
        by_variant_seed.setdefault(key, {})[run["run_kind"]] = run
    for (variant, seed), pair in by_variant_seed.items():
        r1 = pair.get("R1_legacy_jitter")
        r2 = pair.get("R2_honest_tile_footprint")
        if r1 and r2:
            rel = abs(float(r1["aeff_cm2"]) - float(r2["aeff_cm2"])) / max(float(r1["aeff_cm2"]), 1.0e-12)
            gates.append(
                {
                    "run": f"{variant}_seed{seed}",
                    "gate": "r1_r2_aeff_relative_difference_lt_0.02",
                    "value": rel,
                    "pass": rel < 0.02,
                }
            )
    for row in offaxis_table(runs):
        if row["retention_vs_onaxis_r2"] is None or row["analytic_retention_from_curve"] is None:
            continue
        diff = abs(float(row["retention_vs_onaxis_r2"]) - float(row["analytic_retention_from_curve"]))
        gates.append(
            {
                "run": row["run"],
                "gate": "offaxis_retention_matches_local_curve_within_0.03",
                "value": diff,
                "retention_vs_onaxis_r2": row["retention_vs_onaxis_r2"],
                "analytic_retention_from_curve": row["analytic_retention_from_curve"],
                "pass": diff < 0.03,
            }
        )
    for group in seed_summary(runs):
        if group["offaxis_x_arcmin"] != 0.0 or group["offaxis_y_arcmin"] != 0.0:
            continue
        if group["run_kind"] not in {"R1_legacy_jitter", "R2_honest_tile_footprint"}:
            continue
        gates.append(
            {
                "run": group["group"],
                "gate": "seed_aggregate_emergent_focal_diffraction_fraction_0.252_pm_0.006",
                "value": group["mean_emergent_focal_diffraction_fraction"],
                "pass": 0.246 <= float(group["mean_emergent_focal_diffraction_fraction"]) <= 0.258,
            }
        )
        gates.append(
            {
                "run": group["group"],
                "gate": "seed_aggregate_abs_emergent_minus_analytic_lt_0.01",
                "value": abs(float(group["mean_emergent_minus_analytic_focal_diffraction"])),
                "pass": abs(float(group["mean_emergent_minus_analytic_focal_diffraction"])) < 0.01,
            }
        )
    return gates


def offaxis_table(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    on_axis: dict[tuple[str, int], float] = {}
    for run in runs:
        if run["run_kind"] == "R2_honest_tile_footprint" and run["offaxis_x_arcmin"] == 0.0 and run["offaxis_y_arcmin"] == 0.0:
            on_axis[(run["variant"], run["seed"])] = float(run["aeff_cm2"])
    for run in runs:
        if run["offaxis_x_arcmin"] == 0.0 and run["offaxis_y_arcmin"] == 0.0:
            continue
        base = on_axis.get((run["variant"], run["seed"]))
        rows.append(
            {
                "run": run["label"],
                "variant": run["variant"],
                "seed": run["seed"],
                "offaxis_x_arcmin": run["offaxis_x_arcmin"],
                "offaxis_y_arcmin": run["offaxis_y_arcmin"],
                "aeff_cm2": run["aeff_cm2"],
                "retention_vs_onaxis_r2": (float(run["aeff_cm2"]) / base) if base else None,
                "analytic_retention_from_curve": run.get("analytic_offaxis_retention_from_curve"),
            }
        )
    return rows


def seed_summary(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, float, float], list[dict[str, Any]]] = {}
    for run in runs:
        key = (run["variant"], run["run_kind"], float(run["offaxis_x_arcmin"]), float(run["offaxis_y_arcmin"]))
        groups.setdefault(key, []).append(run)
    rows: list[dict[str, Any]] = []
    for (variant, kind, offaxis_x, offaxis_y), items in sorted(groups.items()):
        aeff_values = [float(item["aeff_cm2"]) for item in items]
        r50_values = [float(item["r50_mm"]) for item in items if item["r50_mm"] is not None]
        r90_values = [float(item["r90_mm"]) for item in items if item["r90_mm"] is not None]
        emergent_values = [float(item["emergent_focal_diffraction_fraction"]) for item in items]
        diff_values = [float(item["emergent_minus_analytic_focal_diffraction"]) for item in items]
        rows.append(
            {
                "group": f"{variant}_{kind}_offaxis{offaxis_x:g}_{offaxis_y:g}",
                "variant": variant,
                "run_kind": kind,
                "offaxis_x_arcmin": offaxis_x,
                "offaxis_y_arcmin": offaxis_y,
                "n_seeds": len(items),
                "seeds": sorted(int(item["seed"]) for item in items),
                "mean_aeff_cm2": mean(aeff_values),
                "pstdev_aeff_cm2": pstdev(aeff_values),
                "mean_r50_mm": mean(r50_values),
                "mean_r90_mm": mean(r90_values),
                "mean_emergent_focal_diffraction_fraction": mean(emergent_values),
                "mean_emergent_minus_analytic_focal_diffraction": mean(diff_values),
            }
        )
    return rows


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        f"# {report['model']} Aeff Authority Draft",
        "",
        f"- generated_at_utc: `{report['generated_at_utc']}`",
        f"- git_hash: `{report['git_hash']}`",
        f"- be_radius_mm: `{report['be_radius_mm']}`",
        "",
        "## Runs",
        "",
        "| label | variant | kind | N | jitter mm | offaxis x arcmin | Aeff cm2 | stat cm2 | r50 mm | r90 mm | within-Be |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for run in report["runs"]:
        lines.append(
            "| {label} | {variant} | {kind} | {n} | {jitter:.3g} | {offaxis:.3g} | {aeff:.4g} | {stat:.3g} | {r50} | {r90} | {within:.5f} |".format(
                label=run["label"],
                variant=run["variant"],
                kind=run["run_kind"],
                n=run["n_primaries"],
                jitter=float(run["source_jitter_mm"]),
                offaxis=float(run["offaxis_x_arcmin"]),
                aeff=float(run["aeff_cm2"]),
                stat=float(run["aeff_stat_error_cm2"]),
                r50="NA" if run["r50_mm"] is None else f"{float(run['r50_mm']):.4g}",
                r90="NA" if run["r90_mm"] is None else f"{float(run['r90_mm']):.4g}",
                within=float(run["within_be_capture_fraction"]),
            )
        )
    if report["seed_summary"]:
        lines.extend(
            [
                "",
                "## Seed Summary",
                "",
                "| group | seeds | mean Aeff cm2 | sd Aeff cm2 | mean r50 mm | mean r90 mm | mean emergent |",
                "|---|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for row in report["seed_summary"]:
            lines.append(
                "| {group} | {seeds} | {aeff:.4g} | {sd:.3g} | {r50} | {r90} | {emergent:.5f} |".format(
                    group=row["group"],
                    seeds=",".join(str(seed) for seed in row["seeds"]),
                    aeff=float(row["mean_aeff_cm2"]),
                    sd=0.0 if row["pstdev_aeff_cm2"] is None else float(row["pstdev_aeff_cm2"]),
                    r50="NA" if row["mean_r50_mm"] is None else f"{float(row['mean_r50_mm']):.4g}",
                    r90="NA" if row["mean_r90_mm"] is None else f"{float(row['mean_r90_mm']):.4g}",
                    emergent=float(row["mean_emergent_focal_diffraction_fraction"]),
                )
            )
    if report["offaxis_table"]:
        lines.extend(
            [
                "",
                "## Off-Axis Retention",
                "",
                "| run | offaxis x arcmin | Aeff cm2 | MC retention | local-curve retention |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for row in report["offaxis_table"]:
            mc_retention = row["retention_vs_onaxis_r2"]
            curve_retention = row["analytic_retention_from_curve"]
            lines.append(
                "| {run} | {offaxis:.3g} | {aeff:.4g} | {mc} | {curve} |".format(
                    run=row["run"],
                    offaxis=float(row["offaxis_x_arcmin"]),
                    aeff=float(row["aeff_cm2"]),
                    mc="NA" if mc_retention is None else f"{float(mc_retention):.4f}",
                    curve="NA" if curve_retention is None else f"{float(curve_retention):.4f}",
                )
            )
    lines.extend(["", "## Gates", ""])
    for gate in report["gates"]:
        lines.append(f"- {gate['gate']} [{gate['run']}]: {'PASS' if gate['pass'] else 'FAIL'} value={gate['value']}")
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="append", default=[], help="Run as LABEL=DIR or DIR. If omitted, scan runs/f10m_ge111_511line.")
    parser.add_argument("--run-root", default="runs/f10m_ge111_511line", help="Directory to scan when --run is omitted.")
    parser.add_argument("--out", default="runs/f10m_ge111_511line/optics_aeff_authority_f10m.json")
    parser.add_argument("--markdown-out", default="")
    parser.add_argument("--be-radius-mm", type=float, default=BE_RADIUS_MM)
    args = parser.parse_args()

    root = repo_root()
    run_specs = [parse_run_arg(value) for value in args.run] if args.run else discover_runs(root, args.run_root)
    if not run_specs:
        raise SystemExit("no f10m runs found; pass --run LABEL=DIR or run analysis/run_f10m.sh first")

    runs = [analyze_run(root, label, path if path.is_absolute() else root / path, args.be_radius_mm) for label, path in run_specs]
    report = {
        "model": MODEL,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "git_hash": git_hash(root),
        "be_radius_mm": args.be_radius_mm,
        "aeff_formula": "n_tiles * tile_size_cm^2 * within_be_diffracted_focal_crossings / n_primaries",
        "provenance": {
            "authority_source": "tracked focal_crossings.csv, source_tag=laue_bfull_diffracted, not phase_space.csv",
            "rocking_curve": "data/laue/ge111_511keV_rocking_curve.csv",
            "plan": "docs/CODEX_EXECUTE_F10M_GE111_511LINE_PLAN_20260611.md",
        },
        "runs": runs,
        "seed_summary": seed_summary(runs),
        "offaxis_table": offaxis_table(runs),
        "gates": gate_status(runs),
    }

    out_path = resolve_repo_path(root, args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    md_path = resolve_repo_path(root, args.markdown_out) if args.markdown_out else out_path.with_suffix(".md")
    write_markdown(md_path, report)
    print(f"wrote {out_path}")
    print(f"wrote {md_path}")


if __name__ == "__main__":
    main()
