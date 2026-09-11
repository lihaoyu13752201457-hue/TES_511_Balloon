#!/usr/bin/env python3
"""Build a W2 background-source breakdown for the v3p5 center-finger branch."""

from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
import os
import pickle
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-newgeo")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
STEP05_SCRIPT = ROOT / "code" / "tools" / "build_v3p5_centerfinger_step05_l1_response.py"
W2 = (510.58, 511.42)

CC_HIT_FIELD_RE = re.compile(r"\b(?P<key>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>\S+)")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_step05_module():
    spec = importlib.util.spec_from_file_location("build_v3p5_centerfinger_step05_l1_response", STEP05_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {STEP05_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def step05_out(label: str) -> Path:
    if label == "1of10":
        return ROOT / "stepwise_maintenance" / "step05_veto_time_axis" / "outputs_v3p5_centerfinger_l1"
    return ROOT / "stepwise_maintenance" / "step05_veto_time_axis" / f"outputs_v3p5_centerfinger_{label}_l1"


def step08_out(label: str) -> Path:
    return ROOT / "stepwise_maintenance" / "step08_significance" / f"outputs_v3p5_centerfinger_{label}" / "w2_background_source_breakdown"


def delayed_sim(label: str) -> Path:
    return ROOT / "runs" / f"step02_delayed_transport_v3p5_centerfinger_{label}" / "DelayedDecayRPIPGroundStateFixed.inc1.id1.sim.gz"


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def grouped(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    acc: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        k = tuple(row.get(key, "") for key in keys)
        item = acc.setdefault(k, {key: row.get(key, "") for key in keys} | {"events": 0, "rate_hz": 0.0})
        item["events"] += 1
        item["rate_hz"] += float(row["rate_hz"])
    out = list(acc.values())
    total = sum(float(row["rate_hz"]) for row in out)
    for row in out:
        row["fraction"] = float(row["rate_hz"]) / total if total > 0 else 0.0
    out.sort(key=lambda row: float(row["rate_hz"]), reverse=True)
    return out


def select_w2_background_events(cat: dict[str, Any], step05_mod: Any) -> list[int]:
    disk = step05_mod.side_entry_disk()
    selected: list[int] = []
    stream = cat["stream"]
    mask = (
        (stream != "science")
        & (cat["tes_total_keV"] >= W2[0])
        & (cat["tes_total_keV"] < W2[1])
        & (cat["bgo_total_keV"] < 50.0)
    )
    for idx in np.flatnonzero(mask):
        keep, _cls = step05_mod.side_keep_from_hits(step05_mod.event_hits(cat, int(idx)), disk, "keep")
        if keep:
            selected.append(int(idx))
    return selected


def parse_delayed_event_metadata(sim_path: Path, wanted_ids: set[int]) -> dict[int, dict[str, str]]:
    out: dict[int, dict[str, str]] = {}
    if not wanted_ids:
        return out

    cur_id: int | None = None
    first_volume = ""
    first_primary = ""
    first_primary_volume = ""
    with gzip.open(sim_path, "rt", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if line.startswith("SE"):
                if cur_id in wanted_ids:
                    out[cur_id] = {
                        "primary_nuclide": first_primary or "unknown",
                        "source_volume": first_primary_volume or first_volume or "unknown",
                    }
                    if len(out) == len(wanted_ids):
                        break
                cur_id = None
                first_volume = ""
                first_primary = ""
                first_primary_volume = ""
                continue
            if line.startswith("ID "):
                parts = line.split()
                cur_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
                continue
            if cur_id not in wanted_ids:
                continue
            if not line.startswith("CC HIT "):
                continue
            parts = line.split(maxsplit=3)
            if len(parts) < 3:
                continue
            volume = parts[2]
            fields = {m.group("key"): m.group("value") for m in CC_HIT_FIELD_RE.finditer(line)}
            prim = fields.get("prim", "")
            pid = fields.get("pid", "")
            if not first_volume:
                first_volume = volume
            if not first_primary and prim not in ("", "none"):
                first_primary = prim
            if not first_primary_volume and prim == first_primary and pid == "0":
                first_primary_volume = volume

    if cur_id in wanted_ids and cur_id not in out:
        out[cur_id] = {
            "primary_nuclide": first_primary or "unknown",
            "source_volume": first_primary_volume or first_volume or "unknown",
        }
    return out


def plot_breakdown(outdir: Path, component_rows: list[dict[str, Any]], stream_rows: list[dict[str, Any]]) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8), gridspec_kw={"width_ratios": [2.3, 1.0]})
    top = component_rows[:12]
    labels = [row["component"] for row in reversed(top)]
    values = [float(row["rate_hz"]) for row in reversed(top)]
    axes[0].barh(labels, values, color="#4477AA")
    axes[0].set_xlabel("W2 final background rate (cps)")
    axes[0].set_title("Top W2 Components")
    axes[0].grid(axis="x", alpha=0.25)

    stream_labels = [row["stream"] for row in stream_rows]
    stream_values = [float(row["rate_hz"]) for row in stream_rows]
    axes[1].bar(stream_labels, stream_values, color=["#66AA55", "#CC6677"][: len(stream_rows)])
    axes[1].set_ylabel("cps")
    axes[1].set_title("Stream Split")
    axes[1].grid(axis="y", alpha=0.25)
    fig.tight_layout()
    path = outdir / "w2_background_source_breakdown.png"
    fig.savefig(path, dpi=190)
    plt.close(fig)
    return path


def markdown(summary: dict[str, Any], top_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# v3p5 W2 Background Source Breakdown",
        "",
        f"Status: `{summary['status']}`.",
        "",
        f"Statistics label: `{summary['statistics_label']}`.",
        "",
        f"Selection: `{summary['selection']}`.",
        "",
        f"Total selected W2 final background rate: `{summary['total_rate_hz']:.6g}` cps from `{summary['selected_events']}` catalog events.",
        "",
        "## Top Components",
        "",
        "| rank | component | events | rate cps | fraction |",
        "| ---: | --- | ---: | ---: | ---: |",
    ]
    for i, row in enumerate(top_rows[:15], start=1):
        lines.append(
            f"| {i} | {row['component']} | {row['events']} | {float(row['rate_hz']):.6g} | {float(row['fraction']):.3f} |"
        )
    lines.extend(
        [
            "",
            "Artifacts:",
            f"- component CSV: `{summary['outputs']['components_csv']}`",
            f"- stream CSV: `{summary['outputs']['streams_csv']}`",
            f"- delayed nuclide CSV: `{summary['outputs']['delayed_nuclides_csv']}`",
            f"- figure: `{summary['outputs']['figure']}`",
            "",
            "Notes:",
            "- Prompt components are grouped by atmospheric source particle tag.",
            "- Delayed components are grouped by primary decay nuclide and first primary-volume hit parsed from the delayed SIM.",
            "- The same Step05 side-entry Compton/FoV selection is recomputed here for W2 background events.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="fullstat_v2", help="Run/output label, e.g. fullstat_v2 or 1of10")
    args = ap.parse_args()

    outdir = step08_out(args.label)
    outdir.mkdir(parents=True, exist_ok=True)
    cat_path = step05_out(args.label) / "work" / "event_catalog.pkl"
    cat = pickle.loads(cat_path.read_bytes())
    step05_mod = load_step05_module()
    step05_mod.configure_paths(args.label)

    selected = select_w2_background_events(cat, step05_mod)
    delayed_ids = {int(cat["local_id"][idx]) for idx in selected if str(cat["stream"][idx]) == "delayed"}
    delayed_meta = parse_delayed_event_metadata(delayed_sim(args.label), delayed_ids)

    event_rows: list[dict[str, Any]] = []
    for idx in selected:
        stream = str(cat["stream"][idx])
        tag = str(cat["tag"][idx])
        local_id = int(cat["local_id"][idx])
        rate = float(cat["rate_hz"][idx])
        if stream == "delayed":
            meta = delayed_meta.get(local_id, {"primary_nuclide": "unknown", "source_volume": "unknown"})
            primary = meta["primary_nuclide"]
            volume = meta["source_volume"]
            component = f"delayed:{primary}:{volume}"
        else:
            primary = tag
            volume = ""
            component = f"prompt:{tag}"
        event_rows.append(
            {
                "event_index": idx,
                "stream": stream,
                "tag": tag,
                "local_id": local_id,
                "primary": primary,
                "source_volume": volume,
                "component": component,
                "rate_hz": rate,
                "tes_total_keV": float(cat["tes_total_keV"][idx]),
                "bgo_total_keV": float(cat["bgo_total_keV"][idx]),
                "source_file": str(cat["source_file"][idx]),
            }
        )

    component_rows = grouped(event_rows, ("component", "stream", "tag", "primary", "source_volume"))
    stream_rows = grouped(event_rows, ("stream",))
    prompt_rows = grouped([row for row in event_rows if row["stream"] == "prompt"], ("tag",))
    delayed_nuclide_rows = grouped([row for row in event_rows if row["stream"] == "delayed"], ("primary",))
    delayed_volume_rows = grouped([row for row in event_rows if row["stream"] == "delayed"], ("source_volume",))

    write_csv(outdir / "w2_background_selected_events.csv", event_rows)
    write_csv(outdir / "w2_background_components.csv", component_rows)
    write_csv(outdir / "w2_background_streams.csv", stream_rows)
    write_csv(outdir / "w2_prompt_particles.csv", prompt_rows)
    write_csv(outdir / "w2_delayed_nuclides.csv", delayed_nuclide_rows)
    write_csv(outdir / "w2_delayed_source_volumes.csv", delayed_volume_rows)
    fig = plot_breakdown(outdir, component_rows, stream_rows)
    summary = {
        "status": "PASS_V3P5_W2_BACKGROUND_SOURCE_BREAKDOWN",
        "statistics_label": args.label,
        "selection": "W2 510.58-511.42 keV, active veto <50 keV, side-entry Compton/FoV keep/reject-kept",
        "cat_path": rel(cat_path),
        "selected_events": len(event_rows),
        "total_rate_hz": sum(float(row["rate_hz"]) for row in event_rows),
        "outputs": {
            "summary_json": rel(outdir / "w2_background_source_breakdown_summary.json"),
            "markdown": rel(outdir / "w2_background_source_breakdown.md"),
            "selected_events_csv": rel(outdir / "w2_background_selected_events.csv"),
            "components_csv": rel(outdir / "w2_background_components.csv"),
            "streams_csv": rel(outdir / "w2_background_streams.csv"),
            "prompt_particles_csv": rel(outdir / "w2_prompt_particles.csv"),
            "delayed_nuclides_csv": rel(outdir / "w2_delayed_nuclides.csv"),
            "delayed_source_volumes_csv": rel(outdir / "w2_delayed_source_volumes.csv"),
            "figure": rel(fig),
        },
        "top_components": component_rows[:15],
    }
    write_json(outdir / "w2_background_source_breakdown_summary.json", summary)
    (outdir / "w2_background_source_breakdown.md").write_text(markdown(summary, component_rows), encoding="utf-8")
    print(json.dumps({"status": summary["status"], "selected_events": len(event_rows), "total_rate_hz": summary["total_rate_hz"], "out": rel(outdir)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
