#!/usr/bin/env python3
"""Audit Mass_model_511 activation materials from retained exact-position data.

This is a read-only analysis of the retained all-family weighted RPIP table.  It
does not run particle transport or alter any retained simulation product.
"""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parents[1]
DATA = WORK / "data"

WEIGHTED_TABLE = (
    ROOT
    / "runs/Mass_model_511_nearfield_migration_20260701/"
    "step02_delay_exactpos_candidate_Mass_model_511_fullstat_v1/"
    "exactpos_weighted_rpip_table.csv"
)
SOURCE_SUMMARY = (
    ROOT
    / "engineering/Mass_model_511_nearfield_migration_20260701/"
    "03_detector_transport/delayed/candidate_Mass_model_511/fullstat_v1/F1/"
    "delayed_source_exactpos_summary.json"
)
REFERENCE_CATEGORY_TABLE = (
    ROOT
    / "engineering/geometry_optimization_20260704/"
    "05_neutron_plastic_audit_20260707/"
    "activation_category_comparison_groundstate_fixed.csv"
)

OUT_JSON = DATA / "mass_activation_material_family_audit.json"
OUT_CATEGORY = DATA / "mass_activation_material_categories.csv"
OUT_FAMILY = DATA / "mass_activation_incident_families.csv"
OUT_DTV = DATA / "mass_activation_family_material_dtv.csv"


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def volume_category(name: str) -> str:
    upper = name.upper()
    if upper.startswith("CSI_"):
        return "csi"
    if upper.startswith("TP_") or upper.startswith("TES_"):
        return "tes"
    if "WINDOW" in upper:
        return "window"
    if "COLDPLATE" in upper:
        return "cold_plates"
    if "VACUUM_JACKET" in upper or "OUTER_" in upper or "OUTERSUPPORT" in upper:
        return "outer_mechanics"
    if "W_" in upper or "TUNGSTEN" in upper or name.startswith("Passive_W"):
        return "passive_w_or_collimator"
    if "COLL" in upper or "XS400" in upper:
        return "passive_w_or_collimator"
    return "other_internal"


def incident_family(source_sim: str) -> str:
    marker = "Background_"
    if marker not in source_sim or "_fullsphere" not in source_sim:
        raise ValueError(f"cannot identify incident family from {source_sim!r}")
    return source_sim.split(marker, 1)[1].split("_fullsphere", 1)[0]


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    required = [WEIGHTED_TABLE, SOURCE_SUMMARY, REFERENCE_CATEGORY_TABLE]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit("missing retained authority: " + "; ".join(missing))

    by_category: dict[str, float] = defaultdict(float)
    by_family: dict[str, float] = defaultdict(float)
    by_family_category: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    rows_seen = 0
    with WEIGHTED_TABLE.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            weight = float(row["sample_weight"])
            family = incident_family(row["source_sim"])
            category = volume_category(row["VN"])
            rows_seen += 1
            by_category[category] += weight
            by_family[family] += weight
            by_family_category[family][category] += weight

    total = math.fsum(by_category.values())
    source_summary = json.loads(SOURCE_SUMMARY.read_text(encoding="utf-8"))
    expected_total = float(source_summary["fixed_total_activity_Bq"])

    category_rows = [
        {
            "category": category,
            "activity_Bq": value,
            "fraction": value / total,
            "percent": 100.0 * value / total,
        }
        for category, value in sorted(by_category.items(), key=lambda item: item[1], reverse=True)
    ]
    family_rows = [
        {
            "incident_family": family,
            "activity_Bq": value,
            "fraction": value / total,
            "percent": 100.0 * value / total,
        }
        for family, value in sorted(by_family.items(), key=lambda item: item[1], reverse=True)
    ]

    categories = sorted(by_category)
    active_families = [family for family, value in by_family.items() if value > 0.0]
    dtv_rows: list[dict[str, object]] = []
    for index, family_a in enumerate(sorted(active_families)):
        total_a = by_family[family_a]
        for family_b in sorted(active_families)[index + 1 :]:
            total_b = by_family[family_b]
            dtv = 0.5 * sum(
                abs(
                    by_family_category[family_a].get(category, 0.0) / total_a
                    - by_family_category[family_b].get(category, 0.0) / total_b
                )
                for category in categories
            )
            dtv_rows.append(
                {
                    "family_a": family_a,
                    "family_b": family_b,
                    "total_variation_distance": dtv,
                }
            )
    dtv_rows.sort(key=lambda row: float(row["total_variation_distance"]), reverse=True)

    reference_categories: dict[str, float] = {}
    with REFERENCE_CATEGORY_TABLE.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            metric = row["metric"]
            if metric.startswith("category:"):
                reference_categories[metric.split(":", 1)[1]] = float(row["mass_model_Bq"])

    problems: list[str] = []
    if rows_seen != int(source_summary["eligible_rpip_rows"]):
        problems.append(
            f"weighted-row count {rows_seen} != retained eligible rows "
            f"{source_summary['eligible_rpip_rows']}"
        )
    if not math.isclose(total, expected_total, rel_tol=0.0, abs_tol=1e-6):
        problems.append(f"activity total {total:.12g} != retained total {expected_total:.12g}")
    for category, expected in reference_categories.items():
        observed = by_category.get(category, 0.0)
        if not math.isclose(observed, expected, rel_tol=0.0, abs_tol=1e-6):
            problems.append(
                f"category {category}: weighted table {observed:.12g} != corrected inventory {expected:.12g}"
            )

    payload = {
        "status": "PASS_MASS_ACTIVATION_MATERIAL_FAMILY_AUDIT" if not problems else "FAIL_MASS_ACTIVATION_MATERIAL_FAMILY_AUDIT",
        "scope": (
            "Retained Mass_model_511 all-family day-15 activation only. "
            "This analysis does not extend the final S3d neutron-induced delayed transport."
        ),
        "inputs": {
            "weighted_exact_position_table": rel(WEIGHTED_TABLE),
            "delayed_source_summary": rel(SOURCE_SUMMARY),
            "reference_category_crosscheck": rel(REFERENCE_CATEGORY_TABLE),
        },
        "checks": {
            "weighted_rows": rows_seen,
            "total_activity_Bq": total,
            "retained_total_activity_Bq": expected_total,
            "absolute_activity_delta_Bq": abs(total - expected_total),
            "category_crosscheck_count": len(reference_categories),
        },
        "incident_families": family_rows,
        "material_categories": category_rows,
        "pairwise_material_total_variation": dtv_rows,
        "problems": problems,
    }

    DATA.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_csv(
        OUT_CATEGORY,
        category_rows,
        ["category", "activity_Bq", "fraction", "percent"],
    )
    write_csv(
        OUT_FAMILY,
        family_rows,
        ["incident_family", "activity_Bq", "fraction", "percent"],
    )
    write_csv(
        OUT_DTV,
        dtv_rows,
        ["family_a", "family_b", "total_variation_distance"],
    )
    print(json.dumps({
        "status": payload["status"],
        "weighted_rows": rows_seen,
        "total_activity_Bq": total,
        "top_families": family_rows[:4],
        "top_categories": category_rows[:5],
        "largest_dtv": dtv_rows[:5],
        "problems": problems,
    }, indent=2, ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
