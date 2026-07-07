#!/usr/bin/env python3
"""Overlay all W2 background-event incident rays on the current geo-opt geometry."""

from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import os
import pickle
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Rectangle


ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
OUT = WORK / "figures"
DATA = WORK / "w2_all_particle_ray_overlay_events.csv"
SUMMARY = WORK / "w2_all_particle_ray_overlay_summary.json"
PNG = OUT / "w2_all_particle_rays_current_geo_opt_overlay.png"
SVG = OUT / "w2_all_particle_rays_current_geo_opt_overlay.svg"
BY_PARTICLE_DIR = OUT / "w2_particle_rays_current_geo_opt_by_particle"

HELPER_SCRIPT = WORK / "build_ingress_veto_audit.py"
GEO_BUILDER = ROOT / "engineering/geometry_optimization_20260704/01_geo_opt_s1_bottomw_b4c/build_geo_opt_s1_bottomw_b4c.py"
STEP05_CACHE = (
    ROOT
    / "stepwise_maintenance/step05_veto_time_axis/outputs_geo_opt_s1_bpe_w5_fullstat_v1_l1/work/event_catalog.pkl"
)
P2_ATM511_SIM = (
    ROOT
    / "runs/geometry_optimization_20260704/p2_atm511_unit_geo_opt_s1_bpe_w5_fullstat_v1"
    / "Atm511LowerUnit3M_GeoOptS1BpeW5.inc1.id1.sim.gz"
)

W2_MIN = 510.58
W2_MAX = 511.42
ACTIVE_THRESHOLD_KEV = 50.0
XY_BASE_LIMIT_CM = 45.0
XY_VIEW_SCALE = 1.5
XY_LIMIT_CM = XY_BASE_LIMIT_CM * XY_VIEW_SCALE

ID_RE = re.compile(r"^ID\s+(\d+)")
CC_HIT_RE = re.compile(r"^CC\s+HIT\s+(\S+)\s+(.*)$")
KV_RE = re.compile(r"(\w+)=([^\s]+)")
TP_RE = re.compile(r"^TP_L(?P<layer>\d+)_(?P<pix>\d+)$", re.IGNORECASE)


PARTICLE_STYLE = {
    "eplus": ("#D45D3D", "e+"),
    "n": ("#2F65B0", "n"),
    "atm511": ("#7B3FA1", "atm511"),
    "activation": ("#B05AA0", "activation"),
    "muplus": ("#4E8E2F", "mu+"),
    "muminus": ("#1B6B5A", "mu-"),
    "gamma": ("#B38B00", "gamma"),
    "p": ("#8A5A2B", "p"),
}

VETO_STYLE = {
    "pass": {"label": "not vetoed", "linestyle": "-", "marker": None, "alpha": 0.88, "lw": 1.05},
    "plastic_skin_veto": {"label": "plastic skin veto", "linestyle": (0, (1, 2.2)), "marker": "^", "alpha": 0.62, "lw": 0.95},
    "active_veto": {"label": "active veto", "linestyle": (0, (4, 2.5)), "marker": "s", "alpha": 0.62, "lw": 0.95},
    "compton_fov_veto": {"label": "Compton/FoV veto", "linestyle": (0, (3, 2, 1, 2)), "marker": "o", "alpha": 0.68, "lw": 0.95},
}


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def safe_slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "unknown"


def load_cache() -> dict[str, Any]:
    with STEP05_CACHE.open("rb") as handle:
        return pickle.load(handle)


def is_plastic_skin(vol: str) -> bool:
    return str(vol).upper().startswith("GEOOPT_S1_PLASTICFULLWRAP")


def is_other_active(vol: str, helper: Any) -> bool:
    if is_plastic_skin(vol):
        return False
    upper = str(vol).upper()
    return upper.startswith("CSI_") or "ACTIVE_SHIELD" in upper or "CEBR3" in upper or "BGO" in upper


def parse_hit(line: str, helper: Any) -> dict[str, Any] | None:
    match = CC_HIT_RE.match(line)
    if match is None:
        return None
    vol = match.group(1)
    kv = dict(KV_RE.findall(match.group(2)))
    out: dict[str, Any] = {"volume": vol, "category": helper.volume_category(vol)}
    for key in ("edep_keV", "x", "y", "z", "t"):
        if key in kv:
            try:
                out[key] = float(kv[key])
            except ValueError:
                pass
    return out


def cache_event_hits(cat: dict[str, Any], idx: int) -> list[Any]:
    start = int(cat["pix_start"][idx])
    count = int(cat["pix_count"][idx])
    hits = []
    for j in range(start, start + count):
        hits.append(
            SimpleNamespace(
                x=float(cat["pix_x"][j]),
                y=float(cat["pix_y"][j]),
                z=float(cat["pix_z"][j]),
                e=float(cat["pix_e"][j]),
                pixel_uid=str(cat["pix_uid"][j]),
                layer=int(cat["pix_layer"][j]),
            )
        )
    return hits


def tes_centroid_from_cache(cat: dict[str, Any], idx: int) -> tuple[float | None, float | None, float | None]:
    hits = cache_event_hits(cat, idx)
    total = sum(float(h.e) for h in hits)
    if total <= 0:
        return None, None, None
    return (
        sum(float(h.e) * float(h.x) for h in hits) / total,
        sum(float(h.e) * float(h.y) for h in hits) / total,
        sum(float(h.e) * float(h.z) for h in hits) / total,
    )


def collect_energy_metadata(targets_by_file: dict[str, set[int]], helper: Any) -> dict[tuple[str, int], dict[str, Any]]:
    records: dict[tuple[str, int], dict[str, Any]] = {}
    for source_file, ids in sorted(targets_by_file.items()):
        path = Path(source_file)
        if not path.is_absolute():
            path = ROOT / path
        remaining = set(ids)
        cur_id: int | None = None
        interested = False
        rec: dict[str, Any] | None = None

        def flush() -> None:
            nonlocal cur_id, interested, rec
            if interested and cur_id is not None and rec is not None:
                records[(rel(path), int(cur_id))] = rec
                remaining.discard(int(cur_id))
            cur_id = None
            interested = False
            rec = None

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
                    rec = {
                        "init": None,
                        "plastic_skin_keV": 0.0,
                        "active_other_keV": 0.0,
                        "first_hit_volume": None,
                        "first_hit_category": None,
                        "first_hit_x_cm": None,
                        "first_hit_y_cm": None,
                        "first_hit_z_cm": None,
                    } if interested else None
                    continue
                if not interested or rec is None:
                    continue
                if line.startswith("IA INIT"):
                    rec["init"] = helper.parse_ia_init(line)
                    continue
                if not line.startswith("CC HIT "):
                    continue
                hit = parse_hit(line, helper)
                if hit is None:
                    continue
                vol = str(hit["volume"])
                edep = float(hit.get("edep_keV") or 0.0)
                if rec.get("first_hit_volume") is None:
                    rec["first_hit_volume"] = vol
                    rec["first_hit_category"] = hit.get("category")
                    rec["first_hit_x_cm"] = hit.get("x")
                    rec["first_hit_y_cm"] = hit.get("y")
                    rec["first_hit_z_cm"] = hit.get("z")
                if is_plastic_skin(vol):
                    rec["plastic_skin_keV"] += edep
                elif is_other_active(vol, helper):
                    rec["active_other_keV"] += edep
            flush()
        if remaining:
            raise RuntimeError(f"missing {len(remaining)} selected events in {path}: {sorted(remaining)[:10]}")
    return records


def classify_veto(row: dict[str, Any]) -> str:
    if float(row.get("plastic_skin_keV") or 0.0) >= ACTIVE_THRESHOLD_KEV:
        return "plastic_skin_veto"
    if float(row.get("active_other_keV") or 0.0) >= ACTIVE_THRESHOLD_KEV:
        return "active_veto"
    if not bool(row.get("side_compton_fov_pass")):
        return "compton_fov_veto"
    return "pass"


def prompt_and_delayed_rows(helper: Any, step05: Any, disk: dict[str, Any]) -> list[dict[str, Any]]:
    cat = load_cache()
    stream = np.asarray(cat["stream"], dtype=object)
    tag = np.asarray(cat["tag"], dtype=object)
    tes = np.asarray(cat["tes_total_keV"], dtype=np.float64)
    mask = (stream != "science") & (tes >= W2_MIN) & (tes < W2_MAX)
    indices = [int(i) for i in np.flatnonzero(mask)]

    targets_by_file: dict[str, set[int]] = defaultdict(set)
    for idx in indices:
        targets_by_file[str(cat["source_file"][idx])].add(int(cat["local_id"][idx]))
    metadata = collect_energy_metadata(targets_by_file, helper)

    rows: list[dict[str, Any]] = []
    for idx in indices:
        src = rel(str(cat["source_file"][idx]))
        local_id = int(cat["local_id"][idx])
        meta = metadata[(src, local_id)]
        hits = cache_event_hits(cat, idx)
        keep, side_cls = step05.side_keep_from_hits(hits, disk, "keep")
        tx, ty, tz = tes_centroid_from_cache(cat, idx)
        init = meta.get("init") or {}
        row = {
            "source_family": str(tag[idx]),
            "stream": str(stream[idx]),
            "source_file": src,
            "local_id": local_id,
            "tes_total_keV": float(cat["tes_total_keV"][idx]),
            "combined_active_keV_from_step05": float(cat["bgo_total_keV"][idx]),
            "plastic_skin_keV": float(meta.get("plastic_skin_keV") or 0.0),
            "active_other_keV": float(meta.get("active_other_keV") or 0.0),
            "side_compton_class": side_cls,
            "side_compton_fov_pass": bool(keep),
            "tes_x_cm": tx,
            "tes_y_cm": ty,
            "tes_z_cm": tz,
            "init_x_cm": init.get("init_x_cm"),
            "init_y_cm": init.get("init_y_cm"),
            "init_z_cm": init.get("init_z_cm"),
            "dir_x": init.get("dir_x"),
            "dir_y": init.get("dir_y"),
            "dir_z": init.get("dir_z"),
            "init_energy_keV": init.get("init_energy_keV"),
            "first_hit_volume": meta.get("first_hit_volume"),
            "first_hit_category": meta.get("first_hit_category"),
            "source_scope": "current_geo_opt_prompt_or_delayed",
        }
        row["veto_class"] = classify_veto(row)
        rows.append(row)
    return rows


def atm511_rows(helper: Any, step05: Any, disk: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cur_id: int | None = None
    init: dict[str, Any] | None = None
    first_hit: dict[str, Any] | None = None
    tes_total = 0.0
    plastic = 0.0
    active_other = 0.0
    pix: dict[str, dict[str, Any]] = {}

    def event_hits() -> list[Any]:
        hits = []
        for uid, rec in sorted(pix.items()):
            e = float(rec["e"])
            if e <= 0:
                continue
            hits.append(
                SimpleNamespace(
                    x=float(rec["wx"] / e),
                    y=float(rec["wy"] / e),
                    z=float(rec["wz"] / e),
                    e=e,
                    pixel_uid=uid,
                    layer=int(rec["layer"]),
                )
            )
        return hits

    def centroid() -> tuple[float | None, float | None, float | None]:
        hits = event_hits()
        total = sum(float(h.e) for h in hits)
        if total <= 0:
            return None, None, None
        return (
            sum(float(h.e) * float(h.x) for h in hits) / total,
            sum(float(h.e) * float(h.y) for h in hits) / total,
            sum(float(h.e) * float(h.z) for h in hits) / total,
        )

    def flush() -> None:
        nonlocal cur_id, init, first_hit, tes_total, plastic, active_other, pix
        if cur_id is None:
            return
        if W2_MIN <= tes_total < W2_MAX:
            hits = event_hits()
            keep, side_cls = step05.side_keep_from_hits(hits, disk, "keep")
            tx, ty, tz = centroid()
            init_rec = init or {}
            row = {
                "source_family": "atm511",
                "stream": "atm511_replay",
                "source_file": rel(P2_ATM511_SIM),
                "local_id": int(cur_id),
                "tes_total_keV": float(tes_total),
                "combined_active_keV_from_step05": float(plastic + active_other),
                "plastic_skin_keV": float(plastic),
                "active_other_keV": float(active_other),
                "side_compton_class": side_cls,
                "side_compton_fov_pass": bool(keep),
                "tes_x_cm": tx,
                "tes_y_cm": ty,
                "tes_z_cm": tz,
                "init_x_cm": init_rec.get("init_x_cm"),
                "init_y_cm": init_rec.get("init_y_cm"),
                "init_z_cm": init_rec.get("init_z_cm"),
                "dir_x": init_rec.get("dir_x"),
                "dir_y": init_rec.get("dir_y"),
                "dir_z": init_rec.get("dir_z"),
                "init_energy_keV": init_rec.get("init_energy_keV"),
                "first_hit_volume": None if first_hit is None else first_hit.get("volume"),
                "first_hit_category": None if first_hit is None else first_hit.get("category"),
                "source_scope": "atm511_p2_replay",
            }
            row["veto_class"] = classify_veto(row)
            rows.append(row)
        cur_id = None
        init = None
        first_hit = None
        tes_total = 0.0
        plastic = 0.0
        active_other = 0.0
        pix = {}

    with gzip.open(P2_ATM511_SIM, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if line == "SE":
                flush()
                continue
            match_id = ID_RE.match(line)
            if match_id:
                cur_id = int(match_id.group(1))
                continue
            if cur_id is None:
                continue
            if line.startswith("IA INIT"):
                init = helper.parse_ia_init(line)
                continue
            if not line.startswith("CC HIT "):
                continue
            hit = parse_hit(line, helper)
            if hit is None:
                continue
            if first_hit is None:
                first_hit = hit
            vol = str(hit["volume"])
            edep = float(hit.get("edep_keV") or 0.0)
            match_tp = TP_RE.match(vol)
            if match_tp:
                rec = pix.setdefault(vol, {"e": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0, "layer": int(match_tp.group("layer"))})
                rec["e"] += edep
                rec["wx"] += edep * float(hit.get("x") or 0.0)
                rec["wy"] += edep * float(hit.get("y") or 0.0)
                rec["wz"] += edep * float(hit.get("z") or 0.0)
                tes_total += edep
            elif is_plastic_skin(vol):
                plastic += edep
            elif is_other_active(vol, helper):
                active_other += edep
        flush()
    return rows


def ray_start(row: dict[str, Any]) -> tuple[float | None, float | None, float | None]:
    vals = (row.get("init_x_cm"), row.get("init_y_cm"), row.get("init_z_cm"))
    if any(v is None for v in vals):
        return None, None, None
    return float(vals[0]), float(vals[1]), float(vals[2])


def ray_end(row: dict[str, Any]) -> tuple[float | None, float | None, float | None]:
    vals = (row.get("tes_x_cm"), row.get("tes_y_cm"), row.get("tes_z_cm"))
    if any(v is None for v in vals):
        return None, None, None
    return float(vals[0]), float(vals[1]), float(vals[2])


def plot_ray(ax: Any, row: dict[str, Any], plane: str) -> None:
    start = ray_start(row)
    end = ray_end(row)
    if start[0] is None or end[0] is None:
        return
    family = str(row["source_family"])
    color = PARTICLE_STYLE.get(family, ("#555555", family))[0]
    style = VETO_STYLE[str(row["veto_class"])]
    if plane == "xz":
        xs = [start[0], end[0]]
        ys = [start[2], end[2]]
    else:
        xs = [start[0], end[0]]
        ys = [start[1], end[1]]
    ax.plot(
        xs,
        ys,
        color=color,
        linestyle=style["linestyle"],
        linewidth=style["lw"],
        alpha=style["alpha"],
        marker=style["marker"],
        markevery=[1] if style["marker"] else None,
        markersize=4.0 if style["marker"] else 0,
        markerfacecolor=color,
        markeredgecolor="#111111",
        markeredgewidth=0.35,
        zorder=12 if row["veto_class"] == "pass" else 10,
        clip_on=True,
    )


def draw_geometry_base(geo_builder: Any, ray_scope: str) -> tuple[Any, Any]:
    module = geo_builder.load_exporter()
    xz = geo_builder.projected_segments(module, ("x", "z"))
    xy = geo_builder.projected_segments(module, ("x", "y"))
    fig, axes = plt.subplots(1, 2, figsize=(18.2, 8.2), gridspec_kw={"width_ratios": [1.05, 1.0]})
    ax_xz, ax_xy = axes
    geo_builder.add_segments(ax_xz, module, xz)
    geo_builder.add_segments(ax_xy, module, xy)

    ax_xz.set_title(f"X-Z detail projection with {ray_scope}", fontsize=12)
    ax_xz.set_xlabel("x [cm]")
    ax_xz.set_ylabel("z [cm]")
    ax_xz.set_xlim(-45, 45)
    ax_xz.set_ylim(-34, 32)
    ax_xz.set_aspect("equal", adjustable="box")
    ax_xz.grid(alpha=0.20)
    ax_xz.axhline(-5.2, color="black", ls="--", lw=0.7, alpha=0.45)
    ax_xz.add_patch(
        Rectangle(
            (-geo_builder.BPE_ROUT_CM, geo_builder.SIGNAL_WINDOW_Z_CM - geo_builder.SIGNAL_WINDOW_CUT_HALF_Z_CM),
            geo_builder.BPE_ROUT_CM,
            2.0 * geo_builder.SIGNAL_WINDOW_CUT_HALF_Z_CM,
            fill=False,
            edgecolor="#6f8f00",
            linewidth=1.2,
            linestyle="--",
        )
    )
    ax_xz.add_patch(
        Rectangle(
            (-geo_builder.W_BAFFLE_ROUT_CM, geo_builder.W_BAFFLE_ZMIN_CM),
            2.0 * geo_builder.W_BAFFLE_ROUT_CM,
            geo_builder.W_BAFFLE_THICKNESS_CM,
            fill=False,
            edgecolor="black",
            linewidth=1.4,
        )
    )

    ax_xy.set_title(f"X-Y projection, 1.5x axis view with {ray_scope}", fontsize=12)
    ax_xy.set_xlabel("x [cm]")
    ax_xy.set_ylabel("y [cm]")
    ax_xy.set_xlim(-XY_LIMIT_CM, XY_LIMIT_CM)
    ax_xy.set_ylim(-XY_LIMIT_CM, XY_LIMIT_CM)
    ax_xy.set_aspect("equal", adjustable="box")
    ax_xy.grid(alpha=0.20)
    ax_xy.add_patch(Circle((0, 0), geo_builder.PLASTIC_RIN_CM, fill=False, edgecolor="#0099bb", lw=0.9, ls=":"))
    ax_xy.add_patch(Circle((0, 0), geo_builder.PLASTIC_ROUT_CM, fill=False, edgecolor="#0099bb", lw=1.3))
    ax_xy.add_patch(Circle((0, 0), geo_builder.BPE_RIN_CM, fill=False, edgecolor="#6f8f00", lw=0.9, ls=":"))
    ax_xy.add_patch(Circle((0, 0), geo_builder.BPE_ROUT_CM, fill=False, edgecolor="#6f8f00", lw=1.2))
    ax_xy.add_patch(Circle((0, 0), geo_builder.W_BAFFLE_ROUT_CM, fill=False, edgecolor="black", lw=1.3))
    ax_xy.add_patch(
        Rectangle(
            (-geo_builder.BPE_ROUT_CM, -geo_builder.SIGNAL_WINDOW_CUT_HALF_Y_CM),
            geo_builder.BPE_ROUT_CM,
            2.0 * geo_builder.SIGNAL_WINDOW_CUT_HALF_Y_CM,
            fill=False,
            edgecolor="#6f8f00",
            linewidth=1.1,
            linestyle="--",
        )
    )
    ax_xy.add_patch(Circle((0, 0), geo_builder.TOP_SERVICE_OPENING_RIN_CM, fill=False, edgecolor="#444444", lw=0.8, ls="--"))
    return fig, axes


def add_legends(fig: Any, axes: Any, rows: list[dict[str, Any]], suptitle: str) -> None:
    particle_counts = Counter(str(r["source_family"]) for r in rows)
    particle_handles = []
    for family, count in sorted(particle_counts.items(), key=lambda item: (-item[1], item[0])):
        color, label = PARTICLE_STYLE.get(family, ("#555555", family))
        particle_handles.append(Line2D([0], [0], color=color, lw=2.0, label=f"{label} ({count})"))
    veto_counts = Counter(str(r["veto_class"]) for r in rows)
    veto_handles = []
    for veto, spec in VETO_STYLE.items():
        if veto_counts.get(veto, 0) == 0:
            continue
        veto_handles.append(
            Line2D(
                [0],
                [0],
                color="#222222",
                lw=1.6,
                linestyle=spec["linestyle"],
                marker=spec["marker"],
                markersize=5 if spec["marker"] else 0,
                label=f"{spec['label']} ({veto_counts[veto]})",
            )
        )
    axes[0].legend(handles=particle_handles[:8], loc="lower left", fontsize=7.5, framealpha=0.88, title="Particle color")
    axes[1].legend(handles=veto_handles, loc="lower left", fontsize=8, framealpha=0.88, title="Line style / veto")
    fig.suptitle(suptitle, fontsize=14, y=0.985)
    fig.text(
        0.5,
        0.945,
        f"X-Y axes expanded from ±{XY_BASE_LIMIT_CM:g} cm to ±{XY_LIMIT_CM:g} cm. "
        "Particle color encodes source family; solid means not vetoed. Dashed/dotted rays mark first veto class: plastic skin, non-plastic active shield, or Compton/FoV.",
        ha="center",
        va="top",
        fontsize=9,
        color="#444444",
    )


def build_plot(
    rows: list[dict[str, Any]],
    geo_builder: Any,
    png_path: Path,
    svg_path: Path,
    suptitle: str,
    ray_scope: str,
) -> None:
    png_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = draw_geometry_base(geo_builder, ray_scope)
    # Draw vetoed events first and survivors last so retained events remain visible.
    ordered = sorted(rows, key=lambda r: 1 if r["veto_class"] == "pass" else 0)
    for row in ordered:
        plot_ray(axes[0], row, "xz")
        plot_ray(axes[1], row, "xy")
    add_legends(fig, axes, rows, suptitle)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig(png_path, dpi=220)
    fig.savefig(svg_path)
    plt.close(fig)


def build_plots(rows: list[dict[str, Any]], geo_builder: Any) -> dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    build_plot(
        rows,
        geo_builder,
        PNG,
        SVG,
        "Current geo-opt geometry: all W2 background raw TES events as incident rays",
        "all W2 background-event rays",
    )
    per_particle: dict[str, dict[str, Any]] = {}
    for family in sorted({str(r["source_family"]) for r in rows}):
        family_rows = [r for r in rows if str(r["source_family"]) == family]
        slug = safe_slug(family)
        png = BY_PARTICLE_DIR / f"w2_particle_rays_current_geo_opt_{slug}.png"
        svg = BY_PARTICLE_DIR / f"w2_particle_rays_current_geo_opt_{slug}.svg"
        _, label = PARTICLE_STYLE.get(family, ("#555555", family))
        build_plot(
            family_rows,
            geo_builder,
            png,
            svg,
            f"Current geo-opt geometry: W2 {label} raw TES events as incident rays",
            f"W2 {label} event rays",
        )
        per_particle[family] = {
            "count": len(family_rows),
            "png": rel(png),
            "svg": rel(svg),
        }
    return {
        "combined_png": rel(PNG),
        "combined_svg": rel(SVG),
        "by_particle_dir": rel(BY_PARTICLE_DIR),
        "by_particle": per_particle,
    }


def main() -> int:
    helper = load_module(HELPER_SCRIPT, "ray_overlay_helpers")
    geo_builder = load_module(GEO_BUILDER, "ray_overlay_geo_builder")
    step05 = helper.load_step05_module()
    disk = step05.side_entry_disk()
    rows = prompt_and_delayed_rows(helper, step05, disk)
    rows.extend(atm511_rows(helper, step05, disk))
    rows = [r for r in rows if ray_start(r)[0] is not None and ray_end(r)[0] is not None]
    fields = [
        "source_family",
        "stream",
        "source_file",
        "local_id",
        "veto_class",
        "tes_total_keV",
        "plastic_skin_keV",
        "active_other_keV",
        "side_compton_class",
        "side_compton_fov_pass",
        "init_x_cm",
        "init_y_cm",
        "init_z_cm",
        "dir_x",
        "dir_y",
        "dir_z",
        "init_energy_keV",
        "tes_x_cm",
        "tes_y_cm",
        "tes_z_cm",
        "first_hit_volume",
        "first_hit_category",
        "source_scope",
    ]
    write_csv(DATA, rows, fields)
    plot_outputs = build_plots(rows, geo_builder)

    summary = {
        "status": "PASS_W2_ALL_PARTICLE_RAY_OVERLAY",
        "scope": "Current geo-opt W2 background raw TES events; science focused signal excluded.",
        "w2_window_keV": [W2_MIN, W2_MAX],
        "active_threshold_keV": ACTIVE_THRESHOLD_KEV,
        "xy_axis_view": {
            "base_half_range_cm": XY_BASE_LIMIT_CM,
            "scale": XY_VIEW_SCALE,
            "new_half_range_cm": XY_LIMIT_CM,
        },
        "particle_counts": dict(sorted(Counter(str(r["source_family"]) for r in rows).items())),
        "veto_counts": dict(sorted(Counter(str(r["veto_class"]) for r in rows).items())),
        "outputs": {
            "png": rel(PNG),
            "svg": rel(SVG),
            "events_csv": rel(DATA),
            "plot_outputs": plot_outputs,
        },
        "notes": [
            "Plastic skin veto is separated from non-plastic active veto by rescanning selected SIM hit volumes.",
            "Veto class priority is plastic skin, then non-plastic active shield, then Compton/FoV, then pass.",
            "Prompt/delayed rows come from Step05 event_catalog W2 background records; atmospheric 511 rows come from a scan of the P2 atmospheric-511 replay SIM.",
            "Rays are drawn from IA INIT position to the energy-weighted TES hit centroid in the simulation/world coordinate projections.",
        ],
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
