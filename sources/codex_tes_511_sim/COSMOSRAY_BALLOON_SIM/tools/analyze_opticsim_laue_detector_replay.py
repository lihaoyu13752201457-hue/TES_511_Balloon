#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze an opticsim-derived Laue focal-plane replay through XZTES/Cosima."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import make_complete_day15_report as complete  # noqa: E402


WINDOWS = {
    "broad_480_550": (480.0, 550.0),
    "line_510p3_511p8": (510.3, 511.8),
}


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))


def open_text(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return path.open("r", encoding="utf-8", errors="ignore")


def parse_replay_catalog(path: Path, exposure_s: float) -> dict[str, Any]:
    cat = complete.empty_catalog()
    cur_id: int | None = None
    bgo_total = 0.0
    pix: dict[str, dict[str, float | int]] = {}
    rate_hz = 1.0 / exposure_s

    def flush() -> None:
        nonlocal cur_id, bgo_total, pix
        if cur_id is not None:
            complete.append_event(
                cat,
                "science",
                "opticsim_laue",
                str(path),
                int(cur_id),
                rate_hz,
                bgo_total,
                pix,
            )
        cur_id = None
        bgo_total = 0.0
        pix = {}

    with open_text(path) as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            if line == "SE":
                flush()
                continue
            m_id = complete.ID_RE.match(line)
            if m_id:
                cur_id = int(m_id.group(1))
                cat["n_generated_events_seen"] += 1
                continue
            if not line.startswith("CC HIT "):
                continue
            hit = complete.parse_cc_hit(line)
            if hit is None:
                continue
            vol, edep, x, y, z = hit
            m_tp = complete.TP_RE.match(vol)
            if m_tp:
                layer = int(m_tp.group("layer"))
                rec = pix.setdefault(vol, {"e": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0, "layer": layer})
                rec["e"] = float(rec["e"]) + edep
                rec["wx"] = float(rec["wx"]) + edep * x
                rec["wy"] = float(rec["wy"]) + edep * y
                rec["wz"] = float(rec["wz"]) + edep * z
            elif "BGO" in vol.upper():
                bgo_total += edep
    flush()
    return cat


def classify_window(cat: dict[str, Any], lo: float, hi: float, reject_policy: str) -> dict[str, Any]:
    out = {
        "raw_count": 0,
        "bgo_pass_count": 0,
        "final_count": 0,
        "single_pixel_final_count": 0,
        "multi_pixel_bgo_pass_count": 0,
        "bgo_veto_count": 0,
        "compton_class_counts": Counter(),
    }
    for idx, energy in enumerate(cat["tes_total_keV"]):
        e = float(energy)
        if not (lo <= e < hi):
            continue
        out["raw_count"] += 1
        if float(cat["bgo_total_keV"][idx]) >= complete.BGO_THR_KEV:
            out["bgo_veto_count"] += 1
            continue
        out["bgo_pass_count"] += 1
        if int(cat["pix_count"][idx]) > 1:
            out["multi_pixel_bgo_pass_count"] += 1
        keep, cls = complete.classify_final(complete.event_hits(cat, idx), reject_policy)
        out["compton_class_counts"][cls] += 1
        if keep:
            out["final_count"] += 1
            if int(cat["pix_count"][idx]) == 1:
                out["single_pixel_final_count"] += 1
    out["compton_class_counts"] = dict(out["compton_class_counts"])
    return out


def read_ring_area_cm2(path: Path) -> tuple[float, list[dict[str, str]]]:
    rows: list[dict[str, str]]
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    area_mm2 = sum(float(r["n_tiles"]) * float(r["tile_size_mm"]) ** 2 for r in rows)
    return area_mm2 / 100.0, rows


def eventlist_time_stats(path: Path) -> dict[str, float | int]:
    times = []
    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            parts = line.split()
            if len(parts) >= 5:
                times.append(float(parts[4]))
    arr = np.asarray(times, dtype=float)
    if len(arr) <= 1:
        return {"n_times": int(len(arr))}
    gaps = np.diff(np.sort(arr))
    return {
        "n_times": int(len(arr)),
        "time_min_s": float(np.min(arr)),
        "time_max_s": float(np.max(arr)),
        "gap_mean_s": float(np.mean(gaps)),
        "gap_median_s": float(np.median(gaps)),
        "gap_p05_s": float(np.quantile(gaps, 0.05)),
        "gap_p95_s": float(np.quantile(gaps, 0.95)),
    }


def write_spectrum(
    cat: dict[str, Any],
    out_csv: Path,
    out_png: Path,
    *,
    title: str = "Opticsim Laue focal-plane replay through XZTES",
) -> None:
    bins = np.arange(450.0, 581.0, 1.0)
    raw = np.zeros(len(bins) - 1, dtype=int)
    bgo = np.zeros(len(bins) - 1, dtype=int)
    final = np.zeros(len(bins) - 1, dtype=int)
    for idx, energy in enumerate(cat["tes_total_keV"]):
        e = float(energy)
        k = int(math.floor(e - 450.0))
        if not (0 <= k < len(raw)):
            continue
        raw[k] += 1
        if float(cat["bgo_total_keV"][idx]) < complete.BGO_THR_KEV:
            bgo[k] += 1
            keep, _ = complete.classify_final(complete.event_hits(cat, idx), "keep")
            if keep:
                final[k] += 1
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(["energy_lo_keV", "energy_hi_keV", "raw_count", "bgo_pass_count", "final_count"])
        for i in range(len(raw)):
            writer.writerow([bins[i], bins[i + 1], int(raw[i]), int(bgo[i]), int(final[i])])

    centers = 0.5 * (bins[:-1] + bins[1:])
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    ax.step(centers, raw, where="mid", lw=1.2, label="raw TES")
    ax.step(centers, bgo, where="mid", lw=1.2, label="BGO pass")
    ax.step(centers, final, where="mid", lw=1.2, label="BGO + Compton/FoV")
    ax.axvspan(480.0, 550.0, color="#d1d5db", alpha=0.25, label="480-550 keV")
    ax.set_xlabel("TES total energy (keV)")
    ax.set_ylabel("events per 1 keV bin")
    ax.set_title(title)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_png, dpi=220)
    plt.close(fig)


def write_ring_plot(per_ring_path: Path, out_png: Path) -> None:
    rows = load_json(per_ring_path, [])
    if not rows:
        return
    labels = [str(r["design_energy_keV"]) for r in rows]
    diff = np.asarray([float(r["n_diffracted"]) / float(r["n_primaries"]) for r in rows])
    abs_ = np.asarray([float(r["n_absorbed"]) / float(r["n_primaries"]) for r in rows])
    trans = np.asarray([float(r["n_transmitted"]) / float(r["n_primaries"]) for r in rows])
    x = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    ax.bar(x, diff, label="diffract")
    ax.bar(x, abs_, bottom=diff, label="absorb")
    ax.bar(x, trans, bottom=diff + abs_, label="transmit")
    ax.set_xticks(x, labels)
    ax.set_xlabel("ring design energy (keV)")
    ax.set_ylabel("fraction")
    ax.set_ylim(0, 1)
    ax.set_title("Laue Ge(111) per-ring outcomes")
    ax.legend(fontsize=8, ncol=3)
    fig.tight_layout()
    fig.savefig(out_png, dpi=220)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--laue-summary", type=Path, required=True)
    ap.add_argument("--per-ring", type=Path, required=True)
    ap.add_argument("--ring-config", type=Path, required=True)
    ap.add_argument("--outdir", type=Path, default=ROOT / "reports_260516" / "opticsim_laue_replay_20260521")
    ap.add_argument("--background-cps", type=float, default=5.765235221601166)
    ap.add_argument("--reject-policy", default="keep")
    args = ap.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    manifest = load_json(args.manifest, {})
    laue = load_json(args.laue_summary, {})
    exposure_s = float(manifest.get("coordinate_policy", {}).get("duration_s") or 1800.0)
    n_primaries = int(laue["n_primaries"])
    n_diffracted = int(laue["n_diffracted"])
    area_cm2, _ring_rows = read_ring_area_cm2(args.ring_config)
    cat = parse_replay_catalog(args.sim, exposure_s)
    windows = {name: classify_window(cat, lo, hi, args.reject_policy) for name, (lo, hi) in WINDOWS.items()}

    for win in windows.values():
        for key in ("raw_count", "bgo_pass_count", "final_count"):
            win[f"{key.replace('_count', '')}_rate_hz_replay"] = float(win[key]) / exposure_s
        win["detector_final_survival_per_diffracted"] = float(win["final_count"]) / max(n_diffracted, 1)
        win["end_to_end_final_survival_per_laue_primary"] = float(win["final_count"]) / max(n_primaries, 1)
        win["geometric_area_response_cm2"] = area_cm2 * win["end_to_end_final_survival_per_laue_primary"]
        # Backward-compatible key for reports generated before the CAM511-scale
        # geometry pass.
        win["demo_tile_area_response_cm2"] = win["geometric_area_response_cm2"]
        response = float(win["geometric_area_response_cm2"])
        win["T3_days_for_flux_1e_minus_4_geometric_area"] = (
            (3.0 * math.sqrt(args.background_cps) / (1.0e-4 * response)) ** 2 / 86400.0
            if response > 0
            else float("inf")
        )
        win["T3_days_for_flux_1e_minus_4_demo_area"] = win["T3_days_for_flux_1e_minus_4_geometric_area"]

    write_spectrum(cat, args.outdir / "laue_detector_energy_spectrum.csv", args.outdir / "laue_detector_energy_spectrum.png")
    write_ring_plot(args.per_ring, args.outdir / "laue_per_ring_outcomes.png")
    timing = eventlist_time_stats(Path(manifest["event_list"]))
    summary = {
        "status": "PASS",
        "claim_level": "OPTICSIM_LAUE_RERUN_DETECTOR_REPLAY",
        "sim": str(args.sim),
        "manifest": str(args.manifest),
        "laue_summary": str(args.laue_summary),
        "exposure_s": exposure_s,
        "eventlist_timing": timing,
        "laue": laue,
        "ring_tile_geometric_area_cm2": area_cm2,
        "ring_tile_geometric_area_cm2_demo": area_cm2,
        "estimated_laue_optics_effective_area_cm2": area_cm2 * float(laue.get("diffraction_fraction", 0.0)),
        "detector_catalog": {
            "generated_events_seen": int(cat["n_generated_events_seen"]),
            "events_with_tes_or_bgo": int(len(cat["stream"])),
            "events_with_tes": int(sum(float(e) > 0.0 for e in cat["tes_total_keV"])),
            "events_with_bgo": int(sum(float(e) > 0.0 for e in cat["bgo_total_keV"])),
        },
        "windows": windows,
        "figures": [
            str(args.outdir / "laue_detector_energy_spectrum.png"),
            str(args.outdir / "laue_per_ring_outcomes.png"),
        ],
        "limitations": [
            "This is a rerun of the current opticsim Ge(111) Laue multiring scaffold and XZTES detector replay.",
            "The flux response is normalized by the ring crystal geometric area in the supplied ring config; the claim level depends on whether that config is a demo or a mission-scale design.",
            "Background cps is imported from the current detector prompt+delayed ledger; full simultaneous prompt/delayed/science Cosima transport is still represented by the existing common-timeline tools.",
        ],
    }
    (args.outdir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    broad = windows["broad_480_550"]
    line = windows["line_510p3_511p8"]
    md = [
        "# Opticsim Laue detector replay rerun 2026-05-21",
        "",
        "This run replaces the old parameterized science-source authority for this check with a freshly rerun opticsim Laue phase-space source.",
        "",
        "## Rerun chain",
        "",
        f"- Geant4 Laue primaries: `{n_primaries}`",
        f"- Diffracted focal-plane photons: `{n_diffracted}` (`{float(laue['diffraction_fraction']):.5f}`)",
        f"- Focal spot D90: `{float(laue['spot_d90_cm']):.4f} cm`",
        f"- Cosima replay duration: `{exposure_s:.2f} s`, EventList timing policy: `poisson_duration`",
        f"- Detector replay generated particles: `{cat['n_generated_events_seen']}`",
        "",
        "## Detector selection",
        "",
        "| window | raw | BGO pass | final | detector final / diffracted | end-to-end final / Laue primary |",
        "|---|---:|---:|---:|---:|---:|",
        f"| 480-550 keV | {broad['raw_count']} | {broad['bgo_pass_count']} | {broad['final_count']} | {broad['detector_final_survival_per_diffracted']:.6g} | {broad['end_to_end_final_survival_per_laue_primary']:.6g} |",
        f"| 510.3-511.8 keV | {line['raw_count']} | {line['bgo_pass_count']} | {line['final_count']} | {line['detector_final_survival_per_diffracted']:.6g} | {line['end_to_end_final_survival_per_laue_primary']:.6g} |",
        "",
        "## Normalization note",
        "",
        f"The ring crystal geometric area is `{area_cm2:.6g} cm2`; therefore the broad-window geometric-area final response is `{broad['geometric_area_response_cm2']:.6g} cps/(ph cm-2 s-1)` before atmospheric/visibility scaling.",
        f"Using the current detector background `{args.background_cps:.6g} cps`, the 1e-4 ph cm-2 s-1 broad-window T3 is `{broad['T3_days_for_flux_1e_minus_4_geometric_area']:.6g} d`.",
        "",
        "This number is still scaffold-level unless the ring config is explicitly a mission-scale collecting-area design with an off-axis response matrix.",
    ]
    (args.outdir / "README.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
