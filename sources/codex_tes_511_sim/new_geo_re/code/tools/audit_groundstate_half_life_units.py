#!/usr/bin/env python3
"""Audit ground-state half-life unit handling for the fixed delayed source."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CORRECTIONS_CSV = ROOT / "runs" / "step02_delay_fix_equiv2602_aligned" / "groundstate_activity_corrections.csv"
FIX_SUMMARY_JSON = ROOT / "runs" / "step02_delay_fix_equiv2602_aligned" / "source_fix_summary.json"
FIXED_SOURCE = ROOT / "runs" / "step02_delay_fix_equiv2602_aligned" / "activation_decay_day15_groundstate_fixed.source"
NUBASE_ARCHIVE = ROOT / "inputs" / "nubase" / "nubase_2020.txt"
OUT = ROOT / "outputs" / "reports" / "half_life_unit_audit"

YEAR_S = 31_557_600.0
UNIT_SECONDS = {
    "ps": 1.0e-12,
    "ns": 1.0e-9,
    "us": 1.0e-6,
    "ms": 1.0e-3,
    "s": 1.0,
    "m": 60.0,
    "h": 3600.0,
    "d": 86400.0,
    "y": YEAR_S,
    "ky": 1.0e3 * YEAR_S,
    "My": 1.0e6 * YEAR_S,
    "Gy": 1.0e9 * YEAR_S,
    "Ty": 1.0e12 * YEAR_S,
    "Py": 1.0e15 * YEAR_S,
    "Ey": 1.0e18 * YEAR_S,
    "Zy": 1.0e21 * YEAR_S,
    "Yy": 1.0e24 * YEAR_S,
}
LOWER_UNIT_SECONDS = {key.lower(): value for key, value in UNIT_SECONDS.items()}
PREFIX_YEAR_UNITS = {"ky", "My", "Gy", "Ty", "Py", "Ey", "Zy", "Yy"}
REQUIRED_SELF_TEST_UNITS = ("ky", "My", "Gy", "Ty", "Py", "Ey")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))


def parse_half_life_seconds(value: str, unit: str) -> float | None:
    value_txt = str(value).strip()
    if not value_txt:
        return None
    if "stbl" in value_txt.lower() or "stable" in value_txt.lower():
        return math.inf
    value_txt = re.sub(r"[#?><~*&]", "", value_txt).strip()
    if not value_txt:
        return None
    try:
        val = float(value_txt)
    except ValueError:
        return None
    unit_txt = str(unit).strip() or "s"
    unit_txt = unit_txt.replace("\u03bc", "u").replace("\u00b5", "u")
    if unit_txt in UNIT_SECONDS:
        return val * UNIT_SECONDS[unit_txt]
    lower = unit_txt.lower()
    if lower in LOWER_UNIT_SECONDS:
        return val * LOWER_UNIT_SECONDS[lower]
    return None


def rel_diff(a: float, b: float) -> float:
    return abs(a - b) / max(abs(b), 1.0e-300)


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def nubase_line_lookup(path: Path) -> dict[int, str]:
    if not path.exists():
        return {}
    return {idx: line for idx, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1)}


def nubase_half_life_fields(line: str) -> tuple[str, str]:
    if len(line) < 80:
        return "", ""
    return line[69:78].strip(), line[78:80].strip()


def fixed_source_particle_types(path: Path) -> set[str]:
    if not path.exists():
        return set()
    particle_types: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = re.match(r"^\S+\.ParticleType\s+(\d+)\s*$", line.strip())
        if match:
            particle_types.add(match.group(1))
    return particle_types


def format_sci(value: float | None) -> str:
    if value is None:
        return ""
    if math.isinf(value):
        return "inf"
    return f"{value:.12g}"


def markdown_table(rows: list[dict[str, Any]], fields: list[str]) -> str:
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    return "\n".join(lines)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    corrections = read_csv(CORRECTIONS_CSV) if CORRECTIONS_CSV.exists() else []
    fix_summary = load_json(FIX_SUMMARY_JSON, {})
    nubase_lines = nubase_line_lookup(NUBASE_ARCHIVE)
    source_particle_types = fixed_source_particle_types(FIXED_SOURCE)

    self_test_rows: list[dict[str, Any]] = []
    for unit in REQUIRED_SELF_TEST_UNITS:
        expected = UNIT_SECONDS[unit]
        parsed = parse_half_life_seconds("1", unit)
        err = math.inf if parsed is None else rel_diff(float(parsed), expected)
        self_test_rows.append(
            {
                "unit": unit,
                "expected_seconds": expected,
                "parsed_seconds": "" if parsed is None else parsed,
                "rel_error": err,
            }
        )

    prefix_rows: list[dict[str, Any]] = []
    line_mismatch_rows: list[dict[str, Any]] = []
    unit_counts = Counter(row.get("nubase_raw_unit", "") for row in corrections)

    for row in corrections:
        unit = row.get("nubase_raw_unit", "").strip()
        if unit not in PREFIX_YEAR_UNITS:
            continue
        raw_value = row.get("nubase_raw_value", "")
        expected = parse_half_life_seconds(raw_value, unit)
        try:
            reported = float(row.get("nubase_half_life_s", "nan"))
        except ValueError:
            reported = float("nan")
        err = math.inf if expected is None or not math.isfinite(reported) else rel_diff(reported, float(expected))

        line_no = int(float(row.get("nubase_line", "0") or 0))
        line = nubase_lines.get(line_no, "")
        line_value, line_unit = nubase_half_life_fields(line)
        line_expected = parse_half_life_seconds(line_value, line_unit) if line else None
        line_rel_error = (
            math.inf
            if line_expected is None or not math.isfinite(reported)
            else rel_diff(reported, float(line_expected))
        )
        line_matches = bool(line) and line_value == str(raw_value).strip() and line_unit == unit and line_rel_error <= 1.0e-12
        if not line_matches:
            line_mismatch_rows.append(
                {
                    "nuclide": row.get("nuclide", ""),
                    "ZA": row.get("ZA", ""),
                    "nubase_line": line_no,
                    "csv_raw_value": raw_value,
                    "csv_raw_unit": unit,
                    "line_raw_value": line_value,
                    "line_raw_unit": line_unit,
                    "line_rel_error": line_rel_error,
                }
            )

        prefix_rows.append(
            {
                "VN": row.get("VN", ""),
                "ZA": row.get("ZA", ""),
                "nuclide": row.get("nuclide", ""),
                "action": row.get("action", ""),
                "raw_value": raw_value,
                "raw_unit": unit,
                "expected_half_life_s": "" if expected is None else expected,
                "reported_half_life_s": reported,
                "rel_error": err,
                "old_source_activity_Bq": row.get("old_source_activity_Bq", ""),
                "new_groundstate_activity_Bq": row.get("new_groundstate_activity_Bq", ""),
                "nubase_line": line_no,
                "line_value": line_value,
                "line_unit": line_unit,
                "line_rel_error": line_rel_error,
            }
        )

    max_prefix_rel = max((float(row["rel_error"]) for row in prefix_rows), default=math.inf)
    max_line_rel = max((float(row["line_rel_error"]) for row in prefix_rows), default=math.inf)
    max_self_test_rel = max((float(row["rel_error"]) for row in self_test_rows), default=math.inf)

    w180_rows = [row for row in corrections if row.get("ZA") == "74180" or row.get("nuclide") == "W-180"]
    w183_rows = [row for row in corrections if row.get("ZA") == "74183" or row.get("nuclide") == "W-183"]
    w180_new_total = sum(float(row.get("new_groundstate_activity_Bq") or 0.0) for row in w180_rows)
    w180_old_total = sum(float(row.get("old_source_activity_Bq") or 0.0) for row in w180_rows)
    w180_removed = bool(w180_rows) and all(row.get("action") == "removed_negligible_or_stable" for row in w180_rows)
    forbidden_particle_types = sorted(source_particle_types.intersection({"74180", "74183"}))

    summary = {
        "status": "PASS",
        "claim_level": "L1_HALF_LIFE_PREFIX_UNIT_AUDIT",
        "inputs": {
            "corrections_csv": rel(CORRECTIONS_CSV),
            "fixed_source": rel(FIXED_SOURCE),
            "source_fix_summary": rel(FIX_SUMMARY_JSON),
            "nubase_archive": rel(NUBASE_ARCHIVE),
            "nubase_archive_sha256": sha256_file(NUBASE_ARCHIVE),
            "nubase_archive_lines": len(nubase_lines),
        },
        "checks": {
            "corrections_rows": len(corrections),
            "prefix_year_rows": len(prefix_rows),
            "prefix_year_units_seen": sorted({row["raw_unit"] for row in prefix_rows}),
            "all_raw_unit_counts": dict(sorted(unit_counts.items())),
            "unit_self_test_units": list(REQUIRED_SELF_TEST_UNITS),
            "unit_self_test_max_rel_error": max_self_test_rel,
            "prefix_unit_max_rel_error": max_prefix_rel,
            "prefix_nubase_line_max_rel_error": max_line_rel,
            "prefix_nubase_line_mismatches": len(line_mismatch_rows),
            "w180_rows": len(w180_rows),
            "w180_old_total_activity_Bq": w180_old_total,
            "w180_new_total_activity_Bq": w180_new_total,
            "w180_removed_negligible": w180_removed,
            "w183_rows": len(w183_rows),
            "fixed_source_forbidden_particle_types": forbidden_particle_types,
            "fixed_source_blocks_removed": fix_summary.get("source_blocks_removed"),
            "fixed_source_total_activity_Bq": fix_summary.get("new_total_activity_Bq"),
        },
        "outputs": {
            "prefix_year_unit_rows_csv": rel(OUT / "prefix_year_unit_rows.csv"),
            "unit_self_tests_csv": rel(OUT / "unit_self_tests.csv"),
            "line_mismatches_csv": rel(OUT / "line_mismatches.csv"),
        },
    }

    ok = (
        CORRECTIONS_CSV.exists()
        and FIXED_SOURCE.exists()
        and NUBASE_ARCHIVE.exists()
        and len(corrections) > 0
        and len(prefix_rows) > 0
        and max_self_test_rel <= 1.0e-15
        and max_prefix_rel <= 1.0e-12
        and max_line_rel <= 1.0e-12
        and not line_mismatch_rows
        and len(nubase_lines) > 1000
        and w180_removed
        and 0.0 < w180_new_total < 1.0e-15
        and not forbidden_particle_types
    )
    summary["status"] = "PASS" if ok else "FAIL"

    write_csv(
        OUT / "prefix_year_unit_rows.csv",
        prefix_rows,
        [
            "VN",
            "ZA",
            "nuclide",
            "action",
            "raw_value",
            "raw_unit",
            "expected_half_life_s",
            "reported_half_life_s",
            "rel_error",
            "old_source_activity_Bq",
            "new_groundstate_activity_Bq",
            "nubase_line",
            "line_value",
            "line_unit",
            "line_rel_error",
        ],
    )
    write_csv(OUT / "unit_self_tests.csv", self_test_rows, ["unit", "expected_seconds", "parsed_seconds", "rel_error"])
    write_csv(
        OUT / "line_mismatches.csv",
        line_mismatch_rows,
        [
            "nuclide",
            "ZA",
            "nubase_line",
            "csv_raw_value",
            "csv_raw_unit",
            "line_raw_value",
            "line_raw_unit",
            "line_rel_error",
        ],
    )
    (OUT / "half_life_unit_audit_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    checks = summary["checks"]
    overview_rows = [
        {"metric": "status", "value": summary["status"]},
        {"metric": "claim_level", "value": summary["claim_level"]},
        {"metric": "NUBASE archive", "value": summary["inputs"]["nubase_archive"]},
        {"metric": "NUBASE SHA256", "value": summary["inputs"]["nubase_archive_sha256"]},
        {"metric": "prefix-year rows", "value": checks["prefix_year_rows"]},
        {"metric": "prefix-year units seen", "value": ", ".join(checks["prefix_year_units_seen"])},
        {"metric": "max prefix-unit rel. error", "value": format_sci(checks["prefix_unit_max_rel_error"])},
        {"metric": "max NUBASE-line rel. error", "value": format_sci(checks["prefix_nubase_line_max_rel_error"])},
        {"metric": "W-180 old -> new Bq", "value": f"{format_sci(w180_old_total)} -> {format_sci(w180_new_total)}"},
        {"metric": "fixed source forbidden ZA", "value": ", ".join(forbidden_particle_types) or "none"},
    ]
    sample_rows = [
        {
            "nuclide": row["nuclide"],
            "raw": f"{row['raw_value']} {row['raw_unit']}",
            "reported_s": format_sci(row["reported_half_life_s"]),
            "rel_error": format_sci(row["rel_error"]),
            "action": row["action"],
        }
        for row in prefix_rows[:10]
    ]
    md = [
        "# Half-Life Unit Audit",
        "",
        "This report verifies the ground-state half-life correction evidence used by the fixed delayed source.",
        "",
        markdown_table(overview_rows, ["metric", "value"]),
        "",
        "## Prefix-Year Samples",
        "",
        markdown_table(sample_rows, ["nuclide", "raw", "reported_s", "rel_error", "action"]),
        "",
        "## Outputs",
        "",
        f"- `{rel(OUT / 'prefix_year_unit_rows.csv')}`",
        f"- `{rel(OUT / 'unit_self_tests.csv')}`",
        f"- `{rel(OUT / 'line_mismatches.csv')}`",
        "",
    ]
    (OUT / "half_life_unit_audit.md").write_text("\n".join(md), encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
