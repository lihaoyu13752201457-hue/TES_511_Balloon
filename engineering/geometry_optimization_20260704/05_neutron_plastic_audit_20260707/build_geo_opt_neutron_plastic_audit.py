#!/usr/bin/env python3
"""Audit BPE neutron activation and geo-opt plastic-skin veto effect.

This is a post-processing audit only. It reads existing Mass_model_511 and
geo-opt full-stat products, then replays Step05 with a counterfactual active
veto definition that disables only the GeoOpt plastic skin.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
import math
import multiprocessing as mp
import pickle
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
PKG = ROOT / "engineering/geometry_optimization_20260704"
WORK = PKG / "05_neutron_plastic_audit_20260707"
FIG = WORK / "figures"

GEO_LABEL = "geo_opt_s1_bpe_w5_fullstat_v1"
MASS_LABEL = "candidate_Mass_model_511_fullstat_v1"

GEO_RUN = ROOT / "runs/geometry_optimization_20260704"
MASS_RUN = ROOT / "runs/Mass_model_511_nearfield_migration_20260701"

GEO_BUILDUP = GEO_RUN / "step02_buildup_geo_opt_s1_bpe_w5_fullstat_v1"
MASS_BUILDUP = MASS_RUN / "step02_buildup_candidate_Mass_model_511_fullstat_v1"
GEO_PROMPT = GEO_RUN / "step02_instant_geo_opt_s1_bpe_w5_fullstat_v1"
GEO_DELAYED_SIM = GEO_RUN / "step02_delayed_transport_geo_opt_s1_bpe_w5_fullstat_v1" / "DelayedDecayGeoOptS1BpeW5FullstatV1.inc1.id1.sim.gz"

GEO_INV = GEO_RUN / "step02_decay_source_geo_opt_s1_bpe_w5_fullstat_v1" / "activation_inventory_day15.csv"
MASS_INV = MASS_RUN / "step02_decay_source_candidate_Mass_model_511_fullstat_v1" / "activation_inventory_day15.csv"
GEO_GS = GEO_RUN / "step02_delay_fix_geo_opt_s1_bpe_w5_fullstat_v1" / "groundstate_activity_corrections.csv"
MASS_GS = MASS_RUN / "step02_delay_fix_candidate_Mass_model_511_fullstat_v1" / "groundstate_activity_corrections.csv"

GEO_STEP05_WRAPPER = PKG / "03_step05_detector_response_20260706" / "run_geo_opt_step05_response.py"
GEO_STEP05_ON_OUT = ROOT / "stepwise_maintenance/step05_veto_time_axis/outputs_geo_opt_s1_bpe_w5_fullstat_v1_l1"
PLASTIC_OFF_OUT = WORK / "work" / "step05_plastic_off_catalog"

ACTIVE_VETO_THRESHOLD_KEV = 50.0
COINCIDENCE_WINDOW_S = 1.0e-6
MAX_TIMELINE_DRAW_LAMBDA = 5_000_000.0
GEO_OPT_OUTER_PLASTIC_RADIUS_CM = 27.9
NEUTRON_DEPTH_EDGES = np.linspace(0.0, 35.0, 71)
NEUTRON_LOGE_EDGES = np.linspace(-6.0, 8.0, 71)

CC_HIT_RE = re.compile(r"^CC\s+HIT\s+(\S+)\s+(.*)$")
KV_RE = re.compile(r"(\w+)=([^\s]+)")
ID_RE = re.compile(r"^ID\s+(\d+)")
EC_RE = re.compile(r"^EC\s+([-+0-9.eE]+)")
IP_RE = re.compile(
    r"^CC\s+IP\s+(?P<proc>\S+)\s+(?P<vn>\S+)\s+"
    r"(?P<x>[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s+"
    r"(?P<y>[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s+"
    r"(?P<z>[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s+"
    r"(?P<za>\d+)\s+(?P<exc>[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s+"
    r"(?P<t>[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"
    r"(?:\s+.*)?$"
)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="", errors="ignore") as fh:
        return list(csv.DictReader(fh))


def save_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def volume_category(vn: str) -> str:
    name = str(vn)
    upper = name.upper()
    if name.startswith("GeoOpt_S1_PlasticFullWrap"):
        return "geoopt_plastic_skin"
    if name.startswith("GeoOpt_BPE"):
        return "geoopt_bpe"
    if name.startswith("GeoOpt_W"):
        return "geoopt_w_baffle"
    if name.startswith("GeoOpt_"):
        return "geoopt_other_added"
    if upper.startswith("CSI_"):
        return "csi"
    if upper.startswith("TP_") or upper.startswith("TES_"):
        return "tes"
    if "WINDOW" in upper:
        return "window"
    if "COLDPLATE" in upper:
        return "cold_plates"
    if "VACUUM_JACKET" in upper or "OUTER_" in upper or "OUTERSUPPORT" in upper:
        return "outer_mechanics"
    if "W_" in upper or "TUNGSTEN" in upper or name.startswith("Passive_W"):
        return "passive_w_or_collimator"
    if "COLL" in upper or "XS400" in upper:
        return "passive_w_or_collimator"
    return "other_internal"


def is_added_geoopt_layer(vn: str) -> bool:
    return str(vn).startswith("GeoOpt_")


def load_groundstate_activity(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_csv(path):
        try:
            new_a = float(row.get("new_groundstate_activity_Bq", "0") or 0.0)
            old_a = float(row.get("old_source_activity_Bq", "0") or 0.0)
        except ValueError:
            continue
        action = row.get("action", "")
        if action.startswith("removed"):
            new_a = 0.0
        vn = row["VN"]
        rows.append(
            {
                "VN": vn,
                "ZA": int(row["ZA"]),
                "nuclide": row.get("nuclide", ""),
                "activity_Bq": new_a,
                "old_activity_Bq": old_a,
                "RP_yield": float(row.get("RP_yield", "0") or 0.0),
                "category": volume_category(vn),
                "is_internal": not is_added_geoopt_layer(vn),
            }
        )
    return rows


def sum_activity(rows: list[dict[str, Any]], predicate=lambda r: True) -> float:
    return float(sum(float(r["activity_Bq"]) for r in rows if predicate(r)))


def compare_value(name: str, mass: float, geo: float) -> dict[str, Any]:
    return {
        "metric": name,
        "mass_model_Bq": f"{mass:.12g}",
        "geo_opt_Bq": f"{geo:.12g}",
        "geo_minus_mass_Bq": f"{geo - mass:.12g}",
        "geo_over_mass": "" if mass == 0 else f"{geo / mass:.12g}",
        "relative_change_percent": "" if mass == 0 else f"{100.0 * (geo / mass - 1.0):.9g}",
    }


def build_activation_audit() -> dict[str, Any]:
    geo_rows = load_groundstate_activity(GEO_GS)
    mass_rows = load_groundstate_activity(MASS_GS)

    geo_by_vn = defaultdict(float)
    mass_by_vn = defaultdict(float)
    for row in geo_rows:
        geo_by_vn[row["VN"]] += float(row["activity_Bq"])
    for row in mass_rows:
        mass_by_vn[row["VN"]] += float(row["activity_Bq"])

    common_vn = set(k for k, v in geo_by_vn.items() if v > 0 and not is_added_geoopt_layer(k)) & set(
        k for k, v in mass_by_vn.items() if v > 0
    )
    categories = sorted(set(row["category"] for row in geo_rows + mass_rows))
    category_rows: list[dict[str, Any]] = []
    category_rows.append(compare_value("fixed_total_activity", sum_activity(mass_rows), sum_activity(geo_rows)))
    category_rows.append(
        compare_value(
            "internal_activity_excluding_geoopt_added_layers",
            sum_activity(mass_rows),
            sum_activity(geo_rows, lambda r: bool(r["is_internal"])),
        )
    )
    category_rows.append(
        compare_value(
            "geoopt_added_layers_activity",
            0.0,
            sum_activity(geo_rows, lambda r: not bool(r["is_internal"])),
        )
    )
    category_rows.append(
        compare_value(
            "CsI_activity",
            sum_activity(mass_rows, lambda r: r["category"] == "csi"),
            sum_activity(geo_rows, lambda r: r["category"] == "csi"),
        )
    )
    category_rows.append(
        compare_value(
            "common_internal_volume_names_activity",
            float(sum(mass_by_vn[vn] for vn in common_vn)),
            float(sum(geo_by_vn[vn] for vn in common_vn)),
        )
    )
    for cat in categories:
        category_rows.append(
            compare_value(
                f"category:{cat}",
                sum_activity(mass_rows, lambda r, c=cat: r["category"] == c),
                sum_activity(geo_rows, lambda r, c=cat: r["category"] == c),
            )
        )

    save_csv(
        WORK / "activation_category_comparison_groundstate_fixed.csv",
        category_rows,
        ["metric", "mass_model_Bq", "geo_opt_Bq", "geo_minus_mass_Bq", "geo_over_mass", "relative_change_percent"],
    )

    top_vns = set()
    for mapping in (geo_by_vn, mass_by_vn):
        for vn, _ in sorted(mapping.items(), key=lambda kv: kv[1], reverse=True)[:30]:
            top_vns.add(vn)
    top_rows = []
    for vn in sorted(top_vns, key=lambda x: max(geo_by_vn.get(x, 0.0), mass_by_vn.get(x, 0.0)), reverse=True):
        mass = mass_by_vn.get(vn, 0.0)
        geo = geo_by_vn.get(vn, 0.0)
        top_rows.append(
            {
                "VN": vn,
                "category": volume_category(vn),
                "mass_model_Bq": f"{mass:.12g}",
                "geo_opt_Bq": f"{geo:.12g}",
                "geo_minus_mass_Bq": f"{geo - mass:.12g}",
                "geo_over_mass": "" if mass == 0 else f"{geo / mass:.12g}",
                "relative_change_percent": "" if mass == 0 else f"{100.0 * (geo / mass - 1.0):.9g}",
            }
        )
    save_csv(
        WORK / "activation_top_volume_comparison_groundstate_fixed.csv",
        top_rows,
        ["VN", "category", "mass_model_Bq", "geo_opt_Bq", "geo_minus_mass_Bq", "geo_over_mass", "relative_change_percent"],
    )

    geo_by_nuclide = defaultdict(float)
    mass_by_nuclide = defaultdict(float)
    for row in geo_rows:
        geo_by_nuclide[row["nuclide"]] += float(row["activity_Bq"])
    for row in mass_rows:
        mass_by_nuclide[row["nuclide"]] += float(row["activity_Bq"])
    top_nuclides = set()
    for mapping in (geo_by_nuclide, mass_by_nuclide):
        for nu, _ in sorted(mapping.items(), key=lambda kv: kv[1], reverse=True)[:30]:
            top_nuclides.add(nu)
    nuc_rows = []
    for nu in sorted(top_nuclides, key=lambda x: max(geo_by_nuclide.get(x, 0.0), mass_by_nuclide.get(x, 0.0)), reverse=True):
        mass = mass_by_nuclide.get(nu, 0.0)
        geo = geo_by_nuclide.get(nu, 0.0)
        nuc_rows.append(
            {
                "nuclide": nu,
                "mass_model_Bq": f"{mass:.12g}",
                "geo_opt_Bq": f"{geo:.12g}",
                "geo_minus_mass_Bq": f"{geo - mass:.12g}",
                "geo_over_mass": "" if mass == 0 else f"{geo / mass:.12g}",
                "relative_change_percent": "" if mass == 0 else f"{100.0 * (geo / mass - 1.0):.9g}",
            }
        )
    save_csv(
        WORK / "activation_top_nuclide_comparison_groundstate_fixed.csv",
        nuc_rows,
        ["nuclide", "mass_model_Bq", "geo_opt_Bq", "geo_minus_mass_Bq", "geo_over_mass", "relative_change_percent"],
    )

    return {
        "inputs": {
            "geo_groundstate_corrections": rel(GEO_GS),
            "mass_groundstate_corrections": rel(MASS_GS),
            "geo_inventory_raw": rel(GEO_INV),
            "mass_inventory_raw": rel(MASS_INV),
        },
        "summary": {
            "mass_fixed_total_activity_Bq": sum_activity(mass_rows),
            "geo_fixed_total_activity_Bq": sum_activity(geo_rows),
            "geo_internal_excluding_added_layers_Bq": sum_activity(geo_rows, lambda r: bool(r["is_internal"])),
            "mass_internal_Bq": sum_activity(mass_rows),
            "geo_added_layers_Bq": sum_activity(geo_rows, lambda r: not bool(r["is_internal"])),
            "mass_CsI_Bq": sum_activity(mass_rows, lambda r: r["category"] == "csi"),
            "geo_CsI_Bq": sum_activity(geo_rows, lambda r: r["category"] == "csi"),
            "common_internal_volume_names_count": len(common_vn),
            "mass_common_internal_volume_names_Bq": float(sum(mass_by_vn[vn] for vn in common_vn)),
            "geo_common_internal_volume_names_Bq": float(sum(geo_by_vn[vn] for vn in common_vn)),
        },
        "tables": {
            "category_comparison": rel(WORK / "activation_category_comparison_groundstate_fixed.csv"),
            "top_volume_comparison": rel(WORK / "activation_top_volume_comparison_groundstate_fixed.csv"),
            "top_nuclide_comparison": rel(WORK / "activation_top_nuclide_comparison_groundstate_fixed.csv"),
        },
    }


def open_text(path: Path):
    return gzip.open(path, "rt", encoding="utf-8", errors="ignore") if str(path).endswith(".gz") else path.open(
        "r", encoding="utf-8", errors="ignore"
    )


def parse_one_neutron_file(args_tuple):
    label, path_s, nfiles, sample_cap, depth_edges, loge_edges = args_tuple
    path = Path(path_s)
    weight = 1.0 / max(1, int(nfiles))
    depth_edges = np.asarray(depth_edges, dtype=float)
    loge_edges = np.asarray(loge_edges, dtype=float)
    counters = Counter()
    by_category = Counter()
    weighted_by_category = defaultdict(float)
    hist_w = np.zeros((len(depth_edges) - 1, len(loge_edges) - 1), dtype=float)
    hist_n = np.zeros_like(hist_w)
    samples: list[dict[str, Any]] = []
    rng = np.random.default_rng(260707 + sum(ord(ch) for ch in str(path)))
    seen_points = 0

    cur_id: int | None = None
    cur_ec: float | None = None
    with open_text(path) as fh:
        for raw in fh:
            line = raw.strip()
            m_id = ID_RE.match(line)
            if m_id:
                cur_id = int(m_id.group(1))
                counters["events"] += 1
                cur_ec = None
                continue
            m_ec = EC_RE.match(line)
            if m_ec:
                try:
                    cur_ec = float(m_ec.group(1))
                except ValueError:
                    cur_ec = None
                continue
            if not line.startswith("CC IP RP"):
                continue
            m = IP_RE.match(line)
            if not m or cur_ec is None or cur_ec <= 0:
                counters["rpip_unparsed_or_no_energy"] += 1
                continue
            vn = m.group("vn")
            x = float(m.group("x"))
            y = float(m.group("y"))
            z = float(m.group("z"))
            r = math.sqrt(x * x + y * y)
            depth = max(0.0, GEO_OPT_OUTER_PLASTIC_RADIUS_CM - r)
            loge = math.log10(cur_ec)
            cat = volume_category(vn)
            counters["rpip_points"] += 1
            by_category[cat] += 1
            weighted_by_category[cat] += weight

            ix = int(np.searchsorted(depth_edges, depth, side="right") - 1)
            iy = int(np.searchsorted(loge_edges, loge, side="right") - 1)
            if 0 <= ix < hist_w.shape[0] and 0 <= iy < hist_w.shape[1]:
                hist_w[ix, iy] += weight
                hist_n[ix, iy] += 1.0
            else:
                counters["rpip_outside_plot_range"] += 1

            row = {
                "dataset": label,
                "source_file": rel(path),
                "event_id": cur_id,
                "primary_energy_keV": cur_ec,
                "log10_primary_energy_keV": loge,
                "depth_from_geoopt_outer_radius_cm": depth,
                "r_cm": r,
                "z_cm": z,
                "VN": vn,
                "category": cat,
                "ZA": int(m.group("za")),
                "exc_keV": float(m.group("exc")),
                "weight": weight,
            }
            seen_points += 1
            if len(samples) < sample_cap:
                samples.append(row)
            else:
                j = int(rng.integers(0, seen_points))
                if j < sample_cap:
                    samples[j] = row

    return {
        "label": label,
        "file": rel(path),
        "hist_w": hist_w,
        "hist_n": hist_n,
        "samples": samples,
        "counters": dict(counters),
        "rpip_points_by_category": dict(sorted(by_category.items())),
        "weighted_rpip_points_by_category": {k: float(v) for k, v in sorted(weighted_by_category.items())},
    }


def parse_neutron_rpip_points(label: str, directory: Path, workers: int) -> dict[str, Any]:
    files = sorted(directory.glob("Background_n_fullsphere20*.sim.gz"))
    if not files:
        raise FileNotFoundError(directory)
    sample_cap_per_file = 700
    tasks = [
        (
            label,
            str(path),
            len(files),
            sample_cap_per_file,
            NEUTRON_DEPTH_EDGES.tolist(),
            NEUTRON_LOGE_EDGES.tolist(),
        )
        for path in files
    ]
    if workers > 1 and len(tasks) > 1:
        ctx = mp.get_context("fork") if sys.platform.startswith("linux") else mp.get_context("spawn")
        with ctx.Pool(processes=min(workers, len(tasks))) as pool:
            results = list(pool.imap_unordered(parse_one_neutron_file, tasks, chunksize=1))
    else:
        results = [parse_one_neutron_file(task) for task in tasks]

    counters = Counter()
    by_category = Counter()
    weighted_by_category = defaultdict(float)
    hist_w = np.zeros((len(NEUTRON_DEPTH_EDGES) - 1, len(NEUTRON_LOGE_EDGES) - 1), dtype=float)
    hist_n = np.zeros_like(hist_w)
    samples: list[dict[str, Any]] = []
    for result in results:
        counters.update(result["counters"])
        by_category.update(result["rpip_points_by_category"])
        for key, value in result["weighted_rpip_points_by_category"].items():
            weighted_by_category[key] += float(value)
        hist_w += np.asarray(result["hist_w"], dtype=float)
        hist_n += np.asarray(result["hist_n"], dtype=float)
        samples.extend(result["samples"])
    return {
        "label": label,
        "files": [rel(p) for p in files],
        "hist_w": hist_w,
        "hist_n": hist_n,
        "samples": samples,
        "counters": dict(counters),
        "rpip_points_by_category": dict(sorted(by_category.items())),
        "weighted_rpip_points_by_category": {k: float(v) for k, v in sorted(weighted_by_category.items())},
    }


def build_neutron_energy_depth_plot(workers: int) -> dict[str, Any]:
    FIG.mkdir(parents=True, exist_ok=True)
    geo = parse_neutron_rpip_points("geo_opt_s1_bpe_w5", GEO_BUILDUP, workers=workers)
    mass = parse_neutron_rpip_points("Mass_model_511", MASS_BUILDUP, workers=workers)
    if geo["counters"].get("rpip_points", 0) + mass["counters"].get("rpip_points", 0) <= 0:
        raise RuntimeError("No neutron CC IP RP points parsed")

    binned_rows: list[dict[str, Any]] = []
    for label, obj in (("geo_opt_s1_bpe_w5", geo), ("Mass_model_511", mass)):
        hist_w = np.asarray(obj["hist_w"], dtype=float)
        hist_n = np.asarray(obj["hist_n"], dtype=float)
        for i in range(hist_w.shape[0]):
            for j in range(hist_w.shape[1]):
                if hist_n[i, j] <= 0:
                    continue
                binned_rows.append(
                    {
                        "dataset": label,
                        "depth_bin_lo_cm": f"{NEUTRON_DEPTH_EDGES[i]:.6g}",
                        "depth_bin_hi_cm": f"{NEUTRON_DEPTH_EDGES[i + 1]:.6g}",
                        "log10_energy_bin_lo_keV": f"{NEUTRON_LOGE_EDGES[j]:.6g}",
                        "log10_energy_bin_hi_keV": f"{NEUTRON_LOGE_EDGES[j + 1]:.6g}",
                        "weighted_rpip_points": f"{hist_w[i, j]:.12g}",
                        "raw_rpip_points": int(hist_n[i, j]),
                    }
                )
    save_csv(
        WORK / "neutron_energy_depth_binned.csv",
        binned_rows,
        [
            "dataset",
            "depth_bin_lo_cm",
            "depth_bin_hi_cm",
            "log10_energy_bin_lo_keV",
            "log10_energy_bin_hi_keV",
            "weighted_rpip_points",
            "raw_rpip_points",
        ],
    )

    sample_rows = []
    for label, obj in (("geo_opt_s1_bpe_w5", geo), ("Mass_model_511", mass)):
        for p in obj["samples"]:
            sample_rows.append(
                {
                    "dataset": label,
                    "event_id": p["event_id"],
                    "primary_energy_keV": f"{p['primary_energy_keV']:.12g}",
                    "depth_from_geoopt_outer_radius_cm": f"{p['depth_from_geoopt_outer_radius_cm']:.12g}",
                    "r_cm": f"{p['r_cm']:.12g}",
                    "z_cm": f"{p['z_cm']:.12g}",
                    "VN": p["VN"],
                    "category": p["category"],
                    "weight": f"{p['weight']:.12g}",
                }
            )
    save_csv(
        WORK / "neutron_energy_depth_points_sample.csv",
        sample_rows,
        ["dataset", "event_id", "primary_energy_keV", "depth_from_geoopt_outer_radius_cm", "r_cm", "z_cm", "VN", "category", "weight"],
    )

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharex=True, sharey=True)
    for ax, label, obj in zip(axes, ["geo-opt S1/BPE/W5", "Mass_model_511"], [geo, mass]):
        hist = np.asarray(obj["hist_w"], dtype=float).T
        masked = np.ma.masked_where(hist <= 0, hist)
        mesh = ax.pcolormesh(NEUTRON_DEPTH_EDGES, NEUTRON_LOGE_EDGES, masked, cmap="viridis", shading="auto")
        fig.colorbar(mesh, ax=ax, label="weighted RPIP points/bin")
        ax.set_title(label)
        ax.set_xlabel("radial depth proxy from geo-opt outer plastic radius (cm)")
        ax.grid(True, alpha=0.25)
    axes[0].set_ylabel("primary neutron energy (keV)")
    ticks = np.arange(int(NEUTRON_LOGE_EDGES[0]), int(NEUTRON_LOGE_EDGES[-1]) + 1)
    axes[0].set_yticks(ticks)
    axes[0].set_yticklabels([f"1e{int(t)}" for t in ticks])
    fig.suptitle("Neutron primary energy vs activation production depth (CC IP RP)")
    fig.tight_layout()
    png = FIG / "neutron_energy_depth_hexbin.png"
    fig.savefig(png, dpi=180)
    plt.close(fig)

    def point_summary(obj: dict[str, Any]) -> dict[str, Any]:
        samples = obj["samples"]
        if not samples:
            return {"raw_rpip_points": 0}
        depths = np.asarray([p["depth_from_geoopt_outer_radius_cm"] for p in samples], dtype=float)
        energies = np.asarray([p["primary_energy_keV"] for p in samples], dtype=float)
        by_cat = obj["weighted_rpip_points_by_category"]
        internal = float(
            sum(
                value
                for key, value in by_cat.items()
                if key not in ("geoopt_plastic_skin", "geoopt_bpe", "geoopt_w_baffle", "geoopt_other_added")
            )
        )
        return {
            "raw_rpip_points": int(obj["counters"].get("rpip_points", 0)),
            "weighted_rpip_points": float(sum(by_cat.values())),
            "weighted_internal_rpip_points": internal,
            "weighted_CsI_rpip_points": float(by_cat.get("csi", 0.0)),
            "sample_size_for_quantiles": int(len(samples)),
            "sample_median_depth_cm": float(np.median(depths)),
            "sample_median_primary_energy_keV": float(np.median(energies)),
            "sample_p90_primary_energy_keV": float(np.percentile(energies, 90)),
        }

    return {
        "inputs": {
            "geo_buildup_dir": rel(GEO_BUILDUP),
            "mass_buildup_dir": rel(MASS_BUILDUP),
            "selection": "Background_n_fullsphere20*.sim.gz, CC IP RP rows only",
            "depth_definition": f"max(0, {GEO_OPT_OUTER_PLASTIC_RADIUS_CM} cm - sqrt(x^2+y^2)); x/y from CC IP RP in cm",
            "energy_definition": "event EC value from the same neutron SIM event, interpreted as primary neutron energy in keV",
        },
        "summary": {
            "geo": point_summary(geo),
            "mass": point_summary(mass),
            "geo_rpip_points_by_category": geo["weighted_rpip_points_by_category"],
            "mass_rpip_points_by_category": mass["weighted_rpip_points_by_category"],
        },
        "outputs": {
            "plot": rel(png),
            "binned_csv": rel(WORK / "neutron_energy_depth_binned.csv"),
            "sample_points_csv": rel(WORK / "neutron_energy_depth_points_sample.csv"),
        },
    }


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def legacy_active_veto_no_geoopt_plastic(vol: str) -> bool:
    upper = str(vol).upper()
    return upper.startswith("CSI_") or "ACTIVE_SHIELD" in upper or "CEBR3" in upper or "BGO" in upper


def load_geo_step05(plastic_on: bool, outdir: Path):
    wrapper = load_module(GEO_STEP05_WRAPPER, f"geo_opt_step05_wrapper_{'on' if plastic_on else 'off'}")
    step05 = wrapper.load_step05()
    wrapper.configure_step05(step05)
    if not plastic_on:
        step05.is_v3p5_active_veto_volume = legacy_active_veto_no_geoopt_plastic
        step05.ACTIVE_VETO_MATCH_DESCRIPTION = (
            "counterfactual audit: GeoOpt_S1_PlasticFullWrap* is NOT counted as active-veto energy; "
            "CsI_ plus legacy BGO/ACTIVE_SHIELD/CEBR3 tokens remain active"
        )
    step05.OUT = outdir
    step05._PROMPT_NORMALIZATION_AUDIT = None
    adr = step05.load_adr_module()
    step05.configure_parser(adr)
    return wrapper, step05, adr


def load_or_build_geo_catalog(plastic_on: bool, workers: int, rebuild: bool):
    outdir = GEO_STEP05_ON_OUT if plastic_on else PLASTIC_OFF_OUT
    wrapper, step05, adr = load_geo_step05(plastic_on, outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    cat = adr.load_or_build_catalog(outdir, workers=workers, science_flux=1.0, rebuild=rebuild)
    refreshed = step05.refresh_prompt_event_rates(cat)
    if refreshed:
        cache = outdir / "work" / "event_catalog.pkl"
        cache.parent.mkdir(parents=True, exist_ok=True)
        with cache.open("wb") as fh:
            pickle.dump(cat, fh, protocol=pickle.HIGHEST_PROTOCOL)
    return wrapper, step05, cat, outdir


def direct_windows(step05, cat: dict[str, Any]) -> dict[str, Any]:
    disk = step05.side_entry_disk()
    return {
        name: step05.summarize_window(cat, *bounds, disk=disk, reject_policy="keep")
        for name, bounds in step05.WINDOWS.items()
    }


def summarize_by_tag(step05, cat: dict[str, Any], window: tuple[float, float]) -> dict[str, dict[str, Any]]:
    disk = step05.side_entry_disk()
    emin, emax = window
    out: dict[str, dict[str, Any]] = {}
    stream = np.asarray(cat["stream"], dtype=object)
    tag_arr = np.asarray(cat["tag"], dtype=object)
    tes = np.asarray(cat["tes_total_keV"], dtype=float)
    bgo = np.asarray(cat["bgo_total_keV"], dtype=float)
    rate = np.asarray(cat["rate_hz"], dtype=float)
    for tag in sorted(set(str(x) for x in tag_arr[stream == "prompt"])):
        mask = (stream == "prompt") & (tag_arr == tag) & (tes >= emin) & (tes < emax)
        active = mask & (bgo < step05.ACTIVE_VETO_THRESHOLD_KEV)
        final_rate = 0.0
        final_events = 0
        class_counts = Counter()
        for idx in np.flatnonzero(active):
            keep, cls = step05.side_keep_from_hits(step05.event_hits(cat, int(idx)), disk, "keep")
            class_counts[cls] += 1
            if keep:
                final_rate += float(rate[idx])
                final_events += 1
        out[tag] = {
            "raw_events": int(np.count_nonzero(mask)),
            "active_veto_pass_events": int(np.count_nonzero(active)),
            "side_compton_fov_pass_events": final_events,
            "raw_rate_s-1": float(np.sum(rate[mask])),
            "active_veto_pass_rate_s-1": float(np.sum(rate[active])),
            "side_compton_fov_pass_rate_s-1": final_rate,
            "side_compton_class_counts": dict(sorted(class_counts.items())),
        }
    return out


def compare_windows(on: dict[str, Any], off: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for win in sorted(on):
        for stream in ("prompt", "delayed", "science"):
            on_row = on[win]["by_stream"][stream]
            off_row = off[win]["by_stream"][stream]
            for stage in ("raw_rate_s-1", "active_veto_pass_rate_s-1", "side_compton_fov_pass_rate_s-1"):
                a = float(on_row[stage])
                b = float(off_row[stage])
                rows.append(
                    {
                        "window": win,
                        "stream": stream,
                        "stage": stage.replace("_rate_s-1", ""),
                        "plastic_on_rate_s-1": f"{a:.12g}",
                        "plastic_off_rate_s-1": f"{b:.12g}",
                        "on_minus_off_rate_s-1": f"{a - b:.12g}",
                        "on_over_off": "" if b == 0 else f"{a / b:.12g}",
                        "relative_change_percent": "" if b == 0 else f"{100.0 * (a / b - 1.0):.9g}",
                    }
                )
        for stage in ("raw_rate_s-1", "active_veto_pass_rate_s-1", "side_compton_fov_pass_rate_s-1"):
            on_bg = float(on[win]["by_stream"]["prompt"][stage]) + float(on[win]["by_stream"]["delayed"][stage])
            off_bg = float(off[win]["by_stream"]["prompt"][stage]) + float(off[win]["by_stream"]["delayed"][stage])
            rows.append(
                {
                    "window": win,
                    "stream": "background_prompt_plus_delayed",
                    "stage": stage.replace("_rate_s-1", ""),
                    "plastic_on_rate_s-1": f"{on_bg:.12g}",
                    "plastic_off_rate_s-1": f"{off_bg:.12g}",
                    "on_minus_off_rate_s-1": f"{on_bg - off_bg:.12g}",
                    "on_over_off": "" if off_bg == 0 else f"{on_bg / off_bg:.12g}",
                    "relative_change_percent": "" if off_bg == 0 else f"{100.0 * (on_bg / off_bg - 1.0):.9g}",
                }
            )
    return rows


def build_timeline(step05, cat: dict[str, Any]) -> dict[str, Any]:
    rates = np.asarray(cat["rate_hz"], dtype=float)
    total_rate = float(np.sum(rates))
    full_obs = float(step05.delayed_time_s())
    full_lambda = total_rate * full_obs
    if full_lambda > MAX_TIMELINE_DRAW_LAMBDA:
        obs = MAX_TIMELINE_DRAW_LAMBDA / total_rate
        mode = "ADAPTIVE_BOUNDED_HIGH_RATE_POISSON_DRAW"
    else:
        obs = full_obs
        mode = "FULL_INTERVAL_POISSON_DRAW"
    rng = np.random.default_rng(int(step05.RNG_SEED))
    draw = step05.draw_timeline(cat, obs, rng)
    timeline = step05.analyze_timeline(cat, draw, obs, step05.side_entry_disk(), "keep")
    return {
        "model": {
            "mode": mode,
            "full_obs_time_s": full_obs,
            "timeline_obs_time_s": obs,
            "total_catalog_rate_s-1": total_rate,
            "full_interval_expected_instances": full_lambda,
            "max_timeline_draw_lambda": MAX_TIMELINE_DRAW_LAMBDA,
        },
        "draw_summary": draw["draw_summary"],
        "timeline": timeline,
    }


def parse_eplus_plastic_hits(step05) -> dict[str, Any]:
    files = sorted(GEO_PROMPT.glob("Background_eplus_fullsphere20*.sim.gz"))
    eplus_rate = float(step05.prompt_rate_by_tag()["eplus"])
    counters = Counter()
    edep_sums = Counter()

    def flush(event: dict[str, Any] | None) -> None:
        if event is None:
            return
        counters["generated_events"] += 1
        if event["plastic_edep"] > 0:
            counters["events_with_any_plastic_hit"] += 1
            edep_sums["plastic_edep_keV"] += event["plastic_edep"]
        if event["plastic_edep"] >= ACTIVE_VETO_THRESHOLD_KEV:
            counters["events_with_plastic_edep_ge_50keV"] += 1
        if event["plastic_sec_eplus_edep"] > 0:
            counters["events_with_sec_eplus_plastic_hit"] += 1
            edep_sums["plastic_sec_eplus_edep_keV"] += event["plastic_sec_eplus_edep"]
        if event["plastic_sec_eplus_edep"] >= ACTIVE_VETO_THRESHOLD_KEV:
            counters["events_with_sec_eplus_plastic_edep_ge_50keV"] += 1
        if event["plastic_prim_eplus_edep"] > 0:
            counters["events_with_prim_eplus_plastic_hit"] += 1
            edep_sums["plastic_prim_eplus_edep_keV"] += event["plastic_prim_eplus_edep"]

    for path in files:
        current: dict[str, Any] | None = None
        with open_text(path) as fh:
            for raw in fh:
                line = raw.strip()
                if line.startswith("ID "):
                    flush(current)
                    m = ID_RE.match(line)
                    current = {
                        "id": int(m.group(1)) if m else None,
                        "plastic_edep": 0.0,
                        "plastic_sec_eplus_edep": 0.0,
                        "plastic_prim_eplus_edep": 0.0,
                    }
                    continue
                if current is None or "GeoOpt_S1_PlasticFullWrap" not in line or not line.startswith("CC HIT "):
                    continue
                m = CC_HIT_RE.match(line)
                if not m:
                    continue
                kv = dict(KV_RE.findall(m.group(2)))
                try:
                    edep = float(kv.get("edep_keV", "0") or 0.0)
                except ValueError:
                    continue
                current["plastic_edep"] += edep
                if kv.get("sec") == "e+":
                    current["plastic_sec_eplus_edep"] += edep
                if kv.get("prim") == "e+":
                    current["plastic_prim_eplus_edep"] += edep
        flush(current)

    rates = {k + "_rate_s-1": float(v) * eplus_rate for k, v in counters.items()}
    return {
        "input_files": [rel(p) for p in files],
        "event_rate_s-1": eplus_rate,
        "threshold_keV": ACTIVE_VETO_THRESHOLD_KEV,
        "counts": dict(counters),
        "rates": rates,
        "edep_sums_keV": {k: float(v) for k, v in edep_sums.items()},
        "fractions": {
            "any_plastic_hit_per_generated": counters["events_with_any_plastic_hit"] / counters["generated_events"]
            if counters["generated_events"]
            else None,
            "sec_eplus_plastic_hit_per_generated": counters["events_with_sec_eplus_plastic_hit"] / counters["generated_events"]
            if counters["generated_events"]
            else None,
            "sec_eplus_plastic_ge50_per_generated": counters["events_with_sec_eplus_plastic_edep_ge_50keV"] / counters["generated_events"]
            if counters["generated_events"]
            else None,
        },
    }


def matched_plastic_only_veto_rate(
    on_cat: dict[str, Any], off_cat: dict[str, Any], window: tuple[float, float], tag: str = "eplus"
) -> dict[str, Any]:
    emin, emax = window
    off_map: dict[tuple[str, int], float] = {}
    for i in range(len(off_cat["stream"])):
        if str(off_cat["stream"][i]) != "prompt" or str(off_cat["tag"][i]) != tag:
            continue
        off_map[(str(off_cat["source_file"][i]), int(off_cat["local_id"][i]))] = float(off_cat["bgo_total_keV"][i])

    counters = Counter()
    rates = Counter()
    examples = []
    for i in range(len(on_cat["stream"])):
        if str(on_cat["stream"][i]) != "prompt" or str(on_cat["tag"][i]) != tag:
            continue
        tes = float(on_cat["tes_total_keV"][i])
        if not (emin <= tes < emax):
            continue
        rate = float(on_cat["rate_hz"][i])
        key = (str(on_cat["source_file"][i]), int(on_cat["local_id"][i]))
        off_bgo = off_map.get(key)
        on_bgo = float(on_cat["bgo_total_keV"][i])
        counters["tes_window_events"] += 1
        rates["tes_window_rate_s-1"] += rate
        if off_bgo is None:
            counters["missing_in_off_catalog"] += 1
            continue
        if off_bgo < ACTIVE_VETO_THRESHOLD_KEV and on_bgo >= ACTIVE_VETO_THRESHOLD_KEV:
            counters["vetoed_only_when_plastic_is_active_events"] += 1
            rates["vetoed_only_when_plastic_is_active_rate_s-1"] += rate
            if len(examples) < 20:
                examples.append(
                    {
                        "source_file": rel(Path(key[0])),
                        "local_id": key[1],
                        "tes_total_keV": tes,
                        "plastic_on_active_keV": on_bgo,
                        "plastic_off_active_keV": off_bgo,
                        "rate_s-1": rate,
                    }
                )
        elif off_bgo >= ACTIVE_VETO_THRESHOLD_KEV:
            counters["also_vetoed_without_plastic_events"] += 1
            rates["also_vetoed_without_plastic_rate_s-1"] += rate
        else:
            counters["survives_active_veto_with_plastic_events"] += 1
            rates["survives_active_veto_with_plastic_rate_s-1"] += rate
    save_csv(
        WORK / "plastic_only_veto_eplus_w2_examples.csv",
        examples,
        ["source_file", "local_id", "tes_total_keV", "plastic_on_active_keV", "plastic_off_active_keV", "rate_s-1"],
    )
    return {"counts": dict(counters), "rates": {k: float(v) for k, v in rates.items()}, "examples_csv": rel(WORK / "plastic_only_veto_eplus_w2_examples.csv")}


def build_plastic_veto_audit(workers: int, rebuild_off: bool) -> dict[str, Any]:
    _, step05_on, cat_on, on_out = load_or_build_geo_catalog(True, workers=workers, rebuild=False)
    _, step05_off, cat_off, off_out = load_or_build_geo_catalog(False, workers=workers, rebuild=rebuild_off)

    on_windows = direct_windows(step05_on, cat_on)
    off_windows = direct_windows(step05_off, cat_off)
    rows = compare_windows(on_windows, off_windows)
    save_csv(
        WORK / "plastic_veto_on_off_direct_rate_comparison.csv",
        rows,
        [
            "window",
            "stream",
            "stage",
            "plastic_on_rate_s-1",
            "plastic_off_rate_s-1",
            "on_minus_off_rate_s-1",
            "on_over_off",
            "relative_change_percent",
        ],
    )

    tag_rows: list[dict[str, Any]] = []
    for win, bounds in step05_on.WINDOWS.items():
        on_tags = summarize_by_tag(step05_on, cat_on, bounds)
        off_tags = summarize_by_tag(step05_off, cat_off, bounds)
        for tag in sorted(set(on_tags) | set(off_tags)):
            for stage in ("raw_rate_s-1", "active_veto_pass_rate_s-1", "side_compton_fov_pass_rate_s-1"):
                on_rate = float(on_tags.get(tag, {}).get(stage, 0.0))
                off_rate = float(off_tags.get(tag, {}).get(stage, 0.0))
                tag_rows.append(
                    {
                        "window": win,
                        "tag": tag,
                        "stage": stage.replace("_rate_s-1", ""),
                        "plastic_on_rate_s-1": f"{on_rate:.12g}",
                        "plastic_off_rate_s-1": f"{off_rate:.12g}",
                        "on_minus_off_rate_s-1": f"{on_rate - off_rate:.12g}",
                        "on_over_off": "" if off_rate == 0 else f"{on_rate / off_rate:.12g}",
                        "relative_change_percent": "" if off_rate == 0 else f"{100.0 * (on_rate / off_rate - 1.0):.9g}",
                    }
                )
    save_csv(
        WORK / "plastic_veto_on_off_prompt_by_tag_comparison.csv",
        tag_rows,
        ["window", "tag", "stage", "plastic_on_rate_s-1", "plastic_off_rate_s-1", "on_minus_off_rate_s-1", "on_over_off", "relative_change_percent"],
    )

    eplus_hit = parse_eplus_plastic_hits(step05_on)
    eplus_w2 = matched_plastic_only_veto_rate(cat_on, cat_off, step05_on.WINDOWS["w2_510p58_511p42"], tag="eplus")

    timeline_on = build_timeline(step05_on, cat_on)
    timeline_off = build_timeline(step05_off, cat_off)
    timeline_rows: list[dict[str, Any]] = []
    for win in step05_on.WINDOWS:
        for stage in ("raw", "active_veto_pass", "side_compton_fov_pass"):
            a = float(timeline_on["timeline"]["windows"][win]["rates_s-1"][stage])
            b = float(timeline_off["timeline"]["windows"][win]["rates_s-1"][stage])
            timeline_rows.append(
                {
                    "window": win,
                    "stage": stage,
                    "plastic_on_rate_s-1": f"{a:.12g}",
                    "plastic_off_rate_s-1": f"{b:.12g}",
                    "on_minus_off_rate_s-1": f"{a - b:.12g}",
                    "on_over_off": "" if b == 0 else f"{a / b:.12g}",
                    "relative_change_percent": "" if b == 0 else f"{100.0 * (a / b - 1.0):.9g}",
                }
            )
    save_csv(
        WORK / "plastic_veto_on_off_timeline_rate_comparison.csv",
        timeline_rows,
        ["window", "stage", "plastic_on_rate_s-1", "plastic_off_rate_s-1", "on_minus_off_rate_s-1", "on_over_off", "relative_change_percent"],
    )

    w2_on_bg = (
        on_windows["w2_510p58_511p42"]["by_stream"]["prompt"]["side_compton_fov_pass_rate_s-1"]
        + on_windows["w2_510p58_511p42"]["by_stream"]["delayed"]["side_compton_fov_pass_rate_s-1"]
    )
    w2_off_bg = (
        off_windows["w2_510p58_511p42"]["by_stream"]["prompt"]["side_compton_fov_pass_rate_s-1"]
        + off_windows["w2_510p58_511p42"]["by_stream"]["delayed"]["side_compton_fov_pass_rate_s-1"]
    )
    broad_on_bg = (
        on_windows["broad_480_550"]["by_stream"]["prompt"]["side_compton_fov_pass_rate_s-1"]
        + on_windows["broad_480_550"]["by_stream"]["delayed"]["side_compton_fov_pass_rate_s-1"]
    )
    broad_off_bg = (
        off_windows["broad_480_550"]["by_stream"]["prompt"]["side_compton_fov_pass_rate_s-1"]
        + off_windows["broad_480_550"]["by_stream"]["delayed"]["side_compton_fov_pass_rate_s-1"]
    )

    return {
        "definition": {
            "plastic_on": "GeoOpt_S1_PlasticFullWrap* counted as active-veto energy at 50 keV threshold",
            "plastic_off": "same geometry and same SIM, but GeoOpt_S1_PlasticFullWrap* excluded from active-veto energy in post-processing",
            "not_tested": "removing the plastic material from transport; this audit does not rerun Cosima",
        },
        "inputs": {
            "plastic_on_catalog_outdir": rel(on_out),
            "plastic_off_catalog_outdir": rel(off_out),
            "prompt_dir": rel(GEO_PROMPT),
            "delayed_sim": rel(GEO_DELAYED_SIM),
        },
        "catalogs": {
            "plastic_on_events_kept": int(len(cat_on["stream"])),
            "plastic_off_events_kept": int(len(cat_off["stream"])),
            "plastic_on_total_catalog_rate_s-1": float(np.sum(cat_on["rate_hz"])),
            "plastic_off_total_catalog_rate_s-1": float(np.sum(cat_off["rate_hz"])),
        },
        "direct_summary": {
            "w2_background_plastic_on_cps": float(w2_on_bg),
            "w2_background_plastic_off_cps": float(w2_off_bg),
            "w2_on_minus_off_cps": float(w2_on_bg - w2_off_bg),
            "w2_relative_change_percent": 100.0 * (w2_on_bg / w2_off_bg - 1.0) if w2_off_bg > 0 else None,
            "broad_background_plastic_on_cps": float(broad_on_bg),
            "broad_background_plastic_off_cps": float(broad_off_bg),
            "broad_on_minus_off_cps": float(broad_on_bg - broad_off_bg),
            "broad_relative_change_percent": 100.0 * (broad_on_bg / broad_off_bg - 1.0) if broad_off_bg > 0 else None,
        },
        "eplus_plastic_hits": eplus_hit,
        "eplus_w2_matched_plastic_only_veto": eplus_w2,
        "timeline": {"plastic_on": timeline_on, "plastic_off": timeline_off},
        "tables": {
            "direct_rate_comparison": rel(WORK / "plastic_veto_on_off_direct_rate_comparison.csv"),
            "prompt_by_tag_comparison": rel(WORK / "plastic_veto_on_off_prompt_by_tag_comparison.csv"),
            "timeline_rate_comparison": rel(WORK / "plastic_veto_on_off_timeline_rate_comparison.csv"),
            "eplus_w2_examples": eplus_w2["examples_csv"],
        },
    }


def pct_change(geo: float, mass: float) -> float | None:
    return None if mass == 0 else 100.0 * (geo / mass - 1.0)


def fmt(v: float | None, digits: int = 6) -> str:
    if v is None or not math.isfinite(float(v)):
        return "NA"
    return f"{float(v):.{digits}g}"


def write_report(summary: dict[str, Any]) -> Path:
    activation = summary["activation"]["summary"]
    neutron = summary["neutron_energy_depth"]["summary"]
    plastic = summary["plastic_veto"]["direct_summary"]
    eplus = summary["plastic_veto"]["eplus_plastic_hits"]
    eplus_w2 = summary["plastic_veto"]["eplus_w2_matched_plastic_only_veto"]

    lines = [
        "# Geo-opt S1/BPE/W5 Neutron and Plastic-Skin Audit",
        "",
        f"Status: `{summary['status']}`",
        "",
        "Scope:",
        "- No geometry or Cosima transport was rerun.",
        "- Activation comparison uses ground-state-corrected day-15 activity CSVs.",
        "- Plastic on/off uses the same geo-opt SIM files; only the Step05 active-veto volume definition is changed.",
        "",
        "## 1. BPE / shield-stack neutron activation question",
        "",
        f"- Mass_model_511 fixed total activity: `{fmt(activation['mass_fixed_total_activity_Bq'], 9)} Bq`.",
        f"- Geo-opt fixed total activity: `{fmt(activation['geo_fixed_total_activity_Bq'], 9)} Bq` "
        f"({fmt(pct_change(activation['geo_fixed_total_activity_Bq'], activation['mass_fixed_total_activity_Bq']), 5)}%).",
        f"- Geo-opt internal activity excluding added GeoOpt layers: `{fmt(activation['geo_internal_excluding_added_layers_Bq'], 9)} Bq` "
        f"vs Mass `{fmt(activation['mass_internal_Bq'], 9)} Bq` "
        f"({fmt(pct_change(activation['geo_internal_excluding_added_layers_Bq'], activation['mass_internal_Bq']), 5)}%).",
        f"- CsI activity: geo `{fmt(activation['geo_CsI_Bq'], 9)} Bq` vs Mass `{fmt(activation['mass_CsI_Bq'], 9)} Bq` "
        f"({fmt(pct_change(activation['geo_CsI_Bq'], activation['mass_CsI_Bq']), 5)}%).",
        f"- Added GeoOpt layer activity itself: `{fmt(activation['geo_added_layers_Bq'], 9)} Bq`.",
        "",
        "Interpretation: this supports that the current outer shield stack is reducing internal activation versus Mass_model_511. "
        "It is not a pure BPE-only causal isolation, because the geometry also changed by adding plastic and a W bottom baffle. "
        "A strict BPE-only claim would require an otherwise-identical no-BPE A/B transport.",
        "",
        "Neutron energy-depth audit:",
        f"- Geo neutron weighted RPIP points: `{fmt(neutron['geo']['weighted_rpip_points'], 9)}`; internal `{fmt(neutron['geo']['weighted_internal_rpip_points'], 9)}`; CsI `{fmt(neutron['geo']['weighted_CsI_rpip_points'], 9)}`.",
        f"- Mass neutron weighted RPIP points: `{fmt(neutron['mass']['weighted_rpip_points'], 9)}`; internal `{fmt(neutron['mass']['weighted_internal_rpip_points'], 9)}`; CsI `{fmt(neutron['mass']['weighted_CsI_rpip_points'], 9)}`.",
        f"- Plot: `{summary['neutron_energy_depth']['outputs']['plot']}`.",
        "",
        "## 2. Plastic-skin active veto question",
        "",
        f"- W2 final background with plastic active: `{fmt(plastic['w2_background_plastic_on_cps'], 9)} cps`.",
        f"- W2 final background with plastic disabled in veto accounting: `{fmt(plastic['w2_background_plastic_off_cps'], 9)} cps`.",
        f"- W2 on-off delta: `{fmt(plastic['w2_on_minus_off_cps'], 9)} cps` "
        f"({fmt(plastic['w2_relative_change_percent'], 5)}%).",
        f"- Broad 480-550 final background with plastic active: `{fmt(plastic['broad_background_plastic_on_cps'], 9)} cps`.",
        f"- Broad 480-550 final background with plastic disabled: `{fmt(plastic['broad_background_plastic_off_cps'], 9)} cps`.",
        f"- Broad on-off delta: `{fmt(plastic['broad_on_minus_off_cps'], 9)} cps` "
        f"({fmt(plastic['broad_relative_change_percent'], 5)}%).",
        "",
        "Does it catch positrons?",
        f"- Prompt e+ generated events parsed: `{eplus['counts'].get('generated_events', 0)}`.",
        f"- Events with any GeoOpt plastic hit: `{eplus['counts'].get('events_with_any_plastic_hit', 0)}` "
        f"({fmt(100.0 * eplus['fractions']['any_plastic_hit_per_generated'], 5)}%).",
        f"- Events with `sec=e+` ionization hit in plastic: `{eplus['counts'].get('events_with_sec_eplus_plastic_hit', 0)}` "
        f"({fmt(100.0 * eplus['fractions']['sec_eplus_plastic_hit_per_generated'], 5)}%).",
        f"- Events with `sec=e+` plastic deposit >= 50 keV: `{eplus['counts'].get('events_with_sec_eplus_plastic_edep_ge_50keV', 0)}` "
        f"({fmt(100.0 * eplus['fractions']['sec_eplus_plastic_ge50_per_generated'], 5)}%).",
        f"- In W2 prompt e+ TES-window events, events vetoed only when plastic is active: "
        f"`{eplus_w2['counts'].get('vetoed_only_when_plastic_is_active_events', 0)}`; rate "
        f"`{fmt(eplus_w2['rates'].get('vetoed_only_when_plastic_is_active_rate_s-1', 0.0), 9)} cps`.",
        "",
        "Important caveat: plastic off here means 'do not count plastic energy as veto'. "
        "The plastic material is still present in the transport, so attenuation and scattering by the layer are unchanged.",
        "",
        "Tables:",
        f"- `{summary['activation']['tables']['category_comparison']}`",
        f"- `{summary['activation']['tables']['top_volume_comparison']}`",
        f"- `{summary['neutron_energy_depth']['outputs']['binned_csv']}`",
        f"- `{summary['plastic_veto']['tables']['direct_rate_comparison']}`",
        f"- `{summary['plastic_veto']['tables']['prompt_by_tag_comparison']}`",
        f"- `{summary['plastic_veto']['tables']['timeline_rate_comparison']}`",
        "",
    ]
    path = WORK / "GEO_OPT_NEUTRON_PLASTIC_AUDIT.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--rebuild-plastic-off", action="store_true")
    args = ap.parse_args()

    WORK.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)

    activation = build_activation_audit()
    neutron = build_neutron_energy_depth_plot(workers=max(1, int(args.workers)))
    plastic = build_plastic_veto_audit(workers=max(1, int(args.workers)), rebuild_off=bool(args.rebuild_plastic_off))

    summary = {
        "document_type": "geo_opt_s1_bpe_w5_neutron_plastic_audit",
        "generated_at_utc": now_utc(),
        "status": "PASS_POSTPROCESS_AUDIT_NOT_GEOMETRY_PROMOTION",
        "activation": activation,
        "neutron_energy_depth": neutron,
        "plastic_veto": plastic,
    }
    write_json(WORK / "geo_opt_neutron_plastic_audit_summary.json", summary)
    report = write_report(summary)
    print(json.dumps({"status": summary["status"], "summary": rel(WORK / "geo_opt_neutron_plastic_audit_summary.json"), "report": rel(report)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
