#!/usr/bin/env python3
"""Stream the complete S3d-O8 prompt-gamma SIM denominator.

This intentionally reads only ``ID`` and ``IA INIT`` records from the raw SIM
files.  No SIM file is copied and no event catalog (which is TES-positive only)
is used as the incident denominator.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from scipy.stats import beta


ENERGY_EDGES_KEV = (0, 1000, 2000, 3000, 4000, 5000, 6000, 8000, 10000, 20000, math.inf)
MU_X_EDGES = (-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0000001)
AZ_EDGES_DEG = (0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0, 360.0)


def bin_index(value: float, edges: tuple[float, ...]) -> int:
    for i, hi in enumerate(edges[1:]):
        if value < hi:
            return i
    return len(edges) - 2


def parse_init(line: str) -> tuple[float, float, float, float, float, float, float]:
    fields = [v.strip() for v in line[len("IA INIT") :].split(";")]
    if len(fields) != 23 or int(fields[15]) != 1:
        raise ValueError(f"unexpected IA INIT layout: {line.rstrip()}")
    return tuple(float(fields[i]) for i in (4, 5, 6, 16, 17, 18, 22))  # type: ignore[return-value]


def transformed_direction(dx: float, dy: float, dz: float) -> tuple[float, float, float, float, float]:
    # Canonical S3d InstrumentFrame.Rotation is 0 45 0.  Inverting the
    # placement rotation maps World -> InstrumentFrame as follows.
    c = math.sqrt(0.5)
    x_if, y_if, z_if = c * (dx - dz), dy, c * (dx + dz)
    norm = math.sqrt(x_if * x_if + y_if * y_if + z_if * z_if)
    x_if, y_if, z_if = x_if / norm, y_if / norm, z_if / norm
    az = math.degrees(math.atan2(z_if, y_if)) % 360.0
    theta = math.degrees(math.acos(max(-1.0, min(1.0, x_if))))
    return x_if, y_if, z_if, theta, az


def process_sim(task: tuple[str, dict[int, tuple[int, int, int]]]) -> dict:
    sim_path, labels = task
    counts: Counter[tuple[int, int, int, str]] = Counter()
    selected = []
    current_id: int | None = None
    n_id = n_init = 0
    with gzip.open(sim_path, "rt", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if line.startswith("ID "):
                current_id = int(line.split()[1])
                n_id += 1
            elif line.startswith("IA INIT"):
                if current_id is None:
                    raise ValueError(f"INIT before ID in {sim_path}")
                x, y, z, dx, dy, dz, energy = parse_init(line)
                x_if, y_if, z_if, theta, az = transformed_direction(dx, dy, dz)
                cell = (
                    bin_index(energy, ENERGY_EDGES_KEV),
                    bin_index(x_if, MU_X_EDGES),
                    bin_index(az, AZ_EDGES_DEG),
                )
                counts[cell + ("incident",)] += 1
                pre, veto, step05 = labels.get(current_id, (0, 0, 0))
                if pre:
                    counts[cell + ("pre_w2",)] += 1
                if veto:
                    counts[cell + ("veto_leak",)] += 1
                if step05:
                    counts[cell + ("step05",)] += 1
                if pre:
                    selected.append(
                        {
                            "sim_path": sim_path,
                            "local_event_id": current_id,
                            "energy_keV": energy,
                            "world_x_cm": x,
                            "world_y_cm": y,
                            "world_z_cm": z,
                            "world_dx": dx,
                            "world_dy": dy,
                            "world_dz": dz,
                            "if_dx": x_if,
                            "if_dy": y_if,
                            "if_dz": z_if,
                            "if_theta_from_plus_x_deg": theta,
                            "if_azimuth_about_x_deg": az,
                            "energy_bin": cell[0],
                            "mu_x_bin": cell[1],
                            "azimuth_bin": cell[2],
                            "pre_w2": pre,
                            "veto_leak": veto,
                            "step05": step05,
                        }
                    )
                n_init += 1
    if n_id != n_init:
        raise ValueError(f"ID/INIT mismatch for {sim_path}: {n_id}/{n_init}")
    return {"path": sim_path, "n": n_init, "counts": dict(counts), "selected": selected}


def cp_upper_onesided(k: int, n: int, confidence: float = 0.95) -> float:
    if n <= 0:
        return math.nan
    if k >= n:
        return 1.0
    return float(beta.ppf(confidence, k + 1, n - k))


def edge_text(v: float) -> str:
    return "inf" if math.isinf(v) else f"{v:g}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--w2-events", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path("/home/ubuntu/TES_511_Balloon"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()

    jobs = []
    with args.manifest.open(newline="") as stream:
        for row in csv.DictReader(stream):
            if row["geometry"] == "S3d_O8" and row["family"] == "gamma" and row["mode"] == "instant":
                jobs.append(row)
    if not jobs:
        raise SystemExit("no S3d_O8/instant/gamma rows")

    sim_paths = [(args.repo_root / row["sim_path"]).resolve() for row in jobs]
    if len(sim_paths) != len(set(sim_paths)):
        raise SystemExit("duplicate SIM paths in manifest")
    missing = [str(p) for p in sim_paths if not p.is_file()]
    if missing:
        raise SystemExit(f"missing {len(missing)} SIM paths; first={missing[0]}")

    labels_by_path: dict[str, dict[int, tuple[int, int, int]]] = {}
    with args.w2_events.open(newline="") as stream:
        for row in csv.DictReader(stream):
            if row["family"] != "gamma":
                continue
            path = str(Path(row["source_file"]).resolve())
            event_id = int(row["local_event_id"])
            labels_by_path.setdefault(path, {})[event_id] = (
                1,
                int(row["pass_veto50"] == "True"),
                int(row["step05_pass"] == "True"),
            )

    task_paths = {str(p) for p in sim_paths}
    unknown_label_paths = sorted(set(labels_by_path) - task_paths)
    if unknown_label_paths:
        raise SystemExit(f"W2 labels refer to SIM outside manifest: {unknown_label_paths[0]}")

    aggregate: Counter[tuple[int, int, int, str]] = Counter()
    selected: list[dict] = []
    n_actual = 0
    tasks = [(str(p), labels_by_path.get(str(p), {})) for p in sim_paths]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(process_sim, tasks):
            n_actual += result["n"]
            aggregate.update(result["counts"])
            selected.extend(result["selected"])

    n_manifest = sum(int(row["events"]) for row in jobs)
    tt_s = sum(float(row["TT_s"]) for row in jobs)
    if n_actual != n_manifest:
        raise SystemExit(f"manifest/raw event mismatch: {n_manifest}/{n_actual}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    cell_path = args.output_dir / "incident_gamma_E_mux_az_denominator.csv"
    fieldnames = [
        "energy_lo_keV", "energy_hi_keV", "mu_x_lo", "mu_x_hi", "azimuth_lo_deg", "azimuth_hi_deg",
        "n_incident", "n_pre_w2", "n_veto_leak", "n_step05", "incident_rate_cps", "veto_leak_rate_cps",
        "veto_leak_probability", "veto_leak_probability_upper95_onesided",
    ]
    with cell_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for ie in range(len(ENERGY_EDGES_KEV) - 1):
            for im in range(len(MU_X_EDGES) - 1):
                for ia in range(len(AZ_EDGES_DEG) - 1):
                    n = aggregate[(ie, im, ia, "incident")]
                    if n == 0:
                        continue
                    k = aggregate[(ie, im, ia, "veto_leak")]
                    writer.writerow({
                        "energy_lo_keV": edge_text(ENERGY_EDGES_KEV[ie]),
                        "energy_hi_keV": edge_text(ENERGY_EDGES_KEV[ie + 1]),
                        "mu_x_lo": MU_X_EDGES[im], "mu_x_hi": MU_X_EDGES[im + 1],
                        "azimuth_lo_deg": AZ_EDGES_DEG[ia], "azimuth_hi_deg": AZ_EDGES_DEG[ia + 1],
                        "n_incident": n,
                        "n_pre_w2": aggregate[(ie, im, ia, "pre_w2")],
                        "n_veto_leak": k,
                        "n_step05": aggregate[(ie, im, ia, "step05")],
                        "incident_rate_cps": n / tt_s,
                        "veto_leak_rate_cps": k / tt_s,
                        "veto_leak_probability": k / n,
                        "veto_leak_probability_upper95_onesided": cp_upper_onesided(k, n),
                    })

    cell_n = {(ie, im, ia): aggregate[(ie, im, ia, "incident")]
              for ie in range(len(ENERGY_EDGES_KEV) - 1)
              for im in range(len(MU_X_EDGES) - 1)
              for ia in range(len(AZ_EDGES_DEG) - 1)}
    selected.sort(key=lambda row: (row["veto_leak"], row["step05"], row["sim_path"], row["local_event_id"]), reverse=True)
    for row in selected:
        key = (row["energy_bin"], row["mu_x_bin"], row["azimuth_bin"])
        row["n_incident_same_cell"] = cell_n[key]
        row["n_veto_leak_same_cell"] = aggregate[key + ("veto_leak",)]
        row["veto_leak_probability_same_cell"] = row["n_veto_leak_same_cell"] / row["n_incident_same_cell"]
        row["veto_leak_probability_upper95_same_cell"] = cp_upper_onesided(
            row["n_veto_leak_same_cell"], row["n_incident_same_cell"]
        )
    selected_path = args.output_dir / "pre_w2_gamma_events_with_denominator.csv"
    with selected_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(selected[0]))
        writer.writeheader()
        writer.writerows(selected)

    summary = {
        "geometry": "S3d_O8",
        "family": "gamma",
        "mode": "instant",
        "n_jobs": len(jobs),
        "n_manifest": n_manifest,
        "n_raw_init": n_actual,
        "TT_s": tt_s,
        "event_weight_cps": 1.0 / tt_s,
        "n_pre_w2": sum(v for key, v in aggregate.items() if key[-1] == "pre_w2"),
        "n_veto_leak": sum(v for key, v in aggregate.items() if key[-1] == "veto_leak"),
        "n_step05": sum(v for key, v in aggregate.items() if key[-1] == "step05"),
        "overall_veto_leak_probability": sum(v for key, v in aggregate.items() if key[-1] == "veto_leak") / n_actual,
        "overall_veto_leak_probability_upper95_onesided": cp_upper_onesided(
            sum(v for key, v in aggregate.items() if key[-1] == "veto_leak"), n_actual
        ),
        "energy_edges_keV": [edge_text(v) for v in ENERGY_EDGES_KEV],
        "mu_x_edges": MU_X_EDGES,
        "azimuth_edges_deg": AZ_EDGES_DEG,
        "denominator_source": "one IA INIT per event in every manifest-listed raw SIM",
        "cell_csv": str(cell_path),
        "selected_csv": str(selected_path),
    }
    (args.output_dir / "gamma_denominator_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
