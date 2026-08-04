#!/usr/bin/env python3
"""Build the fail-closed heavy-control versus O8 screening analysis.

The screening gate is intentionally limited to the matched dominant subset
(prompt e+, prompt neutron, and the 3M atmospheric-511 sidecar) plus matched
focused-signal acceptance.  Missing production remains PENDING; present but
inconsistent geometry, source, seed, or event-count evidence is FAIL.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scipy import __version__ as scipy_version
from scipy.stats import norm

from _o8_replay_common import (
    DATA,
    PACKAGE,
    ROOT,
    S3C_GEOMETRY_SETUP,
    S3D_GEOMETRY_SETUP,
    rel,
    sha256,
)


BASE_ANALYZER_PATH = (
    ROOT
    / "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712"
    / "code/build_s3d_screening_analysis.py"
)
ATM_BASE_SCRIPT = (
    ROOT
    / "engineering/geometry_optimization_20260704/12_atm511_sidecar_replay_20260708"
    / "build_geo_opt_atm511_sidecar_replay.py"
)
ENTRY_AUTHORITY = (
    ROOT
    / "engineering/geometry_optimization_20260704/40_s3c_mainline_lightweight_review_20260710"
    / "code/build_s3c_lightweight_analysis.py"
)

S3C_DOMINANT = (
    ROOT
    / "engineering/geometry_optimization_20260704/32_s3c_dominant_backgrounds_20260709"
    / "dominant_background_summary.json"
)
S3C_ATM_SUMMARY = S3C_DOMINANT.parent / "s3c_atm511_sidecar_3m_summary.json"

PROMPT_RUN_DIR = (
    ROOT
    / "runs/geometry_optimization_20260704"
    / "s3d_o8_eqstats_prompt_eplus_n_20260712"
)
PROMPT_SOURCE_MANIFEST = (
    PACKAGE / "config/prompt_eqstats_eplus_n/source_cards/source_migration_manifest.json"
)
PROMPT_PREFLIGHT = DATA / "s3d_o8_prompt_eqstats_preflight.json"

ATM_MANIFEST = DATA / "s3d_o8_atm511_replay_manifest.json"
ATM_RUN_NAME = "Atm511SidecarS3dO8_3M"
ATM_RUN_DIR = (
    ROOT
    / "runs/geometry_optimization_20260704"
    / "s3d_o8_atm511_sidecar_3m_20260712"
)
ATM_SOURCE = ATM_RUN_DIR / f"{ATM_RUN_NAME}.source"
ATM_LOG = ATM_RUN_DIR / f"cosima_{ATM_RUN_NAME}.log"
ATM_SIM = ATM_RUN_DIR / f"{ATM_RUN_NAME}.inc1.id1.sim.gz"

SIGNAL_MANIFEST = DATA / "s3d_o8_signal_replay_manifest.json"
SIGNAL_BRANCHES = {
    "heavy_control": {
        "label": "heavy control",
        "run_name": "Opticsim_laue_f10m_a1_s3c_c0_signal37194",
        "run_dir": (
            ROOT
            / "runs/geometry_optimization_20260704"
            / "s3c_c0_f10m_a1_signal_replay_37194_matched_20260712"
        ),
        "geometry": S3C_GEOMETRY_SETUP,
    },
    "o8": {
        "label": "O8 fallback",
        "run_name": "Opticsim_laue_f10m_a1_s3d_o8_signal37194",
        "run_dir": (
            ROOT
            / "runs/geometry_optimization_20260704"
            / "s3d_o8_f10m_a1_signal_replay_37194_20260712"
        ),
        "geometry": S3D_GEOMETRY_SETUP,
    },
}
for _branch in SIGNAL_BRANCHES.values():
    _branch["source"] = _branch["run_dir"] / f"{_branch['run_name']}.source"
    _branch["sim"] = _branch["run_dir"] / f"{_branch['run_name']}.inc1.id1.sim.gz"

OUT_JSON = DATA / "s3d_o8_screening_analysis.json"
OUT_CSV = DATA / "s3d_o8_screening_comparison.csv"
OUT_MD = PACKAGE / "O8_SCREENING_ANALYSIS.md"
OUT_ATM = DATA / "s3d_o8_atm511_replay_summary.json"
OUT_SIGNAL = DATA / "s3d_o8_signal_replay_summary.json"

ACTIVE_VETO_THRESHOLD_KEV = 50.0
W2 = (510.58, 511.42)
BROAD = (480.0, 550.0)
PROMPT_PARTICLES = ("eplus", "n")
PROMPT_EXPECTED_EVENTS = {"eplus": 243_727 * 8, "n": 963_066 * 8}
PROMPT_EXPECTED_SEEDS = {
    "eplus": [1_007_922, 1_015_841, 1_023_760, 1_031_679, 1_039_598, 1_047_517, 1_055_436, 1_063_355],
    "n": [1_071_274, 1_079_193, 1_087_112, 1_095_031, 1_102_950, 1_110_869, 1_118_788, 1_126_707],
}
PROMPT_EXPECTED_TOTAL = sum(PROMPT_EXPECTED_EVENTS.values())
ATM_EVENTS = 3_000_000
ATM_SEED = 26_070_917
SIGNAL_TRIGGERS = 37_194
SIGNAL_SEED = 260_616
DOMINANT_LIMIT_CPS = 0.0052
SIGNAL_LOSS_LIMIT = 0.02

PROMPT_STAGES = (
    ("raw", "raw_events", "raw_rate_s-1"),
    ("active_veto_pass", "active_veto_pass_events", "active_veto_pass_rate_s-1"),
    (
        "side_compton_fov_pass",
        "side_compton_fov_pass_events",
        "side_compton_fov_pass_rate_s-1",
    ),
)
ATM_STAGES = (
    ("raw", "raw_events", "raw_rate_cps"),
    ("active_veto_pass", "active_veto_pass_events", "active_rate_cps"),
    ("side_compton_fov_pass", "side_compton_fov_pass_events", "final_rate_cps"),
)


def load_module(name: str, path: Path) -> Any:
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {rel(path)}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


base = load_module("o8_screening_shared_analysis", BASE_ANALYZER_PATH)
PendingInput = base.PendingInput
AuditFailure = base.AuditFailure


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def require_file(path: Path, label: str, *, retained: bool = False) -> None:
    base.require_file(path, label, retained=retained)


def require(condition: bool, message: str) -> None:
    base.require(condition, message)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    base.write_csv(path, rows)


def audit_retained_control() -> dict[str, Any]:
    return base.audit_retained_c0()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def prompt_run_audit() -> dict[str, Any]:
    run_summary_path = PROMPT_RUN_DIR / "run_summary.csv"
    for path, label in (
        (run_summary_path, "completed O8 prompt run summary"),
        (PROMPT_SOURCE_MANIFEST, "O8 prompt source manifest"),
        (PROMPT_PREFLIGHT, "O8 prompt preflight"),
        (PROMPT_RUN_DIR / "normalization.json", "O8 prompt normalization"),
        (PROMPT_RUN_DIR / "run_manifest.csv", "O8 prompt run manifest"),
    ):
        require_file(path, label)
    source_manifest = load_json(PROMPT_SOURCE_MANIFEST)
    preflight = load_json(PROMPT_PREFLIGHT)
    normalization = load_json(PROMPT_RUN_DIR / "normalization.json")
    expected_summary_schema = [
        "job_name",
        "particle",
        "status",
        "details",
        "events",
        "generated_particles",
        "cpu_s",
        "observation_time_s",
        "sim_exists",
        "dat_exists",
        "sim_size_bytes",
        "dat_size_bytes",
        "log",
        "sim_path",
        "dat_path",
    ]
    with run_summary_path.open(encoding="utf-8", newline="") as handle:
        summary_reader = csv.DictReader(handle)
        summary_schema = list(summary_reader.fieldnames or [])
        summary_rows = list(summary_reader)
    require(
        summary_schema == expected_summary_schema,
        f"O8 prompt run_summary.csv schema={summary_schema}, expected {expected_summary_schema}",
    )
    manifest_rows = read_csv(PROMPT_RUN_DIR / "run_manifest.csv")
    require(
        source_manifest.get("status") == "PASS_O8_PROMPT_EQSTATS_SOURCE_COPY_PREPARED",
        f"O8 prompt source status={source_manifest.get('status')}",
    )
    require(
        preflight.get("status") == "PASS_O8_PROMPT_EQSTATS_PREFLIGHT",
        f"O8 prompt preflight status={preflight.get('status')}",
    )
    expected_norm = {
        "mode": "instant",
        "gamma_events": 10_000_000,
        "gamma_splits": 12,
        "non_gamma_replicas": 8,
        "farfield_radius_cm": 60.0,
        "jobs": 16,
        "store_isotopes": True,
    }
    for key, expected in expected_norm.items():
        require(
            normalization.get(key) == expected,
            f"O8 prompt normalization {key}={normalization.get(key)!r}, expected {expected!r}",
        )
    require(normalization.get("selected_particles") == ["eplus", "n"], "wrong prompt particle set")
    require(len(summary_rows) == 16 and len(manifest_rows) == 16, "O8 prompt job count is not 16")
    require(
        not [row for row in summary_rows if row.get("status") not in ("PASS", "SKIP")],
        "O8 prompt production contains failed jobs",
    )
    requested = sum(int(row.get("events") or 0) for row in summary_rows)
    generated = sum(int(row.get("generated_particles") or 0) for row in summary_rows)
    require(requested == PROMPT_EXPECTED_TOTAL, f"O8 prompt requested events={requested}")
    require(generated == PROMPT_EXPECTED_TOTAL, f"O8 prompt generated events={generated}")
    summary_by_job = {row["job_name"]: row for row in summary_rows}
    require(
        len(summary_by_job) == 16,
        "O8 prompt run_summary.csv contains duplicate job names",
    )

    expected_contract = {
        (particle, rep): (PROMPT_EXPECTED_EVENTS[particle] // 8, seed)
        for particle, seeds in PROMPT_EXPECTED_SEEDS.items()
        for rep, seed in enumerate(seeds, start=1)
    }
    headers: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for row in manifest_rows:
        key = (row["particle"], int(row["rep"]))
        require(key in expected_contract and key not in seen, f"unexpected/duplicate prompt job {key}")
        expected_events, expected_seed = expected_contract[key]
        require(int(row["events"]) == expected_events, f"prompt {key} event count changed")
        require(int(row["seed"]) == expected_seed, f"prompt {key} seed changed")
        require(row["job_name"] in summary_by_job, f"prompt summary missing {row['job_name']}")
        summary = summary_by_job[row["job_name"]]
        require(summary["particle"] == row["particle"], f"prompt summary particle mismatch for {row['job_name']}")
        require(summary["status"] in ("PASS", "SKIP"), f"prompt summary status={summary['status']} for {row['job_name']}")
        require(int(summary["events"]) == expected_events, f"prompt summary requested count mismatch for {row['job_name']}")
        require(int(summary["generated_particles"]) == expected_events, f"prompt summary generated count mismatch for {row['job_name']}")
        require(summary["sim_exists"] == "True" and summary["dat_exists"] == "True", f"prompt summary output flags failed for {row['job_name']}")
        require(float(summary["cpu_s"]) > 0.0, f"prompt summary CPU time is not positive for {row['job_name']}")
        require(float(summary["observation_time_s"]) > 0.0, f"prompt summary observation time is not positive for {row['job_name']}")
        seen.add(key)
        source = Path(row["temp_source"])
        sim = Path(row["sim_path"])
        dat = Path(row["dat_path"])
        if not source.is_absolute():
            source = ROOT / source
        if not sim.is_absolute():
            sim = ROOT / sim
        if not dat.is_absolute():
            dat = ROOT / dat
        summary_sim = Path(summary["sim_path"])
        summary_dat = Path(summary["dat_path"])
        summary_log = Path(summary["log"])
        if not summary_sim.is_absolute():
            summary_sim = ROOT / summary_sim
        if not summary_dat.is_absolute():
            summary_dat = ROOT / summary_dat
        if not summary_log.is_absolute():
            summary_log = ROOT / summary_log
        require(summary_sim.resolve() == sim.resolve(), f"prompt summary SIM path mismatch for {row['job_name']}")
        require(summary_dat.resolve() == dat.resolve(), f"prompt summary DAT path mismatch for {row['job_name']}")
        require(summary_log.resolve() == Path(row["log"]).resolve(), f"prompt summary log path mismatch for {row['job_name']}")
        require_file(source, f"O8 prompt source {row['job_name']}")
        require_file(sim, f"O8 prompt SIM {row['job_name']}")
        require_file(dat, f"O8 prompt DAT {row['job_name']}")
        require_file(summary_log, f"O8 prompt log {row['job_name']}")
        require(int(summary["sim_size_bytes"]) == sim.stat().st_size, f"prompt SIM size mismatch for {row['job_name']}")
        require(int(summary["dat_size_bytes"]) == dat.stat().st_size, f"prompt DAT size mismatch for {row['job_name']}")
        geometries = base.source_geometry(source)
        require(
            len(geometries) == 1 and base.geometry_matches(geometries[0], S3D_GEOMETRY_SETUP),
            f"O8 prompt source geometry mismatch: {rel(source)}",
        )
        header = base.sim_header(sim, count_events=True)
        require(
            base.geometry_matches(header.get("geometry"), S3D_GEOMETRY_SETUP),
            f"O8 prompt SIM geometry mismatch: {rel(sim)}",
        )
        require(header.get("seed") == expected_seed, f"O8 prompt SIM seed mismatch: {rel(sim)}")
        require(
            header.get("SE") == expected_events and header.get("ID") == expected_events,
            f"O8 prompt observed SE/ID={header.get('SE')}/{header.get('ID')}, "
            f"expected {expected_events}: {rel(sim)}",
        )
        tt = [
            float(line.split()[1])
            for line in dat.read_text(encoding="utf-8", errors="replace").splitlines()
            if line.startswith("TT ")
        ]
        require(len(tt) == 1 and tt[0] > 0.0, f"O8 prompt TT audit failed: {rel(dat)}")
        headers.append(
            {
                "job_name": row["job_name"],
                "particle": row["particle"],
                "replica": int(row["rep"]),
                "events": int(row["events"]),
                "seed": expected_seed,
                "source": rel(source),
                "sim": rel(sim),
                "sim_header": header,
                "summary_row": summary,
                "tt_s": tt[0],
                "status": "PASS",
            }
        )
    require(seen == set(expected_contract), "O8 prompt particle/replica set is incomplete")
    return {
        "status": "PASS",
        "run_dir": rel(PROMPT_RUN_DIR),
        "run_summary": rel(run_summary_path),
        "run_summary_sha256": sha256(run_summary_path),
        "run_summary_schema": summary_schema,
        "jobs": len(summary_rows),
        "events_requested": requested,
        "events_generated": generated,
        "headers": headers,
    }


def analyze_prompt(control: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    run_audit = prompt_run_audit()
    proxy, step05, disk = base.selection_modules()
    cases: dict[str, Any] = {}
    rows: list[dict[str, Any]] = []
    for particle in PROMPT_PARTICLES:
        result = proxy.summarize_prompt_dir(step05, PROMPT_RUN_DIR, disk, "keep", tag=particle)
        summary = result["summary"]
        require(
            int(summary["generated_events_seen"]) == PROMPT_EXPECTED_EVENTS[particle],
            f"analyzed O8 {particle} generated count mismatch",
        )
        cases[particle] = result
        c0_case = control["prompt_cases"][particle]
        c0_summary = c0_case["summary"]
        for stage, count_key, rate_key in PROMPT_STAGES:
            rows.append(
                base.comparison_row(
                    section="prompt",
                    component=particle,
                    stage=stage,
                    metric="W2_rate",
                    unit="cps",
                    c0_count=int(c0_summary[count_key]),
                    c0_value=float(c0_summary[rate_key]),
                    c0_weight=float(c0_case["rate_per_event_s-1"]),
                    s3d_count=int(summary[count_key]),
                    s3d_value=float(summary[rate_key]),
                    s3d_weight=float(result["rate_per_event_s-1"]),
                    note="Garwood rate CI; exact conditional Poisson rate-ratio CI",
                )
            )
    return {
        "status": "PASS_O8_PROMPT_EPLUS_N_ANALYZED",
        "run_audit": run_audit,
        "cases": cases,
    }, rows


def log_tail_text(path: Path, max_bytes: int = 1_048_576) -> str:
    with path.open("rb") as handle:
        handle.seek(0, 2)
        size = handle.tell()
        handle.seek(max(0, size - max_bytes))
        return handle.read().decode("utf-8", errors="replace")


def observation_time_from_log(path: Path) -> float:
    return base.observation_time_from_log(path, running_is_pending=True)


def entry_surface_audit(sim: Path, event_ids: list[int], component: str) -> dict[str, Any]:
    entry = load_module(f"o8_entry_authority_{component}", ENTRY_AUTHORITY)
    ids = {int(value) for value in event_ids}
    if len(ids) != len(event_ids):
        raise AuditFailure(f"duplicate final atmospheric event IDs for {component}")
    found = entry.scan_target_inits(sim, ids) if ids else {}
    rows: list[dict[str, Any]] = []
    for event_id in sorted(ids):
        init = found[event_id]
        rows.append({"event_id": event_id, **init, **entry.classify_entry(init)})
    surface_counts = Counter(str(row["entry_surface"]) for row in rows)
    region_counts = Counter(str(row["entry_region"]) for row in rows)
    require(sum(surface_counts.values()) == len(ids), f"entry-surface closure failed for {component}")
    return {
        "status": "PASS",
        "method": f"{rel(ENTRY_AUTHORITY)}::scan_target_inits + classify_entry",
        "method_sha256": sha256(ENTRY_AUTHORITY),
        "scope": "IA INIT ray/envelope intersection; directional proxy, not first physical interaction",
        "selected_final_events": len(ids),
        "surface_counts": dict(sorted(surface_counts.items())),
        "surface_shares": {
            key: value / len(ids) for key, value in sorted(surface_counts.items())
        }
        if ids
        else {},
        "region_counts": dict(sorted(region_counts.items())),
        "rows": rows,
    }


def analyze_atmospheric(control: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    for path, label in (
        (ATM_MANIFEST, "O8 atmospheric manifest"),
        (ATM_SOURCE, "O8 atmospheric source"),
        (ATM_LOG, "O8 atmospheric log"),
        (ATM_SIM, "O8 atmospheric SIM"),
    ):
        require_file(path, label)
    manifest = load_json(ATM_MANIFEST)
    source_audit = manifest.get("source_authority", {}).get("source_audit", {})
    contract = manifest.get("selection_contract", {})
    run = manifest.get("run", {})
    require(source_audit.get("status") == "PASS", "O8 atmospheric source audit is not PASS")
    require(int(run.get("events", -1)) == ATM_EVENTS, "O8 atmospheric event contract changed")
    require(int(run.get("seed", -1)) == ATM_SEED, "O8 atmospheric seed contract changed")
    require(
        float(contract.get("active_veto_threshold_keV", -1)) == ACTIVE_VETO_THRESHOLD_KEV,
        "O8 atmospheric active-veto threshold is not 50 keV",
    )
    require(
        contract.get("energy_windows_keV", {}).get("w2_510p58_511p42") == list(W2),
        "O8 atmospheric W2 contract changed",
    )
    geometries = base.source_geometry(ATM_SOURCE)
    require(
        len(geometries) == 1 and base.geometry_matches(geometries[0], S3D_GEOMETRY_SETUP),
        "O8 atmospheric source geometry mismatch",
    )
    quick = base.sim_header(ATM_SIM)
    require(base.geometry_matches(quick.get("geometry"), S3D_GEOMETRY_SETUP), "O8 atmospheric SIM geometry mismatch")
    require(quick.get("seed") == ATM_SEED, f"O8 atmospheric SIM seed={quick.get('seed')}")
    observation_time_s = observation_time_from_log(ATM_LOG)

    atm_base = load_module("o8_atm_parser", ATM_BASE_SCRIPT)
    atm_base.SIM = ATM_SIM
    atm_base.LOG = ATM_LOG
    atm_base.ACTIVE_VETO_THRESHOLD_KEV = ACTIVE_VETO_THRESHOLD_KEV
    atm_base.is_active_veto_volume = base.is_active_veto_volume
    step05 = atm_base.load_step05_module()
    step05.is_v3p5_active_veto_volume = base.is_active_veto_volume
    catalog = atm_base.parse_catalog()
    require(int(catalog["generated_events"]) == ATM_EVENTS, "O8 atmospheric catalog ID count is not 3M")
    # Explicit, full readable-stream audit: requested counts or manifest values
    # are never substituted for observed SE/ID.
    header = base.sim_header(ATM_SIM, count_events=True)
    require(base.geometry_matches(header.get("geometry"), S3D_GEOMETRY_SETUP), "counted O8 atmospheric geometry mismatch")
    require(header.get("seed") == ATM_SEED, "counted O8 atmospheric seed mismatch")
    require(
        header.get("SE") == ATM_EVENTS and header.get("ID") == ATM_EVENTS,
        f"O8 atmospheric observed SE/ID={header.get('SE')}/{header.get('ID')}, expected 3M",
    )
    require(int(catalog["generated_events"]) == int(header["ID"]), "catalog/full-stream ID disagreement")
    catalog["observation_time_s"] = observation_time_s
    model = manifest.get("source_model_frozen_from_heavy_control", {})
    phi_4pi = float(model.get("phi_4pi_ph_cm2_s", 0.0))
    require(phi_4pi > 0.0, "O8 atmospheric 4pi flux is missing/non-positive")
    w2 = atm_base.summarize_window(catalog, step05, *W2, phi_4pi)
    broad = atm_base.summarize_window(catalog, step05, *BROAD, phi_4pi)
    event_weight = 1.0 / observation_time_s
    c0_atm = control["atm_case"]
    rows: list[dict[str, Any]] = []
    relative: dict[str, Any] = {}
    for window_name, current, baseline_window in (
        ("w2_510p58_511p42", w2, c0_atm["windows"]["w2_510p58_511p42"]),
        ("broad_480_550", broad, c0_atm["windows"]["broad_480_550"]),
    ):
        relative[window_name] = {}
        for stage, count_key, rate_key in ATM_STAGES:
            c0_count = int(baseline_window[count_key])
            o8_count = int(current[count_key])
            c0_value = float(baseline_window[rate_key])
            o8_value = float(current[rate_key])
            c0_weight = float(baseline_window["event_rate_weight_cps"])
            ratio_ci = base.poisson_rate_ratio_interval(
                o8_count, event_weight, c0_count, c0_weight
            )
            relative[window_name][stage] = {
                "heavy_control_events": c0_count,
                "o8_events": o8_count,
                "heavy_control_rate_cps": c0_value,
                "o8_rate_cps": o8_value,
                "o8_over_heavy_control": o8_value / c0_value if c0_value > 0 else None,
                "ratio_counting_95": ratio_ci,
            }
            if window_name == "w2_510p58_511p42":
                rows.append(
                    base.comparison_row(
                        section="atm511",
                        component="atm511",
                        stage=stage,
                        metric="W2_rate",
                        unit="cps",
                        c0_count=c0_count,
                        c0_value=c0_value,
                        c0_weight=c0_weight,
                        s3d_count=o8_count,
                        s3d_value=o8_value,
                        s3d_weight=event_weight,
                        note="matched 3M sidecar; Garwood rate CI",
                    )
                )

    c0_w2 = c0_atm["windows"]["w2_510p58_511p42"]
    c0_sim = ROOT / c0_atm["inputs"]["sim"]
    require_file(c0_sim, "retained control atmospheric SIM", retained=True)
    entry_audit = {
        "heavy_control": entry_surface_audit(
            c0_sim,
            [int(value) for value in c0_w2["final_event_ids"]],
            "heavy_control_atm511",
        ),
        "o8": entry_surface_audit(
            ATM_SIM,
            [int(value) for value in w2["final_event_ids"]],
            "o8_atm511",
        ),
    }
    payload = {
        "status": "PASS_O8_ATM511_4PI_SIDECAR_REPLAY",
        "generated_at_utc": now_utc(),
        "claim_boundary": (
            "Semi-empirical atmospheric-511 sidecar with the frozen heavy-control source; "
            "not a native EXPACS line component. Entry surfaces are IA INIT direction proxies."
        ),
        "inputs": {
            "manifest": rel(ATM_MANIFEST),
            "source": rel(ATM_SOURCE),
            "log": rel(ATM_LOG),
            "sim": rel(ATM_SIM),
            "heavy_control_summary": rel(S3C_ATM_SUMMARY),
        },
        "sim_header": header,
        "transport": {
            "status": "PASS_COMPLETE_READABLE_SIM",
            "events_requested": ATM_EVENTS,
            "events_generated": int(catalog["generated_events"]),
            "SE": int(header["SE"]),
            "ID": int(header["ID"]),
            "count_authority": header.get("count_authority"),
            "seed": ATM_SEED,
            "geometry": rel(S3D_GEOMETRY_SETUP),
        },
        "source_model": model,
        "normalization": {
            "observation_time_s": observation_time_s,
            "event_rate_weight_cps": event_weight,
            "active_veto_threshold_keV": ACTIVE_VETO_THRESHOLD_KEV,
            "selection_contract": contract,
        },
        "catalog": {
            "generated_events": int(catalog["generated_events"]),
            "kept_events_tes_or_active": int(catalog["kept_events_tes_or_active"]),
            "detector_catalog_event_rate_cps": int(catalog["kept_events_tes_or_active"])
            * event_weight,
            "tes_events": int((catalog["tes_total_keV"] > 0.0).sum()),
            "tes_event_rate_cps": int((catalog["tes_total_keV"] > 0.0).sum())
            * event_weight,
            "observation_time_s": observation_time_s,
        },
        "windows": {"w2_510p58_511p42": w2, "broad_480_550": broad},
        "relative_to_heavy_control": relative,
        "final_w2_entry_surface_audit": entry_audit,
    }
    return payload, rows


def analyze_signal() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    require_file(SIGNAL_MANIFEST, "O8 matched signal manifest")
    manifest = load_json(SIGNAL_MANIFEST)
    contract = manifest.get("matched_contract", {})
    eventlist = manifest.get("reference_authority", {}).get("eventlist_audit", {})
    require(eventlist.get("status") == "PASS", "O8 signal EventList audit is not PASS")
    require(int(eventlist.get("rows", -1)) == SIGNAL_TRIGGERS, "signal EventList row count changed")
    require(int(contract.get("triggers", -1)) == SIGNAL_TRIGGERS, "signal trigger contract changed")
    require(int(contract.get("seed", -1)) == SIGNAL_SEED, "signal seed contract changed")
    require(contract.get("explicit_cosima_seed_argument") is True, "signal -s seed contract absent")
    require(
        contract.get("canonical_sources_identical_except_geometry_run_output") is True,
        "signal source canonical match is not PASS",
    )
    require(
        float(contract.get("selection", {}).get("active_veto_threshold_keV", -1))
        == ACTIVE_VETO_THRESHOLD_KEV,
        "signal active-veto threshold is not 50 keV",
    )
    proxy, step05, disk = base.selection_modules()
    analyzed: dict[str, Any] = {}
    final_ids: dict[str, set[int]] = {}
    for key, branch in SIGNAL_BRANCHES.items():
        require_file(branch["source"], f"{branch['label']} signal source")
        require_file(branch["sim"], f"{branch['label']} signal SIM")
        geometries = base.source_geometry(branch["source"])
        require(
            len(geometries) == 1 and base.geometry_matches(geometries[0], branch["geometry"]),
            f"{branch['label']} signal source geometry mismatch",
        )
        header = base.sim_header(branch["sim"], count_events=True)
        require(base.geometry_matches(header.get("geometry"), branch["geometry"]), f"{branch['label']} signal SIM geometry mismatch")
        require(header.get("seed") == SIGNAL_SEED, f"{branch['label']} signal seed mismatch")
        require(
            header.get("SE") == SIGNAL_TRIGGERS and header.get("ID") == SIGNAL_TRIGGERS,
            f"{branch['label']} signal SE/ID={header.get('SE')}/{header.get('ID')}",
        )
        summary = base.summarize_unit_signal(proxy, step05, disk, branch["sim"])
        require(summary["generated_events_seen"] == SIGNAL_TRIGGERS, f"{branch['label']} analyzed count mismatch")
        summary["final_acceptance_wilson_95"] = base.wilson_interval(
            summary["side_compton_fov_pass_events"], SIGNAL_TRIGGERS
        )
        final_ids[key] = set(summary.pop("final_event_ids"))
        analyzed[key] = {
            "label": branch["label"],
            "geometry": rel(branch["geometry"]),
            "source": rel(branch["source"]),
            "sim": rel(branch["sim"]),
            "sim_header": header,
            "selection": summary,
        }

    c0_sel = analyzed["heavy_control"]["selection"]
    o8_sel = analyzed["o8"]["selection"]
    c0_final = int(c0_sel["side_compton_fov_pass_events"])
    o8_final = int(o8_sel["side_compton_fov_pass_events"])
    require(c0_final > 0, "heavy-control signal final acceptance is zero")
    ratio = o8_final / c0_final
    loss = 1.0 - ratio
    ratio_ci = base.risk_ratio_interval(
        o8_final, SIGNAL_TRIGGERS, c0_final, SIGNAL_TRIGGERS
    )
    paired = {
        "both_pass": len(final_ids["heavy_control"] & final_ids["o8"]),
        "heavy_control_only": len(final_ids["heavy_control"] - final_ids["o8"]),
        "o8_only": len(final_ids["o8"] - final_ids["heavy_control"]),
        "neither": SIGNAL_TRIGGERS - len(final_ids["heavy_control"] | final_ids["o8"]),
    }
    gate_pass = loss <= SIGNAL_LOSS_LIMIT
    comparison = {
        "o8_over_heavy_control_final_acceptance": ratio,
        "risk_ratio_counting_95_katz": ratio_ci,
        "relative_signal_loss": loss,
        "paired_acceptance_counts": paired,
        "promotion_limit_relative_loss": SIGNAL_LOSS_LIMIT,
        "promotion_gate_pass": gate_pass,
        "gate_policy": "central matched acceptance loss <= 2%; interval is diagnostic",
    }
    payload = {
        "status": "PASS_MATCHED_HEAVY_CONTROL_O8_SIGNAL_REPLAY_ANALYZED",
        "generated_at_utc": now_utc(),
        "claim_boundary": "Matched detector transport and W2 selection only.",
        "manifest": rel(SIGNAL_MANIFEST),
        "eventlist_audit": eventlist,
        "selection_contract": contract.get("selection"),
        "branches": analyzed,
        "comparison": comparison,
    }
    c0_ci = c0_sel["final_acceptance_wilson_95"]
    o8_ci = o8_sel["final_acceptance_wilson_95"]
    row = {
        "section": "signal",
        "component": "focused_eventlist",
        "stage": "side_compton_fov_pass",
        "metric": "W2_acceptance",
        "unit": "fraction",
        "c0_count": c0_final,
        "c0_value": c0_final / SIGNAL_TRIGGERS,
        "c0_ci95_low": c0_ci["low"],
        "c0_ci95_high": c0_ci["high"],
        "s3d_count": o8_final,
        "s3d_value": o8_final / SIGNAL_TRIGGERS,
        "s3d_ci95_low": o8_ci["low"],
        "s3d_ci95_high": o8_ci["high"],
        "s3d_over_c0": ratio,
        "ratio_ci95_low": ratio_ci["low"],
        "ratio_ci95_high": ratio_ci["high"],
        "gate_limit": SIGNAL_LOSS_LIMIT,
        "gate_pass": gate_pass,
        "note": "matched 37,194-row EventList; central loss gate <=2%",
    }
    return payload, [row]


def dominant_gate(
    control: dict[str, Any], prompt: dict[str, Any], atmospheric: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    components: list[dict[str, Any]] = []
    for particle in PROMPT_PARTICLES:
        c0_case = control["prompt_cases"][particle]
        o8_case = prompt["cases"][particle]
        components.append(
            {
                "component": particle,
                "heavy_control_events": int(c0_case["summary"]["side_compton_fov_pass_events"]),
                "heavy_control_rate_cps": float(c0_case["summary"]["side_compton_fov_pass_rate_s-1"]),
                "heavy_control_weight_cps": float(c0_case["rate_per_event_s-1"]),
                "o8_events": int(o8_case["summary"]["side_compton_fov_pass_events"]),
                "o8_rate_cps": float(o8_case["summary"]["side_compton_fov_pass_rate_s-1"]),
                "o8_weight_cps": float(o8_case["rate_per_event_s-1"]),
            }
        )
    c0_atm = control["atm_case"]["windows"]["w2_510p58_511p42"]
    o8_atm = atmospheric["windows"]["w2_510p58_511p42"]
    components.append(
        {
            "component": "atm511",
            "heavy_control_events": int(c0_atm["side_compton_fov_pass_events"]),
            "heavy_control_rate_cps": float(c0_atm["final_rate_cps"]),
            "heavy_control_weight_cps": float(c0_atm["event_rate_weight_cps"]),
            "o8_events": int(o8_atm["side_compton_fov_pass_events"]),
            "o8_rate_cps": float(o8_atm["final_rate_cps"]),
            "o8_weight_cps": float(o8_atm["event_rate_weight_cps"]),
        }
    )
    c0_rate = sum(row["heavy_control_rate_cps"] for row in components)
    o8_rate = sum(row["o8_rate_cps"] for row in components)
    c0_sigma = math.sqrt(
        sum(row["heavy_control_events"] * row["heavy_control_weight_cps"] ** 2 for row in components)
    )
    o8_sigma = math.sqrt(sum(row["o8_events"] * row["o8_weight_cps"] ** 2 for row in components))
    z = float(norm.ppf(0.975))
    result = {
        "components": components,
        "definition": "final W2 prompt eplus + neutron + atmospheric-511 matched subset",
        "heavy_control_rate_cps": c0_rate,
        "o8_rate_cps": o8_rate,
        "o8_over_heavy_control": o8_rate / c0_rate if c0_rate > 0 else None,
        "heavy_control_counting_95_gaussian_propagation": [
            max(0.0, c0_rate - z * c0_sigma),
            c0_rate + z * c0_sigma,
        ],
        "o8_counting_95_gaussian_propagation": [
            max(0.0, o8_rate - z * o8_sigma),
            o8_rate + z * o8_sigma,
        ],
        "promotion_limit_cps": DOMINANT_LIMIT_CPS,
        "promotion_gate_pass": o8_rate <= DOMINANT_LIMIT_CPS,
        "gate_policy": "central matched subset rate <= 0.0052 cps; interval is diagnostic",
    }
    csv_row = {
        "section": "dominant_subset",
        "component": "eplus+n+atm511",
        "stage": "side_compton_fov_pass",
        "metric": "W2_rate_sum",
        "unit": "cps",
        "c0_count": sum(row["heavy_control_events"] for row in components),
        "c0_value": c0_rate,
        "c0_ci95_low": result["heavy_control_counting_95_gaussian_propagation"][0],
        "c0_ci95_high": result["heavy_control_counting_95_gaussian_propagation"][1],
        "s3d_count": sum(row["o8_events"] for row in components),
        "s3d_value": o8_rate,
        "s3d_ci95_low": result["o8_counting_95_gaussian_propagation"][0],
        "s3d_ci95_high": result["o8_counting_95_gaussian_propagation"][1],
        "s3d_over_c0": result["o8_over_heavy_control"],
        "gate_limit": DOMINANT_LIMIT_CPS,
        "gate_pass": result["promotion_gate_pass"],
        "note": "central gate; diagnostic independent-Poisson Gaussian propagation",
    }
    return result, csv_row


def pending_payload(kind: str, pending: list[str], failures: list[str]) -> dict[str, Any]:
    return {
        "status": f"FAIL_{kind}_AUDIT" if failures else f"PENDING_{kind}_INPUTS",
        "generated_at_utc": now_utc(),
        "pending_inputs": pending,
        "audit_failures": failures,
        "no_zero_substitution": True,
    }


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# O8 Fallback Screening Analysis",
        "",
        f"Status: `{payload['status']}`",
        "",
        "This is a matched screening result, not the complete eight-family prompt plus delayed mission closure.",
        "",
    ]
    if payload.get("pending_inputs"):
        lines.extend(["## Pending inputs", ""])
        lines.extend(f"- {value}" for value in payload["pending_inputs"])
        lines.append("")
    if payload.get("audit_failures"):
        lines.extend(["## Audit failures", ""])
        lines.extend(f"- {value}" for value in payload["audit_failures"])
        lines.append("")
    gates = payload.get("promotion_gates", {})
    lines.extend(
        [
            "## Preregistered gates",
            "",
            f"Decision so far: `{gates.get('decision_so_far', 'PENDING')}`",
            "",
            "| gate | O8 result | limit | state |",
            "|---|---:|---:|---:|",
        ]
    )
    dominant = gates.get("dominant_subset", {})
    if dominant.get("evaluation_status") in ("PASS", "FAIL"):
        lines.append(
            f"| final W2 e+/n/atm subset | {dominant['o8_rate_cps']:.9g} cps | "
            f"{DOMINANT_LIMIT_CPS:.9g} cps | `{dominant['evaluation_status']}` |"
        )
    else:
        lines.append(f"| final W2 e+/n/atm subset | pending | {DOMINANT_LIMIT_CPS:.9g} cps | `PENDING` |")
    signal = gates.get("signal", {})
    if signal.get("evaluation_status") in ("PASS", "FAIL"):
        lines.append(
            f"| matched focused-signal loss | {signal['relative_signal_loss']:.6%} | "
            f"{SIGNAL_LOSS_LIMIT:.2%} | `{signal['evaluation_status']}` |"
        )
    else:
        lines.append(f"| matched focused-signal loss | pending | {SIGNAL_LOSS_LIMIT:.2%} | `PENDING` |")
    lines.extend(
        [
            "",
            "## Frozen selection",
            "",
            "- Primary line window: `510.58 <= TES energy < 511.42 keV`.",
            "- Active-veto acceptance: summed matched active energy `< 50 keV`.",
            "- Side-entry Compton/FoV: retained `side_keep_from_hits(..., reject_policy='keep')`.",
            "- Signal gate: central matched acceptance loss `<= 2%`.",
            "- Dominant-background gate: central e+/n/atmospheric sum `<= 0.0052 cps`.",
            "",
            "Atmospheric output additionally records the IA INIT entry-surface proxy for every final selected event in both branches.",
            "",
            "Generated files: `data/s3d_o8_screening_analysis.json`, `data/s3d_o8_screening_comparison.csv`, `data/s3d_o8_atm511_replay_summary.json`, and `data/s3d_o8_signal_replay_summary.json`.",
        ]
    )
    return "\n".join(lines) + "\n"


def self_test() -> dict[str, Any]:
    if DOMINANT_LIMIT_CPS != 0.0052 or SIGNAL_LOSS_LIMIT != 0.02:
        raise AuditFailure("preregistered gate constant changed")
    zero = base.poisson_rate_interval(0, 0.001)
    require(zero["low"] == 0.0 and zero["high"] > 0.0, "zero-count Garwood test failed")
    ratio = base.poisson_rate_ratio_interval(18, 1.0, 6, 1.0)
    require(ratio["low"] is not None and ratio["high"] is not None, "Poisson ratio test failed")
    entry = load_module("o8_entry_selftest", ENTRY_AUTHORITY)

    def local_to_global(values: tuple[float, float, float]) -> tuple[float, float, float]:
        return entry.rotate_y(values, 45.0)

    def init(local_p: tuple[float, float, float], local_d: tuple[float, float, float]) -> dict[str, float]:
        p = local_to_global(local_p)
        d = local_to_global(local_d)
        return {
            "init_x_cm": p[0],
            "init_y_cm": p[1],
            "init_z_cm": p[2],
            "dir_x": d[0],
            "dir_y": d[1],
            "dir_z": d[2],
            "init_energy_keV": 511.0,
        }

    surfaces = {
        "side": entry.classify_entry(init((31.0, 5.0, 0.0), (-1.0, 0.0, 0.0)))["entry_surface"],
        "bottom": entry.classify_entry(init((0.0, 0.0, -28.0), (0.0, 0.0, 1.0)))["entry_surface"],
        "top": entry.classify_entry(init((0.0, 0.0, 50.0), (0.0, 0.0, -1.0)))["entry_surface"],
    }
    require(surfaces == {"side": "side", "bottom": "bottom", "top": "top"}, f"entry self-test={surfaces}")
    return {
        "status": "PASS_SELF_TEST",
        "dominant_limit_cps": DOMINANT_LIMIT_CPS,
        "signal_loss_limit": SIGNAL_LOSS_LIMIT,
        "zero_count_garwood_95": zero,
        "entry_surfaces": surfaces,
        "production_launched": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status-only", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        try:
            print(json.dumps(self_test(), indent=2))
            return 0
        except (AuditFailure, OSError, ValueError, KeyError) as exc:
            print(json.dumps({"status": "FAIL_SELF_TEST", "error": str(exc)}, indent=2))
            return 2
    if args.status_only:
        atm_complete = ATM_LOG.is_file() and "Observation time:" in log_tail_text(ATM_LOG)
        readiness = {
            "prompt_run_summary_csv": (PROMPT_RUN_DIR / "run_summary.csv").is_file(),
            "atm_manifest": ATM_MANIFEST.is_file(),
            "atm_completion_record": atm_complete,
            "atm_sim": ATM_SIM.is_file(),
            "signal_manifest": SIGNAL_MANIFEST.is_file(),
            "signal_heavy_control_sim": SIGNAL_BRANCHES["heavy_control"]["sim"].is_file(),
            "signal_o8_sim": SIGNAL_BRANCHES["o8"]["sim"].is_file(),
        }
        ready = all(readiness.values())
        print(
            json.dumps(
                {
                    "status": "READY_FOR_SCREENING_ANALYSIS" if ready else "PENDING_INPUTS",
                    "readiness": readiness,
                    "outputs_unchanged": True,
                },
                indent=2,
            )
        )
        return 0

    pending: list[str] = []
    failures: list[str] = []
    rows: list[dict[str, Any]] = []
    sections: dict[str, Any] = {}
    try:
        control = audit_retained_control()
    except (AuditFailure, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        control = {}
        failures.append(f"retained heavy control: {exc}")

    def run_section(name: str, func: Any, *func_args: Any) -> Any | None:
        try:
            result, section_rows = func(*func_args)
            sections[name] = result
            rows.extend(section_rows)
            return result
        except PendingInput as exc:
            sections[name] = {"status": "PENDING", "reason": str(exc)}
            pending.append(f"{name}: {exc}")
            return None
        except (AuditFailure, OSError, ValueError, KeyError, json.JSONDecodeError, EOFError, gzip.BadGzipFile) as exc:
            sections[name] = {"status": "FAIL", "reason": str(exc)}
            failures.append(f"{name}: {exc}")
            return None

    prompt = run_section("prompt", analyze_prompt, control) if control else None
    atmospheric = run_section("atm511", analyze_atmospheric, control) if control else None
    signal = run_section("signal", analyze_signal)

    if atmospheric is None:
        write_json(
            OUT_ATM,
            pending_payload(
                "O8_ATM511",
                [value for value in pending if value.startswith("atm511:")],
                [value for value in failures if value.startswith("atm511:")],
            ),
        )
    else:
        write_json(OUT_ATM, atmospheric)
    if signal is None:
        write_json(
            OUT_SIGNAL,
            pending_payload(
                "O8_SIGNAL_REPLAY",
                [value for value in pending if value.startswith("signal:")],
                [value for value in failures if value.startswith("signal:")],
            ),
        )
    else:
        write_json(OUT_SIGNAL, signal)

    gates: dict[str, Any] = {}
    if control and prompt and atmospheric:
        dominant, row = dominant_gate(control, prompt, atmospheric)
        rows.append(row)
        dominant["evaluation_status"] = "PASS" if dominant["promotion_gate_pass"] else "FAIL"
        gates["dominant_subset"] = dominant
    else:
        gates["dominant_subset"] = {
            "evaluation_status": "PENDING",
            "reason": "requires retained control, O8 prompt e+/n, and O8 atmospheric-511",
            "promotion_limit_cps": DOMINANT_LIMIT_CPS,
        }
    if signal:
        signal_gate = dict(signal["comparison"])
        signal_gate["evaluation_status"] = "PASS" if signal_gate["promotion_gate_pass"] else "FAIL"
        gates["signal"] = signal_gate
    else:
        gates["signal"] = {
            "evaluation_status": "PENDING",
            "reason": sections.get("signal", {}).get("reason", "O8 signal section unavailable"),
            "promotion_limit_relative_loss": SIGNAL_LOSS_LIMIT,
        }
    gate_rows = [gates["dominant_subset"], gates["signal"]]
    all_evaluated = all(row["evaluation_status"] in ("PASS", "FAIL") for row in gate_rows)
    any_failed = any(row["evaluation_status"] == "FAIL" for row in gate_rows)
    gates["all_required_gates_evaluated"] = all_evaluated
    gates["any_evaluated_gate_failed"] = any_failed
    gates["decision_so_far"] = (
        "FAIL_AT_LEAST_ONE_COMPLETED_GATE"
        if any_failed
        else ("PASS_ALL_COMPLETED_GATES" if any(row["evaluation_status"] == "PASS" for row in gate_rows) else "PENDING")
    )
    if failures:
        status = "FAIL_O8_SCREENING_AUDIT"
    elif pending or not all_evaluated:
        status = "PENDING_O8_SCREENING_INPUTS"
    else:
        status = (
            "FAIL_O8_SCREENING_PROMOTION_GATES"
            if any_failed
            else "PASS_O8_SCREENING_PROMOTION_GATES"
        )
    if not rows:
        rows.append(
            {
                "section": "analysis",
                "component": "all",
                "stage": "input_audit",
                "metric": "status",
                "note": status,
            }
        )
    payload = {
        "status": status,
        "generated_at_utc": now_utc(),
        "claim_boundary": (
            "Matched heavy-control versus O8 screening for prompt eplus/neutron, "
            "atmospheric-511, and focused signal; not full all-family/delayed mission closure."
        ),
        "pending_inputs": pending,
        "audit_failures": failures,
        "no_zero_substitution": True,
        "selection_contract": {
            "w2_window_keV": list(W2),
            "interval_policy": "lower-inclusive, upper-exclusive",
            "active_veto_threshold_keV": ACTIVE_VETO_THRESHOLD_KEV,
            "side_compton_fov": "retained side_keep_from_hits(reject_policy='keep')",
        },
        "gate_contract": {
            "signal_central_relative_loss_max": SIGNAL_LOSS_LIMIT,
            "dominant_subset_central_rate_max_cps": DOMINANT_LIMIT_CPS,
        },
        "counting_interval_contract": {
            "component_rates": "two-sided 95% Garwood exact Poisson interval",
            "component_rate_ratios": "two-sided 95% exact conditional Poisson interval",
            "signal_acceptance": "two-sided 95% Wilson score interval",
            "signal_acceptance_ratio": "two-sided 95% Katz interval plus paired counts",
            "dominant_subset_sum": "independent-Poisson Gaussian propagation; diagnostic only",
            "scipy_version": scipy_version,
        },
        "algorithm_authority": {
            "shared_screening_analyzer": rel(BASE_ANALYZER_PATH),
            "shared_screening_analyzer_sha256": sha256(BASE_ANALYZER_PATH),
            "atmospheric_parser": rel(ATM_BASE_SCRIPT),
            "atmospheric_parser_sha256": sha256(ATM_BASE_SCRIPT),
            "entry_surface_classifier": rel(ENTRY_AUTHORITY),
            "entry_surface_classifier_sha256": sha256(ENTRY_AUTHORITY),
            "analysis_script": rel(Path(__file__)),
            "analysis_script_sha256": sha256(Path(__file__)),
        },
        "retained_control_authority": control,
        "sections": sections,
        "promotion_gates": gates,
        "outputs": {
            "json": rel(OUT_JSON),
            "csv": rel(OUT_CSV),
            "markdown": rel(OUT_MD),
            "atm_summary": rel(OUT_ATM),
            "signal_summary": rel(OUT_SIGNAL),
        },
    }
    write_json(OUT_JSON, payload)
    write_csv(OUT_CSV, rows)
    OUT_MD.write_text(markdown(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": status,
                "pending": len(pending),
                "failures": len(failures),
                "json": rel(OUT_JSON),
                "csv": rel(OUT_CSV),
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )
    return 2 if status == "FAIL_O8_SCREENING_AUDIT" else 0


if __name__ == "__main__":
    raise SystemExit(main())
