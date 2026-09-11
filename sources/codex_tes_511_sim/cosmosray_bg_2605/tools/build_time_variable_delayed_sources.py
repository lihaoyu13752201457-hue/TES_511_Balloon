#!/usr/bin/env python3
"""Build day-series delayed source files by scaling the fixed day-15 source.

This tool is for the constant-profile validation path.  It preserves the
day-15 source geometry/profile definitions and rescales each source-block flux
by the ODE-derived activity ratio for the matching volume and isotope.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ACTIVITY = ROOT / "reports" / "nextphase_511" / "time_variable_day1_day20" / "inventory" / "activity_by_time_nuclide_volume.csv"
DEFAULT_TEMPLATE = ROOT / "production_runs" / "delay_fix_from_buildup_equiv2602" / "activation_decay_day15_groundstate_fixed.source"
DEFAULT_OUT = ROOT / "production_runs" / "time_variable_delayed"

FLUX_RE = re.compile(r"^(?P<name>S_(?P<vn>.+)_(?P<za>\d+)_z\d+)\.Flux\s+(?P<flux>[-+0-9.eE]+)(?P<tail>\s*)$")
FILENAME_RE = re.compile(r"^(?P<run>\S+)\.FileName\s+")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def parse_days(text: str) -> list[float]:
    days = []
    for item in text.split(","):
        item = item.strip()
        if item:
            days.append(float(item))
    return sorted(set(days))


def day_tag(day: float) -> str:
    if abs(day - round(day)) < 1.0e-9:
        return f"day{int(round(day)):02d}"
    return "day" + str(day).replace(".", "p")


def build_ratio_table(activity_csv: Path) -> dict[tuple[float, str, str], float]:
    rows = read_csv(activity_csv)
    ratios: dict[tuple[float, str, str], float] = {}
    for row in rows:
        try:
            day = float(row["day"])
            ref = float(row["reference_activity_Bq_day15"])
            activity = float(row["activity_Bq"])
        except (KeyError, ValueError):
            continue
        vn = row.get("VN", "")
        za = row.get("ZA", "")
        if not vn or not za or ref <= 0.0:
            continue
        ratios[(day, vn, za)] = activity / ref
    return ratios


def rewrite_source_for_day(template_lines: list[str], day: float, ratios: dict[tuple[float, str, str], float], out_source: Path) -> dict[str, object]:
    tag = day_tag(day)
    out_lines: list[str] = []
    n_flux = 0
    missing: list[str] = []
    max_day15_rel_change = 0.0

    for line in template_lines:
        m_file = FILENAME_RE.match(line)
        if m_file:
            run = m_file.group("run")
            out_lines.append(f"{run}.FileName production_runs/time_variable_delayed/{tag}/DelayedDecay_{tag}_constant_profile\n")
            continue
        m = FLUX_RE.match(line.rstrip("\n"))
        if not m:
            out_lines.append(line)
            continue
        name = m.group("name")
        vn = m.group("vn")
        za = m.group("za")
        old_flux = float(m.group("flux"))
        ratio = ratios.get((day, vn, za))
        if ratio is None:
            missing.append(name)
            ratio = 1.0
        new_flux = old_flux * ratio
        if abs(day - 15.0) < 1.0e-9 and old_flux:
            max_day15_rel_change = max(max_day15_rel_change, abs(new_flux - old_flux) / abs(old_flux))
        out_lines.append(f"{name}.Flux {new_flux:.8e}{m.group('tail')}\n")
        n_flux += 1

    out_source.parent.mkdir(parents=True, exist_ok=True)
    out_source.write_text("".join(out_lines), encoding="utf-8")
    return {
        "day": day,
        "tag": tag,
        "source": str(out_source.relative_to(ROOT) if out_source.is_relative_to(ROOT) else out_source),
        "flux_lines_scaled": n_flux,
        "missing_ratio_count": len(missing),
        "missing_ratio_examples": missing[:20],
        "max_day15_flux_rel_change": max_day15_rel_change,
    }


def build_sources(activity_csv: Path, template: Path, outdir: Path, days: list[float]) -> dict[str, object]:
    ratios = build_ratio_table(activity_csv)
    if not ratios:
        raise SystemExit(f"no activity ratios read from {activity_csv}")
    template_lines = template.read_text(encoding="utf-8").splitlines(keepends=True)
    records = []
    for day in days:
        tag = day_tag(day)
        out_source = outdir / tag / f"activation_decay_{tag}_constant_profile.source"
        records.append(rewrite_source_for_day(template_lines, day, ratios, out_source))

    manifest = outdir / "run_manifest.csv"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    with manifest.open("w", encoding="utf-8", newline="") as fh:
        fieldnames = ["day", "tag", "source", "flux_lines_scaled", "missing_ratio_count", "max_day15_flux_rel_change"]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            writer.writerow({k: rec[k] for k in fieldnames})

    day15_records = [r for r in records if abs(float(r["day"]) - 15.0) < 1.0e-9]
    day15_ok = bool(day15_records) and all(
        int(r["missing_ratio_count"]) == 0 and float(r["max_day15_flux_rel_change"]) < 1.0e-10
        for r in day15_records
    )
    passed = all(int(r["missing_ratio_count"]) == 0 for r in records) and day15_ok
    summary = {
        "status": "PASS" if passed else "FAIL",
        "mode": "constant_profile_day_series_source_scaling",
        "activity_csv": str(activity_csv.relative_to(ROOT) if activity_csv.is_relative_to(ROOT) else activity_csv),
        "template_source": str(template.relative_to(ROOT) if template.is_relative_to(ROOT) else template),
        "outdir": str(outdir.relative_to(ROOT) if outdir.is_relative_to(ROOT) else outdir),
        "days": days,
        "records": records,
        "day15_source_reproduces_template_fluxes": day15_ok,
        "caveat": "Sources are scaled from fixed day-15 spatial profiles; no new RPIP spatial distribution is generated for non-constant flight conditions.",
    }
    (outdir / "source_build_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, default=DEFAULT_ACTIVITY)
    parser.add_argument("--template-source", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--days", default="1,5,10,15,20")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    summary = build_sources(args.inventory, args.template_source, args.out, parse_days(args.days))
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
