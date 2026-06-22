#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""makedecaysourcewithplot_rpip_mp2.py

Generate a runnable Cosima delayed-decay *.source* using **true isotope production positions**
from SIM comment lines:

  CC IP RP <VN> x y z ZA exc_keV t

and total isotope yields from Cosima universal isotope store (.dat):

  VN <vol>
  RP <ZA> <exc_keV> <value>

Compared to the original makedecaysourcewithplot.py (IA-based), this version:
  - builds spatial PDFs from *RPIP* points ("CC IP RP") which already match RP totals
  - keeps an **axisymmetric** model (z-bins + radial profile) to avoid 3D histogram explosion
  - uses multiprocessing for SIM parsing + tqdm progress
  - keeps half-life enrichment: cache -> python library -> NUBASE -> optional online (IAEA LiveChart)

Outputs (similar naming style to makedecaysourcewithplot.py):
  activation_decay_dayXX.source
  activation_inventory_dayXX.csv
  unknown_isotopes_dayXX.csv
  no_rpip_points_dayXX.csv
  profiles/...(many radial profile files; required by RadialProfileBeam)
  plot_check_dayXX.png   (single integrated geometry plot if --plot-check)

Units:
  - RPIP positions in SIM are in **cm** (as emitted by your CC IP writer) -> converted to **mm** internally
  - current bounds.json is in **cm** and is used only for plot-check geometry overlays
  - Cosima RadialProfileBeam expects **cm** -> converted when writing

Typical usage:
  python3 makedecaysourcewithplot_rpip_mp2.py \
    --dat "run/*.dat" --sim "run/*.sim.gz" --non-gamma-div 8 \
    --t-ground-days 0 --t-flight-days 15 --t-after-days 0 \
    --z-bins 30 --r-bins 50 \
    --outdir decay_rpip_out --bounds XZTES/bounds.json --plot-check

Note on t-ground-days:
  It is optional pre-flight exposure time you might want to include in activation build-up.
  If you have *no* ground activation scenario, set it to 0.
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
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import multiprocessing as mp

import numpy as np
import matplotlib.pyplot as plt
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable=None, *args, **kwargs):
        return iterable if iterable is not None else []


# -------------------------
# filename tag parsing + weights
# -------------------------
TAG_RE = re.compile(r"Background_(?P<tag>[^_]+)_", re.IGNORECASE)


def parse_tag(path: str) -> str:
    m = TAG_RE.search(Path(path).name)
    return (m.group("tag").lower() if m else "unknown")


def is_gamma(tag: str) -> bool:
    return tag == "gamma"


def open_text(path: str):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return open(path, "rt", encoding="utf-8", errors="ignore")


# -------------------------
# Canonicalize VN (your verify_rp_ip.py logic)
# -------------------------
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


# -------------------------
# Parse RP from .dat
# -------------------------
VN_RE = re.compile(r"^\s*VN\s+(\S+)\s*$")
RP_RE = re.compile(r"^\s*RP\s+(\d+)\s+([-\d.]+)\s+([-\d.eE+]+)\s*$")
TT_RE = re.compile(r"^\s*TT\s+([-\d.eE+]+)\s*$")


def _resolve_div(tag: str, file_count: int, non_gamma_div: float, gamma_div: str) -> float:
    if is_gamma(tag):
        if str(gamma_div).strip().lower() == "auto":
            return float(max(1, file_count))
        return float(gamma_div)
    return float(non_gamma_div)


def _build_normalization_audit(files: list[str], non_gamma_div: float, gamma_div: str) -> tuple[dict[str, float], dict[str, dict[str, object]]]:
    file_count_by_tag = Counter(parse_tag(fp) for fp in files)
    div_by_tag: dict[str, float] = {}
    audit: dict[str, dict[str, object]] = {}
    for tag in sorted(file_count_by_tag):
        n = int(file_count_by_tag[tag])
        div = _resolve_div(tag, n, non_gamma_div, gamma_div)
        div_by_tag[tag] = div
        audit[tag] = {
            "tag": tag,
            "files": n,
            "division": div,
            "is_gamma": is_gamma(tag),
            "gamma_div_mode": gamma_div if is_gamma(tag) else "",
            "tt_count": 0,
            "tt_files": 0,
            "tt_line_count": 0,
            "tt_sum_s": 0.0,
            "tt_mean_s": 0.0,
            "tt_min_s": None,
            "tt_max_s": None,
            "rp_raw_total": 0.0,
            "rp_scaled_total": 0.0,
            "warnings": [],
        }
    return div_by_tag, audit


def _finalize_normalization_audit(audit: dict[str, dict[str, object]], allow_div_mismatch: bool) -> list[str]:
    problems: list[str] = []
    for tag, row in audit.items():
        files = int(row["files"])
        div = float(row["division"])
        warnings = row["warnings"]
        expected = float(files)
        if abs(div - expected) > max(1.0e-9, 1.0e-6 * expected):
            msg = f"tag={tag} has {files} files but division={div:g}"
            warnings.append(msg)
            if not allow_div_mismatch:
                problems.append(msg)
        tt_files = int(row.get("tt_files", row["tt_count"]))
        tt_line_count = int(row.get("tt_line_count", row["tt_count"]))
        if tt_files == 0:
            msg = f"tag={tag} has no TT records"
            warnings.append(msg)
            problems.append(msg)
        if tt_files not in (0, files):
            msg = f"tag={tag} has TT records in {tt_files}/{files} files"
            warnings.append(msg)
            problems.append(msg)
        if tt_line_count != files:
            msg = f"tag={tag} has {tt_line_count} TT lines across {files} files; expected exactly one TT per file"
            warnings.append(msg)
            problems.append(msg)
        tt_min = row["tt_min_s"]
        tt_max = row["tt_max_s"]
        tt_mean = float(row["tt_mean_s"])
        if tt_min is not None and tt_max is not None and tt_mean > 0:
            spread = (float(tt_max) - float(tt_min)) / tt_mean
            row["tt_relative_spread"] = spread
            if spread > 0.02:
                warnings.append(f"tag={tag} TT spread is {spread:.3g}; rate uses mean TT")
    return problems


def _write_normalization_audit(outdir: Path, day_tag: int, audit: dict[str, dict[str, object]], problems: list[str]) -> None:
    rows = []
    for tag in sorted(audit):
        row = dict(audit[tag])
        row["warnings"] = "; ".join(str(x) for x in row.get("warnings", []))
        rows.append(row)
    csv_path = outdir / f"normalization_audit_day{day_tag}.csv"
    json_path = outdir / f"normalization_audit_day{day_tag}.json"
    fields = [
        "tag",
        "files",
        "division",
        "is_gamma",
        "gamma_div_mode",
        "tt_count",
        "tt_files",
        "tt_line_count",
        "tt_sum_s",
        "tt_mean_s",
        "tt_min_s",
        "tt_max_s",
        "tt_relative_spread",
        "rp_raw_total",
        "rp_scaled_total",
        "warnings",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(
        json.dumps({"status": "PASS" if not problems else "FAIL", "problems": problems, "rows": rows}, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_rp_from_dat(dat_files: list[str], non_gamma_div: float, gamma_div: str, allow_div_mismatch: bool):
    """Return:
    - tt_by_tag[tag] = mean TT seconds across files for that tag
    - rp[(tag, VN, ZA, exc_keV)] = value/div
    - normalization audit rows
    """
    rp = defaultdict(float)
    tt_by_tag: dict[str, float] = {}
    tt_values_by_tag: dict[str, list[float]] = defaultdict(list)
    div_by_tag, audit = _build_normalization_audit(dat_files, non_gamma_div, gamma_div)

    for fp in dat_files:
        tag = parse_tag(fp)
        div = float(div_by_tag[tag])
        if div <= 0:
            raise SystemExit(f"Invalid normalization division for tag={tag}: {div}")

        cur_vn = None
        tt_vals_in_file: list[float] = []
        with open_text(fp) as f:
            for line in f:
                m = TT_RE.match(line)
                if m:
                    try:
                        tt_vals_in_file.append(float(m.group(1)))
                    except Exception:
                        pass
                    continue
                m = VN_RE.match(line)
                if m:
                    cur_vn = canon_vn(m.group(1))
                    continue
                m = RP_RE.match(line)
                if m and cur_vn is not None:
                    za = int(m.group(1))
                    exc = float(m.group(2))
                    if abs(exc) < 1e-6:
                        exc = 0.0
                    val = float(m.group(3))
                    audit[tag]["rp_raw_total"] = float(audit[tag]["rp_raw_total"]) + val
                    audit[tag]["rp_scaled_total"] = float(audit[tag]["rp_scaled_total"]) + val / div
                    rp[(tag, cur_vn, za, exc)] += val / div

        audit[tag]["tt_line_count"] = int(audit[tag]["tt_line_count"]) + len(tt_vals_in_file)
        if tt_vals_in_file:
            audit[tag]["tt_files"] = int(audit[tag]["tt_files"]) + 1
            if len(tt_vals_in_file) > 1:
                audit[tag]["warnings"].append(f"{Path(fp).name} has {len(tt_vals_in_file)} TT lines")
            tt_val = tt_vals_in_file[-1]
            if tt_val > 0:
                tt_values_by_tag[tag].append(tt_val)

    for tag, vals in tt_values_by_tag.items():
        mean_tt = float(sum(vals) / len(vals))
        tt_by_tag[tag] = mean_tt
        audit[tag]["tt_count"] = len(vals)
        audit[tag]["tt_files"] = int(audit[tag]["tt_files"])
        audit[tag]["tt_sum_s"] = float(sum(vals))
        audit[tag]["tt_mean_s"] = mean_tt
        audit[tag]["tt_min_s"] = float(min(vals))
        audit[tag]["tt_max_s"] = float(max(vals))

    problems = _finalize_normalization_audit(audit, allow_div_mismatch)
    return tt_by_tag, rp, audit, problems


# -------------------------
# Parse RPIP points from SIM (CC IP RP ...)
# -------------------------
IP_RE = re.compile(
    r"^CC\s+IP\s+(?P<proc>\S+)\s+(?P<vn>\S+)\s+"
    r"(?P<x>[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?)\s+"
    r"(?P<y>[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?)\s+"
    r"(?P<z>[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?)\s+"
    r"(?P<za>\d+)\s+(?P<exc>[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?)\s+"
    r"(?P<t>[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?)"
    r"(?:\s+.*)?$"
)

@dataclass
class RPIPFileResult:
    n_lines: int
    points: dict  # (VN,ZA,exc)-> list[(x_mm,y_mm,z_mm,w)]


def _parse_one_sim_for_rpip(fp: str, div_by_tag: dict[str, float], want_proc: str) -> RPIPFileResult:
    tag = parse_tag(fp)
    div = float(div_by_tag.get(tag, 1.0))
    wfile = 1.0 / div if div > 0 else 1.0

    out = defaultdict(list)
    n = 0
    with open_text(fp) as f:
        for line in f:
            if not line.startswith("CC IP"):
                continue
            m = IP_RE.match(line.strip())
            if not m:
                continue
            proc = m.group("proc")
            if want_proc and proc != want_proc:
                continue

            vn = canon_vn(m.group("vn"))
            za = int(m.group("za"))
            exc = float(m.group("exc"))
            if abs(exc) < 1e-6:
                exc = 0.0

            # emitter wrote cm -> mm
            x_mm = float(m.group("x")) * 10.0
            y_mm = float(m.group("y")) * 10.0
            z_mm = float(m.group("z")) * 10.0

            out[(vn, za, exc)].append((x_mm, y_mm, z_mm, wfile))
            n += 1

    return RPIPFileResult(n_lines=n, points=dict(out))


def _parse_worker_wrapper(args_tuple):
    fp, div_by_tag, want_proc = args_tuple
    return _parse_one_sim_for_rpip(fp, div_by_tag, want_proc)


def parse_rpip_points_mp(sim_files: list[str], div_by_tag: dict[str, float], want_proc: str,
                         workers: int, chunksize: int):
    """Return merged_points[(VN,ZA,exc)] = list of (x_mm,y_mm,z_mm,w)"""
    merged = defaultdict(list)
    total_lines = 0

    task_args = [(f, div_by_tag, want_proc) for f in sim_files]

    # Prefer fork on Linux for speed; fall back to spawn where fork is unavailable.
    if sys.platform.startswith("linux"):
        ctx = mp.get_context("fork")
    else:
        ctx = mp.get_context("spawn")

    with ctx.Pool(processes=workers) as pool:
        it = pool.imap_unordered(_parse_worker_wrapper, task_args, chunksize=chunksize)
        for res in tqdm(it, total=len(sim_files), desc="Parsing SIM for CC IP RP", unit="file"):
            total_lines += res.n_lines
            for k, pts in res.points.items():
                merged[k].extend(pts)

    return merged, total_lines


# -------------------------
# Build axisymmetric (z-bin + r-profile) from RPIP points
# -------------------------
def build_zbins_radial_profiles(points_xyz_w, z_bins: int, r_bins: int, r_max_mm: float | None = None):
    """Return dict with:
      z_edges: (z_bins+1)
      z_weights: (z_bins) normalized
      r_edges: (r_bins+1)
      f_r_bins: list[z_bins] each (r_bins) normalized f(r)
    """
    if len(points_xyz_w) == 0:
        return None

    xs = np.array([p[0] for p in points_xyz_w], dtype=float)
    ys = np.array([p[1] for p in points_xyz_w], dtype=float)
    zs = np.array([p[2] for p in points_xyz_w], dtype=float)
    ws = np.array([p[3] for p in points_xyz_w], dtype=float)
    rs = np.sqrt(xs * xs + ys * ys)

    zmin, zmax = float(np.min(zs)), float(np.max(zs))
    if zmin == zmax:
        zmin -= 0.5
        zmax += 0.5
    z_edges = np.linspace(zmin, zmax, z_bins + 1)

    if r_max_mm is None:
        r_max_mm = float(np.percentile(rs, 99.5)) if len(rs) > 20 else float(np.max(rs))
        r_max_mm = max(r_max_mm, 1.0)
    r_edges = np.linspace(0.0, r_max_mm, r_bins + 1)

    # z bin weights
    z_idx = np.clip(np.digitize(zs, z_edges) - 1, 0, z_bins - 1)
    z_w = np.zeros(z_bins, dtype=float)
    for i in range(z_bins):
        z_w[i] = float(np.sum(ws[z_idx == i]))
    s = float(np.sum(z_w))
    if s <= 0:
        z_w[:] = 1.0 / z_bins
    else:
        z_w /= s

    # r profile per z bin: convert annulus weight -> f(r) by dividing by r_mid
    f_r_bins = []
    r_mid = 0.5 * (r_edges[:-1] + r_edges[1:])
    for i in range(z_bins):
        mask = (z_idx == i)
        if not np.any(mask):
            f_r_bins.append(np.ones(r_bins, dtype=float) / r_bins)
            continue
        ann_hist, _ = np.histogram(rs[mask], bins=r_edges, weights=ws[mask])
        f = ann_hist.astype(float)
        f = np.where(r_mid > 0, f / r_mid, f)
        tot = float(np.sum(f))
        if tot <= 0:
            f[:] = 1.0 / r_bins
        else:
            f /= tot
        f_r_bins.append(f)

    return {
        "z_edges": z_edges,
        "z_weights": z_w,
        "r_edges": r_edges,
        "f_r_bins": f_r_bins,
    }


# -------------------------
# Activity model
# -------------------------
def activity_after_exposure(N_prod: float, TT_s: float, half_life_s: float,
                            t_ground_days: float, t_flight_days: float, t_after_days: float) -> float:
    """Continuous production during (ground+flight), then decay during after."""
    if half_life_s <= 0 or TT_s <= 0:
        return 0.0
    lam = math.log(2.0) / half_life_s
    R = N_prod / TT_s
    Texp = (t_ground_days + t_flight_days) * 86400.0
    Tafter = t_after_days * 86400.0
    A_end = R * (1.0 - math.exp(-lam * Texp))
    return A_end * math.exp(-lam * Tafter)


# -------------------------
# Half-life enrichment (cache -> python lib -> NUBASE -> online)
# -------------------------
# =============================================================================
# 增强型半衰期检索系统 (Fixed-Width Parsing + Multi-Format Matching)
# =============================================================================
# =============================================================================
# 终极半衰期检索系统：针对 NUBASE 2020 固定宽度格式与 IAEA V1 API 优化
# =============================================================================

SYMS = [
    None, "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca",
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr",
    "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
    "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
    "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb",
    "Lu", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
    "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th",
    "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm",
] #

def za_to_nuclide_name(za: int) -> str:
    """ZA (ZZZAAA) -> 标准名称 (例如 He-6)"""
    Z = za // 1000
    A = za % 1000
    if Z <= 0 or Z >= len(SYMS) or SYMS[Z] is None:
        return ""
    return f"{SYMS[Z]}-{A}"

def _get_api_token(nuclide: str) -> str:
    """将 He-6 转换为 IAEA API 要求的 6He 格式"""
    if "-" not in nuclide:
        return nuclide
    sym, a = nuclide.split("-")
    return f"{a}{sym}"

def _get_nuclide_variants(nuclide: str) -> list[str]:
    """生成同位素名称的各种变体以提高匹配率"""
    if not nuclide or "-" not in nuclide:
        return [nuclide]
    sym, a = nuclide.split("-")
    # 生成 [He-6, 6He, 006He] 等变体
    return [nuclide, f"{a}{sym}", f"{int(a):03d}{sym}", f"{sym}{a}"]

def _robust_unit_to_seconds(val_str: str, unit_str: str = "") -> float | None:
    """极其稳健的单位换算器，处理 stbl 标记及 NUBASE 专用单位"""
    s = str(val_str).strip().lower()
    if not s or any(x in s for x in ["stbl", "stable", "inf"]):
        return float("inf")
    
    # 移除 NUBASE 常见的修饰符和统计标记 (#, ?, >, <, ~)
    s = re.sub(r"[#?><~*&]", "", s).strip()
    
    try:
        if not unit_str:
            # 尝试从数值末尾直接提取单位
            m = re.match(r"^([0-9.+-Ee]+)\s*([a-zA-Zµμ]+)$", s)
            if m:
                val, u = float(m.group(1)), m.group(2)
            else:
                val, u = float(s), "s"
        else:
            val, u = float(s), unit_str.strip().lower()
            
        u = u.replace("μ", "u").replace("µ", "u")
        # 支持 NUBASE 的 'y' (year) 等缩写
        mult = {
            "ps": 1e-12, "ns": 1e-9, "us": 1e-6, "ms": 1e-3, 
            "s": 1.0, "sec": 1.0, "m": 60.0, "min": 60.0, 
            "h": 3600.0, "hr": 3600.0, "d": 86400.0, "day": 86400.0,
            "y": 31557600.0, "yr": 31557600.0, "year": 31557600.0
        }
        return val * mult.get(u, 1.0)
    except:
        return None

def load_cache(path: Path) -> dict[str, float]:
    """从 JSON 加载缓存，确保 inf 正确转换"""
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return {str(k): (float("inf") if str(v).lower()=="inf" else float(v)) for k, v in obj.items()}
    except:
        return {}

def save_cache(path: Path, cache: dict[str, float]):
    """保存缓存，将 inf 存储为字符串"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        out = {k: ("inf" if v == float("inf") else v) for k, v in cache.items()}
        path.write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    except:
        pass

def half_life_from_radioactivedecay(nuclide: str) -> tuple[float | None, str]:
    """尝试使用本地 Python 物理库查找"""
    if not nuclide:
        return None, "no_nuclide"
    variants = _get_nuclide_variants(nuclide)
    for rd_lib in ["radioactivedecay", "radiodecay"]:
        try:
            rd = __import__(rd_lib)
            for v in variants:
                try:
                    n = rd.Nuclide(v)
                    hl = float(n.half_life("s"))
                    if math.isfinite(hl) and hl >= 0:
                        return (float("inf") if hl == 0 else hl), f"{rd_lib}_ok"
                except:
                    continue
        except ImportError:
            continue
    return None, "no_python_lib"

def nubase_auto_download(nubase_path: Path) -> tuple[bool, str]:
    """自动获取 NUBASE2020 离线文本库"""
    try:
        import requests
        urls = ["https://www-nds.iaea.org/amdc/ame2020/nubase_4.mas20.txt", 
                "https://www-nds.iaea.org/amdc/ame2020/nubase_2020.txt"]
        for url in urls:
            try:
                r = requests.get(url, timeout=20)
                if r.status_code == 200 and len(r.text) > 100000:
                    nubase_path.parent.mkdir(parents=True, exist_ok=True)
                    nubase_path.write_text(r.text, encoding="utf-8")
                    return True, f"downloaded:{url}"
            except:
                continue
    except:
        return False, "requests_missing"
    return False, "download_failed"

def nubase_fill_half_lives(nubase_path: Path, needed: set[str]) -> dict[str, tuple[float, str]]:
    """
    Robust NUBASE2020 parser:
    match by (Z, A) from fixed columns instead of A El string.
    Columns (1-indexed in NUBASE doc):
      1:3   AAA
      5:8   ZZZi   (ZZZ + i state index)
      70:78 T
      79:80 unit
    """
    found: dict[str, tuple[float, str]] = {}
    if not nubase_path.exists() or not needed:
        return found

    # build needed (Z,A)-> nuclide string mapping, e.g. (6,16)->"C-16"
    need_ZA = {}
    for nu in needed:
        if "-" not in nu:
            continue
        sym, a = nu.split("-", 1)
        try:
            A = int(a)
        except:
            continue
        # reverse lookup symbol -> Z
        Z = None
        for zi in range(1, len(SYMS)):
            if SYMS[zi] == sym:
                Z = zi
                break
        if Z is not None:
            need_ZA[(Z, A)] = nu

    with nubase_path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if not line or line.startswith("#"):
                continue
            if len(line) < 90:
                continue

            try:
                # AAA (col 1:3) -> python [0:3]
                AAA = line[0:3].strip()
                # ZZZi (col 5:8) -> python [4:8]
                ZZZi = line[4:8].strip()
                if not AAA or not ZZZi:
                    continue

                A = int(AAA)
                Z = int(ZZZi[:3])   # first 3 chars are ZZZ
                i_state = ZZZi[3:] if len(ZZZi) > 3 else "0"  # i=0 gs
                # 我们这里默认只取基态（i=0），不区分 isomer
                if i_state not in ("", "0"):
                    continue

                nu = need_ZA.get((Z, A))
                if not nu or nu in found:
                    continue

                hl_val = line[69:78].strip().lower()   # T
                hl_unit = line[78:80].strip().lower()  # unit

                if "stbl" in hl_val or "stable" in hl_val:
                    found[nu] = (float("inf"), "nubase_stable")
                else:
                    sec = _robust_unit_to_seconds(hl_val, hl_unit)
                    if sec is not None:
                        found[nu] = (sec, "nubase")
            except:
                continue

    return found
def online_fill_half_life_livechart(nuclide: str, timeout_s: float = 12.0) -> tuple[float | None, str]:
    """增强版在线爬虫：优先 V1 JSON 接口，失败则进行文本暴力特征匹配"""
    try:
        import requests
    except:
        return None, "requests_missing"

    # 关键修改：IAEA 要求的查询格式是 6He 而不是 He-6
    token = _get_api_token(nuclide)
    url = "https://www-nds.iaea.org/relnsd/v1/data/nuclides"
    
    try:
        r = requests.get(url, params={"nuclides": token}, timeout=timeout_s)
        if r.status_code != 200:
            return None, f"http_{r.status_code}"
        
        if not r.text.strip():
            return None, "empty_response"
        
        # 1. 尝试标准 V1 JSON 解析
        try:
            data = r.json()
            items = data.get("data", [])
            if items:
                it = items[0]
                hl_raw = str(it.get("halfLife", "")).lower()
                # 前置稳定判定
                if "stable" in hl_raw or "stable" in str(it.get("decayMode","")).lower():
                    return float("inf"), "livechart_stable"
                
                val = it.get("halfLifeValue")
                if val is not None:
                    unit = it.get("halfLifeUnit", "s")
                    return _robust_unit_to_seconds(val, unit), "livechart_json"
        except:
            pass

        # 2. 暴力正则备份 (应对 API 格式降级或返回 HTML 情况)
        txt = r.text.lower()
        if "stable" in txt:
            return float("inf"), "livechart_txt_stable"
        # 搜索文本中的 half-life 关键字
        m = re.search(r"half[_\s-]*life[^0-9]*([0-9.+-Ee]+)\s*([a-zµμ]+)", txt)
        if m:
            sec = _robust_unit_to_seconds(m.group(1), m.group(2))
            if sec:
                return sec, "livechart_regex"

    except Exception as e:
        return None, f"net_err_{type(e).__name__}"
    
    return None, "not_found_online"

def build_half_life_db(nuclides: set[str], cache_path: Path, nubase_path: Path,
                       nubase_auto: bool, online_fallback: bool, online_timeout: float,
                       threads: int) -> tuple[dict[str, float], dict[str, str], dict[str, str]]:
    """四级联动半衰期查找引擎：Cache -> Lib -> NUBASE (重对齐版) -> Online"""
    cache = load_cache(cache_path)
    hl_map, why_map, failed = {}, {}, {}

    # 第一级：本地缓存
    for nu in nuclides:
        if nu in cache:
            hl_map[nu] = cache[nu]; why_map[nu] = "cache"

    # 第二级：物理库 (radioactivedecay)
    for nu in [n for n in sorted(nuclides) if n not in hl_map]:
        hl, why = half_life_from_radioactivedecay(nu)
        if hl is not None: 
            hl_map[nu], why_map[nu] = hl, why; cache[nu] = hl

    # 第三级：核心重型解析 - 离线 NUBASE 文件
    unknown = [n for n in sorted(nuclides) if n not in hl_map]
    if unknown:
        if nubase_auto and not nubase_path.exists(): 
            nubase_auto_download(nubase_path)
        if nubase_path.exists():
            nb_data = nubase_fill_half_lives(nubase_path, set(unknown))
            for nu, (hl, why) in nb_data.items():
                hl_map[nu], why_map[nu] = hl, why; cache[nu] = hl

    # 第四级：在线多线程 fallback
    unknown = [n for n in sorted(nuclides) if n not in hl_map]
    if unknown and online_fallback:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=threads) as ex:
            futs = {ex.submit(online_fill_half_life_livechart, nu, online_timeout): nu for nu in unknown}
            for fut in tqdm(as_completed(futs), total=len(futs), desc="Half-life Online", unit="iso"):
                nu = futs[fut]
                try:
                    hl, why = fut.result()
                    if hl is not None:
                        hl_map[nu], why_map[nu] = hl, why; cache[nu] = hl
                    else:
                        failed[nu] = why
                except Exception as e:
                    failed[nu] = f"exc({e})"

    save_cache(cache_path, cache)
    for nu in nuclides:
        if nu not in hl_map and nu not in failed:
            failed[nu] = "not_found_after_all_steps"
    return hl_map, why_map, failed

# -------------------------
# Cosima source writing
# -------------------------
def fmt(x: float) -> str:
    return f"{x:.6g}"


def safe_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", s)

'''
def write_radial_profile_dat(path: Path, r_edges_mm: np.ndarray, f_r: np.ndarray):
    path.parent.mkdir(parents=True, exist_ok=True)
    r_mid = 0.5 * (r_edges_mm[:-1] + r_edges_mm[1:])
    with path.open("w", encoding="utf-8") as f:
        f.write("# r_cm   f(r)  (normalized; MEGAlib samples ~ r*f(r))\n")
        for rmm, fr in zip(r_mid, f_r):
            f.write(f"{fmt(float(rmm/10.0))} {fmt(float(fr))}\n")


def emit_source_block(out, name: str, za: int, exc_keV: float,
                      z0_mm: float, z1_mm: float, profile_file: str,
                      activity_per_s: float, n_particles: int):
    out.write(f"\n# {name}\n")
    out.write(f"{name}.Beam RadialProfileBeam\n")
    out.write(f"{name}.Beam.ProfileFile {profile_file}\n")
    out.write(f"{name}.Beam.Z {fmt(z0_mm/10.0)} {fmt(z1_mm/10.0)}\n")
    out.write(f"{name}.Beam.Phi 0 360\n")
    out.write(f"{name}.Spectrum Mono\n")
    out.write(f"{name}.Spectrum.Energy 0\n")
    out.write(f"{name}.Particles Ion {za} {fmt(exc_keV)}\n")
    out.write(f"{name}.Flux {fmt(activity_per_s)}\n")
    out.write(f"{name}.Beam.NParticles {int(n_particles)}\n")
'''
# -------------------------
# 恢复 1.0 版本的写入逻辑
# -------------------------
def write_radial_profile_dat(path: Path, r_edges_mm: np.ndarray, f_r: np.ndarray):
    path.parent.mkdir(parents=True, exist_ok=True)
    r_mid = 0.5 * (r_edges_mm[:-1] + r_edges_mm[1:])
    with path.open("w", encoding="utf-8") as f:
        f.write("# r_cm   f(r)  (normalized; MEGAlib samples ~ r*f(r))\n")
        for rmm, fr in zip(r_mid, f_r):
            # 将 mm 转换为 cm
            f.write(f"{float(rmm/10.0):.6g} {float(fr):.6g}\n")

def write_cosima_source(path: Path, geometry_path: str, run_name: str,
                        triggers: int, outfile_prefix: str, entries):
    """还原 1.0 语法的全局配置与源定义"""
    lines = []
    lines.append("Version 1")
    # --- 核心修复：强制转换为绝对路径 ---
    abs_geo_path = str(Path(geometry_path).resolve())
    lines.append(f"Geometry {abs_geo_path}")
    # -------------------------------
    lines.append("")
    
    # 物理列表与模式设置 (1.0 核心逻辑)
    lines.append("PhysicsListHD qgsp-bic-hp")
    lines.append("PhysicsListEM LivermorePol")
    lines.append("PhysicsListRadioactiveDecay true")
    lines.append("DecayMode ActivationDelayedDecay") # 自动处理衰变
    
    lines.append("StoreSimulationInfo all")
    lines.append("StoreIsotopes true")
    lines.append("DetectorTimeConstant 1e-9")
    lines.append("")
    
    lines.append(f"Run {run_name}")
    lines.append(f"{run_name}.FileName {outfile_prefix}")
    lines.append(f"{run_name}.Triggers {int(triggers)}")
    lines.append("")

    # 注册所有 Source
    for e in entries:
        lines.append(f"{run_name}.Source {e['name']}")

    lines.append("\n# ===== Sources =====")
    for e in entries:
        name = e["name"]
        za = int(e["za"])
        # 使用绝对路径确保 cosima 能找到剖面文件
        prof_abs = str(Path(e["profile_file"]).resolve())

        # 核心修改：使用 ParticleType ZA 码
        lines.append(f"{name}.ParticleType {za}")
        
        # 核心修改：还原单行单行 Beam 声明格式
        # 格式：Beam 类型 x y z dx dy dz 剖面路径
        lines.append(
            f"{name}.Beam RadialProfileBeam "
            f"{e['x_cm']:.6f} {e['y_cm']:.6f} {e['z_cm']:.6f}  "
            f"{e['dx']:.6f} {e['dy']:.6f} {e['dz']:.6f}  "
            f"{prof_abs}"
        )
        lines.append(f"{name}.Flux {e['rate']:.8e}")
        lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
# -------------------------
# Integrated plot-check
# -------------------------
def load_bounds(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def plot_integrated(bounds: dict, rpip_points_mm: list[tuple[float, float, float]],
                    sampled_points_mm: list[tuple[float, float, float]], out_png: Path, title: str,
                    max_points: int):
    # downsample to keep plot size reasonable
    rng = random.Random(123)
    if len(rpip_points_mm) > max_points:
        rpip_points_mm = rng.sample(rpip_points_mm, max_points)
    if len(sampled_points_mm) > max_points:
        sampled_points_mm = rng.sample(sampled_points_mm, max_points)

    fig = plt.figure(figsize=(7, 10))
    ax = fig.add_subplot(111)

    for item in bounds.get("rects", []):
        x0 = item["x0"]; x1 = item["x1"]; z0 = item["z0"]; z1 = item["z1"]
        ax.add_patch(plt.Rectangle((x0, z0), x1 - x0, z1 - z0, fill=False, linewidth=1))

    def signed_r(points):
        xs = np.array([p[0] for p in points], dtype=float)
        ys = np.array([p[1] for p in points], dtype=float)
        zs = np.array([p[2] for p in points], dtype=float)
        rr = np.sqrt(xs * xs + ys * ys) * np.sign(xs)
        return rr, zs

    if rpip_points_mm:
        rr, zz = signed_r(rpip_points_mm)
        ax.scatter(rr, zz, s=6, marker='.', label="RPIP points")

    if sampled_points_mm:
        rr, zz = signed_r(sampled_points_mm)
        ax.scatter(rr, zz, s=6, marker='x', label="sampled from PDF")

    ax.set_xlabel("signed r (mm)")
    ax.set_ylabel("z (mm)")
    ax.set_title(title)
    ax.legend(loc="best", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_png, dpi=200)
    plt.close(fig)


def sample_from_profile(z_edges: np.ndarray, z_weights: np.ndarray,
                        r_edges: np.ndarray, f_r_bins: list[np.ndarray],
                        n: int, rng: random.Random):
    """Sample n points (x_mm,y_mm,z_mm) from the axisymmetric PDF."""
    if n <= 0:
        return []
    z_bins = len(z_weights)
    # discrete z bin
    z_cdf = np.cumsum(z_weights)
    # prepare r CDF per bin for annulus pdf ~ r*f(r)
    r_mid = 0.5 * (r_edges[:-1] + r_edges[1:])
    r_ann_cdfs = []
    for fr in f_r_bins:
        ann = np.maximum(0.0, r_mid * np.asarray(fr, dtype=float))
        s = float(np.sum(ann))
        if s <= 0:
            ann = np.ones_like(ann) / len(ann)
        else:
            ann = ann / s
        r_ann_cdfs.append(np.cumsum(ann))

    out = []
    for _ in range(n):
        u = rng.random()
        iz = int(np.searchsorted(z_cdf, u, side="right"))
        iz = min(max(iz, 0), z_bins - 1)
        # z uniform within bin
        z0 = float(z_edges[iz]); z1 = float(z_edges[iz + 1])
        z = z0 + (z1 - z0) * rng.random()

        # r bin
        uc = rng.random()
        rcdf = r_ann_cdfs[iz]
        ir = int(np.searchsorted(rcdf, uc, side="right"))
        ir = min(max(ir, 0), len(r_edges) - 2)
        r0 = float(r_edges[ir]); r1 = float(r_edges[ir + 1])
        r = r0 + (r1 - r0) * rng.random()

        phi = 2.0 * math.pi * rng.random()
        x = r * math.cos(phi)
        y = r * math.sin(phi)
        out.append((x, y, z))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dat", required=True, help='Glob for *.dat or *.dat.gz')
    ap.add_argument("--sim", required=True, help='Glob for *.sim or *.sim.gz')
    # 补充 1.0 所需的几何参数路径
    ap.add_argument("--geo", default=str(Path(__file__).resolve().parents[1] / "XZTES" / "TibetTES_v5_6layers.geo.setup"))
    ap.add_argument("--non-gamma-div", type=float, default=8.0)
    ap.add_argument(
        "--gamma-div",
        default="auto",
        help="gamma split normalization divisor; use 'auto' to divide by the number of gamma files",
    )
    ap.add_argument(
        "--allow-div-mismatch",
        action="store_true",
        help="write the normalization audit but do not stop if file count and divisor differ",
    )

    ap.add_argument("--t-ground-days", type=float, default=0.0,
                    help="pre-flight ground exposure days (0 if none)")
    ap.add_argument("--t-flight-days", type=float, default=15.0)
    ap.add_argument("--t-after-days", type=float, default=0.0)

    ap.add_argument("--outdir", default="decay_rpip_out")
    ap.add_argument("--profile-dir", default="profiles", help="relative to outdir")
    ap.add_argument("--outfile-prefix", default="DelayedDecayRPIP")
    ap.add_argument("--triggers", type=int, default=1000000)

    ap.add_argument("--z-bins", type=int, default=60)
    ap.add_argument("--r-bins", type=int, default=100)
    ap.add_argument("--min-points", type=int, default=15,
                    help="min RPIP points for a (VN,ZA,exc) profile; else isotope is skipped")
    ap.add_argument("--n-sample", type=int, default=2000000,
                    help="NParticles per z-bin source")

    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 8) - 2))
    ap.add_argument("--chunksize", type=int, default=1)

    # half-life options
    ap.add_argument("--cache", default="half_life_cache.json")
    ap.add_argument("--nubase", default="nubase_2020.txt")
    ap.add_argument("--nubase-auto-download", action="store_true")
    ap.add_argument("--online-fallback", action="store_true")
    ap.add_argument("--online-timeout", type=float, default=8.0)
    ap.add_argument("--online-threads", type=int, default=12)

    # plot-check
    ap.add_argument("--bounds", default="", help="bounds.json for plot-check")
    ap.add_argument("--plot-check", action="store_true")
    ap.add_argument("--plot-max-points", type=int, default=12000)
    ap.add_argument("--seed", type=int, default=123)
    ap.add_argument("--plot-top-keys", type=int, default=5,
                    help="for integrated plot, include RPIP points from top-N activity keys")

    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    profile_dir = outdir / args.profile_dir
    profile_dir.mkdir(parents=True, exist_ok=True)

    import glob
    dat_files = sorted(glob.glob(args.dat))
    sim_files = sorted(glob.glob(args.sim))
    if not dat_files:
        raise SystemExit(f"No dat files matched: {args.dat}")
    if not sim_files:
        raise SystemExit(f"No sim files matched: {args.sim}")

    z_bins = max(1, int(args.z_bins))
    r_bins = max(1, int(args.r_bins))

    day_tag = int(round(args.t_ground_days + args.t_flight_days)) or 1

    # ---- 1) RP totals
    print("[1/5] Parsing .dat (TT/VN/RP)")
    tt_by_tag, rp, norm_audit, norm_problems = parse_rp_from_dat(
        dat_files,
        args.non_gamma_div,
        args.gamma_div,
        args.allow_div_mismatch,
    )
    _write_normalization_audit(outdir, day_tag, norm_audit, norm_problems)
    if norm_problems:
        raise SystemExit(
            "Normalization audit failed. Re-run with the correct --non-gamma-div/"
            "--gamma-div, or use --allow-div-mismatch for an explicit diagnostic run. "
            + " ; ".join(norm_problems)
        )
    if not rp:
        raise SystemExit("No RP entries found in dat files")
    div_by_tag = {tag: float(row["division"]) for tag, row in norm_audit.items()}

    # ---- 2) RPIP points
    print("[2/5] Parsing SIM for CC IP RP (multiprocessing)")
    rpip_merged, n_lines = parse_rpip_points_mp(
        sim_files, div_by_tag, want_proc="RP",
        workers=max(1, int(args.workers)), chunksize=max(1, int(args.chunksize)),
    )
    print(f"[INFO] CC IP RP lines parsed = {n_lines:,} ; RPIP keys={len(rpip_merged)}")

    # ---- 3) half-life enrichment
    print("[3/5] Half-life enrichment (cache -> python lib -> NUBASE -> online)")
    needed_nuclides = set()
    for (_tag, _vn, za, _exc) in rp.keys():
        nu = za_to_nuclide_name(za)
        if nu: needed_nuclides.add(nu)
    
    hl_map, hl_why, hl_failed = build_half_life_db(
        nuclides=needed_nuclides, cache_path=outdir / args.cache, nubase_path=outdir / args.nubase,
        nubase_auto=args.nubase_auto_download, online_fallback=args.online_fallback,
        online_timeout=float(args.online_timeout), threads=int(args.online_threads),
    )
    print(f"[INFO] half-life resolved: {len(hl_map)}/{len(needed_nuclides)}")

    # ---- 4) build profiles per (VN,ZA,exc)
    print("[4/5] Building axisymmetric profiles from RPIP points")
    profiles = {}
    profile_files = {} # (vn,za,exc,iz)-> relative path
    for (vn, za, exc), pts in tqdm(rpip_merged.items(), desc="Profiles", unit="key"):
        if len(pts) < int(args.min_points): continue
        info = build_zbins_radial_profiles(pts, z_bins=z_bins, r_bins=r_bins)
        if info is None: continue
        profiles[(vn, za, exc)] = info
        
        base = profile_dir / safe_name(vn) / f"ZA{za}_exc{int(round(exc*1e6))}"
        for iz in range(len(info["z_weights"])):
            if info["z_weights"][iz] <= 0: continue # 跳过无产出的层
            pfile = base / f"radial_z{iz:03d}.dat"
            write_radial_profile_dat(pfile, info["r_edges"], info["f_r_bins"][iz])
            profile_files[(vn, za, exc, iz)] = os.path.relpath(pfile, outdir)
    print(f"[INFO] profiles built = {len(profiles)}")

    # ---- 5) compute activities and gather source entries (还原 1.0 逻辑)
    print("[5/5] Computing inventory and gathering source entries")
    out_source = outdir / f"activation_decay_day{day_tag}.source"
    out_inv = outdir / f"activation_inventory_day{day_tag}.csv"
    out_unk = outdir / f"unknown_isotopes_day{day_tag}.csv"
    out_nop = outdir / f"no_rpip_points_day{day_tag}.csv"

    source_entries = [] # 存储 1.0 风格的源列表
    inv_rows, unk_rows, nop_rows = [], [], []
    activity_sum = defaultdict(float)
    yield_sum = defaultdict(float)
    rng = random.Random(int(args.seed))

    for (tag, vn, za, exc), Nprod in rp.items():
        TT = float(tt_by_tag.get(tag, 1.0))
        nu = za_to_nuclide_name(za)
        hl = hl_map.get(nu)
        if hl is None or hl == float("inf") or not (math.isfinite(hl) and hl > 0):
            unk_rows.append([tag, vn, za, exc, nu, "SKIPPED/UNKNOWN", str(hl)])
            continue
        A = activity_after_exposure(Nprod, TT, hl, args.t_ground_days, args.t_flight_days, args.t_after_days)
        if A > 0:
            activity_sum[(vn, za, exc)] += A
            yield_sum[(vn, za, exc)] += Nprod

    # 选取 top keys 用于绘图
    top_keys = sorted(activity_sum.items(), key=lambda kv: kv[1], reverse=True)[: max(1, int(args.plot_top_keys))]
    plot_rpip_pts, plot_samp_pts = [], []

    for (vn, za, exc), A in sorted(activity_sum.items(), key=lambda kv: kv[1], reverse=True):
        prof = profiles.get((vn, za, exc))
        pts = rpip_merged.get((vn, za, exc), [])
        if prof is None or len(pts) < int(args.min_points):
            nop_rows.append([vn, za, exc, len(pts), "NO_PROFILE_OR_TOO_FEW_POINTS"])
            continue

        nu = za_to_nuclide_name(za)
        inv_rows.append([vn, za, nu, exc, yield_sum.get((vn, za, exc)), hl_map.get(nu), A, len(pts)])

        z_edges = prof["z_edges"]
        z_w = prof["z_weights"]
        Wtot = sum(z_w)

        # 按层分发活度到源条目
        for iz, frac in enumerate(z_w):
            if frac <= 0: continue
            pfile_rel = profile_files.get((vn, za, exc, iz))
            if not pfile_rel: continue
            
            # 计算 Z 中心 (cm) 并存入 entries 列表
            z_center_cm = (z_edges[iz] + z_edges[iz+1]) / 20.0
            source_entries.append({
                "name": f"S_{safe_name(vn)}_{za}_z{iz:03d}",
                "za": int(za),
                "rate": float(A * (frac / Wtot)),
                "x_cm": 0.0, "y_cm": 0.0, "z_cm": float(z_center_cm),
                "dx": 0.0, "dy": 0.0, "dz": 1.0,
                "profile_file": str(outdir / pfile_rel)
            })

        # 绘图点收集
        if args.plot_check and any((vn, za, exc) == k for (k, _A) in top_keys):
            plot_rpip_pts.extend([(p[0], p[1], p[2]) for p in pts])
            samp = sample_from_profile(prof["z_edges"], prof["z_weights"], prof["r_edges"], prof["f_r_bins"],
                                       min(len(pts), int(args.plot_max_points) // 5), rng)
            plot_samp_pts.extend(samp)

    # 统一写入 .source 文件
    write_cosima_source(out_source, args.geo, "DecayRun", args.triggers, args.outfile_prefix, source_entries)

    # 写入 CSV
    with out_inv.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["VN", "ZA", "nuclide", "exc_keV", "RP_yield", "hl_s", "Activity_Bq", "Points"])
        csv.writer(f).writerows(inv_rows)
    with out_unk.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["tag", "VN", "ZA", "exc_keV", "nuclide", "reason", "detail"])
        csv.writer(f).writerows(unk_rows)
    with out_nop.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["VN", "ZA", "exc_keV", "N_Points", "reason"])
        csv.writer(f).writerows(nop_rows)

    # 绘图逻辑
    if args.plot_check and args.bounds:
        plot_integrated(load_bounds(args.bounds), plot_rpip_pts, plot_samp_pts, 
                        outdir / f"plot_check_day{day_tag}.png", 
                        f"RPIP Check day{day_tag}", int(args.plot_max_points))

    # 计算归一化信息
    total_activity_bq = sum(e['rate'] for e in source_entries)
    print("\n" + "="*40 + f"\n归一化信息:\n  总活度: {total_activity_bq:.6e} Bq\n  归一化系数: {total_activity_bq / float(args.triggers):.6e} (Bq/count)\n" + "="*40)
    print(f"[OK] wrote: {out_source}")


if __name__ == "__main__":
    main()
