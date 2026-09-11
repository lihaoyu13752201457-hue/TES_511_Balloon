#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from laue511.metrics import binomial_z
from laue511.probabilities import darwin_hamilton_mosaic_probabilities
from laue511.rings import load_ring_config


DEFAULT_RUN = Path("/home/ubuntu/opticsim/runs/geant4_laue_darwin_guan_process")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--geant4-run", default=str(DEFAULT_RUN))
    parser.add_argument("--config", default=str(ROOT / "data/laue/ge111_480_550keV_multiring_darwin_config.csv"))
    parser.add_argument("--out-dir", default=str(ROOT / "reports/python_full_lens_reference"))
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics, per_ring = build_reference(Path(args.config), Path(args.geant4_run))
    _write_csv(out_dir / "per_ring_reference.csv", per_ring)
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_summary(out_dir / "summary.md", metrics)
    print(json.dumps({"ok": metrics["ok"], "out": str(out_dir)}, indent=2, sort_keys=True))
    return 0 if metrics["ok"] else 1


def build_reference(config_path: Path, run_dir: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    rings = load_ring_config(config_path)
    counts_by_ring = _history_counts_by_ring(run_dir / "optics_history.csv")
    per_ring = []
    for ring in rings:
        probs = darwin_hamilton_mosaic_probabilities(
            E_keV=ring.design_energy_keV,
            d_spacing_A=ring.d_spacing_A,
            thickness_mm=ring.thickness_mm,
        )
        counts = counts_by_ring[ring.ring_id]
        n = sum(counts.values())
        area_cm2 = ring.n_tiles * ring.tile_size_mm * ring.tile_size_mm / 100.0
        row = {
            "ring_id": ring.ring_id,
            "design_energy_keV": ring.design_energy_keV,
            "geometric_area_cm2": area_cm2,
            "p_diff_reference": probs.p_diff,
            "p_abs_reference": probs.p_abs,
            "p_trans_reference": probs.p_trans,
            "diffracted_area_reference_cm2": area_cm2 * probs.p_diff,
            "absorbed_area_reference_cm2": area_cm2 * probs.p_abs,
            "transmitted_area_reference_cm2": area_cm2 * probs.p_trans,
            "n_history": n,
            "n_diffracted": counts["DIFFRACT"],
            "n_absorbed": counts["ABSORB"],
            "n_transmitted": counts["TRANSMIT"],
            "observed_diffraction_fraction": counts["DIFFRACT"] / n,
            "observed_absorption_fraction": counts["ABSORB"] / n,
            "observed_transmission_fraction": counts["TRANSMIT"] / n,
            "observed_diffracted_area_cm2": area_cm2 * counts["DIFFRACT"] / n,
            "diffraction_z": binomial_z(counts["DIFFRACT"], n, probs.p_diff),
            "absorption_z": binomial_z(counts["ABSORB"], n, probs.p_abs),
            "transmission_z": binomial_z(counts["TRANSMIT"], n, probs.p_trans),
        }
        row["diffracted_area_delta_cm2"] = row["observed_diffracted_area_cm2"] - row["diffracted_area_reference_cm2"]
        per_ring.append(row)

    totals = _totals(per_ring)
    thresholds = {
        "max_abs_branch_z": 3.0,
        "diffracted_area_abs_delta_cm2": 1.0e-2,
    }
    checks = {
        "branch_statistics": totals["max_abs_branch_z"] <= thresholds["max_abs_branch_z"],
        "diffracted_area": abs(totals["diffracted_area_delta_cm2"]) <= thresholds["diffracted_area_abs_delta_cm2"],
    }
    metrics = {
        "ok": all(checks.values()),
        "checks": checks,
        "thresholds": thresholds,
        "geant4_run": str(run_dir),
        "ring_config": str(config_path),
        **totals,
        "note": (
            "This reference is computed from the ring CSV and the Python "
            "Darwin-Hamilton kernel at exact Bragg incidence; it does not read "
            "the Geant4 recorded probabilities."
        ),
    }
    return metrics, per_ring


def _history_counts_by_ring(path: Path) -> dict[int, Counter[str]]:
    counts: dict[int, Counter[str]] = defaultdict(Counter)
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            counts[int(row["ring_id"])][row["stage"]] += 1
    return counts


def _totals(rows: list[dict[str, object]]) -> dict[str, float]:
    branch_z_values = []
    for row in rows:
        branch_z_values.extend([float(row["diffraction_z"]), float(row["absorption_z"]), float(row["transmission_z"])])
    reference_area = sum(float(row["diffracted_area_reference_cm2"]) for row in rows)
    observed_area = sum(float(row["observed_diffracted_area_cm2"]) for row in rows)
    return {
        "geometric_area_cm2": sum(float(row["geometric_area_cm2"]) for row in rows),
        "diffracted_area_reference_cm2": reference_area,
        "observed_diffracted_area_cm2": observed_area,
        "diffracted_area_delta_cm2": observed_area - reference_area,
        "max_abs_branch_z": max(abs(value) for value in branch_z_values),
    }


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_summary(path: Path, metrics: dict[str, object]) -> None:
    lines = [
        "# Python Full-Lens Reference",
        "",
        f"Status: `{metrics['ok']}`",
        "",
        "This reference uses only the ring CSV and the Python Darwin-Hamilton kernel",
        "at exact Bragg incidence, then compares with the sampled branches in the",
        "current Geant4 five-ring run.",
        "",
        f"- geometric tile area: `{metrics['geometric_area_cm2']:.6g} cm2`",
        f"- reference diffracted area: `{metrics['diffracted_area_reference_cm2']:.6g} cm2`",
        f"- observed diffracted area: `{metrics['observed_diffracted_area_cm2']:.6g} cm2`",
        f"- observed minus reference: `{metrics['diffracted_area_delta_cm2']:.6g} cm2`",
        f"- max branch z-score: `{metrics['max_abs_branch_z']:.6g}`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
