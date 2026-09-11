#!/usr/bin/env python3
"""Prepare local raster assets for the compact SH3 HTML slide deck."""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "outputs" / "figures"
ASSETS = ROOT / "outputs" / "slides" / "assets"
LANCZOS = getattr(Image, "Resampling", Image).LANCZOS


def copy_or_resize(source_name: str, target_name: str, max_dimension: int | None) -> None:
    source = FIGURES / source_name
    target = ASSETS / target_name
    if max_dimension is None:
        shutil.copy2(source, target)
        return

    with Image.open(source) as image:
        width, height = image.size
        scale = min(1.0, max_dimension / max(width, height))
        output_size = (round(width * scale), round(height * scale))
        resized = image.convert("RGB").resize(output_size, LANCZOS)
        resized.save(target, format="PNG", optimize=True)


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    copy_or_resize(
        "sh3_megalib_si_depositions_six_layers.png",
        "megalib_si_depositions.png",
        1200,
    )
    copy_or_resize(
        "sh3_all86_six_layer_matplotlib_map.png",
        "all86_g4cmp_six_layers.png",
        1200,
    )
    copy_or_resize(
        "sh3_candidate_C_six_layer_matplotlib_map.png",
        "candidate_c_six_layers.png",
        None,
    )
    copy_or_resize(
        "sh3_tes_fenics_pulse_comparison.png",
        "tes_pulse_comparison.png",
        None,
    )
    copy_or_resize(
        "sh3_tes_two_node_pulse_comparison.png",
        "tes_two_node_pulse_comparison.png",
        None,
    )
    copy_or_resize(
        "sh3_g4cmp_phonon_transport_physics.png",
        "g4cmp_phonon_transport_physics.png",
        None,
    )
    for path in sorted(ASSETS.glob("*.png")):
        with Image.open(path) as image:
            print(f"{path.relative_to(ROOT)}\t{image.width}x{image.height}\t{path.stat().st_size} bytes")


if __name__ == "__main__":
    main()
