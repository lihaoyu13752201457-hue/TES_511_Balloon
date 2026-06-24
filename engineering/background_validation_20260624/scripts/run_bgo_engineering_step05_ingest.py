#!/usr/bin/env python3
"""Engineering-only Step05 ingest for isolated BGO staged runs.

This reuses the current Step05 parser/selection functions, but keeps all
outputs under engineering/background_validation_20260624.  It intentionally
does not use the legacy bgo_sample label because that label carries a 70 keV
veto threshold; HARNESS_20260624 fixes the authority at 50 keV and 1 us.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
import multiprocessing as mp
import pickle
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
STEP05_PATH = ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except Exception:
        return str(path)


def load_step05():
    spec = importlib.util.spec_from_file_location("bgo_engineering_step05_base", STEP05_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {STEP05_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def delayed_time_from_sim(sim_path: Path) -> float:
    last_ti = 0.0
    opener = gzip.open if sim_path.suffix == ".gz" else open
    with opener(sim_path, "rt", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if line.startswith("TI "):
                parts = line.split()
                if len(parts) >= 2:
                    last_ti = max(last_ti, float(parts[1]))
    if last_ti <= 0.0:
        raise ValueError(f"cannot determine delayed observation time from {sim_path}")
    return last_ti


def merge_cached_catalogs(adr, cache_paths: list[str]) -> dict[str, Any]:
    merged = adr.empty_catalog()
    for cp in sorted(cache_paths):
        with Path(cp).open("rb") as handle:
            adr.merge_one_catalog_into(merged, pickle.load(handle))
    return adr.catalog_to_arrays(merged)


def build_catalog(
    step05,
    adr,
    prompt_dir: Path,
    delayed_sim: Path,
    science_sim: Path | None,
    outdir: Path,
    workers: int,
    rebuild: bool,
) -> dict[str, Any]:
    work = outdir / "work"
    file_cache = work / "file_catalogs"
    file_cache.mkdir(parents=True, exist_ok=True)
    catalog_cache = work / "event_catalog.pkl"
    if catalog_cache.exists() and not rebuild:
        with catalog_cache.open("rb") as handle:
            return pickle.load(handle)

    prompt_files = sorted(prompt_dir.glob("*.sim.gz"))
    if not prompt_files:
        raise FileNotFoundError(f"no prompt sim files in {prompt_dir}")
    tasks = [(str(path), "prompt", 1.0, str(file_cache), rebuild) for path in prompt_files]
    if workers > 1:
        with mp.get_context("fork").Pool(processes=workers) as pool:
            prompt_cache_paths = list(pool.imap_unordered(adr.parse_sim_catalog_to_cache, tasks, chunksize=1))
    else:
        prompt_cache_paths = [adr.parse_sim_catalog_to_cache(task) for task in tasks]

    delayed_cache = adr.parse_sim_catalog_to_cache((str(delayed_sim), "delayed", 1.0, str(file_cache), rebuild))
    cache_paths = prompt_cache_paths + [delayed_cache]
    if science_sim is not None:
        science_cache = adr.parse_sim_catalog_to_cache((str(science_sim), "science", 1.0, str(file_cache), rebuild))
        cache_paths.append(science_cache)
    cat = merge_cached_catalogs(adr, cache_paths)
    with catalog_cache.open("wb") as handle:
        pickle.dump(cat, handle, protocol=pickle.HIGHEST_PROTOCOL)
    return cat


def write_rates_csv(path: Path, windows: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "window",
        "stream",
        "raw_events",
        "active_veto_pass_events",
        "side_compton_fov_pass_events",
        "raw_rate_s-1",
        "active_veto_pass_rate_s-1",
        "side_compton_fov_pass_rate_s-1",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for window, payload in windows.items():
            for stream, row in payload["by_stream"].items():
                out = {"window": window, "stream": stream}
                for key in fields:
                    if key not in out:
                        out[key] = row.get(key, "")
                writer.writerow(out)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-dir", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--delayed-sim", type=Path, required=True)
    parser.add_argument("--fixed-source", type=Path, required=True)
    parser.add_argument("--science-sim", type=Path)
    parser.add_argument("--step09-summary", type=Path)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--rebuild-cache", action="store_true")
    args = parser.parse_args()

    prompt_dir = args.stage_dir / "instant"
    prompt_norm = prompt_dir / "normalization.json"
    if not prompt_norm.exists():
        raise FileNotFoundError(prompt_norm)
    if not args.delayed_sim.exists():
        raise FileNotFoundError(args.delayed_sim)
    if args.science_sim is not None and not args.science_sim.exists():
        raise FileNotFoundError(args.science_sim)
    if args.science_sim is not None and args.step09_summary is None:
        raise SystemExit("--step09-summary is required when --science-sim is provided")
    if args.step09_summary is not None and not args.step09_summary.exists():
        raise FileNotFoundError(args.step09_summary)

    step05 = load_step05()
    step05.OUT = args.outdir
    step05.PROMPT_DIR = prompt_dir
    step05.PROMPT_NORM = prompt_norm
    step05.DELAYED_SIM = args.delayed_sim
    step05.FIXED_SOURCE = args.fixed_source
    step05.ACTIVE_VETO_THRESHOLD_KEV = 50.0
    step05.ACTIVE_VETO_MATCH_DESCRIPTION = "HARNESS_20260624 BGO engineering ingest: CsI_/BGO active-shield volume names, 50 keV veto"
    step05.F10M_A1_AEFF = ROOT / "stepwise_maintenance/step04_opticsim/optics_aeff_authority_f10m_a1.json"
    step05.SCIENCE_RATE_LEDGER = ROOT / "old/config/science_511_onaxis_source/metadata/science_rate_ledger.csv"
    step05.BOUNDARY_CLOSURE_SUMMARY = (
        ROOT / "old/reports/v3p5_boundary_closure_fullstat_v2_exactpos_m50000_s260613_20260613/v3p5_boundary_closure_summary.json"
    )
    if args.science_sim is not None:
        step05.SCIENCE_SIM = args.science_sim
        step05.STEP09_SUMMARY = args.step09_summary
    else:
        step05.STEP09_SUMMARY = (
            ROOT
            / "stepwise_maintenance/step09_optics_bridge/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/step09_focus_summary.json"
        )
    delayed_te = delayed_time_from_sim(args.delayed_sim)
    step05.delayed_time_s = lambda: delayed_te

    args.outdir.mkdir(parents=True, exist_ok=True)
    prompt_audit = step05.prompt_normalization_audit()
    step05.write_prompt_normalization_audit(prompt_audit)
    if prompt_audit["problems"]:
        raise SystemExit("Prompt normalization audit failed: " + "; ".join(prompt_audit["problems"]))

    adr = step05.load_adr_module()
    step05.configure_parser(adr)
    cat = build_catalog(
        step05,
        adr,
        prompt_dir,
        args.delayed_sim,
        args.science_sim,
        args.outdir,
        max(1, args.workers),
        args.rebuild_cache,
    )
    disk = step05.side_entry_disk()
    reject_policy = "keep"
    windows = {
        name: step05.summarize_window(cat, *bounds, disk=disk, reject_policy=reject_policy)
        for name, bounds in step05.WINDOWS.items()
    }
    science_norm = None
    if args.science_sim is not None:
        science_norm = step05.load_science_physical_normalization()
        step05.add_physical_reference_to_windows(windows, science_norm)
    rng = np.random.default_rng(step05.RNG_SEED)
    timeline_draw = step05.draw_timeline(cat, delayed_te, rng)
    timeline = step05.analyze_timeline(cat, timeline_draw, delayed_te, disk, reject_policy)

    summary = {
        "status": "PASS_BGO_ENGINEERING_STEP05_INGEST",
        "label": args.label,
        "claim_level": "BGO engineering ingest; no manuscript-authority CsI/BGO material conclusion without completion audit",
        "inputs": {
            "prompt_dir": rel(prompt_dir),
            "prompt_files": len(sorted(prompt_dir.glob("*.sim.gz"))),
            "prompt_dat_files": len(sorted(prompt_dir.glob("*.dat.inc1.dat"))),
            "delayed_sim": rel(args.delayed_sim),
            "fixed_source": rel(args.fixed_source),
            "science_sim": rel(args.science_sim) if args.science_sim is not None else None,
            "step09_summary": rel(args.step09_summary) if args.step09_summary is not None else None,
            "science_stream": "included" if args.science_sim is not None else "not_run_in_this_ingest",
        },
        "normalization": {
            "prompt_time_s": step05.prompt_time_s(),
            "prompt_rate_rule": "per-tag event rate = 1 / sum(TT_s for prompt dat files with that tag)",
            "delayed_time_s": delayed_te,
            "active_veto_threshold_keV": 50.0,
            "coincidence_window_s": step05.COINCIDENCE_WINDOW_S,
            "reject_policy": reject_policy,
            "science_unit_injection_rate_s-1": 1.0 if args.science_sim is not None else None,
            "prompt_normalization_audit_json": rel(args.outdir / "prompt_normalization_audit.json"),
        },
        "science_physical_normalization": science_norm,
        "catalog": {
            "events_kept": int(len(cat["stream"])),
            "pixel_hits_kept": int(len(cat["pix_e"])),
            "by_stream_events": {stream: int(np.sum(cat["stream"] == stream)) for stream in ("prompt", "delayed", "science")},
            "by_stream_tes_events": {stream: int(np.sum((cat["stream"] == stream) & (cat["tes_total_keV"] > 0))) for stream in ("prompt", "delayed", "science")},
        },
        "windows": windows,
        "timeline": timeline,
        "timeline_draw_summary": timeline_draw["draw_summary"],
    }
    (args.outdir / "bgo_engineering_step05_ingest_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_rates_csv(args.outdir / "bgo_engineering_step05_ingest_rates.csv", windows)
    print(f"[OK] wrote {args.outdir / 'bgo_engineering_step05_ingest_summary.json'}")
    print(f"[OK] wrote {args.outdir / 'bgo_engineering_step05_ingest_rates.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
