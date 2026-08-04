#!/usr/bin/env python3
"""Validate the Mass activation audit and its EN/ZH manuscript integration."""

from __future__ import annotations

import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parents[1]
AUDIT = PACKAGE / "data/mass_activation_material_family_audit.json"
PAPER = ROOT / "core_md/balloon511_ea_latex_drafts"
EN = PAPER / "balloon511_ea_draft_en.tex"
ZH = PAPER / "balloon511_ea_draft_zh.tex"


def require(text: str, fragments: list[str], label: str) -> None:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise AssertionError(f"{label} missing {missing}")


def forbid(text: str, fragments: list[str], label: str) -> None:
    present = [fragment for fragment in fragments if fragment in text]
    if present:
        raise AssertionError(f"{label} retains stale text {present}")


def main() -> int:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    if audit["status"] != "PASS_MASS_ACTIVATION_MATERIAL_FAMILY_AUDIT":
        raise AssertionError(audit["status"])
    if audit["problems"]:
        raise AssertionError(audit["problems"])
    if not math.isclose(
        float(audit["checks"]["total_activity_Bq"]),
        float(audit["checks"]["retained_total_activity_Bq"]),
        rel_tol=0.0,
        abs_tol=1.0e-6,
    ):
        raise AssertionError("activity total does not close")

    en = EN.read_text(encoding="utf-8")
    zh = ZH.read_text(encoding="utf-8")
    require(
        en,
        [
            "products contribute $94.25\\%$",
            "$\\mu^-$-induced products $5.38\\%$",
            "CsI ($63.08\\%$)",
            "$D_{\\mathrm{TV}}=0.823$",
            "$M=50{,}000$ sampled",
            "26 line-window records",
            "primary background budget is therefore",
            "first-scatter cone as an aperture-consistency",
        ],
        "English manuscript",
    )
    require(
        zh,
        [
            "中子诱发产物占 $94.25\\%$",
            "$\\mu^-$ 诱发产物占 $5.38\\%$",
            "$63.08\\%$、$15.71\\%$ 和",
            "$D_{\\mathrm{TV}}=0.823$",
            "$M=50{,}000$ 个产生位置",
            "26 条线窗延迟记录",
            "主要本底预算定义在探测器/低温系统分支上",
            "第一散射锥用于孔径一致性检验",
        ],
        "Chinese manuscript",
    )
    stale = [
        "material-category fractions have not yet been regenerated",
        "adequacy remains to be evaluated at the selected-rate level",
        "selected-rate behavior remains to be tested",
        "geometry-specific appendix position-distribution figure remains",
        "材料类别比例尚未重新生成",
        "仍待在选后率层面评估",
        "选后率行为仍待",
        "附录图仍待重制",
        "Optics-mass prompt and delayed background are not included",
        "This work does not perform imaging",
        "光学质量的瞬发和延迟本底尚未纳入",
        "本文不追求成像",
    ]
    forbid(en, stale, "English manuscript")
    forbid(zh, stale, "Chinese manuscript")

    for tex in (EN, ZH):
        pdf = tex.with_suffix(".pdf")
        if not pdf.is_file() or pdf.stat().st_mtime < tex.stat().st_mtime:
            raise AssertionError(f"stale or missing PDF: {pdf}")

    result = {
        "status": "PASS_EXISTING_EVIDENCE_MANUSCRIPT_SYNC",
        "audit": str(AUDIT.relative_to(ROOT)),
        "manuscripts": [str(EN.relative_to(ROOT)), str(ZH.relative_to(ROOT))],
        "checks": [
            "retained activity closure",
            "incident-family and material fractions",
            "Methods/Results correspondence",
            "absence of stale not-yet-complete wording",
            "current compiled PDFs",
        ],
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
