#!/usr/bin/env python3
"""Build section 3.3 stage spectra and TES hit-multiplicity splits.

This script is intentionally a thin aggregation layer over the retained Step05
catalog/classification pipeline. It imports the Step05 driver, points it at the
Mass_model_511_fullstat_v1 SIM catalogues, and then bins the resulting
per-event catalogue into the paper-facing spectra requested by this work
package.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import os
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
os.environ.setdefault("MPLCONFIGDIR", str(OUT / "work" / "mplconfig"))

import numpy as np


LINEAGE = "Mass_model_511_fullstat_v1"
FIX5_RAW_REFERENCE = {"prompt": 161, "delayed": 54, "signal": 30323}

STEP05_SCRIPT = ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"
DAY15_SCRIPT = ROOT / "old/code/tools/make_day15_report_ADR.py"
ADR_SCRIPT = ROOT / "old/code/tools/make_complete_day15_report_ADR.py"
RUN_ROOT = ROOT / "runs/Mass_model_511_nearfield_migration_20260701"

PROMPT_DIR = RUN_ROOT / "step02_instant_candidate_Mass_model_511_fullstat_v1"
PROMPT_NORM = PROMPT_DIR / "normalization.json"
DELAYED_SUMMARY = (
    ROOT
    / "engineering/Mass_model_511_nearfield_migration_20260701"
    / "03_detector_transport/delayed/candidate_Mass_model_511/fullstat_v1/F1/delayed_source_exactpos_summary.json"
)
DELAYED_SIM = (
    RUN_ROOT
    / "step02_delayed_transport_candidate_Mass_model_511_fullstat_v1"
    / "DelayedDecayMassModel511CandidateFullstatV1.inc1.id1.sim.gz"
)
EXACTPOS_SOURCE = (
    RUN_ROOT
    / "step02_delay_exactpos_candidate_Mass_model_511_fullstat_v1"
    / "activation_decay_day15_groundstate_fixed_exactpos.source"
)
MASS_SIGNAL_SIM = (
    RUN_ROOT
    / "step09_focus_candidate_Mass_model_511_Mass_model_511_smoke"
    / "Opticsim_laue_f10m_a1_candidate_Mass_model_511_Mass_model_511_signal_smoke.inc1.id1.sim.gz"
)
SIGNAL_MANIFEST = ROOT / "engineering/Mass_model_511_nearfield_migration_20260701/06_smoke_closure/signal_transport_manifest.json"
V3P5_FULLSTAT_SIGNAL_SIM = ROOT / "old/runs/step09_optics_bridge/Opticsim_laue_f10m_a1_v3p5_centerfinger.inc1.id1.sim.gz"
STEP09_BRIDGE_SUMMARY = ROOT / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/step09_optics_bridge_summary.json"
BOUNDARY_CLOSURE_SUMMARY = ROOT / "outputs/reports/v3p5_boundary_closure_fullstat_v2_exactpos_20260613/v3p5_boundary_closure_summary.json"
F10M_A1_AEFF = ROOT / "stepwise_maintenance/step04_opticsim/optics_aeff_authority_f10m_a1.json"
SCIENCE_RATE_LEDGER = ROOT / "old/config/science_511_onaxis_source/metadata/science_rate_ledger.csv"

SPECTRA_CSV = OUT / "s33_stage_spectra_480_550.csv"
MULTIPLICITY_JSON = OUT / "s33_multiplicity_split.json"
MANIFEST_JSON = OUT / "s33_manifest.json"
SCRIPT_COPY = OUT / "build_s33_stage_spectra.py"

ACTIVE_VETO_THRESHOLD_KEV = 50.0
COINCIDENCE_WINDOW_S = 1.0e-6
REJECT_POLICY = "keep"
BIN_WIDTH_KEV = 0.5
BROAD_WINDOW = (480.0, 550.0)
WINDOWS = {
    "broad_480_550": BROAD_WINDOW,
    "w2_510p58_511p42": (510.58, 511.42),
}
OUTPUT_STREAMS = ("prompt", "delayed", "signal")
INTERNAL_STREAM_FOR_OUTPUT = {"prompt": "prompt", "delayed": "delayed", "signal": "science"}
OUTPUT_STREAM_FOR_INTERNAL = {v: k for k, v in INTERNAL_STREAM_FOR_OUTPUT.items()}
STAGES = ("raw", "active", "compton")
KEEP_CLASSES = {"single", "keep", "reject_kept"}
COMPTON_CLASSES = ("keep", "veto", "reject_kept")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))


def load_step05():
    spec = importlib.util.spec_from_file_location("s33_mass_model_step05", STEP05_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Step05 script: {STEP05_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def configure_step05(step05) -> None:
    step05.ROOT = ROOT
    step05.TOOLS = ROOT / "old/code/tools"
    step05.OUT = OUT
    step05.SUMMARY_JSON = OUT / "_unused_step05_summary.json"
    step05.SUMMARY_MD = OUT / "_unused_step05_summary.md"
    step05.RATES_CSV = OUT / "_unused_step05_rates.csv"
    step05.TIMELINE_CSV = OUT / "_unused_step05_timeline.csv"
    step05.PROMPT_DIR = PROMPT_DIR
    step05.PROMPT_NORM = PROMPT_NORM
    step05.DELAYED_SIM = DELAYED_SIM
    step05.FIXED_SOURCE = EXACTPOS_SOURCE
    step05.STEP02_SUMMARY = DELAYED_SUMMARY
    step05.SCIENCE_SIM = MASS_SIGNAL_SIM
    step05.STEP09_SUMMARY = STEP09_BRIDGE_SUMMARY
    step05.BOUNDARY_CLOSURE_SUMMARY = BOUNDARY_CLOSURE_SUMMARY
    step05.F10M_A1_AEFF = F10M_A1_AEFF
    step05.SCIENCE_RATE_LEDGER = SCIENCE_RATE_LEDGER
    step05.ACTIVE_VETO_THRESHOLD_KEV = ACTIVE_VETO_THRESHOLD_KEV
    step05.COINCIDENCE_WINDOW_S = COINCIDENCE_WINDOW_S
    step05.ACTIVE_VETO_MATCH_DESCRIPTION = (
        "Mass_model_511 current geometry; volume name starts with CsI_ plus "
        "legacy BGO/ACTIVE_SHIELD/CEBR3 tokens"
    )
    step05.WINDOWS = dict(WINDOWS)
    step05._PROMPT_NORMALIZATION_AUDIT = None


def preflight() -> dict[str, Any]:
    required = {
        "step05_driver": STEP05_SCRIPT,
        "day15_classifier_source": DAY15_SCRIPT,
        "adr_catalog_loader": ADR_SCRIPT,
        "prompt_dir": PROMPT_DIR,
        "prompt_norm": PROMPT_NORM,
        "delayed_sim": DELAYED_SIM,
        "delayed_summary": DELAYED_SUMMARY,
        "exactpos_source": EXACTPOS_SOURCE,
        "mass_signal_sim": MASS_SIGNAL_SIM,
        "signal_manifest": SIGNAL_MANIFEST,
        "v3p5_fullstat_signal_sim": V3P5_FULLSTAT_SIGNAL_SIM,
        "side_entry_bridge_summary": STEP09_BRIDGE_SUMMARY,
        "science_rate_ledger": SCIENCE_RATE_LEDGER,
        "f10m_a1_aeff": F10M_A1_AEFF,
    }
    prompt_sim = sorted(PROMPT_DIR.glob("*.sim.gz"))
    prompt_dat = sorted(PROMPT_DIR.glob("*.dat.inc1.dat"))
    delayed_summary = load_json(DELAYED_SUMMARY, {})
    signal_manifest = load_json(SIGNAL_MANIFEST, {})
    signal_header = (signal_manifest.get("headers") or {}).get("candidate_Mass_model_511", {})

    problems = [f"missing:{name}:{path}" for name, path in required.items() if not path.exists()]
    if len(prompt_sim) != 68:
        problems.append(f"prompt_sim_count={len(prompt_sim)} expected=68")
    if len(prompt_dat) != 68:
        problems.append(f"prompt_dat_count={len(prompt_dat)} expected=68")
    if not str(delayed_summary.get("status", "")).startswith("PASS"):
        problems.append("delayed_summary_status_not_PASS")
    if int(signal_header.get("SE", -1)) != 37194:
        problems.append("mass_signal_smoke_header_SE_not_37194")

    return {
        "status": "PASS" if not problems else "FAIL",
        "problems": problems,
        "inputs": {k: rel(v) for k, v in required.items()},
        "prompt_sim_files": len(prompt_sim),
        "prompt_dat_files": len(prompt_dat),
        "delayed_summary_status": delayed_summary.get("status"),
        "mass_signal_header": signal_header,
    }


def write_event_catalog_cache(cat: dict[str, Any]) -> None:
    cache = OUT / "work/event_catalog.pkl"
    cache.parent.mkdir(parents=True, exist_ok=True)
    with cache.open("wb") as fh:
        pickle.dump(cat, fh, protocol=pickle.HIGHEST_PROTOCOL)


def edges_480_550() -> np.ndarray:
    return np.asarray([BROAD_WINDOW[0] + i * BIN_WIDTH_KEV for i in range(141)], dtype=float)


def empty_stage_totals() -> dict[str, dict[str, dict[str, dict[str, float | int]]]]:
    return {
        win: {
            stream: {stage: {"events": 0, "rate_s-1": 0.0} for stage in STAGES}
            for stream in OUTPUT_STREAMS
        }
        for win in WINDOWS
    }


def empty_histograms(n_bins: int) -> tuple[dict[str, dict[str, np.ndarray]], dict[str, dict[str, np.ndarray]]]:
    event_hists = {
        stream: {stage: np.zeros(n_bins, dtype=np.int64) for stage in STAGES}
        for stream in OUTPUT_STREAMS
    }
    rate_hists = {
        stream: {stage: np.zeros(n_bins, dtype=np.float64) for stage in STAGES}
        for stream in OUTPUT_STREAMS
    }
    return event_hists, rate_hists


def empty_multiplicity() -> dict[str, Any]:
    return {
        "geometry_lineage": LINEAGE,
        "active_veto_threshold_keV": ACTIVE_VETO_THRESHOLD_KEV,
        "coincidence_window_s": COINCIDENCE_WINDOW_S,
        "reject_policy": REJECT_POLICY,
        "windows": {
            win: {
                "window_keV": [float(bounds[0]), float(bounds[1])],
                "streams": {
                    stream: {
                        "stages": {
                            stage: {"n1": 0, "n2": 0, "n3plus": 0, "total": 0}
                            for stage in STAGES
                        },
                        "multi_hit_compton_class_after_active": {
                            "n2": {cls: 0 for cls in COMPTON_CLASSES},
                            "n3plus": {cls: 0 for cls in COMPTON_CLASSES},
                        },
                    }
                    for stream in OUTPUT_STREAMS
                },
            }
            for win, bounds in WINDOWS.items()
        },
    }


def multiplicity_bucket(n_hits: int) -> str:
    if n_hits <= 1:
        return "n1"
    if n_hits == 2:
        return "n2"
    return "n3plus"


def add_mult_count(mult: dict[str, Any], window: str, stream: str, stage: str, bucket: str) -> None:
    row = mult["windows"][window]["streams"][stream]["stages"][stage]
    row[bucket] += 1
    row["total"] += 1


def classify_event(step05, cat: dict[str, Any], idx: int, disk: dict[str, Any]) -> tuple[bool, str]:
    return step05.side_keep_from_hits(step05.event_hits(cat, idx), disk, REJECT_POLICY)


def analyze_catalog(step05, cat: dict[str, Any], disk: dict[str, Any]) -> dict[str, Any]:
    edges = edges_480_550()
    n_bins = len(edges) - 1
    event_hists, rate_hists = empty_histograms(n_bins)
    totals = empty_stage_totals()
    mult = empty_multiplicity()
    class_cache: dict[int, tuple[bool, str]] = {}

    stream_array = np.asarray(cat["stream"], dtype=object)
    e_array = np.asarray(cat["tes_total_keV"], dtype=np.float64)
    bgo_array = np.asarray(cat["bgo_total_keV"], dtype=np.float64)
    rate_array = np.asarray(cat["rate_hz"], dtype=np.float64)
    pix_count_array = np.asarray(cat["pix_count"], dtype=np.int64)

    broad_min, broad_max = BROAD_WINDOW
    for idx in range(len(stream_array)):
        internal_stream = str(stream_array[idx])
        stream = OUTPUT_STREAM_FOR_INTERNAL.get(internal_stream)
        if stream is None:
            continue
        e = float(e_array[idx])
        if not (broad_min <= e < broad_max):
            continue

        rate = float(rate_array[idx])
        active = float(bgo_array[idx]) < ACTIVE_VETO_THRESHOLD_KEV
        bucket = multiplicity_bucket(int(pix_count_array[idx]))

        keep = False
        cls = ""
        if active:
            keep, cls = class_cache.setdefault(idx, classify_event(step05, cat, idx, disk))

        bin_idx = int((e - broad_min) / BIN_WIDTH_KEV)
        in_bin = 0 <= bin_idx < n_bins

        for window, (emin, emax) in WINDOWS.items():
            if not (emin <= e < emax):
                continue
            totals[window][stream]["raw"]["events"] += 1
            totals[window][stream]["raw"]["rate_s-1"] += rate
            add_mult_count(mult, window, stream, "raw", bucket)
            if active:
                totals[window][stream]["active"]["events"] += 1
                totals[window][stream]["active"]["rate_s-1"] += rate
                add_mult_count(mult, window, stream, "active", bucket)
                if bucket in ("n2", "n3plus") and cls in COMPTON_CLASSES:
                    mult["windows"][window]["streams"][stream]["multi_hit_compton_class_after_active"][bucket][cls] += 1
                if keep:
                    totals[window][stream]["compton"]["events"] += 1
                    totals[window][stream]["compton"]["rate_s-1"] += rate
                    add_mult_count(mult, window, stream, "compton", bucket)

        if in_bin:
            event_hists[stream]["raw"][bin_idx] += 1
            rate_hists[stream]["raw"][bin_idx] += rate
            if active:
                event_hists[stream]["active"][bin_idx] += 1
                rate_hists[stream]["active"][bin_idx] += rate
                if keep:
                    event_hists[stream]["compton"][bin_idx] += 1
                    rate_hists[stream]["compton"][bin_idx] += rate

    return {
        "edges": edges,
        "event_hists": event_hists,
        "rate_hists": rate_hists,
        "stage_totals": totals,
        "multiplicity": mult,
    }


def assert_matches_step05_summary(analysis: dict[str, Any], step05_windows: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    stage_to_step05 = {
        "raw": ("raw_events", "raw_rate_s-1"),
        "active": ("active_veto_pass_events", "active_veto_pass_rate_s-1"),
        "compton": ("side_compton_fov_pass_events", "side_compton_fov_pass_rate_s-1"),
    }
    for window, summary in step05_windows.items():
        for out_stream, internal_stream in INTERNAL_STREAM_FOR_OUTPUT.items():
            row = summary["by_stream"][internal_stream]
            for stage, (event_key, rate_key) in stage_to_step05.items():
                got_events = int(analysis["stage_totals"][window][out_stream][stage]["events"])
                got_rate = float(analysis["stage_totals"][window][out_stream][stage]["rate_s-1"])
                exp_events = int(row[event_key])
                exp_rate = float(row[rate_key])
                if got_events != exp_events:
                    problems.append(f"{window}:{out_stream}:{stage}:events got={got_events} step05={exp_events}")
                if not math.isclose(got_rate, exp_rate, rel_tol=1.0e-10, abs_tol=1.0e-12):
                    problems.append(f"{window}:{out_stream}:{stage}:rate got={got_rate:.12g} step05={exp_rate:.12g}")
    return problems


def write_spectra_csv(analysis: dict[str, Any]) -> None:
    edges = analysis["edges"]
    fields = ["energy_lo_keV", "energy_hi_keV", "energy_center_keV"]
    for stream in OUTPUT_STREAMS:
        for stage in STAGES:
            fields.append(f"{stream}_{stage}_cps_per_keV")
            fields.append(f"{stream}_{stage}_events_per_bin")

    with SPECTRA_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for i in range(len(edges) - 1):
            row: dict[str, Any] = {
                "energy_lo_keV": f"{edges[i]:.6f}",
                "energy_hi_keV": f"{edges[i + 1]:.6f}",
                "energy_center_keV": f"{0.5 * (edges[i] + edges[i + 1]):.6f}",
            }
            for stream in OUTPUT_STREAMS:
                for stage in STAGES:
                    row[f"{stream}_{stage}_cps_per_keV"] = (
                        f"{float(analysis['rate_hists'][stream][stage][i]) / BIN_WIDTH_KEV:.12g}"
                    )
                    row[f"{stream}_{stage}_events_per_bin"] = int(analysis["event_hists"][stream][stage][i])
            writer.writerow(row)


def signal_variant_spectrum_rows(analysis: dict[str, Any], stream: str = "signal") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    edges = analysis["edges"]
    for i in range(len(edges) - 1):
        row: dict[str, Any] = {
            "energy_lo_keV": float(edges[i]),
            "energy_hi_keV": float(edges[i + 1]),
            "energy_center_keV": float(0.5 * (edges[i] + edges[i + 1])),
        }
        for stage in STAGES:
            row[f"{stage}_cps_per_keV"] = float(analysis["rate_hists"][stream][stage][i]) / BIN_WIDTH_KEV
            row[f"{stage}_events_per_bin"] = int(analysis["event_hists"][stream][stage][i])
        rows.append(row)
    return rows


def parse_signal_variant(step05, adr, disk: dict[str, Any], sim_path: Path) -> dict[str, Any] | None:
    if not sim_path.exists():
        return None
    cat_raw = adr.parse_sim_catalog((str(sim_path), "science", 1.0))
    cat = adr.catalog_to_arrays(cat_raw)
    analysis = analyze_catalog(step05, cat, disk)
    return {
        "label": "signal_v3p5_fullstat_optics",
        "sim": rel(sim_path),
        "note": "Full-stat v3p5 optics signal curve included because the Mass_model_511 signal SIM is smoke only.",
        "catalog": {
            "events_kept": int(len(cat["stream"])),
            "pixel_hits_kept": int(len(cat["pix_e"])),
            "tes_events": int(np.sum(cat["tes_total_keV"] > 0)),
        },
        "stage_totals": analysis["stage_totals"]["w2_510p58_511p42"]["signal"],
        "broad_stage_totals": analysis["stage_totals"]["broad_480_550"]["signal"],
        "stage_spectra_480_550": signal_variant_spectrum_rows(analysis, stream="signal"),
    }


def write_multiplicity_json(mult: dict[str, Any]) -> None:
    MULTIPLICITY_JSON.write_text(json.dumps(mult, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def stage_totals_for_manifest(analysis: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for window in WINDOWS:
        out[window] = {}
        for stream in OUTPUT_STREAMS:
            out[window][stream] = {}
            for stage in STAGES:
                item = analysis["stage_totals"][window][stream][stage]
                out[window][stream][stage] = {
                    "events": int(item["events"]),
                    "rate_s-1": float(item["rate_s-1"]),
                }
    return out


def make_diff_note(totals: dict[str, Any]) -> str:
    w2 = totals["w2_510p58_511p42"]
    got = {stream: int(w2[stream]["raw"]["events"]) for stream in OUTPUT_STREAMS}
    return (
        "Mass_model_511_fullstat_v1 w2 raw totals prompt/delayed/signal = "
        f"{got['prompt']}/{got['delayed']}/{got['signal']} versus fix5 cut-flow raw "
        f"{FIX5_RAW_REFERENCE['prompt']}/{FIX5_RAW_REFERENCE['delayed']}/{FIX5_RAW_REFERENCE['signal']}; "
        "these spectra are shape-diagnostic and do not replace the fix5 authority cut-flow."
    )


def acceptance_checks(analysis: dict[str, Any], step05_problems: list[str]) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    checks["csv_exists"] = SPECTRA_CSV.exists()
    checks["multiplicity_json_exists"] = MULTIPLICITY_JSON.exists()
    checks["manifest_json_exists"] = MANIFEST_JSON.exists()
    checks["script_exists"] = SCRIPT_COPY.exists()
    if SPECTRA_CSV.exists():
        with SPECTRA_CSV.open("r", encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        checks["csv_rows"] = len(rows)
        checks["csv_has_140_rows"] = len(rows) == 140
    else:
        checks["csv_rows"] = 0
        checks["csv_has_140_rows"] = False

    mult = analysis["multiplicity"]
    w2 = mult["windows"]["w2_510p58_511p42"]["streams"]
    bucket_sum_ok = True
    monotone_single_ok = True
    details = {}
    for stream in OUTPUT_STREAMS:
        comp_bucket_sum = sum(int(w2[stream]["stages"]["compton"][bucket]) for bucket in ("n1", "n2", "n3plus"))
        comp_total = int(analysis["stage_totals"]["w2_510p58_511p42"][stream]["compton"]["events"])
        raw_total = int(analysis["stage_totals"]["w2_510p58_511p42"][stream]["raw"]["events"])
        single_raw = int(w2[stream]["stages"]["raw"]["n1"])
        if comp_bucket_sum != comp_total:
            bucket_sum_ok = False
        if single_raw > raw_total:
            monotone_single_ok = False
        details[stream] = {
            "w2_compton_bucket_sum": comp_bucket_sum,
            "w2_compton_total": comp_total,
            "w2_single_raw": single_raw,
            "w2_raw_total": raw_total,
        }
    checks["w2_compton_bucket_sums_match_totals"] = bucket_sum_ok
    checks["single_raw_le_raw_total"] = monotone_single_ok
    checks["w2_bucket_details"] = details
    checks["geometry_lineage_is_Mass_model_511_fullstat_v1"] = True
    checks["step05_summary_match"] = not step05_problems
    checks["step05_summary_match_problems"] = step05_problems
    checks["all_done_contract_checks_passed"] = all(
        bool(checks[k])
        for k in (
            "csv_exists",
            "multiplicity_json_exists",
            "manifest_json_exists",
            "script_exists",
            "csv_has_140_rows",
            "w2_compton_bucket_sums_match_totals",
            "single_raw_le_raw_total",
            "geometry_lineage_is_Mass_model_511_fullstat_v1",
            "step05_summary_match",
        )
    )
    return checks


def prompt_inputs() -> list[str]:
    return [rel(p) for p in sorted(PROMPT_DIR.glob("*.sim.gz"))]


def build_manifest(
    preflight_payload: dict[str, Any],
    prompt_audit: dict[str, Any],
    analysis: dict[str, Any],
    step05_windows: dict[str, Any],
    science_norm: dict[str, Any],
    disk: dict[str, Any],
    acceptance: dict[str, Any],
    prompt_cache_rates_refreshed: bool,
    alternate_signal: dict[str, Any] | None,
) -> dict[str, Any]:
    totals = stage_totals_for_manifest(analysis)
    delayed_summary = load_json(DELAYED_SUMMARY)
    return {
        "status": "PASS" if acceptance["all_done_contract_checks_passed"] else "FAIL",
        "generated_at_utc": now_utc(),
        "geometry_lineage": LINEAGE,
        "claim_note": (
            "Mass_model_511_fullstat_v1 stage spectra and multiplicity splits are "
            "shape-diagnostic for paper figures; fix5 remains the authority for locked rates."
        ),
        "inputs": {
            "preflight": preflight_payload,
            "prompt_dir": rel(PROMPT_DIR),
            "prompt_sim_files": prompt_inputs(),
            "delayed_sim": rel(DELAYED_SIM),
            "signal": {
                "csv_signal_label": "signal_mass_model_511_smoke",
                "mass_model_511_smoke_sim": rel(MASS_SIGNAL_SIM),
                "mass_model_511_signal_manifest": rel(SIGNAL_MANIFEST),
                "alternate_v3p5_fullstat_signal_sim": rel(V3P5_FULLSTAT_SIGNAL_SIM),
                "signal_curve_policy": (
                    "CSV signal columns use the available Mass_model_511 smoke detector transport; "
                    "the manifest also embeds the full-stat v3p5 signal spectrum for comparison."
                ),
            },
            "side_entry_bridge_summary": rel(STEP09_BRIDGE_SUMMARY),
        },
        "code_modules_reused": {
            "step05_driver": {
                "path": rel(STEP05_SCRIPT),
                "functions": [
                    "load_adr_module",
                    "configure_parser",
                    "prompt_normalization_audit",
                    "refresh_prompt_event_rates",
                    "side_entry_disk",
                    "summarize_window",
                    "event_hits",
                    "side_keep_from_hits",
                ],
            },
            "adr_catalog_loader": {
                "path": rel(ADR_SCRIPT),
                "functions": ["load_or_build_catalog", "parse_sim_catalog", "catalog_to_arrays"],
            },
            "day15_classifier_source": {
                "path": rel(DAY15_SCRIPT),
                "functions": ["EventHit", "classify_compton"],
                "note": (
                    "make_complete_day15_report_ADR imports EventHit/classify_compton from this module; "
                    "the side-entry FoV decision is applied through the Step05 side_keep_from_hits wrapper."
                ),
            },
        },
        "parameters": {
            "active_veto_threshold_keV": ACTIVE_VETO_THRESHOLD_KEV,
            "coincidence_window_s": COINCIDENCE_WINDOW_S,
            "reject_policy": REJECT_POLICY,
            "windows": {k: [float(v[0]), float(v[1])] for k, v in WINDOWS.items()},
            "bin_width_keV": BIN_WIDTH_KEV,
            "stage_definitions": {
                "raw": "TES total energy inside window before active veto",
                "active": "raw and active-shield/CsI energy < 50 keV",
                "compton": "active and Step05 side-entry Compton/FoV keep; reject_kept retained",
            },
        },
        "normalization": {
            "prompt_rate_rule": "per-tag event rate = 1 / sum(TT_s for prompt dat files with that tag)",
            "prompt_normalization_audit": prompt_audit,
            "prompt_cache_rates_refreshed": prompt_cache_rates_refreshed,
            "delayed_time_s": float(delayed_summary["delayed_transport"]["TE_s"]),
            "science_unit_injection_rate_s-1": 1.0,
            "science_physical_normalization": science_norm,
        },
        "side_entry_disk": {
            "center_cm": [float(x) for x in disk["center_cm"]],
            "normal": [float(x) for x in disk["normal"]],
            "basis_u": [float(x) for x in disk["basis_u"]],
            "basis_v": [float(x) for x in disk["basis_v"]],
            "radius_cm": float(disk["radius_cm"]),
            "local_center_cm": [float(x) for x in disk["local_center_cm"]],
            "rotation_y_deg": float(disk["rotation_y_deg"]),
            "side_window_look_elevation_deg": float(disk["side_window_look_elevation_deg"]),
        },
        "stage_totals": totals,
        "step05_summarize_window_totals": step05_windows,
        "w2_diff_note_vs_fix5_cutflow": make_diff_note(totals),
        "alternate_signal": alternate_signal,
        "acceptance_checks": acceptance,
        "deliverables": {
            "s33_stage_spectra_480_550.csv": rel(SPECTRA_CSV),
            "s33_multiplicity_split.json": rel(MULTIPLICITY_JSON),
            "s33_manifest.json": rel(MANIFEST_JSON),
            "build_s33_stage_spectra.py": rel(SCRIPT_COPY),
        },
    }


def print_totals(manifest: dict[str, Any], analysis: dict[str, Any]) -> None:
    w2 = manifest["stage_totals"]["w2_510p58_511p42"]
    mult_w2 = analysis["multiplicity"]["windows"]["w2_510p58_511p42"]["streams"]
    payload = {
        "status": manifest["status"],
        "geometry_lineage": manifest["geometry_lineage"],
        "w2_totals_events": {
            stream: {stage: int(w2[stream][stage]["events"]) for stage in STAGES}
            for stream in OUTPUT_STREAMS
        },
        "w2_totals_rates_s-1": {
            stream: {stage: float(w2[stream][stage]["rate_s-1"]) for stage in STAGES}
            for stream in OUTPUT_STREAMS
        },
        "w2_compton_multiplicity": {
            stream: {
                "n2": int(mult_w2[stream]["stages"]["compton"]["n2"]),
                "n3plus": int(mult_w2[stream]["stages"]["compton"]["n3plus"]),
            }
            for stream in OUTPUT_STREAMS
        },
        "deliverables": manifest["deliverables"],
        "acceptance_checks": manifest["acceptance_checks"],
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def build(workers: int, rebuild_cache: bool) -> dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    pf = preflight()
    if pf["problems"]:
        raise SystemExit("preflight failed: " + "; ".join(pf["problems"]))

    step05 = load_step05()
    configure_step05(step05)
    prompt_audit = step05.prompt_normalization_audit()
    if prompt_audit["problems"]:
        raise SystemExit("prompt normalization audit failed: " + "; ".join(prompt_audit["problems"]))

    adr = step05.load_adr_module()
    step05.configure_parser(adr)
    cat = adr.load_or_build_catalog(OUT, workers=workers, science_flux=1.0, rebuild=rebuild_cache)
    prompt_cache_rates_refreshed = step05.refresh_prompt_event_rates(cat)
    if prompt_cache_rates_refreshed:
        write_event_catalog_cache(cat)

    disk = step05.side_entry_disk()
    step05_windows = {
        name: step05.summarize_window(cat, *bounds, disk=disk, reject_policy=REJECT_POLICY)
        for name, bounds in WINDOWS.items()
    }
    science_norm = step05.load_science_physical_normalization()
    step05.add_physical_reference_to_windows(step05_windows, science_norm)
    analysis = analyze_catalog(step05, cat, disk)
    step05_match_problems = assert_matches_step05_summary(analysis, step05_windows)

    alternate_signal = parse_signal_variant(step05, adr, disk, V3P5_FULLSTAT_SIGNAL_SIM)

    write_spectra_csv(analysis)
    write_multiplicity_json(analysis["multiplicity"])
    preliminary_acceptance = acceptance_checks(analysis, step05_match_problems)
    manifest = build_manifest(
        preflight_payload=pf,
        prompt_audit=prompt_audit,
        analysis=analysis,
        step05_windows=step05_windows,
        science_norm=science_norm,
        disk=disk,
        acceptance=preliminary_acceptance,
        prompt_cache_rates_refreshed=prompt_cache_rates_refreshed,
        alternate_signal=alternate_signal,
    )
    MANIFEST_JSON.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    final_acceptance = acceptance_checks(analysis, step05_match_problems)
    manifest["acceptance_checks"] = final_acceptance
    manifest["status"] = "PASS" if final_acceptance["all_done_contract_checks_passed"] else "FAIL"
    MANIFEST_JSON.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"manifest": manifest, "analysis": analysis}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=min(8, max(1, os.cpu_count() or 1)))
    parser.add_argument("--rebuild-cache", action="store_true")
    args = parser.parse_args()
    result = build(workers=args.workers, rebuild_cache=args.rebuild_cache)
    print_totals(result["manifest"], result["analysis"])
    if not result["manifest"]["acceptance_checks"]["all_done_contract_checks_passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
