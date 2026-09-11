#!/usr/bin/env python3
"""Extract and classify the selected W-grid atmospheric-511 event paths.

This is a read-only audit of the existing Cosima transport.  It scans one
compressed shard at a time and writes only the 151 W2-final selected events.
No transport is started and no authority file is modified.
"""

from __future__ import annotations

import csv
import gzip
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path("/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon")
PKG68 = ROOT / "engineering/geometry_optimization_20260815/68_sh3_wgrid_mono511_statistics_20260824"
RESPONSE = PKG68 / "outputs/01_wgrid_mono511_response_comparison_20260825/response"
RECEIPTS = PKG68 / "transport_full/run/receipts"
OUT = Path(__file__).resolve().parents[1] / "outputs/01_entry_path_diagnosis_20260825"

CATALOG = RESPONSE / "mono_line_event_catalog.npz"
W2_FINAL_BIT = 1 << 4

# Geometry is expressed in the InstrumentFrame.  The frame has Rotation 0 45 0.
ROT_Y_DEG = 45.0
COS45 = math.cos(math.radians(ROT_Y_DEG))
SIN45 = math.sin(math.radians(ROT_Y_DEG))
GRID_X_LOCAL_CM = -44.7
GRID_Y_HALF_CM = 2.7
GRID_Z_CENTER_LOCAL_CM = -2.8
GRID_Z_HALF_CM = 2.7
GRID_X_HALF_CM = 0.4
TES_X_CENTERS_LOCAL_CM = (-38.55, -37.35, -36.15, -34.95, -33.75, -32.55)
TES_X_HALF_WITH_TOL_CM = 0.17
TES_Y_HALF_CM = 1.82
TES_Z_CENTER_LOCAL_CM = -2.8
TES_Z_HALF_CM = 1.82


def world_to_local_position(x: float, y: float, z: float) -> tuple[float, float, float]:
    return COS45 * x - SIN45 * z, y, SIN45 * x + COS45 * z


def world_to_local_direction(dx: float, dy: float, dz: float) -> tuple[float, float, float]:
    return COS45 * dx - SIN45 * dz, dy, SIN45 * dx + COS45 * dz


def norm3(values: tuple[float, float, float]) -> tuple[float, float, float]:
    length = math.sqrt(sum(value * value for value in values))
    if length == 0:
        return math.nan, math.nan, math.nan
    return tuple(value / length for value in values)  # type: ignore[return-value]


def clamp(value: float) -> float:
    return max(-1.0, min(1.0, value))


def angle_deg_from_cos(value: float) -> float:
    return math.degrees(math.acos(clamp(value)))


def inside_tes_local(x: float, y: float, z: float) -> bool:
    return (
        any(abs(x - center) <= TES_X_HALF_WITH_TOL_CM for center in TES_X_CENTERS_LOCAL_CM)
        and abs(y) <= TES_Y_HALF_CM
        and abs(z - TES_Z_CENTER_LOCAL_CM) <= TES_Z_HALF_CM
    )


def inside_grid_local(x: float, y: float, z: float) -> bool:
    return (
        abs(x - GRID_X_LOCAL_CM) <= GRID_X_HALF_CM + 0.02
        and abs(y) <= GRID_Y_HALF_CM + 0.02
        and abs(z - GRID_Z_CENTER_LOCAL_CM) <= GRID_Z_HALF_CM + 0.02
    )


def segment_intersects_grid_envelope(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
) -> bool:
    """Return whether a finite IA-to-IA segment intersects the grid AABB."""
    lower = (
        GRID_X_LOCAL_CM - GRID_X_HALF_CM,
        -GRID_Y_HALF_CM,
        GRID_Z_CENTER_LOCAL_CM - GRID_Z_HALF_CM,
    )
    upper = (
        GRID_X_LOCAL_CM + GRID_X_HALF_CM,
        GRID_Y_HALF_CM,
        GRID_Z_CENTER_LOCAL_CM + GRID_Z_HALF_CM,
    )
    t_min, t_max = 0.0, 1.0
    for p0, p1, lo, hi in zip(start, end, lower, upper):
        delta = p1 - p0
        if abs(delta) <= 1e-12:
            if p0 < lo or p0 > hi:
                return False
            continue
        ta = (lo - p0) / delta
        tb = (hi - p0) / delta
        if ta > tb:
            ta, tb = tb, ta
        t_min = max(t_min, ta)
        t_max = min(t_max, tb)
        if t_min > t_max:
            return False
    return True


def segment_fully_crosses_grid_forward(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
) -> bool:
    """Return whether one +x' segment crosses both W-grid x' faces."""
    delta = tuple(end[index] - start[index] for index in range(3))
    if delta[0] <= 1e-12:
        return False
    for face_x in (GRID_X_LOCAL_CM - GRID_X_HALF_CM, GRID_X_LOCAL_CM + GRID_X_HALF_CM):
        t = (face_x - start[0]) / delta[0]
        if not 0.0 <= t <= 1.0:
            return False
        y = start[1] + t * delta[1]
        z = start[2] + t * delta[2]
        if abs(y) > GRID_Y_HALF_CM or abs(z - GRID_Z_CENTER_LOCAL_CM) > GRID_Z_HALF_CM:
            return False
    return True


def parse_ia(line: str) -> dict[str, Any]:
    fields = [value.strip() for value in line.split(";")]
    head = fields[0].split()
    process = head[1]
    record: dict[str, Any] = {"process": process, "raw": line.rstrip("\n")}
    if len(fields) >= 7:
        try:
            x, y, z = (float(fields[index]) for index in (4, 5, 6))
            lx, ly, lz = world_to_local_position(x, y, z)
            record.update({
                "x": x, "y": y, "z": z,
                "lx": lx, "ly": ly, "lz": lz,
                "in_tes": inside_tes_local(lx, ly, lz),
                "in_grid": inside_grid_local(lx, ly, lz),
            })
        except ValueError:
            pass
    if len(fields) >= 19:
        try:
            dx, dy, dz = (float(fields[index]) for index in (16, 17, 18))
            ldx, ldy, ldz = world_to_local_direction(dx, dy, dz)
            record.update({
                "dx": dx, "dy": dy, "dz": dz,
                "ldx": ldx, "ldy": ldy, "ldz": ldz,
            })
        except ValueError:
            pass
    try:
        record["energy_keV"] = float(fields[-1])
    except (ValueError, IndexError):
        record["energy_keV"] = math.nan
    return record


def scan_selected_events(sim_path: Path, wanted: set[int]) -> dict[int, list[dict[str, Any]]]:
    found: dict[int, list[dict[str, Any]]] = {}
    current: int | None = None
    current_rows: list[dict[str, Any]] = []
    with gzip.open(sim_path, "rt", encoding="utf-8", errors="strict") as handle:
        for line in handle:
            if line.startswith("ID "):
                if current is not None:
                    found[current] = current_rows
                    if set(found) == wanted:
                        break
                fields = line.split()
                event_id = int(fields[1])
                current = event_id if event_id in wanted else None
                current_rows = []
                continue
            if current is not None and line.startswith("IA "):
                current_rows.append(parse_ia(line))
            if current is not None and line.startswith("SE"):
                found[current] = current_rows
                current = None
                current_rows = []
                if set(found) == wanted:
                    break
    if current is not None:
        found[current] = current_rows
    missing = wanted - set(found)
    if missing:
        raise RuntimeError(f"missing selected events in {sim_path}: {sorted(missing)[:10]}")
    return found


def wilson95(successes: int, total: int) -> tuple[float, float]:
    if total <= 0:
        return math.nan, math.nan
    z = 1.959963984540054
    p = successes / total
    den = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / den
    half = z * math.sqrt(p * (1.0 - p) / total + z * z / (4.0 * total * total)) / den
    return center - half, center + half


def atmospheric_band(abs_mu: float) -> str:
    if abs_mu >= 0.8:
        return "near_atmospheric_vertical_abs_mu_ge_0p8"
    if abs_mu < 0.2:
        return "near_atmospheric_horizontal_abs_mu_lt_0p2"
    return "atmospheric_oblique_0p2_to_0p8"


def grid_band(local_dx: float) -> str:
    if local_dx >= 0.8:
        return "grid_facing_near_normal_ldx_ge_0p8"
    if local_dx > 0.0:
        return "grid_facing_oblique_0_to_0p8"
    if local_dx <= -0.8:
        return "rear_near_normal_ldx_le_minus0p8"
    return "rear_oblique_minus0p8_to_0"


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with np.load(CATALOG, allow_pickle=False) as data:
        arrays = {key: data[key] for key in data.files}
    selected_indices = np.flatnonzero((arrays["w2_flags"] & W2_FINAL_BIT) != 0)
    if len(selected_indices) != 151:
        raise RuntimeError(f"expected 151 W2-final events, found {len(selected_indices)}")

    receipts = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(RECEIPTS.glob("*.json"))]
    if len(receipts) != 64:
        raise RuntimeError(f"expected 64 receipts, found {len(receipts)}")

    selected_by_job: dict[int, dict[int, int]] = defaultdict(dict)
    for array_index in selected_indices:
        job_index = int(arrays["event_job_index"][array_index])
        event_id = int(arrays["event_id"][array_index])
        selected_by_job[job_index][event_id] = int(array_index)

    path_rows: list[dict[str, Any]] = []
    for job_index, receipt in enumerate(receipts):
        wanted_map = selected_by_job.get(job_index, {})
        if not wanted_map:
            continue
        sim_path = Path(receipt["sim_path"])
        recovered = scan_selected_events(sim_path, set(wanted_map))
        for event_id, ia_rows in recovered.items():
            array_index = wanted_map[event_id]
            init_rows = [row for row in ia_rows if row["process"] == "INIT"]
            if len(init_rows) != 1:
                raise RuntimeError(f"event {job_index}:{event_id} has {len(init_rows)} INIT rows")
            init = init_rows[0]
            interactions = [row for row in ia_rows if row["process"] != "INIT"]
            tes_positions = [index for index, row in enumerate(interactions) if row.get("in_tes")]
            first_tes_index = tes_positions[0] if tes_positions else None
            pre_tes = interactions[:first_tes_index] if first_tes_index is not None else interactions
            first_tes = interactions[first_tes_index] if first_tes_index is not None else None

            hit_start = int(arrays["hit_start"][array_index])
            hit_count = int(arrays["hit_count"][array_index])
            if hit_count <= 0:
                raise RuntimeError(f"selected event {job_index}:{event_id} has no TES hit")
            hx = float(arrays["hit_x_cm"][hit_start])
            hy = float(arrays["hit_y_cm"][hit_start])
            hz = float(arrays["hit_z_cm"][hit_start])
            hlx, hly, hlz = world_to_local_position(hx, hy, hz)

            dx, dy, dz = float(init["dx"]), float(init["dy"]), float(init["dz"])
            ldx, ldy, ldz = norm3((float(init["ldx"]), float(init["ldy"]), float(init["ldz"])))
            sx, sy, sz = float(init["x"]), float(init["y"]), float(init["z"])
            slx, sly, slz = float(init["lx"]), float(init["ly"]), float(init["lz"])

            grid_t = (GRID_X_LOCAL_CM - slx) / ldx if abs(ldx) > 1e-12 else math.nan
            grid_y = sly + grid_t * ldy if math.isfinite(grid_t) else math.nan
            grid_z = slz + grid_t * ldz if math.isfinite(grid_t) else math.nan
            grid_envelope_intersection = bool(
                math.isfinite(grid_t)
                and grid_t >= 0.0
                and abs(grid_y) <= GRID_Y_HALF_CM
                and abs(grid_z - GRID_Z_CENTER_LOCAL_CM) <= GRID_Z_HALF_CM
            )

            if first_tes is not None:
                target = (float(first_tes["lx"]), float(first_tes["ly"]), float(first_tes["lz"]))
            else:
                target = (hlx, hly, hlz)
            initial_tes_t = (
                (target[0] - slx) * ldx
                + (target[1] - sly) * ldy
                + (target[2] - slz) * ldz
            )
            grid_envelope_before_tes = bool(
                grid_envelope_intersection
                and initial_tes_t >= 0.0
                and grid_t <= initial_tes_t + 0.05
            )
            if pre_tes:
                origin = (float(pre_tes[-1]["lx"]), float(pre_tes[-1]["ly"]), float(pre_tes[-1]["lz"]))
            else:
                origin = (slx, sly, slz)
            last_ldx, last_ldy, last_ldz = norm3(tuple(target[i] - origin[i] for i in range(3)))

            polyline_vertices = [(slx, sly, slz)]
            polyline_vertices.extend(
                (float(row["lx"]), float(row["ly"]), float(row["lz"]))
                for row in pre_tes
            )
            polyline_vertices.append(target)
            polyline_segments = list(zip(polyline_vertices[:-1], polyline_vertices[1:]))
            actual_grid_envelope_contact = any(
                segment_intersects_grid_envelope(start, end)
                for start, end in polyline_segments
            )
            actual_full_grid_crossing = any(
                segment_fully_crosses_grid_forward(start, end)
                for start, end in polyline_segments
            )
            if actual_full_grid_crossing:
                actual_route_class = "full_grid_envelope_crossing"
            elif actual_grid_envelope_contact:
                actual_route_class = "partial_or_grazing_grid_envelope_contact"
            elif ldx > 0.0:
                actual_route_class = "grid_facing_bypass_outside_envelope"
            else:
                actual_route_class = "rear_or_side_bypass"

            has_grid_interaction = any(bool(row.get("in_grid")) for row in pre_tes)
            has_other_pre_tes_interaction = any(not bool(row.get("in_grid")) for row in pre_tes)
            direct_to_tes = len(pre_tes) == 0 and first_tes is not None
            if direct_to_tes and grid_envelope_before_tes:
                coupling_class = "direct_through_grid_envelope_no_recorded_grid_interaction"
            elif direct_to_tes and ldx > 0.0:
                coupling_class = "direct_grid_facing_side_path_not_through_grid_envelope"
            elif direct_to_tes:
                coupling_class = "direct_rear_entry"
            elif has_grid_interaction:
                coupling_class = "pre_tes_interaction_in_grid"
            elif has_other_pre_tes_interaction:
                coupling_class = "pre_tes_interaction_elsewhere"
            else:
                coupling_class = "unresolved"

            source_bin = int(arrays["source_bin80"][array_index])
            path_rows.append({
                "job_index": job_index,
                "job_id": receipt["job_id"],
                "event_id": event_id,
                "source_bin80": source_bin,
                "source_hemisphere": "down" if source_bin < 40 else "up",
                "source_mu_z": dz,
                "source_theta_atmospheric_deg": angle_deg_from_cos(dz),
                "source_abs_mu_z": abs(dz),
                "atmospheric_direction_band": atmospheric_band(abs(dz)),
                "source_x_world_cm": sx,
                "source_y_world_cm": sy,
                "source_z_world_cm": sz,
                "initial_dx_world": dx,
                "initial_dy_world": dy,
                "initial_dz_world": dz,
                "initial_dx_local_grid_normal": ldx,
                "initial_dy_local": ldy,
                "initial_dz_local": ldz,
                "initial_grid_direction_band": grid_band(ldx),
                "initial_angle_to_forward_grid_normal_deg": angle_deg_from_cos(ldx),
                "initial_angle_to_nearest_grid_normal_deg": angle_deg_from_cos(abs(ldx)),
                "grid_plane_t_cm": grid_t,
                "initial_tes_t_cm": initial_tes_t,
                "grid_plane_y_local_cm": grid_y,
                "grid_plane_z_local_cm": grid_z,
                "initial_ray_intersects_grid_envelope": int(grid_envelope_intersection),
                "initial_ray_intersects_grid_envelope_before_tes": int(grid_envelope_before_tes),
                "pre_tes_interaction_count": len(pre_tes),
                "pre_tes_processes": "+".join(str(row["process"]) for row in pre_tes) or "none",
                "grid_interaction_before_tes": int(has_grid_interaction),
                "other_interaction_before_tes": int(has_other_pre_tes_interaction),
                "first_tes_process": first_tes["process"] if first_tes else "missing",
                "last_segment_dx_local": last_ldx,
                "last_segment_dy_local": last_ldy,
                "last_segment_dz_local": last_ldz,
                "last_segment_grid_direction_band": grid_band(last_ldx),
                "last_segment_angle_to_nearest_grid_normal_deg": angle_deg_from_cos(abs(last_ldx)),
                "coupling_class": coupling_class,
                "actual_pre_tes_polyline_segments": len(polyline_segments),
                "actual_grid_envelope_contact_before_tes": int(actual_grid_envelope_contact),
                "actual_full_grid_envelope_crossing_before_tes": int(actual_full_grid_crossing),
                "actual_route_class": actual_route_class,
                "pre_tes_polyline_vertices_local_json": json.dumps(polyline_vertices, separators=(",", ":")),
                "tes_first_hit_layer": int(arrays["hit_layer"][hit_start]),
                "tes_hit_count": hit_count,
                "tes_first_hit_x_local_cm": hlx,
                "tes_first_hit_y_local_cm": hly,
                "tes_first_hit_z_local_cm": hlz,
                "base_event_weight_cps": float(arrays["base_event_weight_cps"][array_index]),
            })

    if len(path_rows) != 151:
        raise RuntimeError(f"path row closure failed: {len(path_rows)}")
    path_rows.sort(key=lambda row: (int(row["job_index"]), int(row["event_id"])))
    write_csv(OUT / "selected_event_paths.csv", path_rows)

    band_rows: list[dict[str, Any]] = []
    for dimension, field in (
        ("atmospheric_vertical_axis", "atmospheric_direction_band"),
        ("initial_grid_normal_axis", "initial_grid_direction_band"),
        ("last_segment_grid_normal_axis", "last_segment_grid_direction_band"),
        ("coupling_path", "coupling_class"),
        ("actual_pre_tes_geometric_route", "actual_route_class"),
    ):
        counts = Counter(str(row[field]) for row in path_rows)
        for category, count in sorted(counts.items()):
            low, high = wilson95(count, len(path_rows))
            band_rows.append({
                "dimension": dimension,
                "category": category,
                "selected_events": count,
                "selected_fraction": count / len(path_rows),
                "wilson95_low": low,
                "wilson95_high": high,
            })
    write_csv(OUT / "selected_path_composition.csv", band_rows)

    source_hemisphere = Counter(str(row["source_hemisphere"]) for row in path_rows)
    coupling_counts = Counter(str(row["coupling_class"]) for row in path_rows)
    initial_near_normal = sum(abs(float(row["initial_dx_local_grid_normal"])) >= 0.8 for row in path_rows)
    forward_near_normal = sum(float(row["initial_dx_local_grid_normal"]) >= 0.8 for row in path_rows)
    atmospheric_near_vertical = sum(float(row["source_abs_mu_z"]) >= 0.8 for row in path_rows)
    last_near_normal = sum(abs(float(row["last_segment_dx_local"])) >= 0.8 for row in path_rows)
    direct = sum(str(row["coupling_class"]).startswith("direct_") for row in path_rows)
    direct_grid_envelope = coupling_counts["direct_through_grid_envelope_no_recorded_grid_interaction"]
    actual_route_counts = Counter(str(row["actual_route_class"]) for row in path_rows)
    actual_route_by_hemisphere = {
        hemisphere: dict(Counter(
            str(row["actual_route_class"])
            for row in path_rows
            if str(row["source_hemisphere"]) == hemisphere
        ))
        for hemisphere in ("down", "up")
    }
    summary = {
        "status": "PASS__EXISTING_WGRID_SELECTED_PATHS_EXTRACTED",
        "selected_events": len(path_rows),
        "event_weight_cps": float(path_rows[0]["base_event_weight_cps"]),
        "selected_rate_cps": len(path_rows) * float(path_rows[0]["base_event_weight_cps"]),
        "source_hemisphere_counts": dict(source_hemisphere),
        "atmospheric_near_vertical_abs_mu_ge_0p8": {
            "count": atmospheric_near_vertical,
            "fraction": atmospheric_near_vertical / len(path_rows),
            "wilson95": wilson95(atmospheric_near_vertical, len(path_rows)),
        },
        "initial_near_either_grid_normal_abs_ldx_ge_0p8": {
            "count": initial_near_normal,
            "fraction": initial_near_normal / len(path_rows),
            "wilson95": wilson95(initial_near_normal, len(path_rows)),
        },
        "initial_grid_facing_near_normal_ldx_ge_0p8": {
            "count": forward_near_normal,
            "fraction": forward_near_normal / len(path_rows),
            "wilson95": wilson95(forward_near_normal, len(path_rows)),
        },
        "last_segment_near_either_grid_normal_abs_ldx_ge_0p8": {
            "count": last_near_normal,
            "fraction": last_near_normal / len(path_rows),
            "wilson95": wilson95(last_near_normal, len(path_rows)),
        },
        "direct_to_tes": {
            "count": direct,
            "fraction": direct / len(path_rows),
            "wilson95": wilson95(direct, len(path_rows)),
        },
        "direct_through_grid_envelope_without_recorded_grid_interaction": {
            "count": direct_grid_envelope,
            "fraction": direct_grid_envelope / len(path_rows),
            "wilson95": wilson95(direct_grid_envelope, len(path_rows)),
        },
        "coupling_counts": dict(coupling_counts),
        "actual_pre_tes_geometric_route_counts": dict(actual_route_counts),
        "actual_pre_tes_geometric_route_by_hemisphere": actual_route_by_hemisphere,
        "definitions": {
            "atmospheric_vertical": "absolute initial world-z direction cosine >= 0.8",
            "grid_near_normal": "absolute initial or last-segment InstrumentFrame-x direction cosine >= 0.8",
            "direct": "the first recorded physical interaction after IA INIT is inside a TES layer",
            "grid_envelope": "straight initial ray intersects x'=-44.7 cm within y'=+-2.7 cm and z'=-2.8+-2.7 cm",
            "actual_pre_tes_geometric_route": "piecewise-linear IA INIT -> pre-TES IA positions -> first TES IA, intersected with the full x'/y'/z' grid envelope",
        },
        "sources": {
            "event_catalog": str(CATALOG),
            "receipts": str(RECEIPTS),
            "geometry": str(PKG68 / "transport_authority/geometry/SH3_Assembly_OptV3.geo"),
        },
    }
    (OUT / "path_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
