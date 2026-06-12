#!/usr/bin/env python3
"""Build v3p5 center-finger 1/10 Step07 source-case rate ledgers."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "stepwise_maintenance" / "step07_source_cases" / "outputs_v3p5_centerfinger_1of10"
STEP05 = ROOT / "stepwise_maintenance" / "step05_veto_time_axis" / "outputs_v3p5_centerfinger_l1" / "step05_v3p5_centerfinger_l1_response_summary.json"
STEP06 = ROOT / "stepwise_maintenance" / "step06_mission_time_variation" / "outputs_v3p5_centerfinger_1of10" / "step06_v3p5_centerfinger_1of10_summary.json"
STEP09 = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs_f10m_a1_v3p5" / "step09_optics_bridge_summary.json"

REFERENCE_FLUX = 1.0e-4
POINT_FLUX_SCAN = [3.0e-5, 5.0e-5, 8.0e-5, 1.0e-4, 1.5e-4, 2.0e-4, 3.0e-4]
TRANSIENT_FLUX_SCAN = [1.0e-4, 3.0e-4, 1.0e-3, 3.0e-3]
TRANSIENT_DURATIONS_S = [3600.0, 21600.0, 86400.0, 259200.0]
DIFFUSE_FOV_FLUX_PROXY = 6.26238e-7


def configure_paths(label: str) -> None:
    global OUT, STEP05, STEP06

    OUT = ROOT / "stepwise_maintenance" / "step07_source_cases" / f"outputs_v3p5_centerfinger_{label}"
    if label == "1of10":
        STEP05 = ROOT / "stepwise_maintenance" / "step05_veto_time_axis" / "outputs_v3p5_centerfinger_l1" / "step05_v3p5_centerfinger_l1_response_summary.json"
    else:
        STEP05 = ROOT / "stepwise_maintenance" / "step05_veto_time_axis" / f"outputs_v3p5_centerfinger_{label}_l1" / "step05_v3p5_centerfinger_l1_response_summary.json"
    STEP06 = (
        ROOT
        / "stepwise_maintenance"
        / "step06_mission_time_variation"
        / f"outputs_v3p5_centerfinger_{label}"
        / f"step06_v3p5_centerfinger_{label}_summary.json"
    )


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


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
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
    if x == 0.0:
        return "0"
    if abs(x) < 1.0e-3 or abs(x) >= 1.0e5:
        return f"{x:.{ndigits}e}"
    return f"{x:.{ndigits}g}"


def response_rows(step05: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for selection, item in step05["windows"].items():
        phys = item["physical_reference_flux"]
        rows.append(
            {
                "selection_id": selection,
                "lo_keV": item["window_keV"][0],
                "hi_keV": item["window_keV"][1],
                "reference_flux_ph_cm2_s": phys["reference_flux_ph_cm2_s"],
                "plane_rate_at_reference_flux_s-1": phys["rate_to_v3p5_injection_plane_s-1"],
                "plane_rate_per_flux_cps_per_ph_cm2_s": phys["rate_to_v3p5_injection_plane_s-1"] / phys["reference_flux_ph_cm2_s"],
                "science_final_cps_at_reference_flux": phys["signal_cps_at_reference_flux"],
                "science_final_response_cps_per_ph_cm2_s": phys["signal_cps_at_reference_flux"] / phys["reference_flux_ph_cm2_s"],
                "background_final_cps_day15": phys["background_cps"],
                "low_stat_final_background_events": phys["low_stat_final_background_events"],
            }
        )
    return rows


def build_rates(resp: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for r in resp:
        selection = r["selection_id"]
        response = float(r["science_final_response_cps_per_ph_cm2_s"])
        background = float(r["background_final_cps_day15"])
        for flux in POINT_FLUX_SCAN:
            rows.append(
                {
                    "analysis_case_id": f"A_point_{selection}_F{flux:.3g}",
                    "source_case_id": "A_GC_CENTRAL_COMPACT_POINT",
                    "source_class": "point_steady",
                    "model_id": "mono_511",
                    "selection_id": selection,
                    "flux_ph_cm2_s": flux,
                    "duration_s": "",
                    "final_rate_day15_cps": response * flux,
                    "background_final_cps_day15": background,
                    "response_cps_per_ph_cm2_s": response,
                    "handling": "focused_EventList_detector_response_linear_flux_scaling",
                }
            )
        rows.append(
            {
                "analysis_case_id": f"B_diffuse_proxy_{selection}",
                "source_case_id": "B_GC_DIFFUSE_BULGE_DISK_PROXY",
                "source_class": "extended_steady",
                "model_id": "routeB_fov_flux_proxy",
                "selection_id": selection,
                "flux_ph_cm2_s": DIFFUSE_FOV_FLUX_PROXY,
                "duration_s": "",
                "final_rate_day15_cps": response * DIFFUSE_FOV_FLUX_PROXY,
                "background_final_cps_day15": background,
                "response_cps_per_ph_cm2_s": response,
                "handling": "aperture_flux_proxy_using_v3p5_selection_response_not_a_focal_spot_source",
            }
        )
        for flux in TRANSIENT_FLUX_SCAN:
            for duration in TRANSIENT_DURATIONS_S:
                rows.append(
                    {
                        "analysis_case_id": f"C_transient_{selection}_F{flux:.3g}_T{int(duration)}s",
                        "source_case_id": "C_V404_TRANSIENT_BENCHMARK",
                        "source_class": "point_transient",
                        "model_id": "mono_511_transient",
                        "selection_id": selection,
                        "flux_ph_cm2_s": flux,
                        "duration_s": duration,
                        "final_rate_day15_cps": response * flux,
                        "background_final_cps_day15": background,
                        "response_cps_per_ph_cm2_s": response,
                        "handling": "focused_EventList_detector_response_linear_flux_scaling_with_duration_gate",
                    }
                )
    return rows


def markdown(summary: dict[str, Any]) -> str:
    checks = summary["checks"]
    return "\n".join(
        [
            "# Step07 v3p5 Center-Finger Source Cases",
            "",
            f"Status: `{summary['status']}`.",
            "",
            f"Claim level: {summary['claim_level']}.",
            "",
            f"This `{summary['statistics_label']}` source-case layer uses the v3p5 Step05 focused EventList detector response and does not change geometry, Step02 transport, or Step05 selection.",
            "",
            "Authority:",
            f"- optics design: `{summary['authority']['optics_design_name']}`",
            f"- A_eff(511): `{summary['authority']['aeff_511_cm2']:.6g} cm2`",
            f"- T_atm ref: `{summary['authority']['T_atm_ref']:.6g}`",
            f"- W2 response: `{checks['w2_response_cps_per_ph_cm2_s']:.6g}` cps/(ph cm^-2 s^-1)",
            f"- W2 instrument background: `{checks['w2_background_final_cps']:.6g}` cps",
            "",
            "Checks:",
            f"- A reference W2 final rate at `1e-4`: `{checks['A_reference_w2_final_rate_day15_cps']:.6g}` cps",
            f"- B diffuse proxy W2 final rate: `{checks['B_diffuse_proxy_w2_final_rate_day15_cps']:.6g}` cps",
            f"- source-case rows: `{checks['source_case_rows']}`",
            "",
            "Outputs:",
            f"- response authority: `{summary['outputs']['v3p5_response_authority']}`",
            f"- source-case rates: `{summary['outputs']['source_case_rates']}`",
            f"- summary JSON: `{summary['outputs']['summary_json']}`",
            "",
            "Limitations:",
            "- B diffuse is a low-stat aperture-flux proxy, not a focal-spot Cosima source;",
            "- broad spectra and off-axis EventLists are not rerun;",
            "- W2 background inherits the selected-event statistics of the chosen Step05 label.",
            "",
        ]
    )


def build_summary(step05: dict[str, Any], step06: dict[str, Any], step09: dict[str, Any], resp: list[dict[str, Any]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    label = step05.get("statistics_label", "1of10")
    resp_by_sel = {row["selection_id"]: row for row in resp}
    w2 = resp_by_sel["w2_510p58_511p42"]
    a_ref = next(row for row in rows if row["analysis_case_id"] == "A_point_w2_510p58_511p42_F0.0001")
    b_ref = next(row for row in rows if row["analysis_case_id"] == "B_diffuse_proxy_w2_510p58_511p42")
    norm = step05["science_physical_normalization"]
    return {
        "status": f"PASS_V3P5_STEP07_SOURCE_CASES_{label.upper()}",
        "statistics_label": label,
        "claim_level": f"V3P5_L1_SOURCE_CASE_FOCUSED_EVENTLIST_RATE_FOLDING_{label.upper()}",
        "inputs": {
            "step05_summary": rel(STEP05),
            "step06_summary": rel(STEP06),
            "step09_summary": rel(STEP09),
        },
        "authority": {
            "optics_design_name": norm["optics_design_name"],
            "optics_profile": norm["optics_profile"],
            "aeff_511_cm2": norm["aeff_511_cm2"],
            "T_atm_ref": norm["atmospheric_transmission"]["T_atm"],
            "reference_flux_ph_cm2_s": norm["reference_flux_ph_cm2_s"],
            "reference_injection_rate_s-1": norm["rate_to_v3p5_injection_plane_s-1"],
            "eventlist_rows": step09["bridge"]["rows_written"],
            "step06_status": step06["status"],
        },
        "checks": {
            "source_case_rows": len(rows),
            "w2_response_cps_per_ph_cm2_s": w2["science_final_response_cps_per_ph_cm2_s"],
            "w2_background_final_cps": w2["background_final_cps_day15"],
            "w2_low_stat_background_events": w2["low_stat_final_background_events"],
            "A_reference_w2_final_rate_day15_cps": a_ref["final_rate_day15_cps"],
            "B_diffuse_proxy_w2_final_rate_day15_cps": b_ref["final_rate_day15_cps"],
            "B_diffuse_proxy_flux_ph_cm2_s": DIFFUSE_FOV_FLUX_PROXY,
        },
        "outputs": {
            "summary_json": rel(OUT / "source_case_summary.json"),
            "readme": rel(OUT / "README.md"),
            "v3p5_response_authority": rel(OUT / "v3p5_response_authority.csv"),
            "source_case_rates": rel(OUT / "source_case_rates.csv"),
        },
        "pending": [
            "Full v3p5 Step08 time-dependent fold.",
            "Diffuse/off-axis EventList source treatment for Route B.",
        ],
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="1of10", help="Run/output label, e.g. 1of10 or fullstat_v2")
    args = ap.parse_args()

    configure_paths(args.label)
    OUT.mkdir(parents=True, exist_ok=True)
    step05 = load_json(STEP05)
    step06 = load_json(STEP06)
    step09 = load_json(STEP09)
    resp = response_rows(step05)
    rows = build_rates(resp)
    write_csv(OUT / "v3p5_response_authority.csv", resp)
    write_csv(OUT / "source_case_rates.csv", rows)
    summary = build_summary(step05, step06, step09, resp, rows)
    write_json(OUT / "source_case_summary.json", summary)
    (OUT / "README.md").write_text(markdown(summary), encoding="utf-8")
    print(json.dumps({"status": summary["status"], "summary": summary["outputs"]["summary_json"], "rates": summary["outputs"]["source_case_rates"]}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
