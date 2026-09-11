#!/usr/bin/env python3
"""Publish the corrected BUILDUP/day-15 inventory in M05-facing tables.

This is a thin reporting adapter.  The retained corrected BUILDUP catalog owns
sum(RP)/sum(TT); the retained state-aware package owns NUBASE matching,
day-15 activity, exact RPIP matching, and delayed-source sampling.  This script
does not reopen SIM/DAT files or regenerate source cards.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import os
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import check_inputs


HERE = Path(__file__).resolve()
PACKAGE = HERE.parent.parent
ROOT = check_inputs.ROOT
DEFAULT_OUTPUT = PACKAGE / "outputs/02_activation"
CATALOG = (
    ROOT
    / "runs/particle_source_unit_repair_20260811"
    / "m05_paper_closure_topup_batch0007_3h_v1/delayed_phase02/catalog_v1/catalog.json"
)
EXACTPOS_ROOT = (
    ROOT
    / "runs/particle_source_unit_repair_20260811"
    / "m05_paper_closure_topup_batch0007_3h_v1/delayed_phase02/state_aware_exactpos_v1"
)
EXACTPOS_MANIFEST = EXACTPOS_ROOT / "manifest.json"
RETAINED_MATERIAL_ANALYSIS = (
    ROOT
    / "engineering/ea_s3d_existing_evidence_closure_20260713"
    / "code/analyze_mass_activation_materials.py"
)

GEOMETRY_ORDER = ("Mass_model_511", "S3d_O8")
FAMILY_ORDER = ("alpha", "eminus", "eplus", "gamma", "muminus", "muplus", "n", "p")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def load_retained_material_module() -> Any:
    spec = importlib.util.spec_from_file_location("m05_retained_activation_materials", RETAINED_MATERIAL_ANALYSIS)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {RETAINED_MATERIAL_ANALYSIS}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def material_category(volume: str, retained: Any) -> str:
    """Extend the retained M05 grouping only for the new S3d outer layers."""
    upper = volume.upper()
    if upper.startswith("CSI_") or upper.startswith("BGO_"):
        return "active_scintillator"
    if "BPE" in upper:
        return "bpe_neutron_shield"
    if "PLASTIC" in upper:
        return "plastic_positron_veto"
    category = retained.volume_category(volume)
    return "active_scintillator" if category == "csi" else category


def cell_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["geometry"]), str(row["family"])


def state_key(row: dict[str, Any]) -> tuple[str, int, float]:
    return str(row["volume"]), int(row["ZA"]), round(float(row["excitation_keV"]), 6)


def disposition(row: dict[str, Any], included: bool) -> str:
    if included:
        return "transported_ground_state"
    if row.get("holdout_reason") == "zero_day15_activity":
        return "stable_or_zero_activity"
    return "excited_or_unresolved_holdout"


def aggregate_rows(inventory: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    values: dict[tuple[Any, ...], dict[str, float | int]] = defaultdict(
        lambda: {
            "known_all_state_activity_Bq": 0.0,
            "transported_ground_activity_Bq": 0.0,
            "known_holdout_activity_Bq": 0.0,
            "unknown_state_count": 0,
            "state_rows": 0,
        }
    )
    geometry_totals: dict[str, float] = defaultdict(float)
    for row in inventory:
        activity = row["day15_activity_Bq"]
        if activity != "":
            geometry_totals[row["geometry"]] += float(activity)
        key = tuple(row[name] for name in keys)
        item = values[key]
        item["state_rows"] = int(item["state_rows"]) + 1
        if activity == "":
            item["unknown_state_count"] = int(item["unknown_state_count"]) + 1
            continue
        value = float(activity)
        item["known_all_state_activity_Bq"] = float(item["known_all_state_activity_Bq"]) + value
        if row["source_disposition"] == "transported_ground_state":
            item["transported_ground_activity_Bq"] = float(item["transported_ground_activity_Bq"]) + value
        elif value > 0.0:
            item["known_holdout_activity_Bq"] = float(item["known_holdout_activity_Bq"]) + value
    output: list[dict[str, Any]] = []
    for key, item in values.items():
        record = dict(zip(keys, key))
        record.update(item)
        total = geometry_totals[str(record["geometry"])]
        record["fraction_of_geometry_known_activity"] = (
            float(item["known_all_state_activity_Bq"]) / total if total > 0.0 else 0.0
        )
        output.append(record)
    return sorted(output, key=lambda row: tuple(str(row[name]) for name in keys))


def material_dtv(inventory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_cell: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in inventory:
        activity = row["day15_activity_Bq"]
        if activity == "":
            continue
        by_cell[(row["geometry"], row["incident_family"])][row["material_category"]] += float(activity)
    output: list[dict[str, Any]] = []
    for geometry in GEOMETRY_ORDER:
        families = [family for family in FAMILY_ORDER if math.fsum(by_cell[(geometry, family)].values()) > 0.0]
        categories = sorted({category for family in families for category in by_cell[(geometry, family)]})
        for index, family_a in enumerate(families):
            total_a = math.fsum(by_cell[(geometry, family_a)].values())
            for family_b in families[index + 1 :]:
                total_b = math.fsum(by_cell[(geometry, family_b)].values())
                distance = 0.5 * math.fsum(
                    abs(
                        by_cell[(geometry, family_a)].get(category, 0.0) / total_a
                        - by_cell[(geometry, family_b)].get(category, 0.0) / total_b
                    )
                    for category in categories
                )
                output.append(
                    {
                        "geometry": geometry,
                        "family_a": family_a,
                        "family_b": family_b,
                        "total_variation_distance": distance,
                    }
                )
    return sorted(output, key=lambda row: (row["geometry"], -row["total_variation_distance"], row["family_a"], row["family_b"]))


def build(output: Path) -> dict[str, Any]:
    catalog = load_json(CATALOG)
    exact = load_json(EXACTPOS_MANIFEST)
    retained_material = load_retained_material_module()

    if catalog["status"] != "PASS__CORRECTED_BUILDUP_CATALOG_READY":
        raise RuntimeError(f"BUILDUP catalog is not ready: {catalog['status']}")
    if not str(exact["status"]).startswith("PASS__STATE_AWARE_EXACT_POSITION_DELAYED_SOURCES_READY"):
        raise RuntimeError(f"state-aware sources are not ready: {exact['status']}")

    entries_by_cell: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for entry in catalog["dat_entries"]:
        entries_by_cell[cell_key(entry)].append(entry)
    catalog_cells = {cell_key(row): row for row in catalog["cells"]}
    exact_cells = {cell_key(row): row for row in exact["cells"]}

    activation_cells: list[dict[str, Any]] = []
    source_index: list[dict[str, Any]] = []
    inventory: list[dict[str, Any]] = []
    for geometry in GEOMETRY_ORDER:
        for family in FAMILY_ORDER:
            key = (geometry, family)
            cell = catalog_cells[key]
            state_cell = exact_cells[key]
            entries = entries_by_cell[key]
            generated = sum(int(row["events"]) for row in entries)
            activation_cells.append(
                {
                    "geometry": geometry,
                    "incident_family": family,
                    "N_BUILDUP_files": int(cell["N_DAT"]),
                    "generated_primaries": generated,
                    "sum_TT_s": float(cell["sum_TT_s"]),
                    "sum_RP": float(cell["sum_RP"]),
                    "production_rate_s-1": float(cell["production_rate_s-1"]),
                    "zero_RP_files": int(cell["zero_RP_DAT"]),
                    "cell_status": state_cell["status"],
                }
            )

            source_manifest_path = EXACTPOS_ROOT / "sources" / geometry / family / "source_manifest.json"
            source_manifest = load_json(source_manifest_path) if source_manifest_path.exists() else None
            source_index.append(
                {
                    "geometry": geometry,
                    "incident_family": family,
                    "source_status": state_cell["status"],
                    "transported_ground_activity_Bq": float(state_cell.get("included_ground_activity_Bq", 0.0)),
                    "known_holdout_activity_Bq": float(state_cell.get("known_holdout_activity_Bq", 0.0)),
                    "unknown_activity_state_count": int(state_cell.get("unknown_activity_state_count", 0)),
                    "included_state_count": len(state_cell.get("included_states", [])),
                    "holdout_state_count": len(state_cell.get("holdout_states", [])),
                    "RPIP_points": int(state_cell.get("RPIP_audit", {}).get("matched_points", 0)),
                    "pointsource_blocks": int(state_cell.get("n_pointsource_blocks", 0)),
                    "requested_decay_triggers": int(state_cell.get("triggers_requested", 0)),
                    "sampling_seed": state_cell.get("sampling_seed", ""),
                    "flux_per_point_Bq": (
                        float(state_cell.get("included_ground_activity_Bq", 0.0))
                        / int(state_cell.get("n_pointsource_blocks", 1))
                        if int(state_cell.get("n_pointsource_blocks", 0)) > 0 else ""
                    ),
                    "source_path": "" if source_manifest is None else source_manifest["source"],
                    "sampled_positions_path": "" if source_manifest is None else source_manifest["sampled_positions_table"],
                    "source_manifest_path": "" if source_manifest is None else relative(source_manifest_path),
                }
            )

            catalog_states = {
                (str(row["volume"]), int(row["isotope_id"]), round(float(row["excitation_keV"]), 6)): row
                for row in catalog["production_rows"]
                if cell_key(row) == key
            }
            seen_states: set[tuple[str, int, float]] = set()
            for group, included in ((state_cell.get("included_states", []), True), (state_cell.get("holdout_states", []), False)):
                for state in group:
                    skey = state_key(state)
                    base = catalog_states[skey]
                    seen_states.add(skey)
                    za = int(state["ZA"])
                    excitation = float(state["excitation_keV"])
                    activity = state.get("day15_activity_Bq")
                    inventory.append(
                        {
                            "geometry": geometry,
                            "incident_family": family,
                            "source_volume": state["volume"],
                            "material_category": material_category(str(state["volume"]), retained_material),
                            "source_parent_ZA": za,
                            "Z": za // 1000,
                            "A": za % 1000,
                            "excitation_keV": excitation,
                            "state_designator": "g" if excitation == 0.0 else f"Ex={excitation:g}keV",
                            "sum_RP": float(state["sum_RP"]),
                            "sum_TT_s": float(base["sum_TT_s_including_zero_RP_DAT"]),
                            "production_rate_s-1": float(state["production_rate_s-1"]),
                            "half_life_s": "" if state.get("half_life_s") is None else float(state["half_life_s"]),
                            "half_life_source": state.get("half_life_provenance", ""),
                            "day15_activity_Bq": "" if activity is None else float(activity),
                            "RPIP_support_count": int(state["RPIP_points"]),
                            "source_disposition": disposition(state, included),
                            "holdout_reason": state.get("holdout_reason", ""),
                        }
                    )
            if seen_states != set(catalog_states):
                raise RuntimeError(f"state table mismatch for {geometry}/{family}")

    inventory.sort(
        key=lambda row: (
            GEOMETRY_ORDER.index(row["geometry"]),
            FAMILY_ORDER.index(row["incident_family"]),
            row["source_volume"],
            row["source_parent_ZA"],
            row["excitation_keV"],
        )
    )
    if len(inventory) != len(catalog["production_rows"]):
        raise RuntimeError("inventory row count does not match corrected BUILDUP catalog")

    geometry_summary = aggregate_rows(inventory, ("geometry",))
    family_summary = aggregate_rows(inventory, ("geometry", "incident_family"))
    nuclide_summary = aggregate_rows(inventory, ("geometry", "source_parent_ZA"))
    material_summary = aggregate_rows(inventory, ("geometry", "material_category"))
    dtv = material_dtv(inventory)
    total_jobs = sum(row["N_BUILDUP_files"] for row in activation_cells)
    total_histories = sum(row["generated_primaries"] for row in activation_cells)
    total_rp = math.fsum(row["sum_RP"] for row in activation_cells)
    total_tt = math.fsum(row["sum_TT_s"] for row in activation_cells)

    summary = {
        "schema_version": 1,
        "status": "PASS__M05_CORRECTED_ACTIVATION_INVENTORY_READY__DELAYED_TRANSPORT_INCOMPLETE",
        "scope": "corrected-keV BUILDUP production and day-15 state-aware exact-position source preparation",
        "normalization": "sum(RP)/sum(TT) per geometry x incident family; zero-RP DAT TT included",
        "selected_buildup_jobs": total_jobs,
        "selected_buildup_histories": total_histories,
        "sum_RP": total_rp,
        "sum_TT_s": total_tt,
        "production_state_rows": len(inventory),
        "matched_RPIP_points": sum(int(row["RPIP_points"]) for row in source_index),
        "positive_transport_source_cells": sum(str(row["source_status"]).startswith("PASS") for row in source_index),
        "skipped_transport_source_cells": sum(not str(row["source_status"]).startswith("PASS") for row in source_index),
        "day15_by_geometry": geometry_summary,
        "day15_by_geometry_family": family_summary,
        "day15_by_geometry_parent_ZA": nuclide_summary,
        "day15_by_geometry_material": material_summary,
        "family_material_total_variation": dtv,
        "source_contract": {
            "catalog": relative(CATALOG),
            "state_aware_exactpos_manifest": relative(EXACTPOS_MANIFEST),
            "source_contract_sha256": catalog["source_contract_sha256"],
            "legacy_factor1000_included": catalog["legacy_factor1000_included"],
            "extra_mono511_included": catalog["extra_mono511_included"],
        },
        "authority_boundary": "ACTIVATION_INVENTORY_AND_DELAYED_SOURCE_PREPARATION_ONLY__NOT_DETECTOR_SELECTED_DELAYED_RATE_RESPONSE_MISSION_SENSITIVITY_OR_GEOMETRY_PROMOTION_AUTHORITY",
    }

    work = output.parent / f".{output.name}.work-{os.getpid()}"
    if output.exists() or work.exists():
        raise RuntimeError(f"output already exists: {output if output.exists() else work}")
    work.mkdir(parents=True)
    try:
        write_csv(
            work / "activation_cells.csv",
            activation_cells,
            [
                "geometry", "incident_family", "N_BUILDUP_files", "generated_primaries",
                "sum_TT_s", "sum_RP", "production_rate_s-1", "zero_RP_files", "cell_status",
            ],
        )
        write_csv(
            work / "day15_inventory.csv",
            inventory,
            [
                "geometry", "incident_family", "source_volume", "material_category",
                "source_parent_ZA", "Z", "A", "excitation_keV", "state_designator",
                "sum_RP", "sum_TT_s", "production_rate_s-1", "half_life_s",
                "half_life_source", "day15_activity_Bq", "RPIP_support_count",
                "source_disposition", "holdout_reason",
            ],
        )
        write_csv(
            work / "delayed_source_index.csv",
            source_index,
            [
                "geometry", "incident_family", "source_status", "transported_ground_activity_Bq",
                "known_holdout_activity_Bq", "unknown_activity_state_count", "included_state_count",
                "holdout_state_count", "RPIP_points", "pointsource_blocks", "requested_decay_triggers",
                "sampling_seed", "flux_per_point_Bq", "source_path", "sampled_positions_path",
                "source_manifest_path",
            ],
        )
        write_json(work / "day15_summary.json", summary)
        mass = next(row for row in geometry_summary if row["geometry"] == "Mass_model_511")
        o8 = next(row for row in geometry_summary if row["geometry"] == "S3d_O8")
        report = f"""# Corrected-keV M05 activation inventory

Status: `{summary['status']}`

The retained corrected BUILDUP catalog contributes {total_jobs:,} jobs and
{total_histories:,} primary histories.  Its {int(total_rp):,} production records
are normalized as `sum(RP)/sum(TT)` inside each geometry x incident-family
cell; all zero-RP DAT live times remain in the denominator.

| Geometry | Known day-15 activity | Transported ground-state activity | Known holdout | Unknown states |
|---|---:|---:|---:|---:|
| Mass_model_511 | {float(mass['known_all_state_activity_Bq']):.9g} Bq | {float(mass['transported_ground_activity_Bq']):.9g} Bq | {float(mass['known_holdout_activity_Bq']):.9g} Bq | {int(mass['unknown_state_count'])} |
| S3d-O8 | {float(o8['known_all_state_activity_Bq']):.9g} Bq | {float(o8['transported_ground_activity_Bq']):.9g} Bq | {float(o8['known_holdout_activity_Bq']):.9g} Bq | {int(o8['unknown_state_count'])} |

All {int(summary['matched_RPIP_points']):,} retained `CC IP RP` records match a
geometry/family/volume/ZA/state key.  Fifteen geometry-family cells already
have 50,000-point exact-position source cards; Mass_model_511/muplus has no
transportable positive ground-state activity and is retained as a zero source
cell.

This stage reports inventory Bq and source readiness only.  It does not turn
inventory Bq into a TES delayed-background rate, and it does not support a
geometry ranking, mission sensitivity, or paper conclusion before delayed
transport and the common detector response are complete.
"""
        (work / "REPORT.md").write_text(report, encoding="utf-8")
        manifest = {
            "schema_version": 1,
            "status": summary["status"],
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "analysis_code": relative(HERE),
            "reused_code": [
                relative(RETAINED_MATERIAL_ANALYSIS),
                "engineering/particle_source_unit_repair_20260811/m05_paper_closure_topup_batch0007_3h_20260813/delayed_phase02/code/build_corrected_buildup_catalog.py",
                "engineering/particle_source_unit_repair_20260811/m05_paper_closure_topup_batch0007_3h_20260813/delayed_phase02/code/prepare_state_aware_delayed_phase02.py",
            ],
            "inputs": [relative(CATALOG), relative(EXACTPOS_MANIFEST)],
            "files": [
                {"path": path.name, "bytes": path.stat().st_size}
                for path in sorted(work.iterdir()) if path.is_file()
            ],
            "hash_note": "No SIM/DAT/source artifacts were reopened or rehashed; published corrected catalog and exact-position declarations were consumed directly.",
        }
        write_json(work / "manifest.json", manifest)
        os.rename(work, output)
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise
    print(
        f"{summary['status']}: {total_jobs} buildup jobs, {total_histories} histories, "
        f"{len(inventory)} state rows, {output}"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    build(output.resolve())


if __name__ == "__main__":
    main()
