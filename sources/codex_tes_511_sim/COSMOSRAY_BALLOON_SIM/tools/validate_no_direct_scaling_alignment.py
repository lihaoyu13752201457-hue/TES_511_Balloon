#!/usr/bin/env python3
"""Validate the no-direct-scaling optics-alignment diagnostic package."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "reports2.0" / "12_FINAL_COMPACT_SOURCE_ANALYSIS" / "no_direct_scaling_optics_alignment"


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    return ap.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def add(rows: list[dict[str, Any]], check: str, status: str, details: str) -> None:
    rows.append({"check": check, "status": status, "details": details})


def bool_field(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def scan_forbidden_scaling(root: Path) -> list[str]:
    bad_tokens = [
        "spot_scale_factor",
        "Aeff_target_factor",
        "aeff_target_factor",
        "Aeff_final = Aeff_L2 *",
        "Aeff_L2 * 6.7",
        "35 / 11",
        "50.89 / 7.58",
    ]
    hits: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".md", ".csv", ".json", ".yaml", ".yml"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in bad_tokens:
            if token in text:
                hits.append(f"{path.relative_to(root)}:{token}")
    return hits


def validate(root: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    required = [
        "README.md",
        "tables/spot_metric_definitions.csv",
        "tables/cam511_comparison_metric_map.csv",
        "tables/fov_footprint_summary.csv",
        "tables/ringwise_focus_diagnostics.csv",
        "tables/geometry_sanity_variants.csv",
        "tables/aeff_transport_debug.csv",
        "notes/claim_control_no_direct_scaling.md",
        "notes/cam511_definition_audit.md",
        "notes/aeff_debug_notes.md",
        "figures/onaxis_core_vs_full_fov_footprint.png",
        "figures/ringwise_centroid_map.png",
        "figures/aeff_by_ring_and_bounce.png",
    ]
    missing = [name for name in required if not (root / name).exists()]
    add(
        results,
        "required_outputs_present",
        "PASS" if not missing else "FAIL",
        "all no-direct-scaling outputs present" if not missing else "missing: " + ", ".join(missing),
    )

    if (root / "tables/cam511_comparison_metric_map.csv").exists():
        rows = read_csv(root / "tables/cam511_comparison_metric_map.csv")
        direct_bad = [
            row for row in rows
            if row.get("current_metric") == "intrinsic_onaxis_core_D95"
            and row.get("comparison_role") not in {"not_preferred", "diagnostic_only"}
        ]
        tuned = [row for row in rows if bool_field(row.get("used_for_tuning"))]
        add(
            results,
            "cam511_spot_not_misused_as_onaxis_r95",
            "PASS" if not direct_bad and not tuned else "FAIL",
            f"bad_direct_rows={len(direct_bad)} tuned_rows={len(tuned)}",
        )

    if (root / "tables/spot_metric_definitions.csv").exists():
        rows = read_csv(root / "tables/spot_metric_definitions.csv")
        ids = {row["metric_id"] for row in rows}
        needed = {"intrinsic_onaxis_core_D95", "expected_full_fov_envelope_D95", "reported_cam511_focused_beam_diameter"}
        add(
            results,
            "intrinsic_and_fov_metrics_separated",
            "PASS" if needed.issubset(ids) else "FAIL",
            f"metrics={sorted(ids)}",
        )

    if (root / "tables/fov_footprint_summary.csv").exists():
        rows = read_csv(root / "tables/fov_footprint_summary.csv")
        values = {row["metric_id"]: float(row["value"]) for row in rows}
        ok = (
            values.get("expected_geometric_full_fov_envelope_D95_mm", 0.0)
            > values.get("intrinsic_onaxis_core_D95_mm", 1.0)
            and values.get("fov_radius_focal_plane_mm", 0.0) > 0.0
        )
        add(
            results,
            "full_fov_footprint_larger_than_intrinsic_core",
            "PASS" if ok else "FAIL",
            json.dumps(values, sort_keys=True),
        )

    if (root / "tables/aeff_transport_debug.csv").exists():
        rows = read_csv(root / "tables/aeff_transport_debug.csv")
        total = next((row for row in rows if row["ring_id"] == "TOTAL"), None)
        ok = total is not None and float(total["Aeff_cm2"]) > 0.0 and float(total["open_geometric_area_cm2"]) > float(total["Aeff_cm2"])
        add(
            results,
            "aeff_debug_physical_decomposition_present",
            "PASS" if ok else "FAIL",
            f"total={total}",
        )

    scaling_hits = scan_forbidden_scaling(root)
    add(
        results,
        "no_direct_scaling_tokens",
        "PASS" if not scaling_hits else "FAIL",
        "no direct scaling tokens found" if not scaling_hits else "hits: " + "; ".join(scaling_hits[:8]),
    )

    return results


def main() -> int:
    args = parse_args()
    root = Path(args.root)
    if not root.is_absolute():
        root = ROOT / root
    results = validate(root)
    write_csv(root / "validation_no_direct_scaling_alignment.csv", results)
    (root / "validation_no_direct_scaling_alignment.json").write_text(
        json.dumps({"results": results}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    for row in results:
        print(f"{row['status']:5} {row['check']}: {row['details']}")
    return 1 if any(row["status"] == "FAIL" for row in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
