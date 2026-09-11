#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_TOP_LEVEL = {
    "README.md",
    "MANIFEST.md",
    "pyproject.toml",
    "laue511",
    "data",
    "tools",
    "tests",
    "reports",
    "benchmarks",
}

ALLOWED_REPORT_DIRS = {
    "geant4_current_crosscheck",
    "geant4_rebuilt_5k_crosscheck",
    "focal_convention_audit",
    "external_lens_handoff",
    "heart_adapter_feasibility",
    "bfull_offaxis_scan",
    "bfull_single_tile_xop_scan",
    "bfull_rocking_curve_map_status",
    "bfull_full_lens_xop_map_scan",
    "full_lens_observables",
    "python_full_lens_reference",
    "cosima_bridge_current_audit",
    "cosima_bridge_transmitted_current_audit",
}

ALLOWED_BENCHMARK_DIRS = {
    "reference_outputs",
    "xop_crystal",
    "xrt_pytte",
    "kohnle1998",
    "crystalpy",
    "opticsim_table_lens",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args()
    root = Path(args.root)
    report = audit_workspace(root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


def audit_workspace(root: Path) -> dict[str, object]:
    problems: list[str] = []
    top_level = {path.name for path in root.iterdir()}
    missing = sorted(EXPECTED_TOP_LEVEL - top_level)
    unexpected = sorted(name for name in top_level - EXPECTED_TOP_LEVEL if not name.startswith("."))
    if missing:
        problems.append("missing top-level entries: " + ",".join(missing))
    if unexpected:
        problems.append("unexpected top-level entries: " + ",".join(unexpected))

    cache_files = _relative_matches(root, lambda path: path.name == "__pycache__" or path.suffix == ".pyc")
    if cache_files:
        problems.append("python cache artifacts present: " + ",".join(cache_files[:5]))

    smoke_artifacts = _relative_matches(
        root,
        lambda path: any(token in path.name.lower() for token in ("smoke", "tmp", "temp")),
    )
    if smoke_artifacts:
        problems.append("smoke/temp artifacts present: " + ",".join(smoke_artifacts[:5]))

    report_dirs = {path.name for path in (root / "reports").iterdir() if path.is_dir()}
    unexpected_reports = sorted(report_dirs - ALLOWED_REPORT_DIRS)
    if unexpected_reports:
        problems.append("unexpected report dirs: " + ",".join(unexpected_reports))

    benchmark_dirs = {path.name for path in (root / "benchmarks").iterdir() if path.is_dir()}
    unexpected_benchmarks = sorted(benchmark_dirs - ALLOWED_BENCHMARK_DIRS)
    if unexpected_benchmarks:
        problems.append("unexpected benchmark dirs: " + ",".join(unexpected_benchmarks))

    total_bytes = sum(path.stat().st_size for path in root.rglob("*") if path.is_file())
    return {
        "ok": not problems,
        "root": str(root),
        "problems": problems,
        "total_bytes": total_bytes,
        "top_level_entries": sorted(top_level),
        "report_dirs": sorted(report_dirs),
        "benchmark_dirs": sorted(benchmark_dirs),
    }


def _relative_matches(root: Path, predicate: object) -> list[str]:
    matches = []
    for path in root.rglob("*"):
        if predicate(path):
            matches.append(str(path.relative_to(root)))
    return matches


if __name__ == "__main__":
    raise SystemExit(main())
