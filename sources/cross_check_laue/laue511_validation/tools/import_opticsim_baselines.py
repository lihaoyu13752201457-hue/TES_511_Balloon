#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--opticsim-root", default="/home/ubuntu/opticsim")
    args = parser.parse_args()

    opticsim = Path(args.opticsim_root)
    pytte_src = opticsim / "runs/laue_pytte_ge111_check"
    kohnle_src = opticsim / "runs/laue_kohnle1998_ge111_benchmark"
    table_lens_src = opticsim / "runs/geant4_laue_darwin_guan_process"

    pytte = _copy_baseline(
        pytte_src,
        ROOT / "benchmarks/xrt_pytte",
        ["pytte_ge111_check.csv", "summary.json"],
    )
    kohnle = _copy_baseline(
        kohnle_src,
        ROOT / "benchmarks/kohnle1998",
        ["benchmark.csv", "summary.json"],
    )
    table_lens = _copy_table_lens_closure(table_lens_src, ROOT / "benchmarks/opticsim_table_lens")
    _write_readmes(pytte, kohnle, table_lens)
    ok = bool(pytte["ok"]) and bool(kohnle["ok"]) and bool(table_lens["ok"])
    print(
        json.dumps(
            {
                "pytte_ok": pytte["ok"],
                "kohnle_ok": kohnle["ok"],
                "opticsim_table_lens_ok": table_lens["ok"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if ok else 1


def _copy_baseline(src: Path, dst: Path, files: list[str]) -> dict[str, object]:
    dst.mkdir(parents=True, exist_ok=True)
    for name in files:
        shutil.copyfile(src / name, dst / name)
    return json.loads((dst / "summary.json").read_text(encoding="utf-8"))


def _copy_table_lens_closure(src: Path, dst: Path) -> dict[str, object]:
    dst.mkdir(parents=True, exist_ok=True)
    raw = json.loads((src / "barhoum_comparison_summary.json").read_text(encoding="utf-8"))
    thresholds = {
        "max_abs_delta_mean_p_diff_by_ring": 1.0e-3,
        "max_abs_delta_sampled_diffraction_fraction_by_ring": 5.0e-3,
        "delta_diffraction_fraction": 2.0e-3,
        "delta_absorption_fraction": 2.0e-3,
        "delta_transmission_fraction": 2.0e-3,
        "delta_spot_d90_cm": 1.0e-2,
    }
    checks = {
        key: abs(float(raw[key])) <= limit
        for key, limit in thresholds.items()
    }
    summary = {
        **raw,
        "ok": all(checks.values()),
        "checks": checks,
        "thresholds": thresholds,
        "source_run": str(src),
        "evidence_type": "opticsim_table_driven_full_lens_closure",
        "note": (
            "Full five-ring opticsim closure between the table-driven "
            "Barhoum-style baseline and the Guan/Reiazi-style online "
            "Darwin-Hamilton process. This is not an external LLL/HEART oracle."
        ),
    }
    shutil.copyfile(src / "barhoum_comparison_per_ring.csv", dst / "per_ring_comparison.csv")
    (dst / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def _write_readmes(pytte: dict[str, object], kohnle: dict[str, object], table_lens: dict[str, object]) -> None:
    (ROOT / "benchmarks/xrt_pytte/README.md").write_text(
        "\n".join(
            [
                "# PyTTE Ge(111) Check",
                "",
                "Imported from `/home/ubuntu/opticsim/runs/laue_pytte_ge111_check`.",
                "",
                f"- ok: {pytte['ok']}",
                f"- cases: {pytte['n_cases']}",
                f"- max warning count: {pytte['max_warning_count']}",
                "",
                str(pytte["interpretation"]),
                "",
            ]
        ),
        encoding="utf-8",
    )
    (ROOT / "benchmarks/kohnle1998/README.md").write_text(
        "\n".join(
            [
                "# Kohnle 1998 Ge(111) Endpoint Benchmark",
                "",
                "Imported from `/home/ubuntu/opticsim/runs/laue_kohnle1998_ge111_benchmark`.",
                "",
                f"- ok: {kohnle['ok']}",
                f"- cases: {kohnle['n_cases']}",
                f"- endpoint max absolute error: {kohnle['endpoint_max_abs_error']:.6g}",
                f"- source: {kohnle['benchmark_source']}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (ROOT / "benchmarks/opticsim_table_lens/README.md").write_text(
        "\n".join(
            [
                "# Opticsim Table-Lens Closure",
                "",
                "Imported from `/home/ubuntu/opticsim/runs/geant4_laue_darwin_guan_process`.",
                "",
                "This is a full five-ring opticsim closure check. It compares the",
                "table-driven Barhoum-style baseline with the Guan/Reiazi-style online",
                "Darwin-Hamilton process using the same Ge(111) lens geometry.",
                "",
                f"- ok: {table_lens['ok']}",
                f"- Guan diffraction fraction: {table_lens['guan_diffraction_fraction']:.6g}",
                f"- table-driven diffraction fraction: {table_lens['barhoum_diffraction_fraction']:.6g}",
                f"- delta diffraction fraction: {table_lens['delta_diffraction_fraction']:.6g}",
                f"- max per-ring mean p_diff delta: {table_lens['max_abs_delta_mean_p_diff_by_ring']:.6g}",
                f"- max per-ring sampled diffraction-fraction delta: {table_lens['max_abs_delta_sampled_diffraction_fraction_by_ring']:.6g}",
                f"- spot d90 delta: {table_lens['delta_spot_d90_cm']:.6g} cm",
                "",
                "It is useful full-lens evidence, but it is still internal to the opticsim",
                "model family and does not replace a direct LLL/HEART-style external oracle.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (ROOT / "benchmarks/README.md").write_text(
        "\n".join(
            [
                "# Benchmarks",
                "",
                "Imported evidence currently available in this workspace:",
                "",
                "- `xrt_pytte/`: PyTTE 1.0 Takagi-Taupin perfect-crystal Ge(111) Laue check.",
                "- `kohnle1998/`: Ge(111) 3-mm mosaic-crystal endpoint benchmark from Kohnle 1998.",
                "- `crystalpy/`: CrystalPy perfect-crystal Laue rocking curve.",
                "- `xop_crystal/`: XOP/CRYSTAL mosaic Laue rocking curve.",
                "- `opticsim_table_lens/`: full five-ring table-driven vs online-process closure.",
                "- `reference_outputs/`: external Laue Lens Library status.",
                "",
                "PyTTE is not used as a direct mosaic-crystal replacement. It verifies a different",
                "limit: perfect-crystal Laue diffraction has a higher peak diffracted branch and",
                "near-conserved forward+diffracted flux.",
                "",
                "`opticsim_table_lens/` is a full-lens closure check, but it remains inside",
                "the opticsim model family and does not replace an external LLL/HEART oracle.",
                "",
            ]
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
