from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_TOLERANCES = {
    "channel_python.transmissivity": 0.01,
    "channel_python.effective_area_cm2": 1.0,
    "channel_python.spot_d90_cm": 0.10,
    "geant4_channel_effective.transmissivity": 0.02,
    "geant4_channel_effective.effective_area_cm2": 2.0,
    "geant4_channel_effective.spot_d90_cm": 0.20,
    "detector_python.measured_peak_fwhm_eV": 30.0,
    "detector_python.selected_fraction_total": 0.03,
    "wsi_crosscheck.max_abs_delta_R": 1.0e-12,
}


def load_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    with p.open() as f:
        return json.load(f)


def dotted_get(data: dict[str, Any], dotted: str) -> Any:
    current: Any = data
    for part in dotted.split("."):
        current = current[part]
    return current


def compare(baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for metric, tolerance in DEFAULT_TOLERANCES.items():
        base = dotted_get(baseline, metric)
        now = dotted_get(current, metric)
        delta = abs(float(now) - float(base))
        rows.append(
            {
                "metric": metric,
                "baseline": base,
                "current": now,
                "abs_delta": delta,
                "tolerance": tolerance,
                "ok": delta <= tolerance,
            }
        )
    return {"ok": all(row["ok"] for row in rows), "comparisons": rows}


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Baseline Regression Comparison",
        "",
        f"Overall status: `{'PASS' if report['ok'] else 'FAIL'}`",
        "",
        "| Metric | Baseline | Current | Abs delta | Tolerance | Status |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in report["comparisons"]:
        lines.append(
            f"| `{row['metric']}` | `{float(row['baseline']):.12g}` | "
            f"`{float(row['current']):.12g}` | `{row['abs_delta']:.3g}` | "
            f"`{row['tolerance']:.3g}` | `{'PASS' if row['ok'] else 'FAIL'}` |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare current metrics against a frozen opticsim baseline.")
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--current", required=True)
    parser.add_argument("--out", default="reports/baseline/baseline_compare_report.md")
    args = parser.parse_args()

    report = compare(load_json(args.baseline), load_json(args.current))
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    write_markdown(report, out)
    print(json.dumps({"ok": report["ok"], "n": len(report["comparisons"])}, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
