#!/usr/bin/env python3
"""Audit the frozen focused EventList against the SH3 active-BGO small aperture.

This is a deterministic straight-line geometry audit.  It launches no particle
transport and makes no detector-response claim.  In particular, the reported
microchannel direct-clear fraction is only a geometric estimate; tungsten
transmission, scattering, and the selected signal effective area require a
dedicated replay of the same EventList through this mass model.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCRIPT = Path(__file__).resolve()
PACKAGE = SCRIPT.parents[1]
GEOMETRY = PACKAGE / "geometry/SH3_Assembly_OptV3.geo"
MANIFEST = PACKAGE / "data/bgo_smallap_sg3grid_manifest.json"
OUTPUT = PACKAGE / "audit/bgo_smallap_signal_clearance.json"

EVENTLIST = Path(
    "/home/ubuntu/TES_511_Balloon/DEEPSEEK_CODE/outputs/eventlists/"
    "Opticsim_laue_f10m_a1_v3p5_centerfinger_optv3_focal_z2p8.eventlist.dat"
)
EVENTLIST_SHA256 = "2cfbeaf78d31df292cb36e36ec97ed116356606537c61ead93fae6fc84bad4d2"
EVENTLIST_ROWS = 37_194
GEOMETRY_SHA256 = "ae015378ca7731eb52545f19e2e7e7df2f88f75026b51d7f5f2dc598bcf1e973"
MANIFEST_STATUS = "PASS__SH3_OPTV3_BGO_SMALLAP_SG3GRID_BUILT"

# Instrument-local geometry, in centimetres.  Here the front active-BGO cut is
# physically the same 3.796 cm square as the grid envelope.
APERTURE_HALF_CM = 1.898
APERTURE_CENTER_Y_CM = 0.0
APERTURE_CENTER_Z_CM = -2.8
INJECTION_X_CM = -46.0
GRID_CENTER_X_CM = -44.7
GRID_W_HALF_DEPTH_CM = 0.399
BGO_FRONT_CENTER_X_CM = -43.7
BGO_FRONT_HALF_DEPTH_CM = 2.0

# Exact SG3 grid solid dimensions and placements.
PITCH_CM = 0.155
WEB_HALF_CM = 0.0065
HORIZONTAL_HALF_SPAN_Y_CM = 1.894
WEB_CENTERS_CM = tuple(-1.7825 + PITCH_CM * index for index in range(24))
VERTICAL_SEGMENTS_CM = (
    (-1.8415, 0.0515),
    *( (-1.705 + PITCH_CM * index, 0.07) for index in range(23) ),
    (1.8415, 0.0515),
)

STATUS_PASS = "PASS__SH3_OPTV3_BGO_SMALLAP_SIGNAL_CLEARANCE_AUDIT"


class AuditError(RuntimeError):
    """Fail-closed audit error."""


@dataclass(frozen=True)
class Ray:
    event_id: int
    x: float
    y: float
    z: float
    dx: float
    dy: float
    dz: float


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    return {
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        path.chmod(0o644)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def nearest_rank(values: Iterable[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise AuditError("cannot calculate a quantile from an empty sequence")
    index = min(len(ordered) - 1, math.ceil(probability * len(ordered)) - 1)
    return ordered[index]


def parse_eventlist() -> tuple[list[Ray], dict[str, Any]]:
    if not EVENTLIST.is_file():
        raise AuditError(f"missing locked EventList: {EVENTLIST}")
    current_sha = sha256(EVENTLIST)
    if current_sha != EVENTLIST_SHA256:
        raise AuditError(
            f"EventList SHA-256 mismatch: expected {EVENTLIST_SHA256}, got {current_sha}"
        )

    rays: list[Ray] = []
    direction_norm_errors: list[float] = []
    local_x_offsets: list[float] = []
    energies: set[float] = set()
    inverse_sqrt_two = 2.0**-0.5
    with EVENTLIST.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            fields = line.split()
            if len(fields) != 15:
                raise AuditError(
                    f"unexpected EventList field count on line {line_number}: {len(fields)}"
                )
            try:
                event_id = int(fields[0])
                world_x, world_y, world_z = map(float, fields[5:8])
                world_dx, world_dy, world_dz = map(float, fields[8:11])
                energy_keV = float(fields[14])
            except ValueError as exc:
                raise AuditError(f"non-numeric EventList row {line_number}") from exc

            # Undo InstrumentFrame.Rotation 0 45 0.
            local_x = (world_x - world_z) * inverse_sqrt_two
            local_y = world_y
            local_z = (world_x + world_z) * inverse_sqrt_two
            local_dx = (world_dx - world_dz) * inverse_sqrt_two
            local_dy = world_dy
            local_dz = (world_dx + world_dz) * inverse_sqrt_two
            if local_dx <= 0.0:
                raise AuditError(f"non-forward EventList ray on line {line_number}")
            rays.append(
                Ray(event_id, local_x, local_y, local_z, local_dx, local_dy, local_dz)
            )
            direction_norm_errors.append(
                abs(math.sqrt(local_dx**2 + local_dy**2 + local_dz**2) - 1.0)
            )
            local_x_offsets.append(abs(local_x - INJECTION_X_CM))
            energies.add(energy_keV)

    if len(rays) != EVENTLIST_ROWS:
        raise AuditError(f"expected {EVENTLIST_ROWS} EventList rows, parsed {len(rays)}")
    if [ray.event_id for ray in rays] != list(range(EVENTLIST_ROWS)):
        raise AuditError("EventList identifiers are not the exact 0..37193 sequence")
    if energies != {511.0}:
        raise AuditError(f"EventList energy contract drift: {sorted(energies)}")
    if max(local_x_offsets) > 1.0e-8:
        raise AuditError("EventList is not on the locked local x=-46 cm injection plane")
    if max(direction_norm_errors) > 1.0e-8:
        raise AuditError("EventList direction vectors are not unit length")

    return rays, {
        **file_record(EVENTLIST),
        "expected_sha256": EVENTLIST_SHA256,
        "row_count": len(rays),
        "event_id_contract": "exact integer sequence 0..37193",
        "energy_values_keV": sorted(energies),
        "injection_local_x_cm": INJECTION_X_CM,
        "maximum_abs_local_x_residual_cm": max(local_x_offsets),
        "maximum_direction_norm_error": max(direction_norm_errors),
    }


def verify_geometry() -> dict[str, Any]:
    if not GEOMETRY.is_file() or not MANIFEST.is_file():
        raise AuditError("small-aperture geometry or manifest is missing")
    geometry_record = file_record(GEOMETRY)
    if geometry_record["sha256"] != GEOMETRY_SHA256:
        raise AuditError(
            f"small-aperture geometry SHA-256 mismatch: {geometry_record['sha256']}"
        )
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("status") != MANIFEST_STATUS:
        raise AuditError(f"small-aperture manifest is not {MANIFEST_STATUS}")
    if (
        manifest.get("outputs", {})
        .get(GEOMETRY.name, {})
        .get("sha256")
        != GEOMETRY_SHA256
    ):
        raise AuditError("manifest does not bind the locked geometry SHA-256")
    contract = manifest.get("aperture_contract", {})
    expected_contract = {
        "new_active_bgo_square_opening_cm": 3.796,
        "perforated_grid_square_cm": 3.796,
        "central_grid_pitch_cm": PITCH_CM,
        "central_grid_web_cm": 2.0 * WEB_HALF_CM,
        "central_grid_w_depth_cm": 2.0 * GRID_W_HALF_DEPTH_CM,
    }
    for key, expected in expected_contract.items():
        if not math.isclose(float(contract.get(key, math.nan)), expected, abs_tol=1.0e-12):
            raise AuditError(f"manifest aperture contract drift for {key}")
    return {
        "geometry": geometry_record,
        "expected_geometry_sha256": GEOMETRY_SHA256,
        "manifest": file_record(MANIFEST),
        "manifest_status": manifest["status"],
        "aperture_contract": contract,
    }


def point_at_x(ray: Ray, x_cm: float) -> tuple[float, float]:
    distance = (x_cm - ray.x) / ray.dx
    y = ray.y + distance * ray.dy - APERTURE_CENTER_Y_CM
    z = ray.z + distance * ray.dz - APERTURE_CENTER_Z_CM
    return y, z


def plane_summary(rays: list[Ray], x_cm: float) -> dict[str, Any]:
    points = [(ray.event_id, *point_at_x(ray, x_cm)) for ray in rays]
    radii = [math.hypot(y, z) for _, y, z in points]
    linf = [max(abs(y), abs(z)) for _, y, z in points]
    worst_index = max(range(len(points)), key=lambda index: linf[index])
    radial_index = max(range(len(points)), key=lambda index: radii[index])
    return {
        "local_x_cm": x_cm,
        "y_range_cm": [min(y for _, y, _ in points), max(y for _, y, _ in points)],
        "z_relative_range_cm": [
            min(z for _, _, z in points),
            max(z for _, _, z in points),
        ],
        "r99_nearest_rank_cm": nearest_rank(radii, 0.99),
        "maximum_radius_cm": radii[radial_index],
        "maximum_radius_event_id": points[radial_index][0],
        "maximum_square_norm_cm": linf[worst_index],
        "maximum_square_norm_event_id": points[worst_index][0],
        "minimum_square_edge_margin_cm": APERTURE_HALF_CM - linf[worst_index],
        "minimum_square_edge_margin_mm": 10.0 * (APERTURE_HALF_CM - linf[worst_index]),
        "minimum_circular_edge_margin_cm": APERTURE_HALF_CM - radii[radial_index],
        "inside_square_count": sum(value <= APERTURE_HALF_CM for value in linf),
        "total_count": len(points),
    }


def corridor_summary(rays: list[Ray], x_low: float, x_high: float) -> dict[str, Any]:
    if x_high <= x_low:
        raise AuditError("corridor endpoints are reversed")
    worst_square: tuple[float, int] = (-math.inf, -1)
    worst_radius: tuple[float, int] = (-math.inf, -1)
    inside = 0
    for ray in rays:
        endpoints = (point_at_x(ray, x_low), point_at_x(ray, x_high))
        # Absolute value and Euclidean norm are convex along a straight segment,
        # so their maxima over the corridor occur at one of its endpoints.
        ray_square = max(max(abs(y), abs(z)) for y, z in endpoints)
        ray_radius = max(math.hypot(y, z) for y, z in endpoints)
        if ray_square <= APERTURE_HALF_CM:
            inside += 1
        if ray_square > worst_square[0]:
            worst_square = (ray_square, ray.event_id)
        if ray_radius > worst_radius[0]:
            worst_radius = (ray_radius, ray.event_id)
    return {
        "local_x_interval_cm": [x_low, x_high],
        "inside_square_for_entire_interval_count": inside,
        "total_count": len(rays),
        "maximum_square_norm_cm": worst_square[0],
        "maximum_square_norm_event_id": worst_square[1],
        "minimum_square_edge_margin_cm": APERTURE_HALF_CM - worst_square[0],
        "minimum_square_edge_margin_mm": 10.0 * (APERTURE_HALF_CM - worst_square[0]),
        "maximum_endpoint_radius_cm": worst_radius[0],
        "maximum_endpoint_radius_event_id": worst_radius[1],
        "minimum_circular_edge_margin_cm": APERTURE_HALF_CM - worst_radius[0],
        "front_plane": plane_summary(rays, x_low),
        "rear_plane": plane_summary(rays, x_high),
    }


def linear_coefficients(ray: Ray, coordinate: str) -> tuple[float, float]:
    if coordinate == "y":
        slope = ray.dy / ray.dx
        intercept = ray.y - slope * ray.x - APERTURE_CENTER_Y_CM
    elif coordinate == "z":
        slope = ray.dz / ray.dx
        intercept = ray.z - slope * ray.x - APERTURE_CENTER_Z_CM
    else:
        raise AuditError(f"unknown coordinate: {coordinate}")
    return intercept, slope


def clip_linear_band(
    intercept: float,
    slope: float,
    band_low: float,
    band_high: float,
    x_low: float,
    x_high: float,
) -> tuple[float, float] | None:
    """Clip an x interval to band_low <= intercept+slope*x <= band_high."""
    if abs(slope) < 1.0e-15:
        return (x_low, x_high) if band_low <= intercept <= band_high else None
    crossing_a = (band_low - intercept) / slope
    crossing_b = (band_high - intercept) / slope
    clipped_low = max(x_low, min(crossing_a, crossing_b))
    clipped_high = min(x_high, max(crossing_a, crossing_b))
    if clipped_low <= clipped_high:
        return clipped_low, clipped_high
    return None


def ray_web_contacts(ray: Ray, x_low: float, x_high: float) -> tuple[bool, bool]:
    y_intercept, y_slope = linear_coefficients(ray, "y")
    z_intercept, z_slope = linear_coefficients(ray, "z")

    horizontal = False
    for center in WEB_CENTERS_CM:
        interval = clip_linear_band(
            z_intercept,
            z_slope,
            center - WEB_HALF_CM,
            center + WEB_HALF_CM,
            x_low,
            x_high,
        )
        if interval is not None and clip_linear_band(
            y_intercept,
            y_slope,
            -HORIZONTAL_HALF_SPAN_Y_CM,
            HORIZONTAL_HALF_SPAN_Y_CM,
            *interval,
        ) is not None:
            horizontal = True
            break

    vertical = False
    for center_y in WEB_CENTERS_CM:
        y_interval = clip_linear_band(
            y_intercept,
            y_slope,
            center_y - WEB_HALF_CM,
            center_y + WEB_HALF_CM,
            x_low,
            x_high,
        )
        if y_interval is None:
            continue
        for center_z, half_height in VERTICAL_SEGMENTS_CM:
            if clip_linear_band(
                z_intercept,
                z_slope,
                center_z - half_height,
                center_z + half_height,
                *y_interval,
            ) is not None:
                vertical = True
                break
        if vertical:
            break
    return horizontal, vertical


def center_plane_web_contact(ray: Ray) -> bool:
    y, z = point_at_x(ray, GRID_CENTER_X_CM)
    horizontal = (
        abs(y) <= HORIZONTAL_HALF_SPAN_Y_CM
        and any(abs(z - center) <= WEB_HALF_CM for center in WEB_CENTERS_CM)
    )
    vertical = (
        any(abs(y - center) <= WEB_HALF_CM for center in WEB_CENTERS_CM)
        and any(
            abs(z - center) <= half_height
            for center, half_height in VERTICAL_SEGMENTS_CM
        )
    )
    return horizontal or vertical


def web_estimate(rays: list[Ray]) -> dict[str, Any]:
    x_low = GRID_CENTER_X_CM - GRID_W_HALF_DEPTH_CM
    x_high = GRID_CENTER_X_CM + GRID_W_HALF_DEPTH_CM
    categories = {
        "direct_clear": 0,
        "horizontal_only_contact": 0,
        "vertical_only_contact": 0,
        "both_horizontal_and_vertical_contact": 0,
    }
    center_contacts = 0
    for ray in rays:
        horizontal, vertical = ray_web_contacts(ray, x_low, x_high)
        if horizontal and vertical:
            categories["both_horizontal_and_vertical_contact"] += 1
        elif horizontal:
            categories["horizontal_only_contact"] += 1
        elif vertical:
            categories["vertical_only_contact"] += 1
        else:
            categories["direct_clear"] += 1
        center_contacts += int(center_plane_web_contact(ray))

    direct_clear = categories["direct_clear"]
    full_depth_contacts = len(rays) - direct_clear
    center_clear = len(rays) - center_contacts
    return {
        "method": (
            "Exact straight-ray intersections with the 24 horizontal and 600 segmented "
            "vertical W-bar boxes over the 0.798 cm W depth."
        ),
        "full_w_depth_local_x_interval_cm": [x_low, x_high],
        "full_depth_categories": categories,
        "full_depth_any_w_web_contact_count": full_depth_contacts,
        "full_depth_any_w_web_contact_fraction": full_depth_contacts / len(rays),
        "full_depth_direct_clear_count": direct_clear,
        "full_depth_direct_clear_fraction": direct_clear / len(rays),
        "center_plane_w_web_contact_count": center_contacts,
        "center_plane_w_web_contact_fraction": center_contacts / len(rays),
        "center_plane_direct_clear_count": center_clear,
        "center_plane_direct_clear_fraction": center_clear / len(rays),
        "finite_grid_normal_open_fraction_from_manifest": 12.158848 / 3.796**2,
        "interpretation": (
            "Geometric estimate only. A web contact is not an absorbed event, and a direct-clear "
            "ray is not necessarily a selected TES event. Tungsten attenuation/scattering and "
            "the selected signal effective area require a dedicated signal EventList replay."
        ),
    }


def direction_summary(rays: list[Ray]) -> dict[str, Any]:
    angles = [
        math.degrees(math.atan2(math.hypot(ray.dy, ray.dz), ray.dx))
        for ray in rays
    ]
    return {
        "median_off_axis_deg": nearest_rank(angles, 0.5),
        "p90_off_axis_deg": nearest_rank(angles, 0.9),
        "p99_off_axis_deg": nearest_rank(angles, 0.99),
        "maximum_off_axis_deg": max(angles),
    }


def main() -> int:
    report: dict[str, Any] = {
        "status": "FAIL",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "component_identity": "SH3_Chimney_DR_Assembly_OptV3_BGO_SmallAp_SG3Grid",
        "transport_launched": False,
        "scope": "Focused EventList straight-line clearance against the 3.796 cm square aperture.",
    }
    try:
        geometry = verify_geometry()
        rays, eventlist = parse_eventlist()
        grid_center = plane_summary(rays, GRID_CENTER_X_CM)
        grid_w_depth = corridor_summary(
            rays,
            GRID_CENTER_X_CM - GRID_W_HALF_DEPTH_CM,
            GRID_CENTER_X_CM + GRID_W_HALF_DEPTH_CM,
        )
        front_bgo_corridor = corridor_summary(
            rays,
            BGO_FRONT_CENTER_X_CM - BGO_FRONT_HALF_DEPTH_CM,
            BGO_FRONT_CENTER_X_CM + BGO_FRONT_HALF_DEPTH_CM,
        )
        microgrid = web_estimate(rays)
        checks = {
            "locked_eventlist_sha256_and_row_count": (
                eventlist["sha256"] == EVENTLIST_SHA256
                and eventlist["row_count"] == EVENTLIST_ROWS
            ),
            "locked_smallap_geometry_sha256": (
                geometry["geometry"]["sha256"] == GEOMETRY_SHA256
            ),
            "all_rays_inside_square_at_grid_center": (
                grid_center["inside_square_count"] == EVENTLIST_ROWS
                and grid_center["minimum_square_edge_margin_cm"] > 0.0
            ),
            "all_rays_inside_square_through_grid_w_depth": (
                grid_w_depth["inside_square_for_entire_interval_count"] == EVENTLIST_ROWS
                and grid_w_depth["minimum_square_edge_margin_cm"] > 0.0
            ),
            "all_rays_inside_square_through_full_front_bgo_depth": (
                front_bgo_corridor["inside_square_for_entire_interval_count"]
                == EVENTLIST_ROWS
                and front_bgo_corridor["minimum_square_edge_margin_cm"] > 0.0
            ),
            "microgrid_result_is_explicitly_non_transport": True,
            "signal_replay_is_explicitly_required": True,
        }
        report.update(
            {
                "status": STATUS_PASS if all(checks.values()) else "FAIL",
                "source_authority": eventlist,
                "geometry_authority": geometry,
                "coordinate_method": {
                    "world_to_instrument": (
                        "x_local=(x_world-z_world)/sqrt(2), y_local=y_world, "
                        "z_local=(x_world+z_world)/sqrt(2)"
                    ),
                    "projection": "linear propagation to fixed local-x planes",
                    "aperture_center_local_cm": [
                        GRID_CENTER_X_CM,
                        APERTURE_CENTER_Y_CM,
                        APERTURE_CENTER_Z_CM,
                    ],
                    "square_half_width_cm": APERTURE_HALF_CM,
                },
                "results": {
                    "grid_center": grid_center,
                    "grid_full_w_depth": grid_w_depth,
                    "full_front_bgo_region_tested_as_same_square_corridor": front_bgo_corridor,
                    "incident_direction": direction_summary(rays),
                    "microgrid_straight_ray_estimate": microgrid,
                },
                "checks": checks,
                "conclusion": {
                    "focused_bundle_envelope": (
                        "All 37,194 locked focused rays clear the 3.796 cm square at the grid "
                        "and across the full front-BGO depth under straight-line propagation."
                    ),
                    "microgrid": (
                        "The aperture edge does not clip the bundle, but the deep 25 x 25 W "
                        "microgrid is not signal-neutral. Its straight-ray web-contact estimate "
                        "cannot replace signal transport."
                    ),
                    "required_next_physics_step": (
                        "Replay this exact EventList through the small-aperture mass model before "
                        "using a signal effective area or Fmin for the variant."
                    ),
                },
                "not_claimed": [
                    "particle transport or detector response",
                    "tungsten absorption, transmission, or scattering probability",
                    "selected signal effective area, background, activation, or sensitivity",
                    "off-axis pointing or attitude-jitter acceptance beyond the locked EventList",
                ],
                "script": file_record(SCRIPT),
            }
        )
    except Exception as exc:
        report["exception"] = {"type": type(exc).__name__, "message": str(exc)}
    atomic_json(OUTPUT, report)
    print(json.dumps({"status": report["status"], "output": str(OUTPUT)}, indent=2))
    return 0 if report["status"] == STATUS_PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
