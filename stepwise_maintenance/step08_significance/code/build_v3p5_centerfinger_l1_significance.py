#!/usr/bin/env python3
"""Build a v3p5 center-finger low-statistics Step08 sidecar.

This is a direct constant-rate expectation from the v3p5 Step05 physical
reference-flux block.  It does not replace the main Step06 time-dependent fold.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
STEP05 = ROOT / "stepwise_maintenance" / "step05_veto_time_axis" / "outputs_v3p5_centerfinger_l1" / "step05_v3p5_centerfinger_l1_response_summary.json"
OUT = ROOT / "stepwise_maintenance" / "step08_significance" / "outputs_v3p5_centerfinger_1of10"
SUMMARY_JSON = OUT / "step08_v3p5_centerfinger_l1_significance_summary.json"
SUMMARY_MD = OUT / "step08_v3p5_centerfinger_l1_significance.md"
WINDOW_CSV = OUT / "step08_v3p5_centerfinger_l1_windows.csv"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def fmt(value: Any, ndigits: int = 6) -> str:
    if value is None:
        return ""
    x = float(value)
    if not math.isfinite(x):
        return "inf" if x > 0 else "-inf"
    if x == 0.0:
        return "0"
    if abs(x) < 1.0e-3 or abs(x) >= 1.0e5:
        return f"{x:.{ndigits}e}"
    return f"{x:.{ndigits}g}"


def build_payload() -> dict[str, Any]:
    step05 = load_json(STEP05)
    problems: list[str] = []
    if step05.get("status") != "PASS_V3P5_STEP05_SIDE_ENTRY_COMPTON_TIME_AXIS_L1":
        problems.append(f"unexpected Step05 status: {step05.get('status')}")
    if "science_physical_normalization" not in step05:
        problems.append("Step05 is missing science_physical_normalization")

    windows: dict[str, Any] = {}
    for name, item in step05.get("windows", {}).items():
        phys = item.get("physical_reference_flux")
        if not phys:
            problems.append(f"{name} is missing physical_reference_flux")
            continue
        windows[name] = {
            "window_keV": item["window_keV"],
            "background_cps": phys["background_cps"],
            "signal_cps_at_reference_flux": phys["signal_cps_at_reference_flux"],
            "signal_to_background": phys["signal_to_background"],
            "source_counts_20d": phys["source_counts_20d"],
            "background_counts_20d": phys["background_counts_20d"],
            "Z20d_direct_s_over_sqrt_b": phys["Z20d_direct_s_over_sqrt_b"],
            "T3_day_constant_rate_direct": phys["T3_day_constant_rate_direct"],
            "T5_day_constant_rate_direct": phys["T5_day_constant_rate_direct"],
            "flux_3sigma_20d_ph_cm2_s": phys["flux_3sigma_20d_ph_cm2_s"],
            "low_stat_final_background_events": phys["low_stat_final_background_events"],
            "low_stat_background_relative_poisson_sigma_approx": phys["low_stat_background_relative_poisson_sigma_approx"],
            "prompt_background_cps": phys["prompt_background_cps"],
            "delayed_background_cps": phys["delayed_background_cps"],
        }

    headline_id = "w2_510p58_511p42" if "w2_510p58_511p42" in windows else next(iter(windows), None)
    headline = windows.get(headline_id, {}) if headline_id else {}
    if headline and float(headline.get("low_stat_final_background_events", 0)) < 50:
        problems.append("headline W2 background is based on fewer than 50 selected background events")
    warnings = [p for p in problems if "fewer than 50" in p]
    hard_problems = [p for p in problems if "fewer than 50" not in p]

    return {
        "status": "PASS_V3P5_STEP08_L1_DIRECT_EXPECTATION_1OF10" if not hard_problems else "FAIL_V3P5_STEP08_L1_DIRECT_EXPECTATION_1OF10",
        "claim_level": "L1 direct constant-rate expectation from v3p5 Step05 physical reference-flux rates; not a full Step06 mission-axis fold",
        "inputs": {
            "step05_summary": rel(STEP05),
            "step05_status": step05.get("status"),
        },
        "physical_normalization": step05.get("science_physical_normalization", {}),
        "headline_window": headline_id,
        "headline": headline,
        "windows": windows,
        "warnings": warnings,
        "problems": hard_problems,
        "pending": [
            "Regenerate full v3p5 Step06 mission-time variation and accidental-live fold.",
            "Increase v3p5 background statistics; the W2 low-stat background here has only 18 final selected events.",
            "Replace axisymmetric delayed-source RadialProfileBeam compression with exact-position delayed-source sampling before paper-facing numbers.",
        ],
    }


def write_csv(payload: dict[str, Any]) -> None:
    fields = [
        "window",
        "lo_keV",
        "hi_keV",
        "background_cps",
        "signal_cps_at_reference_flux",
        "signal_to_background",
        "source_counts_20d",
        "background_counts_20d",
        "Z20d_direct_s_over_sqrt_b",
        "T3_day_constant_rate_direct",
        "T5_day_constant_rate_direct",
        "flux_3sigma_20d_ph_cm2_s",
        "low_stat_final_background_events",
        "low_stat_background_relative_poisson_sigma_approx",
    ]
    with WINDOW_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for name, item in payload["windows"].items():
            lo, hi = item["window_keV"]
            row = {"window": name, "lo_keV": lo, "hi_keV": hi}
            row.update({key: item.get(key) for key in fields if key not in row})
            writer.writerow(row)


def markdown(payload: dict[str, Any]) -> str:
    norm = payload["physical_normalization"]
    headline = payload["headline"]
    lines = [
        "# Step08 v3p5 Center-Finger L1 Direct Significance",
        "",
        f"Status: `{payload['status']}`.",
        "",
        f"Claim level: {payload['claim_level']}.",
        "",
        "This sidecar turns the v3p5 Step05 direct expectation into a low-statistics significance checkpoint. It is intentionally conservative in scope: no Step06 time-dependent scaling, no accidental-live fold, and no profile-likelihood gain are claimed here.",
        "",
        "Normalization:",
        f"- reference flux: `{fmt(norm.get('reference_flux_ph_cm2_s'))} ph cm^-2 s^-1`",
        f"- optics: `{norm.get('optics_design_name')}`",
        f"- A_eff(511): `{fmt(norm.get('aeff_511_cm2'))} cm2`",
        f"- T_atm: `{fmt((norm.get('atmospheric_transmission') or {}).get('T_atm'))}`",
        f"- injection-plane rate: `{fmt(norm.get('rate_to_v3p5_injection_plane_s-1'))} s^-1`",
        "",
        "Headline:",
        f"- window: `{payload['headline_window']}`",
        f"- background: `{fmt(headline.get('background_cps'))} cps`; signal: `{fmt(headline.get('signal_cps_at_reference_flux'))} cps`",
        f"- 20-day direct Z: `{fmt(headline.get('Z20d_direct_s_over_sqrt_b'))}`",
        f"- constant-rate T3/T5: `{fmt(headline.get('T3_day_constant_rate_direct'))}` / `{fmt(headline.get('T5_day_constant_rate_direct'))}` day",
        f"- 20-day 3-sigma flux: `{fmt(headline.get('flux_3sigma_20d_ph_cm2_s'))} ph cm^-2 s^-1`",
        f"- low-stat selected background events: `{headline.get('low_stat_final_background_events')}`",
        "",
        "| window | background cps | signal cps | Z20d direct | T3 day | flux 3sigma 20d | low-stat B events |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, item in payload["windows"].items():
        lines.append(
            f"| {name} | {fmt(item['background_cps'])} | {fmt(item['signal_cps_at_reference_flux'])} | {fmt(item['Z20d_direct_s_over_sqrt_b'])} | {fmt(item['T3_day_constant_rate_direct'])} | {fmt(item['flux_3sigma_20d_ph_cm2_s'])} | {item['low_stat_final_background_events']} |"
        )
    if payload["warnings"]:
        lines.extend(["", "Warnings:"])
        for warning in payload["warnings"]:
            lines.append(f"- {warning}.")
    lines.extend(["", "Pending:"])
    for item in payload["pending"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            f"JSON: `{rel(SUMMARY_JSON)}`",
            f"CSV: `{rel(WINDOW_CSV)}`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    payload = build_payload()
    write_csv(payload)
    SUMMARY_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    SUMMARY_MD.write_text(markdown(payload), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "summary": rel(SUMMARY_JSON), "report": rel(SUMMARY_MD)}, indent=2, ensure_ascii=False))
    return 0 if payload["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
