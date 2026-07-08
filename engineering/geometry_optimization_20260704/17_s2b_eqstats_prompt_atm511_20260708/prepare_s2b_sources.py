#!/usr/bin/env python3
"""Prepare S2b equal-stat source cards from the retained S1 source cards."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
SOURCE_DIR = WORK / "source_cards"
OLD_GEOMETRY = (
    "engineering/geometry_optimization_20260704/01_geo_opt_s1_bottomw_b4c/geometry/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
NEW_GEOMETRY = (
    "engineering/geometry_optimization_20260704/16_geoopt_s2b_cryo_shell_45deg_20260708/geometry/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)


def main() -> int:
    replacements = 0
    for path in sorted(SOURCE_DIR.glob("Background_*_fullsphere20.source")):
        text = path.read_text(encoding="utf-8")
        if OLD_GEOMETRY not in text and NEW_GEOMETRY not in text:
            raise RuntimeError(f"old geometry string not found in {path}")
        text = text.replace(OLD_GEOMETRY, NEW_GEOMETRY)
        path.write_text(text, encoding="utf-8")
        replacements += 1

    manifest_path = SOURCE_DIR / "source_migration_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = json.loads(json.dumps(manifest).replace(OLD_GEOMETRY, NEW_GEOMETRY))
    manifest.update(
        {
            "status": "PASS_S2B_EQSTATS_SOURCE_COPY_PREPARED",
            "geometry_setup": NEW_GEOMETRY,
            "geometry_status": "S2b 45-degree cryo-shell barrel; BPE 20 mm and plastic skin 10 mm; moved R60 source sphere",
            "farfield_radius_cm": 60.0,
            "surrounding_sphere": "SurroundingSphere 60 5 0 9 60",
            "source_parent": "engineering/geometry_optimization_20260704/02_fullstat_prompt_delay_20260706/source_cards",
            "prepared_for": "eplus,n equal-stat prompt plus atmospheric 511 sidecar comparison against S1",
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "status": "PASS",
                "source_cards": replacements,
                "geometry_setup": NEW_GEOMETRY,
                "source_dir": str(SOURCE_DIR.relative_to(ROOT)),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
