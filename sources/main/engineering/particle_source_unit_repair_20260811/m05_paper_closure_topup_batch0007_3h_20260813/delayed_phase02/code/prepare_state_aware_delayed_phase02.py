#!/usr/bin/env python3
"""Prepare state-aware exact-position delayed sources for corrected batch0007.

The default actions are read-only (``--print-plan`` and ``--self-test``).
``--prepare`` consumes the post-campaign corrected BUILDUP catalog, reads only
its declared rich SIM files, and publishes a new write-once source package.
It never launches Cosima.  A separately explicit ``--run-transport`` action is
provided as a thin six-worker controller for a later, separately authorized
phase.  Transport can be limited to a paired family subset or exact job IDs;
each selection gets a distinct write-once summary and is explicitly labelled
as partial unless it covers every prepared job.

Important installed-Cosima boundary
-----------------------------------
The retained exact-position PointSource syntax carries ZA and position, but no
particle excitation.  Therefore this controller never collapses a non-zero
excitation state into the ground state.  It computes and reports state-resolved
production/activity when NUBASE can identify the state, then fail-closes all
non-zero-excitation states from transport.  Ground states retain exact
(geometry, family, logical volume, ZA, excitation=0, position) weighting.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import gzip
import hashlib
import json
import math
import os
import random
import re
import shutil
import signal
import subprocess
import tempfile
import time
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable


THIS_FILE = Path(__file__).resolve()
ROOT = THIS_FILE.parents[5]
RUN_ROOT = (
    ROOT
    / "runs/particle_source_unit_repair_20260811"
    / "m05_paper_closure_topup_batch0007_3h_v1"
)
CATALOG = RUN_ROOT / "delayed_phase02/catalog_v1/catalog.json"
CATALOG_COMPAT = RUN_ROOT / "delayed_phase02/corrected_buildup_catalog.json"
FINAL_VALIDATION = RUN_ROOT / "final_validation.json"
AUTHORITY = RUN_ROOT / "authority.json"
OUTPUT_ROOT = RUN_ROOT / "delayed_phase02/state_aware_exactpos_v1"
NUBASE = ROOT / "inputs/nubase/nubase_2020.txt"
COSIMA = Path("/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima")

SOURCE_CONTRACT_SHA256 = (
    "5424eeca35b20affb153c0e07c31a6582e575f511922bf55f40a5a0f77ab4326"
)
NUBASE_SHA256 = "1585a5eea86c5e17e90307c7e6e786d060049c4039e392a261ff6db977df9859"
GEOMETRIES = ("Mass_model_511", "S3d_O8")
FAMILIES = ("gamma", "n", "eplus", "alpha", "eminus", "muplus", "muminus", "p")
FAMILY_ALIASES = {"neutron": "n", "proton": "p"}
POINTS_PER_POSITIVE_FAMILY = 50_000
TRIGGERS_PER_POSITIVE_FAMILY = 1_000_000
FLIGHT_DAYS = 15.0
MIN_POINTS = 1
TRANSPORT_WORKERS = 6
FILESYSTEM_RESERVE_BYTES = 20 * 1024**3
DECLARED_JOB_CAP_BYTES = 2_000_000_000
PREFERRED_FIRST_FAMILIES = ("p", "n", "alpha", "gamma", "eminus", "muminus")
SEED_BASE = 1_970_000_002
SEED_STRIDE = 98_317

CORRECTED_SOURCE_CARDS = {
    "Mass_model_511": ROOT
    / "engineering/particle_source_unit_repair_20260811/config/source_cards"
    / "mass_model_511/Background_gamma_fullsphere20.source",
    "S3d_O8": ROOT
    / "engineering/particle_source_unit_repair_20260811/config/source_cards"
    / "s3d_o8/Background_gamma_fullsphere20.source",
}

CC_RP_RE = re.compile(
    r"^CC\s+IP\s+RP\s+(?P<volume>\S+)\s+"
    r"(?P<x>[-+0-9.eE]+)\s+(?P<y>[-+0-9.eE]+)\s+"
    r"(?P<z>[-+0-9.eE]+)\s+(?P<za>\d+)\s+"
    r"(?P<exc>[-+0-9.eE]+)\s+(?P<t>[-+0-9.eE]+)"
)
GEOMETRY_RE = re.compile(r"^\s*Geometry\s+(\S+)\s*$")
INCLUDE_RE = re.compile(r"^\s*Include\s+(\S+)\s*$")
COPY_RE = re.compile(r"^\s*(?P<logical>\S+)\.Copy\s+(?P<physical>\S+)\s*$")

UNIT_SECONDS = {
    "fs": 1.0e-15,
    "as": 1.0e-18,
    "zs": 1.0e-21,
    "ys": 1.0e-24,
    "ps": 1.0e-12,
    "ns": 1.0e-9,
    "us": 1.0e-6,
    "ms": 1.0e-3,
    "s": 1.0,
    "m": 60.0,
    "h": 3600.0,
    "d": 86400.0,
    "y": 31_557_600.0,
    "ky": 1.0e3 * 31_557_600.0,
    "My": 1.0e6 * 31_557_600.0,
    "Gy": 1.0e9 * 31_557_600.0,
    "Ty": 1.0e12 * 31_557_600.0,
    "Py": 1.0e15 * 31_557_600.0,
    "Ey": 1.0e18 * 31_557_600.0,
    "Zy": 1.0e21 * 31_557_600.0,
    "Yy": 1.0e24 * 31_557_600.0,
}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_once(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"write-once target exists: {path}")
    partial = path.with_name(f".{path.name}.partial.{os.getpid()}")
    if partial.exists():
        raise FileExistsError(f"partial target exists: {partial}")
    with partial.open("x", encoding="utf-8") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(partial, path)


def atomic_json_once(path: Path, payload: Any) -> None:
    atomic_write_once(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def canonical_family(value: str) -> str:
    return FAMILY_ALIASES.get(str(value), str(value))


def canonical_excitation(value: float | str) -> float:
    raw = Decimal(str(value)).quantize(Decimal("0.01"))
    return 0.0 if raw == 0 else float(raw)


def state_key(volume: str, za: int, excitation_keV: float | str) -> tuple[str, int, float]:
    return (str(volume), int(za), canonical_excitation(excitation_keV))


def source_geometry(geometry: str) -> Path:
    card = CORRECTED_SOURCE_CARDS[geometry]
    if not card.is_file():
        raise RuntimeError(f"missing corrected source card: {card}")
    text = card.read_text(encoding="utf-8", errors="replace")
    if "cosima_spectra_dp_2602units" in text:
        raise RuntimeError(f"legacy factor-1000 reference in corrected card: {card}")
    matches = [GEOMETRY_RE.match(line) for line in text.splitlines()]
    values = [match.group(1) for match in matches if match]
    if len(values) != 1:
        raise RuntimeError(f"expected one Geometry line in {card}, found {values}")
    path = Path(values[0])
    path = path if path.is_absolute() else ROOT / path
    if not path.is_file():
        raise RuntimeError(f"geometry from corrected source card is missing: {path}")
    return path.resolve()


def geometry_copy_map(setup: Path) -> dict[str, str]:
    """Read explicit geometry ``BASE.Copy PHYSICAL`` declarations only."""
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
                if not child.is_absolute():
                    candidate = resolved.parent / child
                    child = candidate if candidate.exists() else ROOT / child
                visit(child)
                continue
            copy = COPY_RE.match(raw)
            if not copy:
                continue
            logical, physical = copy.group("logical"), copy.group("physical")
            old = mapping.get(physical)
            if old is not None and old != logical:
                raise RuntimeError(f"conflicting geometry Copy mapping: {physical}: {old} vs {logical}")
            mapping[physical] = logical

    visit(setup)
    # Most setup files include the same-stem .geo; follow it even if the setup
    # uses a loader-specific spelling not caught above.
    visit(setup.with_suffix(""))
    if setup.name.endswith(".geo.setup"):
        visit(setup.with_name(setup.name[: -len(".setup")]))
    return mapping


def parse_half_life(value: str, unit: str, context: str) -> float | None:
    if "stbl" in context.lower() or "stable" in context.lower():
        return math.inf
    cleaned = re.sub(r"[#?><~*&]", "", value).strip()
    try:
        number = float(cleaned)
    except ValueError:
        return None
    multiplier = UNIT_SECONDS.get(unit.strip()) or UNIT_SECONDS.get(unit.strip().lower())
    return None if multiplier is None else number * multiplier


def load_nubase_states(path: Path = NUBASE) -> dict[int, list[dict[str, Any]]]:
    if path.resolve() == NUBASE.resolve() and sha256(path) != NUBASE_SHA256:
        raise RuntimeError("retained NUBASE-2020 hash mismatch")
    states: dict[int, list[dict[str, Any]]] = defaultdict(list)
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for lineno, line in enumerate(handle, 1):
            if line.startswith("#") or len(line) < 90:
                continue
            try:
                mass = int(line[0:3].strip())
                zstate = line[4:8].strip()
                z = int(zstate[:3])
            except ValueError:
                continue
            state_designator = zstate[3:] if len(zstate) > 3 else "0"
            is_ground = state_designator in ("", "0")
            if is_ground:
                excitation = 0.0
            else:
                cleaned_exc = re.sub(r"[#?><~*&]", "", line[42:54]).strip()
                try:
                    excitation = float(cleaned_exc)
                except ValueError:
                    excitation = None
            half_life = parse_half_life(line[69:78], line[78:80], line[69:90])
            states[1000 * z + mass].append({
                "state_designator": state_designator or "0",
                "is_ground": is_ground,
                "excitation_keV": excitation,
                "half_life_s": half_life,
                "nubase_line": lineno,
                "raw_half_life": line[69:80].strip(),
            })
    return dict(states)


def match_nubase_state(
    table: dict[int, list[dict[str, Any]]], za: int, excitation_keV: float
) -> tuple[dict[str, Any] | None, str]:
    records = table.get(int(za), [])
    if excitation_keV == 0.0:
        matches = [row for row in records if row["is_ground"]]
        return (matches[0], "NUBASE2020_ground") if len(matches) == 1 else (None, "missing_or_ambiguous_ground")
    matches = [
        row for row in records
        if not row["is_ground"]
        and row["excitation_keV"] is not None
        and abs(float(row["excitation_keV"]) - excitation_keV) <= 0.51
    ]
    if len(matches) == 1:
        return matches[0], "NUBASE2020_unique_isomer_energy_within_0.51keV"
    return None, "missing_or_ambiguous_explicit_excited_state"


def activity_from_rate(rate_s: float, half_life_s: float | None) -> float | None:
    if rate_s <= 0.0:
        return 0.0
    if half_life_s is None:
        return None
    if math.isinf(half_life_s):
        return 0.0
    if half_life_s <= 0.0:
        return None
    lam_t = math.log(2.0) * FLIGHT_DAYS * 86400.0 / half_life_s
    return rate_s * (-math.expm1(-lam_t))


def validate_authority() -> dict[str, Any]:
    if not FINAL_VALIDATION.is_file():
        raise RuntimeError(f"batch0007 final validation is absent: {FINAL_VALIDATION}")
    final = load_json(FINAL_VALIDATION)
    if not str(final.get("status", "")).startswith("PASS"):
        raise RuntimeError(f"batch0007 final validation is not PASS: {final.get('status')}")
    authority = load_json(AUTHORITY)
    if authority.get("source_contract_sha256") != SOURCE_CONTRACT_SHA256:
        raise RuntimeError("batch0007 corrected source-contract binding mismatch")
    frozen = authority.get("frozen", {})
    if frozen.get("corrected_keV_sources") is not True or frozen.get("extra_mono511_added") is not False:
        raise RuntimeError(f"batch0007 corrected-source boundary mismatch: {frozen}")
    return {"final_status": final["status"], "authority_status": authority.get("status")}


def resolve_catalog_path() -> Path:
    if CATALOG.is_file():
        return CATALOG
    if CATALOG_COMPAT.is_file():
        return CATALOG_COMPAT
    raise RuntimeError(f"corrected BUILDUP catalog is not yet published: {CATALOG}")


def validate_catalog(payload: dict[str, Any]) -> None:
    if payload.get("status") != "PASS__CORRECTED_BUILDUP_CATALOG_READY":
        raise RuntimeError(f"catalog is not ready: {payload.get('status')}")
    if payload.get("authority_class") != "CORRECTED_KEV_BUILDUP_DAT_AND_RICH_SIM_REFERENCE_CATALOG":
        raise RuntimeError("catalog authority class mismatch")
    if payload.get("mode") != "buildup_only" or payload.get("batch0007_state") != "INCLUDED__FINAL_PASS":
        raise RuntimeError("catalog is not the final batch0007-inclusive BUILDUP authority")
    if payload.get("source_contract_sha256") != SOURCE_CONTRACT_SHA256:
        raise RuntimeError("catalog corrected source-contract binding mismatch")
    if payload.get("legacy_factor1000_included") is not False:
        raise RuntimeError("catalog does not explicitly exclude factor-1000 legacy data")
    if payload.get("extra_mono511_included") is not False:
        raise RuntimeError("catalog does not explicitly exclude an extra mono-511 source")
    normalization = payload.get("normalization") or {}
    if normalization.get("zero_RP_DAT_TT_retained") is not True:
        raise RuntimeError("catalog does not retain zero-RP TT in family denominators")
    if not isinstance(payload.get("dat_entries"), list):
        raise RuntimeError("catalog lacks dat_entries[]")
    if not isinstance(payload.get("production_rows"), list):
        raise RuntimeError("catalog lacks production_rows[]")
    expected_cells = {(geometry, family) for geometry in GEOMETRIES for family in FAMILIES}
    actual_cells = {
        (str(row.get("geometry")), canonical_family(row.get("family", "")))
        for row in payload.get("cells", [])
    }
    if actual_cells != expected_cells or len(payload.get("cells", [])) != len(expected_cells):
        raise RuntimeError(f"catalog cell coverage mismatch: {sorted(actual_cells ^ expected_cells)}")
    bad_geometry = sorted({row.get("geometry") for row in payload["production_rows"]} - set(GEOMETRIES))
    if bad_geometry:
        raise RuntimeError(f"catalog has unexpected geometries: {bad_geometry}")
    for row in payload["production_rows"]:
        if canonical_family(row.get("family", "")) not in FAMILIES:
            raise RuntimeError(f"catalog has unexpected family: {row.get('family')}")
    production_keys = [
        (
            str(row.get("geometry")), canonical_family(row.get("family", "")),
            str(row.get("volume")), int(row.get("isotope_id")),
            canonical_excitation(row.get("excitation_keV")),
        )
        for row in payload["production_rows"]
    ]
    if len(production_keys) != len(set(production_keys)):
        raise RuntimeError("catalog has duplicate geometry/family/volume/ZA/state production keys")


def catalog_rows(payload: dict[str, Any], geometry: str, family: str) -> list[dict[str, Any]]:
    rows = []
    for raw in payload["production_rows"]:
        if raw.get("geometry") != geometry or canonical_family(raw.get("family", "")) != family:
            continue
        row = dict(raw)
        row["family"] = family
        row["volume"] = str(row["volume"])
        row["isotope_id"] = int(row["isotope_id"])
        row["excitation_keV"] = canonical_excitation(row["excitation_keV"])
        row["production_rate_s-1"] = float(row["production_rate_s-1"])
        rows.append(row)
    return rows


def sim_paths(payload: dict[str, Any], geometry: str, family: str) -> list[Path]:
    paths: set[Path] = set()
    for row in payload["dat_entries"]:
        if row.get("geometry") != geometry or canonical_family(row.get("family", "")) != family:
            continue
        reference = row.get("sim_reference") or {}
        value = reference.get("path")
        if not value:
            raise RuntimeError(f"catalog DAT entry lacks SIM reference: {row.get('dat_path')}")
        path = Path(value)
        path = path if path.is_absolute() else ROOT / path
        if not path.is_file():
            raise RuntimeError(f"catalog-declared SIM is missing: {path}")
        paths.add(path.resolve())
    return sorted(paths)


def map_logical_volume(physical: str, logical: set[str], copies: dict[str, str]) -> str | None:
    candidates = set()
    if physical in logical:
        candidates.add(physical)
    target = copies.get(physical)
    if target in logical:
        candidates.add(str(target))
    if len(candidates) == 1:
        return next(iter(candidates))
    if len(candidates) > 1:
        raise RuntimeError(f"ambiguous logical-volume mapping for {physical}: {sorted(candidates)}")
    return None


def parse_rpip_points(
    paths: Iterable[Path],
    production_rows: list[dict[str, Any]],
    copy_map: dict[str, str],
) -> tuple[dict[tuple[str, int, float], list[tuple[float, float, float]]], dict[str, Any]]:
    logical = {str(row["volume"]) for row in production_rows}
    excitation_by_volume_za: dict[tuple[str, int], list[float]] = defaultdict(list)
    for row in production_rows:
        key = (str(row["volume"]), int(row["isotope_id"]))
        value = canonical_excitation(row["excitation_keV"])
        if value not in excitation_by_volume_za[key]:
            excitation_by_volume_za[key].append(value)
    points: dict[tuple[str, int, float], list[tuple[float, float, float]]] = defaultdict(list)
    unmatched_volumes: Counter[str] = Counter()
    unmatched_states: Counter[tuple[str, int, str]] = Counter()
    parsed_lines = 0
    for path in paths:
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                if not raw.startswith("CC IP RP "):
                    continue
                match = CC_RP_RE.match(raw)
                if not match:
                    continue
                parsed_lines += 1
                physical = match.group("volume")
                volume = map_logical_volume(physical, logical, copy_map)
                if volume is None:
                    unmatched_volumes[physical] += 1
                    continue
                za = int(match.group("za"))
                raw_exc = Decimal(match.group("exc"))
                candidates = [
                    value for value in excitation_by_volume_za.get((volume, za), [])
                    if abs(Decimal(str(value)) - raw_exc) <= Decimal("0.0050001")
                ]
                if len(candidates) != 1:
                    unmatched_states[(volume, za, str(raw_exc))] += 1
                    continue
                key = state_key(volume, za, candidates[0])
                points[key].append((float(match.group("x")), float(match.group("y")), float(match.group("z"))))
    return dict(points), {
        "sim_files": len(list(paths)) if not isinstance(paths, list) else len(paths),
        "CC_IP_RP_lines": parsed_lines,
        "matched_points": sum(len(values) for values in points.values()),
        "matched_state_keys": len(points),
        "unmatched_volume_points": sum(unmatched_volumes.values()),
        "unmatched_state_points": sum(unmatched_states.values()),
        "top_unmatched_volumes": unmatched_volumes.most_common(20),
        "top_unmatched_states": [
            {"volume": key[0], "ZA": key[1], "raw_excitation_keV": key[2], "points": count}
            for key, count in unmatched_states.most_common(20)
        ],
    }


def classify_states(
    rows: list[dict[str, Any]],
    points: dict[tuple[str, int, float], list[tuple[float, float, float]]],
    nubase: dict[int, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    included: list[dict[str, Any]] = []
    holdout: list[dict[str, Any]] = []
    for row in rows:
        key = state_key(row["volume"], row["isotope_id"], row["excitation_keV"])
        rate = float(row["production_rate_s-1"])
        match, provenance = match_nubase_state(nubase, key[1], key[2])
        half_life = None if match is None else match["half_life_s"]
        activity = activity_from_rate(rate, half_life)
        record = {
            "volume": key[0],
            "ZA": key[1],
            "excitation_keV": key[2],
            "production_rate_s-1": rate,
            "sum_RP": float(row.get("sum_RP", len(points.get(key, [])))),
            "day15_activity_Bq": activity,
            "half_life_s": half_life,
            "half_life_provenance": provenance,
            "nubase_line": None if match is None else match["nubase_line"],
            "RPIP_points": len(points.get(key, [])),
        }
        record["RPIP_minus_sum_RP"] = record["RPIP_points"] - record["sum_RP"]
        if rate <= 0.0 or activity == 0.0:
            record["holdout_reason"] = "zero_day15_activity"
            holdout.append(record)
        elif activity is None:
            record["holdout_reason"] = "state_half_life_not_explicitly_resolved"
            holdout.append(record)
        elif key[2] != 0.0:
            record["holdout_reason"] = "installed_PointSource_cannot_encode_nonzero_excitation_without_state_collapse"
            holdout.append(record)
        elif not math.isclose(
            float(record["RPIP_points"]), float(record["sum_RP"]),
            rel_tol=0.0, abs_tol=1.0e-9,
        ):
            record["holdout_reason"] = "RPIP_support_count_does_not_equal_catalog_sum_RP"
            holdout.append(record)
        elif len(points.get(key, [])) < MIN_POINTS:
            record["holdout_reason"] = "no_exact_RPIP_support"
            holdout.append(record)
        else:
            record["transport_state"] = "included_ground_state_exact_position"
            included.append(record)
    return included, holdout


def weighted_sample(
    included: list[dict[str, Any]],
    points: dict[tuple[str, int, float], list[tuple[float, float, float]]],
    n: int,
    seed: int,
) -> list[dict[str, Any]]:
    population: list[tuple[dict[str, Any], tuple[float, float, float]]] = []
    weights: list[float] = []
    for row in included:
        key = state_key(row["volume"], row["ZA"], row["excitation_keV"])
        support = points[key]
        per_point = float(row["day15_activity_Bq"]) / len(support)
        for point in support:
            population.append((row, point))
            weights.append(per_point)
    if not population or math.fsum(weights) <= 0.0:
        return []
    cdf: list[float] = []
    running = 0.0
    for weight in weights:
        running += weight
        cdf.append(running)
    rng = random.Random(seed)
    sampled = []
    for _ in range(n):
        index = bisect.bisect_left(cdf, rng.random() * running)
        row, xyz = population[min(index, len(population) - 1)]
        sampled.append({
            "volume": row["volume"],
            "ZA": row["ZA"],
            "excitation_keV": row["excitation_keV"],
            "x_cm": xyz[0], "y_cm": xyz[1], "z_cm": xyz[2],
        })
    return sampled


def write_family_source(
    directory: Path,
    geometry: str,
    family: str,
    sampled: list[dict[str, Any]],
    total_activity: float,
    triggers: int,
) -> tuple[Path, Path]:
    source = directory / "activation_day15_state_aware_exactpos_m50000.source"
    table = directory / "sampled_exact_positions_m50000.csv"
    transport_partial = OUTPUT_ROOT / "transport" / geometry / family / ".attempt01.partial"
    prefix = transport_partial / f"DelayedDay15_{geometry}_{family}_M50000"
    geometry_path = source_geometry(geometry)
    flux = total_activity / len(sampled)
    lines = [
        "Version 1",
        f"Geometry {geometry_path}",
        "",
        "PhysicsListHD qgsp-bic-hp",
        "PhysicsListEM LivermorePol",
        "PhysicsListRadioactiveDecay true",
        "DecayMode ActivationDelayedDecay",
        "StoreSimulationInfo all",
        "StoreIsotopes true",
        "DetectorTimeConstant 1e-9",
        "",
        "Run DecayRun",
        f"DecayRun.FileName {prefix}",
        f"DecayRun.Triggers {int(triggers)}",
        "",
    ]
    lines.extend(f"DecayRun.Source RP_{index:07d}" for index in range(len(sampled)))
    lines.extend(("", "# Exact RPIP positions; state key is audited in each comment."))
    for index, row in enumerate(sampled):
        name = f"RP_{index:07d}"
        lines.append(
            f"# state VN={row['volume']} ZA={row['ZA']} excitation_keV={row['excitation_keV']:.2f}"
        )
        lines.append(f"{name}.ParticleType {row['ZA']}")
        lines.append(f"{name}.Beam PointSource {row['x_cm']:.8g} {row['y_cm']:.8g} {row['z_cm']:.8g}")
        lines.append(f"{name}.Flux {flux:.12e}")
        lines.append("")
    source.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with table.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("sample_index", "volume", "ZA", "excitation_keV", "x_cm", "y_cm", "z_cm"))
        writer.writeheader()
        for index, row in enumerate(sampled):
            writer.writerow({"sample_index": index, **row})
    return source, table


def used_seeds() -> set[int]:
    values: set[int] = set()

    def walk(value: Any, key: str = "") -> None:
        if isinstance(value, dict):
            for child_key, child in value.items():
                walk(child, str(child_key).lower())
        elif isinstance(value, list):
            for child in value:
                walk(child, key)
        elif isinstance(value, int) and (key == "seed" or key.endswith("_seed")):
            if 0 < value < 2**31:
                values.add(value)

    root = ROOT / "runs/particle_source_unit_repair_20260811"
    for path in root.rglob("*.json"):
        if OUTPUT_ROOT in path.parents:
            continue
        try:
            walk(load_json(path))
        except (OSError, UnicodeError, json.JSONDecodeError):
            pass
    return values


def allocate_matched_seeds() -> dict[str, int]:
    reserved = used_seeds()
    result: dict[str, int] = {}
    candidate = SEED_BASE
    for family in FAMILIES:
        while candidate in reserved or candidate in result.values():
            candidate += SEED_STRIDE
        if candidate >= 2**31:
            raise RuntimeError("fresh delayed seed range exhausted")
        result[family] = candidate
        candidate += SEED_STRIDE
    return result


def build_cell(
    staging: Path,
    payload: dict[str, Any],
    geometry: str,
    family: str,
    nubase: dict[int, list[dict[str, Any]]],
    matched_seed: int,
    n_points: int = POINTS_PER_POSITIVE_FAMILY,
    triggers: int = TRIGGERS_PER_POSITIVE_FAMILY,
) -> dict[str, Any]:
    rows = catalog_rows(payload, geometry, family)
    if not rows:
        return {"geometry": geometry, "family": family, "status": "SKIP_NO_PRODUCTION_ROWS"}
    paths = sim_paths(payload, geometry, family)
    copies = geometry_copy_map(source_geometry(geometry))
    points, rpip_audit = parse_rpip_points(paths, rows, copies)
    included, holdout = classify_states(rows, points, nubase)
    included_activity = math.fsum(float(row["day15_activity_Bq"]) for row in included)
    known_holdout_activity = math.fsum(
        float(row["day15_activity_Bq"])
        for row in holdout if row["day15_activity_Bq"] is not None
    )
    unknown_activity_rows = sum(row["day15_activity_Bq"] is None for row in holdout)
    unresolved_positive_ground = [
        row for row in holdout
        if row["excitation_keV"] == 0.0
        and row["production_rate_s-1"] > 0.0
        and row["day15_activity_Bq"] is None
    ]
    if unresolved_positive_ground:
        raise RuntimeError(
            f"{geometry}/{family}: positive ground-state activity is unresolved: "
            f"{unresolved_positive_ground[:5]}"
        )
    incomplete_positive_ground = [
        row for row in holdout
        if row["excitation_keV"] == 0.0
        and row["production_rate_s-1"] > 0.0
        and row["day15_activity_Bq"] is not None
        and row["day15_activity_Bq"] > 0.0
        and row["holdout_reason"] in {
            "no_exact_RPIP_support",
            "RPIP_support_count_does_not_equal_catalog_sum_RP",
        }
    ]
    if incomplete_positive_ground:
        raise RuntimeError(
            f"{geometry}/{family}: positive ground-state exact-position support is incomplete: "
            f"{incomplete_positive_ground[:5]}"
        )
    known_total = included_activity + known_holdout_activity
    if included_activity <= 0.0:
        return {
            "geometry": geometry, "family": family,
            "status": "SKIP_NO_TRANSPORTABLE_POSITIVE_GROUND_ACTIVITY",
            "RPIP_audit": rpip_audit,
            "included_states": included,
            "holdout_states": holdout,
            "known_holdout_activity_Bq": known_holdout_activity,
            "unknown_activity_state_count": unknown_activity_rows,
        }
    sampled = weighted_sample(included, points, n_points, matched_seed)
    if len(sampled) != n_points:
        raise RuntimeError(f"{geometry}/{family}: sampled {len(sampled)} != {n_points}")
    directory = staging / "sources" / geometry / family
    directory.mkdir(parents=True, exist_ok=False)
    source, table = write_family_source(directory, geometry, family, sampled, included_activity, triggers)
    drawn = Counter((row["volume"], row["ZA"], row["excitation_keV"]) for row in sampled)
    manifest = {
        "schema_version": 1,
        "status": "PASS__GROUND_STATE_EXACT_POSITION_SOURCE_READY__NONZERO_STATES_FAIL_CLOSED",
        "geometry": geometry,
        "family": family,
        "source": rel(OUTPUT_ROOT / source.relative_to(staging)),
        "sampled_positions_table": rel(OUTPUT_ROOT / table.relative_to(staging)),
        "geometry_path": rel(source_geometry(geometry)),
        "sampling_seed": matched_seed,
        "transport_seed": matched_seed,
        "matched_geometry_seed_key": f"delayed_phase02|{family}",
        "n_pointsource_blocks": n_points,
        "triggers_requested": triggers,
        "min_points": MIN_POINTS,
        "included_ground_activity_Bq": included_activity,
        "known_holdout_activity_Bq": known_holdout_activity,
        "known_holdout_activity_fraction": known_holdout_activity / known_total if known_total > 0 else 0.0,
        "unknown_activity_state_count": unknown_activity_rows,
        "included_states": included,
        "holdout_states": holdout,
        "sampled_state_counts": [
            {"volume": key[0], "ZA": key[1], "excitation_keV": key[2], "drawn": count}
            for key, count in drawn.most_common()
        ],
        "RPIP_audit": rpip_audit,
        "boundary": [
            "Ground-state activity uses NUBASE-2020 and corrected catalog sum(RP)/sum(TT), including zero-RP TT.",
            "Every sampled source position is an exact CC IP RP position in the matching geometry/family/volume/ZA/state support.",
            "Non-zero excitation states are never collapsed to ground state; the installed PointSource syntax cannot encode their excitation and they remain explicit holdouts.",
            "This is a delayed-source preparation artifact, not a delayed-rate, response, mission-sensitivity, or geometry-promotion authority.",
        ],
    }
    atomic_json_once(directory / "source_manifest.json", manifest)
    return manifest


def make_transport_jobs(cells: list[dict[str, Any]], seeds: dict[str, int]) -> list[dict[str, Any]]:
    jobs = []
    for row in cells:
        if not str(row.get("status", "")).startswith("PASS"):
            continue
        geometry, family = row["geometry"], row["family"]
        source = ROOT / row["source"]
        partial = OUTPUT_ROOT / "transport" / geometry / family / ".attempt01.partial"
        final = partial.parent / "attempt01"
        prefix = partial / f"DelayedDay15_{geometry}_{family}_M50000"
        final_prefix = final / f"DelayedDay15_{geometry}_{family}_M50000"
        jobs.append({
            "job_id": f"delayed02_{family}_{geometry}",
            "geometry": geometry,
            "family": family,
            "source": rel(source),
            "seed": seeds[family],
            "matched_geometry_seed_key": f"delayed_phase02|{family}",
            "triggers": TRIGGERS_PER_POSITIVE_FAMILY,
            "attempt_partial_dir": rel(partial),
            "attempt_final_dir": rel(final),
            "output_prefix": rel(prefix),
            "expected_sim": rel(prefix.with_suffix(".inc1.id1.sim.gz")),
            "published_sim": rel(final_prefix.with_suffix(".inc1.id1.sim.gz")),
            "declared_cap_bytes": DECLARED_JOB_CAP_BYTES,
            "command": [str(COSIMA), "-s", str(seeds[family]), rel(source)],
        })
    return sorted(jobs, key=lambda row: (FAMILIES.index(row["family"]), GEOMETRIES.index(row["geometry"])))


def parse_selector(value: str | None, *, families: bool) -> tuple[str, ...] | None:
    """Parse a comma-separated CLI selector without silently dropping errors."""
    if value is None:
        return None
    tokens = [token.strip() for token in value.split(",") if token.strip()]
    if not tokens:
        raise ValueError("selector must contain at least one non-empty token")
    if families:
        tokens = [canonical_family(token) for token in tokens]
        unknown = sorted(set(tokens) - set(FAMILIES))
        if unknown:
            raise ValueError(f"unknown delayed family selector(s): {unknown}")
    if len(tokens) != len(set(tokens)):
        raise ValueError(f"duplicate selector token(s): {tokens}")
    return tuple(tokens)


def select_transport_jobs(
    planned_jobs: list[dict[str, Any]],
    requested_families: tuple[str, ...] | None = None,
    requested_job_ids: tuple[str, ...] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Select transport work while preserving paired geometry family runs."""
    if requested_families is not None and requested_job_ids is not None:
        raise ValueError("--families and --job-ids are mutually exclusive")
    by_id = {str(job["job_id"]): job for job in planned_jobs}
    if len(by_id) != len(planned_jobs):
        raise RuntimeError("transport plan contains duplicate job IDs")
    if requested_families is not None:
        selected = []
        for family in requested_families:
            family_jobs = [job for job in planned_jobs if job["family"] == family]
            observed = {str(job["geometry"]) for job in family_jobs}
            if observed != set(GEOMETRIES):
                raise RuntimeError(
                    f"paired-family selection requires both geometries for {family}: "
                    f"observed={sorted(observed)}, expected={list(GEOMETRIES)}"
                )
            selected.extend(sorted(family_jobs, key=lambda row: GEOMETRIES.index(row["geometry"])))
        selector_type = "paired_families"
    elif requested_job_ids is not None:
        missing = [job_id for job_id in requested_job_ids if job_id not in by_id]
        if missing:
            raise ValueError(f"unknown delayed transport job ID(s): {missing}")
        selected = [by_id[job_id] for job_id in requested_job_ids]
        for family in {str(job["family"]) for job in selected}:
            observed = {
                str(job["geometry"]) for job in selected if str(job["family"]) == family
            }
            if observed != set(GEOMETRIES):
                raise RuntimeError(
                    f"exact-job selection must retain the matched geometry pair for {family}: "
                    f"observed={sorted(observed)}, expected={list(GEOMETRIES)}"
                )
        selector_type = "exact_job_ids"
    else:
        selected = list(planned_jobs)
        selector_type = "all_prepared_jobs"
    if not selected:
        raise RuntimeError("transport selection contains zero jobs")
    selected_ids = [str(job["job_id"]) for job in selected]
    selected_set = set(selected_ids)
    planned_ids = [str(job["job_id"]) for job in planned_jobs]
    selected_families = {str(job["family"]) for job in selected}
    planned_families = {str(job["family"]) for job in planned_jobs}
    full = selected_set == set(planned_ids) and len(selected_ids) == len(planned_ids)
    metadata = {
        "selector_type": selector_type,
        "requested_families": list(requested_families or ()),
        "requested_job_ids": list(requested_job_ids or ()),
        "selected_job_ids": selected_ids,
        "omitted_job_ids": [job_id for job_id in planned_ids if job_id not in selected_set],
        "selected_families": [family for family in FAMILIES if family in selected_families],
        "fully_omitted_families": [family for family in FAMILIES if family in planned_families - selected_families],
        "prepared_job_count": len(planned_jobs),
        "selected_job_count": len(selected),
        "all_prepared_jobs_selected": full,
        "paired_geometry_requirement": (
            "ENFORCED_FOR_EACH_REQUESTED_FAMILY"
            if requested_families is not None
            else (
                "ENFORCED_FOR_EACH_SELECTED_EXACT_JOB_FAMILY"
                if requested_job_ids is not None else "FULL_PREPARED_PLAN_SELECTED"
            )
        ),
    }
    return selected, metadata


def tree_bytes(path: Path) -> int:
    """Return current logical file bytes below a job attempt directory."""
    if not path.exists():
        return 0
    total = 0
    for directory, _subdirs, files in os.walk(path):
        for name in files:
            try:
                total += (Path(directory) / name).stat().st_size
            except FileNotFoundError:
                # A producer may atomically rename a file between walk/stat.
                pass
    return total


def disk_admission_decision(
    free_bytes: int,
    active_usage: list[dict[str, int]],
    candidate_cap_bytes: int = 0,
    reserve_bytes: int = FILESYSTEM_RESERVE_BYTES,
) -> dict[str, Any]:
    """Reserve every active job's *remaining* cap plus the next job's cap.

    Free space already reflects bytes written by active jobs, so subtracting
    their current sizes from their declared caps avoids double counting while
    still guaranteeing the configured reserve if every admitted job reaches
    its cap.
    """
    cap_exceeded = [
        row for row in active_usage if int(row["current_bytes"]) > int(row["cap_bytes"])
    ]
    active_remaining = sum(
        max(0, int(row["cap_bytes"]) - int(row["current_bytes"]))
        for row in active_usage
    )
    required = int(reserve_bytes) + active_remaining + int(candidate_cap_bytes)
    return {
        "free_bytes": int(free_bytes),
        "reserve_bytes": int(reserve_bytes),
        "active_jobs": len(active_usage),
        "active_current_bytes": sum(int(row["current_bytes"]) for row in active_usage),
        "active_remaining_cap_bytes": active_remaining,
        "candidate_cap_bytes": int(candidate_cap_bytes),
        "required_free_bytes": required,
        "projected_reserve_margin_bytes": int(free_bytes) - required,
        "cap_exceeded_job_ids": [str(row["job_id"]) for row in cap_exceeded],
        "admitted": not cap_exceeded and int(free_bytes) >= required,
    }


def runtime_disk_snapshot(
    active: dict[int, dict[str, Any]], candidate: dict[str, Any] | None = None
) -> dict[str, Any]:
    usage = []
    for item in active.values():
        job = item["job"]
        usage.append({
            "job_id": str(job["job_id"]),
            "current_bytes": tree_bytes(ROOT / job["attempt_partial_dir"]),
            "cap_bytes": int(job["declared_cap_bytes"]),
        })
    candidate_cap = int(candidate["declared_cap_bytes"]) if candidate is not None else 0
    decision = disk_admission_decision(
        shutil.disk_usage(ROOT).free, usage, candidate_cap, FILESYSTEM_RESERVE_BYTES
    )
    decision["active_usage"] = usage
    decision["candidate_job_id"] = str(candidate["job_id"]) if candidate is not None else None
    return decision


def selection_summary_path(selection: dict[str, Any]) -> Path:
    if selection["all_prepared_jobs_selected"]:
        return OUTPUT_ROOT / "transport_summary.json"
    canonical = json.dumps(selection["selected_job_ids"], separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode()).hexdigest()[:12]
    return OUTPUT_ROOT / f"transport_summary.partial_{digest}.json"


def prepare() -> dict[str, Any]:
    authority = validate_authority()
    catalog_path = resolve_catalog_path()
    payload = load_json(catalog_path)
    validate_catalog(payload)
    if OUTPUT_ROOT.exists():
        manifest = load_json(OUTPUT_ROOT / "manifest.json")
        if not str(manifest.get("status", "")).startswith("PASS"):
            raise RuntimeError(f"existing write-once package is not PASS: {OUTPUT_ROOT}")
        return manifest
    staging = OUTPUT_ROOT.with_name(f".{OUTPUT_ROOT.name}.partial.{os.getpid()}")
    if staging.exists():
        raise RuntimeError(f"staging directory exists: {staging}")
    staging.mkdir(parents=True)
    try:
        nubase = load_nubase_states()
        seeds = allocate_matched_seeds()
        cells = []
        for family in FAMILIES:
            for geometry in GEOMETRIES:
                cells.append(build_cell(staging, payload, geometry, family, nubase, seeds[family]))
        jobs = make_transport_jobs(cells, seeds)
        atomic_json_once(staging / "transport_jobs.json", {
            "schema_version": 1,
            "status": "READY_NOT_LAUNCHED",
            "workers": TRANSPORT_WORKERS,
            "filesystem_reserve_bytes": FILESYSTEM_RESERVE_BYTES,
            "jobs": jobs,
            "transport_launched": False,
        })
        manifest = {
            "schema_version": 1,
            "status": "PASS__STATE_AWARE_EXACT_POSITION_DELAYED_SOURCES_READY__TRANSPORT_NOT_LAUNCHED",
            "created_utc": now_utc(),
            "controller": rel(THIS_FILE),
            "catalog": rel(catalog_path),
            "catalog_sha256": sha256(catalog_path),
            "NUBASE": rel(NUBASE),
            "NUBASE_sha256": sha256(NUBASE),
            "NUBASE_expected_sha256": NUBASE_SHA256,
            "source_contract_sha256": SOURCE_CONTRACT_SHA256,
            "batch_authority": authority,
            "positive_transport_jobs": len(jobs),
            "pointsource_blocks_per_job": POINTS_PER_POSITIVE_FAMILY,
            "triggers_per_job": TRIGGERS_PER_POSITIVE_FAMILY,
            "transport_workers": TRANSPORT_WORKERS,
            "filesystem_reserve_bytes": FILESYSTEM_RESERVE_BYTES,
            "matched_transport_seeds": seeds,
            "cells": cells,
            "transport_jobs": rel(OUTPUT_ROOT / "transport_jobs.json"),
            "transport_launched": False,
            "authority_boundary": "CORRECTED_BUILDUP_TO_DELAYED_SOURCE_PREPARATION_ONLY__NONZERO_STATES_FAIL_CLOSED",
        }
        atomic_json_once(staging / "manifest.json", manifest)
        staging.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staging, OUTPUT_ROOT)
        return manifest
    except BaseException:
        # Preserve staging for diagnosis; do not delete evidence.
        raise


def minimal_sim_check(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"status": "FAIL", "problem": "missing_sim", "path": rel(path)}
    geometry = ""
    seed: int | None = None
    se = ids = en = 0
    try:
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                if raw.startswith("Geometry ") and not geometry:
                    # Cosima emits a variable-width separator (commonly three
                    # spaces) after ``Geometry``.  Splitting once on a literal
                    # space leaves leading blanks in the path and can turn an
                    # otherwise valid absolute path into a bogus relative one.
                    fields = raw.split(maxsplit=1)
                    if len(fields) == 2:
                        geometry = fields[1].strip()
                elif raw.startswith("Seed ") and seed is None:
                    fields = raw.split()
                    if len(fields) >= 2:
                        seed = int(fields[1])
                elif raw.startswith("SE"):
                    se += 1
                elif raw.startswith("ID"):
                    ids += 1
                elif raw.startswith("EN"):
                    en += 1
    except (OSError, EOFError) as exc:
        return {"status": "FAIL", "problem": f"gzip_or_read_error:{exc}", "path": rel(path)}
    status = "PASS" if se == ids == TRIGGERS_PER_POSITIVE_FAMILY and en == 1 else "FAIL"
    return {
        "status": status, "path": rel(path), "SE": se, "ID": ids, "EN": en,
        "geometry": geometry, "seed": seed,
    }


def _dedupe_path(value: str) -> str:
    seen: set[str] = set()
    output = []
    for item in value.split(":"):
        if item and item not in seen:
            seen.add(item)
            output.append(item)
    return ":".join(output)


def clean_cosima_env() -> tuple[dict[str, str], dict[str, Any]]:
    """Reproduce the validated batch0006 env-i/source-megalib contract."""
    setup = COSIMA.parent / "source-megalib.sh"
    if not setup.is_file():
        raise RuntimeError(f"missing MEGAlib setup: {setup}")
    command = [
        "/usr/bin/env", "-i", f"HOME={Path.home()}", "USER=ubuntu", "LOGNAME=ubuntu",
        "PATH=/usr/bin:/bin", "SHELL=/bin/bash", "/bin/bash", "--noprofile", "--norc",
        "-c", 'source "$1" >/dev/null 2>&1; env -0', "bash", str(setup),
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"clean MEGAlib environment failed: {result.stderr.decode(errors='replace')}")
    environment: dict[str, str] = {}
    for item in result.stdout.split(b"\0"):
        if item and b"=" in item:
            key, raw = item.split(b"=", 1)
            environment[key.decode(errors="replace")] = raw.decode(errors="replace")
    for key in ("PATH", "LD_LIBRARY_PATH"):
        environment[key] = _dedupe_path(environment.get(key, ""))
    relevant = {
        key: value for key, value in sorted(environment.items())
        if key in {"MEGALIB", "ROOTSYS"} or key.startswith("G4") or key.startswith("GEANT4")
    }
    provenance = {
        "setup": str(setup),
        "setup_sha256": sha256(setup),
        "relevant_environment": relevant,
        "relevant_environment_sha256": hashlib.sha256(
            (json.dumps(relevant, sort_keys=True, separators=(",", ":")) + "\n").encode()
        ).hexdigest(),
        "loader_contract": "env-i_then_source-megalib_then_dedupe_PATH_LD_LIBRARY_PATH",
    }
    return environment, provenance


def run_transport(
    requested_families: tuple[str, ...] | None = None,
    requested_job_ids: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Later-only six-worker controller with subset and live-disk guards."""
    plan_path = OUTPUT_ROOT / "transport_jobs.json"
    plan = load_json(plan_path)
    planned_jobs = list(plan["jobs"])
    selected_jobs, selection = select_transport_jobs(
        planned_jobs, requested_families, requested_job_ids
    )
    summary_path = selection_summary_path(selection)
    if summary_path.exists():
        raise FileExistsError(f"write-once transport summary exists: {summary_path}")
    for job in selected_jobs:
        partial = ROOT / job["attempt_partial_dir"]
        final = ROOT / job["attempt_final_dir"]
        if partial.exists() or final.exists():
            raise RuntimeError(f"write-once transport attempt target exists: {partial} or {final}")
    jobs = deque(selected_jobs)
    active: dict[int, dict[str, Any]] = {}
    completed = []
    launch_admissions = []
    minimum_free_bytes = shutil.disk_usage(ROOT).free
    maximum_active_bytes_by_job: dict[str, int] = defaultdict(int)
    environment, environment_provenance = clean_cosima_env()

    def observe(snapshot: dict[str, Any]) -> None:
        nonlocal minimum_free_bytes
        minimum_free_bytes = min(minimum_free_bytes, int(snapshot["free_bytes"]))
        for row in snapshot["active_usage"]:
            job_id = str(row["job_id"])
            maximum_active_bytes_by_job[job_id] = max(
                maximum_active_bytes_by_job[job_id], int(row["current_bytes"])
            )

    def terminate_active() -> None:
        for item in active.values():
            try:
                os.killpg(item["process"].pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

    while jobs or active:
        active_guard = runtime_disk_snapshot(active)
        observe(active_guard)
        if active and not active_guard["admitted"]:
            terminate_active()
            raise RuntimeError(
                "dynamic disk guard stopped this delayed subset before the 20 GiB reserve "
                f"could be consumed: {active_guard}"
            )
        while jobs and len(active) < TRANSPORT_WORKERS:
            admission = runtime_disk_snapshot(active, jobs[0])
            observe(admission)
            if not admission["admitted"]:
                break
            job = jobs.popleft()
            partial = ROOT / job["attempt_partial_dir"]
            final = ROOT / job["attempt_final_dir"]
            partial.mkdir(parents=True)
            log_path = partial / "cosima.log"
            log_handle = log_path.open("x", encoding="utf-8")
            process = subprocess.Popen(
                [str(COSIMA), "-s", str(job["seed"]), str(ROOT / job["source"])],
                cwd=ROOT,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env=environment,
            )
            active[process.pid] = {"job": job, "process": process, "log": log_handle, "started": time.monotonic()}
            launch_admissions.append({**admission, "launched_job_id": job["job_id"]})
        if not active and jobs:
            blocked = runtime_disk_snapshot(active, jobs[0])
            observe(blocked)
            raise RuntimeError(
                "dynamic disk admission stopped: 20 GiB reserve plus the next declared "
                f"job cap is unavailable: {blocked}"
            )
        time.sleep(1.0)
        for pid, item in list(active.items()):
            code = item["process"].poll()
            if code is None:
                continue
            item["log"].close()
            job = item["job"]
            partial = ROOT / job["attempt_partial_dir"]
            final = ROOT / job["attempt_final_dir"]
            check = minimal_sim_check(ROOT / job["expected_sim"])
            expected_geometry = source_geometry(job["geometry"])
            try:
                observed_geometry = Path(str(check.get("geometry", ""))).resolve()
            except OSError:
                observed_geometry = Path("/__invalid_geometry__")
            if check.get("status") == "PASS" and observed_geometry != expected_geometry:
                check["status"] = "FAIL"
                check["problem"] = "SIM_geometry_header_mismatch"
            if check.get("status") == "PASS" and int(check.get("seed") or -1) != int(job["seed"]):
                check["status"] = "FAIL"
                check["problem"] = "SIM_seed_header_mismatch"
            observed_output_bytes = tree_bytes(partial)
            receipt_status = (
                "PASS"
                if code == 0
                and check["status"] == "PASS"
                and observed_output_bytes <= int(job["declared_cap_bytes"])
                else "FAIL"
            )
            if receipt_status == "PASS":
                check["checked_attempt_path"] = check["path"]
                check["path"] = job["published_sim"]
                check["path_binding"] = "published_after_atomic_attempt_directory_rename"
            receipt = {
                "job": job,
                "returncode": code,
                "wall_s": time.monotonic() - item["started"],
                "observed_output_bytes_before_receipt": observed_output_bytes,
                "declared_cap_bytes": int(job["declared_cap_bytes"]),
                "declared_cap_exceeded": observed_output_bytes > int(job["declared_cap_bytes"]),
                "minimal_sim_check": check,
                "published_sim": job["published_sim"],
                "status": receipt_status,
                "runtime_environment": environment_provenance,
            }
            atomic_json_once(partial / "receipt.json", receipt)
            if receipt["status"] == "PASS":
                os.replace(partial, final)
            completed.append(receipt)
            del active[pid]
            if receipt["status"] != "PASS":
                terminate_active()
                raise RuntimeError(f"delayed transport failed: {job['job_id']}")
    full = bool(selection["all_prepared_jobs_selected"])
    summary = {
        "schema_version": 2,
        "status": (
            "PASS__ALL_PREPARED_DELAYED_TRANSPORT_JOBS_COMPLETED"
            if full else "PASS__SELECTED_DELAYED_TRANSPORT_SUBSET_COMPLETED"
        ),
        "coverage_status": (
            "ALL_PREPARED_JOBS__TRANSPORT_ONLY__DOWNSTREAM_CLOSURE_NOT_CLAIMED"
            if full else "PARTIAL_SUBSET__NOT_FULL_DELAYED_OR_PAPER_CLOSURE"
        ),
        "created_utc": now_utc(),
        "transport_plan": rel(plan_path),
        "selection": selection,
        "jobs": completed,
        "completed": len(completed),
        "completed_job_ids": [receipt["job"]["job_id"] for receipt in completed],
        "dynamic_disk_admission": {
            "policy": "live_free_minus_active_remaining_caps_minus_candidate_cap_ge_20GiB_reserve",
            "filesystem_reserve_bytes": FILESYSTEM_RESERVE_BYTES,
            "minimum_observed_free_bytes": minimum_free_bytes,
            "launch_admissions": launch_admissions,
            "maximum_active_bytes_by_job": dict(sorted(maximum_active_bytes_by_job.items())),
        },
        "paper_closure_claimed": False,
        "authority_boundary": (
            "SELECTED_CORRECTED_KEV_STATE_AWARE_DELAYED_TRANSPORT_ONLY__"
            "NO_RESPONSE_MISSION_SENSITIVITY_GEOMETRY_PROMOTION_OR_FULL_PAPER_CLOSURE"
        ),
        "summary_path": rel(summary_path),
    }
    atomic_json_once(summary_path, summary)
    return summary


def print_plan() -> dict[str, Any]:
    available = CATALOG.is_file() or CATALOG_COMPAT.is_file()
    return {
        "status": "READY_TO_PREPARE" if available else "WAITING_FOR_BATCH0007_CORRECTED_BUILDUP_CATALOG",
        "controller": rel(THIS_FILE),
        "catalog": rel(CATALOG),
        "catalog_available": available,
        "geometries": GEOMETRIES,
        "families": FAMILIES,
        "maximum_candidate_cells": len(GEOMETRIES) * len(FAMILIES),
        "positive_activity_policy": "one source/transport per geometry-family with positive transportable ground-state activity",
        "state_key": ["geometry", "family", "logical_volume", "ZA", "excitation_keV"],
        "min_points": MIN_POINTS,
        "exact_positions_per_positive_family": POINTS_PER_POSITIVE_FAMILY,
        "delayed_triggers_per_positive_family": TRIGGERS_PER_POSITIVE_FAMILY,
        "NUBASE_ground_state": rel(NUBASE),
        "nonzero_excitation_policy": "fail_closed_holdout_never_ground_state_collapse",
        "transport_workers": TRANSPORT_WORKERS,
        "preferred_first_transport_families": PREFERRED_FIRST_FAMILIES,
        "subset_selector_cli": {
            "paired_families": "--families p,n,alpha,gamma,eminus,muminus",
            "exact_jobs": "--job-ids delayed02_p_Mass_model_511,delayed02_p_S3d_O8",
        },
        "dynamic_disk_admission_policy": (
            "live free space must cover 20 GiB reserve, every active job's remaining "
            "declared cap, and the candidate job's declared cap"
        ),
        "matched_geometry_seed_policy": True,
        "filesystem_reserve_bytes": FILESYSTEM_RESERVE_BYTES,
        "transport_launched": False,
    }


def self_test() -> dict[str, Any]:
    nubase = load_nubase_states()
    ground, ground_why = match_nubase_state(nubase, 11024, 0.0)
    isomer, isomer_why = match_nubase_state(nubase, 11024, 472.21)
    assert ground and ground["half_life_s"] and ground["half_life_s"] > 0
    assert isomer and isomer["half_life_s"] and isomer["half_life_s"] > 0
    rows = [
        {"volume": "SyntheticVolume", "isotope_id": 11024, "excitation_keV": 0.0, "production_rate_s-1": 2.0},
        {"volume": "SyntheticVolume", "isotope_id": 11024, "excitation_keV": 472.21, "production_rate_s-1": 1.0},
        {"volume": "SyntheticVolume", "isotope_id": 11024, "excitation_keV": 100.0, "production_rate_s-1": 0.5},
    ]
    points = {
        state_key("SyntheticVolume", 11024, 0.0): [(1.0, 2.0, 3.0), (2.0, 3.0, 4.0)],
        state_key("SyntheticVolume", 11024, 472.21): [(4.0, 5.0, 6.0)],
        state_key("SyntheticVolume", 11024, 100.0): [(7.0, 8.0, 9.0)],
    }
    included, holdout = classify_states(rows, points, nubase)
    assert len(included) == 1 and included[0]["excitation_keV"] == 0.0
    assert any(row["excitation_keV"] == 472.21 and row["day15_activity_Bq"] is not None for row in holdout)
    assert any(row["excitation_keV"] == 100.0 and row["day15_activity_Bq"] is None for row in holdout)
    sampled = weighted_sample(included, points, 100, 1_234_567)
    assert len(sampled) == 100
    assert {row["excitation_keV"] for row in sampled} == {0.0}
    environment, environment_provenance = clean_cosima_env()
    assert environment.get("MEGALIB")
    assert environment_provenance["loader_contract"].startswith("env-i_")
    catalog_fixture = {
        "status": "PASS__CORRECTED_BUILDUP_CATALOG_READY",
        "authority_class": "CORRECTED_KEV_BUILDUP_DAT_AND_RICH_SIM_REFERENCE_CATALOG",
        "source_contract_sha256": SOURCE_CONTRACT_SHA256,
        "legacy_factor1000_included": False,
        "extra_mono511_included": False,
        "mode": "buildup_only",
        "batch0007_state": "INCLUDED__FINAL_PASS",
        "normalization": {"zero_RP_DAT_TT_retained": True},
        "cells": [
            {"geometry": geometry, "family": family}
            for geometry in GEOMETRIES for family in FAMILIES
        ],
        "dat_entries": [],
        "production_rows": [],
    }
    validate_catalog(catalog_fixture)
    bad_fixture = dict(catalog_fixture)
    bad_fixture["status"] = "WAIT__BATCH0007_FINAL_PASS"
    try:
        validate_catalog(bad_fixture)
    except RuntimeError:
        pass
    else:
        raise AssertionError("non-final catalog was not rejected")
    synthetic_jobs = [
        {
            "job_id": f"delayed02_{family}_{geometry}",
            "geometry": geometry,
            "family": family,
            "declared_cap_bytes": DECLARED_JOB_CAP_BYTES,
        }
        for family in FAMILIES for geometry in GEOMETRIES
    ]
    selected, selection = select_transport_jobs(
        synthetic_jobs, PREFERRED_FIRST_FAMILIES, None
    )
    assert len(selected) == 12 and selection["selected_job_count"] == 12
    assert not selection["all_prepared_jobs_selected"]
    assert {job["family"] for job in selected} == set(PREFERRED_FIRST_FAMILIES)
    assert all(
        {job["geometry"] for job in selected if job["family"] == family} == set(GEOMETRIES)
        for family in PREFERRED_FIRST_FAMILIES
    )
    exact, exact_selection = select_transport_jobs(
        synthetic_jobs,
        None,
        ("delayed02_p_Mass_model_511", "delayed02_p_S3d_O8"),
    )
    assert len(exact) == 2 and exact_selection["selector_type"] == "exact_job_ids"
    try:
        select_transport_jobs(
            synthetic_jobs, None, ("delayed02_p_Mass_model_511",)
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("single-geometry exact-job selection was accepted")
    incomplete = [
        job for job in synthetic_jobs
        if job["job_id"] != "delayed02_p_S3d_O8"
    ]
    try:
        select_transport_jobs(incomplete, ("p",), None)
    except RuntimeError:
        pass
    else:
        raise AssertionError("incomplete paired-family transport selection was accepted")
    admission = disk_admission_decision(
        47 * 1024**3,
        [
            {"job_id": f"job{index}", "current_bytes": 0, "cap_bytes": DECLARED_JOB_CAP_BYTES}
            for index in range(5)
        ],
        DECLARED_JOB_CAP_BYTES,
    )
    assert admission["admitted"] and admission["active_jobs"] == 5
    blocked = disk_admission_decision(
        FILESYSTEM_RESERVE_BYTES + DECLARED_JOB_CAP_BYTES - 1,
        [],
        DECLARED_JOB_CAP_BYTES,
    )
    assert not blocked["admitted"]
    over_cap = disk_admission_decision(
        47 * 1024**3,
        [{"job_id": "over", "current_bytes": 3, "cap_bytes": 2}],
    )
    assert not over_cap["admitted"] and over_cap["cap_exceeded_job_ids"] == ["over"]
    with tempfile.TemporaryDirectory(prefix="delayed02_selftest_") as value:
        temp = Path(value)
        # Exercise write syntax without publishing into the campaign namespace.
        old_output = globals()["OUTPUT_ROOT"]
        try:
            globals()["OUTPUT_ROOT"] = temp / "published"
            directory = temp / "source"
            directory.mkdir()
            source, table = write_family_source(directory, "Mass_model_511", "n", sampled, 1.0, 1_000)
            text = source.read_text(encoding="utf-8")
            assert text.count(".ParticleType 11024") == 100
            assert "excitation_keV=0.00" in text
            assert "excitation_keV=472.21" not in text
            assert len(table.read_text(encoding="utf-8").splitlines()) == 101
        finally:
            globals()["OUTPUT_ROOT"] = old_output
    return {
        "status": "PASS__DELAYED_PHASE02_STATIC_AND_SYNTHETIC_SELF_TEST",
        "tests": 26,
        "ground_match": ground_why,
        "isomer_match": isomer_why,
        "included_ground_states": len(included),
        "held_out_states": len(holdout),
        "sampled_positions": len(sampled),
        "preferred_subset_jobs": len(selected),
        "dynamic_disk_admission_tested": True,
        "transport_launched": False,
        "campaign_files_written": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--print-plan", action="store_true")
    actions.add_argument("--self-test", action="store_true")
    actions.add_argument("--prepare", action="store_true")
    actions.add_argument("--run-transport", action="store_true")
    parser.add_argument(
        "--execute-transport",
        action="store_true",
        help="required second gate with --run-transport; never used during preparation",
    )
    selectors = parser.add_mutually_exclusive_group()
    selectors.add_argument(
        "--families",
        help=(
            "comma-separated families; each requested family must have both geometries "
            "in the prepared plan"
        ),
    )
    selectors.add_argument(
        "--job-ids",
        help=(
            "comma-separated exact prepared transport job IDs; every represented family "
            "must include its Mass/O8 pair"
        ),
    )
    args = parser.parse_args()
    if not args.run_transport and (args.families is not None or args.job_ids is not None):
        parser.error("--families/--job-ids are only valid with --run-transport")
    try:
        family_selector = parse_selector(args.families, families=True)
        job_id_selector = parse_selector(args.job_ids, families=False)
    except ValueError as exc:
        parser.error(str(exc))
    if args.print_plan:
        payload = print_plan()
    elif args.self_test:
        payload = self_test()
    elif args.prepare:
        payload = prepare()
    else:
        if not args.execute_transport:
            raise SystemExit("--run-transport requires the separate --execute-transport authorization gate")
        payload = run_transport(family_selector, job_id_selector)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
