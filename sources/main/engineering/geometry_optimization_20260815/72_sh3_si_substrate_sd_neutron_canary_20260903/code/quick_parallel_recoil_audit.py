#!/usr/bin/env python3
"""Read-only parallel audit of Si recoil counts in the completed 10M run."""

from __future__ import annotations

import concurrent.futures
import gzip
import json
import math
import os
import re
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
PRODUCTION = PACKAGE / "production_10m"
RECEIPTS = PRODUCTION / "run/receipts"
PILOT_SIM = (
    PACKAGE / "run/sh3_sisd_n_canary100k_20260903/pass/"
    "sh3_sisd_n_canary100k_20260903.inc1.id1.sim.gz"
)
PILOT_DAT = PILOT_SIM.with_name("sh3_sisd_n_canary100k_20260903.dat.inc1.dat")
OUTPUT = PRODUCTION / "quick_parallel_recoil_audit.json"

ID_RE = re.compile(r"^ID\s+(\d+)")
CC_RE = re.compile(r"^CC\s+HIT\s+(\S+)\s+(.*)$")
KV_RE = re.compile(r"(\w+)=([^\s]+)")
SI_RE = re.compile(r"^Si_Substrate_Stack_side_entry_L[0-5]$")
TES_RE = re.compile(r"^TP_L[0-5]_\d+$")
BGO = {
    "SH3_BGO40_SideShield",
    "SH3_BGO40_FrontOpticalAnnulus",
    "SH3_BGO40_RearColdPortAnnulus",
}


def parse_one(sample: tuple[str, str]) -> dict:
    job_id, sim_text = sample
    sim = Path(sim_text)
    rows: list[tuple[float, float, float, float]] = []
    current: dict | None = None

    def flush() -> None:
        nonlocal current
        if current is not None and current["si"] > 0.0:
            rows.append(
                (current["si"], current["recoil"], current["tes"], current["bgo"])
            )
        current = None

    with gzip.open(sim, "rt", encoding="utf-8", errors="strict") as stream:
        for raw in stream:
            line = raw.strip()
            if line == "SE":
                flush()
                continue
            match = ID_RE.match(line)
            if match:
                flush()
                current = {"si": 0.0, "recoil": 0.0, "tes": 0.0, "bgo": 0.0}
                continue
            if current is None:
                continue
            match = CC_RE.match(line)
            if match is None:
                continue
            volume = match.group(1)
            values = dict(KV_RE.findall(match.group(2)))
            edep = float(values.get("edep_keV", "0"))
            if SI_RE.match(volume):
                current["si"] += edep
                if (
                    values.get("sec", "").startswith("Si")
                    and values.get("par") == "neutron"
                    and values.get("cproc") == "hadElastic"
                ):
                    current["recoil"] += edep
            elif TES_RE.match(volume):
                current["tes"] += edep
            elif volume in BGO:
                current["bgo"] += edep
    flush()
    return {"job_id": job_id, "sim_bytes": sim.stat().st_size, "rows": rows}


def distribution(values: list[float]) -> dict:
    ordered = sorted(values)

    def q(probability: float) -> float | None:
        if not ordered:
            return None
        position = probability * (len(ordered) - 1)
        lo = math.floor(position)
        hi = math.ceil(position)
        fraction = position - lo
        return ordered[lo] * (1 - fraction) + ordered[hi] * fraction

    return {
        "count": len(ordered),
        "min_keV": ordered[0] if ordered else None,
        "q50_keV": q(0.5),
        "q90_keV": q(0.9),
        "q99_keV": q(0.99),
        "max_keV": ordered[-1] if ordered else None,
        "sum_keV": math.fsum(ordered),
    }


def main() -> int:
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    receipt_paths = sorted(RECEIPTS.glob("*.json"))
    if len(receipt_paths) != 99:
        raise RuntimeError(f"expected 99 receipts, got {len(receipt_paths)}")
    receipts = [json.loads(path.read_text(encoding="utf-8")) for path in receipt_paths]
    if any(receipt.get("status") != "PASS" for receipt in receipts):
        raise RuntimeError("non-PASS production receipt")
    samples = [("existing_canary100k", str(PILOT_SIM))]
    samples.extend((receipt["job_id"], receipt["sim_path"]) for receipt in receipts)

    results: list[dict] = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(parse_one, sample): sample[0] for sample in samples}
        for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            result = future.result()
            results.append(result)
            print(json.dumps({"completed_files": index, "job_id": result["job_id"]}), flush=True)

    rows = [row for result in results for row in result["rows"]]
    recoil_rows = [row for row in rows if row[1] > 0.0]
    si_energy = [row[0] for row in rows]
    recoil_energy = [row[1] for row in recoil_rows]
    recoil_si_total = [row[0] for row in recoil_rows]
    tt_production = math.fsum(receipt["isotope_dat"]["TT_s"] for receipt in receipts)
    pilot_tt = float(
        next(
            line.split()[1]
            for line in PILOT_DAT.read_text(encoding="utf-8").splitlines()
            if line.startswith("TT ")
        )
    )
    tt_total = tt_production + pilot_tt

    def n(predicate) -> int:
        return sum(1 for row in rows if predicate(row))

    def nr(predicate) -> int:
        return sum(1 for row in recoil_rows if predicate(row))

    payload = {
        "schema_version": 1,
        "status": "PASS__READ_ONLY_PARALLEL_RECOIL_AUDIT",
        "histories": 10_000_000,
        "TT": {
            "pilot_s": pilot_tt,
            "production_s": tt_production,
            "combined_s": tt_total,
            "combined_min": tt_total / 60.0,
            "combined_h": tt_total / 3600.0,
        },
        "sim_files": len(results),
        "sim_bytes": sum(result["sim_bytes"] for result in results),
        "si_positive_events": len(rows),
        "si_event_energy": distribution(si_energy),
        "si_events": {
            "bgo_lt_50keV": n(lambda row: row[3] < 50.0),
            "tes_positive": n(lambda row: row[2] > 0.0),
            "si_total_ge_510p58keV": n(lambda row: row[0] >= 510.58),
            "si_total_ge_511keV": n(lambda row: row[0] >= 511.0),
            "si_total_raw_510p58_511p42keV": n(lambda row: 510.58 <= row[0] < 511.42),
        },
        "strict_si_elastic_recoil_definition": (
            "Si-substrate CC HIT with secondary Si*, parent neutron, cproc hadElastic"
        ),
        "strict_si_elastic_recoil_events": len(recoil_rows),
        "strict_recoil_component_energy": distribution(recoil_energy),
        "si_total_energy_in_strict_recoil_events": distribution(recoil_si_total),
        "strict_recoil_events": {
            "bgo_lt_50keV": nr(lambda row: row[3] < 50.0),
            "bgo_ge_50keV": nr(lambda row: row[3] >= 50.0),
            "tes_positive": nr(lambda row: row[2] > 0.0),
            "recoil_component_ge_510p58keV": nr(lambda row: row[1] >= 510.58),
            "recoil_component_ge_511keV": nr(lambda row: row[1] >= 511.0),
            "recoil_component_raw_510p58_511p42keV": nr(
                lambda row: 510.58 <= row[1] < 511.42
            ),
            "si_total_ge_510p58keV": nr(lambda row: row[0] >= 510.58),
            "si_total_ge_511keV": nr(lambda row: row[0] >= 511.0),
            "si_total_raw_510p58_511p42keV": nr(
                lambda row: 510.58 <= row[0] < 511.42
            ),
            "si_total_ge_511keV_and_bgo_lt_50keV": nr(
                lambda row: row[0] >= 511.0 and row[3] < 50.0
            ),
            "recoil_component_ge_511keV_and_bgo_lt_50keV": nr(
                lambda row: row[1] >= 511.0 and row[3] < 50.0
            ),
        },
        "rates_per_s": {
            "si_positive": len(rows) / tt_total,
            "strict_si_elastic_recoil": len(recoil_rows) / tt_total,
            "strict_si_elastic_recoil_bgo_lt_50keV": nr(
                lambda row: row[3] < 50.0
            ) / tt_total,
        },
        "interpretation_boundary": (
            "Raw Geant4 deposition only; no athermal-phonon collection, thermal transport, "
            "TES pulse formation, pulse-shape discrimination, or detector response."
        ),
        "workers": 8,
        "pid": os.getpid(),
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
