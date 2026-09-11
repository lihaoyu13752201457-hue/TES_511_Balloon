#!/usr/bin/env python3
"""Render all HTML slides with the bundled Chromium and assemble preview files."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "index.html"
OUT = ROOT / "rendered_preview"
PDF = ROOT / "report_preview.pdf"
OVERVIEW = ROOT / "preview_overview.png"
CHROME = Path(
    "/home/ubuntu/.cache/ms-playwright/"
    "chromium_headless_shell-1223/chrome-headless-shell-linux64/"
    "chrome-headless-shell"
)


def validate_html(text: str) -> dict[str, object]:
    slide_ids = [int(x) for x in re.findall(r'data-slide="(\d+)"', text)]
    notes = re.findall(
        r'<script type="application/json" class="slide-notes">(.*?)</script>',
        text,
        flags=re.S,
    )
    errors: list[str] = []
    if slide_ids != list(range(7)):
        errors.append(f"unexpected slide ids: {slide_ids}")
    if text.count('class="slide active"') != 1:
        errors.append("the first slide must be the only active slide")
    if len(notes) != 7:
        errors.append(f"expected 7 notes blocks, found {len(notes)}")
    for idx, raw in enumerate(notes):
        try:
            payload = json.loads(raw)
            if not {"title", "script", "notes"}.issubset(payload):
                errors.append(f"notes block {idx} is incomplete")
        except json.JSONDecodeError as exc:
            errors.append(f"notes block {idx} is invalid JSON: {exc}")
    for required in [
        '<div class="deck" id="deck">',
        "function goTo(",
        "function next()",
        "function prev()",
        '<meta name="generator" content="html-slides v0.9.4">',
        "height: 100dvh",
        "max-height: min(50vh, 400px)",
        "max-height: 700px",
        "max-height: 600px",
        "max-height: 500px",
    ]:
        if required not in text:
            errors.append(f"missing required fragment: {required}")
    for asset in ["assets/source_components.png", "assets/gamma_source.png"]:
        if not (ROOT / asset).is_file():
            errors.append(f"missing asset: {asset}")
    return {
        "status": "PASS" if not errors else "FAIL",
        "slide_count": len(slide_ids),
        "speaker_notes_count": len(notes),
        "errors": errors,
    }


def render_slide(index: int, output: Path) -> None:
    url = HTML.resolve().as_uri() + f"?slide={index}&export=1"
    command = [
        str(CHROME),
        "--headless",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        "--window-size=1920,1080",
        "--virtual-time-budget=2500",
        f"--screenshot={output}",
        url,
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=60)
    if completed.returncode != 0 or not output.is_file():
        sys.stderr.write(completed.stdout)
        sys.stderr.write(completed.stderr)
        raise RuntimeError(f"Chromium failed while rendering slide {index + 1}")


def make_overview(paths: list[Path]) -> None:
    thumb_w, thumb_h = 640, 360
    gutter, label_h = 28, 34
    columns = 2
    rows = (len(paths) + columns - 1) // columns
    canvas = Image.new(
        "RGB",
        (
            columns * thumb_w + (columns + 1) * gutter,
            rows * (thumb_h + label_h) + (rows + 1) * gutter,
        ),
        "#e8edf2",
    )
    draw = ImageDraw.Draw(canvas)
    for idx, path in enumerate(paths):
        image = Image.open(path).convert("RGB")
        image.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        col, row = idx % columns, idx // columns
        x = gutter + col * (thumb_w + gutter)
        y = gutter + row * (thumb_h + label_h + gutter)
        canvas.paste(image, (x, y))
        draw.text((x, y + thumb_h + 8), f"Slide {idx + 1}", fill="#243544")
    canvas.save(OVERVIEW, optimize=True)


def make_pdf(paths: list[Path]) -> None:
    pages = [Image.open(path).convert("RGB") for path in paths]
    pages[0].save(PDF, save_all=True, append_images=pages[1:], resolution=144.0)


def main() -> None:
    text = HTML.read_text(encoding="utf-8")
    validation = validate_html(text)
    (ROOT / "preview_validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if validation["status"] != "PASS":
        raise SystemExit(json.dumps(validation, ensure_ascii=False, indent=2))
    if not CHROME.is_file():
        raise SystemExit(f"Chromium not found: {CHROME}")

    OUT.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for index in range(7):
        output = OUT / f"slide_{index + 1:02d}.png"
        render_slide(index, output)
        paths.append(output)
    make_overview(paths)
    make_pdf(paths)
    print(json.dumps({"validation": validation, "pdf": str(PDF), "overview": str(OVERVIEW)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
