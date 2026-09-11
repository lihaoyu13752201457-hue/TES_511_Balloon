#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
HtsimPromptDelayMerge_windowAttrib_v6p2_paperstyle.py

在 v6p1 基础上：把分析口径改得更贴近论文 Fig.9 + Fig.10。

核心改动：
1) Prompt + Delayed 都做同一套 “TES-only + window-filtered” 的归因统计：
   - particle types：用 CC HIT 的 sec（能量加权）
   - creation processes：用 CC HIT 的 cproc（能量加权）
     * 把 RadioactiveDecay 映射为 Radioactivation（贴论文标签）
     * 把 primary 映射为 Primary（贴论文标签）
   - creation volumes：用 hit position -> identify_vol -> geom_group（能量加权）
2) 输出 “TOTAL (prompt×scale + delayed)” 的三张饼图（Fig.10 风格）：
   - total_pass_particle_types_pie.png  (secE)
   - total_pass_creation_volume_pie.png (geomE)
   - total_pass_creation_process_pie.png(cprocE)
   只显示占比 >=4% 的分量，其余合并为 others（贴论文图注）
3) 输出 Fig.9 风格的“分量占比”（先不用 cps，按 window 内归一化计数）：
   - prompt: 按文件 tag 的 pass+window 事件计数（再乘 prompt_scale）
   - delayed: 按核素 iso 的 pass+window 事件计数
   - 输出各自分量占比 + 相对 TOTAL 的占比

保留 v6p1 原有输出：
- tes_spectrum_total.csv + fig_total_raw_pass.png
- prompt_eventcount_by_tag_raw/pass_window.csv + pie
- delayed_iso_raw/pass_window.csv + TopN bar
- (可选) buildup 的 CC IP RP 溯源统计

用法同 v6p1。
"""

from __future__ import annotations

import re
import gzip
import math
import json
import glob
import argparse
from pathlib import Path
from multiprocessing import Pool, cpu_count
from collections import defaultdict

import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm


# -----------------------------------------------------------------------------
# bounds.json helpers
# -----------------------------------------------------------------------------
def load_bounds(bounds_path: str) -> dict:
    txt = Path(bounds_path).read_text(encoding="utf-8", errors="ignore").strip()
    if not txt:
        raise SystemExit(f"[ERROR] bounds file empty: {bounds_path}")
    if not txt.lstrip().startswith("{"):
        i0 = txt.find("{")
        i1 = txt.rfind("}")
        if i0 >= 0 and i1 > i0:
            txt = txt[i0:i1 + 1]
    try:
        return json.loads(txt)
    except Exception as e:
        raise SystemExit(f"[ERROR] bounds json parse failed: {e}")


def in_shell(r, z, s):
    if s["z_out_bot"] <= z <= s["z_in_bot"] and r <= s["r_out"]:
        return True
    if s["z_in_bot"] <= z <= s["z_in_top"] and (s["r_in"] <= r <= s["r_out"]):
        return True
    if s["z_in_top"] <= z <= s["z_out_top"] and (s["hole_r"] <= r <= s["r_out"]):
        return True
    return False


def identify_vol(x, y, z, b):
    r = math.hypot(x, y)

    # Copper
    for name in ["CU_BASE", "CU_SUPPORT"]:
        obj = b.get(name)
        if obj and obj["z_bot"] <= z <= obj["z_top"] and r <= obj["r_max"]:
            return "Copper"

    # TES layers
    for i, t in enumerate(b.get("TES_LAYERS", [])):
        if abs(z - t["z_center"]) <= (t["hz"] + 0.05) and r <= (t["r_max"] + 0.05):
            return f"TES_L{i}"

    # Windows
    for w in b.get("WINDOWS", []):
        if abs(z - w["z_center"]) <= (w["thick"] / 2.0 + 0.01) and r <= w["r_max"]:
            return "Window"

    # Collimator
    c = b.get("COLLIMATOR")
    if c and abs(z - c["z_center"]) <= (c["hz"] + 0.01) and r <= c["r_max"]:
        return "Collimator"

    # Shields
    for name, s in b.get("SHIELDS", {}).items():
        if in_shell(r, z, s):
            return name

    return "Other"


# -----------------------------------------------------------------------------
# prompt tag parsing for weighting + event-count attribution
# -----------------------------------------------------------------------------
TAG_RE = re.compile(r"Background_(?P<tag>[^_]+)_", re.IGNORECASE)

FALLBACK_TAGS = [
    ("gamma",   ["_gamma_", "background_gamma", "gamma"]),
    ("p",       ["_p_", "proton"]),
    ("n",       ["_n_", "neutron"]),
    ("alpha",   ["_alpha_", "alpha"]),
    ("muplus",  ["muplus", "mu+"]),
    ("muminus", ["muminus", "mu-"]),
    ("eplus",   ["eplus", "e+"]),
    ("eminus",  ["eminus", "e-"]),
]


def parse_tag_from_name(fp: str) -> str:
    name = Path(fp).name.lower()
    m = TAG_RE.search(name)
    if m:
        return m.group("tag").lower()
    for tag, keys in FALLBACK_TAGS:
        for k in keys:
            if k in name:
                return tag
    return "unknown"


def is_gamma(tag: str) -> bool:
    return tag.lower() == "gamma"


# -----------------------------------------------------------------------------
# VN canonicalization for build-up stats (CC IP RP)
# -----------------------------------------------------------------------------
RE_SEG_SHIELD = re.compile(r"^(Nb_Shield|W_Shield|Cryo_Shell|BGO_Shield|Al_Shell)(?:_p\d+_z\d+)?$", re.I)
RE_TP_NAME = re.compile(r"^TP_L(?P<l>\d+)_(?P<idx>\d+)$", re.I)
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

    m = RE_TP_NAME.match(n)
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


# -----------------------------------------------------------------------------
# IO
# -----------------------------------------------------------------------------
def open_text_gz(path: str):
    return gzip.open(path, "rt", encoding="utf-8", errors="ignore")


# -----------------------------------------------------------------------------
# CC parsing
# -----------------------------------------------------------------------------
KV_RE = re.compile(r"(\b[a-zA-Z_]+)=([^\s]+)")
IP_RE = re.compile(
    r"^CC\s+IP\s+(?P<proc>\S+)\s+(?P<vn>\S+)\s+"
    r"(?P<x>[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?)\s+"
    r"(?P<y>[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?)\s+"
    r"(?P<z>[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?)\s+"
    r"(?P<za>\d+)\s+(?P<exc>[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?)\s+"
    r"(?P<t>[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?)"
    r"(?:\s+.*)?$"
)


def kv_dict(line: str) -> dict:
    return dict(KV_RE.findall(line))


def parse_cc_hit(line: str):
    if not line.startswith("CC HIT"):
        return None
    parts = line.strip().split()
    if len(parts) < 3:
        return None
    vol = parts[2]
    kv = kv_dict(line)
    try:
        edep = float(kv.get("edep_keV", "0"))
    except Exception:
        edep = 0.0

    def fget(k, default="0"):
        try:
            return float(kv.get(k, default))
        except Exception:
            return 0.0

    return {
        "vol": vol,
        "edep": edep,
        "x": fget("x"),
        "y": fget("y"),
        "z": fget("z"),
        "prim": kv.get("prim", "NA"),
        "sec": kv.get("sec", "NA"),
        "par": kv.get("par", "NA"),
        "sproc": kv.get("sproc", "NA"),
        "cproc": kv.get("cproc", "NA"),
    }


def parse_cc_ip_rp(line: str):
    if not line.startswith("CC IP"):
        return None
    m = IP_RE.match(line.strip())
    if not m:
        return None
    if m.group("proc") != "RP":
        return None
    kv = kv_dict(line)
    try:
        za = int(m.group("za"))
    except Exception:
        return None
    nu = za_to_nuclide_name(za).replace("-", "")  # "W183"
    return {
        "nu": nu,
        "vn": canon_vn(m.group("vn")),
        "par": kv.get("par", "NA"),
    }


# -----------------------------------------------------------------------------
# ZA -> nuclide
# -----------------------------------------------------------------------------
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
]


def za_to_nuclide_name(za: int) -> str:
    Z = za // 1000
    A = za % 1000
    if Z <= 0 or Z >= len(SYMS) or SYMS[Z] is None:
        return ""
    return f"{SYMS[Z]}-{A}"


# -----------------------------------------------------------------------------
# HTsim parsing
# -----------------------------------------------------------------------------
def parse_htsim_fast(line: str):
    try:
        parts = line.split(";", 5)
        return float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
    except Exception:
        return None


# -----------------------------------------------------------------------------
# TP mapping + geometry grouping
# -----------------------------------------------------------------------------
def build_tp_idx_map(tp_npix: int, tp_pitch: float, tp_eff_r: float):
    n = int(tp_npix)
    pitch = float(tp_pitch)
    eff_r = float(tp_eff_r)
    x0 = -((n * pitch) / 2.0) + (pitch / 2.0)
    y0 = x0

    idx2 = {}
    idx = 0
    for i in range(n):
        for j in range(n):
            x = x0 + i * pitch
            y = y0 + j * pitch
            r = math.hypot(x, y)
            if r < eff_r:
                idx2[idx] = {"i": i, "j": j}
                idx += 1
    return idx2


def tp_label(vol: str, cfg) -> str:
    m = RE_TP_NAME.match(vol)
    if not m:
        return vol
    l = int(m.group("l"))
    idx = int(m.group("idx"))
    base = f"TES_L{l}"
    mode = cfg.tp_mode

    if mode == "layer":
        return base

    info = cfg.tp_idx_map.get(idx)
    if info is None:
        if mode == "idx":
            return f"{base}_pix{idx}"
        if mode == "ij":
            return f"{base}_(i=?,j=?)"
        return f"{base}_pix{idx}_(i=?,j=?)"

    if mode == "idx":
        return f"{base}_pix{idx}"
    if mode == "ij":
        return f"{base}_(i={info['i']},j={info['j']})"
    return f"{base}_pix{idx}_(i={info['i']},j={info['j']})"


def geom_group(label: str) -> str:
    u = label
    if u.startswith("TES_L"):
        return "TES"
    if u.startswith("Win_") or "window" in u.lower():
        return "Window"
    if "BGO" in u.upper():
        return "BGO"
    if u.endswith("_Shield") or "shield" in u.lower() or u in ("Nb_Shield", "W_Shield", "Cryo_Shell", "Al_Shell"):
        return "Shield"
    if u.startswith("Cu_") or u.lower().startswith("cu") or u == "Copper":
        return "Copper"
    if u.startswith("Coll") or "coll" in u.lower():
        return "Collimator"
    return "Other"


# -----------------------------------------------------------------------------
# Spectrum axis
# -----------------------------------------------------------------------------
def make_axis(emin, emax, binw):
    nbin = int(math.ceil((emax - emin) / binw))
    edges = emin + np.arange(nbin + 1) * binw
    cent = 0.5 * (edges[:-1] + edges[1:])
    return nbin, edges, cent


# -----------------------------------------------------------------------------
# Worker config
# -----------------------------------------------------------------------------
class Cfg:
    def __init__(self, bounds, thr_keV, pos_scale,
                 mode, non_gamma_div,
                 emin, emax, binw,
                 tp_idx_map, tp_mode,
                 geom_mode,
                 file_tag):
        self.bounds = bounds
        self.thr_keV = thr_keV
        self.pos_scale = pos_scale
        self.mode = mode
        self.non_gamma_div = float(non_gamma_div)

        self.emin = float(emin)
        self.emax = float(emax)
        self.binw = float(binw)
        self.nbin, self.edges, self.cent = make_axis(self.emin, self.emax, self.binw)

        self.tp_idx_map = tp_idx_map
        self.tp_mode = tp_mode
        self.geom_mode = geom_mode  # raw / grouped

        # for prompt event-count by tag
        self.file_tag = file_tag


def file_weight(tag: str, cfg: Cfg) -> float:
    if cfg.mode == "delayed":
        return 1.0
    if is_gamma(tag):
        return 1.0
    div = cfg.non_gamma_div if cfg.non_gamma_div > 0 else 1.0
    return 1.0 / div


ISO_RE = re.compile(r"^[A-Za-z]{1,3}\d{1,3}$")


# -----------------------------------------------------------------------------
# Paper-style label mapping for processes
# -----------------------------------------------------------------------------
def map_cproc_to_paper(cproc: str) -> str:
    if not cproc:
        return "NA"
    s = str(cproc)
    low = s.lower()
    if low == "radioactivedecay":
        return "Radioactivation"   # 论文用词
    if low == "primary":
        return "Primary"          # 论文用词
    return s


# -----------------------------------------------------------------------------
# Worker (window-filtered attribution, prompt+delayed unified TES-only CC HIT)
# -----------------------------------------------------------------------------
def worker_one(arg):
    fp, cfg = arg
    try:
        w_file = file_weight(cfg.file_tag, cfg)

        raw_spec = np.zeros(cfg.nbin, dtype=np.float64)
        pass_spec = np.zeros(cfg.nbin, dtype=np.float64)

        raw_total = 0.0
        pass_total = 0.0

        # prompt event-count by tag (windowed)
        evt_tag_raw = 0.0
        evt_tag_pass = 0.0

        # delayed isotopes (windowed): event counts
        raw_iso = defaultdict(float)
        pass_iso = defaultdict(float)

        # unified TES-only attribution (windowed): energy-weighted by CC HIT inside TES
        raw_attr = defaultdict(float)
        pass_attr = defaultdict(float)

        # per-event accumulators
        cur_bgo = 0.0
        cur_tes_sum = 0.0

        # energy-weighted attribution accumulators (TES-only CC HIT)
        cur_primE = defaultdict(float)
        cur_secE = defaultdict(float)
        cur_sprocE = defaultdict(float)
        cur_cprocE = defaultdict(float)
        cur_geomE = defaultdict(float)

        # delayed isotope set per event (TES-only, windowed later)
        cur_delay_isos = set()

        def add_attr(dst: dict, prefix: str, mp: dict):
            for k, v in mp.items():
                dst[f"{prefix}:{k}"] += v * w_file

        def reset_event():
            nonlocal cur_bgo, cur_tes_sum
            cur_bgo = 0.0
            cur_tes_sum = 0.0
            cur_primE.clear()
            cur_secE.clear()
            cur_sprocE.clear()
            cur_cprocE.clear()
            cur_geomE.clear()
            cur_delay_isos.clear()

        def flush_event():
            nonlocal raw_total, pass_total, evt_tag_raw, evt_tag_pass

            if cur_tes_sum <= 0:
                reset_event()
                return

            in_window = (cfg.emin <= cur_tes_sum < cfg.emax)

            if in_window:
                # spectrum
                k = int((cur_tes_sum - cfg.emin) / cfg.binw)
                if 0 <= k < cfg.nbin:
                    raw_spec[k] += w_file
                    raw_total += w_file

                # prompt event-count by tag (raw-window)
                if cfg.mode == "prompt":
                    evt_tag_raw += w_file

                # unified attribution (raw-window)
                add_attr(raw_attr, "primE", cur_primE)
                add_attr(raw_attr, "secE", cur_secE)
                add_attr(raw_attr, "sprocE", cur_sprocE)
                add_attr(raw_attr, "cprocE", cur_cprocE)
                add_attr(raw_attr, "geomE", cur_geomE)

                # delayed isotope (raw-window) event counts
                if cfg.mode == "delayed":
                    for iso in cur_delay_isos:
                        raw_iso[iso] += w_file

            # passed-veto
            if (cur_bgo < cfg.thr_keV) and in_window:
                k = int((cur_tes_sum - cfg.emin) / cfg.binw)
                if 0 <= k < cfg.nbin:
                    pass_spec[k] += w_file
                    pass_total += w_file

                if cfg.mode == "prompt":
                    evt_tag_pass += w_file

                # unified attribution (pass-window)
                add_attr(pass_attr, "primE", cur_primE)
                add_attr(pass_attr, "secE", cur_secE)
                add_attr(pass_attr, "sprocE", cur_sprocE)
                add_attr(pass_attr, "cprocE", cur_cprocE)
                add_attr(pass_attr, "geomE", cur_geomE)

                if cfg.mode == "delayed":
                    for iso in cur_delay_isos:
                        pass_iso[iso] += w_file

            reset_event()

        with open_text_gz(fp) as f:
            for line in f:
                if line.startswith("SE"):
                    flush_event()
                    continue

                if line.startswith("CC HIT"):
                    hit = parse_cc_hit(line)
                    if hit is None or hit["edep"] <= 0:
                        continue

                    # TES-only CC HIT attribution (prompt+delayed unified)
                    x = hit["x"] * cfg.pos_scale
                    y = hit["y"] * cfg.pos_scale
                    z = hit["z"] * cfg.pos_scale
                    vol_cls = identify_vol(x, y, z, cfg.bounds)

                    in_TES = (
                        str(vol_cls).startswith("TES_L")
                        or str(hit["vol"]).startswith("TP_L")
                        or str(hit["vol"]).startswith("TES_Pixel")
                    )
                    if in_TES:
                        # particle types: prefer sec
                        cur_primE[hit["prim"]] += hit["edep"]
                        cur_secE[hit["sec"]] += hit["edep"]
                        cur_sprocE[hit["sproc"]] += hit["edep"]

                        cp = map_cproc_to_paper(hit["cproc"])
                        cur_cprocE[cp] += hit["edep"]

                        g = tp_label(hit["vol"], cfg)
                        if cfg.geom_mode == "grouped":
                            g = geom_group(g)
                        cur_geomE[g] += hit["edep"]

                        # delayed isotope bookkeeping (for topN isotope bars)
                        if cfg.mode == "delayed":
                            prim = hit["prim"]
                            if prim and prim not in ("NA", "none", "None") and ISO_RE.match(prim):
                                cur_delay_isos.add(prim)
                    continue

                if not line.startswith("HTsim"):
                    continue
                parsed = parse_htsim_fast(line)
                if parsed is None:
                    continue
                x, y, z, E = parsed
                x *= cfg.pos_scale
                y *= cfg.pos_scale
                z *= cfg.pos_scale

                vol0 = identify_vol(x, y, z, cfg.bounds)
                if "BGO" in str(vol0).upper():
                    cur_bgo += E
                    continue
                if str(vol0).startswith("TES_L"):
                    cur_tes_sum += E

        flush_event()

        return ("OK", fp,
                raw_spec, pass_spec,
                raw_total, pass_total,
                raw_attr, pass_attr,
                raw_iso, pass_iso,
                evt_tag_raw, evt_tag_pass,
                cfg.file_tag)
    except Exception as e:
        return ("ERR", fp, repr(e))


# -----------------------------------------------------------------------------
# CSV + plotting utils
# -----------------------------------------------------------------------------
def merge_dd(dst: dict, src: dict):
    for k, v in src.items():
        dst[k] += v


def dict_to_csv(path: Path, d: dict, key_name: str, val_name: str):
    items = sorted(d.items(), key=lambda kv: kv[1], reverse=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(f"{key_name},{val_name}\n")
        for k, v in items:
            f.write(f"{k},{v:.12g}\n")


def split_prefix(d: dict, prefix: str) -> dict:
    out = {}
    pre = prefix + ":"
    for k, v in d.items():
        if k.startswith(pre):
            out[k[len(pre):]] = v
    return out


def scale_dict(d: dict, s: float) -> dict:
    return {k: (v * s) for k, v in d.items()}


def pie_threshold_4pct(d: dict, out_png: Path, title: str, min_pct: float = 4.0):
    """
    贴论文：只显示占比>=4%的分量，其余合并为 others。
    """
    items = [(k, float(v)) for k, v in d.items() if float(v) > 0]
    if not items:
        return
    items.sort(key=lambda kv: kv[1], reverse=True)
    total = sum(v for _, v in items)
    if total <= 0:
        return

    labels, vals = [], []
    others = 0.0
    for k, v in items:
        pct = 100.0 * v / total
        if pct >= min_pct:
            labels.append(str(k))
            vals.append(v)
        else:
            others += v
    if others > 0:
        labels.append("others")
        vals.append(others)

    plt.figure(figsize=(10, 8))
    plt.pie(vals, labels=labels, autopct=lambda p: f"{p:.1f}%" if p >= min_pct else "")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(out_png, dpi=250)
    plt.close()


def barh_topn(d: dict, out_png: Path, title: str, topn: int = 25, xlabel="Weighted event counts"):
    items = sorted(d.items(), key=lambda kv: kv[1], reverse=True)[:topn]
    if not items:
        return
    labels = [k for k, _ in items][::-1]
    vals = [float(v) for _, v in items][::-1]
    plt.figure(figsize=(10, max(6, 0.35 * len(labels))))
    y = np.arange(len(labels))
    plt.barh(y, vals)
    plt.yticks(y, labels, fontsize=9)
    plt.xlabel(xlabel)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(out_png, dpi=250)
    plt.close()


def plot_total_spectrum(e_cent, total_raw, total_pass, out_png, title):
    plt.figure(figsize=(12, 7))
    plt.step(e_cent, total_raw, where="mid", label="TOTAL Raw", linewidth=1.6)
    plt.step(e_cent, total_pass, where="mid", label="TOTAL Passed", linewidth=1.6, alpha=0.8)
    plt.yscale("log")
    plt.xlabel("Energy (keV)")
    plt.ylabel("Weighted counts")
    plt.title(title)
    plt.grid(True, which="both", alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_png, dpi=250)
    plt.close()


def write_fraction_csv(path: Path, counts: dict, total: float, key_name="component"):
    items = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(f"{key_name},counts,fraction\n")
        denom = total if total > 0 else 1.0
        for k, v in items:
            f.write(f"{k},{v:.12g},{(v/denom):.12g}\n")


# -----------------------------------------------------------------------------
# build-up scan (CC IP RP)
# -----------------------------------------------------------------------------
def scan_activation_origin(buildup_files: list[str]):
    iso_par = defaultdict(lambda: defaultdict(float))   # iso -> par -> count
    iso_geom = defaultdict(lambda: defaultdict(float))  # iso -> vn  -> count

    for fp in tqdm(buildup_files, desc="Buildup scan (CC IP RP)", unit="file"):
        try:
            with open_text_gz(fp) as f:
                for line in f:
                    if not line.startswith("CC IP"):
                        continue
                    rec = parse_cc_ip_rp(line)
                    if rec is None:
                        continue
                    iso_par[rec["nu"]][rec["par"]] += 1.0
                    iso_geom[rec["nu"]][rec["vn"]] += 1.0
        except Exception:
            continue

    return iso_par, iso_geom


# -----------------------------------------------------------------------------
# main
# -----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--delayed", required=True)
    ap.add_argument("--buildup", default="")
    ap.add_argument("--bounds", required=True)
    ap.add_argument("--outdir", default="merge_out")
    ap.add_argument("--thr", type=float, default=50.0)
    ap.add_argument("--pos_scale", type=float, default=1.0)

    ap.add_argument("--emin", type=float, default=0.0)
    ap.add_argument("--emax", type=float, default=600.0)
    ap.add_argument("--binw", type=float, default=0.1)

    ap.add_argument("--prompt_scale", type=float, default=10.96)
    ap.add_argument("--non_gamma_div", type=float, default=4.0)
    ap.add_argument("--workers", type=int, default=0)

    ap.add_argument("--tp_mode", choices=["layer", "idx", "ij", "idxij"], default="idxij")
    ap.add_argument("--tp_pitch", type=float, default=1.55)
    ap.add_argument("--tp_npix", type=int, default=20)
    ap.add_argument("--tp_eff_r", type=float, default=18.0)

    ap.add_argument("--geom_mode", choices=["raw", "grouped"], default="grouped")

    ap.add_argument("--top_isos", type=int, default=25)
    ap.add_argument("--plot_top_isos", type=int, default=10)

    args = ap.parse_args()

    prompt_files = sorted(glob.glob(args.prompt))
    delayed_files = sorted(glob.glob(args.delayed))
    buildup_files = sorted(glob.glob(args.buildup)) if args.buildup else []

    if not prompt_files:
        raise SystemExit(f"[ERROR] no prompt files matched: {args.prompt}")
    if not delayed_files:
        raise SystemExit(f"[ERROR] no delayed files matched: {args.delayed}")

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    bounds = load_bounds(args.bounds)
    tp_idx_map = build_tp_idx_map(args.tp_npix, args.tp_pitch, args.tp_eff_r)

    nproc = args.workers if args.workers > 0 else min(cpu_count(), max(1, len(prompt_files) + len(delayed_files)))
    print(f"[INFO] workers={nproc} prompt_files={len(prompt_files)} delayed_files={len(delayed_files)} buildup_files={len(buildup_files)}")
    print(f"[INFO] window: [{args.emin}, {args.emax}) keV, binw={args.binw}")

    # ---------------- prompt parse
    prompt_raw = None
    prompt_pass = None
    prompt_raw_total = 0.0
    prompt_pass_total = 0.0

    prompt_attr_raw = defaultdict(float)
    prompt_attr_pass = defaultdict(float)

    # prompt event-count by tag (windowed)
    prompt_evt_tag_raw = defaultdict(float)
    prompt_evt_tag_pass = defaultdict(float)

    errors = []

    pack_prompt = []
    for fp in prompt_files:
        tag = parse_tag_from_name(fp)
        cfg = Cfg(bounds, args.thr, args.pos_scale,
                  mode="prompt", non_gamma_div=args.non_gamma_div,
                  emin=args.emin, emax=args.emax, binw=args.binw,
                  tp_idx_map=tp_idx_map, tp_mode=args.tp_mode,
                  geom_mode=args.geom_mode,
                  file_tag=tag)
        pack_prompt.append((fp, cfg))

    with Pool(nproc) as p:
        for res in tqdm(p.imap_unordered(worker_one, pack_prompt),
                        total=len(pack_prompt), desc="Prompt parsing", unit="file"):
            if res[0] == "ERR":
                errors.append(("prompt", res[1], res[2]))
                continue
            (_, _fp, raw_spec, pass_spec, raw_tot, pass_tot,
             raw_attr, pass_attr, _raw_iso, _pass_iso,
             evt_tag_raw, evt_tag_pass, tag) = res

            if prompt_raw is None:
                prompt_raw = np.zeros_like(raw_spec)
                prompt_pass = np.zeros_like(pass_spec)

            prompt_raw += raw_spec
            prompt_pass += pass_spec
            prompt_raw_total += raw_tot
            prompt_pass_total += pass_tot
            merge_dd(prompt_attr_raw, raw_attr)
            merge_dd(prompt_attr_pass, pass_attr)

            prompt_evt_tag_raw[tag] += evt_tag_raw
            prompt_evt_tag_pass[tag] += evt_tag_pass

    if prompt_raw is None:
        raise SystemExit("[ERROR] prompt parsing produced no valid result (all files failed?)")

    # ---------------- delayed parse
    delayed_raw = None
    delayed_pass = None
    delayed_raw_total = 0.0
    delayed_pass_total = 0.0

    delayed_iso_raw = defaultdict(float)
    delayed_iso_pass = defaultdict(float)

    delayed_attr_raw = defaultdict(float)
    delayed_attr_pass = defaultdict(float)

    pack_delayed = []
    for fp in delayed_files:
        cfg = Cfg(bounds, args.thr, args.pos_scale,
                  mode="delayed", non_gamma_div=1.0,
                  emin=args.emin, emax=args.emax, binw=args.binw,
                  tp_idx_map=tp_idx_map, tp_mode=args.tp_mode,
                  geom_mode=args.geom_mode,
                  file_tag="delayed")
        pack_delayed.append((fp, cfg))

    with Pool(nproc) as p:
        for res in tqdm(p.imap_unordered(worker_one, pack_delayed),
                        total=len(pack_delayed), desc="Delayed parsing", unit="file"):
            if res[0] == "ERR":
                errors.append(("delayed", res[1], res[2]))
                continue
            (_, _fp, raw_spec, pass_spec, raw_tot, pass_tot,
             raw_attr, pass_attr, raw_iso, pass_iso,
             _evt_tag_raw, _evt_tag_pass, _tag) = res

            if delayed_raw is None:
                delayed_raw = np.zeros_like(raw_spec)
                delayed_pass = np.zeros_like(pass_spec)

            delayed_raw += raw_spec
            delayed_pass += pass_spec
            delayed_raw_total += raw_tot
            delayed_pass_total += pass_tot

            merge_dd(delayed_attr_raw, raw_attr)
            merge_dd(delayed_attr_pass, pass_attr)

            merge_dd(delayed_iso_raw, raw_iso)
            merge_dd(delayed_iso_pass, pass_iso)

    if delayed_raw is None:
        raise SystemExit("[ERROR] delayed parsing produced no valid result (all files failed?)")

    # errors
    if errors:
        with (outdir / "errors.csv").open("w", encoding="utf-8") as f:
            f.write("family,file,error\n")
            for fam, fp, err in errors:
                f.write(f"{fam},{fp},{err}\n")
        print(f"[WARN] {len(errors)} file(s) failed. See {outdir/'errors.csv'}")

    # ---------------- scale + total spectrum
    s = float(args.prompt_scale)
    prompt_raw_s = prompt_raw * s
    prompt_pass_s = prompt_pass * s

    total_raw = prompt_raw_s + delayed_raw
    total_pass = prompt_pass_s + delayed_pass

    e_cent = make_axis(args.emin, args.emax, args.binw)[2]
    np.savetxt(
        outdir / "tes_spectrum_total.csv",
        np.column_stack([e_cent, total_raw, total_pass, prompt_pass_s, delayed_pass]),
        delimiter=",",
        header="E_keV,total_raw,total_pass,prompt_pass_scaled,delayed_pass",
        comments="",
    )
    plot_total_spectrum(
        e_cent, total_raw, total_pass,
        outdir / "fig_total_raw_pass.png",
        f"TOTAL Raw vs Passed (window [{args.emin},{args.emax}) keV)"
    )

    # ---------------- write prompt attribution (PASS+WINDOW)
    p_sec_pass = split_prefix(prompt_attr_pass, "secE")
    p_geom_pass = split_prefix(prompt_attr_pass, "geomE")
    p_cproc_pass = split_prefix(prompt_attr_pass, "cprocE")

    dict_to_csv(outdir / "prompt_attr_pass_secE_TESonly_window.csv", p_sec_pass, "sec", "edep_keV_weighted")
    dict_to_csv(outdir / "prompt_attr_pass_geomE_TESonly_window.csv", p_geom_pass, "geom", "edep_keV_weighted")
    dict_to_csv(outdir / "prompt_attr_pass_cprocE_TESonly_window.csv", p_cproc_pass, "cproc", "edep_keV_weighted")

    pie_threshold_4pct(p_sec_pass, outdir / "prompt_pass_particle_types_pie_TESonly_window.png",
                       "Prompt (Pass+Window) particle types (sec, TES-only, energy-weighted)")
    pie_threshold_4pct(p_geom_pass, outdir / "prompt_pass_creation_volume_pie_TESonly_window.png",
                       f"Prompt (Pass+Window) creation volumes (geom, TES-only, energy-weighted)\ngeom_mode={args.geom_mode} tp_mode={args.tp_mode}")
    pie_threshold_4pct(p_cproc_pass, outdir / "prompt_pass_creation_process_pie_TESonly_window.png",
                       "Prompt (Pass+Window) creation processes (cproc, TES-only, energy-weighted)")

    # ---------------- write delayed attribution (PASS+WINDOW)
    d_sec_pass = split_prefix(delayed_attr_pass, "secE")
    d_geom_pass = split_prefix(delayed_attr_pass, "geomE")
    d_cproc_pass = split_prefix(delayed_attr_pass, "cprocE")

    dict_to_csv(outdir / "delayed_attr_pass_secE_TESonly_window.csv", d_sec_pass, "sec", "edep_keV_weighted")
    dict_to_csv(outdir / "delayed_attr_pass_geomE_TESonly_window.csv", d_geom_pass, "geom", "edep_keV_weighted")
    dict_to_csv(outdir / "delayed_attr_pass_cprocE_TESonly_window.csv", d_cproc_pass, "cproc", "edep_keV_weighted")

    pie_threshold_4pct(d_sec_pass, outdir / "delayed_pass_particle_types_pie_TESonly_window.png",
                       "Delayed (Pass+Window) particle types (sec, TES-only, energy-weighted)")
    pie_threshold_4pct(d_geom_pass, outdir / "delayed_pass_creation_volume_pie_TESonly_window.png",
                       f"Delayed (Pass+Window) creation volumes (geom, TES-only, energy-weighted)\ngeom_mode={args.geom_mode} tp_mode={args.tp_mode}")
    pie_threshold_4pct(d_cproc_pass, outdir / "delayed_pass_creation_process_pie_TESonly_window.png",
                       "Delayed (Pass+Window) creation processes (cproc, TES-only, energy-weighted)")

    # ---------------- TOTAL (prompt×scale + delayed) paper-style Fig.10 pies
    # NOTE: prompt_attr_pass 是能量加权但未乘 prompt_scale；合并必须乘 s
    total_sec_pass = defaultdict(float)
    total_geom_pass = defaultdict(float)
    total_cproc_pass = defaultdict(float)

    for k, v in scale_dict(p_sec_pass, s).items():
        total_sec_pass[k] += v
    for k, v in scale_dict(p_geom_pass, s).items():
        total_geom_pass[k] += v
    for k, v in scale_dict(p_cproc_pass, s).items():
        total_cproc_pass[k] += v

    for k, v in d_sec_pass.items():
        total_sec_pass[k] += v
    for k, v in d_geom_pass.items():
        total_geom_pass[k] += v
    for k, v in d_cproc_pass.items():
        total_cproc_pass[k] += v

    dict_to_csv(outdir / "total_attr_pass_secE_TESonly_window.csv", total_sec_pass, "sec", "edep_keV_weighted")
    dict_to_csv(outdir / "total_attr_pass_geomE_TESonly_window.csv", total_geom_pass, "geom", "edep_keV_weighted")
    dict_to_csv(outdir / "total_attr_pass_cprocE_TESonly_window.csv", total_cproc_pass, "cproc", "edep_keV_weighted")

    pie_threshold_4pct(total_sec_pass, outdir / "total_pass_particle_types_pie_TESonly_window.png",
                       "TOTAL (Prompt×scale + Delayed) particle types (sec, TES-only, energy-weighted)")
    pie_threshold_4pct(total_geom_pass, outdir / "total_pass_creation_volume_pie_TESonly_window.png",
                       f"TOTAL (Prompt×scale + Delayed) creation volumes (geom, TES-only, energy-weighted)\ngeom_mode={args.geom_mode} tp_mode={args.tp_mode}")
    pie_threshold_4pct(total_cproc_pass, outdir / "total_pass_creation_process_pie_TESonly_window.png",
                       "TOTAL (Prompt×scale + Delayed) creation processes (cproc, TES-only, energy-weighted)")

    # ---------------- prompt event-count by tag (WINDOWED!) (保留 v6p1)
    dict_to_csv(outdir / "prompt_eventcount_by_tag_raw_window.csv",  prompt_evt_tag_raw,  "tag", "weighted_event_counts")
    dict_to_csv(outdir / "prompt_eventcount_by_tag_pass_window.csv", prompt_evt_tag_pass, "tag", "weighted_event_counts")
    pie_threshold_4pct(prompt_evt_tag_pass, outdir / "prompt_pass_eventcount_by_tag_pie_window.png",
                       "Prompt (Pass+Window) event-count by incident particle tag (>=4% shown)")

    # ---------------- delayed isotopes (WINDOWED!) (保留 v6p1)
    dict_to_csv(outdir / "delayed_iso_raw_window.csv",  delayed_iso_raw,  "isotope", "weighted_event_counts")
    dict_to_csv(outdir / "delayed_iso_pass_window.csv", delayed_iso_pass, "isotope", "weighted_event_counts")
    barh_topn(delayed_iso_pass, outdir / "delayed_iso_pass_top_window.png",
              f"Delayed (Pass+Window) Top{args.top_isos} isotopes", topn=args.top_isos)

    # ---------------- Fig.9-like fractions (counts fractions, no cps)
    # 1) prompt tags: multiply by prompt_scale to match TOTAL composition
    prompt_evt_tag_pass_scaled = {k: v * s for k, v in prompt_evt_tag_pass.items()}
    total_pass_counts = float(sum(prompt_evt_tag_pass_scaled.values()) + sum(delayed_iso_pass.values()))

    write_fraction_csv(outdir / "fig9_fraction_prompt_by_tag_in_prompt.csv",
                       prompt_evt_tag_pass_scaled,
                       total=float(sum(prompt_evt_tag_pass_scaled.values())),
                       key_name="tag")

    write_fraction_csv(outdir / "fig9_fraction_delayed_by_iso_in_delayed.csv",
                       delayed_iso_pass,
                       total=float(sum(delayed_iso_pass.values())),
                       key_name="isotope")

    # relative to TOTAL
    write_fraction_csv(outdir / "fig9_fraction_prompt_by_tag_in_TOTAL.csv",
                       prompt_evt_tag_pass_scaled,
                       total=total_pass_counts,
                       key_name="tag")

    # 只输出 top_isos 相对 TOTAL（否则太长）
    top_isos = [k for k, _ in sorted(delayed_iso_pass.items(), key=lambda kv: kv[1], reverse=True)[:max(1, int(args.top_isos))]]
    delayed_top_for_total = {k: delayed_iso_pass[k] for k in top_isos if k in delayed_iso_pass}
    write_fraction_csv(outdir / "fig9_fraction_delayed_topIso_in_TOTAL.csv",
                       delayed_top_for_total,
                       total=total_pass_counts,
                       key_name="isotope")

    # ---------------- activation origin for Top isotopes (selected by WINDOWED delayed!)
    if buildup_files:
        iso_par, iso_geom = scan_activation_origin(buildup_files)
        summary = outdir / f"activation_origin_summary_top{args.top_isos}_window.csv"
        with summary.open("w", encoding="utf-8") as f:
            f.write("isotope,top_geom,top_geom_frac,top_par,top_par_frac,total_rp_lines\n")
            for iso in top_isos:
                gmap = iso_geom.get(iso, {})
                pmap = iso_par.get(iso, {})
                gt = sum(gmap.values()) or 0.0

                def top1(m):
                    if not m:
                        return ("NA", 0.0)
                    k, v = sorted(m.items(), key=lambda kv: kv[1], reverse=True)[0]
                    tot = sum(m.values()) or 1.0
                    return (k, v / tot)

                g1, gf = top1(gmap)
                p1, pf = top1(pmap)
                f.write(f"{iso},{g1},{gf:.6g},{p1},{pf:.6g},{int(gt)}\n")

        act_dir = outdir / "activation_origin_plots_window"
        act_dir.mkdir(exist_ok=True)

        plot_isos = top_isos[:max(0, int(args.plot_top_isos))]

        for iso in plot_isos:
            gmap = iso_geom.get(iso, {})
            pmap = iso_par.get(iso, {})

            dict_to_csv(act_dir / f"{iso}_geom.csv", gmap, "VN", "counts")
            dict_to_csv(act_dir / f"{iso}_par.csv", pmap, "par", "counts")

            pie_threshold_4pct(gmap, act_dir / f"{iso}_geom_pie.png",
                               f"{iso}: production geometry (VN) [from CC IP RP]\n(selected by Pass+Window Top{args.top_isos})")
            pie_threshold_4pct(pmap, act_dir / f"{iso}_par_pie.png",
                               f"{iso}: inducing particle (par) [from CC IP RP]\n(selected by Pass+Window Top{args.top_isos})")

    print("\n[SANITY] (windowed)")
    print(f"  PROMPT× Raw   = {prompt_raw_total*s:.6g}")
    print(f"  PROMPT× Pass  = {prompt_pass_total*s:.6g}")
    print(f"  DELAYED Raw   = {delayed_raw_total:.6g}")
    print(f"  DELAYED Pass  = {delayed_pass_total:.6g}")
    print(f"  TOTAL Raw(sum)  = {float(np.sum(total_raw)):.6g}")
    print(f"  TOTAL Pass(sum) = {float(np.sum(total_pass)):.6g}")
    print(f"  TOTAL Pass(counts via tag/iso) = {total_pass_counts:.6g}")
    print("[DONE]")


if __name__ == "__main__":
    main()
