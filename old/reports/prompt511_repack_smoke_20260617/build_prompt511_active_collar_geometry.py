#!/usr/bin/env python3
"""Build an active BGO collar variant from the prompt-511 W-liner repack."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "outputs/reports/prompt511_repack_smoke_20260617"
SRC_GEOM = WORK / "geometry_repack"
SRC_NAME = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_repack_r4p25_5p95"
OUT_GEOM = WORK / "geometry_active_collar_bgo"
OUT_NAME = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_active_bgo_collar_r4p25_5p95"
SRC_SETUP = SRC_GEOM / f"{SRC_NAME}.geo.setup"
OUT_SETUP = OUT_GEOM / f"{OUT_NAME}.geo.setup"
SOURCE_IN = WORK / "source_cards"
SOURCE_OUT = WORK / "source_cards_active_collar_bgo"
MANIFEST = WORK / "prompt511_active_collar_bgo_manifest.json"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def replace_geometry_names(text: str) -> str:
    return text.replace(SRC_NAME, OUT_NAME)


def replace_liner_volumes(text: str) -> tuple[str, list[dict[str, str]]]:
    """Replace W shadow liner volumes with active BGO collar volumes."""
    rows = []
    for old in sorted(set(re.findall(r"\b(Prompt511_Repack_W_Liner_z\d+_[ab])\b", text))):
        new = old.replace("Prompt511_Repack_W_Liner", "BGO_Active_Shield_Prompt511_Collar")
        text = text.replace(old, new)
        rows.append({"old": old, "new": new})
    text = re.sub(
        r"^(BGO_Active_Shield_Prompt511_Collar_z\d+_[ab]\.Material)\s+W\s*$",
        r"\1 BGO",
        text,
        flags=re.MULTILINE,
    )
    text = text.replace(
        "// Prompt-511 repack smoke: segmented W shadow liner.",
        "// Prompt-511 active-collar smoke: segmented BGO active veto collar.",
    )
    text = text.replace(
        "// This is a local design-smoke volume, not authority CAD.",
        "// This is a local active-veto design-smoke volume, not authority CAD.",
    )
    return text, rows


def build_geometry() -> dict[str, object]:
    if OUT_GEOM.exists():
        shutil.rmtree(OUT_GEOM)
    shutil.copytree(SRC_GEOM, OUT_GEOM)

    for old in (
        OUT_GEOM / f"{SRC_NAME}.geo.setup",
        OUT_GEOM / f"{SRC_NAME}.geo",
        OUT_GEOM / f"{SRC_NAME}.det",
    ):
        old.rename(OUT_GEOM / old.name.replace(SRC_NAME, OUT_NAME))

    setup = replace_geometry_names(OUT_SETUP.read_text(encoding="utf-8"))
    OUT_SETUP.write_text(setup, encoding="utf-8")

    geo_path = OUT_GEOM / f"{OUT_NAME}.geo"
    geo, rows = replace_liner_volumes(replace_geometry_names(geo_path.read_text(encoding="utf-8")))
    geo_path.write_text(geo, encoding="utf-8")

    det_path = OUT_GEOM / f"{OUT_NAME}.det"
    det_path.write_text(replace_geometry_names(det_path.read_text(encoding="utf-8")), encoding="utf-8")

    return {
        "geometry_setup": rel(OUT_SETUP),
        "geometry_geo": rel(geo_path),
        "geometry_det": rel(det_path),
        "collar_material": "BGO",
        "collar_active_veto_match": "volume names start with BGO_Active_Shield",
        "replaced_volumes": rows,
    }


def migrate_sources() -> dict[str, object]:
    if SOURCE_OUT.exists():
        shutil.rmtree(SOURCE_OUT)
    SOURCE_OUT.mkdir(parents=True)
    rows = []
    for src in sorted(SOURCE_IN.glob("Background_*_fullsphere20.source")):
        text = re.sub(r"^Geometry\s+.+$", f"Geometry {OUT_SETUP}", src.read_text(encoding="utf-8"), count=1, flags=re.MULTILINE)
        out = SOURCE_OUT / src.name
        out.write_text(text, encoding="utf-8")
        rows.append({"source": rel(out), "base_source": rel(src)})
    manifest = {
        "status": "PASS_PROMPT511_ACTIVE_COLLAR_BGO_SOURCE_CARDS",
        "source_dir": rel(SOURCE_OUT),
        "base_source_dir": rel(SOURCE_IN),
        "geometry_setup": rel(OUT_SETUP),
        "farfield_radius_cm": 60.0,
        "sources": rows,
    }
    (SOURCE_OUT / "source_migration_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def write_overlap_source() -> dict[str, str]:
    source = WORK / "overlap_active_collar_bgo.source"
    log = WORK / "overlap_active_collar_bgo.log"
    source.write_text(
        f"""Version                     1
Geometry                    {OUT_SETUP}
CheckForOverlaps            1000 0.0001
PhysicsListEM               LivermorePol
Run Minimum
Minimum.FileName            /tmp/prompt511_active_collar_bgo_overlap
Minimum.NEvents             1
Minimum.Source MinimumS
MinimumS.ParticleType       1
MinimumS.Beam               PointSource 0 0 0
MinimumS.Spectrum           Mono 511
MinimumS.Flux               1.0
""",
        encoding="utf-8",
    )
    return {"overlap_source": rel(source), "overlap_log": rel(log)}


def main() -> int:
    geometry = build_geometry()
    sources = migrate_sources()
    overlap = write_overlap_source()
    payload = {
        "status": "PASS_PROMPT511_ACTIVE_COLLAR_BGO_GEOMETRY_READY",
        "claim_level": "PROMPT511_ACTIVE_COLLAR_BGO_DESIGN_SMOKE_NO_RATE_AUTHORITY",
        "base_geometry": rel(SRC_SETUP),
        "geometry": geometry,
        "sources": sources,
        "overlap": overlap,
    }
    MANIFEST.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "manifest": rel(MANIFEST)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
