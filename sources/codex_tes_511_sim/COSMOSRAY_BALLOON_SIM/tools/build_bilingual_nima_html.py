#!/usr/bin/env python3
"""Build lightweight HTML wrappers for the bilingual NIMA Markdown drafts."""

from __future__ import annotations

import html
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports2.0" / "07_NIMA_MANUSCRIPT"


CSS = """
body { font-family: "Noto Serif CJK SC", "Source Han Serif SC", "DejaVu Serif", serif; color: #1b1b1b; line-height: 1.68; max-width: 1040px; margin: 0 auto; padding: 34px 44px 70px; background: #f8f8f6; }
article { background: #fff; padding: 42px 54px; box-shadow: 0 3px 18px rgba(0,0,0,.08); }
h1 { font-size: 29px; line-height: 1.24; margin-bottom: 14px; }
h2 { margin-top: 38px; border-bottom: 2px solid #222; padding-bottom: 6px; font-size: 22px; }
h3 { margin-top: 25px; font-size: 18px; }
p { margin: 12px 0; }
table { width: 100%; border-collapse: collapse; margin: 16px 0 24px; font-size: 13px; }
th, td { border: 1px solid #d0d0d0; padding: 6px 8px; vertical-align: top; }
th { background: #eceff3; }
pre { background: #f4f4f4; padding: 12px; overflow-x: auto; }
code { font-family: "DejaVu Sans Mono", Consolas, monospace; }
figure { margin: 24px 0 30px; break-inside: avoid; }
img { max-width: 100%; display: block; margin: 0 auto; border: 1px solid #ddd; background: white; }
figcaption { font-size: 13px; color: #444; margin-top: 8px; }
.equation { text-align: center; font-family: "DejaVu Sans", serif; background: #fafafa; border: 1px solid #e4e4e4; padding: 10px; margin: 14px 0; white-space: pre-wrap; }
@media print { body { background: white; padding: 0; } article { box-shadow: none; padding: 0; } h2 { break-before: page; } figure, table { break-inside: avoid; } }
"""


def latex_to_plain(expr: str) -> str:
    text = expr
    replacements = {
        r"\times": "x",
        r"\simeq": "approx.",
        r"\ge": ">=",
        r"\le": "<=",
        r"\sigma": "sigma",
        r"\mu": "micro",
        r"\gamma": "gamma",
        r"\lambda": "lambda",
        r"\rightarrow": "->",
        r"\to": "->",
        r"\sum": "sum",
        r"\Omega": "Omega",
        r"\theta": "theta",
        r"\pi": "pi",
        r"\eta": "eta",
        r"\dot": "",
        r"\boldsymbol": "",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    text = re.sub(r"\\mathrm\{([^{}]+)\}", r"\1", text)
    text = re.sub(r"\\text\{([^{}]+)\}", r"\1", text)
    text = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"(\1)/(\2)", text)
    text = re.sub(r"\^\{([^{}]+)\}", r"^\1", text)
    text = re.sub(r"_\{([^{}]+)\}", r"_\1", text)
    text = re.sub(r"\\([A-Za-z]+)", r"\1", text)
    text = text.replace("{", "").replace("}", "")
    return text


def inline_markup(text: str) -> str:
    text = re.sub(r"\\\((.*?)\\\)", lambda m: latex_to_plain(m.group(1)), text)
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return escaped


def parse_table(lines: list[str]) -> str:
    parsed: list[list[str]] = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and all(set(cell) <= {"-", ":"} for cell in cells):
            continue
        parsed.append(cells)
    if not parsed:
        return ""
    head = "".join(f"<th>{inline_markup(cell)}</th>" for cell in parsed[0])
    body = []
    for row in parsed[1:]:
        body.append("<tr>" + "".join(f"<td>{inline_markup(cell)}</td>" for cell in row) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def flush_paragraph(out: list[str], para: list[str]) -> None:
    if not para:
        return
    text = " ".join(line.strip() for line in para)
    out.append(f"<p>{inline_markup(text)}</p>")
    para.clear()


def markdown_to_html(markdown: str, lang: str, title: str) -> str:
    lines = markdown.splitlines()
    out: list[str] = []
    para: list[str] = []
    i = 0
    in_code = False
    code_lines: list[str] = []
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code:
                out.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
                code_lines.clear()
                in_code = False
            else:
                flush_paragraph(out, para)
                in_code = True
            i += 1
            continue
        if in_code:
            code_lines.append(line)
            i += 1
            continue

        if not stripped:
            flush_paragraph(out, para)
            i += 1
            continue

        if stripped == r"\[":
            flush_paragraph(out, para)
            eq: list[str] = []
            i += 1
            while i < len(lines) and lines[i].strip() != r"\]":
                eq.append(lines[i])
                i += 1
            out.append("<div class=\"equation\">" + html.escape(latex_to_plain("\n".join(eq))) + "</div>")
            i += 1
            continue

        if stripped.startswith("|"):
            flush_paragraph(out, para)
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            out.append(parse_table(table_lines))
            continue

        image = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", stripped)
        if image:
            flush_paragraph(out, para)
            alt, src = image.groups()
            out.append(
                f"<figure><img src=\"{html.escape(src)}\" alt=\"{html.escape(alt)}\">"
                f"<figcaption>{html.escape(alt)}</figcaption></figure>"
            )
            i += 1
            continue

        if stripped.startswith("# "):
            flush_paragraph(out, para)
            out.append(f"<h1>{inline_markup(stripped[2:])}</h1>")
        elif stripped.startswith("## "):
            flush_paragraph(out, para)
            out.append(f"<h2>{inline_markup(stripped[3:])}</h2>")
        elif stripped.startswith("### "):
            flush_paragraph(out, para)
            out.append(f"<h3>{inline_markup(stripped[4:])}</h3>")
        else:
            para.append(line)
        i += 1

    flush_paragraph(out, para)
    body = "\n".join(out)
    return (
        f"<!doctype html><html lang=\"{html.escape(lang)}\"><head><meta charset=\"utf-8\">"
        f"<title>{html.escape(title)}</title><style>{CSS}</style></head><body><article>"
        f"{body}</article></body></html>"
    )


def main() -> int:
    specs = [
        ("tes511_balloon_background_nima_en.md", "tes511_balloon_background_nima_en.html", "en", "TES 511 keV Balloon Background NIMA Draft"),
        ("tes511_balloon_background_nima_zh.md", "tes511_balloon_background_nima_zh.html", "zh-CN", "511 keV TES 气球本底 NIMA 中文草稿"),
    ]
    for md_name, html_name, lang, title in specs:
        markdown = (OUT / md_name).read_text(encoding="utf-8")
        (OUT / html_name).write_text(markdown_to_html(markdown, lang, title), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
