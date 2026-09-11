#!/usr/bin/env python3
"""Build auditable Mass_model_511 vs S3 neutron/BPE evidence for the slide deck.

The script deliberately separates three questions:

1. How many primary-neutron histories still make an interaction inside the
   inner BPE envelope?  This is an IA-history proxy, not a boundary-fluence
   scorer.
2. What is the neutron energy immediately before the first such interior
   interaction?  Initial energy comes from ``IA INIT`` and energy loss is
   followed through the primary-neutron IA chain; the SIM ``EC`` field is not
   used as an initial-energy surrogate.
3. What O/Cu activation is produced by the neutron-only buildup files, and
   where do the relevant evaluated cross sections sit in energy?

All generated products live in the new dated presentation package and do not
modify retained simulation outputs.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import multiprocessing as mp
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-mass511-s3-deck")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "engineering/geometry_optimization_20260704/39_mass511_to_s3_html_presentation_20260710"
ASSETS = WORK / "assets"
DATA = WORK / "data"

S3_BUILDUP = ROOT / "runs/geometry_optimization_20260704/step02_buildup_s3_csi_barrel_fullstat_v1_20260709"
MASS_BUILDUP = ROOT / "runs/Mass_model_511_nearfield_migration_20260701/step02_buildup_candidate_Mass_model_511_fullstat_v1"

S3_GS = ROOT / "runs/geometry_optimization_20260704/step02_delay_fix_s3_csi_barrel_fullstat_v1_20260709/groundstate_activity_corrections.csv"
MASS_GS = ROOT / "runs/Mass_model_511_nearfield_migration_20260701/step02_delay_fix_candidate_Mass_model_511_fullstat_v1/groundstate_activity_corrections.csv"
HALF_LIFE_CACHE = ROOT / "runs/geometry_optimization_20260704/step02_decay_source_s3_csi_barrel_fullstat_v1_20260709/half_life_cache.json"

# S3 local-frame BPE geometry.  The side shell is r=27..29 cm and
# z=-24.5..46.0 cm after applying its local z offset.  The caps extend the
# outer envelope to z=-26.5 and +48.0 cm.
INNER_RADIUS_CM = 27.0
SIDE_ZMIN_CM = -24.5
SIDE_ZMAX_CM = 46.0
BPE_OUTER_RADIUS_CM = 29.0
BPE_BOTTOM_ZMIN_CM = -26.5
BPE_TOP_ZMAX_CM = 48.0

N_REPLICAS = 8
EXPOSURE_DAYS = 15.0

ENERGY_EDGES_KEV = np.logspace(-7, 8, 76)
RATIO_EDGES = np.linspace(0.0, 1.0, 51)

SELECTED_NUCLIDES = {
    8015: "O-15",
    29061: "Cu-61",
    29062: "Cu-62",
    29064: "Cu-64",
    29066: "Cu-66",
}

CROSS_SECTION_FILES = {
    "B10_nalpha": DATA / "b10_nalpha_endfb_viii1_293k.json",
    "Cu63_ng_Cu64": DATA / "cu63_ng_cu64_endfb_viii1_293k.json",
    "Cu65_n2n_Cu64": DATA / "cu65_n2n_cu64_endfb_viii1_293k.json",
    "Cu63_n2n_Cu62": DATA / "cu63_n2n_cu62_endfb_viii1_293k.json",
    "O16_n2n_O15": DATA / "o16_n2n_o15_endfb_viii1_293k.json",
}

REACTION_META = {
    "B10_nalpha": {
        "label": "B-10(n,α)Li-7",
        "target": "B-10",
        "product": "Li-7",
        "reaction_id": 73363,
        "cross_section_id": 126484,
        "color": "#D97706",
    },
    "Cu63_ng_Cu64": {
        "label": "Cu-63(n,γ)Cu-64",
        "target": "Cu-63",
        "product": "Cu-64",
        "reaction_id": 101398,
        "cross_section_id": 170175,
        "color": "#1D4ED8",
    },
    "Cu65_n2n_Cu64": {
        "label": "Cu-65(n,2n)Cu-64",
        "target": "Cu-65",
        "product": "Cu-64",
        "reaction_id": 79347,
        "cross_section_id": 132353,
        "color": "#2563EB",
    },
    "Cu63_n2n_Cu62": {
        "label": "Cu-63(n,2n)Cu-62",
        "target": "Cu-63",
        "product": "Cu-62",
        "reaction_id": 101351,
        "cross_section_id": 170081,
        "color": "#7C3AED",
    },
    "O16_n2n_O15": {
        "label": "O-16(n,2n)O-15",
        "target": "O-16",
        "product": "O-15",
        "reaction_id": 71060,
        "cross_section_id": 124608,
        "color": "#0F766E",
    },
}

MASS_COLOR = "#64748B"
S3_COLOR = "#1D4ED8"
INK = "#172033"
MUTED = "#5F6B7A"
GRID = "#DCE3EA"
AMBER = "#D97706"

IA_PREFIX_RE = re.compile(r"^IA\s+([A-Z0-9]{4})\s+(.*)$")
ID_RE = re.compile(r"^ID\s+(\d+)")
TT_RE = re.compile(r"^\s*TT\s+([-+0-9.eE]+)\s*$")
VN_RE = re.compile(r"^\s*VN\s+(\S+)\s*$")
RP_RE = re.compile(r"^\s*RP\s+(\d+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*$")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def setup_plot_style() -> None:
    regular = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    bold = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"
    if Path(regular).exists():
        font_manager.fontManager.addfont(regular)
        family = font_manager.FontProperties(fname=regular).get_name()
    else:
        family = "DejaVu Sans"
    if Path(bold).exists():
        font_manager.fontManager.addfont(bold)
    plt.rcParams.update(
        {
            "font.family": family,
            "font.size": 12,
            "axes.titlesize": 17,
            "axes.titleweight": "bold",
            "axes.labelsize": 12,
            "axes.labelcolor": INK,
            "axes.edgecolor": GRID,
            "axes.linewidth": 0.8,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "text.color": INK,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def parse_ia(line: str) -> dict[str, Any] | None:
    match = IA_PREFIX_RE.match(line)
    if not match:
        return None
    process = match.group(1)
    parts = [part.strip() for part in match.group(2).split(";")]
    if len(parts) < 23:
        return None
    try:
        return {
            "process": process,
            "id": int(parts[0]),
            "origin": int(parts[1]),
            "detector_type": int(parts[2]),
            "time_s": float(parts[3]),
            "x_cm": float(parts[4]),
            "y_cm": float(parts[5]),
            "z_cm": float(parts[6]),
            "mother_id": int(parts[7]),
            "mother_energy_keV": float(parts[14]),
            "secondary_id": int(parts[15]),
            "secondary_energy_keV": float(parts[22]),
        }
    except (TypeError, ValueError):
        return None


def world_to_local(x: float, y: float, z: float) -> tuple[float, float, float]:
    angle = math.radians(-45.0)
    c, s = math.cos(angle), math.sin(angle)
    return c * x + s * z, y, -s * x + c * z


def inside_inner_envelope(x: float, y: float, z: float) -> bool:
    xl, yl, zl = world_to_local(x, y, z)
    return math.hypot(xl, yl) < INNER_RADIUS_CM and SIDE_ZMIN_CM < zl < SIDE_ZMAX_CM


def in_bpe_geometry(x: float, y: float, z: float) -> bool:
    xl, yl, zl = world_to_local(x, y, z)
    radius = math.hypot(xl, yl)
    in_side = INNER_RADIUS_CM <= radius <= BPE_OUTER_RADIUS_CM and SIDE_ZMIN_CM <= zl <= SIDE_ZMAX_CM
    in_bottom = radius <= BPE_OUTER_RADIUS_CM and BPE_BOTTOM_ZMIN_CM <= zl <= SIDE_ZMIN_CM
    in_top = radius <= BPE_OUTER_RADIUS_CM and SIDE_ZMAX_CM <= zl <= BPE_TOP_ZMAX_CM
    return in_side or in_bottom or in_top


def energy_bin_index(energy_keV: float) -> int | None:
    if not math.isfinite(energy_keV) or energy_keV <= 0:
        return None
    idx = int(np.searchsorted(ENERGY_EDGES_KEV, energy_keV, side="right") - 1)
    return idx if 0 <= idx < len(ENERGY_EDGES_KEV) - 1 else None


def parse_neutron_sim(task: tuple[str, str]) -> dict[str, Any]:
    label, path_s = task
    path = Path(path_s)
    counters = Counter()
    init_hist = np.zeros(len(ENERGY_EDGES_KEV) - 1, dtype=np.int64)
    survivor_init_hist = np.zeros_like(init_hist)
    entry_hist = np.zeros_like(init_hist)
    ratio_hist = np.zeros(len(RATIO_EDGES) - 1, dtype=np.int64)
    entry_thresholds = Counter()

    current_id: int | None = None
    initial_energy: float | None = None
    primary_energy: float | None = None
    first_inside_energy: float | None = None
    bpe_geometric_interactions = 0
    bpe_capture = False
    pm_bpe_keV = 0.0

    def finalize_event() -> None:
        nonlocal current_id, initial_energy, primary_energy, first_inside_energy
        nonlocal bpe_geometric_interactions, bpe_capture, pm_bpe_keV
        if current_id is None:
            return
        counters["generated_histories"] += 1
        if initial_energy is not None and initial_energy > 0:
            idx = energy_bin_index(initial_energy)
            if idx is not None:
                init_hist[idx] += 1
        else:
            counters["missing_initial_energy"] += 1

        if first_inside_energy is not None and first_inside_energy > 0:
            counters["interior_interaction_histories"] += 1
            idx = energy_bin_index(first_inside_energy)
            if idx is not None:
                entry_hist[idx] += 1
            if initial_energy is not None and initial_energy > 0:
                idx0 = energy_bin_index(initial_energy)
                if idx0 is not None:
                    survivor_init_hist[idx0] += 1
                ratio = min(1.0, max(0.0, first_inside_energy / initial_energy))
                ridx = int(np.searchsorted(RATIO_EDGES, ratio, side="right") - 1)
                ridx = min(max(ridx, 0), len(RATIO_EDGES) - 2)
                ratio_hist[ridx] += 1
                if ratio < 0.999:
                    counters["interior_histories_moderated_before_entry"] += 1
            if first_inside_energy < 100.0:
                entry_thresholds["lt_100keV"] += 1
            if first_inside_energy < 1_000.0:
                entry_thresholds["lt_1MeV"] += 1
            if first_inside_energy >= 10_063.4:
                entry_thresholds["ge_10p063MeV"] += 1
            if first_inside_energy >= 11_037.9:
                entry_thresholds["ge_11p038MeV"] += 1
            if first_inside_energy >= 16_651.6:
                entry_thresholds["ge_16p652MeV"] += 1

        if bpe_geometric_interactions > 0:
            counters["histories_with_geometric_bpe_interaction"] += 1
            counters["geometric_bpe_interactions"] += bpe_geometric_interactions
            if first_inside_energy is not None:
                counters["geometric_bpe_then_interior_histories"] += 1
        if bpe_capture:
            counters["histories_captured_in_geometric_bpe"] += 1
        if pm_bpe_keV > 0:
            counters["histories_with_bpe_passive_deposit"] += 1
            counters["bpe_passive_deposit_keV_milli"] += int(round(pm_bpe_keV * 1000.0))
            if first_inside_energy is not None:
                counters["bpe_passive_deposit_then_interior_histories"] += 1

        current_id = None
        initial_energy = None
        primary_energy = None
        first_inside_energy = None
        bpe_geometric_interactions = 0
        bpe_capture = False
        pm_bpe_keV = 0.0

    with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if line == "SE":
                finalize_event()
                continue
            id_match = ID_RE.match(line)
            if id_match:
                current_id = int(id_match.group(1))
                continue
            if line.startswith("PM BoratedPolyethylene5wtB"):
                try:
                    pm_bpe_keV += float(line.split()[-1])
                except (ValueError, IndexError):
                    counters["unparsed_bpe_pm_lines"] += 1
                continue
            if not line.startswith("IA "):
                continue
            ia = parse_ia(line)
            if ia is None:
                counters["unparsed_ia_lines"] += 1
                continue
            if ia["process"] == "INIT":
                if ia["secondary_id"] == 6:
                    initial_energy = float(ia["secondary_energy_keV"])
                    primary_energy = initial_energy
                continue

            # Origin 1 is the neutron created by the INIT record.  Restricting
            # to this chain keeps the Mass/S3 comparison paired and avoids
            # counting an event multiple times when an inelastic reaction
            # creates secondary neutrons.
            if ia["origin"] != 1 or ia["mother_id"] != 6:
                continue
            before = primary_energy if primary_energy is not None else initial_energy
            if in_bpe_geometry(ia["x_cm"], ia["y_cm"], ia["z_cm"]):
                bpe_geometric_interactions += 1
                if ia["process"] == "CAPT":
                    bpe_capture = True
            if first_inside_energy is None and inside_inner_envelope(ia["x_cm"], ia["y_cm"], ia["z_cm"]):
                if before is not None and before > 0:
                    first_inside_energy = float(before)
            primary_energy = max(0.0, float(ia["mother_energy_keV"]))

    finalize_event()
    return {
        "label": label,
        "file": rel(path),
        "counters": dict(counters),
        "init_hist": init_hist,
        "survivor_init_hist": survivor_init_hist,
        "entry_hist": entry_hist,
        "ratio_hist": ratio_hist,
        "entry_thresholds": dict(entry_thresholds),
    }


def read_tt_values(directory: Path) -> list[float]:
    files = sorted(directory.glob("Background_n_fullsphere20_rep*.dat.inc1.dat"))
    if len(files) != N_REPLICAS:
        raise RuntimeError(f"expected {N_REPLICAS} neutron DAT replicas in {directory}, got {len(files)}")
    values: list[float] = []
    for path in files:
        found: list[float] = []
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                match = TT_RE.match(line)
                if match:
                    found.append(float(match.group(1)))
        if len(found) != 1 or found[0] <= 0:
            raise RuntimeError(f"TT division guard failed for {path}: {found}")
        values.append(found[0])
    return values


def hist_quantile(hist: np.ndarray, edges: np.ndarray, q: float) -> float | None:
    total = float(np.sum(hist))
    if total <= 0:
        return None
    target = q * total
    cumulative = np.cumsum(hist)
    idx = int(np.searchsorted(cumulative, target, side="left"))
    idx = min(max(idx, 0), len(hist) - 1)
    before = float(cumulative[idx - 1]) if idx > 0 else 0.0
    width_count = float(hist[idx])
    fraction = 0.5 if width_count <= 0 else min(1.0, max(0.0, (target - before) / width_count))
    lo, hi = float(edges[idx]), float(edges[idx + 1])
    if lo > 0 and hi > 0:
        return float(10 ** (math.log10(lo) + fraction * (math.log10(hi) - math.log10(lo))))
    return lo + fraction * (hi - lo)


def combine_sim_results(label: str, results: list[dict[str, Any]], tt_values: list[float]) -> dict[str, Any]:
    counters = Counter()
    thresholds = Counter()
    init_hist = np.zeros(len(ENERGY_EDGES_KEV) - 1, dtype=np.int64)
    survivor_init_hist = np.zeros_like(init_hist)
    entry_hist = np.zeros_like(init_hist)
    ratio_hist = np.zeros(len(RATIO_EDGES) - 1, dtype=np.int64)
    for row in results:
        counters.update(row["counters"])
        thresholds.update(row["entry_thresholds"])
        init_hist += row["init_hist"]
        survivor_init_hist += row["survivor_init_hist"]
        entry_hist += row["entry_hist"]
        ratio_hist += row["ratio_hist"]

    generated = int(counters["generated_histories"])
    interior = int(counters["interior_interaction_histories"])
    mean_tt = float(np.mean(tt_values))
    equivalent_count = interior / N_REPLICAS
    rate = equivalent_count / mean_tt
    threshold_summary: dict[str, Any] = {}
    for key in ("lt_100keV", "lt_1MeV", "ge_10p063MeV", "ge_11p038MeV", "ge_16p652MeV"):
        count = int(thresholds[key])
        threshold_summary[key] = {
            "raw_histories": count,
            "fraction_of_interior_histories": 0.0 if interior == 0 else count / interior,
        }
    return {
        "label": label,
        "files": [row["file"] for row in sorted(results, key=lambda value: value["file"])],
        "replicas": N_REPLICAS,
        "tt_seconds": tt_values,
        "mean_tt_seconds": mean_tt,
        "generated_histories_raw": generated,
        "generated_histories_per_replica": generated / N_REPLICAS,
        "interior_interaction_histories_raw": interior,
        "interior_interaction_histories_per_replica": equivalent_count,
        "interior_interaction_history_rate_per_s": rate,
        "fraction_of_generated_with_interior_interaction": 0.0 if generated == 0 else interior / generated,
        "entry_energy_median_keV_hist_approx": hist_quantile(entry_hist, ENERGY_EDGES_KEV, 0.5),
        "entry_energy_p10_keV_hist_approx": hist_quantile(entry_hist, ENERGY_EDGES_KEV, 0.1),
        "entry_energy_p90_keV_hist_approx": hist_quantile(entry_hist, ENERGY_EDGES_KEV, 0.9),
        "initial_energy_median_keV_hist_approx": hist_quantile(init_hist, ENERGY_EDGES_KEV, 0.5),
        "entry_over_initial_median_hist_approx": hist_quantile(ratio_hist, RATIO_EDGES, 0.5),
        "thresholds": threshold_summary,
        "counters": dict(sorted(counters.items())),
        "histograms": {
            "energy_edges_keV": ENERGY_EDGES_KEV.tolist(),
            "initial_all": init_hist.tolist(),
            "initial_of_interior_histories": survivor_init_hist.tolist(),
            "energy_before_first_interior_interaction": entry_hist.tolist(),
            "entry_over_initial_edges": RATIO_EDGES.tolist(),
            "entry_over_initial": ratio_hist.tolist(),
        },
    }


def build_transport_evidence(workers: int) -> dict[str, Any]:
    datasets = {
        "Mass_model_511": MASS_BUILDUP,
        "S3": S3_BUILDUP,
    }
    tasks: list[tuple[str, str]] = []
    tt_by_label: dict[str, list[float]] = {}
    for label, directory in datasets.items():
        files = sorted(directory.glob("Background_n_fullsphere20_rep*.sim.gz"))
        if len(files) != N_REPLICAS:
            raise RuntimeError(f"expected {N_REPLICAS} neutron SIM replicas in {directory}, got {len(files)}")
        tasks.extend((label, str(path)) for path in files)
        tt_by_label[label] = read_tt_values(directory)

    if workers > 1:
        ctx = mp.get_context("fork")
        with ctx.Pool(processes=min(workers, len(tasks))) as pool:
            parsed = list(pool.imap_unordered(parse_neutron_sim, tasks, chunksize=1))
    else:
        parsed = [parse_neutron_sim(task) for task in tasks]

    by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in parsed:
        by_label[row["label"]].append(row)
    combined = {label: combine_sim_results(label, by_label[label], tt_by_label[label]) for label in datasets}
    mass_rate = combined["Mass_model_511"]["interior_interaction_history_rate_per_s"]
    s3_rate = combined["S3"]["interior_interaction_history_rate_per_s"]
    combined["comparison"] = {
        "s3_over_mass_interior_interaction_rate": None if mass_rate <= 0 else s3_rate / mass_rate,
        "s3_relative_change_percent": None if mass_rate <= 0 else 100.0 * (s3_rate / mass_rate - 1.0),
        "definition": (
            "Primary-neutron histories with at least one IA interaction inside local r<27 cm and "
            "-24.5<z<46 cm, divided by 8 replicas and mean per-replica TT. This is not a boundary-fluence scorer."
        ),
    }
    return combined


def parse_neutron_only_activation(directory: Path, half_lives: dict[str, float]) -> dict[str, Any]:
    files = sorted(directory.glob("Background_n_fullsphere20_rep*.dat.inc1.dat"))
    if len(files) != N_REPLICAS:
        raise RuntimeError(f"activation TT division guard: expected {N_REPLICAS} files, got {len(files)}")
    raw_counts: defaultdict[tuple[str, int], float] = defaultdict(float)
    tt_values: list[float] = []
    for path in files:
        current_vn: str | None = None
        tt_in_file: list[float] = []
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                match = TT_RE.match(line)
                if match:
                    tt_in_file.append(float(match.group(1)))
                    continue
                match = VN_RE.match(line)
                if match:
                    current_vn = match.group(1)
                    continue
                match = RP_RE.match(line)
                if match and current_vn is not None:
                    za = int(match.group(1))
                    if za in SELECTED_NUCLIDES:
                        raw_counts[(current_vn, za)] += float(match.group(3))
        if len(tt_in_file) != 1 or tt_in_file[0] <= 0:
            raise RuntimeError(f"activation TT division guard failed for {path}: {tt_in_file}")
        tt_values.append(tt_in_file[0])

    mean_tt = float(np.mean(tt_values))
    by_nuclide: defaultdict[str, dict[str, float]] = defaultdict(lambda: {"yield": 0.0, "activity": 0.0})
    by_volume: list[dict[str, Any]] = []
    for (volume, za), raw in sorted(raw_counts.items()):
        nuclide = SELECTED_NUCLIDES[za]
        production = raw / N_REPLICAS
        half_life = float(half_lives[nuclide])
        decay_constant = math.log(2.0) / half_life
        exposure_s = EXPOSURE_DAYS * 86400.0
        activity = (production / mean_tt) * (1.0 - math.exp(-decay_constant * exposure_s))
        by_nuclide[nuclide]["yield"] += production
        by_nuclide[nuclide]["activity"] += activity
        by_volume.append(
            {
                "volume": volume,
                "ZA": za,
                "nuclide": nuclide,
                "replica_averaged_production": production,
                "activity_Bq_after_15d": activity,
            }
        )
    return {
        "files": [rel(path) for path in files],
        "division": N_REPLICAS,
        "tt_seconds": tt_values,
        "mean_tt_seconds": mean_tt,
        "exposure_days": EXPOSURE_DAYS,
        "by_nuclide": {
            nuclide: {
                "replica_averaged_production": values["yield"],
                "activity_Bq_after_15d": values["activity"],
                "half_life_s": float(half_lives[nuclide]),
            }
            for nuclide, values in sorted(by_nuclide.items())
        },
        "by_volume": by_volume,
    }


def load_full_fixed_activity_by_nuclide(path: Path) -> dict[str, float]:
    totals: defaultdict[str, float] = defaultdict(float)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if str(row.get("action", "")).startswith("removed"):
                continue
            try:
                totals[row["nuclide"]] += float(row["new_groundstate_activity_Bq"])
            except (KeyError, TypeError, ValueError):
                continue
    return dict(totals)


def build_activation_evidence() -> dict[str, Any]:
    half_lives = json.loads(HALF_LIFE_CACHE.read_text(encoding="utf-8"))
    missing = sorted(set(SELECTED_NUCLIDES.values()) - set(half_lives))
    if missing:
        raise RuntimeError(f"half-life cache missing {missing}")
    mass = parse_neutron_only_activation(MASS_BUILDUP, half_lives)
    s3 = parse_neutron_only_activation(S3_BUILDUP, half_lives)
    mass_full = load_full_fixed_activity_by_nuclide(MASS_GS)
    s3_full = load_full_fixed_activity_by_nuclide(S3_GS)

    rows: list[dict[str, Any]] = []
    for nuclide in SELECTED_NUCLIDES.values():
        mass_n = mass["by_nuclide"].get(nuclide, {}).get("activity_Bq_after_15d", 0.0)
        s3_n = s3["by_nuclide"].get(nuclide, {}).get("activity_Bq_after_15d", 0.0)
        rows.append(
            {
                "nuclide": nuclide,
                "mass_neutron_only_Bq": mass_n,
                "s3_neutron_only_Bq": s3_n,
                "s3_over_mass_neutron_only": None if mass_n <= 0 else s3_n / mass_n,
                "relative_change_percent": None if mass_n <= 0 else 100.0 * (s3_n / mass_n - 1.0),
                "mass_all_primaries_fixed_Bq": mass_full.get(nuclide, 0.0),
                "s3_all_primaries_fixed_Bq": s3_full.get(nuclide, 0.0),
                "half_life_s": float(half_lives[nuclide]),
            }
        )

    with (DATA / "mass_s3_neutron_only_o_cu_activation.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return {
        "definition": (
            "Neutron-only RP production from eight matched Background_n buildup DAT replicas, divided by eight, "
            "then converted to activity after 15 days using each file family's mean TT and ground-state half-life."
        ),
        "mass": mass,
        "s3": s3,
        "comparison_rows": rows,
        "full_fixed_activity_inputs": {"mass": rel(MASS_GS), "s3": rel(S3_GS)},
        "half_life_input": rel(HALF_LIFE_CACHE),
    }


def load_cross_section(path: Path) -> tuple[np.ndarray, np.ndarray]:
    data = json.loads(path.read_text(encoding="utf-8"))
    axes = {axis["label"]: axis for axis in data["axes"]}
    energy = np.asarray(axes["energy_in"]["values"], dtype=float)
    sigma = np.asarray(axes["crossSection"]["values"], dtype=float)
    if len(energy) != len(sigma) or len(energy) != int(data["point-count"]):
        raise RuntimeError(f"cross-section axis mismatch in {path}")
    return energy, sigma


def interp_logx(energy_eV: np.ndarray, sigma_b: np.ndarray, target_eV: float) -> float | None:
    mask = (energy_eV > 0) & np.isfinite(energy_eV) & np.isfinite(sigma_b)
    x = energy_eV[mask]
    y = sigma_b[mask]
    if target_eV < x.min() or target_eV > x.max():
        return None
    return float(np.interp(math.log(target_eV), np.log(x), y))


def build_cross_section_evidence() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    summaries: dict[str, Any] = {}
    for key, path in CROSS_SECTION_FILES.items():
        if not path.exists():
            raise FileNotFoundError(path)
        energy, sigma = load_cross_section(path)
        positive = sigma > 0
        threshold = float(energy[np.flatnonzero(positive)[0]]) if np.any(positive) else None
        peak_idx = int(np.argmax(sigma))
        meta = REACTION_META[key]
        summaries[key] = {
            **{k: v for k, v in meta.items() if k != "color"},
            "input": rel(path),
            "temperature_K": 293.15,
            "energy_min_eV": float(energy.min()),
            "energy_max_eV": float(energy.max()),
            "positive_threshold_eV": threshold,
            "peak_cross_section_b": float(sigma[peak_idx]),
            "peak_energy_eV": float(energy[peak_idx]),
            "cross_section_at_0p0253eV_b": interp_logx(energy, sigma, 0.0253),
            "cross_section_at_14MeV_b": interp_logx(energy, sigma, 14.0e6),
            "cross_section_at_20MeV_b": interp_logx(energy, sigma, 20.0e6),
        }
        stride = max(1, len(energy) // 2400)
        keep = np.unique(np.r_[np.arange(0, len(energy), stride), len(energy) - 1])
        for idx in keep:
            rows.append(
                {
                    "reaction_key": key,
                    "reaction_label": meta["label"],
                    "energy_eV": float(energy[idx]),
                    "cross_section_b": float(sigma[idx]),
                    "temperature_K": 293.15,
                    "reaction_id": meta["reaction_id"],
                    "cross_section_id": meta["cross_section_id"],
                }
            )

    with (DATA / "endfb_viii1_o_cu_b10_cross_sections.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return {
        "library": "ENDF/B-VIII.1",
        "source": "NNDC ENDF REST API",
        "source_url": "https://www.nndc.bnl.gov/endf-api/",
        "temperature_K": 293.15,
        "reactions": summaries,
        "csv": rel(DATA / "endfb_viii1_o_cu_b10_cross_sections.csv"),
    }


def write_transport_bins(transport: dict[str, Any]) -> None:
    rows: list[dict[str, Any]] = []
    centers = np.sqrt(ENERGY_EDGES_KEV[:-1] * ENERGY_EDGES_KEV[1:])
    for label in ("Mass_model_511", "S3"):
        hist = np.asarray(transport[label]["histograms"]["energy_before_first_interior_interaction"], dtype=float)
        total = float(hist.sum())
        replicas = float(transport[label]["replicas"])
        mean_tt_s = float(transport[label]["mean_tt_seconds"])
        for lo, hi, center, count in zip(ENERGY_EDGES_KEV[:-1], ENERGY_EDGES_KEV[1:], centers, hist):
            dlog10e = math.log10(hi) - math.log10(lo)
            rate_per_s = 0.0 if replicas <= 0 or mean_tt_s <= 0 else count / replicas / mean_tt_s
            rows.append(
                {
                    "dataset": label,
                    "energy_lo_keV": lo,
                    "energy_hi_keV": hi,
                    "energy_center_keV": center,
                    "raw_histories": int(count),
                    "fraction": 0.0 if total <= 0 else count / total,
                    "interior_interaction_rate_per_s": rate_per_s,
                    "rate_density_per_s_per_log10keV": 0.0 if dlog10e <= 0 else rate_per_s / dlog10e,
                }
            )
    with (DATA / "mass_s3_postshield_interaction_energy_bins.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def plot_survivor_count(transport: dict[str, Any]) -> None:
    labels = ["Mass_511", "S3"]
    keys = ["Mass_model_511", "S3"]
    values = [transport[key]["interior_interaction_history_rate_per_s"] for key in keys]
    colors = [MASS_COLOR, S3_COLOR]
    change = transport["comparison"]["s3_relative_change_percent"]

    fig, ax = plt.subplots(figsize=(9.4, 6.3))
    bars = ax.bar(labels, values, width=0.56, color=colors)
    fig.suptitle("穿过外层后，仍在内部发生相互作用的中子历史", fontsize=20, fontweight="bold", y=0.975)
    fig.text(0.5, 0.918, "相同中子源与统计量；单位为等效历史数/秒（不是边界通量）", ha="center", color=MUTED, fontsize=11)
    ax.set_ylabel("内部相互作用历史 / s")
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ymax = max(values) * 1.34 if max(values) > 0 else 1.0
    ax.set_ylim(0, ymax)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + ymax * 0.025, f"{value:.2f}/s", ha="center", va="bottom", fontsize=15, fontweight="bold")
    if change is not None:
        ax.text(0.5, ymax * 0.88, f"S3 相对变化 {change:+.1f}%", ha="center", va="center", fontsize=16, color=S3_COLOR, fontweight="bold")
    fig.text(0.01, 0.012, "判据：一次源中子在屏蔽内表面以内至少发生一次仿真相互作用；8 个重复样本，按等效观测时间归一化。", color=MUTED, fontsize=9.5)
    fig.tight_layout(rect=(0, 0.05, 1, 0.89))
    fig.savefig(ASSETS / "mass_s3_postshield_neutron_count.png", dpi=190)
    plt.close(fig)


def plot_energy_spectrum(transport: dict[str, Any]) -> None:
    centers = np.sqrt(ENERGY_EDGES_KEV[:-1] * ENERGY_EDGES_KEV[1:])
    fig, ax = plt.subplots(figsize=(10.8, 6.2))
    positive_rates: list[float] = []
    for key, label, color in (("Mass_model_511", "Mass_511", MASS_COLOR), ("S3", "S3", S3_COLOR)):
        hist = np.asarray(transport[key]["histograms"]["energy_before_first_interior_interaction"], dtype=float)
        replicas = float(transport[key]["replicas"])
        mean_tt_s = float(transport[key]["mean_tt_seconds"])
        widths_log10 = np.log10(ENERGY_EDGES_KEV[1:]) - np.log10(ENERGY_EDGES_KEV[:-1])
        density = hist / replicas / mean_tt_s / widths_log10
        mask = density > 0
        positive_rates.extend(float(value) for value in density[mask])
        ax.step(centers[mask], density[mask], where="mid", color=color, linewidth=2.4, label=label)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(1e-4, 1e8)
    if positive_rates:
        ax.set_ylim(min(positive_rates) * 0.55, max(positive_rates) * 3.0)
    ax.grid(which="major", color=GRID, linewidth=0.8)
    ax.grid(which="minor", color=GRID, linewidth=0.35, alpha=0.55)
    ax.set_xlabel("中子能量 (keV)")
    ax.set_ylabel("dR/dlog10E (s^-1，内区通量代理)")
    ax.legend(frameon=False, loc="upper left")
    ax.axvspan(10_000, 1e8, color="#F59E0B", alpha=0.08)
    ax.axvline(10_063.4, color="#D97706", linestyle="--", linewidth=1.2)
    ax.axvline(16_651.6, color="#0F766E", linestyle="--", linewidth=1.2)
    top = ax.get_ylim()[1]
    ax.text(11_000, top / 1.8, "Cu 快中子阈值", color="#B45309", fontsize=9, rotation=90, va="top")
    ax.text(18_500, top / 1.8, "O → O-15 阈值", color="#0F766E", fontsize=9, rotation=90, va="top")

    fig.suptitle("Mass_511 与 S3：内区中子能谱的绝对通量代理", fontsize=19, fontweight="bold", y=0.975)
    fig.text(
        0.5,
        0.918,
        "每个 log10 能量区间的内区首次相互作用率；8 个重复按等效观测时间归一化",
        ha="center",
        color=MUTED,
        fontsize=11,
    )
    fig.text(
        0.01,
        0.012,
        "“通量代理”不是边界面通量：它不带 cm^-2 归一化，也不计入无相互作用直接穿过内区的中子。",
        color=MUTED,
        fontsize=9.5,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 0.89))
    fig.savefig(ASSETS / "mass_s3_postshield_neutron_spectrum.png", dpi=190, bbox_inches="tight")
    plt.close(fig)


def plot_activation(activation: dict[str, Any]) -> None:
    order = ["Cu-64", "Cu-66", "Cu-62", "Cu-61", "O-15"]
    rows = {row["nuclide"]: row for row in activation["comparison_rows"]}
    y = np.arange(len(order))
    mass = np.asarray([rows[name]["mass_neutron_only_Bq"] for name in order], dtype=float)
    s3 = np.asarray([rows[name]["s3_neutron_only_Bq"] for name in order], dtype=float)
    floor = 3e-4

    fig, ax = plt.subplots(figsize=(10.0, 6.3))
    ax.hlines(y, np.maximum(mass, floor), np.maximum(s3, floor), color=GRID, linewidth=3, zorder=1)
    ax.scatter(np.maximum(mass, floor), y, s=95, color=MASS_COLOR, label="Mass_511", zorder=3)
    ax.scatter(np.maximum(s3, floor), y, s=95, color=S3_COLOR, label="S3", zorder=3)
    ax.set_xscale("log")
    ax.set_xlim(floor, max(float(mass.max()), float(s3.max())) * 2.5)
    ax.set_yticks(y, order)
    ax.invert_yaxis()
    ax.set_xlabel("中子单独造成的第 15 天活度 (Bq)")
    fig.suptitle("氧、铜活化：Mass_511 与 S3 的中子单独贡献", fontsize=20, fontweight="bold", y=0.975)
    fig.text(0.5, 0.918, "8 个中子重复样本；按等效观测时间归一化；15 天连续照射", ha="center", color=MUTED, fontsize=11)
    ax.grid(axis="x", which="both", color=GRID, linewidth=0.75)
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.legend(frameon=False, loc="lower right")
    for idx, name in enumerate(order):
        ax.text(max(mass[idx], floor) * 0.92, idx - 0.13, f"{mass[idx]:.3g}", ha="right", va="bottom", color=MASS_COLOR, fontsize=9)
        ax.text(max(s3[idx], floor) * 1.08, idx + 0.13, f"{s3[idx]:.3g}", ha="left", va="top", color=S3_COLOR, fontsize=9)
    fig.text(0.01, 0.012, "活度由中子样本的放射性核素产额直接重算；不包含其他粒子造成的活化。", color=MUTED, fontsize=9.5)
    fig.tight_layout(rect=(0, 0.05, 1, 0.89))
    fig.savefig(ASSETS / "mass_s3_neutron_only_o_cu_activation.png", dpi=190)
    plt.close(fig)


def plot_cross_sections(cross_sections: dict[str, Any]) -> None:
    fig, (slow_ax, fast_ax) = plt.subplots(1, 2, figsize=(13.2, 5.9), gridspec_kw={"width_ratios": [1.05, 1.15]})
    for key in ("B10_nalpha", "Cu63_ng_Cu64"):
        energy, sigma = load_cross_section(CROSS_SECTION_FILES[key])
        mask = (energy >= 1e-3) & (energy <= 2e7) & (sigma > 0)
        slow_ax.plot(energy[mask], sigma[mask], linewidth=2.1, color=REACTION_META[key]["color"], label=REACTION_META[key]["label"])
    slow_ax.set_xscale("log")
    slow_ax.set_yscale("log")
    slow_ax.set_xlim(1e-3, 2e7)
    slow_ax.set_ylim(1e-3, 2e5)
    slow_ax.set_xlabel("中子能量 (eV)")
    slow_ax.set_ylabel("截面 (barn)")
    slow_ax.set_title("慢中子：硼吸收与铜俘获")
    slow_ax.grid(which="major", color=GRID, linewidth=0.8)
    slow_ax.grid(which="minor", color=GRID, linewidth=0.35, alpha=0.55)
    slow_ax.legend(frameon=False, fontsize=10, loc="lower left")
    slow_ax.axvline(0.0253, color=MUTED, linestyle=":", linewidth=1.2)
    slow_ax.text(0.031, 7e4, "热中子 0.025 eV", color=MUTED, fontsize=9, rotation=90, va="top")

    for key in ("Cu65_n2n_Cu64", "Cu63_n2n_Cu62", "O16_n2n_O15"):
        energy, sigma = load_cross_section(CROSS_SECTION_FILES[key])
        mask = (energy >= 8e6) & (energy <= 30e6) & (sigma > 0)
        fast_ax.plot(energy[mask] / 1e6, sigma[mask], linewidth=2.25, color=REACTION_META[key]["color"], label=REACTION_META[key]["label"])
    fast_ax.set_yscale("log")
    fast_ax.set_xlim(8, 30)
    fast_ax.set_ylim(1e-5, 2)
    fast_ax.set_xlabel("中子能量 (MeV)")
    fast_ax.set_ylabel("截面 (barn)")
    fast_ax.set_title("快中子：产生 511 keV 相关核素")
    fast_ax.grid(which="major", color=GRID, linewidth=0.8)
    fast_ax.grid(which="minor", color=GRID, linewidth=0.35, alpha=0.55)
    fast_ax.legend(frameon=False, fontsize=9.5, loc="lower right")

    fig.suptitle("为什么先慢化、再由硼吸收：关键活化截面", fontsize=18, fontweight="bold", y=1.01)
    fig.text(0.01, 0.012, "数据：NNDC ENDF API，ENDF/B-VIII.1，293.15 K。1 barn = 10^-24 cm^2。", color=MUTED, fontsize=9.5)
    fig.tight_layout(rect=(0, 0.05, 1, 0.98))
    fig.savefig(ASSETS / "b10_o_cu_activation_cross_sections.png", dpi=190, bbox_inches="tight")
    plt.close(fig)


def write_summary(transport: dict[str, Any], activation: dict[str, Any], cross_sections: dict[str, Any]) -> None:
    payload = {
        "status": "PASS_MASS511_S3_BPE_EVIDENCE_BUILT",
        "generated_at_utc": now_utc(),
        "transport": transport,
        "activation": activation,
        "cross_sections": cross_sections,
        "claim_boundaries": [
            "Mass_511 versus S3 is a full-geometry comparison. S3 changes the active CsI shell, plastic skin and BPE stack; it is not a BPE-only A/B transport.",
            "The remaining-neutron number is the rate of matched primary-neutron histories that later make an IA interaction inside the BPE inner envelope. It is not a surface-current or boundary-fluence tally and misses through-going neutrons that never interact.",
            "BPE passive-deposit counts come from PM BoratedPolyethylene5wtB records. Geometric BPE interaction/capture counts use the nominal BPE shell and do not model support-relief holes in the point classifier.",
            "O/Cu activities are neutron-only, TT-divided reconstructions from the eight buildup DAT replicas. Ground-state half-lives come from the retained S3 cache; all-particle fixed-source activities are shown only as context.",
            "Evaluated cross sections are ENDF/B-VIII.1 at 293.15 K from the official NNDC ENDF REST API; they are microscopic cross sections, not folded reaction rates.",
        ],
        "outputs": {
            "transport_energy_bins": rel(DATA / "mass_s3_postshield_interaction_energy_bins.csv"),
            "activation_csv": rel(DATA / "mass_s3_neutron_only_o_cu_activation.csv"),
            "cross_sections_csv": rel(DATA / "endfb_viii1_o_cu_b10_cross_sections.csv"),
            "figures": [
                rel(ASSETS / "mass_s3_postshield_neutron_count.png"),
                rel(ASSETS / "mass_s3_postshield_neutron_spectrum.png"),
                rel(ASSETS / "mass_s3_neutron_only_o_cu_activation.png"),
                rel(ASSETS / "b10_o_cu_activation_cross_sections.png"),
            ],
        },
    }
    (DATA / "bpe_evidence_summary.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def validate_outputs() -> None:
    expected = [
        DATA / "bpe_evidence_summary.json",
        DATA / "mass_s3_postshield_interaction_energy_bins.csv",
        DATA / "mass_s3_neutron_only_o_cu_activation.csv",
        DATA / "endfb_viii1_o_cu_b10_cross_sections.csv",
        ASSETS / "mass_s3_postshield_neutron_count.png",
        ASSETS / "mass_s3_postshield_neutron_spectrum.png",
        ASSETS / "mass_s3_neutron_only_o_cu_activation.png",
        ASSETS / "b10_o_cu_activation_cross_sections.png",
    ]
    missing = [str(path) for path in expected if not path.exists() or path.stat().st_size <= 0]
    if missing:
        raise RuntimeError(f"missing/empty outputs: {missing}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--render-only", action="store_true", help="reuse the existing JSON summary and redraw figures")
    args = parser.parse_args()
    ASSETS.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    setup_plot_style()

    if args.render_only:
        summary_path = DATA / "bpe_evidence_summary.json"
        retained = json.loads(summary_path.read_text(encoding="utf-8"))
        transport = retained["transport"]
        activation = retained["activation"]
        cross_sections = retained["cross_sections"]
        write_transport_bins(transport)
        print("[1/4] Reusing retained transport evidence", flush=True)
        print("[2/4] Reusing retained activation evidence", flush=True)
        print("[3/4] Reusing retained ENDF/B-VIII.1 evidence", flush=True)
    else:
        print("[1/4] Parsing matched neutron IA histories (Mass_511 and S3)", flush=True)
        transport = build_transport_evidence(max(1, args.workers))
        write_transport_bins(transport)
        print("[2/4] Rebuilding neutron-only O/Cu day-15 activation", flush=True)
        activation = build_activation_evidence()
        print("[3/4] Reading official ENDF/B-VIII.1 cross sections", flush=True)
        cross_sections = build_cross_section_evidence()
    print("[4/4] Rendering white-background figures and summary", flush=True)
    plot_survivor_count(transport)
    plot_energy_spectrum(transport)
    plot_activation(activation)
    plot_cross_sections(cross_sections)
    write_summary(transport, activation, cross_sections)
    validate_outputs()
    print(json.dumps({"status": "PASS", "summary": rel(DATA / "bpe_evidence_summary.json")}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
