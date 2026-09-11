#!/usr/bin/env python3
"""Build an independent, corrected-source EventList benchmark tape.

The tape is sampled directly from the hash-bound 20-bin atmospheric source
card and its corrected-keV ``IP LIN`` spectra.  Retained rich SIM files are not
used as donors.  The deterministic sampler is distribution-compatible with the
source contract, but it intentionally has its own pinned PRNG stream so its
states are an auditable benchmark input rather than an inference from a prior
transport output.
"""

from __future__ import annotations

import bisect
import hashlib
import math
import os
import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from preflight_common import (
    ROOT,
    canonical_json_bytes,
    fsync_directory,
    quarantine_directory_no_replace,
    rel,
    rename_no_replace,
    reject_lexical_symlinks,
    repo_path,
    sha256,
    sha256_bytes,
    strict_json,
    write_once,
)


SOURCE_CONTRACT = ROOT / "engineering/particle_source_unit_repair_20260811/data/source_contract_manifest.json"
TAPE_SCHEMA = Path(__file__).resolve().parents[1] / "schema/tape_root_v1.schema.json"
SOURCE_CONTRACT_SHA256 = "5424eeca35b20affb153c0e07c31a6582e575f511922bf55f40a5a0f77ab4326"
SAMPLER_ALGORITHM = "m05-independent-source-sampler-v2-splitmix64"
TAPE_MANIFEST_SCHEMA = "m05-eventlist-cell-transaction-v2"
FAR_FIELD_RADIUS_CM = 60.0
PARTICLE_TYPES = {
    "gamma": 1,
    "eplus": 2,
    "eminus": 3,
    "n": 6,
    "muplus": 8,
    "muminus": 9,
    "alpha": 21,
}
FAMILY_TOTALS = {
    "gamma": 10_000,
    "n": 2_000,
    "eplus": 500,
    "eminus": 500,
    "alpha": 100,
    "muminus": 250,
    "muplus": 250,
}
FAMILY_SHARDS = {
    "gamma": (2_500, 2_500, 2_500, 2_500),
    "n": (500, 500, 500, 500),
    "eplus": (125, 125, 125, 125),
    "eminus": (125, 125, 125, 125),
    "alpha": (25, 25, 25, 25),
    "muminus": (63, 63, 62, 62),
    "muplus": (63, 63, 62, 62),
}
# Stable order is part of seed derivation and the 28-cell plan.
CELL_COUNTS = {
    (family, mode): FAMILY_SHARDS[family]
    for family in ("gamma", "n", "eplus", "eminus", "alpha", "muminus", "muplus")
    for mode in ("instant", "buildup")
}

SIDECAR_COLUMNS = (
    "schema",
    "row_index0",
    "global_row_index0",
    "eventlist_id",
    "stable_root_id",
    "driver",
    "driver_assignment",
    "bin_index",
    "family",
    "mode",
    "source_card_path",
    "source_card_sha256",
    "source_contract_path",
    "source_contract_sha256",
    "spectrum_path",
    "spectrum_sha256",
    "sampler_algorithm",
    "sampler_seed_u64",
    "sampler_counter_start0",
    "sampler_counter_end0",
    "particle",
    "excitation_keV",
    "source_time_s",
    "global_poisson_time_s",
    "shard_global_time_offset_s",
    "x_cm",
    "y_cm",
    "z_cm",
    "dx",
    "dy",
    "dz",
    "px",
    "py",
    "pz",
    "energy_keV",
    "raw_eventlist_line_sha256",
    "expected_eventlist_binary64_sha256",
    "expected_generated_binary64_sha256",
    "expected_generated_tuple_sha256",
    "control_flag",
)


@dataclass(frozen=True)
class Driver:
    name: str
    bin_index: int
    theta_min_deg: float
    theta_max_deg: float
    flux_cm2_s: float
    spectrum_path: Path
    spectrum_sha256: str
    spectrum_x_keV: tuple[float, ...]
    spectrum_y_per_keV: tuple[float, ...]
    spectrum_cumulative: tuple[float, ...]


@dataclass(frozen=True)
class SourceModel:
    family: str
    particle: int
    source_card_path: Path
    source_card_sha256: str
    total_flux_cm2_s: float
    rate_s_inv: float
    drivers: tuple[Driver, ...]
    flux_cumulative: tuple[float, ...]


@dataclass(frozen=True)
class Primary:
    particle: int
    excitation_keV: float
    source_time_s: float
    global_poisson_time_s: float
    position_cm: tuple[float, float, float]
    direction: tuple[float, float, float]
    polarization: tuple[float, float, float]
    energy_keV: float
    driver: str
    bin_index: int
    spectrum_path: str
    spectrum_sha256: str
    sampler_counter_start0: int
    sampler_counter_end0: int


class SplitMix64:
    """Small pinned counter-addressable PRNG; never used inside transport."""

    _MASK = (1 << 64) - 1
    _GAMMA = 0x9E3779B97F4A7C15

    def __init__(self, seed: int, counter0: int = 0) -> None:
        if not 0 <= seed <= self._MASK or counter0 < 0:
            raise ValueError("invalid SplitMix64 seed/counter")
        self.seed = seed
        self.counter = counter0
        self.state = (seed + counter0 * self._GAMMA) & self._MASK

    def u01_open(self) -> float:
        self.state = (self.state + self._GAMMA) & self._MASK
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & self._MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & self._MASK
        z ^= z >> 31
        self.counter += 1
        # Exactly representable midpoint mapping: strictly inside (0, 1).
        return ((z & self._MASK) + 0.5) / float(1 << 64)


def _finite(value: str, context: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"non-finite {context}")
    return result


def validate_schema_contract() -> dict[str, Any]:
    schema = strict_json(TAPE_SCHEMA)
    if TAPE_SCHEMA.read_bytes() != canonical_json_bytes(schema):
        raise ValueError("tape root schema is not canonical JSON")
    if (
        schema.get("$id") != "urn:tes511:m05-tape-root-v2"
        or schema.get("additionalProperties") is not False
        or schema.get("type") != "object"
        or schema.get("required") != list(SIDECAR_COLUMNS)
        or schema.get("x-exact-tsv-header") != list(SIDECAR_COLUMNS)
        or set(schema.get("properties", {})) != set(SIDECAR_COLUMNS)
    ):
        raise ValueError("tape root schema/header/property closure failed")
    binary = schema.get("x-binary64-digest")
    if binary != {
        "domain_hex": b"m05-eventlist-binary64-v1\0".hex(),
        "endianness": "big",
        "format": ">i12d",
        "order": [
            "particle", "excitation_keV", "source_time_s", "x_cm", "y_cm", "z_cm",
            "dx", "dy", "dz", "px", "py", "pz", "energy_keV",
        ],
        "columns": {
            "expected_eventlist_binary64_sha256": "raw EventList direction exactly as serialized",
            "expected_generated_binary64_sha256": (
                "exact CLHEP Hep3Vector::unit() order: total=dx*dx+dy*dy+dz*dz; "
                "factor=1/sqrt(total); component*=factor; plus exact MCSource/MCRun projections: "
                "parsed=t*1e9; current=(parsed-previous)+previous; seconds=current/1e9 statefully per shard; "
                "position=(position*10)/10; energy=(energy*1e-3)/1e-3"
            ),
        },
    }:
        raise ValueError("tape binary64 digest schema drift")
    return {
        "status": "PASS",
        "schema_path": rel(TAPE_SCHEMA),
        "schema_sha256": sha256(TAPE_SCHEMA),
        "column_count": len(SIDECAR_COLUMNS),
    }


def _parse_spectrum(path: Path, expected_sha256: str) -> tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
    if sha256(path) != expected_sha256:
        raise ValueError(f"corrected spectrum hash drift: {rel(path)}")
    interpolation = 0
    points: list[tuple[float, float]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line == "IP LIN":
            interpolation += 1
            continue
        match = re.fullmatch(r"DP\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)", line)
        if match is None:
            raise ValueError(f"unsupported spectrum record in {rel(path)}: {line}")
        x = _finite(match.group(1), "spectrum energy")
        y = _finite(match.group(2), "spectrum density")
        if x <= 0.0 or y < 0.0 or (points and x <= points[-1][0]):
            raise ValueError(f"invalid IP LIN spectrum point in {rel(path)}")
        points.append((x, y))
    if interpolation != 1 or len(points) < 2:
        raise ValueError(f"{rel(path)} is not one nonempty IP LIN spectrum")
    x_values = tuple(row[0] for row in points)
    y_values = tuple(row[1] for row in points)
    cumulative = [0.0]
    for x0, x1, y0, y1 in zip(x_values, x_values[1:], y_values, y_values[1:]):
        cumulative.append(cumulative[-1] + 0.5 * (y0 + y1) * (x1 - x0))
    if not cumulative[-1] > 0.0:
        raise ValueError(f"zero spectrum integral in {rel(path)}")
    return x_values, y_values, tuple(cumulative)


def _source_card_for_family(contract: dict[str, Any], family: str) -> dict[str, Any]:
    cards = contract.get("geometries", {}).get("mass_model_511", {}).get("cards", [])
    matches = [row for row in cards if row.get("family") == family]
    if len(matches) != 1:
        raise ValueError(f"source contract has no unique Mass_model_511 card for {family}")
    return matches[0]


def load_source_model(family: str) -> SourceModel:
    if family not in PARTICLE_TYPES:
        raise ValueError(f"unsupported smoke family {family}")
    if sha256(SOURCE_CONTRACT) != SOURCE_CONTRACT_SHA256:
        raise ValueError("corrected-keV source contract hash drift")
    contract = strict_json(SOURCE_CONTRACT)
    if contract.get("farfield_radius_cm") != FAR_FIELD_RADIUS_CM or contract.get("bins_per_family") != 20:
        raise ValueError("source radius/bin contract drift")
    policies = contract.get("policies", {})
    if policies.get("additive_mono_511_allowed") is not False:
        raise ValueError("source contract no longer forbids additive mono-511")
    if contract.get("source_model", {}).get("gamma_component") != "broadband_total":
        raise ValueError("gamma source is no longer the retained broadband total")

    card_spec = _source_card_for_family(contract, family)
    source_card = repo_path(card_spec["source"])
    if sha256(source_card) != card_spec.get("source_sha256"):
        raise ValueError("corrected source-card hash drift")
    if card_spec.get("flux_entries") != 20 or card_spec.get("spectrum_references") != 20:
        raise ValueError("source-card manifest is not the exact 20-bin model")

    spectrum_manifest = {
        row["corrected_spectrum"]: row
        for row in contract.get("spectra", {}).get("files", [])
        if row.get("family") == family
    }
    if len(spectrum_manifest) != 20:
        raise ValueError("source contract does not contain exactly 20 family spectra")

    run_sources: list[str] = []
    values: dict[str, dict[str, str]] = {}
    for raw in source_card.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        run_match = re.fullmatch(rf"Background_{re.escape(family)}_fullsphere20\.Source\s+(\S+)", line)
        if run_match:
            run_sources.append(run_match.group(1))
            continue
        item_match = re.fullmatch(
            rf"(Atm_{re.escape(family)}_bin\d{{2}}_(?:down|up))\.(ParticleType|Beam|Spectrum|Flux)\s+(.+)",
            line,
        )
        if item_match:
            name, key, value = item_match.groups()
            if key in values.setdefault(name, {}):
                raise ValueError(f"duplicate {name}.{key}")
            values[name][key] = value
    if len(run_sources) != 20 or len(set(run_sources)) != 20 or set(run_sources) != set(values):
        raise ValueError("source card does not bind exactly 20 unique drivers")

    drivers: list[Driver] = []
    for name in run_sources:
        fields = values[name]
        if set(fields) != {"ParticleType", "Beam", "Spectrum", "Flux"}:
            raise ValueError(f"incomplete driver {name}")
        index_match = re.search(r"_bin(\d{2})_", name)
        if index_match is None:
            raise ValueError("driver lacks bin index")
        bin_index = int(index_match.group(1))
        if int(fields["ParticleType"]) != PARTICLE_TYPES[family]:
            raise ValueError(f"{name}: particle type drift")
        beam = re.fullmatch(
            r"FarFieldAreaSource\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)",
            fields["Beam"],
        )
        spectrum = re.fullmatch(r"File\s+(\S+)", fields["Spectrum"])
        if beam is None or spectrum is None:
            raise ValueError(f"{name}: unsupported beam/spectrum syntax")
        theta_min, theta_max, phi_min, phi_max = (_finite(beam.group(i), "beam bound") for i in range(1, 5))
        if not 0.0 <= theta_min < theta_max <= 180.0 or phi_min != 0.0 or phi_max != 360.0:
            raise ValueError(f"{name}: beam is not a full-phi valid theta interval")
        spectrum_name = spectrum.group(1)
        if spectrum_name not in spectrum_manifest or spectrum_name not in card_spec.get("spectrum_files", []):
            raise ValueError(f"{name}: spectrum is not bound by the corrected source contract")
        spectrum_record = spectrum_manifest[spectrum_name]
        spectrum_path = repo_path(spectrum_name)
        spectrum_sha = spectrum_record["corrected_sha256"]
        x_values, y_values, cumulative = _parse_spectrum(spectrum_path, spectrum_sha)
        flux = _finite(fields["Flux"], "driver flux")
        if flux <= 0.0:
            raise ValueError(f"{name}: non-positive flux")
        drivers.append(
            Driver(
                name=name,
                bin_index=bin_index,
                theta_min_deg=theta_min,
                theta_max_deg=theta_max,
                flux_cm2_s=flux,
                spectrum_path=spectrum_path,
                spectrum_sha256=spectrum_sha,
                spectrum_x_keV=x_values,
                spectrum_y_per_keV=y_values,
                spectrum_cumulative=cumulative,
            )
        )
    if [row.bin_index for row in drivers] != list(range(20)):
        raise ValueError("source drivers are not ordered bins 00 through 19")
    if any(left.theta_max_deg != right.theta_min_deg for left, right in zip(drivers, drivers[1:])):
        raise ValueError("source driver theta bins have a gap or overlap")
    if drivers[0].theta_min_deg != 0.0 or drivers[-1].theta_max_deg != 180.0:
        raise ValueError("source driver theta bins do not cover the full sphere")
    total_flux = math.fsum(driver.flux_cm2_s for driver in drivers)
    expected_flux = float(card_spec["flux_sum_cm2_s"])
    if not math.isclose(total_flux, expected_flux, rel_tol=2e-12, abs_tol=1e-15):
        raise ValueError("20-bin flux sum differs from source-contract manifest")
    flux_cumulative: list[float] = []
    running = 0.0
    for driver in drivers:
        running += driver.flux_cm2_s
        flux_cumulative.append(running)
    return SourceModel(
        family=family,
        particle=PARTICLE_TYPES[family],
        source_card_path=source_card,
        source_card_sha256=card_spec["source_sha256"],
        total_flux_cm2_s=total_flux,
        rate_s_inv=total_flux * math.pi * FAR_FIELD_RADIUS_CM**2,
        drivers=tuple(drivers),
        flux_cumulative=tuple(flux_cumulative),
    )


def _sample_energy(driver: Driver, u: float) -> float:
    target = u * driver.spectrum_cumulative[-1]
    upper = bisect.bisect_left(driver.spectrum_cumulative, target)
    if upper <= 0:
        return driver.spectrum_x_keV[0]
    if upper >= len(driver.spectrum_cumulative):
        return driver.spectrum_x_keV[-1]
    lower = upper - 1
    x0, x1 = driver.spectrum_x_keV[lower], driver.spectrum_x_keV[upper]
    y0, y1 = driver.spectrum_y_per_keV[lower], driver.spectrum_y_per_keV[upper]
    area = target - driver.spectrum_cumulative[lower]
    width = x1 - x0
    slope = (y1 - y0) / width
    if slope == 0.0:
        delta = 0.0 if y0 == 0.0 else area / y0
    else:
        discriminant = y0 * y0 + 2.0 * slope * area
        if discriminant < 0.0 and discriminant > -1e-24:
            discriminant = 0.0
        root = math.sqrt(discriminant)
        # Select the numerically stable in-bin quadratic root.
        candidates = [(-y0 + root) / slope, (-y0 - root) / slope]
        valid = [value for value in candidates if -1e-12 <= value <= width + 1e-12]
        if len(valid) != 1:
            raise ValueError("IP LIN inverse-CDF root is not unique in its interval")
        delta = min(width, max(0.0, valid[0]))
    return x0 + delta


def _sample_primary(
    model: SourceModel,
    rng: SplitMix64,
    *,
    global_time_before_s: float,
    shard_time_offset_s: float,
) -> Primary:
    counter_start = rng.counter
    interarrival_s = -math.log1p(-rng.u01_open()) / model.rate_s_inv
    global_time = global_time_before_s + interarrival_s
    driver_target = rng.u01_open() * model.total_flux_cm2_s
    driver_index = bisect.bisect_left(model.flux_cumulative, driver_target)
    driver = model.drivers[min(driver_index, len(model.drivers) - 1)]

    theta0 = math.radians(driver.theta_min_deg)
    theta1 = math.radians(driver.theta_max_deg)
    theta = math.acos(math.cos(theta0) - rng.u01_open() * (math.cos(theta0) - math.cos(theta1)))
    phi = 2.0 * math.pi * rng.u01_open()
    sky = (math.sin(theta) * math.cos(phi), math.sin(theta) * math.sin(phi), math.cos(theta))
    direction = tuple(-value for value in sky)

    disk_radius = FAR_FIELD_RADIUS_CM * math.sqrt(rng.u01_open())
    disk_phi = 2.0 * math.pi * rng.u01_open()
    x_local = disk_radius * math.cos(disk_phi)
    y_local = disk_radius * math.sin(disk_phi)
    z_local = FAR_FIELD_RADIUS_CM
    position = (
        (x_local * math.cos(theta) + z_local * math.sin(theta)) * math.cos(phi) - y_local * math.sin(phi),
        (x_local * math.cos(theta) + z_local * math.sin(theta)) * math.sin(phi) + y_local * math.cos(phi),
        -x_local * math.sin(theta) + z_local * math.cos(theta),
    )
    energy = _sample_energy(driver, rng.u01_open())
    if rng.counter - counter_start != 7:
        raise AssertionError("sampler draw-count contract drift")
    return Primary(
        particle=model.particle,
        excitation_keV=0.0,
        source_time_s=global_time - shard_time_offset_s,
        global_poisson_time_s=global_time,
        position_cm=position,
        direction=direction,
        polarization=(0.0, 0.0, 0.0),
        energy_keV=energy,
        driver=driver.name,
        bin_index=driver.bin_index,
        spectrum_path=rel(driver.spectrum_path),
        spectrum_sha256=driver.spectrum_sha256,
        sampler_counter_start0=counter_start,
        sampler_counter_end0=rng.counter,
    )


def _normalized(direction: tuple[float, float, float]) -> tuple[float, float, float]:
    # Exact CLHEP Hep3Vector::unit() operation order used by
    # G4ParticleGun::SetParticleMomentumDirection: ordinary left-associated
    # products/sums, one sqrt, one reciprocal, then component*factor.
    total = direction[0] * direction[0] + direction[1] * direction[1] + direction[2] * direction[2]
    if not total > 0.0:
        raise ValueError("zero direction")
    factor = 1.0 / math.sqrt(total)
    return tuple(component * factor for component in direction)


def quantized_generated_tuple(primary: Primary, local_time_s: float | None = None) -> list[int]:
    direction = _normalized(primary.direction)
    time_s = primary.source_time_s if local_time_s is None else local_time_s

    def llround(value: float) -> int:
        return math.floor(value + 0.5) if value >= 0.0 else math.ceil(value - 0.5)

    return [
        primary.particle,
        llround(primary.excitation_keV * 10**6),
        llround(time_s * 10**12),
        *(llround(value * 10**6) for value in primary.position_cm),
        *(llround(value * 10**9) for value in direction),
        *(llround(value * 10**9) for value in primary.polarization),
        llround(primary.energy_keV * 10**6),
    ]


def generated_tuple_hash(primary: Primary, local_time_s: float | None = None) -> str:
    return sha256_bytes(canonical_json_bytes(quantized_generated_tuple(primary, local_time_s)))


def _binary64_hash(primary: Primary, direction: tuple[float, float, float]) -> str:
    values = (
        primary.excitation_keV,
        primary.source_time_s,
        *primary.position_cm,
        *direction,
        *primary.polarization,
        primary.energy_keV,
    )
    if len(values) != 12 or any(not math.isfinite(value) for value in values):
        raise ValueError("non-finite/wrong-length EventList binary64 tuple")
    payload = b"m05-eventlist-binary64-v1\0" + struct.pack(">i12d", primary.particle, *values)
    return sha256_bytes(payload)


def eventlist_binary64_hash(primary: Primary) -> str:
    """Hash the exact parsed EventList tuple, retaining its raw direction bits."""

    return _binary64_hash(primary, primary.direction)


def runtime_source_time_projection(
    raw_source_time_s: float, previous_runtime_internal_time: float = 0.0,
) -> tuple[float, float]:
    """Reproduce MCSource/MCRun's stateful EventList time arithmetic.

    The parsed row time is first multiplied by CLHEP ``second``.  For every
    row after the first, ``CalculateNextEmission`` subtracts the retained
    previous internal ``m_SimulatedTime`` and adds it back.  Cancellation can
    change a handful of rows by one or two ULP, so an independent per-row unit
    round trip is not equivalent.
    """

    parsed_internal_time = raw_source_time_s * 1.0e9
    delta_internal_time = parsed_internal_time - previous_runtime_internal_time
    current_internal_time = delta_internal_time + previous_runtime_internal_time
    return current_internal_time / 1.0e9, current_internal_time


def runtime_projected_primary(
    primary: Primary, *, runtime_source_time_s: float | None = None,
) -> Primary:
    """Return the exact installed-runtime post-GPS binary64 projection."""

    return Primary(
        particle=primary.particle,
        excitation_keV=primary.excitation_keV,
        source_time_s=(
            runtime_source_time_projection(primary.source_time_s)[0]
            if runtime_source_time_s is None else runtime_source_time_s
        ),
        global_poisson_time_s=primary.global_poisson_time_s,
        position_cm=tuple((value * 10.0) / 10.0 for value in primary.position_cm),
        direction=_normalized(primary.direction),
        polarization=primary.polarization,
        energy_keV=(primary.energy_keV * 1.0e-3) / 1.0e-3,
        driver=primary.driver,
        bin_index=primary.bin_index,
        spectrum_path=primary.spectrum_path,
        spectrum_sha256=primary.spectrum_sha256,
        sampler_counter_start0=primary.sampler_counter_start0,
        sampler_counter_end0=primary.sampler_counter_end0,
    )


def generated_binary64_hash(primary: Primary, *, runtime_source_time_s: float | None = None) -> str:
    """Hash the exact installed-runtime post-GPS tuple projection.

    MCSource parses position, time, and energy by multiplying the textual
    values by CLHEP units.  The observer/scorer reports those values after the
    inverse unit division.  Those two binary64 operations are not generally an
    identity.  Direction is transformed once by ``Hep3Vector::unit()`` in
    ``G4SPSAngDistribution::SetParticleMomentumDirection``.  Modeling all four
    boundaries is required for bit-exact comparison with the newly added
    ``G4PrimaryVertex``/``G4PrimaryParticle`` and ``MCRun::GetSimulatedTime``.
    """
    runtime = runtime_projected_primary(primary, runtime_source_time_s=runtime_source_time_s)
    return _binary64_hash(runtime, runtime.direction)


def _eventlist_line(primary: Primary, eventlist_id: int) -> str:
    fields = [
        str(eventlist_id),
        "0",
        str(primary.particle),
        format(primary.excitation_keV, ".17g"),
        format(primary.source_time_s, ".17g"),
        *(format(value, ".17g") for value in primary.position_cm),
        *(format(value, ".17g") for value in primary.direction),
        *(format(value, ".17g") for value in primary.polarization),
        format(primary.energy_keV, ".17g"),
    ]
    if len(fields) != 15:
        raise AssertionError("EventList row is not 15 fields")
    return " ".join(fields)


def _cell_seed(family: str, mode: str) -> int:
    payload = f"{SAMPLER_ALGORITHM}|{SOURCE_CONTRACT_SHA256}|{family}|{mode}"
    return int.from_bytes(hashlib.sha256(payload.encode("utf-8")).digest()[:8], "big")


def _root_payload(
    *,
    row: dict[str, str],
    raw_line_sha256: str,
    eventlist_binary64_sha256: str,
    generated_binary64_sha256: str,
    tuple_sha256: str,
) -> dict[str, Any]:
    return {
        "schema": "m05-tape-root-v2",
        "sampler_algorithm": row["sampler_algorithm"],
        "sampler_seed_u64": int(row["sampler_seed_u64"]),
        "sampler_counter_start0": int(row["sampler_counter_start0"]),
        "sampler_counter_end0": int(row["sampler_counter_end0"]),
        "family": row["family"],
        "mode": row["mode"],
        "global_row_index0": int(row["global_row_index0"]),
        "driver": row["driver"],
        "bin_index": int(row["bin_index"]),
        "source_card_sha256": row["source_card_sha256"],
        "source_contract_sha256": row["source_contract_sha256"],
        "spectrum_sha256": row["spectrum_sha256"],
        "raw_eventlist_line_sha256": raw_line_sha256,
        "expected_eventlist_binary64_sha256": eventlist_binary64_sha256,
        "expected_generated_binary64_sha256": generated_binary64_sha256,
        "expected_generated_tuple_sha256": tuple_sha256,
    }


def _primary_row(
    primary: Primary,
    *,
    model: SourceModel,
    family: str,
    mode: str,
    seed: int,
    row_index0: int,
    global_row_index0: int,
    shard_offset_s: float,
    raw_line_sha256: str,
    eventlist_binary64_sha256: str,
    generated_binary64_sha256: str,
    tuple_sha256: str,
) -> dict[str, str]:
    row = {
        "schema": "m05-tape-root-v2",
        "row_index0": str(row_index0),
        "global_row_index0": str(global_row_index0),
        "eventlist_id": str(row_index0 + 1),
        "stable_root_id": "",
        "driver": primary.driver,
        "driver_assignment": "sampled_exact_not_inferred",
        "bin_index": str(primary.bin_index),
        "family": family,
        "mode": mode,
        "source_card_path": rel(model.source_card_path),
        "source_card_sha256": model.source_card_sha256,
        "source_contract_path": rel(SOURCE_CONTRACT),
        "source_contract_sha256": SOURCE_CONTRACT_SHA256,
        "spectrum_path": primary.spectrum_path,
        "spectrum_sha256": primary.spectrum_sha256,
        "sampler_algorithm": SAMPLER_ALGORITHM,
        "sampler_seed_u64": str(seed),
        "sampler_counter_start0": str(primary.sampler_counter_start0),
        "sampler_counter_end0": str(primary.sampler_counter_end0),
        "particle": str(primary.particle),
        "excitation_keV": format(primary.excitation_keV, ".17g"),
        "source_time_s": format(primary.source_time_s, ".17g"),
        "global_poisson_time_s": format(primary.global_poisson_time_s, ".17g"),
        "shard_global_time_offset_s": format(shard_offset_s, ".17g"),
        "x_cm": format(primary.position_cm[0], ".17g"),
        "y_cm": format(primary.position_cm[1], ".17g"),
        "z_cm": format(primary.position_cm[2], ".17g"),
        "dx": format(primary.direction[0], ".17g"),
        "dy": format(primary.direction[1], ".17g"),
        "dz": format(primary.direction[2], ".17g"),
        "px": format(primary.polarization[0], ".17g"),
        "py": format(primary.polarization[1], ".17g"),
        "pz": format(primary.polarization[2], ".17g"),
        "energy_keV": format(primary.energy_keV, ".17g"),
        "raw_eventlist_line_sha256": raw_line_sha256,
        "expected_eventlist_binary64_sha256": eventlist_binary64_sha256,
        "expected_generated_binary64_sha256": generated_binary64_sha256,
        "expected_generated_tuple_sha256": tuple_sha256,
        "control_flag": "",
    }
    row["stable_root_id"] = sha256_bytes(canonical_json_bytes(_root_payload(
        row=row,
        raw_line_sha256=raw_line_sha256,
        eventlist_binary64_sha256=eventlist_binary64_sha256,
        generated_binary64_sha256=generated_binary64_sha256,
        tuple_sha256=tuple_sha256,
    )))
    # Pre-register three outcome-independent controls in every subshard; extra
    # approximately-one-percent controls are stable-root selected.  Whether a
    # control is TES-zero is known only after transport and is a post-run gate.
    row["control_flag"] = "1" if row_index0 < 3 or int(row["stable_root_id"][:16], 16) % 100 == 0 else "0"
    return row


def _source_time_contract() -> dict[str, str]:
    return {
        "clock_scope": "independent_per_family_mode_cell",
        "within_cell": (
            "source_time_s/global_poisson_time_s represent exposure only inside one family×mode cell; "
            "the cell clock is a combined Poisson process over that family's 20 angular drivers"
        ),
        "cross_family_prohibition": (
            "timestamps from the seven independently sampled family clocks are not one globally coupled timeline "
            "and must never be concatenated or compared as such"
        ),
        "cross_family_accidental_live": (
            "M05 cross-family accidental/live studies must regenerate or merge arrivals using the normalized "
            "per-family rates before applying coincidence or live-time logic"
        ),
    }


def _precision_contract() -> dict[str, Any]:
    return {
        "eventlist_ascii": "all binary64 state fields serialized with C/Python .17g round-trip precision",
        "raw_line_identity": "SHA-256 over the exact EventList line bytes excluding newline",
        "eventlist_binary64_identity": (
            "SHA-256 of domain tag m05-eventlist-binary64-v1\\0, particle int32 big-endian, then "
            "12 big-endian IEEE-754 binary64 values: excitation,time,pos3,raw_direction3,polarization3,energy"
        ),
        "generated_binary64_identity": (
            "same binary64 domain/order as EventList identity, after exact installed runtime projection: "
            "CLHEP Hep3Vector::unit() once for direction; MCSource/MCRun time is stateful per shard as "
            "parsed=t*1e9 then current=(parsed-previous)+previous then seconds=current/1e9; "
            "position=(position*10)/10, and energy=(energy*1e-3)/1e-3 binary64 unit round trips; "
            "excitation and polarization retain their parsed bits"
        ),
        "expected_generated_tuple_hash": (
            "integer canonical comparison tuple: excitation/E/position 1e-6, time 1e-12, "
            "direction/polarization 1e-9; C++ llround halfway-away-from-zero; semantics unchanged"
        ),
        "arm_specific_post_run_closure": {
            "F_U": (
                "planned installed-Cosima MCRun GeneratePrimaries LD_PRELOAD observer records actual post-GPS "
                "primary binary64 fields and actual MCRun simulated time; observer artifacts alone are explicitly "
                "not a job PASS and require the outer transaction validator"
            ),
            "C_N1": (
                "generated_observations binds the normalized post-GPS binary64 generated state and separately "
                "binds the serialized IA INIT state"
            ),
        },
        "serialized_ia_contract": (
            "IA INIT is an independently serialized 17-significant-digit record; compare particle exactly, "
            "position/energy abs<=1e-6 and rel<=1e-9, direction/polarization abs<=1e-9, and require one INIT"
        ),
        "F_U_observation_status": "PLANNED__COMPILE_ONLY_PRELOAD_OBSERVER__NOT_TRANSPORT_VALIDATED",
    }


def build_cell_tapes(family: str, mode: str, output_root: Path) -> dict[str, Any]:
    if (family, mode) not in CELL_COUNTS:
        raise ValueError(f"unknown smoke cell {family}/{mode}")
    counts = CELL_COUNTS[(family, mode)]
    if len(counts) != 4 or sum(counts) != FAMILY_TOTALS[family]:
        raise AssertionError("four-shard cell-count contract drift")
    model = load_source_model(family)
    seed = _cell_seed(family, mode)
    rng = SplitMix64(seed)
    output_root.mkdir(parents=True, exist_ok=True)
    cell_dir = output_root / f"{family}_{mode}"
    partial_dir = output_root / f".{family}_{mode}.partial.{os.getpid()}"
    reject_lexical_symlinks(output_root, stop=Path(output_root.absolute().anchor))
    if cell_dir.exists() or partial_dir.exists():
        raise FileExistsError(f"tape transaction target/partial already exists: {cell_dir} / {partial_dir}")
    partial_dir.mkdir(exist_ok=False)
    fsync_directory(output_root)
    global_time = 0.0
    global_index0 = 0
    shard_records: list[dict[str, Any]] = []
    for shard_index, count in enumerate(counts):
        shard_offset = global_time
        previous_runtime_internal_time = 0.0
        tape_lines: list[str] = []
        sidecar_lines = ["\t".join(SIDECAR_COLUMNS)]
        for row_index0 in range(count):
            primary = _sample_primary(
                model,
                rng,
                global_time_before_s=global_time,
                shard_time_offset_s=shard_offset,
            )
            global_time = primary.global_poisson_time_s
            line = _eventlist_line(primary, row_index0 + 1)
            line_sha = sha256_bytes(line.encode("utf-8"))
            eventlist_binary64_sha = eventlist_binary64_hash(primary)
            runtime_source_time_s, previous_runtime_internal_time = runtime_source_time_projection(
                primary.source_time_s, previous_runtime_internal_time
            )
            generated_binary64_sha = generated_binary64_hash(
                primary, runtime_source_time_s=runtime_source_time_s
            )
            tuple_sha = generated_tuple_hash(primary)
            row = _primary_row(
                primary,
                model=model,
                family=family,
                mode=mode,
                seed=seed,
                row_index0=row_index0,
                global_row_index0=global_index0,
                shard_offset_s=shard_offset,
                raw_line_sha256=line_sha,
                eventlist_binary64_sha256=eventlist_binary64_sha,
                generated_binary64_sha256=generated_binary64_sha,
                tuple_sha256=tuple_sha,
            )
            if any("\t" in value or "\n" in value for value in row.values()):
                raise ValueError("tab/newline in sidecar value")
            tape_lines.append(line)
            sidecar_lines.append("\t".join(row[column] for column in SIDECAR_COLUMNS))
            global_index0 += 1
        tape_path = partial_dir / f"shard{shard_index:04d}.eventlist"
        sidecar_path = partial_dir / f"shard{shard_index:04d}.roots.tsv"
        write_once(tape_path, ("\n".join(tape_lines) + "\n").encode("utf-8"))
        write_once(sidecar_path, ("\n".join(sidecar_lines) + "\n").encode("utf-8"))
        checked = validate_sidecar(tape_path, sidecar_path, verify_authorities=True, verify_sampler=True)
        if checked["event_count"] != count:
            raise ValueError("post-write tape validation count mismatch")
        shard_records.append(
            {
                "event_count": count,
                "shard_index": shard_index,
                "tape_path": rel(cell_dir / tape_path.name),
                "tape_sha256": sha256(tape_path),
                "tape_size_bytes": tape_path.stat().st_size,
                "root_sidecar_path": rel(cell_dir / sidecar_path.name),
                "root_sidecar_sha256": sha256(sidecar_path),
                "root_sidecar_size_bytes": sidecar_path.stat().st_size,
                "source_global_row_start0": global_index0 - count,
                "source_global_row_end0": global_index0 - 1,
                "sampler_counter_start0": (global_index0 - count) * 7,
                "sampler_counter_end0": global_index0 * 7,
                "shard_global_time_offset_s": shard_offset,
                "local_last_time_s": global_time - shard_offset,
                "global_last_time_s": global_time,
                "pre_registered_outcome_independent_control_count": checked[
                    "pre_registered_outcome_independent_control_count"
                ],
            }
        )
    if global_index0 != sum(counts) or rng.counter != 7 * global_index0:
        raise ValueError("cell sampler count/counter closure failed")
    driver_bindings = [
        {
            "driver": driver.name,
            "bin_index": driver.bin_index,
            "theta_min_deg": driver.theta_min_deg,
            "theta_max_deg": driver.theta_max_deg,
            "flux_cm2_s": driver.flux_cm2_s,
            "spectrum_path": rel(driver.spectrum_path),
            "spectrum_sha256": driver.spectrum_sha256,
            "spectrum_point_count": len(driver.spectrum_x_keV),
        }
        for driver in model.drivers
    ]
    result = {
        "cell": f"{family}_{mode}",
        "family": family,
        "mode": mode,
        "events": global_index0,
        "particle_type": model.particle,
        "sampler_algorithm": SAMPLER_ALGORITHM,
        "sampler_seed_u64": seed,
        "uniform_draws_per_primary": 7,
        "source_contract_path": rel(SOURCE_CONTRACT),
        "source_contract_sha256": SOURCE_CONTRACT_SHA256,
        "source_card_path": rel(model.source_card_path),
        "source_card_sha256": model.source_card_sha256,
        "driver_assignment": (
            "exact benchmark driver sampled before transport from the bound corrected source; "
            "not an inferred donor-SIM driver and not an original atmospheric-source event ID"
        ),
        "stable_root_identity_scope": (
            "ordered benchmark identity derived from sampler/source/tape fields; never an original atmospheric-source ID"
        ),
        "driver_bindings": driver_bindings,
        "original_flux_cm2_s": model.total_flux_cm2_s,
        "poisson_rate_s_inv": model.rate_s_inv,
        "source_time_semantics": _source_time_contract(),
        "angular_sampling": "uniform solid angle inside the exact selected full-phi FarFieldAreaSource theta bin",
        "position_sampling": "uniform projected disk of radius 60 cm, rotated by selected sky direction as in FarFieldAreaSource",
        "energy_sampling": "analytic inverse CDF of the hash-bound corrected-keV IP LIN spectrum",
        "gamma_component_policy": "retained broadband total including annihilation bump; additive mono-511 forbidden",
        "donor_transport_dependency": False,
        "precision_contract": _precision_contract(),
        "shards": shard_records,
    }
    manifest = {
        "schema_version": TAPE_MANIFEST_SCHEMA,
        "status": "PASS__TAPE_SIDECAR_TRANSACTION_COMMITTED__NO_TRANSPORT",
        "transport_events_launched": 0,
        "family": family,
        "mode": mode,
        "particle_type": model.particle,
        "event_count": global_index0,
        "shard_count": len(shard_records),
        "sidecar_columns": list(SIDECAR_COLUMNS),
        "sidecar_header_sha256": sha256_bytes(("\t".join(SIDECAR_COLUMNS) + "\n").encode("utf-8")),
        "source_contract_path": rel(SOURCE_CONTRACT),
        "source_contract_sha256": SOURCE_CONTRACT_SHA256,
        "source_card_path": rel(model.source_card_path),
        "source_card_sha256": model.source_card_sha256,
        "all_20_driver_spectrum_flux_bindings": driver_bindings,
        "sampler_algorithm": SAMPLER_ALGORITHM,
        "sampler_seed_u64": seed,
        "source_time_semantics": result["source_time_semantics"],
        "precision_contract": result["precision_contract"],
        "stable_root_identity_scope": result["stable_root_identity_scope"],
        "shards": [
            {
                key: value
                for key, value in shard.items()
                if key not in {"tape_path", "root_sidecar_path"}
            }
            | {
                "tape_file": Path(shard["tape_path"]).name,
                "root_sidecar_file": Path(shard["root_sidecar_path"]).name,
            }
            for shard in shard_records
        ],
    }
    manifest_path = partial_dir / "cell_manifest.json"
    # Commit marker is written last inside a quarantined directory.  Publication
    # is one directory rename, so no tape/sidecar pair is authoritative without
    # its canonical manifest.
    write_once(manifest_path, canonical_json_bytes(manifest))
    validate_cell_manifest(partial_dir, expected_final_dir=cell_dir)
    fsync_directory(partial_dir)
    result["cell_manifest_path"] = rel(cell_dir / "cell_manifest.json")
    result["cell_manifest_sha256"] = sha256(manifest_path)
    result["transaction_publication"] = (
        "single-directory-renameat2-RENAME_NOREPLACE; canonical cell_manifest.json is commit marker"
    )
    published = False
    try:
        rename_no_replace(partial_dir, cell_dir)
        published = True
        fsync_directory(output_root)
    except BaseException as original:
        # A namespace collision leaves ``published`` false and the unrelated
        # target untouched.  A durability failure after publication moves our
        # own cell out of the authoritative name before propagating the
        # original exception.
        if published:
            try:
                quarantine_directory_no_replace(cell_dir)
            except BaseException as cleanup:
                raise original from cleanup
        raise
    return result


def validate_cell_manifest(cell_dir: Path, *, expected_final_dir: Path | None = None) -> dict[str, Any]:
    """Validate only manifest-named tape artifacts; never discover by globbing."""

    reject_lexical_symlinks(cell_dir, stop=Path(cell_dir.absolute().anchor))
    manifest_path = cell_dir / "cell_manifest.json"
    manifest = strict_json(manifest_path)
    if manifest_path.read_bytes() != canonical_json_bytes(manifest):
        raise ValueError("tape cell manifest is not canonical JSON")
    if (
        manifest.get("schema_version") != TAPE_MANIFEST_SCHEMA
        or manifest.get("status") != "PASS__TAPE_SIDECAR_TRANSACTION_COMMITTED__NO_TRANSPORT"
        or manifest.get("transport_events_launched") != 0
        or manifest.get("shard_count") != 4
        or manifest.get("sidecar_columns") != list(SIDECAR_COLUMNS)
        or manifest.get("sidecar_header_sha256")
        != sha256_bytes(("\t".join(SIDECAR_COLUMNS) + "\n").encode("utf-8"))
        or manifest.get("source_time_semantics") != _source_time_contract()
        or manifest.get("precision_contract") != _precision_contract()
    ):
        raise ValueError("tape cell transaction manifest contract drift")
    family, mode = manifest.get("family"), manifest.get("mode")
    if (family, mode) not in CELL_COUNTS or manifest.get("particle_type") != PARTICLE_TYPES[family]:
        raise ValueError("tape cell manifest family/mode/particle drift")
    model = load_source_model(family)
    bindings = manifest.get("all_20_driver_spectrum_flux_bindings")
    expected_bindings = [
        {
            "driver": driver.name,
            "bin_index": driver.bin_index,
            "theta_min_deg": driver.theta_min_deg,
            "theta_max_deg": driver.theta_max_deg,
            "flux_cm2_s": driver.flux_cm2_s,
            "spectrum_path": rel(driver.spectrum_path),
            "spectrum_sha256": driver.spectrum_sha256,
            "spectrum_point_count": len(driver.spectrum_x_keV),
        }
        for driver in model.drivers
    ]
    if (
        bindings != expected_bindings
        or len(bindings) != 20
        or manifest.get("source_contract_sha256") != SOURCE_CONTRACT_SHA256
        or manifest.get("source_card_sha256") != model.source_card_sha256
        or manifest.get("sampler_seed_u64") != _cell_seed(family, mode)
    ):
        raise ValueError("tape cell source/20-driver binding drift")
    rows_seen = 0
    roots_seen: set[str] = set()
    global_times: list[float] = []
    for shard_index, shard in enumerate(manifest.get("shards", [])):
        if shard.get("shard_index") != shard_index:
            raise ValueError("tape transaction shard order drift")
        tape_name = shard.get("tape_file")
        roots_name = shard.get("root_sidecar_file")
        if (
            not isinstance(tape_name, str)
            or not isinstance(roots_name, str)
            or Path(tape_name).name != tape_name
            or Path(roots_name).name != roots_name
        ):
            raise ValueError("tape manifest artifact name is not a basename")
        tape = cell_dir / tape_name
        sidecar = cell_dir / roots_name
        if (
            sha256(tape) != shard.get("tape_sha256")
            or tape.stat().st_size != shard.get("tape_size_bytes")
            or sha256(sidecar) != shard.get("root_sidecar_sha256")
            or sidecar.stat().st_size != shard.get("root_sidecar_size_bytes")
        ):
            raise ValueError("tape transaction artifact digest/size drift")
        checked = validate_sidecar(tape, sidecar, verify_authorities=True, verify_sampler=True)
        if checked["event_count"] != shard.get("event_count"):
            raise ValueError("tape transaction row-count drift")
        rows = _parse_rows(sidecar)
        if int(rows[0]["global_row_index0"]) != rows_seen:
            raise ValueError("cell-wide tape global-row continuity failed")
        for row in rows:
            root = row["stable_root_id"]
            global_time = _finite(row["global_poisson_time_s"], "global Poisson time")
            if root in roots_seen or (global_times and global_time <= global_times[-1]):
                raise ValueError("cell-wide duplicate root/TI or nonmonotone global time")
            roots_seen.add(root)
            global_times.append(global_time)
        rows_seen += len(rows)
    if rows_seen != manifest.get("event_count") or rows_seen != sum(CELL_COUNTS[(family, mode)]):
        raise ValueError("tape cell manifest total row-count drift")
    # During pre-publication validation the manifest names the final authority
    # directory, while bytes still live in the quarantined directory.
    authority_dir = expected_final_dir or cell_dir
    return {
        "status": "PASS",
        "authority_directory": str(authority_dir),
        "event_count": rows_seen,
        "shard_count": 4,
        "unique_root_count": len(roots_seen),
        "all_20_spectra_and_fluxes_bound": True,
        "source_time_semantics": _source_time_contract(),
    }


def _parse_rows(sidecar: Path) -> list[dict[str, str]]:
    lines = sidecar.read_text(encoding="utf-8").splitlines()
    if not lines or tuple(lines[0].split("\t")) != SIDECAR_COLUMNS:
        raise ValueError("wrong root sidecar schema/header")
    rows: list[dict[str, str]] = []
    for line in lines[1:]:
        fields = line.split("\t")
        if len(fields) != len(SIDECAR_COLUMNS):
            raise ValueError("root sidecar row has wrong field count")
        rows.append(dict(zip(SIDECAR_COLUMNS, fields, strict=True)))
    return rows


def _primary_from_row(row: dict[str, str]) -> Primary:
    return Primary(
        particle=int(row["particle"]),
        excitation_keV=_finite(row["excitation_keV"], "excitation"),
        source_time_s=_finite(row["source_time_s"], "source time"),
        global_poisson_time_s=_finite(row["global_poisson_time_s"], "global source time"),
        position_cm=tuple(_finite(row[name], name) for name in ("x_cm", "y_cm", "z_cm")),
        direction=tuple(_finite(row[name], name) for name in ("dx", "dy", "dz")),
        polarization=tuple(_finite(row[name], name) for name in ("px", "py", "pz")),
        energy_keV=_finite(row["energy_keV"], "energy"),
        driver=row["driver"],
        bin_index=int(row["bin_index"]),
        spectrum_path=row["spectrum_path"],
        spectrum_sha256=row["spectrum_sha256"],
        sampler_counter_start0=int(row["sampler_counter_start0"]),
        sampler_counter_end0=int(row["sampler_counter_end0"]),
    )


def validate_sidecar(
    tape: Path,
    sidecar: Path,
    *,
    verify_authorities: bool = True,
    verify_sampler: bool = True,
) -> dict[str, Any]:
    validate_schema_contract()
    tape_lines = tape.read_text(encoding="utf-8").splitlines()
    rows = _parse_rows(sidecar)
    if not rows or len(rows) != len(tape_lines):
        raise ValueError("tape/sidecar row count mismatch")
    family, mode = rows[0]["family"], rows[0]["mode"]
    if (family, mode) not in CELL_COUNTS or any(row["family"] != family or row["mode"] != mode for row in rows):
        raise ValueError("sidecar cell identity mismatch")
    model = load_source_model(family) if verify_authorities or verify_sampler else None
    seed = int(rows[0]["sampler_seed_u64"])
    offset = _finite(rows[0]["shard_global_time_offset_s"], "shard offset")
    first_global_index = int(rows[0]["global_row_index0"])
    if seed != _cell_seed(family, mode) and verify_sampler:
        raise ValueError("sidecar sampler seed derivation mismatch")
    previous_local = 0.0
    previous_global = offset
    previous_runtime_internal_time = 0.0
    stable_ids: set[str] = set()
    for index, (line, row) in enumerate(zip(tape_lines, rows, strict=True)):
        if row["schema"] != "m05-tape-root-v2" or row["driver_assignment"] != "sampled_exact_not_inferred":
            raise ValueError("wrong sidecar schema/driver semantics")
        if row["sampler_algorithm"] != SAMPLER_ALGORITHM:
            raise ValueError("sampler algorithm drift")
        if int(row["row_index0"]) != index or int(row["eventlist_id"]) != index + 1:
            raise ValueError("sidecar row/eventlist ID order mismatch")
        if int(row["global_row_index0"]) != first_global_index + index:
            raise ValueError("sidecar global row order is not contiguous")
        if int(row["sampler_seed_u64"]) != seed or _finite(row["shard_global_time_offset_s"], "offset") != offset:
            raise ValueError("sidecar shard sampler identity is not constant")
        expected_counter = 7 * int(row["global_row_index0"])
        if int(row["sampler_counter_start0"]) != expected_counter or int(row["sampler_counter_end0"]) != expected_counter + 7:
            raise ValueError("sidecar sampler counter is not exact/contiguous")
        fields = line.split()
        if len(fields) != 15 or fields[1] != "0":
            raise ValueError("tape row is not one non-successor primary")
        if int(fields[0]) != index + 1:
            raise ValueError("raw EventList ID order mismatch")
        line_sha = sha256_bytes(line.encode("utf-8"))
        if row["raw_eventlist_line_sha256"] != line_sha:
            raise ValueError("raw tape line hash mismatch")
        primary = _primary_from_row(row)
        numeric_pairs = (
            (fields[2], row["particle"]), (fields[3], row["excitation_keV"]),
            (fields[4], row["source_time_s"]), (fields[5], row["x_cm"]),
            (fields[6], row["y_cm"]), (fields[7], row["z_cm"]),
            (fields[8], row["dx"]), (fields[9], row["dy"]), (fields[10], row["dz"]),
            (fields[11], row["px"]), (fields[12], row["py"]), (fields[13], row["pz"]),
            (fields[14], row["energy_keV"]),
        )
        if any(_finite(left, "tape numeric") != _finite(right, "sidecar numeric") for left, right in numeric_pairs):
            raise ValueError("tape/sidecar primary tuple mismatch")
        tuple_sha = generated_tuple_hash(primary)
        eventlist_binary64_sha = eventlist_binary64_hash(primary)
        runtime_source_time_s, previous_runtime_internal_time = runtime_source_time_projection(
            primary.source_time_s, previous_runtime_internal_time
        )
        generated_binary64_sha = generated_binary64_hash(
            primary, runtime_source_time_s=runtime_source_time_s
        )
        if row["expected_eventlist_binary64_sha256"] != eventlist_binary64_sha:
            raise ValueError("exact EventList binary64 tuple hash mismatch")
        if row["expected_generated_binary64_sha256"] != generated_binary64_sha:
            raise ValueError("normalized generated binary64 tuple hash mismatch")
        if row["expected_generated_tuple_sha256"] != tuple_sha:
            raise ValueError("expected generated tuple hash mismatch")
        for digest_name in (
            "stable_root_id", "source_card_sha256", "source_contract_sha256", "spectrum_sha256",
            "raw_eventlist_line_sha256", "expected_eventlist_binary64_sha256",
            "expected_generated_binary64_sha256", "expected_generated_tuple_sha256",
        ):
            if re.fullmatch(r"[0-9a-f]{64}", row[digest_name]) is None:
                raise ValueError(f"invalid {digest_name}")
        expected_root = sha256_bytes(canonical_json_bytes(_root_payload(
            row=row,
            raw_line_sha256=line_sha,
            eventlist_binary64_sha256=eventlist_binary64_sha,
            generated_binary64_sha256=generated_binary64_sha,
            tuple_sha256=tuple_sha,
        )))
        if row["stable_root_id"] != expected_root or expected_root in stable_ids:
            raise ValueError("stable root ID mismatch or duplicate")
        stable_ids.add(expected_root)
        expected_control = index < 3 or int(expected_root[:16], 16) % 100 == 0
        if row["control_flag"] not in {"0", "1"} or (row["control_flag"] == "1") != expected_control:
            raise ValueError("pre-registered control predicate mismatch")
        if primary.particle != PARTICLE_TYPES[family] or primary.excitation_keV != 0.0 or primary.energy_keV <= 0.0:
            raise ValueError("particle/energy contract mismatch")
        if primary.source_time_s <= previous_local or primary.global_poisson_time_s <= previous_global:
            raise ValueError("source time is not strictly increasing")
        if primary.global_poisson_time_s - offset != primary.source_time_s:
            raise ValueError("shard-local/global Poisson time closure failed")
        previous_local, previous_global = primary.source_time_s, primary.global_poisson_time_s
        direction = _normalized(primary.direction)
        if max(abs(left - right) for left, right in zip(direction, primary.direction, strict=True)) > 2e-15:
            raise ValueError("serialized direction is not unit length")
        sky = tuple(-value for value in direction)
        plane_distance = math.fsum(position * axis for position, axis in zip(primary.position_cm, sky, strict=True))
        tangential2 = math.fsum(value * value for value in primary.position_cm) - plane_distance * plane_distance
        if not math.isclose(plane_distance, FAR_FIELD_RADIUS_CM, rel_tol=0.0, abs_tol=2e-12):
            raise ValueError("far-field start position is off the projected plane")
        if tangential2 < -1e-9 or tangential2 > FAR_FIELD_RADIUS_CM**2 + 1e-8:
            raise ValueError("far-field start position is outside projected disk")
        if model is not None:
            driver = model.drivers[primary.bin_index]
            if primary.driver != driver.name or primary.spectrum_path != rel(driver.spectrum_path):
                raise ValueError("exact sampled driver/spectrum identity mismatch")
            if primary.spectrum_sha256 != driver.spectrum_sha256:
                raise ValueError("sampled spectrum hash mismatch")
            theta = math.degrees(math.acos(max(-1.0, min(1.0, sky[2]))))
            if not driver.theta_min_deg - 2e-12 <= theta <= driver.theta_max_deg + 2e-12:
                raise ValueError("sampled direction lies outside exact driver bin")
            if row["source_card_path"] != rel(model.source_card_path) or row["source_card_sha256"] != model.source_card_sha256:
                raise ValueError("source-card identity mismatch")
            if row["source_contract_path"] != rel(SOURCE_CONTRACT) or row["source_contract_sha256"] != SOURCE_CONTRACT_SHA256:
                raise ValueError("source-contract identity mismatch")
        if verify_sampler:
            if model is None:
                raise AssertionError("sampler verification lacks source model")
            # Reconstruct the preceding global time directly from the serialized sequence.
            replay_rng = SplitMix64(seed, int(row["sampler_counter_start0"]))
            prior_global = offset if index == 0 else _finite(rows[index - 1]["global_poisson_time_s"], "prior global time")
            expected = _sample_primary(model, replay_rng, global_time_before_s=prior_global, shard_time_offset_s=offset)
            if _eventlist_line(expected, index + 1) != line:
                raise ValueError("raw tape row does not reproduce from source sampler")
            if (
                expected.driver != primary.driver
                or expected.spectrum_sha256 != primary.spectrum_sha256
                or expected.sampler_counter_end0 != primary.sampler_counter_end0
                or eventlist_binary64_hash(expected) != row["expected_eventlist_binary64_sha256"]
                or generated_binary64_hash(
                    expected, runtime_source_time_s=runtime_source_time_s
                ) != row["expected_generated_binary64_sha256"]
                or generated_tuple_hash(expected) != row["expected_generated_tuple_sha256"]
            ):
                raise ValueError("source sampler provenance/digests do not reproduce")
    return {
        "event_count": len(rows),
        "first_root_id": rows[0]["stable_root_id"],
        "last_root_id": rows[-1]["stable_root_id"],
        "family": family,
        "mode": mode,
        "sampler_seed_u64": seed,
        "source_time_semantics": _source_time_contract(),
        "pre_registered_outcome_independent_control_count": sum(row["control_flag"] == "1" for row in rows),
    }
