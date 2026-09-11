#!/usr/bin/env python3
"""Recover volume/material origins for OptV3 delayed W2-final survivors."""
from __future__ import annotations

import concurrent.futures
import csv
import gzip
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path("/home/ubuntu/TES_511_Balloon")
PACKAGE = ROOT / "engineering/geometry_optimization_20260815/63_m05new_sg3b_signal_statistics_20260820"
JOB_CATALOGS = ROOT / "DEEPSEEK_CODE/outputs/04_event_catalog_step05_m05_fixed_20260820/job_catalogs"
ACTIVATION = Path("/mnt/data/TES_Balloon_511_data/SH3/sh3_optv3_m05_delayed_activation_v1/generated/activation/manifest.json")
GEOMETRY_DIR = Path("/home/ubuntu/.codex/worktrees/e3cf/TES_511_Balloon/engineering/geometry_optimization_20260815/sh3/assembly_opt_v3/geometry")
OUT = PACKAGE / "outputs/05_optv3_delayed_origins"
FINAL_BIT = 1 << 4
ID_RE = re.compile(r"^ID\s+(\d+)\s+\d+")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def material_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    pattern = re.compile(r"^([A-Za-z0-9_]+)\.Material\s+(\S+)\s*$")
    for path in GEOMETRY_DIR.glob("*.geo"):
        for line in path.read_text(encoding="utf-8", errors="strict").splitlines():
            match = pattern.match(line.strip())
            if not match:
                continue
            volume, material = match.groups()
            old = mapping.setdefault(volume, material)
            if old != material:
                raise RuntimeError(f"material differs for {volume}: {old} vs {material}")
    return mapping


def family_positions() -> dict[str, Path]:
    manifest = load_json(ACTIVATION)
    return {row["family"]: Path(row["positions_path"]) for row in manifest["source_cells"]}


def locator(path: Path) -> dict[str, Any]:
    unique: dict[tuple[float, float, float], tuple[str, int, float]] = {}
    selected = 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if int(row["sample_index"]) % 5:
                continue
            selected += 1
            xyz = (float(row["x_cm"]), float(row["y_cm"]), float(row["z_cm"]))
            value = (row["volume"], int(row["ZA"]), float(row["excitation_keV"]))
            old = unique.setdefault(xyz, value)
            if old != value:
                raise RuntimeError(f"ambiguous source position: {xyz}")
    if selected != 10_000:
        raise RuntimeError(f"stride-5 support != 10,000: {path}")
    coordinates = np.asarray(list(unique), dtype=np.float64)
    return {"tree": cKDTree(coordinates), "metadata": list(unique.values())}


def locate(loc: dict[str, Any], xyz: tuple[float, float, float]) -> tuple[tuple[str, int, float], float]:
    count = len(loc["metadata"])
    k = min(8, count)
    second = math.inf
    while True:
        distances, neighbors = loc["tree"].query(np.asarray(xyz), k=k, p=np.inf, workers=1)
        distance_values = np.atleast_1d(distances)
        neighbor_values = np.atleast_1d(neighbors)
        nearest = float(distance_values[0])
        chosen = loc["metadata"][int(neighbor_values[0])]
        for distance, neighbor in zip(distance_values[1:], neighbor_values[1:]):
            if loc["metadata"][int(neighbor)] != chosen:
                second = float(distance)
                break
        if math.isfinite(second) or k == count:
            break
        k = min(k * 2, count)
    if not (nearest <= 1.0e-3 and second - nearest >= 1.102e-5 and second >= 2.0 * max(nearest, 1.0e-30)):
        raise RuntimeError(f"source position is not unique: nearest={nearest}, second={second}")
    return chosen, nearest


def selected_job(meta_path: Path, positions: dict[str, Path]) -> list[dict[str, Any]]:
    meta = load_json(meta_path)
    if meta.get("stream") != "delayed":
        return []
    family = meta["family"]
    npz_path = Path(meta["catalog_path"])
    with np.load(npz_path, allow_pickle=False) as data:
        mask = (data["w2_flags"] & FINAL_BIT) != 0
        selected_ids = data["event_id"][mask].astype(int)
        selected_za = data["source_za"][mask].astype(int)
    wanted = {int(event_id): int(za) for event_id, za in zip(selected_ids, selected_za)}
    if not wanted:
        return []
    loc = locator(positions[family])
    rows = []
    current_id = None
    with gzip.open(meta["sim_path"], "rt", encoding="utf-8", errors="strict") as handle:
        for raw in handle:
            line = raw.strip()
            match = ID_RE.match(line)
            if match:
                current_id = int(match.group(1))
                continue
            if current_id not in wanted or not line.startswith("IA INIT"):
                continue
            fields = [value.strip() for value in line.split(";")]
            xyz = (float(fields[4]), float(fields[5]), float(fields[6]))
            init_za = int(fields[15])
            (volume, source_za, excitation), distance = locate(loc, xyz)
            if source_za != wanted[current_id]:
                raise RuntimeError(f"catalog/source ZA differs for {meta['job_id']} event {current_id}")
            rows.append({
                "job_id": meta["job_id"], "family": family,
                "event_id": current_id, "source_parent_ZA": source_za,
                "IA_INIT_ZA": init_za, "excitation_keV": excitation,
                "source_volume": volume,
                "x_cm": xyz[0], "y_cm": xyz[1], "z_cm": xyz[2],
                "position_match_distance_cm": distance,
                "day15_event_weight_cps": float(meta["weight_cps"]),
            })
            del wanted[current_id]
            current_id = None
    if wanted:
        raise RuntimeError(f"missing selected INIT records for {meta['job_id']}: {len(wanted)}")
    return rows


def main() -> None:
    positions = family_positions()
    meta_paths = []
    for path in sorted(JOB_CATALOGS.glob("*.json")):
        meta = load_json(path)
        if meta.get("stream") == "delayed":
            meta_paths.append(path)
    all_rows = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(selected_job, path, positions): path for path in meta_paths}
        for future in concurrent.futures.as_completed(futures):
            rows = future.result()
            all_rows.extend(rows)
            print(json.dumps({"job": futures[future].name, "selected": len(rows)}), flush=True)
    all_rows.sort(key=lambda row: (row["family"], row["job_id"], int(row["event_id"])))
    materials = material_map()
    missing_materials = sorted({row["source_volume"] for row in all_rows if row["source_volume"] not in materials})
    if missing_materials:
        raise RuntimeError(f"source-volume material mapping missing: {missing_materials}")
    for row in all_rows:
        row["source_material"] = materials[row["source_volume"]]

    grouped: dict[tuple[str, str, str, int], dict[str, Any]] = defaultdict(
        lambda: {"raw_selected": 0, "day15_rate_cps": 0.0}
    )
    for row in all_rows:
        key = (row["source_material"], row["source_volume"], row["family"], int(row["source_parent_ZA"]))
        grouped[key]["raw_selected"] += 1
        grouped[key]["day15_rate_cps"] += float(row["day15_event_weight_cps"])
    total_rate = math.fsum(float(row["day15_event_weight_cps"]) for row in all_rows)
    groups = []
    for key, value in sorted(grouped.items(), key=lambda item: -float(item[1]["day15_rate_cps"])):
        material, volume, family, za = key
        groups.append({
            "source_material": material, "source_volume": volume,
            "family": family, "source_parent_ZA": za,
            "raw_selected": value["raw_selected"],
            "day15_rate_cps": value["day15_rate_cps"],
            "fraction_of_delayed_W2_final": value["day15_rate_cps"] / total_rate if total_rate else 0.0,
        })
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "optv3_delayed_selected_events.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(all_rows[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(all_rows)
    with (OUT / "optv3_delayed_origin_breakdown.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(groups[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(groups)
    summary = {
        "schema_version": 1,
        "status": "PASS__EXACT_POSITION_VOLUME_MATERIAL_CLOSED",
        "selected_events": len(all_rows),
        "delayed_W2_final_day15_rate_cps": total_rate,
        "groups": len(groups),
        "max_position_match_distance_cm": max(float(row["position_match_distance_cm"]) for row in all_rows),
        "source_parent_ZA_mismatch_events": sum(int(row["IA_INIT_ZA"]) != int(row["source_parent_ZA"]) for row in all_rows),
        "top_groups": groups[:20],
        "authority": {
            "catalogs": str(JOB_CATALOGS),
            "activation_manifest": str(ACTIVATION),
            "geometry_directory": str(GEOMETRY_DIR),
        },
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
