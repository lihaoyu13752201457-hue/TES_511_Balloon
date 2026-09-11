#!/usr/bin/env python3
"""Inject full Chinese review text into the current annotated English PDF.

This is the canonical builder for the user-facing dynamic review PDF.  It
edits only annotation dictionaries in the annotated build of the current
English manuscript, so its pages, figures, page breaks, highlight appearance
streams, and link annotations remain synchronized with the working paper.

Dependency: pikepdf 5+ (Ubuntu package: python3-pikepdf).
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import runpy

try:
    import pikepdf
    from pikepdf import Array, Dictionary, Name, String
except ImportError as exc:  # pragma: no cover - environment guidance
    raise SystemExit(
        "pikepdf is required. On Ubuntu install python3-pikepdf, or expose the "
        "package on PYTHONPATH before running this builder."
    ) from exc


HERE = Path(__file__).resolve().parent
BASE_PDF = HERE.parent / "balloon511_ea_draft_en_peer_review_annotated.pdf"
OUTPUT_PDF = HERE / "balloon511_ea_draft_en_peer_review_annotated_cn_integrated_20260714.pdf"
VALIDATION_JSON = HERE / "ea_peer_review_cn_pdf_validation_20260714.json"
REVIEW_DEFINITIONS = HERE / "build_peer_review.py"
ZH_SOURCE = HERE / "build_peer_review_cn_integrated_20260714.py"
RESOLVED_REVIEW_IDS = {"M03"}


MISSING_NOTES = {
    # formal review id: (zero-based page index, icon rectangle)
    "M06": (1, (548, 765, 566, 783)),
    "M14": (3, (548, 765, 566, 783)),
    "M15": (18, (548, 765, 566, 783)),
    "M21": (15, (548, 765, 566, 783)),
    "M22": (19, (548, 765, 566, 783)),
    "J03": (22, (548, 765, 566, 783)),
}


def page_content_digest(page) -> str:
    """Hash decoded page content streams; annotations are intentionally excluded."""
    contents = page.obj.get("/Contents")
    if contents is None:
        return hashlib.sha256(b"").hexdigest()
    streams = contents if isinstance(contents, pikepdf.Array) else [contents]
    payload = b"".join(stream.read_bytes() for stream in streams)
    return hashlib.sha256(payload).hexdigest()


def review_subject(rid: str, meta, zh, severity_zh: dict[str, str]) -> str:
    round_label = "第二轮新增｜" if rid.startswith("N") else ""
    return f"{rid}｜{round_label}{severity_zh[meta.severity]}｜{zh.category}"


def plain_review_body(
    rid: str,
    local_note: str,
    reviews_by_id: dict[str, object],
    zh_reviews: dict[str, object],
    current_status: dict[str, str],
    overview: str,
) -> str:
    """Compose natural Unicode PDF text without TeX-specific escaping."""
    if rid.startswith("Re-"):
        return f"【第二轮复核】{local_note}"
    zh = zh_reviews[rid]
    meta = reviews_by_id[rid]
    pieces = [
        overview if rid == "J02" and local_note.startswith("本处标题过长") else "",
        current_status.get(rid, ""),
        f"【本处意见】{local_note}",
        f"【正式问题】{zh.title}",
        f"【说明】{zh.finding}",
        f"【修改要求】{zh.action}",
        f"【依据】{zh.basis}",
        f"【初始审阅定位页码】{meta.pages}",
    ]
    return " ｜ ".join(piece for piece in pieces if piece)


def add_text_annotation(pdf, page, *, subject: str, contents: str, color, rect, icon="Note") -> None:
    stamp = datetime.now(timezone.utc).strftime("D:%Y%m%d%H%M%S+00'00'")
    annot = Dictionary(
        {
            "/Type": Name("/Annot"),
            "/Subtype": Name("/Text"),
            "/Rect": Array(rect),
            "/T": String("中文同行审阅"),
            "/Subj": String(subject),
            "/Contents": String(contents),
            "/C": Array(color),
            "/Name": Name(f"/{icon}"),
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
    annots.append(pdf.make_indirect(annot))


def main() -> None:
    defs = runpy.run_path(str(REVIEW_DEFINITIONS), run_name="ea_peer_review_definitions")
    zh_defs = runpy.run_path(str(ZH_SOURCE), run_name="ea_peer_review_zh_definitions")

    all_reviews = [*defs["REVIEWS"], *defs["REVIEWS_R2"]]
    reviews_by_id = {review.rid: review for review in all_reviews}
    zh_reviews = zh_defs["ZH_REVIEWS"]
    pinpoint_zh = zh_defs["PINPOINT_ZH"]
    severity_zh = zh_defs["SEVERITY_ZH"]
    colors = zh_defs["COLORS"]
    current_status = zh_defs["CURRENT_STATUS_ZH"]
    overview = zh_defs["OVERVIEW_ZH"]

    def review_body(rid: str, local_note: str, review_map: dict[str, object]) -> str:
        return plain_review_body(
            rid,
            local_note,
            review_map,
            zh_reviews,
            current_status,
            overview,
        )

    # Map each active English /Contents string to the Chinese local comment.
    old_to_zh: dict[str, tuple[str, str]] = {}
    for rid, _category, anchor, note, _occurrence in defs["ANNOTATIONS"]:
        if rid in RESOLVED_REVIEW_IDS:
            continue
        old = defs["tex_note"](f"{rid}. {note} Full rationale and action: HTML review report.")
        old_to_zh[old] = (rid, pinpoint_zh[(rid, anchor)])
    for rid, _kind, _category, anchor, note in defs["ANNOTATIONS_R2"]:
        old = defs["tex_note"](f"{rid}. {note} Full rationale: HTML report, round-2 addendum.")
        old_to_zh[old] = (rid, pinpoint_zh[(rid, anchor)])
    expected_source_comments = len(
        [row for row in defs["ANNOTATIONS"] if row[0] not in RESOLVED_REVIEW_IDS]
    ) + len(defs["ANNOTATIONS_R2"])
    if len(old_to_zh) != expected_source_comments:
        raise RuntimeError(
            f"Expected {expected_source_comments} unique active source annotations, "
            f"found {len(old_to_zh)}"
        )

    tmp_output = OUTPUT_PDF.with_suffix(".tmp.pdf")
    updated_highlights = 0
    resolved_highlights_removed = 0
    seen_source_comments: set[str] = set()
    with pikepdf.open(BASE_PDF) as pdf:
        baseline_page_count = len(pdf.pages)
        if baseline_page_count < 1:
            raise RuntimeError("Current annotated manuscript has no pages")
        base_page_hashes = [page_content_digest(page) for page in pdf.pages]
        baseline_highlight_count = sum(
            1
            for page in pdf.pages
            for annot in page.obj.get("/Annots", [])
            if str(annot.get("/Subtype", "")) == "/Highlight"
        )
        baseline_link_count = sum(
            1
            for page in pdf.pages
            for annot in page.obj.get("/Annots", [])
            if str(annot.get("/Subtype", "")) == "/Link"
        )
        baseline_root_features = {
            "outlines": "/Outlines" in pdf.Root,
            "names": "/Names" in pdf.Root,
            "open_action": "/OpenAction" in pdf.Root,
        }

        for page_index, page in enumerate(pdf.pages):
            annots = page.obj.get("/Annots")
            if annots is None:
                continue
            retained_annots = Array()
            for annot in annots:
                if str(annot.get("/Subtype", "")) != "/Highlight":
                    retained_annots.append(annot)
                    continue
                old_contents = str(annot.get("/Contents", ""))
                if old_contents not in old_to_zh:
                    raise RuntimeError(
                        f"Unmapped highlight on page {page_index + 1}: "
                        f"subject={str(annot.get('/Subj', ''))!r}, contents={old_contents[:160]!r}"
                    )
                rid, local_note = old_to_zh[old_contents]
                seen_source_comments.add(old_contents)
                if rid in RESOLVED_REVIEW_IDS:
                    resolved_highlights_removed += 1
                    continue
                if rid.startswith("Re-"):
                    subject = f"{rid}｜第二轮复核"
                else:
                    subject = review_subject(rid, reviews_by_id[rid], zh_reviews[rid], severity_zh)
                annot["/T"] = String("中文同行审阅")
                annot["/Subj"] = String(subject)
                annot["/Contents"] = String(review_body(rid, local_note, reviews_by_id))
                updated_highlights += 1
                retained_annots.append(annot)
            page.obj["/Annots"] = retained_annots

        if updated_highlights + resolved_highlights_removed != baseline_highlight_count:
            raise RuntimeError(
                f"Expected {baseline_highlight_count} physical highlight objects, "
                f"updated/removed={updated_highlights}/{resolved_highlights_removed}"
            )
        if seen_source_comments != set(old_to_zh):
            missing = sorted(set(old_to_zh) - seen_source_comments)
            raise RuntimeError(f"Some source annotations were not present in the PDF: {missing}")

        # General reading note. This is a PDF object only and cannot reflow text.
        add_text_annotation(
            pdf,
            pdf.pages[0],
            subject="A00｜总评与阅读说明",
            contents=(
                overview
                + "建议先处理：阈值/击中存储、死时间与屏蔽计数率、Laue 物理验证、源流归一化、同口径比较、有限统计与似然、真实观测几何以及投稿可复现性。"
            ),
            color=(0.75, 0.75, 0.75),
            rect=(548, 800, 566, 818),
            icon="Comment",
        )

        for rid, (page_index, rect) in MISSING_NOTES.items():
            meta = reviews_by_id[rid]
            zh = zh_reviews[rid]
            body = review_body(
                rid,
                "原标注 PDF 没有对应的行内高亮；现补充为相关页面的侧栏便笺。",
                reviews_by_id,
            )
            add_text_annotation(
                pdf,
                pdf.pages[page_index],
                subject=f"{rid}｜{severity_zh[meta.severity]}｜{zh.category}｜补充正式条目",
                contents=body,
                color=tuple(float(value) for value in colors[meta.severity].split()),
                rect=rect,
            )

        pdf.save(tmp_output)

    os.replace(tmp_output, OUTPUT_PDF)

    # Re-open and verify the user-facing artifact.
    validation: dict[str, object] = {
        "baseline_pdf": BASE_PDF.name,
        "output_pdf": OUTPUT_PDF.name,
        "pages": None,
        "page_content_streams_identical": False,
        "highlight_objects_updated": 0,
        "resolved_highlight_objects_removed": resolved_highlights_removed,
        "added_chinese_text_notes": 0,
        "link_annotations_preserved": 0,
        "formal_review_ids_covered": 0,
        "all_review_annotation_authors_chinese": False,
        "all_review_annotation_contents_chinese": False,
        "status": "FAIL",
    }
    formal_ids_seen: set[str] = set()
    authors_ok = True
    contents_ok = True
    highlight_count = 0
    text_note_count = 0
    link_count = 0
    root_features_preserved = False
    resolved_ids_still_present: set[str] = set()
    with pikepdf.open(OUTPUT_PDF) as check:
        validation["pages"] = len(check.pages)
        output_page_hashes = [page_content_digest(page) for page in check.pages]
        output_root_features = {
            "outlines": "/Outlines" in check.Root,
            "names": "/Names" in check.Root,
            "open_action": "/OpenAction" in check.Root,
        }
        root_features_preserved = output_root_features == baseline_root_features
        for page in check.pages:
            for annot in page.obj.get("/Annots", []):
                subtype = str(annot.get("/Subtype", ""))
                if subtype == "/Link":
                    link_count += 1
                    continue
                if subtype not in {"/Highlight", "/Text"}:
                    continue
                subject = str(annot.get("/Subj", ""))
                contents = str(annot.get("/Contents", ""))
                author = str(annot.get("/T", ""))
                if subtype == "/Highlight":
                    highlight_count += 1
                else:
                    text_note_count += 1
                authors_ok &= author == "中文同行审阅"
                contents_ok &= any(token in contents for token in ("【正式问题】", "【第二轮复核】", "【阅读说明】"))
                rid = subject.split("｜", 1)[0]
                if rid in RESOLVED_REVIEW_IDS:
                    resolved_ids_still_present.add(rid)
                if rid in reviews_by_id:
                    formal_ids_seen.add(rid)

    expected_formal_ids = set(reviews_by_id) - RESOLVED_REVIEW_IDS
    validation.update(
        {
            "page_content_streams_identical": base_page_hashes == output_page_hashes,
            "highlight_objects_updated": highlight_count,
            "added_chinese_text_notes": text_note_count,
            "link_annotations_preserved": link_count,
            "catalog_navigation_features_preserved": root_features_preserved,
            "formal_review_ids_covered": len(formal_ids_seen),
            "formal_review_ids_missing": sorted(expected_formal_ids - formal_ids_seen),
            "resolved_review_ids_removed": sorted(RESOLVED_REVIEW_IDS),
            "resolved_review_ids_still_present": sorted(resolved_ids_still_present),
            "all_review_annotation_authors_chinese": authors_ok,
            "all_review_annotation_contents_chinese": contents_ok,
            "output_sha256": hashlib.sha256(OUTPUT_PDF.read_bytes()).hexdigest(),
        }
    )
    passed = all(
        [
            validation["pages"] == baseline_page_count,
            validation["page_content_streams_identical"],
            highlight_count == updated_highlights,
            text_note_count == 7,
            link_count == baseline_link_count,
            root_features_preserved,
            formal_ids_seen == expected_formal_ids,
            not resolved_ids_still_present,
            authors_ok,
            contents_ok,
        ]
    )
    validation["status"] = "PASS" if passed else "FAIL"
    VALIDATION_JSON.write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(validation, ensure_ascii=False, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
