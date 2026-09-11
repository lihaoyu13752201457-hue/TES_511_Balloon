#!/usr/bin/env python3
"""Extract the non-TES 511-keV annihilation partner for retained prompt chains.

This is a read-only lineage and exact point-membership extraction from existing
SIM files.  IA parentage, not Geant4 CC track IDs, defines the photon branch.
No particle transport is run.
"""

from __future__ import annotations

import csv
import gzip
import subprocess
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROMPT_ROOT = HERE.parents[2] / "agents" / "prompt"
S3D_POINTS = PROMPT_ROOT / "prompt_leak_interaction_points.csv"
MASS_HOSTS = PROMPT_ROOT / "mass_model_final_prompt_pair_hosts.csv"
OUT = HERE / "annihilation_partner_paths.csv"
QUERY = HERE.parents[2] / "code" / "query_megalib_geometry"
GEOMETRIES = {
    "S3d_O8": Path(
        "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/"
        "geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/"
        "geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
    ),
    "Mass_model_511": Path(
        "/home/ubuntu/TES_511_Balloon/outputs/geometry/"
        "DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_"
        "20260701_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_"
        "megalib_proxy.geo.setup"
    ),
}


def load_cases() -> list[dict[str, str]]:
    cases: list[dict[str, str]] = []
    with S3D_POINTS.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    by_event: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_event[row["event_id"]].append(row)
    for event_id, event_rows in by_event.items():
        tes = next(row for row in event_rows if row["point_type"] == "TES_HTsim")
        pair = next(row for row in event_rows if row["point_type"] == "PAIR")
        anni = next(row for row in event_rows if row["point_type"] == "ANNI")
        cases.append({
            "geometry": "S3d_O8",
            "family": "gamma",
            "event_id": event_id,
            "source_file": tes["source_file"],
            "tes_annihilation_ia": tes["parent_ia_id"],
            "pair_volume": pair["deepest_true_volume"],
            "pair_material": pair["material"],
            "annihilation_volume": anni["deepest_true_volume"],
            "annihilation_material": anni["material"],
            "init_energy_keV": next(r for r in event_rows if r["point_type"] == "INIT")["energy_keV"],
        })
    with MASS_HOSTS.open(newline="") as stream:
        for row in csv.DictReader(stream):
            cases.append({
                "geometry": "Mass_model_511",
                "family": row["family"],
                "event_id": row["event_id"],
                "source_file": row["source_file"],
                "tes_annihilation_ia": row["tes_lineage_annihilation_ia"],
                "pair_volume": row["tes_lineage_pair_volume"],
                "pair_material": row["tes_lineage_pair_material"],
                "annihilation_volume": row["tes_lineage_annihilation_volume"],
                "annihilation_material": row["tes_lineage_annihilation_material"],
                "init_energy_keV": row["init_energy_keV"],
            })
    return cases


def event_lines(path: str, event_id: str) -> list[str]:
    found = False
    lines: list[str] = []
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if line.startswith("ID "):
                this_id = line.split()[1]
                if found and this_id != event_id:
                    break
                found = this_id == event_id
            if found:
                lines.append(line.rstrip())
    if not lines:
        raise ValueError(f"event {event_id} absent from {path}")
    return lines


def parse_ia(line: str) -> dict[str, object]:
    fields = line.split(";")
    head = fields[0].split()
    return {
        "process": head[1],
        "id": int(head[2]),
        "parent": int(fields[1]),
        "time": float(fields[3]),
        "xyz": tuple(float(fields[i]) for i in (4, 5, 6)),
        "out_type": int(fields[15].split()[0]),
        "direction": tuple(float(fields[i]) for i in (16, 17, 18)),
        "energy": float(fields[22]),
    }


def analyze(case: dict[str, str]) -> dict[str, object]:
    interactions = [
        parse_ia(line) for line in event_lines(case["source_file"], case["event_id"])
        if line.startswith("IA ")
    ]
    parent_of = {int(ia["id"]): int(ia["parent"]) for ia in interactions}
    tes_id = int(case["tes_annihilation_ia"])
    tes_anni = next(ia for ia in interactions if ia["id"] == tes_id and ia["process"] == "ANNI")
    siblings = [
        ia for ia in interactions
        if ia["process"] == "ANNI"
        and ia["id"] != tes_id
        and ia["parent"] == tes_anni["parent"]
        and abs(float(ia["time"]) - float(tes_anni["time"])) < 1e-18
    ]
    if len(siblings) != 1:
        raise ValueError(f"expected one ANNI sibling for {case}, got {siblings}")
    partner = siblings[0]
    partner_id = int(partner["id"])

    def descends_from(ia_id: int, ancestor: int) -> bool:
        seen: set[int] = set()
        while ia_id and ia_id not in seen:
            if ia_id == ancestor:
                return True
            seen.add(ia_id)
            ia_id = parent_of.get(ia_id, 0)
        return False

    branch = sorted(
        [ia for ia in interactions if ia["id"] != partner_id and descends_from(int(ia["id"]), partner_id)],
        key=lambda ia: (float(ia["time"]), int(ia["id"])),
    )
    return {
        **case,
        "tes_annihilation_ia": tes_id,
        "partner_annihilation_ia": partner_id,
        "annihilation_x_cm": tes_anni["xyz"][0],
        "annihilation_y_cm": tes_anni["xyz"][1],
        "annihilation_z_cm": tes_anni["xyz"][2],
        "tes_511_dx": tes_anni["direction"][0],
        "tes_511_dy": tes_anni["direction"][1],
        "tes_511_dz": tes_anni["direction"][2],
        "partner_511_dx": partner["direction"][0],
        "partner_511_dy": partner["direction"][1],
        "partner_511_dz": partner["direction"][2],
        "partner_branch_n_ia": len(branch),
        "_branch": branch,
    }


def query_membership(rows: list[dict[str, object]]) -> dict[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {}
    for geometry, setup in GEOMETRIES.items():
        inputs: list[str] = []
        for row_index, row in enumerate(rows):
            if row["geometry"] != geometry:
                continue
            for branch_index, ia in enumerate(row["_branch"]):
                x, y, z = ia["xyz"]
                inputs.append(f"q{row_index}_{branch_index} {x} {y} {z}")
        proc = subprocess.run(
            [str(QUERY), str(setup)], input="\n".join(inputs) + "\n",
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        )
        for output in proc.stdout.splitlines():
            if not output.startswith("q"):
                continue
            qid, _, _, _, volume, material, _ = output.split(",", 6)
            result[qid] = (volume, material)
    return result


def main() -> None:
    rows = [analyze(case) for case in load_cases()]
    membership = query_membership(rows)
    output_rows: list[dict[str, object]] = []
    for row_index, row in enumerate(rows):
        branch_tokens: list[str] = []
        first_interaction = None
        touched_active = False
        for branch_index, ia in enumerate(row.pop("_branch")):
            volume, material = membership[f"q{row_index}_{branch_index}"]
            process = str(ia["process"])
            branch_tokens.append(f"IA{ia['id']}:{process}@{volume}[{material}]")
            if first_interaction is None and process not in {"ESCP", "RAYL"}:
                first_interaction = (process, volume, material)
            if "BGO" in volume or "Plastic" in volume or "CsI" in volume:
                touched_active = True
        row["partner_first_interaction_process"] = first_interaction[0] if first_interaction else "NONE"
        row["partner_first_interaction_volume"] = first_interaction[1] if first_interaction else "NONE"
        row["partner_first_interaction_material"] = first_interaction[2] if first_interaction else "NONE"
        row["partner_branch_touched_active_volume"] = touched_active
        row["partner_branch"] = "|".join(branch_tokens)
        output_rows.append(row)
    fields = list(output_rows[0])
    with OUT.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output_rows)
    print(f"wrote {len(output_rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
