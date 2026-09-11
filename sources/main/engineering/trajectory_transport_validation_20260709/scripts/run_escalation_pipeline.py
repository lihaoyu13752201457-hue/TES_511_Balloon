#!/usr/bin/env python3
"""Escalate trajectory multi-point validation: live PARMA + multi-species cosima + rates."""
from __future__ import annotations

import csv
import gzip
import json
import math
import os
import re
import subprocess
import time
from collections import defaultdict
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
SPECTRUM_TEMPLATE_DIR = ROOT / "expacs_fullsphere_20bin_sources/cosima_spectra_dp_2602units"

# particles to transport this escalation (high-impact for W2)
PARTICLES = ["eplus", "n", "gamma"]
# MEGAlib ParticleType codes
PTYPE = {"gamma": 1, "eplus": 2, "eminus": 3, "p": 4, "n": 6, "muplus": 8, "muminus": 9, "alpha": 21}
# events per point (escalation micro → medium smoke)
EVENTS = {
    "eplus": 50000,
    "n": 30000,
    "gamma": 60000,
}

PARMA_SOLAR = (2025, 8, 31)
MU_W = 0.1
PARTICLE_NAME_MAP = {
    "gamma": "gamma",
    "n": "n",
    "p": "p",
    "alpha": "alpha",
    "eminus": "eminus",
    "eplus": "eplus",
    "muplus": "muplus",
    "muminus": "muminus",
}


def load_points():
    rows = list(csv.DictReader((PKG / "01_points/validation_points.csv").open()))
    out = []
    for r in rows:
        out.append(
            {
                "point_id": r["point_id"],
                "day_mid": float(r["day_mid"]),
                "altitude_km": float(r["altitude_km"]),
                "latitude_deg": float(r["latitude_deg"]),
                "longitude_deg": float(r["longitude_deg"]),
                "Rc_GV": float(r["Rc_GV"]),
                "analytic_prompt_scale": float(r["analytic_prompt_scale_to_day15"]),
                "analytic_delayed_prod_scale": float(r["analytic_delayed_production_scale_to_day15"]),
                "T_atm": float(r["T_atm_511"]),
            }
        )
    return out


def run_parma(point: dict) -> tuple[dict, list[dict]]:
    y, m, d = PARMA_SOLAR
    cmd = [
        str(PARMA_EXE),
        str(y),
        str(m),
        str(d),
        str(point["latitude_deg"]),
        str(point["longitude_deg"]),
        str(point["altitude_km"]),
        "10.0",
    ]
    proc = subprocess.run(cmd, cwd=str(PARMA_CWD), text=True, capture_output=True, check=True)
    lines = [ln for ln in proc.stdout.splitlines() if ln]
    meta: dict = {}
    start = None
    for i, ln in enumerate(lines):
        if ln.startswith("META,"):
            _, w, rc, depth = ln.split(",")
            meta = {
                "W_index": float(w),
                "Rc_GV_parma": float(rc),
                "depth_g_cm2_parma": float(depth),
            }
        if ln.startswith("particle,"):
            start = i
            break
    if start is None:
        raise RuntimeError("PARMA missing particle table")
    rows = []
    for item in csv.DictReader(lines[start:]):
        rows.append(
            {
                "particle": item["particle"],
                "angle_bin": int(item["angle_bin"]),
                "mu_mid": float(item.get("mu_mid", 0.0)),
                "theta_mid_deg": float(item.get("theta_mid_deg", 0.0)),
                "energy_bin": int(item["energy_bin"]),
                "energy_MeV": float(item["energy_MeV"]),
                "angular_integrated_flux_cm2_s_MeV": max(
                    float(item.get("angular_integrated_flux_cm2_s_MeV", 0.0)), 0.0
                ),
                "differential_flux_cm2_s_sr_MeV": max(
                    float(item["differential_flux_cm2_s_sr_MeV"]), 0.0
                ),
            }
        )
    if not meta or meta.get("W_index", 0) <= 0:
        raise RuntimeError(f"PARMA meta invalid: {meta}")
    return meta, rows


def particle_totals(rows: list[dict]) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    sa = 2.0 * math.pi * MU_W
    for r in rows:
        totals[r["particle"]] += r["differential_flux_cm2_s_sr_MeV"] * sa
    return dict(totals)


def angle_bin_flux(rows: list[dict], particle: str) -> dict[int, float]:
    """Integrate dE of angular-integrated flux per angle bin for one particle."""
    # Use trapezoid on energy grid of angular_integrated_flux_cm2_s_MeV
    by_ang: dict[int, list[tuple[float, float]]] = defaultdict(list)
    for r in rows:
        if r["particle"] != particle:
            continue
        by_ang[r["angle_bin"]].append((r["energy_MeV"], r["angular_integrated_flux_cm2_s_MeV"]))
    out = {}
    for ab, pts in by_ang.items():
        pts = sorted(pts)
        integ = 0.0
        for i in range(len(pts) - 1):
            e0, f0 = pts[i]
            e1, f1 = pts[i + 1]
            integ += 0.5 * (f0 + f1) * (e1 - e0)
        out[ab] = max(integ, 0.0)
    return out


def write_spectrum_pdf(path: Path, energy_MeV: list[float], values: list[float]) -> None:
    """Write MEGAlib spectrum file (IP LIN, DP E pdf) with pdf ~ flux density."""
    # normalize to pdf so integral ~1 for Spectrum File; Flux carries absolute
    # use values as-is if all zero
    total = 0.0
    pts = list(zip(energy_MeV, values))
    pts = [(e, max(v, 0.0)) for e, v in pts]
    for i in range(len(pts) - 1):
        total += 0.5 * (pts[i][1] + pts[i + 1][1]) * (pts[i + 1][0] - pts[i][0])
    lines = [
        "# live PARMA spectrum for trajectory validation",
        "# energy axis: MeV (same convention as cosima_spectra_dp_2602units)",
        "IP LIN",
    ]
    if total <= 0:
        # flat tiny pdf
        for e, _ in pts:
            lines.append(f"DP {e:.10e} {1.0/len(pts):.10e}")
    else:
        for e, v in pts:
            lines.append(f"DP {e:.10e} {(v/total):.10e}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def build_spectra_for_point(point_id: str, rows: list[dict]) -> dict[str, dict[int, float]]:
    """Write spectrum files; return angle-bin absolute fluxes for Flux=.

    Use differential_flux * solid_angle(bin) because angular_integrated in this
    driver build is angle-independent for some particles (observed flat).
    Equal-mu bins: dOmega = 2*pi*dmu with dmu=0.1.
    """
    d_omega = 2.0 * math.pi * MU_W
    abs_flux: dict[str, dict[int, float]] = {}
    for particle in PARTICLES:
        by_ang_e: dict[int, list[tuple[float, float]]] = defaultdict(list)
        for r in rows:
            if r["particle"] != particle:
                continue
            # spectrum shape ~ differential; absolute flux folds solid angle
            by_ang_e[r["angle_bin"]].append(
                (r["energy_MeV"], r["differential_flux_cm2_s_sr_MeV"])
            )
        abs_flux[particle] = {}
        for ab, pts in by_ang_e.items():
            pts = sorted(pts)
            energies = [p[0] for p in pts]
            vals = [p[1] for p in pts]
            integ = 0.0
            for i in range(len(pts) - 1):
                integ += 0.5 * (vals[i] + vals[i + 1]) * (energies[i + 1] - energies[i])
            # Flux for FarFieldAreaSource is particles / cm2 / s into that beam
            abs_flux[particle][ab] = max(integ * d_omega, 0.0)
            sp = (
                PKG
                / "02_sources/spectra_live"
                / point_id
                / f"{particle}_bin{ab:02d}_pdf.dat"
            )
            write_spectrum_pdf(sp, energies, vals)
    return abs_flux


def beam_edges_from_template(particle: str) -> list[tuple[float, float, float, float]]:
    """Parse REF template source for FarFieldAreaSource edges in bin order."""
    src = (SRC_DIR / f"Background_{particle}_fullsphere20.source").read_text()
    edges = []
    for m in re.finditer(
        r"Beam FarFieldAreaSource\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)", src
    ):
        edges.append(tuple(map(float, m.groups())))
    if len(edges) != 20:
        raise RuntimeError(f"{particle}: expected 20 beams, got {len(edges)}")
    return edges


def write_source_card(
    point_id: str,
    particle: str,
    abs_flux: dict[int, float],
    events: int,
    seed: int,
    out_path: Path,
    run_prefix: Path,
) -> None:
    edges = beam_edges_from_template(particle)
    ptype = PTYPE[particle]
    lines = [
        f"# trajectory validation live-PARMA source point={point_id} particle={particle}",
        f"Geometry {GEO}",
        "PhysicsListHD qgsp-bic-hp",
        "PhysicsListEM LivermorePol",
        "StoreSimulationInfo all",
        "StoreIsotopes true",
        "DetectorTimeConstant 1e-9",
        f"Seed {seed}",
        "",
        f"Run TrajVal_{point_id}_{particle}",
        f"TrajVal_{point_id}_{particle}.Events {events}",
        f"TrajVal_{point_id}_{particle}.FileName {run_prefix}",
        f"TrajVal_{point_id}_{particle}.IsotopeProductionFile {run_prefix}.dat",
        "",
    ]
    for ab in range(20):
        name = f"Atm_{particle}_bin{ab:02d}"
        lines.append(f"TrajVal_{point_id}_{particle}.Source {name}")
    lines.append("")
    for ab in range(20):
        name = f"Atm_{particle}_bin{ab:02d}"
        th0, th1, ph0, ph1 = edges[ab]
        # spectrum path relative to ROOT
        sp = f"engineering/trajectory_transport_validation_20260709/02_sources/spectra_live/{point_id}/{particle}_bin{ab:02d}_pdf.dat"
        flux = abs_flux.get(ab, 0.0)
        # ensure nonzero tiny floor so cosima doesn't choke empty beams
        if flux <= 0:
            flux = 1e-30
        lines += [
            f"{name}.ParticleType {ptype}",
            f"{name}.Beam FarFieldAreaSource {th0:.3f} {th1:.3f} {ph0:.3f} {ph1:.3f}",
            f"{name}.Spectrum File {sp}",
            f"{name}.Flux {flux:.12e}",
            "",
        ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n")


def run_cosima(src: Path, log_path: Path) -> dict:
    """Invoke cosima via bash so geant4.sh sets ENSDFSTATE and friends."""
    g4sh = "/home/ubuntu/MEGAlib_Install/megalib-main/external/geant4_v10.02.p03/bin/geant4.sh"
    wrapper = f"""
set -e
source "{g4sh}"
export LD_LIBRARY_PATH="/home/ubuntu/MEGAlib_Install/megalib-main/lib:/home/ubuntu/MEGAlib_Install/megalib-main/external/root_v6.36.6/lib:$LD_LIBRARY_PATH"
export ROOTSYS=/home/ubuntu/MEGAlib_Install/megalib-main/external/root_v6.36.6
cd "{ROOT}"
"{COSIMA}" -v 0 -n "{src.resolve()}"
"""
    t0 = time.time()
    proc = subprocess.run(
        ["bash", "-lc", wrapper],
        text=True,
        capture_output=True,
    )
    dt = time.time() - t0
    log_path.write_text(proc.stdout + "\n---STDERR---\n" + proc.stderr)
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
    return {"rc": proc.returncode, "wall_s": dt, "gen": gen, "obs_s": obs}


def open_sim(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", errors="replace")
    return path.open("rt", errors="replace")


def extract_tes_stats(sim_path: Path) -> dict:
    """TES proxy: sum HTsim energy on det IDs 1–6 (D1..D6).

    MEGAlib HTsim fields: det;x;y;z;energy;time[;...]
    Energy is fields[4], not fields[5] (time).
    """
    n_events = 0
    n_tes = 0
    n_band = 0
    in_event = False
    tes_e = 0.0
    with open_sim(sim_path) as f:
        for line in f:
            if line.startswith("SE"):
                if in_event:
                    n_events += 1
                    if tes_e > 0:
                        n_tes += 1
                        if 480.0 <= tes_e <= 550.0:
                            n_band += 1
                in_event = True
                tes_e = 0.0
            elif in_event and line.startswith("HTsim"):
                try:
                    fields = line.split(None, 1)[1].split(";")
                    det = int(float(fields[0]))
                    e = float(fields[4])  # energy; fields[5] is time
                    if 1 <= det <= 6:
                        tes_e += e
                except Exception:
                    pass
        if in_event:
            n_events += 1
            if tes_e > 0:
                n_tes += 1
                if 480.0 <= tes_e <= 550.0:
                    n_band += 1
    return {"n_events": n_events, "n_tes": n_tes, "n_band480_550": n_band}


def main():
    points = load_points()
    # --- live PARMA ---
    parma_table = []
    all_totals = {}
    all_abs_flux = {}
    for p in points:
        print(f"PARMA {p['point_id']}...", flush=True)
        meta, rows = run_parma(p)
        totals = particle_totals(rows)
        all_totals[p["point_id"]] = totals
        abs_flux = build_spectra_for_point(p["point_id"], rows)
        all_abs_flux[p["point_id"]] = abs_flux
        # dump raw meta
        row = {
            "point_id": p["point_id"],
            "day_mid": p["day_mid"],
            "altitude_km": p["altitude_km"],
            "latitude_deg": p["latitude_deg"],
            "longitude_deg": p["longitude_deg"],
            "analytic_prompt_scale": p["analytic_prompt_scale"],
            **{f"meta_{k}": v for k, v in meta.items()},
            **{f"flux_{k}": totals.get(k, 0.0) for k in sorted(totals)},
        }
        parma_table.append(row)
        # save raw rows sample size control: write per-point summary only
        (PKG / "02_sources/parma_live" / f"{p['point_id']}_meta.json").write_text(
            json.dumps({"meta": meta, "totals": totals, "n_rows": len(rows)}, indent=2) + "\n"
        )

    # scales vs REF
    ref_tot = all_totals["REF"]
    for row in parma_table:
        pid = row["point_id"]
        for part in PARTICLES:
            f = all_totals[pid].get(part, 0.0)
            fr = ref_tot.get(part, 0.0)
            row[f"scale_{part}"] = (f / fr) if fr > 0 else float("nan")
            sa = row["analytic_prompt_scale"]
            row[f"Q_env_{part}_vs_analytic"] = (
                (row[f"scale_{part}"] / sa) if sa and row[f"scale_{part}"] == row[f"scale_{part}"] else float("nan")
            )
    fields = sorted({k for r in parma_table for k in r})
    with (PKG / "02_sources/parma_live/live_parma_scales.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(parma_table)

    print("Live PARMA scales (eplus / n / gamma):")
    for r in parma_table:
        print(
            r["point_id"],
            "e+",
            f"{r.get('scale_eplus', float('nan')):.4f}",
            "Q",
            f"{r.get('Q_env_eplus_vs_analytic', float('nan')):.4f}",
            "n",
            f"{r.get('scale_n', float('nan')):.4f}",
            "g",
            f"{r.get('scale_gamma', float('nan')):.4f}",
            "ana",
            f"{r['analytic_prompt_scale']:.4f}",
        )

    # --- cosima multi-species ---
    run_rows = []
    for p in points:
        pid = p["point_id"]
        for particle in PARTICLES:
            events = EVENTS[particle]
            seed = 40000 + int(p["day_mid"] * 100) + PTYPE[particle]
            rundir = PKG / "04_prompt_smoke/per_point" / pid / particle
            rundir.mkdir(parents=True, exist_ok=True)
            run_prefix = (rundir / f"TrajVal_{pid}_{particle}").resolve()
            src = rundir / f"TrajVal_{pid}_{particle}.source"
            write_source_card(
                pid,
                particle,
                all_abs_flux[pid][particle],
                events,
                seed,
                src,
                run_prefix,
            )
            log = PKG / "logs" / f"{pid}_{particle}_cosima.log"
            print(f"COSIMA {pid} {particle} N={events} ...", flush=True)
            info = run_cosima(src, log)
            sims = list(rundir.glob("*.sim*"))
            print(
                f"  rc={info['rc']} wall={info['wall_s']:.1f}s gen={info['gen']} obs={info['obs_s']} sims={len(sims)}",
                flush=True,
            )
            stats = {}
            if sims:
                stats = extract_tes_stats(sims[0])
            run_rows.append(
                {
                    "point_id": pid,
                    "particle": particle,
                    "events": events,
                    "scale_live_parma": parma_table[[x["point_id"] for x in parma_table].index(pid)].get(
                        f"scale_{particle}", float("nan")
                    ),
                    "analytic_prompt_scale": p["analytic_prompt_scale"],
                    **info,
                    **stats,
                    "sim": str(sims[0].relative_to(PKG)) if sims else "",
                }
            )

    # rates
    for r in run_rows:
        obs = r.get("obs_s") or 0.0
        gen = r.get("gen") or 0.0
        r["gen_rate_hz"] = gen / obs if obs else float("nan")
        r["tes_rate_hz"] = (r.get("n_tes") or 0) / obs if obs else float("nan")
        r["band_rate_hz"] = (r.get("n_band480_550") or 0) / obs if obs else float("nan")

    # Q vs REF per particle
    ref_rates = {
        (r["particle"]): r
        for r in run_rows
        if r["point_id"] == "REF"
    }
    for r in run_rows:
        ref = ref_rates[r["particle"]]
        for key in ("gen_rate_hz", "tes_rate_hz", "band_rate_hz"):
            rr = ref[key]
            r[f"{key}_over_REF"] = (r[key] / rr) if rr and rr == rr and rr > 0 else float("nan")
            sa = r["analytic_prompt_scale"]
            sp = r["scale_live_parma"]
            r[f"Q_{key}_vs_analytic"] = (
                r[f"{key}_over_REF"] / sa if sa and r[f"{key}_over_REF"] == r[f"{key}_over_REF"] else float("nan")
            )
            r[f"Q_{key}_vs_live_parma"] = (
                r[f"{key}_over_REF"] / sp
                if sp and sp == sp and sp > 0 and r[f"{key}_over_REF"] == r[f"{key}_over_REF"]
                else float("nan")
            )

    fields = sorted({k for r in run_rows for k in r})
    with (PKG / "04_prompt_smoke/escalation_prompt_results.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(run_rows)

    # combined eplus+n+gamma band rate per point for rough multi-particle Q
    by_pt: dict[str, dict] = defaultdict(lambda: {"band": 0.0, "tes": 0.0, "obs_w": 0.0})
    for r in run_rows:
        # rate already /s — sum rates across particles
        pid = r["point_id"]
        by_pt[pid]["band"] += r["band_rate_hz"] if r["band_rate_hz"] == r["band_rate_hz"] else 0.0
        by_pt[pid]["tes"] += r["tes_rate_hz"] if r["tes_rate_hz"] == r["tes_rate_hz"] else 0.0
        by_pt[pid]["analytic"] = r["analytic_prompt_scale"]
        by_pt[pid]["parma_eplus"] = next(
            x["scale_eplus"] for x in parma_table if x["point_id"] == pid
        )

    ref_b = by_pt["REF"]["band"]
    ref_t = by_pt["REF"]["tes"]
    combined = []
    for pid, v in by_pt.items():
        row = {
            "point_id": pid,
            "band_rate_sum_hz": v["band"],
            "tes_rate_sum_hz": v["tes"],
            "band_over_REF": v["band"] / ref_b if ref_b > 0 else float("nan"),
            "tes_over_REF": v["tes"] / ref_t if ref_t > 0 else float("nan"),
            "analytic_prompt_scale": v["analytic"],
            "live_parma_eplus_scale": v["parma_eplus"],
        }
        row["Q_band_vs_analytic"] = (
            row["band_over_REF"] / row["analytic_prompt_scale"]
            if row["analytic_prompt_scale"]
            else float("nan")
        )
        row["Q_band_vs_parma_eplus"] = (
            row["band_over_REF"] / row["live_parma_eplus_scale"]
            if row["live_parma_eplus_scale"]
            else float("nan")
        )
        combined.append(row)

    with (PKG / "10_curve_validation/combined_species_Q.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(combined[0].keys()))
        w.writeheader()
        w.writerows(combined)

    decision = {
        "status": "ESCALATED_SMOKE_LIVE_PARMA_MULTI_SPECIES",
        "claim_level": "MEDIUM_SMOKE_NOT_FULL4",
        "particles": PARTICLES,
        "events": EVENTS,
        "parma_cwd_fix": "must run with cwd=parma_cpp",
        "parma_table": parma_table,
        "combined_Q": combined,
        "per_run": run_rows,
        "blocks_full_curve_claim": True,
        "notes": [
            "Live PARMA restored (cwd=parma_cpp).",
            "Spectra rebuilt per point/particle/angle from live PARMA.",
            "Cosima instant multi-species at REF/L1/L2/H1.",
            "Not full4 stats; W2 counts still limited — use gen_rate and broad TES rates cautiously.",
        ],
    }
    (PKG / "10_curve_validation/validation_decision.json").write_text(
        json.dumps(decision, indent=2) + "\n"
    )
    (PKG / "04_prompt_smoke/escalation_summary.json").write_text(
        json.dumps(decision, indent=2) + "\n"
    )
    print("\n=== Combined band Q ===")
    for r in combined:
        print(r)
    print("DONE")


if __name__ == "__main__":
    main()
