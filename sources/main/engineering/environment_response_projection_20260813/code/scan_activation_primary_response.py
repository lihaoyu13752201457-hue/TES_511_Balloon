#!/usr/bin/env python3
"""Recover primary-energy provenance for corrected BUILDUP isotope records.

This is a read-only adapter over the retained rich SIM payloads.  It does not
rerun transport.  Every emitted row joins one ``CC IP RP`` record to the
single ``IA INIT`` primary in the same SIM event, then maps the physical
volume name back to the logical volume used by the corrected inventory.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import math
import os
import re
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from decimal import Decimal
from pathlib import Path
from typing import Any


PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parents[1]
CATALOG = (
    ROOT
    / "runs/particle_source_unit_repair_20260811"
    / "m05_paper_closure_topup_batch0007_3h_v1"
    / "delayed_phase02/catalog_v1/catalog.json"
)
PREPARE = (
    ROOT
    / "engineering/particle_source_unit_repair_20260811"
    / "m05_paper_closure_topup_batch0007_3h_20260813"
    / "delayed_phase02/code/prepare_state_aware_delayed_phase02.py"
)
OUTPUT = PACKAGE / "outputs/tables/activation_rp_primary_energy.csv.gz"
SUMMARY = PACKAGE / "data/activation_scan_summary.json"

CC_RP_RE = re.compile(
    r"^CC\s+IP\s+RP\s+(?P<volume>\S+)\s+"
    r"(?P<x>[-+0-9.eE]+)\s+(?P<y>[-+0-9.eE]+)\s+"
    r"(?P<z>[-+0-9.eE]+)\s+(?P<za>\d+)\s+"
    r"(?P<exc>[-+0-9.eE]+)\s+(?P<t>[-+0-9.eE]+)"
)
FIELDS = (
    "geometry",
    "incident_family",
    "source_file",
    "local_event_id",
    "primary_energy_keV_total",
    "primary_dir_x",
    "primary_dir_y",
    "primary_dir_z",
    "primary_theta_deg",
    "physical_volume",
    "logical_volume",
    "source_parent_ZA",
    "source_excitation_keV",
    "production_x_cm",
    "production_y_cm",
    "production_z_cm",
    "balloon_cell_TT_s",
    "balloon_production_weight_s-1",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_excitation(value: float | str) -> float:
    raw = Decimal(str(value)).quantize(Decimal("0.01"))
    return 0.0 if raw == 0 else float(raw)


def load_prepare_module() -> Any:
    spec = importlib.util.spec_from_file_location("m05_prepare_state_aware", PREPARE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import retained mapper: {PREPARE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_init(line: str) -> tuple[float, float, float, float]:
    fields = [item.strip() for item in line[len("IA INIT") :].split(";")]
    if len(fields) < 23:
        raise RuntimeError(f"Malformed IA INIT: {line.rstrip()}")
    energy = float(fields[22])
    dx, dy, dz = (float(fields[16]), float(fields[17]), float(fields[18]))
    if not (math.isfinite(energy) and energy >= 0.0):
        raise RuntimeError(f"Invalid IA INIT energy: {line.rstrip()}")
    if not math.isclose(dx * dx + dy * dy + dz * dz, 1.0, rel_tol=0.0, abs_tol=2.5e-4):
        raise RuntimeError(f"Invalid IA INIT direction: {line.rstrip()}")
    return energy, dx, dy, dz


def scan_one(task: dict[str, Any]) -> dict[str, Any]:
    path = Path(task["path"])
    logical = set(task["logical"])
    copy_map = task["copy_map"]
    state_exc = {
        (str(volume), int(za)): tuple(float(item) for item in values)
        for volume, za, values in task["state_exc"]
    }
    geometry = str(task["geometry"])
    family = str(task["family"])
    tt_s = float(task["tt_s"])
    current_id: int | None = None
    current_init: tuple[float, float, float, float] | None = None
    init_count = 0
    pending_rp: list[re.Match[str]] = []
    rows: list[tuple[Any, ...]] = []
    unmatched: Counter[str] = Counter()

    def flush_event() -> None:
        nonlocal pending_rp
        if not pending_rp:
            return
        if current_id is None or current_init is None or init_count != 1:
            raise RuntimeError(f"RP record without unique IA INIT in {path}, event {current_id}")
        energy, dx, dy, dz = current_init
        theta = math.degrees(math.acos(max(-1.0, min(1.0, dz))))
        for match in pending_rp:
            physical = match.group("volume")
            candidates = set()
            if physical in logical:
                candidates.add(physical)
            copied = copy_map.get(physical)
            if copied in logical:
                candidates.add(copied)
            if len(candidates) != 1:
                unmatched[physical] += 1
                continue
            volume = next(iter(candidates))
            za = int(match.group("za"))
            raw_exc = Decimal(match.group("exc"))
            matches = [
                value
                for value in state_exc.get((volume, za), ())
                if abs(Decimal(str(value)) - raw_exc) <= Decimal("0.0050001")
            ]
            if len(matches) != 1:
                unmatched[f"{volume}|{za}|{raw_exc}"] += 1
                continue
            rows.append(
                (
                    geometry,
                    family,
                    str(path),
                    current_id,
                    energy,
                    dx,
                    dy,
                    dz,
                    theta,
                    physical,
                    volume,
                    za,
                    canonical_excitation(matches[0]),
                    float(match.group("x")),
                    float(match.group("y")),
                    float(match.group("z")),
                    tt_s,
                    1.0 / tt_s,
                )
            )
        pending_rp = []

    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as stream:
        for raw in stream:
            if raw.startswith("SE"):
                flush_event()
                current_id = None
                current_init = None
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
                current_init = parse_init(raw)
                continue
            if not raw.startswith("CC IP RP "):
                continue
            match = CC_RP_RE.match(raw)
            if not match:
                raise RuntimeError(f"Malformed CC IP RP in {path}: {raw.rstrip()}")
            pending_rp.append(match)
    flush_event()
    return {
        "path": str(path),
        "geometry": geometry,
        "family": family,
        "rows": rows,
        "unmatched": dict(unmatched),
    }


def atomic_write_gzip_csv(path: Path, rows: list[tuple[Any, ...]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".partial", dir=path.parent)
    os.close(fd)
    tmp = Path(name)
    try:
        with gzip.open(tmp, "wt", encoding="utf-8", newline="", compresslevel=6) as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(FIELDS)
            writer.writerows(rows)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    if not CATALOG.is_file() or not PREPARE.is_file():
        raise RuntimeError("Required corrected BUILDUP authority is missing")
    payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    if payload.get("status") != "PASS__CORRECTED_BUILDUP_CATALOG_READY":
        raise RuntimeError(f"BUILDUP catalog is not PASS: {payload.get('status')}")
    if payload.get("coverage", {}).get("sum_RP") != 97247.0:
        raise RuntimeError("Unexpected corrected BUILDUP RP total")

    mapper = load_prepare_module()
    cell_tt = {
        (str(row["geometry"]), str(row["family"])): float(row["sum_TT_s"])
        for row in payload["cells"]
    }
    production_by_cell: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in payload["production_rows"]:
        production_by_cell[(str(row["geometry"]), str(row["family"]))].append(row)
    entry_by_path: dict[Path, dict[str, Any]] = {}
    for entry in payload["dat_entries"]:
        ref = entry.get("sim_reference") or {}
        raw = Path(ref.get("path", ""))
        path = raw if raw.is_absolute() else ROOT / raw
        path = path.resolve()
        if not path.is_file():
            raise RuntimeError(f"Missing rich SIM: {path}")
        old = entry_by_path.get(path)
        if old is not None and (
            old["geometry"] != entry["geometry"] or old["family"] != entry["family"]
        ):
            raise RuntimeError(f"SIM reused across cells: {path}")
        entry_by_path[path] = entry

    copy_maps = {
        geometry: mapper.geometry_copy_map(mapper.source_geometry(geometry))
        for geometry in ("Mass_model_511", "S3d_O8")
    }
    tasks: list[dict[str, Any]] = []
    for path, entry in sorted(entry_by_path.items(), key=lambda item: str(item[0])):
        key = (str(entry["geometry"]), str(entry["family"]))
        production = production_by_cell[key]
        state_exc_map: dict[tuple[str, int], list[float]] = defaultdict(list)
        for row in production:
            value = canonical_excitation(row["excitation_keV"])
            item_key = (str(row["volume"]), int(row["isotope_id"]))
            if value not in state_exc_map[item_key]:
                state_exc_map[item_key].append(value)
        tasks.append(
            {
                "path": str(path),
                "geometry": key[0],
                "family": key[1],
                "tt_s": cell_tt[key],
                "logical": sorted({str(row["volume"]) for row in production}),
                "copy_map": copy_maps[key[0]],
                "state_exc": [
                    (volume, za, sorted(values))
                    for (volume, za), values in sorted(state_exc_map.items())
                ],
            }
        )

    all_rows: list[tuple[Any, ...]] = []
    unmatched: Counter[str] = Counter()
    with ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(scan_one, task) for task in tasks]
        for future in as_completed(futures):
            result = future.result()
            all_rows.extend(result["rows"])
            unmatched.update(result["unmatched"])
    all_rows.sort(key=lambda row: (row[0], row[1], row[2], row[3], row[10], row[11], row[12]))

    key_counts = Counter((row[0], row[1], row[10], int(row[11]), float(row[12])) for row in all_rows)
    expected_counts = {
        (
            str(row["geometry"]),
            str(row["family"]),
            str(row["volume"]),
            int(row["isotope_id"]),
            canonical_excitation(row["excitation_keV"]),
        ): int(round(float(row["sum_RP"])))
        for row in payload["production_rows"]
    }
    mismatches = {
        "|".join(map(str, key)): {"observed": key_counts.get(key, 0), "expected": expected}
        for key, expected in expected_counts.items()
        if key_counts.get(key, 0) != expected
    }
    unexpected_keys = {
        "|".join(map(str, key)): count
        for key, count in key_counts.items()
        if key not in expected_counts
    }
    if unmatched or mismatches or unexpected_keys or len(all_rows) != 97247:
        raise RuntimeError(
            f"Activation scan failed closure: rows={len(all_rows)}, unmatched={sum(unmatched.values())}, "
            f"mismatches={len(mismatches)}, unexpected={len(unexpected_keys)}"
        )

    atomic_write_gzip_csv(OUTPUT, all_rows)
    summary = {
        "schema_version": 1,
        "status": "PASS__ACTIVATION_RP_PRIMARY_ENERGY_EXACT_JOIN",
        "authority_boundary": (
            "Exact join of corrected BUILDUP RP records to their simulated primary energy; "
            "not a LEO/lunar transport or sensitivity authority"
        ),
        "catalog_path": str(CATALOG.relative_to(ROOT)),
        "catalog_sha256": sha256(CATALOG),
        "mapper_path": str(PREPARE.relative_to(ROOT)),
        "mapper_sha256": sha256(PREPARE),
        "sim_files": len(tasks),
        "rp_rows": len(all_rows),
        "expected_rp_rows": 97247,
        "state_keys": len(key_counts),
        "unmatched_records": 0,
        "state_key_mismatches": 0,
        "output_path": str(OUTPUT.relative_to(ROOT)),
        "output_sha256": sha256(OUTPUT),
        "energy_axis": "primary total kinetic energy in keV from IA INIT",
        "normalization": "each RP row has weight 1/sum(TT) within geometry x incident-family BUILDUP cell",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
