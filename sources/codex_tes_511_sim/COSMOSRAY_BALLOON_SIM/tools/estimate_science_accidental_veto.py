#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Estimate accidental background veto of 511-keV science events.

The detector transport has already been simulated in the prompt, delayed and
science SIM files.  This script tests the remaining timing problem: an otherwise
accepted science event can share the 1 us coincidence window with unrelated
background activity and be lost by BGO, energy-window, or Compton/FoV selection.

The estimator bootstraps high-statistics science trials from the audited event
catalog and samples the prompt+delayed background as a Poisson point process.
"""

from __future__ import annotations

import argparse
import json
import math
import pickle
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import make_complete_day15_report as complete


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
DEFAULT_OUT = ROOT / "reports" / "science_accidental_veto"
CATALOG = ROOT / "reports" / "day15_complete_report" / "work" / "event_catalog.pkl"
SUMMARY = ROOT / "reports" / "day15_complete_report" / "complete_day15_summary.json"


WINDOWS = {
    "broad_480_550": (480.0, 550.0),
    "line_510p3_511p8": (510.3, 511.8),
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def classify_candidate(cat: dict, event_indices: np.ndarray, lo: float, hi: float, reject_policy: str) -> tuple[bool, str]:
    energy = float(np.sum(cat["tes_total_keV"][event_indices]))
    bgo = float(np.sum(cat["bgo_total_keV"][event_indices]))
    if not (lo <= energy < hi):
        return False, "energy_out"
    if bgo >= complete.BGO_THR_KEV:
        return False, "bgo_veto"
    hits = complete.aggregate_candidate_hits(cat, event_indices.astype(np.int64))
    keep, cls = complete.classify_final(hits, reject_policy)
    return bool(keep), ("kept" if keep else f"compton_{cls}")


def precompute_isolated(cat: dict, science_idx: np.ndarray, reject_policy: str) -> dict:
    isolated = {}
    energy = cat["tes_total_keV"][science_idx].astype(float)
    bgo = cat["bgo_total_keV"][science_idx].astype(float)
    pix_count = cat["pix_count"][science_idx].astype(int)
    for name, (lo, hi) in WINDOWS.items():
        flags = np.zeros(len(science_idx), dtype=bool)
        causes = Counter()
        in_energy = (energy >= lo) & (energy < hi)
        in_bgo = bgo < complete.BGO_THR_KEV
        fast_reject_energy = ~in_energy
        fast_reject_bgo = in_energy & ~in_bgo
        fast_single_keep = in_energy & in_bgo & (pix_count == 1)
        flags[fast_single_keep] = True
        causes["energy_out"] += int(np.sum(fast_reject_energy))
        causes["bgo_veto"] += int(np.sum(fast_reject_bgo))
        causes["kept"] += int(np.sum(fast_single_keep))

        needs_compton = np.flatnonzero(in_energy & in_bgo & (pix_count != 1))
        for n in needs_compton:
            idx = int(science_idx[n])
            if pix_count[n] <= 0:
                keep, cause = False, "no_tes"
            else:
                keep, cls = complete.classify_final(complete.event_hits(cat, idx), reject_policy)
                cause = "kept" if keep else f"compton_{cls}"
            flags[n] = keep
            causes[cause] += 1
        isolated[name] = {"flags": flags, "causes": dict(causes)}
    return isolated


def binom_err(p: float, n: int) -> float:
    if n <= 0:
        return float("nan")
    return math.sqrt(max(p * (1.0 - p), 0.0) / n)


def run_trials(cat: dict, summary: dict, n_trials: int, seed: int, reject_policy: str) -> dict:
    rng = np.random.default_rng(seed)
    streams = cat["stream"].astype(str)
    science_idx = np.flatnonzero(streams == "science")
    bg_idx = np.flatnonzero((streams == "prompt") | (streams == "delayed"))
    if len(science_idx) == 0 or len(bg_idx) == 0:
        raise RuntimeError("catalog must contain science and prompt/delayed background streams")

    science_rates = cat["rate_hz"][science_idx].astype(float)
    bg_rates = cat["rate_hz"][bg_idx].astype(float)
    science_prob = science_rates / np.sum(science_rates)
    bg_prob = bg_rates / np.sum(bg_rates)
    bg_total_rate = float(np.sum(bg_rates))
    tau = float(summary["normalization"]["coincidence_window_s"])
    q_continue = 1.0 - math.exp(-bg_total_rate * tau)
    p_stop = math.exp(-bg_total_rate * tau)

    # Consecutive background events connected to the science event on each side
    # are geometrically distributed.  This reproduces the same rolling-window
    # grouping criterion used by the production timeline code.
    left = rng.geometric(p_stop, size=n_trials) - 1
    right = rng.geometric(p_stop, size=n_trials) - 1
    bg_counts = (left + right).astype(np.int16)
    total_bg_draws = int(np.sum(bg_counts))
    bg_choices = rng.choice(bg_idx, size=total_bg_draws, replace=True, p=bg_prob) if total_bg_draws else np.empty(0, dtype=np.int64)
    bg_offsets = np.concatenate(([0], np.cumsum(bg_counts, dtype=np.int64)))

    sci_choice_pos = rng.choice(np.arange(len(science_idx)), size=n_trials, replace=True, p=science_prob)
    sci_choices = science_idx[sci_choice_pos]
    isolated = precompute_isolated(cat, science_idx, reject_policy)

    out = {
        "n_trials": int(n_trials),
        "seed": int(seed),
        "coincidence_window_s": tau,
        "background_total_rate_hz": bg_total_rate,
        "science_catalog_events": int(len(science_idx)),
        "background_catalog_events": int(len(bg_idx)),
        "background_cluster": {
            "p_any_background_model": float(1.0 - p_stop * p_stop),
            "q_continue_one_side": float(q_continue),
            "sampled_trials_with_background": int(np.sum(bg_counts > 0)),
            "sampled_background_draws": total_bg_draws,
            "sampled_multiplicity": {str(int(k)): int(v) for k, v in sorted(Counter(bg_counts.tolist()).items())},
        },
        "windows": {},
    }

    mixed_trials = np.flatnonzero(bg_counts > 0)
    for name, (lo, hi) in WINDOWS.items():
        base_flags = isolated[name]["flags"][sci_choice_pos]
        base_selected = int(np.sum(base_flags))
        cause_counts = Counter()
        survived = 0
        altered_kept = 0
        selected_with_bg = 0

        # No accidental background: selected science event remains selected.
        no_bg_base = int(np.sum(base_flags & (bg_counts == 0)))
        survived += no_bg_base

        for trial in mixed_trials:
            if not base_flags[trial]:
                continue
            start = int(bg_offsets[trial])
            end = int(bg_offsets[trial + 1])
            ev = np.concatenate(([sci_choices[trial]], bg_choices[start:end])).astype(np.int64)
            keep, cause = classify_candidate(cat, ev, lo, hi, reject_policy)
            if keep:
                survived += 1
                selected_with_bg += 1
                if end > start:
                    altered_kept += 1
            else:
                cause_counts[cause] += 1

        lost = base_selected - survived
        correction = survived / base_selected if base_selected else float("nan")
        loss = lost / base_selected if base_selected else float("nan")
        accidental_base = int(np.sum(base_flags & (bg_counts > 0)))
        conditional_loss = lost / accidental_base if accidental_base else float("nan")
        out["windows"][name] = {
            "energy_window_keV": [lo, hi],
            "isolated_catalog_causes": isolated[name]["causes"],
            "base_selected_trials": base_selected,
            "base_selected_fraction": base_selected / n_trials,
            "base_selected_with_accidental_bg": accidental_base,
            "survived_trials": int(survived),
            "lost_trials": int(lost),
            "accidental_loss_fraction_all_selected": float(loss),
            "accidental_survival_correction": float(correction),
            "binomial_1sigma_loss_fraction": binom_err(loss, base_selected),
            "conditional_loss_given_accidental_bg": float(conditional_loss),
            "selected_with_accidental_bg": int(selected_with_bg),
            "selected_with_accidental_bg_and_altered_candidate": int(altered_kept),
            "loss_causes": dict(cause_counts),
        }
    return out


def write_csv(result: dict, outdir: Path):
    path = outdir / "science_accidental_veto_summary.csv"
    lines = [
        "window,base_selected_trials,base_selected_fraction,base_selected_with_accidental_bg,lost_trials,loss_fraction_all_selected,loss_fraction_1sigma,survival_correction,conditional_loss_given_accidental_bg,loss_causes\n"
    ]
    for name, vals in result["windows"].items():
        lines.append(
            f"{name},{vals['base_selected_trials']},{vals['base_selected_fraction']:.12g},"
            f"{vals['base_selected_with_accidental_bg']},{vals['lost_trials']},"
            f"{vals['accidental_loss_fraction_all_selected']:.12g},{vals['binomial_1sigma_loss_fraction']:.12g},"
            f"{vals['accidental_survival_correction']:.12g},{vals['conditional_loss_given_accidental_bg']:.12g},"
            f"\"{json.dumps(vals['loss_causes'], sort_keys=True)}\"\n"
        )
    path.write_text("".join(lines), encoding="utf-8")
    return path


def plot_loss(result: dict, outdir: Path):
    path = outdir / "science_accidental_veto_loss.png"
    names = list(result["windows"].keys())
    labels = ["480-550 keV", "510.3-511.8 keV"]
    causes = ["energy_out", "bgo_veto", "compton_veto", "compton_reject_kept", "compton_no_tes"]
    x = np.arange(len(names))
    bottoms = np.zeros(len(names))
    fig, ax = plt.subplots(figsize=(7.0, 4.6))
    colors = {
        "energy_out": "#CC6677",
        "bgo_veto": "#4477AA",
        "compton_veto": "#EE7733",
        "compton_reject_kept": "#AA3377",
        "compton_no_tes": "#BBBBBB",
    }
    for cause in causes:
        vals = []
        for name in names:
            w = result["windows"][name]
            vals.append(w["loss_causes"].get(cause, 0) / max(w["base_selected_trials"], 1))
        vals = np.asarray(vals)
        if np.any(vals > 0):
            ax.bar(x, vals * 100.0, bottom=bottoms * 100.0, color=colors.get(cause, "#999999"), label=cause)
            bottoms += vals
    ax.set_xticks(x, labels)
    ax.set_ylabel("Accidental loss of isolated selected science events (%)")
    ax.set_title("High-statistics accidental veto correction")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(fontsize=8)
    for i, name in enumerate(names):
        corr = result["windows"][name]["accidental_survival_correction"]
        ax.text(i, bottoms[i] * 100.0 + 0.005, f"corr={corr:.5f}", ha="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def update_memory_workflow(result: dict, outdir: Path):
    outdir_abs = outdir.resolve()
    broad = result["windows"]["broad_480_550"]
    line = result["windows"]["line_510p3_511p8"]
    marker = "## 2026-05-12 science accidental veto correction"
    mem_block = f"""

{marker}

- Ran high-statistics science accidental-veto bootstrap using `{CATALOG.relative_to(WORKSPACE)}`; output directory `{outdir_abs.relative_to(WORKSPACE)}`.
- Background total prompt+delayed rate in the event catalog is {result['background_total_rate_hz']:.6g} Hz with coincidence window {result['coincidence_window_s']:.1e} s; probability of at least one accidental background event connected to a science event is {result['background_cluster']['p_any_background_model']:.6g}.
- For isolated selected science events, accidental loss is {broad['accidental_loss_fraction_all_selected']:.6g} in 480-550 keV and {line['accidental_loss_fraction_all_selected']:.6g} in 510.3-511.8 keV; survival corrections are {broad['accidental_survival_correction']:.6g} and {line['accidental_survival_correction']:.6g}.
"""
    wf_block = f"""

{marker}

- Apply science accidental-veto correction factors to Asimov source response when quoting final 511-keV sensitivity: broad 480-550 correction {broad['accidental_survival_correction']:.6g}; line-window correction {line['accidental_survival_correction']:.6g}.
- The correction is based on high-statistics bootstrap of existing detector MC catalogs, not a new Cosima transport run; it addresses accidental timing loss, while intrinsic science BGO/Compton loss is already included in direct-expectation response.
"""
    memory = WORKSPACE / "memory.md"
    workflow = WORKSPACE / "workflow.md"
    mem_text = memory.read_text(encoding="utf-8", errors="ignore")
    wf_text = workflow.read_text(encoding="utf-8", errors="ignore")
    if marker not in mem_text:
        memory.write_text(mem_text.rstrip() + mem_block + "\n", encoding="utf-8")
    if marker not in wf_text:
        workflow.write_text(wf_text.rstrip() + wf_block + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=1_000_000)
    parser.add_argument("--seed", type=int, default=260512)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    # Explicitly read running memory/workflow before the audit.
    _ = (WORKSPACE / "memory.md").read_text(encoding="utf-8", errors="ignore")
    _ = (WORKSPACE / "workflow.md").read_text(encoding="utf-8", errors="ignore")

    args.outdir.mkdir(parents=True, exist_ok=True)
    with CATALOG.open("rb") as fh:
        cat = pickle.load(fh)
    summary = load_json(SUMMARY)
    reject_policy = str(summary["normalization"].get("reject_policy", "keep"))
    result = run_trials(cat, summary, int(args.trials), int(args.seed), reject_policy)
    result["input_catalog"] = str(CATALOG.relative_to(WORKSPACE))
    result["input_summary"] = str(SUMMARY.relative_to(WORKSPACE))
    result["reject_policy"] = reject_policy
    (args.outdir / "science_accidental_veto_summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_csv(result, args.outdir)
    plot_loss(result, args.outdir)
    update_memory_workflow(result, args.outdir)
    print(args.outdir / "science_accidental_veto_summary.json")


if __name__ == "__main__":
    main()
