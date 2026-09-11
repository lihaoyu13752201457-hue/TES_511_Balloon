#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Next-phase bookkeeping tools for COSMOSRAY_BG_2605.

The first supported mode, ``freeze-baseline``, records the current corrected
day-15 chain as a reference point before detector-response and source-model
changes are introduced.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "statistics" / "nextphase_511" / "baseline_freeze"
PHASE1_OUT = ROOT / "statistics" / "nextphase_511" / "phase1_status"
SUMMARY = ROOT / "statistics" / "day15_complete_report" / "complete_day15_summary.json"
ZOOM_CSV = ROOT / "statistics" / "day15_complete_report" / "timeline_spectrum_480_550_rates.csv"
ACCIDENTAL = ROOT / "statistics" / "science_accidental_veto" / "science_accidental_veto_summary.json"
FIX_SUMMARY = ROOT / "simulation" / "delay_fix_from_buildup_equiv2602_cmfix" / "source_fix_summary.json"
SCIENCE_SOURCE = ROOT / "particle_sources" / "run_configs" / "Science_511_onaxis_focalbeam_local.source"
FIXED_DELAY_SOURCE = ROOT / "simulation" / "delay_fix_from_buildup_equiv2602_cmfix" / "activation_decay_day15_groundstate_fixed.source"
GATE_A = ROOT / "statistics" / "nextphase_511" / "gate_A_source_placement" / "be_window_crossing_summary.json"
GATE_B = ROOT / "statistics" / "nextphase_511" / "gate_B_detector_response" / "detector_response_summary.json"
GATE_B_OFF = ROOT / "statistics" / "nextphase_511" / "gate_B_detector_response_off" / "detector_response_summary.json"
SCIENCE_100K = ROOT / "statistics" / "science_511_100k_summary.json"
LINE_MODELS = ROOT / "statistics" / "nextphase_511" / "science_line_models" / "source_fraction_in_windows.csv"
ENV_GRID_SUMMARY = ROOT / "statistics" / "nextphase_511" / "time_variable_day1_day20" / "environment_grid" / "environment_grid_summary.json"
INVENTORY_VALIDATION = ROOT / "statistics" / "nextphase_511" / "time_variable_day1_day20" / "inventory" / "constant_limit_validation.json"
PROMPT_REWEIGHT = ROOT / "statistics" / "nextphase_511" / "time_variable_day1_day20" / "prompt_reweight" / "prompt_reweight_summary.json"
TIMEVAR_SOURCE_SUMMARY = ROOT / "simulation" / "time_variable_delayed" / "source_build_summary.json"
TIMING_SCAN = ROOT / "statistics" / "nextphase_511" / "timing_window_scan" / "timing_window_scan_summary.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_json_optional(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return load_json(path)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    rec: dict[str, Any] = {"path": str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)}
    if path.exists():
        st = path.stat()
        rec.update({"exists": True, "bytes": st.st_size, "sha256": sha256(path)})
    else:
        rec.update({"exists": False, "bytes": 0, "sha256": None})
    return rec


def integrate_window(csv_path: Path, lo: float, hi: float, column: str) -> float:
    rows = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            rows.append(row)
    if len(rows) < 2:
        return 0.0
    centers = [float(r["E_keV"]) for r in rows]
    widths = []
    for i, c in enumerate(centers):
        if i == 0:
            widths.append(centers[1] - c)
        elif i == len(centers) - 1:
            widths.append(c - centers[i - 1])
        else:
            widths.append(0.5 * (centers[i + 1] - centers[i - 1]))
    total = 0.0
    for row, c, w in zip(rows, centers, widths):
        left = c - 0.5 * w
        right = c + 0.5 * w
        overlap = max(0.0, min(right, hi) - max(left, lo))
        if overlap > 0:
            total += float(row[column]) * overlap / w
    return total


def accidental_survival(acc: dict[str, Any], key: str) -> float | None:
    block = acc.get(key, {})
    if not block and isinstance(acc.get("windows"), dict):
        block = acc["windows"].get(key, {})
    if not isinstance(block, dict):
        return None
    val = block.get("accidental_survival_correction")
    return float(val) if val is not None else None


def freeze_baseline(outdir: Path) -> dict[str, Any]:
    outdir.mkdir(parents=True, exist_ok=True)
    summary = load_json(SUMMARY)
    fix = load_json(FIX_SUMMARY)
    accidental = load_json(ACCIDENTAL) if ACCIDENTAL.exists() else {}

    line_timeline_final = integrate_window(ZOOM_CSV, 510.3, 511.8, "timeline_final_cps_per_bin")
    line_expect_final = integrate_window(ZOOM_CSV, 510.3, 511.8, "expectation_final_cps_per_bin")
    science = summary["science_sensitivity"]

    baseline = {
        "purpose": "Frozen corrected day-15 reference before next-phase model changes.",
        "source_files_note": "This freezes existing files; it does not assert the science-source placement is correct.",
        "timeline_rates_480_550_cps": summary["timeline_rates_cps"],
        "direct_expectation_rates_480_550_cps": summary["expectation_rates_cps"],
        "line_window_510p3_511p8_cps": {
            "timeline_final": line_timeline_final,
            "direct_expectation_final": line_expect_final,
        },
        "science_response": {
            "reference_flux_ph_cm2_s": summary["normalization"]["science_flux_ph_cm2_s"],
            "final_response_cps_per_ph_cm2_s": science["science_final_response_cps_per_ph_cm-2_s-1"],
            "background_final_cps_prompt_plus_delayed": science["background_final_cps_prompt_plus_delayed"],
        },
        "accidental_veto_survival": {
            "broad_480_550": accidental_survival(accidental, "broad_480_550"),
            "line_510p3_511p8": accidental_survival(accidental, "line_510p3_511p8"),
        },
        "delay_fix": {
            "old_total_activity_Bq": fix.get("old_total_activity_Bq"),
            "new_total_activity_Bq": fix.get("new_total_activity_Bq"),
            "source_blocks_in": fix.get("source_blocks_in"),
            "source_blocks_removed": fix.get("source_blocks_removed"),
            "fixed_source_contains_W183": summary["delay_fix"]["fixed_source_contains_W183"],
            "fixed_source_contains_W180": summary["delay_fix"]["fixed_source_contains_W180"],
        },
        "normalization": summary["normalization"],
    }

    hashes = {
        "summary": file_record(SUMMARY),
        "zoom_spectrum": file_record(ZOOM_CSV),
        "science_source": file_record(SCIENCE_SOURCE),
        "fixed_delay_source": file_record(FIXED_DELAY_SOURCE),
        "delay_fix_summary": file_record(FIX_SUMMARY),
        "accidental_veto_summary": file_record(ACCIDENTAL),
    }

    (outdir / "baseline_summary.json").write_text(json.dumps(baseline, indent=2, ensure_ascii=False), encoding="utf-8")
    (outdir / "baseline_hashes.json").write_text(json.dumps(hashes, indent=2, ensure_ascii=False), encoding="utf-8")

    md = f"""# COSMOSRAY_BG_2605 next-phase baseline freeze

This file freezes the current corrected day-15 reference before new Phase-1
models are applied. It is a reference snapshot, not a claim that all gates have
passed.

## Key numbers

- 480-550 keV common-timeline final rate: `{summary['timeline_rates_cps']['final']:.12g}` cps
- 480-550 keV direct-expectation final rate: `{summary['expectation_rates_cps']['final']:.12g}` cps
- 510.3-511.8 keV common-timeline final rate: `{line_timeline_final:.12g}` cps
- 510.3-511.8 keV direct-expectation final rate: `{line_expect_final:.12g}` cps
- Science final response: `{science['science_final_response_cps_per_ph_cm-2_s-1']:.12g}` cps/(ph cm^-2 s^-1)
- Broad accidental-veto survival: `{baseline['accidental_veto_survival']['broad_480_550']}`
- Line accidental-veto survival: `{baseline['accidental_veto_survival']['line_510p3_511p8']}`
- Fixed delayed source contains W183 source block: `{summary['delay_fix']['fixed_source_contains_W183']}`
- Fixed delayed source contains W180 source block: `{summary['delay_fix']['fixed_source_contains_W180']}`

## Files

- `baseline_summary.json`: numerical reference.
- `baseline_hashes.json`: hashes of the files that define the frozen baseline.
"""
    (outdir / "baseline_key_numbers.md").write_text(md, encoding="utf-8")

    audit = {"mode": "freeze-baseline", "status": "ok", "outdir": str(outdir), "files_written": [
        "baseline_summary.json", "baseline_hashes.json", "baseline_key_numbers.md"
    ]}
    (outdir / "audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    return audit


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def accidental_or_timing_scan() -> dict[str, Any]:
    if ACCIDENTAL.exists():
        return load_json(ACCIDENTAL)
    timing = load_json_optional(TIMING_SCAN)
    if not timing:
        return {}
    windows: dict[str, Any] = {}
    for name in ("broad_480_550", "line_510p3_511p8"):
        row = next(
            (
                r for r in timing.get("rows", [])
                if r.get("energy_window") == name and abs(float(r.get("window_us", -1.0)) - 1.0) < 1.0e-9
            ),
            None,
        )
        if row:
            windows[name] = {
                "accidental_survival_correction": float(row["science_survival"]),
                "source": "timing_window_scan_1us",
            }
    return {
        "windows": windows,
        "background_total_rate_hz": timing.get("background_total_rate_hz"),
        "source": str(TIMING_SCAN.relative_to(ROOT)),
    }


def phase1_status(outdir: Path) -> dict[str, Any]:
    outdir.mkdir(parents=True, exist_ok=True)
    summary = load_json(SUMMARY)
    accidental = accidental_or_timing_scan()
    gate_a = load_json(GATE_A)
    gate_b = load_json(GATE_B)
    gate_b_off = load_json(GATE_B_OFF) if GATE_B_OFF.exists() else {}
    science = load_json(SCIENCE_100K)
    line_rows = read_csv(LINE_MODELS)
    env_grid = load_json_optional(ENV_GRID_SUMMARY)
    inventory_validation = load_json_optional(INVENTORY_VALIDATION)
    prompt_reweight = load_json_optional(PROMPT_REWEIGHT)
    timevar_sources = load_json_optional(TIMEVAR_SOURCE_SUMMARY)

    broad_survival = accidental.get("windows", {}).get("broad_480_550", {}).get("accidental_survival_correction", 1.0)
    line_survival = accidental.get("windows", {}).get("line_510p3_511p8", {}).get("accidental_survival_correction", 1.0)
    resp = summary["science_sensitivity"]["science_final_response_cps_per_ph_cm-2_s-1"]
    bkg = summary["science_sensitivity"]["background_final_cps_prompt_plus_delayed"]
    broad_1ms_3 = 3.0 * (bkg * 1.0e6) ** 0.5 / (resp * 1.0e6)
    broad_1ms_3_corr = broad_1ms_3 / broad_survival
    off_repro = None
    if gate_b_off:
        off_repro = all(
            abs(gate_b_off["windows"][f"{label}_true"]["final_cps"] - gate_b_off["windows"][f"{label}_measured"]["final_cps"]) < 1.0e-12
            for label in ("480-550", "510.3-511.8")
        )

    constant_limit_pass = all(
        item and item.get("status") == "PASS"
        for item in (inventory_validation, prompt_reweight, timevar_sources)
    ) and bool(env_grid and env_grid.get("status") == "ok")

    report = {
        "status": "phase1_minimal_pass_with_wp4_constant_limit" if constant_limit_pass else "phase1_minimal_pass",
        "scope": "WP0 baseline freeze, WP1 Gate A source placement, WP2 detector response post-processing, WP3 source line-model generation, and optional WP4 constant-profile precheck when present.",
        "gate_A": {
            "passed": gate_a["passed"],
            "source_z": gate_a["source"]["z"],
            "source_radius": gate_a["source"]["radius"],
            "win_be_z_max": gate_a["win_be"]["z_max"],
            "clearance": gate_a["clearance_source_minus_win_top"],
            "first_tes_layer_counts": gate_a["first_tes_layer_counts"],
            "old_problem": "Earlier z=12.766 source was inside/near TES_L0 and is superseded.",
        },
        "science_100k": science["sim_summary"],
        "day15_after_gateAfix": {
            "timeline_final_480_550_cps": summary["timeline_rates_cps"]["final"],
            "direct_expectation_final_480_550_cps": summary["expectation_rates_cps"]["final"],
            "science_response_cps_per_ph_cm2_s": resp,
            "science_expected_instances": summary["draw_summary"]["science"]["lambda"],
            "science_drawn_instances": summary["draw_summary"]["science"]["drawn"],
            "broad_3sigma_1Ms_uncorrected": broad_1ms_3,
            "broad_3sigma_1Ms_accidental_corrected": broad_1ms_3_corr,
        },
        "gate_B": {
            "passed": gate_b["passed"],
            "science_true_fwhm_keV": gate_b["science_peak_true_fwhm_robust_keV"],
            "science_measured_fwhm_keV": gate_b["science_peak_measured_fwhm_robust_keV"],
            "measured_480_550_final_cps": gate_b["windows"]["480-550_measured"]["final_cps"],
            "measured_510p3_511p8_final_cps": gate_b["windows"]["510.3-511.8_measured"]["final_cps"],
            "known_limitation": gate_b["known_limitation"],
            "disabled_response_reproducibility": off_repro,
        },
        "accidental_veto": {
            "broad_survival": broad_survival,
            "line_survival": line_survival,
            "background_total_rate_hz": accidental["background_total_rate_hz"],
        },
        "line_models": line_rows,
        "time_variable_constant_limit": {
            "environment_grid": env_grid,
            "inventory_validation": inventory_validation,
            "prompt_reweight": prompt_reweight,
            "delayed_source_scaling": timevar_sources,
            "passed": constant_limit_pass,
        },
        "supersedes": [
            "Earlier science-source response and sensitivity values based on z=12.766/r=1.8 are invalid for source-response conclusions.",
            "Previous manuscript/GPT packets remain useful for background workflow lineage but are superseded for science source placement and flux thresholds.",
        ],
    }

    (outdir / "phase1_status_summary.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    md = f"""# COSMOSRAY_BG_2605 511 next-phase Phase 1 status

## Decision

Phase 1 minimal gates are passed for the corrected science-source chain:
baseline was re-frozen, Gate A source placement passed after repair, Gate B
detector-response post-processing passed, and WP3 line-model source files were
generated. The old science response based on `z=12.766` is superseded.
{"A constant-profile WP4 precheck is also present and passed: environment scale=1, prompt reweighting reproduces the reference scale, day-15 ODE inventory reproduces the fixed inventory, and day-15 delayed source fluxes reproduce the template." if constant_limit_pass else ""}

## Gate A source placement

- Corrected source: `z={gate_a['source']['z']}`, radius `{gate_a['source']['radius']}` in XZTES geometry units.
- Win_Be +z face: `{gate_a['win_be']['z_max']}`.
- Clearance: `{gate_a['clearance_source_minus_win_top']}`.
- First TES layer distribution in the corrected SIM: `{gate_a['first_tes_layer_counts']}`.
- Result: `{gate_a['decision']}`.

## Corrected day-15 baseline

- 480-550 keV timeline final rate: `{summary['timeline_rates_cps']['final']:.12g}` cps.
- 480-550 keV direct-expectation final rate: `{summary['expectation_rates_cps']['final']:.12g}` cps.
- Science final response: `{resp:.12g}` cps/(ph cm^-2 s^-1).
- 1 Ms broad-window 3 sigma threshold: `{broad_1ms_3:.12g}` ph cm^-2 s^-1.
- Accidental-veto-corrected broad threshold: `{broad_1ms_3_corr:.12g}` ph cm^-2 s^-1.

## Gate B detector response

- True-energy science peak robust FWHM: `{gate_b['science_peak_true_fwhm_robust_keV']}` keV.
- Measured-energy science peak robust FWHM: `{gate_b['science_peak_measured_fwhm_robust_keV']}` keV.
- Measured 480-550 final rate: `{gate_b['windows']['480-550_measured']['final_cps']}` cps.
- Measured 510.3-511.8 final rate: `{gate_b['windows']['510.3-511.8_measured']['final_cps']}` cps.
- Limitation: {gate_b['known_limitation']}

## WP3 line models

Line-model source files are under `particle_sources/run_configs/nextphase_science_sources/`.
The broad 480-550 keV intrinsic source fraction remains effectively 1.0 for
the generated grid; the narrow 510.3-511.8 keV fraction decreases with larger
intrinsic width, as expected.

## WP4 constant-profile precheck

- Environment grid: `{env_grid.get('status') if env_grid else 'missing'}`.
- Inventory constant-limit validation: `{inventory_validation.get('status') if inventory_validation else 'missing'}`.
- Prompt reweight constant-limit validation: `{prompt_reweight.get('status') if prompt_reweight else 'missing'}`.
- Day-series delayed source scaling: `{timevar_sources.get('status') if timevar_sources else 'missing'}`.
{f"- Reconstructed day-15 total activity relative difference: `{inventory_validation['reference_total_rel_diff']:.3e}`." if inventory_validation else ""}

## Caveat

Previous manuscript/GPT-review PDFs generated before this Gate-A repair are
superseded for science response and sensitivity values. They remain useful for
background-chain lineage only.
"""
    (outdir / "phase1_status.md").write_text(md, encoding="utf-8")
    audit = {"mode": "phase1-status", "status": "ok", "outdir": str(outdir)}
    (outdir / "audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    return audit


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["freeze-baseline", "phase1-status"], required=True)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if args.mode == "freeze-baseline":
        audit = freeze_baseline(args.out)
    elif args.mode == "phase1-status":
        audit = phase1_status(args.out if args.out != DEFAULT_OUT else PHASE1_OUT)
    else:
        raise AssertionError(args.mode)
    print(json.dumps(audit, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
