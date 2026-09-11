#!/usr/bin/env python3
"""Targeted stats escalation: more events, same live PARMA spectra & Mass_model geometry.

NOT full4 Fable5 equivalent:
  - still coarse TES proxy (not Step05 W2)
  - no activation/delayed
  - 3 species only

Claim target: tighten e+/TES/band Q errors; confirm env-layer systematic is stable.
"""
from __future__ import annotations

import csv
import json
import math
import os
import re
import subprocess
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path("/home/ubuntu/TES_511_Balloon")
PKG = ROOT / "engineering/trajectory_transport_validation_20260709"
PARMA_EXE = Path(
    "/home/ubuntu/codex_tes_511_sim/COSMOSRAY_BALLOON_SIM/external/expacs_parma/phase2_parma_grid_driver"
)
PARMA_CWD = PARMA_EXE.parent / "parma_cpp"
COSIMA = Path("/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima")
GEO = (
    "outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
SRC_DIR = (
    ROOT
    / "engineering/Mass_model_511_nearfield_migration_20260701/03_source_migration/source_dirs/Mass_model_511"
)
PTYPE = {"gamma": 1, "eplus": 2, "n": 6}
# targeted escalation (still << full4 1e8)
EVENTS = {"eplus": 1_000_000, "n": 200_000, "gamma": 500_000}
MU_W = 0.1
PARTICLES = ["eplus", "n", "gamma"]
OUT = PKG / "05_targeted_stats"
LOGDIR = PKG / "logs" / "targeted"
MAX_PARALLEL = 3  # keep memory under control (~3 Cosima)


def load_points():
    return list(csv.DictReader((PKG / "01_points/validation_points.csv").open()))


def run_parma(lat, lon, alt):
    cmd = [str(PARMA_EXE), "2025", "8", "31", str(lat), str(lon), str(alt), "10.0"]
    proc = subprocess.run(cmd, cwd=str(PARMA_CWD), text=True, capture_output=True, check=True)
    lines = [l for l in proc.stdout.splitlines() if l]
    start = next(i for i, l in enumerate(lines) if l.startswith("particle,"))
    meta_line = next(l for l in lines if l.startswith("META,"))
    _, w, rc, depth = meta_line.split(",")
    meta = {"W": float(w), "Rc": float(rc), "depth": float(depth)}
    rows = list(csv.DictReader(lines[start:]))
    return meta, rows


def build_abs_and_spectra(point_id, rows):
    d_omega = 2 * math.pi * MU_W
    abs_flux = {}
    for particle in PARTICLES:
        by = defaultdict(list)
        for r in rows:
            if r["particle"] != particle:
                continue
            by[int(r["angle_bin"])].append(
                (float(r["energy_MeV"]), float(r["differential_flux_cm2_s_sr_MeV"]))
            )
        abs_flux[particle] = {}
        for ab, pts in by.items():
            pts = sorted(pts)
            e = [p[0] for p in pts]
            v = [p[1] for p in pts]
            integ = sum(0.5 * (v[i] + v[i + 1]) * (e[i + 1] - e[i]) for i in range(len(pts) - 1))
            abs_flux[particle][ab] = max(integ * d_omega, 0.0)
            total = integ if integ > 0 else 0.0
            sp = OUT / "spectra" / point_id / f"{particle}_bin{ab:02d}_pdf.dat"
            sp.parent.mkdir(parents=True, exist_ok=True)
            lines = ["# targeted live PARMA", "IP LIN"]
            if total <= 0:
                for ee in e:
                    lines.append(f"DP {ee:.10e} {1/len(e):.10e}")
            else:
                for ee, vv in zip(e, v):
                    lines.append(f"DP {ee:.10e} {max(vv, 0)/total:.10e}")
            sp.write_text("\n".join(lines) + "\n")
    return abs_flux


def beam_edges(particle):
    src = (SRC_DIR / f"Background_{particle}_fullsphere20.source").read_text()
    return [
        tuple(map(float, m.groups()))
        for m in re.finditer(
            r"Beam FarFieldAreaSource\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)", src
        )
    ]


def write_source(pid, particle, abs_flux, events, seed, src_path, run_prefix):
    edges = beam_edges(particle)
    lines = [
        f"Geometry {GEO}",
        "PhysicsListHD qgsp-bic-hp",
        "PhysicsListEM LivermorePol",
        "StoreSimulationInfo all",
        "StoreIsotopes true",
        "DetectorTimeConstant 1e-9",
        f"Seed {seed}",
        "",
        f"Run TrajVal_{pid}_{particle}",
        f"TrajVal_{pid}_{particle}.Events {events}",
        f"TrajVal_{pid}_{particle}.FileName {run_prefix}",
        f"TrajVal_{pid}_{particle}.IsotopeProductionFile {run_prefix}.dat",
        "",
    ]
    for ab in range(20):
        lines.append(f"TrajVal_{pid}_{particle}.Source Atm_{particle}_bin{ab:02d}")
    lines.append("")
    for ab in range(20):
        th0, th1, ph0, ph1 = edges[ab]
        sp = (
            f"engineering/trajectory_transport_validation_20260709/05_targeted_stats/"
            f"spectra/{pid}/{particle}_bin{ab:02d}_pdf.dat"
        )
        flux = max(abs_flux.get(ab, 0.0), 1e-30)
        name = f"Atm_{particle}_bin{ab:02d}"
        lines += [
            f"{name}.ParticleType {PTYPE[particle]}",
            f"{name}.Beam FarFieldAreaSource {th0:.3f} {th1:.3f} {ph0:.3f} {ph1:.3f}",
            f"{name}.Spectrum File {sp}",
            f"{name}.Flux {flux:.12e}",
            "",
        ]
    src_path.write_text("\n".join(lines) + "\n")


def run_cosima_job(args):
    pid, particle, abs_flux_part, day_mid = args
    events = EVENTS[particle]
    seed = 70000 + int(float(day_mid) * 100) + PTYPE[particle]
    rundir = OUT / "per_point" / pid / particle
    rundir.mkdir(parents=True, exist_ok=True)
    # skip if complete sim already exists with enough size
    existing = [s for s in rundir.glob("*.sim.gz") if s.stat().st_size > 1_000_000]
    log = LOGDIR / f"{pid}_{particle}_targeted.log"
    if existing and log.exists() and "Observation time" in log.read_text(errors="replace"):
        return {
            "point_id": pid,
            "particle": particle,
            "skipped": True,
            "rc": 0,
            "sim": str(existing[0]),
        }

    for f in rundir.glob("*.sim*"):
        if f.stat().st_size < 1000:
            f.unlink()
    run_prefix = (rundir / f"TrajVal_{pid}_{particle}_tgt").resolve()
    src = rundir / f"TrajVal_{pid}_{particle}_tgt.source"
    write_source(pid, particle, abs_flux_part, events, seed, src, run_prefix)

    g4sh = "/home/ubuntu/MEGAlib_Install/megalib-main/external/geant4_v10.02.p03/bin/geant4.sh"
    wrapper = f"""
source "{g4sh}"
export LD_LIBRARY_PATH="/home/ubuntu/MEGAlib_Install/megalib-main/lib:/home/ubuntu/MEGAlib_Install/megalib-main/external/root_v6.36.6/lib:$LD_LIBRARY_PATH"
export ROOTSYS=/home/ubuntu/MEGAlib_Install/megalib-main/external/root_v6.36.6
cd "{ROOT}"
"{COSIMA}" -v 0 -n "{src.resolve()}"
"""
    t0 = time.time()
    proc = subprocess.run(["bash", "-lc", wrapper], text=True, capture_output=True)
    dt = time.time() - t0
    log.write_text(proc.stdout + "\n---STDERR---\n" + proc.stderr)
    gen = obs = None
    for line in (proc.stdout + "\n" + proc.stderr).splitlines():
        if "Total number of generated particles" in line:
            m = re.search(r"(\d+)\s*$", line.strip())
            if m:
                gen = int(m.group(1))
        if "Observation time" in line:
            m = re.search(r"([0-9.eE+\-]+)\s*sec", line)
            if m:
                obs = float(m.group(1))
    sims = list(rundir.glob("*.sim.gz"))
    sizes = [s.stat().st_size for s in sims]
    print(
        f"DONE {pid} {particle} rc={proc.returncode} wall={dt:.0f}s gen={gen} obs={obs} sims={sizes}",
        flush=True,
    )
    return {
        "point_id": pid,
        "particle": particle,
        "skipped": False,
        "rc": proc.returncode,
        "wall_s": dt,
        "gen": gen,
        "obs_s": obs,
        "n_sims": len(sims),
        "sizes": sizes,
    }


def main():
    LOGDIR.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    points = load_points()
    abs_all = {}
    for p in points:
        pid = p["point_id"]
        print(f"PARMA {pid}...", flush=True)
        meta, rows = run_parma(
            float(p["latitude_deg"]), float(p["longitude_deg"]), float(p["altitude_km"])
        )
        abs_all[pid] = build_abs_and_spectra(pid, rows)
        (OUT / "parma_meta" / f"{pid}.json").parent.mkdir(parents=True, exist_ok=True)
        (OUT / "parma_meta" / f"{pid}.json").write_text(json.dumps({"meta": meta}, indent=2))

    jobs = []
    for p in points:
        pid = p["point_id"]
        for part in PARTICLES:
            jobs.append((pid, part, abs_all[pid][part], p["day_mid"]))

    print(f"Launching {len(jobs)} Cosima jobs, max_workers={MAX_PARALLEL}", flush=True)
    results = []
    with ProcessPoolExecutor(max_workers=MAX_PARALLEL) as ex:
        futs = {ex.submit(run_cosima_job, j): j for j in jobs}
        for fut in as_completed(futs):
            results.append(fut.result())

    (OUT / "run_results.json").write_text(json.dumps(results, indent=2) + "\n")
    ok = sum(1 for r in results if r.get("rc") == 0)
    print(f"TARGETED COSIMA DONE ok={ok}/{len(results)}", flush=True)


if __name__ == "__main__":
    main()
