#!/usr/bin/env python3
"""Stream the canonical S3d-O8 gamma SIM shards and build leak denominators.

Only compact counters are retained.  The raw SIM files remain read-only and are
never copied.  Direction bins are equal-solid-angle in mu=cos(theta_x), with
azimuth measured about the InstrumentFrame +x axis as atan2(z, y).
"""

from __future__ import annotations

import argparse
import bisect
import csv
import gzip
import json
import math
import os
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from scipy.stats import beta


ENERGY_EDGES_MEV = (0.0, 1.022, 2.0, 4.0, 5.0, 6.0, 8.0, 12.0, 20.0, 50.0, math.inf)
MU_EDGES = (-1.0, -0.5, 0.0, 0.5, 1.0)
AZ_EDGES_DEG = tuple(float(v) for v in range(0, 361, 45))
EXPECTED_GEOMETRY = (
    "/home/ubuntu/TES_511_Balloon/engineering/geometry_optimization_20260704/"
    "43_geoopt_s3d_o8_fallback_20260712/geometry/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)


def bin_index(value: float, edges: tuple[float, ...]) -> int:
    idx = bisect.bisect_right(edges, value) - 1
    return max(0, min(idx, len(edges) - 2))


def parse_init(line: str) -> tuple[float, float, float, float, float, float, float]:
    fields = [field.strip() for field in line[len("IA INIT") :].split(";")]
    if len(fields) < 23:
        raise ValueError(f"Malformed IA INIT with {len(fields)} fields: {line[:160]!r}")
    return (
        float(fields[4]),
        float(fields[5]),
        float(fields[6]),
        float(fields[16]),
        float(fields[17]),
        float(fields[18]),
        float(fields[22]),
    )


def world_to_instrument_vector(dx: float, dy: float, dz: float) -> tuple[float, float, float]:
    # InstrumentFrame is World rotated +45 deg about y.  Coordinates in the
    # rotated frame use the inverse rotation.
    c = math.sqrt(0.5)
    return c * (dx - dz), dy, c * (dx + dz)


def parse_one_shard(task: dict) -> dict:
    path = Path(task["path"])
    selected_ids = set(task["selected_ids"])
    cube: Counter[tuple[int, int, int]] = Counter()
    selected = []
    parsed = 0
    current_event = None
    geometry = None

    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if geometry is None and line.startswith("Geometry"):
                geometry = line.split(None, 1)[1].strip()
            elif line.startswith("ID "):
                parts = line.split()
                current_event = int(parts[1])
            elif line.startswith("IA INIT"):
                if current_event is None:
                    raise RuntimeError(f"IA INIT before ID in {path}")
                x, y, z, dx, dy, dz, energy_kev = parse_init(line)
                if_dx, if_dy, if_dz = world_to_instrument_vector(dx, dy, dz)
                norm = math.sqrt(if_dx * if_dx + if_dy * if_dy + if_dz * if_dz)
                if norm == 0:
                    raise RuntimeError(f"Zero direction in {path}, event {current_event}")
                if_dx, if_dy, if_dz = if_dx / norm, if_dy / norm, if_dz / norm
                theta = math.degrees(math.acos(max(-1.0, min(1.0, if_dx))))
                azimuth = math.degrees(math.atan2(if_dz, if_dy)) % 360.0
                energy_mev = energy_kev / 1000.0
                ebin = bin_index(energy_mev, ENERGY_EDGES_MEV)
                mubin = bin_index(if_dx, MU_EDGES)
                azbin = bin_index(azimuth, AZ_EDGES_DEG)
                cube[(ebin, mubin, azbin)] += 1
                parsed += 1
                if current_event in selected_ids:
                    selected.append(
                        {
                            "source_file": str(path),
                            "local_event_id": current_event,
                            "init_x_cm": x,
                            "init_y_cm": y,
                            "init_z_cm": z,
                            "init_dir_x": dx,
                            "init_dir_y": dy,
                            "init_dir_z": dz,
                            "init_energy_keV": energy_kev,
                            "if_dir_x": if_dx,
                            "if_dir_y": if_dy,
                            "if_dir_z": if_dz,
                            "if_theta_from_plus_x_deg": theta,
                            "if_azimuth_about_x_deg": azimuth,
                            "energy_bin": ebin,
                            "mu_bin": mubin,
                            "azimuth_bin": azbin,
                        }
                    )

    return {
        "path": str(path),
        "declared_events": int(task["declared_events"]),
        "parsed_events": parsed,
        "geometry": geometry,
        "cube": [[*key, count] for key, count in cube.items()],
        "selected": selected,
    }


def cp_interval(k: int, n: int, alpha: float = 0.05) -> tuple[float, float, float]:
    if n <= 0:
        return math.nan, math.nan, math.nan
    lo = 0.0 if k == 0 else float(beta.ppf(alpha / 2.0, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1.0 - alpha / 2.0, k + 1, n - k))
    upper_one_sided = 1.0 if k == n else float(beta.ppf(1.0 - alpha, k + 1, n - k))
    return lo, hi, upper_one_sided


def edge_label(lo: float, hi: float, unit: str = "") -> str:
    hi_text = "inf" if math.isinf(hi) else f"{hi:g}"
    return f"[{lo:g},{hi_text}){unit}"


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--prompt-summary", type=Path, required=True)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    selected_by_path: dict[str, dict[int, dict]] = {}
    with args.prompt_summary.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["family"] != "gamma" or row["pass_veto50"] != "True":
                continue
            source = str(Path(row["source_file"]).resolve())
            selected_by_path.setdefault(source, {})[int(row["local_event_id"])] = row

    tasks = []
    total_tt_s = 0.0
    total_declared = 0
    with args.manifest.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if not (row["geometry"] == "S3d_O8" and row["family"] == "gamma" and row["mode"] == "instant"):
                continue
            path = (args.raw_root / row["sim_path"]).resolve()
            if not path.is_file():
                raise FileNotFoundError(path)
            declared = int(row["events"])
            tasks.append(
                {
                    "path": str(path),
                    "declared_events": declared,
                    "selected_ids": sorted(selected_by_path.get(str(path), {})),
                }
            )
            total_tt_s += float(row["TT_s"])
            total_declared += declared

    if not tasks:
        raise RuntimeError("No canonical S3d-O8 gamma/instant rows found")

    cube: Counter[tuple[int, int, int]] = Counter()
    selected_found: list[dict] = []
    bad_counts = []
    bad_geometry = []
    with ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(parse_one_shard, task) for task in tasks]
        for completed, future in enumerate(as_completed(futures), 1):
            result = future.result()
            if result["parsed_events"] != result["declared_events"]:
                bad_counts.append(
                    {
                        "path": result["path"],
                        "declared": result["declared_events"],
                        "parsed": result["parsed_events"],
                    }
                )
            if result["geometry"] != EXPECTED_GEOMETRY:
                bad_geometry.append({"path": result["path"], "geometry": result["geometry"]})
            for ebin, mubin, azbin, count in result["cube"]:
                cube[(ebin, mubin, azbin)] += count
            selected_found.extend(result["selected"])
            if completed == 1 or completed % 10 == 0 or completed == len(futures):
                print(f"parsed {completed}/{len(futures)} shards", flush=True)

    total_parsed = sum(cube.values())
    if bad_counts:
        raise RuntimeError(f"Declared/parsed history mismatch: {bad_counts[:5]}")
    if bad_geometry:
        raise RuntimeError(f"Geometry-header mismatch: {bad_geometry[:5]}")
    if total_parsed != total_declared:
        raise RuntimeError(f"Total mismatch: declared={total_declared}, parsed={total_parsed}")

    selected_flags: dict[tuple[int, int, int], dict[str, int]] = {}
    enriched_selected = []
    for found in selected_found:
        source = str(Path(found["source_file"]).resolve())
        event_id = int(found["local_event_id"])
        authority = selected_by_path[source][event_id]
        flags = selected_flags.setdefault(
            (int(found["energy_bin"]), int(found["mu_bin"]), int(found["azimuth_bin"])),
            {"veto_survivors": 0, "step05_survivors": 0},
        )
        flags["veto_survivors"] += 1
        flags["step05_survivors"] += int(authority["step05_pass"] == "True")
        found["pass_veto50"] = True
        found["step05_pass"] = authority["step05_pass"] == "True"
        found["step05_class"] = authority["step05_class"]
        found["event_weight_cps"] = float(authority["event_weight_cps"])
        enriched_selected.append(found)

    expected_selected = sum(len(events) for events in selected_by_path.values())
    if len(enriched_selected) != expected_selected:
        raise RuntimeError(f"Found {len(enriched_selected)}/{expected_selected} veto-surviving gamma events")

    weight_cps = 1.0 / total_tt_s
    energy_rows = []
    direction_rows = []
    for ebin in range(len(ENERGY_EDGES_MEV) - 1):
        n_energy = sum(cube[(ebin, mubin, azbin)] for mubin in range(4) for azbin in range(8))
        k_veto = sum(
            selected_flags.get((ebin, mubin, azbin), {}).get("veto_survivors", 0)
            for mubin in range(4)
            for azbin in range(8)
        )
        k_step05 = sum(
            selected_flags.get((ebin, mubin, azbin), {}).get("step05_survivors", 0)
            for mubin in range(4)
            for azbin in range(8)
        )
        lo, hi, up = cp_interval(k_step05, n_energy)
        energy_rows.append(
            {
                "energy_bin": ebin,
                "energy_range_MeV": edge_label(ENERGY_EDGES_MEV[ebin], ENERGY_EDGES_MEV[ebin + 1]),
                "incident_histories_N": n_energy,
                "incident_rate_cps": n_energy * weight_cps,
                "veto_survivors_k": k_veto,
                "step05_survivors_k": k_step05,
                "step05_leak_fraction": k_step05 / n_energy if n_energy else math.nan,
                "step05_leak_cp95_lo": lo,
                "step05_leak_cp95_hi": hi,
                "step05_leak_one_sided95_upper": up,
                "step05_w2_rate_cps": k_step05 * weight_cps,
            }
        )
        for mubin in range(4):
            for azbin in range(8):
                n = cube[(ebin, mubin, azbin)]
                flags = selected_flags.get((ebin, mubin, azbin), {})
                kv = flags.get("veto_survivors", 0)
                ks = flags.get("step05_survivors", 0)
                dlo, dhi, dup = cp_interval(ks, n)
                direction_rows.append(
                    {
                        "energy_bin": ebin,
                        "energy_range_MeV": edge_label(ENERGY_EDGES_MEV[ebin], ENERGY_EDGES_MEV[ebin + 1]),
                        "mu_bin": mubin,
                        "mu_range": edge_label(MU_EDGES[mubin], MU_EDGES[mubin + 1]),
                        "theta_x_range_deg": f"[{math.degrees(math.acos(MU_EDGES[mubin + 1])):.6g},{math.degrees(math.acos(MU_EDGES[mubin])):.6g}]",
                        "azimuth_bin": azbin,
                        "azimuth_range_deg": edge_label(AZ_EDGES_DEG[azbin], AZ_EDGES_DEG[azbin + 1]),
                        "solid_angle_sr": math.pi / 8.0,
                        "incident_histories_N": n,
                        "incident_rate_cps": n * weight_cps,
                        "veto_survivors_k": kv,
                        "step05_survivors_k": ks,
                        "step05_leak_fraction": ks / n if n else math.nan,
                        "step05_leak_cp95_lo": dlo,
                        "step05_leak_cp95_hi": dhi,
                        "step05_leak_one_sided95_upper": dup,
                        "step05_w2_rate_cps": ks * weight_cps,
                    }
                )

    write_csv(args.output_dir / "prompt_incident_energy_denominators.csv", list(energy_rows[0]), energy_rows)
    write_csv(args.output_dir / "prompt_incident_energy_direction_denominators.csv", list(direction_rows[0]), direction_rows)
    enriched_selected.sort(key=lambda row: int(row["local_event_id"]))
    write_csv(args.output_dir / "prompt_veto_survivors_verified.csv", list(enriched_selected[0]), enriched_selected)

    metadata = {
        "manifest": str(args.manifest.resolve()),
        "prompt_summary": str(args.prompt_summary.resolve()),
        "raw_root": str(args.raw_root.resolve()),
        "geometry_header_required": EXPECTED_GEOMETRY,
        "shards": len(tasks),
        "total_declared_histories": total_declared,
        "total_parsed_histories": total_parsed,
        "total_TT_s": total_tt_s,
        "canonical_event_weight_cps": weight_cps,
        "energy_edges_MeV": ["inf" if math.isinf(v) else v for v in ENERGY_EDGES_MEV],
        "mu_edges": MU_EDGES,
        "azimuth_edges_deg": AZ_EDGES_DEG,
        "direction_transform": "IF=(world_x-world_z, sqrt(2)*world_y, world_x+world_z)/sqrt(2)",
        "azimuth_definition": "atan2(IF_z, IF_y) mod 360 deg about IF +x",
        "each_direction_cell_solid_angle_sr": math.pi / 8.0,
        "veto_survivors": sum(row["veto_survivors_k"] for row in energy_rows),
        "step05_survivors": sum(row["step05_survivors_k"] for row in energy_rows),
        "step05_prompt_w2_cps": sum(row["step05_w2_rate_cps"] for row in energy_rows),
        "raw_files_copied": 0,
    }
    with (args.output_dir / "prompt_denominator_metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print(json.dumps(metadata, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
