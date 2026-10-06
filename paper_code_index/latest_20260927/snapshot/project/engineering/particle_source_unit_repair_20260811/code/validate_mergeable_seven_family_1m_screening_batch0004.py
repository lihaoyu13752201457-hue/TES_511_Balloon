#!/usr/bin/env python3
"""Fail-closed shard, checkpoint, and final validator for batch0004."""

from __future__ import annotations

import argparse
import gzip
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


THIS_FILE = Path(__file__).resolve()
CODE_DIR = THIS_FILE.parent
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

import run_mergeable_seven_family_1m_screening_batch0004 as batch  # noqa: E402
import run_mergeable_two_geometry_smoke as smoke  # noqa: E402
import validate_mergeable_two_geometry_smoke as common  # noqa: E402


GENERATED_RE = re.compile(r"Total number of generated particles:\s+(\d+)")
OBSERVATION_RE = re.compile(r"Observation time:\s+([-+0-9.eE]+) sec")
RETURN_RE = re.compile(r"^returncode=(-?\d+)\s*$", re.MULTILINE)
PEAK_RSS_RE = re.compile(r"^peak_process_group_rss_bytes=(\d+)\s*$", re.MULTILINE)
OUTPUT_CAP_RE = re.compile(r"^attempt_output_cap_bytes=(\d+)\s*$", re.MULTILINE)
INPUT_PRE_RE = re.compile(r"^frozen_input_bundle_sha256_pre=([0-9a-f]{64})\s*$", re.MULTILINE)
INPUT_POST_RE = re.compile(r"^frozen_input_bundle_sha256_post=([0-9a-f]{64}|FAIL)\s*$", re.MULTILINE)


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _campaign_contract(
    contract: dict[str, Any], geometry: str, stage_key: str
) -> dict[str, Any]:
    rows = [
        row for row in contract.get("campaigns", [])
        if row.get("geometry") == geometry and row.get("stage") == stage_key
    ]
    if len(rows) != 1:
        raise ValueError(f"global contract campaign ambiguity: {geometry}/{stage_key}")
    return rows[0]


def _spectrum_hashes(source_contract: dict[str, Any]) -> dict[str, str]:
    return {
        str(row["corrected_spectrum"]): str(row["corrected_sha256"])
        for row in source_contract.get("spectra", {}).get("files", [])
    }


def _expected_job_name(ordinal: int) -> str:
    spec = batch.shard_spec(ordinal)
    return (
        f"Background_{spec['family']}_fullsphere20_batch0004_{spec['mode']}_"
        f"shard{int(spec['stage_ordinal']):04d}"
    )


def _expected_attempt_paths(geometry: str, ordinal: int, attempt: int) -> dict[str, Path]:
    outdir = batch.attempt_dir(geometry, ordinal, attempt)
    name = _expected_job_name(ordinal)
    return {
        "attempt_dir": outdir,
        "attempt_contract": outdir / "attempt_contract.json",
        "attempt_validation": outdir / "attempt_validation.json",
        "job_source": outdir / f"{name}.source",
        "sim": outdir / f"{name}.inc1.id1.sim.gz",
        "isotope_dat": outdir / f"{name}.dat.inc1.dat",
        "log": outdir / f"{name}.log",
    }


def _artifact_snapshot(paths: dict[str, Path]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Hash all signed attempt artifacts and detect changes during hashing."""
    records: dict[str, dict[str, Any]] = {}
    problems: list[str] = []
    for key in ("attempt_contract", "job_source", "sim", "isotope_dat", "log"):
        path = paths[key]
        try:
            before = path.stat()
            digest = smoke.sha256(path)
            after = path.stat()
        except OSError as exc:
            problems.append(f"{key}: snapshot failed: {exc}")
            continue
        before_identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        if before_identity != after_identity:
            problems.append(f"{key}: artifact changed while hashing")
        records[key] = {
            "path": smoke.rel(path),
            "sha256": digest,
            "bytes": after.st_size,
        }
    return records, problems


def _validate_attempt_contract_exact(
    contract: dict[str, Any],
    attempt_contract: dict[str, Any],
    geometry: str,
    ordinal: int,
    attempt: int,
    gate: common.Gate,
) -> None:
    expected = batch._attempt_contract_payload(
        contract,
        geometry,
        ordinal,
        attempt,
        batch._job(geometry, ordinal, attempt, contract["transport"]["cosima"]),
        attempt_contract.get("frozen_input_bundle_sha256_pre"),
    )
    gate.require(attempt_contract == expected,
                 f"{geometry}/shard{ordinal:04d}: attempt contract payload mismatch", "binding")


def _scan_sim_exact(
    path: Path,
    expected_events: int,
    expected_seed: int,
    expected_geometry: Path,
    support_by_bin: dict[int, tuple[float, float]],
    family: str,
) -> dict[str, Any]:
    """Read through gzip EOF and verify exact SE/ID/IA INIT contracts."""
    problems: list[str] = []
    ids: list[int] = []
    se_records = 0
    init_records = 0
    init_by_id: dict[int, int] = {}
    current_id: int | None = None
    header_geometry: str | None = None
    header_seed: int | None = None
    energy_min: float | None = None
    energy_max: float | None = None
    bad_energy = 0
    bad_particle = 0
    bad_direction = 0

    def problem(message: str) -> None:
        if len(problems) < 30:
            problems.append(message)

    try:
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                line = raw.strip()
                if header_geometry is None and (match := common.GEOMETRY_RE.match(line)):
                    header_geometry = match.group(1)
                if header_seed is None and line.startswith("Seed "):
                    try:
                        header_seed = int(line.split()[1])
                    except (IndexError, ValueError):
                        problem(f"malformed SIM Seed header: {line}")
                if line == "SE":
                    se_records += 1
                    current_id = None
                    continue
                if match := common.ID_RE.match(line):
                    current_id = int(match.group(1))
                    ids.append(current_id)
                    init_by_id.setdefault(current_id, 0)
                    continue
                if not line.startswith("IA INIT"):
                    continue
                if current_id is None:
                    problem("IA INIT outside an SE/ID event")
                    continue
                init_by_id[current_id] = init_by_id.get(current_id, 0) + 1
                init_records += 1
                try:
                    init = common.parse_init(line)
                except Exception as exc:
                    problem(f"ID {current_id}: {exc}")
                    continue
                if int(init["particle_type"]) != common.PARTICLE_TYPES[family]:
                    bad_particle += 1
                direction = (float(init["dir_x"]), float(init["dir_y"]), float(init["dir_z"]))
                norm = math.sqrt(math.fsum(value * value for value in direction))
                if not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=5.0e-4):
                    bad_direction += 1
                energy = float(init["energy_keV"])
                energy_min = energy if energy_min is None else min(energy_min, energy)
                energy_max = energy if energy_max is None else max(energy_max, energy)
                angular_bin = common.angular_bin_from_init_dir_z(direction[2])
                low, high = support_by_bin[angular_bin]
                tolerance = max(0.002, 1.0e-10 * max(abs(low), abs(high)))
                if not low - tolerance <= energy <= high + tolerance:
                    neighbors = [
                        support_by_bin[index]
                        for index in (angular_bin - 1, angular_bin + 1)
                        if index in support_by_bin
                    ]
                    if not any(lo - tolerance <= energy <= hi + tolerance for lo, hi in neighbors):
                        bad_energy += 1
    except (OSError, EOFError, gzip.BadGzipFile) as exc:
        problem(f"gzip integrity/EOF failure: {exc}")

    if header_geometry is None:
        problem("missing SIM Geometry header")
    elif common.resolve_repo_path(header_geometry) != expected_geometry.resolve():
        problem(f"wrong SIM Geometry header: {header_geometry}")
    if header_seed != expected_seed:
        problem(f"SIM Seed={header_seed}, expected {expected_seed}")
    if se_records != expected_events:
        problem(f"SE records={se_records}, expected {expected_events}")
    if ids != list(range(1, expected_events + 1)):
        problem(f"SIM IDs are not exactly 1..{expected_events} (observed {len(ids)})")
    bad_init_events = [event_id for event_id, count in init_by_id.items() if count != 1]
    if bad_init_events:
        problem(f"events with IA INIT count != 1: {len(bad_init_events)}")
    if init_records != expected_events:
        problem(f"IA INIT records={init_records}, expected {expected_events}")
    if bad_particle:
        problem(f"wrong IA INIT particle type records={bad_particle}")
    if bad_direction:
        problem(f"non-unit IA INIT direction records={bad_direction}")
    if bad_energy:
        problem(f"IA INIT energy outside corrected per-bin support records={bad_energy}")
    return {
        "events": len(ids),
        "se_records": se_records,
        "id_records": len(ids),
        "ia_init_records": init_records,
        "energy_min_keV": energy_min,
        "energy_max_keV": energy_max,
        "bad_energy_records": bad_energy,
        "bad_particle_records": bad_particle,
        "bad_direction_records": bad_direction,
        "geometry_header": header_geometry,
        "seed_header": header_seed,
        "gzip_eof_read": not any(item.startswith("gzip integrity/EOF") for item in problems),
        "problems": problems,
    }


def _validate_toolchain_contract_exact(
    contract: dict[str, Any], gate: common.Gate
) -> None:
    gate.require(
        contract.get("toolchain") == batch.toolchain_payload(),
        "exact toolchain key/path/hash payload mismatch",
        "toolchain",
    )


def _light_contract_gate(contract: dict[str, Any], gate: common.Gate) -> dict[str, Any] | None:
    gate.require(contract.get("batch_id") == batch.BATCH_ID, "global batch ID mismatch", "contract")
    gate.require(
        contract.get("campaign_version") == batch.CAMPAIGN_VERSION,
        "campaign version mismatch",
        "contract",
    )
    gate.require(
        contract.get("source_contract_manifest_sha256") == batch.SOURCE_CONTRACT_SHA256,
        "source contract binding mismatch",
        "contract",
    )
    gate.require(
        smoke.sha256(batch.SOURCE_CONTRACT) == batch.SOURCE_CONTRACT_SHA256,
        "source contract hash mismatch",
        "contract",
    )
    expected_scope = {
        "included_families": list(batch.FAMILIES),
        "excluded_families": ["p"],
        "modes": list(batch.MODES),
        "gamma_modes": ["buildup"],
        "angular_bins_per_family": 20,
        "mono_511_added": False,
        "store_simulation_info": "all",
        "policy": "gamma buildup plus six non-proton families in instant and buildup",
    }
    gate.require(contract.get("source_scope") == expected_scope, "source scope mismatch", "contract")
    _validate_toolchain_contract_exact(contract, gate)
    stats = contract.get("statistics", {})
    gate.require(
        stats.get("new_events_total") == batch.TOTAL_NEW_EVENTS,
        "new event total mismatch",
        "statistics",
    )
    gate.require(
        stats.get("paired_shards_total") == batch.FINAL_SHARD_COUNT,
        "paired shard total mismatch",
        "statistics",
    )
    gate.require(
        stats.get("transport_jobs_total") == batch.FINAL_JOB_COUNT,
        "transport job total mismatch",
        "statistics",
    )
    gate.require(
        stats.get("stages") == batch.STAGE_SPECS,
        "stage schedule mismatch",
        "statistics",
    )
    gate.require(
        stats.get("paired_shards") == batch.planned_shards(),
        "paired shard schedule mismatch",
        "statistics",
    )
    pairing = contract.get("pairing", {})
    gate.require(pairing.get("policy") == batch.PAIRING_RULE,
                 "operational pairing rule mismatch", "statistics")
    gate.require(pairing.get("statistical_semantics") == batch.PAIRING_STATISTICAL_SEMANTICS,
                 "pairing statistical semantics mismatch", "statistics")
    for path, expected_hash, expected_id, expected_status in (
        (batch.BATCH0000_LEDGER, batch.BATCH0000_SHA256, batch.BATCH0000_ID, batch.BATCH0000_STATUS),
        (batch.BATCH0001_LEDGER, batch.BATCH0001_SHA256, batch.BATCH0001_ID, batch.BATCH0001_STATUS),
        (batch.BATCH0002_LEDGER, batch.BATCH0002_SHA256, batch.BATCH0002_ID, batch.BATCH0002_STATUS),
    ):
        gate.require(path.is_file() and smoke.sha256(path) == expected_hash,
                     f"prior ledger hash mismatch: {expected_id}", "lineage")
        if path.is_file():
            prior = _json(path)
            gate.require(prior.get("batch_id") == expected_id and prior.get("status") == expected_status,
                         f"prior ledger identity/status mismatch: {expected_id}", "lineage")
    gate.require(
        batch.BATCH0002_CONTRACT.is_file()
        and smoke.sha256(batch.BATCH0002_CONTRACT) == batch.BATCH0002_CONTRACT_SHA256,
        "batch0002 credited global contract hash mismatch",
        "lineage",
    )
    dependency = contract.get("batch0003_predecessor_authority", {})
    for path_key, hash_key in (("contract", "contract_sha256"), ("report", "report_sha256"),
                               ("ledger", "ledger_sha256")):
        try:
            path = batch.ROOT / dependency[path_key]
            expected = dependency[hash_key]
        except KeyError:
            gate.problem(f"batch0003 dependency lacks {path_key}/{hash_key}", "lineage")
            continue
        gate.require(path.is_file() and smoke.sha256(path) == expected,
                     f"batch0003 dependency hash mismatch: {path_key}", "lineage")
    profile = dependency.get("profile")
    gate.require(
        dependency.get("selection_policy")
        == "prefer canonical prefix ordinal76; otherwise canonical stage5"
        and dependency.get("required_status")
        == [batch.PREFIX_LEDGER_STATUS, batch.BATCH0003_STATUS],
        "batch0003 predecessor selection contract mismatch",
        "lineage",
    )
    gate.require(
        dependency.get("batch_id") == batch.BATCH0003_ID
        and dependency.get("contract") == smoke.rel(batch.BATCH0003_CONTRACT)
        and batch.BATCH0003_CONTRACT.is_file()
        and dependency.get("contract_sha256") == smoke.sha256(batch.BATCH0003_CONTRACT)
        and dependency.get("state") == smoke.rel(batch.BATCH0003_STATE)
        and dependency.get("candidate_prefix_report") == smoke.rel(batch.PREFIX_REPORT)
        and dependency.get("candidate_prefix_ledger") == smoke.rel(batch.PREFIX_LEDGER)
        and dependency.get("candidate_stage5_report") == smoke.rel(batch.BATCH0003_REPORT)
        and dependency.get("candidate_stage5_ledger") == smoke.rel(batch.BATCH0003_LEDGER)
        and dependency.get("prefix_validator") == smoke.rel(batch.PREFIX_VALIDATOR)
        and dependency.get("prefix_validator_sha256") == batch.PREFIX_VALIDATOR_SHA256,
        "batch0003 predecessor fixed path/hash contract mismatch",
        "lineage",
    )
    parent_contract = _json(batch.BATCH0003_CONTRACT) if batch.BATCH0003_CONTRACT.is_file() else {}
    parent_planned_seeds = [
        int(row["seed"])
        for row in parent_contract.get("statistics", {}).get("paired_shards", [])
    ]
    gate.require(
        dependency.get("seed_exclusion") == {
            "scope": "all batch0003 planned seeds, including ordinals beyond selected authority",
            "planned_seed_count": len(parent_planned_seeds),
            "planned_seed_list_sha256": batch._json_sha256(parent_planned_seeds),
        }
        and dependency.get("prior_credit_rule")
        == (
            "batch0003 instant-gamma exposure is not deducted from batch0004 gamma-buildup "
            "or any non-gamma family+mode target"
        ),
        "batch0003 predecessor seed/prior-credit boundary mismatch",
        "lineage",
    )
    if profile == "prefix_ordinal76":
        gate.require(
            dependency.get("gate") == "PASS__BATCH0003_PREFIX76_AUTHORITY_PRESENT"
            and dependency.get("selected_status") == batch.PREFIX_LEDGER_STATUS
            and dependency.get("report") == smoke.rel(batch.PREFIX_REPORT)
            and dependency.get("ledger") == smoke.rel(batch.PREFIX_LEDGER)
            and dependency.get("prefix_validator") == smoke.rel(batch.PREFIX_VALIDATOR)
            and dependency.get("prefix_validator_sha256") == batch.PREFIX_VALIDATOR_SHA256
            and dependency.get("gamma_exposure") == {
                "mode": "instant",
                "prefix_start_ordinal": 1,
                "prefix_end_ordinal": batch.PREFIX_CHECKPOINT_ORDINAL,
                "prior_events_per_geometry": batch.PREFIX_PRIOR_EVENTS_PER_GEOMETRY,
                "new_events_per_geometry": batch.PREFIX_NEW_EVENTS_PER_GEOMETRY,
                "cumulative_events_per_geometry": batch.PREFIX_CUMULATIVE_EVENTS_PER_GEOMETRY,
                "credited_to_batch0004_buildup": False,
            },
            "batch0003 prefix76 predecessor is not exact frozen PASS",
            "lineage",
        )
    elif profile == "stage5":
        gate.require(
            dependency.get("gate") == "PASS__BATCH0003_STAGE5_AUTHORITY_PRESENT"
            and dependency.get("selected_status") == batch.BATCH0003_STATUS
            and dependency.get("report") == smoke.rel(batch.BATCH0003_REPORT)
            and dependency.get("ledger") == smoke.rel(batch.BATCH0003_LEDGER)
            and dependency.get("gamma_exposure") == {
                "mode": "instant",
                "stage": "5m",
                "prior_events_per_geometry": batch.PREFIX_PRIOR_EVENTS_PER_GEOMETRY,
                "new_events_per_geometry": 4_899_000,
                "cumulative_events_per_geometry": 5_000_000,
                "credited_to_batch0004_buildup": False,
            },
            "batch0003 stage5 predecessor is not exact frozen PASS",
            "lineage",
        )
    else:
        gate.problem("batch0003 predecessor profile is not an accepted PASS profile", "lineage")
    source_contract = _json(batch.SOURCE_CONTRACT) if batch.SOURCE_CONTRACT.is_file() else None
    if source_contract is not None:
        gate.require(
            source_contract.get("source_model", {}).get("profile") == "unit_only_total_gamma",
            "source profile mismatch",
            "contract",
        )
        gate.require(
            source_contract.get("policies", {}).get("additive_mono_511_allowed") is False,
            "mono-511 policy mismatch",
            "contract",
        )
    return source_contract


def validate_attempt(
    contract: dict[str, Any],
    geometry: str,
    ordinal: int,
    attempt: int,
) -> tuple[dict[str, Any], list[str]]:
    gate = common.Gate()
    source_contract = _light_contract_gate(contract, gate)
    try:
        spec = batch.shard_spec(ordinal)
    except ValueError as exc:
        gate.problem(str(exc), "identity")
        spec = {"key": "invalid", "family": "gamma", "mode": "buildup", "stage_ordinal": -1}
    family = str(spec["family"])
    mode = str(spec["mode"])
    label = (
        f"{geometry}/{spec['key']}/global{ordinal:04d}/"
        f"stage{int(spec['stage_ordinal']):04d}/attempt{attempt:02d}"
    )
    gate.require(geometry in batch.GEOMETRIES, f"{label}: unknown geometry", "identity")
    try:
        expected_events = batch.shard_events(ordinal)
        expected_seed = batch.shard_seed(ordinal)
    except ValueError as exc:
        gate.problem(f"{label}: {exc}", "identity")
        expected_events = -1
        expected_seed = -1
    gate.require(1 <= attempt <= batch.MAX_ATTEMPTS, f"{label}: attempt out of range", "identity")
    paths = _expected_attempt_paths(geometry, ordinal, attempt)
    for key in ("attempt_contract", "job_source", "sim", "isotope_dat", "log"):
        path = paths[key]
        gate.require(path.is_file() and path.stat().st_size > 0,
                     f"{label}: missing/empty {key}: {smoke.rel(path)}", "outputs")
        gate.require(common.is_within(path, paths["attempt_dir"]),
                     f"{label}: {key} escapes attempt dir", "outputs")
    if not all(paths[key].is_file() for key in ("attempt_contract", "job_source", "sim", "isotope_dat", "log")):
        return ({
            "schema_version": 1,
            "status": "FAIL",
            "geometry": geometry,
            "ordinal": ordinal,
            "attempt": attempt,
            "events": expected_events,
            "seed": expected_seed,
            "errors": gate.errors,
            "checks": dict(gate.checks),
        }, gate.errors)

    artifacts_pre, snapshot_problems = _artifact_snapshot(paths)
    for problem in snapshot_problems:
        gate.problem(f"{label}: pre-scan {problem}", "artifact_stability")

    attempt_contract = _json(paths["attempt_contract"])
    _validate_attempt_contract_exact(contract, attempt_contract, geometry, ordinal, attempt, gate)
    expected_identity = {
        "global_contract_sha256": smoke.sha256(batch.GLOBAL_CONTRACT),
        "geometry": geometry,
        "stage": spec["key"],
        "mode": mode,
        "family": family,
        "global_ordinal": ordinal,
        "stage_ordinal": spec["stage_ordinal"],
        "attempt": attempt,
        "events": expected_events,
        "seed": expected_seed,
        "job_name": _expected_job_name(ordinal),
    }
    for key, expected in expected_identity.items():
        gate.require(attempt_contract.get(key) == expected,
                     f"{label}: attempt contract {key} mismatch", "binding")
    expected_output_cap = batch._attempt_output_cap_bytes(contract, geometry, ordinal)
    gate.require(
        attempt_contract.get("attempt_output_cap_bytes") == expected_output_cap,
        f"{label}: attempt output cap mismatch",
        "resource_gate",
    )
    campaign = _campaign_contract(contract, geometry, str(spec["key"]))
    base_source = batch.source_card_path(geometry, family)
    flux = common.source_flux(base_source)
    gate.require(math.isfinite(flux) and flux > 0,
                 f"{label}: invalid source flux", "normalization")
    tt_expected = (
        expected_events / (flux * math.pi * batch.FARFIELD_RADIUS_CM**2)
        if math.isfinite(flux) and flux > 0 else None
    )
    gate.require(tt_expected is not None and math.isfinite(tt_expected) and tt_expected > 0,
                 f"{label}: invalid expected TT from events/flux/area", "normalization")
    gate.require(
        smoke.sha256(base_source) == campaign.get("source_card_sha256"),
        f"{label}: corrected source card hash changed",
        "binding",
    )
    gate.require(
        attempt_contract.get("source_card_sha256") == campaign.get("source_card_sha256"),
        f"{label}: attempt source binding mismatch",
        "binding",
    )
    gate.require(
        attempt_contract.get("job_source") == smoke.rel(paths["job_source"])
        and attempt_contract.get("job_source_sha256") == smoke.sha256(paths["job_source"]),
        f"{label}: job-source binding mismatch",
        "binding",
    )
    for key, authority_key in (("sim", "sim"), ("isotope_dat", "isotope_dat"), ("log", "log")):
        gate.require(
            attempt_contract.get(authority_key) == smoke.rel(paths[key]),
            f"{label}: attempt {key} path mismatch",
            "binding",
        )

    spectrum_hashes = _spectrum_hashes(source_contract or {})
    gate.require(len(spectrum_hashes) == 160, f"{label}: corrected spectrum inventory mismatch", "source_refs")
    supports, corrected_refs, legacy_refs = common.validate_source_card(
        gate,
        base_source,
        paths["job_source"],
        family,
        mode,
        _expected_job_name(ordinal),
        expected_events,
        expected_seed,
        paths["attempt_dir"],
        spectrum_hashes,
    )
    gate.require(corrected_refs == 20 and legacy_refs == 0,
                 f"{label}: corrected/legacy reference mismatch", "source_refs")
    migration = _json(batch.source_manifest_path(geometry))
    expected_geometry = common.resolve_repo_path(migration["geometry_setup"])
    gate.require(
        common.source_geometry(paths["job_source"]) == migration["geometry_setup"],
        f"{label}: patched source geometry mismatch",
        "geometry",
    )

    log_text = paths["log"].read_text(encoding="utf-8", errors="replace")
    generated_matches = GENERATED_RE.findall(log_text)
    observation_matches = OBSERVATION_RE.findall(log_text)
    return_matches = RETURN_RE.findall(log_text)
    peak_matches = PEAK_RSS_RE.findall(log_text)
    output_cap_matches = OUTPUT_CAP_RE.findall(log_text)
    input_pre_matches = INPUT_PRE_RE.findall(log_text)
    input_post_matches = INPUT_POST_RE.findall(log_text)
    generated = int(generated_matches[0]) if len(generated_matches) == 1 else None
    observation = float(observation_matches[0]) if len(observation_matches) == 1 else None
    returncode = int(return_matches[0]) if len(return_matches) == 1 else None
    peak_rss = int(peak_matches[0]) if len(peak_matches) == 1 else None
    command = attempt_contract.get("cosima_command", [])
    expected_command = [
        contract["transport"]["cosima"],
        "-s",
        str(expected_seed),
        str(paths["job_source"]),
    ]
    gate.require(command == expected_command, f"{label}: frozen Cosima command mismatch", "transport")
    gate.require(log_text.count(f"cosima_command={' '.join(expected_command)}") == 1,
                 f"{label}: logged Cosima command mismatch", "transport")
    gate.require("MEGAlib version" in log_text, f"{label}: MEGAlib banner missing", "transport")
    gate.require("***  Error" not in log_text and "Segmentation fault" not in log_text,
                 f"{label}: error marker in log", "log")
    gate.require(len(return_matches) == 1 and returncode == 0,
                 f"{label}: nonzero/missing/duplicate return code", "log")
    gate.require(len(generated_matches) == 1 and generated == expected_events,
                 f"{label}: generated count mismatch", "log")
    gate.require(len(peak_matches) == 1 and peak_rss is not None and peak_rss >= 0,
                 f"{label}: missing/invalid peak RSS record", "resource_gate")
    gate.require(len(output_cap_matches) == 1 and int(output_cap_matches[0]) == expected_output_cap,
                 f"{label}: logged output cap mismatch", "resource_gate")
    frozen_pre = attempt_contract.get("frozen_input_bundle_sha256_pre")
    gate.require(
        len(input_pre_matches) == 1
        and len(input_post_matches) == 1
        and input_pre_matches[0] == frozen_pre
        and input_post_matches[0] == frozen_pre,
        f"{label}: frozen input bundle pre/post mismatch",
        "input_integrity",
    )
    gate.require(
        len(observation_matches) == 1
        and observation is not None
        and math.isfinite(observation)
        and observation > 0,
        f"{label}: invalid/duplicate log TT",
        "normalization",
    )

    isotope = common.parse_isotope_dat(paths["isotope_dat"])
    for problem in isotope["problems"]:
        gate.problem(f"{label}: isotope DAT {problem}", "isotope_dat")
    dat_tt = isotope["TT_s"]
    gate.require(dat_tt is not None and math.isfinite(dat_tt) and dat_tt > 0,
                 f"{label}: invalid DAT TT", "isotope_dat")
    if dat_tt is not None and observation is not None:
        gate.require(
            math.isclose(dat_tt, observation, rel_tol=2e-3, abs_tol=2e-6),
            f"{label}: DAT/log TT mismatch",
            "isotope_dat",
        )
    if set(supports) == set(range(20)):
        scan = _scan_sim_exact(
            paths["sim"],
            expected_events,
            expected_seed,
            expected_geometry,
            supports,
            family,
        )
    else:
        scan = {
            "events": 0,
            "se_records": 0,
            "id_records": 0,
            "ia_init_records": 0,
            "energy_min_keV": None,
            "energy_max_keV": None,
            "bad_energy_records": 0,
            "bad_particle_records": 0,
            "bad_direction_records": 0,
            "geometry_header": None,
            "seed_header": None,
            "gzip_eof_read": False,
            "problems": ["cannot scan SIM against incomplete corrected spectrum support"],
        }
    for problem in scan["problems"]:
        gate.problem(f"{label}: {problem}", "sim")

    artifacts, snapshot_problems = _artifact_snapshot(paths)
    for problem in snapshot_problems:
        gate.problem(f"{label}: post-scan {problem}", "artifact_stability")
    gate.require(artifacts == artifacts_pre,
                 f"{label}: attempt artifacts changed during validation", "artifact_stability")
    written_bytes = math.fsum(artifacts.get(key, {}).get("bytes", 0)
                              for key in ("sim", "isotope_dat", "log"))
    gate.require(written_bytes <= expected_output_cap,
                 f"{label}: finalized output exceeds attempt cap", "resource_gate")
    status = "PASS" if not gate.errors else "FAIL"
    payload = {
        "schema_version": 1,
        "status": status,
        "batch_id": batch.BATCH_ID,
        "campaign_version": batch.CAMPAIGN_VERSION,
        "geometry": geometry,
        "stage": spec["key"],
        "mode": mode,
        "family": family,
        "ordinal": ordinal,
        "stage_ordinal": spec["stage_ordinal"],
        "attempt": attempt,
        "events": expected_events,
        "seed": expected_seed,
        "source_references": {"corrected": corrected_refs, "legacy": legacy_refs},
        "peak_process_group_rss_bytes": peak_rss,
        "attempt_output_cap_bytes": expected_output_cap,
        "frozen_input_bundle_sha256": frozen_pre,
        "TT_s_from_log": observation,
        "TT_s_from_isotope_dat": dat_tt,
        "flux_cm2_s": flux,
        "TT_s_expected_mean_from_events_flux_area": tt_expected,
        "TT_authority": batch.TT_AUTHORITY,
        "isotope_store": isotope,
        "sim_scan": scan,
        "artifacts": artifacts,
        "checks": dict(gate.checks),
        "errors": gate.errors,
    }
    return payload, gate.errors


def _receipt_payload(validation: dict[str, Any], validation_path: Path) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "PASS__GEOMETRY_SHARD_MERGE_ELIGIBLE",
        "batch_id": batch.BATCH_ID,
        "campaign_version": batch.CAMPAIGN_VERSION,
        "geometry": validation["geometry"],
        "stage": validation["stage"],
        "mode": validation["mode"],
        "family": validation["family"],
        "ordinal": validation["ordinal"],
        "stage_ordinal": validation["stage_ordinal"],
        "events": validation["events"],
        "seed": validation["seed"],
        "selected_attempt": validation["attempt"],
        "attempt_validation": smoke.rel(validation_path),
        "attempt_validation_sha256": smoke.sha256(validation_path),
        "TT_s_from_log": validation["TT_s_from_log"],
        "TT_s_from_isotope_dat": validation["TT_s_from_isotope_dat"],
        "flux_cm2_s": validation["flux_cm2_s"],
        "TT_s_expected_mean_from_events_flux_area": validation[
            "TT_s_expected_mean_from_events_flux_area"
        ],
        "TT_authority": validation["TT_authority"],
        "source_references": validation["source_references"],
        "peak_process_group_rss_bytes": validation["peak_process_group_rss_bytes"],
        "attempt_output_cap_bytes": validation["attempt_output_cap_bytes"],
        "frozen_input_bundle_sha256": validation["frozen_input_bundle_sha256"],
        "sim_scan": validation["sim_scan"],
        "artifacts": validation["artifacts"],
    }


def _ledger_job_payload(
    validation: dict[str, Any],
    ordinal: int,
    attempt: int,
    receipt_path: Path,
    pair_path: Path,
) -> dict[str, Any]:
    artifacts = validation.get("artifacts", {})
    spec = batch.shard_spec(ordinal)
    return {
        "job_name": _expected_job_name(ordinal),
        "stage": spec["key"],
        "family": spec["family"],
        "mode": spec["mode"],
        "events": batch.shard_events(ordinal),
        "seed": batch.shard_seed(ordinal),
        "ordinal": ordinal,
        "stage_ordinal": spec["stage_ordinal"],
        "selected_attempt": attempt,
        "flux_cm2_s": validation.get("flux_cm2_s"),
        "TT_s_expected_mean_from_events_flux_area": validation.get(
            "TT_s_expected_mean_from_events_flux_area"
        ),
        "TT_s_from_log": validation.get("TT_s_from_log"),
        "TT_s_from_isotope_dat": validation.get("TT_s_from_isotope_dat"),
        "TT_authority": validation.get("TT_authority"),
        "job_source": artifacts.get("job_source", {}).get("path"),
        "job_source_sha256": artifacts.get("job_source", {}).get("sha256"),
        "sim": artifacts.get("sim", {}).get("path"),
        "sim_sha256": artifacts.get("sim", {}).get("sha256"),
        "isotope_dat": artifacts.get("isotope_dat", {}).get("path"),
        "isotope_dat_sha256": artifacts.get("isotope_dat", {}).get("sha256"),
        "log": artifacts.get("log", {}).get("path"),
        "log_sha256": artifacts.get("log", {}).get("sha256"),
        "isotope_store": validation.get("isotope_store"),
        "ia_init": validation.get("sim_scan"),
        "geometry_receipt": smoke.rel(receipt_path),
        "geometry_receipt_sha256": smoke.sha256(receipt_path),
        "pair_receipt": smoke.rel(pair_path),
        "pair_receipt_sha256": smoke.sha256(pair_path),
    }


def validate_shard(geometry: str, ordinal: int, attempt: int, *, write: bool) -> tuple[dict[str, Any], int]:
    if not batch.GLOBAL_CONTRACT.is_file():
        result = {"status": "FAIL", "errors": ["missing global contract"]}
        return result, 1
    contract = _json(batch.GLOBAL_CONTRACT)
    validation, errors = validate_attempt(contract, geometry, ordinal, attempt)
    paths = _expected_attempt_paths(geometry, ordinal, attempt)
    if write:
        batch.atomic_write_once_json(paths["attempt_validation"], validation)
        if not errors:
            receipt = _receipt_payload(validation, paths["attempt_validation"])
            batch.atomic_write_once_json(batch.geometry_receipt_path(geometry, ordinal), receipt)
    result = {
        "status": validation["status"],
        "geometry": geometry,
        "ordinal": ordinal,
        "attempt": attempt,
        "events": validation["events"],
        "seed": validation["seed"],
        "errors": errors,
        "receipt": smoke.rel(batch.geometry_receipt_path(geometry, ordinal)) if not errors else None,
    }
    return result, 0 if not errors else 1


def _full_contract_gate(contract: dict[str, Any], gate: common.Gate) -> tuple[dict[str, Any], dict[str, str]]:
    source_contract = _light_contract_gate(contract, gate) or {}
    gate.require(batch.EXECUTION_STATE.is_file(), "execution state missing", "execution")
    if batch.EXECUTION_STATE.is_file():
        try:
            batch._validate_execution_state(contract, _json(batch.EXECUTION_STATE))
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError, RuntimeError) as exc:
            gate.problem(f"execution state immutable/deadline validation failed: {exc}", "execution")
    _validate_toolchain_contract_exact(contract, gate)
    for name, record in contract.get("toolchain", {}).items():
        path = common.resolve_repo_path(record.get("path", "__missing__"))
        gate.require(path.is_file() and smoke.sha256(path) == record.get("sha256"),
                     f"toolchain hash mismatch: {name}", "toolchain")
    cosima = smoke.resolve_cosima(contract.get("transport", {}).get("cosima"))
    environment, descriptor = smoke.resolve_transport_environment(cosima)
    current_transport = smoke.build_transport_fingerprint(cosima, environment, descriptor)
    gate.require(batch._transport_core(current_transport) == contract.get("transport_core"),
                 "transport fingerprint changed", "transport")
    current_bundles: dict[str, Any] = {}
    for geometry in batch.GEOMETRIES:
        bundle = smoke.build_geometry_bundle(geometry, environment)
        current_bundles[geometry] = bundle
        gate.require(bundle == contract.get("geometry_bundles", {}).get(geometry),
                     f"global geometry bundle changed: {geometry}", "geometry")
        for stage in batch.STAGE_SPECS:
            campaign = _campaign_contract(contract, geometry, str(stage["key"]))
            gate.require(bundle == campaign.get("geometry_bundle"),
                         f"campaign geometry bundle changed: {geometry}/{stage['key']}", "geometry")
        gate.require(common.source_contract_geometry_files(source_contract, geometry, environment) == bundle["files"],
                     f"source/runtime geometry mismatch: {geometry}", "geometry")
    try:
        equivalence = batch.require_prior_credit_equivalence(
            _json(batch.BATCH0000_LEDGER),
            _json(batch.BATCH0001_LEDGER),
            _json(batch.BATCH0002_LEDGER),
            contract["batch0003_predecessor_authority"],
            current_transport,
            current_bundles,
        )
    except (SystemExit, KeyError, TypeError, ValueError) as exc:
        gate.problem(f"prior physics-input equivalence failed: {exc}", "lineage")
    else:
        gate.require(
            equivalence == contract.get("prior_credit_equivalence"),
            "prior 101k transport/geometry equivalence record mismatch",
            "lineage",
        )
    return source_contract, environment


def _validate_campaign_control_files(
    contract: dict[str, Any],
    geometry: str,
    stage_key: str,
    gate: common.Gate,
) -> tuple[Path, Path]:
    campaign_contract = batch.campaign_dir(geometry, stage_key) / "batch_contract.json"
    normalization = batch.campaign_dir(geometry, stage_key) / "normalization.json"
    gate.require(campaign_contract.is_file() and normalization.is_file(),
                 f"{geometry}: campaign contract/normalization missing", "campaigns")
    if campaign_contract.is_file():
        try:
            observed_campaign = _json(campaign_contract)
            expected_campaign = batch._campaign_contract_payload(contract, geometry, stage_key)
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, RuntimeError, ValueError) as exc:
            gate.problem(f"{geometry}: campaign contract unreadable/unbuildable: {exc}", "campaigns")
        else:
            gate.require(observed_campaign == expected_campaign,
                         f"{geometry}: campaign contract payload mismatch", "campaigns")
    if normalization.is_file() and campaign_contract.is_file():
        try:
            observed_normalization = _json(normalization)
            expected_normalization = batch._normalization_payload(contract, geometry, stage_key)
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, RuntimeError, ValueError) as exc:
            gate.problem(f"{geometry}: normalization unreadable/unbuildable: {exc}", "campaigns")
        else:
            gate.require(observed_normalization == expected_normalization,
                         f"{geometry}: normalization payload mismatch", "campaigns")
    return campaign_contract, normalization


def _validate_pair_receipt_exact(
    pair: dict[str, Any],
    ordinal: int,
    label: str,
    gate: common.Gate,
) -> None:
    try:
        expected = batch._pair_receipt_payload(ordinal)
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, RuntimeError, ValueError) as exc:
        gate.problem(f"{label}: expected pair receipt cannot be built: {exc}", "pairing")
        return
    gate.require(pair == expected, f"{label}: pair receipt payload mismatch", "pairing")


def _rehash_prior_credit(
    stage_key: str,
    prior_ledgers: list[dict[str, Any]],
    gate: common.Gate,
) -> dict[str, Any]:
    """Rebind one checkpoint's credited histories to retained artifacts."""
    stage = batch.STAGE_BY_KEY[stage_key]
    family = str(stage["family"])
    mode = str(stage["mode"])
    errors_before = len(gate.errors)
    records: list[dict[str, Any]] = []
    credited: dict[str, int] = {geometry: 0 for geometry in batch.GEOMETRIES}
    for ledger in prior_ledgers[:2]:
        gate.require(
            ledger.get("source_contract_manifest_sha256") == batch.SOURCE_CONTRACT_SHA256,
            f"prior credited source-contract binding mismatch: {ledger.get('batch_id')}",
            "prior_credit",
        )
        for geometry in batch.GEOMETRIES:
            try:
                jobs = batch._family_jobs(ledger, geometry, mode, family)
            except (SystemExit, KeyError, TypeError, ValueError) as exc:
                gate.problem(f"{geometry}: cannot enumerate credited {stage_key} jobs: {exc}", "prior_credit")
                continue
            events = sum(int(job.get("events", 0)) for job in jobs)
            credited[geometry] += events
            for job in jobs:
                for key, hash_key in (
                    ("job_source", "job_source_sha256"),
                    ("sim", "sim_sha256"),
                    ("isotope_dat", "isotope_dat_sha256"),
                    ("log", "log_sha256"),
                ):
                    value = job.get(key)
                    expected_hash = job.get(hash_key)
                    path = common.resolve_repo_path(str(value or "__missing__"))
                    valid = path.is_file() and path.stat().st_size > 0
                    gate.require(valid, f"prior credited artifact missing/empty: {value}", "prior_credit")
                    observed_hash: str | None = None
                    stable_size: int | None = None
                    if valid:
                        before = path.stat()
                        observed_hash = smoke.sha256(path)
                        after = path.stat()
                        stable_size = after.st_size
                        gate.require(
                            (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
                            f"prior credited artifact changed while hashing: {value}",
                            "prior_credit",
                        )
                    gate.require(observed_hash == expected_hash,
                                 f"prior credited artifact hash mismatch: {value}", "prior_credit")
                    records.append({
                        "batch_id": ledger.get("batch_id"),
                        "geometry": geometry,
                        "family": family,
                        "mode": mode,
                        "events": int(job.get("events", 0)),
                        "kind": key,
                        "path": value,
                        "sha256": observed_hash,
                        "bytes": stable_size,
                    })
    for geometry, events in credited.items():
        gate.require(events == int(stage["prior_events_per_geometry"]),
                     f"{geometry}: total prior {stage_key} credit mismatch", "prior_credit")
    return {
        "status": "PASS" if len(gate.errors) == errors_before else "FAIL",
        "stage": stage_key,
        "family": family,
        "mode": mode,
        "credited_events_per_geometry": credited,
        "artifact_count": len(records),
        "artifact_records_sha256": batch._json_sha256(records),
        "artifacts": records,
    }


def _stage_spec(stage: str) -> tuple[dict[str, Any], Path, Path, str]:
    if stage not in batch.STAGE_BY_KEY:
        raise ValueError(f"unknown stage: {stage}")
    spec = batch.STAGE_BY_KEY[stage]
    status_token = stage.upper().replace("-", "_")
    return (
        spec,
        batch.checkpoint_report_path(stage),
        batch.checkpoint_ledger_path(stage),
        f"PASS__BATCH0004_{status_token}_1M_SCREENING_MERGE_ELIGIBLE",
    )


def validate_stage(stage: str) -> tuple[dict[str, Any], dict[str, Any]]:
    gate = common.Gate()
    spec, report_path, _, ledger_status = _stage_spec(stage)
    start_ordinal = int(spec["global_start_ordinal"])
    end_ordinal = int(spec["global_end_ordinal"])
    cumulative_target = int(spec["target_events_per_geometry"])
    prior_events = int(spec["prior_events_per_geometry"])
    expected_new = int(spec["new_events_per_geometry"])
    required = (batch.GLOBAL_CONTRACT, batch.SOURCE_CONTRACT, batch.BATCH0000_LEDGER,
                batch.BATCH0001_LEDGER, batch.BATCH0002_LEDGER,
                batch.BATCH0003_CONTRACT)
    for path in required:
        gate.require(path.is_file(), f"missing required input: {smoke.rel(path)}", "contract")
    if not all(path.is_file() for path in required):
        report = {"schema_version": 1, "status": "FAIL", "stage": stage,
                  "errors": gate.errors, "checks": dict(gate.checks)}
        ledger = {"schema_version": 1, "status": "FAIL_NOT_MERGE_ELIGIBLE",
                  "stage": stage, "errors": gate.errors}
        return report, ledger
    contract = _json(batch.GLOBAL_CONTRACT)
    dependency = contract.get("batch0003_predecessor_authority", {})
    for key in ("report", "ledger"):
        value = dependency.get(key)
        path = batch.ROOT / value if isinstance(value, str) else batch.ROOT / "__missing__"
        gate.require(path.is_file(), f"missing predecessor {key}: {value}", "contract")
    if gate.errors:
        report = {"schema_version": 1, "status": "FAIL", "stage": stage,
                  "errors": gate.errors, "checks": dict(gate.checks)}
        ledger = {"schema_version": 1, "status": "FAIL_NOT_MERGE_ELIGIBLE",
                  "stage": stage, "errors": gate.errors}
        return report, ledger
    _, environment = _full_contract_gate(contract, gate)
    contract_hash = smoke.sha256(batch.GLOBAL_CONTRACT)
    planned_seeds = {batch.shard_seed(ordinal) for ordinal in range(start_ordinal, end_ordinal + 1)}
    prior_ledgers = [_json(path) for path in (batch.BATCH0000_LEDGER, batch.BATCH0001_LEDGER, batch.BATCH0002_LEDGER)]
    historical = batch._prior_seeds(*prior_ledgers)
    historical.update(
        int(row["seed"])
        for row in _json(batch.BATCH0003_CONTRACT).get("statistics", {}).get("paired_shards", [])
    )
    gate.require(planned_seeds.isdisjoint(historical),
                 "stage seed registry overlaps prior batches", "seeds")
    prior_credit_revalidation_initial = _rehash_prior_credit(stage, prior_ledgers, gate)

    campaigns: list[dict[str, Any]] = []
    initial_input_digests: dict[str, str] = {}
    for geometry in batch.GEOMETRIES:
        try:
            current_input_digest = batch._verify_attempt_inputs(
                contract, geometry, start_ordinal, environment
            )
        except Exception as exc:
            gate.problem(f"{geometry}: current frozen input verification failed: {exc}", "input_integrity")
            current_input_digest = ""
        initial_input_digests[geometry] = current_input_digest
        jobs: list[dict[str, Any]] = []
        tt_values: list[float] = []
        for ordinal in range(start_ordinal, end_ordinal + 1):
            label = f"{geometry}/shard{ordinal:04d}"
            receipt_path = batch.geometry_receipt_path(geometry, ordinal)
            pair_path = batch.pair_receipt_path(ordinal)
            gate.require(receipt_path.is_file(), f"{label}: geometry receipt missing", "receipts")
            gate.require(pair_path.is_file(), f"{label}: pair receipt missing", "receipts")
            if not receipt_path.is_file() or not pair_path.is_file():
                continue
            receipt = _json(receipt_path)
            attempt = int(receipt.get("selected_attempt", -1))
            validation, errors = validate_attempt(contract, geometry, ordinal, attempt)
            for error in errors:
                gate.problem(f"{label}: {error}", "shards")
            gate.require(
                validation.get("frozen_input_bundle_sha256") == current_input_digest,
                f"{label}: signed attempt input bundle differs from current frozen bundle",
                "input_integrity",
            )
            validation_path = _expected_attempt_paths(geometry, ordinal, attempt)["attempt_validation"]
            gate.require(validation_path.is_file() and _json(validation_path) == validation,
                         f"{label}: attempt validation file mismatch", "receipts")
            if validation_path.is_file():
                expected_receipt = _receipt_payload(validation, validation_path)
                gate.require(receipt == expected_receipt,
                             f"{label}: immutable geometry receipt mismatch", "receipts")
            pair = _json(pair_path)
            _validate_pair_receipt_exact(pair, ordinal, label, gate)
            gate.require(pair.get("status") == "PASS__PAIRED_SHARD_MERGE_ELIGIBLE",
                         f"{label}: pair receipt status mismatch", "pairing")
            gate.require(pair.get("global_ordinal") == ordinal
                         and pair.get("stage") == stage
                         and pair.get("stage_ordinal") == batch.shard_spec(ordinal)["stage_ordinal"]
                         and pair.get("events_per_geometry") == batch.shard_events(ordinal)
                         and pair.get("paired_seed") == batch.shard_seed(ordinal),
                         f"{label}: pair identity mismatch", "pairing")
            gate.require(pair.get("pairing_rule") == batch.PAIRING_RULE
                         and pair.get("statistical_semantics") == batch.PAIRING_STATISTICAL_SEMANTICS,
                         f"{label}: operational/statistical pairing semantics mismatch", "pairing")
            bound = pair.get("geometry_receipts", {}).get(geometry, {})
            gate.require(bound.get("path") == smoke.rel(receipt_path)
                         and bound.get("sha256") == smoke.sha256(receipt_path),
                         f"{label}: pair-to-geometry receipt binding mismatch", "pairing")
            dat_tt = validation.get("TT_s_from_isotope_dat")
            if isinstance(dat_tt, (int, float)) and dat_tt > 0:
                tt_values.append(float(dat_tt))
            jobs.append(_ledger_job_payload(validation, ordinal, attempt, receipt_path, pair_path))
        new_events = sum(int(job["events"]) for job in jobs)
        expected_shards = int(spec["paired_shards"])
        gate.require(len(jobs) == expected_shards,
                     f"{geometry}: validated shard count mismatch", "campaigns")
        gate.require(new_events == expected_new, f"{geometry}: new event count mismatch", "campaigns")
        gate.require(len({int(job["seed"]) for job in jobs}) == expected_shards,
                     f"{geometry}: duplicate stage seed", "seeds")
        try:
            current_input_digest_post = batch._verify_attempt_inputs(
                contract, geometry, start_ordinal, environment
            )
        except Exception as exc:
            gate.problem(f"{geometry}: post-scan frozen input verification failed: {exc}", "input_integrity")
            current_input_digest_post = ""
        gate.require(current_input_digest_post == current_input_digest,
                     f"{geometry}: frozen input bundle drifted during stage scan", "input_integrity")
        campaign_contract, normalization = _validate_campaign_control_files(
            contract, geometry, stage, gate
        )
        campaigns.append({
            "geometry": geometry,
            "mode": spec["mode"],
            "family": spec["family"],
            "stage": stage,
            "prior_events_credited": prior_events,
            "new_events_validated": new_events,
            "cumulative_events": prior_events + new_events,
            "validated_shards": len(jobs),
            "TT_s_new_sum": math.fsum(tt_values),
            "flux_cm2_s": common.source_flux(
                batch.source_card_path(geometry, str(spec["family"]))
            ),
            "TT_authority": batch.TT_AUTHORITY,
            "campaign_contract": smoke.rel(campaign_contract),
            "campaign_contract_sha256": smoke.sha256(campaign_contract) if campaign_contract.is_file() else None,
            "normalization": smoke.rel(normalization),
            "normalization_sha256": smoke.sha256(normalization) if normalization.is_file() else None,
            "jobs": jobs,
        })

    gate.require(len(campaigns) == len(batch.GEOMETRIES), "campaign count mismatch", "campaigns")
    for ordinal in range(start_ordinal, end_ordinal + 1):
        seeds = {
            job["seed"]
            for campaign in campaigns
            for job in campaign["jobs"]
            if job["ordinal"] == ordinal
        }
        gate.require(seeds == {batch.shard_seed(ordinal)},
                     f"shard{ordinal:04d}: cross-geometry paired seed mismatch", "pairing")
    try:
        _, final_environment = _full_contract_gate(contract, gate)
    except (SystemExit, OSError, KeyError, TypeError, ValueError, RuntimeError) as exc:
        gate.problem(f"final full input gate failed: {exc}", "input_integrity")
    else:
        for geometry in batch.GEOMETRIES:
            try:
                final_digest = batch._verify_attempt_inputs(
                    contract, geometry, start_ordinal, final_environment
                )
            except Exception as exc:
                gate.problem(f"{geometry}: final frozen input verification failed: {exc}", "input_integrity")
                continue
            gate.require(final_digest == initial_input_digests.get(geometry),
                         f"{geometry}: frozen input bundle drifted across full stage validation",
                         "input_integrity")
    prior_credit_revalidation = _rehash_prior_credit(stage, prior_ledgers, gate)
    gate.require(prior_credit_revalidation == prior_credit_revalidation_initial,
                 "prior credited artifacts drifted during stage validation", "prior_credit")
    status = "PASS" if not gate.errors else "FAIL"
    report = {
        "schema_version": 1,
        "status": status,
        "batch_id": batch.BATCH_ID,
        "campaign_version": batch.CAMPAIGN_VERSION,
        "stage": stage,
        "family": spec["family"],
        "mode": spec["mode"],
        "cumulative_target_events_per_geometry": cumulative_target,
        "global_contract": smoke.rel(batch.GLOBAL_CONTRACT),
        "global_contract_sha256": contract_hash,
        "campaigns": campaigns,
        "validated_new_event_count": sum(row["new_events_validated"] for row in campaigns),
        "validated_job_count": sum(len(row["jobs"]) for row in campaigns),
        "prior_credit_revalidation": prior_credit_revalidation,
        "checks": dict(gate.checks),
        "errors": gate.errors,
    }
    ledger = {
        "schema_version": 1,
        "status": ledger_status if status == "PASS" else "FAIL_NOT_MERGE_ELIGIBLE",
        "batch_id": batch.BATCH_ID,
        "campaign_version": batch.CAMPAIGN_VERSION,
        "stage": stage,
        "family": spec["family"],
        "mode": spec["mode"],
        "source_contract_manifest": smoke.rel(batch.SOURCE_CONTRACT),
        "source_contract_manifest_sha256": batch.SOURCE_CONTRACT_SHA256,
        "prior_batches": contract.get("lineage", []),
        "global_contract": smoke.rel(batch.GLOBAL_CONTRACT),
        "global_contract_sha256": contract_hash,
        "validation_report": smoke.rel(report_path),
        "pairing_rule": batch.PAIRING_RULE,
        "statistical_pairing_semantics": batch.PAIRING_STATISTICAL_SEMANTICS,
        "prior_credit_equivalence": contract.get("prior_credit_equivalence"),
        "prior_credit_revalidation": prior_credit_revalidation,
        "transport": contract.get("transport"),
        "transport_core": contract.get("transport_core"),
        "geometry_bundles": contract.get("geometry_bundles"),
        "pooling_boundary": "never pool across geometry, mode, or family",
        "TT_authority": batch.TT_AUTHORITY,
        "cumulative_target_events_per_geometry": cumulative_target,
        "campaigns": campaigns,
        "errors": gate.errors,
    }
    return report, ledger


def _write_stage(stage: str, *, check: bool) -> int:
    _, report_path, ledger_path, _ = _stage_spec(stage)
    report, ledger = validate_stage(stage)
    if check:
        authority_errors: list[str] = []
        report_exists = report_path.is_file()
        ledger_exists = ledger_path.is_file()
        if not report_exists and not ledger_exists:
            authority_errors.append("canonical PASS report and ledger are both missing")
        elif report_exists != ledger_exists:
            authority_errors.append("canonical PASS report and ledger are not a complete pair")
        elif report_exists and ledger_exists:
            try:
                existing_report = _json(report_path)
                existing_ledger = _json(ledger_path)
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                authority_errors.append(f"canonical authority JSON unreadable: {exc}")
            else:
                if existing_report != report:
                    authority_errors.append("canonical PASS report differs from live revalidation")
                expected_ledger = dict(ledger)
                expected_ledger["validation_report_sha256"] = smoke.sha256(report_path)
                if existing_ledger != expected_ledger:
                    authority_errors.append("canonical ledger differs from live expected ledger")
        check_pass = report["status"] == "PASS" and not authority_errors
        print(json.dumps({
            "status": "PASS" if check_pass else "FAIL",
            "stage": stage,
            "errors": list(report["errors"]) + authority_errors,
            "mode": "READ_ONLY_CHECK",
            "would_write_ledger": report["status"] == "PASS",
            "canonical_authority_present": report_exists or ledger_exists,
            "canonical_authority_pair_valid": report_exists and ledger_exists and not authority_errors,
        }, indent=2, ensure_ascii=False))
        return 0 if check_pass else 1
    # A failed validation is diagnostic only.  Publishing a canonical
    # write-once FAIL report would poison resume because the missing ledger
    # could never be completed after the underlying shard is repaired.
    if report["status"] != "PASS":
        print(json.dumps({
            "status": report["status"],
            "stage": stage,
            "errors": report["errors"],
            "validation": None,
            "ledger": None,
            "authority_written": False,
        }, indent=2, ensure_ascii=False))
        return 1

    if report_path.exists():
        if _json(report_path) != report:
            raise SystemExit(f"existing batch0004 {stage} PASS report differs from revalidation")
    else:
        batch.atomic_write_once_json(report_path, report)
    ledger["validation_report_sha256"] = smoke.sha256(report_path)
    if ledger_path.exists():
        if _json(ledger_path) != ledger:
            raise SystemExit(f"existing batch0004 {stage} ledger differs from revalidation")
    else:
        batch.atomic_write_once_json(ledger_path, ledger)
    print(json.dumps({
        "status": report["status"],
        "stage": stage,
        "errors": report["errors"],
        "validation": smoke.rel(report_path),
        "ledger": smoke.rel(ledger_path) if ledger_path.exists() else None,
    }, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


def _rehash_prior_only_muminus_instant(
    prior_ledgers: list[dict[str, Any]], gate: common.Gate
) -> dict[str, Any]:
    """Rebind the over-target batch0002 negative-muon instant credit."""
    errors_before = len(gate.errors)
    records: list[dict[str, Any]] = []
    campaigns: list[dict[str, Any]] = []
    credited: dict[str, int] = {geometry: 0 for geometry in batch.GEOMETRIES}
    for geometry in batch.GEOMETRIES:
        normalized_jobs: list[dict[str, Any]] = []
        authoritative_flux = common.source_flux(
            batch.source_card_path(geometry, "muminus")
        )
        for ledger in prior_ledgers:
            try:
                campaign = batch._campaign(ledger, geometry, "instant")
                jobs = [
                    job for job in campaign.get("jobs", [])
                    if job.get("family") == "muminus"
                ]
                if not jobs:
                    raise ValueError("campaign has no muminus job")
            except (SystemExit, KeyError, TypeError, ValueError) as exc:
                gate.problem(f"{geometry}: cannot enumerate prior muminus instant jobs: {exc}",
                             "prior_credit")
                continue
            for job in jobs:
                events = int(job.get("events", 0))
                credited[geometry] += events
                tt_log = job.get("TT_s_from_log", campaign.get("TT_s_from_log"))
                tt_dat = job.get(
                    "TT_s_from_isotope_dat", campaign.get("TT_s_from_isotope_dat")
                )
                flux = job.get("flux_cm2_s", campaign.get("flux_cm2_s"))
                tt_expected = job.get(
                    "TT_s_expected_mean_from_events_flux_area",
                    campaign.get("TT_s_expected_mean_from_events_flux_area"),
                )
                tt_authority = job.get(
                    "TT_authority", ledger.get("TT_authority", batch.TT_AUTHORITY)
                )
                expected_from_current_flux = (
                    events / (authoritative_flux * math.pi * batch.FARFIELD_RADIUS_CM**2)
                    if events > 0 and authoritative_flux > 0 else math.nan
                )
                numeric_values = {
                    "TT_s_from_log": tt_log,
                    "TT_s_from_isotope_dat": tt_dat,
                    "flux_cm2_s": flux,
                    "TT_s_expected_mean_from_events_flux_area": tt_expected,
                }
                for name, value in numeric_values.items():
                    gate.require(
                        isinstance(value, (int, float))
                        and math.isfinite(float(value))
                        and float(value) > 0,
                        f"{geometry}/{ledger.get('batch_id')}: invalid prior muminus {name}",
                        "prior_credit",
                    )
                if isinstance(tt_log, (int, float)) and isinstance(tt_dat, (int, float)):
                    gate.require(
                        math.isclose(float(tt_log), float(tt_dat), rel_tol=2e-3, abs_tol=2e-6),
                        f"{geometry}/{ledger.get('batch_id')}: prior muminus DAT/log TT mismatch",
                        "prior_credit",
                    )
                if isinstance(flux, (int, float)):
                    gate.require(
                        math.isclose(float(flux), authoritative_flux, rel_tol=1e-12, abs_tol=0.0),
                        f"{geometry}/{ledger.get('batch_id')}: prior muminus flux mismatch",
                        "prior_credit",
                    )
                if isinstance(tt_expected, (int, float)):
                    gate.require(
                        math.isclose(
                            float(tt_expected), expected_from_current_flux,
                            rel_tol=1e-12, abs_tol=1e-15,
                        ),
                        f"{geometry}/{ledger.get('batch_id')}: prior muminus expected TT mismatch",
                        "prior_credit",
                    )
                gate.require(events > 0,
                             f"{geometry}/{ledger.get('batch_id')}: invalid prior muminus events",
                             "prior_credit")
                for key, hash_key in (
                    ("job_source", "job_source_sha256"),
                    ("sim", "sim_sha256"),
                    ("isotope_dat", "isotope_dat_sha256"),
                    ("log", "log_sha256"),
                ):
                    value = job.get(key)
                    path = common.resolve_repo_path(str(value or "__missing__"))
                    valid = path.is_file() and path.stat().st_size > 0
                    gate.require(valid, f"prior muminus artifact missing/empty: {value}", "prior_credit")
                    observed: str | None = None
                    size: int | None = None
                    if valid:
                        before = path.stat()
                        observed = smoke.sha256(path)
                        after = path.stat()
                        size = after.st_size
                        gate.require(
                            (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
                            f"prior muminus artifact changed while hashing: {value}",
                            "prior_credit",
                        )
                    gate.require(observed == job.get(hash_key),
                                 f"prior muminus artifact hash mismatch: {value}", "prior_credit")
                    records.append({
                        "batch_id": ledger.get("batch_id"),
                        "geometry": geometry,
                        "events": int(job.get("events", 0)),
                        "kind": key,
                        "path": value,
                        "sha256": observed,
                        "bytes": size,
                    })
                normalized_jobs.append({
                    "source_batch_id": ledger.get("batch_id"),
                    "source_campaign_version": ledger.get("campaign_version"),
                    "source_job_payload_sha256": batch._json_sha256(job),
                    "geometry": geometry,
                    "mode": "instant",
                    "family": "muminus",
                    "job_name": job.get("job_name"),
                    "events": events,
                    "seed": job.get("seed"),
                    "flux_cm2_s": flux,
                    "TT_s_expected_mean_from_events_flux_area": tt_expected,
                    "TT_s_from_log": tt_log,
                    "TT_s_from_isotope_dat": tt_dat,
                    "TT_authority": tt_authority,
                    "job_source": job.get("job_source"),
                    "job_source_sha256": job.get("job_source_sha256"),
                    "sim": job.get("sim"),
                    "sim_sha256": job.get("sim_sha256"),
                    "isotope_dat": job.get("isotope_dat"),
                    "isotope_dat_sha256": job.get("isotope_dat_sha256"),
                    "log": job.get("log"),
                    "log_sha256": job.get("log_sha256"),
                    "isotope_store": job.get("isotope_store"),
                    "ia_init": job.get("ia_init"),
                })
        campaigns.append({
            "geometry": geometry,
            "mode": "instant",
            "family": "muminus",
            "prior_only": True,
            "prior_events_credited": credited[geometry],
            "new_events_validated": 0,
            "cumulative_events": credited[geometry],
            "screening_target_events": batch.TARGET_EVENTS["muminus"],
            "over_target_events": credited[geometry] - batch.TARGET_EVENTS["muminus"],
            "TT_s_credited_sum": math.fsum(
                float(job["TT_s_from_isotope_dat"])
                for job in normalized_jobs
                if isinstance(job.get("TT_s_from_isotope_dat"), (int, float))
            ),
            "flux_cm2_s": authoritative_flux,
            "TT_authority": batch.TT_AUTHORITY,
            "jobs": normalized_jobs,
        })
    for geometry, events in credited.items():
        gate.require(events == batch.PRIOR_EVENTS[("muminus", "instant")],
                     f"{geometry}: prior-only muminus instant credit mismatch", "prior_credit")
    return {
        "status": "PASS" if len(gate.errors) == errors_before else "FAIL",
        "family": "muminus",
        "mode": "instant",
        "credited_events_per_geometry": credited,
        "screening_target_events_per_geometry": batch.TARGET_EVENTS["muminus"],
        "artifact_count": len(records),
        "artifact_records_sha256": batch._json_sha256(records),
        "artifacts": records,
        "campaigns": campaigns,
    }


def validate_final() -> tuple[dict[str, Any], dict[str, Any]]:
    gate = common.Gate()
    required = [batch.GLOBAL_CONTRACT, batch.SOURCE_CONTRACT]
    required.extend(batch.checkpoint_report_path(key) for key in batch.STAGE_ORDER)
    required.extend(batch.checkpoint_ledger_path(key) for key in batch.STAGE_ORDER)
    for path in required:
        gate.require(path.is_file(), f"missing final input: {smoke.rel(path)}", "authority")
    if not batch.GLOBAL_CONTRACT.is_file():
        report = {"schema_version": 1, "status": "FAIL", "stage": "final",
                  "errors": gate.errors, "checks": dict(gate.checks)}
        return report, {"schema_version": 1, "status": "FAIL_NOT_MERGE_ELIGIBLE",
                        "stage": "final", "errors": gate.errors}

    contract = _json(batch.GLOBAL_CONTRACT)
    _full_contract_gate(contract, gate)
    checkpoint_authorities: list[dict[str, Any]] = []
    all_campaigns: list[dict[str, Any]] = []
    for stage in batch.STAGE_ORDER:
        live_report, live_ledger = validate_stage(stage)
        report_path = batch.checkpoint_report_path(stage)
        ledger_path = batch.checkpoint_ledger_path(stage)
        if not report_path.is_file() or not ledger_path.is_file():
            continue
        existing_report = _json(report_path)
        existing_ledger = _json(ledger_path)
        expected_ledger = dict(live_ledger)
        expected_ledger["validation_report_sha256"] = smoke.sha256(report_path)
        gate.require(live_report.get("status") == "PASS",
                     f"{stage}: live checkpoint revalidation failed", "checkpoints")
        gate.require(existing_report == live_report,
                     f"{stage}: checkpoint report differs from live revalidation", "checkpoints")
        gate.require(existing_ledger == expected_ledger,
                     f"{stage}: checkpoint ledger differs from live revalidation", "checkpoints")
        checkpoint_authorities.append({
            "stage": stage,
            "report": smoke.rel(report_path),
            "report_sha256": smoke.sha256(report_path),
            "ledger": smoke.rel(ledger_path),
            "ledger_sha256": smoke.sha256(ledger_path),
            "status": existing_ledger.get("status"),
        })
        all_campaigns.extend(existing_ledger.get("campaigns", []))
    gate.require(len(checkpoint_authorities) == len(batch.STAGE_ORDER),
                 "final checkpoint authority count mismatch", "checkpoints")
    prior_only = _rehash_prior_only_muminus_instant(
        [_json(path) for path in (batch.BATCH0000_LEDGER, batch.BATCH0001_LEDGER,
                                  batch.BATCH0002_LEDGER)],
        gate,
    )
    status = "PASS" if not gate.errors else "FAIL"
    report = {
        "schema_version": 1,
        "status": status,
        "batch_id": batch.BATCH_ID,
        "campaign_version": batch.CAMPAIGN_VERSION,
        "stage": "final",
        "screening_semantics": (
            "1M gamma-equivalent reduced-statistics checkpoint; not historical full-stat"
        ),
        "global_contract": smoke.rel(batch.GLOBAL_CONTRACT),
        "global_contract_sha256": smoke.sha256(batch.GLOBAL_CONTRACT),
        "checkpoint_authorities": checkpoint_authorities,
        "prior_only_muminus_instant": prior_only,
        "validated_new_event_count": sum(
            int(row.get("new_events_validated", 0)) for row in all_campaigns
        ),
        "validated_job_count": sum(len(row.get("jobs", [])) for row in all_campaigns),
        "checks": dict(gate.checks),
        "errors": gate.errors,
    }
    ledger = {
        "schema_version": 1,
        "status": (
            "PASS__BATCH0004_1M_EQUIVALENT_SCREENING_MERGE_ELIGIBLE"
            if status == "PASS" else "FAIL_NOT_MERGE_ELIGIBLE"
        ),
        "batch_id": batch.BATCH_ID,
        "campaign_version": batch.CAMPAIGN_VERSION,
        "stage": "final",
        "screening_semantics": report["screening_semantics"],
        "source_contract_manifest": smoke.rel(batch.SOURCE_CONTRACT),
        "source_contract_manifest_sha256": batch.SOURCE_CONTRACT_SHA256,
        "global_contract": smoke.rel(batch.GLOBAL_CONTRACT),
        "global_contract_sha256": smoke.sha256(batch.GLOBAL_CONTRACT),
        "validation_report": smoke.rel(batch.FINAL_VALIDATION_REPORT),
        "checkpoint_authorities": checkpoint_authorities,
        "prior_batches": contract.get("lineage", []),
        "prior_only_muminus_instant": prior_only,
        "transport": contract.get("transport"),
        "transport_core": contract.get("transport_core"),
        "geometry_bundles": contract.get("geometry_bundles"),
        "pairing_rule": batch.PAIRING_RULE,
        "statistical_pairing_semantics": batch.PAIRING_STATISTICAL_SEMANTICS,
        "pooling_boundary": "never pool across geometry, mode, or family",
        "TT_authority": batch.TT_AUTHORITY,
        "campaigns": all_campaigns + prior_only["campaigns"],
        "errors": gate.errors,
    }
    return report, ledger


def _write_final(*, check: bool) -> int:
    report, ledger = validate_final()
    report_path = batch.FINAL_VALIDATION_REPORT
    ledger_path = batch.FINAL_LEDGER
    if check:
        authority_errors: list[str] = []
        report_exists = report_path.is_file()
        ledger_exists = ledger_path.is_file()
        if not report_exists and not ledger_exists:
            authority_errors.append("canonical final report and ledger are both missing")
        elif report_exists != ledger_exists:
            authority_errors.append("canonical final report and ledger are not a complete pair")
        elif report_exists and ledger_exists:
            existing_report = _json(report_path)
            existing_ledger = _json(ledger_path)
            expected_ledger = dict(ledger)
            expected_ledger["validation_report_sha256"] = smoke.sha256(report_path)
            if existing_report != report:
                authority_errors.append("canonical final report differs from live revalidation")
            if existing_ledger != expected_ledger:
                authority_errors.append("canonical final ledger differs from live revalidation")
        passed = report["status"] == "PASS" and not authority_errors
        print(json.dumps({
            "status": "PASS" if passed else "FAIL",
            "stage": "final",
            "mode": "READ_ONLY_CHECK",
            "errors": list(report["errors"]) + authority_errors,
        }, indent=2, ensure_ascii=False))
        return 0 if passed else 1
    if report["status"] != "PASS":
        print(json.dumps({"status": "FAIL", "stage": "final", "errors": report["errors"],
                          "authority_written": False}, indent=2, ensure_ascii=False))
        return 1
    if report_path.exists():
        if _json(report_path) != report:
            raise SystemExit("existing batch0004 final PASS report differs from revalidation")
    else:
        batch.atomic_write_once_json(report_path, report)
    ledger["validation_report_sha256"] = smoke.sha256(report_path)
    if ledger_path.exists():
        if _json(ledger_path) != ledger:
            raise SystemExit("existing batch0004 final ledger differs from revalidation")
    else:
        batch.atomic_write_once_json(ledger_path, ledger)
    print(json.dumps({"status": "PASS", "stage": "final",
                      "validation": smoke.rel(report_path), "ledger": smoke.rel(ledger_path)},
                     indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--shard", action="store_true", help="validate and sign one geometry shard")
    mode.add_argument("--stage", choices=batch.STAGE_ORDER, help="validate one family/mode checkpoint")
    mode.add_argument("--final", action="store_true", help="validate all checkpoint authorities")
    parser.add_argument("--geometry", choices=tuple(batch.GEOMETRIES))
    parser.add_argument("--ordinal", type=int)
    parser.add_argument("--attempt", type=int)
    parser.add_argument("--check", action="store_true", help="read-only; do not write receipt/report/ledger")
    args = parser.parse_args()
    if args.shard:
        if args.geometry is None or args.ordinal is None or args.attempt is None:
            parser.error("--shard requires --geometry, --ordinal, and --attempt")
        result, returncode = validate_shard(
            args.geometry,
            args.ordinal,
            args.attempt,
            write=not args.check,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
        return returncode
    if args.geometry is not None or args.ordinal is not None or args.attempt is not None:
        parser.error("--geometry/--ordinal/--attempt are only valid with --shard")
    if args.final:
        return _write_final(check=args.check)
    return _write_stage(str(args.stage), check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
