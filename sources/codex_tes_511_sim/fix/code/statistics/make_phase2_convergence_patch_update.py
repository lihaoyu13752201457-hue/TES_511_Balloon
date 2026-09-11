#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the Phase-2 convergence-patch MD update products.

This is a claim-control/update layer on top of the existing Phase2 convergence
patch.  It does not run new large transport.  The mixed-voxel item is frozen as
a quantified systematic, as allowed by the update MD, rather than promoted to a
transport-validated result.
"""

from __future__ import annotations

import csv
import json
import math
import re
import textwrap
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent
OUT = ROOT / "statistics" / "phase2_convergence_patch_update"
PHASE2 = ROOT / "statistics" / "phase2_real_flight_physical_production"
CONV = ROOT / "statistics" / "phase2_convergence_patch"
NEXT = ROOT / "statistics" / "nextphase_511"

WINDOWS = ["broad_480_550", "line_510p3_511p8"]
TOP_NUCLIDES = ["W-187", "Al-28", "Ge-75", "O-15", "C-11", "Ga-68", "Bi-210", "Mg-27", "Ge-77", "Pb-206"]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: Any, digits: int = 6) -> str:
    try:
        v = float(value)
    except Exception:
        return str(value)
    if not math.isfinite(v):
        return "nan"
    if v != 0 and (abs(v) < 1e-3 or abs(v) >= 1e4):
        return f"{v:.{digits}e}"
    return f"{v:.{digits}g}"


def md_table(rows: list[dict[str, Any]], fields: list[str]) -> str:
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(f, "")) for f in fields) + " |")
    return "\n".join(lines)


def source_authority_update() -> dict[str, Any]:
    out = OUT / "source_authority_update"
    out.mkdir(parents=True, exist_ok=True)
    source = ROOT / "particle_sources" / "run_configs" / "Science_511_onaxis_focalbeam_local.source"
    summary = load_json(ROOT / "statistics" / "day15_complete_report" / "complete_day15_summary.json")
    current_response = float(summary["science_sensitivity"]["science_final_response_cps_per_ph_cm-2_s-1"])

    files = [
        PHASE2 / "CURRENT_AUTHORITIES.md",
        PHASE2 / "phase2_integrated_summary_report_zh.md",
        PHASE2 / "phase2_real_flight_report.md",
        CONV / "final_report" / "COSMOSRAY_BG_2605_Phase2_convergence_patch_report.md",
        CONV / "authority" / "current_authorities.md",
        CONV / "authority" / "superseded_values.md",
        ROOT / "code" / "statistics" / "make_phase2_integrated_summary_report.py",
        ROOT / "code" / "statistics" / "make_phase2_convergence_patch.py",
        ROOT / "code" / "simulation" / "run_phase2_real_flight_pipeline.py",
    ]
    old_source_pat = re.compile(r"(z\s*[= ]\s*12\.766|12\.766\s*/\s*r\s*=\s*1\.8|radius\s*[= ]\s*1\.8|Legacy-not-current science beam: z=12\.766)", re.IGNORECASE)
    old_response_pat = re.compile(r"33\.947|33\.948")
    qualifier_pat = re.compile(r"superseded|invalid|legacy|not current|not-current|excluded|作废|旧|unit-conversion|禁止|invalidated", re.IGNORECASE)

    rows: list[dict[str, Any]] = []
    failures = []
    for path in files:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for label, pat in [("old_source_position_or_radius", old_source_pat), ("old_response", old_response_pat)]:
            for m in pat.finditer(text):
                start = max(0, m.start() - 180)
                end = min(len(text), m.end() + 180)
                context = " ".join(text[start:end].split())
                ok = bool(qualifier_pat.search(context))
                row = {
                    "file": rel(path),
                    "pattern": label,
                    "match": m.group(0),
                    "qualified_context": ok,
                    "context": context,
                    "action": "OK_QUALIFIED_LEGACY_OR_SUPERSEDED" if ok else "FAIL_UNQUALIFIED_CURRENT_CONTEXT",
                }
                rows.append(row)
                if not ok:
                    failures.append(row)

    current_beam_ok = "Beam HomogeneousBeam 0.0 0.0 127.66 0.0 0.0 -1.0 18.0" in source.read_text(encoding="utf-8")
    response_ok = math.isclose(current_response, 24.858993900839696, rel_tol=0.0, abs_tol=1e-12)
    status = "PASS_SOURCE_AUTHORITY_WORDING_LOCKED" if current_beam_ok and response_ok and not failures else "FAIL_SOURCE_AUTHORITY_WORDING"
    write_csv(out / "report_text_patch_list.csv", rows)
    note = f"""# Source Authority Update

当前 science-source authority 为 Gate-A 修正后的 Be-window beam。

- Current source: `{rel(source)}`
- Current source convention: `HomogeneousBeam z=127.66, radius=18.0 geometry units`
- Current response: `{current_response:.15g} cps/(ph cm^-2 s^-1)`
- Old response: `33.947... cps/(ph cm^-2 s^-1)` is superseded and excluded from current claims.
- Old source notation `z=12.766/r=1.8` may only appear in legacy/superseded or unit-conversion context.

Status: `{status}`.
"""
    (out / "source_authority_note.md").write_text(note, encoding="utf-8")
    data = {
        "status": status,
        "current_beam_ok": current_beam_ok,
        "current_response_cps_per_ph_cm2_s": current_response,
        "response_ok": response_ok,
        "unqualified_old_source_or_response_hits": len(failures),
        "scan_rows": len(rows),
    }
    write_json(out / "source_authority_check.json", data)
    return data


def parma_outlier_audit() -> dict[str, Any]:
    out = OUT / "parma_outlier_audit"
    out.mkdir(parents=True, exist_ok=True)

    rate_rows = read_csv(PHASE2 / "prompt_reweight_real" / "prompt_rate_by_time_particle.csv")
    rates: dict[tuple[int, str, str], dict[str, float]] = {}
    totals_by_window = defaultdict(float)
    particle_scale_reported: dict[tuple[int, str], float] = {}
    for r in rate_rows:
        if r["particle"] == "TOTAL":
            continue
        key = (int(r["time_bin_id"]), r["window"], r["particle"])
        val = float(r["final_cps"])
        rates[key] = {"final": val, "scale": float(r["scale"])}
        totals_by_window[r["window"]] += val
        particle_scale_reported[(int(r["time_bin_id"]), r["particle"])] = float(r["scale"])

    # First pass: per time/particle flux totals and capped scale totals.
    grid = PHASE2 / "environment_grid_real" / "environment_grid_real.csv"
    totals: dict[tuple[int, str], dict[str, float]] = defaultdict(lambda: {
        "ref": 0.0,
        "scaled": 0.0,
        "soft": 0.0,
        "hard": 0.0,
        "max_raw_scale": 0.0,
    })
    raw_scale_max = 0.0
    with grid.open("r", encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            t = int(r["time_bin_id"])
            p = r["particle"]
            ref = max(float(r["reference_flux_cm2_s_sr_MeV"]), 0.0)
            scale = float(r["scale_to_reference"])
            raw_scale_max = max(raw_scale_max, scale)
            key = (t, p)
            totals[key]["ref"] += ref
            totals[key]["scaled"] += ref * scale
            totals[key]["soft"] += ref * min(max(scale, 0.1), 10.0)
            totals[key]["hard"] += ref * min(max(scale, 0.2), 5.0)
            totals[key]["max_raw_scale"] = max(totals[key]["max_raw_scale"], scale)

    # Prompt-rate cap impact, using particle/time scale from the same resolved grid.
    cap_rows = []
    cap_totals: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for (t, window, particle), rr in rates.items():
        agg = totals.get((t, particle), {})
        ref = float(agg.get("ref", 0.0))
        unc_scale = float(agg.get("scaled", 0.0)) / ref if ref > 0 else rr["scale"]
        soft_scale = float(agg.get("soft", 0.0)) / ref if ref > 0 else rr["scale"]
        hard_scale = float(agg.get("hard", 0.0)) / ref if ref > 0 else rr["scale"]
        base = rr["final"] / max(unc_scale, 1e-300)
        for mode, scale in [("uncapped", unc_scale), ("soft_capped_0p1_10", soft_scale), ("hard_capped_0p2_5", hard_scale)]:
            cap_totals[mode][window] += base * scale
    for mode in ["uncapped", "soft_capped_0p1_10", "hard_capped_0p2_5"]:
        for window in WINDOWS:
            unc = cap_totals["uncapped"][window]
            val = cap_totals[mode][window]
            cap_rows.append({
                "mode": mode,
                "window": window,
                "final_cps": val,
                "relative_shift_vs_uncapped": abs(val - unc) / max(abs(unc), 1e-30),
            })
    write_csv(out / "parma_capped_vs_uncapped_rates.csv", cap_rows)

    # Second pass: contribution fractions for scale outliers and top contributors.
    contribution_rows: list[dict[str, Any]] = []
    summary_acc = {w: {"scale_gt10": 0.0, "scale_lt0p1": 0.0, "weighted_scale_num": 0.0, "weighted_den": 0.0} for w in WINDOWS}
    top_candidates: list[tuple[float, dict[str, Any]]] = []
    with grid.open("r", encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            t = int(r["time_bin_id"])
            p = r["particle"]
            key_tp = (t, p)
            ref = max(float(r["reference_flux_cm2_s_sr_MeV"]), 0.0)
            scale = float(r["scale_to_reference"])
            scaled = ref * scale
            denom = max(totals[key_tp]["scaled"], 1e-300)
            bin_fraction_within_particle_time = scaled / denom
            row_base: dict[str, Any] = {
                "time_bin": t,
                "day_mid": r["day_mid"],
                "particle": p,
                "angle_bin": r["angle_bin"],
                "energy_bin": r["energy_bin"],
                "energy_MeV": r["energy_MeV"],
                "raw_scale": scale,
                "ref_flux": ref,
                "scaled_flux": scaled,
                "capped_scale_soft_0p1_10": min(max(scale, 0.1), 10.0),
                "capped_scale_hard_0p2_5": min(max(scale, 0.2), 5.0),
                "included_in_baseline": ref > 0 and denom > 0,
            }
            max_frac = 0.0
            for window in WINDOWS:
                particle_rate = rates.get((t, window, p), {}).get("final", 0.0)
                frac = particle_rate * bin_fraction_within_particle_time / max(totals_by_window[window], 1e-300)
                row_base[f"event_weight_fraction_{window}"] = frac
                summary_acc[window]["weighted_scale_num"] += frac * scale
                summary_acc[window]["weighted_den"] += frac
                if scale > 10.0:
                    summary_acc[window]["scale_gt10"] += frac
                if scale < 0.1:
                    summary_acc[window]["scale_lt0p1"] += frac
                max_frac = max(max_frac, frac)
            if scale > 10.0 or scale < 0.1:
                contribution_rows.append(dict(row_base, row_class="scale_outlier"))
            elif max_frac > 2.0e-5:
                top_candidates.append((max_frac, dict(row_base, row_class="top_rate_contribution")))
    top_candidates.sort(key=lambda x: x[0], reverse=True)
    contribution_rows.extend(row for _score, row in top_candidates[:3000])
    # Deduplicate by time/particle/angle/energy.
    dedup = {}
    for r in contribution_rows:
        dedup[(r["time_bin"], r["particle"], r["angle_bin"], r["energy_bin"])] = r
    contribution_rows = list(dedup.values())
    contribution_rows.sort(key=lambda r: max(float(r["event_weight_fraction_broad_480_550"]), float(r["event_weight_fraction_line_510p3_511p8"])), reverse=True)
    write_csv(out / "parma_scale_contribution.csv", contribution_rows)

    broad_unc = cap_totals["uncapped"]["broad_480_550"]
    line_unc = cap_totals["uncapped"]["line_510p3_511p8"]
    broad_soft = cap_totals["soft_capped_0p1_10"]["broad_480_550"]
    line_soft = cap_totals["soft_capped_0p1_10"]["line_510p3_511p8"]
    broad_hard = cap_totals["hard_capped_0p2_5"]["broad_480_550"]
    line_hard = cap_totals["hard_capped_0p2_5"]["line_510p3_511p8"]
    broad_soft_diff = abs(broad_soft - broad_unc) / max(abs(broad_unc), 1e-30)
    line_soft_diff = abs(line_soft - line_unc) / max(abs(line_unc), 1e-30)
    broad_hard_diff = abs(broad_hard - broad_unc) / max(abs(broad_unc), 1e-30)
    line_hard_diff = abs(line_hard - line_unc) / max(abs(line_unc), 1e-30)
    max_diff = max(broad_soft_diff, line_soft_diff, broad_hard_diff, line_hard_diff)
    if max_diff < 0.01:
        decision = "PASS_CONTRIBUTION_WEIGHTED_KEEP_UNCAPPED_BASELINE_LE_1PCT_SYSTEMATIC"
    elif max_diff < 0.03:
        decision = "PASS_CONTRIBUTION_WEIGHTED_ADD_1_TO_3PCT_SYSTEMATIC_BAND"
    else:
        decision = "WARN_OUTLIER_CAP_SHIFT_GT_3PCT_DO_NOT_FREEZE_PROFILE"

    summary_rows = [
        {"item": "max raw scale", "value": fmt(raw_scale_max)},
        {"item": "broad contribution-weighted scale", "value": fmt(summary_acc["broad_480_550"]["weighted_scale_num"] / max(summary_acc["broad_480_550"]["weighted_den"], 1e-30))},
        {"item": "line contribution-weighted scale", "value": fmt(summary_acc["line_510p3_511p8"]["weighted_scale_num"] / max(summary_acc["line_510p3_511p8"]["weighted_den"], 1e-30))},
        {"item": "fraction broad final from scale > 10 bins", "value": fmt(summary_acc["broad_480_550"]["scale_gt10"])},
        {"item": "fraction line final from scale > 10 bins", "value": fmt(summary_acc["line_510p3_511p8"]["scale_gt10"])},
        {"item": "fraction broad final from scale < 0.1 bins", "value": fmt(summary_acc["broad_480_550"]["scale_lt0p1"])},
        {"item": "fraction line final from scale < 0.1 bins", "value": fmt(summary_acc["line_510p3_511p8"]["scale_lt0p1"])},
        {"item": "soft cap broad final difference", "value": fmt(broad_soft_diff)},
        {"item": "soft cap line final difference", "value": fmt(line_soft_diff)},
        {"item": "hard cap broad final difference", "value": fmt(broad_hard_diff)},
        {"item": "hard cap line final difference", "value": fmt(line_hard_diff)},
        {"item": "decision", "value": decision},
    ]
    summary_md = f"""# PARMA Outlier Contribution Audit

This audit uses the existing resolved PARMA grid and the particle-level prompt
rate table.  Because the event catalog does not retain primary energy/source
angle, the contribution mapping is a particle/time flux-weighted proxy, not an
event-resolved reweight.

{md_table(summary_rows, ['item', 'value'])}

The CSV `parma_scale_contribution.csv` contains all scale-outlier bins plus the
largest rate-contributing bins.  Full-grid totals were used for the summary
above, but the full 829k-row grid is not duplicated here to keep the review
packet compact.
"""
    (out / "parma_outlier_summary.md").write_text(summary_md, encoding="utf-8")

    # Heatmap: fraction from scale>10 by particle/time for broad window proxy.
    particles = sorted({p for (_t, p) in totals.keys()})
    times = sorted({t for (t, _p) in totals.keys()})
    pidx = {p: i for i, p in enumerate(particles)}
    tidx = {t: i for i, t in enumerate(times)}
    mat = np.zeros((len(particles), len(times)), dtype=float)
    # Re-read only outlier rows to fill matrix.
    with grid.open("r", encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            scale = float(r["scale_to_reference"])
            if scale <= 10.0:
                continue
            t = int(r["time_bin_id"])
            p = r["particle"]
            ref = max(float(r["reference_flux_cm2_s_sr_MeV"]), 0.0)
            scaled = ref * scale
            denom = max(totals[(t, p)]["scaled"], 1e-300)
            frac_within = scaled / denom
            prate = rates.get((t, "broad_480_550", p), {}).get("final", 0.0)
            mat[pidx[p], tidx[t]] += prate * frac_within / max(totals_by_window["broad_480_550"], 1e-300)
    fig, ax = plt.subplots(figsize=(9, 3.6))
    im = ax.imshow(np.log10(np.clip(mat, 1e-12, None)), aspect="auto", cmap="magma", vmin=-12, vmax=max(-6, float(np.nanmax(np.log10(np.clip(mat, 1e-12, None))))))
    ax.set_yticks(np.arange(len(particles)), particles)
    ax.set_xlabel("time bin")
    ax.set_title("log10 broad-window contribution fraction from scale > 10 bins")
    fig.colorbar(im, ax=ax, label="log10(fraction)")
    fig.tight_layout()
    fig.savefig(out / "parma_scale_outlier_heatmap.png", dpi=220)
    plt.close(fig)

    data = {
        "status": decision,
        "max_raw_scale": raw_scale_max,
        "broad_contribution_weighted_scale": summary_acc["broad_480_550"]["weighted_scale_num"] / max(summary_acc["broad_480_550"]["weighted_den"], 1e-30),
        "line_contribution_weighted_scale": summary_acc["line_510p3_511p8"]["weighted_scale_num"] / max(summary_acc["line_510p3_511p8"]["weighted_den"], 1e-30),
        "broad_fraction_from_scale_gt10": summary_acc["broad_480_550"]["scale_gt10"],
        "line_fraction_from_scale_gt10": summary_acc["line_510p3_511p8"]["scale_gt10"],
        "broad_fraction_from_scale_lt0p1": summary_acc["broad_480_550"]["scale_lt0p1"],
        "line_fraction_from_scale_lt0p1": summary_acc["line_510p3_511p8"]["scale_lt0p1"],
        "soft_cap_broad_relative_difference": broad_soft_diff,
        "soft_cap_line_relative_difference": line_soft_diff,
        "hard_cap_broad_relative_difference": broad_hard_diff,
        "hard_cap_line_relative_difference": line_hard_diff,
        "contribution_rows_written": len(contribution_rows),
        "mapping_limitation": "particle_time_flux_weighted_proxy; event catalog lacks primary energy/source angle",
    }
    write_json(out / "parma_outlier_summary.json", data)
    return data


def parent_feed_data_note() -> dict[str, Any]:
    out = OUT / "parent_feed_data_note"
    out.mkdir(parents=True, exist_ok=True)
    truth = {r["nuclide"]: r for r in read_csv(PHASE2 / "activation_511_truth" / "activation_511_truth_table.csv")}
    rows = []
    for nuc in TOP_NUCLIDES:
        tr = truth.get(nuc, {})
        beta = float(tr.get("beta_plus_branch_proxy", 0.0) or 0.0)
        if nuc in {"O-15", "C-11", "Ga-68"} or beta > 0:
            caveat = "line-window beta+/EC contributor; parent-feed data limitation must be stated separately"
        else:
            caveat = "broad-window/top-contributor parent-feed data limitation"
        rows.append({
            "nuclide": nuc,
            "current_broad_final_cps": tr.get("broad_480_550_final_cps", ""),
            "current_line_final_cps": tr.get("line_510p3_511p8_final_cps", ""),
            "decay_class": tr.get("decay_mode_proxy", "unknown"),
            "parent_feed_availability": "audited_branch_and_parent_production_tables_absent",
            "applied_correction": "none",
            "reason": "No controlled rate-level correction is applied without audited branch-ratio and parent-production tables.",
            "recommended_caveat": caveat,
        })
    write_csv(out / "parent_feed_top_contributors_table.csv", rows)
    note = f"""# Parent-Feed Top-Contributor Data Note

本版本已经对 511 keV 主要贡献核素进行 parent-feed bookkeeping 审计，但由于缺少已审计的 branch-ratio 与 parent-production 表，未对 rate 做 parent-fed 修正。因此，当前 top-contributor rate 应解释为 direct-production/proxy transport 贡献，并带有明确 parent-feed 数据限制。

{md_table(rows, ['nuclide', 'current_broad_final_cps', 'current_line_final_cps', 'decay_class', 'parent_feed_availability', 'applied_correction', 'recommended_caveat'])}

特别说明：O-15、C-11 和 Ga-68 对 511 line-window 的 beta+/EC 解释更敏感；在没有受控 parent-feed 数据之前，不能把 line-window contributor 表解释为 full parent-fed decay-chain result。
"""
    (out / "parent_feed_top_contributors_note.md").write_text(note, encoding="utf-8")
    data = {
        "status": "PASS_PARENT_FEED_TOP_CONTRIBUTOR_DATA_NOTE",
        "rows": len(rows),
        "rate_change_applied": False,
        "beta_plus_line_caveat_nuclides": ["O-15", "C-11", "Ga-68"],
    }
    write_json(out / "parent_feed_data_note_summary.json", data)
    return data


def mixed_voxel_systematic_freeze() -> dict[str, Any]:
    out = OUT / "mixed_voxel_delta"
    out.mkdir(parents=True, exist_ok=True)
    bound = read_csv(CONV / "mixed_voxel_bound" / "worst_case_rate_bound.csv")
    spatial = load_json(NEXT / "activation_spatial_model" / "activation_source_spatial_summary.json")
    rows = []
    for r in bound:
        frac = float(r["bound_fraction_of_final_background"])
        rows.append({
            "window": r["window"],
            "route": "systematic_freeze_no_transport",
            "radial_only_reference_cps": r["measured_final_background_cps"],
            "voxel_delta_transport_cps": "NOT_RUN",
            "conservative_bound_cps": r["worst_case_rate_bound_cps"],
            "bound_fraction_of_final_background": frac,
            "assigned_systematic_fraction": frac,
            "pass_condition": "bound_frozen_not_transport_validated",
        })
    write_csv(out / "radial_vs_voxel_delta_rates.csv", rows)
    template_rows = [
        {
            "metric": "energy_radius_layer_template_distance",
            "value": "NOT_COMPUTED_NO_TRANSPORT",
            "interpretation": "Shape validation is not claimed; radial-only source remains a reference-profile approximation.",
        },
        {
            "metric": "rate_level_systematic_max_fraction",
            "value": max(float(r["bound_fraction_of_final_background"]) for r in bound),
            "interpretation": "Use as conservative mixed-voxel systematic until minimal delta transport is run.",
        },
    ]
    write_csv(out / "radial_vs_voxel_delta_template_distance.csv", template_rows)
    note = f"""# Mixed-Voxel Systematic Freeze

本版本未执行 mixed-voxel source transport。基于 voxel-mode 活度占比和 safety factor 的保守 bound 显示，当前能窗 rate-level 影响不超过约 {100.0 * max(float(r['bound_fraction_of_final_background']) for r in bound):.2f}%。因此 radial-only source 只能作为 reference-profile 近似，而不是已由 voxel transport 验证的最终源模型。

{md_table(rows, ['window', 'route', 'conservative_bound_cps', 'bound_fraction_of_final_background', 'assigned_systematic_fraction'])}

Voxel-mode activity: `{spatial['voxel_activity_Bq']:.15g} Bq`, fraction `{spatial['voxel_activity_fraction']:.15g}`.
"""
    (out / "mixed_voxel_systematic_freeze.md").write_text(note, encoding="utf-8")
    data = {
        "status": "PASS_SYSTEMATIC_FREEZE_NO_DELTA_TRANSPORT",
        "route": "systematic_freeze",
        "new_transport_run": False,
        "voxel_activity_Bq": spatial["voxel_activity_Bq"],
        "voxel_activity_fraction": spatial["voxel_activity_fraction"],
        "max_assigned_systematic_fraction": max(float(r["bound_fraction_of_final_background"]) for r in bound),
        "claim": "radial-only source is a reference-profile approximation, not transport-validated final source model",
    }
    write_json(out / "voxel_delta_transport_summary.json", data)
    return data


def claim_control() -> dict[str, Any]:
    out = OUT / "claim_control"
    out.mkdir(parents=True, exist_ok=True)
    allowed = """# Allowed Claims

- Corrected day-15 static chain is completed and catalog-closed.
- Phase2 reference-profile/proxy convergence gates are completed with quantified limitations.
- PARMA outlier contribution has been audited at particle/time flux-weighted level.
- BGO event-total proxy is retained as a small quantified systematic for the present reference-profile study.
- Mixed voxel is frozen as a rate-level systematic bound unless/until minimal delta transport is run.
"""
    forbidden = """# Forbidden Claims

- Do not claim final measured-telemetry real-flight sensitivity.
- Do not claim publication-level real-flight simulation is complete.
- Do not claim `1e-4 ph cm^-2 s^-1` is robustly detected at 3 sigma in 1 Ms.
- Do not claim full parent-fed decay chains are implemented.
- Do not claim mixed-voxel source transport is complete.
- Do not claim BGO per-hit electronics/timing response is implemented.
"""
    conclusion = """# Final Conclusion Patch

本工作完成了 511 keV TES 本底模型的 corrected day-15 static chain 与 Phase2 reference-profile/proxy convergence audit。当前版本已经显式审计 source authority、catalog closure、PARMA stability/outlier contribution、BGO event-total proxy、mixed-voxel bound/systematic freeze、top-contributor parent-feed 数据限制以及 profile-injection proxy coverage。当前结果应解释为带已量化限制的 reference-profile sensitivity study，而不是最终 real-flight telemetry simulation。
"""
    (out / "allowed_claims.md").write_text(allowed, encoding="utf-8")
    (out / "forbidden_claims.md").write_text(forbidden, encoding="utf-8")
    (out / "final_conclusion_patch.md").write_text(conclusion, encoding="utf-8")
    data = {
        "status": "PASS_CLAIM_CONTROL_PATCH",
        "allowed_claims": 5,
        "forbidden_claims": 6,
    }
    write_json(out / "claim_control_summary.json", data)
    return data


def write_readme(pieces: dict[str, Any]) -> None:
    text = f"""# Phase2 Convergence Patch MD Update

This directory implements `COSMOSRAY_BG_2605_Phase2_收敛补丁_MD更新.md`.

## Status

- U1 source authority: `{pieces['source_authority']['status']}`
- U2 PARMA outlier contribution: `{pieces['parma_outlier']['status']}`
- U3 mixed voxel: `{pieces['mixed_voxel']['status']}`
- U4 parent-feed data note: `{pieces['parent_feed']['status']}`
- Claim control: `{pieces['claim_control']['status']}`

## Main Decision

No new large transport was run.  Mixed voxel is frozen as a quantified
systematic with maximum assigned fraction `{pieces['mixed_voxel']['max_assigned_systematic_fraction']:.6g}`.

The report wording should be: corrected day-15 static chain + Phase2
reference-profile/proxy sensitivity study with quantified limitations.
"""
    (OUT / "README.md").write_text(text, encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    pieces = {
        "source_authority": source_authority_update(),
        "parma_outlier": parma_outlier_audit(),
        "parent_feed": parent_feed_data_note(),
        "mixed_voxel": mixed_voxel_systematic_freeze(),
        "claim_control": claim_control(),
    }
    write_json(OUT / "phase2_convergence_patch_update_summary.json", pieces)
    write_readme(pieces)
    print(json.dumps({"status": "PASS_PHASE2_CONVERGENCE_PATCH_UPDATE_BUILT", "out": rel(OUT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
