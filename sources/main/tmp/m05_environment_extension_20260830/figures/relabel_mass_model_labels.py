#!/usr/bin/env python3
"""Replace legacy design codes with paper-facing mass-model labels in PDF figures."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pymupdf as fitz


FONT_FILE = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")

REPLACEMENTS = {
    "fig04_common_time_normalization.pdf": {
        "SG3 direct": "Model A direct",
        "SH3 direct": "Model B direct",
        "SG3 common time": "Model A common time",
        "SH3 common time": "Model B common time",
        "SG3 background": "Model A background",
        "SH3 background": "Model B background",
        "SG3 signal survival": "Model A signal survival",
        "SH3 signal survival": "Model B signal survival",
    },
    "fig05_pre_veto_spectra.pdf": {
        "SG3 reference": "Mass model A",
        "SH3 chimney": "Mass model B",
    },
    "fig06_bgo_veto_spectrum.pdf": {
        "SH3 response spectrum": "Model B response spectrum",
    },
    "fig08_background_origins.pdf": {
        "SG3": "Model A",
        "SH3": "Model B",
        "SG3 leading delayed origins": "Mass model A delayed origins",
        "SH3 leading delayed origins": "Mass model B delayed origins",
    },
    "fig09_sh3_geometry_background.pdf": {
        "SH3 side-chimney focal-plane geometry":
            "Mass model B: side-chimney focal plane",
    },
    "fig10_mission_performance.pdf": {
        "SG3 reference": "Mass model A",
        "SH3 chimney": "Mass model B",
        "SG3 reference, Gaussian": "Model A, Gaussian",
        "SG3 reference, Asimov": "Model A, Asimov",
        "SH3 chimney, Gaussian": "Model B, Gaussian",
        "SH3 chimney, Asimov": "Model B, Asimov",
    },
}


def spans_on_page(page: fitz.Page) -> list[dict]:
    return [
        span
        for block in page.get_text("dict")["blocks"]
        if "lines" in block
        for line in block["lines"]
        for span in line["spans"]
    ]


def relabel_pdf(source: Path, output: Path, replacements: dict[str, str]) -> int:
    document = fitz.open(source)
    edits: list[tuple[fitz.Page, tuple[float, float], str, float, int]] = []
    counts = {old: 0 for old in replacements}

    for page in document:
        for span in spans_on_page(page):
            old = span["text"]
            if old not in replacements:
                continue
            rect = fitz.Rect(span["bbox"])
            rect.x0 -= 0.35
            rect.x1 += 0.35
            page.add_redact_annot(rect, fill=(1, 1, 1))
            edits.append(
                (page, tuple(span["origin"]), replacements[old], float(span["size"]), int(span["color"]))
            )
            counts[old] += 1

    missing = [old for old, count in counts.items() if count == 0]
    if missing:
        document.close()
        raise RuntimeError(f"{source.name}: labels not found: {missing}")

    for page in document:
        page.apply_redactions(images=0, graphics=0, text=0)
        page.insert_font(fontname="MassModelLabel", fontfile=str(FONT_FILE))

    for page, origin, new, size, colour in edits:
        page.insert_text(
            origin,
            new,
            fontsize=size,
            fontname="MassModelLabel",
            color=fitz.sRGB_to_pdf(colour),
            overlay=True,
        )

    temporary = output.with_suffix(".tmp.pdf")
    document.save(temporary, garbage=4, deflate=True)
    document.close()
    os.replace(temporary, output)
    return len(edits)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    total = 0
    for filename, replacements in REPLACEMENTS.items():
        path = args.directory / filename
        edits = relabel_pdf(path, path, replacements)
        print(f"{filename}: {edits} labels")
        total += edits
    print(f"total: {total} labels")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
