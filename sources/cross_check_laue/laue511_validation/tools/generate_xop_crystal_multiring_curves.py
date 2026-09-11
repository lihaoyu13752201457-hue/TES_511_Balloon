#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from laue511.external_curve import convert_diffpat_to_external_curve, summarize_external_curve
from laue511.rings import RingSpec, load_ring_config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=str(ROOT / "benchmarks/xop_crystal/multiring"))
    parser.add_argument("--ring-config", default=str(ROOT / "data/laue/ge111_480_550keV_multiring_darwin_config.csv"))
    parser.add_argument("--xoppylib-path", default=os.environ.get("LAUE511_XOPPYLIB_PATH", "/tmp/laue511_xop_tools"))
    parser.add_argument("--xdg-data-home", default=os.environ.get("XDG_DATA_HOME", "/home/ubuntu/opticsim/.tools/xdg_data"))
    parser.add_argument("--scan-min-arcsec", type=float, default=-300.0)
    parser.add_argument("--scan-max-arcsec", type=float, default=300.0)
    parser.add_argument("--scan-points", type=int, default=101)
    parser.add_argument("--mosaic-fwhm-arcsec", type=float, default=30.0)
    parser.add_argument("--energy-window-ev", type=float, default=100.0)
    args = parser.parse_args()

    _prepare_optional_xoppylib_path(Path(args.xoppylib_path))
    os.environ.setdefault("MPLCONFIGDIR", "/tmp")
    os.environ.setdefault("XDG_DATA_HOME", args.xdg_data_home)

    try:
        from dabax.dabax_xraylib import DabaxXraylib
        from xoppylib.crystals.tools import bragg_calc2
        from xoppylib.xoppy_util import locations
    except Exception as exc:  # pragma: no cover - depends on optional local XOP install
        raise RuntimeError(
            "xoppylib/dabax are required. Install them into /tmp/laue511_xop_tools "
            "or pass --xoppylib-path to an equivalent isolated install."
        ) from exc

    out_dir = Path(args.out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    rings = load_ring_config(args.ring_config)
    xoppylib_version = _package_version("xoppylib")
    dabax_version = _package_version("dabax")
    source_version = (
        f"CRYSTAL diff_pat v1.8; xoppylib {xoppylib_version}; "
        f"DABAX {dabax_version}; DABAX data {Path(args.xdg_data_home) / 'Dabax'}"
    )

    curves: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="laue511_xop_diffpat_") as tmp:
        tmp_root = Path(tmp)
        for ring in rings:
            curve = _generate_one_ring(
                ring,
                out_dir,
                tmp_root,
                bragg_calc2=bragg_calc2,
                dabax_xraylib=DabaxXraylib,
                diff_pat_bin=Path(locations.home_bin()) / "diff_pat",
                source_version=source_version,
                scan_min_arcsec=args.scan_min_arcsec,
                scan_max_arcsec=args.scan_max_arcsec,
                scan_points=args.scan_points,
                mosaic_fwhm_arcsec=args.mosaic_fwhm_arcsec,
                energy_window_ev=args.energy_window_ev,
            )
            curves.append(curve)

    map_csv = out_dir / "all_ring_rocking_curve_map.csv"
    _write_map_csv(map_csv, curves, out_dir)
    summary = {
        "ok": len(curves) == len(rings) and all(bool(curve["ok"]) for curve in curves),
        "n_rings": len(rings),
        "ring_ids": [ring.ring_id for ring in rings],
        "curves": curves,
        "map_csv": str(map_csv),
        "source_version": source_version,
        "xoppylib_version": xoppylib_version,
        "dabax_version": dabax_version,
        "scan_min_arcsec": args.scan_min_arcsec,
        "scan_max_arcsec": args.scan_max_arcsec,
        "scan_points": args.scan_points,
        "mosaic_fwhm_arcsec": args.mosaic_fwhm_arcsec,
        "note": (
            "Generated with CRYSTAL diff_pat through xoppylib for each configured ring energy. "
            "These are mosaic Laue diffraction curves intended for the B-FULL per-ring finite-MFP backend."
        ),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(out_dir / "summary.md", summary)
    print(json.dumps({"out_dir": str(out_dir), "ok": summary["ok"], "n_rings": len(curves)}, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


def _prepare_optional_xoppylib_path(path: Path) -> None:
    if path.exists():
        sys.path.insert(0, str(path))


def _package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _generate_one_ring(
    ring: RingSpec,
    out_dir: Path,
    tmp_root: Path,
    *,
    bragg_calc2: object,
    dabax_xraylib: object,
    diff_pat_bin: Path,
    source_version: str,
    scan_min_arcsec: float,
    scan_max_arcsec: float,
    scan_points: int,
    mosaic_fwhm_arcsec: float,
    energy_window_ev: float,
) -> dict[str, object]:
    work_dir = tmp_root / f"ring_{ring.ring_id}"
    work_dir.mkdir()
    cwd = Path.cwd()
    os.chdir(work_dir)
    try:
        energy_ev = float(ring.design_energy_keV) * 1000.0
        bragg_file = work_dir / f"bragg_ge111_{ring.design_energy_keV:.0f}keV.dat"
        bragg_calc2(
            descriptor="Ge",
            hh=1,
            kk=1,
            ll=1,
            temper=1.0,
            emin=energy_ev - energy_window_ev,
            emax=energy_ev + energy_window_ev,
            estep=10.0,
            fileout=str(bragg_file),
            material_constants_library=dabax_xraylib(),
        )
        _run_diff_pat(
            diff_pat_bin,
            bragg_file.name,
            energy_ev=energy_ev,
            thickness_cm=float(ring.thickness_mm) / 10.0,
            mosaic_fwhm_deg=mosaic_fwhm_arcsec / 3600.0,
            scan_min_arcsec=scan_min_arcsec,
            scan_max_arcsec=scan_max_arcsec,
            scan_points=scan_points,
        )
        output_name = f"ge111_{ring.design_energy_keV:.0f}keV_rocking_curve.csv"
        curve_path = out_dir / output_name
        conversion = convert_diffpat_to_external_curve(
            work_dir / "diff_pat.dat",
            curve_path,
            thickness_mm=float(ring.thickness_mm),
            diffpat_par=work_dir / "diff_pat.par",
            source_version=source_version,
        )
        summary = summarize_external_curve(
            curve_path,
            energy_keV=float(ring.design_energy_keV),
            d_spacing_A=float(ring.d_spacing_A),
            thickness_mm=float(ring.thickness_mm),
        )
        summary.update(
            {
                "ring_id": ring.ring_id,
                "design_energy_keV": ring.design_energy_keV,
                "thickness_mm": ring.thickness_mm,
                "curve_csv": str(curve_path),
                "conversion": conversion,
            }
        )
        return summary
    finally:
        os.chdir(cwd)


def _run_diff_pat(
    diff_pat_bin: Path,
    bragg_file: str,
    *,
    energy_ev: float,
    thickness_cm: float,
    mosaic_fwhm_deg: float,
    scan_min_arcsec: float,
    scan_max_arcsec: float,
    scan_points: int,
) -> None:
    xoppy_inp = "\n".join(
        [
            bragg_file,
            "1",  # mosaic crystal
            "1",  # diffracted beam in transmission (Laue) geometry
            f"{mosaic_fwhm_deg:.12g}",
            f"{thickness_cm:.12g}",
            "3",  # incident angle minus theta Bragg
            f"{energy_ev:.9f}",
            "3",  # arcsec
            f"{scan_min_arcsec:.12g}",
            f"{scan_max_arcsec:.12g}",
            str(scan_points),
            "",
        ]
    )
    Path("xoppy.inp").write_text(xoppy_inp, encoding="utf-8")
    with Path("diff_pat.stdout").open("w", encoding="utf-8") as stdout:
        completed = subprocess.run(
            [str(diff_pat_bin)],
            stdin=Path("xoppy.inp").open("r", encoding="utf-8"),
            stdout=stdout,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if completed.returncode != 0:
        raise RuntimeError(f"diff_pat failed with exit {completed.returncode}; see {Path.cwd() / 'diff_pat.stdout'}")
    if not Path("diff_pat.dat").exists() or not Path("diff_pat.par").exists():
        raise RuntimeError("diff_pat did not produce diff_pat.dat and diff_pat.par")


def _write_map_csv(path: Path, curves: list[dict[str, object]], base: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["ring_id", "design_energy_keV", "curve_csv", "source", "status"],
        )
        writer.writeheader()
        for curve in curves:
            writer.writerow(
                {
                    "ring_id": curve["ring_id"],
                    "design_energy_keV": curve["design_energy_keV"],
                    "curve_csv": os.path.relpath(Path(str(curve["curve_csv"])).resolve(), start=base.resolve()),
                    "source": "CRYSTAL-diff_pat",
                    "status": "covered" if curve["ok"] else "needs_attention",
                }
            )


def _write_markdown(path: Path, summary: dict[str, object]) -> None:
    lines = [
        "# XOP/CRYSTAL Multiring Rocking Curves",
        "",
        f"- ok: `{summary['ok']}`",
        f"- source: `{summary['source_version']}`",
        f"- map CSV: `{summary['map_csv']}`",
        "",
        "| ring | energy keV | rows | peak reflectivity | integrated R rad | curve |",
        "|---:|---:|---:|---:|---:|---|",
    ]
    for curve in summary["curves"]:
        lines.append(
            "| {ring_id} | {design_energy_keV:.6g} | {n_rows} | {peak_reflectivity:.6g} | "
            "{integrated_reflectivity_rad:.6g} | {curve_csv} |".format(**curve)
        )
    lines.extend(["", str(summary["note"]), ""])
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
