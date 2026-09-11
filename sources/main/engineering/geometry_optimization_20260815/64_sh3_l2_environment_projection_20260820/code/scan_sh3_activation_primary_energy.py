#!/usr/bin/env python3
"""Join SH3 activation records to their incident primary energies.

The scan is intentionally semantic-only: it reads each retained rich SIM once,
joins ``CC IP RP`` records to the unique ``IA INIT`` in the same event, and
checks counts against the already-PASS activation manifest.  It does not hash
the 14 GB SIM payload.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import os
import re
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from decimal import Decimal
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
MANIFEST = Path(
    "/mnt/data/TES_Balloon_511_data/SH3/"
    "sh3_optv3_m05_delayed_activation_v1/generated/activation/manifest.json"
)
SELECTED = (
    ROOT
    / "engineering/geometry_optimization_20260815/"
    "63_m05new_sg3b_signal_statistics_20260820/outputs/05_optv3_delayed_origins/"
    "optv3_delayed_selected_events.csv"
)
OUTPUT = PACKAGE / "outputs/tables/sh3_activation_selected_key_primary_energy.csv.gz"
SUMMARY = PACKAGE / "data/activation_primary_energy_scan_summary.json"

CC_RP_RE = re.compile(
    r"^CC\s+IP\s+RP\s+(?P<volume>\S+)\s+"
    r"(?P<x>[-+0-9.eE]+)\s+(?P<y>[-+0-9.eE]+)\s+"
    r"(?P<z>[-+0-9.eE]+)\s+(?P<za>\d+)\s+"
    r"(?P<exc>[-+0-9.eE]+)\s+(?P<t>[-+0-9.eE]+)"
)
INCLUDE_RE = re.compile(r"^\s*Include\s+(\S+)\s*$")
COPY_RE = re.compile(r"^\s*(?P<logical>\S+)\.Copy\s+(?P<physical>\S+)\s*$")


def canonical_excitation(value: float | str) -> float:
    raw = Decimal(str(value)).quantize(Decimal("0.01"))
    return 0.0 if raw == 0 else float(raw)


def parse_init(line: str) -> float:
    fields = [item.strip() for item in line[len("IA INIT") :].split(";")]
    if len(fields) < 23:
        raise RuntimeError(f"Malformed IA INIT: {line.rstrip()}")
    energy = float(fields[22])
    if not (math.isfinite(energy) and energy >= 0.0):
        raise RuntimeError(f"Invalid IA INIT energy: {line.rstrip()}")
    return energy


def geometry_copy_map(setup: Path) -> dict[str, str]:
    """Use the same MEGAlib ``logical.Copy physical`` mapping as activation preparation."""
    mapping: dict[str, str] = {}
    visited: set[Path] = set()

    def visit(path: Path) -> None:
        resolved = path.resolve()
        if resolved in visited or not resolved.is_file():
            return
        visited.add(resolved)
        for raw in resolved.read_text(encoding="utf-8", errors="replace").splitlines():
            include = INCLUDE_RE.match(raw)
            if include:
                child = Path(include.group(1))
                visit(child if child.is_absolute() else resolved.parent / child)
                continue
            copy = COPY_RE.match(raw)
            if not copy:
                continue
            logical, physical = copy.group("logical"), copy.group("physical")
            old = mapping.get(physical)
            if old is not None and old != logical:
                raise RuntimeError(f"Conflicting geometry Copy mapping: {physical}: {old} vs {logical}")
            mapping[physical] = logical

    visit(setup)
    return mapping


def scan_one(task: dict[str, Any]) -> dict[str, Any]:
    path = Path(task["path"])
    family = str(task["family"])
    wanted = {
        (str(volume), int(za), canonical_excitation(exc))
        for volume, za, exc in task["wanted"]
    }
    copy_map = {str(key): str(value) for key, value in task["copy_map"].items()}
    logical_volumes = {key[0] for key in wanted}
    rows: list[tuple[Any, ...]] = []
    counts: Counter[tuple[str, int, float]] = Counter()
    current_id: int | None = None
    current_energy: float | None = None
    init_count = 0
    cc_lines = 0
    pending: list[re.Match[str]] = []

    def flush_event() -> None:
        nonlocal pending
        if not pending:
            return
        if current_id is None or current_energy is None or init_count != 1:
            raise RuntimeError(f"RP record without unique IA INIT in {path}, event {current_id}")
        for match in pending:
            physical = match.group("volume")
            candidates: set[str] = set()
            if physical in logical_volumes:
                candidates.add(physical)
            copied = copy_map.get(physical)
            if copied in logical_volumes:
                candidates.add(str(copied))
            if len(candidates) != 1:
                continue
            key = (
                next(iter(candidates)),
                int(match.group("za")),
                canonical_excitation(match.group("exc")),
            )
            if key not in wanted:
                continue
            counts[key] += 1
            rows.append(
                (
                    family,
                    key[0],
                    key[1],
                    key[2],
                    current_energy,
                    current_id,
                    str(path),
                )
            )
        pending = []

    with gzip.open(path, "rt", encoding="utf-8", errors="strict") as stream:
        for raw in stream:
            if raw.startswith("SE"):
                flush_event()
                current_id = None
                current_energy = None
                init_count = 0
                continue
            if raw.startswith("ID "):
                parts = raw.split()
                if len(parts) < 2:
                    raise RuntimeError(f"Malformed ID in {path}: {raw.rstrip()}")
                current_id = int(parts[1])
                continue
            if raw.startswith("IA INIT"):
                init_count += 1
                if init_count != 1:
                    raise RuntimeError(f"Multiple IA INIT records in {path}, event {current_id}")
                current_energy = parse_init(raw)
                continue
            if not raw.startswith("CC IP RP "):
                continue
            cc_lines += 1
            match = CC_RP_RE.match(raw)
            if match is None:
                raise RuntimeError(f"Malformed CC IP RP in {path}: {raw.rstrip()}")
            pending.append(match)
    flush_event()
    return {"path": str(path), "family": family, "cc_lines": cc_lines, "rows": rows, "counts": counts}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()

    if not MANIFEST.is_file() or not SELECTED.is_file():
        raise RuntimeError("Required SH3 activation authority is missing")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("status") != "PASS__SH3_OPTV3_M05_DAY15_ACTIVATION_AND_DELAYED_SOURCES_READY":
        raise RuntimeError(f"Activation manifest is not PASS: {manifest.get('status')}")
    if any(int(row.get("unmatched_state_points", 0)) for row in manifest["rpip_scans"]):
        raise RuntimeError("Activation manifest retains unmatched states")
    if any(int(row.get("unmatched_volume_points", 0)) for row in manifest["rpip_scans"]):
        raise RuntimeError("Activation manifest retains unmatched volumes")

    with SELECTED.open("r", encoding="utf-8", newline="") as stream:
        selected_rows = list(csv.DictReader(stream))
    selected_keys = {
        (
            row["family"],
            row["source_volume"],
            int(row["source_parent_ZA"]),
            canonical_excitation(row["excitation_keV"]),
        )
        for row in selected_rows
    }

    expected: dict[tuple[str, str, int, float], int] = {}
    for cell in manifest["source_cells"]:
        family = str(cell["family"])
        for state in cell["included_states"]:
            key = (
                family,
                str(state["volume"]),
                int(state["ZA"]),
                canonical_excitation(state["excitation_keV"]),
            )
            expected[key] = int(round(float(state["sum_RP"])))
    missing_from_manifest = sorted(selected_keys - set(expected))
    if missing_from_manifest:
        raise RuntimeError(f"Selected delayed keys absent from activation manifest: {missing_from_manifest[:5]}")

    wanted_by_family: dict[str, list[tuple[str, int, float]]] = {}
    for family, volume, za, exc in sorted(selected_keys):
        wanted_by_family.setdefault(family, []).append((volume, za, exc))
    geometry = Path(manifest["geometry"])
    if not geometry.is_file():
        raise RuntimeError(f"Missing SH3 geometry used by activation manifest: {geometry}")
    copy_map = geometry_copy_map(geometry)
    tasks = []
    for scan in manifest["rpip_scans"]:
        family = str(scan["family"])
        if family not in wanted_by_family:
            continue
        path = Path(scan["sim_path"])
        if not path.is_file():
            raise RuntimeError(f"Missing retained rich SIM: {path}")
        tasks.append(
            {
                "path": str(path),
                "family": family,
                "wanted": wanted_by_family[family],
                "copy_map": copy_map,
            }
        )

    all_rows: list[tuple[Any, ...]] = []
    observed: Counter[tuple[str, str, int, float]] = Counter()
    scanned_cc_lines = 0
    with ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(scan_one, task) for task in tasks]
        for future in as_completed(futures):
            result = future.result()
            scanned_cc_lines += int(result["cc_lines"])
            all_rows.extend(result["rows"])
            for (volume, za, exc), count in result["counts"].items():
                observed[(result["family"], volume, za, exc)] += int(count)

    # Preserve the small joined table before final closure so a validation
    # issue can be diagnosed without expanding the 14-GB SIM set again.
    all_rows.sort(key=lambda row: (row[0], row[1], row[2], row[3], row[6], row[5]))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = OUTPUT.with_name(f".{OUTPUT.name}.unvalidated")
    with gzip.open(checkpoint, "wt", encoding="utf-8", newline="", compresslevel=6) as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(
            [
                "incident_family",
                "source_volume",
                "source_parent_ZA",
                "source_excitation_keV",
                "primary_energy_keV_total",
                "local_event_id",
                "source_file",
            ]
        )
        writer.writerows(all_rows)

    scanned_families = set(wanted_by_family)
    manifest_cc_lines = sum(
        int(row["CC_IP_RP_lines"])
        for row in manifest["rpip_scans"]
        if str(row["family"]) in scanned_families
    )
    if scanned_cc_lines != manifest_cc_lines:
        raise RuntimeError(f"CC-line closure failed: observed={scanned_cc_lines}, expected={manifest_cc_lines}")
    mismatches = {
        "|".join(map(str, key)): {"observed": observed.get(key, 0), "expected": expected[key]}
        for key in sorted(selected_keys)
        if observed.get(key, 0) != expected[key]
    }
    if mismatches:
        raise RuntimeError(f"Selected activation-key count closure failed: {list(mismatches.items())[:5]}")

    os.replace(checkpoint, OUTPUT)

    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema_version": 1,
        "status": "PASS__SH3_SELECTED_ACTIVATION_KEYS_EXACT_PRIMARY_ENERGY_JOIN",
        "scan_policy": "ONE_SEMANTIC_PASS__NO_SIM_HASH",
        "sim_files": len(tasks),
        "sim_bytes": sum(
            int(row["sim_bytes"])
            for row in manifest["rpip_scans"]
            if str(row["family"]) in scanned_families
        ),
        "all_CC_IP_RP_lines": scanned_cc_lines,
        "selected_delayed_events": len(selected_rows),
        "selected_activation_keys": len(selected_keys),
        "selected_key_RP_rows": len(all_rows),
        "count_mismatches": 0,
        "output": str(OUTPUT.relative_to(ROOT)),
        "energy_axis": "primary total kinetic energy in keV from IA INIT",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
