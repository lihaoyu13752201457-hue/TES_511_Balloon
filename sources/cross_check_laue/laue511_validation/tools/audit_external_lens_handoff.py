#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from laue511.external_lens import import_external_lens_observables


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=str(ROOT / "benchmarks/reference_outputs/external_lens_observables_schema_example.csv"),
    )
    parser.add_argument("--out-dir", default=str(ROOT / "reports/external_lens_handoff"))
    parser.add_argument("--work-dir", default="/tmp/laue511_external_lens_handoff_audit")
    parser.add_argument("--current-observables", default=str(ROOT / "reports/full_lens_observables/metrics.json"))
    parser.add_argument("--python-reference", default=str(ROOT / "reports/python_full_lens_reference/metrics.json"))
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics = audit_handoff(
        input_path=Path(args.input),
        work_dir=Path(args.work_dir),
        current_observables=Path(args.current_observables),
        python_reference=Path(args.python_reference),
    )
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_summary(out_dir / "summary.md", metrics)
    print(json.dumps({"ok": metrics["ok"], "out": str(out_dir)}, indent=2, sort_keys=True))
    return 0 if metrics["ok"] else 1


def audit_handoff(
    *,
    input_path: Path,
    work_dir: Path,
    current_observables: Path,
    python_reference: Path,
) -> dict[str, object]:
    shutil.rmtree(work_dir, ignore_errors=True)
    try:
        summary = import_external_lens_observables(
            input_path,
            work_dir,
            current_observables_path=current_observables,
            python_reference_path=python_reference,
        )
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
    temp_removed = not work_dir.exists()
    agreement_checks = summary.get("agreement_checks", {})
    ok = bool(summary["ok"]) and temp_removed and all(bool(value) for value in agreement_checks.values())
    return {
        "ok": ok,
        "input": str(input_path),
        "work_dir_removed": temp_removed,
        "import_ok": bool(summary["ok"]),
        "n_rows": summary.get("n_rows"),
        "source_tools": summary.get("source_tools", []),
        "source_versions": summary.get("source_versions", []),
        "agreement_checks": agreement_checks,
        "agreement_thresholds": summary.get("agreement_thresholds", {}),
        "comparison": summary.get("comparison", {}),
        "lens_metrics": summary.get("lens_metrics", {}),
    }


def _write_summary(path: Path, metrics: dict[str, object]) -> None:
    lines = [
        "# External Lens Handoff Audit",
        "",
        f"Status: `{metrics['ok']}`",
        f"Input: `{metrics['input']}`",
        f"Rows checked: `{metrics['n_rows']}`",
        f"Temporary work directory removed: `{metrics['work_dir_removed']}`",
        "",
        "## Agreement Checks",
        "",
    ]
    for name, ok in metrics["agreement_checks"].items():
        lines.append(f"- {name}: `{ok}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
