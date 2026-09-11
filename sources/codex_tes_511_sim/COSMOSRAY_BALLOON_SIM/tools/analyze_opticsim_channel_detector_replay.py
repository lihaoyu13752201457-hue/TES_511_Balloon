#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze an opticsim channel focal-plane replay through XZTES/Cosima."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/codex_tes_511_matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import analyze_opticsim_laue_detector_replay as replay_tools  # noqa: E402


WINDOWS = replay_tools.WINDOWS


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))


def read_per_ring_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_channel_ring_plot(per_ring_path: Path, out_png: Path) -> None:
    rows = read_per_ring_csv(per_ring_path)
    if not rows:
        return
    labels = [str(r["ring_id"]) for r in rows]
    survived = np.asarray([float(r["n_survived"]) / float(r["n_primaries"]) for r in rows])
    absorbed = np.asarray([float(r["n_absorbed"]) / float(r["n_primaries"]) for r in rows])
    blocked = np.asarray([float(r["n_entry_blocked"]) / float(r["n_primaries"]) for r in rows])
    leaked = np.asarray([float(r["n_leaked"]) / float(r["n_primaries"]) for r in rows])
    x = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    ax.bar(x, survived, label="survive")
    ax.bar(x, absorbed, bottom=survived, label="absorb")
    ax.bar(x, blocked, bottom=survived + absorbed, label="entry blocked")
    ax.bar(x, leaked, bottom=survived + absorbed + blocked, label="leak")
    ax.set_xticks(x, labels)
    ax.set_xlabel("channel ring id")
    ax.set_ylabel("fraction")
    ax.set_ylim(0, 1)
    ax.set_title("Channel wall-by-wall per-ring outcomes")
    ax.legend(fontsize=8, ncol=4)
    fig.tight_layout()
    fig.savefig(out_png, dpi=220)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sim", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--channel-summary", type=Path, required=True)
    ap.add_argument("--per-ring", type=Path, required=True)
    ap.add_argument("--confidence-summary", type=Path)
    ap.add_argument(
        "--outdir",
        type=Path,
        default=ROOT / "reports_260516" / "opticsim_channel_wallbywall_511_replay_20260521",
    )
    ap.add_argument("--background-cps", type=float, default=5.765235221601166)
    ap.add_argument("--reject-policy", default="keep")
    args = ap.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    manifest = load_json(args.manifest, {})
    channel = load_json(args.channel_summary, {})
    confidence = load_json(args.confidence_summary, {}) if args.confidence_summary else {}
    exposure_s = float(manifest.get("coordinate_policy", {}).get("duration_s") or 1800.0)

    n_primaries = int(channel["n_primaries"])
    n_survived = int(channel["n_survived"])
    aperture_area_cm2 = float(channel["aperture_area_cm2"])
    effective_area_cm2 = float(channel.get("effective_area_cm2", aperture_area_cm2 * float(channel["transmissivity"])))

    cat = replay_tools.parse_replay_catalog(args.sim, exposure_s)
    windows = {
        name: replay_tools.classify_window(cat, lo, hi, args.reject_policy)
        for name, (lo, hi) in WINDOWS.items()
    }

    for win in windows.values():
        for key in ("raw_count", "bgo_pass_count", "final_count"):
            win[f"{key.replace('_count', '')}_rate_hz_replay"] = float(win[key]) / exposure_s
        win["detector_final_survival_per_channel_focal_photon"] = float(win["final_count"]) / max(n_survived, 1)
        win["detector_final_survival_per_diffracted"] = win["detector_final_survival_per_channel_focal_photon"]
        win["end_to_end_final_survival_per_channel_primary"] = float(win["final_count"]) / max(n_primaries, 1)
        win["end_to_end_final_survival_per_laue_primary"] = win["end_to_end_final_survival_per_channel_primary"]
        win["channel_aperture_area_response_cm2"] = (
            aperture_area_cm2 * win["end_to_end_final_survival_per_channel_primary"]
        )
        win["geometric_area_response_cm2"] = win["channel_aperture_area_response_cm2"]
        win["demo_tile_area_response_cm2"] = win["geometric_area_response_cm2"]
        response = float(win["geometric_area_response_cm2"])
        win["T3_days_for_flux_1e_minus_4_geometric_area"] = (
            (3.0 * math.sqrt(args.background_cps) / (1.0e-4 * response)) ** 2 / 86400.0
            if response > 0
            else float("inf")
        )
        win["T3_days_for_flux_1e_minus_4_demo_area"] = win["T3_days_for_flux_1e_minus_4_geometric_area"]

    spectrum_png = args.outdir / "channel_detector_energy_spectrum.png"
    spectrum_csv = args.outdir / "channel_detector_energy_spectrum.csv"
    ring_png = args.outdir / "channel_per_ring_outcomes.png"
    replay_tools.write_spectrum(
        cat,
        spectrum_csv,
        spectrum_png,
        title="Opticsim channel wall-by-wall focal-plane replay through XZTES",
    )
    write_channel_ring_plot(args.per_ring, ring_png)
    timing = replay_tools.eventlist_time_stats(Path(manifest["event_list"]))
    summary = {
        "status": "PASS",
        "claim_level": "OPTICSIM_CHANNEL_WALLBYWALL_DETECTOR_REPLAY",
        "sim": str(args.sim),
        "manifest": str(args.manifest),
        "channel_summary": str(args.channel_summary),
        "confidence_summary": str(args.confidence_summary) if args.confidence_summary else None,
        "exposure_s": exposure_s,
        "eventlist_timing": timing,
        "channel": channel,
        "channel_confidence": confidence,
        "channel_aperture_area_cm2": aperture_area_cm2,
        "ring_tile_geometric_area_cm2": aperture_area_cm2,
        "ring_tile_geometric_area_cm2_demo": aperture_area_cm2,
        "estimated_channel_optics_effective_area_cm2": effective_area_cm2,
        "estimated_optics_effective_area_cm2": effective_area_cm2,
        "geometric_crystal_area_cm2": aperture_area_cm2,
        "detector_catalog": {
            "generated_events_seen": int(cat["n_generated_events_seen"]),
            "events_with_tes_or_bgo": int(len(cat["stream"])),
            "events_with_tes": int(sum(float(e) > 0.0 for e in cat["tes_total_keV"])),
            "events_with_bgo": int(sum(float(e) > 0.0 for e in cat["bgo_total_keV"])),
        },
        "windows": windows,
        "figures": [str(spectrum_png), str(ring_png)],
        "limitations": [
            "The imported channel optics is the current public-geometry wall-by-wall reconstruction from /home/ubuntu/opticsim.",
            "It is not the unpublished original 511-CAM IDL/IMD path model; the opticsim confidence report marks the 80 percent headline match as calibrated, not first-principles.",
            "Detector replay uses the same XZTES/Cosima geometry, BGO veto, and Compton/FoV classification helpers as the Laue route.",
            "Flux response is normalized by the channel aperture area and simulated wall-by-wall primary count.",
        ],
    }
    (args.outdir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    broad = windows["broad_480_550"]
    line = windows["line_510p3_511p8"]
    md = [
        "# Opticsim channel wall-by-wall detector replay 2026-05-21",
        "",
        "Status: `PASS`",
        "",
        "This run imports the closed current-stage channel optics phase space from `/home/ubuntu/opticsim` and replays it through the same XZTES/Cosima detector chain used by the Laue route.",
        "",
        "## Imported channel optics",
        "",
        f"- Channel primaries: `{n_primaries}`",
        f"- Focal-plane surviving photons: `{n_survived}` (`{float(channel['transmissivity']):.6g}`)",
        f"- Aperture area: `{aperture_area_cm2:.6g} cm2`",
        f"- Estimated optics effective area: `{effective_area_cm2:.6g} cm2`",
        f"- Focal spot D90: `{float(channel['spot_d90_cm']):.6g} cm`",
        f"- Cosima replay duration: `{exposure_s:.2f} s`",
        "",
        "## Detector selection",
        "",
        "| window | raw | BGO pass | final | detector final / channel focal photon | end-to-end final / channel primary | response |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| 480-550 keV | {broad['raw_count']} | {broad['bgo_pass_count']} | {broad['final_count']} | {broad['detector_final_survival_per_channel_focal_photon']:.6g} | {broad['end_to_end_final_survival_per_channel_primary']:.6g} | {broad['geometric_area_response_cm2']:.6g} |",
        f"| 510.3-511.8 keV | {line['raw_count']} | {line['bgo_pass_count']} | {line['final_count']} | {line['detector_final_survival_per_channel_focal_photon']:.6g} | {line['end_to_end_final_survival_per_channel_primary']:.6g} | {line['geometric_area_response_cm2']:.6g} |",
        "",
        "The response column is in `cps/(ph cm^-2 s^-1)` before atmospheric/visibility scaling.",
        "",
        "## Claim boundary",
        "",
        "The science channel route is closed at the same scaffold layer as the current Laue route. The channel optics evidence is stronger than a scalar requirement because it carries a wall-by-wall phase-space file, but it still lacks the unpublished original 511-CAM IDL source and exact assembly-tolerance model.",
    ]
    (args.outdir / "README.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "summary": str(args.outdir / "summary.json")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
