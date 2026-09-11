#!/usr/bin/env python3
"""Validate the public-facing EN/ZH EA rewrite against audited design results."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
PAPER = ROOT / "core_md/balloon511_ea_latex_drafts"
EN = PAPER / "balloon511_ea_draft_en.tex"
ZH = PAPER / "balloon511_ea_draft_zh.tex"
EN_PDF = EN.with_suffix(".pdf")
ZH_PDF = ZH.with_suffix(".pdf")
EN_LOG = EN.with_suffix(".log")
ZH_LOG = ZH.with_suffix(".log")
FULLCHAIN = PACKAGE / "data/s3d_o8_fullchain_independent_validation.json"
SCREENING = PACKAGE / "data/s3d_o8_screening_analysis.json"
OUT = PACKAGE / "data/s3d_o8_manuscript_sync_validation.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def now_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def main() -> int:
    required = [EN, ZH, EN_PDF, ZH_PDF, EN_LOG, ZH_LOG, FULLCHAIN, SCREENING]
    problems = [f"missing {path}" for path in required if not path.is_file()]
    if problems:
        raise SystemExit("; ".join(problems))

    en = EN.read_text(encoding="utf-8")
    zh = ZH.read_text(encoding="utf-8")
    authority = json.loads(FULLCHAIN.read_text(encoding="utf-8"))
    screening = json.loads(SCREENING.read_text(encoding="utf-8"))
    if authority.get("status") != "PASS_O8_FULLCHAIN_INDEPENDENT_VALIDATION":
        problems.append(f"full-chain authority={authority.get('status')!r}")
    if screening.get("status") != "PASS_O8_SCREENING_PROMOTION_GATES":
        problems.append(f"screening authority={screening.get('status')!r}")

    fullchain = authority["step05_primary_window"]
    mission = authority["independent_mission_fold"]
    mass = authority["mass_ledger"]
    signal = screening["promotion_gates"]["signal"]
    authority_tokens = [
        rf"${fullchain['background_cps'] * 1e3:.5f}\times10^{{-3}}$",
        rf"${fullchain['signal_cps_at_reference_flux'] * 1e3:.5f}\times10^{{-3}}$",
        rf"${mission['F3_20d_ph_cm2_s'] * 1e5:.4f}\times10^{{-5}}$",
        rf"${mission['F3_20d_conservative95_ph_cm2_s'] * 1e5:.4f}\times10^{{-5}}$",
        f"{mass['baseline_shield_package_kg']:.3f}",
        f"{mass['optimized_shield_package_kg']:.3f}",
        rf"${mass['mass_reduction_fraction'] * 100:.2f}\%$",
        f"{signal['o8_over_heavy_control_final_acceptance']:.4f}",
        f"{signal['risk_ratio_counting_95_katz']['low']:.4f}",
        f"{signal['risk_ratio_counting_95_katz']['high']:.4f}",
    ]

    expected = {
        "en": [
            r"\subsection{Design comparison and statistical analysis}",
            r"\subsection{Reference background decomposition and optimization target}",
            r"\subsection{Constraint-first active-shield iteration}",
            r"\subsection{Optimized full-chain background and counting precision}",
            "Garwood Poisson count intervals",
            "Wilson score intervals",
            "Clopper--Pearson interval",
            "Paired signal counts",
            "17 of 18 atmospheric survivors enter through the side proxy",
            "not to a project-internal geometry or to the",
            "neutron-induced activation only",
        ],
        "zh": [
            r"\subsection{设计比较与统计分析}",
            r"\subsection{参考本底分解与优化目标}",
            r"\subsection{约束优先的主动屏蔽迭代}",
            r"\subsection{优化构型全链本底与计数精度}",
            "Garwood 泊松计数区间",
            "Wilson 评分区间",
            "Clopper--Pearson 区间",
            "配对信号计数",
            "18 条大气幸存记录中有 17 条从侧面进入",
            "并非相对项目内部几何",
            "延迟流仅含中子诱发活化",
        ],
    }
    for language, text, tokens in (("en", en, expected["en"]), ("zh", zh, expected["zh"])):
        for token in tokens + authority_tokens:
            if token not in text:
                problems.append(f"{language} missing manuscript token: {token}")

    forbidden = re.compile(
        r"s3[cd]|mass\\?_model\\?_511|\bO[0-9]+\b|fix5|"
        r"Step[~ ]?0[0-9]|\bW2\b|f10m|recover(?:y|ed)?|恢复缺口",
        re.IGNORECASE,
    )
    for language, text in (("en", en), ("zh", zh)):
        hits = sorted(set(match.group(0) for match in forbidden.finditer(text)))
        if hits:
            problems.append(f"{language} forbidden internal/recovery terms={hits}")

    for language, log_path in (("en", EN_LOG), ("zh", ZH_LOG)):
        log = log_path.read_text(encoding="utf-8", errors="replace")
        if "Overfull \\hbox" in log:
            problems.append(f"{language} compile log contains overfull hbox")
        if "undefined references" in log.lower():
            problems.append(f"{language} compile log contains undefined references")
        if re.search(r"Citation .* undefined", log, re.IGNORECASE):
            problems.append(f"{language} compile log contains undefined citation")

    if EN_PDF.stat().st_size < 1_000_000:
        problems.append("English PDF is unexpectedly small")
    if ZH_PDF.stat().st_size < 1_000_000:
        problems.append("Chinese PDF is unexpectedly small")

    payload = {
        "status": "PASS_O8_EA_MANUSCRIPT_SYNC" if not problems else "FAIL",
        "generated_at_utc": now_utc(),
        "fullchain_authority": str(FULLCHAIN.relative_to(ROOT)),
        "screening_authority": str(SCREENING.relative_to(ROOT)),
        "manuscripts": {
            "en": {
                "tex": str(EN.relative_to(ROOT)),
                "tex_sha256": sha256(EN),
                "pdf": str(EN_PDF.relative_to(ROOT)),
                "pdf_sha256": sha256(EN_PDF),
                "pdf_bytes": EN_PDF.stat().st_size,
            },
            "zh": {
                "tex": str(ZH.relative_to(ROOT)),
                "tex_sha256": sha256(ZH),
                "pdf": str(ZH_PDF.relative_to(ROOT)),
                "pdf_sha256": sha256(ZH_PDF),
                "pdf_bytes": ZH_PDF.stat().st_size,
            },
        },
        "checks": {
            "required_result_tokens_present": not any("missing manuscript token" in p for p in problems),
            "authority_derived_numeric_tokens_present": all(
                token in en and token in zh for token in authority_tokens
            ),
            "forbidden_internal_terms_absent": not any("forbidden internal" in p for p in problems),
            "compile_logs_no_overfull_or_undefined": not any("compile log" in p for p in problems),
            "pdfs_present_and_nontrivial": not any("PDF is unexpectedly small" in p for p in problems),
        },
        "problems": problems,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "output": str(OUT.relative_to(ROOT)), "problems": problems}, indent=2))
    return 0 if not problems else 2


if __name__ == "__main__":
    raise SystemExit(main())
