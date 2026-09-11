#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from laue511.external_curve import convert_diffpat_to_external_curve, import_external_curve


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--diffpat-dat", required=True)
    parser.add_argument("--diffpat-par", required=True)
    parser.add_argument("--out-dir", default=str(ROOT / "benchmarks/xop_crystal"))
    parser.add_argument("--energy-kev", type=float, default=511.0)
    parser.add_argument("--d-spacing-A", type=float, default=3.266590088)
    parser.add_argument("--thickness-mm", type=float, default=10.218801)
    parser.add_argument("--source-version", default=None)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        curve = Path(tmp) / "ge111_511keV_rocking_curve.csv"
        conversion = convert_diffpat_to_external_curve(
            args.diffpat_dat,
            curve,
            thickness_mm=args.thickness_mm,
            diffpat_par=args.diffpat_par,
            source_version=args.source_version,
        )
        summary = import_external_curve(
            curve,
            args.out_dir,
            energy_keV=args.energy_kev,
            d_spacing_A=args.d_spacing_A,
            thickness_mm=args.thickness_mm,
        )
    summary["conversion"] = conversion
    out_dir = Path(args.out_dir)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_readme(out_dir, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


def _write_readme(out_dir: Path, summary: dict[str, object]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    conversion = summary["conversion"]
    (out_dir / "README.md").write_text(
        "\n".join(
            [
                "# XOP/CRYSTAL Rocking Curve",
                "",
                "CRYSTAL `diff_pat` Ge(111) 511 keV mosaic Laue diffraction curve.",
                "",
                f"- ok: {summary['ok']}",
                f"- rows: {summary['n_rows']}",
                f"- source tools: {summary.get('source_tools', [])}",
                f"- source versions: {summary.get('source_versions', [])}",
                f"- peak reflectivity: {summary.get('peak_reflectivity', 'n/a')}",
                f"- absorption: {conversion['absorption']}",
                "",
                "`diff_pat` provides the diffracted rocking curve. The `absorption`",
                "column is computed from the CRYSTAL beta-derived absorption coefficient",
                "reported in `diff_pat.par`; `transmittivity` is the remaining flux",
                "complement after unpolarized diffraction and absorption.",
                "",
            ]
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
