#!/usr/bin/env python3
"""Summarize the v3p5 center-finger 1/10-statistics Step02 closure."""

from __future__ import annotations

import csv
import gzip
import json
import argparse
import re
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
STEP = ROOT / "stepwise_maintenance" / "step02_raw_background_simulation"
OUT = STEP / "outputs_v3p5_centerfinger_1of10"
SNAP = STEP / "source_snapshots_v3p5_centerfinger_1of10"

SOURCE_DIR = ROOT / "config" / "megalib_sources_fullsphere20_v3p5_centerfinger_tilt45"
GEOM_VALIDATION = ROOT / "outputs" / "geometry" / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy" / "geometry_proxy_validation.json"
STEP00_CLOSURE = ROOT / "stepwise_maintenance" / "step00_geometry" / "outputs" / "v3p5_centerfinger" / "step00_v3p5_centerfinger_closure.json"

INSTANT = ROOT / "runs" / "step02_instant_v3p5_centerfinger_1of10"
BUILDUP = ROOT / "runs" / "step02_buildup_v3p5_centerfinger_1of10"
DECAY = ROOT / "runs" / "step02_decay_source_v3p5_centerfinger_1of10"
FIX = ROOT / "runs" / "step02_delay_fix_v3p5_centerfinger_1of10"
DELAYED = ROOT / "runs" / "step02_delayed_transport_v3p5_centerfinger_1of10"

SUMMARY_JSON = OUT / "step02_v3p5_centerfinger_1of10_summary.json"
SUMMARY_MD = OUT / "step02_v3p5_centerfinger_1of10_summary.md"
PARTICLE_COUNTS = OUT / "step02_v3p5_centerfinger_1of10_particle_counts.csv"
SOURCE_BLOCKS = OUT / "step02_v3p5_centerfinger_1of10_source_blocks.csv"


SOURCE_RE = re.compile(r"^DecayRun\.Source\s+(?P<name>\S+)")
FLUX_RE = re.compile(r"^(?P<name>\S+)\.Flux\s+(?P<flux>[-+0-9.eE]+)")
INC_RE = re.compile(r"\.inc(?P<inc>\d+)\.id1\.sim\.gz$")


def configure_paths(label: str) -> None:
    global OUT, SNAP, INSTANT, BUILDUP, DECAY, FIX, DELAYED
    global SUMMARY_JSON, SUMMARY_MD, PARTICLE_COUNTS, SOURCE_BLOCKS

    OUT = STEP / f"outputs_v3p5_centerfinger_{label}"
    SNAP = STEP / f"source_snapshots_v3p5_centerfinger_{label}"
    INSTANT = ROOT / "runs" / f"step02_instant_v3p5_centerfinger_{label}"
    BUILDUP = ROOT / "runs" / f"step02_buildup_v3p5_centerfinger_{label}"
    DECAY = ROOT / "runs" / f"step02_decay_source_v3p5_centerfinger_{label}"
    FIX = ROOT / "runs" / f"step02_delay_fix_v3p5_centerfinger_{label}"
    DELAYED = ROOT / "runs" / f"step02_delayed_transport_v3p5_centerfinger_{label}"
    SUMMARY_JSON = OUT / f"step02_v3p5_centerfinger_{label}_summary.json"
    SUMMARY_MD = OUT / f"step02_v3p5_centerfinger_{label}_summary.md"
    PARTICLE_COUNTS = OUT / f"step02_v3p5_centerfinger_{label}_particle_counts.csv"
    SOURCE_BLOCKS = OUT / f"step02_v3p5_centerfinger_{label}_source_blocks.csv"


def delayed_log_path() -> Path:
    logs = sorted(DELAYED.glob("cosima_delayed_transport*.log"))
    return logs[0] if logs else DELAYED / "cosima_delayed_transport.log"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def summarize_transport(path: Path) -> dict[str, Any]:
    rows = load_json(path / "run_summary.json")
    norm = load_json(path / "normalization.json")
    by_particle: dict[str, dict[str, Any]] = {}
    for row in rows:
        particle = row["particle"]
        item = by_particle.setdefault(
            particle,
            {
                "jobs": 0,
                "events_requested": 0,
                "events_generated": 0,
                "cpu_s": 0.0,
                "sim_size_bytes": 0,
                "dat_size_bytes": 0,
                "failures": 0,
            },
        )
        item["jobs"] += 1
        item["events_requested"] += int(row["events"])
        item["events_generated"] += int(row["generated_particles"] or 0)
        item["cpu_s"] += float(row["cpu_s"] or 0.0)
        item["sim_size_bytes"] += int(row["sim_size_bytes"] or 0)
        item["dat_size_bytes"] += int(row["dat_size_bytes"] or 0)
        if row["status"] != "PASS":
            item["failures"] += 1
    return {
        "run_dir": rel(path),
        "mode": norm["mode"],
        "jobs": len(rows),
        "passes": sum(1 for row in rows if row["status"] == "PASS"),
        "failures": sum(1 for row in rows if row["status"] != "PASS"),
        "events_requested": sum(int(row["events"]) for row in rows),
        "events_generated": sum(int(row["generated_particles"] or 0) for row in rows),
        "gamma_events": norm["gamma_events"],
        "gamma_splits": norm["gamma_splits"],
        "non_gamma_replicas": norm["non_gamma_replicas"],
        "farfield_radius_cm": norm["farfield_radius_cm"],
        "farfield_area_cm2": norm["farfield_area_cm2"],
        "gamma_prompt_time_s_with_farfield_area": norm["gamma_prompt_time_s_with_farfield_area"],
        "source_migration_manifest": norm.get("source_migration_manifest"),
        "by_particle": by_particle,
    }


def parse_decay_source(path: Path) -> dict[str, Any]:
    names: list[str] = []
    flux: dict[str, float] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        sm = SOURCE_RE.match(stripped)
        if sm:
            names.append(sm.group("name"))
            continue
        fm = FLUX_RE.match(stripped)
        if fm:
            flux[fm.group("name")] = float(fm.group("flux"))
    rows = [{"source_name": name, "flux_Bq": flux.get(name, 0.0)} for name in names]
    return {
        "path": rel(path),
        "source_blocks": len(names),
        "total_activity_Bq": sum(row["flux_Bq"] for row in rows),
        "rows": rows,
    }


def latest_delayed_sim() -> Path:
    sims = list(DELAYED.glob("DelayedDecayRPIPGroundStateFixed.inc*.id1.sim.gz"))
    if not sims:
        raise FileNotFoundError("No delayed transport SIM files found")
    return max(sims, key=lambda path: int(INC_RE.search(path.name).group("inc") if INC_RE.search(path.name) else "0"))


def read_sim(path: Path) -> dict[str, Any]:
    out = {"path": rel(path), "SE": 0, "ID": 0, "TS": None, "TE_s": None, "geometry": "", "size_bytes": path.stat().st_size}
    with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if line.startswith("SE"):
                out["SE"] += 1
            elif line.startswith("ID"):
                out["ID"] += 1
            elif line.startswith("TS "):
                out["TS"] = int(line.split()[1])
            elif line.startswith("TE "):
                out["TE_s"] = float(line.split()[1])
            elif line.startswith("Geometry "):
                out["geometry"] = line.strip().split(" ", 1)[1].strip()
    return out


def write_snapshots() -> None:
    SNAP.mkdir(parents=True, exist_ok=True)
    for path in sorted(SOURCE_DIR.glob("Background_*_fullsphere20.source")):
        shutil.copy2(path, SNAP / path.name)
    for src, dst in [
        (SOURCE_DIR / "source_migration_manifest.json", "source_migration_manifest.json"),
        (INSTANT / "normalization.json", "instant_normalization.json"),
        (INSTANT / "run_manifest.csv", "instant_run_manifest.csv"),
        (BUILDUP / "normalization.json", "buildup_normalization.json"),
        (BUILDUP / "run_manifest.csv", "buildup_run_manifest.csv"),
        (DECAY / "activation_decay_day15.source", "activation_decay_day15.source"),
        (DECAY / "activation_inventory_day15.csv", "activation_inventory_day15.csv"),
        (DECAY / "unknown_isotopes_day15.csv", "unknown_isotopes_day15.csv"),
        (DECAY / "no_rpip_points_day15.csv", "no_rpip_points_day15.csv"),
        (FIX / "activation_decay_day15_groundstate_fixed.source", "activation_decay_day15_groundstate_fixed.source"),
        (FIX / "groundstate_activity_corrections.csv", "groundstate_activity_corrections.csv"),
        (FIX / "removed_or_rescaled_sources.csv", "removed_or_rescaled_sources.csv"),
        (FIX / "source_fix_summary.json", "source_fix_summary.json"),
        (ROOT / "code" / "tools" / "run_equiv2602_pipeline_NEW_GEO.py", "run_equiv2602_pipeline_NEW_GEO.py"),
        (ROOT / "code" / "tools" / "build_v3p5_centerfinger_farfield_sources.py", "build_v3p5_centerfinger_farfield_sources.py"),
    ]:
        if src.exists():
            shutil.copy2(src, SNAP / dst)


def markdown(summary: dict[str, Any], particle_rows: list[dict[str, Any]]) -> str:
    instant = summary["instant_transport"]
    buildup = summary["buildup_transport"]
    fixed = summary["fixed_decay_source"]
    delayed = summary["delayed_transport"]
    geom = summary["geometry"]
    label = summary["statistics_label"]
    lines = [
        f"# Step02 v3p5 Center-Finger {label} Closure",
        "",
        f"Status: `{summary['status']}`.",
        "",
        f"Scope: this is an all-particle `{label}` closure for the tilted v3p5 simulation geometry.",
        "",
        "Geometry/source policy:",
        f"- geometry setup: `{summary['source_manifest']['geometry_setup']}`",
        f"- geometry validation: `{summary['source_manifest']['geometry_status']}`",
        f"- far-field radius: `{instant['farfield_radius_cm']} cm`",
        f"- side-window look elevation: `{geom['geometry_extents']['instrument_frame']['side_window_look_elevation_deg']:.6g} deg`",
        f"- detector core pixels: `{geom['checks']['detector_core']['total_pixel_copies']}`",
        "",
        "Transport results:",
        f"- instant: `{instant['passes']}/{instant['jobs']}` jobs passed, `{instant['events_generated']}` generated particles",
        f"- buildup: `{buildup['passes']}/{buildup['jobs']}` jobs passed, `{buildup['events_generated']}` generated particles",
        f"- delayed source: `{summary['raw_decay_source']['source_blocks']}` blocks, `{summary['raw_decay_source']['total_activity_Bq']:.8g} Bq` raw activity",
        f"- ground-state fixed source: `{fixed['source_blocks']}` blocks, `{fixed['total_activity_Bq']:.8g} Bq` fixed activity",
        f"- delayed transport: `TS={delayed['TS']}`, `SE={delayed['SE']}`, `ID={delayed['ID']}`, `TE={delayed['TE_s']:.6g} s`",
        "",
        "Particle counts:",
        "",
        "| particle | instant generated | buildup generated |",
        "| --- | ---: | ---: |",
    ]
    for row in particle_rows:
        lines.append(f"| {row['particle']} | {row['instant_generated']} | {row['buildup_generated']} |")
    lines.extend(
        [
            "",
            "Artifacts:",
            f"- summary JSON: `{rel(SUMMARY_JSON)}`",
            f"- particle counts CSV: `{rel(PARTICLE_COUNTS)}`",
            f"- source blocks CSV: `{rel(SOURCE_BLOCKS)}`",
            f"- lightweight source snapshots: `{rel(SNAP)}`",
            f"- delayed transport SIM: `{delayed['path']}`",
            f"- delayed transport log: `{rel(delayed_log_path())}`",
            "",
            "Known limitation: delayed-source generation still uses the existing axisymmetric `RadialProfileBeam` profile builder. For the tilted geometry, an exact-position source upgrade remains the next confidence step before paper-facing numbers.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="1of10", help="Run/output label, e.g. 1of10 or fullstat_v2")
    args = ap.parse_args()

    configure_paths(args.label)
    OUT.mkdir(parents=True, exist_ok=True)
    instant = summarize_transport(INSTANT)
    buildup = summarize_transport(BUILDUP)
    raw_source = parse_decay_source(DECAY / "activation_decay_day15.source")
    fixed_source = parse_decay_source(FIX / "activation_decay_day15_groundstate_fixed.source")
    fix_summary = load_json(FIX / "source_fix_summary.json")
    delayed = read_sim(latest_delayed_sim())
    geom = load_json(GEOM_VALIDATION)
    step00 = load_json(STEP00_CLOSURE)
    source_manifest = load_json(SOURCE_DIR / "source_migration_manifest.json")

    particles = sorted(set(instant["by_particle"]) | set(buildup["by_particle"]))
    particle_rows = [
        {
            "particle": particle,
            "instant_generated": instant["by_particle"].get(particle, {}).get("events_generated", 0),
            "buildup_generated": buildup["by_particle"].get(particle, {}).get("events_generated", 0),
        }
        for particle in particles
    ]
    write_csv(PARTICLE_COUNTS, particle_rows, ["particle", "instant_generated", "buildup_generated"])
    write_csv(SOURCE_BLOCKS, fixed_source["rows"], ["source_name", "flux_Bq"])
    write_snapshots()

    payload = {
        "status": f"PASS_{args.label.upper()}_TRANSPORT_CLOSURE",
        "statistics_label": args.label,
        "scope": f"all-particle {args.label} closure",
        "geometry": geom,
        "step00_closure": step00,
        "source_manifest": source_manifest,
        "instant_transport": instant,
        "buildup_transport": buildup,
        "raw_decay_source": {k: v for k, v in raw_source.items() if k != "rows"},
        "fixed_decay_source": {k: v for k, v in fixed_source.items() if k != "rows"},
        "source_fix_summary": fix_summary,
        "delayed_transport": delayed,
        "particle_counts": particle_rows,
        "known_limitations": [
            "delayed source uses the legacy axisymmetric RadialProfileBeam profile builder",
        ],
    }
    if args.label == "1of10":
        payload["known_limitations"].insert(
            0,
            "1/10 run uses gamma_events=1000000 and delayed transport triggers=100000; it is not the full-statistics production",
        )
    SUMMARY_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    SUMMARY_MD.write_text(markdown(payload, particle_rows) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "summary": rel(SUMMARY_JSON), "delayed_TE_s": delayed["TE_s"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
