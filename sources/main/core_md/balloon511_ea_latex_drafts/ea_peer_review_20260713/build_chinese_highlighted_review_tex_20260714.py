#!/usr/bin/env python3
"""Chinese phrase-anchor definitions for the highlighted review PDF builder.

The English manuscript remains the revision authority.  This builder creates a
derived Chinese reading edition in which every active formal review item is
attached to the corresponding Chinese phrase.  The production renderer is
``build_chinese_highlighted_review_pdf_20260714.py``; PDF-level rendering is
used because TeX ``soul`` highlighting cannot reconstruct XeCJK text safely.
"""

from __future__ import annotations

from pathlib import Path
import runpy


HERE = Path(__file__).resolve().parent
MANUSCRIPT_DIR = HERE.parent
SOURCE = MANUSCRIPT_DIR / "balloon511_ea_draft_zh.tex"
OUTPUT_TEX = MANUSCRIPT_DIR / "balloon511_ea_draft_zh_peer_review_highlighted_20260714.tex"
EN_DEFINITIONS = HERE / "build_peer_review.py"
CN_DEFINITIONS = HERE / "build_peer_review_cn_integrated_20260714.py"


# Exact current-Chinese anchors for the 52 active line comments.  The keys are
# the English review identifiers and anchors, which makes coverage auditable
# against build_peer_review.py while allowing the displayed phrase to follow
# the Chinese translation and its independent line breaks.
ZH_ANCHORS: dict[tuple[str, str], str] = {
    ("J02", "Detector-coupled Monte Carlo estimate of background and unresolved-line sensitivity for a balloon-borne 511 keV Laue-lens TES telescope"): "气球载 511 keV Laue 透镜 TES 望远镜本底和未分辨线灵敏度的探测器耦合 Monte Carlo 估计",
    ("M18", "single payload-plane observational reference flux"): "唯一的载荷平面观测参考通量",
    ("M17", "increasing the collecting-area-to-detector-area ratio"): "提高收集面积与探测器面积之比",
    ("M17", "estimated interaction efficiency of about"): "预估相互作用效率约为",
    ("M16", "estimated energy resolution and simulation input"): "预估能量分辨率和模拟输入",
    ("M02", "optimized BGO transport records shield hits"): "优化 BGO 输运",
    ("S02", "focal-plane plane"): "焦平面所在平面",
    ("M08", "mosaic system is adopted to make the Monte Carlo calculation convenient"): "在满足预期设计聚焦性能的同时便于蒙特卡洛计算",
    ("M08", "to avoid double counting with standard photoelectric absorption"): "为避免与标准光电吸收重复计数",
    ("M01", "primary background budget"): "主要本底预算定义在探测器/低温系统分支上",
    ("M19", "PARMA3.0"): "PARMA3.0",
    ("S02", "custom recording hook"): "自定义记录钩子",
    ("M04", "source layers used"): "当前探测器耦合计算使用的源层级",
    ("M18", "surviving signal rate"): "存活信号率为",
    ("M05", "not a flight forecast for a named launch campaign"): "而非某一具体发射航次的飞行预报",
    ("M07", "only optimized geometry"): "下文全链和任务计算只使用这一套优化几何",
    ("M12", "counting metric"): "直观的计数指标",
    ("M09", "streams are combined"): "采用独立流的泊松叠加",
    ("M10", "candidate group"): "归并为一个符合候选组",
    ("S02", "starved continuum"): "该窗线主导，连续谱饥饿",
    ("M20", "if any of these 81 trajectories"): "只要这 81 条轨迹中存在任一条",
    ("M20", "retained without ordering"): "超出者不再定序而径直保留",
    ("M20", "Unreconstructed events remain in the baseline rate accounting"): "未重建类保留在基准率核算中",
    ("M20", "retained legacy geometry"): "保留旧几何中的",
    ("M05", "synthetic reference profile"): "合成参考剖面",
    ("M13", "validate the combined"): "直接轨迹输运对合并",
    ("M04", "not present as a narrow feature in the EXPACS continuum"): "EXPACS 连续谱不含这一窄线",
    ("M23", "atmospheric paths"): "大气路径",
    ("M07", "most important active surface"): "最重要的主动表面",
    ("M11", "five final prompt records"): "最终 5 条瞬发记录",
    ("S02", "preregistered"): "预注册主值",
    ("M11", "exact upper counting endpoint"): "精确计数上端",
    ("S02", "two columns answer two useful questions"): "两列回答两个直接问题",
    ("S02", "strongest lesson"): "最有价值的经验",
    ("M23", "failure of anticoincidence"): "并非反符合失效",
    ("S01", "Scope and next steps"): "适用范围与下一步",
    ("J01", "Before publication"): "正式发表前",
    ("J01", "To be completed before journal submission"): "经费来源",
    ("J01", "doi:10.1103/RevModPhys.83.1001"): "doi:10.1103/RevModPhys.83.1001",
    ("N01", "live factor remains between 0.97165 and 0.97985"): "偶然符合活时间因子保持在 0.97165--0.97985",
    ("N02", "plane-parallel slant depth"): "平面平行近似下的斜程柱深",
    ("N03", "require three source layers"): "还需要三层源",
    ("N04", "generated with replicated samples"): "非光子粒子族采用复制样本生成",
    ("N05", "can look exactly like a source photon"): "光子可以与源光子具有",
    ("N06", "ground-state half-lives checked"): "基态半衰期已对照 NUBASE2020 校验",
    ("N07", "dedicated INTEGRAL/IBIS compact-source search"): "INTEGRAL/IBIS 开展的紧致源专项搜索",
    ("N08", "Complete selection gave"): "完整的八族选择",
    ("N09", "event instances yield 1275 mixed-stream coincidences"): "跨流偶然符合",
    ("N10", "condition corresponding to"): "对应的太阳条件",
    ("Re-M02", "kept fixed throughout the final-geometry calculation"): "在整个最终几何计算中保持不变",
    ("Re-M08", "each sample interaction lengths in the same competition framework"): "在同一竞争框架下各自抽样相互作用长度",
    ("Re-M09", "single detector time axis carrying the three"): "同时承载三流物理率的探测器时间轴",
}


# The prior English review represented these six formal items as margin notes.
# The Chinese reading edition can anchor each one to an actual translated
# sentence, so they are highlighted as well.
ZH_FORMAL_ANCHORS = {
    "M06": "精细谱线轮廓测量",
    "M14": "本节描述从源生成到飞行性能评估的整条端到端模拟链",
    "M15": "不同源流的曝光权重不同，最终带权率才是物理结果",
    "M21": "既非气球遥测，也非源可见性/指向时间表",
    "M22": "展示显著度如何随时间积累，而不是只给终点",
    "J03": "伦理审批与参与同意",
}


def markup(anchor: str, color: str, subject: str, body: str) -> str:
    return (
        "\\pdfmarkupcomment[markup=Highlight,"
        f"color={{{color}}},author={{中文同行审阅}},subject={{{subject}}}]"
        f"{{{anchor}}}{{{body}}}"
    )


def overview_note(body: str) -> str:
    return (
        "\\vadjust{\\smash{\\hbox to 0pt{"
        "\\pdfcomment[icon=Note,color={0.72 0.72 0.72},author={中文同行审阅},"
        "subject={A00｜总评与阅读说明}]"
        f"{{{body}}}"
        "\\hss}}}"
    )


def subject_for(rid: str, reviews_by_id, cn_defs) -> str:
    if rid.startswith("Re-"):
        return f"{rid}｜第二轮复核"
    meta = reviews_by_id[rid]
    zh = cn_defs["ZH_REVIEWS"][rid]
    round_label = "第二轮新增｜" if rid.startswith("N") else ""
    return f"{rid}｜{round_label}{cn_defs['SEVERITY_ZH'][meta.severity]}｜{zh.category}"


def color_for(rid: str, kind: str, reviews_by_id, en_defs, cn_defs) -> str:
    if rid.startswith("Re-"):
        return en_defs["R2_COLORS"]["response"]
    if rid.startswith("N"):
        return en_defs["R2_COLORS"][kind]
    return cn_defs["COLORS"][reviews_by_id[rid].severity]


def main() -> None:
    en_defs = runpy.run_path(str(EN_DEFINITIONS), run_name="ea_review_en_defs")
    cn_defs = runpy.run_path(str(CN_DEFINITIONS), run_name="ea_review_cn_defs")
    reviews = [*en_defs["REVIEWS"], *en_defs["REVIEWS_R2"]]
    reviews_by_id = {review.rid: review for review in reviews}

    review_rows: list[tuple[str, str, str]] = []
    for rid, _category, en_anchor, _note, _occurrence in en_defs["ANNOTATIONS"]:
        if rid != "M03":
            review_rows.append((rid, en_anchor, ""))
    for rid, kind, _category, en_anchor, _note in en_defs["ANNOTATIONS_R2"]:
        review_rows.append((rid, en_anchor, kind))

    expected_keys = {(rid, anchor) for rid, anchor, _kind in review_rows}
    if set(ZH_ANCHORS) != expected_keys:
        missing = sorted(expected_keys - set(ZH_ANCHORS))
        extra = sorted(set(ZH_ANCHORS) - expected_keys)
        raise RuntimeError(f"Chinese anchor coverage mismatch; missing={missing}, extra={extra}")
    if set(ZH_FORMAL_ANCHORS) != set(cn_defs["MISSING_FORMAL_ANCHORS"]):
        raise RuntimeError("Formal-anchor coverage differs from the retained review definition")

    source = SOURCE.read_text(encoding="utf-8")
    package_anchor = "\\hypersetup{hidelinks}"
    if source.count(package_anchor) != 1:
        raise RuntimeError("Could not locate the unique hyperref setup")
    source = source.replace(
        package_anchor,
        "\\hypersetup{hidelinks,unicode=true}\n"
        "\\usepackage{pdfcomment}\n"
        "% Chinese review highlights: red major, orange moderate, blue structural, green journal; violet/teal round 2.\n",
        1,
    )

    highlighted = 0
    for rid, en_anchor, kind in review_rows:
        zh_anchor = ZH_ANCHORS[(rid, en_anchor)]
        count = source.count(zh_anchor)
        if count != 1:
            raise RuntimeError(f"Expected one Chinese anchor for {rid}/{en_anchor!r}; found {count}: {zh_anchor!r}")
        local = cn_defs["PINPOINT_ZH"][(rid, en_anchor)]
        subject = cn_defs["tex_comment_safe"](subject_for(rid, reviews_by_id, cn_defs))
        body = cn_defs["review_body"](rid, local, reviews_by_id)
        color = color_for(rid, kind, reviews_by_id, en_defs, cn_defs)
        source = source.replace(zh_anchor, markup(zh_anchor, color, subject, body), 1)
        highlighted += 1

    for rid, zh_anchor in ZH_FORMAL_ANCHORS.items():
        count = source.count(zh_anchor)
        if count != 1:
            raise RuntimeError(f"Expected one formal Chinese anchor for {rid}; found {count}: {zh_anchor!r}")
        local = "本条原无行内高亮；当前中文阅读稿已将其锚定到对应中文句段。"
        subject = cn_defs["tex_comment_safe"](subject_for(rid, reviews_by_id, cn_defs))
        body = cn_defs["review_body"](rid, local, reviews_by_id)
        color = cn_defs["COLORS"][reviews_by_id[rid].severity]
        source = source.replace(zh_anchor, markup(zh_anchor, color, subject, body), 1)
        highlighted += 1

    title_anchor = ZH_ANCHORS[(
        "J02",
        "Detector-coupled Monte Carlo estimate of background and unresolved-line sensitivity for a balloon-borne 511 keV Laue-lens TES telescope",
    )]
    title_markup = markup(
        title_anchor,
        cn_defs["COLORS"][reviews_by_id["J02"].severity],
        cn_defs["tex_comment_safe"](subject_for("J02", reviews_by_id, cn_defs)),
        cn_defs["review_body"](
            "J02",
            cn_defs["PINPOINT_ZH"][(
                "J02",
                "Detector-coupled Monte Carlo estimate of background and unresolved-line sensitivity for a balloon-borne 511 keV Laue-lens TES telescope",
            )],
            reviews_by_id,
        ),
    )
    # The title has already been replaced above. Attach the overview note to
    # that rendered title without introducing a standalone line or page shift.
    if source.count(title_markup) != 1:
        raise RuntimeError("Could not locate highlighted title for overview-note attachment")
    overview = cn_defs["tex_comment_safe"](cn_defs["OVERVIEW_ZH"])
    source = source.replace(title_markup, title_markup + overview_note(overview), 1)

    header = (
        "% Derived Chinese reading edition with line-level peer-review highlights.\n"
        "% English manuscript remains the revision authority; this file is regenerated from balloon511_ea_draft_zh.tex.\n"
        f"% Active highlighted review entries: {highlighted}; overview notes: 1.\n"
    )
    OUTPUT_TEX.write_text(header + source, encoding="utf-8")
    print(f"Wrote {OUTPUT_TEX}")
    print(f"Highlighted formal/page entries: {highlighted}; overview notes: 1")


if __name__ == "__main__":
    print("Anchor definitions only; run build_chinese_highlighted_review_pdf_20260714.py.")
