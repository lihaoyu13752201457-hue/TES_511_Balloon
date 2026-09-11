#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gate B detector-response post-processing for the day-15 event catalog.

The script applies a controlled energy response to the cached event catalog:
TES energy is smeared per pixel before event summing, while BGO is currently
smeared at the stored event-total level because the day-15 catalog does not
retain per-BGO-hit records.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import pickle
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from make_day15_report import EventHit, classify_compton  # noqa: E402

DEFAULT_CONFIG = ROOT / "configs" / "nextphase" / "detector_response.yaml"
DEFAULT_CATALOG = ROOT / "reports" / "day15_complete_report" / "work" / "event_catalog.pkl"
DEFAULT_OUT = ROOT / "reports" / "nextphase_511" / "gate_B_detector_response"
FWHM_TO_SIGMA = 1.0 / 2.3548200450309493


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def axis(emin: float, emax: float, binw: float) -> tuple[np.ndarray, np.ndarray]:
    edges = np.arange(emin, emax + 0.5 * binw, binw)
    return edges, 0.5 * (edges[:-1] + edges[1:])


def load_catalog(path: Path) -> dict[str, Any]:
    with path.open("rb") as fh:
        return pickle.load(fh)


def event_index_for_pixels(pix_count: np.ndarray) -> np.ndarray:
    return np.repeat(np.arange(len(pix_count), dtype=np.int64), pix_count.astype(np.int64))


def apply_response(cat: dict[str, Any], cfg: dict[str, Any], disable: bool = False) -> dict[str, np.ndarray]:
    n_events = len(cat["stream"])
    if disable:
        return {
            "pix_e_meas": cat["pix_e"].astype(np.float64).copy(),
            "tes_total_meas": cat["tes_total_keV"].astype(np.float64).copy(),
            "bgo_total_meas": cat["bgo_total_keV"].astype(np.float64).copy(),
        }
    rng = np.random.default_rng(int(cfg.get("random_seed", 2605511)))
    tes = cfg["TES"]
    bgo = cfg["BGO"]
    sigma_tes = float(tes["fwhm_keV"]) * FWHM_TO_SIGMA
    sigma_bgo = float(bgo["fwhm_keV"]) * FWHM_TO_SIGMA

    pix_true = cat["pix_e"].astype(np.float64)
    pix_meas = pix_true + rng.normal(0.0, sigma_tes, size=len(pix_true))
    if not bool(tes.get("allow_negative_after_noise", False)):
        pix_meas = np.maximum(pix_meas, 0.0)
    pix_meas = np.where(pix_meas >= float(tes["threshold_keV"]), pix_meas, 0.0)

    tes_total = np.zeros(n_events, dtype=np.float64)
    pix_event = event_index_for_pixels(cat["pix_count"])
    np.add.at(tes_total, pix_event, pix_meas)

    bgo_true = cat["bgo_total_keV"].astype(np.float64)
    bgo_meas = bgo_true.copy()
    nonzero = bgo_true > 0
    bgo_meas[nonzero] = bgo_true[nonzero] + rng.normal(0.0, sigma_bgo, size=int(np.sum(nonzero)))
    if not bool(bgo.get("allow_negative_after_noise", False)):
        bgo_meas = np.maximum(bgo_meas, 0.0)
    bgo_meas = np.where(bgo_meas >= float(bgo["threshold_keV"]), bgo_meas, 0.0)

    return {"pix_e_meas": pix_meas, "tes_total_meas": tes_total, "bgo_total_meas": bgo_meas}


def hits_for_event(cat: dict[str, Any], meas: dict[str, np.ndarray], idx: int, measured: bool) -> list[EventHit]:
    start = int(cat["pix_start"][idx])
    count = int(cat["pix_count"][idx])
    hits: list[EventHit] = []
    earr = meas["pix_e_meas"] if measured else cat["pix_e"]
    for j in range(start, start + count):
        e = float(earr[j])
        if e <= 0:
            continue
        hits.append(
            EventHit(
                x=float(cat["pix_x"][j]),
                y=float(cat["pix_y"][j]),
                z=float(cat["pix_z"][j]),
                e=e,
                pixel_uid=str(cat["pix_uid"][j]),
                layer=int(cat["pix_layer"][j]),
            )
        )
    return hits


def final_keep(hits: list[EventHit]) -> bool:
    if len(hits) <= 0:
        return False
    if len(hits) == 1:
        return True
    cls = classify_compton(hits, "keep")
    return cls in ("single", "keep", "reject_kept")


def rates_for_window(cat: dict[str, Any], meas: dict[str, np.ndarray], lo: float, hi: float, measured: bool, bgo_thr: float) -> dict[str, Any]:
    e_total = meas["tes_total_meas"] if measured else cat["tes_total_keV"]
    bgo_total = meas["bgo_total_meas"] if measured else cat["bgo_total_keV"]
    raw_mask = (e_total >= lo) & (e_total < hi)
    bgo_mask = raw_mask & (bgo_total < bgo_thr)
    final_rate = 0.0
    final_by_stream: dict[str, float] = defaultdict(float)
    final_n = 0
    for idx in np.flatnonzero(bgo_mask):
        hits = hits_for_event(cat, meas, int(idx), measured)
        if final_keep(hits):
            rate = float(cat["rate_hz"][idx])
            final_rate += rate
            final_by_stream[str(cat["stream"][idx])] += rate
            final_n += 1
    out = {
        "raw_cps": float(np.sum(cat["rate_hz"][raw_mask])),
        "bgo_cps": float(np.sum(cat["rate_hz"][bgo_mask])),
        "final_cps": float(final_rate),
        "raw_events": int(np.sum(raw_mask)),
        "bgo_events": int(np.sum(bgo_mask)),
        "final_events": int(final_n),
        "final_by_stream_cps": dict(final_by_stream),
    }
    return out


def weighted_hist(e: np.ndarray, w: np.ndarray, edges: np.ndarray) -> np.ndarray:
    return np.histogram(e, bins=edges, weights=w)[0]


def fwhm_from_samples(samples: np.ndarray) -> float | None:
    if len(samples) < 10:
        return None
    p16, p84 = np.percentile(samples, [15.865, 84.135])
    sigma = 0.5 * (p84 - p16)
    return float(2.3548200450309493 * sigma)


def write_rates_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = ["energy_window_keV", "energy_type", "raw_cps", "bgo_cps", "final_cps", "raw_events", "bgo_events", "final_events", "science_final_cps", "background_final_cps"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--disable-detector-response", action="store_true")
    args = ap.parse_args()

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    cfg = load_json(args.config)
    cat = load_catalog(args.catalog)
    meas = apply_response(cat, cfg, disable=args.disable_detector_response)
    bgo_thr = float(cfg["BGO"]["veto_threshold_keV"])

    windows = [(480.0, 550.0), (510.3, 511.8)]
    rows = []
    summary_windows: dict[str, Any] = {}
    for lo, hi in windows:
        label = f"{lo:g}-{hi:g}"
        for measured in (False, True):
            rate = rates_for_window(cat, meas, lo, hi, measured=measured, bgo_thr=bgo_thr)
            stream = rate["final_by_stream_cps"]
            row = {
                "energy_window_keV": label,
                "energy_type": "measured" if measured else "true",
                **rate,
                "science_final_cps": stream.get("science", 0.0),
                "background_final_cps": stream.get("prompt", 0.0) + stream.get("delayed", 0.0),
            }
            rows.append(row)
            summary_windows[f"{label}_{'measured' if measured else 'true'}"] = row
    write_rates_csv(out / "detector_response_component_rates.csv", rows)

    stream = cat["stream"].astype(str)
    science = stream == "science"
    true_sci = cat["tes_total_keV"][science]
    meas_sci = meas["tes_total_meas"][science]
    science_band = (true_sci > 450.0) & (true_sci < 570.0)
    measured_band = (meas_sci > 450.0) & (meas_sci < 570.0)

    # Spectra for all events, weighted by their rates, in the two diagnostic bands.
    for lo, hi, binw, name in ((480.0, 550.0, 0.25, "spectrum_480_550_true_vs_measured.png"), (510.0, 515.0, 0.02, "spectrum_510_515_true_vs_measured.png")):
        edges, centers = axis(lo, hi, binw)
        plt.figure(figsize=(8.2, 5.2))
        plt.step(centers, weighted_hist(cat["tes_total_keV"], cat["rate_hz"], edges), where="mid", label="true deposited energy", lw=1.3)
        plt.step(centers, weighted_hist(meas["tes_total_meas"], cat["rate_hz"], edges), where="mid", label="measured energy", lw=1.3)
        plt.yscale("log")
        plt.xlabel("TES event-summed energy (keV)")
        plt.ylabel("Direct-expectation rate (cps/bin)")
        plt.title(f"Detector response check: {lo:g}-{hi:g} keV")
        plt.grid(True, which="both", alpha=0.25)
        plt.legend()
        plt.tight_layout()
        plt.savefig(out / name, dpi=180)
        plt.close()

    sci_true_fwhm = fwhm_from_samples(true_sci[science_band])
    sci_meas_fwhm = fwhm_from_samples(meas_sci[measured_band])
    if args.disable_detector_response:
        passed = all(
            abs(summary_windows[f"{label}_true"]["final_cps"] - summary_windows[f"{label}_measured"]["final_cps"]) < 1.0e-12
            for label in ("480-550", "510.3-511.8")
        )
    else:
        passed = bool(sci_meas_fwhm is not None and sci_meas_fwhm > 0.05)

    summary = {
        "gate": "B_detector_response",
        "passed": passed,
        "catalog": str(args.catalog),
        "config": str(args.config),
        "detector_response_disabled": bool(args.disable_detector_response),
        "tes_response": cfg["TES"],
        "bgo_response": cfg["BGO"],
        "known_limitation": "BGO response is applied to stored event-total BGO energy because event_catalog.pkl does not retain per-BGO-hit records.",
        "science_peak_true_fwhm_robust_keV": sci_true_fwhm,
        "science_peak_measured_fwhm_robust_keV": sci_meas_fwhm,
        "n_science_events_for_true_width": int(np.sum(science_band)),
        "n_science_events_for_measured_width": int(np.sum(measured_band)),
        "windows": summary_windows,
    }
    (out / "detector_response_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    decision = "PASS" if summary["passed"] else "FAIL"
    md = f"""# Gate B detector-response result

**Decision:** `{decision}`

TES response is applied per pixel, then pixel measured energies are summed at
event level. BGO response is applied to the stored event-total BGO energy in
this first gate because the current catalog does not store per-BGO-hit records.

## Science peak width

- true-energy robust FWHM: `{sci_true_fwhm}`
- measured-energy robust FWHM: `{sci_meas_fwhm}`

## Outputs

- `detector_response_summary.json`
- `detector_response_component_rates.csv`
- `spectrum_480_550_true_vs_measured.png`
- `spectrum_510_515_true_vs_measured.png`
"""
    (out / "gate_B_result.md").write_text(md, encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
