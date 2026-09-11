#!/usr/bin/env python3
"""Screen unvetoed strict Si recoils for a possible 511-keV thermal mapping."""

from __future__ import annotations

import csv
import json
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE / "production_10m/recoil_spectrum"
INPUT = ROOT / "strict_si_elastic_recoil_events_10m.csv"
OUTPUT = ROOT / "strict_si_recoil_thermal_coupling_screen_10m.json"
ROI_LOW = 510.58
ROI_HIGH = 511.42


def main() -> int:
    if not INPUT.is_file():
        raise FileNotFoundError(INPUT)
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    with INPUT.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    unvetoed = [row for row in rows if float(row["bgo_total_keV"]) < 50.0]
    candidates = []
    for row in unvetoed:
        si = float(row["si_total_keV"])
        tes = float(row["tes_total_keV"])
        if tes >= ROI_HIGH or tes + si < ROI_LOW:
            continue
        eta_low = max(0.0, (ROI_LOW - tes) / si)
        eta_high = min(1.0, (ROI_HIGH - tes) / si)
        if eta_low >= eta_high:
            continue
        candidates.append(
            {
                "sample_id": row["sample_id"],
                "job_id": row["job_id"],
                "event_id": int(row["event_id"]),
                "si_total_keV": si,
                "strict_recoil_keV": float(row["si_elastic_recoil_keV"]),
                "tes_direct_keV": tes,
                "bgo_keV": float(row["bgo_total_keV"]),
                "eta_for_511": (511.0 - tes) / si,
                "eta_interval_for_510p58_511p42": [eta_low, eta_high],
            }
        )
    payload = {
        "schema_version": 1,
        "status": "PASS__CONDITIONAL_ENERGY_BALANCE_SCREEN",
        "model": "E_reconstructed = E_TES_direct + eta * E_Si_total, with 0 <= eta <= 1",
        "roi_keV": [ROI_LOW, ROI_HIGH],
        "strict_recoil_events": len(rows),
        "unvetoed_strict_recoil_events": len(unvetoed),
        "unvetoed_direct_TES_events_already_in_roi": sum(
            ROI_LOW <= float(row["tes_total_keV"]) < ROI_HIGH for row in unvetoed
        ),
        "unvetoed_events_with_some_eta_mapping_into_roi": len(candidates),
        "candidates": candidates,
        "interpretation": (
            "Necessary energy-balance condition only. It is not a phonon-transport, "
            "TES pulse-shape, channel-summing, or detector-response calculation."
        ),
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
