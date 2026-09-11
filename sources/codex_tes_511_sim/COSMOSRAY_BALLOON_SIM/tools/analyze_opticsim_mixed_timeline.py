#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a common Poisson timeline from the current opticsim mainline replays.

This is the post-detector timing layer for the opticsim/Laue scaffold rerun:

* Laue science photons are normalized by demo Laue tile area / simulated
  primaries, then scaled by a requested source flux.
* Atmospheric prompt focal-plane crossings are normalized by the EXPACS/PARMA
  source-area rate divided by the simulated primary count.
* Optics activation delayed crossings are normalized by the day-15 total
  activity divided by the sampled decay-ion count.

The script does not rerun Cosima.  It consumes the detector SIM files already
produced from the focal-plane EventLists, places the three streams on a common
Poisson timeline, and applies the same BGO and Compton/FoV selection helpers
used by the existing detector report.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import pickle
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import make_complete_day15_report as complete  # noqa: E402


DEFAULT_OUT = ROOT / "reports_260516" / "opticsim_mixed_timeline_20260521"
DEFAULT_SCIENCE_SIM = (
    ROOT
    / "sources/opticsim_bridge/laue_multiring_science_20260521_rerun100k_poisson1800"
    / "Opticsim_laue_multiring_science_20260521_rerun100k_poisson1800.inc1.id1.sim.gz"
)
DEFAULT_PROMPT_SIM = (
    ROOT
    / "sources/opticsim_bridge/allparticle_farfield_20k_20260521_csvtime"
    / "Opticsim_allparticle_farfield_20k_20260521_csvtime.inc1.id1.sim.gz"
)
DEFAULT_DELAYED_SIM = (
    ROOT
    / "sources/opticsim_bridge/activation_decay_20k_day15_20260521_csvtime"
    / "Opticsim_activation_decay_20k_day15_20260521_csvtime.inc1.id1.sim.gz"
)
DEFAULT_LAUE_REPLAY = ROOT / "reports_260516/opticsim_laue_replay_20260521/summary.json"
DEFAULT_EXPACS = ROOT / "run_configs/opticsim_bridge/expacs_allparticle_farfield_20bins_opticsim_rerun20260521.json"
DEFAULT_PROMPT_SUMMARY = Path("/tmp/codex_opticsim_allparticle_farfield_20k_20260521/summary.json")
DEFAULT_ACTIVATION = ROOT / "reports_260516/opticsim_activation_20k_20260521/source_build_summary.json"
DEFAULT_LOCAL_BACKGROUND = ROOT / "reports/day15_complete_report/complete_day15_summary.json"
DEFAULT_LINE_AUDIT = ROOT / "reports/day15_sci_manuscript/sci_manuscript_audit.json"

WINDOWS = {
    "broad_480_550": (480.0, 550.0),
    "line_510p3_511p8": (510.3, 511.8),
}

ID_RE = re.compile(r"^ID\s+(\d+)")
TI_RE = re.compile(r"^TI\s+([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)")
CC_HIT_RE = complete.CC_HIT_RE
TP_RE = complete.TP_RE


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))


def open_text(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return path.open("r", encoding="utf-8", errors="ignore")


def parse_sim_catalog(path: Path, stream: str, tag: str, rate_hz_per_event: float) -> tuple[dict[str, Any], dict[str, Any]]:
    cat = complete.empty_catalog()
    cur_id: int | None = None
    cur_ti: float | None = None
    bgo_total = 0.0
    pix: dict[str, dict[str, float | int]] = {}
    ti_values: list[float] = []

    def flush() -> None:
        nonlocal cur_id, cur_ti, bgo_total, pix
        if cur_id is not None:
            complete.append_event(cat, stream, tag, str(path), int(cur_id), rate_hz_per_event, bgo_total, pix)
            if cur_ti is not None:
                ti_values.append(float(cur_ti))
        cur_id = None
        cur_ti = None
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
            m_id = ID_RE.match(line)
            if m_id:
                cur_id = int(m_id.group(1))
                cat["n_generated_events_seen"] += 1
                continue
            m_ti = TI_RE.match(line)
            if m_ti:
                cur_ti = float(m_ti.group(1))
                continue
            if not line.startswith("CC HIT "):
                continue
            hit = complete.parse_cc_hit(line)
            if hit is None:
                continue
            vol, edep, x, y, z = hit
            m_tp = TP_RE.match(vol)
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

    arr = np.asarray(ti_values, dtype=float)
    meta = {
        "path": str(path),
        "stream": stream,
        "tag": tag,
        "rate_hz_per_event": rate_hz_per_event,
        "generated_events_seen": int(cat["n_generated_events_seen"]),
        "catalog_events_with_tes_or_bgo": int(len(cat["stream"])),
        "sum_catalog_rate_hz": float(rate_hz_per_event * len(cat["stream"])),
    }
    if len(arr):
        meta.update(
            {
                "sim_time_min_s": float(np.min(arr)),
                "sim_time_max_s": float(np.max(arr)),
                "sim_time_span_s": float(np.max(arr) - np.min(arr)),
            }
        )
    return cat, meta


def merge_catalogs(catalogs: list[dict[str, Any]]) -> dict[str, Any]:
    merged = complete.empty_catalog()
    for cat in catalogs:
        complete.merge_one_catalog_into(merged, cat)
    return complete.catalog_to_arrays(merged)


def classify_event_window(cat: dict[str, Any], idx: int, lo: float, hi: float, reject_policy: str) -> str:
    e = float(cat["tes_total_keV"][idx])
    if not (lo <= e < hi):
        return "energy_out"
    if float(cat["bgo_total_keV"][idx]) >= complete.BGO_THR_KEV:
        return "bgo_veto"
    keep, cls = complete.classify_final(complete.event_hits(cat, idx), reject_policy)
    return "final" if keep else f"compton_{cls}"


def direct_window_rates(cat: dict[str, Any], reject_policy: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, (lo, hi) in WINDOWS.items():
        stages = defaultdict(float)
        by_stream = defaultdict(lambda: defaultdict(float))
        class_counts = Counter()
        for idx in range(len(cat["stream"])):
            e = float(cat["tes_total_keV"][idx])
            if not (lo <= e < hi):
                continue
            stream = str(cat["stream"][idx])
            rate = float(cat["rate_hz"][idx])
            stages["raw"] += rate
            by_stream[stream]["raw"] += rate
            if float(cat["bgo_total_keV"][idx]) >= complete.BGO_THR_KEV:
                class_counts["bgo_veto"] += 1
                continue
            stages["bgo"] += rate
            by_stream[stream]["bgo"] += rate
            keep, cls = complete.classify_final(complete.event_hits(cat, idx), reject_policy)
            class_counts[cls] += 1
            if keep:
                stages["final"] += rate
                by_stream[stream]["final"] += rate
        out[name] = {
            "rates_cps": {k: float(v) for k, v in stages.items()},
            "rates_by_stream_cps": {k: {kk: float(vv) for kk, vv in d.items()} for k, d in by_stream.items()},
            "compton_class_counts": dict(class_counts),
        }
    return out


def summarize_timeline_realizations(
    cat: dict[str, Any],
    obs_time_s: float,
    n_realizations: int,
    seed: int,
    reject_policy: str,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    rows = []
    draw_rows = []
    for i in range(n_realizations):
        timeline = complete.draw_timeline(cat, obs_time_s, rng)
        result = complete.analyze_timeline(cat, timeline, obs_time_s, reject_policy)
        rows.append(
            {
                "realization": i,
                "raw_cps": float(result["stage_rates"].get("raw", 0.0)),
                "bgo_cps": float(result["stage_rates"].get("bgo", 0.0)),
                "final_cps": float(result["stage_rates"].get("final", 0.0)),
                "n_candidates_total": int(result["n_candidates_total"]),
                "n_candidates_with_tes": int(result["n_candidates_with_tes"]),
                "n_mixed_candidates": int(result["n_mixed_candidates"]),
            }
        )
        draw_summary = timeline["draw_summary"]
        draw_rows.append(
            {
                "realization": i,
                **{f"{stream}_drawn": int(draw_summary.get(stream, {}).get("drawn", 0)) for stream in ("prompt", "delayed", "science")},
                **{f"{stream}_lambda": float(draw_summary.get(stream, {}).get("lambda", 0.0)) for stream in ("prompt", "delayed", "science")},
            }
        )

    def stats(key: str) -> dict[str, float]:
        arr = np.asarray([r[key] for r in rows], dtype=float)
        return {
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0,
            "p16": float(np.quantile(arr, 0.16)),
            "median": float(np.median(arr)),
            "p84": float(np.quantile(arr, 0.84)),
        }

    return {
        "rows": rows,
        "draw_rows": draw_rows,
        "stats": {
            "raw_cps": stats("raw_cps"),
            "bgo_cps": stats("bgo_cps"),
            "final_cps": stats("final_cps"),
            "n_candidates_total": stats("n_candidates_total"),
            "n_candidates_with_tes": stats("n_candidates_with_tes"),
            "n_mixed_candidates": stats("n_mixed_candidates"),
        },
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def plot_realizations(rows: list[dict[str, Any]], out: Path) -> None:
    x = np.arange(len(rows))
    raw = np.asarray([r["raw_cps"] for r in rows], dtype=float)
    bgo = np.asarray([r["bgo_cps"] for r in rows], dtype=float)
    final = np.asarray([r["final_cps"] for r in rows], dtype=float)
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    ax.plot(x, raw, lw=1.0, alpha=0.65, label="raw")
    ax.plot(x, bgo, lw=1.0, alpha=0.75, label="BGO pass")
    ax.plot(x, final, lw=1.3, alpha=0.9, label="BGO + Compton/FoV")
    ax.set_xlabel("Poisson timeline realization")
    ax.set_ylabel("480-550 keV rate (cps)")
    ax.set_title("Opticsim mainline common-timeline realizations")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=220)
    plt.close(fig)


def load_local_background_rates(summary_path: Path, line_audit_path: Path) -> dict[str, Any]:
    """Read the existing detector prompt+delayed background ledger.

    This ledger is not an optics response authority.  It is the local detector
    prompt/delayed background simulation already selected on a common Poisson
    timeline with BGO and Compton/FoV veto.
    """

    summary = load_json(summary_path)
    line = load_json(line_audit_path) if line_audit_path.exists() else {}
    broad_bg = float(summary["science_sensitivity"]["background_final_cps_prompt_plus_delayed"])
    prompt_final = float(summary["expectation_rates_by_stream_cps"]["prompt"]["final"])
    delayed_final = float(summary["expectation_rates_by_stream_cps"]["delayed"]["final"])
    return {
        "source": str(summary_path),
        "line_audit": str(line_audit_path),
        "claim": "local detector prompt+delayed background ledger; not a Phase12 optics response",
        "broad_480_550": {
            "background_final_cps_prompt_plus_delayed": broad_bg,
            "prompt_final_cps": prompt_final,
            "delayed_final_cps": delayed_final,
        },
        "line_510p3_511p8": {
            "background_final_cps_prompt_plus_delayed": float(
                line.get("line_window_510p3_511p8", {}).get("background_cps", broad_bg)
            ),
            "prompt_final_cps": None,
            "delayed_final_cps": None,
        },
    }


def significance_summary(
    windows: dict[str, Any],
    science_flux: float,
    exposure_s: float,
    local_background: dict[str, Any] | None,
) -> dict[str, Any]:
    out = {}
    for name, vals in windows.items():
        by_stream = vals["rates_by_stream_cps"]
        optics_bg_cps = float(by_stream.get("prompt", {}).get("final", 0.0) + by_stream.get("delayed", {}).get("final", 0.0))
        local_bg_cps = None
        if local_background is not None and name in local_background:
            local_bg_cps = float(local_background[name]["background_final_cps_prompt_plus_delayed"])
        bg_cps = local_bg_cps if local_bg_cps is not None else optics_bg_cps
        sci_cps = float(by_stream.get("science", {}).get("final", 0.0))
        response = sci_cps / science_flux if science_flux > 0 else float("nan")
        if bg_cps > 0.0 and response > 0.0:
            f3_1ms = 3.0 * math.sqrt(bg_cps * 1.0e6) / (response * 1.0e6)
            t3_for_input = (3.0 * math.sqrt(bg_cps) / max(sci_cps, 1e-300)) ** 2
            z_at_exposure = sci_cps * exposure_s / math.sqrt(bg_cps * exposure_s)
        else:
            f3_1ms = float("inf")
            t3_for_input = float("inf")
            z_at_exposure = float("inf") if sci_cps > 0 else 0.0
        out[name] = {
            "background_final_cps_prompt_plus_delayed": bg_cps,
            "optics_front_prompt_plus_delayed_final_cps": optics_bg_cps,
            "local_detector_background_final_cps_used": local_bg_cps,
            "science_final_cps_at_input_flux": sci_cps,
            "science_response_cps_per_ph_cm2_s": response,
            "flux_3sigma_1Ms_ph_cm2_s": f3_1ms,
            "T3_s_for_input_flux": t3_for_input,
            "T3_days_for_input_flux": t3_for_input / 86400.0,
            "significance_at_obs_time_sigma": z_at_exposure,
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--science-sim", type=Path, default=DEFAULT_SCIENCE_SIM)
    ap.add_argument("--prompt-sim", type=Path, default=DEFAULT_PROMPT_SIM)
    ap.add_argument("--delayed-sim", type=Path, default=DEFAULT_DELAYED_SIM)
    ap.add_argument("--laue-replay-summary", type=Path, default=DEFAULT_LAUE_REPLAY)
    ap.add_argument("--expacs-config", type=Path, default=DEFAULT_EXPACS)
    ap.add_argument("--prompt-transport-summary", type=Path, default=DEFAULT_PROMPT_SUMMARY)
    ap.add_argument("--activation-summary", type=Path, default=DEFAULT_ACTIVATION)
    ap.add_argument("--local-background-summary", type=Path, default=DEFAULT_LOCAL_BACKGROUND)
    ap.add_argument("--line-audit", type=Path, default=DEFAULT_LINE_AUDIT)
    ap.add_argument("--outdir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--science-flux", type=float, default=1.0e-4)
    ap.add_argument("--obs-time-s", type=float, default=1800.0)
    ap.add_argument("--n-realizations", type=int, default=500)
    ap.add_argument("--seed", type=int, default=20260521)
    ap.add_argument("--reject-policy", default="keep")
    args = ap.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)

    laue = load_json(args.laue_replay_summary)
    expacs = load_json(args.expacs_config)
    prompt_summary = load_json(args.prompt_transport_summary)
    activation = load_json(args.activation_summary)
    local_background = load_local_background_rates(args.local_background_summary, args.line_audit)

    laue_area_cm2 = float(laue.get("ring_tile_geometric_area_cm2", laue["ring_tile_geometric_area_cm2_demo"]))
    laue_primaries = int(laue["laue"]["n_primaries"])
    science_rate_per_event = args.science_flux * laue_area_cm2 / laue_primaries

    prompt_total_rate = float(expacs["total_rate_hz_for_this_source_area"])
    prompt_primaries = int(prompt_summary["n_simulated"])
    prompt_rate_per_event = prompt_total_rate / prompt_primaries

    delayed_activity = float(activation["total_activity_Bq_day"])
    delayed_decay_rows = int(activation["n_decay_source_rows"])
    delayed_rate_per_event = delayed_activity / delayed_decay_rows

    source_norm = {
        "science": {
            "flux_ph_cm2_s": args.science_flux,
            "configured_laue_geometric_area_cm2": laue_area_cm2,
            "laue_primaries": laue_primaries,
            "rate_hz_per_laue_primary": science_rate_per_event,
        },
        "prompt": {
            "expacs_total_rate_hz_for_source_area": prompt_total_rate,
            "opticsim_simulated_primaries": prompt_primaries,
            "rate_hz_per_primary": prompt_rate_per_event,
        },
        "delayed": {
            "total_activity_Bq_day15": delayed_activity,
            "sampled_decay_ions": delayed_decay_rows,
            "rate_hz_per_decay_ion": delayed_rate_per_event,
        },
    }

    cats = []
    metas = []
    for path, stream, tag, rate in [
        (args.prompt_sim, "prompt", "opticsim_expacs_allparticle", prompt_rate_per_event),
        (args.delayed_sim, "delayed", "opticsim_activation_day15", delayed_rate_per_event),
        (args.science_sim, "science", "opticsim_laue_point", science_rate_per_event),
    ]:
        cat, meta = parse_sim_catalog(path, stream, tag, rate)
        cats.append(cat)
        metas.append(meta)

    cat = merge_catalogs(cats)
    with (args.outdir / "opticsim_mixed_event_catalog.pkl").open("wb") as fh:
        pickle.dump(cat, fh, protocol=pickle.HIGHEST_PROTOCOL)

    direct = direct_window_rates(cat, args.reject_policy)
    timelines = summarize_timeline_realizations(cat, args.obs_time_s, args.n_realizations, args.seed, args.reject_policy)
    sig = significance_summary(direct, args.science_flux, args.obs_time_s, local_background)

    write_csv(args.outdir / "timeline_realizations.csv", timelines["rows"])
    write_csv(args.outdir / "timeline_draws.csv", timelines["draw_rows"])
    plot_realizations(timelines["rows"], args.outdir / "timeline_realizations_480_550.png")

    summary = {
        "status": "PASS",
        "claim_level": "OPTICSIM_LAUE_SCIENCE_PLUS_LOCAL_DETECTOR_BACKGROUND_COMMON_TIMELINE_SCAFFOLD",
        "normalization": source_norm,
        "inputs": {
            "science_sim": str(args.science_sim),
            "prompt_sim": str(args.prompt_sim),
            "delayed_sim": str(args.delayed_sim),
            "laue_replay_summary": str(args.laue_replay_summary),
            "expacs_config": str(args.expacs_config),
            "prompt_transport_summary": str(args.prompt_transport_summary),
            "activation_summary": str(args.activation_summary),
            "local_background_summary": str(args.local_background_summary),
            "line_audit": str(args.line_audit),
        },
        "local_detector_background": local_background,
        "source_catalogs": metas,
        "catalog_events": int(len(cat["stream"])),
        "catalog_rate_by_stream_hz": {
            stream: float(np.sum(cat["rate_hz"][cat["stream"] == stream]))
            for stream in ("prompt", "delayed", "science")
        },
        "direct_window_rates": direct,
        "timeline": {
            "obs_time_s": args.obs_time_s,
            "n_realizations": args.n_realizations,
            "seed": args.seed,
            "coincidence_window_s": complete.COINCIDENCE_WINDOW_S,
            "stats_480_550": timelines["stats"],
            "realizations_csv": str(args.outdir / "timeline_realizations.csv"),
            "draws_csv": str(args.outdir / "timeline_draws.csv"),
            "figure": str(args.outdir / "timeline_realizations_480_550.png"),
        },
        "significance": sig,
        "limitations": [
            "This common timeline is post-Cosima catalog resampling, matching the existing detector-timing workflow.",
            "The 20k/1k front-optics prompt/delayed detector replays produced no TES/BGO hits in this smoke statistic, so finite sensitivity uses the existing local detector prompt+delayed background ledger.",
            "Prompt and delayed optics catalogs are scaffold-statistics reruns; full production should increase statistics and preserve multi-particle shower correlations more explicitly.",
            "Science normalization uses the Laue geometric tile area in the supplied replay summary; the claim level depends on whether that ring config is a demo, CAM511-inspired scaffold, or production design.",
        ],
    }
    (args.outdir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    broad = sig["broad_480_550"]
    line = sig["line_510p3_511p8"]
    md = f"""# Opticsim Mainline Mixed Timeline

Status: `PASS`

This report uses the current opticsim/Laue mainline detector replays only.  It does not use the old Phase12 parameterized response as a performance authority.

## Inputs

- Science: `{args.science_sim}`
- Prompt: `{args.prompt_sim}`
- Delayed: `{args.delayed_sim}`
- Local detector background ledger: `{args.local_background_summary}`

## Normalization

- Science flux: `{args.science_flux:.6g}` ph cm^-2 s^-1.
- Configured Laue geometric area: `{laue_area_cm2:.6g}` cm2 over `{laue_primaries}` simulated primaries.
- EXPACS/PARMA prompt source-area rate: `{prompt_total_rate:.6g}` Hz over `{prompt_primaries}` simulated primaries.
- Day-15 optics activation activity: `{delayed_activity:.6g}` Bq over `{delayed_decay_rows}` sampled decay ions.

## Direct BGO + Compton/FoV Rates

| window | background final cps | science final cps | response cps/(ph cm^-2 s^-1) | 3sigma 1Ms flux | T3 at input flux |
|---|---:|---:|---:|---:|---:|
| 480-550 keV | {broad['background_final_cps_prompt_plus_delayed']:.6g} | {broad['science_final_cps_at_input_flux']:.6g} | {broad['science_response_cps_per_ph_cm2_s']:.6g} | {broad['flux_3sigma_1Ms_ph_cm2_s']:.6g} | {broad['T3_days_for_input_flux']:.6g} d |
| 510.3-511.8 keV | {line['background_final_cps_prompt_plus_delayed']:.6g} | {line['science_final_cps_at_input_flux']:.6g} | {line['science_response_cps_per_ph_cm2_s']:.6g} | {line['flux_3sigma_1Ms_ph_cm2_s']:.6g} | {line['T3_days_for_input_flux']:.6g} d |

## Common Timeline

`{args.n_realizations}` Poisson timelines of `{args.obs_time_s:.6g}` s were drawn for the current opticsim replay catalog.  The 480-550 keV final-rate mean is `{timelines['stats']['final_cps']['mean']:.6g}` cps, with median `{timelines['stats']['final_cps']['median']:.6g}` cps.  Mixed candidates are counted explicitly in `timeline_realizations.csv`.  The detector-local prompt/delayed background timeline is imported from the corrected day-15 ledger above, because its large event catalog is no longer retained in this compact working tree.

## Claim Control

This closes the requested two-stage timing workflow at scaffold level: opticsim focal-plane science has a detector SIM, front-optics prompt/delayed have detector replays, and the detector-local prompt/delayed background ledger is kept in the second-stage system.  The finite 3sigma numbers above use the local detector background ledger plus the new opticsim/Laue science response.  It is still not a mission-scale sensitivity claim until the Laue collecting area and diffuse high-statistics focal map are promoted from scaffold to production configuration.
"""
    (args.outdir / "README.md").write_text(md, encoding="utf-8")
    print(json.dumps({"status": "PASS", "summary": str(args.outdir / "summary.json")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
