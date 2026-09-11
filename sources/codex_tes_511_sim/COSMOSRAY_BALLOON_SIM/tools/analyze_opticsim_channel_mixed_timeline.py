#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a common Poisson timeline for the current opticsim channel route."""

from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/codex_tes_511_matplotlib")

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import analyze_opticsim_mixed_timeline as mix  # noqa: E402

POISSON_95_ZERO_COUNT_MEAN = 2.995732273553991


DEFAULT_OUT = ROOT / "reports_260516" / "opticsim_mixed_timeline_channel_wallbywall_511_fullchain_20260521"
DEFAULT_SCIENCE_SIM = (
    ROOT
    / "sources/opticsim_bridge/channel_wallbywall_511_20k_20260521_poisson1800"
    / "Opticsim_channel_wallbywall_511_20k_20260521_poisson1800.inc1.id1.sim.gz"
)
DEFAULT_PROMPT_SIM = (
    ROOT
    / "sources/opticsim_bridge/allparticle_farfield_channel_wallbywall_100k_20260521_csvtime"
    / "Opticsim_allparticle_farfield_channel_wallbywall_100k_20260521_csvtime.inc1.id1.sim.gz"
)
DEFAULT_DELAYED_SIM = (
    ROOT
    / "sources/opticsim_bridge/activation_decay_channel_wallbywall_100k_day15_20260521_csvtime"
    / "Opticsim_activation_decay_channel_wallbywall_100k_day15_20260521_csvtime.inc1.id1.sim.gz"
)
DEFAULT_CHANNEL_REPLAY = ROOT / "reports_260516/opticsim_channel_wallbywall_511_replay_20260521/summary.json"
DEFAULT_PROMPT_SUMMARY = ROOT / "runs/opticsim_allparticle_farfield_channel_wallbywall_100k_20260521/summary.json"
DEFAULT_ACTIVATION = ROOT / "reports_260516/opticsim_activation_channel_wallbywall_100k_20260521/source_build_summary.json"


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--science-sim", type=Path, default=DEFAULT_SCIENCE_SIM)
    ap.add_argument("--prompt-sim", type=Path, default=DEFAULT_PROMPT_SIM)
    ap.add_argument("--delayed-sim", type=Path, default=DEFAULT_DELAYED_SIM)
    ap.add_argument("--channel-replay-summary", type=Path, default=DEFAULT_CHANNEL_REPLAY)
    ap.add_argument("--expacs-config", type=Path, default=mix.DEFAULT_EXPACS)
    ap.add_argument("--prompt-transport-summary", type=Path, default=DEFAULT_PROMPT_SUMMARY)
    ap.add_argument("--activation-summary", type=Path, default=DEFAULT_ACTIVATION)
    ap.add_argument("--local-background-summary", type=Path, default=mix.DEFAULT_LOCAL_BACKGROUND)
    ap.add_argument("--line-audit", type=Path, default=mix.DEFAULT_LINE_AUDIT)
    ap.add_argument("--outdir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--science-flux", type=float, default=1.0e-4)
    ap.add_argument("--obs-time-s", type=float, default=1800.0)
    ap.add_argument("--n-realizations", type=int, default=500)
    ap.add_argument("--seed", type=int, default=20260521)
    ap.add_argument("--reject-policy", default="keep")
    return ap.parse_args()


def channel_area_and_primaries(replay: dict[str, Any]) -> tuple[float, int]:
    if "channel_aperture_area_cm2" in replay:
        area_cm2 = float(replay["channel_aperture_area_cm2"])
    else:
        area_cm2 = float(replay["ring_tile_geometric_area_cm2"])
    channel = replay.get("channel", {})
    n_primaries = int(channel.get("n_primaries", replay.get("n_primaries", 0)))
    if n_primaries <= 0:
        raise KeyError("channel replay summary missing channel.n_primaries")
    return area_cm2, n_primaries


def zero_count_upper_limits(
    metas: list[dict[str, Any]],
    local_background: dict[str, float],
    quantile_mean: float = POISSON_95_ZERO_COUNT_MEAN,
) -> dict[str, Any]:
    by_stream: dict[str, dict[str, Any]] = {}
    for meta in metas:
        stream = str(meta["stream"])
        if stream == "science":
            continue
        n_catalog = int(meta["catalog_events_with_tes_or_bgo"])
        row = {
            "catalog_events_with_tes_or_bgo": n_catalog,
            "rate_hz_per_input_event": float(meta["rate_hz_per_event"]),
            "applies": n_catalog == 0,
        }
        if n_catalog == 0:
            row["any_tes_or_bgo_rate_95_cps"] = quantile_mean * float(meta["rate_hz_per_event"])
            row["note"] = "95% Poisson upper limit for zero detected TES/BGO catalog events."
        else:
            row["any_tes_or_bgo_rate_95_cps"] = None
            row["note"] = "Not a zero-count stream; use measured catalog rates instead."
        by_stream[stream] = row

    combined = sum(
        float(row["any_tes_or_bgo_rate_95_cps"] or 0.0)
        for row in by_stream.values()
        if row["applies"]
    )
    return {
        "poisson_mean_95_for_zero_observed": quantile_mean,
        "by_stream": by_stream,
        "prompt_plus_delayed_any_tes_or_bgo_rate_95_cps": combined,
        "fraction_of_local_detector_background": {
            window: (combined / bg if bg > 0.0 else None)
            for window, row in local_background.items()
            if isinstance(row, dict)
            for bg in [float(row.get("background_final_cps_prompt_plus_delayed") or 0.0)]
        },
        "claim_boundary": (
            "This is an any-TES/BGO-event upper limit. The 480-550 keV and "
            "510.3-511.8 keV final-window upper limits cannot exceed it, but "
            "the sampled prompt/delayed catalogs still contain no measured "
            "window events."
        ),
    }


def main() -> int:
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    replay = mix.load_json(args.channel_replay_summary)
    expacs = mix.load_json(args.expacs_config)
    prompt_summary = mix.load_json(args.prompt_transport_summary)
    activation = mix.load_json(args.activation_summary)
    local_background = mix.load_local_background_rates(args.local_background_summary, args.line_audit)

    aperture_area_cm2, channel_primaries = channel_area_and_primaries(replay)
    science_rate_per_event = args.science_flux * aperture_area_cm2 / channel_primaries

    prompt_total_rate = float(expacs["total_rate_hz_for_this_source_area"])
    prompt_primaries = int(prompt_summary["n_simulated"])
    prompt_rate_per_event = prompt_total_rate / prompt_primaries

    delayed_activity = float(activation["total_activity_Bq_day"])
    delayed_decay_rows = int(activation["n_decay_source_rows"])
    delayed_rate_per_event = delayed_activity / delayed_decay_rows if delayed_decay_rows > 0 else 0.0

    source_norm = {
        "science": {
            "flux_ph_cm2_s": args.science_flux,
            "configured_channel_aperture_area_cm2": aperture_area_cm2,
            "channel_primaries": channel_primaries,
            "rate_hz_per_channel_primary": science_rate_per_event,
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
        (args.prompt_sim, "prompt", "opticsim_channel_expacs_allparticle", prompt_rate_per_event),
        (args.delayed_sim, "delayed", "opticsim_channel_activation_day15", delayed_rate_per_event),
        (args.science_sim, "science", "opticsim_channel_point", science_rate_per_event),
    ]:
        cat, meta = mix.parse_sim_catalog(path, stream, tag, rate)
        cats.append(cat)
        metas.append(meta)

    cat = mix.merge_catalogs(cats)
    with (args.outdir / "opticsim_channel_mixed_event_catalog.pkl").open("wb") as fh:
        pickle.dump(cat, fh, protocol=pickle.HIGHEST_PROTOCOL)

    direct = mix.direct_window_rates(cat, args.reject_policy)
    timelines = mix.summarize_timeline_realizations(
        cat,
        args.obs_time_s,
        args.n_realizations,
        args.seed,
        args.reject_policy,
    )
    sig = mix.significance_summary(direct, args.science_flux, args.obs_time_s, local_background)
    upper_limits = zero_count_upper_limits(metas, local_background)

    mix.write_csv(args.outdir / "timeline_realizations.csv", timelines["rows"])
    mix.write_csv(args.outdir / "timeline_draws.csv", timelines["draw_rows"])
    mix.plot_realizations(timelines["rows"], args.outdir / "timeline_realizations_480_550.png")

    summary = {
        "status": "PASS",
        "claim_level": "OPTICSIM_CHANNEL_SCIENCE_PLUS_LOCAL_DETECTOR_BACKGROUND_COMMON_TIMELINE_SCAFFOLD",
        "normalization": source_norm,
        "inputs": {
            "science_sim": str(args.science_sim),
            "prompt_sim": str(args.prompt_sim),
            "delayed_sim": str(args.delayed_sim),
            "channel_replay_summary": str(args.channel_replay_summary),
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
        "zero_count_upper_limits_95": upper_limits,
        "direct_window_rates": direct,
        "timeline": {
            "obs_time_s": args.obs_time_s,
            "n_realizations": args.n_realizations,
            "seed": args.seed,
            "coincidence_window_s": mix.complete.COINCIDENCE_WINDOW_S,
            "stats_480_550": timelines["stats"],
            "realizations_csv": str(args.outdir / "timeline_realizations.csv"),
            "draws_csv": str(args.outdir / "timeline_draws.csv"),
            "figure": str(args.outdir / "timeline_realizations_480_550.png"),
        },
        "significance": sig,
        "limitations": [
            "This common timeline is post-Cosima catalog resampling, matching the existing Laue detector-timing workflow.",
            "The science stream uses the imported wall-by-wall channel phase space and XZTES/Cosima detector replay.",
            "The prompt and delayed optics streams use the available channel_4ring mass scaffold because the unpublished full wall-by-wall channel mass/activation model is not available locally.",
            "Finite 3sigma numbers use the existing local detector prompt+delayed background ledger plus the new channel science response.",
        ],
    }
    (args.outdir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    broad = sig["broad_480_550"]
    line = sig["line_510p3_511p8"]
    prompt_upper = upper_limits["by_stream"]["prompt"]["any_tes_or_bgo_rate_95_cps"]
    delayed_upper = upper_limits["by_stream"]["delayed"]["any_tes_or_bgo_rate_95_cps"]
    prompt_upper_text = f"{prompt_upper:.6g}" if prompt_upper is not None else "not applicable"
    delayed_upper_text = f"{delayed_upper:.6g}" if delayed_upper is not None else "not applicable"
    md = f"""# Opticsim Channel Mixed Timeline

Status: `PASS`

This report is the channel-route counterpart of the current Laue mixed-timeline scaffold. It replaces the Laue science optics with the imported wall-by-wall channel phase space and uses the same XZTES/Cosima detector replay, BGO veto, Compton/FoV selection, and local detector background ledger.

## Inputs

- Science: `{args.science_sim}`
- Prompt: `{args.prompt_sim}`
- Delayed: `{args.delayed_sim}`
- Local detector background ledger: `{args.local_background_summary}`

## Normalization

- Science flux: `{args.science_flux:.6g}` ph cm^-2 s^-1.
- Configured channel aperture area: `{aperture_area_cm2:.6g}` cm2 over `{channel_primaries}` simulated channel primaries.
    - EXPACS/PARMA prompt source-area rate: `{prompt_total_rate:.6g}` Hz over `{prompt_primaries}` simulated primaries.
    - Day-15 channel-mass activation activity: `{delayed_activity:.6g}` Bq over `{delayed_decay_rows}` sampled decay ions.

## Zero-Count Prompt/Delayed Upper Limits

- Prompt detector catalog events with TES/BGO: `{metas[0]['catalog_events_with_tes_or_bgo']}`; 95% any-TES/BGO rate upper limit `{prompt_upper_text}` cps.
- Delayed detector catalog events with TES/BGO: `{metas[1]['catalog_events_with_tes_or_bgo']}`; 95% any-TES/BGO rate upper limit `{delayed_upper_text}` cps.
- Combined prompt+delayed any-TES/BGO 95% upper limit: `{upper_limits['prompt_plus_delayed_any_tes_or_bgo_rate_95_cps']:.6g}` cps.

This is an upper limit, not a measured zero background. The final-window rates for 480-550 keV and 510.3-511.8 keV cannot exceed the any-TES/BGO upper limit, but the sampled prompt/delayed catalogs still contain no measured window events.

## Direct BGO + Compton/FoV Rates

| window | background final cps | science final cps | response cps/(ph cm^-2 s^-1) | 3sigma 1Ms flux | T3 at input flux |
|---|---:|---:|---:|---:|---:|
| 480-550 keV | {broad['background_final_cps_prompt_plus_delayed']:.6g} | {broad['science_final_cps_at_input_flux']:.6g} | {broad['science_response_cps_per_ph_cm2_s']:.6g} | {broad['flux_3sigma_1Ms_ph_cm2_s']:.6g} | {broad['T3_days_for_input_flux']:.6g} d |
| 510.3-511.8 keV | {line['background_final_cps_prompt_plus_delayed']:.6g} | {line['science_final_cps_at_input_flux']:.6g} | {line['science_response_cps_per_ph_cm2_s']:.6g} | {line['flux_3sigma_1Ms_ph_cm2_s']:.6g} | {line['T3_days_for_input_flux']:.6g} d |

## Common Timeline

`{args.n_realizations}` Poisson timelines of `{args.obs_time_s:.6g}` s were drawn for the current channel replay catalog. The 480-550 keV final-rate mean is `{timelines['stats']['final_cps']['mean']:.6g}` cps, with median `{timelines['stats']['final_cps']['median']:.6g}` cps.

## Claim Control

The channel science path is closed at the same detector-chain layer as the Laue route. The prompt/delayed optics-mass path is still a scaffold using `channel_4ring` mass geometry, so it supports workflow closure and rate bookkeeping but not a publication-grade channel activation claim.
"""
    (args.outdir / "README.md").write_text(md, encoding="utf-8")
    print(json.dumps({"status": "PASS", "summary": str(args.outdir / "summary.json")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
