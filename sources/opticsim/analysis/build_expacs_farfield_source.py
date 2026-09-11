from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


PARTICLE_TYPE_TO_NAME = {
    1: ("gamma", 22),
    2: ("e+", -11),
    3: ("e-", 11),
    4: ("proton", 2212),
    6: ("neutron", 2112),
    8: ("mu+", -13),
    9: ("mu-", 13),
    21: ("alpha", 1000020040),
}


@dataclass(frozen=True)
class Component:
    name: str
    particle_type: int
    particle_name: str
    pdg_encoding: int
    theta_min_deg: float
    theta_max_deg: float
    phi_min_deg: float
    phi_max_deg: float
    spectrum_file: str
    flux_cm2_s: float


def parse_cosima_source(path: Path, repo_root: Path) -> list[Component]:
    state: dict[str, dict[str, object]] = {}
    particle_re = re.compile(r"^([A-Za-z0-9_]+)\.ParticleType\s+(\d+)\s*$")
    beam_re = re.compile(
        r"^([A-Za-z0-9_]+)\.Beam\s+FarFieldAreaSource\s+"
        r"([0-9.eE+-]+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s*$"
    )
    spectrum_re = re.compile(r"^([A-Za-z0-9_]+)\.Spectrum\s+File\s+(.+?)\s*$")
    flux_re = re.compile(r"^([A-Za-z0-9_]+)\.Flux\s+([0-9.eE+-]+)\s*$")
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        for regex, keys in (
            (particle_re, ("particle_type",)),
            (beam_re, ("theta_min_deg", "theta_max_deg", "phi_min_deg", "phi_max_deg")),
            (spectrum_re, ("spectrum_file",)),
            (flux_re, ("flux_cm2_s",)),
        ):
            match = regex.match(line)
            if not match:
                continue
            name = match.group(1)
            row = state.setdefault(name, {})
            values = match.groups()[1:]
            for key, value in zip(keys, values):
                if key == "spectrum_file":
                    row[key] = value
                elif key == "particle_type":
                    row[key] = int(value)
                else:
                    row[key] = float(value)
            break

    components: list[Component] = []
    required = {
        "particle_type",
        "theta_min_deg",
        "theta_max_deg",
        "phi_min_deg",
        "phi_max_deg",
        "spectrum_file",
        "flux_cm2_s",
    }
    for name, row in sorted(state.items()):
        if not required.issubset(row):
            continue
        particle_type = int(row["particle_type"])
        if particle_type not in PARTICLE_TYPE_TO_NAME:
            raise ValueError(f"unsupported MEGAlib particle type {particle_type} in {name}")
        particle_name, pdg_encoding = PARTICLE_TYPE_TO_NAME[particle_type]
        spectrum_path = Path(str(row["spectrum_file"]))
        if not spectrum_path.is_absolute():
            spectrum_path = repo_root / spectrum_path
        components.append(
            Component(
                name=name,
                particle_type=particle_type,
                particle_name=particle_name,
                pdg_encoding=pdg_encoding,
                theta_min_deg=float(row["theta_min_deg"]),
                theta_max_deg=float(row["theta_max_deg"]),
                phi_min_deg=float(row["phi_min_deg"]),
                phi_max_deg=float(row["phi_max_deg"]),
                spectrum_file=str(spectrum_path),
                flux_cm2_s=float(row["flux_cm2_s"]),
            )
        )
    if not components:
        raise ValueError(f"no complete FarFieldAreaSource components parsed from {path}")
    return components


def read_spectrum(path: Path) -> tuple[list[float], list[float]]:
    energies: list[float] = []
    weights: list[float] = []
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) == 3 and parts[0] == "DP":
            energies.append(float(parts[1]))
            weights.append(max(0.0, float(parts[2])))
    if len(energies) < 2:
        raise ValueError(f"spectrum has fewer than two DP rows: {path}")
    return energies, weights


def trapezoid_areas(energies: list[float], weights: list[float]) -> list[float]:
    areas: list[float] = []
    for idx in range(len(energies) - 1):
        width = max(0.0, energies[idx + 1] - energies[idx])
        areas.append(0.5 * (weights[idx] + weights[idx + 1]) * width)
    if sum(areas) <= 0.0:
        return [max(0.0, energies[idx + 1] - energies[idx]) for idx in range(len(energies) - 1)]
    return areas


def choose_index(weights: Iterable[float], rng: random.Random) -> int:
    values = list(weights)
    total = sum(values)
    if total <= 0.0:
        raise ValueError("cannot sample from non-positive weights")
    threshold = rng.random() * total
    running = 0.0
    for idx, value in enumerate(values):
        running += value
        if running >= threshold:
            return idx
    return len(values) - 1


def sample_energy(energies: list[float], weights: list[float], rng: random.Random) -> float:
    areas = trapezoid_areas(energies, weights)
    idx = choose_index(areas, rng)
    return energies[idx] + rng.random() * (energies[idx + 1] - energies[idx])


def sample_direction(component: Component, rng: random.Random) -> tuple[float, float, float, float, float]:
    cos_a = math.cos(math.radians(component.theta_min_deg))
    cos_b = math.cos(math.radians(component.theta_max_deg))
    cos_theta = min(cos_a, cos_b) + rng.random() * abs(cos_a - cos_b)
    theta = math.degrees(math.acos(max(-1.0, min(1.0, cos_theta))))
    phi = component.phi_min_deg + rng.random() * (component.phi_max_deg - component.phi_min_deg)
    sin_theta = math.sqrt(max(0.0, 1.0 - cos_theta * cos_theta))
    phi_rad = math.radians(phi)
    return sin_theta * math.cos(phi_rad), sin_theta * math.sin(phi_rad), cos_theta, theta, phi


def orthonormal_disk_basis(ux: float, uy: float, uz: float) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    if abs(uz) < 0.9:
        ax, ay, az = -uy, ux, 0.0
    else:
        ax, ay, az = 0.0, -uz, uy
    norm = math.sqrt(ax * ax + ay * ay + az * az)
    ax, ay, az = ax / norm, ay / norm, az / norm
    bx = uy * az - uz * ay
    by = uz * ax - ux * az
    bz = ux * ay - uy * ax
    return (ax, ay, az), (bx, by, bz)


def sample_position_on_farfield_disk(
    ux: float,
    uy: float,
    uz: float,
    source_distance_mm: float,
    source_radius_mm: float,
    rng: random.Random,
) -> tuple[float, float, float]:
    a, b = orthonormal_disk_basis(ux, uy, uz)
    radius = source_radius_mm * math.sqrt(rng.random())
    angle = 2.0 * math.pi * rng.random()
    dx = radius * math.cos(angle)
    dy = radius * math.sin(angle)
    return (
        -source_distance_mm * ux + dx * a[0] + dy * b[0],
        -source_distance_mm * uy + dx * a[1] + dy * b[1],
        -source_distance_mm * uz + dx * a[2] + dy * b[2],
    )


def write_config(path: Path, args: argparse.Namespace, components: list[Component]) -> dict[str, object]:
    area_cm2 = math.pi * (args.source_radius_mm / 10.0) ** 2
    total_flux = sum(component.flux_cm2_s for component in components)
    doc = {
        "created_by": "analysis/build_expacs_farfield_source.py",
        "cosima_source": str(args.cosima_source),
        "coordinate_convention": {
            "theta_phi_definition": "same theta/phi bins as the Cosima FarFieldAreaSource; theta=0 is +z in the opticsim source frame",
            "position_rule": "primary position = -source_distance_mm * direction + random offset in a disk perpendicular to direction",
            "momentum_direction": "ux,uy,uz points from the far-field source disk toward the optics origin",
            "pointing_note": "If the optics axis is not aligned with the local atmospheric zenith axis, rotate the sampled primary vectors before Geant4 injection.",
            "world_20m_12m_focal_note": "source_distance_mm is only the upstream sampling-plane distance from the optics origin. If the detector/focal plane is +12 m downstream and the world span is limited to 20 m, use source_distance_mm <= 8000 mm or enlarge the world; the flux normalization is set by source_radius_mm, not this distance.",
        },
        "source_distance_mm": args.source_distance_mm,
        "source_radius_mm": args.source_radius_mm,
        "source_area_cm2": area_cm2,
        "total_flux_cm2_s": total_flux,
        "total_rate_hz_for_this_source_area": total_flux * area_cm2,
        "sample_weight_convention": {
            "with_duration_s": "CSV weight is the dimensionless expected number of physical primaries represented by one sampled row: total_rate_hz * duration_s / n.",
            "without_duration_s": "CSV rows are sampled as a Poisson sequence and weight is 1.0 per primary.",
        },
        "components": [asdict(component) for component in components],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, sort_keys=True))
    return doc


def write_samples(path: Path, args: argparse.Namespace, components: list[Component], config: dict[str, object]) -> None:
    rng = random.Random(args.seed)
    spectra = {component.name: read_spectrum(Path(component.spectrum_file)) for component in components}
    component_weights = [component.flux_cm2_s for component in components]
    total_rate_hz = float(config["total_rate_hz_for_this_source_area"])
    if total_rate_hz <= 0.0:
        raise ValueError("total far-field source rate is not positive")
    path.parent.mkdir(parents=True, exist_ok=True)
    if args.duration_s is not None:
        times = sorted(rng.random() * args.duration_s for _ in range(args.n))
    else:
        times = []
        time_s = 0.0
        for _ in range(args.n):
            time_s += -math.log(max(1.0e-16, 1.0 - rng.random())) / total_rate_hz
            times.append(time_s)
    if args.duration_s is not None:
        event_weight = total_rate_hz * args.duration_s / max(1, args.n)
    else:
        event_weight = 1.0
    fields = [
        "event_id",
        "time_s",
        "particle_name",
        "pdg_encoding",
        "E_keV",
        "x_mm",
        "y_mm",
        "z_mm",
        "ux",
        "uy",
        "uz",
        "weight",
        "source_tag",
        "component",
        "theta_deg",
        "phi_deg",
        "source_radius_mm",
        "source_distance_mm",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for event_id, time_s in enumerate(times):
            component = components[choose_index(component_weights, rng)]
            energies, weights = spectra[component.name]
            energy_kev = sample_energy(energies, weights, rng)
            ux, uy, uz, theta, phi = sample_direction(component, rng)
            x, y, z = sample_position_on_farfield_disk(
                ux,
                uy,
                uz,
                args.source_distance_mm,
                args.source_radius_mm,
                rng,
            )
            writer.writerow(
                {
                    "event_id": event_id,
                    "time_s": f"{time_s:.12e}",
                    "particle_name": component.particle_name,
                    "pdg_encoding": component.pdg_encoding,
                    "E_keV": f"{energy_kev:.12g}",
                    "x_mm": f"{x:.12g}",
                    "y_mm": f"{y:.12g}",
                    "z_mm": f"{z:.12g}",
                    "ux": f"{ux:.12g}",
                    "uy": f"{uy:.12g}",
                    "uz": f"{uz:.12g}",
                    "weight": f"{event_weight:.12e}",
                    "source_tag": "expacs_parma_allparticle_farfield",
                    "component": component.name,
                    "theta_deg": f"{theta:.8f}",
                    "phi_deg": f"{phi:.8f}",
                    "source_radius_mm": f"{args.source_radius_mm:.12g}",
                    "source_distance_mm": f"{args.source_distance_mm:.12g}",
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an opticsim all-particle far-field source from the Cosima EXPACS/PARMA source.")
    parser.add_argument("--cosima-source", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--out-config", type=Path, required=True)
    parser.add_argument("--sample-out", type=Path, default=None)
    parser.add_argument("--n", type=int, default=0, help="Number of primary samples to write when --sample-out is set.")
    parser.add_argument("--duration-s", type=float, default=None, help="Optional exposure duration for uniformly sampled event times.")
    parser.add_argument("--seed", type=int, default=20260520)
    parser.add_argument("--source-distance-mm", type=float, default=8000.0)
    parser.add_argument("--source-radius-mm", type=float, default=100.0)
    args = parser.parse_args()
    if args.n < 0:
        raise ValueError("--n must be non-negative")
    if args.sample_out is not None and args.n <= 0:
        raise ValueError("--n must be positive when --sample-out is set")
    if args.source_distance_mm <= 0.0 or args.source_radius_mm <= 0.0:
        raise ValueError("source distance/radius must be positive")
    if args.duration_s is not None and args.duration_s <= 0.0:
        raise ValueError("--duration-s must be positive")
    return args


def main() -> int:
    args = parse_args()
    components = parse_cosima_source(args.cosima_source, args.repo_root)
    config = write_config(args.out_config, args, components)
    if args.sample_out is not None:
        write_samples(args.sample_out, args, components, config)
    summary = {
        "components": len(components),
        "out_config": str(args.out_config),
        "sample_out": str(args.sample_out) if args.sample_out else None,
        "source_radius_mm": args.source_radius_mm,
        "source_distance_mm": args.source_distance_mm,
        "total_flux_cm2_s": config["total_flux_cm2_s"],
        "total_rate_hz_for_this_source_area": config["total_rate_hz_for_this_source_area"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
