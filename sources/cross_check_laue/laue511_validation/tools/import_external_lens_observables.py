#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from laue511.external_lens import import_external_lens_observables


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--out-dir", default=str(ROOT / "benchmarks/reference_outputs/external_lens_observables"))
    parser.add_argument("--current-observables", default=str(ROOT / "reports/full_lens_observables/metrics.json"))
    parser.add_argument("--python-reference", default=str(ROOT / "reports/python_full_lens_reference/metrics.json"))
    args = parser.parse_args()

    summary = import_external_lens_observables(
        args.input,
        args.out_dir,
        current_observables_path=args.current_observables,
        python_reference_path=args.python_reference,
    )
    _write_readme(Path(args.out_dir), summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


def _write_readme(out_dir: Path, summary: dict[str, object]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# External Lens Observables",
        "",
        "Imported full-lens observables from an external Laue-lens oracle.",
        "",
        f"- ok: {summary['ok']}",
        f"- rows: {summary['n_rows']}",
        f"- source tools: {summary.get('source_tools', [])}",
        f"- source versions: {summary.get('source_versions', [])}",
        "",
    ]
    if summary.get("ok"):
        lens = summary["lens_metrics"]
        comp = summary["comparison"]
        lines.extend(
            [
                f"- diffracted area: {lens['diffracted_area_cm2']:.6g} cm2",
                f"- spot d90: {lens['spot_d90_cm']:.6g} cm",
                f"- area minus current observed: {comp['diffracted_area_minus_current_observed_cm2']:.6g} cm2",
                f"- area minus Python reference: {comp['diffracted_area_minus_python_reference_cm2']:.6g} cm2",
                "",
            ]
        )
    out_dir.joinpath("README.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
