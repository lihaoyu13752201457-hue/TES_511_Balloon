#!/usr/bin/env python3
"""Build source-level visual records for cosmosray_bg_260516.

Outputs:
  source_injection_geometry_1000.png
  source_primary_summary.csv
  activation_rpip_mechanism_map.png
  activation_rpip_mechanism_summary.csv
  activation_rpip_volume_summary.csv
  activation_rpip_top_isotopes.csv
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import os
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECORDS = HERE.parent if HERE.name == "07_figure_scripts" else HERE
SOURCE_RECORDS = RECORDS / "01_source_injection_smoke"
ACTIVATION_RECORDS = RECORDS / "04_activation_rpip"
os.environ.setdefault("MPLCONFIGDIR", str(HERE / ".mplconfig"))
(HERE / ".mplconfig").mkdir(exist_ok=True)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle, Rectangle


ROOT = RECORDS.parent
BOUNDS = ROOT / "XZTES" / "bounds.json"
SOURCE_FILE = SOURCE_RECORDS / "source_smoke1000" / "mixed_fullsphere_1000.source"
SIM_FILE = SOURCE_RECORDS / "source_smoke1000" / "mixed_fullsphere_1000.sim.inc1.id1.sim.gz"
BUILDDIR = ROOT / "production_runs" / "buildup_equiv2602"
GROUNDSTATE_CORRECTIONS = ROOT / "production_runs" / "delay_fix_from_buildup_equiv2602" / "groundstate_activity_corrections.csv"

PARTICLE_BY_ID = {
    1: "gamma",
    2: "e+",
    3: "e-",
    4: "proton",
    6: "neutron",
    8: "mu+",
    9: "mu-",
    21: "alpha",
}

PARTICLE_COLORS = {
    "gamma": "#1f77b4",
    "e+": "#e377c2",
    "e-": "#17becf",
    "proton": "#d62728",
    "neutron": "#2ca02c",
    "mu+": "#ff7f0e",
    "mu-": "#9467bd",
    "alpha": "#8c564b",
    "unknown": "#7f7f7f",
}

MECH_COLORS = {
    "nCapture": "#7f3c8d",
    "neutronInelastic": "#e68310",
    "protonInelastic": "#d62728",
    "hadElastic": "#17becf",
    "CoulombScat": "#9467bd",
    "other": "#222222",
}

ISOTOPE_COLORS = [
    "#7f3c8d",
    "#e68310",
    "#3969ac",
    "#d62728",
    "#9467bd",
    "#17becf",
    "#f2b701",
    "#a05d56",
    "#e73f74",
    "#6b6ecf",
]


INIT_RE = re.compile(r"^IA INIT")
RPIP_RE = re.compile(
    r"^CC\s+IP\s+RP\s+(?P<vn>\S+)\s+"
    r"(?P<x>[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?)\s+"
    r"(?P<y>[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?)\s+"
    r"(?P<z>[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?)\s+"
    r"(?P<za>\d+)\s+(?P<exc>[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?)\s+"
    r"(?P<t>[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?)\s*(?P<rest>.*)$",
    re.IGNORECASE,
)
KV_RE = re.compile(r"(\w+)=([^\s]+)")


def load_bounds() -> dict:
    return json.loads(BOUNDS.read_text())


def rect(ax, x0, z0, w, h, color, alpha=0.28, ec="black", lw=0.45, zorder=1):
    patch = Rectangle((x0, z0), w, h, facecolor=color, edgecolor=ec, lw=lw, alpha=alpha, zorder=zorder)
    ax.add_patch(patch)
    return patch


def draw_xz_geometry(ax, bounds: dict, label=False, compact=False):
    colors = {
        "Al_Shell": "#a7a9ac",
        "BGO_Shield": "#84c184",
        "Cryo_Shell": "#c7c9cc",
        "W_Shield": "#555555",
        "Nb_Shield": "#5ac8d8",
    }
    order = ["Al_Shell", "BGO_Shield", "Cryo_Shell", "W_Shield", "Nb_Shield"]
    for name in order:
        sh = bounds["SHIELDS"][name]
        rout = sh["r_out"]
        rin = sh["r_in"]
        z0 = sh["z_out_bot"]
        z1 = sh["z_out_top"]
        zi0 = sh["z_in_bot"]
        zi1 = sh["z_in_top"]
        hole = sh.get("hole_r", rin)
        c = colors[name]
        rect(ax, -rout, z0, rout - rin, z1 - z0, c)
        rect(ax, rin, z0, rout - rin, z1 - z0, c)
        rect(ax, -rout, z0, 2 * rout, max(zi0 - z0, 0.0), c)
        rect(ax, -rout, zi1, rout - hole, max(z1 - zi1, 0.0), c)
        rect(ax, hole, zi1, rout - hole, max(z1 - zi1, 0.0), c)
        if label and not compact:
            ax.text(rout + 2, 0.5 * (z0 + z1), name, fontsize=7, va="center")

    cu = bounds["CU_BASE"]
    rect(ax, -cu["r_max"], cu["z_bot"], 2 * cu["r_max"], cu["z_top"] - cu["z_bot"], "#c98942", 0.55)
    pole = bounds["CU_SUPPORT"]
    rect(ax, -pole["r_max"], pole["z_bot"], 2 * pole["r_max"], pole["z_top"] - pole["z_bot"], "#c98942", 0.55)

    for sub in bounds["SUBSTRATES"]:
        rect(ax, -sub["r_max"], sub["z_center"] - sub["hz"], 2 * sub["r_max"], 2 * sub["hz"], "#4c78a8", 0.55)

    for layer in bounds["TES_LAYERS"]:
        rect(ax, -layer["r_max"], layer["z_center"] - layer["hz"], 2 * layer["r_max"], 2 * layer["hz"], "#e45756", 0.44)

    for win in bounds["WINDOWS"]:
        h = max(float(win["thick"]), 0.65 if not compact else 0.35)
        rect(ax, -win["r_max"], win["z_center"] - 0.5 * h, 2 * win["r_max"], h, "#b279d6", 0.45)

    col = bounds["COLLIMATOR"]
    rect(ax, -col["r_max"], col["z_center"] - col["hz"], 2 * col["r_max"], 2 * col["hz"], "#333333", 0.55)
    ax.axvline(0, color="0.55", lw=0.4, ls=":")


def draw_xz_geometry_outline(ax, bounds: dict):
    """Draw geometry as muted grayscale outlines so activation points carry color."""
    fills = {
        "Al_Shell": "#f2f2f2",
        "BGO_Shield": "#e0e0e0",
        "Cryo_Shell": "#eeeeee",
        "W_Shield": "#d0d0d0",
        "Nb_Shield": "#f7f7f7",
    }
    edges = {
        "Al_Shell": "#4d4d4d",
        "BGO_Shield": "#6f6f6f",
        "Cryo_Shell": "#8a8a8a",
        "W_Shield": "#252525",
        "Nb_Shield": "#737373",
    }
    for name in ["Al_Shell", "BGO_Shield", "Cryo_Shell", "W_Shield", "Nb_Shield"]:
        sh = bounds["SHIELDS"][name]
        rout = sh["r_out"]
        rin = sh["r_in"]
        z0 = sh["z_out_bot"]
        z1 = sh["z_out_top"]
        zi0 = sh["z_in_bot"]
        zi1 = sh["z_in_top"]
        hole = sh.get("hole_r", rin)
        fc = fills[name]
        ec = edges[name]
        rect(ax, -rout, z0, rout - rin, z1 - z0, fc, alpha=0.20, ec=ec, lw=0.8, zorder=1)
        rect(ax, rin, z0, rout - rin, z1 - z0, fc, alpha=0.20, ec=ec, lw=0.8, zorder=1)
        rect(ax, -rout, z0, 2 * rout, max(zi0 - z0, 0.0), fc, alpha=0.20, ec=ec, lw=0.8, zorder=1)
        rect(ax, -rout, zi1, rout - hole, max(z1 - zi1, 0.0), fc, alpha=0.20, ec=ec, lw=0.8, zorder=1)
        rect(ax, hole, zi1, rout - hole, max(z1 - zi1, 0.0), fc, alpha=0.20, ec=ec, lw=0.8, zorder=1)
        ax.text(rout + 1.8, 0.5 * (z0 + z1), name, fontsize=7, color=ec, va="center")

    cu = bounds["CU_BASE"]
    rect(ax, -cu["r_max"], cu["z_bot"], 2 * cu["r_max"], cu["z_top"] - cu["z_bot"], "#cfcfcf", 0.35, ec="#525252", lw=0.8, zorder=2)
    pole = bounds["CU_SUPPORT"]
    rect(ax, -pole["r_max"], pole["z_bot"], 2 * pole["r_max"], pole["z_top"] - pole["z_bot"], "#cfcfcf", 0.35, ec="#525252", lw=0.8, zorder=2)

    for sub in bounds["SUBSTRATES"]:
        rect(ax, -sub["r_max"], sub["z_center"] - sub["hz"], 2 * sub["r_max"], 2 * sub["hz"], "#f5f5f5", 0.7, ec="#666666", lw=0.55, zorder=3)

    for layer in bounds["TES_LAYERS"]:
        rect(ax, -layer["r_max"], layer["z_center"] - layer["hz"], 2 * layer["r_max"], 2 * layer["hz"], "none", 0.0, ec="#1a1a1a", lw=0.9, zorder=4)

    for win in bounds["WINDOWS"]:
        h = max(float(win["thick"]), 0.35)
        rect(ax, -win["r_max"], win["z_center"] - 0.5 * h, 2 * win["r_max"], h, "#f0f0f0", 0.5, ec="#525252", lw=0.55, zorder=4)

    col = bounds["COLLIMATOR"]
    rect(ax, -col["r_max"], col["z_center"] - col["hz"], 2 * col["r_max"], 2 * col["hz"], "#a8a8a8", 0.55, ec="#111111", lw=0.75, zorder=4)
    ax.axvline(0, color="0.45", lw=0.5, ls=":", zorder=4)


def parse_init_events(sim_file: Path) -> list[dict]:
    events = []
    with gzip.open(sim_file, "rt", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if not INIT_RE.match(line):
                continue
            parts = [p.strip() for p in line.split(";")]
            try:
                x = float(parts[4])
                y = float(parts[5])
                z = float(parts[6])
                pid = int(float(parts[15]))
                dx = float(parts[16])
                dy = float(parts[17])
                dz = float(parts[18])
                energy = float(parts[-1])
            except (ValueError, IndexError):
                continue
            particle = PARTICLE_BY_ID.get(pid, "unknown")
            theta = math.degrees(math.acos(max(-1.0, min(1.0, -dz))))
            events.append(
                {
                    "x": x,
                    "y": y,
                    "z": z,
                    "dx": dx,
                    "dy": dy,
                    "dz": dz,
                    "pid": pid,
                    "particle": particle,
                    "energy_keV": energy,
                    "theta_deg_from_top": theta,
                    "direction_class": "down" if dz < 0 else "up",
                }
            )
    return events


def write_primary_summary(events: list[dict]):
    out = SOURCE_RECORDS / "source_primary_summary.csv"
    counter = Counter((e["particle"], e["direction_class"]) for e in events)
    energy = defaultdict(list)
    for e in events:
        energy[(e["particle"], e["direction_class"])].append(e["energy_keV"])
    with out.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["particle", "direction_class", "count", "mean_energy_keV"])
        for key, count in sorted(counter.items()):
            vals = energy[key]
            w.writerow([key[0], key[1], count, sum(vals) / len(vals)])


def plot_source_geometry(events: list[dict], bounds: dict):
    fig = plt.figure(figsize=(14, 9), constrained_layout=True)
    gs = fig.add_gridspec(2, 3, width_ratios=[1.6, 1.0, 1.0])
    ax = fig.add_subplot(gs[:, 0])
    ax_xy = fig.add_subplot(gs[0, 1])
    ax_theta = fig.add_subplot(gs[0, 2])
    ax_bar = fig.add_subplot(gs[1, 1:])

    draw_xz_geometry(ax, bounds, label=False)
    lines_by_particle = defaultdict(list)
    points_by_particle = defaultdict(lambda: ([], []))
    max_len = 210.0
    for e in events:
        x0, z0 = e["x"], e["z"]
        x1 = x0 + e["dx"] * max_len
        z1 = z0 + e["dz"] * max_len
        p = e["particle"]
        lines_by_particle[p].append([(x0, z0), (x1, z1)])
        points_by_particle[p][0].append(x0)
        points_by_particle[p][1].append(z0)

    for particle, lines in lines_by_particle.items():
        lc = LineCollection(lines, colors=PARTICLE_COLORS.get(particle, "#7f7f7f"), linewidths=0.65, alpha=0.23)
        ax.add_collection(lc)
        xs, zs = points_by_particle[particle]
        ax.scatter(xs, zs, s=9, color=PARTICLE_COLORS.get(particle, "#7f7f7f"), alpha=0.65, label=particle, edgecolors="none")

    ax.set_title("1000 generated primaries: X-Z entry display")
    ax.set_xlabel("X")
    ax.set_ylabel("Z")
    ax.set_xlim(-230, 230)
    ax.set_ylim(-230, 230)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, lw=0.3, alpha=0.25)
    ax.legend(loc="lower left", fontsize=8, ncol=2, frameon=True)

    for particle in sorted(points_by_particle):
        xs = [e["x"] for e in events if e["particle"] == particle]
        ys = [e["y"] for e in events if e["particle"] == particle]
        ax_xy.scatter(xs, ys, s=10, color=PARTICLE_COLORS.get(particle, "#7f7f7f"), alpha=0.7, label=particle, edgecolors="none")
    ax_xy.add_patch(Circle((0, 0), 67, fill=False, lw=1.0, ec="black", alpha=0.7))
    ax_xy.set_title("Primary start points: X-Y")
    ax_xy.set_xlabel("X")
    ax_xy.set_ylabel("Y")
    ax_xy.set_xlim(-230, 230)
    ax_xy.set_ylim(-230, 230)
    ax_xy.set_aspect("equal", adjustable="box")
    ax_xy.grid(True, lw=0.3, alpha=0.25)

    theta_down = [e["theta_deg_from_top"] for e in events if e["direction_class"] == "down"]
    theta_up = [e["theta_deg_from_top"] for e in events if e["direction_class"] == "up"]
    bins = list(range(0, 181, 10))
    ax_theta.hist(theta_down, bins=bins, color="#4c78a8", alpha=0.75, label="down")
    ax_theta.hist(theta_up, bins=bins, color="#f58518", alpha=0.75, label="up")
    ax_theta.set_title("Incoming theta")
    ax_theta.set_xlabel("theta from +Z downward axis (deg)")
    ax_theta.set_ylabel("count")
    ax_theta.legend(fontsize=8)
    ax_theta.grid(True, lw=0.3, alpha=0.25)

    particle_counts = Counter(e["particle"] for e in events)
    labels = [p for p, _ in particle_counts.most_common()]
    values = [particle_counts[p] for p in labels]
    ax_bar.bar(labels, values, color=[PARTICLE_COLORS.get(p, "#7f7f7f") for p in labels])
    ax_bar.set_title("Generated particle mix in this 1000-trigger smoke run")
    ax_bar.set_ylabel("generated primaries")
    ax_bar.grid(axis="y", lw=0.3, alpha=0.25)
    for i, v in enumerate(values):
        ax_bar.text(i, v + max(values) * 0.01, str(v), ha="center", va="bottom", fontsize=8)

    fig.suptitle("Full-sphere atmospheric source, Cosima smoke1000", fontsize=14)
    fig.savefig(SOURCE_RECORDS / "source_injection_geometry_1000.png", dpi=220)
    plt.close(fig)


def category_mechanism(cproc: str) -> str:
    if cproc in MECH_COLORS:
        return cproc
    if cproc in {"nFission", "neutronFission"}:
        return "neutronInelastic"
    if "Capture" in cproc:
        return "nCapture"
    if "protonInelastic" in cproc:
        return "protonInelastic"
    if "neutronInelastic" in cproc:
        return "neutronInelastic"
    if "hadElastic" in cproc:
        return "hadElastic"
    if "Coulomb" in cproc:
        return "CoulombScat"
    return "other"


def nuclide_from_za(za: int) -> str:
    z = za // 1000
    a = za % 1000
    symbols = [
        "",
        "H",
        "He",
        "Li",
        "Be",
        "B",
        "C",
        "N",
        "O",
        "F",
        "Ne",
        "Na",
        "Mg",
        "Al",
        "Si",
        "P",
        "S",
        "Cl",
        "Ar",
        "K",
        "Ca",
        "Sc",
        "Ti",
        "V",
        "Cr",
        "Mn",
        "Fe",
        "Co",
        "Ni",
        "Cu",
        "Zn",
        "Ga",
        "Ge",
        "As",
        "Se",
        "Br",
        "Kr",
        "Rb",
        "Sr",
        "Y",
        "Zr",
        "Nb",
        "Mo",
        "Tc",
        "Ru",
        "Rh",
        "Pd",
        "Ag",
        "Cd",
        "In",
        "Sn",
        "Sb",
        "Te",
        "I",
        "Xe",
        "Cs",
        "Ba",
        "La",
        "Ce",
        "Pr",
        "Nd",
        "Pm",
        "Sm",
        "Eu",
        "Gd",
        "Tb",
        "Dy",
        "Ho",
        "Er",
        "Tm",
        "Yb",
        "Lu",
        "Hf",
        "Ta",
        "W",
        "Re",
        "Os",
        "Ir",
        "Pt",
        "Au",
        "Hg",
        "Tl",
        "Pb",
        "Bi",
    ]
    sym = symbols[z] if 0 <= z < len(symbols) else f"Z{z}"
    return f"{sym}-{a}"


def iter_rpip_files():
    return sorted(BUILDDIR.glob("*.sim.gz"))


def load_removed_groundstate_za() -> dict[int, dict]:
    """Return ZA values that the existing ground-state fix removes as stable/negligible."""
    removed: dict[int, dict] = {}
    if not GROUNDSTATE_CORRECTIONS.exists():
        return removed
    with GROUNDSTATE_CORRECTIONS.open(newline="") as fh:
        for row in csv.DictReader(fh):
            action = row.get("action", "")
            if action != "removed_negligible_or_stable":
                continue
            try:
                za = int(row["ZA"])
            except (KeyError, ValueError):
                continue
            removed.setdefault(
                za,
                {
                    "nuclide": row.get("nuclide", nuclide_from_za(za)),
                    "reason": row.get("nubase_why", action),
                    "half_life_s": row.get("nubase_half_life_s", ""),
                    "count": 0,
                },
            )
    return removed


def scan_rpip(max_points: int, per_file_limit: int, full_scan: bool, seed: int = 260516):
    files = iter_rpip_files()
    rng = random.Random(seed)
    removed_za = load_removed_groundstate_za()
    sample = []
    total = 0
    raw_total = 0
    excluded = Counter()
    mechanism = Counter()
    volume = Counter()
    primary = Counter()
    isotope = Counter()
    mechanism_by_primary = Counter()

    for idx, fp in enumerate(files, 1):
        file_points = 0
        with gzip.open(fp, "rt", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                if not line.startswith("CC IP RP"):
                    continue
                m = RPIP_RE.match(line.strip())
                if not m:
                    continue
                rest = dict(KV_RE.findall(m.group("rest")))
                cproc = rest.get("cproc", "unknown")
                prim = rest.get("prim", "unknown")
                cat = category_mechanism(cproc)
                vn = m.group("vn")
                za = int(m.group("za"))
                raw_total += 1
                if za in removed_za:
                    excluded[(za, removed_za[za]["nuclide"], removed_za[za]["reason"], removed_za[za]["half_life_s"])] += 1
                    file_points += 1
                    if not full_scan and file_points >= per_file_limit:
                        break
                    continue
                total += 1
                item = {
                    "x": float(m.group("x")),
                    "y": float(m.group("y")),
                    "z": float(m.group("z")),
                    "vn": vn,
                    "za": za,
                    "nuclide": nuclide_from_za(za),
                    "cproc": cproc,
                    "mechanism": cat,
                    "prim": prim,
                }
                mechanism[cat] += 1
                volume[vn] += 1
                primary[prim] += 1
                isotope[(za, item["nuclide"])] += 1
                mechanism_by_primary[(cat, prim)] += 1
                if len(sample) < max_points:
                    sample.append(item)
                else:
                    j = rng.randrange(total)
                    if j < max_points:
                        sample[j] = item
                file_points += 1
                if not full_scan and file_points >= per_file_limit:
                    break
        if idx % 10 == 0 or idx == len(files):
            print(
                f"scanned {idx}/{len(files)} buildup SIM files; "
                f"kept RPIP={total} excluded={sum(excluded.values())}",
                flush=True,
            )
    return {
        "sample": sample,
        "total": total,
        "raw_total": raw_total,
        "excluded": excluded,
        "files": len(files),
        "per_file_limit": per_file_limit,
        "full_scan": full_scan,
        "mechanism": mechanism,
        "volume": volume,
        "primary": primary,
        "isotope": isotope,
        "mechanism_by_primary": mechanism_by_primary,
    }


def write_counter_csv(path: Path, header: list[str], rows):
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for row in rows:
            w.writerow(row)


def write_rpip_summaries(stats: dict):
    total = stats["total"]
    with (ACTIVATION_RECORDS / "activation_rpip_points_sample.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["x", "y", "z", "volume", "ZA", "nuclide", "mechanism", "cproc", "primary"])
        for p in stats["sample"]:
            w.writerow([p["x"], p["y"], p["z"], p["vn"], p["za"], p["nuclide"], p["mechanism"], p["cproc"], p["prim"]])
    write_counter_csv(
        ACTIVATION_RECORDS / "activation_rpip_mechanism_summary.csv",
        ["mechanism", "count", "fraction"],
        ((k, v, v / total if total else 0.0) for k, v in stats["mechanism"].most_common()),
    )
    write_counter_csv(
        ACTIVATION_RECORDS / "activation_rpip_volume_summary.csv",
        ["volume", "count", "fraction"],
        ((k, v, v / total if total else 0.0) for k, v in stats["volume"].most_common()),
    )
    write_counter_csv(
        ACTIVATION_RECORDS / "activation_rpip_top_isotopes.csv",
        ["ZA", "nuclide", "count", "fraction"],
        ((za, nuc, v, v / total if total else 0.0) for (za, nuc), v in stats["isotope"].most_common(60)),
    )
    excluded_total = sum(stats["excluded"].values())
    write_counter_csv(
        ACTIVATION_RECORDS / "activation_rpip_excluded_stable_or_negligible.csv",
        ["ZA", "nuclide", "reason", "half_life_s", "excluded_raw_rpip_records", "fraction_of_excluded"],
        (
            (za, nuc, reason, hl, v, v / excluded_total if excluded_total else 0.0)
            for (za, nuc, reason, hl), v in stats["excluded"].most_common()
        ),
    )


def plot_rpip_map(stats: dict, bounds: dict):
    sample = stats["sample"]
    fig = plt.figure(figsize=(13.5, 8.5), constrained_layout=True)
    gs = fig.add_gridspec(2, 3, width_ratios=[1.55, 1.0, 1.0])
    ax = fig.add_subplot(gs[:, 0])
    ax_mech = fig.add_subplot(gs[0, 1])
    ax_vol = fig.add_subplot(gs[0, 2])
    ax_iso = fig.add_subplot(gs[1, 1])
    ax_note = fig.add_subplot(gs[1, 2])

    draw_xz_geometry(ax, bounds, label=False)
    by_mech = defaultdict(lambda: ([], []))
    for p in sample:
        by_mech[p["mechanism"]][0].append(p["x"])
        by_mech[p["mechanism"]][1].append(p["z"])
    for mech, (xs, zs) in by_mech.items():
        ax.scatter(
            xs,
            zs,
            s=4.0,
            color=MECH_COLORS.get(mech, "#7f7f7f"),
            alpha=0.48,
            label=mech,
            edgecolors="none",
            rasterized=True,
            zorder=8,
        )
    ax.set_title(
        "Delayed-relevant RPIP points on XZTES X-Z\n"
        "material-colored geometry; points are mechanism colors"
    )
    ax.set_xlabel("X")
    ax.set_ylabel("Z")
    ax.set_xlim(-78, 78)
    ax.set_ylim(-82, 135)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, lw=0.3, alpha=0.25)
    ax.legend(loc="upper left", fontsize=8, frameon=True)

    mechs = stats["mechanism"].most_common()
    ax_mech.barh([m for m, _ in mechs], [v for _, v in mechs], color=[MECH_COLORS.get(m, "#7f7f7f") for m, _ in mechs])
    ax_mech.invert_yaxis()
    ax_mech.set_title("Activation mechanism count")
    ax_mech.set_xlabel("RPIP points")
    ax_mech.grid(axis="x", lw=0.3, alpha=0.25)

    vols = stats["volume"].most_common(10)
    ax_vol.barh([v for v, _ in vols], [c for _, c in vols], color="#4c78a8")
    ax_vol.invert_yaxis()
    ax_vol.set_title("Top production volumes")
    ax_vol.set_xlabel("RPIP points")
    ax_vol.grid(axis="x", lw=0.3, alpha=0.25)

    isos = stats["isotope"].most_common(10)
    labels = [nuc for (_, nuc), _ in isos]
    vals = [c for _, c in isos]
    ax_iso.barh(labels, vals, color="#636363")
    ax_iso.invert_yaxis()
    ax_iso.set_title("Top produced isotopes by RPIP count")
    ax_iso.set_xlabel("RPIP points")
    ax_iso.grid(axis="x", lw=0.3, alpha=0.25)

    ax_note.axis("off")
    scan_note = "full scan" if stats["full_scan"] else f"per-file cap={stats['per_file_limit']:,}; {stats['files']} files"
    ax_note.text(
        0.0,
        0.96,
        "Color rule\n\n"
        "Geometry: original material colors\n"
        "Activation points: colored by mechanism\n"
        "No activation point category uses BGO-like green\n\n"
        f"Scan: {scan_note}\n"
        f"Raw sampled RPIP: {stats['raw_total']:,}\n"
        f"Kept delayed-relevant: {stats['total']:,}\n"
        f"Filtered stable/negligible: {sum(stats['excluded'].values()):,}\n\n"
        "Filtering uses existing ground-state corrections\n"
        "before plotting delayed-relevant points.",
        fontsize=9,
        va="top",
    )

    fig.suptitle("Delayed-relevant activation points on material-colored XZTES geometry", fontsize=14)
    fig.savefig(ACTIVATION_RECORDS / "activation_rpip_mechanism_map.png", dpi=220)
    plt.close(fig)


def plot_rpip_isotope_map(stats: dict, bounds: dict):
    sample = stats["sample"]
    top_keys = [key for key, _ in stats["isotope"].most_common(8)]
    color_by_key = {key: ISOTOPE_COLORS[i % len(ISOTOPE_COLORS)] for i, key in enumerate(top_keys)}

    fig, ax = plt.subplots(figsize=(8.2, 9.0), constrained_layout=True)
    draw_xz_geometry(ax, bounds, label=False)

    other_x, other_z = [], []
    grouped = defaultdict(lambda: ([], []))
    for p in sample:
        key = (p["za"], p["nuclide"])
        if key in color_by_key:
            grouped[key][0].append(p["x"])
            grouped[key][1].append(p["z"])
        else:
            other_x.append(p["x"])
            other_z.append(p["z"])

    if other_x:
        ax.scatter(other_x, other_z, s=2.5, color="#bdbdbd", alpha=0.25, label="other", edgecolors="none", rasterized=True, zorder=7)
    for key, (xs, zs) in grouped.items():
        ax.scatter(xs, zs, s=4.5, color=color_by_key[key], alpha=0.55, label=key[1], edgecolors="none", rasterized=True, zorder=8)

    ax.set_title("Delayed-relevant RPIP points by isotope\nmaterial-colored geometry")
    ax.set_xlabel("X")
    ax.set_ylabel("Z")
    ax.set_xlim(-78, 84)
    ax.set_ylim(-82, 135)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, lw=0.3, alpha=0.22)
    ax.legend(loc="upper left", fontsize=8, frameon=True)
    fig.savefig(ACTIVATION_RECORDS / "activation_rpip_isotope_map.png", dpi=220)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-rpip-points", type=int, default=120000)
    ap.add_argument("--rpip-lines-per-file", type=int, default=2500)
    ap.add_argument("--full-rpip-scan", action="store_true")
    ap.add_argument("--skip-rpip", action="store_true")
    args = ap.parse_args()

    bounds = load_bounds()
    events = parse_init_events(SIM_FILE)
    if not events:
        raise SystemExit(f"No IA INIT records found in {SIM_FILE}")
    write_primary_summary(events)
    plot_source_geometry(events, bounds)
    print(f"wrote source figure from {len(events)} primary INIT records")

    if not args.skip_rpip:
        stats = scan_rpip(args.max_rpip_points, args.rpip_lines_per_file, args.full_rpip_scan)
        write_rpip_summaries(stats)
        plot_rpip_map(stats, bounds)
        plot_rpip_isotope_map(stats, bounds)
        print(
            f"wrote RPIP figure from {stats['total']} kept production records; "
            f"excluded {sum(stats['excluded'].values())} stable/negligible raw records"
        )


if __name__ == "__main__":
    main()
