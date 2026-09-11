#!/usr/bin/env python3
"""Stream only the receipt-bound SIMs needed for A/B/C direct-TES channels."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

WORKSPACE = Path("/home/ubuntu/neutron_fen")
PACKAGE = Path("/home/ubuntu/TES_511_Balloon/engineering/geometry_optimization_20260815/72_sh3_si_substrate_sd_neutron_canary_20260903")
TARGETS = {
    "sh3_sisd_n10m_shard0037": {989: "A"},
    "sh3_sisd_n10m_shard0049": {2764: "B", 639: "C"},
}
HIT_RE = re.compile(r"^CC HIT (\S+) edep_keV=([^ ]+) .*? t=([^ ]+)")
TES_RE = re.compile(r"^TP_L([0-5])_(\d{5})$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    records = []
    sources = []
    for job_id, targets in TARGETS.items():
        receipt_path = PACKAGE / "production_10m/run/receipts" / f"{job_id}.json"
        receipt = json.loads(receipt_path.read_text())
        if receipt["status"] != "PASS" or receipt["job_id"] != job_id:
            raise SystemExit(f"receipt is not PASS: {receipt_path}")
        sim_path = Path(receipt["sim_path"])
        stat = sim_path.stat()
        if stat.st_size != receipt["sim_bytes"]:
            raise SystemExit(f"SIM size differs from receipt: {sim_path}")
        current_event = None
        selected = False
        found = set()
        with gzip.open(sim_path, "rt", errors="strict") as stream:
            for line in stream:
                if line.startswith("SE"):
                    current_event = None
                    selected = False
                elif line.startswith("ID "):
                    current_event = int(line.split()[1])
                    selected = current_event in targets
                    if selected:
                        found.add(current_event)
                elif selected and line.startswith("CC HIT "):
                    match = HIT_RE.match(line.rstrip("\n"))
                    if not match:
                        raise SystemExit(f"cannot parse selected CC HIT: {line[:160]}")
                    volume, energy, time_s = match.groups()
                    tes = TES_RE.match(volume)
                    if tes:
                        records.append(
                            {
                                "candidate": targets[current_event],
                                "job_id": job_id,
                                "event_id": current_event,
                                "layer": int(tes.group(1)),
                                "pixel_id": int(tes.group(2)),
                                "volume": volume,
                                "edep_keV": float(energy),
                                "time_ns": float(time_s) * 1e9,
                            }
                        )
        if found != set(targets):
            raise SystemExit(f"missing target events in {sim_path}: {set(targets) - found}")
        sources.append(
            {
                "job_id": job_id,
                "receipt_path": str(receipt_path),
                "receipt_sha256": sha256(receipt_path),
                "sim_path": str(sim_path),
                "sim_bytes": stat.st_size,
                "sim_digest_policy": "NOT_COMPUTED__TARGETED_STREAM_ONLY",
                "target_event_ids": sorted(targets),
            }
        )

    grouped = defaultdict(lambda: {"energy_keV": 0.0, "hit_count": 0, "times_ns": []})
    for row in records:
        key = (row["candidate"], row["layer"], row["pixel_id"])
        grouped[key]["energy_keV"] += row["edep_keV"]
        grouped[key]["hit_count"] += 1
        grouped[key]["times_ns"].append(row["time_ns"])
    rows = []
    for (candidate, layer, pixel), value in sorted(grouped.items()):
        rows.append(
            {
                "candidate": candidate,
                "layer": layer,
                "pixel_id": pixel,
                "channel": f"L{layer}:P{pixel}",
                "energy_keV": value["energy_keV"],
                "hit_count": value["hit_count"],
                "first_time_ns": min(value["times_ns"]),
                "last_time_ns": max(value["times_ns"]),
            }
        )
    csv_path = WORKSPACE / "outputs/candidate_direct_tes_channels.csv"
    with csv_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    expected = {"A": 17.13377, "B": 0.0, "C": 458.391770806}
    totals = {name: sum(row["energy_keV"] for row in rows if row["candidate"] == name) for name in expected}
    output = {
        "schema_version": 1,
        "status": "PASS",
        "scope": "Only receipt-bound shard0037 event 989 and shard0049 events 2764/639 were streamed; no SIM was copied.",
        "sources": sources,
        "counts": {"raw_tes_hits": len(records), "aggregated_channels": len(rows)},
        "candidate_totals_keV": totals,
        "expected_compact_catalog_totals_keV": expected,
        "candidate_channel_multiplicity": {name: sum(row["candidate"] == name for row in rows) for name in expected},
        "self_checks": {
            "all_candidates_found": set(totals) == set(expected),
            "tes_totals_match_compact_catalog_abs_1e-8_keV": all(abs(totals[k] - expected[k]) < 1e-8 for k in expected),
        },
        "output_csv": {"path": str(csv_path), "sha256": sha256(csv_path)},
    }
    out_path = WORKSPACE / "outputs/candidate_direct_tes_channels.json"
    out_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    if not all(output["self_checks"].values()):
        raise SystemExit("self-check failed")
    print(json.dumps({"status": "PASS", "totals_keV": totals,
                      "channel_multiplicity": output["candidate_channel_multiplicity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
