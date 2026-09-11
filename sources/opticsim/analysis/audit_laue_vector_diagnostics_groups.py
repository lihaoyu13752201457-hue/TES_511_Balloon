#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Iterable


HC_KEV_A = 12.398419843320026


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def norm(a: tuple[float, float, float]) -> float:
    return math.sqrt(dot(a, a))


def unit(a: Iterable[float]) -> tuple[float, float, float]:
    v = tuple(float(x) for x in a)
    n = norm(v)
    if n == 0.0:
        raise ValueError("zero-length vector")
    return (v[0] / n, v[1] / n, v[2] / n)


def sub(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def mul(scale: float, a: tuple[float, float, float]) -> tuple[float, float, float]:
    return (scale * a[0], scale * a[1], scale * a[2])


def angle_rad(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.acos(max(-1.0, min(1.0, dot(unit(a), unit(b)))))


def reflect(direction: tuple[float, float, float], normal: tuple[float, float, float]) -> tuple[float, float, float]:
    k = unit(direction)
    n = unit(normal)
    return unit((k[0] - 2.0 * dot(k, n) * n[0], k[1] - 2.0 * dot(k, n) * n[1], k[2] - 2.0 * dot(k, n) * n[2]))


def wave_number_inv_a(energy_keV: float) -> float:
    return 2.0 * math.pi * energy_keV / HC_KEV_A


def qvalue(row: dict[str, str], key: str) -> float | None:
    value = row.get(key, "")
    return float(value) if value != "" else None


def quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, math.ceil(q * len(ordered)) - 1))
    return ordered[idx]


def stat(values: list[float]) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "max": 0.0, "p50": 0.0, "p90": 0.0, "p99": 0.0}
    return {
        "mean": sum(values) / len(values),
        "max": max(values),
        "p50": quantile(values, 0.50),
        "p90": quantile(values, 0.90),
        "p99": quantile(values, 0.99),
    }


def metric_row(key: str, rows: list[dict[str, float]]) -> dict[str, float | int | str]:
    def vals(name: str) -> list[float]:
        return [row[name] for row in rows]

    out: dict[str, float | int | str] = {"group": key, "n": len(rows)}
    for name in (
        "angle_code_vs_recorded_reflect_rad",
        "q_vector_error_invA",
        "q_minus_G_nominal_mag_invA",
        "q_minus_G_perturbed_mag_invA",
        "relative_bragg_residual_nominal",
        "relative_bragg_residual_perturbed",
        "q_parallel_G_perturbed_angle_rad",
        "mosaic_perturbation_rad",
    ):
        summary = stat(vals(name))
        for suffix, value in summary.items():
            out[f"{name}_{suffix}"] = value
    return out


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize Laue vector residuals by ring and tile.")
    parser.add_argument("--run-dir", default="runs/geant4_laue_darwin_guan_vector_diagnostics_prod100k")
    parser.add_argument("--out-dir", default="records/2026-05-24_optics_evidence_gap_closure/laue")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    history = read_csv(run_dir / "optics_history.csv")
    summary = read_json(run_dir / "summary.json")

    events: list[dict[str, float | int | str]] = []
    for row in history:
        if row["stage"] != "DIFFRACT":
            continue
        k_in = unit((float(row["ux_in"]), float(row["uy_in"]), float(row["uz_in"])))
        k_out = unit((float(row["ux_out"]), float(row["uy_out"]), float(row["uz_out"])))
        normal = unit((float(row["plane_normal_x"]), float(row["plane_normal_y"]), float(row["plane_normal_z"])))
        q_recorded = (
            float(row["scattering_q_vector_x_invA"]),
            float(row["scattering_q_vector_y_invA"]),
            float(row["scattering_q_vector_z_invA"]),
        )
        g_perturbed = (
            float(row["lattice_G_perturbed_x_invA"]),
            float(row["lattice_G_perturbed_y_invA"]),
            float(row["lattice_G_perturbed_z_invA"]),
        )
        q_calc = mul(wave_number_inv_a(float(row["E_keV"])), sub(k_out, k_in))
        events.append(
            {
                "event_id": int(row["event_id"]),
                "ring_id": int(row["ring_id"]),
                "tile_id": int(row["tile_id"]),
                "angle_code_vs_recorded_reflect_rad": angle_rad(k_out, reflect(k_in, normal)),
                "q_vector_error_invA": norm(sub(q_calc, q_recorded)),
                "q_minus_G_nominal_mag_invA": float(row["q_minus_G_nominal_mag_invA"]),
                "q_minus_G_perturbed_mag_invA": float(row["q_minus_G_perturbed_mag_invA"]),
                "relative_bragg_residual_nominal": float(row["relative_bragg_residual_nominal"]),
                "relative_bragg_residual_perturbed": float(row["relative_bragg_residual_perturbed"]),
                "q_parallel_G_perturbed_angle_rad": min(angle_rad(q_recorded, g_perturbed), angle_rad(mul(-1.0, q_recorded), g_perturbed)),
                "mosaic_perturbation_rad": float(row["mosaic_perturbation_rad"]),
            }
        )

    per_ring_groups: dict[str, list[dict[str, float]]] = defaultdict(list)
    per_tile_groups: dict[str, list[dict[str, float]]] = defaultdict(list)
    for event in events:
        per_ring_groups[str(event["ring_id"])].append(event)  # type: ignore[arg-type]
        per_tile_groups[f"{event['ring_id']}:{event['tile_id']}"].append(event)  # type: ignore[arg-type]

    per_ring = [metric_row(key, rows) for key, rows in sorted(per_ring_groups.items(), key=lambda item: int(item[0]))]
    per_tile = [metric_row(key, rows) for key, rows in sorted(per_tile_groups.items(), key=lambda item: tuple(map(int, item[0].split(":"))))]
    event_csv = out_dir / "laue_vector_diagnostics_prod100k_events.csv"
    ring_csv = out_dir / "laue_vector_diagnostics_prod100k_per_ring.csv"
    tile_csv = out_dir / "laue_vector_diagnostics_prod100k_per_tile.csv"
    write_csv(event_csv, events)
    write_csv(ring_csv, per_ring)
    write_csv(tile_csv, per_tile)

    worst_tiles = sorted(
        per_tile,
        key=lambda row: float(row["relative_bragg_residual_perturbed_max"]),
        reverse=True,
    )[:20]
    report = out_dir / "laue_vector_diagnostics_prod100k_group_residuals.md"
    lines = [
        "# Laue vector diagnostics production residuals",
        "",
        f"- run_dir: `{run_dir}`",
        f"- n_primaries: {summary.get('n_primaries')}",
        f"- diffracted_events: {len(events)}",
        f"- model: `{summary.get('model')}`",
        f"- event_csv: `{event_csv}`",
        f"- per_ring_csv: `{ring_csv}`",
        f"- per_tile_csv: `{tile_csv}`",
        "",
        "## Naming",
        "",
        "- `scattering_q_vector_* = |k| * (k_out - k_in)` in inverse Angstrom.",
        "- `reciprocal_vector_*` is retained as a backward-compatible alias for the same scattering vector.",
        "- `lattice_G_nominal_*` uses the unperturbed design-focus plane normal and fixed `|G|=2*pi/d_hkl`.",
        "- `lattice_G_perturbed_*` uses the recorded virtual-crystallite plane normal and the same fixed lattice magnitude.",
        "",
        "## Per-Ring Residuals",
        "",
        "| ring | n | max reflect angle rad | max q err invA | p99 q-G pert invA | max rel Bragg pert | p99 mosaic rad |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in per_ring:
        lines.append(
            f"| {row['group']} | {row['n']} | {row['angle_code_vs_recorded_reflect_rad_max']:.6g} | "
            f"{row['q_vector_error_invA_max']:.6g} | {row['q_minus_G_perturbed_mag_invA_p99']:.6g} | "
            f"{row['relative_bragg_residual_perturbed_max']:.6g} | {row['mosaic_perturbation_rad_p99']:.6g} |"
        )
    lines.extend(
        [
            "",
            "## Worst Tiles By Relative Bragg Residual",
            "",
            "| ring:tile | n | max rel Bragg pert | p99 q-G pert invA | max reflect angle rad |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in worst_tiles:
        lines.append(
            f"| {row['group']} | {row['n']} | {row['relative_bragg_residual_perturbed_max']:.6g} | "
            f"{row['q_minus_G_perturbed_mag_invA_p99']:.6g} | {row['angle_code_vs_recorded_reflect_rad_max']:.6g} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The recorded-plane reflection invariant is the direct vector-implementation check; it should be near zero.",
            "- `q-G` is intentionally reported separately. The current Guan-style virtual-crystallite model perturbs the plane normal and reflects elastically, while the Darwin-Hamilton branch probability is computed from scalar detuning around the nominal Bragg condition.",
            "- Therefore a nonzero `q-G` or `|q|-|G|` residual is expected for off-Bragg/mosaic-perturbed events. It is a model-systematics diagnostic, not a hidden retuning target.",
            "- Publication-grade closure would require a model that samples crystallite orientation and enforces the Ewald/Laue condition consistently, or explicitly justifies the present off-Bragg residual as an accepted approximation.",
            "",
        ]
    )
    report.write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
