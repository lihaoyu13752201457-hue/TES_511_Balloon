#!/usr/bin/env python3
"""Prepare deterministic, staged per-HIT inputs for the SH3 G4CMP driver.

The script consumes only outputs/unvetoed_events.{json,csv}.  It writes four
plain CSV inputs (one row per Si energy deposit) and a hash-pinned manifest.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable


SOURCE_SHA256 = {
    "outputs/unvetoed_events.json":
        "ad1410863bb46e70061fa0c6f86bf425d4ff6df0a3e513e4beab041cbafd95c7",
    "outputs/unvetoed_events.csv":
        "bd5c36f9c5e135381d460e09e492fcc4946ccbc8425945c3bd06b4ffc5f47b93",
}

POINT_ENERGIES_KEV = (30.0, 140.0, 500.0, 568.0, 1407.0)
POINT_POSITIONS_YZ_MM = (
    ("center", 0.0, 0.0),
    ("edge", 17.0, 0.0),
)
POINT_DEPTHS_X_MM = (
    ("front", -0.10),
    ("middle", 0.0),
    ("back", 0.10),
)
SLAB_HALF_EXTENTS_MM = (0.15, 18.0, 18.0)
POINT_TEMPLATE_LAYER = 0

CSV_FIELDS = [
    "group", "group_event_index", "group_hit_index", "input_event_key",
    "synthetic", "synthetic_point_id", "source_event_order",
    "original_sample_id", "original_job_id", "original_event_id",
    "candidate", "strict_recoil_event", "layer", "event_si_total_keV",
    "event_tes_direct_keV", "event_bgo_total_keV", "hit_time_s",
    "hit_time_ns", "hit_time_relative_ns", "local_x_mm", "local_y_mm",
    "local_z_mm", "energy_keV", "global_x_cm", "global_y_cm",
    "global_z_cm", "secondary", "parent", "step_process",
    "creation_process", "is_si_elastic_recoil", "original_source_csv_row",
]

STAGE_SPECS = (
    (1, "point_validation", "outputs/g4cmp_inputs/01_point_validation.csv"),
    (2, "exact_ABC", "outputs/g4cmp_inputs/02_exact_ABC.csv"),
    (3, "strict51", "outputs/g4cmp_inputs/03_strict51.csv"),
    (4, "all86", "outputs/g4cmp_inputs/04_all86.csv"),
)


def die(message: str) -> None:
    raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def close(a: float, b: float, *, abs_tol: float = 2e-6) -> bool:
    return math.isclose(a, b, rel_tol=2e-10, abs_tol=abs_tol)


def verified_source(root: Path) -> tuple[dict[str, Any], list[dict[str, str]], dict[str, Any]]:
    resolved_root = root.resolve(strict=True)
    source_meta: dict[str, Any] = {}
    paths: dict[str, Path] = {}
    for rel, expected in SOURCE_SHA256.items():
        path = (resolved_root / rel).resolve(strict=True)
        try:
            path.relative_to(resolved_root)
        except ValueError:
            die(f"refusing source outside workspace: {path}")
        actual = sha256(path)
        if actual != expected:
            die(f"SHA-256 mismatch for {rel}: expected {expected}, got {actual}")
        paths[rel] = path
        source_meta[rel] = {
            "bytes": path.stat().st_size,
            "sha256": actual,
            "matches_pinned_sha256": True,
        }

    with paths["outputs/unvetoed_events.json"].open(encoding="utf-8") as handle:
        catalog = json.load(handle)
    if catalog.get("status") != "PASS__86_UNVETOED_SI_EVENTS_EXTRACTED":
        die("unvetoed JSON does not have the required PASS status")
    if not catalog.get("self_checks", {}).get("all_required_checks_pass"):
        die("unvetoed JSON self-checks are not PASS")

    with paths["outputs/unvetoed_events.csv"].open(
        newline="", encoding="utf-8"
    ) as handle:
        source_csv_rows = list(csv.DictReader(handle))
    if len(source_csv_rows) != 327:
        die(f"expected 327 flat source HIT rows, got {len(source_csv_rows)}")
    return catalog, source_csv_rows, source_meta


def crosscheck_json_csv(catalog: dict[str, Any], csv_rows: list[dict[str, str]]) -> None:
    json_hits: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for event in catalog["events"]:
        for hit in event["hits"]:
            json_hits.append((event, hit))
    if len(json_hits) != len(csv_rows):
        die("nested JSON/flat CSV HIT-count mismatch")
    for n, ((event, hit), row) in enumerate(zip(json_hits, csv_rows), start=1):
        identity_json = (
            event["sample_id"], event["job_id"], event["event_id"],
            event["event_order"], hit["hit_order"], hit["source_csv_row"],
        )
        identity_csv = (
            row["sample_id"], row["job_id"], int(row["event_id"]),
            int(row["event_order"]), int(row["hit_order"]),
            int(row["source_csv_row"]),
        )
        if identity_json != identity_csv:
            die(f"nested JSON/flat CSV identity mismatch at flattened row {n}")
        numeric_pairs = [
            (hit["edep_keV"], float(row["edep_keV"])),
            (hit["time_s"], float(row["time_s"])),
            *zip(
                hit["slab_local_position_mm"],
                (
                    float(row["slab_local_x_mm"]),
                    float(row["slab_local_y_mm"]),
                    float(row["slab_local_z_mm"]),
                ),
            ),
        ]
        if not all(close(float(a), float(b), abs_tol=1e-12) for a, b in numeric_pairs):
            die(f"nested JSON/flat CSV numeric mismatch at flattened row {n}")


def event_key(event: dict[str, Any]) -> str:
    return f"{event['sample_id']}|{event['job_id']}|{event['event_id']}"


def real_event_rows(
    group: str, events: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    rows: list[dict[str, Any]] = []
    expected_energy: dict[str, float] = {}
    for group_event_index, event in enumerate(events, start=1):
        key = event_key(event)
        expected_energy[key] = float(event["si_total_keV"])
        first_time_ns = min(float(hit["time_ns"]) for hit in event["hits"])
        for group_hit_index, hit in enumerate(event["hits"], start=1):
            local = hit["slab_local_position_mm"]
            global_position = hit["global_position_cm"]
            rows.append({
                "group": group,
                "group_event_index": group_event_index,
                "group_hit_index": group_hit_index,
                "input_event_key": key,
                "synthetic": 0,
                "synthetic_point_id": "",
                "source_event_order": event["event_order"],
                "original_sample_id": event["sample_id"],
                "original_job_id": event["job_id"],
                "original_event_id": event["event_id"],
                "candidate": event["candidate"] or "",
                "strict_recoil_event": int(event["strict_recoil_event"]),
                "layer": hit["layer"],
                "event_si_total_keV": event["si_total_keV"],
                "event_tes_direct_keV": event["tes_total_keV"],
                "event_bgo_total_keV": event["bgo_total_keV"],
                "hit_time_s": hit["time_s"],
                "hit_time_ns": hit["time_ns"],
                "hit_time_relative_ns": float(hit["time_ns"]) - first_time_ns,
                "local_x_mm": local[0],
                "local_y_mm": local[1],
                "local_z_mm": local[2],
                "energy_keV": hit["edep_keV"],
                "global_x_cm": global_position[0],
                "global_y_cm": global_position[1],
                "global_z_cm": global_position[2],
                "secondary": hit["secondary"],
                "parent": hit["parent"],
                "step_process": hit["step_process"],
                "creation_process": hit["creation_process"],
                "is_si_elastic_recoil": int(hit["is_si_elastic_recoil"]),
                "original_source_csv_row": hit["source_csv_row"],
            })
    return rows, expected_energy


def point_rows() -> tuple[list[dict[str, Any]], dict[str, float]]:
    rows: list[dict[str, Any]] = []
    expected_energy: dict[str, float] = {}
    event_index = 0
    for energy_keV in POINT_ENERGIES_KEV:
        energy_label = str(int(energy_keV))
        for position_label, y_mm, z_mm in POINT_POSITIONS_YZ_MM:
            for depth_label, x_mm in POINT_DEPTHS_X_MM:
                event_index += 1
                point_id = f"E{energy_label}_{position_label}_{depth_label}"
                if not all(
                    abs(value) < bound
                    for value, bound in zip(
                        (x_mm, y_mm, z_mm), SLAB_HALF_EXTENTS_MM
                    )
                ):
                    die(f"synthetic point is not strictly inside slab: {point_id}")
                expected_energy[point_id] = energy_keV
                rows.append({
                    "group": "point_validation",
                    "group_event_index": event_index,
                    "group_hit_index": 1,
                    "input_event_key": point_id,
                    "synthetic": 1,
                    "synthetic_point_id": point_id,
                    "source_event_order": "",
                    "original_sample_id": "",
                    "original_job_id": "",
                    "original_event_id": "",
                    "candidate": "",
                    "strict_recoil_event": 0,
                    "layer": POINT_TEMPLATE_LAYER,
                    "event_si_total_keV": energy_keV,
                    "event_tes_direct_keV": 0.0,
                    "event_bgo_total_keV": 0.0,
                    "hit_time_s": 0.0,
                    "hit_time_ns": 0.0,
                    "hit_time_relative_ns": 0.0,
                    "local_x_mm": x_mm,
                    "local_y_mm": y_mm,
                    "local_z_mm": z_mm,
                    "energy_keV": energy_keV,
                    "global_x_cm": "",
                    "global_y_cm": "",
                    "global_z_cm": "",
                    "secondary": "synthetic",
                    "parent": "synthetic",
                    "step_process": "synthetic_point_injection",
                    "creation_process": "synthetic_point_injection",
                    "is_si_elastic_recoil": 0,
                    "original_source_csv_row": "",
                })
    return rows, expected_energy


def check_stage_energy(
    rows: list[dict[str, Any]], expected_energy: dict[str, float]
) -> None:
    actual: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        actual[str(row["input_event_key"])].append(float(row["energy_keV"]))
    if set(actual) != set(expected_energy):
        die("stage event-key set mismatch during energy check")
    for key in sorted(expected_energy):
        total = math.fsum(actual[key])
        if not close(total, expected_energy[key]):
            die(f"stage energy mismatch for {key}: {total} vs {expected_energy[key]}")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def select_events(
    catalog: dict[str, Any], predicate: Callable[[dict[str, Any]], bool]
) -> list[dict[str, Any]]:
    return [event for event in catalog["events"] if predicate(event)]


def build(root: Path) -> dict[str, Any]:
    catalog, source_csv_rows, source_meta = verified_source(root)
    crosscheck_json_csv(catalog, source_csv_rows)

    by_candidate = {
        event["candidate"]: event
        for event in catalog["events"] if event["candidate"] is not None
    }
    if set(by_candidate) != {"A", "B", "C"}:
        die(f"expected exact candidate labels A/B/C, got {sorted(by_candidate)}")
    exact_abc = [by_candidate[label] for label in ("A", "B", "C")]
    strict51 = select_events(catalog, lambda event: bool(event["strict_recoil_event"]))
    all86 = list(catalog["events"])
    if len(strict51) != 51 or len(all86) != 86:
        die("source subset counts are not strict51/all86")

    stage_payloads: dict[str, tuple[list[dict[str, Any]], dict[str, float]]] = {
        "point_validation": point_rows(),
        "exact_ABC": real_event_rows("exact_ABC", exact_abc),
        "strict51": real_event_rows("strict51", strict51),
        "all86": real_event_rows("all86", all86),
    }

    stages: list[dict[str, Any]] = []
    for order, group, rel in STAGE_SPECS:
        rows, expected = stage_payloads[group]
        check_stage_energy(rows, expected)
        event_indices = [int(row["group_event_index"]) for row in rows]
        unique_indices = sorted(set(event_indices))
        if unique_indices != list(range(1, len(expected) + 1)):
            die(f"non-contiguous event indices in {group}")
        path = root / rel
        write_csv(path, rows)
        stages.append({
            "stage_order": order,
            "group": group,
            "path": rel,
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
            "event_count": len(expected),
            "hit_row_count": len(rows),
            "total_injected_si_energy_keV": math.fsum(
                float(row["energy_keV"]) for row in rows
            ),
            "per_event_energy_conservation_pass": True,
        })

    expected_counts = {
        "point_validation": (30, 30),
        "exact_ABC": (3, 46),
        "strict51": (51, 54),
        "all86": (86, 327),
    }
    if {
        stage["group"]: (stage["event_count"], stage["hit_row_count"])
        for stage in stages
    } != expected_counts:
        die("stage event/HIT row counts differ from pinned expectations")

    point_data = stage_payloads["point_validation"][0]
    point_strict_inside = all(
        all(
            abs(float(row[field])) < bound
            for field, bound in zip(
                ("local_x_mm", "local_y_mm", "local_z_mm"),
                SLAB_HALF_EXTENTS_MM,
            )
        )
        for row in point_data
    )
    if not point_strict_inside:
        die("at least one point-validation coordinate touches/exceeds the slab")

    manifest = {
        "schema_version": 1,
        "status": "PASS__G4CMP_STAGED_INPUTS_PREPARED",
        "scope": "Per-Si-HIT energy/time/local-position inputs for the SH3 G4CMP ladder",
        "source_inputs": source_meta,
        "csv_schema": {
            "fields_in_order": CSV_FIELDS,
            "row_granularity": "one Si energy-deposition HIT per row",
            "units": {
                "energy": "keV",
                "hit_time_s": "s",
                "hit_time_ns_and_relative": "ns",
                "local_position": "mm in slab frame",
                "global_position": "cm in transport world frame; blank for synthetic points",
            },
            "local_axis_convention": (
                "x is the 0.3-mm thickness axis; y,z are the 36-mm in-plane axes"
            ),
        },
        "ordering": {
            "point_validation": (
                "energy order 30,140,500,568,1407 keV; center then edge; "
                "front,middle,back depth"
            ),
            "exact_ABC": "candidate A, then B, then C; source hit_order within event",
            "strict51": "source event_order; source hit_order within event",
            "all86": "source event_order; source hit_order within event",
        },
        "point_validation_design": {
            "energies_keV": list(POINT_ENERGIES_KEV),
            "template_layer": POINT_TEMPLATE_LAYER,
            "template_layer_rationale": "all six snapshotted Si slabs share identical dimensions",
            "slab_half_extents_mm": list(SLAB_HALF_EXTENTS_MM),
            "in_plane_positions_mm": {
                name: [y, z] for name, y, z in POINT_POSITIONS_YZ_MM
            },
            "thickness_depths_x_mm": {
                name: x for name, x in POINT_DEPTHS_X_MM
            },
            "minimum_boundary_clearance_mm": 0.05,
        },
        "stages": stages,
        "self_checks": {
            "source_sha256_all_match": True,
            "source_json_csv_rowwise_crosscheck_pass": True,
            "fixed_order_and_contiguous_group_event_indices": True,
            "point_event_count_is_30": True,
            "point_coordinates_strictly_inside_slab": point_strict_inside,
            "exact_candidate_order_is_A_B_C": True,
            "strict_event_count_is_51": True,
            "all_event_count_is_86": True,
            "all_stage_event_energy_sums_match": True,
            "all_required_checks_pass": True,
        },
    }
    manifest_path = root / "outputs/g4cmp_input_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="workspace root (default: parent of code/)",
    )
    args = parser.parse_args()
    manifest = build(args.workspace.resolve(strict=True))
    summary = ", ".join(
        f"{stage['group']}={stage['event_count']} events/{stage['hit_row_count']} HITs"
        for stage in manifest["stages"]
    )
    print(f"PASS: {summary}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
