#!/usr/bin/env python3
"""Fail-closed dynamic validator and merge ledger for seven-family batch0001."""

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

import run_mergeable_two_geometry_seven_family_batch0001 as batch  # noqa: E402
import run_mergeable_two_geometry_smoke as smoke  # noqa: E402
import validate_mergeable_two_geometry_smoke as common  # noqa: E402


GENERATED_RE = re.compile(r"Total number of generated particles:\s+(\d+)")
OBSERVATION_RE = re.compile(r"Observation time:\s+([-+0-9.eE]+) sec")
RETURN_RE = re.compile(r"^returncode=(\d+)\s*$", re.MULTILINE)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def expected_jobs(source_dir: Path, mode: str) -> dict[str, dict[str, Any]]:
    fluxes = batch._source_fluxes(source_dir)
    selected_events = batch.expected_events_by_family(source_dir)
    sources = {
        family: (source_dir / f"Background_{family}_fullsphere20.source").resolve()
        for family in batch.FAMILIES
    }
    expected: dict[str, dict[str, Any]] = {}
    ordinal = 0
    gamma_parts = [
        batch.GAMMA_EVENTS // batch.GAMMA_SPLITS
        + (1 if index < batch.GAMMA_EVENTS % batch.GAMMA_SPLITS else 0)
        for index in range(batch.GAMMA_SPLITS)
    ]
    for part, events in enumerate(gamma_parts, 1):
        ordinal += 1
        name = f"Background_gamma_fullsphere20_rep01_part{part:02d}"
        expected[name] = {
            "family": "gamma",
            "mode": mode,
            "events": events,
            "rep": 1,
            "part": part,
            "seed": batch.SEED_BASE_BY_MODE[mode] + ordinal * batch.SEED_STRIDE,
            "source": sources["gamma"],
            "flux_cm2_s": fluxes["gamma"],
        }
    for family in sorted(set(batch.FAMILIES) - {"gamma"}):
        ordinal += 1
        name = f"Background_{family}_fullsphere20_rep01_part01"
        expected[name] = {
            "family": family,
            "mode": mode,
            "events": selected_events[family],
            "rep": 1,
            "part": 1,
            "seed": batch.SEED_BASE_BY_MODE[mode] + ordinal * batch.SEED_STRIDE,
            "source": sources[family],
            "flux_cm2_s": fluxes[family],
        }
    if len(expected) != batch.EXPECTED_JOBS_PER_CAMPAIGN:
        raise ValueError(f"expected job count={len(expected)}")
    return expected


def expected_all_base_events(source_dir: Path) -> dict[str, int]:
    fluxes = batch._source_fluxes(source_dir)
    gamma_flux = fluxes["gamma"]
    return {
        family: batch.GAMMA_EVENTS
        if family == "gamma"
        else int(round(flux / gamma_flux * batch.GAMMA_EVENTS))
        for family, flux in fluxes.items()
    }


def validate_campaign(
    gate: common.Gate,
    geometry: str,
    mode: str,
    spectrum_hashes: dict[str, str],
    global_contract: dict[str, Any],
    global_contract_hash: str,
    current_geometry_bundle: dict[str, Any],
) -> dict[str, Any]:
    label = f"{geometry}/{mode}"
    outdir = batch.output_dir(geometry, mode)
    source_dir = batch.GEOMETRIES[geometry]
    expected = expected_jobs(source_dir, mode)
    migration_path = batch.source_manifest_path(geometry)
    migration = load_json(migration_path)
    expected_geometry = common.resolve_repo_path(migration["geometry_setup"])

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
        return {"geometry": geometry, "mode": mode, "status": "FAIL_MISSING_CAMPAIGN_FILES", "jobs": []}

    batch_contract = load_json(paths["batch_contract"])
    normalization = load_json(paths["normalization"])
    summary_rows = load_json(paths["summary_json"])
    binding = normalization.get("mergeable_batch_binding", {})
    fixed = {
        "batch_id": batch.BATCH_ID,
        "campaign_version": batch.CAMPAIGN_VERSION,
        "geometry": geometry,
        "mode": mode,
        "source_contract_manifest_sha256": batch.SOURCE_CONTRACT_SHA256,
        "source_migration_manifest_sha256": smoke.sha256(migration_path),
        "global_contract_sha256": global_contract_hash,
    }
    for key, value in fixed.items():
        gate.require(batch_contract.get(key) == value, f"{label}: batch contract {key} mismatch", "binding")
        gate.require(binding.get(key) == value, f"{label}: normalization binding {key} mismatch", "binding")
    gate.require(
        binding.get("batch_contract_sha256") == smoke.sha256(paths["batch_contract"]),
        f"{label}: batch contract hash binding mismatch",
        "binding",
    )
    gate.require(
        binding.get("prior_merge_ledger_sha256") == batch.PRIOR_LEDGER_SHA256,
        f"{label}: prior ledger binding mismatch",
        "binding",
    )
    frozen_bundle = global_contract["geometry_bundles"][geometry]
    gate.require(batch_contract.get("geometry_bundle") == frozen_bundle, f"{label}: frozen geometry mismatch", "geometry")
    gate.require(current_geometry_bundle == frozen_bundle, f"{label}: current geometry changed", "geometry")
    gate.require(
        binding.get("geometry_bundle_sha256") == frozen_bundle["bundle_sha256"],
        f"{label}: geometry digest binding mismatch",
        "geometry",
    )
    frozen_transport = global_contract["transport"]
    for key, value in {
        "transport_cosima": frozen_transport["cosima"],
        "transport_cosima_sha256": frozen_transport["cosima_sha256"],
        "transport_shared_libraries_bundle_sha256": frozen_transport["shared_libraries_bundle_sha256"],
        "transport_environment_sha256": frozen_transport["environment"]["relevant_variables_sha256"],
        "dynamic_validator_sha256": global_contract["toolchain"]["dynamic_validator"]["sha256"],
    }.items():
        gate.require(binding.get(key) == value, f"{label}: {key} binding mismatch", "transport")

    expected_normalization = {
        "mode": mode,
        "source_dir": smoke.rel(source_dir.resolve()),
        "outdir": smoke.rel(outdir.resolve()),
        "gamma_events": batch.GAMMA_EVENTS,
        "gamma_splits": batch.GAMMA_SPLITS,
        "non_gamma_replicas": batch.NON_GAMMA_REPLICAS,
        "farfield_radius_cm": batch.FARFIELD_RADIUS_CM,
        "jobs": batch.EXPECTED_JOBS_PER_CAMPAIGN,
        "store_isotopes": True,
        "seed_base": batch.SEED_BASE_BY_MODE[mode],
        "seed_stride": batch.SEED_STRIDE,
    }
    for key, value in expected_normalization.items():
        gate.require(normalization.get(key) == value, f"{label}: normalization {key} mismatch", "normalization")
    gate.require(
        normalization.get("selected_particles") == sorted(batch.FAMILIES),
        f"{label}: selected particle set is not the fixed seven-family set",
        "normalization",
    )
    gate.require("p" not in normalization.get("selected_particles", []), f"{label}: proton was selected", "normalization")
    gate.require(normalization.get("legacy_runner_estimate_authority") is False, f"{label}: legacy estimator not disabled", "resource")
    gate.require(
        normalization.get("corrected_smoke_resource_estimate")
        == next(
            item
            for item in global_contract["resource_gate"]["campaigns"]
            if item["geometry"] == geometry and item["mode"] == mode
        ),
        f"{label}: corrected smoke resource estimate mismatch",
        "resource",
    )
    gate.require("farfield_radius_warning" not in normalization, f"{label}: farfield radius warning present", "normalization")
    fluxes = batch._source_fluxes(source_dir)
    normalized_fluxes = normalization.get("flux_by_particle_cm2_s", {})
    gate.require(set(normalized_fluxes) == set(batch.ALL_SOURCE_FAMILIES), f"{label}: flux map is not canonical all-eight", "normalization")
    for family, value in fluxes.items():
        observed = common.parse_float(normalized_fluxes.get(family))
        gate.require(
            observed is not None and math.isclose(observed, value, rel_tol=1.0e-12, abs_tol=1.0e-15),
            f"{label}: flux mismatch for {family}",
            "normalization",
        )
    gate.require(
        normalization.get("base_events_by_particle") == expected_all_base_events(source_dir),
        f"{label}: base event map mismatch",
        "normalization",
    )

    with paths["manifest"].open(newline="", encoding="utf-8") as handle:
        manifest_rows = list(csv.DictReader(handle))
    with paths["summary_csv"].open(newline="", encoding="utf-8") as handle:
        summary_csv_rows = list(csv.DictReader(handle))
    manifest_by_name = {row["job_name"]: row for row in manifest_rows}
    summary_by_name = {str(row.get("job_name")): row for row in summary_rows}
    summary_csv_by_name = {row["job_name"]: row for row in summary_csv_rows}
    for name, rows in (
        ("manifest", manifest_rows),
        ("summary JSON", summary_rows),
        ("summary CSV", summary_csv_rows),
    ):
        gate.require(len(rows) == batch.EXPECTED_JOBS_PER_CAMPAIGN, f"{label}: {name} row count mismatch", "jobs")
    gate.require(set(manifest_by_name) == set(expected), f"{label}: manifest job set mismatch", "jobs")
    gate.require(set(summary_by_name) == set(expected), f"{label}: summary job set mismatch", "jobs")
    gate.require(set(summary_csv_by_name) == set(expected), f"{label}: CSV summary job set mismatch", "jobs")

    jobs: list[dict[str, Any]] = []
    seeds: list[int] = []
    corrected_refs = 0
    legacy_refs = 0
    family_tt: dict[str, float] = {}
    activation: dict[tuple[str, str, int, float], float] = {}
    for job_name, exp in expected.items():
        row = manifest_by_name.get(job_name)
        summary = summary_by_name.get(job_name)
        summary_csv = summary_csv_by_name.get(job_name)
        if row is None or summary is None or summary_csv is None:
            continue
        prefix = f"{label}/{job_name}"
        family = exp["family"]
        for key, value in {
            "particle": family,
            "mode": mode,
            "events": str(exp["events"]),
            "rep": str(exp["rep"]),
            "part": str(exp["part"]),
            "seed": str(exp["seed"]),
        }.items():
            gate.require(row.get(key) == value, f"{prefix}: manifest {key} mismatch", "jobs")
        gate.require(str(row.get("store_isotopes", "")).lower() == "true", f"{prefix}: isotope store disabled", "jobs")
        gate.require(common.resolve_repo_path(row["source"]) == exp["source"], f"{prefix}: wrong base source", "jobs")

        job_source = common.resolve_repo_path(row["temp_source"])
        sim_path = common.resolve_repo_path(row["sim_path"])
        dat_path = common.resolve_repo_path(row["dat_path"])
        log_path = common.resolve_repo_path(row["log"])
        expected_paths = {
            "job_source": outdir / "job_sources" / f"{job_name}.source",
            "sim": outdir / f"{job_name}.inc1.id1.sim.gz",
            "dat": outdir / f"{job_name}.dat.inc1.dat",
            "log": outdir / "logs" / f"{job_name}.log",
        }
        for kind, path in (("job_source", job_source), ("sim", sim_path), ("dat", dat_path), ("log", log_path)):
            gate.require(path == expected_paths[kind].resolve(), f"{prefix}: unexpected {kind} path", "outputs")
            gate.require(common.is_within(path, outdir), f"{prefix}: {kind} escapes output directory", "outputs")
            gate.require(path.is_file() and path.stat().st_size > 0, f"{prefix}: missing/empty {kind}", "outputs")
        if not all(path.is_file() for path in (job_source, sim_path, dat_path, log_path)):
            continue

        gate.require(common.source_geometry(job_source) == migration["geometry_setup"], f"{prefix}: geometry mismatch", "geometry")
        supports, corrected, legacy = common.validate_source_card(
            gate,
            exp["source"],
            job_source,
            family,
            mode,
            job_name,
            exp["events"],
            exp["seed"],
            outdir,
            spectrum_hashes,
        )
        corrected_refs += corrected
        legacy_refs += legacy

        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        generated_match = GENERATED_RE.search(log_text)
        observation_match = OBSERVATION_RE.search(log_text)
        return_match = RETURN_RE.search(log_text)
        generated = int(generated_match.group(1)) if generated_match else None
        observation = float(observation_match.group(1)) if observation_match else None
        expected_command = f"cosima_command={global_contract['transport']['cosima']} -s {exp['seed']} {job_source}"
        gate.require(log_text.count(expected_command) == 1, f"{prefix}: Cosima command mismatch", "transport")
        gate.require("MEGAlib version" in log_text, f"{prefix}: MEGAlib banner missing", "transport")
        gate.require("***  Error" not in log_text and "Segmentation fault" not in log_text, f"{prefix}: error marker", "log")
        gate.require(return_match is not None and int(return_match.group(1)) == 0, f"{prefix}: nonzero/missing return", "log")
        gate.require(generated == exp["events"], f"{prefix}: generated count mismatch", "log")
        gate.require(observation is not None and math.isfinite(observation) and observation > 0.0, f"{prefix}: invalid TT", "normalization")

        isotope = common.parse_isotope_dat(dat_path)
        for problem in isotope["problems"]:
            gate.problem(f"{prefix}: isotope DAT {problem}", "isotope_dat")
        dat_tt = isotope["TT_s"]
        gate.require(dat_tt is not None and dat_tt > 0.0, f"{prefix}: invalid DAT TT", "isotope_dat")
        if dat_tt is not None:
            family_tt[family] = math.fsum((family_tt.get(family, 0.0), dat_tt))
            if observation is not None:
                gate.require(
                    math.isclose(dat_tt, observation, rel_tol=2.0e-3, abs_tol=2.0e-6),
                    f"{prefix}: DAT/log TT mismatch",
                    "isotope_dat",
                )
            for record in isotope["RP_totals_by_volume_isotope_state"]:
                key = (family, str(record["volume"]), int(record["isotope_id"]), float(record["excitation_keV"]))
                activation[key] = math.fsum((activation.get(key, 0.0), float(record["sum_RP"])))

        gate.require(summary.get("status") == "PASS", f"{prefix}: summary not PASS", "summary")
        gate.require(int(summary.get("events", -1)) == exp["events"], f"{prefix}: summary events mismatch", "summary")
        gate.require(int(summary.get("generated_particles") or -1) == exp["events"], f"{prefix}: summary generated mismatch", "summary")
        gate.require(summary.get("sim_exists") is True and summary.get("dat_exists") is True, f"{prefix}: summary output flags", "summary")
        for key in ("particle", "status", "events", "generated_particles"):
            gate.require(str(summary_csv.get(key, "")) == str(summary.get(key, "")), f"{prefix}: JSON/CSV {key} mismatch", "summary")

        scan = common.scan_sim(sim_path, family, exp["events"], exp["seed"], expected_geometry, supports)
        for problem in scan["problems"]:
            gate.problem(f"{prefix}: {problem}", "sim")
        area = math.pi * batch.FARFIELD_RADIUS_CM * batch.FARFIELD_RADIUS_CM
        seeds.append(exp["seed"])
        jobs.append(
            {
                "job_name": job_name,
                "family": family,
                "events": exp["events"],
                "seed": exp["seed"],
                "flux_cm2_s": exp["flux_cm2_s"],
                "TT_s_from_log": observation,
                "TT_s_from_isotope_dat": dat_tt,
                "TT_s_expected_mean_from_events_flux_area": exp["events"] / (exp["flux_cm2_s"] * area),
                "job_source": smoke.rel(job_source),
                "job_source_sha256": smoke.sha256(job_source),
                "sim": smoke.rel(sim_path),
                "sim_sha256": smoke.sha256(sim_path),
                "isotope_dat": smoke.rel(dat_path),
                "isotope_dat_sha256": smoke.sha256(dat_path),
                "isotope_store": isotope,
                "log": smoke.rel(log_path),
                "log_sha256": smoke.sha256(log_path),
                "ia_init": scan,
            }
        )

    gate.require(corrected_refs == 20 * batch.EXPECTED_JOBS_PER_CAMPAIGN, f"{label}: corrected refs={corrected_refs}", "source_refs")
    gate.require(legacy_refs == 0, f"{label}: legacy refs={legacy_refs}", "source_refs")
    gate.require(set(family_tt) == set(batch.FAMILIES), f"{label}: family TT coverage mismatch", "isotope_dat")
    gate.require(sorted(seeds) == sorted(batch.expected_seeds(mode)), f"{label}: seed registry mismatch", "seeds")
    activation_rows = []
    for (family, volume, isotope_id, excitation), sum_rp in sorted(activation.items()):
        activation_rows.append(
            {
                "family": family,
                "volume": volume,
                "isotope_id": isotope_id,
                "excitation_keV": excitation,
                "sum_RP": sum_rp,
                "sum_TT_s": family_tt[family],
                "sum_RP_over_sum_TT_s-1": sum_rp / family_tt[family],
            }
        )
    return {
        "geometry": geometry,
        "mode": mode,
        "batch_id": batch.BATCH_ID,
        "outdir": smoke.rel(outdir),
        "source_dir": smoke.rel(source_dir),
        "source_migration_manifest": smoke.rel(migration_path),
        "source_migration_manifest_sha256": smoke.sha256(migration_path),
        "geometry_setup": smoke.rel(expected_geometry),
        "geometry_setup_sha256": smoke.sha256(expected_geometry),
        "geometry_bundle": frozen_bundle,
        "batch_contract": smoke.rel(paths["batch_contract"]),
        "batch_contract_sha256": smoke.sha256(paths["batch_contract"]),
        "normalization": smoke.rel(paths["normalization"]),
        "normalization_sha256": smoke.sha256(paths["normalization"]),
        "run_manifest": smoke.rel(paths["manifest"]),
        "run_manifest_sha256": smoke.sha256(paths["manifest"]),
        "run_summary_json": smoke.rel(paths["summary_json"]),
        "run_summary_json_sha256": smoke.sha256(paths["summary_json"]),
        "run_summary_csv": smoke.rel(paths["summary_csv"]),
        "run_summary_csv_sha256": smoke.sha256(paths["summary_csv"]),
        "run_summary_md": smoke.rel(paths["summary_md"]),
        "run_summary_md_sha256": smoke.sha256(paths["summary_md"]),
        "corrected_spectrum_references": corrected_refs,
        "legacy_spectrum_references": legacy_refs,
        "events_requested": sum(item["events"] for item in expected.values()),
        "events_with_validated_ia_init": sum(item["ia_init"]["ia_init_records"] for item in jobs),
        "seeds": sorted(seeds),
        "family_exposure_for_prompt_and_activation": [
            {"family": family, "sum_TT_s": family_tt[family]} for family in sorted(family_tt)
        ],
        "activation_RP_by_family_volume_isotope_state": activation_rows,
        "zero_RP_merge_rule": "include registered family TT even when no RP row exists for an isotope state",
        "jobs": jobs,
    }


def validate() -> tuple[dict[str, Any], dict[str, Any]]:
    gate = common.Gate()
    for path in (batch.GLOBAL_CONTRACT, batch.SOURCE_CONTRACT, batch.PRIOR_LEDGER, batch.RUNNER):
        gate.require(path.is_file(), f"missing required input {smoke.rel(path)}", "contract")
    if not all(path.is_file() for path in (batch.GLOBAL_CONTRACT, batch.SOURCE_CONTRACT, batch.PRIOR_LEDGER)):
        return (
            {"schema_version": 1, "status": "FAIL", "errors": gate.errors, "checks": dict(gate.checks)},
            {"schema_version": 1, "status": "FAIL_NOT_MERGE_ELIGIBLE", "errors": gate.errors},
        )

    contract = load_json(batch.GLOBAL_CONTRACT)
    source_contract = load_json(batch.SOURCE_CONTRACT)
    prior_ledger = load_json(batch.PRIOR_LEDGER)
    contract_hash = smoke.sha256(batch.GLOBAL_CONTRACT)
    gate.require(contract.get("batch_id") == batch.BATCH_ID, "global batch ID mismatch", "contract")
    gate.require(contract.get("campaign_version") == batch.CAMPAIGN_VERSION, "campaign version mismatch", "contract")
    gate.require(smoke.sha256(batch.SOURCE_CONTRACT) == batch.SOURCE_CONTRACT_SHA256, "source contract hash mismatch", "contract")
    gate.require(contract.get("source_contract_manifest_sha256") == batch.SOURCE_CONTRACT_SHA256, "source binding mismatch", "contract")
    gate.require(smoke.sha256(batch.PRIOR_LEDGER) == batch.PRIOR_LEDGER_SHA256, "prior ledger hash mismatch", "lineage")
    gate.require(prior_ledger.get("status") == batch.PRIOR_LEDGER_STATUS, "prior ledger not merge-eligible", "lineage")
    gate.require(prior_ledger.get("batch_id") == batch.PRIOR_BATCH_ID, "prior batch ID mismatch", "lineage")
    gate.require(source_contract.get("families") == list(batch.ALL_SOURCE_FAMILIES), "canonical source family set mismatch", "contract")
    gate.require(source_contract.get("source_model", {}).get("profile") == "unit_only_total_gamma", "source profile mismatch", "contract")
    gate.require(source_contract.get("policies", {}).get("additive_mono_511_allowed") is False, "mono-511 policy mismatch", "contract")
    gate.require(contract.get("runner_sha256") == smoke.sha256(batch.RUNNER), "runner hash mismatch", "contract")
    for name, record in contract.get("toolchain", {}).items():
        path = common.resolve_repo_path(record.get("path", "__missing__"))
        gate.require(path.is_file() and smoke.sha256(path) == record.get("sha256"), f"toolchain hash mismatch: {name}", "contract")
    gate.require(
        contract.get("toolchain", {}).get("dynamic_validator", {}).get("sha256") == smoke.sha256(THIS_FILE),
        "dynamic validator self hash mismatch",
        "contract",
    )
    for key, value in {
        "gamma_events": batch.GAMMA_EVENTS,
        "gamma_splits": batch.GAMMA_SPLITS,
        "non_gamma_replicas": batch.NON_GAMMA_REPLICAS,
        "farfield_radius_cm": batch.FARFIELD_RADIUS_CM,
        "expected_jobs_per_campaign": batch.EXPECTED_JOBS_PER_CAMPAIGN,
    }.items():
        gate.require(contract.get("statistics", {}).get(key) == value, f"statistics {key} mismatch", "contract")
    gate.require(contract.get("source_scope", {}).get("included_families") == list(batch.FAMILIES), "seven-family scope mismatch", "contract")
    gate.require(contract.get("source_scope", {}).get("excluded_families") == ["p"], "proton exclusion mismatch", "contract")

    frozen_transport = contract.get("transport", {})
    cosima = smoke.resolve_cosima(frozen_transport.get("cosima"))
    environment, descriptor = smoke.resolve_transport_environment(cosima)
    current_transport = smoke.build_transport_fingerprint(cosima, environment, descriptor)
    for key in ("cosima", "cosima_sha256", "help_returncode", "help_banner_sha256", "shared_libraries", "shared_libraries_bundle_sha256"):
        gate.require(current_transport.get(key) == frozen_transport.get(key), f"transport {key} mismatch", "transport")
    for key in ("setup_script", "setup_script_sha256", "relevant_variables", "relevant_variables_sha256"):
        gate.require(
            current_transport.get("environment", {}).get(key) == frozen_transport.get("environment", {}).get(key),
            f"transport environment {key} mismatch",
            "transport",
        )
    # Access/metadata timestamps can legitimately change while Geant4 reads its
    # data files.  Freeze the path/size/content inventory, but do not make the
    # merge verdict depend on that volatile stat-only digest.
    def g4_core(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {key: value for key, value in item.items() if key != "stat_inventory_sha256"}
            for item in items
        ]

    gate.require(
        g4_core(current_transport.get("environment", {}).get("g4_data_roots", []))
        == g4_core(frozen_transport.get("environment", {}).get("g4_data_roots", [])),
        "transport environment g4_data_roots mismatch",
        "transport",
    )

    current_bundles: dict[str, dict[str, Any]] = {}
    for geometry in batch.GEOMETRIES:
        bundle = smoke.build_geometry_bundle(geometry, environment)
        current_bundles[geometry] = bundle
        gate.require(bundle == contract.get("geometry_bundles", {}).get(geometry), f"{geometry}: geometry bundle mismatch", "geometry")
        gate.require(
            common.source_contract_geometry_files(source_contract, geometry, environment) == bundle["files"],
            f"{geometry}: source/runtime geometry inventory mismatch",
            "geometry",
        )

    workers = contract.get("execution", {}).get("workers")
    gate.require(isinstance(workers, int) and workers > 0, "workers invalid", "contract")
    campaigns_index = {
        (item.get("geometry"), item.get("mode")): item for item in contract.get("campaigns", [])
    }
    expected_pairs = {(geometry, mode) for mode in batch.MODES for geometry in batch.GEOMETRIES}
    gate.require(set(campaigns_index) == expected_pairs and len(contract.get("campaigns", [])) == 4, "campaign set mismatch", "contract")
    for geometry, mode in sorted(expected_pairs):
        item = campaigns_index.get((geometry, mode), {})
        gate.require(item.get("expected_seeds") == batch.expected_seeds(mode), f"{geometry}/{mode}: seeds mismatch", "seeds")
        if isinstance(workers, int) and workers > 0:
            gate.require(item.get("command") == batch.runner_command(geometry, mode, workers, cosima), f"{geometry}/{mode}: command mismatch", "contract")

    prior_seeds = batch.prior_seed_registry(prior_ledger)
    instant = set(batch.expected_seeds("instant"))
    buildup = set(batch.expected_seeds("buildup"))
    gate.require(instant.isdisjoint(buildup), "batch0001 mode seed overlap", "seeds")
    gate.require((instant | buildup).isdisjoint(prior_seeds), "batch0001 overlaps batch0000 seeds", "seeds")
    gate.require(max(instant | buildup) < batch.RESERVED_FULL_TARGET_SEED_START, "batch0001 enters full-target seed namespace", "seeds")

    spectrum_hashes = {
        str(entry["corrected_spectrum"]): str(entry["corrected_sha256"])
        for entry in source_contract.get("spectra", {}).get("files", [])
    }
    gate.require(len(spectrum_hashes) == 160, "corrected spectrum hash inventory mismatch", "contract")
    campaigns: list[dict[str, Any]] = []
    for mode in batch.MODES:
        for geometry in batch.GEOMETRIES:
            try:
                campaigns.append(
                    validate_campaign(
                        gate,
                        geometry,
                        mode,
                        spectrum_hashes,
                        contract,
                        contract_hash,
                        current_bundles[geometry],
                    )
                )
            except Exception as exc:
                gate.problem(f"{geometry}/{mode}: validator exception {type(exc).__name__}: {exc}", "campaign_crash")
                campaigns.append({"geometry": geometry, "mode": mode, "status": "FAIL_VALIDATOR_EXCEPTION", "jobs": []})

    by_pair = {(item["geometry"], item["mode"]): item for item in campaigns}
    for mode in batch.MODES:
        mass = by_pair.get(("mass_model_511", mode), {})
        o8 = by_pair.get(("s3d_o8", mode), {})
        mass_signature = [(job.get("job_name"), job.get("events"), job.get("seed")) for job in mass.get("jobs", [])]
        o8_signature = [(job.get("job_name"), job.get("events"), job.get("seed")) for job in o8.get("jobs", [])]
        gate.require(
            mass_signature == o8_signature and len(mass_signature) == batch.EXPECTED_JOBS_PER_CAMPAIGN,
            f"{mode}: matched Mass/O8 stream mismatch",
            "paired_seeds",
        )

    total_jobs = sum(len(item.get("jobs", [])) for item in campaigns)
    total_events = sum(sum(int(job.get("events", 0)) for job in item.get("jobs", [])) for item in campaigns)
    status = "PASS" if not gate.errors else "FAIL"
    report = {
        "schema_version": 1,
        "status": status,
        "validator": smoke.rel(THIS_FILE),
        "validator_sha256": smoke.sha256(THIS_FILE),
        "batch_id": batch.BATCH_ID,
        "campaign_version": batch.CAMPAIGN_VERSION,
        "source_contract_manifest": smoke.rel(batch.SOURCE_CONTRACT),
        "source_contract_manifest_sha256": batch.SOURCE_CONTRACT_SHA256,
        "prior_merge_ledger": smoke.rel(batch.PRIOR_LEDGER),
        "prior_merge_ledger_sha256": batch.PRIOR_LEDGER_SHA256,
        "global_contract": smoke.rel(batch.GLOBAL_CONTRACT),
        "global_contract_sha256": contract_hash,
        "runner": smoke.rel(batch.RUNNER),
        "runner_sha256": smoke.sha256(batch.RUNNER),
        "transport": frozen_transport,
        "toolchain": contract.get("toolchain"),
        "checks": dict(sorted(gate.checks.items())),
        "errors": gate.errors,
        "campaign_count": len(campaigns),
        "validated_job_count": total_jobs,
        "validated_event_count": total_events,
        "campaigns": campaigns,
        "claims": {
            "corrected_source_transport": status == "PASS",
            "future_merge_eligibility": status == "PASS",
            "full_chain_or_geometry_promotion_authority": False,
        },
    }
    ledger = {
        "schema_version": 1,
        "status": "PASS__BATCH0001_MERGE_ELIGIBLE" if status == "PASS" else "FAIL_NOT_MERGE_ELIGIBLE",
        "batch_id": batch.BATCH_ID,
        "campaign_version": batch.CAMPAIGN_VERSION,
        "validation_report": smoke.rel(batch.VALIDATION_REPORT),
        "source_contract_manifest": smoke.rel(batch.SOURCE_CONTRACT),
        "source_contract_manifest_sha256": batch.SOURCE_CONTRACT_SHA256,
        "prior_batches": [
            {
                "batch_id": batch.PRIOR_BATCH_ID,
                "ledger": smoke.rel(batch.PRIOR_LEDGER),
                "ledger_sha256": batch.PRIOR_LEDGER_SHA256,
                "status": batch.PRIOR_LEDGER_STATUS,
            }
        ],
        "global_contract": smoke.rel(batch.GLOBAL_CONTRACT),
        "global_contract_sha256": contract_hash,
        "runner": smoke.rel(batch.RUNNER),
        "runner_sha256": smoke.sha256(batch.RUNNER),
        "validator": smoke.rel(THIS_FILE),
        "validator_sha256": smoke.sha256(THIS_FILE),
        "transport": frozen_transport,
        "toolchain": contract.get("toolchain"),
        "geometry_bundles": contract.get("geometry_bundles"),
        "pooling_boundary": "never pool across geometry, mode, or family",
        "prompt_merge_rule": "within one geometry+mode+family: rate = sum(selected) / sum(TT)",
        "activation_isotope_merge_rule": (
            "within one geometry+mode+family+production-volume+isotope-state: rate = sum(RP) / sum(TT)"
        ),
        "family_combination_rule": "sum separately normalized family rates; do not pool raw counts or TT",
        "TT_authority": "use positive matching DAT/log TT; events/(flux*pi*R^2) is expectation only",
        "zero_RP_rule": "include every registered family TT, including batches with no RP row for the isotope state",
        "seed_registry_rule": "future accepted batches must register seeds disjoint from batch0000 and batch0001",
        "excluded_family": "p",
        "errors": gate.errors,
        "campaigns": campaigns if status == "PASS" else [],
    }
    return report, ledger


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="read-only validation; do not write report/ledger")
    args = parser.parse_args()
    try:
        report, ledger = validate()
    except Exception as exc:
        report = {
            "schema_version": 1,
            "status": "FAIL",
            "validator": smoke.rel(THIS_FILE),
            "errors": [f"unexpected validator failure: {type(exc).__name__}: {exc}"],
        }
        ledger = {"schema_version": 1, "status": "FAIL_NOT_MERGE_ELIGIBLE", "errors": report["errors"]}
    if not args.check:
        smoke.atomic_json(batch.VALIDATION_REPORT, report)
        smoke.atomic_json(batch.MERGE_LEDGER, ledger)
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if report.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
