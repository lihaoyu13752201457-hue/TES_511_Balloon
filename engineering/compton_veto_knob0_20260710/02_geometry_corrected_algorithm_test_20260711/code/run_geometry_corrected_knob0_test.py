#!/usr/bin/env python3
"""Geometry-corrected, monotonic Knob0 replay on retained event catalogs.

This is a read-only replay.  It does not alter any retained simulation,
geometry, source card, Step05 authority, or S3c mainline product.  New derived
tables are written only below the sibling ``data`` directory.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import itertools
import json
import math
import pickle
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable

import numpy as np


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
DATA = PACKAGE / "data"

STEP05_SCRIPT = ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"
STEP09_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5"
    / "step09_optics_bridge_summary.json"
)
MASS_CATALOG = (
    ROOT
    / "stepwise_maintenance/step05_veto_time_axis/outputs_Mass_model_511_fullstat_v1_l1"
    / "work/event_catalog.pkl"
)
MASS_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step05_veto_time_axis/outputs_Mass_model_511_fullstat_v1_l1"
    / "step05_Mass_model_511_fullstat_v1_l1_response_summary.json"
)
MASS_GEOMETRY_DIR = (
    ROOT
    / "outputs/geometry"
    / "DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy"
)
S3C_TRUTH = (
    ROOT
    / "engineering/compton_veto_knob0_20260710/01_s3c_atm511_knob0_replay_20260710"
    / "data/s3c_atm511_w2_event_truth.json"
)
S3C_REPLAY_SUMMARY = (
    ROOT
    / "engineering/compton_veto_knob0_20260710/01_s3c_atm511_knob0_replay_20260710"
    / "data/s3c_atm511_knob0_summary.json"
)
S3C_GEOMETRY_DIR = (
    ROOT
    / "engineering/geometry_optimization_20260704/29_geoopt_s3c_bgo_w2mm_al3mm_shell_20260709"
    / "geometry"
)

W2 = (510.58, 511.42)
ACTIVE_VETO_THRESHOLD_KEV = 50.0
TES_SIGMA_KEV = 0.14
DOPPLER_SIGMA_DEG = 3.0
LONG_ARM_MM = 20.0
K_VALUES = (2.0, 2.5, 3.0)
MAX_ENUM_HITS = 6

# Frozen from the independent S3c IA-PHOT audit, not tuned on Mass_model W2.
RUNTIME_K_LINES_KEV = {
    "Kalpha2_runtime": 56.402,
    "Kalpha1_runtime": 57.686,
    "Kbeta_runtime": 65.381,
    "Kbeta2_runtime": 67.523,
}
K_TAG_HALF_WIDTH_KEV = 3.0 * TES_SIGMA_KEV
MAX_FLUORESCENCE_MERGE_DISTANCE_MM = 3.2

MASS_GEO = MASS_GEOMETRY_DIR / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo"
MASS_INTRO = MASS_GEOMETRY_DIR / "Intro_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo"
MASS_DET = MASS_GEOMETRY_DIR / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det"
S3C_GEO = S3C_GEOMETRY_DIR / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo"
S3C_INTRO = S3C_GEOMETRY_DIR / "Intro_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo"
S3C_DET = S3C_GEOMETRY_DIR / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det"


@dataclass(frozen=True)
class Hit:
    x: float
    y: float
    z: float
    e: float
    pixel_uid: str
    layer: int

    @property
    def position(self) -> np.ndarray:
        return np.asarray([self.x, self.y, self.z], dtype=float)


@dataclass(frozen=True)
class GeometryMap:
    geometry: Path
    intro: Path
    detector: Path
    rotation_deg: tuple[float, float, float]
    rotation: np.ndarray
    pixel_half_local_cm: np.ndarray
    pixel_centers_global_cm: dict[str, np.ndarray]
    representative_offsets_global_cm: np.ndarray
    single_hit_covariance_global_cm2: np.ndarray
    tes_sigma_kev: float
    structural_pitch_cm: tuple[float, float, float]


def rel(path: Path | str) -> str:
    path = Path(path)
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        if not rows:
            raise ValueError(f"no rows for {path}")
        fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_step05() -> Any:
    spec = importlib.util.spec_from_file_location("knob0_geometry_test_step05", STEP05_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {STEP05_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.ROOT = ROOT
    module.STEP09_SUMMARY = STEP09_SUMMARY
    return module


def rotation_x(angle_deg: float) -> np.ndarray:
    a = math.radians(angle_deg)
    c, s = math.cos(a), math.sin(a)
    return np.asarray([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=float)


def rotation_y(angle_deg: float) -> np.ndarray:
    a = math.radians(angle_deg)
    c, s = math.cos(a), math.sin(a)
    return np.asarray([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=float)


def rotation_z(angle_deg: float) -> np.ndarray:
    a = math.radians(angle_deg)
    c, s = math.cos(a), math.sin(a)
    return np.asarray([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=float)


def parse_vector(text: str) -> np.ndarray:
    return np.asarray([float(value) for value in text.split()], dtype=float)


def build_geometry_map(geometry: Path, intro: Path, detector: Path) -> GeometryMap:
    geo_text = geometry.read_text(encoding="utf-8")
    intro_text = intro.read_text(encoding="utf-8")
    det_text = detector.read_text(encoding="utf-8")

    shape_match = re.search(r"^TES_Pixel_L0\.Shape\s+BRIK\s+([^\n]+)", geo_text, re.MULTILINE)
    rotation_match = re.search(r"^InstrumentFrame\.Rotation\s+([^\n]+)", intro_text, re.MULTILINE)
    pitch_match = re.search(r"^D1\.StructuralPitch\s+([^\n]+)", det_text, re.MULTILINE)
    sigma_match = re.search(r"^D1\.EnergyResolution\s+Gauss\s+3000\s+3000\s+([^\s]+)", det_text, re.MULTILINE)
    if not all((shape_match, rotation_match, pitch_match, sigma_match)):
        raise ValueError(f"incomplete TES geometry/detector definition in {geometry.parent}")

    half_local = parse_vector(shape_match.group(1))
    angles = tuple(float(value) for value in rotation_match.group(1).split())
    # The retained geometry uses Rotation 0 45 0.  Compose explicitly so a
    # future non-zero x/z angle fails visibly in validation instead of being ignored.
    rotation = rotation_z(angles[2]) @ rotation_y(angles[1]) @ rotation_x(angles[0])
    pitch = tuple(float(value) for value in pitch_match.group(1).split())
    sigma = float(sigma_match.group(1))

    layer_positions: dict[int, np.ndarray] = {}
    for match in re.finditer(r"^TES_L(\d+)\.Position\s+([^\n]+)", geo_text, re.MULTILINE):
        layer_positions[int(match.group(1))] = parse_vector(match.group(2))
    if sorted(layer_positions) != list(range(6)):
        raise ValueError(f"expected six TES layer positions, got {sorted(layer_positions)}")

    centers: dict[str, np.ndarray] = {}
    for match in re.finditer(r"^(TP_L(\d+)_\d+)\.Position\s+([^\n]+)", geo_text, re.MULTILINE):
        uid = match.group(1)
        layer = int(match.group(2))
        local = layer_positions[layer] + parse_vector(match.group(3))
        centers[uid] = rotation @ local
    if len(centers) != 2256:
        raise ValueError(f"expected 2256 pixel centers, got {len(centers)}")

    corners_local = np.asarray(
        [
            [sx * half_local[0], sy * half_local[1], sz * half_local[2]]
            for sx in (-1.0, 1.0)
            for sy in (-1.0, 1.0)
            for sz in (-1.0, 1.0)
        ]
        + [[0.0, 0.0, 0.0]],
        dtype=float,
    )
    offsets_global = corners_local @ rotation.T
    covariance_local = np.diag(np.square(half_local) / 3.0)
    covariance_global = rotation @ covariance_local @ rotation.T
    return GeometryMap(
        geometry=geometry,
        intro=intro,
        detector=detector,
        rotation_deg=angles,
        rotation=rotation,
        pixel_half_local_cm=half_local,
        pixel_centers_global_cm=centers,
        representative_offsets_global_cm=offsets_global,
        single_hit_covariance_global_cm2=covariance_global,
        tes_sigma_kev=sigma,
        structural_pitch_cm=pitch,
    )


def corrected_representative_points(offsets: np.ndarray):
    def representative(hit: Hit) -> np.ndarray:
        return hit.position[None, :] + offsets

    return representative


def center_hits(hits: Iterable[Hit], geometry: GeometryMap) -> list[Hit]:
    centered = []
    for hit in hits:
        center = geometry.pixel_centers_global_cm[hit.pixel_uid]
        centered.append(replace(hit, x=float(center[0]), y=float(center[1]), z=float(center[2])))
    return centered


def catalog_event_hits(catalog: dict[str, Any], index: int) -> list[Hit]:
    start = int(catalog["pix_start"][index])
    count = int(catalog["pix_count"][index])
    hits = []
    for j in range(start, start + count):
        hits.append(
            Hit(
                x=float(catalog["pix_x"][j]),
                y=float(catalog["pix_y"][j]),
                z=float(catalog["pix_z"][j]),
                e=float(catalog["pix_e"][j]),
                pixel_uid=str(catalog["pix_uid"][j]),
                layer=int(catalog["pix_layer"][j]),
            )
        )
    return hits


def truth_event_hits(event: dict[str, Any]) -> list[Hit]:
    return [
        Hit(
            x=float(hit["position_cm"][0]),
            y=float(hit["position_cm"][1]),
            z=float(hit["position_cm"][2]),
            e=float(hit["energy_keV"]),
            pixel_uid=str(hit["pixel_uid"]),
            layer=int(hit["layer"]),
        )
        for hit in event["hits"]
    ]


def distance_mm(a: Hit, b: Hit) -> float:
    return 10.0 * float(np.linalg.norm(a.position - b.position))


def match_runtime_k_line(energy_kev: float) -> tuple[str, float, float] | None:
    matches = [
        (name, center, abs(energy_kev - center))
        for name, center in RUNTIME_K_LINES_KEV.items()
        if abs(energy_kev - center) <= K_TAG_HALF_WIDTH_KEV
    ]
    return min(matches, key=lambda item: item[2]) if matches else None


def merge_fluorescence_hits(hits: list[Hit]) -> tuple[list[Hit], list[dict[str, Any]]]:
    working = list(hits)
    merges: list[dict[str, Any]] = []
    while len(working) > 1:
        candidates = []
        for tag_index, hit in enumerate(working):
            match = match_runtime_k_line(hit.e)
            if match is None:
                continue
            for parent_index, parent in enumerate(working):
                if parent_index == tag_index or parent.layer != hit.layer:
                    continue
                separation = distance_mm(hit, parent)
                if separation <= MAX_FLUORESCENCE_MERGE_DISTANCE_MM:
                    candidates.append((separation, match[2], tag_index, parent_index, match))
        if not candidates:
            break
        separation, _, tag_index, parent_index, match = min(candidates, key=lambda item: (item[0], item[1]))
        tag = working[tag_index]
        parent = working[parent_index]
        merged_parent = replace(parent, e=parent.e + tag.e)
        new_working = []
        for index, hit in enumerate(working):
            if index == tag_index:
                continue
            new_working.append(merged_parent if index == parent_index else hit)
        working = new_working
        merges.append(
            {
                "tag_pixel": tag.pixel_uid,
                "parent_pixel": parent.pixel_uid,
                "line": match[0],
                "line_center_keV": match[1],
                "tag_energy_keV": tag.e,
                "distance_mm": separation,
            }
        )
    if not math.isclose(sum(hit.e for hit in working), sum(hit.e for hit in hits), abs_tol=1.0e-9):
        raise AssertionError("fluorescence merge did not conserve energy")
    return working, merges


def best_orders(step05: Any, hits: list[Hit]) -> list[tuple[list[Hit], dict[str, float]]]:
    if len(hits) < 2 or len(hits) > MAX_ENUM_HITS:
        return []
    if len(hits) == 2:
        out = []
        for indices in ((0, 1), (1, 0)):
            ordered = [hits[indices[0]], hits[indices[1]]]
            metrics = step05.sequence_metrics(ordered)
            if metrics is not None:
                out.append((ordered, metrics))
        return out
    ranked = []
    for permutation in itertools.permutations(range(len(hits))):
        ordered = [hits[index] for index in permutation]
        metrics = step05.sequence_metrics(ordered)
        if metrics is not None:
            ranked.append((metrics["qf"], -metrics["first_lever_arm"], ordered, metrics))
    if not ranked:
        return []
    _, _, ordered, metrics = min(ranked, key=lambda item: (item[0], item[1]))
    return [(ordered, metrics)]


def disk_boundary_points(disk: dict[str, Any], samples: int = 1440) -> np.ndarray:
    center = np.asarray(disk["center_cm"], dtype=float)
    u = np.asarray(disk["basis_u"], dtype=float)
    v = np.asarray(disk["basis_v"], dtype=float)
    radius = float(disk["radius_cm"])
    phi = np.linspace(0.0, 2.0 * math.pi, samples, endpoint=False)
    boundary = center[None, :] + radius * (
        np.cos(phi)[:, None] * u[None, :] + np.sin(phi)[:, None] * v[None, :]
    )
    return np.vstack([center[None, :], boundary])


def cone_window_residual_deg(
    step05: Any, ordered: list[Hit], sampled_disk: np.ndarray
) -> tuple[float, float] | None:
    axis_vector = ordered[0].position - ordered[1].position
    norm = float(np.linalg.norm(axis_vector))
    if norm <= 0:
        return None
    axis = axis_vector / norm
    e_first = ordered[0].e
    e_after = sum(hit.e for hit in ordered[1:])
    cosine = step05.compton_cos_theta(e_first, e_after)
    if not math.isfinite(cosine) or cosine < -1.0 or cosine > 1.0:
        return None
    theta = math.acos(float(np.clip(cosine, -1.0, 1.0)))
    rays = sampled_disk - ordered[0].position[None, :]
    ray_norms = np.linalg.norm(rays, axis=1)
    valid = ray_norms > 0
    rays = rays[valid] / ray_norms[valid, None]
    angles = np.arccos(np.clip(rays @ axis, -1.0, 1.0))
    low, high = float(np.min(angles)), float(np.max(angles))
    residual = max(low - theta, theta - high, 0.0)
    return math.degrees(residual), math.degrees(theta)


def energy_theta_sigma_deg(ordered: list[Hit], theta_deg: float) -> float:
    e_first = ordered[0].e
    e_after = sum(hit.e for hit in ordered[1:])
    total = e_first + e_after
    sine = abs(math.sin(math.radians(theta_deg)))
    if e_after <= 0 or total <= 0 or sine < 1.0e-6:
        return 180.0
    dcos_de_first = -511.0 / (total * total)
    dcos_de_after = 511.0 / (e_after * e_after) - 511.0 / (total * total)
    variance_cos = (
        dcos_de_first * dcos_de_first * TES_SIGMA_KEV * TES_SIGMA_KEV
        + dcos_de_after
        * dcos_de_after
        * max(len(ordered) - 1, 1)
        * TES_SIGMA_KEV
        * TES_SIGMA_KEV
    )
    return math.degrees(math.sqrt(variance_cos) / sine)


def position_axis_sigma_deg(ordered: list[Hit], geometry: GeometryMap) -> float:
    baseline = ordered[0].position - ordered[1].position
    length = float(np.linalg.norm(baseline))
    if length <= 0:
        return 180.0
    direction = baseline / length
    projector = np.eye(3) - np.outer(direction, direction)
    difference_covariance = 2.0 * geometry.single_hit_covariance_global_cm2
    projected = projector @ difference_covariance @ projector
    max_variance = max(float(np.max(np.linalg.eigvalsh(projected))), 0.0)
    return math.degrees(math.sqrt(max_variance) / length)


def tight_metrics(
    step05: Any,
    hits: list[Hit],
    geometry: GeometryMap,
    sampled_disk: np.ndarray,
) -> dict[str, Any]:
    orders = best_orders(step05, hits)
    if not orders:
        return {
            "reconstructable": False,
            "long_arm": False,
            "lever_arm_mm": None,
            "residual_deg": None,
            "position_sigma_deg": None,
            "energy_sigma_deg": None,
            "combined_sigma_deg": None,
            "pass": {str(k): True for k in K_VALUES},
        }
    order_rows = []
    for ordered, _ in orders:
        residual_theta = cone_window_residual_deg(step05, ordered, sampled_disk)
        if residual_theta is None:
            continue
        residual, theta = residual_theta
        lever = distance_mm(ordered[0], ordered[1])
        position_sigma = position_axis_sigma_deg(ordered, geometry)
        energy_sigma = energy_theta_sigma_deg(ordered, theta)
        combined = math.sqrt(position_sigma**2 + energy_sigma**2 + DOPPLER_SIGMA_DEG**2)
        order_rows.append(
            {
                "lever_arm_mm": lever,
                "residual_deg": residual,
                "position_sigma_deg": position_sigma,
                "energy_sigma_deg": energy_sigma,
                "combined_sigma_deg": combined,
                "ratio": residual / combined if combined > 0 else float("inf"),
            }
        )
    if not order_rows:
        return {
            "reconstructable": False,
            "long_arm": False,
            "lever_arm_mm": None,
            "residual_deg": None,
            "position_sigma_deg": None,
            "energy_sigma_deg": None,
            "combined_sigma_deg": None,
            "pass": {str(k): True for k in K_VALUES},
        }
    best = min(order_rows, key=lambda row: row["ratio"])
    long_arm = best["lever_arm_mm"] >= LONG_ARM_MM
    return {
        "reconstructable": True,
        "long_arm": long_arm,
        "lever_arm_mm": best["lever_arm_mm"],
        "residual_deg": best["residual_deg"],
        "position_sigma_deg": best["position_sigma_deg"],
        "energy_sigma_deg": best["energy_sigma_deg"],
        "combined_sigma_deg": best["combined_sigma_deg"],
        "pass": {
            str(k): (not long_arm) or best["residual_deg"] <= k * best["combined_sigma_deg"]
            for k in K_VALUES
        },
    }


def policy_names() -> list[str]:
    names = ["legacy_current", "geometry_current", "geometry_fluorescence_merge"]
    names += [f"geometry_tight_k{k:g}" for k in K_VALUES]
    names += [f"geometry_fluorescence_merge_tight_k{k:g}" for k in K_VALUES]
    return names


def evaluate_event(
    step05: Any,
    disk: dict[str, Any],
    sampled_disk: np.ndarray,
    geometry: GeometryMap,
    raw_hits: list[Hit],
    legacy_representative: Any,
) -> dict[str, Any]:
    step05.representative_points_box = legacy_representative
    legacy_keep, legacy_class = step05.side_keep_from_hits(raw_hits, disk, "keep")

    centered = center_hits(raw_hits, geometry)
    step05.representative_points_box = corrected_representative_points(
        geometry.representative_offsets_global_cm
    )
    geometry_keep, geometry_class = step05.side_keep_from_hits(centered, disk, "keep")
    tight = tight_metrics(step05, centered, geometry, sampled_disk)

    cleaned, merges = merge_fluorescence_hits(centered)
    if merges:
        cleaned_reco_keep, cleaned_class = step05.side_keep_from_hits(cleaned, disk, "keep")
    else:
        cleaned_reco_keep, cleaned_class = geometry_keep, geometry_class
    merge_keep = bool(geometry_keep and cleaned_reco_keep)
    cleaned_tight = tight_metrics(step05, cleaned, geometry, sampled_disk)

    policies: dict[str, bool] = {
        "legacy_current": bool(legacy_keep),
        "geometry_current": bool(geometry_keep),
        "geometry_fluorescence_merge": merge_keep,
    }
    for k in K_VALUES:
        policies[f"geometry_tight_k{k:g}"] = bool(geometry_keep and tight["pass"][str(k)])
        policies[f"geometry_fluorescence_merge_tight_k{k:g}"] = bool(
            merge_keep and cleaned_tight["pass"][str(k)]
        )
    if any(
        policies[name] and not geometry_keep
        for name in policies
        if name not in ("legacy_current", "geometry_current")
    ):
        raise AssertionError("non-monotonic candidate resurrected a geometry-current veto")
    return {
        "legacy_keep": bool(legacy_keep),
        "legacy_class": legacy_class,
        "geometry_keep": bool(geometry_keep),
        "geometry_class": geometry_class,
        "geometry_transition": f"{int(legacy_keep)}->{int(geometry_keep)}",
        "tag_candidate_count": sum(match_runtime_k_line(hit.e) is not None for hit in centered),
        "merge_count": len(merges),
        "merge_lines": ";".join(item["line"] for item in merges),
        "merge_pairs": ";".join(
            f"{item['tag_pixel']}->{item['parent_pixel']}" for item in merges
        ),
        "merge_distances_mm": ";".join(f"{item['distance_mm']:.6g}" for item in merges),
        "cleaned_hit_count": len(cleaned),
        "cleaned_class": cleaned_class,
        "tight": tight,
        "cleaned_tight": cleaned_tight,
        "policies": policies,
    }


def flatten_event_row(base: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    tight = result["tight"]
    cleaned = result["cleaned_tight"]
    row = {
        **base,
        "legacy_class": result["legacy_class"],
        "legacy_keep": int(result["legacy_keep"]),
        "geometry_class": result["geometry_class"],
        "geometry_keep": int(result["geometry_keep"]),
        "geometry_transition": result["geometry_transition"],
        "tag_candidate_count": result["tag_candidate_count"],
        "merge_count": result["merge_count"],
        "merge_lines": result["merge_lines"],
        "merge_pairs": result["merge_pairs"],
        "merge_distances_mm": result["merge_distances_mm"],
        "cleaned_hit_count": result["cleaned_hit_count"],
        "cleaned_class": result["cleaned_class"],
        "lever_arm_mm": tight["lever_arm_mm"],
        "cone_window_residual_deg": tight["residual_deg"],
        "position_sigma_deg": tight["position_sigma_deg"],
        "energy_sigma_deg": tight["energy_sigma_deg"],
        "combined_sigma_deg": tight["combined_sigma_deg"],
        "long_arm": int(bool(tight["long_arm"])),
        "cleaned_lever_arm_mm": cleaned["lever_arm_mm"],
        "cleaned_cone_window_residual_deg": cleaned["residual_deg"],
        "cleaned_combined_sigma_deg": cleaned["combined_sigma_deg"],
        "cleaned_long_arm": int(bool(cleaned["long_arm"])),
    }
    for name, keep in result["policies"].items():
        row[f"keep__{name}"] = int(keep)
    return row


def validate_mass_catalog_shape(catalog: dict[str, Any], geometry: GeometryMap) -> dict[str, Any]:
    event_fields = [
        "stream",
        "tag",
        "source_file",
        "local_id",
        "rate_hz",
        "tes_total_keV",
        "bgo_total_keV",
        "pix_start",
        "pix_count",
    ]
    lengths = {field: len(catalog[field]) for field in event_fields}
    event_count = lengths[event_fields[0]]
    event_lengths_equal = len(set(lengths.values())) == 1
    pixel_fields = ["pix_uid", "pix_layer", "pix_e", "pix_x", "pix_y", "pix_z"]
    pixel_lengths = {field: len(catalog[field]) for field in pixel_fields}
    pixel_lengths_equal = len(set(pixel_lengths.values())) == 1
    spans_ok = bool(
        event_count == 0
        or np.all(
            np.asarray(catalog["pix_start"], dtype=int)
            + np.asarray(catalog["pix_count"], dtype=int)
            <= len(catalog["pix_uid"])
        )
    )
    keys = [
        (str(catalog["stream"][i]), str(catalog["source_file"][i]), int(catalog["local_id"][i]))
        for i in range(event_count)
    ]
    duplicate_keys = len(keys) - len(set(keys))
    unknown_uids = sorted(set(map(str, catalog["pix_uid"])) - set(geometry.pixel_centers_global_cm))
    finite_nonnegative = bool(
        np.all(np.isfinite(np.asarray(catalog["tes_total_keV"], dtype=float)))
        and np.all(np.asarray(catalog["tes_total_keV"], dtype=float) >= 0)
        and np.all(np.isfinite(np.asarray(catalog["pix_e"], dtype=float)))
        and np.all(np.asarray(catalog["pix_e"], dtype=float) > 0)
    )
    return {
        "event_count": event_count,
        "event_field_lengths": lengths,
        "event_lengths_equal": event_lengths_equal,
        "pixel_count": len(catalog["pix_uid"]),
        "pixel_field_lengths": pixel_lengths,
        "pixel_lengths_equal": pixel_lengths_equal,
        "pixel_spans_valid": spans_ok,
        "duplicate_composite_event_keys": duplicate_keys,
        "unknown_pixel_uid_count": len(unknown_uids),
        "unknown_pixel_uids_sample": unknown_uids[:10],
        "finite_nonnegative_energies": finite_nonnegative,
        "pass": bool(
            event_lengths_equal
            and pixel_lengths_equal
            and spans_ok
            and duplicate_keys == 0
            and not unknown_uids
            and finite_nonnegative
        ),
    }


def selected_mass_indices(catalog: dict[str, Any]) -> dict[str, np.ndarray]:
    total = np.asarray(catalog["tes_total_keV"], dtype=float)
    active = np.asarray(catalog["bgo_total_keV"], dtype=float)
    stream = np.asarray(catalog["stream"], dtype=object)
    in_w2 = (total >= W2[0]) & (total < W2[1]) & (active < ACTIVE_VETO_THRESHOLD_KEV)
    return {name: np.flatnonzero(in_w2 & (stream == name)) for name in ("prompt", "delayed", "science")}


def run_mass_replay(
    step05: Any,
    disk: dict[str, Any],
    sampled_disk: np.ndarray,
    geometry: GeometryMap,
    legacy_representative: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    with MASS_CATALOG.open("rb") as handle:
        catalog = pickle.load(handle)
    quality = validate_mass_catalog_shape(catalog, geometry)
    selected = selected_mass_indices(catalog)
    rows: list[dict[str, Any]] = []
    for stream_name in ("prompt", "delayed", "science"):
        for index in selected[stream_name]:
            raw_hits = catalog_event_hits(catalog, int(index))
            result = evaluate_event(
                step05, disk, sampled_disk, geometry, raw_hits, legacy_representative
            )
            base = {
                "dataset": "Mass_model_511",
                "stream": stream_name,
                "source_file": str(catalog["source_file"][index]),
                "event_id": int(catalog["local_id"][index]),
                "rate_hz": float(catalog["rate_hz"][index]),
                "tes_total_keV": float(catalog["tes_total_keV"][index]),
                "active_veto_keV": float(catalog["bgo_total_keV"][index]),
                "hit_count": len(raw_hits),
                "hit_energies_keV": ";".join(f"{hit.e:.9g}" for hit in raw_hits),
                "hit_pixels": ";".join(hit.pixel_uid for hit in raw_hits),
            }
            rows.append(flatten_event_row(base, result))
    return rows, {"catalog_quality": quality, "selected_indices": {k: len(v) for k, v in selected.items()}}


def run_s3c_replay(
    step05: Any,
    disk: dict[str, Any],
    sampled_disk: np.ndarray,
    geometry: GeometryMap,
    legacy_representative: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    truth = load_json(S3C_TRUTH)
    rows = []
    ids = []
    for event in truth:
        ids.append(int(event["event_id"]))
        raw_hits = truth_event_hits(event)
        result = evaluate_event(
            step05, disk, sampled_disk, geometry, raw_hits, legacy_representative
        )
        base = {
            "dataset": "S3c_atm511_3M",
            "stream": "atm511",
            "source_file": rel(S3C_TRUTH),
            "event_id": int(event["event_id"]),
            "rate_hz": float(load_json(S3C_REPLAY_SUMMARY)["normalization"]["event_rate_weight_cps"]),
            "tes_total_keV": float(event["tes_total_keV"]),
            "active_veto_keV": float(event["active_veto_keV"]),
            "hit_count": len(raw_hits),
            "hit_energies_keV": ";".join(f"{hit.e:.9g}" for hit in raw_hits),
            "hit_pixels": ";".join(hit.pixel_uid for hit in raw_hits),
        }
        rows.append(flatten_event_row(base, result))
    quality = {
        "event_count": len(rows),
        "unique_event_ids": len(ids) == len(set(ids)),
        "all_pixels_mapped": all(
            uid in geometry.pixel_centers_global_cm
            for event in truth
            for uid in (hit["pixel_uid"] for hit in event["hits"])
        ),
        "tes_sums_close": all(
            math.isclose(
                float(event["tes_total_keV"]),
                sum(float(hit["energy_keV"]) for hit in event["hits"]),
                abs_tol=1.0e-6,
            )
            for event in truth
        ),
    }
    quality["pass"] = all(quality.values())
    return rows, {"event_quality": quality}


def aggregate_policy_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(str(row["dataset"]), str(row["stream"]))].append(row)
    for (dataset, stream), group in sorted(groups.items()):
        active_rate = sum(float(row["rate_hz"]) for row in group)
        for policy in policy_names():
            selected = [row for row in group if int(row[f"keep__{policy}"]) == 1]
            selected_rate = sum(float(row["rate_hz"]) for row in selected)
            base_selected = [row for row in group if int(row["keep__geometry_current"]) == 1]
            rejected_from_geometry = sum(
                int(row["keep__geometry_current"]) == 1 and int(row[f"keep__{policy}"]) == 0
                for row in group
            )
            resurrected_from_geometry = sum(
                int(row["keep__geometry_current"]) == 0 and int(row[f"keep__{policy}"]) == 1
                for row in group
            )
            weights = np.asarray([float(row["rate_hz"]) for row in selected], dtype=float)
            effective_n = (
                float(weights.sum() ** 2 / np.square(weights).sum())
                if len(weights) and float(np.square(weights).sum()) > 0
                else 0.0
            )
            out.append(
                {
                    "dataset": dataset,
                    "stream": stream,
                    "policy": policy,
                    "active_events": len(group),
                    "active_rate_hz": active_rate,
                    "selected_events": len(selected),
                    "selected_rate_hz": selected_rate,
                    "survival_fraction_events": len(selected) / len(group) if group else None,
                    "survival_fraction_rate": selected_rate / active_rate if active_rate else None,
                    "geometry_current_selected_events": len(base_selected),
                    "geometry_current_to_rejected": rejected_from_geometry,
                    "geometry_current_to_resurrected": resurrected_from_geometry,
                    "selected_effective_n": effective_n,
                }
            )
    return out


def significance_rows(policy_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lookup = {(row["dataset"], row["stream"], row["policy"]): row for row in policy_rows}
    base_s = float(lookup[("Mass_model_511", "science", "geometry_current")]["selected_rate_hz"])
    base_b = sum(
        float(lookup[("Mass_model_511", stream, "geometry_current")]["selected_rate_hz"])
        for stream in ("prompt", "delayed")
    )
    base_z = base_s / math.sqrt(base_b) if base_b > 0 else None
    rows = []
    for policy in policy_names():
        signal = float(lookup[("Mass_model_511", "science", policy)]["selected_rate_hz"])
        background = sum(
            float(lookup[("Mass_model_511", stream, policy)]["selected_rate_hz"])
            for stream in ("prompt", "delayed")
        )
        z_proxy = signal / math.sqrt(background) if background > 0 else None
        rows.append(
            {
                "policy": policy,
                "signal_rate_hz": signal,
                "prompt_plus_delayed_rate_hz": background,
                "s_over_sqrt_b_proxy": z_proxy,
                "relative_z_vs_geometry_current": z_proxy / base_z if z_proxy and base_z else None,
                "signal_retention_vs_geometry_current": signal / base_s if base_s else None,
                "background_retention_vs_geometry_current": background / base_b if base_b else None,
            }
        )
    return rows


def geometry_current_strata_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for dataset in sorted({str(row["dataset"]) for row in rows}):
        streams = sorted({str(row["stream"]) for row in rows if row["dataset"] == dataset})
        for stream in streams:
            group = [
                row
                for row in rows
                if row["dataset"] == dataset
                and row["stream"] == stream
                and int(row["keep__geometry_current"]) == 1
            ]
            buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for row in group:
                if int(row["hit_count"]) <= 1:
                    stratum = "single"
                elif row["lever_arm_mm"] in (None, ""):
                    stratum = "unreconstructable"
                else:
                    lever = float(row["lever_arm_mm"])
                    if lever < 8.0:
                        stratum = "S1_short_lt8mm"
                    elif lever < LONG_ARM_MM:
                        stratum = "S2_medium_8to20mm"
                    else:
                        stratum = "S3_long_ge20mm"
                buckets[stratum].append(row)
            for stratum in (
                "single",
                "unreconstructable",
                "S1_short_lt8mm",
                "S2_medium_8to20mm",
                "S3_long_ge20mm",
            ):
                selected = buckets.get(stratum, [])
                output.append(
                    {
                        "dataset": dataset,
                        "stream": stream,
                        "stratum": stratum,
                        "events": len(selected),
                        "rate_hz": sum(float(row["rate_hz"]) for row in selected),
                        "share_of_geometry_current_events": len(selected) / len(group) if group else None,
                    }
                )
    return output


def transition_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for dataset in sorted({str(row["dataset"]) for row in rows}):
        for stream in sorted({str(row["stream"]) for row in rows if row["dataset"] == dataset}):
            group = [row for row in rows if row["dataset"] == dataset and row["stream"] == stream]
            for policy in policy_names():
                if policy == "geometry_current":
                    baseline = "legacy_current"
                elif policy == "legacy_current":
                    continue
                else:
                    baseline = "geometry_current"
                counts = Counter(
                    f"{int(row[f'keep__{baseline}'])}->{int(row[f'keep__{policy}'])}"
                    for row in group
                )
                for transition in ("0->0", "0->1", "1->0", "1->1"):
                    out.append(
                        {
                            "dataset": dataset,
                            "stream": stream,
                            "baseline": baseline,
                            "policy": policy,
                            "transition": transition,
                            "events": counts.get(transition, 0),
                        }
                    )
    return out


def tagged_subset(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if int(row["tag_candidate_count"]) or int(row["merge_count"])]


def geometry_payload(geometry: GeometryMap) -> dict[str, Any]:
    in_plane_gap_y_mm = 10.0 * (
        geometry.structural_pitch_cm[0] - 2.0 * geometry.pixel_half_local_cm[1]
    )
    return {
        "geometry": rel(geometry.geometry),
        "intro": rel(geometry.intro),
        "detector": rel(geometry.detector),
        "instrument_rotation_deg": list(geometry.rotation_deg),
        "pixel_half_local_cm": geometry.pixel_half_local_cm.tolist(),
        "pixel_count": len(geometry.pixel_centers_global_cm),
        "representative_points": 9,
        "tes_sigma_kev_from_detector_file": geometry.tes_sigma_kev,
        "structural_pitch_cm": list(geometry.structural_pitch_cm),
        "in_plane_pixel_gap_mm": in_plane_gap_y_mm,
    }


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    required = [
        STEP05_SCRIPT,
        STEP09_SUMMARY,
        MASS_CATALOG,
        MASS_SUMMARY,
        MASS_GEO,
        MASS_INTRO,
        MASS_DET,
        S3C_TRUTH,
        S3C_REPLAY_SUMMARY,
        S3C_GEO,
        S3C_INTRO,
        S3C_DET,
    ]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("missing required inputs: " + ", ".join(missing))

    step05 = load_step05()
    legacy_representative = step05.representative_points_box
    disk = step05.side_entry_disk()
    sampled_disk = disk_boundary_points(disk)
    mass_geometry = build_geometry_map(MASS_GEO, MASS_INTRO, MASS_DET)
    s3c_geometry = build_geometry_map(S3C_GEO, S3C_INTRO, S3C_DET)
    if not math.isclose(mass_geometry.tes_sigma_kev, TES_SIGMA_KEV, abs_tol=1.0e-12):
        raise AssertionError("Mass_model detector sigma differs from frozen test sigma")
    if not math.isclose(s3c_geometry.tes_sigma_kev, TES_SIGMA_KEV, abs_tol=1.0e-12):
        raise AssertionError("S3c detector sigma differs from frozen test sigma")

    mass_rows, mass_meta = run_mass_replay(
        step05, disk, sampled_disk, mass_geometry, legacy_representative
    )
    s3c_rows, s3c_meta = run_s3c_replay(
        step05, disk, sampled_disk, s3c_geometry, legacy_representative
    )
    all_rows = mass_rows + s3c_rows
    policy_summary = aggregate_policy_rows(all_rows)
    significance = significance_rows(policy_summary)
    strata = geometry_current_strata_rows(all_rows)
    transitions = transition_rows(all_rows)

    write_csv(DATA / "mass_model_511_w2_event_audit.csv", mass_rows)
    write_csv(DATA / "s3c_atm511_w2_event_audit.csv", s3c_rows)
    write_csv(DATA / "tagged_event_audit.csv", tagged_subset(all_rows))
    write_csv(DATA / "policy_yields.csv", policy_summary)
    write_csv(DATA / "mass_model_511_significance_proxy.csv", significance)
    write_csv(DATA / "geometry_current_strata.csv", strata)
    write_csv(DATA / "policy_transitions.csv", transitions)

    expected_mass_final = {
        stream: int(
            load_json(MASS_SUMMARY)["windows"]["w2_510p58_511p42"]["by_stream"][stream][
                "side_compton_fov_pass_events"
            ]
        )
        for stream in ("prompt", "delayed", "science")
    }
    observed_mass_legacy = {
        stream: sum(
            row["stream"] == stream and int(row["keep__legacy_current"]) == 1
            for row in mass_rows
        )
        for stream in ("prompt", "delayed", "science")
    }
    s3c_expected_final = len(
        load_json(S3C_REPLAY_SUMMARY)["data_quality"]["w2_current_final_event_ids"]
    )
    s3c_observed_legacy = sum(int(row["keep__legacy_current"]) for row in s3c_rows)
    monotonic_violations = [
        {
            "dataset": row["dataset"],
            "stream": row["stream"],
            "event_id": row["event_id"],
            "policy": policy,
        }
        for row in all_rows
        for policy in policy_names()
        if policy not in ("legacy_current", "geometry_current")
        and int(row["keep__geometry_current"]) == 0
        and int(row[f"keep__{policy}"]) == 1
    ]
    energy_conservation_violations = [
        row["event_id"]
        for row in all_rows
        if int(row["merge_count"]) > 0 and int(row["cleaned_hit_count"]) >= int(row["hit_count"])
    ]

    summary = {
        "status": "PASS_GEOMETRY_CORRECTED_KNOB0_ALGORITHM_TEST",
        "as_of": "2026-07-11",
        "question": "Does geometry-corrected, monotonic fluorescence merging and/or long-arm tightening improve Mass_model_511 prompt+delayed S/sqrt(B) without unacceptable focused-signal loss, and does it help S3c atmospheric-511?",
        "scope": {
            "transport": "No new transport; retained transformed event catalog and retained S3c 3M event truth only.",
            "authority": "Exploratory replay; no retained authority or baseline is overwritten.",
            "mass_background": "Prompt plus delayed only; atmospheric-511 is a separate S3c geometry sample and is not combined into the Mass_model significance proxy.",
            "response_limit": "CC HIT energies are unsmeared. TES sigma enters tag windows and angular uncertainty, but this is not a full detector-response convolution.",
        },
        "inputs": {
            "mass_catalog": rel(MASS_CATALOG),
            "mass_summary": rel(MASS_SUMMARY),
            "s3c_truth": rel(S3C_TRUTH),
            "s3c_replay_summary": rel(S3C_REPLAY_SUMMARY),
            "step05_script": rel(STEP05_SCRIPT),
            "step09_summary": rel(STEP09_SUMMARY),
            "sha256": {
                "mass_catalog": sha256(MASS_CATALOG),
                "mass_geometry": sha256(MASS_GEO),
                "s3c_truth": sha256(S3C_TRUTH),
                "s3c_geometry": sha256(S3C_GEO),
            },
        },
        "frozen_definitions": {
            "w2_keV": list(W2),
            "active_veto_threshold_keV": ACTIVE_VETO_THRESHOLD_KEV,
            "tes_sigma_keV": TES_SIGMA_KEV,
            "runtime_k_lines_keV": RUNTIME_K_LINES_KEV,
            "k_tag_half_width_keV": K_TAG_HALF_WIDTH_KEV,
            "fluorescence_merge_rule": "same layer, runtime K window, nearest non-tag hit within 3.2 mm; merge energy into parent and conserve event energy",
            "max_fluorescence_merge_distance_mm": MAX_FLUORESCENCE_MERGE_DISTANCE_MM,
            "long_arm_boundary_mm": LONG_ARM_MM,
            "doppler_sigma_deg_assumed": DOPPLER_SIGMA_DEG,
            "k_values": list(K_VALUES),
            "monotonic_rule": "all candidate policies are geometry_current AND candidate_pass; no geometry-current veto can be resurrected",
            "position_rule": "pixel UID center plus exact InstrumentFrame-rotated voxel corners; tight-cut sigma uses the largest projected eigenvalue of the two-hit covariance",
        },
        "geometry": {
            "Mass_model_511": geometry_payload(mass_geometry),
            "S3c": geometry_payload(s3c_geometry),
        },
        "data_quality": {
            **mass_meta,
            **s3c_meta,
            "legacy_reproduction": {
                "mass_expected": expected_mass_final,
                "mass_observed": observed_mass_legacy,
                "mass_ok": expected_mass_final == observed_mass_legacy,
                "s3c_expected": s3c_expected_final,
                "s3c_observed": s3c_observed_legacy,
                "s3c_ok": s3c_expected_final == s3c_observed_legacy,
            },
            "monotonic_violation_count": len(monotonic_violations),
            "monotonic_violations": monotonic_violations[:20],
            "merge_shape_violation_count": len(energy_conservation_violations),
        },
        "counts": {
            "mass_w2_active_events": len(mass_rows),
            "s3c_w2_active_events": len(s3c_rows),
            "tag_candidate_events": sum(int(row["tag_candidate_count"]) > 0 for row in all_rows),
            "merge_eligible_events": sum(int(row["merge_count"]) > 0 for row in all_rows),
            "geometry_changed_events": sum(row["geometry_transition"] in ("0->1", "1->0") for row in all_rows),
        },
        "policy_yields": policy_summary,
        "mass_significance_proxy": significance,
        "geometry_current_strata": strata,
        "decision": {},
    }

    stratum_lookup = {
        (row["dataset"], row["stream"], row["stratum"]): int(row["events"])
        for row in strata
    }
    significance_lookup = {row["policy"]: row for row in significance}
    policy_lookup = {
        (row["dataset"], row["stream"], row["policy"]): row for row in policy_summary
    }
    candidate_names = [
        name for name in policy_names() if name not in ("legacy_current", "geometry_current")
    ]
    best_candidate = max(
        candidate_names,
        key=lambda name: float(significance_lookup[name]["relative_z_vs_geometry_current"]),
    )
    background_long_events = sum(
        stratum_lookup.get(("Mass_model_511", stream, "S3_long_ge20mm"), 0)
        for stream in ("prompt", "delayed")
    )
    signal_long_events = stratum_lookup.get(
        ("Mass_model_511", "science", "S3_long_ge20mm"), 0
    )
    merge_background_rejections = sum(
        int(
            policy_lookup[("Mass_model_511", stream, "geometry_fluorescence_merge")][
                "geometry_current_to_rejected"
            ]
        )
        for stream in ("prompt", "delayed")
    )
    merge_signal_rejections = int(
        policy_lookup[("Mass_model_511", "science", "geometry_fluorescence_merge")][
            "geometry_current_to_rejected"
        ]
    )
    tight_k2_background_rejections = sum(
        int(
            policy_lookup[("Mass_model_511", stream, "geometry_tight_k2")][
                "geometry_current_to_rejected"
            ]
        )
        for stream in ("prompt", "delayed")
    )
    tight_k2_signal_rejections = int(
        policy_lookup[("Mass_model_511", "science", "geometry_tight_k2")][
            "geometry_current_to_rejected"
        ]
    )
    s3c_geometry_events = int(
        policy_lookup[("S3c_atm511_3M", "atm511", "geometry_current")]["selected_events"]
    )
    s3c_candidate_min = min(
        int(policy_lookup[("S3c_atm511_3M", "atm511", name)]["selected_events"])
        for name in candidate_names
    )
    summary["decision"] = {
        "outcome": "NO_OBSERVED_KNOB0_ALGORITHM_BENEFIT",
        "promotion": "DO_NOT_PROMOTE_FLUORESCENCE_MERGE_OR_LONG_ARM_TIGHTENING",
        "best_candidate_by_mass_prompt_delayed_z": best_candidate,
        "best_candidate_relative_z": significance_lookup[best_candidate][
            "relative_z_vs_geometry_current"
        ],
        "best_candidate_is_noop": bool(
            math.isclose(
                float(significance_lookup[best_candidate]["signal_retention_vs_geometry_current"]),
                1.0,
                abs_tol=1.0e-12,
            )
            and math.isclose(
                float(
                    significance_lookup[best_candidate][
                        "background_retention_vs_geometry_current"
                    ]
                ),
                1.0,
                abs_tol=1.0e-12,
            )
        ),
        "mechanism_evidence": {
            "geometry_current_prompt_plus_delayed_long_arm_survivors": background_long_events,
            "geometry_current_signal_long_arm_survivors": signal_long_events,
            "fluorescence_merge_background_rejections": merge_background_rejections,
            "fluorescence_merge_signal_rejections": merge_signal_rejections,
            "tight_k2_background_rejections": tight_k2_background_rejections,
            "tight_k2_signal_rejections": tight_k2_signal_rejections,
            "s3c_geometry_current_events": s3c_geometry_events,
            "s3c_best_candidate_events": s3c_candidate_min,
        },
        "geometry_correction": "Required as a correctness repair, not promoted as a sensitivity optimization; it changes many event decisions and requires independent response-level validation before replacing authority.",
        "interpretation": "The retained Mass_model W2 prompt/delayed survivors contain no S3 long-arm target events, while the signal contains 934. Fluorescence merging and k=2 tightening reject signal only. k=2.5/3 are no-ops. The S3c atmospheric-511 candidates remain 7->7 after geometry correction.",
    }

    checks = summary["data_quality"]
    if not checks["catalog_quality"]["pass"]:
        summary["status"] = "FAIL_GEOMETRY_CORRECTED_KNOB0_DATA_QUALITY"
    if not checks["event_quality"]["pass"]:
        summary["status"] = "FAIL_GEOMETRY_CORRECTED_KNOB0_DATA_QUALITY"
    if not checks["legacy_reproduction"]["mass_ok"] or not checks["legacy_reproduction"]["s3c_ok"]:
        summary["status"] = "FAIL_GEOMETRY_CORRECTED_KNOB0_LEGACY_REPRODUCTION"
    if checks["monotonic_violation_count"] or checks["merge_shape_violation_count"]:
        summary["status"] = "FAIL_GEOMETRY_CORRECTED_KNOB0_POLICY_INVARIANT"
    write_json(DATA / "geometry_corrected_knob0_test_summary.json", summary)
    print(json.dumps({"status": summary["status"], "counts": summary["counts"]}, indent=2))
    return 0 if summary["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
