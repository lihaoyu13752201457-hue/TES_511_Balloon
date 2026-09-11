#!/usr/bin/env python3
"""Convert the aligned EA manuscripts to first-citation-order numeric references."""

from __future__ import annotations

import re
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCES = (
    HERE / "balloon511_ea_draft_en.tex",
    HERE / "balloon511_ea_draft_zh.tex",
)
BEGIN = r"\begin{thebibliography}{99}"
END = r"\end{thebibliography}"
BIBITEM_RE = re.compile(
    r"\\bibitem(?:\[[^]]*\])?\{(?P<key>[^}]+)\}(?P<body>.*?)(?=\n\\bibitem|\Z)",
    re.S,
)


def first_citation_order(body: str) -> list[str]:
    order: list[str] = []
    for group in re.findall(r"\\cite\{([^}]+)\}", body):
        for raw_key in group.split(","):
            key = raw_key.strip()
            if key and key not in order:
                order.append(key)
    return order


def convert(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    before, remainder = text.split(BEGIN, 1)
    bibliography_text, after = remainder.split(END, 1)
    order = first_citation_order(before)
    entries = {
        match.group("key"): match.group("body").strip()
        for match in BIBITEM_RE.finditer(bibliography_text)
    }
    if set(order) != set(entries):
        missing = sorted(set(order) - set(entries))
        unused = sorted(set(entries) - set(order))
        raise RuntimeError(f"{path.name}: missing={missing}, unused={unused}")
    rebuilt = "\n\n".join(
        f"\\bibitem{{{key}}}\n{entries[key]}" for key in order
    )
    output = f"{before}{BEGIN}\n\n{rebuilt}\n\n{END}{after}"
    path.write_text(output, encoding="utf-8")
    return order


def main() -> None:
    orders = [convert(path) for path in SOURCES]
    if orders[0] != orders[1]:
        raise RuntimeError("English and Chinese first-citation orders differ")
    print(f"NUMERIC_CITATIONS_READY references={len(orders[0])}")


if __name__ == "__main__":
    main()
