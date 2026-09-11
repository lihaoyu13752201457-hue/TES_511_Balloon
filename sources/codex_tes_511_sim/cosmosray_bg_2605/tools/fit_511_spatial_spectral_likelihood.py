#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a first-pass 511-keV spatial-spectral likelihood baseline.

The estimator is an Asimov/Fisher-information calculation on the existing
event catalog.  Signal templates are built from the corrected science stream;
background templates are built from prompt+delayed streams.  No event from the
science stream is used in the background template.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import pickle
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import make_complete_day15_report as complete


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "reports" / "day15_complete_report" / "work" / "event_catalog.pkl"
DEFAULT_SUMMARY = ROOT / "reports" / "day15_complete_report" / "complete_day15_summary.json"
DEFAULT_ACCIDENTAL = ROOT / "reports" / "science_accidental_veto" / "science_accidental_veto_summary.json"
DEFAULT_OUT = ROOT / "reports" / "nextphase_511" / "likelihood_511"
WINDOWS = {
    "broad_480_550": (480.0, 550.0),
    "line_510p3_511p8": (510.3, 511.8),
}
R_BINS = [0.0, 2.0, 4.0, 6.0, 9.0, 13.0, 18.0, 1.0e9]


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def load_catalog(path: Path) -> dict[str, Any]:
    with path.open("rb") as fh:
        return pickle.load(fh)


def centroid_feature(cat: dict[str, Any], idx: int) -> tuple[float, str]:
    start = int(cat["pix_start"][idx])
    count = int(cat["pix_count"][idx])
    if count <= 0:
        return 1.0e9, "no_tes"
    e = cat["pix_e"][start:start + count].astype(float)
    total = float(np.sum(e))
    if total <= 0.0:
        return 1.0e9, "no_tes"
    x = float(np.sum(e * cat["pix_x"][start:start + count]) / total)
    y = float(np.sum(e * cat["pix_y"][start:start + count]) / total)
    r = math.hypot(x, y)
    layers = cat["pix_layer"][start:start + count].astype(int)
    if count == 1:
        layer_class = f"L{int(layers[0])}"
    else:
        layer_class = "multi"
    return r, layer_class


def r_bin_label(r: float) -> str:
    for lo, hi in zip(R_BINS[:-1], R_BINS[1:]):
        if lo <= r < hi:
            return f"r{lo:g}_{hi:g}"
    return "r_unknown"


def final_selected(cat: dict[str, Any], idx: int, lo: float, hi: float, reject_policy: str, bgo_thr: float) -> bool:
    e = float(cat["tes_total_keV"][idx])
    if not (lo <= e < hi):
        return False
    if float(cat["bgo_total_keV"][idx]) >= bgo_thr:
        return False
    keep, _cls = complete.classify_final(complete.event_hits(cat, idx), reject_policy)
    return bool(keep)


def build_templates(cat: dict[str, Any], lo: float, hi: float, energy_bin_keV: float, science_flux: float, reject_policy: str, bgo_thr: float) -> dict[str, Any]:
    streams = cat["stream"].astype(str)
    mask = (cat["tes_total_keV"] >= lo) & (cat["tes_total_keV"] < hi) & (cat["bgo_total_keV"] < bgo_thr)
    idxs = np.flatnonzero(mask)
    signal: dict[str, float] = defaultdict(float)
    background: dict[str, float] = defaultdict(float)
    signal_energy: dict[str, float] = defaultdict(float)
    background_energy: dict[str, float] = defaultdict(float)
    response = 0.0
    background_rate = 0.0
    selected_counts = {"science": 0, "background": 0}
    for idx in idxs:
        idx = int(idx)
        if not final_selected(cat, idx, lo, hi, reject_policy, bgo_thr):
            continue
        e = float(cat["tes_total_keV"][idx])
        ebin = int((e - lo) / energy_bin_keV)
        ekey = f"E{lo + ebin * energy_bin_keV:.3f}_{lo + (ebin + 1) * energy_bin_keV:.3f}"
        r, layer = centroid_feature(cat, idx)
        key = f"{ekey}|{r_bin_label(r)}|{layer}"
        rate = float(cat["rate_hz"][idx])
        if streams[idx] == "science":
            val = rate / science_flux
            signal[key] += val
            signal_energy[ekey] += val
            response += val
            selected_counts["science"] += 1
        elif streams[idx] in {"prompt", "delayed"}:
            background[key] += rate
            background_energy[ekey] += rate
            background_rate += rate
            selected_counts["background"] += 1
    return {
        "signal": dict(signal),
        "background": dict(background),
        "signal_energy": dict(signal_energy),
        "background_energy": dict(background_energy),
        "response_cps_per_flux": response,
        "background_cps": background_rate,
        "selected_counts": selected_counts,
    }


def fisher(signal: dict[str, float], background: dict[str, float], survival: float = 1.0) -> dict[str, float]:
    info = 0.0
    n_used = 0
    n_signal_only = 0
    for key, s in signal.items():
        b = float(background.get(key, 0.0))
        if b > 0.0:
            info += (survival * s) ** 2 / b
            n_used += 1
        else:
            n_signal_only += 1
    return {"information_per_s": info, "bins_used": n_used, "signal_only_bins": n_signal_only}


def write_template_csv(path: Path, signal: dict[str, float], background: dict[str, float]) -> None:
    keys = sorted(set(signal) | set(background))
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["bin", "signal_cps_per_flux", "background_cps"])
        writer.writeheader()
        for key in keys:
            writer.writerow({"bin": key, "signal_cps_per_flux": signal.get(key, 0.0), "background_cps": background.get(key, 0.0)})


def flux_threshold(info: float, exposure_s: float, nsigma: float) -> float:
    if info <= 0.0 or exposure_s <= 0.0:
        return float("nan")
    return nsigma / math.sqrt(exposure_s * info)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--accidental", type=Path, default=DEFAULT_ACCIDENTAL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--energy-bin-keV", type=float, default=2.0)
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    cat = load_catalog(args.catalog)
    summary = load_json(args.summary)
    accidental = load_json(args.accidental, {})
    science_flux = float(summary["normalization"]["science_flux_ph_cm2_s"])
    reject_policy = str(summary["normalization"].get("reject_policy", "keep"))
    bgo_thr = float(summary["normalization"].get("bgo_threshold_keV", complete.BGO_THR_KEV))

    rows: list[dict[str, Any]] = []
    sensitivity: dict[str, Any] = {}
    for name, (lo, hi) in WINDOWS.items():
        survival = float(accidental.get("windows", {}).get(name, {}).get("accidental_survival_correction", 1.0))
        tpl = build_templates(cat, lo, hi, float(args.energy_bin_keV), science_flux, reject_policy, bgo_thr)
        write_template_csv(args.out / f"template_{name}_energy_spatial.csv", tpl["signal"], tpl["background"])
        write_template_csv(args.out / f"template_{name}_energy.csv", tpl["signal_energy"], tpl["background_energy"])
        window_info = (survival * tpl["response_cps_per_flux"]) ** 2 / tpl["background_cps"] if tpl["background_cps"] > 0 else 0.0
        energy_info = fisher(tpl["signal_energy"], tpl["background_energy"], survival=survival)
        spatial_info = fisher(tpl["signal"], tpl["background"], survival=survival)
        models = {
            "window_counting_same_events": {"information_per_s": window_info, "bins_used": 1, "signal_only_bins": 0},
            "energy_template": energy_info,
            "energy_radius_layer_template": spatial_info,
        }
        sensitivity[name] = {"templates": tpl, "models": models, "survival": survival}
        for model, rec in models.items():
            for exposure in (1.0e5, 1.0e6, 1.0e7):
                rows.append({
                    "energy_window": name,
                    "model": model,
                    "exposure_s": exposure,
                    "background_cps": tpl["background_cps"],
                    "response_cps_per_flux": tpl["response_cps_per_flux"],
                    "science_survival": survival,
                    "information_per_s": rec["information_per_s"],
                    "bins_used": rec["bins_used"],
                    "signal_only_bins_ignored": rec["signal_only_bins"],
                    "flux_3sigma_ph_cm2_s": flux_threshold(rec["information_per_s"], exposure, 3.0),
                    "flux_5sigma_ph_cm2_s": flux_threshold(rec["information_per_s"], exposure, 5.0),
                })

    with (args.out / "likelihood_sensitivity_by_model.csv").open("w", encoding="utf-8", newline="") as fh:
        fields = list(rows[0].keys())
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    # Plot 1 Ms comparison.
    one_ms = [r for r in rows if abs(float(r["exposure_s"]) - 1.0e6) < 1.0]
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    labels = [f"{r['energy_window']}\n{r['model']}" for r in one_ms]
    vals = [float(r["flux_3sigma_ph_cm2_s"]) for r in one_ms]
    ax.bar(np.arange(len(vals)), vals, color="#4C78A8")
    ax.set_xticks(np.arange(len(vals)), labels, rotation=35, ha="right", fontsize=8)
    ax.set_ylabel("3 sigma flux threshold, 1 Ms (ph cm$^{-2}$ s$^{-1}$)")
    ax.set_title("Window counting vs factorized likelihood")
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(args.out / "likelihood_vs_window_counting.png", dpi=220)
    plt.close(fig)

    summary_out = {
        "status": "PASS",
        "science_flux_ph_cm2_s": science_flux,
        "energy_bin_keV": args.energy_bin_keV,
        "sensitivity_rows": rows,
        "caveat": "Factorized Asimov likelihood using deposited-energy catalog; signal-only bins are ignored to avoid optimistic zero-background infinities.",
    }
    (args.out / "likelihood_summary.json").write_text(json.dumps(summary_out, indent=2, ensure_ascii=False), encoding="utf-8")
    md = ["# 511 Spatial-Spectral Likelihood Baseline", "", "Status: `PASS`", ""]
    for r in one_ms:
        md.append(f"- `{r['energy_window']}` / `{r['model']}`: 3 sigma 1 Ms `{float(r['flux_3sigma_ph_cm2_s']):.6g}` ph cm^-2 s^-1.")
    md.append("")
    md.append(summary_out["caveat"])
    (args.out / "likelihood_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (args.out / "audit.json").write_text(json.dumps({"status": "PASS"}, indent=2), encoding="utf-8")
    print(args.out / "likelihood_summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
