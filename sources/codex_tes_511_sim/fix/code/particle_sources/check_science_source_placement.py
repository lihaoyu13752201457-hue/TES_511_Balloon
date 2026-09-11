#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gate A: science-source placement sanity checks.

This script is intentionally conservative. It does not infer hidden unit
conversions from comments. It reads the source, geometry and, when available,
the SIM file itself, then checks whether the science beam starts outside the
Be entrance window and outside the TES stack in the same coordinate system that
Cosima records in the SIM.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT / "particle_sources" / "run_configs" / "Science_511_onaxis_focalbeam_local.source"
DEFAULT_GEO = ROOT / "code" / "geometry" / "TibetTES_v5_6layers.geo"
DEFAULT_DET = ROOT / "code" / "geometry" / "TibetTES_v5_6layers.det"
DEFAULT_SIM = ROOT / "simulation" / "science_511_onaxis_source" / "Science_511_onaxis_focalbeam_cmfix.inc1.id1.sim.gz"
DEFAULT_OUT = ROOT / "statistics" / "nextphase_511" / "gate_A_source_placement"

BEAM_RE = re.compile(
    r"^(?P<name>\S+)\.Beam\s+HomogeneousBeam\s+"
    r"(?P<x>[-+0-9.eE]+)\s+(?P<y>[-+0-9.eE]+)\s+(?P<z>[-+0-9.eE]+)\s+"
    r"(?P<dx>[-+0-9.eE]+)\s+(?P<dy>[-+0-9.eE]+)\s+(?P<dz>[-+0-9.eE]+)\s+"
    r"(?P<radius>[-+0-9.eE]+)"
)
SIM_BEAM_RE = re.compile(
    r"^BeamType\s+HomogeneousBeam\s+"
    r"(?P<x>[-+0-9.eE]+)\s+(?P<y>[-+0-9.eE]+)\s+(?P<z>[-+0-9.eE]+)\s+"
    r"(?P<dx>[-+0-9.eE]+)\s+(?P<dy>[-+0-9.eE]+)\s+(?P<dz>[-+0-9.eE]+)\s+"
    r"(?P<radius>[-+0-9.eE]+)"
)
POSITION_RE = re.compile(r"^(?P<name>\S+)\.Position\s+(?P<x>[-+0-9.eE]+)\s+(?P<y>[-+0-9.eE]+)\s+(?P<z>[-+0-9.eE]+)")
SHAPE_RE = re.compile(r"^(?P<name>\S+)\.Shape\s+(?P<kind>\S+)\s+(?P<args>.*)$")
ID_RE = re.compile(r"^ID\s+(\d+)")
CC_RE = re.compile(r"^CC\s+HIT\s+(?P<vol>\S+)\s+(?P<rest>.*)$")
KV_RE = re.compile(r"(\w+)=([^\s]+)")
IA_INIT_RE = re.compile(r"^IA INIT\s+\S+\s+\S+\s*\S*\s*;\s*(?P<x>[-+0-9.]+);\s*(?P<y>[-+0-9.]+);\s*(?P<z>[-+0-9.]+);")


def open_text(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return path.open("r", encoding="utf-8", errors="ignore")


def parse_source(path: Path) -> dict[str, Any]:
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = BEAM_RE.match(line.strip())
        if m:
            vals = {k: float(m.group(k)) for k in ("x", "y", "z", "dx", "dy", "dz", "radius")}
            vals["source_name"] = m.group("name")
            vals["beam_type"] = "HomogeneousBeam"
            return vals
    raise ValueError(f"No HomogeneousBeam line found in {path}")


def parse_shape_hz_and_radius(kind: str, args: str) -> tuple[float | None, float | None]:
    vals = [float(x) for x in args.split()]
    if kind == "BRIK" and len(vals) >= 3:
        return vals[2], math.hypot(vals[0], vals[1])
    if kind == "PCON" and len(vals) >= 6:
        # PCON phi_start phi_stop n z r_in r_out ...
        n = int(vals[2])
        triples = vals[3:3 + 3 * n]
        zs = triples[0::3]
        rout = triples[2::3]
        if zs:
            return 0.5 * (max(zs) - min(zs)), max(rout)
    return None, None


def parse_geometry(path: Path) -> dict[str, dict[str, Any]]:
    shapes: dict[str, dict[str, Any]] = {}
    positions: dict[str, tuple[float, float, float]] = {}
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        m_shape = SHAPE_RE.match(line)
        if m_shape:
            hz, radius = parse_shape_hz_and_radius(m_shape.group("kind"), m_shape.group("args"))
            shapes[m_shape.group("name")] = {
                "kind": m_shape.group("kind"),
                "args": m_shape.group("args"),
                "hz": hz,
                "radius": radius,
            }
        m_pos = POSITION_RE.match(line)
        if m_pos:
            positions[m_pos.group("name")] = (float(m_pos.group("x")), float(m_pos.group("y")), float(m_pos.group("z")))
    out: dict[str, dict[str, Any]] = {}
    for name, shape in shapes.items():
        rec = dict(shape)
        if name in positions:
            rec["position"] = positions[name]
            zc = positions[name][2]
            if rec.get("hz") is not None:
                rec["z_min"] = zc - rec["hz"]
                rec["z_max"] = zc + rec["hz"]
        out[name] = rec
    return out


def parse_sim(path: Path, max_events: int) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "exists": path.exists(),
        "beam": None,
        "events_seen": 0,
        "ia_init_z": [],
        "first_cc_volume": Counter(),
        "first_cc_z": [],
        "first_tes_layer": Counter(),
        "first_tes_z": [],
        "first_tes_volume": Counter(),
        "has_win_be_hit": 0,
    }
    if not path.exists():
        return stats

    cur_id = None
    first_cc_done = False
    first_tes_done = False
    has_win = False

    def flush():
        nonlocal cur_id, first_cc_done, first_tes_done, has_win
        if cur_id is not None:
            stats["events_seen"] += 1
            if has_win:
                stats["has_win_be_hit"] += 1
        cur_id = None
        first_cc_done = False
        first_tes_done = False
        has_win = False

    with open_text(path) as fh:
        for raw in fh:
            line = raw.strip()
            m_beam = SIM_BEAM_RE.match(line)
            if m_beam:
                stats["beam"] = {k: float(m_beam.group(k)) for k in ("x", "y", "z", "dx", "dy", "dz", "radius")}
            if line == "SE":
                flush()
                if stats["events_seen"] >= max_events:
                    break
                continue
            m_id = ID_RE.match(line)
            if m_id:
                cur_id = int(m_id.group(1))
                continue
            m_init = IA_INIT_RE.match(line)
            if m_init:
                stats["ia_init_z"].append(float(m_init.group("z")))
                continue
            m_cc = CC_RE.match(line)
            if not m_cc:
                continue
            vol = m_cc.group("vol")
            kv = dict(KV_RE.findall(m_cc.group("rest")))
            z = float(kv["z"]) if "z" in kv else float("nan")
            if "WIN_BE" in vol.upper():
                has_win = True
            if not first_cc_done:
                stats["first_cc_volume"][vol] += 1
                stats["first_cc_z"].append(z)
                first_cc_done = True
            if vol.startswith("TP_L") and not first_tes_done:
                lm = re.match(r"TP_L(\d+)_", vol)
                layer = lm.group(1) if lm else "unknown"
                stats["first_tes_layer"][layer] += 1
                stats["first_tes_volume"][vol] += 1
                stats["first_tes_z"].append(z)
                first_tes_done = True
    flush()
    return stats


def write_table(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({k for row in rows for k in row})
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--science-source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--geometry", type=Path, default=DEFAULT_GEO)
    ap.add_argument("--detector", type=Path, default=DEFAULT_DET)
    ap.add_argument("--science-sim", type=Path, default=DEFAULT_SIM)
    ap.add_argument("--max-events", type=int, default=5000)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    source = parse_source(args.science_source)
    geo = parse_geometry(args.geometry)
    sim = parse_sim(args.science_sim, args.max_events)

    win_be = geo.get("Win_Be")
    tes_layers = {k: v for k, v in geo.items() if re.match(r"TES_L\d+$", k)}
    if win_be is None:
        raise ValueError("Win_Be not found in geometry")

    source_z = float(source["z"])
    source_radius = float(source["radius"])
    win_top = float(win_be["z_max"])
    win_radius = float(win_be["radius"])
    clearance = source_z - win_top
    inside_tes = []
    for name, rec in sorted(tes_layers.items()):
        if rec.get("z_min") is not None and rec["z_min"] <= source_z <= rec["z_max"]:
            inside_tes.append(name)

    source_static_pass = (
        source["dz"] < 0
        and clearance > 0
        and clearance <= 0.2
        and source_radius <= win_radius
        and not inside_tes
    )
    sim_beam_match = True
    if sim["beam"] is not None:
        sim_beam_match = abs(float(sim["beam"]["z"]) - source_z) < 1.0e-6
    first_cc_in_tes_at_source = False
    if sim["first_cc_z"]:
        median_first_cc_z = sorted(sim["first_cc_z"])[len(sim["first_cc_z"]) // 2]
        first_cc_in_tes_at_source = abs(median_first_cc_z - source_z) < 1.0e-3 and bool(sim["first_tes_layer"])
    else:
        median_first_cc_z = None
    sim_pass = (not args.science_sim.exists()) or (sim_beam_match and not first_cc_in_tes_at_source)
    gate_pass = bool(source_static_pass and sim_pass)

    rows = [
        {
            "item": "source_beam",
            "z": source_z,
            "radius": source_radius,
            "dz": source["dz"],
            "note": "HomogeneousBeam from source file",
        },
        {
            "item": "Win_Be",
            "z_center": win_be["position"][2],
            "z_min": win_be["z_min"],
            "z_max": win_be["z_max"],
            "radius": win_radius,
            "note": "Entrance window from geometry",
        },
        {
            "item": "source_to_Win_Be_top_clearance",
            "z": clearance,
            "note": "Positive small value is expected for +z entrance source",
        },
    ]
    for name, rec in sorted(tes_layers.items()):
        rows.append({
            "item": name,
            "z_center": rec["position"][2],
            "z_min": rec["z_min"],
            "z_max": rec["z_max"],
            "radius": rec["radius"],
            "source_inside": name in inside_tes,
        })
    write_table(out / "source_geometry_table.csv", rows)

    fv_rows = [{"volume": k, "count": v} for k, v in sim["first_cc_volume"].most_common()]
    write_table(out / "first_volume_stats.csv", fv_rows)

    if sim["first_tes_z"]:
        plt.figure(figsize=(7.2, 4.8))
        plt.hist(sim["first_tes_z"], bins=60, color="#4C78A8", alpha=0.85)
        plt.axvline(source_z, color="#E45756", lw=1.5, label="source z")
        plt.axvline(win_top, color="#54A24B", lw=1.5, label="Win_Be +z face")
        plt.xlabel("First TES CC HIT z")
        plt.ylabel("Events")
        plt.title("Science-source first TES hit z sanity")
        plt.legend()
        plt.tight_layout()
        plt.savefig(out / "first_tes_hit_z_hist.png", dpi=180)
        plt.close()

    result = {
        "gate": "A_source_placement",
        "passed": gate_pass,
        "source_file": str(args.science_source),
        "geometry": str(args.geometry),
        "detector": str(args.detector),
        "science_sim": str(args.science_sim),
        "source": source,
        "win_be": {
            "z_center": win_be["position"][2],
            "z_min": win_be["z_min"],
            "z_max": win_be["z_max"],
            "radius": win_radius,
        },
        "clearance_source_minus_win_top": clearance,
        "source_inside_tes_layers": inside_tes,
        "source_static_pass": source_static_pass,
        "sim_beam_match": sim_beam_match,
        "first_cc_in_tes_at_source": first_cc_in_tes_at_source,
        "median_first_cc_z": median_first_cc_z,
        "sim_events_scanned": sim["events_seen"],
        "sim_beam": sim["beam"],
        "first_cc_volume_top10": dict(sim["first_cc_volume"].most_common(10)),
        "first_tes_layer_counts": dict(sim["first_tes_layer"].most_common()),
        "has_win_be_energy_hit_events": sim["has_win_be_hit"],
        "decision": "PASS" if gate_pass else "FAIL",
    }
    (out / "be_window_crossing_summary.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    if gate_pass:
        conclusion = "PASS: the source starts just outside Win_Be, points toward -z, is not inside the TES stack, and the SIM beam header is consistent."
    else:
        conclusion = "FAIL: the source/SIM placement is inconsistent with a Be-window entrance source. Do not update 511 sensitivity until fixed and rerun."
    md = f"""# Gate A source-placement result

**Decision:** `{result['decision']}`

{conclusion}

## Key checks

- source z: `{source_z}`
- Win_Be +z face: `{win_top}`
- source minus Win_Be +z face: `{clearance}`
- source radius: `{source_radius}`
- Win_Be radius: `{win_radius}`
- source inside TES layers: `{inside_tes}`
- SIM events scanned: `{sim['events_seen']}`
- first CC hit in TES at source plane: `{first_cc_in_tes_at_source}`
- first CC volume top 10: `{dict(sim['first_cc_volume'].most_common(10))}`

## Outputs

- `source_geometry_table.csv`
- `first_volume_stats.csv`
- `first_tes_hit_z_hist.png`
- `be_window_crossing_summary.json`
"""
    (out / "gate_A_result.md").write_text(md, encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if gate_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
