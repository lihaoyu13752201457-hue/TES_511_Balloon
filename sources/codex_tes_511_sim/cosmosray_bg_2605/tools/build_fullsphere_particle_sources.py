#!/usr/bin/env python3
"""Build per-particle full-sphere Cosima sources for 2605 production.

The archive source is a single all-particle run.  The 2602 production workflow
used one source per particle so gamma could define the Monte Carlo statistics
and non-gamma particles could be flux-matched with replicas.  This script
recreates that layout using the corrected 20-bin down/up full-sphere inputs.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PARTICLE_ORDER = ["gamma", "n", "p", "alpha", "eminus", "eplus", "muminus", "muplus"]
PARTICLE_TYPE = {
    "gamma": 1,
    "eplus": 2,
    "eminus": 3,
    "p": 4,
    "n": 6,
    "muplus": 8,
    "muminus": 9,
    "alpha": 21,
}


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    rows.sort(key=lambda r: (PARTICLE_ORDER.index(r["particle"]), int(r["bin_id"])))
    return rows


def spectrum_dp_path(row: dict[str, str], spectrum_dir_name: str) -> Path:
    raw = Path(row["cosima_spectrum_path"])
    return ROOT / raw.parent.parent / spectrum_dir_name / raw.name


def lightcurve_path(row: dict[str, str]) -> Path:
    direction = "down" if row["component_name"].endswith("_down") else "up"
    name = f"{row['particle']}_bin{row['bin_id']}_{direction}_BHNo.lc"
    return ROOT / "time_variable_balloon_background_curves_verified" / "lightcurves_dp" / name


def write_source(
    particle: str,
    rows: list[dict[str, str]],
    outdir: Path,
    *,
    include_lightcurves: bool,
    spectrum_dir_name: str,
) -> dict[str, object]:
    outdir.mkdir(parents=True, exist_ok=True)
    run_name = f"Background_{particle}_fullsphere20"
    source_path = outdir / f"{run_name}.source"
    total_flux = sum(float(r["flux_cm2_s"]) for r in rows)

    lines: list[str] = [
        "# Auto-generated per-particle 2605 full-sphere source",
        "# theta=0-180 deg, phi=0-360 deg, 20 equal-mu bins",
        f"# particle={particle} total_flux_cm2_s={total_flux:.12e}",
        f"# spectrum_dir={spectrum_dir_name}",
        "",
        "Geometry TibetTES_v5_6layers.geo.setup",
        "PhysicsListHD qgsp-bic-hp",
        "PhysicsListEM LivermorePol",
        "StoreSimulationInfo all",
        "StoreIsotopes true",
        "DecayMode ActivationBuildUp",
        "DetectorTimeConstant 1e-9",
        "Seed 12345",
        "",
        f"Run {run_name}",
        f"{run_name}.Events 1000000",
        f"{run_name}.FileName {run_name}",
        f"{run_name}.IsotopeProductionFile {run_name}.isotopes",
        "",
    ]
    for row in rows:
        lines.append(f"{run_name}.Source {row['component_name']}")
    lines.append("")

    for row in rows:
        name = row["component_name"]
        spec = spectrum_dp_path(row, spectrum_dir_name)
        if not spec.exists():
            raise FileNotFoundError(spec)
        if include_lightcurves:
            lc = lightcurve_path(row)
            if not lc.exists():
                raise FileNotFoundError(lc)
        theta_min = float(row["theta_min_deg"])
        theta_max = float(row["theta_max_deg"])
        lines.extend(
            [
                f"{name}.ParticleType {PARTICLE_TYPE[particle]}",
                f"{name}.Beam FarFieldAreaSource {theta_min:.3f} {theta_max:.3f} 0.000 360.000",
                f"{name}.Spectrum File {rel(spec)}",
                f"{name}.Flux {float(row['flux_cm2_s']):.12e}",
            ]
        )
        if include_lightcurves:
            lines.append(f"{name}.LightCurve File false {rel(lc)}")
        lines.append("")

    source_path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "particle": particle,
        "source": rel(source_path),
        "components": len(rows),
        "total_flux_cm2_s": total_flux,
        "include_lightcurves": include_lightcurves,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, default=ROOT / "expacs_fullsphere_20bin_sources/manifest.csv")
    ap.add_argument("--outdir", type=Path, default=ROOT / "megalib_sources_fullsphere20")
    ap.add_argument("--with-lightcurves", action="store_true")
    ap.add_argument(
        "--spectrum-dir-name",
        default="cosima_spectra_dp_2602units",
        help="Spectrum directory under expacs_fullsphere_20bin_sources. Default matches 2602 energy-axis convention.",
    )
    args = ap.parse_args()
    if not args.manifest.is_absolute():
        args.manifest = ROOT / args.manifest
    if not args.outdir.is_absolute():
        args.outdir = ROOT / args.outdir

    rows = load_manifest(args.manifest)
    by_particle: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        particle = row["particle"]
        if particle not in PARTICLE_TYPE:
            raise ValueError(f"Unknown particle in manifest: {particle}")
        by_particle[particle].append(row)

    summaries = []
    for particle in PARTICLE_ORDER:
        part_rows = by_particle.get(particle, [])
        if len(part_rows) != 20:
            raise ValueError(f"{particle}: expected 20 bins, got {len(part_rows)}")
        summaries.append(
            write_source(
                particle,
                part_rows,
                args.outdir,
                include_lightcurves=args.with_lightcurves,
                spectrum_dir_name=args.spectrum_dir_name,
            )
        )

    summary_path = args.outdir / "flux_summary.json"
    summary_path.write_text(json.dumps(summaries, indent=2) + "\n", encoding="utf-8")
    csv_path = args.outdir / "flux_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)

    for row in summaries:
        print(
            f"{row['particle']:8s} flux={row['total_flux_cm2_s']:.12e} "
            f"components={row['components']} source={row['source']}"
        )
    print(f"Wrote {rel(summary_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
