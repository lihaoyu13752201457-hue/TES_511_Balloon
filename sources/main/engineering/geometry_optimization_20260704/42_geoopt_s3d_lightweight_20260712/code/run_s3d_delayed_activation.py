#!/usr/bin/env python3
"""Prepare and run the S3d-O9 full-prompt and neutron delayed chain.

The retained S3c products are read-only templates/provenance.  Every generated
source card, run manifest, transport file, and audit is written to a new S3d
path.  Heavy transport is impossible unless ``--allow-heavy-run`` is supplied.

Production contract
-------------------
* prompt authority: all eight prompt families, gamma split 12, seven other
  families with eight replicas (68 jobs total);
* delayed activation driver: neutron only, eight buildup replicas;
* RPIP normalization: TT divided by eight for the neutron family;
* raw inventory: N_SAMPLE=2,000,000 and 1,000,000 requested triggers;
* fixed inventory: NUBASE-2020 ground-state correction;
* exact source: M=50,000, seed=260613, exact RPIP positions;
* delayed transport: SE=ID=1,000,000 and the S3d geometry in the SIM header.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import re
import shlex
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _s3d_replay_common import audit_geometry_authority, cosima_environment


ROOT = Path(__file__).resolve().parents[4]
WORK = Path(__file__).resolve().parents[1]
DATA = WORK / "data"
CONFIG = WORK / "config/full_prompt_all8"
SOURCE_CARDS = CONFIG / "source_cards"
LOGS = WORK / "logs/fullchain_delayed"

GEOMETRY_REL = (
    "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/geometry/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
GEOMETRY = ROOT / GEOMETRY_REL
GEOMETRY_MANIFEST = DATA / "s3d_geometry_manifest.json"
TEMPLATE_SOURCE_DIR = (
    ROOT
    / "engineering/geometry_optimization_20260704/32_s3c_dominant_backgrounds_20260709/source_cards"
)

RUN_ROOT = ROOT / "runs/geometry_optimization_20260704"
FULL_PROMPT_LABEL = "s3d_o9_fullstat_prompt_all8_20260712"
FULL_PROMPT_DIR = RUN_ROOT / FULL_PROMPT_LABEL
DELAY_LABEL = "s3d_o9_neutron_delayed_m50000_20260712"
INSTANT_DIR = RUN_ROOT / f"step02_instant_{DELAY_LABEL}"
BUILDUP_DIR = RUN_ROOT / f"step02_buildup_{DELAY_LABEL}"
RAW_DIR = RUN_ROOT / f"step02_decay_source_{DELAY_LABEL}"
FIX_DIR = RUN_ROOT / f"step02_delay_fix_{DELAY_LABEL}"
EXACT_DIR = RUN_ROOT / f"step02_delay_exactpos_{DELAY_LABEL}"
DELAYED_TRANSPORT_DIR = RUN_ROOT / f"step02_delayed_transport_{DELAY_LABEL}"
DELAYED_REPORT_DIR = WORK / "fullchain/delayed_source"
CAMPAIGN_MANIFEST = DATA / "s3d_delayed_activation_campaign.json"
PREPARED_AUDIT = DATA / "s3d_full_prompt_and_delayed_preflight.json"

RUN_EQUIV = ROOT / "code/tools/run_equiv2602_pipeline_NEW_GEO.py"
MAKE_RPIP = ROOT / "code/tools/makedecaysourcewithplot_rpip.py"
FIX_SOURCE = ROOT / "code/tools/build_fixed_delay_source.py"
EXACTPOS_HELPER = ROOT / "code/tools/build_fix5_1of10_exactpos_delayed_source.py"
NUBASE = ROOT / "inputs/nubase/nubase_2020.txt"
ALL_TAGS = ("alpha", "eminus", "eplus", "gamma", "muminus", "muplus", "n", "p")
GAMMA_EVENTS = 10_000_000
GAMMA_SPLITS = 12
NON_GAMMA_REPLICAS = 8
NON_GAMMA_DIV = 8
FARFIELD_RADIUS_CM = 60.0
N_SAMPLE = 2_000_000
RAW_TRIGGERS = 1_000_000
M_BLOCKS = 50_000
SEED = 260613
SOURCE_PREFIX = DELAYED_TRANSPORT_DIR / "DelayedDecayS3dO9NeutronM50000"

GEOMETRY_LINE_RE = re.compile(r"^\s*Geometry\s+(.+?)\s*$")
GEOMETRY_COMMENT_RE = re.compile(r"^\s*#\s*geometry_setup\s*=.*$")
FLUX_RE = re.compile(r"\.Flux\s+([-+0-9.eE]+)\s*$")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_path(value: str | Path | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    path = Path(str(value).strip())
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve().as_posix()


def geometry_matches(value: str | Path | None) -> bool:
    return normalize_path(value) == GEOMETRY.resolve().as_posix()


def source_geometry(path: Path) -> list[str]:
    values: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = GEOMETRY_LINE_RE.match(raw)
        if match:
            values.append(match.group(1).strip())
    return values


def source_flux(path: Path) -> float:
    total = 0.0
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = FLUX_RE.search(raw)
        if match:
            total += float(match.group(1))
    return total


def canonical_source_text(text: str) -> str:
    out: list[str] = []
    for raw in text.splitlines():
        if GEOMETRY_LINE_RE.match(raw):
            out.append("Geometry <GEOMETRY>")
        elif GEOMETRY_COMMENT_RE.match(raw):
            out.append("# geometry_setup=<GEOMETRY>")
        else:
            out.append(raw)
    return "\n".join(out).rstrip() + "\n"


def migrate_source_cards() -> dict[str, Any]:
    SOURCE_CARDS.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    problems: list[str] = []
    for tag in ALL_TAGS:
        src = TEMPLATE_SOURCE_DIR / f"Background_{tag}_fullsphere20.source"
        dst = SOURCE_CARDS / src.name
        if not src.exists():
            problems.append(f"missing template source: {rel(src)}")
            continue
        src_text = src.read_text(encoding="utf-8", errors="replace")
        lines: list[str] = []
        geometry_count = 0
        comment_count = 0
        for raw in src_text.splitlines():
            if GEOMETRY_LINE_RE.match(raw):
                lines.append(f"Geometry {GEOMETRY_REL}")
                geometry_count += 1
            elif GEOMETRY_COMMENT_RE.match(raw):
                lines.append(f"# geometry_setup={GEOMETRY_REL}")
                comment_count += 1
            else:
                lines.append(raw)
        dst_text = "\n".join(lines).rstrip() + "\n"
        dst.write_text(dst_text, encoding="utf-8")
        card_problems: list[str] = []
        if geometry_count != 1:
            card_problems.append(f"geometry_line_count={geometry_count}")
        if source_geometry(dst) != [GEOMETRY_REL]:
            card_problems.append(f"geometry_lines={source_geometry(dst)}")
        if canonical_source_text(src_text) != canonical_source_text(dst_text):
            card_problems.append("non_geometry_text_changed")
        if "29_geoopt_s3c" in dst_text or "S3C_BGO" in " ".join(source_geometry(dst)):
            card_problems.append("stale_s3c_geometry_reference")
        rows.append(
            {
                "particle": tag,
                "source": rel(dst),
                "template_source": rel(src),
                "geometry_lines": source_geometry(dst),
                "geometry_line_count": geometry_count,
                "geometry_comment_count": comment_count,
                "total_flux_cm2_s": source_flux(dst),
                "template_sha256": sha256(src),
                "source_sha256": sha256(dst),
                "canonical_non_geometry_match": not card_problems,
                "problems": card_problems,
            }
        )
        problems.extend(f"{tag}: {item}" for item in card_problems)

    payload = {
        "status": "PASS_S3D_O9_ALL8_SOURCE_CARDS" if not problems and len(rows) == 8 else "FAIL_S3D_O9_ALL8_SOURCE_CARDS",
        "generated_at_utc": now_utc(),
        "label": FULL_PROMPT_LABEL,
        "geometry_setup": GEOMETRY_REL,
        "geometry_manifest": rel(GEOMETRY_MANIFEST),
        "geometry_status": "S3d O9: uniform 30 mm BGO, no outer W, retained 3 mm Al/Kapton and unchanged inner detector",
        "farfield_radius_cm": FARFIELD_RADIUS_CM,
        "pointing_policy": "unchanged 20-bin full-sphere source cards; only geometry metadata repointed",
        "source_dir": rel(SOURCE_CARDS),
        "template_source_dir": rel(TEMPLATE_SOURCE_DIR),
        "statistics_reference": "10M gamma, 12 gamma splits, 8 replicas per non-gamma family",
        "sources": rows,
        "problems": problems,
    }
    write_json(SOURCE_CARDS / "source_migration_manifest.json", payload)
    if problems:
        raise SystemExit("source migration failed: " + "; ".join(problems))
    return payload


def run_command(cmd: list[str], log_path: Path, env: dict[str, str] | None = None) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as handle:
        handle.write("command=" + shlex.join(cmd) + "\n")
        handle.write("-" * 72 + "\n")
        proc = subprocess.run(cmd, cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT, check=False)
        handle.write("-" * 72 + "\n")
        handle.write(f"returncode={proc.returncode}\n")
    if proc.returncode != 0:
        raise RuntimeError(f"command failed ({proc.returncode}); see {rel(log_path)}")


def equiv_command(mode: str, outdir: Path, workers: int, particles: str = "") -> list[str]:
    cmd = [
        sys.executable,
        str(RUN_EQUIV),
        "--mode",
        mode,
        "--source-dir",
        str(SOURCE_CARDS),
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
    ]
    if particles:
        cmd.extend(["--particles", particles])
    return cmd


def prepare_job_sources(workers: int) -> None:
    for mode, outdir, particles, name in (
        ("instant", FULL_PROMPT_DIR, "", "prepare_full_prompt_all8.log"),
        ("buildup", BUILDUP_DIR, "n", "prepare_neutron_buildup.log"),
    ):
        cmd = equiv_command(mode, outdir, workers, particles)
        cmd.append("--prepare-sources-only")
        run_command(cmd, LOGS / name)


def read_manifest_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def inspect_prepared_jobs() -> dict[str, Any]:
    geometry_authority = audit_geometry_authority()
    _env, megalib_evidence = cosima_environment()
    problems: list[str] = []
    summaries: dict[str, Any] = {}
    for name, run_dir, expected_jobs, mode in (
        ("full_prompt", FULL_PROMPT_DIR, 68, "instant"),
        ("neutron_buildup", BUILDUP_DIR, 8, "buildup"),
    ):
        manifest = run_dir / "run_manifest.csv"
        norm_path = run_dir / "normalization.json"
        rows = read_manifest_csv(manifest) if manifest.exists() else []
        norm = load_json(norm_path) if norm_path.exists() else {}
        item_problems: list[str] = []
        if len(rows) != expected_jobs:
            item_problems.append(f"job_count={len(rows)} expected={expected_jobs}")
        counts = Counter(row.get("particle", "") for row in rows)
        expected_counts = {"gamma": 12, **{tag: 8 for tag in ALL_TAGS if tag != "gamma"}} if name == "full_prompt" else {"n": 8}
        if dict(counts) != expected_counts:
            item_problems.append(f"particle_counts={dict(counts)} expected={expected_counts}")
        seeds = [row.get("seed") for row in rows]
        if len(set(seeds)) != len(seeds):
            item_problems.append("non_unique_job_seeds")
        source_checks: list[dict[str, Any]] = []
        for row in rows:
            temp = Path(row["temp_source"])
            if not temp.is_absolute():
                temp = ROOT / temp
            text = temp.read_text(encoding="utf-8", errors="replace") if temp.exists() else ""
            geoms = source_geometry(temp) if temp.exists() else []
            has_store = "StoreIsotopes true" in text
            has_buildup = "DecayMode ActivationBuildUp" in text
            ok = temp.exists() and len(geoms) == 1 and geometry_matches(geoms[0]) and has_store
            ok = ok and (has_buildup if mode == "buildup" else not has_buildup)
            if not ok:
                item_problems.append(f"prepared_source_invalid={row.get('job_name')}")
            source_checks.append(
                {
                    "job_name": row.get("job_name"),
                    "particle": row.get("particle"),
                    "source": rel(temp),
                    "geometry": geoms[0] if len(geoms) == 1 else geoms,
                    "store_isotopes": has_store,
                    "activation_buildup": has_buildup,
                    "status": "PASS" if ok else "FAIL",
                }
            )
        summaries[name] = {
            "run_dir": rel(run_dir),
            "manifest": rel(manifest),
            "normalization": rel(norm_path),
            "job_count": len(rows),
            "particle_counts": dict(counts),
            "normalization_selected_particles": norm.get("selected_particles"),
            "source_checks": source_checks,
            "problems": item_problems,
        }
        problems.extend(f"{name}: {value}" for value in item_problems)

    payload = {
        "status": "PASS_S3D_O9_FULL_PROMPT_DELAYED_PREFLIGHT" if not problems else "FAIL_S3D_O9_FULL_PROMPT_DELAYED_PREFLIGHT",
        "generated_at_utc": now_utc(),
        "geometry_setup": GEOMETRY_REL,
        "geometry_authority": geometry_authority,
        "megalib_environment": megalib_evidence,
        "statistics": {
            "full_prompt_jobs": 68,
            "gamma_events": GAMMA_EVENTS,
            "gamma_splits": GAMMA_SPLITS,
            "non_gamma_replicas": NON_GAMMA_REPLICAS,
            "neutron_buildup_jobs": 8,
            "non_gamma_tt_division": NON_GAMMA_DIV,
            "n_sample": N_SAMPLE,
            "raw_triggers": RAW_TRIGGERS,
            "m_exact_pointsource_blocks": M_BLOCKS,
            "seed": SEED,
        },
        "runs": summaries,
        "problems": problems,
    }
    write_json(PREPARED_AUDIT, payload)
    if problems:
        raise SystemExit("prepared-job audit failed: " + "; ".join(problems))
    return payload


def run_equiv_transport(mode: str, outdir: Path, workers: int, particles: str, force: bool) -> None:
    env, evidence = cosima_environment()
    cmd = equiv_command(mode, outdir, workers, particles)
    cmd.extend(["--cosima", evidence["cosima"]])
    cmd.append("--allow-heavy-run")
    if force:
        cmd.append("--force")
    run_command(cmd, LOGS / ("run_full_prompt_all8.log" if mode == "instant" else "run_neutron_buildup.log"), env)


def open_text(path: Path):
    return gzip.open(path, "rt", encoding="utf-8", errors="ignore") if path.suffix == ".gz" else path.open("r", encoding="utf-8", errors="ignore")


def sim_header(path: Path, count_events: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {"path": rel(path), "exists": path.exists(), "geometry": None, "SE": 0, "ID": 0, "TS": 0, "TE_s": None}
    if not path.exists():
        return out
    with open_text(path) as handle:
        for raw in handle:
            if raw.startswith("Geometry"):
                parts = raw.split(None, 1)
                out["geometry"] = parts[1].strip() if len(parts) == 2 else ""
            elif count_events and raw.startswith("SE"):
                out["SE"] += 1
            elif count_events and raw.startswith("ID "):
                out["ID"] += 1
            elif count_events and raw.startswith("TS"):
                out["TS"] += 1
            elif count_events and raw.startswith("TE "):
                parts = raw.split()
                if len(parts) > 1:
                    try:
                        out["TE_s"] = float(parts[1])
                    except ValueError:
                        pass
            if not count_events and out["geometry"]:
                break
    out["geometry_match"] = geometry_matches(out["geometry"])
    return out


def tt_line_count(path: Path) -> int:
    return sum(1 for raw in path.read_text(encoding="utf-8", errors="replace").splitlines() if raw.startswith("TT "))


def assemble_instant_neutron() -> dict[str, Any]:
    source_summary = FULL_PROMPT_DIR / "run_summary.json"
    source_norm = FULL_PROMPT_DIR / "normalization.json"
    if not source_summary.exists() or not source_norm.exists():
        raise SystemExit("full prompt run is not complete; cannot assemble neutron instant provenance")
    rows = [dict(row) for row in load_json(source_summary) if row.get("particle") == "n"]
    problems: list[str] = []
    if len(rows) != 8:
        problems.append(f"neutron_rows={len(rows)}")
    headers: list[dict[str, Any]] = []
    for row in rows:
        sim = ROOT / row["sim_path"] if not Path(row["sim_path"]).is_absolute() else Path(row["sim_path"])
        dat = ROOT / row["dat_path"] if not Path(row["dat_path"]).is_absolute() else Path(row["dat_path"])
        header = sim_header(sim)
        headers.append({"job_name": row.get("job_name"), **header})
        if row.get("status") not in ("PASS", "SKIP"):
            problems.append(f"{row.get('job_name')}: status={row.get('status')}")
        if int(row.get("generated_particles") or 0) != int(row.get("events") or 0):
            problems.append(f"{row.get('job_name')}: generated mismatch")
        if not header.get("geometry_match"):
            problems.append(f"{row.get('job_name')}: wrong SIM geometry")
        if not dat.exists() or tt_line_count(dat) != 1:
            problems.append(f"{row.get('job_name')}: dat/TT invalid")
        row["details"] = f"{row.get('details', '')}; assembled_from={rel(FULL_PROMPT_DIR)}"
        row["sim_header_geometry"] = header.get("geometry")
        row["sim_header_geometry_ok"] = header.get("geometry_match")

    norm = load_json(source_norm)
    assembled_norm = dict(norm)
    assembled_norm.update(
        {
            "outdir": rel(INSTANT_DIR),
            "selected_particles": ["n"],
            "jobs": len(rows),
            "assembled_from_existing_full_prompt_run": rel(FULL_PROMPT_DIR),
            "neutron_delay_scope": "instant provenance only; delayed inventory uses independent neutron ActivationBuildUp transport",
        }
    )
    INSTANT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(INSTANT_DIR / "run_summary.json", rows)
    write_json(INSTANT_DIR / "normalization.json", assembled_norm)
    with (INSTANT_DIR / "run_summary.csv").open("w", encoding="utf-8", newline="") as handle:
        fields = list(rows[0]) if rows else ["job_name"]
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    payload = {
        "status": "PASS_S3D_O9_NEUTRON_INSTANT_PROVENANCE" if not problems else "FAIL_S3D_O9_NEUTRON_INSTANT_PROVENANCE",
        "generated_at_utc": now_utc(),
        "source_full_prompt_run": rel(FULL_PROMPT_DIR),
        "instant_dir": rel(INSTANT_DIR),
        "rows": len(rows),
        "events_requested": sum(int(row.get("events") or 0) for row in rows),
        "events_generated": sum(int(row.get("generated_particles") or 0) for row in rows),
        "geometry_setup": GEOMETRY_REL,
        "sim_headers": headers,
        "problems": problems,
    }
    write_json(INSTANT_DIR / "assembled_instant_manifest.json", payload)
    if problems:
        raise SystemExit("instant provenance audit failed: " + "; ".join(problems))
    return payload


def validate_neutron_buildup() -> dict[str, Any]:
    summary = BUILDUP_DIR / "run_summary.json"
    norm = BUILDUP_DIR / "normalization.json"
    problems: list[str] = []
    rows = load_json(summary) if summary.exists() else []
    normalization = load_json(norm) if norm.exists() else {}
    headers: list[dict[str, Any]] = []
    if len(rows) != 8 or any(row.get("particle") != "n" for row in rows):
        problems.append(f"expected 8 neutron rows, found {len(rows)}")
    for row in rows:
        sim = ROOT / row["sim_path"] if not Path(row["sim_path"]).is_absolute() else Path(row["sim_path"])
        dat = ROOT / row["dat_path"] if not Path(row["dat_path"]).is_absolute() else Path(row["dat_path"])
        header = sim_header(sim)
        headers.append({"job_name": row.get("job_name"), **header})
        if row.get("status") not in ("PASS", "SKIP"):
            problems.append(f"{row.get('job_name')}: status={row.get('status')}")
        if int(row.get("generated_particles") or 0) != int(row.get("events") or 0):
            problems.append(f"{row.get('job_name')}: generated mismatch")
        if not header.get("geometry_match"):
            problems.append(f"{row.get('job_name')}: wrong SIM geometry")
        if not dat.exists() or tt_line_count(dat) != 1:
            problems.append(f"{row.get('job_name')}: dat/TT invalid")
    return {
        "status": "PASS" if not problems else "FAIL",
        "run_dir": rel(BUILDUP_DIR),
        "jobs": len(rows),
        "events_requested": sum(int(row.get("events") or 0) for row in rows),
        "events_generated": sum(int(row.get("generated_particles") or 0) for row in rows),
        "normalization": normalization,
        "sim_headers": headers,
        "problems": problems,
    }


def build_raw_source(workers: int, force: bool) -> dict[str, Any]:
    buildup = validate_neutron_buildup()
    if buildup["status"] != "PASS":
        raise SystemExit("neutron buildup is not ready: " + "; ".join(buildup["problems"]))
    marker = RAW_DIR / "activation_decay_day15.source"
    if force or not marker.exists():
        cmd = [
            sys.executable,
            str(MAKE_RPIP),
            "--dat",
            str(BUILDUP_DIR / "*.dat.inc1.dat"),
            "--sim",
            str(BUILDUP_DIR / "*.inc1.id1.sim.gz"),
            "--geo",
            GEOMETRY_REL,
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
            str(RAW_DIR / f"DelayedDecayRaw_{DELAY_LABEL}"),
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
        run_command(cmd, LOGS / "build_raw_neutron_delayed_source.log")
    return {"raw_source": rel(marker), "exists": marker.exists(), "n_sample": N_SAMPLE, "triggers": RAW_TRIGGERS}


def build_fixed_source(force: bool) -> dict[str, Any]:
    marker = FIX_DIR / "activation_decay_day15_groundstate_fixed.source"
    if force or not marker.exists():
        cmd = [
            sys.executable,
            str(FIX_SOURCE),
            "--source",
            str(RAW_DIR / "activation_decay_day15.source"),
            "--dat-glob",
            str(BUILDUP_DIR / "*.dat.inc1.dat"),
            "--nubase",
            str(NUBASE),
            "--outdir",
            str(FIX_DIR),
            "--outfile-prefix",
            str(FIX_DIR / f"DelayedDecayFixed_{DELAY_LABEL}"),
            "--output-source-name",
            marker.name,
            "--triggers",
            str(RAW_TRIGGERS),
            "--geometry",
            str(GEOMETRY),
            "--non-gamma-div",
            str(NON_GAMMA_DIV),
            "--gamma-div",
            "auto",
            "--t-flight-days",
            "15",
        ]
        run_command(cmd, LOGS / "build_fixed_neutron_delayed_source.log")
    audit_path = FIX_DIR / "normalization_audit_groundstate_fix.json"
    summary_path = FIX_DIR / "source_fix_summary.json"
    audit = load_json(audit_path) if audit_path.exists() else {}
    summary = load_json(summary_path) if summary_path.exists() else {}
    problems = list(audit.get("problems") or [])
    rows = audit.get("rows") or []
    if audit.get("status") != "PASS":
        problems.append(f"normalization_status={audit.get('status')}")
    if len(rows) != 1 or rows[0].get("tag") != "n":
        problems.append(f"normalization_rows={rows}")
    elif any(
        float(rows[0].get(key, -1)) != expected
        for key, expected in (("files", 8), ("division", 8.0), ("tt_count", 8), ("tt_files", 8), ("tt_line_count", 8))
    ):
        problems.append(f"TT/division guard failed: {rows[0]}")
    if not marker.exists() or source_geometry(marker) != [GEOMETRY.resolve().as_posix()]:
        problems.append("fixed source missing or wrong geometry")
    result = {
        "status": "PASS" if not problems else "FAIL",
        "fixed_source": rel(marker),
        "normalization_audit": rel(audit_path),
        "source_fix_summary": rel(summary_path),
        "new_total_activity_Bq": summary.get("new_total_activity_Bq"),
        "source_blocks_in": summary.get("source_blocks_in"),
        "source_blocks_removed": summary.get("source_blocks_removed"),
        "nubase": rel(NUBASE),
        "nubase_sha256": sha256(NUBASE) if NUBASE.exists() else None,
        "tt_division_rows": rows,
        "problems": problems,
    }
    if problems:
        raise SystemExit("ground-state/TT audit failed: " + "; ".join(problems))
    return result


def load_exactpos():
    spec = importlib.util.spec_from_file_location("s3d_o9_exactpos_helper", EXACTPOS_HELPER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load exact-position helper: {EXACTPOS_HELPER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def configure_exactpos(module: Any) -> None:
    EXACT_DIR.mkdir(parents=True, exist_ok=True)
    DELAYED_TRANSPORT_DIR.mkdir(parents=True, exist_ok=True)
    DELAYED_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    module.LABEL = f"{DELAY_LABEL}_exactpos_m50000_s{SEED}"
    module.REPORT_DIR = DELAYED_REPORT_DIR
    module.INSTANT = INSTANT_DIR
    module.BUILDUP = BUILDUP_DIR
    module.RAW_SOURCE_DIR = RAW_DIR
    module.FIX = FIX_DIR
    module.FIXED_SOURCE = FIX_DIR / "activation_decay_day15_groundstate_fixed.source"
    module.FIX_SUMMARY = FIX_DIR / "source_fix_summary.json"
    module.FIX_AUDIT = FIX_DIR / "normalization_audit_groundstate_fix.json"
    module.SOURCE_DIR = EXACT_DIR
    module.TRANSPORT_DIR = DELAYED_TRANSPORT_DIR
    module.SOURCE_PREFIX = SOURCE_PREFIX
    module.SOURCE = EXACT_DIR / "activation_decay_day15_groundstate_fixed_exactpos_m50000.source"
    module.MANIFEST = EXACT_DIR / f"{DELAY_LABEL}_exactpos_m50000_s{SEED}_delayed_source_manifest.json"
    module.WEIGHTED_TABLE = EXACT_DIR / f"exactpos_weighted_rpip_table_m50000_s{SEED}.csv"
    module.SUMMARY_JSON = DELAYED_REPORT_DIR / "delayed_source_exactpos_summary.json"
    module.SUMMARY_MD = DELAYED_REPORT_DIR / "delayed_source_exactpos_summary.md"
    module.GEOMETRY = GEOMETRY


def correct_exactpos_boundary(module: Any, manifest: dict[str, Any], transport: dict[str, Any] | None) -> dict[str, Any]:
    manifest["boundary"] = [
        "The exact-position source uses the S3d-O9 neutron-only eight-replica buildup and day-15 NUBASE ground-state-corrected activity.",
        "It is a transport artifact, not a detector-selected rate authority until Step05 and Step06-Step08 are complete.",
        f"Sampling uses M={M_BLOCKS}, seed={SEED}, N_SAMPLE={N_SAMPLE}, raw triggers={RAW_TRIGGERS}, and neutron TT division={NON_GAMMA_DIV}.",
    ]
    manifest["provenance_contract"] = {
        "geometry_setup": GEOMETRY_REL,
        "full_prompt_instant": rel(FULL_PROMPT_DIR),
        "assembled_neutron_instant": rel(INSTANT_DIR),
        "neutron_buildup": rel(BUILDUP_DIR),
        "nubase": rel(NUBASE),
        "nubase_sha256": sha256(NUBASE),
        "non_gamma_div": NON_GAMMA_DIV,
        "n_sample": N_SAMPLE,
        "raw_triggers": RAW_TRIGGERS,
        "m_pointsource_blocks": M_BLOCKS,
        "seed": SEED,
    }
    module.write_json(module.MANIFEST, manifest)
    module.write_summary(manifest, transport)
    return manifest


def build_exactpos_source(force: bool) -> dict[str, Any]:
    assemble_instant_neutron()
    fixed = build_fixed_source(force=False)
    if fixed["status"] != "PASS":
        raise SystemExit("fixed source is not ready")
    module = load_exactpos()
    configure_exactpos(module)
    if force or not module.SOURCE.exists():
        manifest = module.build_source(M_BLOCKS, RAW_TRIGGERS, SEED)
    else:
        manifest = load_json(module.MANIFEST)
    manifest = correct_exactpos_boundary(module, manifest, manifest.get("delayed_transport"))
    audit = validate_exactpos(module, require_transport=False)
    if audit["status"] != "PASS":
        raise SystemExit("exact-position audit failed: " + "; ".join(audit["problems"]))
    return audit


def validate_exactpos(module: Any | None = None, require_transport: bool = False) -> dict[str, Any]:
    module = module or load_exactpos()
    configure_exactpos(module)
    problems: list[str] = []
    manifest = load_json(module.MANIFEST) if module.MANIFEST.exists() else {}
    summary = load_json(module.SUMMARY_JSON) if module.SUMMARY_JSON.exists() else {}
    source_text = module.SOURCE.read_text(encoding="utf-8", errors="replace") if module.SOURCE.exists() else ""
    if not module.SOURCE.exists():
        problems.append("missing exact-position source")
    if source_geometry(module.SOURCE) != [GEOMETRY_REL] if module.SOURCE.exists() else True:
        problems.append("exact-position source geometry mismatch")
    if f"DecayRun.Triggers {RAW_TRIGGERS}" not in source_text:
        problems.append("exact-position trigger count mismatch")
    if source_text.count(".ParticleType ") != M_BLOCKS or source_text.count(".Beam PointSource ") != M_BLOCKS:
        problems.append("exact-position PointSource block count mismatch")
    if manifest.get("n_pointsource_blocks") != M_BLOCKS or manifest.get("seed") != SEED:
        problems.append("exact-position manifest M/seed mismatch")
    sampling = manifest.get("sampling_audit") or summary.get("sampling_audit") or {}
    if sampling.get("status") != "PASS" or sampling.get("problems"):
        problems.append(f"sampling audit={sampling.get('status')} problems={sampling.get('problems')}")
    if float(sampling.get("matched_back_to_exact_table_fraction", 0.0)) != 1.0:
        problems.append("sampled points do not fully map to the weighted table")
    weighted_rows: list[dict[str, str]] = []
    if module.WEIGHTED_TABLE.exists():
        with module.WEIGHTED_TABLE.open("r", encoding="utf-8", newline="") as handle:
            weighted_rows = list(csv.DictReader(handle))
    if not weighted_rows:
        problems.append("empty exact-position weighted table")
    bad_source_sims = [row.get("source_sim", "") for row in weighted_rows if rel(BUILDUP_DIR) not in row.get("source_sim", "")]
    if bad_source_sims:
        problems.append(f"weighted-table source provenance mismatch: {bad_source_sims[:3]}")
    stale = [row for row in weighted_rows if "29_geoopt_s3c" in row.get("source_sim", "")]
    if stale:
        problems.append("weighted table contains stale S3c transport paths")
    transport = manifest.get("delayed_transport") or summary.get("delayed_transport") or {}
    if require_transport:
        if transport.get("SE") != RAW_TRIGGERS or transport.get("ID") != RAW_TRIGGERS:
            problems.append(f"delayed SE/ID={transport.get('SE')}/{transport.get('ID')}")
        if not geometry_matches(transport.get("geometry")):
            problems.append("delayed SIM geometry mismatch")
        if not str(manifest.get("status", "")).startswith("PASS"):
            problems.append(f"delayed manifest status={manifest.get('status')}")
    return {
        "status": "PASS" if not problems else "FAIL",
        "source": rel(module.SOURCE),
        "manifest": rel(module.MANIFEST),
        "summary": rel(module.SUMMARY_JSON),
        "weighted_table": rel(module.WEIGHTED_TABLE),
        "weighted_rows": len(weighted_rows),
        "m_pointsource_blocks": manifest.get("n_pointsource_blocks"),
        "seed": manifest.get("seed"),
        "sampling_status": sampling.get("status"),
        "transport": transport,
        "problems": problems,
    }


def run_delayed_transport(force: bool) -> dict[str, Any]:
    module = load_exactpos()
    configure_exactpos(module)
    validate = validate_exactpos(module, require_transport=False)
    if validate["status"] != "PASS":
        raise SystemExit("exact-position source is not ready: " + "; ".join(validate["problems"]))
    sim = SOURCE_PREFIX.with_suffix(".inc1.id1.sim.gz")
    if force or not sim.exists():
        env, evidence = cosima_environment()
        run_command([evidence["cosima"], "-s", str(SEED), str(module.SOURCE)], LOGS / "run_neutron_delayed_transport.log", env)
    manifest = module.summarize_transport()
    manifest = correct_exactpos_boundary(module, manifest, manifest.get("delayed_transport"))
    audit = validate_exactpos(module, require_transport=True)
    if audit["status"] != "PASS":
        raise SystemExit("delayed transport audit failed: " + "; ".join(audit["problems"]))
    return audit


def current_status() -> dict[str, Any]:
    source_manifest = load_json(SOURCE_CARDS / "source_migration_manifest.json") if (SOURCE_CARDS / "source_migration_manifest.json").exists() else {}
    prepared = load_json(PREPARED_AUDIT) if PREPARED_AUDIT.exists() else {}
    assembled = load_json(INSTANT_DIR / "assembled_instant_manifest.json") if (INSTANT_DIR / "assembled_instant_manifest.json").exists() else {}
    buildup = validate_neutron_buildup()
    fix_audit = load_json(FIX_DIR / "normalization_audit_groundstate_fix.json") if (FIX_DIR / "normalization_audit_groundstate_fix.json").exists() else {}
    exact = validate_exactpos(require_transport=False)
    exact_transport = validate_exactpos(require_transport=True)
    return {
        "generated_at_utc": now_utc(),
        "document_type": "s3d_o9_full_prompt_and_neutron_only_delayed_chain",
        "geometry_setup": GEOMETRY_REL,
        "source_cards": {"status": source_manifest.get("status"), "manifest": rel(SOURCE_CARDS / "source_migration_manifest.json")},
        "prepared_jobs": {"status": prepared.get("status"), "audit": rel(PREPARED_AUDIT)},
        "full_prompt": {
            "run_dir": rel(FULL_PROMPT_DIR),
            "summary_exists": (FULL_PROMPT_DIR / "run_summary.json").exists(),
            "expected_jobs": 68,
        },
        "assembled_neutron_instant": assembled,
        "neutron_buildup": buildup,
        "groundstate_fix": {
            "status": fix_audit.get("status"),
            "audit": rel(FIX_DIR / "normalization_audit_groundstate_fix.json"),
            "nubase": rel(NUBASE),
            "nubase_sha256": sha256(NUBASE) if NUBASE.exists() else None,
        },
        "exact_position_source": exact,
        "delayed_transport": exact_transport,
        "statistics": {
            "gamma_events": GAMMA_EVENTS,
            "gamma_splits": GAMMA_SPLITS,
            "non_gamma_replicas": NON_GAMMA_REPLICAS,
            "non_gamma_div": NON_GAMMA_DIV,
            "n_sample": N_SAMPLE,
            "raw_triggers": RAW_TRIGGERS,
            "m_blocks": M_BLOCKS,
            "seed": SEED,
        },
        "claim_boundary": "No detector-selected delayed rate or Step05-Step08 sensitivity claim is valid until the downstream closure consumes this transport.",
    }


def write_campaign() -> dict[str, Any]:
    payload = current_status()
    transport_ready = payload["delayed_transport"]["status"] == "PASS"
    payload["status"] = "PASS_S3D_O9_NEUTRON_DELAYED_TRANSPORT" if transport_ready else "S3D_O9_NEUTRON_DELAYED_CHAIN_INCOMPLETE"
    write_json(CAMPAIGN_MANIFEST, payload)
    return payload


def require_heavy_permission(args: argparse.Namespace, stage: str) -> None:
    if not args.allow_heavy_run:
        raise SystemExit(f"{stage} is production work; re-run with --allow-heavy-run after checking disk/runtime")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "stage",
        choices=("prepare", "run-full-prompt", "assemble-instant", "run-buildup", "prepare-delay", "run-delay", "status", "all"),
        nargs="?",
        default="status",
    )
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--allow-heavy-run", action="store_true")
    args = parser.parse_args()

    if args.stage in ("prepare", "all"):
        migrate_source_cards()
        prepare_job_sources(args.workers)
        inspect_prepared_jobs()
    if args.stage in ("run-full-prompt", "all"):
        require_heavy_permission(args, "run-full-prompt")
        run_equiv_transport("instant", FULL_PROMPT_DIR, args.workers, "", args.force)
    if args.stage in ("assemble-instant", "all"):
        assemble_instant_neutron()
    if args.stage in ("run-buildup", "all"):
        require_heavy_permission(args, "run-buildup")
        run_equiv_transport("buildup", BUILDUP_DIR, args.workers, "n", args.force)
    if args.stage in ("prepare-delay", "all"):
        require_heavy_permission(args, "prepare-delay")
        build_raw_source(args.workers, args.force)
        build_fixed_source(args.force)
        build_exactpos_source(args.force)
    if args.stage in ("run-delay", "all"):
        require_heavy_permission(args, "run-delay")
        run_delayed_transport(args.force)

    payload = write_campaign()
    print(json.dumps({"status": payload["status"], "campaign_manifest": rel(CAMPAIGN_MANIFEST)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
