#!/usr/bin/env python3
"""Build a v3p5 Step05 L1 detector-response summary.

This reuses the existing SIM catalog parser from make_complete_day15_report_ADR,
but does not reuse its Compton/FoV veto because that code assumes a z-entry
Be-window plane.  The v3p5 side-entry geometry needs a separate cone/side-plane
migration before a final Step05 veto claim.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import pickle
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "code" / "tools"
OUT = ROOT / "stepwise_maintenance" / "step05_veto_time_axis" / "outputs_v3p5_centerfinger_l1"
SUMMARY_JSON = OUT / "step05_v3p5_centerfinger_l1_response_summary.json"
SUMMARY_MD = OUT / "step05_v3p5_centerfinger_l1_response_summary.md"
RATES_CSV = OUT / "step05_v3p5_centerfinger_l1_rates.csv"
TIMELINE_CSV = OUT / "step05_v3p5_centerfinger_l1_timeline_rates.csv"

PROMPT_DIR = ROOT / "runs" / "step02_instant_v3p5_centerfinger_1of10"
PROMPT_NORM = PROMPT_DIR / "normalization.json"
DELAYED_SIM = ROOT / "runs" / "step02_delayed_transport_v3p5_centerfinger_1of10" / "DelayedDecayRPIPGroundStateFixed.inc1.id1.sim.gz"
FIXED_SOURCE = ROOT / "runs" / "step02_delay_fix_v3p5_centerfinger_1of10" / "activation_decay_day15_groundstate_fixed.source"
STEP02_SUMMARY = ROOT / "stepwise_maintenance" / "step02_raw_background_simulation" / "outputs_v3p5_centerfinger_1of10" / "step02_v3p5_centerfinger_1of10_summary.json"
SCIENCE_SIM = ROOT / "runs" / "step09_optics_bridge" / "Opticsim_laue_f10m_a1_v3p5_centerfinger.inc1.id1.sim.gz"
STEP09_SUMMARY = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs_f10m_a1_v3p5" / "step09_optics_bridge_summary.json"
F10M_A1_AEFF = ROOT / "stepwise_maintenance" / "step04_opticsim" / "optics_aeff_authority_f10m_a1.json"
SCIENCE_RATE_LEDGER = ROOT / "config" / "science_511_onaxis_source" / "metadata" / "science_rate_ledger.csv"
BOUNDARY_CLOSURE_SUMMARY = ROOT / "outputs" / "reports" / "v3p5_boundary_closure_20260613" / "v3p5_boundary_closure_summary.json"
ACTIVE_VETO_THRESHOLD_KEV = 50.0
ACTIVE_VETO_MATCH_DESCRIPTION = "volume name starts with CsI_ plus legacy BGO/ACTIVE_SHIELD/CEBR3 tokens"
BGO_SAMPLE_LABEL = "bgo_sample_fullstat_v2_exactpos"

WINDOWS = {
    "broad_480_550": (480.0, 550.0),
    "w2_510p58_511p42": (510.58, 511.42),
}

REFERENCE_FLUX_PH_CM2_S = 1.0e-4
MISSION_DAYS = 20.0
SECONDS_PER_DAY = 86400.0
ME_KEV = 511.0
PIX_HALF_X_CM = 0.075
PIX_HALF_Y_CM = 0.075
PIX_HALF_Z_CM = 0.150
N_CONE_SAMPLES = 24
MAX_ENUM_HITS = 6
COINCIDENCE_WINDOW_S = 1.0e-6
RNG_SEED = 260512
TAG_RE = re.compile(r"Background_(?P<tag>[^_]+)_", re.IGNORECASE)
TT_RE = re.compile(r"^\s*TT\s+([-+0-9.eE]+)\s*$")

_PROMPT_NORMALIZATION_AUDIT: dict[str, Any] | None = None


def is_exactpos_label(label: str) -> bool:
    return label.startswith("fullstat_v2_exactpos")


def is_bgo_sample_label(label: str) -> bool:
    return label == BGO_SAMPLE_LABEL


def configure_paths(label: str) -> None:
    global _PROMPT_NORMALIZATION_AUDIT
    global OUT, SUMMARY_JSON, SUMMARY_MD, RATES_CSV, TIMELINE_CSV
    global PROMPT_DIR, PROMPT_NORM, DELAYED_SIM, FIXED_SOURCE, STEP02_SUMMARY
    global SCIENCE_SIM, STEP09_SUMMARY, BOUNDARY_CLOSURE_SUMMARY
    global ACTIVE_VETO_THRESHOLD_KEV, ACTIVE_VETO_MATCH_DESCRIPTION

    _PROMPT_NORMALIZATION_AUDIT = None
    ACTIVE_VETO_THRESHOLD_KEV = 50.0
    ACTIVE_VETO_MATCH_DESCRIPTION = "volume name starts with CsI_ plus legacy BGO/ACTIVE_SHIELD/CEBR3 tokens"
    SCIENCE_SIM = ROOT / "runs" / "step09_optics_bridge" / "Opticsim_laue_f10m_a1_v3p5_centerfinger.inc1.id1.sim.gz"
    STEP09_SUMMARY = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs_f10m_a1_v3p5" / "step09_optics_bridge_summary.json"

    if is_bgo_sample_label(label):
        OUT = ROOT / "stepwise_maintenance" / "step05_veto_time_axis" / "outputs_bgo_sample_fullstat_v2_exactpos_l1"
        SUMMARY_JSON = OUT / "step05_bgo_sample_l1_response_summary.json"
        SUMMARY_MD = OUT / "step05_bgo_sample_l1_response_summary.md"
        RATES_CSV = OUT / "step05_bgo_sample_l1_rates.csv"
        TIMELINE_CSV = OUT / "step05_bgo_sample_l1_timeline_rates.csv"
        PROMPT_DIR = ROOT / "runs" / "step02_bgo_sample_fullstat_v2_instant"
        PROMPT_NORM = PROMPT_DIR / "normalization.json"
        DELAYED_SIM = ROOT / "runs" / "step02_bgo_sample_fullstat_v2_exactpos_delayed_transport" / "DelayedDecayBgoSampleFullstatV2Exactpos.inc1.id1.sim.gz"
        FIXED_SOURCE = ROOT / "runs" / "step02_bgo_sample_fullstat_v2_delay_fix" / "activation_decay_day15_groundstate_fixed.source"
        STEP02_SUMMARY = ROOT / "Bgo_sample" / "step02_fullstat_v2_exactpos_summary.json"
        SCIENCE_SIM = ROOT / "runs" / "step09_bgo_sample_focus" / "Opticsim_laue_f10m_a1_bgo_sample.inc1.id1.sim.gz"
        STEP09_SUMMARY = ROOT / "Bgo_sample" / "step09_focus_summary.json"
        BOUNDARY_CLOSURE_SUMMARY = (
            ROOT
            / "outputs"
            / "reports"
            / "v3p5_boundary_closure_fullstat_v2_exactpos_20260613"
            / "v3p5_boundary_closure_summary.json"
        )
        ACTIVE_VETO_THRESHOLD_KEV = 70.0
        ACTIVE_VETO_MATCH_DESCRIPTION = "volume name contains BGO/ACTIVE_SHIELD active-shield tokens; Bgo_sample uses a 70 keV veto threshold"
        return

    if label == "1of10":
        OUT = ROOT / "stepwise_maintenance" / "step05_veto_time_axis" / "outputs_v3p5_centerfinger_l1"
    else:
        OUT = ROOT / "stepwise_maintenance" / "step05_veto_time_axis" / f"outputs_v3p5_centerfinger_{label}_l1"
    SUMMARY_JSON = OUT / "step05_v3p5_centerfinger_l1_response_summary.json"
    SUMMARY_MD = OUT / "step05_v3p5_centerfinger_l1_response_summary.md"
    RATES_CSV = OUT / "step05_v3p5_centerfinger_l1_rates.csv"
    TIMELINE_CSV = OUT / "step05_v3p5_centerfinger_l1_timeline_rates.csv"

    prompt_label = "fullstat_v2" if is_exactpos_label(label) else label
    PROMPT_DIR = ROOT / "runs" / f"step02_instant_v3p5_centerfinger_{prompt_label}"
    PROMPT_NORM = PROMPT_DIR / "normalization.json"
    DELAYED_SIM = ROOT / "runs" / f"step02_delayed_transport_v3p5_centerfinger_{label}" / "DelayedDecayRPIPGroundStateFixed.inc1.id1.sim.gz"
    FIXED_SOURCE = ROOT / "runs" / f"step02_delay_fix_v3p5_centerfinger_{label}" / "activation_decay_day15_groundstate_fixed.source"
    STEP02_SUMMARY = (
        ROOT
        / "stepwise_maintenance"
        / "step02_raw_background_simulation"
        / f"outputs_v3p5_centerfinger_{label}"
        / f"step02_v3p5_centerfinger_{label}_summary.json"
    )
    if is_exactpos_label(label):
        BOUNDARY_CLOSURE_SUMMARY = (
            ROOT
            / "outputs"
            / "reports"
            / "v3p5_boundary_closure_fullstat_v2_exactpos_20260613"
            / "v3p5_boundary_closure_summary.json"
        )
    else:
        BOUNDARY_CLOSURE_SUMMARY = (
            ROOT
            / "outputs"
            / "reports"
            / "v3p5_boundary_closure_20260613"
            / "v3p5_boundary_closure_summary.json"
        )


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_prompt_tag(path: Path | str) -> str:
    m = TAG_RE.search(Path(path).name)
    return m.group("tag").lower() if m else "unknown"


def load_adr_module():
    sys.path.insert(0, str(TOOLS))
    spec = importlib.util.spec_from_file_location("make_complete_day15_report_ADR", TOOLS / "make_complete_day15_report_ADR.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load make_complete_day15_report_ADR")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def is_v3p5_active_veto_volume(vol: str) -> bool:
    upper = str(vol).upper()
    return upper.startswith("CSI_") or "ACTIVE_SHIELD" in upper or "CEBR3" in upper or "BGO" in upper


def prompt_time_s() -> float:
    return float(load_json(PROMPT_NORM)["gamma_prompt_time_s_with_farfield_area"])


def build_prompt_normalization_audit() -> dict[str, Any]:
    norm = load_json(PROMPT_NORM)
    dat_files = sorted(PROMPT_DIR.glob("*.dat.inc1.dat"))
    if not dat_files:
        raise FileNotFoundError(f"No prompt dat files found in {PROMPT_DIR}")

    rows_by_tag: dict[str, dict[str, Any]] = {}
    problems: list[str] = []
    non_gamma_expected = norm.get("non_gamma_replicas")
    gamma_expected = norm.get("gamma_splits")

    for path in dat_files:
        tag = parse_prompt_tag(path)
        row = rows_by_tag.setdefault(
            tag,
            {
                "tag": tag,
                "files": 0,
                "tt_files": 0,
                "tt_line_count": 0,
                "tt_sum_s": 0.0,
                "tt_mean_s": 0.0,
                "tt_min_s": None,
                "tt_max_s": None,
                "rate_hz_per_event": 0.0,
                "rate_times_tt_sum": 0.0,
                "expected_files_from_normalization": "",
                "warnings": [],
            },
        )
        row["files"] += 1
        tt_values: list[float] = []
        with path.open("r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                m = TT_RE.match(line)
                if not m:
                    continue
                try:
                    tt_values.append(float(m.group(1)))
                except ValueError:
                    pass
        row["tt_line_count"] += len(tt_values)
        if len(tt_values) != 1:
            msg = f"{path.name} has {len(tt_values)} TT records; expected exactly 1"
            row["warnings"].append(msg)
            problems.append(msg)
            continue
        tt = tt_values[0]
        if not math.isfinite(tt) or tt <= 0.0:
            msg = f"{path.name} has invalid TT={tt}"
            row["warnings"].append(msg)
            problems.append(msg)
            continue
        row["tt_files"] += 1
        row["tt_sum_s"] += tt
        row["tt_min_s"] = tt if row["tt_min_s"] is None else min(float(row["tt_min_s"]), tt)
        row["tt_max_s"] = tt if row["tt_max_s"] is None else max(float(row["tt_max_s"]), tt)

    for tag, row in rows_by_tag.items():
        expected = gamma_expected if tag == "gamma" else non_gamma_expected
        if expected is not None:
            row["expected_files_from_normalization"] = int(expected)
            if int(row["files"]) != int(expected):
                msg = f"tag={tag} has {row['files']} files but normalization expects {expected}"
                row["warnings"].append(msg)
                problems.append(msg)
        if int(row["tt_files"]) != int(row["files"]):
            msg = f"tag={tag} has valid TT in {row['tt_files']}/{row['files']} files"
            if msg not in row["warnings"]:
                row["warnings"].append(msg)
            problems.append(msg)
        tt_sum = float(row["tt_sum_s"])
        if tt_sum <= 0.0:
            msg = f"tag={tag} has non-positive TT sum"
            row["warnings"].append(msg)
            problems.append(msg)
            continue
        row["tt_mean_s"] = tt_sum / float(row["tt_files"])
        row["rate_hz_per_event"] = 1.0 / tt_sum
        row["rate_times_tt_sum"] = row["rate_hz_per_event"] * tt_sum
        if abs(float(row["rate_times_tt_sum"]) - 1.0) > 1.0e-12:
            msg = f"tag={tag} rate*sumTT={row['rate_times_tt_sum']:.12g}, expected 1"
            row["warnings"].append(msg)
            problems.append(msg)

    rows = [rows_by_tag[tag] for tag in sorted(rows_by_tag)]
    return {
        "status": "PASS" if not problems else "FAIL",
        "problems": problems,
        "prompt_dir": rel(PROMPT_DIR),
        "prompt_norm": rel(PROMPT_NORM),
        "normalization_json": {
            "non_gamma_replicas": norm.get("non_gamma_replicas"),
            "gamma_splits": norm.get("gamma_splits"),
            "gamma_prompt_time_s_with_farfield_area": norm.get("gamma_prompt_time_s_with_farfield_area"),
            "non_gamma_combined_norm_factor": norm.get("non_gamma_combined_norm_factor"),
        },
        "rows": rows,
    }


def prompt_normalization_audit() -> dict[str, Any]:
    global _PROMPT_NORMALIZATION_AUDIT
    if _PROMPT_NORMALIZATION_AUDIT is None:
        _PROMPT_NORMALIZATION_AUDIT = build_prompt_normalization_audit()
    return _PROMPT_NORMALIZATION_AUDIT


def prompt_rate_by_tag() -> dict[str, float]:
    audit = prompt_normalization_audit()
    if audit["problems"]:
        raise RuntimeError("Prompt normalization audit failed: " + "; ".join(audit["problems"]))
    return {row["tag"]: float(row["rate_hz_per_event"]) for row in audit["rows"]}


def write_prompt_normalization_audit(audit: dict[str, Any]) -> None:
    fields = [
        "tag",
        "files",
        "tt_files",
        "tt_line_count",
        "tt_sum_s",
        "tt_mean_s",
        "tt_min_s",
        "tt_max_s",
        "rate_hz_per_event",
        "rate_times_tt_sum",
        "expected_files_from_normalization",
        "warnings",
    ]
    rows = []
    for row in audit["rows"]:
        out = dict(row)
        out["warnings"] = "; ".join(str(item) for item in out.get("warnings", []))
        rows.append(out)
    with (OUT / "prompt_normalization_audit.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (OUT / "prompt_normalization_audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def refresh_prompt_event_rates(cat: dict[str, Any]) -> bool:
    rates = prompt_rate_by_tag()
    stream = np.asarray(cat["stream"], dtype=object)
    tag = np.asarray(cat["tag"], dtype=object)
    mask_prompt = stream == "prompt"
    if not np.any(mask_prompt):
        return False
    rate_hz = np.asarray(cat["rate_hz"], dtype=np.float64)
    changed = False
    for name, target in rates.items():
        mask = mask_prompt & (tag == name)
        if not np.any(mask):
            continue
        if not np.allclose(rate_hz[mask], target, rtol=0.0, atol=1.0e-18):
            rate_hz[mask] = target
            changed = True
    missing = sorted(set(str(x) for x in tag[mask_prompt]) - set(rates))
    if missing:
        raise RuntimeError(f"Prompt catalog has tags missing from normalization audit: {missing}")
    if changed:
        cat["rate_hz"] = rate_hz
    return changed


def write_event_catalog_cache(cat: dict[str, Any]) -> None:
    cache = OUT / "work" / "event_catalog.pkl"
    cache.parent.mkdir(parents=True, exist_ok=True)
    with cache.open("wb") as fh:
        pickle.dump(cat, fh, protocol=pickle.HIGHEST_PROTOCOL)


def delayed_time_s() -> float:
    summary = load_json(STEP02_SUMMARY)
    transport = summary.get("delayed_transport") or summary.get("transport")
    if not isinstance(transport, dict) or "TE_s" not in transport:
        raise KeyError(f"Cannot locate delayed transport TE_s in {STEP02_SUMMARY}")
    return float(transport["TE_s"])


def load_reference_atmospheric_transmission() -> dict[str, Any]:
    rows = []
    with SCIENCE_RATE_LEDGER.open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            rows.append(row)
    if not rows:
        raise ValueError(f"empty science-rate ledger: {SCIENCE_RATE_LEDGER}")
    best = min(rows, key=lambda row: abs(float(row["flux_ph_cm2_s"]) - REFERENCE_FLUX_PH_CM2_S))
    if abs(float(best["flux_ph_cm2_s"]) - REFERENCE_FLUX_PH_CM2_S) > 1.0e-12:
        raise ValueError(f"no {REFERENCE_FLUX_PH_CM2_S:g} reference-flux row in {SCIENCE_RATE_LEDGER}")
    return {
        "ledger": rel(SCIENCE_RATE_LEDGER),
        "source_id": best["source_id"],
        "flux_ph_cm2_s": float(best["flux_ph_cm2_s"]),
        "mainline_A_opt_cm2_in_ledger": float(best["A_opt_cm2"]),
        "T_atm": float(best["T_atm"]),
        "note": (
            "Only scalar T_atm is inherited from this mainline ledger; v3p5/f10m A1 uses the "
            "f10m_a1 A_eff authority below. A dedicated 45 deg side-entry LOS atmosphere "
            f"sidecar is available in {rel(BOUNDARY_CLOSURE_SUMMARY)}."
        ),
    }


def load_science_physical_normalization() -> dict[str, Any]:
    aeff = load_json(F10M_A1_AEFF)
    atm = load_reference_atmospheric_transmission()
    aeff_cm2 = float(aeff["aeff_511_cm2"])
    t_atm = float(atm["T_atm"])
    injection_rate = REFERENCE_FLUX_PH_CM2_S * aeff_cm2 * t_atm
    seed = aeff.get("seed_aggregate", {}).get("a1_R2_honest_tile_footprint", {})
    return {
        "reference_flux_ph_cm2_s": REFERENCE_FLUX_PH_CM2_S,
        "mission_days_for_direct_expectation": MISSION_DAYS,
        "optics_authority": rel(F10M_A1_AEFF),
        "optics_design_name": aeff.get("design_name"),
        "optics_profile": "f10m_a1_v3p5",
        "aeff_511_cm2": aeff_cm2,
        "aeff_seed_pstdev_cm2": seed.get("pstdev_aeff_cm2"),
        "atmospheric_transmission": atm,
        "rate_to_v3p5_injection_plane_s-1": injection_rate,
        "unit_eventlist_injection_rate_s-1": 1.0,
        "scale_from_unit_eventlist_rate": injection_rate,
    }


def add_physical_reference_to_windows(windows: dict[str, Any], norm: dict[str, Any]) -> None:
    mission_s = MISSION_DAYS * SECONDS_PER_DAY
    injection_rate = float(norm["rate_to_v3p5_injection_plane_s-1"])
    for item in windows.values():
        by = item["by_stream"]
        prompt = by["prompt"]["side_compton_fov_pass_rate_s-1"]
        delayed = by["delayed"]["side_compton_fov_pass_rate_s-1"]
        science_unit = by["science"]["side_compton_fov_pass_rate_s-1"]
        background = prompt + delayed
        signal = science_unit * injection_rate
        source_counts = signal * mission_s
        background_counts = background * mission_s
        z20 = source_counts / math.sqrt(background_counts) if background_counts > 0 else None
        flux3 = REFERENCE_FLUX_PH_CM2_S * 3.0 / z20 if z20 and z20 > 0 else None
        t3 = MISSION_DAYS * (3.0 / z20) ** 2 if z20 and z20 > 0 else None
        t5 = MISSION_DAYS * (5.0 / z20) ** 2 if z20 and z20 > 0 else None
        bkg_events = by["prompt"]["side_compton_fov_pass_events"] + by["delayed"]["side_compton_fov_pass_events"]
        item["physical_reference_flux"] = {
            "reference_flux_ph_cm2_s": REFERENCE_FLUX_PH_CM2_S,
            "rate_to_v3p5_injection_plane_s-1": injection_rate,
            "prompt_background_cps": prompt,
            "delayed_background_cps": delayed,
            "background_cps": background,
            "signal_cps_at_reference_flux": signal,
            "signal_to_background": signal / background if background > 0 else None,
            "mission_days": MISSION_DAYS,
            "source_counts_20d": source_counts,
            "background_counts_20d": background_counts,
            "Z20d_direct_s_over_sqrt_b": z20,
            "T3_day_constant_rate_direct": t3,
            "T5_day_constant_rate_direct": t5,
            "flux_3sigma_20d_ph_cm2_s": flux3,
            "low_stat_final_background_events": bkg_events,
            "low_stat_background_relative_poisson_sigma_approx": (1.0 / math.sqrt(bkg_events)) if bkg_events > 0 else None,
            "low_stat_prompt_final_events": by["prompt"]["side_compton_fov_pass_events"],
            "low_stat_delayed_final_events": by["delayed"]["side_compton_fov_pass_events"],
            "science_unit_rate_final_events": by["science"]["side_compton_fov_pass_events"],
            "claim_note": "Direct expectation only. It uses the v3p5 1/10 Step05 selected-event rates and does not replace a full Step06-Step08 mission-axis regeneration.",
        }


def signal_triggers() -> int:
    summary = load_json(STEP09_SUMMARY)
    if "step09_focused_signal" in summary:
        return int(summary["step09_focused_signal"]["eventlist_rows"])
    if "triggers" in summary:
        return int(summary["triggers"])
    return int(summary["bridge"]["rows_written"])


def step09_bridge() -> dict[str, Any]:
    summary = load_json(STEP09_SUMMARY)
    bridge = summary.get("bridge") or summary.get("base_bridge")
    if not isinstance(bridge, dict):
        raise KeyError(f"Cannot locate Step09 bridge geometry in {STEP09_SUMMARY}")
    return bridge


def configure_parser(adr) -> None:
    adr.PROMPT_DIR = PROMPT_DIR
    adr.PROMPT_NORM = PROMPT_NORM
    adr.DELAY_DIR = DELAYED_SIM.parent
    adr.FIXED_DELAY_SIM = DELAYED_SIM
    adr.FIXED_SOURCE = FIXED_SOURCE
    adr.SCIENCE_SIM = SCIENCE_SIM
    adr.is_active_veto_volume = is_v3p5_active_veto_volume
    adr.prompt_time_s = prompt_time_s
    adr.delayed_time_s = delayed_time_s
    adr.science_generated_triggers = signal_triggers
    adr.science_rate_for_flux = lambda flux_ph_cm2_s: float(flux_ph_cm2_s)

    def event_rate_for_mode(path: str, mode: str, science_flux: float):
        if mode == "prompt":
            tag = adr.parse_tag(path)
            rates = prompt_rate_by_tag()
            if tag not in rates:
                raise ValueError(f"prompt tag {tag!r} missing from normalization audit")
            return "prompt", tag, rates[tag]
        if mode == "delayed":
            return "delayed", "activation", 1.0 / delayed_time_s()
        if mode == "science":
            return "science", "focused_eventlist_unit_rate", float(science_flux) / max(signal_triggers(), 1)
        raise ValueError(mode)

    adr.event_rate_for_mode = event_rate_for_mode


def unit(v: np.ndarray) -> np.ndarray | None:
    n = float(np.linalg.norm(v))
    return None if n <= 0.0 else v / n


def rotate_y(values: tuple[float, float, float], angle_deg: float) -> np.ndarray:
    x, y, z = values
    a = math.radians(angle_deg)
    c = math.cos(a)
    s = math.sin(a)
    return np.asarray([c * x + s * z, y, -s * x + c * z], dtype=float)


def side_entry_disk() -> dict[str, Any]:
    bridge = step09_bridge()
    angle = float(bridge["instrument_rotation_y_deg"])
    local_center = (
        float(bridge["x_plane_cm"]),
        float(bridge["axis_y_cm"]),
        float(bridge["axis_z_cm"]),
    )
    center = rotate_y(local_center, angle)
    # The disk plane is perpendicular to local +x. The sign of the normal does
    # not affect the ray/plane intersection parameter.
    normal = unit(rotate_y((1.0, 0.0, 0.0), angle))
    if normal is None:
        raise ValueError("bad side-entry disk normal")
    ref = np.asarray([0.0, 0.0, 1.0], dtype=float)
    if abs(float(np.dot(normal, ref))) > 0.9:
        ref = np.asarray([0.0, 1.0, 0.0], dtype=float)
    u = unit(np.cross(normal, ref))
    if u is None:
        raise ValueError("bad side-entry disk basis")
    v = unit(np.cross(normal, u))
    if v is None:
        raise ValueError("bad side-entry disk basis")
    return {
        "center_cm": center,
        "normal": normal,
        "basis_u": u,
        "basis_v": v,
        "radius_cm": float(bridge["be_radius_cm"]),
        "local_center_cm": local_center,
        "rotation_y_deg": angle,
        "side_window_look_elevation_deg": float(bridge["side_window_look_elevation_deg"]),
    }


def representative_points_box(hit) -> np.ndarray:
    pts = []
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            for sz in (-1.0, 1.0):
                pts.append([hit.x + sx * PIX_HALF_X_CM, hit.y + sy * PIX_HALF_Y_CM, hit.z + sz * PIX_HALF_Z_CM])
    pts.append([hit.x, hit.y, hit.z])
    return np.asarray(pts, dtype=float)


def orthonormal_basis_batch(axis_hat: np.ndarray):
    ref = np.zeros_like(axis_hat)
    mask = np.abs(axis_hat[:, 2]) < 0.9
    ref[mask] = np.asarray([0.0, 0.0, 1.0])
    ref[~mask] = np.asarray([1.0, 0.0, 0.0])
    e1 = np.cross(axis_hat, ref)
    n1 = np.linalg.norm(e1, axis=1)
    valid1 = n1 > 1.0e-12
    e1[valid1] /= n1[valid1, None]
    e2 = np.cross(axis_hat, e1)
    n2 = np.linalg.norm(e2, axis=1)
    valid2 = n2 > 1.0e-12
    e2[valid2] /= n2[valid2, None]
    return e1, e2, valid1 & valid2


def compton_cos_theta(e_first: float, e_second: float) -> float:
    e0 = e_first + e_second
    ep = e_second
    if e0 <= 0 or ep <= 0:
        return float("nan")
    return 1.0 - ME_KEV * (1.0 / ep - 1.0 / e0)


def segments_intersect_disk_2d(segments: np.ndarray, radius: float) -> bool:
    if segments is None or len(segments) == 0:
        return False
    p0 = segments[:, 0, :]
    p1 = segments[:, 1, :]
    d = p1 - p0
    a = np.sum(d * d, axis=1)
    t = np.zeros(len(segments), dtype=float)
    nz = a > 1.0e-18
    if np.any(nz):
        t[nz] = -np.sum(p0[nz] * d[nz], axis=1) / a[nz]
        t[nz] = np.clip(t[nz], 0.0, 1.0)
    closest = p0 + t[:, None] * d
    r2 = np.sum(closest * closest, axis=1)
    return bool(np.any(r2 <= radius * radius))


def sample_cone_side_disk(hit1, hit2, e_first: float, e_second: float, disk: dict[str, Any]) -> tuple[bool, bool]:
    ctheta = compton_cos_theta(e_first, e_second)
    if (not np.isfinite(ctheta)) or ctheta < -1.0 or ctheta > 1.0:
        return False, False
    theta = math.acos(float(np.clip(ctheta, -1.0, 1.0)))
    reps1 = representative_points_box(hit1)
    reps2 = representative_points_box(hit2)
    p1 = np.repeat(reps1, len(reps2), axis=0)
    p2 = np.tile(reps2, (len(reps1), 1))
    axis_vec = p1 - p2
    norms = np.linalg.norm(axis_vec, axis=1)
    valid_norm = norms > 1.0e-12
    if not np.any(valid_norm):
        return True, False
    p1 = p1[valid_norm]
    axis_hat = axis_vec[valid_norm] / norms[valid_norm, None]
    e1, e2, valid_basis = orthonormal_basis_batch(axis_hat)
    if not np.any(valid_basis):
        return True, False
    p1 = p1[valid_basis]
    axis_hat = axis_hat[valid_basis]
    e1 = e1[valid_basis]
    e2 = e2[valid_basis]

    phis = np.linspace(0.0, 2.0 * math.pi, N_CONE_SAMPLES, endpoint=False)
    dirs = (
        math.cos(theta) * axis_hat[:, None, :]
        + math.sin(theta)
        * (np.cos(phis)[None, :, None] * e1[:, None, :] + np.sin(phis)[None, :, None] * e2[:, None, :])
    )
    center = np.asarray(disk["center_cm"], dtype=float)
    normal = np.asarray(disk["normal"], dtype=float)
    u = np.asarray(disk["basis_u"], dtype=float)
    v = np.asarray(disk["basis_v"], dtype=float)
    denom = np.tensordot(dirs, normal, axes=([2], [0]))
    numer = np.dot(center, normal) - np.dot(p1, normal)
    t = np.full(denom.shape, np.nan, dtype=float)
    valid_denom = np.abs(denom) > 1.0e-12
    numer_grid = np.broadcast_to(numer[:, None], denom.shape)
    t[valid_denom] = numer_grid[valid_denom] / denom[valid_denom]
    valid = valid_denom & (t > 0.0) & np.isfinite(t)
    if not np.any(valid):
        return True, False

    points = p1[:, None, :] + np.where(valid, t, 0.0)[:, :, None] * dirs
    relp = points - center
    coords = np.stack([np.tensordot(relp, u, axes=([2], [0])), np.tensordot(relp, v, axes=([2], [0]))], axis=2)
    r2 = np.sum(coords * coords, axis=2)
    if bool(np.any(valid & (r2 <= float(disk["radius_cm"]) ** 2))):
        return True, True

    segs = []
    for i in range(coords.shape[0]):
        valid_i = valid[i]
        seg_mask = valid_i & np.roll(valid_i, -1)
        idx = np.where(seg_mask)[0]
        if len(idx):
            segs.append(np.stack([coords[i, idx], coords[i, (idx + 1) % coords.shape[1]]], axis=1))
    flat_segments = np.concatenate(segs, axis=0) if segs else np.empty((0, 2, 2), dtype=float)
    return True, segments_intersect_disk_2d(flat_segments, float(disk["radius_cm"]))


def sequence_metrics(ordered: list[Any]) -> dict[str, float] | None:
    n = len(ordered)
    energies = np.asarray([h.e for h in ordered], dtype=float)
    positions = np.asarray([[h.x, h.y, h.z] for h in ordered], dtype=float)
    if np.any(~np.isfinite(energies)) or np.any(energies <= 0):
        return None
    total_e = float(np.sum(energies))
    rem_after = total_e - np.cumsum(energies)
    cos_kin = []
    theta1 = None
    for i in range(n - 1):
        if rem_after[i] <= 0:
            return None
        c = compton_cos_theta(float(energies[i]), float(rem_after[i]))
        if (not np.isfinite(c)) or c < -1.0 or c > 1.0:
            return None
        cos_kin.append(float(c))
        if i == 0:
            theta1 = math.degrees(math.acos(float(np.clip(c, -1.0, 1.0))))
    qf_terms = []
    for i in range(1, n - 1):
        u_prev = unit(positions[i] - positions[i - 1])
        u_next = unit(positions[i + 1] - positions[i])
        if u_prev is None or u_next is None:
            return None
        qf_terms.append((cos_kin[i] - float(np.dot(u_prev, u_next))) ** 2)
    return {
        "qf": float(np.sum(qf_terms)) if qf_terms else 0.0,
        "first_lever_arm": float(np.linalg.norm(positions[1] - positions[0])),
        "e_first": float(energies[0]),
        "e_after1": float(rem_after[0]),
        "theta1": float(theta1) if theta1 is not None else float("nan"),
    }


def classify_side_compton(hits: list[Any], disk: dict[str, Any], reject_policy: str) -> str:
    if len(hits) <= 1:
        return "single"
    if len(hits) == 2:
        decisions = []
        for a, b in ((hits[0], hits[1]), (hits[1], hits[0])):
            ok, intersects = sample_cone_side_disk(a, b, a.e, b.e, disk)
            if ok:
                decisions.append(intersects)
        cls = "reject" if not decisions else ("keep" if any(decisions) else "veto")
    else:
        import itertools

        if len(hits) > MAX_ENUM_HITS:
            cls = "reject"
        else:
            valid = []
            for perm in itertools.permutations(range(len(hits))):
                ordered = [hits[i] for i in perm]
                metrics = sequence_metrics(ordered)
                if metrics is None:
                    continue
                valid.append((metrics["qf"], -metrics["first_lever_arm"], ordered, metrics))
            if not valid:
                cls = "reject"
            else:
                _, _, ordered, metrics = sorted(valid, key=lambda x: (x[0], x[1]))[0]
                ok, intersects = sample_cone_side_disk(ordered[0], ordered[1], metrics["e_first"], metrics["e_after1"], disk)
                cls = "reject" if not ok else ("keep" if intersects else "veto")
    if cls == "reject" and reject_policy == "keep":
        return "reject_kept"
    return cls


def side_keep_from_hits(hits: list[Any], disk: dict[str, Any], reject_policy: str) -> tuple[bool, str]:
    cls = classify_side_compton(hits, disk, reject_policy)
    return cls in ("single", "keep", "reject_kept"), cls


def event_hits(cat: dict, idx: int):
    s = int(cat["pix_start"][idx])
    n = int(cat["pix_count"][idx])
    hits = []
    for j in range(s, s + n):
        hits.append(
            type("Hit", (), {})()
        )
        hits[-1].x = float(cat["pix_x"][j])
        hits[-1].y = float(cat["pix_y"][j])
        hits[-1].z = float(cat["pix_z"][j])
        hits[-1].e = float(cat["pix_e"][j])
        hits[-1].pixel_uid = str(cat["pix_uid"][j])
        hits[-1].layer = int(cat["pix_layer"][j])
    return hits


def summarize_window(cat: dict, emin: float, emax: float, disk: dict[str, Any], reject_policy: str) -> dict[str, Any]:
    out: dict[str, Any] = {"window_keV": [emin, emax], "by_stream": {}, "total": {}}
    for stream in ("prompt", "delayed", "science"):
        mask_stream = cat["stream"] == stream
        mask_tes = mask_stream & (cat["tes_total_keV"] >= emin) & (cat["tes_total_keV"] < emax)
        mask_active = mask_tes & (cat["bgo_total_keV"] < ACTIVE_VETO_THRESHOLD_KEV)
        final_rate = 0.0
        final_events = 0
        class_counts = Counter()
        for idx in np.flatnonzero(mask_active):
            keep, cls = side_keep_from_hits(event_hits(cat, int(idx)), disk, reject_policy)
            class_counts[cls] += 1
            if keep:
                final_events += 1
                final_rate += float(cat["rate_hz"][idx])
        raw_rate = float(np.sum(cat["rate_hz"][mask_tes]))
        active_rate = float(np.sum(cat["rate_hz"][mask_active]))
        raw_events = int(np.sum(mask_tes))
        active_events = int(np.sum(mask_active))
        out["by_stream"][stream] = {
            "raw_events": raw_events,
            "active_veto_pass_events": active_events,
            "side_compton_fov_pass_events": final_events,
            "raw_rate_s-1": raw_rate,
            "active_veto_pass_rate_s-1": active_rate,
            "side_compton_fov_pass_rate_s-1": final_rate,
            "active_veto_survival_fraction": active_rate / raw_rate if raw_rate > 0 else None,
            "side_compton_fov_survival_fraction_vs_active": final_rate / active_rate if active_rate > 0 else None,
            "side_compton_class_counts": dict(sorted(class_counts.items())),
        }
    for stage in ("raw", "active_veto_pass", "side_compton_fov_pass"):
        key = f"{stage}_rate_s-1" if stage != "raw" else "raw_rate_s-1"
        ekey = f"{stage}_events" if stage != "raw" else "raw_events"
        out["total"][stage] = {
            "events": int(sum(out["by_stream"][s][ekey] for s in out["by_stream"])),
            "rate_s-1": float(sum(out["by_stream"][s][key] for s in out["by_stream"])),
        }
    return out


def aggregate_candidate_hits(cat: dict, event_indices: np.ndarray):
    by_uid: dict[str, dict[str, Any]] = {}
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
        hit = type("Hit", (), {})()
        hit.x = rec["wx"] / e
        hit.y = rec["wy"] / e
        hit.z = rec["wz"] / e
        hit.e = e
        hit.pixel_uid = uid
        hit.layer = int(rec["layer"])
        hits.append(hit)
    return hits


def draw_timeline(cat: dict, obs_time_s: float, rng: np.random.Generator) -> dict[str, Any]:
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


def analyze_timeline(cat: dict, timeline: dict[str, Any], obs_time_s: float, disk: dict[str, Any], reject_policy: str) -> dict[str, Any]:
    out = {
        "obs_time_s": obs_time_s,
        "n_event_instances": int(len(timeline["event_index"])),
        "n_candidates_total": 0,
        "n_candidates_with_tes": 0,
        "n_mixed_candidates": 0,
        "windows": {
            name: {
                "counts": {"raw": 0, "active_veto_pass": 0, "side_compton_fov_pass": 0},
                "rates_s-1": {"raw": 0.0, "active_veto_pass": 0.0, "side_compton_fov_pass": 0.0},
                "side_compton_class_counts": {},
            }
            for name in WINDOWS
        },
    }
    class_counts = {name: Counter() for name in WINDOWS}
    idxs = timeline["event_index"]
    times = timeline["time_s"]
    n = len(idxs)
    if n > 0:
        boundaries = np.empty(n, dtype=bool)
        boundaries[0] = True
        boundaries[1:] = (times[1:] - times[:-1]) > COINCIDENCE_WINDOW_S
        starts = np.flatnonzero(boundaries)
        ends = np.empty_like(starts)
        if len(starts) > 1:
            ends[:-1] = starts[1:]
        ends[-1] = n
        sizes = ends - starts
        out["n_candidates_total"] = int(len(starts))

        single_starts = starts[sizes == 1]
        single_event_idx = idxs[single_starts]
        if len(single_event_idx) > 0:
            single_e = cat["tes_total_keV"][single_event_idx]
            single_bgo = cat["bgo_total_keV"][single_event_idx]
            out["n_candidates_with_tes"] += int(np.count_nonzero(single_e > 0))
            for name, (emin, emax) in WINDOWS.items():
                raw_mask = (single_e >= emin) & (single_e < emax)
                out["windows"][name]["counts"]["raw"] += int(np.count_nonzero(raw_mask))
                if not np.any(raw_mask):
                    continue
                active_mask = raw_mask & (single_bgo < ACTIVE_VETO_THRESHOLD_KEV)
                out["windows"][name]["counts"]["active_veto_pass"] += int(np.count_nonzero(active_mask))
                vetoed = int(np.count_nonzero(raw_mask & ~active_mask))
                if vetoed:
                    class_counts[name]["active_veto"] += vetoed
                for idx in single_event_idx[active_mask]:
                    keep, cls = side_keep_from_hits(event_hits(cat, int(idx)), disk, reject_policy)
                    class_counts[name][cls] += 1
                    if keep:
                        out["windows"][name]["counts"]["side_compton_fov_pass"] += 1

        for start, end in zip(starts[sizes > 1], ends[sizes > 1]):
            ev = idxs[start:end]
            streams = set(str(x) for x in cat["stream"][ev])
            if len(streams) > 1:
                out["n_mixed_candidates"] += 1
            e = float(np.sum(cat["tes_total_keV"][ev]))
            bgo = float(np.sum(cat["bgo_total_keV"][ev]))
            if e > 0:
                out["n_candidates_with_tes"] += 1
            for name, (emin, emax) in WINDOWS.items():
                if not (emin <= e < emax):
                    continue
                out["windows"][name]["counts"]["raw"] += 1
                if bgo < ACTIVE_VETO_THRESHOLD_KEV:
                    out["windows"][name]["counts"]["active_veto_pass"] += 1
                    keep, cls = side_keep_from_hits(aggregate_candidate_hits(cat, ev), disk, reject_policy)
                    class_counts[name][cls] += 1
                    if keep:
                        out["windows"][name]["counts"]["side_compton_fov_pass"] += 1
                else:
                    class_counts[name]["active_veto"] += 1
    for name in WINDOWS:
        for stage, count in out["windows"][name]["counts"].items():
            out["windows"][name]["rates_s-1"][stage] = float(count) / obs_time_s if obs_time_s > 0 else 0.0
        out["windows"][name]["side_compton_class_counts"] = dict(sorted(class_counts[name].items()))
    return out


def write_rates_csv(payload: dict[str, Any]) -> None:
    with RATES_CSV.open("w", encoding="utf-8", newline="") as fh:
        fields = ["window", "stream", "stage", "events", "rate_s-1", "survival_fraction_vs_raw"]
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for win, item in payload["windows"].items():
            for stream, row in item["by_stream"].items():
                raw = row["raw_rate_s-1"]
                for stage, event_key, rate_key in (
                    ("raw", "raw_events", "raw_rate_s-1"),
                    ("active_veto_pass", "active_veto_pass_events", "active_veto_pass_rate_s-1"),
                    ("side_compton_fov_pass", "side_compton_fov_pass_events", "side_compton_fov_pass_rate_s-1"),
                ):
                    writer.writerow(
                        {
                            "window": win,
                            "stream": stream,
                            "stage": stage,
                            "events": row[event_key],
                            "rate_s-1": f"{row[rate_key]:.12g}",
                            "survival_fraction_vs_raw": "" if raw <= 0 else f"{row[rate_key] / raw:.12g}",
                        }
                    )


def write_timeline_csv(payload: dict[str, Any]) -> None:
    with TIMELINE_CSV.open("w", encoding="utf-8", newline="") as fh:
        fields = ["window", "stage", "counts", "rate_s-1"]
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for win, item in payload["timeline"]["windows"].items():
            for stage, count in item["counts"].items():
                writer.writerow({"window": win, "stage": stage, "counts": count, "rate_s-1": f"{item['rates_s-1'][stage]:.12g}"})


def markdown(payload: dict[str, Any]) -> str:
    label = payload["statistics_label"]
    title = "# Step05 Bgo_sample L1 Detector Response" if is_bgo_sample_label(label) else "# Step05 v3p5 Center-Finger L1 Detector Response"
    claim = (
        f"Bgo_sample side-entry Compton/FoV response with {ACTIVE_VETO_THRESHOLD_KEV:g} keV BGO active-veto threshold; "
        "direct detector-response expectation feeding the closed Step06--Step08 hard-window material comparison."
        if is_bgo_sample_label(label)
        else "v3p5 side-entry Compton/FoV migrated to the tilted Be disk, plus direct expectation, physical reference-flux scaling, and one common Poisson time-axis draw."
    )
    lines = [
        title,
        "",
        f"Status: `{payload['status']}`.",
        "",
        f"Claim level: {claim} Statistics label: `{label}`.",
        "",
        "Inputs:",
        f"- prompt: `{payload['inputs']['prompt_dir']}`",
        f"- delayed: `{payload['inputs']['delayed_sim']}`",
        f"- focused signal: `{payload['inputs']['science_sim']}`",
        "",
        "Normalization:",
        f"- prompt time: `{payload['normalization']['prompt_time_s']:.9g} s`",
        f"- prompt rate normalization: per-tag `1/sum(TT_tag)` from `{payload['normalization']['prompt_normalization_audit_csv']}`",
        f"- delayed observation time: `{payload['normalization']['delayed_time_s']:.9g} s`",
        "- focused signal direct rates are first normalized to a unit EventList injection rate (`1 injected focused photon/s`).",
        f"- physical reference flux: `{payload['science_physical_normalization']['reference_flux_ph_cm2_s']:.6g} ph cm^-2 s^-1`",
        f"- f10m A1 A_eff(511): `{payload['science_physical_normalization']['aeff_511_cm2']:.8g} cm2`",
        f"- inherited T_atm: `{payload['science_physical_normalization']['atmospheric_transmission']['T_atm']:.8g}`",
        f"- active-veto threshold: `{payload['normalization']['active_veto_threshold_keV']:.6g} keV`",
        f"- T_atm boundary: scalar mainline reference transmission is inherited here; the dedicated 45 deg side-entry LOS atmosphere sidecar is `{rel(BOUNDARY_CLOSURE_SUMMARY)}`.",
        f"- reference injection-plane rate: `{payload['science_physical_normalization']['rate_to_v3p5_injection_plane_s-1']:.8g} s^-1`",
        "",
    ]
    for win, item in payload["windows"].items():
        phys = item["physical_reference_flux"]
        lines.extend(
            [
                f"## {win}",
                "",
                "| stream | raw rate | active-veto rate | side Compton/FoV rate | final/active |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for stream, row in item["by_stream"].items():
            surv = row["side_compton_fov_survival_fraction_vs_active"]
            lines.append(
                f"| {stream} | {row['raw_rate_s-1']:.6g} | {row['active_veto_pass_rate_s-1']:.6g} | {row['side_compton_fov_pass_rate_s-1']:.6g} | {'' if surv is None else f'{surv:.6g}'} |"
            )
        lines.extend(
            [
                "",
                "Physical reference direct expectation:",
                f"- background: `{phys['background_cps']:.6g} cps`; signal at reference flux: `{phys['signal_cps_at_reference_flux']:.6g} cps`",
                f"- 20-day counts: S `{phys['source_counts_20d']:.6g}`, B `{phys['background_counts_20d']:.6g}`",
                f"- Z20d direct S/sqrt(B): `{phys['Z20d_direct_s_over_sqrt_b']:.6g}`; T3 constant-rate direct: `{phys['T3_day_constant_rate_direct']:.6g} day`; 20-day 3-sigma flux: `{phys['flux_3sigma_20d_ph_cm2_s']:.6g} ph cm^-2 s^-1`",
                f"- low-stat final background events: `{phys['low_stat_final_background_events']}`; approximate relative Poisson sigma `{phys['low_stat_background_relative_poisson_sigma_approx']:.6g}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Common Poisson Time Axis",
            "",
            f"- observation time: `{payload['timeline']['obs_time_s']:.9g} s`",
            f"- event instances drawn: `{payload['timeline']['n_event_instances']}`",
            f"- candidates: `{payload['timeline']['n_candidates_total']}` total, `{payload['timeline']['n_candidates_with_tes']}` with TES energy, `{payload['timeline']['n_mixed_candidates']}` mixed-stream",
            "",
            "| window | raw cps | active-veto cps | side Compton/FoV cps |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for win, item in payload["timeline"]["windows"].items():
        rates = item["rates_s-1"]
        lines.append(f"| {win} | {rates['raw']:.6g} | {rates['active_veto_pass']:.6g} | {rates['side_compton_fov_pass']:.6g} |")
    lines.extend(["", "Pending before paper-facing v3p5 statistics:"])
    for item in payload.get("pending", []):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            f"CSV: `{rel(RATES_CSV)}`",
            f"Timeline CSV: `{rel(TIMELINE_CSV)}`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="1of10", help="Run/output label, e.g. 1of10 or fullstat_v2")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--rebuild-cache", action="store_true")
    args = ap.parse_args()

    configure_paths(args.label)
    OUT.mkdir(parents=True, exist_ok=True)
    prompt_audit = prompt_normalization_audit()
    write_prompt_normalization_audit(prompt_audit)
    if prompt_audit["problems"]:
        raise SystemExit("Prompt normalization audit failed: " + "; ".join(prompt_audit["problems"]))
    adr = load_adr_module()
    configure_parser(adr)
    cat = adr.load_or_build_catalog(OUT, workers=args.workers, science_flux=1.0, rebuild=args.rebuild_cache)
    prompt_cache_rates_refreshed = refresh_prompt_event_rates(cat)
    if prompt_cache_rates_refreshed:
        write_event_catalog_cache(cat)
    disk = side_entry_disk()
    reject_policy = "keep"

    windows = {name: summarize_window(cat, *bounds, disk=disk, reject_policy=reject_policy) for name, bounds in WINDOWS.items()}
    science_norm = load_science_physical_normalization()
    add_physical_reference_to_windows(windows, science_norm)
    rng = np.random.default_rng(RNG_SEED)
    timeline_draw = draw_timeline(cat, delayed_time_s(), rng)
    timeline = analyze_timeline(cat, timeline_draw, delayed_time_s(), disk, reject_policy)
    if is_bgo_sample_label(args.label):
        pending = [
            "Downstream Step06--Step08 and the BGO-vs-CsI hard-window comparison are closed for this label; this file remains the Step05 detector-response authority.",
            "Optional: run BGO spatial/profile-likelihood sidecars before claiming spatial-analysis gains.",
            "Optional: add BGO material-uncertainty or detector-threshold sensitivity scans before claiming robustness against those choices.",
        ]
    elif is_exactpos_label(args.label):
        pending = [
            "quantify exact-RPIP PointSource support-size stability, or run the full weighted-table source if Cosima parsing is made practical",
            "add selection-consistent spatial/profile likelihood products",
        ]
    else:
        pending = [
            "promote smoke-validated exact-RPIP PointSource sampling to v3p5 fullstat fixed-inventory delayed transport",
        ]
    status = (
        "PASS_BGO_SAMPLE_STEP05_SIDE_ENTRY_COMPTON_TIME_AXIS_L1_FULLSTAT_V2_EXACTPOS"
        if is_bgo_sample_label(args.label)
        else f"PASS_V3P5_STEP05_SIDE_ENTRY_COMPTON_TIME_AXIS_L1_{args.label.upper()}"
    )
    claim_level = (
        "BGO_SAMPLE_L1_DETECTOR_RESPONSE_FULLSTAT_V2_EXACTPOS_NOT_STEP08_SENSITIVITY"
        if is_bgo_sample_label(args.label)
        else f"L1 side-entry Compton/FoV + common Poisson time-axis; direct physical reference-flux scaling added; {args.label} statistics"
    )
    payload = {
        "status": status,
        "statistics_label": args.label,
        "claim_level": claim_level,
        "inputs": {
            "prompt_dir": rel(PROMPT_DIR),
            "prompt_files": len(sorted(PROMPT_DIR.glob("*.sim.gz"))),
            "prompt_dat_files": len(sorted(PROMPT_DIR.glob("*.dat.inc1.dat"))),
            "delayed_sim": rel(DELAYED_SIM),
            "science_sim": rel(SCIENCE_SIM),
        },
        "normalization": {
            "prompt_time_s": prompt_time_s(),
            "prompt_rate_rule": "per-tag event rate = 1 / sum(TT_s for prompt dat files with that tag)",
            "prompt_cache_rates_refreshed": prompt_cache_rates_refreshed,
            "prompt_normalization_audit_csv": rel(OUT / "prompt_normalization_audit.csv"),
            "prompt_normalization_audit_json": rel(OUT / "prompt_normalization_audit.json"),
            "prompt_normalization_audit": prompt_audit,
            "delayed_time_s": delayed_time_s(),
            "science_unit_injection_rate_s-1": 1.0,
            "active_veto_threshold_keV": ACTIVE_VETO_THRESHOLD_KEV,
            "active_veto_match": ACTIVE_VETO_MATCH_DESCRIPTION,
            "reject_policy": reject_policy,
            "coincidence_window_s": COINCIDENCE_WINDOW_S,
            "rng_seed": RNG_SEED,
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
            "by_stream_events": {stream: int(np.sum(cat["stream"] == stream)) for stream in ("prompt", "delayed", "science")},
            "by_stream_tes_events": {stream: int(np.sum((cat["stream"] == stream) & (cat["tes_total_keV"] > 0))) for stream in ("prompt", "delayed", "science")},
        },
        "windows": windows,
        "timeline": timeline,
        "timeline_draw_summary": timeline_draw["draw_summary"],
        "pending": pending,
    }
    write_rates_csv(payload)
    write_timeline_csv(payload)
    SUMMARY_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    SUMMARY_MD.write_text(markdown(payload), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "summary": rel(SUMMARY_JSON), "report": rel(SUMMARY_MD)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
