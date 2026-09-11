#!/usr/bin/env python3
"""Shared, side-effect-free contracts for the corrected-keV proton P0 pilot."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import uuid
from dataclasses import dataclass
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any, Iterable


THIS_FILE = Path(__file__).resolve()
P0_ROOT = THIS_FILE.parents[1]
REPAIR_ROOT = P0_ROOT.parent
ROOT = REPAIR_ROOT.parents[1]
RUN_ROOT = ROOT / "runs/particle_source_unit_repair_20260811/proton_p0_sixband_pilot_20260812"
SOURCE_MANIFEST = P0_ROOT / "data/proton_p0_sixband_source_manifest.json"
SCIENCE_CONTRACT = P0_ROOT / "data/proton_p0_sixband_science_contract.json"
SOURCE_CONTRACT = REPAIR_ROOT / "data/source_contract_manifest.json"
SOURCE_CONTRACT_SHA256 = "5424eeca35b20affb153c0e07c31a6582e575f511922bf55f40a5a0f77ab4326"

GEOMETRIES = ("mass_model_511", "s3d_o8")
MODES = ("instant", "buildup")
GEOMETRY_SOURCE_DIR = {
    "mass_model_511": "mass_model_511",
    "s3d_o8": "s3d_o8",
}
PARENT_SOURCE = {
    geometry: REPAIR_ROOT / "config/source_cards" / source_dir / "Background_p_fullsphere20.source"
    for geometry, source_dir in GEOMETRY_SOURCE_DIR.items()
}
EXPECTED_PARENT_SOURCE_SHA256 = {
    "mass_model_511": "342d75b341bdc8ac6bc400604ce92d4b5a62c4e9308c8f0a20a38395529c13ce",
    "s3d_o8": "171ad9ba2079406fca665fd0cc6d58ffc5171f7bdc324df5b5a5182194b68b95",
}

TOTAL_FLUX_DECIMAL = Decimal("0.1123007216313341")
EVENTS_PER_CELL = 256
SHARDS_PER_CELL = 4
EVENTS_PER_SHARD = 64
FARFIELD_RADIUS_CM = Decimal("60")
JOB_COUNT = len(GEOMETRIES) * len(MODES) * 6 * SHARDS_PER_CELL
PRIMARY_COUNT = JOB_COUNT * EVENTS_PER_SHARD

FLUX_RE = re.compile(r"^(?P<name>Atm_p_bin(?P<bin>[0-9]{2})_(?:down|up))\.Flux\s+(?P<value>\S+)\s*$")
SPECTRUM_RE = re.compile(
    r"^(?P<name>Atm_p_bin(?P<bin>[0-9]{2})_(?:down|up))\.Spectrum\s+File\s+(?P<path>\S+)\s*$"
)
BEAM_RE = re.compile(r"^Atm_p_bin(?P<bin>[0-9]{2})_(?:down|up)\.Beam\s+(.+?)\s*$")
GEOMETRY_RE = re.compile(r"^Geometry\s+(.+?)\s*$")


@dataclass(frozen=True)
class Band:
    index: int
    key: str
    low_keV: Decimal
    high_keV: Decimal
    high_inclusive: bool
    flux_cm2_s: Decimal
    weight: Decimal


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_digest(payload: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def load_json_strict(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON token {token}")
            ),
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"cannot load strict JSON {rel(path)}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON root is not an object: {rel(path)}")
    return payload


def atomic_write_once_json(path: Path, payload: dict[str, Any]) -> bool:
    """Publish canonical JSON without replacing any existing authority bytes."""

    data = json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex}")
    created = False
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
            created = True
        except FileExistsError:
            if path.read_bytes() != data:
                raise RuntimeError(f"write-once JSON already differs: {rel(path)}")
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return created


def atomic_replace_json(path: Path, payload: dict[str, Any]) -> None:
    data = json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex}")
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def parse_dp_decimal(path: Path) -> list[tuple[Decimal, Decimal]]:
    points: list[tuple[Decimal, Decimal]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        fields = raw.split()
        if len(fields) == 3 and fields[0] == "DP":
            points.append((Decimal(fields[1]), Decimal(fields[2])))
    if len(points) < 2:
        raise RuntimeError(f"fewer than two DP rows: {rel(path)}")
    if any(x <= 0 or y < 0 for x, y in points):
        raise RuntimeError(f"non-positive energy or negative density: {rel(path)}")
    if any(right[0] <= left[0] for left, right in zip(points, points[1:])):
        raise RuntimeError(f"non-monotonic spectrum energy axis: {rel(path)}")
    return points


def linear_value(
    left: tuple[Decimal, Decimal],
    right: tuple[Decimal, Decimal],
    x: Decimal,
) -> Decimal:
    x0, y0 = left
    x1, y1 = right
    if not x0 <= x <= x1:
        raise ValueError("interpolation point outside segment")
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def integrate_linear(
    points: list[tuple[Decimal, Decimal]],
    low: Decimal | None = None,
    high: Decimal | None = None,
) -> Decimal:
    lo = points[0][0] if low is None else low
    hi = points[-1][0] if high is None else high
    if hi <= lo:
        return Decimal(0)
    total = Decimal(0)
    for left, right in zip(points, points[1:]):
        x0, _ = left
        x1, _ = right
        segment_low = max(x0, lo)
        segment_high = min(x1, hi)
        if segment_high <= segment_low:
            continue
        y_low = linear_value(left, right, segment_low)
        y_high = linear_value(left, right, segment_high)
        total += (y_low + y_high) * (segment_high - segment_low) / Decimal(2)
    return total


def conditional_points(
    points: list[tuple[Decimal, Decimal]],
    low: Decimal,
    high: Decimal,
) -> tuple[list[tuple[Decimal, Decimal]], Decimal]:
    support_low = points[0][0]
    support_high = points[-1][0]
    clipped_low = max(low, support_low)
    clipped_high = min(high, support_high)
    if clipped_high <= clipped_low:
        raise RuntimeError("band does not overlap spectrum support")
    selected: list[tuple[Decimal, Decimal]] = []
    for left, right in zip(points, points[1:]):
        if left[0] <= clipped_low <= right[0]:
            selected.append((clipped_low, linear_value(left, right, clipped_low)))
            break
    selected.extend((x, y) for x, y in points if clipped_low < x < clipped_high)
    for left, right in zip(points, points[1:]):
        if left[0] <= clipped_high <= right[0]:
            selected.append((clipped_high, linear_value(left, right, clipped_high)))
            break
    deduplicated: list[tuple[Decimal, Decimal]] = []
    for row in selected:
        if deduplicated and row[0] == deduplicated[-1][0]:
            deduplicated[-1] = row
        else:
            deduplicated.append(row)
    integral = integrate_linear(deduplicated)
    if integral <= 0:
        raise RuntimeError("conditional band has non-positive integral")
    return [(x, y / integral) for x, y in deduplicated], integral


def parent_card_records(path: Path) -> dict[str, Any]:
    flux: dict[int, Decimal] = {}
    spectra: dict[int, Path] = {}
    beams: dict[int, str] = {}
    geometry: list[Path] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if match := FLUX_RE.match(stripped):
            flux[int(match.group("bin"))] = Decimal(match.group("value"))
        elif match := SPECTRUM_RE.match(stripped):
            spectra[int(match.group("bin"))] = resolve_path(match.group("path"))
        elif match := BEAM_RE.match(stripped):
            beams[int(match.group("bin"))] = match.group(1)
        elif match := GEOMETRY_RE.match(stripped):
            geometry.append(resolve_path(match.group(1)))
    if set(flux) != set(range(20)) or set(spectra) != set(range(20)) or set(beams) != set(range(20)):
        raise RuntimeError(f"parent proton card does not contain exact 20-bin records: {rel(path)}")
    if len(geometry) != 1:
        raise RuntimeError(f"parent proton card Geometry count is not one: {rel(path)}")
    if sum(flux.values(), Decimal(0)) != TOTAL_FLUX_DECIMAL:
        raise RuntimeError(f"parent proton Flux sum is not exact canonical Decimal: {rel(path)}")
    return {"flux": flux, "spectra": spectra, "beams": beams, "geometry": geometry[0]}


def load_source_manifest(*, required: bool = True) -> dict[str, Any] | None:
    if not SOURCE_MANIFEST.is_file():
        if required:
            raise RuntimeError(
                "P0 conditional-source science contract is not frozen; source manifest is absent"
            )
        return None
    manifest = load_json_strict(SOURCE_MANIFEST)
    validate_source_manifest(manifest, verify_files=True)
    return manifest


def bands_from_manifest(manifest: dict[str, Any]) -> tuple[Band, ...]:
    rows = manifest.get("bands")
    if not isinstance(rows, list) or len(rows) != 6:
        raise RuntimeError("P0 source manifest must define exactly six bands")
    bands: list[Band] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or row.get("index") != index or row.get("key") != f"b{index}":
            raise RuntimeError("P0 band identity/order mismatch")
        bands.append(
            Band(
                index=index,
                key=f"b{index}",
                low_keV=Decimal(str(row["low_keV"])),
                high_keV=Decimal(str(row["high_keV"])),
                high_inclusive=bool(row["high_inclusive"]),
                flux_cm2_s=Decimal(str(row["flux_cm2_s"])),
                weight=Decimal(str(row["weight"])),
            )
        )
    return tuple(bands)


def band_source_path(geometry: str, band_key: str) -> Path:
    return P0_ROOT / "config/source_cards" / geometry / f"Background_p_fullsphere20_{band_key}.source"


def validate_source_manifest(manifest: dict[str, Any], *, verify_files: bool) -> None:
    exact_keyset(
        manifest,
        {
            "schema_version",
            "status",
            "derivation",
            "authority_boundary",
            "source_contract_manifest",
            "source_contract_manifest_sha256",
            "science_contract",
            "science_contract_sha256",
            "total_flux_cm2_s",
            "bands",
            "angular_bin_partial_flux",
            "conditional_spectra",
            "geometries",
            "normalization",
            "events_per_cell",
            "shards_per_cell",
            "events_per_shard",
        },
        "P0 source manifest",
    )
    if manifest.get("schema_version") != 1:
        raise RuntimeError("P0 source manifest schema mismatch")
    if manifest.get("status") != "PASS__P0_SIXBAND_CONDITIONAL_SOURCE_DERIVATION":
        raise RuntimeError("P0 source manifest is not a clean PASS")
    if manifest.get("source_contract_manifest_sha256") != SOURCE_CONTRACT_SHA256:
        raise RuntimeError("P0 source manifest corrected-keV contract binding mismatch")
    if manifest.get("source_contract_manifest") != rel(SOURCE_CONTRACT):
        raise RuntimeError("P0 source manifest corrected-keV contract path mismatch")
    if manifest.get("science_contract") != rel(SCIENCE_CONTRACT):
        raise RuntimeError("P0 source manifest science-contract path mismatch")
    if Decimal(str(manifest.get("total_flux_cm2_s"))) != TOTAL_FLUX_DECIMAL:
        raise RuntimeError("P0 source manifest total Flux mismatch")
    bands = bands_from_manifest(manifest)
    rows = manifest.get("bands", [])
    with localcontext() as context:
        context.prec = 400
        flux_sum = sum((Decimal(str(row["flux_cm2_s"])) for row in rows), Decimal(0))
        if flux_sum != TOTAL_FLUX_DECIMAL:
            raise RuntimeError("P0 band partial Flux values do not close exactly")
        weight_sum = sum((Decimal(str(row["weight"])) for row in rows), Decimal(0))
        if weight_sum != Decimal(1):
            raise RuntimeError("P0 band weights do not close exactly to one")
    previous_high: Decimal | None = None
    for index, row in enumerate(rows):
        low = Decimal(str(row["low_keV"]))
        high = Decimal(str(row["high_keV"]))
        if row.get("index") != index or row.get("key") != f"b{index}" or high <= low:
            raise RuntimeError("P0 band envelope is malformed")
        if previous_high is not None and low != previous_high:
            raise RuntimeError("P0 band envelope has a gap or overlap")
        previous_high = high
    if tuple(band.key for band in bands) != tuple(f"b{index}" for index in range(6)):
        raise RuntimeError("P0 parsed band order mismatch")
    if (
        manifest.get("events_per_cell") != EVENTS_PER_CELL
        or manifest.get("shards_per_cell") != SHARDS_PER_CELL
        or manifest.get("events_per_shard") != EVENTS_PER_SHARD
    ):
        raise RuntimeError("P0 source manifest statistics mismatch")
    partial_rows = manifest.get("angular_bin_partial_flux")
    if not isinstance(partial_rows, list) or len(partial_rows) != 20:
        raise RuntimeError("P0 angular partial-Flux inventory is not exact 20")
    for angular, record in enumerate(partial_rows):
        if not isinstance(record, dict) or record.get("angular_bin") != angular:
            raise RuntimeError("P0 angular partial-Flux identity/order mismatch")
        values = record.get("partial_flux_cm2_s")
        if not isinstance(values, list) or len(values) != 6:
            raise RuntimeError(f"bin{angular:02d}: partial-Flux vector is not length six")
        decimals = [Decimal(str(value)) for value in values]
        parent_flux = parent_card_records(PARENT_SOURCE["mass_model_511"])["flux"][angular]
        with localcontext() as context:
            context.prec = 400
            if (
                Decimal(str(record.get("parent_flux_cm2_s"))) != parent_flux
                or any(value <= 0 for value in decimals)
                or sum(decimals, Decimal(0)) != parent_flux
                or record.get("exact_residual_closure") is not True
            ):
                raise RuntimeError(f"bin{angular:02d}: partial-Flux proof mismatch")
    spectrum_rows = manifest.get("conditional_spectra")
    if not isinstance(spectrum_rows, list) or len(spectrum_rows) != 120:
        raise RuntimeError("P0 conditional spectrum inventory is not exact 120")
    identities: set[tuple[str, int]] = set()
    for record in spectrum_rows:
        if not isinstance(record, dict):
            raise RuntimeError("P0 conditional spectrum row is not an object")
        identity = (str(record.get("band")), record.get("angular_bin"))
        if type(identity[1]) is not int or identity in identities:
            raise RuntimeError("P0 conditional spectrum identity is invalid/duplicate")
        identities.add((identity[0], int(identity[1])))
        band_index = int(identity[0][1:]) if re.fullmatch(r"b[0-5]", identity[0]) else -1
        angular = int(identity[1])
        if band_index < 0 or not 0 <= angular < 20:
            raise RuntimeError("P0 conditional spectrum band/bin is outside contract")
        if (
            Decimal(str(record.get("low_keV"))) != bands[band_index].low_keV
            or Decimal(str(record.get("high_keV"))) != bands[band_index].high_keV
        ):
            raise RuntimeError("P0 conditional spectrum support differs from band envelope")
    if identities != {(f"b{band}", angular) for band in range(6) for angular in range(20)}:
        raise RuntimeError("P0 conditional spectrum identities are incomplete")
    geometries = manifest.get("geometries")
    if not isinstance(geometries, dict) or set(geometries) != set(GEOMETRIES):
        raise RuntimeError("P0 source manifest geometry set mismatch")
    for geometry in GEOMETRIES:
        record = geometries[geometry]
        parent = PARENT_SOURCE[geometry]
        if record.get("parent_source") != rel(parent):
            raise RuntimeError(f"{geometry}: P0 parent source path mismatch")
        if record.get("parent_source_sha256") != EXPECTED_PARENT_SOURCE_SHA256[geometry]:
            raise RuntimeError(f"{geometry}: P0 parent source hash mismatch")
        cards = record.get("band_source_cards")
        if not isinstance(cards, list) or len(cards) != 6:
            raise RuntimeError(f"{geometry}: P0 source-card count mismatch")
        for index, card in enumerate(cards):
            expected_path = band_source_path(geometry, f"b{index}")
            if card.get("band") != f"b{index}" or card.get("path") != rel(expected_path):
                raise RuntimeError(f"{geometry}/b{index}: P0 source-card identity mismatch")
            if verify_files:
                if not expected_path.is_file() or sha256(expected_path) != card.get("sha256"):
                    raise RuntimeError(f"{geometry}/b{index}: P0 source-card hash mismatch")
    if verify_files:
        if sha256(SOURCE_CONTRACT) != SOURCE_CONTRACT_SHA256:
            raise RuntimeError("corrected-keV source contract hash drift")
        if (
            not SCIENCE_CONTRACT.is_file()
            or sha256(SCIENCE_CONTRACT) != manifest.get("science_contract_sha256")
        ):
            raise RuntimeError("P0 frozen science-contract hash drift")
        science = load_json_strict(SCIENCE_CONTRACT)
        if (
            science.get("schema_version") != 1
            or science.get("status") != "FROZEN__P0_SIXBAND_SCIENCE_CONTRACT"
            or science.get("band_count") != 6
            or Decimal(str(science.get("total_flux_cm2_s"))) != TOTAL_FLUX_DECIMAL
            or [Decimal(str(value)) for value in science.get("energy_edges_keV", [])]
            != [bands[0].low_keV, *(band.high_keV for band in bands)]
        ):
            raise RuntimeError("P0 science contract content differs from source manifest")
        for geometry in GEOMETRIES:
            parent = PARENT_SOURCE[geometry]
            if not parent.is_file() or sha256(parent) != EXPECTED_PARENT_SOURCE_SHA256[geometry]:
                raise RuntimeError(f"{geometry}: parent proton source hash drift")
        for row in manifest.get("conditional_spectra", []):
            path = resolve_path(str(row.get("path")))
            if not path.is_file() or sha256(path) != row.get("sha256"):
                raise RuntimeError(f"conditional spectrum hash mismatch: {row.get('path')}")


def decimal_to_json(value: Decimal) -> str:
    return format(value, "f")


def tt_expected_seconds(events: int, flux_cm2_s: Decimal) -> Decimal:
    if events <= 0 or flux_cm2_s <= 0:
        raise ValueError("events and Flux must be positive")
    with localcontext() as context:
        context.prec = 50
        return Decimal(events) / (flux_cm2_s * Decimal(str(math.pi)) * FARFIELD_RADIUS_CM**2)


def stable_file_snapshot(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise RuntimeError(f"symlink is forbidden for authority/artifact: {rel(path)}")
    before = path.stat()
    digest = sha256(path)
    after = path.stat()
    identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if identity_before != identity_after or after.st_size <= 0:
        raise RuntimeError(f"file changed during hash: {rel(path)}")
    return {
        "path": rel(path),
        "sha256": digest,
        "size_bytes": after.st_size,
        "device": after.st_dev,
        "inode": after.st_ino,
        "mtime_ns": after.st_mtime_ns,
    }


def exact_keyset(payload: dict[str, Any], keys: Iterable[str], label: str) -> None:
    expected = set(keys)
    observed = set(payload)
    if observed != expected:
        raise RuntimeError(
            f"{label} key set mismatch: missing={sorted(expected-observed)}, extra={sorted(observed-expected)}"
        )
