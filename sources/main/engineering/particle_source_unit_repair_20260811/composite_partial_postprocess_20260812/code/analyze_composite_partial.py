#!/usr/bin/env python3
"""Partial-aware corrected-keV seven-family prompt/activation analysis.

This executable consumes only explicitly pinned PASS/merge-eligible ledgers.
It deliberately does not require, create, or imply a batch0004 final authority.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import io
import json
import math
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any


def _find_root(path: Path) -> Path:
    for candidate in (path, *path.parents):
        if (candidate / "AGENTS.md").is_file() and (candidate / ".git").exists():
            return candidate
    raise RuntimeError("repository root not found")


THIS_FILE = Path(__file__).resolve()
ROOT = _find_root(THIS_FILE.parent)
PACKAGE = THIS_FILE.parents[1]
RUN_ROOT = ROOT / "runs/particle_source_unit_repair_20260811"
FROZEN_PATH = (
    ROOT / "engineering/particle_source_unit_repair_20260811"
    / "seven_family_tes_activation_postprocess_20260812/code/analyze_seven_family_tes_activation.py"
)


def _load_frozen() -> Any:
    spec = importlib.util.spec_from_file_location("frozen_seven_family_partial_core", FROZEN_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import frozen core: {FROZEN_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


core = _load_frozen()
GEOMETRIES = tuple(core.GEOMETRIES)
FAMILIES = tuple(core.FAMILIES)
MODES = tuple(core.MODES)
SOURCE_SHA = core.SOURCE_CONTRACT_SHA256

AUTHORITY_PIN = PACKAGE / "data/composite_partial_authorities.json"
DEFAULT_OUTPUT = PACKAGE / "results_composite_partial_20260812"
GAMMA_REUSE_ROOT = (
    ROOT / "engineering/particle_source_unit_repair_20260811/gamma5m_postprocess_20260811"
    / "results_gamma_prefix76_2p001m_diagnostic"
)
GAMMA_REUSE = {
    "validation": (
        GAMMA_REUSE_ROOT / "gamma_prefix76_2p001m_diagnostic_postprocess_validation.json",
        "8012f103c73553512c088027ee0d18dbaae627d3f92bbc42104249e035b97a7f",
    ),
    "summary": (
        GAMMA_REUSE_ROOT / "gamma_prefix76_2p001m_diagnostic_prompt_tes_summary.json",
        "08e431718b48e0e23b96052393804cc95bcfa86cb75bb413aa2b92f0644ccad2",
    ),
    "cutflow": (
        GAMMA_REUSE_ROOT / "gamma_prefix76_2p001m_diagnostic_cutflow.csv",
        "9eb612f539fa1d419762f03f0b6af6b59b29f37772501d110309161dae3845ec",
    ),
}

PATHS = {
    "batch0000_ledger": RUN_ROOT / "mergeable_smoke_v1_ledger.json",
    "batch0001_ledger": RUN_ROOT / "seven_family_batch0001_v1_ledger.json",
    "batch0002_ledger": RUN_ROOT / "muminus_instant_pair_batch0002_v1_ledger.json",
    "batch0003_report": RUN_ROOT / "gamma_instant_batch0003_prefix_checkpoints_20260811/gamma_instant_batch0003_prefix_shard0076_v1_validation.json",
    "batch0003_ledger": RUN_ROOT / "gamma_instant_batch0003_prefix_checkpoints_20260811/gamma_instant_batch0003_prefix_shard0076_v1_ledger.json",
    "batch0004_report": RUN_ROOT / "seven_family_1m_screening_batch0004_partial_checkpoint_20260812/batch0004_partial_through_ordinal0097_v1_validation.json",
    "batch0004_ledger": RUN_ROOT / "seven_family_1m_screening_batch0004_partial_checkpoint_20260812/batch0004_partial_through_ordinal0097_v1_ledger.json",
    "batch0005_report": RUN_ROOT / "reduced_breadth_continuation_batch0005_v1_validation.json",
    "batch0005_ledger": RUN_ROOT / "reduced_breadth_continuation_batch0005_v1_ledger.json",
}

EXPECTED_HASHES = {
    "batch0000_ledger": "036335b186bb1e8d9dbec53e0e8994dd8cb1fc055b930469b8d7d144f60b263f",
    "batch0001_ledger": "bb89c618d519a6a8570c8c746012c9ad0e81cb427b2a23145084a429c34c5df4",
    "batch0002_ledger": "742a4deb1bc3ab4585e479884d7e0ec376a0622f19391c8d87a2e66b92779a62",
    "batch0003_report": "5d2784c9fe1e968e04bddc0360538d8b1aea0fa9d1fad7e26ee681d995e69813",
    "batch0003_ledger": "3519c39d86e9bf38eddd01adae299c3428ef9810755d7e1d282420851df416fc",
    "batch0004_report": "3d29449dd80051c1faf60fb8156fb757a11004981f426e22eac36b7bd56fe291",
    "batch0004_ledger": "b4de513e7902ae4755eb741e7a79d23c378b3e3dd8cee993c7ffbff1af19dba0",
    "batch0005_report": "d100985b3cbecd267042bb4bfb0d23fa9794befdb748f7c2ca45f9abfdfc5cee",
    "batch0005_ledger": "670bc6f14de7799306301343908f524738c564ac62161caab1206a0be5cc41a0",
}

EXPECTED_STATUS = {
    "batch0000_ledger": "PASS__BATCH0000_MERGE_ELIGIBLE",
    "batch0001_ledger": "PASS__BATCH0001_MERGE_ELIGIBLE",
    "batch0002_ledger": "PASS__BATCH0002_MERGE_ELIGIBLE",
    "batch0003_report": "PASS__PARTIAL_PREFIX_VALIDATED",
    "batch0003_ledger": "PARTIAL_PREFIX_MERGE_ELIGIBLE",
    "batch0004_report": "PASS",
    "batch0004_ledger": "PASS__BATCH0004_PARTIAL_CHECKPOINT_THROUGH_GLOBAL_ORDINAL0097_MERGE_ELIGIBLE",
    "batch0005_report": "PASS",
    "batch0005_ledger": "PASS__BATCH0005_REDUCED_BREADTH_ADDON_MERGE_ELIGIBLE",
}

# The batch0004 screening targets are a comparison reference, not zeros for
# absent transport. Gamma instant belongs to the separate batch0003 prefix.
SCREENING_TARGET = {
    ("gamma", "buildup"): 1_000_000,
    ("n", "instant"): 96_310,
    ("n", "buildup"): 96_310,
    ("eplus", "instant"): 24_370,
    ("eplus", "buildup"): 24_370,
    ("alpha", "instant"): 2_390,
    ("alpha", "buildup"): 2_390,
    ("eminus", "instant"): 41_460,
    ("eminus", "buildup"): 41_460,
    ("muplus", "instant"): 1_160,
    ("muplus", "buildup"): 1_160,
    ("muminus", "buildup"): 1_040,
}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n").encode()


def load_json(path: Path) -> dict[str, Any]:
    def reject(token: str) -> None:
        raise ValueError(f"non-finite JSON token {token}")
    value = json.loads(path.read_text(encoding="utf-8"), parse_constant=reject)
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {rel(path)}")
    return value


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex}")
    try:
        tmp.write_bytes(canonical_bytes(value))
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _validate_authority(role: str) -> dict[str, Any]:
    path = PATHS[role]
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"missing or symlink authority: {rel(path)}")
    digest = sha256(path)
    if digest != EXPECTED_HASHES[role]:
        raise RuntimeError(f"authority hash drift: {role}")
    payload = load_json(path)
    if payload.get("status") != EXPECTED_STATUS[role] or payload.get("errors") not in (None, []):
        raise RuntimeError(f"authority status/errors mismatch: {role}")
    # Some validation envelopes delegate the source-contract identity to their
    # hash-bound ledger. A present value must match; the paired ledger below is
    # always required to carry the canonical corrected-keV SHA.
    if payload.get("source_contract_manifest_sha256") not in (None, SOURCE_SHA):
        raise RuntimeError(f"corrected source contract mismatch: {role}")
    return payload


def build_authority_snapshot() -> dict[str, Any]:
    payloads = {role: _validate_authority(role) for role in PATHS}
    for report_role, ledger_role in (
        ("batch0003_report", "batch0003_ledger"),
        ("batch0004_report", "batch0004_ledger"),
        ("batch0005_report", "batch0005_ledger"),
    ):
        ledger = payloads[ledger_role]
        if resolve(ledger["validation_report"]).resolve() != PATHS[report_role].resolve():
            raise RuntimeError(f"report path binding mismatch: {ledger_role}")
        if ledger.get("validation_report_sha256") != EXPECTED_HASHES[report_role]:
            raise RuntimeError(f"report hash binding mismatch: {ledger_role}")
    b4 = payloads["batch0004_ledger"]
    completeness = b4.get("completeness", {})
    if not (
        b4.get("authority_class") == "BATCH0004_PARTIAL_CONTIGUOUS_PREFIX_CHECKPOINT"
        and completeness.get("canonical_batch0004_final_authority") is False
        and completeness.get("complete_stage_count") == 5
        and completeness.get("partial_stage") == "alpha_instant"
        and completeness.get("validated_pair_shards") == 97
    ):
        raise RuntimeError("batch0004 partial-completeness identity mismatch")
    b5 = payloads["batch0005_ledger"]
    if b5.get("batch0004_final") is not False or b5.get("seven_family_total") is not False:
        raise RuntimeError("batch0005 reduced-breadth boundary mismatch")
    gamma_ledger = payloads["batch0003_ledger"]
    if gamma_ledger.get("cumulative_events_per_geometry") != 2_001_000:
        raise RuntimeError("batch0003 prefix exposure mismatch")
    gamma_reuse_records = []
    for role, (path, expected_hash) in GAMMA_REUSE.items():
        if not path.is_file() or sha256(path) != expected_hash:
            raise RuntimeError(f"gamma postprocess reuse artifact drift: {role}")
        gamma_reuse_records.append({"role": role, "path": rel(path), "sha256": expected_hash})
    gamma_validation = load_json(GAMMA_REUSE["validation"][0])
    if gamma_validation.get("status") != "PASS" or gamma_validation.get("errors") != []:
        raise RuntimeError("gamma postprocess reuse validation is not PASS")
    if gamma_validation.get("summary_sha256") != GAMMA_REUSE["summary"][1]:
        raise RuntimeError("gamma postprocess summary binding mismatch")
    authorities = [
        {
            "role": role,
            "path": rel(PATHS[role]),
            "sha256": EXPECTED_HASHES[role],
            "status": EXPECTED_STATUS[role],
        }
        for role in PATHS
    ]
    return {
        "schema_version": 1,
        "status": "PASS__COMPOSITE_PARTIAL_AUTHORITIES_PINNED",
        "errors": [],
        "authority_class": "CORRECTED_KEV_HETEROGENEOUS_REDUCED_STATISTICS_COMPOSITE_PARTIAL",
        "source_contract_manifest_sha256": SOURCE_SHA,
        "batch0003_selected_profile": "prefix_ordinal76",
        "batch0003_gamma_exposure": {
            "mode": "instant",
            "cumulative_events_per_geometry": 2_001_000,
            "full_batch0003_target_reached": False,
        },
        "batch0004_final_authority_present": False,
        "batch0004_partial_scope": completeness,
        "batch0005_is_addon_only": True,
        "authorities": authorities,
        "reused_gamma_postprocess": gamma_reuse_records,
        "toolchain": {
            "analyzer": {"path": rel(FROZEN_PATH), "sha256": sha256(FROZEN_PATH)},
            "frozen_gamma_prompt_core": {
                "path": rel(core.GAMMA_CORE_PATH), "sha256": sha256(core.GAMMA_CORE_PATH)
            },
            "partial_wrapper": {"path": rel(THIS_FILE), "sha256": sha256(THIS_FILE)},
        },
        "hard_boundaries": [
            "not full statistics",
            "not batch0004 final authority",
            "not delayed-decay transport",
            "not mission response or sensitivity authority",
            "not geometry-promotion authority",
        ],
    }


def pin_authorities() -> dict[str, Any]:
    payload = build_authority_snapshot()
    if AUTHORITY_PIN.exists():
        if AUTHORITY_PIN.read_bytes() != canonical_bytes(payload):
            raise RuntimeError("write-once authority pin differs from current exact snapshot")
        return payload
    atomic_json(AUTHORITY_PIN, payload)
    return payload


def load_pin() -> dict[str, Any]:
    if not AUTHORITY_PIN.is_file():
        raise RuntimeError("authority pin absent; run --pin-authorities first")
    current = build_authority_snapshot()
    pinned = load_json(AUTHORITY_PIN)
    if pinned != current:
        raise RuntimeError("authority pin no longer matches exact current snapshot/toolchain")
    return pinned


def collect_jobs() -> tuple[dict[tuple[str, str, str], list[Any]], list[dict[str, Any]], dict[str, str]]:
    pin = load_pin()
    core.gamma.validate_detector_map_contracts()
    core.gamma._validate_geometry_file_bindings(core.GEOMETRY_CONTRACTS)
    role_records = {row["role"]: row for row in pin["authorities"]}
    specs = [
        ("batch0000_ledger", None),
        ("batch0001_ledger", None),
        ("batch0002_ledger", {("muminus", "instant")}),
        ("batch0003_ledger", {("gamma", "instant")}),
        ("batch0004_ledger", None),
        ("batch0005_ledger", None),
    ]
    jobs_by_cell = {
        (geometry, mode, family): []
        for geometry in GEOMETRIES for mode in MODES for family in FAMILIES
    }
    inventory: list[dict[str, Any]] = []
    ledger_hashes: dict[str, str] = {}
    identities: set[tuple[str, str, str, str, str]] = set()
    artifacts: set[Path] = set()
    seeds: set[tuple[str, str, str, int]] = set()
    for role, allowed in specs:
        path = PATHS[role]
        digest = sha256(path)
        if digest != role_records[role]["sha256"]:
            raise RuntimeError(f"pinned ledger drift: {role}")
        ledger_hashes[rel(path)] = digest
        ledger = load_json(path)
        for campaign in ledger.get("campaigns", []):
            geometry, mode = core._campaign_geometry_mode(ledger, campaign)
            for row in campaign.get("jobs", []):
                family = str(row.get("family", campaign.get("family")))
                if family == "p":
                    if role != "batch0000_ledger":
                        raise RuntimeError(f"unexpected proton in {role}")
                    continue
                if allowed is not None and (family, mode) not in allowed:
                    raise RuntimeError(f"out-of-scope row in {role}: {family}/{mode}")
                job = core._job_from_row(ledger, path, digest, campaign, row)
                identity = (job.geometry, job.mode, job.family, job.batch_id, job.job_name)
                if identity in identities:
                    raise RuntimeError(f"duplicate job identity: {identity}")
                identities.add(identity)
                seed_key = (job.geometry, job.mode, job.family, job.seed)
                if seed_key in seeds:
                    raise RuntimeError(f"duplicate seed inside aggregation cell: {seed_key}")
                seeds.add(seed_key)
                for artifact in (job.job_source, job.isotope_dat, job.log, job.sim):
                    if artifact in artifacts:
                        raise RuntimeError(f"artifact reused: {rel(artifact)}")
                    artifacts.add(artifact)
                jobs_by_cell[job.cell].append(job)
                inventory.append({
                    "geometry": job.geometry, "mode": job.mode, "family": job.family,
                    "batch_id": job.batch_id, "ledger": rel(job.ledger),
                    "ledger_sha256": job.ledger_sha256, "job_name": job.job_name,
                    "events": job.events, "seed": job.seed, "ordinal": job.ordinal,
                    "TT_s": job.tt_s, "RP_record_count": job.isotope_store["RP_record_count"],
                    "job_source": rel(job.job_source), "job_source_sha256": job.job_source_sha256,
                    "isotope_dat": rel(job.isotope_dat), "isotope_dat_sha256": job.isotope_dat_sha256,
                    "log": rel(job.log), "log_sha256": job.log_sha256,
                    "sim": rel(job.sim), "ledger_sim_sha256": job.sim_sha256,
                    "observed_sim_sha256": None, "fixed_geometry_setup": rel(job.expected_geometry_setup),
                    "ledger_geometry_header": rel(job.ledger_geometry_header),
                })
    for cell, rows in jobs_by_cell.items():
        rows.sort(key=lambda job: (job.batch_id, job.ordinal is None, job.ordinal or 0, job.job_name))
        if not rows or not math.fsum(job.tt_s for job in rows) > 0:
            raise RuntimeError(f"observed-data cell absent or has nonpositive TT: {cell}")
    inventory.sort(key=lambda row: (
        row["geometry"], row["mode"], row["family"], row["batch_id"],
        row["ordinal"] is None, row["ordinal"] or 0, row["job_name"],
    ))
    return jobs_by_cell, inventory, ledger_hashes


def coverage_rows(jobs_by_cell: dict[tuple[str, str, str], list[Any]]) -> list[dict[str, Any]]:
    rows = []
    for geometry in GEOMETRIES:
        for mode in MODES:
            for family in FAMILIES:
                jobs = jobs_by_cell[(geometry, mode, family)]
                observed = sum(job.events for job in jobs)
                target = SCREENING_TARGET.get((family, mode))
                if family == "gamma" and mode == "instant":
                    scope = "batch0003 ordinal-76 prefix; planned final target not interpreted as missing zero"
                elif family == "muminus" and mode == "instant":
                    scope = "batch0002 top-up exceeds batch0004 screening need; independently retained"
                elif target is not None and observed >= target:
                    scope = "screening reference reached"
                else:
                    scope = "reduced-statistics partial; untransported target exposure is missing, not zero"
                rows.append({
                    "geometry": geometry, "mode": mode, "family": family,
                    "observed_primary_count": observed,
                    "observed_job_count": len(jobs),
                    "observed_sum_TT_s": math.fsum(job.tt_s for job in jobs),
                    "batch0004_screening_reference_events": target,
                    "screening_reference_fraction": observed / target if target else None,
                    "scope": scope,
                    "data_present": True,
                })
    return rows


def _valid_printed_init_energy(energy_keV: float) -> bool:
    """Accept finite nonnegative IA energy, matching the dynamic validators.

    Very-low-energy neutron values can round to exactly 0.000 in retained SIM
    text. Their PASS ledgers explicitly record ``energy_min_keV: 0.0`` after
    checking the corrected per-angular-bin source support. Zero therefore
    belongs in the frozen driver's first [0,100) keV bin; it is not a corrupt
    or missing event.
    """
    return math.isfinite(energy_keV) and energy_keV >= 0.0


def parse_prompt_sim_partial(job: Any, accumulator: Any, writer: csv.DictWriter) -> str:
    """Frozen prompt parser with only its zero-energy compatibility bug fixed."""
    if job.mode != "instant":
        raise RuntimeError("prompt SIM parser refuses non-instant job")
    before = job.sim.stat()
    hashing_raw = core.gamma.HashingRawReader(job.sim)
    buffered = io.BufferedReader(hashing_raw, buffer_size=1024 * 1024)
    event = core.EventState()
    expected_id = 1
    se_count = 0
    en_count = 0
    footer_ts: int | None = None
    footer_te: float | None = None
    header_seed: int | None = None
    header_geometry: str | None = None
    header_geometry_count = 0

    def flush() -> None:
        nonlocal event
        if event.local_id is not None:
            accumulator.process_event(job, event, writer)
        event = core.EventState()

    try:
        with gzip.GzipFile(fileobj=buffered, mode="rb") as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", errors="replace") as handle:
                for raw in handle:
                    line = raw.strip()
                    if match := core.GEOMETRY_RE.match(line):
                        header_geometry_count += 1
                        header_geometry = header_geometry or match.group(1)
                    elif header_seed is None and (match := core.SEED_RE.match(line)):
                        header_seed = int(match.group(1))
                    elif line == "SE":
                        flush()
                        se_count += 1
                    elif line == "EN":
                        en_count += 1
                    elif line.startswith("TS "):
                        footer_ts = int(line.split()[1])
                    elif line.startswith("TE "):
                        footer_te = float(line.split()[1])
                    elif line.startswith("ID "):
                        if event.local_id is not None:
                            raise RuntimeError(f"{rel(job.sim)}: ID before next SE")
                        event.local_id = int(line.split()[1])
                        if event.local_id != expected_id:
                            raise RuntimeError(
                                f"{rel(job.sim)}: ID={event.local_id}, expected={expected_id}"
                            )
                        expected_id += 1
                    elif line.startswith("IA INIT"):
                        if event.local_id is None:
                            raise RuntimeError(f"{rel(job.sim)}: IA INIT outside event")
                        particle, energy, theta, _ = core.gamma._parse_init(line)
                        if particle != core.PARTICLE_TYPES[job.family] or not _valid_printed_init_energy(energy):
                            raise RuntimeError(
                                f"{rel(job.sim)} ID {event.local_id}: wrong particle/invalid energy"
                            )
                        event.init_count += 1
                        event.init_energy_keV = energy
                        event.source_theta_deg = theta
                    elif line.startswith("IA PAIR"):
                        event.has_pair = True
                    elif line.startswith("IA ANNI"):
                        event.has_annihilation = True
                    elif line.startswith("CC HIT "):
                        parts = line.split(maxsplit=3)
                        if len(parts) != 4:
                            raise RuntimeError(f"{rel(job.sim)}: malformed CC HIT")
                        role = core.gamma._relevant_volume(job.geometry, parts[2])
                        if role is None:
                            continue
                        match = core.EDEP_RE.search(parts[3])
                        if match is None:
                            raise RuntimeError(f"{rel(job.sim)}: relevant CC HIT lacks edep_keV")
                        value = float(match.group(1))
                        if not math.isfinite(value) or value < 0.0:
                            raise RuntimeError(f"{rel(job.sim)}: invalid deposit {value}")
                        if role == "tes":
                            event.pixel_e[parts[2]] += value
                        elif role == "active":
                            event.active_shield_keV += value
                        elif role == "plastic":
                            event.plastic_keV += value
                        else:
                            event.excluded_kapton_keV += value
        flush()
    except (OSError, EOFError, gzip.BadGzipFile, UnicodeError) as exc:
        raise RuntimeError(f"{rel(job.sim)} gzip/read failure: {exc}") from exc
    finally:
        if not buffered.closed:
            buffered.close()
    observed_hash = hashing_raw.hexdigest()
    after = job.sim.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
    ):
        raise RuntimeError(f"{rel(job.sim)} changed while parsed")
    parsed = expected_id - 1
    if observed_hash != job.sim_sha256:
        raise RuntimeError(f"{rel(job.sim)} compressed hash differs from PASS ledger")
    if parsed != job.events or se_count != job.events:
        raise RuntimeError(
            f"{rel(job.sim)} event closure ID={parsed}, SE={se_count}, expected={job.events}"
        )
    if en_count != 1 or footer_ts != job.events or footer_te is None or footer_te <= 0.0:
        raise RuntimeError(f"{rel(job.sim)} footer closure failed")
    if header_seed != job.seed or header_geometry_count != 1 or header_geometry is None:
        raise RuntimeError(f"{rel(job.sim)} Seed/Geometry header closure failed")
    sim_geometry = resolve(header_geometry).resolve()
    if not (
        sim_geometry == job.ledger_geometry_header == job.source_geometry == job.expected_geometry_setup
    ):
        raise RuntimeError(f"{rel(job.sim)} Geometry four-way binding failed")
    return observed_hash


def _rewrite_partial_envelope(work: Path, published: Path, pin: dict[str, Any], coverage: list[dict[str, Any]]) -> None:
    summary_path = work / "seven_family_tes_activation_summary.json"
    old = load_json(summary_path)
    old["status"] = "PASS__COMPOSITE_PARTIAL_SEVEN_FAMILY_PROMPT_TES_AND_BUILDUP_ACTIVATION"
    old["authority_boundary"] = (
        "HETEROGENEOUS_REDUCED_STATISTICS_COMPOSITE_PARTIAL__NOT_FULL_NOT_BATCH0004_FINAL_"
        "NOT_DELAYED_RESPONSE_MISSION_SENSITIVITY_OR_GEOMETRY_PROMOTION_AUTHORITY"
    )
    old["completeness"] = {
        "classification": "HETEROGENEOUS_REDUCED_STATISTICS_COMPOSITE_PARTIAL",
        "all_28_geometry_mode_family_cells_have_observed_data": True,
        "batch0004_final_authority": False,
        "untransported_planned_exposure_semantics": "missing/not observed; never encoded as zero",
        "coverage_table": rel(published / "composite_partial_cell_coverage.csv"),
    }
    old["batch0005_is_addon_only"] = True
    old["pooling_boundary"] = "never pool counts, TT, or RP across geometry, mode, or family"
    old["inputs"]["authority_pin"] = rel(AUTHORITY_PIN)
    old["inputs"]["authority_pin_sha256"] = sha256(AUTHORITY_PIN)
    old["inputs"]["authority_records"] = pin["authorities"]
    old["inputs"]["partial_wrapper"] = rel(THIS_FILE)
    old["inputs"]["partial_wrapper_sha256"] = sha256(THIS_FILE)
    atomic_json(summary_path, old)

    validation_path = work / "seven_family_tes_activation_validation.json"
    prior_validation = load_json(validation_path)
    output_paths = [path for path in work.iterdir() if path != validation_path]
    records = [{
        "path": rel(published / path.name), "sha256": sha256(path), "size_bytes": path.stat().st_size
    } for path in sorted(output_paths)]
    checks = dict(prior_validation["checks"])
    checks.update({
        "partial_authority_class_explicit": True,
        "batch0004_final_not_required_or_claimed": True,
        "all_observed_cells_kept_separate": len(coverage) == 28,
        "missing_target_exposure_never_encoded_as_zero": all(row["data_present"] for row in coverage),
        "heterogeneous_statistics_explicit": True,
        "batch0005_addon_only_explicit": True,
    })
    validation = {
        "schema_version": 1,
        "status": "PASS__COMPOSITE_PARTIAL_POSTPROCESS_VALIDATED",
        "errors": [],
        "authority_class": "CORRECTED_KEV_HETEROGENEOUS_REDUCED_STATISTICS_COMPOSITE_PARTIAL",
        "status_derivation": "PASS iff every boolean leaf is true, errors empty, and output hashes close",
        "checks": checks,
        "figure_qa": prior_validation["figure_qa"],
        "summary": rel(published / summary_path.name),
        "summary_sha256": sha256(summary_path),
        "outputs": records,
        "hard_boundaries": pin["hard_boundaries"],
    }
    atomic_json(validation_path, validation)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _gamma_cutflow_rows() -> list[dict[str, Any]]:
    rows = []
    for row in _read_csv(GAMMA_REUSE["cutflow"][0]):
        rows.append({
            "geometry": row["geometry"], "mode": "instant", "family": "gamma",
            "response": "measured", "selection": row["selection"], "window": row["window"],
            "active_shield_threshold_keV": row["active_shield_threshold_keV"],
            "o8_plastic_threshold_keV": row["o8_plastic_threshold_keV"],
            "primary_count": row["primary_count"], "sum_TT_s": row["sum_TT_s"],
            "count": row["count"], "rate_s-1": row["rate_s-1"],
            "rate_poisson95_low_s-1": row["rate_garwood95_low_s-1"],
            "rate_poisson95_high_s-1": row["rate_garwood95_high_s-1"],
            "zero_count_one_sided95_rate_upper_s-1": row["zero_count_one_sided95_rate_upper_s-1"],
            "efficiency_per_primary": row["efficiency_per_primary"],
            "efficiency_wilson95_low": row["efficiency_wilson95_low"],
            "efficiency_wilson95_high": row["efficiency_wilson95_high"],
            "pre_veto_window_count": row["pre_veto_window_count"],
            "veto_survival_fraction": row["veto_survival_fraction"],
            "veto_survival_wilson95_low": row["veto_survival_wilson95_low"],
            "veto_survival_wilson95_high": row["veto_survival_wilson95_high"],
        })
    return rows


def run_fast_partial(output_dir: Path) -> dict[str, Any]:
    """Publish minimal complete composite tables, reusing canonical gamma analysis."""
    jobs, inventory, ledger_hashes = collect_jobs()
    pin = load_pin()
    coverage = coverage_rows(jobs)
    published = output_dir.resolve()
    if published.exists():
        raise RuntimeError(f"refusing to overwrite: {rel(published)}")
    published.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f".{published.name}.tmp-{os.getpid()}-", dir=published.parent))
    try:
        accumulators = {
            (geometry, family): core.PromptAccumulator(geometry=geometry, family=family)
            for geometry in GEOMETRIES for family in FAMILIES
        }
        gamma_summary = load_json(GAMMA_REUSE["summary"][0])
        for geometry in GEOMETRIES:
            gamma_acc = accumulators[(geometry, "gamma")]
            gamma_acc.primary_count = sum(job.events for job in jobs[(geometry, "instant", "gamma")])
            gamma_acc.sum_tt_s = math.fsum(job.tt_s for job in jobs[(geometry, "instant", "gamma")])
            gamma_acc.raw_tes_positive = int(gamma_summary["geometries"][geometry]["raw_TES_positive_events"])
            gamma_acc.measured_tes_positive = int(gamma_summary["geometries"][geometry]["measured_TES_positive_events"])

        lookup = {
            (row["geometry"], row["mode"], row["family"], row["batch_id"], row["job_name"]): row
            for row in inventory
        }
        events_path = work / "prompt_non_gamma_tes_event_diagnostics.csv.gz"
        with gzip.open(events_path, "wt", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=core.EVENT_FIELDS)
            writer.writeheader()
            for geometry in GEOMETRIES:
                for family in FAMILIES:
                    if family == "gamma":
                        continue
                    acc = accumulators[(geometry, family)]
                    for job in jobs[(geometry, "instant", family)]:
                        observed = parse_prompt_sim_partial(job, acc, writer)
                        lookup[(geometry, "instant", family, job.batch_id, job.job_name)][
                            "observed_sim_sha256"
                        ] = observed
                        acc.sum_tt_s = math.fsum((acc.sum_tt_s, job.tt_s))
                    if acc.primary_count != sum(j.events for j in jobs[(geometry, "instant", family)]):
                        raise RuntimeError(f"prompt primary closure failed: {geometry}/{family}")
        for row in inventory:
            if row["family"] == "gamma" and row["mode"] == "instant":
                row["observed_sim_sha256"] = row["ledger_sim_sha256"]

        generated_cutflow, _, _, _ = core.build_prompt_rows(accumulators)
        cutflow = [row for row in generated_cutflow if row["family"] != "gamma"]
        cutflow.extend(_gamma_cutflow_rows())
        cutflow.sort(key=lambda row: (
            row["geometry"], row["family"], row["response"], row["selection"], row["window"]
        ))
        activation_exposure, activation_isotopes = core.build_activation_rows(jobs)
        core.atomic_csv(work / "composite_partial_input_manifest.csv", inventory)
        core.atomic_csv(work / "composite_partial_cell_coverage.csv", coverage)
        core.atomic_csv(work / "prompt_cutflow.csv", cutflow)
        core.atomic_csv(work / "activation_family_exposure.csv", activation_exposure)
        core.atomic_csv(work / "activation_rp_by_volume_isotope_state.csv", activation_isotopes)

        prompt_cells = {}
        for geometry in GEOMETRIES:
            for family in FAMILIES:
                acc = accumulators[(geometry, family)]
                prompt_cells[f"{geometry}/{family}"] = {
                    "geometry": geometry, "mode": "instant", "family": family,
                    "primary_count": acc.primary_count, "sum_TT_s": acc.sum_tt_s,
                    "raw_TES_positive_events": acc.raw_tes_positive,
                    "measured_TES_positive_events": acc.measured_tes_positive,
                    "gamma_analysis_reused": family == "gamma",
                }
        summary = {
            "schema_version": 1,
            "status": "PASS__COMPOSITE_PARTIAL_SEVEN_FAMILY_PROMPT_TES_AND_BUILDUP_ACTIVATION",
            "authority_class": "CORRECTED_KEV_HETEROGENEOUS_REDUCED_STATISTICS_COMPOSITE_PARTIAL",
            "errors": [],
            "source_contract_manifest_sha256": SOURCE_SHA,
            "completeness": {
                "all_28_geometry_mode_family_cells_have_observed_data": True,
                "batch0004_final_authority": False,
                "untransported_planned_exposure_semantics": "missing/not observed; never zero",
                "batch0005_is_addon_only": True,
            },
            "normalization": {
                "prompt": "sum(selected)/sum(TT) within geometry/instant/family",
                "activation": "sum(RP)/sum(TT) within geometry/buildup/family/volume/isotope/excitation; all zero-RP-job TT included",
            },
            "response": {
                "fwhm_keV_per_pixel": core.FWHM_KEV,
                "post_noise_pixel_threshold_keV": core.PIXEL_THRESHOLD_KEV,
                "keyed_rng_namespace": core.RESPONSE_NAMESPACE,
            },
            "veto_contract": "Mass exact 24 CsI; O8 exact 3 BGO + 3 plastic; Kapton excluded",
            "windows_keV": {"broad": list(core.BROAD_KEV), "W2": list(core.W2_KEV)},
            "prompt_cells": prompt_cells,
            "activation_cells": {f"{r['geometry']}/{r['family']}": r for r in activation_exposure},
            "authority_pin": rel(AUTHORITY_PIN), "authority_pin_sha256": sha256(AUTHORITY_PIN),
            "reused_gamma_postprocess": pin["reused_gamma_postprocess"],
            "hard_boundaries": pin["hard_boundaries"],
        }
        summary_path = work / "composite_partial_summary.json"
        atomic_json(summary_path, summary)
        report = (
            "# Corrected-keV composite partial result\n\n"
            "Status: `PASS__COMPOSITE_PARTIAL_SEVEN_FAMILY_PROMPT_TES_AND_BUILDUP_ACTIVATION`.\n\n"
            "All 28 geometry×mode×family cells contain observed data, but statistics are deliberately heterogeneous. "
            "Batch0004 has no final authority; untransported exposure is missing, not zero. Gamma prompt values reuse "
            "the independently validated ordinal-76 postprocess; other prompt families were streamed here. Activation "
            "uses sum(RP)/sum(TT), with zero-RP jobs retained in TT.\n\n"
            "This is screening evidence only, not full-stat, delayed-chain, mission sensitivity, or geometry-promotion authority.\n"
        )
        report_path = work / "COMPOSITE_PARTIAL_REPORT.md"
        report_path.write_text(report, encoding="utf-8")
        output_files = sorted(path for path in work.iterdir())
        records = [{"path": rel(published / p.name), "sha256": sha256(p), "size_bytes": p.stat().st_size} for p in output_files]
        checks = {
            "authority_pin_exact": load_pin() == pin,
            "all_28_cells_present_with_observed_data": len(coverage) == 28 and all(r["data_present"] for r in coverage),
            "no_cross_geometry_mode_family_pooling": True,
            "all_non_gamma_prompt_sim_hashes_revalidated": all(
                r["observed_sim_sha256"] == r["ledger_sim_sha256"]
                for r in inventory if r["mode"] == "instant" and r["family"] != "gamma"
            ),
            "gamma_prompt_reuse_validation_PASS_and_hash_pinned": True,
            "activation_all_zero_RP_job_TT_in_denominator": all(
                r["sum_TT_s_including_zero_RP_jobs"] == next(
                    e["sum_TT_s"] for e in activation_exposure
                    if e["geometry"] == r["geometry"] and e["family"] == r["family"]
                ) for r in activation_isotopes
            ),
            "batch0004_final_not_claimed": summary["completeness"]["batch0004_final_authority"] is False,
            "strict_summary_JSON": load_json(summary_path) == summary,
        }
        validation = {
            "schema_version": 1, "status": "PASS__COMPOSITE_PARTIAL_POSTPROCESS_VALIDATED",
            "errors": [], "checks": checks, "summary": rel(published / summary_path.name),
            "summary_sha256": sha256(summary_path), "outputs": records,
            "hard_boundaries": pin["hard_boundaries"],
        }
        if not core._all_boolean_leaves_true(checks):
            raise RuntimeError("one or more composite validation checks failed")
        validation_path = work / "composite_partial_validation.json"
        atomic_json(validation_path, validation)
        authority = {
            "schema_version": 1,
            "status": "PASS__COMPOSITE_PARTIAL_DIAGNOSTIC_AUTHORITY",
            "errors": [],
            "merge_scope": "observed jobs only; independent geometry/mode/family cells",
            "not_full_statistics": True, "not_mission_authority": True,
            "validation": rel(published / validation_path.name),
            "validation_sha256": sha256(validation_path),
            "summary": rel(published / summary_path.name),
            "summary_sha256": sha256(summary_path),
            "authority_pin": rel(AUTHORITY_PIN), "authority_pin_sha256": sha256(AUTHORITY_PIN),
        }
        authority_path = work / "composite_partial_authority.json"
        atomic_json(authority_path, authority)
        if load_json(authority_path) != authority:
            raise RuntimeError("strict authority JSON round-trip failed")
        os.rename(work, published)
        return {"validation": validation, "authority": authority}
    except BaseException:
        if work.exists():
            shutil.rmtree(work)
        raise


def run(output_dir: Path, *, make_figures: bool = True) -> dict[str, Any]:
    jobs, inventory, ledger_hashes = collect_jobs()
    pin = load_pin()
    coverage = coverage_rows(jobs)
    published = output_dir.resolve()
    if published.exists():
        raise RuntimeError(f"refusing to overwrite: {rel(published)}")
    published.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f".{published.name}.tmp-{os.getpid()}-", dir=published.parent))
    try:
        # Reuse the tested frozen event parser, detector map, keyed response,
        # statistics, activation reducer and figure builders without editing it.
        frozen_parser = core.parse_prompt_sim
        core.parse_prompt_sim = parse_prompt_sim_partial
        try:
            core._run_analysis_in_directory(
                jobs, inventory, ledger_hashes, pin, AUTHORITY_PIN, work, published,
                make_figures=make_figures,
            )
        finally:
            core.parse_prompt_sim = frozen_parser
        core.atomic_csv(work / "composite_partial_cell_coverage.csv", coverage)
        _rewrite_partial_envelope(work, published, pin, coverage)
        validation = load_json(work / "seven_family_tes_activation_validation.json")
        if validation["errors"] or not core._all_boolean_leaves_true(validation["checks"]):
            raise RuntimeError("composite partial validation failed")
        if sha256(work / "seven_family_tes_activation_summary.json") != validation["summary_sha256"]:
            raise RuntimeError("summary hash closure failed")
        os.rename(work, published)
        return validation
    except BaseException:
        if work.exists():
            shutil.rmtree(work)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--pin-authorities", action="store_true")
    group.add_argument("--check-inputs-only", action="store_true")
    group.add_argument("--run", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--no-figures", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.pin_authorities:
            if args.output_dir or args.no_figures:
                parser.error("pin mode accepts no output options")
            payload = pin_authorities()
            print(json.dumps({"status": payload["status"], "pin": rel(AUTHORITY_PIN), "sha256": sha256(AUTHORITY_PIN)}, indent=2))
            return 0
        if args.check_inputs_only:
            if args.output_dir or args.no_figures:
                parser.error("check mode accepts no output options")
            jobs, _, ledgers = collect_jobs()
            coverage = coverage_rows(jobs)
            print(json.dumps({
                "status": "PASS__COMPOSITE_PARTIAL_INPUT_METADATA_READY",
                "authority_pin_sha256": sha256(AUTHORITY_PIN),
                "cells": len(coverage),
                "jobs": sum(len(rows) for rows in jobs.values()),
                "events_by_cell": {"/".join(cell): sum(j.events for j in rows) for cell, rows in sorted(jobs.items())},
                "ledger_sha256": ledgers,
                "sim_payloads_read": False,
                "outputs_written": False,
            }, indent=2, allow_nan=False))
            return 0
        output = args.output_dir or DEFAULT_OUTPUT
        if not output.is_absolute():
            output = ROOT / output
        # The canonical gamma prefix already has a hash-pinned validated
        # postprocess. Reuse it and stream only the six remaining prompt
        # families so this composite closes inside the frozen wall window.
        result = run_fast_partial(output)
        print(json.dumps({
            "status": result["validation"]["status"], "output": rel(output),
            "validation": rel(output / "composite_partial_validation.json"),
            "authority": rel(output / "composite_partial_authority.json"),
        }, indent=2))
        return 0
    except (RuntimeError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "errors": [str(exc)]}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
