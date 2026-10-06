#!/usr/bin/env python3
"""Compare the first 100 baseline and minimal-SD alpha histories."""

from __future__ import annotations

import gzip
import argparse
import json
import math
import re
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
MANIFEST = PACKAGE / "PILOT_MANIFEST.json"
RUN_STATE = PACKAGE / "PILOT_RUN_STATE.json"
OUTPUT = PACKAGE / "PILOT_PHYSICS_VALIDATION.json"

ACTIVE_VOLUMES = {
    "TES_Pixel_L0",
    "TES_Pixel_L1",
    "TES_Pixel_L2",
    "TES_Pixel_L3",
    "TES_Pixel_L4",
    "TES_Pixel_L5",
    "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm",
    "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm",
    "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm",
    "BGO_S3C_FullWrap_SideShell_WindowCut_40mm",
    "BGO_S3D_O8_FullWrap_BottomCap_30mm",
    "BGO_S3D_O8_FullWrap_TopAnnulus_10mm",
}
HIT_RE = re.compile(r"^CC HIT (\S+) edep_keV=([0-9.eE+-]+)\b")
TES_COPY_RE = re.compile(r"^TP_L[0-5]_\d+$")


def parse_prefix(path: Path, limit: int) -> list[dict]:
    events: list[dict] = []
    current: dict | None = None
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as stream:
        for raw in stream:
            line = raw.rstrip("\n")
            if line.startswith("ID "):
                fields = line.split()
                current = {
                    "id": int(fields[1]),
                    "ti": None,
                    "init": None,
                    "hits": {},
                    "htsim": [],
                }
                continue
            if current is None:
                continue
            if line == "SE":
                events.append(current)
                current = None
                if len(events) == limit:
                    break
                continue
            if line.startswith("TI "):
                current["ti"] = line
            elif line.startswith("IA INIT"):
                current["init"] = line
            elif line.startswith("HTsim "):
                # StoreSimulationInfo=all appends interaction-origin IDs after
                # the six detector-hit physics fields; init-only deliberately
                # omits that lineage suffix.  The response uses only the common
                # detector, position, energy, and time fields.
                current["htsim"].append(";".join(line.split(";")[:6]))
            else:
                match = HIT_RE.match(line)
                if match and (
                    match.group(1) in ACTIVE_VOLUMES or TES_COPY_RE.match(match.group(1))
                ):
                    volume = match.group(1)
                    energy = float(match.group(2))
                    row = current["hits"].setdefault(volume, {"count": 0, "sum_keV": 0.0})
                    row["count"] += 1
                    row["sum_keV"] += energy
    if current is not None and len(events) < limit:
        events.append(current)
    if len(events) != limit:
        raise RuntimeError(f"{path}: parsed {len(events)} events, expected {limit}")
    return events


def compare(reference: list[dict], candidate: list[dict], *, hit_mode: str) -> dict:
    mismatched_ids = []
    mismatched_ti = []
    mismatched_init = []
    mismatched_active_hits = []
    mismatched_htsim = []
    for left, right in zip(reference, candidate, strict=True):
        event_id = left["id"]
        if event_id != right["id"]:
            mismatched_ids.append([event_id, right["id"]])
            continue
        if left["ti"] != right["ti"]:
            mismatched_ti.append(event_id)
        if left["init"] != right["init"]:
            mismatched_init.append(event_id)
        if hit_mode == "active_cc_hit":
            volumes = set(left["hits"]) | set(right["hits"])
            for volume in sorted(volumes):
                a = left["hits"].get(volume, {"count": 0, "sum_keV": 0.0})
                b = right["hits"].get(volume, {"count": 0, "sum_keV": 0.0})
                if a["count"] != b["count"] or not math.isclose(
                    a["sum_keV"], b["sum_keV"], rel_tol=1e-12, abs_tol=1e-9
                ):
                    mismatched_active_hits.append(
                        {
                            "event": event_id,
                            "volume": volume,
                            "reference": a,
                            "candidate": b,
                        }
                    )
        elif hit_mode == "htsim_exact":
            if left["htsim"] != right["htsim"]:
                mismatched_htsim.append(event_id)
        else:
            raise ValueError(hit_mode)
    return {
        "event_count": len(reference),
        "mismatched_ids": len(mismatched_ids),
        "mismatched_ti": len(mismatched_ti),
        "mismatched_init": len(mismatched_init),
        "mismatched_active_volume_event_pairs": len(mismatched_active_hits),
        "mismatched_htsim_events": len(mismatched_htsim),
        "first_active_hit_mismatches": mismatched_active_hits[:10],
        "pass": not (
            mismatched_ids
            or mismatched_ti
            or mismatched_init
            or mismatched_active_hits
            or mismatched_htsim
        ),
    }


def only_sim(directory: Path) -> Path:
    paths = sorted(directory.glob("*.sim")) + sorted(directory.glob("*.sim.gz"))
    if len(paths) != 1:
        raise RuntimeError(f"expected one SIM in {directory}, found {len(paths)}")
    return paths[0]


def main() -> int:
    global MANIFEST, RUN_STATE, OUTPUT
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--state", type=Path, default=RUN_STATE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    MANIFEST = args.manifest.resolve()
    RUN_STATE = args.state.resolve()
    OUTPUT = args.output.resolve()
    if OUTPUT.exists():
        raise FileExistsError(f"non-overwrite validation gate: {OUTPUT}")
    manifest = json.loads(MANIFEST.read_text())
    state = json.loads(RUN_STATE.read_text())
    if state.get("status") != "COMPLETE":
        raise RuntimeError(f"paired pilot is not complete: {state.get('status')}")
    limit = int(manifest["events"])
    baseline = parse_prefix(Path(manifest["baseline_sim"]), limit)
    pilot_paths = {
        row["store_simulation_info"]: only_sim(Path(row["output_root"]) / "pass")
        for row in manifest["jobs"]
    }
    all_events = parse_prefix(pilot_paths["all"], limit)
    init_events = parse_prefix(pilot_paths["init-only"], limit)
    baseline_vs_minimal_all = compare(
        baseline, all_events, hit_mode="active_cc_hit"
    )
    minimal_all_vs_initonly = compare(
        all_events, init_events, hit_mode="htsim_exact"
    )
    result = {
        "schema_version": 1,
        "status": (
            "PASS__ACTIVE_HISTORIES_IDENTICAL"
            if baseline_vs_minimal_all["pass"] and minimal_all_vs_initonly["pass"]
            else "FAIL__ACTIVE_HISTORIES_DIFFER"
        ),
        "events_compared": limit,
        "comparison_scope": "PRIMARY_INIT_TI_AND_12_ACTIVE_VOLUME_CC_HIT_COUNTS_AND_ENERGY_SUMS",
        "baseline_vs_minimal_all": baseline_vs_minimal_all,
        "minimal_all_vs_initonly": minimal_all_vs_initonly,
        "run_state": state,
        "pooling_policy": (
            "POOL_AT_SELECTED_COUNT_AND_EQUIVALENT_EXPOSURE_LEVEL; "
            "KEEP_SETUP_STRATA; DO_NOT_RAW-MERGE_SIM_OR_LEDGER"
        ),
    }
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
