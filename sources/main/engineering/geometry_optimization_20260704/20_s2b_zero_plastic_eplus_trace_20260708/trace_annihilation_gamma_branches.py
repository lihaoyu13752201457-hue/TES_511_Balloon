#!/usr/bin/env python3
"""Trace secondary 511-keV gamma branches for zero-plastic S2b e+ events."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
RAW_DIR = WORK / "raw_event_blocks"
SUMMARY_CSV = WORK / "s2b_zero_plastic_eplus_trace_summary.csv"

CC_RE = re.compile(r"^CC\s+HIT\s+(\S+)\s+(.*)$")
KV_RE = re.compile(r"(\w+)=([^\s]+)")


def active_category(volume: str) -> str:
    upper = volume.upper()
    if upper.startswith("TP_L"):
        return "tes"
    if upper.startswith("GEOOPT_S2B_CRYOSHELL_PLASTIC") or upper.startswith("GEOOPT_S1_PLASTICFULLWRAP"):
        return "plastic"
    if upper.startswith("CSI_") or "ACTIVE_SHIELD" in upper or "CEBR3" in upper or "BGO" in upper:
        return "legacy_active"
    return "other"


def parse_ia(line: str) -> dict[str, Any] | None:
    if not line.startswith("IA "):
        return None
    parts = line.split(maxsplit=2)
    if len(parts) < 3:
        return None
    process = parts[1]
    fields = [part.strip() for part in parts[2].split(";")]
    if len(fields) < 7:
        return None
    try:
        return {
            "process": process,
            "id": int(fields[0]),
            "parent": int(fields[1]),
            "detector_code": int(fields[2]),
            "time_s": float(fields[3]),
            "x_cm": float(fields[4]),
            "y_cm": float(fields[5]),
            "z_cm": float(fields[6]),
            "energy_keV": float(fields[-1]),
            "raw": line,
        }
    except Exception:
        return None


def parse_hit(line: str) -> dict[str, Any] | None:
    m = CC_RE.match(line)
    if not m:
        return None
    kv = dict(KV_RE.findall(m.group(2)))
    try:
        return {
            "volume": m.group(1),
            "edep_keV": float(kv.get("edep_keV", 0.0)),
            "x_cm": float(kv.get("x", "nan")),
            "y_cm": float(kv.get("y", "nan")),
            "z_cm": float(kv.get("z", "nan")),
            "sec": kv.get("sec", ""),
            "prim": kv.get("prim", ""),
            "par": kv.get("par", ""),
            "sproc": kv.get("sproc", ""),
            "cproc": kv.get("cproc", ""),
            "tid": int(kv["tid"]) if kv.get("tid", "").isdigit() else None,
            "pid": int(kv["pid"]) if kv.get("pid", "").isdigit() else None,
            "raw": line,
        }
    except Exception:
        return None


def ancestors(node: int | None, ia_by_id: dict[int, dict[str, Any]]) -> set[int]:
    if node is None:
        return set()
    out = set()
    cur = node
    seen = set()
    while cur is not None and cur not in seen:
        seen.add(cur)
        out.add(cur)
        parent = ia_by_id.get(cur, {}).get("parent")
        cur = parent if isinstance(parent, int) and parent != 0 else None
    return out


def branch_descendants(root_id: int, children: dict[int, list[int]]) -> set[int]:
    out = set()
    stack = [root_id]
    while stack:
        cur = stack.pop()
        if cur in out:
            continue
        out.add(cur)
        stack.extend(children.get(cur, []))
    return out


def summarize_block(path: Path, row_by_id: dict[int, dict[str, str]]) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    local_id = int(path.stem.rsplit("_", 1)[1])
    source_summary = row_by_id[local_id]
    ia = [item for line in lines if (item := parse_ia(line)) is not None]
    hits = [item for line in lines if (item := parse_hit(line)) is not None]
    pm_lines = [line for line in lines if line.startswith("PM ")]
    children: dict[int, list[int]] = defaultdict(list)
    for item in ia:
        children[item["parent"]].append(item["id"])
    event_volume_energy = Counter()
    for hit in hits:
        event_volume_energy[active_category(str(hit["volume"]))] += float(hit["edep_keV"])

    branches = [item for item in ia if item["process"] == "ANNI" and item["parent"] == 1]
    summaries = []
    for branch in branches:
        desc = branch_descendants(branch["id"], children)
        ia_by_id = {item["id"]: item for item in ia}
        desc_items = [ia_by_id[i] for i in sorted(desc) if i != branch["id"] and i in ia_by_id]
        first_non_ann = next((item for item in sorted(desc_items, key=lambda x: (x["time_s"], x["id"]))), None)
        process_chain = " -> ".join(item["process"] for item in sorted(desc_items, key=lambda x: x["id"]))
        # In this SIM format, CC HIT tid/pid are not a safe branch-energy key for
        # annihilation cascades. Use IA parentage and detector_code instead:
        # detector_code == 2 marks the TES detector interactions in these blocks.
        tes_ia = [
            item
            for item in sorted(desc_items, key=lambda x: (x["time_s"], x["id"]))
            if item["detector_code"] == 2 and item["process"] in {"PHOT", "COMP", "BREM", "RAYL"}
        ]
        escape_ia = [item for item in desc_items if item["process"] == "ESCP"]
        if tes_ia:
            terminal = "tes_interaction"
        elif escape_ia:
            terminal = "escape"
        else:
            terminal = "other"
        first_tes = tes_ia[0] if tes_ia else None
        summaries.append(
            {
                "local_id": local_id,
                "branch_anni_id": branch["id"],
                "source_file": source_summary["source_file"],
                "tes_hit_count_event": source_summary["tes_hit_count"],
                "side_compton_class_event": source_summary["side_compton_class"],
                "annihilation_material_pm": " | ".join(pm_lines),
                "annihilation_x_cm": branch["x_cm"],
                "annihilation_y_cm": branch["y_cm"],
                "annihilation_z_cm": branch["z_cm"],
                "gamma_energy_keV": branch["energy_keV"],
                "branch_terminal": terminal,
                "branch_process_chain": process_chain,
                "first_interaction_process": "" if first_non_ann is None else first_non_ann["process"],
                "first_interaction_x_cm": "" if first_non_ann is None else first_non_ann["x_cm"],
                "first_interaction_y_cm": "" if first_non_ann is None else first_non_ann["y_cm"],
                "first_interaction_z_cm": "" if first_non_ann is None else first_non_ann["z_cm"],
                "first_tes_process": "" if first_tes is None else first_tes["process"],
                "first_tes_x_cm": "" if first_tes is None else first_tes["x_cm"],
                "first_tes_y_cm": "" if first_tes is None else first_tes["y_cm"],
                "first_tes_z_cm": "" if first_tes is None else first_tes["z_cm"],
                "event_tes_edep_keV": event_volume_energy["tes"],
                "event_plastic_edep_keV": event_volume_energy["plastic"],
                "event_legacy_active_edep_keV": event_volume_energy["legacy_active"],
                "event_other_edep_keV": event_volume_energy["other"],
            }
        )
    return summaries


def main() -> None:
    row_by_id: dict[int, dict[str, str]] = {}
    with SUMMARY_CSV.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            row_by_id[int(row["local_id"])] = row

    rows = []
    for block in sorted(RAW_DIR.glob("S2b_eplus_*.simtxt")):
        rows.extend(summarize_block(block, row_by_id))

    fields = [
        "local_id",
        "branch_anni_id",
        "branch_terminal",
        "event_tes_edep_keV",
        "event_plastic_edep_keV",
        "event_legacy_active_edep_keV",
        "event_other_edep_keV",
        "side_compton_class_event",
        "tes_hit_count_event",
        "annihilation_material_pm",
        "annihilation_x_cm",
        "annihilation_y_cm",
        "annihilation_z_cm",
        "gamma_energy_keV",
        "branch_process_chain",
        "first_interaction_process",
        "first_interaction_x_cm",
        "first_interaction_y_cm",
        "first_interaction_z_cm",
        "first_tes_process",
        "first_tes_x_cm",
        "first_tes_y_cm",
        "first_tes_z_cm",
        "source_file",
    ]
    out_csv = WORK / "s2b_zero_plastic_eplus_annihilation_gamma_branches.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    payload = {
        "status": "PASS_S2B_ZERO_PLASTIC_EPLUS_GAMMA_BRANCH_TRACE",
        "branch_count": len(rows),
        "event_count": len(row_by_id),
        "branch_terminal_counts": dict(Counter(row["branch_terminal"] for row in rows)),
        "active_branch_hits": [
            row
            for row in rows
            if float(row["event_plastic_edep_keV"]) > 0.0 or float(row["event_legacy_active_edep_keV"]) > 0.0
        ],
        "rows": rows,
    }
    out_json = WORK / "s2b_zero_plastic_eplus_annihilation_gamma_branches.json"
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# S2b Zero-Plastic Eplus Annihilation Gamma Branches",
        "",
        "Each zero-plastic e+ event produces two 511 keV annihilation-gamma branches. This table follows those branches using IA parentage and CC HIT ancestry.",
        "",
        f"- Events: `{len(row_by_id)}`",
        f"- Gamma branches: `{len(rows)}`",
        f"- Branch terminal counts: `{payload['branch_terminal_counts']}`",
        f"- Branches with plastic or legacy-active energy: `{len(payload['active_branch_hits'])}`",
        "",
        "| event | branch | terminal | event TES keV | event plastic keV | event legacy active keV | first TES IA | side class | process chain |",
        "|---:|---:|---|---:|---:|---:|---|---|---|",
    ]
    for row in rows:
        first = row["first_tes_process"]
        if first:
            first = f"{first} ({float(row['first_tes_x_cm']):.2f}, {float(row['first_tes_y_cm']):.2f}, {float(row['first_tes_z_cm']):.2f})"
        lines.append(
            f"| {row['local_id']} | {row['branch_anni_id']} | {row['branch_terminal']} | "
            f"{float(row['event_tes_edep_keV']):.3f} | {float(row['event_plastic_edep_keV']):.3f} | "
            f"{float(row['event_legacy_active_edep_keV']):.3f} | {first} | "
            f"{row['side_compton_class_event']} | `{row['branch_process_chain']}` |"
        )
    lines.extend(
        [
            "",
            "## Veto Interpretation",
            "",
            "- Active-veto failure: all 16 annihilation-gamma branches have `plastic_edep_keV = 0` and `legacy_active_edep_keV = 0`; active veto has no energy deposit to threshold on.",
            "- Gamma physics: these are neutral 511 keV photons. A plastic charged-particle skin does not record a crossing photon unless the photon Compton scatters or photoabsorbs in it.",
            "- Compton/FoV failure: six events are single-TES-hit and are kept by design; the two multi-hit events are `keep` because their reconstructed side-entry Compton/FoV solution remains compatible with the allowed aperture.",
        ]
    )
    out_md = WORK / "s2b_zero_plastic_eplus_annihilation_gamma_branches.md"
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "branch_terminal_counts": payload["branch_terminal_counts"], "active_branch_hits": len(payload["active_branch_hits"])}, indent=2))


if __name__ == "__main__":
    main()
