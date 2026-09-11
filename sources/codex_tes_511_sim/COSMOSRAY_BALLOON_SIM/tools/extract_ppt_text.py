#!/usr/bin/env python3
"""Extract text from the original cosmosray_0416 PPTX-in-ZIP bundle."""

from __future__ import annotations

import io
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ZIP_PATH = ROOT.parent / "cosmosray_0416.zip"
OUT_PATH = ROOT / "docs" / "cosmosray_0416_ppt_text.txt"
TEXT_TAG = "{http://schemas.openxmlformats.org/drawingml/2006/main}t"


def slide_number(name: str) -> int:
    m = re.search(r"slide(\d+)\.xml$", name)
    return int(m.group(1)) if m else 0


def extract() -> list[tuple[str, list[str]]]:
    with zipfile.ZipFile(ZIP_PATH) as outer:
        pptx_names = [n for n in outer.namelist() if n.lower().endswith(".pptx")]
        if not pptx_names:
            raise FileNotFoundError(f"No pptx found in {ZIP_PATH}")
        with zipfile.ZipFile(io.BytesIO(outer.read(pptx_names[0]))) as pptx:
            slides = sorted(
                [
                    n
                    for n in pptx.namelist()
                    if n.startswith("ppt/slides/slide") and n.endswith(".xml")
                ],
                key=slide_number,
            )
            extracted: list[tuple[str, list[str]]] = []
            for slide in slides:
                root = ET.fromstring(pptx.read(slide))
                texts = [t.text.strip() for t in root.iter(TEXT_TAG) if t.text and t.text.strip()]
                extracted.append((slide, texts))
            return extracted


def main() -> int:
    slides = extract()
    OUT_PATH.parent.mkdir(exist_ok=True)
    lines = [f"source_zip: {ZIP_PATH}", f"slide_count: {len(slides)}", ""]
    for slide, texts in slides:
        lines.append(f"## {slide}")
        lines.extend(texts)
        lines.append("")
    OUT_PATH.write_text("\n".join(lines))
    print(f"wrote {OUT_PATH}")
    print(f"slides {len(slides)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

