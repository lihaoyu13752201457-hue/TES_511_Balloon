#!/usr/bin/env python3
"""Freeze a higher-stat, non-overwriting root-19932 extension."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
GEOMETRY = PACKAGE / "data/lc1_geometry_manifest.json"
PLAN = PACKAGE / "data/lc1_root19932_extension_plan.json"
INPUTS = PACKAGE / "smoke_inputs_root19932_extension"
RUN_ROOT = ROOT / "runs/particle_source_unit_repair_20260811/s3d_o8_lc1_root19932_extension_20260814_v1"
BASE_SETUP = ROOT / (
    "engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
SEED = 2090000003
N = 8192


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    if PLAN.exists() or INPUTS.exists():
        raise RuntimeError("extension inputs already exist; builder is write-once")
    setups = {"A_baseline": BASE_SETUP}
    for item in json.loads(GEOMETRY.read_text(encoding="utf-8"))["variants"]:
        setups[item["key"]] = ROOT / item["setup"]["path"]
    events = INPUTS / "eventlists/gamma_root_5769keV_event19932_8192.eventlist.dat"
    events.parent.mkdir(parents=True)
    lines = []
    for i in range(N):
        lines.append(
            f"{i+1} 0 1 0 {i*1e-9:.12e} 62.49008000 -16.03987000 -0.23171000 "
            "-0.96476000 0.26018000 0.03927000 0 0 0 5768.820000\n"
        )
    events.write_text("".join(lines), encoding="utf-8")
    jobs = []
    for key, setup in setups.items():
        job = f"gamma_root_5769_event19932_N8192__{key}"
        partial = RUN_ROOT / job / ".attempt01.partial"
        final = RUN_ROOT / job / "attempt01"
        source = INPUTS / "sources" / key / f"{job}.source"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(
            f"""# LC1 root-19932 conditional extension; no sky-rate authority.
Version 1
Geometry {setup.resolve()}
PhysicsListEM LivermorePol
PhysicsListHD qgsp-bic-hp
StoreSimulationInfo all
DiscretizeHits true
DetectorTimeConstant 1e-9
Seed {SEED}

Run {job}
{job}.FileName {(partial / job).resolve()}
{job}.NEvents {N}
{job}.Source {job}_PhaseSpace
{job}_PhaseSpace.EventList {events.resolve()}
""",
            encoding="utf-8",
        )
        jobs.append({
            "job_id": job,
            "cell_id": "gamma_root_5769_event19932_N8192",
            "geometry_key": key,
            "geometry_setup": str(setup.resolve()),
            "eventlist": str(events.resolve()),
            "eventlist_sha256": sha256(events),
            "n_events": N,
            "seed": SEED,
            "source": str(source.resolve()),
            "source_sha256": sha256(source),
            "partial_dir": str(partial.resolve()),
            "final_dir": str(final.resolve()),
        })
    plan = {
        "schema_version": 1,
        "status": "FROZEN_ROOT19932_EXTENSION__TRANSPORT_NOT_RUN",
        "confirmation_token": "S3D_O8_LC1_ROOT19932_EXTENSION_V1",
        "run_root": str(RUN_ROOT.resolve()),
        "memory_policy": {
            "serial_jobs": True,
            "minimum_mem_available_kib": 1572864,
            "minimum_free_disk_bytes": 20 * 1024**3,
            "sim_file_cap_bytes": 1024**3,
        },
        "jobs": jobs,
        "totals": {"jobs": 3, "events": 3 * N},
        "pairing_rule": "identical input tape and CLI seed across the three geometries; analyze geometry cells separately",
        "claim_boundary": "Fixed single-direction conditional mechanism extension only; no sky rate or promotion authority.",
    }
    PLAN.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(PLAN)


if __name__ == "__main__":
    main()
