#!/usr/bin/env python3
"""Analyze corrected-neutron crossings of the three S3d-O8 BPE volumes."""

from __future__ import annotations

import csv
import gzip
import json
import math
import multiprocessing as mp
import re
import zlib
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "engineering/particle_source_unit_repair_20260811/bpe_neutron_boundary_20260813"
RUN = ROOT / "runs/particle_source_unit_repair_20260811/bpe_neutron_boundary_20260813/production_attempt04"
OUT = PACKAGE / "outputs"

G4NDL = Path(
    "/home/ubuntu/MEGAlib_Install/megalib-main/external/geant4_v10.02.p03/"
    "share/Geant4-10.2.3/data/G4NDL4.5"
)
CU63_PROD = G4NDL / "IsotopeProduction/CrossSection/29_63_Copper"
CU65_PROD = G4NDL / "IsotopeProduction/CrossSection/29_65_Copper"
CU63_CAPTURE = G4NDL / "Capture/CrossSection/29_63_Copper.z"

IA_RE = re.compile(r"^IA\s+(ENTR|EXIT)\s+(.*)$")
ID_RE = re.compile(r"^ID\s+(\d+)")
TT_RE = re.compile(r"^TT\s+([-+0-9.eE]+)")
SEED_RE = re.compile(r"^Seed\s+(\d+)")

ENERGY_EDGES_KEV = np.logspace(-9, 9, 181)
EVALUATED_XS_MAX_KEV = 100000.0
ABUNDANCE_63 = 0.6915
ABUNDANCE_65 = 0.3085
EPS_CM = 2.0e-3

def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def world_to_local(x: float, y: float, z: float) -> tuple[float, float, float]:
    c = math.sqrt(0.5)
    s = -math.sqrt(0.5)
    return c * x + s * z, y, -s * x + c * z


def classify_boundary(
    process: str, x: float, y: float, z: float, ux: float, uy: float, uz: float
) -> tuple[str, str, float] | None:
    xl, yl, zl = world_to_local(x, y, z)
    uxl, uyl, uzl = world_to_local(ux, uy, uz)
    radius = math.hypot(xl, yl)

    if process == "ENTR":
        if abs(radius - 29.0) < EPS_CM and -24.5 + EPS_CM < zl < 46.0 - EPS_CM:
            mu = -(xl * uxl + yl * uyl) / radius
            if mu > 0:
                return "outer_input", "side", mu
        if abs(zl + 26.5) < EPS_CM and radius < 29.0 - EPS_CM and uzl > 0:
            return "outer_input", "bottom", uzl
        if abs(zl - 48.0) < EPS_CM and radius < 29.0 - EPS_CM and uzl < 0:
            return "outer_input", "top", -uzl

    if process == "EXIT":
        if abs(radius - 27.0) < EPS_CM and -24.5 + EPS_CM < zl < 46.0 - EPS_CM:
            mu = -(xl * uxl + yl * uyl) / radius
            if mu > 0:
                return "inner_output", "side", mu
        if abs(zl + 24.5) < EPS_CM and radius < 27.0 - EPS_CM and uzl > 0:
            return "inner_output", "bottom", uzl
        if abs(zl - 46.0) < EPS_CM and radius < 27.0 - EPS_CM and uzl < 0:
            return "inner_output", "top", -uzl
    return None


def parse_boundary_ia(line: str) -> dict[str, float | int | str] | None:
    match = IA_RE.match(line)
    if match is None:
        return None
    parts = [part.strip() for part in match.group(2).split(";")]
    if len(parts) < 15:
        return None
    return {
        "process": match.group(1),
        "origin": int(parts[1]),
        "x": float(parts[4]),
        "y": float(parts[5]),
        "z": float(parts[6]),
        "particle": int(parts[7]),
        "ux": float(parts[8]),
        "uy": float(parts[9]),
        "uz": float(parts[10]),
        "energy_keV": float(parts[14]),
    }


def dat_for_sim(path: Path) -> Path:
    suffix = ".inc1.id1.sim.gz"
    return Path(str(path)[: -len(suffix)] + ".dat.inc1.dat")


def parse_one(path_s: str) -> dict:
    path = Path(path_s)
    crossings: dict[str, list[tuple[float, float, str]]] = defaultdict(list)
    counts = Counter()
    paired: list[tuple[float, float]] = []
    first_passage: list[tuple[float, float | None]] = []
    first_outer_energy: float | None = None
    first_inner_energy: float | None = None
    paired_this_event = False
    header_seed = None

    with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            seed_match = SEED_RE.match(line)
            if seed_match:
                header_seed = int(seed_match.group(1))
            if line == "SE":
                if first_outer_energy is not None:
                    first_passage.append((first_outer_energy, first_inner_energy))
                first_outer_energy = None
                first_inner_energy = None
                paired_this_event = False
                continue
            if ID_RE.match(line):
                counts["generated_events"] += 1
                continue
            if not line.startswith("IA ENTR") and not line.startswith("IA EXIT"):
                continue
            ia = parse_boundary_ia(line)
            if ia is None or ia["particle"] != 6:
                continue
            boundary = classify_boundary(
                str(ia["process"]),
                float(ia["x"]),
                float(ia["y"]),
                float(ia["z"]),
                float(ia["ux"]),
                float(ia["uy"]),
                float(ia["uz"]),
            )
            if boundary is None:
                continue
            stage, surface, mu = boundary
            energy = float(ia["energy_keV"])
            crossings[f"all:{stage}"].append((energy, mu, surface))
            if ia["origin"] == 1:
                crossings[f"primary:{stage}"].append((energy, mu, surface))
                if stage == "outer_input" and first_outer_energy is None:
                    first_outer_energy = energy
                    counts["primary_histories_entering_outer_bpe"] += 1
                elif stage == "inner_output" and first_outer_energy is not None and not paired_this_event:
                    paired.append((first_outer_energy, energy))
                    first_inner_energy = energy
                    paired_this_event = True
                    counts["primary_histories_reaching_inner_bpe"] += 1

    if first_outer_energy is not None:
        first_passage.append((first_outer_energy, first_inner_energy))

    dat_path = dat_for_sim(path)
    tt = None
    for line in dat_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = TT_RE.match(line)
        if match:
            tt = float(match.group(1))
            break
    return {
        "sim": rel(path),
        "dat": rel(dat_path),
        "tt_s": tt,
        "header_seed": header_seed,
        "counts": dict(counts),
        "crossings": dict(crossings),
        "paired": paired,
        "first_passage": first_passage,
    }


def parse_isotope_production(path: Path) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    n_products = int(lines[0])
    cursor = 1
    out: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for _ in range(n_products):
        product = lines[cursor].upper()
        cursor += 1
        cursor += 2  # reaction identifier and state flag
        n_points = int(lines[cursor])
        cursor += 1
        values: list[float] = []
        while len(values) < 2 * n_points:
            values.extend(float(value) for value in lines[cursor].split())
            cursor += 1
        array = np.asarray(values[: 2 * n_points], dtype=float).reshape(-1, 2)
        out[product] = (array[:, 0] / 1000.0, array[:, 1])
    return out


def parse_capture(path: Path) -> tuple[np.ndarray, np.ndarray]:
    text = zlib.decompress(path.read_bytes()).decode("utf-8")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    n_points = int(lines[4])
    values: list[float] = []
    for line in lines[5:]:
        values.extend(float(value) for value in line.split())
        if len(values) >= 2 * n_points:
            break
    array = np.asarray(values[: 2 * n_points], dtype=float).reshape(-1, 2)
    return array[:, 0] / 1000.0, array[:, 1]


def interp_xs(table: tuple[np.ndarray, np.ndarray], energy_keV: np.ndarray) -> np.ndarray:
    return np.interp(energy_keV, table[0], table[1], left=0.0, right=0.0)


def effective_xs(
    reaction: str,
    energy_keV: np.ndarray,
    prod63: dict[str, tuple[np.ndarray, np.ndarray]],
    prod65: dict[str, tuple[np.ndarray, np.ndarray]],
    capture63: tuple[np.ndarray, np.ndarray],
) -> np.ndarray:
    if reaction == "Cu64":
        return ABUNDANCE_63 * interp_xs(capture63, energy_keV) + ABUNDANCE_65 * interp_xs(
            prod65["CU64"], energy_keV
        )
    if reaction == "Cu62":
        return ABUNDANCE_63 * interp_xs(prod63["CU62"], energy_keV) + ABUNDANCE_65 * interp_xs(
            prod65["CU62"], energy_keV
        )
    if reaction == "Cu61":
        return ABUNDANCE_63 * interp_xs(prod63["CU61"], energy_keV) + ABUNDANCE_65 * interp_xs(
            prod65["CU61"], energy_keV
        )
    raise ValueError(reaction)


def channel_xs(
    reaction: str,
    channel: str,
    energy_keV: np.ndarray,
    prod63: dict[str, tuple[np.ndarray, np.ndarray]],
    prod65: dict[str, tuple[np.ndarray, np.ndarray]],
    capture63: tuple[np.ndarray, np.ndarray],
) -> np.ndarray:
    if channel == "total":
        result = effective_xs(reaction, energy_keV, prod63, prod65, capture63)
    elif reaction == "Cu64" and channel == "63Cu(n,gamma)":
        result = ABUNDANCE_63 * interp_xs(capture63, energy_keV)
    elif reaction == "Cu64" and channel == "65Cu(n,2n)":
        result = ABUNDANCE_65 * interp_xs(prod65["CU64"], energy_keV)
    elif reaction == "Cu62" and channel == "63Cu(n,2n)":
        result = ABUNDANCE_63 * interp_xs(prod63["CU62"], energy_keV)
    elif reaction == "Cu62" and channel == "65Cu(n,4n)":
        result = ABUNDANCE_65 * interp_xs(prod65["CU62"], energy_keV)
    elif reaction == "Cu61" and channel == "63Cu(n,3n)":
        result = ABUNDANCE_63 * interp_xs(prod63["CU61"], energy_keV)
    elif reaction == "Cu61" and channel == "65Cu(n,5n)":
        result = ABUNDANCE_65 * interp_xs(prod65["CU61"], energy_keV)
    else:
        raise ValueError((reaction, channel))
    return np.where(
        (energy_keV > 0.0) & (energy_keV <= EVALUATED_XS_MAX_KEV), result, 0.0
    )


REACTION_CHANNELS = {
    "Cu61": ("total", "63Cu(n,3n)", "65Cu(n,5n)"),
    "Cu62": ("total", "63Cu(n,2n)", "65Cu(n,4n)"),
    "Cu64": ("total", "63Cu(n,gamma)", "65Cu(n,2n)"),
}


def jackknife_se(values: list[float]) -> float:
    array = np.asarray(values, dtype=float)
    mean = np.mean(array)
    return float(math.sqrt((len(array) - 1) / len(array) * np.sum((array - mean) ** 2)))


def q(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    return float(np.quantile(np.asarray(values, dtype=float), quantile))


def energy_summary(values: list[float]) -> dict:
    array = np.asarray(values, dtype=float)
    if len(array) == 0:
        return {"count": 0}
    return {
        "count": int(len(array)),
        "nonpositive_energy_count": int(np.count_nonzero(array <= 0)),
        "p10_keV": float(np.quantile(array, 0.1)),
        "median_keV": float(np.quantile(array, 0.5)),
        "p90_keV": float(np.quantile(array, 0.9)),
        "thermal_le_0p5eV_fraction": float(np.mean(array <= 5.0e-4)),
        "gt_100keV_fraction": float(np.mean(array > 100.0)),
        "gt_1MeV_fraction": float(np.mean(array > 1000.0)),
        "gt_10MeV_fraction": float(np.mean(array > 10000.0)),
        "gt_11MeV_fraction": float(np.mean(array > 11000.0)),
        "gt_20MeV_fraction": float(np.mean(array > 20000.0)),
        "gt_30MeV_fraction": float(np.mean(array > 30000.0)),
        "gt_39MeV_fraction": float(np.mean(array > 39000.0)),
        "gt_100MeV_fraction": float(np.mean(array > 100000.0)),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sims = sorted(RUN.glob("shard*/bpe_boundary_shard*.inc1.id1.sim.gz"))
    with mp.get_context("fork").Pool(processes=6) as pool:
        parsed = pool.map(parse_one, [str(path) for path in sims])

    total_tt = sum(float(row["tt_s"]) for row in parsed)
    total_events = sum(int(row["counts"].get("generated_events", 0)) for row in parsed)
    if len(sims) != 8 or total_events != 100000:
        raise RuntimeError(f"Expected 8 shards and 100000 events, got {len(sims)} and {total_events}")
    if len({row["header_seed"] for row in parsed}) != len(parsed):
        raise RuntimeError("SIM shards are not independent: duplicate header seed detected")
    combined_crossings: dict[str, list[tuple[float, float, str]]] = defaultdict(list)
    paired: list[tuple[float, float]] = []
    first_passage: list[tuple[float, float | None]] = []
    total_counts = Counter()
    for row in parsed:
        total_counts.update(row["counts"])
        paired.extend(row["paired"])
        first_passage.extend(row["first_passage"])
        for key, values in row["crossings"].items():
            combined_crossings[key].extend(values)

    spectrum_rows: list[dict] = []
    for population in ("primary", "all"):
        for stage in ("outer_input", "inner_output"):
            values = combined_crossings[f"{population}:{stage}"]
            energies = np.asarray([value[0] for value in values], dtype=float)
            hist, _ = np.histogram(energies, bins=ENERGY_EDGES_KEV)
            for index, count in enumerate(hist):
                spectrum_rows.append(
                    {
                        "population": population,
                        "stage": stage,
                        "energy_lo_keV": ENERGY_EDGES_KEV[index],
                        "energy_hi_keV": ENERGY_EDGES_KEV[index + 1],
                        "crossings": int(count),
                        "crossing_rate_s-1": float(count / total_tt),
                    }
                )
    with (OUT / "boundary_spectrum.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(spectrum_rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(spectrum_rows)

    prod63 = parse_isotope_production(CU63_PROD)
    prod65 = parse_isotope_production(CU65_PROD)
    capture63 = parse_capture(CU63_CAPTURE)
    fold_rows: list[dict] = []
    for population in ("primary", "all"):
        for stage in ("outer_input", "inner_output"):
            values = combined_crossings[f"{population}:{stage}"]
            energies = np.asarray([value[0] for value in values], dtype=float)
            mus = np.asarray([value[1] for value in values], dtype=float)
            for reaction, channels in REACTION_CHANNELS.items():
                for channel in channels:
                    sigma = channel_xs(reaction, channel, energies, prod63, prod65, capture63)
                    fold_rows.append(
                        {
                            "population": population,
                            "stage": stage,
                            "reaction_product": reaction,
                            "reaction_channel": channel,
                            "crossings": len(values),
                            "sum_sigma_b": float(np.sum(sigma)),
                            "evaluated_le100MeV_current_index_b_s-1": float(
                                np.sum(sigma) / total_tt
                            ),
                            "evaluated_le100MeV_surface_scalar_flux_proxy_b_s-1": float(
                                np.sum(sigma / mus) / total_tt
                            ),
                        }
                    )

    fold_lookup = {
        (row["population"], row["stage"], row["reaction_product"], row["reaction_channel"]): row
        for row in fold_rows
    }
    ratio_rows: list[dict] = []
    for population in ("primary", "all"):
        for reaction, channels in REACTION_CHANNELS.items():
            for channel in channels:
                before = fold_lookup[(population, "outer_input", reaction, channel)]
                after = fold_lookup[(population, "inner_output", reaction, channel)]
                if before["evaluated_le100MeV_current_index_b_s-1"] == 0:
                    continue
                shard_current_in = []
                shard_current_out = []
                shard_flux_in = []
                shard_flux_out = []
                for parsed_row in parsed:
                    for stage, current_target, flux_target in (
                        ("outer_input", shard_current_in, shard_flux_in),
                        ("inner_output", shard_current_out, shard_flux_out),
                    ):
                        shard_values = parsed_row["crossings"].get(f"{population}:{stage}", [])
                        shard_e = np.asarray([value[0] for value in shard_values], dtype=float)
                        shard_mu = np.asarray([value[1] for value in shard_values], dtype=float)
                        shard_sigma = channel_xs(
                            reaction, channel, shard_e, prod63, prod65, capture63
                        )
                        current_target.append(float(np.sum(shard_sigma)))
                        flux_target.append(float(np.sum(shard_sigma / shard_mu)))
                current_in_total = sum(shard_current_in)
                current_out_total = sum(shard_current_out)
                flux_in_total = sum(shard_flux_in)
                flux_out_total = sum(shard_flux_out)
                current_loo = [
                    (current_out_total - shard_current_out[i])
                    / (current_in_total - shard_current_in[i])
                    for i in range(len(parsed))
                ]
                flux_loo = [
                    (flux_out_total - shard_flux_out[i]) / (flux_in_total - shard_flux_in[i])
                    for i in range(len(parsed))
                ]
                ratio_rows.append(
                    {
                        "population": population,
                        "reaction_product": reaction,
                        "reaction_channel": channel,
                        "output_over_input_evaluated_le100MeV_current_index": after[
                            "evaluated_le100MeV_current_index_b_s-1"
                        ]
                        / before["evaluated_le100MeV_current_index_b_s-1"],
                        "current_ratio_jackknife_se": jackknife_se(current_loo),
                        "output_over_input_evaluated_le100MeV_flux_proxy": after[
                            "evaluated_le100MeV_surface_scalar_flux_proxy_b_s-1"
                        ]
                        / before["evaluated_le100MeV_surface_scalar_flux_proxy_b_s-1"],
                        "flux_proxy_ratio_jackknife_se": jackknife_se(flux_loo),
                    }
                )
    with (OUT / "cu_reaction_fold.csv").open("w", encoding="utf-8", newline="") as handle:
        rows = fold_rows + ratio_rows
        fields = sorted({key for row in rows for key in row})
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    paired_in = [value[0] for value in paired]
    paired_out = [value[1] for value in paired]
    paired_ratio = [out / inc for inc, out in paired if inc > 0]
    all_first_in = [value[0] for value in first_passage]
    input_bins = (
        ("thermal_le_0p5eV", 0.0, 5.0e-4),
        ("0p5eV_to_100keV", 5.0e-4, 100.0),
        ("100keV_to_1MeV", 100.0, 1000.0),
        ("1_to_10MeV", 1000.0, 10000.0),
        ("10_to_20MeV", 10000.0, 20000.0),
        ("20_to_39MeV", 20000.0, 39000.0),
        ("ge_39MeV", 39000.0, math.inf),
    )
    transmission_by_input_energy = {}
    for label, lo, hi in input_bins:
        selected = [row for row in first_passage if lo <= row[0] < hi]
        reached = sum(row[1] is not None for row in selected)
        transmission_by_input_energy[label] = {
            "entered_histories": len(selected),
            "inner_reached_histories": reached,
            "conditional_transmission_fraction": reached / len(selected) if selected else None,
        }
    crossing_summary = {}
    for population in ("primary", "all"):
        crossing_summary[population] = {}
        for stage in ("outer_input", "inner_output"):
            values = combined_crossings[f"{population}:{stage}"]
            energies = [value[0] for value in values]
            surfaces = Counter(value[2] for value in values)
            crossing_summary[population][stage] = {
                **energy_summary(energies),
                "crossing_rate_s-1": len(values) / total_tt,
                "surface_counts": dict(surfaces),
            }

    ratios = {
        row["reaction_product"]: row[
            "output_over_input_evaluated_le100MeV_current_index"
        ]
        for row in ratio_rows
        if row["population"] == "all" and row["reaction_channel"] == "total"
    }
    channel_ratios = {
        f"{row['reaction_product']}::{row['reaction_channel']}": {
            "current_ratio": row["output_over_input_evaluated_le100MeV_current_index"],
            "current_ratio_jackknife_se": row["current_ratio_jackknife_se"],
            "flux_proxy_ratio": row["output_over_input_evaluated_le100MeV_flux_proxy"],
            "flux_proxy_ratio_jackknife_se": row["flux_proxy_ratio_jackknife_se"],
        }
        for row in ratio_rows
        if row["population"] == "all"
    }
    summary = {
        "status": "PASS__CORRECTED_NEUTRON_BPE_BOUNDARY_DIAGNOSTIC",
        "authority": {
            "role": "non_mergeable_boundary_diagnostic",
            "run": rel(RUN),
            "analysis_code": rel(Path(__file__)),
            "source_cards": rel(PACKAGE / "source_cards/attempt04"),
            "source_contract": (
                "engineering/particle_source_unit_repair_20260811/data/"
                "source_contract_manifest.json"
            ),
            "geometry_setup": (
                "engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/"
                "geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
            ),
            "workers": 6,
            "events_per_shard": 12500,
            "cli_seeds": [88813200 + index for index in range(1, 9)],
            "store_text_scientific_precision": 9,
            "watched_volumes": [
                "GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm",
                "GeoOpt_S2B_CryoShell_BPE5_BottomCap_20mm",
                "GeoOpt_S2B_CryoShell_BPE5_TopCap_20mm",
            ],
            "supersedes": (
                "production_attempt03, whose six simultaneous jobs shared one default time seed and "
                "whose final two shared another; attempt03 is excluded from every result."
            ),
        },
        "generated_events": total_events,
        "total_TT_s": total_tt,
        "shards": [
            {
                "sim": row["sim"],
                "dat": row["dat"],
                "tt_s": row["tt_s"],
                "header_seed": row["header_seed"],
                "counts": row["counts"],
            }
            for row in parsed
        ],
        "crossings": crossing_summary,
        "primary_first_passage": {
            "outer_entry_histories": int(total_counts["primary_histories_entering_outer_bpe"]),
            "inner_reached_histories": int(total_counts["primary_histories_reaching_inner_bpe"]),
            "conditional_transmission_fraction": total_counts["primary_histories_reaching_inner_bpe"]
            / total_counts["primary_histories_entering_outer_bpe"],
            "all_entering_input_energy": energy_summary(all_first_in),
            "transmitted_input_energy": energy_summary(paired_in),
            "transmitted_output_energy": energy_summary(paired_out),
            "Eout_over_Ein_p10": q(paired_ratio, 0.1),
            "Eout_over_Ein_median": q(paired_ratio, 0.5),
            "Eout_over_Ein_p90": q(paired_ratio, 0.9),
            "fraction_Eout_lt_0p9_Ein": float(np.mean(np.asarray(paired_ratio) < 0.9)),
            "fraction_Eout_lt_0p1_Ein": float(np.mean(np.asarray(paired_ratio) < 0.1)),
            "fraction_Eout_lt_Ein": float(np.mean(np.asarray(paired_ratio) < 1.0 - 1.0e-9)),
            "fraction_Eout_equal_Ein_within_1ppm": float(
                np.mean(np.abs(np.asarray(paired_ratio) - 1.0) <= 1.0e-6)
            ),
            "transmission_by_input_energy": transmission_by_input_energy,
        },
        "cu_reaction_evaluated_le100MeV_current_index_output_over_input": ratios,
        "cu_reaction_channel_output_over_input": channel_ratios,
        "cross_section_sources": {
            "Cu63_isotope_production": str(CU63_PROD),
            "Cu65_isotope_production": str(CU65_PROD),
            "Cu63_capture": str(CU63_CAPTURE),
            "energy_unit": "keV after conversion from G4NDL eV",
            "cross_section_unit": "barn",
            "evaluated_range_note": (
                "All Cu reaction indices use the common evaluated interval 0<E<=100 MeV. "
                "Higher-energy crossings are reported in the spectra but excluded from the fold."
            ),
        },
        "scope": (
            "Conditional transport through the three nominal BPE bodies. First passage means first nominal outer "
            "inward contact to the first later nominal inner arrival and can include reflection/re-entry. "
            "Relief/opening bypasses are not counted. "
            "The Cu fold diagnoses direct neutron activation; secondary hadronic cascades and the final no-BPE "
            "geometry require a matched buildup comparison."
        ),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    centers = np.sqrt(ENERGY_EDGES_KEV[:-1] * ENERGY_EDGES_KEV[1:])
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    for stage, label, color in (
        ("outer_input", "Entering BPE outer surface", "#64748b"),
        ("inner_output", "Leaving BPE toward interior", "#2563eb"),
    ):
        values = np.asarray([v[0] for v in combined_crossings[f"all:{stage}"]])
        hist, _ = np.histogram(values, bins=ENERGY_EDGES_KEV)
        axes[0].step(centers, hist / total_tt, where="mid", label=label, color=color)
    axes[0].set_xscale("log")
    axes[0].set_yscale("log")
    axes[0].set_xlabel("Neutron kinetic energy (keV)")
    axes[0].set_ylabel("Boundary-crossing rate / bin (s$^{-1}$)")
    axes[0].legend(frameon=False)
    axes[0].grid(alpha=0.25)

    names = ["Cu61", "Cu62", "Cu64"]
    values = [ratios[name] for name in names]
    errors = [
        channel_ratios[f"{name}::total"]["current_ratio_jackknife_se"] for name in names
    ]
    axes[1].bar(
        names,
        values,
        yerr=errors,
        capsize=4,
        color=["#7c3aed", "#a855f7", "#2563eb"],
    )
    axes[1].axhline(1.0, color="black", lw=1)
    axes[1].set_ylabel("BPE output / input Cu reaction-current index")
    axes[1].grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT / "bpe_boundary_spectrum_cu_fold.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
