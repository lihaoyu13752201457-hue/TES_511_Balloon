#!/usr/bin/env python3
"""Lightweight checks for Compton/FoV back-projection geometry."""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-newgeo")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code" / "tools"))

from make_day15_report_ADR import BE_WINDOW_Z_CM, EventHit, classify_hit2, compton_cos_theta


def on_axis_two_hit_event(theta_deg: float = 60.0) -> list[EventHit]:
    """Construct a two-hit event whose true incoming ray passes through Be-window center."""
    theta = math.radians(theta_deg)
    total_e = 511.0
    scattered_e = total_e / (2.0 - math.cos(theta))
    recoil_e = total_e - scattered_e

    first = EventHit(x=0.0, y=0.0, z=6.0, e=recoil_e, pixel_uid="synthetic_first", layer=0)
    scattered_dir = (math.sin(theta), 0.0, -math.cos(theta))
    second = EventHit(
        x=first.x + scattered_dir[0],
        y=first.y + scattered_dir[1],
        z=first.z + scattered_dir[2],
        e=scattered_e,
        pixel_uid="synthetic_second",
        layer=1,
    )
    assert math.isclose(compton_cos_theta(first.e, second.e), math.cos(theta), rel_tol=1.0e-12)
    assert first.z < BE_WINDOW_Z_CM
    return [first, second]


def main() -> int:
    cls = classify_hit2(on_axis_two_hit_event())
    if cls != "keep":
        raise AssertionError(f"Expected Be-window-center synthetic event to keep, got {cls!r}")
    print("PASS compton_fov_geometry")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
