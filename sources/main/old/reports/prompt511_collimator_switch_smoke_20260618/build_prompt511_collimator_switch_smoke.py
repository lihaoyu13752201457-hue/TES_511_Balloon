#!/usr/bin/env python3
"""Build current-geometry collimator-off prompt-511 smoke inputs."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "outputs/reports/prompt511_collimator_switch_smoke_20260618"
RUNS = WORK / "runs"
BASE_GEO_DIR = ROOT / "outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
BASE_GEO_NAME = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
BASE_SETUP = BASE_GEO_DIR / f"{BASE_GEO_NAME}.geo.setup"
SOURCE_BASE_DIR = ROOT / "config/megalib_sources_fullsphere20_v3p5_centerfinger_tilt45"
SOURCE_OUT_DIR = WORK / "source_cards"
GEOM_OUT_DIR = WORK / "geometry_collimator_off"
NEW_GEO_NAME = f"{BASE_GEO_NAME}_collimator_off"
NEW_SETUP = GEOM_OUT_DIR / f"{NEW_GEO_NAME}.geo.setup"
OVERLAP_SOURCE = WORK / "overlap_collimator_off.source"
OVERLAP_LOG = WORK / "overlap_collimator_off.log"
MANIFEST = WORK / "prompt511_collimator_switch_smoke_manifest.json"

GEOMETRY_RE = re.compile(r"^Geometry\s+.+$", re.MULTILINE)
EVENTS_RE = re.compile(r"^(?P<run>\S+)\.Events\s+\d+\s*$", re.MULTILINE)

COLLIMATOR_VOLUMES = [
    "W_Side_Aperture_Sleeve_collimator_ZP_panel",
    "W_Side_Aperture_Sleeve_collimator_ZM_panel",
    "W_Side_Aperture_Sleeve_collimator_YP_panel",
    "W_Side_Aperture_Sleeve_collimator_YM_panel",
]


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def replace_prop(text: str, volume: str, prop: str, value: str) -> str:
    pattern = re.compile(rf"^{re.escape(volume)}\.{re.escape(prop)}\s+.*$", re.MULTILINE)
    repl = f"{volume}.{prop} {value}"
    text, n = pattern.subn(repl, text, count=1)
    if n != 1:
        raise RuntimeError(f"failed to replace {volume}.{prop}")
    return text


def rewrite_setup(setup_path: Path) -> None:
    text = setup_path.read_text(encoding="utf-8")
    text = text.replace(f"Name {BASE_GEO_NAME}", f"Name {NEW_GEO_NAME}")
    text = text.replace(f"Include {BASE_GEO_NAME}.geo", f"Include {NEW_GEO_NAME}.geo")
    text = text.replace(f"Include {BASE_GEO_NAME}.det", f"Include {NEW_GEO_NAME}.det")
    setup_path.write_text(text, encoding="utf-8")


def build_geometry() -> dict[str, Any]:
    if GEOM_OUT_DIR.exists():
        shutil.rmtree(GEOM_OUT_DIR)
    shutil.copytree(BASE_GEO_DIR, GEOM_OUT_DIR)
    old_geo = GEOM_OUT_DIR / f"{BASE_GEO_NAME}.geo"
    old_setup = GEOM_OUT_DIR / f"{BASE_GEO_NAME}.geo.setup"
    old_det = GEOM_OUT_DIR / f"{BASE_GEO_NAME}.det"
    new_geo = GEOM_OUT_DIR / f"{NEW_GEO_NAME}.geo"
    new_setup = GEOM_OUT_DIR / f"{NEW_GEO_NAME}.geo.setup"
    new_det = GEOM_OUT_DIR / f"{NEW_GEO_NAME}.det"
    old_geo.rename(new_geo)
    old_setup.rename(new_setup)
    old_det.rename(new_det)
    rewrite_setup(new_setup)

    text = new_geo.read_text(encoding="utf-8")
    for volume in COLLIMATOR_VOLUMES:
        text = replace_prop(text, volume, "Material", "Vacuum")
        text = replace_prop(text, volume, "Visibility", "0")
    new_geo.write_text(text, encoding="utf-8")
    return {
        "geometry_setup": rel(new_setup),
        "geometry_geo": rel(new_geo),
        "geometry_det": rel(new_det),
        "collimator_off_volumes": COLLIMATOR_VOLUMES,
    }


def migrate_sources(events_override: int | None = None) -> dict[str, Any]:
    if SOURCE_OUT_DIR.exists():
        shutil.rmtree(SOURCE_OUT_DIR)
    SOURCE_OUT_DIR.mkdir(parents=True)
    rows = []
    for src in sorted(SOURCE_BASE_DIR.glob("Background_*_fullsphere20.source")):
        text = src.read_text(encoding="utf-8", errors="replace")
        text = GEOMETRY_RE.sub(f"Geometry {NEW_SETUP}", text, count=1)
        if events_override is not None:
            text = EVENTS_RE.sub(lambda m: f"{m.group('run')}.Events {int(events_override)}", text, count=1)
        out = SOURCE_OUT_DIR / src.name
        out.write_text(text, encoding="utf-8")
        rows.append({"source": rel(out), "base_source": rel(src)})
    return {
        "status": "PASS_COLLIMATOR_OFF_SOURCE_CARDS",
        "source_dir": rel(SOURCE_OUT_DIR),
        "base_source_dir": rel(SOURCE_BASE_DIR),
        "geometry_setup": rel(NEW_SETUP),
        "sources": rows,
    }


def write_overlap_source() -> dict[str, str]:
    text = f"""Version                     1
Geometry                    {NEW_SETUP}
CheckForOverlaps            1000 0.0001
PhysicsListEM               LivermorePol
Run Minimum
Minimum.FileName            /tmp/prompt511_collimator_off_overlap
Minimum.NEvents             1
Minimum.Source MinimumS
MinimumS.ParticleType       1
MinimumS.Beam               PointSource 0 0 0
MinimumS.Spectrum           Mono 511
MinimumS.Flux               1.0
"""
    OVERLAP_SOURCE.write_text(text, encoding="utf-8")
    return {"overlap_source": rel(OVERLAP_SOURCE), "overlap_log": rel(OVERLAP_LOG)}


def build_inputs(args: argparse.Namespace) -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    RUNS.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "PASS_PROMPT511_COLLIMATOR_SWITCH_SMOKE_INPUTS",
        "constraints": rel(WORK / "CONSTRAINTS.md"),
        "base_geometry": rel(BASE_SETUP),
        "geometry": build_geometry(),
        "source_cards": migrate_sources(args.events_override),
        "overlap": write_overlap_source(),
        "claim_level": "diagnostic collimator-off prompt-eplus smoke; not authority",
    }
    MANIFEST.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "manifest": rel(MANIFEST)}, indent=2, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    build = sub.add_parser("build-inputs")
    build.add_argument("--events-override", type=int, default=None)
    args = parser.parse_args()
    if args.cmd == "build-inputs":
        build_inputs(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
