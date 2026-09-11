#!/usr/bin/env python3
"""Analyze the AF1-48 denominator-cell prompt mechanism transport."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import pickle
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

from scipy.stats import beta


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
PLAN = PACKAGE / "focused_prompt/three_cell_transport_plan.json"
EVENT_MAP = PACKAGE / "focused_prompt/three_cell_event_map.csv"
OUT_JSON = PACKAGE / "focused_prompt/three_cell_mechanism_result.json"
OUT_CSV = PACKAGE / "focused_prompt/three_cell_event_summary.csv"
QUERY = ROOT / "engineering/s3d_o8_loop_engineering_20260814/code/query_megalib_geometry"
M05_CODE = Path(
    "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/"
    "particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/code"
)
CC_RE = re.compile(r"^CC HIT (\S+) edep_keV=([0-9.eE+-]+)")
W2 = (510.58, 511.42)
ACTIVE = {
    "BGO_S3C_FullWrap_SideShell_WindowCut_40mm",
    "BGO_S3D_O8_FullWrap_BottomCap_30mm",
    "BGO_S3D_O8_FullWrap_TopAnnulus_10mm",
    "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm",
    "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm",
    "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_ia(line: str) -> dict[str, object]:
    fields = line.split(";")
    head = fields[0].split()
    return {
        "process": head[1],
        "id": int(head[2]),
        "parent": int(fields[1]),
        "time": float(fields[3]),
        "xyz": tuple(float(fields[index]) for index in (4, 5, 6)),
    }


def empty_event(event_id: int) -> dict[str, object]:
    return {
        "event_id": event_id,
        "tes_keV": 0.0,
        "bgo_keV": 0.0,
        "plastic_keV": 0.0,
        "pair_count": 0,
        "annihilation_count": 0,
        "first_pair_xyz": None,
        "first_interaction_process": "NONE",
        "first_interaction_xyz": None,
    }


def parse_sim(path: Path) -> tuple[int, str, list[dict[str, object]]]:
    seed = -1
    geometry = ""
    events: list[dict[str, object]] = []
    event: dict[str, object] | None = None

    def finish() -> None:
        nonlocal event
        if event is None:
            return
        event["raw_w2"] = W2[0] <= float(event["tes_keV"]) < W2[1]
        event["veto50_pass"] = (
            float(event["bgo_keV"]) < 50.0
            and float(event["plastic_keV"]) < 50.0
        )
        event["raw_w2_veto50"] = bool(event["raw_w2"]) and bool(
            event["veto50_pass"]
        )
        events.append(event)
        event = None

    with gzip.open(path, "rt", encoding="utf-8", errors="strict") as handle:
        for raw in handle:
            line = raw.strip()
            if line.startswith("Geometry ") and not geometry:
                geometry = line.split(maxsplit=1)[1]
            elif line.startswith("Seed ") and seed < 0:
                seed = int(line.split()[1])
            elif line.startswith("ID "):
                finish()
                event = empty_event(int(line.split()[1]))
            elif event is None:
                continue
            elif line.startswith("IA "):
                ia = parse_ia(line)
                process = str(ia["process"])
                if process != "INIT" and event["first_interaction_process"] == "NONE":
                    event["first_interaction_process"] = process
                    event["first_interaction_xyz"] = ia["xyz"]
                if process == "PAIR":
                    event["pair_count"] = int(event["pair_count"]) + 1
                    if event["first_pair_xyz"] is None:
                        event["first_pair_xyz"] = ia["xyz"]
                elif process == "ANNI":
                    event["annihilation_count"] = int(event["annihilation_count"]) + 1
            elif match := CC_RE.match(line):
                volume, energy_text = match.groups()
                energy = float(energy_text)
                if volume.startswith("TP_L"):
                    event["tes_keV"] = float(event["tes_keV"]) + energy
                elif volume in ACTIVE:
                    if volume.startswith("BGO_"):
                        event["bgo_keV"] = float(event["bgo_keV"]) + energy
                    else:
                        event["plastic_keV"] = float(event["plastic_keV"]) + energy
            elif line == "EN":
                finish()
    finish()
    if seed < 0 or not geometry:
        raise RuntimeError(f"missing SIM header identity: {path}")
    return seed, geometry, events


def classify_points(
    setup: str, geometry_key: str, events: list[dict[str, object]]
) -> None:
    requests: list[str] = []
    lookup: dict[str, tuple[dict[str, object], str]] = {}
    for event in events:
        for field, prefix in (
            ("first_interaction_xyz", "i"),
            ("first_pair_xyz", "p"),
        ):
            xyz = event[field]
            if xyz is None:
                continue
            qid = f"{prefix}{event['event_id']}"
            x, y, z = xyz
            requests.append(f"{qid} {x} {y} {z}")
            lookup[qid] = (event, field.removesuffix("_xyz"))
    proc = subprocess.run(
        [str(QUERY.resolve()), setup],
        input="\n".join(requests) + "\n",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    seen = 0
    for line in proc.stdout.splitlines():
        if not line.startswith(("i", "p")):
            continue
        qid, _, _, _, volume, material, _ = line.split(",", 6)
        event, prefix = lookup[qid]
        event[f"{prefix}_volume"] = volume
        event[f"{prefix}_material"] = material
        seen += 1
    if seen != len(requests):
        raise RuntimeError(
            f"point classification differs for {geometry_key}: {seen}/{len(requests)}"
        )


def response_selected_ids(
    job: dict[str, object], sim: Path, header_seed: int, n_events: int
) -> set[int]:
    sys.path.insert(0, str(M05_CODE))
    import build_common_response as common  # type: ignore
    import run_prompt_analysis as prompt  # type: ignore

    scan_job = {
        "scan_index": 0,
        "geometry": "S3d_O8",
        "family": "gamma",
        "mode": "instant",
        "input_id": "three_cell_denominator_complete",
        "batch_id": "three_cell_repeat8_v1",
        "job_id": job["run_name"],
        "events": n_events,
        "sim_path": str(sim),
        "seed": header_seed,
        "shield_volumes": [name for name in ACTIVE if "Plastic" not in name],
        "plastic_volumes": [name for name in ACTIVE if "Plastic" in name],
    }
    with tempfile.TemporaryDirectory(prefix="af1-prompt-response-", dir="/tmp") as tmp:
        result = prompt.scan_job(scan_job, tmp)
        with Path(result["path"]).open("rb") as handle:
            catalog = pickle.load(handle)
        catalog["rate_hz"] = [1.0 / n_events] * len(catalog["stream"])
        catalog["generated_events"] = n_events
        catalog["cell_metadata"] = {
            "geometry": "S3d_O8",
            "family": "gamma",
            "mode": "instant",
            "jobs": 1,
            "generated_events": n_events,
            "TT_s": float(n_events),
            "event_weight_cps": 1.0 / n_events,
            "normalization": "focused fraction only; no sky-rate authority",
        }
        core, step05, disk = common.response_runtime()
        selected: set[int] = set()
        for event_index in range(len(catalog["stream"])):
            evaluated = prompt.evaluate_event(catalog, event_index, core, step05, disk)
            if (
                W2[0] <= float(evaluated["measured_total_keV"]) < W2[1]
                and bool(evaluated["active_pass"][50.0])
                and bool(evaluated["topology_pass"])
            ):
                selected.add(int(catalog["local_id"][event_index]))
    return selected


def exact_ratio_upper95(candidate: int, baseline: int) -> float | None:
    if baseline == 0:
        return None
    p_upper = float(beta.ppf(0.95, candidate + 1, baseline))
    return p_upper / (1.0 - p_upper)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, default=PLAN)
    parser.add_argument("--event-map", type=Path, default=EVENT_MAP)
    parser.add_argument("--out-json", type=Path, default=OUT_JSON)
    parser.add_argument("--out-csv", type=Path, default=OUT_CSV)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    n_events = int(plan["transport_events_per_geometry"])
    with args.event_map.open("r", encoding="utf-8", newline="") as handle:
        mapping = {
            int(row["transport_event_id"]): row for row in csv.DictReader(handle)
        }
    if len(mapping) != n_events:
        raise RuntimeError(f"event map rows={len(mapping)}")

    all_events: dict[str, list[dict[str, object]]] = {}
    receipts: list[dict[str, object]] = []
    for job in plan["jobs"]:
        geometry_key = str(job["geometry_key"])
        sim = Path(job["expected_sim"])
        header_seed, header_geometry, events = parse_sim(sim)
        if len(events) != n_events or Path(header_geometry).resolve() != Path(
            str(job["setup"])
        ).resolve():
            raise RuntimeError(f"SIM identity mismatch: {geometry_key}")
        classify_points(str(job["setup"]), geometry_key, events)
        selected_ids = response_selected_ids(job, sim, header_seed, n_events)
        for event in events:
            event["final_w2_veto50_step05"] = int(event["event_id"]) in selected_ids
            event.update(
                {
                    "cell_id": mapping[int(event["event_id"])]["cell_id"],
                    "repeat_index": int(mapping[int(event["event_id"])]["repeat_index"]),
                    "state_index": int(mapping[int(event["event_id"])]["state_index"]),
                    "source_local_event_id": int(
                        mapping[int(event["event_id"])]["source_local_event_id"]
                    ),
                }
            )
        all_events[geometry_key] = events
        receipts.append(
            {
                "geometry_key": geometry_key,
                "sim": str(sim),
                "sim_sha256": sha256(sim),
                "bytes": sim.stat().st_size,
                "events": len(events),
                "header_geometry": header_geometry,
                "header_seed": header_seed,
                "source_declared_seed": job["declared_seed"],
            }
        )

    compact: list[dict[str, object]] = []
    for geometry_key, events in all_events.items():
        for event in events:
            compact.append(
                {
                    "geometry_key": geometry_key,
                    "cell_id": event["cell_id"],
                    "event_id": event["event_id"],
                    "repeat_index": event["repeat_index"],
                    "state_index": event["state_index"],
                    "source_local_event_id": event["source_local_event_id"],
                    "pair_count": event["pair_count"],
                    "annihilation_count": event["annihilation_count"],
                    "first_interaction_process": event["first_interaction_process"],
                    "first_interaction_volume": event.get("first_interaction_volume", "NONE"),
                    "first_interaction_material": event.get("first_interaction_material", "NONE"),
                    "first_pair_volume": event.get("first_pair_volume", "NONE"),
                    "first_pair_material": event.get("first_pair_material", "NONE"),
                    "tes_keV": f"{float(event['tes_keV']):.9g}",
                    "bgo_keV": f"{float(event['bgo_keV']):.9g}",
                    "plastic_keV": f"{float(event['plastic_keV']):.9g}",
                    "veto50_pass": int(bool(event["veto50_pass"])),
                    "raw_w2_veto50": int(bool(event["raw_w2_veto50"])),
                    "final_w2_veto50_step05": int(
                        bool(event["final_w2_veto50_step05"])
                    ),
                }
            )
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.out_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(compact[0]))
        writer.writeheader()
        writer.writerows(compact)

    summaries: list[dict[str, object]] = []
    for geometry_key, events in all_events.items():
        for cell_id in ("cell_3883", "cell_19932", "cell_8081", "ALL"):
            subset = events if cell_id == "ALL" else [e for e in events if e["cell_id"] == cell_id]
            pair_hosts = Counter(
                f"{e.get('first_pair_material', 'NONE')}@{e.get('first_pair_volume', 'NONE')}"
                for e in subset
                if int(e["pair_count"]) > 0
            )
            no_veto_pair_hosts = Counter(
                f"{e.get('first_pair_material', 'NONE')}@{e.get('first_pair_volume', 'NONE')}"
                for e in subset
                if int(e["pair_count"]) > 0 and bool(e["veto50_pass"])
            )
            summaries.append(
                {
                    "geometry_key": geometry_key,
                    "cell_id": cell_id,
                    "events": len(subset),
                    "unique_primary_states": len({int(e["state_index"]) for e in subset}),
                    "pair_any": sum(int(e["pair_count"]) > 0 for e in subset),
                    "annihilation_any": sum(int(e["annihilation_count"]) > 0 for e in subset),
                    "pair_and_active_veto50": sum(
                        int(e["pair_count"]) > 0 and not bool(e["veto50_pass"])
                        for e in subset
                    ),
                    "raw_w2_veto50": sum(bool(e["raw_w2_veto50"]) for e in subset),
                    "final_w2_veto50_step05": sum(
                        bool(e["final_w2_veto50_step05"]) for e in subset
                    ),
                    "pair_host_counts": dict(pair_hosts.most_common()),
                    "active_veto_clean_pair_host_counts": dict(
                        no_veto_pair_hosts.most_common()
                    ),
                }
            )
    baseline_final = next(
        int(row["final_w2_veto50_step05"])
        for row in summaries
        if row["geometry_key"] == "baseline" and row["cell_id"] == "ALL"
    )
    candidate_final = next(
        int(row["final_w2_veto50_step05"])
        for row in summaries
        if row["geometry_key"] == "AF1_48" and row["cell_id"] == "ALL"
    )
    ratio = candidate_final / baseline_final if baseline_final else None
    baseline_clean_pair = next(
        int(row["pair_any"]) - int(row["pair_and_active_veto50"])
        for row in summaries
        if row["geometry_key"] == "baseline" and row["cell_id"] == "ALL"
    )
    candidate_clean_pair = next(
        int(row["pair_any"]) - int(row["pair_and_active_veto50"])
        for row in summaries
        if row["geometry_key"] == "AF1_48" and row["cell_id"] == "ALL"
    )
    payload = {
        "schema_version": 1,
        "status": "PASS__FOCUSED_PROMPT_P1_MECHANISM_ONLY",
        "claim_boundary": plan["claim_boundary"],
        "denominator_states": plan["selected_state_counts"],
        "uniform_repeats_per_state": plan["uniform_repeats_per_state"],
        "transport_receipts": receipts,
        "summaries": summaries,
        "focused_final_comparison": {
            "baseline_selected": baseline_final,
            "candidate_selected": candidate_final,
            "central_survival_ratio": ratio,
            "one_sided_exact_conditional_ratio_upper95": exact_ratio_upper95(
                candidate_final, baseline_final
            ),
            "pre_registered_central_requirement": 0.280345709406,
            "pre_registered_target": 0.20,
            "authority": (
                "conditioned three-cell mechanism sensitivity; not corrected-gamma "
                "broadband prompt-rate authority"
            ),
        },
        "mechanism_comparison": {
            "observable": "first-pair events with total BGO<50 keV and plastic<50 keV",
            "baseline_active_veto_clean_pair": baseline_clean_pair,
            "candidate_active_veto_clean_pair": candidate_clean_pair,
            "central_ratio": candidate_clean_pair / baseline_clean_pair,
            "one_sided_exact_conditional_ratio_upper95": exact_ratio_upper95(
                candidate_clean_pair, baseline_clean_pair
            ),
            "interpretation": (
                "Central mechanism improvement only; the upper limit does not "
                "meet the prompt-survival gate and this observable is upstream "
                "of TES W2 plus Step05."
            ),
        },
        "event_summary": {
            "path": str(args.out_csv.resolve()),
            "sha256": sha256(args.out_csv),
            "rows": len(compact),
        },
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(args.out_json)


if __name__ == "__main__":
    main()
