#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a day-15 background report from the completed 2605 production runs.

The script is intentionally read-only with respect to simulation products.  It
parses the existing prompt instant SIM files and the fixed delayed SIM file,
applies the same event-level TES/BGO selection used in the old 2602 workflow,
adds a compact Compton/FoV veto estimate in the 480-550 keV window, and writes
figures plus a PDF report.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import multiprocessing as mp
import re
import textwrap
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.font_manager import FontProperties, fontManager
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTDIR = ROOT / "outputs" / "reports" / "day15_pdf_report"
PROMPT_DIR = ROOT / "runs" / "step02_instant_equiv2602_aligned"
DELAY_DIR = ROOT / "runs" / "step02_delayed_transport_equiv2602_aligned"
DELAY_FIX_DIR = ROOT / "runs" / "step02_delay_fix_equiv2602_aligned"
DECAY_DIR = ROOT / "runs" / "step02_decay_source_equiv2602_aligned"
BOUNDS_PATH = ROOT / "outputs" / "geometry" / "XZTES_ADR_v4c_mkflange_cm" / "bounds.json"
PRODUCTION_STATUS = ROOT / "outputs" / "reports" / "production_ADR_status.md"
SCIENCE_SUMMARY = ROOT / "outputs" / "reports" / "science_511_ADR_100k" / "science_511_100k_summary.json"
SCIENCE_LEDGER = ROOT / "config" / "science_511_onaxis_source" / "metadata" / "science_rate_ledger.csv"
FLUX_CLOSURE = ROOT / "expacs_fullsphere_20bin_sources" / "flux_closure_audit.csv"
ACTIVATION_INVENTORY = DECAY_DIR / "activation_inventory_day15.csv"
FIX_SUMMARY = DELAY_FIX_DIR / "source_fix_summary.json"
FIX_ACTIONS = DELAY_FIX_DIR / "removed_or_rescaled_sources.csv"
FIXED_DELAY_SIM = DELAY_DIR / "DelayedDecayRPIPGroundStateFixed.inc1.id1.sim.gz"

ME_KEV = 511.0
BE_WINDOW_Z_CM = 12.8425
BE_WINDOW_R_CM = 1.898
PIX_HALF_X_CM = 0.075
PIX_HALF_Y_CM = 0.075
PIX_HALF_Z_CM = 0.150
N_CONE_SAMPLES_STATS = 24
MAX_ABS_XY_STATS_CM = 8.0
MAX_ENUM_HITS = 6

TAG_RE = re.compile(r"Background_(?P<tag>[^_]+)_", re.IGNORECASE)


def is_active_veto_volume(vol: str) -> bool:
    upper = str(vol).upper()
    return ("BGO" in upper) or ("ACTIVE_SHIELD" in upper) or ("CEBR3" in upper)


def active_veto_volume_name() -> str:
    bounds = load_json(BOUNDS_PATH, {})
    active = bounds.get("ACTIVE_SHIELD", {}) if isinstance(bounds, dict) else {}
    return str(active.get("name") or "active shield")


@dataclass
class EventHit:
    x: float
    y: float
    z: float
    e: float
    pixel_uid: str
    layer: int


def nested_float_dict():
    return defaultdict(float)


def setup_fonts() -> FontProperties:
    font_path = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
    bold_path = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
    if font_path.exists():
        fontManager.addfont(str(font_path))
        plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "DejaVu Sans"]
        plt.rcParams["font.family"] = "sans-serif"
    if bold_path.exists():
        fontManager.addfont(str(bold_path))
    plt.rcParams["axes.unicode_minus"] = False
    return FontProperties(fname=str(font_path)) if font_path.exists() else FontProperties()


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))


def load_bounds(path: Path) -> dict:
    txt = path.read_text(encoding="utf-8", errors="ignore").strip()
    return json.loads(txt)


def in_shell(r: float, z: float, s: dict) -> bool:
    if s["z_out_bot"] <= z <= s["z_in_bot"] and r <= s["r_out"]:
        return True
    if s["z_in_bot"] <= z <= s["z_in_top"] and (s["r_in"] <= r <= s["r_out"]):
        return True
    hole = s.get("hole_r", s.get("hole", s["r_in"]))
    if s["z_in_top"] <= z <= s["z_out_top"] and (hole <= r <= s["r_out"]):
        return True
    return False


def identify_vol(x: float, y: float, z: float, bounds: dict) -> str:
    r = math.hypot(x, y)
    for name in ("CU_BASE", "CU_SUPPORT"):
        obj = bounds.get(name)
        if obj and obj["z_bot"] <= z <= obj["z_top"] and r <= obj["r_max"]:
            return "Copper"
    for i, t in enumerate(bounds.get("TES_LAYERS", [])):
        if abs(z - t["z_center"]) <= (t["hz"] + 0.05) and r <= (t["r_max"] + 0.05):
            return f"TES_L{i}"
    for w in bounds.get("WINDOWS", []):
        if abs(z - w["z_center"]) <= (w["thick"] / 2.0 + 0.01) and r <= w["r_max"]:
            return "Window"
    c = bounds.get("COLLIMATOR")
    if c and abs(z - c["z_center"]) <= (c["hz"] + 0.01) and r <= c["r_max"]:
        return "Collimator"
    for name, s in bounds.get("SHIELDS", {}).items():
        if in_shell(r, z, s):
            return name
    return "Other"


def parse_tag(path: str) -> str:
    m = TAG_RE.search(Path(path).name)
    return m.group("tag").lower() if m else "unknown"


def prompt_file_weight(path: str) -> float:
    return 1.0 if parse_tag(path) == "gamma" else 1.0 / 8.0


def open_text(path: str):
    return gzip.open(path, "rt", encoding="utf-8", errors="ignore") if path.endswith(".gz") else open(path, "rt", encoding="utf-8", errors="ignore")


def parse_htsim(line: str):
    try:
        parts = line.split(";", 5)
        return float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
    except Exception:
        return None


def representative_points_box(hit: EventHit):
    pts = []
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            for sz in (-1.0, 1.0):
                pts.append([hit.x + sx * PIX_HALF_X_CM, hit.y + sy * PIX_HALF_Y_CM, hit.z + sz * PIX_HALF_Z_CM])
    pts.append([hit.x, hit.y, hit.z])
    return np.asarray(pts, dtype=float)


def unit(v: np.ndarray):
    n = float(np.linalg.norm(v))
    return None if n <= 0 else v / n


def compton_cos_theta(e_first: float, e_second: float) -> float:
    e0 = e_first + e_second
    ep = e_second
    if e0 <= 0 or ep <= 0:
        return float("nan")
    return 1.0 - ME_KEV * (1.0 / ep - 1.0 / e0)


def _orthonormal_basis_batch(axis_hat: np.ndarray):
    ref = np.zeros_like(axis_hat)
    mask = np.abs(axis_hat[:, 2]) < 0.9
    ref[mask] = np.array([0.0, 0.0, 1.0])
    ref[~mask] = np.array([1.0, 0.0, 0.0])
    e1 = np.cross(axis_hat, ref)
    n1 = np.linalg.norm(e1, axis=1)
    valid1 = n1 > 1.0e-12
    e1[valid1] /= n1[valid1, None]
    e2 = np.cross(axis_hat, e1)
    n2 = np.linalg.norm(e2, axis=1)
    valid2 = n2 > 1.0e-12
    e2[valid2] /= n2[valid2, None]
    return e1, e2, valid1 & valid2


def curve_intersects_disk(points: np.ndarray, radius: float) -> bool:
    if len(points) == 0:
        return False
    r2 = points[:, 0] * points[:, 0] + points[:, 1] * points[:, 1]
    return bool(np.any(r2 <= radius * radius))


def segments_intersect_disk(segments: np.ndarray, radius: float) -> bool:
    if segments is None or len(segments) == 0:
        return False
    p0 = segments[:, 0, :2]
    p1 = segments[:, 1, :2]
    d = p1 - p0
    a = np.sum(d * d, axis=1)
    t = np.zeros(len(segments), dtype=float)
    nz = a > 1.0e-18
    if np.any(nz):
        t[nz] = -np.sum(p0[nz] * d[nz], axis=1) / a[nz]
        t[nz] = np.clip(t[nz], 0.0, 1.0)
    closest = p0 + t[:, None] * d
    r2 = np.sum(closest * closest, axis=1)
    return bool(np.any(r2 <= radius * radius))


def sample_cone_plane(hit1: EventHit, hit2: EventHit, e_first: float, e_second: float):
    ctheta = compton_cos_theta(e_first, e_second)
    if (not np.isfinite(ctheta)) or ctheta < -1.0 or ctheta > 1.0:
        return False, False
    theta = math.acos(float(np.clip(ctheta, -1.0, 1.0)))
    reps1 = representative_points_box(hit1)
    reps2 = representative_points_box(hit2)
    p1 = np.repeat(reps1, len(reps2), axis=0)
    p2 = np.tile(reps2, (len(reps1), 1))
    # The measured second hit defines the scattered-photon direction p1->p2.
    # Source/FoV testing needs the back-projected incident ray, so the cone
    # axis points from the first hit back toward the source plane.
    axis_vec = p1 - p2
    norms = np.linalg.norm(axis_vec, axis=1)
    valid_norm = norms > 1.0e-12
    if not np.any(valid_norm):
        return True, False
    p1 = p1[valid_norm]
    axis_hat = axis_vec[valid_norm] / norms[valid_norm, None]
    e1, e2, valid_basis = _orthonormal_basis_batch(axis_hat)
    if not np.any(valid_basis):
        return True, False
    p1 = p1[valid_basis]
    axis_hat = axis_hat[valid_basis]
    e1 = e1[valid_basis]
    e2 = e2[valid_basis]

    phis = np.linspace(0.0, 2.0 * math.pi, N_CONE_SAMPLES_STATS, endpoint=False)
    dirs = (
        math.cos(theta) * axis_hat[:, None, :]
        + math.sin(theta)
        * (np.cos(phis)[None, :, None] * e1[:, None, :] + np.sin(phis)[None, :, None] * e2[:, None, :])
    )
    dz = dirs[:, :, 2]
    valid_dz = np.abs(dz) > 1.0e-12
    z0 = np.broadcast_to(p1[:, 2][:, None], dz.shape)
    t = np.full(dz.shape, np.nan, dtype=float)
    t[valid_dz] = (BE_WINDOW_Z_CM - z0[valid_dz]) / dz[valid_dz]
    valid = valid_dz & (t > 0) & np.isfinite(t)
    points = p1[:, None, :] + np.where(valid, t, 0.0)[:, :, None] * dirs
    valid_xy = (np.abs(points[:, :, 0]) <= MAX_ABS_XY_STATS_CM) & (np.abs(points[:, :, 1]) <= MAX_ABS_XY_STATS_CM)
    valid = valid & valid_xy
    points[~valid] = np.nan

    curves = []
    segs = []
    for i in range(points.shape[0]):
        pts_i = points[i]
        valid_i = valid[i]
        if np.any(valid_i):
            curves.append(pts_i[valid_i])
        seg_mask = valid_i & np.roll(valid_i, -1)
        idx = np.where(seg_mask)[0]
        if len(idx):
            segs.append(np.stack([pts_i[idx], pts_i[(idx + 1) % len(valid_i)]], axis=1))
    flat_points = np.vstack(curves) if curves else np.empty((0, 3), dtype=float)
    flat_segments = np.concatenate(segs, axis=0) if segs else np.empty((0, 2, 3), dtype=float)
    if len(flat_points) == 0 and len(flat_segments) == 0:
        return True, False
    intersects = curve_intersects_disk(flat_points, BE_WINDOW_R_CM) or segments_intersect_disk(flat_segments, BE_WINDOW_R_CM)
    return True, bool(intersects)


def classify_hit2(hits: list[EventHit]) -> str:
    h1, h2 = hits[0], hits[1]
    decisions = []
    for a, b in ((h1, h2), (h2, h1)):
        ok, intersects = sample_cone_plane(a, b, a.e, b.e)
        if ok:
            decisions.append(intersects)
    if not decisions:
        return "reject"
    return "keep" if any(decisions) else "veto"


def sequence_metrics(ordered: list[EventHit]):
    n = len(ordered)
    energies = np.asarray([h.e for h in ordered], dtype=float)
    positions = np.asarray([[h.x, h.y, h.z] for h in ordered], dtype=float)
    if np.any(~np.isfinite(energies)) or np.any(energies <= 0):
        return None
    total_e = float(np.sum(energies))
    rem_after = total_e - np.cumsum(energies)
    cos_kin = []
    theta1 = None
    for i in range(n - 1):
        if rem_after[i] <= 0:
            return None
        c = compton_cos_theta(float(energies[i]), float(rem_after[i]))
        if (not np.isfinite(c)) or c < -1.0 or c > 1.0:
            return None
        cos_kin.append(float(c))
        if i == 0:
            theta1 = math.degrees(math.acos(float(np.clip(c, -1.0, 1.0))))
    qf_terms = []
    for i in range(1, n - 1):
        u_prev = unit(positions[i] - positions[i - 1])
        u_next = unit(positions[i + 1] - positions[i])
        if u_prev is None or u_next is None:
            return None
        qf_terms.append((cos_kin[i] - float(np.dot(u_prev, u_next))) ** 2)
    return {
        "qf": float(np.sum(qf_terms)) if qf_terms else 0.0,
        "first_lever_arm": float(np.linalg.norm(positions[1] - positions[0])),
        "e_first": float(energies[0]),
        "e_after1": float(rem_after[0]),
        "theta1": float(theta1) if theta1 is not None else float("nan"),
    }


def classify_hit3plus(hits: list[EventHit]) -> str:
    import itertools

    if len(hits) > MAX_ENUM_HITS:
        return "reject"
    valid = []
    for perm in itertools.permutations(range(len(hits))):
        ordered = [hits[i] for i in perm]
        m = sequence_metrics(ordered)
        if m is None:
            continue
        valid.append((m["qf"], -m["first_lever_arm"], ordered, m))
    if not valid:
        return "reject"
    _, _, ordered, m = sorted(valid, key=lambda x: (x[0], x[1]))[0]
    ok, intersects = sample_cone_plane(ordered[0], ordered[1], m["e_first"], m["e_after1"])
    if not ok:
        return "reject"
    return "keep" if intersects else "veto"


def classify_compton(hits: list[EventHit], reject_policy: str) -> str:
    if len(hits) <= 1:
        return "single"
    cls = classify_hit2(hits) if len(hits) == 2 else classify_hit3plus(hits)
    if cls == "reject" and reject_policy == "keep":
        return "reject_kept"
    return cls


def make_axis(emin: float, emax: float, binw: float):
    edges = np.arange(emin, emax + 0.5 * binw, binw, dtype=float)
    cent = 0.5 * (edges[:-1] + edges[1:])
    return edges, cent


def init_result(n_main: int, n_zoom: int):
    return {
        "main_raw": np.zeros(n_main, dtype=float),
        "main_bgo": np.zeros(n_main, dtype=float),
        "zoom_raw": np.zeros(n_zoom, dtype=float),
        "zoom_bgo": np.zeros(n_zoom, dtype=float),
        "zoom_final": np.zeros(n_zoom, dtype=float),
        "main_raw_by_tag": {},
        "window": defaultdict(float),
        "window_w2": defaultdict(float),
        "by_tag": defaultdict(nested_float_dict),
        "compton_class": defaultdict(float),
        "n_events": 0,
        "n_tes_events": 0,
    }


def add_hist(hist: np.ndarray, value: float, weight: float, emin: float, binw: float):
    k = int((value - emin) / binw)
    if 0 <= k < len(hist):
        hist[k] += weight


def add_tag_hist(store: dict, tag: str, value: float, weight: float, emin: float, binw: float, n_bins: int):
    k = int((value - emin) / binw)
    if 0 <= k < n_bins:
        if tag not in store:
            store[tag] = np.zeros(n_bins, dtype=float)
        store[tag][k] += weight


def parse_one_file(args_tuple):
    fp, mode, bounds, main_emin, main_emax, main_binw, zoom_emin, zoom_emax, zoom_binw, bgo_thr, reject_policy = args_tuple
    n_main = int(math.ceil((main_emax - main_emin) / main_binw))
    n_zoom = int(math.ceil((zoom_emax - zoom_emin) / zoom_binw))
    res = init_result(n_main, n_zoom)
    tag = parse_tag(fp) if mode == "prompt" else "activation"
    weight = prompt_file_weight(fp) if mode == "prompt" else 1.0

    cur_tes: list[EventHit] = []
    cur_bgo = 0.0

    def add_window(name: str, w: float):
        res["window"][name] += w
        res["window_w2"][name] += w * w
        res["by_tag"][tag][name] += w

    def flush_event():
        nonlocal cur_tes, cur_bgo
        if not cur_tes:
            cur_bgo = 0.0
            return
        res["n_tes_events"] += 1
        e_sum = float(sum(h.e for h in cur_tes))
        if main_emin <= e_sum < main_emax:
            add_hist(res["main_raw"], e_sum, weight, main_emin, main_binw)
            add_tag_hist(res["main_raw_by_tag"], tag, e_sum, weight, main_emin, main_binw, n_main)
            if cur_bgo < bgo_thr:
                add_hist(res["main_bgo"], e_sum, weight, main_emin, main_binw)
        if zoom_emin <= e_sum < zoom_emax:
            add_hist(res["zoom_raw"], e_sum, weight, zoom_emin, zoom_binw)
            add_window("raw", weight)
            if cur_bgo < bgo_thr:
                add_hist(res["zoom_bgo"], e_sum, weight, zoom_emin, zoom_binw)
                add_window("bgo", weight)
                cls = classify_compton(cur_tes, reject_policy)
                res["compton_class"][cls] += weight
                if cls in ("single", "keep", "reject_kept"):
                    add_hist(res["zoom_final"], e_sum, weight, zoom_emin, zoom_binw)
                    add_window("final", weight)
            else:
                res["compton_class"]["bgo_veto"] += weight
        cur_tes = []
        cur_bgo = 0.0

    with open_text(fp) as fh:
        for line in fh:
            if line.startswith("SE"):
                flush_event()
                res["n_events"] += 1
                continue
            if not line.startswith("HTsim"):
                continue
            parsed = parse_htsim(line)
            if parsed is None:
                continue
            x, y, z, e = parsed
            vol = identify_vol(x, y, z, bounds)
            if is_active_veto_volume(vol):
                cur_bgo += e
            elif str(vol).startswith("TES_L"):
                try:
                    layer = int(str(vol).replace("TES_L", ""))
                except Exception:
                    layer = -1
                cur_tes.append(EventHit(x=x, y=y, z=z, e=e, pixel_uid=f"{vol}:{x:.3f}:{y:.3f}:{z:.3f}", layer=layer))
    flush_event()
    return res


def reduce_results(results: Iterable[dict], n_main: int, n_zoom: int):
    out = init_result(n_main, n_zoom)
    for res in results:
        for k in ("main_raw", "main_bgo", "zoom_raw", "zoom_bgo", "zoom_final"):
            out[k] += res[k]
        for tag, hist in res["main_raw_by_tag"].items():
            if tag not in out["main_raw_by_tag"]:
                out["main_raw_by_tag"][tag] = np.zeros(n_main, dtype=float)
            out["main_raw_by_tag"][tag] += hist
        for k, v in res["window"].items():
            out["window"][k] += v
        for k, v in res["window_w2"].items():
            out["window_w2"][k] += v
        for tag, d in res["by_tag"].items():
            for k, v in d.items():
                out["by_tag"][tag][k] += v
        for k, v in res["compton_class"].items():
            out["compton_class"][k] += v
        out["n_events"] += res["n_events"]
        out["n_tes_events"] += res["n_tes_events"]
    return out


def rate_and_err(weight: float, weight2: float, time_s: float):
    if time_s <= 0:
        return 0.0, 0.0
    return weight / time_s, math.sqrt(max(weight2, 0.0)) / time_s


def load_prompt_norm() -> dict:
    return load_json(PROMPT_DIR / "normalization.json", {})


def parse_delayed_observation_time(log_path: Path) -> float:
    if not log_path.exists():
        return 9003.74091
    for line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "Observation time:" in line:
            vals = re.findall(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", line)
            if vals:
                return float(vals[0])
    return 9003.74091


def read_csv_dicts(path: Path, limit: int | None = None):
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8-sig", errors="ignore") as fh:
        for row in csv.DictReader(fh):
            rows.append(row)
            if limit is not None and len(rows) >= limit:
                break
    return rows


def save_spectrum_csv(path: Path, centers: np.ndarray, columns: dict[str, np.ndarray]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        names = list(columns.keys())
        writer.writerow(["E_keV", *names])
        for i, e in enumerate(centers):
            writer.writerow([f"{e:.6g}", *[f"{columns[name][i]:.12g}" for name in names]])


def save_spectrum_dat(path: Path, centers: np.ndarray, columns: dict[str, np.ndarray]):
    path.parent.mkdir(parents=True, exist_ok=True)
    names = list(columns.keys())
    with path.open("w", encoding="utf-8") as fh:
        fh.write("# E_keV " + " ".join(names) + "\n")
        for i, e in enumerate(centers):
            vals = " ".join(f"{columns[name][i]:.12e}" for name in names)
            fh.write(f"{e:.6f} {vals}\n")


def save_component_rate_table(path: Path, centers: np.ndarray, binw: float, components: dict[str, np.ndarray]):
    path.parent.mkdir(parents=True, exist_ok=True)
    ranges = [(100.0, 5000.0), (100.0, 10000.0), (480.0, 550.0)]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["component", *[f"rate_{lo:g}_{hi:g}_keV_cps" for lo, hi in ranges]])
        for name, y in components.items():
            row = [name]
            for lo, hi in ranges:
                mask = (centers >= lo) & (centers < hi)
                row.append(f"{float(np.sum(y[mask]) * binw):.12g}")
            writer.writerow(row)


def fixed_activation_inventory_rows(outdir: Path) -> list[dict]:
    inv_rows = read_csv_dicts(ACTIVATION_INVENTORY)
    action_rows = read_csv_dicts(FIX_ACTIONS)
    grouped: dict[tuple[str, str, str], dict[str, float]] = {}
    for row in action_rows:
        key = (row.get("VN", ""), row.get("ZA", ""), row.get("nuclide", ""))
        item = grouped.setdefault(key, {"old": 0.0, "new": 0.0})
        item["old"] += float(row.get("old_flux_Bq", 0.0))
        item["new"] += float(row.get("new_flux_Bq", 0.0))

    fixed_rows = []
    for row in inv_rows:
        key = (row.get("VN", ""), row.get("ZA", ""), row.get("nuclide", ""))
        old_activity = float(row.get("Activity_Bq", 0.0))
        if key in grouped:
            new_activity = grouped[key]["new"]
            scale = new_activity / grouped[key]["old"] if grouped[key]["old"] > 0 else 0.0
        else:
            new_activity = old_activity
            scale = 1.0
        if new_activity <= 1.0e-12:
            continue
        new_row = dict(row)
        new_row["Activity_Bq_before_fix"] = f"{old_activity:.12g}"
        new_row["Activity_Bq_after_fix"] = f"{new_activity:.12g}"
        new_row["fix_scale"] = f"{scale:.12g}"
        fixed_rows.append(new_row)

    fixed_rows.sort(key=lambda r: float(r["Activity_Bq_after_fix"]), reverse=True)
    out_csv = outdir / "activation_inventory_day15_after_groundstate_fix.csv"
    if fixed_rows:
        fields = [
            "VN",
            "ZA",
            "nuclide",
            "exc_keV",
            "RP_yield",
            "hl_s",
            "Activity_Bq_before_fix",
            "Activity_Bq_after_fix",
            "fix_scale",
            "Points",
        ]
        with out_csv.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            for row in fixed_rows:
                writer.writerow({k: row.get(k, "") for k in fields})
    return fixed_rows


def component_label(tag: str) -> str:
    return {
        "gamma": "CosmicPhotons",
        "p": "CosmicProtons",
        "n": "CosmicNeutrons",
        "alpha": "CosmicAlphas",
        "eplus": "CosmicPositrons",
        "eminus": "CosmicElectrons",
        "electron": "CosmicElectrons",
        "muplus": "CosmicMuons",
        "muminus": "CosmicMuons",
    }.get(tag, f"Prompt_{tag}")


def make_plots(outdir: Path, main_cent, zoom_cent, prompt, delayed, times, summary, font_prop, main_binw: float):
    figdir = outdir / "figures"
    figdir.mkdir(parents=True, exist_ok=True)

    prompt_time = times["prompt_s"]
    delayed_time = times["delayed_s"]
    main_total_raw = prompt["main_raw"] / prompt_time + delayed["main_raw"] / delayed_time
    main_total_bgo = prompt["main_bgo"] / prompt_time + delayed["main_bgo"] / delayed_time
    main_prompt_bgo = prompt["main_bgo"] / prompt_time
    main_delayed_bgo = delayed["main_bgo"] / delayed_time
    zoom_total_raw = prompt["zoom_raw"] / prompt_time + delayed["zoom_raw"] / delayed_time
    zoom_total_bgo = prompt["zoom_bgo"] / prompt_time + delayed["zoom_bgo"] / delayed_time
    zoom_total_final = prompt["zoom_final"] / prompt_time + delayed["zoom_final"] / delayed_time

    component_diff: dict[str, np.ndarray] = {}
    for tag, hist in prompt["main_raw_by_tag"].items():
        label = component_label(tag)
        component_diff.setdefault(label, np.zeros_like(hist, dtype=float))
        component_diff[label] += hist / prompt_time / main_binw
    component_diff["ActivationDelay(day15)"] = delayed["main_raw"] / delayed_time / main_binw
    component_diff = {k: v for k, v in component_diff.items() if np.any(v > 0)}
    component_order = [
        "CosmicPhotons",
        "CosmicProtons",
        "CosmicNeutrons",
        "CosmicAlphas",
        "CosmicElectrons",
        "CosmicPositrons",
        "CosmicMuons",
        "ActivationDelay(day15)",
    ]
    ordered_component_diff = {
        k: component_diff[k]
        for k in component_order
        if k in component_diff
    }
    for k in sorted(component_diff):
        if k not in ordered_component_diff:
            ordered_component_diff[k] = component_diff[k]
    total_component_diff = sum(ordered_component_diff.values(), np.zeros_like(main_cent, dtype=float))
    image8_columns = dict(ordered_component_diff)
    image8_columns["Total"] = total_component_diff
    save_spectrum_csv(outdir / "image8_like_component_spectrum.csv", main_cent, image8_columns)
    save_spectrum_dat(outdir / "image8_like_component_spectrum.dat", main_cent, image8_columns)
    save_component_rate_table(outdir / "image8_like_component_rates.csv", main_cent, main_binw, image8_columns)

    p = figdir / "spectrum_100_10000_raw_bgo.png"
    plt.figure(figsize=(11, 6.2))
    plt.step(main_cent, main_total_raw, where="mid", label="No veto", lw=1.5)
    plt.step(main_cent, main_total_bgo, where="mid", label="After BGO veto", lw=1.5)
    plt.step(main_cent, main_prompt_bgo, where="mid", label="Prompt after BGO", lw=1.0, ls="--")
    plt.step(main_cent, main_delayed_bgo, where="mid", label="Delayed after BGO", lw=1.0, ls="--")
    plt.yscale("log")
    plt.xlim(100, 10000)
    plt.xlabel("TES event-summed energy (keV)", fontproperties=font_prop)
    plt.ylabel("Rate (counts s$^{-1}$ bin$^{-1}$)", fontproperties=font_prop)
    plt.title("Day-15 TES background spectrum: no veto and BGO veto", fontproperties=font_prop)
    plt.grid(True, which="both", alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(p, dpi=220)
    plt.close()

    pi8 = figdir / "image8_like_component_spectrum.png"
    plt.figure(figsize=(9.0, 6.0))
    colors = {
        "CosmicPhotons": "#1f77b4",
        "CosmicProtons": "#2ca02c",
        "CosmicNeutrons": "#17becf",
        "CosmicAlphas": "#d62728",
        "CosmicElectrons": "#9467bd",
        "CosmicPositrons": "#8c564b",
        "CosmicMuons": "#e377c2",
        "ActivationDelay(day15)": "#7f7f7f",
    }
    for name, y in ordered_component_diff.items():
        yy = np.where(y > 0, y, np.nan)
        plt.plot(main_cent, yy, lw=1.1, label=name, color=colors.get(name))
    plt.plot(main_cent, np.where(total_component_diff > 0, total_component_diff, np.nan), lw=1.6, color="black", label="Total")
    plt.xscale("log")
    plt.yscale("log")
    plt.xlim(100, 10000)
    positive = total_component_diff[total_component_diff > 0]
    if len(positive):
        plt.ylim(max(float(np.min(positive)) * 0.5, 1.0e-6), float(np.max(positive)) * 2.0)
    plt.xlabel("Energy [keV]", fontproperties=font_prop)
    plt.ylabel("Counts/keV/s", fontproperties=font_prop)
    plt.title("IMAGE8-style day-15 no-veto background components", fontproperties=font_prop)
    plt.grid(True, which="both", alpha=0.25)
    plt.legend(fontsize=8, ncol=2)
    plt.tight_layout()
    plt.savefig(pi8, dpi=220)
    plt.close()

    pz = figdir / "spectrum_480_550_veto_chain.png"
    plt.figure(figsize=(11, 6.2))
    plt.step(zoom_cent, zoom_total_raw, where="mid", label="No veto", lw=1.6)
    plt.step(zoom_cent, zoom_total_bgo, where="mid", label="After BGO veto", lw=1.6)
    plt.step(zoom_cent, zoom_total_final, where="mid", label="After BGO + Compton/FoV", lw=1.8)
    plt.yscale("log")
    plt.xlim(480, 550)
    plt.xlabel("TES event-summed energy (keV)", fontproperties=font_prop)
    plt.ylabel("Rate (counts s$^{-1}$ bin$^{-1}$)", fontproperties=font_prop)
    plt.title("511 keV window veto chain", fontproperties=font_prop)
    txt = (
        f"No veto: {summary['rates_cps']['total_raw_480_550']:.3g} cps\n"
        f"BGO veto: {summary['rates_cps']['total_bgo_480_550']:.3g} cps\n"
        f"BGO+Compton/FoV: {summary['rates_cps']['total_final_480_550']:.3g} cps"
    )
    plt.text(0.02, 0.98, txt, transform=plt.gca().transAxes, va="top", ha="left",
             bbox=dict(boxstyle="round,pad=0.35", facecolor="white", alpha=0.86, edgecolor="none"))
    plt.grid(True, which="both", alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(pz, dpi=220)
    plt.close()

    pv = figdir / "veto_rates_bar.png"
    labels = ["No veto", "BGO", "BGO+Compton/FoV"]
    vals = [
        summary["rates_cps"]["total_raw_480_550"],
        summary["rates_cps"]["total_bgo_480_550"],
        summary["rates_cps"]["total_final_480_550"],
    ]
    plt.figure(figsize=(7.8, 5.5))
    bars = plt.bar(labels, vals, color=["#4C78A8", "#72B7B2", "#F58518"])
    for b, v in zip(bars, vals):
        plt.text(b.get_x() + b.get_width() / 2, v, f"{v:.3g}", ha="center", va="bottom")
    plt.ylabel("480-550 keV rate (cps)", fontproperties=font_prop)
    plt.title("Veto effect in the 511 keV analysis window", fontproperties=font_prop)
    plt.grid(True, axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(pv, dpi=220)
    plt.close()

    pp = figdir / "prompt_particle_raw_contribution.png"
    tag_rates = {}
    for tag, d in prompt["by_tag"].items():
        tag_rates[tag] = d.get("raw", 0.0) / prompt_time
    tag_rates = {k: v for k, v in sorted(tag_rates.items(), key=lambda kv: kv[1], reverse=True) if v > 0}
    if tag_rates:
        plt.figure(figsize=(7.6, 6.0))
        plt.pie(list(tag_rates.values()), labels=[f"{k}\n{v:.2g} cps" for k, v in tag_rates.items()],
                autopct="%1.1f%%", startangle=90)
        plt.title("Prompt contribution by primary particle, no veto, 480-550 keV", fontproperties=font_prop)
        plt.tight_layout()
        plt.savefig(pp, dpi=220)
        plt.close()

    pa = figdir / "activation_top10_after_fix.png"
    fixed_rows = fixed_activation_inventory_rows(outdir)
    top = fixed_rows[:10]
    if top:
        labels = [r["nuclide"] + " " + r["VN"] for r in top][::-1]
        vals = [float(r["Activity_Bq_after_fix"]) for r in top][::-1]
        plt.figure(figsize=(9.0, 5.8))
        plt.barh(labels, vals, color="#54A24B")
        plt.xlabel("Activity after ground-state fix (Bq)", fontproperties=font_prop)
        plt.title("Top activation components after delay fix, day 15", fontproperties=font_prop)
        plt.grid(True, axis="x", alpha=0.25)
        plt.tight_layout()
        plt.savefig(pa, dpi=220)
        plt.close()

    return {
        "main": str(p),
        "zoom": str(pz),
        "veto": str(pv),
        "image8_like": str(pi8),
        "prompt_pie": str(pp) if pp.exists() else "",
        "activation": str(pa) if pa.exists() else "",
    }


def wrapped_lines(text: str, width: int = 56):
    lines = []
    for para in text.split("\n"):
        para = para.strip()
        if not para:
            lines.append("")
        else:
            lines.extend(textwrap.wrap(para, width=width, break_long_words=True, replace_whitespace=False))
    return lines


def add_text_page(pdf: PdfPages, title: str, body: str, font_prop: FontProperties):
    fig = plt.figure(figsize=(8.27, 11.69))
    fig.patch.set_facecolor("white")
    fig.text(0.08, 0.94, title, fontsize=19, fontweight="bold", fontproperties=font_prop, va="top")
    y = 0.89
    for line in wrapped_lines(body, width=48):
        if y < 0.08:
            pdf.savefig(fig)
            plt.close(fig)
            fig = plt.figure(figsize=(8.27, 11.69))
            fig.patch.set_facecolor("white")
            y = 0.94
        fig.text(0.08, y, line, fontsize=11.2, fontproperties=font_prop, va="top")
        y -= 0.026 if line else 0.018
    pdf.savefig(fig)
    plt.close(fig)


def add_image_page(pdf: PdfPages, title: str, image_path: str, caption: str, font_prop: FontProperties):
    if not image_path:
        return
    img = plt.imread(image_path)
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.patch.set_facecolor("white")
    fig.text(0.05, 0.94, title, fontsize=17, fontweight="bold", fontproperties=font_prop, va="top")
    ax = fig.add_axes([0.06, 0.16, 0.88, 0.70])
    ax.imshow(img)
    ax.axis("off")
    fig.text(0.06, 0.08, "\n".join(wrapped_lines(caption, width=100)), fontsize=10.5, fontproperties=font_prop, va="top")
    pdf.savefig(fig)
    plt.close(fig)


def build_pdf(out_pdf: Path, summary: dict, figure_paths: dict, font_prop: FontProperties):
    rate = summary["rates_cps"]
    fix = summary["delay_fix"]
    science = summary["science_source"]
    body1 = f"""\
本报告读取当前 NEW_GEO_RE/ADR 工作区的已完成输出生成，目标是复刻 cosmosray_0416.pptx 的本底汇报结构，同时记录 ADR 几何 cmfix 相比原始 mm 文件的单位修正。

当前状态：NEW_GEO_RE/ADR 已完成 3 mm TES 基准的 cm 几何、20 个全空间等 μ 角区间的大气宇宙线源、2602 等效统计 instant prompt、buildup prompt、从 buildup 的 RPIP 位置生成 day-15 delayed source、W183/W180 ground-state/isomer 修正、以及 fixed delayed 1M Cosima 运行。science 511 keV on-axis beam 也完成了 100k 验证运行。

你的流程判断是对的：科学源用聚焦光学和大气衰减得到入射到焦平面前的 511 keV 通量；大气宇宙线先跑 buildup 记录活化核素，再独立跑 instant prompt；用 buildup 的 RPIP 核素产额和位置生成第 15 天的 delayed source；最后把 instant 和 delayed 两个 SIM 家族归一化、合并并做 BGO/Compton veto。

我这里有一个实现口径差别：本报告的平均能谱和平均计数率没有显式抽样一条随机泊松时间轴，而是对 prompt 与 delayed 事件库直接做事件权重归一化后相加。原因是独立泊松流叠加的期望谱等于各分量率谱之和，直接率谱相加没有额外随机时间轴噪声，更适合报告稳定数值。真正要评估偶然符合、跨事件 BGO 误 veto、死时间和电子学时间窗时，仍然应该生成泊松时间轴；这一步作为下一阶段保留。
"""
    body2 = f"""\
归一化口径：prompt 使用 instant_equiv2602 的 60 个 SIM 文件。gamma 权重为 1，非 gamma 8 个 replica 权重为 1/8；共同等效 prompt 时间为 {summary['times_s']['prompt_s']:.6g} s。delayed 使用 fixed day-15 1M SIM，Cosima log 给出的 observation time 为 {summary['times_s']['delayed_s']:.6g} s。

VETO 口径：raw stage 要求 TES 阵列 event-summed energy 落入 480-550 keV；active-shield/BGO veto 要求同一 Cosima event 内主动 veto 通道总沉积能量 < 50 keV；当前 authority 主动 veto 体积名为 {active_veto_volume_name()}，代码把 BGO、ACTIVE_SHIELD、CEBR3 体积都归入同一 veto 通道。Compton/FoV veto 只作用于 active-shield-pass 的多 TES pixel 事件。2-hit 事件测试两个顺序的第一康普顿锥是否与 Be-window disk 相交；3-hit+ 事件用经典 CSR 全排列选 QF 最小序列，再测试 best-sequence 第一锥。reject_policy=keep，用于保守保留无有效锥或过多 hit 的歧义事件；本报告数值与 2602 PPT 不要求完全相同，因为 delayed 源已采用 day-15 ground-state/isomer 修正。

第 15 天 480-550 keV 结果：no veto = {rate['total_raw_480_550']:.4g} cps，BGO veto 后 = {rate['total_bgo_480_550']:.4g} cps，BGO+Compton/FoV 后 = {rate['total_final_480_550']:.4g} cps。BGO 保留比例为 {rate['bgo_survival_fraction']:.3f}，最终保留比例为 {rate['final_survival_fraction']:.3f}。

Delayed source 修正：修正前总活度 {fix['old_total_activity_Bq']:.6g} Bq；修正后 {fix['new_total_activity_Bq']:.6g} Bq；source blocks 从 {fix['source_blocks_in']} 减到 {fix['source_blocks_after_fix']}，移除了 {fix['source_blocks_removed']} 个 block。主修正是 W-183/W-180 ground-state 被误当作短寿命 isomer 的问题。
"""
    body3 = f"""\
科学源口径：当前 science 511 source 是 Level-1 optics 模型，即外部 CAM511 光学有效面积与大气透过率先给出焦平面前 photon rate，再用 Cosima 的 HomogeneousBeam 在 Be window 附近注入 511 keV 均匀圆斑。100k 验证中 event-summed 480-550 keV selection efficiency = {science['epsilon_480_550']:.6g}。

使用 ledger 中 A_eff(511 keV) = {science['A_eff_cm2']:.4g} cm2、T_atm = {science['T_atm']:.4g}，如果天体线通量为 1e-4 ph cm^-2 s^-1，则焦平面前注入率约 {science['rate_for_1e4_flux_s^-1']:.4g} s^-1，选中率约 {science['selected_rate_for_1e4_flux_s^-1']:.4g} s^-1。该信号率应与下方第 15 天本底 veto 后率比较。

限制：1) prompt time-variable light-curve wrapper 已可运行，但当前包内 prompt lightcurve_shape 全为 1.0，物理上的飞行轨迹变化尚未重新生成；2) 本 PDF 未重新生成完整随机时间轴，因此不报告偶然符合率；3) Compton/FoV veto 是基于 HTsim pixel energy 的 2602-style 几何 veto，不是完整 Revan 重建输出；4) delayed 是 day-15 fixed source，本报告不含 day-5。
"""
    with PdfPages(out_pdf) as pdf:
        add_text_page(pdf, "球载 511 keV TES 谱仪本底模拟：NEW_GEO_RE/ADR day-15 报告", body1, font_prop)
        add_text_page(pdf, "方法与归一化", body2, font_prop)
        add_image_page(pdf, "100-10000 keV 能谱", figure_paths["main"], "Raw 与 BGO veto 后的 TES event-summed rate spectrum。Compton/FoV veto 只在 511 keV 窗口内解释。", font_prop)
        add_image_page(pdf, "类似 IMAGE8 的分成分谱", figure_paths.get("image8_like", ""), "按《基于立方星》IMAGE8 风格绘制的 no-veto 分成分微分谱，单位 Counts/keV/s。2605 当前只有全空间大气宇宙线 prompt 分量和合并后的 day-15 activation delayed 分量，因此 delayed 没有再按原初粒子拆分。", font_prop)
        add_image_page(pdf, "480-550 keV VETO 链", figure_paths["zoom"], "511 keV 分析窗口内的 no-veto、BGO-veto、BGO+Compton/FoV-veto 谱。", font_prop)
        add_image_page(pdf, "VETO 后计数率", figure_paths["veto"], "480-550 keV integrated cps。reject_policy=keep 保守保留歧义 Compton 重建事件。", font_prop)
        add_image_page(pdf, "Prompt 粒子贡献", figure_paths.get("prompt_pie", ""), "Prompt no-veto 480-550 keV 贡献按 primary particle 分解，非 gamma replica 已按 1/8 归一化。", font_prop)
        add_image_page(pdf, "Buildup 活化分量", figure_paths.get("activation", ""), "从 2605 buildup RPIP 产额得到的 day-15 活化源 top components，图中已应用 ground-state/isomer 修正；W-183 ground state 已从 delayed source 中移除。", font_prop)
        add_text_page(pdf, "科学源与限制", body3, font_prop)


def build_summary(prompt, delayed, times, args) -> dict:
    prompt_time = times["prompt_s"]
    delayed_time = times["delayed_s"]

    def stage_rate(stage: str):
        p, pe = rate_and_err(prompt["window"].get(stage, 0.0), prompt["window_w2"].get(stage, 0.0), prompt_time)
        d, de = rate_and_err(delayed["window"].get(stage, 0.0), delayed["window_w2"].get(stage, 0.0), delayed_time)
        return p, pe, d, de, p + d, math.sqrt(pe * pe + de * de)

    pr, pre, dr, dre, tr, tre = stage_rate("raw")
    pb, pbe, db, dbe, tb, tbe = stage_rate("bgo")
    pf, pfe, df, dfe, tf, tfe = stage_rate("final")
    fix = load_json(FIX_SUMMARY, {})
    science_json = load_json(SCIENCE_SUMMARY, {})
    science_cfg = science_json.get("source_config", {}) if isinstance(science_json, dict) else {}
    science_sim = science_json.get("sim_summary", {}) if isinstance(science_json, dict) else {}
    ledger = read_csv_dicts(SCIENCE_LEDGER)
    ledger_1e4 = next((r for r in ledger if abs(float(r["flux_ph_cm2_s"]) - 1.0e-4) < 1e-12), ledger[0] if ledger else {})
    n_trig = int(science_cfg.get("triggers", science_sim.get("stored_events", 0)))
    eps = float(
        science_sim.get(
            "events_sum_480_550_per_trigger",
            science_sim.get("events_sum_480_550_keV", 0) / max(n_trig, 1),
        )
    )
    inj_1e4 = float(ledger_1e4.get("rate_to_injection_plane_s^-1", 0.0)) if ledger_1e4 else 0.0
    science = {
        "generated_triggers": n_trig,
        "epsilon_480_550": eps,
        "A_eff_cm2": float(ledger_1e4.get("A_opt_cm2", 50.89)) if ledger_1e4 else 50.89,
        "T_atm": float(ledger_1e4.get("T_atm", 0.0)) if ledger_1e4 else 0.0,
        "rate_for_1e4_flux_s^-1": inj_1e4,
        "selected_rate_for_1e4_flux_s^-1": inj_1e4 * eps,
    }
    return {
        "analysis": {
            "energy_window_keV": [args.zoom_emin, args.zoom_emax],
            "bgo_threshold_keV": args.bgo_thr,
            "reject_policy": args.reject_policy,
            "compton_veto_note": "Applied only to BGO-pass multihit events in 480-550 keV.",
        },
        "times_s": times,
        "rates_cps": {
            "prompt_raw_480_550": pr,
            "prompt_bgo_480_550": pb,
            "prompt_final_480_550": pf,
            "delayed_raw_480_550": dr,
            "delayed_bgo_480_550": db,
            "delayed_final_480_550": df,
            "total_raw_480_550": tr,
            "total_raw_err_480_550": tre,
            "total_bgo_480_550": tb,
            "total_bgo_err_480_550": tbe,
            "total_final_480_550": tf,
            "total_final_err_480_550": tfe,
            "bgo_survival_fraction": tb / tr if tr > 0 else 0.0,
            "final_survival_fraction": tf / tr if tr > 0 else 0.0,
        },
        "weighted_counts_480_550": {
            "prompt": {k: prompt["window"].get(k, 0.0) for k in ("raw", "bgo", "final")},
            "delayed": {k: delayed["window"].get(k, 0.0) for k in ("raw", "bgo", "final")},
        },
        "prompt_by_particle_weighted_counts": {tag: dict(d) for tag, d in sorted(prompt["by_tag"].items())},
        "compton_class_weighted_counts": {
            "prompt": dict(prompt["compton_class"]),
            "delayed": dict(delayed["compton_class"]),
        },
        "delay_fix": {
            "old_total_activity_Bq": fix.get("old_total_activity_Bq", 0.0),
            "new_total_activity_Bq": fix.get("new_total_activity_Bq", 0.0),
            "source_blocks_in": fix.get("source_blocks_in", 0),
            "source_blocks_removed": fix.get("source_blocks_removed", 0),
            "source_blocks_after_fix": int(fix.get("source_blocks_in", 0)) - int(fix.get("source_blocks_removed", 0)),
        },
        "science_source": science,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=str(DEFAULT_OUTDIR))
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--main-emin", type=float, default=100.0)
    ap.add_argument("--main-emax", type=float, default=10000.0)
    ap.add_argument("--main-binw", type=float, default=10.0)
    ap.add_argument("--zoom-emin", type=float, default=480.0)
    ap.add_argument("--zoom-emax", type=float, default=550.0)
    ap.add_argument("--zoom-binw", type=float, default=0.5)
    ap.add_argument("--bgo-thr", type=float, default=50.0)
    ap.add_argument("--reject-policy", choices=["keep", "drop"], default="keep")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    font_prop = setup_fonts()
    bounds = load_bounds(BOUNDS_PATH)
    prompt_norm = load_prompt_norm()
    prompt_time = float(prompt_norm.get("gamma_prompt_time_s_with_farfield_area", 29.47521574873429))
    delayed_time = parse_delayed_observation_time(DELAY_DIR / "cosima_delayed_transport_1m.log")
    times = {"prompt_s": prompt_time, "delayed_s": delayed_time}

    main_edges, main_cent = make_axis(args.main_emin, args.main_emax, args.main_binw)
    zoom_edges, zoom_cent = make_axis(args.zoom_emin, args.zoom_emax, args.zoom_binw)
    n_main = len(main_cent)
    n_zoom = len(zoom_cent)

    prompt_files = sorted(str(p) for p in PROMPT_DIR.glob("*.sim.gz"))
    delayed_files = [str(FIXED_DELAY_SIM)]
    if not prompt_files:
        raise SystemExit(f"No prompt SIM files under {PROMPT_DIR}")
    if not FIXED_DELAY_SIM.exists():
        raise SystemExit(f"Missing delayed SIM: {FIXED_DELAY_SIM}")

    common = (bounds, args.main_emin, args.main_emax, args.main_binw, args.zoom_emin, args.zoom_emax, args.zoom_binw, args.bgo_thr, args.reject_policy)
    prompt_tasks = [(fp, "prompt", *common) for fp in prompt_files]
    delayed_tasks = [(fp, "delayed", *common) for fp in delayed_files]
    nproc = max(1, int(args.workers))
    print(f"[INFO] parsing prompt files={len(prompt_tasks)} workers={nproc}")
    with mp.get_context("fork").Pool(processes=nproc) as pool:
        prompt_res = list(pool.imap_unordered(parse_one_file, prompt_tasks, chunksize=1))
    print("[INFO] parsing fixed delayed file")
    # The delayed run is one large gzip file; running it in-process avoids
    # pickling a large result from a child process.
    delayed_res = [parse_one_file(delayed_tasks[0])]
    prompt = reduce_results(prompt_res, n_main, n_zoom)
    delayed = reduce_results(delayed_res, n_main, n_zoom)

    summary = build_summary(prompt, delayed, times, args)
    summary_path = outdir / "day15_report_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    save_spectrum_csv(
        outdir / "spectrum_100_10000_rates.csv",
        main_cent,
        {
            "total_raw_cps_per_bin": prompt["main_raw"] / prompt_time + delayed["main_raw"] / delayed_time,
            "total_bgo_cps_per_bin": prompt["main_bgo"] / prompt_time + delayed["main_bgo"] / delayed_time,
            "prompt_bgo_cps_per_bin": prompt["main_bgo"] / prompt_time,
            "delayed_bgo_cps_per_bin": delayed["main_bgo"] / delayed_time,
        },
    )
    save_spectrum_csv(
        outdir / "spectrum_480_550_rates.csv",
        zoom_cent,
        {
            "total_raw_cps_per_bin": prompt["zoom_raw"] / prompt_time + delayed["zoom_raw"] / delayed_time,
            "total_bgo_cps_per_bin": prompt["zoom_bgo"] / prompt_time + delayed["zoom_bgo"] / delayed_time,
            "total_final_cps_per_bin": prompt["zoom_final"] / prompt_time + delayed["zoom_final"] / delayed_time,
            "prompt_final_cps_per_bin": prompt["zoom_final"] / prompt_time,
            "delayed_final_cps_per_bin": delayed["zoom_final"] / delayed_time,
        },
    )

    figure_paths = make_plots(outdir, main_cent, zoom_cent, prompt, delayed, times, summary, font_prop, args.main_binw)
    pdf_path = outdir / "cosmosray_bg_NEW_GEO_RE_ADR_day15_report.pdf"
    build_pdf(pdf_path, summary, figure_paths, font_prop)
    print(f"[OK] wrote {summary_path}")
    print(f"[OK] wrote {pdf_path}")


if __name__ == "__main__":
    main()
