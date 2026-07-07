#!/usr/bin/env python3
"""Run Step05 detector response for the geo-opt S1/BPE/W5 full-stat branch.

This wrapper reuses the established Step05 parser/selection functions while
pinning every input/output path to the geometry-optimization branch. It also
builds and runs the matching focused-signal replay, because using a fix5 or
Mass_model_511 signal SIM would make the signal-retention part of Step05
geometry-inconsistent.
"""

from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
import pickle
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
PKG = ROOT / "engineering/geometry_optimization_20260704"
WORK = PKG / "03_step05_detector_response_20260706"
STEP05_SCRIPT = ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"

LABEL = "geo_opt_s1_bpe_w5_fullstat_v1"
OUT = ROOT / "stepwise_maintenance/step05_veto_time_axis/outputs_geo_opt_s1_bpe_w5_fullstat_v1_l1"
SUMMARY_JSON = OUT / "step05_geo_opt_s1_bpe_w5_fullstat_v1_l1_response_summary.json"
SUMMARY_MD = OUT / "step05_geo_opt_s1_bpe_w5_fullstat_v1_l1_response_summary.md"
RATES_CSV = OUT / "step05_geo_opt_s1_bpe_w5_fullstat_v1_l1_rates.csv"
TIMELINE_CSV = OUT / "step05_geo_opt_s1_bpe_w5_fullstat_v1_l1_timeline_rates.csv"

GEOMETRY = (
    "engineering/geometry_optimization_20260704/01_geo_opt_s1_bottomw_b4c/geometry/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
GEOMETRY_PATH = ROOT / GEOMETRY
CAMPAIGN_MANIFEST = PKG / "02_fullstat_prompt_delay_20260706/geo_opt_s1_bpe_w5_fullstat_v1_campaign_manifest.json"
DELAYED_SUMMARY = PKG / "02_fullstat_prompt_delay_20260706/delayed_source/delayed_source_exactpos_summary.json"

RUN_ROOT = ROOT / "runs/geometry_optimization_20260704"
PROMPT_DIR = RUN_ROOT / "step02_instant_geo_opt_s1_bpe_w5_fullstat_v1"
PROMPT_NORM = PROMPT_DIR / "normalization.json"
DELAYED_SIM = RUN_ROOT / "step02_delayed_transport_geo_opt_s1_bpe_w5_fullstat_v1/DelayedDecayGeoOptS1BpeW5FullstatV1.inc1.id1.sim.gz"
EXACTPOS_SOURCE = RUN_ROOT / "step02_delay_exactpos_geo_opt_s1_bpe_w5_fullstat_v1/activation_decay_day15_groundstate_fixed_exactpos.source"

SIGNAL_RUN_DIR = RUN_ROOT / "step09_focus_geo_opt_s1_bpe_w5_fullstat_v1"
SIGNAL_PREFIX = "Opticsim_laue_f10m_a1_geo_opt_s1_bpe_w5_fullstat_v1_signal"
SIGNAL_SOURCE = SIGNAL_RUN_DIR / f"{SIGNAL_PREFIX}.source"
SIGNAL_SIM = SIGNAL_RUN_DIR / f"{SIGNAL_PREFIX}.inc1.id1.sim.gz"
SIGNAL_LOG = SIGNAL_RUN_DIR / "cosima_geo_opt_signal.log"
SIGNAL_MANIFEST = WORK / "signal_transport_manifest.json"
SIGNAL_TRIGGERS = 37194
SIGNAL_SEED = 260616
MAX_TIMELINE_DRAW_LAMBDA = 5_000_000.0
EVENTLIST = (
    ROOT
    / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/eventlists/"
    "Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat"
)
MEGALIB_ENV = Path("/tmp/geo_opt_step05_megalib_env.log")
COSIMA = Path("/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima")
SOURCE_MEGALIB = Path("/home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh")

STEP09_BRIDGE_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/step09_optics_bridge_summary.json"
)
BOUNDARY_CLOSURE_SUMMARY = (
    ROOT
    / "outputs/reports/v3p5_boundary_closure_fullstat_v2_exactpos_20260613/v3p5_boundary_closure_summary.json"
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


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_step05():
    spec = importlib.util.spec_from_file_location("geo_opt_step05_l1", STEP05_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Step05 script: {STEP05_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def geo_opt_active_veto_volume(vol: str) -> bool:
    upper = str(vol).upper()
    return (
        upper.startswith("CSI_")
        or "ACTIVE_SHIELD" in upper
        or "CEBR3" in upper
        or "BGO" in upper
        or "GEOOPT_S1_PLASTICFULLWRAP" in upper
    )


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
    step05.ACTIVE_VETO_MATCH_DESCRIPTION = (
        "geo-opt S1/BPE/W5 current geometry; active-veto volumes are CsI_ plus "
        "legacy BGO/ACTIVE_SHIELD/CEBR3 tokens plus GeoOpt_S1_PlasticFullWrap plastic skin"
    )
    step05.is_v3p5_active_veto_volume = geo_opt_active_veto_volume
    step05._PROMPT_NORMALIZATION_AUDIT = None


def build_signal_source() -> dict[str, Any]:
    SIGNAL_RUN_DIR.mkdir(parents=True, exist_ok=True)
    body = f"""# Geo-opt focused-signal source copy.
# Replays the current f10m A1 Step09 EventList through geo_opt_s1_bpe_w5_fullstat_v1.
# This is geometry-local signal input for Step05, not a standalone promotion artifact.

Version 1
Geometry {GEOMETRY}
PhysicsListEM LivermorePol
PhysicsListHD qgsp-bic-hp
StoreSimulationInfo all
DiscretizeHits true
DetectorTimeConstant 1e-9
Seed {SIGNAL_SEED}

Run {SIGNAL_PREFIX}
{SIGNAL_PREFIX}.FileName {rel(SIGNAL_RUN_DIR / SIGNAL_PREFIX)}
{SIGNAL_PREFIX}.Triggers {SIGNAL_TRIGGERS}
{SIGNAL_PREFIX}.Source {SIGNAL_PREFIX}_EventList

{SIGNAL_PREFIX}_EventList.EventList {rel(EVENTLIST)}
"""
    SIGNAL_SOURCE.write_text(body, encoding="utf-8")
    return {
        "source": rel(SIGNAL_SOURCE),
        "geometry": GEOMETRY,
        "triggers": SIGNAL_TRIGGERS,
        "seed": SIGNAL_SEED,
        "eventlist": rel(EVENTLIST),
    }


def inspect_signal_header(path: Path) -> dict[str, Any]:
    out: dict[str, Any] = {"exists": path.exists(), "SE": 0, "ID": 0, "TS": 0, "TE_s": None, "geometry": None}
    if not path.exists():
        return out
    try:
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
    except (EOFError, OSError, gzip.BadGzipFile) as exc:
        out["header_read_error"] = type(exc).__name__
    return out


def signal_ready() -> bool:
    header = inspect_signal_header(SIGNAL_SIM)
    return (
        header.get("exists") is True
        and header.get("SE") == SIGNAL_TRIGGERS
        and header.get("ID") == SIGNAL_TRIGGERS
        and GEOMETRY in str(header.get("geometry", ""))
    )


def run_signal_transport(force: bool = False) -> dict[str, Any]:
    source_record = build_signal_source()
    if signal_ready() and not force:
        header = inspect_signal_header(SIGNAL_SIM)
        payload = {
            "document_type": "geo_opt_s1_bpe_w5_focused_signal_transport",
            "generated_at_utc": now_utc(),
            "status": "PASS_SIGNAL_TRANSPORT_REUSED",
            "source_record": source_record,
            "run_record": {
                "status": "PASS",
                "returncode": 0,
                "sim": rel(SIGNAL_SIM),
                "log": rel(SIGNAL_LOG),
                "size_bytes": SIGNAL_SIM.stat().st_size,
                "reused_existing": True,
            },
            "header": header,
        }
        write_json(SIGNAL_MANIFEST, payload)
        return payload

    cmd = (
        f"source {SOURCE_MEGALIB} > {MEGALIB_ENV} && "
        f"{COSIMA} -s {SIGNAL_SEED} {SIGNAL_SOURCE} > {SIGNAL_LOG} 2>&1"
    )
    result = subprocess.run(["bash", "-lc", cmd], cwd=ROOT)
    header = inspect_signal_header(SIGNAL_SIM)
    problems: list[str] = []
    if result.returncode != 0:
        problems.append(f"cosima_returncode={result.returncode}")
    if header.get("SE") != SIGNAL_TRIGGERS or header.get("ID") != SIGNAL_TRIGGERS:
        problems.append(f"signal_header_counts={header.get('SE')}/{header.get('ID')}")
    if GEOMETRY not in str(header.get("geometry", "")):
        problems.append("signal_header_geometry_not_geo_opt")
    payload = {
        "document_type": "geo_opt_s1_bpe_w5_focused_signal_transport",
        "generated_at_utc": now_utc(),
        "status": "PASS_SIGNAL_TRANSPORT" if not problems else "FAIL_SIGNAL_TRANSPORT",
        "problems": problems,
        "source_record": source_record,
        "run_record": {
            "status": "PASS" if result.returncode == 0 else "FAIL",
            "returncode": result.returncode,
            "sim": rel(SIGNAL_SIM),
            "log": rel(SIGNAL_LOG),
            "size_bytes": SIGNAL_SIM.stat().st_size if SIGNAL_SIM.exists() else 0,
            "reused_existing": False,
        },
        "header": header,
    }
    write_json(SIGNAL_MANIFEST, payload)
    if problems:
        raise SystemExit("Signal transport failed: " + "; ".join(problems))
    return payload


def preflight(signal_manifest: dict[str, Any]) -> dict[str, Any]:
    campaign = load_json(CAMPAIGN_MANIFEST) if CAMPAIGN_MANIFEST.exists() else {}
    delayed_summary = load_json(DELAYED_SUMMARY) if DELAYED_SUMMARY.exists() else {}
    required = {
        "geometry": GEOMETRY_PATH,
        "campaign_manifest": CAMPAIGN_MANIFEST,
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
    delayed_transport = delayed_summary.get("delayed_transport") or {}
    signal_header = signal_manifest.get("header") or {}
    problems = list(missing)
    if campaign.get("status") != "PASS_PROMPT_AND_DELAYED_TRANSPORT":
        problems.append(f"campaign_status={campaign.get('status')}")
    if len(prompt_sim) != 68:
        problems.append(f"prompt_sim_count={len(prompt_sim)}")
    if len(prompt_dat) != 68:
        problems.append(f"prompt_dat_count={len(prompt_dat)}")
    if not delayed_status.startswith("PASS"):
        problems.append(f"delayed_summary_status={delayed_status or 'MISSING'}")
    if delayed_transport.get("SE") != 1_000_000 or delayed_transport.get("ID") != 1_000_000:
        problems.append(f"delayed_header_counts={delayed_transport.get('SE')}/{delayed_transport.get('ID')}")
    if GEOMETRY not in str(delayed_transport.get("geometry", "")):
        problems.append("delayed_header_geometry_not_geo_opt")
    if signal_header.get("SE") != SIGNAL_TRIGGERS or signal_header.get("ID") != SIGNAL_TRIGGERS:
        problems.append(f"signal_header_counts={signal_header.get('SE')}/{signal_header.get('ID')}")
    if GEOMETRY not in str(signal_header.get("geometry", "")):
        problems.append("signal_header_geometry_not_geo_opt")
    return {
        "status": "PASS" if not problems else "FAIL",
        "problems": problems,
        "inputs": {name: rel(path) for name, path in required.items()},
        "prompt_sim_files": len(prompt_sim),
        "prompt_dat_files": len(prompt_dat),
        "campaign_status": campaign.get("status"),
        "delayed_summary_status": delayed_status,
        "delayed_transport": delayed_transport,
        "signal_header": signal_header,
        "active_veto_extension": "GeoOpt_S1_PlasticFullWrap* volumes are counted as active-veto energy in bgo_total_keV.",
        "side_entry_bridge_reuse": (
            "The f10m A1 EventList/side-entry disk bridge is reused from the fix5 Step09 summary; "
            "the signal detector transport SIM itself is rerun through the geo-opt geometry."
        ),
    }


def write_event_catalog_cache(cat: dict[str, Any]) -> None:
    cache = OUT / "work/event_catalog.pkl"
    cache.parent.mkdir(parents=True, exist_ok=True)
    with cache.open("wb") as fh:
        pickle.dump(cat, fh, protocol=pickle.HIGHEST_PROTOCOL)


def build_timeline_response(step05, cat: dict[str, Any], disk: dict[str, Any], reject_policy: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    full_obs_time_s = float(step05.delayed_time_s())
    rates = np.asarray(cat["rate_hz"], dtype=np.float64)
    total_rate = float(np.sum(rates))
    full_lambda = total_rate * full_obs_time_s
    if full_lambda <= MAX_TIMELINE_DRAW_LAMBDA:
        obs_time_s = full_obs_time_s
        mode = "FULL_INTERVAL_POISSON_DRAW"
    else:
        obs_time_s = MAX_TIMELINE_DRAW_LAMBDA / total_rate
        mode = "ADAPTIVE_BOUNDED_HIGH_RATE_POISSON_DRAW"
    rng = np.random.default_rng(step05.RNG_SEED)
    timeline_draw = step05.draw_timeline(cat, obs_time_s, rng)
    timeline = step05.analyze_timeline(cat, timeline_draw, obs_time_s, disk, reject_policy)
    model = {
        "mode": mode,
        "full_obs_time_s": full_obs_time_s,
        "timeline_obs_time_s": obs_time_s,
        "total_catalog_rate_s-1": total_rate,
        "full_interval_expected_instances": full_lambda,
        "max_timeline_draw_lambda": MAX_TIMELINE_DRAW_LAMBDA,
        "bounded_fraction_of_full_interval": obs_time_s / full_obs_time_s if full_obs_time_s > 0 else None,
        "note": (
            "The geo-opt active-skin catalog has a high active-only rate. "
            "When the full-interval draw would exceed max_timeline_draw_lambda, "
            "the same Poisson grouping/veto/Compton code is run on a bounded "
            "observation interval and rates are reported per second."
        ),
    }
    return timeline, timeline_draw["draw_summary"], model


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Step05 geo-opt S1/BPE/W5 Full-Stat V1 L1 Detector Response",
        "",
        f"Status: `{payload['status']}`",
        "",
        "Claim level: geometry-optimization Step05 detector response for prompt, exact-position delayed, and focused EventList signal. This is not a Step06--Step08 mission fold and not a final promotion decision.",
        "",
        "Inputs:",
        f"- prompt: `{payload['inputs']['prompt_dir']}`",
        f"- delayed: `{payload['inputs']['delayed_sim']}`",
        f"- focused signal: `{payload['inputs']['science_sim']}`",
        f"- signal manifest: `{payload['inputs']['signal_manifest']}`",
        f"- side-entry bridge source: `{payload['inputs']['side_entry_bridge_summary']}`",
        "",
        "Normalization / Veto:",
        f"- prompt time: `{payload['normalization']['prompt_time_s']:.9g} s`",
        f"- delayed observation time: `{payload['normalization']['delayed_time_s']:.9g} s`",
        f"- active-veto threshold: `{payload['normalization']['active_veto_threshold_keV']:.6g} keV`",
        f"- active-veto match: {payload['normalization']['active_veto_match']}",
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
            f"- time-axis mode: `{payload['timeline_model']['mode']}`; timeline observation `{payload['timeline_model']['timeline_obs_time_s']:.6g} s`; full-interval expected instances `{payload['timeline_model']['full_interval_expected_instances']:.6g}`.",
            "- Step06--Step08 mission/time/significance folds are not generated by this Step05 run.",
            "- Geometry trade-off claims require comparing this Step05/Step06--08 branch against Mass_model_511/fix5 authority outputs.",
            "- The focused signal was rerun through the geo-opt geometry; do not substitute the Mass_model_511 or fix5 signal SIM for this label.",
            "",
            f"CSV: `{rel(RATES_CSV)}`",
            f"Timeline CSV: `{rel(TIMELINE_CSV)}`",
        ]
    )
    return "\n".join(lines) + "\n"


def build(workers: int, rebuild_cache: bool, force_signal: bool) -> dict[str, Any]:
    signal_manifest = run_signal_transport(force=force_signal)
    step05 = load_step05()
    configure_step05(step05)
    OUT.mkdir(parents=True, exist_ok=True)
    pf = preflight(signal_manifest)
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
    timeline, timeline_draw_summary, timeline_model = build_timeline_response(step05, cat, disk, reject_policy)

    payload = {
        "status": "PASS_GEO_OPT_S1_BPE_W5_STEP05_SIDE_ENTRY_COMPTON_TIME_AXIS_L1_FULLSTAT_V1_NOT_PROMOTION",
        "statistics_label": LABEL,
        "generated_at_utc": now_utc(),
        "claim_level": "GEO_OPT_S1_BPE_W5_FULLSTAT_V1_L1_PROMPT_DELAYED_SIGNAL_NOT_STEP08_NOT_PROMOTION",
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
        "timeline_draw_summary": timeline_draw_summary,
        "timeline_model": timeline_model,
        "downstream_status": {
            "step06_step08": "NOT_RUN",
            "promotion_review": "NOT_RUN",
            "signal_transport": signal_manifest.get("status"),
        },
        "pending": [
            "Run Step06--Step08 for this geo-opt label before mission-mean Z20d/F3 claims.",
            "Compare against Mass_model_511/fix5 with the same selection and active-veto assumptions before making a geometry decision.",
        ],
    }
    step05.write_rates_csv(payload)
    step05.write_timeline_csv(payload)
    write_json(SUMMARY_JSON, payload)
    SUMMARY_MD.write_text(markdown(payload), encoding="utf-8")
    return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--rebuild-cache", action="store_true")
    ap.add_argument("--force-signal", action="store_true")
    args = ap.parse_args()
    payload = build(workers=args.workers, rebuild_cache=args.rebuild_cache, force_signal=args.force_signal)
    print(json.dumps({"status": payload["status"], "summary": rel(SUMMARY_JSON), "report": rel(SUMMARY_MD)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
