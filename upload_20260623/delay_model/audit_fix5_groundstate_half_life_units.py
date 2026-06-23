#!/usr/bin/env python3
"""Audit fix5 ground-state delayed-source normalization and NUBASE rows."""

from __future__ import annotations

import csv
import json
import math
import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from audit_groundstate_half_life_units import (
    REQUIRED_SELF_TEST_UNITS,
    UNIT_SECONDS,
    fixed_source_particle_types,
    format_sci,
    nubase_half_life_fields,
    nubase_line_lookup,
    parse_half_life_seconds,
    rel_diff,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[2]
LABEL = "fix5_1of10"
OUT = ROOT / "outputs" / "reports" / LABEL
CORRECTIONS = ROOT / "runs" / "step02_delay_fix_fix5_1of10" / "groundstate_activity_corrections.csv"
FIX_SUMMARY = ROOT / "runs" / "step02_delay_fix_fix5_1of10" / "source_fix_summary.json"
FIXED_SOURCE = ROOT / "runs" / "step02_delay_fix_fix5_1of10" / "activation_decay_day15_groundstate_fixed.source"
NORMALIZATION_AUDIT = ROOT / "runs" / "step02_delay_fix_fix5_1of10" / "normalization_audit_groundstate_fix.json"
NUBASE = ROOT / "inputs" / "nubase" / "nubase_2020.txt"
FIX5_GEO_SUFFIX = (
    "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
FORBIDDEN_BASELINE_SUFFIX = (
    "outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)


def configure_paths(label: str) -> None:
    global LABEL, OUT, CORRECTIONS, FIX_SUMMARY, FIXED_SOURCE, NORMALIZATION_AUDIT
    if label in ("fix5_1of10", "1of10"):
        LABEL = "fix5_1of10"
        delay_fix = ROOT / "runs" / "step02_delay_fix_fix5_1of10"
    elif label in ("fix5_fullstat_v2", "fix5_fullstat_v2_exactpos_m50000_s260613"):
        LABEL = "fix5_fullstat_v2_exactpos_m50000_s260613"
        delay_fix = ROOT / "runs" / "step02_delay_fix_fix5_fullstat_v2"
    else:
        raise SystemExit(f"unsupported fix5 ground-state audit label: {label}")
    OUT = ROOT / "outputs" / "reports" / LABEL
    CORRECTIONS = delay_fix / "groundstate_activity_corrections.csv"
    FIX_SUMMARY = delay_fix / "source_fix_summary.json"
    FIXED_SOURCE = delay_fix / "activation_decay_day15_groundstate_fixed.source"
    NORMALIZATION_AUDIT = delay_fix / "normalization_audit_groundstate_fix.json"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def source_geometry(path: Path) -> str:
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("Geometry "):
            return line.split(" ", 1)[1].strip()
    return ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="fix5_1of10")
    args = parser.parse_args()
    configure_paths(args.label)

    OUT.mkdir(parents=True, exist_ok=True)
    corrections = read_csv(CORRECTIONS)
    norm = load_json(NORMALIZATION_AUDIT)
    fix = load_json(FIX_SUMMARY)
    nubase_lines = nubase_line_lookup(NUBASE)

    self_tests = []
    for unit in REQUIRED_SELF_TEST_UNITS:
        expected = UNIT_SECONDS[unit]
        parsed = parse_half_life_seconds("1", unit)
        err = math.inf if parsed is None else rel_diff(float(parsed), expected)
        self_tests.append({"unit": unit, "expected_seconds": expected, "parsed_seconds": parsed, "rel_error": err})

    line_checks = []
    line_mismatches = []
    for row in corrections:
        line_no = int(float(row.get("nubase_line") or 0))
        line = nubase_lines.get(line_no, "")
        line_value, line_unit = nubase_half_life_fields(line)
        reported = float(row.get("nubase_half_life_s") or "nan")
        expected = parse_half_life_seconds(line_value, line_unit) if line else None
        rel_error = math.inf if expected is None or not math.isfinite(reported) else rel_diff(reported, float(expected))
        ok = bool(line) and line_value == row.get("nubase_raw_value", "").strip() and line_unit == row.get("nubase_raw_unit", "").strip() and rel_error <= 1.0e-12
        item = {
            "VN": row.get("VN", ""),
            "ZA": row.get("ZA", ""),
            "nuclide": row.get("nuclide", ""),
            "action": row.get("action", ""),
            "nubase_line": line_no,
            "csv_raw_value": row.get("nubase_raw_value", ""),
            "csv_raw_unit": row.get("nubase_raw_unit", ""),
            "line_raw_value": line_value,
            "line_raw_unit": line_unit,
            "reported_half_life_s": reported,
            "line_expected_half_life_s": "" if expected is None else expected,
            "line_rel_error": rel_error,
            "status": "PASS" if ok else "FAIL",
        }
        line_checks.append(item)
        if not ok:
            line_mismatches.append(item)

    norm_rows = []
    norm_problems = list(norm.get("problems") or [])
    for row in norm.get("rows", []):
        files = float(row["files"])
        division = float(row["division"])
        raw = float(row["rp_raw_total"])
        scaled = float(row["rp_scaled_total"])
        expected_scaled = raw / division if division else math.inf
        rel_error = rel_diff(scaled, expected_scaled) if math.isfinite(expected_scaled) else math.inf
        ok = abs(division - files) <= max(1.0e-9, 1.0e-6 * files) and rel_error <= 1.0e-12
        if not ok:
            norm_problems.append(f"normalization mismatch for tag={row['tag']}")
        norm_rows.append(
            {
                "tag": row["tag"],
                "files": row["files"],
                "division": row["division"],
                "rp_raw_total": row["rp_raw_total"],
                "rp_scaled_total": row["rp_scaled_total"],
                "expected_scaled_total": expected_scaled,
                "scaled_rel_error": rel_error,
                "status": "PASS" if ok else "FAIL",
            }
        )

    geom = source_geometry(FIXED_SOURCE)
    particle_types = fixed_source_particle_types(FIXED_SOURCE)
    forbidden_particle_types = sorted(particle_types.intersection({"74180", "74183"}))
    unit_counts = Counter(row.get("nubase_raw_unit", "") for row in corrections)
    w_rows = [row for row in corrections if int(row["ZA"]) // 1000 == 74 or "Passive_W" in row["VN"] or "Coll" in row["VN"]]
    w_activity = sum(float(row.get("new_groundstate_activity_Bq") or 0.0) for row in w_rows)

    problems = []
    if norm.get("status") != "PASS" or norm.get("problems"):
        problems.append("normalization_audit_not_pass")
    problems.extend(norm_problems)
    if line_mismatches:
        problems.append(f"nubase_line_mismatches={len(line_mismatches)}")
    if max(float(row["rel_error"]) for row in self_tests) > 1.0e-15:
        problems.append("unit_self_test_failed")
    if not geom.endswith(FIX5_GEO_SUFFIX):
        problems.append("fixed_source_geometry_not_fix5")
    if geom.endswith(FORBIDDEN_BASELINE_SUFFIX):
        problems.append("fixed_source_geometry_hits_forbidden_baseline")
    if forbidden_particle_types:
        problems.append(f"forbidden_particle_types={forbidden_particle_types}")
    if not w_rows:
        problems.append("missing_w_or_collimator_rows_for_fix5_audit")

    summary = {
        "status": "PASS_FIX5_GROUNDSTATE_HALF_LIFE_AUDIT" if not problems else "FAIL_FIX5_GROUNDSTATE_HALF_LIFE_AUDIT",
        "claim_level": "FIX5_DELAYED_SOURCE_NORMALIZATION_AUDIT_NOT_RATE_AUTHORITY",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "label": LABEL,
        "inputs": {
            "corrections_csv": rel(CORRECTIONS),
            "source_fix_summary": rel(FIX_SUMMARY),
            "fixed_source": rel(FIXED_SOURCE),
            "normalization_audit": rel(NORMALIZATION_AUDIT),
            "nubase_archive": rel(NUBASE),
            "nubase_archive_sha256": sha256_file(NUBASE),
        },
        "checks": {
            "corrections_rows": len(corrections),
            "nubase_archive_lines": len(nubase_lines),
            "nubase_line_mismatches": len(line_mismatches),
            "unit_self_test_max_rel_error": max(float(row["rel_error"]) for row in self_tests),
            "raw_unit_counts": dict(sorted(unit_counts.items())),
            "normalization_status": norm.get("status"),
            "normalization_problems": norm.get("problems"),
            "normalization_rows": len(norm_rows),
            "fixed_source_geometry": geom,
            "fixed_source_forbidden_particle_types": forbidden_particle_types,
            "old_total_activity_Bq": fix.get("old_total_activity_Bq"),
            "new_total_activity_Bq": fix.get("new_total_activity_Bq"),
            "source_blocks_in": fix.get("source_blocks_in"),
            "source_blocks_removed": fix.get("source_blocks_removed"),
            "w_or_collimator_rows": len(w_rows),
            "w_or_collimator_new_activity_Bq": w_activity,
        },
        "w_or_collimator_rows": w_rows,
        "problems": problems,
        "outputs": {
            "summary_json": rel(OUT / "fix5_groundstate_half_life_audit_summary.json"),
            "line_checks_csv": rel(OUT / "fix5_groundstate_half_life_line_checks.csv"),
            "normalization_rows_csv": rel(OUT / "fix5_groundstate_normalization_rows.csv"),
            "report_md": rel(OUT / "fix5_groundstate_half_life_audit.md"),
        },
    }

    write_csv(
        OUT / "fix5_groundstate_half_life_line_checks.csv",
        line_checks,
        [
            "VN",
            "ZA",
            "nuclide",
            "action",
            "nubase_line",
            "csv_raw_value",
            "csv_raw_unit",
            "line_raw_value",
            "line_raw_unit",
            "reported_half_life_s",
            "line_expected_half_life_s",
            "line_rel_error",
            "status",
        ],
    )
    write_csv(
        OUT / "fix5_groundstate_normalization_rows.csv",
        norm_rows,
        [
            "tag",
            "files",
            "division",
            "rp_raw_total",
            "rp_scaled_total",
            "expected_scaled_total",
            "scaled_rel_error",
            "status",
        ],
    )
    (OUT / "fix5_groundstate_half_life_audit_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    md = [
        f"# {LABEL} Ground-State Half-Life Audit",
        "",
        f"Status: `{summary['status']}`.",
        "",
        f"- corrections rows: `{summary['checks']['corrections_rows']}`",
        f"- NUBASE line mismatches: `{summary['checks']['nubase_line_mismatches']}`",
        f"- unit self-test max rel. error: `{format_sci(summary['checks']['unit_self_test_max_rel_error'])}`",
        f"- normalization status: `{summary['checks']['normalization_status']}`",
        f"- fixed source activity: `{summary['checks']['new_total_activity_Bq']}` Bq",
        f"- W/collimator rows/activity: `{summary['checks']['w_or_collimator_rows']}` / `{summary['checks']['w_or_collimator_new_activity_Bq']}` Bq",
        f"- fixed source geometry: `{summary['checks']['fixed_source_geometry']}`",
        "",
        "Problems:",
    ]
    md.extend(f"- {problem}" for problem in problems)
    if not problems:
        md.append("- none")
    md.append("")
    (OUT / "fix5_groundstate_half_life_audit.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps({"status": summary["status"], "problems": problems}, indent=2, ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
