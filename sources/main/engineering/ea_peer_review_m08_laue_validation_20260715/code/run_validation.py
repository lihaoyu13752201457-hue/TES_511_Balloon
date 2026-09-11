#!/usr/bin/env python3
"""Run the M08 Geant4 single-tile validation matrix."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXE = Path("/tmp/ea_m08_bfull_build_20260715/laue_multiring_bfull_demo")
ENERGIES_KEV = (480, 500, 511, 530, 550)
OFFSETS_ARCSEC = (-90, -60, -30, -18, -12, -6, 0, 6, 12, 18, 30, 60, 90)


@dataclass(frozen=True)
class RunSpec:
    group: str
    name: str
    energy_keV: int
    offset_arcsec: float
    n_events: int
    seed: int
    max_step_mm: float
    source_jitter_mm: float
    outgoing_model: str

    @property
    def out_dir(self) -> Path:
        return ROOT / "outputs" / self.group / self.name


def offset_tag(value: float) -> str:
    sign = "p" if value >= 0.0 else "m"
    return f"{sign}{abs(value):06.1f}".replace(".", "p")


def build_specs(args: argparse.Namespace) -> list[RunSpec]:
    specs: list[RunSpec] = []
    if args.section in ("all", "rta"):
        for energy_index, energy in enumerate(ENERGIES_KEV):
            for offset_index, offset in enumerate(OFFSETS_ARCSEC):
                specs.append(
                    RunSpec(
                        group="rta_scan",
                        name=f"E{energy}_off_{offset_tag(float(offset))}",
                        energy_keV=energy,
                        offset_arcsec=float(offset),
                        n_events=args.n_rta,
                        seed=2026071500 + energy_index * 100 + offset_index,
                        max_step_mm=1.0,
                        source_jitter_mm=0.0,
                        outgoing_model="gaussian_plane",
                    )
                )
    if args.section in ("all", "step"):
        for index, max_step in enumerate((0.0, 5.0, 1.0, 0.2)):
            tag = "unlimited" if max_step == 0.0 else f"{max_step:g}mm".replace(".", "p")
            specs.append(
                RunSpec(
                    group="step_convergence",
                    name=f"step_{tag}",
                    energy_keV=511,
                    offset_arcsec=0.0,
                    n_events=args.n_step,
                    seed=20260715511,
                    max_step_mm=max_step,
                    source_jitter_mm=0.0,
                    outgoing_model="gaussian_plane",
                )
            )
    if args.section in ("all", "mosaic"):
        for source_name, jitter, n_events in (
            ("point", 0.0, args.n_mosaic_point),
            ("footprint18mm", 18.0, args.n_mosaic_footprint),
        ):
            for model_index, model in enumerate(("gaussian_plane", "gaussian_outgoing", "ideal_plane")):
                specs.append(
                    RunSpec(
                        group="mosaic_outgoing",
                        name=f"{source_name}_{model}",
                        energy_keV=511,
                        offset_arcsec=0.0,
                        n_events=n_events,
                        seed=20260715600 + model_index,
                        max_step_mm=1.0,
                        source_jitter_mm=jitter,
                        outgoing_model=model,
                    )
                )
    return specs


def run_one(exe: Path, spec: RunSpec, force: bool) -> dict[str, object]:
    summary_path = spec.out_dir / "summary.json"
    if summary_path.exists() and not force:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        return {"name": spec.name, "group": spec.group, "status": "existing", "n": summary["n_primaries"]}
    spec.out_dir.mkdir(parents=True, exist_ok=True)
    ring_config = ROOT / "data" / "ring_configs" / f"ge111_f10m_{spec.energy_keV}keV_single_tile.csv"
    curve = ROOT / "data" / "xop_fixed_10p218801mm" / f"ge111_{spec.energy_keV}keV_rocking_curve.csv"
    command = [
        str(exe),
        "--n",
        str(spec.n_events),
        "--seed",
        str(spec.seed),
        "--ring-config",
        str(ring_config),
        "--rocking-curve-csv",
        str(curve),
        "--focal-mm",
        "10000",
        "--source-jitter-mm",
        f"{spec.source_jitter_mm:.12g}",
        "--offaxis-x-arcmin",
        f"{spec.offset_arcsec / 60.0:.12g}",
        "--only-ring-id",
        "0",
        "--only-tile-id",
        "0",
        "--max-step-mm",
        f"{spec.max_step_mm:.12g}",
        "--outgoing-mosaic-model",
        spec.outgoing_model,
        "--out",
        str(spec.out_dir),
    ]
    metadata = {
        "group": spec.group,
        "name": spec.name,
        "energy_keV": spec.energy_keV,
        "offset_arcsec": spec.offset_arcsec,
        "n_events": spec.n_events,
        "seed": spec.seed,
        "max_step_mm": spec.max_step_mm,
        "source_jitter_mm": spec.source_jitter_mm,
        "outgoing_model": spec.outgoing_model,
        "command": command,
    }
    (spec.out_dir / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (spec.out_dir / "run.log").open("w", encoding="utf-8") as log:
        completed = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=False)
    if completed.returncode != 0 or not summary_path.exists():
        raise RuntimeError(f"run failed ({completed.returncode}): {spec.group}/{spec.name}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if int(summary["n_primaries"]) != spec.n_events:
        raise RuntimeError(f"primary-count mismatch: {spec.group}/{spec.name}")
    return {"name": spec.name, "group": spec.group, "status": "ran", "n": spec.n_events}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", type=Path, default=DEFAULT_EXE)
    parser.add_argument("--section", choices=("all", "rta", "step", "mosaic"), default="all")
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--n-rta", type=int, default=20000)
    parser.add_argument("--n-step", type=int, default=50000)
    parser.add_argument("--n-mosaic-point", type=int, default=100000)
    parser.add_argument("--n-mosaic-footprint", type=int, default=50000)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if not args.exe.is_file():
        raise FileNotFoundError(args.exe)
    if "G4LEDATA" not in os.environ:
        raise RuntimeError("Geant4 data environment is missing; invoke through run_with_geant4_114.sh")
    specs = build_specs(args)
    results: list[dict[str, object]] = []
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        future_map = {pool.submit(run_one, args.exe, spec, args.force): spec for spec in specs}
        for future in as_completed(future_map):
            spec = future_map[future]
            try:
                results.append(future.result())
                print(f"OK {spec.group}/{spec.name}", flush=True)
            except Exception as exc:
                failures.append(f"{spec.group}/{spec.name}: {exc}")
                print(f"FAIL {failures[-1]}", flush=True)

    manifest = {
        "ok": not failures and len(results) == len(specs),
        "section": args.section,
        "executable": str(args.exe),
        "requested_runs": len(specs),
        "completed_runs": len(results),
        "failures": failures,
        "results": sorted(results, key=lambda item: (str(item["group"]), str(item["name"]))),
    }
    path = ROOT / "outputs" / f"run_manifest_{args.section}.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"ok": manifest["ok"], "manifest": str(path), "runs": len(results)}, indent=2))
    return 0 if manifest["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
