#!/usr/bin/env python3
"""Build a true RPIP production-position map for Step03.

This is intentionally separate from ``delay_source_2d_schematic.png``:

* this script visualizes true ``CC IP RP`` production positions from buildup
  SIM files;
* the delayed Cosima source itself is the compressed z-bin + radial-profile
  representation written by ``makedecaysourcewithplot_rpip.py``.
"""

from __future__ import annotations

import csv
import gzip
import json
import math
import os
import random
import re
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
STEP = Path(__file__).resolve().parents[1]
OUT = STEP / "outputs"
BOUNDS = ROOT / "outputs" / "geometry" / "XZTES_ADR_v4c_mkflange_cm" / "bounds.json"
BUILDUP = ROOT / "runs" / "step02_buildup_equiv2602_aligned"
INVENTORY = STEP / "source_snapshots" / "activation_inventory_day15.csv"
G4_DATA = Path("/home/ubuntu/MEGAlib_Install/megalib-main/external/geant4_v10.02.p03/share/Geant4-10.2.3/data")
G4_RADIOACTIVE = Path(os.environ.get("G4RADIOACTIVEDATA", str(G4_DATA / "RadioactiveDecay4.3.2")))
G4_LEVEL_GAMMA = Path(os.environ.get("G4LEVELGAMMADATA", str(G4_DATA / "PhotonEvaporation3.2")))

SAMPLE_SIZE = 50000
SEED = 260530
W1_LO_KEV = 500.99393711182086
W1_HI_KEV = 521.0060628881791
BRANCH_INTENSITY_MIN = 1.0e-12
LEVEL_MATCH_TOL_KEV = 2.0
MAX_LABEL_LINES = 4

SYMBOLS = [
    None, "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne", "Na", "Mg",
    "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca", "Sc", "Ti", "V", "Cr",
    "Mn", "Fe", "Co", "Ni", "Cu", "Zn", "Ga", "Ge", "As", "Se", "Br", "Kr",
    "Rb", "Sr", "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
    "In", "Sn", "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
    "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu", "Hf",
    "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg", "Tl", "Pb", "Bi", "Po",
    "At", "Rn", "Fr", "Ra", "Ac", "Th", "Pa", "U", "Np", "Pu", "Am", "Cm",
    "Bk", "Cf", "Es", "Fm", "Md", "No", "Lr", "Rf", "Db", "Sg", "Bh", "Hs",
    "Mt", "Ds", "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og",
]

IP_RE = re.compile(
    r"^CC\s+IP\s+(?P<proc>\S+)\s+(?P<vn>\S+)\s+"
    r"(?P<x>[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?)\s+"
    r"(?P<y>[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?)\s+"
    r"(?P<z>[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?)\s+"
    r"(?P<za>\d+)\s+(?P<exc>[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?)\s+"
    r"(?P<t>[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?)"
    r"(?:\s+.*)?$",
    re.IGNORECASE,
)
RE_SEG_SHIELD = re.compile(r"^(Nb_Shield|W_Shield|Cryo_Shell|BGO_Shield|Al_Shell)(?:_p\d+_z\d+)?$", re.I)
RE_TP = re.compile(r"^TP_L(?P<l>\d+)_\d+$", re.I)
RE_TESPIX = re.compile(r"^TES_Pixel_L(?P<l>\d+)$", re.I)
RE_COLLBAR = re.compile(r"^(CollBar[XY])_\d+$", re.I)


def canon_vn(vn: str) -> str:
    if not vn:
        return "Other"
    n = str(vn)
    m = RE_SEG_SHIELD.match(n)
    if m:
        return m.group(1)
    m = RE_TESPIX.match(n)
    if m:
        return f"TES_L{int(m.group('l'))}"
    if n.startswith("TES_L"):
        return n
    m = RE_TP.match(n)
    if m:
        return f"TES_L{int(m.group('l'))}"
    m = RE_COLLBAR.match(n)
    if m:
        return m.group(1)
    if n in ("Cu_Base", "Cu_SupportPole", "CU_BASE", "CU_SUPPORT", "Copper"):
        return "Copper"
    if n in ("Collimator", "CollimatorVac", "CollimatorEnvelope"):
        return "CollimatorVac"
    if "window" in n.lower() or n.lower().startswith("win"):
        return "Window"
    return n


def read_inventory() -> tuple[set[tuple[str, int]], dict[tuple[str, int], str]]:
    keys: set[tuple[str, int]] = set()
    nuclides: dict[tuple[str, int], str] = {}
    with INVENTORY.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                activity = float(row["Activity_Bq"])
                za = int(row["ZA"])
            except (KeyError, ValueError):
                continue
            if activity <= 0.0:
                continue
            key = (canon_vn(row.get("VN", "")), za)
            keys.add(key)
            nuclides[key] = row.get("nuclide", str(za))
    return keys, nuclides


def split_za(za: int) -> tuple[int, int]:
    return za // 1000, za % 1000


def nuclide_label_from_za(za: int) -> str:
    z, a = split_za(za)
    if 0 < z < len(SYMBOLS):
        return f"{SYMBOLS[z]}-{a}"
    return str(za)


@lru_cache(maxsize=None)
def load_level_transitions(z: int, a: int) -> dict[float, list[dict]]:
    path = G4_LEVEL_GAMMA / f"z{z}.a{a}"
    transitions: dict[float, list[dict]] = defaultdict(list)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 7:
                continue
            try:
                level = float(parts[0])
                energy = float(parts[1])
                gamma_probability = float(parts[2])
                alpha = float(parts[6])
            except ValueError:
                continue
            if energy > 0.0 and gamma_probability > 0.0:
                transitions[round(level, 6)].append(
                    {
                        "energy_keV": energy,
                        "gamma_probability": gamma_probability,
                        "alpha": max(0.0, alpha),
                    }
                )
    return dict(transitions)


def nearest_level(levels: list[float], target: float) -> float | None:
    if not levels:
        return None
    level = min(levels, key=lambda value: abs(value - target))
    if abs(level - target) > LEVEL_MATCH_TOL_KEV:
        return None
    return level


@lru_cache(maxsize=None)
def collect_w1_gamma_yields(z: int, a: int, excitation_keV: float) -> tuple[tuple[float, float], ...]:
    transitions = load_level_transitions(z, a)
    levels = sorted(transitions)

    def walk(level_energy: float, depth: int = 0, stack: tuple[float, ...] = ()) -> dict[float, float]:
        if depth > 24:
            return {}
        level = nearest_level(levels, level_energy)
        if level is None or level in stack:
            return {}

        rows = transitions.get(level, [])
        weights = [
            max(0.0, float(row["gamma_probability"])) * (1.0 + max(0.0, float(row["alpha"])))
            for row in rows
        ]
        total_weight = sum(weights)
        if total_weight <= 0.0:
            return {}

        yields: dict[float, float] = defaultdict(float)
        for row, weight in zip(rows, weights):
            energy = float(row["energy_keV"])
            alpha = max(0.0, float(row["alpha"]))
            channel_probability = weight / total_weight
            gamma_probability = 1.0 / (1.0 + alpha)
            if W1_LO_KEV <= energy <= W1_HI_KEV:
                yields[round(energy, 4)] += channel_probability * gamma_probability
            lower = max(0.0, level - energy)
            if lower > 1.0e-3:
                for downstream_energy, downstream_yield in walk(lower, depth + 1, stack + (level,)).items():
                    yields[downstream_energy] += channel_probability * downstream_yield
        return dict(yields)

    return tuple(sorted(walk(excitation_keV).items()))


def daughter_for_mode(z: int, a: int, mode: str) -> tuple[int, int] | None:
    if mode == "BetaMinus":
        return z + 1, a
    if mode in {"BetaPlus", "KshellEC", "LshellEC", "MshellEC"}:
        return z - 1, a
    if mode == "Alpha":
        return z - 2, a - 4
    return None


@lru_cache(maxsize=None)
def w1_decay_line_yields_for_za(za: int) -> tuple[tuple[str, float, float], ...]:
    z, a = split_za(za)
    path = G4_RADIOACTIVE / f"z{z}.a{a}"
    if not path.exists():
        return ()

    line_yields: dict[tuple[str, float], float] = defaultdict(float)
    current_parent_exc = 0.0
    in_ground_parent_block = False
    mode_fractions: dict[str, float] = {}

    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            stripped = raw.strip()
            if not stripped:
                continue
            if stripped.startswith("P"):
                parts = stripped.split()
                try:
                    current_parent_exc = float(parts[1])
                except (IndexError, ValueError):
                    current_parent_exc = 0.0
                in_ground_parent_block = abs(current_parent_exc) <= 1.0e-6
                continue

            parts = stripped.split()
            if len(parts) < 3:
                continue
            mode = parts[0]
            if mode not in {"BetaMinus", "BetaPlus", "KshellEC", "LshellEC", "MshellEC", "Alpha", "IT"}:
                continue
            try:
                daughter_exc = float(parts[1])
                intensity = float(parts[2])
            except ValueError:
                continue
            if intensity <= BRANCH_INTENSITY_MIN:
                continue
            if len(parts) == 3:
                mode_fractions[mode] = intensity
                continue

            if mode == "IT":
                if in_ground_parent_block:
                    continue
                branch_fraction = intensity / 100.0
                for energy, gamma_yield in collect_w1_gamma_yields(z, a, current_parent_exc):
                    line_yields[("gamma", energy)] += branch_fraction * gamma_yield
                continue

            if not in_ground_parent_block:
                continue
            # In this Geant4 dataset the concrete daughter-level rows are
            # stored as percent per parent decay, e.g. Cu-64 beta+ has header
            # 0.17665 and row intensity 17.665. Use the concrete row directly.
            branch_fraction = intensity / 100.0
            if branch_fraction <= BRANCH_INTENSITY_MIN:
                continue
            if mode == "BetaPlus":
                line_yields[("annihilation", 511.0)] += branch_fraction * 2.0

            daughter = daughter_for_mode(z, a, mode)
            if daughter is None:
                continue
            dz, da = daughter
            if dz <= 0 or da <= 0:
                continue
            for energy, gamma_yield in collect_w1_gamma_yields(dz, da, daughter_exc):
                line_yields[("gamma", energy)] += branch_fraction * gamma_yield

    return tuple(
        (kind, energy, yield_per_decay)
        for (kind, energy), yield_per_decay in sorted(line_yields.items(), key=lambda item: (item[0][1], item[0][0]))
        if yield_per_decay > BRANCH_INTENSITY_MIN
    )


def format_decay_lines(lines: list[dict]) -> str:
    if not lines:
        return ""
    ordered = sorted(lines, key=lambda item: float(item.get("line_rate_per_s", 0.0)), reverse=True)
    labels = []
    for item in ordered[:MAX_LABEL_LINES]:
        kind = "annih" if item["kind"] == "annihilation" else "g"
        labels.append(f"{float(item['energy_keV']):.3f} {kind}")
    if len(ordered) > MAX_LABEL_LINES:
        labels.append(f"+{len(ordered) - MAX_LABEL_LINES}")
    return ", ".join(labels)


def summarize_w1_decay_line_activity() -> list[dict]:
    activity_by_za: dict[int, float] = defaultdict(float)
    label_by_za: dict[int, str] = {}
    with INVENTORY.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                activity = float(row["Activity_Bq"])
                za = int(row["ZA"])
            except (KeyError, ValueError):
                continue
            if activity <= 0.0:
                continue
            activity_by_za[za] += activity
            label_by_za[za] = row.get("nuclide") or nuclide_label_from_za(za)

    rows: list[dict] = []
    for za, activity in activity_by_za.items():
        line_tuples = w1_decay_line_yields_for_za(za)
        if not line_tuples:
            continue
        line_rows = [
            {
                "kind": kind,
                "energy_keV": energy,
                "yield_per_decay": yield_per_decay,
                "line_rate_per_s": activity * yield_per_decay,
            }
            for kind, energy, yield_per_decay in line_tuples
        ]
        total_yield = sum(float(item["yield_per_decay"]) for item in line_rows)
        total_line_rate = activity * total_yield
        rows.append(
            {
                "ZA": za,
                "nuclide": label_by_za.get(za, nuclide_label_from_za(za)),
                "Activity_Bq": activity,
                "W1_photons_per_decay": total_yield,
                "W1_line_rate_per_s": total_line_rate,
                "W1_decay_lines": line_rows,
                "W1_decay_line_label": format_decay_lines(line_rows),
            }
        )
    rows.sort(key=lambda row: float(row["W1_line_rate_per_s"]), reverse=True)
    return rows


def open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return path.open("r", encoding="utf-8", errors="ignore")


def reservoir_add(reservoir: list[dict], item: dict, seen: int, rng: random.Random) -> None:
    if len(reservoir) < SAMPLE_SIZE:
        reservoir.append(item)
        return
    idx = rng.randrange(seen)
    if idx < SAMPLE_SIZE:
        reservoir[idx] = item


def parse_rpip_sample() -> tuple[list[dict], dict]:
    delayed_keys, nuclides = read_inventory()
    rng = random.Random(SEED)
    sample: list[dict] = []
    volume_counts: Counter[str] = Counter()
    nuclide_counts: Counter[str] = Counter()
    za_counts: Counter[str] = Counter()
    proc_counts: Counter[str] = Counter()
    total_cc_ip = 0
    delayed_matched = 0
    files = sorted(BUILDUP.glob("*.sim.gz"))

    for index, sim in enumerate(files, start=1):
        file_matches = 0
        with open_text(sim) as handle:
            for raw in handle:
                if not raw.startswith("CC IP"):
                    continue
                total_cc_ip += 1
                m = IP_RE.match(raw.strip())
                if not m:
                    continue
                vn = canon_vn(m.group("vn"))
                za = int(m.group("za"))
                key = (vn, za)
                if key not in delayed_keys:
                    continue
                delayed_matched += 1
                file_matches += 1
                nuclide = nuclides.get(key, str(za))
                volume_counts[vn] += 1
                nuclide_counts[nuclide] += 1
                za_counts[str(za)] += 1
                proc_counts[m.group("proc")] += 1
                item = {
                    "x_cm": float(m.group("x")),
                    "y_cm": float(m.group("y")),
                    "z_cm": float(m.group("z")),
                    "VN": vn,
                    "ZA": za,
                    "nuclide": nuclide,
                    "process": m.group("proc"),
                    "source_file": sim.name,
                }
                reservoir_add(sample, item, delayed_matched, rng)
        print(f"[{index:02d}/{len(files):02d}] {sim.name}: matched {file_matches}")

    summary = {
        "sim_files": len(files),
        "total_cc_ip_lines_seen": total_cc_ip,
        "delayed_relevant_rpip_points": delayed_matched,
        "sample_size": len(sample),
        "sample_seed": SEED,
        "selection": "CC IP RP positions with (canonical VN, ZA) present in positive-activity day15 inventory",
        "top_volumes": volume_counts.most_common(20),
        "top_nuclides": nuclide_counts.most_common(20),
        "top_processes": proc_counts.most_common(20),
        "source_representation_note": (
            "This map uses true RPIP production coordinates. The production delayed Cosima source "
            "compresses these points into z-bin + radial-profile RadialProfileBeam blocks."
        ),
    }
    return sample, summary


def write_sample_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["x_cm", "y_cm", "z_cm", "VN", "ZA", "nuclide", "process", "source_file"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def read_sample_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_w1_activity_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "rank",
                "ZA",
                "nuclide",
                "Activity_Bq",
                "W1_photons_per_decay",
                "W1_line_rate_per_s",
                "W1_decay_lines_keV",
            ],
        )
        writer.writeheader()
        for rank, row in enumerate(rows, start=1):
            writer.writerow(
                {
                    "rank": rank,
                    "ZA": row["ZA"],
                    "nuclide": row["nuclide"],
                    "Activity_Bq": f"{float(row['Activity_Bq']):.12e}",
                    "W1_photons_per_decay": f"{float(row['W1_photons_per_decay']):.12e}",
                    "W1_line_rate_per_s": f"{float(row['W1_line_rate_per_s']):.12e}",
                    "W1_decay_lines_keV": row["W1_decay_line_label"],
                }
            )


def draw_geometry_xz(ax, bounds: dict) -> None:
    from matplotlib.patches import Rectangle

    def rect_rz(r: float, z0: float, z1: float, color: str, alpha: float, label: str | None = None) -> None:
        ax.add_patch(Rectangle((-r, z0), 2.0 * r, z1 - z0, facecolor=color, edgecolor=color, alpha=alpha, lw=0.8, label=label))

    for item in bounds.get("CRYOSTAT_SHELLS", []):
        rect_rz(float(item["r_out"]), float(item["z_out_bot"]), float(item["z_out_top"]), "#9fb7d6", 0.12)
    for item in bounds.get("OPEN_BOTTOM_CANS", []):
        rect_rz(float(item["r_out"]), float(item["z_in_bot"]), float(item["z_out_top"]), "#5ac8d8", 0.16)
    if bounds.get("SAMPLE_BOX"):
        sb = bounds["SAMPLE_BOX"]
        rect_rz(float(sb["r_out"]), float(sb["z_out_bot"]), float(sb["z_out_top"]), "#c07a3a", 0.22, "sample box")
    if bounds.get("ACTIVE_SHIELD"):
        active = bounds["ACTIVE_SHIELD"]
        rect_rz(float(active["r_out"]), float(active["z_out_bot"]), float(active["z_out_top"]), "#84c184", 0.13, "active shield")
    if bounds.get("OUTER_MECHANICAL_SHELL"):
        outer = bounds["OUTER_MECHANICAL_SHELL"]
        rect_rz(float(outer["r_out"]), float(outer["z_out_bot"]), float(outer["z_out_top"]), "#a7a9ac", 0.10, "outer shell")
    for idx, layer in enumerate(bounds.get("TES_LAYERS", [])):
        ax.add_patch(
            Rectangle(
                (-float(layer["r_max"]), float(layer["z_center"]) - float(layer["hz"])),
                2.0 * float(layer["r_max"]),
                2.0 * float(layer["hz"]),
                facecolor="#d73027",
                edgecolor="#8c1d18",
                alpha=0.65,
                lw=0.5,
                label="TES" if idx == 0 else None,
            )
        )


def make_plot(path: Path, rows: list[dict], summary: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec
    from matplotlib.patches import Circle

    bounds = json.loads(BOUNDS.read_text(encoding="utf-8"))
    fig = plt.figure(figsize=(16.8, 9.6), constrained_layout=True)
    gs = GridSpec(2, 3, figure=fig, width_ratios=[1.55, 1.0, 1.05])
    ax_xz = fig.add_subplot(gs[:, 0])
    ax_xy = fig.add_subplot(gs[0, 1])
    ax_vol = fig.add_subplot(gs[0, 2])
    ax_nuc = fig.add_subplot(gs[1, 1:])

    volume_palette = {
        "CsI_Active_Shield_Bottom00": "#6f3fb2",
        "CsI_Active_Shield_Bottom01": "#6f3fb2",
        "CsI_Active_Shield_Bottom02": "#6f3fb2",
        "CsI_Active_Shield_Bottom03": "#6f3fb2",
        "CsI_Active_Shield_Side00": "#8750c7",
        "CsI_Active_Shield_Side01": "#8750c7",
        "CsI_Active_Shield_Side02": "#8750c7",
        "CsI_Active_Shield_Side03": "#8750c7",
        "CsI_Active_Shield_Side04": "#8750c7",
        "CsI_Active_Shield_Side05": "#8750c7",
        "CsI_Active_Shield_Side06": "#8750c7",
        "CsI_Active_Shield_Side07": "#8750c7",
        "CsI_Active_Shield_Top00": "#9d65d4",
        "CsI_Active_Shield_Top01": "#9d65d4",
        "CsI_Active_Shield_Top02": "#9d65d4",
        "CsI_Active_Shield_Top03": "#9d65d4",
        "CsI_Active_Shield_Top04": "#9d65d4",
        "CsI_Active_Shield_Top05": "#9d65d4",
        "CsI_Active_Shield_Top06": "#9d65d4",
        "CsI_Active_Shield_Top07": "#9d65d4",
        "Outer_Al_Mech_Shell": "#7f8c8d",
        "Passive_Cu_Inner_Liner": "#b97832",
        "Passive_W_Outer_Liner": "#5b5550",
        "Passive_Bottom_W_Shield": "#5b5550",
        "Passive_Top_W_Aperture_Annulus": "#5b5550",
    }
    colors = [volume_palette.get(row["VN"], "#2f78b7") for row in rows]
    xs = [float(row["x_cm"]) for row in rows]
    ys = [float(row["y_cm"]) for row in rows]
    zs = [float(row["z_cm"]) for row in rows]

    draw_geometry_xz(ax_xz, bounds)
    ax_xz.scatter(xs, zs, s=3.5, c=colors, alpha=0.38, linewidths=0)
    ax_xz.set_xlim(-16, 16)
    ax_xz.set_ylim(-23, 17)
    ax_xz.set_aspect("equal", adjustable="box")
    ax_xz.grid(alpha=0.18)
    ax_xz.set_xlabel("x / cm")
    ax_xz.set_ylabel("z / cm")
    ax_xz.set_title(f"True delayed-relevant RPIP production positions (sample n={len(rows)})")

    for r, color in [
        (bounds.get("SAMPLE_BOX", {}).get("r_out"), "#c07a3a"),
        (bounds.get("ACTIVE_SHIELD", {}).get("r_out"), "#84c184"),
        (bounds.get("OUTER_MECHANICAL_SHELL", {}).get("r_out"), "#a7a9ac"),
    ]:
        if r:
            ax_xy.add_patch(Circle((0, 0), float(r), fill=False, edgecolor=color, lw=1.0, alpha=0.85))
    ax_xy.scatter(xs, ys, s=3.0, c=colors, alpha=0.32, linewidths=0)
    ax_xy.set_xlim(-16, 16)
    ax_xy.set_ylim(-16, 16)
    ax_xy.set_aspect("equal", adjustable="box")
    ax_xy.grid(alpha=0.18)
    ax_xy.set_xlabel("x / cm")
    ax_xy.set_ylabel("y / cm")
    ax_xy.set_title("True x-y production footprint")

    top_vol = summary["top_volumes"][:12]
    ax_vol.barh([v for v, _ in reversed(top_vol)], [c for _, c in reversed(top_vol)], color="0.35")
    ax_vol.set_title("Top RPIP production volumes")
    ax_vol.set_xlabel("true RPIP point count")

    w1_rows = summary.get("w1_decay_line_activity", [])[:14]
    if w1_rows:
        labels = [
            f"{row['nuclide']} ({row['W1_decay_line_label']} keV)"
            for row in reversed(w1_rows)
        ]
        values = [float(row["W1_line_rate_per_s"]) for row in reversed(w1_rows)]
        ax_nuc.barh(labels, values, color="#4b6f9f")
        ax_nuc.set_title(f"W1 {W1_LO_KEV:.3f}-{W1_HI_KEV:.3f} keV decay-line yield from day-15 inventory")
        ax_nuc.set_xlabel("estimated emitted W1 photons / s")
    else:
        ax_nuc.text(0.5, 0.5, "No W1 decay lines found in local G4 data", ha="center", va="center", transform=ax_nuc.transAxes)
        ax_nuc.set_axis_off()

    fig.suptitle("Step03 true RPIP production map, before z/r radial-profile source compression")
    fig.savefig(path, dpi=190)
    plt.close(fig)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    sample_path = OUT / "rpip_production_points_sample.csv"
    summary_path = OUT / "rpip_production_map_summary.json"
    if sample_path.exists() and summary_path.exists():
        sample = read_sample_csv(sample_path)
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        print(f"[INFO] reusing {sample_path}")
        print(f"[INFO] reusing {summary_path}")
    else:
        sample, summary = parse_rpip_sample()
    w1_activity_rows = summarize_w1_decay_line_activity()
    summary["w1_decay_line_activity"] = w1_activity_rows
    summary["w1_decay_line_activity_note"] = (
        "Nuclides are selected by local Geant4 RadioactiveDecay/PhotonEvaporation decay products inside "
        f"W1 {W1_LO_KEV:.6f}-{W1_HI_KEV:.6f} keV. Bars use total day-15 inventory activity multiplied by "
        "local Geant4 decay branch and de-excitation yields. They are emitted-source photon rates, not detector rates."
    )
    write_sample_csv(sample_path, sample)
    write_w1_activity_csv(OUT / "w1_decay_line_activity_by_nuclide.csv", w1_activity_rows)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    make_plot(OUT / "rpip_production_map.png", sample, summary)
    print(f"[OK] wrote {OUT / 'rpip_production_points_sample.csv'}")
    print(f"[OK] wrote {OUT / 'w1_decay_line_activity_by_nuclide.csv'}")
    print(f"[OK] wrote {OUT / 'rpip_production_map_summary.json'}")
    print(f"[OK] wrote {OUT / 'rpip_production_map.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
