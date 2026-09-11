#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from laue511.rings import load_ring_config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ring-config", default=str(ROOT / "data/laue/ge111_480_550keV_multiring_darwin_config.csv"))
    parser.add_argument("--xop-summary", default=str(ROOT / "benchmarks/xop_crystal/summary.json"))
    parser.add_argument("--xop-curve", default=str(ROOT / "benchmarks/xop_crystal/ge111_511keV_rocking_curve.csv"))
    parser.add_argument("--multiring-summary", default=str(ROOT / "benchmarks/xop_crystal/multiring/summary.json"))
    parser.add_argument("--out-dir", default=str(ROOT / "reports/bfull_rocking_curve_map_status"))
    parser.add_argument("--energy-match-kev", type=float, default=0.25)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rings = load_ring_config(args.ring_config)
    xop_summary_path = Path(args.xop_summary)
    xop_curve_path = Path(args.xop_curve)
    multiring_summary_path = Path(args.multiring_summary)
    xop_summary = json.loads(xop_summary_path.read_text(encoding="utf-8")) if xop_summary_path.exists() else {}
    multiring_summary = (
        json.loads(multiring_summary_path.read_text(encoding="utf-8")) if multiring_summary_path.exists() else {}
    )
    xop_ok = bool(xop_summary.get("ok")) and xop_curve_path.exists()
    xop_energy = float(xop_summary.get("energy_keV", 511.0)) if xop_summary else 511.0
    multiring_curves = _multiring_curves_by_ring(multiring_summary, multiring_summary_path)

    coverage_rows: list[dict[str, object]] = []
    map_rows: list[dict[str, object]] = []
    for ring in rings:
        curve_path = multiring_curves.get(ring.ring_id)
        source_note = "multiring XOP/CRYSTAL diff_pat curve matches this ring id"
        energy_delta: float | str = ""
        if curve_path is None:
            energy_delta = abs(float(ring.design_energy_keV) - xop_energy)
            if xop_ok and energy_delta <= args.energy_match_keV:
                curve_path = xop_curve_path
                source_note = "single-energy XOP/CRYSTAL diff_pat curve matches this ring energy"
        covered = curve_path is not None and curve_path.exists()
        curve_rel = _relpath(curve_path, out_dir) if covered else ""
        status = "covered" if covered else "missing_external_curve"
        note = (
            source_note
            if covered
            else "external XOP/CRYSTAL rocking curve for this ring energy is not present"
        )
        coverage_rows.append(
            {
                "ring_id": ring.ring_id,
                "design_energy_keV": ring.design_energy_keV,
                "status": status,
                "curve_csv": curve_rel,
                "energy_delta_keV": energy_delta if xop_ok else "",
                "note": note,
            }
        )
        if covered:
            map_rows.append(
                {
                    "ring_id": ring.ring_id,
                    "design_energy_keV": ring.design_energy_keV,
                    "curve_csv": curve_rel,
                    "source": "CRYSTAL-diff_pat",
                    "status": status,
                }
            )

    coverage_csv = out_dir / "rocking_curve_coverage.csv"
    map_csv = out_dir / "available_rocking_curve_map.csv"
    _write_csv(coverage_csv, coverage_rows)
    _write_csv(map_csv, map_rows, fieldnames=["ring_id", "design_energy_keV", "curve_csv", "source", "status"])

    covered_ring_ids = [int(row["ring_id"]) for row in map_rows]
    missing_ring_ids = [int(row["ring_id"]) for row in coverage_rows if row["status"] != "covered"]
    all_covered = not missing_ring_ids and bool(covered_ring_ids)
    summary = {
        "ok": all_covered,
        "status": "ready" if all_covered else "partial",
        "all_rings_covered": all_covered,
        "covered_ring_ids": covered_ring_ids,
        "missing_ring_ids": missing_ring_ids,
        "n_rings": len(rings),
        "xop_summary": str(xop_summary_path),
        "xop_curve": str(xop_curve_path),
        "multiring_summary": str(multiring_summary_path),
        "multiring_summary_ok": bool(multiring_summary.get("ok")),
        "xop_curve_ok": xop_ok,
        "xop_energy_keV": xop_energy,
        "energy_match_keV": args.energy_match_kev,
        "map_csv": str(map_csv),
        "coverage_csv": str(coverage_csv),
        "note": (
            "Only rings with an energy-matched external XOP/CRYSTAL rocking curve are written to available_rocking_curve_map.csv. "
            "Run B-FULL full-lens external-table validation with --require-rocking-curve-map only after all rings are covered."
        ),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(out_dir / "summary.md", summary, coverage_rows)
    print(json.dumps({"out_dir": str(out_dir), "status": summary["status"], "ok": summary["ok"]}, indent=2, sort_keys=True))
    return 0


def _multiring_curves_by_ring(summary: dict[str, object], summary_path: Path) -> dict[int, Path]:
    if not summary.get("ok"):
        return {}
    base = summary_path.parent
    curves: dict[int, Path] = {}
    for row in summary.get("curves", []):
        if not isinstance(row, dict):
            continue
        ring_id = int(row["ring_id"])
        path = Path(str(row["curve_csv"]))
        if not path.is_absolute():
            path = base / path
        curves[ring_id] = path
    return curves


def _relpath(path: Path, base: Path) -> str:
    return os.path.relpath(path.resolve(), start=base.resolve())


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    if fieldnames is None:
        fieldnames = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown(path: Path, summary: dict[str, object], rows: list[dict[str, object]]) -> None:
    lines = [
        "# B-FULL Rocking-Curve Map Status",
        "",
        f"- status: `{summary['status']}`",
        f"- all rings covered: `{summary['all_rings_covered']}`",
        f"- covered ring ids: `{summary['covered_ring_ids']}`",
        f"- missing ring ids: `{summary['missing_ring_ids']}`",
        f"- map CSV: `{summary['map_csv']}`",
        "",
        "| ring | energy keV | status | curve CSV |",
        "|---:|---:|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {ring_id} | {design_energy_keV:.6g} | {status} | {curve_csv} |".format(**row)
        )
    lines.extend(["", str(summary["note"]), ""])
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
