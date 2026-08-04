#!/usr/bin/env python3
"""Build the highlighted Chinese manuscript with its Chinese action sidebar.

The Chinese manuscript on the left is a sentence-aligned reading translation
of the current English authority.  Review entries and their Pxx-xx identifiers
are anchored directly on the translated Chinese phrases, rendered as coloured
highlights, and connected to the visible right sidebar.  Pxx-xx identifiers are
therefore based on the Chinese reading edition's own pagination and line order.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from typing import Iterable

try:
    import pikepdf
    from pikepdf import Array, Rectangle, String
except ImportError as exc:  # pragma: no cover - environment guidance
    raise SystemExit(
        "pikepdf is required. Install python3-pikepdf or expose it on PYTHONPATH."
    ) from exc

from reportlab.lib.colors import Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


HERE = Path(__file__).resolve().parent
MANUSCRIPT_PDF = HERE.parent / "balloon511_ea_draft_zh_peer_review_highlighted_20260714.pdf"
MANUSCRIPT_VALIDATION_JSON = HERE / "ea_peer_review_zh_highlights_validation_20260714.json"
OUTPUT_PDF = HERE / "balloon511_ea_draft_zh_peer_review_visible_sidebar_20260714.pdf"
VALIDATION_JSON = HERE / "ea_peer_review_zh_visible_sidebar_validation_20260714.json"
OVERLAY_PDF = HERE / ".ea_peer_review_zh_visible_sidebar_overlay_20260714.tmp.pdf"
BASE_BUILDER = HERE / "build_visible_chinese_sidebar_pdf_20260714.py"


def load_base_builder():
    spec = importlib.util.spec_from_file_location("ea_visible_sidebar_base", BASE_BUILDER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load sidebar builder: {BASE_BUILDER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


base = load_base_builder()
FONT_PATH = base.FONT_PATH
FONT_NAME = base.FONT_NAME
SIDEBAR_WIDTH = base.SIDEBAR_WIDTH


def sidebar_segments(entry) -> list[tuple[str, str]]:
    original_subject = entry.subject.split("｜", 1)[1] if "｜" in entry.subject else entry.subject
    review_id = original_subject.split("｜", 1)[0]
    if review_id == "A00":
        return [
            (
                "使用方法",
                "中文正文与当前英文稿按章节和段落一一对应；请用右栏的 Pxx-xx 编号指定修改项。",
            ),
            (
                "修改基准",
                "实际修改只落到英文权威稿，随后同步中文译稿和本阅读版；颜色表示优先级。",
            ),
            (
                "优先顺序",
                "先处理阈值与击中存储、死时间和屏蔽计数率、Laue 物理验证、源流归一化、同口径比较、有限统计与似然、真实观测几何及投稿可复现性。",
            ),
        ]
    return base.sidebar_segments(entry)


def entry_lines(entry, body_size: float, width: float) -> list[str]:
    lines: list[str] = []
    for label, content in sidebar_segments(entry):
        lines.extend(base.wrap_text(f"{label}：{content}", body_size, width))
    return lines


def choose_body_size(entries, width: float, available_height: float) -> tuple[float, float]:
    for body_size in (7.4, 7.0, 6.6, 6.2, 5.8, 5.4):
        leading = body_size + 2.0
        total = sum(21.0 + len(entry_lines(entry, body_size, width)) * leading for entry in entries)
        total += max(0, len(entries) - 1) * 5.0
        if total <= available_height:
            return body_size, leading
    raise RuntimeError("Chinese review sidebar text does not fit without truncation")


def draw_sidebar(
    pdf_canvas: canvas.Canvas,
    entries,
    page_number: int,
    page_count: int,
    manuscript_width: float,
    page_height: float,
) -> None:
    panel_x = manuscript_width
    panel_width = SIDEBAR_WIDTH
    pdf_canvas.setFillColor(Color(0.965, 0.97, 0.975))
    pdf_canvas.rect(panel_x, 0, panel_width, page_height, stroke=0, fill=1)
    pdf_canvas.setStrokeColor(Color(0.36, 0.42, 0.48))
    pdf_canvas.setLineWidth(1.0)
    pdf_canvas.line(panel_x, 0, panel_x, page_height)

    margin = 15.0
    content_x = panel_x + margin
    content_width = panel_width - 2.0 * margin
    pdf_canvas.setFillColor(Color(0.11, 0.18, 0.25))
    pdf_canvas.rect(panel_x, page_height - 62.0, panel_width, 62.0, stroke=0, fill=1)
    pdf_canvas.setFillColor(Color(1, 1, 1))
    pdf_canvas.setFont(FONT_NAME, 13.0)
    pdf_canvas.drawString(content_x, page_height - 23.0, f"本页修改意见｜第 {page_number}/{page_count} 页")
    pdf_canvas.setFont(FONT_NAME, 8.0)
    pdf_canvas.drawString(content_x, page_height - 39.0, "左侧为当前英文稿的逐句中文译稿；右栏编号沿用英文审阅版。")
    pdf_canvas.setFont(FONT_NAME, 6.8)
    pdf_canvas.drawString(content_x, page_height - 52.0, "红=重大　橙=中等　蓝=结构　绿=期刊　紫/青=第二轮")

    if not entries:
        pdf_canvas.setFillColor(Color(0.28, 0.32, 0.36))
        pdf_canvas.setFont(FONT_NAME, 10.0)
        pdf_canvas.drawString(content_x, page_height - 100.0, "本页没有单独修改项。")
    else:
        top_y = page_height - 73.0
        bottom_y = 31.0
        body_size, leading = choose_body_size(entries, content_width - 16.0, top_y - bottom_y)
        y = top_y

        for entry in entries:
            body_lines = entry_lines(entry, body_size, content_width - 16.0)
            box_height = 18.0 + len(body_lines) * leading + 3.0
            pdf_canvas.setFillColor(base.light_fill(entry.color))
            pdf_canvas.setStrokeColor(Color(*entry.color))
            pdf_canvas.setLineWidth(0.8)
            pdf_canvas.roundRect(content_x, y - box_height, content_width, box_height, 4.0, stroke=1, fill=1)

            pdf_canvas.setFillColor(Color(*entry.color))
            pdf_canvas.roundRect(content_x + 5.0, y - 15.0, 15.0, 12.0, 3.0, stroke=0, fill=1)
            number_size = 7.0 if entry.number < 10 else 6.2
            number_text = str(entry.number)
            pdf_canvas.setFillColor(base.text_color(entry.color))
            pdf_canvas.setFont(FONT_NAME, number_size)
            number_width = pdfmetrics.stringWidth(number_text, FONT_NAME, number_size)
            pdf_canvas.drawString(content_x + 12.5 - number_width / 2.0, y - 12.1, number_text)

            original_subject = entry.subject.split("｜", 1)[1] if "｜" in entry.subject else entry.subject
            header = f"{entry.code}｜{original_subject}"
            header_lines = base.wrap_text(header, 8.0, content_width - 30.0)
            pdf_canvas.setFillColor(Color(0.10, 0.13, 0.16))
            pdf_canvas.setFont(FONT_NAME, 8.0)
            pdf_canvas.drawString(content_x + 24.0, y - 12.0, header_lines[0])

            text_y = y - 24.0
            pdf_canvas.setFillColor(Color(0.12, 0.14, 0.16))
            pdf_canvas.setFont(FONT_NAME, body_size)
            for line in body_lines:
                pdf_canvas.drawString(content_x + 8.0, text_y, line)
                text_y -= leading
            y -= box_height + 5.0

        if y < bottom_y - 0.5:
            raise RuntimeError(f"Sidebar overflow on page {page_number}: y={y:.2f}")

    pdf_canvas.setFillColor(Color(0.35, 0.38, 0.42))
    pdf_canvas.setFont(FONT_NAME, 6.5)
    pdf_canvas.drawString(content_x, 14.0, "中文正文用于阅读；实际修改以英文权威稿为准并同步回本译稿。")


def page_stream_payloads(page) -> list[bytes]:
    contents = page.obj.get("/Contents")
    if contents is None:
        return []
    streams: Iterable = contents if isinstance(contents, pikepdf.Array) else [contents]
    return [stream.read_bytes() for stream in streams]


def main() -> None:
    for required_path in (MANUSCRIPT_PDF, MANUSCRIPT_VALIDATION_JSON, BASE_BUILDER, FONT_PATH):
        if not required_path.exists():
            raise SystemExit(f"Required input not found: {required_path}")
    pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))

    manuscript_sha256 = hashlib.sha256(MANUSCRIPT_PDF.read_bytes()).hexdigest()
    manuscript_validation = json.loads(MANUSCRIPT_VALIDATION_JSON.read_text(encoding="utf-8"))
    manuscript_validation_hash_match = (
        manuscript_validation.get("status") == "PASS"
        and manuscript_validation.get("output_sha256") == manuscript_sha256
    )

    temporary_output = OUTPUT_PDF.with_suffix(".tmp.pdf")
    page_models = []
    original_payloads: list[list[bytes]] = []
    sidebar_entry_count = 0
    baseline_highlight_count = 0
    baseline_text_note_count = 0
    baseline_link_count = 0

    with pikepdf.open(MANUSCRIPT_PDF) as manuscript_pdf:
        page_count = len(manuscript_pdf.pages)
        if page_count < 1:
            raise RuntimeError("Highlighted Chinese manuscript has no pages")

        baseline_highlight_count = sum(
            1
            for page in manuscript_pdf.pages
            for annotation in page.obj.get("/Annots", [])
            if str(annotation.get("/Subtype", "")) == "/Highlight"
        )
        baseline_text_note_count = sum(
            1
            for page in manuscript_pdf.pages
            for annotation in page.obj.get("/Annots", [])
            if str(annotation.get("/Subtype", "")) == "/Text"
        )
        baseline_link_count = sum(
            1
            for page in manuscript_pdf.pages
            for annotation in page.obj.get("/Annots", [])
            if str(annotation.get("/Subtype", "")) == "/Link"
        )

        for page_number, manuscript_page in enumerate(manuscript_pdf.pages, start=1):
            manuscript_box = [float(value) for value in manuscript_page.obj.MediaBox]
            if manuscript_box[0] != 0.0 or manuscript_box[1] != 0.0:
                raise RuntimeError(f"Unsupported Chinese page origin on page {page_number}: {manuscript_box}")
            width = manuscript_box[2] - manuscript_box[0]
            height = manuscript_box[3] - manuscript_box[1]
            entries = base.collect_entries(manuscript_page)
            base.assign_numbers(entries, page_number, height)
            page_models.append((width, height, entries))
            sidebar_entry_count += len(entries)
            original_payloads.append(page_stream_payloads(manuscript_page))

        overlay = canvas.Canvas(str(OVERLAY_PDF), pageCompression=1)
        for page_number, (width, height, entries) in enumerate(page_models, start=1):
            overlay.setPageSize((width + SIDEBAR_WIDTH, height))
            base.draw_badges(overlay, entries, width)
            draw_sidebar(overlay, entries, page_number, page_count, width, height)
            overlay.showPage()
        overlay.save()

        with pikepdf.open(OVERLAY_PDF) as overlay_pdf:
            if len(overlay_pdf.pages) != page_count:
                raise RuntimeError("Overlay page count mismatch")
            for index, page in enumerate(manuscript_pdf.pages):
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

        manuscript_pdf.docinfo["/Title"] = String("EA draft — highlighted Chinese manuscript with visible action sidebar")
        manuscript_pdf.save(temporary_output)

    os.replace(temporary_output, OUTPUT_PDF)
    if OVERLAY_PDF.exists():
        OVERLAY_PDF.unlink()

    preserved_original_streams = True
    expanded_boxes_valid = True
    rendered_sidebar_codes = 0
    highlight_count = 0
    text_note_count = 0
    link_count = 0
    numbered_review_annotation_objects = 0
    review_ids_present: set[str] = set()
    root_features = {}
    with pikepdf.open(OUTPUT_PDF) as check:
        root_features = {
            "outlines": "/Outlines" in check.Root,
            "names": "/Names" in check.Root,
            "open_action": "/OpenAction" in check.Root,
        }
        for index, page in enumerate(check.pages):
            width, _height, entries = page_models[index]
            box = [float(value) for value in page.obj.MediaBox]
            expanded_boxes_valid &= abs((box[2] - box[0]) - (width + SIDEBAR_WIDTH)) < 0.02
            output_payload = b"".join(page_stream_payloads(page))
            preserved_original_streams &= all(payload in output_payload for payload in original_payloads[index])
            page_codes: set[str] = set()
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
                    numbered_review_annotation_objects += 1
                    page_codes.add(subject.split("｜", 1)[0])
                    original_subject = subject.split("｜", 1)[1] if "｜" in subject else subject
                    review_ids_present.add(original_subject.split("｜", 1)[0])
            rendered_sidebar_codes += len(page_codes)

    validation = {
        "manuscript_pdf": MANUSCRIPT_PDF.name,
        "output_pdf": OUTPUT_PDF.name,
        "pages": len(page_models),
        "visible_sidebar_width_pt": SIDEBAR_WIDTH,
        "unique_page_sidebar_entries": sidebar_entry_count,
        "unique_page_sidebar_entries_recounted": rendered_sidebar_codes,
        "highlight_objects_preserved": highlight_count,
        "text_note_objects_preserved": text_note_count,
        "numbered_review_annotation_objects": numbered_review_annotation_objects,
        "link_annotations_preserved": link_count,
        "original_chinese_content_streams_preserved": preserved_original_streams,
        "expanded_page_boxes_valid": expanded_boxes_valid,
        "catalog_navigation_features": root_features,
        "manuscript_validation": MANUSCRIPT_VALIDATION_JSON.name,
        "manuscript_sha256": manuscript_sha256,
        "manuscript_validation_hash_match": manuscript_validation_hash_match,
        "expected_formal_review_ids": sorted(base.EXPECTED_FORMAL_REVIEW_IDS),
        "expected_supplemental_review_ids": sorted(base.EXPECTED_SUPPLEMENTAL_REVIEW_IDS),
        "review_ids_present": sorted(review_ids_present),
        "missing_review_ids": sorted(base.EXPECTED_REVIEW_IDS - review_ids_present),
        "unexpected_review_ids": sorted(review_ids_present - base.EXPECTED_REVIEW_IDS),
        "output_sha256": hashlib.sha256(OUTPUT_PDF.read_bytes()).hexdigest(),
    }
    validation["status"] = (
        "PASS"
        if len(page_models) > 0
        and sidebar_entry_count == base.EXPECTED_PAGE_SIDEBAR_ENTRIES
        and sidebar_entry_count == rendered_sidebar_codes
        and highlight_count == baseline_highlight_count
        and text_note_count == baseline_text_note_count == 1
        and numbered_review_annotation_objects == highlight_count + text_note_count
        and link_count == baseline_link_count
        and manuscript_validation_hash_match
        and review_ids_present == base.EXPECTED_REVIEW_IDS
        and preserved_original_streams
        and expanded_boxes_valid
        and all(root_features.values())
        else "FAIL"
    )
    VALIDATION_JSON.write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if validation["status"] != "PASS":
        raise RuntimeError(json.dumps(validation, ensure_ascii=False, indent=2))
    print(json.dumps(validation, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
