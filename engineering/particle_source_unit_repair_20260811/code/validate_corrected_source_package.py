#!/usr/bin/env python3
"""Fail-closed static validation for the corrected TES-511 source package.

The validator deliberately re-derives every important quantity from the raw
files.  A manifest is an inventory to be checked, not evidence that its own
claims are true.  No retained source, geometry, or spectrum is modified.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable


PACKAGE = Path(__file__).resolve().parents[1]
REPOSITORY = Path(__file__).resolve().parents[3]
MANIFEST_RELATIVE = Path("data/source_contract_manifest.json")
REPORT_RELATIVE = Path("data/static_validation.json")
DEFAULT_MEGALIB_ROOT = Path("/home/ubuntu/MEGAlib_Install/megalib-main")

FAMILIES = (
    "alpha",
    "eminus",
    "eplus",
    "gamma",
    "muminus",
    "muplus",
    "n",
    "p",
)
GEOMETRIES = ("mass_model_511", "s3c_c0", "s3d_o8")
PARTICLE_TYPES = {
    "alpha": "21",
    "eminus": "3",
    "eplus": "2",
    "gamma": "1",
    "muminus": "9",
    "muplus": "8",
    "n": "6",
    "p": "4",
}
ENERGY_SCALES = {family: (4000.0 if family == "alpha" else 1000.0) for family in FAMILIES}

PROPERTY_RE = re.compile(
    r"^([A-Za-z][A-Za-z0-9_]*)\.(ParticleType|Beam|Spectrum|Flux)\s+(.+?)\s*$"
)
RUN_SOURCE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*\.Source\s+(\S+)\s*$")
GEOMETRY_RE = re.compile(r"^Geometry\s+(\S+)\s*$")
RADIUS_RE = re.compile(r"^\s*#\s*farfield_radius_cm\s*=\s*([-+0-9.eE]+)\s*$", re.MULTILINE)
BIN_RE = re.compile(r"_bin(\d{2})(?:_|\b)")
LEGACY_MARKER = "cosima_spectra_dp_2602units"
INCLUDE_RE = re.compile(r"^\s*Include\s+(?P<target>\S+)\s*$")
RAW_INVENTORY_ALGORITHM = "sha256 of sorted UTF-8 lines: relative_name<TAB>file_sha256<LF>"
GEOMETRY_BUNDLE_ALGORITHM = (
    "sha256 of sorted UTF-8 lines: "
    "scope<TAB>logical_path<TAB>file_sha256<LF>"
)
INDEPENDENT_RAW_LEDGER_SHA256 = (
    "2f103de0c90408d3d2f62f8961030f4f1732d64b4b20f1685dd2fa15b61ca41c"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def trapz(points: list[tuple[float, float]]) -> float:
    return math.fsum(
        0.5 * (y0 + y1) * (x1 - x0)
        for (x0, y0), (x1, y1) in zip(points, points[1:])
    )


def finite_number(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def close(a: float, b: float, *, rel: float = 1.0e-9, abs_: float = 1.0e-12) -> bool:
    return math.isclose(a, b, rel_tol=rel, abs_tol=abs_)


def _count_field(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, list):
        return len(value)
    return None


def _recursive_values(value: Any, key: str) -> list[Any]:
    found: list[Any] = []
    if isinstance(value, dict):
        for current_key, current_value in value.items():
            if current_key == key:
                found.append(current_value)
            found.extend(_recursive_values(current_value, key))
    elif isinstance(value, list):
        for item in value:
            found.extend(_recursive_values(item, key))
    return found


def _objects_with_path_and_hash(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if "path" in value and "sha256" in value:
            found.append(value)
        for child in value.values():
            found.extend(_objects_with_path_and_hash(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_objects_with_path_and_hash(child))
    return found


@dataclass(frozen=True)
class SourceDefinition:
    particle_type: str
    beam: tuple[Decimal, Decimal, Decimal, Decimal]
    spectrum: str
    flux: Decimal


@dataclass(frozen=True)
class ParsedCard:
    geometry: str
    radius_cm: Decimal
    definitions: dict[str, SourceDefinition]
    run_sources: tuple[str, ...]
    active_contract: tuple[str, ...]


class Gate:
    """Collect all independent failures while keeping every check fail-closed."""

    def __init__(
        self,
        package_root: Path,
        repository_root: Path,
        megalib_root: Path,
    ) -> None:
        self.package_root = package_root.resolve()
        self.repository_root = repository_root.resolve()
        self.megalib_root = megalib_root.resolve()
        self.errors: list[str] = []

    def require(self, condition: bool, message: str) -> bool:
        if not condition:
            self.errors.append(message)
        return condition

    def resolve(self, value: Any, *, label: str) -> Path | None:
        if not isinstance(value, str) or not value.strip():
            self.errors.append(f"{label}: path is missing or not a string")
            return None
        path = Path(value)
        if path.is_absolute():
            return path.resolve()
        # Contract paths are repository-relative.  Package-relative paths are
        # accepted only when the repository-relative spelling does not exist;
        # this keeps isolated temporary fixtures convenient without making the
        # production interpretation ambiguous.
        repository_candidate = (self.repository_root / path).resolve()
        package_candidate = (self.package_root / path).resolve()
        if repository_candidate.exists() or not package_candidate.exists():
            return repository_candidate
        return package_candidate

    def read_json(self, path: Path, *, label: str) -> dict[str, Any] | None:
        if not self.require(path.is_file(), f"{label}: missing file: {path}"):
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            self.errors.append(f"{label}: cannot parse JSON: {exc}")
            return None
        if not isinstance(value, dict):
            self.errors.append(f"{label}: top level must be an object")
            return None
        return value

    def check_hash(self, path: Path | None, expected: Any, *, label: str) -> None:
        if path is None or not path.is_file():
            if path is not None:
                self.errors.append(f"{label}: cannot hash missing file: {path}")
            return
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            self.errors.append(f"{label}: invalid or missing SHA-256 in manifest")
            return
        actual = sha256(path)
        self.require(actual == expected, f"{label}: SHA-256 mismatch ({actual} != {expected})")


def parse_raw(path: Path) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for raw_line in path.read_text(encoding="utf-8", errors="strict").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = stripped.split()
        if len(fields) != 2:
            raise ValueError(f"unexpected active raw-spectrum line: {raw_line!r}")
        points.append((float(fields[0]), float(fields[1])))
    if len(points) < 2:
        raise ValueError("fewer than two raw-spectrum points")
    return points


def parse_dp(path: Path) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    interpolation_lines = 0
    for raw_line in path.read_text(encoding="utf-8", errors="strict").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = stripped.split()
        if fields == ["IP", "LIN"]:
            interpolation_lines += 1
        elif len(fields) == 3 and fields[0] == "DP":
            points.append((float(fields[1]), float(fields[2])))
        else:
            raise ValueError(f"unexpected active DP line: {raw_line!r}")
    if interpolation_lines != 1:
        raise ValueError(f"expected exactly one 'IP LIN', found {interpolation_lines}")
    if len(points) < 2:
        raise ValueError("fewer than two DP points")
    return points


def _decimal_tuple(fields: Iterable[str], *, label: str) -> tuple[Decimal, ...]:
    try:
        values = tuple(Decimal(field) for field in fields)
    except InvalidOperation as exc:
        raise ValueError(f"{label}: non-numeric value") from exc
    if not all(value.is_finite() for value in values):
        raise ValueError(f"{label}: non-finite value")
    return values


def parse_source_card(path: Path) -> ParsedCard:
    text = path.read_text(encoding="utf-8", errors="strict")
    geometry_values: list[str] = []
    property_values: dict[str, dict[str, str]] = defaultdict(dict)
    run_sources: list[str] = []
    active_contract: list[str] = []

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        geometry_match = GEOMETRY_RE.fullmatch(stripped)
        if geometry_match:
            geometry_values.append(geometry_match.group(1))
        run_source_match = RUN_SOURCE_RE.fullmatch(stripped)
        if run_source_match:
            run_sources.append(run_source_match.group(1))
        property_match = PROPERTY_RE.fullmatch(stripped)
        if property_match:
            name, prop, value = property_match.groups()
            if prop in property_values[name]:
                raise ValueError(f"duplicate {name}.{prop}")
            property_values[name][prop] = value

        # Only Spectrum targets may differ from the retained parent card.
        if property_match and property_match.group(2) == "Spectrum":
            active_contract.append(f"{property_match.group(1)}.Spectrum File <CORRECTED_DP>")
        else:
            active_contract.append(stripped)

    if len(geometry_values) != 1:
        raise ValueError(f"expected one active Geometry line, found {len(geometry_values)}")
    radius_matches = RADIUS_RE.findall(text)
    if len(radius_matches) != 1:
        raise ValueError(f"expected one farfield_radius_cm comment, found {len(radius_matches)}")
    radius = _decimal_tuple(radius_matches, label="farfield radius")[0]

    definitions: dict[str, SourceDefinition] = {}
    required = {"ParticleType", "Beam", "Spectrum", "Flux"}
    for name, values in property_values.items():
        missing = required - set(values)
        extra = set(values) - required
        if missing or extra:
            raise ValueError(f"{name}: incomplete definition; missing={sorted(missing)}, extra={sorted(extra)}")
        beam_fields = values["Beam"].split()
        if len(beam_fields) != 5 or beam_fields[0] != "FarFieldAreaSource":
            raise ValueError(f"{name}: Beam is not a four-angle FarFieldAreaSource")
        spectrum_fields = values["Spectrum"].split()
        if len(spectrum_fields) != 2 or spectrum_fields[0] != "File":
            raise ValueError(f"{name}: Spectrum is not 'File PATH'")
        particle_fields = values["ParticleType"].split()
        flux_fields = values["Flux"].split()
        if len(particle_fields) != 1 or len(flux_fields) != 1:
            raise ValueError(f"{name}: invalid ParticleType or Flux arity")
        flux = _decimal_tuple(flux_fields, label=f"{name}.Flux")[0]
        if flux <= 0:
            raise ValueError(f"{name}: Flux must be positive")
        definitions[name] = SourceDefinition(
            particle_type=particle_fields[0],
            beam=_decimal_tuple(beam_fields[1:], label=f"{name}.Beam"),  # type: ignore[arg-type]
            spectrum=spectrum_fields[1],
            flux=flux,
        )

    return ParsedCard(
        geometry=geometry_values[0],
        radius_cm=radius,
        definitions=definitions,
        run_sources=tuple(run_sources),
        active_contract=tuple(active_contract),
    )


def _validate_numeric_points(
    gate: Gate, points: list[tuple[float, float]], *, label: str
) -> None:
    gate.require(all(math.isfinite(x) and math.isfinite(y) for x, y in points), f"{label}: non-finite x/y")
    gate.require(all(y >= 0.0 for _, y in points), f"{label}: negative PDF/flux value")
    gate.require(all(x1 > x0 for (x0, _), (x1, _) in zip(points, points[1:])), f"{label}: energy axis is not strictly increasing")


def validate_spectra(
    gate: Gate, manifest: dict[str, Any]
) -> tuple[dict[tuple[str, int], Path], dict[str, Any]]:
    section = manifest.get("spectra")
    if not isinstance(section, dict):
        gate.errors.append("manifest.spectra must be an object")
        return {}, {"files": 0}
    files = section.get("files")
    if not isinstance(files, list):
        gate.errors.append("manifest.spectra.files must be an array")
        return {}, {"files": 0}
    gate.require(section.get("count") == 160, "manifest.spectra.count must equal 160")
    gate.require(len(files) == 160, f"manifest must inventory 160 spectra, found {len(files)}")
    root_path = gate.resolve(section.get("root"), label="manifest.spectra.root")
    if root_path is not None:
        gate.require(root_path.is_dir(), f"corrected spectrum root is missing: {root_path}")

    indexed: dict[tuple[str, int], Path] = {}
    per_family: Counter[str] = Counter()
    integrals: list[float] = []
    for index, row in enumerate(files):
        label = f"spectra.files[{index}]"
        if not isinstance(row, dict):
            gate.errors.append(f"{label}: entry must be an object")
            continue
        family = row.get("family")
        bin_id = row.get("bin_id")
        if family not in FAMILIES:
            gate.errors.append(f"{label}: invalid family {family!r}")
            continue
        try:
            bin_number = int(bin_id)
        except (TypeError, ValueError):
            gate.errors.append(f"{label}: invalid bin_id {bin_id!r}")
            continue
        gate.require(0 <= bin_number < 20, f"{label}: bin_id outside 0..19")
        key = (family, bin_number)
        gate.require(key not in indexed, f"{label}: duplicate family/bin {key}")

        raw_path = gate.resolve(row.get("raw_spectrum"), label=f"{label}.raw_spectrum")
        snapshot_path = gate.resolve(
            row.get("package_raw_snapshot_path"),
            label=f"{label}.package_raw_snapshot_path",
        )
        corrected_path = gate.resolve(row.get("corrected_spectrum"), label=f"{label}.corrected_spectrum")
        gate.require(
            raw_path is not None and raw_path == snapshot_path,
            f"{label}: raw_spectrum must be the package-owned raw snapshot",
        )
        if raw_path is not None:
            gate.require(
                raw_path.suffix == ".raw-spectrum",
                f"{label}: raw snapshot must use .raw-spectrum extension",
            )
            try:
                raw_path.relative_to(gate.package_root)
            except ValueError:
                gate.errors.append(
                    f"{label}: raw snapshot is outside the repair package"
                )
        declared_raw_hashes = {
            row.get("raw_sha256"),
            row.get("package_raw_snapshot_sha256"),
            row.get("original_raw_sha256"),
        }
        gate.require(
            len(declared_raw_hashes) == 1
            and None not in declared_raw_hashes,
            f"{label}: snapshot/original raw SHA-256 mapping is inconsistent",
        )
        gate.require(
            row.get("snapshot_original_hash_match") is True,
            f"{label}: snapshot_original_hash_match must be true",
        )
        original_raw_path = row.get("original_raw_path")
        gate.require(
            isinstance(original_raw_path, str)
            and original_raw_path.startswith(
                "expacs_fullsphere_20bin_sources/raw_expacs/"
            )
            and original_raw_path.endswith(".dat"),
            f"{label}: invalid bootstrap-only original_raw_path mapping",
        )
        if corrected_path is not None:
            indexed[key] = corrected_path
            if root_path is not None:
                gate.require(corrected_path.parent == root_path, f"{label}: corrected spectrum is outside the declared root")
        per_family[family] += 1
        expected_scale = ENERGY_SCALES[family]
        gate.require(finite_number(row.get("energy_scale_to_total_keV")) and float(row["energy_scale_to_total_keV"]) == expected_scale, f"{label}: energy scale must be {expected_scale:g}")
        raw_unit = row.get("raw_energy_unit")
        if family == "alpha":
            gate.require(raw_unit in {"MeV/n", "MeV_per_nucleon"}, f"{label}: alpha raw unit must be MeV/n")
        else:
            gate.require(raw_unit == "MeV", f"{label}: raw unit must be MeV")
        gate.require(row.get("output_energy_unit") in {"keV", "keV_total"}, f"{label}: output unit must be total keV")

        gate.check_hash(raw_path, row.get("raw_sha256"), label=f"{label}.raw")
        gate.check_hash(
            snapshot_path,
            row.get("package_raw_snapshot_sha256"),
            label=f"{label}.package_raw_snapshot",
        )
        gate.check_hash(corrected_path, row.get("corrected_sha256"), label=f"{label}.corrected")
        if raw_path is None or corrected_path is None or not raw_path.is_file() or not corrected_path.is_file():
            continue
        try:
            raw_points = parse_raw(raw_path)
            corrected_points = parse_dp(corrected_path)
        except (OSError, UnicodeError, ValueError) as exc:
            gate.errors.append(f"{label}: spectrum parse failure: {exc}")
            continue
        _validate_numeric_points(gate, raw_points, label=f"{label}.raw")
        _validate_numeric_points(gate, corrected_points, label=f"{label}.corrected")
        gate.require(len(raw_points) == len(corrected_points), f"{label}: raw/DP point counts differ")
        gate.require(row.get("point_count") == len(corrected_points), f"{label}: manifest point_count mismatch")

        raw_integral = trapz(raw_points)
        corrected_integral = trapz(corrected_points)
        integrals.append(corrected_integral)
        gate.require(math.isfinite(raw_integral) and raw_integral > 0.0, f"{label}: raw integral must be finite and positive")
        gate.require(close(corrected_integral, 1.0, rel=0.0, abs_=1.0e-8), f"{label}: corrected DP integral is not 1 ({corrected_integral:.17g})")
        if finite_number(row.get("raw_integral")):
            gate.require(close(float(row["raw_integral"]), raw_integral, rel=1.0e-10), f"{label}: manifest raw_integral mismatch")
        else:
            gate.errors.append(f"{label}: missing/non-finite raw_integral")
        if finite_number(row.get("corrected_pdf_integral")):
            gate.require(close(float(row["corrected_pdf_integral"]), corrected_integral, rel=1.0e-10), f"{label}: manifest corrected_pdf_integral mismatch")
        else:
            gate.errors.append(f"{label}: missing/non-finite corrected_pdf_integral")

        if len(raw_points) == len(corrected_points) and raw_integral > 0.0:
            for point_index, ((raw_x, raw_y), (dp_x, dp_y)) in enumerate(zip(raw_points, corrected_points)):
                expected_x = raw_x * expected_scale
                expected_y = raw_y / (raw_integral * expected_scale)
                gate.require(close(dp_x, expected_x, rel=2.0e-11, abs_=1.0e-8), f"{label}: raw->DP energy conversion failed at point {point_index} ({dp_x:g} != {expected_x:g})")
                gate.require(close(dp_y, expected_y, rel=2.0e-9, abs_=1.0e-18), f"{label}: raw->DP PDF conversion failed at point {point_index}")

    for family in FAMILIES:
        gate.require(per_family[family] == 20, f"{family}: expected 20 corrected spectra, found {per_family[family]}")
        bins = {bin_id for current_family, bin_id in indexed if current_family == family}
        gate.require(bins == set(range(20)), f"{family}: corrected spectrum bins are not exactly 00..19")
    if root_path is not None and root_path.is_dir():
        actual_files = sorted(path for path in root_path.iterdir() if path.is_file())
        gate.require(len(actual_files) == 160, f"corrected spectrum root must contain exactly 160 spectrum files, found {len(actual_files)}")
        gate.require({path.resolve() for path in actual_files} == {path.resolve() for path in indexed.values()}, "corrected spectrum root and manifest inventory differ")
    return indexed, {
        "files": len(indexed),
        "families": dict(sorted(per_family.items())),
        "integral_min": min(integrals) if integrals else None,
        "integral_max": max(integrals) if integrals else None,
    }


def validate_input_provenance(
    gate: Gate, manifest: dict[str, Any]
) -> dict[tuple[str, int], Decimal]:
    """Hash-check declared inputs and load the independent per-bin Flux ledger."""
    provenance = manifest.get("input_provenance")
    if not isinstance(provenance, dict):
        gate.errors.append("manifest.input_provenance must be an object")
        return {}
    hashed_inputs = _objects_with_path_and_hash(provenance)
    environment = manifest.get("source_model", {}).get("environment", {}) if isinstance(manifest.get("source_model"), dict) else {}
    hashed_inputs.extend(_objects_with_path_and_hash(environment))
    gate.require(bool(hashed_inputs), "input_provenance must contain at least one path+sha256 file record")
    seen_paths: set[Path] = set()
    for index, row in enumerate(hashed_inputs):
        label = f"input_provenance.hashed_file[{index}]"
        path = gate.resolve(row.get("path"), label=f"{label}.path")
        if path is not None:
            gate.require(path not in seen_paths, f"{label}: duplicate hashed input path")
            seen_paths.add(path)
        gate.check_hash(path, row.get("sha256"), label=label)

    evidence_record = provenance.get("independent_raw_hash_evidence")
    evidence_by_original: dict[str, tuple[int, str]] = {}
    if not isinstance(evidence_record, dict):
        gate.errors.append(
            "input_provenance.independent_raw_hash_evidence must be a frozen ledger"
        )
    else:
        evidence_path = gate.resolve(
            evidence_record.get("path"),
            label="input_provenance.independent_raw_hash_evidence.path",
        )
        gate.require(
            evidence_record.get("sha256") == INDEPENDENT_RAW_LEDGER_SHA256,
            "independent raw hash ledger SHA-256 is not the frozen audit anchor",
        )
        gate.require(
            evidence_record.get("raw_entry_count") == 160,
            "independent raw hash ledger raw_entry_count must be 160",
        )
        gate.require(
            "normal build has no dependency" in str(evidence_record.get("source", "")),
            "independent raw hash ledger source/provenance statement is missing",
        )
        if evidence_path is not None and evidence_path.is_file():
            try:
                with evidence_path.open(encoding="utf-8", newline="") as handle:
                    evidence_rows = list(csv.DictReader(handle))
            except (OSError, UnicodeError, csv.Error) as exc:
                gate.errors.append(f"independent raw hash ledger parse failure: {exc}")
                evidence_rows = []
            for row_index, evidence_row in enumerate(evidence_rows):
                original = evidence_row.get("source", "")
                if not original.startswith(
                    "expacs_fullsphere_20bin_sources/raw_expacs/"
                ):
                    continue
                label = f"independent raw hash ledger row {row_index + 2}"
                try:
                    size = int(evidence_row.get("size_bytes", ""))
                except ValueError:
                    gate.errors.append(f"{label}: invalid size_bytes")
                    continue
                file_hash = evidence_row.get("sha256")
                gate.require(
                    isinstance(file_hash, str)
                    and re.fullmatch(r"[0-9a-f]{64}", file_hash) is not None,
                    f"{label}: invalid SHA-256",
                )
                gate.require(
                    original not in evidence_by_original,
                    f"{label}: duplicate original raw path",
                )
                if isinstance(file_hash, str):
                    evidence_by_original[original] = (size, file_hash)
        gate.require(
            len(evidence_by_original) == 160,
            f"independent raw hash ledger must contain 160 raw entries, found {len(evidence_by_original)}",
        )

    flux_record = provenance.get("flux_manifest")
    if not isinstance(flux_record, dict):
        gate.errors.append("input_provenance.flux_manifest must be a path+sha256 object")
        return {}
    flux_path = gate.resolve(flux_record.get("path"), label="input_provenance.flux_manifest.path")
    if flux_path is None or not flux_path.is_file():
        return {}
    flux_by_bin: dict[tuple[str, int], Decimal] = {}
    try:
        with flux_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except (OSError, UnicodeError, csv.Error) as exc:
        gate.errors.append(f"input_provenance.flux_manifest: cannot parse CSV: {exc}")
        return {}
    gate.require(len(rows) == 160, f"retained Flux manifest must contain 160 rows, found {len(rows)}")
    original_raw_by_bin: dict[tuple[str, int], str] = {}
    for index, row in enumerate(rows):
        label = f"retained Flux manifest row {index + 2}"
        family = row.get("particle")
        try:
            bin_id = int(row.get("bin_id", ""))
            flux = Decimal(row.get("flux_cm2_s", ""))
        except (ValueError, InvalidOperation):
            gate.errors.append(f"{label}: invalid family/bin/flux fields")
            continue
        if family not in FAMILIES or not 0 <= bin_id < 20:
            gate.errors.append(f"{label}: invalid family/bin ({family!r}, {bin_id!r})")
            continue
        key = (family, bin_id)
        gate.require(key not in flux_by_bin, f"{label}: duplicate family/bin {key}")
        gate.require(flux.is_finite() and flux > 0, f"{label}: flux must be finite and positive")
        flux_by_bin[key] = flux
        raw_mapping = row.get("raw_spectrum_path")
        if isinstance(raw_mapping, str) and raw_mapping:
            original_raw_by_bin[key] = raw_mapping
        else:
            gate.errors.append(f"{label}: missing raw_spectrum_path mapping")
    gate.require(set(flux_by_bin) == {(family, bin_id) for family in FAMILIES for bin_id in range(20)}, "retained Flux manifest family/bin inventory is not exactly 8x20")
    gate.require(
        set(original_raw_by_bin) == set(flux_by_bin),
        "retained Flux manifest raw-spectrum mapping is not exactly 8x20",
    )

    source_model = manifest.get("source_model")
    environment = source_model.get("environment") if isinstance(source_model, dict) else None
    if not isinstance(environment, dict):
        gate.errors.append("source_model.environment must be an object derived from manifest.csv")
    else:
        numeric_columns = {
            "latitude_deg": "expacs_lat_deg",
            "longitude_deg": "expacs_lon_deg",
            "altitude_km": "expacs_altitude_km",
            "cutoff_rigidity_gv": "expacs_Rc_GV",
        }
        for target_key, csv_key in numeric_columns.items():
            try:
                values = {Decimal(row[csv_key]) for row in rows}
            except (KeyError, InvalidOperation):
                gate.errors.append(f"retained Flux manifest has invalid {csv_key}")
                continue
            gate.require(len(values) == 1, f"retained Flux manifest {csv_key} is not unique across 160 rows")
            if len(values) == 1 and finite_number(environment.get(target_key)):
                gate.require(close(float(environment[target_key]), float(next(iter(values))), rel=0.0, abs_=1.0e-12), f"source_model.environment.{target_key} disagrees with manifest.csv")
            elif len(values) == 1:
                gate.errors.append(f"source_model.environment.{target_key} is missing/non-finite")
        combined_values = {row.get("W_or_date", "") for row in rows}
        gate.require(len(combined_values) == 1, "retained Flux manifest W_or_date is not unique across 160 rows")
        if len(combined_values) == 1:
            combined = next(iter(combined_values))
            match = re.fullmatch(r"\s*(\d{4}-\d{2}-\d{2})\s*;\s*W\s*=\s*([-+0-9.eE]+)\s*", combined)
            if not match:
                gate.errors.append("retained Flux manifest W_or_date has an unsupported format")
            else:
                gate.require(environment.get("date") == match.group(1), "source_model.environment.date disagrees with manifest.csv")
                gate.require(finite_number(environment.get("solar_modulation_w")) and close(float(environment["solar_modulation_w"]), float(match.group(2)), rel=0.0, abs_=1.0e-12), "source_model.environment.solar_modulation_w disagrees with manifest.csv")
        gate.require({row.get("black_hole_mode") for row in rows} == {"No"}, "retained Flux manifest black_hole_mode must be uniquely No")

    raw_record = provenance.get("raw_spectrum_dir")
    if not isinstance(raw_record, dict):
        gate.errors.append("input_provenance.raw_spectrum_dir must be an inventory object")
    else:
        raw_dir = gate.resolve(raw_record.get("path"), label="input_provenance.raw_spectrum_dir.path")
        if raw_dir is not None and raw_dir.is_dir():
            raw_files = sorted(path for path in raw_dir.iterdir() if path.is_file())
            gate.require(raw_record.get("count") == 160, "raw_spectrum_dir manifest count must be 160")
            gate.require(
                raw_record.get("role") == "package_owned_primary_raw_baseline",
                "raw_spectrum_dir role must identify the package-owned primary baseline",
            )
            gate.require(
                raw_record.get("snapshot_extension") == ".raw-spectrum",
                "raw_spectrum_dir snapshot_extension must be .raw-spectrum",
            )
            try:
                raw_dir.relative_to(gate.package_root)
            except ValueError:
                gate.errors.append(
                    "input_provenance raw_spectrum_dir is outside the repair package"
                )
            gate.require(len(raw_files) == 160, f"raw spectrum directory must contain exactly 160 files, found {len(raw_files)}")
            gate.require(
                all(
                    path.suffix == ".raw-spectrum" and not path.is_symlink()
                    for path in raw_files
                ),
                "raw spectrum directory contains a wrong-extension file or symlink",
            )
            inventory_payload = "".join(
                f"{path.relative_to(raw_dir).as_posix()}\t{sha256(path)}\n"
                for path in raw_files
            ).encode("utf-8")
            inventory_digest = hashlib.sha256(inventory_payload).hexdigest()
            gate.require(
                raw_record.get("inventory_algorithm") == RAW_INVENTORY_ALGORITHM,
                "raw_spectrum_dir inventory_algorithm is missing or unsupported",
            )
            gate.require(raw_record.get("inventory_sha256") == inventory_digest, "raw spectrum directory inventory SHA-256 mismatch")
            declared_raw_paths: set[Path] = set()
            spectra_section = manifest.get("spectra")
            spectrum_rows = spectra_section.get("files", []) if isinstance(spectra_section, dict) else []
            for index, spectrum_row in enumerate(spectrum_rows):
                if isinstance(spectrum_row, dict):
                    declared = gate.resolve(spectrum_row.get("raw_spectrum"), label=f"spectra.files[{index}].raw_spectrum")
                    if declared is not None:
                        declared_raw_paths.add(declared)
                    family = spectrum_row.get("family")
                    try:
                        bin_id = int(spectrum_row.get("bin_id", ""))
                    except (TypeError, ValueError):
                        continue
                    key = (family, bin_id)
                    expected_original = original_raw_by_bin.get(key)
                    gate.require(
                        expected_original is not None
                        and spectrum_row.get("original_raw_path")
                        == expected_original,
                        f"spectra.files[{index}]: original raw mapping disagrees with manifest.csv",
                    )
                    evidence_identity = evidence_by_original.get(
                        str(spectrum_row.get("original_raw_path", ""))
                    )
                    gate.require(
                        evidence_identity is not None
                        and spectrum_row.get("original_raw_sha256")
                        == evidence_identity[1],
                        f"spectra.files[{index}]: original raw SHA-256 disagrees with independent audit ledger",
                    )
                    if declared is not None and declared.is_file() and evidence_identity:
                        gate.require(
                            declared.stat().st_size == evidence_identity[0]
                            and sha256(declared) == evidence_identity[1],
                            f"spectra.files[{index}]: package raw snapshot differs from independent audit ledger",
                        )
                    snapshot_name = Path(
                        str(spectrum_row.get("package_raw_snapshot_path", ""))
                    ).name
                    expected_snapshot_name = (
                        Path(expected_original).with_suffix(".raw-spectrum").name
                        if expected_original is not None
                        else ""
                    )
                    gate.require(
                        snapshot_name == expected_snapshot_name,
                        f"spectra.files[{index}]: raw snapshot filename does not map to original raw name",
                    )
            gate.require(declared_raw_paths == {path.resolve() for path in raw_files}, "raw spectrum directory and manifest spectrum inventory differ")
            if isinstance(source_model, dict):
                retained_root = gate.resolve(source_model.get("retained_raw_root"), label="source_model.retained_raw_root")
                gate.require(retained_root == raw_dir, "source_model.retained_raw_root disagrees with input_provenance")
        elif raw_dir is not None:
            gate.errors.append(f"raw spectrum directory is missing: {raw_dir}")

    bootstrap = provenance.get("raw_snapshot_bootstrap_source")
    if not isinstance(bootstrap, dict):
        gate.errors.append(
            "input_provenance.raw_snapshot_bootstrap_source must document the optional bootstrap"
        )
    else:
        gate.require(
            bootstrap.get("normal_build_dependency") is False,
            "global ignored raw directory must not be a normal-build dependency",
        )
        original_root = (
            source_model.get("original_raw_root")
            if isinstance(source_model, dict)
            else None
        )
        gate.require(
            isinstance(bootstrap.get("path"), str)
            and bootstrap.get("path") == original_root,
            "bootstrap raw mapping disagrees with source_model.original_raw_root",
        )
        gate.require(
            "--bootstrap-raw-snapshots" in str(bootstrap.get("policy", "")),
            "bootstrap raw policy must require explicit --bootstrap-raw-snapshots",
        )
    return flux_by_bin


def _geometry_bundle_path(
    gate: Gate,
    row: dict[str, Any],
    *,
    label: str,
) -> Path | None:
    scope = row.get("scope")
    logical = row.get("logical_path")
    if not isinstance(logical, str) or not logical:
        gate.errors.append(f"{label}: logical_path is missing")
        return None
    if scope == "repository":
        gate.require(
            row.get("path") == logical,
            f"{label}: repository path and logical_path must be identical",
        )
        return gate.resolve(row.get("path"), label=f"{label}.path")
    if scope == "megalib":
        relative_value = row.get("path_relative_to_megalib")
        if not isinstance(relative_value, str) or not relative_value:
            gate.errors.append(f"{label}: missing path_relative_to_megalib")
            return None
        relative = Path(relative_value)
        gate.require(
            not relative.is_absolute() and ".." not in relative.parts,
            f"{label}: unsafe MEGAlib-relative path",
        )
        expected_logical = f"$(MEGALIB)/{relative.as_posix()}"
        gate.require(
            logical == expected_logical
            and row.get("include_token") == expected_logical,
            f"{label}: MEGAlib logical/include identity mismatch",
        )
        path = (gate.megalib_root / relative).resolve()
        try:
            path.relative_to(gate.megalib_root)
        except ValueError:
            gate.errors.append(f"{label}: MEGAlib path escapes its root")
        return path
    gate.errors.append(f"{label}: unsupported geometry scope {scope!r}")
    return None


def validate_geometry_bundle(
    gate: Gate,
    package: dict[str, Any],
    *,
    label: str,
) -> tuple[Path | None, dict[str, Any]]:
    """Re-hash and independently traverse one recursive geometry bundle."""
    bundle = package.get("geometry_bundle")
    if not isinstance(bundle, dict):
        gate.errors.append(f"{label}.geometry_bundle must be an object")
        return None, {"files": 0, "bundle_sha256": None}
    gate.require(
        bundle.get("bundle_algorithm") == GEOMETRY_BUNDLE_ALGORITHM,
        f"{label}: geometry bundle algorithm is missing or unsupported",
    )
    files = bundle.get("files")
    if not isinstance(files, list):
        gate.errors.append(f"{label}.geometry_bundle.files must be an array")
        return None, {"files": 0, "bundle_sha256": None}
    gate.require(
        bundle.get("entry_count") == len(files) and len(files) >= 3,
        f"{label}: geometry bundle entry_count mismatch",
    )

    identities: list[tuple[str, str]] = []
    rows_by_identity: dict[tuple[str, str], dict[str, Any]] = {}
    paths_by_identity: dict[tuple[str, str], Path] = {}
    actual_hashes: dict[tuple[str, str], str] = {}
    roles: Counter[str] = Counter()
    for index, row in enumerate(files):
        row_label = f"{label}.geometry_bundle.files[{index}]"
        if not isinstance(row, dict):
            gate.errors.append(f"{row_label}: entry must be an object")
            continue
        scope = row.get("scope")
        logical = row.get("logical_path")
        if not isinstance(scope, str) or not isinstance(logical, str):
            gate.errors.append(f"{row_label}: scope/logical_path must be strings")
            continue
        identity = (scope, logical)
        identities.append(identity)
        gate.require(
            identity not in rows_by_identity,
            f"{row_label}: duplicate scope/logical_path identity",
        )
        rows_by_identity[identity] = row
        role = row.get("role")
        if isinstance(role, str):
            roles[role] += 1
        else:
            gate.errors.append(f"{row_label}: role is missing")
        path = _geometry_bundle_path(gate, row, label=row_label)
        if path is None:
            continue
        paths_by_identity[identity] = path
        if not gate.require(path.is_file(), f"{row_label}: geometry file is missing: {path}"):
            continue
        gate.require(not path.is_symlink(), f"{row_label}: geometry bundle files must not be symlinks")
        actual_hash = sha256(path)
        actual_hashes[identity] = actual_hash
        gate.require(
            row.get("sha256") == actual_hash,
            f"{row_label}: geometry file SHA-256 mismatch",
        )
        gate.require(
            row.get("size_bytes") == path.stat().st_size,
            f"{row_label}: geometry file size mismatch",
        )
        try:
            path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            gate.errors.append(f"{row_label}: geometry file is not readable UTF-8: {exc}")

    gate.require(
        identities == sorted(identities),
        f"{label}: geometry bundle files are not deterministically sorted",
    )
    gate.require(
        len(rows_by_identity) == len(files),
        f"{label}: geometry bundle identities are not unique",
    )
    gate.require(roles["setup"] == 1, f"{label}: geometry bundle must have one setup")
    gate.require(
        roles["direct_geometry"] == 1,
        f"{label}: geometry bundle must have one direct geometry",
    )
    gate.require(
        roles["direct_detector"] == 1,
        f"{label}: geometry bundle must have one direct detector",
    )
    external_count = sum(scope != "repository" for scope, _ in identities)
    gate.require(
        bundle.get("external_include_count") == external_count,
        f"{label}: external_include_count mismatch",
    )

    digest_payload = "".join(
        f"{scope}\t{logical}\t{actual_hashes.get((scope, logical), '')}\n"
        for scope, logical in sorted(rows_by_identity)
    ).encode("utf-8")
    actual_bundle_hash = hashlib.sha256(digest_payload).hexdigest()
    gate.require(
        len(actual_hashes) == len(files),
        f"{label}: not every geometry bundle file could be hashed",
    )
    gate.require(
        bundle.get("bundle_sha256") == actual_bundle_hash,
        f"{label}: recursive geometry bundle SHA-256 mismatch",
    )
    gate.require(
        package.get("geometry_bundle_sha256") == actual_bundle_hash,
        f"{label}: package geometry_bundle_sha256 mismatch",
    )

    role_to_identity: dict[str, tuple[str, str]] = {}
    for identity, row in rows_by_identity.items():
        role = row.get("role")
        if role in {"setup", "direct_geometry", "direct_detector"}:
            role_to_identity[str(role)] = identity
    nested_names = {
        "setup_file": "setup",
        "geometry_file": "direct_geometry",
        "detector_file": "direct_detector",
    }
    for nested_name, role in nested_names.items():
        nested = bundle.get(nested_name)
        identity = role_to_identity.get(role)
        nested_label = f"{label}.geometry_bundle.{nested_name}"
        if not isinstance(nested, dict) or identity is None:
            gate.errors.append(f"{nested_label}: missing identity")
            continue
        row = rows_by_identity[identity]
        expected_path = row.get("path")
        gate.require(
            nested.get("path") == expected_path
            and nested.get("sha256") == row.get("sha256")
            and nested.get("size_bytes") == row.get("size_bytes"),
            f"{nested_label}: identity disagrees with files inventory",
        )

    setup_identity = role_to_identity.get("setup")
    setup_path = paths_by_identity.get(setup_identity) if setup_identity else None
    declared_setup = gate.resolve(
        package.get("geometry_setup"), label=f"{label}.geometry_setup"
    )
    gate.require(
        setup_path is not None and declared_setup == setup_path,
        f"{label}: geometry_setup does not resolve to bundle setup_file",
    )

    # Independently traverse every Include from the setup.  This makes a
    # manifest that omits or adds a transitive file fail even if its own digest
    # is internally self-consistent.
    visited: set[tuple[str, str]] = set()
    pending: list[tuple[str, str]] = [setup_identity] if setup_identity else []
    while pending:
        identity = pending.pop(0)
        if identity in visited:
            continue
        visited.add(identity)
        path = paths_by_identity.get(identity)
        if path is None or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            match = INCLUDE_RE.match(line)
            if match is None:
                continue
            token = match.group("target").strip('"\'')
            if token.startswith("$(MEGALIB)/"):
                relative = token.removeprefix("$(MEGALIB)/")
                child_identity = ("megalib", token)
                child_path = (gate.megalib_root / relative).resolve()
            elif "$(" in token:
                gate.errors.append(
                    f"{label}: unsupported include variable at {identity[1]}:{line_number}"
                )
                continue
            else:
                child_path = (path.parent / token).resolve()
                try:
                    logical = child_path.relative_to(
                        gate.repository_root
                    ).as_posix()
                except ValueError:
                    gate.errors.append(
                        f"{label}: repository Include escapes root at {identity[1]}:{line_number}"
                    )
                    continue
                child_identity = ("repository", logical)
            gate.require(
                child_identity in rows_by_identity,
                f"{label}: transitive Include missing from bundle: {child_identity[1]}",
            )
            gate.require(
                paths_by_identity.get(child_identity) == child_path,
                f"{label}: Include path resolution disagrees with bundle: {child_identity[1]}",
            )
            child_row = rows_by_identity.get(child_identity)
            if child_row is not None:
                if identity == setup_identity and child_path.suffix == ".geo":
                    expected_role = "direct_geometry"
                elif identity == setup_identity and child_path.suffix == ".det":
                    expected_role = "direct_detector"
                elif child_identity[0] == "megalib":
                    expected_role = "transitive_megalib"
                else:
                    expected_role = "transitive_repository"
                gate.require(
                    child_row.get("role") == expected_role,
                    f"{label}: wrong role for Include {child_identity[1]}",
                )
            if child_identity not in visited:
                pending.append(child_identity)
    gate.require(
        visited == set(rows_by_identity),
        f"{label}: geometry bundle inventory is not exactly the recursive Include closure",
    )
    return setup_path, {
        "files": len(files),
        "external_files": external_count,
        "bundle_sha256": actual_bundle_hash,
    }


def _solid_angle(beam: tuple[Decimal, Decimal, Decimal, Decimal]) -> float:
    theta_min, theta_max, phi_min, phi_max = map(float, beam)
    return math.radians(phi_max - phi_min) * (
        math.cos(math.radians(theta_min)) - math.cos(math.radians(theta_max))
    )


def _validate_card_semantics(
    gate: Gate,
    family: str,
    source: ParsedCard,
    parent: ParsedCard,
    expected_geometry: Path | None,
    spectra: dict[tuple[str, int], Path],
    flux_by_bin: dict[tuple[str, int], Decimal],
    *,
    label: str,
) -> int:
    gate.require(source.active_contract == parent.active_contract, f"{label}: active directives differ from parent beyond Spectrum paths")
    gate.require(source.geometry == parent.geometry, f"{label}: Geometry differs from parent")
    if expected_geometry is not None:
        actual_geometry = gate.resolve(source.geometry, label=f"{label}.Geometry")
        gate.require(actual_geometry == expected_geometry, f"{label}: Geometry does not match package manifest")
        gate.require(expected_geometry.is_file(), f"{label}: Geometry file does not exist: {expected_geometry}")
    gate.require(source.radius_cm == parent.radius_cm == Decimal("60"), f"{label}: farfield radius is not retained at R=60 cm")
    gate.require(len(source.definitions) == 20, f"{label}: expected 20 source definitions, found {len(source.definitions)}")
    gate.require(set(source.definitions) == set(parent.definitions), f"{label}: source-name set differs from parent")
    gate.require(len(source.run_sources) == 20 and len(set(source.run_sources)) == 20, f"{label}: Run must reference 20 unique angular sources")
    gate.require(set(source.run_sources) == set(source.definitions), f"{label}: Run source list and definitions differ")
    gate.require(source.run_sources == parent.run_sources, f"{label}: Run source order/list differs from parent")

    seen_bins: set[int] = set()
    solid_angles: list[float] = []
    for name, definition in source.definitions.items():
        parent_definition = parent.definitions.get(name)
        if parent_definition is not None:
            gate.require(definition.particle_type == parent_definition.particle_type, f"{label}:{name}: ParticleType differs from parent")
            gate.require(definition.beam == parent_definition.beam, f"{label}:{name}: Beam differs from parent")
            gate.require(definition.flux == parent_definition.flux, f"{label}:{name}: Flux differs from parent")
        gate.require(definition.particle_type == PARTICLE_TYPES[family], f"{label}:{name}: unexpected ParticleType {definition.particle_type}")
        bin_match = BIN_RE.search(name)
        if not bin_match:
            gate.errors.append(f"{label}:{name}: cannot identify angular bin")
            continue
        bin_id = int(bin_match.group(1))
        gate.require(bin_id not in seen_bins, f"{label}: duplicate bin {bin_id:02d}")
        seen_bins.add(bin_id)
        spectrum_path = gate.resolve(definition.spectrum, label=f"{label}:{name}.Spectrum")
        expected_spectrum = spectra.get((family, bin_id))
        gate.require(LEGACY_MARKER not in definition.spectrum, f"{label}:{name}: legacy 2602units reference is forbidden")
        gate.require(expected_spectrum is not None and spectrum_path == expected_spectrum, f"{label}:{name}: Spectrum does not resolve to the manifest-corrected file")
        retained_flux = flux_by_bin.get((family, bin_id))
        if retained_flux is not None:
            relative_delta = abs(definition.flux - retained_flux) / retained_flux
            gate.require(relative_delta <= Decimal("1e-12"), f"{label}:{name}: Flux differs from retained manifest.csv (relative delta {relative_delta})")
        theta_min, theta_max, phi_min, phi_max = map(float, definition.beam)
        gate.require(0.0 <= theta_min < theta_max <= 180.0, f"{label}:{name}: invalid theta bounds")
        gate.require(phi_min == 0.0 and phi_max == 360.0, f"{label}:{name}: phi bounds must be 0..360 deg")
        solid_angles.append(_solid_angle(definition.beam))

    gate.require(seen_bins == set(range(20)), f"{label}: source bins are not exactly 00..19")
    if solid_angles:
        expected_bin = 4.0 * math.pi / 20.0
        gate.require(max(abs(value - expected_bin) for value in solid_angles) <= 1.0e-4, f"{label}: angular bins are not equal-mu within source-card precision")
        gate.require(abs(math.fsum(solid_angles) - 4.0 * math.pi) <= 1.0e-10, f"{label}: angular coverage does not close to 4pi")
    return len(source.definitions)


def validate_geometries(
    gate: Gate,
    manifest: dict[str, Any],
    manifest_path: Path,
    spectra: dict[tuple[str, int], Path],
    flux_by_bin: dict[tuple[str, int], Decimal],
) -> dict[str, Any]:
    geometries = manifest.get("geometries")
    if not isinstance(geometries, dict):
        gate.errors.append("manifest.geometries must be an object")
        return {"cards": 0, "spectrum_references": 0}
    gate.require(set(geometries) == set(GEOMETRIES), f"manifest geometries must be exactly {list(GEOMETRIES)}")
    manifest_digest = sha256(manifest_path) if manifest_path.is_file() else ""
    card_count = 0
    reference_count = 0
    legacy_count = 0
    package_summary: dict[str, Any] = {}

    for geometry_key in GEOMETRIES:
        package = geometries.get(geometry_key)
        label = f"geometries.{geometry_key}"
        if not isinstance(package, dict):
            gate.errors.append(f"{label}: missing package object")
            continue
        gate.require(finite_number(package.get("farfield_radius_cm")) and float(package["farfield_radius_cm"]) == 60.0, f"{label}: farfield_radius_cm must be 60")
        parent_dir = gate.resolve(package.get("parent_source_dir"), label=f"{label}.parent_source_dir")
        source_dir = gate.resolve(package.get("source_dir"), label=f"{label}.source_dir")
        declared_geometry_path = gate.resolve(package.get("geometry_setup"), label=f"{label}.geometry_setup")
        bundle_setup, bundle_summary = validate_geometry_bundle(
            gate, package, label=label
        )
        geometry_path = bundle_setup or declared_geometry_path
        if parent_dir is not None:
            gate.require(parent_dir.is_dir(), f"{label}: parent source directory is missing")
        if source_dir is not None:
            gate.require(source_dir.is_dir(), f"{label}: corrected source directory is missing")
        if parent_dir is not None and source_dir is not None:
            gate.require(parent_dir != source_dir, f"{label}: refusing an in-place parent source edit")
        cards = package.get("cards")
        if not isinstance(cards, list):
            gate.errors.append(f"{label}.cards must be an array")
            continue
        gate.require(len(cards) == 8, f"{label}: expected 8 cards, found {len(cards)}")
        family_rows: dict[str, dict[str, Any]] = {}
        family_sources: dict[str, Path] = {}
        family_parents: dict[str, Path] = {}
        parsed_flux: dict[str, float] = {}

        for card_index, row in enumerate(cards):
            card_label = f"{label}.cards[{card_index}]"
            if not isinstance(row, dict):
                gate.errors.append(f"{card_label}: entry must be an object")
                continue
            family = row.get("family")
            if family not in FAMILIES:
                gate.errors.append(f"{card_label}: invalid family {family!r}")
                continue
            gate.require(family not in family_rows, f"{card_label}: duplicate family {family}")
            family_rows[family] = row
            source_path = gate.resolve(row.get("source"), label=f"{card_label}.source")
            parent_path = gate.resolve(row.get("parent_source"), label=f"{card_label}.parent_source")
            if source_path is not None:
                family_sources[family] = source_path
            if parent_path is not None:
                family_parents[family] = parent_path
            gate.check_hash(source_path, row.get("source_sha256"), label=f"{card_label}.source")
            gate.check_hash(parent_path, row.get("parent_sha256"), label=f"{card_label}.parent")
            gate.require(row.get("spectrum_references") == 20, f"{card_label}: manifest spectrum_references must be 20")
            gate.require(row.get("flux_entries") == 20, f"{card_label}: manifest flux_entries must be 20")
            gate.require(row.get("geometry_line_count") == 1, f"{card_label}: manifest geometry_line_count must be 1")
            geometry_lines = row.get("geometry_lines")
            if isinstance(geometry_lines, list) and len(geometry_lines) == 1:
                declared_card_geometry = gate.resolve(geometry_lines[0], label=f"{card_label}.geometry_lines[0]")
                gate.require(declared_card_geometry == geometry_path, f"{card_label}: manifest geometry_lines disagrees with package geometry")
            else:
                gate.errors.append(f"{card_label}: manifest geometry_lines must contain one path")
            if source_dir is not None and source_path is not None:
                gate.require(source_path.parent == source_dir, f"{card_label}: source is outside declared source_dir")
            if parent_dir is not None and parent_path is not None:
                gate.require(parent_path.parent == parent_dir, f"{card_label}: parent is outside declared parent_source_dir")
            if source_path is None or parent_path is None or not source_path.is_file() or not parent_path.is_file():
                continue
            try:
                parsed_source = parse_source_card(source_path)
                parsed_parent = parse_source_card(parent_path)
            except (OSError, UnicodeError, ValueError) as exc:
                gate.errors.append(f"{card_label}: source-card parse failure: {exc}")
                continue
            references = _validate_card_semantics(
                gate,
                family,
                parsed_source,
                parsed_parent,
                geometry_path,
                spectra,
                flux_by_bin,
                label=card_label,
            )
            reference_count += references
            declared_spectrum_files = row.get("spectrum_files")
            if isinstance(declared_spectrum_files, list):
                declared_spectra = {
                    path
                    for item_index, item in enumerate(declared_spectrum_files)
                    if (path := gate.resolve(item, label=f"{card_label}.spectrum_files[{item_index}]")) is not None
                }
                actual_spectra = {
                    path
                    for source_name, definition in parsed_source.definitions.items()
                    if (path := gate.resolve(definition.spectrum, label=f"{card_label}:{source_name}.Spectrum")) is not None
                }
                gate.require(len(declared_spectrum_files) == 20 and declared_spectra == actual_spectra, f"{card_label}: manifest spectrum_files differs from the 20 card references")
            else:
                gate.errors.append(f"{card_label}: manifest spectrum_files must be an array")
            legacy_count += sum(LEGACY_MARKER in item.spectrum for item in parsed_source.definitions.values())
            flux_sum = float(sum((item.flux for item in parsed_source.definitions.values()), Decimal(0)))
            parsed_flux[family] = flux_sum
            if finite_number(row.get("flux_sum_cm2_s")):
                gate.require(close(float(row["flux_sum_cm2_s"]), flux_sum, rel=1.0e-12), f"{card_label}: manifest flux_sum_cm2_s mismatch")
            else:
                gate.errors.append(f"{card_label}: missing/non-finite flux_sum_cm2_s")
            card_count += 1

        gate.require(set(family_rows) == set(FAMILIES), f"{label}: card families are not exactly the eight-family set")
        if source_dir is not None and source_dir.is_dir():
            actual_cards = set(source_dir.glob("Background_*_fullsphere20.source"))
            gate.require(actual_cards == set(family_sources.values()), f"{label}: source_dir card inventory differs from manifest")
            package_manifest_path = source_dir / "source_migration_manifest.json"
            package_manifest = gate.read_json(package_manifest_path, label=f"{label}.source_migration_manifest")
            if package_manifest is not None:
                gate.require(package_manifest.get("schema_version") == 1, f"{label}: package manifest schema_version must be 1")
                gate.require(package_manifest.get("problems") == [], f"{label}: package manifest problems must be empty")
                gate.require(finite_number(package_manifest.get("farfield_radius_cm")) and float(package_manifest["farfield_radius_cm"]) == 60.0, f"{label}: package manifest radius must be 60")
                manifest_ref = gate.resolve(package_manifest.get("source_contract_manifest_path"), label=f"{label}.source_contract_manifest_path")
                gate.require(manifest_ref == manifest_path.resolve(), f"{label}: package manifest points to the wrong global contract")
                gate.require(package_manifest.get("source_contract_manifest_sha256") == manifest_digest, f"{label}: package manifest global-contract SHA-256 mismatch")
                gate.require(
                    package_manifest.get("geometry_bundle")
                    == package.get("geometry_bundle"),
                    f"{label}: package manifest geometry_bundle differs from global contract",
                )
                gate.require(
                    package_manifest.get("geometry_bundle_sha256")
                    == package.get("geometry_bundle_sha256")
                    == bundle_summary.get("bundle_sha256"),
                    f"{label}: package manifest geometry bundle SHA-256 mismatch",
                )
                for key, expected_path in (
                    ("source_dir", source_dir),
                    ("parent_source_dir", parent_dir),
                    ("geometry_setup", geometry_path),
                ):
                    declared = gate.resolve(package_manifest.get(key), label=f"{label}.source_migration_manifest.{key}")
                    gate.require(declared == expected_path, f"{label}: package manifest {key} disagrees with global contract")
                source_rows = package_manifest.get("sources")
                if not isinstance(source_rows, list):
                    gate.errors.append(f"{label}: package manifest sources must be an array")
                else:
                    gate.require(len(source_rows) == 8, f"{label}: package manifest must inventory 8 sources")
                    by_family = {
                        row.get("particle"): row
                        for row in source_rows
                        if isinstance(row, dict) and row.get("particle") in FAMILIES
                    }
                    gate.require(set(by_family) == set(FAMILIES), f"{label}: package-manifest particles are incomplete")
                    for family, source_row in by_family.items():
                        row_label = f"{label}.source_migration_manifest.sources[{family}]"
                        gate.require(source_row.get("problems") == [], f"{row_label}: problems must be empty")
                        gate.require(source_row.get("canonical_non_spectrum_fields_preserved") is True, f"{row_label}: canonical non-spectrum preservation flag must be true")
                        gate.require(source_row.get("geometry_line_count") == 1, f"{row_label}: geometry_line_count must be 1")
                        row_geometry_lines = source_row.get("geometry_lines")
                        if isinstance(row_geometry_lines, list) and len(row_geometry_lines) == 1:
                            row_geometry = gate.resolve(row_geometry_lines[0], label=f"{row_label}.geometry_lines[0]")
                            gate.require(row_geometry == geometry_path, f"{row_label}: geometry_lines disagrees with package geometry")
                        else:
                            gate.errors.append(f"{row_label}: geometry_lines must contain one path")
                        declared_source = gate.resolve(source_row.get("source"), label=f"{row_label}.source")
                        declared_parent = gate.resolve(source_row.get("parent_source"), label=f"{row_label}.parent_source")
                        gate.require(declared_source == family_sources.get(family), f"{row_label}: source path mismatch")
                        gate.require(declared_parent == family_parents.get(family), f"{row_label}: parent path mismatch")
                        if declared_source is not None:
                            gate.check_hash(declared_source, source_row.get("source_sha256"), label=f"{row_label}.source")
                        if declared_parent is not None:
                            gate.check_hash(declared_parent, source_row.get("parent_sha256"), label=f"{row_label}.parent")
                        refs = _count_field(source_row.get("spectrum_references"))
                        gate.require(refs == 20, f"{row_label}: spectrum_references must count 20")
                        row_spectrum_files = source_row.get("spectrum_files")
                        if isinstance(row_spectrum_files, list):
                            declared = {
                                path
                                for item_index, item in enumerate(row_spectrum_files)
                                if (path := gate.resolve(item, label=f"{row_label}.spectrum_files[{item_index}]")) is not None
                            }
                            expected = {spectra[(family, bin_id)] for bin_id in range(20) if (family, bin_id) in spectra}
                            gate.require(len(row_spectrum_files) == 20 and declared == expected, f"{row_label}: spectrum_files must match the 20 corrected spectra")
                        else:
                            gate.errors.append(f"{row_label}: spectrum_files must be an array")
                        legacy_refs = _count_field(source_row.get("legacy_2602unit_references"))
                        if legacy_refs is not None:
                            gate.require(legacy_refs == 0, f"{row_label}: legacy reference count must be zero")
                        corrected_refs = _count_field(source_row.get("corrected_keV_references"))
                        if corrected_refs is not None:
                            gate.require(corrected_refs == 20, f"{row_label}: corrected reference count must be 20")
                        if "total_flux_cm2_s" in source_row and family in parsed_flux:
                            gate.require(close(float(source_row["total_flux_cm2_s"]), parsed_flux[family], rel=1.0e-12), f"{row_label}: total flux mismatch")

        package_summary[geometry_key] = {
            "cards": len(family_rows),
            "geometry_bundle": bundle_summary,
            "spectrum_references": 20 * len(family_rows),
            "legacy_references": sum(
                1
                for source_path in family_sources.values()
                if source_path.is_file()
                for _ in re.finditer(LEGACY_MARKER, source_path.read_text(encoding="utf-8", errors="replace"))
            ),
        }

    gate.require(card_count == 24, f"expected 24 validated source cards, found {card_count}")
    gate.require(reference_count == 480, f"expected exactly 480 corrected spectrum references, found {reference_count}")
    gate.require(legacy_count == 0, f"expected zero legacy spectrum references, found {legacy_count}")
    return {
        "cards": card_count,
        "spectrum_references": reference_count,
        "legacy_references": legacy_count,
        "packages": package_summary,
    }


def run_validation(
    package_root: Path = PACKAGE,
    repository_root: Path = REPOSITORY,
    manifest_path: Path | None = None,
    megalib_root: Path | None = None,
) -> dict[str, Any]:
    """Validate the package without writing any files and return a JSON-ready result."""
    package_root = package_root.resolve()
    repository_root = repository_root.resolve()
    if megalib_root is None:
        megalib_root = Path(
            os.environ.get("MEGALIB", str(DEFAULT_MEGALIB_ROOT))
        )
    if manifest_path is None:
        manifest_path = package_root / MANIFEST_RELATIVE
    elif not manifest_path.is_absolute():
        manifest_path = package_root / manifest_path
    manifest_path = manifest_path.resolve()
    gate = Gate(package_root, repository_root, megalib_root)
    manifest = gate.read_json(manifest_path, label="source contract manifest")
    report: dict[str, Any] = {
        "schema_version": 1,
        "validator": "validate_corrected_source_package.py",
        "mode": "static_fail_closed",
        "source_contract_manifest": str(manifest_path),
    }
    if manifest is None:
        report.update(status="FAIL", errors=gate.errors)
        return report

    gate.require(manifest.get("schema_version") == 1, "manifest schema_version must be 1")
    gate.require(manifest.get("families") == list(FAMILIES), f"manifest families must be exactly {list(FAMILIES)}")
    gate.require(manifest.get("bins_per_family") == 20, "manifest bins_per_family must be 20")
    gate.require(finite_number(manifest.get("farfield_radius_cm")) and float(manifest["farfield_radius_cm"]) == 60.0, "manifest farfield_radius_cm must be 60")
    energy_contract = manifest.get("energy_contract")
    if not isinstance(energy_contract, dict):
        gate.errors.append("manifest.energy_contract must be an object")
    else:
        gate.require(energy_contract.get("output_energy_unit") == "keV_total", "energy_contract.output_energy_unit must be keV_total")
        scale_map = energy_contract.get("family_energy_scale_to_total_keV")
        gate.require(
            isinstance(scale_map, dict)
            and set(scale_map) == set(FAMILIES)
            and all(finite_number(scale_map.get(family)) and float(scale_map[family]) == ENERGY_SCALES[family] for family in FAMILIES),
            "energy_contract family scale map must be alpha=4000 and every non-alpha family=1000",
        )
        alpha_contract = energy_contract.get("alpha")
        non_alpha_contract = energy_contract.get("non_alpha")
        gate.require(isinstance(alpha_contract, dict) and alpha_contract.get("energy_scale_to_total_keV") == 4000.0, "energy_contract.alpha scale must be 4000")
        gate.require(isinstance(non_alpha_contract, dict) and non_alpha_contract.get("energy_scale_to_total_keV") == 1000.0, "energy_contract.non_alpha scale must be 1000")
    additive_values = _recursive_values(manifest.get("policies", {}), "additive_mono_511_allowed")
    gate.require(bool(additive_values) and all(value is False for value in additive_values), "policy additive_mono_511_allowed=false is required")
    policies = manifest.get("policies")
    if isinstance(policies, dict):
        gate.require(policies.get("source_card_flux_values_preserved") is True, "policy source_card_flux_values_preserved=true is required")
        gate.require(policies.get("parent_inputs_mutated") is False, "policy parent_inputs_mutated=false is required")
    source_model = manifest.get("source_model", {})
    manifest_text = json.dumps(source_model, sort_keys=True).lower()
    gate.require("broadband" in manifest_text and "total" in manifest_text, "source_model must explicitly identify retained broadband-total gamma")
    if isinstance(source_model, dict):
        gate.require(source_model.get("profile") == "unit_only_total_gamma", "source_model.profile must be unit_only_total_gamma")
        gate.require(source_model.get("gamma_component") == "broadband_total", "source_model.gamma_component must be broadband_total")

    flux_by_bin = validate_input_provenance(gate, manifest)
    spectra, spectra_summary = validate_spectra(gate, manifest)
    geometry_summary = validate_geometries(gate, manifest, manifest_path, spectra, flux_by_bin)
    report.update(
        status="PASS" if not gate.errors else "FAIL",
        source_contract_manifest_sha256=sha256(manifest_path),
        spectra=spectra_summary,
        source_packages=geometry_summary,
        errors=gate.errors,
    )
    return report


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", type=Path, default=PACKAGE)
    parser.add_argument("--repository-root", type=Path, default=REPOSITORY)
    parser.add_argument(
        "--megalib-root",
        type=Path,
        default=Path(os.environ.get("MEGALIB", str(DEFAULT_MEGALIB_ROOT))),
    )
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--check", action="store_true", help="validate read-only; never write static_validation.json")
    args = parser.parse_args(argv)

    try:
        report = run_validation(
            args.package_root,
            args.repository_root,
            args.manifest,
            args.megalib_root,
        )
    except Exception as exc:  # A validator crash is a validation failure, never a pass.
        report = {
            "schema_version": 1,
            "validator": "validate_corrected_source_package.py",
            "mode": "static_fail_closed",
            "status": "FAIL",
            "errors": [f"unexpected validator failure: {type(exc).__name__}: {exc}"],
        }
    if not args.check:
        write_report(args.package_root.resolve() / REPORT_RELATIVE, report)
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if report.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
