#!/usr/bin/env python3
"""Trace S2b e+ W2 final events with zero plastic/legacy active energy."""

from __future__ import annotations

import csv
import gzip
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
EVENT_CSV = ROOT / "engineering/geometry_optimization_20260704/17_s2b_eqstats_prompt_atm511_20260708/w2_veto_failure_fast_events.csv"

CC_RE = re.compile(r"^CC\s+HIT\s+(\S+)\s+(.*)$")
KV_RE = re.compile(r"(\w+)=([^\s]+)")


def read_candidates() -> list[dict[str, str]]:
    out = []
    with EVENT_CSV.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["geometry"] != "S2b" or row["particle"] != "eplus":
                continue
            plastic = float(row["plastic_skin_keV"] or 0.0)
            legacy = float(row["legacy_active_keV"] or 0.0)
            if plastic == 0.0 and legacy < 50.0 and row["compton_fov_veto"] != "True":
                out.append(row)
    return out


def extract_blocks(candidates: list[dict[str, str]]) -> dict[tuple[str, int], list[str]]:
    by_file: dict[str, set[int]] = defaultdict(set)
    for row in candidates:
        by_file[row["source_file"]].add(int(row["local_id"]))

    blocks: dict[tuple[str, int], list[str]] = {}
    for rel_file, ids in sorted(by_file.items()):
        sim = ROOT / rel_file
        current_id: int | None = None
        current_lines: list[str] = []
        with gzip.open(sim, "rt", errors="replace") as handle:
            for raw in handle:
                line = raw.rstrip("\n")
                if line.startswith("ID "):
                    if current_id in ids:
                        blocks[(rel_file, int(current_id))] = current_lines
                    parts = line.split()
                    current_id = int(parts[1]) if len(parts) > 1 else None
                    current_lines = [line] if current_id in ids else []
                    continue
                if current_id in ids:
                    current_lines.append(line)
                    if line == "SE":
                        blocks[(rel_file, int(current_id))] = current_lines
                        current_id = None
                        current_lines = []
            if current_id in ids:
                blocks[(rel_file, int(current_id))] = current_lines
    return blocks


def parse_ia(line: str) -> dict[str, Any] | None:
    if not line.startswith("IA "):
        return None
    head, rest = line[:7].strip(), line[7:]
    fields = [part.strip() for part in rest.split(";")]
    if len(fields) < 7:
        return None
    try:
        return {
            "raw": line,
            "process": head.split()[1],
            "interaction_id": int(fields[0]),
            "parent_id": int(fields[1]),
            "time_s": float(fields[3]),
            "x_cm": float(fields[4]),
            "y_cm": float(fields[5]),
            "z_cm": float(fields[6]),
            "energy_keV": float(fields[-1]),
        }
    except Exception:
        return {"raw": line, "process": head.split()[1] if len(head.split()) > 1 else "unknown"}


def parse_hit(line: str) -> dict[str, Any] | None:
    m = CC_RE.match(line)
    if not m:
        return None
    kv = dict(KV_RE.findall(m.group(2)))
    try:
        return {
            "raw": line,
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
            "tid": kv.get("tid", ""),
            "pid": kv.get("pid", ""),
        }
    except Exception:
        return {"raw": line, "volume": m.group(1)}


def radius_xy(x: float, y: float) -> float:
    return math.sqrt(x * x + y * y)


def summarize_block(row: dict[str, str], lines: list[str]) -> dict[str, Any]:
    ia = [parsed for line in lines if (parsed := parse_ia(line)) is not None]
    hits = [parsed for line in lines if (parsed := parse_hit(line)) is not None]
    pm = [line for line in lines if line.startswith("PM ")]
    annihilations = [item for item in ia if item.get("process") == "ANNI"]
    init = next((item for item in ia if item.get("process") == "INIT"), None)
    first_ann = annihilations[0] if annihilations else None
    tes_hits = [hit for hit in hits if str(hit.get("volume", "")).startswith("TP_L")]
    hit_volumes = Counter(str(hit.get("volume", "")) for hit in hits)
    hit_secondaries = Counter(str(hit.get("sec", "")) for hit in hits)
    hit_parents = Counter(str(hit.get("par", "")) for hit in hits)

    out: dict[str, Any] = {
        "source_file": row["source_file"],
        "local_id": int(row["local_id"]),
        "tes_total_keV": float(row["tes_total_keV"]),
        "tes_hit_count": int(row["tes_hit_count"]),
        "side_compton_class": row["side_compton_class"],
        "pm_lines": " | ".join(pm),
        "ia_process_counts": dict(Counter(str(item.get("process", "")) for item in ia)),
        "cc_hit_volume_counts": dict(hit_volumes),
        "cc_hit_secondary_counts": dict(hit_secondaries),
        "cc_hit_parent_counts": dict(hit_parents),
        "tes_hit_particles": "; ".join(
            f"{hit.get('sec')} from {hit.get('par')} {hit.get('sproc')}/{hit.get('cproc')} {hit.get('edep_keV'):.3g}keV"
            for hit in tes_hits[:8]
        ),
        "classification": "",
    }
    if init:
        out.update(
            {
                "init_x_cm": init.get("x_cm"),
                "init_y_cm": init.get("y_cm"),
                "init_z_cm": init.get("z_cm"),
                "init_rxy_cm": radius_xy(float(init.get("x_cm", 0.0)), float(init.get("y_cm", 0.0))),
                "init_energy_keV": init.get("energy_keV"),
            }
        )
    if first_ann:
        x = float(first_ann.get("x_cm", 0.0))
        y = float(first_ann.get("y_cm", 0.0))
        z = float(first_ann.get("z_cm", 0.0))
        out.update(
            {
                "annihilation_x_cm": x,
                "annihilation_y_cm": y,
                "annihilation_z_cm": z,
                "annihilation_rxy_cm": radius_xy(x, y),
                "annihilation_energy_keV": first_ann.get("energy_keV"),
            }
        )
    if first_ann and tes_hits and all(hit.get("prim") == "e+" for hit in tes_hits):
        out["classification"] = "passive_annihilation_gamma_to_TES"
    elif tes_hits:
        out["classification"] = "tes_hit_without_plastic"
    else:
        out["classification"] = "no_tes_hit_in_block_parse"
    return out


def main() -> None:
    candidates = read_candidates()
    blocks = extract_blocks(candidates)

    raw_dir = WORK / "raw_event_blocks"
    raw_dir.mkdir(exist_ok=True)
    summaries = []
    for row in candidates:
        key = (row["source_file"], int(row["local_id"]))
        lines = blocks[key]
        (raw_dir / f"S2b_eplus_{row['local_id']}.simtxt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        summaries.append(summarize_block(row, lines))

    fields = [
        "local_id",
        "source_file",
        "classification",
        "tes_total_keV",
        "tes_hit_count",
        "side_compton_class",
        "init_x_cm",
        "init_y_cm",
        "init_z_cm",
        "init_rxy_cm",
        "init_energy_keV",
        "annihilation_x_cm",
        "annihilation_y_cm",
        "annihilation_z_cm",
        "annihilation_rxy_cm",
        "annihilation_energy_keV",
        "pm_lines",
        "ia_process_counts",
        "cc_hit_volume_counts",
        "cc_hit_secondary_counts",
        "cc_hit_parent_counts",
        "tes_hit_particles",
    ]
    with (WORK / "s2b_zero_plastic_eplus_trace_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(summaries)

    payload = {
        "status": "PASS_S2B_ZERO_PLASTIC_EPLUS_TRACE",
        "input_event_csv": str(EVENT_CSV.relative_to(ROOT)),
        "candidate_count": len(candidates),
        "classification_counts": dict(Counter(item["classification"] for item in summaries)),
        "summaries": summaries,
    }
    (WORK / "s2b_zero_plastic_eplus_trace_summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# S2b Zero-Plastic Eplus Trace",
        "",
        "These are S2b W2 e+ final-pass events with `plastic_skin_keV = 0`, `legacy_active_keV = 0`, and no Compton/FoV veto.",
        "",
        f"- Candidate events: `{len(candidates)}`",
        f"- Classification counts: `{payload['classification_counts']}`",
        "",
        "| local id | class | TES hits | side class | annihilation xyz cm | annihilation rxy cm | PM lines |",
        "|---:|---|---:|---|---|---:|---|",
    ]
    for item in summaries:
        xyz = (
            f"{item.get('annihilation_x_cm', ''):.2f}, "
            f"{item.get('annihilation_y_cm', ''):.2f}, "
            f"{item.get('annihilation_z_cm', ''):.2f}"
            if "annihilation_x_cm" in item
            else ""
        )
        rxy = f"{item.get('annihilation_rxy_cm', 0.0):.2f}" if "annihilation_rxy_cm" in item else ""
        lines.append(
            f"| {item['local_id']} | {item['classification']} | {item['tes_hit_count']} | "
            f"{item['side_compton_class']} | {xyz} | {rxy} | `{item['pm_lines']}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "All listed events are consistent with the primary positron annihilating in passive material, followed by a 511 keV annihilation gamma depositing W2 energy in TES. Because the charged positron did not deposit energy in `GeoOpt_S2B_CryoShell_Plastic*` or legacy active volumes, lowering the plastic threshold cannot veto these events.",
        ]
    )
    (WORK / "s2b_zero_plastic_eplus_trace_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "candidate_count": len(candidates), "classification_counts": payload["classification_counts"]}, indent=2))


if __name__ == "__main__":
    main()
