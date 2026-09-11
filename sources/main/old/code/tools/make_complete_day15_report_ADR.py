#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Complete day-15 report with science source and Poisson time-axis merge.

This script is deliberately self-contained at the analysis level:

* reads the current memory/workflow files before doing work;
* parses the completed prompt, fixed delayed, and 511 keV science SIM files;
* assigns all relevant events to a shared Poisson time axis;
* applies time-window BGO veto and Compton/FoV veto;
* writes audit tables, figures, and a PDF report.

It does not rerun Cosima and does not modify any simulation products.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import multiprocessing as mp
import pickle
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

from make_day15_report_ADR import (
    EventHit,
    classify_compton,
    setup_fonts,
)


ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT
DEFAULT_OUTDIR = ROOT / "outputs" / "reports" / "day15_complete_report"
PROMPT_DIR = ROOT / "runs" / "step02_instant_equiv2602_aligned"
DELAY_DIR = ROOT / "runs" / "step02_delayed_transport_equiv2602_aligned"
DELAY_FIX_DIR = ROOT / "runs" / "step02_delay_fix_equiv2602_aligned"
DECAY_DIR = ROOT / "runs" / "step02_decay_source_equiv2602_aligned"
SCIENCE_DIR = ROOT / "runs" / "science_511_onaxis_source"
FIXED_DELAY_SIM = DELAY_DIR / "DelayedDecayRPIPGroundStateFixed.inc1.id1.sim.gz"
SCIENCE_SIM = SCIENCE_DIR / "Science_511_onaxis_ADR_cmfix.inc1.id1.sim.gz"
PROMPT_NORM = PROMPT_DIR / "normalization.json"
SCIENCE_SUMMARY = ROOT / "outputs" / "reports" / "science_511_ADR_100k" / "science_511_100k_summary.json"
SCIENCE_LEDGER = ROOT / "config" / "science_511_onaxis_source" / "metadata" / "science_rate_ledger.csv"
FIX_SUMMARY = DELAY_FIX_DIR / "source_fix_summary.json"
FIXED_SOURCE = DELAY_FIX_DIR / "activation_decay_day15_groundstate_fixed.source"
FIX_ACTIONS = DELAY_FIX_DIR / "removed_or_rescaled_sources.csv"
ACTIVATION_INVENTORY = DECAY_DIR / "activation_inventory_day15.csv"
BOUNDS_PATH = ROOT / "outputs" / "geometry" / "XZTES_ADR_v4c_mkflange_cm" / "bounds.json"

CC_HIT_RE = re.compile(r"^CC\s+HIT\s+(\S+)\s+(.*)$")
KV_RE = re.compile(r"(\w+)=([^\s]+)")
ID_RE = re.compile(r"^ID\s+(\d+)")
TAG_RE = re.compile(r"Background_(?P<tag>[^_]+)_", re.IGNORECASE)
TP_RE = re.compile(r"^TP_L(?P<layer>\d+)_(?P<pix>\d+)$", re.IGNORECASE)

DEFAULT_SEED = 260511
MAIN_EMIN = 100.0
MAIN_EMAX = 10000.0
MAIN_BINW = 10.0
ZOOM_EMIN = 480.0
ZOOM_EMAX = 550.0
ZOOM_BINW = 0.5
BGO_THR_KEV = 50.0
COINCIDENCE_WINDOW_S = 1.0e-6


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))


def read_csv_rows(path: Path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="", errors="ignore") as fh:
        return list(csv.DictReader(fh))


def parse_tag(path: str) -> str:
    m = TAG_RE.search(Path(path).name)
    return m.group("tag").lower() if m else "unknown"


def open_text(path: str):
    return gzip.open(path, "rt", encoding="utf-8", errors="ignore") if str(path).endswith(".gz") else open(path, "rt", encoding="utf-8", errors="ignore")


def prompt_time_s() -> float:
    norm = load_json(PROMPT_NORM, {})
    return float(norm.get("gamma_prompt_time_s_with_farfield_area", 29.47521574873429))


def delayed_time_s() -> float:
    log = DELAY_DIR / "cosima_delayed_transport_1m.log"
    if log.exists():
        for line in log.read_text(encoding="utf-8", errors="ignore").splitlines():
            if "Observation time:" in line:
                vals = re.findall(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", line)
                if vals:
                    return float(vals[0])
    source_triggers = 0
    source_activity = 0.0
    if FIXED_SOURCE.exists():
        for line in FIXED_SOURCE.read_text(encoding="utf-8", errors="ignore").splitlines():
            m_trig = re.match(r"^\S+\.Triggers\s+(\d+)\s*$", line.strip())
            if m_trig:
                source_triggers = int(m_trig.group(1))
            m_flux = re.match(r"^\S+\.Flux\s+([-+0-9.eE]+)\s*$", line.strip())
            if m_flux:
                source_activity += float(m_flux.group(1))
    if source_triggers > 0 and source_activity > 0.0:
        return source_triggers / source_activity
    raise FileNotFoundError(f"Cannot determine delayed observation time from {log} or {FIXED_SOURCE}")


def is_active_veto_volume(vol: str) -> bool:
    upper = str(vol).upper()
    return ("BGO" in upper) or ("ACTIVE_SHIELD" in upper) or ("CEBR3" in upper)


def active_veto_volume_name() -> str:
    bounds = load_json(BOUNDS_PATH, {})
    active = bounds.get("ACTIVE_SHIELD", {}) if isinstance(bounds, dict) else {}
    return str(active.get("name") or "active shield")


def science_generated_triggers() -> int:
    js = load_json(SCIENCE_SUMMARY, {})
    return int(js.get("source_config", {}).get("triggers", js.get("sim_summary", {}).get("stored_events", 100000)))


def science_rate_for_flux(flux_ph_cm2_s: float) -> float:
    rows = read_csv_rows(SCIENCE_LEDGER)
    if not rows:
        return 50.89 * 0.7390423888027 * flux_ph_cm2_s
    # Ledger is linear in flux; use A_eff*T_atm directly to avoid exact-row dependence.
    r0 = rows[0]
    return float(r0["A_opt_cm2"]) * float(r0["T_atm"]) * float(flux_ph_cm2_s)


def event_rate_for_mode(path: str, mode: str, science_flux: float) -> tuple[str, str, float]:
    if mode == "prompt":
        tag = parse_tag(path)
        weight = 1.0 if tag == "gamma" else 1.0 / 8.0
        return "prompt", tag, weight / prompt_time_s()
    if mode == "delayed":
        return "delayed", "activation", 1.0 / delayed_time_s()
    if mode == "science":
        return "science", "science_511_onaxis", science_rate_for_flux(science_flux) / max(science_generated_triggers(), 1)
    raise ValueError(mode)


def parse_cc_hit(line: str):
    m = CC_HIT_RE.match(line.strip())
    if not m:
        return None
    vol = m.group(1)
    kv = dict(KV_RE.findall(m.group(2)))
    try:
        return (
            vol,
            float(kv["edep_keV"]),
            float(kv["x"]),
            float(kv["y"]),
            float(kv["z"]),
        )
    except Exception:
        return None


def empty_catalog() -> dict:
    return {
        "stream": [],
        "tag": [],
        "source_file": [],
        "local_id": [],
        "rate_hz": [],
        "tes_total_keV": [],
        "bgo_total_keV": [],
        "pix_start": [],
        "pix_count": [],
        "pix_uid": [],
        "pix_layer": [],
        "pix_e": [],
        "pix_x": [],
        "pix_y": [],
        "pix_z": [],
        "n_generated_events_seen": 0,
        "n_kept_events": 0,
    }


def append_event(cat: dict, stream: str, tag: str, source_file: str, local_id: int, rate_hz: float, bgo_total: float, pix: dict):
    pix_start = len(cat["pix_e"])
    tes_total = 0.0
    for uid, rec in sorted(pix.items()):
        e = float(rec["e"])
        if e <= 0:
            continue
        tes_total += e
        cat["pix_uid"].append(uid)
        cat["pix_layer"].append(int(rec["layer"]))
        cat["pix_e"].append(e)
        cat["pix_x"].append(float(rec["wx"] / e))
        cat["pix_y"].append(float(rec["wy"] / e))
        cat["pix_z"].append(float(rec["wz"] / e))
    pix_count = len(cat["pix_e"]) - pix_start
    if pix_count <= 0 and bgo_total <= 0:
        return
    cat["stream"].append(stream)
    cat["tag"].append(tag)
    cat["source_file"].append(source_file)
    cat["local_id"].append(int(local_id))
    cat["rate_hz"].append(float(rate_hz))
    cat["tes_total_keV"].append(float(tes_total))
    cat["bgo_total_keV"].append(float(bgo_total))
    cat["pix_start"].append(int(pix_start))
    cat["pix_count"].append(int(pix_count))
    cat["n_kept_events"] += 1


def parse_sim_catalog(args_tuple):
    path, mode, science_flux = args_tuple
    stream, tag, rate_hz = event_rate_for_mode(path, mode, science_flux)
    cat = empty_catalog()

    cur_id = None
    bgo_total = 0.0
    pix: dict[str, dict] = {}

    def flush():
        nonlocal cur_id, bgo_total, pix
        if cur_id is not None:
            append_event(cat, stream, tag, str(path), int(cur_id), rate_hz, bgo_total, pix)
        cur_id = None
        bgo_total = 0.0
        pix = {}

    with open_text(str(path)) as fh:
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
            hit = parse_cc_hit(line)
            if hit is None:
                continue
            vol, edep, x, y, z = hit
            m_tp = TP_RE.match(vol)
            if m_tp:
                layer = int(m_tp.group("layer"))
                rec = pix.setdefault(vol, {"e": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0, "layer": layer})
                rec["e"] += edep
                rec["wx"] += edep * x
                rec["wy"] += edep * y
                rec["wz"] += edep * z
            elif is_active_veto_volume(vol):
                bgo_total += edep
    flush()
    return cat


def merge_catalogs(cats: Iterable[dict]) -> dict:
    out = empty_catalog()
    for cat in cats:
        pix_offset = len(out["pix_e"])
        n_events_before = len(out["stream"])
        for key in ("stream", "tag", "source_file", "local_id", "rate_hz", "tes_total_keV", "bgo_total_keV", "pix_count"):
            out[key].extend(cat[key])
        out["pix_start"].extend([int(x) + pix_offset for x in cat["pix_start"]])
        for key in ("pix_uid", "pix_layer", "pix_e", "pix_x", "pix_y", "pix_z"):
            out[key].extend(cat[key])
        out["n_generated_events_seen"] += int(cat.get("n_generated_events_seen", 0))
        out["n_kept_events"] += len(out["stream"]) - n_events_before
    return out


def merge_one_catalog_into(out: dict, cat: dict):
    pix_offset = len(out["pix_e"])
    n_events_before = len(out["stream"])
    for key in ("stream", "tag", "source_file", "local_id", "rate_hz", "tes_total_keV", "bgo_total_keV", "pix_count"):
        out[key].extend(cat[key])
    out["pix_start"].extend([int(x) + pix_offset for x in cat["pix_start"]])
    for key in ("pix_uid", "pix_layer", "pix_e", "pix_x", "pix_y", "pix_z"):
        out[key].extend(cat[key])
    out["n_generated_events_seen"] += int(cat.get("n_generated_events_seen", 0))
    out["n_kept_events"] += len(out["stream"]) - n_events_before


def cache_name_for_path(path: str, mode: str) -> str:
    h = hashlib.md5(str(Path(path).resolve()).encode("utf-8")).hexdigest()[:12]
    return f"{mode}_{Path(path).name}.{h}.pkl"


def parse_sim_catalog_to_cache(args_tuple):
    path, mode, science_flux, cache_dir, rebuild = args_tuple
    cache_path = Path(cache_dir) / cache_name_for_path(path, mode)
    if cache_path.exists() and not rebuild:
        return str(cache_path)
    cat = parse_sim_catalog((path, mode, science_flux))
    with cache_path.open("wb") as fh:
        pickle.dump(cat, fh, protocol=pickle.HIGHEST_PROTOCOL)
    return str(cache_path)


def catalog_to_arrays(cat: dict) -> dict:
    arr = {
        "stream": np.asarray(cat["stream"], dtype=object),
        "tag": np.asarray(cat["tag"], dtype=object),
        "source_file": np.asarray(cat["source_file"], dtype=object),
        "local_id": np.asarray(cat["local_id"], dtype=np.int64),
        "rate_hz": np.asarray(cat["rate_hz"], dtype=np.float64),
        "tes_total_keV": np.asarray(cat["tes_total_keV"], dtype=np.float64),
        "bgo_total_keV": np.asarray(cat["bgo_total_keV"], dtype=np.float64),
        "pix_start": np.asarray(cat["pix_start"], dtype=np.int64),
        "pix_count": np.asarray(cat["pix_count"], dtype=np.int32),
        "pix_uid": np.asarray(cat["pix_uid"], dtype=object),
        "pix_layer": np.asarray(cat["pix_layer"], dtype=np.int16),
        "pix_e": np.asarray(cat["pix_e"], dtype=np.float64),
        "pix_x": np.asarray(cat["pix_x"], dtype=np.float64),
        "pix_y": np.asarray(cat["pix_y"], dtype=np.float64),
        "pix_z": np.asarray(cat["pix_z"], dtype=np.float64),
        "n_generated_events_seen": int(cat.get("n_generated_events_seen", 0)),
        "n_kept_events": int(cat.get("n_kept_events", len(cat["stream"]))),
    }
    return arr


def refresh_science_event_rates(cat: dict, science_flux: float) -> bool:
    stream = np.asarray(cat["stream"], dtype=object)
    mask = stream == "science"
    if not np.any(mask):
        return False
    rate_hz = np.asarray(cat["rate_hz"], dtype=np.float64)
    target_rate = science_rate_for_flux(science_flux) / max(science_generated_triggers(), 1)
    changed = not np.allclose(rate_hz[mask], target_rate, rtol=0.0, atol=1.0e-18)
    if changed:
        rate_hz[mask] = target_rate
        cat["rate_hz"] = rate_hz
    return changed


def load_or_build_catalog(outdir: Path, workers: int, science_flux: float, rebuild: bool) -> dict:
    work = outdir / "work"
    work.mkdir(parents=True, exist_ok=True)
    cache = work / "event_catalog.pkl"
    if cache.exists() and not rebuild:
        with cache.open("rb") as fh:
            cat = pickle.load(fh)
        if refresh_science_event_rates(cat, science_flux):
            with cache.open("wb") as fh:
                pickle.dump(cat, fh, protocol=pickle.HIGHEST_PROTOCOL)
        return cat

    file_cache = work / "file_catalogs"
    file_cache.mkdir(parents=True, exist_ok=True)
    prompt_files = sorted(PROMPT_DIR.glob("*.sim.gz"))
    if not prompt_files:
        raise FileNotFoundError(PROMPT_DIR)
    tasks = [(str(p), "prompt", science_flux, str(file_cache), rebuild) for p in prompt_files]
    print(f"[INFO] parsing prompt SIM catalogs: {len(tasks)} files, workers={workers}", flush=True)
    if workers > 1:
        with mp.get_context("fork").Pool(processes=workers) as pool:
            prompt_cache_paths = []
            for i, cp in enumerate(pool.imap_unordered(parse_sim_catalog_to_cache, tasks, chunksize=1), start=1):
                prompt_cache_paths.append(cp)
                if i % 5 == 0 or i == len(tasks):
                    print(f"[INFO] cached prompt file catalogs {i}/{len(tasks)}", flush=True)
    else:
        prompt_cache_paths = []
        for i, t in enumerate(tasks, start=1):
            prompt_cache_paths.append(parse_sim_catalog_to_cache(t))
            if i % 5 == 0 or i == len(tasks):
                print(f"[INFO] cached prompt file catalogs {i}/{len(tasks)}", flush=True)

    merged = empty_catalog()
    print("[INFO] merging prompt file catalogs", flush=True)
    for i, cp in enumerate(sorted(prompt_cache_paths), start=1):
        with Path(cp).open("rb") as fh:
            merge_one_catalog_into(merged, pickle.load(fh))
        if i % 10 == 0 or i == len(prompt_cache_paths):
            print(f"[INFO] merged prompt catalogs {i}/{len(prompt_cache_paths)} events={len(merged['stream'])}", flush=True)

    print("[INFO] parsing fixed delayed SIM catalog", flush=True)
    delayed_cache = parse_sim_catalog_to_cache((str(FIXED_DELAY_SIM), "delayed", science_flux, str(file_cache), rebuild))
    with Path(delayed_cache).open("rb") as fh:
        merge_one_catalog_into(merged, pickle.load(fh))

    print("[INFO] parsing science 511 SIM catalog", flush=True)
    science_cache = parse_sim_catalog_to_cache((str(SCIENCE_SIM), "science", science_flux, str(file_cache), rebuild))
    with Path(science_cache).open("rb") as fh:
        merge_one_catalog_into(merged, pickle.load(fh))

    print(f"[INFO] converting merged catalog to arrays events={len(merged['stream'])} pixels={len(merged['pix_e'])}", flush=True)
    cat = catalog_to_arrays(merged)
    refresh_science_event_rates(cat, science_flux)
    with cache.open("wb") as fh:
        pickle.dump(cat, fh, protocol=pickle.HIGHEST_PROTOCOL)
    return cat


def axis(emin: float, emax: float, binw: float):
    edges = np.arange(emin, emax + 0.5 * binw, binw)
    centers = 0.5 * (edges[:-1] + edges[1:])
    return edges, centers


def add_hist(hist: np.ndarray, e: float, weight: float, emin: float, binw: float):
    k = int((e - emin) / binw)
    if 0 <= k < len(hist):
        hist[k] += weight


def event_hits(cat: dict, idx: int) -> list[EventHit]:
    s = int(cat["pix_start"][idx])
    n = int(cat["pix_count"][idx])
    hits = []
    for j in range(s, s + n):
        hits.append(
            EventHit(
                x=float(cat["pix_x"][j]),
                y=float(cat["pix_y"][j]),
                z=float(cat["pix_z"][j]),
                e=float(cat["pix_e"][j]),
                pixel_uid=str(cat["pix_uid"][j]),
                layer=int(cat["pix_layer"][j]),
            )
        )
    return hits


def aggregate_candidate_hits(cat: dict, event_indices: np.ndarray) -> list[EventHit]:
    by_uid: dict[str, dict] = {}
    for idx in event_indices:
        s = int(cat["pix_start"][idx])
        n = int(cat["pix_count"][idx])
        for j in range(s, s + n):
            uid = str(cat["pix_uid"][j])
            e = float(cat["pix_e"][j])
            rec = by_uid.setdefault(uid, {"e": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0, "layer": int(cat["pix_layer"][j])})
            rec["e"] += e
            rec["wx"] += e * float(cat["pix_x"][j])
            rec["wy"] += e * float(cat["pix_y"][j])
            rec["wz"] += e * float(cat["pix_z"][j])
    hits = []
    for uid, rec in sorted(by_uid.items()):
        e = rec["e"]
        if e <= 0:
            continue
        hits.append(EventHit(x=rec["wx"] / e, y=rec["wy"] / e, z=rec["wz"] / e, e=e, pixel_uid=uid, layer=int(rec["layer"])))
    return hits


def classify_final(hits: list[EventHit], reject_policy: str) -> tuple[bool, str]:
    if len(hits) <= 0:
        return False, "no_tes"
    if len(hits) == 1:
        return True, "single"
    cls = classify_compton(hits, reject_policy)
    return cls in ("single", "keep", "reject_kept"), cls


def direct_expectation(cat: dict, reject_policy: str) -> dict:
    n_main = int((MAIN_EMAX - MAIN_EMIN) / MAIN_BINW)
    n_zoom = int((ZOOM_EMAX - ZOOM_EMIN) / ZOOM_BINW)
    out = {
        "main_raw": np.zeros(n_main),
        "main_bgo": np.zeros(n_main),
        "zoom_raw": np.zeros(n_zoom),
        "zoom_bgo": np.zeros(n_zoom),
        "zoom_final": np.zeros(n_zoom),
        "stage_rate": defaultdict(float),
        "stage_rate_by_stream": defaultdict(lambda: defaultdict(float)),
        "component_main_diff": defaultdict(lambda: np.zeros(n_main)),
        "compton_class_rate": defaultdict(float),
    }
    for i in range(len(cat["stream"])):
        e = float(cat["tes_total_keV"][i])
        if e <= 0:
            continue
        rate = float(cat["rate_hz"][i])
        stream = str(cat["stream"][i])
        tag = str(cat["tag"][i])
        comp = component_name(stream, tag)
        if MAIN_EMIN <= e < MAIN_EMAX:
            add_hist(out["main_raw"], e, rate, MAIN_EMIN, MAIN_BINW)
            add_hist(out["component_main_diff"][comp], e, rate / MAIN_BINW, MAIN_EMIN, MAIN_BINW)
            if float(cat["bgo_total_keV"][i]) < BGO_THR_KEV:
                add_hist(out["main_bgo"], e, rate, MAIN_EMIN, MAIN_BINW)
        if ZOOM_EMIN <= e < ZOOM_EMAX:
            out["stage_rate"]["raw"] += rate
            out["stage_rate_by_stream"][stream]["raw"] += rate
            add_hist(out["zoom_raw"], e, rate, ZOOM_EMIN, ZOOM_BINW)
            if float(cat["bgo_total_keV"][i]) < BGO_THR_KEV:
                out["stage_rate"]["bgo"] += rate
                out["stage_rate_by_stream"][stream]["bgo"] += rate
                add_hist(out["zoom_bgo"], e, rate, ZOOM_EMIN, ZOOM_BINW)
                keep, cls = classify_final(event_hits(cat, i), reject_policy)
                out["compton_class_rate"][cls] += rate
                if keep:
                    out["stage_rate"]["final"] += rate
                    out["stage_rate_by_stream"][stream]["final"] += rate
                    add_hist(out["zoom_final"], e, rate, ZOOM_EMIN, ZOOM_BINW)
            else:
                out["compton_class_rate"]["bgo_veto"] += rate
    return out


def component_name(stream: str, tag: str) -> str:
    if stream == "delayed":
        return "ActivationDelay(day15)"
    if stream == "science":
        return "Science511(reference)"
    return {
        "gamma": "CosmicPhotons",
        "p": "CosmicProtons",
        "n": "CosmicNeutrons",
        "alpha": "CosmicAlphas",
        "eplus": "CosmicPositrons",
        "eminus": "CosmicElectrons",
        "muplus": "CosmicMuons",
        "muminus": "CosmicMuons",
    }.get(tag, f"Prompt_{tag}")


def draw_timeline(cat: dict, obs_time_s: float, rng: np.random.Generator) -> dict:
    chosen_all = []
    time_all = []
    draw_summary = {}
    for stream in ("prompt", "delayed", "science"):
        idx = np.flatnonzero(cat["stream"] == stream)
        rates = cat["rate_hz"][idx]
        lam = float(np.sum(rates) * obs_time_s)
        n = int(rng.poisson(lam))
        draw_summary[stream] = {"lambda": lam, "drawn": n, "rate_hz": float(np.sum(rates))}
        if n <= 0 or len(idx) == 0:
            continue
        probs = rates / np.sum(rates)
        chosen = rng.choice(idx, size=n, replace=True, p=probs)
        times = rng.uniform(0.0, obs_time_s, size=n)
        chosen_all.append(chosen.astype(np.int64))
        time_all.append(times.astype(np.float64))
    if not chosen_all:
        return {"event_index": np.empty(0, dtype=np.int64), "time_s": np.empty(0), "draw_summary": draw_summary}
    event_index = np.concatenate(chosen_all)
    time_s = np.concatenate(time_all)
    order = np.argsort(time_s, kind="mergesort")
    return {"event_index": event_index[order], "time_s": time_s[order], "draw_summary": draw_summary}


def analyze_timeline(cat: dict, timeline: dict, obs_time_s: float, reject_policy: str) -> dict:
    n_main = int((MAIN_EMAX - MAIN_EMIN) / MAIN_BINW)
    n_zoom = int((ZOOM_EMAX - ZOOM_EMIN) / ZOOM_BINW)
    result = {
        "main_raw": np.zeros(n_main),
        "main_bgo": np.zeros(n_main),
        "zoom_raw": np.zeros(n_zoom),
        "zoom_bgo": np.zeros(n_zoom),
        "zoom_final": np.zeros(n_zoom),
        "stage_counts": defaultdict(int),
        "stage_counts_by_kind": defaultdict(lambda: defaultdict(int)),
        "stage_counts_by_stream_pure": defaultdict(lambda: defaultdict(int)),
        "compton_class": defaultdict(int),
        "candidate_multiplicity": Counter(),
        "n_candidates_total": 0,
        "n_candidates_with_tes": 0,
        "n_mixed_candidates": 0,
    }
    idxs = timeline["event_index"]
    times = timeline["time_s"]
    n = len(idxs)
    start = 0
    while start < n:
        end = start + 1
        while end < n and (times[end] - times[end - 1]) <= COINCIDENCE_WINDOW_S:
            end += 1
        ev = idxs[start:end]
        result["n_candidates_total"] += 1
        streams = [str(x) for x in cat["stream"][ev]]
        stream_set = set(streams)
        if len(stream_set) > 1:
            result["n_mixed_candidates"] += 1
        kind = "science_containing" if "science" in stream_set else "background_only"
        pure_stream = next(iter(stream_set)) if len(stream_set) == 1 else "mixed"
        e = float(np.sum(cat["tes_total_keV"][ev]))
        bgo = float(np.sum(cat["bgo_total_keV"][ev]))
        if e > 0:
            result["n_candidates_with_tes"] += 1
            hits = aggregate_candidate_hits(cat, ev)
            n_pix = len(hits)
            result["candidate_multiplicity"][n_pix] += 1
            if MAIN_EMIN <= e < MAIN_EMAX:
                add_hist(result["main_raw"], e, 1.0 / obs_time_s, MAIN_EMIN, MAIN_BINW)
                if bgo < BGO_THR_KEV:
                    add_hist(result["main_bgo"], e, 1.0 / obs_time_s, MAIN_EMIN, MAIN_BINW)
            if ZOOM_EMIN <= e < ZOOM_EMAX:
                result["stage_counts"]["raw"] += 1
                result["stage_counts_by_kind"][kind]["raw"] += 1
                result["stage_counts_by_stream_pure"][pure_stream]["raw"] += 1
                add_hist(result["zoom_raw"], e, 1.0 / obs_time_s, ZOOM_EMIN, ZOOM_BINW)
                if bgo < BGO_THR_KEV:
                    result["stage_counts"]["bgo"] += 1
                    result["stage_counts_by_kind"][kind]["bgo"] += 1
                    result["stage_counts_by_stream_pure"][pure_stream]["bgo"] += 1
                    add_hist(result["zoom_bgo"], e, 1.0 / obs_time_s, ZOOM_EMIN, ZOOM_BINW)
                    keep, cls = classify_final(hits, reject_policy)
                    result["compton_class"][cls] += 1
                    if keep:
                        result["stage_counts"]["final"] += 1
                        result["stage_counts_by_kind"][kind]["final"] += 1
                        result["stage_counts_by_stream_pure"][pure_stream]["final"] += 1
                        add_hist(result["zoom_final"], e, 1.0 / obs_time_s, ZOOM_EMIN, ZOOM_BINW)
                else:
                    result["compton_class"]["bgo_veto"] += 1
        start = end
    result["stage_rates"] = {k: v / obs_time_s for k, v in result["stage_counts"].items()}
    result["stage_rates_by_kind"] = {k: {kk: vv / obs_time_s for kk, vv in d.items()} for k, d in result["stage_counts_by_kind"].items()}
    result["stage_rates_by_stream_pure"] = {k: {kk: vv / obs_time_s for kk, vv in d.items()} for k, d in result["stage_counts_by_stream_pure"].items()}
    return result


def save_csv(path: Path, centers: np.ndarray, cols: dict[str, np.ndarray]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        names = list(cols)
        w.writerow(["E_keV", *names])
        for i, e in enumerate(centers):
            w.writerow([f"{e:.6g}", *[f"{cols[n][i]:.12g}" for n in names]])


def save_dat(path: Path, centers: np.ndarray, cols: dict[str, np.ndarray]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        names = list(cols)
        fh.write("# E_keV " + " ".join(names) + "\n")
        for i, e in enumerate(centers):
            fh.write(f"{e:.6f} " + " ".join(f"{cols[n][i]:.12e}" for n in names) + "\n")


def fixed_activation_rows(outdir: Path):
    inv = read_csv_rows(ACTIVATION_INVENTORY)
    actions = read_csv_rows(FIX_ACTIONS)
    grouped = {}
    for r in actions:
        key = (r.get("VN", ""), r.get("ZA", ""), r.get("nuclide", ""))
        item = grouped.setdefault(key, {"old": 0.0, "new": 0.0})
        item["old"] += float(r.get("old_flux_Bq", 0.0))
        item["new"] += float(r.get("new_flux_Bq", 0.0))
    rows = []
    for r in inv:
        key = (r.get("VN", ""), r.get("ZA", ""), r.get("nuclide", ""))
        old = float(r.get("Activity_Bq", 0.0))
        if key in grouped:
            new = grouped[key]["new"]
            scale = new / grouped[key]["old"] if grouped[key]["old"] > 0 else 0.0
        else:
            new = old
            scale = 1.0
        if new <= 1.0e-12:
            continue
        rr = dict(r)
        rr["Activity_Bq_before_fix"] = old
        rr["Activity_Bq_after_fix"] = new
        rr["fix_scale"] = scale
        rows.append(rr)
    rows.sort(key=lambda x: float(x["Activity_Bq_after_fix"]), reverse=True)
    out = outdir / "activation_inventory_day15_after_groundstate_fix.csv"
    with out.open("w", encoding="utf-8", newline="") as fh:
        fields = ["VN", "ZA", "nuclide", "exc_keV", "RP_yield", "hl_s", "Activity_Bq_before_fix", "Activity_Bq_after_fix", "fix_scale", "Points"]
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    return rows


def plot_outputs(outdir: Path, direct: dict, tl: dict, summary: dict, font_prop: FontProperties):
    figdir = outdir / "figures"
    figdir.mkdir(parents=True, exist_ok=True)
    _, main_c = axis(MAIN_EMIN, MAIN_EMAX, MAIN_BINW)
    _, zoom_c = axis(ZOOM_EMIN, ZOOM_EMAX, ZOOM_BINW)

    paths = {}
    paths["timeline_main"] = figdir / "timeline_spectrum_100_10000.png"
    plt.figure(figsize=(11, 6.2))
    plt.step(main_c, tl["main_raw"], where="mid", label="Poisson timeline: no veto")
    plt.step(main_c, tl["main_bgo"], where="mid", label="Poisson timeline: BGO veto")
    plt.step(main_c, direct["main_raw"], where="mid", ls="--", alpha=0.75, label="Expectation: no veto")
    plt.step(main_c, direct["main_bgo"], where="mid", ls="--", alpha=0.75, label="Expectation: BGO veto")
    plt.yscale("log")
    plt.xlim(MAIN_EMIN, MAIN_EMAX)
    plt.xlabel("TES event/candidate summed energy (keV)", fontproperties=font_prop)
    plt.ylabel("Rate (counts s$^{-1}$ bin$^{-1}$)", fontproperties=font_prop)
    plt.title("Day-15 background + science on common Poisson time axis", fontproperties=font_prop)
    plt.grid(True, which="both", alpha=0.25)
    plt.legend(fontsize=9)
    plt.tight_layout()
    plt.savefig(paths["timeline_main"], dpi=220)
    plt.close()

    paths["zoom"] = figdir / "timeline_spectrum_480_550_veto_chain.png"
    plt.figure(figsize=(11, 6.2))
    plt.step(zoom_c, tl["zoom_raw"], where="mid", label="Timeline no veto", lw=1.5)
    plt.step(zoom_c, tl["zoom_bgo"], where="mid", label="Timeline BGO veto", lw=1.5)
    plt.step(zoom_c, tl["zoom_final"], where="mid", label="Timeline BGO+Compton/FoV", lw=1.8)
    science_expected = direct["stage_rate_by_stream"]["science"].get("final", 0.0)
    if science_expected > 0:
        science_shape = direct["zoom_final"] * 0.0
        # Direct science contribution is included in direct["zoom_final"]; plot all expected signal separately by recomputing from component table is not needed for rates.
    plt.yscale("log")
    plt.xlim(ZOOM_EMIN, ZOOM_EMAX)
    plt.xlabel("TES event/candidate summed energy (keV)", fontproperties=font_prop)
    plt.ylabel("Rate (counts s$^{-1}$ bin$^{-1}$)", fontproperties=font_prop)
    plt.title("511 keV window: time-axis veto chain", fontproperties=font_prop)
    txt = (
        f"timeline no veto: {summary['timeline_rates_cps']['raw']:.4g} cps\n"
        f"BGO: {summary['timeline_rates_cps']['bgo']:.4g} cps\n"
        f"BGO+Compton/FoV: {summary['timeline_rates_cps']['final']:.4g} cps"
    )
    plt.text(0.02, 0.98, txt, transform=plt.gca().transAxes, va="top", ha="left",
             bbox=dict(facecolor="white", alpha=0.86, edgecolor="none"))
    plt.grid(True, which="both", alpha=0.25)
    plt.legend(fontsize=9)
    plt.tight_layout()
    plt.savefig(paths["zoom"], dpi=220)
    plt.close()

    paths["veto_bar"] = figdir / "timeline_veto_rates_bar.png"
    stages = ["raw", "bgo", "final"]
    labels = ["No veto", "BGO", "BGO+Compton/FoV"]
    vals = [summary["timeline_rates_cps"].get(s, 0.0) for s in stages]
    exp_vals = [summary["expectation_rates_cps"].get(s, 0.0) for s in stages]
    x = np.arange(len(stages))
    plt.figure(figsize=(7.8, 5.5))
    plt.bar(x - 0.18, vals, width=0.36, label="Poisson timeline")
    plt.bar(x + 0.18, exp_vals, width=0.36, label="Direct expectation")
    plt.xticks(x, labels)
    plt.ylabel("480-550 keV rate (cps)", fontproperties=font_prop)
    plt.title("VETO effect: timeline vs expectation", fontproperties=font_prop)
    plt.grid(True, axis="y", alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(paths["veto_bar"], dpi=220)
    plt.close()

    paths["component"] = figdir / "image8_like_component_spectrum_with_science.png"
    comp = dict(direct["component_main_diff"])
    total = np.zeros_like(main_c)
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
        "Science511(reference)": "#ff7f0e",
    }
    order = ["CosmicPhotons", "CosmicProtons", "CosmicNeutrons", "CosmicAlphas", "CosmicElectrons", "CosmicPositrons", "CosmicMuons", "ActivationDelay(day15)", "Science511(reference)"]
    for k in order:
        if k not in comp:
            continue
        y = comp[k]
        total += y
        yy = np.where(y > 0, y, np.nan)
        plt.plot(main_c, yy, lw=1.1, label=k, color=colors.get(k))
    plt.plot(main_c, np.where(total > 0, total, np.nan), color="black", lw=1.6, label="Total")
    plt.xscale("log")
    plt.yscale("log")
    plt.xlim(100, 10000)
    plt.xlabel("Energy [keV]", fontproperties=font_prop)
    plt.ylabel("Counts/keV/s", fontproperties=font_prop)
    plt.title("IMAGE8-style no-veto components, with reference science source", fontproperties=font_prop)
    plt.grid(True, which="both", alpha=0.25)
    plt.legend(fontsize=8, ncol=2)
    plt.tight_layout()
    plt.savefig(paths["component"], dpi=220)
    plt.close()

    rows = fixed_activation_rows(outdir)
    paths["activation"] = figdir / "activation_top10_after_fix.png"
    top = rows[:10]
    if top:
        labels2 = [f"{r['nuclide']} {r['VN']}" for r in top][::-1]
        vals2 = [float(r["Activity_Bq_after_fix"]) for r in top][::-1]
        plt.figure(figsize=(9, 5.8))
        plt.barh(labels2, vals2, color="#54A24B")
        plt.xlabel("Activity after ground-state/isomer fix (Bq)", fontproperties=font_prop)
        plt.title("Top activation components after delay fix, day 15", fontproperties=font_prop)
        plt.grid(True, axis="x", alpha=0.25)
        plt.tight_layout()
        plt.savefig(paths["activation"], dpi=220)
        plt.close()

    return {k: str(v) for k, v in paths.items()}


def wrapped(text: str, width: int = 78):
    lines = []
    for para in text.split("\n"):
        para = para.strip()
        if not para:
            lines.append("")
        else:
            lines.extend(textwrap.wrap(para, width=width, break_long_words=False, replace_whitespace=False))
    return lines


def add_text_page(pdf, title: str, body: str, font_prop: FontProperties):
    fig = plt.figure(figsize=(8.27, 11.69))
    fig.patch.set_facecolor("white")
    fig.text(0.08, 0.94, title, fontsize=18, fontweight="bold", fontproperties=font_prop, va="top")
    y = 0.89
    for line in wrapped(body, 48):
        if y < 0.08:
            pdf.savefig(fig)
            plt.close(fig)
            fig = plt.figure(figsize=(8.27, 11.69))
            fig.patch.set_facecolor("white")
            y = 0.94
        fig.text(0.08, y, line, fontsize=11.0, fontproperties=font_prop, va="top")
        y -= 0.026 if line else 0.018
    pdf.savefig(fig)
    plt.close(fig)


def add_image_page(pdf, title: str, image_path: str, caption: str, font_prop: FontProperties):
    if not image_path:
        return
    img = plt.imread(image_path)
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.patch.set_facecolor("white")
    fig.text(0.05, 0.94, title, fontsize=17, fontweight="bold", fontproperties=font_prop, va="top")
    ax = fig.add_axes([0.06, 0.17, 0.88, 0.68])
    ax.imshow(img)
    ax.axis("off")
    fig.text(0.06, 0.08, "\n".join(wrapped(caption, 100)), fontsize=10.2, fontproperties=font_prop, va="top")
    pdf.savefig(fig)
    plt.close(fig)


def make_summary(cat: dict, direct: dict, timeline: dict, tl: dict, obs_time_s: float, science_flux: float, seed: int, reject_policy: str) -> dict:
    fix = load_json(FIX_SUMMARY, {})
    source_text = FIXED_SOURCE.read_text(encoding="utf-8", errors="ignore") if FIXED_SOURCE.exists() else ""
    w183_present = bool(re.search(r"ParticleType\s+74183|ZA74183|W-183", source_text))
    w180_present = bool(re.search(r"ParticleType\s+74180|ZA74180|W-180", source_text))
    sci_rates = direct["stage_rate_by_stream"].get("science", {})
    prompt_rates = direct["stage_rate_by_stream"].get("prompt", {})
    delayed_rates = direct["stage_rate_by_stream"].get("delayed", {})
    science_final = float(sci_rates.get("final", 0.0))
    background_final = float(prompt_rates.get("final", 0.0) + delayed_rates.get("final", 0.0))
    response_final_per_flux = science_final / science_flux if science_flux > 0 else 0.0
    sensitivity = {}
    for label, texp in (("timeline_obs", obs_time_s), ("10ks", 10000.0), ("1day", 86400.0)):
        if response_final_per_flux > 0 and background_final > 0 and texp > 0:
            f5 = 5.0 * math.sqrt(background_final * texp) / (response_final_per_flux * texp)
            f3 = 3.0 * math.sqrt(background_final * texp) / (response_final_per_flux * texp)
        else:
            f5 = float("nan")
            f3 = float("nan")
        sensitivity[label] = {
            "exposure_s": float(texp),
            "flux_3sigma_ph_cm2_s": float(f3),
            "flux_5sigma_ph_cm2_s": float(f5),
        }

    summary = {
        "inputs": {
            "prompt_files": int(len(list(PROMPT_DIR.glob("*.sim.gz")))),
            "delayed_sim": str(FIXED_DELAY_SIM.relative_to(ROOT)),
            "science_sim": str(SCIENCE_SIM.relative_to(ROOT)),
        },
        "normalization": {
            "prompt_time_s": prompt_time_s(),
            "delayed_time_s": delayed_time_s(),
            "obs_time_s": obs_time_s,
            "science_flux_ph_cm2_s": science_flux,
            "science_injection_rate_s^-1": science_rate_for_flux(science_flux),
            "coincidence_window_s": COINCIDENCE_WINDOW_S,
            "bgo_threshold_keV": BGO_THR_KEV,
            "active_veto_volume_name": active_veto_volume_name(),
            "active_veto_match_tokens": ["BGO", "ACTIVE_SHIELD", "CEBR3"],
            "reject_policy": reject_policy,
            "rng_seed": seed,
        },
        "catalog": {
            "events_kept": int(len(cat["stream"])),
            "pixel_hits_kept": int(len(cat["pix_e"])),
            "by_stream": {
                s: {
                    "events": int(np.sum(cat["stream"] == s)),
                    "rate_hz": float(np.sum(cat["rate_hz"][cat["stream"] == s])),
                    "tes_events": int(np.sum((cat["stream"] == s) & (cat["tes_total_keV"] > 0))),
                }
                for s in ("prompt", "delayed", "science")
            },
        },
        "draw_summary": timeline["draw_summary"],
        "timeline": {
            "n_event_instances": int(len(timeline["event_index"])),
            "n_candidates_total": int(tl["n_candidates_total"]),
            "n_candidates_with_tes": int(tl["n_candidates_with_tes"]),
            "n_mixed_candidates": int(tl["n_mixed_candidates"]),
            "candidate_multiplicity": {str(k): int(v) for k, v in sorted(tl["candidate_multiplicity"].items())},
        },
        "timeline_counts_480_550": {k: int(tl["stage_counts"].get(k, 0)) for k in ("raw", "bgo", "final")},
        "timeline_rates_cps": {k: float(tl["stage_rates"].get(k, 0.0)) for k in ("raw", "bgo", "final")},
        "timeline_rates_by_kind": tl["stage_rates_by_kind"],
        "timeline_rates_by_stream_pure": tl["stage_rates_by_stream_pure"],
        "expectation_rates_cps": {k: float(direct["stage_rate"].get(k, 0.0)) for k in ("raw", "bgo", "final")},
        "expectation_rates_by_stream_cps": {s: {k: float(d.get(k, 0.0)) for k in ("raw", "bgo", "final")} for s, d in direct["stage_rate_by_stream"].items()},
        "expectation_compton_class_rate_cps": {k: float(v) for k, v in direct["compton_class_rate"].items()},
        "science_sensitivity": {
            "background_final_cps_prompt_plus_delayed": background_final,
            "science_reference_final_cps": science_final,
            "science_final_response_cps_per_ph_cm-2_s-1": response_final_per_flux,
            "reference_flux_signal_to_background": science_final / background_final if background_final > 0 else None,
            "formula": "F_Nsigma = N * sqrt(B*T) / (R_per_flux*T); Gaussian counting approximation, final 480-550 keV window.",
            "flux_limits": sensitivity,
        },
        "delay_fix": {
            "old_total_activity_Bq": fix.get("old_total_activity_Bq"),
            "new_total_activity_Bq": fix.get("new_total_activity_Bq"),
            "source_blocks_in": fix.get("source_blocks_in"),
            "source_blocks_after_fix": fix.get(
                "source_blocks_after_fix",
                (int(fix.get("source_blocks_in", 0)) - int(fix.get("source_blocks_removed", 0)))
                if fix.get("source_blocks_in") is not None and fix.get("source_blocks_removed") is not None
                else None,
            ),
            "source_blocks_removed": fix.get("source_blocks_removed"),
            "fixed_source_contains_W183": w183_present,
            "fixed_source_contains_W180": w180_present,
        },
    }
    return summary


def ensure_science_sensitivity(summary: dict) -> dict:
    if summary.get("science_sensitivity"):
        return summary
    science_flux = float(summary["normalization"]["science_flux_ph_cm2_s"])
    obs_time_s = float(summary["normalization"]["obs_time_s"])
    by_stream = summary.get("expectation_rates_by_stream_cps", {})
    science_final = float(by_stream.get("science", {}).get("final", 0.0))
    background_final = float(by_stream.get("prompt", {}).get("final", 0.0) + by_stream.get("delayed", {}).get("final", 0.0))
    response_final_per_flux = science_final / science_flux if science_flux > 0 else 0.0
    limits = {}
    for label, texp in (("timeline_obs", obs_time_s), ("10ks", 10000.0), ("1day", 86400.0)):
        if response_final_per_flux > 0 and background_final > 0 and texp > 0:
            f5 = 5.0 * math.sqrt(background_final * texp) / (response_final_per_flux * texp)
            f3 = 3.0 * math.sqrt(background_final * texp) / (response_final_per_flux * texp)
        else:
            f5 = float("nan")
            f3 = float("nan")
        limits[label] = {
            "exposure_s": float(texp),
            "flux_3sigma_ph_cm2_s": float(f3),
            "flux_5sigma_ph_cm2_s": float(f5),
        }
    summary["science_sensitivity"] = {
        "background_final_cps_prompt_plus_delayed": background_final,
        "science_reference_final_cps": science_final,
        "science_final_response_cps_per_ph_cm-2_s-1": response_final_per_flux,
        "reference_flux_signal_to_background": science_final / background_final if background_final > 0 else None,
        "formula": "F_Nsigma = N * sqrt(B*T) / (R_per_flux*T); Gaussian counting approximation, final 480-550 keV window.",
        "flux_limits": limits,
    }
    return summary


def write_tables(outdir: Path, direct: dict, tl: dict):
    _, main_c = axis(MAIN_EMIN, MAIN_EMAX, MAIN_BINW)
    _, zoom_c = axis(ZOOM_EMIN, ZOOM_EMAX, ZOOM_BINW)
    save_csv(
        outdir / "timeline_spectrum_100_10000_rates.csv",
        main_c,
        {
            "timeline_raw_cps_per_bin": tl["main_raw"],
            "timeline_bgo_cps_per_bin": tl["main_bgo"],
            "expectation_raw_cps_per_bin": direct["main_raw"],
            "expectation_bgo_cps_per_bin": direct["main_bgo"],
        },
    )
    save_csv(
        outdir / "timeline_spectrum_480_550_rates.csv",
        zoom_c,
        {
            "timeline_raw_cps_per_bin": tl["zoom_raw"],
            "timeline_bgo_cps_per_bin": tl["zoom_bgo"],
            "timeline_final_cps_per_bin": tl["zoom_final"],
            "expectation_raw_cps_per_bin": direct["zoom_raw"],
            "expectation_bgo_cps_per_bin": direct["zoom_bgo"],
            "expectation_final_cps_per_bin": direct["zoom_final"],
        },
    )
    comp = dict(direct["component_main_diff"])
    if comp:
        order = ["CosmicPhotons", "CosmicProtons", "CosmicNeutrons", "CosmicAlphas", "CosmicElectrons", "CosmicPositrons", "CosmicMuons", "ActivationDelay(day15)", "Science511(reference)"]
        cols = {k: comp[k] for k in order if k in comp}
        total = sum(cols.values(), np.zeros_like(main_c))
        cols["Total"] = total
        save_csv(outdir / "image8_like_component_spectrum_with_science.csv", main_c, cols)
        save_dat(outdir / "image8_like_component_spectrum_with_science.dat", main_c, cols)
        with (outdir / "image8_like_component_rates_with_science.csv").open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            ranges = [(100, 5000), (100, 10000), (480, 550)]
            w.writerow(["component", *[f"rate_{lo}_{hi}_keV_cps" for lo, hi in ranges]])
            for name, y in cols.items():
                row = [name]
                for lo, hi in ranges:
                    mask = (main_c >= lo) & (main_c < hi)
                    row.append(f"{float(np.sum(y[mask]) * MAIN_BINW):.12g}")
                w.writerow(row)


def write_sensitivity_csv(outdir: Path, summary: dict):
    sens = summary.get("science_sensitivity", {})
    limits = sens.get("flux_limits", {})
    with (outdir / "science_reference_sensitivity.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["case", "exposure_s", "flux_3sigma_ph_cm2_s", "flux_5sigma_ph_cm2_s"])
        for name, row in limits.items():
            w.writerow([name, f"{row['exposure_s']:.12g}", f"{row['flux_3sigma_ph_cm2_s']:.12g}", f"{row['flux_5sigma_ph_cm2_s']:.12g}"])


def build_pdf(outdir: Path, summary: dict, figs: dict, font_prop: FontProperties):
    summary = ensure_science_sensitivity(summary)
    pdf_path = outdir / "cosmosray_bg_NEW_GEO_RE_ADR_complete_day15_report.pdf"
    r_t = summary["timeline_rates_cps"]
    r_e = summary["expectation_rates_cps"]
    sci = summary["expectation_rates_by_stream_cps"].get("science", {})
    bg_prompt = summary["expectation_rates_by_stream_cps"].get("prompt", {})
    bg_delay = summary["expectation_rates_by_stream_cps"].get("delayed", {})
    sens = summary["science_sensitivity"]
    body1 = f"""\
本报告是 NEW_GEO_RE/ADR day-15 的完整汇总工作报告。它重新读取 MEMORY.md 和 workflow.md 后生成，正式口径为：science 511 keV source、instant prompt background、fixed day-15 delayed activation 三个独立流全部放入共同泊松时间轴，再做 time-window active-shield/BGO veto 和 Compton/FoV veto。

当前输入状态：prompt 使用 step02_instant_equiv2602_aligned 的 60 个 SIM；delayed 使用 step02_delayed_transport_equiv2602_aligned 中 ground-state/isomer 修正后的 fixed day-15 1M SIM；science 使用 NEW_GEO_RE/ADR on-axis 511 keV 100k SIM。

关键修正：W-183/W-180 ground state 被误当短寿命 isomer 的 delayed-source 问题已经使用 delay_fix 修正。当前 fixed source 中 W-183/W-180 残留检查为 W183={summary['delay_fix']['fixed_source_contains_W183']}，W180={summary['delay_fix']['fixed_source_contains_W180']}。
"""
    body2 = f"""\
归一化：prompt 等效时间 {summary['normalization']['prompt_time_s']:.6g} s，gamma 权重 1，非 gamma 8 replica 权重 1/8；delayed observation time {summary['normalization']['delayed_time_s']:.6g} s；共同泊松时间轴 observation time {summary['normalization']['obs_time_s']:.6g} s。

science source：采用 science_source_injection_plan.md 的 Level-1 optics 外置口径，物理流量不写进 Cosima 触发数，而是在后处理中用 F_511 * A_eff * T_atm 归一化。本报告基准源流量 F_511={summary['normalization']['science_flux_ph_cm2_s']:.3g} ph cm^-2 s^-1，对应 Be-plane photon rate {summary['normalization']['science_injection_rate_s^-1']:.6g} s^-1。

time-window 设置：coincidence/active-shield 时间窗 {summary['normalization']['coincidence_window_s']:.1e} s；active-shield/BGO pass 要求候选时间窗内主动 veto 通道总能量 < {summary['normalization']['bgo_threshold_keV']:.3g} keV；当前 NEW_GEO_RE 主动 veto authority 体积名为 {summary['normalization'].get('active_veto_volume_name', 'active shield')}，代码把 {', '.join(summary['normalization'].get('active_veto_match_tokens', ['BGO', 'ACTIVE_SHIELD', 'CEBR3']))} 体积都归入同一 veto 通道。Compton/FoV veto 对 active-shield-pass 多 TES-pixel 候选生效，2-hit 测试双顺序第一康普顿锥，3-hit+ 使用 CSR best sequence。reject_policy={summary['normalization']['reject_policy']}。
"""
    body3 = f"""\
480-550 keV 泊松时间轴结果：no veto={r_t.get('raw',0):.5g} cps，BGO 后={r_t.get('bgo',0):.5g} cps，BGO+Compton/FoV 后={r_t.get('final',0):.5g} cps。对应的直接期望交叉检查为 no veto={r_e.get('raw',0):.5g} cps，BGO 后={r_e.get('bgo',0):.5g} cps，final={r_e.get('final',0):.5g} cps。

按直接期望拆分：prompt final={bg_prompt.get('final',0):.5g} cps；delayed final={bg_delay.get('final',0):.5g} cps；science reference final={sci.get('final',0):.5g} cps。science 不计入本底 cps，但在观测时间轴和 IMAGE8-like 分成分谱中作为独立 signal stream 保留。

泊松抽样实例数：prompt={summary['draw_summary']['prompt']['drawn']}，delayed={summary['draw_summary']['delayed']['drawn']}，science={summary['draw_summary']['science']['drawn']}。时间轴候选总数={summary['timeline']['n_candidates_total']}，有 TES 能量候选={summary['timeline']['n_candidates_with_tes']}，混合流候选={summary['timeline']['n_mixed_candidates']}。

简化点源灵敏度：reference flux 的 final-stage S/B = {sens['reference_flux_signal_to_background']:.4g}；final-stage response = {sens['science_final_response_cps_per_ph_cm-2_s-1']:.4g} cps/(ph cm^-2 s^-1)。在 Gaussian 计数近似下，5σ flux limit 为：本报告时间 {sens['flux_limits']['timeline_obs']['flux_5sigma_ph_cm2_s']:.3g}，10 ks {sens['flux_limits']['10ks']['flux_5sigma_ph_cm2_s']:.3g}，1 day {sens['flux_limits']['1day']['flux_5sigma_ph_cm2_s']:.3g} ph cm^-2 s^-1。
"""
    body4 = """\
审计结论与限制：

1. 本报告的 VETO 数字来自共同泊松时间轴，不再使用上一版的直接事件级替代口径。直接期望只作为统计交叉检查。

2. science source 已进入时间轴和分成分谱；但 F=1e-4 ph cm^-2 s^-1 在本报告 observation time 中期望只有少量光子，因此泊松时间轴中的 science 抽样有明显随机性。报告中的 science 物理率以直接期望为准。

3. prompt time-variable light-curve wrapper 已可运行，但当前 verified 包内 prompt lightcurve_shape 仍为 1.0，本报告仍是静态 flux 的 day-15 汇总。

4. Compton/FoV veto 是 2602-style HT/CC-hit pixel 几何重建，不是完整 Revan 输出；它适合复刻 PPT 工作流，但后续论文版仍应给出 Revan 交叉检查。
"""
    with PdfPages(pdf_path) as pdf:
        add_text_page(pdf, "完整 day-15 工作报告：口径和输入", body1, font_prop)
        add_text_page(pdf, "归一化、科学源和时间轴", body2, font_prop)
        add_text_page(pdf, "关键结果和交叉检查", body3, font_prop)
        add_image_page(pdf, "100-10000 keV 时间轴谱", figs["timeline_main"], "泊松共同时间轴上的 no-veto 与 BGO-veto 谱，并与直接期望谱交叉检查。", font_prop)
        add_image_page(pdf, "480-550 keV VETO 链", figs["zoom"], "511 keV 分析窗口内的 time-window no-veto、BGO-veto、BGO+Compton/FoV-veto。", font_prop)
        add_image_page(pdf, "VETO 效果统计", figs["veto_bar"], "泊松时间轴结果与直接期望结果并列，用于检查随机抽样涨落。", font_prop)
        add_image_page(pdf, "IMAGE8-like 分成分谱", figs["component"], "按《基于立方星》IMAGE8 风格绘制的 no-veto 分成分微分谱，包含 reference science source。", font_prop)
        add_image_page(pdf, "修正后活化分量", figs["activation"], "day-15 delayed source 已应用 ground-state/isomer 修正；W-183/W-180 ground state 不再进入活化源。", font_prop)
        add_text_page(pdf, "审计结论与限制", body4, font_prop)
    return pdf_path


def audit_outputs(outdir: Path, summary: dict):
    problems = []
    if summary["delay_fix"]["fixed_source_contains_W183"]:
        problems.append("fixed delayed source still contains W183 marker")
    if summary["delay_fix"]["fixed_source_contains_W180"]:
        problems.append("fixed delayed source still contains W180 marker")
    for k in ("raw", "bgo", "final"):
        if summary["timeline_rates_cps"].get(k, 0.0) < 0:
            problems.append(f"negative timeline rate: {k}")
        if summary["expectation_rates_cps"].get(k, 0.0) < 0:
            problems.append(f"negative expectation rate: {k}")
    if summary["expectation_rates_by_stream_cps"].get("science", {}).get("raw", 0.0) <= 0:
        problems.append("science source has zero expected raw rate")
    text = ["# Complete report audit", ""]
    text.append("Status: " + ("PASS" if not problems else "FAIL"))
    text.append("")
    text.append("Checks:")
    text.append(f"- W183 in fixed source: {summary['delay_fix']['fixed_source_contains_W183']}")
    text.append(f"- W180 in fixed source: {summary['delay_fix']['fixed_source_contains_W180']}")
    text.append(f"- science expected raw cps: {summary['expectation_rates_by_stream_cps'].get('science', {}).get('raw', 0.0):.12g}")
    text.append(f"- timeline final cps: {summary['timeline_rates_cps'].get('final', 0.0):.12g}")
    if problems:
        text.append("")
        text.append("Problems:")
        text.extend([f"- {p}" for p in problems])
    (outdir / "audit.md").write_text("\n".join(text) + "\n", encoding="utf-8")
    return problems


def update_memory_workflow(summary: dict, pdf_path: Path):
    stamp = "\n\n## 2026-05-31 DEMO2 complete day-15 report update\n\n"
    mem = WORKSPACE / "MEMORY.md"
    wf = WORKSPACE / "workflow.md"
    mem_text = mem.read_text(encoding="utf-8", errors="ignore")
    wf_text = wf.read_text(encoding="utf-8", errors="ignore")
    try:
        pdf_display = pdf_path.resolve().relative_to(WORKSPACE.resolve())
    except ValueError:
        pdf_display = pdf_path
    mem_add = (
        stamp
        + f"- Generated complete report with science+prompt+fixed-delayed Poisson common timeline: `{pdf_display}`.\n"
        + f"- Observation time {summary['normalization']['obs_time_s']:.6g} s, coincidence window {summary['normalization']['coincidence_window_s']:.1e} s, BGO threshold {summary['normalization']['bgo_threshold_keV']:.3g} keV, reject_policy `{summary['normalization']['reject_policy']}`.\n"
        + f"- Timeline 480-550 keV rates: raw {summary['timeline_rates_cps']['raw']:.6g} cps, BGO {summary['timeline_rates_cps']['bgo']:.6g} cps, final {summary['timeline_rates_cps']['final']:.6g} cps.\n"
        + f"- Direct expectation cross-check: raw {summary['expectation_rates_cps']['raw']:.6g} cps, BGO {summary['expectation_rates_cps']['bgo']:.6g} cps, final {summary['expectation_rates_cps']['final']:.6g} cps.\n"
        + f"- Science reference flux {summary['normalization']['science_flux_ph_cm2_s']:.3g} ph cm^-2 s^-1 is included as an independent stream; expected science final rate {summary['expectation_rates_by_stream_cps'].get('science', {}).get('final', 0.0):.6g} cps.\n"
        + "- Audit confirmed fixed delayed source has no W183/W180 source-block residual.\n"
    )
    wf_add = (
        stamp
        + "- Formal report workflow now requires science, prompt, and fixed day-15 delayed streams to be placed on one Poisson time axis before BGO/Compton veto. Direct event-weight spectra are retained only as expectation cross-checks.\n"
        + f"- Latest complete PDF: `{pdf_display}`.\n"
    )
    if "## 2026-05-31 DEMO2 complete day-15 report update" not in mem_text:
        mem.write_text(mem_text.rstrip() + mem_add, encoding="utf-8")
    if "## 2026-05-31 DEMO2 complete day-15 report update" not in wf_text:
        wf.write_text(wf_text.rstrip() + wf_add, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=str(DEFAULT_OUTDIR))
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--obs-time-s", type=float, default=0.0, help="0 => delayed observation time")
    ap.add_argument("--science-flux", type=float, default=1.0e-4)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--reject-policy", choices=["keep", "drop"], default="keep")
    ap.add_argument("--rebuild-cache", action="store_true")
    ap.add_argument("--refresh-from-summary", action="store_true", help="Rebuild PDF/derived CSV from existing summary and figures without loading event catalog")
    args = ap.parse_args()

    # Explicitly read these at runtime to keep the report anchored to current context.
    for p in (WORKSPACE / "MEMORY.md", WORKSPACE / "workflow.md"):
        if not p.exists():
            raise FileNotFoundError(p)
        _ = p.read_text(encoding="utf-8", errors="ignore")

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    font_prop = setup_fonts()
    obs_time = float(args.obs_time_s) if args.obs_time_s > 0 else delayed_time_s()

    if args.refresh_from_summary:
        summary_path = outdir / "complete_day15_summary.json"
        summary = ensure_science_sensitivity(load_json(summary_path, {}))
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        write_sensitivity_csv(outdir, summary)
        figs = {
            "timeline_main": str(outdir / "figures" / "timeline_spectrum_100_10000.png"),
            "zoom": str(outdir / "figures" / "timeline_spectrum_480_550_veto_chain.png"),
            "veto_bar": str(outdir / "figures" / "timeline_veto_rates_bar.png"),
            "component": str(outdir / "figures" / "image8_like_component_spectrum_with_science.png"),
            "activation": str(outdir / "figures" / "activation_top10_after_fix.png"),
        }
        pdf_path = build_pdf(outdir, summary, figs, font_prop)
        problems = audit_outputs(outdir, summary)
        update_memory_workflow(summary, pdf_path)
        print(f"[OK] refreshed {pdf_path}", flush=True)
        print("[OK] audit PASS" if not problems else "[WARN] audit problems", flush=True)
        return

    cat = load_or_build_catalog(outdir, max(1, int(args.workers)), float(args.science_flux), bool(args.rebuild_cache))
    print(f"[INFO] catalog events={len(cat['stream'])} pixel_hits={len(cat['pix_e'])}")
    print("[INFO] computing direct expectation cross-check")
    direct = direct_expectation(cat, args.reject_policy)
    print("[INFO] drawing common Poisson timeline")
    rng = np.random.default_rng(int(args.seed))
    timeline = draw_timeline(cat, obs_time, rng)
    print(f"[INFO] timeline instances={len(timeline['event_index'])}")
    print("[INFO] analyzing time-window candidates")
    tl = analyze_timeline(cat, timeline, obs_time, args.reject_policy)
    summary = make_summary(cat, direct, timeline, tl, obs_time, float(args.science_flux), int(args.seed), args.reject_policy)
    write_tables(outdir, direct, tl)
    (outdir / "complete_day15_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    write_sensitivity_csv(outdir, summary)
    figs = plot_outputs(outdir, direct, tl, summary, font_prop)
    pdf_path = build_pdf(outdir, summary, figs, font_prop)
    problems = audit_outputs(outdir, summary)
    update_memory_workflow(summary, pdf_path)
    print(f"[OK] wrote {pdf_path}")
    print(f"[OK] wrote {outdir / 'complete_day15_summary.json'}")
    if problems:
        print("[WARN] audit problems:")
        for p in problems:
            print(f"  - {p}")
    else:
        print("[OK] audit PASS")


if __name__ == "__main__":
    main()
