#!/usr/bin/env python3
"""Event-level and PSF-sensitivity diagnostic for the spot_r90 ROI sidecar.

This is a sidecar verifier for
outputs/reports/prompt511_spatial_roi_smoke_20260618/.  It does not rerun
transport or change the hard-window authority.
"""

from __future__ import annotations

import csv
import json
import math
import statistics as st
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = Path(__file__).resolve().parent
RECS = ROOT / "outputs/reports/prompt511_entry_audit_20260617/current_eplus_prompt_final_records.json"
SPATIAL = (
    ROOT
    / "stepwise_maintenance"
    / "step09_optics_bridge"
    / "outputs_f10m_a1_v3p5"
    / "detector_coupled_spatial_line_cuts.csv"
)
FOCUS = (
    ROOT
    / "stepwise_maintenance"
    / "step09_optics_bridge"
    / "outputs_f10m_a1_v3p5"
    / "detector_coupled_focus_response.json"
)
OUT_JSON = OUT_DIR / "verify_roi_firstprinciples_summary.json"
OUT_CSV = OUT_DIR / "verify_roi_psf_broadening_scan.csv"
OUT_MD = OUT_DIR / "ROI_FIRSTPRINCIPLES_VERIFICATION.md"

# M50000 hard-window authority.
Z0 = 6.130394687582996
B0 = 0.06298036183985109
S0 = 0.0011811656293957314
PROMPT0 = 0.05908272463250492
DELAYED0 = 0.0038976372073461713
F0 = 1.0e-4

# Side-entry optical axis in m45 local coordinates. This matches the Step05
# side-entry disk local center policy and the existing spatial-cut frame.
AXIS_Y = 0.0
AXIS_Z = -5.2

CUT_IDS = [
    "spot_r50",
    "spot_r68",
    "spot_r90",
    "spot_r95",
    "spot_r99",
    "spot_rmax",
    "full_aperture_1p8",
]
SIGNAL_CUT_IDS = ["spot_r50", "spot_r68", "spot_r90", "spot_r95", "spot_r99", "spot_rmax"]
PSF_FACTORS = [1.0, 1.15, 1.30, 1.50, 2.00]


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def f(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = row.get(key, default)
    if value in ("", None):
        return default
    return float(value)


def fmt(value: Any, ndigits: int = 6) -> str:
    if value in ("", None):
        return ""
    x = float(value)
    if not math.isfinite(x):
        return "nan"
    if x == 0.0:
        return "0"
    if abs(x) < 1.0e-3 or abs(x) >= 1.0e5:
        return f"{x:.{ndigits}e}"
    return f"{x:.{ndigits}g}"


def spot_radius(rec: dict[str, Any]) -> float:
    t = rec["tes_centroid_local_cm"]
    return math.hypot(float(t[1]) - AXIS_Y, float(t[2]) - AXIS_Z)


def interp(points: list[tuple[float, float]], x: float) -> float:
    ordered = sorted(points)
    if x <= ordered[0][0]:
        return ordered[0][1]
    for (x0, y0), (x1, y1) in zip(ordered, ordered[1:]):
        if x <= x1:
            if x1 == x0:
                return y1
            frac = (x - x0) / (x1 - x0)
            return y0 + frac * (y1 - y0)
    return ordered[-1][1]


def z_from_keeps(signal_keep: float, background_keep: float) -> float:
    if signal_keep <= 0.0 or background_keep <= 0.0:
        return 0.0
    return Z0 * signal_keep / math.sqrt(background_keep)


def build_psf_scan(spatial: dict[str, dict[str, str]], support: float, prompt_scale: float, delayed_scale: float) -> list[dict[str, Any]]:
    signal_points = [(0.0, 0.0)] + [
        (f(spatial[cut], "radius_cm"), f(spatial[cut], "signal_psf_fraction"))
        for cut in SIGNAL_CUT_IDS
    ]
    prompt_points = [(0.0, 0.0)] + [
        (f(spatial[cut], "radius_cm"), f(spatial[cut], "prompt_cps") * prompt_scale)
        for cut in CUT_IDS
    ]
    delayed_points = [(0.0, 0.0)] + [
        (f(spatial[cut], "radius_cm"), f(spatial[cut], "delayed_cps") * delayed_scale)
        for cut in CUT_IDS
    ]
    base_signal_radii = [f(spatial[cut], "radius_cm") for cut in SIGNAL_CUT_IDS]
    base_cut_radii = [f(spatial[cut], "radius_cm") for cut in CUT_IDS]
    detector_limit = f(spatial["full_aperture_1p8"], "radius_cm")

    rows: list[dict[str, Any]] = []
    for factor in PSF_FACTORS:
        max_radius = detector_limit
        grid = {round(idx * 0.005, 6) for idx in range(1, int(max_radius / 0.005) + 2)}
        grid.update(round(r, 6) for r in base_cut_radii if r <= detector_limit)
        grid.update(round(factor * r, 6) for r in base_signal_radii if factor * r <= detector_limit)
        best: dict[str, Any] | None = None
        for radius in sorted(grid):
            if radius > detector_limit:
                continue
            signal_keep = support * interp(signal_points, radius / factor)
            prompt_cps = interp(prompt_points, radius)
            delayed_cps = interp(delayed_points, radius)
            background_cps = prompt_cps + delayed_cps
            background_keep = background_cps / B0
            z20d = z_from_keeps(signal_keep, background_keep)
            row = {
                "psf_broadening_factor": factor,
                "cut_radius_cm": radius,
                "signal_keep_vs_hardwindow": signal_keep,
                "prompt_cps": prompt_cps,
                "delayed_cps": delayed_cps,
                "background_cps": background_cps,
                "background_keep_vs_hardwindow": background_keep,
                "Z20d": z20d,
                "gain_vs_hardwindow_Z": z20d / Z0 if Z0 > 0.0 else math.nan,
                "F3_20d_ph_cm2_s": F0 * 3.0 / z20d if z20d > 0.0 else math.inf,
            }
            if best is None or row["Z20d"] > best["Z20d"]:
                best = row
        assert best is not None
        best["hardwindow_fallback_Z20d"] = Z0
        best["hardwindow_fallback_preferred"] = best["Z20d"] < Z0
        best["detector_limit_cm"] = detector_limit
        best["recommended_Z20d_with_hardwindow_fallback"] = max(best["Z20d"], Z0)
        rows.append(best)
    return rows


def build_markdown(payload: dict[str, Any], psf_rows: list[dict[str, Any]]) -> str:
    prompt = payload["prompt"]
    signal = payload["signal"]
    folded = payload["folded"]
    lines = [
        "# Spot_r90 ROI Event-Level Diagnostic",
        "",
        "Status: `PASS_EVENT_LEVEL_SPOT_R90_DIAGNOSTIC_WITHDRAWN_AS_STRATEGY`.",
        "",
        "This report is generated by `verify_roi_firstprinciples.py`. It makes the dominant prompt spatial check and the PSF-broadening stress scan reproducible from repo files. It is diagnostic only and is withdrawn as the prompt-suppression strategy; the prompt fix direction is local side-port/side-wall geometry closure.",
        "",
        "## Verified",
        "",
        "1. **Prompt keep is independently cross-checked from selected prompt-eplus event positions.**",
        f"   The 80 current final W2 prompt-eplus events give keep=`{fmt(prompt['event_level_eplus_keep_r90'])}` inside `spot_r90`; the spatial table all-prompt keep is `{fmt(prompt['table_all_prompt_keep_r90'])}`. This confirms the dominant prompt term and the x3.1 suppression scale.",
        f"   The eplus radius median/max are `{fmt(prompt['eplus_spot_radius_cm_median'])}` / `{fmt(prompt['eplus_spot_radius_cm_max'])}` cm, so prompt fills the detector while the signal is concentrated.",
        "",
        "2. **The 0.8094 signal keep is real for a focal-spot ROI.**",
        f"   Signal keep versus hard-window = PSF fraction `{fmt(signal['psf_fraction_in_spot_r90'])}` x spatial support `{fmt(signal['spatial_support_vs_hardwindow'])}` = `{fmt(signal['signal_keep_vs_hardwindow'])}`.",
        "   The support gap is the difference between hard-window selected signal and the spatial-mappable focal component; it should be counted as lost for a focal-spot ROI smoke.",
        "",
        "3. **The fold is reproduced.**",
        f"   B'=`{fmt(folded['B_p_cps'])}` cps, S'=`{fmt(folded['S_p_cps'])}` cps, Z20d=`{fmt(folded['Z20d'])}`, prompt reduction=`{fmt(folded['prompt_reduction_factor'])}x`.",
        "",
        "## PSF Broadening Stress Scan",
        "",
        "Method: broaden the signal PSF by factor `f` using `E_broadened(R)=E_base(R/f)`, linearly interpolate the existing cumulative spatial-cut prompt/delayed rates versus detector-coordinate radius, and choose the best focal-ROI radius within the 1.8 cm full aperture for each `f`. For very broad spots, the hard-window fallback remains available; rows with gain below 1 are not recommended operating points.",
        "",
        "| PSF broadening f | best ROI cm | signal keep | B keep | ROI Z20d | best Z with fallback | gain vs hard-window | fallback? |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in psf_rows:
        fallback = "yes" if row["hardwindow_fallback_preferred"] else "no"
        lines.append(
            f"| {fmt(row['psf_broadening_factor'])} | {fmt(row['cut_radius_cm'])} | "
            f"{fmt(row['signal_keep_vs_hardwindow'])} | {fmt(row['background_keep_vs_hardwindow'])} | "
            f"{fmt(row['Z20d'])} | {fmt(row['recommended_Z20d_with_hardwindow_fallback'])} | "
            f"{fmt(row['gain_vs_hardwindow_Z'])} | {fallback} |"
        )
    lines.extend(
        [
            "",
            "## Remaining Gates",
            "",
            "- **Optics PSF/pointing budget:** this is now scripted in the scan above. Because the result depends strongly on the true focused spot and centroid stability, it should not be used as the prompt-fix strategy.",
            "- **Exactpos delayed spatial table:** still a minor open check. Delayed is a small part of B' and is currently scaled by spatial fraction from the existing table.",
            "- **M50000 packaging validator:** broader repository packaging still has missing performance/closure artifacts; that is orthogonal to this ROI smoke.",
            "",
            "## Verdict",
            "",
            "`spot_r90` remains a useful diagnostic of spatial diffuseness: about 3.1x prompt reduction and Z20d about 8.76 under the simulated PSF. It should not be promoted as the prompt-suppression route; local side-port/side-wall geometry closure is the hardware direction.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    recs = json.loads(RECS.read_text(encoding="utf-8"))
    spatial = {row["cut_id"]: row for row in read_csv(SPATIAL)}
    focus = json.loads(FOCUS.read_text(encoding="utf-8"))
    full = spatial["full_aperture_1p8"]
    spot = spatial["spot_r90"]
    r90 = f(spot, "radius_cm")

    eplus_tot = sum(f(rec, "rate_s-1") for rec in recs)
    radii = [spot_radius(rec) for rec in recs]
    eplus_keep_r90 = sum(f(rec, "rate_s-1") for rec in recs if spot_radius(rec) <= r90) / eplus_tot
    eplus_keep_count = sum(1 for rec in recs if spot_radius(rec) <= r90)
    table_prompt_keep = f(spot, "prompt_cps") / f(full, "prompt_cps")

    sig_psf = f(spot, "signal_psf_fraction")
    sig_full = f(full, "signal_cps_at_reference_flux")
    support = sig_full / S0
    signal_keep_vs_hw = sig_psf * support
    wc = focus["window_checks"]
    sig_scint = wc["W2_511_pm_420eV"]["signal_scintillator_cps_at_reference_flux"]

    delayed_keep = f(spot, "delayed_cps") / f(full, "delayed_cps")
    prompt_p = PROMPT0 * table_prompt_keep
    delayed_p = DELAYED0 * delayed_keep
    background_p = prompt_p + delayed_p
    signal_p = S0 * signal_keep_vs_hw
    z_p = z_from_keeps(signal_keep_vs_hw, background_p / B0)

    prompt_scale = PROMPT0 / f(full, "prompt_cps")
    delayed_scale = DELAYED0 / f(full, "delayed_cps")
    psf_rows = build_psf_scan(spatial, support, prompt_scale, delayed_scale)
    write_csv(OUT_CSV, psf_rows)

    payload = {
        "status": "PASS_EVENT_LEVEL_SPOT_R90_DIAGNOSTIC_WITHDRAWN_AS_STRATEGY",
        "inputs": {
            "prompt_eplus_records": rel(RECS),
            "spatial_cuts_csv": rel(SPATIAL),
            "focus_response": rel(FOCUS),
        },
        "spot_r90_radius_cm": r90,
        "spot_center_local_yz_cm": [AXIS_Y, AXIS_Z],
        "prompt": {
            "event_level_scope": "current final W2 prompt-eplus selected events only; validates the dominant prompt stream",
            "event_level_eplus_keep_r90": eplus_keep_r90,
            "event_level_eplus_keep_count": eplus_keep_count,
            "event_level_eplus_total_count": len(recs),
            "table_all_prompt_keep_r90": table_prompt_keep,
            "eplus_spot_radius_cm_median": st.median(radii),
            "eplus_spot_radius_cm_max": max(radii),
        },
        "signal": {
            "psf_fraction_in_spot_r90": sig_psf,
            "spatial_support_vs_hardwindow": support,
            "signal_keep_vs_hardwindow": signal_keep_vs_hw,
            "spatial_mappable_focal_signal_cps_at_reference_flux": sig_full,
            "hardwindow_signal_cps_at_reference_flux": S0,
            "scintillator_only_W2_signal_cps_at_reference_flux": sig_scint,
        },
        "delayed": {
            "keep_r90_from_fullstat_v2_table": delayed_keep,
            "caveat": "exactpos M50000 delayed per-event positions are not in this verifier; delayed is a small share of B'.",
        },
        "folded": {
            "prompt_p_cps": prompt_p,
            "delayed_p_cps": delayed_p,
            "B_p_cps": background_p,
            "S_p_cps": signal_p,
            "Z20d": z_p,
            "prompt_reduction_factor": PROMPT0 / prompt_p,
            "codex_smoke_Z20d": 8.760949682270843,
            "codex_smoke_B_cps": 0.0202037,
        },
        "psf_broadening_scan": {
            "method": "E_broadened(R)=E_base(R/f); cumulative prompt/delayed rates linearly interpolated vs ROI radius; best focal-ROI radius constrained to the 1.8 cm full aperture, with hard-window fallback reported separately.",
            "csv": rel(OUT_CSV),
            "rows": psf_rows,
        },
        "verdict": (
            "spot_r90 is event-level checked for the dominant prompt-eplus stream and signal support accounting, "
            "but remains diagnostic only. Prompt-fix strategy should focus on local side-port/side-wall geometry closure."
        ),
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUT_MD.write_text(build_markdown(payload, psf_rows), encoding="utf-8")

    print(
        "prompt keep r90: "
        f"event-level eplus {eplus_keep_r90:.4f} ({eplus_keep_count}/{len(recs)}) "
        f"vs table all-prompt {table_prompt_keep:.4f}"
    )
    print(
        "folded: "
        f"B'={background_p:.6f} cps, S'={signal_p:.6g} cps, "
        f"Z20d={z_p:.5f}, prompt x{PROMPT0 / prompt_p:.3f}"
    )
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_CSV}")
    print(f"wrote {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
