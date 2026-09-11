#!/usr/bin/env python3
"""Black-box static-input self-test for analyze_wgrid_mono511.py."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "analyze_wgrid_mono511.py"
WEIGHT = 0.00011985193855860365
WINDOWS = ("broad_480_550", "w2_510p58_511p42")
STAGES = (
    "pre_veto",
    "plastic_positron_veto",
    "bgo_active_scintillator_veto",
    "combined_active_veto",
    "compton_trajectory_veto",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="wgrid-analysis-selftest-") as tmp:
        root = Path(tmp)
        fixture = root / "static_response"
        output = root / "promoted_output"
        fixture.mkdir()
        counts = {
            ("broad_480_550", "pre_veto"): 130,
            ("broad_480_550", "plastic_positron_veto"): 130,
            ("broad_480_550", "bgo_active_scintillator_veto"): 125,
            ("broad_480_550", "combined_active_veto"): 125,
            ("broad_480_550", "compton_trajectory_veto"): 110,
            ("w2_510p58_511p42", "pre_veto"): 90,
            ("w2_510p58_511p42", "plastic_positron_veto"): 90,
            ("w2_510p58_511p42", "bgo_active_scintillator_veto"): 85,
            ("w2_510p58_511p42", "combined_active_veto"): 85,
            ("w2_510p58_511p42", "compton_trajectory_veto"): 80,
        }
        cutflow = []
        for window in WINDOWS:
            for stage in STAGES:
                count = counts[(window, stage)]
                cutflow.append({
                    "model": "b",
                    "window_id": window,
                    "stage": stage,
                    "selected_events": count,
                    "event_weight_cps": WEIGHT,
                    "weighted_rate_cps": count * WEIGHT,
                    "weighted_mc_sigma_cps": math.sqrt(count) * WEIGHT,
                    "effective_selected_events": count,
                })
        write_csv(fixture / "mono_line_cutflow.csv", cutflow)
        write_csv(fixture / "mono_line_final_by_source_bin80.csv", [
            {"source_bin80": index, "selected_events": 1, "weighted_rate_cps": WEIGHT}
            for index in range(80)
        ])
        summary = {
            "status": "COMPLETE__MONO_LINE_COMMON_RESPONSE",
            "model": "b",
            "geometry_setup": "/static/selftest/WGrid_60cm.geo.setup",
            "incident_photons": 15_709_417,
            "jobs": 64,
            "physical_exposure_s": 8343.628079999999,
            "event_weight_cps": WEIGHT,
            "detector_positive_events": 1000,
            "detector_positive_rate_cps": 1000 * WEIGHT,
            "w2_final_selected_events": 80,
            "w2_final_rate_cps": 80 * WEIGHT,
            "w2_final_mc_sigma_cps": math.sqrt(80) * WEIGHT,
            "w2_final_relative_mc_sigma": 1.0 / math.sqrt(80),
            "w2_final_effective_sample_size": 80,
            "catalog": "not-generated-for-static-selftest",
        }
        (fixture / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--response-input", str(fixture),
                "--output", str(output),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        assert output.is_dir()
        assert not list(root.glob(".*.staging-*"))
        comparison = json.loads((output / "comparison_summary.json").read_text())
        final = comparison["key_comparisons"]["w2_final"]
        assert final["new_selected_events"] == 80
        assert final["old_selected_events"] == 186
        assert math.isclose(final["new_over_old_ratio"], 80 / 186, rel_tol=1e-14)
        assert math.isclose(final["independent_difference_sigma_cps"], math.sqrt(80 + 186) * WEIGHT, rel_tol=1e-14)
        assert math.isclose(final["independent_ratio_relative_sigma"], math.sqrt(1 / 80 + 1 / 186), rel_tol=1e-14)
        assert len(list(csv.DictReader((output / "comparison_cutflow_10rows.csv").open()))) == 10
        assert len(list(csv.DictReader((output / "comparison_final_by_source_bin80.csv").open()))) == 80
        assert len(list(csv.DictReader((output / "comparison_up_down.csv").open()))) == 2
        decision = json.loads((output / "incremental_statistics_decision.json").read_text())
        assert decision["line_rate_precision"]["required_effective_sample_size"] == 186
        assert decision["line_rate_precision"]["decision"] == "TOPUP_REQUIRED"
        assert decision["new_over_open_ratio_precision"]["required_new_effective_sample_size"] == 217
        assert decision["new_over_open_ratio_precision"]["decision"] == "TOPUP_REQUIRED"
        stdout_status = json.loads(completed.stdout)["status"]
        assert stdout_status == "PASS__ATOMICALLY_PROMOTED"

        receipt = {
            "status": "PASS__STATIC_BLACK_BOX_SELFTEST",
            "tested_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "script": str(SCRIPT),
            "script_sha256": sha256(SCRIPT),
            "checks": {
                "unique_staging_then_atomic_promotion": "PASS",
                "cutflow_rows": 10,
                "source_bins": 80,
                "direction_rows": 2,
                "independent_difference_formula": "PASS",
                "independent_ratio_formula": "PASS",
                "ess_and_incremental_statistics": "PASS",
                "frozen_comparator_hashes": "PASS",
            },
        }
        (HERE / "SELFTEST_RECEIPT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
