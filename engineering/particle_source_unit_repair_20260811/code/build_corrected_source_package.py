#!/usr/bin/env python3
"""Build the fail-closed corrected-keV particle-source package.

The retained EXPACS/PARMA tables use MeV for seven particle families and
MeV/nucleon for alpha particles.  Cosima's ``Spectrum File`` energy axis is
total kinetic energy in keV, so the conversion is E*1000 for non-alpha
families and E*4000 for alpha particles.  The source-card Flux values are
already correct and are deliberately left byte-for-byte unchanged.

This builder never edits retained inputs and never launches Cosima.  Normal
builds use only the package-owned ``.raw-spectrum`` baseline.  The ignored
global ``raw_expacs/*.dat`` files can be read only through the explicit,
first-use-only ``--bootstrap-raw-snapshots`` mode.  Every derived artifact is
rendered in memory and the default mode refuses to overwrite differing
content.  ``--check`` is a strict, read-only comparison.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parents[1]
RAW_ROOT = PACKAGE / "input/raw_expacs"
RAW_EVIDENCE_LEDGER = PACKAGE / "input/source_unit_audit_evidence_hashes.csv"
BOOTSTRAP_RAW_ROOT = ROOT / "expacs_fullsphere_20bin_sources/raw_expacs"
FLUX_MANIFEST = ROOT / "expacs_fullsphere_20bin_sources/manifest.csv"
FLUX_CLOSURE_AUDIT = ROOT / "expacs_fullsphere_20bin_sources/flux_closure_audit.csv"
EXPACS_WORKBOOK = ROOT / "expacs_fullsphere_20bin_sources/_workbook/EXPACS-eng.xlsx"
SPECTRUM_ROOT = PACKAGE / "spectra/correct_keV_total"
SOURCE_CARD_ROOT = PACKAGE / "config/source_cards"
CONTRACT_MANIFEST = PACKAGE / "data/source_contract_manifest.json"
DEFAULT_MEGALIB_ROOT = Path("/home/ubuntu/MEGAlib_Install/megalib-main")
EXPECTED_RAW_EVIDENCE_LEDGER_SHA256 = (
    "2f103de0c90408d3d2f62f8961030f4f1732d64b4b20f1685dd2fa15b61ca41c"
)

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
BINS_PER_FAMILY = 20
FARFIELD_RADIUS_CM = 60.0

PARENT_SOURCE_DIRS = {
    "mass_model_511": ROOT
    / "engineering/Mass_model_511_nearfield_migration_20260701/03_source_migration/source_dirs/Mass_model_511",
    "s3c_c0": ROOT
    / "engineering/geometry_optimization_20260704/32_s3c_dominant_backgrounds_20260709/source_cards",
    "s3d_o8": ROOT
    / "engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/config/full_prompt_all8/source_cards",
}

RAW_NAME_RE = re.compile(
    r"^spectrum_(?P<family>[a-z]+)_bin(?P<bin>\d{2})_"
    r"theta(?P<theta>[0-9]+(?:\.[0-9]+)?)_BH(?P<black_hole>[^.]+)"
    r"(?P<suffix>\.dat|\.raw-spectrum)$"
)
INCLUDE_RE = re.compile(r"^\s*Include\s+(?P<target>\S+)\s*$")
SPECTRUM_LINE_RE = re.compile(
    r"^(?P<prefix>\s*\S+\.Spectrum\s+File\s+)(?P<path>\S+)(?P<suffix>\s*)$"
)
SPECTRUM_DIR_RE = re.compile(r"^\s*#\s*spectrum_dir=.*$")
GEOMETRY_RE = re.compile(r"^\s*Geometry\s+(?P<path>\S+)\s*$")
FLUX_RE = re.compile(r"\.Flux\s+([-+0-9.eE]+)\s*$")
BEAM_RE = re.compile(r"\.Beam\s+FarFieldAreaSource\s+")
BIN_FROM_REFERENCE_RE = re.compile(
    r"^(?P<family>[a-z]+)_bin(?P<bin>\d{2})_theta"
    r"(?P<theta>[0-9]+(?:\.[0-9]+)?)_pdf\.dat$"
)


@dataclass(frozen=True)
class Output:
    """One deterministic package artifact."""

    path: Path
    content: bytes
    kind: str


@dataclass(frozen=True)
class RawSpectrum:
    """Parsed retained spectrum and its file-level metadata."""

    path: Path
    family: str
    bin_id: str
    theta_label: str
    black_hole_mode: str
    metadata: dict[str, str]
    points: tuple[tuple[float, float], ...]


def repo_rel(path: Path) -> str:
    """Return a stable POSIX path relative to the repository root."""

    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise RuntimeError(f"path is outside repository root: {path}") from exc


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_bytes(payload: Any) -> bytes:
    """Canonical human-readable JSON used by every generated manifest."""

    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def trapz(points: Iterable[tuple[float, float]]) -> float:
    rows = tuple(points)
    return math.fsum(
        0.5 * (y0 + y1) * (x1 - x0)
        for (x0, y0), (x1, y1) in zip(rows, rows[1:])
    )


def snapshot_name(original_name: str) -> str:
    match = RAW_NAME_RE.match(original_name)
    if match is None or match.group("suffix") != ".dat":
        raise RuntimeError(f"unexpected bootstrap raw filename: {original_name}")
    return original_name.removesuffix(".dat") + ".raw-spectrum"


def load_original_raw_hash_evidence() -> dict[str, dict[str, Any]]:
    """Load the independently generated audit hashes for the 160 raw tables."""

    if not RAW_EVIDENCE_LEDGER.is_file() or RAW_EVIDENCE_LEDGER.is_symlink():
        raise RuntimeError(
            f"raw audit evidence ledger is missing: {repo_rel(RAW_EVIDENCE_LEDGER)}"
        )
    ledger_hash = sha256_file(RAW_EVIDENCE_LEDGER)
    if ledger_hash != EXPECTED_RAW_EVIDENCE_LEDGER_SHA256:
        raise RuntimeError(
            "raw audit evidence ledger hash changed: "
            f"{ledger_hash} != {EXPECTED_RAW_EVIDENCE_LEDGER_SHA256}"
        )
    with RAW_EVIDENCE_LEDGER.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required_fields = {"source", "size_bytes", "sha256"}
    if not rows or not required_fields.issubset(rows[0]):
        raise RuntimeError("raw audit evidence ledger schema is invalid")

    expected_parent = repo_rel(BOOTSTRAP_RAW_ROOT)
    evidence: dict[str, dict[str, Any]] = {}
    for row in rows:
        source = row.get("source", "")
        source_path = Path(source)
        if source_path.parent.as_posix() != expected_parent:
            continue
        name = source_path.name
        match = RAW_NAME_RE.match(name)
        if match is None or match.group("suffix") != ".dat":
            raise RuntimeError(f"invalid raw audit evidence path: {source}")
        if name in evidence:
            raise RuntimeError(f"duplicate raw audit evidence row: {source}")
        try:
            size_bytes = int(row["size_bytes"])
        except (KeyError, ValueError) as exc:
            raise RuntimeError(f"invalid raw audit evidence size: {source}") from exc
        digest = row.get("sha256", "")
        if size_bytes <= 0 or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise RuntimeError(f"invalid raw audit evidence identity: {source}")
        evidence[name] = {
            "original_raw_path": source,
            "original_raw_sha256": digest,
            "original_raw_size_bytes": size_bytes,
        }
    expected_total = len(FAMILIES) * BINS_PER_FAMILY
    if len(evidence) != expected_total:
        raise RuntimeError(
            f"raw audit evidence closure failed: {len(evidence)} != {expected_total}"
        )
    return evidence


def bootstrap_raw_snapshots() -> int:
    """Freeze ignored global raw tables into a trackable package directory.

    This is the only code path allowed to read ``BOOTSTRAP_RAW_ROOT``.  It is
    intentionally first-use-only: an existing snapshot directory, including
    a partial one, is never merged with another bootstrap source.
    """

    if RAW_ROOT.exists():
        raise RuntimeError(
            f"package raw snapshot directory already exists: {repo_rel(RAW_ROOT)}; "
            "bootstrap is first-use-only, so use the normal builder or --check"
        )
    if not BOOTSTRAP_RAW_ROOT.is_dir():
        raise RuntimeError(
            "explicit bootstrap source is missing: "
            f"{repo_rel(BOOTSTRAP_RAW_ROOT)}"
        )

    evidence = load_original_raw_hash_evidence()
    originals = sorted(BOOTSTRAP_RAW_ROOT.glob("spectrum_*.dat"))
    expected_total = len(FAMILIES) * BINS_PER_FAMILY
    if len(originals) != expected_total:
        raise RuntimeError(
            f"bootstrap requires exactly {expected_total} global raw spectra, "
            f"found {len(originals)}"
        )

    staged: list[tuple[str, bytes]] = []
    seen_keys: set[tuple[str, str]] = set()
    for original in originals:
        expected = evidence.get(original.name)
        if expected is None:
            raise RuntimeError(
                f"bootstrap raw is absent from audit evidence: {original.name}"
            )
        content = original.read_bytes()
        if (
            len(content) != expected["original_raw_size_bytes"]
            or sha256_bytes(content) != expected["original_raw_sha256"]
        ):
            raise RuntimeError(
                f"bootstrap raw differs from audit evidence: {original.name}"
            )
        parsed = parse_raw(original)
        key = (parsed.family, parsed.bin_id)
        if key in seen_keys:
            raise RuntimeError(f"duplicate bootstrap raw family/bin: {key}")
        seen_keys.add(key)
        staged.append((snapshot_name(original.name), content))
    expected_keys = {
        (family, f"{bin_number:02d}")
        for family in FAMILIES
        for bin_number in range(BINS_PER_FAMILY)
    }
    if seen_keys != expected_keys:
        raise RuntimeError(
            "bootstrap raw family/bin closure failed: "
            f"missing={sorted(expected_keys - seen_keys)}, "
            f"extra={sorted(seen_keys - expected_keys)}"
        )

    RAW_ROOT.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(
        tempfile.mkdtemp(prefix=".raw_expacs-bootstrap-", dir=RAW_ROOT.parent)
    )
    try:
        for name, content in staged:
            (stage / name).write_bytes(content)
        staged_files = sorted(path for path in stage.iterdir() if path.is_file())
        if len(staged_files) != expected_total:
            raise RuntimeError("staged raw snapshot inventory is incomplete")
        for path in staged_files:
            original = BOOTSTRAP_RAW_ROOT / (
                path.name.removesuffix(".raw-spectrum") + ".dat"
            )
            if path.read_bytes() != original.read_bytes():
                raise RuntimeError(
                    f"bootstrap byte-preservation check failed: {path.name}"
                )
        stage.rename(RAW_ROOT)
    except Exception:
        if stage.exists():
            shutil.rmtree(stage)
        raise
    return len(staged)


def parse_raw(path: Path) -> RawSpectrum:
    match = RAW_NAME_RE.match(path.name)
    if match is None:
        raise RuntimeError(f"unexpected raw spectrum filename: {repo_rel(path)}")

    metadata: dict[str, str] = {}
    points: list[tuple[float, float]] = []
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8", errors="strict").splitlines(), start=1
    ):
        stripped = raw_line.strip()
        if stripped.startswith("#"):
            comment = stripped[1:].strip()
            if "=" in comment:
                key, value = comment.split("=", 1)
                metadata[key.strip()] = value.strip()
            continue
        if not stripped:
            continue
        fields = stripped.split()
        if len(fields) != 2:
            raise RuntimeError(
                f"{repo_rel(path)}:{line_number}: expected two numeric columns"
            )
        try:
            energy, density = map(float, fields)
        except ValueError as exc:
            raise RuntimeError(
                f"{repo_rel(path)}:{line_number}: invalid numeric row"
            ) from exc
        if not math.isfinite(energy) or not math.isfinite(density):
            raise RuntimeError(
                f"{repo_rel(path)}:{line_number}: non-finite spectrum value"
            )
        points.append((energy, density))

    family = match.group("family")
    bin_id = match.group("bin")
    if family not in FAMILIES:
        raise RuntimeError(f"unsupported family in {repo_rel(path)}: {family}")
    if len(points) < 2:
        raise RuntimeError(f"raw spectrum has fewer than two points: {repo_rel(path)}")
    if any(x1 <= x0 for (x0, _), (x1, _) in zip(points, points[1:])):
        raise RuntimeError(f"energy axis is not strictly increasing: {repo_rel(path)}")
    if any(y < 0.0 for _, y in points):
        raise RuntimeError(f"negative flux density in raw spectrum: {repo_rel(path)}")
    if metadata.get("particle") != family:
        raise RuntimeError(
            f"filename/header family mismatch in {repo_rel(path)}: "
            f"{family!r} != {metadata.get('particle')!r}"
        )
    if metadata.get("bin") != bin_id:
        raise RuntimeError(
            f"filename/header bin mismatch in {repo_rel(path)}: "
            f"{bin_id!r} != {metadata.get('bin')!r}"
        )

    expected_unit = "MeV_per_nucleon" if family == "alpha" else "MeV"
    if metadata.get("energy_unit") != expected_unit:
        raise RuntimeError(
            f"unexpected raw energy unit in {repo_rel(path)}: "
            f"{metadata.get('energy_unit')!r}; expected {expected_unit!r}"
        )
    integral = trapz(points)
    if not math.isfinite(integral) or integral <= 0.0:
        raise RuntimeError(f"non-positive raw flux integral: {repo_rel(path)}")

    return RawSpectrum(
        path=path,
        family=family,
        bin_id=bin_id,
        theta_label=match.group("theta"),
        black_hole_mode=match.group("black_hole"),
        metadata=metadata,
        points=tuple(points),
    )


def load_raw_spectra() -> dict[tuple[str, str], RawSpectrum]:
    if not RAW_ROOT.is_dir():
        raise RuntimeError(
            f"package raw snapshot directory is missing: {repo_rel(RAW_ROOT)}; "
            "run once with --bootstrap-raw-snapshots on the retained workspace"
        )
    raw_paths = sorted(path for path in RAW_ROOT.iterdir() if path.is_file())
    expected_total = len(FAMILIES) * BINS_PER_FAMILY
    if len(raw_paths) != expected_total:
        raise RuntimeError(
            f"expected {expected_total} package raw snapshots, found {len(raw_paths)}"
        )

    spectra: dict[tuple[str, str], RawSpectrum] = {}
    for path in raw_paths:
        if path.is_symlink() or path.suffix != ".raw-spectrum":
            raise RuntimeError(
                f"unexpected package raw snapshot entry: {repo_rel(path)}"
            )
        parsed = parse_raw(path)
        key = (parsed.family, parsed.bin_id)
        if key in spectra:
            raise RuntimeError(f"duplicate raw family/bin: {key}")
        spectra[key] = parsed

    expected_keys = {
        (family, f"{bin_number:02d}")
        for family in FAMILIES
        for bin_number in range(BINS_PER_FAMILY)
    }
    missing = sorted(expected_keys - spectra.keys())
    extra = sorted(spectra.keys() - expected_keys)
    if missing or extra:
        raise RuntimeError(f"raw family/bin closure failed: missing={missing}, extra={extra}")
    return spectra


def unique_manifest_value(rows: list[dict[str, str]], field: str) -> str:
    values = {row.get(field, "") for row in rows}
    if len(values) != 1 or "" in values:
        raise RuntimeError(
            f"flux manifest field {field!r} is not uniquely populated: "
            f"{sorted(values)!r}"
        )
    return next(iter(values))


def load_input_context(
    raw_spectra: dict[tuple[str, str], RawSpectrum],
) -> tuple[dict[str, Any], dict[str, Any], dict[tuple[str, str], dict[str, Any]]]:
    """Validate and freeze the retained EXPACS/PARMA environment metadata."""

    raw_hash_evidence = load_original_raw_hash_evidence()
    required_files = (EXPACS_WORKBOOK, FLUX_MANIFEST, FLUX_CLOSURE_AUDIT)
    for path in required_files:
        if not path.is_file():
            raise RuntimeError(f"required source-provenance file is missing: {path}")

    with FLUX_MANIFEST.open(encoding="utf-8", newline="") as handle:
        manifest_rows = list(csv.DictReader(handle))
    expected_total = len(FAMILIES) * BINS_PER_FAMILY
    if len(manifest_rows) != expected_total:
        raise RuntimeError(
            f"flux manifest row closure failed: {len(manifest_rows)} != "
            f"{expected_total}"
        )
    manifest_family_bins = {
        (row["particle"], row["bin_id"]) for row in manifest_rows
    }
    if manifest_family_bins != set(raw_spectra):
        raise RuntimeError("flux manifest family/bin inventory does not close")

    original_mapping: dict[tuple[str, str], dict[str, Any]] = {}
    expected_original_root = repo_rel(BOOTSTRAP_RAW_ROOT)
    for row in manifest_rows:
        key = (row["particle"], row["bin_id"])
        original_path = row["raw_spectrum_path"]
        if Path(original_path).parent.as_posix() != expected_original_root:
            raise RuntimeError(
                f"unexpected original raw root for {key}: {original_path}"
            )
        expected_snapshot_name = snapshot_name(Path(original_path).name)
        snapshot = raw_spectra[key]
        if snapshot.path.name != expected_snapshot_name:
            raise RuntimeError(
                f"original/package raw mapping mismatch for {key}: "
                f"{original_path} -> {snapshot.path.name}"
            )
        evidence = raw_hash_evidence.get(Path(original_path).name)
        if evidence is None or evidence["original_raw_path"] != original_path:
            raise RuntimeError(
                f"original raw is absent from independent audit evidence: {original_path}"
            )
        snapshot_hash = sha256_file(snapshot.path)
        snapshot_size = snapshot.path.stat().st_size
        if (
            snapshot_hash != evidence["original_raw_sha256"]
            or snapshot_size != evidence["original_raw_size_bytes"]
        ):
            raise RuntimeError(
                f"package raw snapshot differs from independent audit evidence: "
                f"{repo_rel(snapshot.path)}"
            )
        original_mapping[key] = {
            "original_raw_path": original_path,
            "original_raw_sha256": evidence["original_raw_sha256"],
            "original_raw_size_bytes": evidence["original_raw_size_bytes"],
        }

    with FLUX_CLOSURE_AUDIT.open(encoding="utf-8", newline="") as handle:
        closure_rows = list(csv.DictReader(handle))
    closure_families = [row.get("particle") for row in closure_rows]
    if len(closure_rows) != len(FAMILIES) or set(closure_families) != set(FAMILIES):
        raise RuntimeError(
            "flux-closure family inventory does not match the eight-family contract"
        )

    w_or_date = unique_manifest_value(manifest_rows, "W_or_date")
    environment_match = re.fullmatch(
        r"(?P<date>\d{4}-\d{2}-\d{2});\s*W=(?P<w>[-+0-9.eE]+)",
        w_or_date,
    )
    if environment_match is None:
        raise RuntimeError(f"cannot parse manifest W_or_date value: {w_or_date!r}")
    environment = {
        "altitude_km": float(
            unique_manifest_value(manifest_rows, "expacs_altitude_km")
        ),
        "cutoff_rigidity_gv": float(
            unique_manifest_value(manifest_rows, "expacs_Rc_GV")
        ),
        "date": environment_match.group("date"),
        "latitude_deg": float(
            unique_manifest_value(manifest_rows, "expacs_lat_deg")
        ),
        "longitude_deg": float(
            unique_manifest_value(manifest_rows, "expacs_lon_deg")
        ),
        "solar_modulation_w": float(environment_match.group("w")),
    }

    inventory_digest = hashlib.sha256()
    for raw in sorted(raw_spectra.values(), key=lambda item: item.path.name):
        inventory_digest.update(raw.path.name.encode("utf-8"))
        inventory_digest.update(b"\t")
        inventory_digest.update(sha256_file(raw.path).encode("ascii"))
        inventory_digest.update(b"\n")
    provenance = {
        "independent_raw_hash_evidence": {
            "path": repo_rel(RAW_EVIDENCE_LEDGER),
            "sha256": EXPECTED_RAW_EVIDENCE_LEDGER_SHA256,
            "raw_entry_count": len(raw_hash_evidence),
            "source": (
                "frozen copy of particle_source_unit_audit_20260811/data/"
                "evidence_hashes.csv; normal build has no dependency on that audit package"
            ),
        },
        "expacs_workbook": {
            "path": repo_rel(EXPACS_WORKBOOK),
            "sha256": sha256_file(EXPACS_WORKBOOK),
        },
        "flux_closure_audit": {
            "path": repo_rel(FLUX_CLOSURE_AUDIT),
            "sha256": sha256_file(FLUX_CLOSURE_AUDIT),
        },
        "flux_manifest": {
            "path": repo_rel(FLUX_MANIFEST),
            "sha256": sha256_file(FLUX_MANIFEST),
        },
        "raw_spectrum_dir": {
            "count": len(raw_spectra),
            "inventory_algorithm": (
                "sha256 of sorted UTF-8 lines: relative_name<TAB>file_sha256<LF>"
            ),
            "inventory_sha256": inventory_digest.hexdigest(),
            "path": repo_rel(RAW_ROOT),
            "role": "package_owned_primary_raw_baseline",
            "snapshot_extension": ".raw-spectrum",
        },
        "raw_snapshot_bootstrap_source": {
            "normal_build_dependency": False,
            "path": expected_original_root,
            "policy": "read only by explicit --bootstrap-raw-snapshots",
        },
    }
    return environment, provenance, original_mapping


def parse_rendered_dp(content: bytes) -> tuple[tuple[float, float], ...]:
    points: list[tuple[float, float]] = []
    for line in content.decode("utf-8").splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[0] == "DP":
            points.append((float(fields[1]), float(fields[2])))
    if len(points) < 2:
        raise RuntimeError("rendered spectrum contains fewer than two DP rows")
    return tuple(points)


def render_spectrum(
    raw: RawSpectrum, original: dict[str, Any]
) -> tuple[bytes, dict[str, Any]]:
    energy_scale = 4000.0 if raw.family == "alpha" else 1000.0
    raw_integral = trapz(raw.points)
    corrected = tuple(
        (energy * energy_scale, density / (raw_integral * energy_scale))
        for energy, density in raw.points
    )

    output_name = (
        f"{raw.family}_bin{raw.bin_id}_theta{raw.theta_label}_pdf.spectrum"
    )
    output_path = SPECTRUM_ROOT / output_name
    lines = [
        "# Package-owned corrected Cosima differential-probability spectrum.",
        f"# raw_source={repo_rel(raw.path)}",
        f"# raw_energy_unit={raw.metadata['energy_unit']}",
        "# cosima_energy_unit=keV_total",
        f"# energy_scale_to_total_keV={energy_scale:.1f}",
        "# pdf_policy=unit trapezoidal integral on corrected total-keV axis",
    ]
    if raw.family == "gamma":
        lines.append(
            "# gamma_policy=retained broadband total; additive mono-511 forbidden"
        )
    lines.append("IP LIN")
    lines.extend(f"DP {energy:.10e} {pdf:.10e}" for energy, pdf in corrected)
    content = ("\n".join(lines) + "\n").encode("utf-8")

    serialized_points = parse_rendered_dp(content)
    serialized_integral = trapz(serialized_points)
    if abs(serialized_integral - 1.0) > 1.0e-8:
        raise RuntimeError(
            f"serialized PDF normalization failed for {output_name}: "
            f"integral={serialized_integral:.17g}"
        )

    snapshot_path = repo_rel(raw.path)
    snapshot_hash = sha256_file(raw.path)
    if original["original_raw_sha256"] != snapshot_hash:
        raise RuntimeError(
            f"original/package raw hash mismatch for {raw.family} bin {raw.bin_id}"
        )
    metadata = {
        "bin_id": raw.bin_id,
        "black_hole_mode": raw.black_hole_mode,
        "corrected_pdf_integral": serialized_integral,
        "corrected_sha256": sha256_bytes(content),
        "corrected_spectrum": repo_rel(output_path),
        "energy_scale_to_total_keV": energy_scale,
        "family": raw.family,
        "output_energy_unit": "keV_total",
        "original_raw_path": original["original_raw_path"],
        "original_raw_sha256": original["original_raw_sha256"],
        "original_raw_size_bytes": original["original_raw_size_bytes"],
        "package_raw_snapshot_path": snapshot_path,
        "package_raw_snapshot_sha256": snapshot_hash,
        "point_count": len(serialized_points),
        "raw_energy_unit": raw.metadata["energy_unit"],
        "raw_integral": raw_integral,
        # Backward-compatible canonical aliases consumed by the static gate.
        "raw_sha256": snapshot_hash,
        "raw_spectrum": snapshot_path,
        "snapshot_original_hash_match": True,
        "theta_mid_deg": float(raw.metadata["theta_mid_deg"]),
    }
    return content, metadata


def replace_line_preserving_ending(line: str, replacement: str) -> str:
    if line.endswith("\r\n"):
        return replacement + "\r\n"
    if line.endswith("\n"):
        return replacement + "\n"
    return replacement


def render_source_card(
    parent: Path,
    target: Path,
    family: str,
    spectra: dict[tuple[str, str], RawSpectrum],
) -> tuple[bytes, dict[str, Any]]:
    parent_bytes = parent.read_bytes()
    try:
        parent_text = parent_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"source card is not UTF-8: {repo_rel(parent)}") from exc

    lines = parent_text.splitlines(keepends=True)
    replaced_dir = 0
    replaced_refs: list[str] = []
    seen_bins: set[str] = set()
    output_lines: list[str] = []
    target_spectrum_dir = repo_rel(SPECTRUM_ROOT)

    for line in lines:
        body = line.rstrip("\r\n")
        if SPECTRUM_DIR_RE.match(body):
            replaced_dir += 1
            output_lines.append(
                replace_line_preserving_ending(
                    line, f"# spectrum_dir={target_spectrum_dir}"
                )
            )
            continue

        match = SPECTRUM_LINE_RE.match(body)
        if match is None:
            output_lines.append(line)
            continue

        reference_name = Path(match.group("path")).name
        reference_match = BIN_FROM_REFERENCE_RE.match(reference_name)
        if reference_match is None:
            raise RuntimeError(
                f"unexpected Spectrum File reference in {repo_rel(parent)}: "
                f"{match.group('path')}"
            )
        ref_family = reference_match.group("family")
        bin_id = reference_match.group("bin")
        if ref_family != family:
            raise RuntimeError(
                f"source-card family/reference mismatch in {repo_rel(parent)}: "
                f"{family!r} != {ref_family!r}"
            )
        if bin_id in seen_bins:
            raise RuntimeError(
                f"duplicate Spectrum File bin {bin_id} in {repo_rel(parent)}"
            )
        raw = spectra.get((family, bin_id))
        if raw is None:
            raise RuntimeError(
                f"no retained raw spectrum for {family} bin {bin_id}"
            )
        if reference_match.group("theta") != raw.theta_label:
            raise RuntimeError(
                f"theta label mismatch for {family} bin {bin_id} in "
                f"{repo_rel(parent)}"
            )

        corrected_path = SPECTRUM_ROOT / (
            f"{family}_bin{bin_id}_theta{raw.theta_label}_pdf.spectrum"
        )
        corrected_reference = repo_rel(corrected_path)
        new_body = (
            match.group("prefix") + corrected_reference + match.group("suffix")
        )
        output_lines.append(replace_line_preserving_ending(line, new_body))
        replaced_refs.append(corrected_reference)
        seen_bins.add(bin_id)

    if replaced_dir != 1:
        raise RuntimeError(
            f"expected one spectrum_dir comment in {repo_rel(parent)}, "
            f"found {replaced_dir}"
        )
    expected_bins = {f"{index:02d}" for index in range(BINS_PER_FAMILY)}
    if seen_bins != expected_bins:
        raise RuntimeError(
            f"Spectrum File bin closure failed in {repo_rel(parent)}: "
            f"missing={sorted(expected_bins - seen_bins)}, "
            f"extra={sorted(seen_bins - expected_bins)}"
        )

    output_text = "".join(output_lines)
    # A source card with any non-file spectrum component could silently add a
    # monoenergetic component.  No such component is allowed in this package.
    spectrum_statements = [
        line.strip()
        for line in output_text.splitlines()
        if ".Spectrum" in line and not line.lstrip().startswith("#")
    ]
    if len(spectrum_statements) != BINS_PER_FAMILY or any(
        ".Spectrum File " not in line for line in spectrum_statements
    ):
        raise RuntimeError(
            f"unexpected non-file or additive spectrum statement in {repo_rel(parent)}"
        )

    geometry_lines = [
        match.group("path")
        for line in output_text.splitlines()
        if (match := GEOMETRY_RE.match(line)) is not None
    ]
    if len(geometry_lines) != 1:
        raise RuntimeError(
            f"expected one Geometry line in {repo_rel(parent)}, "
            f"found {len(geometry_lines)}"
        )
    flux_values = [
        float(match.group(1))
        for line in output_text.splitlines()
        if (match := FLUX_RE.search(line)) is not None
    ]
    beam_count = sum(
        1 for line in output_text.splitlines() if BEAM_RE.search(line) is not None
    )
    if len(flux_values) != BINS_PER_FAMILY or beam_count != BINS_PER_FAMILY:
        raise RuntimeError(
            f"Flux/Beam closure failed in {repo_rel(parent)}: "
            f"flux={len(flux_values)}, beam={beam_count}"
        )

    content = output_text.encode("utf-8")
    metadata = {
        "family": family,
        "flux_entries": len(flux_values),
        "flux_sum_cm2_s": math.fsum(flux_values),
        "geometry_line_count": len(geometry_lines),
        "geometry_lines": geometry_lines,
        "parent_sha256": sha256_bytes(parent_bytes),
        "parent_source": repo_rel(parent),
        "source": repo_rel(target),
        "source_sha256": sha256_bytes(content),
        "spectrum_files": replaced_refs,
        "spectrum_references": len(replaced_refs),
    }
    return content, metadata


def resolve_geometry_include(
    including_file: Path, include_token: str
) -> tuple[Path, str, str, str | None]:
    """Resolve one geometry Include into a portable logical identity."""

    megalib_prefix = "$(MEGALIB)/"
    if include_token.startswith(megalib_prefix):
        relative = include_token.removeprefix(megalib_prefix)
        megalib_root = Path(os.environ.get("MEGALIB", str(DEFAULT_MEGALIB_ROOT)))
        resolved = (megalib_root / relative).resolve()
        return resolved, "megalib", include_token, relative
    if "$(" in include_token:
        raise RuntimeError(
            f"unsupported geometry include variable in {including_file}: "
            f"{include_token}"
        )

    resolved = (including_file.parent / include_token).resolve()
    try:
        logical = resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise RuntimeError(
            f"geometry include escapes repository: {including_file} -> "
            f"{include_token}"
        ) from exc
    return resolved, "repository", logical, None


def build_geometry_bundle(setup_path: Path) -> dict[str, Any]:
    """Hash the complete transitive geometry include bundle."""

    setup_path = setup_path.resolve()
    if not setup_path.is_file() or setup_path.is_symlink():
        raise RuntimeError(f"geometry setup is missing or symlinked: {setup_path}")
    try:
        setup_logical = setup_path.relative_to(ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise RuntimeError(f"geometry setup is outside repository: {setup_path}") from exc

    pending: list[tuple[Path, str, str, str | None, str]] = [
        (setup_path, "repository", setup_logical, None, "setup")
    ]
    visited: dict[Path, dict[str, Any]] = {}
    direct_geometry: Path | None = None
    direct_detector: Path | None = None

    while pending:
        path, scope, logical, relative_to_megalib, role = pending.pop(0)
        resolved = path.resolve()
        if resolved in visited:
            continue
        if not resolved.is_file() or resolved.is_symlink():
            raise RuntimeError(
                f"geometry bundle include is missing or symlinked: {logical}"
            )
        content = resolved.read_bytes()
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RuntimeError(f"geometry bundle file is not UTF-8: {logical}") from exc

        row: dict[str, Any] = {
            "logical_path": logical,
            "role": role,
            "scope": scope,
            "sha256": sha256_bytes(content),
            "size_bytes": len(content),
        }
        if scope == "repository":
            row["path"] = logical
        else:
            row["include_token"] = logical
            row["path_relative_to_megalib"] = relative_to_megalib
        visited[resolved] = row

        for line_number, line in enumerate(text.splitlines(), start=1):
            match = INCLUDE_RE.match(line)
            if match is None:
                continue
            token = match.group("target").strip('"\'')
            child, child_scope, child_logical, child_relative = (
                resolve_geometry_include(resolved, token)
            )
            if resolved == setup_path:
                if child.suffix == ".geo":
                    if direct_geometry is not None:
                        raise RuntimeError(
                            f"multiple direct .geo includes in {setup_logical}"
                        )
                    direct_geometry = child.resolve()
                    child_role = "direct_geometry"
                elif child.suffix == ".det":
                    if direct_detector is not None:
                        raise RuntimeError(
                            f"multiple direct .det includes in {setup_logical}"
                        )
                    direct_detector = child.resolve()
                    child_role = "direct_detector"
                else:
                    raise RuntimeError(
                        f"unsupported direct setup include at {setup_logical}:"
                        f"{line_number}: {token}"
                    )
            else:
                child_role = (
                    "transitive_repository"
                    if child_scope == "repository"
                    else "transitive_megalib"
                )
            pending.append(
                (child, child_scope, child_logical, child_relative, child_role)
            )

    if direct_geometry is None or direct_detector is None:
        raise RuntimeError(
            f"setup must directly include exactly one .geo and one .det: "
            f"{setup_logical}"
        )

    files = sorted(visited.values(), key=lambda row: (row["scope"], row["logical_path"]))
    digest_payload = "".join(
        f"{row['scope']}\t{row['logical_path']}\t{row['sha256']}\n"
        for row in files
    ).encode("utf-8")

    def identity(path: Path) -> dict[str, Any]:
        row = visited[path.resolve()]
        return {
            "path": row["path"],
            "sha256": row["sha256"],
            "size_bytes": row["size_bytes"],
        }

    return {
        "bundle_algorithm": (
            "sha256 of sorted UTF-8 lines: "
            "scope<TAB>logical_path<TAB>file_sha256<LF>"
        ),
        "bundle_sha256": sha256_bytes(digest_payload),
        "detector_file": identity(direct_detector),
        "entry_count": len(files),
        "external_include_count": sum(
            row["scope"] != "repository" for row in files
        ),
        "files": files,
        "geometry_file": identity(direct_geometry),
        "setup_file": identity(setup_path),
    }


def build_expected_outputs() -> tuple[list[Output], dict[str, Any]]:
    raw_spectra = load_raw_spectra()
    environment, input_provenance, original_mapping = load_input_context(
        raw_spectra
    )
    outputs: list[Output] = []
    spectrum_records: list[dict[str, Any]] = []

    for family in FAMILIES:
        for bin_number in range(BINS_PER_FAMILY):
            raw = raw_spectra[(family, f"{bin_number:02d}")]
            content, metadata = render_spectrum(
                raw, original_mapping[(family, f"{bin_number:02d}")]
            )
            output_path = ROOT / metadata["corrected_spectrum"]
            outputs.append(Output(output_path, content, "spectrum"))
            spectrum_records.append(metadata)

    geometry_records: dict[str, dict[str, Any]] = {}
    for geometry_key, parent_dir in PARENT_SOURCE_DIRS.items():
        if not parent_dir.is_dir():
            raise RuntimeError(f"parent source directory is missing: {parent_dir}")
        target_dir = SOURCE_CARD_ROOT / geometry_key
        cards: list[dict[str, Any]] = []
        geometry_setup: str | None = None
        geometry_outputs: list[Output] = []

        for family in FAMILIES:
            parent = parent_dir / f"Background_{family}_fullsphere20.source"
            if not parent.is_file():
                raise RuntimeError(f"parent source card is missing: {parent}")
            target = target_dir / parent.name
            content, metadata = render_source_card(
                parent, target, family, raw_spectra
            )
            card_geometry = metadata["geometry_lines"][0]
            if geometry_setup is None:
                geometry_setup = card_geometry
            elif card_geometry != geometry_setup:
                raise RuntimeError(
                    f"geometry mismatch across {geometry_key} cards: "
                    f"{geometry_setup!r} != {card_geometry!r}"
                )
            geometry_outputs.append(Output(target, content, "source_card"))
            cards.append(metadata)

        assert geometry_setup is not None
        geometry_bundle = build_geometry_bundle(ROOT / geometry_setup)
        outputs.extend(geometry_outputs)
        geometry_records[geometry_key] = {
            "cards": cards,
            "farfield_radius_cm": FARFIELD_RADIUS_CM,
            "geometry_bundle": geometry_bundle,
            "geometry_bundle_sha256": geometry_bundle["bundle_sha256"],
            "geometry_setup": geometry_setup,
            "parent_source_dir": repo_rel(parent_dir),
            "source_dir": repo_rel(target_dir),
        }

    contract = {
        "bins_per_family": BINS_PER_FAMILY,
        "energy_contract": {
            "alpha": {
                "conversion": "E_total_keV = E_MeV_per_nucleon * 4 * 1000",
                "energy_scale_to_total_keV": 4000.0,
                "raw_energy_unit": "MeV_per_nucleon",
            },
            "cosima_energy_axis": "total kinetic energy in keV",
            "output_energy_unit": "keV_total",
            "family_energy_scale_to_total_keV": {
                family: (4000.0 if family == "alpha" else 1000.0)
                for family in FAMILIES
            },
            "non_alpha": {
                "conversion": "E_total_keV = E_MeV * 1000",
                "energy_scale_to_total_keV": 1000.0,
                "raw_energy_unit": "MeV",
            },
            "pdf_normalization": (
                "p_keV = raw_density / "
                "(trapezoidal_raw_integral * energy_scale_to_total_keV)"
            ),
        },
        "families": list(FAMILIES),
        "farfield_radius_cm": FARFIELD_RADIUS_CM,
        "generated_by": repo_rel(Path(__file__)),
        "geometries": geometry_records,
        "input_provenance": input_provenance,
        "policies": {
            "additive_mono_511_allowed": False,
            "derived_files_are_package_owned": True,
            "flux_policy": (
                "copy every parent source-card Flux value unchanged; do not "
                "rescale Flux when correcting the energy axis"
            ),
            "gamma_policy": (
                "retained EXPACS/PARMA broadband-total gamma spectrum; it is "
                "the only gamma component in these cards"
            ),
            "parent_inputs_mutated": False,
            "raw_baseline_policy": (
                "normal build and check use only package-owned .raw-spectrum "
                "snapshots; ignored global .dat files are bootstrap-only"
            ),
            "source_card_flux_values_preserved": True,
            "transport_authority": (
                "not granted by static generation; dynamic IA INIT smoke and "
                "matched reruns remain required"
            ),
        },
        "schema_version": 1,
        "source_model": {
            "angular_binning": "20 equal-mu full-sphere FarFieldAreaSource bins",
            "black_hole_mode": "No",
            "environment": environment,
            "gamma_component": "broadband_total",
            "profile": "unit_only_total_gamma",
            "original_raw_root": repo_rel(BOOTSTRAP_RAW_ROOT),
            "retained_raw_root": repo_rel(RAW_ROOT),
        },
        "spectra": {
            "count": len(spectrum_records),
            "files": spectrum_records,
            "root": repo_rel(SPECTRUM_ROOT),
        },
        "status": "CORRECTED_KEV_SOURCE_PACKAGE_GENERATED_NOT_TRANSPORT_VALIDATED",
    }
    contract_content = json_bytes(contract)
    contract_hash = sha256_bytes(contract_content)
    outputs.append(Output(CONTRACT_MANIFEST, contract_content, "contract_manifest"))

    for geometry_key, geometry in geometry_records.items():
        source_entries = []
        for card in geometry["cards"]:
            source_entries.append(
                {
                    "canonical_non_spectrum_fields_preserved": True,
                    "geometry_line_count": card["geometry_line_count"],
                    "geometry_lines": card["geometry_lines"],
                    "particle": card["family"],
                    "parent_sha256": card["parent_sha256"],
                    "parent_source": card["parent_source"],
                    "problems": [],
                    "source": card["source"],
                    "source_sha256": card["source_sha256"],
                    "spectrum_files": card["spectrum_files"],
                    "spectrum_references": card["spectrum_references"],
                    "total_flux_cm2_s": card["flux_sum_cm2_s"],
                }
            )
        source_manifest = {
            "farfield_radius_cm": FARFIELD_RADIUS_CM,
            "geometry_bundle": geometry["geometry_bundle"],
            "geometry_bundle_sha256": geometry["geometry_bundle_sha256"],
            "geometry_setup": geometry["geometry_setup"],
            "geometry_status": (
                f"{geometry_key}: retained geometry; corrected-keV source "
                "references only"
            ),
            "label": f"{geometry_key}_corrected_keV_all8_fullsphere20",
            "parent_source_dir": geometry["parent_source_dir"],
            "pointing_policy": (
                "unchanged parent 20-bin full-sphere beams and Flux values; "
                "only spectrum_dir comment and Spectrum File paths replaced"
            ),
            "problems": [],
            "schema_version": 1,
            "source_contract_manifest_path": repo_rel(CONTRACT_MANIFEST),
            "source_contract_manifest_sha256": contract_hash,
            "source_dir": geometry["source_dir"],
            "sources": source_entries,
            "status": "GENERATED_CORRECTED_KEV_NOT_TRANSPORT_VALIDATED",
        }
        manifest_path = ROOT / geometry["source_dir"] / "source_migration_manifest.json"
        outputs.append(
            Output(manifest_path, json_bytes(source_manifest), "source_manifest")
        )

    paths = [output.path for output in outputs]
    if len(paths) != len(set(paths)):
        raise RuntimeError("internal error: duplicate generated output path")
    expected_outputs = (
        len(FAMILIES) * BINS_PER_FAMILY
        + len(PARENT_SOURCE_DIRS) * len(FAMILIES)
        + len(PARENT_SOURCE_DIRS)
        + 1
    )
    if len(outputs) != expected_outputs:
        raise RuntimeError(
            f"internal output closure failed: {len(outputs)} != {expected_outputs}"
        )
    return outputs, contract


def compare_outputs(outputs: list[Output]) -> tuple[list[Output], list[Output]]:
    missing: list[Output] = []
    different: list[Output] = []
    for output in outputs:
        if not output.path.exists():
            missing.append(output)
        elif (
            output.path.is_symlink()
            or not output.path.is_file()
            or output.path.read_bytes() != output.content
        ):
            different.append(output)
    return missing, different


def print_mismatches(label: str, outputs: list[Output]) -> None:
    for output in outputs:
        print(f"{label} [{output.kind}] {repo_rel(output.path)}", file=sys.stderr)


def atomic_write_output(output: Output) -> None:
    try:
        output.path.relative_to(PACKAGE)
    except ValueError as exc:
        raise RuntimeError(
            f"refusing to write generated output outside repair package: "
            f"{output.path}"
        ) from exc
    if output.path.exists() and (
        output.path.is_symlink() or not output.path.is_file()
    ):
        raise RuntimeError(
            f"refusing to replace non-regular generated target: "
            f"{repo_rel(output.path)}"
        )

    output.path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.path.name}.builder-tmp-", dir=output.path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(output.content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(0o644)
        os.replace(temporary, output.path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build or check corrected total-keV spectra and source cards."
    )
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--check",
        action="store_true",
        help="read-only: require every derived artifact to match expected content",
    )
    modes.add_argument(
        "--bootstrap-raw-snapshots",
        action="store_true",
        help=(
            "first use only: byte-freeze ignored global raw .dat files into "
            "package-owned .raw-spectrum inputs, then refresh generated outputs"
        ),
    )
    modes.add_argument(
        "--refresh-generated",
        action="store_true",
        help=(
            "explicitly replace differing builder-managed outputs inside this "
            "repair package; never modifies retained parents or raw snapshots"
        ),
    )
    args = parser.parse_args()

    try:
        bootstrapped = (
            bootstrap_raw_snapshots() if args.bootstrap_raw_snapshots else 0
        )
        outputs, contract = build_expected_outputs()
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    missing, different = compare_outputs(outputs)
    if args.check:
        if missing:
            print_mismatches("MISSING", missing)
        if different:
            print_mismatches("DIFFERENT", different)
        if missing or different:
            print(
                f"CHECK FAIL: missing={len(missing)} different={len(different)}",
                file=sys.stderr,
            )
            return 1
        print(
            "CHECK PASS: "
            f"spectra={contract['spectra']['count']} "
            f"source_cards={len(PARENT_SOURCE_DIRS) * len(FAMILIES)} "
            f"manifests={len(PARENT_SOURCE_DIRS) + 1}"
        )
        return 0

    refresh_generated = args.bootstrap_raw_snapshots or args.refresh_generated
    if different and not refresh_generated:
        print_mismatches("REFUSING_TO_OVERWRITE", different)
        print(
            "BUILD FAIL: existing derived content differs; no files were written",
            file=sys.stderr,
        )
        return 1

    # All default-mode conflicts were checked before the first write.  The two
    # explicit mutation modes remain confined to builder-managed package paths.
    write_set = missing + (different if refresh_generated else [])
    for output in outputs:
        if output not in write_set:
            continue
        try:
            atomic_write_output(output)
        except (OSError, RuntimeError) as exc:
            print(f"BUILD FAIL: {exc}", file=sys.stderr)
            return 2

    print(
        "BUILD PASS: "
        f"bootstrapped_raw={bootstrapped} created={len(missing)} "
        f"refreshed={len(different) if refresh_generated else 0} "
        f"unchanged={len(outputs) - len(write_set)} "
        f"spectra={contract['spectra']['count']} "
        f"source_cards={len(PARENT_SOURCE_DIRS) * len(FAMILIES)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
