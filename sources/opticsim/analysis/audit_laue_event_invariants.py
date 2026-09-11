#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Iterable


HC_KEV_A = 12.398419843320026


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def unit(values: Iterable[float]) -> tuple[float, float, float]:
    xyz = tuple(float(v) for v in values)
    norm = math.sqrt(sum(v * v for v in xyz))
    if norm == 0.0:
        raise ValueError("zero-length vector")
    return (xyz[0] / norm, xyz[1] / norm, xyz[2] / norm)


def dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def sub(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def mul(scale: float, a: tuple[float, float, float]) -> tuple[float, float, float]:
    return (scale * a[0], scale * a[1], scale * a[2])


def norm(a: tuple[float, float, float]) -> float:
    return math.sqrt(dot(a, a))


def angle_rad(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    value = max(-1.0, min(1.0, dot(unit(a), unit(b))))
    return math.acos(value)


def bragg_angle_rad(energy_keV: float, d_spacing_a: float) -> float:
    wavelength_a = HC_KEV_A / energy_keV
    arg = wavelength_a / (2.0 * d_spacing_a)
    return math.asin(max(-1.0, min(1.0, arg)))


def wave_number_inv_a(energy_keV: float) -> float:
    return 2.0 * math.pi * energy_keV / HC_KEV_A


def reflect(direction: tuple[float, float, float], normal: tuple[float, float, float]) -> tuple[float, float, float]:
    k = unit(direction)
    n = unit(normal)
    return unit((k[0] - 2.0 * dot(k, n) * n[0], k[1] - 2.0 * dot(k, n) * n[1], k[2] - 2.0 * dot(k, n) * n[2]))


def quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, math.ceil(q * len(ordered)) - 1))
    return ordered[idx]


def stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {"max": 0.0, "p50": 0.0, "p90": 0.0, "p99": 0.0}
    return {
        "max": max(values),
        "p50": quantile(values, 0.50),
        "p90": quantile(values, 0.90),
        "p99": quantile(values, 0.99),
    }


def format_stats(values: list[float]) -> str:
    s = stats(values)
    return f"max={s['max']:.6g}, p50={s['p50']:.6g}, p90={s['p90']:.6g}, p99={s['p99']:.6g}"


def optional_float(row: dict[str, str], key: str) -> float | None:
    value = row.get(key, "")
    if value == "":
        return None
    return float(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit event-level Laue direction invariants from existing run CSVs.")
    parser.add_argument("--run-dir", default="runs/geant4_laue_multiring_darwin")
    parser.add_argument("--ring-config", default="data/laue/ge111_480_550keV_multiring_darwin_config.csv")
    parser.add_argument("--out", default="records/2026-05-24_optics_audit_followup/laue_event_invariants.md")
    parser.add_argument("--csv", default="")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    history_path = run_dir / "optics_history.csv"
    phase_path = run_dir / "phase_space.csv"
    summary_path = run_dir / "summary.json"
    out_path = Path(args.out)
    csv_path = Path(args.csv) if args.csv else out_path.with_suffix(".csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    summary = read_json(summary_path)
    focal_mm = float(summary.get("focal_length_mm", 8300.0))
    rings = {int(row["ring_id"]): row for row in read_csv(Path(args.ring_config))}
    phase_by_event = {int(row["event_id"]): row for row in read_csv(phase_path)}
    history = read_csv(history_path)

    rows: list[dict[str, object]] = []
    missing_phase = 0
    for row in history:
        if row["stage"] != "DIFFRACT":
            continue
        event_id = int(row["event_id"])
        ring_id = int(row["ring_id"])
        pos = (float(row["x_mm"]), float(row["y_mm"]), float(row["z_mm"]))
        k_in = unit((float(row["ux_in"]), float(row["uy_in"]), float(row["uz_in"])))
        k_out = unit((float(row["ux_out"]), float(row["uy_out"]), float(row["uz_out"])))
        phase = phase_by_event.get(event_id)
        if phase is None:
            missing_phase += 1
            focus = (0.0, 0.0, focal_mm)
        else:
            focus = (float(phase["x_mm"]), float(phase["y_mm"]), float(phase["z_mm"]))
        actual_focus_dir = unit((focus[0] - pos[0], focus[1] - pos[1], focus[2] - pos[2]))
        nominal_focus_dir = unit((-pos[0], -pos[1], focal_mm - pos[2]))

        implied_normal = unit(sub(k_in, k_out))
        reflected = reflect(k_in, implied_normal)
        ring = rings[ring_id]
        theta_b = bragg_angle_rad(float(row["E_keV"]), float(ring["d_spacing_A"]))
        theta_local = 0.5 * math.atan2(math.hypot(pos[0], pos[1]), focal_mm - pos[2])
        recorded_reflect_angle = None
        recorded_normal_norm_error = None
        recorded_q_vector_error = None
        recorded_q_mag_expected_diff = None
        recorded_q_parallel_angle = None
        q_minus_g_nominal = optional_float(row, "q_minus_G_nominal_mag_invA")
        q_minus_g_perturbed = optional_float(row, "q_minus_G_perturbed_mag_invA")
        relative_bragg_nominal = optional_float(row, "relative_bragg_residual_nominal")
        relative_bragg_perturbed = optional_float(row, "relative_bragg_residual_perturbed")
        recorded_model = row.get("vector_diagnostic_model", "")
        recorded_mosaic = optional_float(row, "mosaic_perturbation_rad")
        if row.get("plane_normal_x", ""):
            recorded_normal_raw = (
                float(row["plane_normal_x"]),
                float(row["plane_normal_y"]),
                float(row["plane_normal_z"]),
            )
            recorded_normal_norm_error = abs(norm(recorded_normal_raw) - 1.0)
            recorded_normal = unit(recorded_normal_raw)
            recorded_reflect_angle = angle_rad(k_out, reflect(k_in, recorded_normal))
            q_calc = mul(wave_number_inv_a(float(row["E_keV"])), sub(k_out, k_in))
            q_x_key = "scattering_q_vector_x_invA" if row.get("scattering_q_vector_x_invA", "") else "reciprocal_vector_x_invA"
            q_y_key = "scattering_q_vector_y_invA" if row.get("scattering_q_vector_y_invA", "") else "reciprocal_vector_y_invA"
            q_z_key = "scattering_q_vector_z_invA" if row.get("scattering_q_vector_z_invA", "") else "reciprocal_vector_z_invA"
            if row.get(q_x_key, ""):
                q_recorded = (
                    float(row[q_x_key]),
                    float(row[q_y_key]),
                    float(row[q_z_key]),
                )
                recorded_q_vector_error = norm(sub(q_calc, q_recorded))
                if norm(q_recorded) > 0.0:
                    recorded_q_parallel_angle = min(
                        angle_rad(q_recorded, recorded_normal),
                        angle_rad(mul(-1.0, q_recorded), recorded_normal),
                    )
            if row.get("reciprocal_vector_expected_mag_invA", ""):
                recorded_q_mag_expected_diff = abs(
                    float(row["reciprocal_vector_mag_invA"]) - float(row["reciprocal_vector_expected_mag_invA"])
                )
        rows.append(
            {
                "event_id": event_id,
                "ring_id": ring_id,
                "tile_id": int(row["tile_id"]),
                "energy_keV": float(row["E_keV"]),
                "norm_error": abs(math.sqrt(dot(k_out, k_out)) - 1.0),
                "angle_code_vs_actual_focus_rad": angle_rad(k_out, actual_focus_dir),
                "angle_code_vs_nominal_focus_rad": angle_rad(k_out, nominal_focus_dir),
                "angle_code_vs_implied_reflect_rad": angle_rad(k_out, reflected),
                "theta_B_rad": theta_b,
                "theta_local_rad": theta_local,
                "delta_theta_history_rad": float(row["grazing_angle_rad"]),
                "delta_theta_recomputed_rad": theta_local - theta_b,
                "delta_theta_abs_diff_rad": abs(float(row["grazing_angle_rad"]) - (theta_local - theta_b)),
                "implied_plane_normal_x": implied_normal[0],
                "implied_plane_normal_y": implied_normal[1],
                "implied_plane_normal_z": implied_normal[2],
                "recorded_vector_diagnostic_model": recorded_model,
                "recorded_plane_normal_norm_error": recorded_normal_norm_error,
                "angle_code_vs_recorded_reflect_rad": recorded_reflect_angle,
                "recorded_q_vector_error_invA": recorded_q_vector_error,
                "recorded_q_parallel_angle_rad": recorded_q_parallel_angle,
                "recorded_q_mag_minus_expected_abs_invA": recorded_q_mag_expected_diff,
                "q_minus_G_nominal_mag_invA": q_minus_g_nominal,
                "q_minus_G_perturbed_mag_invA": q_minus_g_perturbed,
                "relative_bragg_residual_nominal": relative_bragg_nominal,
                "relative_bragg_residual_perturbed": relative_bragg_perturbed,
                "recorded_mosaic_perturbation_rad": recorded_mosaic,
            }
        )

    fields = list(rows[0].keys()) if rows else []
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    norm_errors = [float(row["norm_error"]) for row in rows]
    actual_focus_angles = [float(row["angle_code_vs_actual_focus_rad"]) for row in rows]
    nominal_focus_angles = [float(row["angle_code_vs_nominal_focus_rad"]) for row in rows]
    implied_reflect_angles = [float(row["angle_code_vs_implied_reflect_rad"]) for row in rows]
    delta_diffs = [float(row["delta_theta_abs_diff_rad"]) for row in rows]
    recorded_reflect_angles = [
        float(row["angle_code_vs_recorded_reflect_rad"])
        for row in rows
        if row["angle_code_vs_recorded_reflect_rad"] is not None
    ]
    recorded_normal_norm_errors = [
        float(row["recorded_plane_normal_norm_error"])
        for row in rows
        if row["recorded_plane_normal_norm_error"] is not None
    ]
    recorded_q_vector_errors = [
        float(row["recorded_q_vector_error_invA"])
        for row in rows
        if row["recorded_q_vector_error_invA"] is not None
    ]
    recorded_q_parallel_angles = [
        float(row["recorded_q_parallel_angle_rad"])
        for row in rows
        if row["recorded_q_parallel_angle_rad"] is not None
    ]
    recorded_q_mag_expected_diffs = [
        float(row["recorded_q_mag_minus_expected_abs_invA"])
        for row in rows
        if row["recorded_q_mag_minus_expected_abs_invA"] is not None
    ]
    q_minus_g_nominal_values = [
        float(row["q_minus_G_nominal_mag_invA"])
        for row in rows
        if row["q_minus_G_nominal_mag_invA"] is not None
    ]
    q_minus_g_perturbed_values = [
        float(row["q_minus_G_perturbed_mag_invA"])
        for row in rows
        if row["q_minus_G_perturbed_mag_invA"] is not None
    ]
    relative_bragg_nominal_values = [
        float(row["relative_bragg_residual_nominal"])
        for row in rows
        if row["relative_bragg_residual_nominal"] is not None
    ]
    relative_bragg_perturbed_values = [
        float(row["relative_bragg_residual_perturbed"])
        for row in rows
        if row["relative_bragg_residual_perturbed"] is not None
    ]
    recorded_mosaic_values = [
        float(row["recorded_mosaic_perturbation_rad"])
        for row in rows
        if row["recorded_mosaic_perturbation_rad"] is not None
    ]
    worst_actual = max(rows, key=lambda row: float(row["angle_code_vs_actual_focus_rad"]), default=None)

    vector_tolerance_rad = 1.0e-7
    q_tolerance_inv_a = 1.0e-8
    if recorded_reflect_angles:
        strict_vector_status = (
            "PASS_RECORDED_PLANE_NORMAL"
            if max(recorded_reflect_angles) < vector_tolerance_rad
            and max(recorded_normal_norm_errors or [0.0]) < 1.0e-10
            and max(recorded_q_vector_errors or [0.0]) < q_tolerance_inv_a
            else "FAIL_RECORDED_PLANE_NORMAL"
        )
    else:
        strict_vector_status = "UNKNOWN_NOT_RECORDED"
    direction_model = str(summary.get("plane_normal_diagnostic_model", "focus_preserving_scaffold_existing_history"))
    # The run CSV stores decimal text, so a few 1e-8 rad angular residues are
    # expected after reloading vectors from text rather than binary doubles.
    focus_tolerance_rad = 1.0e-7
    if actual_focus_angles and max(actual_focus_angles) < focus_tolerance_rad:
        focus_status = "PASS"
    else:
        focus_status = "WARN"

    lines = [
        "# Laue event-level direction invariant audit",
        "",
        f"- run_dir: `{run_dir}`",
        f"- history: `{history_path}`",
        f"- phase_space: `{phase_path}`",
        f"- output_csv: `{csv_path}`",
        f"- diffracted_events_checked: {len(rows)}",
        f"- missing_phase_rows: {missing_phase}",
        f"- direction_model: `{direction_model}`",
        f"- strict_vector_diffraction_status: `{strict_vector_status}`",
        f"- recorded_plane_normal_rows: {len(recorded_reflect_angles)}",
        "",
        "## Result",
        "",
        (
            "When `plane_normal_*` and `reciprocal_vector_*` columns are present, this audit checks the emitted "
            "`k_out` against reflection across the recorded plane normal and checks the recorded reciprocal vector "
            "against `|k|*(k_out-k_in)`. Older runs without those columns remain limited to focus and scalar-Bragg checks."
        ),
        "",
        "| metric | value |",
        "|---|---:|",
        f"| k_out norm error | {format_stats(norm_errors)} |",
        f"| angle k_out vs actual phase-space focus | {format_stats(actual_focus_angles)} |",
        f"| angle k_out vs nominal optical-axis focus | {format_stats(nominal_focus_angles)} |",
        f"| angle k_out vs implied reflection plane | {format_stats(implied_reflect_angles)} |",
        f"| angle k_out vs recorded plane-normal reflection | {format_stats(recorded_reflect_angles)} |",
        f"| recorded plane-normal norm error | {format_stats(recorded_normal_norm_errors)} |",
        f"| recorded reciprocal-vector error | {format_stats(recorded_q_vector_errors)} |",
        f"| recorded reciprocal-vector parallel angle | {format_stats(recorded_q_parallel_angles)} |",
        f"| abs(recorded q magnitude - ideal Bragg q magnitude) | {format_stats(recorded_q_mag_expected_diffs)} |",
        f"| q minus nominal lattice G magnitude | {format_stats(q_minus_g_nominal_values)} |",
        f"| q minus perturbed lattice G magnitude | {format_stats(q_minus_g_perturbed_values)} |",
        f"| relative Bragg residual vs nominal G | {format_stats(relative_bragg_nominal_values)} |",
        f"| relative Bragg residual vs perturbed G | {format_stats(relative_bragg_perturbed_values)} |",
        f"| recorded mosaic perturbation | {format_stats(recorded_mosaic_values)} |",
        f"| abs(history delta_theta - recomputed delta_theta) | {format_stats(delta_diffs)} |",
        "",
        f"Focus-direction invariant: **{focus_status}** at tolerance `{focus_tolerance_rad:g} rad`",
        f"Recorded plane-normal vector invariant: **{strict_vector_status}** at tolerance `{vector_tolerance_rad:g} rad`",
        "",
        "## Worst event",
        "",
    ]
    if worst_actual:
        lines.extend(
            [
                "| field | value |",
                "|---|---:|",
                *[f"| {key} | {value} |" for key, value in worst_actual.items()],
                "",
            ]
        )
    lines.extend(
        [
            "## Claim boundary",
            "",
            "- `PASS_RECORDED_PLANE_NORMAL` means the checked run emits a plane-normal diagnostic and `k_out` is consistent with reflection across that recorded normal.",
            "- A table-driven run may still be a focus-preserving scaffold if its recorded diagnostic model is a design-focus normal with separate focal-plane mosaic jitter.",
            "- A Guan-style run with `guan_virtual_crystallite_plane_normal` can support a strict recorded-vector claim for the checked event stream; publication-grade validation still depends on material/systematics evidence.",
            "- Nonzero `q-G` and relative Bragg residuals expose off-Bragg/mosaic detuning in the current virtual-crystallite model; they are not hidden by the reflection-angle invariant.",
            "",
        ]
    )
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
