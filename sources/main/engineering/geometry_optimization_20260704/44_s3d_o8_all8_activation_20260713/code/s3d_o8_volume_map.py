"""Fail-closed S3d-O8 logical/physical volume-name reconciliation.

MEGAlib isotope DAT files use logical-volume names, while ``CC IP RP`` records
can use physical copy names.  The historical generic helpers collapsed every
name containing ``window`` and did not resolve the multihole-W copies.  For
this campaign we keep exact logical names and resolve physical names only via
the retained geometry's explicit ``BASE.Copy COPY`` declarations.  No generic
numeric-suffix stripping is allowed.
"""

from __future__ import annotations

import gzip
import re
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterable


VN_RE = re.compile(r"^\s*VN\s+(\S+)\s*$")
RP_RE = re.compile(r"^\s*RP\s+(\d+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*$")
COPY_RE = re.compile(r"^\s*(?P<logical>\S+)\.Copy\s+(?P<physical>\S+)\s*$")
TES_COPY_RE = re.compile(r"^TP_L(?P<layer>[0-5])_\d{5}$")
W_HBAR_COPY_RE = re.compile(r"^W_Multihole_Collimator_HBar_\d{3}$")
W_VBAR_COPY_RE = re.compile(
    r"^W_Multihole_Collimator_VBar_(?P<kind>Center|Edge)_\d{4}$"
)

LOGICAL_VOLUMES: set[str] = set()
GEOMETRY_COPY_MAP: dict[str, str] = {}
EXCITATION_QUANTUM_KEV = Decimal("0.01")
EXCITATION_MATCH_TOLERANCE_KEV = Decimal("0.0050001")
EXPECTED_GEOMETRY_COPY_DECLARATIONS = 2_880


def canonicalize_excitation(value_keV: float | str) -> float:
    """Match SIM excitation values at the 0.01-keV precision printed by DAT."""
    quantized = Decimal(str(value_keV)).quantize(
        EXCITATION_QUANTUM_KEV,
        rounding=ROUND_HALF_UP,
    )
    value = float(quantized)
    return 0.0 if value == 0.0 else value


def excitation_values_from_dat(
    dat_files: Iterable[Path],
) -> dict[tuple[str, int], set[Decimal]]:
    values: dict[tuple[str, int], set[Decimal]] = defaultdict(set)
    for path in dat_files:
        current: str | None = None
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = VN_RE.match(raw)
            if match:
                current = match.group(1)
                continue
            rmatch = RP_RE.match(raw)
            if rmatch and current is not None:
                values[(current, int(rmatch.group(1)))].add(Decimal(rmatch.group(2)))
    return values


def match_dat_excitation(
    vn: str,
    za: int,
    sim_or_dat_excitation_keV: float | str,
    dat_values: dict[tuple[str, int], set[Decimal]],
) -> float:
    raw = Decimal(str(sim_or_dat_excitation_keV))
    candidates = [
        value
        for value in dat_values.get((str(vn), int(za)), set())
        if abs(value - raw) <= EXCITATION_MATCH_TOLERANCE_KEV
    ]
    if len(candidates) != 1:
        raise RuntimeError(
            "S3d-O8 excitation match must be unique: "
            f"VN={vn} ZA={za} raw_keV={raw} candidates={sorted(candidates)}"
        )
    value = float(candidates[0])
    return 0.0 if value == 0.0 else value


def logical_volumes_from_dat(dat_files: Iterable[Path]) -> set[str]:
    names: set[str] = set()
    for path in dat_files:
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = VN_RE.match(raw)
            if match:
                names.add(match.group(1))
    return names


def copy_map_from_geometry(path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    conflicts: dict[str, set[str]] = defaultdict(set)
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = COPY_RE.match(raw)
        if not match:
            continue
        logical = match.group("logical")
        physical = match.group("physical")
        tes = TES_COPY_RE.match(physical)
        w_hbar = W_HBAR_COPY_RE.match(physical)
        w_vbar = W_VBAR_COPY_RE.match(physical)
        if tes:
            expected_logical = f"TES_Pixel_L{tes.group('layer')}"
        elif w_hbar:
            expected_logical = "W_Multihole_Collimator_HBar"
        elif w_vbar:
            expected_logical = (
                f"W_Multihole_Collimator_VBar_{w_vbar.group('kind')}"
            )
        else:
            raise RuntimeError(
                f"unreviewed S3d-O8 geometry Copy declaration: {raw.strip()}"
            )
        if logical != expected_logical:
            raise RuntimeError(
                "S3d-O8 geometry Copy/base disagreement: "
                f"{physical} -> {logical}, expected {expected_logical}"
            )
        if physical in mapping and mapping[physical] != logical:
            conflicts[physical].update((mapping[physical], logical))
        mapping[physical] = logical
    if conflicts:
        raise RuntimeError(
            "conflicting geometry Copy declarations: "
            + repr({key: sorted(values) for key, values in sorted(conflicts.items())})
        )
    if not mapping:
        raise RuntimeError(f"geometry has no Copy declarations: {path}")
    if len(mapping) != EXPECTED_GEOMETRY_COPY_DECLARATIONS:
        raise RuntimeError(
            "unexpected S3d-O8 geometry Copy count: "
            f"{len(mapping)} != {EXPECTED_GEOMETRY_COPY_DECLARATIONS}"
        )
    return mapping


def configure(
    logical_volumes: Iterable[str],
    geometry_copy_map: dict[str, str] | None = None,
) -> None:
    global LOGICAL_VOLUMES, GEOMETRY_COPY_MAP
    LOGICAL_VOLUMES = {str(value) for value in logical_volumes if str(value)}
    GEOMETRY_COPY_MAP = dict(geometry_copy_map or {})


def _alias_candidates(name: str) -> set[str]:
    candidates: set[str] = set()
    target = GEOMETRY_COPY_MAP.get(name)
    if target in LOGICAL_VOLUMES:
        candidates.add(target)
    return candidates


def canonicalize(name: str) -> str:
    value = str(name)
    if not value:
        return "Other"
    candidates: set[str] = set()
    if value in LOGICAL_VOLUMES:
        candidates.add(value)
    candidates.update(_alias_candidates(value))
    if len(candidates) > 1:
        raise RuntimeError(
            f"ambiguous S3d-O8 physical-volume mapping for {value}: {sorted(candidates)}"
        )
    if candidates:
        return next(iter(candidates))
    return value


def _open_sim(path: Path):
    return gzip.open(path, "rt", encoding="utf-8", errors="ignore")


def _dat_job(path: Path) -> str:
    suffix = ".dat.inc1.dat"
    return path.name[: -len(suffix)] if path.name.endswith(suffix) else path.stem


def _sim_job(path: Path) -> str:
    suffix = ".inc1.id1.sim.gz"
    return path.name[: -len(suffix)] if path.name.endswith(suffix) else path.stem


def audit(
    dat_files: list[Path],
    sim_files: list[Path],
    geometry_copy_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    logical = logical_volumes_from_dat(dat_files)
    configure(logical, geometry_copy_map)

    production_by_volume: dict[str, float] = defaultdict(float)
    production_by_key: dict[tuple[str, int, float], float] = defaultdict(float)
    dat_counts_by_job: dict[str, Counter[tuple[str, int, float]]] = {}
    dat_excitation_by_job: dict[
        str, dict[tuple[str, int], set[Decimal]]
    ] = {}
    for path in dat_files:
        job = _dat_job(path)
        job_counts: Counter[tuple[str, int, float]] = Counter()
        job_excitation: dict[tuple[str, int], set[Decimal]] = defaultdict(set)
        current: str | None = None
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = VN_RE.match(raw)
            if match:
                current = match.group(1)
                continue
            rmatch = RP_RE.match(raw)
            if rmatch and current is not None:
                za = int(rmatch.group(1))
                excitation_decimal = Decimal(rmatch.group(2))
                excitation = float(excitation_decimal)
                if excitation == 0.0:
                    excitation = 0.0
                production = float(rmatch.group(3))
                production_by_volume[current] += production
                production_by_key[(current, za, excitation)] += production
                job_counts[(current, za, excitation)] += production
                job_excitation[(current, za)].add(excitation_decimal)
        dat_counts_by_job[job] = job_counts
        dat_excitation_by_job[job] = job_excitation

    physical_counts: Counter[str] = Counter()
    mapped_counts: Counter[str] = Counter()
    mapped_key_counts: Counter[tuple[str, int, float]] = Counter()
    excitation_adjustments: Counter[tuple[str, str]] = Counter()
    mapping: dict[str, str] = {}
    ambiguous: list[str] = []
    excitation_match_failures: list[dict[str, Any]] = []
    sim_counts_by_job: dict[str, Counter[tuple[str, int, float]]] = {}
    for path in sim_files:
        job = _sim_job(path)
        job_counts: Counter[tuple[str, int, float]] = Counter()
        with _open_sim(path) as handle:
            for raw in handle:
                if not raw.startswith("CC IP RP "):
                    continue
                fields = raw.split()
                if len(fields) < 9:
                    continue
                physical = fields[3]
                physical_counts[physical] += 1
                try:
                    logical_name = canonicalize(physical)
                except RuntimeError as exc:
                    ambiguous.append(str(exc))
                    continue
                mapping[physical] = logical_name
                mapped_counts[logical_name] += 1
                try:
                    za = int(fields[7])
                    raw_excitation = float(fields[8])
                except ValueError:
                    continue
                try:
                    excitation = match_dat_excitation(
                        logical_name,
                        za,
                        raw_excitation,
                        dat_excitation_by_job.get(job, {}),
                    )
                except RuntimeError as exc:
                    excitation_match_failures.append(
                        {
                            "job": job,
                            "physical": physical,
                            "logical": logical_name,
                            "ZA": za,
                            "sim_raw_excitation_keV": raw_excitation,
                            "problem": str(exc),
                        }
                    )
                    continue
                mapped_key_counts[(logical_name, za, excitation)] += 1
                job_counts[(logical_name, za, excitation)] += 1
                if raw_excitation != excitation:
                    excitation_adjustments[
                        (f"{raw_excitation:.12g}", f"{excitation:.2f}")
                    ] += 1
        sim_counts_by_job[job] = job_counts

    job_set_problems: list[str] = []
    if set(dat_counts_by_job) != set(sim_counts_by_job):
        job_set_problems.append(
            "DAT/SIM job sets differ: "
            f"DAT_only={sorted(set(dat_counts_by_job) - set(sim_counts_by_job))} "
            f"SIM_only={sorted(set(sim_counts_by_job) - set(dat_counts_by_job))}"
        )
    per_job_key_mismatches: list[dict[str, Any]] = []
    for job in sorted(set(dat_counts_by_job) | set(sim_counts_by_job)):
        expected_counts = dat_counts_by_job.get(job, Counter())
        observed_counts = sim_counts_by_job.get(job, Counter())
        for key in sorted(set(expected_counts) | set(observed_counts)):
            expected = float(expected_counts.get(key, 0.0))
            observed = int(observed_counts.get(key, 0))
            if abs(expected - observed) > 1.0e-9:
                per_job_key_mismatches.append(
                    {
                        "job": job,
                        "logical": key[0],
                        "ZA": key[1],
                        "excitation_keV": key[2],
                        "dat_raw_RP": expected,
                        "sim_RPIP_points": observed,
                        "delta": observed - expected,
                    }
                )

    unmatched_physical = [
        {
            "physical": physical,
            "mapped": mapping.get(physical, physical),
            "points": count,
        }
        for physical, count in sorted(physical_counts.items())
        if mapping.get(physical, physical) not in logical
    ]
    unmatched_logical_namespace = [
        name for name in sorted(logical) if mapped_counts.get(name, 0) == 0
    ]
    missing_logical = [
        {
            "logical": name,
            "rp_raw_total": value,
            "mapped_points": mapped_counts.get(name, 0),
        }
        for name, value in sorted(production_by_volume.items())
        if value > 0.0 and mapped_counts.get(name, 0) == 0
    ]
    missing_production_keys = [
        {
            "logical": key[0],
            "ZA": key[1],
            "excitation_keV": key[2],
            "rp_raw_total": value,
            "mapped_points": mapped_key_counts.get(key, 0),
        }
        for key, value in sorted(production_by_key.items())
        if value > 0.0 and mapped_key_counts.get(key, 0) == 0
    ]
    problems: list[str] = []
    if ambiguous:
        problems.append(f"ambiguous mappings: {ambiguous[:20]}")
    problems.extend(job_set_problems)
    if excitation_match_failures:
        problems.append(
            f"unmatched or ambiguous excitation records: {len(excitation_match_failures)}"
        )
    if unmatched_physical:
        problems.append(
            f"unmatched physical volumes: {[row['physical'] for row in unmatched_physical[:20]]}"
        )
    if sum(production_by_volume.values()) > 0.0 and unmatched_logical_namespace:
        problems.append(
            "DAT logical volumes without any SIM RPIP namespace support: "
            + repr(unmatched_logical_namespace[:20])
        )
    if missing_logical:
        problems.append(
            f"positive-production logical volumes without RPIP points: {[row['logical'] for row in missing_logical[:20]]}"
        )
    if missing_production_keys:
        problems.append(
            "positive-production (VN,ZA,excitation) keys without RPIP points: "
            + repr(
                [
                    (row["logical"], row["ZA"], row["excitation_keV"])
                    for row in missing_production_keys[:20]
                ]
            )
        )
    if per_job_key_mismatches:
        problems.append(
            f"per-job DAT RP / SIM RPIP key-count mismatches: {len(per_job_key_mismatches)}"
        )
    return {
        "status": "PASS" if not problems else "FAIL",
        "dat_files": len(dat_files),
        "sim_files": len(sim_files),
        "logical_volumes": len(logical),
        "physical_volumes": len(physical_counts),
        "identity_physical_volumes": sum(
            1 for physical, logical_name in mapping.items() if physical == logical_name
        ),
        "geometry_copy_physical_volumes": sum(
            1 for physical, logical_name in mapping.items() if physical != logical_name
        ),
        "resolved_logical_targets": len(set(mapping.values())),
        "rpip_points": sum(physical_counts.values()),
        "dat_production_keys": len(production_by_key),
        "rpip_keys": len(mapped_key_counts),
        "geometry_copy_declarations": len(GEOMETRY_COPY_MAP),
        "dat_jobs": sorted(dat_counts_by_job),
        "sim_jobs": sorted(sim_counts_by_job),
        "copy_or_alias_mappings": [
            {
                "physical": physical,
                "logical": logical_name,
                "points": physical_counts[physical],
            }
            for physical, logical_name in sorted(mapping.items())
            if physical != logical_name
        ],
        "unmatched_physical": unmatched_physical,
        "unmatched_logical_namespace": unmatched_logical_namespace,
        "missing_logical": missing_logical,
        "missing_production_keys": missing_production_keys,
        "excitation_quantization_keV": float(EXCITATION_QUANTUM_KEV),
        "excitation_adjustments": [
            {
                "raw_keV": raw,
                "canonical_keV": canonical,
                "points": count,
            }
            for (raw, canonical), count in sorted(excitation_adjustments.items())
        ],
        "excitation_match_tolerance_keV": float(EXCITATION_MATCH_TOLERANCE_KEV),
        "excitation_match_failures": excitation_match_failures,
        "per_job_key_mismatches": per_job_key_mismatches,
        "ambiguous": ambiguous,
        "problems": problems,
    }
