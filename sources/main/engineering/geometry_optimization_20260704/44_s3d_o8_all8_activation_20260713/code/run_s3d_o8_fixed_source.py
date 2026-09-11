#!/usr/bin/env python3
"""Run the shared ground-state fixer with the S3d-O8 volume map."""

from __future__ import annotations

import glob
import importlib.util
import sys
from pathlib import Path

from s3d_o8_volume_map import (
    canonicalize,
    copy_map_from_geometry,
    configure,
    logical_volumes_from_dat,
)


ROOT = Path(__file__).resolve().parents[4]
TOOL = ROOT / "code/tools/build_fixed_delay_source.py"


def argument_value(flag: str) -> str:
    try:
        return sys.argv[sys.argv.index(flag) + 1]
    except (ValueError, IndexError) as exc:
        raise SystemExit(f"required wrapper argument is missing: {flag}") from exc


def main() -> int:
    dat_files = [Path(value) for value in sorted(glob.glob(argument_value("--dat-glob")))]
    if not dat_files:
        raise SystemExit("S3d-O8 wrapper found no DAT files")
    geometry_setup = Path(argument_value("--geometry"))
    if not geometry_setup.is_absolute():
        geometry_setup = ROOT / geometry_setup
    configure(
        logical_volumes_from_dat(dat_files),
        copy_map_from_geometry(geometry_setup.resolve().with_suffix("")),
    )
    spec = importlib.util.spec_from_file_location("s3d_o8_fixed_source_shared", TOOL)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {TOOL}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.canon_vn = canonicalize
    module.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
