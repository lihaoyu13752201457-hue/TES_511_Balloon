#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from laue511.external_lens import import_external_lens_hits


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--out-dir", default=str(ROOT / "benchmarks/reference_outputs/external_lens_observables"))
    parser.add_argument("--current-observables", default=str(ROOT / "reports/full_lens_observables/metrics.json"))
    parser.add_argument("--python-reference", default=str(ROOT / "reports/python_full_lens_reference/metrics.json"))
    parser.add_argument("--geometric-area-cm2", type=float)
    parser.add_argument("--incident-weight", type=float, required=True)
    parser.add_argument("--position-unit", choices=("cm", "mm"), default="cm")
    parser.add_argument("--x-column", default="x_cm")
    parser.add_argument("--y-column", default="y_cm")
    parser.add_argument("--weight-column", default="weight")
    parser.add_argument("--source-tool", default="external-hit-table")
    parser.add_argument("--source-version", default="unspecified")
    args = parser.parse_args()

    geometric_area = args.geometric_area_cm2
    if geometric_area is None:
        current = json.loads(Path(args.current_observables).read_text(encoding="utf-8"))
        geometric_area = float(current["geometric_area_cm2"])

    summary = import_external_lens_hits(
        args.input,
        args.out_dir,
        current_observables_path=args.current_observables,
        python_reference_path=args.python_reference,
        geometric_area_cm2=geometric_area,
        incident_weight=args.incident_weight,
        position_unit=args.position_unit,
        x_column=args.x_column,
        y_column=args.y_column,
        weight_column=args.weight_column,
        source_tool=args.source_tool,
        source_version=args.source_version,
    )
    _write_readme(Path(args.out_dir), summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


def _write_readme(out_dir: Path, summary: dict[str, object]) -> None:
    lines = [
        "# External Lens Observables",
        "",
        "Imported from an external detector-plane hit table.",
        "",
        f"- ok: {summary['ok']}",
    ]
    hit_summary = summary.get("hit_summary", {})
    if isinstance(hit_summary, dict):
        lines.extend(
            [
                f"- hit rows: {hit_summary.get('n_hits')}",
                f"- incident weight: {hit_summary.get('incident_weight')}",
                f"- diffracted weight: {hit_summary.get('diffracted_weight')}",
            ]
        )
    if summary.get("ok"):
        lens = summary["lens_metrics"]
        comp = summary["comparison"]
        lines.extend(
            [
                f"- diffracted area: {lens['diffracted_area_cm2']:.6g} cm2",
                f"- spot d90: {lens['spot_d90_cm']:.6g} cm",
                f"- area minus current observed: {comp['diffracted_area_minus_current_observed_cm2']:.6g} cm2",
                f"- area minus Python reference: {comp['diffracted_area_minus_python_reference_cm2']:.6g} cm2",
            ]
        )
    out_dir.joinpath("README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
