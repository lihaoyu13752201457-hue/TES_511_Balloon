#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NaI active-shield substitution workflow for the day-15 TES 511-keV chain.

This file intentionally lives under Records/08 so the BGO baseline code and
production products remain untouched.  It prepares a copied geometry where the
active shield volume keeps the legacy detector name ``BGO_Shield`` but uses the
MEGAlib ``NaI`` material, then analyzes prompt, delayed, and Laue-science SIM
outputs with a NaI-veto threshold.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import os
import pickle
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / ".mplconfig"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
import make_complete_day15_report as complete  # noqa: E402

COSIMA = "/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima"
GEOM_DIR = HERE / "geometry"
SOURCE_DIR = HERE / "sources_fullsphere20_nai"
RUNS_DIR = HERE / "runs"
OUTPUT_DIR = HERE / "analysis"

GEOM_SETUP = GEOM_DIR / "TibetTES_v5_6layers_NaI.geo.setup"
INSTANT_DIR = RUNS_DIR / "instant_nai_gamma500k"
BUILDUP_DIR = RUNS_DIR / "buildup_nai_gamma500k"
DECAY_DIR = RUNS_DIR / "decay_from_buildup_day15"
DELAY_FIX_DIR = RUNS_DIR / "delay_fix_day15"
SCIENCE_DIR = RUNS_DIR / "laue_science_nai_detector"

SCIENCE_SOURCE_IN = ROOT / "run_configs/opticsim_bridge/Opticsim_laue_511_mono_ge_hkl_f17p5_100k_20260521_poisson1800.source"
SCIENCE_SUMMARY = ROOT / "reports_260516/opticsim_mixed_timeline_laue_511_f17p5_fullchain_20260521/summary.json"
NUBASE = ROOT / "cosmosray_buildup_rpmpia/decay_rpip_out/nubase_2020.txt"
HALF_LIFE_CACHE = ROOT / "cosmosray_buildup_rpmpia/decay_rpip_out/half_life_cache.json"
BOUNDS = ROOT / "XZTES/bounds.json"

ZOOM = (480.0, 550.0, 0.5)
MAIN = (100.0, 10000.0, 10.0)
LINE = (510.3, 511.8)

ID_RE = re.compile(r"^ID\s+(\d+)")
CC_HIT_RE = complete.CC_HIT_RE
TP_RE = complete.TP_RE
TAG_RE = re.compile(r"Background_(?P<tag>[^_]+)_", re.IGNORECASE)


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="", errors="ignore") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def axis(emin: float, emax: float, binw: float) -> tuple[np.ndarray, np.ndarray]:
    edges = np.arange(emin, emax + 0.5 * binw, binw)
    return edges, 0.5 * (edges[:-1] + edges[1:])


def tag_from_path(path: Path) -> str:
    m = TAG_RE.search(path.name)
    return m.group("tag").lower() if m else "unknown"


def open_text(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return path.open("r", encoding="utf-8", errors="ignore")


def prepare_inputs() -> dict[str, Any]:
    """Copy baseline inputs and patch only the local copies."""
    GEOM_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    DECAY_DIR.mkdir(parents=True, exist_ok=True)

    for name in ("Intro_TibetTES.geo", "Materials_TibetTES.geo", "TibetTES_v5_6layers.det", "bounds.json"):
        shutil.copy2(ROOT / "XZTES" / name, GEOM_DIR / name)

    geo_text = (ROOT / "XZTES/TibetTES_v5_6layers.geo").read_text(encoding="utf-8")
    geo_text = geo_text.replace("BGO_Shield.Material BGO", "BGO_Shield.Material NaI")
    (GEOM_DIR / "TibetTES_v5_6layers_NaI.geo").write_text(geo_text, encoding="utf-8")
    GEOM_SETUP.write_text(
        "Name TibetTES_NaI_Shield\n"
        "Version 1\n"
        "Include TibetTES_v5_6layers_NaI.geo\n"
        "Include TibetTES_v5_6layers.det\n"
        "SurroundingSphere 150 0 0 19 150\n",
        encoding="utf-8",
    )

    for src in sorted((ROOT / "megalib_sources_fullsphere20").glob("Background_*_fullsphere20.source")):
        text = src.read_text(encoding="utf-8", errors="ignore")
        text = re.sub(r"^Geometry\s+.*$", f"Geometry {GEOM_SETUP}", text, flags=re.MULTILINE)
        (SOURCE_DIR / src.name).write_text(text, encoding="utf-8")

    if NUBASE.exists():
        shutil.copy2(NUBASE, DECAY_DIR / "nubase_2020.txt")
    if HALF_LIFE_CACHE.exists():
        DECAY_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(HALF_LIFE_CACHE, DECAY_DIR / "half_life_cache.json")

    summary = {
        "status": "prepared",
        "geometry_setup": rel(GEOM_SETUP),
        "material_substitution": "BGO_Shield.Material BGO -> NaI in copied geometry only",
        "volume_name_note": "The sensitive volume is still named BGO_Shield for detector-map compatibility; its material is NaI.",
        "source_dir": rel(SOURCE_DIR),
    }
    (HERE / "prepare_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def run_checked(cmd: list[str], cwd: Path = ROOT) -> None:
    print("[RUN]", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run(cmd, cwd=str(cwd), check=True)


def run_transport(args: argparse.Namespace) -> None:
    prepare_inputs()
    workers = str(args.workers)
    gamma_events = str(args.gamma_events)
    common = [
        "--source-dir",
        str(SOURCE_DIR),
        "--gamma-events",
        gamma_events,
        "--gamma-splits",
        str(args.gamma_splits),
        "--non-gamma-replicas",
        str(args.non_gamma_replicas),
        "--workers",
        workers,
        "--allow-heavy-run",
        "--keep-sources",
    ]
    run_checked(["python3", "tools/run_equiv2602_pipeline.py", "--mode", "instant", "--outdir", str(INSTANT_DIR), *common])
    run_checked(["python3", "tools/run_equiv2602_pipeline.py", "--mode", "buildup", "--outdir", str(BUILDUP_DIR), *common])

    DECAY_DIR.mkdir(parents=True, exist_ok=True)
    if NUBASE.exists():
        shutil.copy2(NUBASE, DECAY_DIR / "nubase_2020.txt")
    if HALF_LIFE_CACHE.exists():
        shutil.copy2(HALF_LIFE_CACHE, DECAY_DIR / "half_life_cache.json")

    run_checked(
        [
            "python3",
            "tools/makedecaysourcewithplot_rpip.py",
            "--dat",
            str(BUILDUP_DIR / "Background_*_fullsphere20_rep*_part*.dat.inc1.dat"),
            "--sim",
            str(BUILDUP_DIR / "Background_*_fullsphere20_rep*_part*.inc1.id1.sim.gz"),
            "--geo",
            str(GEOM_SETUP),
            "--non-gamma-div",
            str(args.non_gamma_replicas),
            "--t-flight-days",
            "15",
            "--outdir",
            str(DECAY_DIR),
            "--outfile-prefix",
            str(DECAY_DIR / "DelayedDecayNaIRPIP"),
            "--triggers",
            str(args.delayed_triggers),
            "--z-bins",
            "30",
            "--r-bins",
            "50",
            "--workers",
            workers,
            "--bounds",
            str(BOUNDS),
            "--plot-check",
        ]
    )

    run_checked(
        [
            "python3",
            "tools/build_fixed_delay_source.py",
            "--source",
            str(DECAY_DIR / "activation_decay_day15.source"),
            "--dat-glob",
            str(BUILDUP_DIR / "Background_*_fullsphere20_rep*_part*.dat.inc1.dat"),
            "--nubase",
            str(DECAY_DIR / "nubase_2020.txt"),
            "--outdir",
            str(DELAY_FIX_DIR),
            "--outfile-prefix",
            str(DELAY_FIX_DIR / "DelayedDecayNaIRPIPGroundStateFixed"),
            "--triggers",
            str(args.delayed_triggers),
            "--geometry",
            str(GEOM_SETUP),
            "--non-gamma-div",
            str(args.non_gamma_replicas),
            "--t-flight-days",
            "15",
        ]
    )

    run_checked([COSIMA, str(DELAY_FIX_DIR / "activation_decay_day15_groundstate_fixed.source")])
    run_science_source(args.science_triggers)


def run_science_source(triggers: int) -> Path:
    SCIENCE_DIR.mkdir(parents=True, exist_ok=True)
    text = SCIENCE_SOURCE_IN.read_text(encoding="utf-8", errors="ignore")
    text = re.sub(r"^Geometry\s+.*$", f"Geometry {GEOM_SETUP}", text, flags=re.MULTILINE)
    text = re.sub(r"^(Opticsim_\S+)\.FileName\s+.*$", rf"\1.FileName {SCIENCE_DIR / 'Opticsim_laue_f17p5_NaI'}", text, flags=re.MULTILINE)
    text = re.sub(r"^(Opticsim_\S+)\.Triggers\s+\d+", rf"\1.Triggers {int(triggers)}", text, flags=re.MULTILINE)
    out_source = SCIENCE_DIR / "Opticsim_laue_f17p5_NaI.source"
    out_source.write_text(text, encoding="utf-8")
    run_checked([COSIMA, str(out_source)])
    return SCIENCE_DIR / "Opticsim_laue_f17p5_NaI.inc1.id1.sim.gz"


def prompt_rate_per_event(path: Path, normalization: dict[str, Any]) -> float:
    tag = tag_from_path(path)
    div = float(normalization.get("non_gamma_replicas", 1.0))
    weight = 1.0 if tag == "gamma" else 1.0 / div
    prompt_time_s = float(normalization["gamma_prompt_time_s_with_farfield_area"])
    return weight / prompt_time_s


def delayed_rate_per_event(summary: dict[str, Any], triggers: int) -> float:
    return float(summary["new_total_activity_Bq"]) / max(1, int(triggers))


def science_rate_per_event(flux: float) -> float:
    summary = load_json(SCIENCE_SUMMARY, {})
    norm = summary.get("normalization", {}).get("science", {})
    area = float(norm.get("configured_laue_geometric_area_cm2", 151.05458624))
    primaries = float(norm.get("laue_primaries", 100000))
    return flux * area / primaries


def parse_sim(path: Path, stream: str, tag: str, rate_hz: float) -> dict[str, Any]:
    cat = complete.empty_catalog()
    cur_id: int | None = None
    shield = 0.0
    pix: dict[str, dict[str, float | int]] = {}

    def flush() -> None:
        nonlocal cur_id, shield, pix
        if cur_id is not None:
            complete.append_event(cat, stream, tag, str(path), int(cur_id), rate_hz, shield, pix)
        cur_id = None
        shield = 0.0
        pix = {}

    with open_text(path) as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            if line == "SE":
                flush()
                continue
            m_id = ID_RE.match(line)
            if m_id:
                cur_id = int(m_id.group(1))
                cat["n_generated_events_seen"] += 1
                continue
            if not line.startswith("CC HIT "):
                continue
            hit = complete.parse_cc_hit(line)
            if hit is None:
                continue
            vol, edep, x, y, z = hit
            m_tp = TP_RE.match(vol)
            if m_tp:
                layer = int(m_tp.group("layer"))
                rec = pix.setdefault(vol, {"e": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0, "layer": layer})
                rec["e"] = float(rec["e"]) + edep
                rec["wx"] = float(rec["wx"]) + edep * x
                rec["wy"] = float(rec["wy"]) + edep * y
                rec["wz"] = float(rec["wz"]) + edep * z
            elif "BGO_SHIELD" in vol.upper() or "NAI_SHIELD" in vol.upper():
                shield += edep
    flush()
    return cat


def build_catalog(args: argparse.Namespace) -> dict[str, Any]:
    cache = OUTPUT_DIR / "nai_event_catalog.pkl"
    if cache.exists() and not args.rebuild_catalog:
        with cache.open("rb") as fh:
            return pickle.load(fh)

    normalization = load_json(INSTANT_DIR / "normalization.json")
    delay_summary = load_json(DELAY_FIX_DIR / "source_fix_summary.json")
    delayed_source = DELAY_FIX_DIR / "activation_decay_day15_groundstate_fixed.source"
    delayed_triggers = parse_source_triggers(delayed_source)
    delayed_sim = DELAY_FIX_DIR / "DelayedDecayNaIRPIPGroundStateFixed.inc1.id1.sim.gz"
    if not delayed_sim.exists():
        matches = sorted(DELAY_FIX_DIR.glob("DelayedDecayNaIRPIPGroundStateFixed*.sim.gz"))
        delayed_sim = matches[0] if matches else delayed_sim
    science_sim = SCIENCE_DIR / "Opticsim_laue_f17p5_NaI.inc1.id1.sim.gz"

    merged = complete.empty_catalog()
    prompt_files = sorted(INSTANT_DIR.glob("Background_*_fullsphere20_rep*_part*.inc1.id1.sim.gz"))
    for i, path in enumerate(prompt_files, 1):
        tag = tag_from_path(path)
        complete.merge_one_catalog_into(merged, parse_sim(path, "prompt", tag, prompt_rate_per_event(path, normalization)))
        if i % 10 == 0 or i == len(prompt_files):
            print(f"[INFO] prompt catalogs {i}/{len(prompt_files)} events={len(merged['stream'])}", flush=True)

    complete.merge_one_catalog_into(
        merged,
        parse_sim(delayed_sim, "delayed", "activation_nai_day15", delayed_rate_per_event(delay_summary, delayed_triggers)),
    )
    complete.merge_one_catalog_into(merged, parse_sim(science_sim, "science", "laue_f17p5", science_rate_per_event(args.science_flux)))
    cat = complete.catalog_to_arrays(merged)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with cache.open("wb") as fh:
        pickle.dump(cat, fh, protocol=pickle.HIGHEST_PROTOCOL)
    return cat


def parse_source_triggers(path: Path) -> int:
    text = path.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"\.Triggers\s+(\d+)", text)
    return int(m.group(1)) if m else 1


def direct_rates(cat: dict[str, Any], threshold: float, reject_policy: str) -> dict[str, Any]:
    complete.BGO_THR_KEV = float(threshold)
    out = {
        "windows": {},
        "spectrum_480_550": None,
        "component_rates": defaultdict(lambda: defaultdict(float)),
    }
    windows = {"broad_480_550": (480.0, 550.0), "line_510p3_511p8": LINE}
    for wname, (lo, hi) in windows.items():
        rates = defaultdict(float)
        by_stream = defaultdict(lambda: defaultdict(float))
        classes = defaultdict(float)
        for idx in range(len(cat["stream"])):
            e = float(cat["tes_total_keV"][idx])
            if not (lo <= e < hi):
                continue
            rate = float(cat["rate_hz"][idx])
            stream = str(cat["stream"][idx])
            rates["raw"] += rate
            by_stream[stream]["raw"] += rate
            if float(cat["bgo_total_keV"][idx]) >= threshold:
                classes["nai_veto"] += rate
                continue
            rates["nai"] += rate
            by_stream[stream]["nai"] += rate
            keep, cls = complete.classify_final(complete.event_hits(cat, idx), reject_policy)
            classes[cls] += rate
            if keep:
                rates["final"] += rate
                by_stream[stream]["final"] += rate
        out["windows"][wname] = {
            "rates_cps": dict(rates),
            "rates_by_stream_cps": {k: dict(v) for k, v in by_stream.items()},
            "class_rate_cps": dict(classes),
        }

    edges, centers = axis(*ZOOM)
    cols = {
        "raw_cps_per_bin": np.zeros(len(centers)),
        "nai_veto_pass_cps_per_bin": np.zeros(len(centers)),
        "nai_plus_compton_cps_per_bin": np.zeros(len(centers)),
    }
    for idx in range(len(cat["stream"])):
        e = float(cat["tes_total_keV"][idx])
        if not (ZOOM[0] <= e < ZOOM[1]):
            continue
        k = int((e - ZOOM[0]) / ZOOM[2])
        rate = float(cat["rate_hz"][idx])
        cols["raw_cps_per_bin"][k] += rate
        if float(cat["bgo_total_keV"][idx]) < threshold:
            cols["nai_veto_pass_cps_per_bin"][k] += rate
            keep, _cls = complete.classify_final(complete.event_hits(cat, idx), reject_policy)
            if keep:
                cols["nai_plus_compton_cps_per_bin"][k] += rate
    out["spectrum_480_550"] = {"centers": centers, "cols": cols}
    return out


def timeline_rates(cat: dict[str, Any], threshold: float, obs_time_s: float, seed: int, reject_policy: str) -> dict[str, Any]:
    complete.BGO_THR_KEV = float(threshold)
    rng = np.random.default_rng(seed)
    timeline = complete.draw_timeline(cat, obs_time_s, rng)
    result = complete.analyze_timeline(cat, timeline, obs_time_s, reject_policy)
    return {"draw_summary": timeline["draw_summary"], "result": result}


def plot_spectrum(path: Path, centers: np.ndarray, cols: dict[str, np.ndarray], threshold: float) -> None:
    plt.figure(figsize=(10.5, 5.8))
    labels = {
        "raw_cps_per_bin": "No veto",
        "nai_veto_pass_cps_per_bin": f"NaI veto pass ({threshold:g} keV)",
        "nai_plus_compton_cps_per_bin": "NaI + Compton/FoV",
    }
    for key, y in cols.items():
        yy = np.where(y > 0, y, np.nan)
        plt.step(centers, yy, where="mid", label=labels.get(key, key), lw=1.5)
    plt.yscale("log")
    plt.xlim(480, 550)
    plt.xlabel("TES summed energy (keV)")
    plt.ylabel("Rate (cps/bin)")
    plt.title("NaI-shield day-15 480-550 keV veto chain")
    plt.grid(True, which="both", alpha=0.25)
    plt.legend()
    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=220)
    plt.close()


def plot_flux_scan(path: Path, rows: list[dict[str, Any]]) -> None:
    xs = [float(r["flux_ph_cm2_s"]) for r in rows]
    ys = [float(r["T3_days"]) for r in rows]
    plt.figure(figsize=(7.2, 5.0))
    plt.loglog(xs, ys, marker="o")
    plt.xlabel("511-keV point-source flux (ph cm$^{-2}$ s$^{-1}$)")
    plt.ylabel("Time to 3 sigma (days)")
    plt.title("NaI-shield 3-sigma point-source performance")
    plt.grid(True, which="both", alpha=0.3)
    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=220)
    plt.close()


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    cat = build_catalog(args)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    threshold_rows = []
    threshold_summaries = {}
    for thr in args.thresholds:
        direct = direct_rates(cat, thr, args.reject_policy)
        broad = direct["windows"]["broad_480_550"]
        threshold_rows.append(
            {
                "threshold_keV": thr,
                "raw_cps": broad["rates_cps"].get("raw", 0.0),
                "nai_pass_cps": broad["rates_cps"].get("nai", 0.0),
                "final_cps": broad["rates_cps"].get("final", 0.0),
                "final_prompt_cps": broad["rates_by_stream_cps"].get("prompt", {}).get("final", 0.0),
                "final_delayed_cps": broad["rates_by_stream_cps"].get("delayed", {}).get("final", 0.0),
                "final_science_cps_at_reference_flux": broad["rates_by_stream_cps"].get("science", {}).get("final", 0.0),
            }
        )
        threshold_summaries[str(thr)] = direct["windows"]

    direct = direct_rates(cat, args.threshold, args.reject_policy)
    spec = direct["spectrum_480_550"]
    spec_rows = []
    centers = spec["centers"]
    for i, e in enumerate(centers):
        rec = {"E_keV": e}
        rec.update({k: float(v[i]) for k, v in spec["cols"].items()})
        spec_rows.append(rec)
    write_csv(OUTPUT_DIR / "spectrum_480_550_nai_veto.csv", spec_rows, ["E_keV", *spec["cols"].keys()])
    plot_spectrum(OUTPUT_DIR / "spectrum_480_550_nai_veto.png", centers, spec["cols"], args.threshold)

    broad = direct["windows"]["broad_480_550"]
    final_bg = (
        broad["rates_by_stream_cps"].get("prompt", {}).get("final", 0.0)
        + broad["rates_by_stream_cps"].get("delayed", {}).get("final", 0.0)
    )
    signal_at_ref = broad["rates_by_stream_cps"].get("science", {}).get("final", 0.0)
    response = signal_at_ref / args.science_flux if args.science_flux > 0 else 0.0
    flux_rows = []
    for flux in args.flux_scan:
        signal = response * flux
        t3 = (3.0 * math.sqrt(final_bg) / signal) ** 2 if final_bg > 0 and signal > 0 else math.inf
        flux_rows.append({"flux_ph_cm2_s": flux, "signal_cps": signal, "background_cps": final_bg, "T3_s": t3, "T3_days": t3 / 86400.0})
    write_csv(OUTPUT_DIR / "point_source_3sigma_flux_scan.csv", flux_rows, ["flux_ph_cm2_s", "signal_cps", "background_cps", "T3_s", "T3_days"])
    plot_flux_scan(OUTPUT_DIR / "point_source_3sigma_flux_scan.png", flux_rows)

    write_csv(
        OUTPUT_DIR / "nai_threshold_scan_480_550.csv",
        threshold_rows,
        [
            "threshold_keV",
            "raw_cps",
            "nai_pass_cps",
            "final_cps",
            "final_prompt_cps",
            "final_delayed_cps",
            "final_science_cps_at_reference_flux",
        ],
    )

    tl = timeline_rates(cat, args.threshold, args.obs_time_s, args.seed, args.reject_policy)
    summary = {
        "status": "PASS",
        "claim_level": "NAI_SHIELD_MATERIAL_SUBSTITUTION_PILOT_MC",
        "inputs": {
            "geometry_setup": rel(GEOM_SETUP),
            "instant_dir": rel(INSTANT_DIR),
            "buildup_dir": rel(BUILDUP_DIR),
            "delayed_source": rel(DELAY_FIX_DIR / "activation_decay_day15_groundstate_fixed.source"),
            "science_dir": rel(SCIENCE_DIR),
        },
        "normalization": {
            "science_flux_ph_cm2_s": args.science_flux,
            "nai_veto_threshold_nominal_keV": args.threshold,
            "threshold_scan_keV": args.thresholds,
            "coincidence_window_s": complete.COINCIDENCE_WINDOW_S,
            "timeline_obs_time_s": args.obs_time_s,
            "reject_policy": args.reject_policy,
        },
        "catalog": {
            "events_kept": int(len(cat["stream"])),
            "pixel_hits_kept": int(len(cat["pix_e"])),
            "rate_by_stream_hz": {s: float(np.sum(cat["rate_hz"][cat["stream"] == s])) for s in ("prompt", "delayed", "science")},
        },
        "direct_window_rates": direct["windows"],
        "threshold_scan": threshold_rows,
        "point_source_3sigma": {
            "background_final_cps_480_550": final_bg,
            "science_response_cps_per_ph_cm2_s": response,
            "flux_scan_csv": rel(OUTPUT_DIR / "point_source_3sigma_flux_scan.csv"),
            "flux_scan_png": rel(OUTPUT_DIR / "point_source_3sigma_flux_scan.png"),
        },
        "timeline_realization": {
            "draw_summary": tl["draw_summary"],
            "rates_cps_480_550": {k: float(v) for k, v in tl["result"]["stage_rates"].items()},
            "counts_480_550": {k: int(v) for k, v in tl["result"]["stage_counts"].items()},
            "n_candidates_total": int(tl["result"]["n_candidates_total"]),
            "n_candidates_with_tes": int(tl["result"]["n_candidates_with_tes"]),
            "n_mixed_candidates": int(tl["result"]["n_mixed_candidates"]),
        },
        "outputs": {
            "spectrum_csv": rel(OUTPUT_DIR / "spectrum_480_550_nai_veto.csv"),
            "spectrum_png": rel(OUTPUT_DIR / "spectrum_480_550_nai_veto.png"),
            "threshold_scan_csv": rel(OUTPUT_DIR / "nai_threshold_scan_480_550.csv"),
        },
        "limitations": [
            "Pilot-statistics NaI material-substitution run; it is not a full 25M-primary production rerun.",
            "The active shield volume keeps the legacy name BGO_Shield so existing detector mapping and parser remain valid; the copied geometry material is NaI.",
            "Nominal NaI threshold is 100 keV, with 40/200 keV sensitivity scan retained because literature thresholds are instrument/electronics dependent.",
            "3-sigma performance is a counting/Asimov flux scan using the measured NaI detector response, not a full profile-likelihood injection campaign.",
        ],
    }
    (OUTPUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    write_readme(summary, flux_rows)
    return summary


def write_readme(summary: dict[str, Any], flux_rows: list[dict[str, Any]]) -> None:
    broad = summary["direct_window_rates"]["broad_480_550"]["rates_cps"]
    perf = summary["point_source_3sigma"]
    readme = f"""# NaI Shield Substitution, Day-15 Pilot

## What was changed

This directory is a copied-material substitution study.  The baseline
`XZTES` geometry was copied locally and only the active shield material was
changed from `BGO` to `NaI`:

- geometry: `{summary['inputs']['geometry_setup']}`
- legacy sensitive-volume name retained: `BGO_Shield`
- physical material in the copied geometry: `NaI`

The old BGO baseline code and old production files were not edited.

## NaI veto threshold

Nominal threshold used here: `{summary['normalization']['nai_veto_threshold_nominal_keV']}` keV.

Reasoning: NaI/CsI gamma-ray scintillator shield systems use instrument-specific
low-level discriminator settings.  The OSSE documentation describes a NaI(Tl)
annular active anticoincidence shield, with energy losses above 0.10 MeV used
for rejection and a programmable shield discriminator range of 0.03-0.47 MeV.
BeppoSAX/GRBM provides a lower-threshold CsI(Na) active-shield comparison point
near the 40-700 keV band.  Because the exact electronics for this concept are
not fixed, this study uses 100 keV as the NaI nominal threshold and keeps a
40/100/200 keV threshold scan.

Sources checked:

- BeppoSAX GRBM performance paper: https://arxiv.org/abs/astro-ph/9708168
- CGRO/OSSE instrument appendix: https://heasarc.gsfc.nasa.gov/docs/cgro/cossc/nra/appendix_g.html

## Day-15 480-550 keV result

Direct expectation rates:

| stage | rate cps |
|---|---:|
| no veto | {broad.get('raw', 0.0):.6g} |
| NaI veto pass | {broad.get('nai', 0.0):.6g} |
| NaI + Compton/FoV | {broad.get('final', 0.0):.6g} |

Final background-only rate used for the 3-sigma point-source scan:
`{perf['background_final_cps_480_550']:.6g}` cps.

Science response:
`{perf['science_response_cps_per_ph_cm2_s']:.6g}` cps per ph cm^-2 s^-1.

## 3-sigma performance

| flux ph cm^-2 s^-1 | T3 days |
|---:|---:|
"""
    for row in flux_rows:
        readme += f"| {float(row['flux_ph_cm2_s']):.6g} | {float(row['T3_days']):.6g} |\n"
    readme += f"""
## Outputs

- spectrum: `{summary['outputs']['spectrum_csv']}`
- spectrum figure: `{summary['outputs']['spectrum_png']}`
- threshold scan: `{summary['outputs']['threshold_scan_csv']}`
- flux scan: `{perf['flux_scan_csv']}`

## Claim boundary

This is a pilot-statistics material-substitution run.  It is strong enough to
show whether NaI obviously helps or hurts in the same pipeline, but it should
not be called the final NaI design result until the same statistics as the BGO
baseline are rerun.
"""
    (HERE / "README.md").write_text(readme, encoding="utf-8")


def parse_thresholds(text: str) -> list[float]:
    return [float(x.strip()) for x in text.split(",") if x.strip()]


def parse_flux_scan(text: str) -> list[float]:
    return [float(x.strip()) for x in text.split(",") if x.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prepare")

    run = sub.add_parser("run")
    run.add_argument("--gamma-events", type=int, default=500_000)
    run.add_argument("--gamma-splits", type=int, default=2)
    run.add_argument("--non-gamma-replicas", type=int, default=2)
    run.add_argument("--workers", type=int, default=8)
    run.add_argument("--delayed-triggers", type=int, default=100_000)
    run.add_argument("--science-triggers", type=int, default=100_000)

    an = sub.add_parser("analyze")
    an.add_argument("--threshold", type=float, default=100.0)
    an.add_argument("--thresholds", type=parse_thresholds, default=parse_thresholds("40,100,200"))
    an.add_argument("--science-flux", type=float, default=1.0e-4)
    an.add_argument("--flux-scan", type=parse_flux_scan, default=parse_flux_scan("1e-5,3e-5,1e-4,3e-4,1e-3,3e-3,1e-2"))
    an.add_argument("--obs-time-s", type=float, default=1800.0)
    an.add_argument("--seed", type=int, default=20260522)
    an.add_argument("--reject-policy", default="keep")
    an.add_argument("--rebuild-catalog", action="store_true")

    args = ap.parse_args()
    if args.cmd == "prepare":
        print(json.dumps(prepare_inputs(), indent=2, ensure_ascii=False))
    elif args.cmd == "run":
        run_transport(args)
    elif args.cmd == "analyze":
        print(json.dumps(analyze(args), indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
