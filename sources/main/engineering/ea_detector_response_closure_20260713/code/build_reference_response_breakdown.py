#!/usr/bin/env python3
"""Build the response-convolved Mass_model_511 reference-background breakdown."""

from __future__ import annotations

import csv
import importlib.util
import json
import math
import pickle
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parents[1]
CLOSURE_SCRIPT = Path(__file__).resolve().with_name("build_o8_energy_response_closure.py")
CLOSURE_SUMMARY = PACKAGE / "data/o8_energy_response_closure_summary.json"
LEGACY_BREAKDOWN = (
    ROOT
    / "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712"
    / "data/reference_baseline_background_breakdown.json"
)
DELAYED_EVENTS = (
    ROOT
    / "engineering/Mass_model_511_nearfield_migration_20260701/14_replacement_review_20260703"
    / "mass_model_511_w_activation_selected_w2_events.csv"
)
OUTPUT = PACKAGE / "data/reference_response_background_breakdown.json"


class BreakdownError(RuntimeError):
    pass


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_closure() -> Any:
    spec = importlib.util.spec_from_file_location("reference_response_closure", CLOSURE_SCRIPT)
    if spec is None or spec.loader is None:
        raise BreakdownError(f"cannot import {CLOSURE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def selected_delayed_rows(closure: Any) -> list[dict[str, str]]:
    cat = closure.compact_event_catalog(closure.REFERENCE_CATALOG, "reference_breakdown")
    _hits, totals, _multiplicity = closure.measured_hits(
        cat,
        closure.PRIMARY_RESPONSE_SEED,
        apply_response=True,
        apply_threshold=True,
    )
    selected = (
        (cat.stream == "delayed")
        & (totals >= closure.WINDOWS["w2_510p58_511p42"][0])
        & (totals < closure.WINDOWS["w2_510p58_511p42"][1])
        & (cat.active_keV < closure.ACTIVE_VETO_THRESHOLD_KEV)
    )
    selected_full_indices = {int(cat.event_id[index]) for index in np.flatnonzero(selected)}
    with closure.REFERENCE_CATALOG.open("rb") as handle:
        raw = pickle.load(handle)
    selected_local_ids = {int(raw["local_id"][index]) for index in selected_full_indices}
    with DELAYED_EVENTS.open("r", encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if int(row["local_id"]) in selected_local_ids]
    if len(rows) != len(selected_local_ids):
        raise BreakdownError(
            f"delayed-event provenance matched {len(rows)}/{len(selected_local_ids)} selected records"
        )
    return rows


def main() -> int:
    for path in (CLOSURE_SUMMARY, LEGACY_BREAKDOWN, DELAYED_EVENTS):
        if not path.is_file():
            raise BreakdownError(f"missing input: {path}")
    closure = load_closure()
    summary = load_json(CLOSURE_SUMMARY)
    if summary.get("status") != "PASS_O8_EVENT_LEVEL_420EV_FWHM_ENERGY_RESPONSE_CLOSURE":
        raise BreakdownError(f"energy-response closure is not PASS: {summary.get('status')}")
    legacy = load_json(LEGACY_BREAKDOWN)
    primary = summary["primary_authority"]
    selection = primary["reference_catalog_selection"]["windows"]["w2_510p58_511p42"]
    step05 = primary["reference_step05"]["windows"]["w2_510p58_511p42"]
    mission = primary["reference_mission_fold"]
    by = selection["by_stream"]
    prompt = by["prompt"]
    delayed = by["delayed"]
    prompt_rows: list[dict[str, Any]] = []
    for particle, record in selection["prompt_final_by_tag"].items():
        events = int(record["events"])
        if events <= 0:
            continue
        rate = float(record["rate_cps"])
        weight = float(record["event_weight_cps"])
        prompt_rows.append(
            {
                "particle": particle,
                "events": events,
                "rate_cps": rate,
                "mc_sigma_cps": math.sqrt(events) * weight,
                "fraction_of_prompt": rate / float(prompt["side_compton_fov_pass_rate_cps"]),
            }
        )
    prompt_rows.sort(key=lambda row: float(row["rate_cps"]), reverse=True)

    delayed_rows = selected_delayed_rows(closure)
    event_weight = float(delayed["side_compton_fov_pass_rate_cps"]) / int(
        delayed["side_compton_fov_pass_events"]
    )
    nuclide_names = {29061: "Cu-61", 29062: "Cu-62", 29064: "Cu-64"}
    nuclide_counts = Counter(int(row["ZA"]) for row in delayed_rows)
    delayed_nuclides = [
        {
            "ZA": za,
            "nuclide": nuclide_names.get(za, str(za)),
            "events": count,
            "rate_cps": count * event_weight,
            "fraction_of_delayed": count / len(delayed_rows),
        }
        for za, count in sorted(nuclide_counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    volume_counts = Counter(row["VN"] for row in delayed_rows)
    delayed_volumes = [
        {
            "source_volume": volume,
            "events": count,
            "rate_cps": count * event_weight,
            "fraction_of_delayed": count / len(delayed_rows),
        }
        for volume, count in sorted(volume_counts.items(), key=lambda item: (-item[1], item[0]))
    ]

    prompt_rate = float(prompt["side_compton_fov_pass_rate_cps"])
    delayed_rate = float(delayed["side_compton_fov_pass_rate_cps"])
    total_rate = prompt_rate + delayed_rate
    prompt_sigma = float(prompt["side_compton_fov_pass_rate_stat_sigma_cps"])
    delayed_sigma = float(delayed["side_compton_fov_pass_rate_stat_sigma_cps"])
    payload = {
        "status": "PASS_REFERENCE_RESPONSE_BACKGROUND_BREAKDOWN",
        "response_seed": closure.PRIMARY_RESPONSE_SEED,
        "response_model": primary["step05"]["response_model"],
        "selection": {
            "window_keV": list(closure.WINDOWS["w2_510p58_511p42"]),
            "active_veto_threshold_keV": closure.ACTIVE_VETO_THRESHOLD_KEV,
            "side_compton_fov_reject_policy": "keep",
        },
        "reference_baseline": {
            "prompt": {
                "events": int(prompt["side_compton_fov_pass_events"]),
                "rate_cps": prompt_rate,
                "mc_sigma_cps": prompt_sigma,
            },
            "delayed": {
                "events": int(delayed["side_compton_fov_pass_events"]),
                "rate_cps": delayed_rate,
                "mc_sigma_cps": delayed_sigma,
            },
            "total": {
                "events": int(prompt["side_compton_fov_pass_events"])
                + int(delayed["side_compton_fov_pass_events"]),
                "rate_cps": total_rate,
                "mc_sigma_cps": math.hypot(prompt_sigma, delayed_sigma),
            },
            "prompt_fraction": prompt_rate / total_rate,
            "delayed_fraction": delayed_rate / total_rate,
            "signal_cps_at_reference_flux": step05["physical_reference_flux"][
                "signal_cps_at_reference_flux"
            ],
            "mission": {
                "Z20d": mission["Z20d"],
                "F3_20d_ph_cm2_s": mission["flux_3sigma_20d_ph_cm2_s"],
            },
        },
        "prompt_particles": prompt_rows,
        "delayed_inventory": legacy["delayed_inventory"],
        "delayed_selected_nuclides": delayed_nuclides,
        "delayed_selected_source_volumes": delayed_volumes,
        "inputs": {
            "energy_response_closure": rel(CLOSURE_SUMMARY),
            "legacy_inventory_authority": rel(LEGACY_BREAKDOWN),
            "delayed_event_provenance": rel(DELAYED_EVENTS),
        },
        "claim_boundary": (
            "Response-convolved reference-geometry detector-selected rates and origin "
            "breakdown. The atmospheric-511 sidecar is not part of this reference branch."
        ),
    }
    if sum(int(row["events"]) for row in delayed_nuclides) != int(
        delayed["side_compton_fov_pass_events"]
    ):
        raise BreakdownError("delayed nuclide count does not close")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "output": rel(OUTPUT)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
