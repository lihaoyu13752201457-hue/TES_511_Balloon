#!/usr/bin/env python3
"""Create event-level source timing diagnostics from a 100-event Cosima SIM."""

from __future__ import annotations

import csv
import gzip
import json
import math
import os
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECORDS = HERE.parent if HERE.name == "07_figure_scripts" else HERE
SOURCE_RECORDS = RECORDS / "01_source_injection_smoke"
EVENT_TIMING_RECORDS = SOURCE_RECORDS / "event_timing_smoke"
os.environ.setdefault("MPLCONFIGDIR", str(HERE / ".mplconfig"))
(HERE / ".mplconfig").mkdir(exist_ok=True)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle

from make_source_visuals import PARTICLE_BY_ID, PARTICLE_COLORS, draw_xz_geometry, load_bounds


SIM_FILE = SOURCE_RECORDS / "source_smoke1000" / "mixed_fullsphere_100_vrml.sim.inc1.id1.sim.gz"
EVENTS_CSV = EVENT_TIMING_RECORDS / "source_time_trajectory_100.csv"
HITS_CSV = SOURCE_RECORDS / "source_hit_time_response_100.csv"
SUMMARY_JSON = EVENT_TIMING_RECORDS / "source_time_trajectory_summary.json"
OUT_PNG = EVENT_TIMING_RECORDS / "source_time_trajectory_100.png"

C_CM_PER_NS = 29.9792458
DISPLAY_PATH_CM = 260.0

REST_MASS_KEV = {
    "e+": 510.99895,
    "e-": 510.99895,
    "proton": 938272.08816,
    "neutron": 939565.42052,
    "mu+": 105658.3755,
    "mu-": 105658.3755,
    "alpha": 3727379.378,
}

FLOAT = r"[+-]?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?"
HIT_RE = re.compile(
    rf"^CC HIT (?P<volume>\S+) "
    rf"edep_keV=(?P<edep>{FLOAT}) "
    rf"x=(?P<x>{FLOAT}) y=(?P<y>{FLOAT}) z=(?P<z>{FLOAT}) "
    rf"t=(?P<t>{FLOAT}) "
    r"sec=(?P<sec>\S+) .*? prim=(?P<prim>\S+) .*? cproc=(?P<cproc>\S+)"
)


def parse_ia(line: str) -> dict | None:
    parts = [part.strip() for part in line.split(";")]
    if len(parts) < 19:
        return None
    tokens = parts[0].split()
    if len(tokens) < 2 or tokens[0] != "IA":
        return None
    try:
        pid = int(float(parts[15]))
        dx, dy, dz = float(parts[16]), float(parts[17]), float(parts[18])
        return {
            "kind": tokens[1],
            "t_local_s": float(parts[3]),
            "x": float(parts[4]),
            "y": float(parts[5]),
            "z": float(parts[6]),
            "pid": pid,
            "particle": PARTICLE_BY_ID.get(pid, "unknown"),
            "dx": dx,
            "dy": dy,
            "dz": dz,
            "energy_keV": float(parts[-1]),
        }
    except ValueError:
        return None


def parse_sim(sim_file: Path) -> tuple[list[dict], list[dict]]:
    events = []
    hits = []
    current = None

    def finish_current():
        if current and current.get("init") and current.get("ti_s") is not None:
            events.append(current)

    with gzip.open(sim_file, "rt", encoding="utf-8", errors="ignore") as fh:
        for raw in fh:
            line = raw.strip()
            if line == "SE":
                finish_current()
                current = {"id": None, "ti_s": None, "ed_keV": None, "ec_keV": None, "init": None, "ia": []}
                continue
            if current is None:
                continue
            if line.startswith("ID "):
                fields = line.split()
                current["id"] = int(fields[1]) if len(fields) > 1 else None
            elif line.startswith("TI "):
                current["ti_s"] = float(line.split()[1])
            elif line.startswith("ED "):
                current["ed_keV"] = float(line.split()[1])
            elif line.startswith("EC "):
                current["ec_keV"] = float(line.split()[1])
            elif line.startswith("IA "):
                ia = parse_ia(line)
                if ia is None:
                    continue
                current["ia"].append(ia)
                if ia["kind"] == "INIT":
                    current["init"] = ia
            elif line.startswith("CC HIT"):
                match = HIT_RE.match(line)
                if not match:
                    continue
                hit = {key: match.group(key) for key in match.groupdict()}
                for key in ("edep", "x", "y", "z", "t"):
                    hit[key] = float(hit[key])
                hit["event_id"] = current["id"]
                hit["event_ti_s"] = current["ti_s"]
                hit["t_abs_s"] = (current["ti_s"] or 0.0) + hit["t"]
                hits.append(hit)
    finish_current()
    return events, hits


def beta_for(particle: str, energy_keV: float) -> float:
    if particle == "gamma":
        return 1.0
    rest = REST_MASS_KEV.get(particle)
    if rest is None or energy_keV <= 0:
        return 1.0
    gamma = 1.0 + energy_keV / rest
    return math.sqrt(max(0.0, 1.0 - 1.0 / (gamma * gamma)))


def event_rows(events: list[dict]) -> list[dict]:
    rows = []
    for event in events:
        init = event["init"]
        dx, dy, dz = init["dx"], init["dy"], init["dz"]
        norm = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
        ux, uy, uz = dx / norm, dy / norm, dz / norm
        particle = init["particle"]
        beta = beta_for(particle, init["energy_keV"])
        tof_ns = DISPLAY_PATH_CM / max(beta * C_CM_PER_NS, 1.0e-12)
        theta = math.degrees(math.acos(max(-1.0, min(1.0, -uz))))
        rows.append(
            {
                "event_id": event["id"],
                "ti_s": event["ti_s"],
                "ti_us": event["ti_s"] * 1.0e6,
                "particle": particle,
                "energy_keV": init["energy_keV"],
                "x0_cm": init["x"],
                "y0_cm": init["y"],
                "z0_cm": init["z"],
                "ux": ux,
                "uy": uy,
                "uz": uz,
                "beta": beta,
                "display_path_cm": DISPLAY_PATH_CM,
                "display_tof_ns": tof_ns,
                "x1_cm": init["x"] + ux * DISPLAY_PATH_CM,
                "y1_cm": init["y"] + uy * DISPLAY_PATH_CM,
                "z1_cm": init["z"] + uz * DISPLAY_PATH_CM,
                "theta_deg_from_top": theta,
                "ed_keV": event["ed_keV"],
                "ec_keV": event["ec_keV"],
                "ia_records": len(event["ia"]),
            }
        )
    return rows


def write_csvs(rows: list[dict], hits: list[dict]):
    with EVENTS_CSV.open("w", newline="") as fh:
        fields = list(rows[0].keys()) if rows else []
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    hit_fields = [
        "event_id",
        "event_ti_s",
        "t",
        "t_abs_s",
        "volume",
        "edep",
        "x",
        "y",
        "z",
        "sec",
        "prim",
        "cproc",
    ]
    with HITS_CSV.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=hit_fields)
        writer.writeheader()
        for hit in hits:
            writer.writerow({key: hit.get(key, "") for key in hit_fields})


def write_summary(rows: list[dict], hits: list[dict]):
    particle_counts = Counter(row["particle"] for row in rows)
    hit_volume_counts = Counter(hit["volume"] for hit in hits)
    hit_particle_counts = Counter(hit["sec"] for hit in hits)
    summary = {
        "sim_file": str(SIM_FILE.relative_to(RECORDS)),
        "events": len(rows),
        "hits": len(hits),
        "event_time_min_s": min(row["ti_s"] for row in rows) if rows else None,
        "event_time_max_s": max(row["ti_s"] for row in rows) if rows else None,
        "event_time_span_s": (max(row["ti_s"] for row in rows) - min(row["ti_s"] for row in rows)) if rows else None,
        "particle_counts": dict(particle_counts.most_common()),
        "hit_volume_counts": dict(hit_volume_counts.most_common()),
        "hit_secondary_counts": dict(hit_particle_counts.most_common()),
        "display_path_cm": DISPLAY_PATH_CM,
        "c_cm_per_ns": C_CM_PER_NS,
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")


def plot(rows: list[dict], hits: list[dict]):
    bounds = load_bounds()
    t_us = np.array([row["ti_us"] for row in rows])
    norm = plt.Normalize(float(t_us.min()), float(t_us.max()))
    cmap = plt.get_cmap("viridis")

    fig = plt.figure(figsize=(16, 9.5), constrained_layout=True)
    gs = fig.add_gridspec(2, 3, width_ratios=[1.45, 1.0, 1.0])
    ax_traj = fig.add_subplot(gs[:, 0])
    ax_xyz = fig.add_subplot(gs[0, 1])
    ax_xy = fig.add_subplot(gs[0, 2])
    ax_hit_xz = fig.add_subplot(gs[1, 1])
    ax_hit_t = fig.add_subplot(gs[1, 2])

    draw_xz_geometry(ax_traj, bounds, label=False, compact=True)
    segments = [[(row["x0_cm"], row["z0_cm"]), (row["x1_cm"], row["z1_cm"])] for row in rows]
    lc = LineCollection(segments, cmap=cmap, norm=norm, linewidths=0.8, alpha=0.42)
    lc.set_array(t_us)
    ax_traj.add_collection(lc)
    ax_traj.scatter(
        [row["x0_cm"] for row in rows],
        [row["z0_cm"] for row in rows],
        c=t_us,
        cmap=cmap,
        norm=norm,
        s=14,
        edgecolors="black",
        linewidths=0.25,
        zorder=8,
    )
    ax_traj.set_title("100 native primaries: X-Z trajectories colored by event time")
    ax_traj.set_xlabel("X (cm)")
    ax_traj.set_ylabel("Z (cm)")
    ax_traj.set_xlim(-235, 235)
    ax_traj.set_ylim(-235, 235)
    ax_traj.set_aspect("equal", adjustable="box")
    ax_traj.grid(True, lw=0.3, alpha=0.25)
    fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax_traj, label="event time TI (us)")

    ax_xyz.plot(t_us, [row["x0_cm"] for row in rows], ".-", ms=3, lw=0.8, label="x0")
    ax_xyz.plot(t_us, [row["y0_cm"] for row in rows], ".-", ms=3, lw=0.8, label="y0")
    ax_xyz.plot(t_us, [row["z0_cm"] for row in rows], ".-", ms=3, lw=0.8, label="z0")
    ax_xyz.set_title("Primary start position vs observation time")
    ax_xyz.set_xlabel("TI (us)")
    ax_xyz.set_ylabel("position (cm)")
    ax_xyz.grid(True, lw=0.3, alpha=0.25)
    ax_xyz.legend(fontsize=8, ncol=3)

    ax_xy.scatter(
        [row["x0_cm"] for row in rows],
        [row["y0_cm"] for row in rows],
        c=t_us,
        cmap=cmap,
        norm=norm,
        s=18,
        edgecolors="black",
        linewidths=0.25,
    )
    ax_xy.add_patch(Circle((0, 0), math.sqrt(70685.8 / math.pi), fill=False, ec="black", lw=0.8, alpha=0.55))
    ax_xy.set_title("Primary start points: X-Y")
    ax_xy.set_xlabel("X (cm)")
    ax_xy.set_ylabel("Y (cm)")
    ax_xy.set_xlim(-235, 235)
    ax_xy.set_ylim(-235, 235)
    ax_xy.set_aspect("equal", adjustable="box")
    ax_xy.grid(True, lw=0.3, alpha=0.25)

    draw_xz_geometry(ax_hit_xz, bounds, label=False, compact=True)
    if hits:
        hit_abs_us = np.array([hit["t_abs_s"] * 1.0e6 for hit in hits])
        hit_norm = plt.Normalize(float(hit_abs_us.min()), float(hit_abs_us.max()))
        sizes = [10.0 + 18.0 * math.log10(hit["edep"] + 1.0) for hit in hits]
        ax_hit_xz.scatter(
            [hit["x"] for hit in hits],
            [hit["z"] for hit in hits],
            c=hit_abs_us,
            cmap="plasma",
            norm=hit_norm,
            s=sizes,
            alpha=0.72,
            edgecolors="black",
            linewidths=0.2,
            zorder=8,
        )
        fig.colorbar(plt.cm.ScalarMappable(norm=hit_norm, cmap="plasma"), ax=ax_hit_xz, label="absolute hit time (us)")
    else:
        ax_hit_xz.text(0.5, 0.5, "No CC HIT records", transform=ax_hit_xz.transAxes, ha="center", va="center")
    ax_hit_xz.set_title("Detector hit positions: X-Z")
    ax_hit_xz.set_xlabel("X (cm)")
    ax_hit_xz.set_ylabel("Z (cm)")
    ax_hit_xz.set_xlim(-78, 78)
    ax_hit_xz.set_ylim(-82, 135)
    ax_hit_xz.set_aspect("equal", adjustable="box")
    ax_hit_xz.grid(True, lw=0.3, alpha=0.25)

    if hits:
        volumes = sorted({hit["volume"] for hit in hits})
        palette = plt.get_cmap("tab10")
        color_by_volume = {vol: palette(i % 10) for i, vol in enumerate(volumes)}
        for vol in volumes:
            group = [hit for hit in hits if hit["volume"] == vol]
            ax_hit_t.scatter(
                [hit["t"] * 1.0e9 for hit in group],
                [hit["edep"] for hit in group],
                s=18,
                color=color_by_volume[vol],
                alpha=0.75,
                label=vol,
                edgecolors="none",
            )
        ax_hit_t.set_yscale("log")
        ax_hit_t.legend(fontsize=8)
    else:
        ax_hit_t.text(0.5, 0.5, "No CC HIT records", transform=ax_hit_t.transAxes, ha="center", va="center")
    ax_hit_t.set_title("Detector response time within event")
    ax_hit_t.set_xlabel("local hit time after primary birth (ns)")
    ax_hit_t.set_ylabel("hit energy deposit (keV)")
    ax_hit_t.grid(True, which="both", lw=0.3, alpha=0.25)

    fig.suptitle("Time-dependent source trajectories and detector hit response, native 100-event run", fontsize=14)
    fig.savefig(OUT_PNG, dpi=220)
    plt.close(fig)


def main():
    events, hits = parse_sim(SIM_FILE)
    rows = event_rows(events)
    write_csvs(rows, hits)
    write_summary(rows, hits)
    plot(rows, hits)
    print(f"wrote {OUT_PNG} from {len(rows)} events and {len(hits)} hit records")


if __name__ == "__main__":
    main()
