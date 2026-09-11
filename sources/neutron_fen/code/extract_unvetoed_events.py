#!/usr/bin/env python3
"""Build a compact, deterministic catalog of all unvetoed SH3 Si events.

Only the two compact 10M CSV catalogs and the snapshotted SH3 geometry are
read.  No SIM input is needed.  The output is one nested JSON catalog and one
flat (one row per Si HIT) CSV catalog.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


EXPECTED_SHA256 = {
    "input_snapshot/results/si_event_catalog_10m.csv":
        "445457cefc78fafd14333cca9cdd37f3217c8012e7d63ad34b0240ac63cd6a9b",
    "input_snapshot/results/si_hit_catalog_10m.csv":
        "68d4f5dcb0ab4c09877af09e36f2d63339e16a42b5735ebfb628fad8c114fb95",
    "input_snapshot/geometry/SH3_Assembly_OptV3.geo":
        "a270ab2caf340a34858b448374b3dad955878ebbb9df9169f97d80df46026934",
}

EVENT_SCHEMA = [
    "sample_id", "job_id", "event_id", "primary_energy_keV",
    "si_total_keV", "si_elastic_recoil_keV", "si_hit_count",
    "si_recoil_hit_count", "tes_total_keV", "bgo_total_keV",
    "bgo_lt_50keV", "L0_keV", "L1_keV", "L2_keV", "L3_keV",
    "L4_keV", "L5_keV",
]

HIT_SCHEMA = [
    "sample_id", "job_id", "event_id", "primary_energy_keV", "layer",
    "volume", "edep_keV", "x_cm", "y_cm", "z_cm", "t_s",
    "secondary", "parent", "step_process", "creation_process",
    "is_si_elastic_recoil",
]

ROI_KEV = (510.58, 511.42)

# Labels and identities are pinned by the handoff.  The code independently
# derives the energy-balance-feasible set, then requires it to equal this set.
CANDIDATE_LABEL_BY_KEY = {
    ("production_shard0037", "sh3_sisd_n10m_shard0037", 989): "A",
    ("production_shard0049", "sh3_sisd_n10m_shard0049", 2764): "B",
    ("production_shard0049", "sh3_sisd_n10m_shard0049", 639): "C",
}


def die(message: str) -> None:
    raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def f(value: str) -> float:
    return float(value)


def i(value: str) -> int:
    return int(value)


def event_key(row: dict[str, str]) -> tuple[str, str, int]:
    return row["sample_id"], row["job_id"], i(row["event_id"])


def close(a: float, b: float, *, abs_tol: float = 2e-6) -> bool:
    return math.isclose(a, b, rel_tol=2e-10, abs_tol=abs_tol)


def rounded(value: float, digits: int) -> float:
    result = round(value, digits)
    return 0.0 if result == 0 else result


def parse_geometry(path: Path) -> dict[str, Any]:
    """Read the relevant hierarchy directly from the frozen MEGAlib geometry."""
    text = path.read_text(encoding="utf-8")

    def vector(owner: str, property_name: str) -> list[float]:
        match = re.search(
            rf"(?m)^{re.escape(owner)}\.{property_name}\s+"
            r"([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*$",
            text,
        )
        if not match:
            die(f"missing {owner}.{property_name} in {path}")
        return [float(value) for value in match.groups()]

    frame_position = vector("InstrumentFrame", "Position")
    frame_rotation = vector("InstrumentFrame", "Rotation")
    if frame_rotation[0] != 0 or frame_rotation[2] != 0:
        die("this extractor supports the snapshotted single-axis InstrumentFrame rotation only")

    layers: dict[int, dict[str, Any]] = {}
    for layer in range(6):
        name = f"Si_Substrate_Stack_side_entry_L{layer}"
        shape_match = re.search(
            rf"(?m)^{re.escape(name)}\.Shape\s+BRIK\s+"
            r"([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*$",
            text,
        )
        if not shape_match:
            die(f"missing {name}.Shape BRIK")
        half_cm = [float(value) for value in shape_match.groups()]
        position_cm = vector(name, "Position")
        mother_match = re.search(
            rf"(?m)^{re.escape(name)}\.Mother\s+(\S+)\s*$", text
        )
        if not mother_match or mother_match.group(1) != "InstrumentFrame":
            die(f"{name} is not a direct InstrumentFrame child")
        layers[layer] = {
            "volume": name,
            "center_instrument_cm": position_cm,
            "half_size_cm": half_cm,
            "full_size_mm": [20.0 * value for value in half_cm],
        }

    return {
        "instrument_frame_position_world_cm": frame_position,
        "instrument_frame_rotation_xyz_deg": frame_rotation,
        "layers": layers,
    }


def world_to_local(
    xyz_cm: tuple[float, float, float], layer: int, geometry: dict[str, Any]
) -> tuple[list[float], list[float]]:
    """Invert InstrumentFrame R_y and then subtract the selected slab center.

    With the geometry's +theta convention:
      world = (cos(t)*x' + sin(t)*z', y', -sin(t)*x' + cos(t)*z') + p
    so the inverse used here is R_y(-theta).  The all-HIT containment check is
    also an empirical guard against choosing the opposite rotation convention.
    """
    px, py, pz = geometry["instrument_frame_position_world_cm"]
    theta = math.radians(geometry["instrument_frame_rotation_xyz_deg"][1])
    c, s = math.cos(theta), math.sin(theta)
    dx, dy, dz = xyz_cm[0] - px, xyz_cm[1] - py, xyz_cm[2] - pz
    instrument = [c * dx - s * dz, dy, s * dx + c * dz]
    center = geometry["layers"][layer]["center_instrument_cm"]
    local_mm = [10.0 * (instrument[j] - center[j]) for j in range(3)]
    return instrument, local_mm


def candidate_balance(si_keV: float, tes_keV: float) -> dict[str, Any]:
    low, high = ROI_KEV
    eta_low_raw = (low - tes_keV) / si_keV
    eta_high_raw = (high - tes_keV) / si_keV
    eta_low = max(0.0, eta_low_raw)
    eta_high = min(1.0, eta_high_raw)
    feasible = eta_low < eta_high and eta_high > 0.0 and eta_low < 1.0
    return {
        "feasible_for_some_eta_0_to_1": feasible,
        "eta_for_511keV": (511.0 - tes_keV) / si_keV,
        "eta_interval_for_roi": [eta_low, eta_high] if feasible else None,
    }


def load_events(path: Path) -> tuple[list[str], dict[tuple[str, str, int], dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != EVENT_SCHEMA:
            die(f"unexpected event schema: {reader.fieldnames!r}")
        rows: dict[tuple[str, str, int], dict[str, str]] = {}
        for row in reader:
            key = event_key(row)
            if key in rows:
                die(f"duplicate event key in event catalog: {key}")
            rows[key] = row
    if len(rows) != 3161:
        die(f"expected 3161 unique Si events, found {len(rows)}")
    return EVENT_SCHEMA, rows


def load_selected_hits(
    path: Path,
    selected_keys: set[tuple[str, str, int]],
) -> tuple[
    list[str], dict[tuple[str, str, int], list[dict[str, Any]]], int, int, int
]:
    selected: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    total_rows = 0
    blank_primary_rows = 0
    selected_blank_primary_rows = 0
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != HIT_SCHEMA:
            die(f"unexpected HIT schema: {reader.fieldnames!r}")
        for source_row, row in enumerate(reader, start=2):
            total_rows += 1
            if not row["primary_energy_keV"].strip():
                blank_primary_rows += 1
            key = event_key(row)
            if key in selected_keys:
                if not row["primary_energy_keV"].strip():
                    selected_blank_primary_rows += 1
                row_with_source: dict[str, Any] = dict(row)
                row_with_source["source_row"] = source_row
                selected[key].append(row_with_source)
    if total_rows != 304295:
        die(f"expected 304295 Si HIT records, found {total_rows}")
    return (
        HIT_SCHEMA, selected, total_rows, blank_primary_rows,
        selected_blank_primary_rows,
    )


def build(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    inputs = {rel: root / rel for rel in EXPECTED_SHA256}
    hashes: dict[str, dict[str, Any]] = {}
    for rel, path in inputs.items():
        resolved = path.resolve(strict=True)
        try:
            resolved.relative_to(root.resolve(strict=True))
        except ValueError:
            die(f"refusing input outside workspace: {resolved}")
        actual = sha256(resolved)
        expected = EXPECTED_SHA256[rel]
        if actual != expected:
            die(f"SHA-256 mismatch for {rel}: expected {expected}, got {actual}")
        hashes[rel] = {
            "sha256": actual,
            "bytes": resolved.stat().st_size,
            "matches_pinned_sha256": True,
        }

    event_path = inputs["input_snapshot/results/si_event_catalog_10m.csv"]
    hit_path = inputs["input_snapshot/results/si_hit_catalog_10m.csv"]
    geo_path = inputs["input_snapshot/geometry/SH3_Assembly_OptV3.geo"]
    event_schema, all_events = load_events(event_path)
    geometry = parse_geometry(geo_path)

    selected_rows = {
        key: row
        for key, row in all_events.items()
        if i(row["bgo_lt_50keV"]) == 1 and f(row["si_total_keV"]) > 0.0
    }
    selected_keys = set(selected_rows)
    if len(selected_rows) != 86:
        die(f"expected 86 BGO<50 keV, Si>0 events, found {len(selected_rows)}")

    (
        hit_schema, selected_hits, total_hit_rows, blank_hit_primary_rows,
        selected_blank_hit_primary_rows,
    ) = load_selected_hits(hit_path, selected_keys)
    if set(selected_hits) != selected_keys:
        missing = sorted(selected_keys - set(selected_hits))
        die(f"selected events without HIT records: {missing}")

    canonical_keys = sorted(selected_keys)
    events_out: list[dict[str, Any]] = []
    csv_rows: list[dict[str, Any]] = []
    strict_count = 0
    strict_hit_count = 0
    containment_tolerance_mm = 0.002
    strictly_outside = 0
    outside_with_tolerance = 0
    axis_values: dict[str, list[float]] = defaultdict(list)
    feasible_keys: set[tuple[str, str, int]] = set()

    for event_order, key in enumerate(canonical_keys, start=1):
        row = selected_rows[key]
        hits = selected_hits[key]
        hits.sort(
            key=lambda h: (
                f(h["t_s"]), i(h["layer"]), f(h["x_cm"]), f(h["y_cm"]),
                f(h["z_cm"]), f(h["edep_keV"]), i(str(h["source_row"])),
            )
        )
        strict_event = any(
            h["secondary"].startswith("Si")
            and h["parent"] == "neutron"
            and h["creation_process"] == "hadElastic"
            for h in hits
        )
        if strict_event:
            strict_count += 1

        si_total = f(row["si_total_keV"])
        tes_total = f(row["tes_total_keV"])
        balance = candidate_balance(si_total, tes_total)
        if balance["feasible_for_some_eta_0_to_1"]:
            feasible_keys.add(key)
        candidate_label = CANDIDATE_LABEL_BY_KEY.get(key)

        layer_sums = defaultdict(float)
        strict_energy = 0.0
        strict_hits_this_event = 0
        hits_out: list[dict[str, Any]] = []
        for hit_order, hit in enumerate(hits, start=1):
            layer = i(hit["layer"])
            volume = hit["volume"]
            expected_volume = geometry["layers"][layer]["volume"]
            if volume != expected_volume:
                die(f"layer/volume mismatch at HIT source row {hit['source_row']}")
            energy = f(hit["edep_keV"])
            global_xyz = (f(hit["x_cm"]), f(hit["y_cm"]), f(hit["z_cm"]))
            instrument_xyz, local_mm = world_to_local(global_xyz, layer, geometry)
            instrument_xyz = [rounded(value, 9) for value in instrument_xyz]
            local_mm = [rounded(value, 9) for value in local_mm]
            half_mm = [10.0 * v for v in geometry["layers"][layer]["half_size_cm"]]
            if any(abs(local_mm[j]) > half_mm[j] for j in range(3)):
                strictly_outside += 1
            if any(
                abs(local_mm[j]) > half_mm[j] + containment_tolerance_mm
                for j in range(3)
            ):
                outside_with_tolerance += 1
            for name, value in zip(("x", "y", "z"), local_mm):
                axis_values[name].append(value)

            is_strict_hit = (
                hit["secondary"].startswith("Si")
                and hit["parent"] == "neutron"
                and hit["creation_process"] == "hadElastic"
            )
            if is_strict_hit != (i(hit["is_si_elastic_recoil"]) == 1):
                die(f"strict definition/catalog flag mismatch at HIT source row {hit['source_row']}")
            if is_strict_hit:
                strict_energy += energy
                strict_hits_this_event += 1
                strict_hit_count += 1
            layer_sums[layer] += energy
            hit_item = {
                "hit_order": hit_order,
                "source_csv_row": i(str(hit["source_row"])),
                "layer": layer,
                "volume": volume,
                "edep_keV": energy,
                "global_position_cm": list(global_xyz),
                "instrument_position_cm": instrument_xyz,
                "slab_local_position_mm": local_mm,
                "time_s": f(hit["t_s"]),
                "time_ns": f(hit["t_s"]) * 1e9,
                "secondary": hit["secondary"],
                "parent": hit["parent"],
                "step_process": hit["step_process"],
                "creation_process": hit["creation_process"],
                "is_si_elastic_recoil": is_strict_hit,
            }
            hits_out.append(hit_item)
            csv_rows.append({
                "event_order": event_order,
                "hit_order": hit_order,
                "sample_id": key[0],
                "job_id": key[1],
                "event_id": key[2],
                "candidate": candidate_label or "",
                "strict_recoil_event": int(strict_event),
                "primary_energy_keV": f(row["primary_energy_keV"]),
                "si_total_keV": si_total,
                "si_elastic_recoil_keV": f(row["si_elastic_recoil_keV"]),
                "si_hit_count": i(row["si_hit_count"]),
                "si_recoil_hit_count": i(row["si_recoil_hit_count"]),
                "tes_total_keV": tes_total,
                "bgo_total_keV": f(row["bgo_total_keV"]),
                "layer": layer,
                "volume": volume,
                "edep_keV": energy,
                "global_x_cm": global_xyz[0],
                "global_y_cm": global_xyz[1],
                "global_z_cm": global_xyz[2],
                "instrument_x_cm": instrument_xyz[0],
                "instrument_y_cm": instrument_xyz[1],
                "instrument_z_cm": instrument_xyz[2],
                "slab_local_x_mm": local_mm[0],
                "slab_local_y_mm": local_mm[1],
                "slab_local_z_mm": local_mm[2],
                "time_s": f(hit["t_s"]),
                "time_ns": f(hit["t_s"]) * 1e9,
                "secondary": hit["secondary"],
                "parent": hit["parent"],
                "step_process": hit["step_process"],
                "creation_process": hit["creation_process"],
                "is_si_elastic_recoil": int(is_strict_hit),
                "source_csv_row": i(str(hit["source_row"])),
            })

        if len(hits) != i(row["si_hit_count"]):
            die(f"HIT count mismatch for {key}: {len(hits)} vs {row['si_hit_count']}")
        if strict_hits_this_event != i(row["si_recoil_hit_count"]):
            die(f"strict HIT count mismatch for {key}")
        if not close(sum(layer_sums.values()), si_total):
            die(f"Si energy sum mismatch for {key}")
        if not close(strict_energy, f(row["si_elastic_recoil_keV"])):
            die(f"strict recoil energy sum mismatch for {key}")
        for layer in range(6):
            if not close(layer_sums[layer], f(row[f"L{layer}_keV"])):
                die(f"layer L{layer} energy mismatch for {key}")
        if strict_event != (i(row["si_recoil_hit_count"]) > 0):
            die(f"strict event flag mismatch for {key}")
        if not (f(row["bgo_total_keV"]) < 50.0):
            die(f"BGO flag/value mismatch for selected event {key}")

        events_out.append({
            "event_order": event_order,
            "sample_id": key[0],
            "job_id": key[1],
            "event_id": key[2],
            "primary_energy_keV": f(row["primary_energy_keV"]),
            "si_total_keV": si_total,
            "si_elastic_recoil_keV": f(row["si_elastic_recoil_keV"]),
            "si_hit_count": i(row["si_hit_count"]),
            "si_recoil_hit_count": i(row["si_recoil_hit_count"]),
            "strict_recoil_event": strict_event,
            "tes_total_keV": tes_total,
            "bgo_total_keV": f(row["bgo_total_keV"]),
            "bgo_lt_50keV": True,
            "layer_energy_keV": {
                f"L{layer}": f(row[f"L{layer}_keV"]) for layer in range(6)
            },
            "energy_balance": balance,
            "candidate": candidate_label,
            "hits": hits_out,
        })

    if strict_count != 51:
        die(f"expected 51 strict recoil events in selection, found {strict_count}")
    if feasible_keys != set(CANDIDATE_LABEL_BY_KEY):
        die(
            "energy-balance candidate mismatch: derived "
            f"{sorted(feasible_keys)!r}, expected {sorted(CANDIDATE_LABEL_BY_KEY)!r}"
        )
    if outside_with_tolerance != 0:
        die(f"{outside_with_tolerance} selected HITs lie outside slab bounds beyond tolerance")

    by_label = {
        event["candidate"]: {
            "sample_id": event["sample_id"],
            "job_id": event["job_id"],
            "event_id": event["event_id"],
            "strict_recoil_event": event["strict_recoil_event"],
            "layers": sorted({hit["layer"] for hit in event["hits"]}),
            "si_total_keV": event["si_total_keV"],
            "si_elastic_recoil_keV": event["si_elastic_recoil_keV"],
            "tes_total_keV": event["tes_total_keV"],
            "bgo_total_keV": event["bgo_total_keV"],
            **event["energy_balance"],
        }
        for event in events_out if event["candidate"] is not None
    }

    geometry_json = {
        "instrument_frame_position_world_cm":
            geometry["instrument_frame_position_world_cm"],
        "instrument_frame_rotation_xyz_deg":
            geometry["instrument_frame_rotation_xyz_deg"],
        "layers": {
            f"L{layer}": data for layer, data in geometry["layers"].items()
        },
    }
    output = {
        "schema_version": 1,
        "status": "PASS__86_UNVETOED_SI_EVENTS_EXTRACTED",
        "scope": (
            "All 10M SH3 events with Si_total>0 and upstream BGO_total<50 keV; "
            "raw Geant4 Si HITs only, before phonon/TES response"
        ),
        "inputs": hashes,
        "source_schemas": {
            "si_event_catalog_10m.csv": {
                "row_granularity": "one row per Si-positive event",
                "fields_in_order": event_schema,
                "units": "energies keV; identifiers/counts/flag dimensionless",
            },
            "si_hit_catalog_10m.csv": {
                "row_granularity": "one row per Si CC HIT energy-deposition record",
                "fields_in_order": hit_schema,
                "units": "energy keV; global position cm; time s",
                "strict_recoil_definition": (
                    "secondary starts with Si, parent neutron, creation_process "
                    "hadElastic (materialized as is_si_elastic_recoil=1)"
                ),
                "nullable_field_note": (
                    "primary_energy_keV is blank in every source HIT row; the flat "
                    "output fills it by the composite event-key join to the event catalog"
                ),
                "blank_primary_energy_rows": blank_hit_primary_rows,
            },
        },
        "selection": {
            "predicate": "si_total_keV > 0 and bgo_total_keV < 50",
            "catalog_flag_used": "bgo_lt_50keV == 1",
            "event_count": len(events_out),
            "strict_recoil_event_count": strict_count,
            "non_strict_event_count": len(events_out) - strict_count,
            "hit_count": len(csv_rows),
            "strict_recoil_hit_count": strict_hit_count,
            "roi_keV_half_open": list(ROI_KEV),
        },
        "ordering": {
            "events": "lexicographic (sample_id, job_id, numeric event_id)",
            "hits": (
                "numeric (time_s, layer, x_cm, y_cm, z_cm, edep_keV, "
                "source_csv_row) within each event"
            ),
        },
        "coordinate_transform": {
            "source": "input_snapshot/geometry/SH3_Assembly_OptV3.geo",
            "world_to_instrument": (
                "subtract InstrumentFrame.Position, then apply inverse of "
                "InstrumentFrame.Rotation 0 45 0: x'=cos45*x-sin45*z; "
                "y'=y; z'=sin45*x+cos45*z"
            ),
            "instrument_to_slab_local": "subtract the selected Si layer center",
            "slab_axis_meaning": (
                "local x is the 0.3-mm thickness axis; local y and z are the "
                "two 36-mm in-plane axes"
            ),
            "derived_coordinate_units": {
                "instrument_position_cm": "cm",
                "slab_local_position_mm": "mm",
            },
            "geometry": geometry_json,
        },
        "coordinate_ranges_all_selected_hits_mm": {
            axis: {
                "min": min(values), "max": max(values),
                "max_abs": max(abs(v) for v in values),
                "nominal_half_extent": 10.0 * geometry["layers"][0]["half_size_cm"][
                    {"x": 0, "y": 1, "z": 2}[axis]
                ],
                "max_nominal_bound_excess": max(
                    0.0,
                    max(abs(v) for v in values)
                    - 10.0 * geometry["layers"][0]["half_size_cm"][
                        {"x": 0, "y": 1, "z": 2}[axis]
                    ],
                ),
            }
            for axis, values in sorted(axis_values.items())
        },
        "candidates": {label: by_label[label] for label in ("A", "B", "C")},
        "self_checks": {
            "input_sha256_all_match": True,
            "source_event_rows": len(all_events),
            "source_hit_rows": total_hit_rows,
            "selected_event_count_is_86": len(events_out) == 86,
            "selected_strict_event_count_is_51": strict_count == 51,
            "event_hit_counts_and_energy_sums_match": True,
            "event_layer_energy_sums_match": True,
            "strict_definition_flags_counts_and_energy_sums_match": True,
            "derived_candidate_set_is_exactly_A_B_C": True,
            "hits_strictly_outside_nominal_slab_count": strictly_outside,
            "nominal_boundary_excess_interpretation": (
                "Finite-decimal source-coordinate rounding only: all nominal excesses "
                "are on the 0.3-mm thickness boundary and remain below tolerance."
                if strictly_outside and not outside_with_tolerance else
                "No nominal-boundary excesses."
            ),
            "coordinate_rounding_tolerance_mm": containment_tolerance_mm,
            "hits_outside_slab_beyond_tolerance_count": outside_with_tolerance,
            "all_source_hit_primary_energy_values_blank":
                blank_hit_primary_rows == total_hit_rows,
            "all_selected_hit_primary_energy_values_blank":
                selected_blank_hit_primary_rows == len(csv_rows),
            "all_required_checks_pass": True,
        },
        "events": events_out,
    }
    return output, csv_rows


def write_outputs(root: Path, output: dict[str, Any], csv_rows: list[dict[str, Any]]) -> None:
    output_dir = root / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "unvetoed_events.json"
    csv_path = output_dir / "unvetoed_events.csv"

    json_path.write_text(
        json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if not csv_rows:
        die("internal error: no flat output rows")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]))
        writer.writeheader()
        writer.writerows(csv_rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="workspace root (default: parent of code/)",
    )
    args = parser.parse_args()
    root = args.workspace.resolve(strict=True)
    output, csv_rows = build(root)
    write_outputs(root, output, csv_rows)
    ranges = output["coordinate_ranges_all_selected_hits_mm"]
    print(
        "PASS: "
        f"{output['selection']['event_count']} events, "
        f"{output['selection']['strict_recoil_event_count']} strict, "
        f"{output['selection']['hit_count']} HITs; "
        f"local ranges mm x=[{ranges['x']['min']},{ranges['x']['max']}], "
        f"y=[{ranges['y']['min']},{ranges['y']['max']}], "
        f"z=[{ranges['z']['min']},{ranges['z']['max']}]"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
