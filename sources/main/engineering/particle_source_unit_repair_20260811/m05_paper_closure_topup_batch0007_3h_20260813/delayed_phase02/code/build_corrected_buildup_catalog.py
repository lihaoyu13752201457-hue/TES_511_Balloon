#!/usr/bin/env python3
"""Build the corrected-keV BUILDUP authority catalog for delayed phase02.

The adapter reads only canonical PASS ledgers/final receipt selections.  It
does not open SIM payloads and never launches transport.  The DAT inventory
retains every positive TT, including DATs with no RP records, so production
rates can be formed as ``sum(RP) / sum(TT)`` inside one geometry/family cell.

``--check`` is strictly read-only.  ``--publish`` is allowed only after the
batch0007 final PASS bundle exists and publishes an atomic, write-once catalog
directory plus a relative compatibility symlink.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
import os
import shutil
import sys
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


def find_root(path: Path) -> Path:
    for candidate in (path, *path.parents):
        if (candidate / "AGENTS.md").is_file() and (candidate / ".git").exists():
            return candidate
    raise RuntimeError("repository root not found")


THIS_FILE = Path(__file__).resolve()
ROOT = find_root(THIS_FILE.parent)
RUN_BASE = ROOT / "runs/particle_source_unit_repair_20260811"
BATCH0006_ROOT = RUN_BASE / "m05_16h_90gb_campaign_batch0006_v1"
BATCH0007_ROOT = RUN_BASE / "m05_paper_closure_topup_batch0007_3h_v1"
PUBLISH_ROOT = BATCH0007_ROOT / "delayed_phase02"
CATALOG_DIR = PUBLISH_ROOT / "catalog_v1"
COMPAT_LINK = PUBLISH_ROOT / "corrected_buildup_catalog.json"
SOURCE_CONTRACT_SHA256 = "5424eeca35b20affb153c0e07c31a6582e575f511922bf55f40a5a0f77ab4326"
FORBIDDEN_SOURCE_TOKEN = "cosima_spectra_dp_2602units"

PARTIAL_POSTPROCESSOR = (
    ROOT / "engineering/particle_source_unit_repair_20260811"
    / "composite_partial_postprocess_20260812/code/analyze_composite_partial.py"
)

OLD_LEDGER_ROLES = (
    "batch0000_ledger",
    "batch0001_ledger",
    "batch0004_ledger",
    "batch0005_ledger",
)

GEOMETRY_ALIASES = {
    "mass_model_511": "Mass_model_511",
    "Mass_model_511": "Mass_model_511",
    "s3d_o8": "S3d_O8",
    "S3d_O8": "S3d_O8",
}
FAMILY_ALIASES = {
    "gamma": "gamma",
    "n": "n",
    "neutron": "n",
    "eplus": "eplus",
    "alpha": "alpha",
    "eminus": "eminus",
    "muplus": "muplus",
    "muminus": "muminus",
    "p": "p",
    "proton": "p",
}
GEOMETRIES = ("Mass_model_511", "S3d_O8")
FAMILIES = ("gamma", "n", "eplus", "alpha", "eminus", "muplus", "muminus", "p")

BATCH0006_BUNDLES = (
    (
        "batch0006_recovery0008",
        BATCH0006_ROOT / "recovery0008_current_attempt_disk_admission",
        "PASS__REPLANNED_MAINLINE_EVENT_TARGET_COMPLETE",
        "path",
    ),
    (
        "batch0006_continuation0001_recovery0005",
        BATCH0006_ROOT / "continuation0001_recovery0005_finish_proton_wave",
        "PASS__CONTINUATION0001_NON_GAMMA_DEWEIGHT_COMPLETE__GAMMA_LOCKED",
        "receipt",
    ),
)

BATCH0007_BUNDLE = (
    "batch0007_final",
    BATCH0007_ROOT,
    "PASS__BATCH0007_SUPPLEMENTAL_TRANSPORT_COMPLETE",
    "path",
)


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


partial = load_module(PARTIAL_POSTPROCESSOR, "batch0007_delayed_partial_authority_core")
dat_core = partial.core


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
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def canonical_sha(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    def reject(token: str) -> None:
        raise ValueError(f"non-finite JSON token {token!r}")

    value = json.loads(path.read_text(encoding="utf-8"), parse_constant=reject)
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {rel(path)}")
    return value


def normalize_geometry(value: Any) -> str:
    try:
        return GEOMETRY_ALIASES[str(value)]
    except KeyError as exc:
        raise RuntimeError(f"unknown geometry {value!r}") from exc


def normalize_family(value: Any) -> str:
    try:
        return FAMILY_ALIASES[str(value)]
    except KeyError as exc:
        raise RuntimeError(f"unknown family {value!r}") from exc


def isotope_za(isotope_id: int) -> tuple[int, int]:
    z, a = divmod(isotope_id, 1000)
    if z <= 0 or a <= 0:
        raise RuntimeError(f"invalid isotope id {isotope_id}")
    return z, a


def parse_dat(path: Path) -> dict[str, Any]:
    parsed = dat_core.parse_isotope_dat(path)
    records = []
    total = 0.0
    for row in parsed["RP_records"]:
        isotope_id = int(row["isotope_id"])
        z, a = isotope_za(isotope_id)
        rp = float(row["RP"])
        total = math.fsum((total, rp))
        records.append({
            "volume": str(row["volume"]),
            "isotope_id": isotope_id,
            "Z": z,
            "A": a,
            "excitation_keV": float(row["excitation_keV"]),
            "RP": rp,
        })
    records.sort(key=lambda row: (
        row["volume"], row["isotope_id"], row["excitation_keV"], row["RP"]
    ))
    return {
        "TT_s": float(parsed["TT_s"]),
        "RP_record_count": len(records),
        "sum_RP": total,
        "records": records,
    }


def require_dat_binding(
    path: Path,
    declared_sha: str,
    declared_tt: Any,
    declared_rp_count: Any,
    declared_rp_sum: Any | None,
) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink() or path.stat().st_size <= 0:
        raise RuntimeError(f"missing/empty/symlink DAT: {rel(path)}")
    if sha256(path) != declared_sha:
        raise RuntimeError(f"DAT hash differs from canonical declaration: {rel(path)}")
    parsed = parse_dat(path)
    if not math.isclose(parsed["TT_s"], float(declared_tt), rel_tol=0.0, abs_tol=1e-12):
        raise RuntimeError(f"DAT TT differs from canonical declaration: {rel(path)}")
    if int(parsed["RP_record_count"]) != int(declared_rp_count):
        raise RuntimeError(f"DAT RP count differs from canonical declaration: {rel(path)}")
    if declared_rp_sum is not None and not math.isclose(
        parsed["sum_RP"], float(declared_rp_sum), rel_tol=0.0, abs_tol=1e-12
    ):
        raise RuntimeError(f"DAT RP sum differs from canonical declaration: {rel(path)}")
    return parsed


def require_corrected_source(path: Path, declared_sha: str) -> None:
    if not path.is_file() or path.is_symlink() or sha256(path) != declared_sha:
        raise RuntimeError(f"source missing or hash drift: {rel(path)}")
    text = path.read_text(encoding="utf-8", errors="strict")
    if FORBIDDEN_SOURCE_TOKEN in text:
        raise RuntimeError(f"legacy factor-1000 source reference: {rel(path)}")


def authority_record(role: str, path: Path, status: str) -> dict[str, Any]:
    return {"role": role, "path": rel(path), "sha256": sha256(path), "status": status}


def old_entry(
    role: str,
    ledger_path: Path,
    ledger_sha: str,
    ledger: dict[str, Any],
    campaign: dict[str, Any],
    row: dict[str, Any],
) -> dict[str, Any]:
    geometry = normalize_geometry(campaign.get("geometry"))
    family = normalize_family(row.get("family", campaign.get("family")))
    dat_path = resolve(str(row["isotope_dat"])).resolve()
    store = row.get("isotope_store", {})
    parsed = require_dat_binding(
        dat_path,
        str(row["isotope_dat_sha256"]),
        row.get("TT_s_from_isotope_dat"),
        store.get("RP_record_count"),
        sum(float(item["RP"]) for item in store.get("RP_records", [])),
    )
    if not math.isclose(
        parsed["TT_s"], float(row.get("TT_s_from_log")), rel_tol=0.0, abs_tol=1e-12
    ):
        raise RuntimeError(f"ledger DAT/log TT mismatch: {rel(dat_path)}")
    source_path = resolve(str(row["job_source"])).resolve()
    require_corrected_source(source_path, str(row["job_source_sha256"]))
    expected_header = Path(
        dat_core.GEOMETRY_CONTRACTS[
            "mass_model_511" if geometry == "Mass_model_511" else "s3d_o8"
        ]["geometry_setup"]
    ).resolve()
    actual_header = resolve(str(row.get("ia_init", {}).get("geometry_header", "__missing__"))).resolve()
    if actual_header != expected_header:
        raise RuntimeError(f"geometry header mismatch for {row.get('job_name')}")
    sim_path = resolve(str(row["sim"])).resolve()
    if not sim_path.is_file() or sim_path.stat().st_size <= 0:
        raise RuntimeError(f"missing declared SIM reference: {rel(sim_path)}")
    return {
        "geometry": geometry,
        "family": family,
        "mode": "buildup",
        "batch_id": str(ledger["batch_id"]),
        "job_id": str(row["job_name"]),
        "events": int(row["events"]),
        "seed": int(row["seed"]),
        "authority_role": role,
        "authority_path": rel(ledger_path),
        "authority_sha256": ledger_sha,
        "receipt_path": None,
        "receipt_sha256": None,
        "dat_path": rel(dat_path),
        "dat_sha256": str(row["isotope_dat_sha256"]),
        "TT_s": parsed["TT_s"],
        "RP_record_count": parsed["RP_record_count"],
        "sum_RP": parsed["sum_RP"],
        "zero_RP": parsed["sum_RP"] == 0.0,
        "records": parsed["records"],
        "sim_reference": {
            "path": rel(sim_path),
            "declared_sha256": str(row["sim_sha256"]),
            "payload_opened_by_catalog_builder": False,
            "cc_ip_rp_position_support": "UNVERIFIED_OLD_SIM_REFERENCE",
        },
    }


def collect_old() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    snapshot = partial.build_authority_snapshot()
    if snapshot.get("status") != "PASS__COMPOSITE_PARTIAL_AUTHORITIES_PINNED":
        raise RuntimeError("composite partial authority selector did not PASS")
    entries: list[dict[str, Any]] = []
    authorities: list[dict[str, Any]] = []
    for role in OLD_LEDGER_ROLES:
        path = partial.PATHS[role].resolve()
        expected_hash = partial.EXPECTED_HASHES[role]
        expected_status = partial.EXPECTED_STATUS[role]
        ledger = partial._validate_authority(role)
        if sha256(path) != expected_hash:
            raise RuntimeError(f"postprocessor authority hash drift: {role}")
        authorities.append(authority_record(role, path, expected_status))
        for campaign in ledger.get("campaigns", []):
            if str(campaign.get("mode")) != "buildup":
                continue
            for row in campaign.get("jobs", []):
                entries.append(old_entry(role, path, expected_hash, ledger, campaign, row))
    return entries, authorities, snapshot


def validate_bundle(
    role: str,
    directory: Path,
    expected_status: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    validation_path = directory / "final_validation.json"
    ledger_path = directory / "final_ledger.json"
    umbrella_path = directory / "final_umbrella.json"
    for path in (validation_path, ledger_path, umbrella_path):
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"missing canonical final bundle file: {rel(path)}")
    validation = load_json(validation_path)
    ledger = load_json(ledger_path)
    umbrella = load_json(umbrella_path)
    if not (
        validation.get("status") == ledger.get("status") == umbrella.get("status") == expected_status
        and validation.get("selected_receipts") == ledger.get("selected_receipts")
        and validation.get("errors") in (None, [])
        and ledger.get("errors") in (None, [])
        and validation.get("missing_jobs") in (None, [])
        and ledger.get("missing_jobs") in (None, [])
        and resolve(str(umbrella.get("final_validation", "__missing__"))).resolve() == validation_path.resolve()
        and resolve(str(umbrella.get("final_ledger", "__missing__"))).resolve() == ledger_path.resolve()
    ):
        raise RuntimeError(f"canonical final bundle mismatch: {role}")
    records = [
        authority_record(f"{role}:final_validation", validation_path, expected_status),
        authority_record(f"{role}:final_ledger", ledger_path, expected_status),
        authority_record(f"{role}:final_umbrella", umbrella_path, expected_status),
    ]
    return validation, records


def receipt_entry(
    role: str,
    final_sha: str,
    selected: dict[str, Any],
    receipt_path: Path,
    *,
    rich_sim: bool,
) -> dict[str, Any] | None:
    if not receipt_path.is_file() or receipt_path.is_symlink():
        raise RuntimeError(f"missing selected receipt: {rel(receipt_path)}")
    receipt = load_json(receipt_path)
    job = receipt.get("job", {})
    if receipt.get("status") != "PASS" or receipt.get("errors") != []:
        raise RuntimeError(f"selected receipt is not PASS: {rel(receipt_path)}")
    if str(job.get("job_id")) != str(selected.get("job_id")):
        raise RuntimeError(f"selected receipt job binding mismatch: {rel(receipt_path)}")
    expected_global_sha = sha256(BATCH0006_ROOT / "global_contract.json")
    if receipt.get("global_contract_sha256") != expected_global_sha:
        raise RuntimeError(f"selected receipt global-contract mismatch: {rel(receipt_path)}")
    if str(job.get("mode")) != "buildup":
        return None
    geometry = normalize_geometry(job.get("geometry"))
    family = normalize_family(job.get("family"))
    attempt = resolve(str(receipt["attempt_dir"])).resolve()
    artifacts = receipt.get("artifacts", {})
    dat_decl = artifacts.get("dat", {})
    source_decl = artifacts.get("source", {})
    sim_decl = artifacts.get("sim", {})
    dat_path = attempt / str(dat_decl.get("name", "__missing__"))
    source_path = attempt / str(source_decl.get("name", "__missing__"))
    sim_path = attempt / str(sim_decl.get("name", "__missing__"))
    isotope = receipt.get("isotope_dat", {})
    parsed = require_dat_binding(
        dat_path,
        str(dat_decl.get("sha256")),
        isotope.get("TT_s"),
        isotope.get("RP_record_count"),
        isotope.get("RP_sum"),
    )
    require_corrected_source(source_path, str(source_decl.get("sha256")))
    if int(receipt.get("source", {}).get("legacy_references", -1)) != 0:
        raise RuntimeError(f"receipt declares legacy source references: {rel(receipt_path)}")
    if not sim_path.is_file() or sim_path.stat().st_size <= 0:
        raise RuntimeError(f"missing selected SIM reference: {rel(sim_path)}")
    sim_geometry = resolve(str(receipt.get("sim", {}).get("geometry_header", "__missing__"))).resolve()
    expected_geometry = Path(
        dat_core.GEOMETRY_CONTRACTS[
            "mass_model_511" if geometry == "Mass_model_511" else "s3d_o8"
        ]["geometry_setup"]
    ).resolve()
    if sim_geometry != expected_geometry:
        raise RuntimeError(f"selected receipt geometry mismatch: {rel(receipt_path)}")
    return {
        "geometry": geometry,
        "family": family,
        "mode": "buildup",
        "batch_id": role,
        "job_id": str(job["job_id"]),
        "events": int(job["events"]),
        "seed": int(job["seed"]),
        "authority_role": role,
        "authority_path": str(selected.get("_final_path")),
        "authority_sha256": final_sha,
        "receipt_path": rel(receipt_path),
        "receipt_sha256": sha256(receipt_path),
        "dat_path": rel(dat_path),
        "dat_sha256": str(dat_decl["sha256"]),
        "TT_s": parsed["TT_s"],
        "RP_record_count": parsed["RP_record_count"],
        "sum_RP": parsed["sum_RP"],
        "zero_RP": parsed["sum_RP"] == 0.0,
        "records": parsed["records"],
        "sim_reference": {
            "path": rel(sim_path),
            "declared_sha256": str(sim_decl["sha256"]),
            "payload_opened_by_catalog_builder": False,
            "cc_ip_rp_position_support": (
                "DECLARED_RICH_SIM_REFERENCE__REQUIRES_SEPARATE_CC_IP_RP_PARSE"
                if rich_sim else "UNVERIFIED_OLD_SIM_REFERENCE"
            ),
        },
    }


def collect_receipt_bundle(
    role: str,
    directory: Path,
    expected_status: str,
    selected_path_key: str,
    *,
    rich_sim: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    final, authorities = validate_bundle(role, directory, expected_status)
    final_path = directory / "final_validation.json"
    final_sha = sha256(final_path)
    entries: list[dict[str, Any]] = []
    for original in final.get("selected_receipts", []):
        selected = dict(original)
        selected["_final_path"] = rel(final_path)
        receipt_path = resolve(str(selected.get(selected_path_key, "__missing__"))).resolve()
        entry = receipt_entry(role, final_sha, selected, receipt_path, rich_sim=rich_sim)
        if entry is not None:
            entries.append(entry)
    return entries, authorities


def validate_global_contract() -> dict[str, Any]:
    path = BATCH0006_ROOT / "global_contract.json"
    contract = load_json(path)
    source = contract.get("source_contract", {})
    if not (
        source.get("sha256") == SOURCE_CONTRACT_SHA256
        and source.get("forbidden_reference_substring") == FORBIDDEN_SOURCE_TOKEN
        and source.get("standalone_mono511_forbidden") is True
        and contract.get("compact_transport_authorized") is False
    ):
        raise RuntimeError("batch0006 global corrected-source contract mismatch")
    return authority_record("batch0006_global_contract", path, str(contract.get("status")))


def validate_batch0007_contract() -> dict[str, Any]:
    path = BATCH0007_ROOT / "authority.json"
    authority = load_json(path)
    frozen = authority.get("frozen", {})
    if not (
        authority.get("source_contract_sha256") == SOURCE_CONTRACT_SHA256
        and frozen.get("corrected_keV_sources") is True
        and frozen.get("legacy_2602units_forbidden") is True
        and frozen.get("extra_mono511_added") is False
    ):
        raise RuntimeError("batch0007 corrected-source contract mismatch")
    return authority_record("batch0007_plan_authority", path, str(authority.get("status")))


def dedupe(entries: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    by_identity: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    by_dat: dict[str, tuple[str, str, str, str]] = {}
    for entry in entries:
        identity = (
            str(entry["geometry"]), str(entry["family"]),
            str(entry["batch_id"]), str(entry["job_id"]),
        )
        existing = by_identity.get(identity)
        if existing is not None:
            if canonical_bytes(existing) != canonical_bytes(entry):
                raise RuntimeError(f"conflicting duplicate geometry/family job identity: {identity}")
            continue
        dat_path = str(entry["dat_path"])
        if dat_path in by_dat:
            raise RuntimeError(f"one DAT selected by two identities: {dat_path}")
        by_dat[dat_path] = identity
        by_identity[identity] = entry
    return sorted(by_identity.values(), key=lambda row: (
        row["geometry"], row["family"], row["batch_id"], row["job_id"], row["dat_path"]
    ))


def aggregate(entries: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    production: dict[tuple[str, str, str, int, float], float] = defaultdict(float)
    positive_dat: dict[tuple[str, str, str, int, float], set[str]] = defaultdict(set)
    for entry in entries:
        cell = (str(entry["geometry"]), str(entry["family"]))
        grouped[cell].append(entry)
        for record in entry["records"]:
            key = (
                cell[0], cell[1], str(record["volume"]),
                int(record["isotope_id"]), float(record["excitation_keV"]),
            )
            production[key] = math.fsum((production[key], float(record["RP"])))
            if float(record["RP"]) > 0.0:
                positive_dat[key].add(str(entry["dat_path"]))
    cells: list[dict[str, Any]] = []
    for geometry in GEOMETRIES:
        for family in FAMILIES:
            rows = grouped.get((geometry, family), [])
            if not rows:
                raise RuntimeError(f"missing corrected BUILDUP cell: {geometry}/{family}")
            sum_tt = math.fsum(float(row["TT_s"]) for row in rows)
            sum_rp = math.fsum(float(row["sum_RP"]) for row in rows)
            if not sum_tt > 0.0:
                raise RuntimeError(f"nonpositive BUILDUP TT: {geometry}/{family}")
            cells.append({
                "geometry": geometry,
                "family": family,
                "mode": "buildup",
                "N_DAT": len(rows),
                "sum_TT_s": sum_tt,
                "sum_RP": sum_rp,
                "RP_record_count": sum(int(row["RP_record_count"]) for row in rows),
                "zero_RP_DAT": sum(bool(row["zero_RP"]) for row in rows),
                "production_rate_s-1": sum_rp / sum_tt,
            })
    cell_by_key = {(row["geometry"], row["family"]): row for row in cells}
    production_rows: list[dict[str, Any]] = []
    for key in sorted(production):
        geometry, family, volume, isotope_id, excitation = key
        cell = cell_by_key[(geometry, family)]
        z, a = isotope_za(isotope_id)
        sum_rp = production[key]
        production_rows.append({
            "geometry": geometry,
            "family": family,
            "volume": volume,
            "isotope_id": isotope_id,
            "Z": z,
            "A": a,
            "excitation_keV": excitation,
            "sum_RP": sum_rp,
            "sum_TT_s_including_zero_RP_DAT": cell["sum_TT_s"],
            "production_rate_s-1": sum_rp / float(cell["sum_TT_s"]),
            "N_DAT_denominator": cell["N_DAT"],
            "N_DAT_with_positive_RP_for_state": len(positive_dat[key]),
            "N_DAT_with_zero_RP_for_state": cell["N_DAT"] - len(positive_dat[key]),
        })
    return cells, production_rows


def csv_bytes(rows: list[dict[str, Any]], fieldnames: list[str]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def build_catalog(*, require_batch0007: bool) -> tuple[dict[str, Any], bytes, bytes, str]:
    entries, authorities, old_snapshot = collect_old()
    authorities.append(validate_global_contract())
    for role, directory, status, key in BATCH0006_BUNDLES:
        new_entries, records = collect_receipt_bundle(
            role, directory, status, key, rich_sim=True
        )
        entries.extend(new_entries)
        authorities.extend(records)
    batch0007_state = "PENDING__FINAL_NOT_PUBLISHED"
    final7 = BATCH0007_ROOT / "final_validation.json"
    if final7.is_file():
        try:
            authorities.append(validate_batch0007_contract())
            role, directory, status, key = BATCH0007_BUNDLE
            new_entries, records = collect_receipt_bundle(
                role, directory, status, key, rich_sim=True
            )
            entries.extend(new_entries)
            authorities.extend(records)
            batch0007_state = "INCLUDED__FINAL_PASS"
        except RuntimeError:
            if require_batch0007:
                raise
            batch0007_state = "NOT_INCLUDED__FINAL_PRESENT_BUT_NOT_PASS"
    elif require_batch0007:
        raise RuntimeError("batch0007 final PASS bundle is not published; catalog publication is gated")
    entries = dedupe(entries)
    cells, production_rows = aggregate(entries)
    cell_fields = [
        "geometry", "family", "mode", "N_DAT", "sum_TT_s", "sum_RP",
        "RP_record_count", "zero_RP_DAT", "production_rate_s-1",
    ]
    production_fields = [
        "geometry", "family", "volume", "isotope_id", "Z", "A",
        "excitation_keV", "sum_RP", "sum_TT_s_including_zero_RP_DAT",
        "production_rate_s-1", "N_DAT_denominator",
        "N_DAT_with_positive_RP_for_state", "N_DAT_with_zero_RP_for_state",
    ]
    cell_csv = csv_bytes(cells, cell_fields)
    production_csv = csv_bytes(production_rows, production_fields)
    authorities.sort(key=lambda row: row["role"])
    catalog = {
        "schema_version": 1,
        "status": (
            "PASS__CORRECTED_BUILDUP_CATALOG_READY"
            if batch0007_state == "INCLUDED__FINAL_PASS"
            else "WAIT__BATCH0007_FINAL_PASS"
        ),
        "authority_class": "CORRECTED_KEV_BUILDUP_DAT_AND_RICH_SIM_REFERENCE_CATALOG",
        "source_contract_sha256": SOURCE_CONTRACT_SHA256,
        "legacy_factor1000_included": False,
        "extra_mono511_included": False,
        "mode": "buildup_only",
        "batch0007_state": batch0007_state,
        "old_authority_selector": {
            "path": rel(PARTIAL_POSTPROCESSOR),
            "sha256": sha256(PARTIAL_POSTPROCESSOR),
            "snapshot_sha256": canonical_sha(old_snapshot),
            "selected_roles": list(OLD_LEDGER_ROLES),
        },
        "authorities": authorities,
        "normalization": {
            "cell": "geometry x family x buildup",
            "production_rate": "sum(RP) / sum(TT)",
            "zero_RP_DAT_TT_retained": True,
            "pool_across_geometry_or_family": False,
            "activity_claimed": False,
            "note": "production_rate_s-1 is an isotope-production rate; activation/decay is required before activity",
        },
        "spatial_contract": {
            "DAT_role": "logical-volume/isotope-state production aggregate",
            "exact_position_role": "CC IP RP records in declared rich SIM references",
            "SIM_payloads_opened_by_catalog_builder": False,
            "position_catalog_materialized": False,
            "uniform-volume_substitution_is_exact_position": False,
        },
        "coverage": {
            "geometries": list(GEOMETRIES),
            "families": list(FAMILIES),
            "cells": len(cells),
            "N_DAT": len(entries),
            "sum_TT_s": math.fsum(float(row["TT_s"]) for row in entries),
            "sum_RP": math.fsum(float(row["sum_RP"]) for row in entries),
            "zero_RP_DAT": sum(bool(row["zero_RP"]) for row in entries),
        },
        "cells": cells,
        "production_rows": production_rows,
        "dat_entries": entries,
        "sidecars": {
            "cell_summary_csv": {
                "path": "cell_summary.csv",
                "sha256": hashlib.sha256(cell_csv).hexdigest(),
            },
            "production_by_volume_isotope_state_csv": {
                "path": "production_by_volume_isotope_state.csv",
                "sha256": hashlib.sha256(production_csv).hexdigest(),
            },
        },
        "authority_boundary": [
            "corrected-keV production inventory and delayed-source preparation input only",
            "not delayed-decay transport",
            "not mission response or sensitivity authority",
            "not final geometry promotion authority",
        ],
    }
    return catalog, cell_csv, production_csv, batch0007_state


def publish(catalog: dict[str, Any], cell_csv: bytes, production_csv: bytes) -> None:
    expected = {
        "catalog.json": canonical_bytes(catalog),
        "cell_summary.csv": cell_csv,
        "production_by_volume_isotope_state.csv": production_csv,
    }
    PUBLISH_ROOT.mkdir(parents=True, exist_ok=True)
    if CATALOG_DIR.exists():
        if not CATALOG_DIR.is_dir() or CATALOG_DIR.is_symlink():
            raise RuntimeError(f"canonical catalog path has wrong type: {rel(CATALOG_DIR)}")
        for name, content in expected.items():
            path = CATALOG_DIR / name
            if not path.is_file() or path.is_symlink() or path.read_bytes() != content:
                raise RuntimeError(f"write-once catalog differs: {rel(path)}")
    else:
        temporary = PUBLISH_ROOT / f".catalog_v1.partial-{os.getpid()}-{uuid.uuid4().hex}"
        temporary.mkdir()
        try:
            for name, content in expected.items():
                path = temporary / name
                path.write_bytes(content)
                with path.open("rb") as handle:
                    os.fsync(handle.fileno())
            os.replace(temporary, CATALOG_DIR)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
    target = Path("catalog_v1/catalog.json")
    if COMPAT_LINK.is_symlink():
        if Path(os.readlink(COMPAT_LINK)) != target:
            raise RuntimeError(f"compatibility symlink target drift: {rel(COMPAT_LINK)}")
    elif COMPAT_LINK.exists():
        raise RuntimeError(f"compatibility view is not a symlink: {rel(COMPAT_LINK)}")
    else:
        temporary_link = PUBLISH_ROOT / f".{COMPAT_LINK.name}.partial-{os.getpid()}-{uuid.uuid4().hex}"
        try:
            temporary_link.symlink_to(target)
            os.replace(temporary_link, COMPAT_LINK)
        finally:
            temporary_link.unlink(missing_ok=True)


def self_test() -> dict[str, Any]:
    entries = [
        {
            "geometry": "Mass_model_511", "family": "eminus", "batch_id": "a",
            "job_id": "zero", "dat_path": "zero.dat", "TT_s": 3.0,
            "sum_RP": 0.0, "RP_record_count": 0, "zero_RP": True, "records": [],
        },
        {
            "geometry": "Mass_model_511", "family": "eminus", "batch_id": "a",
            "job_id": "positive", "dat_path": "positive.dat", "TT_s": 2.0,
            "sum_RP": 10.0, "RP_record_count": 1, "zero_RP": False,
            "records": [{"volume": "V", "isotope_id": 29064, "Z": 29, "A": 64,
                         "excitation_keV": 0.0, "RP": 10.0}],
        },
    ]
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in entries:
        grouped[(row["geometry"], row["family"])].append(row)
    rows = grouped[("Mass_model_511", "eminus")]
    denominator = math.fsum(float(row["TT_s"]) for row in rows)
    assert denominator == 5.0
    assert math.fsum(float(row["sum_RP"]) for row in rows) / denominator == 2.0
    assert isotope_za(29064) == (29, 64)
    assert len(dedupe(entries + [entries[0]])) == 2
    assert not CATALOG_DIR.exists() or CATALOG_DIR.is_dir()
    return {
        "status": "PASS__CORRECTED_BUILDUP_CATALOG_SELF_TEST",
        "tests": 5,
        "zero_RP_TT_denominator": denominator,
        "synthetic_rate_s-1": 2.0,
        "writes_performed": False,
        "transport_launched": False,
        "SIM_payload_opened": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--publish", action="store_true")
    group.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), indent=2, sort_keys=True))
        return 0
    catalog, _cells, _production, state = build_catalog(require_batch0007=args.publish)
    if args.publish:
        publish(catalog, _cells, _production)
    print(json.dumps({
        "status": catalog["status"],
        "mode": "publish" if args.publish else "check",
        "batch0007_state": state,
        "coverage": catalog["coverage"],
        "canonical_catalog": rel(CATALOG_DIR / "catalog.json"),
        "compatibility_view": rel(COMPAT_LINK),
        "writes_performed": bool(args.publish),
        "transport_launched": False,
        "SIM_payload_opened": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
