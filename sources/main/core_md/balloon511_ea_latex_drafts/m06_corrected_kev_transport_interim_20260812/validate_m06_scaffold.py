#!/usr/bin/env python3
"""Validate the M06 corrected-keV non-full interim manuscript."""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]

EN = HERE / "balloon511_ea_draft_en_m06_corrected_kev_transport_interim_20260812.tex"
ZH = HERE / "balloon511_ea_draft_zh_m06_corrected_kev_transport_interim_20260812.tex"
NUMBERS = HERE / "manuscript_numbers.json"
SNAPSHOT = HERE / "PARENT_SNAPSHOT.json"

REQUIRED_FILES = {
    "README.md",
    "CHANGELOG.md",
    "DATA_AUTHORITY_MATRIX.md",
    "PARENT_SNAPSHOT.json",
    "manuscript_numbers.json",
    "validate_m06_scaffold.py",
    EN.name,
    ZH.name,
}

FORBIDDEN_BUILD_SUFFIXES = {
    ".aux", ".bbl", ".bcf", ".blg", ".fdb_latexmk", ".fls", ".log",
    ".out", ".pdf", ".run.xml", ".synctex.gz", ".xdv",
}

FORBIDDEN_ACTIVE_NUMERIC_TOKENS = {
    "6.965\\times10^{-3}",
    "9.862\\times10^{-4}",
    "1.974\\times10^{-5}",
    "5.293\\times10^{-5}",
    "36.4525153\\,\\mathrm{Bq}",
    "141.83\\,\\mathrm{Bq}",
    "Z=15.20",
    "显著度 15.20",
}

FORBIDDEN_ACTIVE_AUTHORITY_PHRASES = {
    "sensitivity reported here",
    "post-selection rates and sensitivity results",
    "the final BGO geometry",
    "final optimized geometry",
    "For the final scintillator active-veto calculation",
    "本文报告的 $3\\sigma$ 灵敏度",
    "选后率和灵敏度结果",
    "最终 BGO 几何",
    "最终优化版本",
    "在最终闪烁体主动 veto 计算中",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(relative: str | Path) -> dict:
    path = relative if isinstance(relative, Path) else REPO / relative
    return json.loads(path.read_text(encoding="utf-8"))


def close(a: float | int | None, b: float | int | None) -> bool:
    if a is None or b is None:
        return a is b
    return math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=1e-15)


def active_tex(text: str) -> tuple[str, str]:
    open_token = "\n\\iffalse\n"
    close_token = "\n\\fi\n"
    if text.count(open_token) != 1 or text.count(close_token) != 1:
        raise ValueError("expected one inherited-history \\iffalse ... \\fi block")
    before, rest = text.split(open_token, 1)
    disabled, after = rest.split(close_token, 1)
    return before + after, disabled


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def main() -> int:
    errors: list[str] = []

    for name in sorted(REQUIRED_FILES):
        path = HERE / name
        if not path.is_file() or path.is_symlink():
            fail(errors, f"missing, non-regular, or linked required file: {name}")

    for path in HERE.rglob("*"):
        if path.is_file() and any(path.name.lower().endswith(x) for x in FORBIDDEN_BUILD_SUFFIXES):
            fail(errors, f"compiled/build artifact present in M06: {path.name}")

    try:
        snapshot = load_json(SNAPSHOT)
        numbers = load_json(NUMBERS)
    except Exception as exc:
        fail(errors, f"cannot parse local JSON: {exc}")
        snapshot, numbers = {}, {}

    if snapshot.get("publication_authority") is not False:
        fail(errors, "parent snapshot must keep publication_authority=false")
    if numbers.get("publication_authority") is not False:
        fail(errors, "number registry must keep publication_authority=false")
    if numbers.get("schema_version") != "2.0":
        fail(errors, "number registry schema_version must be 2.0")

    artifacts = snapshot.get("artifacts", [])
    if len(artifacts) != 6:
        fail(errors, f"expected six M05 lineage artifacts, found {len(artifacts)}")
    for artifact in artifacts:
        relative = artifact.get("path")
        if not isinstance(relative, str):
            fail(errors, "snapshot artifact has no path")
            continue
        parent = REPO / relative
        if not parent.is_file() or parent.is_symlink():
            fail(errors, f"M05 parent artifact missing: {relative}")
            continue
        if parent.stat().st_size != artifact.get("bytes") or sha256(parent) != artifact.get("sha256"):
            fail(errors, f"M05 parent artifact changed: {relative}")
        copied_to = artifact.get("copied_to")
        if copied_to:
            target = REPO / copied_to
            if not target.is_file() or target.is_symlink():
                fail(errors, f"M06 target missing or linked: {copied_to}")
            elif (parent.stat().st_dev, parent.stat().st_ino) == (target.stat().st_dev, target.stat().st_ino):
                fail(errors, f"M06 target is a hard link to M05: {copied_to}")

    source = numbers.get("source_contract", {})
    authorities = numbers.get("authorities", {})
    authority_specs = [
        (source.get("path"), source.get("sha256"), None),
        (source.get("static_validation_path"), source.get("static_validation_sha256"), "PASS"),
        (authorities.get("gamma_prefix", {}).get("ledger_path"), authorities.get("gamma_prefix", {}).get("ledger_sha256"), None),
        (authorities.get("gamma_prefix", {}).get("validation_path"), authorities.get("gamma_prefix", {}).get("validation_sha256"), None),
        (authorities.get("gamma_postprocess", {}).get("summary_path"), authorities.get("gamma_postprocess", {}).get("summary_sha256"), None),
        (authorities.get("gamma_postprocess", {}).get("validation_path"), authorities.get("gamma_postprocess", {}).get("validation_sha256"), "PASS"),
        (authorities.get("gamma_postprocess", {}).get("spectrum_png_path"), authorities.get("gamma_postprocess", {}).get("spectrum_png_sha256"), None),
        (authorities.get("gamma_postprocess", {}).get("spectrum_svg_path"), authorities.get("gamma_postprocess", {}).get("spectrum_svg_sha256"), None),
        (authorities.get("gamma_postprocess", {}).get("veto_png_path"), authorities.get("gamma_postprocess", {}).get("veto_png_sha256"), None),
        (authorities.get("batch0004_partial", {}).get("ledger_path"), authorities.get("batch0004_partial", {}).get("ledger_sha256"), None),
        (authorities.get("batch0004_partial", {}).get("validation_path"), authorities.get("batch0004_partial", {}).get("validation_sha256"), "PASS"),
        (authorities.get("batch0005_addon", {}).get("ledger_path"), authorities.get("batch0005_addon", {}).get("ledger_sha256"), None),
        (authorities.get("batch0005_addon", {}).get("validation_path"), authorities.get("batch0005_addon", {}).get("validation_sha256"), "PASS"),
    ]
    for relative, expected_hash, expected_status in authority_specs:
        if not isinstance(relative, str) or not isinstance(expected_hash, str):
            fail(errors, "authority registry has an incomplete path/hash pair")
            continue
        path = REPO / relative
        if not path.is_file():
            fail(errors, f"authority artifact missing: {relative}")
            continue
        if sha256(path) != expected_hash:
            fail(errors, f"authority SHA-256 mismatch: {relative}")
        if expected_status:
            data = load_json(path)
            if data.get("status") != expected_status or data.get("errors"):
                fail(errors, f"authority validation is not clean PASS: {relative}")

    # Exact gamma row reconciliation against the PASS post-process summary.
    try:
        gamma_summary = load_json(authorities["gamma_postprocess"]["summary_path"])
        expected_rows = numbers.get("gamma_cutflow_by_geometry_selection_window", [])
        expected_index = {(r["geometry"], r["selection"], r["window"]): r for r in expected_rows}
        actual_rows = [r for g in gamma_summary.get("geometries", {}).values() for r in g.get("cutflow", [])]
        actual_index = {(r["geometry"], r["selection"], r["window"]): r for r in actual_rows}
        if len(expected_rows) != 24 or len(expected_index) != 24 or len(actual_index) != 24:
            fail(errors, f"gamma cutflow must contain 24 unique rows; registry={len(expected_index)}, authority={len(actual_index)}")
        field_map = {
            "primary_count": "primary_count",
            "sum_TT_s": "sum_TT_s",
            "count": "count",
            "rate_s-1": "rate_s-1",
            "efficiency_per_primary": "efficiency_per_primary",
            "veto_survival": "veto_survival_fraction",
        }
        for key, record in expected_index.items():
            actual = actual_index.get(key)
            if actual is None:
                fail(errors, f"gamma authority row missing: {key}")
                continue
            for own, remote in field_map.items():
                if not close(record.get(own), actual.get(remote)):
                    fail(errors, f"gamma mismatch {key} field {own}")
            if not all(close(a, b) for a, b in zip(record.get("garwood95_s-1", []), [actual.get("rate_garwood95_low_s-1"), actual.get("rate_garwood95_high_s-1")])):
                fail(errors, f"gamma Garwood mismatch: {key}")
            if not all(close(a, b) for a, b in zip(record.get("wilson95", []), [actual.get("efficiency_wilson95_low"), actual.get("efficiency_wilson95_high")])):
                fail(errors, f"gamma Wilson mismatch: {key}")
    except Exception as exc:
        fail(errors, f"gamma reconciliation failed: {exc}")

    # Exact per-campaign exposure reconciliation for batch0004 and batch0005.
    try:
        expected_exposure = numbers.get("transport_exposure_by_batch_stage_geometry", [])
        exp_index = {(r["batch"], r["stage"], r["geometry"]): r for r in expected_exposure}
        actual_index: dict[tuple[str, str, str], dict] = {}
        for batch, auth_key in (("0004", "batch0004_partial"), ("0005", "batch0005_addon")):
            ledger = load_json(authorities[auth_key]["ledger_path"])
            for campaign in ledger.get("campaigns", []):
                jobs = campaign.get("jobs", [])
                key = (batch, campaign["stage"], campaign["geometry"])
                actual_index[key] = {
                    "new_events": sum(job.get("events", 0) for job in jobs),
                    "cumulative_events": campaign.get("cumulative_events"),
                    "TT_s": campaign.get("TT_s_new_sum"),
                    "RP_records": sum(job.get("isotope_store", {}).get("RP_record_count", 0) for job in jobs),
                    "sum_RP": sum(sum(item.get("RP", 0.0) for item in job.get("isotope_store", {}).get("RP_records", [])) for job in jobs),
                }
        if len(exp_index) != 26 or len(actual_index) != 26:
            fail(errors, f"transport exposure must contain 26 unique rows; registry={len(exp_index)}, authority={len(actual_index)}")
        for key, record in exp_index.items():
            actual = actual_index.get(key)
            if actual is None:
                fail(errors, f"transport authority row missing: {key}")
                continue
            for field in ("new_events", "TT_s", "RP_records", "sum_RP"):
                if not close(record.get(field), actual.get(field)):
                    fail(errors, f"transport mismatch {key} field {field}")
            if "cumulative_events" in record and not close(record["cumulative_events"], actual.get("cumulative_events")):
                fail(errors, f"transport mismatch {key} field cumulative_events")
    except Exception as exc:
        fail(errors, f"transport-exposure reconciliation failed: {exc}")

    blocked = numbers.get("blocked_claims", {})
    required_blocked = {
        "complete_seven_family_total", "proton_weighted_estimate", "activity_Bq",
        "delayed_rate", "common_detector_response_closure", "geometry_promotion",
        "mission_significance", "flux_sensitivity",
    }
    for key in required_blocked:
        if blocked.get(key) is not True:
            fail(errors, f"required claim is not blocked: {key}")

    active_figure_count = 0
    for language, path in (("en", EN), ("zh", ZH)):
        try:
            text = path.read_text(encoding="utf-8")
            active, disabled = active_tex(text)
        except Exception as exc:
            fail(errors, f"cannot parse {language} TeX authority boundary: {exc}")
            continue
        if "DRAFT -- NOT_PUBLICATION_AUTHORITY" not in active:
            fail(errors, f"{language} TeX lacks active draft banner")
        if len(disabled) < 10000:
            fail(errors, f"{language} inherited M05 block is unexpectedly short")
        for token in FORBIDDEN_ACTIVE_NUMERIC_TOKENS:
            if token in active:
                fail(errors, f"{language} active TeX contains blocked inherited token: {token}")
        for phrase in FORBIDDEN_ACTIVE_AUTHORITY_PHRASES:
            if phrase in active:
                fail(errors, f"{language} active TeX contains authority-leaking phrase: {phrase}")
        required = {
            "2{,}001{,}000",
            "tab:m06_gamma_cutflow" if language == "en" else "tab:m06_gamma_cutflow_zh",
            "tab:m06_transport_exposure" if language == "en" else "tab:m06_transport_exposure_zh",
            "gamma_prefix76_2p001m_diagnostic_tes_spectra.png",
            "gamma_prefix76_2p001m_diagnostic_veto_cutflow.png",
            "not activity" if language == "en" else "不是活度",
            "not support a full background rate" if language == "en" else "不支持完整本底率",
            "historical design target" if language == "en" else "历史设计目标",
            "corrected mission sensitivity is not reported" if language == "en" else "更正后的任务灵敏度不在 M06 中报告",
            "S3d-O8 BGO candidate" if language == "en" else "S3d-O8 BGO 候选几何",
            "not a geometry promotion" if language == "en" else "不代表几何晋级",
        }
        for token in required:
            if token not in active:
                fail(errors, f"{language} active TeX lacks required interim token: {token}")
        figure_targets = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", active)
        if not figure_targets:
            fail(errors, f"{language} active TeX has no includegraphics target")
        for target in figure_targets:
            figure = (path.parent / target).resolve()
            active_figure_count += 1
            if not figure.is_file():
                fail(errors, f"{language} active includegraphics target does not exist: {target}")

    matrix = (HERE / "DATA_AUTHORITY_MATRIX.md").read_text(encoding="utf-8")
    for token in ("5424eeca", "b4de513e", "670bc6f1", "RP", "BLOCKED", "NOT_PUBLICATION_AUTHORITY"):
        if token not in matrix:
            fail(errors, f"authority matrix lacks token: {token}")

    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, ensure_ascii=False, indent=2))
        return 1

    report = {
        "status": "PASS",
        "publication_authority": False,
        "parent_artifacts_verified": len(artifacts),
        "authority_artifacts_hash_verified": len(authority_specs),
        "gamma_geometry_selection_window_records_verified": len(numbers["gamma_cutflow_by_geometry_selection_window"]),
        "transport_stage_geometry_records_verified": len(numbers["transport_exposure_by_batch_stage_geometry"]),
        "bilingual_active_interim_documents_verified": 2,
        "active_includegraphics_targets_verified": active_figure_count,
        "compiled_artifacts_in_m06": 0,
        "blocked_claims_verified": len(required_blocked),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
