#!/usr/bin/env python3
"""Assemble the presentation as one HTML file with the Pro runtime inlined."""

from pathlib import Path


WORK = Path(__file__).resolve().parent
SKILL = Path("/home/ubuntu/.codex/skills/html-slides")
TEMPLATE = WORK / "deck_template.html"
OUTPUT = WORK / "index.html"


def main() -> int:
    html = TEMPLATE.read_text(encoding="utf-8")
    replacements = {
        "{{COMPONENTS_CSS}}": (SKILL / "assets/components.css").read_text(encoding="utf-8"),
        "{{THEME_CSS}}": (SKILL / "assets/themes/editorial-light.css").read_text(encoding="utf-8"),
        "{{SLIDES_RUNTIME_JS}}": (SKILL / "assets/slides-runtime.js").read_text(encoding="utf-8"),
    }
    for marker, payload in replacements.items():
        if marker not in html:
            raise RuntimeError(f"missing template marker {marker}")
        html = html.replace(marker, payload)
    if "{{" in html or "}}" in html:
        raise RuntimeError("unresolved template marker remains")
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUTPUT} ({OUTPUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
