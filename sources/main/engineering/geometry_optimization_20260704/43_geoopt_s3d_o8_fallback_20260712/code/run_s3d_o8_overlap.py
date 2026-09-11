#!/usr/bin/env python3
"""Run the one-event Cosima load/overlap smoke for the isolated O8 package."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
WORK = Path(__file__).resolve().parents[1]
SHARED_RUNNER = (
    ROOT
    / "engineering/geometry_optimization_20260704"
    / "42_geoopt_s3d_lightweight_20260712/code/run_s3d_overlap.py"
)
STEM = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
sys.dont_write_bytecode = True


def load_shared_runner():
    spec = importlib.util.spec_from_file_location(
        "s3d_o8_shared_overlap_runner", SHARED_RUNNER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load shared runner: {SHARED_RUNNER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    shared = load_shared_runner()
    geometry = WORK / "geometry"
    data = WORK / "data"
    shared.WORK = WORK
    shared.GEOMETRY = geometry
    shared.DATA = data
    shared.VALIDATION = WORK / "validation"
    shared.SOURCE = geometry / "overlap_check_s3d_o8.source"
    shared.SETUP = geometry / f"{STEM}.geo.setup"
    shared.GEO = geometry / f"{STEM}.geo"
    shared.DET = geometry / f"{STEM}.det"
    shared.LOG = shared.VALIDATION / "cosima_overlap_s3d_o8.log"
    shared.SUMMARY = data / "cosima_overlap_s3d_o8_summary.json"
    return shared.main()


if __name__ == "__main__":
    raise SystemExit(main())
