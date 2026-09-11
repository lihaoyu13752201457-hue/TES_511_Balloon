#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from laue511.geometry import plane_hit_at_z
from laue511.metrics import containment_diameter_mm
from laue511.rings import load_ring_config


DEFAULT_RUN = Path("/home/ubuntu/opticsim/runs/geant4_laue_darwin_guan_process")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--geant4-run", default=str(DEFAULT_RUN))
    parser.add_argument("--config", default=str(ROOT / "data/laue/ge111_480_550keV_multiring_darwin_config.csv"))
    parser.add_argument("--out-dir", default=str(ROOT / "reports/full_lens_observables"))
    args = parser.parse_args()

    run_dir = Path(args.geant4_run)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    metrics, per_ring_rows = audit_full_lens_observables(run_dir, Path(args.config))
    _write_per_ring_csv(out_dir / "per_ring_effective_area.csv", per_ring_rows)
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_summary(out_dir / "summary.md", metrics)
    print(json.dumps({"ok": metrics["ok"], "out": str(out_dir)}, indent=2, sort_keys=True))
    return 0 if metrics["ok"] else 1


def audit_full_lens_observables(run_dir: Path, config_path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    focal_z_mm = float(summary["focal_length_mm"])
    rings = {ring.ring_id: ring for ring in load_ring_config(config_path)}
    history = _read_rows(run_dir / "optics_history.csv")
    phase = _read_rows(run_dir / "phase_space.csv")
    transmitted = _read_rows(run_dir / "transmitted_space.csv")

    history_by_key = {(row["event_id"], row["track_id"]): row for row in history}
    diffract_history = {key: row for key, row in history_by_key.items() if row["stage"] == "DIFFRACT"}
    transmit_history = {key: row for key, row in history_by_key.items() if row["stage"] == "TRANSMIT"}

    phase_delta = _max_intersection_delta_mm(phase, diffract_history, focal_z_mm)
    transmitted_delta = _max_intersection_delta_mm(transmitted, transmit_history, focal_z_mm)
    phase_points = [(float(row["x_mm"]), float(row["y_mm"])) for row in phase]
    spot_d90_cm = containment_diameter_mm(phase_points, 0.9) / 10.0

    counts = Counter(row["stage"] for row in history)
    summary_counts_match = (
        counts["DIFFRACT"] == int(summary["n_diffracted"])
        and counts["ABSORB"] == int(summary["n_absorbed"])
        and counts["TRANSMIT"] == int(summary["n_transmitted"])
        and len(history) == int(summary["n_primaries"])
    )
    phase_rows_match_history = len(phase) == counts["DIFFRACT"]
    transmitted_rows_match_history = len(transmitted) == counts["TRANSMIT"]

    per_ring_rows = _per_ring_effective_area_rows(history, rings)
    expected_effective_area = sum(float(row["expected_diffracted_area_cm2"]) for row in per_ring_rows)
    observed_effective_area = sum(float(row["observed_diffracted_area_cm2"]) for row in per_ring_rows)
    effective_area_delta = observed_effective_area - expected_effective_area

    thresholds = {
        "max_phase_intersection_delta_mm": 1.0e-5,
        "max_transmitted_intersection_delta_mm": 1.0e-8,
        "spot_d90_summary_delta_cm": 1.0e-5,
        "effective_area_abs_delta_cm2": 1.0e-2,
    }
    spot_delta = spot_d90_cm - float(summary["spot_d90_cm"])
    checks = {
        "summary_counts_match": summary_counts_match,
        "phase_rows_match_history": phase_rows_match_history,
        "transmitted_rows_match_history": transmitted_rows_match_history,
        "phase_intersection": phase_delta <= thresholds["max_phase_intersection_delta_mm"],
        "transmitted_intersection": transmitted_delta <= thresholds["max_transmitted_intersection_delta_mm"],
        "spot_d90_matches_summary": abs(spot_delta) <= thresholds["spot_d90_summary_delta_cm"],
        "effective_area_mc_closure": abs(effective_area_delta) <= thresholds["effective_area_abs_delta_cm2"],
    }
    metrics = {
        "ok": all(checks.values()),
        "checks": checks,
        "thresholds": thresholds,
        "geant4_run": str(run_dir),
        "ring_config": str(config_path),
        "focal_z_mm": focal_z_mm,
        "n_history_rows": len(history),
        "n_phase_rows": len(phase),
        "n_transmitted_rows": len(transmitted),
        "history_counts": dict(counts),
        "summary_counts": {
            "DIFFRACT": summary["n_diffracted"],
            "ABSORB": summary["n_absorbed"],
            "TRANSMIT": summary["n_transmitted"],
            "TOTAL": summary["n_primaries"],
        },
        "max_phase_intersection_delta_mm": phase_delta,
        "max_transmitted_intersection_delta_mm": transmitted_delta,
        "spot_d90_cm": spot_d90_cm,
        "summary_spot_d90_cm": summary["spot_d90_cm"],
        "spot_d90_summary_delta_cm": spot_delta,
        "geometric_area_cm2": sum(float(row["geometric_area_cm2"]) for row in per_ring_rows),
        "expected_diffracted_area_cm2": expected_effective_area,
        "observed_diffracted_area_cm2": observed_effective_area,
        "effective_area_delta_cm2": effective_area_delta,
        "note": (
            "Effective area is computed from ring geometric tile area and the "
            "recorded per-ring diffraction probabilities/fractions for the current "
            "five-ring opticsim run."
        ),
    }
    return metrics, per_ring_rows


def _per_ring_effective_area_rows(history: list[dict[str, str]], rings: dict[int, object]) -> list[dict[str, object]]:
    rows_by_ring: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in history:
        rows_by_ring[int(row["ring_id"])].append(row)
    out = []
    for ring_id in sorted(rows_by_ring):
        rows = rows_by_ring[ring_id]
        ring = rings[ring_id]
        counts = Counter(row["stage"] for row in rows)
        geometric_area = ring.n_tiles * ring.tile_size_mm * ring.tile_size_mm / 100.0
        mean_p_diff = sum(float(row["p_reflect"]) for row in rows) / len(rows)
        observed_fraction = counts["DIFFRACT"] / len(rows)
        out.append(
            {
                "ring_id": ring_id,
                "design_energy_keV": ring.design_energy_keV,
                "n_history": len(rows),
                "n_diffracted": counts["DIFFRACT"],
                "geometric_area_cm2": geometric_area,
                "mean_p_diff": mean_p_diff,
                "observed_diffraction_fraction": observed_fraction,
                "expected_diffracted_area_cm2": geometric_area * mean_p_diff,
                "observed_diffracted_area_cm2": geometric_area * observed_fraction,
                "diffracted_area_delta_cm2": geometric_area * (observed_fraction - mean_p_diff),
            }
        )
    return out


def _max_intersection_delta_mm(rows: list[dict[str, str]], history_by_key: dict[tuple[str, str], dict[str, str]], z_mm: float) -> float:
    max_delta = 0.0
    for row in rows:
        hist = history_by_key[(row["event_id"], row["track_id"])]
        hit = plane_hit_at_z(
            (float(hist["x_mm"]), float(hist["y_mm"]), float(hist["z_mm"])),
            (float(hist["ux_out"]), float(hist["uy_out"]), float(hist["uz_out"])),
            z_mm,
        )
        delta = math.hypot(hit[0] - float(row["x_mm"]), hit[1] - float(row["y_mm"]))
        max_delta = max(max_delta, delta)
    return max_delta


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _write_per_ring_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_summary(path: Path, metrics: dict[str, object]) -> None:
    lines = [
        "# Full-Lens Observables Audit",
        "",
        f"Geant4 run: `{metrics['geant4_run']}`",
        f"Status: `{metrics['ok']}`",
        "",
        "## Geometry",
        "",
        f"- phase-space intersection max delta: `{metrics['max_phase_intersection_delta_mm']:.6g} mm`",
        f"- transmitted-space intersection max delta: `{metrics['max_transmitted_intersection_delta_mm']:.6g} mm`",
        f"- spot d90: `{metrics['spot_d90_cm']:.6g} cm`",
        f"- spot d90 delta vs run summary: `{metrics['spot_d90_summary_delta_cm']:.6g} cm`",
        "",
        "## Effective Area",
        "",
        f"- geometric tile area: `{metrics['geometric_area_cm2']:.6g} cm2`",
        f"- expected diffracted area: `{metrics['expected_diffracted_area_cm2']:.6g} cm2`",
        f"- observed diffracted area: `{metrics['observed_diffracted_area_cm2']:.6g} cm2`",
        f"- observed minus expected: `{metrics['effective_area_delta_cm2']:.6g} cm2`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
