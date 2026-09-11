#!/usr/bin/env python3
"""Extend the frozen 257-state prompt mechanism tape to 64 uniform repeats."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
SOURCE_STATES = PACKAGE / "focused_prompt/three_cell_primary_states.csv"
BASE_PLAN = PACKAGE / "focused_prompt/three_cell_transport_plan.json"
OUT = PACKAGE / "focused_prompt_repeat64"
EVENTLIST = OUT / "three_cell_primary_states_repeat64.eventlist.dat"
EVENT_MAP = OUT / "three_cell_event_map_repeat64.csv"
PLAN = OUT / "three_cell_transport_plan_repeat64.json"
RUN_ROOT = ROOT / "runs/s3d_o8_loop_engineering_20260814/af1_48_prompt_p1_repeat64_20260814"
REPEATS = 64


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    base = json.loads(BASE_PLAN.read_text(encoding="utf-8"))
    with SOURCE_STATES.open("r", encoding="utf-8", newline="") as handle:
        states = list(csv.DictReader(handle))
    if len(states) != 257:
        raise RuntimeError(f"frozen state count={len(states)}")
    OUT.mkdir(parents=True, exist_ok=True)
    mapping: list[dict[str, object]] = []
    with EVENTLIST.open("w", encoding="utf-8") as handle:
        event_id = 0
        for repeat in range(REPEATS):
            for state_index, row in enumerate(states):
                event_id += 1
                handle.write(
                    f"{event_id} 0 1 0 {(event_id-1)*1e-9:.12e} "
                    f"{float(row['x_cm']):.8f} {float(row['y_cm']):.8f} "
                    f"{float(row['z_cm']):.8f} {float(row['dx']):.8f} "
                    f"{float(row['dy']):.8f} {float(row['dz']):.8f} 0 0 0 "
                    f"{float(row['energy_keV']):.8f}\n"
                )
                mapping.append(
                    {
                        "transport_event_id": event_id,
                        "repeat_index": repeat,
                        "state_index": state_index,
                        "cell_id": row["cell_id"],
                        "source_sim_path": row["sim_path"],
                        "source_local_event_id": row["source_local_event_id"],
                    }
                )
    with EVENT_MAP.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(mapping[0]))
        writer.writeheader()
        writer.writerows(mapping)

    jobs: list[dict[str, object]] = []
    for base_job, seed in zip(base["jobs"], (141421357, 173205081), strict=True):
        geometry_key = str(base_job["geometry_key"])
        setup = Path(base_job["setup"])
        run_name = f"gamma_three_cell_repeat64__{geometry_key}"
        source = OUT / f"{run_name}.source"
        prefix = RUN_ROOT / geometry_key / run_name
        prefix.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(
            f"""# Denominator-complete three-cell prompt extension; no sky-rate authority.
Version 1
Geometry {setup.resolve()}
PhysicsListEM LivermorePol
PhysicsListHD qgsp-bic-hp
StoreSimulationInfo all
DiscretizeHits true
DetectorTimeConstant 1e-9
Seed {seed}

Run {run_name}
{run_name}.FileName {prefix.resolve()}
{run_name}.NEvents {len(mapping)}
{run_name}.Source {run_name}_PhaseSpace
{run_name}_PhaseSpace.EventList {EVENTLIST.resolve()}
""",
            encoding="utf-8",
        )
        jobs.append(
            {
                "geometry_key": geometry_key,
                "setup": str(setup.resolve()),
                "source": str(source.resolve()),
                "source_sha256": sha256(source),
                "declared_seed": seed,
                "run_name": run_name,
                "expected_sim": str(Path(f"{prefix}.inc1.id1.sim.gz").resolve()),
            }
        )
    payload = {
        **{key: value for key, value in base.items() if key not in {"jobs", "status", "eventlist", "eventlist_sha256", "event_map", "event_map_sha256", "uniform_repeats_per_state", "transport_events_per_geometry"}},
        "status": "FROZEN_REPEAT64__TRANSPORT_NOT_YET_VERIFIED",
        "parent_plan": str(BASE_PLAN.resolve()),
        "parent_plan_sha256": sha256(BASE_PLAN),
        "uniform_repeats_per_state": REPEATS,
        "transport_events_per_geometry": len(mapping),
        "eventlist": str(EVENTLIST.resolve()),
        "eventlist_sha256": sha256(EVENTLIST),
        "event_map": str(EVENT_MAP.resolve()),
        "event_map_sha256": sha256(EVENT_MAP),
        "jobs": jobs,
    }
    PLAN.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(PLAN)


if __name__ == "__main__":
    main()
