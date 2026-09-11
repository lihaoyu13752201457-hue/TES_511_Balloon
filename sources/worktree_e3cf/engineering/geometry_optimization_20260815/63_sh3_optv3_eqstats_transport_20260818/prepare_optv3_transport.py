#!/usr/bin/env python3
"""Prepare non-overwriting SH3 OptV3 corrected-keV and PARMA511 profiles.

The generated plans are consumed by the existing canonical run.py and
progress.py.  This file is a physics/source adapter, not an executor.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parent
EXECUTOR = Path("/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute")
GEOMETRY = REPO / (
    "engineering/geometry_optimization_20260815/sh3/assembly_opt_v3/geometry/"
    "SH3_Assembly_OptV3.geo.setup"
)
GEOMETRY_SHA256 = "52397889d6ac0d08296549942633ff09216cf1494fedb985127c48120d46eaea"
SOURCE_ROOT = REPO / (
    "engineering/particle_source_unit_repair_20260811/config/source_cards/s3d_o8"
)
SOURCE_CONTRACT = REPO / (
    "engineering/particle_source_unit_repair_20260811/data/source_contract_manifest.json"
)
SOURCE_STATIC = REPO / (
    "engineering/particle_source_unit_repair_20260811/data/static_validation.json"
)
OPT_STATIC = REPO / (
    "engineering/geometry_optimization_20260815/sh3/assembly_opt_v3/audit/"
    "assembly_opt_v3_static_validation.json"
)
OPT_OVERLAP = REPO / (
    "engineering/geometry_optimization_20260815/sh3/assembly_opt_v3/audit/"
    "assembly_opt_v3_overlap_validation.json"
)
SG3_INITIAL_PLAN = Path(
    "/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute/generated/job_plan.json"
)
SG3_EXTRA_PLAN = Path(
    "/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute/generated/"
    "sg3b_plan1_extra2x_v1/job_plan.json"
)
SG3_INITIAL_PLAN_SHA256 = "037bbec0815687381c1e40ea3f6f009982dd8c9faa936ddc24e7a833391f35de"
SG3_EXTRA_PLAN_SHA256 = "3c3a282b1f43205a183a8040f9a77a21f036f95b2f87f0b3d7d66f6e4e32059b"
SG3_CONFIG = EXECUTOR / "config.json"
LINE_ROOT = REPO / (
    "engineering/m04_validation_geometry_handoff_20260810/"
    "02_parma_atm511_repair_20260810"
)
LINE_FRAGMENT = LINE_ROOT / "line/PARMA_atm511_day15_fullsphere_80bins.inc.source"
LINE_CSV = LINE_ROOT / "line/parma511_day15_80bins.csv"
LINE_CONTRACT = LINE_ROOT / "transport/line_only_transport_contract.json"
LINE_FRAGMENT_SHA256 = "fc386a44b096d33d12d4a096532a3a57da5743681d93e779e653ae1349f776e6"
LINE_CSV_SHA256 = "2f4ae904bf89179fe1709e3a8123ff864f4450e8bcf443389898ea43cd6a5a32"
LINE_CONTRACT_SHA256 = "87e034405d46c0a928f4e4c2aa2c36030f110f7dc8ab4c843436bf195bf9357f"
LINE_ENERGY_KEV = 510.99895
LINE_FLUX_4PI = 0.16651547160226118
FAMILIES = ("p", "n", "alpha", "gamma", "eminus", "eplus", "muminus", "muplus")
SMOKE_EVENTS = {
    "p": 23,
    "n": 96,
    "alpha": 2,
    "gamma": 1000,
    "eminus": 41,
    "eplus": 24,
    "muminus": 1,
    "muplus": 1,
}
PARMA_PRODUCTION_EVENTS = [50_000] + [250_000] * 11 + [200_000]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def import_canonical_prepare():
    sys.path.insert(0, str(EXECUTOR))
    spec = importlib.util.spec_from_file_location("canonical_sg3_prepare", EXECUTOR / "prepare.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load canonical preparation helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def authority_gate() -> dict[str, Any]:
    pinned = {
        GEOMETRY: GEOMETRY_SHA256,
        SG3_INITIAL_PLAN: SG3_INITIAL_PLAN_SHA256,
        SG3_EXTRA_PLAN: SG3_EXTRA_PLAN_SHA256,
        LINE_FRAGMENT: LINE_FRAGMENT_SHA256,
        LINE_CSV: LINE_CSV_SHA256,
        LINE_CONTRACT: LINE_CONTRACT_SHA256,
    }
    for path, expected in pinned.items():
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"pinned authority mismatch: {path}")
    if load(SOURCE_STATIC).get("status") != "PASS":
        raise RuntimeError("corrected-keV static source authority is not PASS")
    if load(OPT_STATIC).get("status") != "PASS__SH3_ASSEMBLY_OPT_V3_STATIC":
        raise RuntimeError("OptV3 static authority is not PASS")
    overlap = load(OPT_OVERLAP)
    if (
        overlap.get("status") != "PASS__SH3_ASSEMBLY_OPT_V3_OVERLAP_NO_TRANSPORT"
        or overlap.get("transport_launched") is not False
    ):
        raise RuntimeError("OptV3 overlap authority mismatch")
    setup = GEOMETRY.read_text(encoding="utf-8")
    if setup.count("SurroundingSphere 95 0 0 8 95") != 1:
        raise RuntimeError("OptV3 source-surface contract drift")
    contract = load(SOURCE_CONTRACT)
    if contract.get("energy_contract", {}).get("output_energy_unit") != "keV_total":
        raise RuntimeError("source contract is not corrected total-keV")
    line = load(LINE_CONTRACT)
    if (
        line.get("line_energy_keV") != LINE_ENERGY_KEV
        or line.get("physical_angular_grid_equal_mu_bins") != 80
        or not math.isclose(
            float(line.get("physical_4pi_flux_ph_cm2_s", -1)),
            LINE_FLUX_4PI,
            rel_tol=0,
            abs_tol=1e-15,
        )
    ):
        raise RuntimeError("PARMA511 line contract drift")
    return {
        "geometry_setup": str(GEOMETRY),
        "geometry_setup_sha256": sha256(GEOMETRY),
        "surrounding_sphere": "95 0 0 8 95",
        "source_contract": str(SOURCE_CONTRACT),
        "source_contract_sha256": sha256(SOURCE_CONTRACT),
        "source_static": str(SOURCE_STATIC),
        "optv3_static": str(OPT_STATIC),
        "optv3_overlap": str(OPT_OVERLAP),
        "sg3_initial_plan_sha256": sha256(SG3_INITIAL_PLAN),
        "sg3_extra_plan_sha256": sha256(SG3_EXTRA_PLAN),
    }


def occupied_seed_authority(
    canonical, additional_registries: list[Path]
) -> tuple[set[int], dict[str, Any]]:
    config = load(SG3_CONFIG)
    occupied, audit = canonical.occupied_seeds(config)
    extra_paths = [
        EXECUTOR / "generated/seed_registry.json",
        EXECUTOR / "generated/sg3b_plan1_extra2x_v1/seed_registry.json",
    ]
    for path in extra_paths:
        payload = load(path)
        for row in payload.get("seeds", []):
            seed = row.get("seed")
            if isinstance(seed, int) and seed > 0:
                occupied.add(seed)
    for path in additional_registries:
        if not path.is_file():
            raise FileNotFoundError(f"additional seed registry not found: {path}")
        payload = load(path)
        rows = payload.get("seeds")
        if not isinstance(rows, list):
            raise RuntimeError(f"additional seed registry lacks rows: {path}")
        for row in rows:
            seed = row.get("seed") if isinstance(row, dict) else None
            if not isinstance(seed, int) or seed <= 0:
                raise RuntimeError(f"invalid seed row in {path}")
            occupied.add(seed)
    audit = dict(audit)
    audit.update(
        checked_additional_seed_registries=[str(path) for path in extra_paths],
        checked_user_seed_registries=[str(path) for path in additional_registries],
        occupied_seed_count_after_additional=len(occupied),
    )
    return occupied, audit


def corrected_cells(kind: str) -> list[dict[str, Any]]:
    if kind == "smoke":
        rows = []
        ordinal = 0
        for mode in ("instant", "buildup"):
            for family in FAMILIES:
                ordinal += 1
                rows.append(
                    {
                        "batch_id": "smoke0000",
                        "ordinal": ordinal,
                        "mode": mode,
                        "family": family,
                        "shard": 1,
                        "events": SMOKE_EVENTS[family],
                        "target_histories": SMOKE_EVENTS[family],
                        "estimated_bytes": 256 * 1024**2,
                    }
                )
        return rows
    rows = []
    ordinal = 0
    for batch_id, path in (("initial", SG3_INITIAL_PLAN), ("extra2x", SG3_EXTRA_PLAN)):
        for source in load(path)["jobs"]:
            if batch_id == "initial" and source["mode"] == "buildup" and source["family"] == "alpha":
                continue
            ordinal += 1
            rows.append(
                {
                    "batch_id": batch_id,
                    "ordinal": ordinal,
                    "mode": source["mode"],
                    "family": source["family"],
                    "shard": source["shard"],
                    "events": source["events"],
                    "target_histories": source["events"],
                    "estimated_bytes": source["estimated_bytes"],
                    "sg3b_source_job_id": source["job_id"],
                }
            )
    instant = sum(row["events"] for row in rows if row["mode"] == "instant")
    buildup = sum(row["events"] for row in rows if row["mode"] == "buildup")
    if len(rows) != 41 or instant != 3_842_079 or buildup != 3_045_028:
        raise RuntimeError("canonical accepted-cell target drift")
    return rows


def build_corrected(
    kind: str,
    root: Path,
    canonical,
    occupied: set[int],
    seed_audit: dict[str, Any],
    authority: dict[str, Any],
) -> dict[str, Any]:
    profile = f"SH3_OPTV3_{kind.upper()}_CORRECTED_KEV_20260818_V1"
    generated = root / "generated"
    run_root = root / "run"
    sources_dir = generated / "sources"
    sources_dir.mkdir(parents=True)
    run_root.mkdir(parents=True)
    jobs = []
    seed_rows = []
    source_rows = []
    for cell in corrected_cells(kind):
        batch = cell["batch_id"]
        mode = cell["mode"]
        family = cell["family"]
        shard = cell["shard"]
        job_id = f"optv3_{batch}_{mode}_{family}_shard{shard:04d}"
        run_name = f"OptV3_{batch}_{mode}_{family}_{shard:04d}"
        seed = canonical.derive_seed(profile, job_id, occupied)
        source_path = sources_dir / f"{job_id}.source"
        output_prefix = run_root / "jobs" / job_id / "active" / job_id
        base_path = SOURCE_ROOT / f"Background_{family}_fullsphere20.source"
        patch_config = {
            "corrected_token": "engineering/particle_source_unit_repair_20260811/spectra/correct_keV_total/",
            "forbidden_legacy_token": "cosima_spectra_dp_2602units",
        }
        text = canonical.patch_source(
            base_path.read_text(encoding="utf-8"),
            setup=GEOMETRY,
            output_prefix=output_prefix,
            job_id=job_id,
            run_name=run_name,
            mode=mode,
            seed=seed,
            events=cell["events"],
            config=patch_config,
        )
        text = text.replace("# farfield_radius_cm=60", "# farfield_radius_cm=95")
        source_path.write_text(text, encoding="utf-8")
        job = {
            **cell,
            "job_id": job_id,
            "stage": "background",
            "candidate": "SH3_OptV3",
            "seed": seed,
            "source_path": str(source_path),
            "setup_path": str(GEOMETRY),
            "output_prefix": str(output_prefix),
            "production_canary": (
                mode == "instant" and family == "gamma" and shard == 1 and batch in {"smoke0000", "initial"}
            ),
        }
        jobs.append(job)
        seed_rows.append({"job_id": job_id, "seed": seed, "namespace": profile})
        source_rows.append(
            {
                **{key: job[key] for key in ("job_id", "mode", "family", "events", "seed", "source_path", "setup_path")},
                "source_sha256": sha256(source_path),
                "corrected_spectrum_references": text.count(".Spectrum File "),
                "legacy_spectrum_references": text.count("cosima_spectra_dp_2602units"),
                "source_surface_radius_cm": 95.0,
            }
        )
    if sum(bool(job["production_canary"]) for job in jobs) != 1:
        raise RuntimeError("corrected profile must have exactly one canary")
    totals = {
        "jobs": len(jobs),
        "instant_histories": sum(job["events"] for job in jobs if job["mode"] == "instant"),
        "buildup_histories": sum(job["events"] for job in jobs if job["mode"] == "buildup"),
    }
    dump(generated / "job_plan.json", {"schema_version": 1, "profile_id": profile, "candidate": "SH3_OptV3", "status": "PASS", "scope": "CORRECTED_KEV_INSTANT_AND_BUILDUP", "jobs": jobs, "totals": totals})
    dump(generated / "seed_registry.json", {"schema_version": 1, "profile_id": profile, "status": "PASS__FRESH_GLOBALLY_DISJOINT_SEEDS", "seeds": seed_rows, "authority": seed_audit})
    dump(generated / "source_manifest.json", {"schema_version": 1, "profile_id": profile, "status": "PASS__SH3_OPTV3_CORRECTED_BACKGROUND_SOURCES", "gamma_profile": "unit_only_total_gamma", "additive_mono511": False, "sources": source_rows, "authority": authority})
    preflight = {"schema_version": 1, "profile_id": profile, "status": "PASS__SH3_OPTV3_BACKGROUND_TRANSPORT_PREFLIGHT", "checked_at": utc_now(), "candidate": "SH3_OptV3", "authority": authority, "job_plan": totals, "source_manifest_status": "PASS__SH3_OPTV3_CORRECTED_BACKGROUND_SOURCES", "seed_registry_status": "PASS__FRESH_GLOBALLY_DISJOINT_SEEDS", "workers": 6, "resource_snapshot": {"disk_free_bytes": shutil.disk_usage(root).free}, "veto_boundary": "POSTPROCESS_ONLY__NOT_A_TRANSPORT_GATE"}
    dump(generated / "preflight.json", preflight)
    estimated_total = sum(job["estimated_bytes"] for job in jobs)
    start_gate = (12 * 1024**3) if kind == "smoke" else estimated_total + 20 * 1024**3
    config = {
        "schema_version": 1,
        "profile_id": profile,
        "candidate": "SH3_OptV3",
        "display_title": f"SH3 OptV3 {kind} corrected-keV background",
        "generated_root": str(generated),
        "run_root": str(run_root),
        "geometry_setup": str(GEOMETRY),
        "allowed_stages": ["background"],
        "expected_jobs": len(jobs),
        "expected_instant_histories": totals["instant_histories"],
        "expected_buildup_histories": totals["buildup_histories"],
        "canary_job_id": next(job["job_id"] for job in jobs if job["production_canary"]),
        "workers": 6,
        "max_workers": 8,
        "max_attempts": 2,
        "cosima": "/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima",
        "cosima_workdir": str(REPO),
        "megalib_environment": "/home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh",
        "poll_seconds": 2.0,
        "progress_interval_seconds": 2.0,
        "start_free_bytes": start_gate,
        "dynamic_reserve_bytes": 8 * 1024**3 if kind == "smoke" else 20 * 1024**3,
        "launch_mem_available_bytes": int(1.5 * 1024**3),
        "runtime_mem_floor_bytes": 1 * 1024**3,
        "launch_swap_free_bytes": 4 * 1024**3,
        "runtime_swap_floor_bytes": 1 * 1024**3,
        "launch_worker_reservation_bytes": 1 * 1024**3,
        "aggregate_worker_rss_ceiling_bytes": 0,
        "launch_memory_full_psi_avg10_max": 100.0,
        "runtime_memory_full_psi_avg10_max": 100.0,
        "source_policy": "corrected_keV_background",
        "corrected_token": "engineering/particle_source_unit_repair_20260811/spectra/correct_keV_total/",
        "forbidden_legacy_token": "cosima_spectra_dp_2602units",
        "seed_registry_pass_status": "PASS__FRESH_GLOBALLY_DISJOINT_SEEDS",
        "source_manifest_pass_status": "PASS__SH3_OPTV3_CORRECTED_BACKGROUND_SOURCES",
        "preflight_pass_status": "PASS__SH3_OPTV3_BACKGROUND_TRANSPORT_PREFLIGHT",
    }
    dump(root / "config.json", config)
    return {"profile_id": profile, "root": str(root), "config": str(root / "config.json"), "jobs": len(jobs), "events": totals["instant_histories"] + totals["buildup_histories"], "estimated_artifact_bytes": estimated_total, "workers": 6}


def parma_source(job_id: str, events: int, seed: int, output_prefix: Path, fragment: str) -> str:
    bound = fragment.replace("PARMA511Day15", job_id)
    text = "\n".join(
        [
            "# SH3 OptV3 standalone PARMA atmospheric annihilation-line sidecar.",
            "# NON_ADDITIVE_SIDECAR: do not add to unit_only_total_gamma.",
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
            bound.rstrip(),
            "",
        ]
    )
    if text.count(f"{job_id}.Source ") != 80 or text.count(".Spectrum Mono 510.99895") != 80:
        raise RuntimeError("PARMA source binding/energy count drift")
    if "Spectrum File" in text or "cosima_spectra_dp_2602units" in text:
        raise RuntimeError("PARMA sidecar contains broadband/legacy spectrum")
    flux = sum(float(line.rsplit(maxsplit=1)[-1]) for line in text.splitlines() if ".Flux " in line and not line.lstrip().startswith("#"))
    if not math.isclose(flux, LINE_FLUX_4PI, rel_tol=0, abs_tol=1e-15):
        raise RuntimeError("PARMA source flux drift")
    return text


def build_parma(
    kind: str,
    root: Path,
    canonical,
    occupied: set[int],
    seed_audit: dict[str, Any],
    authority: dict[str, Any],
) -> dict[str, Any]:
    profile = f"SH3_OPTV3_{kind.upper()}_PARMA511_20260818_V1"
    generated = root / "generated"
    run_root = root / "run"
    sources_dir = generated / "sources"
    sources_dir.mkdir(parents=True)
    run_root.mkdir(parents=True)
    events_rows = [1000] if kind == "smoke" else PARMA_PRODUCTION_EVENTS
    fragment = LINE_FRAGMENT.read_text(encoding="utf-8")
    jobs = []
    seeds = []
    source_rows = []
    for ordinal, events in enumerate(events_rows, 1):
        job_id = f"optv3_{kind}_parma511_shard{ordinal:04d}"
        seed = canonical.derive_seed(profile, job_id, occupied)
        output_prefix = run_root / "jobs" / job_id / "active" / job_id
        source_path = sources_dir / f"{job_id}.source"
        text = parma_source(job_id, events, seed, output_prefix, fragment)
        source_path.write_text(text, encoding="utf-8")
        job = {
            "candidate": "SH3_OptV3",
            "estimated_bytes": 256 * 1024**2 if kind == "smoke" else 2 * 1024**3,
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
        seeds.append({"job_id": job_id, "seed": seed, "namespace": profile})
        source_rows.append({**{key: job[key] for key in ("job_id", "mode", "family", "events", "seed", "source_path", "setup_path")}, "source_sha256": sha256(source_path), "line_energy_keV": LINE_ENERGY_KEV, "angular_bins": 80, "physical_4pi_flux_ph_cm2_s": LINE_FLUX_4PI, "scope": "NON_ADDITIVE_SIDECAR"})
    totals = {"jobs": len(jobs), "instant_histories": 0, "buildup_histories": 0}
    dump(generated / "job_plan.json", {"schema_version": 1, "profile_id": profile, "candidate": "SH3_OptV3", "status": "PASS", "scope": "NON_ADDITIVE_PARMA511_SIDECAR", "jobs": jobs, "totals": totals, "parma511_histories": sum(events_rows)})
    dump(generated / "seed_registry.json", {"schema_version": 1, "profile_id": profile, "status": "PASS__FRESH_GLOBALLY_DISJOINT_PARMA511_SHARD_SEEDS", "seeds": seeds, "authority": seed_audit})
    dump(generated / "source_manifest.json", {"schema_version": 1, "profile_id": profile, "status": "PASS__SH3_OPTV3_PARMA511_80BIN_SOURCES", "standalone_sidecar": True, "broadband_component_included": False, "additive_recomposition_authorized": False, "sources": source_rows, "authority": authority})
    preflight = {"schema_version": 1, "profile_id": profile, "status": "PASS__SH3_OPTV3_PARMA511_MONO_LINE_PREFLIGHT", "checked_at": utc_now(), "candidate": "SH3_OptV3", "authority": authority, "job_plan": totals, "parma511_histories": sum(events_rows), "source_manifest_status": "PASS__SH3_OPTV3_PARMA511_80BIN_SOURCES", "seed_registry_status": "PASS__FRESH_GLOBALLY_DISJOINT_PARMA511_SHARD_SEEDS", "workers": 8, "scope": "NON_ADDITIVE_SIDECAR"}
    dump(generated / "preflight.json", preflight)
    config = {
        "schema_version": 1,
        "profile_id": profile,
        "candidate": "SH3_OptV3",
        "display_title": f"SH3 OptV3 {kind} PARMA511 sidecar",
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
        "start_free_bytes": 12 * 1024**3 if kind == "smoke" else 24 * 1024**3,
        "dynamic_reserve_bytes": 8 * 1024**3 if kind == "smoke" else 20 * 1024**3,
        "launch_mem_available_bytes": int(1.5 * 1024**3),
        "runtime_mem_floor_bytes": 1 * 1024**3,
        "launch_swap_free_bytes": 4 * 1024**3,
        "runtime_swap_floor_bytes": 1 * 1024**3,
        "launch_worker_reservation_bytes": 1 * 1024**3,
        "aggregate_worker_rss_ceiling_bytes": 0,
        "launch_memory_full_psi_avg10_max": 100.0,
        "runtime_memory_full_psi_avg10_max": 100.0,
        "source_policy": "standalone_parma511_mono_line_80bin",
        "forbidden_legacy_token": "cosima_spectra_dp_2602units",
        "seed_registry_pass_status": "PASS__FRESH_GLOBALLY_DISJOINT_PARMA511_SHARD_SEEDS",
        "source_manifest_pass_status": "PASS__SH3_OPTV3_PARMA511_80BIN_SOURCES",
        "preflight_pass_status": "PASS__SH3_OPTV3_PARMA511_MONO_LINE_PREFLIGHT",
    }
    dump(root / "config.json", config)
    return {"profile_id": profile, "root": str(root), "config": str(root / "config.json"), "jobs": len(jobs), "events": sum(events_rows), "workers": 8, "scope": "NON_ADDITIVE_SIDECAR"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=("smoke", "production"), required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--additional-seed-registry", type=Path, action="append", default=[]
    )
    args = parser.parse_args()
    output = args.output_root.resolve()
    if output.exists():
        raise FileExistsError(f"non-overwrite gate: {output}")
    output.mkdir(parents=True)
    canonical = import_canonical_prepare()
    authority = authority_gate()
    occupied, seed_audit = occupied_seed_authority(
        canonical, [path.resolve() for path in args.additional_seed_registry]
    )
    corrected = build_corrected(args.kind, output / "corrected_kev", canonical, occupied, seed_audit, authority)
    parma = build_parma(args.kind, output / "parma511", canonical, occupied, seed_audit, authority)
    umbrella = {
        "schema_version": 1,
        "status": f"PASS__SH3_OPTV3_{args.kind.upper()}_PROFILES_PREPARED",
        "prepared_at": utc_now(),
        "kind": args.kind,
        "geometry_setup": str(GEOMETRY),
        "geometry_setup_sha256": sha256(GEOMETRY),
        "corrected_kev": corrected,
        "parma511": parma,
        "parma511_composition": "NON_ADDITIVE_SIDECAR",
        "executor": str(EXECUTOR / "run.py"),
        "progress": str(EXECUTOR / "progress.py"),
    }
    dump(output / "PREPARATION_RECEIPT.json", umbrella)
    print(json.dumps(umbrella, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
