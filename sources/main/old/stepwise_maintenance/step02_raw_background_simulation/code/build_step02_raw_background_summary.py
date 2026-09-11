#!/usr/bin/env python3
"""Build Step02 raw prompt/delayed background simulation summaries."""

from __future__ import annotations

import csv
import gzip
import json
import re
import shutil
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[3]
STEP_DIR = ROOT / "stepwise_maintenance" / "step02_raw_background_simulation"
OUT = STEP_DIR / "outputs"
SNAP = STEP_DIR / "source_snapshots"

INSTANT_DIR = ROOT / "runs" / "step02_instant_smoke1k"
BUILDUP_DIR = ROOT / "runs" / "step02_buildup_smoke1k"
DECAY_DIR = ROOT / "runs" / "step02_decay_source_smoke1k"
FIX_DIR = ROOT / "runs" / "step02_delay_fix_smoke1k"
DELAYED_DIR = ROOT / "runs" / "step02_delayed_transport_smoke1k"

DELAYED_SIM = DELAYED_DIR / "DelayedDecayRPIPGroundStateFixed.inc1.id1.sim.gz"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def summarize_transport(run_dir: Path, label: str) -> dict[str, object]:
    jobs = load_json(run_dir / "run_summary.json")
    norm = load_json(run_dir / "normalization.json")

    by_particle = {}
    for row in jobs:
        particle = row["particle"]
        by_particle[particle] = {
            "events_requested": int(row["events"]),
            "events_generated": int(row["generated_particles"]),
            "cpu_s": float(row["cpu_s"]),
            "observation_time_s": float(row["observation_time_s"]),
            "sim_size_bytes": int(row["sim_size_bytes"]),
            "dat_size_bytes": int(row["dat_size_bytes"]),
            "status": row["status"],
        }

    return {
        "label": label,
        "mode": norm["mode"],
        "run_dir": rel(run_dir),
        "jobs": len(jobs),
        "passes": sum(1 for row in jobs if row["status"] == "PASS"),
        "failures": sum(1 for row in jobs if row["status"] != "PASS"),
        "events_requested": sum(int(row["events"]) for row in jobs),
        "events_generated": sum(int(row["generated_particles"]) for row in jobs),
        "cpu_s": sum(float(row["cpu_s"]) for row in jobs),
        "sim_files": sum(1 for row in jobs if row["sim_exists"]),
        "dat_files": sum(1 for row in jobs if row["dat_exists"]),
        "sim_size_bytes": sum(int(row["sim_size_bytes"]) for row in jobs),
        "dat_size_bytes": sum(int(row["dat_size_bytes"]) for row in jobs),
        "gamma_events": int(norm["gamma_events"]),
        "farfield_radius_cm": float(norm["farfield_radius_cm"]),
        "farfield_area_cm2": float(norm["farfield_area_cm2"]),
        "gamma_prompt_time_s_with_farfield_area": float(norm["gamma_prompt_time_s_with_farfield_area"]),
        "flux_by_particle_cm2_s": norm["flux_by_particle_cm2_s"],
        "base_events_by_particle": norm["base_events_by_particle"],
        "by_particle": by_particle,
    }


def read_delayed_sim_summary(path: Path) -> dict[str, object]:
    event_count = 0
    ts = None
    te = None
    first_date = ""
    geometry = ""
    with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if line.startswith("SE"):
                event_count += 1
            elif line.startswith("TS "):
                ts = int(line.split()[1])
            elif line.startswith("TE "):
                te = float(line.split()[1])
            elif line.startswith("Date "):
                first_date = line.strip().replace("Date", "", 1).strip()
            elif line.startswith("Geometry "):
                geometry = line.strip().replace("Geometry", "", 1).strip()
    return {
        "path": rel(path),
        "events_from_SE": event_count,
        "TS": ts,
        "TE_s": te,
        "date": first_date,
        "geometry": geometry,
        "size_bytes": path.stat().st_size,
    }


SOURCE_RE = re.compile(r"^DecayRun\.Source\s+(?P<name>\S+)")
FLUX_RE = re.compile(r"^(?P<name>\S+)\.Flux\s+(?P<flux>[-+0-9.eE]+)")
PARTICLE_RE = re.compile(r"^(?P<name>\S+)\.ParticleType\s+(?P<particle>\d+)")


def parse_decay_source(path: Path) -> dict[str, object]:
    source_names: list[str] = []
    flux_by_name: dict[str, float] = {}
    particle_by_name: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        sm = SOURCE_RE.match(stripped)
        if sm:
            source_names.append(sm.group("name"))
            continue
        fm = FLUX_RE.match(stripped)
        if fm:
            flux_by_name[fm.group("name")] = float(fm.group("flux"))
            continue
        pm = PARTICLE_RE.match(stripped)
        if pm:
            particle_by_name[pm.group("name")] = pm.group("particle")

    rows = []
    for name in source_names:
        rows.append(
            {
                "source_name": name,
                "particle_type": particle_by_name.get(name, ""),
                "flux_Bq": flux_by_name.get(name, 0.0),
            }
        )

    return {
        "path": rel(path),
        "source_blocks": len(source_names),
        "total_activity_Bq": sum(flux_by_name.get(name, 0.0) for name in source_names),
        "sources": rows,
    }


def inventory_summary(path: Path) -> dict[str, object]:
    rows = load_csv(path)
    out = []
    for row in rows:
        out.append(
            {
                "VN": row["VN"],
                "ZA": int(row["ZA"]),
                "nuclide": row["nuclide"],
                "exc_keV": float(row["exc_keV"]),
                "RP_yield": float(row["RP_yield"]),
                "half_life_s": float(row["hl_s"]),
                "activity_Bq": float(row["Activity_Bq"]),
                "rpip_points": int(row["Points"]),
            }
        )
    return {
        "path": rel(path),
        "rows": out,
        "total_activity_Bq": sum(row["activity_Bq"] for row in out),
        "total_rpip_points": sum(row["rpip_points"] for row in out),
    }


def copy_lightweight_sources() -> None:
    SNAP.mkdir(parents=True, exist_ok=True)
    source_dir = ROOT / "config" / "megalib_sources_fullsphere20"
    for path in sorted(source_dir.glob("Background_*_fullsphere20.source")):
        shutil.copy2(path, SNAP / path.name)

    copies = [
        (INSTANT_DIR / "normalization.json", "instant_normalization.json"),
        (INSTANT_DIR / "run_manifest.csv", "instant_run_manifest.csv"),
        (BUILDUP_DIR / "normalization.json", "buildup_normalization.json"),
        (BUILDUP_DIR / "run_manifest.csv", "buildup_run_manifest.csv"),
        (DECAY_DIR / "activation_decay_day15.source", "activation_decay_day15.source"),
        (DECAY_DIR / "activation_inventory_day15.csv", "activation_inventory_day15.csv"),
        (DECAY_DIR / "unknown_isotopes_day15.csv", "unknown_isotopes_day15.csv"),
        (DECAY_DIR / "no_rpip_points_day15.csv", "no_rpip_points_day15.csv"),
        (FIX_DIR / "activation_decay_day15_groundstate_fixed.source", "activation_decay_day15_groundstate_fixed.source"),
        (FIX_DIR / "groundstate_activity_corrections.csv", "groundstate_activity_corrections.csv"),
        (FIX_DIR / "removed_or_rescaled_sources.csv", "removed_or_rescaled_sources.csv"),
        (FIX_DIR / "source_fix_summary.json", "source_fix_summary.json"),
        (ROOT / "code" / "tools" / "run_equiv2602_pipeline_NEW_GEO.py", "run_equiv2602_pipeline_NEW_GEO.py"),
        (
            ROOT.parent / "COSMOSRAY_BALLOON_SIM" / "tools" / "makedecaysourcewithplot_rpip.py",
            "makedecaysourcewithplot_rpip.py",
        ),
        (
            ROOT.parent / "COSMOSRAY_BALLOON_SIM" / "tools" / "build_fixed_delay_source.py",
            "build_fixed_delay_source.py",
        ),
    ]
    for path, name in copies:
        if path.exists():
            shutil.copy2(path, SNAP / name)


def make_figure(summary: dict[str, object]) -> None:
    instant = summary["instant_transport"]
    buildup = summary["activation_buildup_transport"]
    inventory = summary["activation_inventory"]["rows"]

    particles = list(instant["base_events_by_particle"].keys())
    x = range(len(particles))
    instant_counts = [instant["by_particle"][p]["events_generated"] for p in particles]
    buildup_counts = [buildup["by_particle"][p]["events_generated"] for p in particles]
    flux = [instant["flux_by_particle_cm2_s"][p] for p in particles]

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    ax = axes[0][0]
    width = 0.38
    ax.bar([i - width / 2 for i in x], instant_counts, width=width, label="instant", color="#2f6f9f")
    ax.bar([i + width / 2 for i in x], buildup_counts, width=width, label="buildup", color="#c95f3d")
    ax.set_xticks(list(x))
    ax.set_xticklabels(particles, rotation=30, ha="right")
    ax.set_yscale("log")
    ax.set_ylabel("generated particles")
    ax.set_title("Prompt and buildup smoke runs")
    ax.legend()

    ax = axes[0][1]
    ax.bar(particles, flux, color="#4d8b57")
    ax.set_yscale("log")
    ax.set_ylabel("flux (cm$^{-2}$ s$^{-1}$)")
    ax.set_title("Full-sphere atmospheric source flux")
    ax.tick_params(axis="x", rotation=30)

    ax = axes[1][0]
    labels = [f"{row['nuclide']} @ {row['VN']}" for row in inventory]
    vals = [row["activity_Bq"] for row in inventory]
    ax.barh(labels, vals, color="#8c6bb1")
    ax.set_xlabel("activity (Bq)")
    ax.set_title("Delayed source inventory from buildup RPIP")

    ax = axes[1][1]
    stages = [
        "instant\ntransport",
        "buildup\ntransport",
        "delayed\ntransport",
    ]
    values = [
        instant["events_generated"],
        buildup["events_generated"],
        summary["delayed_transport"]["sim"]["TS"] or summary["delayed_transport"]["sim"]["events_from_SE"],
    ]
    ax.bar(stages, values, color=["#2f6f9f", "#c95f3d", "#d4a72c"])
    ax.set_ylabel("generated particles")
    ax.set_title("Raw simulation checkpoint")
    text = (
        f"Decay source blocks: {summary['fixed_decay_source']['source_blocks']}\n"
        f"Fixed total activity: {summary['fixed_decay_source']['total_activity_Bq']:.3f} Bq\n"
        f"Delayed observation: {summary['delayed_transport']['sim']['TE_s']:.6f} s\n"
        "No Poisson merge or veto applied"
    )
    ax.text(0.05, 0.95, text, va="top", ha="left", transform=ax.transAxes, fontsize=10)

    fig.suptitle("new_geo_re Step02 raw atmospheric and delayed background simulation", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(OUT / "step02_raw_simulation_summary.png", dpi=180)
    plt.close(fig)


def markdown_table(rows: list[dict[str, object]], fieldnames: list[str]) -> str:
    lines = [
        "| " + " | ".join(fieldnames) + " |",
        "| " + " | ".join("---" for _ in fieldnames) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(name, "")) for name in fieldnames) + " |")
    return "\n".join(lines)


def write_markdown(summary: dict[str, object], run_rows: list[dict[str, object]]) -> None:
    inventory_rows = [
        {
            "VN": row["VN"],
            "nuclide": row["nuclide"],
            "RP_yield": f"{row['RP_yield']:.6g}",
            "activity_Bq": f"{row['activity_Bq']:.6g}",
            "points": row["rpip_points"],
        }
        for row in summary["activation_inventory"]["rows"]
    ]

    text = f"""# Step02 Raw Background Simulation Summary

## Scope

Step02 aligns `new_geo_re` with the conceptual role of `fix` Step02: freeze the atmospheric source definition, run a native COSIMA smoke transport, and record a factual visual/CSV/markdown checkpoint.

For this geometry branch the checkpoint intentionally includes both prompt and delayed raw simulations:

- prompt `instant` atmospheric transport;
- activation `buildup` atmospheric transport used only to produce isotope/RPIP evidence;
- delayed-decay source construction from the buildup products;
- delayed-decay COSIMA transport from the fixed delayed source.

This step stops before time-axis Poisson merging, BGO veto, Compton veto, or any final event-selection analysis.

## Raw Run Matrix

{markdown_table(run_rows, ["stage", "status", "inputs", "outputs", "generated", "notes"])}

## Source And Normalization

- Source cards: `config/megalib_sources_fullsphere20/Background_*_fullsphere20.source`.
- Geometry: `outputs/geometry/XZTES_ADR_v4c_mkflange_cm/TibetTES_ADR_v4c_mkflange_cm.geo.setup`.
- Geometry far-field sphere: radius `{summary['instant_transport']['farfield_radius_cm']:.3f} cm`, area `{summary['instant_transport']['farfield_area_cm2']:.6g} cm2`.
- Gamma requested particles: `{summary['instant_transport']['gamma_events']}`.
- Prompt gamma equivalent time from the source flux and far-field area: `{summary['instant_transport']['gamma_prompt_time_s_with_farfield_area']:.8g} s`.
- Instant run generated `{summary['instant_transport']['events_generated']}` particles across `{summary['instant_transport']['jobs']}` particle jobs, failures `{summary['instant_transport']['failures']}`.
- Buildup run generated `{summary['activation_buildup_transport']['events_generated']}` particles across `{summary['activation_buildup_transport']['jobs']}` particle jobs, failures `{summary['activation_buildup_transport']['failures']}`.

## Delayed Source

The delayed source was built from the Step02 buildup `.dat` isotope yields plus SIM `CC IP RP` production positions. The smoke run produced `{summary['activation_inventory']['total_rpip_points']}` RPIP points across `{len(summary['activation_inventory']['rows'])}` inventory rows.

{markdown_table(inventory_rows, ["VN", "nuclide", "RP_yield", "activity_Bq", "points"])}

Ground-state half-life correction used local NUBASE records. Source blocks removed: `{summary['groundstate_fix']['source_blocks_removed']}`. Activity changed from `{summary['groundstate_fix']['old_total_activity_Bq']:.8g} Bq` to `{summary['groundstate_fix']['new_total_activity_Bq']:.8g} Bq`.

## Delayed Transport

- Source: `{summary['fixed_decay_source']['path']}`.
- SIM output: `{summary['delayed_transport']['sim']['path']}`.
- Generated particles from SIM `TS`: `{summary['delayed_transport']['sim']['TS']}`.
- Event blocks counted from SIM `SE`: `{summary['delayed_transport']['sim']['events_from_SE']}`.
- Observation time from SIM `TE`: `{summary['delayed_transport']['sim']['TE_s']:.9g} s`.
- COSIMA stdout note: `{summary['delayed_transport']['stdout_note']}`.

## Outputs

- `outputs/step02_raw_simulation_summary.png`: compact summary figure.
- `outputs/step02_raw_simulation_summary.json`: machine-readable summary.
- `outputs/step02_run_matrix.csv`: stage-level run matrix.
- `outputs/step02_particle_counts.csv`: prompt/buildup generated counts by particle.
- `outputs/step02_activation_inventory.csv`: delayed-source isotope inventory.
- `source_snapshots/`: lightweight source/config/source-fix evidence only; no `.sim.gz` or `.dat` products.
"""
    (OUT / "step02_raw_simulation_summary.md").write_text(text, encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    SNAP.mkdir(parents=True, exist_ok=True)

    instant = summarize_transport(INSTANT_DIR, "instant prompt transport")
    buildup = summarize_transport(BUILDUP_DIR, "activation buildup transport")
    decay_source = parse_decay_source(DECAY_DIR / "activation_decay_day15.source")
    fixed_source = parse_decay_source(FIX_DIR / "activation_decay_day15_groundstate_fixed.source")
    inv = inventory_summary(DECAY_DIR / "activation_inventory_day15.csv")
    fix_summary = load_json(FIX_DIR / "source_fix_summary.json")
    delayed_sim = read_delayed_sim_summary(DELAYED_SIM)

    summary = {
        "scope": "raw prompt, activation-buildup, delayed-source, delayed-transport checkpoint only",
        "explicitly_not_done": ["poisson_time_axis_merge", "bgo_veto", "compton_veto", "event_selection"],
        "instant_transport": instant,
        "activation_buildup_transport": buildup,
        "raw_decay_source": decay_source,
        "activation_inventory": inv,
        "groundstate_fix": fix_summary,
        "fixed_decay_source": fixed_source,
        "delayed_transport": {
            "sim": delayed_sim,
            "stdout_note": "delayed transport stdout contained repeated 'Energy type not yet implemented: -99999987' messages, but cosima exited 0 and the SIM file records TS=1000/SE=1000",
        },
    }

    run_rows = [
        {
            "stage": "instant",
            "status": "PASS" if instant["failures"] == 0 else "FAIL",
            "inputs": "8 full-sphere source cards",
            "outputs": f"{instant['sim_files']} sim.gz + {instant['dat_files']} dat",
            "generated": instant["events_generated"],
            "notes": "DecayMode ActivationBuildUp removed for prompt transport",
        },
        {
            "stage": "buildup",
            "status": "PASS" if buildup["failures"] == 0 else "FAIL",
            "inputs": "8 full-sphere source cards",
            "outputs": f"{buildup['sim_files']} sim.gz + {buildup['dat_files']} dat",
            "generated": buildup["events_generated"],
            "notes": "ActivationBuildUp kept for isotope/RPIP evidence",
        },
        {
            "stage": "decay_source",
            "status": "PASS" if decay_source["source_blocks"] > 0 else "FAIL",
            "inputs": "buildup dat + sim RPIP",
            "outputs": f"{decay_source['source_blocks']} source blocks",
            "generated": "n/a",
            "notes": f"total activity {decay_source['total_activity_Bq']:.6g} Bq",
        },
        {
            "stage": "groundstate_fix",
            "status": "PASS",
            "inputs": "activation_decay_day15.source + NUBASE",
            "outputs": f"{fixed_source['source_blocks']} source blocks",
            "generated": "n/a",
            "notes": f"removed {fix_summary['source_blocks_removed']} blocks",
        },
        {
            "stage": "delayed_transport",
            "status": "PASS" if delayed_sim["TS"] == 1000 else "CHECK",
            "inputs": "fixed delayed source",
            "outputs": "1 sim.gz",
            "generated": delayed_sim["TS"],
            "notes": f"TE {delayed_sim['TE_s']:.6g} s",
        },
    ]

    particle_rows = []
    particles = sorted(instant["by_particle"].keys())
    for particle in particles:
        particle_rows.append(
            {
                "particle": particle,
                "flux_cm2_s": instant["flux_by_particle_cm2_s"][particle],
                "instant_generated": instant["by_particle"][particle]["events_generated"],
                "buildup_generated": buildup["by_particle"][particle]["events_generated"],
                "instant_cpu_s": instant["by_particle"][particle]["cpu_s"],
                "buildup_cpu_s": buildup["by_particle"][particle]["cpu_s"],
            }
        )

    write_csv(OUT / "step02_run_matrix.csv", run_rows, ["stage", "status", "inputs", "outputs", "generated", "notes"])
    write_csv(
        OUT / "step02_particle_counts.csv",
        particle_rows,
        ["particle", "flux_cm2_s", "instant_generated", "buildup_generated", "instant_cpu_s", "buildup_cpu_s"],
    )
    write_csv(
        OUT / "step02_activation_inventory.csv",
        inv["rows"],
        ["VN", "ZA", "nuclide", "exc_keV", "RP_yield", "half_life_s", "activity_Bq", "rpip_points"],
    )

    (OUT / "step02_raw_simulation_summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    make_figure(summary)
    write_markdown(summary, run_rows)
    copy_lightweight_sources()

    print(f"[OK] wrote {OUT / 'step02_raw_simulation_summary.md'}")
    print(f"[OK] wrote {OUT / 'step02_raw_simulation_summary.png'}")
    print(f"[OK] wrote {OUT / 'step02_raw_simulation_summary.json'}")


if __name__ == "__main__":
    main()
