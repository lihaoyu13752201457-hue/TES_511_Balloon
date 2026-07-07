#!/usr/bin/env python3
"""Run Step05 detector response for Mass_model_511 full-stat v1.

This wrapper reuses the established Step05 parser/selection functions while
pinning every input/output path to the Mass_model_511 engineering branch.  It
does not modify the old Step05 script and does not write into fix5 outputs.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "engineering/Mass_model_511_nearfield_migration_20260701"
STEP05_SCRIPT = ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"

LABEL = "Mass_model_511_fullstat_v1"
OUT = ROOT / "stepwise_maintenance/step05_veto_time_axis/outputs_Mass_model_511_fullstat_v1_l1"
SUMMARY_JSON = OUT / "step05_Mass_model_511_fullstat_v1_l1_response_summary.json"
SUMMARY_MD = OUT / "step05_Mass_model_511_fullstat_v1_l1_response_summary.md"
RATES_CSV = OUT / "step05_Mass_model_511_fullstat_v1_l1_rates.csv"
TIMELINE_CSV = OUT / "step05_Mass_model_511_fullstat_v1_l1_timeline_rates.csv"
RUN_ROOT = ROOT / "runs/Mass_model_511_nearfield_migration_20260701"

PROMPT_DIR = RUN_ROOT / "step02_instant_candidate_Mass_model_511_fullstat_v1"
PROMPT_NORM = PROMPT_DIR / "normalization.json"
DELAYED_DIR = RUN_ROOT / "step02_delayed_transport_candidate_Mass_model_511_fullstat_v1"
DELAYED_SIM = DELAYED_DIR / "DelayedDecayMassModel511CandidateFullstatV1.inc1.id1.sim.gz"
EXACTPOS_DIR = RUN_ROOT / "step02_delay_exactpos_candidate_Mass_model_511_fullstat_v1"
EXACTPOS_SOURCE = EXACTPOS_DIR / "activation_decay_day15_groundstate_fixed_exactpos.source"
DELAYED_SUMMARY = (
    PKG
    / "03_detector_transport/delayed/candidate_Mass_model_511/fullstat_v1/F1/delayed_source_exactpos_summary.json"
)
SIGNAL_SIM = (
    RUN_ROOT
    / "step09_focus_candidate_Mass_model_511_Mass_model_511_smoke"
    / "Opticsim_laue_f10m_a1_candidate_Mass_model_511_Mass_model_511_signal_smoke.inc1.id1.sim.gz"
)
SIGNAL_MANIFEST = PKG / "06_smoke_closure/signal_transport_manifest.json"
STEP09_BRIDGE_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/step09_optics_bridge_summary.json"
)
BOUNDARY_CLOSURE_SUMMARY = (
    ROOT
    / "outputs/reports/v3p5_boundary_closure_fullstat_v2_exactpos_20260613/v3p5_boundary_closure_summary.json"
)
MASS_GEOMETRY = (
    "outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_step05():
    spec = importlib.util.spec_from_file_location("mass_model_511_step05_l1", STEP05_SCRIPT)
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
    step05.SUMMARY_JSON = SUMMARY_JSON
    step05.SUMMARY_MD = SUMMARY_MD
    step05.RATES_CSV = RATES_CSV
    step05.TIMELINE_CSV = TIMELINE_CSV
    step05.PROMPT_DIR = PROMPT_DIR
    step05.PROMPT_NORM = PROMPT_NORM
    step05.DELAYED_SIM = DELAYED_SIM
    step05.FIXED_SOURCE = EXACTPOS_SOURCE
    step05.STEP02_SUMMARY = DELAYED_SUMMARY
    step05.SCIENCE_SIM = SIGNAL_SIM
    step05.STEP09_SUMMARY = STEP09_BRIDGE_SUMMARY
    step05.BOUNDARY_CLOSURE_SUMMARY = BOUNDARY_CLOSURE_SUMMARY
    step05.F10M_A1_AEFF = ROOT / "stepwise_maintenance/step04_opticsim/optics_aeff_authority_f10m_a1.json"
    step05.SCIENCE_RATE_LEDGER = ROOT / "old/config/science_511_onaxis_source/metadata/science_rate_ledger.csv"
    step05.ACTIVE_VETO_THRESHOLD_KEV = 50.0
    step05.ACTIVE_VETO_MATCH_DESCRIPTION = "Mass_model_511 current geometry; volume name starts with CsI_ plus legacy BGO/ACTIVE_SHIELD/CEBR3 tokens"
    step05._PROMPT_NORMALIZATION_AUDIT = None


def preflight(step05) -> dict[str, Any]:
    delayed_summary = load_json(DELAYED_SUMMARY) if DELAYED_SUMMARY.exists() else {}
    signal_manifest = load_json(SIGNAL_MANIFEST) if SIGNAL_MANIFEST.exists() else {}
    required = {
        "prompt_dir": PROMPT_DIR,
        "prompt_norm": PROMPT_NORM,
        "delayed_sim": DELAYED_SIM,
        "exactpos_source": EXACTPOS_SOURCE,
        "delayed_summary": DELAYED_SUMMARY,
        "signal_sim": SIGNAL_SIM,
        "signal_manifest": SIGNAL_MANIFEST,
        "bridge_summary_for_side_entry_disk": STEP09_BRIDGE_SUMMARY,
    }
    missing = [name for name, path in required.items() if not path.exists()]
    prompt_sim = sorted(PROMPT_DIR.glob("*.sim.gz"))
    prompt_dat = sorted(PROMPT_DIR.glob("*.dat.inc1.dat"))
    delayed_status = str(delayed_summary.get("status", ""))
    signal_header = (signal_manifest.get("headers") or {}).get("candidate_Mass_model_511", {})
    problems = list(missing)
    if len(prompt_sim) != 68:
        problems.append(f"prompt_sim_count={len(prompt_sim)}")
    if len(prompt_dat) != 68:
        problems.append(f"prompt_dat_count={len(prompt_dat)}")
    if not delayed_status.startswith("PASS"):
        problems.append(f"delayed_summary_status={delayed_status or 'MISSING'}")
    if signal_header.get("SE") != 37194 or MASS_GEOMETRY not in str(signal_header.get("geometry", "")):
        problems.append("signal_header_not_current_geometry_full_eventlist")
    return {
        "status": "PASS" if not problems else "FAIL",
        "problems": problems,
        "inputs": {name: rel(path) for name, path in required.items()},
        "prompt_sim_files": len(prompt_sim),
        "prompt_dat_files": len(prompt_dat),
        "delayed_summary_status": delayed_status,
        "signal_header": signal_header,
        "side_entry_bridge_reuse": (
            "The f10m A1 EventList/side-entry disk bridge is reused from the retained Step09 bridge summary; "
            "the detector transport SIM itself is the current Mass_model_511 geometry."
        ),
    }


def write_event_catalog_cache(cat: dict[str, Any]) -> None:
    cache = OUT / "work/event_catalog.pkl"
    cache.parent.mkdir(parents=True, exist_ok=True)
    with cache.open("wb") as fh:
        pickle.dump(cat, fh, protocol=pickle.HIGHEST_PROTOCOL)


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Step05 Mass_model_511 Full-Stat V1 L1 Detector Response",
        "",
        f"Status: `{payload['status']}`",
        "",
        "Claim level: current-geometry Mass_model_511 full-stat prompt, exact-position delayed, and focused EventList detector-response extraction. This is not a no-effect/replacement decision and does not replace Step06--Step08.",
        "",
        "Inputs:",
        f"- prompt: `{payload['inputs']['prompt_dir']}`",
        f"- delayed: `{payload['inputs']['delayed_sim']}`",
        f"- focused signal: `{payload['inputs']['science_sim']}`",
        f"- side-entry bridge source: `{payload['inputs']['side_entry_bridge_summary']}`",
        "",
        "Normalization:",
        f"- prompt time: `{payload['normalization']['prompt_time_s']:.9g} s`",
        f"- delayed observation time: `{payload['normalization']['delayed_time_s']:.9g} s`",
        f"- active-veto threshold: `{payload['normalization']['active_veto_threshold_keV']:.6g} keV`",
        f"- reject policy: `{payload['normalization']['reject_policy']}`",
        "",
    ]
    for win, item in payload["windows"].items():
        phys = item["physical_reference_flux"]
        lines.extend(
            [
                f"## {win}",
                "",
                "| stream | raw rate | active-veto rate | side Compton/FoV rate | final events |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for stream, row in item["by_stream"].items():
            lines.append(
                f"| {stream} | {row['raw_rate_s-1']:.6g} | {row['active_veto_pass_rate_s-1']:.6g} | {row['side_compton_fov_pass_rate_s-1']:.6g} | {row['side_compton_fov_pass_events']} |"
            )
        lines.extend(
            [
                "",
                f"- background: `{phys['background_cps']:.6g} cps`; signal at reference flux: `{phys['signal_cps_at_reference_flux']:.6g} cps`",
                f"- Z20d direct S/sqrt(B): `{phys['Z20d_direct_s_over_sqrt_b']:.6g}`; 20-day 3-sigma flux: `{phys['flux_3sigma_20d_ph_cm2_s']:.6g} ph cm^-2 s^-1`",
                f"- low-stat final background events: `{phys['low_stat_final_background_events']}`",
                "",
            ]
        )
    lines.extend(
        [
            "Downstream status:",
            "- Step06--Step08 products were generated separately from this Step05 output.",
            "- Replacement review was completed separately and requires user review; it is not an automatic fix5 replacement.",
            "- Mass_model_511 P1/P2/P3 replay was completed separately and is not paper-applied here.",
            "",
            f"CSV: `{rel(RATES_CSV)}`",
            f"Timeline CSV: `{rel(TIMELINE_CSV)}`",
        ]
    )
    return "\n".join(lines) + "\n"


def build(workers: int, rebuild_cache: bool) -> dict[str, Any]:
    step05 = load_step05()
    configure_step05(step05)
    OUT.mkdir(parents=True, exist_ok=True)
    pf = preflight(step05)
    if pf["problems"]:
        raise SystemExit("Step05 preflight failed: " + "; ".join(pf["problems"]))

    prompt_audit = step05.prompt_normalization_audit()
    step05.write_prompt_normalization_audit(prompt_audit)
    if prompt_audit["problems"]:
        raise SystemExit("Prompt normalization audit failed: " + "; ".join(prompt_audit["problems"]))

    adr = step05.load_adr_module()
    step05.configure_parser(adr)
    cat = adr.load_or_build_catalog(OUT, workers=workers, science_flux=1.0, rebuild=rebuild_cache)
    prompt_cache_rates_refreshed = step05.refresh_prompt_event_rates(cat)
    if prompt_cache_rates_refreshed:
        write_event_catalog_cache(cat)

    disk = step05.side_entry_disk()
    reject_policy = "keep"
    windows = {
        name: step05.summarize_window(cat, *bounds, disk=disk, reject_policy=reject_policy)
        for name, bounds in step05.WINDOWS.items()
    }
    science_norm = step05.load_science_physical_normalization()
    step05.add_physical_reference_to_windows(windows, science_norm)
    rng = np.random.default_rng(step05.RNG_SEED)
    timeline_draw = step05.draw_timeline(cat, step05.delayed_time_s(), rng)
    timeline = step05.analyze_timeline(cat, timeline_draw, step05.delayed_time_s(), disk, reject_policy)

    payload = {
        "status": "PASS_MASS_MODEL_511_STEP05_SIDE_ENTRY_COMPTON_TIME_AXIS_L1_FULLSTAT_V1_NOT_REPLACEMENT",
        "statistics_label": LABEL,
        "generated_at_utc": now_utc(),
        "claim_level": "MASS_MODEL_511_FULLSTAT_V1_L1_PROMPT_DELAYED_SIGNAL_NOT_NO_EFFECT_DECISION",
        "preflight": pf,
        "inputs": {
            "prompt_dir": rel(PROMPT_DIR),
            "prompt_files": len(sorted(PROMPT_DIR.glob("*.sim.gz"))),
            "prompt_dat_files": len(sorted(PROMPT_DIR.glob("*.dat.inc1.dat"))),
            "delayed_sim": rel(DELAYED_SIM),
            "delayed_summary": rel(DELAYED_SUMMARY),
            "science_sim": rel(SIGNAL_SIM),
            "signal_manifest": rel(SIGNAL_MANIFEST),
            "side_entry_bridge_summary": rel(STEP09_BRIDGE_SUMMARY),
        },
        "normalization": {
            "prompt_time_s": step05.prompt_time_s(),
            "prompt_rate_rule": "per-tag event rate = 1 / sum(TT_s for prompt dat files with that tag)",
            "prompt_cache_rates_refreshed": prompt_cache_rates_refreshed,
            "prompt_normalization_audit_csv": rel(OUT / "prompt_normalization_audit.csv"),
            "prompt_normalization_audit_json": rel(OUT / "prompt_normalization_audit.json"),
            "prompt_normalization_audit": prompt_audit,
            "delayed_time_s": step05.delayed_time_s(),
            "science_unit_injection_rate_s-1": 1.0,
            "active_veto_threshold_keV": step05.ACTIVE_VETO_THRESHOLD_KEV,
            "active_veto_match": step05.ACTIVE_VETO_MATCH_DESCRIPTION,
            "reject_policy": reject_policy,
            "coincidence_window_s": step05.COINCIDENCE_WINDOW_S,
            "rng_seed": step05.RNG_SEED,
            "side_entry_disk": {
                "center_cm": [float(x) for x in disk["center_cm"]],
                "normal": [float(x) for x in disk["normal"]],
                "radius_cm": float(disk["radius_cm"]),
                "local_center_cm": list(disk["local_center_cm"]),
                "rotation_y_deg": float(disk["rotation_y_deg"]),
                "side_window_look_elevation_deg": float(disk["side_window_look_elevation_deg"]),
            },
        },
        "science_physical_normalization": science_norm,
        "catalog": {
            "events_kept": int(len(cat["stream"])),
            "pixel_hits_kept": int(len(cat["pix_e"])),
            "by_stream_events": {
                stream: int(np.sum(cat["stream"] == stream)) for stream in ("prompt", "delayed", "science")
            },
            "by_stream_tes_events": {
                stream: int(np.sum((cat["stream"] == stream) & (cat["tes_total_keV"] > 0)))
                for stream in ("prompt", "delayed", "science")
            },
        },
        "windows": windows,
        "timeline": timeline,
        "timeline_draw_summary": timeline_draw["draw_summary"],
        "downstream_status": {
            "step06_step08": "COMPLETED_SEPARATELY",
            "replacement_review": "USER_REVIEW_REQUIRED_MASS_MODEL_511_NOT_AUTO_REPLACEMENT",
            "p1_p2_p3_replay": "PASS_MASS_MODEL_511_P1_P2_P3_REPLAY_NOT_PAPER_APPLIED",
        },
        "pending": [
            "User decision is required before replacing the paper-facing fix5 authority with Mass_model_511 values.",
            "Manuscript application of accepted Mass_model_511 replacement/P1/P2/P3 values is not yet done.",
        ],
    }
    step05.write_rates_csv(payload)
    step05.write_timeline_csv(payload)
    SUMMARY_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    SUMMARY_MD.write_text(markdown(payload), encoding="utf-8")
    return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--rebuild-cache", action="store_true")
    args = ap.parse_args()
    payload = build(workers=args.workers, rebuild_cache=args.rebuild_cache)
    print(json.dumps({"status": payload["status"], "summary": rel(SUMMARY_JSON), "report": rel(SUMMARY_MD)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
