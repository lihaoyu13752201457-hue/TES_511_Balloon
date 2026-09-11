#!/usr/bin/env python3
"""Build a reviewer-friendly PDF with a physically visible Chinese sidebar.

The earlier integrated PDF stored full Chinese advice in PDF annotation
dictionaries.  Some browser viewers render the coloured highlights but hide
their annotation bodies.  This builder therefore widens every page and draws
the page-specific review advice into the new right-hand area.  Each independent
comment receives a number; the same number is drawn beside its highlight and
used in the visible sidebar.

The original manuscript page remains at its native size on the left.  Existing
highlights, links, outlines, named destinations, and full pop-up comments are
preserved.

Runtime dependencies:
  * reportlab (Ubuntu package python3-reportlab)
  * pikepdf 5+ (Ubuntu package python3-pikepdf)
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Iterable

try:
    import pikepdf
    from pikepdf import Array, Rectangle, String
except ImportError as exc:  # pragma: no cover - environment guidance
    raise SystemExit(
        "pikepdf is required. Install python3-pikepdf or expose it on PYTHONPATH."
    ) from exc

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color


HERE = Path(__file__).resolve().parent
INPUT_PDF = HERE / "balloon511_ea_draft_en_peer_review_annotated_cn_integrated_20260714.pdf"
INPUT_VALIDATION_JSON = HERE / "ea_peer_review_cn_pdf_validation_20260714.json"
OUTPUT_PDF = HERE / "balloon511_ea_draft_en_peer_review_annotated_cn_visible_sidebar_20260714.pdf"
VALIDATION_JSON = HERE / "ea_peer_review_cn_visible_sidebar_validation_20260714.json"
OVERLAY_PDF = HERE / ".ea_peer_review_cn_visible_sidebar_overlay_20260714.tmp.pdf"

FONT_PATH = Path("/usr/share/fonts/truetype/arphic-gbsn00lp/gbsn00lp.ttf")
FONT_NAME = "EAReviewChinese"
SIDEBAR_WIDTH = 370.0
RESOLVED_REVIEW_IDS = {"M03"}
EXPECTED_FORMAL_REVIEW_IDS = (
    {f"M{number:02d}" for number in range(1, 24)}
    | {f"N{number:02d}" for number in range(1, 11)}
    | {"S01", "S02", "J01", "J02", "J03"}
) - RESOLVED_REVIEW_IDS
EXPECTED_SUPPLEMENTAL_REVIEW_IDS = {"A00", "Re-M02", "Re-M08", "Re-M09"}
EXPECTED_REVIEW_IDS = EXPECTED_FORMAL_REVIEW_IDS | EXPECTED_SUPPLEMENTAL_REVIEW_IDS
EXPECTED_PAGE_SIDEBAR_ENTRIES = 59

RENDER_REPLACEMENTS = str.maketrans(
    {
        "–": "-",
        "−": "-",
        "⁻": "-",
        "⁴": "^4",
        "₀": "_0",
        "₃": "_3",
        "ₖ": "_k",
        "ₗ": "_l",
    }
)


@dataclass
class ReviewEntry:
    annotations: list
    subtype: str
    subject: str
    contents: str
    color: tuple[float, float, float]
    rects: list[tuple[float, float, float, float]]
    target_y: float
    number: int = 0
    code: str = ""
    badge_y: float = 0.0


def annotation_rect(annotation) -> tuple[float, float, float, float]:
    values = [float(value) for value in annotation.get("/Rect", [0, 0, 0, 0])]
    if len(values) != 4:
        raise RuntimeError(f"Unexpected annotation rectangle: {values}")
    return tuple(values)  # type: ignore[return-value]


def annotation_color(annotation) -> tuple[float, float, float]:
    values = [float(value) for value in annotation.get("/C", [0.5, 0.5, 0.5])]
    if len(values) < 3:
        return (0.5, 0.5, 0.5)
    return tuple(max(0.0, min(1.0, value)) for value in values[:3])  # type: ignore[return-value]


def collect_entries(page) -> list[ReviewEntry]:
    """Collapse wrapped highlight objects into independent page comments."""
    grouped: dict[tuple[str, str, str], list] = {}
    for annotation in page.obj.get("/Annots", []):
        subtype = str(annotation.get("/Subtype", ""))
        if subtype not in {"/Highlight", "/Text"}:
            continue
        if str(annotation.get("/T", "")) != "中文同行审阅":
            continue
        subject = str(annotation.get("/Subj", ""))
        contents = str(annotation.get("/Contents", ""))
        key = (subtype, subject, contents)
        grouped.setdefault(key, []).append(annotation)

    entries: list[ReviewEntry] = []
    for (subtype, subject, contents), annotations in grouped.items():
        rects = [annotation_rect(annotation) for annotation in annotations]
        # Use the first/highest wrapped segment as the visible badge anchor.
        target_y = max((rect[1] + rect[3]) / 2.0 for rect in rects)
        entries.append(
            ReviewEntry(
                annotations=annotations,
                subtype=subtype,
                subject=subject,
                contents=contents,
                color=annotation_color(annotations[0]),
                rects=rects,
                target_y=target_y,
            )
        )
    entries.sort(key=lambda item: (-item.target_y, item.subject))
    return entries


def assign_numbers(entries: list[ReviewEntry], page_number: int, page_height: float) -> None:
    previous_y = page_height + 20.0
    for number, entry in enumerate(entries, start=1):
        entry.number = number
        entry.code = f"P{page_number:02d}-{number:02d}"
        proposed = min(page_height - 14.0, max(14.0, entry.target_y))
        if previous_y - proposed < 16.0:
            proposed = previous_y - 16.0
        entry.badge_y = max(12.0, proposed)
        previous_y = entry.badge_y

        old_subject = entry.subject
        old_contents = entry.contents
        entry.subject = f"{entry.code}｜{old_subject}"
        entry.contents = f"【对应可见侧栏】{entry.code}。{old_contents}"
        for annotation in entry.annotations:
            annotation["/Subj"] = String(entry.subject)
            annotation["/Contents"] = String(entry.contents)


SECTION_PATTERN = re.compile(r"【([^】]+)】(.*?)(?=【[^】]+】|$)", re.S)


def sections_from_comment(contents: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    for label, text in SECTION_PATTERN.findall(contents):
        cleaned = text.strip().strip("｜").strip()
        if cleaned:
            sections[label] = cleaned
    return sections


def sidebar_segments(entry: ReviewEntry) -> list[tuple[str, str]]:
    sections = sections_from_comment(entry.contents)
    original_subject = entry.subject.split("｜", 1)[1] if "｜" in entry.subject else entry.subject
    rid = original_subject.split("｜", 1)[0]

    if rid == "A00":
        return [
            (
                "使用方法",
                "左侧每个彩色标注旁都有编号；在本页右栏找到同一编号，直接按“修改动作”处理。颜色表示优先级，不表示具体修改方式。",
            ),
            (
                "优先顺序",
                "先处理阈值与击中存储、死时间和屏蔽计数率、Laue 物理验证、源流归一化、同口径比较、有限统计与似然、真实观测几何及投稿可复现性。",
            ),
        ]

    if rid.startswith("Re-"):
        return [("复核结论与动作", sections.get("第二轮复核", entry.contents))]

    result: list[tuple[str, str]] = []
    if "7 月 14 日状态" in sections:
        result.append(("当前状态", sections["7 月 14 日状态"]))
    if "正式问题" in sections:
        result.append(("问题", sections["正式问题"]))
    if "本处意见" in sections:
        result.append(("为什么标这里", sections["本处意见"]))
    if "修改要求" in sections:
        result.append(("修改动作", sections["修改要求"]))
    if not result:
        result.append(("审阅意见", entry.contents))
    return result


def wrap_text(text: str, font_size: float, width: float) -> list[str]:
    # The visible sidebar uses a GB font that covers Chinese, Latin and Greek.
    # Normalize its handful of missing super/subscript glyphs into readable
    # linear notation; the full Unicode wording remains in the PDF pop-up.
    text = " ".join(text.translate(RENDER_REPLACEMENTS).split())
    if not text:
        return []
    lines: list[str] = []
    current = ""
    for character in text:
        candidate = current + character
        if current and pdfmetrics.stringWidth(candidate, FONT_NAME, font_size) > width:
            lines.append(current.rstrip())
            current = character.lstrip()
        else:
            current = candidate
    if current:
        lines.append(current.rstrip())
    return lines


def entry_lines(entry: ReviewEntry, body_size: float, width: float) -> list[tuple[str, bool]]:
    lines: list[tuple[str, bool]] = []
    for label, text in sidebar_segments(entry):
        wrapped = wrap_text(f"{label}：{text}", body_size, width)
        lines.extend((line, False) for line in wrapped)
    return lines


def choose_body_size(entries: list[ReviewEntry], width: float, available_height: float) -> tuple[float, float]:
    for body_size in (7.4, 7.0, 6.6, 6.2, 5.8):
        leading = body_size + 2.0
        total = 0.0
        for entry in entries:
            total += 21.0 + len(entry_lines(entry, body_size, width)) * leading
        total += max(0, len(entries) - 1) * 5.0
        if total <= available_height:
            return body_size, leading
    raise RuntimeError("Visible sidebar text does not fit without truncation")


def light_fill(color: tuple[float, float, float]) -> Color:
    return Color(*(0.90 + 0.10 * component for component in color))


def text_color(color: tuple[float, float, float]) -> Color:
    luminance = 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]
    return Color(0.08, 0.08, 0.08) if luminance > 0.68 else Color(1, 1, 1)


def draw_badges(c: canvas.Canvas, entries: list[ReviewEntry], manuscript_width: float) -> None:
    badge_x = manuscript_width - 11.0
    for entry in entries:
        target_x = min(manuscript_width - 24.0, max(rect[2] for rect in entry.rects) + 3.0)
        c.setStrokeColor(Color(*entry.color))
        c.setLineWidth(0.65)
        c.line(target_x, entry.target_y, badge_x - 7.5, entry.badge_y)
        c.setFillColor(Color(*entry.color))
        c.circle(badge_x, entry.badge_y, 7.2, stroke=0, fill=1)
        c.setFillColor(text_color(entry.color))
        c.setFont(FONT_NAME, 6.2 if entry.number < 10 else 5.5)
        number = str(entry.number)
        number_width = pdfmetrics.stringWidth(number, FONT_NAME, 6.2 if entry.number < 10 else 5.5)
        c.drawString(badge_x - number_width / 2.0, entry.badge_y - 2.2, number)


def draw_sidebar(
    c: canvas.Canvas,
    entries: list[ReviewEntry],
    page_number: int,
    page_count: int,
    manuscript_width: float,
    page_height: float,
) -> None:
    panel_x = manuscript_width
    panel_width = SIDEBAR_WIDTH
    c.setFillColor(Color(0.965, 0.97, 0.975))
    c.rect(panel_x, 0, panel_width, page_height, stroke=0, fill=1)
    c.setStrokeColor(Color(0.36, 0.42, 0.48))
    c.setLineWidth(1.0)
    c.line(panel_x, 0, panel_x, page_height)

    margin = 15.0
    content_x = panel_x + margin
    content_width = panel_width - 2.0 * margin
    c.setFillColor(Color(0.11, 0.18, 0.25))
    c.rect(panel_x, page_height - 62.0, panel_width, 62.0, stroke=0, fill=1)
    c.setFillColor(Color(1, 1, 1))
    c.setFont(FONT_NAME, 13.0)
    c.drawString(content_x, page_height - 23.0, f"本页修改意见｜第 {page_number}/{page_count} 页")
    c.setFont(FONT_NAME, 8.0)
    c.drawString(content_x, page_height - 39.0, "左侧编号与右栏一一对应；每条均说明为什么标注、具体怎么改。")
    c.setFont(FONT_NAME, 6.8)
    c.drawString(content_x, page_height - 52.0, "红=重大　橙=中等　蓝=结构　绿=期刊　紫/青=第二轮")

    if not entries:
        c.setFillColor(Color(0.28, 0.32, 0.36))
        c.setFont(FONT_NAME, 10.0)
        c.drawString(content_x, page_height - 100.0, "本页没有单独修改项。")
        return

    top_y = page_height - 73.0
    bottom_y = 31.0
    body_size, leading = choose_body_size(entries, content_width - 16.0, top_y - bottom_y)
    y = top_y

    for entry in entries:
        body_lines = entry_lines(entry, body_size, content_width - 16.0)
        box_height = 18.0 + len(body_lines) * leading + 3.0
        c.setFillColor(light_fill(entry.color))
        c.setStrokeColor(Color(*entry.color))
        c.setLineWidth(0.8)
        c.roundRect(content_x, y - box_height, content_width, box_height, 4.0, stroke=1, fill=1)

        c.setFillColor(Color(*entry.color))
        c.roundRect(content_x + 5.0, y - 15.0, 15.0, 12.0, 3.0, stroke=0, fill=1)
        c.setFillColor(text_color(entry.color))
        c.setFont(FONT_NAME, 7.0 if entry.number < 10 else 6.2)
        number = str(entry.number)
        number_width = pdfmetrics.stringWidth(number, FONT_NAME, 7.0 if entry.number < 10 else 6.2)
        c.drawString(content_x + 12.5 - number_width / 2.0, y - 12.1, number)

        original_subject = entry.subject.split("｜", 1)[1] if "｜" in entry.subject else entry.subject
        c.setFillColor(Color(0.10, 0.13, 0.16))
        c.setFont(FONT_NAME, 8.0)
        header = f"{entry.code}｜{original_subject}"
        header_lines = wrap_text(header, 8.0, content_width - 30.0)
        # Subjects are deliberately compact; use the first line and let the body carry detail.
        c.drawString(content_x + 24.0, y - 12.0, header_lines[0])

        text_y = y - 24.0
        c.setFillColor(Color(0.12, 0.14, 0.16))
        c.setFont(FONT_NAME, body_size)
        for line, _is_header in body_lines:
            c.drawString(content_x + 8.0, text_y, line)
            text_y -= leading
        y -= box_height + 5.0

    if y < bottom_y - 0.5:
        raise RuntimeError(f"Sidebar overflow on page {page_number}: y={y:.2f}")

    c.setFillColor(Color(0.35, 0.38, 0.42))
    c.setFont(FONT_NAME, 6.5)
    c.drawString(content_x, 14.0, "完整说明、依据和基线页码仍保留在可点击批注中；右栏已包含可执行修改动作。")


def page_stream_payloads(page) -> list[bytes]:
    contents = page.obj.get("/Contents")
    if contents is None:
        return []
    streams: Iterable = contents if isinstance(contents, pikepdf.Array) else [contents]
    return [stream.read_bytes() for stream in streams]


def main() -> None:
    if not INPUT_PDF.exists():
        raise SystemExit(f"Input PDF not found: {INPUT_PDF}")
    if not INPUT_VALIDATION_JSON.exists():
        raise SystemExit(f"Input validation not found: {INPUT_VALIDATION_JSON}")
    if not FONT_PATH.exists():
        raise SystemExit(f"Chinese font not found: {FONT_PATH}")
    pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))

    input_sha256 = hashlib.sha256(INPUT_PDF.read_bytes()).hexdigest()
    input_validation = json.loads(INPUT_VALIDATION_JSON.read_text(encoding="utf-8"))
    input_validation_hash_match = (
        input_validation.get("status") == "PASS"
        and input_validation.get("output_sha256") == input_sha256
    )

    temporary_output = OUTPUT_PDF.with_suffix(".tmp.pdf")
    page_models: list[tuple[float, float, list[ReviewEntry]]] = []
    original_payloads: list[list[bytes]] = []
    page_entry_count = 0
    baseline_link_count = 0

    with pikepdf.open(INPUT_PDF) as pdf:
        page_count = len(pdf.pages)
        if page_count < 1:
            raise RuntimeError("Current integrated review PDF has no pages")

        for page_number, page in enumerate(pdf.pages, start=1):
            box = [float(value) for value in page.obj.MediaBox]
            width, height = box[2] - box[0], box[3] - box[1]
            if box[0] != 0.0 or box[1] != 0.0:
                raise RuntimeError(f"Unsupported non-zero page origin on page {page_number}: {box}")
            entries = collect_entries(page)
            assign_numbers(entries, page_number, height)
            page_models.append((width, height, entries))
            page_entry_count += len(entries)
            baseline_link_count += sum(
                1
                for annotation in page.obj.get("/Annots", [])
                if str(annotation.get("/Subtype", "")) == "/Link"
            )
            original_payloads.append(page_stream_payloads(page))

        overlay = canvas.Canvas(str(OVERLAY_PDF), pageCompression=1)
        for page_number, (width, height, entries) in enumerate(page_models, start=1):
            overlay.setPageSize((width + SIDEBAR_WIDTH, height))
            draw_badges(overlay, entries, width)
            draw_sidebar(overlay, entries, page_number, page_count, width, height)
            overlay.showPage()
        overlay.save()

        with pikepdf.open(OVERLAY_PDF) as overlay_pdf:
            if len(overlay_pdf.pages) != page_count:
                raise RuntimeError("Overlay page count mismatch")
            for index, page in enumerate(pdf.pages):
                width, height, _entries = page_models[index]
                expanded_box = Array([0, 0, width + SIDEBAR_WIDTH, height])
                page.obj["/MediaBox"] = expanded_box
                page.obj["/CropBox"] = Array(expanded_box)
                for optional_box in ("/TrimBox", "/BleedBox", "/ArtBox"):
                    if optional_box in page.obj:
                        page.obj[optional_box] = Array(expanded_box)
                page.add_overlay(
                    overlay_pdf.pages[index],
                    Rectangle(0, 0, width + SIDEBAR_WIDTH, height),
                    shrink=True,
                    expand=True,
                )

        pdf.docinfo["/Title"] = String("EA draft peer review — visible Chinese action sidebar")
        pdf.save(temporary_output)

    os.replace(temporary_output, OUTPUT_PDF)
    if OVERLAY_PDF.exists():
        OVERLAY_PDF.unlink()

    highlight_count = 0
    text_note_count = 0
    link_count = 0
    numbered_annotations = 0
    preserved_original_streams = True
    widths_ok = True
    page_entries_recounted = 0
    review_ids_present: set[str] = set()
    resolved_ids_still_present: set[str] = set()
    root_features = {}
    with pikepdf.open(OUTPUT_PDF) as check:
        root_features = {
            "outlines": "/Outlines" in check.Root,
            "names": "/Names" in check.Root,
            "open_action": "/OpenAction" in check.Root,
        }
        for index, page in enumerate(check.pages):
            width, height, _entries = page_models[index]
            box = [float(value) for value in page.obj.MediaBox]
            widths_ok &= abs((box[2] - box[0]) - (width + SIDEBAR_WIDTH)) < 0.02
            output_payload = b"".join(page_stream_payloads(page))
            # pikepdf wraps the original stream in q/Q before invoking the
            # sidebar Form XObject.  Require every original decoded stream to
            # remain byte-for-byte embedded inside that wrapper.
            preserved_original_streams &= all(
                item in output_payload for item in original_payloads[index]
            )
            seen_page_codes: set[str] = set()
            for annotation in page.obj.get("/Annots", []):
                subtype = str(annotation.get("/Subtype", ""))
                if subtype == "/Link":
                    link_count += 1
                    continue
                if subtype not in {"/Highlight", "/Text"}:
                    continue
                if subtype == "/Highlight":
                    highlight_count += 1
                else:
                    text_note_count += 1
                subject = str(annotation.get("/Subj", ""))
                contents = str(annotation.get("/Contents", ""))
                expected_prefix = f"P{index + 1:02d}-"
                if subject.startswith(expected_prefix) and contents.startswith("【对应可见侧栏】"):
                    numbered_annotations += 1
                    seen_page_codes.add(subject.split("｜", 1)[0])
                    original_subject = subject.split("｜", 1)[1] if "｜" in subject else subject
                    rid = original_subject.split("｜", 1)[0]
                    review_ids_present.add(rid)
                    if rid in RESOLVED_REVIEW_IDS:
                        resolved_ids_still_present.add(rid)
            page_entries_recounted += len(seen_page_codes)

    validation = {
        "input_pdf": INPUT_PDF.name,
        "output_pdf": OUTPUT_PDF.name,
        "pages": len(page_models),
        "visible_sidebar_width_pt": SIDEBAR_WIDTH,
        "unique_page_sidebar_entries": page_entry_count,
        "unique_page_sidebar_entries_recounted": page_entries_recounted,
        "numbered_review_annotation_objects": numbered_annotations,
        "highlight_objects_preserved": highlight_count,
        "text_note_objects_preserved": text_note_count,
        "link_annotations_preserved": link_count,
        "original_manuscript_content_streams_preserved": preserved_original_streams,
        "expanded_page_boxes_valid": widths_ok,
        "catalog_navigation_features": root_features,
        "input_validation": INPUT_VALIDATION_JSON.name,
        "input_sha256": input_sha256,
        "input_validation_hash_match": input_validation_hash_match,
        "expected_formal_review_ids": sorted(EXPECTED_FORMAL_REVIEW_IDS),
        "expected_supplemental_review_ids": sorted(EXPECTED_SUPPLEMENTAL_REVIEW_IDS),
        "review_ids_present": sorted(review_ids_present),
        "missing_review_ids": sorted(EXPECTED_REVIEW_IDS - review_ids_present),
        "unexpected_review_ids": sorted(review_ids_present - EXPECTED_REVIEW_IDS),
        "resolved_review_ids_removed": sorted(RESOLVED_REVIEW_IDS),
        "resolved_review_ids_still_present": sorted(resolved_ids_still_present),
        "output_sha256": hashlib.sha256(OUTPUT_PDF.read_bytes()).hexdigest(),
    }
    validation["status"] = (
        "PASS"
        if len(page_models) > 0
        and page_entry_count == EXPECTED_PAGE_SIDEBAR_ENTRIES
        and page_entry_count == page_entries_recounted
        and numbered_annotations == highlight_count + text_note_count
        and highlight_count > 0
        and text_note_count == 7
        and link_count == baseline_link_count
        and input_validation_hash_match
        and review_ids_present == EXPECTED_REVIEW_IDS
        and not resolved_ids_still_present
        and preserved_original_streams
        and widths_ok
        and all(root_features.values())
        else "FAIL"
    )
    VALIDATION_JSON.write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if validation["status"] != "PASS":
        raise RuntimeError(json.dumps(validation, ensure_ascii=False, indent=2))
    print(json.dumps(validation, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
