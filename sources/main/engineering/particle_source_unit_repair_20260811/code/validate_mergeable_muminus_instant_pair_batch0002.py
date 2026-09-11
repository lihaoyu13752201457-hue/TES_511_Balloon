#!/usr/bin/env python3
"""Fail-closed dynamic validator for paired instant-muminus batch0002."""

from __future__ import annotations

import argparse
import csv
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

import run_mergeable_muminus_instant_pair_batch0002 as batch  # noqa: E402
import run_mergeable_two_geometry_smoke as smoke  # noqa: E402
import validate_mergeable_two_geometry_smoke as common  # noqa: E402


GENERATED_RE = re.compile(r"Total number of generated particles:\s+(\d+)")
OBSERVATION_RE = re.compile(r"Observation time:\s+([-+0-9.eE]+) sec")
RETURN_RE = re.compile(r"^returncode=(\d+)\s*$", re.MULTILINE)


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _expected_job_name() -> str:
    return f"Background_{batch.FAMILY}_fullsphere20_batch0002_pair"


def validate() -> tuple[dict[str, Any], dict[str, Any]]:
    gate = common.Gate()
    required = (batch.GLOBAL_CONTRACT, batch.SOURCE_CONTRACT, batch.BATCH0000_LEDGER,
                batch.BATCH0001_LEDGER, batch.GENERIC_RUNNER)
    for path in required:
        gate.require(path.is_file(), f"missing required input: {smoke.rel(path)}", "contract")
    if not all(path.is_file() for path in required):
        return ({"schema_version": 1, "status": "FAIL", "errors": gate.errors,
                 "checks": dict(gate.checks)},
                {"schema_version": 1, "status": "FAIL_NOT_MERGE_ELIGIBLE", "errors": gate.errors})

    contract = _json(batch.GLOBAL_CONTRACT)
    source_contract = _json(batch.SOURCE_CONTRACT)
    ledger0 = _json(batch.BATCH0000_LEDGER)
    ledger1 = _json(batch.BATCH0001_LEDGER)
    contract_hash = smoke.sha256(batch.GLOBAL_CONTRACT)
    gate.require(contract.get("batch_id") == batch.BATCH_ID, "global batch ID mismatch", "contract")
    gate.require(contract.get("campaign_version") == batch.CAMPAIGN_VERSION,
                 "campaign version mismatch", "contract")
    gate.require(contract.get("source_contract_manifest_sha256") == batch.SOURCE_CONTRACT_SHA256,
                 "source contract binding mismatch", "contract")
    gate.require(smoke.sha256(batch.SOURCE_CONTRACT) == batch.SOURCE_CONTRACT_SHA256,
                 "source contract hash mismatch", "contract")
    for ledger, expected_hash, batch_id, status in (
        (ledger0, batch.BATCH0000_SHA256, batch.BATCH0000_ID, batch.BATCH0000_STATUS),
        (ledger1, batch.BATCH0001_SHA256, batch.BATCH0001_ID, batch.BATCH0001_STATUS),
    ):
        gate.require(ledger.get("batch_id") == batch_id and ledger.get("status") == status,
                     f"prior ledger status mismatch: {batch_id}", "lineage")
        gate.require(ledger.get("source_contract_manifest_sha256") == batch.SOURCE_CONTRACT_SHA256,
                     f"prior ledger source binding mismatch: {batch_id}", "lineage")
        path = batch.BATCH0000_LEDGER if batch_id == batch.BATCH0000_ID else batch.BATCH0001_LEDGER
        gate.require(smoke.sha256(path) == expected_hash,
                     f"prior ledger hash mismatch: {batch_id}", "lineage")
    gate.require(any(row.get("ledger_sha256") == batch.BATCH0000_SHA256
                     for row in ledger1.get("prior_batches", [])),
                 "batch0001 lineage omits batch0000", "lineage")
    gate.require(source_contract.get("source_model", {}).get("profile") == "unit_only_total_gamma",
                 "source profile mismatch", "contract")
    gate.require(source_contract.get("policies", {}).get("additive_mono_511_allowed") is False,
                 "mono-511 policy mismatch", "contract")
    gate.require(contract.get("source_scope") == {"included_families": [batch.FAMILY],
                                                  "excluded_families": ["p"], "angular_bins": 20},
                 "source family scope mismatch", "contract")
    gate.require(contract.get("statistics", {}).get("events_per_geometry") == batch.EVENTS,
                 "event-count contract mismatch", "contract")
    gate.require(contract.get("pairing", {}).get("seed") == batch.SEED,
                 "pair seed mismatch", "seeds")
    gate.require(contract.get("pairing", {}).get("buildup_included") is False,
                 "buildup incorrectly included", "contract")
    for name, record in contract.get("toolchain", {}).items():
        path = common.resolve_repo_path(record.get("path", "__missing__"))
        gate.require(path.is_file() and smoke.sha256(path) == record.get("sha256"),
                     f"toolchain hash mismatch: {name}", "toolchain")
    gate.require(contract.get("toolchain", {}).get("dynamic_validator", {}).get("sha256")
                 == smoke.sha256(THIS_FILE), "validator self hash mismatch", "toolchain")

    cosima = smoke.resolve_cosima(contract.get("transport", {}).get("cosima"))
    environment, descriptor = smoke.resolve_transport_environment(cosima)
    current_transport = smoke.build_transport_fingerprint(cosima, environment, descriptor)
    gate.require(batch._transport_core(current_transport) == contract.get("transport_core"),
                 "transport fingerprint changed", "transport")
    current_bundles: dict[str, dict[str, Any]] = {}
    for geometry in batch.GEOMETRIES:
        bundle = smoke.build_geometry_bundle(geometry, environment)
        current_bundles[geometry] = bundle
        gate.require(bundle == contract.get("geometry_bundles", {}).get(geometry),
                     f"geometry bundle changed: {geometry}", "geometry")
        gate.require(common.source_contract_geometry_files(source_contract, geometry, environment)
                     == bundle["files"], f"source/runtime geometry mismatch: {geometry}", "geometry")

    campaigns_by_geometry = {row.get("geometry"): row for row in contract.get("campaigns", [])}
    gate.require(set(campaigns_by_geometry) == set(batch.GEOMETRIES) and len(contract.get("campaigns", [])) == 2,
                 "campaign pair mismatch", "contract")
    prior_seeds = batch._prior_seeds(ledger0, ledger1)
    gate.require(batch.SEED not in prior_seeds, "batch0002 seed overlaps prior ledger", "seeds")

    spectrum_hashes = {
        str(row["corrected_spectrum"]): str(row["corrected_sha256"])
        for row in source_contract.get("spectra", {}).get("files", [])
    }
    gate.require(len(spectrum_hashes) == 160, "corrected spectrum inventory mismatch", "contract")
    validated_campaigns: list[dict[str, Any]] = []
    all_seeds: list[int] = []
    for geometry in batch.GEOMETRIES:
        label = f"{geometry}/{batch.MODE}/{batch.FAMILY}"
        campaign = campaigns_by_geometry.get(geometry, {})
        outdir = batch.output_dir(geometry)
        paths = {
            "batch_contract": outdir / "batch_contract.json",
            "normalization": outdir / "normalization.json",
            "manifest": outdir / "run_manifest.csv",
            "summary_json": outdir / "run_summary.json",
            "summary_csv": outdir / "run_summary.csv",
            "summary_md": outdir / "run_summary.md",
        }
        for path in paths.values():
            gate.require(path.is_file(), f"{label}: missing {smoke.rel(path)}", "outputs")
        if not all(path.is_file() for path in paths.values()):
            continue
        batch_contract = _json(paths["batch_contract"])
        normalization = _json(paths["normalization"])
        gate.require(batch_contract.get("global_contract_sha256") == contract_hash,
                     f"{label}: global contract hash mismatch", "binding")
        for key, expected in (("geometry", geometry), ("mode", batch.MODE),
                              ("family", batch.FAMILY), ("events", batch.EVENTS), ("seed", batch.SEED)):
            gate.require(batch_contract.get(key) == expected,
                         f"{label}: batch contract {key} mismatch", "binding")
        gate.require(batch_contract.get("geometry_bundle") == current_bundles[geometry],
                     f"{label}: campaign geometry bundle mismatch", "geometry")
        source_card = common.resolve_repo_path(campaign.get("source_card", "__missing__"))
        migration_path = common.resolve_repo_path(campaign.get("source_migration_manifest", "__missing__"))
        gate.require(source_card.is_file() and smoke.sha256(source_card) == campaign.get("source_card_sha256"),
                     f"{label}: corrected source-card hash mismatch", "binding")
        gate.require(migration_path.is_file() and smoke.sha256(migration_path)
                     == campaign.get("source_migration_manifest_sha256"),
                     f"{label}: source migration hash mismatch", "binding")
        gate.require(normalization.get("selected_particles") == [batch.FAMILY]
                     and normalization.get("excluded_particles") == ["p"],
                     f"{label}: particle selection mismatch", "normalization")
        gate.require(normalization.get("events") == batch.EVENTS and normalization.get("jobs") == 1,
                     f"{label}: normalization count mismatch", "normalization")
        gate.require(normalization.get("seed") == batch.SEED,
                     f"{label}: normalization seed mismatch", "seeds")
        gate.require(normalization.get("prior_merge_ledger_sha256") == batch.BATCH0001_SHA256,
                     f"{label}: batch0001 binding mismatch", "lineage")
        gate.require(normalization.get("batch_contract_sha256") == smoke.sha256(paths["batch_contract"]),
                     f"{label}: batch contract hash binding mismatch", "binding")

        with paths["manifest"].open(newline="", encoding="utf-8") as handle:
            manifest_rows = list(csv.DictReader(handle))
        summaries = _json(paths["summary_json"])
        with paths["summary_csv"].open(newline="", encoding="utf-8") as handle:
            summary_csv_rows = list(csv.DictReader(handle))
        gate.require(len(manifest_rows) == len(summaries) == len(summary_csv_rows) == 1,
                     f"{label}: expected one manifest/summary row", "jobs")
        if not manifest_rows or not summaries or not summary_csv_rows:
            continue
        manifest = manifest_rows[0]
        summary = summaries[0]
        summary_csv = summary_csv_rows[0]
        job_name = _expected_job_name()
        expected_manifest = {"job_name": job_name, "particle": batch.FAMILY, "mode": batch.MODE,
                             "events": str(batch.EVENTS), "rep": "1", "part": "1",
                             "seed": str(batch.SEED), "store_isotopes": "True"}
        for key, expected in expected_manifest.items():
            gate.require(manifest.get(key) == expected,
                         f"{label}: manifest {key} mismatch", "jobs")
        base_source = (batch.GEOMETRIES[geometry] / f"Background_{batch.FAMILY}_fullsphere20.source").resolve()
        job_source = common.resolve_repo_path(manifest["temp_source"])
        sim_path = common.resolve_repo_path(manifest["sim_path"])
        dat_path = common.resolve_repo_path(manifest["dat_path"])
        log_path = common.resolve_repo_path(manifest["log"])
        expected_paths = {
            "job_source": outdir / "job_sources" / f"{job_name}.source",
            "sim": outdir / f"{job_name}.inc1.id1.sim.gz",
            "dat": outdir / f"{job_name}.dat.inc1.dat",
            "log": outdir / "logs" / f"{job_name}.log",
        }
        for kind, path in (("job_source", job_source), ("sim", sim_path),
                           ("dat", dat_path), ("log", log_path)):
            gate.require(path.resolve() == expected_paths[kind].resolve(),
                         f"{label}: unexpected {kind} path", "outputs")
            gate.require(common.is_within(path, outdir), f"{label}: {kind} escapes output dir", "outputs")
            gate.require(path.is_file() and path.stat().st_size > 0,
                         f"{label}: missing/empty {kind}", "outputs")
        if not all(path.is_file() for path in (job_source, sim_path, dat_path, log_path)):
            continue

        migration = _json(batch.source_manifest_path(geometry))
        expected_geometry = common.resolve_repo_path(migration["geometry_setup"])
        gate.require(common.source_geometry(job_source) == migration["geometry_setup"],
                     f"{label}: source geometry mismatch", "geometry")
        supports, corrected_refs, legacy_refs = common.validate_source_card(
            gate, base_source, job_source, batch.FAMILY, batch.MODE, job_name,
            batch.EVENTS, batch.SEED, outdir, spectrum_hashes,
        )
        gate.require(corrected_refs == 20 and legacy_refs == 0,
                     f"{label}: corrected/legacy spectrum reference mismatch", "source_refs")

        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        generated_match = GENERATED_RE.search(log_text)
        observation_match = OBSERVATION_RE.search(log_text)
        return_match = RETURN_RE.search(log_text)
        generated = int(generated_match.group(1)) if generated_match else None
        observation = float(observation_match.group(1)) if observation_match else None
        expected_command = f"cosima_command={contract['transport']['cosima']} -s {batch.SEED} {job_source}"
        gate.require(log_text.count(expected_command) == 1, f"{label}: Cosima command mismatch", "transport")
        gate.require("MEGAlib version" in log_text, f"{label}: MEGAlib banner missing", "transport")
        gate.require("***  Error" not in log_text and "Segmentation fault" not in log_text,
                     f"{label}: error marker in log", "log")
        gate.require(return_match is not None and int(return_match.group(1)) == 0,
                     f"{label}: nonzero/missing return", "log")
        gate.require(generated == batch.EVENTS, f"{label}: generated count mismatch", "log")
        gate.require(observation is not None and math.isfinite(observation) and observation > 0,
                     f"{label}: invalid log TT", "normalization")

        isotope = common.parse_isotope_dat(dat_path)
        for problem in isotope["problems"]:
            gate.problem(f"{label}: isotope DAT {problem}", "isotope_dat")
        dat_tt = isotope["TT_s"]
        gate.require(dat_tt is not None and dat_tt > 0, f"{label}: invalid DAT TT", "isotope_dat")
        if dat_tt is not None and observation is not None:
            gate.require(math.isclose(dat_tt, observation, rel_tol=2e-3, abs_tol=2e-6),
                         f"{label}: DAT/log TT mismatch", "isotope_dat")
        gate.require(summary.get("status") == "PASS" and int(summary.get("events", -1)) == batch.EVENTS
                     and int(summary.get("generated_particles") or -1) == batch.EVENTS,
                     f"{label}: JSON summary mismatch", "summary")
        for key in ("job_name", "particle", "status", "events", "generated_particles"):
            gate.require(str(summary_csv.get(key, "")) == str(summary.get(key, "")),
                         f"{label}: JSON/CSV {key} mismatch", "summary")
        scan = common.scan_sim(sim_path, batch.FAMILY, batch.EVENTS, batch.SEED,
                               expected_geometry, supports)
        for problem in scan["problems"]:
            gate.problem(f"{label}: {problem}", "sim")
        all_seeds.append(batch.SEED)
        area = math.pi * batch.FARFIELD_RADIUS_CM ** 2
        flux = common.source_flux(base_source)
        job_record = {"job_name": job_name, "family": batch.FAMILY,
                      "events": batch.EVENTS, "seed": batch.SEED,
                      "job_source": smoke.rel(job_source), "job_source_sha256": smoke.sha256(job_source),
                      "sim": smoke.rel(sim_path), "sim_sha256": smoke.sha256(sim_path),
                      "isotope_dat": smoke.rel(dat_path), "isotope_dat_sha256": smoke.sha256(dat_path),
                      "isotope_store": isotope, "log": smoke.rel(log_path),
                      "log_sha256": smoke.sha256(log_path), "ia_init": scan}
        validated_campaigns.append({
            "geometry": geometry, "mode": batch.MODE, "family": batch.FAMILY,
            "events_requested": batch.EVENTS, "events_with_validated_ia_init": scan["ia_init_records"],
            "seed": batch.SEED, "flux_cm2_s": flux,
            "TT_s_from_log": observation, "TT_s_from_isotope_dat": dat_tt,
            "TT_s_expected_mean_from_events_flux_area": batch.EVENTS / (flux * area),
            "geometry_bundle": current_bundles[geometry],
            "batch_contract": smoke.rel(paths["batch_contract"]),
            "batch_contract_sha256": smoke.sha256(paths["batch_contract"]),
            "normalization": smoke.rel(paths["normalization"]),
            "normalization_sha256": smoke.sha256(paths["normalization"]),
            "jobs": [job_record],
            "job": job_record,
        })

    gate.require(len(validated_campaigns) == 2, "validated campaign count mismatch", "campaigns")
    gate.require(all_seeds == [batch.SEED, batch.SEED],
                 "paired seed registry mismatch", "seeds")
    for campaign in validated_campaigns:
        jobs = campaign.get("jobs")
        gate.require(isinstance(jobs, list) and len(jobs) == 1 and isinstance(jobs[0], dict),
                     f"{campaign.get('geometry')}: standard jobs[] ledger schema mismatch", "ledger_schema")
        if isinstance(jobs, list) and len(jobs) == 1 and isinstance(jobs[0], dict):
            gate.require(campaign.get("job") == jobs[0],
                         f"{campaign.get('geometry')}: compatibility job alias mismatch", "ledger_schema")
            gate.require(jobs[0].get("family") == batch.FAMILY
                         and jobs[0].get("seed") == batch.SEED
                         and jobs[0].get("events") == batch.EVENTS,
                         f"{campaign.get('geometry')}: jobs[] identity mismatch", "ledger_schema")
    status = "PASS" if not gate.errors else "FAIL"
    report = {
        "schema_version": 1, "status": status, "batch_id": batch.BATCH_ID,
        "campaign_version": batch.CAMPAIGN_VERSION, "errors": gate.errors,
        "checks": dict(gate.checks), "global_contract": smoke.rel(batch.GLOBAL_CONTRACT),
        "global_contract_sha256": contract_hash, "campaigns": validated_campaigns,
    }
    ledger = {
        "schema_version": 1,
        "status": "PASS__BATCH0002_MERGE_ELIGIBLE" if status == "PASS" else "FAIL_NOT_MERGE_ELIGIBLE",
        "batch_id": batch.BATCH_ID, "campaign_version": batch.CAMPAIGN_VERSION,
        "source_contract_manifest": smoke.rel(batch.SOURCE_CONTRACT),
        "source_contract_manifest_sha256": batch.SOURCE_CONTRACT_SHA256,
        "prior_batches": contract.get("lineage", []),
        "global_contract": smoke.rel(batch.GLOBAL_CONTRACT),
        "global_contract_sha256": contract_hash,
        "validation_report": smoke.rel(batch.VALIDATION_REPORT),
        "pairing_rule": "Mass_model_511/S3d-O8 same-seed matched transport; never pool geometries",
        "pooling_boundary": "never pool across geometry, mode, or family",
        "TT_authority": "positive matching isotope-DAT/log TT",
        "excluded_family": "p", "campaigns": validated_campaigns, "errors": gate.errors,
    }
    return report, ledger


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true",
        help="read-only dynamic revalidation; do not write or replace validation/ledger files",
    )
    args = parser.parse_args()
    if not args.check and (batch.VALIDATION_REPORT.exists() or batch.MERGE_LEDGER.exists()):
        raise SystemExit("write-once batch0002 validation/ledger target exists")
    report, ledger = validate()
    if args.check:
        print(json.dumps({"status": report["status"], "errors": report["errors"],
                          "mode": "READ_ONLY_CHECK", "would_write_ledger": report["status"] == "PASS"},
                         indent=2, ensure_ascii=False))
        return 0 if report["status"] == "PASS" else 1
    smoke.atomic_json(batch.VALIDATION_REPORT, report)
    if report["status"] == "PASS":
        ledger["validation_report_sha256"] = smoke.sha256(batch.VALIDATION_REPORT)
        smoke.atomic_json(batch.MERGE_LEDGER, ledger)
    print(json.dumps({"status": report["status"], "errors": report["errors"],
                      "validation": smoke.rel(batch.VALIDATION_REPORT),
                      "ledger": smoke.rel(batch.MERGE_LEDGER) if batch.MERGE_LEDGER.exists() else None},
                     indent=2, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
