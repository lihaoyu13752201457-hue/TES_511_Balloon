#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_calibrated(summary: dict) -> list[str]:
    errors: list[str] = []
    expected = {
        "schema_version": "channel_optics_summary_v2",
        "model_class": "calibrated_detector_handoff",
        "is_calibrated_handoff": True,
        "is_public_wallbywall_geometry": False,
        "is_first_principles_80pct_closure": False,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            errors.append(f"{key} expected {value!r}, got {summary.get(key)!r}")
    return errors


def check_wallbywall(summary: dict) -> list[str]:
    errors: list[str] = []
    expected = {
        "schema_version": "channel_optics_summary_v2",
        "model_class": "public_geometry_wallbywall_reconstruction",
        "is_calibrated_handoff": False,
        "is_public_wallbywall_geometry": True,
        "is_first_principles_80pct_closure": False,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            errors.append(f"{key} expected {value!r}, got {summary.get(key)!r}")
    if summary.get("transmissivity") == summary.get("target_transmissivity"):
        errors.append("public wall-by-wall summary should not mirror a calibration target transmissivity")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate calibrated handoff and public wall-by-wall schema separation.")
    parser.add_argument("--calibrated", required=True, help="Calibrated/channel handoff summary.json")
    parser.add_argument("--wallbywall", action="append", required=True, help="Public wall-by-wall summary.json; repeatable")
    parser.add_argument("--out", default="records/2026-05-24_optics_evidence_gap_closure/schema/channel_schema_separation.md")
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    calibrated_path = Path(args.calibrated)
    calibrated = read_json(calibrated_path)
    calibrated_errors = check_calibrated(calibrated)
    wall_results = []
    for path_text in args.wallbywall:
        path = Path(path_text)
        summary = read_json(path)
        errors = check_wallbywall(summary)
        wall_results.append({"path": path, "summary": summary, "errors": errors})

    overall = not calibrated_errors and all(not item["errors"] for item in wall_results)
    json_path = out_path.with_suffix(".json")
    json_path.write_text(
        json.dumps(
            {
                "overall": overall,
                "calibrated": {"path": str(calibrated_path), "errors": calibrated_errors},
                "wallbywall": [{"path": str(item["path"]), "errors": item["errors"]} for item in wall_results],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Channel schema separation validation",
        "",
        f"- calibrated_summary: `{calibrated_path}`",
        f"- wallbywall_summaries: `{[str(item['path']) for item in wall_results]}`",
        f"- summary_json: `{json_path}`",
        f"- overall_status: **{'PASS' if overall else 'FAIL'}**",
        "",
        "## Calibrated Handoff",
        "",
        "| field | value |",
        "|---|---|",
        f"| model_class | `{calibrated.get('model_class')}` |",
        f"| is_calibrated_handoff | `{calibrated.get('is_calibrated_handoff')}` |",
        f"| is_public_wallbywall_geometry | `{calibrated.get('is_public_wallbywall_geometry')}` |",
        f"| is_first_principles_80pct_closure | `{calibrated.get('is_first_principles_80pct_closure')}` |",
        f"| transmissivity | `{calibrated.get('transmissivity')}` |",
        f"| errors | `{calibrated_errors}` |",
        "",
        "## Public Wall-By-Wall",
        "",
        "| path | model_class | calibrated | public_wallbywall | first_principles_80pct | transmissivity | errors |",
        "|---|---|---|---|---|---:|---|",
    ]
    for item in wall_results:
        summary = item["summary"]
        lines.append(
            f"| `{item['path']}` | `{summary.get('model_class')}` | `{summary.get('is_calibrated_handoff')}` | "
            f"`{summary.get('is_public_wallbywall_geometry')}` | `{summary.get('is_first_principles_80pct_closure')}` | "
            f"{summary.get('transmissivity')} | `{item['errors']}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The calibrated handoff schema is explicitly separate from public wall-by-wall reconstruction schema.",
            "- Both schemas set `is_first_principles_80pct_closure=false`.",
            "- This check does not tune or compare public wall-by-wall transmission to 0.80; it only prevents semantic mixing.",
            "",
        ]
    )
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
