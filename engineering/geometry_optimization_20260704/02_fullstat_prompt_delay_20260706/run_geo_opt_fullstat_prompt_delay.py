#!/usr/bin/env python3
"""Run full-stat prompt and delayed datasets for the geo-opt S1/BPE/W5 geometry.

This runner intentionally keeps the production branch separate from the
Mass_model_511 authority outputs.  It copies Mass_model_511 source cards, changes
only their Geometry line / geometry_setup comment to the local geo-opt geometry,
then runs the same full-stat prompt, buildup, exact-position delayed-source, and
delayed-transport statistics as Mass_model_511 fullstat_v1.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
import re
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
LOG_DIR = WORK / "logs"
SOURCE_DIR = WORK / "source_cards"
MASS_SOURCE_DIR = (
    ROOT
    / "engineering/Mass_model_511_nearfield_migration_20260701/03_source_migration/source_dirs/Mass_model_511"
)
MASS_GEOMETRY = (
    "outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
GEOMETRY = (
    "engineering/geometry_optimization_20260704/01_geo_opt_s1_bottomw_b4c/geometry/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
GEOMETRY_MANIFEST = (
    ROOT
    / "engineering/geometry_optimization_20260704/01_geo_opt_s1_bottomw_b4c/"
    "geo_opt_s1_bottomw_b4c_manifest.json"
)
RUN_ROOT = ROOT / "runs/geometry_optimization_20260704"
LABEL = "geo_opt_s1_bpe_w5_fullstat_v1"
PROMPT_DIR = RUN_ROOT / f"step02_instant_{LABEL}"
BUILDUP_DIR = RUN_ROOT / f"step02_buildup_{LABEL}"
RAW_DIR = RUN_ROOT / f"step02_decay_source_{LABEL}"
FIX_DIR = RUN_ROOT / f"step02_delay_fix_{LABEL}"
EXACT_DIR = RUN_ROOT / f"step02_delay_exactpos_{LABEL}"
DELAYED_TRANSPORT_DIR = RUN_ROOT / f"step02_delayed_transport_{LABEL}"
DELAYED_REPORT_DIR = WORK / "delayed_source"
MANIFEST = WORK / f"{LABEL}_campaign_manifest.json"

RUN_EQUIV = ROOT / "code/tools/run_equiv2602_pipeline_NEW_GEO.py"
MAKE_RPIP = ROOT / "code/tools/makedecaysourcewithplot_rpip.py"
FIX_SOURCE = ROOT / "code/tools/build_fixed_delay_source.py"
EXACTPOS = ROOT / "code/tools/build_fix5_1of10_exactpos_delayed_source.py"
NUBASE = ROOT / "inputs/nubase/nubase_2020.txt"
MEGALIB_ENV = Path("/home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh")
COSIMA = "/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima"

GAMMA_EVENTS = 10_000_000
GAMMA_SPLITS = 12
NON_GAMMA_REPLICAS = 8
FARFIELD_RADIUS_CM = 60.0
M_BLOCKS = 50_000
SEED = 260613
RAW_TRIGGERS = 1_000_000
N_SAMPLE = 2_000_000
NON_GAMMA_DIV = 8

SOURCE_RE = re.compile(r"Background_(?P<tag>.+?)_fullsphere20\.source$")
FLUX_RE = re.compile(r"\.Flux\s+([-+0-9.eE]+)\s*$")


spec = importlib.util.spec_from_file_location("geo_opt_exactpos_helper", EXACTPOS)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load exactpos helper from {EXACTPOS}")
exactpos = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = exactpos
spec.loader.exec_module(exactpos)


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def source_tag(path: Path) -> str:
    match = SOURCE_RE.match(path.name)
    if not match:
        raise ValueError(f"Unexpected source filename: {path.name}")
    return match.group("tag")


def source_flux(path: Path) -> float:
    total = 0.0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = FLUX_RE.search(line)
        if match:
            total += float(match.group(1))
    return total


def run_cmd(cmd: list[str], log_path: Path, *, megalib: bool = False) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if megalib:
        if not MEGALIB_ENV.exists():
            raise RuntimeError(f"Missing MEGAlib environment script: {MEGALIB_ENV}")
        shell_cmd = f"source {shlex.quote(str(MEGALIB_ENV))} >/tmp/geo_opt_fullstat_megalib_env.log && " + shlex.join(cmd)
        launch = ["bash", "-lc", shell_cmd]
    else:
        launch = cmd
    with log_path.open("w", encoding="utf-8") as log:
        log.write("command=" + " ".join(shlex.quote(part) for part in launch) + "\n")
        log.write("-" * 72 + "\n")
        proc = subprocess.run(launch, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=False)
        log.write("-" * 72 + "\n")
        log.write(f"returncode={proc.returncode}\n")
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, launch)


def migrate_source_cards() -> dict[str, Any]:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    problems: list[str] = []
    for src in sorted(MASS_SOURCE_DIR.glob("Background_*_fullsphere20.source")):
        dst = SOURCE_DIR / src.name
        text = src.read_text(encoding="utf-8", errors="replace")
        text = text.replace(MASS_GEOMETRY, GEOMETRY)
        text = text.replace(
            "# v3p5 center-finger migrated source card",
            "# geo-opt S1/BPE/W5 source card copied from Mass_model_511",
        )
        dst.write_text(text, encoding="utf-8")
        geometry_lines = [line.strip() for line in text.splitlines() if line.strip().startswith("Geometry ")]
        comments = [line.strip() for line in text.splitlines() if line.strip().startswith("# geometry_setup=")]
        ok = (
            geometry_lines == [f"Geometry {GEOMETRY}"]
            and comments
            and comments[0] == f"# geometry_setup={GEOMETRY}"
            and MASS_GEOMETRY not in text
        )
        if not ok:
            problems.append(src.name)
        rows.append(
            {
                "particle": source_tag(dst),
                "source": rel(dst),
                "template_source": rel(src),
                "total_flux_cm2_s": source_flux(dst),
                "geometry_setup": GEOMETRY,
                "geometry_lines": geometry_lines,
                "geometry_comment": comments[0] if comments else None,
                "contains_mass_model_geometry": MASS_GEOMETRY in text,
                "status": "PASS" if ok else "FAIL",
            }
        )
    payload = {
        "status": "PASS_GEO_OPT_SOURCE_COPY_PREPARED" if not problems else "FAIL_GEO_OPT_SOURCE_COPY",
        "label": LABEL,
        "generated_at_utc": now_utc(),
        "source_dir": rel(SOURCE_DIR),
        "template_source_dir": rel(MASS_SOURCE_DIR),
        "geometry_setup": GEOMETRY,
        "geometry_manifest": rel(GEOMETRY_MANIFEST),
        "change_scope": "Copied Mass_model_511 source cards; changed only Geometry line, geometry_setup comment, and header label.",
        "farfield_radius_cm": FARFIELD_RADIUS_CM,
        "statistics_reference": "Mass_model_511 fullstat_v1 / fix5_fullstat_v2-equivalent source surface statistics",
        "sources": rows,
        "problems": problems,
    }
    write_json(SOURCE_DIR / "source_migration_manifest.json", payload)
    return payload


def inspect_sim_header(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": rel(path), "exists": False, "contains_geometry": False}
    lines: list[str] = []
    try:
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
            for _, line in zip(range(260), handle):
                lines.append(line)
    except (EOFError, OSError, gzip.BadGzipFile) as exc:
        return {
            "path": rel(path),
            "exists": True,
            "contains_geometry": False,
            "header_read_error": type(exc).__name__,
        }
    text = "".join(lines)
    return {"path": rel(path), "exists": True, "contains_geometry": GEOMETRY in text}


def summarize_step02_run(mode: str, outdir: Path) -> dict[str, Any]:
    manifest = outdir / "run_manifest.csv"
    summary = outdir / "run_summary.json"
    jobs: list[dict[str, str]] = []
    if manifest.exists():
        with manifest.open(newline="", encoding="utf-8") as handle:
            jobs = list(csv.DictReader(handle))
    rows = load_json(summary) if summary.exists() else []
    headers = [inspect_sim_header(Path(job["sim_path"])) for job in jobs]
    pass_or_skip = sum(1 for row in rows if row.get("status") in ("PASS", "SKIP"))
    fail = sum(1 for row in rows if row.get("status") == "FAIL")
    status = "NOT_PREPARED"
    if jobs:
        status = "PREPARED"
    if jobs and len(rows) == len(jobs) and pass_or_skip == len(jobs) and fail == 0:
        status = "PASS_TRANSPORT" if all(item["contains_geometry"] for item in headers) else "FAIL_HEADER_GEOMETRY"
    return {
        "mode": mode,
        "outdir": rel(outdir),
        "run_manifest": rel(manifest),
        "run_summary": rel(summary) if summary.exists() else None,
        "jobs": len(jobs),
        "summary_rows": len(rows),
        "pass_or_skip": pass_or_skip,
        "fail": fail,
        "events_requested": sum(int(job.get("events", 0)) for job in jobs),
        "sim_headers_with_expected_geometry": sum(1 for item in headers if item["exists"] and item["contains_geometry"]),
        "sim_headers_checked": len(headers),
        "status": status,
    }


def run_step02(mode: str, outdir: Path, workers: int, force: bool) -> dict[str, Any]:
    cmd = [
        "python3",
        str(RUN_EQUIV),
        "--mode",
        mode,
        "--source-dir",
        str(SOURCE_DIR),
        "--outdir",
        str(outdir),
        "--gamma-events",
        str(GAMMA_EVENTS),
        "--gamma-splits",
        str(GAMMA_SPLITS),
        "--non-gamma-replicas",
        str(NON_GAMMA_REPLICAS),
        "--farfield-radius-cm",
        str(FARFIELD_RADIUS_CM),
        "--workers",
        str(workers),
        "--keep-sources",
        "--allow-heavy-run",
    ]
    if force:
        cmd.append("--force")
    run_cmd(cmd, LOG_DIR / f"run_{mode}.log", megalib=True)
    return summarize_step02_run(mode, outdir)


def require_buildup_ready() -> None:
    for mode, outdir in (("instant", PROMPT_DIR), ("buildup", BUILDUP_DIR)):
        summary = summarize_step02_run(mode, outdir)
        if summary["status"] != "PASS_TRANSPORT":
            raise SystemExit(f"{mode} is not ready for delayed-source build: {summary}")


def build_raw_source(workers: int, force: bool) -> dict[str, Any]:
    require_buildup_ready()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    marker = RAW_DIR / "activation_decay_day15.source"
    cmd = [
        "python3",
        str(MAKE_RPIP),
        "--dat",
        str(BUILDUP_DIR / "*.dat.inc1.dat"),
        "--sim",
        str(BUILDUP_DIR / "*.inc1.id1.sim.gz"),
        "--geo",
        GEOMETRY,
        "--non-gamma-div",
        str(NON_GAMMA_DIV),
        "--gamma-div",
        "auto",
        "--t-ground-days",
        "0",
        "--t-flight-days",
        "15",
        "--t-after-days",
        "0",
        "--outdir",
        str(RAW_DIR),
        "--outfile-prefix",
        str(RAW_DIR / f"DelayedDecayRaw_{LABEL}"),
        "--triggers",
        str(RAW_TRIGGERS),
        "--z-bins",
        "60",
        "--r-bins",
        "100",
        "--n-sample",
        str(N_SAMPLE),
        "--workers",
        str(workers),
        "--nubase",
        str(NUBASE),
        "--seed",
        str(SEED),
    ]
    if force or not marker.exists():
        run_cmd(cmd, LOG_DIR / "build_raw_delayed_source.log")
    return {
        "raw_source_dir": rel(RAW_DIR),
        "raw_source": rel(marker),
        "exists": marker.exists(),
        "log": rel(LOG_DIR / "build_raw_delayed_source.log"),
    }


def build_fixed_source(force: bool) -> dict[str, Any]:
    FIX_DIR.mkdir(parents=True, exist_ok=True)
    source = RAW_DIR / "activation_decay_day15.source"
    marker = FIX_DIR / "activation_decay_day15_groundstate_fixed.source"
    cmd = [
        "python3",
        str(FIX_SOURCE),
        "--source",
        str(source),
        "--dat-glob",
        str(BUILDUP_DIR / "*.dat.inc1.dat"),
        "--nubase",
        str(NUBASE),
        "--outdir",
        str(FIX_DIR),
        "--outfile-prefix",
        str(FIX_DIR / f"DelayedDecayFixed_{LABEL}"),
        "--output-source-name",
        "activation_decay_day15_groundstate_fixed.source",
        "--triggers",
        str(RAW_TRIGGERS),
        "--geometry",
        str(ROOT / GEOMETRY),
        "--non-gamma-div",
        str(NON_GAMMA_DIV),
        "--gamma-div",
        "auto",
        "--t-flight-days",
        "15",
    ]
    if force or not marker.exists():
        run_cmd(cmd, LOG_DIR / "build_fixed_delayed_source.log")
    audit = FIX_DIR / "normalization_audit_groundstate_fix.json"
    audit_json = load_json(audit) if audit.exists() else {}
    return {
        "fix_dir": rel(FIX_DIR),
        "fixed_source": rel(marker),
        "normalization_audit": rel(audit),
        "normalization_status": audit_json.get("status"),
        "normalization_problems": audit_json.get("problems", []),
        "log": rel(LOG_DIR / "build_fixed_delayed_source.log"),
    }


def configure_exactpos() -> None:
    EXACT_DIR.mkdir(parents=True, exist_ok=True)
    DELAYED_TRANSPORT_DIR.mkdir(parents=True, exist_ok=True)
    DELAYED_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    exactpos.LABEL = f"{LABEL}_exactpos_m50000_s{SEED}"
    exactpos.REPORT_DIR = DELAYED_REPORT_DIR
    exactpos.INSTANT = PROMPT_DIR
    exactpos.BUILDUP = BUILDUP_DIR
    exactpos.RAW_SOURCE_DIR = RAW_DIR
    exactpos.FIX = FIX_DIR
    exactpos.FIXED_SOURCE = FIX_DIR / "activation_decay_day15_groundstate_fixed.source"
    exactpos.FIX_SUMMARY = FIX_DIR / "source_fix_summary.json"
    exactpos.FIX_AUDIT = FIX_DIR / "normalization_audit_groundstate_fix.json"
    exactpos.SOURCE_DIR = EXACT_DIR
    exactpos.TRANSPORT_DIR = DELAYED_TRANSPORT_DIR
    exactpos.SOURCE_PREFIX = DELAYED_TRANSPORT_DIR / "DelayedDecayGeoOptS1BpeW5FullstatV1"
    exactpos.SOURCE = EXACT_DIR / "activation_decay_day15_groundstate_fixed_exactpos.source"
    exactpos.MANIFEST = EXACT_DIR / f"{LABEL}_exactpos_delayed_source_manifest.json"
    exactpos.WEIGHTED_TABLE = EXACT_DIR / "exactpos_weighted_rpip_table.csv"
    exactpos.SUMMARY_JSON = DELAYED_REPORT_DIR / "delayed_source_exactpos_summary.json"
    exactpos.SUMMARY_MD = DELAYED_REPORT_DIR / "delayed_source_exactpos_summary.md"
    exactpos.GEOMETRY = ROOT / GEOMETRY


def build_exactpos_source(force: bool) -> dict[str, Any]:
    configure_exactpos()
    if force or not exactpos.SOURCE.exists():
        exactpos.build_source(M_BLOCKS, RAW_TRIGGERS, SEED)
    summary = load_json(exactpos.SUMMARY_JSON)
    return {
        "source": rel(exactpos.SOURCE),
        "summary": rel(exactpos.SUMMARY_JSON),
        "manifest": rel(exactpos.MANIFEST),
        "weighted_table": rel(exactpos.WEIGHTED_TABLE),
        "status": summary.get("status"),
        "n_pointsource_blocks": summary.get("n_pointsource_blocks"),
        "triggers": RAW_TRIGGERS,
        "sampling_status": summary.get("sampling_audit", {}).get("status"),
        "sampling_problems": summary.get("sampling_audit", {}).get("problems", []),
    }


def run_delayed_transport(force: bool) -> dict[str, Any]:
    configure_exactpos()
    sim = exactpos.SOURCE_PREFIX.with_suffix(".inc1.id1.sim.gz")
    log = LOG_DIR / "run_delayed_transport.log"
    if force or not sim.exists():
        run_cmd([COSIMA, "-s", str(SEED), str(exactpos.SOURCE)], log, megalib=True)
    manifest = exactpos.summarize_transport()
    transport = manifest.get("delayed_transport", {})
    header_geometry = str(transport.get("geometry", ""))
    return {
        "status": manifest.get("status"),
        "source": rel(exactpos.SOURCE),
        "transport_sim": transport.get("path"),
        "SE": transport.get("SE"),
        "ID": transport.get("ID"),
        "TS": transport.get("TS"),
        "TE_s": transport.get("TE_s"),
        "geometry": header_geometry,
        "contains_expected_geometry": GEOMETRY in header_geometry,
        "log": rel(log),
    }


def write_campaign_manifest(records: dict[str, Any]) -> None:
    prompt_ok = all(
        row.get("status") == "PASS_TRANSPORT" for row in records.get("prompt_buildup", [])
    )
    delayed_rows = records.get("delayed_transport", [])
    delayed_ok = bool(delayed_rows) and all(str(row.get("status", "")).startswith("PASS") for row in delayed_rows)
    if prompt_ok and delayed_ok:
        status = "PASS_PROMPT_AND_DELAYED_TRANSPORT"
    elif prompt_ok:
        status = "PASS_PROMPT_BUILDUP_DELAYED_IN_PROGRESS_OR_PREPARED"
    else:
        status = "IN_PROGRESS_OR_PREPARED"
    payload = {
        "document_type": "geo_opt_s1_bpe_w5_fullstat_prompt_delay_campaign",
        "generated_at_utc": now_utc(),
        "status": status,
        "claim_boundary": (
            "Transport datasets only. Detector-rate/background claims require Step05 detector response, "
            "normalization audit review, and downstream rate/significance rebuild."
        ),
        "label": LABEL,
        "geometry": GEOMETRY,
        "geometry_manifest": rel(GEOMETRY_MANIFEST),
        "statistics_reference": "Mass_model_511 fullstat_v1",
        "statistics": {
            "gamma_events": GAMMA_EVENTS,
            "gamma_splits": GAMMA_SPLITS,
            "non_gamma_replicas": NON_GAMMA_REPLICAS,
            "farfield_radius_cm": FARFIELD_RADIUS_CM,
            "m_pointsource_blocks": M_BLOCKS,
            "seed": SEED,
            "raw_triggers": RAW_TRIGGERS,
            "n_sample": N_SAMPLE,
            "non_gamma_div": NON_GAMMA_DIV,
        },
        "work_dir": rel(WORK),
        "run_root": rel(RUN_ROOT),
        **records,
    }
    write_json(MANIFEST, payload)
    lines = [
        "# GeoOpt S1/BPE/W5 Fullstat Prompt + Delay Campaign",
        "",
        f"- generated_at_utc: `{payload['generated_at_utc']}`",
        f"- status: `{payload['status']}`",
        f"- geometry: `{GEOMETRY}`",
        f"- statistics_reference: `{payload['statistics_reference']}`",
        "",
        "## Prompt/Buildup",
        "",
        "| Mode | Status | Jobs | Events | Header geometry | Summary |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in records.get("prompt_buildup", []):
        lines.append(
            f"| `{row.get('mode')}` | `{row.get('status')}` | {row.get('jobs')} | "
            f"{row.get('events_requested')} | {row.get('sim_headers_with_expected_geometry')}/{row.get('sim_headers_checked')} | "
            f"`{row.get('run_summary')}` |"
        )
    lines.extend(["", "## Delayed", ""])
    lines.append(f"- raw_source: `{records.get('raw_source', {}).get('raw_source')}`")
    lines.append(f"- fixed_source: `{records.get('fixed_source', {}).get('fixed_source')}`")
    lines.append(f"- exactpos_source: `{records.get('exactpos_source', {}).get('source')}`")
    for row in records.get("delayed_transport", []):
        lines.append(f"- delayed_transport: `{row.get('status')}` `{row.get('transport_sim')}`")
    lines.extend(["", "Boundary: this is not a detector-rate or no-effect claim."])
    (WORK / f"{LABEL}_campaign_manifest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def current_records() -> dict[str, Any]:
    records: dict[str, Any] = {
        "source_migration": load_json(SOURCE_DIR / "source_migration_manifest.json")
        if (SOURCE_DIR / "source_migration_manifest.json").exists()
        else None,
        "prompt_buildup": [
            summarize_step02_run("instant", PROMPT_DIR),
            summarize_step02_run("buildup", BUILDUP_DIR),
        ],
        "raw_source": {
            "raw_source_dir": rel(RAW_DIR),
            "raw_source": rel(RAW_DIR / "activation_decay_day15.source"),
            "exists": (RAW_DIR / "activation_decay_day15.source").exists(),
        },
        "fixed_source": {
            "fix_dir": rel(FIX_DIR),
            "fixed_source": rel(FIX_DIR / "activation_decay_day15_groundstate_fixed.source"),
            "exists": (FIX_DIR / "activation_decay_day15_groundstate_fixed.source").exists(),
        },
        "exactpos_source": {
            "source": rel(EXACT_DIR / "activation_decay_day15_groundstate_fixed_exactpos.source"),
            "exists": (EXACT_DIR / "activation_decay_day15_groundstate_fixed_exactpos.source").exists(),
        },
        "delayed_transport": [],
    }
    sim = DELAYED_TRANSPORT_DIR / "DelayedDecayGeoOptS1BpeW5FullstatV1.inc1.id1.sim.gz"
    if sim.exists():
        configure_exactpos()
        try:
            manifest = exactpos.summarize_transport()
            transport = manifest.get("delayed_transport", {})
            records["delayed_transport"].append(
                {
                    "status": manifest.get("status"),
                    "transport_sim": transport.get("path"),
                    "SE": transport.get("SE"),
                    "ID": transport.get("ID"),
                    "TE_s": transport.get("TE_s"),
                    "geometry": transport.get("geometry"),
                    "contains_expected_geometry": GEOMETRY in str(transport.get("geometry", "")),
                }
            )
        except Exception as exc:  # summary should not mask production status
            records["delayed_transport"].append({"status": f"SUMMARY_FAILED: {exc}", "transport_sim": rel(sim)})
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Run source migration, prompt, buildup, delayed source, and delayed transport.")
    parser.add_argument("--migrate-sources", action="store_true")
    parser.add_argument("--run-prompt", action="store_true")
    parser.add_argument("--run-buildup", action="store_true")
    parser.add_argument("--prepare-delay", action="store_true")
    parser.add_argument("--run-delay", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    if args.all:
        args.migrate_sources = True
        args.run_prompt = True
        args.run_buildup = True
        args.prepare_delay = True
        args.run_delay = True
    if not any((args.migrate_sources, args.run_prompt, args.run_buildup, args.prepare_delay, args.run_delay, args.status)):
        args.status = True

    records = current_records()
    if args.migrate_sources:
        records["source_migration"] = migrate_source_cards()
        if records["source_migration"]["status"] != "PASS_GEO_OPT_SOURCE_COPY_PREPARED":
            write_campaign_manifest(records)
            raise SystemExit("Source-card migration failed")
    if args.run_prompt:
        records["prompt_buildup"][0] = run_step02("instant", PROMPT_DIR, args.workers, args.force)
    if args.run_buildup:
        records["prompt_buildup"][1] = run_step02("buildup", BUILDUP_DIR, args.workers, args.force)
    if args.prepare_delay:
        records["raw_source"] = build_raw_source(args.workers, args.force)
        records["fixed_source"] = build_fixed_source(args.force)
        records["exactpos_source"] = build_exactpos_source(args.force)
    if args.run_delay:
        records["delayed_transport"] = [run_delayed_transport(args.force)]

    write_campaign_manifest(records)
    print(json.dumps({"manifest": rel(MANIFEST), **records}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
