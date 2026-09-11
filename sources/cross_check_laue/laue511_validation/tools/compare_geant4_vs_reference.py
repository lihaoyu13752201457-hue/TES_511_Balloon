#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from laue511.bragg import bragg_angle_rad, focal_length_mm_from_radius
from laue511.metrics import binomial_z, branch_fractions, mean
from laue511.phase_space import read_rows, summarize_history, validate_phase_space
from laue511.probabilities import darwin_hamilton_mosaic_probabilities
from laue511.rings import find_ring, load_ring_config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--geant4-run", required=True)
    parser.add_argument("--config", default=str(ROOT / "data/laue/ge111_480_550keV_multiring_darwin_config.csv"))
    parser.add_argument("--out", required=True)
    parser.add_argument("--max-rows", type=int, default=0, help="0 means all rows")
    args = parser.parse_args()

    run_dir = Path(args.geant4_run)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    rings = load_ring_config(args.config)
    history_path = run_dir / "optics_history.csv"
    phase_path = run_dir / "phase_space.csv"
    transmitted_path = run_dir / "transmitted_space.csv"
    history = read_rows(history_path)
    if args.max_rows:
        history = history[: args.max_rows]

    per_ring_counts: dict[int, Counter[str]] = defaultdict(Counter)
    per_ring_recorded: dict[int, dict[str, list[float]]] = defaultdict(_prob_lists)
    per_ring_reference: dict[int, dict[str, list[float]]] = defaultdict(_prob_lists)
    max_abs_delta = {"p_diff": 0.0, "p_abs": 0.0, "p_trans": 0.0}

    for row in history:
        ring_id = int(row["ring_id"])
        ring = find_ring(rings, ring_id)
        stage = row.get("stage") or row.get("branch") or ""
        delta_theta = _float_field(row, "delta_theta_model_rad", "delta_theta_actual_rad", "grazing_angle_rad")
        ref = darwin_hamilton_mosaic_probabilities(
            E_keV=float(row.get("E_keV") or ring.design_energy_keV),
            d_spacing_A=ring.d_spacing_A,
            thickness_mm=ring.thickness_mm,
            delta_theta_rad=delta_theta,
        )
        rec = {
            "p_diff": _float_field(row, "p_reflect", "p_diff", "p_diff_raw"),
            "p_abs": _float_field(row, "p_absorb", "p_abs", "p_abs_raw"),
            "p_trans": _float_field(row, "p_transmit", "p_trans", "p_trans_raw"),
        }
        ref_probs = {"p_diff": ref.p_diff, "p_abs": ref.p_abs, "p_trans": ref.p_trans}
        per_ring_counts[ring_id][stage] += 1
        for key in ("p_diff", "p_abs", "p_trans"):
            per_ring_recorded[ring_id][key].append(rec[key])
            per_ring_reference[ring_id][key].append(ref_probs[key])
            max_abs_delta[key] = max(max_abs_delta[key], abs(rec[key] - ref_probs[key]))

    ring_metrics = []
    for ring_id in sorted(per_ring_counts):
        counts = per_ring_counts[ring_id]
        n = sum(counts.values())
        mean_ref = {key: mean(per_ring_reference[ring_id][key]) for key in ("p_diff", "p_abs", "p_trans")}
        mean_rec = {key: mean(per_ring_recorded[ring_id][key]) for key in ("p_diff", "p_abs", "p_trans")}
        ring_metrics.append(
            {
                "ring_id": ring_id,
                "n": n,
                "counts": dict(counts),
                "branch_fractions": branch_fractions(counts),
                "mean_recorded": mean_rec,
                "mean_reference": mean_ref,
                "mean_abs_probability_delta": {
                    key: mean(abs(a - b) for a, b in zip(per_ring_recorded[ring_id][key], per_ring_reference[ring_id][key]))
                    for key in ("p_diff", "p_abs", "p_trans")
                },
                "branch_z": {
                    "DIFFRACT": binomial_z(counts.get("DIFFRACT", 0), n, mean_ref["p_diff"]),
                    "ABSORB": binomial_z(counts.get("ABSORB", 0), n, mean_ref["p_abs"]),
                    "TRANSMIT": binomial_z(counts.get("TRANSMIT", 0), n, mean_ref["p_trans"]),
                },
            }
        )

    phase_validation = validate_phase_space(phase_path) if phase_path.exists() else {"ok": False, "errors": ["missing phase_space.csv"]}
    transmitted_validation = validate_phase_space(transmitted_path) if transmitted_path.exists() else {"ok": False, "errors": ["missing transmitted_space.csv"]}
    history_summary = summarize_history(history_path)
    columns = set(history_summary["columns"])
    focal_check = _focal_length_check(rings, run_dir / "summary.json")
    geant4_summary = _load_json(run_dir / "summary.json")
    vector_diagnostics = _vector_diagnostics_summary(history, columns)
    metrics = {
        "geant4_run": str(run_dir),
        "geant4_summary": geant4_summary,
        "ring_config": args.config,
        "n_history_rows_checked": len(history),
        "probability_max_abs_delta": max_abs_delta,
        "ring_metrics": ring_metrics,
        "phase_space_validation": phase_validation,
        "transmitted_space_validation": transmitted_validation,
        "history_schema": {
            "vector_diagnostics_present": "plane_normal_x" in columns and "relative_bragg_residual_perturbed" in columns,
            "columns": history_summary["columns"],
        },
        "vector_diagnostics": vector_diagnostics,
        "focal_length_check": focal_check,
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_summary(out_dir / "summary.md", metrics)
    print(json.dumps({"out": str(out_dir), "n_history_rows_checked": len(history), "max_abs_delta": max_abs_delta}, indent=2, sort_keys=True))
    return 0


def _prob_lists() -> dict[str, list[float]]:
    return {"p_diff": [], "p_abs": [], "p_trans": []}


def _focal_length_check(rings: list[object], summary_path: Path) -> dict[str, object]:
    inferred = []
    for ring in rings:
        theta = bragg_angle_rad(ring.design_energy_keV, ring.d_spacing_A)
        inferred.append(focal_length_mm_from_radius(ring.radius_mm, theta))
    geant4_focal = None
    if summary_path.exists():
        geant4_focal = json.loads(summary_path.read_text(encoding="utf-8")).get("focal_length_mm")
    mean_inferred = mean(inferred)
    return {
        "ring_config_focal_length_mm_mean": mean_inferred,
        "ring_config_focal_length_mm_min": min(inferred),
        "ring_config_focal_length_mm_max": max(inferred),
        "geant4_summary_focal_length_mm": geant4_focal,
        "relative_delta_vs_geant4_summary": None if geant4_focal is None else (mean_inferred - float(geant4_focal)) / mean_inferred,
    }


def _load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _vector_diagnostics_summary(rows: list[dict[str, str]], columns: set[str]) -> dict[str, object]:
    required = {
        "vector_diagnostic_model",
        "angle_code_vs_recorded_reflect_rad",
        "elastic_error",
        "relative_bragg_residual_nominal",
        "relative_bragg_residual_perturbed",
    }
    if not required.issubset(columns):
        return {"available": False}
    diffracted = [row for row in rows if row.get("stage") == "DIFFRACT"]
    with_model = [row for row in diffracted if row.get("vector_diagnostic_model")]
    return {
        "available": True,
        "n_diffracted": len(diffracted),
        "n_diffracted_with_model": len(with_model),
        "models": sorted({row["vector_diagnostic_model"] for row in with_model}),
        "max_angle_code_vs_recorded_reflect_rad": max(
            (_float_field(row, "angle_code_vs_recorded_reflect_rad") for row in with_model),
            default=0.0,
        ),
        "max_elastic_error": max((_float_field(row, "elastic_error") for row in with_model), default=0.0),
        "max_relative_bragg_residual_nominal": max(
            (_float_field(row, "relative_bragg_residual_nominal") for row in with_model),
            default=0.0,
        ),
        "max_relative_bragg_residual_perturbed": max(
            (_float_field(row, "relative_bragg_residual_perturbed") for row in with_model),
            default=0.0,
        ),
    }


def _float_field(row: dict[str, str], *names: str) -> float:
    for name in names:
        if name in row and row[name] != "":
            return float(row[name])
    return 0.0


def _write_summary(path: Path, metrics: dict[str, object]) -> None:
    lines = [
        "# Geant4 vs Python Laue reference",
        "",
        f"Geant4 run: `{metrics['geant4_run']}`",
        f"Rows checked: {metrics['n_history_rows_checked']}",
        "",
        "## Probability kernel agreement",
        "",
    ]
    for key, value in metrics["probability_max_abs_delta"].items():
        lines.append(f"- {key}: max abs delta {value:.6g}")
    lines.extend(["", "## Ring branch checks", ""])
    for item in metrics["ring_metrics"]:
        frac = item["branch_fractions"]
        z = item["branch_z"]
        lines.append(
            f"- ring {item['ring_id']}: N={item['n']}, "
            f"diff={frac.get('DIFFRACT', 0.0):.6f} (z={z['DIFFRACT']:.2f}), "
            f"abs={frac.get('ABSORB', 0.0):.6f} (z={z['ABSORB']:.2f}), "
            f"trans={frac.get('TRANSMIT', 0.0):.6f} (z={z['TRANSMIT']:.2f})"
        )
    lines.extend(
        [
            "",
            "## Focal Length",
            "",
        ]
    )
    focal = metrics["focal_length_check"]
    lines.append(f"- ring CSV inferred focal length mean: {focal['ring_config_focal_length_mm_mean']:.6f} mm")
    lines.append(f"- Geant4 summary focal length: {focal['geant4_summary_focal_length_mm']} mm")
    if focal["relative_delta_vs_geant4_summary"] is not None:
        lines.append(f"- relative delta: {focal['relative_delta_vs_geant4_summary']:.6g}")
    lines.extend(
        [
            "",
            "## Schema",
            "",
            f"- phase_space.csv ok: {metrics['phase_space_validation']['ok']}",
            f"- transmitted_space.csv ok: {metrics['transmitted_space_validation']['ok']}",
            f"- vector diagnostics present in optics_history.csv: {metrics['history_schema']['vector_diagnostics_present']}",
        ]
    )
    vector = metrics["vector_diagnostics"]
    if vector.get("available"):
        lines.append(f"- diffracted rows with vector model: {vector['n_diffracted_with_model']}/{vector['n_diffracted']}")
        lines.append(f"- max angle_code_vs_recorded_reflect_rad: {vector['max_angle_code_vs_recorded_reflect_rad']:.6g}")
        lines.append(f"- max relative_bragg_residual_perturbed: {vector['max_relative_bragg_residual_perturbed']:.6g}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
