#!/usr/bin/env python3
"""Add line-level Chinese review highlights to the Chinese manuscript PDF.

Text coordinates come from the rendered Chinese PDF itself.  English review
coordinates are never copied, so every highlight follows the translated line
breaks.  The annotation text is the same complete Chinese finding/action text
used by the visible action sidebar.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess

from lxml import etree

try:
    import pikepdf
    from pikepdf import Array, Dictionary, Name, String
except ImportError as exc:  # pragma: no cover - environment guidance
    raise SystemExit(
        "pikepdf is required. Install python3-pikepdf or expose it on PYTHONPATH."
    ) from exc


HERE = Path(__file__).resolve().parent
MANUSCRIPT_DIR = HERE.parent
INPUT_PDF = MANUSCRIPT_DIR / "balloon511_ea_draft_zh.pdf"
OUTPUT_PDF = MANUSCRIPT_DIR / "balloon511_ea_draft_zh_peer_review_highlighted_20260714.pdf"
VALIDATION_JSON = HERE / "ea_peer_review_zh_highlights_validation_20260714.json"
BBOX_XML = HERE / ".balloon511_ea_draft_zh_bbox_20260714.tmp.html"
EN_DEFINITIONS = HERE / "build_peer_review.py"
CN_DEFINITIONS = HERE / "build_peer_review_cn_integrated_20260714.py"
ANCHOR_DEFINITIONS = HERE / "build_chinese_highlighted_review_tex_20260714.py"


@dataclass(frozen=True)
class Word:
    line: int
    text: str
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass(frozen=True)
class LocatedSegment:
    page: int
    x0: float
    y0: float
    x1: float
    y1: float


HYPHENS = str.maketrans({"–": "-", "—": "-", "−": "-", "‑": "-"})


def normalized_char(character: str) -> str:
    if character.isspace() or character in {"\u200b", "\ufeff"}:
        return ""
    return character.translate(HYPHENS)


def normalized_text(text: str) -> str:
    value = "".join(normalized_char(character) for character in text)
    while "--" in value:
        value = value.replace("--", "-")
    return value


def extract_bbox_pages() -> tuple[list[list[Word]], list[float]]:
    subprocess.run(
        ["pdftotext", "-bbox-layout", str(INPUT_PDF), str(BBOX_XML)],
        check=True,
        capture_output=True,
        text=True,
    )
    parser = etree.HTMLParser(recover=True, encoding="utf-8")
    root = etree.parse(str(BBOX_XML), parser).getroot()
    pages: list[list[Word]] = []
    heights: list[float] = []
    for page in root.xpath("//page"):
        heights.append(float(page.attrib["height"]))
        words: list[Word] = []
        line_number = 0
        for line in page.xpath(".//line"):
            for element in line.xpath("./word"):
                words.append(
                    Word(
                        line=line_number,
                        text="".join(element.itertext()),
                        x0=float(element.attrib["xmin"]),
                        y0=float(element.attrib["ymin"]),
                        x1=float(element.attrib["xmax"]),
                        y1=float(element.attrib["ymax"]),
                    )
                )
            line_number += 1
        pages.append(words)
    return pages, heights


def page_character_map(words: list[Word]):
    text: list[str] = []
    mapping: list[tuple[int, int]] = []
    for word_index, word in enumerate(words):
        for character_index, character in enumerate(word.text):
            normalized = normalized_char(character)
            if normalized:
                text.append(normalized)
                mapping.append((word_index, character_index))
    return "".join(text), mapping


def locate_anchor(anchor: str, pages: list[list[Word]]) -> list[LocatedSegment]:
    target = normalized_text(anchor)
    matches: list[tuple[int, int, int, list[tuple[int, int]], list[Word]]] = []
    for page_index, words in enumerate(pages):
        page_text, mapping = page_character_map(words)
        cursor = 0
        while True:
            start = page_text.find(target, cursor)
            if start < 0:
                break
            matches.append((page_index, start, start + len(target), mapping, words))
            cursor = start + 1
    if len(matches) != 1:
        raise RuntimeError(f"Expected one rendered match for {anchor!r}; found {len(matches)}")

    page_index, start, end, mapping, words = matches[0]
    per_word: dict[int, list[int]] = {}
    for word_index, character_index in mapping[start:end]:
        per_word.setdefault(word_index, []).append(character_index)

    per_line: dict[int, list[tuple[float, float, float, float]]] = {}
    for word_index, character_indices in per_word.items():
        word = words[word_index]
        character_count = max(1, len(word.text))
        first = min(character_indices)
        last = max(character_indices) + 1
        width = word.x1 - word.x0
        x0 = word.x0 + width * first / character_count
        x1 = word.x0 + width * last / character_count
        per_line.setdefault(word.line, []).append((x0, word.y0, x1, word.y1))

    segments: list[LocatedSegment] = []
    for line in sorted(per_line):
        boxes = per_line[line]
        segments.append(
            LocatedSegment(
                page=page_index,
                x0=min(box[0] for box in boxes),
                y0=min(box[1] for box in boxes),
                x1=max(box[2] for box in boxes),
                y1=max(box[3] for box in boxes),
            )
        )
    return segments


def page_content_digest(page) -> str:
    contents = page.obj.get("/Contents")
    if contents is None:
        return hashlib.sha256(b"").hexdigest()
    streams = contents if isinstance(contents, pikepdf.Array) else [contents]
    payload = b"".join(stream.read_bytes() for stream in streams)
    return hashlib.sha256(payload).hexdigest()


def add_highlight(
    pdf,
    page,
    *,
    segment: LocatedSegment,
    page_height: float,
    subject: str,
    contents: str,
    color: tuple[float, float, float],
    unique_name: str,
) -> None:
    padding = 0.8
    left = segment.x0 - padding
    right = segment.x1 + padding
    top = page_height - segment.y0 + padding
    bottom = page_height - segment.y1 - padding
    stamp = datetime.now(timezone.utc).strftime("D:%Y%m%d%H%M%S+00'00'")
    annotation = Dictionary(
        {
            "/Type": Name("/Annot"),
            "/Subtype": Name("/Highlight"),
            "/Rect": Array([left, bottom, right, top]),
            "/QuadPoints": Array([left, top, right, top, left, bottom, right, bottom]),
            "/T": String("中文同行审阅"),
            "/Subj": String(subject),
            "/Contents": String(contents),
            "/C": Array(color),
            "/CA": 0.38,
            "/F": 4,
            "/NM": String(unique_name),
            "/M": String(stamp),
            "/CreationDate": String(stamp),
        }
    )
    annots = page.obj.get("/Annots")
    if annots is None:
        page.obj["/Annots"] = Array()
        annots = page.obj["/Annots"]
    annots.append(pdf.make_indirect(annotation))


def add_overview_note(pdf, page, contents: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("D:%Y%m%d%H%M%S+00'00'")
    annotation = Dictionary(
        {
            "/Type": Name("/Annot"),
            "/Subtype": Name("/Text"),
            "/Rect": Array([548, 800, 566, 818]),
            "/T": String("中文同行审阅"),
            "/Subj": String("A00｜总评与阅读说明"),
            "/Contents": String(contents),
            "/C": Array([0.75, 0.75, 0.75]),
            "/Name": Name("/Comment"),
            "/F": 4,
            "/Open": False,
            "/M": String(stamp),
            "/CreationDate": String(stamp),
        }
    )
    annots = page.obj.get("/Annots")
    if annots is None:
        page.obj["/Annots"] = Array()
        annots = page.obj["/Annots"]
    annots.append(pdf.make_indirect(annotation))


def plain_review_body(rid: str, local_note: str, reviews_by_id, cn_defs) -> str:
    if rid.startswith("Re-"):
        return f"【第二轮复核】{local_note}"
    zh = cn_defs["ZH_REVIEWS"][rid]
    meta = reviews_by_id[rid]
    pieces = [
        cn_defs["OVERVIEW_ZH"] if rid == "J02" and local_note.startswith("本处标题过长") else "",
        cn_defs["CURRENT_STATUS_ZH"].get(rid, ""),
        f"【本处意见】{local_note}",
        f"【正式问题】{zh.title}",
        f"【说明】{zh.finding}",
        f"【修改要求】{zh.action}",
        f"【依据】{zh.basis}",
        f"【初始审阅定位页码】{meta.pages}",
    ]
    return " ｜ ".join(piece for piece in pieces if piece)


def main() -> None:
    for path in (INPUT_PDF, EN_DEFINITIONS, CN_DEFINITIONS, ANCHOR_DEFINITIONS):
        if not path.exists():
            raise SystemExit(f"Required input not found: {path}")

    en_defs = runpy.run_path(str(EN_DEFINITIONS), run_name="ea_review_en_defs")
    cn_defs = runpy.run_path(str(CN_DEFINITIONS), run_name="ea_review_cn_defs")
    anchor_defs = runpy.run_path(str(ANCHOR_DEFINITIONS), run_name="ea_review_zh_anchors")
    zh_anchors = anchor_defs["ZH_ANCHORS"]
    formal_anchors = anchor_defs["ZH_FORMAL_ANCHORS"]
    reviews = [*en_defs["REVIEWS"], *en_defs["REVIEWS_R2"]]
    reviews_by_id = {review.rid: review for review in reviews}

    rows: list[tuple[str, str, str]] = []
    for rid, _category, en_anchor, _note, _occurrence in en_defs["ANNOTATIONS"]:
        if rid != "M03":
            rows.append((rid, en_anchor, ""))
    for rid, kind, _category, en_anchor, _note in en_defs["ANNOTATIONS_R2"]:
        rows.append((rid, en_anchor, kind))
    if len(rows) != 52 or len(formal_anchors) != 6:
        raise RuntimeError("Unexpected active review-anchor count")

    bbox_pages, bbox_heights = extract_bbox_pages()
    located_rows = []
    for rid, en_anchor, kind in rows:
        zh_anchor = zh_anchors[(rid, en_anchor)]
        located_rows.append((rid, en_anchor, kind, zh_anchor, locate_anchor(zh_anchor, bbox_pages)))
    for rid, zh_anchor in formal_anchors.items():
        located_rows.append((rid, "", "", zh_anchor, locate_anchor(zh_anchor, bbox_pages)))

    temporary_output = OUTPUT_PDF.with_suffix(".tmp.pdf")
    added_objects = 0
    baseline_link_count = 0
    with pikepdf.open(INPUT_PDF) as pdf:
        if len(pdf.pages) != len(bbox_pages):
            raise RuntimeError("Rendered-text page count differs from PDF page count")
        baseline_hashes = [page_content_digest(page) for page in pdf.pages]
        baseline_root_features = {
            "outlines": "/Outlines" in pdf.Root,
            "names": "/Names" in pdf.Root,
            "open_action": "/OpenAction" in pdf.Root,
        }
        baseline_link_count = sum(
            1
            for page in pdf.pages
            for annotation in page.obj.get("/Annots", [])
            if str(annotation.get("/Subtype", "")) == "/Link"
        )

        for entry_index, (rid, en_anchor, kind, _zh_anchor, segments) in enumerate(located_rows, start=1):
            if en_anchor:
                local_note = cn_defs["PINPOINT_ZH"][(rid, en_anchor)]
            else:
                local_note = "本条原无行内高亮；当前中文阅读稿已将其锚定到对应中文句段。"
            subject = anchor_defs["subject_for"](rid, reviews_by_id, cn_defs)
            contents = plain_review_body(rid, local_note, reviews_by_id, cn_defs)
            if rid.startswith("Re-"):
                color_string = en_defs["R2_COLORS"]["response"]
            elif rid.startswith("N"):
                color_string = en_defs["R2_COLORS"][kind]
            else:
                color_string = cn_defs["COLORS"][reviews_by_id[rid].severity]
            color = tuple(float(value) for value in color_string.split())
            for segment_index, segment in enumerate(segments, start=1):
                add_highlight(
                    pdf,
                    pdf.pages[segment.page],
                    segment=segment,
                    page_height=bbox_heights[segment.page],
                    subject=subject,
                    contents=contents,
                    color=color,
                    unique_name=f"EA-ZH-{entry_index:02d}-{segment_index:02d}",
                )
                added_objects += 1

        add_overview_note(
            pdf,
            pdf.pages[0],
            cn_defs["OVERVIEW_ZH"]
            + "建议先处理：阈值/击中存储、死时间与屏蔽计数率、Laue 物理验证、源流归一化、同口径比较、有限统计与似然、真实观测几何及投稿可复现性。",
        )
        pdf.docinfo["/Title"] = String("EA draft — Chinese manuscript with line-level peer-review highlights")
        pdf.save(temporary_output)

    os.replace(temporary_output, OUTPUT_PDF)
    if BBOX_XML.exists():
        BBOX_XML.unlink()

    highlight_objects = 0
    text_notes = 0
    link_count = 0
    authors_ok = True
    contents_ok = True
    formal_ids: set[str] = set()
    with pikepdf.open(OUTPUT_PDF) as check:
        output_hashes = [page_content_digest(page) for page in check.pages]
        output_root_features = {
            "outlines": "/Outlines" in check.Root,
            "names": "/Names" in check.Root,
            "open_action": "/OpenAction" in check.Root,
        }
        for page in check.pages:
            for annotation in page.obj.get("/Annots", []):
                subtype = str(annotation.get("/Subtype", ""))
                if subtype == "/Link":
                    link_count += 1
                    continue
                if subtype not in {"/Highlight", "/Text"}:
                    continue
                if subtype == "/Highlight":
                    highlight_objects += 1
                else:
                    text_notes += 1
                subject = str(annotation.get("/Subj", ""))
                contents = str(annotation.get("/Contents", ""))
                authors_ok &= str(annotation.get("/T", "")) == "中文同行审阅"
                contents_ok &= any(token in contents for token in ("【正式问题】", "【第二轮复核】", "【阅读说明】"))
                rid = subject.split("｜", 1)[0]
                if rid in reviews_by_id:
                    formal_ids.add(rid)

    expected_formal_ids = set(reviews_by_id) - {"M03"}
    validation = {
        "input_pdf": INPUT_PDF.name,
        "output_pdf": OUTPUT_PDF.name,
        "pages": len(bbox_pages),
        "active_review_entries_highlighted": len(located_rows),
        "highlight_annotation_objects": highlight_objects,
        "overview_text_notes": text_notes,
        "page_content_streams_identical": baseline_hashes == output_hashes,
        "link_annotations_preserved": link_count,
        "catalog_navigation_features_preserved": output_root_features == baseline_root_features,
        "formal_review_ids_covered": len(formal_ids),
        "formal_review_ids_missing": sorted(expected_formal_ids - formal_ids),
        "all_review_annotation_authors_chinese": authors_ok,
        "all_review_annotation_contents_chinese": contents_ok,
        "output_sha256": hashlib.sha256(OUTPUT_PDF.read_bytes()).hexdigest(),
    }
    validation["status"] = (
        "PASS"
        if len(located_rows) == 58
        and highlight_objects == added_objects
        and highlight_objects >= 58
        and text_notes == 1
        and baseline_hashes == output_hashes
        and link_count == baseline_link_count
        and output_root_features == baseline_root_features
        and formal_ids == expected_formal_ids
        and authors_ok
        and contents_ok
        else "FAIL"
    )
    VALIDATION_JSON.write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if validation["status"] != "PASS":
        raise RuntimeError(json.dumps(validation, ensure_ascii=False, indent=2))
    print(json.dumps(validation, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
