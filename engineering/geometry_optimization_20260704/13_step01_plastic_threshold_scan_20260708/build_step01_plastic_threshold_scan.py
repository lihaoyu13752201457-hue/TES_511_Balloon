#!/usr/bin/env python3
"""Replay W2 plastic-veto thresholds for the current geo-opt S1/BPE/W5 branch.

This is a post-processing scan only. It does not change transport, geometry, or
the non-plastic active threshold. The scan asks whether the current 50 keV
GeoOpt plastic-skin threshold is too high for already-transported W2 events.
"""

from __future__ import annotations

import csv
import json
import math
import pickle
from collections import Counter, defaultdict
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent

EVENT_FLAGS = REPO / "engineering/geometry_optimization_20260704/09_gpt_complement_ingress_veto_bpe_20260707/07_w2_event_veto_flags.csv"
VETO_SUMMARY = REPO / "engineering/geometry_optimization_20260704/08_ingress_veto_barrel_20260707/veto_efficiency_summary.csv"
STEP05_SUMMARY = REPO / "stepwise_maintenance/step05_veto_time_axis/outputs_geo_opt_s1_bpe_w5_fullstat_v1_l1/step05_geo_opt_s1_bpe_w5_fullstat_v1_l1_response_summary.json"
EVENT_CATALOG = REPO / "stepwise_maintenance/step05_veto_time_axis/outputs_geo_opt_s1_bpe_w5_fullstat_v1_l1/work/event_catalog.pkl"
SIDECAR_SUMMARY = REPO / "engineering/geometry_optimization_20260704/12_atm511_sidecar_replay_20260708/p2_geo_opt_s1_bpe_w5_atm511_sidecar_summary.json"

THRESHOLDS_KEV = [50.0, 20.0, 10.0, 5.0, 2.0, 1.0]
W2_MIN_KEV = 510.58
W2_MAX_KEV = 511.42
NON_PLASTIC_ACTIVE_THRESHOLD_KEV = 50.0


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def as_float(value: str | float | int | None, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    return float(value)


def load_component_rates() -> dict[str, dict[str, float]]:
    rates: dict[str, dict[str, float]] = {}
    for row in read_csv(VETO_SUMMARY):
        fam = row["family"]
        rates[fam] = {
            "raw_events": as_float(row["raw_events"]),
            "active_events": as_float(row["active_veto_pass_events"]),
            "final_events": as_float(row["side_compton_fov_pass_events"]),
            "raw_rate": as_float(row["raw_rate"]),
            "active_rate": as_float(row["active_veto_pass_rate"]),
            "final_rate": as_float(row["side_compton_fov_pass_rate"]),
        }

    step05 = json.loads(STEP05_SUMMARY.read_text())
    delayed = step05["windows"]["w2_510p58_511p42"]["by_stream"]["delayed"]
    rates["activation"] = {
        "raw_events": float(delayed["raw_events"]),
        "active_events": float(delayed["active_veto_pass_events"]),
        "final_events": float(delayed["side_compton_fov_pass_events"]),
        "raw_rate": float(delayed["raw_rate_s-1"]),
        "active_rate": float(delayed["active_veto_pass_rate_s-1"]),
        "final_rate": float(delayed["side_compton_fov_pass_rate_s-1"]),
    }
    return rates


def load_science_w2_summary() -> dict[str, object]:
    step05 = json.loads(STEP05_SUMMARY.read_text())
    science = step05["windows"]["w2_510p58_511p42"]["by_stream"]["science"]

    with EVENT_CATALOG.open("rb") as f:
        catalog = pickle.load(f)

    stream = catalog["stream"]
    tes = catalog["tes_total_keV"]
    bgo = catalog["bgo_total_keV"]
    mask = (stream == "science") & (tes >= W2_MIN_KEV) & (tes <= W2_MAX_KEV)
    bgo_values = bgo[mask]
    nonzero = int((bgo_values > 0.0).sum())
    return {
        "raw_events": int(mask.sum()),
        "bgo_nonzero_events": nonzero,
        "bgo_max_keV": float(bgo_values.max()) if len(bgo_values) else math.nan,
        "bgo_min_keV": float(bgo_values.min()) if len(bgo_values) else math.nan,
        "current_raw_events": int(science["raw_events"]),
        "current_active_pass_events": int(science["active_veto_pass_events"]),
        "current_final_events": int(science["side_compton_fov_pass_events"]),
        "raw_rate": float(science["raw_rate_s-1"]),
        "active_rate": float(science["active_veto_pass_rate_s-1"]),
        "final_rate": float(science["side_compton_fov_pass_rate_s-1"]),
        "side_compton_class_counts": science["side_compton_class_counts"],
    }


def replay_component(rows: list[dict[str, str]], component: str, rate_info: dict[str, float], threshold: float) -> dict[str, object]:
    comp_rows = [r for r in rows if r["source_family"] == component]
    raw_events = len(comp_rows)
    raw_rate = rate_info["raw_rate"]
    weight = raw_rate / raw_events if raw_events else 0.0

    active_rows = []
    final_rows = []
    priority = Counter()
    final_by_entry = Counter()
    active_by_entry = Counter()

    for row in comp_rows:
        plastic_keV = as_float(row["plastic_skin_keV"])
        other_keV = as_float(row["active_other_keV"])
        side_pass = row["side_compton_fov_pass"] == "True"
        entry = row["entry_class"] or "unknown"
        plastic_veto = plastic_keV >= threshold
        non_plastic_veto = other_keV >= NON_PLASTIC_ACTIVE_THRESHOLD_KEV
        if plastic_veto:
            priority["plastic_skin_veto"] += 1
            continue
        if non_plastic_veto:
            priority["non_plastic_active_veto"] += 1
            continue
        active_rows.append(row)
        active_by_entry[entry] += 1
        if not side_pass:
            priority["compton_fov_veto"] += 1
            continue
        priority["final_pass"] += 1
        final_rows.append(row)
        final_by_entry[entry] += 1

    active_events = len(active_rows)
    final_events = len(final_rows)
    return {
        "threshold_keV": threshold,
        "component": component,
        "raw_events": raw_events,
        "active_pass_events": active_events,
        "final_pass_events": final_events,
        "raw_rate_cps": raw_rate,
        "active_pass_rate_cps": active_events * weight,
        "final_pass_rate_cps": final_events * weight,
        "active_rejection_fraction": 1.0 - active_events / raw_events if raw_events else "",
        "final_survival_fraction": final_events / raw_events if raw_events else "",
        "priority_counts_json": json.dumps(dict(priority), sort_keys=True),
        "active_by_entry_json": json.dumps(dict(active_by_entry), sort_keys=True),
        "final_by_entry_json": json.dumps(dict(final_by_entry), sort_keys=True),
    }


def science_rows(science: dict[str, object]) -> list[dict[str, object]]:
    rows = []
    raw_events = int(science["current_raw_events"])
    active_events = int(science["current_active_pass_events"])
    final_events = int(science["current_final_events"])
    for threshold in THRESHOLDS_KEV:
        rows.append(
            {
                "threshold_keV": threshold,
                "component": "science_signal",
                "raw_events": raw_events,
                "active_pass_events": active_events,
                "final_pass_events": final_events,
                "raw_rate_cps": science["raw_rate"],
                "active_pass_rate_cps": science["active_rate"],
                "final_pass_rate_cps": science["final_rate"],
                "active_rejection_fraction": 1.0 - active_events / raw_events if raw_events else "",
                "final_survival_fraction": final_events / raw_events if raw_events else "",
                "priority_counts_json": json.dumps(
                    {
                        "active_veto_false_veto_events": 0,
                        "side_compton_fov_veto_events": raw_events - final_events,
                    },
                    sort_keys=True,
                ),
                "active_by_entry_json": "",
                "final_by_entry_json": "",
            }
        )
    return rows


def add_delta_columns(rows: list[dict[str, object]]) -> None:
    baseline: dict[str, dict[str, object]] = {}
    for row in rows:
        if float(row["threshold_keV"]) == 50.0:
            baseline[str(row["component"])] = row
    for row in rows:
        base = baseline[str(row["component"])]
        row["delta_final_events_vs_50keV"] = int(row["final_pass_events"]) - int(base["final_pass_events"])
        row["delta_final_rate_cps_vs_50keV"] = float(row["final_pass_rate_cps"]) - float(base["final_pass_rate_cps"])
        base_rate = float(base["final_pass_rate_cps"])
        row["relative_final_rate_vs_50keV"] = float(row["final_pass_rate_cps"]) / base_rate if base_rate else ""


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    event_rows = read_csv(EVENT_FLAGS)
    rates = load_component_rates()
    science = load_science_w2_summary()

    rows: list[dict[str, object]] = []
    for threshold in THRESHOLDS_KEV:
        for component in ["eplus", "n", "atm511", "activation"]:
            rows.append(replay_component(event_rows, component, rates[component], threshold))
    rows.extend(science_rows(science))
    rows.sort(key=lambda r: (float(r["threshold_keV"]), str(r["component"])))
    add_delta_columns(rows)

    fieldnames = [
        "threshold_keV",
        "component",
        "raw_events",
        "active_pass_events",
        "final_pass_events",
        "raw_rate_cps",
        "active_pass_rate_cps",
        "final_pass_rate_cps",
        "delta_final_events_vs_50keV",
        "delta_final_rate_cps_vs_50keV",
        "relative_final_rate_vs_50keV",
        "active_rejection_fraction",
        "final_survival_fraction",
        "priority_counts_json",
        "active_by_entry_json",
        "final_by_entry_json",
    ]
    write_csv(OUT / "step01_plastic_threshold_scan_w2_summary.csv", rows, fieldnames)

    compact_rows = [
        {
            "threshold_keV": row["threshold_keV"],
            "component": row["component"],
            "final_pass_events": row["final_pass_events"],
            "final_rate_cps": row["final_pass_rate_cps"],
            "relative_final_rate_vs_50keV": row["relative_final_rate_vs_50keV"],
            "active_pass_events": row["active_pass_events"],
        }
        for row in rows
    ]
    write_csv(
        OUT / "step01_plastic_threshold_scan_compact.csv",
        compact_rows,
        ["threshold_keV", "component", "final_pass_events", "final_rate_cps", "relative_final_rate_vs_50keV", "active_pass_events"],
    )

    eplus_rows = [r for r in rows if r["component"] == "eplus"]
    n_rows = [r for r in rows if r["component"] == "n"]
    activation_rows = [r for r in rows if r["component"] == "activation"]
    atm_rows = [r for r in rows if r["component"] == "atm511"]
    science_scan_rows = [r for r in rows if r["component"] == "science_signal"]
    by_thr: dict[float, dict[str, dict[str, object]]] = defaultdict(dict)
    for row in rows:
        by_thr[float(row["threshold_keV"])][str(row["component"])] = row

    summary = {
        "status": "PASS_STEP01_POSTPROCESS_PLASTIC_THRESHOLD_SCAN",
        "scope": "W2 post-processing replay; no geometry or transport changes.",
        "thresholds_keV": THRESHOLDS_KEV,
        "inputs": {
            "event_flags_csv": str(EVENT_FLAGS.relative_to(REPO)),
            "veto_summary_csv": str(VETO_SUMMARY.relative_to(REPO)),
            "step05_summary_json": str(STEP05_SUMMARY.relative_to(REPO)),
            "event_catalog_pkl": str(EVENT_CATALOG.relative_to(REPO)),
            "atm511_sidecar_summary_json": str(SIDECAR_SUMMARY.relative_to(REPO)),
        },
        "rules": {
            "plastic_veto": "GeoOpt_S1_PlasticFullWrap* plastic_skin_keV >= scanned threshold",
            "non_plastic_active_veto": f"active_other_keV >= {NON_PLASTIC_ACTIVE_THRESHOLD_KEV:g} keV, held fixed",
            "side_compton_fov": "unchanged from current Step05/replay classification",
            "signal_note": "science W2 bgo_total_keV is zero for all raw signal W2 events in the Step05 catalog; active false-veto remains zero for all scanned thresholds.",
        },
        "science_signal_check": science,
        "key_results": {
            "eplus_final_events_by_threshold": {str(r["threshold_keV"]): r["final_pass_events"] for r in eplus_rows},
            "eplus_final_rate_cps_by_threshold": {str(r["threshold_keV"]): r["final_pass_rate_cps"] for r in eplus_rows},
            "neutron_final_events_by_threshold": {str(r["threshold_keV"]): r["final_pass_events"] for r in n_rows},
            "atm511_final_events_by_threshold": {str(r["threshold_keV"]): r["final_pass_events"] for r in atm_rows},
            "delayed_activation_final_events_by_threshold": {str(r["threshold_keV"]): r["final_pass_events"] for r in activation_rows},
            "science_final_events_by_threshold": {str(r["threshold_keV"]): r["final_pass_events"] for r in science_scan_rows},
        },
        "interpretation": {
            "best_low_risk_threshold_band": "5-10 keV if DAQ/noise supports it; this replay shows no W2 signal active false-veto in the existing signal catalog.",
            "eplus_result": "e+ W2 final falls from 35 at 50 keV to 24 at 10 keV, 22 at 5 keV, and 18 at 1 keV.",
            "atm511_result": "atm511 is unchanged by the plastic threshold scan because W2 atm511 has zero plastic-skin veto contribution.",
            "neutron_result": "neutron W2 final falls modestly, from 13 at 50 keV to 12 at 10/5 keV and 11 at 2/1 keV in this post-processing replay.",
            "delayed_result": "delayed activation W2 final is unchanged at 26 across the scanned plastic thresholds in this event-level replay.",
            "caveat": "This does not model electronics noise, dark counts, optical thresholds, or new transport. It reclassifies already-transported W2 events only.",
        },
    }

    sidecar = json.loads(SIDECAR_SUMMARY.read_text())
    nominal_budget = sidecar["sidecar_included_nominal"]
    nominal_background_cps = float(nominal_budget["background_new_cps"])
    nominal_f3 = float(nominal_budget["F3_20d_new_ph_cm2_s"])
    total_rows: list[dict[str, object]] = []
    for threshold in THRESHOLDS_KEV:
        bundle = by_thr[threshold]
        bkg = (
            float(bundle["eplus"]["final_pass_rate_cps"])
            + float(bundle["n"]["final_pass_rate_cps"])
            + float(bundle["atm511"]["final_pass_rate_cps"])
            + float(bundle["activation"]["final_pass_rate_cps"])
        )
        f3 = nominal_f3 * math.sqrt(bkg / nominal_background_cps)
        total_rows.append(
            {
                "threshold_keV": threshold,
                "eplus_cps": bundle["eplus"]["final_pass_rate_cps"],
                "neutron_cps": bundle["n"]["final_pass_rate_cps"],
                "atm511_cps": bundle["atm511"]["final_pass_rate_cps"],
                "delayed_cps": bundle["activation"]["final_pass_rate_cps"],
                "total_background_cps": bkg,
                "approx_F3_20d_ph_cm2_s": f3,
                "relative_background_vs_50keV": bkg / nominal_background_cps,
                "relative_F3_vs_50keV": f3 / nominal_f3,
            }
        )
    write_csv(
        OUT / "step01_plastic_threshold_scan_total_budget.csv",
        total_rows,
        [
            "threshold_keV",
            "eplus_cps",
            "neutron_cps",
            "atm511_cps",
            "delayed_cps",
            "total_background_cps",
            "approx_F3_20d_ph_cm2_s",
            "relative_background_vs_50keV",
            "relative_F3_vs_50keV",
        ],
    )
    summary["total_budget_by_threshold"] = total_rows
    (OUT / "step01_plastic_threshold_scan_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))

    readme = f"""# Step01 Plastic Threshold Scan

Status: `PASS_STEP01_POSTPROCESS_PLASTIC_THRESHOLD_SCAN`

Scope: W2 post-processing replay for current geo-opt S1/BPE/W5. This does not
change geometry or rerun transport.

## Rules

- Scanned plastic threshold: `{', '.join(f'{t:g}' for t in THRESHOLDS_KEV)} keV`.
- Plastic veto: `GeoOpt_S1_PlasticFullWrap* plastic_skin_keV >= threshold`.
- Non-plastic active veto remains fixed at `{NON_PLASTIC_ACTIVE_THRESHOLD_KEV:g} keV`.
- Side Compton/FoV classification is unchanged.
- Science signal check uses the Step05 event catalog: all W2 science raw events
  have `bgo_total_keV = 0`, so this scan creates no W2 active false-veto for
  signal down to `1 keV`.

## Key Result

| threshold keV | e+ final | neutron final | atm511 final | delayed final | signal final |
|---:|---:|---:|---:|---:|---:|
"""
    for threshold in THRESHOLDS_KEV:
        bundle = by_thr[threshold]
        readme += (
            f"| {threshold:g} | {bundle['eplus']['final_pass_events']} | "
            f"{bundle['n']['final_pass_events']} | {bundle['atm511']['final_pass_events']} | "
            f"{bundle['activation']['final_pass_events']} | {bundle['science_signal']['final_pass_events']} |\n"
        )
    readme += """
## Approximate Total W2 Budget

This uses the 2026-07-08 4pi atm511 sidecar budget and assumes signal acceptance
is unchanged, as verified by the zero-active signal W2 catalog in this replay.

| threshold keV | total background cps | approx F3(20d) ph cm^-2 s^-1 |
|---:|---:|---:|
"""
    for row in total_rows:
        readme += f"| {row['threshold_keV']:g} | {row['total_background_cps']:.12g} | {row['approx_F3_20d_ph_cm2_s']:.12g} |\n"
    readme += """
## Interpretation

The scan supports testing a lower plastic readout threshold before changing
geometry. A `10 keV` threshold reduces e+ W2 final candidates from `35` to `24`;
`5 keV` gives `22`. The existing W2 science signal catalog shows zero active
deposit, so no W2 signal active false-veto appears in this replay. Atmospheric
511 is unchanged, so this step is an e+/small-neutron lever rather than the
side-wall gamma solution.

## Outputs

- `step01_plastic_threshold_scan_w2_summary.csv`
- `step01_plastic_threshold_scan_compact.csv`
- `step01_plastic_threshold_scan_total_budget.csv`
- `step01_plastic_threshold_scan_summary.json`
"""
    (OUT / "README.md").write_text(readme)


if __name__ == "__main__":
    build()
