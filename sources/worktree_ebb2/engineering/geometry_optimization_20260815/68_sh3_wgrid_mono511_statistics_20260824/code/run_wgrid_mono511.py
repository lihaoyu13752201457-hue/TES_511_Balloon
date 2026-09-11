#!/usr/bin/env python3
"""Prepare, run, and validate the SH3+W-grid PARMA mono-511 campaign.

The production campaign is deliberately line-only.  It uses the same
15,709,417 incident photons, 60 cm source surface, day-15 80-bin PARMA line,
and guarded Cosima executor as the promoted open-frame SH3 comparator.
Nothing in the open-frame geometry or its response products is modified.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve()
PACKAGE = HERE.parents[1]
REPO = PACKAGE.parents[2]

GEOMETRY_SOURCE = REPO / (
    "engineering/geometry_optimization_20260815/sh3/"
    "assembly_opt_v3_wgrid_20260824"
)
SOURCE_SOURCE = REPO / (
    "engineering/m04_validation_geometry_handoff_20260810/"
    "02_parma_atm511_repair_20260810"
)
COMPARATOR_ROOT = REPO / (
    "engineering/geometry_optimization_20260815/"
    "67_m05_mono511_flux_closure_20260823/outputs/01_line_response_b60"
)
EXECUTOR = Path("/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute")
RUNNER = EXECUTOR / "run.py"
COSIMA = Path("/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima")
MEGALIB_ENVIRONMENT = Path(
    "/home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh"
)

AUTHORITY = PACKAGE / "transport_authority"
GEOMETRY = AUTHORITY / "geometry"
LINE_AUTHORITY = AUTHORITY / "parma_line"
SETUP = GEOMETRY / "SH3_Assembly_OptV3_WGrid_60cm.geo.setup"
GEO = GEOMETRY / "SH3_Assembly_OptV3.geo"
DET = GEOMETRY / "SH3_Assembly_OptV3.det"
MATERIALS = GEOMETRY / "Materials_SH3_Assembly_OptV3.geo"
LINE_FRAGMENT = LINE_AUTHORITY / "PARMA_atm511_day15_fullsphere_80bins.inc.source"
LINE_CONTRACT = LINE_AUTHORITY / "line_only_transport_contract.json"

SMOKE_ROOT = PACKAGE / "transport_smoke"
FULL_ROOT = PACKAGE / "transport_full"
FULL_EVENTS = 15_709_417
LINE_ENERGY_KEV = 510.99895
LINE_FLUX_4PI = 0.16651547160226118
SURFACE = "60 5 0 9 60"

EXPECTED = {
    "geometry_geo": "d6392df0d13692b9b238e839296939de6336dcb66c6fe2b1b99b2226281d6daf",
    "geometry_det": "12d3a6831f3d00da6668f48487e5d83f7a0354419fdec75cfec211b28373cae9",
    "geometry_materials": "56f6c2b58f072f4350a1fed8707490ed4f0b196769a9a4e22e0acb2ebe58ae0a",
    "line_fragment": "fc386a44b096d33d12d4a096532a3a57da5743681d93e779e653ae1349f776e6",
    "line_contract": "87e034405d46c0a928f4e4c2aa2c36030f110f7dc8ab4c843436bf195bf9357f",
    "normalized_fragment": "91463c9f6c6be08ec974354860ac6470e4d7e32e97b56ea459dedbc0ed4382a0",
    "response_config": "e2780f3ff5fa85f45403661ac939eaa94331daa6dfa79fe62a062229bce84d53",
    "response_builder": "f6d968e8804ed3b64e127786da9c376502d2c7bb85405a7949a8c1c4bb80b401",
}

RESPONSE_CONFIG = REPO / "DEEPSEEK_CODE/modified/analysis_inputs_optv3_B.json"
RESPONSE_BUILDER = REPO / "DEEPSEEK_CODE/modified/build_event_catalog_sh3_step05.py"
RESPONSE_SIDE_COMPTON = REPO / "DEEPSEEK_CODE/modified/step05_side_compton.py"
GEOMETRY_MANIFEST = GEOMETRY_SOURCE / "data/assembly_opt_v3_wgrid_manifest.json"
GEOMETRY_STATIC = GEOMETRY_SOURCE / "audit/assembly_opt_v3_wgrid_static_validation.json"
GEOMETRY_OVERLAP = GEOMETRY_SOURCE / "audit/assembly_opt_v3_wgrid_overlap_validation.json"
GEOMETRY_WRL_VALIDATION = GEOMETRY_SOURCE / "audit/assembly_opt_v3_wgrid_wrl_export_validation.json"
GEOMETRY_WRL = GEOMETRY_SOURCE / "figures/SH3_Chimney_DR_Assembly_OptV3_WGrid.wrl"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.{os.getpid()}.partial")
    partial.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(partial, path)


def write_once(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != content:
            raise RuntimeError(f"write-once conflict: {path}")
        return
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def assert_hash(path: Path, expected: str, label: str) -> None:
    observed = sha256(path)
    if observed != expected:
        raise RuntimeError(f"{label} hash drift: {observed} != {expected}")


def file_record(path: Path) -> dict[str, Any]:
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": sha256(path)}


def normalized_fragment(text: str, run_id: str) -> list[str]:
    prefix = f"{run_id}.Source "
    rows: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith(prefix):
            rows.append("PARMA511Day15.Source " + line[len(prefix):])
        elif line.startswith("PARMA511_bin"):
            rows.append(line)
    return rows


def normalized_fragment_sha(text: str, run_id: str) -> str:
    rows = normalized_fragment(text, run_id)
    if len(rows) != 400:
        raise RuntimeError(f"PARMA normalized fragment has {len(rows)} rows, expected 400")
    return hashlib.sha256(("\n".join(rows) + "\n").encode("utf-8")).hexdigest()


def validate_surface() -> dict[str, Any]:
    points: list[tuple[float, float, float]] = []
    inside = False
    triple = re.compile(r"\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+),?\s*$")
    with GEOMETRY_WRL.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if "point [" in line:
                inside = True
                continue
            if inside and "]" in line:
                inside = False
                continue
            if inside and (match := triple.match(line)):
                points.append(tuple(float(value) / 10.0 for value in match.groups()))
    if not points:
        raise RuntimeError("native W-grid WRL contains no vertices")
    center = (5.0, 0.0, 9.0)
    distances = [math.dist(point, center) for point in points]
    farthest = max(range(len(points)), key=distances.__getitem__)
    hidden = sorted({
        line.split(".Visibility", 1)[0]
        for line in GEO.read_text(encoding="utf-8").splitlines()
        if line.endswith(".Visibility 0")
    })
    allowed = ("WorldVolume", "InstrumentFrame", "TES_L", "TP_L", "W_Multihole_CollimatorVac")
    unexpected = [name for name in hidden if not name.startswith(allowed)]
    maximum = distances[farthest]
    checks = {
        "setup_exact_60cm_surface": SETUP.read_text(encoding="utf-8").count(
            f"SurroundingSphere {SURFACE}"
        ) == 1,
        "visible_vertices_present": bool(points),
        "visible_vertices_inside_surface": maximum < 60.0,
        "positive_radial_margin": 60.0 - maximum > 0.0,
        "hidden_classes_expected": not unexpected,
    }
    payload = {
        "schema_version": 1,
        "status": "PASS__SH3_WGRID_60CM_SURFACE_ENCLOSES_GEOMETRY" if all(checks.values()) else "FAIL",
        "generated_at_utc": utc_now(),
        "checks": checks,
        "surface": {"radius_cm": 60.0, "center_cm": center, "contract": SURFACE},
        "native_wrl": {
            **file_record(GEOMETRY_WRL),
            "vertex_count": len(points),
            "maximum_radius_cm": maximum,
            "radial_margin_cm": 60.0 - maximum,
            "farthest_vertex_cm": points[farthest],
            "axis_bounds_cm": {
                axis: [min(point[index] for point in points), max(point[index] for point in points)]
                for index, axis in enumerate(("x", "y", "z"))
            },
        },
        "hidden_geometry": {"count": len(hidden), "unexpected": unexpected},
        "setup": file_record(SETUP),
    }
    if not payload["status"].startswith("PASS"):
        raise RuntimeError(json.dumps(payload, indent=2))
    return payload


def prepare_authority() -> dict[str, Any]:
    receipt = PACKAGE / "audit/authority_receipt.json"
    if receipt.is_file():
        payload = load_json(receipt)
        if payload.get("status") != "PASS__SH3_WGRID_MONO511_AUTHORITY_FROZEN":
            raise RuntimeError("existing authority receipt is not PASS")
        return payload
    required = [
        GEOMETRY_SOURCE / "geometry/SH3_Assembly_OptV3.geo",
        GEOMETRY_SOURCE / "geometry/SH3_Assembly_OptV3.det",
        GEOMETRY_SOURCE / "geometry/Materials_SH3_Assembly_OptV3.geo",
        SOURCE_SOURCE / "line/PARMA_atm511_day15_fullsphere_80bins.inc.source",
        SOURCE_SOURCE / "transport/line_only_transport_contract.json",
        GEOMETRY_MANIFEST, GEOMETRY_STATIC, GEOMETRY_OVERLAP,
        GEOMETRY_WRL_VALIDATION, GEOMETRY_WRL, RESPONSE_CONFIG, RESPONSE_BUILDER,
        COMPARATOR_ROOT / "summary.json", COMPARATOR_ROOT / "MERGE_RECEIPT.json",
    ]
    if any(not path.is_file() for path in required):
        missing = [str(path) for path in required if not path.is_file()]
        raise FileNotFoundError(f"authority file missing: {missing}")
    if AUTHORITY.exists():
        raise FileExistsError(f"partial authority directory requires inspection: {AUTHORITY}")
    GEOMETRY.mkdir(parents=True)
    LINE_AUTHORITY.mkdir(parents=True)
    shutil.copy2(required[0], GEO)
    shutil.copy2(required[1], DET)
    shutil.copy2(required[2], MATERIALS)
    shutil.copy2(required[3], LINE_FRAGMENT)
    shutil.copy2(required[4], LINE_CONTRACT)
    write_once(
        SETUP,
        "Name SH3_Chimney_DR_Assembly_OptV3_WGrid_60cm\n"
        "Version 1\n"
        "Include SH3_Assembly_OptV3.geo\n"
        "Include SH3_Assembly_OptV3.det\n"
        f"SurroundingSphere {SURFACE}\n",
    )
    assert_hash(GEO, EXPECTED["geometry_geo"], "W-grid geometry")
    assert_hash(DET, EXPECTED["geometry_det"], "W-grid detector map")
    assert_hash(MATERIALS, EXPECTED["geometry_materials"], "W-grid materials")
    assert_hash(LINE_FRAGMENT, EXPECTED["line_fragment"], "PARMA line fragment")
    assert_hash(LINE_CONTRACT, EXPECTED["line_contract"], "PARMA line contract")
    assert_hash(RESPONSE_CONFIG, EXPECTED["response_config"], "B response config")
    assert_hash(RESPONSE_BUILDER, EXPECTED["response_builder"], "B response builder")
    if normalized_fragment_sha(LINE_FRAGMENT.read_text(encoding="utf-8"), "PARMA511Day15") != EXPECTED["normalized_fragment"]:
        raise RuntimeError("normalized PARMA fragment contract drift")
    line = load_json(LINE_CONTRACT)
    if not math.isclose(float(line["line_energy_keV"]), LINE_ENERGY_KEV, rel_tol=0, abs_tol=1e-12):
        raise RuntimeError("PARMA line energy drift")
    if not math.isclose(float(line["physical_4pi_flux_ph_cm2_s"]), LINE_FLUX_4PI, rel_tol=0, abs_tol=1e-15):
        raise RuntimeError("PARMA line flux drift")
    for path, expected_status in (
        (GEOMETRY_MANIFEST, "PASS__SH3_ASSEMBLY_OPT_V3_WGRID_BUILT"),
        (GEOMETRY_STATIC, "PASS__SH3_ASSEMBLY_OPT_V3_WGRID_STATIC"),
        (GEOMETRY_OVERLAP, "PASS__SH3_ASSEMBLY_OPT_V3_WGRID_OVERLAP_NO_TRANSPORT"),
        (GEOMETRY_WRL_VALIDATION, "PASS__SH3_ASSEMBLY_OPT_V3_WGRID_NATIVE_WRL_NO_TRANSPORT"),
    ):
        if load_json(path).get("status") != expected_status:
            raise RuntimeError(f"geometry authority not PASS: {path}")
    surface = validate_surface()
    atomic_json(PACKAGE / "audit/source_surface_60cm_validation.json", surface)
    comparator = load_json(COMPARATOR_ROOT / "summary.json")
    if int(comparator["incident_photons"]) != FULL_EVENTS:
        raise RuntimeError("promoted SH3 comparator incident count drift")
    payload = {
        "schema_version": 1,
        "status": "PASS__SH3_WGRID_MONO511_AUTHORITY_FROZEN",
        "generated_at_utc": utc_now(),
        "scope": "monoenergetic atmospheric 511 keV transport and common response only",
        "geometry": {"setup": file_record(SETUP), "geo": file_record(GEO), "det": file_record(DET), "materials": file_record(MATERIALS)},
        "source": {
            "provider": "PARMA dedicated atmospheric annihilation-line parameterization",
            "atmospheric_state": "day-15 reference state shared with the broadband field",
            "line_energy_keV": LINE_ENERGY_KEV,
            "full_space_flux_ph_cm2_s": LINE_FLUX_4PI,
            "equal_mu_components": 80,
            "source_surface": SURFACE,
            "fragment": file_record(LINE_FRAGMENT),
            "line_contract": file_record(LINE_CONTRACT),
            "normalized_fragment_sha256": EXPECTED["normalized_fragment"],
        },
        "response_authority": {
            "config": file_record(RESPONSE_CONFIG),
            "builder": file_record(RESPONSE_BUILDER),
            "fwhm_keV": 0.42,
            "post_noise_pixel_threshold_keV": 0.3,
            "bgo_veto_threshold_keV": 50.0,
            "w2_window_keV": [510.58, 511.42],
        },
        "comparator": file_record(COMPARATOR_ROOT / "summary.json"),
        "surface_validation": file_record(PACKAGE / "audit/source_surface_60cm_validation.json"),
        "full_campaign_incident_photons": FULL_EVENTS,
    }
    atomic_json(receipt, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return payload


def import_prepare() -> Any:
    if str(EXECUTOR) not in sys.path:
        sys.path.insert(0, str(EXECUTOR))
    spec = importlib.util.spec_from_file_location("wgrid_canonical_prepare", EXECUTOR / "prepare.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("canonical preparation helper unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def collect_seed_values(value: Any, key: str = "") -> set[int]:
    seeds: set[int] = set()
    if isinstance(value, dict):
        for child_key, child in value.items():
            seeds.update(collect_seed_values(child, child_key))
    elif isinstance(value, list):
        if "seed" in key.lower():
            seeds.update(item for item in value if isinstance(item, int) and item > 0)
        else:
            for child in value:
                seeds.update(collect_seed_values(child, key))
    elif isinstance(value, int) and "seed" in key.lower() and value > 0:
        seeds.add(value)
    return seeds


def event_shards(total_events: int) -> list[int]:
    if total_events == 1000:
        return [1000]
    if total_events != FULL_EVENTS:
        raise RuntimeError("only the frozen smoke and full campaign sizes are accepted")
    rows = [50_000]
    remaining = total_events - rows[0]
    while remaining:
        value = min(250_000, remaining)
        rows.append(value)
        remaining -= value
    if rows != [50_000] + [250_000] * 62 + [159_417]:
        raise RuntimeError("full campaign shard matrix drift")
    return rows


def parma_source(job_id: str, events: int, seed: int, output_prefix: Path) -> str:
    fragment = LINE_FRAGMENT.read_text(encoding="utf-8").replace("PARMA511Day15", job_id)
    text = "\n".join([
        "# SH3 W-grid standalone PARMA atmospheric 511-keV line transport.",
        "# Line-only campaign; broadband components are intentionally absent.",
        f"Geometry {SETUP}",
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
        fragment.rstrip(),
        "",
    ])
    if text.count(f"{job_id}.Source ") != 80 or text.count(".Spectrum Mono 510.99895") != 80:
        raise RuntimeError("PARMA 80-bin source binding drift")
    flux = math.fsum(
        float(line.rsplit(maxsplit=1)[-1])
        for line in text.splitlines()
        if ".Flux " in line and not line.lstrip().startswith("#")
    )
    if not math.isclose(flux, LINE_FLUX_4PI, rel_tol=0, abs_tol=2e-15):
        raise RuntimeError(f"PARMA flux drift: {flux}")
    if normalized_fragment_sha(text, job_id) != EXPECTED["normalized_fragment"]:
        raise RuntimeError("normalized 80-bin source drift")
    return text


def prepare_bundle(root: Path, total_events: int) -> dict[str, Any]:
    prepare_authority()
    if root.exists():
        raise FileExistsError(f"non-overwrite bundle gate: {root}")
    canonical = import_prepare()
    occupied, occupied_audit = canonical.occupied_seeds(load_json(EXECUTOR / "config.json"))
    comparator_seeds = collect_seed_values(load_json(COMPARATOR_ROOT / "MERGE_RECEIPT.json"))
    if len(comparator_seeds) != 70:
        raise RuntimeError(f"expected 70 comparator seeds, found {len(comparator_seeds)}")
    occupied.update(comparator_seeds)
    if root == FULL_ROOT:
        smoke_registry = SMOKE_ROOT / "generated/seed_registry.json"
        if not smoke_registry.is_file():
            raise RuntimeError("smoke seed registry must exist before full preparation")
        occupied.update(collect_seed_values(load_json(smoke_registry)))
    generated = root / "generated"
    sources = generated / "sources"
    run_root = root / "run"
    sources.mkdir(parents=True)
    run_root.mkdir(parents=True)
    profile = f"SH3_WGRID_60CM_PARMA511_{root.name}_20260824"
    candidate = "SH3_WGrid_60cm"
    shards = event_shards(total_events)
    jobs: list[dict[str, Any]] = []
    seed_rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    for ordinal, events in enumerate(shards, 1):
        job_id = f"wgrid_parma511_{'smoke' if total_events == 1000 else 'full'}_shard{ordinal:04d}"
        seed = canonical.derive_seed(profile, job_id, occupied)
        output_prefix = run_root / "jobs" / job_id / "active" / job_id
        source_path = sources / f"{job_id}.source"
        source_path.write_text(parma_source(job_id, events, seed, output_prefix), encoding="utf-8")
        job = {
            "candidate": candidate,
            "estimated_bytes": max(256 * 1024**2, events * 700),
            "events": events,
            "family": "parma511",
            "job_id": job_id,
            "mode": "atm511",
            "ordinal": ordinal,
            "output_prefix": str(output_prefix),
            "production_canary": ordinal == 1,
            "requires_isotope_dat": False,
            "seed": seed,
            "setup_path": str(SETUP),
            "source_path": str(source_path),
            "stage": "background",
        }
        jobs.append(job)
        seed_rows.append({"job_id": job_id, "seed": seed, "namespace": profile})
        source_rows.append({
            "job_id": job_id, "mode": "atm511", "family": "parma511",
            "events": events, "seed": seed, "source_path": str(source_path),
            "setup_path": str(SETUP), "source_sha256": sha256(source_path),
            "source_surface": SURFACE,
            "composition": "standalone_parma_atmospheric_annihilation_line",
        })
    totals = {"jobs": len(jobs), "instant_histories": 0, "buildup_histories": 0}
    statuses = {
        "seed": "PASS__SH3_WGRID_FRESH_DISJOINT_SEEDS",
        "source": "PASS__SH3_WGRID_PARMA511_80MU_SOURCES",
        "preflight": "PASS__SH3_WGRID_60CM_PARMA511_PREFLIGHT",
    }
    authority = load_json(PACKAGE / "audit/authority_receipt.json")
    atomic_json(generated / "job_plan.json", {
        "schema_version": 1, "profile_id": profile, "candidate": candidate,
        "status": "PASS", "jobs": jobs, "totals": totals,
    })
    atomic_json(generated / "seed_registry.json", {
        "schema_version": 1, "profile_id": profile, "status": statuses["seed"], "seeds": seed_rows,
    })
    atomic_json(generated / "source_manifest.json", {
        "schema_version": 1, "profile_id": profile, "status": statuses["source"],
        "sources": source_rows, "authority": authority,
    })
    atomic_json(generated / "preflight.json", {
        "schema_version": 1, "profile_id": profile, "candidate": candidate,
        "status": statuses["preflight"], "job_plan": totals, "authority": authority,
    })
    config = {
        "schema_version": 1,
        "profile_id": profile,
        "candidate": candidate,
        "display_title": f"SH3 W-grid 60 cm PARMA mono511 {root.name}",
        "generated_root": str(generated),
        "run_root": str(run_root),
        "geometry_setup": str(SETUP),
        "allowed_stages": ["background"],
        "expected_jobs": len(jobs),
        "expected_instant_histories": 0,
        "expected_buildup_histories": 0,
        "canary_job_id": jobs[0]["job_id"],
        "workers": 1 if total_events == 1000 else 2,
        "max_workers": 2,
        "max_attempts": 2,
        "cosima": str(COSIMA),
        "cosima_workdir": str(REPO),
        "megalib_environment": str(MEGALIB_ENVIRONMENT),
        "poll_seconds": 2.0,
        "progress_interval_seconds": 2.0,
        "start_free_bytes": 30 * 1024**3,
        "dynamic_reserve_bytes": 20 * 1024**3,
        "launch_mem_available_bytes": 1200 * 1024**2,
        "runtime_mem_floor_bytes": 700 * 1024**2,
        "launch_swap_free_bytes": 3 * 1024**3,
        "runtime_swap_floor_bytes": 1 * 1024**3,
        "launch_worker_reservation_bytes": 850 * 1024**2,
        "aggregate_worker_rss_ceiling_bytes": 0,
        "launch_memory_full_psi_avg10_max": 100.0,
        "runtime_memory_full_psi_avg10_max": 100.0,
        "source_policy": "standalone_parma511_mono_line_80bin",
        "seed_registry_pass_status": statuses["seed"],
        "source_manifest_pass_status": statuses["source"],
        "preflight_pass_status": statuses["preflight"],
    }
    atomic_json(root / "config.json", config)
    contract = {
        "schema_version": 1,
        "status": "PASS__SH3_WGRID_MONO511_BUNDLE_PREPARED",
        "prepared_at_utc": utc_now(),
        "root": str(root),
        "incident_photons": total_events,
        "jobs": len(jobs),
        "estimated_bytes": sum(int(job["estimated_bytes"]) for job in jobs),
        "line_energy_keV": LINE_ENERGY_KEV,
        "line_flux_4pi_ph_cm2_s": LINE_FLUX_4PI,
        "source_surface": SURFACE,
        "comparator_seed_count_excluded": len(comparator_seeds),
        "canonical_seed_authority": occupied_audit,
        "hashes": {
            "config": sha256(root / "config.json"),
            "job_plan": sha256(generated / "job_plan.json"),
            "seed_registry": sha256(generated / "seed_registry.json"),
            "source_manifest": sha256(generated / "source_manifest.json"),
            "preflight": sha256(generated / "preflight.json"),
            "authority_receipt": sha256(PACKAGE / "audit/authority_receipt.json"),
        },
        "sim_digest_policy": "PATH_SIZE_HEADER_ONLY__NO_FULL_SIM_HASH",
    }
    atomic_json(root / "BUNDLE_CONTRACT.json", contract)
    print(json.dumps(contract, indent=2, sort_keys=True))
    return contract


def validate_bundle(root: Path) -> dict[str, Any]:
    contract = load_json(root / "BUNDLE_CONTRACT.json")
    controller = load_json(root / "run/controller_state.json")
    if contract.get("status") != "PASS__SH3_WGRID_MONO511_BUNDLE_PREPARED":
        raise RuntimeError("bundle preparation contract is not PASS")
    if controller.get("status") != "COMPLETE" or controller.get("error") is not None:
        raise RuntimeError("transport controller is not complete")
    receipt_paths = sorted((root / "run/receipts").glob("*.json"))
    receipts = [load_json(path) for path in receipt_paths]
    if len(receipts) != int(contract["jobs"]) or int(controller.get("completed_count", -1)) != len(receipts):
        raise RuntimeError("receipt/controller count mismatch")
    if any(row.get("status") != "PASS" or row.get("errors") for row in receipts):
        raise RuntimeError("a transport receipt is not PASS")
    seeds = [int(row["seed"]) for row in receipts]
    if len(seeds) != len(set(seeds)):
        raise RuntimeError("transport seed reuse")
    comparator_seeds = collect_seed_values(load_json(COMPARATOR_ROOT / "MERGE_RECEIPT.json"))
    if set(seeds) & comparator_seeds:
        raise RuntimeError("transport seed overlaps promoted SH3 comparator")
    total_events = 0
    total_exposure = 0.0
    total_bytes = 0
    for row in receipts:
        total_events += int(row["events"])
        total_exposure += float(row["log"]["observation_time_s"])
        total_bytes += int(row["artifact_bytes"])
        if int(row["log"]["generated_events"]) != int(row["events"]):
            raise RuntimeError(f"generated-event mismatch: {row['job_id']}")
        if Path(row["setup_path"]).resolve() != SETUP.resolve():
            raise RuntimeError(f"receipt setup mismatch: {row['job_id']}")
        if Path(row["sim_header"]["geometry"]).resolve() != SETUP.resolve():
            raise RuntimeError(f"SIM header geometry mismatch: {row['job_id']}")
        if int(row["sim_header"]["seed"]) != int(row["seed"]):
            raise RuntimeError(f"SIM header seed mismatch: {row['job_id']}")
        sim = Path(row["sim_path"])
        source = Path(row["source_path"])
        if not sim.is_file() or sim.stat().st_size != int(row["sim_bytes"]):
            raise RuntimeError(f"SIM path/size mismatch: {row['job_id']}")
        if not source.is_file() or sha256(source) != row["source_sha256"]:
            raise RuntimeError(f"source path/hash mismatch: {row['job_id']}")
        text = source.read_text(encoding="utf-8")
        if text.count(".Spectrum Mono 510.99895") != 80 or text.count(".Source ") != 80:
            raise RuntimeError(f"source 80-bin binding mismatch: {row['job_id']}")
        if normalized_fragment_sha(text, str(row["job_id"])) != EXPECTED["normalized_fragment"]:
            raise RuntimeError(f"source normalized fragment mismatch: {row['job_id']}")
        flux = math.fsum(
            float(line.rsplit(maxsplit=1)[-1])
            for line in text.splitlines()
            if ".Flux " in line and not line.lstrip().startswith("#")
        )
        if not math.isclose(flux, LINE_FLUX_4PI, rel_tol=0, abs_tol=2e-15):
            raise RuntimeError(f"source flux mismatch: {row['job_id']}")
    if total_events != int(contract["incident_photons"]):
        raise RuntimeError("transport incident total mismatch")
    receipt_digest = hashlib.sha256()
    for path in receipt_paths:
        receipt_digest.update(path.name.encode("utf-8") + b"\0")
        receipt_digest.update(sha256(path).encode("ascii") + b"\n")
    payload = {
        "schema_version": 1,
        "status": "PASS__SH3_WGRID_MONO511_TRANSPORT_COMPLETE",
        "root": str(root),
        "jobs": len(receipts),
        "incident_photons": total_events,
        "physical_exposure_s": total_exposure,
        "artifact_bytes": total_bytes,
        "unique_seeds": len(set(seeds)),
        "comparator_seed_overlap": 0,
        "geometry_setup": str(SETUP),
        "geometry_setup_sha256": sha256(SETUP),
        "geometry_geo_sha256": sha256(GEO),
        "line_energy_keV": LINE_ENERGY_KEV,
        "line_flux_4pi_ph_cm2_s": LINE_FLUX_4PI,
        "source_surface": SURFACE,
        "normalized_fragment_sha256": EXPECTED["normalized_fragment"],
        "receipts_manifest_sha256": receipt_digest.hexdigest(),
        "sim_hashes_computed": 0,
        "contract_sha256": sha256(root / "BUNDLE_CONTRACT.json"),
        "controller_sha256": sha256(root / "run/controller_state.json"),
    }
    output = root / "TRANSPORT_VALIDATION.json"
    if output.exists():
        if load_json(output) != payload:
            raise RuntimeError("existing validation differs; refusing overwrite")
    else:
        atomic_json(output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return payload


def run_bundle(root: Path) -> dict[str, Any]:
    controller = root / "run/controller_state.json"
    if controller.is_file():
        state = load_json(controller)
        if state.get("status") == "COMPLETE" and state.get("error") is None:
            return validate_bundle(root)
    config = load_json(root / "config.json")
    workers = int(config["workers"])
    command = [sys.executable, str(RUNNER), "--config", str(root / "config.json"), "--workers", str(workers)]
    with (root / "runner.log").open("a", encoding="utf-8", buffering=1) as handle:
        completed = subprocess.run(command, cwd=REPO, stdout=handle, stderr=subprocess.STDOUT, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"canonical runner failed with code {completed.returncode}")
    return validate_bundle(root)


def self_test() -> dict[str, Any]:
    full = event_shards(FULL_EVENTS)
    smoke = event_shards(1000)
    assert full == [50_000] + [250_000] * 62 + [159_417]
    assert sum(full) == FULL_EVENTS and smoke == [1000]
    source = SOURCE_SOURCE / "line/PARMA_atm511_day15_fullsphere_80bins.inc.source"
    assert sha256(source) == EXPECTED["line_fragment"]
    assert normalized_fragment_sha(source.read_text(encoding="utf-8"), "PARMA511Day15") == EXPECTED["normalized_fragment"]
    payload = {
        "status": "PASS__SH3_WGRID_MONO511_RUNNER_SELF_TEST",
        "full_incident_photons": FULL_EVENTS,
        "full_jobs": len(full),
        "smoke_incident_photons": 1000,
        "transport_started": False,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "self-test", "prepare-authority", "prepare-smoke", "run-smoke",
            "validate-smoke", "prepare-full", "run-full", "validate-full",
        ),
    )
    args = parser.parse_args()
    if args.command == "self-test":
        self_test()
    elif args.command == "prepare-authority":
        prepare_authority()
    elif args.command == "prepare-smoke":
        prepare_bundle(SMOKE_ROOT, 1000)
    elif args.command == "run-smoke":
        run_bundle(SMOKE_ROOT)
    elif args.command == "validate-smoke":
        validate_bundle(SMOKE_ROOT)
    elif args.command == "prepare-full":
        prepare_bundle(FULL_ROOT, FULL_EVENTS)
    elif args.command == "run-full":
        run_bundle(FULL_ROOT)
    else:
        validate_bundle(FULL_ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
