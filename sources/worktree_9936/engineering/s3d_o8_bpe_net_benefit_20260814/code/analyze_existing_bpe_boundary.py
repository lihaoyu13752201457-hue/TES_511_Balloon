#!/usr/bin/env python3
"""Re-audit the accepted S3d-O8 20 mm BPE watched-volume run.

This is deliberately a boundary ledger, not a 20 mm versus 0 mm background
comparison.  It adds the denominators and directional bookkeeping that are
needed before a topology proposal is defensible:

* all generated primary neutrons, binned by energy and global travel direction;
* the first nominal BPE contact, including surface, incidence cosine and zone;
* first-passage primary outcomes (transmission/moderation/reflection/etc.);
* secondary neutron and photon current leaving the nominal inner BPE surface.

The watched-volume file does not store a complete interaction genealogy.  A
primary neutron with no watched-volume EXIT is therefore labelled
``no_surviving_primary_exit`` and must not be called an absorption.  Likewise,
inner-emergent photons are a guard diagnostic, not a process-pure capture-gamma
tally.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


RUN_DEFAULT = Path(
    "/home/ubuntu/TES_511_Balloon/runs/particle_source_unit_repair_20260811/"
    "bpe_neutron_boundary_20260813/production_attempt04"
)
PACKAGE_DEFAULT = Path(__file__).resolve().parents[1]

IA_WATCHED_RE = re.compile(r"^IA\s+(ENTR|EXIT)\s+(.*)$")
IA_INIT_RE = re.compile(r"^IA\s+INIT\s+(.*)$")
ID_RE = re.compile(r"^ID\s+(\d+)")
EPS_CM = 2.0e-3

ENERGY_EDGES_KEV = np.asarray(
    [-np.inf, 5.0e-4, 100.0, 1.0e3, 1.0e4, 2.0e4, 3.9e4, 1.0e5, np.inf]
)
ENERGY_LABELS = [
    "<=0.5 eV",
    "0.5 eV-100 keV",
    "0.1-1 MeV",
    "1-10 MeV",
    "10-20 MeV",
    "20-39 MeV",
    "39-100 MeV",
    ">=100 MeV",
]
UZ_EDGES = np.linspace(-1.0, 1.0, 9)
UZ_LABELS = [f"[{UZ_EDGES[i]:+.2f},{UZ_EDGES[i + 1]:+.2f}{']' if i == 7 else ')'}" for i in range(8)]

OUTCOME_ORDER = [
    "transmitted_unchanged",
    "transmitted_mild_loss",
    "transmitted_moderated_10_90pct",
    "transmitted_strong_moderation",
    "transmitted_energy_gain",
    "reflected_to_outer_surface",
    "relief_or_edge_exit",
    "no_surviving_primary_exit",
]


@dataclass
class InitRecord:
    event_id: int
    energy_keV: float
    ux: float
    uy: float
    uz: float


@dataclass
class Crossing:
    sequence: int
    process: str
    origin: int
    particle: int
    x: float
    y: float
    z: float
    ux: float
    uy: float
    uz: float
    energy_keV: float
    role: str | None = None
    surface: str | None = None
    mu: float | None = None


@dataclass
class EventState:
    event_id: int | None = None
    init: InitRecord | None = None
    crossings: list[Crossing] = field(default_factory=list)


def world_to_local(x: float, y: float, z: float) -> tuple[float, float, float]:
    """Rotate global coordinates into InstrumentFrame (45 deg about y)."""
    c = math.sqrt(0.5)
    s = -math.sqrt(0.5)
    return c * x + s * z, y, -s * x + c * z


def nominal_boundary(crossing: Crossing) -> tuple[str, str, float] | None:
    """Classify crossings at the nominal 20 mm BPE envelope surfaces."""
    xl, yl, zl = world_to_local(crossing.x, crossing.y, crossing.z)
    uxl, uyl, uzl = world_to_local(crossing.ux, crossing.uy, crossing.uz)
    radius = math.hypot(xl, yl)
    radial_dot = (xl * uxl + yl * uyl) / radius if radius else 0.0

    if crossing.process == "ENTR":
        if abs(radius - 29.0) < EPS_CM and -24.5 + EPS_CM < zl < 46.0 - EPS_CM:
            if radial_dot < 0:
                return "outer_input", "side", -radial_dot
        if abs(zl + 26.5) < EPS_CM and radius < 29.0 - EPS_CM and uzl > 0:
            return "outer_input", "bottom", uzl
        if abs(zl - 48.0) < EPS_CM and radius < 29.0 - EPS_CM and uzl < 0:
            return "outer_input", "top", -uzl

        if abs(radius - 27.0) < EPS_CM and -24.5 + EPS_CM < zl < 46.0 - EPS_CM:
            if radial_dot > 0:
                return "inner_input", "side", radial_dot
        if abs(zl + 24.5) < EPS_CM and radius < 27.0 - EPS_CM and uzl < 0:
            return "inner_input", "bottom", -uzl
        if abs(zl - 46.0) < EPS_CM and radius < 27.0 - EPS_CM and uzl > 0:
            return "inner_input", "top", uzl

    if crossing.process == "EXIT":
        if abs(radius - 27.0) < EPS_CM and -24.5 + EPS_CM < zl < 46.0 - EPS_CM:
            if radial_dot < 0:
                return "inner_output", "side", -radial_dot
        if abs(zl + 24.5) < EPS_CM and radius < 27.0 - EPS_CM and uzl > 0:
            return "inner_output", "bottom", uzl
        if abs(zl - 46.0) < EPS_CM and radius < 27.0 - EPS_CM and uzl < 0:
            return "inner_output", "top", -uzl

        if abs(radius - 29.0) < EPS_CM and -24.5 + EPS_CM < zl < 46.0 - EPS_CM:
            if radial_dot > 0:
                return "outer_output", "side", radial_dot
        if abs(zl + 26.5) < EPS_CM and radius < 29.0 - EPS_CM and uzl < 0:
            return "outer_output", "bottom", -uzl
        if abs(zl - 48.0) < EPS_CM and radius < 29.0 - EPS_CM and uzl > 0:
            return "outer_output", "top", uzl
    return None


def parse_init(line: str, event_id: int) -> InitRecord | None:
    match = IA_INIT_RE.match(line)
    if not match:
        return None
    parts = [part.strip() for part in match.group(1).split(";")]
    if len(parts) < 23 or int(parts[15]) != 6:
        return None
    return InitRecord(
        event_id=event_id,
        energy_keV=float(parts[22]),
        ux=float(parts[16]),
        uy=float(parts[17]),
        uz=float(parts[18]),
    )


def parse_crossing(line: str, sequence: int) -> Crossing | None:
    match = IA_WATCHED_RE.match(line)
    if not match:
        return None
    parts = [part.strip() for part in match.group(2).split(";")]
    if len(parts) < 15:
        return None
    crossing = Crossing(
        sequence=sequence,
        process=match.group(1),
        origin=int(parts[1]),
        particle=int(parts[7]),
        x=float(parts[4]),
        y=float(parts[5]),
        z=float(parts[6]),
        ux=float(parts[8]),
        uy=float(parts[9]),
        uz=float(parts[10]),
        energy_keV=float(parts[14]),
    )
    classified = nominal_boundary(crossing)
    if classified:
        crossing.role, crossing.surface, crossing.mu = classified
    return crossing


def energy_band(energy_keV: float) -> str:
    index = int(np.searchsorted(ENERGY_EDGES_KEV, energy_keV, side="right") - 1)
    return ENERGY_LABELS[min(max(index, 0), len(ENERGY_LABELS) - 1)]


def uz_band(uz: float) -> str:
    index = int(np.searchsorted(UZ_EDGES, uz, side="right") - 1)
    return UZ_LABELS[min(max(index, 0), len(UZ_LABELS) - 1)]


def contact_zone(contact: Crossing) -> tuple[str, str, float, float]:
    xl, yl, zl = world_to_local(contact.x, contact.y, contact.z)
    radius = math.hypot(xl, yl)
    phi_deg = math.degrees(math.atan2(yl, xl)) % 360.0
    sector = int(phi_deg // 45.0)
    if contact.surface == "side":
        z_index = min(2, max(0, int((zl + 24.5) / (70.5 / 3.0))))
        zone = f"side_z{z_index}_phi{sector}"
    else:
        r_index = min(2, max(0, int(radius / (29.0 / 3.0))))
        zone = f"{contact.surface}_r{r_index}_phi{sector}"
    return zone, f"phi{sector}", zl, phi_deg


def primary_outcome(entry_energy: float, exit_energy: float | None, terminal: str) -> str:
    if exit_energy is None:
        return terminal
    ratio = exit_energy / entry_energy if entry_energy > 0 else math.nan
    if ratio > 1.0 + 1.0e-6:
        return "transmitted_energy_gain"
    if abs(ratio - 1.0) <= 1.0e-6:
        return "transmitted_unchanged"
    if ratio >= 0.9:
        return "transmitted_mild_loss"
    if ratio >= 0.1:
        return "transmitted_moderated_10_90pct"
    return "transmitted_strong_moderation"


def wilson_interval(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return math.nan, math.nan
    p = k / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denom
    half = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / denom
    return center - half, center + half


def process_event(
    event: EventState,
    shard: str,
    source_rows: list[dict],
    contact_rows: list[dict],
    secondary_rows: list[dict],
    current_counts: Counter,
) -> None:
    if event.event_id is None or event.init is None:
        return
    init = event.init
    source_rows.append(
        {
            "shard": shard,
            "event_id": init.event_id,
            "source_energy_keV": init.energy_keV,
            "energy_band": energy_band(init.energy_keV),
            "source_ux": init.ux,
            "source_uy": init.uy,
            "source_uz": init.uz,
            "uz_band": uz_band(init.uz),
        }
    )

    primary_neutrons = [c for c in event.crossings if c.particle == 6 and c.origin == 1]
    contact = next((c for c in primary_neutrons if c.role == "outer_input"), None)
    if contact is not None:
        after = [c for c in primary_neutrons if c.sequence > contact.sequence]
        inner = next((c for c in after if c.role == "inner_output"), None)
        if inner is not None:
            terminal = "transmitted"
            exit_energy = inner.energy_keV
        elif any(c.role == "outer_output" for c in after):
            terminal = "reflected_to_outer_surface"
            exit_energy = None
        elif any(c.process == "EXIT" for c in after):
            terminal = "relief_or_edge_exit"
            exit_energy = None
        else:
            terminal = "no_surviving_primary_exit"
            exit_energy = None
        outcome = primary_outcome(contact.energy_keV, exit_energy, terminal)
        zone, phi_sector, local_z, local_phi = contact_zone(contact)
        ratio = exit_energy / contact.energy_keV if exit_energy is not None and contact.energy_keV > 0 else math.nan
        contact_rows.append(
            {
                "shard": shard,
                "event_id": init.event_id,
                "source_energy_keV": init.energy_keV,
                "source_uz": init.uz,
                "contact_energy_keV": contact.energy_keV,
                "source_energy_band": energy_band(init.energy_keV),
                "contact_energy_band": energy_band(contact.energy_keV),
                "uz_band": uz_band(init.uz),
                "surface": contact.surface,
                "incidence_mu": contact.mu,
                "zone": zone,
                "phi_sector": phi_sector,
                "local_z_cm": local_z,
                "local_phi_deg": local_phi,
                "outcome": outcome,
                "reached_inner": int(inner is not None),
                "inner_energy_keV": exit_energy,
                "energy_ratio": ratio,
            }
        )

    entered_origins: set[int] = set()
    for crossing in event.crossings:
        if crossing.process == "ENTR":
            entered_origins.add(crossing.origin)
        if crossing.role:
            current_counts[(crossing.role, crossing.surface, crossing.particle)] += 1
        if crossing.role != "inner_output" or crossing.origin == 1 or crossing.particle not in (1, 6):
            continue
        born_in_watched_bpe = crossing.origin not in entered_origins
        label = "photon" if crossing.particle == 1 else "neutron"
        if label == "photon" and abs(crossing.energy_keV - 477.6) <= 2.0:
            line_class = "B10_478keV_window"
        elif label == "photon" and abs(crossing.energy_keV - 2223.25) <= 10.0:
            line_class = "H_2223keV_window"
        else:
            line_class = "other"
        secondary_rows.append(
            {
                "shard": shard,
                "event_id": init.event_id,
                "particle": label,
                "origin": crossing.origin,
                "surface": crossing.surface,
                "energy_keV": crossing.energy_keV,
                "energy_band": energy_band(crossing.energy_keV),
                "born_in_watched_bpe": int(born_in_watched_bpe),
                "line_class": line_class,
            }
        )


def parse_sim(path: Path, source_rows: list[dict], contact_rows: list[dict], secondary_rows: list[dict], current_counts: Counter) -> None:
    shard = path.parent.name
    event = EventState()
    sequence = 0
    with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if line == "SE":
                process_event(event, shard, source_rows, contact_rows, secondary_rows, current_counts)
                event = EventState()
                sequence = 0
                continue
            id_match = ID_RE.match(line)
            if id_match:
                event.event_id = int(id_match.group(1))
                continue
            if line.startswith("IA INIT") and event.event_id is not None:
                event.init = parse_init(line, event.event_id)
                continue
            if line.startswith(("IA ENTR", "IA EXIT")):
                sequence += 1
                crossing = parse_crossing(line, sequence)
                if crossing is not None:
                    event.crossings.append(crossing)
    process_event(event, shard, source_rows, contact_rows, secondary_rows, current_counts)


def aggregate_source(source: pd.DataFrame, contacts: pd.DataFrame) -> pd.DataFrame:
    source_counts = source.groupby(["energy_band", "uz_band"], observed=False).size().rename("source_histories")
    contact_counts = (
        contacts.groupby(["source_energy_band", "uz_band"], observed=False)
        .size()
        .rename("first_contacts")
    )
    contact_counts.index = contact_counts.index.set_names(["energy_band", "uz_band"])
    table = pd.concat([source_counts, contact_counts], axis=1).fillna(0).reset_index()
    table["source_histories"] = table["source_histories"].astype(int)
    table["first_contacts"] = table["first_contacts"].astype(int)
    table["contact_probability"] = table["first_contacts"] / table["source_histories"].replace(0, np.nan)
    return table


def aggregate_outcomes(contacts: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    group_cols = ["contact_energy_band", "surface", "uz_band"]
    for keys, frame in contacts.groupby(group_cols, observed=False):
        n = len(frame)
        shard_den = frame.groupby("shard").size()
        for outcome in OUTCOME_ORDER:
            k = int((frame["outcome"] == outcome).sum())
            low, high = wilson_interval(k, n)
            per_shard = (
                frame.assign(hit=(frame["outcome"] == outcome).astype(int))
                .groupby("shard")["hit"]
                .agg(["sum", "count"])
            )
            fractions = per_shard["sum"] / per_shard["count"]
            rows.append(
                {
                    "contact_energy_band": keys[0],
                    "surface": keys[1],
                    "uz_band": keys[2],
                    "outcome": outcome,
                    "count": k,
                    "contact_denominator": n,
                    "fraction": k / n if n else math.nan,
                    "wilson95_low": low,
                    "wilson95_high": high,
                    "shards_with_denominator": int((shard_den > 0).sum()),
                    "shard_fraction_sd": float(fractions.std(ddof=1)) if len(fractions) > 1 else math.nan,
                    "shard_fraction_sem": float(fractions.sem(ddof=1)) if len(fractions) > 1 else math.nan,
                }
            )
    return pd.DataFrame(rows)


def aggregate_spatial(contacts: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for (surface, zone), frame in contacts.groupby(["surface", "zone"], observed=False):
        n = len(frame)
        k = int(frame["reached_inner"].sum())
        low, high = wilson_interval(k, n)
        shard = frame.groupby("shard")["reached_inner"].agg(["sum", "count"])
        fractions = shard["sum"] / shard["count"]
        rows.append(
            {
                "surface": surface,
                "zone": zone,
                "contact_denominator": n,
                "reached_inner": k,
                "transmission_fraction": k / n,
                "wilson95_low": low,
                "wilson95_high": high,
                "shards_with_denominator": len(shard),
                "shard_fraction_sd": float(fractions.std(ddof=1)) if len(fractions) > 1 else math.nan,
                "shard_fraction_sem": float(fractions.sem(ddof=1)) if len(fractions) > 1 else math.nan,
                "median_contact_energy_keV": float(frame["contact_energy_keV"].median()),
                "median_incidence_mu": float(frame["incidence_mu"].median()),
            }
        )
    return pd.DataFrame(rows).sort_values(["surface", "zone"])


def style_axes(ax: plt.Axes) -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#d9dee8", linewidth=0.7, alpha=0.7)


def plot_denominators(source_agg: pd.DataFrame, out: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13.2, 5.2), constrained_layout=True)
    for ax, field, title, cmap in [
        (axes[0], "source_histories", "Generated source histories", "Blues"),
        (axes[1], "contact_probability", "Probability of first nominal BPE contact", "YlOrRd"),
    ]:
        pivot = source_agg.pivot(index="energy_band", columns="uz_band", values=field).reindex(
            index=ENERGY_LABELS, columns=UZ_LABELS
        )
        image = ax.imshow(pivot.to_numpy(), aspect="auto", cmap=cmap)
        ax.set_title(title, loc="left", fontsize=12, weight="bold")
        ax.set_xlabel("Global neutron travel direction $u_z$")
        ax.set_ylabel("Incident neutron energy")
        ax.set_xticks(range(len(UZ_LABELS)), UZ_LABELS, rotation=45, ha="right", fontsize=8)
        ax.set_yticks(range(len(ENERGY_LABELS)), ENERGY_LABELS, fontsize=9)
        fig.colorbar(image, ax=ax, fraction=0.045, pad=0.03)
    fig.suptitle("S3d-O8 20 mm BPE: incident denominator and geometric interception", fontsize=15, weight="bold")
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_transport(contacts: pd.DataFrame, out: Path) -> None:
    grouped = (
        contacts.groupby(["contact_energy_band", "outcome"], observed=False)
        .size()
        .unstack(fill_value=0)
        .reindex(index=ENERGY_LABELS, columns=OUTCOME_ORDER, fill_value=0)
    )
    fractions = grouped.div(grouped.sum(axis=1), axis=0)
    colors = ["#4f6bed", "#75a7ff", "#42b8a5", "#167d6f", "#f0a33a", "#9c6ade", "#d66b5d", "#60697a"]
    labels = [
        "unchanged",
        "<10% loss",
        "10-90% loss",
        ">90% loss",
        "energy gain",
        "back-reflected",
        "relief/edge exit",
        "no primary exit",
    ]
    fig, ax = plt.subplots(figsize=(11.8, 5.6), constrained_layout=True)
    bottom = np.zeros(len(fractions))
    for outcome, color, label in zip(OUTCOME_ORDER, colors, labels):
        values = fractions[outcome].to_numpy()
        ax.bar(ENERGY_LABELS, values, bottom=bottom, color=color, width=0.78, label=label)
        bottom += values
    ax.set_ylim(0, 1)
    ax.set_ylabel("Fraction of first-contact histories")
    ax.set_xlabel("Energy at first BPE contact")
    ax.set_title("What 20 mm BPE does to the primary neutron", loc="left", fontsize=14, weight="bold")
    ax.tick_params(axis="x", rotation=30)
    ax.legend(ncol=4, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.20))
    style_axes(ax)
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_spatial(spatial: pd.DataFrame, out: Path) -> None:
    side = spatial[spatial["surface"] == "side"].copy()
    matrix = np.full((3, 8), np.nan)
    denom = np.zeros((3, 8), dtype=int)
    for row in side.itertuples():
        match = re.match(r"side_z(\d)_phi(\d)", row.zone)
        if not match:
            continue
        zi, pi = map(int, match.groups())
        matrix[zi, pi] = row.transmission_fraction
        denom[zi, pi] = row.contact_denominator
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.4), constrained_layout=True)
    im0 = axes[0].imshow(matrix, origin="lower", aspect="auto", vmin=0, vmax=1, cmap="viridis")
    axes[0].set_title("Conditional primary transmission", loc="left", weight="bold")
    axes[0].set_xlabel("Local azimuth sector (45° each)")
    axes[0].set_ylabel("Side-shell local-z third")
    axes[0].set_xticks(range(8), [f"{45*i}–{45*(i+1)}°" for i in range(8)], rotation=35, ha="right", fontsize=8)
    axes[0].set_yticks(range(3), ["low", "middle", "high"])
    fig.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.03)
    im1 = axes[1].imshow(denom, origin="lower", aspect="auto", cmap="Blues")
    axes[1].set_title("Incident denominator", loc="left", weight="bold")
    axes[1].set_xlabel("Local azimuth sector (45° each)")
    axes[1].set_ylabel("Side-shell local-z third")
    axes[1].set_xticks(range(8), [f"{45*i}–{45*(i+1)}°" for i in range(8)], rotation=35, ha="right", fontsize=8)
    axes[1].set_yticks(range(3), ["low", "middle", "high"])
    fig.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.03)
    fig.suptitle("Side-shell spatial map — denominator shown beside efficiency", fontsize=14, weight="bold")
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_secondaries(secondaries: pd.DataFrame, out: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.8), constrained_layout=True)
    for particle, color in [("neutron", "#4f6bed"), ("photon", "#e07142")]:
        values = secondaries.loc[
            (secondaries["particle"] == particle) & (secondaries["energy_keV"] > 0), "energy_keV"
        ].to_numpy()
        if len(values):
            bins = np.logspace(-9, 9, 145)
            axes[0].hist(values, bins=bins, histtype="step", linewidth=1.6, color=color, label=f"{particle} (crossings)")
    axes[0].set_xscale("log")
    axes[0].set_yscale("log")
    axes[0].set_xlabel("Inner-emergent energy (keV)")
    axes[0].set_ylabel("Watched-volume crossings")
    axes[0].set_title("Secondary inward current", loc="left", weight="bold")
    axes[0].legend(frameon=False)
    style_axes(axes[0])

    photons = secondaries[secondaries["particle"] == "photon"]
    line_counts = photons.groupby(["line_class", "born_in_watched_bpe"], observed=False).size().unstack(fill_value=0)
    line_counts = line_counts.reindex(["B10_478keV_window", "H_2223keV_window", "other"], fill_value=0)
    x = np.arange(len(line_counts))
    axes[1].bar(x, line_counts.get(0, pd.Series(0, index=line_counts.index)), color="#b8c0cc", label="entered BPE earlier")
    axes[1].bar(
        x,
        line_counts.get(1, pd.Series(0, index=line_counts.index)),
        bottom=line_counts.get(0, pd.Series(0, index=line_counts.index)),
        color="#e07142",
        label="track first seen exiting BPE",
    )
    axes[1].set_xticks(x, ["478 keV window", "2.223 MeV window", "other photons"], rotation=20, ha="right")
    axes[1].set_ylabel("Inner-emergent photon crossings")
    axes[1].set_title("Capture-line guard (not process-pure)", loc="left", weight="bold")
    axes[1].legend(frameon=False)
    style_axes(axes[1])
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, default=RUN_DEFAULT)
    parser.add_argument("--package", type=Path, default=PACKAGE_DEFAULT)
    args = parser.parse_args()
    data_dir = args.package / "data"
    figure_dir = args.package / "figures"
    data_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    sim_paths = sorted(args.run.glob("shard*/*.sim.gz"))
    if len(sim_paths) != 8:
        raise SystemExit(f"Expected 8 accepted shard SIMs, found {len(sim_paths)}")
    source_rows: list[dict] = []
    contact_rows: list[dict] = []
    secondary_rows: list[dict] = []
    current_counts: Counter = Counter()
    for path in sim_paths:
        print(f"streaming {path}", flush=True)
        parse_sim(path, source_rows, contact_rows, secondary_rows, current_counts)

    source = pd.DataFrame(source_rows)
    contacts = pd.DataFrame(contact_rows)
    secondaries = pd.DataFrame(secondary_rows)
    source["energy_band"] = pd.Categorical(source["energy_band"], ENERGY_LABELS, ordered=True)
    source["uz_band"] = pd.Categorical(source["uz_band"], UZ_LABELS, ordered=True)
    contacts["source_energy_band"] = pd.Categorical(contacts["source_energy_band"], ENERGY_LABELS, ordered=True)
    contacts["contact_energy_band"] = pd.Categorical(contacts["contact_energy_band"], ENERGY_LABELS, ordered=True)
    contacts["uz_band"] = pd.Categorical(contacts["uz_band"], UZ_LABELS, ordered=True)

    if len(source) != 100_000:
        raise SystemExit(f"Expected 100000 primary INIT records, found {len(source)}")
    source_agg = aggregate_source(source, contacts)
    outcomes = aggregate_outcomes(contacts)
    spatial = aggregate_spatial(contacts)

    contacts.to_csv(data_dir / "contact_event_outcomes.csv", index=False)
    source_agg.to_csv(data_dir / "incident_energy_direction_denominator.csv", index=False)
    outcomes.to_csv(data_dir / "boundary_outcomes_by_energy_surface_direction.csv", index=False)
    spatial.to_csv(data_dir / "spatial_zone_stats.csv", index=False)
    secondaries.to_csv(data_dir / "inner_emergent_secondaries.csv", index=False)

    transmitted = contacts[contacts["reached_inner"] == 1]
    surface_stats = []
    for surface, frame in contacts.groupby("surface"):
        k = int(frame["reached_inner"].sum())
        low, high = wilson_interval(k, len(frame))
        surface_stats.append(
            {
                "surface": surface,
                "contacts": len(frame),
                "reached_inner": k,
                "fraction": k / len(frame),
                "wilson95": [low, high],
            }
        )
    line_counts = (
        secondaries[secondaries["particle"] == "photon"]
        .groupby(["line_class", "born_in_watched_bpe"])
        .size()
        .to_dict()
    )
    summary = {
        "scope": "accepted 20 mm BPE watched-volume boundary run; not a 0 mm A/B comparison",
        "run": str(args.run),
        "sim_files": [str(path) for path in sim_paths],
        "generated_primary_neutrons": len(source),
        "unique_primary_first_contacts": len(contacts),
        "first_contact_probability": len(contacts) / len(source),
        "unique_primary_reached_inner": int(contacts["reached_inner"].sum()),
        "conditional_transmission": float(contacts["reached_inner"].mean()),
        "conditional_transmission_wilson95": wilson_interval(int(contacts["reached_inner"].sum()), len(contacts)),
        "outcome_counts": {key: int((contacts["outcome"] == key).sum()) for key in OUTCOME_ORDER},
        "surface_stats": surface_stats,
        "contact_energy_median_keV": float(contacts["contact_energy_keV"].median()),
        "inner_primary_energy_median_keV": float(transmitted["inner_energy_keV"].median()),
        "secondary_inner_output_records": len(secondaries),
        "secondary_inner_output_by_particle": {k: int(v) for k, v in secondaries.groupby("particle").size().to_dict().items()},
        "secondary_tracks_first_seen_exiting_bpe": int(secondaries["born_in_watched_bpe"].sum()),
        "photon_line_guard_counts": {f"{k[0]}|born={k[1]}": int(v) for k, v in line_counts.items()},
        "all_nominal_surface_crossing_counts": {
            f"{role}|{surface}|particle={particle}": int(count)
            for (role, surface, particle), count in sorted(current_counts.items())
        },
        "interpretation_guard": [
            "no_surviving_primary_exit is not a process-pure absorption tally",
            "inner-emergent photon line windows are not process-pure capture-gamma tallies",
            "crossing counts include recrossings; unique first-contact and first-passage counts do not",
            "this run contains no 0 mm BPE control, downstream inventory, selected W2, prompt veto, or focused-signal response",
        ],
    }
    (data_dir / "bpe_boundary_reaudit_summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    plot_denominators(source_agg, figure_dir / "bpe_energy_direction_denominators.png")
    plot_transport(contacts, figure_dir / "bpe_primary_transport_ledger.png")
    plot_spatial(spatial, figure_dir / "bpe_side_spatial_denominator_map.png")
    plot_secondaries(secondaries, figure_dir / "bpe_inner_emergent_secondaries.png")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
