#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path("/home/ubuntu/TES_511_Balloon")
EA = ROOT / "core_md/balloon511_ea_latex_drafts"
PARTIAL = EA / "_recovered_partial"
OUT = EA / "recovered_compile_ready"
NIMA = ROOT / "core_md/balloon511_nima_latex_drafts"


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def extract_between(text: str, start: str, end: str) -> str:
    i = text.index(start) + len(start)
    j = text.index(end, i)
    return text[i:j]


def extract_bibliography(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    start = text.index(r"\begin{thebibliography}")
    end = text.index(r"\end{thebibliography}", start) + len(r"\end{thebibliography}")
    return text[start:end]


def lines_1based(text: str, start: int, end: int) -> list[str]:
    lines = text.splitlines()
    return lines[start - 1 : end]


def drop_unmatched_equation_ends(lines: list[str]) -> list[str]:
    cleaned = []
    depth = 0
    for line in lines:
        if r"\begin{equation}" in line:
            depth += 1
            cleaned.append(line)
            continue
        if r"\end{equation}" in line:
            if depth == 0:
                cleaned.append("% [RECOVERY CLEANUP: dropped unmatched \\end{equation}]")
                continue
            depth -= 1
            cleaned.append(line)
            continue
        cleaned.append(line)
    return cleaned


def build_en():
    src_path = PARTIAL / "balloon511_ea_draft_en.recovered_partial.tex"
    src = src_path.read_text(encoding="utf-8", errors="replace")
    title = extract_between(
        src,
        r"\title[Detector-coupled Monte Carlo estimate for a balloon-borne 511 keV TES telescope]{",
        "}\n\n\\author",
    )
    abstract = extract_between(src, r"\abstract{", "}\n\n\\keywords")
    keywords = extract_between(src, r"\keywords{", "}\n\n\\maketitle")

    body = []
    body.extend(drop_unmatched_equation_ends(lines_1based(src, 62, 529)))
    body.append("")
    body.append(r"\section{Results}")
    body.append(r"\label{sec:results}")
    body.append("")
    body.append(
        "The recovered log fragments around the original detailed results tables are structurally mixed. "
        "This compile-ready copy therefore keeps the confirmed primary selected-rate numbers in a compact "
        "recovery table and leaves the original detailed table reconstruction to manual editing."
    )
    body.append("")
    body.append(r"\begin{table}[h]")
    body.append(r"\centering")
    body.append(r"\caption{Recovered primary unresolved-line selected-rate result.}")
    body.append(r"\label{tab:primary_sensitivity}")
    body.append(r"\begin{tabular}{lll}")
    body.append(r"\toprule")
    body.append(r"Quantity & Value & Note \\")
    body.append(r"\midrule")
    body.append(r"Day-15 selected background & $3.92\times10^{-2}\cps$ & Prompt + delayed \\")
    body.append(r"Day-15 selected signal at $\fzero$ & $1.19\times10^{-3}\cps$ & $\fzero=10^{-4}\phcms$ \\")
    body.append(r"Prompt background fraction & $93.4\%$ & Dominant component \\")
    body.append(r"20 d diagnostic $Z$ & $7.80$ & Counting metric \\")
    body.append(r"$\fthree(20\,\mathrm{d})$ & $3.85\times10^{-5}\phcms$ & Reference model only \\")
    body.append(r"\bottomrule")
    body.append(r"\end{tabular}")
    body.append(r"\end{table}")
    body.append("")
    body.append(r"\clearpage")
    body.append(r"\section*{Recovery gap note}")
    body.append(
        "The original recovered log fragments become structurally inconsistent after this point. "
        "The broad-window diagnostic paragraph and several nearby transition lines are omitted "
        "from this compile-ready reading copy; see the raw partial source and recovery manifest."
    )
    body.append("")
    body.extend(lines_1based(src, 687, 714))
    body.append("")
    body.append(r"\section*{Data and software availability}")
    body.append(
        "Before publication, a versioned public repository or institutional archive should "
        "provide the geometry and source definitions, random seeds, analysis and figure-generation "
        "scripts, LaTeX source, and derived validation products needed to reproduce the tables "
        "and figures in this paper. This compile-ready recovery copy is not the original final manuscript."
    )
    body.append("")
    body.append(r"\section*{Declarations}")
    body.append(r"\textbf{Funding} To be completed before journal submission.")
    body.append("")
    body.append(r"\textbf{Competing interests} To be completed before journal submission.")
    body.append("")
    body.append(r"\textbf{Author contributions} To be completed before journal submission.")
    body.append("")
    body.append(r"\textbf{Ethics approval and consent to participate} Not applicable.")
    body.append("")
    body.extend(lines_1based(src, 843, 959))

    preamble = r"""\documentclass[11pt]{article}
\usepackage[a4paper,top=2.4cm,bottom=2.5cm,left=2.0cm,right=2.0cm]{geometry}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{fontspec}
\setmainfont{TeX Gyre Termes}
\usepackage{booktabs}
\usepackage{graphicx}
\graphicspath{{../}}
\usepackage[section]{placeins}
\usepackage{xcolor}
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning}
\usepackage{caption}
\captionsetup{font=small,labelfont=bf}
\usepackage{titlesec}
\titleformat{\section}{\normalfont\large\bfseries}{\thesection}{0.6em}{}
\titleformat{\subsection}{\normalfont\normalsize\bfseries}{\thesubsection}{0.5em}{}
\titleformat{\subsubsection}{\normalfont\normalsize\bfseries}{\thesubsubsection}{0.5em}{}
\usepackage{hyperref}
\hypersetup{hidelinks}
\setlength{\emergencystretch}{3em}
\newcommand{\keV}{\ensuremath{\,\mathrm{keV}}}
\newcommand{\MeV}{\ensuremath{\,\mathrm{MeV}}}
\newcommand{\cms}{\ensuremath{\,\mathrm{cm^{-2}\,s^{-1}}}}
\newcommand{\phcms}{\ensuremath{\,\mathrm{ph\,cm^{-2}\,s^{-1}}}}
\newcommand{\cps}{\ensuremath{\,\mathrm{s^{-1}}}}
\newcommand{\wii}{W_{511}}
\newcommand{\aeff}{A_{\mathrm{eff}}}
\newcommand{\fzero}{F_{0}}
\newcommand{\fthree}{F_{3\sigma}}
\newcommand{\added}[1]{{\color{red}#1}}
\newcommand{\rewritten}[1]{{\color{green!45!black}#1}}
\newenvironment{addedblock}{\begingroup\color{red}}{\endgroup}
\newenvironment{rewrittenblock}{\begingroup\color{green!45!black}}{\endgroup}
\raggedbottom
"""
    doc = [
        "% RECOVERED COMPILE-READY READING COPY 20260708",
        "% Generated from partial Codex-log recovery. Not the original final EA source.",
        preamble,
        r"\begin{document}",
        r"\begin{center}",
        r"{\LARGE\bfseries " + title + r"\par}",
        r"\vspace{1em}",
        r"{\large Authors omitted for review\par}",
        r"\end{center}",
        r"\begin{abstract}",
        abstract,
        r"\end{abstract}",
        r"\noindent\textbf{Keywords}\hspace{0.7em}" + keywords,
        r"\vspace{1em}",
        "",
        "\n".join(body),
        r"\end{document}",
        "",
    ]
    write(OUT / "balloon511_ea_draft_en.compile_ready.tex", "\n".join(doc))


def build_zh():
    src_path = PARTIAL / "balloon511_ea_draft_zh.recovered_partial.tex"
    src = src_path.read_text(encoding="utf-8", errors="replace")
    body = []
    body.extend(lines_1based(src, 1, 392))
    body.insert(22, r"\graphicspath{{../}}")
    body.append("")
    body.append(r"\clearpage")
    body.append(r"\section*{恢复缺口说明}")
    body.append(
        "原始日志片段在第 381--635 行和附录/参考文献附近存在缺口。"
        "本文件只生成可阅读 PDF，缺失正文请继续从恢复片段或人工补稿。"
    )
    body.append("")
    body.append(extract_bibliography(NIMA / "balloon511_nima_draft_zh.tex"))
    body.append(r"\end{document}")
    write(OUT / "balloon511_ea_draft_zh.compile_ready.tex", "\n".join(body) + "\n")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    build_en()
    build_zh()
    print(OUT)


if __name__ == "__main__":
    main()
