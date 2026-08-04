#!/usr/bin/env python3
"""Validate that the EA manuscripts and figures match the response authority."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parents[1]
DATA = PACKAGE / "data"
PAPER = ROOT / "core_md/balloon511_ea_latex_drafts"
SUMMARY = DATA / "o8_energy_response_closure_summary.json"
BREAKDOWN = DATA / "reference_response_background_breakdown.json"
MULTIPLICITY = DATA / "reference_response_multiplicity.json"
PROVENANCE = PAPER / "paper_source_figure_table/background_optimization_story_provenance_20260713.json"
OUTPUT = DATA / "detector_response_manuscript_sync_validation.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def close(actual: float, expected: float, *, rel: float = 1.0e-10) -> None:
    if not math.isclose(actual, expected, rel_tol=rel, abs_tol=1.0e-14):
        raise AssertionError(f"numeric mismatch: {actual!r} != {expected!r}")


def require(text: str, fragments: list[str], label: str) -> None:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise AssertionError(f"{label} is missing required fragments: {missing}")


def forbid(text: str, fragments: list[str], label: str) -> None:
    present = [fragment for fragment in fragments if fragment in text]
    if present:
        raise AssertionError(f"{label} retains stale fragments: {present}")


def main() -> int:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    breakdown = json.loads(BREAKDOWN.read_text(encoding="utf-8"))
    multiplicity = json.loads(MULTIPLICITY.read_text(encoding="utf-8"))
    provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))

    if summary["status"] != "PASS_O8_EVENT_LEVEL_420EV_FWHM_ENERGY_RESPONSE_CLOSURE":
        raise AssertionError(summary["status"])
    if breakdown["status"] != "PASS_REFERENCE_RESPONSE_BACKGROUND_BREAKDOWN":
        raise AssertionError(breakdown["status"])
    if multiplicity["status"] != "PASS_REFERENCE_RESPONSE_SPECTRA_MULTIPLICITY":
        raise AssertionError(multiplicity["status"])

    primary = summary["primary_authority"]
    w2 = primary["step05"]["windows"]["w2_510p58_511p42"]
    reference = primary["reference_step05"]["windows"]["w2_510p58_511p42"]
    close(w2["physical_reference_flux"]["background_cps"], 0.005849518473351069)
    close(w2["physical_reference_flux"]["signal_cps_at_reference_flux"], 0.001113481171255802)
    close(primary["mission_fold"]["Z20d"], 18.563290210456216)
    close(primary["mission_fold"]["flux_3sigma_20d_ph_cm2_s"], 1.616092818669709e-5)
    close(reference["physical_reference_flux"]["background_cps"], 0.046432049209645075)
    close(primary["reference_mission_fold"]["flux_3sigma_20d_ph_cm2_s"], 4.442557438187135e-5)

    en_path = PAPER / "balloon511_ea_draft_en.tex"
    zh_path = PAPER / "balloon511_ea_draft_zh.tex"
    en = en_path.read_text(encoding="utf-8")
    zh = zh_path.read_text(encoding="utf-8")
    require(
        en,
        [
            "$(4.64320\\pm0.54324)\\times10^{-2}\\cps$",
            "Prompt background & Line-window pre-veto & 148",
            "Prompt subtotal & 63 & $4.27321\\times10^{-2}$",
            "Delayed activation & 26 & $3.69999\\times10^{-3}$",
            "24 $^{64}$Cu, 2 $^{61}$Cu",
            "$61.68\\%$ of the focused-signal rate",
            "An independent topology benchmark uses the MEGAlib \\texttt{revan}",
            "$5.84952\\times10^{-3}\\cps$",
            "a 64-seed response ensemble tests numerical stability",
        ],
        "English manuscript",
    )
    require(
        zh,
        [
            "$(4.64320\\pm0.54324)\\times10^{-2}\\cps$",
            "瞬发本底 & 线窗预 veto & 148",
            "瞬发小计 & 63 & $4.27321\\times10^{-2}$",
            "延迟活化 & 26 & $3.69999\\times10^{-3}$",
            "24 条 $^{64}$Cu、2 条 $^{61}$Cu",
            "$61.68\\%$ 的聚焦信号率",
            "MEGAlib \\texttt{revan} 康普顿事例重建器",
            "$5.84952\\times10^{-3}\\cps$",
            "64 个确定性响应种子提供独立的数值积分检查",
        ],
        "Chinese manuscript",
    )
    stale = [
        "4.80735",
        "25 of the 28",
        "25 of 28",
        "unnoised summed energies",
        "未加噪的求和能量",
        "Prompt background & Line-window pre-veto & 153",
        "瞬发本底 & 线窗预 veto & 153",
        "\\added{",
        "\\rewritten{",
        "\\textcolor{red}",
        "\\color{red}",
    ]
    forbid(en, stale, "English manuscript")
    forbid(zh, stale, "Chinese manuscript")

    for tex_path in (en_path, zh_path):
        pdf_path = tex_path.with_suffix(".pdf")
        if not pdf_path.is_file() or pdf_path.stat().st_size < 100_000:
            raise AssertionError(f"missing or implausibly small PDF: {pdf_path}")
        if pdf_path.stat().st_mtime < tex_path.stat().st_mtime:
            raise AssertionError(f"PDF is older than TeX source: {pdf_path}")

    for rel_path, record in provenance["inputs"].items():
        path = ROOT / rel_path
        if sha256(path) != record["sha256"]:
            raise AssertionError(f"stale figure provenance for {rel_path}")

    payload = {
        "status": "PASS_DETECTOR_RESPONSE_MANUSCRIPT_SYNC",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "authorities": {
            "response_summary": str(SUMMARY.relative_to(ROOT)),
            "reference_breakdown": str(BREAKDOWN.relative_to(ROOT)),
            "reference_multiplicity": str(MULTIPLICITY.relative_to(ROOT)),
            "figure_provenance": str(PROVENANCE.relative_to(ROOT)),
        },
        "manuscripts": {
            "english_tex_sha256": sha256(en_path),
            "english_pdf_sha256": sha256(en_path.with_suffix(".pdf")),
            "chinese_tex_sha256": sha256(zh_path),
            "chinese_pdf_sha256": sha256(zh_path.with_suffix(".pdf")),
        },
        "checks": [
            "response and reference numerical authorities",
            "English/Chinese required result strings",
            "absence of stale pre-response numbers and active red revision markup",
            "compiled PDFs newer than TeX sources",
            "figure-provenance input hashes",
        ],
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
