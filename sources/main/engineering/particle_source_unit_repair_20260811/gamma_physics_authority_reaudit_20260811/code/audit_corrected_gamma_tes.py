#!/usr/bin/env python3
"""Event-level re-audit of corrected-keV prompt-gamma TES-positive events.

This is deliberately narrower than Step05.  It reads the validated 100k
instant gamma sample for each retained geometry, applies the frozen pixel
response, and reports transparent shield/pixel cut-flow diagnostics.  The
active-shield contracts are geometry-specific and exclude Kapton:

* Mass_model_511: only the retained CsI side, bottom, and top-annulus volumes.
* S3d-O8: only the three physical BGO crystal volumes.

Only TES-positive events are retained in the compressed event table.
"""

from __future__ import annotations

import csv
import gzip
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np


def find_root(path: Path) -> Path:
    for candidate in (path, *path.parents):
        if (candidate / ".git").exists() and (candidate / "AGENTS.md").is_file():
            return candidate
    raise RuntimeError("repository root not found")


THIS_FILE = Path(__file__).resolve()
ROOT = find_root(THIS_FILE.parent)
PACKAGE = THIS_FILE.parents[1]
DATA_DIR = PACKAGE / "data"
RUN_ROOT = ROOT / "runs/particle_source_unit_repair_20260811"
SUMMARY_JSON = DATA_DIR / "corrected_gamma_tes_authority_reaudit_summary.json"
EVENT_CSV_GZ = DATA_DIR / "corrected_gamma_tes_positive_events.csv.gz"

TES_RE = re.compile(r"^TP_L([0-5])_(\d+)$", re.IGNORECASE)
FWHM_KEV = 0.420
SIGMA_KEV = FWHM_KEV / 2.3548200450309493
PIXEL_THRESHOLD_KEV = 0.3
W2_KEV = (510.58, 511.42)
BROAD_KEV = (480.0, 550.0)
RESPONSE_SEEDS = {"mass_model_511": 2_605_110_102, "s3d_o8": 2_605_110_202}

MASS_CSI_PREFIXES = (
    "CsI_Side_Segment_",
    "CsI_Bottom_Quadrant_",
    "CsI_TopAnnulus_Segment_",
)
O8_TRUE_BGO_VOLUMES = frozenset(
    {
        "BGO_S3C_FullWrap_SideShell_WindowCut_40mm",
        "BGO_S3D_O8_FullWrap_BottomCap_30mm",
        "BGO_S3D_O8_FullWrap_TopAnnulus_10mm",
    }
)
O8_TRUE_PLASTIC_VOLUMES = frozenset(
    {
        "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm",
        "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm",
        "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm",
    }
)

THETA_EDGES = [
    0.000,
    25.842,
    36.870,
    45.573,
    53.130,
    60.000,
    66.422,
    72.542,
    78.463,
    84.261,
    90.000,
    95.739,
    101.537,
    107.458,
    113.578,
    120.000,
    126.870,
    134.427,
    143.130,
    154.158,
    180.000,
]
ENERGY_EDGES = [0, 100, 300, 480, 550, 1000, 3000, 10000, 30000, 100000, 300000, 1e99]
ENERGY_LABELS = [
    "<100 keV",
    "100-300 keV",
    "300-480 keV",
    "480-550 keV",
    "0.55-1 MeV",
    "1-3 MeV",
    "3-10 MeV",
    "10-30 MeV",
    "30-100 MeV",
    "100-300 MeV",
    ">=300 MeV",
]


def bin_index(value: float, edges: list[float]) -> int:
    for index in range(len(edges) - 1):
        if edges[index] <= value < edges[index + 1]:
            return index
    return len(edges) - 2


def mass_csi_active(volume: str) -> bool:
    return any(volume.startswith(prefix) for prefix in MASS_CSI_PREFIXES)


def o8_true_bgo(volume: str) -> bool:
    return volume in O8_TRUE_BGO_VOLUMES


def o8_true_plastic(volume: str) -> bool:
    return volume in O8_TRUE_PLASTIC_VOLUMES


def is_active_kapton(volume: str) -> bool:
    upper = volume.upper()
    return "KAPTON" in upper and ("ACTIVE" in upper or "BGO" in upper)


def category(volume: str) -> str:
    upper = volume.upper()
    if TES_RE.match(volume):
        return "tes"
    if mass_csi_active(volume):
        return "mass_csi"
    if o8_true_bgo(volume):
        return "o8_true_bgo"
    if o8_true_plastic(volume):
        return "o8_true_plastic"
    if is_active_kapton(volume):
        return "active_kapton_excluded"
    if "BPE" in upper or "BORATED" in upper or "POLYETHYLENE" in upper:
        return "bpe"
    if upper.startswith("PASSIVE_W_") or "TUNGSTEN" in upper:
        return "tungsten"
    if "OUTER_AL" in upper:
        return "outer_al"
    if any(
        token in upper
        for token in ("VACUUM_JACKET", "SHIELD_", "MAGSHIELD", "CU_50MK", "STILL_", "PLATE_300K")
    ):
        return "cryostat_shield"
    if any(token in upper for token in ("SUPPORT", "FLANGE", "PIPE", "CONDUIT", "ROD", "RING")):
        return "support_service"
    return "other"


def first_interaction_class(volume: str) -> str:
    upper = volume.upper()
    if volume == "BGO_S3C_FullWrap_SideShell_WindowCut_40mm":
        return "bgo_side_shell_material_with_aperture_cut"
    if volume == "Outer_Al_S3C_BGO_Mechanical_SideShell_WindowCut_3mm":
        return "outer_al_side_shell_material_with_aperture_cut"
    if "RECTCUT_WINDOW_BAND" in upper:
        return "window_band_material_not_open_aperture"
    if upper.startswith("WIN_"):
        return "window_material"
    if any(token in upper for token in ("PIPE", "CONDUIT", "SERVICE", "PORTFLANGE", "PUMPLINE")):
        return "service_port_or_pipe_material"
    if "BOTTOM" in upper or "BASEMOUNT" in upper:
        return "bottom_material"
    if "TOP" in upper:
        return "top_material"
    if "SIDE" in upper or "DETECTOR_BAY" in upper:
        return "side_material"
    if TES_RE.match(volume):
        return "tes_first_recorded_deposit"
    return "other_material"


def parse_key_values(parts: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for part in parts:
        if "=" in part:
            key, value = part.split("=", 1)
            result[key] = value
    return result


def new_event() -> dict[str, Any]:
    return {
        "id": None,
        "ed": None,
        "ec": None,
        "ns": None,
        "init": None,
        "pixel_e": defaultdict(float),
        "pixel_xyz": defaultdict(lambda: [0.0, 0.0, 0.0, 0.0]),
        "dep_category": defaultdict(float),
        "first_any": None,
        "first_primary": None,
        "tes_tracks": set(),
        "track_info": {},
        "ia": Counter(),
        "tes_by_particle": defaultdict(float),
        "tes_primary_track_keV": 0.0,
    }


def side_window_intersection(initial: dict[str, Any]) -> tuple[bool, float | None, float | None]:
    """Intersect the IA INIT ray with the frozen Step09 side-entry disk."""

    angle = math.radians(45.0)
    cosine = math.cos(angle)
    sine = math.sin(angle)

    def rotate_y(point: tuple[float, float, float]) -> tuple[float, float, float]:
        x, y, z = point
        return cosine * x + sine * z, y, -sine * x + cosine * z

    center = rotate_y((-13.1, 0.0, -5.2))
    normal = rotate_y((1.0, 0.0, 0.0))
    position = initial["position"]
    direction = initial["direction"]
    denominator = sum(direction[index] * normal[index] for index in range(3))
    if abs(denominator) < 1.0e-12:
        return False, None, None
    distance = sum((center[index] - position[index]) * normal[index] for index in range(3)) / denominator
    intersection = tuple(position[index] + distance * direction[index] for index in range(3))
    radial = math.sqrt(sum((intersection[index] - center[index]) ** 2 for index in range(3)))
    return distance >= 0.0 and radial <= 1.898, distance, radial


def trace_ancestry(event: dict[str, Any]) -> tuple[list[str], list[str], bool]:
    processes: set[str] = set()
    particles: set[str] = set()
    complete = True
    for start in event["tes_tracks"]:
        track = start
        seen: set[int] = set()
        for _ in range(64):
            if track in seen:
                complete = False
                break
            seen.add(track)
            info = event["track_info"].get(track)
            if info is None:
                complete = False
                break
            processes.add(info["creator_process"])
            particles.add(info["particle"])
            if track == 1 or info["parent_id"] == 0:
                break
            track = info["parent_id"]
        else:
            complete = False
    return sorted(processes), sorted(particles), complete


def parse_geometry(
    geometry: str,
    paths: list[Path],
    denominator: dict[str, list[int]],
) -> tuple[list[dict[str, Any]], int]:
    rng = np.random.default_rng(RESPONSE_SEEDS[geometry])
    rows: list[dict[str, Any]] = []
    primary_count = 0

    for path in paths:
        event = new_event()

        def flush() -> None:
            nonlocal event, primary_count
            if event["id"] is None:
                return
            primary_count += 1
            initial = event["init"]
            if initial is None:
                raise RuntimeError(f"{path}: event {event['id']} lacks IA INIT")
            energy_bin = bin_index(initial["energy_keV"], ENERGY_EDGES)
            theta_bin = bin_index(initial["theta_deg"], THETA_EDGES)
            denominator["energy"][energy_bin] += 1
            denominator["theta"][theta_bin] += 1

            raw_pixels = [(pixel, energy) for pixel, energy in sorted(event["pixel_e"].items()) if energy > 0.0]
            raw_total = math.fsum(energy for _, energy in raw_pixels)
            if raw_total <= 0.0:
                return
            measured_pixels: list[tuple[str, float]] = []
            for pixel, energy in raw_pixels:
                measured = float(energy + rng.normal(0.0, SIGMA_KEV))
                if measured >= PIXEL_THRESHOLD_KEV:
                    measured_pixels.append((pixel, measured))
            measured_total = math.fsum(energy for _, energy in measured_pixels)

            edge_pixels: list[str] = []
            for pixel, _ in raw_pixels:
                match = TES_RE.match(pixel)
                assert match is not None
                row_index, column_index = divmod(int(match.group(2)), 20)
                if row_index in (0, 19) or column_index in (0, 19):
                    edge_pixels.append(pixel)

            weight = math.fsum(values[3] for values in event["pixel_xyz"].values())
            centroid: list[float | None]
            line_miss: float | None
            line_along: float | None
            if weight > 0.0:
                centroid = [
                    math.fsum(values[index] for values in event["pixel_xyz"].values()) / weight
                    for index in range(3)
                ]
                displacement = [centroid[index] - initial["position"][index] for index in range(3)]
                line_along = math.fsum(
                    displacement[index] * initial["direction"][index] for index in range(3)
                )
                closest = [
                    initial["position"][index] + line_along * initial["direction"][index]
                    for index in range(3)
                ]
                line_miss = math.sqrt(math.fsum((centroid[index] - closest[index]) ** 2 for index in range(3)))
            else:
                centroid = [None, None, None]
                line_miss = None
                line_along = None

            intersects_window, window_distance, window_radial = side_window_intersection(initial)
            ancestry_processes, ancestry_particles, ancestry_complete = trace_ancestry(event)
            first = event["first_primary"] or event["first_any"]
            mass_csi_keV = event["dep_category"]["mass_csi"]
            o8_bgo_keV = event["dep_category"]["o8_true_bgo"]
            o8_plastic_keV = event["dep_category"]["o8_true_plastic"]
            active_shield_keV = mass_csi_keV if geometry == "mass_model_511" else o8_bgo_keV

            rows.append(
                {
                    "geometry": geometry,
                    "shard": path.name,
                    "local_id": event["id"],
                    "init_energy_keV": initial["energy_keV"],
                    "theta_deg": initial["theta_deg"],
                    "theta_bin": theta_bin,
                    "direction_hemisphere": "down" if initial["theta_deg"] < 90.0 else "up",
                    "dir_x": initial["direction"][0],
                    "dir_y": initial["direction"][1],
                    "dir_z": initial["direction"][2],
                    "tes_raw_keV": raw_total,
                    "tes_measured_keV": measured_total,
                    "raw_pixel_count": len(raw_pixels),
                    "measured_pixel_count": len(measured_pixels),
                    "pixels": ";".join(pixel for pixel, _ in raw_pixels),
                    "edge_pixel_count": len(edge_pixels),
                    "edge_pixels": ";".join(edge_pixels),
                    "active_shield_keV": active_shield_keV,
                    "active_shield_contract": "explicit_CsI_whitelist" if geometry == "mass_model_511" else "three_exact_BGO_crystals",
                    "mass_csi_keV": mass_csi_keV,
                    "o8_true_bgo_keV": o8_bgo_keV,
                    "o8_true_plastic_keV": o8_plastic_keV,
                    "excluded_active_kapton_keV": event["dep_category"]["active_kapton_excluded"],
                    "bpe_keV": event["dep_category"]["bpe"],
                    "tungsten_keV": event["dep_category"]["tungsten"],
                    "outer_al_keV": event["dep_category"]["outer_al"],
                    "cryostat_shield_keV": event["dep_category"]["cryostat_shield"],
                    "tes_primary_track_keV": event["tes_primary_track_keV"],
                    "tes_gamma_track_keV": event["tes_by_particle"]["gamma"],
                    "tes_electron_track_keV": event["tes_by_particle"]["e-"],
                    "tes_positron_track_keV": event["tes_by_particle"]["e+"],
                    "ed_header_keV": event["ed"],
                    "ec_header_keV": event["ec"],
                    "ns_header_keV": event["ns"],
                    "first_primary_volume": first["volume"] if first else "",
                    "first_primary_process": first["step_process"] if first else "",
                    "first_interaction_class": first_interaction_class(first["volume"]) if first else "no_recorded_deposit",
                    "straight_primary_intersects_signal_window": intersects_window,
                    "window_plane_distance_cm": window_distance,
                    "window_radial_cm": window_radial,
                    "primary_line_to_tes_centroid_miss_cm": line_miss,
                    "primary_line_tes_along_cm": line_along,
                    "ancestry_creator_processes": ";".join(ancestry_processes),
                    "ancestry_particles": ";".join(ancestry_particles),
                    "ancestry_complete": ancestry_complete,
                    "has_pair_ia": event["ia"]["PAIR"] > 0,
                    "has_annihilation_ia": event["ia"]["ANNI"] > 0,
                    "has_compton_ia": event["ia"]["COMP"] > 0,
                    "has_photoelectric_ia": event["ia"]["PHOT"] > 0,
                    "energy_bin": ENERGY_LABELS[energy_bin],
                }
            )

        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if line == "SE":
                    flush()
                    event = new_event()
                    continue
                if line.startswith("ID "):
                    event["id"] = int(line.split()[1])
                    continue
                if line.startswith("ED "):
                    event["ed"] = float(line.split()[1])
                    continue
                if line.startswith("EC "):
                    event["ec"] = float(line.split()[1])
                    continue
                if line.startswith("NS "):
                    event["ns"] = float(line.split()[1])
                    continue
                if line.startswith("IA INIT"):
                    parts = line.split(";")
                    direction = tuple(float(parts[index]) for index in (16, 17, 18))
                    direction_z = max(-1.0, min(1.0, direction[2]))
                    event["init"] = {
                        "position": tuple(float(parts[index]) for index in (4, 5, 6)),
                        "direction": direction,
                        "energy_keV": float(parts[22]),
                        "theta_deg": math.degrees(math.acos(direction_z)),
                    }
                    continue
                if line.startswith("IA "):
                    event["ia"][line.split()[1]] += 1
                    continue
                if not line.startswith("CC HIT "):
                    continue
                parts = line.split()
                volume = parts[2]
                values = parse_key_values(parts[3:])
                try:
                    energy = float(values["edep_keV"])
                    time = float(values["t"])
                    track_id = int(values["tid"])
                    parent_id = int(values["pid"])
                except (KeyError, ValueError):
                    continue
                record = {
                    "volume": volume,
                    "time": time,
                    "track_id": track_id,
                    "parent_id": parent_id,
                    "particle": values.get("sec", ""),
                    "step_process": values.get("sproc", ""),
                    "creator_process": values.get("cproc", ""),
                }
                event["dep_category"][category(volume)] += energy
                if event["first_any"] is None or time < event["first_any"]["time"]:
                    event["first_any"] = record
                if track_id == 1 and (
                    event["first_primary"] is None or time < event["first_primary"]["time"]
                ):
                    event["first_primary"] = record
                event["track_info"].setdefault(
                    track_id,
                    {
                        "parent_id": parent_id,
                        "particle": values.get("sec", ""),
                        "creator_process": values.get("cproc", ""),
                    },
                )
                if TES_RE.match(volume):
                    event["pixel_e"][volume] += energy
                    event["tes_tracks"].add(track_id)
                    event["tes_by_particle"][values.get("sec", "unknown")] += energy
                    if track_id == 1:
                        event["tes_primary_track_keV"] += energy
                    try:
                        x, y, z = (float(values[axis]) for axis in ("x", "y", "z"))
                    except (KeyError, ValueError):
                        x = y = z = 0.0
                    event["pixel_xyz"][volume][0] += energy * x
                    event["pixel_xyz"][volume][1] += energy * y
                    event["pixel_xyz"][volume][2] += energy * z
                    event["pixel_xyz"][volume][3] += energy
        flush()

    return rows, primary_count


def selected(rows: list[dict[str, Any]], window: str) -> list[dict[str, Any]]:
    if window == "tes_positive":
        return rows
    low, high = BROAD_KEV if window == "broad_480_550" else W2_KEV
    return [row for row in rows if low <= row["tes_measured_keV"] < high]


def build_cutflow(geometry: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for window in ("tes_positive", "broad_480_550", "w2_510p58_511p42"):
        base = selected(rows, window)
        record: dict[str, Any] = {
            "measured_energy_selection": len(base),
            "raw_pixel_multiplicity": dict(
                sorted(
                    Counter(
                        "3+" if row["raw_pixel_count"] >= 3 else str(row["raw_pixel_count"])
                        for row in base
                    ).items()
                )
            ),
            "events_with_any_edge_pixel": sum(row["edge_pixel_count"] > 0 for row in base),
        }
        for threshold in (50, 70, 80):
            shield_pass = [row for row in base if row["active_shield_keV"] < threshold]
            prefix = f"active_shield_lt_{threshold}_keV"
            record[prefix] = len(shield_pass)
            if geometry == "s3d_o8":
                post_veto = [row for row in shield_pass if row["o8_true_plastic_keV"] < 50.0]
                post_veto_key = f"{prefix}_and_plastic_lt_50_keV"
                record[post_veto_key] = len(post_veto)
            else:
                post_veto = shield_pass
                post_veto_key = prefix
            record[f"{post_veto_key}_and_single_pixel"] = sum(
                row["raw_pixel_count"] == 1 for row in post_veto
            )
            record[f"{post_veto_key}_and_no_edge_pixel"] = sum(
                row["edge_pixel_count"] == 0 for row in post_veto
            )
            record[f"{post_veto_key}_single_pixel_and_no_edge"] = sum(
                row["raw_pixel_count"] == 1 and row["edge_pixel_count"] == 0
                for row in post_veto
            )
        result[window] = record
    return result


def summarize_geometry(
    geometry: str,
    rows: list[dict[str, Any]],
    denominator: dict[str, list[int]],
) -> dict[str, Any]:
    energy_driver: list[dict[str, Any]] = []
    for index, label in enumerate(ENERGY_LABELS):
        subset = [row for row in rows if row["energy_bin"] == label]
        primaries = denominator["energy"][index]
        energy_driver.append(
            {
                "bin": label,
                "primaries": primaries,
                "tes_positive": len(subset),
                "tes_positive_fraction": len(subset) / primaries if primaries else None,
                "shield50_plastic50_pass": sum(
                    row["active_shield_keV"] < 50.0
                    and (geometry != "s3d_o8" or row["o8_true_plastic_keV"] < 50.0)
                    for row in subset
                ),
            }
        )
    theta_driver: list[dict[str, Any]] = []
    for index in range(20):
        subset = [row for row in rows if row["theta_bin"] == index]
        primaries = denominator["theta"][index]
        theta_driver.append(
            {
                "bin": index,
                "theta_deg": [THETA_EDGES[index], THETA_EDGES[index + 1]],
                "primaries": primaries,
                "tes_positive": len(subset),
                "tes_positive_fraction": len(subset) / primaries if primaries else None,
                "shield50_plastic50_pass": sum(
                    row["active_shield_keV"] < 50.0
                    and (geometry != "s3d_o8" or row["o8_true_plastic_keV"] < 50.0)
                    for row in subset
                ),
            }
        )
    return {
        "cutflow": build_cutflow(geometry, rows),
        "initial_energy_driver": energy_driver,
        "theta_driver": theta_driver,
        "direction_hemisphere": dict(Counter(row["direction_hemisphere"] for row in rows)),
        "first_interaction_class": dict(Counter(row["first_interaction_class"] for row in rows)),
        "first_primary_volume": dict(Counter(row["first_primary_volume"] for row in rows)),
        "straight_primary_intersects_signal_window": sum(
            row["straight_primary_intersects_signal_window"] for row in rows
        ),
        "direct_primary_track_tes_events": sum(row["tes_primary_track_keV"] > 0.0 for row in rows),
        "pair_present_events": sum(row["has_pair_ia"] for row in rows),
        "annihilation_present_events": sum(row["has_annihilation_ia"] for row in rows),
        "active_shield_positive_events": sum(row["active_shield_keV"] > 0.0 for row in rows),
        "o8_plastic_positive_events": sum(row["o8_true_plastic_keV"] > 0.0 for row in rows),
        "bpe_positive_events": sum(row["bpe_keV"] > 0.0 for row in rows),
        "ancestry_incomplete_events": sum(not row["ancestry_complete"] for row in rows),
    }


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    inputs = {
        "mass_model_511": sorted(
            (RUN_ROOT / "mass_model_511/instant_seven_family_batch0001_v1").glob(
                "Background_gamma_fullsphere20_rep01_part0[1-4].inc1.id1.sim.gz"
            )
        ),
        "s3d_o8": sorted(
            (RUN_ROOT / "s3d_o8/instant_seven_family_batch0001_v1").glob(
                "Background_gamma_fullsphere20_rep01_part0[1-4].inc1.id1.sim.gz"
            )
        ),
    }
    for geometry, paths in inputs.items():
        if len(paths) != 4:
            raise RuntimeError(f"{geometry}: expected four gamma shards, found {len(paths)}")

    denominators = {
        geometry: {"energy": [0] * len(ENERGY_LABELS), "theta": [0] * 20}
        for geometry in inputs
    }
    all_rows: dict[str, list[dict[str, Any]]] = {}
    primary_counts: dict[str, int] = {}
    for geometry, paths in inputs.items():
        all_rows[geometry], primary_counts[geometry] = parse_geometry(
            geometry, paths, denominators[geometry]
        )
        if primary_counts[geometry] != 100_000:
            raise RuntimeError(f"{geometry}: expected 100000 primaries, got {primary_counts[geometry]}")

    fieldnames = list(all_rows["mass_model_511"][0].keys())
    with gzip.open(EVENT_CSV_GZ, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for geometry in ("mass_model_511", "s3d_o8"):
            writer.writerows(all_rows[geometry])

    payload = {
        "status": "PASS__CORRECTED_GAMMA_TES_EVENT_LEVEL_REAUDIT",
        "authority_boundary": "DIAGNOSTIC_CUTFLOW__NOT_FULL_STEP05_OR_RATE_AUTHORITY",
        "scope": "corrected-keV instant gamma, 100000 primaries per geometry",
        "response": {
            "fwhm_keV": FWHM_KEV,
            "sigma_keV": SIGMA_KEV,
            "pixel_threshold_keV": PIXEL_THRESHOLD_KEV,
            "seeds": RESPONSE_SEEDS,
            "energy_windows_keV": {"broad": list(BROAD_KEV), "W2": list(W2_KEV)},
        },
        "active_shield_contracts": {
            "mass_model_511": {
                "kind": "explicit_CsI_whitelist",
                "allowed_prefixes": list(MASS_CSI_PREFIXES),
                "kapton_included": False,
            },
            "s3d_o8": {
                "kind": "three_exact_BGO_crystals",
                "allowed_volumes": sorted(O8_TRUE_BGO_VOLUMES),
                "plastic_volumes": sorted(O8_TRUE_PLASTIC_VOLUMES),
                "kapton_included": False,
            },
        },
        "edge_pixel_definition": {
            "kind": "diagnostic_proxy_not_authorized_Step05_cut",
            "definition": "20x20 pixel index with row or column in {0,19}",
        },
        "signal_window_ray_definition": {
            "source": "frozen Step09 side-entry disk",
            "local_center_cm": [-13.1, 0.0, -5.2],
            "rotation_y_deg": 45.0,
            "radius_cm": 1.898,
        },
        "inputs": {
            geometry: [path.relative_to(ROOT).as_posix() for path in paths]
            for geometry, paths in inputs.items()
        },
        "primary_counts": primary_counts,
        "tes_positive_event_counts": {geometry: len(rows) for geometry, rows in all_rows.items()},
        "denominators": denominators,
        "geometries": {
            geometry: summarize_geometry(geometry, all_rows[geometry], denominators[geometry])
            for geometry in ("mass_model_511", "s3d_o8")
        },
        "event_table": EVENT_CSV_GZ.relative_to(ROOT).as_posix(),
    }
    SUMMARY_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "summary": SUMMARY_JSON.relative_to(ROOT).as_posix(),
                "event_table": EVENT_CSV_GZ.relative_to(ROOT).as_posix(),
                "primary_counts": primary_counts,
                "tes_positive_event_counts": payload["tes_positive_event_counts"],
                "cutflow": {
                    geometry: payload["geometries"][geometry]["cutflow"]
                    for geometry in ("mass_model_511", "s3d_o8")
                },
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
