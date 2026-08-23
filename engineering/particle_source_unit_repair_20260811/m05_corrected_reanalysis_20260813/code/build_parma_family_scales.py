#!/usr/bin/env python3
"""Build energy-integrated PARMA family scales for the retained 81-bin trajectory."""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import check_inputs


HERE = Path(__file__).resolve()
PACKAGE = HERE.parent.parent
ROOT = check_inputs.ROOT
TRAJECTORY = ROOT / "engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/fullchain/step06/atmosphere_transmission_511_by_time.csv"
OUTPUT = PACKAGE / "data/parma_energy_integrated_family_scales_81bins.csv"
SOURCE_CONTRACT = ROOT / "engineering/particle_source_unit_repair_20260811/data/source_contract_manifest.json"
PARMA_EXE = Path("/home/ubuntu/codex_tes_511_sim/COSMOSRAY_BALLOON_SIM/external/expacs_parma/phase2_parma_grid_driver")
PARMA_CWD = PARMA_EXE.parent / "parma_cpp"
FAMILIES = ("alpha", "eminus", "eplus", "gamma", "muminus", "muplus", "n", "p")
DELTA_OMEGA_SR = 2.0 * math.pi * 0.1
SOURCE_ENVIRONMENT = json.loads(SOURCE_CONTRACT.read_text(encoding="utf-8"))["source_model"]["environment"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def trapz(points: list[tuple[float, float]]) -> float:
    points.sort()
    return math.fsum(
        0.5 * (left[1] + right[1]) * (right[0] - left[0])
        for left, right in zip(points, points[1:])
    )


def evaluate(task: tuple[int, dict[str, str]]) -> dict[str, Any]:
    index, row = task
    year, month, day = (int(value) for value in SOURCE_ENVIRONMENT["date"].split("-"))
    command = [
        str(PARMA_EXE), str(year), str(month), str(day), str(row["latitude_deg"]), str(row["longitude_deg"]),
        str(row["altitude_km"]), "10.0",
    ]
    process = subprocess.run(command, cwd=PARMA_CWD, check=True, text=True, capture_output=True)
    lines = [line for line in process.stdout.splitlines() if line]
    meta = next(line for line in lines if line.startswith("META,")).split(",")
    start = next(i for i, line in enumerate(lines) if line.startswith("particle,"))
    spectra: defaultdict[tuple[str, int], list[tuple[float, float]]] = defaultdict(list)
    for item in csv.DictReader(lines[start:]):
        family = item["particle"]
        if family in FAMILIES:
            spectra[(family, int(item["angle_bin"]))].append(
                (float(item["energy_MeV"]), max(float(item["differential_flux_cm2_s_sr_MeV"]), 0.0))
            )
    flux = {
        family: math.fsum(trapz(spectra[(family, angle_bin)]) * DELTA_OMEGA_SR for angle_bin in range(20))
        for family in FAMILIES
    }
    return {
        "index": index, "time_bin_id": int(row["time_bin_id"]), "day_mid": float(row["day_mid"]),
        "altitude_km": float(row["altitude_km"]), "latitude_deg": float(row["latitude_deg"]),
        "longitude_deg": float(row["longitude_deg"]), "W_index": float(meta[1]),
        "Rc_GV_parma": float(meta[2]), "depth_g_cm2_parma": float(meta[3]), "flux": flux,
    }


def run(output: Path, workers: int) -> None:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    rows = read_csv(TRAJECTORY)
    results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(evaluate, task) for task in enumerate(rows)]
        for future in as_completed(futures):
            results.append(future.result())
            if len(results) % 8 == 0 or len(results) == len(rows):
                print(f"PARMA energy integration {len(results)}/{len(rows)}", flush=True)
    results.sort(key=lambda row: row["index"])
    reference_environment = {
        "latitude_deg": SOURCE_ENVIRONMENT["latitude_deg"],
        "longitude_deg": SOURCE_ENVIRONMENT["longitude_deg"],
        "altitude_km": SOURCE_ENVIRONMENT["altitude_km"],
        "time_bin_id": -1, "day_mid": -1.0,
    }
    reference = evaluate((-1, reference_environment))
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "time_bin_id", "day_mid", "altitude_km", "latitude_deg", "longitude_deg",
        "Rc_GV_parma", "depth_g_cm2_parma", "W_index",
        *(f"flux_{family}_cm2_s" for family in FAMILIES),
        *(f"scale_{family}_to_parma_reference" for family in FAMILIES),
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in results:
            record: dict[str, Any] = {name: row[name] for name in fields[:8]}
            for family in FAMILIES:
                record[f"flux_{family}_cm2_s"] = row["flux"][family]
                record[f"scale_{family}_to_parma_reference"] = row["flux"][family] / reference["flux"][family]
            writer.writerow(record)
    metadata = {
        "schema_version": 1,
        "status": "PASS__PARMA_ENERGY_INTEGRATED_81BIN_RELATIVE_SCALES",
        "trajectory": str(TRAJECTORY.relative_to(ROOT)),
        "driver": str(PARMA_EXE),
        "date": SOURCE_ENVIRONMENT["date"],
        "reference_environment": {
            **reference_environment,
            "parma_W_index": reference["W_index"],
            "parma_Rc_GV": reference["Rc_GV_parma"],
            "parma_depth_g_cm2": reference["depth_g_cm2_parma"],
        },
        "corrected_source_contract_environment": SOURCE_ENVIRONMENT,
        "normalization_boundary": (
            "Only PARMA family flux ratios to the 34N,100E,38km driver reference are used. "
            "The driver's absolute flux is not substituted for the corrected source-card flux."
        ),
        "known_model_difference": (
            f"The date-driven PARMA executable returns W={reference['W_index']}; "
            f"the retained corrected source contract records W={SOURCE_ENVIRONMENT['solar_modulation_w']}."
        ),
        "energy_integration": "trapezoidal dE within each of 20 equal-mu bins, then sum 2*pi*0.1",
        "workers": workers,
        "output": str(output.relative_to(ROOT)),
    }
    output.with_suffix(".json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{metadata['status']}: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    run(args.output.resolve(), args.workers)
