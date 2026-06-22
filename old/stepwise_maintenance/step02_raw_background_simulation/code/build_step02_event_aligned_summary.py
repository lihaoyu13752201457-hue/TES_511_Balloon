#!/usr/bin/env python3
"""Build the Step02 event-aligned production summary for new_geo_re."""

from __future__ import annotations

import csv
import gzip
import json
import re
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[3]
STEP_DIR = ROOT / "stepwise_maintenance" / "step02_raw_background_simulation"
OUT = STEP_DIR / "outputs"

INSTANT_DIR = ROOT / "runs" / "step02_instant_equiv2602_aligned"
BUILDUP_DIR = ROOT / "runs" / "step02_buildup_equiv2602_aligned"
DECAY_DIR = ROOT / "runs" / "step02_decay_source_equiv2602_aligned"
FIX_DIR = ROOT / "runs" / "step02_delay_fix_equiv2602_aligned"
DELAYED_DIR = ROOT / "runs" / "step02_delayed_transport_equiv2602_aligned"
DELAYED_SIM = DELAYED_DIR / "DelayedDecayRPIPGroundStateFixed.inc1.id1.sim.gz"
DELAYED_LOG = DELAYED_DIR / "cosima_delayed_transport_1m.log"

OLD_INSTANT_NORM = (
    ROOT.parent
    / "COSMOSRAY_BALLOON_SIM"
    / "production_runs"
    / "instant_equiv2602"
    / "normalization.json"
)

SOURCE_RE = re.compile(r"^DecayRun\.Source\s+(?P<name>\S+)")
FLUX_RE = re.compile(r"^(?P<name>\S+)\.Flux\s+(?P<flux>[-+0-9.eE]+)")


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
    by_particle: dict[str, dict[str, object]] = defaultdict(
        lambda: {
            "events_requested": 0,
            "events_generated": 0,
            "jobs": 0,
            "cpu_s": 0.0,
            "sim_size_bytes": 0,
            "dat_size_bytes": 0,
            "failures": 0,
        }
    )
    for row in jobs:
        particle = row["particle"]
        item = by_particle[particle]
        item["events_requested"] += int(row["events"])
        item["events_generated"] += int(row["generated_particles"])
        item["jobs"] += 1
        item["cpu_s"] += float(row["cpu_s"])
        item["sim_size_bytes"] += int(row["sim_size_bytes"])
        item["dat_size_bytes"] += int(row["dat_size_bytes"])
        if row["status"] != "PASS":
            item["failures"] += 1

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
        "gamma_splits": int(norm["gamma_splits"]),
        "non_gamma_replicas": int(norm["non_gamma_replicas"]),
        "farfield_radius_cm": float(norm["farfield_radius_cm"]),
        "farfield_area_cm2": float(norm["farfield_area_cm2"]),
        "gamma_prompt_time_s_with_farfield_area": float(norm["gamma_prompt_time_s_with_farfield_area"]),
        "flux_by_particle_cm2_s": norm["flux_by_particle_cm2_s"],
        "base_events_by_particle": norm["base_events_by_particle"],
        "by_particle": dict(by_particle),
    }


def parse_decay_source(path: Path) -> dict[str, object]:
    source_names: list[str] = []
    flux_by_name: dict[str, float] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        sm = SOURCE_RE.match(stripped)
        if sm:
            source_names.append(sm.group("name"))
            continue
        fm = FLUX_RE.match(stripped)
        if fm:
            flux_by_name[fm.group("name")] = float(fm.group("flux"))
    return {
        "path": rel(path),
        "source_blocks": len(source_names),
        "total_activity_Bq": sum(flux_by_name.get(name, 0.0) for name in source_names),
    }


def inventory_summary(path: Path) -> dict[str, object]:
    rows = load_csv(path)
    clean_rows = []
    for row in rows:
        clean_rows.append(
            {
                "VN": row["VN"],
                "ZA": int(row["ZA"]),
                "nuclide": row["nuclide"],
                "exc_keV": float(row["exc_keV"]),
                "RP_yield": float(row["RP_yield"]),
                "activity_Bq": float(row["Activity_Bq"]),
                "rpip_points": int(row["Points"]),
            }
        )
    return {
        "path": rel(path),
        "rows": clean_rows,
        "total_activity_Bq": sum(row["activity_Bq"] for row in clean_rows),
        "total_rpip_points": sum(row["rpip_points"] for row in clean_rows),
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


def count_log_note(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"path": rel(path), "energy_type_messages": None}
    count = 0
    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if "Energy type not yet implemented: -99999987" in line:
                count += 1
    return {"path": rel(path), "energy_type_messages": count}


def make_particle_rows(summary: dict[str, object]) -> list[dict[str, object]]:
    instant = summary["instant_transport"]
    buildup = summary["activation_buildup_transport"]
    old = summary["old_balloonsim_target"]
    rows = []
    for particle in sorted(instant["by_particle"].keys()):
        rows.append(
            {
                "particle": particle,
                "old_target_events": old["event_targets_by_particle"][particle],
                "new_instant_events": instant["by_particle"][particle]["events_generated"],
                "new_buildup_events": buildup["by_particle"][particle]["events_generated"],
                "instant_delta": instant["by_particle"][particle]["events_generated"]
                - old["event_targets_by_particle"][particle],
                "buildup_delta": buildup["by_particle"][particle]["events_generated"]
                - old["event_targets_by_particle"][particle],
            }
        )
    return rows


def make_figure(summary: dict[str, object], particle_rows: list[dict[str, object]]) -> None:
    particles = [row["particle"] for row in particle_rows]
    old_counts = [row["old_target_events"] for row in particle_rows]
    instant_counts = [row["new_instant_events"] for row in particle_rows]
    buildup_counts = [row["new_buildup_events"] for row in particle_rows]

    inv_rows = sorted(
        summary["activation_inventory"]["rows"],
        key=lambda row: row["activity_Bq"],
        reverse=True,
    )[:15]

    fig, axes = plt.subplots(2, 2, figsize=(13, 8.5))
    ax = axes[0][0]
    x = range(len(particles))
    width = 0.26
    ax.bar([i - width for i in x], old_counts, width=width, label="old target", color="#5b6770")
    ax.bar(x, instant_counts, width=width, label="new instant", color="#2f6f9f")
    ax.bar([i + width for i in x], buildup_counts, width=width, label="new buildup", color="#c95f3d")
    ax.set_xticks(list(x))
    ax.set_xticklabels(particles, rotation=30, ha="right")
    ax.set_yscale("log")
    ax.set_ylabel("events")
    ax.set_title("Event-count alignment by particle")
    ax.legend(fontsize=8)

    ax = axes[0][1]
    stages = ["instant", "buildup", "delayed"]
    values = [
        summary["instant_transport"]["events_generated"],
        summary["activation_buildup_transport"]["events_generated"],
        summary["delayed_transport"]["sim"]["TS"],
    ]
    ax.bar(stages, values, color=["#2f6f9f", "#c95f3d", "#d4a72c"])
    ax.set_yscale("log")
    ax.set_ylabel("events")
    ax.set_title("Aligned raw simulation products")

    ax = axes[1][0]
    ax.barh(
        [f"{row['nuclide']} @ {row['VN']}" for row in reversed(inv_rows)],
        [row["activity_Bq"] for row in reversed(inv_rows)],
        color="#4d8b57",
    )
    ax.set_xlabel("activity (Bq)")
    ax.set_title("Top delayed-source activities")

    ax = axes[1][1]
    text = (
        f"Prompt/buildup events: {summary['instant_transport']['events_generated']:,}\n"
        f"Delayed TS/SE: {summary['delayed_transport']['sim']['TS']:,} / "
        f"{summary['delayed_transport']['sim']['events_from_SE']:,}\n"
        f"Delayed TE: {summary['delayed_transport']['sim']['TE_s']:.6g} s\n"
        f"Fixed activity: {summary['fixed_decay_source']['total_activity_Bq']:.6g} Bq\n"
        f"New far-field radius: {summary['instant_transport']['farfield_radius_cm']:.1f} cm\n"
        f"Old target radius: {summary['old_balloonsim_target']['farfield_radius_cm']:.1f} cm\n"
        "Aligned on event counts, not physical exposure time"
    )
    ax.axis("off")
    ax.text(0.02, 0.96, text, va="top", ha="left", fontsize=11)

    fig.suptitle("new_geo_re Step02 event-aligned background simulation", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(OUT / "step02_event_aligned_summary.png", dpi=180)
    plt.close(fig)


def markdown_table(rows: list[dict[str, object]], fieldnames: list[str]) -> str:
    lines = [
        "| " + " | ".join(fieldnames) + " |",
        "| " + " | ".join("---" for _ in fieldnames) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(name, "")) for name in fieldnames) + " |")
    return "\n".join(lines)


def write_markdown(summary: dict[str, object], particle_rows: list[dict[str, object]]) -> None:
    old = summary["old_balloonsim_target"]
    instant = summary["instant_transport"]
    buildup = summary["activation_buildup_transport"]
    delayed = summary["delayed_transport"]["sim"]
    fix = summary["groundstate_fix"]

    text = f"""# Step02 Event-Aligned Production Summary

## Scope

This report records the production-scale event-count alignment between `new_geo_re` and the old `COSMOSRAY_BALLOON_SIM` balloon run family. It is still a raw Step02 product: no Poisson time-axis merge, BGO veto, Compton veto, or final event selection has been applied.

The alignment target is the old production run event budget, not the physical exposure time. `new_geo_re` uses its current geometry/source far-field area, so the gamma equivalent prompt time differs even though the requested event counts match.

## Alignment Target

- Old target normalization: `{old['path']}`.
- Old prompt far-field radius: `{old['farfield_radius_cm']:.3f} cm`, area `{old['farfield_area_cm2']:.6g} cm2`.
- Old prompt gamma equivalent time: `{old['gamma_prompt_time_s_with_farfield_area']:.8g} s`.
- New prompt far-field radius: `{instant['farfield_radius_cm']:.3f} cm`, area `{instant['farfield_area_cm2']:.6g} cm2`.
- New prompt gamma equivalent time: `{instant['gamma_prompt_time_s_with_farfield_area']:.8g} s`.

## Particle Event Counts

{markdown_table(particle_rows, ['particle', 'old_target_events', 'new_instant_events', 'new_buildup_events', 'instant_delta', 'buildup_delta'])}

## Run Products

- Instant run: `{instant['run_dir']}`, jobs `{instant['jobs']}`, failures `{instant['failures']}`, events `{instant['events_generated']:,}`, CPU `{instant['cpu_s']:.3f} s`.
- Buildup run: `{buildup['run_dir']}`, jobs `{buildup['jobs']}`, failures `{buildup['failures']}`, events `{buildup['events_generated']:,}`, CPU `{buildup['cpu_s']:.3f} s`.
- Delayed source: `{summary['raw_decay_source']['path']}`, source blocks `{summary['raw_decay_source']['source_blocks']}`, activity `{summary['raw_decay_source']['total_activity_Bq']:.8g} Bq`.
- Ground-state fixed source: `{summary['fixed_decay_source']['path']}`, source blocks `{summary['fixed_decay_source']['source_blocks']}`, activity `{summary['fixed_decay_source']['total_activity_Bq']:.8g} Bq`.
- Ground-state fix: removed `{fix['source_blocks_removed']}` source blocks; activity `{fix['old_total_activity_Bq']:.8g} Bq` -> `{fix['new_total_activity_Bq']:.8g} Bq`.
- Delayed transport SIM: `{delayed['path']}`, `TS {delayed['TS']}`, `SE {delayed['events_from_SE']}`, `TE {delayed['TE_s']:.9g} s`, size `{delayed['size_bytes']}` bytes.
- COSIMA log: `{summary['delayed_transport']['log']['path']}`, repeated `Energy type not yet implemented: -99999987` messages counted `{summary['delayed_transport']['log']['energy_type_messages']}`.

## Delayed Source Evidence

- Inventory rows: `{len(summary['activation_inventory']['rows'])}`.
- RPIP points: `{summary['activation_inventory']['total_rpip_points']}`.
- Inventory activity sum: `{summary['activation_inventory']['total_activity_Bq']:.8g} Bq`.

## Outputs

- `outputs/step02_event_aligned_summary.md`
- `outputs/step02_event_aligned_summary.json`
- `outputs/step02_event_aligned_particle_counts.csv`
- `outputs/step02_event_aligned_summary.png`
"""
    (OUT / "step02_event_aligned_summary.md").write_text(text, encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    instant = summarize_transport(INSTANT_DIR, "event-aligned instant prompt transport")
    buildup = summarize_transport(BUILDUP_DIR, "event-aligned activation buildup transport")
    old_norm = load_json(OLD_INSTANT_NORM)
    old_targets = {
        particle: int(events) * (1 if particle == "gamma" else int(old_norm["non_gamma_replicas"]))
        for particle, events in old_norm["base_events_by_particle"].items()
    }

    summary = {
        "scope": "event-count aligned raw prompt, activation-buildup, delayed-source, delayed-transport checkpoint only",
        "explicitly_not_done": ["poisson_time_axis_merge", "bgo_veto", "compton_veto", "event_selection"],
        "old_balloonsim_target": {
            "path": rel(OLD_INSTANT_NORM),
            "farfield_radius_cm": float(old_norm["farfield_radius_cm"]),
            "farfield_area_cm2": float(old_norm["farfield_area_cm2"]),
            "gamma_prompt_time_s_with_farfield_area": float(old_norm["gamma_prompt_time_s_with_farfield_area"]),
            "event_targets_by_particle": old_targets,
            "total_event_target": sum(old_targets.values()),
        },
        "instant_transport": instant,
        "activation_buildup_transport": buildup,
        "raw_decay_source": parse_decay_source(DECAY_DIR / "activation_decay_day15.source"),
        "activation_inventory": inventory_summary(DECAY_DIR / "activation_inventory_day15.csv"),
        "groundstate_fix": load_json(FIX_DIR / "source_fix_summary.json"),
        "fixed_decay_source": parse_decay_source(FIX_DIR / "activation_decay_day15_groundstate_fixed.source"),
        "delayed_transport": {
            "sim": read_delayed_sim_summary(DELAYED_SIM),
            "log": count_log_note(DELAYED_LOG),
        },
    }

    particle_rows = make_particle_rows(summary)

    write_csv(
        OUT / "step02_event_aligned_particle_counts.csv",
        particle_rows,
        ["particle", "old_target_events", "new_instant_events", "new_buildup_events", "instant_delta", "buildup_delta"],
    )
    (OUT / "step02_event_aligned_summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    make_figure(summary, particle_rows)
    write_markdown(summary, particle_rows)

    print(f"[OK] wrote {OUT / 'step02_event_aligned_summary.md'}")
    print(f"[OK] wrote {OUT / 'step02_event_aligned_summary.png'}")
    print(f"[OK] wrote {OUT / 'step02_event_aligned_summary.json'}")


if __name__ == "__main__":
    main()
