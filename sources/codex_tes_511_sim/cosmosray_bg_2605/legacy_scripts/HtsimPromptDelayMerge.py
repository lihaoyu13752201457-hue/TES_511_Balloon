#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
htsim_prompt_delayed_merge_v3.py

Prompt + Delayed spectrum merging with your weighting rules:

Prompt family:
  - gamma weight = 1
  - non-gamma weight = 1/non_gamma_div (default 4)
  - then multiply whole prompt contribution by prompt_scale (e.g. 10.96)

Delayed family:
  - all weight = 1 (no div)

Outputs 3 figures:
  (1) TOTAL spectrum: Raw vs Passed-veto
  (2) Passed-veto TOTAL spectrum with dashed Prompt/Delayed components
  (3) Passed-veto zoom 500-550 keV with binw=0.015 keV, dashed Prompt/Delayed components

Assumptions:
- Event boundary line starts with "SE"
- HTsim line format: "HTsim id; x; y; z; E; ..."
- bounds.json classifies xyz into TES_L0..TES_L5 and BGO volumes (name contains "BGO")
- BGO veto: sum(E in BGO volumes) < thr_keV
- TES spectrum: per-event sum of TES Edep (keV)
"""

import re
import gzip
import math
import json
import glob
import argparse
from pathlib import Path
from multiprocessing import Pool, cpu_count

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

    # 1) Copper first
    for name in ["CU_BASE", "CU_SUPPORT"]:
        obj = b.get(name)
        if obj and obj["z_bot"] <= z <= obj["z_top"] and r <= obj["r_max"]:
            return "Copper"

    # 2) TES layers
    for i, t in enumerate(b.get("TES_LAYERS", [])):
        if abs(z - t["z_center"]) <= (t["hz"] + 0.05) and r <= (t["r_max"] + 0.05):
            return f"TES_L{i}"

    # 3) Window
    for w in b.get("WINDOWS", []):
        if abs(z - w["z_center"]) <= (w["thick"] / 2.0 + 0.01) and r <= w["r_max"]:
            return "Window"

    # 4) Collimator
    c = b.get("COLLIMATOR")
    if c and abs(z - c["z_center"]) <= (c["hz"] + 0.01) and r <= c["r_max"]:
        return "Collimator"

    # 5) Shields (includes BGO if your names contain BGO)
    for name, s in b.get("SHIELDS", {}).items():
        if in_shell(r, z, s):
            return name

    return "Other"


# -----------------------------------------------------------------------------
# tag parsing (only used to decide gamma vs non-gamma for prompt set)
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
# HTsim parsing
# -----------------------------------------------------------------------------
def open_text_gz(path: str):
    return gzip.open(path, "rt", encoding="utf-8", errors="ignore")


def parse_htsim_fast(line: str):
    try:
        parts = line.split(";", 5)
        return float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
    except Exception:
        return None


# -----------------------------------------------------------------------------
# Histogram helper
# -----------------------------------------------------------------------------
def make_axis(emin, emax, binw):
    nbin = int(math.ceil((emax - emin) / binw))
    edges = emin + np.arange(nbin + 1) * binw
    cent = 0.5 * (edges[:-1] + edges[1:])
    return nbin, edges, cent


# -----------------------------------------------------------------------------
# Worker
# -----------------------------------------------------------------------------
class Cfg:
    def __init__(self, bounds, thr_keV, pos_scale,
                 mode, non_gamma_div,
                 # main spectrum config
                 emin, emax, binw,
                 # zoom spectrum config
                 z_emin, z_emax, z_binw):
        self.bounds = bounds
        self.thr_keV = thr_keV
        self.pos_scale = pos_scale
        self.mode = mode  # "prompt" or "delayed"
        self.non_gamma_div = float(non_gamma_div)

        self.emin = float(emin)
        self.emax = float(emax)
        self.binw = float(binw)
        self.nbin, self.edges, self.cent = make_axis(self.emin, self.emax, self.binw)

        self.z_emin = float(z_emin)
        self.z_emax = float(z_emax)
        self.z_binw = float(z_binw)
        self.z_nbin, self.z_edges, self.z_cent = make_axis(self.z_emin, self.z_emax, self.z_binw)


def file_weight(fp: str, cfg: Cfg) -> float:
    """
    YOUR RULE:
      prompt:
        gamma => 1
        non-gamma => 1/non_gamma_div (default 4)
      delayed:
        all => 1
    """
    if cfg.mode == "delayed":
        return 1.0
    tag = parse_tag_from_name(fp)
    if is_gamma(tag):
        return 1.0
    div = cfg.non_gamma_div if cfg.non_gamma_div > 0 else 1.0
    return 1.0 / div


def worker_one(fp_cfg):
    fp, cfg = fp_cfg
    w_file = file_weight(fp, cfg)

    # main
    raw_spec = np.zeros(cfg.nbin, dtype=np.float64)
    pass_spec = np.zeros(cfg.nbin, dtype=np.float64)

    # zoom: only meaningful for passed-veto spectrum
    pass_zoom = np.zeros(cfg.z_nbin, dtype=np.float64)

    raw_total = 0.0
    pass_total = 0.0
    pass_zoom_total = 0.0

    cur_bgo = 0.0
    cur_tes_sum = 0.0

    def flush_event():
        nonlocal cur_bgo, cur_tes_sum, raw_total, pass_total, pass_zoom_total

        if cur_tes_sum > 0:
            # raw always fills
            k = int((cur_tes_sum - cfg.emin) / cfg.binw)
            if 0 <= k < cfg.nbin:
                raw_spec[k] += w_file
                raw_total += w_file

            # passed veto
            if cur_bgo < cfg.thr_keV:
                if 0 <= k < cfg.nbin:
                    pass_spec[k] += w_file
                    pass_total += w_file

                kz = int((cur_tes_sum - cfg.z_emin) / cfg.z_binw)
                if 0 <= kz < cfg.z_nbin:
                    pass_zoom[kz] += w_file
                    pass_zoom_total += w_file

        cur_bgo = 0.0
        cur_tes_sum = 0.0

    with open_text_gz(fp) as f:
        for line in f:
            if line.startswith("SE"):
                flush_event()
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
    return raw_spec, pass_spec, pass_zoom, raw_total, pass_total, pass_zoom_total


# -----------------------------------------------------------------------------
# Plotting
# -----------------------------------------------------------------------------
def _annot(ax, text):
    ax.text(
        0.02, 0.98, text,
        transform=ax.transAxes,
        va="top", ha="left",
        fontsize=10,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="white", alpha=0.88, edgecolor="none"),
    )


def plot1_raw_vs_pass(e_cent, total_raw, total_pass, thr, out_png, binw):
    raw_total = float(np.sum(total_raw))
    pass_total = float(np.sum(total_pass))
    eff = pass_total / raw_total if raw_total > 0 else 0.0

    plt.figure(figsize=(12, 7))
    plt.step(e_cent, total_raw, where="mid", label="TOTAL Raw (No Veto)", linewidth=1.6)
    plt.step(e_cent, total_pass, where="mid", label="TOTAL Passed Veto", linewidth=1.6, alpha=0.75)

    plt.yscale("log")
    plt.xlabel("Energy (keV)")
    plt.ylabel("Weighted counts (arb.)")
    plt.title(f"TES spectrum TOTAL: Raw vs Passed (binw={binw:g} keV)")
    plt.grid(True, which="both", alpha=0.3)
    plt.legend()

    ax = plt.gca()
    _annot(ax,
           f"BGO veto: sum(BGO) < {thr:g} keV\n"
           f"[TOTAL] Raw={raw_total:.6g}  Pass={pass_total:.6g}  Pass/Raw={eff:.4f}")
    plt.tight_layout()
    plt.savefig(out_png, dpi=300)
    plt.close()


def plot2_pass_with_components(e_cent, total_pass, prompt_pass, delayed_pass, thr, out_png, binw,
                               totals_text):
    plt.figure(figsize=(12, 7))
    plt.step(e_cent, total_pass, where="mid", label="TOTAL Passed Veto", linewidth=1.8)
    plt.step(e_cent, prompt_pass, where="mid", linestyle="--", label="Prompt Passed (scaled)", linewidth=1.2, alpha=0.9)
    plt.step(e_cent, delayed_pass, where="mid", linestyle="--", label="Delayed Passed", linewidth=1.2, alpha=0.9)

    plt.yscale("log")
    plt.xlabel("Energy (keV)")
    plt.ylabel("Weighted counts (arb.)")
    plt.title(f"TES spectrum (Passed veto) TOTAL with components (binw={binw:g} keV)")
    plt.grid(True, which="both", alpha=0.3)
    plt.legend()

    ax = plt.gca()
    _annot(ax, f"BGO veto: sum(BGO) < {thr:g} keV\n" + totals_text)
    plt.tight_layout()
    plt.savefig(out_png, dpi=300)
    plt.close()


def plot3_zoom_pass(e_cent_zoom, total_pass_zoom, prompt_pass_zoom, delayed_pass_zoom,
                    thr, out_png, binw_zoom, totals_text):
    plt.figure(figsize=(12, 7))
    plt.step(e_cent_zoom, total_pass_zoom, where="mid", label="TOTAL Passed Veto", linewidth=1.8)
    plt.step(e_cent_zoom, prompt_pass_zoom, where="mid", linestyle="--", label="Prompt Passed (scaled)", linewidth=1.2, alpha=0.9)
    plt.step(e_cent_zoom, delayed_pass_zoom, where="mid", linestyle="--", label="Delayed Passed", linewidth=1.2, alpha=0.9)

    plt.yscale("log")
    plt.xlabel("Energy (keV)")
    plt.ylabel("Weighted counts (arb.)")
    plt.title(f"TES spectrum (Passed veto) ZOOM 500–550 keV (binw={binw_zoom:g} keV)")
    plt.grid(True, which="both", alpha=0.3)
    plt.legend()

    ax = plt.gca()
    _annot(ax, f"BGO veto: sum(BGO) < {thr:g} keV\n" + totals_text)
    plt.tight_layout()
    plt.savefig(out_png, dpi=300)
    plt.close()


def find_bounds_auto(files, bounds_arg):
    if bounds_arg:
        return bounds_arg
    if files:
        d = Path(files[0]).resolve().parent
        cand = d / "bounds.json"
        if cand.exists():
            return str(cand)
    cand2 = Path("bounds.json").resolve()
    if cand2.exists():
        return str(cand2)
    return None


def safe_frac(a, b):
    return (a / b) if b > 0 else 0.0


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True, help="Glob for prompt sim.gz family")
    ap.add_argument("--delayed", required=True, help="Glob for delayed sim.gz (single file ok)")
    ap.add_argument("--bounds", default=None, help="bounds.json path (optional; auto-search if omitted)")
    ap.add_argument("--outdir", default="merge_out_v3")
    ap.add_argument("--thr", type=float, default=50.0)
    ap.add_argument("--pos_scale", type=float, default=1.0)

    # main spectrum
    ap.add_argument("--emin", type=float, default=0.0)
    ap.add_argument("--emax", type=float, default=600.0)
    ap.add_argument("--binw", type=float, default=0.1)

    # zoom spectrum
    ap.add_argument("--zoom_emin", type=float, default=500.0)
    ap.add_argument("--zoom_emax", type=float, default=550.0)
    ap.add_argument("--zoom_binw", type=float, default=0.015)

    # scaling rules
    ap.add_argument("--prompt_scale", type=float, default=10.96)
    ap.add_argument("--non_gamma_div", type=float, default=4.0,
                    help="Prompt only: non-gamma weight = 1/non_gamma_div. (You want div4)")
    ap.add_argument("--workers", type=int, default=0, help="0=auto")
    args = ap.parse_args()

    prompt_files = sorted(glob.glob(args.prompt))
    delayed_files = sorted(glob.glob(args.delayed))
    if not prompt_files:
        raise SystemExit(f"[ERROR] no prompt files matched: {args.prompt}")
    if not delayed_files:
        raise SystemExit(f"[ERROR] no delayed files matched: {args.delayed}")

    bounds_path = find_bounds_auto(prompt_files + delayed_files, args.bounds)
    if not bounds_path:
        raise SystemExit("[ERROR] bounds.json not found. Provide --bounds or place bounds.json in sim dir / cwd.")
    bounds = load_bounds(bounds_path)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    nproc = args.workers if args.workers > 0 else min(cpu_count(), max(1, len(prompt_files) + len(delayed_files)))
    print(f"[INFO] prompt_files={len(prompt_files)} delayed_files={len(delayed_files)} workers={nproc}")
    print(f"[INFO] bounds={bounds_path}")
    print(f"[INFO] prompt weighting: gamma=1 ; non-gamma=1/{args.non_gamma_div:g}")
    print(f"[INFO] prompt_scale={args.prompt_scale:g} (applied AFTER summing prompt)")
    print(f"[INFO] delayed weighting: all=1 (no div)")
    print(f"[INFO] zoom: {args.zoom_emin:g}-{args.zoom_emax:g} keV binw={args.zoom_binw:g} keV")

    cfg_prompt = Cfg(bounds, args.thr, args.pos_scale,
                     mode="prompt", non_gamma_div=args.non_gamma_div,
                     emin=args.emin, emax=args.emax, binw=args.binw,
                     z_emin=args.zoom_emin, z_emax=args.zoom_emax, z_binw=args.zoom_binw)

    cfg_delayed = Cfg(bounds, args.thr, args.pos_scale,
                      mode="delayed", non_gamma_div=1.0,
                      emin=args.emin, emax=args.emax, binw=args.binw,
                      z_emin=args.zoom_emin, z_emax=args.zoom_emax, z_binw=args.zoom_binw)

    # Parse prompt
    pack_prompt = [(fp, cfg_prompt) for fp in prompt_files]
    with Pool(nproc) as p:
        res_prompt = list(tqdm(p.imap_unordered(worker_one, pack_prompt),
                               total=len(pack_prompt), desc="Prompt parsing", unit="file"))

    # Parse delayed
    pack_delayed = [(fp, cfg_delayed) for fp in delayed_files]
    with Pool(nproc) as p:
        res_delayed = list(tqdm(p.imap_unordered(worker_one, pack_delayed),
                                total=len(pack_delayed), desc="Delayed parsing", unit="file"))

    # Reduce prompt
    prompt_raw = np.zeros(cfg_prompt.nbin, dtype=np.float64)
    prompt_pass = np.zeros(cfg_prompt.nbin, dtype=np.float64)
    prompt_pass_zoom = np.zeros(cfg_prompt.z_nbin, dtype=np.float64)
    prompt_raw_total = 0.0
    prompt_pass_total = 0.0
    prompt_pass_zoom_total = 0.0

    for raw_spec, pass_spec, pass_zoom, raw_tot, pass_tot, pass_zoom_tot in res_prompt:
        prompt_raw += raw_spec
        prompt_pass += pass_spec
        prompt_pass_zoom += pass_zoom
        prompt_raw_total += raw_tot
        prompt_pass_total += pass_tot
        prompt_pass_zoom_total += pass_zoom_tot

    # Reduce delayed
    delayed_raw = np.zeros(cfg_delayed.nbin, dtype=np.float64)
    delayed_pass = np.zeros(cfg_delayed.nbin, dtype=np.float64)
    delayed_pass_zoom = np.zeros(cfg_delayed.z_nbin, dtype=np.float64)
    delayed_raw_total = 0.0
    delayed_pass_total = 0.0
    delayed_pass_zoom_total = 0.0

    for raw_spec, pass_spec, pass_zoom, raw_tot, pass_tot, pass_zoom_tot in res_delayed:
        delayed_raw += raw_spec
        delayed_pass += pass_spec
        delayed_pass_zoom += pass_zoom
        delayed_raw_total += raw_tot
        delayed_pass_total += pass_tot
        delayed_pass_zoom_total += pass_zoom_tot

    # Scale prompt AFTER summing
    s = float(args.prompt_scale)
    prompt_raw_s = prompt_raw * s
    prompt_pass_s = prompt_pass * s
    prompt_pass_zoom_s = prompt_pass_zoom * s

    prompt_raw_total_s = prompt_raw_total * s
    prompt_pass_total_s = prompt_pass_total * s
    prompt_pass_zoom_total_s = prompt_pass_zoom_total * s

    # Total
    total_raw = prompt_raw_s + delayed_raw
    total_pass = prompt_pass_s + delayed_pass
    total_pass_zoom = prompt_pass_zoom_s + delayed_pass_zoom

    total_raw_total = prompt_raw_total_s + delayed_raw_total
    total_pass_total = prompt_pass_total_s + delayed_pass_total
    total_pass_zoom_total = prompt_pass_zoom_total_s + delayed_pass_zoom_total

    # Axes
    e_cent = cfg_prompt.cent
    z_cent = cfg_prompt.z_cent

    # ---- CSV outputs
    csv_main = outdir / "tes_spectrum_main_total_raw_pass_components.csv"
    np.savetxt(
        csv_main,
        np.column_stack([e_cent, total_raw, total_pass, prompt_pass_s, delayed_pass]),
        delimiter=",",
        header="E_keV,total_raw,total_pass,prompt_pass_scaled,delayed_pass",
        comments="",
    )
    print(f"[OK] wrote {csv_main}")

    csv_zoom = outdir / "tes_spectrum_zoom_500_550_pass_components.csv"
    np.savetxt(
        csv_zoom,
        np.column_stack([z_cent, total_pass_zoom, prompt_pass_zoom_s, delayed_pass_zoom]),
        delimiter=",",
        header="E_keV,total_pass,prompt_pass_scaled,delayed_pass",
        comments="",
    )
    print(f"[OK] wrote {csv_zoom}")

    # ---- Annotation text (NO unscaled prompt)
    tot_text = (
        f"[TOTAL]   Raw={total_raw_total:.6g}  Pass={total_pass_total:.6g}  Pass/Raw={safe_frac(total_pass_total, total_raw_total):.4f}\n"
        f"[PROMPT×] Raw={prompt_raw_total_s:.6g}  Pass={prompt_pass_total_s:.6g}  Pass/Raw={safe_frac(prompt_pass_total_s, prompt_raw_total_s):.4f}\n"
        f"[DELAYED] Raw={delayed_raw_total:.6g}  Pass={delayed_pass_total:.6g}  Pass/Raw={safe_frac(delayed_pass_total, delayed_raw_total):.4f}"
    )

    # ---- Plot (1): TOTAL raw vs pass
    plot1_raw_vs_pass(
        e_cent=e_cent,
        total_raw=total_raw,
        total_pass=total_pass,
        thr=args.thr,
        out_png=outdir / "fig1_total_raw_vs_pass.png",
        binw=args.binw
    )
    print(f"[OK] wrote {outdir/'fig1_total_raw_vs_pass.png'}")

    # ---- Plot (2): pass only with dashed components
    plot2_pass_with_components(
        e_cent=e_cent,
        total_pass=total_pass,
        prompt_pass=prompt_pass_s,
        delayed_pass=delayed_pass,
        thr=args.thr,
        out_png=outdir / "fig2_pass_total_with_components.png",
        binw=args.binw,
        totals_text=tot_text
    )
    print(f"[OK] wrote {outdir/'fig2_pass_total_with_components.png'}")

    # ---- Plot (3): zoom pass only with dashed components
    # (annotation still uses overall totals; 如果你想换成 zoom 区间 totals，我也能给你改)
    plot3_zoom_pass(
        e_cent_zoom=z_cent,
        total_pass_zoom=total_pass_zoom,
        prompt_pass_zoom=prompt_pass_zoom_s,
        delayed_pass_zoom=delayed_pass_zoom,
        thr=args.thr,
        out_png=outdir / "fig3_pass_zoom_500_550.png",
        binw_zoom=args.zoom_binw,
        totals_text=tot_text
    )
    print(f"[OK] wrote {outdir/'fig3_pass_zoom_500_550.png'}")

    # ---- Sanity prints
    print("\n[SANITY]")
    print(f"  PROMPT× Raw   = {prompt_raw_total_s:.6g}")
    print(f"  DELAYED Raw   = {delayed_raw_total:.6g}")
    print(f"  TOTAL Raw     = {total_raw_total:.6g}")
    print(f"  TOTAL Pass    = {total_pass_total:.6g}")
    print(f"  TOTAL Pass (zoom binning sum) = {total_pass_zoom_total:.6g}  (should be <= TOTAL Pass)")
    print("[DONE]")


if __name__ == "__main__":
    main()
