#!/usr/bin/env python3
"""W2 incident-angle and neutron-depth audit plots for the current geo-opt run.

This reads existing event-level audit products only.  It does not change
geometry and does not launch transport.
"""

from __future__ import annotations

import csv
import json
import math
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
RAY_EVENTS = WORK / "w2_all_particle_ray_overlay_events.csv"
DEPTH_PROXY = WORK / "html_conclusion_report_20260707/data/neutron_energy_depth_proxy.csv"
ATM511_SOURCE = (
    ROOT
    / "runs/geometry_optimization_20260704/p2_atm511_unit_geo_opt_s1_bpe_w5_fullstat_v1"
    / "Atm511LowerUnit3M_GeoOptS1BpeW5.source"
)

OUT = WORK / "figures/w2_angle_depth_audit_20260707"
DATA_OUT = WORK / "angle_depth_audit_20260707"
ANGLE_EVENTS_CSV = DATA_OUT / "w2_incident_angle_events.csv"
ENTRY_COUNTS_CSV = DATA_OUT / "w2_entry_class_counts.csv"
NEUTRON_DEPTH_CSV = DATA_OUT / "w2_neutron_energy_depth_with_entry.csv"
SUMMARY_JSON = DATA_OUT / "w2_angle_depth_summary.json"

W2_WINDOW = "w2_510p58_511p42"
RAW_STAGE = "raw"

TOKENS = {
    "surface": "#FCFCFD",
    "panel": "#FFFFFF",
    "ink": "#1F2430",
    "muted": "#6F768A",
    "grid": "#E6E8F0",
    "axis": "#D7DBE7",
}

COLORS = {
    "blue": {"base": "#A3BEFA", "mid": "#5477C4", "dark": "#2E4780"},
    "gold": {"base": "#FFE15B", "mid": "#B8A037", "dark": "#736422"},
    "orange": {"base": "#F0986E", "mid": "#CC6F47", "dark": "#804126"},
    "olive": {"base": "#A3D576", "mid": "#71B436", "dark": "#386411"},
    "pink": {"base": "#F390CA", "mid": "#BD569B", "dark": "#8A3A6F"},
    "neutral": {"base": "#C5CAD3", "mid": "#7A828F", "dark": "#464C55"},
}

ENTRY_ORDER = [
    "side_window",
    "side_wall",
    "top",
    "bottom",
    "envelope_miss",
    "unknown",
]
ENTRY_STYLE = {
    "side_window": {"label": "side window proxy", "color": COLORS["gold"]["base"], "edge": COLORS["gold"]["dark"], "marker": "*"},
    "side_wall": {"label": "side wall", "color": COLORS["blue"]["base"], "edge": COLORS["blue"]["dark"], "marker": "o"},
    "top": {"label": "top", "color": COLORS["olive"]["base"], "edge": COLORS["olive"]["dark"], "marker": "^"},
    "bottom": {"label": "bottom", "color": COLORS["orange"]["base"], "edge": COLORS["orange"]["dark"], "marker": "s"},
    "envelope_miss": {"label": "envelope miss", "color": COLORS["neutral"]["base"], "edge": COLORS["neutral"]["dark"], "marker": "x"},
    "unknown": {"label": "unknown", "color": COLORS["pink"]["base"], "edge": COLORS["pink"]["dark"], "marker": "D"},
}

STATUS_STYLE = {
    "active veto reject": {"label": "active veto reject", "color": COLORS["orange"]["base"], "edge": COLORS["orange"]["dark"]},
    "active pass, Compton/FoV veto": {"label": "active pass, Compton/FoV veto", "color": COLORS["gold"]["base"], "edge": COLORS["gold"]["dark"]},
    "final pass": {"label": "final pass", "color": COLORS["blue"]["base"], "edge": COLORS["blue"]["dark"]},
}

PARTICLE_LABEL = {
    "atm511": "atm511",
    "eplus": "e+",
    "n": "n",
    "activation": "activation",
    "muplus": "mu+",
    "muminus": "mu-",
    "gamma": "gamma",
    "p": "p",
}


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def maybe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(out):
        return None
    return out


def rotate_y(vec: tuple[float, float, float] | list[float] | np.ndarray, angle_deg: float) -> np.ndarray:
    x, y, z = [float(v) for v in vec]
    a = math.radians(angle_deg)
    c = math.cos(a)
    s = math.sin(a)
    return np.asarray([c * x + s * z, y, -s * x + c * z], dtype=float)


def local_angles(row: dict[str, Any]) -> tuple[float | None, float | None]:
    dx = maybe_float(row.get("dir_x"))
    dy = maybe_float(row.get("dir_y"))
    dz = maybe_float(row.get("dir_z"))
    if dx is None or dy is None or dz is None:
        return None, None
    d = rotate_y((dx, dy, dz), -45.0)
    norm = float(np.linalg.norm(d))
    if norm <= 0:
        return None, None
    d = d / norm
    theta = math.degrees(math.acos(max(-1.0, min(1.0, float(d[2])))))
    phi = math.degrees(math.atan2(float(d[1]), float(d[0]))) % 360.0
    return theta, phi


def entry_class(row: dict[str, Any]) -> str:
    region = str(row.get("entry_region_proxy") or "")
    surface = str(row.get("entry_surface_proxy") or "")
    canonical = str(row.get("entry_region") or "")
    if region == "side_neg_x_window_axis_pm15deg" or canonical == "side_window":
        return "side_window"
    if surface == "side":
        return "side_wall"
    if surface == "top":
        return "top"
    if surface == "bottom":
        return "bottom"
    if surface == "miss_current_outer_envelope":
        return "envelope_miss"
    return "unknown"


def phi_sector(phi_deg: float) -> str:
    phi = phi_deg % 360.0
    idx = int(math.floor((phi + 22.5) / 45.0)) % 8
    return f"phi{idx:02d}_{idx * 45:03d}deg"


def signed_window_axis_delta_deg(phi_deg: float) -> float:
    return ((phi_deg - 180.0 + 180.0) % 360.0) - 180.0


def classify_envelope_entry(row: dict[str, Any]) -> dict[str, Any]:
    init = (maybe_float(row.get("init_x_cm")), maybe_float(row.get("init_y_cm")), maybe_float(row.get("init_z_cm")))
    direction = (maybe_float(row.get("dir_x")), maybe_float(row.get("dir_y")), maybe_float(row.get("dir_z")))
    if any(v is None for v in init) or any(v is None for v in direction):
        return {"entry_surface_proxy": "missing_init", "entry_region_proxy": "missing_init"}

    p = rotate_y((float(init[0]), float(init[1]), float(init[2])), -45.0)
    d = rotate_y((float(direction[0]), float(direction[1]), float(direction[2])), -45.0)
    norm = float(np.linalg.norm(d))
    if norm <= 0:
        return {"entry_surface_proxy": "bad_init_dir", "entry_region_proxy": "bad_init_dir"}
    d = d / norm

    r_outer = 27.9
    z_min = -23.6
    z_max = 7.7
    candidates: list[tuple[float, str, np.ndarray]] = []

    a = d[0] ** 2 + d[1] ** 2
    b = 2.0 * (p[0] * d[0] + p[1] * d[1])
    c = p[0] ** 2 + p[1] ** 2 - r_outer**2
    if abs(a) > 1.0e-15:
        disc = b * b - 4.0 * a * c
        if disc >= 0:
            root = math.sqrt(disc)
            for t in ((-b - root) / (2.0 * a), (-b + root) / (2.0 * a)):
                if t > 0:
                    q = p + t * d
                    if z_min - 1.0e-6 <= q[2] <= z_max + 1.0e-6:
                        candidates.append((float(t), "side", q))

    if abs(d[2]) > 1.0e-15:
        for z_cap, surface in ((z_min, "bottom"), (z_max, "top")):
            t = (z_cap - p[2]) / d[2]
            if t > 0:
                q = p + t * d
                if q[0] ** 2 + q[1] ** 2 <= r_outer**2 + 1.0e-6:
                    candidates.append((float(t), surface, q))

    if not candidates:
        phi0 = math.degrees(math.atan2(p[1], p[0])) % 360.0
        return {
            "entry_surface_proxy": "miss_current_outer_envelope",
            "entry_region_proxy": phi_sector(phi0),
            "entry_phi_deg_local": None,
        }

    _, surface, q = sorted(candidates, key=lambda item: item[0])[0]
    phi = math.degrees(math.atan2(q[1], q[0])) % 360.0
    delta = signed_window_axis_delta_deg(phi)
    if surface == "side" and abs(delta) <= 15.0:
        region = "side_neg_x_window_axis_pm15deg"
    elif surface == "side":
        region = f"side_{phi_sector(phi)}"
    else:
        region = f"{surface}_{phi_sector(phi)}"
    return {
        "entry_surface_proxy": surface,
        "entry_region_proxy": region,
        "entry_phi_deg_local": float(phi),
        "entry_window_axis_delta_deg": float(delta),
        "entry_local_x_cm": float(q[0]),
        "entry_local_y_cm": float(q[1]),
        "entry_local_z_cm": float(q[2]),
    }


def xz_quadrant(row: dict[str, Any]) -> str:
    x = maybe_float(row.get("init_x_cm"))
    z = maybe_float(row.get("init_z_cm"))
    if x is None or z is None:
        return "unknown"
    if x >= 0 and z >= 0:
        return "right_upper"
    if x >= 0 and z < 0:
        return "right_lower"
    if x < 0 and z >= 0:
        return "left_upper"
    return "left_lower"


def savefig(fig: Any, stem: str) -> dict[str, str]:
    OUT.mkdir(parents=True, exist_ok=True)
    png = OUT / f"{stem}.png"
    svg = OUT / f"{stem}.svg"
    fig.savefig(png, dpi=220, bbox_inches="tight")
    fig.savefig(svg, bbox_inches="tight")
    plt.close(fig)
    return {"png": rel(png), "svg": rel(svg)}


def set_theme() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": TOKENS["surface"],
            "axes.facecolor": TOKENS["panel"],
            "axes.edgecolor": TOKENS["axis"],
            "axes.labelcolor": TOKENS["ink"],
            "axes.titlecolor": TOKENS["ink"],
            "xtick.color": TOKENS["muted"],
            "ytick.color": TOKENS["muted"],
            "grid.color": TOKENS["grid"],
            "grid.linewidth": 0.8,
            "font.family": "DejaVu Sans",
        }
    )


def add_header(fig: Any, title: str, subtitle: str) -> None:
    fig.text(0.065, 0.985, title, ha="left", va="top", fontsize=14, fontweight="semibold", color=TOKENS["ink"])
    fig.text(0.065, 0.952, subtitle, ha="left", va="top", fontsize=9.5, color=TOKENS["muted"])


def load_w2_raw_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in read_csv(RAY_EVENTS):
        key = (row.get("source_family") or "", row.get("source_file") or "", row.get("local_id") or "")
        if key in seen:
            continue
        seen.add(key)
        theta, phi = local_angles(row)
        envelope = classify_envelope_entry(row)
        enriched = dict(row)
        enriched.update(envelope)
        enriched["theta_local_deg"] = theta
        enriched["phi_local_deg"] = phi
        dz = maybe_float(row.get("dir_z"))
        norm = math.sqrt(
            (maybe_float(row.get("dir_x")) or 0.0) ** 2
            + (maybe_float(row.get("dir_y")) or 0.0) ** 2
            + (maybe_float(row.get("dir_z")) or 0.0) ** 2
        )
        enriched["theta_from_global_plus_z_deg"] = math.degrees(math.acos(max(-1.0, min(1.0, dz / norm)))) if dz is not None and norm > 0 else None
        enriched["entry_class"] = entry_class(row)
        enriched["entry_class"] = entry_class(enriched)
        enriched["xz_init_quadrant"] = xz_quadrant(row)
        enriched["tes_energy_keV"] = row.get("tes_total_keV")
        enriched["first_recorded_volume"] = row.get("first_hit_volume")
        enriched["first_recorded_material"] = row.get("first_hit_category")
        rows.append(enriched)
    return rows


def particle_order(rows: list[dict[str, Any]]) -> list[str]:
    counts = Counter(str(r["source_family"]) for r in rows)
    return [k for k, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def histogram_counts(rows: list[dict[str, Any]], value_field: str, bins: np.ndarray, entry: str) -> np.ndarray:
    vals = [float(r[value_field]) for r in rows if r.get("entry_class") == entry and r.get(value_field) is not None]
    if not vals:
        return np.zeros(len(bins) - 1, dtype=int)
    counts, _ = np.histogram(vals, bins=bins)
    return counts.astype(int)


def plot_angle_hist(rows: list[dict[str, Any]], value_field: str, bins: np.ndarray, stem: str, axis_label: str, title: str, subtitle: str) -> dict[str, str]:
    families = particle_order(rows)
    ncols = 2
    nrows = int(math.ceil(len(families) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(13.2, 2.55 * nrows + 1.1), squeeze=False)
    centers = 0.5 * (bins[:-1] + bins[1:])
    width = float(np.diff(bins)[0]) * 0.90

    for idx, family in enumerate(families):
        ax = axes[idx // ncols][idx % ncols]
        part = [r for r in rows if r["source_family"] == family and r.get(value_field) is not None]
        bottom = np.zeros(len(bins) - 1, dtype=int)
        for entry in ENTRY_ORDER:
            counts = histogram_counts(part, value_field, bins, entry)
            if counts.sum() == 0:
                continue
            style = ENTRY_STYLE[entry]
            ax.bar(
                centers,
                counts,
                width=width,
                bottom=bottom,
                color=style["color"],
                edgecolor=style["edge"],
                linewidth=0.65,
            )
            bottom += counts
        if value_field == "phi_local_deg":
            ax.axvspan(165, 195, color=COLORS["gold"]["base"], alpha=0.13, linewidth=0)
            ax.axvline(180, color=COLORS["gold"]["dark"], linewidth=0.8, linestyle=":")
        ax.set_title(f"{PARTICLE_LABEL.get(family, family)} (n={len(part)})", fontsize=10, pad=2)
        ax.set_xlim(float(bins[0]), float(bins[-1]))
        ax.set_ylabel("count")
        ax.grid(axis="y", alpha=0.65)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        if idx // ncols == nrows - 1:
            ax.set_xlabel(axis_label)
        else:
            ax.set_xlabel("")

    for idx in range(len(families), nrows * ncols):
        axes[idx // ncols][idx % ncols].axis("off")

    handles = [
        Patch(facecolor=ENTRY_STYLE[e]["color"], edgecolor=ENTRY_STYLE[e]["edge"], label=ENTRY_STYLE[e]["label"])
        for e in ENTRY_ORDER
        if any(r.get("entry_class") == e for r in rows)
    ]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.52, 0.925), ncol=3, frameon=False, fontsize=8.5)
    add_header(fig, title, subtitle)
    fig.tight_layout(rect=[0.04, 0.04, 1.0, 0.88])
    return savefig(fig, stem)


def plot_entry_counts(rows: list[dict[str, Any]]) -> dict[str, str]:
    families = particle_order(rows)
    fig, ax = plt.subplots(figsize=(10.4, 5.6))
    y = np.arange(len(families))
    left = np.zeros(len(families), dtype=float)
    for entry in ENTRY_ORDER:
        vals = np.asarray([sum(1 for r in rows if r["source_family"] == f and r.get("entry_class") == entry) for f in families], dtype=float)
        if vals.sum() == 0:
            continue
        style = ENTRY_STYLE[entry]
        ax.barh(y, vals, left=left, color=style["color"], edgecolor=style["edge"], linewidth=0.8, label=style["label"])
        left += vals
    ax.set_yticks(y, [f"{PARTICLE_LABEL.get(f, f)} ({sum(1 for r in rows if r['source_family'] == f)})" for f in families])
    ax.invert_yaxis()
    ax.set_xlabel("W2 raw TES event count")
    ax.grid(axis="x", alpha=0.65)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.02), ncol=3, frameon=False, fontsize=8.5)
    add_header(
        fig,
        "W2 ingress class by particle",
        "Window is a proxy: side-envelope entry within ±15° of the local negative-X side-window axis; side wall is the remaining side entry.",
    )
    fig.tight_layout(rect=[0.04, 0.03, 1.0, 0.86])
    return savefig(fig, "w2_entry_class_by_particle")


def load_neutron_depth(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    n_by_id = {str(r.get("local_id")): r for r in rows if r.get("source_family") == "n"}
    out: list[dict[str, Any]] = []
    for row in read_csv(DEPTH_PROXY):
        local_id = str(row.get("local_id") or "")
        ingress = n_by_id.get(local_id, {})
        enriched: dict[str, Any] = dict(row)
        enriched["source_family"] = "n"
        enriched["entry_class"] = ingress.get("entry_class", "unknown")
        enriched["entry_surface_proxy"] = ingress.get("entry_surface_proxy", "")
        enriched["entry_region_proxy"] = ingress.get("entry_region_proxy", "")
        enriched["source_file"] = ingress.get("source_file", "")
        enriched["theta_local_deg"] = ingress.get("theta_local_deg")
        enriched["phi_local_deg"] = ingress.get("phi_local_deg")
        out.append(enriched)
    return out


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def plot_neutron_depth(depth_rows: list[dict[str, Any]]) -> dict[str, str]:
    plot_rows = [
        r
        for r in depth_rows
        if truthy(r.get("plotted"))
        and maybe_float(r.get("depth_projection_cm")) is not None
        and maybe_float(r.get("init_energy_keV")) is not None
        and (maybe_float(r.get("init_energy_keV")) or 0.0) > 0
    ]
    fig, ax = plt.subplots(figsize=(9.2, 5.7))
    for row in plot_rows:
        status = str(row.get("status") or "unknown")
        status_style = STATUS_STYLE.get(status, {"color": COLORS["neutral"]["base"], "edge": COLORS["neutral"]["dark"]})
        entry = str(row.get("entry_class") or "unknown")
        entry_style = ENTRY_STYLE.get(entry, ENTRY_STYLE["unknown"])
        ax.scatter(
            float(row["depth_projection_cm"]),
            max(1.0e-3, float(row["init_energy_keV"])),
            s=54 if entry == "side_window" else 42,
            marker=entry_style["marker"],
            color=status_style["color"],
            edgecolor=status_style["edge"] if entry_style["marker"] != "x" else status_style["color"],
            linewidth=0.8,
            alpha=0.86,
        )
    ax.set_yscale("log")
    ax.set_xlabel("First-hit depth proxy from envelope entry [cm]")
    ax.set_ylabel("Initial neutron energy [keV, log scale]")
    ax.grid(True, which="major", alpha=0.65)
    ax.grid(True, which="minor", axis="y", alpha=0.20)
    ax.axvline(0, color=TOKENS["ink"], linestyle=":", linewidth=0.8)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    status_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="",
            markersize=7,
            markerfacecolor=style["color"],
            markeredgecolor=style["edge"],
            label=style["label"],
        )
        for status, style in STATUS_STYLE.items()
        if any(str(r.get("status")) == status for r in plot_rows)
    ]
    entry_handles = [
        Line2D(
            [0],
            [0],
            marker=ENTRY_STYLE[e]["marker"],
            linestyle="",
            markersize=7,
            markerfacecolor=TOKENS["panel"] if ENTRY_STYLE[e]["marker"] != "x" else COLORS["neutral"]["dark"],
            markeredgecolor=COLORS["neutral"]["dark"],
            label=ENTRY_STYLE[e]["label"],
        )
        for e in ENTRY_ORDER
        if any(str(r.get("entry_class")) == e for r in plot_rows)
    ]
    leg1 = ax.legend(handles=status_handles, loc="lower left", bbox_to_anchor=(0, 1.02), frameon=False, ncol=3, fontsize=8.2)
    ax.add_artist(leg1)
    ax.legend(handles=entry_handles, loc="lower right", bbox_to_anchor=(1, 1.02), frameon=False, ncol=3, fontsize=8.2)
    not_plotted = len(depth_rows) - len(plot_rows)
    add_header(
        fig,
        "W2 neutron energy versus first-hit depth proxy",
        f"W2 raw neutron candidates with usable positive-energy projected depth: {len(plot_rows)}/{len(depth_rows)}; {not_plotted} are missing, negative-depth, or zero-energy proxy rows. This is not a continuous Geant4 energy-loss scorer.",
    )
    fig.tight_layout(rect=[0.04, 0.03, 1.0, 0.82])
    return savefig(fig, "w2_neutron_energy_vs_depth_entry_status")


def write_angle_events(rows: list[dict[str, Any]]) -> None:
    fields = [
        "source_family",
        "local_id",
        "source_file",
        "tes_energy_keV",
        "init_energy_keV",
        "theta_local_deg",
        "phi_local_deg",
        "theta_from_global_plus_z_deg",
        "entry_class",
        "entry_surface_proxy",
        "entry_region_proxy",
        "entry_phi_deg_local",
        "xz_init_quadrant",
        "first_recorded_volume",
        "first_recorded_material",
        "init_x_cm",
        "init_y_cm",
        "init_z_cm",
        "dir_x",
        "dir_y",
        "dir_z",
        "side_compton_class",
    ]
    write_csv(ANGLE_EVENTS_CSV, rows, fields)


def write_entry_counts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for family in particle_order(rows):
        total = sum(1 for r in rows if r["source_family"] == family)
        for entry in ENTRY_ORDER:
            count = sum(1 for r in rows if r["source_family"] == family and r.get("entry_class") == entry)
            if count == 0:
                continue
            out.append(
                {
                    "source_family": family,
                    "entry_class": entry,
                    "count": count,
                    "share": count / total if total else None,
                }
            )
    write_csv(ENTRY_COUNTS_CSV, out, ["source_family", "entry_class", "count", "share"])
    return out


def write_neutron_depth(depth_rows: list[dict[str, Any]]) -> None:
    fields = [
        "local_id",
        "status",
        "init_energy_keV",
        "depth_projection_cm",
        "depth_distance_cm",
        "entry_class",
        "entry_surface_proxy",
        "entry_region_proxy",
        "theta_local_deg",
        "phi_local_deg",
        "first_hit_category",
        "first_hit_volume",
        "plotted",
    ]
    write_csv(NEUTRON_DEPTH_CSV, depth_rows, fields)


def parse_atm511_source_definition() -> dict[str, Any]:
    source_text = ATM511_SOURCE.read_text(encoding="utf-8", errors="ignore")
    beams = []
    fluxes = []
    for raw in source_text.splitlines():
        line = raw.strip()
        if ".Beam FarFieldAreaSource" in line:
            parts = line.split()
            beams.append([float(parts[-4]), float(parts[-3]), float(parts[-2]), float(parts[-1])])
        if ".Flux " in line:
            fluxes.append(float(line.split()[-1]))
    theta_min = min(b[0] for b in beams) if beams else None
    theta_max = max(b[1] for b in beams) if beams else None
    phi_min = min(b[2] for b in beams) if beams else None
    phi_max = max(b[3] for b in beams) if beams else None
    return {
        "source_card": rel(ATM511_SOURCE),
        "name": "Atm511LowerUnit3M_GeoOptS1BpeW5",
        "particle_type": "gamma (MEGAlib ParticleType 1)",
        "spectrum": "Mono 511 keV",
        "beam_model": "FarFieldAreaSource",
        "theta_deg_range": [theta_min, theta_max],
        "phi_deg_range": [phi_min, phi_max],
        "number_of_theta_bins": len(beams),
        "flux_per_bin": fluxes[:3],
        "total_declared_flux": sum(fluxes),
        "interpretation": "Lower-hemisphere 511-keV line source, not a full-4pi isotropic source.",
    }


def summarize(rows: list[dict[str, Any]], entry_counts: list[dict[str, Any]], depth_rows: list[dict[str, Any]], figures: dict[str, Any]) -> dict[str, Any]:
    atm = [r for r in rows if r.get("source_family") == "atm511"]
    theta_vals = [float(r["theta_local_deg"]) for r in atm if r.get("theta_local_deg") is not None]
    phi_vals = [float(r["phi_local_deg"]) for r in atm if r.get("phi_local_deg") is not None]
    atm_entry = Counter(str(r.get("entry_class")) for r in atm)
    atm_quad = Counter(str(r.get("xz_init_quadrant")) for r in atm)
    by_family_entry: dict[str, dict[str, int]] = defaultdict(dict)
    for rec in entry_counts:
        by_family_entry[str(rec["source_family"])][str(rec["entry_class"])] = int(rec["count"])
    plotted_depth = [
        r
        for r in depth_rows
        if truthy(r.get("plotted"))
        and maybe_float(r.get("depth_projection_cm")) is not None
        and maybe_float(r.get("init_energy_keV")) is not None
        and (maybe_float(r.get("init_energy_keV")) or 0.0) > 0
    ]
    return {
        "status": "PASS_W2_ANGLE_DEPTH_AUDIT",
        "scope": "Current geo-opt W2 raw TES background candidates only.",
        "w2_window": W2_WINDOW,
        "angle_definition": {
            "frame": "local detector frame after rotate_y(world_direction, -45 deg)",
            "theta_local_deg": "acos(dir_local_z), 0 deg is +local z",
            "phi_local_deg": "atan2(dir_local_y, dir_local_x), 0..360 deg; side-window axis proxy is local phi=180 deg +/-15 deg",
        },
        "source_counts": dict(sorted(Counter(str(r["source_family"]) for r in rows).items())),
        "entry_counts_by_source_family": dict(sorted(by_family_entry.items())),
        "atm511_source_definition": parse_atm511_source_definition(),
        "atm511_w2_conditional_diagnostics": {
            "w2_raw_count": len(atm),
            "theta_local_deg_min_max": [min(theta_vals), max(theta_vals)] if theta_vals else None,
            "phi_local_deg_min_max": [min(phi_vals), max(phi_vals)] if phi_vals else None,
            "entry_class_counts": dict(sorted(atm_entry.items())),
            "xz_start_quadrant_counts": dict(sorted(atm_quad.items())),
        },
        "neutron_depth_proxy": {
            "rows_total": len(depth_rows),
            "rows_plotted_positive_energy_and_depth": len(plotted_depth),
            "rows_not_plotted": len(depth_rows) - len(plotted_depth),
            "depth_proxy_definition": "Projected distance from outer-envelope entry proxy to first recorded hit along the initial neutron direction.",
            "limitation": "This is a first-hit depth proxy, not a continuous kinetic-energy-vs-depth scorer.",
        },
        "outputs": {
            "angle_events_csv": rel(ANGLE_EVENTS_CSV),
            "entry_counts_csv": rel(ENTRY_COUNTS_CSV),
            "neutron_depth_csv": rel(NEUTRON_DEPTH_CSV),
            "summary_json": rel(SUMMARY_JSON),
            "figures": figures,
        },
    }


def main() -> int:
    set_theme()
    rows = load_w2_raw_rows()
    write_angle_events(rows)
    entry_counts = write_entry_counts(rows)
    depth_rows = load_neutron_depth(rows)
    write_neutron_depth(depth_rows)

    theta_bins = np.arange(0, 180 + 10, 10, dtype=float)
    phi_bins = np.arange(0, 360 + 30, 30, dtype=float)
    figures = {
        "theta_by_particle_entry": plot_angle_hist(
            rows,
            "theta_local_deg",
            theta_bins,
            "w2_incident_theta_by_particle_entry",
            "local theta [deg]",
            "W2 incident theta distributions by particle",
            "Raw TES candidates in 510.58-511.42 keV; bars are stacked by envelope-entry class.",
        ),
        "phi_by_particle_entry": plot_angle_hist(
            rows,
            "phi_local_deg",
            phi_bins,
            "w2_incident_phi_by_particle_entry",
            "local phi [deg]",
            "W2 incident phi distributions by particle",
            "Raw TES candidates in 510.58-511.42 keV; gold shading marks the side-window axis proxy at local phi=180 deg +/-15 deg.",
        ),
        "entry_class_by_particle": plot_entry_counts(rows),
        "neutron_energy_vs_depth": plot_neutron_depth(depth_rows),
    }

    summary = summarize(rows, entry_counts, depth_rows, figures)
    SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
