#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scan coincidence-window systematics for the 511-keV analysis.

The production day-15 report uses one finite Poisson time-axis realization at
1 us.  This script estimates the window dependence with higher-statistics
cluster bootstraps from the same audited event catalog:

* background-only clusters: candidate starts occur at rate lambda exp(-lambda tau)
  and the forward cluster size follows the same rolling-gap rule as the
  production merge;
* science-centered accidental loss: unrelated prompt/delayed events connected
  to the science time on either side are sampled with the same geometric gap
  model used in ``estimate_science_accidental_veto.py``.

The scan is intentionally a timing-systematic estimator.  It does not rerun
Cosima and it uses the current baseline deposited-energy catalog so the 1 us
row can be compared to the existing accidental-veto correction.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import pickle
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import make_complete_day15_report as complete


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
DEFAULT_CONFIG = ROOT / "configs" / "nextphase" / "timing_windows.yaml"
DEFAULT_CATALOG = ROOT / "reports" / "day15_complete_report" / "work" / "event_catalog.pkl"
DEFAULT_SUMMARY = ROOT / "reports" / "day15_complete_report" / "complete_day15_summary.json"
DEFAULT_ACCIDENTAL = ROOT / "reports" / "science_accidental_veto" / "science_accidental_veto_summary.json"
DEFAULT_OUT = ROOT / "reports" / "nextphase_511" / "timing_window_scan"
WINDOWS = {
    "broad_480_550": (480.0, 550.0),
    "line_510p3_511p8": (510.3, 511.8),
}


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def load_catalog(path: Path) -> dict[str, Any]:
    with path.open("rb") as fh:
        return pickle.load(fh)


def classify_candidate(cat: dict[str, Any], event_indices: np.ndarray, lo: float, hi: float, reject_policy: str, bgo_thr: float) -> tuple[bool, str]:
    energy = float(np.sum(cat["tes_total_keV"][event_indices]))
    if not (lo <= energy < hi):
        return False, "energy_out"
    bgo = float(np.sum(cat["bgo_total_keV"][event_indices]))
    if bgo >= bgo_thr:
        return False, "bgo_veto"
    hits = complete.aggregate_candidate_hits(cat, event_indices.astype(np.int64))
    keep, cls = complete.classify_final(hits, reject_policy)
    return bool(keep), ("kept" if keep else f"compton_{cls}")


def classify_single_event(cat: dict[str, Any], idx: int, lo: float, hi: float, reject_policy: str, bgo_thr: float) -> tuple[bool, str]:
    e = float(cat["tes_total_keV"][idx])
    if not (lo <= e < hi):
        return False, "energy_out"
    if float(cat["bgo_total_keV"][idx]) >= bgo_thr:
        return False, "bgo_veto"
    keep, cls = complete.classify_final(complete.event_hits(cat, idx), reject_policy)
    return bool(keep), ("kept" if keep else f"compton_{cls}")


def binom_err(p: float, n: int) -> float:
    if n <= 0 or not math.isfinite(p):
        return float("nan")
    return math.sqrt(max(p * (1.0 - p), 0.0) / n)


def precompute_isolated_science(cat: dict[str, Any], science_idx: np.ndarray, reject_policy: str, bgo_thr: float) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    energy = cat["tes_total_keV"][science_idx].astype(float)
    bgo = cat["bgo_total_keV"][science_idx].astype(float)
    pix_count = cat["pix_count"][science_idx].astype(int)
    for name, (lo, hi) in WINDOWS.items():
        flags = np.zeros(len(science_idx), dtype=bool)
        causes = Counter()
        in_energy = (energy >= lo) & (energy < hi)
        in_bgo = bgo < bgo_thr
        fast_energy = ~in_energy
        fast_bgo = in_energy & ~in_bgo
        fast_single = in_energy & in_bgo & (pix_count == 1)
        flags[fast_single] = True
        causes["energy_out"] += int(np.sum(fast_energy))
        causes["bgo_veto"] += int(np.sum(fast_bgo))
        causes["kept"] += int(np.sum(fast_single))
        needs_compton = np.flatnonzero(in_energy & in_bgo & (pix_count != 1))
        for pos in needs_compton:
            idx = int(science_idx[pos])
            if pix_count[pos] <= 0:
                keep, cause = False, "no_tes"
            else:
                keep, cls = complete.classify_final(complete.event_hits(cat, idx), reject_policy)
                cause = "kept" if keep else f"compton_{cls}"
            flags[pos] = keep
            causes[cause] += 1
        out[name] = {"flags": flags, "causes": dict(causes)}
    return out


def sample_cluster_choices(rng: np.random.Generator, choices: np.ndarray, probs: np.ndarray, counts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    total = int(np.sum(counts))
    if total <= 0:
        return np.empty(0, dtype=np.int64), np.concatenate(([0], np.cumsum(counts, dtype=np.int64)))
    draw = rng.choice(choices, size=total, replace=True, p=probs)
    offsets = np.concatenate(([0], np.cumsum(counts, dtype=np.int64)))
    return draw.astype(np.int64), offsets


def background_cluster_scan(
    cat: dict[str, Any],
    bg_idx: np.ndarray,
    bg_prob: np.ndarray,
    bg_total_rate: float,
    tau_s: float,
    n_trials: int,
    rng: np.random.Generator,
    reject_policy: str,
    bgo_thr: float,
) -> dict[str, Any]:
    p_stop = math.exp(-bg_total_rate * tau_s)
    # Candidate starts are events with a quiet interval before them.
    cluster_start_rate = bg_total_rate * p_stop
    extra_counts = rng.geometric(p_stop, size=n_trials) - 1
    first = rng.choice(bg_idx, size=n_trials, replace=True, p=bg_prob)
    extra, offsets = sample_cluster_choices(rng, bg_idx, bg_prob, extra_counts.astype(np.int64))

    result: dict[str, Any] = {
        "cluster_start_rate_hz": float(cluster_start_rate),
        "mean_cluster_size_model": float(1.0 / p_stop),
        "sampled_cluster_size_mean": float(1.0 + np.mean(extra_counts)),
        "sampled_cluster_size_counts": {str(int(k) + 1): int(v) for k, v in sorted(Counter(extra_counts.tolist()).items())},
        "windows": {},
    }

    for name, (lo, hi) in WINDOWS.items():
        kept = 0
        causes = Counter()
        for trial in range(n_trials):
            start = int(offsets[trial])
            end = int(offsets[trial + 1])
            if end > start:
                ev = np.concatenate(([first[trial]], extra[start:end])).astype(np.int64)
                keep, cause = classify_candidate(cat, ev, lo, hi, reject_policy, bgo_thr)
            else:
                keep, cause = classify_single_event(cat, int(first[trial]), lo, hi, reject_policy, bgo_thr)
            if keep:
                kept += 1
            causes[cause] += 1
        p_keep = kept / n_trials
        result["windows"][name] = {
            "kept_clusters": int(kept),
            "keep_fraction_per_cluster": float(p_keep),
            "keep_fraction_1sigma": binom_err(p_keep, n_trials),
            "final_background_cps": float(cluster_start_rate * p_keep),
            "loss_or_reject_causes": dict(causes),
        }
    return result


def science_survival_scan(
    cat: dict[str, Any],
    science_idx: np.ndarray,
    science_prob: np.ndarray,
    isolated: dict[str, dict[str, Any]],
    bg_idx: np.ndarray,
    bg_prob: np.ndarray,
    bg_total_rate: float,
    tau_s: float,
    n_trials: int,
    rng: np.random.Generator,
    reject_policy: str,
    bgo_thr: float,
) -> dict[str, Any]:
    p_stop = math.exp(-bg_total_rate * tau_s)
    left = rng.geometric(p_stop, size=n_trials) - 1
    right = rng.geometric(p_stop, size=n_trials) - 1
    bg_counts = (left + right).astype(np.int64)
    bg_draws, offsets = sample_cluster_choices(rng, bg_idx, bg_prob, bg_counts)
    sci_pos = rng.choice(np.arange(len(science_idx)), size=n_trials, replace=True, p=science_prob)
    sci_choice = science_idx[sci_pos]

    result: dict[str, Any] = {
        "p_any_background_model": float(1.0 - p_stop * p_stop),
        "mean_connected_background_events_model": float(2.0 * (1.0 / p_stop - 1.0)),
        "sampled_trials_with_background": int(np.sum(bg_counts > 0)),
        "sampled_connected_background_mean": float(np.mean(bg_counts)),
        "sampled_background_draws": int(np.sum(bg_counts)),
        "windows": {},
    }
    mixed_trials = np.flatnonzero(bg_counts > 0)
    for name, (lo, hi) in WINDOWS.items():
        base_flags = isolated[name]["flags"][sci_pos]
        base_selected = int(np.sum(base_flags))
        survived = int(np.sum(base_flags & (bg_counts == 0)))
        loss_causes = Counter()
        selected_with_bg = int(np.sum(base_flags & (bg_counts > 0)))
        for trial in mixed_trials:
            if not base_flags[trial]:
                continue
            start = int(offsets[trial])
            end = int(offsets[trial + 1])
            ev = np.concatenate(([sci_choice[trial]], bg_draws[start:end])).astype(np.int64)
            keep, cause = classify_candidate(cat, ev, lo, hi, reject_policy, bgo_thr)
            if keep:
                survived += 1
            else:
                loss_causes[cause] += 1
        lost = base_selected - survived
        loss = lost / base_selected if base_selected else float("nan")
        survival = survived / base_selected if base_selected else float("nan")
        conditional = lost / selected_with_bg if selected_with_bg else float("nan")
        result["windows"][name] = {
            "base_selected_trials": base_selected,
            "base_selected_fraction": float(base_selected / n_trials),
            "selected_with_background": selected_with_bg,
            "survived_trials": int(survived),
            "lost_trials": int(lost),
            "accidental_loss_fraction_all_selected": float(loss),
            "accidental_survival_correction": float(survival),
            "loss_fraction_1sigma": binom_err(loss, base_selected),
            "conditional_loss_given_background": float(conditional),
            "loss_causes": dict(loss_causes),
        }
    return result


def run_scan(cat: dict[str, Any], cfg: dict[str, Any], summary: dict[str, Any], n_trials: int, seed: int) -> dict[str, Any]:
    streams = cat["stream"].astype(str)
    bg_idx = np.flatnonzero((streams == "prompt") | (streams == "delayed"))
    science_idx = np.flatnonzero(streams == "science")
    if len(bg_idx) == 0 or len(science_idx) == 0:
        raise RuntimeError("catalog must contain prompt/delayed background and science streams")
    bg_rates = cat["rate_hz"][bg_idx].astype(float)
    sci_rates = cat["rate_hz"][science_idx].astype(float)
    bg_prob = bg_rates / np.sum(bg_rates)
    sci_prob = sci_rates / np.sum(sci_rates)
    bg_total_rate = float(np.sum(bg_rates))
    reject_policy = str(cfg.get("policies", {}).get("reject_policy", summary["normalization"].get("reject_policy", "keep")))
    bgo_thr = float(cfg.get("policies", {}).get("bgo_threshold_keV", summary["normalization"].get("bgo_threshold_keV", complete.BGO_THR_KEV)))
    rng = np.random.default_rng(seed)
    isolated = precompute_isolated_science(cat, science_idx, reject_policy, bgo_thr)

    rows = []
    scan = {
        "status": "PASS",
        "seed": int(seed),
        "n_trials_per_window": int(n_trials),
        "input_catalog": str(DEFAULT_CATALOG.relative_to(WORKSPACE)),
        "input_summary": str(DEFAULT_SUMMARY.relative_to(WORKSPACE)),
        "reject_policy": reject_policy,
        "bgo_threshold_keV": bgo_thr,
        "background_total_rate_hz": bg_total_rate,
        "windows_us": [float(x) for x in cfg["windows_us"]],
        "energy_windows": {k: list(v) for k, v in WINDOWS.items()},
        "scan": {},
        "baseline_1us_reference": load_json(DEFAULT_ACCIDENTAL, {}),
    }
    bkg = summary["science_sensitivity"]["background_final_cps_prompt_plus_delayed"]
    response = summary["science_sensitivity"]["science_final_response_cps_per_ph_cm-2_s-1"]

    for window_us in scan["windows_us"]:
        tau_s = float(window_us) * 1.0e-6
        bg_result = background_cluster_scan(cat, bg_idx, bg_prob, bg_total_rate, tau_s, n_trials, rng, reject_policy, bgo_thr)
        sci_result = science_survival_scan(cat, science_idx, sci_prob, isolated, bg_idx, bg_prob, bg_total_rate, tau_s, n_trials, rng, reject_policy, bgo_thr)
        scan["scan"][str(window_us)] = {"tau_s": tau_s, "background": bg_result, "science": sci_result}
        for name in WINDOWS:
            bg_cps = bg_result["windows"][name]["final_background_cps"]
            survival = sci_result["windows"][name]["accidental_survival_correction"]
            # For broad window use the current broad response/background.  For
            # line row the response is not in the complete summary, so report
            # the timing correction and background rate; the final report will
            # use existing line-window response from the review packet if present.
            if name == "broad_480_550" and response > 0.0 and survival > 0.0:
                flux3 = 3.0 * math.sqrt(max(bg_cps, 0.0) * 1.0e6) / (response * survival * 1.0e6)
            else:
                flux3 = float("nan")
            rows.append({
                "window_us": window_us,
                "energy_window": name,
                "p_any_science_background": sci_result["p_any_background_model"],
                "mean_connected_background_science": sci_result["mean_connected_background_events_model"],
                "background_cluster_start_rate_hz": bg_result["cluster_start_rate_hz"],
                "background_final_cps": bg_cps,
                "science_survival": survival,
                "science_loss_fraction": sci_result["windows"][name]["accidental_loss_fraction_all_selected"],
                "science_loss_1sigma": sci_result["windows"][name]["loss_fraction_1sigma"],
                "broad_flux3_1Ms_if_applicable": flux3,
                "dominant_science_loss_causes": json.dumps(sci_result["windows"][name]["loss_causes"], sort_keys=True),
            })
    scan["rows"] = rows
    return scan


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "window_us", "energy_window", "p_any_science_background", "mean_connected_background_science",
        "background_cluster_start_rate_hz", "background_final_cps", "science_survival",
        "science_loss_fraction", "science_loss_1sigma", "broad_flux3_1Ms_if_applicable",
        "dominant_science_loss_causes",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def plot_outputs(result: dict[str, Any], outdir: Path) -> dict[str, str]:
    rows = result["rows"]
    out: dict[str, str] = {}
    labels = {"broad_480_550": "480-550 keV", "line_510p3_511p8": "510.3-511.8 keV"}
    for key, ylabel, filename in [
        ("background_final_cps", "Background final rate (cps)", "background_rate_vs_window.png"),
        ("science_survival", "Science accidental survival", "science_survival_vs_window.png"),
    ]:
        fig, ax = plt.subplots(figsize=(7.2, 4.8))
        for name in WINDOWS:
            rr = [r for r in rows if r["energy_window"] == name]
            ax.plot([r["window_us"] for r in rr], [r[key] for r in rr], marker="o", label=labels[name])
        ax.set_xscale("log")
        ax.set_xlabel("Coincidence window (us)")
        ax.set_ylabel(ylabel)
        ax.grid(True, which="both", alpha=0.25)
        ax.legend()
        fig.tight_layout()
        path = outdir / filename
        fig.savefig(path, dpi=220)
        plt.close(fig)
        out[filename] = str(path)

    # Stacked broad-window science loss causes.
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    broad_rows = [r for r in rows if r["energy_window"] == "broad_480_550"]
    x = np.arange(len(broad_rows))
    causes = sorted({c for r in broad_rows for c in json.loads(r["dominant_science_loss_causes"]).keys()})
    bottom = np.zeros(len(broad_rows))
    for cause in causes:
        vals = []
        for r in broad_rows:
            d = json.loads(r["dominant_science_loss_causes"])
            # Convert counts to fraction using total loss fraction distribution.
            total = sum(d.values())
            frac = r["science_loss_fraction"] * d.get(cause, 0) / total if total else 0.0
            vals.append(frac)
        vals_arr = np.asarray(vals)
        ax.bar(x, vals_arr * 100.0, bottom=bottom * 100.0, label=cause)
        bottom += vals_arr
    ax.set_xticks(x, [f"{r['window_us']:g}" for r in broad_rows])
    ax.set_xlabel("Coincidence window (us)")
    ax.set_ylabel("Broad-window science loss (%)")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    path = outdir / "lost_cause_vs_window.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    out["lost_cause_vs_window.png"] = str(path)
    return out


def write_recommendation(result: dict[str, Any], outdir: Path) -> None:
    rows = result["rows"]
    broad = [r for r in rows if r["energy_window"] == "broad_480_550"]
    row_1 = min(broad, key=lambda r: abs(float(r["window_us"]) - 1.0))
    row_10 = min(broad, key=lambda r: abs(float(r["window_us"]) - 10.0))
    row_100 = min(broad, key=lambda r: abs(float(r["window_us"]) - 100.0))
    strong = row_100["science_survival"] < 0.9 or row_100["background_final_cps"] > 1.5 * row_1["background_final_cps"]
    md = f"""# Timing-window scan recommendation

Status: `{result['status']}`

The scan uses the corrected day-15 event catalog and bootstraps candidate
clusters for each electronics coincidence window.  It is a timing-systematic
estimator, not a new transport run.

## Key broad-window rows

- 1 us: background final `{row_1['background_final_cps']:.6g}` cps, science survival `{row_1['science_survival']:.6g}`.
- 10 us: background final `{row_10['background_final_cps']:.6g}` cps, science survival `{row_10['science_survival']:.6g}`.
- 100 us: background final `{row_100['background_final_cps']:.6g}` cps, science survival `{row_100['science_survival']:.6g}`.

## Recommendation

Use 1 us as the baseline electronics window for quoted sensitivities.  Treat
10--100 us as a hardware systematic bracket.  The 100 us row {'is' if strong else 'is not'}
large enough to be a dominant systematic under the current conservative window
counter.
"""
    (outdir / "timing_window_recommendation.md").write_text(md, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--trials", type=int, default=500_000)
    parser.add_argument("--seed", type=int, default=26051206)
    args = parser.parse_args()

    _ = (WORKSPACE / "memory.md").read_text(encoding="utf-8", errors="ignore")
    _ = (WORKSPACE / "workflow.md").read_text(encoding="utf-8", errors="ignore")
    args.out.mkdir(parents=True, exist_ok=True)
    cfg = load_json(args.config)
    cat = load_catalog(args.catalog)
    summary = load_json(args.summary)
    result = run_scan(cat, cfg, summary, int(args.trials), int(args.seed))
    result["figures"] = plot_outputs(result, args.out)
    (args.out / "timing_window_scan_summary.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    write_csv(args.out / "timing_window_scan_summary.csv", result["rows"])
    write_recommendation(result, args.out)
    (args.out / "audit.json").write_text(json.dumps({"status": result["status"], "trials": args.trials, "seed": args.seed}, indent=2), encoding="utf-8")
    print(args.out / "timing_window_scan_summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
