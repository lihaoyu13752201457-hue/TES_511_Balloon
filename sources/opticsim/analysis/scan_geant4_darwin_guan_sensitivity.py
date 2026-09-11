from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


CASES = [
    {"case": "nominal", "mosaic_fwhm_arcsec": 30.0, "crystallite_um": 5.0},
    {"case": "mosaic_narrow", "mosaic_fwhm_arcsec": 15.0, "crystallite_um": 5.0},
    {"case": "mosaic_wide", "mosaic_fwhm_arcsec": 60.0, "crystallite_um": 5.0},
    {"case": "crystallite_thin", "mosaic_fwhm_arcsec": 30.0, "crystallite_um": 2.5},
    {"case": "crystallite_thick", "mosaic_fwhm_arcsec": 30.0, "crystallite_um": 20.0},
]


def geant4_env(demo: Path) -> dict[str, str]:
    env = dict(os.environ)
    if "opticsim-build-g4-11.4.0" in str(demo):
        for key in list(env):
            if key.startswith("G4") or key == "GEANT4_DATA_DIR":
                env.pop(key, None)
        env["LD_LIBRARY_PATH"] = "/home/ubuntu/software/geant4-11.4.0-install/lib:" + env.get("LD_LIBRARY_PATH", "")
        env["PATH"] = "/home/ubuntu/software/geant4-11.4.0-install/bin:" + env.get("PATH", "")
        env["GEANT4_DATA_DIR"] = "/home/ubuntu/software/geant4-11.4.0-install/share/Geant4/data"
    return env


def resolve_demo(path: str | None) -> Path:
    if path:
        demo = Path(path)
        return demo if demo.is_absolute() else ROOT / demo
    preferred = Path("/tmp/opticsim-build-g4-11.4.0/laue_multiring_darwin_guan_demo")
    if preferred.exists():
        return preferred
    return Path("/tmp/opticsim-build/laue_multiring_darwin_guan_demo")


def load_summary(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def display_path(path: Path) -> str:
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def run_case(demo: Path, out_root: Path, case: dict[str, float | str], n_events: int, seed: int) -> dict[str, Any]:
    case_dir = out_root / str(case["case"])
    cmd = [
        str(demo),
        "--n",
        str(n_events),
        "--seed",
        str(seed),
        "--ring-config",
        "data/laue/ge111_480_550keV_multiring_darwin_config.csv",
        "--efficiency-table",
        "data/laue/Ge111_480_550keV_darwin_mosaic_table.csv",
        "--mosaic-fwhm-arcsec",
        str(case["mosaic_fwhm_arcsec"]),
        "--crystallite-um",
        str(case["crystallite_um"]),
        "--out",
        str(case_dir),
    ]
    subprocess.run(
        cmd,
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=geant4_env(demo),
    )
    summary = load_summary(case_dir / "summary.json")
    return {
        "case": case["case"],
        "mosaic_fwhm_arcsec": case["mosaic_fwhm_arcsec"],
        "crystallite_um": case["crystallite_um"],
        "n_primaries": summary["n_primaries"],
        "diffraction_fraction": summary["diffraction_fraction"],
        "absorption_fraction": summary["absorption_fraction"],
        "transmission_fraction": summary["transmission_fraction"],
        "spot_d90_cm": summary["spot_d90_cm"],
        "uses_external_efficiency_table_for_physics": summary["uses_external_efficiency_table_for_physics"],
        "online_physics_backend": summary["online_physics_backend"],
        "summary_path": display_path(case_dir / "summary.json"),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, summary: dict[str, Any]) -> None:
    rows = summary["rows"]
    nominal = summary["nominal"]
    lines = [
        "# Geant4 Darwin/Guan Sensitivity Check",
        "",
        "This is a small sanity check for the compiled 02 implementation. It does not claim to reproduce the full Guan/Reiazi benchmark matrix; it checks whether the local online Darwin-Hamilton backend responds to physical crystal parameters.",
        "",
        "## Result Table",
        "",
        "| case | mosaic FWHM arcsec | crystallite um | diffraction | absorption | transmission | spot D90 cm | delta diffraction vs nominal |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['case']} | {row['mosaic_fwhm_arcsec']:.1f} | {row['crystallite_um']:.1f} | "
            f"{row['diffraction_fraction']:.5f} | {row['absorption_fraction']:.5f} | "
            f"{row['transmission_fraction']:.5f} | {row['spot_d90_cm']:.5f} | "
            f"{row['delta_diffraction_vs_nominal']:+.5f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            f"- Nominal case: mosaic `{nominal['mosaic_fwhm_arcsec']}` arcsec, crystallite `{nominal['crystallite_um']}` um, diffraction `{nominal['diffraction_fraction']:.5f}`.",
            f"- Narrower mosaic case changes diffraction by `{summary['mosaic_narrow_delta']:+.5f}` relative to nominal.",
            f"- Wider mosaic case changes diffraction by `{summary['mosaic_wide_delta']:+.5f}` relative to nominal.",
            f"- Crystallite-thickness endpoints change diffraction by `{summary['crystallite_span']:.5f}` across the scanned range.",
            "- All cases report `uses_external_efficiency_table_for_physics=false`, so this is a runtime check of the online 02 backend rather than the 01 probability CSV.",
            "",
            "## Boundary",
            "",
            "This is a local fixed-lens sensitivity check. A paper-level Reiazi reproduction would still require XOP benchmarks over perfect/mosaic crystals, materials, energies, mosaicity, absorption, and crystallite direction/thickness.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a small Geant4 Darwin/Guan physical-parameter sensitivity check.")
    parser.add_argument("--demo", default=None)
    parser.add_argument("--out", default="runs/geant4_laue_darwin_guan_sensitivity")
    parser.add_argument("--n", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=20260522)
    args = parser.parse_args()

    demo = resolve_demo(args.demo)
    if not demo.exists():
        raise SystemExit(f"missing executable: {demo}")
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    for index, case in enumerate(CASES):
        row = run_case(demo, out, case, args.n, args.seed + index)
        rows.append(row)

    nominal = next(row for row in rows if row["case"] == "nominal")
    for row in rows:
        row["delta_diffraction_vs_nominal"] = row["diffraction_fraction"] - nominal["diffraction_fraction"]
        row["delta_spot_d90_cm_vs_nominal"] = row["spot_d90_cm"] - nominal["spot_d90_cm"]

    by_case = {row["case"]: row for row in rows}
    crystallite_values = [
        by_case["crystallite_thin"]["diffraction_fraction"],
        nominal["diffraction_fraction"],
        by_case["crystallite_thick"]["diffraction_fraction"],
    ]
    summary = {
        "ok": True,
        "system": "geant4_laue_darwin_guan_sensitivity",
        "n_cases": len(rows),
        "n_primaries_per_case": args.n,
        "nominal": nominal,
        "rows": rows,
        "mosaic_narrow_delta": by_case["mosaic_narrow"]["delta_diffraction_vs_nominal"],
        "mosaic_wide_delta": by_case["mosaic_wide"]["delta_diffraction_vs_nominal"],
        "crystallite_span": max(crystallite_values) - min(crystallite_values),
        "all_cases_online_backend": all(row["uses_external_efficiency_table_for_physics"] is False for row in rows),
        "interpretation": (
            "The compiled 02 backend responds to mosaic/crystallite inputs without reading the 01 probability table. "
            "This is a small fixed-lens sanity check, not a full Guan/Reiazi XOP benchmark reproduction."
        ),
    }
    write_csv(out / "sensitivity.csv", rows)
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_report(out / "GEANT4_DARWIN_GUAN_SENSITIVITY_CHECK.md", summary)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
