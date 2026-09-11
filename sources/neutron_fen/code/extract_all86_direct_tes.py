#!/usr/bin/env python3
"""Extract direct TES-channel deposits for the 86 BGO-unvetoed Si events.

The compact Si catalog stores only event-level direct-TES totals.  This script
therefore streams only the receipt-bound SIM files containing the selected 86
events.  It never copies a SIM and stops each stream after the last requested
event has been fully read.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import re
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


WORKSPACE = Path("/home/ubuntu/neutron_fen")
PACKAGE = Path(
    "/home/ubuntu/TES_511_Balloon/engineering/geometry_optimization_20260815/"
    "72_sh3_si_substrate_sd_neutron_canary_20260903"
)
INPUT = WORKSPACE / "outputs/unvetoed_events.csv"
OUTPUT_DIR = WORKSPACE / "outputs/neutron_energy_band"
OUTPUT_CSV = OUTPUT_DIR / "direct_tes_channels_all86.csv"
OUTPUT_JSON = OUTPUT_DIR / "direct_tes_channels_all86_manifest.json"

HIT_RE = re.compile(r"^CC HIT (\S+) edep_keV=([^ ]+) .*? t=([^ ]+)")
TES_RE = re.compile(r"^TP_L([0-5])_(\d{5})$")
CANARY_JOB = "sh3_sisd_n_canary100k_20260903"
CANARY_SIM = (
    PACKAGE / "run" / CANARY_JOB / "pass" /
    f"{CANARY_JOB}.inc1.id1.sim.gz"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_source(job_id: str) -> dict[str, object]:
    if job_id == CANARY_JOB:
        sim_path = CANARY_SIM.resolve(strict=True)
        return {
            "job_id": job_id,
            "sim_path": str(sim_path),
            "sim_bytes": sim_path.stat().st_size,
            "receipt_path": None,
            "receipt_sha256": None,
            "validation": "fixed pass/ path from the handed-off canary work package",
        }

    receipt_path = (
        PACKAGE / "production_10m/run/receipts" / f"{job_id}.json"
    ).resolve(strict=True)
    receipt = json.loads(receipt_path.read_text())
    if receipt.get("status") != "PASS" or receipt.get("job_id") != job_id:
        raise RuntimeError(f"invalid receipt: {receipt_path}")
    sim_path = Path(receipt["sim_path"]).resolve(strict=True)
    if PACKAGE.resolve() not in sim_path.parents:
        raise RuntimeError(f"SIM outside authorized package: {sim_path}")
    if sim_path.stat().st_size != int(receipt["sim_bytes"]):
        raise RuntimeError(f"SIM size mismatch: {sim_path}")
    return {
        "job_id": job_id,
        "sim_path": str(sim_path),
        "sim_bytes": sim_path.stat().st_size,
        "receipt_path": str(receipt_path),
        "receipt_sha256": sha256(receipt_path),
        "validation": "PASS receipt; job id and byte count verified",
    }


def stream_job(task: tuple[str, tuple[int, ...]]) -> dict[str, object]:
    job_id, target_tuple = task
    targets = set(target_tuple)
    source = resolve_source(job_id)
    sim_path = Path(str(source["sim_path"]))
    found: set[int] = set()
    records: list[dict[str, object]] = []
    current_event: int | None = None
    selected = False
    selected_event_open = False
    bytes_uncompressed = 0

    with gzip.open(sim_path, "rt", errors="strict") as stream:
        for line in stream:
            bytes_uncompressed += len(line)
            if line.startswith("SE"):
                if selected_event_open:
                    selected_event_open = False
                    if found == targets:
                        break
                current_event = None
                selected = False
            elif line.startswith("ID "):
                current_event = int(line.split()[1])
                selected = current_event in targets
                if selected:
                    found.add(current_event)
                    selected_event_open = True
            elif selected and line.startswith("CC HIT "):
                match = HIT_RE.match(line.rstrip("\n"))
                if not match:
                    raise RuntimeError(
                        f"cannot parse selected CC HIT in {job_id}: {line[:180]}"
                    )
                volume, energy, time_s = match.groups()
                tes = TES_RE.match(volume)
                if tes:
                    records.append(
                        {
                            "job_id": job_id,
                            "event_id": current_event,
                            "layer": int(tes.group(1)),
                            "pixel_id": int(tes.group(2)),
                            "channel": f"L{int(tes.group(1))}:P{int(tes.group(2))}",
                            "energy_keV": float(energy),
                            "time_ns": float(time_s) * 1e9,
                        }
                    )

    if found != targets:
        raise RuntimeError(
            f"missing target events in {sim_path}: {sorted(targets - found)}"
        )
    source["target_event_ids"] = sorted(targets)
    source["selected_raw_tes_hit_count"] = len(records)
    source["streamed_uncompressed_characters"] = bytes_uncompressed
    return {"source": source, "records": records}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    event_meta: dict[tuple[str, int], dict[str, object]] = {}
    job_targets: dict[str, set[int]] = defaultdict(set)
    with INPUT.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            key = (row["job_id"], int(row["event_id"]))
            job_targets[key[0]].add(key[1])
            metadata = {
                "event_order": int(row["event_order"]),
                "sample_id": row["sample_id"],
                "candidate": row["candidate"],
                "strict_recoil_event": int(row["strict_recoil_event"]),
                "catalog_tes_total_keV": float(row["tes_total_keV"]),
                "si_total_keV": float(row["si_total_keV"]),
                "bgo_total_keV": float(row["bgo_total_keV"]),
            }
            if key in event_meta and event_meta[key] != metadata:
                raise RuntimeError(f"inconsistent repeated event metadata: {key}")
            event_meta[key] = metadata

    if len(event_meta) != 86:
        raise RuntimeError(f"expected 86 events, found {len(event_meta)}")
    tasks = sorted((job, tuple(sorted(ids))) for job, ids in job_targets.items())
    with ProcessPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(stream_job, tasks))

    raw_records = [record for result in results for record in result["records"]]
    grouped: dict[tuple[str, int, int, int], dict[str, object]] = defaultdict(
        lambda: {"energy_keV": 0.0, "hit_count": 0, "times_ns": []}
    )
    for record in raw_records:
        key = (
            str(record["job_id"]), int(record["event_id"]),
            int(record["layer"]), int(record["pixel_id"]),
        )
        grouped[key]["energy_keV"] = float(grouped[key]["energy_keV"]) + float(record["energy_keV"])
        grouped[key]["hit_count"] = int(grouped[key]["hit_count"]) + 1
        grouped[key]["times_ns"].append(float(record["time_ns"]))

    rows: list[dict[str, object]] = []
    for (job_id, event_id, layer, pixel_id), values in grouped.items():
        meta = event_meta[(job_id, event_id)]
        times = list(values["times_ns"])
        rows.append(
            {
                "event_order": meta["event_order"],
                "sample_id": meta["sample_id"],
                "job_id": job_id,
                "event_id": event_id,
                "candidate": meta["candidate"],
                "strict_recoil_event": meta["strict_recoil_event"],
                "layer": layer,
                "pixel_id": pixel_id,
                "channel": f"L{layer}:P{pixel_id}",
                "direct_tes_energy_keV": values["energy_keV"],
                "hit_count": values["hit_count"],
                "first_time_ns": min(times),
                "last_time_ns": max(times),
            }
        )
    rows.sort(key=lambda row: (int(row["event_order"]), int(row["layer"]), int(row["pixel_id"])))
    fieldnames = [
        "event_order", "sample_id", "job_id", "event_id", "candidate",
        "strict_recoil_event", "layer", "pixel_id", "channel",
        "direct_tes_energy_keV", "hit_count", "first_time_ns", "last_time_ns",
    ]
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    extracted_totals: dict[tuple[str, int], float] = defaultdict(float)
    for row in rows:
        extracted_totals[(str(row["job_id"]), int(row["event_id"]))] += float(row["direct_tes_energy_keV"])
    mismatches = []
    for key, meta in event_meta.items():
        expected = float(meta["catalog_tes_total_keV"])
        actual = extracted_totals.get(key, 0.0)
        if not math.isclose(actual, expected, rel_tol=2e-10, abs_tol=2e-6):
            mismatches.append({"job_id": key[0], "event_id": key[1], "expected": expected, "actual": actual})

    manifest = {
        "schema_version": 1,
        "status": "PASS" if not mismatches else "FAIL",
        "scope": "Direct TP_Lx_pixel hits for exactly the 86 BGO<50 keV Si-positive events; only 56 bound SIM streams were opened and no SIM was copied.",
        "input": {"path": str(INPUT), "sha256": sha256(INPUT)},
        "counts": {
            "selected_events": len(event_meta),
            "source_sim_files": len(results),
            "raw_direct_tes_hits": len(raw_records),
            "aggregated_direct_tes_channels": len(rows),
            "events_with_direct_tes_energy": sum(value > 0 for value in extracted_totals.values()),
        },
        "self_checks": {
            "selected_event_count_is_86": len(event_meta) == 86,
            "all_event_direct_tes_totals_match_compact_catalog": not mismatches,
            "mismatches": mismatches,
        },
        "sources": [result["source"] for result in results],
        "output": {"path": str(OUTPUT_CSV), "sha256": sha256(OUTPUT_CSV)},
    }
    OUTPUT_JSON.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    if manifest["status"] != "PASS":
        raise SystemExit(json.dumps(manifest["self_checks"], indent=2))
    print(json.dumps(manifest["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
