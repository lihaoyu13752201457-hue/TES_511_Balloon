#!/usr/bin/env python3
"""Summarize the NEW_GEO_RE ADR 511 keV science-source Cosima run."""

from __future__ import annotations

import argparse
import gzip
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT / "config" / "run_configs" / "Science_511_onaxis_ADR_cm_local.source"
DEFAULT_SIM = ROOT / "runs" / "science_511_onaxis_source" / "Science_511_onaxis_ADR_cmfix.inc1.id1.sim.gz"
DEFAULT_OUTDIR = ROOT / "outputs" / "reports" / "science_511_ADR_100k"


def parse_source(path: Path) -> dict:
    text = path.read_text(errors="replace")
    triggers = None
    trigger_match = re.search(r"^\S+\.Triggers\s+(\d+)\b", text, flags=re.MULTILINE)
    if trigger_match:
        triggers = int(trigger_match.group(1))

    flux = None
    flux_match = re.search(r"\bScience511_OnAxis\.Flux\s+([0-9.eE+-]+)\b", text)
    if flux_match:
        flux = float(flux_match.group(1))

    return {
        "source": str(path.relative_to(ROOT)),
        "triggers": triggers,
        "flux_ph_s": flux,
        "has_homogeneous_beam": "Science511_OnAxis.Beam HomogeneousBeam" in text,
        "has_mono_511": "Science511_OnAxis.Spectrum Mono 511.000000" in text,
    }


def summarize_event(stats: dict, energies: list[float]) -> None:
    if not energies:
        return
    total = sum(energies)
    stats["events_with_htsim"] += 1
    stats["htsim_energy_sum_keV"] += total
    stats["max_event_sum_keV"] = max(stats["max_event_sum_keV"], total)
    stats["min_event_sum_keV"] = min(stats["min_event_sum_keV"], total)
    if 480.0 <= total <= 550.0:
        stats["events_sum_480_550_keV"] += 1
    if 506.0 <= total <= 516.0:
        stats["events_sum_506_516_keV"] += 1
    if any(480.0 <= e <= 550.0 for e in energies):
        stats["events_any_hit_480_550_keV"] += 1


def parse_sim(path: Path) -> dict:
    stats = {
        "sim": str(path.relative_to(ROOT)),
        "sim_size_bytes": path.stat().st_size,
        "stored_events": 0,
        "events_with_htsim": 0,
        "htsim_hits": 0,
        "cc_hit_lines": 0,
        "events_sum_480_550_keV": 0,
        "events_sum_506_516_keV": 0,
        "events_any_hit_480_550_keV": 0,
        "htsim_energy_sum_keV": 0.0,
        "min_event_sum_keV": float("inf"),
        "max_event_sum_keV": float("-inf"),
        "geometry_in_sim": None,
        "beam_type_in_sim": None,
        "spectral_type_in_sim": None,
    }
    current_energies: list[float] = []
    seen_event = False

    with gzip.open(path, "rt", errors="replace") as f:
        for line in f:
            if line.startswith("Geometry "):
                stats["geometry_in_sim"] = line.split(maxsplit=1)[1].strip()
            elif line.startswith("BeamType "):
                stats["beam_type_in_sim"] = line.split(maxsplit=1)[1].strip()
            elif line.startswith("SpectralType "):
                stats["spectral_type_in_sim"] = line.split(maxsplit=1)[1].strip()
            elif line.startswith("ID "):
                if seen_event:
                    summarize_event(stats, current_energies)
                stats["stored_events"] += 1
                current_energies = []
                seen_event = True
            elif line.startswith("CC HIT "):
                stats["cc_hit_lines"] += 1
            elif line.startswith("HTsim"):
                stats["htsim_hits"] += 1
                parts = [p.strip() for p in line.split(";")]
                if len(parts) >= 5:
                    try:
                        current_energies.append(float(parts[4]))
                    except ValueError:
                        pass

    if seen_event:
        summarize_event(stats, current_energies)

    if stats["events_with_htsim"] == 0:
        stats["min_event_sum_keV"] = None
        stats["max_event_sum_keV"] = None
        stats["mean_event_sum_keV"] = None
    else:
        stats["mean_event_sum_keV"] = stats["htsim_energy_sum_keV"] / stats["events_with_htsim"]

    return stats


def add_rates(row: dict, triggers: int | None) -> None:
    if not triggers:
        return
    row["stored_events_per_trigger"] = row["stored_events"] / triggers
    row["events_with_htsim_per_trigger"] = row["events_with_htsim"] / triggers
    row["events_sum_480_550_per_trigger"] = row["events_sum_480_550_keV"] / triggers
    row["events_sum_506_516_per_trigger"] = row["events_sum_506_516_keV"] / triggers
    row["events_any_hit_480_550_per_trigger"] = row["events_any_hit_480_550_keV"] / triggers


def write_outputs(summary: dict, outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "science_511_100k_summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    source = summary["source_config"]
    sim = summary["sim_summary"]
    lines = [
        "# NEW_GEO_RE ADR Science 511 100k Summary",
        "",
        f"- status: {summary['status']}",
        f"- source: `{source['source']}`",
        f"- sim: `{sim['sim']}`",
        f"- generated triggers: {source['triggers']}",
        f"- stored SIM events: {sim['stored_events']}",
        f"- events with HTsim: {sim['events_with_htsim']}",
        f"- HTsim hits: {sim['htsim_hits']}",
        f"- event-summed 480-550 keV events: {sim['events_sum_480_550_keV']}",
        f"- event-summed 506-516 keV events: {sim['events_sum_506_516_keV']}",
        f"- any single HTsim hit 480-550 keV events: {sim['events_any_hit_480_550_keV']}",
        f"- stored events per trigger: {sim.get('stored_events_per_trigger')}",
        f"- event-summed 480-550 per trigger: {sim.get('events_sum_480_550_per_trigger')}",
        f"- beam in SIM: `{sim['beam_type_in_sim']}`",
        f"- spectrum in SIM: `{sim['spectral_type_in_sim']}`",
    ]
    (outdir / "science_511_100k_summary.md").write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--sim", type=Path, default=DEFAULT_SIM)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    args = parser.parse_args()

    source = parse_source(args.source)
    sim = parse_sim(args.sim)
    add_rates(sim, source["triggers"])

    status = "PASS"
    details = []
    if source["triggers"] != 100000:
        status = "FAIL"
        details.append(f"expected 100000 triggers, got {source['triggers']}")
    if not source["has_homogeneous_beam"] or not source["has_mono_511"]:
        status = "FAIL"
        details.append("source beam or spectrum token mismatch")
    if sim["stored_events"] <= 0 or sim["events_sum_480_550_keV"] <= 0:
        status = "FAIL"
        details.append("SIM has no stored 511-window events")
    if sim["spectral_type_in_sim"] != "Mono 511":
        status = "FAIL"
        details.append(f"unexpected SIM spectrum {sim['spectral_type_in_sim']!r}")

    summary = {
        "status": status,
        "details": "; ".join(details) if details else "completed",
        "source_config": source,
        "sim_summary": sim,
    }
    write_outputs(summary, args.outdir)

    print(
        f"{status} science511_100k: triggers={source['triggers']} "
        f"stored_events={sim['stored_events']} "
        f"event_sum_480_550={sim['events_sum_480_550_keV']} "
        f"event_sum_506_516={sim['events_sum_506_516_keV']}"
    )
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
