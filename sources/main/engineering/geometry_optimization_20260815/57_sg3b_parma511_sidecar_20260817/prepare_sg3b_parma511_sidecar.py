#!/usr/bin/env python3
"""Prepare a non-overwriting SG3B PARMA atmospheric 511-keV line sidecar.

This is a thin adapter around the retained, validated PARMA day-15 80-bin
source fragment and the canonical SG3B guarded executor.  It deliberately
does not include or reference a broadband photon continuum.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path("/home/ubuntu/TES_511_Balloon")
PROFILE_ID = "SG3B_PARMA511_MONO_3M_80BIN_20260817_V1"
DEFAULT_OUTPUT = Path("/mnt/data/TES_Balloon_511_data/SG3/sg3b_parma511_sidecar_3m_v1")
GEOMETRY = Path(
    "/home/ubuntu/.codex/worktrees/4f50/TES_511_Balloon/engineering/"
    "geometry_optimization_20260815/55_geoopt_sg3b_bi_halfcylinder_al_harness_20260816/"
    "geometry/DEMO2_DR_v3p5_SG3B.geo.setup"
)
LINE_DIR = REPO / (
    "engineering/m04_validation_geometry_handoff_20260810/"
    "02_parma_atm511_repair_20260810/line"
)
LINE_FRAGMENT = LINE_DIR / "PARMA_atm511_day15_fullsphere_80bins.inc.source"
LINE_CSV = LINE_DIR / "parma511_day15_80bins.csv"
LINE_CONTRACT = REPO / (
    "engineering/m04_validation_geometry_handoff_20260810/"
    "02_parma_atm511_repair_20260810/transport/line_only_transport_contract.json"
)
O8_CAMPAIGN = REPO / (
    "engineering/m04_validation_geometry_handoff_20260810/"
    "02_parma_atm511_repair_20260810/transport/campaigns/"
    "o8_parma511_line_nominal_180m_20260810/campaign_manifest.json"
)
DELAYED_REGISTRY = Path(
    "/mnt/data/TES_Balloon_511_data/SG3/sg3b_m05_delayed_1m_sharded_v2/"
    "generated/seed_registry.json"
)
CANONICAL_EXECUTOR = Path("/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute")
LINE_ENERGY_KEV = 510.99895
LINE_FLUX_4PI = 0.16651547160226118
SHARD_EVENTS = [50_000] + [250_000] * 11 + [200_000]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def collect_nested_seeds(value: Any, result: set[int]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"seed", "transport_seed"} and isinstance(item, int) and item > 0:
                result.add(item)
            collect_nested_seeds(item, result)
    elif isinstance(value, list):
        for item in value:
            collect_nested_seeds(item, result)


def collect_occupied_seeds() -> tuple[set[int], list[dict[str, Any]]]:
    occupied: set[int] = set()
    authorities: list[dict[str, Any]] = []
    delayed = json.loads(DELAYED_REGISTRY.read_text(encoding="utf-8"))
    collect_nested_seeds(delayed, occupied)

    paths = [Path(row["path"]) for row in delayed.get("authorities", [])]
    paths.append(DELAYED_REGISTRY)
    paths.append(O8_CAMPAIGN)
    seen: set[Path] = set()
    for path in paths:
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        before = len(occupied)
        if path.suffix == ".json":
            collect_nested_seeds(json.loads(path.read_text(encoding="utf-8")), occupied)
        elif path.suffix == ".csv":
            with path.open(newline="", encoding="utf-8") as handle:
                for row in csv.DictReader(handle):
                    for key, item in row.items():
                        if "seed" in key.lower() and str(item).isdigit() and int(item) > 0:
                            occupied.add(int(item))
        authorities.append(
            {
                "path": str(path),
                "sha256": sha256(path),
                "new_unique_seeds": len(occupied) - before,
            }
        )
    if len(occupied) < 695:
        raise RuntimeError(f"seed authority coverage unexpectedly small: {len(occupied)} < 695")
    return occupied, authorities


def fresh_seed(identity: str, occupied: set[int]) -> int:
    counter = 0
    while True:
        material = f"{PROFILE_ID}|{identity}|counter={counter}".encode("utf-8")
        value = 1 + int.from_bytes(hashlib.sha256(material).digest()[:8], "big") % 2_147_483_646
        if value not in occupied:
            occupied.add(value)
            return value
        counter += 1


def validate_authority() -> tuple[str, str, list[dict[str, str]]]:
    for path in (GEOMETRY, LINE_FRAGMENT, LINE_CSV, LINE_CONTRACT, O8_CAMPAIGN):
        if not path.is_file():
            raise FileNotFoundError(path)
    contract = json.loads(LINE_CONTRACT.read_text(encoding="utf-8"))
    if contract.get("line_energy_keV") != LINE_ENERGY_KEV:
        raise RuntimeError("line energy differs from retained transport contract")
    if contract.get("physical_angular_grid_equal_mu_bins") != 80:
        raise RuntimeError("retained transport contract is not the 80-bin grid")
    if not math.isclose(
        float(contract.get("physical_4pi_flux_ph_cm2_s", -1)),
        LINE_FLUX_4PI,
        rel_tol=0,
        abs_tol=1e-15,
    ):
        raise RuntimeError("line flux differs from retained transport contract")

    with LINE_CSV.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 80:
        raise RuntimeError(f"PARMA grid row count is {len(rows)}, expected 80")
    if [row["direction_label"] for row in rows].count("down") != 40:
        raise RuntimeError("PARMA down-going bin count is not 40")
    if [row["direction_label"] for row in rows].count("up") != 40:
        raise RuntimeError("PARMA up-going bin count is not 40")
    flux = sum(float(row["line_flux_ph_cm-2_s-1"]) for row in rows)
    fractions = sum(float(row["line_fraction"]) for row in rows)
    if not math.isclose(flux, LINE_FLUX_4PI, rel_tol=0, abs_tol=1e-15):
        raise RuntimeError(f"PARMA CSV flux sum drift: {flux}")
    if not math.isclose(fractions, 1.0, rel_tol=0, abs_tol=1e-15):
        raise RuntimeError(f"PARMA CSV line fractions do not close: {fractions}")
    evidence = [
        {"path": str(path), "sha256": sha256(path)}
        for path in (GEOMETRY, LINE_FRAGMENT, LINE_CSV, LINE_CONTRACT)
    ]
    return sha256(LINE_FRAGMENT), sha256(LINE_CSV), evidence


def source_text(job_id: str, events: int, seed: int, output_prefix: Path, fragment: str) -> str:
    bound_fragment = fragment.replace("PARMA511Day15", job_id)
    text = "\n".join(
        [
            "# SG3B standalone PARMA atmospheric annihilation-line sidecar.",
            "# Retained physical module: 80 equal-mu bins; mono 510.99895 keV.",
            "# It excludes the broadband continuum and must not be added to unit_only_total_gamma",
            "# without a separate flux-closed de-duplication/recomposition step.",
            f"Geometry {GEOMETRY}",
            "PhysicsListHD qgsp-bic-hp",
            "PhysicsListEM LivermorePol",
            "StoreSimulationInfo all",
            "StoreIsotopes false",
            "DetectorTimeConstant 1e-9",
            f"Seed {seed}",
            "",
            f"Run {job_id}",
            f"{job_id}.Events {events}",
            f"{job_id}.FileName {output_prefix}",
            "",
            bound_fragment.rstrip(),
            "",
        ]
    )
    if text.count(f"{job_id}.Source ") != 80:
        raise RuntimeError(f"{job_id}: source-binding count is not 80")
    if text.count(".Spectrum Mono 510.99895") != 80:
        raise RuntimeError(f"{job_id}: mono-energy row count is not 80")
    if text.count(".ParticleType 1") != 80:
        raise RuntimeError(f"{job_id}: gamma particle row count is not 80")
    if "Spectrum File" in text or "cosima_spectra_dp_2602units" in text:
        raise RuntimeError(f"{job_id}: forbidden broadband/legacy spectrum reference")
    flux = sum(
        float(line.rsplit(maxsplit=1)[-1])
        for line in text.splitlines()
        if ".Flux " in line and not line.lstrip().startswith("#")
    )
    if not math.isclose(flux, LINE_FLUX_4PI, rel_tol=0, abs_tol=1e-15):
        raise RuntimeError(f"{job_id}: source-card flux sum drift: {flux}")
    return text


def prepare(output: Path) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"non-overwrite gate: output already exists: {output}")
    if sum(SHARD_EVENTS) != 3_000_000:
        raise RuntimeError("shard events do not sum to 3,000,000")
    fragment_sha, csv_sha, authority_evidence = validate_authority()
    occupied, seed_authorities = collect_occupied_seeds()
    prior_seed_count = len(occupied)

    generated = output / "generated"
    sources = generated / "sources"
    run_root = output / "run"
    sources.mkdir(parents=True)
    run_root.mkdir(parents=True)
    fragment = LINE_FRAGMENT.read_text(encoding="utf-8")

    jobs: list[dict[str, Any]] = []
    seed_rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    for ordinal, events in enumerate(SHARD_EVENTS, 1):
        job_id = f"sg3b_parma511_shard{ordinal:04d}"
        identity = f"SG3B|background|parma511|shard{ordinal:04d}|events{events}"
        seed = fresh_seed(identity, occupied)
        output_prefix = run_root / "jobs" / job_id / "active" / job_id
        source_path = sources / f"{job_id}.source"
        source_path.write_text(
            source_text(job_id, events, seed, output_prefix, fragment),
            encoding="utf-8",
        )
        job = {
            "candidate": "SG3B",
            "estimated_bytes": 2 * 1024**3,
            "events": events,
            "family": "parma511",
            "job_id": job_id,
            "mode": "atm511",
            "ordinal": ordinal,
            "output_prefix": str(output_prefix),
            "production_canary": ordinal == 1,
            "requires_isotope_dat": False,
            "seed": seed,
            "setup_path": str(GEOMETRY),
            "source_path": str(source_path),
            "stage": "background",
        }
        jobs.append(job)
        seed_rows.append(
            {
                "job_id": job_id,
                "seed": seed,
                "seed_identity": identity,
                "collision_with_prior": False,
                "transport_seed_role": "FRESH_PER_SHARD_GEANT4_RANDOM_STREAM",
            }
        )
        source_rows.append(
            {
                **{key: job[key] for key in ("job_id", "mode", "family", "events", "seed", "source_path", "setup_path")},
                "source_sha256": sha256(source_path),
                "line_energy_keV": LINE_ENERGY_KEV,
                "angular_bins": 80,
                "physical_4pi_flux_ph_cm2_s": LINE_FLUX_4PI,
                "scope": "standalone_atmospheric_annihilation_line_only",
            }
        )

    totals = {"jobs": len(jobs), "instant_histories": 0, "buildup_histories": 0}
    dump(
        generated / "job_plan.json",
        {
            "schema_version": 1,
            "status": "PASS",
            "profile_id": PROFILE_ID,
            "candidate": "SG3B",
            "jobs": jobs,
            "totals": totals,
            "parma511_histories": sum(row["events"] for row in jobs),
        },
    )
    dump(
        generated / "seed_registry.json",
        {
            "schema_version": 1,
            "status": "PASS__FRESH_GLOBALLY_DISJOINT_PARMA511_SHARD_SEEDS",
            "profile_id": PROFILE_ID,
            "occupied_prior_seed_count": prior_seed_count,
            "fresh_seed_count": len(seed_rows),
            "authorities": seed_authorities,
            "seeds": seed_rows,
        },
    )
    dump(
        generated / "source_manifest.json",
        {
            "schema_version": 1,
            "status": "PASS__SG3B_PARMA511_80BIN_SOURCES",
            "profile_id": PROFILE_ID,
            "authority": authority_evidence,
            "line_fragment_sha256": fragment_sha,
            "parma_80bin_csv_sha256": csv_sha,
            "standalone_sidecar": True,
            "broadband_component_included": False,
            "additive_recomposition_authorized": False,
            "sources": source_rows,
        },
    )
    dump(
        generated / "preflight.json",
        {
            "schema_version": 1,
            "status": "PASS__SG3B_PARMA511_MONO_LINE_PREFLIGHT",
            "profile_id": PROFILE_ID,
            "candidate": "SG3B",
            "prepared_at": utc_now(),
            "job_plan": totals,
            "parma511_histories": 3_000_000,
            "line_energy_keV": LINE_ENERGY_KEV,
            "physical_4pi_flux_ph_cm2_s": LINE_FLUX_4PI,
            "physical_angular_grid_equal_mu_bins": 80,
            "geometry_setup": str(GEOMETRY),
            "geometry_setup_sha256": sha256(GEOMETRY),
            "scope": "standalone_line_sidecar__no_broadband_continuum",
            "recomposition_boundary": "DO_NOT_ADD_TO_UNIT_ONLY_TOTAL_GAMMA_WITHOUT_FLUX_CLOSED_DEDUPLICATION",
        },
    )

    config = {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "candidate": "SG3B",
        "display_title": "SG3B PARMA atmospheric mono-511 sidecar",
        "generated_root": str(generated),
        "run_root": str(run_root),
        "geometry_setup": str(GEOMETRY),
        "allowed_stages": ["background"],
        "expected_jobs": len(jobs),
        "expected_instant_histories": 0,
        "expected_buildup_histories": 0,
        "canary_job_id": jobs[0]["job_id"],
        "workers": 8,
        "max_workers": 8,
        "max_attempts": 2,
        "cosima": "/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima",
        "cosima_workdir": str(REPO),
        "megalib_environment": "/home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh",
        "poll_seconds": 2.0,
        "progress_interval_seconds": 2.0,
        "start_free_bytes": 100 * 1024**3,
        "dynamic_reserve_bytes": 64 * 1024**3,
        "launch_mem_available_bytes": int(1.5 * 1024**3),
        "runtime_mem_floor_bytes": int(1.5 * 1024**3),
        "launch_swap_free_bytes": 4 * 1024**3,
        "runtime_swap_floor_bytes": 1 * 1024**3,
        "launch_worker_reservation_bytes": int(1.25 * 1024**3),
        "aggregate_worker_rss_ceiling_bytes": 0,
        "launch_memory_full_psi_avg10_max": 100.0,
        "runtime_memory_full_psi_avg10_max": 100.0,
        "prepared_free_bytes": shutil.disk_usage(output).free,
        "source_policy": "standalone_parma511_mono_line_80bin",
        "forbidden_legacy_token": "cosima_spectra_dp_2602units",
        "seed_registry_pass_status": "PASS__FRESH_GLOBALLY_DISJOINT_PARMA511_SHARD_SEEDS",
        "source_manifest_pass_status": "PASS__SG3B_PARMA511_80BIN_SOURCES",
        "preflight_pass_status": "PASS__SG3B_PARMA511_MONO_LINE_PREFLIGHT",
    }
    dump(output / "config.json", config)
    summary = {
        "status": "PASS__SG3B_PARMA511_SIDECAR_PREPARED",
        "output": str(output),
        "config": str(output / "config.json"),
        "jobs": len(jobs),
        "events": sum(row["events"] for row in jobs),
        "workers": 8,
        "occupied_prior_seeds": prior_seed_count,
        "fresh_seeds": len(seed_rows),
        "executor": str(CANONICAL_EXECUTOR / "run.py"),
    }
    dump(output / "PREPARATION_RECEIPT.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(prepare(args.output.resolve()), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
