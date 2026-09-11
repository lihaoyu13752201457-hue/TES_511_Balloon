from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from external_baseline.io_contract_py.io_contract import validate_run_contract, write_validation_report
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from external_baseline.io_contract_py.io_contract import validate_run_contract, write_validation_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate staged optics/detector CSV interface contracts.")
    parser.add_argument("--phase-space", default="runs/channel_4ring_calibrated_v2/phase_space.csv")
    parser.add_argument("--optics-history", default="runs/channel_4ring_calibrated_v2/optics_history.csv")
    parser.add_argument("--hits", default="runs/detector_only_4ring_calibrated_v2/hits.csv")
    parser.add_argument("--event-summary", default="runs/detector_only_4ring_calibrated_v2/event_summary.csv")
    parser.add_argument("--out", default="runs/io_contract_validation")
    args = parser.parse_args()

    def optional_path(value: str):
        return None if value.strip().lower() in {"", "none", "null", "-"} else value

    report = validate_run_contract(
        phase_space=optional_path(args.phase_space),
        optics_history=optional_path(args.optics_history),
        hits=optional_path(args.hits),
        event_summary=optional_path(args.event_summary),
    )
    out = Path(args.out)
    write_validation_report(report, out / "summary.json", out / "validation_report.md")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
