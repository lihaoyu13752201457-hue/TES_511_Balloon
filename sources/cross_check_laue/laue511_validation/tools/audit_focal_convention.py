#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from laue511.constants import DEFAULT_FOCAL_LENGTH_MM
from laue511.focal import audit_focal_convention
from laue511.rings import load_ring_config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(ROOT / "data/laue/ge111_480_550keV_multiring_darwin_config.csv"))
    parser.add_argument("--focal-mm", type=float, default=DEFAULT_FOCAL_LENGTH_MM)
    parser.add_argument("--out-dir", default=str(ROOT / "reports/focal_convention_audit"))
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics = audit_focal_convention(load_ring_config(args.config), args.focal_mm)
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_csv(out_dir / "focal_convention.csv", metrics["rows"])
    _write_summary(out_dir / "summary.md", metrics)
    print(json.dumps({key: metrics[key] for key in _SUMMARY_KEYS}, indent=2, sort_keys=True))
    return 0


_SUMMARY_KEYS = [
    "focal_mm_evaluated",
    "center_plane_focal_mm_mean",
    "entry_face_bragg_focal_mm_min",
    "entry_face_bragg_focal_mm_max",
    "max_abs_center_plane_radius_delta_mm",
    "max_abs_delta_theta_entry_arcsec",
    "max_abs_p_diff_delta",
    "max_abs_p_diff_rel_delta",
]


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_summary(path: Path, metrics: dict[str, object]) -> None:
    lines = [
        "# Focal Convention Audit",
        "",
        f"Evaluated Geant4 focal plane: `{metrics['focal_mm_evaluated']:.6f} mm`",
        "",
        "## Summary",
        "",
        f"- ring CSV center-plane focal mean: `{metrics['center_plane_focal_mm_mean']:.6f} mm`",
        f"- entry-face Bragg focal range: `{metrics['entry_face_bragg_focal_mm_min']:.6f}` to `{metrics['entry_face_bragg_focal_mm_max']:.6f} mm`",
        f"- max center-plane radius delta at evaluated focal: `{metrics['max_abs_center_plane_radius_delta_mm']:.6g} mm`",
        f"- max entry-face delta theta: `{metrics['max_abs_delta_theta_entry_arcsec']:.6g} arcsec`",
        f"- max absolute p_diff shift from exact-Bragg probability: `{metrics['max_abs_p_diff_delta']:.6g}`",
        f"- max relative p_diff shift: `{metrics['max_abs_p_diff_rel_delta']:.6g}`",
        "",
        "## Interpretation",
        "",
        "The ring CSV is internally consistent as a center-plane Bragg-radius table.",
        "The current Geant4 process evaluates interactions at the upstream crystal face and focuses to the configured focal plane.",
        "At `8300 mm`, this creates a small ring-dependent angular offset that is already included in the recorded Geant4 probabilities.",
        "",
        "Recommendation for the current cross-check: keep `8300 mm` as the operational Geant4 convention for existing runs, and record the CSV center-plane convention explicitly.",
        "",
        "## Per Ring",
        "",
        "| ring | E_keV | center focal mm | entry Bragg focal mm | entry delta arcsec | p_diff shift |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in metrics["rows"]:
        lines.append(
            f"| {row['ring_id']} | {row['energy_keV']:.1f} | "
            f"{row['center_plane_focal_mm_from_config']:.6f} | "
            f"{row['entry_face_bragg_focal_mm']:.6f} | "
            f"{row['delta_theta_entry_arcsec']:.6g} | "
            f"{row['p_diff_abs_delta']:.6g} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
