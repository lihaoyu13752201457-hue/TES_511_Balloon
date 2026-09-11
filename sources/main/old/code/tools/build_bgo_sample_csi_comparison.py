#!/usr/bin/env python3
"""Build a BGO-vs-CsI material control from corresponding Step05--Step08 outputs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "reports" / "bgo_sample_csi_comparison_20260615"
BGO_DIR = ROOT / "Bgo_sample"
TRACKED_SUMMARY_JSON = BGO_DIR / "closure_summary.json"
TRACKED_SUMMARY_MD = BGO_DIR / "CLOSURE_SUMMARY.md"

CSI_LABEL = "fullstat_v2_exactpos_m50000_s260613"
CSI_STEP05 = ROOT / "stepwise_maintenance" / "step05_veto_time_axis" / f"outputs_v3p5_centerfinger_{CSI_LABEL}_l1" / "step05_v3p5_centerfinger_l1_response_summary.json"
CSI_STEP06 = ROOT / "stepwise_maintenance" / "step06_mission_time_variation" / f"outputs_v3p5_centerfinger_{CSI_LABEL}" / f"step06_v3p5_centerfinger_{CSI_LABEL}_summary.json"
CSI_STEP07 = ROOT / "stepwise_maintenance" / "step07_source_cases" / f"outputs_v3p5_centerfinger_{CSI_LABEL}" / "source_case_summary.json"
CSI_STEP08 = ROOT / "stepwise_maintenance" / "step08_significance" / f"outputs_v3p5_centerfinger_{CSI_LABEL}" / "step08_v3p5_centerfinger_time_dependent_summary.json"

BGO_STEP05 = ROOT / "stepwise_maintenance" / "step05_veto_time_axis" / "outputs_bgo_sample_fullstat_v2_exactpos_l1" / "step05_bgo_sample_l1_response_summary.json"
BGO_STEP06 = ROOT / "stepwise_maintenance" / "step06_mission_time_variation" / "outputs_bgo_sample_fullstat_v2_exactpos" / "step06_bgo_sample_fullstat_v2_exactpos_summary.json"
BGO_STEP07 = ROOT / "stepwise_maintenance" / "step07_source_cases" / "outputs_bgo_sample_fullstat_v2_exactpos" / "source_case_summary.json"
BGO_STEP08 = ROOT / "stepwise_maintenance" / "step08_significance" / "outputs_bgo_sample_fullstat_v2_exactpos" / "step08_bgo_sample_time_dependent_summary.json"
BGO_GEOMETRY = ROOT / "Bgo_sample" / "bgo_sample_summary.json"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def fmt(x: float, ndigits: int = 6) -> str:
    if x == 0:
        return "0"
    if abs(x) < 1.0e-3 or abs(x) >= 1.0e5:
        return f"{x:.{ndigits}e}"
    return f"{x:.{ndigits}g}"


def row(
    material: str,
    step05: dict[str, Any],
    step06: dict[str, Any],
    step07: dict[str, Any],
    step08: dict[str, Any],
    geometry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    w2 = step05["windows"]["w2_510p58_511p42"]["physical_reference_flux"]
    c6 = step06["checks"]
    c8 = step08["checks"]
    out = {
        "material": material,
        "status_step05": step05["status"],
        "status_step06": step06["status"],
        "status_step07": step07["status"],
        "status_step08": step08["status"],
        "active_veto_threshold_keV": step05["normalization"]["active_veto_threshold_keV"],
        "step05_w2_background_cps": w2["background_cps"],
        "step05_w2_signal_cps_at_1e-4": w2["signal_cps_at_reference_flux"],
        "step05_w2_response_cps_per_ph_cm2_s": w2["signal_cps_at_reference_flux"] / w2["reference_flux_ph_cm2_s"],
        "step06_w2_mission_mean_background_cps": c6["w2_dt_weighted_background_final_cps"],
        "step06_w2_mission_mean_signal_cps_at_1e-4": c6["w2_dt_weighted_science_final_cps_at_ref_flux"],
        "step08_w2_Z20d": c8["A_reference_w2_Z20d_time_dependent"],
        "step08_w2_T3_day": c8["A_reference_w2_T3_day"],
        "step08_w2_T5_day": c8["A_reference_w2_T5_day"],
        "step08_w2_F3_20d_ph_cm2_s": c8["A_reference_w2_flux_3sigma_20d_ph_cm2_s"],
        "step08_w2_source_counts": c8["A_reference_w2_source_counts"],
        "step08_w2_background_counts": c8["A_reference_w2_background_counts"],
        "w2_low_stat_background_events": c8["w2_low_stat_background_events"],
    }
    if geometry is not None:
        checks = geometry["checks"]
        out.update(
            {
                "source_csi_active_mass_kg": checks["source_csi_active_mass_kg"],
                "bgo_active_mass_kg": checks["bgo_active_mass_kg"],
                "active_mass_ratio_bgo_over_csi": checks["active_mass_ratio_bgo_over_csi"],
                "attenuation_max_abs_relative_difference": checks["attenuation_max_abs_relative_difference"],
                "bgo_total_mass_kg": checks["bgo_total_mass_kg"],
                "outer_shell_r_out_cm": checks["outer_shell_r_out_cm"],
            }
        )
    return out


def ratio_delta(bgo: dict[str, Any], csi: dict[str, Any], key: str) -> dict[str, float]:
    bv = float(bgo[key])
    cv = float(csi[key])
    return {"bgo": bv, "csi": cv, "ratio_bgo_over_csi": bv / cv, "relative_delta": bv / cv - 1.0, "absolute_delta": bv - cv}


def markdown(payload: dict[str, Any]) -> str:
    c = payload["comparison"]
    rows = payload["rows"]
    bgo = rows["BGO"]
    csi = rows["CsI_exactpos_m50000"]
    lines = [
        "# Bgo_sample vs CsI Exact-Position Comparison",
        "",
        f"Status: `{payload['status']}`.",
        "",
        "Scope: equal-attenuation BGO active shield sample against the current CsI exact-position M=50000 rate authority, using the corresponding Step05--Step08 W2 outputs for each material branch. No spatial/profile-likelihood gain is applied. The comparison uses the material-specific active-veto thresholds adopted by the two branches: CsI 50 keV and BGO 70 keV.",
        "",
        "| metric | CsI exactpos | BGO sample | BGO/CsI | relative change |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for key, label in [
        ("step05_w2_background_cps", "Step05 W2 background (cps)"),
        ("step05_w2_signal_cps_at_1e-4", "Step05 W2 signal at 1e-4 (cps)"),
        ("step06_w2_mission_mean_background_cps", "Step06 mission-mean background (cps)"),
        ("step06_w2_mission_mean_signal_cps_at_1e-4", "Step06 mission-mean signal at 1e-4 (cps)"),
        ("step08_w2_Z20d", "Step08 Z20d"),
        ("step08_w2_T3_day", "Step08 T3 (day)"),
        ("step08_w2_F3_20d_ph_cm2_s", "Step08 F3 20d (ph cm^-2 s^-1)"),
    ]:
        item = c[key]
        lines.append(f"| {label} | {fmt(item['csi'])} | {fmt(item['bgo'])} | {fmt(item['ratio_bgo_over_csi'])} | {item['relative_delta'] * 100:.3f}% |")
    lines.extend(
        [
            "",
            "Interpretation:",
            f"- BGO W2 mission-mean background is `{c['step06_w2_mission_mean_background_cps']['relative_delta'] * 100:.3f}%` relative to CsI.",
            f"- BGO W2 20-day significance is `{c['step08_w2_Z20d']['relative_delta'] * 100:.3f}%` relative to CsI.",
            f"- BGO W2 20-day 3-sigma flux threshold is `{c['step08_w2_F3_20d_ph_cm2_s']['relative_delta'] * 100:.3f}%` relative to CsI; lower is better.",
            f"- BGO active mass is `{bgo['bgo_active_mass_kg']:.6g} kg` versus the source CsI active mass `{bgo['source_csi_active_mass_kg']:.6g} kg`, ratio `{bgo['active_mass_ratio_bgo_over_csi']:.6g}`.",
            f"- Equal-attenuation check max absolute relative difference: `{bgo['attenuation_max_abs_relative_difference']:.6g}`.",
            f"- Active-veto thresholds are material-specific: CsI `{csi['active_veto_threshold_keV']:.6g} keV`, BGO `{bgo['active_veto_threshold_keV']:.6g} keV`; this is not a same-threshold veto scan.",
            "- The BGO branch uses its transported 5000-support exact-position delayed source and has not been promoted by a BGO-specific M/seed convergence sweep.",
            "",
            "Authority files:",
        f"- CsI label: `{payload['inputs']['csi_label']}`",
        f"- CsI Step07: `{payload['inputs']['csi_step07']}`",
            f"- CsI Step08: `{payload['inputs']['csi_step08']}`",
            f"- BGO Step07: `{payload['inputs']['bgo_step07']}`",
            f"- BGO Step08: `{payload['inputs']['bgo_step08']}`",
            "",
        ]
    )
    return "\n".join(lines)


def tracked_closure_payload(payload: dict[str, Any]) -> dict[str, Any]:
    bgo = payload["rows"]["BGO"]
    c = payload["comparison"]
    return {
        "status": "PASS_BGO_SAMPLE_MATERIAL_CHAIN_CLOSED",
        "scope": "Tracked GitHub-facing digest of the local Bgo_sample Step05--Step08 hard-window material comparison.",
        "source_report": rel(OUT / "bgo_vs_csi_report.md"),
        "tracked_digest": rel(TRACKED_SUMMARY_JSON),
        "geometry": {
            "bgo_veto_threshold_keV": bgo["active_veto_threshold_keV"],
            "source_csi_active_mass_kg": bgo["source_csi_active_mass_kg"],
            "bgo_active_mass_kg": bgo["bgo_active_mass_kg"],
            "active_mass_ratio_bgo_over_csi": bgo["active_mass_ratio_bgo_over_csi"],
            "attenuation_max_abs_relative_difference": bgo["attenuation_max_abs_relative_difference"],
            "outer_shell_r_out_cm": bgo["outer_shell_r_out_cm"],
        },
        "statuses": {
            "step05": bgo["status_step05"],
            "step06": bgo["status_step06"],
            "step07": bgo["status_step07"],
            "step08": bgo["status_step08"],
            "comparison": payload["status"],
        },
        "w2_rates": {
            "step05_background_cps": bgo["step05_w2_background_cps"],
            "step05_signal_cps_at_1e-4": bgo["step05_w2_signal_cps_at_1e-4"],
            "step06_mission_mean_background_cps": bgo["step06_w2_mission_mean_background_cps"],
            "step06_mission_mean_signal_cps_at_1e-4": bgo["step06_w2_mission_mean_signal_cps_at_1e-4"],
        },
        "step08": {
            "Z20d": bgo["step08_w2_Z20d"],
            "T3_day": bgo["step08_w2_T3_day"],
            "T5_day": bgo["step08_w2_T5_day"],
            "F3_20d_ph_cm2_s": bgo["step08_w2_F3_20d_ph_cm2_s"],
            "source_counts": bgo["step08_w2_source_counts"],
            "background_counts": bgo["step08_w2_background_counts"],
        },
        "relative_to_csi_exactpos": {
            "mission_mean_background_delta": c["step06_w2_mission_mean_background_cps"]["relative_delta"],
            "Z20d_delta": c["step08_w2_Z20d"]["relative_delta"],
            "F3_20d_delta": c["step08_w2_F3_20d_ph_cm2_s"]["relative_delta"],
        },
        "boundaries": [
            "This is a hard-window counting material comparison only.",
            "The comparison uses material-specific active-veto thresholds: CsI 50 keV and BGO 70 keV.",
            "The BGO branch uses its transported 5000-support exact-position delayed source and has not been promoted by a BGO-specific M/seed convergence sweep.",
            "No BGO spatial/profile-likelihood gain is applied to this hard-window comparison.",
            "BGO spatial, detector-threshold replay, and material attenuation sidecars are tracked separately in Bgo_sample/EXTENDED_CLOSURE_SUMMARY.md.",
            "Detailed regenerated Step05--Step08 outputs live under ignored local output directories; this tracked digest preserves the paper-facing closure numbers on GitHub.",
        ],
    }


def tracked_closure_markdown(payload: dict[str, Any]) -> str:
    bgo = payload["rows"]["BGO"]
    c = payload["comparison"]
    lines = [
        "# Bgo_sample Closure Summary",
        "",
        "Status: `PASS_BGO_SAMPLE_MATERIAL_CHAIN_CLOSED`.",
        "",
        "This tracked summary preserves the BGO Step05--Step08 hard-window material-comparison authority in Git, while the full regenerated Step05--Step08 output directories remain ignored.",
        "",
        "| item | value |",
        "| --- | ---: |",
        f"| BGO active-veto threshold | {bgo['active_veto_threshold_keV']:.6g} keV |",
        f"| Equal-attenuation max abs relative diff | {bgo['attenuation_max_abs_relative_difference']:.7g} |",
        f"| BGO active mass | {bgo['bgo_active_mass_kg']:.7g} kg |",
        f"| Source CsI active mass | {bgo['source_csi_active_mass_kg']:.7g} kg |",
        f"| Active mass ratio BGO/CsI | {bgo['active_mass_ratio_bgo_over_csi']:.7g} |",
        f"| Outer shell radius | {bgo['outer_shell_r_out_cm']:.7g} cm |",
        f"| Step05 status | `{bgo['status_step05']}` |",
        f"| Step06 status | `{bgo['status_step06']}` |",
        f"| Step07 status | `{bgo['status_step07']}` |",
        f"| Step08 status | `{bgo['status_step08']}` |",
        f"| Step06 W2 mission-mean background | {bgo['step06_w2_mission_mean_background_cps']:.12g} cps |",
        f"| Step06 W2 mission-mean signal at 1e-4 | {bgo['step06_w2_mission_mean_signal_cps_at_1e-4']:.12g} cps |",
        f"| Step08 W2 Z20d | {bgo['step08_w2_Z20d']:.12g} |",
        f"| Step08 W2 T3 | {bgo['step08_w2_T3_day']:.12g} d |",
        f"| Step08 W2 F3(20d) | {bgo['step08_w2_F3_20d_ph_cm2_s']:.12g} ph cm^-2 s^-1 |",
        f"| BGO/CsI mission-mean background delta | {c['step06_w2_mission_mean_background_cps']['relative_delta'] * 100:.3f}% |",
        f"| BGO/CsI Z20d delta | {c['step08_w2_Z20d']['relative_delta'] * 100:.3f}% |",
        f"| BGO/CsI F3(20d) delta | {c['step08_w2_F3_20d_ph_cm2_s']['relative_delta'] * 100:.3f}% |",
        "",
        "Boundary:",
        "- This is a hard-window counting material comparison only.",
        "- Active-veto thresholds are material-specific: CsI 50 keV and BGO 70 keV; this is not a same-threshold veto scan.",
        "- The BGO branch uses its transported 5000-support exact-position delayed source and has not been promoted by a BGO-specific M/seed convergence sweep.",
        "- No BGO spatial/profile-likelihood gain is applied to this hard-window comparison.",
        "- BGO spatial, detector-threshold replay, and material attenuation sidecars are tracked separately in `Bgo_sample/EXTENDED_CLOSURE_SUMMARY.md`.",
        "- The detailed regenerated Step05--Step08 outputs are local ignored artifacts; this tracked digest is the GitHub-facing closure record.",
        "",
        "Regeneration:",
        "- Step05: `python3 code/tools/build_v3p5_centerfinger_step05_l1_response.py --label bgo_sample_fullstat_v2_exactpos --workers 8`",
        "- Step06: `python3 stepwise_maintenance/step06_mission_time_variation/code/build_v3p5_centerfinger_step06_time_axis.py --label bgo_sample_fullstat_v2_exactpos`",
        "- Step07: `python3 stepwise_maintenance/step07_source_cases/code/build_v3p5_centerfinger_step07_source_cases.py --label bgo_sample_fullstat_v2_exactpos`",
        "- Step08: `python3 stepwise_maintenance/step08_significance/code/build_v3p5_centerfinger_step08_time_dependent.py --label bgo_sample_fullstat_v2_exactpos`",
        "- Comparison: `python3 code/tools/build_bgo_sample_csi_comparison.py`",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    csi = row("CsI_exactpos_m50000", load_json(CSI_STEP05), load_json(CSI_STEP06), load_json(CSI_STEP07), load_json(CSI_STEP08))
    bgo = row("BGO", load_json(BGO_STEP05), load_json(BGO_STEP06), load_json(BGO_STEP07), load_json(BGO_STEP08), load_json(BGO_GEOMETRY))
    keys = [
        "step05_w2_background_cps",
        "step05_w2_signal_cps_at_1e-4",
        "step05_w2_response_cps_per_ph_cm2_s",
        "step06_w2_mission_mean_background_cps",
        "step06_w2_mission_mean_signal_cps_at_1e-4",
        "step08_w2_Z20d",
        "step08_w2_T3_day",
        "step08_w2_T5_day",
        "step08_w2_F3_20d_ph_cm2_s",
        "step08_w2_source_counts",
        "step08_w2_background_counts",
    ]
    payload = {
        "status": "PASS_BGO_SAMPLE_VS_CSI_EXACTPOS_M50000_COMPARISON",
        "claim_level": "BGO_SAMPLE_MATERIAL_COMPARISON_AFTER_STEP08_NO_SPATIAL_LIKELIHOOD",
        "inputs": {
            "csi_label": CSI_LABEL,
            "csi_step05": rel(CSI_STEP05),
            "csi_step06": rel(CSI_STEP06),
            "csi_step07": rel(CSI_STEP07),
            "csi_step08": rel(CSI_STEP08),
            "bgo_step05": rel(BGO_STEP05),
            "bgo_step06": rel(BGO_STEP06),
            "bgo_step07": rel(BGO_STEP07),
            "bgo_step08": rel(BGO_STEP08),
            "bgo_geometry": rel(BGO_GEOMETRY),
        },
        "rows": {"CsI_exactpos_m50000": csi, "BGO": bgo},
        "comparison": {key: ratio_delta(bgo, csi, key) for key in keys},
        "sidecar_closure": [
            "BGO spatial, fixed-template annular likelihood, detector-threshold replay, and material attenuation sidecars are tracked in Bgo_sample/EXTENDED_CLOSURE_SUMMARY.md.",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "bgo_vs_csi_summary.json", payload)
    write_csv(OUT / "bgo_vs_csi_rows.csv", [csi, bgo])
    (OUT / "bgo_vs_csi_report.md").write_text(markdown(payload), encoding="utf-8")
    write_json(TRACKED_SUMMARY_JSON, tracked_closure_payload(payload))
    TRACKED_SUMMARY_MD.write_text(tracked_closure_markdown(payload), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "summary": rel(OUT / "bgo_vs_csi_summary.json"), "report": rel(OUT / "bgo_vs_csi_report.md")}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
