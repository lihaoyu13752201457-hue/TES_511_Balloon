#!/usr/bin/env python3
"""Build the frozen-S3d-O8 versus fresh-SE3 matched day-15 comparison.

Background authority is deliberately asymmetric but auditable: S3d-O8
prompt, delayed, and activation rows are strictly filtered from the retained
104d M05 small tables, while SE3 rows come from this fresh package.  The only
fresh signal authority is the SE3 stage-04 ``FULL_ENVELOPE_SE3_ONLY`` product.
No fresh S3d transport or receipt is required.  In the absence of a frozen
full-envelope S3d small-table authority, signal/F3 geometry ratios are emitted
as ``UNAVAILABLE_BY_USER_SCOPE``; the historical post-Be signal is never used
as a substitute denominator.

``--check-prerequisites`` reads only CSV/JSON tables and file metadata.  It
does not open catalogs or rich SIM payloads.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shutil
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from se3_plan1_common import FAMILIES, PACKAGE_ROOT, PROFILE_ID, REPO_ROOT


HERE = Path(__file__).resolve()
DEFAULT_CONFIG = PACKAGE_ROOT / "analysis_inputs.json"
GEOMETRIES = ("S3d_O8", "SE3")
FRESH_SIGNAL_GEOMETRIES = ("SE3",)
FAMILY_ORDER = tuple(FAMILIES)
STREAMS = ("prompt", "delayed")
WINDOWS = ("broad_480_550", "w2_510p58_511p42")
FINAL_RESPONSE = "measured"
FINAL_STAGE = "side_compton_fov_pass"
SIGNAL_SCOPE = "FULL_ENVELOPE_SE3_ONLY"
SIGNAL_RATIO_UNAVAILABLE = "UNAVAILABLE_BY_USER_SCOPE"
MAX_CSV_BYTES = 128 * 1024**2
MAX_JSON_BYTES = 16 * 1024**2

ELEMENTS = (
    "n", "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne", "Na", "Mg",
    "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn",
    "Fe", "Co", "Ni", "Cu", "Zn", "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb",
    "Sr", "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In",
    "Sn", "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd", "Pm",
    "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu", "Hf", "Ta",
    "W", "Re", "Os", "Ir", "Pt", "Au", "Hg", "Tl", "Pb", "Bi", "Po", "At",
    "Rn", "Fr", "Ra", "Ac", "Th", "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk",
    "Cf", "Es", "Fm", "Md", "No", "Lr", "Rf", "Db", "Sg", "Bh", "Hs", "Mt",
    "Ds", "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og",
)

COMMON_REQUIRED = {
    "geometry", "stream", "family", "response_state", "stage", "window_id",
    "generated_events", "selected_events", "event_weight", "weighted_value",
    "weighted_stat_sigma", "weighted_lower95", "weighted_upper95", "weighted_unit",
}
OCCUPANCY_REQUIRED = {
    "geometry", "stream", "family", "generated_events", "detector_occupancy_events",
    "tes_positive_events", "active_only_events", "pixel_hits", "weighted_occupancy",
    "weighted_tes", "weighted_active_only", "weighted_stat_sigma", "weighted_unit",
}
LINEAGE_REQUIRED = {
    "geometry", "stream", "family", "local_event_id", "event_weight_cps",
    "source_parent_ZA", "source_volume",
}
SIGNAL_REQUIRED = {
    "geometry", "response_state", "stage", "window_id", "trials", "selected_events",
    "acceptance", "acceptance_lower95", "acceptance_upper95", "input_optics_aeff_cm2",
    "selected_effective_area_cm2", "selected_effective_area_lower95_cm2",
    "selected_effective_area_upper95_cm2", "signal_scope",
}
ACTIVATION_CELL_REQUIRED = {
    "geometry", "incident_family", "N_BUILDUP_files", "generated_primaries", "sum_TT_s",
    "sum_RP", "production_rate_s-1", "zero_RP_files", "cell_status",
}
INVENTORY_REQUIRED = {
    "geometry", "incident_family", "source_volume", "material_category",
    "source_parent_ZA", "day15_activity_Bq", "source_disposition", "holdout_reason",
}
SOURCE_INDEX_REQUIRED = {
    "geometry", "incident_family", "execution_disposition",
    "transported_ground_activity_Bq", "transported_ground_rate_upper95_s-1",
    "transported_ground_A15_upper95_Bq_conservative", "zero_A15_upper_provenance",
}
ZERO_PROVENANCE_REQUIRED = {
    "geometry", "family", "execution_disposition", "central_delayed_rate_cps",
    "transported_ground_activity_Bq", "transported_ground_rate_upper95_s-1",
    "transported_ground_A15_upper95_Bq_conservative", "zero_A15_upper_provenance",
    "upper_excludes_known_and_unresolved_holdout", "stage03_catalog_opened", "SIM_opened",
}
RUN_DISPOSITION = "RUN_83334"
ZERO_DISPOSITION = "SKIP_ZERO_A15"


def load_json(path: Path) -> dict[str, Any]:
    if path.suffix != ".json" or path.stat().st_size > MAX_JSON_BYTES:
        raise RuntimeError(f"refusing non-small JSON authority: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return value


def read_csv(path: Path, required: set[str] | None = None) -> list[dict[str, str]]:
    if path.suffix != ".csv" or path.stat().st_size > MAX_CSV_BYTES:
        raise RuntimeError(f"refusing non-small CSV authority: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or ())
        if required is not None and not required.issubset(fields):
            raise RuntimeError(
                f"CSV schema differs for {path}: missing={sorted(required - fields)}"
            )
        return list(reader)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"refusing schema-less empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    names = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=names, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def input_paths(config: dict[str, Any]) -> dict[str, Path]:
    frozen = Path(config["frozen_s3d"]["m05_outputs"])
    fresh_activation = Path(config["outputs"]["stage_02"])
    fresh_common = Path(config["outputs"]["stage_04"])
    return {
        "frozen_s3d_common_cutflow": frozen / "04_common_response/common_cutflow.csv",
        "frozen_s3d_occupancy": frozen / "04_common_response/common_fullband_occupancy.csv",
        "frozen_s3d_lineage": frozen / "04_common_response/selected_background_w2_lineage.csv",
        "frozen_s3d_activation_cells": frozen / "02_activation/activation_cells.csv",
        "frozen_s3d_inventory": frozen / "02_activation/day15_inventory.csv",
        "frozen_s3d_activation_summary": frozen / "02_activation/day15_summary.json",
        "fresh_se3_activation_cells": fresh_activation / "activation_cells.csv",
        "fresh_se3_inventory": fresh_activation / "day15_inventory.csv",
        "fresh_se3_activation_summary": fresh_activation / "day15_summary.json",
        "fresh_se3_source_index": fresh_activation / "delayed_source_index.csv",
        "fresh_common_cutflow": fresh_common / "common_cutflow.csv",
        "fresh_common_occupancy": fresh_common / "common_fullband_occupancy.csv",
        "fresh_common_lineage": fresh_common / "selected_background_w2_lineage.csv",
        "fresh_full_envelope_signal": fresh_common / "signal_acceptance_effective_area.csv",
        "fresh_common_summary": fresh_common / "summary.json",
        "fresh_zero_A15_provenance": fresh_common / "delayed_zero_A15_provenance.csv",
    }


def geometry_rows(
    rows: Iterable[dict[str, str]], geometry: str, *, label: str
) -> list[dict[str, str]]:
    selected = [dict(row) for row in rows if row.get("geometry") == geometry]
    if not selected:
        raise RuntimeError(f"strict geometry filter selected no {geometry} rows from {label}")
    if any(row.get("geometry") != geometry for row in selected):
        raise AssertionError("geometry filter failed")
    return selected


def unique_index(
    rows: Iterable[dict[str, str]], keys: tuple[str, ...], *, label: str
) -> dict[tuple[str, ...], dict[str, str]]:
    result: dict[tuple[str, ...], dict[str, str]] = {}
    for row in rows:
        key = tuple(str(row[name]) for name in keys)
        if key in result:
            raise RuntimeError(f"duplicate {label} key: {key}")
        result[key] = row
    return result


def background_common(rows: list[dict[str, str]], geometry: str, label: str) -> list[dict[str, str]]:
    selected = [
        row for row in geometry_rows(rows, geometry, label=label)
        if row["stream"] in STREAMS
    ]
    for stream in STREAMS:
        families = {row["family"] for row in selected if row["stream"] == stream}
        if families != set(FAMILY_ORDER):
            raise RuntimeError(
                f"{label} {geometry}/{stream} family closure differs: {sorted(families)}"
            )
    return selected


def signal_common(rows: list[dict[str, str]], geometry: str, label: str) -> list[dict[str, str]]:
    return [
        row for row in geometry_rows(rows, geometry, label=label)
        if row["stream"] == "signal"
    ]


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes")


def fresh_registered_source_contract(
    source_rows: list[dict[str, str]],
    zero_rows: list[dict[str, str]],
    inventory_rows: list[dict[str, str]],
    common_rows: list[dict[str, str]],
) -> dict[str, dict[str, Any]]:
    """Close eight registered families without fabricating isotope rows."""
    selected_sources = [row for row in source_rows if row.get("geometry") == "SE3"]
    if len(selected_sources) != len(source_rows):
        raise RuntimeError("fresh delayed-source index is not SE3-only")
    source_index = unique_index(
        selected_sources, ("incident_family",), label="fresh SE3 registered delayed source"
    )
    if {key[0] for key in source_index} != set(FAMILY_ORDER):
        raise RuntimeError("fresh delayed-source index does not register all eight families")
    zero_index = unique_index(
        [row for row in zero_rows if row.get("geometry") == "SE3"],
        ("family",),
        label="fresh SE3 zero-A15 provenance",
    )
    if len(zero_index) != len(zero_rows):
        raise RuntimeError("fresh zero-A15 provenance is not SE3-only")
    inventory_by_family: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in inventory_rows:
        family = str(row.get("incident_family", ""))
        if family not in FAMILY_ORDER:
            raise RuntimeError(f"fresh inventory contains an unregistered family: {family!r}")
        inventory_by_family[family].append(row)
    common_by_family: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in common_rows:
        if row.get("geometry") == "SE3" and row.get("stream") == "delayed":
            common_by_family[str(row.get("family", ""))].append(row)

    registry: dict[str, dict[str, Any]] = {}
    expected_zero: set[str] = set()
    for family in FAMILY_ORDER:
        source = source_index[(family,)]
        disposition = str(source.get("execution_disposition", ""))
        if disposition not in (RUN_DISPOSITION, ZERO_DISPOSITION):
            raise RuntimeError(f"fresh source disposition differs for {family}: {disposition!r}")
        activity = float(source["transported_ground_activity_Bq"])
        transported_rows = [
            row for row in inventory_by_family.get(family, [])
            if row.get("source_disposition") == "transported_ground_state"
        ]
        if disposition == RUN_DISPOSITION:
            if not math.isfinite(activity) or activity <= 0.0 or not transported_rows:
                raise RuntimeError(f"RUN_83334 family lacks transported inventory: {family}")
            inventory_activity = math.fsum(
                float(row["day15_activity_Bq"]) for row in transported_rows
            )
            if not math.isclose(
                inventory_activity, activity, rel_tol=2.0e-12, abs_tol=1.0e-12
            ):
                raise RuntimeError(f"RUN_83334 source-index/inventory activity differs: {family}")
            if (family,) in zero_index:
                raise RuntimeError(f"RUN_83334 family appears in zero provenance: {family}")
            registry[family] = {
                "execution_disposition": disposition,
                "transported_ground_activity_Bq": activity,
                "finite_A15_upper95_Bq": None,
                "zero_A15_upper_provenance": None,
                "inventory_state_rows": len(inventory_by_family.get(family, [])),
            }
            continue

        expected_zero.add(family)
        if activity != 0.0 or transported_rows:
            raise RuntimeError(f"SKIP_ZERO_A15 family has transported activity rows: {family}")
        provenance = zero_index.get((family,))
        if provenance is None:
            raise RuntimeError(f"SKIP_ZERO_A15 family lacks stage04 provenance: {family}")
        rate_upper = float(provenance["transported_ground_rate_upper95_s-1"])
        a15_upper = float(provenance["transported_ground_A15_upper95_Bq_conservative"])
        if not all(math.isfinite(value) and value > 0.0 for value in (rate_upper, a15_upper)):
            raise RuntimeError(f"SKIP_ZERO_A15 finite upper is invalid: {family}")
        if not math.isclose(rate_upper, a15_upper, rel_tol=0.0, abs_tol=1.0e-18):
            raise RuntimeError(f"SKIP_ZERO_A15 rate/A15 upper differs: {family}")
        if not math.isclose(
            float(source["transported_ground_rate_upper95_s-1"]),
            rate_upper,
            rel_tol=0.0,
            abs_tol=1.0e-18,
        ) or not math.isclose(
            float(source["transported_ground_A15_upper95_Bq_conservative"]),
            a15_upper,
            rel_tol=0.0,
            abs_tol=1.0e-18,
        ):
            raise RuntimeError(f"stage02/stage04 SKIP_ZERO_A15 upper binding differs: {family}")
        upper_provenance = str(provenance.get("zero_A15_upper_provenance", ""))
        if (
            float(provenance["central_delayed_rate_cps"]) != 0.0
            or float(provenance["transported_ground_activity_Bq"]) != 0.0
            or not upper_provenance
            or not truthy(provenance["upper_excludes_known_and_unresolved_holdout"])
            or truthy(provenance["stage03_catalog_opened"])
            or truthy(provenance["SIM_opened"])
        ):
            raise RuntimeError(f"SKIP_ZERO_A15 stage04 provenance contract differs: {family}")
        family_common = common_by_family.get(family, [])
        if not family_common or any(
            int(row["selected_events"]) != 0
            or float(row["event_weight"]) != 0.0
            or float(row["weighted_value"]) != 0.0
            or row.get("execution_disposition") != ZERO_DISPOSITION
            or not math.isclose(
                float(row["transported_ground_A15_upper95_Bq_conservative"]),
                a15_upper,
                rel_tol=0.0,
                abs_tol=1.0e-18,
            )
            for row in family_common
        ):
            raise RuntimeError(f"SKIP_ZERO_A15 common-response central-zero closure differs: {family}")
        registry[family] = {
            "execution_disposition": disposition,
            "transported_ground_activity_Bq": 0.0,
            "finite_A15_upper95_Bq": a15_upper,
            "finite_rate_upper95_s-1": rate_upper,
            "zero_A15_upper_provenance": upper_provenance,
            "upper_excludes_known_and_unresolved_holdout": True,
            "inventory_state_rows": len(inventory_by_family.get(family, [])),
            "exact_empty_inventory_family": family not in inventory_by_family,
        }
    if {key[0] for key in zero_index} != expected_zero:
        raise RuntimeError("stage02 dispositions and stage04 zero provenance family sets differ")
    return registry


def validate_small_table_contract(config: dict[str, Any], paths: dict[str, Path]) -> dict[str, Any]:
    frozen_common_all = read_csv(paths["frozen_s3d_common_cutflow"], COMMON_REQUIRED)
    frozen_occ_all = read_csv(paths["frozen_s3d_occupancy"], OCCUPANCY_REQUIRED)
    frozen_lineage_all = read_csv(paths["frozen_s3d_lineage"], LINEAGE_REQUIRED)
    frozen_cells_all = read_csv(paths["frozen_s3d_activation_cells"], ACTIVATION_CELL_REQUIRED)
    frozen_inventory_all = read_csv(paths["frozen_s3d_inventory"], INVENTORY_REQUIRED)
    frozen_activation_summary = load_json(paths["frozen_s3d_activation_summary"])

    fresh_cells_all = read_csv(paths["fresh_se3_activation_cells"], ACTIVATION_CELL_REQUIRED)
    fresh_inventory_all = read_csv(paths["fresh_se3_inventory"], INVENTORY_REQUIRED)
    fresh_activation_summary = load_json(paths["fresh_se3_activation_summary"])
    fresh_source_rows = read_csv(paths["fresh_se3_source_index"], SOURCE_INDEX_REQUIRED)
    fresh_common_all = read_csv(paths["fresh_common_cutflow"], COMMON_REQUIRED)
    fresh_occ_all = read_csv(paths["fresh_common_occupancy"], OCCUPANCY_REQUIRED)
    fresh_lineage_all = read_csv(paths["fresh_common_lineage"], LINEAGE_REQUIRED)
    fresh_signal_all = read_csv(paths["fresh_full_envelope_signal"], SIGNAL_REQUIRED)
    fresh_common_summary = load_json(paths["fresh_common_summary"])
    fresh_zero_rows = read_csv(paths["fresh_zero_A15_provenance"], ZERO_PROVENANCE_REQUIRED)

    for label, rows in (
        ("fresh activation cells", fresh_cells_all),
        ("fresh day15 inventory", fresh_inventory_all),
        ("fresh common cutflow", fresh_common_all),
        ("fresh occupancy", fresh_occ_all),
        ("fresh lineage", fresh_lineage_all),
        ("fresh signal acceptance", fresh_signal_all),
    ):
        geometries = {row.get("geometry") for row in rows}
        if label in ("fresh lineage", "fresh day15 inventory") and not rows:
            continue
        if geometries != {"SE3"}:
            raise RuntimeError(
                f"{label} must be SE3-only under user scope; got {sorted(str(v) for v in geometries)}"
            )

    for label, summary in (
        ("frozen S3d activation", frozen_activation_summary),
        ("fresh SE3 activation", fresh_activation_summary),
        ("fresh common response", fresh_common_summary),
    ):
        if not str(summary.get("status", "")).startswith("PASS__"):
            raise RuntimeError(f"{label} status is not PASS: {summary.get('status')}")
    if fresh_common_summary.get("signal_scope") != SIGNAL_SCOPE:
        raise RuntimeError(
            "fresh stage04 summary must declare signal_scope=FULL_ENVELOPE_SE3_ONLY; "
            f"got {fresh_common_summary.get('signal_scope')!r}"
        )

    frozen_background = background_common(
        frozen_common_all, "S3d_O8", "104d frozen common_cutflow"
    )
    fresh_background = background_common(
        fresh_common_all, "SE3", "fresh common_cutflow"
    )
    common_key = ("stream", "family", "response_state", "stage", "window_id")
    frozen_background_index = unique_index(
        frozen_background, common_key, label="frozen S3d background cutflow"
    )
    fresh_background_index = unique_index(
        fresh_background, common_key, label="fresh SE3 background cutflow"
    )
    if set(frozen_background_index) != set(fresh_background_index):
        raise RuntimeError("S3d/SE3 background common-cutflow key closure differs")

    fresh_signal_geometry_set = {row["geometry"] for row in fresh_signal_all}
    if fresh_signal_geometry_set != set(FRESH_SIGNAL_GEOMETRIES):
        raise RuntimeError(
            f"fresh signal table geometry closure differs: {sorted(fresh_signal_geometry_set)}"
        )
    if any(row.get("signal_scope") != SIGNAL_SCOPE for row in fresh_signal_all):
        raise RuntimeError(
            "every fresh SE3 signal row must declare a full-envelope scope"
        )
    expected_trials = int(config["signal"]["eventlist_rows"])
    if any(int(row["trials"]) != expected_trials for row in fresh_signal_all):
        raise RuntimeError("fresh full-envelope signal trial count differs from frozen ray bank")
    expected_aeff = float(config["signal"]["input_optics_aeff_cm2"])
    if any(
        not math.isclose(float(row["input_optics_aeff_cm2"]), expected_aeff, rel_tol=0.0, abs_tol=1e-12)
        for row in fresh_signal_all
    ):
        raise RuntimeError("fresh full-envelope signal input Aeff differs from config")
    signal_key = ("response_state", "stage", "window_id")
    signal_indexes = {
        geometry: unique_index(
            geometry_rows(fresh_signal_all, geometry, label="fresh signal table"),
            signal_key,
            label=f"fresh {geometry} signal",
        )
        for geometry in FRESH_SIGNAL_GEOMETRIES
    }
    expected_signal_keys = {
        (response, stage, window)
        for response, stage in ((FINAL_RESPONSE, FINAL_STAGE),)
        for window in WINDOWS
    }
    if not expected_signal_keys.issubset(set(signal_indexes["SE3"])):
        raise RuntimeError("fresh SE3 full-envelope final-signal closure differs")

    fresh_signal_common = unique_index(
        signal_common(fresh_common_all, "SE3", "fresh common_cutflow"),
        common_key,
        label="fresh SE3 signal common cutflow",
    )
    if not fresh_signal_common:
        raise RuntimeError("fresh common_cutflow lacks SE3 full-envelope signal rows")
    if any(
        row.get("signal_scope") != SIGNAL_SCOPE
        for row in fresh_signal_common.values()
    ):
        raise RuntimeError("fresh SE3 signal common-cutflow scope differs")
    if any(
        row.get("geometry") == "S3d_O8" and row.get("stream") == "signal"
        for row in fresh_common_all
    ):
        raise RuntimeError("fresh stage04 unexpectedly contains S3d signal transport")

    frozen_occ = [
        row for row in geometry_rows(frozen_occ_all, "S3d_O8", label="104d frozen occupancy")
        if row["stream"] in STREAMS
    ]
    fresh_se3_occ = [
        row for row in geometry_rows(fresh_occ_all, "SE3", label="fresh occupancy")
        if row["stream"] in STREAMS
    ]
    occupancy_key = ("stream", "family")
    if set(unique_index(frozen_occ, occupancy_key, label="frozen S3d occupancy")) != set(
        unique_index(fresh_se3_occ, occupancy_key, label="fresh SE3 occupancy")
    ):
        raise RuntimeError("S3d/SE3 background occupancy key closure differs")
    fresh_signal_occ = unique_index(
        [
            row for row in geometry_rows(fresh_occ_all, "SE3", label="fresh occupancy")
            if row["stream"] == "signal"
        ],
        occupancy_key,
        label="fresh SE3 signal occupancy",
    )
    if not fresh_signal_occ:
        raise RuntimeError("fresh SE3 full-envelope signal occupancy is missing")
    if any(
        row.get("signal_scope") != SIGNAL_SCOPE
        for row in fresh_signal_occ.values()
    ):
        raise RuntimeError("fresh SE3 signal occupancy scope differs")
    if any(
        row.get("geometry") == "S3d_O8" and row.get("stream") == "signal"
        for row in fresh_occ_all
    ):
        raise RuntimeError("fresh occupancy unexpectedly contains S3d signal transport")

    frozen_cells = geometry_rows(
        frozen_cells_all, "S3d_O8", label="104d frozen activation_cells"
    )
    fresh_cells = geometry_rows(fresh_cells_all, "SE3", label="fresh activation_cells")
    frozen_inventory = geometry_rows(
        frozen_inventory_all, "S3d_O8", label="104d frozen day15_inventory"
    )
    if any(row.get("geometry") != "SE3" for row in fresh_inventory_all):
        raise RuntimeError("fresh day15_inventory contains a non-SE3 row")
    # An exact zero-RP family may publish no isotope/state row at all.  Family
    # registration is closed by delayed_source_index.csv, not by inventing an
    # inventory sentinel.
    fresh_inventory = [dict(row) for row in fresh_inventory_all]
    for geometry, cells, inventory in (
        ("S3d_O8", frozen_cells, frozen_inventory),
        ("SE3", fresh_cells, fresh_inventory),
    ):
        cell_families = {row["incident_family"] for row in cells}
        inventory_families = {row["incident_family"] for row in inventory}
        if cell_families != set(FAMILY_ORDER):
            raise RuntimeError(f"{geometry} activation family closure differs")
        if geometry == "S3d_O8" and inventory_families != set(FAMILY_ORDER):
            raise RuntimeError(f"{geometry} legacy inventory family closure differs")
        unique_index(cells, ("incident_family",), label=f"{geometry} activation cells")

    fresh_registry = fresh_registered_source_contract(
        fresh_source_rows, fresh_zero_rows, fresh_inventory, fresh_common_all
    )

    frozen_lineage = geometry_rows(
        frozen_lineage_all, "S3d_O8", label="104d frozen W2 lineage"
    )
    fresh_lineage = [
        dict(row) for row in fresh_lineage_all if row.get("geometry") == "SE3"
    ]
    for label, rows in (("frozen S3d", frozen_lineage), ("fresh SE3", fresh_lineage)):
        if any(row["stream"] not in STREAMS for row in rows):
            raise RuntimeError(f"{label} selected-background lineage contains non-background rows")
        if any(row["family"] not in FAMILY_ORDER for row in rows):
            raise RuntimeError(f"{label} selected-background lineage contains an unknown family")
        if any(float(row["event_weight_cps"]) < 0.0 for row in rows):
            raise RuntimeError(f"{label} selected-background lineage has a negative weight")

    return {
        "frozen_s3d_background_cutflow_rows": len(frozen_background),
        "fresh_se3_background_cutflow_rows": len(fresh_background),
        "fresh_signal_rows": len(fresh_signal_all),
        "frozen_s3d_inventory_rows": len(frozen_inventory),
        "fresh_se3_inventory_rows": len(fresh_inventory),
        "fresh_se3_registered_source_cells": len(fresh_registry),
        "fresh_se3_zero_A15_families": [
            family for family in FAMILY_ORDER
            if fresh_registry[family]["execution_disposition"] == ZERO_DISPOSITION
        ],
        "frozen_s3d_lineage_rows": len(frozen_lineage),
        "fresh_se3_lineage_rows": len(fresh_lineage),
        "signal_scope": SIGNAL_SCOPE,
        "signal_trials_SE3": expected_trials,
        "fresh_s3d_signal_receipt_required": False,
        "s3d_full_envelope_signal_ratio_status": SIGNAL_RATIO_UNAVAILABLE,
        "old_post_be_signal_tables_opened": 0,
    }


def check_prerequisites(config_path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config_path = config_path.resolve()
    errors: list[str] = []
    missing_inputs: list[str] = []
    authority_missing: list[str] = []
    validated: dict[str, Any] = {}
    try:
        config = load_json(config_path)
    except Exception as exc:
        return {
            "schema_version": 1,
            "status": "FAIL__SE3_MATCHED_CONFIG",
            "ready": False,
            "errors": [str(exc)],
            "missing_inputs": [],
            "large_payload_access_policy": "NO_SIM_OR_CATALOG_OPEN_OR_HASH",
        }
    paths = input_paths(config)
    for role, path in paths.items():
        if not path.is_file() or path.stat().st_size <= 0:
            if role.startswith("fresh_"):
                missing_inputs.append(f"{role}:{path}")
            else:
                authority_missing.append(f"{role}:{path}")
    if authority_missing:
        errors.append(
            "required frozen S3d small-table authority missing: "
            + "; ".join(sorted(authority_missing))
        )
    if not missing_inputs and not authority_missing:
        try:
            validated = validate_small_table_contract(config, paths)
        except Exception as exc:
            errors.append(str(exc))
    ready = not errors and not missing_inputs
    if ready:
        status = "READY__SE3_MATCHED_SMALL_TABLES_AND_SE3_FULL_ENVELOPE_SIGNAL"
    elif errors:
        status = "FAIL__SE3_MATCHED_AUTHORITY_OR_CONTRACT"
    else:
        status = "NOT_READY__SE3_SMALL_TABLES_OR_SE3_SIGNAL_INCOMPLETE"
    return {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "status": status,
        "ready": ready,
        "config": str(config_path),
        "missing_inputs": missing_inputs,
        "authority_missing": authority_missing,
        "errors": errors,
        "validated": validated,
        "input_paths": {role: display_path(path) for role, path in paths.items()},
        "geometry_authority": {
            "S3d_O8_background_activation": "104d_frozen_M05_small_tables_only",
            "SE3_background_activation": "fresh_stage02_stage04",
            "S3d_O8_signal": SIGNAL_RATIO_UNAVAILABLE,
            "SE3_signal": "fresh_stage04_FULL_ENVELOPE_SE3_ONLY",
        },
        "fresh_s3d_receipt_required": False,
        "forbidden_signal_authority": "historical_post-Be_signal_not_a_ratio_denominator",
        "large_payload_access_policy": "CSV_JSON_STAT_ONLY__NO_SIM_OR_CATALOG_OPEN_OR_HASH",
    }


def optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    result = float(value)
    if not math.isfinite(result):
        return None
    return result


def isotope_label(za: int) -> str:
    z, a = divmod(za, 1000)
    return f"{ELEMENTS[z]}-{a}" if 0 <= z < len(ELEMENTS) else f"ZA-{za}"


def garwood_count_interval(count: int, confidence: float = 0.95) -> tuple[float, float]:
    if count < 0:
        raise ValueError("Poisson count must be non-negative")
    from scipy.stats import chi2

    alpha = 1.0 - confidence
    lower = 0.0 if count == 0 else 0.5 * float(chi2.ppf(alpha / 2.0, 2 * count))
    upper = 0.5 * float(chi2.ppf(1.0 - alpha / 2.0, 2 * (count + 1)))
    return lower, upper


def support_flag(count: int, *, structural_zero: bool = False) -> str:
    if structural_zero:
        return "NO_TRANSPORTED_ACTIVITY_SUPPORT__STRUCTURAL_ZERO"
    if count == 0:
        return "ZERO_MC_SURVIVOR__USE_TWO_SIDED_GARWOOD_AND_ONE_SIDED_UL"
    if count < 10:
        return "LOW_MC_SUPPORT__GARWOOD_INTERVAL_REQUIRED"
    return "FINITE_MC_SUPPORT"


def ratio_evidence(
    numerator: float,
    numerator_lower: float | None,
    numerator_upper: float | None,
    denominator: float,
    denominator_lower: float | None,
    denominator_upper: float | None,
    *,
    numerator_count: int | None = None,
    denominator_count: int | None = None,
) -> dict[str, Any]:
    central = numerator / denominator if denominator > 0.0 else None
    lower_proxy = None
    upper_proxy = None
    if denominator_upper is not None and denominator_upper > 0.0 and numerator_lower is not None:
        lower_proxy = numerator_lower / denominator_upper
    if denominator_lower is not None and denominator_lower > 0.0 and numerator_upper is not None:
        upper_proxy = numerator_upper / denominator_lower
    if denominator == 0.0 and numerator == 0.0:
        flag = "BOTH_CENTRAL_ZERO__RATIO_UNDEFINED__USE_BOTH_GARWOOD_UL"
    elif denominator == 0.0:
        flag = "S3D_DENOMINATOR_ZERO__CENTRAL_RATIO_UNDEFINED__USE_GARWOOD_BOUND"
    elif numerator == 0.0:
        flag = "SE3_NUMERATOR_ZERO__CENTRAL_ZERO_NOT_PHYSICAL_ZERO__USE_GARWOOD_UL"
    elif (numerator_count is not None and numerator_count < 10) or (
        denominator_count is not None and denominator_count < 10
    ):
        flag = "FINITE_CENTRAL_RATIO__LOW_MC_SUPPORT__INTERVAL_PROXY_PRIMARY"
    else:
        flag = "FINITE_CENTRAL_RATIO"
    return {
        "central": central,
        "lower95_proxy": lower_proxy,
        "upper95_proxy": upper_proxy,
        "flag": flag,
    }


def prefix_ratio(record: dict[str, Any], prefix: str, evidence: dict[str, Any]) -> None:
    record[f"{prefix}_central"] = evidence["central"]
    record[f"{prefix}_lower95_proxy"] = evidence["lower95_proxy"]
    record[f"{prefix}_upper95_proxy"] = evidence["upper95_proxy"]
    record[f"{prefix}_evidence_flag"] = evidence["flag"]


def common_key(row: dict[str, str]) -> tuple[str, str, str, str, str]:
    return (
        row["stream"], row["family"], row["response_state"], row["stage"], row["window_id"]
    )


def load_ready_inputs(
    config_path: Path,
) -> tuple[dict[str, Any], dict[str, Path], dict[str, Any], dict[str, Any]]:
    prerequisite = check_prerequisites(config_path)
    if not prerequisite["ready"]:
        raise RuntimeError(json.dumps(prerequisite, indent=2, sort_keys=True))
    config = load_json(config_path)
    paths = input_paths(config)

    frozen_common = background_common(
        read_csv(paths["frozen_s3d_common_cutflow"], COMMON_REQUIRED),
        "S3d_O8",
        "104d frozen common_cutflow",
    )
    fresh_common_all = read_csv(paths["fresh_common_cutflow"], COMMON_REQUIRED)
    fresh_se3_background = background_common(
        fresh_common_all, "SE3", "fresh common_cutflow"
    )
    fresh_se3_signal = signal_common(
        fresh_common_all, "SE3", "fresh common_cutflow"
    )
    common_by_geometry = {
        "S3d_O8": frozen_common,
        "SE3": fresh_se3_background + fresh_se3_signal,
    }

    frozen_occ_all = read_csv(paths["frozen_s3d_occupancy"], OCCUPANCY_REQUIRED)
    fresh_occ_all = read_csv(paths["fresh_common_occupancy"], OCCUPANCY_REQUIRED)
    occupancy_by_geometry = {
        "S3d_O8": [
            row for row in geometry_rows(
                frozen_occ_all, "S3d_O8", label="104d frozen occupancy"
            ) if row["stream"] in STREAMS
        ],
        "SE3": [
            row for row in geometry_rows(fresh_occ_all, "SE3", label="fresh occupancy")
            if row["stream"] in (*STREAMS, "signal")
        ],
    }

    frozen_lineage = geometry_rows(
        read_csv(paths["frozen_s3d_lineage"], LINEAGE_REQUIRED),
        "S3d_O8",
        label="104d frozen lineage",
    )
    fresh_lineage = [
        dict(row)
        for row in read_csv(paths["fresh_common_lineage"], LINEAGE_REQUIRED)
        if row.get("geometry") == "SE3"
    ]
    frozen_cells = geometry_rows(
        read_csv(paths["frozen_s3d_activation_cells"], ACTIVATION_CELL_REQUIRED),
        "S3d_O8",
        label="104d frozen activation cells",
    )
    fresh_cells = geometry_rows(
        read_csv(paths["fresh_se3_activation_cells"], ACTIVATION_CELL_REQUIRED),
        "SE3",
        label="fresh activation cells",
    )
    frozen_inventory = geometry_rows(
        read_csv(paths["frozen_s3d_inventory"], INVENTORY_REQUIRED),
        "S3d_O8",
        label="104d frozen inventory",
    )
    fresh_inventory = read_csv(paths["fresh_se3_inventory"], INVENTORY_REQUIRED)
    if any(row.get("geometry") != "SE3" for row in fresh_inventory):
        raise RuntimeError("fresh inventory contains a non-SE3 row")
    fresh_source_rows = read_csv(paths["fresh_se3_source_index"], SOURCE_INDEX_REQUIRED)
    fresh_zero_rows = read_csv(paths["fresh_zero_A15_provenance"], ZERO_PROVENANCE_REQUIRED)
    fresh_registry = fresh_registered_source_contract(
        fresh_source_rows, fresh_zero_rows, fresh_inventory, fresh_common_all
    )
    signal_rows = read_csv(paths["fresh_full_envelope_signal"], SIGNAL_REQUIRED)
    payload = {
        "common": common_by_geometry,
        "occupancy": occupancy_by_geometry,
        "lineage": {"S3d_O8": frozen_lineage, "SE3": fresh_lineage},
        "activation_cells": {"S3d_O8": frozen_cells, "SE3": fresh_cells},
        "inventory": {"S3d_O8": frozen_inventory, "SE3": fresh_inventory},
        "source_registry": {
            "S3d_O8": {
                family: {"execution_disposition": RUN_DISPOSITION}
                for family in FAMILY_ORDER
            },
            "SE3": fresh_registry,
        },
        "zero_A15_provenance": fresh_zero_rows,
        "signal": signal_rows,
        "fresh_common_summary": load_json(paths["fresh_common_summary"]),
        "fresh_activation_summary": load_json(paths["fresh_se3_activation_summary"]),
        "frozen_activation_summary": load_json(paths["frozen_s3d_activation_summary"]),
    }
    return config, paths, prerequisite, payload


def final_common_index(payload: dict[str, Any]) -> dict[tuple[str, str, str, str], dict[str, str]]:
    result: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for geometry in GEOMETRIES:
        for row in payload["common"][geometry]:
            if (
                row["stream"] in STREAMS
                and row["response_state"] == FINAL_RESPONSE
                and row["stage"] == FINAL_STAGE
                and row["window_id"] in WINDOWS
            ):
                key = (geometry, row["stream"], row["family"], row["window_id"])
                if key in result:
                    raise RuntimeError(f"duplicate final common-response row: {key}")
                result[key] = row
    expected = {
        (geometry, stream, family, window)
        for geometry in GEOMETRIES
        for stream in STREAMS
        for family in FAMILY_ORDER
        for window in WINDOWS
    }
    if set(result) != expected:
        raise RuntimeError("final background common-response closure differs")
    return result


def common_stat(row: dict[str, str]) -> dict[str, Any]:
    count = int(row["selected_events"])
    return {
        "generated_events": int(row["generated_events"]),
        "selected_events": count,
        "event_weight_cps": float(row["event_weight"]),
        "rate_cps": float(row["weighted_value"]),
        "stat_sigma_cps": float(row["weighted_stat_sigma"]),
        "lower95_cps": float(row["weighted_lower95"]),
        "upper95_cps": float(row["weighted_upper95"]),
        "support_flag": support_flag(count),
    }


def aggregate_component(
    final: dict[tuple[str, str, str, str], dict[str, str]],
    geometry: str,
    stream: str,
    window: str,
) -> dict[str, Any]:
    rows = [common_stat(final[(geometry, stream, family, window)]) for family in FAMILY_ORDER]
    count = sum(int(row["selected_events"]) for row in rows)
    return {
        "selected_events": count,
        "rate_cps": math.fsum(float(row["rate_cps"]) for row in rows),
        "stat_sigma_cps": math.sqrt(math.fsum(float(row["stat_sigma_cps"]) ** 2 for row in rows)),
        "lower95_sum_family_garwood_cps": math.fsum(float(row["lower95_cps"]) for row in rows),
        "upper95_sum_family_garwood_cps": math.fsum(float(row["upper95_cps"]) for row in rows),
        "support_flag": support_flag(count),
    }


def signal_index(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    selected = [
        row for row in rows
        if row["response_state"] == FINAL_RESPONSE and row["stage"] == FINAL_STAGE
        and row["window_id"] in WINDOWS
    ]
    result = unique_index(selected, ("geometry", "window_id"), label="final signal acceptance")
    expected = {("SE3", window) for window in WINDOWS}
    if set(result) != expected:
        raise RuntimeError("final SE3-only full-envelope signal closure differs")
    return result


def build_day15_comparison(payload: dict[str, Any]) -> list[dict[str, Any]]:
    final = final_common_index(payload)
    signals = signal_index(payload["signal"])
    output: list[dict[str, Any]] = []
    for window in WINDOWS:
        components = {
            (geometry, stream): aggregate_component(final, geometry, stream, window)
            for geometry in GEOMETRIES for stream in STREAMS
        }
        totals: dict[str, dict[str, Any]] = {}
        for geometry in GEOMETRIES:
            prompt_row = components[(geometry, "prompt")]
            delayed_row = components[(geometry, "delayed")]
            totals[geometry] = {
                "selected_events": prompt_row["selected_events"] + delayed_row["selected_events"],
                "rate_cps": prompt_row["rate_cps"] + delayed_row["rate_cps"],
                "stat_sigma_cps": math.hypot(
                    prompt_row["stat_sigma_cps"], delayed_row["stat_sigma_cps"]
                ),
                "lower95_sum_family_garwood_cps": (
                    prompt_row["lower95_sum_family_garwood_cps"]
                    + delayed_row["lower95_sum_family_garwood_cps"]
                ),
                "upper95_sum_family_garwood_cps": (
                    prompt_row["upper95_sum_family_garwood_cps"]
                    + delayed_row["upper95_sum_family_garwood_cps"]
                ),
            }
        record: dict[str, Any] = {
            "scope": "day15_matched_common_response_diagnostic",
            "profile_id": PROFILE_ID,
            "window_id": window,
            "response_state": FINAL_RESPONSE,
            "stage": FINAL_STAGE,
            "signal_scope": SIGNAL_SCOPE,
            "signal_geometry_ratio_status": SIGNAL_RATIO_UNAVAILABLE,
            "S3d_O8_full_envelope_signal_ratio_eligible": False,
            "SE3_full_envelope_signal_absolute_eligible": True,
            "old_post_be_S3d_signal_ratio_eligible": False,
            "fresh_s3d_signal_transport_required": False,
            "interval_note": "background bounds are sums of per-family two-sided Garwood bounds",
        }
        for geometry in GEOMETRIES:
            for stream in STREAMS:
                item = components[(geometry, stream)]
                for name, value in item.items():
                    record[f"{geometry}_{stream}_{name}"] = value
            for name, value in totals[geometry].items():
                record[f"{geometry}_background_{name}"] = value
        se3_signal = signals[("SE3", window)]
        for name in (
            "trials", "selected_events", "acceptance", "acceptance_lower95",
            "acceptance_upper95", "input_optics_aeff_cm2", "selected_effective_area_cm2",
            "selected_effective_area_lower95_cm2", "selected_effective_area_upper95_cm2",
        ):
            record[f"S3d_O8_signal_{name}"] = None
            record[f"SE3_signal_{name}"] = (
                int(se3_signal[name])
                if name in ("trials", "selected_events")
                else float(se3_signal[name])
            )

        for stream in STREAMS:
            se3 = components[("SE3", stream)]
            s3d = components[("S3d_O8", stream)]
            prefix_ratio(record, f"SE3_over_S3d_{stream}_rate", ratio_evidence(
                se3["rate_cps"], se3["lower95_sum_family_garwood_cps"],
                se3["upper95_sum_family_garwood_cps"], s3d["rate_cps"],
                s3d["lower95_sum_family_garwood_cps"], s3d["upper95_sum_family_garwood_cps"],
                numerator_count=se3["selected_events"], denominator_count=s3d["selected_events"],
            ))
        prefix_ratio(record, "SE3_over_S3d_background_rate", ratio_evidence(
            totals["SE3"]["rate_cps"], totals["SE3"]["lower95_sum_family_garwood_cps"],
            totals["SE3"]["upper95_sum_family_garwood_cps"], totals["S3d_O8"]["rate_cps"],
            totals["S3d_O8"]["lower95_sum_family_garwood_cps"],
            totals["S3d_O8"]["upper95_sum_family_garwood_cps"],
            numerator_count=totals["SE3"]["selected_events"],
            denominator_count=totals["S3d_O8"]["selected_events"],
        ))
        record["SE3_over_S3d_signal_aeff_central"] = None
        record["SE3_over_S3d_signal_aeff_lower95_proxy"] = None
        record["SE3_over_S3d_signal_aeff_upper95_proxy"] = None
        record["SE3_over_S3d_signal_aeff_evidence_flag"] = SIGNAL_RATIO_UNAVAILABLE
        se3_background = totals["SE3"]["rate_cps"]
        se3_aeff = float(se3_signal["selected_effective_area_cm2"])
        record["S3d_O8_aeff_over_sqrt_background_cm2_sqrt_s"] = None
        record["SE3_aeff_over_sqrt_background_cm2_sqrt_s"] = (
            se3_aeff / math.sqrt(se3_background) if se3_background > 0.0 else None
        )
        record["SE3_over_S3d_background_limited_coefficient"] = None
        record["coefficient_evidence_flag"] = (
            "SE3_ABSOLUTE_AVAILABLE__S3D_FULL_ENVELOPE_RATIO_UNAVAILABLE_BY_USER_SCOPE"
        )
        output.append(record)
    return output


def inventory_family_stats(rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {
        family: {
            "state_rows": 0,
            "transported_ground_activity_Bq": 0.0,
            "known_holdout_activity_Bq": 0.0,
            "unknown_activity_state_count": 0,
        } for family in FAMILY_ORDER
    }
    for row in rows:
        family = row["incident_family"]
        item = result[family]
        item["state_rows"] += 1
        activity = optional_float(row["day15_activity_Bq"])
        if row["source_disposition"] == "transported_ground_state":
            if activity is None:
                raise RuntimeError(f"transported inventory row lacks day15 activity: {family}")
            item["transported_ground_activity_Bq"] += activity
        elif activity is None:
            item["unknown_activity_state_count"] += 1
        else:
            item["known_holdout_activity_Bq"] += activity
    return result


def build_family_comparison(payload: dict[str, Any]) -> list[dict[str, Any]]:
    final = final_common_index(payload)
    cell_index = {
        geometry: unique_index(
            payload["activation_cells"][geometry], ("incident_family",),
            label=f"{geometry} activation family",
        ) for geometry in GEOMETRIES
    }
    inventory_stats = {
        geometry: inventory_family_stats(payload["inventory"][geometry])
        for geometry in GEOMETRIES
    }
    output: list[dict[str, Any]] = []
    for family in FAMILY_ORDER:
        record: dict[str, Any] = {
            "family": family,
            "window_id": "w2_510p58_511p42",
            "response_state": FINAL_RESPONSE,
            "stage": FINAL_STAGE,
        }
        for geometry in GEOMETRIES:
            cell = cell_index[geometry][(family,)]
            for field in (
                "N_BUILDUP_files", "generated_primaries", "sum_TT_s", "sum_RP",
                "production_rate_s-1", "zero_RP_files", "cell_status",
            ):
                value: Any = cell[field]
                if field in ("N_BUILDUP_files", "generated_primaries", "zero_RP_files"):
                    value = int(value)
                elif field != "cell_status":
                    value = float(value)
                record[f"{geometry}_activation_{field}"] = value
            for field, value in inventory_stats[geometry][family].items():
                record[f"{geometry}_day15_{field}"] = value
            registered = payload["source_registry"][geometry][family]
            record[f"{geometry}_execution_disposition"] = registered.get(
                "execution_disposition", RUN_DISPOSITION
            )
            record[f"{geometry}_zero_A15_finite_upper95_Bq"] = registered.get(
                "finite_A15_upper95_Bq"
            )
            record[f"{geometry}_zero_A15_upper_provenance"] = registered.get(
                "zero_A15_upper_provenance"
            )
            record[f"{geometry}_exact_empty_inventory_family"] = bool(
                registered.get("exact_empty_inventory_family", False)
            )
            for stream in STREAMS:
                stat = common_stat(final[(geometry, stream, family, "w2_510p58_511p42")])
                for field, value in stat.items():
                    record[f"{geometry}_{stream}_{field}"] = value
        for stream in STREAMS:
            se3 = common_stat(final[("SE3", stream, family, "w2_510p58_511p42")])
            s3d = common_stat(final[("S3d_O8", stream, family, "w2_510p58_511p42")])
            prefix_ratio(record, f"SE3_over_S3d_{stream}_rate", ratio_evidence(
                se3["rate_cps"], se3["lower95_cps"], se3["upper95_cps"],
                s3d["rate_cps"], s3d["lower95_cps"], s3d["upper95_cps"],
                numerator_count=se3["selected_events"], denominator_count=s3d["selected_events"],
            ))
        se3_activity = inventory_stats["SE3"][family]["transported_ground_activity_Bq"]
        s3d_activity = inventory_stats["S3d_O8"][family]["transported_ground_activity_Bq"]
        prefix_ratio(record, "SE3_over_S3d_transport_activity", ratio_evidence(
            se3_activity, se3_activity, se3_activity, s3d_activity, s3d_activity, s3d_activity
        ))
        output.append(record)
    return output


def inventory_dimension_key(row: dict[str, str], dimension: str) -> str:
    if dimension == "parent":
        return str(int(row["source_parent_ZA"]))
    if dimension == "material":
        return row["material_category"]
    if dimension == "volume":
        return row["source_volume"]
    raise ValueError(dimension)


def lineage_dimension_key(
    row: dict[str, str], dimension: str, material_by_volume: dict[str, str]
) -> str:
    if dimension == "parent":
        return str(int(row["source_parent_ZA"]))
    if dimension == "material":
        return material_by_volume[row["source_volume"]]
    if dimension == "volume":
        return row["source_volume"]
    raise ValueError(dimension)


def build_material_maps(payload: dict[str, Any]) -> dict[str, dict[str, str]]:
    output: dict[str, dict[str, str]] = {}
    for geometry in GEOMETRIES:
        mapping: dict[str, str] = {}
        for row in payload["inventory"][geometry]:
            volume = row["source_volume"]
            material = row["material_category"]
            old = mapping.setdefault(volume, material)
            if old != material:
                raise RuntimeError(f"{geometry}/{volume} has inconsistent material categories")
        output[geometry] = mapping
    return output


def delayed_family_weights(payload: dict[str, Any]) -> dict[tuple[str, str], float]:
    final = final_common_index(payload)
    result: dict[tuple[str, str], float] = {}
    for geometry in GEOMETRIES:
        for family in FAMILY_ORDER:
            row = final[(geometry, "delayed", family, "w2_510p58_511p42")]
            weight = float(row["event_weight"])
            disposition = payload.get("source_registry", {}).get(geometry, {}).get(
                family, {}
            ).get("execution_disposition", RUN_DISPOSITION)
            if disposition == ZERO_DISPOSITION:
                if weight != 0.0 or float(row["weighted_value"]) != 0.0:
                    raise RuntimeError(f"zero-source delayed central value differs: {geometry}/{family}")
            elif weight <= 0.0:
                raise RuntimeError(f"non-positive delayed event weight: {geometry}/{family}")
            result[(geometry, family)] = weight
    return result


def dimension_activity(
    payload: dict[str, Any], dimension: str
) -> tuple[
    dict[tuple[str, str], dict[str, Any]],
    dict[tuple[str, str], set[str]],
]:
    stats: dict[tuple[str, str], dict[str, Any]] = defaultdict(lambda: {
        "state_rows": 0,
        "transported_activity_Bq": 0.0,
        "known_holdout_activity_Bq": 0.0,
        "unknown_activity_state_count": 0,
    })
    support: dict[tuple[str, str], set[str]] = defaultdict(set)
    for geometry in GEOMETRIES:
        for row in payload["inventory"][geometry]:
            key = inventory_dimension_key(row, dimension)
            item = stats[(geometry, key)]
            item["state_rows"] += 1
            activity = optional_float(row["day15_activity_Bq"])
            if row["source_disposition"] == "transported_ground_state":
                if activity is None:
                    raise RuntimeError(f"transported activity missing: {geometry}/{dimension}/{key}")
                item["transported_activity_Bq"] += activity
                if activity > 0.0:
                    support[(geometry, key)].add(row["incident_family"])
            elif activity is None:
                item["unknown_activity_state_count"] += 1
            else:
                item["known_holdout_activity_Bq"] += activity
    return dict(stats), dict(support)


def dimension_lineage_counts(
    payload: dict[str, Any], dimension: str, material_maps: dict[str, dict[str, str]]
) -> tuple[Counter[tuple[str, str, str]], dict[tuple[str, str], float]]:
    counts: Counter[tuple[str, str, str]] = Counter()
    weighted: dict[tuple[str, str], float] = defaultdict(float)
    expected_weights = delayed_family_weights(payload)
    for geometry in GEOMETRIES:
        for row in payload["lineage"][geometry]:
            if row["stream"] != "delayed":
                continue
            key = lineage_dimension_key(row, dimension, material_maps[geometry])
            family = row["family"]
            weight = float(row["event_weight_cps"])
            if not math.isclose(
                weight, expected_weights[(geometry, family)], rel_tol=2.0e-12, abs_tol=1.0e-18
            ):
                raise RuntimeError(f"lineage/common-response weight mismatch: {geometry}/{family}")
            counts[(geometry, key, family)] += 1
            weighted[(geometry, key)] += weight
    return counts, dict(weighted)


def cellwise_lineage_stat(
    geometry: str,
    key: str,
    support_families: set[str],
    counts: Counter[tuple[str, str, str]],
    weights: dict[tuple[str, str], float],
) -> dict[str, Any]:
    if not support_families:
        return {
            "selected_events": 0,
            "rate_cps": 0.0,
            "stat_sigma_cps": 0.0,
            "lower95_sum_cellwise_garwood_cps": 0.0,
            "upper95_sum_cellwise_garwood_cps": 0.0,
            "zero_count_one_sided95_upper_sum_cellwise_cps": 0.0,
            "support_flag": support_flag(0, structural_zero=True),
        }
    selected = 0
    rate = sigma2 = lower = upper = 0.0
    for family in sorted(support_families, key=FAMILY_ORDER.index):
        count = counts[(geometry, key, family)]
        weight = weights[(geometry, family)]
        lo_count, hi_count = garwood_count_interval(count)
        selected += count
        rate += count * weight
        sigma2 += count * weight * weight
        lower += lo_count * weight
        upper += hi_count * weight
    one_sided = (
        math.fsum(-math.log(0.05) * weights[(geometry, family)] for family in support_families)
        if selected == 0 else 0.0
    )
    return {
        "selected_events": selected,
        "rate_cps": rate,
        "stat_sigma_cps": math.sqrt(sigma2),
        "lower95_sum_cellwise_garwood_cps": lower,
        "upper95_sum_cellwise_garwood_cps": upper,
        "zero_count_one_sided95_upper_sum_cellwise_cps": one_sided,
        "support_flag": support_flag(selected),
    }


def build_dimension_comparison(payload: dict[str, Any], dimension: str) -> list[dict[str, Any]]:
    material_maps = build_material_maps(payload)
    activity, support = dimension_activity(payload, dimension)
    counts, direct_weighted = dimension_lineage_counts(payload, dimension, material_maps)
    weights = delayed_family_weights(payload)
    keys = {
        key for _, key in activity
        if any(
            activity.get((geometry, key), {}).get(field, 0)
            for geometry in GEOMETRIES
            for field in (
                "transported_activity_Bq", "known_holdout_activity_Bq",
                "unknown_activity_state_count",
            )
        )
    } | {key for _, key, _ in counts}
    output: list[dict[str, Any]] = []
    for key in sorted(keys, key=lambda value: int(value) if dimension == "parent" else value):
        record: dict[str, Any] = {
            f"source_{dimension}": int(key) if dimension == "parent" else key,
            "selection_scope": "delayed measured W2 after explicit veto plus Step05",
            "interval_method": "sum of incident-family cellwise Garwood bounds; not a joint systematic interval",
        }
        if dimension == "parent":
            record["isotope_label"] = isotope_label(int(key))
        if dimension == "volume":
            for geometry in GEOMETRIES:
                record[f"{geometry}_material_category"] = material_maps[geometry].get(key, "")
        geometry_stats: dict[str, dict[str, Any]] = {}
        for geometry in GEOMETRIES:
            inv = activity.get((geometry, key), {
                "state_rows": 0,
                "transported_activity_Bq": 0.0,
                "known_holdout_activity_Bq": 0.0,
                "unknown_activity_state_count": 0,
            })
            selected = cellwise_lineage_stat(
                geometry, key, support.get((geometry, key), set()), counts, weights
            )
            if not math.isclose(
                selected["rate_cps"], direct_weighted.get((geometry, key), 0.0),
                rel_tol=2.0e-12, abs_tol=1.0e-18,
            ):
                raise RuntimeError(f"lineage aggregation closure differs: {geometry}/{dimension}/{key}")
            geometry_stats[geometry] = {**inv, **selected}
            for name, value in inv.items():
                record[f"{geometry}_{name}"] = value
            for name, value in selected.items():
                record[f"{geometry}_selected_{name}"] = value
        se3 = geometry_stats["SE3"]
        s3d = geometry_stats["S3d_O8"]
        prefix_ratio(record, "SE3_over_S3d_transport_activity", ratio_evidence(
            se3["transported_activity_Bq"], se3["transported_activity_Bq"],
            se3["transported_activity_Bq"], s3d["transported_activity_Bq"],
            s3d["transported_activity_Bq"], s3d["transported_activity_Bq"],
        ))
        prefix_ratio(record, "SE3_over_S3d_selected_rate", ratio_evidence(
            se3["rate_cps"], se3["lower95_sum_cellwise_garwood_cps"],
            se3["upper95_sum_cellwise_garwood_cps"], s3d["rate_cps"],
            s3d["lower95_sum_cellwise_garwood_cps"],
            s3d["upper95_sum_cellwise_garwood_cps"],
            numerator_count=se3["selected_events"], denominator_count=s3d["selected_events"],
        ))
        output.append(record)
    return output


def build_cutflow_comparison(payload: dict[str, Any]) -> list[dict[str, Any]]:
    index_keys = ("stream", "family", "response_state", "stage", "window_id")
    background_indexes = {
        geometry: unique_index(
            [row for row in payload["common"][geometry] if row["stream"] in STREAMS],
            index_keys,
            label=f"{geometry} background common cutflow",
        )
        for geometry in GEOMETRIES
    }
    if set(background_indexes["S3d_O8"]) != set(background_indexes["SE3"]):
        raise RuntimeError("matched background common cutflow key closure differs")
    se3_signal_index = unique_index(
        [row for row in payload["common"]["SE3"] if row["stream"] == "signal"],
        index_keys,
        label="SE3 full-envelope signal common cutflow",
    )
    output: list[dict[str, Any]] = []
    for key in sorted(background_indexes["S3d_O8"]):
        record: dict[str, Any] = {
            "stream": key[0], "family": key[1], "response_state": key[2],
            "stage": key[3], "window_id": key[4],
            "signal_scope": "NOT_APPLICABLE_BACKGROUND",
            "S3d_O8_authority": "104d_frozen_M05_small_table",
            "SE3_authority": "fresh_stage04",
        }
        stats: dict[str, dict[str, Any]] = {}
        for geometry in GEOMETRIES:
            stat = common_stat(background_indexes[geometry][key])
            stats[geometry] = stat
            for name, value in stat.items():
                record[f"{geometry}_{name}"] = value
        prefix_ratio(record, "SE3_over_S3d_weighted_value", ratio_evidence(
            stats["SE3"]["rate_cps"], stats["SE3"]["lower95_cps"],
            stats["SE3"]["upper95_cps"], stats["S3d_O8"]["rate_cps"],
            stats["S3d_O8"]["lower95_cps"], stats["S3d_O8"]["upper95_cps"],
            numerator_count=stats["SE3"]["selected_events"],
            denominator_count=stats["S3d_O8"]["selected_events"],
        ))
        output.append(record)
    for key in sorted(se3_signal_index):
        se3_stat = common_stat(se3_signal_index[key])
        record = {
            "stream": key[0], "family": key[1], "response_state": key[2],
            "stage": key[3], "window_id": key[4],
            "signal_scope": SIGNAL_SCOPE,
            "S3d_O8_authority": SIGNAL_RATIO_UNAVAILABLE,
            "SE3_authority": "fresh_stage04_FULL_ENVELOPE_SE3_ONLY",
        }
        for name in se3_stat:
            record[f"S3d_O8_{name}"] = None
            record[f"SE3_{name}"] = se3_stat[name]
        record["SE3_over_S3d_weighted_value_central"] = None
        record["SE3_over_S3d_weighted_value_lower95_proxy"] = None
        record["SE3_over_S3d_weighted_value_upper95_proxy"] = None
        record["SE3_over_S3d_weighted_value_evidence_flag"] = SIGNAL_RATIO_UNAVAILABLE
        output.append(record)
    return output


def build_occupancy_comparison(payload: dict[str, Any]) -> list[dict[str, Any]]:
    background_indexes = {
        geometry: unique_index(
            [row for row in payload["occupancy"][geometry] if row["stream"] in STREAMS],
            ("stream", "family"),
            label=f"{geometry} matched background occupancy",
        ) for geometry in GEOMETRIES
    }
    if set(background_indexes["S3d_O8"]) != set(background_indexes["SE3"]):
        raise RuntimeError("matched background occupancy key closure differs")
    se3_signal_index = unique_index(
        [row for row in payload["occupancy"]["SE3"] if row["stream"] == "signal"],
        ("stream", "family"),
        label="SE3 full-envelope signal occupancy",
    )
    output: list[dict[str, Any]] = []
    for stream, family in sorted(background_indexes["S3d_O8"]):
        record: dict[str, Any] = {
            "stream": stream,
            "family": family,
            "signal_scope": "NOT_APPLICABLE_BACKGROUND",
        }
        for geometry in GEOMETRIES:
            row = background_indexes[geometry][(stream, family)]
            for field in (
                "generated_events", "detector_occupancy_events", "tes_positive_events",
                "active_only_events", "pixel_hits",
            ):
                record[f"{geometry}_{field}"] = int(row[field])
            for field in (
                "weighted_occupancy", "weighted_tes", "weighted_active_only", "weighted_stat_sigma",
            ):
                record[f"{geometry}_{field}"] = float(row[field])
            record[f"{geometry}_support_flag"] = support_flag(
                int(row["detector_occupancy_events"])
            )
        ratio = ratio_evidence(
            record["SE3_weighted_occupancy"], None, None,
            record["S3d_O8_weighted_occupancy"], None, None,
            numerator_count=record["SE3_detector_occupancy_events"],
            denominator_count=record["S3d_O8_detector_occupancy_events"],
        )
        prefix_ratio(record, "SE3_over_S3d_weighted_occupancy", ratio)
        output.append(record)
    for (stream, family), row in sorted(se3_signal_index.items()):
        record = {
            "stream": stream,
            "family": family,
            "signal_scope": SIGNAL_SCOPE,
        }
        for field in (
            "generated_events", "detector_occupancy_events", "tes_positive_events",
            "active_only_events", "pixel_hits",
        ):
            record[f"S3d_O8_{field}"] = None
            record[f"SE3_{field}"] = int(row[field])
        for field in (
            "weighted_occupancy", "weighted_tes", "weighted_active_only", "weighted_stat_sigma",
        ):
            record[f"S3d_O8_{field}"] = None
            record[f"SE3_{field}"] = float(row[field])
        record["S3d_O8_support_flag"] = SIGNAL_RATIO_UNAVAILABLE
        record["SE3_support_flag"] = support_flag(int(row["detector_occupancy_events"]))
        record["SE3_over_S3d_weighted_occupancy_central"] = None
        record["SE3_over_S3d_weighted_occupancy_lower95_proxy"] = None
        record["SE3_over_S3d_weighted_occupancy_upper95_proxy"] = None
        record["SE3_over_S3d_weighted_occupancy_evidence_flag"] = SIGNAL_RATIO_UNAVAILABLE
        output.append(record)
    return output


def provenance_rows(paths: dict[str, Path]) -> list[dict[str, Any]]:
    roles = {
        "frozen_s3d_common_cutflow": "S3d prompt+delayed only; strict geometry filter",
        "frozen_s3d_occupancy": "S3d prompt+delayed only; strict geometry filter",
        "frozen_s3d_lineage": "S3d selected background W2 only; strict geometry filter",
        "frozen_s3d_activation_cells": "S3d activation only; strict geometry filter",
        "frozen_s3d_inventory": "S3d day15 activation only; strict geometry filter",
        "frozen_s3d_activation_summary": "S3d activation status only; no signal content",
        "fresh_se3_activation_cells": "SE3 activation",
        "fresh_se3_inventory": "SE3 day15 activation",
        "fresh_se3_activation_summary": "SE3 activation status",
        "fresh_se3_source_index": "SE3 eight-family RUN_83334/SKIP_ZERO_A15 registration authority",
        "fresh_common_cutflow": "SE3 background plus fresh SE3-only full-envelope signal",
        "fresh_common_occupancy": "SE3 background plus fresh SE3-only full-envelope signal",
        "fresh_common_lineage": "SE3 selected background W2",
        "fresh_full_envelope_signal": "SE3-only full-envelope signal acceptance authority",
        "fresh_common_summary": "FULL_ENVELOPE_SE3_ONLY scope gate",
        "fresh_zero_A15_provenance": "SE3 exact-zero central cells and finite activation upper provenance",
    }
    return [{
        "role": role,
        "path": display_path(path),
        "bytes": path.stat().st_size,
        "row_filter_or_use": roles[role],
        "large_payload_opened": False,
        "hash_recomputed": False,
    } for role, path in paths.items()]


def build_report(day15: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    w2 = next(row for row in day15 if row["window_id"] == "w2_510p58_511p42")
    return "\n".join([
        "# S3d-O8 versus SE3 matched day-15 comparison",
        "",
        f"Status: `{summary['status']}`",
        "",
        "| W2 measured after explicit veto + Step05 | S3d-O8 | SE3 | SE3/S3d |",
        "|---|---:|---:|---:|",
        (
            f"| prompt (cps) | {w2['S3d_O8_prompt_rate_cps']:.8g} | "
            f"{w2['SE3_prompt_rate_cps']:.8g} | "
            f"{w2['SE3_over_S3d_prompt_rate_central']!s} |"
        ),
        (
            f"| delayed day15 (cps) | {w2['S3d_O8_delayed_rate_cps']:.8g} | "
            f"{w2['SE3_delayed_rate_cps']:.8g} | "
            f"{w2['SE3_over_S3d_delayed_rate_central']!s} |"
        ),
        (
            f"| total background (cps) | {w2['S3d_O8_background_rate_cps']:.8g} | "
            f"{w2['SE3_background_rate_cps']:.8g} | "
            f"{w2['SE3_over_S3d_background_rate_central']!s} |"
        ),
        (
            f"| full-envelope selected Aeff (cm²) | unavailable by user scope | "
            f"{w2['SE3_signal_selected_effective_area_cm2']:.8g} | "
            f"{SIGNAL_RATIO_UNAVAILABLE} |"
        ),
        "",
        (
            "S3d-O8 background and activation use only strictly filtered 104d frozen small tables. "
            "Fresh signal transport is SE3-only. No fresh S3d receipt is required. The historical "
            "post-Be S3d signal is not substituted for the missing fair full-envelope denominator."
        ),
        "",
        (
            "Zero survivors retain two-sided Garwood bounds and a one-sided upper-limit flag. "
            "Central ratios are never treated as promotion authority when either side has zero or "
            "low Monte Carlo support. Mission folding and F3 remain stage06 work."
        ),
        (
            "A fresh SKIP_ZERO_A15 family retains an exact central zero without an invented isotope "
            "row. Its finite activation upper and holdout-separation provenance remain machine-readable "
            "in family_comparison.csv and summary.json for the conservative stage06 proxy."
        ),
        "",
    ])


def run(config_path: Path, output: Path) -> dict[str, Any]:
    config, paths, prerequisite, payload = load_ready_inputs(config_path)
    if output.exists():
        raise FileExistsError(f"refusing to overwrite matched output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f".{output.name}.work-", dir=output.parent))
    try:
        day15 = build_day15_comparison(payload)
        family = build_family_comparison(payload)
        parent = build_dimension_comparison(payload, "parent")
        material = build_dimension_comparison(payload, "material")
        volume = build_dimension_comparison(payload, "volume")
        cutflow = build_cutflow_comparison(payload)
        occupancy = build_occupancy_comparison(payload)
        provenance = provenance_rows(paths)

        write_csv(work / "s3d_o8_vs_se3_day15.csv", day15)
        write_csv(work / "family_comparison.csv", family)
        write_csv(work / "parent_comparison.csv", parent)
        write_csv(work / "material_comparison.csv", material)
        write_csv(work / "volume_comparison.csv", volume)
        write_csv(work / "cutflow_comparison.csv", cutflow)
        write_csv(work / "occupancy_comparison.csv", occupancy)
        write_csv(work / "input_provenance.csv", provenance)

        w2 = next(row for row in day15 if row["window_id"] == "w2_510p58_511p42")
        summary = {
            "schema_version": 1,
            "profile_id": PROFILE_ID,
            "status": "PASS__SE3_PLAN1_DAY15_BACKGROUND_COMPARISON_AND_SE3_ONLY_FULL_ENVELOPE_SIGNAL",
            "geometries": list(GEOMETRIES),
            "signal_scope": SIGNAL_SCOPE,
            "signal_authority": {
                "S3d_O8": SIGNAL_RATIO_UNAVAILABLE,
                "SE3": display_path(paths["fresh_full_envelope_signal"]),
                "SE3_trials": int(config["signal"]["eventlist_rows"]),
                "fresh_s3d_receipt_required": False,
                "historical_post_be_signal_opened": False,
                "historical_post_be_scope": "CONTINUITY_ONLY__RATIO_ELIGIBLE_FALSE",
                "historical_post_be_used_as_denominator": False,
            },
            "background_activation_authority": {
                "S3d_O8": "strictly filtered 104d frozen M05 CSV rows",
                "SE3": "fresh stage02/stage04 CSV rows",
            },
            "w2": w2,
            "row_counts": {
                "day15": len(day15), "family": len(family), "parent": len(parent),
                "material": len(material), "volume": len(volume), "cutflow": len(cutflow),
                "occupancy": len(occupancy),
            },
            "zero_count_policy": {
                "two_sided": "95% Garwood per incident-family cell",
                "zero_one_sided": "95% Poisson UL = -ln(0.05), summed cellwise when applicable",
                "ratio": "central ratio blank when S3d denominator is zero; evidence flag always retained",
                "SKIP_ZERO_A15": (
                    "central delayed response remains exactly zero with no isotope sentinel; "
                    "finite activation upper provenance is retained for stage06"
                ),
                "SE3_zero_A15_families": [
                    family for family in FAMILY_ORDER
                    if payload["source_registry"]["SE3"][family]["execution_disposition"]
                    == ZERO_DISPOSITION
                ],
                "SE3_zero_A15_provenance": {
                    family: payload["source_registry"]["SE3"][family]
                    for family in FAMILY_ORDER
                    if payload["source_registry"]["SE3"][family]["execution_disposition"]
                    == ZERO_DISPOSITION
                },
            },
            "source_mix_boundary": (
                "stride-5 position-mixture uncertainty remains separate from transport-count MC intervals"
            ),
            "state_boundary": (
                "non-ground and unresolved NUBASE state holdouts remain outside transported delayed rates"
            ),
            "large_payload_policy": "small CSV/JSON tables only; no SIM, catalog, or large-payload hash",
            "prerequisite_status": prerequisite["status"],
            "authority_boundary": (
                "MATCHED_DAY15_BACKGROUND_AND_SE3_ABSOLUTE_FULL_ENVELOPE_DIAGNOSTIC__"
                "S3D_SIGNAL_RATIO_UNAVAILABLE_BY_USER_SCOPE"
            ),
        }
        write_json(work / "summary.json", summary)
        (work / "REPORT.md").write_text(build_report(day15, summary), encoding="utf-8")
        files = sorted(path for path in work.iterdir() if path.is_file())
        manifest = {
            "schema_version": 1,
            "profile_id": PROFILE_ID,
            "status": summary["status"],
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "analysis_code": display_path(HERE),
            "inputs": provenance,
            "files": [
                {"path": path.name, "bytes": path.stat().st_size} for path in files
            ],
            "hash_policy": "No large artifact or SIM was opened or hashed.",
            "forbidden_old_post_be_signal_inputs": [],
        }
        write_json(work / "manifest.json", manifest)
        os.rename(work, output)
        print(json.dumps({
            "status": summary["status"],
            "output": str(output),
            "w2_background_ratio": w2["SE3_over_S3d_background_rate_central"],
            "w2_signal_aeff_ratio": SIGNAL_RATIO_UNAVAILABLE,
        }, sort_keys=True))
        return summary
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise


def self_test() -> dict[str, Any]:
    lower0, upper0 = garwood_count_interval(0)
    if lower0 != 0.0 or not math.isclose(upper0, 3.6888794541139354, rel_tol=1e-12):
        raise AssertionError("zero-count two-sided Garwood self-test failed")
    finite = ratio_evidence(2.0, 1.0, 3.0, 4.0, 2.0, 6.0, numerator_count=2, denominator_count=4)
    if finite["central"] != 0.5 or finite["lower95_proxy"] != 1.0 / 6.0:
        raise AssertionError("finite ratio self-test failed")
    zero_den = ratio_evidence(1.0, 0.2, 2.0, 0.0, 0.0, 3.0, numerator_count=1, denominator_count=0)
    if zero_den["central"] is not None or "DENOMINATOR_ZERO" not in zero_den["flag"]:
        raise AssertionError("zero-denominator ratio self-test failed")
    both_zero = ratio_evidence(0.0, 0.0, 1.0, 0.0, 0.0, 2.0, numerator_count=0, denominator_count=0)
    if both_zero["central"] is not None or "BOTH_CENTRAL_ZERO" not in both_zero["flag"]:
        raise AssertionError("both-zero ratio self-test failed")
    synthetic_signal = [
        {"geometry": geometry, "signal_scope": SIGNAL_SCOPE, "trials": "37194"}
        for geometry in FRESH_SIGNAL_GEOMETRIES
    ]
    if {row["geometry"] for row in synthetic_signal} != set(FRESH_SIGNAL_GEOMETRIES) or any(
        row["signal_scope"] != SIGNAL_SCOPE for row in synthetic_signal
    ):
        raise AssertionError("SE3-only full-envelope signal prerequisite self-test failed")
    if SIGNAL_RATIO_UNAVAILABLE != "UNAVAILABLE_BY_USER_SCOPE":
        raise AssertionError("machine-readable unavailable status drift")
    zero_family = FAMILY_ORDER[0]
    finite_upper = 0.125
    source_rows = [{
        "geometry": "SE3",
        "incident_family": family,
        "execution_disposition": ZERO_DISPOSITION if family == zero_family else RUN_DISPOSITION,
        "transported_ground_activity_Bq": "0" if family == zero_family else "1",
        "transported_ground_rate_upper95_s-1": str(finite_upper) if family == zero_family else "",
        "transported_ground_A15_upper95_Bq_conservative": str(finite_upper) if family == zero_family else "",
        "zero_A15_upper_provenance": "finite 3.688879/sumTT" if family == zero_family else "",
    } for family in FAMILY_ORDER]
    inventory_rows = [{
        "geometry": "SE3", "incident_family": family,
        "source_disposition": "transported_ground_state", "day15_activity_Bq": "1",
    } for family in FAMILY_ORDER if family != zero_family]
    common_rows = [{
        "geometry": "SE3", "stream": "delayed", "family": family,
        "selected_events": "0", "event_weight": "0", "weighted_value": "0",
        "execution_disposition": ZERO_DISPOSITION,
        "transported_ground_A15_upper95_Bq_conservative": str(finite_upper),
    } for family in (zero_family,)]
    zero_rows = [{
        "geometry": "SE3", "family": zero_family,
        "execution_disposition": ZERO_DISPOSITION,
        "central_delayed_rate_cps": "0", "transported_ground_activity_Bq": "0",
        "transported_ground_rate_upper95_s-1": str(finite_upper),
        "transported_ground_A15_upper95_Bq_conservative": str(finite_upper),
        "zero_A15_upper_provenance": "finite 3.688879/sumTT",
        "upper_excludes_known_and_unresolved_holdout": "true",
        "stage03_catalog_opened": "false", "SIM_opened": "false",
    }]
    registry = fresh_registered_source_contract(
        source_rows, zero_rows, inventory_rows, common_rows
    )
    if (
        registry[zero_family]["execution_disposition"] != ZERO_DISPOSITION
        or not registry[zero_family]["exact_empty_inventory_family"]
        or registry[zero_family]["finite_A15_upper95_Bq"] != finite_upper
        or any(row["incident_family"] == zero_family for row in inventory_rows)
    ):
        raise AssertionError("exact-empty zero-RP family registry self-test failed")
    return {
        "schema_version": 1,
        "status": "PASS__SE3_MATCHED_ADAPTER_SYNTHETIC_SELF_TEST",
        "checks": [
            "zero_count_two_sided_Garwood",
            "finite_ratio_interval_proxy",
            "zero_denominator_fail_closed_ratio",
            "both_zero_fail_closed_ratio",
            "SE3_only_FULL_ENVELOPE_signal_scope",
            "S3d_full_envelope_ratio_unavailable_by_user_scope",
            "RUN_plus_SKIPPED_ZERO_registered_family_closure",
            "exact_empty_zero_RP_inventory_without_isotope_sentinel",
            "zero_A15_central_zero_and_finite_upper_provenance",
        ],
        "files_opened": 0,
        "sim_opened": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--check-prerequisites", action="store_true")
    actions.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), indent=2, sort_keys=True))
        return 0
    config_path = args.config.resolve()
    if args.check_prerequisites:
        result = check_prerequisites(config_path)
        print(json.dumps(result, indent=2, sort_keys=True))
        if result["ready"]:
            return 0
        return 2 if str(result.get("status", "")).startswith("NOT_READY__") else 1
    config = load_json(config_path)
    output = args.output or Path(config["outputs"]["stage_05"])
    run(config_path, output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
