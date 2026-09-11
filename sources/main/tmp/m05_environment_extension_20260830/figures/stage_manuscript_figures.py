#!/usr/bin/env python3
"""Stage exactly the PDF figures referenced by the bilingual M05 manuscript."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path


HERE = Path(__file__).resolve().parent
DEST = HERE / "manuscript"

FIGURES = (
    "fig01_mass_models_ab_en.pdf",
    "fig01_mass_models_ab_zh.pdf",
    "fig02_workflow_en.pdf",
    "fig02_workflow_zh.pdf",
    "fig03_corrected_kev_sources.pdf",
    "fig_activation_positions_model_a_en.pdf",
    "fig_activation_positions_model_a_zh.pdf",
    "fig_activation_positions_model_b_en.pdf",
    "fig_activation_positions_model_b_zh.pdf",
    "fig04a_poisson_time_axis_schematic.pdf",
    "fig_compton_aperture_consistency_en.pdf",
    "fig_compton_aperture_consistency_zh.pdf",
    "fig04_trajectory_prompt_validation.pdf",
    "fig04_common_time_normalization.pdf",
    "fig08_background_origins.pdf",
    "fig09_mass_model_b_geometry_background.pdf",
    "fig07_hit_multiplicity.pdf",
    "fig05_broadband_veto_spectra.pdf",
    "fig10_mission_performance.pdf",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    missing = [name for name in FIGURES if not (HERE / name).is_file()]
    if missing:
        raise FileNotFoundError(f"missing manuscript figures: {missing}")

    DEST.mkdir(parents=True, exist_ok=True)
    for path in DEST.glob("*.pdf"):
        if path.name not in FIGURES:
            raise RuntimeError(f"unexpected PDF already present in staging folder: {path}")

    lines = [
        "# M05 manuscript figure manifest",
        "",
        "This directory contains exactly the PDF figures referenced by the current English and Chinese manuscripts.",
        "",
        "| File | Bytes | SHA-256 |",
        "|---|---:|---|",
    ]
    for name in FIGURES:
        source = HERE / name
        target = DEST / name
        shutil.copy2(source, target)
        lines.append(f"| `{name}` | {target.stat().st_size} | `{sha256(target)}` |")

    (DEST / "MANIFEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"staged {len(FIGURES)} figures in {DEST}")


if __name__ == "__main__":
    main()
