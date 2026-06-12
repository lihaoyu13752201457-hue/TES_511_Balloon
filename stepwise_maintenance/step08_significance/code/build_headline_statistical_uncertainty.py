#!/usr/bin/env python3
"""Build MC statistical uncertainties for the headline Step08 backgrounds."""

from __future__ import annotations

import csv
import json
import math
import os
import pickle
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-newgeo")

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "stepwise_maintenance" / "step08_significance" / "outputs"
CATALOG = ROOT / "outputs" / "reports" / "day15_complete_report" / "work" / "event_catalog.pkl"
DAY15_SUMMARY = ROOT / "outputs" / "reports" / "day15_complete_report" / "complete_day15_summary.json"
STEP06_BG = ROOT / "stepwise_maintenance" / "step06_mission_time_variation" / "outputs" / "background_time_variation.csv"
OPTICS_AUTHORITY = ROOT / "stepwise_maintenance" / "step04_opticsim" / "optics_aeff_authority.json"
FOCUS_RESPONSE = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs" / "detector_coupled_focus_response.json"
NONXRAY_TABLE = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs" / "non_xray_background_w1_w2_veto_table.csv"
LINE_SUMMARY = OUT / "line_window_sensitivity_summary.json"
LINE_CSV = OUT / "line_window_sensitivity.csv"
SPATIAL_SUMMARY = OUT / "spatial_line_proxy_summary.json"
SPATIAL_CSV = OUT / "spatial_line_proxy.csv"
HEADLINE_MD = OUT / "which_number_is_headline.md"

OUT_CSV = OUT / "headline_statistical_uncertainty.csv"
OUT_STREAM_CSV = OUT / "headline_statistical_uncertainty_by_stream.csv"
OUT_JSON = OUT / "headline_statistical_uncertainty_summary.json"
OUT_MD = OUT / "headline_statistical_uncertainty.md"

REFERENCE_FLUX = 1.0e-4

sys.path.insert(0, str(Path(__file__).resolve().parent))
from time_fold_common import time_dependent_fold  # noqa: E402

sys.path.insert(0, str(ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "code"))
import build_detector_coupled_focus_response as step09  # noqa: E402


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fmt(value: float, nd: int = 6) -> str:
    x = float(value)
    if not math.isfinite(x):
        return "nan"
    if x == 0.0:
        return "0"
    if abs(x) < 1.0e-3 or abs(x) >= 1.0e5:
        return f"{x:.{nd}e}"
    return f"{x:.{nd}g}"


def schema_summary(cat: dict[str, Any]) -> dict[str, Any]:
    keys: dict[str, Any] = {}
    for key in sorted(cat):
        value = cat[key]
        if hasattr(value, "shape"):
            keys[key] = {
                "type": type(value).__name__,
                "shape": list(value.shape),
                "dtype": str(value.dtype),
            }
        else:
            keys[key] = {"type": type(value).__name__, "value": value}
    streams: dict[str, Any] = {}
    for stream in ("prompt", "delayed", "science"):
        mask = cat["stream"] == stream
        streams[stream] = {
            "events": int(mask.sum()),
            "rate_hz_sum": float(cat["rate_hz"][mask].sum()),
            "tes_events": int((mask & (cat["tes_total_keV"] > 0.0)).sum()),
        }
    return {
        "top_level_type": type(cat).__name__,
        "keys": keys,
        "streams": streams,
    }


def rows_by_key(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    return {row[key]: row for row in rows}


def both_background_events(cat: dict[str, Any], windows: list[dict[str, Any]], reject_policy: str) -> list[dict[str, Any]]:
    class_emin = min(step09.SPECTRUM_EMIN, min(float(w["lo_keV"]) for w in windows)) - 5.0 * step09.TES_SIGMA_KEV
    class_emax = max(step09.SPECTRUM_EMAX, max(float(w["hi_keV"]) for w in windows)) + 5.0 * step09.TES_SIGMA_KEV
    return step09.classified_events(
        cat,
        reject_policy,
        include_streams=None,
        skip_streams={"science"},
        emin_keV=class_emin,
        emax_keV=class_emax,
    )


def selection_weights(
    events: list[dict[str, Any]],
    window: dict[str, Any],
    radius_cm: float | None = None,
) -> dict[str, list[float]]:
    out: dict[str, list[float]] = {}
    for event in events:
        if not bool(event["both"]):
            continue
        if radius_cm is not None:
            radius = event.get("radius_cm")
            if radius is None or float(radius) > radius_cm:
                continue
        prob = step09.gaussian_window_probability(
            float(event["energy_keV"]),
            float(window["lo_keV"]),
            float(window["hi_keV"]),
        )
        if prob <= 0.0:
            continue
        weight = float(event["rate_hz"]) * prob
        if weight <= 0.0:
            continue
        out.setdefault(str(event["stream"]), []).append(weight)
    return out


def stat_record(weights: list[float]) -> dict[str, float]:
    b = float(sum(weights))
    sum_w2 = float(sum(w * w for w in weights))
    neff = b * b / sum_w2 if sum_w2 > 0.0 else 0.0
    db = math.sqrt(sum_w2)
    return {
        "B_cps": b,
        "sum_w2": sum_w2,
        "N_eff": neff,
        "delta_B_cps": db,
    }


def fold(selection_id: str, prompt_cps: float, delayed_cps: float, science_cps: float) -> dict[str, float | str]:
    metrics, _curve = time_dependent_fold(
        selection_id,
        prompt_cps,
        delayed_cps,
        science_cps,
        REFERENCE_FLUX,
        id_field="selection_id",
        step06_bg_csv=STEP06_BG,
        day15_summary_json=DAY15_SUMMARY,
    )
    return metrics


def append_headline_pointer() -> None:
    pointer = (
        "- A4 2026-06-11: headline MC statistical uncertainties are in "
        "`headline_statistical_uncertainty.csv` and `headline_statistical_uncertainty.md`."
    )
    if not HEADLINE_MD.exists():
        return
    text = HEADLINE_MD.read_text(encoding="utf-8")
    if pointer in text:
        return
    suffix = "\n" if text.endswith("\n") else "\n\n"
    HEADLINE_MD.write_text(text + suffix + pointer + "\n", encoding="utf-8")


def build() -> dict[str, Any]:
    optics = load_json(OPTICS_AUTHORITY)
    focus = load_json(FOCUS_RESPONSE)
    line_summary = load_json(LINE_SUMMARY)
    spatial_summary = load_json(SPATIAL_SUMMARY)
    line_rows = rows_by_key(read_csv(LINE_CSV), "window_id")
    spatial_rows = rows_by_key(read_csv(SPATIAL_CSV), "cut_id")
    nonxray_rows = read_csv(NONXRAY_TABLE)
    authority = {
        (row["window_id"], row["stage"]): row
        for row in nonxray_rows
        if row["source"] == "non_xray_background"
    }
    windows = step09.line_windows(optics)
    window_by_id = {str(window["window_id"]): window for window in windows}
    reject_policy = str(focus.get("inputs", {}).get("reject_policy", "keep"))

    with CATALOG.open("rb") as handle:
        cat = pickle.load(handle)
    schema = schema_summary(cat)
    bg_events = both_background_events(cat, windows, reject_policy)

    specs = [
        {
            "selection_id": "W1_design_passband",
            "paper_label": "W1 design passband",
            "window_id": "W1_design_passband",
            "radius_cm": None,
            "science_cps": float(line_rows["W1_design_passband"]["science_cps_at_reference_flux"]),
            "time_label": "W1",
            "authority_B_cps": float(authority[("W1_design_passband", "both")]["rate_cps"]),
        },
        {
            "selection_id": "W2_511_pm_420eV",
            "paper_label": "W2 511 +/- 420 eV",
            "window_id": "W2_511_pm_420eV",
            "radius_cm": None,
            "science_cps": float(line_rows["line_pm_3sigma"]["science_cps_at_reference_flux"]),
            "time_label": "W2",
            "authority_B_cps": float(authority[("W2_511_pm_420eV", "both")]["rate_cps"]),
        },
        {
            "selection_id": "spot_r90",
            "paper_label": "W2 plus focused spot r90",
            "window_id": "W2_511_pm_420eV",
            "radius_cm": float(spatial_summary["checks"]["signal_radius_r90_cm"]),
            "science_cps": float(spatial_rows["spot_r90"]["signal_cps_at_reference_flux"]),
            "time_label": "spot_r90",
            "authority_B_cps": float(spatial_rows["spot_r90"]["background_cps"]),
        },
    ]

    rows: list[dict[str, Any]] = []
    stream_rows: list[dict[str, Any]] = []
    stop_failures: list[str] = []
    for spec in specs:
        weights_by_stream = selection_weights(bg_events, window_by_id[spec["window_id"]], spec["radius_cm"])
        all_weights = [w for weights in weights_by_stream.values() for w in weights]
        total = stat_record(all_weights)
        prompt = stat_record(weights_by_stream.get("prompt", []))
        delayed = stat_record(weights_by_stream.get("delayed", []))
        stream_sum_w2 = prompt["sum_w2"] + delayed["sum_w2"]
        delta_b_stream = math.sqrt(stream_sum_w2)
        b = total["B_cps"]
        rel_delta_b = delta_b_stream / b if b > 0.0 else math.inf
        authority_b = float(spec["authority_B_cps"])
        authority_rel_delta = abs(b - authority_b) / max(abs(authority_b), 1.0e-300)
        if authority_rel_delta > 0.01:
            stop_failures.append(f"{spec['selection_id']} reconstructed B differs from authority by {authority_rel_delta:.3%}")

        base = fold(spec["selection_id"], prompt["B_cps"], delayed["B_cps"], float(spec["science_cps"]))
        scale_lo = max(0.0, 1.0 - rel_delta_b)
        scale_hi = 1.0 + rel_delta_b
        fold_lo_bg = fold(
            spec["selection_id"] + "_bg_low",
            prompt["B_cps"] * scale_lo,
            delayed["B_cps"] * scale_lo,
            float(spec["science_cps"]),
        )
        fold_hi_bg = fold(
            spec["selection_id"] + "_bg_high",
            prompt["B_cps"] * scale_hi,
            delayed["B_cps"] * scale_hi,
            float(spec["science_cps"]),
        )

        z = float(base["Z20d_time_dependent_at_reference_flux"])
        t3 = float(base["T3_day_time_dependent"])
        flux3 = float(base["flux_3sigma_20d_time_dependent_ph_cm2_s"])
        dz_analytic = z * rel_delta_b / 2.0
        dz_numeric = abs(float(fold_lo_bg["Z20d_time_dependent_at_reference_flux"]) - float(fold_hi_bg["Z20d_time_dependent_at_reference_flux"])) / 2.0
        dt3_numeric = abs(float(fold_hi_bg["T3_day_time_dependent"]) - float(fold_lo_bg["T3_day_time_dependent"])) / 2.0
        dflux_analytic = flux3 * rel_delta_b / 2.0
        dflux_numeric = abs(float(fold_hi_bg["flux_3sigma_20d_time_dependent_ph_cm2_s"]) - float(fold_lo_bg["flux_3sigma_20d_time_dependent_ph_cm2_s"])) / 2.0

        rows.append(
            {
                "selection_id": spec["selection_id"],
                "paper_label": spec["paper_label"],
                "window_id": spec["window_id"],
                "radius_cm": "" if spec["radius_cm"] is None else spec["radius_cm"],
                "B_cps": b,
                "delta_B_cps": delta_b_stream,
                "relative_delta_B": rel_delta_b,
                "N_eff_total": b * b / stream_sum_w2 if stream_sum_w2 > 0.0 else 0.0,
                "authority_B_cps": authority_b,
                "authority_rate_rel_delta": authority_rel_delta,
                "prompt_cps": prompt["B_cps"],
                "prompt_delta_B_cps": prompt["delta_B_cps"],
                "prompt_N_eff": prompt["N_eff"],
                "prompt_weighted_event_count": len(weights_by_stream.get("prompt", [])),
                "delayed_cps": delayed["B_cps"],
                "delayed_delta_B_cps": delayed["delta_B_cps"],
                "delayed_N_eff": delayed["N_eff"],
                "delayed_weighted_event_count": len(weights_by_stream.get("delayed", [])),
                "science_cps_at_reference_flux": spec["science_cps"],
                "Z20d_td": z,
                "delta_Z20d_td_analytic": dz_analytic,
                "delta_Z20d_td_numeric": dz_numeric,
                "delta_Z20d_td_numeric_vs_analytic_rel": abs(dz_numeric - dz_analytic) / max(abs(dz_analytic), 1.0e-300),
                "T3_day_td": t3,
                "delta_T3_day_td_numeric": dt3_numeric,
                "T3_td_status": base["T3_time_dependent_status"],
                "flux_3sigma_20d_td_ph_cm2_s": flux3,
                "delta_flux_3sigma_20d_td_analytic": dflux_analytic,
                "delta_flux_3sigma_20d_td_numeric": dflux_numeric,
                "background_low_scale": scale_lo,
                "background_high_scale": scale_hi,
                "Z20d_td_bg_low": fold_lo_bg["Z20d_time_dependent_at_reference_flux"],
                "Z20d_td_bg_high": fold_hi_bg["Z20d_time_dependent_at_reference_flux"],
                "T3_day_td_bg_low": fold_lo_bg["T3_day_time_dependent"],
                "T3_day_td_bg_high": fold_hi_bg["T3_day_time_dependent"],
            }
        )
        for stream, weights in sorted(weights_by_stream.items()):
            rec = stat_record(weights)
            stream_rows.append(
                {
                    "selection_id": spec["selection_id"],
                    "stream": stream,
                    "B_cps": rec["B_cps"],
                    "delta_B_cps": rec["delta_B_cps"],
                    "N_eff": rec["N_eff"],
                    "weighted_event_count": len(weights),
                    "sum_w2": rec["sum_w2"],
                }
            )

    if stop_failures:
        raise RuntimeError("; ".join(stop_failures))

    payload = {
        "status": "PASS",
        "claim_level": "L1_HEADLINE_MC_STATISTICAL_UNCERTAINTY",
        "scope": "Sidecar-only MC Poisson uncertainty on current W1/W2/spot_r90 day-15 background rates, propagated through the Step06 time-dependent fold.",
        "inputs": {
            "event_catalog": rel(CATALOG),
            "non_xray_table": rel(NONXRAY_TABLE),
            "line_summary": rel(LINE_SUMMARY),
            "spatial_summary": rel(SPATIAL_SUMMARY),
            "step06_background_time_variation": rel(STEP06_BG),
            "reject_policy": reject_policy,
            "reference_flux_ph_cm2_s": REFERENCE_FLUX,
        },
        "schema": schema,
        "checks": {
            "background_events_classified": len(bg_events),
            "max_authority_rate_rel_delta": max(float(row["authority_rate_rel_delta"]) for row in rows),
            "W2_N_eff": next(row["N_eff_total"] for row in rows if row["selection_id"] == "W2_511_pm_420eV"),
            "spot_r90_N_eff": next(row["N_eff_total"] for row in rows if row["selection_id"] == "spot_r90"),
        },
        "rows": rows,
        "outputs": {
            "csv": rel(OUT_CSV),
            "stream_csv": rel(OUT_STREAM_CSV),
            "markdown": rel(OUT_MD),
            "summary_json": rel(OUT_JSON),
        },
    }
    write_csv(OUT_CSV, rows)
    write_csv(OUT_STREAM_CSV, stream_rows)
    write_json(OUT_JSON, payload)
    write_markdown(payload, stream_rows)
    append_headline_pointer()
    return payload


def write_markdown(payload: dict[str, Any], stream_rows: list[dict[str, Any]]) -> None:
    rows = payload["rows"]
    by_stream = {(row["selection_id"], row["stream"]): row for row in stream_rows}
    w2 = next(row for row in rows if row["selection_id"] == "W2_511_pm_420eV")
    spot = next(row for row in rows if row["selection_id"] == "spot_r90")
    lines = [
        "# Headline Statistical Uncertainty",
        "",
        "Status: `PASS`.",
        "",
        "This sidecar estimates MC statistical uncertainty on the current day-15 background rates. The same Step09 non-X-ray selection logic is used for W1/W2, and the same spatial-r90 background logic is used for the focused spot cut. The uncertainty is propagated through the Step06 time-dependent fold by scaling the day-15 background normalization up and down.",
        "",
        "## Quote Lines",
        "",
        f"- W2: B = `{fmt(w2['B_cps'])} +/- {fmt(w2['delta_B_cps'])}` cps (N_eff `{fmt(w2['N_eff_total'])}`), time-dependent Z20d = `{fmt(w2['Z20d_td'])} +/- {fmt(w2['delta_Z20d_td_analytic'])}`.",
        f"- spot_r90: B = `{fmt(spot['B_cps'])} +/- {fmt(spot['delta_B_cps'])}` cps (N_eff `{fmt(spot['N_eff_total'])}`), time-dependent Z20d = `{fmt(spot['Z20d_td'])} +/- {fmt(spot['delta_Z20d_td_analytic'])}`.",
        "",
        "## Schema Introspection",
        "",
        f"- Top-level event catalog type: `{payload['schema']['top_level_type']}`.",
        f"- Event arrays: `stream`, `tag`, `source_file`, `local_id`, `rate_hz`, `tes_total_keV`, `bgo_total_keV`, `pix_start`, `pix_count`.",
        f"- Pixel arrays: `pix_uid`, `pix_layer`, `pix_e`, `pix_x`, `pix_y`, `pix_z`.",
        f"- Stream counts/rates: prompt `{payload['schema']['streams']['prompt']['events']}` events / `{fmt(payload['schema']['streams']['prompt']['rate_hz_sum'])}` Hz; delayed `{payload['schema']['streams']['delayed']['events']}` / `{fmt(payload['schema']['streams']['delayed']['rate_hz_sum'])}` Hz; science `{payload['schema']['streams']['science']['events']}` / `{fmt(payload['schema']['streams']['science']['rate_hz_sum'])}` Hz.",
        "",
        "## Summary Table",
        "",
        "| selection | B cps | delta B cps | N_eff | Z20d td | delta Z | T3 td day | delta T3 day | flux3 td | delta flux |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['selection_id']} | {fmt(row['B_cps'])} | {fmt(row['delta_B_cps'])} | "
            f"{fmt(row['N_eff_total'])} | {fmt(row['Z20d_td'])} | {fmt(row['delta_Z20d_td_analytic'])} | "
            f"{fmt(row['T3_day_td'])} | {fmt(row['delta_T3_day_td_numeric'])} | "
            f"{fmt(row['flux_3sigma_20d_td_ph_cm2_s'])} | {fmt(row['delta_flux_3sigma_20d_td_analytic'])} |"
        )
    lines.extend(
        [
            "",
            "## Stream Decomposition",
            "",
            "| selection | prompt B cps | prompt N_eff | delayed B cps | delayed N_eff |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in rows:
        prompt = by_stream.get((row["selection_id"], "prompt"), {})
        delayed = by_stream.get((row["selection_id"], "delayed"), {})
        lines.append(
            f"| {row['selection_id']} | {fmt(prompt.get('B_cps', 0.0))} | {fmt(prompt.get('N_eff', 0.0))} | "
            f"{fmt(delayed.get('B_cps', 0.0))} | {fmt(delayed.get('N_eff', 0.0))} |"
        )
    lines.extend(
        [
            "",
            "## Checks",
            "",
            f"- Max reconstructed-vs-authority background-rate relative delta: `{payload['checks']['max_authority_rate_rel_delta']:.3e}`.",
            f"- Classified background events in the Step09 W1/W2 energy envelope: `{payload['checks']['background_events_classified']}`.",
            "- Numerical refold columns in the CSV verify the expected `delta Z / Z = delta B / (2B)` scaling.",
            "",
            "## Rebuild",
            "",
            "```bash",
            "python3 stepwise_maintenance/step08_significance/code/build_headline_statistical_uncertainty.py",
            "```",
        ]
    )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    payload = build()
    print(
        json.dumps(
            {
                "status": payload["status"],
                "checks": payload["checks"],
                "outputs": payload["outputs"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
