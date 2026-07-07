#!/usr/bin/env python3
"""Build Mass_model_511 smoke-level detector closure artifacts.

This script consumes transport products under
`runs/Mass_model_511_nearfield_migration_20260701/`, reuses the current Step05
detector-response parser, and writes only package-local closure artifacts.  It
does not modify source authorities, Step05 authority outputs, or the older
nearfield engineering package.
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
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "engineering/Mass_model_511_nearfield_migration_20260701"
RUN_ROOT = ROOT / "runs/Mass_model_511_nearfield_migration_20260701"
CLOSURE_DIR = PKG / "06_smoke_closure"
STEP05_PATH = ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"
STEP09_BRIDGE_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5"
    / "step09_optics_bridge_summary.json"
)
BASE_SIGNAL_SOURCE = (
    ROOT
    / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/run_configs"
    / "Opticsim_laue_f10m_a1_v3p5_centerfinger.source"
)
COSIMA = "/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima"

BASELINE_BRANCH = "baseline_detector"
CANDIDATE_BRANCH = "candidate_Mass_model_511"
BRANCHES = (BASELINE_BRANCH, CANDIDATE_BRANCH)
GEOMETRIES = {
    BASELINE_BRANCH: (
        "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/"
        "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
    ),
    CANDIDATE_BRANCH: (
        "outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy/"
        "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
    ),
}

MODES = ("instant", "buildup")
DELAYED_STAGES = ("S0", "S1")
QUANTITATIVE_DELAYED_STAGE = "S1"
ACTIVE_VETO_THRESHOLD_KEV = 50.0
REJECT_POLICY = "keep"
SIGNAL_TRIGGERS = 37194
SIGNAL_SEED = 260616

BANDS = {
    "all_50_8000": (50.0, 8000.0),
    "b100_300": (100.0, 300.0),
    "b300_480": (300.0, 480.0),
    "b480_550": (480.0, 550.0),
    "w2_510p58_511p42": (510.58, 511.42),
    "b550_800": (550.0, 800.0),
    "b800_1500": (800.0, 1500.0),
    "b1500_3000": (1500.0, 3000.0),
    "b3000_8000": (3000.0, 8000.0),
}
SIGNAL_BANDS = {
    "all_50_8000": BANDS["all_50_8000"],
    "b480_550": BANDS["b480_550"],
    "w2_510p58_511p42": BANDS["w2_510p58_511p42"],
}
STAGES = ("raw", "active_veto_pass", "side_compton_fov_pass")


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except Exception:
        return str(path)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def load_step05():
    spec = importlib.util.spec_from_file_location("mass_model_511_step05_base", STEP05_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {STEP05_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def merge_cached_catalogs(adr, cache_paths: list[str]) -> dict[str, Any]:
    merged = adr.empty_catalog()
    for cache_path in sorted(cache_paths):
        with Path(cache_path).open("rb") as handle:
            adr.merge_one_catalog_into(merged, pickle.load(handle))
    return adr.catalog_to_arrays(merged)


def prompt_run_dir(branch: str, mode: str) -> Path:
    return RUN_ROOT / f"step02_{mode}_{branch}_smoke"


def prompt_outdir(branch: str, mode: str) -> Path:
    return CLOSURE_DIR / "prompt_step05" / branch / mode


def delayed_run_dir(branch: str, stage: str) -> Path:
    return RUN_ROOT / f"step02_delayed_transport_{branch}_{stage}_smoke"


def delayed_exact_dir(branch: str, stage: str) -> Path:
    return RUN_ROOT / f"step02_delay_exactpos_{branch}_{stage}_smoke"


def delayed_outdir(branch: str, stage: str) -> Path:
    return CLOSURE_DIR / "delayed_step05" / branch / stage


def signal_run_dir(branch: str) -> Path:
    return RUN_ROOT / f"step09_focus_{branch}_Mass_model_511_smoke"


def signal_source_path(branch: str) -> Path:
    return signal_run_dir(branch) / f"Opticsim_laue_f10m_a1_{branch}_Mass_model_511_signal_smoke.source"


def signal_prefix(branch: str) -> Path:
    return signal_run_dir(branch) / f"Opticsim_laue_f10m_a1_{branch}_Mass_model_511_signal_smoke"


def signal_sim_path(branch: str) -> Path:
    return Path(f"{signal_prefix(branch)}.inc1.id1.sim.gz")


def empty_metric() -> dict[str, Any]:
    return {"events": 0, "rate_s-1": 0.0, "sum_w2_s-2": 0.0, "sigma_s-1": 0.0}


def add_metric(metric: dict[str, Any], weights: np.ndarray) -> None:
    if len(weights) == 0:
        return
    metric["events"] += int(len(weights))
    metric["rate_s-1"] += float(np.sum(weights))
    metric["sum_w2_s-2"] += float(np.sum(weights * weights))


def finalize_metric(metric: dict[str, Any]) -> dict[str, Any]:
    out = dict(metric)
    out["sigma_s-1"] = math.sqrt(max(float(out["sum_w2_s-2"]), 0.0))
    return out


def compare_metric(base: dict[str, Any], cand: dict[str, Any]) -> dict[str, Any]:
    b = float(base["rate_s-1"])
    c = float(cand["rate_s-1"])
    sb = float(base["sigma_s-1"])
    sc = float(cand["sigma_s-1"])
    sd = math.sqrt(sb * sb + sc * sc)
    delta = c - b
    rel_delta = delta / b if b > 0.0 else None
    rel_sigma = sd / b if b > 0.0 else None
    return {
        "baseline_events": int(base["events"]),
        "candidate_events": int(cand["events"]),
        "baseline_rate_s-1": b,
        "candidate_rate_s-1": c,
        "baseline_sigma_s-1": sb,
        "candidate_sigma_s-1": sc,
        "absolute_delta_s-1": delta,
        "delta_sigma_s-1_independent": sd,
        "z_delta_independent": delta / sd if sd > 0.0 else None,
        "relative_delta": rel_delta,
        "relative_delta_sigma_independent": rel_sigma,
        "relative_delta_ci95_lo": rel_delta - 1.96 * rel_sigma if rel_delta is not None and rel_sigma is not None else None,
        "relative_delta_ci95_hi": rel_delta + 1.96 * rel_sigma if rel_delta is not None and rel_sigma is not None else None,
    }


def compare_fraction(base: dict[str, Any], cand: dict[str, Any]) -> dict[str, Any]:
    b = float(base["acceptance_fraction"])
    c = float(cand["acceptance_fraction"])
    sb = float(base["poisson_sigma_fraction"])
    sc = float(cand["poisson_sigma_fraction"])
    sd = math.sqrt(sb * sb + sc * sc)
    delta = c - b
    rel_delta = delta / b if b > 0.0 else None
    rel_sigma = sd / b if b > 0.0 else None
    return {
        "baseline_events": int(base["events"]),
        "candidate_events": int(cand["events"]),
        "baseline_acceptance_fraction": b,
        "candidate_acceptance_fraction": c,
        "absolute_delta_fraction": delta,
        "delta_sigma_fraction_independent": sd,
        "z_delta_independent": delta / sd if sd > 0.0 else None,
        "relative_delta": rel_delta,
        "relative_delta_sigma_independent": rel_sigma,
        "relative_delta_ci95_lo": rel_delta - 1.96 * rel_sigma if rel_delta is not None and rel_sigma is not None else None,
        "relative_delta_ci95_hi": rel_delta + 1.96 * rel_sigma if rel_delta is not None and rel_sigma is not None else None,
    }


def configure_prompt_step05(step05, prompt_dir: Path, outdir: Path) -> None:
    step05.OUT = outdir
    step05.PROMPT_DIR = prompt_dir
    step05.PROMPT_NORM = prompt_dir / "normalization.json"
    step05.STEP09_SUMMARY = STEP09_BRIDGE_SUMMARY
    step05.ACTIVE_VETO_THRESHOLD_KEV = ACTIVE_VETO_THRESHOLD_KEV
    step05.ACTIVE_VETO_MATCH_DESCRIPTION = "Mass_model_511 smoke closure: v3p5 active veto tokens, 50 keV"
    step05._PROMPT_NORMALIZATION_AUDIT = None


def build_prompt_catalog(step05, adr, branch: str, mode: str, workers: int, rebuild: bool) -> dict[str, Any]:
    prompt_dir = prompt_run_dir(branch, mode)
    if not (prompt_dir / "normalization.json").exists():
        raise FileNotFoundError(prompt_dir / "normalization.json")
    sim_files = sorted(prompt_dir.glob("*.sim.gz"))
    if not sim_files:
        raise FileNotFoundError(f"no prompt SIM files in {prompt_dir}")
    local_out = prompt_outdir(branch, mode)
    work = local_out / "work"
    file_cache = work / "file_catalogs"
    file_cache.mkdir(parents=True, exist_ok=True)
    catalog_cache = work / "event_catalog.pkl"
    if catalog_cache.exists() and not rebuild:
        with catalog_cache.open("rb") as handle:
            return pickle.load(handle)

    configure_prompt_step05(step05, prompt_dir, local_out)
    local_out.mkdir(parents=True, exist_ok=True)
    audit = step05.prompt_normalization_audit()
    step05.write_prompt_normalization_audit(audit)
    if audit.get("problems"):
        raise RuntimeError(f"prompt normalization audit failed for {branch}/{mode}: {audit['problems']}")
    step05.configure_parser(adr)
    tasks = [(str(path), "prompt", 1.0, str(file_cache), rebuild) for path in sim_files]
    print(f"[INFO] parse prompt {branch}/{mode}: files={len(tasks)} workers={workers}", flush=True)
    if workers > 1:
        with mp.get_context("fork").Pool(processes=workers) as pool:
            cache_paths = []
            for i, cache_path in enumerate(pool.imap_unordered(adr.parse_sim_catalog_to_cache, tasks, chunksize=1), 1):
                cache_paths.append(cache_path)
                if i % 8 == 0 or i == len(tasks):
                    print(f"[INFO] cached prompt {branch}/{mode}: {i}/{len(tasks)}", flush=True)
    else:
        cache_paths = []
        for i, task in enumerate(tasks, 1):
            cache_paths.append(adr.parse_sim_catalog_to_cache(task))
            if i % 8 == 0 or i == len(tasks):
                print(f"[INFO] cached prompt {branch}/{mode}: {i}/{len(tasks)}", flush=True)
    cat = merge_cached_catalogs(adr, cache_paths)
    with catalog_cache.open("wb") as handle:
        pickle.dump(cat, handle, protocol=pickle.HIGHEST_PROTOCOL)
    return cat


def summarize_rate_catalog(step05, cat: dict[str, Any], bands: dict[str, tuple[float, float]]) -> dict[str, Any]:
    disk = step05.side_entry_disk()
    summary: dict[str, Any] = {
        "catalog": {
            "events_kept": int(len(cat["stream"])),
            "pixel_hits_kept": int(len(cat["pix_e"])),
            "generated_events_seen": int(cat.get("n_generated_events_seen", 0)),
            "tes_events": int(np.sum(cat["tes_total_keV"] > 0.0)),
            "active_veto_events": int(np.sum(cat["bgo_total_keV"] >= ACTIVE_VETO_THRESHOLD_KEV)),
            "rate_sum_s-1": float(np.sum(cat["rate_hz"])),
        },
        "bands": {},
    }
    for band, (emin, emax) in bands.items():
        mask_energy = (cat["tes_total_keV"] >= emin) & (cat["tes_total_keV"] < emax)
        mask_active = mask_energy & (cat["bgo_total_keV"] < ACTIVE_VETO_THRESHOLD_KEV)
        final_keep = np.zeros(len(cat["stream"]), dtype=bool)
        class_counts = Counter()
        for idx in np.flatnonzero(mask_active):
            keep, cls = step05.side_keep_from_hits(step05.event_hits(cat, int(idx)), disk, REJECT_POLICY)
            class_counts[cls] += 1
            if keep:
                final_keep[idx] = True
        masks = {
            "raw": mask_energy,
            "active_veto_pass": mask_active,
            "side_compton_fov_pass": final_keep,
        }
        band_payload: dict[str, Any] = {
            "window_keV": [emin, emax],
            "total": {},
            "by_tag": {},
            "side_compton_class_counts_after_active_veto": dict(sorted(class_counts.items())),
        }
        for stage, mask in masks.items():
            metric = empty_metric()
            add_metric(metric, cat["rate_hz"][mask])
            band_payload["total"][stage] = finalize_metric(metric)
            by_tag: dict[str, Any] = {}
            for tag in sorted(set(str(x) for x in cat["tag"][mask])):
                tag_mask = mask & (cat["tag"] == tag)
                row = empty_metric()
                add_metric(row, cat["rate_hz"][tag_mask])
                by_tag[tag] = finalize_metric(row)
            band_payload["by_tag"][stage] = by_tag
        summary["bands"][band] = band_payload
    return summary


def load_delayed_manifest(branch: str) -> dict[str, Any] | None:
    branch_manifest = PKG / "03_detector_transport" / f"delayed_transport_campaign_manifest_{branch}.json"
    if branch_manifest.exists():
        return read_json(branch_manifest)
    aggregate = PKG / "03_detector_transport/delayed_transport_campaign_manifest.json"
    if not aggregate.exists():
        return None
    data = read_json(aggregate)
    if data.get("branch") == branch:
        return data
    payloads = data.get("branch_payloads")
    if isinstance(payloads, dict) and branch in payloads:
        return payloads[branch]
    return None


def delayed_transport_record(branch: str, stage: str) -> dict[str, Any]:
    manifest = load_delayed_manifest(branch)
    if not manifest:
        raise FileNotFoundError(f"missing delayed transport manifest for {branch}")
    for row in manifest.get("transports", []):
        if row.get("branch") == branch and row.get("stage") == stage:
            return row
    raise KeyError(f"missing delayed transport record for {branch}/{stage}")


def delayed_sim_path(branch: str, stage: str) -> Path:
    record = delayed_transport_record(branch, stage)
    path = ROOT / str(record.get("transport_sim", ""))
    if path.exists():
        return path
    sims = sorted(delayed_run_dir(branch, stage).glob("*.sim.gz"))
    if len(sims) == 1:
        return sims[0]
    raise FileNotFoundError(f"cannot resolve delayed SIM for {branch}/{stage}")


def build_delayed_catalog(step05, adr, branch: str, stage: str, rebuild: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    record = delayed_transport_record(branch, stage)
    te_s = float(record["TE_s"])
    sim = delayed_sim_path(branch, stage)
    local_out = delayed_outdir(branch, stage)
    file_cache = local_out / "work" / "file_catalogs"
    file_cache.mkdir(parents=True, exist_ok=True)
    catalog_cache = local_out / "work" / "event_catalog.pkl"
    meta_cache = local_out / "work" / "event_catalog_meta.json"
    if catalog_cache.exists() and meta_cache.exists() and not rebuild:
        meta = read_json(meta_cache)
        if meta.get("TE_s") == te_s and meta.get("sim") == rel(sim):
            with catalog_cache.open("rb") as handle:
                return pickle.load(handle), record

    step05.delayed_time_s = lambda: te_s
    step05.STEP09_SUMMARY = STEP09_BRIDGE_SUMMARY
    step05.ACTIVE_VETO_THRESHOLD_KEV = ACTIVE_VETO_THRESHOLD_KEV
    step05.ACTIVE_VETO_MATCH_DESCRIPTION = "Mass_model_511 smoke closure: delayed active veto, 50 keV"
    step05.configure_parser(adr)
    print(f"[INFO] parse delayed {branch}/{stage}: {rel(sim)}", flush=True)
    cache_path = adr.parse_sim_catalog_to_cache((str(sim), "delayed", 1.0, str(file_cache), rebuild))
    cat = merge_cached_catalogs(adr, [cache_path])
    with catalog_cache.open("wb") as handle:
        pickle.dump(cat, handle, protocol=pickle.HIGHEST_PROTOCOL)
    write_json(meta_cache, {"sim": rel(sim), "TE_s": te_s, "generated_at_utc": now_utc()})
    return cat, record


def patch_signal_source_text(text: str, branch: str) -> str:
    old_run = "Opticsim_laue_f10m_a1_fix5_fullstat_v2_exactpos_m50000_s260613"
    new_run = f"Opticsim_laue_f10m_a1_{branch}_Mass_model_511_signal_smoke"
    geometry = GEOMETRIES[branch]
    out: list[str] = []
    counts = {"Geometry": 0, "Seed": 0, "Run": 0, "FileName": 0, "Triggers": 0}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# Auto-generated"):
            out.append("# Harness-local Mass_model_511 signal smoke source copy.")
        elif stripped.startswith("# Replays"):
            out.append(f"# Replays the current f10m A1 Step09 EventList through {branch}.")
        elif stripped.startswith("Geometry "):
            out.append(f"Geometry {geometry}")
            counts["Geometry"] += 1
        elif stripped.startswith("Seed "):
            out.append(f"Seed {SIGNAL_SEED}")
            counts["Seed"] += 1
        elif stripped == f"Run {old_run}":
            out.append(f"Run {new_run}")
            counts["Run"] += 1
        elif stripped.startswith(f"{old_run}.FileName "):
            out.append(f"{new_run}.FileName {rel(signal_prefix(branch))}")
            counts["FileName"] += 1
        elif stripped.startswith(f"{old_run}.Triggers "):
            out.append(f"{new_run}.Triggers {SIGNAL_TRIGGERS}")
            counts["Triggers"] += 1
        elif stripped.startswith(f"{old_run}.Source "):
            out.append(f"{new_run}.Source {new_run}_EventList")
        elif stripped.startswith(f"{old_run}_EventList.EventList "):
            out.append(f"{new_run}_EventList.EventList {stripped.split(None, 1)[1]}")
        else:
            out.append(line.replace(old_run, new_run))
    bad = {key: value for key, value in counts.items() if value != 1}
    if bad:
        raise ValueError(f"unexpected signal source line counts for {branch}: {bad}")
    return "\n".join(out) + "\n"


def prepare_signal_sources() -> list[dict[str, Any]]:
    base_text = BASE_SIGNAL_SOURCE.read_text(encoding="utf-8", errors="replace")
    records = []
    for branch in BRANCHES:
        rd = signal_run_dir(branch)
        rd.mkdir(parents=True, exist_ok=True)
        source = signal_source_path(branch)
        source.write_text(patch_signal_source_text(base_text, branch), encoding="utf-8")
        records.append(
            {
                "branch": branch,
                "source": rel(source),
                "geometry": GEOMETRIES[branch],
                "triggers": SIGNAL_TRIGGERS,
                "seed": SIGNAL_SEED,
            }
        )
    return records


def run_signal_cosima(branch: str, cosima: str, force: bool) -> dict[str, Any]:
    sim = signal_sim_path(branch)
    log = signal_run_dir(branch) / f"cosima_{branch}_signal.log"
    if sim.exists() and not force:
        return {"branch": branch, "status": "EXISTS", "sim": rel(sim), "log": rel(log), "returncode": 0}
    with log.open("w", encoding="utf-8") as handle:
        proc = subprocess.run([cosima, str(signal_source_path(branch).resolve())], cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT)
    return {
        "branch": branch,
        "status": "PASS" if proc.returncode == 0 and sim.exists() else "FAIL",
        "returncode": proc.returncode,
        "sim": rel(sim),
        "log": rel(log),
        "size_bytes": sim.stat().st_size if sim.exists() else 0,
    }


def signal_header(path: Path) -> dict[str, Any]:
    out: dict[str, Any] = {"exists": path.exists(), "SE": 0, "ID": 0, "TS": 0, "TE_s": None, "geometry": None}
    if not path.exists():
        return out
    with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            if raw.startswith("Geometry"):
                parts = raw.split(None, 1)
                out["geometry"] = parts[1].strip() if len(parts) == 2 else ""
            elif raw.startswith("SE"):
                out["SE"] += 1
            elif raw.startswith("ID "):
                out["ID"] += 1
            elif raw.startswith("TS"):
                out["TS"] += 1
            elif raw.startswith("TE "):
                parts = raw.split()
                if len(parts) > 1:
                    try:
                        out["TE_s"] = float(parts[1])
                    except ValueError:
                        pass
    return out


def configure_signal_adr(step05, adr) -> None:
    adr.is_active_veto_volume = step05.is_v3p5_active_veto_volume

    def event_rate_for_mode(path: str, mode: str, science_flux: float):
        return "science", "focused_eventlist_unit_rate", 1.0 / SIGNAL_TRIGGERS

    adr.event_rate_for_mode = event_rate_for_mode


def build_signal_catalog(step05, adr, branch: str, rebuild: bool) -> dict[str, Any]:
    sim = signal_sim_path(branch)
    if not sim.exists():
        raise FileNotFoundError(sim)
    local_out = CLOSURE_DIR / "signal_step05" / branch
    file_cache = local_out / "work" / "file_catalogs"
    file_cache.mkdir(parents=True, exist_ok=True)
    catalog_cache = local_out / "work" / "event_catalog.pkl"
    if catalog_cache.exists() and not rebuild:
        with catalog_cache.open("rb") as handle:
            return pickle.load(handle)
    configure_signal_adr(step05, adr)
    print(f"[INFO] parse signal {branch}: {rel(sim)}", flush=True)
    cache_path = adr.parse_sim_catalog_to_cache((str(sim), "science", 1.0, str(file_cache), rebuild))
    with Path(cache_path).open("rb") as handle:
        cat = adr.catalog_to_arrays(pickle.load(handle))
    with catalog_cache.open("wb") as handle:
        pickle.dump(cat, handle, protocol=pickle.HIGHEST_PROTOCOL)
    return cat


def summarize_signal(step05, cat: dict[str, Any]) -> dict[str, Any]:
    step05.STEP09_SUMMARY = STEP09_BRIDGE_SUMMARY
    step05.ACTIVE_VETO_THRESHOLD_KEV = ACTIVE_VETO_THRESHOLD_KEV
    disk = step05.side_entry_disk()
    summary: dict[str, Any] = {
        "catalog": {
            "events_kept": int(len(cat["stream"])),
            "pixel_hits_kept": int(len(cat["pix_e"])),
            "generated_events_seen": int(cat.get("n_generated_events_seen", 0)),
            "tes_events": int(np.sum(cat["tes_total_keV"] > 0.0)),
        },
        "bands": {},
    }
    for band, (emin, emax) in SIGNAL_BANDS.items():
        mask_energy = (cat["tes_total_keV"] >= emin) & (cat["tes_total_keV"] < emax)
        mask_active = mask_energy & (cat["bgo_total_keV"] < ACTIVE_VETO_THRESHOLD_KEV)
        final_keep = np.zeros(len(cat["stream"]), dtype=bool)
        class_counts = Counter()
        for idx in np.flatnonzero(mask_active):
            keep, cls = step05.side_keep_from_hits(step05.event_hits(cat, int(idx)), disk, REJECT_POLICY)
            class_counts[cls] += 1
            if keep:
                final_keep[idx] = True
        masks = {"raw": mask_energy, "active_veto_pass": mask_active, "side_compton_fov_pass": final_keep}
        stages: dict[str, Any] = {}
        for stage, mask in masks.items():
            events = int(np.sum(mask))
            stages[stage] = {
                "events": events,
                "acceptance_fraction": events / SIGNAL_TRIGGERS,
                "poisson_sigma_fraction": math.sqrt(events) / SIGNAL_TRIGGERS if events > 0 else 0.0,
                "unit_eventlist_rate_s-1": float(np.sum(cat["rate_hz"][mask])),
            }
        summary["bands"][band] = {
            "window_keV": [emin, emax],
            "stages": stages,
            "side_compton_class_counts_after_active_veto": dict(sorted(class_counts.items())),
        }
    return summary


def total_metric(prompt: dict[str, Any], delayed: dict[str, Any]) -> dict[str, Any]:
    return finalize_metric(
        {
            "events": int(prompt["events"]) + int(delayed["events"]),
            "rate_s-1": float(prompt["rate_s-1"]) + float(delayed["rate_s-1"]),
            "sum_w2_s-2": float(prompt["sum_w2_s-2"]) + float(delayed["sum_w2_s-2"]),
        }
    )


def sensitivity_proxy(signal: dict[str, Any], background: dict[str, Any]) -> dict[str, Any]:
    bkg = float(background["rate_s-1"])
    acc = float(signal["acceptance_fraction"])
    sigma_acc = float(signal["poisson_sigma_fraction"])
    value = acc / math.sqrt(bkg) if bkg > 0 else None
    sigma = sigma_acc / math.sqrt(bkg) if bkg > 0 else None
    return {
        "signal_acceptance_fraction": acc,
        "signal_acceptance_sigma_fraction": sigma_acc,
        "background_rate_s-1": bkg,
        "background_sigma_s-1": float(background["sigma_s-1"]),
        "acceptance_over_sqrt_background": value,
        "acceptance_over_sqrt_background_sigma_signal_only": sigma,
    }


def compare_sensitivity_proxy(base: dict[str, Any], cand: dict[str, Any]) -> dict[str, Any]:
    b = base["acceptance_over_sqrt_background"]
    c = cand["acceptance_over_sqrt_background"]
    if b is None or c is None:
        return {"baseline_proxy": b, "candidate_proxy": c, "relative_delta": None}
    delta = c - b
    return {
        "baseline_proxy": b,
        "candidate_proxy": c,
        "absolute_delta": delta,
        "relative_delta": delta / b if b > 0 else None,
        "note": "Smoke proxy only: acceptance/sqrt(background rate), not a regenerated Step08 mission significance.",
    }


def build_markdown(payload: dict[str, Any]) -> str:
    key = payload["key_metrics"]
    lines = [
        "# Mass_model_511 Smoke Closure Conclusion",
        "",
        f"generated_at_utc: `{payload['generated_at_utc']}`",
        f"status: `{payload['status']}`",
        "",
        "## Conclusion",
        "",
        (
            "The Mass_model_511 package is closed at the smoke-matrix detector-response level: "
            "baseline and candidate prompt/buildup, delayed S1, and focused-signal smoke products "
            "were propagated through the Step05 detector-response selections."
            if payload["status"] == "PASS_SMOKE_MATRIX_CLOSURE"
            else "The Mass_model_511 closure is incomplete; see missing requirements below."
        ),
        "",
        "This is not a full-stat or manuscript-release closure. The conclusion is restricted to the "
        "smoke matrix and a Step08-style sensitivity proxy; publication claims still require the "
        "full-stat campaign and downstream mission-axis regeneration.",
        "",
        "## Key W2 Rows",
        "",
        "| quantity | baseline | candidate | rel delta | 95% CI / note |",
        "| --- | ---: | ---: | ---: | --- |",
    ]

    def rate_row(name: str, row: dict[str, Any]) -> None:
        rel_delta = "NA" if row.get("relative_delta") is None else f"{float(row['relative_delta']):.4g}"
        ci = "NA"
        if row.get("relative_delta_ci95_lo") is not None:
            ci = f"[{float(row['relative_delta_ci95_lo']):.4g}, {float(row['relative_delta_ci95_hi']):.4g}]"
        lines.append(
            f"| {name} | {float(row['baseline_rate_s-1']):.6g} cps | "
            f"{float(row['candidate_rate_s-1']):.6g} cps | {rel_delta} | {ci} |"
        )

    for name in (
        "prompt instant final W2",
        "prompt buildup final W2",
        "delayed S1 final W2",
        "total instant+S1 final W2",
        "total buildup+S1 final W2",
    ):
        if name in key:
            rate_row(name, key[name])
    if "signal final W2 acceptance" in key:
        row = key["signal final W2 acceptance"]
        rel_delta = "NA" if row.get("relative_delta") is None else f"{float(row['relative_delta']):.4g}"
        ci = "NA"
        if row.get("relative_delta_ci95_lo") is not None:
            ci = f"[{float(row['relative_delta_ci95_lo']):.4g}, {float(row['relative_delta_ci95_hi']):.4g}]"
        lines.append(
            f"| signal final W2 acceptance | {float(row['baseline_acceptance_fraction']):.6g} | "
            f"{float(row['candidate_acceptance_fraction']):.6g} | {rel_delta} | {ci} |"
        )
    if "sensitivity proxy instant+S1" in key:
        row = key["sensitivity proxy instant+S1"]
        rel_delta = "NA" if row.get("relative_delta") is None else f"{float(row['relative_delta']):.4g}"
        lines.append(
            f"| sensitivity proxy instant+S1 | {float(row['baseline_proxy']):.6g} | "
            f"{float(row['candidate_proxy']):.6g} | {rel_delta} | smoke proxy |"
        )

    lines.extend(
        [
            "",
            "## Scope And Boundary",
            "",
            "- Geometry/source authority was not edited during closure.",
            "- Old `engineering/nearfield_mass_impact_20260625/` outputs were not overwritten.",
            "- Active veto threshold: `50 keV`; side-entry Compton/FoV policy: `keep` rejects.",
            "- Quantitative delayed row uses `S1` (`1,000,000` delayed triggers in the smoke matrix).",
            "- Full-stat/background publication closure remains `NOT_RUN` in this package.",
            "",
            "## Artifacts",
            "",
            f"- JSON: `{payload['artifacts']['closure_json']}`",
            f"- prompt comparison CSV: `{payload['artifacts']['prompt_comparison_csv']}`",
            f"- delayed comparison CSV: `{payload['artifacts']['delayed_comparison_csv']}`",
            f"- signal comparison CSV: `{payload['artifacts']['signal_comparison_csv']}`",
            f"- key metrics CSV: `{payload['artifacts']['key_metrics_csv']}`",
        ]
    )
    if payload["missing_requirements"]:
        lines.extend(["", "## Missing Requirements", ""])
        for item in payload["missing_requirements"]:
            lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def main() -> int:
    default_cosima = shutil.which("cosima") or COSIMA
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--rebuild-cache", action="store_true")
    ap.add_argument("--prepare-signal", action="store_true")
    ap.add_argument("--run-signal", action="store_true")
    ap.add_argument("--signal-only", action="store_true")
    ap.add_argument("--force-signal", action="store_true")
    ap.add_argument("--cosima", default=default_cosima)
    args = ap.parse_args()

    CLOSURE_DIR.mkdir(parents=True, exist_ok=True)
    signal_sources = prepare_signal_sources() if (args.prepare_signal or args.run_signal) else []
    signal_runs: list[dict[str, Any]] = []
    if args.run_signal:
        for branch in BRANCHES:
            signal_runs.append(run_signal_cosima(branch, args.cosima, args.force_signal))
    if args.signal_only:
        manifest = {
            "document_type": "mass_model_511_focused_signal_smoke_transport",
            "generated_at_utc": now_utc(),
            "status": "PASS_SIGNAL_TRANSPORT"
            if signal_runs and all(row.get("status") in {"PASS", "EXISTS"} for row in signal_runs)
            else "PREPARED_OR_INCOMPLETE_SIGNAL_TRANSPORT",
            "source_records": signal_sources,
            "run_records": signal_runs,
            "headers": {branch: signal_header(signal_sim_path(branch)) for branch in BRANCHES},
            "source_authority_edited": False,
            "old_nearfield_engineering_edited": False,
        }
        write_json(CLOSURE_DIR / "signal_transport_manifest.json", manifest)
        print(json.dumps({"status": manifest["status"], "manifest": rel(CLOSURE_DIR / "signal_transport_manifest.json")}, indent=2))
        return 0 if str(manifest["status"]).startswith("PASS") else 2
    signal_manifest = CLOSURE_DIR / "signal_transport_manifest.json"
    if signal_manifest.exists():
        manifest = read_json(signal_manifest)
        if not signal_sources:
            signal_sources = list(manifest.get("source_records", []))
        if not signal_runs:
            signal_runs = list(manifest.get("run_records", []))

    step05 = load_step05()
    step05.STEP09_SUMMARY = STEP09_BRIDGE_SUMMARY
    adr = step05.load_adr_module()
    adr.is_active_veto_volume = step05.is_v3p5_active_veto_volume

    missing: list[str] = []
    prompt_summaries: dict[str, Any] = {}
    prompt_rows: list[dict[str, Any]] = []
    for mode in MODES:
        branch_ready = True
        for branch in BRANCHES:
            try:
                cat = build_prompt_catalog(step05, adr, branch, mode, max(1, args.workers), args.rebuild_cache)
                summary = summarize_rate_catalog(step05, cat, BANDS)
                prompt_summaries[f"{branch}/{mode}"] = summary
                write_json(prompt_outdir(branch, mode) / "prompt_step05_summary.json", summary)
            except Exception as exc:
                branch_ready = False
                missing.append(f"prompt {branch}/{mode}: {exc}")
        if branch_ready:
            base = prompt_summaries[f"{BASELINE_BRANCH}/{mode}"]
            cand = prompt_summaries[f"{CANDIDATE_BRANCH}/{mode}"]
            for band in BANDS:
                for stage in STAGES:
                    row = {"mode": mode, "band": band, "stage": stage}
                    row.update(compare_metric(base["bands"][band]["total"][stage], cand["bands"][band]["total"][stage]))
                    prompt_rows.append(row)

    delayed_summaries: dict[str, Any] = {}
    delayed_meta: dict[str, Any] = {}
    delayed_rows: list[dict[str, Any]] = []
    for stage in DELAYED_STAGES:
        branch_ready = True
        for branch in BRANCHES:
            try:
                cat, meta = build_delayed_catalog(step05, adr, branch, stage, args.rebuild_cache)
                summary = summarize_rate_catalog(step05, cat, BANDS)
                delayed_summaries[f"{branch}/{stage}"] = summary
                delayed_meta[f"{branch}/{stage}"] = meta
                write_json(delayed_outdir(branch, stage) / "delayed_step05_summary.json", summary)
            except Exception as exc:
                branch_ready = False
                missing.append(f"delayed {branch}/{stage}: {exc}")
        if branch_ready:
            base = delayed_summaries[f"{BASELINE_BRANCH}/{stage}"]
            cand = delayed_summaries[f"{CANDIDATE_BRANCH}/{stage}"]
            for band in BANDS:
                for filter_stage in STAGES:
                    row = {"transport_stage": stage, "band": band, "filter_stage": filter_stage}
                    row.update(compare_metric(base["bands"][band]["total"][filter_stage], cand["bands"][band]["total"][filter_stage]))
                    delayed_rows.append(row)

    signal_summaries: dict[str, Any] = {}
    signal_rows: list[dict[str, Any]] = []
    for branch in BRANCHES:
        try:
            cat = build_signal_catalog(step05, adr, branch, args.rebuild_cache)
            summary = summarize_signal(step05, cat)
            signal_summaries[branch] = summary
            write_json(CLOSURE_DIR / "signal_step05" / branch / "signal_step05_summary.json", summary)
        except Exception as exc:
            missing.append(f"signal {branch}: {exc}")
    if set(signal_summaries) == set(BRANCHES):
        for band in SIGNAL_BANDS:
            for stage in STAGES:
                row = {"band": band, "stage": stage}
                row.update(
                    compare_fraction(
                        signal_summaries[BASELINE_BRANCH]["bands"][band]["stages"][stage],
                        signal_summaries[CANDIDATE_BRANCH]["bands"][band]["stages"][stage],
                    )
                )
                signal_rows.append(row)

    key_metrics: dict[str, Any] = {}

    def find_prompt(mode: str) -> dict[str, Any] | None:
        for row in prompt_rows:
            if row["mode"] == mode and row["band"] == "w2_510p58_511p42" and row["stage"] == "side_compton_fov_pass":
                return row
        return None

    def find_delayed() -> dict[str, Any] | None:
        for row in delayed_rows:
            if (
                row["transport_stage"] == QUANTITATIVE_DELAYED_STAGE
                and row["band"] == "w2_510p58_511p42"
                and row["filter_stage"] == "side_compton_fov_pass"
            ):
                return row
        return None

    prompt_instant = find_prompt("instant")
    prompt_buildup = find_prompt("buildup")
    delayed_s1 = find_delayed()
    if prompt_instant:
        key_metrics["prompt instant final W2"] = prompt_instant
    if prompt_buildup:
        key_metrics["prompt buildup final W2"] = prompt_buildup
    if delayed_s1:
        key_metrics["delayed S1 final W2"] = delayed_s1

    total_metrics_by_label: dict[str, dict[str, Any]] = {}
    if delayed_s1:
        for mode, prompt_row, label in (
            ("instant", prompt_instant, "total instant+S1 final W2"),
            ("buildup", prompt_buildup, "total buildup+S1 final W2"),
        ):
            if not prompt_row:
                continue
            base_total = total_metric(
                {
                    "events": prompt_row["baseline_events"],
                    "rate_s-1": prompt_row["baseline_rate_s-1"],
                    "sum_w2_s-2": prompt_row["baseline_sigma_s-1"] ** 2,
                },
                {
                    "events": delayed_s1["baseline_events"],
                    "rate_s-1": delayed_s1["baseline_rate_s-1"],
                    "sum_w2_s-2": delayed_s1["baseline_sigma_s-1"] ** 2,
                },
            )
            cand_total = total_metric(
                {
                    "events": prompt_row["candidate_events"],
                    "rate_s-1": prompt_row["candidate_rate_s-1"],
                    "sum_w2_s-2": prompt_row["candidate_sigma_s-1"] ** 2,
                },
                {
                    "events": delayed_s1["candidate_events"],
                    "rate_s-1": delayed_s1["candidate_rate_s-1"],
                    "sum_w2_s-2": delayed_s1["candidate_sigma_s-1"] ** 2,
                },
            )
            row = compare_metric(base_total, cand_total)
            key_metrics[label] = row
            total_metrics_by_label[label] = {"baseline": base_total, "candidate": cand_total}

    signal_w2 = None
    for row in signal_rows:
        if row["band"] == "w2_510p58_511p42" and row["stage"] == "side_compton_fov_pass":
            signal_w2 = row
            key_metrics["signal final W2 acceptance"] = row
            break

    if signal_w2 and "total instant+S1 final W2" in total_metrics_by_label:
        base_signal = signal_summaries[BASELINE_BRANCH]["bands"]["w2_510p58_511p42"]["stages"]["side_compton_fov_pass"]
        cand_signal = signal_summaries[CANDIDATE_BRANCH]["bands"]["w2_510p58_511p42"]["stages"]["side_compton_fov_pass"]
        key_metrics["sensitivity proxy instant+S1"] = compare_sensitivity_proxy(
            sensitivity_proxy(base_signal, total_metrics_by_label["total instant+S1 final W2"]["baseline"]),
            sensitivity_proxy(cand_signal, total_metrics_by_label["total instant+S1 final W2"]["candidate"]),
        )

    prompt_csv = CLOSURE_DIR / "prompt_rate_comparison.csv"
    delayed_csv = CLOSURE_DIR / "delayed_rate_comparison.csv"
    signal_csv = CLOSURE_DIR / "signal_acceptance_comparison.csv"
    key_csv = CLOSURE_DIR / "combined_key_metrics.csv"
    closure_json = CLOSURE_DIR / "mass_model_511_smoke_closure.json"
    conclusion_md = CLOSURE_DIR / "CONCLUSION.md"

    write_csv(prompt_csv, prompt_rows)
    write_csv(delayed_csv, delayed_rows)
    write_csv(signal_csv, signal_rows)
    key_rows = [{"quantity": key, **value} for key, value in key_metrics.items()]
    write_csv(key_csv, key_rows)

    required_keys = {
        "prompt instant final W2",
        "prompt buildup final W2",
        "delayed S1 final W2",
        "total instant+S1 final W2",
        "signal final W2 acceptance",
        "sensitivity proxy instant+S1",
    }
    for key in sorted(required_keys - set(key_metrics)):
        missing.append(f"key metric missing: {key}")
    status = "PASS_SMOKE_MATRIX_CLOSURE" if not missing else "INCOMPLETE_SMOKE_MATRIX_CLOSURE"

    payload = {
        "document_type": "mass_model_511_smoke_matrix_detector_closure",
        "generated_at_utc": now_utc(),
        "status": status,
        "claim_boundary": (
            "Smoke-matrix detector-response closure only. Not full-stat, not manuscript-release, "
            "and not a replacement for Step06-Step08 mission-axis regeneration."
        ),
        "fullstat_status": "NOT_RUN",
        "source_authority_edited": False,
        "old_nearfield_engineering_edited": False,
        "branches": list(BRANCHES),
        "geometries": GEOMETRIES,
        "active_veto_threshold_keV": ACTIVE_VETO_THRESHOLD_KEV,
        "reject_policy": REJECT_POLICY,
        "delayed_quantitative_stage": QUANTITATIVE_DELAYED_STAGE,
        "signal_source_records": signal_sources,
        "signal_run_records": signal_runs,
        "signal_headers": {branch: signal_header(signal_sim_path(branch)) for branch in BRANCHES},
        "prompt_summaries": prompt_summaries,
        "delayed_summaries": delayed_summaries,
        "delayed_transport_meta": delayed_meta,
        "signal_summaries": signal_summaries,
        "prompt_comparisons": prompt_rows,
        "delayed_comparisons": delayed_rows,
        "signal_comparisons": signal_rows,
        "key_metrics": key_metrics,
        "missing_requirements": missing,
        "artifacts": {
            "closure_json": rel(closure_json),
            "conclusion_md": rel(conclusion_md),
            "prompt_comparison_csv": rel(prompt_csv),
            "delayed_comparison_csv": rel(delayed_csv),
            "signal_comparison_csv": rel(signal_csv),
            "key_metrics_csv": rel(key_csv),
        },
    }
    write_json(closure_json, payload)
    conclusion_md.write_text(build_markdown(payload), encoding="utf-8")
    print(json.dumps({"status": status, "json": rel(closure_json), "conclusion": rel(conclusion_md)}, indent=2))
    return 0 if status == "PASS_SMOKE_MATRIX_CLOSURE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
