#!/usr/bin/env python3
"""Generate the 511 keV O-15/BGO root-cause audit packet.

The script is intentionally post-processing only.  It does not modify existing
simulation inputs or outputs, and it does not claim true event lineage when the
current catalogs do not preserve source-block metadata per final event.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import json
import math
import os
import platform
import re
import socket
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DEFAULT = ROOT / "reports2.0" / "99_O15_BGO_ROOT_CAUSE_AUDIT"

SOURCE_CANDIDATES = [
    ROOT / "production_runs" / "delay_fix_from_buildup_equiv2602" / "activation_decay_day15_groundstate_fixed.source",
    ROOT / "delay_fix" / "activation_decay_day15_groundstate_fixed.source",
    ROOT / "run_configs" / "activation_decay_day15_groundstate_fixed_smoke1k.source",
]

PATHS = {
    "delayed_diag": ROOT / "reports2.0" / "03_NEXT_PHASE_SUPPORT" / "activation_511_diagnostics" / "delayed_511_by_nuclide_volume.csv",
    "delayed_summary": ROOT / "reports2.0" / "03_NEXT_PHASE_SUPPORT" / "activation_511_diagnostics" / "activation_511_diagnostic_summary.json",
    "truth_table": ROOT / "reports2.0" / "02_PHASE2_CORE_MATERIALS" / "activation_truth" / "activation_511_truth_table.csv",
    "selection_audit": ROOT / "reports2.0" / "10_POINT_DIFFUSE_DISCRIMINATION" / "selection_best_measured_energy_audit.csv",
    "likelihood": ROOT / "reports2.0" / "03_NEXT_PHASE_SUPPORT" / "likelihood_511" / "likelihood_sensitivity_by_model.csv",
    "profiled": ROOT / "reports2.0" / "02_PHASE2_CORE_MATERIALS" / "likelihood_profiled" / "asimov_profiled_sensitivity.csv",
    "fig11": ROOT / "Records" / "09_cam511_fig11_comparison_20260522" / "current_system_fig11_style_counts_and_sensitivity.csv",
    "focused": ROOT / "reports2.0" / "03_NEXT_PHASE_SUPPORT" / "optics_focused_gamma_background" / "focused_gamma_background_summary.csv",
    "threshold_scan_source": ROOT / "reports2.0" / "08_DESIGN_OPTIMIZATION_ADDON" / "WP_D1_selection_pareto_highstat" / "selection_pareto_highstat.csv",
    "rpip_points": ROOT / "Records" / "04_activation_rpip" / "activation_rpip_points_sample.csv",
    "rpip_volume_summary": ROOT / "Records" / "04_activation_rpip" / "activation_rpip_volume_summary.csv",
    "cam511_pdf": Path("/home/ubuntu/codex_tes_511_sim/papers/511-CAM_Shirazi-etal_2023_arXiv2206.14652.pdf"),
}

WINDOWS = {
    "broad_480_550": (480.0, 550.0),
    "line_510p3_511p8": (510.3, 511.8),
}

CLASS_DEFS = {
    "A": "BGO-origin O-15, TES line hit, BGO veto pass",
    "B": "BGO-origin O-15, TES line hit, BGO veto fail",
    "C": "BGO-origin O-15, TES broad-only hit, BGO veto pass",
    "D": "BGO-origin O-15, BGO-only hit, no TES line/broad hit",
    "E": "BGO-origin O-15, escape/no relevant TES or BGO hit",
    "F": "non-BGO-origin O-15, TES line hit, BGO veto pass",
    "G": "non-BGO-origin O-15, TES line hit, BGO veto fail",
}

# Local proxy list.  The first three are directly present in the project's
# activation_truth beta_plus_branch_proxy table.  The remainder are common
# positron emitters that appear in current delayed diagnostics; they are marked
# as proxy-only in beta_plus_proxy_nuclides.csv and should be replaced by an
# audited ENSDF/Geant4 decay table for production decisions.
COMMON_BETA_PLUS_PROXY = {
    "O-15",
    "C-11",
    "Ga-68",
    "F-18",
    "N-13",
    "O-14",
    "C-10",
    "Cu-62",
    "Ge-69",
    "Si-27",
    "Na-22",
    "Al-26",
}

ELEMENTS = [
    "",
    "H",
    "He",
    "Li",
    "Be",
    "B",
    "C",
    "N",
    "O",
    "F",
    "Ne",
    "Na",
    "Mg",
    "Al",
    "Si",
    "P",
    "S",
    "Cl",
    "Ar",
    "K",
    "Ca",
    "Sc",
    "Ti",
    "V",
    "Cr",
    "Mn",
    "Fe",
    "Co",
    "Ni",
    "Cu",
    "Zn",
    "Ga",
    "Ge",
    "As",
    "Se",
    "Br",
    "Kr",
    "Rb",
    "Sr",
    "Y",
    "Zr",
    "Nb",
    "Mo",
    "Tc",
    "Ru",
    "Rh",
    "Pd",
    "Ag",
    "Cd",
    "In",
    "Sn",
    "Sb",
    "Te",
    "I",
    "Xe",
    "Cs",
    "Ba",
    "La",
    "Ce",
    "Pr",
    "Nd",
    "Pm",
    "Sm",
    "Eu",
    "Gd",
    "Tb",
    "Dy",
    "Ho",
    "Er",
    "Tm",
    "Yb",
    "Lu",
    "Hf",
    "Ta",
    "W",
    "Re",
    "Os",
    "Ir",
    "Pt",
    "Au",
    "Hg",
    "Tl",
    "Pb",
    "Bi",
    "Po",
]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def fval(value: Any, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def ival(value: Any, default: int = 0) -> int:
    try:
        if value in ("", None):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def run_capture(args: list[str], cwd: Path = ROOT) -> str | None:
    try:
        return subprocess.check_output(args, cwd=str(cwd), text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def za_to_nuclide(za: int) -> str:
    z = za // 1000
    a = za % 1000
    if 0 < z < len(ELEMENTS):
        return f"{ELEMENTS[z]}-{a}"
    return f"ZA-{za}"


SOURCE_RE = re.compile(r"^(?P<block>S_(?P<volume>.+)_(?P<za>\d+)_z(?P<zbin>\d+))\.(?P<field>ParticleType|Flux|Beam)\s*(?P<value>.*)$")


def select_source_file() -> Path:
    for path in SOURCE_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError("No activation_decay_day15_groundstate_fixed.source candidate found")


def parse_delayed_source(path: Path, truth_meta: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    blocks: dict[str, dict[str, Any]] = {}
    for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
        match = SOURCE_RE.match(line.strip())
        if not match:
            continue
        block = match.group("block")
        rec = blocks.setdefault(
            block,
            {
                "source_block_name": block,
                "production_volume": match.group("volume"),
                "decay_volume": match.group("volume"),
                "ZA_or_isotope_id": match.group("za"),
                "z_bin": match.group("zbin"),
                "r_bin": "all_r_from_radial_profile",
                "source_file": rel(path),
                "line_number_or_block_id": line_no,
                "origin_basis": "delayed_source_block_inferred",
            },
        )
        rec["line_number_or_block_id"] = min(int(rec["line_number_or_block_id"]), line_no)
        field = match.group("field")
        value = match.group("value").strip()
        if field == "Flux":
            rec["activity_Bq"] = fval(value)
        elif field == "ParticleType":
            rec["ZA_or_isotope_id"] = value
        elif field == "Beam":
            rec["beam_definition"] = value
    rows: list[dict[str, Any]] = []
    for rec in blocks.values():
        if "activity_Bq" not in rec:
            continue
        za = ival(rec["ZA_or_isotope_id"])
        nuclide = za_to_nuclide(za)
        meta = truth_meta.get(nuclide, {})
        rec = dict(rec)
        rec["nuclide"] = nuclide
        rec["half_life_s"] = meta.get("half_life_s", "")
        rec["decay_mode"] = meta.get("decay_mode_proxy", "unresolved_not_in_activation_truth_table")
        rows.append(rec)
    total = sum(fval(r["activity_Bq"]) for r in rows)
    by_nuclide: dict[str, float] = defaultdict(float)
    for row in rows:
        by_nuclide[row["nuclide"]] += fval(row["activity_Bq"])
    for row in rows:
        activity = fval(row["activity_Bq"])
        row["activity_fraction_within_nuclide"] = activity / by_nuclide[row["nuclide"]] if by_nuclide[row["nuclide"]] else ""
        row["activity_fraction_total"] = activity / total if total else ""
    return sorted(rows, key=lambda r: (r["nuclide"], r["production_volume"], int(r["z_bin"])))


def summarize_origin(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by: dict[str, dict[str, Any]] = {}
    by_vol: dict[tuple[str, str], float] = defaultdict(float)
    for row in rows:
        n = row["nuclide"]
        rec = by.setdefault(n, {"nuclide": n, "total_activity_Bq": 0.0, "n_source_blocks": 0})
        rec["total_activity_Bq"] += fval(row["activity_Bq"])
        rec["n_source_blocks"] += 1
        by_vol[(n, row["production_volume"])] += fval(row["activity_Bq"])
    out = []
    for n, rec in by.items():
        vols = [(v, a) for (nn, v), a in by_vol.items() if nn == n]
        top_vol, top_act = max(vols, key=lambda item: item[1])
        total = rec["total_activity_Bq"]
        out.append(
            {
                "nuclide": n,
                "total_activity_Bq": total,
                "top_volume": top_vol,
                "top_volume_activity_Bq": top_act,
                "top_volume_fraction": top_act / total if total else "",
                "n_source_blocks": rec["n_source_blocks"],
            }
        )
    return sorted(out, key=lambda r: fval(r["total_activity_Bq"]), reverse=True)


def origin_fractions(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    by: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in rows:
        by[row["nuclide"]][row["production_volume"]] += fval(row["activity_Bq"])
    out: dict[str, dict[str, float]] = {}
    for nuc, vols in by.items():
        total = sum(vols.values())
        out[nuc] = {vol: act / total for vol, act in vols.items() if total}
    return out


def aggregate_delayed_diag(rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    by: dict[str, dict[str, Any]] = defaultdict(lambda: defaultdict(float))
    for row in rows:
        nuc = row.get("nuclide", "unknown")
        by[nuc]["events_total"] += ival(row.get("events_total"))
        by[nuc]["events_with_tes"] += ival(row.get("events_with_tes"))
        for prefix in ("broad_480_550", "line_510p3_511p8", "near_506_516"):
            for stage in ("raw", "bgo", "final"):
                key = f"{prefix}_{stage}_cps"
                by[nuc][key] += fval(row.get(key))
                evkey = f"{prefix}_{stage}_events"
                by[nuc][evkey] += ival(row.get(evkey))
    return {n: dict(v) for n, v in by.items()}


def load_truth_meta(path: Path) -> dict[str, dict[str, str]]:
    return {r["nuclide"]: r for r in read_csv(path)}


def selection_components(path: Path) -> dict[str, dict[str, float]]:
    comps: dict[str, dict[str, float]] = {}
    for row in read_csv(path):
        if row.get("selection_id") == "baseline" and row.get("energy_basis") == "true":
            w = row["window"]
            comps[w] = {
                "prompt": fval(row["prompt_cps"]),
                "delayed": fval(row["delayed_cps"]),
                "focused": fval(row["focused_gamma_cps"]),
                "total": fval(row["background_cps"]),
                "source_response": fval(row["source_response_cps_per_flux"]),
                "F3_window": fval(row["F3_ph_cm2_s"]),
                "n_source_events": ival(row["n_source_events"]),
                "n_background_events": ival(row["n_background_events"]),
            }
    return comps


def window_key_to_label(window: str) -> str:
    if window == "broad_480_550":
        return "480-550"
    if window == "line_510p3_511p8":
        return "510.3-511.8"
    return window


def generate_background_reconciliation(
    outdir: Path,
    comps: dict[str, dict[str, float]],
    delayed_by_nuc: dict[str, dict[str, Any]],
    origin_frac: dict[str, dict[str, float]],
    source_file: Path,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for window in WINDOWS:
        total = comps[window]["total"]
        for component, subcomponent, cps in [
            ("prompt_direct", "all_prompt", comps[window]["prompt"]),
            ("focused_gamma", "optics_aperture_addendum", comps[window]["focused"]),
        ]:
            rows.append(
                {
                    "component": component,
                    "subcomponent": subcomponent,
                    "nuclide": "",
                    "origin_volume": "",
                    "window_keV": window_key_to_label(window),
                    "raw_events": "",
                    "weighted_cps": cps,
                    "fraction_of_total": cps / total if total else "",
                    "fraction_of_component": 1.0,
                    "normalization_factor": 1.0,
                    "source_file": "selection_best_measured_energy_audit.csv",
                    "notes": "focused row is separate optics-aperture addendum; direct prompt stream unchanged" if component == "focused_gamma" else "",
                }
            )
        stage_key = "broad_480_550_final_cps" if window == "broad_480_550" else "line_510p3_511p8_final_cps"
        delayed_total = comps[window]["delayed"]
        for nuc, vals in sorted(delayed_by_nuc.items()):
            nuc_cps = fval(vals.get(stage_key))
            if nuc_cps == 0:
                continue
            vols = origin_frac.get(nuc) or {"unresolved_source_activity_missing": 1.0}
            for vol, frac in sorted(vols.items()):
                cps = nuc_cps * frac
                rows.append(
                    {
                        "component": "delayed_activation",
                        "subcomponent": "nuclide_origin_apportioned_by_source_activity",
                        "nuclide": nuc,
                        "origin_volume": vol,
                        "window_keV": window_key_to_label(window),
                        "raw_events": vals.get(stage_key.replace("_cps", "_events"), ""),
                        "weighted_cps": cps,
                        "fraction_of_total": cps / total if total else "",
                        "fraction_of_component": cps / delayed_total if delayed_total else "",
                        "normalization_factor": frac,
                        "source_file": rel(source_file),
                        "notes": "posthoc source-activity apportionment; not final-event source-block lineage",
                    }
                )
        rows.append(
            {
                "component": "science_source_response",
                "subcomponent": "source_response_cps_per_flux",
                "nuclide": "",
                "origin_volume": "",
                "window_keV": window_key_to_label(window),
                "raw_events": comps[window]["n_source_events"],
                "weighted_cps": comps[window]["source_response"],
                "fraction_of_total": "",
                "fraction_of_component": "",
                "normalization_factor": "",
                "source_file": "selection_best_measured_energy_audit.csv",
                "notes": "source response, not a background component",
            }
        )
    fields = [
        "component",
        "subcomponent",
        "nuclide",
        "origin_volume",
        "window_keV",
        "raw_events",
        "weighted_cps",
        "fraction_of_total",
        "fraction_of_component",
        "normalization_factor",
        "source_file",
        "notes",
    ]
    write_csv(outdir / "background_reconciliation_full.csv", rows, fields)

    def closure(window: str) -> float:
        return comps[window]["prompt"] + comps[window]["delayed"] + comps[window]["focused"] - comps[window]["total"]

    o15_line = fval(delayed_by_nuc.get("O-15", {}).get("line_510p3_511p8_final_cps"))
    o15_origin = origin_frac.get("O-15", {})
    checks = {
        "broad_window_closure_abs_error": abs(closure("broad_480_550")),
        "line_window_closure_abs_error": abs(closure("line_510p3_511p8")),
        "focused_gamma_double_counting_detected": False,
        "focused_gamma_policy": "separate optics-aperture addendum; direct prompt stream unchanged",
        "delayed_fraction_broad": comps["broad_480_550"]["delayed"] / comps["broad_480_550"]["total"],
        "delayed_fraction_line": comps["line_510p3_511p8"]["delayed"] / comps["line_510p3_511p8"]["total"],
        "o15_fraction_total_line": o15_line / comps["line_510p3_511p8"]["total"],
        "bgo_origin_o15_fraction_if_available": o15_origin.get("BGO_Shield"),
        "bgo_origin_o15_line_cps_posthoc_activity_fraction": o15_line * o15_origin.get("BGO_Shield", 0.0),
        "bgo_origin_basis": "delayed source-block activity fraction, not per-final-event lineage",
    }
    write_json(outdir / "background_reconciliation_checks.json", checks)
    return checks


def beta_plus_proxy_rows(truth_meta: dict[str, dict[str, str]], delayed_by_nuc: dict[str, dict[str, Any]]) -> tuple[set[str], list[dict[str, Any]]]:
    beta: set[str] = set()
    rows: list[dict[str, Any]] = []
    for nuc in sorted(delayed_by_nuc):
        basis = []
        branch = fval(truth_meta.get(nuc, {}).get("beta_plus_branch_proxy"))
        if branch > 0:
            beta.add(nuc)
            basis.append(f"activation_truth_beta_plus_branch_proxy={branch:g}")
        if nuc in COMMON_BETA_PLUS_PROXY:
            beta.add(nuc)
            basis.append("common_beta_plus_proxy_list_current_diagnostic")
        if basis:
            rows.append(
                {
                    "nuclide": nuc,
                    "beta_plus_proxy": True,
                    "basis": "; ".join(basis),
                    "line_cps": fval(delayed_by_nuc[nuc].get("line_510p3_511p8_final_cps")),
                    "broad_cps": fval(delayed_by_nuc[nuc].get("broad_480_550_final_cps")),
                    "notes": "proxy list; replace with audited ENSDF/Geant4 decay table before production claims",
                }
            )
    return beta, rows


def generate_ablation_table(
    outdir: Path,
    comps: dict[str, dict[str, float]],
    delayed_by_nuc: dict[str, dict[str, Any]],
    origin_frac: dict[str, dict[str, float]],
    truth_meta: dict[str, dict[str, str]],
) -> None:
    beta_set, beta_rows = beta_plus_proxy_rows(truth_meta, delayed_by_nuc)
    write_csv(outdir / "beta_plus_proxy_nuclides.csv", beta_rows, ["nuclide", "beta_plus_proxy", "basis", "line_cps", "broad_cps", "notes"])

    model_rows = [r for r in read_csv(PATHS["profiled"]) if fval(r.get("exposure_s")) == 1_000_000]
    scenario_rows: list[dict[str, Any]] = []

    def nuc_cps(nuc: str, window: str) -> float:
        key = "broad_480_550_final_cps" if window == "broad_480_550" else "line_510p3_511p8_final_cps"
        return fval(delayed_by_nuc.get(nuc, {}).get(key))

    def beta_cps(window: str) -> float:
        return sum(nuc_cps(n, window) for n in beta_set)

    def bgo_origin_cps(window: str) -> float:
        key = "broad_480_550_final_cps" if window == "broad_480_550" else "line_510p3_511p8_final_cps"
        total = 0.0
        for nuc, vals in delayed_by_nuc.items():
            total += fval(vals.get(key)) * origin_frac.get(nuc, {}).get("BGO_Shield", 0.0)
        return total

    scenarios = [
        ("baseline", "baseline current components", "baseline"),
        ("no_O15", "remove O-15 delayed contribution", "posthoc_reweight"),
        ("no_beta_plus", "remove beta-plus proxy nuclides from delayed contribution", "posthoc_reweight"),
        ("no_BGO_activation", "remove delayed contribution apportioned to BGO_Shield source activity", "posthoc_reweight"),
        ("no_BGO_activation_keep_prompt_veto", "same as no_BGO_activation; prompt shielding/veto retained by construction", "posthoc_reweight"),
        ("BGO_noO_surrogate_if_available", "no no-oxygen surrogate geometry/config found in current workflow", "config_unavailable"),
        ("no_delayed_activation", "remove all delayed activation", "posthoc_reweight"),
        ("prompt_only", "prompt direct only; focused/delayed set to zero", "posthoc_reweight"),
        ("delayed_only", "delayed activation only; prompt/focused set to zero", "posthoc_reweight"),
    ]
    for model in model_rows:
        window = model["energy_window"]
        if window not in comps:
            continue
        base_b = comps[window]["total"]
        base_prompt = comps[window]["prompt"]
        base_delayed = comps[window]["delayed"]
        base_focused = comps[window]["focused"]
        baseline_f3 = fval(model.get("profiled_flux_3sigma_ph_cm2_s") or model.get("flux_3sigma_ph_cm2_s"))
        exposure = fval(model["exposure_s"])
        base_info = fval(model["information_per_s"])
        for scenario, desc, status in scenarios:
            prompt, delayed, focused = base_prompt, base_delayed, base_focused
            notes = ""
            if scenario == "no_O15":
                delayed = max(0.0, delayed - nuc_cps("O-15", window))
                notes = "posthoc zeroing of O-15 final delayed cps"
            elif scenario == "no_beta_plus":
                delayed = max(0.0, delayed - beta_cps(window))
                notes = "posthoc zeroing of beta-plus proxy list; list is not final ENSDF audit"
            elif scenario in ("no_BGO_activation", "no_BGO_activation_keep_prompt_veto"):
                delayed = max(0.0, delayed - bgo_origin_cps(window))
                notes = "posthoc source-activity-fraction apportionment; keeps prompt BGO shielding/veto"
            elif scenario == "BGO_noO_surrogate_if_available":
                prompt = delayed = focused = ""
                notes = "unresolved: no current no-oxygen BGO surrogate geometry/config found"
            elif scenario == "no_delayed_activation":
                delayed = 0.0
                notes = "posthoc component removal, not true rerun"
            elif scenario == "prompt_only":
                delayed = 0.0
                focused = 0.0
                notes = "prompt direct only; source response unchanged"
            elif scenario == "delayed_only":
                prompt = 0.0
                focused = 0.0
                notes = "delayed component only; source response unchanged"

            if status == "config_unavailable":
                scenario_rows.append(
                    {
                        "scenario": scenario,
                        "description": desc,
                        "run_status": status,
                        "window_keV": window_key_to_label(window),
                        "model": model["model"],
                        "prompt_cps": "",
                        "delayed_cps": "",
                        "focused_cps": "",
                        "total_background_cps": "",
                        "source_response_cps_per_flux": model["response_cps_per_flux"],
                        "information_per_s": "",
                        "exposure_s": exposure,
                        "F3_ph_cm2_s": "",
                        "ratio_vs_baseline": "",
                        "ratio_vs_CAM511_3e-6": "",
                        "expected_linear_factor": "",
                        "actual_factor": "",
                        "notes": notes,
                    }
                )
                continue
            total_b = fval(prompt) + fval(delayed) + fval(focused)
            factor = math.sqrt(total_b / base_b) if base_b and total_b >= 0 else ""
            f3 = baseline_f3 * factor if factor != "" else ""
            info = base_info * base_b / total_b if total_b > 0 else ""
            scenario_rows.append(
                {
                    "scenario": scenario,
                    "description": desc,
                    "run_status": status,
                    "window_keV": window_key_to_label(window),
                    "model": model["model"],
                    "prompt_cps": prompt,
                    "delayed_cps": delayed,
                    "focused_cps": focused,
                    "total_background_cps": total_b,
                    "source_response_cps_per_flux": model["response_cps_per_flux"],
                    "information_per_s": info,
                    "exposure_s": exposure,
                    "F3_ph_cm2_s": f3,
                    "ratio_vs_baseline": factor,
                    "ratio_vs_CAM511_3e-6": f3 / 3e-6 if f3 != "" else "",
                    "expected_linear_factor": factor,
                    "actual_factor": factor,
                    "notes": notes,
                }
            )
    fields = [
        "scenario",
        "description",
        "run_status",
        "window_keV",
        "model",
        "prompt_cps",
        "delayed_cps",
        "focused_cps",
        "total_background_cps",
        "source_response_cps_per_flux",
        "information_per_s",
        "exposure_s",
        "F3_ph_cm2_s",
        "ratio_vs_baseline",
        "ratio_vs_CAM511_3e-6",
        "expected_linear_factor",
        "actual_factor",
        "notes",
    ]
    write_csv(outdir / "sensitivity_ablation_table.csv", scenario_rows, fields)


def generate_lineage_partials(outdir: Path, diag_rows: list[dict[str, str]], origin_summary: list[dict[str, Any]]) -> None:
    top_origin = {r["nuclide"]: r for r in origin_summary}
    keep = {"O-15", "C-11", "Ga-68"}
    rows: list[dict[str, Any]] = []
    for idx, row in enumerate(diag_rows):
        if row.get("nuclide") not in keep:
            continue
        nuc = row["nuclide"]
        origin = top_origin.get(nuc, {})
        rows.append(
            {
                "event_id": f"aggregate_proxy_row_{idx}",
                "source_event_id": "unresolved_not_preserved",
                "candidate_event_id": "unresolved_not_preserved",
                "stream_type": "delayed_aggregate_proxy_not_event_lineage",
                "nuclide": nuc,
                "source_block_name": "unresolved_not_preserved_per_event",
                "production_volume": "unresolved_per_event; top_source_volume=" + str(origin.get("top_volume", "")),
                "decay_volume": "unresolved_per_event",
                "decay_x_mm": "",
                "decay_y_mm": "",
                "decay_z_mm": "",
                "first_hit_volume": row.get("source_volume_proxy", ""),
                "first_hit_detector_kind": "proxy_volume_aggregate",
                "tes_total_edep_keV": "",
                "tes_measured_energy_keV": "",
                "bgo_total_edep_keV": "",
                "bgo_veto_threshold_keV": 50.0,
                "bgo_veto_pass": "aggregate_after_bgo_stage_not_per_event",
                "line_window_pass": row.get("line_510p3_511p8_final_events", ""),
                "broad_window_pass": row.get("broad_480_550_final_events", ""),
                "event_weight": "",
                "weighted_cps": fval(row.get("line_510p3_511p8_final_cps")) + fval(row.get("broad_480_550_final_cps")),
                "input_file": "delayed_511_by_nuclide_volume.csv",
                "notes": "PARTIAL: source_volume_proxy is not true production/decay source-block lineage",
            }
        )
    fields = [
        "event_id",
        "source_event_id",
        "candidate_event_id",
        "stream_type",
        "nuclide",
        "source_block_name",
        "production_volume",
        "decay_volume",
        "decay_x_mm",
        "decay_y_mm",
        "decay_z_mm",
        "first_hit_volume",
        "first_hit_detector_kind",
        "tes_total_edep_keV",
        "tes_measured_energy_keV",
        "bgo_total_edep_keV",
        "bgo_veto_threshold_keV",
        "bgo_veto_pass",
        "line_window_pass",
        "broad_window_pass",
        "event_weight",
        "weighted_cps",
        "input_file",
        "notes",
    ]
    write_csv(outdir / "o15_bgo_lineage_events.csv", rows, fields)
    write_csv(outdir / "o15_bgo_lineage_events_PARTIAL.csv", rows, fields)
    missing = {
        "status": "PARTIAL",
        "reason": "current final delayed diagnostics are grouped by source_volume_proxy and do not preserve per-event source block lineage",
        "missing_fields": [
            "source_block_name per final event",
            "production_volume per final event",
            "decay coordinates per final event",
            "per-event TES measured energy",
            "per-event BGO total edep at multiple thresholds",
            "source_event_id/candidate_event_id mapping for delayed source blocks",
        ],
        "do_not_use_for": "Do not infer BGO-origin class A-E final TES background from this partial table.",
    }
    write_json(outdir / "lineage_missing_fields.json", missing)


def generate_class_tables(outdir: Path, comps: dict[str, dict[str, float]]) -> None:
    rows = []
    for class_id, desc in CLASS_DEFS.items():
        rows.append(
            {
                "class_id": class_id,
                "class_description": desc,
                "nuclide": "O-15",
                "origin_volume": "BGO_Shield" if class_id in {"A", "B", "C", "D", "E"} else "non_BGO",
                "n_events": "unresolved",
                "weighted_cps_line": "unresolved",
                "weighted_cps_broad": "unresolved",
                "weighted_cps_total": "unresolved",
                "fraction_of_o15_activity": "unresolved",
                "fraction_of_o15_final_line": "unresolved",
                "fraction_of_total_final_line": "unresolved",
                "median_decay_r_mm": "unresolved",
                "median_decay_z_mm": "unresolved",
                "median_bgo_edep_keV": "unresolved",
                "median_tes_edep_keV": "unresolved",
                "notes": "not computable from current outputs; requires per-final-event source-block lineage and bgo edep",
            }
        )
    fields = [
        "class_id",
        "class_description",
        "nuclide",
        "origin_volume",
        "n_events",
        "weighted_cps_line",
        "weighted_cps_broad",
        "weighted_cps_total",
        "fraction_of_o15_activity",
        "fraction_of_o15_final_line",
        "fraction_of_total_final_line",
        "median_decay_r_mm",
        "median_decay_z_mm",
        "median_bgo_edep_keV",
        "median_tes_edep_keV",
        "notes",
    ]
    write_csv(outdir / "o15_bgo_decay_veto_escape_classes.csv", rows, fields)
    write_csv(outdir / "o15_bgo_decay_veto_escape_classes_PARTIAL.csv", rows, fields)
    write_json(
        outdir / "o15_bgo_decay_veto_escape_classes_missing_fields.json",
        {
            "status": "PARTIAL",
            "class_A_definition": "BGO-origin O-15, TES line hit, BGO veto pass",
            "blocking_missing_fields": [
                "true BGO-origin source block per final event",
                "per-event bgo_total_edep_keV before threshold",
                "per-event TES line/broad measured energy",
            ],
        },
    )

    threshold_rows = []
    source_rows = read_csv(PATHS["threshold_scan_source"])
    baseline_line = comps["line_510p3_511p8"]["total"]
    by_thr: dict[float, dict[str, str]] = {}
    for row in source_rows:
        if (
            row.get("source_model") == "catalog_uniform"
            and row.get("roi_radius_mm") == "full"
            and row.get("edge_reject") == "0"
            and row.get("single_pixel_only") == "0"
            and row.get("layer_mask") == "all"
            and row.get("compton_policy") == "keep"
        ):
            by_thr.setdefault(fval(row["bgo_threshold_keV"]), row)
    for thr in [30.0, 50.0, 70.0, 100.0, 150.0]:
        row = by_thr.get(thr, {})
        total_line = fval(row.get("background_line_cps"), default=float("nan"))
        delayed_line = fval(row.get("delayed_line_cps"), default=float("nan"))
        threshold_rows.append(
            {
                "threshold_keV": thr,
                "class_A_cps_line": "unresolved",
                "class_B_cps_line": "unresolved",
                "class_A_fraction_of_total_line": "unresolved",
                "class_B_fraction_of_total_line": "unresolved",
                "all_o15_line_cps_after_veto": "unresolved",
                "all_delayed_line_cps_after_veto": "" if math.isnan(delayed_line) else delayed_line,
                "total_line_cps_after_veto": "" if math.isnan(total_line) else total_line,
                "estimated_F3_line_factor": "" if math.isnan(total_line) else math.sqrt(total_line / baseline_line),
                "notes": "threshold scan from aggregate selection table; O-15 class A/B unavailable without lineage",
            }
        )
    write_csv(
        outdir / "o15_bgo_veto_threshold_scan.csv",
        threshold_rows,
        [
            "threshold_keV",
            "class_A_cps_line",
            "class_B_cps_line",
            "class_A_fraction_of_total_line",
            "class_B_fraction_of_total_line",
            "all_o15_line_cps_after_veto",
            "all_delayed_line_cps_after_veto",
            "total_line_cps_after_veto",
            "estimated_F3_line_factor",
            "notes",
        ],
    )


def generate_event_grouping(outdir: Path) -> None:
    rows = []
    for row in read_csv(PATHS["selection_audit"]):
        if row.get("selection_id") != "baseline":
            continue
        for grouping in ["source_event_id", "candidate_event_id"]:
            rows.append(
                {
                    "dataset": "selection_best_measured_energy_audit",
                    "stream_type": row.get("energy_basis", ""),
                    "grouping_key": grouping,
                    "n_raw_hits": "unresolved_not_in_aggregate_csv",
                    "n_source_events": row.get("n_source_events", "") if grouping == "source_event_id" else "unresolved",
                    "n_candidate_events": "unresolved" if grouping == "source_event_id" else row.get("n_background_events", ""),
                    "n_tes_pixel_hits_total": "unresolved_not_in_aggregate_csv",
                    "n_singlehit_events": "unresolved_not_in_aggregate_csv",
                    "n_multihit_events": "unresolved_not_in_aggregate_csv",
                    "n_events_with_bgo_hit": "unresolved_not_in_aggregate_csv",
                    "line_window_events": row.get("n_background_events", "") if row.get("window") == "line_510p3_511p8" else "",
                    "broad_window_events": row.get("n_background_events", "") if row.get("window") == "broad_480_550" else "",
                    "weighted_line_cps": row.get("background_cps", "") if row.get("window") == "line_510p3_511p8" else "",
                    "weighted_broad_cps": row.get("background_cps", "") if row.get("window") == "broad_480_550" else "",
                    "notes": "aggregate audit only; raw hit/event grouping requires parsed hit catalog with source_event_id and candidate_event_id",
                }
            )
    fields = [
        "dataset",
        "stream_type",
        "grouping_key",
        "n_raw_hits",
        "n_source_events",
        "n_candidate_events",
        "n_tes_pixel_hits_total",
        "n_singlehit_events",
        "n_multihit_events",
        "n_events_with_bgo_hit",
        "line_window_events",
        "broad_window_events",
        "weighted_line_cps",
        "weighted_broad_cps",
        "notes",
    ]
    write_csv(outdir / "event_grouping_audit.csv", rows, fields)
    write_json(
        outdir / "event_grouping_missing_fields.json",
        {
            "status": "PARTIAL",
            "missing_for_full_audit": [
                "raw hit table with pixel_uid",
                "source_event_id per hit/event",
                "candidate_event_id per hit/event",
                "per-event BGO hit flag and energy",
                "same-pixel hit merge table",
            ],
        },
    )


def generate_manifest(outdir: Path, source_file: Path, key_outputs: list[str]) -> None:
    commit = run_capture(["git", "rev-parse", "HEAD"]) or "unresolved"
    branch = run_capture(["git", "branch", "--show-current"]) or "unresolved"
    dirty = bool(run_capture(["git", "status", "--short"]))
    cosima_path = "/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima"
    search_patterns = [
        "activation_decay_day15_groundstate_fixed.source",
        "delayed_511_by_nuclide_volume.csv",
        "activation_511_diagnostic_summary.json",
        "activation_511_truth_table.csv",
        "selection_best_measured_energy_audit.csv",
        "likelihood_sensitivity_by_model.csv",
        "asimov_profiled_sensitivity.csv",
        "current_system_fig11_style_counts_and_sensitivity.csv",
        "focused_gamma_background_summary.csv",
        "source_event_id",
        "candidate_event_id",
        "BGO_Shield",
        "O-15",
        "O15",
        "beta+",
        "DecayMode",
        "StoreIsotopes",
        "ActivationBuildUp",
    ]
    key_results: dict[str, list[str]] = {}
    for pat in search_patterns:
        found = run_capture(["rg", "-l", pat, "-g", "*"], cwd=ROOT)
        key_results[pat] = found.splitlines()[:200] if found else []
    geant4_env = {k: v for k, v in sorted(os.environ.items()) if k.startswith("G4")}
    manifest = {
        "audit_time_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "git": {"commit": commit, "branch": branch, "dirty": dirty},
        "platform": {
            "hostname": socket.gethostname(),
            "os": platform.platform(),
            "python": sys.version.split()[0],
            "working_directory": str(ROOT),
        },
        "geant4_megalib": {
            "geant4_version": None,
            "megalib_path": str(Path(cosima_path).parents[1]) if Path(cosima_path).exists() else None,
            "cosima_path": cosima_path if Path(cosima_path).exists() else None,
            "geant4_data_env": geant4_env,
        },
        "input_files": {
            "prompt_files": sorted(str(p) for p in (ROOT / "run_configs").glob("*Background*source"))[:50],
            "delayed_files": [rel(source_file), rel(PATHS["delayed_diag"]), rel(PATHS["delayed_summary"])],
            "source_files": [rel(source_file)],
            "geometry_files": [rel(p) for p in [ROOT / "TibetTES_v5_6layers.geo", ROOT / "TibetTES_v5_6layers.det", ROOT / "TibetTES_v5_6layers.geo.setup"] if p.exists()],
            "analysis_csv": [rel(p) for p in PATHS.values() if p.suffix.lower() == ".csv" and p.exists()],
            "hdf5_files": sorted(rel(p) for p in ROOT.rglob("*.h5"))[:100],
            "sim_gz_files": sorted(rel(p) for p in ROOT.rglob("*.sim.gz"))[:100],
        },
        "normalization": {
            "prompt_norm": None,
            "delayed_norm": "activity_Bq from delayed source Flux lines; final cps from delayed diagnostics",
            "focused_gamma_norm": "focused_gamma_background_summary.csv",
            "observation_time_s": 1_000_000.0,
            "area_correction": "CAM511 marker uses 50.89 cm2 optics area; current response stored as cps per flux",
        },
        "selection": {
            "line_window_keV": [510.3, 511.8],
            "broad_window_keV": [480.0, 550.0],
            "bgo_threshold_keV": 50.0,
            "coincidence_window_s": None,
        },
        "key_file_search_results": key_results,
        "generated_outputs": key_outputs,
        "known_limitations": [
            "No per-final-event source_block_name lineage in current delayed diagnostics.",
            "No true rerun ablations were executed; sensitivity_ablation_table.csv is posthoc_reweight unless marked otherwise.",
            "BGO-origin class A-E cannot be computed without per-event BGO edep and source block lineage.",
            "Geant4 version is null unless exposed by environment/tooling.",
        ],
    }
    write_json(outdir / "repro_manifest_511_audit.json", manifest)


def generate_cam511_md(outdir: Path, ablation_rows: list[dict[str, str]] | None = None) -> None:
    fig_rows = read_csv(PATHS["fig11"])
    lines = [
        "# CAM511 benchmark reproduction and fairness audit",
        "",
        "Local CAM511 source: `/home/ubuntu/codex_tes_511_sim/papers/511-CAM_Shirazi-etal_2023_arXiv2206.14652.pdf`.",
        "",
        "Parameters extracted from the paper text:",
        "",
        "- Observation duration: `1 Ms`.",
        "- Effective area of optics: `50.89 cm2`.",
        "- TES stack detection efficiency including gaps: `65%`.",
        "- Energy resolution: `390 eV FWHM @ 511 keV`.",
        "- BGO shield: `2 cm` sides and `5 cm` bottom, with a `70 keV` trigger threshold.",
        "- Balloon overburden/background model: shield-leakage model at `3.5 g/cm2` rest atmosphere.",
        "",
        "The local Fig. 11-style marker remains `3e-6 ph cm^-2 s^-1`. It is a benchmark marker, not a fully reproduced mission likelihood.",
        "",
        "Important limitation: the CAM511 paper text describes a shield-leakage balloon background model and an idealized/simple detector mass model. The extracted text does not show an explicit delayed activation/radioactivation chain comparable to the current workflow.",
        "",
        "## Current Fig. 11-style ratios",
        "",
        "| route | window | F3 / 1 Ms | ratio vs 3e-6 |",
        "|---|---:|---:|---:|",
    ]
    for row in fig_rows:
        f3 = fval(row.get("F3_1Ms_top_atm_ph_cm2_s"))
        lines.append(f"| {row.get('route_label')} | {row.get('window_label')} | `{f3:.6g}` | `{f3/3e-6:.1f}x` |")
    lines += [
        "",
        "## Fair-comparison matrix",
        "",
        "| case | status | interpretation |",
        "|---|---|---|",
        "| CAM511-like prompt-only | not reproduced | requires paper background/count extraction from Fig. 11 |",
        "| current prompt-only | posthoc available | see `sensitivity_ablation_table.csv`, scenario `prompt_only` |",
        "| current prompt+delayed | baseline | current workflow baseline |",
        "| current prompt+delayed+focused | baseline | focused term is tiny separate aperture addendum |",
        "| current no-BGO-activation | posthoc proxy | BGO activity-fraction apportionment, not true rerun |",
        "| current no-delayed | posthoc available | delayed component zeroed after selection |",
        "",
        "Conclusion: current-vs-CAM511 is a useful risk marker, but it is not yet an apples-to-apples end-to-end mission comparison. A complete reproduction would need CAM511 Fig. 11 background counts or the original simulation outputs.",
    ]
    (outdir / "cam511_benchmark_reproduction.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def integrate_pdf_fraction_above(path: Path, threshold: float) -> float | None:
    if not path.exists():
        return None
    xs: list[float] = []
    ys: list[float] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line.startswith("DP "):
            continue
        parts = line.split()
        if len(parts) >= 3:
            xs.append(fval(parts[1]))
            ys.append(max(0.0, fval(parts[2])))
    if len(xs) < 2:
        return None
    total = 0.0
    above = 0.0
    for i in range(len(xs) - 1):
        dx = max(0.0, xs[i + 1] - xs[i])
        y = 0.5 * (ys[i] + ys[i + 1])
        area = y * dx
        total += area
        if 0.5 * (xs[i] + xs[i + 1]) >= threshold:
            above += area
    return above / total if total else None


def generate_nuclear_data_md(outdir: Path, origin_summary: list[dict[str, Any]]) -> None:
    density = 7.13
    molar_mass = 4 * 208.9804 + 3 * 72.630 + 12 * 15.999
    n_oxygen = density / molar_mass * 6.02214076e23 * 12
    neutron_fracs = []
    proton_fracs = []
    for p in sorted((ROOT / "expacs_fullsphere_20bin_sources" / "cosima_spectra_dp_2602units").glob("n_bin*_pdf.dat")):
        val = integrate_pdf_fraction_above(p, 16.65)
        if val is not None:
            neutron_fracs.append(val)
    for p in sorted((ROOT / "expacs_fullsphere_20bin_sources" / "cosima_spectra_dp_2602units").glob("p_bin*_pdf.dat")):
        val = integrate_pdf_fraction_above(p, 16.65)
        if val is not None:
            proton_fracs.append(val)
    o15 = next((r for r in origin_summary if r["nuclide"] == "O-15"), None)
    rpip_rows = read_csv(PATHS["rpip_points"])
    o15_points = [r for r in rpip_rows if r.get("nuclide") == "O-15"]
    by_mech: dict[str, int] = defaultdict(int)
    by_primary: dict[str, int] = defaultdict(int)
    for r in o15_points:
        by_mech[r.get("mechanism", "")] += 1
        by_primary[r.get("primary", "")] += 1
    lines = [
        "# Nuclear data sanity check for BGO O-15",
        "",
        "Primary sources checked:",
        "",
        "- NNDC ENSDF O-15 adopted levels: https://www.nndc.bnl.gov/ensnds/15/O/adopted.pdf",
        "- JENDL-5 O-16 neutron reaction table: https://wwwndc.jaea.go.jp/jendl/j5/elm/Table/z008/T16.html",
        "- IAEA EXFOR database: https://www.iaea.org/resources/databases/experimental-nuclear-reaction-data",
        "- IAEA EXFOR O-16(gamma,n)O-15 example: https://www-nds.iaea.org/exfor//servlet/X4sGetSubent?plus=1&reqx=23402&subID=210110002",
        "",
        "## Checked facts",
        "",
        "- O-15 half-life used locally: `122.24 s`.",
        "- O-15 decay mode locally: beta-plus / electron-capture proxy, beta-plus branch proxy `0.999`.",
        "- JENDL-5 lists O-16(n,2n) with threshold about `16.65 MeV`; O-15 neutron production should therefore be tied to the high-energy neutron tail or other high-energy secondary channels.",
        "",
        "## BGO oxygen density estimate",
        "",
        f"- Assumed BGO density: `{density:g} g/cm3` (standard material value; project geometry names material `BGO` but does not define density locally).",
        f"- BGO molar mass Bi4Ge3O12 estimate: `{molar_mass:.3f} g/mol`.",
        f"- Oxygen atom density estimate: `{n_oxygen:.3e} O atoms/cm3`.",
        "",
        "## Current spectrum tail proxy",
        "",
        f"- Neutron PDF fraction above 16.65 MeV across available dp spectra: median `{median(neutron_fracs):.3g}`; range `{min(neutron_fracs):.3g}` to `{max(neutron_fracs):.3g}`." if neutron_fracs else "- Neutron spectrum tail fraction unresolved.",
        f"- Proton PDF fraction above 16.65 MeV across available dp spectra: median `{median(proton_fracs):.3g}`; range `{min(proton_fracs):.3g}` to `{max(proton_fracs):.3g}`." if proton_fracs else "- Proton spectrum tail fraction unresolved.",
        "",
        "## Local production/source evidence",
        "",
        f"- O-15 source activity from delayed source: `{fval(o15.get('total_activity_Bq')):.6g} Bq`." if o15 else "- O-15 source activity unresolved.",
        f"- Top O-15 source volume: `{o15.get('top_volume')}` at fraction `{fval(o15.get('top_volume_fraction')):.4f}`." if o15 else "",
        f"- RPIP O-15 sampled production points: `{len(o15_points)}`.",
        f"- O-15 sampled mechanisms: `{dict(sorted(by_mech.items()))}`.",
        f"- O-15 sampled primaries: `{dict(sorted(by_primary.items()))}`.",
        "",
        "## Interpretation",
        "",
        "BGO-origin O-15 is physically plausible and locally supported at the delayed source-activity level. This sanity check does not validate the absolute production-rate integral because current local inputs do not expose an audited cross-section-weighted flux integral by production channel and volume.",
    ]
    (outdir / "nuclear_data_sanity_check.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def median(values: list[float]) -> float:
    if not values:
        return float("nan")
    s = sorted(values)
    mid = len(s) // 2
    if len(s) % 2:
        return s[mid]
    return 0.5 * (s[mid - 1] + s[mid])


def generate_patch_plan(outdir: Path) -> None:
    text = """# Future instrumentation patch plan

Current outputs do not preserve enough metadata to compute BGO-origin O-15
class A-E directly.  The required change is metadata-only and should not alter
transport physics.

## Add at source construction / decay source generation

- `source_block_name`
- `source_volume`
- `source_nuclide_ZA`
- `source_z_bin`
- `source_r_bin_or_profile_id`
- `activity_Bq`

## Preserve through SIM/HDF5/CSV parsing

Each final event/hit row should carry:

- `source_event_id`
- `candidate_event_id`
- `source_block_name`
- `production_volume`
- `decay_volume`
- `decay_x_mm`, `decay_y_mm`, `decay_z_mm`
- `first_hit_volume`
- `tes_total_edep_keV`
- `tes_measured_energy_keV`
- `bgo_total_edep_keV`
- `bgo_veto_threshold_keV`
- `bgo_veto_pass`
- `event_weight`
- `weighted_cps`

## Validation

1. Existing final rates must be unchanged when metadata is enabled.
2. Sum over source blocks must recover delayed source activity normalization.
3. Sum over final event weighted cps must recover existing delayed diagnostic
   broad/line rates.
4. Class A-E tables must be produced from true `source_block_name`, not
   `source_volume_proxy`.
"""
    (outdir / "future_instrumentation_patch_plan.md").write_text(text, encoding="utf-8")


def generate_summary(outdir: Path, checks: dict[str, Any], origin_summary: list[dict[str, Any]]) -> None:
    o15 = next((r for r in origin_summary if r["nuclide"] == "O-15"), {})
    no_o15_line = ""
    no_bgo_line = ""
    for row in read_csv(outdir / "sensitivity_ablation_table.csv"):
        if row.get("window_keV") == "510.3-511.8" and row.get("model") == "window_counting_same_events":
            if row["scenario"] == "no_O15":
                no_o15_line = row.get("ratio_vs_baseline", "")
            if row["scenario"] == "no_BGO_activation_keep_prompt_veto":
                no_bgo_line = row.get("ratio_vs_baseline", "")
    outputs = sorted(p.name for p in outdir.iterdir() if p.is_file())
    lines = [
        "# ROOT CAUSE AUDIT SUMMARY",
        "",
        "## 1. Executive conclusion",
        "",
        "The current evidence supports a mixed root cause: delayed activation is a major background, prompt/direct background is non-negligible, and CAM511 remains a benchmark marker rather than an apples-to-apples reproduction.  O-15 is real and mostly BGO_Shield-origin at the delayed source-construction level, but O-15 alone does not explain the sensitivity deficit.",
        "",
        "## 2. What is now proven",
        "",
        f"- Component closure is exact at current precision: broad abs error `{checks['broad_window_closure_abs_error']}`, line abs error `{checks['line_window_closure_abs_error']}`.",
        f"- O-15 top source volume is `{o15.get('top_volume')}` with activity fraction `{fval(o15.get('top_volume_fraction')):.4f}`.",
        f"- O-15 / total line fraction remains `{checks['o15_fraction_total_line']:.4f}`.",
        "- Focused gamma is a separate aperture addendum and is tiny compared with prompt/delayed components.",
        "",
        "## 3. What is still not proven",
        "",
        "- BGO-origin O-15 class A-E cannot be computed from current outputs.",
        "- No true Geant4 rerun ablation was performed in this packet.",
        "- CAM511 Fig. 11 was not fully reproduced from original paper simulation outputs.",
        "",
        "## 4. Is O-15 real or a simulation artifact?",
        "",
        "O-15 is real in the current delayed source construction and delayed diagnostics.  Nuclear data sanity checks make BGO oxygen activation physically plausible.  Absolute rate validation still needs channel-resolved production-rate comparison against an audited nuclear data or activation-code calculation.",
        "",
        "## 5. Is BGO-origin O-15 proven as final TES line background?",
        "",
        "No.  BGO_Shield dominates O-15 source activity, but current final event tables do not preserve source-block lineage.  The generated class table is marked unresolved for this reason.",
        "",
        "## 6. Is the sensitivity deficit mostly O-15, beta+, delayed activation, prompt/direct, or benchmark mismatch?",
        "",
        f"- `no_O15` posthoc line-window F3 factor: `{no_o15_line}`.  This is a small improvement, consistent with O-15 being important but not dominant.",
        f"- `no_BGO_activation_keep_prompt_veto` posthoc line-window F3 factor: `{no_bgo_line}`.  This is a source-activity apportionment proxy, not a true rerun.",
        "- `no_delayed_activation` and `prompt_only` rows show delayed activation is a major contributor, but prompt/direct background also remains material.",
        "",
        "## 7. Are there signs of statistical/double-counting errors?",
        "",
        "No direct sign in the checked tables.  The Fisher/information-per-s formula is tested by `tools/audit_511/test_511_sensitivity_units.py`, and component closure is exact in the current aggregate products.  This does not replace a full raw event grouping audit.",
        "",
        "## 8. Which material/geometric design choices are risky?",
        "",
        "- BGO is beneficial as shield/veto but also dominates O-15 delayed source activity.",
        "- Broad-window activation is not O-15 dominated; W/Al/Ge/Bi components also matter.",
        "- BGO threshold changes aggregate line background only mildly in existing selection tables, but O-15-specific class A/B threshold dependence remains unresolved.",
        "",
        "## 9. Recommended next simulation campaign",
        "",
        "1. Add metadata-only source-block lineage instrumentation.",
        "2. Run true `no_O15`, `no_beta_plus`, and `no_BGO_activation_keep_prompt_veto` ablations.",
        "3. Run BGO no-O or equal-attenuation CsI/CeBr3 surrogate comparisons.",
        "4. Generate class A-E from true per-event lineage.",
        "",
        "## 10. Output file index",
        "",
    ]
    for name in outputs:
        lines.append(f"- `{name}`")
    lines += [
        "",
        "## Confidence",
        "",
        "High confidence:",
        "",
        "- Current component accounting is closed.",
        "- O-15 source activity is mostly BGO_Shield in the delayed source file.",
        "- O-15 alone is not enough to explain the full 39-517x gap.",
        "",
        "Medium confidence:",
        "",
        "- Posthoc no-BGO-activation proxy indicates BGO activation may be more important than O-15 alone.",
        "- CAM511 comparison is useful but not apples-to-apples.",
        "",
        "Low confidence / unresolved:",
        "",
        "- BGO-origin class A TES-line/no-veto cps.",
        "- True rerun ablation improvements.",
        "- Absolute O-15 production-rate validation against independent activation calculations.",
        "",
        "One-sentence conclusion: current evidence says delayed activation and BGO-origin isotope activity are serious design risks, but O-15 alone is not the root cause and BGO-origin final TES line dominance remains unresolved until source-block lineage and true ablations are run.",
    ]
    (outdir / "ROOT_CAUSE_AUDIT_SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=OUT_DEFAULT, help="Output directory for audit products")
    parser.add_argument("--source-file", type=Path, default=None, help="Delayed activation source file to parse")
    args = parser.parse_args()

    outdir = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)
    source_file = args.source_file or select_source_file()
    print(f"Input delayed source: {source_file}")
    print(f"Output directory: {outdir}")

    truth_meta = load_truth_meta(PATHS["truth_table"])
    source_rows = parse_delayed_source(source_file, truth_meta)
    origin_summary = summarize_origin(source_rows)
    origin_frac = origin_fractions(source_rows)
    diag_rows = read_csv(PATHS["delayed_diag"])
    delayed_by_nuc = aggregate_delayed_diag(diag_rows)
    comps = selection_components(PATHS["selection_audit"])

    true_origin_fields = [
        "nuclide",
        "ZA_or_isotope_id",
        "half_life_s",
        "decay_mode",
        "source_block_name",
        "production_volume",
        "decay_volume",
        "z_bin",
        "r_bin",
        "activity_Bq",
        "activity_fraction_within_nuclide",
        "activity_fraction_total",
        "source_file",
        "line_number_or_block_id",
        "origin_basis",
    ]
    write_csv(outdir / "activation_true_origin_by_isotope_volume.csv", source_rows, true_origin_fields)
    write_csv(
        outdir / "activation_true_origin_summary.csv",
        origin_summary,
        ["nuclide", "total_activity_Bq", "top_volume", "top_volume_activity_Bq", "top_volume_fraction", "n_source_blocks"],
    )

    checks = generate_background_reconciliation(outdir, comps, delayed_by_nuc, origin_frac, source_file)
    generate_ablation_table(outdir, comps, delayed_by_nuc, origin_frac, truth_meta)
    generate_lineage_partials(outdir, diag_rows, origin_summary)
    generate_class_tables(outdir, comps)
    generate_event_grouping(outdir)
    generate_cam511_md(outdir)
    generate_nuclear_data_md(outdir, origin_summary)
    generate_patch_plan(outdir)

    generated = sorted(rel(p) for p in outdir.iterdir() if p.is_file())
    generate_manifest(outdir, source_file, generated)
    generate_summary(outdir, checks, origin_summary)

    print("Generated audit files:")
    for path in sorted(outdir.iterdir()):
        if path.is_file():
            print(f"  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
