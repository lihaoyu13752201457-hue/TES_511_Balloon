#!/usr/bin/env python3
"""Parse first-layer TES efficiency from the 100k 511 keV Cosima SIM data."""

from __future__ import annotations

import argparse
import gzip
import json
import math
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SIM_CANDIDATES = [
    ROOT / "runs" / "science_511_onaxis_source" / "Science_511_onaxis_ADR_cmfix.inc1.id1.sim.gz",
    ROOT / "runs" / "science_511_onaxis_source" / "Science_511_onaxis_ADR_cmfix_smoke1k.inc1.id1.sim.gz",
]
DEFAULT_LOG_CANDIDATES = [
    ROOT / "runs" / "science_511_onaxis_source" / "cosima_science_100k.log",
    ROOT / "outputs" / "reports" / "science_511_ADR_cm_100k_cosima.log",
    ROOT / "outputs" / "reports" / "science_511_ADR_cm_smoke1k_cosima.log",
]
DEFAULT_GEO_CANDIDATES = [
    ROOT / "outputs" / "geometry" / "XZTES_ADR_v4c_mkflange_cm" / "TibetTES_ADR_v4c_mkflange_cm.geo",
]

FIRST_LAYER = 5


def first_existing(candidates: list[Path]) -> Path:
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("None of the candidate paths exists: " + ", ".join(map(str, candidates)))


def binomial_sigma(p: float, n: int) -> float:
    return math.sqrt(max(p * (1.0 - p), 0.0) / n)


def parse_generated_particles(log_path: Path) -> int | None:
    pattern = re.compile(r"Total number of generated particles:\s+(\d+)")
    for line in log_path.read_text(errors="replace").splitlines():
        match = pattern.search(line)
        if match:
            return int(match.group(1))
    return None


def parse_l5_geometry(geo_path: Path) -> dict:
    text = geo_path.read_text(errors="replace")
    shape = re.search(r"TES_Pixel_L5\.Shape\s+BRIK\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", text)
    if not shape:
        raise ValueError(f"Cannot find TES_Pixel_L5.Shape in {geo_path}")
    hx, hy, hz = map(float, shape.groups())

    pixels: list[tuple[float, float]] = []
    for match in re.finditer(r"TP_L5_\d+\.Position\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", text):
        x, y, _ = map(float, match.groups())
        pixels.append((x, y))

    if not pixels:
        raise ValueError(f"Cannot find TP_L5 pixel positions in {geo_path}")

    centers: dict[int, float] = {}
    for match in re.finditer(r"TES_L(\d+)\.Position\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", text):
        layer = int(match.group(1))
        centers[layer] = float(match.group(4))

    if FIRST_LAYER not in centers:
        raise ValueError(f"Cannot find TES_L{FIRST_LAYER}.Position in {geo_path}")

    return {
        "half_size": [hx, hy, hz],
        "pixel_count": len(pixels),
        "pixels": pixels,
        "layer_centers": centers,
        "center_z": centers[FIRST_LAYER],
        "top_z": centers[FIRST_LAYER] + hz,
        "bottom_z": centers[FIRST_LAYER] - hz,
    }


def in_l5_pixel(x: float, y: float, pixels: list[tuple[float, float]], hx: float, hy: float) -> bool:
    return any(abs(x - px) <= hx and abs(y - py) <= hy for px, py in pixels)


def layer_from_htsim_z(z: float, centers: dict[int, float]) -> int | None:
    for layer, center in centers.items():
        if abs(z - center) < 1e-3:
            return layer
    return None


def nearest_tes_layer_for_ia_z(z: float, centers: dict[int, float], max_distance: float) -> int | None:
    layer = min(centers, key=lambda item: abs(z - centers[item]))
    if abs(z - centers[layer]) <= max_distance:
        return layer
    return None


def new_event() -> dict:
    return {
        "geom_l5_footprint": False,
        "l5_ht_energy": 0.0,
        "l5_cc": False,
        "first_ht_layer": None,
        "first_cc_volume": None,
        "first_noninit_ia_seen": False,
        "first_noninit_ia_layer": None,
        "first_l5_ia_z": None,
    }


def parse_sim(sim_path: Path, geom: dict) -> dict:
    hx, hy, hz = geom["half_size"]
    top_z = geom["top_z"]
    bottom_z = geom["bottom_z"]
    pixels = geom["pixels"]
    centers = geom["layer_centers"]
    max_layer_distance = max(hz + 0.01, 0.02)

    stats = Counter()
    first_cc_counter = Counter()
    first_ht_layer_counter = Counter()
    first_ia_layer_counter = Counter()
    first_l5_ia_depths: list[float] = []

    def finish(event: dict | None) -> None:
        if event is None:
            return
        stats["events"] += 1
        l5_hit = event["l5_ht_energy"] > 0
        l5_full_506_516 = 506.0 <= event["l5_ht_energy"] <= 516.0
        if l5_hit:
            stats["events_l5_ht_any"] += 1
        if l5_full_506_516:
            stats["events_l5_ht_506_516"] += 1
        if event["l5_cc"]:
            stats["events_l5_cc_any"] += 1
        if event["first_noninit_ia_layer"] == FIRST_LAYER:
            stats["events_first_ia_l5"] += 1
        if event["first_ht_layer"] == FIRST_LAYER:
            stats["events_first_ht_l5"] += 1
        if event["geom_l5_footprint"]:
            stats["events_geom_l5_footprint"] += 1
            if l5_hit:
                stats["geom_l5_footprint_l5_ht_any"] += 1
            if l5_full_506_516:
                stats["geom_l5_footprint_l5_ht_506_516"] += 1
            if event["l5_cc"]:
                stats["geom_l5_footprint_l5_cc_any"] += 1
            if event["first_noninit_ia_layer"] == FIRST_LAYER:
                stats["geom_l5_footprint_first_ia_l5"] += 1
            elif event["first_noninit_ia_seen"]:
                stats["geom_l5_footprint_prior_non_l5_ia"] += 1
        elif l5_hit:
            stats["not_geom_l5_footprint_but_l5_ht"] += 1

        if event["first_l5_ia_z"] is not None:
            depth = top_z - event["first_l5_ia_z"]
            first_l5_ia_depths.append(depth)

        first_cc_counter[event["first_cc_volume"]] += 1
        first_ht_layer_counter[event["first_ht_layer"]] += 1
        first_ia_layer_counter[event["first_noninit_ia_layer"]] += 1

    event = None
    with gzip.open(sim_path, "rt", errors="replace") as handle:
        for line in handle:
            if line.startswith("ID "):
                finish(event)
                event = new_event()
            elif event is not None and line.startswith("IA INIT"):
                fields = [field.strip() for field in line.split(None, 2)[2].split(";")]
                x = float(fields[4])
                y = float(fields[5])
                event["geom_l5_footprint"] = in_l5_pixel(x, y, pixels, hx, hy)
            elif event is not None and line.startswith("HTsim"):
                fields = [field.strip() for field in line.split(";")]
                if len(fields) >= 5:
                    z = float(fields[3])
                    energy = float(fields[4])
                    layer = layer_from_htsim_z(z, centers)
                    if event["first_ht_layer"] is None and layer is not None:
                        event["first_ht_layer"] = layer
                    if layer == FIRST_LAYER:
                        event["l5_ht_energy"] += energy
            elif event is not None and line.startswith("CC HIT "):
                volume = line.split()[2]
                if event["first_cc_volume"] is None:
                    event["first_cc_volume"] = volume
                if re.match(r"TP_L5_\d+", volume):
                    event["l5_cc"] = True
            elif event is not None and line.startswith("IA "):
                parts = line.split(None, 2)
                if len(parts) < 3 or parts[1] in {"INIT", "ESCP"}:
                    continue
                fields = [field.strip() for field in parts[2].split(";")]
                if len(fields) <= 6:
                    continue
                z = float(fields[6])
                layer = nearest_tes_layer_for_ia_z(z, centers, max_layer_distance)
                if event["first_noninit_ia_seen"] is False:
                    event["first_noninit_ia_seen"] = True
                    event["first_noninit_ia_layer"] = layer
                if event["first_l5_ia_z"] is None and bottom_z <= z <= top_z:
                    event["first_l5_ia_z"] = z
    finish(event)

    return {
        "stats": dict(stats),
        "first_cc_counter": {str(k): v for k, v in first_cc_counter.most_common(30)},
        "first_ht_layer_counter": {str(k): v for k, v in first_ht_layer_counter.items()},
        "first_ia_layer_counter": {str(k): v for k, v in first_ia_layer_counter.items()},
        "first_l5_ia_depths": first_l5_ia_depths,
    }


def summarize(sim_path: Path, log_path: Path, geo_path: Path) -> dict:
    geom = parse_l5_geometry(geo_path)
    parsed = parse_sim(sim_path, geom)
    stats = parsed["stats"]
    generated = parse_generated_particles(log_path) or stats["events"]
    footprint = stats["events_geom_l5_footprint"]
    depths = parsed["first_l5_ia_depths"]

    def rate(key: str, denominator: int) -> dict:
        count = stats[key]
        p = count / denominator if denominator else 0.0
        return {"count": count, "denominator": denominator, "rate": p, "sigma": binomial_sigma(p, denominator)}

    depth_summary = {
        "count": len(depths),
        "min": min(depths) if depths else None,
        "max": max(depths) if depths else None,
        "mean": sum(depths) / len(depths) if depths else None,
        "gt_0p3_count": sum(depth > 0.3 for depth in depths),
        "gt_0p3_rate": (sum(depth > 0.3 for depth in depths) / len(depths)) if depths else None,
    }

    return {
        "inputs": {
            "sim": str(sim_path),
            "log": str(log_path),
            "geo": str(geo_path),
        },
        "generated_particles": generated,
        "stored_sim_events": stats["events"],
        "first_layer_definition": {
            "beam_direction": "+z to -z",
            "first_tes_layer": "TES_L5 / TP_L5_*",
            "center_z": geom["center_z"],
            "top_z": geom["top_z"],
            "bottom_z": geom["bottom_z"],
            "pixel_half_size": geom["half_size"],
            "pixel_count": geom["pixel_count"],
        },
        "rates_all_generated": {
            "l5_active_tes_any_ht": rate("events_l5_ht_any", generated),
            "l5_active_tes_full_energy_506_516": rate("events_l5_ht_506_516", generated),
            "l5_active_tes_any_cc": rate("events_l5_cc_any", generated),
            "first_noninit_interaction_in_l5_slab": rate("events_first_ia_l5", generated),
        },
        "rates_conditioned_on_l5_pixel_footprint": {
            "footprint": rate("events_geom_l5_footprint", generated),
            "l5_active_tes_any_ht": rate("geom_l5_footprint_l5_ht_any", footprint),
            "l5_active_tes_full_energy_506_516": rate("geom_l5_footprint_l5_ht_506_516", footprint),
            "first_noninit_interaction_in_l5_slab": rate("geom_l5_footprint_first_ia_l5", footprint),
            "prior_non_l5_interaction": rate("geom_l5_footprint_prior_non_l5_ia", footprint),
        },
        "first_l5_interaction_depth_from_top": depth_summary,
        "first_cc_counter_top30": parsed["first_cc_counter"],
        "first_ht_layer_counter": parsed["first_ht_layer_counter"],
        "first_ia_layer_counter": parsed["first_ia_layer_counter"],
    }


def write_report(summary: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    all_rates = summary["rates_all_generated"]
    footprint_rates = summary["rates_conditioned_on_l5_pixel_footprint"]
    depth = summary["first_l5_interaction_depth_from_top"]

    def fmt(row: dict) -> str:
        return f"{row['count']}/{row['denominator']} = {row['rate']:.6f} +/- {row['sigma']:.6f}"

    lines = [
        "# First-layer TES 511 keV efficiency",
        "",
        f"- SIM: `{summary['inputs']['sim']}`",
        f"- Log: `{summary['inputs']['log']}`",
        f"- Geometry: `{summary['inputs']['geo']}`",
        f"- Generated particles: {summary['generated_particles']}",
        f"- Stored SIM events: {summary['stored_sim_events']}",
        "- First TES layer for this source direction: `TES_L5` / `TP_L5_*`.",
        "",
        "## All generated photons",
        "",
        f"- L5 active TES any HTsim hit: {fmt(all_rates['l5_active_tes_any_ht'])}",
        f"- L5 active TES full-energy 506-516 keV: {fmt(all_rates['l5_active_tes_full_energy_506_516'])}",
        f"- First non-init interaction in L5 slab: {fmt(all_rates['first_noninit_interaction_in_l5_slab'])}",
        "",
        "## Conditioned on L5 active-pixel footprint",
        "",
        f"- Initial ray intersects a TP_L5 pixel footprint: {fmt(footprint_rates['footprint'])}",
        f"- L5 active TES any HTsim hit within that footprint: {fmt(footprint_rates['l5_active_tes_any_ht'])}",
        f"- L5 active TES full-energy 506-516 keV within that footprint: {fmt(footprint_rates['l5_active_tes_full_energy_506_516'])}",
        f"- First non-init interaction in L5 slab within that footprint: {fmt(footprint_rates['first_noninit_interaction_in_l5_slab'])}",
        f"- Prior non-L5 interaction within that footprint: {fmt(footprint_rates['prior_non_l5_interaction'])}",
        "",
        "## First L5 interaction depth",
        "",
        f"- First L5 IA count: {depth['count']}",
        f"- Depth range from L5 top face: {depth['min']:.6f} to {depth['max']:.6f}",
        f"- Mean depth from L5 top face: {depth['mean']:.6f}",
        f"- First L5 IA deeper than 0.3 cm from top face: {depth['gt_0p3_count']}/{depth['count']} = {depth['gt_0p3_rate']:.6f}",
        "",
        "## Interpretation",
        "",
        "This report is generated directly from the selected SIM and current",
        "geometry file. For the cm-scaled geometry the L5 active thickness is",
        "0.3 cm, so no first L5 interaction depth can exceed the physical slab",
        "thickness except for parser/numerical error.",
    ]
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", type=Path, default=None)
    ap.add_argument("--log", type=Path, default=None)
    ap.add_argument("--geo", type=Path, default=None)
    ap.add_argument("--out-md", type=Path, default=ROOT / "tests" / "first_layer_511_efficiency_report.md")
    ap.add_argument("--out-json", type=Path, default=ROOT / "tests" / "first_layer_511_efficiency_summary.json")
    args = ap.parse_args()

    sim = args.sim or first_existing(DEFAULT_SIM_CANDIDATES)
    log = args.log or first_existing(DEFAULT_LOG_CANDIDATES)
    geo = args.geo or first_existing(DEFAULT_GEO_CANDIDATES)
    summary = summarize(sim, log, geo)
    write_report(summary, args.out_md, args.out_json)
    all_rates = summary["rates_all_generated"]
    footprint_rates = summary["rates_conditioned_on_l5_pixel_footprint"]
    print("All generated L5 any HT:", all_rates["l5_active_tes_any_ht"])
    print("All generated L5 full 506-516:", all_rates["l5_active_tes_full_energy_506_516"])
    print("Footprint-conditioned L5 any HT:", footprint_rates["l5_active_tes_any_ht"])
    print(f"Wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
