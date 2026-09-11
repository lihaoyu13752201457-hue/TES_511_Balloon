#!/usr/bin/env python3
"""Build a clean manuscript TeX from the tracked-review English source.

The transformation is deliberately limited to presentation markup: accepted
text inside ``\\revblue`` is retained, revision labels/deletion notes are
removed, and the visible anonymous-review placeholders requested by the author
are omitted.  The source review copy is never modified.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


DROP_COMMANDS = {r"\revmark", r"\revdeleted"}
KEEP_ARGUMENT_COMMANDS = {r"\revblue"}


def _balanced_argument(text: str, opening: int) -> tuple[str, int]:
    if opening >= len(text) or text[opening] != "{":
        raise ValueError(f"Expected opening brace at offset {opening}")
    depth = 1
    pos = opening + 1
    while pos < len(text):
        char = text[pos]
        if char == "\\" and pos + 1 < len(text) and text[pos + 1] in "{}":
            pos += 2
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[opening + 1 : pos], pos + 1
        pos += 1
    raise ValueError(f"Unbalanced argument beginning at offset {opening}")


def _strip_revision_commands(text: str) -> str:
    out: list[str] = []
    pos = 0
    commands = sorted(DROP_COMMANDS | KEEP_ARGUMENT_COMMANDS, key=len, reverse=True)
    while pos < len(text):
        command = next((item for item in commands if text.startswith(item, pos)), None)
        if command is None:
            out.append(text[pos])
            pos += 1
            continue

        after = pos + len(command)
        while after < len(text) and text[after].isspace():
            after += 1
        if after >= len(text) or text[after] != "{":
            out.append(text[pos])
            pos += 1
            continue

        argument, end = _balanced_argument(text, after)
        if command in KEEP_ARGUMENT_COMMANDS:
            out.append(_strip_revision_commands(argument))
        pos = end
    return "".join(out)


def clean_manuscript(text: str) -> str:
    revision_definition = re.compile(
        r"^\\(?:definecolor\{revisionblue\}|newcommand\{\\(?:revmark|revdeleted|revblue)\}).*$"
    )
    text = "\n".join(
        line for line in text.splitlines() if not revision_definition.match(line)
    ) + "\n"
    text = _strip_revision_commands(text)
    text = text.replace(r"\color{revisionblue}", "")
    text = text.replace(r"\captionsetup{font={color=revisionblue}}", "")
    text = re.sub(
        r"(?:\\noindent)?\\textbf\{\[R(?:11|13|14|15|16)\]\}\s*",
        "",
        text,
    )

    # The clean anonymous manuscript omits visible author/affiliation review
    # placeholders and the still-unassigned contribution statement.
    text = re.sub(
        r"\\vspace\{1\.1em\}\s*"
        r"\{\\large Authors omitted for review\\par\}\s*"
        r"\\vspace\{0\.3em\}\s*"
        r"\{\\normalsize\\itshape Affiliations omitted for review\\par\}\s*",
        "",
        text,
        count=1,
    )
    text = re.sub(
        r"\n\\textbf\{Author contributions\} To be completed before journal submission\.\n",
        "\n",
        text,
        count=1,
    )

    forbidden = (
        r"\revmark",
        r"\revdeleted",
        r"\revblue",
        "revisionblue",
        "Authors omitted for review",
        "Affiliations omitted for review",
        "Author contributions",
    )
    leftovers = [token for token in forbidden if token in text]
    if re.search(r"\[R\d+\]", text):
        leftovers.append("[R<n>]")
    if leftovers:
        raise RuntimeError(f"Revision/placeholder tokens remain: {leftovers}")
    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    cleaned = clean_manuscript(args.source.read_text(encoding="utf-8"))
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.destination.write_text(cleaned, encoding="utf-8")


if __name__ == "__main__":
    main()
