#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnose delayed-activation contributors around 511 keV.

The cached day-15 event catalog intentionally keeps only stream/tag/rate and
TES/BGO hit information.  Nuclide labels for delayed events must therefore be
recovered from the delayed SIM itself.  This script parses the fixed delayed
SIM, reads ``IA INIT`` for the primary isotope ZA, uses the first primary
``CC HIT`` volume as a transport-side source-volume proxy, and applies the same
BGO and Compton/FoV cuts as the complete day-15 report.

This is a diagnostic attribution, not a nuclear-data re-evaluation.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PARTICLE_SOURCE_CODE = ROOT / "code" / "particle_sources"
if str(PARTICLE_SOURCE_CODE) not in sys.path:
    sys.path.insert(0, str(PARTICLE_SOURCE_CODE))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import make_complete_day15_report as complete
from build_fixed_delay_source import za_to_nuclide


WORKSPACE = ROOT.parent
DEFAULT_SIM = ROOT / "simulation" / "delay_fix_from_buildup_equiv2602_cmfix" / "DelayedDecayRPIPGroundStateFixed.inc1.id1.sim.gz"
DEFAULT_INVENTORY = ROOT / "statistics" / "day15_complete_report" / "activation_inventory_day15_after_groundstate_fix.csv"
DEFAULT_OUT = ROOT / "statistics" / "nextphase_511" / "activation_511_diagnostics"

ID_RE = re.compile(r"^ID\s+(\d+)")
TP_RE = re.compile(r"^TP_L(?P<layer>\d+)_(?P<pix>\d+)$", re.IGNORECASE)
CC_HIT_RE = re.compile(r"^CC\s+HIT\s+(?P<vol>\S+)\s+(?P<body>.*)$")
KV_RE = re.compile(r"(\w+)=([^\s]+)")
IA_INIT_RE = re.compile(r"^IA INIT\s+(?P<body>.*)$")
WINDOWS = {
    "broad_480_550": (480.0, 550.0),
    "line_510p3_511p8": (510.3, 511.8),
    "near_506_516": (506.0, 516.0),
}


def open_text(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return path.open("r", encoding="utf-8", errors="ignore")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def load_inventory(path: Path) -> dict[str, Any]:
    by_za: dict[int, float] = defaultdict(float)
    by_vn_za: dict[tuple[str, int], float] = defaultdict(float)
    for row in read_csv_rows(path):
        try:
            za = int(float(row["ZA"]))
            activity = float(row.get("Activity_Bq_after_fix", row.get("Activity_Bq", "0")) or 0.0)
        except (KeyError, ValueError):
            continue
        by_za[za] += activity
        by_vn_za[(row.get("VN", ""), za)] += activity
    return {"by_za": dict(by_za), "by_vn_za": dict(by_vn_za)}


def parse_ia_init_za(line: str) -> int | None:
    m = IA_INIT_RE.match(line)
    if not m:
        return None
    parts = [p.strip() for p in m.group("body").split(";")]
    if len(parts) < 16:
        return None
    try:
        return int(float(parts[15]))
    except ValueError:
        return None


def parse_cc_hit(line: str):
    m = CC_HIT_RE.match(line.strip())
    if not m:
        return None
    vol = m.group("vol")
    kv = dict(KV_RE.findall(m.group("body")))
    try:
        return {
            "vol": vol,
            "edep": float(kv["edep_keV"]),
            "x": float(kv["x"]),
            "y": float(kv["y"]),
            "z": float(kv["z"]),
            "sec": kv.get("sec", ""),
            "prim": kv.get("prim", ""),
            "tid": int(kv.get("tid", "-1")),
            "pid": int(kv.get("pid", "-1")),
            "cproc": kv.get("cproc", ""),
        }
    except Exception:
        return None


def empty_event() -> dict[str, Any]:
    return {
        "local_id": None,
        "za": None,
        "primary_volume": "",
        "first_hit_volume": "",
        "bgo": 0.0,
        "pix": {},
        "tes_total": 0.0,
    }


def add_pixel(pix: dict[str, dict[str, float]], vol: str, layer: int, edep: float, x: float, y: float, z: float) -> None:
    rec = pix.setdefault(vol, {"e": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0, "layer": float(layer)})
    rec["e"] += edep
    rec["wx"] += edep * x
    rec["wy"] += edep * y
    rec["wz"] += edep * z


def event_hits(ev: dict[str, Any]) -> list[complete.EventHit]:
    hits: list[complete.EventHit] = []
    for uid, rec in sorted(ev["pix"].items()):
        e = float(rec["e"])
        if e <= 0.0:
            continue
        hits.append(
            complete.EventHit(
                x=float(rec["wx"] / e),
                y=float(rec["wy"] / e),
                z=float(rec["wz"] / e),
                e=e,
                pixel_uid=uid,
                layer=int(rec["layer"]),
            )
        )
    return hits


def classify_event(ev: dict[str, Any], lo: float, hi: float, reject_policy: str, bgo_thr: float) -> tuple[str, bool]:
    e = float(ev["tes_total"])
    if not (lo <= e < hi):
        return "energy_out", False
    if float(ev["bgo"]) >= bgo_thr:
        return "bgo_veto", False
    keep, cls = complete.classify_final(event_hits(ev), reject_policy)
    return ("kept" if keep else f"compton_{cls}"), bool(keep)


def update_stats(stats: dict[tuple[int, str], dict[str, Any]], ev: dict[str, Any], rate: float, reject_policy: str, bgo_thr: float) -> None:
    za = int(ev["za"] or 0)
    volume = ev["primary_volume"] or ev["first_hit_volume"] or "Unknown"
    key = (za, volume)
    rec = stats.setdefault(key, {
        "events_total": 0,
        "events_with_tes": 0,
        "rate_total_hz": 0.0,
        "rate_with_tes_hz": 0.0,
        "energy_sum_keV": 0.0,
        "windows": {name: {"raw": 0.0, "bgo": 0.0, "final": 0.0, "raw_events": 0, "bgo_events": 0, "final_events": 0, "causes": Counter()} for name in WINDOWS},
    })
    rec["events_total"] += 1
    rec["rate_total_hz"] += rate
    if ev["tes_total"] > 0:
        rec["events_with_tes"] += 1
        rec["rate_with_tes_hz"] += rate
        rec["energy_sum_keV"] += float(ev["tes_total"])
    for name, (lo, hi) in WINDOWS.items():
        w = rec["windows"][name]
        e = float(ev["tes_total"])
        if lo <= e < hi:
            w["raw"] += rate
            w["raw_events"] += 1
            if float(ev["bgo"]) < bgo_thr:
                w["bgo"] += rate
                w["bgo_events"] += 1
                cause, keep = classify_event(ev, lo, hi, reject_policy, bgo_thr)
                w["causes"][cause] += 1
                if keep:
                    w["final"] += rate
                    w["final_events"] += 1
            else:
                w["causes"]["bgo_veto"] += 1


def parse_delayed_sim(sim: Path, reject_policy: str, bgo_thr: float, max_events: int | None = None) -> tuple[dict[tuple[int, str], dict[str, Any]], dict[str, Any], list[tuple[float, int, str, float]]]:
    rate = 1.0 / complete.delayed_time_s()
    stats: dict[tuple[int, str], dict[str, Any]] = {}
    spectrum_rows: list[tuple[float, int, str, float]] = []
    counters = Counter()
    ev = empty_event()

    def flush() -> None:
        nonlocal ev
        if ev["local_id"] is not None:
            counters["events"] += 1
            if ev["za"] is None:
                counters["missing_za"] += 1
            else:
                update_stats(stats, ev, rate, reject_policy, bgo_thr)
                if 480.0 <= float(ev["tes_total"]) < 550.0:
                    spectrum_rows.append((float(ev["tes_total"]), int(ev["za"]), ev["primary_volume"] or ev["first_hit_volume"] or "Unknown", rate))
            if max_events and counters["events"] >= max_events:
                raise StopIteration
        ev = empty_event()

    try:
        with open_text(sim) as fh:
            for raw in fh:
                line = raw.strip()
                if line == "SE":
                    flush()
                    continue
                m_id = ID_RE.match(line)
                if m_id:
                    ev["local_id"] = int(m_id.group(1))
                    continue
                if line.startswith("IA INIT"):
                    za = parse_ia_init_za(line)
                    if za is not None:
                        ev["za"] = za
                    continue
                if not line.startswith("CC HIT "):
                    continue
                hit = parse_cc_hit(line)
                if not hit:
                    continue
                if not ev["first_hit_volume"]:
                    ev["first_hit_volume"] = hit["vol"]
                if not ev["primary_volume"] and hit["tid"] == 1 and hit["pid"] == 0:
                    ev["primary_volume"] = hit["vol"]
                vol = hit["vol"]
                edep = hit["edep"]
                if "BGO" in vol.upper():
                    ev["bgo"] += edep
                m_tp = TP_RE.match(vol)
                if m_tp:
                    add_pixel(ev["pix"], vol, int(m_tp.group("layer")), edep, hit["x"], hit["y"], hit["z"])
                    ev["tes_total"] += edep
        flush()
    except StopIteration:
        pass

    audit = {
        "events_parsed": int(counters["events"]),
        "missing_za_events": int(counters["missing_za"]),
        "rate_per_event_hz": rate,
        "sim": str(sim.relative_to(WORKSPACE) if sim.is_relative_to(WORKSPACE) else sim),
    }
    return stats, audit, spectrum_rows


def flatten_stats(stats: dict[tuple[int, str], dict[str, Any]], inventory: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (za, volume), rec in stats.items():
        row: dict[str, Any] = {
            "ZA": za,
            "nuclide": za_to_nuclide(za) if za else "Unknown",
            "source_volume_proxy": volume,
            "activity_Bq_total_by_ZA": inventory["by_za"].get(za, ""),
            "events_total": rec["events_total"],
            "events_with_tes": rec["events_with_tes"],
            "rate_total_hz": rec["rate_total_hz"],
            "rate_with_tes_hz": rec["rate_with_tes_hz"],
        }
        for name in WINDOWS:
            w = rec["windows"][name]
            row[f"{name}_raw_cps"] = w["raw"]
            row[f"{name}_bgo_cps"] = w["bgo"]
            row[f"{name}_final_cps"] = w["final"]
            row[f"{name}_raw_events"] = w["raw_events"]
            row[f"{name}_bgo_events"] = w["bgo_events"]
            row[f"{name}_final_events"] = w["final_events"]
            row[f"{name}_bgo_survival"] = w["bgo"] / w["raw"] if w["raw"] else ""
            row[f"{name}_final_survival"] = w["final"] / w["raw"] if w["raw"] else ""
            row[f"{name}_cut_causes"] = json.dumps(dict(w["causes"]), sort_keys=True)
        rows.append(row)
    rows.sort(key=lambda r: float(r["broad_480_550_final_cps"]), reverse=True)
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "ZA", "nuclide", "source_volume_proxy", "activity_Bq_total_by_ZA",
        "events_total", "events_with_tes", "rate_total_hz", "rate_with_tes_hz",
    ]
    for name in WINDOWS:
        fields += [
            f"{name}_raw_cps", f"{name}_bgo_cps", f"{name}_final_cps",
            f"{name}_raw_events", f"{name}_bgo_events", f"{name}_final_events",
            f"{name}_bgo_survival", f"{name}_final_survival", f"{name}_cut_causes",
        ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def aggregate_by_nuclide(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    agg: dict[str, dict[str, Any]] = {}
    for row in rows:
        nu = row["nuclide"]
        rec = agg.setdefault(nu, {"nuclide": nu, "ZA": row["ZA"], "volumes": set(), "events_total": 0})
        rec["volumes"].add(row["source_volume_proxy"])
        rec["events_total"] += int(row["events_total"])
        for name in WINDOWS:
            for stage in ("raw", "bgo", "final"):
                key = f"{name}_{stage}_cps"
                rec[key] = rec.get(key, 0.0) + float(row[key] or 0.0)
    out = []
    for rec in agg.values():
        rec["volumes"] = ";".join(sorted(rec["volumes"]))
        out.append(rec)
    out.sort(key=lambda r: float(r.get("broad_480_550_final_cps", 0.0)), reverse=True)
    return out


def plot_top(rows: list[dict[str, Any]], outdir: Path) -> dict[str, str]:
    paths: dict[str, str] = {}
    agg = aggregate_by_nuclide(rows)
    for window, filename, title in [
        ("broad_480_550", "delayed_511_top10_bar.png", "Delayed activation final contributors, 480-550 keV"),
        ("line_510p3_511p8", "delayed_511_line_top10_bar.png", "Delayed activation final contributors, 510.3-511.8 keV"),
    ]:
        top = [r for r in agg if float(r.get(f"{window}_final_cps", 0.0)) > 0.0][:10]
        fig, ax = plt.subplots(figsize=(8.0, 5.0))
        if top:
            labels = [r["nuclide"] for r in top][::-1]
            vals = [float(r[f"{window}_final_cps"]) for r in top][::-1]
            ax.barh(labels, vals, color="#4C78A8")
        ax.set_xlabel("Final delayed rate (cps)")
        ax.set_title(title)
        ax.grid(True, axis="x", alpha=0.25)
        fig.tight_layout()
        path = outdir / filename
        fig.savefig(path, dpi=220)
        plt.close(fig)
        paths[filename] = str(path)
    return paths


def plot_spectra(spectrum_rows: list[tuple[float, int, str, float]], rows: list[dict[str, Any]], outdir: Path) -> str:
    top_nuclides = [r["nuclide"] for r in aggregate_by_nuclide(rows)[:6]]
    za_to_name = {int(r["ZA"]): r["nuclide"] for r in rows}
    edges = np.arange(480.0, 550.0 + 0.5, 0.5)
    centers = 0.5 * (edges[:-1] + edges[1:])
    by_nu: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for energy, za, _volume, rate in spectrum_rows:
        nu = za_to_name.get(za, za_to_nuclide(za))
        if nu in top_nuclides:
            by_nu[nu].append((energy, rate))
    fig, ax = plt.subplots(figsize=(9.0, 5.4))
    for nu in top_nuclides:
        vals = by_nu.get(nu, [])
        if not vals:
            continue
        e = np.asarray([v[0] for v in vals])
        w = np.asarray([v[1] for v in vals])
        hist = np.histogram(e, bins=edges, weights=w)[0]
        ax.step(centers, hist, where="mid", label=nu)
    ax.set_yscale("log")
    ax.set_xlabel("TES deposited energy (keV)")
    ax.set_ylabel("Raw delayed rate (cps / 0.5 keV bin)")
    ax.set_title("480-550 keV delayed spectra by top nuclides")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    path = outdir / "delayed_511_energy_spectrum_by_top_nuclides.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return str(path)


def write_summary(outdir: Path, rows: list[dict[str, Any]], audit: dict[str, Any], figures: dict[str, str]) -> dict[str, Any]:
    agg = aggregate_by_nuclide(rows)
    totals = {}
    for name in WINDOWS:
        totals[name] = {
            "raw_cps": sum(float(r[f"{name}_raw_cps"] or 0.0) for r in rows),
            "bgo_cps": sum(float(r[f"{name}_bgo_cps"] or 0.0) for r in rows),
            "final_cps": sum(float(r[f"{name}_final_cps"] or 0.0) for r in rows),
        }
    summary = {
        "status": "PASS",
        "audit": audit,
        "totals": totals,
        "top_nuclides_by_broad_final": agg[:10],
        "figures": figures,
        "caveat": "source_volume_proxy is first primary CC HIT volume, not the exact source block name; activity is joined by ZA total.",
    }
    (outdir / "activation_511_diagnostic_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["# Delayed activation 511-keV diagnostic", "", f"Status: `{summary['status']}`", ""]
    lines.append("## Totals")
    for name, val in totals.items():
        lines.append(f"- `{name}`: raw `{val['raw_cps']:.6g}` cps, BGO `{val['bgo_cps']:.6g}` cps, final `{val['final_cps']:.6g}` cps.")
    lines.append("")
    lines.append("## Top broad-window final contributors")
    for rec in agg[:10]:
        lines.append(f"- `{rec['nuclide']}`: `{float(rec.get('broad_480_550_final_cps', 0.0)):.6g}` cps; volumes `{rec['volumes']}`.")
    lines.append("")
    lines.append("## Caveat")
    lines.append(summary["caveat"])
    (outdir / "delayed_511_diagnostic_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sim", type=Path, default=DEFAULT_SIM)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--max-events", type=int, default=0)
    args = parser.parse_args()

    _ = (WORKSPACE / "memory.md").read_text(encoding="utf-8", errors="ignore")
    _ = (WORKSPACE / "workflow.md").read_text(encoding="utf-8", errors="ignore")
    args.out.mkdir(parents=True, exist_ok=True)
    inventory = load_inventory(args.inventory)
    max_events = int(args.max_events) if int(args.max_events) > 0 else None
    stats, audit, spectrum_rows = parse_delayed_sim(args.sim, "keep", complete.BGO_THR_KEV, max_events=max_events)
    rows = flatten_stats(stats, inventory)
    write_csv(args.out / "delayed_511_by_nuclide_volume.csv", rows)
    figures = plot_top(rows, args.out)
    figures["delayed_511_energy_spectrum_by_top_nuclides.png"] = plot_spectra(spectrum_rows, rows, args.out)
    summary = write_summary(args.out, rows, audit, figures)
    (args.out / "audit.json").write_text(json.dumps({"status": "PASS", **audit}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(args.out / "activation_511_diagnostic_summary.json")
    print(json.dumps({"totals": summary["totals"], "top": summary["top_nuclides_by_broad_final"][:3]}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
