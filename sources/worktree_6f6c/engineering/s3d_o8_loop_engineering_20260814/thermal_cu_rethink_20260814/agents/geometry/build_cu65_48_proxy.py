#!/usr/bin/env python3
"""Build a minimal 48-volume elemental-Cu -> same-density Cu-65 proxy.

Only material references on the frozen 48-volume cold-core whitelist change.
No dimensions, placements, detector mappings, CuNi, or other Copper volumes
are altered.  This builder does not launch particle transport.
"""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


SOURCE_DIR = Path(
    "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/"
    "geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry"
)
SOURCE_STEM = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
OUTPUT_STEM = "S3D_O8_coldcore48_Cu65_same_density_proxy"
HERE = Path(__file__).resolve().parent
WHITELIST = (
    HERE.parents[2]
    / "reconsideration_20260814/agents/geometry/CU_TO_AL_WHITELIST.txt"
)


def read_whitelist() -> set[str]:
    names = {
        line.strip()
        for line in WHITELIST.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    if len(names) != 48:
        raise RuntimeError(f"expected 48 frozen volumes, got {len(names)}")
    return names


def build(output_dir: Path) -> Path:
    whitelist = read_whitelist()
    source_geo = SOURCE_DIR / f"{SOURCE_STEM}.geo"
    text = source_geo.read_text()
    current_volume: str | None = None
    changed: set[str] = set()
    lines: list[str] = []
    volume_re = re.compile(r"^Volume (\S+)$")
    for line in text.splitlines():
        match = volume_re.match(line)
        if match:
            current_volume = match.group(1)
        if current_volume in whitelist and line == f"{current_volume}.Material Copper":
            line = f"{current_volume}.Material Copper65"
            changed.add(current_volume)
        lines.append(line)
    if changed != whitelist:
        raise RuntimeError(
            f"material-scope mismatch: missing={sorted(whitelist - changed)} "
            f"extra={sorted(changed - whitelist)}"
        )
    candidate_geo = "\n".join(lines) + "\n"

    materials = (SOURCE_DIR / "Materials_DEMO2_DR_v3p5.geo").read_text()
    if "Material Copper65" in materials:
        raise RuntimeError("source materials unexpectedly already define Copper65")
    materials += (
        "\n# BEGIN S3D_O8_COLDCORE48_CU65_PROXY\n"
        "# Numeric ComponentByAtoms form: atomic mass [g/mole], Z, atom count.\n"
        "Material Copper65\n"
        "Copper65.Density 8.954\n"
        "Copper65.ComponentByAtoms 65 29 1\n"
        "# END S3D_O8_COLDCORE48_CU65_PROXY\n"
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{OUTPUT_STEM}.geo").write_text(candidate_geo)
    (output_dir / "Materials_DEMO2_DR_v3p5.geo").write_text(materials)
    shutil.copy2(
        SOURCE_DIR / f"Intro_{SOURCE_STEM}.geo",
        output_dir / f"Intro_{SOURCE_STEM}.geo",
    )
    shutil.copy2(SOURCE_DIR / f"{SOURCE_STEM}.det", output_dir / f"{OUTPUT_STEM}.det")
    setup = (
        f"Name {OUTPUT_STEM}\n"
        "Version 1\n"
        f"Include {OUTPUT_STEM}.geo\n"
        f"Include {OUTPUT_STEM}.det\n"
        "SurroundingSphere 60 5 0 9 60\n"
    )
    output_setup = output_dir / f"{OUTPUT_STEM}.geo.setup"
    output_setup.write_text(setup)
    manifest = output_dir / "CU65_48_VOLUME_MANIFEST.txt"
    manifest.write_text("\n".join(sorted(changed)) + "\n")
    return output_setup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    setup = build(args.output_dir)
    print(f"output_setup={setup}")
    print("changed_volume_count=48")
    print("density_g_cm3=8.954")
    print("component_by_atoms=65,29,1")


if __name__ == "__main__":
    main()
