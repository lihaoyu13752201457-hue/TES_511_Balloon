#!/usr/bin/env python3
"""Fail-closed validator for the corrected-keV proton P0 six-band pilot.

The validator is intentionally usable before transport: ``--preflight``
reports a structured WAIT while the review-owned science contract and derived
source manifest are absent.  A PASS job receipt is published only after a full
gzip/IA/source/DAT/log scan.  Cell and final authorities are likewise
write-once and are never published for a FAIL result.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any, Iterable


THIS_FILE = Path(__file__).resolve()
CODE_DIR = THIS_FILE.parent
REPAIR_CODE = THIS_FILE.parents[2] / "code"
for directory in (CODE_DIR, REPAIR_CODE):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import build_proton_p0_sixband_sources as source_builder  # noqa: E402
import p0_common as p0  # noqa: E402
import run_proton_p0_sixband_pilot as batch  # noqa: E402
import validate_mergeable_two_geometry_smoke as smoke_validation  # noqa: E402


GENERATED_RE = re.compile(r"Total number of generated particles:\s+(\d+)")
OBSERVATION_RE = re.compile(r"Observation time:\s+([-+0-9.eE]+) sec")
RETURN_RE = re.compile(r"^returncode=(-?\d+)\s*$", re.MULTILINE)
PEAK_RSS_RE = re.compile(r"^peak_process_group_rss_bytes=(\d+)\s*$", re.MULTILINE)
OUTPUT_CAP_RE = re.compile(r"^attempt_output_cap_bytes=(\d+)\s*$", re.MULTILINE)
FILE_CAP_RE = re.compile(r"^per_file_RLIMIT_FSIZE_bytes=(\d+)\s*$", re.MULTILINE)
INPUT_PRE_RE = re.compile(r"^frozen_input_bundle_sha256_pre=([0-9a-f]{64})\s*$", re.MULTILINE)
INPUT_POST_RE = re.compile(r"^frozen_input_bundle_sha256_post=([0-9a-f]{64}|FAIL)\s*$", re.MULTILINE)
WATCHDOG_RE = re.compile(r"^watchdog_reason=(\S+)\s*$", re.MULTILINE)
WALL_RE = re.compile(r"^wall_s=([-+0-9.eE]+)\s*$", re.MULTILINE)
EDEP_RE = re.compile(r"\bedep_keV=([-+0-9.eE]+)(?:\s|$)")

TES_RE = re.compile(r"^TP_L[0-5]_[0-9]+$")
MASS_VETO = frozenset(
    {
        "CsI_Side_Segment_00",
        "CsI_Side_Segment_01",
        "CsI_Side_Segment_02",
        "CsI_Side_Segment_03_below_side_port",
        "CsI_Side_Segment_03_above_side_port",
        "CsI_Side_Segment_03_rectcut_window_band",
        "CsI_Side_Segment_04_below_side_port",
        "CsI_Side_Segment_04_above_side_port",
        "CsI_Side_Segment_04_rectcut_window_band",
        "CsI_Side_Segment_05",
        "CsI_Side_Segment_06",
        "CsI_Side_Segment_07",
        *(f"CsI_Bottom_Quadrant_{index:02d}" for index in range(4)),
        *(f"CsI_TopAnnulus_Segment_{index:02d}" for index in range(8)),
    }
)
O8_BGO_VETO = frozenset(
    {
        "BGO_S3C_FullWrap_SideShell_WindowCut_40mm",
        "BGO_S3D_O8_FullWrap_BottomCap_30mm",
        "BGO_S3D_O8_FullWrap_TopAnnulus_10mm",
    }
)
O8_PLASTIC_VETO = frozenset(
    {
        "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm",
        "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm",
        "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm",
    }
)
VETO_THRESHOLDS_KEV = (50.0, 70.0, 80.0)
TT_AUTHORITY = (
    "per job actual isotope-DAT TT, cross-checked against log Observation time; "
    "rates are summed as sum_b(count_b/sum_TT_b), never pooled as sum(count)/sum(TT)"
)


class Gate:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.checks: dict[str, int] = defaultdict(int)

    def require(self, condition: bool, message: str, category: str) -> None:
        self.checks[category] += 1
        if not condition and len(self.errors) < 100:
            self.errors.append(message)

    def problem(self, message: str, category: str) -> None:
        self.require(False, message, category)


def _strict(path: Path) -> dict[str, Any]:
    return p0.load_json_strict(path)


def _expected_paths(job_ordinal: int, attempt: int) -> dict[str, Path]:
    spec = batch.job_spec(job_ordinal, p0.load_source_manifest(required=True) or {})
    paths = batch._job_paths(spec, attempt)
    paths["attempt_validation"] = paths["directory"] / "attempt_validation.json"
    return paths


def _artifact_snapshot(paths: dict[str, Path]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    records: dict[str, dict[str, Any]] = {}
    problems: list[str] = []
    for key in ("attempt_contract", "source", "sim", "dat", "log"):
        path = paths[key]
        try:
            record = p0.stable_file_snapshot(path)
        except (OSError, RuntimeError) as exc:
            problems.append(f"{key}: {exc}")
            continue
        records[key] = {
            "path": record["path"],
            "sha256": record["sha256"],
            "bytes": record["size_bytes"],
        }
    return records, problems


def _single_float(matches: list[str]) -> float | None:
    if len(matches) != 1:
        return None
    try:
        value = float(matches[0])
    except (TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) else None


def _manifest_indexes(manifest: dict[str, Any]) -> tuple[dict[tuple[str, int], dict[str, Any]], dict[int, dict[str, Any]]]:
    spectra: dict[tuple[str, int], dict[str, Any]] = {}
    for row in manifest.get("conditional_spectra", []):
        if not isinstance(row, dict):
            raise RuntimeError("conditional spectrum inventory contains a non-object")
        key = (str(row.get("band")), row.get("angular_bin"))
        if type(key[1]) is not int or key in spectra:
            raise RuntimeError("conditional spectrum inventory identity is ambiguous")
        spectra[(key[0], int(key[1]))] = row
    if set(spectra) != {(f"b{band}", angular) for band in range(6) for angular in range(20)}:
        raise RuntimeError("conditional spectrum inventory is not exact 6x20")
    partial: dict[int, dict[str, Any]] = {}
    for row in manifest.get("angular_bin_partial_flux", []):
        if not isinstance(row, dict) or type(row.get("angular_bin")) is not int:
            raise RuntimeError("angular partial-Flux inventory is malformed")
        angular = int(row["angular_bin"])
        if angular in partial:
            raise RuntimeError("duplicate angular partial-Flux row")
        partial[angular] = row
    if set(partial) != set(range(20)):
        raise RuntimeError("angular partial-Flux inventory is not exact 20 bins")
    return spectra, partial


def validate_source_package(manifest: dict[str, Any]) -> dict[str, Any]:
    """Recompute the derived-source semantics; hashes alone are insufficient."""

    p0.validate_source_manifest(manifest, verify_files=True)
    source_builder.validate_published_package_exact(manifest)
    bands = p0.bands_from_manifest(manifest)
    spectra, partial = _manifest_indexes(manifest)
    checks = 0
    for angular in range(20):
        values = [Decimal(str(value)) for value in partial[angular].get("partial_flux_cm2_s", [])]
        parent_flux = Decimal(str(partial[angular].get("parent_flux_cm2_s")))
        if len(values) != 6 or any(value <= 0 for value in values):
            raise RuntimeError(f"angular bin {angular}: non-positive/incomplete partial Flux")
        parent = p0.parent_card_records(p0.PARENT_SOURCE["mass_model_511"])["flux"][angular]
        with localcontext() as context:
            context.prec = 400
            if parent_flux != parent or sum(values, Decimal(0)) != parent:
                raise RuntimeError(f"angular bin {angular}: exact partial-Flux closure failure")
        checks += 1
    for geometry in p0.GEOMETRIES:
        parent_path = p0.PARENT_SOURCE[geometry]
        parent_text = parent_path.read_text(encoding="utf-8")
        for band in bands:
            card_path = p0.band_source_path(geometry, band.key)
            derived_text = card_path.read_text(encoding="utf-8")
            source_builder.allowed_band_card_diff(parent_text, derived_text)
            card = p0.parent_card_records(card_path)
            expected_flux = {
                angular: Decimal(str(partial[angular]["partial_flux_cm2_s"][band.index]))
                for angular in range(20)
            }
            if card["flux"] != expected_flux:
                raise RuntimeError(f"{geometry}/{band.key}: card partial Flux differs from proof")
            for angular in range(20):
                row = spectra[(band.key, angular)]
                expected_path = p0.resolve_path(str(row["path"]))
                if card["spectra"][angular] != expected_path:
                    raise RuntimeError(f"{geometry}/{band.key}/bin{angular:02d}: spectrum path mismatch")
                points = p0.parse_dp_decimal(expected_path)
                integral = p0.integrate_linear(points)
                if abs(integral - Decimal(1)) > Decimal("1e-20"):
                    raise RuntimeError(f"{band.key}/bin{angular:02d}: conditional PDF not unit trapezoid")
                low = Decimal(str(row["low_keV"]))
                high = Decimal(str(row["high_keV"]))
                if points[0][0] != low or points[-1][0] != high:
                    raise RuntimeError(f"{band.key}/bin{angular:02d}: conditional support mismatch")
                checks += 1
    return {
        "status": "PASS__P0_DERIVED_SOURCE_SEMANTICS",
        "checks": checks,
        "conditional_spectra": 120,
        "derived_source_cards": 12,
        "total_flux_cm2_s": p0.decimal_to_json(p0.TOTAL_FLUX_DECIMAL),
    }


def _source_support_and_flux(
    manifest: dict[str, Any], geometry: str, band_key: str
) -> tuple[dict[int, tuple[float, float]], Decimal]:
    spectra, partial = _manifest_indexes(manifest)
    supports: dict[int, tuple[float, float]] = {}
    for angular in range(20):
        row = spectra[(band_key, angular)]
        points = p0.parse_dp_decimal(p0.resolve_path(str(row["path"])))
        supports[angular] = (float(points[0][0]), float(points[-1][0]))
    band = next(item for item in p0.bands_from_manifest(manifest) if item.key == band_key)
    with localcontext() as context:
        context.prec = 400
        summed = sum(
            (Decimal(str(partial[angular]["partial_flux_cm2_s"][band.index])) for angular in range(20)),
            Decimal(0),
        )
    if summed != band.flux_cm2_s:
        raise RuntimeError(f"{band_key}: all-angle partial Flux does not close")
    return supports, summed


def _validate_job_source(
    gate: Gate,
    manifest: dict[str, Any],
    spec: dict[str, Any],
    attempt: int,
    paths: dict[str, Path],
) -> tuple[dict[int, tuple[float, float]], Decimal]:
    geometry = str(spec["geometry"])
    band_key = str(spec["band"])
    base = p0.band_source_path(geometry, band_key)
    try:
        # This proves the new derived contract separately from the runtime patch.
        source_builder.allowed_band_card_diff(
            p0.PARENT_SOURCE[geometry].read_text(encoding="utf-8"),
            base.read_text(encoding="utf-8"),
        )
        expected = smoke_validation.expected_patched_source(
            base,
            str(spec["mode"]),
            int(spec["events"]),
            int(spec["seed"]),
            paths["sim_prefix"],
            paths["isotope_prefix"],
        )
        observed = paths["source"].read_text(encoding="utf-8")
        gate.require(observed == expected, "runtime job source differs from exact allowed patch", "source")
        gate.require("cosima_spectra_dp_2602units" not in observed, "legacy spectrum reference present", "source")
        gate.require(observed.count("StoreSimulationInfo all") == 1, "StoreSimulationInfo all is not exact", "source")
        if spec["mode"] == "buildup":
            gate.require(observed.count("DecayMode ActivationBuildUp") == 1, "buildup DecayMode missing", "source")
        else:
            gate.require("DecayMode ActivationBuildUp" not in observed, "instant source contains buildup mode", "source")
        supports, flux = _source_support_and_flux(manifest, geometry, band_key)
        gate.require(p0.parent_card_records(paths["source"])["flux"] == p0.parent_card_records(base)["flux"],
                     "runtime patch changed partial Flux", "source")
        return supports, flux
    except Exception as exc:
        gate.problem(f"source validation failed: {exc}", "source")
        return {}, Decimal(0)


def _hit_volume(line: str) -> tuple[str, float] | None:
    fields = line.split()
    match = EDEP_RE.search(line)
    if len(fields) < 3 or match is None:
        return None
    try:
        energy = float(match.group(1))
    except ValueError:
        return None
    if not math.isfinite(energy) or energy < 0:
        return None
    return fields[2], energy


def _finish_prompt_event(
    geometry: str,
    tes: dict[str, float],
    bgo_or_csi: float,
    plastic: float,
    summary: dict[str, Any],
) -> None:
    tes_values = [value for value in tes.values() if value > 0]
    raw_total = math.fsum(tes_values)
    raw_any = raw_total > 0
    raw_window = 480.0 <= raw_total < 550.0
    summary["raw_tes_positive_events"] += int(raw_any)
    summary["raw_tes_480_550_events"] += int(raw_window)
    for threshold in VETO_THRESHOLDS_KEV:
        passes = bgo_or_csi < threshold and (geometry == "mass_model_511" or plastic < 50.0)
        key = str(int(threshold))
        summary["veto_survivors_tes_positive"][key] += int(raw_any and passes)
        summary["veto_survivors_tes_480_550"][key] += int(raw_window and passes)


def scan_sim(
    path: Path,
    *,
    geometry: str,
    mode: str,
    expected_events: int,
    expected_seed: int,
    expected_geometry: Path,
    support_by_bin: dict[int, tuple[float, float]],
) -> dict[str, Any]:
    """Read through gzip EOF and validate primaries plus P0 postprocess readiness."""

    problems: list[str] = []
    ids: list[int] = []
    se_count = 0
    init_count = 0
    init_by_event: dict[int, int] = defaultdict(int)
    current_id: int | None = None
    header_geometry: str | None = None
    header_seed: int | None = None
    bad_particle = bad_direction = bad_energy = malformed_hit = malformed_rp = 0
    energy_min: float | None = None
    energy_max: float | None = None
    tes: dict[str, float] = defaultdict(float)
    veto = plastic = 0.0
    prompt = {
        "raw_tes_positive_events": 0,
        "raw_tes_480_550_events": 0,
        "veto_survivors_tes_positive": {str(int(value)): 0 for value in VETO_THRESHOLDS_KEV},
        "veto_survivors_tes_480_550": {str(int(value)): 0 for value in VETO_THRESHOLDS_KEV},
        "veto_semantics": (
            "true physical volume sums per event: Mass exact 24 CsI; S3d-O8 exact 3 BGO and "
            "3 plastic, with plastic fixed at <50 keV; Kapton is not veto"
        ),
    }
    rp_by_state: dict[tuple[str, int, float], int] = defaultdict(int)

    def problem(message: str) -> None:
        if len(problems) < 40:
            problems.append(message)

    def close_event() -> None:
        nonlocal tes, veto, plastic
        if current_id is not None and mode == "instant":
            _finish_prompt_event(geometry, tes, veto, plastic, prompt)
        tes = defaultdict(float)
        veto = 0.0
        plastic = 0.0

    try:
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                line = raw.strip()
                if header_geometry is None and (match := smoke_validation.GEOMETRY_RE.match(line)):
                    header_geometry = match.group(1)
                if header_seed is None and line.startswith("Seed "):
                    try:
                        header_seed = int(line.split()[1])
                    except (IndexError, ValueError):
                        problem("malformed Seed header")
                if line == "SE":
                    close_event()
                    se_count += 1
                    current_id = None
                    continue
                if match := smoke_validation.ID_RE.match(line):
                    current_id = int(match.group(1))
                    ids.append(current_id)
                    continue
                if line.startswith("IA INIT"):
                    if current_id is None:
                        problem("IA INIT outside event")
                        continue
                    init_by_event[current_id] += 1
                    init_count += 1
                    try:
                        init = smoke_validation.parse_init(line)
                        if int(init["particle_type"]) != 4:
                            bad_particle += 1
                        direction = tuple(float(init[key]) for key in ("dir_x", "dir_y", "dir_z"))
                        norm = math.sqrt(math.fsum(value * value for value in direction))
                        if not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=5e-4):
                            bad_direction += 1
                        angular = smoke_validation.angular_bin_from_init_dir_z(direction[2])
                        energy = float(init["energy_keV"])
                        low, high = support_by_bin[angular]
                        tolerance = max(0.002, 1e-10 * max(abs(low), abs(high)))
                        if not low - tolerance <= energy <= high + tolerance:
                            bad_energy += 1
                        energy_min = energy if energy_min is None else min(energy_min, energy)
                        energy_max = energy if energy_max is None else max(energy_max, energy)
                    except Exception as exc:
                        problem(f"malformed IA INIT: {exc}")
                    continue
                if line.startswith("CC HIT") and mode == "instant":
                    parsed = _hit_volume(line)
                    if parsed is None:
                        malformed_hit += 1
                        continue
                    volume, energy = parsed
                    if TES_RE.match(volume):
                        tes[volume] += energy
                    if geometry == "mass_model_511" and volume in MASS_VETO:
                        veto += energy
                    elif geometry == "s3d_o8" and volume in O8_BGO_VETO:
                        veto += energy
                    elif geometry == "s3d_o8" and volume in O8_PLASTIC_VETO:
                        plastic += energy
                    continue
                if line.startswith("CC IP RP"):
                    fields = line.split()
                    try:
                        volume = fields[3]
                        isotope = int(fields[7])
                        excitation = float(fields[8])
                        if isotope <= 0 or not volume or not math.isfinite(excitation) or excitation < 0:
                            raise ValueError("invalid RP identity")
                        rp_by_state[(volume, isotope, excitation)] += 1
                    except (IndexError, ValueError):
                        malformed_rp += 1
            close_event()
    except (OSError, EOFError, gzip.BadGzipFile) as exc:
        problem(f"gzip integrity/EOF failure: {exc}")

    if header_geometry is None:
        problem("missing Geometry header")
    elif p0.resolve_path(header_geometry) != expected_geometry.resolve():
        problem(f"wrong Geometry header: {header_geometry}")
    if header_seed != expected_seed:
        problem(f"Seed={header_seed}, expected {expected_seed}")
    if se_count != expected_events:
        problem(f"SE records={se_count}, expected {expected_events}")
    if ids != list(range(1, expected_events + 1)):
        problem(f"IDs are not exactly 1..{expected_events}")
    if init_count != expected_events or any(init_by_event.get(index, 0) != 1 for index in range(1, expected_events + 1)):
        problem("IA INIT is not exactly one per expected event")
    if bad_particle:
        problem(f"wrong proton ParticleType records={bad_particle}")
    if bad_direction:
        problem(f"non-unit direction records={bad_direction}")
    if bad_energy:
        problem(f"energy outside selected angular-bin band records={bad_energy}")
    if malformed_hit:
        problem(f"malformed CC HIT records={malformed_hit}")
    if malformed_rp:
        problem(f"malformed CC IP RP records={malformed_rp}")
    return {
        "events": len(ids),
        "se_records": se_count,
        "ia_init_records": init_count,
        "energy_min_keV": energy_min,
        "energy_max_keV": energy_max,
        "bad_particle_records": bad_particle,
        "bad_direction_records": bad_direction,
        "bad_energy_records": bad_energy,
        "geometry_header": header_geometry,
        "seed_header": header_seed,
        "gzip_eof_read": not any(item.startswith("gzip integrity") for item in problems),
        "prompt": prompt if mode == "instant" else None,
        "buildup_rp_ip": [
            {"volume": key[0], "isotope_id": key[1], "excitation_keV": key[2], "count": value}
            for key, value in sorted(rp_by_state.items())
        ],
        "buildup_rp_ip_count": sum(rp_by_state.values()),
        "problems": problems,
    }


def _validate_contract(contract: dict[str, Any], gate: Gate) -> None:
    gate.require(contract.get("batch_id") == batch.BATCH_ID, "batch ID mismatch", "contract")
    gate.require(contract.get("campaign_version") == batch.CAMPAIGN_VERSION, "campaign version mismatch", "contract")
    gate.require(contract.get("toolchain") == batch.toolchain_payload(), "toolchain key/path/hash mismatch", "toolchain")
    source = contract.get("source", {})
    gate.require(source.get("conditional_source_manifest") == p0.rel(p0.SOURCE_MANIFEST), "source manifest path mismatch", "contract")
    gate.require(source.get("conditional_source_manifest_sha256") == p0.sha256(p0.SOURCE_MANIFEST), "source manifest hash mismatch", "contract")
    stats = contract.get("statistics", {})
    gate.require(stats.get("transport_jobs") == 96 and stats.get("primaries") == 6144, "96/6144 closure mismatch", "contract")
    gate.require(stats.get("jobs") == batch.jobs(p0.load_source_manifest(required=True) or {}), "frozen job schedule mismatch", "contract")
    gate.require(source.get("geant4_cut_changes") is False, "Geant4 CUT change is forbidden", "contract")
    execution = contract.get("execution", {})
    try:
        started = datetime.fromisoformat(str(execution.get("frozen_started_utc")))
        deadline = datetime.fromisoformat(str(execution.get("frozen_deadline_utc")))
        gate.require(started.tzinfo is not None and deadline.tzinfo is not None, "execution window is not aware UTC", "deadline")
        gate.require(deadline > started and math.isclose((deadline - started).total_seconds(), 12 * 3600, abs_tol=1e-6),
                     "execution window is not the inherited exact 12h", "deadline")
    except (TypeError, ValueError):
        gate.problem("malformed inherited execution window", "deadline")
    predecessor = contract.get("predecessor", {})
    gate.require(str(predecessor.get("gate", "")).startswith("PASS"), "batch0004 predecessor is not PASS", "predecessor")
    gate.require(predecessor.get("report_sha256") == p0.sha256(batch.BATCH4_REPORT), "batch0004 report hash mismatch", "predecessor")
    gate.require(predecessor.get("ledger_sha256") == p0.sha256(batch.BATCH4_LEDGER), "batch0004 ledger hash mismatch", "predecessor")


def validate_attempt(job_ordinal: int, attempt: int) -> tuple[dict[str, Any], list[str]]:
    gate = Gate()
    if not batch.GLOBAL_CONTRACT.is_file():
        return {"schema_version": 1, "status": "FAIL", "errors": ["missing global contract"]}, ["missing global contract"]
    contract = _strict(batch.GLOBAL_CONTRACT)
    manifest = p0.load_source_manifest(required=True) or {}
    _validate_contract(contract, gate)
    try:
        spec = batch.job_spec(job_ordinal, manifest)
    except Exception as exc:
        return {"schema_version": 1, "status": "FAIL", "errors": [str(exc)]}, [str(exc)]
    gate.require(type(attempt) is int and 1 <= attempt <= batch.MAX_ATTEMPTS, "attempt out of range", "identity")
    paths = _expected_paths(job_ordinal, attempt)
    for key in ("attempt_contract", "source", "sim", "dat", "log"):
        path = paths[key]
        gate.require(path.is_file() and path.stat().st_size > 0 if path.exists() else False,
                     f"missing/empty {key}: {p0.rel(path)}", "outputs")
        try:
            path.resolve().relative_to(paths["directory"].resolve())
        except ValueError:
            gate.problem(f"{key} escapes attempt directory", "outputs")
    if not all(paths[key].is_file() for key in ("attempt_contract", "source", "sim", "dat", "log")):
        return {
            "schema_version": 1,
            "status": "FAIL",
            "job_ordinal": job_ordinal,
            "attempt": attempt,
            "errors": gate.errors,
        }, gate.errors
    pre, snapshot_errors = _artifact_snapshot(paths)
    for error in snapshot_errors:
        gate.problem(f"pre-scan {error}", "stability")
    attempt_contract = _strict(paths["attempt_contract"])
    try:
        live_input_pre = batch._attempt_input_digest(contract, spec)
        gate.require(
            live_input_pre == attempt_contract.get("frozen_input_bundle_sha256_pre"),
            "current frozen input bundle differs from attempt contract",
            "binding",
        )
    except Exception as exc:
        live_input_pre = "FAIL"
        gate.problem(f"cannot recompute current frozen input bundle: {exc}", "binding")
    try:
        expected_contract = batch._attempt_contract(
            contract,
            spec,
            attempt,
            batch._generic_job(spec, attempt, str(contract["transport"]["cosima"])),
            str(attempt_contract.get("frozen_input_bundle_sha256_pre")),
        )
        gate.require(attempt_contract == expected_contract, "attempt contract exact payload mismatch", "binding")
    except Exception as exc:
        gate.problem(f"attempt contract reconstruction failed: {exc}", "binding")
    supports, flux_decimal = _validate_job_source(gate, manifest, spec, attempt, paths)
    source_geometry = manifest.get("geometries", {}).get(spec["geometry"], {}).get("geometry")
    expected_geometry = p0.resolve_path(source_geometry) if isinstance(source_geometry, str) else Path("/__invalid__")

    log_text = paths["log"].read_text(encoding="utf-8", errors="replace")
    generated_matches = GENERATED_RE.findall(log_text)
    observation_matches = OBSERVATION_RE.findall(log_text)
    return_matches = RETURN_RE.findall(log_text)
    peak_matches = PEAK_RSS_RE.findall(log_text)
    output_cap_matches = OUTPUT_CAP_RE.findall(log_text)
    file_cap_matches = FILE_CAP_RE.findall(log_text)
    input_pre_matches = INPUT_PRE_RE.findall(log_text)
    input_post_matches = INPUT_POST_RE.findall(log_text)
    watchdog_matches = WATCHDOG_RE.findall(log_text)
    wall_matches = WALL_RE.findall(log_text)
    observation = _single_float(observation_matches)
    generated = int(generated_matches[0]) if len(generated_matches) == 1 else None
    returncode = int(return_matches[0]) if len(return_matches) == 1 else None
    peak_rss = int(peak_matches[0]) if len(peak_matches) == 1 else None
    frozen = attempt_contract.get("frozen_input_bundle_sha256_pre")
    expected_command_line = "cosima_command=" + " ".join(str(value) for value in attempt_contract.get("command", []))
    gate.require(len(generated_matches) == 1 and generated == spec["events"], "generated particle count mismatch", "log")
    gate.require(len(return_matches) == 1 and returncode == 0, "return code is not exact zero", "log")
    gate.require(len(observation_matches) == 1 and observation is not None and observation > 0, "invalid/duplicate log TT", "normalization")
    gate.require(len(peak_matches) == 1 and peak_rss is not None and peak_rss >= 0, "invalid peak RSS", "resource")
    gate.require(len(output_cap_matches) == 1 and int(output_cap_matches[0]) == batch.ATTEMPT_OUTPUT_CAP_BYTES,
                 "aggregate output-cap log mismatch", "resource")
    gate.require(len(file_cap_matches) == 1 and int(file_cap_matches[0]) == batch.PER_FILE_CAP_BYTES,
                 "per-file RLIMIT log mismatch", "resource")
    gate.require(len(input_pre_matches) == len(input_post_matches) == 1 and input_pre_matches[0] == frozen and input_post_matches[0] == frozen,
                 "frozen input pre/post log mismatch", "binding")
    gate.require(log_text.count(expected_command_line) == 1, "logged command differs from frozen command", "log")
    gate.require(len(watchdog_matches) == 1 and watchdog_matches[0] == "process_exit", "watchdog did not record clean process exit", "log")
    wall_s = _single_float(wall_matches)
    gate.require(len(wall_matches) == 1 and wall_s is not None and wall_s > 0, "invalid/duplicate wall time", "log")
    gate.require("MEGAlib version" in log_text, "MEGAlib banner missing", "log")
    gate.require("***  Error" not in log_text and "Segmentation fault" not in log_text,
                 "fatal marker in log", "log")

    isotope = smoke_validation.parse_isotope_dat(paths["dat"])
    for problem in isotope["problems"]:
        gate.problem(f"isotope DAT: {problem}", "dat")
    dat_tt = isotope.get("TT_s")
    gate.require(type(dat_tt) in (int, float) and math.isfinite(float(dat_tt)) and float(dat_tt) > 0,
                 "invalid DAT TT", "normalization")
    if observation is not None and type(dat_tt) in (int, float):
        gate.require(math.isclose(float(dat_tt), observation, rel_tol=2e-3, abs_tol=2e-6),
                     "DAT/log TT mismatch", "normalization")
    tt_expected = float(p0.tt_expected_seconds(int(spec["events"]), flux_decimal)) if flux_decimal > 0 else None
    gate.require(tt_expected is not None and math.isfinite(tt_expected) and tt_expected > 0,
                 "expected TT is not finite positive", "normalization")
    if supports:
        scan = scan_sim(
            paths["sim"],
            geometry=str(spec["geometry"]),
            mode=str(spec["mode"]),
            expected_events=int(spec["events"]),
            expected_seed=int(spec["seed"]),
            expected_geometry=expected_geometry,
            support_by_bin=supports,
        )
    else:
        scan = {"events": 0, "problems": ["source support unavailable"]}
    for problem in scan["problems"]:
        gate.problem(f"SIM: {problem}", "sim")
    dat_rp_count = sum(float(row["sum_RP"]) for row in isotope.get("RP_totals_by_volume_isotope_state", []))
    if spec["mode"] == "buildup":
        gate.require(math.isclose(dat_rp_count, float(scan.get("buildup_rp_ip_count", 0)), rel_tol=0, abs_tol=1e-9),
                     "SIM CC IP RP count differs from DAT sum_RP", "activation")

    post, snapshot_errors = _artifact_snapshot(paths)
    for error in snapshot_errors:
        gate.problem(f"post-scan {error}", "stability")
    gate.require(pre == post, "attempt artifacts changed during validation", "stability")
    try:
        live_input_post = batch._attempt_input_digest(contract, spec)
        gate.require(
            live_input_pre != "FAIL" and live_input_post == live_input_pre == frozen,
            "current frozen input bundle changed during validation",
            "binding",
        )
    except Exception as exc:
        gate.problem(f"cannot post-recompute frozen input bundle: {exc}", "binding")
    output_bytes = sum(int(post.get(key, {}).get("bytes", 0)) for key in ("sim", "dat", "log"))
    gate.require(output_bytes <= batch.ATTEMPT_OUTPUT_CAP_BYTES, "final aggregate output exceeds cap", "resource")
    status = "PASS" if not gate.errors else "FAIL"
    payload = {
        "schema_version": 1,
        "status": status,
        "batch_id": batch.BATCH_ID,
        "campaign_version": batch.CAMPAIGN_VERSION,
        "job_ordinal": job_ordinal,
        "cell_ordinal": spec["cell_ordinal"],
        "cell_key": spec["cell_key"],
        "geometry": spec["geometry"],
        "mode": spec["mode"],
        "family": "p",
        "band": spec["band"],
        "band_index": spec["band_index"],
        "shard": spec["shard"],
        "attempt": attempt,
        "events": spec["events"],
        "seed": spec["seed"],
        "flux_cm2_s": p0.decimal_to_json(flux_decimal),
        "band_flux_weight": next(row["weight"] for row in manifest["bands"] if row["key"] == spec["band"]),
        "TT_s_from_log": observation,
        "TT_s_from_isotope_dat": dat_tt,
        "TT_s_expected_mean_from_events_flux_area": tt_expected,
        "TT_authority": TT_AUTHORITY,
        "peak_process_group_rss_bytes": peak_rss,
        "attempt_output_cap_bytes": batch.ATTEMPT_OUTPUT_CAP_BYTES,
        "frozen_input_bundle_sha256": frozen,
        "sim_scan": scan,
        "isotope_store": isotope,
        "artifacts": post,
        "checks": dict(gate.checks),
        "errors": gate.errors,
    }
    return payload, gate.errors


def _receipt_payload(validation: dict[str, Any], validation_path: Path) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "PASS__P0_JOB_MERGE_ELIGIBLE",
        "batch_id": batch.BATCH_ID,
        "campaign_version": batch.CAMPAIGN_VERSION,
        "job_ordinal": validation["job_ordinal"],
        "cell_ordinal": validation["cell_ordinal"],
        "cell_key": validation["cell_key"],
        "geometry": validation["geometry"],
        "mode": validation["mode"],
        "family": "p",
        "band": validation["band"],
        "band_index": validation["band_index"],
        "shard": validation["shard"],
        "events": validation["events"],
        "seed": validation["seed"],
        "selected_attempt": validation["attempt"],
        "attempt_validation": p0.rel(validation_path),
        "attempt_validation_sha256": p0.sha256(validation_path),
        "flux_cm2_s": validation["flux_cm2_s"],
        "band_flux_weight": validation["band_flux_weight"],
        "TT_s_from_log": validation["TT_s_from_log"],
        "TT_s_from_isotope_dat": validation["TT_s_from_isotope_dat"],
        "TT_s_expected_mean_from_events_flux_area": validation["TT_s_expected_mean_from_events_flux_area"],
        "TT_authority": validation["TT_authority"],
        "peak_process_group_rss_bytes": validation["peak_process_group_rss_bytes"],
        "sim_scan": validation["sim_scan"],
        "isotope_store": validation["isotope_store"],
        "artifacts": validation["artifacts"],
    }


def _publish_pair(
    report_path: Path,
    ledger_path: Path,
    expected_report: dict[str, Any],
    ledger_builder: Any,
    *,
    check: bool,
) -> None:
    report_exists = report_path.is_file()
    ledger_exists = ledger_path.is_file()
    if ledger_exists and not report_exists:
        raise RuntimeError("canonical ledger exists without its bound report")
    if check and not (report_exists and ledger_exists):
        raise RuntimeError("canonical report+ledger pair is absent")
    if report_exists:
        if _strict(report_path) != expected_report:
            raise RuntimeError(f"canonical report differs from live validation: {p0.rel(report_path)}")
    elif check:
        raise RuntimeError("canonical report is absent")
    else:
        p0.atomic_write_once_json(report_path, expected_report)
    expected_ledger = ledger_builder(p0.sha256(report_path))
    if ledger_exists:
        if _strict(ledger_path) != expected_ledger:
            raise RuntimeError(f"canonical ledger differs from expected: {p0.rel(ledger_path)}")
    elif check:
        raise RuntimeError("canonical ledger is absent")
    else:
        p0.atomic_write_once_json(ledger_path, expected_ledger)


def write_job(job_ordinal: int, attempt: int) -> int:
    validation, errors = validate_attempt(job_ordinal, attempt)
    if errors:
        print(json.dumps(validation, indent=2, sort_keys=True, allow_nan=False))
        return 1
    paths = _expected_paths(job_ordinal, attempt)
    validation_path = paths["attempt_validation"]
    receipt_path = batch.receipt_path(job_ordinal)
    p0.atomic_write_once_json(validation_path, validation)
    expected_receipt = _receipt_payload(validation, validation_path)
    if receipt_path.is_file():
        if _strict(receipt_path) != expected_receipt:
            raise RuntimeError("existing job receipt differs from live revalidation")
    else:
        p0.atomic_write_once_json(receipt_path, expected_receipt)
    print(json.dumps({"status": expected_receipt["status"], "job_ordinal": job_ordinal, "attempt": attempt}))
    return 0


def _load_live_receipt(job_ordinal: int) -> tuple[dict[str, Any], dict[str, Any]]:
    receipt_path = batch.receipt_path(job_ordinal)
    if not receipt_path.is_file():
        raise RuntimeError(f"job{job_ordinal:04d}: receipt absent")
    receipt = _strict(receipt_path)
    selected = receipt.get("selected_attempt")
    if type(selected) is not int:
        raise RuntimeError(f"job{job_ordinal:04d}: receipt selected_attempt is not integer")
    validation, errors = validate_attempt(job_ordinal, selected)
    if errors:
        raise RuntimeError(f"job{job_ordinal:04d}: live revalidation FAIL: {errors[:3]}")
    path = _expected_paths(job_ordinal, selected)["attempt_validation"]
    if not path.is_file() or _strict(path) != validation:
        raise RuntimeError(f"job{job_ordinal:04d}: canonical attempt validation absent/different")
    expected = _receipt_payload(validation, path)
    if receipt != expected:
        raise RuntimeError(f"job{job_ordinal:04d}: receipt differs from exact expected payload")
    return validation, receipt


def _sum_prompt(validations: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(validations)
    total_tt = math.fsum(float(row["TT_s_from_isotope_dat"]) for row in rows)
    counts: dict[str, int] = {
        "raw_tes_positive_events": sum(int(row["sim_scan"]["prompt"]["raw_tes_positive_events"]) for row in rows),
        "raw_tes_480_550_events": sum(int(row["sim_scan"]["prompt"]["raw_tes_480_550_events"]) for row in rows),
    }
    for label in ("veto_survivors_tes_positive", "veto_survivors_tes_480_550"):
        for threshold in ("50", "70", "80"):
            counts[f"{label}_{threshold}keV"] = sum(
                int(row["sim_scan"]["prompt"][label][threshold]) for row in rows
            )
    return {"sum_TT_s": total_tt, "counts": counts, "rates_s-1": {key: value / total_tt for key, value in counts.items()}}


def _sum_rp(validations: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int, float], float] = defaultdict(float)
    for validation in validations:
        for row in validation["isotope_store"]["RP_totals_by_volume_isotope_state"]:
            grouped[(str(row["volume"]), int(row["isotope_id"]), float(row["excitation_keV"]))] += float(row["sum_RP"])
    return [
        {"volume": key[0], "isotope_id": key[1], "excitation_keV": key[2], "sum_RP": value}
        for key, value in sorted(grouped.items())
    ]


def validate_cell(cell_key: str) -> tuple[dict[str, Any], dict[str, Any]]:
    contract = _strict(batch.GLOBAL_CONTRACT)
    manifest = p0.load_source_manifest(required=True) or {}
    gate = Gate()
    _validate_contract(contract, gate)
    if gate.errors:
        raise RuntimeError("global contract FAIL: " + " | ".join(gate.errors[:5]))
    cell_rows = [row for row in batch.jobs(manifest) if row["cell_key"] == cell_key]
    if len(cell_rows) != 4:
        raise RuntimeError(f"unknown/incomplete P0 cell {cell_key!r}")
    validations: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    for spec in cell_rows:
        validation, receipt = _load_live_receipt(int(spec["job_ordinal"]))
        validations.append(validation)
        receipts.append(receipt)
    events = sum(int(row["events"]) for row in validations)
    seeds = [int(row["seed"]) for row in validations]
    if events != p0.EVENTS_PER_CELL or len(seeds) != len(set(seeds)):
        raise RuntimeError(f"{cell_key}: 256-event/unique-seed closure failed")
    mode = str(cell_rows[0]["mode"])
    band_record = next(row for row in manifest["bands"] if row["key"] == cell_rows[0]["band"])
    sum_tt = math.fsum(float(row["TT_s_from_isotope_dat"]) for row in validations)
    prompt_summary = _sum_prompt(validations) if mode == "instant" else None
    buildup_summary = _sum_rp(validations) if mode == "buildup" else None
    report = {
        "schema_version": 1,
        "status": "PASS__P0_CELL_MERGE_ELIGIBLE",
        "batch_id": batch.BATCH_ID,
        "campaign_version": batch.CAMPAIGN_VERSION,
        "cell_key": cell_key,
        "cell_ordinal": cell_rows[0]["cell_ordinal"],
        "geometry": cell_rows[0]["geometry"],
        "mode": mode,
        "family": "p",
        "band": cell_rows[0]["band"],
        "band_index": cell_rows[0]["band_index"],
        "band_flux_cm2_s": band_record["flux_cm2_s"],
        "band_flux_weight": band_record["weight"],
        "events": events,
        "jobs": 4,
        "seeds": seeds,
        "sum_TT_s": sum_tt,
        "TT_authority": TT_AUTHORITY,
        "prompt_summary": prompt_summary,
        "buildup_RP_by_volume_isotope_state": buildup_summary,
        "job_receipts": [
            {"path": p0.rel(batch.receipt_path(int(row["job_ordinal"]))), "sha256": p0.sha256(batch.receipt_path(int(row["job_ordinal"])))}
            for row in cell_rows
        ],
        "errors": [],
    }
    ledger = {
        "schema_version": 1,
        "status": "PASS__P0_CELL_MERGE_ELIGIBLE",
        "batch_id": batch.BATCH_ID,
        "campaign_version": batch.CAMPAIGN_VERSION,
        "cell_key": cell_key,
        "validation_report": p0.rel(batch.cell_report_path(cell_key)),
        "validation_report_sha256": "__REPORT_SHA__",
        "events": events,
        "sum_TT_s": sum_tt,
        "band": cell_rows[0]["band"],
        "band_index": cell_rows[0]["band_index"],
        "band_flux_cm2_s": band_record["flux_cm2_s"],
        "band_flux_weight": band_record["weight"],
        "prompt_summary": prompt_summary,
        "buildup_RP_by_volume_isotope_state": buildup_summary,
        "jobs": receipts,
    }
    return report, ledger


def write_cell(cell_key: str, *, check: bool) -> int:
    report, ledger = validate_cell(cell_key)
    _publish_pair(
        batch.cell_report_path(cell_key),
        batch.cell_ledger_path(cell_key),
        report,
        lambda digest: {**ledger, "validation_report_sha256": digest},
        check=check,
    )
    print(json.dumps({"status": report["status"], "cell_key": cell_key}))
    return 0


def _prompt_weighted_recomposition(geometry: str, ledgers: list[dict[str, Any]]) -> dict[str, Any]:
    if len(ledgers) != 6:
        raise RuntimeError(f"{geometry}: prompt recomposition does not have six bands")
    metric_names = sorted(ledgers[0]["prompt_summary"]["counts"])
    metrics: dict[str, Any] = {}
    for metric in metric_names:
        contributions: list[dict[str, Any]] = []
        rate = 0.0
        weighted_efficiency = Decimal(0)
        for ledger in sorted(ledgers, key=lambda row: int(row["band_index"])):
            count = int(ledger["prompt_summary"]["counts"][metric])
            tt_s = float(ledger["sum_TT_s"])
            weight = Decimal(str(ledger["band_flux_weight"]))
            contribution = count / tt_s
            rate += contribution
            weighted_efficiency += weight * Decimal(count) / Decimal(int(ledger["events"]))
            contributions.append(
                {
                    "band": ledger["band"],
                    "count": count,
                    "sum_TT_s": tt_s,
                    "rate_contribution_s-1": contribution,
                    "band_flux_weight": ledger["band_flux_weight"],
                }
            )
        metrics[metric] = {
            "physical_rate_s-1": rate,
            "flux_weighted_per_primary_efficiency": p0.decimal_to_json(weighted_efficiency),
            "band_contributions": contributions,
        }
    return {
        "geometry": geometry,
        "policy": "sum over six bands of selected_count_band/sum_TT_band",
        "forbidden": "sum(all counts)/sum(all band TT)",
        "metrics": metrics,
    }


def _activation_weighted_recomposition(geometry: str, ledgers: list[dict[str, Any]]) -> dict[str, Any]:
    if len(ledgers) != 6:
        raise RuntimeError(f"{geometry}: activation recomposition does not have six bands")
    ordered = sorted(ledgers, key=lambda row: int(row["band_index"]))
    state_keys = sorted(
        {
            (str(row["volume"]), int(row["isotope_id"]), float(row["excitation_keV"]))
            for ledger in ordered
            for row in ledger["buildup_RP_by_volume_isotope_state"]
        }
    )
    rp_lookup: dict[tuple[str, tuple[str, int, float]], float] = {}
    band_totals: list[dict[str, Any]] = []
    for ledger in ordered:
        total_rp = 0.0
        for row in ledger["buildup_RP_by_volume_isotope_state"]:
            key = (str(row["volume"]), int(row["isotope_id"]), float(row["excitation_keV"]))
            rp = float(row["sum_RP"])
            rp_lookup[(str(ledger["band"]), key)] = rp
            total_rp += rp
        band_totals.append(
            {
                "band": ledger["band"],
                "sum_RP_all_states": total_rp,
                "sum_TT_s": float(ledger["sum_TT_s"]),
                "is_explicit_zero_RP_band": total_rp == 0.0,
            }
        )
    grouped: dict[tuple[str, int, float], dict[str, Any]] = {}
    for key in state_keys:
        entry = {
            "volume": key[0],
            "isotope_id": key[1],
            "excitation_keV": key[2],
            "production_rate_s-1": 0.0,
            "band_contributions": [],
        }
        for ledger in ordered:
            tt_s = float(ledger["sum_TT_s"])
            rp = rp_lookup.get((str(ledger["band"]), key), 0.0)
            contribution = rp / tt_s
            entry["production_rate_s-1"] += contribution
            entry["band_contributions"].append(
                {
                    "band": ledger["band"],
                    "sum_RP": rp,
                    "sum_TT_s": tt_s,
                    "rate_contribution_s-1": contribution,
                    "is_explicit_zero": rp == 0.0,
                }
            )
        grouped[key] = entry
    return {
        "geometry": geometry,
        "policy": "sum over six bands of RP_band/sum_TT_band by volume+isotope+state",
        "zero_RP_band_policy": "valid positive TT remains an explicit zero contribution",
        "band_totals_including_zero": band_totals,
        "states": [grouped[key] for key in sorted(grouped)],
    }


def validate_final(*, check_cells: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    contract = _strict(batch.GLOBAL_CONTRACT)
    contract_hash_pre = p0.sha256(batch.GLOBAL_CONTRACT)
    manifest = p0.load_source_manifest(required=True) or {}
    gate = Gate()
    _validate_contract(contract, gate)
    if gate.errors:
        raise RuntimeError("global contract FAIL: " + " | ".join(gate.errors[:5]))
    source_semantics_pre = validate_source_package(manifest)
    # Revalidate predecessor immediately before commit; this is supervised by the runner deadline.
    inherited_deadline = datetime.fromisoformat(str(contract["execution"]["frozen_deadline_utc"]))
    batch._validate_batch4_authority(require=True, deadline=inherited_deadline, run_check=True)
    cell_ledgers: list[dict[str, Any]] = []
    for cell in batch.cells(manifest):
        write_cell(str(cell["cell_key"]), check=check_cells)
        cell_ledgers.append(_strict(batch.cell_ledger_path(str(cell["cell_key"]))))
    job_receipts = [_strict(batch.receipt_path(index)) for index in range(1, p0.JOB_COUNT + 1)]
    seeds = [int(row["seed"]) for row in job_receipts]
    if len(job_receipts) != 96 or sum(int(row["events"]) for row in job_receipts) != 6144 or len(seeds) != len(set(seeds)):
        raise RuntimeError("final 96-job/6144-primary/unique-seed closure failed")
    prompt_recomposition: list[dict[str, Any]] = []
    activation_recomposition: list[dict[str, Any]] = []
    for geometry in p0.GEOMETRIES:
        instant = [row for row in cell_ledgers if row["jobs"][0]["geometry"] == geometry and row["jobs"][0]["mode"] == "instant"]
        buildup = [row for row in cell_ledgers if row["jobs"][0]["geometry"] == geometry and row["jobs"][0]["mode"] == "buildup"]
        prompt = _prompt_weighted_recomposition(geometry, instant)
        prompt["band_cell_ledgers"] = [
            {"cell_key": row["cell_key"], "path": p0.rel(batch.cell_ledger_path(row["cell_key"])), "sha256": p0.sha256(batch.cell_ledger_path(row["cell_key"]))}
            for row in instant
        ]
        prompt_recomposition.append(prompt)
        activation = _activation_weighted_recomposition(geometry, buildup)
        activation["band_cell_ledgers"] = [
            {"cell_key": row["cell_key"], "path": p0.rel(batch.cell_ledger_path(row["cell_key"])), "sha256": p0.sha256(batch.cell_ledger_path(row["cell_key"]))}
            for row in buildup
        ]
        activation_recomposition.append(activation)
    source_semantics_post = validate_source_package(manifest)
    if source_semantics_post != source_semantics_pre:
        raise RuntimeError("source semantic validation changed during final scan")
    if p0.sha256(batch.GLOBAL_CONTRACT) != contract_hash_pre:
        raise RuntimeError("global contract changed during final validation")
    report = {
        "schema_version": 1,
        "status": "PASS__PROTON_P0_SIXBAND_WEIGHTED_PILOT",
        "batch_id": batch.BATCH_ID,
        "campaign_version": batch.CAMPAIGN_VERSION,
        "authority_boundary": contract["authority_boundary"],
        "transport_jobs": 96,
        "primaries": 6144,
        "geometries": 2,
        "modes": 2,
        "bands": 6,
        "full_stat_claim": False,
        "cut_modified": False,
        "source_semantics": source_semantics_post,
        "prompt_weighted_recomposition": prompt_recomposition,
        "activation_weighted_recomposition": activation_recomposition,
        "cell_authorities": [
            {"cell_key": row["cell_key"], "path": p0.rel(batch.cell_ledger_path(row["cell_key"])), "sha256": p0.sha256(batch.cell_ledger_path(row["cell_key"]))}
            for row in cell_ledgers
        ],
        "errors": [],
    }
    ledger = {
        "schema_version": 1,
        "status": report["status"],
        "batch_id": batch.BATCH_ID,
        "campaign_version": batch.CAMPAIGN_VERSION,
        "validation_report": p0.rel(batch.FINAL_REPORT),
        "validation_report_sha256": "__REPORT_SHA__",
        "global_contract": p0.rel(batch.GLOBAL_CONTRACT),
        "global_contract_sha256": p0.sha256(batch.GLOBAL_CONTRACT),
        "conditional_source_manifest": p0.rel(p0.SOURCE_MANIFEST),
        "conditional_source_manifest_sha256": p0.sha256(p0.SOURCE_MANIFEST),
        "predecessor": contract["predecessor"],
        "transport_core": contract["transport_core"],
        "geometry_bundles": contract["geometry_bundles"],
        "transport_jobs": 96,
        "primaries": 6144,
        "full_stat_claim": False,
        "automatic_delete": False,
        "prompt_weighted_recomposition": prompt_recomposition,
        "activation_weighted_recomposition": activation_recomposition,
        "cells": cell_ledgers,
    }
    return report, ledger


def write_final(*, check: bool) -> int:
    report, ledger = validate_final(check_cells=check)
    _publish_pair(
        batch.FINAL_REPORT,
        batch.FINAL_LEDGER,
        report,
        lambda digest: {**ledger, "validation_report_sha256": digest},
        check=check,
    )
    print(json.dumps({"status": report["status"], "transport_jobs": 96, "primaries": 6144}))
    return 0


def preflight() -> int:
    if not p0.SOURCE_MANIFEST.is_file():
        print(
            json.dumps(
                {
                    "status": "WAIT__P0_SIXBAND_SCIENCE_CONTRACT_NOT_FROZEN",
                    "transport_launched": False,
                    "canonical_outputs_written": False,
                    "source_manifest": p0.rel(p0.SOURCE_MANIFEST),
                },
                indent=2,
            )
        )
        return 0
    manifest = p0.load_source_manifest(required=True) or {}
    result = validate_source_package(manifest)
    predecessor = batch._validate_batch4_authority(require=False, deadline=None, run_check=False)
    print(json.dumps({**result, "transport_launched": False, "predecessor": predecessor}, indent=2, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preflight", action="store_true")
    group.add_argument("--job", type=int)
    group.add_argument("--cell")
    group.add_argument("--final", action="store_true")
    parser.add_argument("--attempt", type=int)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        if args.preflight:
            if args.attempt is not None or args.check:
                parser.error("--preflight does not accept --attempt/--check")
            return preflight()
        if args.job is not None:
            if args.attempt is None or args.check:
                parser.error("--job requires --attempt and does not accept --check")
            return write_job(args.job, args.attempt)
        if args.attempt is not None:
            parser.error("--attempt is only valid with --job")
        if args.cell is not None:
            return write_cell(args.cell, check=args.check)
        return write_final(check=args.check)
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "errors": [str(exc)]}, indent=2, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
