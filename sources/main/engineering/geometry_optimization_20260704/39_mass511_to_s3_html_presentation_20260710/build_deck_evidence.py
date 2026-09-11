#!/usr/bin/env python3
"""Build auditable figures and compact image assets for the Mass_511→S3 deck.

The trajectory plots deliberately rebuild the S3 W2 final-event sample from
the authoritative Step05 / atmospheric sidecar inputs.  Rays are straight
incident chords from the true ``IA INIT`` origin (or its intersection with
the S3 outer envelope) to the energy-weighted TES hit centroid; they are not
Geant4 step-by-step tracks.
"""

from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import math
import os
import pickle
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from PIL import Image


ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
ASSETS = WORK / "assets"

W2_MIN = 510.58
W2_MAX = 511.42
ACTIVE_THRESHOLD_KEV = 50.0

PROMPT_AUDIT = (
    ROOT
    / "engineering/geometry_optimization_20260704/24_s3_vs_mass511_step05_sensitivity_20260709"
    / "s3_prompt_eplus_n_unvetoed_event_audit.json"
)
DELAYED_FILE_CATALOG = (
    ROOT
    / "stepwise_maintenance/step05_veto_time_axis/outputs_s3_csi_barrel_fullstat_v1_20260709_l1"
    / "work/file_catalogs/delayed_DelayedDecayS3CsiBarrelFullstatV1M50000.inc1.id1.sim.gz.af1aae196a2f.pkl"
)
ATM_SUMMARY = (
    ROOT
    / "engineering/geometry_optimization_20260704/22_s3_eqstats_prompt_atm511_20260709"
    / "s3_atm511_sidecar_3m_summary.json"
)
S3_VISUAL_BUILDER = (
    ROOT
    / "engineering/geometry_optimization_20260704/21_geoopt_s3_csi_barrel_20260709"
    / "build_s3_full_visuals.py"
)

ID_RE = re.compile(r"^ID\s+(\d+)")
CC_HIT_RE = re.compile(r"^CC\s+HIT\s+(\S+)\s+(.*)$")
KV_RE = re.compile(r"(\w+)=([^\s]+)")

COLORS = {
    "eplus": "#F06A4B",
    "n": "#3D8BFF",
    "atm511": "#A66BFF",
    "activation": "#F2B84B",
}
LABELS = {
    "eplus": "e+ prompt",
    "n": "neutron prompt",
    "atm511": "ATM511",
    "activation": "activation / delayed",
}

# S3 outer plastic envelope in the instrument frame.
OUTER_RADIUS_CM = 30.0
OUTER_ZMIN_CM = -27.5
OUTER_ZMAX_CM = 49.0
WINDOW_Z0_CM = -5.2
WINDOW_HALF_Y_CM = 1.898
WINDOW_HALF_Z_CM = 1.898


STATIC_IMAGES = {
    "mass_2d_processed.png": ROOT
    / "outputs/reports/Mass_model_511_stage_diam_300_300_300_350_350_400_20260701"
    / "Mass_model_511_stage_diam_300_300_300_350_350_400_2d_schematic.png",
    "s1_2d_processed.png": ROOT
    / "engineering/geometry_optimization_20260704/01_geo_opt_s1_bottomw_b4c/figures"
    / "geo_opt_s1_bottomw_b4c_2d_detail.png",
    "s2b_2d_processed.png": ROOT
    / "engineering/geometry_optimization_20260704/16_geoopt_s2b_cryo_shell_45deg_20260708/figures"
    / "geoopt_s2b_cryo_shell_45deg_2d_detail.png",
    "s3_2d_processed.png": ROOT
    / "engineering/geometry_optimization_20260704/21_geoopt_s3_csi_barrel_20260709/figures"
    / "geoopt_s3_csi_barrel_full_2d.png",
    "s3_rz_processed.png": ROOT
    / "engineering/geometry_optimization_20260704/21_geoopt_s3_csi_barrel_20260709/figures"
    / "geoopt_s3_csi_barrel_rz_layers.png",
    "s3a_2d_processed.png": ROOT
    / "engineering/geometry_optimization_20260704/27_geoopt_s3a_bgo_barrel_20260709/figures"
    / "geoopt_s3a_bgo_barrel_full_2d_preview.png",
    "s3a_shell_processed.png": ROOT
    / "engineering/geometry_optimization_20260704/27_geoopt_s3a_bgo_barrel_20260709/figures"
    / "geoopt_s3a_bgo_barrel_shell_zoom_preview.png",
    "s3b_2d_processed.png": ROOT
    / "engineering/geometry_optimization_20260704/28_geoopt_s3b_w2mm_al3mm_shell_20260709/figures"
    / "geoopt_s3b_w2mm_al3mm_full_2d_preview.png",
    "s3b_shell_processed.png": ROOT
    / "engineering/geometry_optimization_20260704/28_geoopt_s3b_w2mm_al3mm_shell_20260709/figures"
    / "geoopt_s3b_w2mm_al3mm_shell_zoom_preview.png",
    "s3c_2d_processed.png": ROOT
    / "engineering/geometry_optimization_20260704/29_geoopt_s3c_bgo_w2mm_al3mm_shell_20260709/figures"
    / "geoopt_s3c_bgo_w2mm_al3mm_full_2d_preview.png",
    "s3c_shell_processed.png": ROOT
    / "engineering/geometry_optimization_20260704/29_geoopt_s3c_bgo_w2mm_al3mm_shell_20260709/figures"
    / "geoopt_s3c_bgo_w2mm_al3mm_shell_zoom_preview.png",
}


def rel(path: Path | str) -> str:
    p = Path(path).resolve()
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return str(p)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def parse_ia_init(line: str) -> dict[str, float] | None:
    try:
        fields = [part.strip() for part in line.split("IA INIT", 1)[1].split(";")]
        x, y, z = (float(fields[4]), float(fields[5]), float(fields[6]))
        dx, dy, dz = (float(fields[16]), float(fields[17]), float(fields[18]))
        energy = float(fields[-1])
    except Exception:
        return None
    return {
        "init_x_cm": x,
        "init_y_cm": y,
        "init_z_cm": z,
        "dir_x": dx,
        "dir_y": dy,
        "dir_z": dz,
        "init_energy_keV": energy,
    }


def parse_hit(line: str) -> dict[str, Any] | None:
    match = CC_HIT_RE.match(line)
    if match is None:
        return None
    kv = dict(KV_RE.findall(match.group(2)))
    try:
        return {
            "volume": match.group(1),
            "edep_keV": float(kv.get("edep_keV", 0.0)),
            "x": float(kv.get("x", "nan")),
            "y": float(kv.get("y", "nan")),
            "z": float(kv.get("z", "nan")),
        }
    except ValueError:
        return None


def is_tes_volume(volume: str) -> bool:
    upper = volume.upper()
    return upper.startswith("TP_") or upper.startswith("TES_")


def scan_target_events(path: Path, ids: set[int], collect_tes: bool) -> dict[int, dict[str, Any]]:
    """Stream one SIM and retain only selected event INIT/TES metadata."""
    remaining = set(int(i) for i in ids)
    records: dict[int, dict[str, Any]] = {}
    cur_id: int | None = None
    interested = False
    init: dict[str, float] | None = None
    tes_e = tes_wx = tes_wy = tes_wz = 0.0

    def flush() -> None:
        nonlocal cur_id, interested, init, tes_e, tes_wx, tes_wy, tes_wz
        if interested and cur_id is not None:
            rec: dict[str, Any] = {"init": init}
            if collect_tes and tes_e > 0:
                rec.update(
                    {
                        "tes_x_cm": tes_wx / tes_e,
                        "tes_y_cm": tes_wy / tes_e,
                        "tes_z_cm": tes_wz / tes_e,
                        "tes_total_keV_from_sim": tes_e,
                    }
                )
            records[int(cur_id)] = rec
            remaining.discard(int(cur_id))
        cur_id = None
        interested = False
        init = None
        tes_e = tes_wx = tes_wy = tes_wz = 0.0

    print(f"scan {rel(path)} targets={len(ids)}", flush=True)
    with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if line == "SE":
                flush()
                if not remaining:
                    break
                continue
            match_id = ID_RE.match(line)
            if match_id:
                cur_id = int(match_id.group(1))
                interested = cur_id in remaining
                continue
            if not interested:
                continue
            if line.startswith("IA INIT"):
                init = parse_ia_init(line)
                continue
            if collect_tes and line.startswith("CC HIT "):
                hit = parse_hit(line)
                if hit is None or not is_tes_volume(str(hit["volume"])):
                    continue
                e = float(hit["edep_keV"])
                if e <= 0:
                    continue
                tes_e += e
                tes_wx += e * float(hit["x"])
                tes_wy += e * float(hit["y"])
                tes_wz += e * float(hit["z"])
        flush()
    if remaining:
        raise RuntimeError(f"missing {len(remaining)} events in {path}: {sorted(remaining)[:12]}")
    return records


def weighted_centroid(hits: list[dict[str, Any]]) -> tuple[float, float, float]:
    total = sum(float(hit.get("e_keV", 0.0)) for hit in hits)
    if total <= 0:
        raise RuntimeError("TES centroid has zero energy")
    return tuple(
        sum(float(hit.get("e_keV", 0.0)) * float(hit[axis]) for hit in hits) / total
        for axis in ("x", "y", "z")
    )


def load_prompt_rows() -> list[dict[str, Any]]:
    data = json.loads(PROMPT_AUDIT.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    targets: dict[Path, set[int]] = defaultdict(set)
    for event in data["events"]:
        x, y, z = weighted_centroid(event["tes_hits"])
        path = Path(event["source_file"])
        row = {
            "source_family": str(event["tag"]),
            "source_file": rel(path),
            "local_id": int(event["local_id"]),
            "tes_total_keV": float(event["tes_total_keV"]),
            "rate_cps": float(event["rate_hz"]),
            "tes_x_cm": x,
            "tes_y_cm": y,
            "tes_z_cm": z,
            "selection_scope": "S3 Step05 W2 active-veto and side-Compton/FoV survivor",
        }
        rows.append(row)
        targets[path].add(int(event["local_id"]))
    metadata: dict[tuple[str, int], dict[str, Any]] = {}
    for path, ids in sorted(targets.items(), key=lambda item: str(item[0])):
        for event_id, rec in scan_target_events(path, ids, collect_tes=False).items():
            metadata[(rel(path), event_id)] = rec
    for row in rows:
        init = metadata[(row["source_file"], row["local_id"])]["init"]
        if init is None:
            raise RuntimeError(f"missing prompt INIT: {row['source_file']} ID {row['local_id']}")
        row.update(init)
    return rows


def catalog_centroid(cat: dict[str, Any], idx: int) -> tuple[float, float, float]:
    start = int(cat["pix_start"][idx])
    count = int(cat["pix_count"][idx])
    indices = range(start, start + count)
    total = sum(float(cat["pix_e"][j]) for j in indices)
    if total <= 0:
        raise RuntimeError(f"zero TES energy for delayed catalog index {idx}")
    return tuple(
        sum(float(cat["pix_e"][j]) * float(cat[key][j]) for j in range(start, start + count)) / total
        for key in ("pix_x", "pix_y", "pix_z")
    )


def load_delayed_rows() -> list[dict[str, Any]]:
    with DELAYED_FILE_CATALOG.open("rb") as handle:
        cat = pickle.load(handle)
    rows: list[dict[str, Any]] = []
    for idx, (tes, active) in enumerate(zip(cat["tes_total_keV"], cat["bgo_total_keV"])):
        if not (W2_MIN <= float(tes) < W2_MAX and float(active) < ACTIVE_THRESHOLD_KEV):
            continue
        x, y, z = catalog_centroid(cat, idx)
        rows.append(
            {
                "source_family": "activation",
                "source_file": rel(cat["source_file"][idx]),
                "local_id": int(cat["local_id"][idx]),
                "tes_total_keV": float(tes),
                "rate_cps": float(cat["rate_hz"][idx]),
                "tes_x_cm": x,
                "tes_y_cm": y,
                "tes_z_cm": z,
                "selection_scope": "S3 Step05 W2 delayed active-veto survivor; all 12 also side-Compton/FoV pass",
            }
        )
    if len(rows) != 12:
        raise RuntimeError(f"expected 12 delayed final events, got {len(rows)}")
    by_path: dict[Path, set[int]] = defaultdict(set)
    for row in rows:
        by_path[ROOT / row["source_file"]].add(int(row["local_id"]))
    metadata: dict[tuple[str, int], dict[str, Any]] = {}
    for path, ids in by_path.items():
        for event_id, rec in scan_target_events(path, ids, collect_tes=False).items():
            metadata[(rel(path), event_id)] = rec
    for row in rows:
        init = metadata[(row["source_file"], row["local_id"])]["init"]
        if init is None:
            raise RuntimeError(f"missing delayed INIT ID {row['local_id']}")
        row.update(init)
    return rows


def load_atm_rows() -> list[dict[str, Any]]:
    data = json.loads(ATM_SUMMARY.read_text(encoding="utf-8"))
    window = data["windows"]["w2_510p58_511p42"]
    ids = [int(value) for value in window["final_event_ids"]]
    energies = [float(value) for value in window["final_energies_keV"]]
    sim = ROOT / data["inputs"]["sim"]
    records = scan_target_events(sim, set(ids), collect_tes=True)
    rows: list[dict[str, Any]] = []
    for event_id, energy in zip(ids, energies):
        rec = records[event_id]
        if rec.get("init") is None or rec.get("tes_x_cm") is None:
            raise RuntimeError(f"incomplete ATM511 event {event_id}: {rec}")
        row = {
            "source_family": "atm511",
            "source_file": rel(sim),
            "local_id": event_id,
            "tes_total_keV": energy,
            "rate_cps": float(window["event_rate_weight_cps"]),
            "tes_x_cm": float(rec["tes_x_cm"]),
            "tes_y_cm": float(rec["tes_y_cm"]),
            "tes_z_cm": float(rec["tes_z_cm"]),
            "selection_scope": "S3 3M semi-empirical 4pi ATM511 sidecar W2 final survivor",
        }
        row.update(rec["init"])
        rows.append(row)
    if len(rows) != 56:
        raise RuntimeError(f"expected 56 ATM511 final events, got {len(rows)}")
    return rows


def rotate_y(vec: tuple[float, float, float] | np.ndarray, angle_deg: float) -> np.ndarray:
    x, y, z = [float(value) for value in vec]
    angle = math.radians(angle_deg)
    c, s = math.cos(angle), math.sin(angle)
    return np.asarray([c * x + s * z, y, -s * x + c * z], dtype=float)


def classify_entry(row: dict[str, Any]) -> dict[str, Any]:
    p = rotate_y((row["init_x_cm"], row["init_y_cm"], row["init_z_cm"]), -45.0)
    d = rotate_y((row["dir_x"], row["dir_y"], row["dir_z"]), -45.0)
    norm = float(np.linalg.norm(d))
    if norm <= 0:
        raise RuntimeError(f"bad INIT direction for {row['source_family']} {row['local_id']}")
    d /= norm
    radius = math.hypot(float(p[0]), float(p[1]))
    inside = radius <= OUTER_RADIUS_CM + 1e-7 and OUTER_ZMIN_CM - 1e-7 <= p[2] <= OUTER_ZMAX_CM + 1e-7
    base = {
        "init_local_x_cm": float(p[0]),
        "init_local_y_cm": float(p[1]),
        "init_local_z_cm": float(p[2]),
        "dir_local_x": float(d[0]),
        "dir_local_y": float(d[1]),
        "dir_local_z": float(d[2]),
    }
    if inside:
        base.update(
            {
                "entry_surface": "internal",
                "entry_region": activation_origin_region(p),
                "plot_start_x_cm": float(row["init_x_cm"]),
                "plot_start_y_cm": float(row["init_y_cm"]),
                "plot_start_z_cm": float(row["init_z_cm"]),
            }
        )
        return base

    candidates: list[tuple[float, str, np.ndarray]] = []
    a = d[0] ** 2 + d[1] ** 2
    b = 2.0 * (p[0] * d[0] + p[1] * d[1])
    c = p[0] ** 2 + p[1] ** 2 - OUTER_RADIUS_CM**2
    if abs(a) > 1e-15:
        disc = b * b - 4.0 * a * c
        if disc >= 0:
            root = math.sqrt(disc)
            for t in ((-b - root) / (2.0 * a), (-b + root) / (2.0 * a)):
                if t <= 0:
                    continue
                q = p + t * d
                if OUTER_ZMIN_CM - 1e-6 <= q[2] <= OUTER_ZMAX_CM + 1e-6:
                    candidates.append((float(t), "side", q))
    if abs(d[2]) > 1e-15:
        for zcap, surface in ((OUTER_ZMIN_CM, "bottom"), (OUTER_ZMAX_CM, "top")):
            t = (zcap - p[2]) / d[2]
            if t <= 0:
                continue
            q = p + t * d
            if q[0] ** 2 + q[1] ** 2 <= OUTER_RADIUS_CM**2 + 1e-6:
                candidates.append((float(t), surface, q))
    if not candidates:
        base.update(
            {
                "entry_surface": "miss",
                "entry_region": "miss_outer_envelope",
                "plot_start_x_cm": float(row["init_x_cm"]),
                "plot_start_y_cm": float(row["init_y_cm"]),
                "plot_start_z_cm": float(row["init_z_cm"]),
            }
        )
        return base
    _, surface, q = min(candidates, key=lambda item: item[0])
    phi = math.degrees(math.atan2(float(q[1]), float(q[0]))) % 360.0
    is_window = (
        surface == "side"
        and q[0] < 0
        and abs(float(q[1])) <= WINDOW_HALF_Y_CM
        and abs(float(q[2]) - WINDOW_Z0_CM) <= WINDOW_HALF_Z_CM
    )
    if is_window:
        region = "side_window_aperture"
    elif surface == "side":
        sector = int(math.floor((phi + 22.5) / 45.0)) % 8
        region = f"side_phi_sector_{sector}"
    else:
        region = surface
    start_world = rotate_y(q, 45.0)
    base.update(
        {
            "entry_surface": surface,
            "entry_region": region,
            "entry_phi_deg_local": phi,
            "entry_local_x_cm": float(q[0]),
            "entry_local_y_cm": float(q[1]),
            "entry_local_z_cm": float(q[2]),
            "plot_start_x_cm": float(start_world[0]),
            "plot_start_y_cm": float(start_world[1]),
            "plot_start_z_cm": float(start_world[2]),
        }
    )
    return base


def activation_origin_region(p_local: np.ndarray) -> str:
    r = math.hypot(float(p_local[0]), float(p_local[1]))
    z = float(p_local[2])
    if r >= 21.2 and -23.4 <= z <= 44.9:
        return "barrel_side"
    if z < -19.4:
        return "bottom_end"
    if z > 40.9:
        return "top_end"
    if r < 21.2:
        return "inner_instrument"
    return "other_internal"


def process_static_images() -> dict[str, dict[str, Any]]:
    outputs: dict[str, dict[str, Any]] = {}
    ASSETS.mkdir(parents=True, exist_ok=True)
    for name, source in STATIC_IMAGES.items():
        if not source.exists():
            raise FileNotFoundError(source)
        target = ASSETS / name
        with Image.open(source) as image:
            original = image.size
            image = image.convert("RGB")
            if image.width > 1200:
                height = max(1, round(image.height * 1200 / image.width))
                image = image.resize((1200, height), Image.Resampling.LANCZOS)
            image.save(target, format="PNG", optimize=True, compress_level=9)
            outputs[name] = {
                "source": rel(source),
                "source_size_px": list(original),
                "processed_size_px": list(image.size),
                "output": rel(target),
            }
    return outputs


def chart_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 13,
            "axes.labelsize": 10,
            "axes.edgecolor": "#53606f",
            "axes.facecolor": "#fbfaf6",
            "figure.facecolor": "#fbfaf6",
            "grid.color": "#cbd2d9",
            "grid.alpha": 0.30,
            "text.color": "#17202b",
            "axes.labelcolor": "#17202b",
            "xtick.color": "#33404f",
            "ytick.color": "#33404f",
        }
    )


def add_geometry(ax: Any, builder: Any, exporter: Any, segments: dict[str, Any]) -> None:
    builder.add_segments(ax, exporter, segments)
    ax.grid(True, linewidth=0.35, alpha=0.26)
    ax.set_aspect("equal", adjustable="box")


def ray_points(row: dict[str, Any], plane: str) -> tuple[list[float], list[float]]:
    start = (row["plot_start_x_cm"], row["plot_start_y_cm"], row["plot_start_z_cm"])
    end = (row["tes_x_cm"], row["tes_y_cm"], row["tes_z_cm"])
    if plane == "xz":
        return [start[0], end[0]], [start[2], end[2]]
    if plane == "xy":
        return [start[0], end[0]], [start[1], end[1]]
    raise ValueError(plane)


def draw_ray(ax: Any, row: dict[str, Any], plane: str, arrow: bool, alpha: float) -> None:
    xs, ys = ray_points(row, plane)
    color = COLORS[row["source_family"]]
    ax.plot(xs, ys, color=color, lw=1.05, alpha=alpha, zorder=12)
    ax.scatter(xs[0], ys[0], s=11, facecolor="none", edgecolor=color, linewidth=0.65, alpha=min(1, alpha + 0.18), zorder=13)
    ax.scatter(xs[1], ys[1], s=12, facecolor=color, edgecolor="#1b1e24", linewidth=0.25, alpha=min(1, alpha + 0.12), zorder=14)
    if arrow:
        x0 = xs[0] + 0.56 * (xs[1] - xs[0])
        y0 = ys[0] + 0.56 * (ys[1] - ys[0])
        x1 = xs[0] + 0.69 * (xs[1] - xs[0])
        y1 = ys[0] + 0.69 * (ys[1] - ys[0])
        ax.annotate(
            "",
            xy=(x1, y1),
            xytext=(x0, y0),
            arrowprops={"arrowstyle": "-|>", "color": color, "lw": 0.8, "alpha": alpha},
            zorder=15,
        )


def build_trajectory_figures(rows: list[dict[str, Any]]) -> dict[str, Any]:
    builder = load_module(S3_VISUAL_BUILDER, "deck_s3_visual_builder")
    exporter = builder.load_exporter()
    xz, _ = builder.projected_segments(exporter, ("x", "z"))
    xy, _ = builder.projected_segments(exporter, ("x", "y"))

    combined = ASSETS / "s3_w2_final_trajectory_overlay.png"
    fig, axes = plt.subplots(1, 2, figsize=(15.8, 7.0))
    for ax, segs, plane, title, xlabel, ylabel in (
        (axes[0], xz, "xz", "World X–Z", "x [cm]", "z [cm]"),
        (axes[1], xy, "xy", "World X–Y", "x [cm]", "y [cm]"),
    ):
        add_geometry(ax, builder, exporter, segs)
        for row in sorted(rows, key=lambda item: item["source_family"] == "atm511"):
            draw_ray(ax, row, plane, arrow=False, alpha=0.52 if row["source_family"] == "atm511" else 0.82)
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
    axes[0].set_xlim(-48, 56)
    axes[0].set_ylim(-44, 62)
    axes[1].set_xlim(-52, 58)
    axes[1].set_ylim(-52, 52)
    counts = Counter(row["source_family"] for row in rows)
    handles = [
        Line2D([0], [0], color=COLORS[key], lw=2.5, label=f"{LABELS[key]}  n={counts[key]}")
        for key in ("eplus", "n", "atm511", "activation")
    ]
    axes[1].legend(handles=handles, loc="lower right", fontsize=9, framealpha=0.92)
    fig.suptitle("S3 W2 final survivors — incident chords over the S3 geometry", fontsize=16, weight="bold", y=0.985)
    fig.text(
        0.5,
        0.018,
        "True IA INIT direction → S3 outer-envelope intersection (activation: true internal origin) → energy-weighted TES centroid. "
        "Straight chords are directional proxies, not step-by-step Geant4 paths.",
        ha="center",
        fontsize=9,
        color="#4c5866",
    )
    fig.tight_layout(rect=[0, 0.072, 1, 0.94])
    fig.savefig(combined, dpi=190, bbox_inches="tight")
    plt.close(fig)

    by_component = ASSETS / "s3_w2_trajectories_by_component.png"
    fig, axes = plt.subplots(2, 2, figsize=(14.6, 12.0))
    for ax, family in zip(axes.flat, ("eplus", "n", "atm511", "activation")):
        add_geometry(ax, builder, exporter, xz)
        selected = [row for row in rows if row["source_family"] == family]
        for row in selected:
            draw_ray(ax, row, "xz", arrow=True, alpha=0.76 if family == "atm511" else 0.92)
        rate = sum(float(row["rate_cps"]) for row in selected)
        ax.set_title(f"{LABELS[family]}  ·  n={len(selected)}  ·  {rate:.5f} cps", color=COLORS[family], weight="bold")
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("z [cm]")
        ax.set_xlim(-48, 56)
        ax.set_ylim(-44, 62)
    fig.suptitle("S3 W2 directional evidence by final-background family", fontsize=17, weight="bold", y=0.988)
    fig.text(
        0.5,
        0.014,
        "Open circle: S3 outer-envelope entry (activation: internal decay origin). Filled dot: TES energy centroid. "
        "n and all direction fractions are low-count diagnostics, not precision angular distributions.",
        ha="center",
        fontsize=9,
        color="#4c5866",
    )
    fig.tight_layout(rect=[0, 0.045, 1, 0.96])
    fig.savefig(by_component, dpi=190, bbox_inches="tight")
    plt.close(fig)
    return {"combined": rel(combined), "by_component": rel(by_component)}


def build_component_share(rows: list[dict[str, Any]]) -> dict[str, Any]:
    rates = {key: sum(float(row["rate_cps"]) for row in rows if row["source_family"] == key) for key in COLORS}
    total = sum(rates.values())
    order = ["atm511", "eplus", "n", "activation"]
    path = ASSETS / "s3_w2_component_rate_share.png"
    fig, ax = plt.subplots(figsize=(9.4, 6.6), constrained_layout=True)
    wedges, _ = ax.pie(
        [rates[key] for key in order],
        colors=[COLORS[key] for key in order],
        startangle=90,
        counterclock=False,
        wedgeprops={"width": 0.36, "edgecolor": "#fbfaf6", "linewidth": 2},
    )
    ax.text(0, 0.08, f"{total:.5f}", ha="center", va="center", fontsize=24, weight="bold")
    ax.text(0, -0.14, "matched B [cps]", ha="center", va="center", fontsize=11, color="#5a6572")
    labels = [f"{LABELS[key]}  {rates[key]:.5f} cps  ({100 * rates[key] / total:.1f}%)" for key in order]
    ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(0.90, 0.5), frameon=False, fontsize=11)
    ax.set_title("S3 matched W2 residual composition", fontsize=16, weight="bold", pad=14)
    fig.text(
        0.5,
        0.02,
        "Prompt + delayed Step05 mainline, plus the nominal semi-empirical 4π ATM511 sidecar.",
        ha="center",
        fontsize=9,
        color="#4c5866",
    )
    fig.savefig(path, dpi=190, bbox_inches="tight")
    plt.close(fig)
    return {"rates_cps": rates, "total_cps": total, "figure": rel(path)}


def build_direction_share(rows: list[dict[str, Any]]) -> dict[str, Any]:
    external_families = ["eplus", "n", "atm511"]
    surface_order = ["side", "top", "bottom", "miss"]
    surface_colors = {"side": "#2AA198", "top": "#5D8CDE", "bottom": "#E07A5F", "miss": "#A0A8B3"}
    counts = {family: Counter(row["entry_surface"] for row in rows if row["source_family"] == family) for family in external_families}
    activation = Counter(row["entry_region"] for row in rows if row["source_family"] == "activation")
    path = ASSETS / "s3_w2_entry_direction_share.png"
    fig, axes = plt.subplots(1, 2, figsize=(14.5, 6.2), gridspec_kw={"width_ratios": [1.35, 1]}, constrained_layout=True)
    ax = axes[0]
    y = np.arange(len(external_families))
    left = np.zeros(len(external_families))
    for surface in surface_order:
        fractions = []
        for family in external_families:
            total = sum(counts[family].values())
            fractions.append(100.0 * counts[family].get(surface, 0) / total if total else 0.0)
        bars = ax.barh(y, fractions, left=left, color=surface_colors[surface], label=surface, height=0.56)
        for i, (bar, value) in enumerate(zip(bars, fractions)):
            if value >= 8:
                ax.text(left[i] + value / 2, bar.get_y() + bar.get_height() / 2, f"{value:.0f}%", ha="center", va="center", fontsize=9, color="white", weight="bold")
        left += np.asarray(fractions)
    ax.set_yticks(y, [f"{LABELS[f]}  n={sum(counts[f].values())}" for f in external_families])
    ax.set_xlim(0, 100)
    ax.set_xlabel("fraction of final events within each family [%]")
    ax.set_title("Outer-envelope entry surface")
    ax.legend(ncol=4, loc="lower center", bbox_to_anchor=(0.5, -0.24), frameon=False)
    ax.grid(axis="x")
    ax.invert_yaxis()

    ax = axes[1]
    origin_order = [key for key, _ in activation.most_common()]
    values = [activation[key] for key in origin_order]
    bars = ax.bar(range(len(origin_order)), values, color=COLORS["activation"], width=0.62)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.15, str(value), ha="center", va="bottom", weight="bold")
    ax.set_xticks(range(len(origin_order)), [name.replace("_", "\n") for name in origin_order])
    ax.set_ylabel("final activation events")
    ax.set_title("Activation: internal decay-origin region")
    ax.grid(axis="y")
    fig.suptitle("Where S3 W2 survivors come from", fontsize=16, weight="bold")
    fig.text(
        0.5,
        0.005,
        "Entry surfaces are finite-cylinder intersections in the 45° instrument frame. Counts: e+ 12, n 3, ATM511 56, activation 12; angular fractions are diagnostic only.",
        ha="center",
        fontsize=9,
        color="#4c5866",
    )
    fig.savefig(path, dpi=190, bbox_inches="tight")
    plt.close(fig)
    return {
        "external_entry_counts": {family: dict(counter) for family, counter in counts.items()},
        "activation_origin_counts": dict(activation),
        "figure": rel(path),
    }


def build_evolution_performance() -> dict[str, Any]:
    versions = ["Mass_511", "S1", "S3"]
    background = [0.074118455, 0.0561719, 0.0222344226]
    f3 = [5.244247e-5, 4.62986e-5, 2.852908e-5]
    colors = ["#7F8C9A", "#47B6A6", "#A66BFF"]
    path = ASSETS / "mass_s1_s3_matched_performance.png"
    fig, axes = plt.subplots(1, 2, figsize=(13.6, 5.8))
    for ax, values, ylabel, title, formatter in (
        (axes[0], background, "matched W2 background [cps]", "Background falls 70%: Mass → S3", lambda v: f"{v:.5f}"),
        (axes[1], f3, "20 d, 3σ flux [ph cm⁻² s⁻¹]", "Sensitivity improves 45.6%", lambda v: f"{v * 1e5:.2f}×10⁻⁵"),
    ):
        bars = ax.bar(versions, values, color=colors, width=0.60)
        ax.grid(axis="y")
        ax.set_ylabel(ylabel)
        ax.set_title(title, weight="bold")
        ax.set_ylim(0, max(values) * 1.24)
        for bar, value in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, value * 1.035, formatter(value), ha="center", va="bottom", fontsize=10, weight="bold")
    fig.suptitle("Matched atmospheric-511 performance evolution", fontsize=16, weight="bold", y=0.985)
    fig.text(
        0.5,
        0.018,
        "Mass and S1: retained full-chain references. S3: direct Step05 expectation + matched nominal ATM511; S3 Step06–08 not regenerated.",
        ha="center",
        fontsize=9,
        color="#4c5866",
    )
    fig.tight_layout(rect=[0, 0.075, 1, 0.92])
    fig.savefig(path, dpi=190, bbox_inches="tight")
    plt.close(fig)
    return {"versions": versions, "background_cps": background, "f3": f3, "figure": rel(path)}


def build_s3abc_screening() -> dict[str, Any]:
    versions = ["S3", "S3a", "S3b", "S3c"]
    components = {
        "eplus": [0.00950537, 0.000678454, 0.00678757, 0.00135997],
        "n": [0.000678527, 0.00271376, 0.00203630, 0.00135670],
        "atm511": [0.0108831, 0.00174823, 0.00931889, 0.00116688],
    }
    totals = [sum(components[key][i] for key in components) for i in range(len(versions))]
    f3 = [2.85291e-5, 1.51955e-5, 2.65869e-5, 1.35976e-5]
    path = ASSETS / "s3abc_dominant_screening.png"
    fig, axes = plt.subplots(1, 2, figsize=(14.5, 6.1))
    ax = axes[0]
    bottom = np.zeros(len(versions))
    for key in ("eplus", "n", "atm511"):
        values = np.asarray(components[key])
        ax.bar(versions, values, bottom=bottom, color=COLORS[key], label=LABELS[key], width=0.62)
        bottom += values
    for i, total in enumerate(totals):
        ax.text(i, total + 0.00045, f"{total:.4f}\n{total / totals[0]:.3f}×", ha="center", va="bottom", fontsize=9, weight="bold")
    ax.set_ylabel("dominant-subset final rate [cps]")
    ax.set_ylim(0, max(totals) * 1.23)
    ax.set_title("Prompt + ATM511 screening", weight="bold")
    ax.grid(axis="y")
    ax.legend(frameon=False, loc="upper right")

    ax = axes[1]
    bars = ax.bar(versions, np.asarray(f3) * 1e5, color=["#7F8C9A", "#6D77D8", "#4D96B8", "#A66BFF"], width=0.62)
    for bar, value in zip(bars, f3):
        ax.text(bar.get_x() + bar.get_width() / 2, value * 1e5 + 0.06, f"{value * 1e5:.2f}", ha="center", va="bottom", weight="bold")
    ax.set_ylabel("estimated F₃ [×10⁻⁵ ph cm⁻² s⁻¹]")
    ax.set_ylim(0, max(f3) * 1e5 * 1.22)
    ax.set_title("Background-only estimate", weight="bold")
    ax.grid(axis="y")
    fig.suptitle("S3a/b/c: BGO is the strong lever; W-only is modest", fontsize=16, weight="bold", y=0.985)
    fig.text(
        0.5,
        0.018,
        "Equal-stat dominant subset (e+, n, ATM511). F₃ keeps S3 signal and non-dominant residual fixed; not a delayed/full-chain promotion result. Neutron counts are low-stat.",
        ha="center",
        fontsize=9,
        color="#4c5866",
    )
    fig.tight_layout(rect=[0, 0.075, 1, 0.92])
    fig.savefig(path, dpi=190, bbox_inches="tight")
    plt.close(fig)
    return {"versions": versions, "components_cps": components, "totals_cps": totals, "estimated_f3": f3, "figure": rel(path)}


def write_events_csv(rows: list[dict[str, Any]]) -> Path:
    path = WORK / "s3_w2_final_trajectory_events.csv"
    fields = [
        "source_family",
        "source_file",
        "local_id",
        "tes_total_keV",
        "rate_cps",
        "init_x_cm",
        "init_y_cm",
        "init_z_cm",
        "dir_x",
        "dir_y",
        "dir_z",
        "tes_x_cm",
        "tes_y_cm",
        "tes_z_cm",
        "entry_surface",
        "entry_region",
        "entry_phi_deg_local",
        "entry_local_x_cm",
        "entry_local_y_cm",
        "entry_local_z_cm",
        "selection_scope",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return path


def main() -> int:
    chart_style()
    ASSETS.mkdir(parents=True, exist_ok=True)
    static_assets = process_static_images()
    reconstruction_cache = WORK / "s3_w2_reconstructed_trajectory_rows.json"
    if reconstruction_cache.exists():
        rows = json.loads(reconstruction_cache.read_text(encoding="utf-8"))
        print(f"reuse {rel(reconstruction_cache)} rows={len(rows)}", flush=True)
    else:
        rows = load_prompt_rows()
        rows.extend(load_delayed_rows())
        rows.extend(load_atm_rows())
        for row in rows:
            row.update(classify_entry(row))
        reconstruction_cache.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")

    counts = Counter(row["source_family"] for row in rows)
    expected = {"eplus": 12, "n": 3, "atm511": 56, "activation": 12}
    if dict(counts) != expected:
        raise RuntimeError(f"unexpected final event counts: {dict(counts)} != {expected}")
    window_violations = [row for row in rows if not (W2_MIN <= float(row["tes_total_keV"]) < W2_MAX)]
    if window_violations:
        raise RuntimeError(f"{len(window_violations)} W2 violations")

    events_csv = write_events_csv(rows)
    trajectory_figures = build_trajectory_figures(rows)
    component_share = build_component_share(rows)
    direction_share = build_direction_share(rows)
    evolution = build_evolution_performance()
    screening = build_s3abc_screening()

    summary = {
        "status": "PASS_MASS511_TO_S3_HTML_DECK_EVIDENCE",
        "generated_for": "Mass_511 to S3/S3a/S3b/S3c HTML presentation",
        "s3_geometry": rel(
            ROOT
            / "engineering/geometry_optimization_20260704/21_geoopt_s3_csi_barrel_20260709/geometry"
            / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
        ),
        "w2_window_keV": [W2_MIN, W2_MAX],
        "event_counts": dict(counts),
        "event_rates_cps": component_share["rates_cps"],
        "matched_total_background_cps": component_share["total_cps"],
        "trajectory_definition": (
            "Straight incident chord from true IA INIT origin, clipped to its first finite-cylinder S3 outer-envelope "
            "intersection for external sources, to the energy-weighted TES hit centroid. Activation starts at its true internal decay origin."
        ),
        "trajectory_caveat": "Directional proxy, not a Geant4 step-by-step particle path or a boundary-crossing scorer.",
        "entry_surface_model": {
            "frame": "instrument local, inverse world Y rotation of 45 degrees",
            "outer_radius_cm": OUTER_RADIUS_CM,
            "z_range_cm": [OUTER_ZMIN_CM, OUTER_ZMAX_CM],
            "window_center_z_cm": WINDOW_Z0_CM,
            "window_half_y_cm": WINDOW_HALF_Y_CM,
            "window_half_z_cm": WINDOW_HALF_Z_CM,
        },
        "known_side_window_truth_correction": {
            "old_packet_claim": "0/83",
            "status": "REJECTED_AS_UNAUDITABLE",
            "reason": "packet forced side-window=false for ATM511 and delayed rows with missing origins",
            "prompt_truth_preexisting": "0/15 prompt line-to-TES crossings in the packet audit",
            "this_output": "reconstructed all 83 IA INIT trajectories and finite-envelope entry proxies; does not claim exact boundary-crossing truth",
        },
        "direction_share": direction_share,
        "evolution": evolution,
        "s3abc_screening": screening,
        "static_assets": static_assets,
        "outputs": {
            "reconstruction_cache": rel(reconstruction_cache),
            "events_csv": rel(events_csv),
            "trajectory_figures": trajectory_figures,
            "component_share": component_share["figure"],
            "direction_share": direction_share["figure"],
            "evolution_performance": evolution["figure"],
            "s3abc_screening": screening["figure"],
        },
        "source_provenance": {
            "prompt": rel(PROMPT_AUDIT),
            "delayed_file_catalog": rel(DELAYED_FILE_CATALOG),
            "atm511": rel(ATM_SUMMARY),
        },
        "claim_boundaries": [
            "ATM511 is a semi-empirical 4pi sidecar, not native EXPACS.",
            "S3 matched performance is a direct Step05 expectation; S3 Step06-Step08 were not regenerated.",
            "S3a/b/c values are equal-stat dominant-background screening; delayed/full-chain promotion is pending.",
            "Focused signal uses the retained f10m A1 EventList bridge; optics hardware mass is not in prompt/delayed transport.",
        ],
    }
    summary_path = WORK / "deck_evidence_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "counts": dict(counts), "outputs": summary["outputs"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
