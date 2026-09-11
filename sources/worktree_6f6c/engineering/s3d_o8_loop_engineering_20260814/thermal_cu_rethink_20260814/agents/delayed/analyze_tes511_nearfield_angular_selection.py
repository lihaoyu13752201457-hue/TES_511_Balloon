#!/usr/bin/env python3
"""Audit passive angular separability of the selected delayed TES-bound 511s.

This is deliberately a small, read-only post-processing calculation.  It uses
the full optics EventList as the signal-direction/footprint denominator and the
420-row official selected delayed lineage as the delayed denominator.  It does
not infer a veto efficiency from the geometrical result.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path


HERE = Path(__file__).resolve().parent
LINEAGE = HERE / "delayed_annihilation_sibling_events.csv"
SIGNAL = Path(
    "/home/ubuntu/TES_511_Balloon/stepwise_maintenance/step09_optics_bridge/"
    "outputs_f10m_a1_v3p5/eventlists/"
    "Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat"
)
OUT_SUMMARY = HERE / "tes511_nearfield_angular_separation.csv"
OUT_HOTSPOTS = HERE / "tes511_nearfield_same_face_events.csv"

# Nominal TES envelope used by the S3d-O8 geometry audit, InstrumentFrame cm.
BOX = ((-3.15, 3.15), (-1.8, 1.8), (-7.0, -3.4))
C = math.sqrt(0.5)


def world_to_if(x: float, y: float, z: float) -> tuple[float, float, float]:
    return C * (x - z), y, C * (x + z)


def theta_x_deg(dx: float, dy: float, dz: float) -> float:
    n = math.sqrt(dx * dx + dy * dy + dz * dz)
    return math.degrees(math.acos(max(-1.0, min(1.0, dx / n))))


def neff(weights: list[float]) -> float:
    if not weights:
        return 0.0
    s = sum(weights)
    return s * s / sum(w * w for w in weights)


def dominant(weights: list[float]) -> float:
    return max(weights) / sum(weights) if weights else 0.0


def weighted(rows: list[dict[str, object]]) -> list[float]:
    return [float(r["mission_counts_20d_baseline_live"]) for r in rows]


def quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    x = q * (len(ordered) - 1)
    lo, hi = math.floor(x), math.ceil(x)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] * (hi - x) + ordered[hi] * (x - lo)


def ray_box_entry(
    p: tuple[float, float, float], d: tuple[float, float, float]
) -> tuple[str, tuple[float, float, float]] | None:
    t_enter = -math.inf
    t_exit = math.inf
    entry_face = ""
    axes = "xyz"
    for axis, ((lo, hi), pi, di) in enumerate(zip(BOX, p, d)):
        if abs(di) < 1e-15:
            if pi < lo or pi > hi:
                return None
            continue
        if di > 0:
            t_near, t_far, face = (lo - pi) / di, (hi - pi) / di, axes[axis] + "-"
        else:
            t_near, t_far, face = (hi - pi) / di, (lo - pi) / di, axes[axis] + "+"
        if t_near > t_enter:
            t_enter, entry_face = t_near, face
        t_exit = min(t_exit, t_far)
    if t_exit < max(t_enter, 0.0):
        return None
    t = max(t_enter, 0.0)
    return entry_face, tuple(pi + t * di for pi, di in zip(p, d))


def add_row(
    out: list[dict[str, object]],
    section: str,
    selection: str,
    n: int,
    counts: float,
    denominator_counts: float,
    weights: list[float],
    note: str = "",
) -> None:
    out.append(
        {
            "section": section,
            "selection": selection,
            "n_rows": n,
            "mission_counts_20d_baseline_live": f"{counts:.12f}",
            "fraction_of_section_denominator": f"{counts / denominator_counts:.12g}",
            "Neff": f"{neff(weights):.9f}",
            "dominant_event_fraction": f"{dominant(weights):.12g}",
            "note": note,
        }
    )


def main() -> None:
    signal_theta: list[float] = []
    signal_entry_y: list[float] = []
    signal_entry_z: list[float] = []
    signal_entry_face: list[str] = []
    with SIGNAL.open() as f:
        for line in f:
            fields = line.split()
            wx, wy, wz = map(float, fields[5:8])
            wdx, wdy, wdz = map(float, fields[8:11])
            x, y, z = world_to_if(wx, wy, wz)
            dx, dy, dz = world_to_if(wdx, wdy, wdz)
            signal_theta.append(theta_x_deg(dx, dy, dz))
            t = (BOX[0][0] - x) / dx
            signal_entry_y.append(y + t * dy)
            signal_entry_z.append(z + t * dz)
            hit = ray_box_entry((x, y, z), (dx, dy, dz))
            signal_entry_face.append(hit[0] if hit else "MISS")

    footprint = (
        min(signal_entry_y),
        max(signal_entry_y),
        min(signal_entry_z),
        max(signal_entry_z),
    )

    with LINEAGE.open(newline="") as f:
        all_rows = list(csv.DictReader(f))
    for row in all_rows:
        row["mission_counts_20d_baseline_live"] = float(
            row["mission_counts_20d_baseline_live"]
        )
    trace = [r for r in all_rows if int(r["traceable_sibling"]) == 1]
    unknown = [r for r in all_rows if int(r["traceable_sibling"]) != 1]
    all_counts = sum(weighted(all_rows))
    trace_counts = sum(weighted(trace))

    for row in trace:
        d = tuple(float(row[k]) for k in ("tes_511_IF_dx", "tes_511_IF_dy", "tes_511_IF_dz"))
        d_world = tuple(
            float(row[k])
            for k in ("tes_511_world_dx", "tes_511_world_dy", "tes_511_world_dz")
        )
        p = world_to_if(
            float(row["annihilation_world_x_cm"]),
            float(row["annihilation_world_y_cm"]),
            float(row["annihilation_world_z_cm"]),
        )
        row["theta_from_signal_axis_deg"] = theta_x_deg(*d)
        n_world = math.sqrt(sum(v * v for v in d_world))
        # The EventList axis is (+1/sqrt(2), 0, -1/sqrt(2)) in WorldFrame.
        dot_world = C * (d_world[0] - d_world[2]) / n_world
        row["theta_worldframe_crosscheck_deg"] = math.degrees(
            math.acos(max(-1.0, min(1.0, dot_world)))
        )
        # Intentionally retain the invalid mixed-frame number to expose the
        # easy-to-make error of dotting the WorldFrame axis into IF components.
        n_if = math.sqrt(sum(v * v for v in d))
        dot_mixed_invalid = C * (d[0] - d[2]) / n_if
        row["theta_mixed_frame_INVALID_deg"] = math.degrees(
            math.acos(max(-1.0, min(1.0, dot_mixed_invalid)))
        )
        hit = ray_box_entry(p, d)
        if hit is None:
            row["tes_box_entry_face"] = "MISS"
            row["entry_x_cm"] = row["entry_y_cm"] = row["entry_z_cm"] = math.nan
        else:
            row["tes_box_entry_face"] = hit[0]
            row["entry_x_cm"], row["entry_y_cm"], row["entry_z_cm"] = hit[1]
        row["inside_signal_entry_footprint"] = int(
            row["tes_box_entry_face"] == "x-"
            and footprint[0] <= float(row["entry_y_cm"]) <= footprint[1]
            and footprint[2] <= float(row["entry_z_cm"]) <= footprint[3]
        )

    summary: list[dict[str, object]] = []
    summary.append(
        {
            "section": "signal",
            "selection": "all EventList rays",
            "n_rows": len(signal_theta),
            "mission_counts_20d_baseline_live": "",
            "fraction_of_section_denominator": "1",
            "Neff": "",
            "dominant_event_fraction": "",
            "note": (
                f"theta_deg min/median/p95/p99/max={min(signal_theta):.9f}/"
                f"{quantile(signal_theta, 0.5):.9f}/{quantile(signal_theta, 0.95):.9f}/"
                f"{quantile(signal_theta, 0.99):.9f}/{max(signal_theta):.9f}; "
                f"entry faces={sorted(set(signal_entry_face))}"
            ),
        }
    )
    summary.append(
        {
            "section": "signal",
            "selection": "x- entry footprint bounding rectangle",
            "n_rows": len(signal_theta),
            "mission_counts_20d_baseline_live": "",
            "fraction_of_section_denominator": "1",
            "Neff": "",
            "dominant_event_fraction": "",
            "note": (
                f"x=-3.15 cm; y=[{footprint[0]:.9f},{footprint[1]:.9f}] cm; "
                f"z=[{footprint[2]:.9f},{footprint[3]:.9f}] cm"
            ),
        }
    )
    add_row(
        summary,
        "delayed_denominator",
        "all official selected delayed",
        len(all_rows),
        all_counts,
        all_counts,
        weighted(all_rows),
    )
    add_row(
        summary,
        "delayed_denominator",
        "unique traceable ANNI-to-TES direction",
        len(trace),
        trace_counts,
        all_counts,
        weighted(trace),
        "directional denominator for all following traceable selections",
    )
    add_row(
        summary,
        "delayed_denominator",
        "multi-ANNI direction UNKNOWN",
        len(unknown),
        sum(weighted(unknown)),
        all_counts,
        weighted(unknown),
        "count pessimistically accepted in the full-D footprint upper bound",
    )

    for angle in (0.459802, 1, 2, 3, 5, 10, 15, 20, 30, 45, 60, 90):
        selected = [r for r in trace if float(r["theta_from_signal_axis_deg"]) <= angle]
        add_row(
            summary,
            "delayed_axis_cone",
            f"theta_to_+x_IF <= {angle:g} deg",
            len(selected),
            sum(weighted(selected)),
            trace_counts,
            weighted(selected),
        )

    crosscheck_10 = [r for r in trace if float(r["theta_worldframe_crosscheck_deg"]) <= 10]
    mixed_invalid_10 = [r for r in trace if float(r["theta_mixed_frame_INVALID_deg"]) <= 10]
    add_row(
        summary,
        "coordinate_crosscheck",
        "WorldFrame dot: TES ray vs (+1/sqrt2,0,-1/sqrt2), <=10 deg",
        len(crosscheck_10),
        sum(weighted(crosscheck_10)),
        trace_counts,
        weighted(crosscheck_10),
        "must equal IF-frame dot against (+1,0,0)",
    )
    add_row(
        summary,
        "coordinate_crosscheck",
        "INVALID mixed-frame dot: tes_511_IF vs WorldFrame axis, <=10 deg",
        len(mixed_invalid_10),
        sum(weighted(mixed_invalid_10)),
        trace_counts,
        weighted(mixed_invalid_10),
        "coordinate-frame error retained only to reproduce the spurious 4-row result",
    )

    face_order = ("x-", "x+", "y-", "y+", "z-", "z+", "MISS")
    for face in face_order:
        selected = [r for r in trace if r["tes_box_entry_face"] == face]
        if selected:
            add_row(
                summary,
                "delayed_TES_envelope_entry_face",
                face,
                len(selected),
                sum(weighted(selected)),
                trace_counts,
                weighted(selected),
            )

    inside = [r for r in trace if int(r["inside_signal_entry_footprint"]) == 1]
    inside_counts = sum(weighted(inside))
    add_row(
        summary,
        "ideal_nearfield_mask",
        "traceable delayed entering x- inside full signal footprint bbox",
        len(inside),
        inside_counts,
        trace_counts,
        weighted(inside),
        "observed ideal binary-mask leakage; not a material attenuation prediction",
    )
    pessimistic_counts = inside_counts + sum(weighted(unknown))
    add_row(
        summary,
        "ideal_nearfield_mask",
        "same selection + all direction-UNKNOWN rows accepted",
        len(inside) + len(unknown),
        pessimistic_counts,
        all_counts,
        weighted(inside) + weighted(unknown),
        "pessimistic point estimate on the complete 420-row denominator",
    )

    # Weighted-Neff proxy only: it is intentionally labelled non-rigorous.
    zero_cone_95 = 1.0 - 0.05 ** (1.0 / neff(weighted(trace)))
    summary.append(
        {
            "section": "statistics_caveat",
            "selection": "zero observed delayed within 10-deg cone",
            "n_rows": 0,
            "mission_counts_20d_baseline_live": "0",
            "fraction_of_section_denominator": f"{zero_cone_95:.12g}",
            "Neff": f"{neff(weighted(trace)):.9f}",
            "dominant_event_fraction": "",
            "note": "95% zero-binomial proxy using Neff; heuristic, not a rigorous weighted confidence interval",
        }
    )

    prompt = 55398.979434
    delayed = all_counts
    # PA-X1 has no signal replay.  Its same-normalization optimistic gate must
    # therefore remain the baseline formal gate, not the AF1-Al candidate-own
    # signal gate (S20=1653.53937791, G=27341.9247429).
    baseline_s20 = 1645.387753
    gate = 27073.008579
    f_accept = pessimistic_counts / delayed
    mu_cu = 0.749
    summary.append(
        {
            "section": "budget_authority",
            "selection": "PA-X1 baseline formal signal gate",
            "n_rows": len(signal_theta),
            "mission_counts_20d_baseline_live": f"{gate:.12f}",
            "fraction_of_section_denominator": "1",
            "Neff": "",
            "dominant_event_fraction": "",
            "note": f"baseline S20={baseline_s20:.6f}; PA-X1 has straight-ray geometry only and no signal replay",
        }
    )
    summary.append(
        {
            "section": "budget_authority",
            "selection": "STALE_INVALID_FOR_PA-X1: AF1-Al candidate-own gate",
            "n_rows": 0,
            "mission_counts_20d_baseline_live": "27341.924742900000",
            "fraction_of_section_denominator": "",
            "Neff": "",
            "dominant_event_fraction": "",
            "note": "S20=1653.53937791 belongs only to the measured AF1-Al candidate and must not be transferred to PA-X1",
        }
    )

    budget_scenarios = (
        ("BG-J4_4cm", 4.0, (3.0, 3.1, 3.2, 4.0)),
        ("BG-TAU5_5p8314cm", 5.8314, (2.2, 2.3, 2.308064, 2.4)),
    )
    for label, bgo_chord, cu_chords in budget_scenarios:
        prompt_after_bgo = prompt * math.exp(-0.276 * bgo_chord)
        delayed_allow = gate - prompt_after_bgo
        required_t = (delayed_allow / delayed - f_accept) / (1.0 - f_accept)
        required_chord = -math.log(required_t) / mu_cu
        summary.append(
            {
                "section": "ideal_Cu_shadow_budget",
                "selection": f"{label}: required uniform rejected-angle Cu chord",
                "n_rows": 0,
                "mission_counts_20d_baseline_live": f"{delayed_allow:.12f}",
                "fraction_of_section_denominator": f"{required_chord:.12g}",
                "Neff": "",
                "dominant_event_fraction": "",
                "note": (
                    f"BGO_chord={bgo_chord:.4f} cm; prompt_after_BGO={prompt_after_bgo:.9f}; "
                    f"D_allowed={delayed_allow:.9f}; ideal required Cu chord={required_chord:.9f} cm"
                ),
            }
        )
        for chord in cu_chords:
            d_res = delayed * (f_accept + (1.0 - f_accept) * math.exp(-mu_cu * chord))
            total = prompt_after_bgo + d_res
            summary.append(
                {
                    "section": "ideal_Cu_shadow_budget",
                    "selection": f"{label}: uniform rejected-angle Cu chord {chord:g} cm",
                    "n_rows": len(all_rows),
                    "mission_counts_20d_baseline_live": f"{total:.12f}",
                    "fraction_of_section_denominator": f"{total / gate:.12g}",
                    "Neff": "",
                    "dominant_event_fraction": "",
                    "note": (
                        f"prompt_after_BGO={prompt_after_bgo:.9f}; delayed={d_res:.9f}; "
                        f"margin_to_gate={gate-total:.9f}; ideal required chord={required_chord:.9f} cm"
                    ),
                }
            )

        conservative_t = (
            delayed_allow / delayed - zero_cone_95
        ) / (1.0 - zero_cone_95)
        if conservative_t <= 0:
            conservative_note = (
                "no finite Cu chord: heuristic open-fraction upper exceeds the entire delayed allowance"
            )
        else:
            conservative_note = (
                f"heuristic required Cu chord={-math.log(conservative_t) / mu_cu:.9f} cm"
            )
        summary.append(
            {
                "section": "statistics_caveat",
                "selection": f"{label}: Cu chord if Neff zero-binomial proxy replaces observed open fraction",
                "n_rows": 0,
                "mission_counts_20d_baseline_live": "",
                "fraction_of_section_denominator": f"{conservative_t:.12g}",
                "Neff": f"{neff(weighted(trace)):.9f}",
                "dominant_event_fraction": "",
                "note": conservative_note,
            }
        )

    fields = list(summary[0])
    with OUT_SUMMARY.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(summary)

    hotspot_fields = [
        "family",
        "local_event_id",
        "source_parent_ZA",
        "source_volume",
        "source_material_group",
        "source_component_group",
        "mission_counts_20d_baseline_live",
        "theta_from_signal_axis_deg",
        "theta_worldframe_crosscheck_deg",
        "theta_mixed_frame_INVALID_deg",
        "tes_box_entry_face",
        "entry_x_cm",
        "entry_y_cm",
        "entry_z_cm",
        "inside_signal_entry_footprint",
    ]
    same_face = [r for r in trace if r["tes_box_entry_face"] == "x-"]
    same_face.sort(key=lambda r: float(r["mission_counts_20d_baseline_live"]), reverse=True)
    with OUT_HOTSPOTS.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=hotspot_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(same_face)

    print(f"signal={len(signal_theta)} max_theta={max(signal_theta):.12f}")
    print(f"delayed={len(all_rows)} trace={len(trace)} trace_counts={trace_counts:.12f}")
    print(f"footprint={footprint}")
    print(f"inside={len(inside)} counts={inside_counts:.12f} full_pess={pessimistic_counts/all_counts:.12g}")
    print(f"formal_baseline_gate={gate:.12f} from baseline_S20={baseline_s20:.6f}")


if __name__ == "__main__":
    main()
