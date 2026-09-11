#!/usr/bin/env python3
"""Independent closure checks for the M05NEW SG3B/OptV3 comparison package."""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

ROOT = Path("/home/ubuntu/TES_511_Balloon")
PACKAGE = ROOT / "engineering/geometry_optimization_20260815/63_m05new_sg3b_signal_statistics_20260820"
M05NEW = ROOT / "core_md/balloon511_ea_latex_drafts/M05NEW"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    signal = load(PACKAGE / "outputs/01_signal/summary.json")
    catalog = load(PACKAGE / "outputs/03_expanded_catalog/summary.json")
    timeline = load(PACKAGE / "outputs/04_candidate_timeline/summary.json")
    origins = load(PACKAGE / "outputs/05_optv3_delayed_origins/summary.json")
    comparison = load(M05NEW / "SG3B_OPTV3_COMPARISON.json")
    with (M05NEW / "M05_PAPER_DATA_TABLE.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    final = timeline["mission_final_20day"]
    stats = timeline["statistical_uncertainty"]
    checks = {
        "signal_status_pass": signal["status"] == "PASS",
        "signal_event_count_37194": int(signal["events"]) == 37_194,
        "signal_geometry_is_sg3b": str(signal["geometry"]).endswith("DEMO2_DR_v3p5_SG3B.geo.setup"),
        "signal_aeff_positive": float(signal["effective_area"]["w2_510p58_511p42"]["compton_trajectory_veto"]["Aeff_cm2"]) > 0,
        "publication_precision_rule_met": bool(catalog["publication_precision_rule_met"]),
        "sparse_gamma_uncertainty_explicit": (
            int(catalog["combined_gamma_W2_final_raw_survivors"]) > 0
            and float(catalog["combined_gamma_W2_final_rate_sigma_cps"]) > 0
            and math.isclose(
                float(catalog["combined_gamma_W2_final_relative_sigma"]),
                1.0 / math.sqrt(int(catalog["combined_gamma_W2_final_raw_survivors"])),
                rel_tol=1e-12,
            )
        ),
        "expanded_background_precision_better_than_20pct": float(catalog["direct_final_day15"]["relative_sigma"]) < 0.20,
        "timeline_status_pass": str(timeline["status"]).startswith("PASS__M05NEW_SG3B"),
        "timeline_20day_background_positive": float(final["cumulative_background_counts"]) > 0,
        "timeline_20day_kernel_positive": float(final["cumulative_signal_counts_per_unit_flux"]) > 0,
        "timeline_fmin_error_positive": float(stats["Fmin_3sigma_gaussian_standard_error_ph_cm2_s"]) > 0,
        "timeline_fmin_relative_error_below_10pct": float(stats["Fmin_3sigma_gaussian_relative_standard_error"]) < 0.10,
        "optv3_origin_status_pass": str(origins["status"]).startswith("PASS"),
        "optv3_origin_selected_111": int(origins["selected_events"]) == 111,
        "optv3_origin_rate_closure": math.isclose(float(origins["delayed_W2_final_day15_rate_cps"]), 0.003624666352, rel_tol=0, abs_tol=5e-13),
        # The original closure had 98 rows.  Later paper-ready figures or bounded
        # engineering decisions may append READY rows without invalidating it.
        "table_at_least_98_unique_rows": len(rows) >= 98 and len({row["ID"] for row in rows}) == len(rows),
        "table_has_sg3b_column": bool(rows) and "SG3B基线值" in rows[0],
        "table_sg3b_cells_complete": bool(rows) and all(row.get("SG3B基线值", "").strip() for row in rows),
        "table_no_required_gap_status": all(row["状态"] != "MISSING_REQUIRED_IF_RETAINED" for row in rows),
        "comparison_status_pass": comparison["status"].startswith("PASS"),
        "optv3_fmin_better_than_sg3b": float(comparison["ratios_OptV3_over_SG3B"]["Fmin"]) < 1.0,
    }
    result = {
        "schema_version": 1,
        "status": "PASS__M05NEW_ALL_REQUIRED_DATA_CLOSED" if all(checks.values()) else "FAIL",
        "checks": checks,
        "passed": sum(checks.values()),
        "total": len(checks),
        "SG3B_Fmin_3sigma_gaussian": float(final["Fmin_3sigma_gaussian_ph_cm2_s"]),
        "SG3B_Fmin_standard_error": float(stats["Fmin_3sigma_gaussian_standard_error_ph_cm2_s"]),
        "OptV3_Fmin_3sigma_gaussian": float(comparison["OptV3"]["Fmin_3sigma_gaussian"]),
        "OptV3_Fmin_standard_error": float(comparison["OptV3"]["Fmin_3sigma_standard_error"]),
    }
    out = M05NEW / "M05NEW_VALIDATION.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)
    if result["status"] == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
