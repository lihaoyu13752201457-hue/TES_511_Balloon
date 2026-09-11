#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
SYSTEM_DIR = Path(__file__).resolve().parent
HC_KEV_A = 12.398419843320026
COPY_STRIDE = 100000


@dataclass(frozen=True)
class Vector3:
    x: float
    y: float
    z: float

    def __add__(self, other: Vector3) -> Vector3:
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vector3) -> Vector3:
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, value: float) -> Vector3:
        return Vector3(self.x * value, self.y * value, self.z * value)

    def dot(self, other: Vector3) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vector3) -> Vector3:
        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def norm(self) -> float:
        return math.sqrt(self.dot(self))

    def unit(self) -> Vector3:
        norm = self.norm()
        if norm <= 0.0:
            raise ValueError("zero vector")
        return self * (1.0 / norm)


@dataclass(frozen=True)
class RingSpec:
    ring_id: int
    design_energy_keV: float
    radius_mm: float
    n_tiles: int
    material: str
    h: int
    k: int
    l: int
    d_spacing_A: float
    tile_size_mm: float
    thickness_mm: float


@dataclass(frozen=True)
class EfficiencyRow:
    energy_keV: float
    theta_B_rad: float
    delta_theta_rad: float
    material: str
    h: int
    k: int
    l: int
    mosaic_fwhm_arcmin: float
    thickness_mm: float
    p_diff: float
    p_abs: float
    p_trans: float
    source: str


@dataclass(frozen=True)
class CrystalDecision:
    theta_local_rad: float
    theta_B_rad: float
    delta_theta_rad: float
    probs: EfficiencyRow
    plane_normal: Vector3
    ideal_out_dir: Vector3
    reflected_out_dir: Vector3
    reflected_minus_ideal_norm: float
    bragg_angle_from_plane_rad: float


@dataclass
class RingAccumulator:
    n: int = 0
    sampled_diff: int = 0
    sampled_abs: int = 0
    sampled_trans: int = 0
    expected_diff: float = 0.0
    expected_abs: float = 0.0
    expected_trans: float = 0.0
    sum_delta_theta_abs: float = 0.0
    max_reflection_vector_error: float = 0.0
    max_plane_minus_bragg_abs_rad: float = 0.0


class DarwinDynamicalModel:
    """Table-backed Darwin/Zachariasen probability model.

    This mirrors the role of Guan's model class: crystal physics lives here,
    while the process adapter only applies a Geant4 step decision.
    """

    def __init__(self, rows: Iterable[EfficiencyRow]) -> None:
        self.rows = sorted(
            rows,
            key=lambda row: (
                row.material,
                row.h,
                row.k,
                row.l,
                row.energy_keV,
                row.delta_theta_rad,
            ),
        )
        if not self.rows:
            raise ValueError("empty Darwin table")

    @classmethod
    def from_csv(cls, path: Path) -> DarwinDynamicalModel:
        rows: list[EfficiencyRow] = []
        with path.open(newline="", encoding="utf-8") as handle:
            for raw in csv.DictReader(handle):
                row = EfficiencyRow(
                    energy_keV=float(raw["E_keV"]),
                    theta_B_rad=float(raw["theta_B_rad"]),
                    delta_theta_rad=float(raw["delta_theta_rad"]),
                    material=raw["material"],
                    h=int(raw["h"]),
                    k=int(raw["k"]),
                    l=int(raw["l"]),
                    mosaic_fwhm_arcmin=float(raw["mosaic_fwhm_arcmin"]),
                    thickness_mm=float(raw["thickness_mm"]),
                    p_diff=float(raw["p_diff"]),
                    p_abs=float(raw["p_abs"]),
                    p_trans=float(raw["p_trans"]),
                    source=raw.get("source", ""),
                )
                validate_probabilities(row)
                rows.append(row)
        return cls(rows)

    def lookup(self, ring: RingSpec, delta_theta_rad: float) -> EfficiencyRow:
        candidates = [
            row
            for row in self.rows
            if row.material == ring.material
            and row.h == ring.h
            and row.k == ring.k
            and row.l == ring.l
        ]
        if not candidates:
            raise ValueError(f"no Darwin rows for {ring.material}({ring.h}{ring.k}{ring.l})")
        nearest_energy = min(candidates, key=lambda row: abs(row.energy_keV - ring.design_energy_keV)).energy_keV
        same_energy = [row for row in candidates if abs(row.energy_keV - nearest_energy) < 1e-9]
        same_energy.sort(key=lambda row: row.delta_theta_rad)
        if delta_theta_rad <= same_energy[0].delta_theta_rad:
            return same_energy[0]
        if delta_theta_rad >= same_energy[-1].delta_theta_rad:
            return same_energy[-1]
        for lower, upper in zip(same_energy, same_energy[1:]):
            if lower.delta_theta_rad <= delta_theta_rad <= upper.delta_theta_rad:
                return interpolate_efficiency(lower, upper, delta_theta_rad)
        return min(same_energy, key=lambda row: abs(row.delta_theta_rad - delta_theta_rad))


class GuanStyleCrystalBraggModel:
    """Crystal-physics model separated from Geant4 process bookkeeping."""

    def __init__(self, darwin: DarwinDynamicalModel, focal_length_mm: float) -> None:
        self.darwin = darwin
        self.focal_length_mm = focal_length_mm

    def evaluate(self, ring: RingSpec, position_mm: Vector3, in_dir: Vector3) -> CrystalDecision:
        theta_local = 0.5 * math.atan2(
            math.hypot(position_mm.x, position_mm.y),
            self.focal_length_mm - position_mm.z,
        )
        theta_B = bragg_angle_rad(ring.design_energy_keV, ring.d_spacing_A)
        delta_theta = theta_local - theta_B
        probs = self.darwin.lookup(ring, delta_theta)
        ideal_out = (Vector3(-position_mm.x, -position_mm.y, self.focal_length_mm - position_mm.z)).unit()
        plane_normal = (in_dir - ideal_out).unit()
        reflected = reflect(in_dir, plane_normal).unit()
        bragg_from_plane = math.asin(abs(in_dir.unit().dot(plane_normal)))
        return CrystalDecision(
            theta_local_rad=theta_local,
            theta_B_rad=theta_B,
            delta_theta_rad=delta_theta,
            probs=probs,
            plane_normal=plane_normal,
            ideal_out_dir=ideal_out,
            reflected_out_dir=reflected,
            reflected_minus_ideal_norm=(reflected - ideal_out).norm(),
            bragg_angle_from_plane_rad=bragg_from_plane,
        )


class Geant4ProcessAdapter:
    """Small adapter that mirrors a Geant4 PostStepDoIt branch application."""

    def __init__(self, model: GuanStyleCrystalBraggModel, rng: random.Random) -> None:
        self.model = model
        self.rng = rng

    def sample_stage(self, probs: EfficiencyRow) -> str:
        u = self.rng.random()
        if u < probs.p_abs:
            return "ABSORB"
        if u >= probs.p_abs + probs.p_diff:
            return "TRANSMIT"
        return "DIFFRACT"

    def diffracted_direction(self, decision: CrystalDecision) -> Vector3:
        sigma = fwhm_arcmin_to_sigma_rad(decision.probs.mosaic_fwhm_arcmin)
        return perturb_direction(decision.reflected_out_dir, sigma, self.rng)


def validate_probabilities(row: EfficiencyRow) -> None:
    if row.p_diff < 0.0 or row.p_abs < 0.0 or row.p_trans < 0.0:
        raise ValueError("negative Darwin probability")
    total = row.p_diff + row.p_abs + row.p_trans
    if abs(total - 1.0) > 1e-8:
        raise ValueError(f"Darwin probabilities do not sum to one: {total}")


def interpolate_efficiency(lower: EfficiencyRow, upper: EfficiencyRow, delta_theta_rad: float) -> EfficiencyRow:
    if upper.delta_theta_rad == lower.delta_theta_rad:
        return lower
    f = (delta_theta_rad - lower.delta_theta_rad) / (upper.delta_theta_rad - lower.delta_theta_rad)

    def lerp(a: float, b: float) -> float:
        return a + f * (b - a)

    p_diff = lerp(lower.p_diff, upper.p_diff)
    p_abs = lerp(lower.p_abs, upper.p_abs)
    p_trans = lerp(lower.p_trans, upper.p_trans)
    total = p_diff + p_abs + p_trans
    return EfficiencyRow(
        energy_keV=lower.energy_keV,
        theta_B_rad=lerp(lower.theta_B_rad, upper.theta_B_rad),
        delta_theta_rad=delta_theta_rad,
        material=lower.material,
        h=lower.h,
        k=lower.k,
        l=lower.l,
        mosaic_fwhm_arcmin=lerp(lower.mosaic_fwhm_arcmin, upper.mosaic_fwhm_arcmin),
        thickness_mm=lerp(lower.thickness_mm, upper.thickness_mm),
        p_diff=p_diff / total,
        p_abs=p_abs / total,
        p_trans=p_trans / total,
        source=lower.source + ":delta_interpolated",
    )


def bragg_angle_rad(energy_keV: float, d_spacing_A: float) -> float:
    arg = (HC_KEV_A / energy_keV) / (2.0 * d_spacing_A)
    if arg <= 0.0 or arg >= 1.0:
        raise ValueError("invalid Bragg argument")
    return math.asin(arg)


def reflect(in_dir: Vector3, plane_normal: Vector3) -> Vector3:
    k = in_dir.unit()
    n = plane_normal.unit()
    return k - n * (2.0 * k.dot(n))


def fwhm_arcmin_to_sigma_rad(fwhm_arcmin: float) -> float:
    return (fwhm_arcmin / 60.0) * math.pi / 180.0 / 2.355


def perturb_direction(direction: Vector3, sigma_rad: float, rng: random.Random) -> Vector3:
    base = direction.unit()
    if sigma_rad <= 0.0:
        return base
    reference = Vector3(0.0, 0.0, 1.0)
    e1 = base.cross(reference)
    if e1.norm() < 1e-12:
        e1 = base.cross(Vector3(1.0, 0.0, 0.0))
    e1 = e1.unit()
    e2 = base.cross(e1).unit()
    return (base + e1 * rng.gauss(0.0, sigma_rad) + e2 * rng.gauss(0.0, sigma_rad)).unit()


def plane_hit_mm(position: Vector3, direction: Vector3, focal_length_mm: float) -> Vector3:
    if abs(direction.z) < 1e-12:
        raise ValueError("direction is parallel to focal plane")
    t = (focal_length_mm - position.z) / direction.z
    return position + direction * t


def load_rings(path: Path, focal_length_mm: float) -> list[RingSpec]:
    rings: list[RingSpec] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            ring = RingSpec(
                ring_id=int(raw["ring_id"]),
                design_energy_keV=float(raw["design_energy_keV"]),
                radius_mm=float(raw["radius_mm"]),
                n_tiles=int(raw["n_tiles"]),
                material=raw["material"],
                h=int(raw["h"]),
                k=int(raw["k"]),
                l=int(raw["l"]),
                d_spacing_A=float(raw["d_spacing_A"]),
                tile_size_mm=float(raw["tile_size_mm"]),
                thickness_mm=float(raw["thickness_mm"]),
            )
            expected_radius = focal_length_mm * math.tan(2.0 * bragg_angle_rad(ring.design_energy_keV, ring.d_spacing_A))
            if abs(expected_radius - ring.radius_mm) > 0.2:
                raise ValueError(
                    f"ring {ring.ring_id} radius {ring.radius_mm} mm does not match Bragg radius {expected_radius} mm"
                )
            rings.append(ring)
    rings.sort(key=lambda row: row.ring_id)
    if not rings:
        raise ValueError("empty ring config")
    return rings


def ring_and_tile_for_event(rings: list[RingSpec], event_id: int) -> tuple[RingSpec, int]:
    idx = event_id % sum(row.n_tiles for row in rings)
    for ring in rings:
        if idx < ring.n_tiles:
            return ring, idx
        idx -= ring.n_tiles
    return rings[-1], rings[-1].n_tiles - 1


def event_position_mm(ring: RingSpec, tile_id: int, source_jitter_mm: float, rng: random.Random) -> Vector3:
    phi = 2.0 * math.pi * tile_id / ring.n_tiles
    dx = (rng.random() - 0.5) * source_jitter_mm
    dy = (rng.random() - 0.5) * source_jitter_mm
    return Vector3(
        ring.radius_mm * math.cos(phi) + dx,
        ring.radius_mm * math.sin(phi) + dy,
        -0.5 * ring.thickness_mm,
    )


def containment_diameter_cm(points: list[Vector3], fraction: float = 0.9) -> float:
    if not points:
        return 0.0
    radii_mm = sorted(math.hypot(point.x, point.y) for point in points)
    idx = min(len(radii_mm) - 1, max(0, math.ceil(fraction * len(radii_mm)) - 1))
    return 2.0 * radii_mm[idx] / 10.0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_barhoum_reference(path: Path) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    summary_path = path / "summary.json"
    ring_path = path / "per_ring_summary.csv"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else None
    if not ring_path.exists():
        return summary, []
    with ring_path.open(newline="", encoding="utf-8") as handle:
        return summary, list(csv.DictReader(handle))


def simulate(args: argparse.Namespace) -> dict[str, Any]:
    ring_config = resolve_path(args.ring_config)
    table_path = resolve_path(args.efficiency_table)
    barhoum_dir = resolve_path(args.barhoum_reference)
    out_dir = resolve_path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    rings = load_rings(ring_config, args.focal_mm)
    darwin = DarwinDynamicalModel.from_csv(table_path)
    model = GuanStyleCrystalBraggModel(darwin, args.focal_mm)
    rng = random.Random(args.seed)
    adapter = Geant4ProcessAdapter(model, rng)
    in_dir = Vector3(0.0, 0.0, 1.0)

    stats = {ring.ring_id: RingAccumulator() for ring in rings}
    hits: list[Vector3] = []
    max_probability_sum_error = 0.0
    for event_id in range(args.n):
        ring, tile_id = ring_and_tile_for_event(rings, event_id)
        position = event_position_mm(ring, tile_id, args.source_jitter_mm, rng)
        decision = model.evaluate(ring, position, in_dir)
        probs = decision.probs
        acc = stats[ring.ring_id]
        acc.n += 1
        acc.expected_diff += probs.p_diff
        acc.expected_abs += probs.p_abs
        acc.expected_trans += probs.p_trans
        acc.sum_delta_theta_abs += abs(decision.delta_theta_rad)
        acc.max_reflection_vector_error = max(acc.max_reflection_vector_error, decision.reflected_minus_ideal_norm)
        acc.max_plane_minus_bragg_abs_rad = max(
            acc.max_plane_minus_bragg_abs_rad,
            abs(decision.bragg_angle_from_plane_rad - decision.theta_B_rad),
        )
        max_probability_sum_error = max(max_probability_sum_error, abs(probs.p_diff + probs.p_abs + probs.p_trans - 1.0))
        stage = adapter.sample_stage(probs)
        if stage == "ABSORB":
            acc.sampled_abs += 1
        elif stage == "TRANSMIT":
            acc.sampled_trans += 1
        else:
            acc.sampled_diff += 1
            diffracted_dir = adapter.diffracted_direction(decision)
            hits.append(plane_hit_mm(position, diffracted_dir, args.focal_mm))

    per_ring = build_per_ring_summary(rings, stats)
    write_per_ring_csv(out_dir / "per_ring_summary.csv", per_ring)

    barhoum_summary, barhoum_rings = read_barhoum_reference(barhoum_dir)
    comparison = compare_to_barhoum(per_ring, barhoum_summary, barhoum_rings)
    write_comparison_csv(out_dir / "barhoum_comparison.csv", comparison["per_ring"])
    summary = build_summary(
        args=args,
        rings=rings,
        darwin=darwin,
        per_ring=per_ring,
        comparison=comparison,
        barhoum_summary=barhoum_summary,
        ring_config=ring_config,
        table_path=table_path,
        barhoum_dir=barhoum_dir,
        spot_d90_cm=containment_diameter_cm(hits),
        max_probability_sum_error=max_probability_sum_error,
    )
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(out_dir / "GEANT4_DARWIN_GUAN_VS_BARHOUM_REPORT.md", summary, per_ring, comparison)
    return summary


def build_per_ring_summary(rings: list[RingSpec], stats: dict[int, RingAccumulator]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ring in rings:
        acc = stats[ring.ring_id]
        n = float(acc.n)
        rows.append(
            {
                "ring_id": ring.ring_id,
                "design_energy_keV": ring.design_energy_keV,
                "radius_mm": ring.radius_mm,
                "n_events": acc.n,
                "sampled_n_diffracted": acc.sampled_diff,
                "sampled_n_absorbed": acc.sampled_abs,
                "sampled_n_transmitted": acc.sampled_trans,
                "sampled_diffraction_fraction": acc.sampled_diff / n if n else 0.0,
                "expected_diffraction_fraction": acc.expected_diff / n if n else 0.0,
                "expected_absorption_fraction": acc.expected_abs / n if n else 0.0,
                "expected_transmission_fraction": acc.expected_trans / n if n else 0.0,
                "mean_abs_delta_theta_rad": acc.sum_delta_theta_abs / n if n else 0.0,
                "max_reflection_vector_error": acc.max_reflection_vector_error,
                "max_plane_minus_bragg_abs_rad": acc.max_plane_minus_bragg_abs_rad,
            }
        )
    return rows


def compare_to_barhoum(
    per_ring: list[dict[str, Any]],
    barhoum_summary: dict[str, Any] | None,
    barhoum_rings: list[dict[str, str]],
) -> dict[str, Any]:
    by_ring = {int(row["ring_id"]): row for row in barhoum_rings}
    comparison_rows: list[dict[str, Any]] = []
    max_expected_delta = 0.0
    max_sampled_branch_delta = 0.0
    for row in per_ring:
        ref = by_ring.get(int(row["ring_id"]))
        if not ref:
            continue
        delta_mean_p = float(row["expected_diffraction_fraction"]) - float(ref["mean_p_diff"])
        delta_sampled = float(row["sampled_diffraction_fraction"]) - float(ref["diffraction_fraction"])
        max_expected_delta = max(max_expected_delta, abs(delta_mean_p))
        max_sampled_branch_delta = max(max_sampled_branch_delta, abs(delta_sampled))
        comparison_rows.append(
            {
                "ring_id": row["ring_id"],
                "design_energy_keV": row["design_energy_keV"],
                "guan_expected_p_diff": row["expected_diffraction_fraction"],
                "barhoum_mean_p_diff": float(ref["mean_p_diff"]),
                "delta_expected_minus_barhoum_mean_p_diff": delta_mean_p,
                "guan_sampled_diffraction_fraction": row["sampled_diffraction_fraction"],
                "barhoum_sampled_diffraction_fraction": float(ref["diffraction_fraction"]),
                "delta_sampled_fraction": delta_sampled,
            }
        )
    totals = {
        "max_abs_delta_expected_p_diff_vs_barhoum_mean_p_diff": max_expected_delta,
        "max_abs_delta_sampled_diffraction_fraction_vs_barhoum": max_sampled_branch_delta,
    }
    if barhoum_summary is not None:
        total_n = sum(float(row["n_events"]) for row in per_ring)
        total_expected_diff = sum(float(row["expected_diffraction_fraction"]) * float(row["n_events"]) for row in per_ring)
        total_sampled_diff = sum(float(row["sampled_n_diffracted"]) for row in per_ring)
        totals.update(
            {
                "guan_expected_diffraction_fraction": total_expected_diff / total_n,
                "guan_sampled_diffraction_fraction": total_sampled_diff / total_n,
                "barhoum_diffraction_fraction": float(barhoum_summary["diffraction_fraction"]),
                "delta_total_expected_diffraction_fraction": total_expected_diff / total_n
                - float(barhoum_summary["diffraction_fraction"]),
                "delta_total_sampled_diffraction_fraction": total_sampled_diff / total_n
                - float(barhoum_summary["diffraction_fraction"]),
            }
        )
    return {"totals": totals, "per_ring": comparison_rows}


def build_summary(
    *,
    args: argparse.Namespace,
    rings: list[RingSpec],
    darwin: DarwinDynamicalModel,
    per_ring: list[dict[str, Any]],
    comparison: dict[str, Any],
    barhoum_summary: dict[str, Any] | None,
    ring_config: Path,
    table_path: Path,
    barhoum_dir: Path,
    spot_d90_cm: float,
    max_probability_sum_error: float,
) -> dict[str, Any]:
    total_n = sum(float(row["n_events"]) for row in per_ring)
    total_expected_diff = sum(float(row["expected_diffraction_fraction"]) * float(row["n_events"]) for row in per_ring)
    total_expected_abs = sum(float(row["expected_absorption_fraction"]) * float(row["n_events"]) for row in per_ring)
    total_expected_trans = sum(float(row["expected_transmission_fraction"]) * float(row["n_events"]) for row in per_ring)
    total_sampled_diff = sum(int(row["sampled_n_diffracted"]) for row in per_ring)
    total_sampled_abs = sum(int(row["sampled_n_absorbed"]) for row in per_ring)
    total_sampled_trans = sum(int(row["sampled_n_transmitted"]) for row in per_ring)
    return {
        "system": "laue_darwin_guan_same_geometry",
        "implementation_style": "guan_style_model_process_split",
        "not_a_claim": "This is not the Guan/Reiazi source code and not a Geant4 toolkit EM category patch; it is a same-geometry closure package using their model/process separation idea.",
        "physics_backend": "Zachariasen/Darwin mosaic-crystal table",
        "same_geometry_as": str(ring_config.relative_to(ROOT) if ring_config.is_relative_to(ROOT) else ring_config),
        "efficiency_table": str(table_path.relative_to(ROOT) if table_path.is_relative_to(ROOT) else table_path),
        "barhoum_reference_dir": str(barhoum_dir.relative_to(ROOT) if barhoum_dir.is_relative_to(ROOT) else barhoum_dir),
        "ring_config_sha256": sha256_file(ring_config),
        "efficiency_table_sha256": sha256_file(table_path),
        "focal_length_mm": args.focal_mm,
        "source_jitter_mm": args.source_jitter_mm,
        "seed": args.seed,
        "n_events": args.n,
        "n_rings": len(rings),
        "n_tiles_total": sum(ring.n_tiles for ring in rings),
        "efficiency_table_rows": len(darwin.rows),
        "expected_n_diffracted": total_expected_diff,
        "expected_n_absorbed": total_expected_abs,
        "expected_n_transmitted": total_expected_trans,
        "expected_diffraction_fraction": total_expected_diff / total_n,
        "expected_absorption_fraction": total_expected_abs / total_n,
        "expected_transmission_fraction": total_expected_trans / total_n,
        "sampled_n_diffracted": total_sampled_diff,
        "sampled_n_absorbed": total_sampled_abs,
        "sampled_n_transmitted": total_sampled_trans,
        "sampled_diffraction_fraction": total_sampled_diff / total_n,
        "sampled_absorption_fraction": total_sampled_abs / total_n,
        "sampled_transmission_fraction": total_sampled_trans / total_n,
        "sampled_spot_d90_cm": spot_d90_cm,
        "max_probability_sum_error": max_probability_sum_error,
        "max_reflection_vector_error": max(float(row["max_reflection_vector_error"]) for row in per_ring),
        "max_plane_minus_bragg_abs_rad": max(float(row["max_plane_minus_bragg_abs_rad"]) for row in per_ring),
        "barhoum_reference": barhoum_summary,
        "comparison_to_barhoum": comparison["totals"],
        "source_links": {
            "barhoum_2022": "https://agenda.infn.it/event/21084/contributions/178539/",
            "guan_2023": "https://digitalcommons.library.tmc.edu/uthgsbs_docs/3758/",
            "reiazi_2025": "https://mdanderson.elsevierpure.com/en/publications/g4braggreflection-for-accurate-modeling-of-bragg-reflection-in-pe-2/",
            "geant4_processes": "https://geant4.web.cern.ch/documentation/dev/bfad_html/ForApplicationDevelopers/TrackingAndPhysics/physicsProcess.html",
        },
    }


def write_per_ring_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_comparison_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, summary: dict[str, Any], per_ring: list[dict[str, Any]], comparison: dict[str, Any]) -> None:
    cmp_totals = summary["comparison_to_barhoum"]
    lines = [
        "# GEANT4 Darwin/Guan-style vs Barhoum-style Laue Comparison",
        "",
        "## 1. Geant4 底层原理",
        "",
        "Geant4 的粒子输运不是把所有物理都写在 tracking loop 里，而是让 process manager 在每一步询问各个 physics process。"
        "离散过程通常通过 mean-free-path / interaction-length 竞争决定 step 限制，然后在 `PostStepDoIt` 改变 track、产生 secondary 或终止 track。",
        "",
        "Barhoum-style Laue lens advanced example 的核心是：用一个 forced discrete process 在 lens boundary 处接管光子，"
        "在 `PostStepDoIt` 中决定 `ABSORB / TRANSMIT / DIFFRACT`。这能快速把 Laue focusing 放入 Geant4 tracking，但晶体物理与 Geant4 step bookkeeping 容易混在同一个 process 类里。",
        "",
        "Guan/Reiazi-style 路线更接近 Geant4 EM process 的结构：process 类负责 Geant4 接口，Darwin/Zachariasen 或 dynamical diffraction model 类负责晶体物理。"
        "本目录复现的是这种分层思想，而不是声称移植了他们的源码。",
        "",
        "## 2. 本目录实现",
        "",
        "- 本 Python runner 是 legacy table-backed closure check：`DarwinDynamicalModel` 读取同一张 Zachariasen/Darwin mosaic-crystal 概率表，并按材料、hkl、能量、Bragg mismatch 插值。",
        "- 当前 02 的 compiled Geant4 executable 已把物理后端移到在线 Darwin-Hamilton mosaic 计算，不在 tracking 时读取 01 概率表。",
        "- `GuanStyleCrystalBraggModel`: 只负责晶体物理，计算局部 Bragg mismatch、概率、晶面法向和由 Bragg/specular geometry 得到的理想衍射方向。",
        "- `Geant4ProcessAdapter`: 只模拟 Geant4 `PostStepDoIt` 的应用层行为：根据概率抽样三分支，必要时给衍射方向叠加 mosaic angular spread。",
        "- 几何完全沿用 canonical Ge(111) 五环配置，目录内保留一份快照用于 hash/回归检查。",
        "",
        "## 3. 关键结果",
        "",
        f"- 事件数：`{summary['n_events']}`；环数：`{summary['n_rings']}`；总 tile 数：`{summary['n_tiles_total']}`。",
        f"- Guan-style expected diffraction fraction: `{summary['expected_diffraction_fraction']:.6f}`。",
        f"- Guan-style sampled diffraction fraction: `{summary['sampled_diffraction_fraction']:.6f}`。",
        f"- Barhoum-style Geant4 sampled diffraction fraction: `{cmp_totals.get('barhoum_diffraction_fraction', float('nan')):.6f}`。",
        f"- total expected delta vs Barhoum sampled fraction: `{cmp_totals.get('delta_total_expected_diffraction_fraction', float('nan')):.6f}`。",
        f"- max per-ring expected-p delta vs Barhoum mean-p: `{cmp_totals['max_abs_delta_expected_p_diff_vs_barhoum_mean_p_diff']:.6e}`。",
        f"- max reflection vector error: `{summary['max_reflection_vector_error']:.6e}`。",
        f"- max plane-Bragg residual: `{summary['max_plane_minus_bragg_abs_rad']:.6e}` rad。",
        f"- sampled focal D90 from mosaic angular spread: `{summary['sampled_spot_d90_cm']:.6f}` cm。",
        "",
        "## 4. Per-ring Comparison",
        "",
        "| ring | keV | Guan expected p_diff | Barhoum mean p_diff | delta |",
        "|---:|---:|---:|---:|---:|",
    ]
    by_cmp = {int(row["ring_id"]): row for row in comparison["per_ring"]}
    for row in per_ring:
        cmp_row = by_cmp.get(int(row["ring_id"]))
        if cmp_row is None:
            continue
        lines.append(
            f"| {row['ring_id']} | {float(row['design_energy_keV']):.0f} | "
            f"{float(cmp_row['guan_expected_p_diff']):.6f} | "
            f"{float(cmp_row['barhoum_mean_p_diff']):.6f} | "
            f"{float(cmp_row['delta_expected_minus_barhoum_mean_p_diff']):+.3e} |"
        )
    lines.extend(
        [
            "",
            "## 5. 信心边界",
            "",
            "高信心：同几何、model/process 分层、Bragg/specular 方向闭合、legacy table-backed runner 与现有 Barhoum-style mean probabilities 对齐。",
            "",
            "不能声称：这不是 Guan/Reiazi 源码移植；没有把 `G4CrystalBraggReflection` 或 `G4BraggReflection` 真正注册进 Geant4 EM category；"
            "也没有完成真实晶体批次、弯曲晶体、装调误差和 publication-grade same-lens validation。",
            "",
            "## 6. Sources",
            "",
            "- Barhoum 2022: https://agenda.infn.it/event/21084/contributions/178539/",
            "- Guan 2023: https://digitalcommons.library.tmc.edu/uthgsbs_docs/3758/",
            "- Reiazi 2025: https://mdanderson.elsevierpure.com/en/publications/g4braggreflection-for-accurate-modeling-of-bragg-reflection-in-pe-2/",
            "- Geant4 process model: https://geant4.web.cern.ch/documentation/dev/bfad_html/ForApplicationDevelopers/TrackingAndPhysics/physicsProcess.html",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run same-geometry Guan/Darwin-style Laue comparison against the Barhoum-style Geant4 output.")
    parser.add_argument("--n", type=int, default=100000)
    parser.add_argument("--seed", type=int, default=20260521)
    parser.add_argument("--focal-mm", type=float, default=8300.0)
    parser.add_argument("--source-jitter-mm", type=float, default=0.3)
    parser.add_argument("--ring-config", default="systems/laue_darwin_guan/geometry/ge111_480_550keV_multiring_darwin_config.csv")
    parser.add_argument("--efficiency-table", default="data/laue/Ge111_480_550keV_darwin_mosaic_table.csv")
    parser.add_argument("--barhoum-reference", default="runs/geant4_laue_multiring_darwin")
    parser.add_argument("--out", default="systems/laue_darwin_guan/results/same_geometry_comparison")
    args = parser.parse_args()
    if args.n <= 0:
        raise SystemExit("--n must be positive")
    summary = simulate(args)
    print(json.dumps({
        "out": str(resolve_path(args.out)),
        "expected_diffraction_fraction": summary["expected_diffraction_fraction"],
        "sampled_diffraction_fraction": summary["sampled_diffraction_fraction"],
        "barhoum_diffraction_fraction": summary["comparison_to_barhoum"].get("barhoum_diffraction_fraction"),
        "max_abs_delta_expected_p_diff": summary["comparison_to_barhoum"]["max_abs_delta_expected_p_diff_vs_barhoum_mean_p_diff"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
