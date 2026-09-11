#!/usr/bin/env python3
"""Build a detailed Phase 07-12 progress PPT and companion PPT memory file."""

from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
R2 = ROOT / "reports2.0"
OUT = R2 / "PPT_FULL_PROGRESS_REPORT"
TOP_MEMORY = R2 / "memoryforPPT.md"
LOCAL_MEMORY = OUT / "memoryforPPT.md"
MD_REPORT = OUT / "phase07_12_progress_report.md"
PPTX_OUT = OUT / "cosmosray_bg_2605_phase07_12_progress_report.pptx"
MANIFEST = OUT / "ppt_manifest.csv"

WIDE_W = Inches(13.333333)
WIDE_H = Inches(7.5)

FONT = "Microsoft YaHei"
TITLE = RGBColor(23, 43, 77)
ACCENT = RGBColor(0, 92, 175)
ACCENT_2 = RGBColor(28, 126, 93)
WARN = RGBColor(184, 92, 0)
RED = RGBColor(170, 46, 38)
TEXT = RGBColor(34, 41, 47)
MUTED = RGBColor(92, 101, 116)
LIGHT = RGBColor(246, 248, 251)
LINE = RGBColor(215, 221, 230)
WHITE = RGBColor(255, 255, 255)
DARK = RGBColor(15, 32, 54)


def read_json(rel: str, default=None):
    path = R2 / rel
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(rel: str) -> list[dict[str, str]]:
    path = R2 / rel
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def first_row(rel: str) -> dict[str, str]:
    rows = read_csv(rel)
    return rows[0] if rows else {}


def lookup_lineage(lineage: list[dict], quantity: str, default=""):
    for row in lineage:
        if row.get("quantity") == quantity:
            return row.get("value", default)
    return default


def as_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def fmt(value, ndigits: int = 6) -> str:
    if value is None:
        return ""
    x = as_float(value)
    if x is None:
        return str(value)
    ax = abs(x)
    if ax != 0 and (ax < 1e-3 or ax >= 1e5):
        return f"{x:.{ndigits}e}"
    return f"{x:.{ndigits}g}"


def pct(value, ndigits: int = 2) -> str:
    x = as_float(value, 0.0)
    return f"{x * 100:.{ndigits}f}%"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def make_context() -> dict:
    lineage = read_json("07_NIMA_MANUSCRIPT/final_numerical_lineage.json", [])
    phase10 = read_json("10_POINT_DIFFUSE_DISCRIMINATION/phase10_summary.json", {})
    phase11 = read_json("11_METRIC_RECONCILIATION_AND_OPTICS_GATE/phase11_summary.json", {})
    phase12 = read_json("12_FINAL_COMPACT_SOURCE_ANALYSIS/phase12_summary.json", {})
    source9 = read_json("09_SOURCE_CASES_ABC/source_case_summary.json", {})
    design_meta = read_json("08_DESIGN_OPTIMIZATION_ADDON/run_metadata.json", {})
    sel11 = read_json("11_METRIC_RECONCILIATION_AND_OPTICS_GATE/selection_best_upgrade_decision.json", {})
    sel12 = read_json("12_FINAL_COMPACT_SOURCE_ANALYSIS/selection_upgrade_decision_final.json", {})
    fp = read_json(
        "12_FINAL_COMPACT_SOURCE_ANALYSIS/first_principles_channeling_optics/"
        "first_principles_optics_coupling_summary.json",
        {},
    )
    l1_raw = read_json(
        "12_FINAL_COMPACT_SOURCE_ANALYSIS/first_principles_channeling_optics/"
        "first_principles_onaxis_summary_L1_surface.json",
        {},
    )
    l2_raw = read_json(
        "12_FINAL_COMPACT_SOURCE_ANALYSIS/first_principles_channeling_optics/"
        "first_principles_onaxis_summary_L2_parratt.json",
        {},
    )
    l1 = l1_raw.get("summary", l1_raw) if isinstance(l1_raw, dict) else {}
    l2 = l2_raw.get("summary", l2_raw) if isinstance(l2_raw, dict) else {}
    nds = read_json(
        "12_FINAL_COMPACT_SOURCE_ANALYSIS/no_direct_scaling_optics_alignment/"
        "validation_no_direct_scaling_alignment.json",
        {},
    )

    metric_rows = read_csv("12_FINAL_COMPACT_SOURCE_ANALYSIS/metric_closure_final.csv")
    metric_by_id = {r.get("metric_id", ""): r for r in metric_rows}
    audit_rows = read_csv("10_POINT_DIFFUSE_DISCRIMINATION/selection_best_measured_energy_audit.csv")
    audit_by_key = {
        (r.get("selection_id", ""), r.get("energy_basis", ""), r.get("window", "")): r
        for r in audit_rows
    }
    design_best = first_row(
        "08_DESIGN_OPTIMIZATION_ADDON/WP_D1_selection_pareto_highstat/"
        "top20_catalog_uniform_highstat.csv"
    )
    rec_table = read_csv(
        "08_DESIGN_OPTIMIZATION_ADDON/WP_D5_design_recommendation/design_recommendation_table.csv"
    )
    fov_rows = read_csv(
        "12_FINAL_COMPACT_SOURCE_ANALYSIS/no_direct_scaling_optics_alignment/"
        "tables/fov_footprint_summary.csv"
    )
    fov = {r.get("metric_id", ""): r.get("value", "") for r in fov_rows}
    aeff_total = {}
    for row in read_csv(
        "12_FINAL_COMPACT_SOURCE_ANALYSIS/no_direct_scaling_optics_alignment/"
        "tables/aeff_transport_debug.csv"
    ):
        if row.get("ring_id") == "TOTAL":
            aeff_total = row
            break

    return {
        "lineage": lineage,
        "phase10": phase10,
        "phase11": phase11,
        "phase12": phase12,
        "source9": source9,
        "design_meta": design_meta,
        "sel11": sel11,
        "sel12": sel12,
        "fp": fp,
        "l1": l1,
        "l2": l2,
        "nds": nds,
        "metric_rows": metric_rows,
        "metric": metric_by_id,
        "audit": audit_by_key,
        "design_best": design_best,
        "rec_table": rec_table,
        "fov": fov,
        "aeff_total": aeff_total,
    }


def image_path(relpath: str) -> Path:
    return R2 / relpath


IMAGES = {
    "day15_rates": image_path("04_FIGURES/day15/timeline_veto_rates_bar.png"),
    "day15_spectrum": image_path("04_FIGURES/day15/timeline_spectrum_480_550_veto_chain.png"),
    "nima_dashboard": image_path("04_FIGURES/nima_update/nima_small_stat_dashboard.png"),
    "focused_gamma": image_path("04_FIGURES/nima_update/optics_focused_gamma_background_addendum.png"),
    "design_q": image_path(
        "08_DESIGN_OPTIMIZATION_ADDON/WP_D1_selection_pareto_highstat/"
        "highstat_q_vs_background.png"
    ),
    "design_accept": image_path(
        "08_DESIGN_OPTIMIZATION_ADDON/WP_D1_selection_pareto_highstat/"
        "highstat_source_acceptance_vs_background.png"
    ),
    "source_a": image_path("09_SOURCE_CASES_ABC/figures/A_GC_POINT_detectability.png"),
    "source_b": image_path("09_SOURCE_CASES_ABC/figures/B_diffuse_expected_line_background.png"),
    "phase10_prob": image_path("10_POINT_DIFFUSE_DISCRIMINATION/figures/A_vs_B_detection_probability.png"),
    "phase10_selection": image_path(
        "10_POINT_DIFFUSE_DISCRIMINATION/figures/selection_best_true_vs_measured.png"
    ),
    "metric_f3": image_path("11_METRIC_RECONCILIATION_AND_OPTICS_GATE/figures/metric_F3_comparison.png"),
    "selection_gate": image_path(
        "11_METRIC_RECONCILIATION_AND_OPTICS_GATE/figures/selection_upgrade_decision_tree.png"
    ),
    "optics_schema": image_path("11_METRIC_RECONCILIATION_AND_OPTICS_GATE/figures/optics_schema_overview.png"),
    "metric_final": image_path("12_FINAL_COMPACT_SOURCE_ANALYSIS/final_figures/metric_closure_phase9_phase10_phase12.png"),
    "decision_matrix": image_path("12_FINAL_COMPACT_SOURCE_ANALYSIS/final_figures/selection_decision_matrix.png"),
    "optics_req": image_path("12_FINAL_COMPACT_SOURCE_ANALYSIS/final_figures/optics_bandpass_or_requirement.png"),
    "exposure_req": image_path("12_FINAL_COMPACT_SOURCE_ANALYSIS/final_figures/exposure_requirement_vs_flux.png"),
    "fp_l2_spot": image_path(
        "12_FINAL_COMPACT_SOURCE_ANALYSIS/first_principles_channeling_optics/"
        "figures/first_principles_L2_focal_spot.png"
    ),
    "fp_reflectivity": image_path(
        "12_FINAL_COMPACT_SOURCE_ANALYSIS/first_principles_channeling_optics/"
        "figures/reflectivity_wsi_parratt.png"
    ),
    "nds_fov": image_path(
        "12_FINAL_COMPACT_SOURCE_ANALYSIS/no_direct_scaling_optics_alignment/"
        "figures/onaxis_core_vs_full_fov_footprint.png"
    ),
    "nds_ring": image_path(
        "12_FINAL_COMPACT_SOURCE_ANALYSIS/no_direct_scaling_optics_alignment/"
        "figures/ringwise_centroid_map.png"
    ),
    "nds_aeff": image_path(
        "12_FINAL_COMPACT_SOURCE_ANALYSIS/no_direct_scaling_optics_alignment/"
        "figures/aeff_by_ring_and_bounce.png"
    ),
}


class Deck:
    def __init__(self) -> None:
        self.prs = Presentation()
        self.prs.slide_width = WIDE_W
        self.prs.slide_height = WIDE_H
        self.slide_no = 0
        self.artifacts: list[tuple[str, str]] = []

    def add_bg(self, slide, section: str = ""):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, WIDE_W, WIDE_H)
        bg.fill.solid()
        bg.fill.fore_color.rgb = WHITE
        bg.line.color.rgb = WHITE

        header = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, WIDE_W, Inches(0.18))
        header.fill.solid()
        header.fill.fore_color.rgb = ACCENT
        header.line.color.rgb = ACCENT

        footer = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(7.22), WIDE_W, Inches(0.28))
        footer.fill.solid()
        footer.fill.fore_color.rgb = LIGHT
        footer.line.color.rgb = LINE
        box = slide.shapes.add_textbox(Inches(0.38), Inches(7.24), Inches(12.6), Inches(0.18))
        tf = box.text_frame
        tf.clear()
        p = tf.paragraphs[0]
        p.text = f"COSMOSRAY_BG_2605 Phase07-12 progress report | {section}"
        p.font.name = FONT
        p.font.size = Pt(7.5)
        p.font.color.rgb = MUTED
        p.alignment = PP_ALIGN.RIGHT

    def title_box(self, slide, title: str, kicker: str | None = None):
        if kicker:
            k = slide.shapes.add_textbox(Inches(0.55), Inches(0.42), Inches(12.2), Inches(0.25))
            tf = k.text_frame
            tf.clear()
            p = tf.paragraphs[0]
            p.text = kicker
            p.font.name = FONT
            p.font.size = Pt(9)
            p.font.bold = True
            p.font.color.rgb = ACCENT
        t = slide.shapes.add_textbox(Inches(0.55), Inches(0.63), Inches(12.2), Inches(0.58))
        tf = t.text_frame
        tf.clear()
        p = tf.paragraphs[0]
        p.text = title
        p.font.name = FONT
        p.font.size = Pt(24)
        p.font.bold = True
        p.font.color.rgb = TITLE

    def add_text(
        self,
        slide,
        x,
        y,
        w,
        h,
        lines: list[str],
        font_size: float = 14,
        color: RGBColor = TEXT,
        bullet: bool = True,
        bold_first: bool = False,
        line_spacing: float = 1.05,
    ):
        shape = slide.shapes.add_textbox(x, y, w, h)
        tf = shape.text_frame
        tf.clear()
        tf.word_wrap = True
        for i, line in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = line
            p.font.name = FONT
            p.font.size = Pt(font_size)
            p.font.color.rgb = color
            p.font.bold = bool(bold_first and i == 0)
            p.level = 0
            p.space_after = Pt(3)
            p.line_spacing = line_spacing
            if bullet:
                p.text = f"• {line}"
        return shape

    def add_plain_text(self, slide, x, y, w, h, text: str, font_size: float = 12, color: RGBColor = TEXT):
        shape = slide.shapes.add_textbox(x, y, w, h)
        tf = shape.text_frame
        tf.clear()
        p = tf.paragraphs[0]
        p.text = text
        p.font.name = FONT
        p.font.size = Pt(font_size)
        p.font.color.rgb = color
        tf.word_wrap = True
        return shape

    def add_callout(self, slide, x, y, w, h, label: str, value: str, color: RGBColor = ACCENT):
        rect = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
        rect.fill.solid()
        rect.fill.fore_color.rgb = LIGHT
        rect.line.color.rgb = LINE
        label_box = slide.shapes.add_textbox(x + Inches(0.12), y + Inches(0.08), w - Inches(0.24), Inches(0.25))
        tf = label_box.text_frame
        tf.clear()
        p = tf.paragraphs[0]
        p.text = label
        p.font.name = FONT
        p.font.size = Pt(8.5)
        p.font.bold = True
        p.font.color.rgb = MUTED
        value_box = slide.shapes.add_textbox(x + Inches(0.12), y + Inches(0.34), w - Inches(0.24), h - Inches(0.36))
        tf = value_box.text_frame
        tf.clear()
        p = tf.paragraphs[0]
        p.text = value
        p.font.name = FONT
        p.font.size = Pt(15)
        p.font.bold = True
        p.font.color.rgb = color

    def add_picture_fit(self, slide, path: Path, x, y, w, h, caption: str | None = None):
        if not path.exists():
            self.add_plain_text(
                slide,
                x,
                y + h / 2 - Inches(0.2),
                w,
                Inches(0.4),
                f"缺少图像: {rel(path)}",
                font_size=10,
                color=RED,
            )
            return
        with Image.open(path) as img:
            iw, ih = img.size
        scale = min(w / iw, h / ih)
        new_w = int(iw * scale)
        new_h = int(ih * scale)
        pic_x = x + (w - new_w) / 2
        pic_y = y + (h - new_h) / 2
        slide.shapes.add_picture(str(path), pic_x, pic_y, width=new_w, height=new_h)
        self.artifacts.append((rel(path), "figure used in PPT"))
        if caption:
            self.add_plain_text(slide, x, y + h + Inches(0.03), w, Inches(0.22), caption, font_size=7.5, color=MUTED)

    def add_standard_slide(
        self,
        title: str,
        bullets: list[str],
        section: str,
        kicker: str | None = None,
        image: Path | None = None,
        image_caption: str | None = None,
        callouts: list[tuple[str, str, RGBColor]] | None = None,
    ):
        self.slide_no += 1
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self.add_bg(slide, section)
        self.title_box(slide, title, kicker)
        if image:
            self.add_text(slide, Inches(0.72), Inches(1.52), Inches(5.25), Inches(4.35), bullets, font_size=13.2)
            if callouts:
                cx = Inches(0.72)
                for label, value, color in callouts[:3]:
                    self.add_callout(slide, cx, Inches(6.05), Inches(1.65), Inches(0.74), label, value, color)
                    cx += Inches(1.78)
            self.add_picture_fit(slide, image, Inches(6.25), Inches(1.45), Inches(6.55), Inches(5.38), image_caption)
        else:
            self.add_text(slide, Inches(0.82), Inches(1.47), Inches(11.75), Inches(5.45), bullets, font_size=15)
            if callouts:
                n = len(callouts)
                box_w = Inches(11.2 / max(n, 1))
                cx = Inches(0.92)
                for label, value, color in callouts:
                    self.add_callout(slide, cx, Inches(5.92), box_w - Inches(0.13), Inches(0.86), label, value, color)
                    cx += box_w
        return slide

    def add_cover(self):
        self.slide_no += 1
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, WIDE_W, WIDE_H)
        bg.fill.solid()
        bg.fill.fore_color.rgb = DARK
        bg.line.color.rgb = DARK

        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(0.28), WIDE_H)
        bar.fill.solid()
        bar.fill.fore_color.rgb = ACCENT
        bar.line.color.rgb = ACCENT

        title = slide.shapes.add_textbox(Inches(0.86), Inches(1.25), Inches(11.6), Inches(1.1))
        tf = title.text_frame
        tf.clear()
        p = tf.paragraphs[0]
        p.text = "球载 511 keV TES 谱仪本底与紧致源分析"
        p.font.name = FONT
        p.font.size = Pt(32)
        p.font.bold = True
        p.font.color.rgb = WHITE

        sub = slide.shapes.add_textbox(Inches(0.88), Inches(2.38), Inches(11.6), Inches(0.8))
        tf = sub.text_frame
        tf.clear()
        p = tf.paragraphs[0]
        p.text = "COSMOSRAY_BG_2605 全流程推进报告 | Phase 07-12 收口版"
        p.font.name = FONT
        p.font.size = Pt(20)
        p.font.color.rgb = RGBColor(218, 230, 245)

        bullets = [
            "仿照原始 0416 基础报告的逻辑骨架：背景 -> 仪器/源项 -> 本底链 -> 分析链 -> 结论边界。",
            "新增重点：NIMA 论文稿、设计优化、A/B/C 源型、点/弥散判别、指标重对齐、Phase12 终局闭环、first-principles optics 与 no-direct-scaling 诊断。",
            "最终口径：Decision C / requirements-only；当前结果支持下一步需求定义，不支持最终天体物理发现声称。",
        ]
        self.add_text(slide, Inches(1.03), Inches(3.55), Inches(11.2), Inches(1.45), bullets, font_size=14, color=RGBColor(231, 238, 248))
        info = slide.shapes.add_textbox(Inches(0.92), Inches(6.55), Inches(11.8), Inches(0.3))
        tf = info.text_frame
        tf.clear()
        p = tf.paragraphs[0]
        p.text = f"Generated from reports2.0 on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        p.font.name = FONT
        p.font.size = Pt(9)
        p.font.color.rgb = RGBColor(180, 196, 218)

    def add_section(self, title: str, subtitle: str, section: str):
        self.slide_no += 1
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, WIDE_W, WIDE_H)
        bg.fill.solid()
        bg.fill.fore_color.rgb = RGBColor(242, 246, 251)
        bg.line.color.rgb = RGBColor(242, 246, 251)
        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, WIDE_W, Inches(0.24))
        bar.fill.solid()
        bar.fill.fore_color.rgb = ACCENT
        bar.line.color.rgb = ACCENT
        k = slide.shapes.add_textbox(Inches(0.82), Inches(1.9), Inches(11.7), Inches(0.32))
        tf = k.text_frame
        tf.clear()
        p = tf.paragraphs[0]
        p.text = section
        p.font.name = FONT
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = ACCENT
        t = slide.shapes.add_textbox(Inches(0.82), Inches(2.34), Inches(11.7), Inches(0.78))
        tf = t.text_frame
        tf.clear()
        p = tf.paragraphs[0]
        p.text = title
        p.font.name = FONT
        p.font.size = Pt(30)
        p.font.bold = True
        p.font.color.rgb = TITLE
        s = slide.shapes.add_textbox(Inches(0.84), Inches(3.3), Inches(10.8), Inches(0.8))
        tf = s.text_frame
        tf.clear()
        p = tf.paragraphs[0]
        p.text = subtitle
        p.font.name = FONT
        p.font.size = Pt(16)
        p.font.color.rgb = MUTED

    def add_timeline(self, ctx: dict):
        self.slide_no += 1
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self.add_bg(slide, "Phase map")
        self.title_box(slide, "Phase07-12 的逻辑链", "从论文谱系到终局 claim-control")
        phases = [
            ("07", "NIMA 谱系", "锁定本底、响应和灵敏度基线", "VALIDATED_REFERENCE"),
            ("08", "设计优化", "扫描 ROI/BGO/layer/single hit；只做 add-on", "DESIGN_ADDON"),
            ("09", "A/B/C 源型", "A 紧致点源、B 弥散前景、C V404 benchmark", "PLACEHOLDER_OPTICS"),
            ("10", "点/弥散 L1", "count-only scaffold + measured-energy audit", "CONSERVATIVE_DIAGNOSTIC"),
            ("11", "指标重对齐", "解释 Phase9/10 差异，建立 optics gate", "SCHEMA_ONLY"),
            ("12", "终局闭环", "Decision C，requirements-only", "PARAMETRIC_REQUIREMENT"),
        ]
        x0 = Inches(0.72)
        y0 = Inches(1.55)
        box_w = Inches(1.92)
        gap = Inches(0.16)
        for i, (pid, name, desc, status) in enumerate(phases):
            x = x0 + i * (box_w + gap)
            rect = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y0, box_w, Inches(3.9))
            rect.fill.solid()
            rect.fill.fore_color.rgb = WHITE
            rect.line.color.rgb = LINE
            num = slide.shapes.add_textbox(x + Inches(0.1), y0 + Inches(0.18), box_w - Inches(0.2), Inches(0.35))
            tf = num.text_frame
            tf.clear()
            p = tf.paragraphs[0]
            p.text = f"PHASE {pid}"
            p.font.name = FONT
            p.font.size = Pt(10)
            p.font.bold = True
            p.font.color.rgb = ACCENT
            nm = slide.shapes.add_textbox(x + Inches(0.1), y0 + Inches(0.62), box_w - Inches(0.2), Inches(0.45))
            tf = nm.text_frame
            tf.clear()
            p = tf.paragraphs[0]
            p.text = name
            p.font.name = FONT
            p.font.size = Pt(15)
            p.font.bold = True
            p.font.color.rgb = TITLE
            ds = slide.shapes.add_textbox(x + Inches(0.1), y0 + Inches(1.18), box_w - Inches(0.2), Inches(1.25))
            tf = ds.text_frame
            tf.clear()
            p = tf.paragraphs[0]
            p.text = desc
            p.font.name = FONT
            p.font.size = Pt(10.5)
            p.font.color.rgb = TEXT
            st = slide.shapes.add_textbox(x + Inches(0.1), y0 + Inches(2.95), box_w - Inches(0.2), Inches(0.58))
            tf = st.text_frame
            tf.clear()
            p = tf.paragraphs[0]
            p.text = status
            p.font.name = FONT
            p.font.size = Pt(8.5)
            p.font.bold = True
            p.font.color.rgb = ACCENT_2 if pid in {"07", "12"} else MUTED
        self.add_plain_text(
            slide,
            Inches(0.9),
            Inches(6.05),
            Inches(11.4),
            Inches(0.45),
            "这条链的关键不是“数值越来越好”，而是不断收紧 authority、metric 和 claim boundary：只有同一能量轴、同一模板维度、同一光学 authority 下的数字才允许互相比较。",
            font_size=12.5,
            color=TEXT,
        )

    def save(self):
        self.prs.save(PPTX_OUT)
        self.artifacts.append((rel(PPTX_OUT), "generated PowerPoint report"))


def add_all_slides(deck: Deck, ctx: dict):
    lin = ctx["lineage"]
    metric = ctx["metric"]
    audit = ctx["audit"]
    design = ctx["design_best"]
    source9 = ctx["source9"]
    auth9 = source9.get("authority", {})
    checks9 = source9.get("checks", {})
    phase10 = ctx["phase10"]
    phase11 = ctx["phase11"]
    phase12 = ctx["phase12"]
    fp = ctx["fp"]
    l1 = ctx["l1"]
    l2 = ctx["l2"]
    fov = ctx["fov"]
    aeff = ctx["aeff_total"]

    b_prompt = lookup_lineage(lin, "prompt final 480-550")
    b_delay = lookup_lineage(lin, "delayed final 480-550")
    b_focus = lookup_lineage(lin, "focused gamma broad addendum")
    b_total = lookup_lineage(lin, "background-only 480-550")
    response = lookup_lineage(lin, "corrected science response")
    f3_broad = lookup_lineage(lin, "broad profiled 3sigma / 1 Ms")
    f3_erl = lookup_lineage(lin, "broad ERL profiled 3sigma / 1 Ms")
    p3 = lookup_lineage(lin, "P>=3sigma at 1e-4, 1 Ms")

    deck.add_cover()

    deck.add_section(
        "先把原始 0416 报告的骨架保留下来",
        "新 PPT 不推翻旧报告，而是在同一条主线下把 source authority、detector response、metric 和 optics claim 重新收紧。",
        "Report lineage",
    )

    deck.add_standard_slide(
        "0416 基础报告的原始结构",
        [
            "原 PPT 的主线是：科学背景 -> TES 仪器 -> balloon 本底 -> mass model -> detector response -> prompt/delayed 源项 -> VETO/Compton -> day-15 结果。",
            "旧结论的定性判断仍然有用：延迟活化是 511 keV 附近主要本底；BGO 对 prompt 有效；Compton / coincidence 类 cut 对 delayed 也有贡献。",
            "旧 PPT 的 day-15 终态数值只是 legacy reference：raw 14.1 cps、BGO 11.1 cps、Compton 后 8.56 cps；本轮改用 Phase2/07-12 的 authority。",
            "本报告沿用 0416 的“从物理链到结果链”的讲述方式，但所有关键数值都从 `reports2.0` 重新取证。",
        ],
        "Report lineage",
    )

    deck.add_standard_slide(
        "2605 版本的核心变化",
        [
            "几何主干保持与 2602/XZTES 一致，报告重点转为 source、response、background ledger、metric 和 claim-control 的闭环。",
            "prompt 由 full-sphere 20-bin、down/up 分量和 real-flight profile 支撑；delayed 使用修正后的 day-15 activation source。",
            "science source authority 改为 Gate-A corrected Be-window HomogeneousBeam：z=127.66，半径 18.0 geometry units。",
            "当前 response authority 是 24.858994 cps/(ph cm^-2 s^-1)；旧 33.947... 已明确作废。",
            "所有 Phase07-12 的结果都必须带 claim level；不能把 placeholder optics 或 parametric requirement 写成 final production detectability。",
        ],
        "Report lineage",
        callouts=[
            ("science response", f"{fmt(response)} cps/flux", ACCENT),
            ("background 480-550", f"{fmt(b_total)} cps", ACCENT_2),
            ("final decision", str(phase12.get("final_decision_code", "C")), WARN),
        ],
    )

    deck.add_standard_slide(
        "本轮最关键的修正",
        [
            "Gate A 修正了 511 source placement，避免把 post-optics Be-window detector response source 与真实天体源/光学前源混为一谈。",
            "delay source 去除 W183/W180 ground-state 问题，重新冻结 activation source 的可用版本。",
            "BGO 仍然是 event-total proxy，不是完整 per-hit electronics model；PPT 和论文只能按 proxy/systematic 口径写。",
            "prompt lightcurve 当前存在 static fallback WARN；硬检查通过，但不能把它写成真实 telemetry 完全建模。",
            "focused gamma aperture background 被加进 ledger，但量级很小：broad addendum 约 1.02e-6 cps。",
        ],
        "Authority updates",
        image=IMAGES["focused_gamma"],
        image_caption="Focused gamma aperture addendum retained as a small background/systematic term.",
    )

    deck.add_timeline(ctx)

    deck.add_section(
        "Phase07：NIMA 论文稿与最终数值谱系",
        "Phase07 的任务是把当前可发表的本底、响应、灵敏度和限制口径写成可审阅的 NIMA-style 论文底稿。",
        "Phase07",
    )

    deck.add_standard_slide(
        "Phase07 的角色：把数字变成有 authority 的谱系",
        [
            "Phase07 不是重新跑大规模 MC，而是把 Phase2 的 production/result ledger、Gate A/B/C 修正和 NIMA 论文叙事固定下来。",
            "核心产物包括 `final_numerical_lineage.csv/json`、中英文 NIMA draft、详细中文 paper、图件和 claim-control 插入文本。",
            "谱系表要求每个数字都有 source_definition 和 used_for，防止同一页 PPT 上混用 diagnostic、background ledger、sensitivity proxy。",
            "这一层保留 reference-profile/proxy 限制：当前 1 Ms、1e-4 flux 不能写成稳健 3sigma 检出。",
        ],
        "Phase07",
        image=IMAGES["nima_dashboard"],
        image_caption="NIMA update dashboard: compact view of line/background/statistical state.",
    )

    deck.add_standard_slide(
        "Phase07 背景 ledger",
        [
            f"prompt final 480-550 keV = {fmt(b_prompt)} cps。",
            f"delayed final 480-550 keV = {fmt(b_delay)} cps，仍是主导分量。",
            f"focused gamma broad addendum = {fmt(b_focus)} cps；纳入 ledger，但远小于 prompt/delayed。",
            f"background-only 480-550 keV = {fmt(b_total)} cps。",
            f"reference science final at F=1e-4 = {fmt(lookup_lineage(lin, 'reference science final 480-550'))} cps；只作为 diagnostic stream，不是独立本底项。",
        ],
        "Phase07",
        image=IMAGES["day15_spectrum"],
        image_caption="480-550 keV veto-chain spectrum, reused as the baseline background ledger visual.",
        callouts=[
            ("prompt", f"{fmt(b_prompt)} cps", ACCENT),
            ("delayed", f"{fmt(b_delay)} cps", WARN),
            ("total B", f"{fmt(b_total)} cps", ACCENT_2),
        ],
    )

    deck.add_standard_slide(
        "Phase07 灵敏度口径",
        [
            f"corrected science response = {fmt(response)} cps/(ph cm^-2 s^-1)。",
            f"broad window profiled 3sigma / 1 Ms = {fmt(f3_broad)} ph cm^-2 s^-1，是保守 window-counting reference。",
            f"broad ERL profiled 3sigma / 1 Ms = {fmt(f3_erl)} ph cm^-2 s^-1，是更强的 template/proxy anchor。",
            f"line ERL profiled 3sigma / 1 Ms = {fmt(lookup_lineage(lin, 'line ERL profiled 3sigma / 1 Ms'))} ph cm^-2 s^-1。",
            f"F=1e-4、1 Ms 下 P(>=3sigma) 仅 {p3}；因此不能写成稳健 3sigma 检出。",
        ],
        "Phase07",
        image=IMAGES["day15_rates"],
        image_caption="Veto-chain rate decomposition used to anchor the sensitivity discussion.",
        callouts=[
            ("window F3", fmt(f3_broad), WARN),
            ("ERL F3", fmt(f3_erl), ACCENT),
            ("P3 @1e-4", str(p3), RED),
        ],
    )

    deck.add_standard_slide(
        "Phase07 给后续阶段留下的约束",
        [
            "所有后续 source-case 和 point/diffuse 分析必须继承同一个 detector-response authority，不能重新引入旧 response。",
            "真实天体源与 post-optics detector response source 必须分层：A/C 可以作为 point-source transport candidate，B 只能作为 FoV aperture foreground/null model。",
            "设计优化只能先作为 add-on；除非 measured-energy、template metric、source leakage、optics authority 同时过关，否则不能替换 baseline。",
            "光学相关结论必须标注 placeholder / schema / requirement / first-principles-input / production 之一区别。",
        ],
        "Phase07",
    )

    deck.add_section(
        "Phase08：设计优化 add-on",
        "这一阶段回答“哪些 cut/selection 可能有潜力”，但主动防止 selection-only best 直接替代主分析。",
        "Phase08",
    )

    deck.add_standard_slide(
        "Phase08 扫描的问题",
        [
            "扫描 BGO threshold、ROI radius、edge reject、single-pixel、layer mask、Compton policy 等组合。",
            "目标量使用 Q = response / sqrt(background)，与 Phase07 ERL F3 anchor 对应成 potential gain。",
            "high-stat 扫描触发后，catalog-uniform 最优配置为 `bgo30_r18_cent_single_top1_L5_keep`。",
            "Phase08 的设计原则：只给 immediate analysis setting / candidate，不能改变 detector response 或 background authority。",
        ],
        "Phase08",
        image=IMAGES["design_q"],
        image_caption="High-stat selection Pareto: Q improvement versus residual background.",
    )

    deck.add_standard_slide(
        "Phase08 主要数值",
        [
            f"baseline background = {fmt(ctx['design_meta'].get('baseline', {}).get('background_broad_final_cps'))} cps。",
            f"baseline science response = {fmt(ctx['design_meta'].get('baseline', {}).get('science_response_cps_per_flux'))} cps/flux。",
            f"selection-only best: B={fmt(design.get('background_broad_cps'))} cps，R={fmt(design.get('science_response_cps_per_flux'))} cps/flux。",
            f"selection-only best: Q/Q0={fmt(design.get('q_over_q0'))}，design-scaled F3={fmt(design.get('f3_best_scaled_1Ms_ph_cm2_s'))}。",
            "ROI with focal-core source bound 看起来更强，但依赖真实 focal spot retained by ROI，不能提前升级。",
        ],
        "Phase08",
        image=IMAGES["design_accept"],
        image_caption="Source acceptance versus background, showing why ROI/layer policies require later measured/template audits.",
        callouts=[
            ("best Q/Q0", fmt(design.get("q_over_q0")), ACCENT),
            ("best B", f"{fmt(design.get('background_broad_cps'))} cps", ACCENT_2),
            ("best F3", fmt(design.get("f3_best_scaled_1Ms_ph_cm2_s")), WARN),
        ],
    )

    deck.add_standard_slide(
        "Phase08 的限制",
        [
            "设计优化中的 source acceptance 来自 catalog-uniform 或 focal-core conditional bound，不等同于最终 measured-energy template performance。",
            "selection-only best 看起来从 Q/Q0 上有潜力，但它牺牲了一部分 response；是否真的更优需要 Phase10/12 的 measured/template 复核。",
            "BGO threshold 与 layer/ROI 组合依赖 event-catalog proxy；不能被写成硬件已经完成的电子学选择。",
            "这一阶段保留的正确结论是“值得进一步审计”，不是“最终飞行灵敏度已经提高”。",
        ],
        "Phase08",
    )

    deck.add_section(
        "Phase09：A/B/C 天体源构建层",
        "Phase09 把 science case 从单一 511 source 扩成 A 紧致源、B 弥散前景/null、C V404 benchmark，同时不改 detector chain。",
        "Phase09",
    )

    deck.add_standard_slide(
        "A/B/C 三类源的分工",
        [
            "A = `A_GC_CENTRAL_COMPACT_SPI_ANCHOR`：银河中心方向紧致点源主科学 case，association 只是 assumption，不声称 Sgr A* 已确认。",
            "B = diffuse bulge/disk aperture foreground/null：只做 FoV aperture integral，不生成 Cosima focal-spot source。",
            "C = V404 transient benchmark：作为 secondary transient / bandpass-risk benchmark，不能写成最终 V404 detectability。",
            "这一层不改 geometry、prompt/delayed background、detector response 或 event catalog。",
        ],
        "Phase09",
        image=IMAGES["source_a"],
        image_caption="A compact-source detectability folding under placeholder optics assumptions.",
    )

    deck.add_standard_slide(
        "Phase09 的数值闭环",
        [
            f"A source response closure relative error = {fmt(checks9.get('A_point_source_current_response_closure_relative_error'))}。",
            f"B default diffuse cps = {fmt(checks9.get('B_default_diffuse_cps'))}，约为 instrument background 的 {fmt(checks9.get('B_default_diffuse_to_instrument_background_fraction'))}。",
            f"Plane-rate cps/flux = {fmt(auth9.get('plane_rate_cps_per_flux'))}，transport selection efficiency = {fmt(auth9.get('transport_selection_efficiency'))}。",
            f"C at z=0.1 observed energy = {fmt(checks9.get('C_redshift_z0p10_observed_energy_keV'))} keV，状态为 {checks9.get('C_redshift_bandpass_status')}",
            f"placeholder optics = {checks9.get('placeholder_optics')}；full optics ray tracing done = {checks9.get('full_optics_ray_tracing_done')}。",
        ],
        "Phase09",
        image=IMAGES["source_b"],
        image_caption="B diffuse aperture foreground remains a null/foreground term, not a focal-spot Cosima source.",
    )

    deck.add_standard_slide(
        "Phase09 的逻辑贡献",
        [
            "它把“我们到底在测什么源”说清楚：主分析是 A compact-source detectability，不是把所有 GC 511 emission 都当点源。",
            "它把 B diffuse 放在 null/foreground 位置，从而为 Phase10 的 point/diffuse scaffold 提供对照。",
            "它把 C/V404 降级为 benchmark，防止一个红移/展宽/bandpass 风险 case 被误写成主结果。",
            "它还明确了当前光学仍是 placeholder table；真实 production optics 必须另行提供 Aeff(E,theta)、PSF、FoV、bandpass、focal-plane map。",
        ],
        "Phase09",
    )

    deck.add_section(
        "Phase10：紧致源 A 与弥散 B/null 的 L1 判别",
        "这一阶段建立 point/diffuse discrimination scaffold，并对 Phase08 selection-only best 做 measured-energy 审计。",
        "Phase10",
    )

    deck.add_standard_slide(
        "Phase10 L1 scaffold",
        [
            f"status = {phase10.get('status')}。",
            f"point/diffuse rows = {phase10.get('point_diffuse_rows')}；selection audit rows = {phase10.get('selection_audit_rows')}。",
            f"case id = {phase10.get('case_id')}；optics status = {phase10.get('optics_status')}。",
            f"claim status = {phase10.get('claim_status')}。",
            "这里故意采用 conservative count-based F3，避免把 Phase09/Phase08 的 ERL/profiled 设计数值当作 count-only 检出概率。",
        ],
        "Phase10",
        image=IMAGES["phase10_prob"],
        image_caption="A-vs-B detection probability with placeholder penalties and explicit claim boundary.",
    )

    p10_base = metric.get("phase10_baseline_count_only", {})
    p10_sel = audit.get(("bgo30_r18_cent_single_top1_L5_keep", "measured", "broad_480_550"), {})
    deck.add_standard_slide(
        "Phase10 的 measured-energy audit",
        [
            f"baseline count-only F3 = {fmt(p10_base.get('F3_1Ms'))}，P3@1e-4 = {fmt(p10_base.get('P_ge_3sigma_at_1e-4_1Ms'))}。",
            f"selection-only best measured broad F3 = {fmt(p10_sel.get('F3_ph_cm2_s'))}。",
            f"selection-only best measured P3@1e-4 = {fmt(p10_sel.get('P_ge_3sigma_at_1e_minus_4'))}。",
            f"true/measured response rel diff = {fmt(p10_sel.get('true_measured_response_rel_diff'))}；background rel diff = {fmt(p10_sel.get('true_measured_background_rel_diff'))}。",
            "结论：measured-energy audit 通过，但没有证明 Phase08 design-Q sensitivity 可以升级为主结果。",
        ],
        "Phase10",
        image=IMAGES["phase10_selection"],
        image_caption="Selection best true-vs-measured audit; pass status does not equal main-analysis upgrade.",
        callouts=[
            ("baseline count F3", fmt(p10_base.get("F3_1Ms")), WARN),
            ("selection F3", fmt(p10_sel.get("F3_ph_cm2_s")), ACCENT),
            ("selection P3", fmt(p10_sel.get("P_ge_3sigma_at_1e_minus_4")), RED),
        ],
    )

    deck.add_standard_slide(
        "Phase10 避免的两个误用",
        [
            "误用一：把 Phase09/Phase08 的 ERL/profiled F3 与 Phase10 count-only F3 直接比较。修正：Phase11 做 metric crosswalk。",
            "误用二：把 B diffuse 生成为 focal-spot source。修正：B 只作为 aperture foreground/null model，保持 source physics 分层。",
            "Phase10 保留的正确用法是：给 A compact-source vs B diffuse-null 判别一个 L1 scaffold，并给 selection-only best 一个 measured-energy audit。",
            "它不是最终 imaging/point-diffuse separation，也不是 production optics detectability。",
        ],
        "Phase10",
    )

    deck.add_section(
        "Phase11：指标重对齐与 production optics gate",
        "Phase11 是本轮逻辑最重要的一步：解释 Phase9/10 数字差异，并阻止 selection-only best 静默替换 baseline。",
        "Phase11",
    )

    deck.add_standard_slide(
        "Phase11 metric crosswalk",
        [
            f"status = {phase11.get('status')}；metric rows = {phase11.get('metric_rows')}。",
            "crosswalk 明确每个指标的 energy_axis、statistic_type、template_dimension、claim_level。",
            "Phase7/9 的 ERL/template/profiled 数字不能与 Phase10 count-only scalar 直接排名。",
            "common factor consistency = true，说明 Phase9/10 差异主要来自 metric-definition change，而不是 selection-specific physics failure。",
        ],
        "Phase11",
        image=IMAGES["metric_f3"],
        image_caption="Metric F3 comparison; the main disagreement is the metric definition.",
    )

    deck.add_standard_slide(
        "Phase11 对 selection-only best 的升级判据",
        [
            f"audit executed = {ctx['sel11'].get('audit_executed')}。",
            f"performance reproduced = {ctx['sel11'].get('performance_reproduced')}。",
            f"upgraded to main analysis = {ctx['sel11'].get('upgraded_to_main_analysis')}。",
            f"measured broad F3 = {fmt(ctx['sel11'].get('measured_broad_F3'))}；Phase9 design-Q F3 = {fmt(ctx['sel11'].get('phase9_selection_design_Q_F3'))}。",
            "primary reason：measured broad count-only audit 已执行，但未在同一 measured/template metric 下复现 design-Q sensitivity；BGO 仍是 event-total proxy。",
        ],
        "Phase11",
        image=IMAGES["selection_gate"],
        image_caption="Three-state selection gate: audited is not the same as upgraded.",
    )

    deck.add_standard_slide(
        "Phase11 production optics gate",
        [
            f"optics status = {phase11.get('optics_status')}；requirements rows = {phase11.get('requirements_rows')}。",
            "schema gate 要求真实 Aeff(E,theta)、PSF、FoV、bandpass、focal-plane response map 和 pointing/visibility。",
            "point/diffuse template TS scaffold 的 claim level 仍是 PLACEHOLDER_OPTICS_ONLY。",
            "这个 gate 的意义是：只要 optics authority 不是 production，任何 A/B template detectability 都只能写成 requirement 或 scaffold。",
        ],
        "Phase11",
        image=IMAGES["optics_schema"],
        image_caption="Production optics schema; schema exists, but production optics does not.",
    )

    deck.add_standard_slide(
        "Phase11 形成的写作规则",
        [
            "可以写：selection-only best has a measured-energy audit。",
            "可以写：selection-only best remains analysis-only pending measured/template reproduction。",
            "可以写：baseline remains the primary validated reference。",
            "禁止写：selection best replaces baseline。",
            "禁止写：Phase10 measured audit proves the design-Q gain 或 selection-only best is final flight sensitivity。",
        ],
        "Phase11",
    )

    deck.add_section(
        "Phase12：终局 compact-source closure",
        "Phase12 把 Phase9/10/11 的指标、selection、source-case 和 optics 状态全部收口，给出最终 Decision C。",
        "Phase12",
    )

    deck.add_standard_slide(
        "Phase12 最终决策",
        [
            f"status = {phase12.get('status')}。",
            f"final decision code = {phase12.get('final_decision_code')}；final claim level = {phase12.get('final_claim_level')}。",
            f"primary metric = {phase12.get('primary_metric_id')}。",
            f"selection upgraded to main analysis = {phase12.get('selection_upgraded_to_main_analysis')}。",
            f"optics status = {phase12.get('optics_status')}。",
            "最终包不再新开 source phase；剩余限制转为 optics/electronics/metric requirements。",
        ],
        "Phase12",
        image=IMAGES["decision_matrix"],
        image_caption="Final decision matrix: Decision C, requirements-only.",
        callouts=[
            ("decision", str(phase12.get("final_decision_code")), WARN),
            ("primary", "measured ERL", ACCENT),
            ("selection upgrade", str(phase12.get("selection_upgraded_to_main_analysis")), RED),
        ],
    )

    p12_base = metric.get("phase12_baseline_measured_ERL", {})
    p12_sel = metric.get("phase12_selection_best_measured_ERL", {})
    p09_base = metric.get("phase9_baseline_ERL", {})
    p10_base = metric.get("phase10_baseline_count_only", {})
    deck.add_standard_slide(
        "Phase12 metric closure",
        [
            f"Phase9 baseline ERL F3 = {fmt(p09_base.get('F3_1Ms'))}。",
            f"Phase10 baseline count-only F3 = {fmt(p10_base.get('F3_1Ms'))}，ratio_to_phase9_ERL={fmt(p10_base.get('ratio_to_phase9_ERL'))}。",
            f"Phase12 baseline measured ERL F3 = {fmt(p12_base.get('F3_1Ms'))}，P3@1e-4={fmt(p12_base.get('P_ge_3sigma_at_1e-4_1Ms'))}。",
            f"Phase12 baseline measured ERL ratio_to_phase9_ERL={fmt(p12_base.get('ratio_to_phase9_ERL'))}；20% closure gate 未通过。",
            "因此它接近 1e-4 只是 measured-template analysis result，不能作为最终 production compact-source claim。",
        ],
        "Phase12",
        image=IMAGES["metric_final"],
        image_caption="Phase9/10/12 metric closure and the final measured ERL result.",
        callouts=[
            ("primary F3", fmt(p12_base.get("F3_1Ms")), ACCENT),
            ("P3 @1e-4", fmt(p12_base.get("P_ge_3sigma_at_1e-4_1Ms")), WARN),
            ("ratio vs P9", fmt(p12_base.get("ratio_to_phase9_ERL")), RED),
        ],
    )

    deck.add_standard_slide(
        "Phase12 selection 最终没有升级",
        [
            f"selection id = {ctx['sel12'].get('selection_id')}。",
            f"selection measured ERL F3 = {fmt(p12_sel.get('F3_1Ms'))}；baseline measured ERL F3 = {fmt(p12_base.get('F3_1Ms'))}。",
            f"selection P3@1e-4 = {fmt(p12_sel.get('P_ge_3sigma_at_1e-4_1Ms'))}；baseline P3@1e-4 = {fmt(p12_base.get('P_ge_3sigma_at_1e-4_1Ms'))}。",
            f"performance reproduced under final metric = {ctx['sel12'].get('performance_reproduced_under_final_metric')}。",
            "Phase12 的主结果仍是 baseline；selection-only best 只保留为 analysis-only design comparison。",
        ],
        "Phase12",
        image=IMAGES["exposure_req"],
        image_caption="Exposure requirement view: useful as requirement framing, not as final discovery claim.",
    )

    deck.add_standard_slide(
        "Phase12 A/B 与 optics requirements 的边界",
        [
            f"AB likelihood rows = {phase12.get('AB_likelihood_rows')}；injection recovery rows = {phase12.get('injection_recovery_rows')}。",
            "A/B template likelihood 只支持参数化 optics requirement，不支持 production optics detectability。",
            "optics requirements table 的作用是列出 response gain、background reduction、exposure、bandpass/PSF/FoV 信息需求。",
            "最终禁止口径：unqualified astrophysical discovery、confirmed source identity、final production optics detectability、final V404 detectability。",
        ],
        "Phase12",
        image=IMAGES["optics_req"],
        image_caption="Optics bandpass / OR requirements figure used to frame future work.",
    )

    deck.add_section(
        "Phase12 之后的光学推进：first-principles 与 no-direct-scaling",
        "这部分不是新 Phase13，而是把 optics 从 placeholder 往可审阅 requirement input 推进一步，并记录仍未满足的 production 条件。",
        "Optics addendum",
    )

    deck.add_standard_slide(
        "first-principles channeling optics 的新增内容",
        [
            "新增 L1 W 单面 Fresnel 与 L2 W/Si Parratt multilayer table；不使用 CAM511 calibration/effective lookup。",
            f"L1 on-axis Aeff = {fmt(l1.get('estimated_effective_area_cm2'))} cm2，HPD = {fmt(l1.get('weighted_hpd_diameter_mm'))} mm。",
            f"L2 Parratt on-axis Aeff = {fmt(l2.get('estimated_effective_area_cm2', fp.get('firstprinciples_aeff_cm2')))} cm2，HPD = {fmt(l2.get('weighted_hpd_diameter_mm', fp.get('weighted_hpd_diameter_mm')))} mm。",
            f"Phase12 coupling status = {fp.get('status')}；claim level = {fp.get('claim_level')}。",
            "耦合方式是 scalar Aeff rescale of existing Phase12 measured detector/background templates；没有新的 Cosima detector transport。",
        ],
        "Optics addendum",
        image=IMAGES["fp_l2_spot"],
        image_caption="First-principles L2 on-axis focal spot; requirement input only.",
        callouts=[
            ("L2 Aeff", f"{fmt(fp.get('firstprinciples_aeff_cm2'))} cm2", ACCENT),
            ("scale vs 50.89", fmt(fp.get("response_scale_vs_current_cam511_normalization")), WARN),
            ("claim", "REQ input", RED),
        ],
    )

    deck.add_standard_slide(
        "first-principles optics 的物理解释",
        [
            "Parratt W/Si reflectivity table 作为 511 keV multilayer 反射权重输入，替代经验 effective lookup。",
            "L2 Aeff 明显低于当前 50.89 cm2 CAM511 normalization，说明不能把它直接拿来增强探测结论。",
            "当前最稳妥口径：它是 first-principles optics requirement input，用来暴露 Aeff/spot/FoV 需求，而不是 production optics response。",
            "重复性能瓶颈已通过预计算 511 keV reflectivity vector 与几何 alpha-grid 插值解决，没有降低统计量来凑结果。",
        ],
        "Optics addendum",
        image=IMAGES["fp_reflectivity"],
        image_caption="W/Si Parratt reflectivity table used by the first-principles optics layer.",
    )

    deck.add_standard_slide(
        "focal spot 差异的当前理解",
        [
            "L2 on-axis intrinsic D95 约 10.9 mm；这更像 intrinsic specular core。",
            "CAM511 few-cm focused-beam scale 不能直接当作 on-axis r95 去比较，除非外部审阅确认它就是同一定义。",
            "当把 full-FoV 几何 footprint 纳入后，4.47 arcmin FoV 在 12 m 焦平面半径约 15.6 mm。",
            "expected full-FoV envelope D95 约 42.1 mm，现有矩阵 FoV-edge D95 median 约 39.9 mm；这解释了为什么看上去接近 CAM511 few-cm scale。",
            "因此当前策略是先对齐 metric definition，而不是用乘系数把 spot 贴到 CAM511。",
        ],
        "Optics addendum",
        image=IMAGES["nds_fov"],
        image_caption="No-direct-scaling diagnostic: intrinsic on-axis core versus full-FoV footprint.",
        callouts=[
            ("on-axis D95", f"{fmt(fov.get('intrinsic_onaxis_core_D95_mm'))} mm", ACCENT),
            ("FoV radius", f"{fmt(fov.get('fov_radius_focal_plane_mm'))} mm", WARN),
            ("envelope D95", f"{fmt(fov.get('expected_geometric_full_fov_envelope_D95_mm'))} mm", ACCENT_2),
        ],
    )

    deck.add_standard_slide(
        "no-direct-scaling alignment 的硬检查",
        [
            "required outputs present: PASS。",
            "cam511 spot not misused as on-axis r95: PASS。",
            "intrinsic and FoV metrics separated: PASS。",
            "full-FoV footprint larger than intrinsic core: PASS。",
            "no direct scaling tokens found: PASS。",
            "这支持当前口径：不要与 CAM511 数字硬拟合；先把 spot metric、Aeff transport 和 FoV footprint 定义对齐。",
        ],
        "Optics addendum",
        image=IMAGES["nds_ring"],
        image_caption="Ring-wise centroid map used as a geometry sanity check.",
    )

    deck.add_standard_slide(
        "Aeff transport debug",
        [
            f"open geometric area = {fmt(aeff.get('open_geometric_area_cm2'))} cm2。",
            f"L2 Aeff = {fmt(aeff.get('Aeff_cm2'))} cm2。",
            f"Aeff / open geometric = {fmt(aeff.get('Aeff_over_open_geometric'))}。",
            f"mean total reflectivity product = {fmt(aeff.get('mean_total_reflectivity_product'))}，median product 极低，说明加权由少数高反射路径主导。",
            f"mean bounce count = {fmt(aeff.get('mean_bounce_count'))}；p95 bounce count = {fmt(aeff.get('p95_bounce_count'))}。",
            "这不是 tuning；表中 used_for_tuning=false。",
        ],
        "Optics addendum",
        image=IMAGES["nds_aeff"],
        image_caption="Aeff by ring and bounce diagnostics, without direct scaling.",
    )

    deck.add_section(
        "最终综合：现在能说什么，不能说什么",
        "这组 slide 是给论文/PPT 结论页直接使用的 claim-control 摘要。",
        "Synthesis",
    )

    deck.add_standard_slide(
        "Phase07-12 的综合结果",
        [
            f"当前 480-550 keV background-only ledger = {fmt(b_total)} cps，其中 delayed={fmt(b_delay)} cps 是主导。",
            f"当前 detector/source response authority = {fmt(response)} cps/(ph cm^-2 s^-1)。",
            f"Phase12 primary metric baseline measured ERL F3 = {fmt(p12_base.get('F3_1Ms'))} ph cm^-2 s^-1，P3@1e-4={fmt(p12_base.get('P_ge_3sigma_at_1e-4_1Ms'))}。",
            "这个结果接近 1e-4，但没有通过 Phase9 closure、selection upgrade、production optics 三重条件。",
            "最终结论是 requirements-only：下一步应补 production optics/electronics/pointing 信息，而不是提前写最终探测声明。",
        ],
        "Synthesis",
        image=IMAGES["metric_final"],
    )

    deck.add_standard_slide(
        "现在可以安全写进报告/论文的内容",
        [
            "当前模拟链给出了一个可审计的 balloon 511 keV TES background ledger 和 measured-template sensitivity proxy。",
            "1 Ms、F=1e-4 的紧致源检出在 measured ERL proxy 下变得“接近有意义”，但仍不是稳健 final claim。",
            "selection-only best 有 measured-energy audit，能作为 design comparison 保留；baseline 仍是主分析 reference。",
            "first-principles channeling optics 已作为 requirement input 接入 Phase12，但不是 production optics authority。",
            "CAM511 few-cm focal scale 应优先与 full-FoV / engineering footprint metric 对齐，不应直接压到 on-axis intrinsic core。",
        ],
        "Synthesis",
    )

    deck.add_standard_slide(
        "必须避免的错误表述",
        [
            "不能说已经实现最终银河中心紧致源 3sigma 探测。",
            "不能说 A source identity 已确认，尤其不能把 A 直接写成 confirmed Sgr A* source。",
            "不能说 selection-only best 已替代 baseline 或证明 Phase08 design-Q gain。",
            "不能说当前 optics 是 production ray-traced optics response。",
            "不能说 CAM511 spot discrepancy 已通过标定/缩放解决；当前只是 metric-alignment 解释和 first-principles requirement input。",
        ],
        "Synthesis",
    )

    deck.add_standard_slide(
        "建议下一步",
        [
            "向 GPT Pro / 光学审阅确认 CAM511 few-cm focal spot 的严格定义：on-axis containment、full-FoV footprint、还是工程 focused-beam diameter。",
            "扩展 first-principles response matrix：能量、theta/phi、PSF tails、bandpass、off-axis throughput 和 focal-plane map。",
            "把 BGO/event-total proxy 推进到 per-hit/electronics model，尤其是阈值、死时间、coincidence/accidental 影响。",
            "对 prompt real-flight lightcurve 的 static WARN 做真实 profile 替代或明确 systematic freeze。",
            "保持 Phase12 Decision C 作为当前封口；下一步应是 production optics/electronics requirement fulfillment，而不是新建未定义 Phase13。",
        ],
        "Synthesis",
        image=IMAGES["optics_req"],
    )


def build_memory(ctx: dict) -> str:
    lin = ctx["lineage"]
    metric = ctx["metric"]
    p12 = ctx["phase12"]
    p10 = ctx["phase10"]
    p11 = ctx["phase11"]
    fp = ctx["fp"]
    fov = ctx["fov"]
    aeff = ctx["aeff_total"]
    p12_base = metric.get("phase12_baseline_measured_ERL", {})
    p12_sel = metric.get("phase12_selection_best_measured_ERL", {})
    lines = [
        "# memoryforPPT",
        "",
        "本文件是 `reports2.0` 下 PPT 版本的可更新上下文。后续若继续改 PPT，应先更新这里，再运行 `python3 tools/build_phase07_12_progress_ppt.py`。",
        "",
        "## 本 PPT 的定位",
        "",
        "- 模仿 `cosmosray_0416.zip/cosmosray_0416.pptx` 的基础报告逻辑：背景、仪器/源项、本底链、模拟链、结果、结论。",
        "- 新报告覆盖 `reports2.0` 的 Phase07-12，以及 Phase12 后新增的 first-principles channeling optics 与 no-direct-scaling optics alignment。",
        "- 最终口径必须保持：Decision C / requirements-only；不得把当前结果写成最终天体物理发现或 production optics detectability。",
        "",
        "## 当前核心 authority",
        "",
        f"- corrected science response: `{fmt(lookup_lineage(lin, 'corrected science response'))} cps/(ph cm^-2 s^-1)`.",
        f"- prompt final 480-550: `{fmt(lookup_lineage(lin, 'prompt final 480-550'))} cps`.",
        f"- delayed final 480-550: `{fmt(lookup_lineage(lin, 'delayed final 480-550'))} cps`.",
        f"- focused gamma broad addendum: `{fmt(lookup_lineage(lin, 'focused gamma broad addendum'))} cps`.",
        f"- background-only 480-550: `{fmt(lookup_lineage(lin, 'background-only 480-550'))} cps`.",
        f"- Phase07 broad ERL profiled F3 / 1 Ms: `{fmt(lookup_lineage(lin, 'broad ERL profiled 3sigma / 1 Ms'))}`.",
        f"- Phase07 P>=3sigma at F=1e-4, 1 Ms: `{lookup_lineage(lin, 'P>=3sigma at 1e-4, 1 Ms')}`.",
        "",
        "## Phase07-12 逻辑摘要",
        "",
        "- Phase07: NIMA-style manuscript and final numerical lineage. 作用是固定本底、响应、灵敏度和 claim-control。",
        "- Phase08: design optimization add-on. selection-only best 有潜力，但只能作为 design comparison。",
        "- Phase09: A/B/C source-case layer. A=GC compact source, B=diffuse aperture/null, C=V404 benchmark。",
        f"- Phase10: `{p10.get('status')}`; optics status `{p10.get('optics_status')}`; claim `{p10.get('claim_status')}`。",
        f"- Phase11: `{p11.get('status')}`; selection upgraded `{p11.get('selection_upgraded_to_main_analysis')}`; optics `{p11.get('optics_status')}`。",
        f"- Phase12: `{p12.get('status')}`; decision `{p12.get('final_decision_code')}`; claim `{p12.get('final_claim_level')}`。",
        "",
        "## Phase12 最终数字",
        "",
        f"- primary metric: `{p12.get('primary_metric_id')}`.",
        f"- baseline measured ERL F3: `{fmt(p12_base.get('F3_1Ms'))}`.",
        f"- baseline measured ERL P3@1e-4: `{fmt(p12_base.get('P_ge_3sigma_at_1e-4_1Ms'))}`.",
        f"- baseline measured ERL ratio to Phase9 ERL: `{fmt(p12_base.get('ratio_to_phase9_ERL'))}`.",
        f"- selection measured ERL F3: `{fmt(p12_sel.get('F3_1Ms'))}`.",
        f"- selection measured ERL P3@1e-4: `{fmt(p12_sel.get('P_ge_3sigma_at_1e-4_1Ms'))}`.",
        "- selection-only best 未升级，主结果保持 baseline。",
        "",
        "## 光学新增结论",
        "",
        f"- first-principles optics status: `{fp.get('status')}`.",
        f"- optics id: `{fp.get('optics_id')}`.",
        f"- first-principles L2 Aeff: `{fmt(fp.get('firstprinciples_aeff_cm2'))} cm2`.",
        f"- response scale vs 50.89 normalization: `{fmt(fp.get('response_scale_vs_current_cam511_normalization'))}`.",
        f"- weighted HPD diameter: `{fmt(fp.get('weighted_hpd_diameter_mm'))} mm`.",
        "- claim level: `FIRST_PRINCIPLES_OPTICS_REQUIREMENT_INPUT`; production optics response is false。",
        f"- no-direct-scaling intrinsic on-axis D95: `{fmt(fov.get('intrinsic_onaxis_core_D95_mm'))} mm`.",
        f"- FoV radius at 4.47 arcmin / 12 m: `{fmt(fov.get('fov_radius_focal_plane_mm'))} mm`.",
        f"- expected full-FoV envelope D95: `{fmt(fov.get('expected_geometric_full_fov_envelope_D95_mm'))} mm`.",
        f"- matrix FoV-edge D95 median: `{fmt(fov.get('matrix_fov_edge_D95_median_mm'))} mm`.",
        f"- Aeff/open geometric: `{fmt(aeff.get('Aeff_over_open_geometric'))}`; used_for_tuning=false。",
        "",
        "## PPT 输出",
        "",
        f"- PowerPoint: `{rel(PPTX_OUT)}`",
        f"- Markdown report: `{rel(MD_REPORT)}`",
        f"- Manifest: `{rel(MANIFEST)}`",
        "",
        "## 禁止口径",
        "",
        "- 不得声称最终银河中心紧致源探测。",
        "- 不得声称 source identity 已确认。",
        "- 不得声称 selection-only best 替代 baseline。",
        "- 不得声称当前 optics 是 production optics authority。",
        "- 不得用直接乘系数把 first-principles spot 或 Aeff 调到 CAM511；必须先对齐 metric definition。",
        "",
        "## 更新规则",
        "",
        "- 如果后续有新数值，优先更新对应 CSV/JSON authority，再重跑 PPT 生成脚本。",
        "- 如果同一错误重复出现两次，停止试错；查找 3-5 种修复方案，选择最高效且最符合物理 authority 的方案实施。",
        "- PPT 中所有数字都应能追溯到 `reports2.0` 下的文件。",
        "",
    ]
    return "\n".join(lines)


def build_markdown_report(ctx: dict) -> str:
    lin = ctx["lineage"]
    metric = ctx["metric"]
    p12_base = metric.get("phase12_baseline_measured_ERL", {})
    p12_sel = metric.get("phase12_selection_best_measured_ERL", {})
    rows = [
        "# COSMOSRAY_BG_2605 Phase07-12 PPT Report Source",
        "",
        "本 Markdown 是 PPT 的文字版来源，便于后续审阅和更新。",
        "",
        "## 总结",
        "",
        "- 本轮推进从 NIMA 论文稿和最终数值谱系开始，逐步加入设计优化、A/B/C 源型、点/弥散判别、指标重对齐和 Phase12 终局闭环。",
        "- 当前最终结论是 Decision C / requirements-only。主指标 baseline measured ERL 已接近 `1e-4 ph cm^-2 s^-1`，但没有通过 Phase9 closure、selection upgrade、production optics 三重条件。",
        "- first-principles optics 与 no-direct-scaling alignment 已经显著改善光学讨论的物理性，但仍只能作为 requirements input。",
        "",
        "## Key Numbers",
        "",
        "| quantity | value |",
        "| --- | ---: |",
        f"| response | {fmt(lookup_lineage(lin, 'corrected science response'))} cps/flux |",
        f"| prompt 480-550 | {fmt(lookup_lineage(lin, 'prompt final 480-550'))} cps |",
        f"| delayed 480-550 | {fmt(lookup_lineage(lin, 'delayed final 480-550'))} cps |",
        f"| total background 480-550 | {fmt(lookup_lineage(lin, 'background-only 480-550'))} cps |",
        f"| Phase07 broad ERL F3 | {fmt(lookup_lineage(lin, 'broad ERL profiled 3sigma / 1 Ms'))} |",
        f"| Phase12 baseline measured ERL F3 | {fmt(p12_base.get('F3_1Ms'))} |",
        f"| Phase12 baseline measured ERL P3@1e-4 | {fmt(p12_base.get('P_ge_3sigma_at_1e-4_1Ms'))} |",
        f"| Phase12 selection measured ERL F3 | {fmt(p12_sel.get('F3_1Ms'))} |",
        "",
        "## Slide Deck Logic",
        "",
        "1. 原始 0416 报告结构和本轮 authority 更新。",
        "2. Phase07 NIMA 数值谱系和 sensitivity boundary。",
        "3. Phase08 design optimization add-on 与不能升级的原因。",
        "4. Phase09 A/B/C source-case layer。",
        "5. Phase10 point/diffuse L1 scaffold 和 measured-energy audit。",
        "6. Phase11 metric crosswalk、selection upgrade gate 和 production optics schema。",
        "7. Phase12 final closure：Decision C / requirements-only。",
        "8. first-principles channeling optics 和 no-direct-scaling optics alignment。",
        "9. 最终可以写/不能写的 claim-control。",
        "",
        "## Source Artifacts",
        "",
        "- `reports2.0/07_NIMA_MANUSCRIPT/final_numerical_lineage.json`",
        "- `reports2.0/08_DESIGN_OPTIMIZATION_ADDON/`",
        "- `reports2.0/09_SOURCE_CASES_ABC/`",
        "- `reports2.0/10_POINT_DIFFUSE_DISCRIMINATION/`",
        "- `reports2.0/11_METRIC_RECONCILIATION_AND_OPTICS_GATE/`",
        "- `reports2.0/12_FINAL_COMPACT_SOURCE_ANALYSIS/`",
        "",
    ]
    return "\n".join(rows)


def write_manifest(deck: Deck):
    rows = []
    for path, role in sorted(set(deck.artifacts)):
        p = ROOT / path if not Path(path).is_absolute() else Path(path)
        rows.append(
            {
                "relative_path": path,
                "exists": p.exists(),
                "bytes": p.stat().st_size if p.exists() else "",
                "role": role,
            }
        )
    rows.extend(
        [
            {
                "relative_path": rel(TOP_MEMORY),
                "exists": TOP_MEMORY.exists(),
                "bytes": TOP_MEMORY.stat().st_size if TOP_MEMORY.exists() else "",
                "role": "top-level PPT memory context",
            },
            {
                "relative_path": rel(MD_REPORT),
                "exists": MD_REPORT.exists(),
                "bytes": MD_REPORT.stat().st_size if MD_REPORT.exists() else "",
                "role": "Markdown source summary for generated PPT",
            },
        ]
    )
    with MANIFEST.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["relative_path", "exists", "bytes", "role"])
        writer.writeheader()
        writer.writerows(rows)


def update_reports_manifest():
    manifest = R2 / "MANIFEST.tsv"
    lines = []
    for path in sorted(R2.rglob("*")):
        if path.is_file():
            lines.append(f"{path.relative_to(R2)}\t{path.stat().st_size}")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def copy_script_to_reports():
    dest = R2 / "05_SCRIPTS_AND_CONFIG" / "tools" / Path(__file__).name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__), dest)
    return dest


def main() -> int:
    from build_nima_centered_phase07_12_ppt import main as build_nima_centered

    return build_nima_centered()


if __name__ == "__main__":
    raise SystemExit(main())
