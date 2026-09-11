#!/usr/bin/env python3
"""Static conformance checks for the generated HTML deck."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup, Tag
from PIL import Image


WORK = Path(__file__).resolve().parent
HTML = WORK / "index.html"
SKILL = Path("/home/ubuntu/.codex/skills/html-slides")
REPORT = WORK / "deck_static_validation.json"


def main() -> int:
    problems: list[str] = []
    text = HTML.read_text(encoding="utf-8")
    soup = BeautifulSoup(text, "html.parser")

    meta = soup.find("meta", attrs={"name": "generator"})
    if meta is None or meta.get("content") != "html-slides v0.9.4":
        problems.append("missing or incorrect generator meta")

    deck = soup.find("main", id="deck")
    if deck is None or "deck" not in deck.get("class", []):
        problems.append("missing <main class=deck id=deck>")
        slides: list[Tag] = []
    else:
        slides = [child for child in deck.find_all("div", class_="slide", recursive=False)]

    expected_indices = list(range(len(slides)))
    actual_indices = [int(slide.get("data-slide", -1)) for slide in slides]
    if actual_indices != expected_indices:
        problems.append(f"non-sequential data-slide values: {actual_indices}")
    active = [i for i, slide in enumerate(slides) if "active" in slide.get("class", [])]
    if active != [0]:
        problems.append(f"expected only slide 0 active, got {active}")
    if len(slides) != 21:
        problems.append(f"expected 21 slides, got {len(slides)}")

    notes_titles: list[str] = []
    for index, slide in enumerate(slides):
        if len(slide.select(":scope > .split")) != 1:
            problems.append(f"slide {index} does not have exactly one direct split layout")
        if len(slide.select(":scope > .split > .visual")) != 1:
            problems.append(f"slide {index} does not have exactly one visual half")
        if len(slide.select(":scope > .split > .copy")) != 1:
            problems.append(f"slide {index} does not have exactly one copy half")
        if len(slide.select(":scope > .split > .visual > img")) != 1:
            problems.append(f"slide {index} visual half does not contain exactly one image")
        tag_children = [child for child in slide.children if isinstance(child, Tag)]
        if not tag_children:
            problems.append(f"slide {index} has no children")
            continue
        last = tag_children[-1]
        if last.name != "script" or "slide-notes" not in last.get("class", []):
            problems.append(f"slide {index} speaker notes are not the last child")
            continue
        try:
            payload = json.loads(last.get_text())
            if not all(key in payload for key in ("title", "script", "notes")):
                problems.append(f"slide {index} notes schema incomplete")
            notes_titles.append(str(payload.get("title", "")))
        except json.JSONDecodeError as exc:
            problems.append(f"slide {index} invalid notes JSON: {exc}")

    ids = [str(tag["id"]) for tag in soup.find_all(attrs={"id": True})]
    duplicates = [name for name, count in Counter(ids).items() if count > 1]
    if duplicates:
        problems.append(f"duplicate element ids: {duplicates}")

    image_records: list[dict[str, object]] = []
    for image in soup.find_all("img"):
        src = str(image.get("src", ""))
        alt = str(image.get("alt", "")).strip()
        if not alt:
            problems.append(f"image without alt: {src}")
        if not src and image.get("id") == "lightboxImage":
            continue
        if not src:
            problems.append("image with empty src")
            continue
        if src.startswith(("http://", "https://", "data:")):
            problems.append(f"non-local image source: {src}")
            continue
        path = (WORK / src).resolve()
        if not path.exists():
            problems.append(f"missing image: {src}")
            continue
        with Image.open(path) as raster:
            width, height = raster.size
        if "processed" in path.name and width > 1200:
            problems.append(f"processed image wider than 1200 px: {src} ({width})")
        image_records.append({"src": src, "width": width, "height": height, "bytes": path.stat().st_size})

    required_payloads = {
        "components_css": (SKILL / "assets/components.css").read_text(encoding="utf-8"),
        "theme_css": (SKILL / "assets/themes/editorial-light.css").read_text(encoding="utf-8"),
        "runtime_js": (SKILL / "assets/slides-runtime.js").read_text(encoding="utf-8"),
    }
    embedded = {name: payload in text for name, payload in required_payloads.items()}
    for name, present in embedded.items():
        if not present:
            problems.append(f"required Pro payload not embedded verbatim: {name}")
    for fn in ("function goTo(", "function next(", "function prev("):
        if fn not in text:
            problems.append(f"missing global navigation function: {fn}")
    if "grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);" not in text:
        problems.append("missing equal half-image/half-copy layout rule")
    if "animation: none !important;" not in text or "transition: none !important;" not in text:
        problems.append("animations or transitions are not globally disabled")
    if soup.select(".glow-blob"):
        problems.append("glow blobs must not appear in the white static deck")
    motion_classes = sorted({
        cls
        for tag in soup.find_all(class_=True)
        for cls in tag.get("class", [])
        if str(cls).startswith(("anim-", "bounce-"))
    })
    if motion_classes:
        problems.append(f"motion classes present: {motion_classes}")
    if "{{" in text or "}}" in text:
        problems.append("unresolved template marker")

    report = {
        "status": "PASS" if not problems else "FAIL",
        "html": str(HTML),
        "slides": len(slides),
        "speaker_notes": len(notes_titles),
        "note_titles": notes_titles,
        "images": image_records,
        "required_payloads_embedded_verbatim": embedded,
        "problems": problems,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
