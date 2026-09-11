from __future__ import annotations

import os
import argparse
import re
import textwrap
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/opticsim_mpl")

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.font_manager import FontProperties


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "records" / "2026-05-18_bounce_path_reconciliation.md"
DEFAULT_OUT = ROOT / "records" / "2026-05-18_bounce_path_reconciliation.pdf"
DEFAULT_PLOT = ROOT / "runs" / "channel_bounce_path_reconciliation" / "channel_bounce_path_reconciliation.png"

FONT_REG = FontProperties(fname="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
FONT_BOLD = FontProperties(fname="/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")


def clean_markdown(line: str) -> tuple[str, str]:
    if line.startswith("# "):
        return "title", line[2:].strip()
    if line.startswith("## "):
        return "heading", line[3:].strip()
    if re.match(r"^\d+\. ", line):
        return "body", line.strip()
    if line.startswith("- "):
        return "body", line.strip()
    return "body", line.rstrip()


def wrap_line(text: str, width: int) -> list[str]:
    if not text:
        return [""]
    return textwrap.wrap(text, width=width, break_long_words=True, replace_whitespace=False) or [text]


def draw_text_page(pdf: PdfPages, entries: list[tuple[str, str]], page_no: int, source: Path) -> None:
    fig = plt.figure(figsize=(8.27, 11.69), dpi=150)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()

    y = 0.94
    for kind, text in entries:
        if kind == "title":
            ax.text(0.08, y, text, fontproperties=FONT_BOLD, fontsize=20, color="#0f172a", va="top")
            y -= 0.055
        elif kind == "heading":
            ax.text(0.08, y, text, fontproperties=FONT_BOLD, fontsize=14, color="#111827", va="top")
            y -= 0.034
        elif kind == "code":
            ax.text(
                0.09,
                y,
                text,
                fontproperties=FONT_REG,
                fontsize=8.2,
                color="#334155",
                va="top",
                family="monospace",
            )
            y -= 0.021
        else:
            ax.text(0.09, y, text, fontproperties=FONT_REG, fontsize=10.2, color="#111827", va="top")
            y -= 0.026

    ax.text(0.08, 0.035, f"{source.relative_to(ROOT)} | page {page_no}", fontproperties=FONT_REG, fontsize=7.5, color="#64748b")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def paginate(lines: list[str]) -> list[list[tuple[str, str]]]:
    pages: list[list[tuple[str, str]]] = []
    current: list[tuple[str, str]] = []
    used = 0.0
    in_code = False

    def cost(kind: str) -> float:
        if kind == "title":
            return 2.4
        if kind == "heading":
            return 1.6
        if kind == "code":
            return 0.9
        return 1.0

    def flush() -> None:
        nonlocal current, used
        if current:
            pages.append(current)
        current = []
        used = 0.0

    for raw in lines:
        if raw.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            wrapped = wrap_line(raw.rstrip(), 82)
            for part in wrapped:
                if used + cost("code") > 33.5:
                    flush()
                current.append(("code", part))
                used += cost("code")
            continue

        kind, text = clean_markdown(raw)
        width = 28 if kind == "title" else 44 if kind == "heading" else 57
        wrapped = wrap_line(text, width)
        for index, part in enumerate(wrapped):
            out_kind = kind if index == 0 else "body"
            if used + cost(out_kind) > 33.5:
                flush()
            current.append((out_kind, part))
            used += cost(out_kind)
        if raw == "":
            used += 0.35
    flush()
    return pages


def draw_plot_page(pdf: PdfPages, plot_path: Path) -> None:
    fig = plt.figure(figsize=(11.69, 8.27), dpi=150)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    ax.text(0.06, 0.92, "附图：Channel Bounce/Path Reconciliation", fontproperties=FONT_BOLD, fontsize=20, color="#0f172a")
    if plot_path.exists():
        img = mpimg.imread(plot_path)
        img_ax = fig.add_axes([0.06, 0.15, 0.88, 0.68])
        img_ax.imshow(img)
        img_ax.set_axis_off()
    else:
        ax.text(0.5, 0.5, f"缺少图像：{plot_path}", fontproperties=FONT_REG, fontsize=12, ha="center")
    ax.text(0.06, 0.06, str(plot_path.relative_to(ROOT)), fontproperties=FONT_REG, fontsize=8.5, color="#64748b")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a Chinese PDF from a records markdown file.")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--plot", default=str(DEFAULT_PLOT))
    parser.add_argument("--no-plot", action="store_true")
    args = parser.parse_args()

    source = Path(args.source)
    if not source.is_absolute():
        source = ROOT / source
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    plot_path = Path(args.plot)
    if not plot_path.is_absolute():
        plot_path = ROOT / plot_path

    lines = source.read_text(encoding="utf-8").splitlines()
    pages = paginate(lines)
    with PdfPages(out) as pdf:
        for page_no, entries in enumerate(pages, start=1):
            draw_text_page(pdf, entries, page_no, source)
        if not args.no_plot:
            draw_plot_page(pdf, plot_path)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
