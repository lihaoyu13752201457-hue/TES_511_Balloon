#!/usr/bin/env python3
"""Read-only SE3 prompt-entry and delayed-activation origin analysis.

This adapter reuses the retained S3d IA-INIT outer-envelope classifier and the
SE3 keyed detector response.  It starts no transport and computes no large
artifact digest.  Outputs are compact review tables under this package.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import math
import pickle
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any


ROOT = Path("/home/ubuntu/TES_511_Balloon")
SE3_ROOT = Path(
    "/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/"
    "geometry_optimization_20260815/47_se3_plan1_transport_20260815"
)
ENTRY_AUTHORITY = Path(
    "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/"
    "geometry_optimization_20260704/40_s3c_mainline_lightweight_review_20260710/"
    "code/build_s3c_lightweight_analysis.py"
)
PACKAGE = ROOT / (
    "engineering/geometry_optimization_20260815/"
    "48_se3_background_optimization_review_20260816"
)
DATA = PACKAGE / "data"

PROMPT_CODE = SE3_ROOT / "code"
PROMPT_CATALOG = SE3_ROOT / "outputs/01_prompt/catalog/SE3"
DAY15_INVENTORY = SE3_ROOT / "outputs/02_activation/day15_inventory.csv"
SELECTED_LINEAGE = (
    SE3_ROOT / "outputs/04_common_response/selected_background_w2_lineage.csv"
)
DELAYED_CATALOG = SE3_ROOT / "outputs/03_delayed/catalog/SE3"
PARENT_COMPARISON = SE3_ROOT / "outputs/05_matched_comparison/parent_comparison.csv"

FAMILIES = ("p", "n", "alpha", "gamma", "eminus", "eplus", "muminus", "muplus")
WINDOWS = {
    "broad_480_550": (480.0, 550.0),
    "w2_510p58_511p42": (510.58, 511.42),
}


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def in_window(value: float, bounds: tuple[float, float]) -> bool:
    return bounds[0] <= value < bounds[1]


def rotate_y(values: tuple[float, float, float], angle_deg: float) -> tuple[float, float, float]:
    x, y, z = values
    angle = math.radians(angle_deg)
    cosine = math.cos(angle)
    sine = math.sin(angle)
    return cosine * x + sine * z, y, -sine * x + cosine * z


def scan_one_source(task: tuple[str, list[int]]) -> tuple[str, dict[int, dict[str, Any]]]:
    path_text, ids = task
    authority = load_module(
        f"se3_entry_authority_{abs(hash(path_text))}", ENTRY_AUTHORITY
    )
    path = Path(path_text)
    found = authority.scan_target_inits(path, set(ids))
    return path_text, {
        event_id: {**init, **authority.classify_entry(init)}
        for event_id, init in found.items()
    }


def prompt_entry_analysis() -> dict[str, Any]:
    sys.path.insert(0, str(PROMPT_CODE))
    import run_prompt_analysis as prompt  # type: ignore

    config = json.loads((SE3_ROOT / "analysis_inputs.json").read_text(encoding="utf-8"))
    core, step05, disk = prompt.response_runtime(config)

    event_rows: list[dict[str, Any]] = []
    targets: dict[str, set[int]] = defaultdict(set)
    for family in FAMILIES:
        with (PROMPT_CATALOG / f"{family}.pkl").open("rb") as handle:
            catalog = pickle.load(handle)
        for index in range(len(catalog["stream"])):
            event = prompt.evaluate_event(catalog, index, core, step05, disk)
            measured = float(event["measured_total_keV"])
            flags = {
                name: in_window(measured, bounds) for name, bounds in WINDOWS.items()
            }
            if not any(flags.values()):
                continue
            source_file = str(catalog["source_file"][index])
            local_id = int(catalog["local_id"][index])
            targets[source_file].add(local_id)
            event_rows.append({
                "family": family,
                "source_file": source_file,
                "local_event_id": local_id,
                "job_name": str(catalog["job_name"][index]),
                "transport_seed": int(catalog["seed"][index]),
                "event_weight_cps": float(catalog["cell_metadata"]["event_weight_cps"]),
                "measured_total_keV": measured,
                "raw_total_keV": float(event["raw_total_keV"]),
                "shield_keV": float(event["shield_keV"]),
                "plastic_keV": float(event["plastic_keV"]),
                "active_veto50_pass": bool(event["active_pass"][50.0]),
                "topology_pass": bool(event["topology_pass"]),
                **flags,
            })

    entry_by_source: dict[str, dict[int, dict[str, Any]]] = {}
    tasks = [(path, sorted(ids)) for path, ids in sorted(targets.items())]
    with ProcessPoolExecutor(max_workers=min(8, len(tasks))) as pool:
        futures = {pool.submit(scan_one_source, task): task[0] for task in tasks}
        for future in as_completed(futures):
            path, found = future.result()
            entry_by_source[path] = found

    for row in event_rows:
        row.update(entry_by_source[row["source_file"]][row["local_event_id"]])
    event_rows.sort(
        key=lambda row: (row["family"], row["source_file"], row["local_event_id"])
    )

    event_fields = [
        "family", "source_file", "local_event_id", "job_name", "transport_seed",
        "event_weight_cps", "measured_total_keV", "raw_total_keV", "shield_keV",
        "plastic_keV", "active_veto50_pass", "topology_pass", "broad_480_550",
        "w2_510p58_511p42", "init_x_cm", "init_y_cm", "init_z_cm", "dir_x",
        "dir_y", "dir_z", "init_energy_keV", "entry_surface", "entry_region",
        "entry_phi_deg_local", "entry_local_x_cm", "entry_local_y_cm",
        "entry_local_z_cm",
    ]
    write_csv(DATA / "prompt_entry_events.csv", event_rows, event_fields)

    summary_rows: list[dict[str, Any]] = []
    for window_id in WINDOWS:
        selected = [row for row in event_rows if row[window_id]]
        total_rate = math.fsum(float(row["event_weight_cps"]) for row in selected)
        groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in selected:
            groups[(row["family"], row["entry_surface"], row["entry_region"])].append(row)
        for (family, surface, region), rows in sorted(groups.items()):
            rate = math.fsum(float(row["event_weight_cps"]) for row in rows)
            veto_rows = [row for row in rows if row["active_veto50_pass"]]
            veto_rate = math.fsum(float(row["event_weight_cps"]) for row in veto_rows)
            summary_rows.append({
                "window_id": window_id,
                "family": family,
                "entry_surface": surface,
                "entry_region": region,
                "pre_veto_events": len(rows),
                "pre_veto_rate_cps": rate,
                "share_of_window_rate": rate / total_rate if total_rate else 0.0,
                "after_veto50_events": len(veto_rows),
                "after_veto50_rate_cps": veto_rate,
            })
    write_csv(
        DATA / "prompt_entry_summary.csv",
        summary_rows,
        [
            "window_id", "family", "entry_surface", "entry_region",
            "pre_veto_events", "pre_veto_rate_cps", "share_of_window_rate",
            "after_veto50_events", "after_veto50_rate_cps",
        ],
    )

    surface_rows: list[dict[str, Any]] = []
    for window_id in WINDOWS:
        selected = [row for row in event_rows if row[window_id]]
        total_rate = math.fsum(float(row["event_weight_cps"]) for row in selected)
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in selected:
            grouped[row["entry_surface"]].append(row)
        for surface, rows in sorted(grouped.items()):
            rate = math.fsum(float(row["event_weight_cps"]) for row in rows)
            surface_rows.append({
                "window_id": window_id,
                "entry_surface": surface,
                "pre_veto_events": len(rows),
                "pre_veto_rate_cps": rate,
                "share_of_window_rate": rate / total_rate if total_rate else 0.0,
                "after_veto50_events": sum(bool(row["active_veto50_pass"]) for row in rows),
                "after_veto50_rate_cps": math.fsum(
                    float(row["event_weight_cps"])
                    for row in rows if row["active_veto50_pass"]
                ),
            })
    write_csv(
        DATA / "prompt_entry_surface_summary.csv",
        surface_rows,
        [
            "window_id", "entry_surface", "pre_veto_events", "pre_veto_rate_cps",
            "share_of_window_rate", "after_veto50_events", "after_veto50_rate_cps",
        ],
    )
    return {
        "selected_catalog_events": len(event_rows),
        "source_files_scanned": len(tasks),
        "large_payload_hashes_computed": 0,
        "windows": {
            window_id: {
                "pre_veto_events": sum(row[window_id] for row in event_rows),
                "pre_veto_rate_cps": math.fsum(
                    float(row["event_weight_cps"]) for row in event_rows if row[window_id]
                ),
                "after_veto50_events": sum(
                    bool(row[window_id] and row["active_veto50_pass"]) for row in event_rows
                ),
                "after_veto50_rate_cps": math.fsum(
                    float(row["event_weight_cps"])
                    for row in event_rows if row[window_id] and row["active_veto50_pass"]
                ),
            }
            for window_id in WINDOWS
        },
    }


def activation_origin_analysis() -> dict[str, Any]:
    inventory = [
        row for row in read_csv(DAY15_INVENTORY)
        if row["geometry"] == "SE3" and row["source_disposition"] == "transported_ground_state"
    ]
    lineage = [
        row for row in read_csv(SELECTED_LINEAGE)
        if row["geometry"] == "SE3" and row["stream"] == "delayed"
    ]
    delayed_by_family: dict[str, dict[int, dict[str, Any]]] = {}
    for family in FAMILIES:
        path = DELAYED_CATALOG / f"{family}.pkl"
        if not path.is_file():
            continue
        with path.open("rb") as handle:
            catalog = pickle.load(handle)
        delayed_by_family[family] = {
            int(catalog["local_id"][index]): {
                "production_x_cm": float(catalog["production_x_cm"][index]),
                "production_y_cm": float(catalog["production_y_cm"][index]),
                "production_z_cm": float(catalog["production_z_cm"][index]),
            }
            for index in range(len(catalog["stream"]))
        }
    for row in lineage:
        origin = delayed_by_family[row["family"]][int(row["local_event_id"])]
        row.update(origin)
        local = rotate_y(
            (origin["production_x_cm"], origin["production_y_cm"], origin["production_z_cm"]),
            -45.0,
        )
        row.update({
            "production_local_x_cm": local[0],
            "production_local_y_cm": local[1],
            "production_local_z_cm": local[2],
        })
    write_csv(
        DATA / "selected_delayed_event_origins.csv",
        lineage,
        list(lineage[0]),
    )
    parent_labels = {
        row["source_parent"]: row["isotope_label"] for row in read_csv(PARENT_COMPARISON)
    }
    volume_material: dict[str, str] = {}
    for row in inventory:
        volume = row["source_volume"]
        material = row["material_category"]
        previous = volume_material.setdefault(volume, material)
        if previous != material:
            raise RuntimeError(f"material category drift for {volume}: {previous} vs {material}")

    dimensions = {
        "material": ("material_category", lambda row: row["material_category"]),
        "volume": ("source_volume", lambda row: row["source_volume"]),
        "parent": ("source_parent_ZA", lambda row: row["source_parent_ZA"]),
        "incident_family": ("incident_family", lambda row: row["incident_family"]),
    }
    total_activity = math.fsum(float(row["day15_activity_Bq"]) for row in inventory)
    total_selected = math.fsum(float(row["event_weight_cps"]) for row in lineage)
    output_counts: dict[str, int] = {}

    for name, (key_name, inventory_key) in dimensions.items():
        activity: dict[str, float] = defaultdict(float)
        state_rows: dict[str, int] = defaultdict(int)
        selected_rate: dict[str, float] = defaultdict(float)
        selected_weight_squares: dict[str, float] = defaultdict(float)
        selected_events: dict[str, int] = defaultdict(int)
        family_support: dict[str, set[str]] = defaultdict(set)
        parent_support: dict[str, set[str]] = defaultdict(set)
        volume_support: dict[str, set[str]] = defaultdict(set)
        selected_coordinates: dict[str, list[tuple[float, float, float, float]]] = defaultdict(list)
        selected_local_coordinates: dict[str, list[tuple[float, float, float, float]]] = defaultdict(list)

        for row in inventory:
            key = str(inventory_key(row))
            activity[key] += float(row["day15_activity_Bq"])
            state_rows[key] += 1
            family_support[key].add(row["incident_family"])
            parent_support[key].add(row["source_parent_ZA"])
            volume_support[key].add(row["source_volume"])
        for row in lineage:
            if name == "material":
                key = volume_material[row["source_volume"]]
            elif name == "volume":
                key = row["source_volume"]
            elif name == "parent":
                key = row["source_parent_ZA"]
            else:
                key = row["family"]
            selected_rate[key] += float(row["event_weight_cps"])
            selected_weight_squares[key] += float(row["event_weight_cps"]) ** 2
            selected_events[key] += 1
            selected_coordinates[key].append((
                float(row["production_x_cm"]),
                float(row["production_y_cm"]),
                float(row["production_z_cm"]),
                float(row["event_weight_cps"]),
            ))
            selected_local_coordinates[key].append((
                float(row["production_local_x_cm"]),
                float(row["production_local_y_cm"]),
                float(row["production_local_z_cm"]),
                float(row["event_weight_cps"]),
            ))

        keys = sorted(
            set(activity) | set(selected_rate),
            key=lambda key: (-selected_rate[key], -activity[key], key),
        )
        rows: list[dict[str, Any]] = []
        for key in keys:
            a15 = activity[key]
            rate = selected_rate[key]
            variance = selected_weight_squares[key]
            coords = selected_coordinates[key]
            local_coords = selected_local_coordinates[key]
            coord_weight = math.fsum(value[3] for value in coords)
            row = {
                key_name: key,
                "isotope_label": parent_labels.get(key, "") if name == "parent" else "",
                "transported_state_rows": state_rows[key],
                "transported_day15_activity_Bq": a15,
                "activity_share": a15 / total_activity if total_activity else 0.0,
                "selected_W2_events": selected_events[key],
                "selected_W2_rate_cps": rate,
                "selected_W2_stat_sigma_cps": math.sqrt(variance),
                "selected_W2_Neff": rate * rate / variance if variance else 0.0,
                "selected_rate_share": rate / total_selected if total_selected else 0.0,
                "selected_cps_per_Bq": rate / a15 if a15 else "",
                "incident_family_support": ";".join(sorted(family_support[key])),
                "parent_support_count": len(parent_support[key]),
                "volume_support_count": len(volume_support[key]),
                "selected_production_x_weighted_cm": (
                    math.fsum(value[0] * value[3] for value in coords) / coord_weight
                    if coord_weight else ""
                ),
                "selected_production_y_weighted_cm": (
                    math.fsum(value[1] * value[3] for value in coords) / coord_weight
                    if coord_weight else ""
                ),
                "selected_production_z_weighted_cm": (
                    math.fsum(value[2] * value[3] for value in coords) / coord_weight
                    if coord_weight else ""
                ),
                "selected_production_local_x_weighted_cm": (
                    math.fsum(value[0] * value[3] for value in local_coords) / coord_weight
                    if coord_weight else ""
                ),
                "selected_production_local_y_weighted_cm": (
                    math.fsum(value[1] * value[3] for value in local_coords) / coord_weight
                    if coord_weight else ""
                ),
                "selected_production_local_z_weighted_cm": (
                    math.fsum(value[2] * value[3] for value in local_coords) / coord_weight
                    if coord_weight else ""
                ),
            }
            rows.append(row)
        fields = [
            key_name, "isotope_label", "transported_state_rows",
            "transported_day15_activity_Bq", "activity_share", "selected_W2_events",
            "selected_W2_rate_cps", "selected_W2_stat_sigma_cps", "selected_W2_Neff",
            "selected_rate_share", "selected_cps_per_Bq",
            "incident_family_support", "parent_support_count", "volume_support_count",
            "selected_production_x_weighted_cm", "selected_production_y_weighted_cm",
            "selected_production_z_weighted_cm",
            "selected_production_local_x_weighted_cm",
            "selected_production_local_y_weighted_cm",
            "selected_production_local_z_weighted_cm",
        ]
        write_csv(DATA / f"activation_origin_by_{name}.csv", rows, fields)
        output_counts[name] = len(rows)

    return {
        "transported_day15_activity_Bq": total_activity,
        "selected_delayed_W2_events": len(lineage),
        "selected_delayed_W2_rate_cps": total_selected,
        "output_row_counts": output_counts,
    }


def sensitivity_scenarios() -> dict[str, Any]:
    baseline = {
        "B20_counts": 98_257.66905,
        "S20_counts": 1_279.288658,
        "Z20": 4.081175,
        "F3_ph_cm2_s": 7.350822463e-5,
        "signal_Aeff_cm2": 11.69478,
    }
    reductions = (0.0, 0.25, 0.40, 0.50, 0.60, 0.65, 0.70, 0.7883, 0.9299)
    rows: list[dict[str, Any]] = []
    for reduction in reductions:
        for retention in (1.0, 0.98):
            background = baseline["B20_counts"] * (1.0 - reduction)
            signal = baseline["S20_counts"] * retention
            z20 = signal / math.sqrt(background)
            f3 = 1.0e-4 * 3.0 / z20
            rows.append({
                "background_reduction_fraction": reduction,
                "signal_Aeff_retention_fraction": retention,
                "B20_counts": background,
                "S20_counts": signal,
                "Z20": z20,
                "F3_ph_cm2_s": f3,
                "F3_ratio_to_SE3": f3 / baseline["F3_ph_cm2_s"],
            })
    write_csv(
        DATA / "optimization_sensitivity_scenarios.csv",
        rows,
        [
            "background_reduction_fraction", "signal_Aeff_retention_fraction",
            "B20_counts", "S20_counts", "Z20", "F3_ph_cm2_s", "F3_ratio_to_SE3",
        ],
    )
    return {"baseline": baseline, "scenario_rows": len(rows)}


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    prompt = prompt_entry_analysis()
    activation = activation_origin_analysis()
    sensitivity = sensitivity_scenarios()
    summary = {
        "status": "PASS__SE3_BACKGROUND_ORIGIN_REVIEW_TABLES",
        "scope": "read-only derived analysis; no transport; no large-payload digest",
        "prompt": prompt,
        "activation": activation,
        "sensitivity": sensitivity,
        "methods": {
            "prompt_response": str(SE3_ROOT / "code/run_prompt_analysis.py"),
            "entry_classifier": str(ENTRY_AUTHORITY),
            "activation_inventory": str(DAY15_INVENTORY),
            "selected_lineage": str(SELECTED_LINEAGE),
        },
    }
    write_json(DATA / "analysis_summary.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
