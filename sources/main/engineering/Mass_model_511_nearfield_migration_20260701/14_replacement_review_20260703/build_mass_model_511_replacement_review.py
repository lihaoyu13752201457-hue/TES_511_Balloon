#!/usr/bin/env python3
"""Build the Mass_model_511 vs fix5 replacement review.

This is a read-only audit over existing full-stat outputs.  It does not rerun
Cosima and does not modify manuscript files.
"""

from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import math
import pickle
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent

MASS_LABEL = "Mass_model_511_fullstat_v1"
FIX5_LABEL = "fix5_fullstat_v2_exactpos_m50000_s260613"
COORD_MATCH_DECIMALS = 5
COORD_NEAREST_TOLERANCE_CM = 1.0e-5
DOMINANT_THRESHOLD = 0.5

STEP05_SCRIPT = ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"
MASS_STEP05_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step05_veto_time_axis/outputs_Mass_model_511_fullstat_v1_l1"
    / "step05_Mass_model_511_fullstat_v1_l1_response_summary.json"
)
MASS_STEP06_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step06_mission_time_variation/outputs_Mass_model_511_fullstat_v1"
    / "step06_Mass_model_511_fullstat_v1_summary.json"
)
MASS_STEP07_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step07_source_cases/outputs_Mass_model_511_fullstat_v1/source_case_summary.json"
)
MASS_STEP08_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step08_significance/outputs_Mass_model_511_fullstat_v1"
    / "step08_Mass_model_511_fullstat_v1_time_dependent_summary.json"
)
MASS_DELAYED_SOURCE_SUMMARY = (
    ROOT
    / "engineering/Mass_model_511_nearfield_migration_20260701/03_detector_transport/delayed"
    / "candidate_Mass_model_511/fullstat_v1/F1/delayed_source_exactpos_summary.json"
)
MASS_TRANSPORT_MANIFEST = (
    ROOT
    / "engineering/Mass_model_511_nearfield_migration_20260701/03_detector_transport"
    / "delayed_transport_campaign_manifest_candidate_Mass_model_511_fullstat_v1.json"
)
MASS_CATALOG = (
    ROOT
    / "stepwise_maintenance/step05_veto_time_axis/outputs_Mass_model_511_fullstat_v1_l1/work/event_catalog.pkl"
)
MASS_DELAYED_SIM = (
    ROOT
    / "runs/Mass_model_511_nearfield_migration_20260701"
    / "step02_delayed_transport_candidate_Mass_model_511_fullstat_v1"
    / "DelayedDecayMassModel511CandidateFullstatV1.inc1.id1.sim.gz"
)
MASS_EXACTPOS_TABLE = (
    ROOT
    / "runs/Mass_model_511_nearfield_migration_20260701"
    / "step02_delay_exactpos_candidate_Mass_model_511_fullstat_v1/exactpos_weighted_rpip_table.csv"
)
FIX5_PROMOTION_DECISION = ROOT / "outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_promotion_decision.json"
P1P2P3_REPLAY_README = (
    ROOT
    / "engineering/Mass_model_511_nearfield_migration_20260701/15_p1_p2_p3_replay_20260703/README.md"
)

OUT_JSON = OUT / "mass_model_511_replacement_review.json"
OUT_MD = OUT / "MASS_MODEL_511_REPLACEMENT_REVIEW.md"
OUT_CSV = OUT / "mass_model_511_vs_fix5_metrics.csv"
OUT_W_JSON = OUT / "mass_model_511_w_activation_selected_w2_audit.json"
OUT_W_CSV = OUT / "mass_model_511_w_activation_selected_w2_events.csv"


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def coord_key(za: str | int, x: float, y: float, z: float) -> tuple[str, str, str, str]:
    fmt = f"{{:.{COORD_MATCH_DECIMALS}f}}"
    return (str(int(float(za))), fmt.format(x), fmt.format(y), fmt.format(z))


def is_w_or_collimator_origin(volume: str, za: str | int | None) -> bool:
    lower = volume.lower()
    by_volume = lower.startswith("passive_w") or "collimator" in lower or "tungsten" in lower or "w_shield" in lower
    try:
        by_za = int(float(za)) // 1000 == 74
    except (TypeError, ValueError):
        by_za = False
    return by_volume or by_za


def load_step05_module():
    spec = importlib.util.spec_from_file_location("mass_model_511_step05_audit_module", STEP05_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {STEP05_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    # Mass_model_511 Step05 used the fix5 f10m A1 side-entry bridge definition.
    mod.ROOT = ROOT
    mod.TOOLS = ROOT / "old/code/tools"
    mod.configure_paths(FIX5_LABEL)
    return mod


def selected_delayed_w2_events(step05_mod, cat: dict[str, Any]) -> list[dict[str, Any]]:
    disk = step05_mod.side_entry_disk()
    selected: list[dict[str, Any]] = []
    stream = np.asarray(cat["stream"], dtype=object)
    energy = np.asarray(cat["tes_total_keV"], dtype=float)
    bgo = np.asarray(cat["bgo_total_keV"], dtype=float)
    mask = (
        (stream == "delayed")
        & (energy >= 510.58)
        & (energy < 511.42)
        & (bgo < float(step05_mod.ACTIVE_VETO_THRESHOLD_KEV))
    )
    for idx in np.flatnonzero(mask):
        keep, cls = step05_mod.side_keep_from_hits(step05_mod.event_hits(cat, int(idx)), disk, "keep")
        if not keep:
            continue
        selected.append(
            {
                "catalog_index": int(idx),
                "local_id": int(cat["local_id"][idx]),
                "tes_total_keV": float(cat["tes_total_keV"][idx]),
                "bgo_total_keV": float(cat["bgo_total_keV"][idx]),
                "rate_hz": float(cat["rate_hz"][idx]),
                "side_compton_class": cls,
                "pix_count": int(cat["pix_count"][idx]),
            }
        )
    return selected


def parse_ia_init_for_ids(wanted: set[int]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    current_id: int | None = None
    with gzip.open(MASS_DELAYED_SIM, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            if raw.startswith("ID "):
                parts = raw.split()
                current_id = int(parts[1]) if len(parts) >= 2 else None
                continue
            if current_id not in wanted:
                continue
            if raw.startswith("IA INIT"):
                parts = [part.strip() for part in raw.split(";")]
                if len(parts) < 16:
                    raise ValueError(f"bad IA INIT line for ID {current_id}: {raw[:120]}")
                out[current_id] = {
                    "source_x_cm": float(parts[4]),
                    "source_y_cm": float(parts[5]),
                    "source_z_cm": float(parts[6]),
                    "ZA": int(float(parts[15])),
                }
                if len(out) == len(wanted):
                    break
    return out


def load_exactpos_index() -> tuple[dict[tuple[str, str, str, str], list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    lookup: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    by_za: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with MASS_EXACTPOS_TABLE.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            row["_x_cm_float"] = float(row["x_cm"])
            row["_y_cm_float"] = float(row["y_cm"])
            row["_z_cm_float"] = float(row["z_cm"])
            key = coord_key(row["ZA"], float(row["x_cm"]), float(row["y_cm"]), float(row["z_cm"]))
            za_key = str(int(float(row["ZA"])))
            lookup[key].append(row)
            by_za[za_key].append(row)
    return lookup, by_za


def source_distance_cm(init: dict[str, Any], row: dict[str, Any]) -> float:
    dx = float(init["source_x_cm"]) - float(row["_x_cm_float"])
    dy = float(init["source_y_cm"]) - float(row["_y_cm_float"])
    dz = float(init["source_z_cm"]) - float(row["_z_cm_float"])
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def match_exactpos_source(
    init: dict[str, Any],
    lookup: dict[tuple[str, str, str, str], list[dict[str, Any]]],
    by_za: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, Any] | None, str, int, float | None]:
    key = coord_key(init["ZA"], init["source_x_cm"], init["source_y_cm"], init["source_z_cm"])
    keyed = lookup.get(key, [])
    if len(keyed) == 1:
        return keyed[0], "KEY_MATCH", 1, source_distance_cm(init, keyed[0])
    if len(keyed) > 1:
        return None, "AMBIGUOUS_KEY_MATCH", len(keyed), None

    candidates: list[tuple[float, dict[str, Any]]] = []
    for candidate in by_za.get(str(int(init["ZA"])), []):
        distance_cm = source_distance_cm(init, candidate)
        if distance_cm <= COORD_NEAREST_TOLERANCE_CM:
            candidates.append((distance_cm, candidate))
    candidates.sort(key=lambda item: item[0])
    if len(candidates) == 1:
        return candidates[0][1], "NEAREST_MATCH_WITHIN_TOLERANCE", 1, candidates[0][0]
    if not candidates:
        return None, "NO_MATCH_WITHIN_TOLERANCE", 0, None
    return None, "AMBIGUOUS_NEAREST_MATCH_WITHIN_TOLERANCE", len(candidates), candidates[0][0]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def build_w_activation_audit(mass_step05: dict[str, Any]) -> dict[str, Any]:
    step05_mod = load_step05_module()
    with MASS_CATALOG.open("rb") as handle:
        cat = pickle.load(handle)
    selected = selected_delayed_w2_events(step05_mod, cat)
    ids = {row["local_id"] for row in selected}
    ia = parse_ia_init_for_ids(ids)
    lookup, by_za = load_exactpos_index()

    rows: list[dict[str, Any]] = []
    problems: list[str] = []
    for row in selected:
        local_id = int(row["local_id"])
        init = ia.get(local_id)
        if init is None:
            problems.append(f"missing_IA_INIT_for_ID_{local_id}")
            rows.append({**row, "source_match_status": "MISSING_IA_INIT"})
            continue
        match, match_status, match_count, match_distance_cm = match_exactpos_source(init, lookup, by_za)
        if match is None:
            problems.append(f"exactpos_{match_status}_{match_count}_for_ID_{local_id}")
            match = {}
        volume = str(match.get("VN", ""))
        source_za = match.get("ZA", init["ZA"])
        rows.append(
            {
                **row,
                **init,
                "source_match_status": match_status,
                "source_match_count": match_count,
                "source_match_distance_cm": match_distance_cm,
                "VN": volume,
                "source_ZA": source_za,
                "source_sim": match.get("source_sim", ""),
                "sample_weight": match.get("sample_weight", ""),
                "is_w_or_collimator_origin": is_w_or_collimator_origin(volume, source_za),
            }
        )

    write_csv(OUT_W_CSV, rows)

    total_rate = sum(float(row.get("rate_hz", 0.0)) for row in rows)
    w_rate = sum(float(row.get("rate_hz", 0.0)) for row in rows if row.get("is_w_or_collimator_origin") is True)
    expected_delayed = float(
        mass_step05["windows"]["w2_510p58_511p42"]["by_stream"]["delayed"]["side_compton_fov_pass_rate_s-1"]
    )
    expected_events = int(
        mass_step05["windows"]["w2_510p58_511p42"]["by_stream"]["delayed"]["side_compton_fov_pass_events"]
    )
    close_rate = abs(total_rate - expected_delayed) <= 1.0e-15
    close_events = len(rows) == expected_events
    volume_counts = Counter(str(row.get("VN", "")) for row in rows)
    volume_rates: dict[str, float] = defaultdict(float)
    for row in rows:
        volume_rates[str(row.get("VN", ""))] += float(row.get("rate_hz", 0.0))
    top_volumes = [
        {"VN": volume, "events": volume_counts[volume], "rate_hz": volume_rates[volume]}
        for volume, _count in volume_counts.most_common(20)
    ]

    payload = {
        "status": "PASS_MASS_MODEL_511_SELECTED_W_ACTIVATION_W2_AUDIT"
        if not problems and close_rate and close_events
        else "FAIL_MASS_MODEL_511_SELECTED_W_ACTIVATION_W2_AUDIT",
        "label": MASS_LABEL,
        "generated_at_utc": now_utc(),
        "method": (
            "Recompute the Step05 W2 delayed final selection from event_catalog.pkl, parse IA INIT for those "
            "delayed SIM event IDs, and match source ZA/x/y/z back to the Mass_model_511 exactpos weighted "
            "RPIP table."
        ),
        "source_position_match": {
            "key": ["ZA", "x_cm", "y_cm", "z_cm"],
            "coordinate_decimals": COORD_MATCH_DECIMALS,
            "nearest_tolerance_cm": COORD_NEAREST_TOLERANCE_CM,
        },
        "inputs": {
            "step05_summary": rel(MASS_STEP05_SUMMARY),
            "event_catalog": rel(MASS_CATALOG),
            "delayed_sim": rel(MASS_DELAYED_SIM),
            "exactpos_table": rel(MASS_EXACTPOS_TABLE),
            "side_entry_bridge_source": "fix5 Step09 f10m A1 side-entry disk; detector events are Mass_model_511 current-geometry SIM",
        },
        "selection": {
            "stream": "delayed",
            "window_keV": [510.58, 511.42],
            "active_veto_threshold_keV": float(step05_mod.ACTIVE_VETO_THRESHOLD_KEV),
            "side_compton_fov_policy": "same side_keep_from_hits/event_hits/side_entry_disk implementation as Step05",
        },
        "checks": {
            "selected_events": len(rows),
            "expected_step05_delayed_selected_events": expected_events,
            "selected_rate_hz": total_rate,
            "expected_step05_delayed_rate_hz": expected_delayed,
            "rate_abs_delta_hz": total_rate - expected_delayed,
            "events_match_step05": close_events,
            "rate_matches_step05": close_rate,
            "ia_init_matches": len(ia),
            "exactpos_match_failures": len(problems),
            "w_or_collimator_selected_events": sum(1 for row in rows if row.get("is_w_or_collimator_origin") is True),
            "w_or_collimator_selected_rate_hz": w_rate,
            "w_or_collimator_fraction_of_delayed_selected_rate": w_rate / total_rate if total_rate > 0 else None,
            "w_or_collimator_dominant_threshold_fraction": DOMINANT_THRESHOLD,
            "w_or_collimator_is_dominant_component": (w_rate / total_rate) >= DOMINANT_THRESHOLD if total_rate > 0 else False,
        },
        "top_source_volumes": top_volumes,
        "event_table": rel(OUT_W_CSV),
        "problems": problems,
    }
    write_json(OUT_W_JSON, payload)
    return payload


def rate_sigma(rate: float, events: int) -> float:
    return rate / math.sqrt(events) if events > 0 else float("nan")


def build_metric_rows(mass: dict[str, Any], fix5: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def add(metric: str, mass_value: float | int | str | None, fix_value: float | int | str | None, unit: str = "") -> None:
        ratio = ""
        delta = ""
        try:
            mv = float(mass_value)  # type: ignore[arg-type]
            fv = float(fix_value)  # type: ignore[arg-type]
            delta = mv - fv
            ratio = mv / fv if fv != 0 else ""
        except (TypeError, ValueError):
            pass
        rows.append(
            {
                "metric": metric,
                "Mass_model_511_fullstat_v1": mass_value,
                "fix5_fullstat_v2_exactpos_m50000_s260613": fix_value,
                "delta_mass_minus_fix5": delta,
                "ratio_mass_over_fix5": ratio,
                "unit": unit,
            }
        )

    add("W2 prompt final rate", mass["prompt_cps"], fix5["prompt_cps"], "cps")
    add("W2 delayed final rate", mass["delayed_cps"], fix5["delayed_cps"], "cps")
    add("W2 total background", mass["B_cps"], fix5["B_cps"], "cps")
    add("W2 background sigma", mass["B_sigma_cps"], fix5["B_sigma_cps"], "cps")
    add("W2 signal at 1e-4", mass["signal_cps"], fix5["signal_cps"], "cps")
    add("20-day Z at 1e-4", mass["Z20d"], fix5["Z20d"], "")
    add("20-day 3-sigma flux", mass["F3_20d_ph_cm2_s"], fix5["F3_20d_ph_cm2_s"], "ph cm^-2 s^-1")
    add("W/collimator selected delayed rate", mass["w_activation_cps"], fix5["w_activation_cps"], "cps")
    add("W/collimator fraction of delayed selected rate", mass["w_activation_fraction_of_delayed_selected_rate"], fix5["w_activation_fraction_of_delayed_selected_rate"], "")
    return rows


def write_metric_csv(rows: list[dict[str, Any]]) -> None:
    fields = [
        "metric",
        "Mass_model_511_fullstat_v1",
        "fix5_fullstat_v2_exactpos_m50000_s260613",
        "delta_mass_minus_fix5",
        "ratio_mass_over_fix5",
        "unit",
    ]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def build_review() -> dict[str, Any]:
    mass_step05 = load_json(MASS_STEP05_SUMMARY)
    mass_step06 = load_json(MASS_STEP06_SUMMARY)
    mass_step07 = load_json(MASS_STEP07_SUMMARY)
    mass_step08 = load_json(MASS_STEP08_SUMMARY)
    mass_delayed_source = load_json(MASS_DELAYED_SOURCE_SUMMARY)
    mass_transport_manifest = load_json(MASS_TRANSPORT_MANIFEST)
    mass_transport = (mass_transport_manifest.get("transports") or [{}])[0]
    fix5 = load_json(FIX5_PROMOTION_DECISION)
    w_audit = build_w_activation_audit(mass_step05)

    w2 = mass_step05["windows"]["w2_510p58_511p42"]
    prompt = w2["by_stream"]["prompt"]
    delayed = w2["by_stream"]["delayed"]
    science = w2["by_stream"]["science"]
    phys = w2["physical_reference_flux"]
    step08_checks = mass_step08["checks"]

    prompt_rate = float(prompt["side_compton_fov_pass_rate_s-1"])
    delayed_rate = float(delayed["side_compton_fov_pass_rate_s-1"])
    prompt_events = int(prompt["side_compton_fov_pass_events"])
    delayed_events = int(delayed["side_compton_fov_pass_events"])
    prompt_sigma = rate_sigma(prompt_rate, prompt_events)
    delayed_sigma = rate_sigma(delayed_rate, delayed_events)
    mass_b_sigma = math.sqrt(prompt_sigma * prompt_sigma + delayed_sigma * delayed_sigma)
    mass_signal = float(phys["signal_cps_at_reference_flux"])

    mass_metrics = {
        "B_cps": prompt_rate + delayed_rate,
        "B_sigma_cps": mass_b_sigma,
        "B_sigma_method": "quadrature of prompt_cps/sqrt(prompt_selected_events) and delayed_cps/sqrt(delayed_selected_events)",
        "prompt_cps": prompt_rate,
        "prompt_sigma_cps": prompt_sigma,
        "prompt_selected_events": prompt_events,
        "delayed_cps": delayed_rate,
        "delayed_sigma_cps": delayed_sigma,
        "delayed_selected_events": delayed_events,
        "signal_cps": mass_signal,
        "Z20d": float(step08_checks["A_reference_w2_Z20d_time_dependent"]),
        "F3_20d_ph_cm2_s": float(step08_checks["A_reference_w2_flux_3sigma_20d_ph_cm2_s"]),
        "w_activation_cps": float(w_audit["checks"]["w_or_collimator_selected_rate_hz"]),
        "w_activation_selected_events": int(w_audit["checks"]["w_or_collimator_selected_events"]),
        "w_activation_fraction_of_delayed_selected_rate": w_audit["checks"]["w_or_collimator_fraction_of_delayed_selected_rate"],
        "w_activation_dominant_component": w_audit["checks"]["w_or_collimator_is_dominant_component"],
    }

    b_delta = mass_metrics["B_cps"] - float(fix5["B_cps"])
    b_combined_sigma = math.sqrt(mass_metrics["B_sigma_cps"] ** 2 + float(fix5["B_sigma_cps"]) ** 2)
    b_delta_sigma = b_delta / b_combined_sigma if b_combined_sigma > 0 else None
    f3_ratio = mass_metrics["F3_20d_ph_cm2_s"] / float(fix5["F3_20d_ph_cm2_s"])
    z_ratio = mass_metrics["Z20d"] / float(fix5["Z20d"])
    signal_ratio = mass_metrics["signal_cps"] / float(fix5["signal_cps"])

    threshold_evaluation = {
        "fix5_stat_match": {
            "reference_label": FIX5_LABEL,
            "m_pointsource_blocks_required": 50000,
            "seed_required": 260613,
            "delayed_transport_SE_required": 1000000,
            "mass_m_pointsource_blocks": int(mass_delayed_source["n_pointsource_blocks"]),
            "mass_seed": int(mass_delayed_source["seed"]),
            "mass_delayed_transport_SE": int(mass_transport["SE"]),
            "mass_delayed_transport_ID": int(mass_transport["ID"]),
            "status": "PASS"
            if int(mass_delayed_source["n_pointsource_blocks"]) == 50000
            and int(mass_delayed_source["seed"]) == 260613
            and int(mass_transport["SE"]) == 1000000
            and int(mass_transport["ID"]) == 1000000
            else "FAIL",
        },
        "background_change_vs_fix5": {
            "delta_cps": b_delta,
            "combined_sigma_cps": b_combined_sigma,
            "delta_in_combined_sigma": b_delta_sigma,
            "compatible_with_fix5_within_2sigma": abs(b_delta_sigma) <= 2.0 if b_delta_sigma is not None else False,
            "mass_background_higher_than_fix5": b_delta > 0.0,
        },
        "signal_change_vs_fix5": {
            "signal_ratio_mass_over_fix5": signal_ratio,
            "signal_within_5pct_of_fix5": abs(signal_ratio - 1.0) <= 0.05,
        },
        "significance_change_vs_fix5": {
            "Z20d_ratio_mass_over_fix5": z_ratio,
            "F3_ratio_mass_over_fix5": f3_ratio,
            "mass_Z20d_not_worse_than_fix5": mass_metrics["Z20d"] >= float(fix5["Z20d"]),
            "mass_F3_not_worse_than_fix5": mass_metrics["F3_20d_ph_cm2_s"] <= float(fix5["F3_20d_ph_cm2_s"]),
        },
        "w_activation": {
            "rate_decomposition_available": w_audit["status"].startswith("PASS"),
            "dominant_component": mass_metrics["w_activation_dominant_component"],
            "selected_rate_hz": mass_metrics["w_activation_cps"],
            "fraction_of_delayed_selected_rate": mass_metrics["w_activation_fraction_of_delayed_selected_rate"],
        },
    }

    blocking_items: list[str] = []
    if threshold_evaluation["fix5_stat_match"]["status"] != "PASS":
        blocking_items.append("Mass_model_511 fullstat sampling does not match the fix5 M/seed/SE authority.")
    if not threshold_evaluation["w_activation"]["rate_decomposition_available"]:
        blocking_items.append("W/collimator-origin selected W2 delayed decomposition is not closed.")
    if threshold_evaluation["w_activation"]["dominant_component"]:
        blocking_items.append("W/collimator-origin selected W2 delayed component is dominant.")
    if not threshold_evaluation["significance_change_vs_fix5"]["mass_Z20d_not_worse_than_fix5"]:
        blocking_items.append("Mass_model_511 Z20d is lower than fix5.")
    if not threshold_evaluation["significance_change_vs_fix5"]["mass_F3_not_worse_than_fix5"]:
        blocking_items.append("Mass_model_511 20-day 3-sigma flux is higher than fix5.")

    decision = (
        "PASS_MASS_MODEL_511_REPLACES_FIX5"
        if not blocking_items
        else "USER_REVIEW_REQUIRED_MASS_MODEL_511_NOT_AUTO_REPLACEMENT"
    )
    decision_reason = (
        "All automatic replacement checks pass."
        if not blocking_items
        else "Current-geometry full chain is closed with fix5-matched M statistics, but automatic replacement is not supported because "
        + "; ".join(item.rstrip(".") for item in blocking_items)
        + "."
    )

    metric_rows = build_metric_rows(mass_metrics, fix5)
    write_metric_csv(metric_rows)

    payload = {
        "document_type": "mass_model_511_vs_fix5_replacement_review",
        "generated_at_utc": now_utc(),
        "mass_label": MASS_LABEL,
        "fix5_reference_label": FIX5_LABEL,
        "decision": decision,
        "decision_reason": decision_reason,
        "claim_boundary": (
            "Replacement/no-material-effect review over existing current-geometry Mass_model_511 full-stat Step05--Step08 "
            "outputs. This does not rerun Revan; Mass_model_511 P1/P2/P3 replay is tracked separately and is not "
            "applied to the manuscript here."
        ),
        "mass_metrics": mass_metrics,
        "fix5_reference_metrics": {
            key: fix5[key]
            for key in [
                "B_cps",
                "B_sigma_cps",
                "prompt_cps",
                "prompt_sigma_cps",
                "prompt_selected_events",
                "delayed_cps",
                "delayed_sigma_cps",
                "delayed_selected_events",
                "signal_cps",
                "Z20d",
                "F3_20d_ph_cm2_s",
                "w_activation_cps",
                "w_activation_selected_events",
                "w_activation_fraction_of_delayed_selected_rate",
                "w_activation_dominant_component",
            ]
        },
        "comparison_vs_fix5": {
            "B_ratio_mass_over_fix5": mass_metrics["B_cps"] / float(fix5["B_cps"]),
            "B_delta_cps": b_delta,
            "B_delta_combined_sigma": b_delta_sigma,
            "delayed_ratio_mass_over_fix5": mass_metrics["delayed_cps"] / float(fix5["delayed_cps"]),
            "signal_ratio_mass_over_fix5": signal_ratio,
            "Z20d_ratio_mass_over_fix5": z_ratio,
            "F3_ratio_mass_over_fix5": f3_ratio,
        },
        "threshold_evaluation": threshold_evaluation,
        "blocking_items": blocking_items,
        "evidence": {
            "mass_step05_summary": rel(MASS_STEP05_SUMMARY),
            "mass_step06_summary": rel(MASS_STEP06_SUMMARY),
            "mass_step07_summary": rel(MASS_STEP07_SUMMARY),
            "mass_step08_summary": rel(MASS_STEP08_SUMMARY),
            "mass_delayed_source_summary": rel(MASS_DELAYED_SOURCE_SUMMARY),
            "mass_delayed_transport_manifest": rel(MASS_TRANSPORT_MANIFEST),
            "mass_w_activation_selected_w2_audit": rel(OUT_W_JSON),
            "mass_w_activation_selected_w2_events": rel(OUT_W_CSV),
            "mass_model_511_p1_p2_p3_replay": rel(P1P2P3_REPLAY_README),
            "fix5_promotion_decision": rel(FIX5_PROMOTION_DECISION),
            "metrics_csv": rel(OUT_CSV),
        },
        "pending_if_used_for_paper_authority": [
            "Mass_model_511-specific P1/P2/P3 replay is completed separately but is not applied to the manuscript here.",
            "User decision is required before replacing the paper-facing fix5 authority with Mass_model_511 values.",
        ],
    }
    write_json(OUT_JSON, payload)
    write_markdown(payload, metric_rows)
    return payload


def write_markdown(payload: dict[str, Any], metric_rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Mass_model_511 Replacement Review",
        "",
        f"Status: `{payload['decision']}`",
        "",
        payload["decision_reason"],
        "",
        "## Key Comparison",
        "",
        "| metric | Mass_model_511 | fix5 | ratio Mass/fix5 | unit |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for row in metric_rows:
        ratio = row["ratio_mass_over_fix5"]
        ratio_text = "" if ratio == "" else f"{float(ratio):.6g}"
        mass_value = row["Mass_model_511_fullstat_v1"]
        fix_value = row["fix5_fullstat_v2_exactpos_m50000_s260613"]
        if isinstance(mass_value, float):
            mass_text = f"{mass_value:.8g}"
        else:
            mass_text = str(mass_value)
        if isinstance(fix_value, float):
            fix_text = f"{fix_value:.8g}"
        else:
            fix_text = str(fix_value)
        lines.append(f"| {row['metric']} | {mass_text} | {fix_text} | {ratio_text} | {row['unit']} |")

    comparison = payload["comparison_vs_fix5"]
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            f"- M/seed/transport statistics: `{payload['threshold_evaluation']['fix5_stat_match']['status']}`.",
            f"- Background is higher than fix5 by `{comparison['B_delta_cps']:.6g} cps`, which is `{comparison['B_delta_combined_sigma']:.3g}` combined sigma.",
            f"- Signal response is essentially unchanged: Mass/fix5 ratio `{comparison['signal_ratio_mass_over_fix5']:.6g}`.",
            f"- Final 20-day sensitivity is worse than fix5: F3 ratio `{comparison['F3_ratio_mass_over_fix5']:.6g}`, Z ratio `{comparison['Z20d_ratio_mass_over_fix5']:.6g}`.",
            f"- W/collimator-origin selected delayed W2 rate is `{payload['mass_metrics']['w_activation_cps']:.6g} cps` and is not dominant: `{payload['mass_metrics']['w_activation_dominant_component']}`.",
            "",
            "## Evidence",
            "",
        ]
    )
    for key, value in payload["evidence"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Pending", ""])
    for item in payload["pending_if_used_for_paper_authority"]:
        lines.append(f"- {item}")
    lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    payload = build_review()
    print(
        json.dumps(
            {
                "decision": payload["decision"],
                "B_ratio_mass_over_fix5": payload["comparison_vs_fix5"]["B_ratio_mass_over_fix5"],
                "F3_ratio_mass_over_fix5": payload["comparison_vs_fix5"]["F3_ratio_mass_over_fix5"],
                "w_activation_cps": payload["mass_metrics"]["w_activation_cps"],
                "out": rel(OUT_JSON),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if payload["decision"].startswith("PASS") or payload["decision"].startswith("USER_REVIEW_REQUIRED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
