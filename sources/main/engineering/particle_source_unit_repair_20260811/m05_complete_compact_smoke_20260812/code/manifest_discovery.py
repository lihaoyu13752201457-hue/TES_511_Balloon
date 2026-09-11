#!/usr/bin/env python3
"""Resolve every donor/cassette input from pinned ledgers, never from directories."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from preflight_common import (
    ROOT,
    canonical_json_bytes,
    reject_lexical_symlinks,
    rel,
    repo_path,
    sha256,
    sha256_bytes,
    strict_json,
    verify_file,
)


AUTHORITY_REGISTRY: dict[str, dict[str, Any]] = {
    "batch0001": {
        "path": "runs/particle_source_unit_repair_20260811/seven_family_batch0001_v1_ledger.json",
        "sha256": "bb89c618d519a6a8570c8c746012c9ad0e81cb427b2a23145084a429c34c5df4",
        "status": "PASS__BATCH0001_MERGE_ELIGIBLE",
        "canonical_semantics_sha256": "b9c28f390d5ecafe29329921f167cddaa47673e94a64bec4c9a75b4a493b2579",
        "validation_path": "runs/particle_source_unit_repair_20260811/seven_family_batch0001_v1_validation.json",
        "validation_sha256": "386f5e1e51cb2be0eaa2b493a9a4f0c52dead1c86398aa419223d930392cf5a1",
        "validation_canonical_semantics_sha256": "f65a9e4da8f9af26627baaecae56c6f9a51cc5df3665a9f197b3b06e87a47788",
        "validation_status": "PASS",
        "kind": "merge_ledger_v1",
    },
    "batch0003_prefix76": {
        "path": (
            "runs/particle_source_unit_repair_20260811/"
            "gamma_instant_batch0003_prefix_checkpoints_20260811/"
            "gamma_instant_batch0003_prefix_shard0076_v1_ledger.json"
        ),
        "sha256": "3519c39d86e9bf38eddd01adae299c3428ef9810755d7e1d282420851df416fc",
        "status": "PARTIAL_PREFIX_MERGE_ELIGIBLE",
        "validation_status": "PASS__PARTIAL_PREFIX_VALIDATED",
        "canonical_semantics_sha256": "86c2a3bc72eca7d638bdc2b8887ecf8efbb6b9bcead74945af0632b3e8f3f3ed",
        "validation_path": (
            "runs/particle_source_unit_repair_20260811/"
            "gamma_instant_batch0003_prefix_checkpoints_20260811/"
            "gamma_instant_batch0003_prefix_shard0076_v1_validation.json"
        ),
        "validation_sha256": "5d2784c9fe1e968e04bddc0360538d8b1aea0fa9d1fad7e26ee681d995e69813",
        "validation_canonical_semantics_sha256": "78cd85b4ee40268d127d128780a6b153bb54cfca42679b75727b36620db3274b",
        "kind": "paired_prefix_ledger_v1",
    },
}

FROZEN_MEGALIB_ROOT = Path("/home/ubuntu/MEGAlib_Install/megalib-main")
_INCLUDE_TOKEN = re.compile(r"[^\s#]+")


@dataclass(frozen=True)
class JobRef:
    authority_id: str
    geometry: str
    mode: str
    family: str
    job: dict[str, Any]

    def bind_artifacts(self) -> dict[str, dict[str, Any]]:
        pairs = {
            "sim": "sim_sha256",
            "isotope_dat": "isotope_dat_sha256",
            "log": "log_sha256",
            "job_source": "job_source_sha256",
        }
        result: dict[str, dict[str, Any]] = {}
        for path_key, hash_key in pairs.items():
            if path_key not in self.job or hash_key not in self.job:
                raise ValueError(f"{self.authority_id}:{self.job.get('job_name')}: missing {path_key}/{hash_key}")
            path = verify_file(self.job[path_key], self.job[hash_key])
            result[path_key] = {
                "path": rel(path),
                "sha256": self.job[hash_key],
                "size_bytes": path.stat().st_size,
            }
        return result


def load_authority(authority_id: str) -> dict[str, Any]:
    if authority_id not in AUTHORITY_REGISTRY:
        raise KeyError(f"unregistered ledger authority {authority_id!r}")
    spec = AUTHORITY_REGISTRY[authority_id]
    path = verify_file(spec["path"], spec["sha256"])
    ledger = strict_json(path)
    if sha256_bytes(canonical_json_bytes(ledger)) != spec["canonical_semantics_sha256"]:
        raise ValueError(f"{authority_id}: canonical JSON semantics drift")
    if not isinstance(ledger, dict) or ledger.get("status") != spec["status"]:
        raise ValueError(f"{authority_id}: wrong ledger type/status")
    validation_path = verify_file(spec["validation_path"], spec["validation_sha256"])
    validation = strict_json(validation_path)
    if sha256_bytes(canonical_json_bytes(validation)) != spec["validation_canonical_semantics_sha256"]:
        raise ValueError(f"{authority_id}: validation canonical JSON semantics drift")
    if validation.get("status") != spec["validation_status"] or validation.get("errors") != []:
        raise ValueError(f"{authority_id}: validation status/errors are not closed")
    if ledger.get("validation_report") != spec["validation_path"]:
        raise ValueError(f"{authority_id}: ledger does not bind the pinned validation path")
    recorded_validation_sha = ledger.get("validation_report_sha256")
    if recorded_validation_sha is not None and recorded_validation_sha != spec["validation_sha256"]:
        raise ValueError(f"{authority_id}: ledger validation SHA drift")
    if spec["kind"] == "paired_prefix_ledger_v1":
        _validate_prefix76(ledger, validation)
    else:
        _validate_batch0001(ledger, validation)
    return ledger


def _actual_authority_path(value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        reject_lexical_symlinks(candidate, stop=Path(candidate.anchor))
        if not candidate.is_file():
            raise FileNotFoundError(candidate)
        return candidate
    return repo_path(value)


def verify_geometry_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    """Re-hash a geometry bundle and close its recursive ``Include`` graph.

    The ledger's file list is not sufficient by itself: Geomega follows
    ``Include`` directives at runtime.  Starting at the pinned setup file, the
    resolved include graph must therefore be exactly the pinned file set.  The
    only variable accepted in an include is the frozen installed
    ``$(MEGALIB)`` prefix; globs, unknown variables, cycles, links, unpinned
    includes, and unreferenced ledger files all fail closed.
    """

    files = bundle.get("files")
    if bundle.get("digest_contract") != "SHA256 of sorted path\\0sha256\\n records":
        raise ValueError("geometry bundle digest contract drift")
    if not isinstance(files, list) or len(files) != bundle.get("file_count") or not files:
        raise ValueError("geometry bundle file-count closure failed")
    paths = [row.get("path") for row in files]
    if any(not isinstance(value, str) or not value for value in paths) or len(set(paths)) != len(paths):
        raise ValueError("geometry bundle contains missing/duplicate paths")
    records: list[str] = []
    pinned_by_absolute: dict[Path, dict[str, Any]] = {}
    for row in files:
        if set(row) != {"path", "sha256"}:
            raise ValueError("geometry bundle file record has unexpected fields")
        path = _actual_authority_path(row["path"])
        absolute = path.resolve(strict=True)
        if absolute in pinned_by_absolute:
            raise ValueError("geometry bundle paths alias the same authority")
        if sha256(path) != row["sha256"]:
            raise ValueError(f"geometry bundle artifact hash drift: {row['path']}")
        pinned_by_absolute[absolute] = row
        records.append(f"{row['path']}\0{row['sha256']}\n")
    digest = hashlib.sha256("".join(sorted(records)).encode("utf-8")).hexdigest()
    if digest != bundle.get("bundle_sha256"):
        raise ValueError("geometry bundle digest does not reproduce")
    setup = bundle.get("setup")
    if setup not in paths or not str(setup).endswith(".geo.setup"):
        raise ValueError("geometry bundle setup is not one of the pinned files")
    setup_absolute = _actual_authority_path(setup).resolve(strict=True)

    visited: set[Path] = set()
    active: set[Path] = set()
    include_edges = 0

    def resolve_include(parent: Path, token: str) -> Path:
        if any(character in token for character in "*?["):
            raise ValueError(f"geometry Include glob is forbidden: {token}")
        if token.startswith("$(MEGALIB)/"):
            suffix = token[len("$(MEGALIB)/"):]
            if not suffix or "$" in suffix or "{" in suffix or "}" in suffix:
                raise ValueError(f"malformed frozen MEGALIB Include: {token}")
            candidate = FROZEN_MEGALIB_ROOT / suffix
        elif "$" in token or "{" in token or "}" in token:
            raise ValueError(f"unknown geometry Include variable: {token}")
        else:
            raw = Path(token)
            candidate = raw if raw.is_absolute() else parent.parent / raw
        reject_lexical_symlinks(candidate, stop=Path(candidate.anchor))
        try:
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError as exc:
            raise ValueError(f"geometry Include is missing: {token}") from exc
        if not resolved.is_file():
            raise ValueError(f"geometry Include is not a regular file: {token}")
        return resolved

    def visit(path: Path) -> None:
        nonlocal include_edges
        if path in active:
            raise ValueError(f"geometry Include cycle detected at {path}")
        if path in visited:
            return
        if path not in pinned_by_absolute:
            raise ValueError(f"geometry Include resolves outside the pinned bundle: {path}")
        active.add(path)
        text = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            statement = line.split("#", 1)[0].strip()
            if not statement:
                continue
            if statement == "Include" or statement.startswith("Include ") or statement.startswith("Include\t"):
                fields = statement.split()
                if len(fields) != 2 or fields[0] != "Include" or _INCLUDE_TOKEN.fullmatch(fields[1]) is None:
                    raise ValueError(f"malformed geometry Include at {path}:{line_number}")
                child = resolve_include(path, fields[1])
                if child not in pinned_by_absolute:
                    raise ValueError(f"geometry Include is not pinned: {path}:{line_number}: {fields[1]}")
                include_edges += 1
                visit(child)
        active.remove(path)
        visited.add(path)

    visit(setup_absolute)
    if visited != set(pinned_by_absolute):
        missing = sorted(str(path) for path in set(pinned_by_absolute) - visited)
        raise ValueError(f"geometry bundle contains files outside the setup Include closure: {missing}")
    return {
        "bundle_sha256": digest,
        "file_count": len(files),
        "setup": setup,
        "include_edge_count": include_edges,
        "include_closure_file_count": len(visited),
    }


def _validate_batch0001(ledger: dict[str, Any], validation: dict[str, Any]) -> None:
    campaigns = ledger.get("campaigns")
    if not isinstance(campaigns, list) or len(campaigns) != 4:
        raise ValueError("batch0001 must contain four geometry/mode campaigns")
    cells = {(c.get("geometry"), c.get("mode")) for c in campaigns}
    if cells != {
        ("mass_model_511", "instant"),
        ("mass_model_511", "buildup"),
        ("s3d_o8", "instant"),
        ("s3d_o8", "buildup"),
    }:
        raise ValueError("batch0001 campaign closure failed")
    for campaign in campaigns:
        jobs = campaign.get("jobs")
        if not isinstance(jobs, list) or len(jobs) != 10:
            raise ValueError("batch0001 campaign must contain exactly ten jobs")
        families = {job.get("family") for job in jobs}
        if families != {"gamma", "n", "eminus", "eplus", "alpha", "muminus", "muplus"}:
            raise ValueError("batch0001 seven-family set drift")
        if sum(int(job.get("events", -1)) for job in jobs) != 116_673:
            raise ValueError("batch0001 per-campaign event count drift")
    if sum(int(job["events"]) for campaign in campaigns for job in campaign["jobs"]) != 466_692:
        raise ValueError("batch0001 total event count drift")
    if ledger.get("errors") != [] or ledger.get("source_contract_manifest_sha256") != (
        "5424eeca35b20affb153c0e07c31a6582e575f511922bf55f40a5a0f77ab4326"
    ):
        raise ValueError("batch0001 errors/source contract drift")
    bundles = ledger.get("geometry_bundles", {})
    expected_bundles = {
        "mass_model_511": "6170bfaaefaea1f9a85b9ca6dc51117fb1c9e08ba10f52c9436cedc4b57a0b61",
        "s3d_o8": "8cdb6577489cd049c812dbce1f1ad46225332141c9754cdf5a2eda58f4a73492",
    }
    if {name: value.get("bundle_sha256") for name, value in bundles.items()} != expected_bundles:
        raise ValueError("batch0001 canonical geometry bundle drift")
    if set(bundles) != set(expected_bundles):
        raise ValueError("batch0001 geometry bundle key-set drift")
    for geometry, bundle in bundles.items():
        checked = verify_geometry_bundle(bundle)
        if checked["bundle_sha256"] != expected_bundles[geometry]:
            raise ValueError("batch0001 geometry bundle authority drift")

    if (
        validation.get("batch_id") != ledger.get("batch_id")
        or validation.get("campaign_version") != ledger.get("campaign_version")
        or validation.get("campaign_count") != 4
        or validation.get("validated_job_count") != 40
        or validation.get("validated_event_count") != 466_692
        or validation.get("source_contract_manifest_sha256") != ledger.get("source_contract_manifest_sha256")
        or validation.get("campaigns") != campaigns
    ):
        raise ValueError("batch0001 ledger/validation campaign-job closure failed")
    validation_bundles = {
        campaign.get("geometry"): campaign.get("geometry_bundle")
        for campaign in validation.get("campaigns", [])
    }
    if set(validation_bundles) != set(bundles):
        raise ValueError("batch0001 validation geometry set drift")
    for geometry, bundle in validation_bundles.items():
        if bundle != bundles[geometry]:
            raise ValueError("batch0001 ledger/validation geometry bundle mismatch")


def _validate_prefix76(ledger: dict[str, Any], validation: dict[str, Any]) -> None:
    spec = AUTHORITY_REGISTRY["batch0003_prefix76"]
    if ledger.get("validation_status") != spec["validation_status"]:
        raise ValueError("prefix76 validation status is not PASS")
    if (
        ledger.get("prefix_start_ordinal") != 1
        or ledger.get("prefix_end_ordinal") != 76
        or ledger.get("validated_pair_count") != 76
    ):
        raise ValueError("prefix76 boundary/count closure failed")
    pair_receipts = ledger.get("pair_receipts")
    if not isinstance(pair_receipts, list) or len(pair_receipts) != 76:
        raise ValueError("prefix76 must bind exactly 76 pair receipts")
    if [row.get("ordinal") for row in pair_receipts] != list(range(1, 77)):
        raise ValueError("prefix76 receipt ordinals are not exactly 1..76")
    campaign_jobs: dict[tuple[str, int], dict[str, Any]] = {}
    for campaign in ledger.get("campaigns", []):
        for job in campaign.get("jobs", []):
            key = (campaign.get("geometry"), int(job.get("ordinal", -1)))
            if key in campaign_jobs:
                raise ValueError("prefix76 duplicate geometry/ordinal job identity")
            campaign_jobs[key] = job
    for expected_ordinal, receipt in enumerate(pair_receipts, start=1):
        receipt_path = verify_file(receipt.get("path", ""), receipt.get("sha256", ""))
        parsed = strict_json(receipt_path)
        if (
            parsed.get("status") != "PASS__PAIRED_SHARD_MERGE_ELIGIBLE"
            or parsed.get("ordinal") != expected_ordinal
            or parsed.get("paired_seed") != receipt.get("paired_seed")
            or parsed.get("events_per_geometry") != receipt.get("events_per_geometry")
        ):
            raise ValueError("prefix76 pair receipt status drift")
        geometry_receipts = parsed.get("geometry_receipts")
        if not isinstance(geometry_receipts, dict) or set(geometry_receipts) != {"mass_model_511", "s3d_o8"}:
            raise ValueError("prefix76 pair receipt geometry set drift")
        for geometry, geometry_ref in geometry_receipts.items():
            job = campaign_jobs.get((geometry, expected_ordinal))
            if job is None:
                raise ValueError("prefix76 pair receipt has no ledger job")
            if (
                job.get("pair_receipt") != receipt.get("path")
                or job.get("pair_receipt_sha256") != receipt.get("sha256")
                or job.get("geometry_receipt") != geometry_ref.get("path")
                or job.get("geometry_receipt_sha256") != geometry_ref.get("sha256")
                or job.get("seed") != parsed.get("paired_seed")
                or job.get("events") != parsed.get("events_per_geometry")
                or job.get("selected_attempt") != geometry_ref.get("selected_attempt")
            ):
                raise ValueError("prefix76 pair/geometry/job binding drift")
            geometry_path = verify_file(geometry_ref.get("path", ""), geometry_ref.get("sha256", ""))
            geometry_receipt = strict_json(geometry_path)
            if (
                geometry_receipt.get("status") != "PASS__GEOMETRY_SHARD_MERGE_ELIGIBLE"
                or geometry_receipt.get("geometry") != geometry
                or geometry_receipt.get("mode") != "instant"
                or geometry_receipt.get("family") != "gamma"
                or geometry_receipt.get("ordinal") != expected_ordinal
                or geometry_receipt.get("seed") != parsed.get("paired_seed")
                or geometry_receipt.get("events") != parsed.get("events_per_geometry")
                or geometry_receipt.get("selected_attempt") != geometry_ref.get("selected_attempt")
            ):
                raise ValueError("prefix76 geometry receipt content drift")
    campaigns = ledger.get("campaigns")
    if not isinstance(campaigns, list) or len(campaigns) != 2:
        raise ValueError("prefix76 must contain exactly two geometry campaigns")
    if {c.get("geometry") for c in campaigns} != {"mass_model_511", "s3d_o8"}:
        raise ValueError("prefix76 geometry closure failed")
    for campaign in campaigns:
        if campaign.get("family") != "gamma" or campaign.get("mode") != "instant":
            raise ValueError("prefix76 campaign family/mode drift")
        jobs = campaign.get("jobs")
        if not isinstance(jobs, list) or len(jobs) != 76:
            raise ValueError("prefix76 campaign must contain 76 jobs")
        if [job.get("ordinal") for job in jobs] != list(range(1, 77)):
            raise ValueError("prefix76 is not the exact continuous ordinal 1..76 prefix")
        if {job.get("family") for job in jobs} != {"gamma"}:
            raise ValueError("prefix76 family/mode drift")
    if ledger.get("errors") != [] or ledger.get("source_contract_manifest_sha256") != (
        "5424eeca35b20affb153c0e07c31a6582e575f511922bf55f40a5a0f77ab4326"
    ):
        raise ValueError("prefix76 errors/source contract drift")
    expected_bundles = {
        "mass_model_511": "6170bfaaefaea1f9a85b9ca6dc51117fb1c9e08ba10f52c9436cedc4b57a0b61",
        "s3d_o8": "8cdb6577489cd049c812dbce1f1ad46225332141c9754cdf5a2eda58f4a73492",
    }
    validation_bundles = validation.get("geometry_bundles")
    if not isinstance(validation_bundles, dict) or {
        name: value.get("bundle_sha256") for name, value in validation_bundles.items()
    } != expected_bundles:
        raise ValueError("prefix76 validation geometry bundle drift")
    for geometry, bundle in validation_bundles.items():
        if verify_geometry_bundle(bundle)["bundle_sha256"] != expected_bundles[geometry]:
            raise ValueError("prefix76 validation geometry authority drift")
    if (
        validation.get("batch_id") != ledger.get("batch_id")
        or validation.get("campaign_version") != ledger.get("campaign_version")
        or validation.get("validated_pair_count") != 76
        or validation.get("validated_geometry_job_count") != 152
        or validation.get("source_contract_manifest_sha256") != ledger.get("source_contract_manifest_sha256")
        or validation.get("pair_receipts") != pair_receipts
        or validation.get("campaigns") != campaigns
    ):
        raise ValueError("prefix76 ledger/validation campaign-job closure failed")


def iter_jobs(authority_id: str) -> Iterator[JobRef]:
    ledger = load_authority(authority_id)
    for campaign in ledger["campaigns"]:
        geometry = campaign["geometry"]
        mode = campaign["mode"]
        for job in campaign["jobs"]:
            family = job["family"]
            yield JobRef(authority_id, geometry, mode, family, job)


def resolve_job(
    authority_id: str,
    *,
    geometry: str,
    mode: str,
    family: str,
    job_name: str | None = None,
    ordinal: int | None = None,
) -> JobRef:
    if (job_name is None) == (ordinal is None):
        raise ValueError("selector must provide exactly one of job_name or ordinal")
    matches = []
    for ref in iter_jobs(authority_id):
        if (ref.geometry, ref.mode, ref.family) != (geometry, mode, family):
            continue
        if job_name is not None and ref.job.get("job_name") == job_name:
            matches.append(ref)
        if ordinal is not None and ref.job.get("ordinal") == ordinal:
            matches.append(ref)
    if len(matches) != 1:
        raise ValueError(f"selector resolved {len(matches)} jobs, expected exactly one")
    return matches[0]


DONOR_SELECTORS: dict[tuple[str, str], dict[str, Any]] = {
    ("gamma", "instant"): {
        "authority_id": "batch0003_prefix76",
        "geometry": "mass_model_511",
        "ordinal": 1,
    },
    ("n", "buildup"): {
        "authority_id": "batch0001",
        "geometry": "mass_model_511",
        "job_name": "Background_n_fullsphere20_rep01_part01",
    },
    ("eplus", "instant"): {
        "authority_id": "batch0001",
        "geometry": "mass_model_511",
        "job_name": "Background_eplus_fullsphere20_rep01_part01",
    },
    ("eplus", "buildup"): {
        "authority_id": "batch0001",
        "geometry": "mass_model_511",
        "job_name": "Background_eplus_fullsphere20_rep01_part01",
    },
    ("alpha", "instant"): {
        "authority_id": "batch0001",
        "geometry": "mass_model_511",
        "job_name": "Background_alpha_fullsphere20_rep01_part01",
    },
    ("alpha", "buildup"): {
        "authority_id": "batch0001",
        "geometry": "mass_model_511",
        "job_name": "Background_alpha_fullsphere20_rep01_part01",
    },
}


def resolve_donor(family: str, mode: str) -> JobRef:
    selector = dict(DONOR_SELECTORS[(family, mode)])
    authority_id = selector.pop("authority_id")
    geometry = selector.pop("geometry")
    return resolve_job(
        authority_id,
        geometry=geometry,
        mode=mode,
        family=family,
        **selector,
    )


def registered_authorities() -> list[dict[str, Any]]:
    output = []
    for authority_id in sorted(AUTHORITY_REGISTRY):
        spec = AUTHORITY_REGISTRY[authority_id]
        path = ROOT / spec["path"]
        load_authority(authority_id)
        output.append(
            {
                "authority_id": authority_id,
                "kind": spec["kind"],
                "path": spec["path"],
                "sha256": spec["sha256"],
                "size_bytes": path.stat().st_size,
                "status": spec["status"],
                "canonical_semantics_sha256": spec["canonical_semantics_sha256"],
                "validation_path": spec["validation_path"],
                "validation_sha256": spec["validation_sha256"],
                "validation_status": spec["validation_status"],
                "validation_canonical_semantics_sha256": spec["validation_canonical_semantics_sha256"],
            }
        )
    return output
