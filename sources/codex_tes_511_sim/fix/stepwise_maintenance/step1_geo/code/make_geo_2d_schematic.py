#!/usr/bin/env python3
"""Regenerate only the step1 geometry 2D schematic."""

from __future__ import annotations

from build_step1_geo import (
    GEOMETRY_FILES,
    OUTPUT_DIR,
    build_instances,
    load_bounds,
    make_2d_schematic,
    parse_geometry,
)


def main() -> None:
    volumes, objects = parse_geometry(GEOMETRY_FILES)
    instances = build_instances(volumes, objects)
    make_2d_schematic(OUTPUT_DIR / "geometry_schematic_2d.png", volumes, instances, load_bounds())


if __name__ == "__main__":
    main()
