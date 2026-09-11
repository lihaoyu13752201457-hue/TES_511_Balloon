#!/usr/bin/env python3
"""Pure validation helpers for the M05 batch0006 campaign controller.

The functions in this module do not launch transport and do not write files.
They deliberately accept already-read values where practical so the campaign
controller can freeze inputs before calling them and can unit-test its gates
without depending on live machine state.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Collection, Iterable, Mapping, Sequence


BATCH_ID = "m05_16h_90gb_campaign_batch0006"
FORBIDDEN_SPECTRUM_SUBSTRING = "cosima_spectra_dp_2602units"
CORRECTED_SPECTRUM_ROOT = (
    "engineering/particle_source_unit_repair_20260811/spectra/correct_keV_total/"
)

REQUESTED_CAMPAIGN_CAP_BYTES = 90_000_000_000
FILESYSTEM_RESERVE_BYTES = 20 * 1024**3
SMOKE_HARD_CAP_BYTES = 8_000_000_000
PRE_PROTON_RESERVATION_BYTES = 20_000_000_000
CAMPAIGN_EMERGENCY_RESERVE_BYTES = 5_000_000_000
RSS_HEADROOM_BYTES = 2 * 1024**3

SEVEN_FAMILY_TOTAL_EVENTS = 6_001_652
SEVEN_FAMILY_TOTALS = {
    "gamma": 5_086_475,
    "neutron": 518_725,
    "eplus": 131_257,
    "alpha": 13_441,
    "eminus": 242_617,
    "muplus": 6_248,
    "muminus": 2_889,
}
GEOMETRY_LABELS = frozenset({"Mass_model_511", "S3d_O8"})
MODES = frozenset({"instant", "buildup"})
SMOKE_TOTAL_EVENTS = 55_424
SMOKE_TOTAL_SHARDS = 100

_SEED_META_WORDS = frozenset(
    {
        "base",
        "stride",
        "count",
        "sha256",
        "digest",
        "hash",
        "policy",
        "rule",
        "formula",
        "status",
        "collision",
        "namespace",
    }
)
_SEED_CONTAINER_KEYS = frozenset(
    {
        "seed_registry",
        "seeds",
        "planned_seeds",
        "registered_planned_seeds",
        "prior_registered_seeds",
        "expected_seeds",
        "expected_seeds_by_mode",
        "paired_seeds",
        "frozen_planned_seeds",
    }
)


class CampaignValidationError(ValueError):
    """Raised when a frozen batch0006 contract does not close exactly."""


def _path_text(parts: Sequence[str | int]) -> str:
    result = "$"
    for part in parts:
        if isinstance(part, int):
            result += f"[{part}]"
        else:
            result += "." + part
    return result


def _seed_key_kind(key: str) -> tuple[bool, bool]:
    """Return ``(seed_bearing, container)`` for one JSON object key."""
    normalized = key.strip().lower().replace("-", "_")
    words = set(normalized.split("_"))
    if not ({"seed", "seeds"} & words):
        return False, False
    if words & _SEED_META_WORDS:
        return False, False
    return True, normalized in _SEED_CONTAINER_KEYS or normalized.endswith("_seeds")


def _is_seed_metadata_key(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_")
    words = set(normalized.split("_"))
    return bool(({"seed", "seeds"} & words) and (words & _SEED_META_WORDS))


def extract_seed_evidence(payload: Any) -> dict[int, tuple[str, ...]]:
    """Recursively extract used/registered/frozen planned seed values.

    Every returned integer is accompanied by all JSON paths that asserted it.
    Seed metadata (counts, hashes, bases, strides, policies and namespaces) is
    intentionally excluded.  Numeric leaves below a ``seed_registry`` or
    explicit ``*_seeds`` container are included even when their immediate key
    is a mode name such as ``instant``.
    """
    evidence: dict[int, list[str]] = defaultdict(list)

    def visit(value: Any, path: tuple[str | int, ...], seed_context: bool) -> None:
        if isinstance(value, Mapping):
            for raw_key, child in value.items():
                key = str(raw_key)
                seed_bearing, is_container = _seed_key_kind(key)
                child_context = (
                    False
                    if _is_seed_metadata_key(key)
                    else seed_context or seed_bearing or is_container
                )
                visit(child, path + (key,), child_context)
            return
        if isinstance(value, (list, tuple)):
            for index, child in enumerate(value):
                visit(child, path + (index,), seed_context)
            return
        if seed_context and isinstance(value, int) and not isinstance(value, bool) and value > 0:
            evidence[value].append(_path_text(path))

    visit(payload, (), False)
    return {seed: tuple(paths) for seed, paths in sorted(evidence.items())}


def extract_seeds_from_json_files(paths: Iterable[Path]) -> dict[int, tuple[str, ...]]:
    """Read selected small JSON authorities and merge their seed evidence.

    Discovery is intentionally left to the controller: it should pass only the
    batch0000--0005 ledgers/contracts/states and explicitly selected diagnostic
    frozen contracts, rather than blindly parsing large transport products.
    """
    merged: dict[int, list[str]] = defaultdict(list)
    for path in sorted((Path(item) for item in paths), key=lambda item: str(item)):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for seed, json_paths in extract_seed_evidence(payload).items():
            merged[seed].extend(f"{path}:{json_path}" for json_path in json_paths)
    return {seed: tuple(records) for seed, records in sorted(merged.items())}


def derive_fresh_seed(
    identity: str | Sequence[object],
    occupied: Collection[int],
    *,
    namespace: str = BATCH_ID,
    minimum: int = 1,
    maximum: int = 2_147_483_646,
) -> int:
    """Derive a deterministic, signed-32-bit-safe fresh transport seed.

    Collision resolution is itself SHA-256 based, so the result is independent
    of set ordering and reproducible from the frozen identity and registry.
    Geometry should be omitted from ``identity`` when the two geometries are
    intentionally assigned the same operational paired seed.
    """
    if minimum < 1 or maximum < minimum:
        raise CampaignValidationError("invalid seed interval")
    material = identity if isinstance(identity, str) else "\x1f".join(map(str, identity))
    unavailable = set(occupied)
    span = maximum - minimum + 1
    for probe in range(span):
        digest = hashlib.sha256(
            f"{namespace}\x1e{material}\x1e{probe}".encode("utf-8")
        ).digest()
        candidate = minimum + int.from_bytes(digest[:8], "big") % span
        if candidate not in unavailable:
            return candidate
    raise CampaignValidationError("seed interval exhausted")


def derive_fresh_seed_plan(
    identities: Sequence[str | Sequence[object]],
    occupied: Collection[int],
    **kwargs: Any,
) -> list[int]:
    """Derive a unique ordered seed plan, reserving each result immediately."""
    reserved = set(occupied)
    result: list[int] = []
    for identity in identities:
        seed = derive_fresh_seed(identity, reserved, **kwargs)
        reserved.add(seed)
        result.append(seed)
    return result


def _required_columns(rows: Sequence[Mapping[str, str]], required: Collection[str]) -> None:
    if not rows:
        raise CampaignValidationError("CSV has no data rows")
    missing = set(required) - set(rows[0])
    if missing:
        raise CampaignValidationError(f"CSV missing columns: {sorted(missing)}")


def validate_seven_family_rows(
    rows: Sequence[Mapping[str, str]],
    *,
    expected_family_totals: Mapping[str, int] = SEVEN_FAMILY_TOTALS,
    expected_total: int = SEVEN_FAMILY_TOTAL_EVENTS,
) -> dict[str, Any]:
    """Validate the exact 28-cell stage10 allocation and event closure."""
    _required_columns(
        rows,
        {
            "family",
            "geometry",
            "mode",
            "r1_remaining_events",
            "stage10_point_events",
            "initial_shard_events",
        },
    )
    expected_cells = {
        (family, geometry, mode)
        for family in expected_family_totals
        for geometry in GEOMETRY_LABELS
        for mode in MODES
    }
    seen: set[tuple[str, str, str]] = set()
    family_totals: dict[str, int] = defaultdict(int)
    for index, row in enumerate(rows, start=2):
        cell = (row["family"], row["geometry"], row["mode"])
        if cell in seen:
            raise CampaignValidationError(f"duplicate allocation cell at CSV line {index}: {cell}")
        seen.add(cell)
        try:
            remaining = int(row["r1_remaining_events"])
            events = int(row["stage10_point_events"])
            shard = int(row["initial_shard_events"])
        except (TypeError, ValueError) as exc:
            raise CampaignValidationError(f"non-integer allocation value at CSV line {index}") from exc
        if remaining <= 0 or events <= 0 or shard <= 0 or events > remaining:
            raise CampaignValidationError(f"invalid allocation magnitude at CSV line {index}")
        family_totals[cell[0]] += events
    if seen != expected_cells:
        missing = sorted(expected_cells - seen)
        extra = sorted(seen - expected_cells)
        raise CampaignValidationError(f"allocation cell mismatch: missing={missing}, extra={extra}")
    observed_family_totals = dict(sorted(family_totals.items()))
    expected_family_totals_dict = dict(sorted(expected_family_totals.items()))
    if observed_family_totals != expected_family_totals_dict:
        raise CampaignValidationError(
            f"family event totals differ: {observed_family_totals} != {expected_family_totals_dict}"
        )
    observed_total = sum(family_totals.values())
    if observed_total != expected_total:
        raise CampaignValidationError(f"stage10 total {observed_total} != {expected_total}")
    return {
        "status": "PASS",
        "cell_count": len(seen),
        "family_totals": observed_family_totals,
        "total_events": observed_total,
    }


def validate_smoke_rows(
    rows: Sequence[Mapping[str, str]],
    *,
    expected_total_events: int = SMOKE_TOTAL_EVENTS,
    expected_total_shards: int = SMOKE_TOTAL_SHARDS,
) -> dict[str, Any]:
    """Validate stage00 per-cell patterns and selected-arm totals."""
    _required_columns(
        rows,
        {
            "family",
            "events_per_geometry_mode",
            "subshards_per_cell",
            "subshard_pattern",
            "selected_arm_total_events",
        },
    )
    families: set[str] = set()
    total_events = 0
    total_shards = 0
    for index, row in enumerate(rows, start=2):
        family = row["family"]
        if family in families:
            raise CampaignValidationError(f"duplicate smoke family at CSV line {index}: {family}")
        families.add(family)
        try:
            per_cell = int(row["events_per_geometry_mode"])
            per_cell_shards = int(row["subshards_per_cell"])
            declared_total = int(row["selected_arm_total_events"])
            pattern = [int(item) for item in row["subshard_pattern"].split("+")]
        except (TypeError, ValueError) as exc:
            raise CampaignValidationError(f"invalid smoke row at CSV line {index}") from exc
        if len(pattern) != per_cell_shards or any(item <= 0 for item in pattern):
            raise CampaignValidationError(f"smoke shard pattern count mismatch at CSV line {index}")
        if sum(pattern) != per_cell:
            raise CampaignValidationError(f"smoke shard pattern events mismatch at CSV line {index}")
        if declared_total != per_cell * 4:
            raise CampaignValidationError(f"smoke four-cell total mismatch at CSV line {index}")
        total_events += declared_total
        total_shards += per_cell_shards * 4
    if total_events != expected_total_events or total_shards != expected_total_shards:
        raise CampaignValidationError(
            f"smoke closure differs: events={total_events}, shards={total_shards}"
        )
    return {
        "status": "PASS",
        "family_count": len(families),
        "total_events": total_events,
        "total_shards": total_shards,
    }


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """Read a UTF-8 CSV into immutable-validation-friendly row dictionaries."""
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def patch_source_exact(
    source_text: str,
    *,
    seed: int,
    events: int,
    sim_prefix: str,
    isotope_prefix: str,
    mode: str,
    expected_geometry: str | None = None,
) -> str:
    """Patch one corrected-keV production card with exact control-line counts.

    Unlike the legacy helper, malformed/missing/duplicate controls are rejected
    rather than repaired heuristically.  The returned text is deterministic and
    can be hash-bound before launch.
    """
    if mode not in MODES:
        raise CampaignValidationError(f"invalid mode: {mode}")
    if seed <= 0 or events <= 0 or not sim_prefix or not isotope_prefix:
        raise CampaignValidationError("source patch arguments must be positive/non-empty")
    lines = source_text.splitlines()
    controls = {
        "geometry": [],
        "seed": [],
        "events": [],
        "filename": [],
        "isotope": [],
        "store": [],
        "decay": [],
        "run": [],
    }
    for index, raw in enumerate(lines):
        stripped = raw.strip()
        if stripped.startswith("Geometry "):
            controls["geometry"].append(index)
        elif stripped.startswith("Seed "):
            controls["seed"].append(index)
        elif stripped.startswith("Run "):
            controls["run"].append(index)
        elif stripped.startswith("StoreIsotopes"):
            controls["store"].append(index)
        elif stripped.startswith("DecayMode"):
            controls["decay"].append(index)
        elif ".Events" in raw:
            controls["events"].append(index)
        elif ".FileName" in raw:
            controls["filename"].append(index)
        elif ".IsotopeProductionFile" in raw:
            controls["isotope"].append(index)
    for name, indices in controls.items():
        if len(indices) != 1:
            raise CampaignValidationError(f"source requires exactly one {name} control, got {len(indices)}")
    geometry_line = lines[controls["geometry"][0]].strip()
    if expected_geometry is not None and geometry_line != f"Geometry {expected_geometry}":
        raise CampaignValidationError("source geometry does not match the requested geometry")
    if source_text.count(".Spectrum File ") != 20:
        raise CampaignValidationError("source does not have exactly 20 Spectrum File references")
    if source_text.count(CORRECTED_SPECTRUM_ROOT) != 20:
        raise CampaignValidationError("source does not have exactly 20 corrected-keV references")
    if FORBIDDEN_SPECTRUM_SUBSTRING in source_text:
        raise CampaignValidationError("source contains the legacy factor-1000 spectrum reference")
    if lines[controls["store"][0]].strip() != "StoreIsotopes true":
        raise CampaignValidationError("source StoreIsotopes control differs from true")
    if lines[controls["decay"][0]].strip() != "DecayMode ActivationBuildUp":
        raise CampaignValidationError("source DecayMode baseline is not ActivationBuildUp")

    patched: list[str] = []
    for index, raw in enumerate(lines):
        if index == controls["seed"][0]:
            patched.append(f"Seed {seed}")
        elif index == controls["events"][0]:
            prefix = raw.split(".Events", 1)[0].strip()
            patched.append(f"{prefix}.Events {events}")
        elif index == controls["filename"][0]:
            prefix = raw.split(".FileName", 1)[0].strip()
            patched.append(f"{prefix}.FileName {sim_prefix}")
        elif index == controls["isotope"][0]:
            prefix = raw.split(".IsotopeProductionFile", 1)[0].strip()
            patched.append(f"{prefix}.IsotopeProductionFile {isotope_prefix}")
        elif index == controls["decay"][0] and mode == "instant":
            continue
        else:
            patched.append(raw)
    result = "\n".join(patched) + "\n"
    expected_decay_count = 1 if mode == "buildup" else 0
    post_counts = {
        "Seed ": sum(line.strip().startswith("Seed ") for line in patched),
        ".Events": sum(".Events" in line for line in patched),
        ".FileName": sum(".FileName" in line for line in patched),
        ".IsotopeProductionFile": sum(".IsotopeProductionFile" in line for line in patched),
        "StoreIsotopes": sum(line.strip().startswith("StoreIsotopes") for line in patched),
        "DecayMode": sum(line.strip().startswith("DecayMode") for line in patched),
    }
    expected_counts = {
        "Seed ": 1,
        ".Events": 1,
        ".FileName": 1,
        ".IsotopeProductionFile": 1,
        "StoreIsotopes": 1,
        "DecayMode": expected_decay_count,
    }
    if post_counts != expected_counts:
        raise CampaignValidationError(f"patched source control mismatch: {post_counts}")
    return result


def verify_source_patch_exact(source_text: str, patched_text: str, **kwargs: Any) -> None:
    """Reject a job card unless it byte-matches the deterministic exact patch."""
    expected = patch_source_exact(source_text, **kwargs)
    if patched_text != expected:
        raise CampaignValidationError("job source does not exactly match deterministic patch")


def decide_compact_arm(
    authorization: Mapping[str, Any] | None,
    *,
    authorization_is_write_once: bool = False,
    preflight_elapsed_s: float = 0.0,
    required_contract_sha256: str | None = None,
) -> dict[str, Any]:
    """Select compact only on explicit early, write-once transport authority.

    Any missing or ambiguous evidence deterministically returns the rich F-only
    baseline.  This is a static authorization decision, not a performance or
    physics-result arm-selection function.
    """
    reasons: list[str] = []
    if authorization is None:
        reasons.append("no_compact_authorization")
    else:
        if preflight_elapsed_s < 0 or preflight_elapsed_s > 20 * 60:
            reasons.append("authorization_outside_20_minute_preflight")
        if not authorization_is_write_once:
            reasons.append("authorization_not_proven_write_once")
        if authorization.get("batch_id") != BATCH_ID:
            reasons.append("authorization_batch_id_mismatch")
        if authorization.get("transport_authorized") is not True:
            reasons.append("transport_authorized_not_true")
        if authorization.get("scope") != "MATCHED_F_C_STAGE00_ALL_32_CELLS":
            reasons.append("authorization_scope_mismatch")
        if authorization.get("errors") != []:
            reasons.append("authorization_errors_not_empty")
        if required_contract_sha256 is not None and (
            authorization.get("campaign_contract_sha256") != required_contract_sha256
        ):
            reasons.append("authorization_contract_hash_mismatch")
    if reasons:
        return {
            "status": "PASS__F_ONLY_FALLBACK",
            "selected_launch_path": "F_ONLY",
            "selected_arm": "F_RICH_BASELINE",
            "compact_transport_authorized": False,
            "reasons": reasons,
        }
    return {
        "status": "PASS__MATCHED_F_C_AUTHORIZED",
        "selected_launch_path": "MATCHED_F_C",
        "selected_arm": None,
        "compact_transport_authorized": True,
        "reasons": [],
    }


def campaign_cap_at_t0(
    free_bytes_at_t0: int,
    *,
    requested_cap_bytes: int = REQUESTED_CAMPAIGN_CAP_BYTES,
    filesystem_reserve_bytes: int = FILESYSTEM_RESERVE_BYTES,
) -> int:
    """Compute ``min(90 GB, free(T0) - 20 GiB)`` without underflow."""
    if free_bytes_at_t0 < 0:
        raise CampaignValidationError("free bytes cannot be negative")
    return max(0, min(requested_cap_bytes, free_bytes_at_t0 - filesystem_reserve_bytes))


def disk_launch_gate(
    *,
    stage: str,
    campaign_bytes: int,
    active_declared_caps_bytes: int,
    candidate_declared_cap_bytes: int,
    campaign_cap_bytes: int,
    filesystem_free_bytes: int,
    smoke_bytes: int | None = None,
) -> dict[str, Any]:
    """Evaluate all campaign and live-filesystem launch inequalities.

    ``active_declared_caps_bytes`` excludes the candidate.  The projected value
    includes current published campaign bytes, all active attempts, and the new
    attempt cap.  No measured output is deleted or discounted by this gate.
    """
    values = {
        "campaign_bytes": campaign_bytes,
        "active_declared_caps_bytes": active_declared_caps_bytes,
        "candidate_declared_cap_bytes": candidate_declared_cap_bytes,
        "campaign_cap_bytes": campaign_cap_bytes,
        "filesystem_free_bytes": filesystem_free_bytes,
    }
    if any(value < 0 for value in values.values()):
        raise CampaignValidationError("disk gate values cannot be negative")
    normalized = stage.lower()
    if normalized in {"stage00", "smoke"}:
        reservation = PRE_PROTON_RESERVATION_BYTES
    elif normalized in {"stage10", "seven_family", "seven-family"}:
        reservation = PRE_PROTON_RESERVATION_BYTES
    elif normalized in {"stage20", "proton"}:
        reservation = CAMPAIGN_EMERGENCY_RESERVE_BYTES
    else:
        raise CampaignValidationError(f"unknown disk-gate stage: {stage}")
    active_including_candidate = active_declared_caps_bytes + candidate_declared_cap_bytes
    projected_campaign = campaign_bytes + active_including_candidate
    stage_limit = max(0, campaign_cap_bytes - reservation)
    required_filesystem_free = FILESYSTEM_RESERVE_BYTES + active_including_candidate
    reasons: list[str] = []
    if projected_campaign > stage_limit:
        reasons.append("campaign_stage_reservation_gate")
    if filesystem_free_bytes < required_filesystem_free:
        reasons.append("filesystem_20gib_plus_active_caps_gate")
    projected_smoke: int | None = None
    if normalized in {"stage00", "smoke"}:
        published_smoke = campaign_bytes if smoke_bytes is None else smoke_bytes
        if published_smoke < 0:
            raise CampaignValidationError("smoke bytes cannot be negative")
        projected_smoke = published_smoke + active_including_candidate
        if projected_smoke > SMOKE_HARD_CAP_BYTES:
            reasons.append("smoke_8gb_hard_cap")
    return {
        "status": "PASS" if not reasons else "FAIL_STOP_LAUNCH",
        "stage": normalized,
        "campaign_cap_bytes": campaign_cap_bytes,
        "stage_campaign_limit_bytes": stage_limit,
        "projected_campaign_bytes": projected_campaign,
        "active_including_candidate_bytes": active_including_candidate,
        "filesystem_free_bytes": filesystem_free_bytes,
        "required_filesystem_free_bytes": required_filesystem_free,
        "projected_smoke_bytes": projected_smoke,
        "reasons": reasons,
    }


def rss_launch_gate(
    *,
    stage: str,
    mem_available_bytes: int,
    active_p95_rss_upper_bytes: Sequence[int],
    candidate_p95_rss_upper_bytes: int,
    workers_after_launch: int,
    completed_same_arm_receipts: int,
) -> dict[str, Any]:
    """Evaluate the strict RSS headroom and concurrency-calibration gates."""
    if (
        mem_available_bytes < 0
        or candidate_p95_rss_upper_bytes < 0
        or workers_after_launch < 1
        or completed_same_arm_receipts < 0
        or any(value < 0 for value in active_p95_rss_upper_bytes)
    ):
        raise CampaignValidationError("invalid RSS gate value")
    normalized = stage.lower()
    is_proton = normalized in {"stage20", "proton"}
    max_workers = 2 if is_proton else 3
    rss_sum = sum(active_p95_rss_upper_bytes) + candidate_p95_rss_upper_bytes
    required = rss_sum + RSS_HEADROOM_BYTES
    reasons: list[str] = []
    # The README uses a strict '< MemAvailable' inequality.
    if required >= mem_available_bytes:
        reasons.append("p95_rss_sum_plus_2gib_not_below_memavailable")
    if workers_after_launch > max_workers:
        reasons.append("stage_worker_max_exceeded")
    if is_proton and workers_after_launch > 1 and completed_same_arm_receipts < 8:
        reasons.append("proton_second_worker_requires_8_receipts")
    if not is_proton and workers_after_launch > 2 and completed_same_arm_receipts < 8:
        reasons.append("third_worker_requires_8_receipts")
    return {
        "status": "PASS" if not reasons else "FAIL_STOP_LAUNCH",
        "stage": normalized,
        "workers_after_launch": workers_after_launch,
        "completed_same_arm_receipts": completed_same_arm_receipts,
        "rss_upper_sum_bytes": rss_sum,
        "rss_headroom_bytes": RSS_HEADROOM_BYTES,
        "required_mem_available_strictly_above_bytes": required,
        "mem_available_bytes": mem_available_bytes,
        "reasons": reasons,
    }


def validate_plan_files(allocation_csv: Path, smoke_csv: Path) -> dict[str, Any]:
    """Convenience read-only validation of both frozen batch0006 CSV plans."""
    return {
        "status": "PASS",
        "seven_family": validate_seven_family_rows(read_csv_rows(allocation_csv)),
        "smoke": validate_smoke_rows(read_csv_rows(smoke_csv)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allocation-csv", type=Path)
    parser.add_argument("--smoke-csv", type=Path)
    args = parser.parse_args()
    if (args.allocation_csv is None) != (args.smoke_csv is None):
        parser.error("--allocation-csv and --smoke-csv must be supplied together")
    if args.allocation_csv is None:
        parser.error("this helper CLI requires both plan CSV paths")
    print(json.dumps(validate_plan_files(args.allocation_csv, args.smoke_csv), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
