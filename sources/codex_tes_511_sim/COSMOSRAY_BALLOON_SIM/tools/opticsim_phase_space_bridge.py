#!/usr/bin/env python3
"""Convert opticsim focal-plane phase space CSV files into Cosima EventList sources.

The bridge deliberately keeps the Geant4 optics world and the MEGAlib/Cosima
detector world separate. opticsim transports photons through the optical module
and writes phase_space.csv at the focal plane; this script replays those
particles at the current XZTES Be-window injection plane as a Cosima EventList.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REQUIRED_FIELDS = {
    "event_id",
    "E_keV",
    "x_mm",
    "y_mm",
    "z_mm",
    "ux",
    "uy",
    "uz",
    "weight",
    "source_tag",
}

MEGALIB_PARTICLE_NAME_TO_TYPE = {
    "gamma": 1,
    "e+": 2,
    "e-": 3,
    "proton": 4,
    "anti_proton": 5,
    "neutron": 6,
    "anti_neutron": 7,
    "mu+": 8,
    "mu-": 9,
    "tau+": 10,
    "tau-": 11,
    "nu_e": 12,
    "anti_nu_e": 13,
    "nu_mu": 14,
    "anti_nu_mu": 15,
    "nu_tau": 16,
    "anti_nu_tau": 17,
    "deuteron": 18,
    "triton": 19,
    "He3": 20,
    "alpha": 21,
    "GenericIon": 22,
    "pi+": 23,
    "pi0": 24,
    "pi-": 25,
    "eta": 26,
    "eta_prime": 27,
    "kaon+": 28,
    "kaon0": 29,
    "anti_kaon0": 30,
    "kaon0S": 31,
    "kaon0L": 32,
    "kaon-": 33,
    "lambda": 34,
    "anti_lambda": 35,
    "sigma+": 36,
    "anti_sigma+": 37,
    "sigma0": 38,
    "anti_sigma0": 39,
    "sigma-": 40,
    "anti_sigma-": 41,
    "xi0": 42,
    "anti_xi0": 43,
    "xi-": 44,
    "anti_xi-": 45,
    "omega-": 46,
    "anti_omega-": 47,
    "rho+": 48,
    "rho0": 49,
    "rho-": 50,
    "delta-": 51,
    "delta0": 52,
    "delta+": 53,
    "delta++": 54,
    "omega": 55,
}

GEANT4_ALIASES_TO_MEGALIB_NAME = {
    "anti-proton": "anti_proton",
    "anti-neutron": "anti_neutron",
    "alpha_particle": "alpha",
    "deuterium": "deuteron",
    "tritium": "triton",
    "He3": "He3",
    "GenericIon": "GenericIon",
}

PDG_TO_MEGALIB_PARTICLE_TYPE = {
    22: 1,
    -11: 2,
    11: 3,
    2212: 4,
    -2212: 5,
    2112: 6,
    -2112: 7,
    -13: 8,
    13: 9,
    -15: 10,
    15: 11,
    12: 12,
    -12: 13,
    14: 14,
    -14: 15,
    16: 16,
    -16: 17,
    1000010020: 18,
    1000010030: 19,
    1000020030: 20,
    1000020040: 21,
    211: 23,
    111: 24,
    -211: 25,
    221: 26,
    331: 27,
    321: 28,
    311: 29,
    -311: 30,
    310: 31,
    130: 32,
    -321: 33,
    3122: 34,
    -3122: 35,
    3222: 36,
    -3222: 37,
    3212: 38,
    -3212: 39,
    3112: 40,
    -3112: 41,
    3322: 42,
    -3322: 43,
    3312: 44,
    -3312: 45,
    3334: 46,
    -3334: 47,
    213: 48,
    113: 49,
    -213: 50,
    1114: 51,
    2114: 52,
    2214: 53,
    2224: 54,
    223: 55,
}


@dataclass
class PhaseSpaceRow:
    source_path: Path
    source_line: int
    original_event_id: str
    energy_kev: float
    x_mm: float
    y_mm: float
    z_mm: float
    ux: float
    uy: float
    uz: float
    weight: float
    source_tag: str
    particle_type: int | None = None
    particle_name: str | None = None
    pdg_encoding: int | None = None
    time_s: float | None = None


@dataclass
class BridgeStats:
    rows_seen: int = 0
    rows_written: int = 0
    rows_skipped_weight: int = 0
    rows_skipped_invalid: int = 0
    min_energy_kev: float | None = None
    max_energy_kev: float | None = None
    max_abs_x_numeric: float = 0.0
    max_abs_y_numeric: float = 0.0
    max_radius_numeric: float = 0.0
    min_uz_out: float | None = None
    max_uz_out: float | None = None
    particle_type_counts: dict[int, int] | None = None

    def record(self, energy_kev: float, x: float, y: float, ux: float, uy: float, uz: float, particle_type: int) -> None:
        del ux, uy
        self.rows_written += 1
        self.min_energy_kev = energy_kev if self.min_energy_kev is None else min(self.min_energy_kev, energy_kev)
        self.max_energy_kev = energy_kev if self.max_energy_kev is None else max(self.max_energy_kev, energy_kev)
        self.max_abs_x_numeric = max(self.max_abs_x_numeric, abs(x))
        self.max_abs_y_numeric = max(self.max_abs_y_numeric, abs(y))
        self.max_radius_numeric = max(self.max_radius_numeric, math.hypot(x, y))
        self.min_uz_out = uz if self.min_uz_out is None else min(self.min_uz_out, uz)
        self.max_uz_out = uz if self.max_uz_out is None else max(self.max_uz_out, uz)
        if self.particle_type_counts is None:
            self.particle_type_counts = {}
        self.particle_type_counts[particle_type] = self.particle_type_counts.get(particle_type, 0) + 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase-space",
        action="append",
        required=True,
        type=Path,
        help="Input opticsim phase_space.csv or transmitted_space.csv. Repeat to merge files.",
    )
    parser.add_argument("--name", required=True, help="Run/source stem, e.g. Opticsim_channel_4ring_science.")
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("sources/opticsim_bridge"),
        help="Directory for EventList and manifest outputs.",
    )
    parser.add_argument(
        "--run-config-out",
        type=Path,
        default=Path("run_configs/opticsim_bridge"),
        help="Directory for generated .source files.",
    )
    parser.add_argument(
        "--geometry",
        default="TibetTES_v5_6layers.geo.setup",
        help="Cosima geometry setup path as seen from the run directory.",
    )
    parser.add_argument("--physics-em", default="LivermorePol")
    parser.add_argument("--physics-hd", default="qgsp-bic-hp")
    parser.add_argument("--seed", type=int, default=5112026)
    parser.add_argument(
        "--z-plane",
        type=float,
        default=127.66,
        help="XZTES numeric injection z coordinate. Default is just outside the Be-window +z face.",
    )
    parser.add_argument(
        "--xy-scale",
        type=float,
        default=1.0,
        help="Scale from opticsim focal-plane mm to XZTES numeric x/y units.",
    )
    parser.add_argument(
        "--direction-policy",
        choices=("reverse_z", "negate_all", "as_is", "fixed_minus_z"),
        default="reverse_z",
        help="Map opticsim focal-plane directions into detector injection directions.",
    )
    parser.add_argument(
        "--particle-type",
        type=int,
        default=1,
        help="Fallback MEGAlib particle type. 1 is gamma in the existing project sources.",
    )
    parser.add_argument(
        "--particle-type-field",
        default="auto",
        help=(
            "Optional CSV field containing MEGAlib particle type. Use 'auto' to accept "
            "particle_type if present, then particle_name/particle, then pdg_encoding/pdg; "
            "use 'none' to force --particle-type."
        ),
    )
    parser.add_argument(
        "--time-step-s",
        type=float,
        default=1.0e-9,
        help="Monotonic spacing for --time-policy sequential.",
    )
    parser.add_argument(
        "--time-policy",
        choices=("sequential", "duration", "poisson_duration", "rate", "csv"),
        default="sequential",
        help=(
            "How to assign EventList times. Use 'csv' to read a time_s column from the "
            "phase-space CSV. Use 'poisson_duration' to draw sorted uniform times over "
            "the requested duration, equivalent to a Poisson process conditioned on the "
            "fixed EventList multiplicity."
        ),
    )
    parser.add_argument(
        "--duration-s",
        type=float,
        default=None,
        help="Spread events evenly over this exposure for --time-policy duration.",
    )
    parser.add_argument(
        "--event-rate-hz",
        type=float,
        default=None,
        help="Use this replay rate for --time-policy rate.",
    )
    parser.add_argument(
        "--time-start-s",
        type=float,
        default=0.0,
        help="Start time offset for EventList entries.",
    )
    parser.add_argument(
        "--run-stop",
        choices=("triggers", "duration"),
        default="triggers",
        help="Stop generated .source files by trigger count or by duration.",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Optional cap for EventList rows. By default all positive-weight rows are written.",
    )
    parser.add_argument(
        "--smoke-triggers",
        type=int,
        default=1000,
        help="Also emit a smoke .source capped to this many triggers when enough rows exist.",
    )
    parser.add_argument(
        "--relative-eventlist-path",
        default=None,
        help="Override the EventList path written into .source files. Default is relative to cwd.",
    )
    return parser.parse_args()


def load_rows(paths: Iterable[Path], particle_type_field: str = "auto") -> Iterable[PhaseSpaceRow]:
    for path in paths:
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise ValueError(f"{path} has no CSV header")
            missing = sorted(REQUIRED_FIELDS.difference(reader.fieldnames))
            if missing:
                raise ValueError(f"{path} missing required field(s): {', '.join(missing)}")
            particle_field: str | None = None
            if particle_type_field == "auto" and "particle_type" in reader.fieldnames:
                particle_field = "particle_type"
            elif particle_type_field != "auto" and particle_type_field != "none":
                if particle_type_field not in reader.fieldnames:
                    raise ValueError(f"{path} missing requested --particle-type-field '{particle_type_field}'")
                particle_field = particle_type_field
            particle_name_field: str | None = None
            for candidate in ("particle_name", "particle"):
                if candidate in reader.fieldnames:
                    particle_name_field = candidate
                    break
            pdg_field: str | None = None
            for candidate in ("pdg_encoding", "pdg", "pdg_id"):
                if candidate in reader.fieldnames:
                    pdg_field = candidate
                    break
            time_field: str | None = None
            for candidate in ("time_s", "global_time_s"):
                if candidate in reader.fieldnames:
                    time_field = candidate
                    break
            for line_no, row in enumerate(reader, start=2):
                try:
                    particle_type: int | None = None
                    if particle_field is not None and row.get(particle_field, "") != "":
                        particle_type = int(row[particle_field])
                    particle_name: str | None = None
                    if particle_name_field is not None and row.get(particle_name_field, "") != "":
                        particle_name = row[particle_name_field].strip()
                    pdg_encoding: int | None = None
                    if pdg_field is not None and row.get(pdg_field, "") != "":
                        pdg_encoding = int(row[pdg_field])
                    time_s: float | None = None
                    if time_field is not None and row.get(time_field, "") != "":
                        time_s = float(row[time_field])
                    yield PhaseSpaceRow(
                        source_path=path,
                        source_line=line_no,
                        original_event_id=row["event_id"],
                        energy_kev=float(row["E_keV"]),
                        x_mm=float(row["x_mm"]),
                        y_mm=float(row["y_mm"]),
                        z_mm=float(row["z_mm"]),
                        ux=float(row["ux"]),
                        uy=float(row["uy"]),
                        uz=float(row["uz"]),
                        weight=float(row["weight"]),
                        source_tag=row["source_tag"],
                        particle_type=particle_type,
                        particle_name=particle_name,
                        pdg_encoding=pdg_encoding,
                        time_s=time_s,
                    )
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"{path}:{line_no}: invalid numeric row: {exc}") from exc


def normalize_direction(ux: float, uy: float, uz: float) -> tuple[float, float, float]:
    norm = math.sqrt(ux * ux + uy * uy + uz * uz)
    if not math.isfinite(norm) or norm <= 0.0:
        raise ValueError("direction norm is not positive and finite")
    return ux / norm, uy / norm, uz / norm


def map_direction(row: PhaseSpaceRow, policy: str) -> tuple[float, float, float]:
    if policy == "reverse_z":
        ux, uy, uz = row.ux, row.uy, -row.uz
    elif policy == "negate_all":
        ux, uy, uz = -row.ux, -row.uy, -row.uz
    elif policy == "as_is":
        ux, uy, uz = row.ux, row.uy, row.uz
    elif policy == "fixed_minus_z":
        ux, uy, uz = 0.0, 0.0, -1.0
    else:
        raise ValueError(f"unknown direction policy: {policy}")
    return normalize_direction(ux, uy, uz)


def event_time_seconds(
    row: PhaseSpaceRow,
    index: int,
    args: argparse.Namespace,
    total_rows_hint: int | None = None,
    precomputed_times: list[float] | None = None,
) -> float:
    if args.time_policy == "csv":
        if row.time_s is None:
            raise ValueError("--time-policy csv requires a time_s or global_time_s CSV column")
        if not math.isfinite(row.time_s):
            raise ValueError("CSV time_s is not finite")
        return row.time_s
    if args.time_policy == "sequential":
        return args.time_start_s + index * args.time_step_s
    if args.time_policy == "rate":
        if args.event_rate_hz is None or args.event_rate_hz <= 0.0:
            raise ValueError("--event-rate-hz must be positive for --time-policy rate")
        return args.time_start_s + index / args.event_rate_hz
    if args.time_policy == "duration":
        if args.duration_s is None or args.duration_s <= 0.0:
            raise ValueError("--duration-s must be positive for --time-policy duration")
        if total_rows_hint is not None and total_rows_hint > 1:
            return args.time_start_s + args.duration_s * index / (total_rows_hint - 1)
        return args.time_start_s + index * args.time_step_s
    if args.time_policy == "poisson_duration":
        if precomputed_times is None:
            raise ValueError("internal error: poisson_duration requires precomputed times")
        if index >= len(precomputed_times):
            raise ValueError("internal error: poisson_duration index exceeds precomputed times")
        return precomputed_times[index]
    raise ValueError(f"unknown time policy: {args.time_policy}")


def resolve_particle_type(row: PhaseSpaceRow, args: argparse.Namespace) -> int:
    if args.particle_type_field == "none":
        return args.particle_type
    if row.particle_type is not None:
        return row.particle_type
    if args.particle_type_field == "auto":
        if row.particle_name:
            name = GEANT4_ALIASES_TO_MEGALIB_NAME.get(row.particle_name, row.particle_name)
            if name not in MEGALIB_PARTICLE_NAME_TO_TYPE:
                raise ValueError(f"unsupported particle_name '{row.particle_name}'")
            return MEGALIB_PARTICLE_NAME_TO_TYPE[name]
        if row.pdg_encoding is not None:
            if row.pdg_encoding not in PDG_TO_MEGALIB_PARTICLE_TYPE:
                raise ValueError(f"unsupported pdg_encoding {row.pdg_encoding}")
            return PDG_TO_MEGALIB_PARTICLE_TYPE[row.pdg_encoding]
        return args.particle_type
    return args.particle_type


def count_positive_weight_rows(args: argparse.Namespace) -> int:
    count = 0
    for row in load_rows(args.phase_space, args.particle_type_field):
        if row.weight <= 0.0:
            continue
        count += 1
        if args.max_rows is not None and count >= args.max_rows:
            break
    return count


def write_event_list(args: argparse.Namespace, event_list_path: Path) -> tuple[BridgeStats, list[dict[str, object]]]:
    stats = BridgeStats()
    skipped_examples: list[dict[str, object]] = []
    next_id = 0
    duration_rows_hint = args.max_rows
    if args.time_policy in {"duration", "poisson_duration"} and duration_rows_hint is None:
        duration_rows_hint = count_positive_weight_rows(args)
    precomputed_times: list[float] | None = None
    if args.time_policy == "poisson_duration":
        if args.duration_s is None or args.duration_s <= 0.0:
            raise ValueError("--duration-s must be positive for --time-policy poisson_duration")
        if duration_rows_hint is None or duration_rows_hint <= 0:
            raise ValueError("no rows available for --time-policy poisson_duration")
        rng = random.Random(args.seed)
        t0 = args.time_start_s
        precomputed_times = sorted(t0 + rng.random() * args.duration_s for _ in range(duration_rows_hint))

    with event_list_path.open("w", newline="") as handle:
        for row in load_rows(args.phase_space, args.particle_type_field):
            stats.rows_seen += 1
            if row.weight <= 0.0:
                stats.rows_skipped_weight += 1
                continue
            if args.max_rows is not None and next_id >= args.max_rows:
                break
            try:
                ux, uy, uz = map_direction(row, args.direction_policy)
                x_numeric = row.x_mm * args.xy_scale
                y_numeric = row.y_mm * args.xy_scale
                z_numeric = args.z_plane
                particle_type = resolve_particle_type(row, args)
                if not all(
                    math.isfinite(v)
                    for v in (row.energy_kev, x_numeric, y_numeric, z_numeric, ux, uy, uz)
                ):
                    raise ValueError("non-finite output value")
            except ValueError as exc:
                stats.rows_skipped_invalid += 1
                if len(skipped_examples) < 5:
                    skipped_examples.append(
                        {
                            "path": str(row.source_path),
                            "line": row.source_line,
                            "event_id": row.original_event_id,
                            "reason": str(exc),
                        }
                    )
                continue

            try:
                event_time = event_time_seconds(row, next_id, args, duration_rows_hint, precomputed_times)
            except ValueError as exc:
                stats.rows_skipped_invalid += 1
                if len(skipped_examples) < 5:
                    skipped_examples.append(
                        {
                            "path": str(row.source_path),
                            "line": row.source_line,
                            "event_id": row.original_event_id,
                            "reason": str(exc),
                        }
                    )
                continue
            fields = [
                next_id,
                0,
                particle_type,
                0,
                f"{event_time:.12e}",
                f"{x_numeric:.12g}",
                f"{y_numeric:.12g}",
                f"{z_numeric:.12g}",
                f"{ux:.12g}",
                f"{uy:.12g}",
                f"{uz:.12g}",
                "0",
                "0",
                "0",
                f"{row.energy_kev:.12g}",
            ]
            handle.write(" ".join(str(v) for v in fields))
            handle.write("\n")
            stats.record(row.energy_kev, x_numeric, y_numeric, ux, uy, uz, particle_type)
            next_id += 1

    return stats, skipped_examples


def write_source_file(
    path: Path,
    *,
    name: str,
    geometry: str,
    physics_em: str,
    physics_hd: str,
    seed: int,
    event_list_ref: str,
    triggers: int,
    run_stop: str,
    duration_s: float | None,
    output_stem: str,
) -> None:
    source_name = f"{name}_PhaseSpace"
    content = f"""# Auto-generated opticsim-to-Cosima EventList bridge source.
# The source replays opticsim focal-plane phase-space particles at the
# existing XZTES Be-window injection plane. Run from the repository root so
# the EventList path below resolves correctly.

Version 1
Geometry {geometry}
PhysicsListEM {physics_em}
PhysicsListHD {physics_hd}
StoreSimulationInfo all
DiscretizeHits true
DetectorTimeConstant 1e-9
Seed {seed}

Run {name}
{name}.FileName {output_stem}
"""
    if run_stop == "duration":
        if duration_s is None or duration_s <= 0.0:
            raise ValueError("--duration-s must be positive when --run-stop duration")
        content += f"{name}.Duration {duration_s:.12g}\n"
    else:
        content += f"{name}.Triggers {triggers}\n"
    content += f"""\
{name}.Source {source_name}

{source_name}.EventList {event_list_ref}
"""
    path.write_text(content)


def manifest_dict(
    args: argparse.Namespace,
    event_list_path: Path,
    source_path: Path,
    smoke_source_path: Path | None,
    stats: BridgeStats,
    skipped_examples: list[dict[str, object]],
    event_list_ref: str,
) -> dict[str, object]:
    warnings = [
        "Cosima EventList positions are parsed with cm units internally; these files intentionally keep the same numeric coordinate convention as the existing XZTES source files.",
        "Default direction_policy=reverse_z maps opticsim rays traveling toward +z at the focal plane into detector-injection rays traveling toward -z from the Be-window side.",
        "This bridge replaces the parameterized post-optics science-beam model. It can carry prompt all-particle focal-plane crossings from an opticsim transport, but it does not by itself create a delayed activation isotope inventory or decay workflow for optics hardware.",
    ]
    return {
        "name": args.name,
        "inputs": [str(path) for path in args.phase_space],
        "event_list": str(event_list_path),
        "event_list_reference_in_source": event_list_ref,
        "source_file": str(source_path),
        "smoke_source_file": str(smoke_source_path) if smoke_source_path else None,
        "rows_seen": stats.rows_seen,
        "rows_written": stats.rows_written,
        "rows_skipped_weight": stats.rows_skipped_weight,
        "rows_skipped_invalid": stats.rows_skipped_invalid,
        "energy_kev_min": stats.min_energy_kev,
        "energy_kev_max": stats.max_energy_kev,
        "max_abs_x_numeric": stats.max_abs_x_numeric,
        "max_abs_y_numeric": stats.max_abs_y_numeric,
        "max_radius_numeric": stats.max_radius_numeric,
        "direction_uz_min": stats.min_uz_out,
        "direction_uz_max": stats.max_uz_out,
        "particle_type_counts": {str(k): v for k, v in sorted((stats.particle_type_counts or {}).items())},
        "coordinate_policy": {
            "z_plane_numeric": args.z_plane,
            "xy_scale_numeric_per_opticsim_mm": args.xy_scale,
            "direction_policy": args.direction_policy,
            "particle_type": args.particle_type,
            "particle_type_field": args.particle_type_field,
            "time_policy": args.time_policy,
            "time_step_s": args.time_step_s,
            "time_start_s": args.time_start_s,
            "duration_s": args.duration_s,
            "event_rate_hz": args.event_rate_hz,
            "run_stop": args.run_stop,
        },
        "skipped_examples": skipped_examples,
        "warnings": warnings,
    }


def main() -> int:
    args = parse_args()
    for path in args.phase_space:
        if not path.exists():
            raise FileNotFoundError(path)

    args.outdir.mkdir(parents=True, exist_ok=True)
    args.run_config_out.mkdir(parents=True, exist_ok=True)

    event_list_path = args.outdir / f"{args.name}.eventlist.dat"
    source_path = args.run_config_out / f"{args.name}.source"
    smoke_source_path = args.run_config_out / f"{args.name}_smoke{args.smoke_triggers}.source"
    manifest_path = args.outdir / f"{args.name}.manifest.json"

    event_list_ref = args.relative_eventlist_path or str(event_list_path)
    stats, skipped_examples = write_event_list(args, event_list_path)
    if stats.rows_written == 0:
        raise RuntimeError("no positive-weight valid rows were written to the EventList")

    output_stem = str(args.outdir / args.name)
    write_source_file(
        source_path,
        name=args.name,
        geometry=args.geometry,
        physics_em=args.physics_em,
        physics_hd=args.physics_hd,
        seed=args.seed,
        event_list_ref=event_list_ref,
        triggers=stats.rows_written,
        run_stop=args.run_stop,
        duration_s=args.duration_s,
        output_stem=output_stem,
    )

    smoke_source: Path | None = None
    if args.smoke_triggers > 0:
        smoke_triggers = min(args.smoke_triggers, stats.rows_written)
        smoke_source = smoke_source_path
        write_source_file(
            smoke_source,
            name=f"{args.name}_Smoke",
            geometry=args.geometry,
            physics_em=args.physics_em,
            physics_hd=args.physics_hd,
            seed=args.seed,
            event_list_ref=event_list_ref,
            triggers=smoke_triggers,
            run_stop="triggers",
            duration_s=None,
            output_stem=str(args.outdir / f"{args.name}_smoke{smoke_triggers}"),
        )

    manifest = manifest_dict(args, event_list_path, source_path, smoke_source, stats, skipped_examples, event_list_ref)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
