#!/usr/bin/env python3
"""Audit S3d-O8 background retention under fixed-pixel fiducial cuts.

This is a deliberately narrow post-processing audit.  It streams the seven
authoritative delayed raw SIM files once, extracts only the 420 events already
selected by the corrected common response, and recovers the fixed TES pixel
centres from the ``HTsim`` type-2 records.  No transport is launched and no SIM
is copied.

The output separates four notions which must not be conflated:

* an event cut on the energy-weighted *fixed-pixel-centre* centroid;
* the historical event cut on the energy-deposit centroid;
* a deepest-layer cut;
* a diagnostic literal edge-channel mask which drops pixels outside the mask
  and then only rechecks W2 (it does not rerun Step05 topology).
"""

from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any


PACKAGE = Path(__file__).resolve().parents[1]
DATA = PACKAGE / "data"
DELAYED_LEDGER = DATA / "delayed_selected_event_ledger.csv"
PROMPT_EVENTS = DATA / "prompt_events.csv"
FROZEN_DELAYED = Path(
    "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/"
    "particle_source_unit_repair_20260811/s3d_o8_low_grammage_core_20260814/"
    "data/frozen_delayed_source_coordinates.csv"
)
MISSION = Path(
    "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/"
    "particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/"
    "outputs/06_mission"
)
EXTRACTOR = PACKAGE / "code/build_prompt_track_ledgers.py"

W2_LO_KEV = 510.58
W2_HI_KEV = 511.42
PIXEL_THRESHOLD_KEV = 0.3
SIGMA_KEV = 0.420 / 2.3548200450309493
AXIS_Y_CM = 0.0
AXIS_Z_CM = -5.2
FROZEN_RADIUS_CM = 1.35
FROZEN_LAYER_MAX = 3
HISTORICAL_FROZEN_PROMPT_COUNTS = 27807.0882801


def load_extractor() -> Any:
    spec = importlib.util.spec_from_file_location("s3d_o8_prompt_extractor", EXTRACTOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {EXTRACTOR}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty CSV: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def canonical_key(row: dict[str, str]) -> tuple[str, str, int]:
    return row["incident_family"], row["source_file"], int(row["delayed_local_event_id"])


def frozen_key(row: dict[str, str]) -> tuple[str, str, int]:
    return row["family"], row["source_file"], int(row["local_event_id"])


def stream_selected_events(
    path: Path,
    targets: dict[int, dict[str, str]],
    extractor: Any,
) -> tuple[dict[int, dict[str, Any]], str, int]:
    """Read one gzip once and retain only requested event CC/HTsim records."""
    found: dict[int, dict[str, Any]] = {}
    header_geometry = ""
    header_seed = -1
    current_id: int | None = None
    current: dict[str, Any] | None = None

    with gzip.open(path, "rt", encoding="utf-8", errors="strict") as handle:
        for line_no, raw in enumerate(handle, 1):
            line = raw.strip()
            if not header_geometry and line.startswith("Geometry "):
                header_geometry = line.split(maxsplit=1)[1].strip()
            elif header_seed < 0 and line.startswith("Seed "):
                header_seed = int(line.split()[1])
            if line.startswith("ID "):
                parts = line.split()
                current_id = int(parts[1])
                current = (
                    {"cc": [], "htsim": [], "id_second": int(parts[2]), "id_line": line_no}
                    if current_id in targets
                    else None
                )
                continue
            if line == "SE":
                if current is not None and current_id is not None:
                    if current_id in found:
                        raise RuntimeError(f"duplicate selected ID {current_id} in {path}")
                    found[current_id] = current
                current_id = None
                current = None
                continue
            if current is None or current_id is None:
                continue
            uid = f"delayed__{targets[current_id]['incident_family']}__ID{current_id}"
            if line.startswith("CC HIT "):
                current["cc"].append(
                    extractor.parse_cc(
                        line,
                        event_uid=uid,
                        source_file=str(path),
                        local_id=current_id,
                        line_no=line_no,
                        cc_seq=len(current["cc"]) + 1,
                    )
                )
            elif line.startswith("HTsim "):
                current["htsim"].append(
                    extractor.parse_htsim(
                        line,
                        event_uid=uid,
                        source_file=str(path),
                        local_id=current_id,
                        line_no=line_no,
                        htsim_seq=len(current["htsim"]) + 1,
                    )
                )

    missing = sorted(set(targets) - set(found))
    if missing:
        raise RuntimeError(f"{path}: missing {len(missing)} selected IDs, first={missing[:5]}")
    if not header_geometry or header_seed < 0:
        raise RuntimeError(f"{path}: missing Geometry/Seed header")
    return found, header_geometry, header_seed


def weighted_centroid(
    pixels: list[dict[str, Any]],
    xyz_names: tuple[str, str, str],
) -> tuple[float, float, float, float]:
    total = math.fsum(float(pixel["measured_keV"]) for pixel in pixels)
    xyz = tuple(
        math.fsum(float(pixel["measured_keV"]) * float(pixel[name]) for pixel in pixels) / total
        for name in xyz_names
    )
    return xyz[0], xyz[1], xyz[2], math.hypot(xyz[1] - AXIS_Y_CM, xyz[2] - AXIS_Z_CM)


def match_fixed_centres(
    ht_rows: list[dict[str, Any]], pixels: dict[str, dict[str, Any]]
) -> None:
    """Match TES HTsim centres after coalescing repeated records per centre.

    Delayed decays can emit several HTsim type-2 records for one TES pixel.
    The prompt-only helper assumes one record per pixel, so the general replay
    first sums records sharing the same fixed centre and then matches by energy.
    """
    grouped: dict[tuple[float, float, float], dict[str, float]] = {}
    for row in ht_rows:
        if int(row["detector_type"]) != 2:
            continue
        key = (
            float(row["world_x_cm"]),
            float(row["world_y_cm"]),
            float(row["world_z_cm"]),
        )
        target = grouped.setdefault(
            key,
            {
                "energy_keV": 0.0,
                "if_x": float(row["IF_x_cm"]),
                "if_y": float(row["IF_y_cm"]),
                "if_z": float(row["IF_z_cm"]),
            },
        )
        target["energy_keV"] += float(row["energy_keV"])
    if len(grouped) < len(pixels):
        raise RuntimeError(
            f"too few type-2 HTsim centres for TES pixels: {len(grouped)} < {len(pixels)}"
        )
    unmatched_centres = set(grouped)
    # Match each explicit TP_* pixel to the type-2 record with the same summed
    # energy.  Other detector systems also emit type-2 HTsim records, so extra
    # centres are expected and are ignored after the energy/spatial match.
    for uid in sorted(pixels):
        pixel = pixels[uid]
        centre = min(
            unmatched_centres,
            key=lambda key: (
                abs(float(pixel["raw_keV"]) - grouped[key]["energy_keV"]),
                (key[0] - float(pixel["deposit_centroid_world_x_cm"])) ** 2
                + (key[1] - float(pixel["deposit_centroid_world_y_cm"])) ** 2
                + (key[2] - float(pixel["deposit_centroid_world_z_cm"])) ** 2,
                key,
            ),
        )
        ht = grouped[centre]
        residual = float(pixel["raw_keV"]) - ht["energy_keV"]
        if abs(residual) > 1.0e-3:
            raise RuntimeError(f"HTsim/pixel aggregate energy mismatch for {uid}: {residual}")
        pixel.update(
            {
                "pixel_center_world_x_cm": centre[0],
                "pixel_center_world_y_cm": centre[1],
                "pixel_center_world_z_cm": centre[2],
                "pixel_center_IF_x_cm": ht["if_x"],
                "pixel_center_IF_y_cm": ht["if_y"],
                "pixel_center_IF_z_cm": ht["if_z"],
            }
        )
        unmatched_centres.remove(centre)


def recover_delayed_events(rows: list[dict[str, str]], extractor: Any) -> list[dict[str, Any]]:
    by_path: defaultdict[str, dict[int, dict[str, str]]] = defaultdict(dict)
    for row in rows:
        event_id = int(row["delayed_local_event_id"])
        if event_id in by_path[row["source_file"]]:
            raise RuntimeError(f"duplicate event ID within SIM: {row['source_file']} ID={event_id}")
        by_path[row["source_file"]][event_id] = row

    recovered: list[dict[str, Any]] = []
    for index, (source_file, targets) in enumerate(sorted(by_path.items()), 1):
        path = Path(source_file)
        if not path.is_file():
            raise FileNotFoundError(path)
        raw_events, geometry, seed = stream_selected_events(path, targets, extractor)
        for event_id, raw in raw_events.items():
            row = targets[event_id]
            expected_seed = int(row["transport_seed"])
            if seed != expected_seed:
                raise RuntimeError(f"{path}: seed {seed} != ledger {expected_seed}")
            if raw["id_second"] != event_id:
                raise RuntimeError(f"{path}: ID columns differ for {event_id}")

            pixels_by_uid = extractor.pixel_groups(raw["cc"])
            try:
                match_fixed_centres(raw["htsim"], pixels_by_uid)
            except RuntimeError as exc:
                raise RuntimeError(f"{row['incident_family']} ID={event_id}: {exc}") from exc
            measured: list[dict[str, Any]] = []
            family = row["incident_family"]
            for uid in sorted(pixels_by_uid):
                pixel = pixels_by_uid[uid]
                normal = extractor.keyed_standard_normal(
                    "s3d_o8",
                    "delayed",
                    family,
                    row["batch_id"],
                    expected_seed,
                    row["job_name"],
                    event_id,
                    uid,
                )
                value = float(pixel["raw_keV"]) + SIGMA_KEV * normal
                pixel["measured_keV"] = value
                if value >= PIXEL_THRESHOLD_KEV:
                    measured.append(pixel)
            if not measured:
                raise RuntimeError(f"selected event has no measured pixels: {family} ID={event_id}")
            measured_total = math.fsum(float(pixel["measured_keV"]) for pixel in measured)
            authority_total = float(row["measured_total_keV"])
            if abs(measured_total - authority_total) > 1.0e-9:
                raise RuntimeError(
                    f"{family} ID={event_id}: measured total residual "
                    f"{measured_total-authority_total:.12g} keV"
                )
            if len(measured) != int(row["measured_multiplicity"]):
                raise RuntimeError(f"{family} ID={event_id}: measured multiplicity differs")

            fixed = weighted_centroid(
                measured,
                ("pixel_center_IF_x_cm", "pixel_center_IF_y_cm", "pixel_center_IF_z_cm"),
            )
            # Common-response PSF/fiducial replay used energy-deposit centroids,
            # transformed into the instrument frame only after event averaging.
            deposit_world = weighted_centroid(
                measured,
                (
                    "deposit_centroid_world_x_cm",
                    "deposit_centroid_world_y_cm",
                    "deposit_centroid_world_z_cm",
                ),
            )
            dx, dy, dz = extractor.world_to_instrument(*deposit_world[:3])
            deposit_radius = math.hypot(dy - AXIS_Y_CM, dz - AXIS_Z_CM)
            pixel_radii = [
                math.hypot(
                    float(pixel["pixel_center_IF_y_cm"]) - AXIS_Y_CM,
                    float(pixel["pixel_center_IF_z_cm"]) - AXIS_Z_CM,
                )
                for pixel in measured
            ]
            recovered.append(
                {
                    "stream": "delayed",
                    "family": family,
                    "source_file": source_file,
                    "local_event_id": event_id,
                    "batch_id": row["batch_id"],
                    "job_name": row["job_name"],
                    "transport_seed": expected_seed,
                    "event_weight_cps": float(row["event_weight_cps"]),
                    "source_parent_ZA": row["source_parent_ZA"],
                    "measured_total_keV": measured_total,
                    "measured_multiplicity": len(measured),
                    "fixed_centroid_r_cm": fixed[3],
                    "deposit_centroid_r_cm": deposit_radius,
                    "max_fixed_pixel_r_cm": max(pixel_radii),
                    "deepest_layer": max(int(pixel["layer"]) for pixel in measured),
                    "pixels": [
                        {
                            "uid": str(pixel["pixel_uid"]),
                            "layer": int(pixel["layer"]),
                            "measured_keV": float(pixel["measured_keV"]),
                            "fixed_r_cm": radius,
                        }
                        for pixel, radius in zip(measured, pixel_radii)
                    ],
                    "sim_header_geometry": geometry,
                }
            )
        print(
            f"raw delayed scan {index}/{len(by_path)}: {targets[next(iter(targets))]['incident_family']} "
            f"selected={len(targets)}",
            flush=True,
        )
    recovered.sort(key=lambda row: (row["family"], row["source_file"], row["local_event_id"]))
    return recovered


def recover_prompt_events(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    recovered = []
    for row in rows:
        if row["step05_pass"].lower() != "true":
            continue
        recovered.append(
            {
                "stream": "prompt",
                "family": row["family"],
                "source_file": row["source_file"],
                "local_event_id": int(row["local_event_id"]),
                "batch_id": row["batch_id"],
                "job_name": row["job_name"],
                "transport_seed": int(row["transport_seed"]),
                "event_weight_cps": float(row["event_weight_cps"]),
                "source_parent_ZA": "",
                "measured_total_keV": float(row["tes_measured_total_keV"]),
                "measured_multiplicity": int(row["tes_measured_pixel_count"]),
                "fixed_centroid_r_cm": float(row["fixed_pixel_centroid_r_cm"]),
                # Deposit-centroid replay is not needed for the frozen authority;
                # both Step05 prompt survivors are single-pixel events.
                "deposit_centroid_r_cm": None,
                "max_fixed_pixel_r_cm": float(row["fixed_pixel_centroid_r_cm"]),
                "deepest_layer": int(row["deepest_measured_layer"]),
                "pixels": [
                    {
                        "uid": "single_measured_pixel",
                        "layer": int(row["deepest_measured_layer"]),
                        "measured_keV": float(row["tes_measured_total_keV"]),
                        "fixed_r_cm": float(row["fixed_pixel_centroid_r_cm"]),
                    }
                ],
                "sim_header_geometry": row["sim_header_geometry"],
            }
        )
    return recovered


def mission_quanta(
    events: list[dict[str, Any]],
) -> tuple[dict[tuple[str, str], float], float]:
    timeline = [row for row in read_csv(MISSION / "mission_timeline.csv") if row["geometry"] == "S3d_O8"]
    time_ids = {row["time_bin_id"] for row in timeline}
    keys = {(event["family"], str(event["source_parent_ZA"])) for event in events}
    scale: dict[tuple[str, str, str], float] = {}
    for row in read_csv(MISSION / "family_parent_activity_by_time.csv"):
        if row["geometry"] != "S3d_O8" or row["time_bin_id"] not in time_ids:
            continue
        key = (row["incident_family"], row["source_parent_ZA"])
        if key in keys:
            scale[(row["time_bin_id"], *key)] = float(
                row["activity_scale_to_constant_environment_day15_inventory"]
            )
    factors: defaultdict[tuple[str, str], float] = defaultdict(float)
    for time in timeline:
        live = float(time["accidental_live_factor"]) * float(time["trajectory_quadrature_weight_s"])
        for key in keys:
            factors[key] += live * scale.get((time["time_bin_id"], *key), 0.0)
    prompt_total = math.fsum(
        float(time["prompt_final_cps_noacc"])
        * float(time["accidental_live_factor"])
        * float(time["trajectory_quadrature_weight_s"])
        for time in timeline
    )
    # The corrected S3d-O8 prompt authority contains two equal-weight gamma
    # roots, so the matched 20-day prompt quantum is exactly half the mission
    # stage's integrated prompt total.
    return dict(factors), prompt_total / 2.0


def keep_event(event: dict[str, Any], kind: str, radius: float, layer: int) -> bool:
    if kind == "fixed_centroid":
        return float(event["fixed_centroid_r_cm"]) <= radius and int(event["deepest_layer"]) <= layer
    if kind == "deposit_centroid":
        value = event["deposit_centroid_r_cm"]
        if value is None:
            value = event["fixed_centroid_r_cm"]
        return float(value) <= radius and int(event["deepest_layer"]) <= layer
    if kind == "all_fixed_pixels":
        return float(event["max_fixed_pixel_r_cm"]) <= radius and int(event["deepest_layer"]) <= layer
    if kind == "literal_channel_mask_w2_only":
        retained = [
            pixel
            for pixel in event["pixels"]
            if float(pixel["fixed_r_cm"]) <= radius and int(pixel["layer"]) <= layer
        ]
        total = math.fsum(float(pixel["measured_keV"]) for pixel in retained)
        return W2_LO_KEV <= total < W2_HI_KEV
    raise ValueError(kind)


def aggregate(
    events: list[dict[str, Any]],
    keep: list[bool],
    mission_factors: dict[tuple[str, str], float],
    prompt_mission_quantum: float,
) -> dict[str, Any]:
    retained = [event for event, passed in zip(events, keep) if passed]
    prompt = [event for event in retained if event["stream"] == "prompt"]
    delayed = [event for event in retained if event["stream"] == "delayed"]

    def rate_stats(rows: list[dict[str, Any]]) -> tuple[int, float, float, float]:
        rate = math.fsum(float(row["event_weight_cps"]) for row in rows)
        sumw2 = math.fsum(float(row["event_weight_cps"]) ** 2 for row in rows)
        neff = rate * rate / sumw2 if sumw2 else 0.0
        return len(rows), rate, sumw2, neff

    p_n, p_rate, p_w2, p_neff = rate_stats(prompt)
    d_n, d_rate, d_w2, d_neff = rate_stats(delayed)
    event_mission_quanta = [prompt_mission_quantum for _ in prompt]
    event_mission_quanta.extend(
        float(event["event_weight_cps"])
        * mission_factors[(event["family"], str(event["source_parent_ZA"]))]
        for event in delayed
    )
    b20 = math.fsum(event_mission_quanta)
    b20_sumq2 = math.fsum(value * value for value in event_mission_quanta)
    b20_neff = b20 * b20 / b20_sumq2 if b20_sumq2 else 0.0
    return {
        "prompt_events": p_n,
        "prompt_rate_cps": p_rate,
        "prompt_sum_weight_sq_cps2": p_w2,
        "prompt_neff": p_neff,
        "delayed_events": d_n,
        "delayed_rate_cps": d_rate,
        "delayed_sum_weight_sq_cps2": d_w2,
        "delayed_neff": d_neff,
        "total_events": len(retained),
        "total_rate_cps": p_rate + d_rate,
        "total_sum_weight_sq_cps2": p_w2 + d_w2,
        "total_rate_neff": (p_rate + d_rate) ** 2 / (p_w2 + d_w2) if p_w2 + d_w2 else 0.0,
        "background_counts_20d": b20,
        "background_counts_20d_sum_quantum_sq": b20_sumq2,
        "background_counts_20d_neff": b20_neff,
    }


def scan(
    events: list[dict[str, Any]],
    mission_factors: dict[tuple[str, str], float],
    prompt_mission_quantum: float,
) -> list[dict[str, Any]]:
    baseline = aggregate(events, [True] * len(events), mission_factors, prompt_mission_quantum)
    radii = [round(0.15 * index, 2) for index in range(2, 25)]
    if FROZEN_RADIUS_CM not in radii:
        radii.append(FROZEN_RADIUS_CM)
    radii = sorted(set(radii))
    specs: list[tuple[str, str, float, int]] = []
    for kind in ("fixed_centroid", "all_fixed_pixels", "literal_channel_mask_w2_only"):
        specs.extend((kind, "pure_radial", radius, 5) for radius in radii)
    specs.extend(("fixed_centroid", "pure_layer", math.inf, layer) for layer in range(6))
    specs.extend(
        ("fixed_centroid", "joint_radius_layer", radius, layer)
        for radius in radii
        for layer in range(6)
    )
    # One explicit reproduction of the legacy common-response deposit-centroid
    # replay which yielded 137 rows, distinct from the frozen fixed-centre 135.
    specs.append(("deposit_centroid", "legacy_discrepancy_replay", FROZEN_RADIUS_CM, FROZEN_LAYER_MAX))

    rows: list[dict[str, Any]] = []
    for kind, scan_family, radius, layer in specs:
        flags = [keep_event(event, kind, radius, layer) for event in events]
        stats = aggregate(events, flags, mission_factors, prompt_mission_quantum)
        f_rate = stats["total_rate_cps"] / baseline["total_rate_cps"]
        f_b20 = stats["background_counts_20d"] / baseline["background_counts_20d"]
        retained_var = stats["background_counts_20d_sum_quantum_sq"]
        rejected_var = baseline["background_counts_20d_sum_quantum_sq"] - retained_var
        sigma_f = math.sqrt(max(0.0, retained_var * (1.0 - f_b20) ** 2 + rejected_var * f_b20**2)) / baseline[
            "background_counts_20d"
        ]
        sqrt_f = math.sqrt(f_b20)
        sqrt_sigma = 0.5 * sigma_f / sqrt_f if sqrt_f else 0.0
        rows.append(
            {
                "cut_semantics": kind,
                "scan_family": scan_family,
                "radius_cut_cm": "inf" if math.isinf(radius) else radius,
                "deepest_layer_max": layer,
                **stats,
                "prompt_rate_retention": stats["prompt_rate_cps"] / baseline["prompt_rate_cps"],
                "delayed_rate_retention": stats["delayed_rate_cps"] / baseline["delayed_rate_cps"],
                "total_rate_retention": f_rate,
                "background_counts_20d_retention_fB": f_b20,
                "background_counts_20d_retention_sigma_proxy": sigma_f,
                "sqrt_fB__fmin_ratio_if_signal_retention_1": sqrt_f,
                "sqrt_fB_sigma_proxy": sqrt_sigma,
                "minimum_signal_retention_for_improvement": sqrt_f,
                "fmin_ratio_formula": "sqrt(fB)/fS",
            }
        )
    return rows


def event_key(event: dict[str, Any]) -> tuple[str, str, int]:
    return event["family"], event["source_file"], int(event["local_event_id"])


def run(output_csv: Path, audit_json: Path, event_csv: Path) -> None:
    extractor = load_extractor()
    delayed_input = read_csv(DELAYED_LEDGER)
    delayed = recover_delayed_events(delayed_input, extractor)
    prompt = recover_prompt_events(read_csv(PROMPT_EVENTS))
    events = prompt + delayed
    mission_factors, prompt_mission_quantum = mission_quanta(delayed)
    scan_rows = scan(events, mission_factors, prompt_mission_quantum)

    fixed_set = {
        event_key(event)
        for event in delayed
        if keep_event(event, "fixed_centroid", FROZEN_RADIUS_CM, FROZEN_LAYER_MAX)
    }
    deposit_set = {
        event_key(event)
        for event in delayed
        if keep_event(event, "deposit_centroid", FROZEN_RADIUS_CM, FROZEN_LAYER_MAX)
    }
    frozen_set = {frozen_key(row) for row in read_csv(FROZEN_DELAYED)}
    baseline = aggregate(events, [True] * len(events), mission_factors, prompt_mission_quantum)
    fixed_stats = aggregate(
        events,
        [keep_event(event, "fixed_centroid", FROZEN_RADIUS_CM, FROZEN_LAYER_MAX) for event in events],
        mission_factors,
        prompt_mission_quantum,
    )
    deposit_stats = aggregate(
        events,
        [keep_event(event, "deposit_centroid", FROZEN_RADIUS_CM, FROZEN_LAYER_MAX) for event in events],
        mission_factors,
        prompt_mission_quantum,
    )

    compact_events = []
    for event in events:
        compact_events.append(
            {
                "stream": event["stream"],
                "family": event["family"],
                "local_event_id": event["local_event_id"],
                "source_file": event["source_file"],
                "event_weight_cps": event["event_weight_cps"],
                "source_parent_ZA": event["source_parent_ZA"],
                "measured_total_keV": event["measured_total_keV"],
                "measured_multiplicity": event["measured_multiplicity"],
                "fixed_centroid_r_cm": event["fixed_centroid_r_cm"],
                "deposit_centroid_r_cm": event["deposit_centroid_r_cm"],
                "max_fixed_pixel_r_cm": event["max_fixed_pixel_r_cm"],
                "deepest_layer": event["deepest_layer"],
                "passes_frozen_fixed_centroid_joint": keep_event(
                    event, "fixed_centroid", FROZEN_RADIUS_CM, FROZEN_LAYER_MAX
                ),
                "passes_legacy_deposit_centroid_joint": keep_event(
                    event, "deposit_centroid", FROZEN_RADIUS_CM, FROZEN_LAYER_MAX
                ),
            }
        )

    audit = {
        "status": "PASS_BACKGROUND_EDGE_CUT_REPLAY",
        "scope": "S3d-O8 corrected common-response W2 Step05 prompt+delayed survivors",
        "authorities": {
            "delayed_ledger": str(DELAYED_LEDGER.resolve()),
            "prompt_events": str(PROMPT_EVENTS.resolve()),
            "frozen_delayed_135": str(FROZEN_DELAYED),
            "mission": str(MISSION),
        },
        "reconstruction": {
            "delayed_rows": len(delayed),
            "prompt_step05_rows": len(prompt),
            "raw_delayed_SIM_files_streamed": len({event["source_file"] for event in delayed}),
            "response_namespace": extractor.RESPONSE_NAMESPACE,
            "pixel_coordinate_authority": "HTsim type-2 fixed TES pixel centre",
            "deposit_coordinate_authority": "CC HIT energy-deposit centroid per pixel",
            "all_selected_measured_totals_and_multiplicities_exact": True,
        },
        "baseline": baseline,
        "frozen_fixed_pixel_joint": fixed_stats,
        "legacy_deposit_centroid_joint": deposit_stats,
        "prompt_mission_quantum": {
            "matched_exact_trajectory_counts_per_prompt_root": prompt_mission_quantum,
            "historical_frozen_scalar_counts": HISTORICAL_FROZEN_PROMPT_COUNTS,
            "historical_minus_matched_counts": (
                HISTORICAL_FROZEN_PROMPT_COUNTS - prompt_mission_quantum
            ),
            "frozen_joint_total_counts_with_historical_scalar": (
                fixed_stats["background_counts_20d"]
                - prompt_mission_quantum
                + HISTORICAL_FROZEN_PROMPT_COUNTS
            ),
        },
        "frozen_delayed_set_comparison": {
            "durable_frozen_rows": len(frozen_set),
            "fixed_replay_rows": len(fixed_set),
            "deposit_replay_rows": len(deposit_set),
            "fixed_equals_durable_frozen": fixed_set == frozen_set,
            "fixed_not_in_deposit": [list(value) for value in sorted(fixed_set - deposit_set)],
            "deposit_not_in_fixed": [list(value) for value in sorted(deposit_set - fixed_set)],
        },
        "interpretation": {
            "fmin_ratio": "Fmin(cut)/Fmin(base) = sqrt(fB20)/fS20 under the same significance convention",
            "strict_improvement_gate": "fS20 > sqrt(fB20)",
            "statistics": (
                "sum-weight-squared and Neff are MC quantum proxies, not physical systematic errors; "
                "the prompt baseline has only two equal-weight roots and the frozen joint cut only one"
            ),
            "literal_channel_mask_limit": (
                "literal_channel_mask_w2_only drops masked pixels and rechecks W2 but does not rerun Step05; "
                "use only as a diagnostic, not as the decision authority"
            ),
        },
    }
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    write_csv(output_csv, scan_rows)
    write_csv(event_csv, compact_events)
    audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-csv", type=Path, default=DATA / "agent_background_edge_cut.csv")
    parser.add_argument("--audit-json", type=Path, default=DATA / "agent_background_edge_cut_audit.json")
    parser.add_argument("--event-csv", type=Path, default=DATA / "agent_background_edge_cut_events.csv")
    args = parser.parse_args()
    run(args.output_csv, args.audit_json, args.event_csv)


if __name__ == "__main__":
    main()
