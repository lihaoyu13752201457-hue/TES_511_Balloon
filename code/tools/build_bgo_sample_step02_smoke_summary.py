#!/usr/bin/env python3
"""Summarize Bgo_sample Step02 prompt/buildup smoke transport."""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BGO_DIR = ROOT / "Bgo_sample"
SOURCE_MANIFEST = ROOT / "config" / "megalib_sources_fullsphere20_bgo_sample_tilt45" / "source_migration_manifest.json"
INSTANT = ROOT / "runs" / "step02_bgo_sample_smoke_instant"
BUILDUP = ROOT / "runs" / "step02_bgo_sample_smoke_buildup"
SUMMARY_JSON = BGO_DIR / "step02_smoke_summary.json"
SUMMARY_MD = BGO_DIR / "STEP02_SMOKE.md"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sim_info(path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {
        "path": rel(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "SE": 0,
        "ID": 0,
        "TS": None,
        "TE_s": None,
        "geometry": "",
    }
    if not path.exists():
        return info
    with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if line.startswith("SE"):
                info["SE"] += 1
            elif line.startswith("ID"):
                info["ID"] += 1
            elif line.startswith("TS "):
                info["TS"] = int(line.split()[1])
            elif line.startswith("TE "):
                info["TE_s"] = float(line.split()[1])
            elif line.startswith("Geometry "):
                info["geometry"] = line.strip().split(" ", 1)[1].strip()
    return info


def source_mode_checks(path: Path, mode: str) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    return {
        "path": rel(path),
        "exists": path.exists(),
        "geometry_is_bgo_sample": "Geometry Bgo_sample/Bgo_sample.geo.setup" in text,
        "store_isotopes_true": "StoreIsotopes true" in text,
        "has_activation_buildup": "DecayMode ActivationBuildUp" in text,
        "activation_mode_expected": mode == "buildup",
    }


def summarize_run(path: Path, mode: str) -> dict[str, Any]:
    rows = load_json(path / "run_summary.json")
    norm = load_json(path / "normalization.json")
    job_rows: list[dict[str, Any]] = []
    problems: list[str] = []
    for row in rows:
        sim = sim_info(ROOT / row["sim_path"])
        source = source_mode_checks(path / "job_sources" / f"{row['job_name']}.source", mode)
        dat = ROOT / row["dat_path"]
        item = {
            "job_name": row["job_name"],
            "particle": row["particle"],
            "status": row["status"],
            "events": int(row["events"]),
            "generated_particles": int(row["generated_particles"] or 0),
            "cpu_s": float(row["cpu_s"] or 0.0),
            "observation_time_s": float(row["observation_time_s"] or 0.0),
            "sim": sim,
            "dat_path": row["dat_path"],
            "dat_exists": dat.exists(),
            "dat_size_bytes": dat.stat().st_size if dat.exists() else 0,
            "source": source,
        }
        job_rows.append(item)
        if row["status"] != "PASS":
            problems.append(f"{mode}:{row['job_name']}:status={row['status']}")
        if item["generated_particles"] != item["events"]:
            problems.append(f"{mode}:{row['job_name']}:generated mismatch")
        if sim["SE"] != item["events"] or sim["ID"] != item["events"]:
            problems.append(f"{mode}:{row['job_name']}:sim event count mismatch")
        if "Bgo_sample/Bgo_sample.geo.setup" not in sim["geometry"]:
            problems.append(f"{mode}:{row['job_name']}:SIM geometry is not Bgo_sample")
        if not item["dat_exists"] or item["dat_size_bytes"] <= 0:
            problems.append(f"{mode}:{row['job_name']}:missing DAT")
        if not source["geometry_is_bgo_sample"]:
            problems.append(f"{mode}:{row['job_name']}:source geometry is not Bgo_sample")
        if source["has_activation_buildup"] != source["activation_mode_expected"]:
            problems.append(f"{mode}:{row['job_name']}:activation mode mismatch")
    return {
        "run_dir": rel(path),
        "mode": mode,
        "normalization": {
            "source_dir": norm["source_dir"],
            "gamma_events": norm["gamma_events"],
            "gamma_splits": norm["gamma_splits"],
            "non_gamma_replicas": norm["non_gamma_replicas"],
            "farfield_radius_cm": norm["farfield_radius_cm"],
            "selected_particles": norm["selected_particles"],
            "base_events_by_particle": norm["base_events_by_particle"],
        },
        "jobs": len(job_rows),
        "passes": sum(1 for row in job_rows if row["status"] == "PASS"),
        "events_requested": sum(row["events"] for row in job_rows),
        "events_generated": sum(row["generated_particles"] for row in job_rows),
        "sim_size_bytes": sum(row["sim"]["size_bytes"] for row in job_rows),
        "dat_size_bytes": sum(row["dat_size_bytes"] for row in job_rows),
        "rows": job_rows,
        "problems": problems,
    }


def markdown(summary: dict[str, Any]) -> str:
    instant = summary["instant"]
    buildup = summary["buildup"]
    lines = [
        "# Bgo_sample Step02 Smoke Transport",
        "",
        f"Status: `{summary['status']}`.",
        "",
        "Scope: prompt and activation-build-up smoke transport only. This is not an all-particle Step02 production, not a delayed source, and not a Step05--Step08 BGO sensitivity result.",
        "",
        "Source and geometry:",
        f"- source cards: `{summary['source_manifest']['source_dir']}`",
        f"- geometry setup: `{summary['source_manifest']['geometry_setup']}`",
        f"- far-field radius: `{summary['source_manifest']['farfield_radius_cm']} cm`",
        f"- BGO threshold: `{summary['source_manifest']['bgo_checks']['bgo_veto_threshold_keV']} keV`",
        f"- attenuation check: `{summary['source_manifest']['bgo_checks']['attenuation_status']}` with max relative difference `{summary['source_manifest']['bgo_checks']['attenuation_max_abs_relative_difference']}`",
        "",
        "Smoke runs:",
        f"- instant: `{instant['passes']}/{instant['jobs']}` jobs passed, `{instant['events_generated']}` generated particles",
        f"- buildup: `{buildup['passes']}/{buildup['jobs']}` jobs passed, `{buildup['events_generated']}` generated particles",
        f"- selected particles: `{', '.join(instant['normalization']['selected_particles'])}`",
        "",
        "Boundary:",
        "- This closes BGO source-card migration and prompt/buildup Cosima transport connectivity only.",
        "- Full BGO Step02 requires all particles and production statistics.",
        "- BGO delayed source, delayed transport, Step05 response, Step06/07/08 significance, and BGO-vs-CsI comparison remain not run for this Bgo_sample package.",
        "",
        "Outputs:",
        f"- summary JSON: `{rel(SUMMARY_JSON)}`",
        f"- instant run: `{instant['run_dir']}`",
        f"- buildup run: `{buildup['run_dir']}`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    manifest = load_json(SOURCE_MANIFEST)
    instant = summarize_run(INSTANT, "instant")
    buildup = summarize_run(BUILDUP, "buildup")
    problems = []
    problems.extend(instant["problems"])
    problems.extend(buildup["problems"])
    if manifest.get("status") != "PASS":
        problems.append("source_manifest_status_not_PASS")
    if manifest.get("geometry_setup") != "Bgo_sample/Bgo_sample.geo.setup":
        problems.append("source_manifest_geometry_not_Bgo_sample")

    summary = {
        "status": "PASS_BGO_SAMPLE_STEP02_SMOKE_TRANSPORT" if not problems else "FAIL_BGO_SAMPLE_STEP02_SMOKE_TRANSPORT",
        "claim_level": "BGO_SAMPLE_STEP02_PROMPT_BUILDUP_SMOKE_NO_RATE_NO_DELAYED_SOURCE_NO_SIGNIFICANCE",
        "source_manifest": manifest,
        "instant": instant,
        "buildup": buildup,
        "problems": problems,
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    SUMMARY_MD.write_text(markdown(summary), encoding="utf-8")
    print(json.dumps({"status": summary["status"], "problems": problems, "summary": rel(SUMMARY_JSON)}, indent=2))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
