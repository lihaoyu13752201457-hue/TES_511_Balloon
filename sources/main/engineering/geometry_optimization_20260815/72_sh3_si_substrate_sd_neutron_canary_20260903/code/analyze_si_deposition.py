#!/usr/bin/env python3
"""Stream the SH3 Si-SD canary into compact Si hit/event diagnostics.

The parser conventions are reused from the current M05 event-catalog code and
the retained neutron/plastic audit: event boundaries are ID/SE records and
exact unsmeared deposits are read from ``CC HIT ... edep_keV=...`` records.
No detector-response or Si-to-TES collection model is applied here.
"""

from __future__ import annotations

import csv
import gzip
import json
import math
import os
import re
from collections import Counter
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
SIM = (
    PACKAGE
    / "run/sh3_sisd_n_canary100k_20260903/pass/"
    "sh3_sisd_n_canary100k_20260903.inc1.id1.sim.gz"
)
OUTPUTS = PACKAGE / "outputs"
SUMMARY = OUTPUTS / "si_deposition_summary.json"
HITS = OUTPUTS / "si_hit_catalog.csv"
EVENTS = OUTPUTS / "si_event_catalog.csv"

ID_RE = re.compile(r"^ID\s+(\d+)")
CC_HIT_RE = re.compile(r"^CC\s+HIT\s+(\S+)\s+(.*)$")
KV_RE = re.compile(r"(\w+)=([^\s]+)")
SI_RE = re.compile(r"^Si_Substrate_Stack_side_entry_L([0-5])$")
TES_RE = re.compile(r"^TP_L[0-5]_\d+$")
BGO_VOLUMES = {
    "SH3_BGO40_SideShield",
    "SH3_BGO40_FrontOpticalAnnulus",
    "SH3_BGO40_RearColdPortAnnulus",
}
THRESHOLDS_KEV = (0.001, 0.3, 1.0, 10.0, 50.0, 100.0, 510.58)


def quantile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def distribution(values: list[float]) -> dict[str, float | int | None]:
    return {
        "count": len(values),
        "min_keV": min(values) if values else None,
        "q50_keV": quantile(values, 0.50),
        "q90_keV": quantile(values, 0.90),
        "q99_keV": quantile(values, 0.99),
        "max_keV": max(values) if values else None,
        "sum_keV": math.fsum(values),
    }


def fresh_event(event_id: int) -> dict:
    return {
        "event_id": event_id,
        "primary_energy_keV": None,
        "si_layer_keV": [0.0] * 6,
        "si_recoil_layer_keV": [0.0] * 6,
        "si_hit_count": 0,
        "si_recoil_hit_count": 0,
        "tes_keV": 0.0,
        "bgo_keV": 0.0,
    }


def main() -> int:
    if not SIM.is_file():
        raise FileNotFoundError(SIM)
    if any(path.exists() for path in (SUMMARY, HITS, EVENTS)):
        raise FileExistsError("non-overwrite output gate")
    OUTPUTS.mkdir(parents=True, exist_ok=False)

    hit_tmp = HITS.with_suffix(".csv.partial")
    event_tmp = EVENTS.with_suffix(".csv.partial")
    counters: Counter[str] = Counter()
    hit_pair_counts: Counter[tuple[str, str]] = Counter()
    hit_pair_energy: Counter[tuple[str, str]] = Counter()
    layer_event_counts: Counter[int] = Counter()
    layer_energy: Counter[int] = Counter()
    layer_recoil_energy: Counter[int] = Counter()
    si_event_energy: list[float] = []
    recoil_event_energy: list[float] = []
    si_primary_energy: list[float] = []
    recoil_primary_energy: list[float] = []
    current: dict | None = None

    with (
        hit_tmp.open("w", encoding="utf-8", newline="") as hit_handle,
        event_tmp.open("w", encoding="utf-8", newline="") as event_handle,
    ):
        hit_writer = csv.writer(hit_handle, lineterminator="\n")
        event_writer = csv.writer(event_handle, lineterminator="\n")
        hit_writer.writerow(
            (
                "event_id", "primary_energy_keV", "layer", "volume", "edep_keV",
                "x_cm", "y_cm", "z_cm", "t_s", "secondary", "parent",
                "step_process", "creation_process", "is_si_elastic_recoil",
            )
        )
        event_writer.writerow(
            (
                "event_id", "primary_energy_keV", "si_total_keV",
                "si_elastic_recoil_keV", "si_hit_count", "si_recoil_hit_count",
                "tes_total_keV", "bgo_total_keV", "bgo_lt_50keV",
                "L0_keV", "L1_keV", "L2_keV", "L3_keV", "L4_keV", "L5_keV",
            )
        )

        def flush() -> None:
            nonlocal current
            if current is None:
                return
            counters["generated_events"] += 1
            layers = current["si_layer_keV"]
            recoil_layers = current["si_recoil_layer_keV"]
            si_total = math.fsum(layers)
            recoil_total = math.fsum(recoil_layers)
            if si_total > 0.0:
                counters["si_positive_events"] += 1
                si_event_energy.append(si_total)
                if current["primary_energy_keV"] is not None:
                    si_primary_energy.append(current["primary_energy_keV"])
                for layer, energy in enumerate(layers):
                    if energy > 0.0:
                        layer_event_counts[layer] += 1
                        layer_energy[layer] += energy
                for threshold in THRESHOLDS_KEV:
                    if si_total >= threshold:
                        counters[f"si_events_ge_{threshold:g}_keV"] += 1
                if 510.58 <= si_total < 511.42:
                    counters["si_events_in_raw_510p58_511p42_window"] += 1
                if current["tes_keV"] > 0.0:
                    counters["si_and_tes_positive_events"] += 1
                if current["bgo_keV"] >= 50.0:
                    counters["si_events_bgo_ge_50keV"] += 1
                else:
                    counters["si_events_bgo_lt_50keV"] += 1
                event_writer.writerow(
                    (
                        current["event_id"], current["primary_energy_keV"], si_total,
                        recoil_total, current["si_hit_count"],
                        current["si_recoil_hit_count"], current["tes_keV"],
                        current["bgo_keV"], int(current["bgo_keV"] < 50.0), *layers,
                    )
                )
            if recoil_total > 0.0:
                counters["si_elastic_recoil_events"] += 1
                recoil_event_energy.append(recoil_total)
                if current["primary_energy_keV"] is not None:
                    recoil_primary_energy.append(current["primary_energy_keV"])
                for layer, energy in enumerate(recoil_layers):
                    layer_recoil_energy[layer] += energy
                if current["tes_keV"] > 0.0:
                    counters["si_recoil_and_tes_positive_events"] += 1
                if current["bgo_keV"] >= 50.0:
                    counters["si_recoil_events_bgo_ge_50keV"] += 1
                else:
                    counters["si_recoil_events_bgo_lt_50keV"] += 1
            current = None

        with gzip.open(SIM, "rt", encoding="utf-8", errors="strict") as stream:
            for raw in stream:
                line = raw.strip()
                if line == "SE":
                    flush()
                    continue
                match_id = ID_RE.match(line)
                if match_id:
                    if current is not None:
                        raise RuntimeError("ID before SE event boundary")
                    current = fresh_event(int(match_id.group(1)))
                    continue
                if current is None:
                    continue
                if line.startswith("IA INIT"):
                    fields = [item.strip() for item in line[len("IA INIT") :].split(";")]
                    if len(fields) >= 23:
                        current["primary_energy_keV"] = float(fields[22])
                    continue
                hit_match = CC_HIT_RE.match(line)
                if hit_match is None:
                    continue
                volume = hit_match.group(1)
                values = dict(KV_RE.findall(hit_match.group(2)))
                edep = float(values.get("edep_keV", "0"))
                si_match = SI_RE.match(volume)
                if si_match:
                    layer = int(si_match.group(1))
                    secondary = values.get("sec", "")
                    parent = values.get("par", "")
                    step_process = values.get("sproc", "")
                    creation_process = values.get("cproc", "")
                    is_recoil = (
                        secondary.startswith("Si")
                        and parent == "neutron"
                        and creation_process == "hadElastic"
                    )
                    current["si_layer_keV"][layer] += edep
                    current["si_hit_count"] += 1
                    counters["si_hit_records"] += 1
                    layer_energy[layer] += 0.0  # ensure zero-valued layers are represented
                    pair = (secondary, creation_process)
                    hit_pair_counts[pair] += 1
                    hit_pair_energy[pair] += edep
                    if is_recoil:
                        current["si_recoil_layer_keV"][layer] += edep
                        current["si_recoil_hit_count"] += 1
                        counters["si_elastic_recoil_hit_records"] += 1
                    hit_writer.writerow(
                        (
                            current["event_id"], current["primary_energy_keV"], layer,
                            volume, edep, values.get("x", ""), values.get("y", ""),
                            values.get("z", ""), values.get("t", ""), secondary,
                            parent, step_process, creation_process, int(is_recoil),
                        )
                    )
                elif TES_RE.match(volume):
                    current["tes_keV"] += edep
                elif volume in BGO_VOLUMES:
                    current["bgo_keV"] += edep
        flush()

    if counters["generated_events"] != 100000:
        raise RuntimeError(f"generated event mismatch: {counters['generated_events']}")
    os.replace(hit_tmp, HITS)
    os.replace(event_tmp, EVENTS)

    top_pairs = sorted(
        hit_pair_counts,
        key=lambda pair: (hit_pair_energy[pair], hit_pair_counts[pair]),
        reverse=True,
    )[:20]
    summary = {
        "schema_version": 1,
        "status": "PASS__SH3_SI_SD_CANARY_SUMMARIZED",
        "scope": "raw Geant4 Si energy deposition; no phonon/thermal/TES response",
        "sim": str(SIM),
        "sim_bytes": SIM.stat().st_size,
        "event_counts": dict(sorted(counters.items())),
        "fractions_per_primary": {
            key: counters[key] / counters["generated_events"]
            for key in (
                "si_positive_events",
                "si_elastic_recoil_events",
                "si_and_tes_positive_events",
                "si_events_bgo_lt_50keV",
                "si_recoil_events_bgo_lt_50keV",
            )
        },
        "si_event_total_energy": distribution(si_event_energy),
        "si_elastic_recoil_event_energy": distribution(recoil_event_energy),
        "primary_energy_for_si_events": distribution(si_primary_energy),
        "primary_energy_for_si_elastic_recoil_events": distribution(recoil_primary_energy),
        "layers": {
            f"L{layer}": {
                "positive_events": layer_event_counts[layer],
                "all_si_deposition_sum_keV": layer_energy[layer],
                "elastic_recoil_deposition_sum_keV": layer_recoil_energy[layer],
            }
            for layer in range(6)
        },
        "top_si_hit_secondary_creation_pairs_by_energy": [
            {
                "secondary": pair[0],
                "creation_process": pair[1],
                "hit_records": hit_pair_counts[pair],
                "deposition_sum_keV": hit_pair_energy[pair],
            }
            for pair in top_pairs
        ],
        "outputs": {
            "si_hit_catalog": str(HITS),
            "si_event_catalog": str(EVENTS),
        },
        "elastic_recoil_definition": (
            "CC HIT in a Si substrate with secondary starting 'Si', parent neutron, "
            "and creation process hadElastic"
        ),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
