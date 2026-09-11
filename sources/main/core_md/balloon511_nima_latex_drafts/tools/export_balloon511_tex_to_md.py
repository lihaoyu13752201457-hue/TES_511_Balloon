#!/usr/bin/env python3
"""Export the Balloon511 NIM A LaTeX draft to a GPT-reviewable Markdown copy.

This is not a submission converter.  It preserves equations and complex tables
as LaTeX where that is the least lossy representation, while converting section
structure, abstracts, bibliography entries, and figure image references.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


SECTION_COMMANDS = [
    (r"\\section\{([^{}]+)\}", "##"),
    (r"\\subsection\{([^{}]+)\}", "###"),
    (r"\\subsubsection\{([^{}]+)\}", "####"),
]


def strip_latex_markup(text: str) -> str:
    replacements = {
        r"\keV": " keV",
        r"\MeV": " MeV",
        r"\cps": " s^{-1}",
        r"\cms": " ph cm^{-2} s^{-1}",
        r"\wii": "W_{511}",
        r"\fzero": "F_0",
        r"\fthree": "F_{3\\sigma}",
        r"\aeff": "A_{\\mathrm{eff}}",
        r"~": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"\\cite\{([^{}]+)\}", r"[\1]", text)
    text = re.sub(r"\\ref\{([^{}]+)\}", r"\1", text)
    text = re.sub(r"\\label\{[^{}]+\}", "", text)
    text = re.sub(r"\\url\{([^{}]+)\}", r"\1", text)
    text = re.sub(r"\\mathrm\{([^{}]+)\}", r"\1", text)
    text = re.sub(r"\\textit\{([^{}]+)\}", r"*\1*", text)
    text = re.sub(r"\\textbf\{([^{}]+)\}", r"**\1**", text)
    text = text.replace(r"\%", "%")
    text = text.replace(r"\_", "_")
    text = text.replace(r"\times", "x")
    text = text.replace(r"\inW_{511}", r"\in W_{511}")
    text = re.sub(r"(\\(?:in|notin|subset|leq|geq|lt|gt))(?=W_\{511\})", r"\1 ", text)
    return text.strip()


def extract_group(lines: list[str], start: int, begin: str, end: str) -> tuple[list[str], int]:
    block: list[str] = []
    i = start
    depth = 0
    while i < len(lines):
        line = lines[i]
        if begin in line:
            depth += line.count(begin)
        if end in line:
            depth -= line.count(end)
            if depth <= 0:
                return block, i
        elif depth > 0:
            block.append(line.rstrip("\n"))
        i += 1
    return block, i


def convert_figure(block: list[str], base_dir: Path) -> str:
    caption = ""
    path = ""
    for line in block:
        cap = re.search(r"\\caption\{(.+)\}", line)
        if cap:
            caption = strip_latex_markup(cap.group(1))
        inc = re.search(r"\\includegraphics(?:\[[^\]]+\])?\{([^{}]+)\}", line)
        if inc:
            path = inc.group(1)
    if not path:
        return "```latex\n" + "\n".join(block) + "\n```"
    image_path = path
    if not image_path.startswith("/"):
        image_path = str((base_dir / image_path).as_posix())
    alt = caption or Path(path).stem
    return f"![{alt}]({image_path})\n\n*{caption}*" if caption else f"![{alt}]({image_path})"


def convert_table(block: list[str]) -> str:
    caption = ""
    for line in block:
        cap = re.search(r"\\caption\{(.+)\}", line)
        if cap:
            caption = strip_latex_markup(cap.group(1))
            break
    head = f"**Table: {caption}**\n\n" if caption else ""
    return head + "```latex\n" + "\n".join(block) + "\n```"


def convert_tex(tex: str, base_dir: Path) -> str:
    lines = tex.splitlines()
    out: list[str] = []
    in_preamble = True
    in_bibliography = False
    i = 0

    title_match = re.search(r"\\title\{(.+?)\}", tex)
    if title_match:
        out.append(f"# {strip_latex_markup(title_match.group(1))}")
        out.append("")
        out.append(
            "> Review packet generated from `balloon511_nima_draft_en.tex`. "
            "Equations and complex tables are intentionally preserved close to LaTeX."
        )
        out.append("")

    while i < len(lines):
        line = lines[i]
        raw = line.strip()

        if raw.startswith("%") or not raw:
            i += 1
            continue
        if raw == r"\begin{document}":
            in_preamble = False
            i += 1
            continue
        if in_preamble or raw in {
            r"\begin{frontmatter}",
            r"\end{frontmatter}",
            r"\begin{keyword}",
            r"\end{keyword}",
            r"\end{document}",
        }:
            i += 1
            continue

        if raw == r"\begin{abstract}":
            block, end_i = extract_group(lines, i, r"\begin{abstract}", r"\end{abstract}")
            out.extend(["## Abstract", "", strip_latex_markup(" ".join(block)), ""])
            i = end_i + 1
            continue

        if raw.startswith(r"\begin{figure}"):
            block, end_i = extract_group(lines, i, r"\begin{figure}", r"\end{figure}")
            out.extend([convert_figure(block, base_dir), ""])
            i = end_i + 1
            continue

        if raw.startswith(r"\begin{table}"):
            block, end_i = extract_group(lines, i, r"\begin{table}", r"\end{table}")
            out.extend([convert_table(block), ""])
            i = end_i + 1
            continue

        if raw.startswith(r"\begin{equation}") or raw.startswith(r"\begin{align}"):
            end = r"\end{align}" if raw.startswith(r"\begin{align}") else r"\end{equation}"
            block, end_i = extract_group(lines, i, raw, end)
            out.extend(["```latex", raw, *block, end, "```", ""])
            i = end_i + 1
            continue

        if raw.startswith(r"\input{"):
            input_path = re.search(r"\\input\{([^{}]+)\}", raw)
            if input_path:
                inc = base_dir / input_path.group(1)
                if inc.exists():
                    out.extend([f"```latex\n% input: {input_path.group(1)}\n{inc.read_text(encoding='utf-8').strip()}\n```", ""])
            i += 1
            continue

        if raw.startswith(r"\begin{thebibliography}"):
            out.extend(["## References", ""])
            in_bibliography = True
            i += 1
            continue
        if raw.startswith(r"\end{thebibliography}"):
            in_bibliography = False
            i += 1
            continue
        if in_bibliography:
            bib = re.match(r"\\bibitem\{([^{}]+)\}", raw)
            if bib:
                out.append(f"- **{bib.group(1)}** ")
            elif out and out[-1].startswith("- **"):
                out[-1] += strip_latex_markup(raw)
            else:
                out.append(strip_latex_markup(raw))
            i += 1
            continue

        converted = raw
        for pattern, hashes in SECTION_COMMANDS:
            match = re.match(pattern, raw)
            if match:
                converted = f"{hashes} {strip_latex_markup(match.group(1))}"
                break
        else:
            if raw.startswith("\\"):
                i += 1
                continue
            converted = strip_latex_markup(raw)

        if converted:
            out.append(converted)
            out.append("")
        i += 1

    return "\n".join(out).replace("\n\n\n", "\n\n").strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="balloon511_nima_draft_en.tex")
    parser.add_argument("--output", default="balloon511_nima_draft_en.md")
    args = parser.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)
    tex = in_path.read_text(encoding="utf-8")
    out_path.write_text(convert_tex(tex, in_path.parent), encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
