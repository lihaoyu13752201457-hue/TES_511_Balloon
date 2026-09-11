#!/usr/bin/env python3
"""Build a small paired LC1 mechanism smoke; no transport is run here."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
INPUTS = PACKAGE / "smoke_inputs"
EVENTS = INPUTS / "eventlists"
SOURCES = INPUTS / "sources"
PLAN = PACKAGE / "data/lc1_smoke_plan.json"
RUN_ROOT = ROOT / "runs/particle_source_unit_repair_20260811/s3d_o8_low_grammage_core_smoke_20260814_v1"
GEOM_MANIFEST = PACKAGE / "data/lc1_geometry_manifest.json"
GEOM_VALIDATION = PACKAGE / "data/lc1_geometry_validation.json"
LG1_EVENTS = ROOT / "engineering/particle_source_unit_repair_20260811/s3d_o8_lg1_screening_20260813/smoke_inputs/eventlists"

BASE_SETUP = ROOT / (
    "engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def eventlist(path: Path, n: int, position: tuple[float, float, float], direction: tuple[float, float, float], energy: float) -> None:
    lines = []
    for i in range(n):
        lines.append(
            f"{i+1} 0 1 0 {i*1e-9:.12e} "
            f"{position[0]:.8f} {position[1]:.8f} {position[2]:.8f} "
            f"{direction[0]:.8f} {direction[1]:.8f} {direction[2]:.8f} 0 0 0 {energy:.6f}\n"
        )
    path.write_text("".join(lines), encoding="utf-8")


def source_text(job: str, setup: Path, events: Path, n_events: int, seed: int, output_prefix: Path) -> str:
    return f"""# LC1 paired mechanism smoke; no sky-rate or promotion interpretation.
Version 1
Geometry {setup.resolve()}
PhysicsListEM LivermorePol
PhysicsListHD qgsp-bic-hp
StoreSimulationInfo all
DiscretizeHits true
DetectorTimeConstant 1e-9
Seed {seed}

Run {job}
{job}.FileName {output_prefix.resolve()}
{job}.NEvents {n_events}
{job}.Source {job}_PhaseSpace
{job}_PhaseSpace.EventList {events.resolve()}
"""


def main() -> None:
    validation = json.loads(GEOM_VALIDATION.read_text(encoding="utf-8"))
    if validation.get("status") != "PASS_LC1_STATIC_GEOMETRY_VALIDATION__COSIMA_NOT_RUN":
        raise RuntimeError("LC1 static validation gate is not PASS")
    geometry = json.loads(GEOM_MANIFEST.read_text(encoding="utf-8"))
    setups = {"A_baseline": BASE_SETUP}
    for item in geometry["variants"]:
        setups[item["key"]] = ROOT / item["setup"]["path"]

    if PLAN.exists() or INPUTS.exists():
        raise RuntimeError("smoke inputs/plan already exist; builder is write-once")
    EVENTS.mkdir(parents=True)
    SOURCES.mkdir(parents=True)

    focused = EVENTS / "focused_first1000.eventlist.dat"
    shutil.copyfile(LG1_EVENTS / focused.name, focused)
    root_4148 = EVENTS / "gamma_root_4148keV_event3883_512.eventlist.dat"
    root_5769 = EVENTS / "gamma_root_5769keV_event19932_512.eventlist.dat"
    shutil.copyfile(LG1_EVENTS / root_4148.name, root_4148)
    shutil.copyfile(LG1_EVENTS / root_5769.name, root_5769)
    root_6346 = EVENTS / "gamma_root_6346keV_event8081_512.eventlist.dat"
    eventlist(
        root_6346,
        512,
        (25.46579, -31.55969, -38.99286),
        (-0.47432, 0.55762, 0.68123),
        6345.94,
    )
    tapes = [
        ("focused_first1000", focused, 1000, 2130000003),
        ("gamma_root_4148_event3883", root_4148, 512, 2130007922),
        ("gamma_root_5769_event19932", root_5769, 512, 2130015841),
        ("gamma_root_6346_event8081", root_6346, 512, 2130023760),
    ]
    # Fail if any chosen seed already appears in existing source/JSON text.
    # SIM-header collision is separately rechecked by the validator before run.
    selected = {seed for _, _, _, seed in tapes}
    seed_re = re.compile(r"(?<![0-9])(" + "|".join(map(str, sorted(selected))) + r")(?![0-9])")
    collisions = []
    for base in (ROOT, Path("/home/ubuntu/TES_511_Balloon")):
        for suffix in ("*.source", "*.json"):
            for path in base.rglob(suffix):
                if PACKAGE in path.parents or RUN_ROOT in path.parents or any(part in {".git", ".tools"} for part in path.parts):
                    continue
                try:
                    if seed_re.search(path.read_text(encoding="utf-8", errors="ignore")):
                        collisions.append(str(path))
                except OSError:
                    pass
    if collisions:
        raise RuntimeError(f"selected seed collision(s): {collisions[:20]}")

    jobs = []
    for tape, events, n_events, seed in tapes:
        for geometry_key, setup in setups.items():
            job = f"{tape}__{geometry_key}"
            final_dir = RUN_ROOT / job / "attempt01"
            partial_dir = RUN_ROOT / job / ".attempt01.partial"
            prefix = partial_dir / job
            source_dir = SOURCES / geometry_key
            source_dir.mkdir(exist_ok=True)
            source = source_dir / f"{job}.source"
            source.write_text(source_text(job, setup, events, n_events, seed, prefix), encoding="utf-8")
            jobs.append({
                "job_id": job,
                "cell_id": tape,
                "geometry_key": geometry_key,
                "geometry_setup": str(setup.resolve()),
                "eventlist": str(events.resolve()),
                "eventlist_sha256": sha256(events),
                "n_events": n_events,
                "seed": seed,
                "source": str(source.resolve()),
                "source_sha256": sha256(source),
                "partial_dir": str(partial_dir.resolve()),
                "final_dir": str(final_dir.resolve()),
            })
    plan = {
        "schema_version": 1,
        "status": "FROZEN_INPUTS__TRANSPORT_NOT_RUN",
        "confirmation_token": "S3D_O8_LC1_MECHANISM_SMOKE_V1",
        "run_root": str(RUN_ROOT.resolve()),
        "memory_policy": {
            "serial_jobs": True,
            "minimum_mem_available_kib": 1572864,
            "minimum_free_disk_bytes": 20 * 1024**3,
            "sim_file_cap_bytes": 1024**3,
        },
        "pairing_rule": "same event list and same seed across geometries within each cell; no pooling across geometries",
        "jobs": jobs,
        "totals": {"jobs": len(jobs), "events": sum(j["n_events"] for j in jobs)},
        "claim_boundary": "Directional/focused mechanism smoke only; not broadband rate, activation, delayed, common-response, or mission authority.",
    }
    PLAN.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(PLAN)


if __name__ == "__main__":
    main()
