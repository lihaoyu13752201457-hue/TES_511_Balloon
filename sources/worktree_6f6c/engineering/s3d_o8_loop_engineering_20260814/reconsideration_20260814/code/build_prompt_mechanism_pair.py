#!/usr/bin/env python3
"""Freeze the denominator-complete three-cell AF1-48 prompt mechanism test.

All S3d-O8 INSTANT gamma SIMs are streamed read-only.  Only primaries in the
three predeclared E x direction cells are sent to the exact baseline active-
grammage query; the 257 primaries in the matching grammage bins are retained.
Each primary state is repeated uniformly to sample transport stochasticity.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import subprocess
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
PROMPT_AGENT = ROOT / "engineering/s3d_o8_loop_engineering_20260814/agents/prompt"
sys.path.insert(0, str(PROMPT_AGENT))
from stream_gamma_active_grammage import GRAMMAGE_EDGES  # type: ignore
from stream_gamma_denominator import (  # type: ignore
    AZ_EDGES_DEG,
    ENERGY_EDGES_KEV,
    MU_X_EDGES,
    bin_index,
    parse_init,
    transformed_direction,
)


MANIFEST = Path(
    "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/"
    "particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/"
    "outputs/01_prompt/prompt_input_manifest.csv"
)
SOURCE_ROOT = Path("/home/ubuntu/TES_511_Balloon")
BASE_SETUP = Path(
    "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/"
    "geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/"
    "geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
CANDIDATE_SETUP = (
    PACKAGE
    / "agents/geometry/candidate_proxy/"
    "S3D_O8_unified_Al_mag05_innerBPE_topcatch_proxy.geo.setup"
)
QUERY = PROMPT_AGENT / "active_chord_query"
OUT = PACKAGE / "focused_prompt"
STATE_CSV = OUT / "three_cell_primary_states.csv"
EVENTLIST = OUT / "three_cell_primary_states_repeat8.eventlist.dat"
EVENT_MAP = OUT / "three_cell_event_map.csv"
PLAN = OUT / "three_cell_transport_plan.json"
RUN_ROOT = ROOT / "runs/s3d_o8_loop_engineering_20260814/af1_48_prompt_p1_20260814"
REPEATS = 8

# (energy bin, IF mu-x bin, IF azimuth bin) -> required active-grammage bin.
TARGETS = {
    (4, 4, 1): (3, "cell_3883"),
    (5, 1, 6): (5, "cell_19932"),
    (6, 0, 0): (4, "cell_8081"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def gamma_jobs() -> list[dict[str, str]]:
    with MANIFEST.open("r", encoding="utf-8", newline="") as handle:
        rows = [
            row
            for row in csv.DictReader(handle)
            if row["geometry"] == "S3d_O8"
            and row["family"] == "gamma"
            and row["mode"] == "instant"
        ]
    if not rows:
        raise RuntimeError("no S3d-O8 INSTANT gamma jobs")
    return rows


def collect_chunk(entries: list[tuple[int, str]]) -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    for job_index, path_text in entries:
        path = Path(path_text)
        current_id: int | None = None
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if line.startswith("ID "):
                    current_id = int(line.split()[1])
                elif line.startswith("IA INIT"):
                    if current_id is None:
                        raise RuntimeError(f"INIT before ID: {path}")
                    x, y, z, dx, dy, dz, energy = parse_init(line)
                    mux, _, _, _, az = transformed_direction(dx, dy, dz)
                    key = (
                        bin_index(energy, ENERGY_EDGES_KEV),
                        bin_index(mux, MU_X_EDGES),
                        bin_index(az, AZ_EDGES_DEG),
                    )
                    if key not in TARGETS:
                        continue
                    selected.append(
                        {
                            "job_index": job_index,
                            "sim_path": str(path),
                            "source_local_event_id": current_id,
                            "energy_keV": energy,
                            "x_cm": x,
                            "y_cm": y,
                            "z_cm": z,
                            "dx": dx,
                            "dy": dy,
                            "dz": dz,
                            "energy_bin": key[0],
                            "mu_x_bin": key[1],
                            "azimuth_bin": key[2],
                            "target_grammage_bin": TARGETS[key][0],
                            "cell_id": TARGETS[key][1],
                        }
                    )
    return selected


def collect_prefiltered(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    entries = [
        (index, str((SOURCE_ROOT / job["sim_path"]).resolve()))
        for index, job in enumerate(rows)
    ]
    chunks = [entries[index::3] for index in range(3)]
    selected: list[dict[str, object]] = []
    with ProcessPoolExecutor(max_workers=3) as pool:
        for part in pool.map(collect_chunk, chunks):
            selected.extend(part)
    selected.sort(
        key=lambda row: (int(row["job_index"]), int(row["source_local_event_id"]))
    )
    for index, row in enumerate(selected):
        row["query_id"] = f"q{index}"
    return selected


def query_grammage(rows: list[dict[str, object]]) -> None:
    proc = subprocess.Popen(
        [str(QUERY.resolve()), str(BASE_SETUP.resolve())],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert proc.stdin is not None and proc.stdout is not None
    by_id = {str(row["query_id"]): row for row in rows}
    requests: list[str] = []
    for row in rows:
        dx, dy, dz = (float(row[name]) for name in ("dx", "dy", "dz"))
        norm = math.sqrt(dx * dx + dy * dy + dz * dz)
        ux, uy, uz = dx / norm, dy / norm, dz / norm
        x, y, z = (float(row[name]) for name in ("x_cm", "y_cm", "z_cm"))
        t_closest = -(x * ux + y * uy + z * uz)
        requests.append(
            f"{row['query_id']} {x:.8g} {y:.8g} {z:.8g} "
            f"{dx:.8g} {dy:.8g} {dz:.8g} {t_closest:.12g}\n"
        )
    # communicate() drains stdout while feeding stdin and avoids a pipe-buffer
    # deadlock for the ~2200 prefiltered rays.
    stdout, stderr = proc.communicate("".join(requests))
    n_read = 0
    for line in stdout.splitlines():
        if not line.startswith("q"):
            continue
        qid, bgo, plastic, grammage = line.rstrip().split(",")
        row = by_id[qid]
        row["bgo_chord_cm"] = float(bgo)
        row["plastic_chord_cm"] = float(plastic)
        row["active_grammage_g_cm2"] = float(grammage)
        row["active_grammage_bin"] = bin_index(
            max(0.0, float(grammage)), GRAMMAGE_EDGES
        )
        n_read += 1
    rc = proc.returncode
    if rc != 0 or n_read != len(rows):
        raise RuntimeError(
            f"active grammage query failed rc={rc}, rows={n_read}/{len(rows)}: "
            f"{stderr[-1000:]}"
        )


def write_sources(states: list[dict[str, object]]) -> list[dict[str, object]]:
    OUT.mkdir(parents=True, exist_ok=True)
    fields = list(states[0])
    with STATE_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(states)

    mapping: list[dict[str, object]] = []
    with EVENTLIST.open("w", encoding="utf-8") as handle:
        event_id = 0
        for repeat in range(REPEATS):
            for state_id, row in enumerate(states):
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
                        "state_index": state_id,
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
    for geometry_key, setup, seed in (
        ("baseline", BASE_SETUP, 31415927),
        ("AF1_48", CANDIDATE_SETUP, 27182819),
    ):
        run_name = f"gamma_three_cell_repeat8__{geometry_key}"
        source = OUT / f"{run_name}.source"
        prefix = RUN_ROOT / geometry_key / run_name
        prefix.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(
            f"""# Denominator-complete three-cell prompt mechanism test; no sky-rate authority.
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
    return jobs


def main() -> None:
    for path in (MANIFEST, BASE_SETUP, CANDIDATE_SETUP, QUERY):
        if not path.exists():
            raise FileNotFoundError(path)
    jobs = gamma_jobs()
    prefiltered = collect_prefiltered(jobs)
    query_grammage(prefiltered)
    states = [
        row
        for row in prefiltered
        if int(row["active_grammage_bin"]) == int(row["target_grammage_bin"])
    ]
    counts = Counter(str(row["cell_id"]) for row in states)
    expected = {"cell_3883": 71, "cell_19932": 94, "cell_8081": 92}
    if dict(counts) != expected:
        raise RuntimeError(f"denominator cell mismatch: {dict(counts)} != {expected}")
    transport_jobs = write_sources(states)
    payload = {
        "schema_version": 1,
        "status": "FROZEN__TRANSPORT_NOT_YET_VERIFIED",
        "claim_boundary": (
            "Three predeclared E x direction x active-grammage cells only; "
            "mechanism sensitivity, not a broadband prompt-rate estimate."
        ),
        "geometry_mode_family": "S3d_O8 x INSTANT x gamma",
        "manifest": str(MANIFEST),
        "manifest_rows": len(jobs),
        "prefiltered_E_direction_states": len(prefiltered),
        "selected_state_counts": expected,
        "selected_states": len(states),
        "uniform_repeats_per_state": REPEATS,
        "transport_events_per_geometry": len(states) * REPEATS,
        "state_csv": str(STATE_CSV.resolve()),
        "state_csv_sha256": sha256(STATE_CSV),
        "eventlist": str(EVENTLIST.resolve()),
        "eventlist_sha256": sha256(EVENTLIST),
        "event_map": str(EVENT_MAP.resolve()),
        "event_map_sha256": sha256(EVENT_MAP),
        "jobs": transport_jobs,
    }
    PLAN.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(PLAN)


if __name__ == "__main__":
    main()
