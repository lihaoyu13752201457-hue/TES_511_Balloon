#!/usr/bin/env python3
"""Stream the validated LC1 SIM files and compare paired mechanism cells."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import re
import argparse
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
PLAN = PACKAGE / "data/lc1_smoke_plan_v2.json"
LEDGER = PACKAGE / "data/lc1_smoke_ledger_v2.json"
OUT_JSON = PACKAGE / "data/lc1_smoke_analysis.json"
OUT_CSV = PACKAGE / "data/lc1_smoke_event_summary.csv"
ACTIVE_INPUT = ROOT / "engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/analysis_inputs.json"
W2 = (510.58, 511.42)
TARGET_PREFIXES = (
    "ColdPlate_MXC_50mK_SD_anchor",
    "Cu_50mK_StillLike_Can_bottom_cap_2mm",
    "DR_MixingChamber_Cu",
    "Cu_SubstrateSupport_",
    "Nb_MagShield_Inner_Cylinder_2mm",
    "Nb_MagShield_Inner_Back_ColdFingerCap_2mm",
    "MuMetal_MagShield_Outer_Cylinder_2mm",
)
CC_RE = re.compile(r"^CC HIT (\S+) edep_keV=([0-9.eE+-]+)")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def empty_event() -> dict:
    return {
        "event_id": None,
        "tes_keV": 0.0,
        "bgo_keV": 0.0,
        "plastic_keV": 0.0,
        "target_keV": defaultdict(float),
        "pair_count": 0,
        "anni_count": 0,
        "first_pair_xyz_cm": None,
    }


def parse_sim(path: Path, active: set[str]) -> list[dict]:
    events = []
    event = None

    def finish() -> None:
        nonlocal event
        if event is None or event["event_id"] is None:
            return
        event["target_keV"] = dict(event["target_keV"])
        event["raw_w2"] = W2[0] <= event["tes_keV"] <= W2[1]
        event["veto50_pass"] = event["bgo_keV"] < 50.0 and event["plastic_keV"] < 50.0
        event["w2_veto50"] = event["raw_w2"] and event["veto50_pass"]
        events.append(event)
        event = None

    with gzip.open(path, "rt", encoding="utf-8", errors="strict") as f:
        for raw in f:
            line = raw.strip()
            if line.startswith("ID "):
                finish()
                event = empty_event()
                event["event_id"] = int(line.split()[1])
            elif event is None:
                continue
            elif match := CC_RE.match(line):
                volume, energy_text = match.groups()
                energy = float(energy_text)
                if volume.startswith("TP_L"):
                    event["tes_keV"] += energy
                if volume in active:
                    if volume.startswith("BGO_"):
                        event["bgo_keV"] += energy
                    elif volume.startswith("GeoOpt_"):
                        event["plastic_keV"] += energy
                for prefix in TARGET_PREFIXES:
                    if volume.startswith(prefix):
                        event["target_keV"][prefix] += energy
                        break
            elif line.startswith("IA PAIR"):
                event["pair_count"] += 1
                if event["first_pair_xyz_cm"] is None:
                    fields = [field.strip() for field in line.split("PAIR", 1)[1].split(";")]
                    event["first_pair_xyz_cm"] = [float(fields[i]) for i in (4, 5, 6)]
            elif line.startswith("IA ANNI"):
                event["anni_count"] += 1
            elif line == "EN":
                finish()
    finish()
    return events


def summarize(events: list[dict]) -> dict:
    return {
        "events": len(events),
        "pair_any": sum(e["pair_count"] > 0 for e in events),
        "annihilation_any": sum(e["anni_count"] > 0 for e in events),
        "raw_w2": sum(e["raw_w2"] for e in events),
        "veto50_pass_all_energy": sum(e["veto50_pass"] for e in events),
        "raw_w2_and_veto50_pass": sum(e["w2_veto50"] for e in events),
        "raw_w2_and_veto50_fraction": sum(e["w2_veto50"] for e in events) / len(events),
        "pair_host_target_hit_any": {
            prefix: sum(e["target_keV"].get(prefix, 0.0) > 0 for e in events)
            for prefix in TARGET_PREFIXES
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, default=PLAN)
    parser.add_argument("--ledger", type=Path, default=LEDGER)
    parser.add_argument("--out-json", type=Path, default=OUT_JSON)
    parser.add_argument("--out-csv", type=Path, default=OUT_CSV)
    args = parser.parse_args()
    args.plan = args.plan.resolve()
    args.ledger = args.ledger.resolve()
    args.out_json = args.out_json.resolve()
    args.out_csv = args.out_csv.resolve()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
    if ledger.get("status") != "PASS_LC1_SERIAL_SMOKE_TRANSPORT":
        raise RuntimeError("transport ledger is not PASS")
    if ledger.get("plan_sha256") != sha256(args.plan):
        raise RuntimeError("ledger/plan hash mismatch")
    active = set(json.loads(ACTIVE_INPUT.read_text(encoding="utf-8"))["geometries"]["S3d_O8"]["active_veto_volumes"])
    if len(active) != 6:
        raise RuntimeError("active-veto contract is not six exact volumes")
    plan_jobs = {j["job_id"]: j for j in plan["jobs"]}
    records = []
    compact_rows = []
    by_cell_geometry = {}
    for receipt in ledger["jobs"]:
        job = plan_jobs[receipt["job_id"]]
        path = Path(receipt["sim"]["path"])
        if sha256(path) != receipt["sim"]["sha256"]:
            raise RuntimeError(f"SIM changed: {path}")
        events = parse_sim(path, active)
        if len(events) != job["n_events"]:
            raise RuntimeError(f"event count mismatch: {job['job_id']}")
        summary = summarize(events)
        record = {
            "job_id": job["job_id"],
            "cell_id": job["cell_id"],
            "geometry_key": job["geometry_key"],
            "seed": job["seed"],
            "sim_sha256": receipt["sim"]["sha256"],
            **summary,
        }
        records.append(record)
        by_cell_geometry[(job["cell_id"], job["geometry_key"])] = {e["event_id"]: e for e in events}
        for e in events:
            compact_rows.append({
                "cell_id": job["cell_id"],
                "geometry_key": job["geometry_key"],
                "event_id": e["event_id"],
                "tes_keV": f"{e['tes_keV']:.9g}",
                "bgo_keV": f"{e['bgo_keV']:.9g}",
                "plastic_keV": f"{e['plastic_keV']:.9g}",
                "pair_count": e["pair_count"],
                "anni_count": e["anni_count"],
                "raw_w2": int(e["raw_w2"]),
                "veto50_pass": int(e["veto50_pass"]),
                "w2_veto50": int(e["w2_veto50"]),
                "first_pair_x_cm": "" if e["first_pair_xyz_cm"] is None else f"{e['first_pair_xyz_cm'][0]:.8g}",
                "first_pair_y_cm": "" if e["first_pair_xyz_cm"] is None else f"{e['first_pair_xyz_cm'][1]:.8g}",
                "first_pair_z_cm": "" if e["first_pair_xyz_cm"] is None else f"{e['first_pair_xyz_cm'][2]:.8g}",
            })

    comparisons = []
    cells = sorted({j["cell_id"] for j in plan["jobs"]})
    for cell in cells:
        base = by_cell_geometry[(cell, "A_baseline")]
        for candidate in ("LC1_Cu", "LC1_CuNb"):
            cand = by_cell_geometry[(cell, candidate)]
            if set(base) != set(cand):
                raise RuntimeError(f"paired event IDs differ: {cell} {candidate}")
            table = Counter((int(base[i]["w2_veto50"]), int(cand[i]["w2_veto50"])) for i in base)
            comparisons.append({
                "cell_id": cell,
                "candidate": candidate,
                "baseline_pass": sum(e["w2_veto50"] for e in base.values()),
                "candidate_pass": sum(e["w2_veto50"] for e in cand.values()),
                "paired_00": table[(0, 0)],
                "paired_01": table[(0, 1)],
                "paired_10": table[(1, 0)],
                "paired_11": table[(1, 1)],
            })
    with args.out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(compact_rows[0]))
        writer.writeheader()
        writer.writerows(compact_rows)
    output = {
        "schema_version": 1,
        "status": "PASS_LC1_MECHANISM_SMOKE_ANALYSIS__NO_RATE_OR_PROMOTION_AUTHORITY",
        "window_keV": list(W2),
        "veto_threshold_keV": 50.0,
        "active_veto_volumes": sorted(active),
        "jobs": records,
        "paired_comparisons": comparisons,
        "event_summary_csv": {"path": str(args.out_csv.relative_to(ROOT)), "sha256": sha256(args.out_csv), "rows": len(compact_rows)},
        "claim_boundary": "Fixed-direction/focused conditional mechanism evidence only; no broadband prompt rate or activation/delayed closure.",
    }
    args.out_json.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.out_json)


if __name__ == "__main__":
    main()
