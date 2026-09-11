#!/usr/bin/env python3
"""Summarize the completed SH3 Si-substrate-SD neutron 10M campaign.

The denominator is the exact generated-history count from the bound run
receipts plus the retained 100k all-event canary.  The production SIM files
contain complete IA/CC records only for events with at least one sensitive
hit; paired same-seed validation established that this storage filter
preserves the active-event CC records used here.

This remains a raw Geant4 energy-deposition audit.  It does not map substrate
energy into phonons collected by the TES and does not apply detector response.
"""

from __future__ import annotations

import csv
import gzip
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path

import analyze_si_deposition as base


PACKAGE = Path(__file__).resolve().parents[1]
PRODUCTION = PACKAGE / "production_10m"
CONFIG_PATH = PRODUCTION / "config.json"
PLAN_PATH = PRODUCTION / "generated/job_plan.json"
EXISTING_SIM = (
    PACKAGE
    / "run/sh3_sisd_n_canary100k_20260903/pass/"
    "sh3_sisd_n_canary100k_20260903.inc1.id1.sim.gz"
)
EXISTING_STATE = PACKAGE / "PILOT_RUN_STATE.json"
OUTPUTS = PRODUCTION / "analysis_10m"
SUMMARY = OUTPUTS / "si_deposition_summary_10m.json"
HITS = OUTPUTS / "si_hit_catalog_10m.csv"
EVENTS = OUTPUTS / "si_event_catalog_10m.csv"

CANONICAL_EXECUTE = Path(
    "/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute"
)
sys.path.insert(0, str(CANONICAL_EXECUTE))
from common import load_bound_receipt  # noqa: E402


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    for path in (CONFIG_PATH, PLAN_PATH, EXISTING_SIM, EXISTING_STATE):
        if not path.is_file():
            raise FileNotFoundError(path)
    if any(path.exists() for path in (SUMMARY, HITS, EVENTS)):
        raise FileExistsError("non-overwrite output gate")

    config = load_json(CONFIG_PATH)
    plan_payload = load_json(PLAN_PATH)
    jobs = plan_payload["jobs"]
    receipts: list[dict] = []
    for job in jobs:
        receipt = load_bound_receipt(config, job)
        if receipt is None:
            raise RuntimeError(f"campaign is incomplete: missing receipt for {job['job_id']}")
        receipts.append(receipt)

    existing_state = load_json(EXISTING_STATE)
    existing_jobs = existing_state.get("jobs", [])
    if (
        existing_state.get("status") != "COMPLETE"
        or len(existing_jobs) != 1
        or existing_jobs[0].get("status") != "PASS"
        or existing_jobs[0].get("generated_events") != 100000
        or Path(existing_jobs[0].get("path", "")).resolve() != EXISTING_SIM.parent.resolve()
    ):
        raise RuntimeError("retained 100k canary state is not bound PASS evidence")
    production_histories = sum(int(receipt["events"]) for receipt in receipts)
    if production_histories != 9_900_000 or len(receipts) != 99:
        raise RuntimeError("production receipt count/history total mismatch")
    total_histories = 100_000 + production_histories
    if total_histories != 10_000_000:
        raise RuntimeError("combined history total mismatch")

    samples = [
        {
            "sample_id": "existing_canary100k",
            "job_id": "sh3_sisd_n_canary100k_20260903",
            "histories": 100_000,
            "storage": "all_events",
            "sim_path": str(EXISTING_SIM),
        }
    ]
    samples.extend(
        {
            "sample_id": f"production_shard{index:04d}",
            "job_id": receipt["job_id"],
            "histories": int(receipt["events"]),
            "storage": "everyeventwithhits",
            "sim_path": receipt["sim_path"],
        }
        for index, receipt in enumerate(receipts, start=1)
    )

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
    total_sim_bytes = 0

    with (
        hit_tmp.open("w", encoding="utf-8", newline="") as hit_handle,
        event_tmp.open("w", encoding="utf-8", newline="") as event_handle,
    ):
        hit_writer = csv.writer(hit_handle, lineterminator="\n")
        event_writer = csv.writer(event_handle, lineterminator="\n")
        hit_writer.writerow(
            (
                "sample_id", "job_id", "event_id", "primary_energy_keV",
                "layer", "volume", "edep_keV", "x_cm", "y_cm", "z_cm",
                "t_s", "secondary", "parent", "step_process",
                "creation_process", "is_si_elastic_recoil",
            )
        )
        event_writer.writerow(
            (
                "sample_id", "job_id", "event_id", "primary_energy_keV",
                "si_total_keV", "si_elastic_recoil_keV", "si_hit_count",
                "si_recoil_hit_count", "tes_total_keV", "bgo_total_keV",
                "bgo_lt_50keV", "L0_keV", "L1_keV", "L2_keV", "L3_keV",
                "L4_keV", "L5_keV",
            )
        )

        current: dict | None = None
        current_sample: dict | None = None

        def flush() -> None:
            nonlocal current
            if current is None:
                return
            counters["stored_event_records"] += 1
            layers = current["si_layer_keV"]
            recoil_layers = current["si_recoil_layer_keV"]
            si_total = math.fsum(layers)
            recoil_total = math.fsum(recoil_layers)
            tes_total = current["tes_keV"]
            bgo_total = current["bgo_keV"]
            if tes_total > 0.0:
                counters["tes_positive_events"] += 1
                if 510.58 <= tes_total < 511.42:
                    counters["tes_events_in_raw_510p58_511p42_window"] += 1
            if bgo_total > 0.0:
                counters["bgo_positive_events"] += 1
            if si_total > 0.0:
                counters["si_positive_events"] += 1
                si_event_energy.append(si_total)
                if current["primary_energy_keV"] is not None:
                    si_primary_energy.append(current["primary_energy_keV"])
                for layer, energy in enumerate(layers):
                    if energy > 0.0:
                        layer_event_counts[layer] += 1
                        layer_energy[layer] += energy
                for threshold in base.THRESHOLDS_KEV:
                    if si_total >= threshold:
                        counters[f"si_events_ge_{threshold:g}_keV"] += 1
                if 510.58 <= si_total < 511.42:
                    counters["si_events_in_raw_510p58_511p42_window"] += 1
                if tes_total > 0.0:
                    counters["si_and_tes_positive_events"] += 1
                if bgo_total >= 50.0:
                    counters["si_events_bgo_ge_50keV"] += 1
                else:
                    counters["si_events_bgo_lt_50keV"] += 1
                event_writer.writerow(
                    (
                        current_sample["sample_id"], current_sample["job_id"],
                        current["event_id"], current["primary_energy_keV"],
                        si_total, recoil_total, current["si_hit_count"],
                        current["si_recoil_hit_count"], tes_total, bgo_total,
                        int(bgo_total < 50.0), *layers,
                    )
                )
            if recoil_total > 0.0:
                counters["si_elastic_recoil_events"] += 1
                recoil_event_energy.append(recoil_total)
                if current["primary_energy_keV"] is not None:
                    recoil_primary_energy.append(current["primary_energy_keV"])
                for layer, energy in enumerate(recoil_layers):
                    layer_recoil_energy[layer] += energy
                if tes_total > 0.0:
                    counters["si_recoil_and_tes_positive_events"] += 1
                if bgo_total >= 50.0:
                    counters["si_recoil_events_bgo_ge_50keV"] += 1
                else:
                    counters["si_recoil_events_bgo_lt_50keV"] += 1
            current = None

        for sample_index, sample in enumerate(samples, start=1):
            sim = Path(sample["sim_path"])
            if not sim.is_file() or sim.stat().st_size <= 0:
                raise RuntimeError(f"missing/empty bound SIM: {sim}")
            total_sim_bytes += sim.stat().st_size
            current_sample = sample
            with gzip.open(sim, "rt", encoding="utf-8", errors="strict") as stream:
                for raw in stream:
                    line = raw.strip()
                    if line == "SE":
                        flush()
                        continue
                    match_id = base.ID_RE.match(line)
                    if match_id:
                        # Cosima can end the last retained event at EN rather than SE.
                        flush()
                        current = base.fresh_event(int(match_id.group(1)))
                        continue
                    if current is None:
                        continue
                    if line.startswith("IA INIT"):
                        fields = [item.strip() for item in line[len("IA INIT") :].split(";")]
                        if len(fields) >= 23:
                            current["primary_energy_keV"] = float(fields[22])
                        continue
                    hit_match = base.CC_HIT_RE.match(line)
                    if hit_match is None:
                        continue
                    volume = hit_match.group(1)
                    values = dict(base.KV_RE.findall(hit_match.group(2)))
                    edep = float(values.get("edep_keV", "0"))
                    si_match = base.SI_RE.match(volume)
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
                        pair = (secondary, creation_process)
                        hit_pair_counts[pair] += 1
                        hit_pair_energy[pair] += edep
                        if is_recoil:
                            current["si_recoil_layer_keV"][layer] += edep
                            current["si_recoil_hit_count"] += 1
                            counters["si_elastic_recoil_hit_records"] += 1
                        hit_writer.writerow(
                            (
                                sample["sample_id"], sample["job_id"],
                                current["event_id"], current["primary_energy_keV"],
                                layer, volume, edep, values.get("x", ""),
                                values.get("y", ""), values.get("z", ""),
                                values.get("t", ""), secondary, parent,
                                step_process, creation_process, int(is_recoil),
                            )
                        )
                    elif base.TES_RE.match(volume):
                        current["tes_keV"] += edep
                    elif volume in base.BGO_VOLUMES:
                        current["bgo_keV"] += edep
            flush()
            print(
                json.dumps(
                    {
                        "sample": sample_index,
                        "of": len(samples),
                        "job_id": sample["job_id"],
                        "si_positive_so_far": counters["si_positive_events"],
                    }
                ),
                flush=True,
            )

    os.replace(hit_tmp, HITS)
    os.replace(event_tmp, EVENTS)
    counters["histories_generated"] = total_histories
    top_pairs = sorted(
        hit_pair_counts,
        key=lambda pair: (hit_pair_energy[pair], hit_pair_counts[pair]),
        reverse=True,
    )[:20]
    fraction_keys = (
        "si_positive_events",
        "si_elastic_recoil_events",
        "si_and_tes_positive_events",
        "si_events_bgo_lt_50keV",
        "si_recoil_events_bgo_lt_50keV",
        "si_events_in_raw_510p58_511p42_window",
        "tes_events_in_raw_510p58_511p42_window",
    )
    summary = {
        "schema_version": 1,
        "status": "PASS__SH3_SI_SD_NEUTRON_10M_SUMMARIZED",
        "scope": "raw Geant4 Si energy deposition; no phonon/thermal/TES response",
        "histories": {
            "existing_all_event_canary": 100_000,
            "production_everyeventwithhits": production_histories,
            "combined": total_histories,
        },
        "storage_validation": str(PACKAGE / "HITSONLY_VALIDATION.json"),
        "production_receipts": len(receipts),
        "sim_files": len(samples),
        "sim_bytes": total_sim_bytes,
        "event_counts": dict(sorted(counters.items())),
        "fractions_per_primary": {
            key: counters[key] / total_histories for key in fraction_keys
        },
        "si_event_total_energy": base.distribution(si_event_energy),
        "si_elastic_recoil_event_energy": base.distribution(recoil_event_energy),
        "primary_energy_for_si_events": base.distribution(si_primary_energy),
        "primary_energy_for_si_elastic_recoil_events": base.distribution(
            recoil_primary_energy
        ),
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
        "elastic_recoil_definition": (
            "CC HIT in a Si substrate with secondary starting 'Si', parent neutron, "
            "and creation process hadElastic"
        ),
        "outputs": {
            "si_hit_catalog": str(HITS),
            "si_event_catalog": str(EVENTS),
        },
    }
    SUMMARY.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
