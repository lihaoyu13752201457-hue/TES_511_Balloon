#!/usr/bin/env python3
"""Build and run Mass_model_511 delayed detector transport.

The historical default remains the smoke campaign.  Publication-stat follow-up
must be requested explicitly with ``--stat-label fullstat_v1`` so smoke S0/S1
paths cannot be confused with the current-geometry full-stat delayed branch.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "engineering/Mass_model_511_nearfield_migration_20260701"
TRANSPORT_DIR = PKG / "03_detector_transport"
SMOKE_MATRIX = PKG / "02_run_plan/smoke_run_matrix.csv"
RUN_ROOT = ROOT / "runs/Mass_model_511_nearfield_migration_20260701"
NUBASE = ROOT / "inputs/nubase/nubase_2020.txt"
MAKE_RPIP = ROOT / "code/tools/makedecaysourcewithplot_rpip.py"
FIX_SOURCE = ROOT / "code/tools/build_fixed_delay_source.py"
EXACTPOS = ROOT / "code/tools/build_fix5_1of10_exactpos_delayed_source.py"
COSIMA = "/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima"

CANDIDATE_BRANCH = "candidate_Mass_model_511"
BASELINE_BRANCH = "baseline_detector"
CANDIDATE_GEOMETRY = (
    "outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
BASELINE_GEOMETRY = (
    "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
BRANCH_GEOMETRY = {
    CANDIDATE_BRANCH: CANDIDATE_GEOMETRY,
    BASELINE_BRANCH: BASELINE_GEOMETRY,
}
BRANCH = CANDIDATE_BRANCH
GEOMETRY = CANDIDATE_GEOMETRY
STAT_LABEL = "smoke"
M_BLOCKS = 50_000
DEFAULT_SEED = 260613
FULLSTAT_FIX5_SEED = 260613
FULLSTAT_FIX5_RAW_TRIGGERS = 1_000_000
FULLSTAT_FIX5_N_SAMPLE = 2_000_000
FULLSTAT_FIX5_NON_GAMMA_DIV = 8


spec = importlib.util.spec_from_file_location("mass_model_511_exactpos_helper", EXACTPOS)
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


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def set_branch(branch: str) -> None:
    global BRANCH, GEOMETRY
    if branch not in BRANCH_GEOMETRY:
        raise SystemExit(f"Unknown branch: {branch}")
    BRANCH = branch
    GEOMETRY = BRANCH_GEOMETRY[branch]


def set_stat_label(label: str) -> None:
    global STAT_LABEL
    if label not in ("smoke", "fullstat_v1"):
        raise SystemExit(f"Unknown stat label: {label}")
    if label == "fullstat_v1" and BRANCH != CANDIDATE_BRANCH:
        raise SystemExit("fullstat_v1 delayed follow-up is currently defined only for candidate_Mass_model_511")
    STAT_LABEL = label


def path_suffix() -> str:
    return f"{BRANCH}_{STAT_LABEL}"


def stage_path_suffix(stage: str) -> str:
    if STAT_LABEL == "smoke":
        return f"{BRANCH}_{stage}_smoke"
    return path_suffix()


def source_stage_token(stage: str) -> str:
    if STAT_LABEL == "smoke":
        return f"_{stage}"
    return ""


def transport_prefix(stage: str) -> str:
    stage_token = stage if STAT_LABEL == "smoke" else "FullstatV1"
    if BRANCH == CANDIDATE_BRANCH:
        return f"DelayedDecayMassModel511Candidate{stage_token}"
    if BRANCH == BASELINE_BRANCH:
        return f"DelayedDecayMassModel511Baseline{stage_token}"
    safe = BRANCH.replace("-", "_").replace("/", "_")
    return f"DelayedDecayMassModel511_{safe}_{stage_token}"


def run_dir(mode: str) -> Path:
    return RUN_ROOT / f"step02_{mode}_{path_suffix()}"


def raw_source_dir() -> Path:
    return RUN_ROOT / f"step02_decay_source_{path_suffix()}"


def fix_dir() -> Path:
    return RUN_ROOT / f"step02_delay_fix_{path_suffix()}"


def exact_dir(stage: str) -> Path:
    return RUN_ROOT / f"step02_delay_exactpos_{stage_path_suffix(stage)}"


def transport_run_dir(stage: str) -> Path:
    return RUN_ROOT / f"step02_delayed_transport_{stage_path_suffix(stage)}"


def report_dir(stage: str) -> Path:
    return TRANSPORT_DIR / "delayed" / BRANCH / STAT_LABEL / stage


def selected(values: tuple[str, ...], requested: str) -> list[str]:
    if requested == "all":
        return list(values)
    return [item.strip() for item in requested.split(",") if item.strip()]


def stage_triggers(raw_triggers: int) -> dict[str, int]:
    if STAT_LABEL == "fullstat_v1":
        return {"F1": int(raw_triggers)}
    mapping = {"delayed_syntax_S0": "S0", "delayed_quantitative_S1": "S1"}
    out: dict[str, int] = {}
    with SMOKE_MATRIX.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["branch"] != BRANCH or row["stage"] not in mapping:
                continue
            if row["geometry_setup"] != GEOMETRY:
                raise SystemExit(f"Delayed matrix geometry mismatch for {row['stage']}: {row['geometry_setup']}")
            out[mapping[row["stage"]]] = int(row["total_requested_events"])
    missing = sorted(set(mapping.values()) - set(out))
    if missing:
        raise SystemExit(f"Missing delayed stages in {SMOKE_MATRIX}: {missing}")
    return out


def enforce_fullstat_fix5_statistics(args: argparse.Namespace) -> None:
    if STAT_LABEL != "fullstat_v1":
        return
    expected = {
        "seed": FULLSTAT_FIX5_SEED,
        "raw_triggers": FULLSTAT_FIX5_RAW_TRIGGERS,
        "n_sample": FULLSTAT_FIX5_N_SAMPLE,
        "non_gamma_div": FULLSTAT_FIX5_NON_GAMMA_DIV,
    }
    actual = {
        "seed": int(args.seed),
        "raw_triggers": int(args.raw_triggers),
        "n_sample": int(args.n_sample),
        "non_gamma_div": int(args.non_gamma_div),
    }
    problems = [f"{key}={actual[key]} expected {value}" for key, value in expected.items() if actual[key] != value]
    if problems:
        raise SystemExit(
            "fullstat_v1 must match fix5_fullstat_v2_exactpos_m50000_s260613 statistics: "
            + "; ".join(problems)
        )


def require_prompt_buildup() -> None:
    for mode in ("instant", "buildup"):
        d = run_dir(mode)
        summary = d / "run_summary.json"
        if not summary.exists():
            raise SystemExit(f"Missing {mode} run summary: {summary}")
        rows = json.loads(summary.read_text(encoding="utf-8"))
        problems = [
            f"{mode} rows={len(rows)}" if len(rows) != 68 else "",
            f"{mode} non-pass jobs" if any(row.get("status") not in ("PASS", "SKIP") for row in rows) else "",
            f"{mode} sim_files={len(list(d.glob('*.sim.gz')))}" if len(list(d.glob("*.sim.gz"))) != 68 else "",
            f"{mode} dat_files={len(list(d.glob('*.dat.inc1.dat')))}"
            if len(list(d.glob("*.dat.inc1.dat"))) != 68
            else "",
        ]
        problems = [item for item in problems if item]
        if problems:
            raise SystemExit("; ".join(problems))


def run_cmd(cmd: list[str], log_path: Path | None = None) -> None:
    if log_path is None:
        subprocess.run(cmd, cwd=ROOT, check=True)
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        log.write("command=" + " ".join(cmd) + "\n")
        log.write("-" * 72 + "\n")
        proc = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=False)
        log.write("-" * 72 + "\n")
        log.write(f"returncode={proc.returncode}\n")
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd)


def build_raw_source(args: argparse.Namespace) -> dict[str, Any]:
    require_prompt_buildup()
    outdir = raw_source_dir()
    outdir.mkdir(parents=True, exist_ok=True)
    marker = outdir / "activation_decay_day15.source"
    cmd = [
        "python3",
        str(MAKE_RPIP),
        "--dat",
        str(run_dir("buildup") / "*.dat.inc1.dat"),
        "--sim",
        str(run_dir("buildup") / "*.inc1.id1.sim.gz"),
        "--geo",
        GEOMETRY,
        "--non-gamma-div",
        str(args.non_gamma_div),
        "--gamma-div",
        "auto",
        "--t-ground-days",
        "0",
        "--t-flight-days",
        "15",
        "--t-after-days",
        "0",
        "--outdir",
        str(outdir),
        "--outfile-prefix",
        str(outdir / f"DelayedDecayMassModel511Raw_{BRANCH}"),
        "--triggers",
        str(args.raw_triggers),
        "--z-bins",
        "60",
        "--r-bins",
        "100",
        "--n-sample",
        str(args.n_sample),
        "--workers",
        str(args.workers),
        "--nubase",
        str(NUBASE),
        "--seed",
        str(args.seed),
    ]
    if args.force or not marker.exists():
        run_cmd(cmd, outdir / "build_raw_source.log")
    return {
        "branch": BRANCH,
        "raw_source_dir": rel(outdir),
        "raw_source": rel(marker),
        "exists": marker.exists(),
        "log": rel(outdir / "build_raw_source.log"),
    }


def build_fixed_source(args: argparse.Namespace) -> dict[str, Any]:
    outdir = fix_dir()
    outdir.mkdir(parents=True, exist_ok=True)
    source = raw_source_dir() / "activation_decay_day15.source"
    marker = outdir / "activation_decay_day15_groundstate_fixed.source"
    cmd = [
        "python3",
        str(FIX_SOURCE),
        "--source",
        str(source),
        "--dat-glob",
        str(run_dir("buildup") / "*.dat.inc1.dat"),
        "--nubase",
        str(NUBASE),
        "--outdir",
        str(outdir),
        "--outfile-prefix",
        str(outdir / f"DelayedDecayMassModel511Fixed_{BRANCH}"),
        "--output-source-name",
        "activation_decay_day15_groundstate_fixed.source",
        "--triggers",
        str(args.raw_triggers),
        "--geometry",
        str(ROOT / GEOMETRY),
        "--non-gamma-div",
        str(args.non_gamma_div),
        "--gamma-div",
        "auto",
        "--t-flight-days",
        "15",
    ]
    if args.force or not marker.exists():
        run_cmd(cmd, outdir / "build_fixed_source.log")
    audit = outdir / "normalization_audit_groundstate_fix.json"
    summary = outdir / "source_fix_summary.json"
    data = json.loads(audit.read_text(encoding="utf-8")) if audit.exists() else {}
    return {
        "branch": BRANCH,
        "fix_dir": rel(outdir),
        "fixed_source": rel(marker),
        "source_fix_summary": rel(summary),
        "normalization_audit": rel(audit),
        "normalization_status": data.get("status"),
        "normalization_problems": data.get("problems", []),
        "log": rel(outdir / "build_fixed_source.log"),
    }


def configure_exactpos(stage: str) -> None:
    source_dir = exact_dir(stage)
    tdir = transport_run_dir(stage)
    source_dir.mkdir(parents=True, exist_ok=True)
    tdir.mkdir(parents=True, exist_ok=True)

    stage_token = source_stage_token(stage)
    exactpos.LABEL = f"Mass_model_511_{stage_path_suffix(stage)}"
    exactpos.REPORT_DIR = report_dir(stage)
    exactpos.INSTANT = run_dir("instant")
    exactpos.BUILDUP = run_dir("buildup")
    exactpos.RAW_SOURCE_DIR = raw_source_dir()
    exactpos.FIX = fix_dir()
    exactpos.FIXED_SOURCE = fix_dir() / "activation_decay_day15_groundstate_fixed.source"
    exactpos.FIX_SUMMARY = fix_dir() / "source_fix_summary.json"
    exactpos.FIX_AUDIT = fix_dir() / "normalization_audit_groundstate_fix.json"
    exactpos.SOURCE_DIR = source_dir
    exactpos.TRANSPORT_DIR = tdir
    exactpos.SOURCE_PREFIX = tdir / transport_prefix(stage)
    exactpos.SOURCE = source_dir / f"activation_decay_day15_groundstate_fixed_exactpos{stage_token}.source"
    exactpos.MANIFEST = source_dir / f"{stage_path_suffix(stage)}_exactpos_delayed_source_manifest.json"
    exactpos.WEIGHTED_TABLE = source_dir / f"exactpos_weighted_rpip_table{stage_token}.csv"
    exactpos.SUMMARY_JSON = exactpos.REPORT_DIR / "delayed_source_exactpos_summary.json"
    exactpos.SUMMARY_MD = exactpos.REPORT_DIR / "delayed_source_exactpos_summary.md"
    exactpos.GEOMETRY = ROOT / GEOMETRY


def build_exactpos_source(stage: str, triggers: int, args: argparse.Namespace) -> dict[str, Any]:
    configure_exactpos(stage)
    if args.force or not exactpos.SOURCE.exists():
        exactpos.build_source(M_BLOCKS, triggers, args.seed)
    summary = json.loads(exactpos.SUMMARY_JSON.read_text(encoding="utf-8"))
    return {
        "branch": BRANCH,
        "stage": stage,
        "source": rel(exactpos.SOURCE),
        "summary": rel(exactpos.SUMMARY_JSON),
        "manifest": rel(exactpos.MANIFEST),
        "weighted_table": rel(exactpos.WEIGHTED_TABLE),
        "status": summary.get("status"),
        "n_pointsource_blocks": summary.get("n_pointsource_blocks"),
        "triggers": triggers,
        "sampling_status": summary.get("sampling_audit", {}).get("status"),
        "sampling_problems": summary.get("sampling_audit", {}).get("problems", []),
    }


def run_transport(stage: str, args: argparse.Namespace) -> dict[str, Any]:
    configure_exactpos(stage)
    sim = exactpos.SOURCE_PREFIX.with_suffix(".inc1.id1.sim.gz")
    log = exactpos.TRANSPORT_DIR / f"cosima_{BRANCH}_{stage}.log"
    if args.force or not sim.exists():
        run_cmd([args.cosima, "-s", str(args.seed), str(exactpos.SOURCE)], log)
    manifest = exactpos.summarize_transport()
    transport = manifest.get("delayed_transport", {})
    return {
        "branch": BRANCH,
        "stage": stage,
        "status": manifest.get("status"),
        "source": rel(exactpos.SOURCE),
        "transport_sim": transport.get("path"),
        "SE": transport.get("SE"),
        "ID": transport.get("ID"),
        "TS": transport.get("TS"),
        "TE_s": transport.get("TE_s"),
        "geometry": transport.get("geometry"),
        "log": rel(log),
    }


def write_campaign_manifest(records: dict[str, Any], args: argparse.Namespace) -> None:
    transports = records.get("transports", [])
    pass_transport = bool(transports) and all(str(row.get("status", "")).startswith("PASS") for row in transports)
    payload = {
        "document_type": "mass_model_511_g3_g4_delayed_transport_campaign",
        "generated_at_utc": now_utc(),
        "status": "PASS_DELAYED_TRANSPORT" if pass_transport else "IN_PROGRESS_OR_PREPARED",
        "claim_boundary": (
            "Delayed source/transport artifact only. Detector delayed-rate claims require Step05 response, "
            "W/collimator audit, mission fold, and verifier approval."
        ),
        "source_authority_edited": False,
        "old_nearfield_engineering_edited": False,
        "branch": BRANCH,
        "stat_label": STAT_LABEL,
        "geometry": GEOMETRY,
        "m_pointsource_blocks": M_BLOCKS,
        "seed": args.seed,
        **records,
    }
    manifest_stem = f"delayed_transport_campaign_manifest_{path_suffix()}"
    branch_json = TRANSPORT_DIR / f"{manifest_stem}.json"
    branch_md = TRANSPORT_DIR / f"{manifest_stem}.md"
    write_json(branch_json, payload)
    lines = [
        "# Mass_model_511 Delayed Transport",
        "",
        f"- generated_at_utc: `{payload['generated_at_utc']}`",
        f"- status: `{payload['status']}`",
        f"- branch: `{BRANCH}`",
        f"- stat_label: `{STAT_LABEL}`",
        f"- geometry: `{GEOMETRY}`",
        f"- M point-source blocks: `{M_BLOCKS}`",
        f"- seed: `{args.seed}`",
        "",
        "| Stage | Source status | Transport status | Triggers | SE | ID | TE_s | Log |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    source_by_stage = {row["stage"]: row for row in records.get("exactpos_sources", [])}
    transport_by_stage = {row["stage"]: row for row in transports}
    for stage in records.get("stages", []):
        src = source_by_stage.get(stage, {})
        trn = transport_by_stage.get(stage, {})
        lines.append(
            f"| `{stage}` | `{src.get('status')}` | `{trn.get('status')}` | {src.get('triggers')} | "
            f"{trn.get('SE')} | {trn.get('ID')} | {trn.get('TE_s')} | `{trn.get('log')}` |"
        )
    lines.extend(["", "Boundary: this is not a detector-rate or no-effect claim."])
    branch_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    branch_payloads: dict[str, Any] = {path_suffix(): payload}
    legacy = TRANSPORT_DIR / "delayed_transport_campaign_manifest.json"
    if legacy.exists():
        try:
            old_payload = json.loads(legacy.read_text(encoding="utf-8"))
            old_branch = old_payload.get("branch")
            if old_branch and old_payload.get("document_type") == "mass_model_511_g3_g4_delayed_transport_campaign":
                old_stat = old_payload.get("stat_label", "smoke")
                old_key = f"{old_branch}_{old_stat}"
                branch_payloads.setdefault(str(old_key), old_payload)
                old_branch_json = TRANSPORT_DIR / f"delayed_transport_campaign_manifest_{old_branch}_{old_stat}.json"
                if not old_branch_json.exists():
                    write_json(old_branch_json, old_payload)
        except Exception:
            pass
    for path in sorted(TRANSPORT_DIR.glob("delayed_transport_campaign_manifest_*.json")):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        branch = row.get("branch")
        if branch:
            stat_label = row.get("stat_label", "smoke")
            branch_payloads[f"{branch}_{stat_label}"] = row

    aggregate = {
        "document_type": "mass_model_511_g3_g4_delayed_transport_campaign_aggregate",
        "generated_at_utc": now_utc(),
        "status": "PASS_DELAYED_TRANSPORT_ALL_AVAILABLE"
        if branch_payloads and all(str(row.get("status", "")).startswith("PASS") for row in branch_payloads.values())
        else "IN_PROGRESS_OR_PREPARED",
        "claim_boundary": payload["claim_boundary"],
        "source_authority_edited": False,
        "old_nearfield_engineering_edited": False,
        "branch_stat_labels": sorted(branch_payloads),
        "branch_manifests": {
            key: rel(TRANSPORT_DIR / f"delayed_transport_campaign_manifest_{key}.json")
            for key in sorted(branch_payloads)
        },
        "branch_payloads": branch_payloads,
    }
    write_json(legacy, aggregate)
    agg_lines = [
        "# Mass_model_511 Delayed Transport Aggregate",
        "",
        f"- generated_at_utc: `{aggregate['generated_at_utc']}`",
        f"- status: `{aggregate['status']}`",
        "",
        "| Branch/stat label | Status | Manifest |",
        "| --- | --- | --- |",
    ]
    for branch in sorted(branch_payloads):
        agg_lines.append(
            f"| `{branch}` | `{branch_payloads[branch].get('status')}` | `{aggregate['branch_manifests'][branch]}` |"
        )
    agg_lines.extend(["", "Boundary: this is not a detector-rate or no-effect claim."])
    (TRANSPORT_DIR / "delayed_transport_campaign_manifest.md").write_text(
        "\n".join(agg_lines) + "\n", encoding="utf-8"
    )


def main() -> int:
    default_cosima = shutil.which("cosima") or COSIMA
    ap = argparse.ArgumentParser()
    ap.add_argument("--branch", choices=sorted(BRANCH_GEOMETRY), default=CANDIDATE_BRANCH)
    ap.add_argument("--stat-label", choices=("smoke", "fullstat_v1"), default="smoke")
    ap.add_argument("--stages", default="all", help="all or comma list: smoke uses S0,S1; fullstat_v1 uses F1")
    ap.add_argument("--prepare-source", action="store_true")
    ap.add_argument("--run-transport", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--cosima", default=default_cosima)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--non-gamma-div", type=int, default=8)
    ap.add_argument("--raw-triggers", type=int, default=1_000_000)
    ap.add_argument("--n-sample", type=int, default=2_000_000)
    args = ap.parse_args()
    set_branch(args.branch)
    set_stat_label(args.stat_label)
    enforce_fullstat_fix5_statistics(args)
    if not args.prepare_source and not args.run_transport:
        args.prepare_source = True

    triggers_by_stage = stage_triggers(args.raw_triggers)
    stages = selected(tuple(sorted(triggers_by_stage)), args.stages)
    bad_stages = sorted(set(stages) - set(triggers_by_stage))
    if bad_stages:
        raise SystemExit(f"Unknown stages: {bad_stages}")

    records: dict[str, Any] = {
        "stages": stages,
        "raw_sources": [],
        "fixed_sources": [],
        "exactpos_sources": [],
        "transports": [],
    }
    if args.prepare_source:
        records["raw_sources"].append(build_raw_source(args))
        records["fixed_sources"].append(build_fixed_source(args))
        for stage in stages:
            records["exactpos_sources"].append(build_exactpos_source(stage, triggers_by_stage[stage], args))
    if args.run_transport:
        for stage in stages:
            records["transports"].append(run_transport(stage, args))
    write_campaign_manifest(records, args)
    print(json.dumps(records, indent=2, ensure_ascii=False))
    transports = records["transports"]
    return 0 if not transports or all(str(row.get("status", "")).startswith("PASS") for row in transports) else 2


if __name__ == "__main__":
    raise SystemExit(main())
