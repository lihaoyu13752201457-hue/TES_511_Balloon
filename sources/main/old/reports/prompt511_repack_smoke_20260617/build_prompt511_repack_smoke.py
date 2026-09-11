#!/usr/bin/env python3
"""Build and summarize prompt-511 local-repack smoke inputs.

This script intentionally writes only inside
outputs/reports/prompt511_repack_smoke_20260617. It copies the current v3p5
geometry, locally repacks the side-entry support/can volumes needed to reserve
a segmented W shadow liner, and builds source cards that point to the copied
geometry.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "outputs/reports/prompt511_repack_smoke_20260617"
RUNS = WORK / "runs"
BASE_GEO_DIR = ROOT / "outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
BASE_GEO_NAME = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
BASE_SETUP = BASE_GEO_DIR / f"{BASE_GEO_NAME}.geo.setup"
SOURCE_BASE_DIR = ROOT / "config/megalib_sources_fullsphere20_v3p5_centerfinger_tilt45"
SOURCE_OUT_DIR = WORK / "source_cards"
GEOM_OUT_DIR = WORK / "geometry_repack"
NEW_GEO_NAME = f"{BASE_GEO_NAME}_prompt511_repack_r4p25_5p95"
NEW_SETUP = GEOM_OUT_DIR / f"{NEW_GEO_NAME}.geo.setup"
OVERLAP_SOURCE = WORK / "overlap_repack.source"
OVERLAP_LOG = WORK / "overlap_repack.log"
MANIFEST = WORK / "prompt511_repack_smoke_manifest.json"
DIRECT_SUMMARY = WORK / "prompt511_repack_direct_summary.json"
DIRECT_MD = WORK / "prompt511_repack_direct_summary.md"
DEFAULT_DELAYED_REPLAY_SOURCES = 2000

LINE_WINDOW = (510.58, 511.42)
W_R0 = 4.25
W_R1 = 5.95
W_Z_SEGS = [(-8.75, -0.65), (0.65, 4.65)]
SIGNAL_GAP = (160.0, 200.0)

GEOMETRY_RE = re.compile(r"^Geometry\s+.+$", re.MULTILINE)
EVENTS_RE = re.compile(r"^(?P<run>\S+)\.Events\s+\d+\s*$", re.MULTILINE)
FILENAME_RE = re.compile(r"^(?P<run>\S+)\.FileName\s+.+$", re.MULTILINE)
ID_RE = re.compile(r"^ID\s+(\d+)")
TE_RE = re.compile(r"^TE\s+([-+0-9.eE]+)")
CC_HIT_RE = re.compile(r"^CC HIT\s+(\S+)\s+(.*)$")
KV_RE = re.compile(r"(\w+)=([^\s]+)")
DECAY_SOURCE_RE = re.compile(r"^DecayRun\.Source\s+(RP_\d+)\s*$", re.MULTILINE)
RP_PROP_RE = re.compile(r"^(RP_\d+)\.(\w+)\s+(.*)$")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def fmt(x: float) -> str:
    return f"{x:.6g}"


def replace_prop(text: str, volume: str, prop: str, value: str) -> str:
    pattern = re.compile(rf"^{re.escape(volume)}\.{re.escape(prop)}\s+.*$", re.MULTILINE)
    repl = f"{volume}.{prop} {value}"
    text, n = pattern.subn(repl, text, count=1)
    if n != 1:
        raise RuntimeError(f"failed to replace {volume}.{prop}")
    return text


def patch_volume(text: str, volume: str, shape: str | None = None, position: str | None = None) -> str:
    if shape is not None:
        text = replace_prop(text, volume, "Shape", shape)
    if position is not None:
        text = replace_prop(text, volume, "Position", position)
    return text


def append_w_liner(text: str) -> str:
    lines = [
        "",
        "// Prompt-511 repack smoke: segmented W shadow liner.",
        f"// r=[{W_R0},{W_R1}] cm, z={W_Z_SEGS}, signal phi gap={SIGNAL_GAP} deg.",
        "// This is a local design-smoke volume, not authority CAD.",
    ]
    for iz, (z0, z1) in enumerate(W_Z_SEGS, start=1):
        sectors = [
            ("a", 0.025, SIGNAL_GAP[0] - 0.05),
            ("b", SIGNAL_GAP[1] + 0.025, 360.0 - SIGNAL_GAP[1] - 0.05),
        ]
        for suffix, start, delta in sectors:
            volume = f"Prompt511_Repack_W_Liner_z{iz}_{suffix}"
            lines.extend(
                [
                    f"Volume {volume}",
                    f"{volume}.Material W",
                    f"{volume}.Visibility 1",
                    (
                        f"{volume}.Shape PCON {fmt(start)} {fmt(delta)} 2 "
                        f"{fmt(z0)} {fmt(W_R0)} {fmt(W_R1)} "
                        f"{fmt(z1)} {fmt(W_R0)} {fmt(W_R1)}"
                    ),
                    f"{volume}.Position 0 0 0",
                    f"{volume}.Mother InstrumentFrame",
                    "",
                ]
            )
    return text.rstrip() + "\n" + "\n".join(lines) + "\n"


def repack_geometry_text(text: str) -> str:
    # Compact the local light/magnetic can stack inside r < W_R0.
    panel_specs = {
        "Nb_SideEntry_Sample_Can_with_side_aperture_ZM_panel": ("BRIK 3.25 2.28 0.025", "0.05 0 -9.225"),
        "Nb_SideEntry_Sample_Can_with_side_aperture_YP_panel": ("BRIK 3.25 0.025 3.55", "0.05 2.27 -5.2"),
        "Nb_SideEntry_Sample_Can_with_side_aperture_YM_panel": ("BRIK 3.25 0.025 3.55", "0.05 -2.27 -5.2"),
        "Cryoperm_Horizontal_Sleeve_1p2mm_ZM_panel": ("BRIK 3.25 2.43 0.06", "0.05 0 -9.51"),
        "Cryoperm_Horizontal_Sleeve_1p2mm_YP_panel": ("BRIK 3.25 0.06 3.7", "0.05 2.42 -5.2"),
        "Cryoperm_Horizontal_Sleeve_1p2mm_YM_panel": ("BRIK 3.25 0.06 3.7", "0.05 -2.42 -5.2"),
        "Al_50mK_Local_Can_side_entry_ZM_panel": ("BRIK 3.25 2.58 0.04", "0.05 0 -9.74"),
        "Al_50mK_Local_Can_side_entry_YP_panel": ("BRIK 3.25 0.04 3.85", "0.05 2.57 -5.2"),
        "Al_50mK_Local_Can_side_entry_YM_panel": ("BRIK 3.25 0.04 3.85", "0.05 -2.57 -5.2"),
    }
    for volume, (shape, position) in panel_specs.items():
        text = patch_volume(text, volume, shape, position)

    # Keep the deepest support disk downstream of TES_L5 and inside the
    # reserved W annulus, with clearance to the four pre-existing edge rods.
    text = patch_volume(
        text,
        "Cu_SubstrateSupport_SolidDisk_L0_deepest",
        "BRIK 0.15 1.85 1.85",
        "3.42 0 -5.2",
    )

    # Shorten local off-axis Cu fingers into inner stubs so they do not enter
    # the reserved r=4.25-5.95 W annulus in this design smoke.
    for volume, hx, y, z in [
        ("Cu_ColdFinger_OffAxis_YP_ZP_from_Disk_to_Stem", 0.18, 1.1, -4.1),
        ("Cu_ColdFinger_OffAxis_YM_ZP_from_Disk_to_Stem", 0.18, -1.1, -4.1),
        ("Cu_ColdFinger_OffAxis_YP_ZM_from_Disk_to_Stem", 0.18, 1.1, -6.3),
        ("Cu_ColdFinger_OffAxis_YM_ZM_from_Disk_to_Stem", 0.18, -1.1, -6.3),
    ]:
        text = patch_volume(
            text,
            volume,
            f"BRIK {hx} 0.113137085 0.113137085",
            f"3.79 {y} {z}",
        )

    # Move the continuous heat exchanger outside the W liner while keeping it
    # inside the nearby cable/support radius.
    for volume in ("DR_Continuous_HEX_CuNi_MXC_to_CP", "DR_Continuous_HEX_CuNi_CP_to_Still"):
        text = patch_volume(text, volume, "PCON 0 108 2 -2.1 6.38 6.55 2.1 6.38 6.55")

    return append_w_liner(text)


def rewrite_setup(setup_path: Path) -> None:
    text = setup_path.read_text(encoding="utf-8")
    text = text.replace(f"Name {BASE_GEO_NAME}", f"Name {NEW_GEO_NAME}")
    text = text.replace(f"Include {BASE_GEO_NAME}.geo", f"Include {NEW_GEO_NAME}.geo")
    text = text.replace(f"Include {BASE_GEO_NAME}.det", f"Include {NEW_GEO_NAME}.det")
    setup_path.write_text(text, encoding="utf-8")


def build_geometry() -> dict[str, Any]:
    if GEOM_OUT_DIR.exists():
        shutil.rmtree(GEOM_OUT_DIR)
    shutil.copytree(BASE_GEO_DIR, GEOM_OUT_DIR)
    old_geo = GEOM_OUT_DIR / f"{BASE_GEO_NAME}.geo"
    old_setup = GEOM_OUT_DIR / f"{BASE_GEO_NAME}.geo.setup"
    old_det = GEOM_OUT_DIR / f"{BASE_GEO_NAME}.det"
    new_geo = GEOM_OUT_DIR / f"{NEW_GEO_NAME}.geo"
    new_setup = GEOM_OUT_DIR / f"{NEW_GEO_NAME}.geo.setup"
    new_det = GEOM_OUT_DIR / f"{NEW_GEO_NAME}.det"
    old_geo.rename(new_geo)
    old_setup.rename(new_setup)
    old_det.rename(new_det)
    rewrite_setup(new_setup)
    new_geo.write_text(repack_geometry_text(new_geo.read_text(encoding="utf-8")), encoding="utf-8")
    return {"geometry_setup": rel(new_setup), "geometry_geo": rel(new_geo), "geometry_det": rel(new_det)}


def migrate_sources(events_override: int | None = None) -> dict[str, Any]:
    if SOURCE_OUT_DIR.exists():
        shutil.rmtree(SOURCE_OUT_DIR)
    SOURCE_OUT_DIR.mkdir(parents=True)
    rows = []
    for src in sorted(SOURCE_BASE_DIR.glob("Background_*_fullsphere20.source")):
        text = src.read_text(encoding="utf-8", errors="replace")
        text = GEOMETRY_RE.sub(f"Geometry {NEW_SETUP}", text, count=1)
        if events_override is not None:
            text = EVENTS_RE.sub(lambda m: f"{m.group('run')}.Events {int(events_override)}", text, count=1)
        out = SOURCE_OUT_DIR / src.name
        out.write_text(text, encoding="utf-8")
        rows.append({"source": rel(out), "base_source": rel(src)})
    manifest = {
        "status": "PASS_PROMPT511_REPACK_SOURCE_CARDS",
        "source_dir": rel(SOURCE_OUT_DIR),
        "base_source_dir": rel(SOURCE_BASE_DIR),
        "geometry_setup": rel(NEW_SETUP),
        "farfield_radius_cm": 60.0,
        "sources": rows,
    }
    (SOURCE_OUT_DIR / "source_migration_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def write_overlap_source() -> dict[str, str]:
    text = f"""Version                     1
Geometry                    {NEW_SETUP}
CheckForOverlaps            1000 0.0001
PhysicsListEM               LivermorePol
Run Minimum
Minimum.FileName            /tmp/prompt511_repack_overlap
Minimum.NEvents             1
Minimum.Source MinimumS
MinimumS.ParticleType       1
MinimumS.Beam               PointSource 0 0 0
MinimumS.Spectrum           Mono 511
MinimumS.Flux               1.0
"""
    OVERLAP_SOURCE.write_text(text, encoding="utf-8")
    return {"overlap_source": rel(OVERLAP_SOURCE), "overlap_log": rel(OVERLAP_LOG)}


def reduce_delayed_replay_text(text: str, max_sources: int) -> tuple[str, dict[str, Any]]:
    source_ids = [m.group(1) for m in DECAY_SOURCE_RE.finditer(text)]
    total = len(source_ids)
    if total == 0:
        raise RuntimeError("delayed replay source has no DecayRun.Source entries")
    keep = min(int(max_sources), total)
    if keep <= 0:
        raise RuntimeError("delayed replay source keep count must be positive")
    if keep == total:
        return text, {"total_sources": total, "kept_sources": keep, "flux_scale": 1.0}

    if keep == 1:
        selected_indices = {0}
    else:
        selected_indices = {round(i * (total - 1) / (keep - 1)) for i in range(keep)}
    selected = {source_ids[i] for i in sorted(selected_indices)}
    scale = total / len(selected)

    lines: list[str] = []
    for line in text.splitlines():
        source_match = DECAY_SOURCE_RE.match(line)
        if source_match:
            if source_match.group(1) in selected:
                lines.append(line)
            continue

        prop_match = RP_PROP_RE.match(line)
        if prop_match:
            source_id, prop, value = prop_match.groups()
            if source_id not in selected:
                continue
            if prop == "Flux":
                value = fmt(float(value) * scale)
            lines.append(f"{source_id}.{prop} {value}")
            continue

        lines.append(line)

    lines.insert(
        1,
        (
            f"# prompt511_repack reduced delayed replay: kept {len(selected)}/{total} "
            f"RP sources and scaled kept fluxes by {scale:.12g}"
        ),
    )
    return "\n".join(lines).rstrip() + "\n", {
        "total_sources": total,
        "kept_sources": len(selected),
        "flux_scale": scale,
    }


def write_delayed_replay_source(triggers: int, max_sources: int) -> dict[str, Any]:
    base = ROOT / "runs/step02_delay_fix_v3p5_centerfinger_fullstat_v2_exactpos_m50000_s260613/activation_decay_day15_groundstate_fixed.source"
    outdir = RUNS / "delayed_replay_existing_inventory"
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / "activation_decay_day15_groundstate_fixed_repack_replay_reduced.source"
    text = base.read_text(encoding="utf-8", errors="replace")
    text = GEOMETRY_RE.sub(f"Geometry {NEW_SETUP}", text, count=1)
    text = re.sub(r"^DecayRun\.FileName\s+.+$", f"DecayRun.FileName {outdir / 'DelayedDecayExistingInventoryRepackReduced'}", text, count=1, flags=re.MULTILINE)
    text = re.sub(r"^DecayRun\.Triggers\s+\d+\s*$", f"DecayRun.Triggers {int(triggers)}", text, count=1, flags=re.MULTILINE)
    text, reduction = reduce_delayed_replay_text(text, max_sources)
    out.write_text(text, encoding="utf-8")
    return {
        "delayed_replay_source": rel(out),
        "source_prefix": rel(outdir / "DelayedDecayExistingInventoryRepackReduced"),
        "triggers": str(int(triggers)),
        "source_reduction": reduction,
        "boundary": "flux-preserving transport replay of downsampled existing delayed inventory only; it does not include new W-liner activation",
    }


def build_inputs(args: argparse.Namespace) -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "PASS_PROMPT511_REPACK_SMOKE_INPUTS",
        "constraints": rel(WORK / "CONSTRAINTS.md"),
        "base_geometry": rel(BASE_SETUP),
        "geometry": build_geometry(),
        "source_cards": migrate_sources(args.events_override),
        "overlap": write_overlap_source(),
        "delayed_replay": write_delayed_replay_source(args.delayed_replay_triggers, args.delayed_replay_sources),
        "analytic_screen_upper_bound": {
            "basis": rel(ROOT / "outputs/reports/prompt511_entry_audit_20260617/current_eplus_prompt_final_records.json"),
            "W_liner_r_cm": [W_R0, W_R1],
            "W_liner_z_segments_cm": W_Z_SEGS,
            "signal_gap_deg": SIGNAL_GAP,
            "expected_prompt_eplus_suppression_upper_bound": "about 4.6x from the 80-event geometric screen; MC can only reduce this if W add-back matters",
        },
    }
    MANIFEST.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "manifest": rel(MANIFEST)}, indent=2, ensure_ascii=False))


def parse_cc_hit(line: str) -> tuple[str, float] | None:
    m = CC_HIT_RE.match(line.strip())
    if not m:
        return None
    vol = m.group(1)
    kv = dict(KV_RE.findall(m.group(2)))
    try:
        return vol, float(kv["edep_keV"])
    except Exception:
        return None


def sim_te(path: Path) -> float | None:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", errors="ignore") as fh:
        for raw in fh:
            m = TE_RE.match(raw.strip())
            if m:
                return float(m.group(1))
    return None


def parse_sim_raw_window(path: Path, rate_per_event: float) -> dict[str, Any]:
    current_id: int | None = None
    tes_total = 0.0
    events_seen = 0
    kept = []
    opener = gzip.open if path.suffix == ".gz" else open

    def flush() -> None:
        nonlocal current_id, tes_total
        if current_id is None:
            return
        if LINE_WINDOW[0] <= tes_total < LINE_WINDOW[1]:
            kept.append({"local_id": current_id, "tes_total_keV": tes_total})
        current_id = None
        tes_total = 0.0

    with opener(path, "rt", encoding="utf-8", errors="ignore") as fh:
        for raw in fh:
            line = raw.strip()
            if line == "SE":
                flush()
                continue
            m_id = ID_RE.match(line)
            if m_id:
                current_id = int(m_id.group(1))
                events_seen += 1
                continue
            if not line.startswith("CC HIT TP_L"):
                continue
            hit = parse_cc_hit(line)
            if hit is not None:
                _vol, edep = hit
                tes_total += edep
    flush()
    return {
        "path": rel(path),
        "events_seen": events_seen,
        "line_window_events": len(kept),
        "line_window_rate_s-1": len(kept) * rate_per_event,
        "rate_per_event_s-1": rate_per_event,
        "examples": kept[:20],
    }


def load_prompt_rates(prompt_dir: Path) -> dict[str, float]:
    norm = json.loads((prompt_dir / "normalization.json").read_text(encoding="utf-8"))
    rows = {}
    for tag in norm["selected_particles"]:
        dats = sorted(prompt_dir.glob(f"Background_{tag}_fullsphere20_*.dat.inc1.dat"))
        tt_sum = 0.0
        for dat in dats:
            for raw in dat.read_text(encoding="utf-8", errors="ignore").splitlines():
                if raw.startswith("TT "):
                    tt_sum += float(raw.split()[1])
        if tt_sum > 0:
            rows[tag] = 1.0 / tt_sum
    return rows


def summarize_direct(args: argparse.Namespace) -> None:
    prompt_dir = Path(args.prompt_dir) if args.prompt_dir else RUNS / "instant_lowstat"
    delayed_sim = Path(args.delayed_sim) if args.delayed_sim else None
    prompt_rates = load_prompt_rates(prompt_dir) if prompt_dir.exists() and (prompt_dir / "normalization.json").exists() else {}
    prompt_rows = []
    for sim in sorted(prompt_dir.glob("*.sim.gz")):
        tag = "unknown"
        m = re.search(r"Background_([^_]+)_", sim.name)
        if m:
            tag = m.group(1).lower()
        rate = prompt_rates.get(tag)
        if rate is None:
            continue
        prompt_rows.append({**parse_sim_raw_window(sim, rate), "stream": "prompt", "tag": tag})

    delayed_rows = []
    if delayed_sim is not None and delayed_sim.exists():
        te = sim_te(delayed_sim)
        if te and te > 0:
            delayed_rows.append({**parse_sim_raw_window(delayed_sim, 1.0 / te), "stream": "delayed", "tag": "activation", "TE_s": te})

    by_stream = defaultdict(lambda: {"events": 0, "rate_s-1": 0.0})
    by_tag = defaultdict(lambda: {"events": 0, "rate_s-1": 0.0})
    for row in prompt_rows + delayed_rows:
        by_stream[row["stream"]]["events"] += int(row["line_window_events"])
        by_stream[row["stream"]]["rate_s-1"] += float(row["line_window_rate_s-1"])
        by_tag[f"{row['stream']}:{row['tag']}"]["events"] += int(row["line_window_events"])
        by_tag[f"{row['stream']}:{row['tag']}"]["rate_s-1"] += float(row["line_window_rate_s-1"])

    payload = {
        "status": "PASS_PROMPT511_REPACK_DIRECT_PARSE",
        "claim_level": "raw TES line-window direct smoke; no veto, no Compton/FoV, no time curve",
        "line_window_keV": list(LINE_WINDOW),
        "inputs": {
            "prompt_dir": rel(prompt_dir),
            "delayed_sim": rel(delayed_sim) if delayed_sim else None,
            "manifest": rel(MANIFEST),
        },
        "totals_by_stream": dict(by_stream),
        "totals_by_stream_tag": dict(by_tag),
        "prompt_files": prompt_rows,
        "delayed_files": delayed_rows,
        "limitations": [
            "Raw TES line-window only; no active veto or Compton/FoV rejection.",
            "If delayed_sim is the replay source, new W-liner activation is not included.",
            "Low-stat event counts are not rate authority.",
        ],
    }
    DIRECT_SUMMARY.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Prompt-511 Repack Direct Smoke Summary",
        "",
        f"Status: `{payload['status']}`",
        "",
        "| stream | events | raw line-window rate [s^-1] |",
        "|---|---:|---:|",
    ]
    for stream in sorted(by_stream):
        row = by_stream[stream]
        lines.append(f"| {stream} | {int(row['events'])} | {float(row['rate_s-1']):.6g} |")
    lines.extend(["", "By stream/tag:", "", "| stream:tag | events | rate [s^-1] |", "|---|---:|---:|"])
    for key in sorted(by_tag):
        row = by_tag[key]
        lines.append(f"| {key} | {int(row['events'])} | {float(row['rate_s-1']):.6g} |")
    lines.extend(["", "Limitations:", ""])
    lines.extend(f"- {item}" for item in payload["limitations"])
    DIRECT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "summary": rel(DIRECT_SUMMARY), "report": rel(DIRECT_MD)}, indent=2, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    build = sub.add_parser("build-inputs")
    build.add_argument("--events-override", type=int, default=None)
    build.add_argument("--delayed-replay-triggers", type=int, default=20000)
    build.add_argument("--delayed-replay-sources", type=int, default=DEFAULT_DELAYED_REPLAY_SOURCES)
    direct = sub.add_parser("direct-summary")
    direct.add_argument("--prompt-dir", default="")
    direct.add_argument("--delayed-sim", default="")
    args = parser.parse_args()
    if args.cmd == "build-inputs":
        build_inputs(args)
    elif args.cmd == "direct-summary":
        summarize_direct(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
