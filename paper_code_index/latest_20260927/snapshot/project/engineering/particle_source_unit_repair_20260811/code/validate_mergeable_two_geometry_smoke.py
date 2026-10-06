#!/usr/bin/env python3
"""Fail-closed validator and merge ledger for the corrected-source smoke."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any

from run_mergeable_two_geometry_smoke import (
    BATCH_ID,
    CAMPAIGN_VERSION,
    EXPECTED_JOBS_PER_CAMPAIGN,
    FAMILIES,
    FARFIELD_RADIUS_CM,
    GAMMA_EVENTS,
    GAMMA_SPLITS,
    GEOMETRIES,
    GLOBAL_CONTRACT,
    MERGE_LEDGER,
    MODES,
    NON_GAMMA_REPLICAS,
    PACKAGE,
    ROOT,
    RUNNER,
    RUN_ROOT,
    SEED_BASE_BY_MODE,
    SEED_STRIDE,
    SOURCE_CONTRACT,
    VALIDATION_REPORT,
    atomic_json,
    build_geometry_bundle,
    build_transport_fingerprint,
    expected_seeds,
    output_dir,
    rel,
    resolve_cosima,
    resolve_transport_environment,
    runner_command,
    sha256,
    source_manifest_path,
)


PARTICLE_TYPES = {
    "alpha": 21,
    "eminus": 3,
    "eplus": 2,
    "gamma": 1,
    "muminus": 9,
    "muplus": 8,
    "n": 6,
    "p": 4,
}
SOURCE_NAME_RE = re.compile(r"^Background_(?P<family>.+?)_fullsphere20\.source$")
JOB_NAME_RE = re.compile(
    r"^Background_(?P<family>.+?)_fullsphere20_rep(?P<rep>\d{2})_part(?P<part>\d{2})$"
)
FLUX_RE = re.compile(r"\.Flux\s+([-+0-9.eE]+)\s*$")
SPECTRUM_RE = re.compile(r"\.Spectrum\s+File\s+(\S+)\s*$")
GEOMETRY_RE = re.compile(r"^Geometry\s+(\S+)\s*$")
ID_RE = re.compile(r"^ID\s+(\d+)(?:\s|$)")
GENERATED_RE = re.compile(r"Total number of generated particles:\s+(\d+)")
OBSERVATION_RE = re.compile(r"Observation time:\s+([-+0-9.eE]+) sec")
RETURN_RE = re.compile(r"^returncode=(\d+)\s*$", re.MULTILINE)
LEGACY_MARKER = "cosima_spectra_dp_2602units"
ACTIVE_PROPERTY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*\.(ParticleType|Beam|Spectrum|Flux)\s+")
SPECTRUM_FILE_RE = re.compile(r"^(?P<family>.+?)_bin(?P<bin>\d{2})_theta.+\.spectrum$")


class Gate:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.checks: Counter[str] = Counter()

    def require(self, condition: bool, message: str, check: str = "requirements") -> bool:
        self.checks[check] += 1
        if not condition:
            self.errors.append(message)
            return False
        return True

    def problem(self, message: str, check: str = "requirements") -> None:
        self.checks[check] += 1
        self.errors.append(message)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def source_contract_geometry_files(
    source_contract: dict[str, Any], geometry: str, environment: dict[str, str]
) -> list[dict[str, str]]:
    files: list[dict[str, str]] = []
    bundle = source_contract["geometries"][geometry]["geometry_bundle"]
    for entry in bundle["files"]:
        if entry.get("scope") == "repository":
            path = resolve_repo_path(entry["path"])
        elif entry.get("scope") == "megalib":
            megalib = environment.get("MEGALIB")
            if not megalib:
                raise ValueError("MEGALIB is unset while resolving source-contract geometry bundle")
            path = (Path(megalib) / entry["path_relative_to_megalib"]).resolve()
        else:
            raise ValueError(f"unknown geometry bundle scope {entry.get('scope')!r}")
        files.append({"path": rel(path), "sha256": str(entry["sha256"])})
    return sorted(files, key=lambda item: item["path"])


def parse_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return parsed if math.isfinite(parsed) else None


def source_flux(path: Path) -> float:
    values = [
        float(match.group(1))
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if (match := FLUX_RE.search(line))
    ]
    if len(values) != 20 or any(value <= 0.0 or not math.isfinite(value) for value in values):
        raise ValueError(f"{rel(path)} does not contain 20 positive finite Flux entries")
    return math.fsum(values)


def source_geometry(path: Path) -> str:
    values = [
        match.group(1)
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if (match := GEOMETRY_RE.match(line.strip()))
    ]
    if len(values) != 1:
        raise ValueError(f"{rel(path)} has {len(values)} Geometry lines")
    return values[0]


def spectrum_points(path: Path) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[0] == "DP":
            points.append((float(fields[1]), float(fields[2])))
    if len(points) < 2:
        raise ValueError(f"{rel(path)} has fewer than two DP points")
    if any(not math.isfinite(x) or not math.isfinite(y) for x, y in points):
        raise ValueError(f"{rel(path)} has non-finite DP values")
    return points


def expected_patched_source(
    base_source: Path,
    mode: str,
    events: int,
    seed: int,
    sim_prefix: Path,
    isotope_prefix: Path,
) -> str:
    """Reproduce the runner's complete, explicitly allowed card transform."""
    run_name: str | None = None
    seen_seed = False
    seen_store = False
    seen_iso = False
    lines: list[str] = []
    for line in base_source.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith("Run "):
            fields = stripped.split()
            if len(fields) >= 2:
                run_name = fields[1]
            lines.append(line)
            continue
        if stripped.startswith("Seed "):
            seen_seed = True
            lines.append(f"Seed {seed}")
            continue
        if stripped.startswith("StoreIsotopes"):
            seen_store = True
            lines.append("StoreIsotopes true")
            continue
        if stripped.startswith("DecayMode"):
            if mode == "buildup":
                lines.append("DecayMode ActivationBuildUp")
            continue
        if ".Events" in line:
            prefix = line.split(".Events", 1)[0].strip()
            lines.append(f"{prefix}.Events {events}")
            continue
        if ".FileName" in line:
            prefix = line.split(".FileName", 1)[0].strip()
            lines.append(f"{prefix}.FileName {sim_prefix}")
            continue
        if ".IsotopeProductionFile" in line:
            seen_iso = True
            prefix = line.split(".IsotopeProductionFile", 1)[0].strip()
            lines.append(f"{prefix}.IsotopeProductionFile {isotope_prefix}")
            continue
        lines.append(line)

    insert_at = 0
    for index, line in enumerate(lines):
        if line.strip().startswith("Geometry "):
            insert_at = index + 1
            break
    additions: list[str] = []
    if not seen_seed:
        additions.append(f"Seed {seed}")
    if not seen_store:
        additions.append("StoreIsotopes true")
    if mode == "buildup" and not any(line.strip().startswith("DecayMode") for line in lines):
        additions.append("DecayMode ActivationBuildUp")
    if additions:
        lines[insert_at:insert_at] = additions
    if not seen_iso and run_name:
        lines.append(f"{run_name}.IsotopeProductionFile {isotope_prefix}")
    return "\n".join(lines) + "\n"


def parse_isotope_dat(path: Path) -> dict[str, Any]:
    """Parse universal isotope-store TT/RP records without assuming RP exists."""
    tt_values: list[float] = []
    records: list[dict[str, Any]] = []
    problems: list[str] = []
    current_volume: str | None = None
    end_count = 0
    for line_number, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if fields[0] == "TT":
            if len(fields) != 2:
                problems.append(f"line {line_number}: malformed TT")
                continue
            value = parse_float(fields[1])
            if value is None or value <= 0.0:
                problems.append(f"line {line_number}: TT is not positive finite")
            else:
                tt_values.append(value)
            continue
        if fields[0] == "VN":
            current_volume = line[2:].strip()
            if not current_volume:
                problems.append(f"line {line_number}: empty VN")
            continue
        if fields[0] == "RP":
            if len(fields) != 4:
                problems.append(f"line {line_number}: malformed RP field count={len(fields)}")
                continue
            try:
                isotope_id = int(fields[1])
            except ValueError:
                isotope_id = -1
            excitation = parse_float(fields[2])
            value = parse_float(fields[3])
            if current_volume is None:
                problems.append(f"line {line_number}: RP appears before VN")
            if isotope_id <= 0:
                problems.append(f"line {line_number}: invalid isotope ID")
            if excitation is None or excitation < 0.0:
                problems.append(f"line {line_number}: excitation is not finite nonnegative")
            if value is None or value < 0.0:
                problems.append(f"line {line_number}: RP is not finite nonnegative")
            if current_volume is not None and isotope_id > 0 and excitation is not None and excitation >= 0.0 and value is not None and value >= 0.0:
                records.append(
                    {
                        "volume": current_volume,
                        "isotope_id": isotope_id,
                        "excitation_keV": excitation,
                        "RP": value,
                    }
                )
            continue
        if fields[0] == "EN" and len(fields) == 1:
            end_count += 1
            continue
        problems.append(f"line {line_number}: unrecognized isotope-store record {fields[0]!r}")

    if len(tt_values) != 1:
        problems.append(f"TT record count={len(tt_values)}, expected 1")
    if end_count != 1:
        problems.append(f"EN record count={end_count}, expected 1")
    grouped: dict[tuple[str, int, float], float] = {}
    for record in records:
        key = (str(record["volume"]), int(record["isotope_id"]), float(record["excitation_keV"]))
        grouped[key] = math.fsum((grouped.get(key, 0.0), float(record["RP"])))
    totals = [
        {
            "volume": key[0],
            "isotope_id": key[1],
            "excitation_keV": key[2],
            "sum_RP": value,
        }
        for key, value in sorted(grouped.items())
    ]
    return {
        "TT_s": tt_values[0] if len(tt_values) == 1 else None,
        "RP_record_count": len(records),
        "RP_records": records,
        "RP_totals_by_volume_isotope_state": totals,
        "problems": problems,
    }


def expected_job_contract(source_dir: Path, mode: str) -> dict[str, dict[str, Any]]:
    fluxes: dict[str, float] = {}
    sources: dict[str, Path] = {}
    for path in sorted(source_dir.glob("Background_*_fullsphere20.source")):
        match = SOURCE_NAME_RE.match(path.name)
        if not match:
            continue
        family = match.group("family")
        fluxes[family] = source_flux(path)
        sources[family] = path.resolve()
    if set(fluxes) != set(FAMILIES):
        raise ValueError(f"{rel(source_dir)} is not the complete eight-family source")
    gamma_flux = fluxes["gamma"]
    events = {
        family: GAMMA_EVENTS if family == "gamma" else int(round(flux / gamma_flux * GAMMA_EVENTS))
        for family, flux in fluxes.items()
    }
    order = ["gamma", *sorted(set(FAMILIES) - {"gamma"})]
    expected: dict[str, dict[str, Any]] = {}
    for ordinal, family in enumerate(order, 1):
        name = f"Background_{family}_fullsphere20_rep01_part01"
        expected[name] = {
            "family": family,
            "mode": mode,
            "events": events[family],
            "rep": 1,
            "part": 1,
            "seed": SEED_BASE_BY_MODE[mode] + ordinal * SEED_STRIDE,
            "source": sources[family],
            "flux_cm2_s": fluxes[family],
        }
    return expected


def parse_init(line: str) -> dict[str, float | int]:
    fields = [field.strip() for field in line.split("IA INIT", 1)[1].split(";")]
    if len(fields) < 23:
        raise ValueError(f"malformed IA INIT with {len(fields)} fields")
    values: dict[str, float | int] = {
        "particle_type": int(fields[15]),
        "dir_x": float(fields[16]),
        "dir_y": float(fields[17]),
        "dir_z": float(fields[18]),
        "energy_keV": float(fields[22]),
    }
    if not all(math.isfinite(float(value)) for value in values.values()):
        raise ValueError("non-finite IA INIT field")
    return values


def angular_bin_from_init_dir_z(dir_z: float) -> int:
    # FarFieldAreaSource source direction is opposite the inward IA direction.
    return max(0, min(19, int(math.floor((1.0 + dir_z) * 10.0))))


def scan_sim(
    path: Path,
    family: str,
    expected_events: int,
    expected_seed: int,
    expected_geometry: Path,
    support_by_bin: dict[int, tuple[float, float]],
) -> dict[str, Any]:
    problems: list[str] = []
    ids: list[int] = []
    init_records = 0
    current_id: int | None = None
    current_init = 0
    header_geometry: str | None = None
    header_seed: int | None = None
    energy_min: float | None = None
    energy_max: float | None = None
    bad_energy = 0
    bad_particle = 0
    bad_direction = 0

    def add_problem(message: str) -> None:
        if len(problems) < 20:
            problems.append(message)

    def finish_event() -> None:
        nonlocal current_id, current_init
        if current_id is None:
            return
        if current_init != 1:
            add_problem(f"ID {current_id}: IA INIT count={current_init}, expected 1")
        current_id = None
        current_init = 0

    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.strip()
            if header_geometry is None and (match := GEOMETRY_RE.match(line)):
                header_geometry = match.group(1)
            if header_seed is None and line.startswith("Seed "):
                try:
                    header_seed = int(line.split()[1])
                except (IndexError, ValueError):
                    add_problem(f"malformed SIM Seed header: {line}")
            if line == "SE":
                finish_event()
                continue
            if match := ID_RE.match(line):
                if current_id is not None:
                    add_problem(f"ID {current_id}: next ID arrived before SE")
                    finish_event()
                current_id = int(match.group(1))
                ids.append(current_id)
                continue
            if not line.startswith("IA INIT"):
                continue
            if current_id is None:
                add_problem("IA INIT outside an event")
                continue
            current_init += 1
            init_records += 1
            try:
                init = parse_init(line)
            except Exception as exc:
                add_problem(f"ID {current_id}: {exc}")
                continue
            if int(init["particle_type"]) != PARTICLE_TYPES[family]:
                bad_particle += 1
            direction = (float(init["dir_x"]), float(init["dir_y"]), float(init["dir_z"]))
            norm = math.sqrt(math.fsum(component * component for component in direction))
            if not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=5.0e-4):
                bad_direction += 1
            energy = float(init["energy_keV"])
            energy_min = energy if energy_min is None else min(energy_min, energy)
            energy_max = energy if energy_max is None else max(energy_max, energy)
            angular_bin = angular_bin_from_init_dir_z(direction[2])
            low, high = support_by_bin[angular_bin]
            tolerance = max(0.002, 1.0e-10 * max(abs(low), abs(high)))
            if not low - tolerance <= energy <= high + tolerance:
                # Printed IA directions have only five decimals.  Admit the
                # immediately adjacent angular supports only at a rounded edge.
                neighbor_support = [
                    support_by_bin[index]
                    for index in (angular_bin - 1, angular_bin + 1)
                    if index in support_by_bin
                ]
                if not any(lo - tolerance <= energy <= hi + tolerance for lo, hi in neighbor_support):
                    bad_energy += 1
        finish_event()

    if header_geometry is None:
        add_problem("missing SIM Geometry header")
    elif resolve_repo_path(header_geometry) != expected_geometry.resolve():
        add_problem(f"wrong SIM Geometry header: {header_geometry}")
    if header_seed != expected_seed:
        add_problem(f"SIM Seed={header_seed}, expected {expected_seed}")
    if ids != list(range(1, expected_events + 1)):
        add_problem(f"SIM IDs are not exactly 1..{expected_events} (observed {len(ids)})")
    if init_records != expected_events:
        add_problem(f"IA INIT records={init_records}, expected {expected_events}")
    if bad_particle:
        add_problem(f"wrong IA INIT particle type records={bad_particle}")
    if bad_direction:
        add_problem(f"non-unit IA INIT direction records={bad_direction}")
    if bad_energy:
        add_problem(f"IA INIT energy outside corrected per-bin support records={bad_energy}")
    return {
        "events": len(ids),
        "ia_init_records": init_records,
        "energy_min_keV": energy_min,
        "energy_max_keV": energy_max,
        "bad_energy_records": bad_energy,
        "bad_particle_records": bad_particle,
        "bad_direction_records": bad_direction,
        "geometry_header": header_geometry,
        "seed_header": header_seed,
        "problems": problems,
    }


def validate_source_card(
    gate: Gate,
    base_source: Path,
    job_source: Path,
    family: str,
    mode: str,
    job_name: str,
    events: int,
    seed: int,
    outdir: Path,
    spectrum_hashes: dict[str, str],
) -> tuple[dict[int, tuple[float, float]], int, int]:
    label = rel(job_source)
    text = job_source.read_text(encoding="utf-8", errors="replace")
    base_text = base_source.read_text(encoding="utf-8", errors="replace")
    base_properties = [line.strip() for line in base_text.splitlines() if ACTIVE_PROPERTY_RE.match(line.strip())]
    job_properties = [line.strip() for line in text.splitlines() if ACTIVE_PROPERTY_RE.match(line.strip())]
    gate.require(job_properties == base_properties, f"{label}: active source fields differ from corrected original card", "source_card")
    expected_text = expected_patched_source(
        base_source,
        mode,
        events,
        seed,
        outdir / job_name,
        outdir / f"{job_name}.dat",
    )
    gate.require(
        text == expected_text,
        f"{label}: full card differs from deterministic allowed runner transform",
        "source_card_exact",
    )
    gate.require("StoreSimulationInfo all" in text, f"{label}: StoreSimulationInfo all missing", "source_card")
    gate.require("StoreIsotopes true" in text, f"{label}: StoreIsotopes true missing", "source_card")
    gate.require(text.count("PhysicsListHD qgsp-bic-hp") == 1, f"{label}: PhysicsListHD contract changed", "source_card")
    gate.require(text.count("PhysicsListEM LivermorePol") == 1, f"{label}: PhysicsListEM contract changed", "source_card")
    gate.require(text.count("DetectorTimeConstant 1e-9") == 1, f"{label}: DetectorTimeConstant contract changed", "source_card")
    gate.require(text.count(f"Seed {seed}") == 1, f"{label}: Seed directive mismatch", "source_card")
    has_buildup = "DecayMode ActivationBuildUp" in text
    gate.require(has_buildup == (mode == "buildup"), f"{label}: DecayMode does not match {mode}", "source_card")

    refs = [match.group(1) for line in text.splitlines() if (match := SPECTRUM_RE.search(line))]
    corrected = 0
    legacy = text.count(LEGACY_MARKER)
    bins: dict[int, tuple[float, float]] = {}
    observed_bins: set[int] = set()
    for value in refs:
        path = resolve_repo_path(value)
        match = SPECTRUM_FILE_RE.match(path.name)
        if not match or match.group("family") != family:
            gate.problem(f"{label}: wrong-family or malformed spectrum reference {value}", "source_refs")
            continue
        bin_index = int(match.group("bin"))
        observed_bins.add(bin_index)
        expected_hash = spectrum_hashes.get(rel(path))
        if not is_within(path, PACKAGE / "spectra/correct_keV_total") or expected_hash is None:
            gate.problem(f"{label}: spectrum is outside canonical corrected contract: {value}", "source_refs")
            continue
        if not path.is_file():
            gate.problem(f"{label}: missing spectrum {value}", "source_refs")
            continue
        gate.require(sha256(path) == expected_hash, f"{label}: spectrum hash mismatch {value}", "source_hash")
        points = spectrum_points(path)
        bins[bin_index] = (points[0][0], points[-1][0])
        corrected += 1
    gate.require(len(refs) == 20, f"{label}: spectrum refs={len(refs)}, expected 20", "source_refs")
    gate.require(observed_bins == set(range(20)), f"{label}: angular spectrum bins are not exactly 00..19", "source_refs")
    gate.require(legacy == 0, f"{label}: legacy corrected-unit marker count={legacy}", "source_refs")
    gate.require(corrected == 20, f"{label}: canonical corrected refs={corrected}, expected 20", "source_refs")
    return bins, corrected, legacy


def validate_campaign(
    gate: Gate,
    geometry: str,
    mode: str,
    spectrum_hashes: dict[str, str],
    global_contract_hash: str,
    global_contract: dict[str, Any],
    current_geometry_bundle: dict[str, Any],
) -> dict[str, Any]:
    label = f"{geometry}/{mode}"
    outdir = output_dir(geometry, mode)
    expected = expected_job_contract(GEOMETRIES[geometry], mode)
    migration_path = source_manifest_path(geometry)
    migration = load_json(migration_path)
    expected_geometry = resolve_repo_path(migration["geometry_setup"])
    gate.require(expected_geometry.is_file(), f"{label}: geometry file missing {rel(expected_geometry)}", "geometry")
    gate.require(
        migration.get("source_contract_manifest_sha256") == sha256(SOURCE_CONTRACT),
        f"{label}: source migration manifest is not bound to current source contract",
        "binding",
    )

    batch_contract_path = outdir / "batch_contract.json"
    normalization_path = outdir / "normalization.json"
    manifest_path = outdir / "run_manifest.csv"
    summary_path = outdir / "run_summary.json"
    summary_csv_path = outdir / "run_summary.csv"
    summary_md_path = outdir / "run_summary.md"
    for required in (
        batch_contract_path,
        normalization_path,
        manifest_path,
        summary_path,
        summary_csv_path,
        summary_md_path,
    ):
        gate.require(required.is_file(), f"{label}: missing {rel(required)}", "outputs")
    if not all(
        path.is_file()
        for path in (
            batch_contract_path,
            normalization_path,
            manifest_path,
            summary_path,
            summary_csv_path,
            summary_md_path,
        )
    ):
        return {"geometry": geometry, "mode": mode, "status": "FAIL_MISSING_CAMPAIGN_FILES", "jobs": []}

    batch_contract = load_json(batch_contract_path)
    normalization = load_json(normalization_path)
    summary_rows = load_json(summary_path)
    binding = normalization.get("mergeable_smoke_binding", {})
    fixed_contract = {
        "batch_id": BATCH_ID,
        "campaign_version": CAMPAIGN_VERSION,
        "geometry": geometry,
        "mode": mode,
        "source_contract_manifest_sha256": sha256(SOURCE_CONTRACT),
        "source_migration_manifest_sha256": sha256(migration_path),
        "global_contract_sha256": global_contract_hash,
    }
    for key, value in fixed_contract.items():
        gate.require(batch_contract.get(key) == value, f"{label}: batch_contract {key} mismatch", "binding")
        gate.require(binding.get(key) == value, f"{label}: normalization binding {key} mismatch", "binding")
    frozen_geometry_bundle = global_contract["geometry_bundles"][geometry]
    gate.require(batch_contract.get("geometry_bundle") == frozen_geometry_bundle, f"{label}: batch geometry bundle mismatch", "geometry")
    gate.require(
        batch_contract.get("source_contract_geometry_bundle_sha256")
        == global_contract["source_contract_geometry_bundle_sha256_by_geometry"][geometry],
        f"{label}: batch source-contract geometry bundle digest mismatch",
        "geometry",
    )
    gate.require(current_geometry_bundle == frozen_geometry_bundle, f"{label}: current transitive geometry bundle changed", "geometry")
    gate.require(
        binding.get("geometry_bundle_sha256") == frozen_geometry_bundle["bundle_sha256"],
        f"{label}: normalization geometry bundle digest mismatch",
        "geometry",
    )
    frozen_transport = global_contract["transport"]
    for key, value in {
        "transport_cosima": frozen_transport["cosima"],
        "transport_cosima_sha256": frozen_transport["cosima_sha256"],
        "transport_shared_libraries_bundle_sha256": frozen_transport["shared_libraries_bundle_sha256"],
        "transport_environment_sha256": frozen_transport["environment"]["relevant_variables_sha256"],
        "source_contract_geometry_bundle_sha256": global_contract[
            "source_contract_geometry_bundle_sha256_by_geometry"
        ][geometry],
        "dynamic_validator_sha256": global_contract["toolchain"]["dynamic_validator"]["sha256"],
    }.items():
        gate.require(binding.get(key) == value, f"{label}: normalization {key} mismatch", "transport")
    gate.require(
        binding.get("batch_contract_sha256") == sha256(batch_contract_path),
        f"{label}: normalization batch-contract hash mismatch",
        "binding",
    )
    gate.require(
        resolve_repo_path(binding.get("batch_contract", "__missing__")) == batch_contract_path.resolve(),
        f"{label}: normalization points to wrong batch contract",
        "binding",
    )

    expected_normalization = {
        "mode": mode,
        "source_dir": rel(GEOMETRIES[geometry]),
        "outdir": rel(outdir),
        "gamma_events": GAMMA_EVENTS,
        "gamma_splits": GAMMA_SPLITS,
        "non_gamma_replicas": NON_GAMMA_REPLICAS,
        "farfield_radius_cm": FARFIELD_RADIUS_CM,
        "jobs": EXPECTED_JOBS_PER_CAMPAIGN,
        "store_isotopes": True,
        "seed_base": SEED_BASE_BY_MODE[mode],
        "seed_stride": SEED_STRIDE,
    }
    for key, value in expected_normalization.items():
        gate.require(normalization.get(key) == value, f"{label}: normalization {key}={normalization.get(key)!r}, expected {value!r}", "normalization")
    gate.require(
        normalization.get("selected_particles") == sorted(FAMILIES),
        f"{label}: selected_particles is not exactly all eight families",
        "normalization",
    )
    gate.require("farfield_radius_warning" not in normalization, f"{label}: farfield radius warning is present", "normalization")
    expected_fluxes = {item["family"]: item["flux_cm2_s"] for item in expected.values()}
    expected_events_by_family = {item["family"]: item["events"] for item in expected.values()}
    normalized_fluxes = normalization.get("flux_by_particle_cm2_s", {})
    gate.require(set(normalized_fluxes) == set(FAMILIES), f"{label}: normalization flux family set mismatch", "normalization")
    for family, flux in expected_fluxes.items():
        observed_flux = parse_float(normalized_fluxes.get(family))
        gate.require(
            observed_flux is not None and math.isclose(observed_flux, flux, rel_tol=1.0e-12, abs_tol=1.0e-15),
            f"{label}: normalization flux mismatch for {family}",
            "normalization",
        )
    gate.require(
        normalization.get("base_events_by_particle") == expected_events_by_family,
        f"{label}: normalization base_events_by_particle mismatch",
        "normalization",
    )
    area = math.pi * FARFIELD_RADIUS_CM * FARFIELD_RADIUS_CM
    expected_gamma_time = GAMMA_EVENTS / (expected_fluxes["gamma"] * area)
    for key, value in {
        "farfield_area_cm2": area,
        "gamma_prompt_time_s_with_farfield_area": expected_gamma_time,
        "gamma_norm_factor_cm2_s_per_count": expected_fluxes["gamma"] / GAMMA_EVENTS,
        "non_gamma_combined_norm_factor_cm2_s_per_count": expected_fluxes["gamma"] / GAMMA_EVENTS,
    }.items():
        observed = parse_float(normalization.get(key))
        gate.require(
            observed is not None and math.isclose(observed, value, rel_tol=1.0e-12, abs_tol=1.0e-15),
            f"{label}: normalization {key} mismatch",
            "normalization",
        )

    with manifest_path.open(newline="", encoding="utf-8") as handle:
        manifest_rows = list(csv.DictReader(handle))
    with summary_csv_path.open(newline="", encoding="utf-8") as handle:
        summary_csv_rows = list(csv.DictReader(handle))
    summary_by_name = {str(row.get("job_name")): row for row in summary_rows}
    summary_csv_by_name = {str(row.get("job_name")): row for row in summary_csv_rows}
    manifest_by_name = {str(row.get("job_name")): row for row in manifest_rows}
    gate.require(len(manifest_rows) == EXPECTED_JOBS_PER_CAMPAIGN, f"{label}: run_manifest rows={len(manifest_rows)}", "jobs")
    gate.require(len(manifest_by_name) == len(manifest_rows), f"{label}: duplicate run_manifest job names", "jobs")
    gate.require(len(summary_rows) == EXPECTED_JOBS_PER_CAMPAIGN, f"{label}: run_summary rows={len(summary_rows)}", "jobs")
    gate.require(len(summary_by_name) == len(summary_rows), f"{label}: duplicate run_summary job names", "jobs")
    gate.require(len(summary_csv_rows) == EXPECTED_JOBS_PER_CAMPAIGN, f"{label}: run_summary.csv rows={len(summary_csv_rows)}", "jobs")
    gate.require(len(summary_csv_by_name) == len(summary_csv_rows), f"{label}: duplicate run_summary.csv job names", "jobs")
    gate.require(set(manifest_by_name) == set(expected), f"{label}: run_manifest job set differs from fixed all-eight contract", "jobs")
    gate.require(set(summary_by_name) == set(expected), f"{label}: run_summary job set differs from run contract", "jobs")
    gate.require(set(summary_csv_by_name) == set(expected), f"{label}: run_summary.csv job set differs from run contract", "jobs")

    campaign_jobs: list[dict[str, Any]] = []
    campaign_seeds: list[int] = []
    corrected_refs = 0
    legacy_refs = 0
    activation_accumulator: dict[tuple[str, str, int, float], float] = {}
    family_tt_accumulator: dict[str, float] = {}
    for job_name, job_expected in expected.items():
        row = manifest_by_name.get(job_name)
        summary = summary_by_name.get(job_name)
        summary_csv = summary_csv_by_name.get(job_name)
        if row is None or summary is None or summary_csv is None:
            continue
        family = job_expected["family"]
        prefix = f"{label}/{job_name}"
        scalar_expectations = {
            "particle": family,
            "mode": mode,
            "events": str(job_expected["events"]),
            "rep": "1",
            "part": "1",
            "seed": str(job_expected["seed"]),
        }
        for key, value in scalar_expectations.items():
            gate.require(row.get(key) == value, f"{prefix}: manifest {key}={row.get(key)!r}, expected {value!r}", "jobs")
        gate.require(str(row.get("store_isotopes", "")).lower() == "true", f"{prefix}: isotope store disabled", "jobs")
        gate.require(resolve_repo_path(row["source"]) == job_expected["source"], f"{prefix}: wrong corrected base source", "jobs")

        job_source = resolve_repo_path(row["temp_source"])
        sim_path = resolve_repo_path(row["sim_path"])
        dat_path = resolve_repo_path(row["dat_path"])
        log_path = resolve_repo_path(row["log"])
        expected_paths = {
            "job source": outdir / "job_sources" / f"{job_name}.source",
            "SIM": outdir / f"{job_name}.inc1.id1.sim.gz",
            "DAT": outdir / f"{job_name}.dat.inc1.dat",
            "log": outdir / "logs" / f"{job_name}.log",
        }
        for kind, path in (("job source", job_source), ("SIM", sim_path), ("DAT", dat_path), ("log", log_path)):
            gate.require(is_within(path, outdir), f"{prefix}: {kind} escapes campaign directory", "outputs")
            gate.require(path == expected_paths[kind].resolve(), f"{prefix}: unexpected {kind} path", "outputs")
            gate.require(path.is_file(), f"{prefix}: missing {kind} {rel(path)}", "outputs")
        if not all(path.is_file() for path in (job_source, sim_path, dat_path, log_path)):
            continue
        gate.require(sim_path.stat().st_size > 0, f"{prefix}: empty SIM", "outputs")
        gate.require(dat_path.stat().st_size > 0, f"{prefix}: empty isotope DAT", "outputs")
        gate.require(log_path.stat().st_size > 0, f"{prefix}: empty log", "outputs")

        gate.require(source_geometry(job_source) == migration["geometry_setup"], f"{prefix}: job source geometry mismatch", "geometry")
        supports, corrected, legacy = validate_source_card(
            gate,
            job_expected["source"],
            job_source,
            family,
            mode,
            job_name,
            job_expected["events"],
            job_expected["seed"],
            outdir,
            spectrum_hashes,
        )
        corrected_refs += corrected
        legacy_refs += legacy
        if set(supports) != set(range(20)):
            continue

        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        generated_match = GENERATED_RE.search(log_text)
        observation_match = OBSERVATION_RE.search(log_text)
        return_match = RETURN_RE.search(log_text)
        generated = int(generated_match.group(1)) if generated_match else None
        observation = float(observation_match.group(1)) if observation_match else None
        expected_cosima_command = (
            f"cosima_command={global_contract['transport']['cosima']} -s {job_expected['seed']} {job_source}"
        )
        gate.require("***  Error" not in log_text and "Segmentation fault" not in log_text, f"{prefix}: Cosima error marker in log", "log")
        gate.require(
            log_text.count(expected_cosima_command) == 1,
            f"{prefix}: logged Cosima command/path/seed/source differs from frozen transport contract",
            "transport",
        )
        gate.require("MEGAlib version" in log_text, f"{prefix}: MEGAlib banner missing from log", "transport")
        gate.require(return_match is not None and int(return_match.group(1)) == 0, f"{prefix}: missing/nonzero returncode", "log")
        gate.require(generated == job_expected["events"], f"{prefix}: generated={generated}, expected={job_expected['events']}", "log")
        area = math.pi * FARFIELD_RADIUS_CM * FARFIELD_RADIUS_CM
        tt_formula = job_expected["events"] / (job_expected["flux_cm2_s"] * area)
        gate.require(
            observation is not None and math.isfinite(observation) and observation > 0.0,
            f"{prefix}: missing/nonpositive observation time",
            "normalization",
        )

        isotope_store = parse_isotope_dat(dat_path)
        for problem in isotope_store["problems"]:
            gate.problem(f"{prefix}: isotope DAT {problem}", "isotope_dat")
        dat_tt = isotope_store["TT_s"]
        gate.require(
            dat_tt is not None and math.isfinite(dat_tt) and dat_tt > 0.0,
            f"{prefix}: isotope DAT has no unique positive finite TT",
            "isotope_dat",
        )
        if dat_tt is not None:
            family_tt_accumulator[family] = math.fsum((family_tt_accumulator.get(family, 0.0), dat_tt))
            if observation is not None:
                gate.require(
                    math.isclose(dat_tt, observation, rel_tol=2.0e-3, abs_tol=2.0e-6),
                    f"{prefix}: isotope DAT TT={dat_tt:.12g} differs from log TT={observation:.12g}",
                    "isotope_dat",
                )
            for isotope in isotope_store["RP_totals_by_volume_isotope_state"]:
                key = (
                    family,
                    str(isotope["volume"]),
                    int(isotope["isotope_id"]),
                    float(isotope["excitation_keV"]),
                )
                activation_accumulator[key] = math.fsum(
                    (activation_accumulator.get(key, 0.0), float(isotope["sum_RP"]))
                )

        gate.require(summary.get("status") == "PASS", f"{prefix}: run_summary status={summary.get('status')!r}", "summary")
        gate.require(int(summary.get("events", -1)) == job_expected["events"], f"{prefix}: summary event request mismatch", "summary")
        gate.require(int(summary.get("generated_particles") or -1) == job_expected["events"], f"{prefix}: summary generated mismatch", "summary")
        gate.require(summary.get("sim_exists") is True and summary.get("dat_exists") is True, f"{prefix}: summary output flags are not true", "summary")
        for key, path in (("log", log_path), ("sim_path", sim_path), ("dat_path", dat_path)):
            gate.require(
                summary.get(key) == rel(path),
                f"{prefix}: summary {key} path mismatch",
                "summary",
            )
        gate.require(
            int(summary.get("sim_size_bytes") or -1) == sim_path.stat().st_size,
            f"{prefix}: summary SIM size mismatch",
            "summary",
        )
        gate.require(
            int(summary.get("dat_size_bytes") or -1) == dat_path.stat().st_size,
            f"{prefix}: summary DAT size mismatch",
            "summary",
        )
        for key in ("particle", "status", "events", "generated_particles"):
            gate.require(
                str(summary_csv.get(key, "")) == str(summary.get(key, "")),
                f"{prefix}: JSON/CSV summary {key} mismatch",
                "summary",
            )

        sim_scan = scan_sim(
            sim_path,
            family,
            job_expected["events"],
            job_expected["seed"],
            expected_geometry,
            supports,
        )
        for problem in sim_scan["problems"]:
            gate.problem(f"{prefix}: {problem}", "sim")
        campaign_seeds.append(job_expected["seed"])
        campaign_jobs.append(
            {
                "job_name": job_name,
                "family": family,
                "events": job_expected["events"],
                "seed": job_expected["seed"],
                "flux_cm2_s": job_expected["flux_cm2_s"],
                "TT_s_from_log": observation,
                "TT_s_from_isotope_dat": dat_tt,
                "TT_s_expected_mean_from_events_flux_area": tt_formula,
                "TT_authority": (
                    "positive matching DAT/log TT; events/(flux*pi*R^2) is only the stochastic expectation"
                ),
                "job_source": rel(job_source),
                "job_source_sha256": sha256(job_source),
                "sim": rel(sim_path),
                "sim_sha256": sha256(sim_path),
                "isotope_dat": rel(dat_path),
                "isotope_dat_sha256": sha256(dat_path),
                "isotope_store": isotope_store,
                "log": rel(log_path),
                "log_sha256": sha256(log_path),
                "ia_init": sim_scan,
            }
        )

    gate.require(corrected_refs == 160, f"{label}: corrected refs={corrected_refs}, expected 160", "source_refs")
    gate.require(legacy_refs == 0, f"{label}: legacy refs={legacy_refs}, expected 0", "source_refs")
    gate.require(set(family_tt_accumulator) == set(FAMILIES), f"{label}: DAT TT does not cover all eight families", "isotope_dat")
    gate.require(len(set(campaign_seeds)) == EXPECTED_JOBS_PER_CAMPAIGN, f"{label}: seeds are not unique within campaign", "seeds")
    gate.require(sorted(campaign_seeds) == sorted(expected_seeds(mode)), f"{label}: explicit seed set mismatch", "seeds")
    family_exposure = [
        {"family": family, "sum_TT_s": family_tt_accumulator[family]}
        for family in sorted(family_tt_accumulator)
    ]
    activation_production = []
    for (family, volume, isotope_id, excitation), sum_rp in sorted(activation_accumulator.items()):
        sum_tt = family_tt_accumulator[family]
        activation_production.append(
            {
                "family": family,
                "volume": volume,
                "isotope_id": isotope_id,
                "excitation_keV": excitation,
                "sum_RP": sum_rp,
                "sum_TT_s": sum_tt,
                "sum_RP_over_sum_TT_s-1": sum_rp / sum_tt,
            }
        )
    return {
        "geometry": geometry,
        "mode": mode,
        "batch_id": BATCH_ID,
        "outdir": rel(outdir),
        "source_dir": rel(GEOMETRIES[geometry]),
        "source_migration_manifest": rel(migration_path),
        "source_migration_manifest_sha256": sha256(migration_path),
        "geometry_setup": rel(expected_geometry),
        "geometry_setup_sha256": sha256(expected_geometry) if expected_geometry.is_file() else None,
        "normalization": rel(normalization_path),
        "normalization_sha256": sha256(normalization_path),
        "batch_contract": rel(batch_contract_path),
        "batch_contract_sha256": sha256(batch_contract_path),
        "run_manifest": rel(manifest_path),
        "run_manifest_sha256": sha256(manifest_path),
        "run_summary_json": rel(summary_path),
        "run_summary_json_sha256": sha256(summary_path),
        "run_summary_csv": rel(summary_csv_path),
        "run_summary_csv_sha256": sha256(summary_csv_path),
        "run_summary_md": rel(summary_md_path),
        "run_summary_md_sha256": sha256(summary_md_path),
        "geometry_bundle": frozen_geometry_bundle,
        "corrected_spectrum_references": corrected_refs,
        "legacy_spectrum_references": legacy_refs,
        "events_requested": sum(item["events"] for item in expected.values()),
        "events_with_validated_ia_init": sum(job["ia_init"]["ia_init_records"] for job in campaign_jobs),
        "seeds": sorted(campaign_seeds),
        "family_exposure_for_prompt_and_activation": family_exposure,
        "activation_RP_by_family_volume_isotope_state": activation_production,
        "zero_RP_merge_rule": (
            "family TT applies even when a batch has no RP row for an isotope; merge isotope RP against all "
            "registered family TT, including zero-RP batches"
        ),
        "jobs": campaign_jobs,
    }


def validate() -> tuple[dict[str, Any], dict[str, Any]]:
    gate = Gate()
    for required in (GLOBAL_CONTRACT, SOURCE_CONTRACT, RUNNER):
        gate.require(required.is_file(), f"missing required contract input {rel(required)}", "contract")
    if not GLOBAL_CONTRACT.is_file() or not SOURCE_CONTRACT.is_file():
        report = {
            "schema_version": 1,
            "status": "FAIL",
            "validator": rel(Path(__file__)),
            "errors": gate.errors,
            "checks": dict(gate.checks),
        }
        return report, {"schema_version": 1, "status": "FAIL_NOT_MERGE_ELIGIBLE", "errors": gate.errors}

    global_contract = load_json(GLOBAL_CONTRACT)
    source_contract = load_json(SOURCE_CONTRACT)
    source_contract_hash = sha256(SOURCE_CONTRACT)
    global_contract_hash = sha256(GLOBAL_CONTRACT)
    gate.require(global_contract.get("batch_id") == BATCH_ID, "global batch_id mismatch", "contract")
    gate.require(global_contract.get("campaign_version") == CAMPAIGN_VERSION, "global campaign_version mismatch", "contract")
    gate.require(global_contract.get("source_contract_manifest_sha256") == source_contract_hash, "global source contract hash mismatch", "contract")
    gate.require(global_contract.get("runner_sha256") == sha256(RUNNER), "current runner hash differs from global contract", "contract")
    toolchain = global_contract.get("toolchain", {})
    dynamic_record = toolchain.get("dynamic_validator", {})
    gate.require(
        dynamic_record.get("path") == rel(Path(__file__)) and dynamic_record.get("sha256") == sha256(Path(__file__)),
        "dynamic validator self hash/path differs from frozen toolchain",
        "contract",
    )
    for name, record in toolchain.items():
        try:
            path = resolve_repo_path(record["path"])
            gate.require(path.is_file() and sha256(path) == record["sha256"], f"frozen toolchain hash mismatch: {name}", "contract")
        except Exception as exc:
            gate.problem(f"malformed frozen toolchain record {name}: {exc}", "contract")
    stats = global_contract.get("statistics", {})
    for key, value in {
        "gamma_events": GAMMA_EVENTS,
        "gamma_splits": GAMMA_SPLITS,
        "non_gamma_replicas": NON_GAMMA_REPLICAS,
        "farfield_radius_cm": FARFIELD_RADIUS_CM,
        "expected_jobs_per_campaign": EXPECTED_JOBS_PER_CAMPAIGN,
    }.items():
        gate.require(stats.get(key) == value, f"global statistics {key} mismatch", "contract")
    gate.require(source_contract.get("families") == list(FAMILIES), "source contract families mismatch", "contract")
    gate.require(source_contract.get("bins_per_family") == 20, "source contract bins_per_family mismatch", "contract")
    gate.require(source_contract.get("farfield_radius_cm") == FARFIELD_RADIUS_CM, "source contract farfield radius mismatch", "contract")
    gate.require(source_contract.get("source_model", {}).get("profile") == "unit_only_total_gamma", "wrong source profile", "contract")
    gate.require(source_contract.get("policies", {}).get("additive_mono_511_allowed") is False, "source contract permits additive mono-511", "contract")

    frozen_transport = global_contract.get("transport", {})
    frozen_cosima = resolve_cosima(frozen_transport.get("cosima"))
    transport_environment, environment_descriptor = resolve_transport_environment(frozen_cosima)
    current_transport = build_transport_fingerprint(
        frozen_cosima, transport_environment, environment_descriptor
    )
    for key in (
        "cosima",
        "cosima_sha256",
        "help_returncode",
        "help_banner_sha256",
        "shared_libraries",
        "shared_libraries_bundle_sha256",
    ):
        gate.require(current_transport.get(key) == frozen_transport.get(key), f"transport fingerprint mismatch: {key}", "transport")
    for key in (
        "setup_script",
        "setup_script_sha256",
        "relevant_variables",
        "relevant_variables_sha256",
    ):
        gate.require(
            current_transport.get("environment", {}).get(key)
            == frozen_transport.get("environment", {}).get(key),
            f"transport environment fingerprint mismatch: {key}",
            "transport",
        )
    def g4_core(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {key: value for key, value in item.items() if key != "stat_inventory_sha256"}
            for item in items
        ]

    gate.require(
        g4_core(current_transport.get("environment", {}).get("g4_data_roots", []))
        == g4_core(frozen_transport.get("environment", {}).get("g4_data_roots", [])),
        "transport environment fingerprint mismatch: G4 data content inventories",
        "transport",
    )

    current_geometry_bundles: dict[str, dict[str, Any]] = {}
    frozen_geometry_bundles = global_contract.get("geometry_bundles", {})
    for geometry in GEOMETRIES:
        current_bundle = build_geometry_bundle(geometry, transport_environment)
        current_geometry_bundles[geometry] = current_bundle
        gate.require(
            current_bundle == frozen_geometry_bundles.get(geometry),
            f"{geometry}: transitive geometry bundle differs from global contract",
            "geometry",
        )
        source_bundle = source_contract["geometries"][geometry]
        gate.require(
            source_bundle.get("geometry_bundle_sha256")
            == global_contract.get("source_contract_geometry_bundle_sha256_by_geometry", {}).get(geometry),
            f"{geometry}: source-contract geometry bundle digest binding mismatch",
            "geometry",
        )
        expected_files = source_contract_geometry_files(source_contract, geometry, transport_environment)
        gate.require(
            expected_files == current_bundle["files"],
            f"{geometry}: runtime geometry file hashes differ from source-contract bundle inventory",
            "geometry",
        )

    workers = global_contract.get("execution", {}).get("workers")
    gate.require(isinstance(workers, int) and workers > 0, "global execution workers is not positive integer", "contract")
    contract_campaigns = global_contract.get("campaigns", [])
    campaign_index = {
        (item.get("geometry"), item.get("mode")): item
        for item in contract_campaigns
        if isinstance(item, dict)
    }
    expected_pairs = {(geometry, mode) for mode in MODES for geometry in GEOMETRIES}
    gate.require(len(contract_campaigns) == 4 and len(campaign_index) == 4, "global contract does not contain four unique campaigns", "contract")
    gate.require(set(campaign_index) == expected_pairs, "global contract campaign geometry/mode set mismatch", "contract")
    if isinstance(workers, int) and workers > 0:
        for geometry, mode in sorted(expected_pairs):
            campaign = campaign_index.get((geometry, mode), {})
            expected_values = {
                "batch_id": BATCH_ID,
                "campaign_version": CAMPAIGN_VERSION,
                "geometry": geometry,
                "mode": mode,
                "outdir": rel(output_dir(geometry, mode)),
                "source_dir": rel(GEOMETRIES[geometry]),
                "source_migration_manifest": rel(source_manifest_path(geometry)),
                "source_migration_manifest_sha256": sha256(source_manifest_path(geometry)),
                "source_contract_manifest": rel(SOURCE_CONTRACT),
                "source_contract_manifest_sha256": source_contract_hash,
                "geometry_bundle": frozen_geometry_bundles.get(geometry),
                "source_contract_geometry_bundle_sha256": source_contract["geometries"][geometry][
                    "geometry_bundle_sha256"
                ],
                "seed_base": SEED_BASE_BY_MODE[mode],
                "seed_stride": SEED_STRIDE,
                "expected_seeds": expected_seeds(mode),
                "command": runner_command(geometry, mode, workers, frozen_cosima),
            }
            for key, value in expected_values.items():
                gate.require(campaign.get(key) == value, f"global campaign {geometry}/{mode} {key} mismatch", "contract")

    spectrum_hashes = {
        str(entry["corrected_spectrum"]): str(entry["corrected_sha256"])
        for entry in source_contract.get("spectra", {}).get("files", [])
    }
    gate.require(len(spectrum_hashes) == 160, f"canonical corrected spectrum hash entries={len(spectrum_hashes)}", "contract")

    campaigns: list[dict[str, Any]] = []
    for mode in MODES:
        for geometry in GEOMETRIES:
            try:
                campaigns.append(
                    validate_campaign(
                        gate,
                        geometry,
                        mode,
                        spectrum_hashes,
                        global_contract_hash,
                        global_contract,
                        current_geometry_bundles[geometry],
                    )
                )
            except Exception as exc:
                gate.problem(f"{geometry}/{mode}: unexpected validation failure: {type(exc).__name__}: {exc}", "campaign_crash")
                campaigns.append({"geometry": geometry, "mode": mode, "status": "FAIL_VALIDATOR_EXCEPTION", "jobs": []})

    by_pair = {(item["geometry"], item["mode"]): item for item in campaigns}
    for mode in MODES:
        mass = by_pair.get(("mass_model_511", mode), {})
        o8 = by_pair.get(("s3d_o8", mode), {})
        mass_signature = [(job.get("job_name"), job.get("events"), job.get("seed")) for job in mass.get("jobs", [])]
        o8_signature = [(job.get("job_name"), job.get("events"), job.get("seed")) for job in o8.get("jobs", [])]
        gate.require(mass_signature == o8_signature and len(mass_signature) == EXPECTED_JOBS_PER_CAMPAIGN, f"{mode}: Mass/O8 matched-A/B job and seed streams differ", "paired_seeds")
    instant = set(expected_seeds("instant"))
    buildup = set(expected_seeds("buildup"))
    gate.require(instant.isdisjoint(buildup), "instant and buildup seed registries overlap", "paired_seeds")

    total_jobs = sum(len(campaign.get("jobs", [])) for campaign in campaigns)
    total_events = sum(sum(int(job.get("events", 0)) for job in campaign.get("jobs", [])) for campaign in campaigns)
    status = "PASS" if not gate.errors else "FAIL"
    report = {
        "schema_version": 1,
        "status": status,
        "validator": rel(Path(__file__)),
        "validator_sha256": sha256(Path(__file__)),
        "batch_id": BATCH_ID,
        "campaign_version": CAMPAIGN_VERSION,
        "source_contract_manifest": rel(SOURCE_CONTRACT),
        "source_contract_manifest_sha256": source_contract_hash,
        "global_contract": rel(GLOBAL_CONTRACT),
        "global_contract_sha256": global_contract_hash,
        "runner": rel(RUNNER),
        "runner_sha256": sha256(RUNNER),
        "transport": frozen_transport,
        "toolchain": global_contract.get("toolchain"),
        "checks": dict(sorted(gate.checks.items())),
        "errors": gate.errors,
        "campaign_count": len(campaigns),
        "validated_job_count": total_jobs,
        "validated_event_count": total_events,
        "campaigns": campaigns,
        "claims": {
            "source_transport_smoke": status == "PASS",
            "future_merge_eligibility": status == "PASS",
            "full_chain_or_physics_authority": False,
        },
    }
    ledger = {
        "schema_version": 1,
        "status": "PASS__BATCH0000_MERGE_ELIGIBLE" if status == "PASS" else "FAIL_NOT_MERGE_ELIGIBLE",
        "batch_id": BATCH_ID,
        "campaign_version": CAMPAIGN_VERSION,
        "validation_report": rel(VALIDATION_REPORT),
        "source_contract_manifest": rel(SOURCE_CONTRACT),
        "source_contract_manifest_sha256": source_contract_hash,
        "global_contract": rel(GLOBAL_CONTRACT),
        "global_contract_sha256": global_contract_hash,
        "runner": rel(RUNNER),
        "runner_sha256": sha256(RUNNER),
        "validator": rel(Path(__file__)),
        "validator_sha256": sha256(Path(__file__)),
        "transport": frozen_transport,
        "toolchain": global_contract.get("toolchain"),
        "geometry_bundles": frozen_geometry_bundles,
        "pooling_boundary": "never pool across geometry, mode, or family",
        "prompt_merge_rule": "within one geometry+mode+family: rate = sum(selected) / sum(TT)",
        "activation_isotope_merge_rule": (
            "within one geometry+mode+family+production-volume+isotope-state: production rate = sum(RP) / sum(TT)"
        ),
        "family_combination_rule": "sum separately normalized family rates; do not pool their raw counts or TT",
        "replica_rule": "read TT and RP from each recorded batch/job; no hardcoded replica divisor",
        "TT_authority": (
            "use the positive matching isotope-DAT/log observation TT; events/(flux*pi*R^2) is only the "
            "stochastic expectation"
        ),
        "zero_RP_rule": (
            "for an isotope-state union across batches, include every registered family TT in the denominator, "
            "including batches with no RP row for that volume/isotope-state"
        ),
        "seed_registry_rule": (
            "future batches in the same geometry+mode must register explicit seed sets disjoint from all prior batches; "
            "same-mode Mass/O8 equality is intentional matched-A/B provenance"
        ),
        "errors": gate.errors,
        "campaigns": campaigns if status == "PASS" else [],
    }
    return report, ledger


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate read-only; do not write report or ledger")
    args = parser.parse_args()
    try:
        report, ledger = validate()
    except Exception as exc:
        report = {
            "schema_version": 1,
            "status": "FAIL",
            "validator": rel(Path(__file__)),
            "errors": [f"unexpected validator failure: {type(exc).__name__}: {exc}"],
        }
        ledger = {
            "schema_version": 1,
            "status": "FAIL_NOT_MERGE_ELIGIBLE",
            "errors": report["errors"],
        }
    if not args.check:
        atomic_json(VALIDATION_REPORT, report)
        atomic_json(MERGE_LEDGER, ledger)
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if report.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
