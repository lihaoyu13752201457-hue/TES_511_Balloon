#!/usr/bin/env python3
"""Find a simple DR-to-top-BGO annihilation-partner sightline.

This is a read-only geometry query.  It samples rays that are exactly opposite
to a photon from the observed event-19932 annihilation point to a physically
allowed central TES target.  It does not run particle transport.
"""

from __future__ import annotations

import csv
import io
import math
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent / "escape_chimney_scan.csv"
SETUP = Path(
    "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/"
    "geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/"
    "geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
TRACER = (
    ROOT
    / "engineering/s3d_o8_loop_engineering_20260814/agents/prompt/"
    "trace_true_geometry_rays"
)

# Observed event-19932 annihilation position, in world coordinates.
SOURCE_WORLD = (-0.23969, 0.87711, 2.32687)
SQRT2 = math.sqrt(2.0)
TOP_Z_LOCAL = 40.9
CHANNEL_RADIUS_CM = 1.25

TES_LAYER_X_LOCAL = (-3.0, -1.8, -0.6, 0.6)  # frozen deepest <= L3
TES_CENTER_Z_LOCAL = -5.2
TES_TRANSVERSE_RADIUS_CM = 1.35
GRID_CM = tuple(-1.2 + 0.3 * i for i in range(9))

INTENDED_PLATE_VOLUMES = {
    "ColdPlate_CP_100mK_intercept",
    "ColdPlate_Still_0p7K",
    "ColdPlate_4K",
    "ColdPlate_60K",
    "Plate_300K_Top_Service_Lid",
}
IGNORE_VOLUMES = {
    "InstrumentFrame",
    "WorldVolume",
    "DR_MixingChamber_Cu",  # source host; the chimney begins at its surface
}

TOP_SERVICE_RELIEFS = (
    ("GasReturn_A", 5.0, 3.2, 1.95),
    ("PumpFill_B", 7.4, -2.8, 1.69),
    ("Vacuum_C", -4.5, 6.5, 1.29),
    ("Micro_01", -2.4, 8.8, 0.95),
    ("Micro_02", -0.2, 8.9, 0.95),
    ("Micro_03", 2.0, 8.8, 0.95),
    ("Micro_04", 4.2, 8.6, 0.95),
    ("Micro_05", 6.4, 8.3, 0.95),
    ("Micro_06", -1.3, 10.9, 0.95),
    ("Micro_07", 0.9, 11.1, 0.95),
    ("Micro_08", 3.1, 10.9, 0.95),
    ("Micro_09", 5.3, 10.5, 0.95),
)


def world_to_local(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = vector
    return ((x - z) / SQRT2, y, (x + z) / SQRT2)


def local_to_world(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = vector
    return ((x + z) / SQRT2, y, (-x + z) / SQRT2)


def unit(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    norm = math.sqrt(sum(value * value for value in vector))
    return tuple(value / norm for value in vector)


def point_at_local_z(
    origin: tuple[float, float, float],
    direction: tuple[float, float, float],
    z: float,
) -> tuple[float, float, float]:
    scale = (z - origin[2]) / direction[2]
    return tuple(origin[i] + scale * direction[i] for i in range(3))


def main() -> None:
    source_local = world_to_local(SOURCE_WORLD)
    rays: list[dict[str, object]] = []
    feed: list[str] = []
    ray_index = 0
    for layer, target_x in enumerate(TES_LAYER_X_LOCAL):
        for target_y in GRID_CM:
            for target_z_offset in GRID_CM:
                if math.hypot(target_y, target_z_offset) > TES_TRANSVERSE_RADIUS_CM:
                    continue
                target = (
                    target_x,
                    target_y,
                    TES_CENTER_Z_LOCAL + target_z_offset,
                )
                direction_local = unit(tuple(source_local[i] - target[i] for i in range(3)))
                if direction_local[2] <= 0:
                    continue
                top = point_at_local_z(source_local, direction_local, TOP_Z_LOCAL)
                top_radius = math.hypot(top[0], top[1])
                if top_radius + CHANNEL_RADIUS_CM >= 25.2:
                    continue
                service_clearance = min(
                    math.hypot(top[0] - x, top[1] - y) - relief_radius
                    for _, x, y, relief_radius in TOP_SERVICE_RELIEFS
                )
                if service_clearance <= CHANNEL_RADIUS_CM:
                    continue
                direction_world = local_to_world(direction_local)
                t_top = (TOP_Z_LOCAL - source_local[2]) / direction_local[2]
                ray_id = f"c{ray_index:04d}"
                ray_index += 1
                feed.append(
                    " ".join(
                        [
                            ray_id,
                            *(f"{value:.12g}" for value in SOURCE_WORLD),
                            *(f"{value:.12g}" for value in direction_world),
                            f"{t_top:.12g}",
                            "0.01",
                        ]
                    )
                )
                rays.append(
                    {
                        "ray_id": ray_id,
                        "layer": layer,
                        "target_x_local_cm": target[0],
                        "target_y_local_cm": target[1],
                        "target_z_local_cm": target[2],
                        "dir_x_local": direction_local[0],
                        "dir_y_local": direction_local[1],
                        "dir_z_local": direction_local[2],
                        "top_x_local_cm": top[0],
                        "top_y_local_cm": top[1],
                        "top_r_local_cm": top_radius,
                        "top_service_edge_clearance_cm": service_clearance,
                    }
                )

    result = subprocess.run(
        [str(TRACER), str(SETUP)],
        input="\n".join(feed) + "\n",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    lines = result.stdout.splitlines()
    header_index = next(i for i, line in enumerate(lines) if line.startswith("ray_id,"))
    segments = list(csv.DictReader(io.StringIO("\n".join(lines[header_index:]))))
    by_ray: dict[str, list[dict[str, str]]] = {}
    for segment in segments:
        by_ray.setdefault(segment["ray_id"], []).append(segment)

    output: list[dict[str, object]] = []
    plate_z = {
        "CP": 5.0,
        "Still": 11.0,
        "4K": 20.0,
        "60K": 29.0,
        "300K": 38.0,
    }
    for ray in rays:
        ray_segments = by_ray.get(str(ray["ray_id"]), [])
        extra: dict[str, float] = {}
        for segment in ray_segments:
            volume = segment["deepest_volume"]
            if volume in IGNORE_VOLUMES or volume in INTENDED_PLATE_VOLUMES:
                continue
            extra[volume] = extra.get(volume, 0.0) + float(segment["path_cm"])
        direction = (
            float(ray["dir_x_local"]),
            float(ray["dir_y_local"]),
            float(ray["dir_z_local"]),
        )
        row = {
            **ray,
            "extra_blocker_count": len(extra),
            "extra_blocker_path_cm": sum(extra.values()),
            "extra_blockers": "|".join(
                f"{name}:{path:.4f}" for name, path in sorted(extra.items())
            ),
        }
        for label, z in plate_z.items():
            point = point_at_local_z(source_local, direction, z)
            row[f"hole_{label}_x_local_cm"] = point[0]
            row[f"hole_{label}_y_local_cm"] = point[1]
        output.append(row)

    output.sort(
        key=lambda row: (
            int(row["extra_blocker_count"]),
            float(row["extra_blocker_path_cm"]),
            float(row["top_r_local_cm"]),
        )
    )
    with OUT.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)

    best = output[0]
    print(f"sampled_rays={len(output)}")
    print(f"best_ray={best['ray_id']}")
    print(f"best_target=L{best['layer']} ({best['target_x_local_cm']},{best['target_y_local_cm']},{best['target_z_local_cm']})")
    print(f"best_top=({best['top_x_local_cm']},{best['top_y_local_cm']}) r={best['top_r_local_cm']}")
    print(f"best_extra_blockers={best['extra_blockers'] or 'NONE'}")
    print(f"output={OUT}")


if __name__ == "__main__":
    main()
