#!/usr/bin/env python3
"""Wrapper for BGO engineering exact-position delayed sources.

The source-building algorithm is the existing fix5 exact-position builder. This
wrapper only redirects paths to HARNESS_20260624 BGO staged-run directories.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BUILDER_PATH = ROOT / "code/tools/build_fix5_1of10_exactpos_delayed_source.py"
BGO_GEOMETRY = (
    ROOT
    / "engineering/background_validation_20260624/04_bgo_variant/geometry_bgo_same_envelope/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_bgo_same_envelope_megalib_proxy.geo.setup"
)


def load_builder():
    spec = importlib.util.spec_from_file_location("bgo_engineering_exactpos_builder", BUILDER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {BUILDER_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def configure(builder, stage_dir: Path, label: str, prefix_name: str) -> None:
    instant = stage_dir / "instant"
    buildup = stage_dir / "buildup"
    raw = stage_dir / "decay_source"
    fix = stage_dir / "delay_fix"
    transport = stage_dir / "delayed_transport_exactpos"
    report = stage_dir / "exactpos_report"

    builder.LABEL = label
    builder.REPORT_DIR = report
    builder.INSTANT = instant
    builder.BUILDUP = buildup
    builder.RAW_SOURCE_DIR = raw
    builder.FIX = fix
    builder.FIXED_SOURCE = fix / "activation_decay_day15_groundstate_fixed.source"
    builder.FIX_SUMMARY = fix / "source_fix_summary.json"
    builder.FIX_AUDIT = fix / "normalization_audit_groundstate_fix.json"
    builder.SOURCE_DIR = fix
    builder.TRANSPORT_DIR = transport
    builder.SOURCE_PREFIX = transport / prefix_name
    builder.SOURCE = fix / f"activation_decay_day15_groundstate_fixed_exactpos_{label}.source"
    builder.MANIFEST = fix / f"{label}_delayed_source_manifest.json"
    builder.WEIGHTED_TABLE = fix / f"exactpos_weighted_rpip_table_{label}.csv"
    builder.SUMMARY_JSON = report / f"{label}_delayed_source_exactpos_summary.json"
    builder.SUMMARY_MD = report / f"{label}_delayed_source_exactpos_summary.md"
    builder.GEOMETRY = BGO_GEOMETRY


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-dir", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--prefix-name", required=True)
    sub = parser.add_subparsers(dest="cmd", required=True)
    build = sub.add_parser("build-source")
    build.add_argument("--n-decays", type=int, default=5000)
    build.add_argument("--triggers", type=int, default=100000)
    build.add_argument("--seed", type=int, default=260613)
    sub.add_parser("summarize-transport")
    args = parser.parse_args()

    builder = load_builder()
    configure(builder, args.stage_dir, args.label, args.prefix_name)
    if args.cmd == "build-source":
        builder.build_source(args.n_decays, args.triggers, args.seed)
    elif args.cmd == "summarize-transport":
        manifest = builder.summarize_transport()
        return 0 if manifest["status"].startswith("PASS") else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
