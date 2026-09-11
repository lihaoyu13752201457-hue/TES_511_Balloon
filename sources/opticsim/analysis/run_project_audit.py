from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


COMMANDS = [
    {
        "name": "python_unittest",
        "cmd": ["python3", "-m", "unittest", "discover", "-s", "tests"],
        "required": True,
    },
    {
        "name": "cmake_build",
        "cmd": ["cmake", "--build", "/tmp/opticsim-build"],
        "required": True,
    },
    {
        "name": "baseline_freeze",
        "cmd": ["python3", "analysis/freeze_baseline.py", "--out", "reports/baseline"],
        "required": True,
        "must_contain": "baseline_metrics.json",
    },
    {
        "name": "baseline_self_compare",
        "cmd": [
            "python3",
            "analysis/compare_to_baseline.py",
            "--baseline",
            "reports/baseline/baseline_metrics.json",
            "--current",
            "reports/baseline/baseline_metrics.json",
        ],
        "required": True,
        "must_contain": "\"ok\": true",
    },
    {
        "name": "two_wall_reflect",
        "cmd": ["timeout", "10s", "/tmp/opticsim-build/channel_two_wall_demo", "1", "1", "0", "0"],
        "required": True,
        "must_contain": "reflect=2 absorb=0 leak=0",
    },
    {
        "name": "two_wall_absorb",
        "cmd": ["timeout", "10s", "/tmp/opticsim-build/channel_two_wall_demo", "1", "0", "1", "0"],
        "required": True,
        "must_contain": "reflect=0 absorb=1 leak=0",
    },
    {
        "name": "two_wall_leak",
        "cmd": ["timeout", "10s", "/tmp/opticsim-build/channel_two_wall_demo", "1", "0", "0", "1"],
        "required": True,
        "must_contain": "reflect=0 absorb=0 leak=1",
    },
    {
        "name": "two_wall_table_reflect",
        "cmd": [
            "timeout",
            "10s",
            "/tmp/opticsim-build/channel_two_wall_table_demo",
            "--n",
            "3",
            "--R",
            "1",
            "--A",
            "0",
            "--T",
            "0",
            "--out",
            "runs/geant4_channel_two_wall_table_reflect_audit",
        ],
        "required": True,
        "must_contain": "reflect=6 absorb=0 leak=0",
    },
    {
        "name": "two_wall_table_absorb",
        "cmd": [
            "timeout",
            "10s",
            "/tmp/opticsim-build/channel_two_wall_table_demo",
            "--n",
            "3",
            "--R",
            "0",
            "--A",
            "1",
            "--T",
            "0",
            "--out",
            "runs/geant4_channel_two_wall_table_absorb_audit",
        ],
        "required": True,
        "must_contain": "reflect=0 absorb=3 leak=0",
    },
    {
        "name": "two_wall_table_leak",
        "cmd": [
            "timeout",
            "10s",
            "/tmp/opticsim-build/channel_two_wall_table_demo",
            "--n",
            "3",
            "--R",
            "0",
            "--A",
            "0",
            "--T",
            "1",
            "--out",
            "runs/geant4_channel_two_wall_table_leak_audit",
        ],
        "required": True,
        "must_contain": "reflect=0 absorb=0 leak=3",
    },
    {
        "name": "two_wall_table_wsi",
        "cmd": [
            "timeout",
            "10s",
            "/tmp/opticsim-build/channel_two_wall_table_demo",
            "--n",
            "1000",
            "--energy-keV",
            "511",
            "--theta-rad",
            "1.5e-4",
            "--reflectivity-table",
            "data/reflectivity/WSi_511keV_parratt_grid.csv",
            "--out",
            "runs/geant4_channel_two_wall_table",
            "--seed",
            "20260517",
        ],
        "required": True,
        "must_contain": "CHANNEL_TWO_WALL_TABLE_SUMMARY events=1000",
    },
    {
        "name": "single_curved_constant",
        "cmd": [
            "timeout",
            "10s",
            "/tmp/opticsim-build/channel_single_curved_demo",
            "--n",
            "20",
            "--R",
            "1",
            "--A",
            "0",
            "--T",
            "0",
            "--segments",
            "64",
            "--bend-angle-rad",
            "0.003833333333",
            "--out",
            "runs/geant4_channel_single_curved_bend12m_constant",
            "--seed",
            "20260517",
        ],
        "required": True,
        "must_contain": "CHANNEL_SINGLE_CURVED_SUMMARY events=20",
    },
    {
        "name": "single_curved_table",
        "cmd": [
            "timeout",
            "10s",
            "/tmp/opticsim-build/channel_single_curved_demo",
            "--n",
            "200",
            "--segments",
            "64",
            "--bend-angle-rad",
            "0.003833333333",
            "--reflectivity-table",
            "data/reflectivity/WSi_511keV_parratt_grid.csv",
            "--out",
            "runs/geant4_channel_single_curved_bend12m_table",
            "--seed",
            "20260517",
        ],
        "required": True,
        "must_contain": "CHANNEL_SINGLE_CURVED_SUMMARY events=200",
    },
    {
        "name": "single_curved_scan",
        "cmd": [
            "python3",
            "analysis/scan_single_curved_geometry.py",
            "--out",
            "runs/geant4_channel_single_curved_scan",
        ],
        "required": True,
        "must_contain": "geant4_channel_single_curved_scan",
    },
    {
        "name": "single_curved_gap_scan",
        "cmd": [
            "python3",
            "analysis/scan_single_curved_gap.py",
            "--out",
            "runs/geant4_channel_single_curved_gap_scan",
        ],
        "required": True,
        "must_contain": "geant4_channel_single_curved_gap_scan",
    },
    {
        "name": "channel_geometry_constraints",
        "cmd": [
            "python3",
            "analysis/estimate_channel_geometry_constraints.py",
            "--out",
            "runs/channel_geometry_constraints",
        ],
        "required": True,
        "must_contain": "channel_geometry_constraints",
    },
    {
        "name": "channel_bounce_path_reconciliation",
        "cmd": [
            "python3",
            "analysis/reconcile_channel_bounce_path.py",
            "--out",
            "runs/channel_bounce_path_reconciliation",
        ],
        "required": True,
        "must_contain": "channel_bounce_path_reconciliation",
    },
    {
        "name": "io_contract_python_detector",
        "cmd": ["python3", "analysis/validate_io_contract.py", "--out", "runs/io_contract_validation"],
        "required": True,
        "must_contain": "\"ok\": true",
    },
    {
        "name": "io_contract_g4_detector",
        "cmd": [
            "python3",
            "analysis/validate_io_contract.py",
            "--phase-space",
            "runs/channel_4ring_calibrated_v2/phase_space.csv",
            "--optics-history",
            "runs/channel_4ring_calibrated_v2/optics_history.csv",
            "--hits",
            "runs/geant4_detector_only_1k/hits.csv",
            "--event-summary",
            "runs/geant4_detector_only_1k/event_summary.csv",
            "--out",
            "runs/io_contract_validation_geant4_detector_1k",
        ],
        "required": True,
        "must_contain": "\"ok\": true",
    },
    {
        "name": "io_contract_g4_laue",
        "cmd": [
            "python3",
            "analysis/validate_io_contract.py",
            "--phase-space",
            "runs/geant4_laue_one_ring/phase_space.csv",
            "--optics-history",
            "runs/geant4_laue_one_ring/optics_history.csv",
            "--hits",
            "none",
            "--event-summary",
            "none",
            "--out",
            "runs/io_contract_validation_geant4_laue_one_ring",
        ],
        "required": True,
        "must_contain": "\"ok\": true",
    },
    {
        "name": "io_contract_g4_channel",
        "cmd": [
            "python3",
            "analysis/validate_io_contract.py",
            "--phase-space",
            "runs/geant4_channel_4ring_effective/phase_space.csv",
            "--optics-history",
            "runs/geant4_channel_4ring_effective/optics_history.csv",
            "--hits",
            "none",
            "--event-summary",
            "none",
            "--out",
            "runs/io_contract_validation_geant4_channel_4ring_effective",
        ],
        "required": True,
        "must_contain": "\"ok\": true",
    },
    {
        "name": "wsi_parratt_crosscheck",
        "cmd": ["python3", "analysis/crosscheck_wsi_parratt.py", "--out", "runs/wsi_parratt_crosscheck"],
        "required": True,
        "must_contain": "\"status\": \"PASS\"",
    },
    {
        "name": "pdfinfo_progress_report",
        "cmd": ["pdfinfo", "reports/opticsim_progress_report.pdf"],
        "required": True,
        "must_contain": "Pages:",
    },
]


def run_command(spec: dict[str, object]) -> dict[str, object]:
    started = time.time()
    completed = subprocess.run(
        spec["cmd"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    output = completed.stdout
    must = spec.get("must_contain")
    contains_ok = True if not must else str(must) in output
    ok = completed.returncode == 0 and contains_ok
    return {
        "name": spec["name"],
        "cmd": spec["cmd"],
        "required": bool(spec.get("required", True)),
        "returncode": completed.returncode,
        "ok": ok,
        "duration_s": round(time.time() - started, 3),
        "must_contain": must,
        "stdout_tail": output[-4000:],
    }


def write_markdown(report: dict[str, object], path: Path) -> None:
    lines = [
        "# Project Audit Report",
        "",
        f"Overall status: `{'PASS' if report['ok'] else 'FAIL'}`",
        f"Commands run: `{len(report['commands'])}`",
        f"Total duration: `{report['duration_s']} s`",
        "",
        "| Check | Status | Duration(s) |",
        "| --- | --- | ---: |",
    ]
    for row in report["commands"]:
        lines.append(f"| `{row['name']}` | `{'PASS' if row['ok'] else 'FAIL'}` | {row['duration_s']} |")
    lines.append("")
    for row in report["commands"]:
        if row["ok"]:
            continue
        lines.append(f"## Failed: {row['name']}")
        lines.append("")
        lines.append("```text")
        lines.append(str(row["stdout_tail"]))
        lines.append("```")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the project-level audit suite for external review.")
    parser.add_argument("--out", default="reports/project_audit")
    args = parser.parse_args()

    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    started = time.time()
    results = [run_command(spec) for spec in COMMANDS]
    report = {
        "ok": all(row["ok"] or not row["required"] for row in results),
        "duration_s": round(time.time() - started, 3),
        "commands": results,
    }
    with (out / "audit_summary.json").open("w") as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write("\n")
    write_markdown(report, out / "audit_report.md")
    print(json.dumps({"ok": report["ok"], "duration_s": report["duration_s"], "n_commands": len(results)}, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
