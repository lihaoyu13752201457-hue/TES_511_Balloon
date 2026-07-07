#!/usr/bin/env python3
"""Fast ingress/veto audit using final-candidate atmospheric 511 metadata.

This complements ``build_ingress_veto_audit.py``.  It keeps the exact current
geo-opt e+/n W2 raw->active->final event extraction, but avoids rescanning all
3M atmospheric-511 events for the atmospheric cutflow.  For atmospheric 511,
the vetted P2 replay summary supplies raw/active/final counts and rates, while
this script extracts ingress metadata only for the final W2 candidate IDs.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
SLOW_SCRIPT = WORK / "build_ingress_veto_audit.py"


def load_slow_module():
    spec = importlib.util.spec_from_file_location("ingress_veto_slow_helpers", SLOW_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SLOW_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    m = load_slow_module()
    step05 = m.load_step05_module()
    disk = step05.side_entry_disk()
    cat = m.load_current_catalog()
    material_map = m.load_material_map()

    veto_summaries: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    for family in ("eplus", "n"):
        summary, rows = m.summarize_current_prompt_family(
            cat,
            step05,
            disk,
            family,
            "w2_510p58_511p42",
            *m.WINDOWS["w2_510p58_511p42"],
        )
        veto_summaries.append(summary)
        event_rows.extend(rows)

    p2 = m.load_json(m.P2_ATM511_SUMMARY)
    w2 = p2["windows"]["w2_510p58_511p42"]
    raw = int(w2["raw_events"])
    active = int(w2["active_veto_pass_events"])
    final_ids = [int(x) for x in w2["final_event_ids"]]
    final = int(w2["side_compton_fov_pass_events"])
    obs = raw / float(w2["raw_rate_per_unit_flux_cps_per_ph_cm2_s"])
    atm_summary = {
        "family": "atm511",
        "window": "w2_510p58_511p42",
        "generated_events": int(p2["catalog"]["generated_events"]),
        "observation_time_s": obs,
        "raw_events": raw,
        "active_veto_pass_events": active,
        "side_compton_fov_pass_events": final,
        "raw_rate_s-1_per_unit_flux": float(w2["raw_rate_per_unit_flux_cps_per_ph_cm2_s"]),
        "active_veto_pass_rate_s-1_per_unit_flux": float(w2["active_rate_per_unit_flux_cps_per_ph_cm2_s"]),
        "side_compton_fov_pass_rate_s-1_per_unit_flux": float(w2["final_rate_per_unit_flux_cps_per_ph_cm2_s"]),
        "active_veto_rejection_fraction_vs_raw_count": 1.0 - active / raw if raw else None,
        "side_compton_fov_rejection_fraction_vs_active_count": 1.0 - final / active if active else None,
        "final_survival_fraction_vs_raw_count": final / raw if raw else None,
        "side_compton_class_counts": w2["side_compton_class_counts"],
        "ingress_metadata_scope": "side_compton_fov_pass final candidates only",
    }
    veto_summaries.append(atm_summary)

    # Atmospheric ingress metadata only for the already-vetted final W2 event IDs.
    targets = {str(m.P2_ATM511_SIM): set(final_ids)}
    atm_metadata = m.collect_selected_event_metadata(targets)
    final_energy = {int(eid): float(en) for eid, en in zip(final_ids, w2["final_energies_keV"])}
    final_bgo = {int(eid): float(en) for eid, en in zip(final_ids, w2["final_bgo_keV"])}
    for eid in final_ids:
        meta = atm_metadata[(m.rel(m.P2_ATM511_SIM), eid)]
        init = meta.get("init") or {}
        row = {
            "family": "atm511",
            "window": "w2_510p58_511p42",
            "source_file": m.rel(m.P2_ATM511_SIM),
            "local_id": eid,
            # Ingress rows for atm511 are final-candidate scoped; the global
            # raw/active/final cutflow is reported in veto_efficiency_summary.*.
            "stage_raw": False,
            "stage_active_veto_pass": False,
            "stage_side_compton_fov_pass": True,
            "tes_total_keV": final_energy.get(eid),
            "active_veto_keV": final_bgo.get(eid),
            "rate_s-1_per_unit_flux": float(w2["final_rate_per_unit_flux_cps_per_ph_cm2_s"]) / max(1, final),
            "side_compton_class": "final_pass_from_p2_replay",
            "entry_surface_proxy": meta.get("entry_surface_proxy"),
            "entry_region_proxy": meta.get("entry_region_proxy"),
            "entry_phi_deg_local": meta.get("entry_phi_deg_local"),
            "entry_local_x_cm": meta.get("entry_local_x_cm"),
            "entry_local_y_cm": meta.get("entry_local_y_cm"),
            "entry_local_z_cm": meta.get("entry_local_z_cm"),
            "init_x_cm": init.get("init_x_cm"),
            "init_y_cm": init.get("init_y_cm"),
            "init_z_cm": init.get("init_z_cm"),
            "dir_x": init.get("dir_x"),
            "dir_y": init.get("dir_y"),
            "dir_z": init.get("dir_z"),
            "theta_from_global_plus_z_deg": init.get("theta_from_global_plus_z_deg"),
            "init_energy_keV": init.get("init_energy_keV"),
            "first_hit_volume": meta.get("first_hit_volume"),
            "first_hit_category": meta.get("first_hit_category"),
            "first_hit_x_cm": meta.get("first_hit_x_cm"),
            "first_hit_y_cm": meta.get("first_hit_y_cm"),
            "first_hit_z_cm": meta.get("first_hit_z_cm"),
        }
        event_rows.append(row)

    ingress_rows = m.aggregate_ingress(event_rows)
    ingress_event_stage_rows = m.build_ingress_event_stage_rows(event_rows, material_map)
    veto_rows = m.build_veto_rows(veto_summaries)
    veto_region_rows = m.build_veto_by_ingress_region(event_rows)
    side_class_rows = m.build_side_class_rows(event_rows)

    m.write_csv(
        WORK / "ingress_summary.csv",
        ingress_event_stage_rows,
        [
            "source_family",
            "window",
            "stage",
            "event_count",
            "rate_or_transfer",
            "rate_units",
            "source_theta_bin",
            "source_phi_bin",
            "first_recorded_volume",
            "first_recorded_material",
            "entry_region",
            "first_recorded_x_cm",
            "first_recorded_y_cm",
            "first_recorded_z_cm",
            "tes_energy_keV",
            "active_veto_energy_keV",
            "side_compton_class",
            "entry_surface_proxy",
            "entry_region_proxy",
            "entry_phi_deg_local",
            "source_file",
            "local_id",
            "init_x_cm",
            "init_y_cm",
            "init_z_cm",
            "dir_x",
            "dir_y",
            "dir_z",
            "init_energy_keV",
        ],
    )
    m.write_csv(
        WORK / "ingress_aggregate_summary.csv",
        ingress_rows,
        ["family", "window", "stage", "group_by", "group_value", "events", "fraction_of_stage"],
    )
    m.write_json(
        WORK / "ingress_summary.json",
        {
            "status": "PASS_FAST_INGRESS_AUDIT_CURRENT_GEO_OPT",
            "generated_at_utc": m.now_utc(),
            "inputs": {
                "step05_cache": m.rel(m.STEP05_CACHE),
                "atm511_summary": m.rel(m.P2_ATM511_SUMMARY),
                "atm511_sim_for_final_candidate_metadata": m.rel(m.P2_ATM511_SIM),
                "step05_algorithm": m.rel(m.STEP05_SCRIPT),
                "side_entry_bridge": m.rel(m.STEP09_BRIDGE),
            },
            "method": {
                "window": "w2_510p58_511p42",
                "active_threshold_keV": m.ACTIVE_VETO_THRESHOLD_KEV,
                "entry_proxy": "IA INIT ray intersection with current geo-opt outer envelope in instrument-local coordinates.",
                "entry_proxy_limits": "Not a Geant4 boundary scorer; outer envelope proxy ignores local cutouts and support reliefs.",
                "atm511_ingress_scope": "final W2 side_compton_fov_pass candidates only; atm511 raw/active cutflow is from P2 replay summary.",
            },
            "aggregate_rows": ingress_rows,
            "event_stage_rows": ingress_event_stage_rows,
            "event_rows": event_rows,
        },
    )
    m.write_csv(
        WORK / "veto_efficiency_summary.csv",
        veto_rows,
        [
            "family",
            "window",
            "raw_events",
            "active_veto_pass_events",
            "side_compton_fov_pass_events",
            "raw_rate",
            "active_veto_pass_rate",
            "side_compton_fov_pass_rate",
            "active_veto_rejection_fraction_count",
            "compton_fov_rejection_fraction_vs_active_count",
            "total_rejection_fraction_count",
            "active_veto_rejection_fraction_rate",
            "compton_fov_rejection_fraction_vs_active_rate",
            "total_rejection_fraction_rate",
            "final_survival_fraction_vs_raw_rate",
            "side_compton_class_counts_json",
            "rate_units",
        ],
    )
    m.write_csv(
        WORK / "veto_efficiency_by_source_window_stage.csv",
        veto_rows,
        [
            "family",
            "window",
            "raw_events",
            "active_veto_pass_events",
            "side_compton_fov_pass_events",
            "raw_rate",
            "active_veto_pass_rate",
            "side_compton_fov_pass_rate",
            "active_veto_rejection_fraction_count",
            "compton_fov_rejection_fraction_vs_active_count",
            "total_rejection_fraction_count",
            "active_veto_rejection_fraction_rate",
            "compton_fov_rejection_fraction_vs_active_rate",
            "total_rejection_fraction_rate",
            "final_survival_fraction_vs_raw_rate",
            "side_compton_class_counts_json",
            "rate_units",
        ],
    )
    m.write_csv(
        WORK / "veto_efficiency_by_ingress_region.csv",
        veto_region_rows,
        [
            "family",
            "window",
            "entry_region",
            "raw_events",
            "active_veto_pass_events",
            "side_compton_fov_pass_events",
            "raw_rate",
            "active_veto_pass_rate",
            "side_compton_fov_pass_rate",
            "active_veto_rejection_fraction_count",
            "compton_fov_rejection_fraction_vs_active_count",
            "total_rejection_fraction_count",
            "active_veto_rejection_fraction_rate",
            "compton_fov_rejection_fraction_vs_active_rate",
            "total_rejection_fraction_rate",
        ],
    )
    m.write_csv(
        WORK / "side_compton_class_counts.csv",
        side_class_rows,
        ["family", "window", "side_compton_class", "events", "rate", "survives_reject_policy_keep"],
    )
    m.write_json(
        WORK / "veto_efficiency_summary.json",
        {
            "status": "PASS_FAST_VETO_EFFICIENCY_AUDIT_CURRENT_GEO_OPT",
            "generated_at_utc": m.now_utc(),
            "method": {
                "active_threshold_keV": m.ACTIVE_VETO_THRESHOLD_KEV,
                "active_volume_rule": "CsI/BGO/ACTIVE_SHIELD/CEBR3 plus GeoOpt_S1_PlasticFullWrap* for current geo-opt audit.",
                "compton_fov_algorithm": m.rel(m.STEP05_SCRIPT),
                "side_entry_bridge": m.rel(m.STEP09_BRIDGE),
                "atm511_cutflow_source": m.rel(m.P2_ATM511_SUMMARY),
            },
            "summaries": veto_summaries,
            "csv_rows": veto_rows,
            "by_ingress_region_rows": veto_region_rows,
            "side_compton_class_rows": side_class_rows,
        },
    )
    m.write_markdown(veto_rows, ingress_rows, event_rows)
    with (WORK / "ingress_summary.md").open("a", encoding="utf-8") as handle:
        handle.write(
            "\n## Fast Audit Caveat\n\n"
            "Atmospheric 511 ingress rows are extracted only for the 95 final W2 "
            "side_compton_fov_pass candidates listed in the P2 replay summary. "
            "The atmospheric raw/active/final veto cutflow is still the full P2 "
            "3M replay cutflow from `p2_geo_opt_s1_bpe_w5_atm511_transfer_summary.json`.\n"
        )
    with (WORK / "veto_efficiency_summary.md").open("a", encoding="utf-8") as handle:
        handle.write(
            "\n## Fast Audit Caveat\n\n"
            "Atmospheric 511 veto efficiency is sourced from the full P2 replay "
            "summary. Atmospheric ingress-region breakdown is final-candidate only.\n"
        )
    print(
        json.dumps(
            {
                "status": "PASS_FAST_INGRESS_VETO_AUDIT",
                "veto_rows": len(veto_rows),
                "ingress_event_stage_rows": len(ingress_event_stage_rows),
                "atm511_final_ids": len(final_ids),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
