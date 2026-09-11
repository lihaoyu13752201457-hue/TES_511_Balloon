#!/usr/bin/env python3
"""Trace the leading delayed source volumes from DECA to TES deposits.

The script reads only existing ledgers and raw SIM files.  It does not launch
transport.  The five leading source volumes are selected by summed W2 rate,
not by row count.  For their selected events, HTsim type-2 TES records are
matched to explicit TP_* CC pixels, contributor IA origin chains are followed
back to DECA, and TES CC deposits provide an independent final-particle view.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


PACKAGE = Path(__file__).resolve().parents[1]
DATA = PACKAGE / "data"
LEDGER = DATA / "delayed_selected_event_ledger.csv"
EXTRACTOR = PACKAGE / "code/build_prompt_track_ledgers.py"

PARTICLE = {
    0: "none",
    1: "gamma",
    2: "e+",
    3: "e-",
    4: "p",
    5: "mu+",
    6: "mu-",
    12: "neutrino_code12",
    13: "n",
    21: "alpha",
}


def particle_name(code: int) -> str:
    if code >= 10000:
        return f"ion_ZA_{code}"
    return PARTICLE.get(code, f"particle_code_{code}")


def load_extractor() -> Any:
    spec = importlib.util.spec_from_file_location("s3d_o8_prompt_extractor_chain", EXTRACTOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {EXTRACTOR}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"empty output: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def top_volumes(rows: list[dict[str, str]], count: int) -> list[str]:
    rate: defaultdict[str, float] = defaultdict(float)
    for row in rows:
        rate[row["source_volume"]] += float(row["w2_rate_cps"])
    return [name for name, _ in sorted(rate.items(), key=lambda item: (-item[1], item[0]))[:count]]


def stream_targets(
    path: Path,
    targets: dict[int, dict[str, str]],
    extractor: Any,
) -> dict[int, dict[str, Any]]:
    found: dict[int, dict[str, Any]] = {}
    current_id: int | None = None
    current: dict[str, Any] | None = None
    with gzip.open(path, "rt", encoding="utf-8", errors="strict") as handle:
        for line_no, raw in enumerate(handle, 1):
            line = raw.strip()
            if line.startswith("ID "):
                fields = line.split()
                current_id = int(fields[1])
                current = (
                    {"id_second": int(fields[2]), "ia": [], "cc": [], "htsim": []}
                    if current_id in targets
                    else None
                )
                continue
            if line == "SE":
                if current is not None and current_id is not None:
                    found[current_id] = current
                current_id = None
                current = None
                continue
            if current is None or current_id is None:
                continue
            uid = f"delayed_chain__{targets[current_id]['incident_family']}__ID{current_id}"
            if line.startswith("IA "):
                current["ia"].append(
                    extractor.parse_ia(
                        line,
                        event_uid=uid,
                        source_file=str(path),
                        local_id=current_id,
                        line_no=line_no,
                    )
                )
            elif line.startswith("CC HIT "):
                current["cc"].append(
                    extractor.parse_cc(
                        line,
                        event_uid=uid,
                        source_file=str(path),
                        local_id=current_id,
                        line_no=line_no,
                        cc_seq=len(current["cc"]) + 1,
                    )
                )
            elif line.startswith("HTsim "):
                current["htsim"].append(
                    extractor.parse_htsim(
                        line,
                        event_uid=uid,
                        source_file=str(path),
                        local_id=current_id,
                        line_no=line_no,
                        htsim_seq=len(current["htsim"]) + 1,
                    )
                )
    missing = sorted(set(targets) - set(found))
    if missing:
        raise RuntimeError(f"{path}: missing selected IDs {missing[:8]}")
    return found


def match_tes_htsim(
    ht_rows: list[dict[str, Any]],
    pixels: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return type-2 HTsim groups which match explicit TP_* pixel energies."""
    grouped: dict[tuple[float, float, float], dict[str, Any]] = {}
    for row in ht_rows:
        if int(row["detector_type"]) != 2:
            continue
        centre = (
            float(row["world_x_cm"]),
            float(row["world_y_cm"]),
            float(row["world_z_cm"]),
        )
        item = grouped.setdefault(
            centre,
            {"centre": centre, "energy_keV": 0.0, "contributors": set(), "records": 0},
        )
        item["energy_keV"] += float(row["energy_keV"])
        item["contributors"].update(int(value) for value in row["_contributing_ia_ids"])
        item["records"] += 1
    unmatched = set(grouped)
    matched = []
    for uid in sorted(pixels):
        pixel = pixels[uid]
        centre = min(
            unmatched,
            key=lambda key: (
                abs(float(pixel["raw_keV"]) - float(grouped[key]["energy_keV"])),
                (key[0] - float(pixel["deposit_centroid_world_x_cm"])) ** 2
                + (key[1] - float(pixel["deposit_centroid_world_y_cm"])) ** 2
                + (key[2] - float(pixel["deposit_centroid_world_z_cm"])) ** 2,
                key,
            ),
        )
        item = grouped[centre]
        residual = float(pixel["raw_keV"]) - float(item["energy_keV"])
        if abs(residual) > 1.0e-3:
            raise RuntimeError(f"{uid}: HTsim energy residual {residual}")
        matched.append(
            {
                "pixel_uid": uid,
                "energy_keV": item["energy_keV"],
                "contributors": sorted(item["contributors"]),
                "htsim_records": item["records"],
            }
        )
        unmatched.remove(centre)
    return matched


def ancestry_chain(ia_id: int, by_id: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    chain = []
    seen: set[int] = set()
    current = ia_id
    while current:
        if current in seen or current not in by_id:
            raise RuntimeError(f"broken/cyclic IA origin chain at {current}")
        seen.add(current)
        node = by_id[current]
        chain.append(node)
        current = int(node["origin_ia_id"])
    chain.reverse()
    return chain


def signature_from_deca(ia_rows: list[dict[str, Any]], source_za: int) -> tuple[str, str]:
    deca = [
        row
        for row in ia_rows
        if row["process"] == "DECA" and int(row["mother_particle_code"]) == source_za
    ]
    if not deca:
        deca = [row for row in ia_rows if row["process"] == "DECA"]
    emitted = sorted(
        particle_name(int(row["secondary_particle_code"]))
        for row in deca
        if int(row["secondary_particle_code"]) < 10000
    )
    daughters = sorted(
        particle_name(int(row["secondary_particle_code"]))
        for row in deca
        if int(row["secondary_particle_code"]) >= 10000
    )
    return "+".join(emitted) if emitted else "UNKNOWN_NO_NONION_DECA_RECORD", "+".join(daughters)


def delivery_class(branches: set[str], processes: set[str]) -> str:
    if "ANNI" in processes:
        return "DECA_eplus__ANNI_gamma__TES"
    if "gamma" in branches:
        return "DECA_gamma__TES"
    if "e-" in branches and "BREM" in processes:
        return "DECA_eminus__BREM_gamma_or_electron__TES"
    if "e-" in branches:
        return "DECA_eminus__direct_or_scattered_electron__TES"
    if "e+" in branches:
        return "DECA_eplus__ANNI_not_on_saved_TES_contributor_chain"
    return "UNKNOWN_DECA_TO_TES_DELIVERY"


def analyze_event(row: dict[str, str], raw: dict[str, Any], extractor: Any) -> dict[str, Any]:
    if raw["id_second"] != int(row["delayed_local_event_id"]):
        raise RuntimeError("SIM ID columns differ")
    ia_rows = raw["ia"]
    by_id = {int(item["ia_id"]): item for item in ia_rows}
    if len(by_id) != len(ia_rows):
        raise RuntimeError("duplicate IA IDs")
    pixels = extractor.pixel_groups(raw["cc"])
    matched = match_tes_htsim(raw["htsim"], pixels)

    branch_particles: set[str] = set()
    path_processes: set[str] = set()
    path_signatures: set[str] = set()
    entry_particles: set[str] = set()
    contributor_total = 0
    contributor_with_deca = 0
    for item in matched:
        for contributor in item["contributors"]:
            contributor_total += 1
            chain = ancestry_chain(contributor, by_id)
            processes = [str(node["process"]) for node in chain]
            path_processes.update(processes)
            deca_nodes = [node for node in chain if node["process"] == "DECA"]
            if deca_nodes:
                contributor_with_deca += 1
                branch_particles.add(
                    particle_name(int(deca_nodes[0]["secondary_particle_code"]))
                )
            path_signatures.add(">".join(processes))
            detector_nodes = [
                node
                for node in chain
                if int(node["detector_type"]) == 2
                and node["process"] not in {"INIT", "DECA", "ENTR", "ESCP"}
            ]
            if detector_nodes:
                entry_particles.add(
                    particle_name(int(detector_nodes[0]["mother_particle_code"]))
                )

    tes_cc = [item for item in raw["cc"] if str(item["tes_pixel_uid"])]
    deposit_by_particle: defaultdict[str, float] = defaultdict(float)
    deposit_by_process: defaultdict[str, float] = defaultdict(float)
    for item in tes_cc:
        deposit_by_particle[str(item["secondary_particle"])] += float(item["edep_keV"])
        deposit_by_process[
            f"{item['secondary_particle']}:{item['secondary_process']}"
        ] += float(item["edep_keV"])
    raw_total = math.fsum(deposit_by_particle.values())
    if abs(raw_total - 510.99891) > 0.02:
        raise RuntimeError(f"unexpected selected raw TES total {raw_total}")

    source_za = int(row["source_parent_ZA"])
    emission_signature, daughters = signature_from_deca(ia_rows, source_za)
    if contributor_total and contributor_with_deca == contributor_total:
        ancestry_status = "EXACT_ALL_TES_CONTRIBUTORS_REACH_DECA"
    elif contributor_with_deca:
        ancestry_status = "PARTIAL_SOME_TES_CONTRIBUTORS_REACH_DECA"
    else:
        ancestry_status = "UNKNOWN_NO_TES_CONTRIBUTOR_REACHES_DECA"
    entry_status = "EXACT_IA_TES_ENTRY" if entry_particles else "UNKNOWN_NO_TES_INTERACTION_IA"

    return {
        "source_volume": row["source_volume"],
        "exact_material": row["exact_material"],
        "incident_activation_family": row["incident_family"],
        "local_event_id": int(row["delayed_local_event_id"]),
        "source_file": row["source_file"],
        "source_parent_ZA": source_za,
        "source_isotope": row["source_isotope"],
        "event_weight_cps": float(row["w2_rate_cps"]),
        "DECA_emission_signature": emission_signature,
        "DECA_daughter_ions": daughters,
        "TES_delivery_class": delivery_class(branch_particles, path_processes),
        "TES_entry_mother_particles": "+".join(sorted(entry_particles)) if entry_particles else "UNKNOWN",
        "TES_contributor_branch_particles": "+".join(sorted(branch_particles)) if branch_particles else "UNKNOWN",
        "TES_ancestry_processes": "+".join(sorted(path_processes)),
        "TES_ancestry_path_signatures": " | ".join(sorted(path_signatures)),
        "TES_HTsim_matched_pixels": len(matched),
        "TES_HTsim_contributors": contributor_total,
        "TES_HTsim_contributors_reaching_DECA": contributor_with_deca,
        "ancestry_status": ancestry_status,
        "TES_entry_status": entry_status,
        "TES_CC_raw_total_keV": raw_total,
        "TES_CC_deposit_particle_energy_json": json.dumps(
            dict(sorted(deposit_by_particle.items())), separators=(",", ":")
        ),
        "TES_CC_deposit_process_energy_json": json.dumps(
            dict(sorted(deposit_by_process.items())), separators=(",", ":")
        ),
        "evidence_scope": (
            "IA origin chain for matched TES HTsim contributors plus TP_* CC deposits; "
            "CC samples are deposits, not complete boundary-crossing step tracks"
        ),
    }


def event_group_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dimensions = {
        "parent_isotope": "source_isotope",
        "activation_incident_family": "incident_activation_family",
        "DECA_emission_signature": "DECA_emission_signature",
        "TES_delivery_class": "TES_delivery_class",
        "TES_entry_mother_particles": "TES_entry_mother_particles",
        "ancestry_status": "ancestry_status",
    }
    output = []
    for volume in sorted({event["source_volume"] for event in events}):
        volume_events = [event for event in events if event["source_volume"] == volume]
        volume_rate = math.fsum(event["event_weight_cps"] for event in volume_events)
        for dimension, field in dimensions.items():
            grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
            for event in volume_events:
                grouped[str(event[field])].append(event)
            for category, rows in sorted(
                grouped.items(),
                key=lambda item: -math.fsum(row["event_weight_cps"] for row in item[1]),
            ):
                rate = math.fsum(row["event_weight_cps"] for row in rows)
                sumw2 = math.fsum(row["event_weight_cps"] ** 2 for row in rows)
                output.append(
                    {
                        "source_volume": volume,
                        "exact_material": volume_events[0]["exact_material"],
                        "dimension": dimension,
                        "category": category,
                        "metric": "selected_event_W2_rate",
                        "support_events": len(rows),
                        "w2_rate_cps": rate,
                        "fraction_of_volume_W2_rate": rate / volume_rate,
                        "mc_neff": rate * rate / sumw2 if sumw2 else 0.0,
                        "evidence_status": "FACT_FROM_SELECTED_LEDGER_AND_RAW_SIM",
                    }
                )
    return output


def deposit_group_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for volume in sorted({event["source_volume"] for event in events}):
        volume_events = [event for event in events if event["source_volume"] == volume]
        volume_rate = math.fsum(event["event_weight_cps"] for event in volume_events)
        contributions: defaultdict[str, float] = defaultdict(float)
        support: defaultdict[str, int] = defaultdict(int)
        for event in volume_events:
            deposits = json.loads(event["TES_CC_deposit_particle_energy_json"])
            total = math.fsum(float(value) for value in deposits.values())
            for particle, energy in deposits.items():
                contributions[particle] += event["event_weight_cps"] * float(energy) / total
                support[particle] += 1
        for particle, rate_equivalent in sorted(contributions.items(), key=lambda item: -item[1]):
            output.append(
                {
                    "source_volume": volume,
                    "exact_material": volume_events[0]["exact_material"],
                    "dimension": "TES_CC_deposit_particle",
                    "category": particle,
                    "metric": "CC_energy_share_weighted_selected_W2_rate",
                    "support_events": support[particle],
                    "w2_rate_cps": rate_equivalent,
                    "fraction_of_volume_W2_rate": rate_equivalent / volume_rate,
                    "mc_neff": "",
                    "evidence_status": "FACT_FROM_TP_PIXEL_CC_DEPOSITS",
                }
            )
    return output


def volume_overview(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for volume in sorted({event["source_volume"] for event in events}):
        subset = [event for event in events if event["source_volume"] == volume]
        rate = math.fsum(event["event_weight_cps"] for event in subset)
        sumw2 = math.fsum(event["event_weight_cps"] ** 2 for event in subset)
        exact = [
            event
            for event in subset
            if event["ancestry_status"] == "EXACT_ALL_TES_CONTRIBUTORS_REACH_DECA"
        ]
        entry = [event for event in subset if event["TES_entry_status"] == "EXACT_IA_TES_ENTRY"]
        rows.append(
            {
                "source_volume": volume,
                "exact_material": subset[0]["exact_material"],
                "selected_events": len(subset),
                "w2_rate_cps": rate,
                "mc_neff": rate * rate / sumw2,
                "exact_DECA_to_TES_events": len(exact),
                "exact_DECA_to_TES_rate_cps": math.fsum(event["event_weight_cps"] for event in exact),
                "exact_DECA_to_TES_rate_coverage": math.fsum(event["event_weight_cps"] for event in exact) / rate,
                "exact_TES_entry_events": len(entry),
                "exact_TES_entry_rate_coverage": math.fsum(event["event_weight_cps"] for event in entry) / rate,
            }
        )
    rows.sort(key=lambda row: -row["w2_rate_cps"])
    return rows


def run(event_csv: Path, summary_csv: Path, audit_json: Path, note_md: Path, count: int) -> None:
    extractor = load_extractor()
    all_rows = read_csv(LEDGER)
    leaders = top_volumes(all_rows, count)
    selected = [row for row in all_rows if row["source_volume"] in leaders]
    by_path: defaultdict[str, dict[int, dict[str, str]]] = defaultdict(dict)
    for row in selected:
        by_path[row["source_file"]][int(row["delayed_local_event_id"])] = row
    events = []
    for index, (source_file, targets) in enumerate(sorted(by_path.items()), 1):
        raw_events = stream_targets(Path(source_file), targets, extractor)
        for event_id, raw in raw_events.items():
            events.append(analyze_event(targets[event_id], raw, extractor))
        print(f"chain raw scan {index}/{len(by_path)} selected={len(targets)}", flush=True)
    events.sort(key=lambda event: (leaders.index(event["source_volume"]), event["incident_activation_family"], event["local_event_id"]))

    overview = volume_overview(events)
    summary = event_group_rows(events) + deposit_group_rows(events)
    summary.sort(
        key=lambda row: (
            leaders.index(row["source_volume"]),
            row["dimension"],
            -float(row["w2_rate_cps"]),
        )
    )
    total_rate = math.fsum(float(row["w2_rate_cps"]) for row in all_rows)
    selected_rate = math.fsum(event["event_weight_cps"] for event in events)
    exact_rate = math.fsum(
        event["event_weight_cps"]
        for event in events
        if event["ancestry_status"] == "EXACT_ALL_TES_CONTRIBUTORS_REACH_DECA"
    )
    entry_rate = math.fsum(
        event["event_weight_cps"]
        for event in events
        if event["TES_entry_status"] == "EXACT_IA_TES_ENTRY"
    )
    audit = {
        "status": "PASS_DELAYED_TOP5_DECA_TO_TES_CHAIN_AUDIT",
        "selection": {
            "rule": "top five source_volume by summed selected W2 rate",
            "volumes": leaders,
            "selected_events": len(events),
            "selected_rate_cps": selected_rate,
            "all_delayed_events": len(all_rows),
            "all_delayed_rate_cps": total_rate,
            "selected_rate_coverage": selected_rate / total_rate,
        },
        "coverage": {
            "exact_all_TES_contributors_reach_DECA_events": sum(
                event["ancestry_status"] == "EXACT_ALL_TES_CONTRIBUTORS_REACH_DECA"
                for event in events
            ),
            "exact_all_TES_contributors_reach_DECA_rate_cps": exact_rate,
            "exact_DECA_chain_fraction_of_selected_rate": exact_rate / selected_rate,
            "exact_TES_entry_rate_cps": entry_rate,
            "exact_TES_entry_fraction_of_selected_rate": entry_rate / selected_rate,
            "unknown_or_partial_DECA_chain_rate_cps": selected_rate - exact_rate,
            "unknown_TES_entry_rate_cps": selected_rate - entry_rate,
        },
        "volume_overview": overview,
        "semantics": {
            "incident_activation_family": "particle family which produced the radionuclide inventory, not the decay particle entering TES",
            "TES_entry": "mother particle at first saved IA interaction with detector_type=2 on a matched TES HTsim contributor chain",
            "TES_deposit": "energy deposited in TP_* CC records grouped by CC secondary-particle label",
            "limitation": "CC deposits and IA chords are not a complete Geant4 boundary-step trajectory",
        },
    }

    event_csv.parent.mkdir(parents=True, exist_ok=True)
    write_csv(event_csv, events)
    write_csv(summary_csv, summary)
    audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# S3d-O8 delayed top-five source volumes: DECA to TES audit",
        "",
        f"The five volumes cover {len(events)}/420 selected events and "
        f"{selected_rate:.12g}/{total_rate:.12g} cps ({selected_rate/total_rate:.2%}) of delayed W2 rate.",
        "They were ranked by W2 rate, not row count.",
        "",
        "|rank|source volume|material|events|W2 rate (cps)|Neff|exact DECA ancestry rate coverage|exact TES-entry rate coverage|",
        "|---:|---|---|---:|---:|---:|---:|---:|",
    ]
    for rank, row in enumerate(overview, 1):
        lines.append(
            f"|{rank}|{row['source_volume']}|{row['exact_material']}|{row['selected_events']}|"
            f"{row['w2_rate_cps']:.9g}|{row['mc_neff']:.3f}|"
            f"{row['exact_DECA_to_TES_rate_coverage']:.2%}|{row['exact_TES_entry_rate_coverage']:.2%}|"
        )
    lines.extend(
        [
            "",
            "`incident_activation_family` is the atmospheric particle family that produced the isotope; it is not the delayed particle entering TES.",
            "The event CSV freezes exact DECA emissions, matched HTsim contributor chains, first saved TES-interaction mother particles, and TP-pixel CC deposit particles.",
            "Any contributor without a complete IA-origin path to DECA or without a saved detector-type-2 interaction is explicitly marked UNKNOWN/PARTIAL.",
            "CC HIT records are energy-deposit samples, not complete boundary-crossing Geant4 steps.",
            "",
        ]
    )
    note_md.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-count", type=int, default=5)
    parser.add_argument("--event-csv", type=Path, default=DATA / "agent_delayed_top5_tes_chain_events.csv")
    parser.add_argument("--summary-csv", type=Path, default=DATA / "agent_delayed_top5_tes_chain_summary.csv")
    parser.add_argument("--audit-json", type=Path, default=DATA / "agent_delayed_top5_tes_chain_audit.json")
    parser.add_argument("--note-md", type=Path, default=PACKAGE / "DELAYED_TOP5_TES_CHAIN_AUDIT.md")
    args = parser.parse_args()
    run(args.event_csv, args.summary_csv, args.audit_json, args.note_md, args.top_count)


if __name__ == "__main__":
    main()
