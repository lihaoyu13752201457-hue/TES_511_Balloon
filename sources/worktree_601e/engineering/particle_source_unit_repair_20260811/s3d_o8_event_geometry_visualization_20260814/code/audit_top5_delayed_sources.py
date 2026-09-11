#!/usr/bin/env python3
"""Read-only audit of the five leading S3d-O8 delayed W2 source volumes.

This script launches no transport.  It reconciles the selected-event ledger
with the full day-15 inventory, the partial exact production-origin links, and
raw delayed SIM records.  Raw SIM parsing is limited to already-selected events
from the five leading volumes.

Important semantic separation:

* ``incident_family`` is the activation inventory branch's incident primary;
* ``interacting_particle``/``creator_process`` describe direct isotope creation
  only for exact-linked production rows;
* IA DECA records list products emitted directly by the decaying source ion;
* TES CC HIT ``secondary_particle`` is a particle depositing energy in a TES
  absorber, not an audited boundary-crossing/entry particle.
"""

from __future__ import annotations

import gzip
import importlib.util
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
AUDIT = ROOT / "audit"
INVENTORY = Path(
    "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/"
    "particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/"
    "outputs/02_activation/day15_inventory.csv"
)
EXTRACTOR = ROOT / "code" / "build_prompt_track_ledgers.py"


PARTICLE_NAMES = {
    0: "none",
    1: "gamma",
    2: "e+",
    3: "e-",
    4: "proton",
    5: "anti_proton",
    6: "neutron",
    7: "anti_neutron",
    8: "mu+",
    9: "mu-",
    10: "tau+",
    11: "tau-",
    12: "nu_e",
    13: "anti_nu_e",
    14: "nu_mu",
    15: "anti_nu_mu",
    16: "nu_tau",
    17: "anti_nu_tau",
    18: "deuteron",
    19: "triton",
    20: "He3",
    21: "alpha",
    22: "generic_ion",
    23: "pi+",
    24: "pi0",
    25: "pi-",
}


def particle_name(code: int) -> str:
    if code > 1000:
        return f"ion_Z{code // 1000}_A{code % 1000}"
    return PARTICLE_NAMES.get(code, f"particle_code_{code}")


def load_extractor() -> Any:
    spec = importlib.util.spec_from_file_location("top5_raw_parser", EXTRACTOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {EXTRACTOR}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def neff(weights: pd.Series) -> float:
    total = float(weights.sum())
    sumsq = float(np.square(weights.to_numpy(dtype=float)).sum())
    return total * total / sumsq if sumsq else 0.0


def exact_material_for_volume(frame: pd.DataFrame, volume: str) -> str:
    values = sorted(frame.loc[frame["source_volume"] == volume, "exact_material"].unique())
    if len(values) != 1:
        raise RuntimeError(f"{volume}: expected one exact material, got {values}")
    return values[0]


def top_volumes(delayed: pd.DataFrame) -> list[str]:
    return (
        delayed.groupby("source_volume", sort=False)["w2_rate_cps"]
        .sum()
        .sort_values(ascending=False, kind="mergesort")
        .head(5)
        .index.tolist()
    )


def link_keys(links: pd.DataFrame) -> set[tuple[str, int]]:
    return set(
        zip(
            links["delayed_source_file"].astype(str),
            links["delayed_local_event_id"].astype(int),
        )
    )


def build_volume_and_breakdown(
    delayed: pd.DataFrame,
    points: pd.DataFrame,
    inventory: pd.DataFrame,
    links: pd.DataFrame,
    volumes: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    total_w2 = float(delayed["w2_rate_cps"].sum())
    exact_keys = link_keys(links)
    point_cells = points.drop_duplicates("source_key_id")
    volume_rows: list[dict[str, Any]] = []
    breakdown_rows: list[dict[str, Any]] = []
    origin_rows: list[dict[str, Any]] = []

    for volume_rank, volume in enumerate(volumes, start=1):
        selected = delayed[delayed["source_volume"] == volume].copy()
        material = exact_material_for_volume(delayed, volume)
        selected_total = float(selected["w2_rate_cps"].sum())
        selected_sumw2 = float(np.square(selected["w2_rate_cps"]).sum())
        full_inventory = inventory[inventory["source_volume"] == volume].copy()
        linked_cells = point_cells[point_cells["source_volume"] == volume]
        selected["has_exact_origin"] = [
            (str(path), int(event_id)) in exact_keys
            for path, event_id in zip(selected["source_file"], selected["delayed_local_event_id"])
        ]
        exact_selected = selected[selected["has_exact_origin"]]
        exact_rate = float(exact_selected["w2_rate_cps"].sum())
        volume_rows.append(
            {
                "volume_rank_by_selected_w2": volume_rank,
                "source_volume": volume,
                "exact_material": material,
                "full_inventory_cell_rows": int(len(full_inventory)),
                "full_inventory_day15_activity_Bq": float(full_inventory["day15_activity_Bq"].sum()),
                "full_inventory_production_rate_s_1": float(full_inventory["production_rate_s-1"].sum()),
                "w2_linked_unique_inventory_cells": int(len(linked_cells)),
                "w2_linked_cell_day15_activity_Bq": float(linked_cells["inventory_cell_day15_activity_Bq"].sum()),
                "w2_linked_cell_production_rate_s_1": float(linked_cells["inventory_cell_production_rate_s-1"].sum()),
                "selected_w2_event_rows": int(len(selected)),
                "selected_w2_rate_cps": selected_total,
                "selected_w2_share_of_all_delayed": selected_total / total_w2,
                "selected_w2_sum_weight_sq_cps2": selected_sumw2,
                "selected_w2_event_neff": selected_total * selected_total / selected_sumw2,
                "exact_origin_linked_selected_rows": int(len(exact_selected)),
                "exact_origin_row_coverage": float(len(exact_selected) / len(selected)),
                "exact_origin_linked_w2_rate_cps": exact_rate,
                "exact_origin_w2_rate_coverage": exact_rate / selected_total,
                "activity_denominator_note": (
                    "full inventory sums every unique S3d-O8 day15 inventory cell in the volume; "
                    "W2-linked activity sums only unique cells represented by selected W2 events"
                ),
            }
        )

        grouped = selected.groupby(
            ["source_parent_ZA", "source_isotope", "incident_family"],
            sort=False,
            dropna=False,
        )
        groups: list[dict[str, Any]] = []
        for (za, isotope, family), group in grouped:
            rate = float(group["w2_rate_cps"].sum())
            inv_match = full_inventory[
                (full_inventory["source_parent_ZA"] == int(za))
                & (full_inventory["incident_family"] == family)
                & (full_inventory["excitation_keV"] == float(group["source_excitation_keV"].iloc[0]))
            ]
            if len(inv_match) != 1:
                raise RuntimeError(
                    f"inventory key mismatch {volume} {family} {za}: rows={len(inv_match)}"
                )
            exact_group = group[group["has_exact_origin"]]
            groups.append(
                {
                    "volume_rank_by_selected_w2": volume_rank,
                    "source_volume": volume,
                    "exact_material": material,
                    "source_parent_ZA": int(za),
                    "source_isotope": isotope,
                    "incident_family": family,
                    "incident_family_semantics": (
                        "activation inventory incident-primary branch; not necessarily direct isotope-maker"
                    ),
                    "inventory_day15_activity_Bq": float(inv_match["day15_activity_Bq"].iloc[0]),
                    "inventory_production_rate_s_1": float(inv_match["production_rate_s-1"].iloc[0]),
                    "source_point_count": int(group["source_point_id"].nunique()),
                    "selected_w2_event_rows": int(len(group)),
                    "selected_w2_rate_cps": rate,
                    "selected_w2_share_within_volume": rate / selected_total,
                    "selected_w2_share_of_all_delayed": rate / total_w2,
                    "selected_w2_event_neff": neff(group["w2_rate_cps"]),
                    "exact_origin_linked_rows": int(len(exact_group)),
                    "exact_origin_linked_w2_rate_cps": float(exact_group["w2_rate_cps"].sum()),
                }
            )
        groups.sort(key=lambda row: (-row["selected_w2_rate_cps"], row["source_isotope"], row["incident_family"]))
        for rank, row in enumerate(groups, start=1):
            row["rank_within_volume_by_selected_w2"] = rank
            breakdown_rows.append(row)

        selected_link_rows = links[links["source_volume"] == volume].copy()
        for _, link in selected_link_rows.iterrows():
            event_match = selected[
                (selected["source_file"] == link["delayed_source_file"])
                & (selected["delayed_local_event_id"] == int(link["delayed_local_event_id"]))
            ]
            if len(event_match) != 1:
                raise RuntimeError(
                    f"selected-event match for exact link is not unique: {volume} "
                    f"ID={link['delayed_local_event_id']} rows={len(event_match)}"
                )
            row = link.to_dict()
            row.update(
                {
                    "volume_rank_by_selected_w2": volume_rank,
                    "selected_volume_event_rows": int(len(selected)),
                    "selected_volume_w2_rate_cps": selected_total,
                    "exact_origin_row_coverage_for_volume": float(len(exact_selected) / len(selected)),
                    "exact_origin_w2_rate_coverage_for_volume": exact_rate / selected_total,
                    "production_reaction_descriptor": (
                        f"{link['interacting_particle']} --{link['creator_process']}--> {link['source_isotope']}"
                    ),
                    "selected_event_w2_rate_cps": float(event_match["w2_rate_cps"].iloc[0]),
                    "transport_primary_energy_MeV": float(link["primary_energy_keV"]) / 1000.0,
                    "energy_semantics": (
                        "transport primary initial energy; local interacting-particle energy at production is not recorded"
                    ),
                    "local_production_reaction_energy": "UNKNOWN",
                }
            )
            origin_rows.append(row)

    return (
        pd.DataFrame(volume_rows),
        pd.DataFrame(breakdown_rows),
        pd.DataFrame(origin_rows),
    )


def stream_raw_top5(
    selected: pd.DataFrame,
    extractor: Any,
) -> pd.DataFrame:
    targets_by_file: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    for row in selected.to_dict("records"):
        targets_by_file[str(row["source_file"])][int(row["delayed_local_event_id"])] = row

    output: list[dict[str, Any]] = []
    for file_index, (source_file, targets) in enumerate(sorted(targets_by_file.items()), start=1):
        current_id: int | None = None
        current: dict[str, Any] | None = None
        found: set[int] = set()
        with gzip.open(source_file, "rt", encoding="utf-8", errors="strict") as handle:
            for line_no, raw in enumerate(handle, start=1):
                line = raw.strip()
                if line.startswith("ID "):
                    event_id = int(line.split()[1])
                    current_id = event_id
                    current = {"deca": [], "tes_cc": []} if event_id in targets else None
                    continue
                if line == "SE":
                    if current is not None and current_id is not None:
                        row = targets[current_id]
                        direct = [
                            ia
                            for ia in current["deca"]
                            if int(ia["mother_particle_code"]) == int(row["source_parent_ZA"])
                        ]
                        if not direct:
                            raise RuntimeError(
                                f"no direct source-parent DECA IA for {source_file} ID={current_id}"
                            )
                        emitted = [
                            {
                                "code": int(ia["secondary_particle_code"]),
                                "particle": particle_name(int(ia["secondary_particle_code"])),
                                "energy_keV": float(ia["secondary_energy_keV"]),
                            }
                            for ia in direct
                        ]
                        mobile = [item for item in emitted if item["code"] < 1000]
                        deposits: defaultdict[str, float] = defaultdict(float)
                        processes: set[str] = set()
                        for cc in current["tes_cc"]:
                            deposits[str(cc["secondary_particle"])] += float(cc["edep_keV"])
                            processes.add(
                                f"{cc['secondary_particle']}:{cc['secondary_process']}"
                                f"<-{cc['parent_particle']}:{cc['creator_process']}"
                            )
                        if not deposits:
                            raise RuntimeError(f"no TES CC HIT for selected event {source_file} ID={current_id}")
                        particle_signature = "+".join(sorted(deposits))
                        direct_signature = "+".join(sorted(item["particle"] for item in mobile)) or "none"
                        dominant = max(deposits, key=deposits.get)
                        output.append(
                            {
                                "source_volume": row["source_volume"],
                                "exact_material": row["exact_material"],
                                "source_isotope": row["source_isotope"],
                                "incident_family": row["incident_family"],
                                "source_file": source_file,
                                "local_event_id": current_id,
                                "event_weight_cps": float(row["w2_rate_cps"]),
                                "measured_total_keV": float(row["measured_total_keV"]),
                                "direct_source_decay_products_json": json.dumps(emitted, separators=(",", ":")),
                                "direct_mobile_decay_signature": direct_signature,
                                "tes_deposit_particle_signature": particle_signature,
                                "tes_dominant_raw_edep_particle": dominant,
                                "tes_raw_edep_by_particle_keV_json": json.dumps(
                                    dict(sorted(deposits.items())), separators=(",", ":")
                                ),
                                "tes_raw_edep_total_keV": float(math.fsum(deposits.values())),
                                "tes_cc_process_signatures_json": json.dumps(sorted(processes), separators=(",", ":")),
                                "annihilation_gamma_cascade_supported": any(
                                    "<-e+:annihil" in value for value in processes
                                ),
                                "carrier_mechanism_inference": (
                                    "source beta+ -> positron annihilation gamma -> TES photon interaction/electron deposit"
                                ),
                                "strict_TES_boundary_entry_particle": "UNKNOWN",
                                "strict_entry_unknown_reason": (
                                    "CC HIT is an energy-deposit sample and raw SIM contains no complete boundary-step log"
                                ),
                            }
                        )
                        found.add(current_id)
                    current_id = None
                    current = None
                    continue
                if current is None or current_id is None:
                    continue
                uid = f"top5_delayed__ID{current_id}"
                if line.startswith("IA DECA"):
                    current["deca"].append(
                        extractor.parse_ia(
                            line,
                            event_uid=uid,
                            source_file=source_file,
                            local_id=current_id,
                            line_no=line_no,
                        )
                    )
                elif line.startswith("CC HIT TP_"):
                    current["tes_cc"].append(
                        extractor.parse_cc(
                            line,
                            event_uid=uid,
                            source_file=source_file,
                            local_id=current_id,
                            line_no=line_no,
                            cc_seq=len(current["tes_cc"]) + 1,
                        )
                    )
        missing = sorted(set(targets) - found)
        if missing:
            raise RuntimeError(f"{source_file}: missing {len(missing)} targets, first={missing[:5]}")
        print(
            f"raw read-only audit {file_index}/{len(targets_by_file)}: "
            f"events={len(targets)} file={Path(source_file).name}",
            flush=True,
        )
    result = pd.DataFrame(output)
    return result.sort_values(["source_volume", "incident_family", "local_event_id"])


def particle_summary(events: pd.DataFrame, volumes: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for volume_rank, volume in enumerate(volumes, start=1):
        frame = events[events["source_volume"] == volume]
        volume_rate = float(frame["event_weight_cps"].sum())
        for dimension, column in [
            ("direct_mobile_decay_signature", "direct_mobile_decay_signature"),
            ("tes_deposit_particle_signature", "tes_deposit_particle_signature"),
            ("tes_dominant_raw_edep_particle", "tes_dominant_raw_edep_particle"),
        ]:
            grouped = []
            for value, group in frame.groupby(column, sort=False, dropna=False):
                rate = float(group["event_weight_cps"].sum())
                grouped.append((str(value), group, rate))
            grouped.sort(key=lambda item: (-item[2], item[0]))
            for rank, (value, group, rate) in enumerate(grouped, start=1):
                rows.append(
                    {
                        "volume_rank_by_selected_w2": volume_rank,
                        "source_volume": volume,
                        "dimension": dimension,
                        "rank_within_volume_dimension": rank,
                        "signature": value,
                        "selected_event_rows": int(len(group)),
                        "selected_w2_rate_cps": rate,
                        "selected_w2_rate_share_within_volume": rate / volume_rate,
                        "selected_event_neff": neff(group["event_weight_cps"]),
                        "semantics": (
                            "direct DECA products are exact IA records; TES deposit particles are exact CC labels; "
                            "neither establishes a TES boundary-entry particle"
                        ),
                    }
                )
    return pd.DataFrame(rows)


def origin_summary(origin: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "volume_rank_by_selected_w2",
        "source_volume",
        "exact_material",
        "source_isotope",
        "incident_family",
        "transport_primary",
        "interacting_particle",
        "creator_process",
        "production_reaction_descriptor",
    ]
    rows: list[dict[str, Any]] = []
    for key, group in origin.groupby(columns, sort=False, dropna=False):
        row = dict(zip(columns, key))
        row.update(
            {
                "exact_linked_selected_rows": int(len(group)),
                "exact_linked_selected_w2_rate_cps": float(group["selected_event_w2_rate_cps"].sum()),
                "transport_primary_energy_MeV_min": float(group["transport_primary_energy_MeV"].min()),
                "transport_primary_energy_MeV_max": float(group["transport_primary_energy_MeV"].max()),
                "transport_primary_energy_MeV_values_json": json.dumps(
                    sorted(float(value) for value in group["transport_primary_energy_MeV"]),
                    separators=(",", ":"),
                ),
                "production_rate_contribution_s_1_sum": float(
                    group["production_rate_contribution_s-1"].sum()
                ),
                "local_interacting_particle_energy": "UNKNOWN",
                "coverage_semantics": (
                    "exact-link subset only; per-volume row and W2-rate coverage are in top5_delayed_volume_audit.csv"
                ),
            }
        )
        rows.append(row)
    result = pd.DataFrame(rows)
    return result.sort_values(
        ["volume_rank_by_selected_w2", "exact_linked_selected_w2_rate_cps", "production_reaction_descriptor"],
        ascending=[True, False, True],
    )


def main() -> None:
    delayed = pd.read_csv(DATA / "delayed_selected_event_ledger.csv")
    points = pd.read_csv(DATA / "delayed_source_point_ledger.csv")
    links = pd.read_csv(DATA / "delayed_partial_production_origin_links.csv")
    inventory = pd.read_csv(INVENTORY)
    inventory = inventory[inventory["geometry"] == "S3d_O8"].copy()
    key = ["incident_family", "source_volume", "source_parent_ZA", "excitation_keV"]
    if inventory.duplicated(key).any():
        raise RuntimeError("full S3d-O8 inventory is not unique at expected cell grain")

    volumes = top_volumes(delayed)
    volume_table, breakdown, origin = build_volume_and_breakdown(
        delayed, points, inventory, links, volumes
    )
    top5_selected = delayed[delayed["source_volume"].isin(volumes)].copy()
    raw_events = stream_raw_top5(top5_selected, load_extractor())
    particle_table = particle_summary(raw_events, volumes)
    origin_aggregate = origin_summary(origin)

    volume_path = DATA / "top5_delayed_volume_audit.csv"
    breakdown_path = DATA / "top5_delayed_isotope_family_breakdown.csv"
    origin_path = DATA / "top5_delayed_exact_origin_links.csv"
    origin_summary_path = DATA / "top5_delayed_exact_origin_summary.csv"
    event_path = DATA / "top5_delayed_decay_tes_event_proxy.csv"
    particle_path = DATA / "top5_delayed_decay_tes_particle_summary.csv"
    volume_table.to_csv(volume_path, index=False)
    breakdown.to_csv(breakdown_path, index=False)
    origin.to_csv(origin_path, index=False)
    origin_aggregate.to_csv(origin_summary_path, index=False)
    raw_events.to_csv(event_path, index=False)
    particle_table.to_csv(particle_path, index=False)

    audit = {
        "status": "PASS_READ_ONLY_TOP5_DELAYED_AUDIT",
        "authorities": {
            "selected_event_ledger": str((DATA / "delayed_selected_event_ledger.csv").resolve()),
            "source_point_ledger": str((DATA / "delayed_source_point_ledger.csv").resolve()),
            "partial_exact_origin_links": str((DATA / "delayed_partial_production_origin_links.csv").resolve()),
            "full_day15_inventory": str(INVENTORY),
            "raw_SIM_files": sorted(top5_selected["source_file"].unique().tolist()),
        },
        "top5_volumes": volumes,
        "checks": {
            "full_inventory_expected_grain_unique": True,
            "top5_selected_rows": int(len(top5_selected)),
            "raw_selected_events_recovered": int(len(raw_events)),
            "all_raw_events_have_direct_source_parent_DECA": True,
            "all_raw_events_have_TES_CC_deposit": True,
            "all_top5_events_direct_mobile_decay_signature_eplus_nu_e": bool(
                (raw_events["direct_mobile_decay_signature"] == "e++nu_e").all()
            ),
            "all_top5_events_TES_deposit_signature_electron_gamma": bool(
                (raw_events["tes_deposit_particle_signature"] == "e-+gamma").all()
            ),
            "all_top5_events_annihilation_gamma_cascade_supported": bool(
                raw_events["annihilation_gamma_cascade_supported"].all()
            ),
            "top5_TES_raw_edep_total_keV_min": float(raw_events["tes_raw_edep_total_keV"].min()),
            "top5_TES_raw_edep_total_keV_max": float(raw_events["tes_raw_edep_total_keV"].max()),
            "strict_TES_boundary_entry_particle_closed": False,
            "strict_entry_status": "UNKNOWN",
            "strict_entry_reason": (
                "Raw CC HIT records are deposit samples, not complete Geant4 boundary steps. "
                "The depositing particle and direct decay products are auditable proxies."
            ),
        },
        "semantic_gates": {
            "incident_family": (
                "FACT: activation inventory incident-primary branch; it may differ from the particle "
                "directly creating the isotope"
            ),
            "interacting_particle_creator_process": (
                "FACT only for exact-linked production rows; exact links cover a weighted fraction "
                "reported per volume"
            ),
            "transport_primary_energy": (
                "FACT: initial primary energy; not local production-interaction energy"
            ),
            "local_production_interaction_energy": "UNKNOWN: absent from link schema",
            "direct_decay_products": "FACT from source-parent IA DECA nodes in selected raw SIM",
            "TES_deposit_particle": "FACT from TP_* CC HIT labels",
            "TES_boundary_entry_particle": "UNKNOWN",
        },
        "output_columns_for_citation": {
            "volume_table": [
                "full_inventory_day15_activity_Bq",
                "w2_linked_cell_day15_activity_Bq",
                "selected_w2_rate_cps",
                "selected_w2_share_of_all_delayed",
                "selected_w2_event_neff",
                "exact_origin_row_coverage",
                "exact_origin_w2_rate_coverage",
            ],
            "breakdown": [
                "source_isotope",
                "incident_family",
                "inventory_day15_activity_Bq",
                "selected_w2_rate_cps",
                "selected_w2_share_within_volume",
                "selected_w2_event_neff",
            ],
            "origin": [
                "interacting_particle",
                "creator_process",
                "production_reaction_descriptor",
                "transport_primary_energy_MeV",
                "local_production_reaction_energy",
            ],
            "origin_summary": [
                "source_isotope",
                "incident_family",
                "interacting_particle",
                "creator_process",
                "exact_linked_selected_w2_rate_cps",
                "transport_primary_energy_MeV_min",
                "transport_primary_energy_MeV_max",
                "local_interacting_particle_energy",
            ],
            "decay_TES_proxy": [
                "direct_source_decay_products_json",
                "tes_deposit_particle_signature",
                "tes_raw_edep_by_particle_keV_json",
                "strict_TES_boundary_entry_particle",
            ],
        },
    }
    audit_path = AUDIT / "top5_delayed_sources_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    assert len(raw_events) == len(top5_selected) == 205
    assert set(volume_table["source_volume"]) == set(volumes)
    assert (raw_events["strict_TES_boundary_entry_particle"] == "UNKNOWN").all()
    for path in [
        volume_path,
        breakdown_path,
        origin_path,
        origin_summary_path,
        event_path,
        particle_path,
        audit_path,
    ]:
        print(path, flush=True)


if __name__ == "__main__":
    main()
