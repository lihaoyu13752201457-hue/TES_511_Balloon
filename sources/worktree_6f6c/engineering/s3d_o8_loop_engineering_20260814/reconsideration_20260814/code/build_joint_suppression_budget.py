#!/usr/bin/env python3
"""Build an exact mission-count suppression frontier for S3d-O8.

This is a post-processing screen, not transport.  It preserves the official
geometry x mode x family x parent-ZA normalization boundary, folds every one
of the 420 selected delayed lineages through the retained 81-node mission
timeline, and then asks what *net* prompt/Cu/Nb+Mu suppression a candidate
would require.  No component scaling is treated as a physics prediction.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
OUT_DATA = PACKAGE / "data"
AUDIT_CODE = PACKAGE.parent / "agents" / "delayed"
sys.path.insert(0, str(AUDIT_CODE))
from analyze_delayed import material_label  # noqa: E402


SOURCE = Path(
    "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/"
    "particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813"
)
LINEAGE = SOURCE / "outputs/04_common_response/selected_background_w2_lineage.csv"
MISSION = SOURCE / "outputs/06_mission"
GEOMETRY = "S3d_O8"
EXPECTED_ROWS = 420
EXPECTED_DELAYED_CPS = 0.05447975222726722


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows = [
        row
        for row in read_csv(LINEAGE)
        if row["geometry"] == GEOMETRY and row["stream"] == "delayed"
    ]
    if len(rows) != EXPECTED_ROWS:
        raise RuntimeError(f"selected delayed row drift: {len(rows)}")

    events = [
        {
            "family": row["family"],
            "parent_ZA": int(row["source_parent_ZA"]),
            "material": material_label(row["source_volume"]),
            "weight_cps": float(row["event_weight_cps"]),
        }
        for row in rows
    ]
    static_total = math.fsum(event["weight_cps"] for event in events)
    if not math.isclose(static_total, EXPECTED_DELAYED_CPS, abs_tol=1e-14):
        raise RuntimeError(f"static delayed drift: {static_total}")

    timeline = [
        row for row in read_csv(MISSION / "mission_timeline.csv")
        if row["geometry"] == GEOMETRY
    ]
    timeline.sort(key=lambda row: int(row["time_bin_id"]))
    if len(timeline) != 81:
        raise RuntimeError(f"timeline row drift: {len(timeline)}")

    scale_rows = [
        row for row in read_csv(MISSION / "family_parent_activity_by_time.csv")
        if row["geometry"] == GEOMETRY
    ]
    scales = {
        (int(row["time_bin_id"]), row["incident_family"], int(row["source_parent_ZA"])):
        float(row["activity_scale_to_constant_environment_day15_inventory"])
        for row in scale_rows
    }
    dt = [float(row["trajectory_quadrature_weight_s"]) for row in timeline]
    live = [float(row["accidental_live_factor"]) for row in timeline]

    def mission_counts(materials: set[str] | None = None) -> float:
        chosen = events if materials is None else [
            event for event in events if event["material"] in materials
        ]
        return math.fsum(
            math.fsum(
                event["weight_cps"]
                * scales[(node, event["family"], event["parent_ZA"])]
                for event in chosen
            )
            * dt[node]
            * live[node]
            for node in range(81)
        )

    delayed_total = mission_counts()
    counts_by_material = {
        material: mission_counts({material})
        for material in sorted({event["material"] for event in events})
    }
    material_closure = math.fsum(counts_by_material.values())
    if not math.isclose(material_closure, delayed_total, abs_tol=1e-8):
        raise RuntimeError(f"material closure drift: {material_closure} vs {delayed_total}")

    prompt_counts = math.fsum(
        float(row["prompt_final_cps_noacc"])
        * float(row["accidental_live_factor"])
        * float(row["trajectory_quadrature_weight_s"])
        for row in timeline
    )
    summary = json.loads((MISSION / "summary.json").read_text(encoding="utf-8"))
    signal_counts = float(summary["geometries"][GEOMETRY]["source_counts_20d"])
    exact_gate = (signal_counts / 10.0) ** 2
    baseline_total = prompt_counts + delayed_total
    official_total = float(summary["geometries"][GEOMETRY]["background_counts_20d"])
    if not math.isclose(baseline_total, official_total, abs_tol=1e-8):
        raise RuntimeError("prompt + delayed does not close to mission summary")

    cu = counts_by_material["Copper"]
    nb = counts_by_material["Nb"]
    mu = counts_by_material["Mu-metal"]
    magnetic = nb + mu
    fixed_other = delayed_total - cu - magnetic

    frontier: list[dict[str, Any]] = []
    for signal_retention in (1.0, 0.95, 0.90):
        gate = exact_gate * signal_retention**2
        for cu_i in range(21):
            cu_suppression = cu_i / 20.0
            for mag_i in range(21):
                magnetic_suppression = mag_i / 20.0
                delayed_residual = (
                    fixed_other
                    + cu * (1.0 - cu_suppression)
                    + magnetic * (1.0 - magnetic_suppression)
                )
                required_prompt_suppression = (
                    1.0 - (gate - delayed_residual) / prompt_counts
                )
                frontier.append(
                    {
                        "signal_retention": signal_retention,
                        "net_copper_suppression": cu_suppression,
                        "net_nb_plus_mu_suppression": magnetic_suppression,
                        "delayed_residual_counts": delayed_residual,
                        "candidate_gate_counts": gate,
                        "required_prompt_suppression_raw": required_prompt_suppression,
                        "required_prompt_suppression_clipped": min(
                            1.0, max(0.0, required_prompt_suppression)
                        ),
                        "feasible_with_prompt_zero": int(required_prompt_suppression <= 1.0),
                        "no_prompt_reduction_needed": int(required_prompt_suppression <= 0.0),
                    }
                )

    hypotheses = [
        ("baseline", 0.0, 0.0, 0.0, 1.0),
        ("ideal_all_Cu_only", 1.0, 0.0, 1.0, 1.0),
        ("TC_AF1_screen_floor", 0.90, 0.50, 0.70, 1.0),
        ("TC_AF1_screen_nominal", 0.95, 0.75, 0.80, 0.95),
        ("TC_AF1_screen_strong", 1.0, 0.75, 0.90, 0.95),
    ]
    screens: list[dict[str, Any]] = []
    for name, s_cu, s_mag, s_prompt, s_signal in hypotheses:
        residual_delayed = fixed_other + cu * (1 - s_cu) + magnetic * (1 - s_mag)
        residual_prompt = prompt_counts * (1 - s_prompt)
        residual_total = residual_delayed + residual_prompt
        gate = exact_gate * s_signal**2
        screens.append(
            {
                "screen": name,
                "net_copper_suppression": s_cu,
                "net_nb_plus_mu_suppression": s_mag,
                "net_prompt_suppression": s_prompt,
                "signal_retention": s_signal,
                "residual_prompt_counts": residual_prompt,
                "residual_delayed_counts": residual_delayed,
                "residual_total_counts": residual_total,
                "candidate_gate_counts": gate,
                "gate_ratio": residual_total / gate,
                "arithmetic_pass": int(residual_total <= gate),
                "status": "HYPOTHESIS_ONLY__NOT_A_TRANSPORT_RESULT",
            }
        )

    OUT_DATA.mkdir(parents=True, exist_ok=True)
    write_csv(OUT_DATA / "joint_suppression_frontier.csv", frontier)
    write_csv(OUT_DATA / "joint_candidate_hypothesis_screens.csv", screens)
    summary_out = {
        "schema_version": 1,
        "geometry": GEOMETRY,
        "boundary": "official S3d_O8 delayed lineage x exact family x parent_ZA x 81 mission nodes",
        "official_selected_rows": len(events),
        "mission_counts": {
            "signal": signal_counts,
            "prompt": prompt_counts,
            "delayed": delayed_total,
            "background": baseline_total,
            "gate": exact_gate,
            "delayed_copper": cu,
            "delayed_nb": nb,
            "delayed_mu": mu,
            "delayed_nb_plus_mu": magnetic,
            "delayed_fixed_other": fixed_other,
        },
        "counts_by_material": counts_by_material,
        "interpretation_guard": (
            "Suppression coordinates are net candidate outcomes, not mass-scaling predictions; "
            "they include any activation or host migration only after candidate transport measures it."
        ),
    }
    (OUT_DATA / "joint_suppression_budget_summary.json").write_text(
        json.dumps(summary_out, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        "PASS: "
        f"P={prompt_counts:.9f}, D={delayed_total:.9f}, Cu={cu:.9f}, "
        f"Nb+Mu={magnetic:.9f}, fixed={fixed_other:.9f}, gate={exact_gate:.9f}"
    )


if __name__ == "__main__":
    main()
