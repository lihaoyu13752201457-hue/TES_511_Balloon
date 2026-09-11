#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from laue511.external_curve import import_external_curve


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--out-dir", default=str(ROOT / "benchmarks/xop_crystal"))
    parser.add_argument("--energy-kev", type=float, default=511.0)
    parser.add_argument("--d-spacing-A", type=float, default=3.266590088)
    parser.add_argument("--thickness-mm", type=float, default=10.218801)
    args = parser.parse_args()

    summary = import_external_curve(
        args.input,
        args.out_dir,
        energy_keV=args.energy_kev,
        d_spacing_A=args.d_spacing_A,
        thickness_mm=args.thickness_mm,
    )
    _write_readme(Path(args.out_dir), summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


def _write_readme(out_dir: Path, summary: dict[str, object]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "README.md").write_text(
        "\n".join(
            [
                "# XOP/CRYSTAL Rocking Curve",
                "",
                "External rocking-curve import for Ge(111) near 511 keV.",
                "",
                f"- ok: {summary['ok']}",
                f"- rows: {summary['n_rows']}",
                f"- source tools: {summary.get('source_tools', [])}",
                f"- peak reflectivity: {summary.get('peak_reflectivity', 'n/a')}",
                "",
            ]
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
