#!/usr/bin/env python3
"""Audit S3d-O8 focused-signal retention under transverse TES fiducial cuts.

The official stage04 response is reproduced from the retained 37,194-event
post-Be-window replay.  The response/topology decision continues to use the
recorded per-pixel deposit centroid, exactly as stage04 does.  The new
fiducial coordinate is deliberately different: ``HTsim`` detector-type 2
records are matched to their CC pixel aggregates and used as fixed TES pixel
centres.  This keeps the signal scan on the same pixel-centre convention as
the prompt event audit.

No transport is launched.  Source worktrees and the 24 MB SIM are read-only.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import importlib.util
import json
import math
import pickle
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.stats import beta


WORKTREE = Path("/home/ubuntu/.codex/worktrees/601e/TES_511_Balloon")
PACKAGE = (
    WORKTREE
    / "engineering/particle_source_unit_repair_20260811"
    / "s3d_o8_event_geometry_visualization_20260814"
)
SOURCE_TREE = Path("/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon")
LIVE_ROOT = Path("/home/ubuntu/TES_511_Balloon")
STAGE04_PACKAGE = (
    SOURCE_TREE
    / "engineering/particle_source_unit_repair_20260811"
    / "m05_corrected_reanalysis_20260813"
)
STAGE04_CODE = STAGE04_PACKAGE / "code"
STAGE04_OUTPUT = STAGE04_PACKAGE / "outputs/04_common_response"
COMMON_CODE = STAGE04_CODE / "build_common_response.py"
SIM = (
    LIVE_ROOT
    / "runs/geometry_optimization_20260704"
    / "s3d_o8_f10m_a1_signal_replay_37194_20260712"
    / "Opticsim_laue_f10m_a1_s3d_o8_signal37194.inc1.id1.sim.gz"
)
SOURCE = SIM.parent / "Opticsim_laue_f10m_a1_s3d_o8_signal37194.source"
EVENTLIST = (
    SOURCE_TREE
    / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/eventlists"
    / "Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat"
)
STEP09 = (
    SOURCE_TREE
    / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5"
    / "step09_optics_bridge_summary.json"
)
OFFICIAL_SIGNAL = STAGE04_OUTPUT / "signal_acceptance_effective_area.csv"
OFFICIAL_PSF = STAGE04_OUTPUT / "signal_psf.csv"
OFFICIAL_MISSION = STAGE04_PACKAGE / "outputs/06_mission/summary.json"

OUT_CSV = PACKAGE / "data/agent_signal_edge_cut.csv"
OUT_LAYER_CSV = PACKAGE / "data/agent_signal_layer_cut.csv"
OUT_AUDIT = PACKAGE / "audit/agent_signal_edge_cut.json"
GEOMETRY_MANIFEST = PACKAGE / "data/geometry_volume_manifest.csv"

TRIALS = 37_194
W2 = (510.58, 511.42)
AXIS_Y_CM = 0.0
AXIS_Z_CM = -5.2
RADIUS_GRID_CM = sorted({round(0.40 + 0.05 * index, 2) for index in range(29)} | {1.35, 2.0})


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def quantile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, math.ceil(fraction * len(ordered)) - 1))]


def clopper_pearson(count: int, trials: int) -> tuple[float, float]:
    low = 0.0 if count == 0 else float(beta.ppf(0.025, count, trials - count + 1))
    high = 1.0 if count == trials else float(beta.ppf(0.975, count + 1, trials - count))
    return low, high


def world_to_if(x: float, y: float, z: float) -> tuple[float, float, float]:
    c = math.sqrt(0.5)
    return c * (x - z), y, c * (x + z)


def htsim_centres(required_ids: set[int]) -> dict[int, list[dict[str, float]]]:
    grouped: dict[int, dict[tuple[float, float, float], dict[str, float]]] = {}
    current_id: int | None = None
    with gzip.open(SIM, "rt", encoding="utf-8", errors="strict") as handle:
        for raw in handle:
            line = raw.strip()
            if line.startswith("ID "):
                current_id = int(line.split()[1])
                continue
            if current_id not in required_ids or not line.startswith("HTsim "):
                continue
            fields = [field.strip() for field in line.split("HTsim", 1)[1].split(";")]
            if int(fields[0]) != 2:
                continue
            x, y, z, energy = (float(fields[index]) for index in (1, 2, 3, 4))
            x_if, y_if, z_if = world_to_if(x, y, z)
            key = (x, y, z)
            target = grouped.setdefault(current_id, {}).setdefault(
                key,
                {
                    "world_x_cm": x,
                    "world_y_cm": y,
                    "world_z_cm": z,
                    "IF_x_cm": x_if,
                    "IF_y_cm": y_if,
                    "IF_z_cm": z_if,
                    "raw_energy_keV": 0.0,
                    "radius_cm": math.hypot(y_if - AXIS_Y_CM, z_if - AXIS_Z_CM),
                },
            )
            target["raw_energy_keV"] += energy
    return {event_id: list(rows.values()) for event_id, rows in grouped.items()}


def match_fixed_centres(
    catalog: dict[str, Any], event_index: int, centres: list[dict[str, float]]
) -> tuple[dict[str, dict[str, float]], float, float, int]:
    start = int(catalog["pix_start"][event_index])
    count = int(catalog["pix_count"][event_index])
    stop = start + count
    if len(centres) < count:
        raise RuntimeError(
            f"too few HTsim type-2 centres at event {catalog['local_id'][event_index]}: "
            f"{len(centres)} < {count} TP pixels"
        )
    raw_rows = []
    for hit_index in range(start, stop):
        raw_rows.append(
            {
                "uid": str(catalog["pix_uid"][hit_index]),
                "layer": int(catalog["pix_layer"][hit_index]),
                "energy": float(catalog["pix_e"][hit_index]),
                "x": float(catalog["pix_x"][hit_index]),
                "y": float(catalog["pix_y"][hit_index]),
                "z": float(catalog["pix_z"][hit_index]),
            }
        )
    cost = np.zeros((count, len(centres)), dtype=float)
    for i, raw in enumerate(raw_rows):
        for j, fixed in enumerate(centres):
            energy_term = abs(raw["energy"] - fixed["raw_energy_keV"]) * 1.0e6
            spatial_term = math.sqrt(
                (raw["x"] - fixed["world_x_cm"]) ** 2
                + (raw["y"] - fixed["world_y_cm"]) ** 2
                + (raw["z"] - fixed["world_z_cm"]) ** 2
            )
            cost[i, j] = energy_term + spatial_term
    left, right = linear_sum_assignment(cost)
    mapping: dict[str, dict[str, float]] = {}
    max_energy_residual = 0.0
    max_layer_residual = 0.0
    for i, j in zip(left.tolist(), right.tolist(), strict=True):
        raw = raw_rows[i]
        fixed = dict(centres[j])
        energy_residual = abs(raw["energy"] - fixed["raw_energy_keV"])
        expected_x_if = -3.0 + 1.2 * raw["layer"]
        layer_residual = abs(fixed["IF_x_cm"] - expected_x_if)
        max_energy_residual = max(max_energy_residual, energy_residual)
        max_layer_residual = max(max_layer_residual, layer_residual)
        fixed["layer"] = float(raw["layer"])
        mapping[raw["uid"]] = fixed
    if max_energy_residual > 1.0e-3:
        raise RuntimeError(f"HTsim energy matching residual={max_energy_residual:.9g} keV")
    if max_layer_residual > 5.0e-4:
        raise RuntimeError(f"HTsim layer-plane residual={max_layer_residual:.9g} cm")
    return mapping, max_energy_residual, max_layer_residual, len(centres) - count


def official_stage04_row() -> dict[str, str]:
    rows = read_csv(OFFICIAL_SIGNAL)
    matches = [
        row
        for row in rows
        if row["geometry"] == "S3d_O8"
        and row["response_state"] == "measured"
        and row["stage"] == "side_compton_fov_pass"
        and row["window_id"] == "w2_510p58_511p42"
    ]
    if len(matches) != 1:
        raise RuntimeError(f"official stage04 signal authority cardinality={len(matches)}")
    return matches[0]


def main() -> None:
    if str(STAGE04_CODE) not in sys.path:
        sys.path.insert(0, str(STAGE04_CODE))
    common = load_module("agent_signal_edge_common", COMMON_CODE)
    prompt = common.prompt
    config = common.load_json(common.CONFIG)
    active = list(config["geometries"]["S3d_O8"]["active_veto_volumes"])
    eventlist_sha = sha256(EVENTLIST)
    source_seed = common.source_seed(SOURCE)
    job = {
        "scan_index": 0,
        "geometry": "S3d_O8",
        "family": "focused_511",
        "mode": "signal",
        "input_id": "focused_signal_eventlist",
        "batch_id": f"eventlist_sha256:{eventlist_sha}",
        "job_id": "Opticsim_laue_f10m_a1_s3d_o8_signal37194",
        "events": TRIALS,
        "sim_path": str(SIM),
        "seed": source_seed,
        "source_declared_seed": source_seed,
        "shield_volumes": [name for name in active if "Plastic" not in name],
        "plastic_volumes": [name for name in active if "Plastic" in name],
    }
    optics_aeff = float(common.load_json(common.OPTICS)["aeff_511_cm2"])
    bridge = common.load_json(STEP09)["bridge"]
    if float(bridge["axis_y_cm"]) != AXIS_Y_CM or float(bridge["axis_z_cm"]) != AXIS_Z_CM:
        raise RuntimeError(f"signal-axis authority changed: {bridge}")

    with tempfile.TemporaryDirectory(prefix="s3d_o8_signal_edge_") as temp_name:
        temp = Path(temp_name)
        scan = prompt.scan_job(job, str(temp))
        catalog_path = temp / "signal.pkl"
        common.publish_signal_catalog(
            job,
            scan,
            catalog_path,
            optics_aeff,
            eventlist_sha,
            "not_recomputed__stage04_input_authority",
        )
        with catalog_path.open("rb") as handle:
            catalog = pickle.load(handle)

        required_ids = {int(value) for value in catalog["local_id"]}
        centres = htsim_centres(required_ids)
        core, step05, disk = common.response_runtime()
        records: list[dict[str, Any]] = []
        max_energy_residual = 0.0
        max_layer_residual = 0.0
        extra_type2_centres = 0
        events_with_extra_type2_centres = 0
        deposit_radii: list[float] = []
        fixed_radii: list[float] = []
        official_count = 0
        for event_index in range(len(catalog["stream"])):
            local_id = int(catalog["local_id"][event_index])
            fixed, energy_residual, layer_residual, extra_centres = match_fixed_centres(
                catalog, event_index, centres.get(local_id, [])
            )
            max_energy_residual = max(max_energy_residual, energy_residual)
            max_layer_residual = max(max_layer_residual, layer_residual)
            extra_type2_centres += extra_centres
            events_with_extra_type2_centres += int(extra_centres > 0)
            event = prompt.evaluate_event(catalog, event_index, core, step05, disk)
            measured_hits = list(event["measured_hits"])
            fixed_hits = [(hit, fixed[str(hit.pixel_uid)]) for hit in measured_hits]
            total = math.fsum(float(hit.e) for hit in measured_hits)
            official = bool(
                prompt.in_window(total, W2)
                and event["active_pass"][50.0]
                and event["topology_pass"]
            )
            fixed_centroid_radius: float | None = None
            max_pixel_radius: float | None = None
            max_layer: int | None = None
            if fixed_hits:
                fixed_y = math.fsum(float(hit.e) * point["IF_y_cm"] for hit, point in fixed_hits) / total
                fixed_z = math.fsum(float(hit.e) * point["IF_z_cm"] for hit, point in fixed_hits) / total
                fixed_centroid_radius = math.hypot(fixed_y - AXIS_Y_CM, fixed_z - AXIS_Z_CM)
                max_pixel_radius = max(point["radius_cm"] for _, point in fixed_hits)
                max_layer = max(int(hit.layer) for hit, _ in fixed_hits)
            if official:
                official_count += 1
                deposit_radius = common.centroid_radius(measured_hits, bridge)
                if deposit_radius is None or fixed_centroid_radius is None:
                    raise RuntimeError("official signal event has no measurable centroid")
                deposit_radii.append(float(deposit_radius))
                fixed_radii.append(float(fixed_centroid_radius))
            records.append(
                {
                    "local_id": local_id,
                    "active": bool(event["active_pass"][50.0]),
                    "official": official,
                    "fixed_centroid_radius": fixed_centroid_radius,
                    "max_pixel_radius": max_pixel_radius,
                    "max_layer": max_layer,
                    "fixed_hits": fixed_hits,
                }
            )

    authority = official_stage04_row()
    authority_count = int(authority["selected_events"])
    if official_count != authority_count:
        raise RuntimeError(f"stage04 reproduction count={official_count}, authority={authority_count}")
    authority_psf = [
        row
        for row in read_csv(OFFICIAL_PSF)
        if row["geometry"] == "S3d_O8"
        and row["stage"] == "side_compton_fov_pass"
        and row["window_id"] == "w2_510p58_511p42"
    ]
    if len(authority_psf) != 1:
        raise RuntimeError("stage04 PSF authority cardinality changed")
    deposit_quantiles = {f"r{int(q * 100)}_cm": quantile(deposit_radii, q) for q in (0.5, 0.9, 0.95, 0.99)}
    fixed_quantiles = {f"r{int(q * 100)}_cm": quantile(fixed_radii, q) for q in (0.5, 0.9, 0.95, 0.99)}
    for key, value in deposit_quantiles.items():
        if abs(value - float(authority_psf[0][key])) > 1.0e-12:
            raise RuntimeError(f"stage04 deposit-centroid PSF mismatch for {key}")

    mission = common.load_json(OFFICIAL_MISSION)
    mission_s20 = float(mission["geometries"]["S3d_O8"]["source_counts_20d"])
    selected_aeff = float(authority["selected_effective_area_cm2"])
    geometry_pixels = [
        row for row in read_csv(GEOMETRY_MANIFEST) if row["geometry_name"].startswith("TP_L")
    ]
    if len(geometry_pixels) != 2_256:
        raise RuntimeError(f"geometry TES pixel cardinality={len(geometry_pixels)}, expected 2256")
    geometry_pixel_radii = [
        math.hypot(
            0.5 * (float(row["instrument_y_min_cm"]) + float(row["instrument_y_max_cm"])),
            0.5 * (float(row["instrument_z_min_cm"]) + float(row["instrument_z_max_cm"]))
            - AXIS_Z_CM,
        )
        for row in geometry_pixels
    ]
    rows: list[dict[str, Any]] = []
    for radius in RADIUS_GRID_CM:
        centroid_count = sum(
            1
            for row in records
            if row["official"]
            and row["fixed_centroid_radius"] is not None
            and row["fixed_centroid_radius"] <= radius
        )
        strict_count = sum(
            1
            for row in records
            if row["official"]
            and row["max_pixel_radius"] is not None
            and row["max_pixel_radius"] <= radius
        )
        centroid_l3_count = sum(
            1
            for row in records
            if row["official"]
            and row["fixed_centroid_radius"] is not None
            and row["fixed_centroid_radius"] <= radius
            and row["max_layer"] is not None
            and row["max_layer"] <= 3
        )
        mask_count = 0
        for row in records:
            if not row["active"]:
                continue
            inside = [hit for hit, point in row["fixed_hits"] if point["radius_cm"] <= radius]
            if len(inside) == len(row["fixed_hits"]):
                # Identical hit set, energy and topology to the already cached
                # official decision; avoid re-enumerating Compton cones for
                # every radius value.
                mask_count += int(row["official"])
                continue
            inside_total = math.fsum(float(hit.e) for hit in inside)
            if not prompt.in_window(inside_total, W2):
                continue
            topology_pass, _ = prompt.topology_keep(inside, step05, disk)
            if topology_pass:
                mask_count += 1
        centroid_fraction = centroid_count / official_count
        strict_fraction = strict_count / official_count
        mask_fraction = mask_count / official_count
        centroid_l3_fraction = centroid_l3_count / official_count
        physical_pixel_count = sum(pixel_radius <= radius for pixel_radius in geometry_pixel_radii)
        physical_pixel_fraction = physical_pixel_count / len(geometry_pixel_radii)
        low, high = clopper_pearson(centroid_count, TRIALS)
        rows.append(
            {
                "radius_cm": radius,
                "physical_TES_pixels_inside": physical_pixel_count,
                "physical_TES_pixel_fraction": physical_pixel_fraction,
                "physical_TES_pixels_inside_per_layer": physical_pixel_count // 6,
                "baseline_official_stage04_events": official_count,
                "centroid_gate_events": centroid_count,
                "centroid_gate_fS": centroid_fraction,
                "centroid_gate_trial_acceptance": centroid_count / TRIALS,
                "centroid_gate_trial_acceptance_lower95": low,
                "centroid_gate_trial_acceptance_upper95": high,
                "centroid_gate_selected_aeff_cm2": selected_aeff * centroid_fraction,
                "centroid_gate_postBe_S20_diagnostic": mission_s20 * centroid_fraction,
                "centroid_gate_postBe_B20max_diagnostic": (mission_s20 * centroid_fraction / 10.0) ** 2,
                "all_measured_pixels_inside_events": strict_count,
                "all_measured_pixels_inside_fS": strict_fraction,
                "pixel_mask_reselect_events": mask_count,
                "pixel_mask_reselect_fS": mask_fraction,
                "centroid_and_max_layer_le3_events": centroid_l3_count,
                "centroid_and_max_layer_le3_fS": centroid_l3_fraction,
                "coordinate_semantics": "HTsim type2 fixed TES pixel centres; IF y-z radius about (0,-5.2 cm)",
                "selection_scope": "official measured W2+active50+side-Compton, then post-selection gate; pixel_mask column reselects after literal masking",
                "signal_scope_caveat": "post-Be-window detector acceptance only; not full-envelope BPE/plastic transmission",
            }
        )

    layer_rows: list[dict[str, Any]] = []
    for max_layer in range(6):
        count = sum(
            1
            for row in records
            if row["official"] and row["max_layer"] is not None and row["max_layer"] <= max_layer
        )
        fraction = count / official_count
        layer_rows.append(
            {
                "deepest_measured_layer_max": max_layer,
                "events": count,
                "fS": fraction,
                "selected_aeff_cm2": selected_aeff * fraction,
                "postBe_S20_diagnostic": mission_s20 * fraction,
                "scope_caveat": "post-Be-window S3d-O8 stage04; event veto on deepest measured layer",
            }
        )

    write_csv(OUT_CSV, rows)
    write_csv(OUT_LAYER_CSV, layer_rows)
    audit = {
        "status": "PASS_SIGNAL_EDGE_CUT_AUDIT",
        "facts": {
            "trials": TRIALS,
            "official_stage04_final_measured_w2_events": official_count,
            "official_selected_aeff_cm2": selected_aeff,
            "official_postBe_S20_counts_20d": mission_s20,
            "catalog_TES_positive_events": len(records),
            "geometry_physical_TES_pixels": len(geometry_pixels),
            "geometry_physical_TES_pixels_per_layer": len(geometry_pixels) // 6,
            "HTsim_events_with_centres": len(centres),
            "max_HTsim_CC_energy_match_residual_keV": max_energy_residual,
            "max_HTsim_layer_plane_residual_cm": max_layer_residual,
            "non_TP_extra_HTsim_type2_centres": extra_type2_centres,
            "events_with_non_TP_extra_HTsim_type2_centres": events_with_extra_type2_centres,
            "stage04_deposit_centroid_psf_reproduced": deposit_quantiles,
            "fixed_pixel_centroid_psf": fixed_quantiles,
            "world_to_InstrumentFrame": {
                "x_IF": "(x_world-z_world)/sqrt(2)",
                "y_IF": "y_world",
                "z_IF": "(x_world+z_world)/sqrt(2)",
            },
            "fiducial_axis_IF_yz_cm": [AXIS_Y_CM, AXIS_Z_CM],
        },
        "interpretation": {
            "centroid_gate": "additional event-level gate on the energy-weighted fixed-pixel centroid",
            "all_measured_pixels_inside": "additional event veto if any measured pixel centre lies outside",
            "pixel_mask_reselect": "literal removal of outside pixel energies followed by W2 and topology reselection",
            "layer_gate": "additional event veto on deepest measured layer",
        },
        "scope_caveat": (
            "The retained stage04 signal catalog is explicitly normalized at the post-Be-window "
            "injection plane.  These fS values audit a TES analysis cut; they are not evidence for "
            "BPE/plastic transmission and cannot replace a candidate-own full-envelope S20."
        ),
        "sources": {
            "sim": str(SIM),
            "source": str(SOURCE),
            "eventlist": str(EVENTLIST),
            "stage04_code": str(COMMON_CODE),
            "stage04_signal_authority": str(OFFICIAL_SIGNAL),
            "stage04_psf_authority": str(OFFICIAL_PSF),
            "mission_authority": str(OFFICIAL_MISSION),
        },
        "outputs": {
            "radius_scan": str(OUT_CSV),
            "layer_scan": str(OUT_LAYER_CSV),
        },
    }
    OUT_AUDIT.parent.mkdir(parents=True, exist_ok=True)
    OUT_AUDIT.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit["facts"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
