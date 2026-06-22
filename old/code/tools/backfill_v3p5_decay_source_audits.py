#!/usr/bin/env python3
"""Backfill v3p5 decay-source normalization audit files.

This does not regenerate source blocks or rerun transport. It reuses the
current source-builder audit functions on the existing buildup .dat files and
writes the raw and ground-state-fix normalization audit artifacts.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-newgeo")

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "code" / "tools"
sys.path.insert(0, str(TOOLS))

import build_fixed_delay_source as fixed_audit  # noqa: E402
import makedecaysourcewithplot_rpip as raw_audit  # noqa: E402


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def label_paths(label: str) -> tuple[Path, Path, Path]:
    suffix = f"_v3p5_centerfinger_{label}"
    return (
        ROOT / f"runs/step02_buildup{suffix}",
        ROOT / f"runs/step02_decay_source{suffix}",
        ROOT / f"runs/step02_delay_fix{suffix}",
    )


def backfill(label: str) -> dict[str, object]:
    buildup_dir, raw_dir, fixed_dir = label_paths(label)
    norm_path = buildup_dir / "normalization.json"
    if not norm_path.exists():
        raise FileNotFoundError(norm_path)
    norm = json.loads(norm_path.read_text(encoding="utf-8"))
    non_gamma_div = float(norm.get("non_gamma_replicas", 1.0))
    gamma_div = "auto"
    dat_paths = sorted(buildup_dir.glob("*.dat.inc1.dat"))
    if not dat_paths:
        raise FileNotFoundError(f"no buildup dat files under {buildup_dir}")

    raw_dir.mkdir(parents=True, exist_ok=True)
    fixed_dir.mkdir(parents=True, exist_ok=True)

    raw_tt, raw_rp, raw_norm_audit, raw_problems = raw_audit.parse_rp_from_dat(
        [str(path) for path in dat_paths],
        non_gamma_div,
        gamma_div,
        False,
    )
    raw_audit._write_normalization_audit(raw_dir, 15, raw_norm_audit, raw_problems)

    fixed_tt, fixed_rp, fixed_norm_audit, fixed_problems = fixed_audit.parse_rp_from_dat(
        dat_paths,
        non_gamma_div,
        gamma_div,
        False,
    )
    fixed_csv, fixed_json = fixed_audit._write_normalization_audit(
        fixed_dir,
        fixed_norm_audit,
        fixed_problems,
    )

    problems = raw_problems + fixed_problems
    if problems:
        raise RuntimeError("; ".join(problems))
    return {
        "label": label,
        "status": "PASS",
        "dat_files": len(dat_paths),
        "non_gamma_div": non_gamma_div,
        "gamma_div": gamma_div,
        "raw_audit_json": rel(raw_dir / "normalization_audit_day15.json"),
        "raw_audit_csv": rel(raw_dir / "normalization_audit_day15.csv"),
        "fixed_audit_json": rel(fixed_json),
        "fixed_audit_csv": rel(fixed_csv),
        "raw_tags": sorted(raw_tt),
        "fixed_tags": sorted(fixed_tt),
        "raw_rp_terms": len(raw_rp),
        "fixed_rp_terms": len(fixed_rp),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", action="append", default=[], help="v3p5 label to audit, repeatable")
    args = parser.parse_args()
    labels = args.label or ["1of10", "fullstat_v2"]
    rows = [backfill(label) for label in labels]
    out = {
        "status": "PASS_V3P5_DECAY_SOURCE_AUDIT_BACKFILL",
        "labels": rows,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
