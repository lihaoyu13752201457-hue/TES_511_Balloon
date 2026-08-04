#!/usr/bin/env python3
"""Dedicated, fail-closed S3d-O9 Step05--Step08 closure.

This postprocessor is deliberately geometry- and campaign-specific.  It never
launches Cosima and it never redirects generic Step05--Step08 builders with an
arbitrary label.  When any production input is absent, ``preflight`` and
``all`` write a PENDING audit and stop before creating a result summary.

The completed path merges four independently normalized background inputs:

* all-eight-family prompt transport, normalized per family by ``1/sum(TT)``;
* neutron-only, NUBASE-corrected exact-position delayed transport;
* the semiempirical 3M atmospheric-511 sidecar, normalized by its Cosima
  observation time and scaled along the mission by its physical 4pi flux;
* the geometry-local 37,194-row f10m-A1 focused EventList signal replay.

All streams use the retained side-entry selection implementation, a 50-keV
analysis veto, and the frozen monotonic Knob0 policy.  The native 80-keV BGO
detector threshold is recorded as a systematic and is not silently conflated
with the analysis threshold.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import pickle
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from scipy.stats import beta, chi2

from _s3d_replay_common import (
    AuditError,
    S3D_GEOMETRY_SETUP,
    audit_geometry_authority,
    rel,
    selection_contract,
    sha256,
    sim_header,
)


ROOT = Path(__file__).resolve().parents[4]
WORK = Path(__file__).resolve().parents[1]
DATA = WORK / "data"
FULLCHAIN = WORK / "fullchain"
STEP05_OUT = FULLCHAIN / "step05"
STEP06_OUT = FULLCHAIN / "step06"
STEP07_OUT = FULLCHAIN / "step07"
STEP08_OUT = FULLCHAIN / "step08"

PREFLIGHT_JSON = DATA / "s3d_step05_08_closure_preflight.json"
STEP05_CORE_JSON = STEP05_OUT / "step05_s3d_o9_core_no_atm511_summary.json"
STEP05_JSON = STEP05_OUT / "step05_s3d_o9_fullchain_l1_response_summary.json"
STEP05_RATES = STEP05_OUT / "step05_s3d_o9_fullchain_l1_rates.csv"
STEP06_JSON = STEP06_OUT / "step06_s3d_o9_fullchain_summary.json"
STEP06_BG = STEP06_OUT / "background_time_variation.csv"
STEP07_JSON = STEP07_OUT / "source_case_summary.json"
STEP07_RATES = STEP07_OUT / "source_case_rates.csv"
STEP08_JSON = STEP08_OUT / "step08_s3d_o9_fullchain_time_dependent_summary.json"

PROMPT_DIR = (
    ROOT
    / "runs/geometry_optimization_20260704"
    / "s3d_o9_fullstat_prompt_all8_20260712"
)
PROMPT_SUMMARY = PROMPT_DIR / "run_summary.json"
PROMPT_NORM = PROMPT_DIR / "normalization.json"
PROMPT_MANIFEST = PROMPT_DIR / "run_manifest.csv"
PROMPT_SOURCE_MANIFEST = (
    WORK / "config/full_prompt_all8/source_cards/source_migration_manifest.json"
)

DELAY_LABEL = "s3d_o9_neutron_delayed_m50000_20260712"
DELAYED_SIM = (
    ROOT
    / "runs/geometry_optimization_20260704"
    / f"step02_delayed_transport_{DELAY_LABEL}"
    / "DelayedDecayS3dO9NeutronM50000.inc1.id1.sim.gz"
)
FIX_DIR = (
    ROOT
    / "runs/geometry_optimization_20260704"
    / f"step02_delay_fix_{DELAY_LABEL}"
)
FIXED_SOURCE = FIX_DIR / "activation_decay_day15_groundstate_fixed.source"
FIX_AUDIT = FIX_DIR / "normalization_audit_groundstate_fix.json"
GROUNDSTATE = FIX_DIR / "groundstate_activity_corrections.csv"
EXACT_SUMMARY = FULLCHAIN / "delayed_source/delayed_source_exactpos_summary.json"
DELAY_CAMPAIGN = DATA / "s3d_delayed_activation_campaign.json"
NUBASE = ROOT / "inputs/nubase/nubase_2020.txt"

SIGNAL_RUN_DIR = (
    ROOT
    / "runs/geometry_optimization_20260704"
    / "s3d_o9_f10m_a1_signal_replay_37194_20260712"
)
SIGNAL_NAME = "Opticsim_laue_f10m_a1_s3d_o9_signal37194"
SIGNAL_SOURCE = SIGNAL_RUN_DIR / f"{SIGNAL_NAME}.source"
SIGNAL_SIM = SIGNAL_RUN_DIR / f"{SIGNAL_NAME}.inc1.id1.sim.gz"
SIGNAL_MANIFEST = DATA / "s3d_signal_replay_manifest.json"
EVENTLIST = (
    ROOT
    / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/eventlists"
    / "Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat"
)

ATM_RUN_DIR = (
    ROOT
    / "runs/geometry_optimization_20260704"
    / "s3d_o9_atm511_sidecar_3m_20260712"
)
ATM_NAME = "Atm511SidecarS3dO9_3M"
ATM_SOURCE = ATM_RUN_DIR / f"{ATM_NAME}.source"
ATM_SIM = ATM_RUN_DIR / f"{ATM_NAME}.inc1.id1.sim.gz"
ATM_LOG = ATM_RUN_DIR / f"cosima_{ATM_NAME}.log"
ATM_MANIFEST = DATA / "s3d_atm511_replay_manifest.json"
ATM_SUMMARY = DATA / "s3d_atm511_replay_summary.json"
SCREENING_ANALYSIS = DATA / "s3d_screening_analysis.json"
SIGNAL_REPLAY_SUMMARY = DATA / "s3d_signal_replay_summary.json"

STEP05_SCRIPT = ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"
STEP06_SCRIPT = (
    ROOT
    / "stepwise_maintenance/step06_mission_time_variation/code"
    / "build_v3p5_centerfinger_step06_time_axis.py"
)
BRIDGE_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5"
    / "step09_optics_bridge_summary.json"
)
AEFF_AUTHORITY = (
    ROOT
    / "stepwise_maintenance/step04_opticsim"
    / "optics_aeff_authority_f10m_a1.json"
)
SCIENCE_LEDGER = (
    ROOT
    / "old/config/science_511_onaxis_source/metadata/science_rate_ledger.csv"
)
BOUNDARY_SUMMARY = (
    ROOT
    / "old/reports/v3p5_boundary_closure_fullstat_v2_exactpos_20260613"
    / "v3p5_boundary_closure_summary.json"
)
C0_CONTEXT = (
    ROOT
    / "engineering/geometry_optimization_20260704"
    / "40_s3c_mainline_lightweight_review_20260710/data"
    / "s3c_mainline_analysis_summary.json"
)
REFERENCE_STEP05 = (
    ROOT
    / "stepwise_maintenance/step05_veto_time_axis"
    / "outputs_Mass_model_511_fullstat_v1_l1"
    / "step05_Mass_model_511_fullstat_v1_l1_response_summary.json"
)
REFERENCE_STEP08 = (
    ROOT
    / "stepwise_maintenance/step08_significance"
    / "outputs_Mass_model_511_fullstat_v1"
    / "step08_Mass_model_511_fullstat_v1_time_dependent_summary.json"
)

MANUSCRIPT_DISPLAY = {
    "optimized": "lightweight optimized active-shield configuration",
    "heavy_control": "otherwise-identical heavy active-shield control",
    "reference_baseline": "reference detector baseline",
}

ALL_TAGS = ("alpha", "eminus", "eplus", "gamma", "muminus", "muplus", "n", "p")
EXPECTED_PROMPT_COUNTS = {"gamma": 12, **{tag: 8 for tag in ALL_TAGS if tag != "gamma"}}
WINDOWS = {
    "broad_480_550": (480.0, 550.0),
    "w2_510p58_511p42": (510.58, 511.42),
}
SIGNAL_EVENTS = 37_194
ATM_EVENTS = 3_000_000
DELAYED_EVENTS = 1_000_000
ACTIVE_VETO_THRESHOLD_KEV = 50.0
NATIVE_BGO_THRESHOLD_KEV = 80.0
COINCIDENCE_WINDOW_S = 1.0e-6
REFERENCE_FLUX = 1.0e-4
MISSION_DAYS = 20.0
SECONDS_PER_DAY = 86_400.0
MAX_TIMELINE_DRAW_LAMBDA = 5_000_000.0
CONFIDENCE = 0.95
ALPHA_TWO_SIDED = 1.0 - CONFIDENCE

POINT_FLUX_SCAN = [3.0e-5, 5.0e-5, 8.0e-5, 1.0e-4, 1.5e-4, 2.0e-4, 3.0e-4]
TRANSIENT_FLUX_SCAN = [1.0e-4, 3.0e-4, 1.0e-3, 3.0e-3]
TRANSIENT_DURATIONS_S = [3600.0, 21600.0, 86400.0, 259200.0]
DIFFUSE_FOV_FLUX_PROXY = 6.26238e-7

TT_RE = re.compile(r"^\s*TT\s+([-+0-9.eE]+)\s*$")
GEOMETRY_RE = re.compile(r"^\s*Geometry\s+(.+?)\s*$", re.M)
_SIM_HEADER_CACHE: dict[tuple[str, bool, int, int], dict[str, Any]] = {}


class ClosureGateError(RuntimeError):
    """A present input violates the paper-grade closure contract."""


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    materialized = list(rows)
    fields: list[str] = []
    for row in materialized:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows({key: row.get(key, "") for key in fields} for row in materialized)


def resolve_repo_path(value: str | Path) -> Path:
    path = Path(str(value).strip())
    return path if path.is_absolute() else ROOT / path


def source_geometry(path: Path) -> list[str]:
    if not path.is_file():
        return []
    return GEOMETRY_RE.findall(path.read_text(encoding="utf-8", errors="replace"))


def exact_geometry(value: str | None) -> bool:
    if value is None or not str(value).strip():
        return False
    path = Path(str(value).strip())
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve() == S3D_GEOMETRY_SETUP.resolve()


def tt_values(path: Path) -> list[float]:
    if not path.is_file():
        return []
    values: list[float] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = TT_RE.match(raw)
        if match:
            values.append(float(match.group(1)))
    return values


def cached_sim_header(path: Path, *, count_events: bool = False) -> dict[str, Any]:
    stat = path.stat() if path.is_file() else None
    key = (
        str(path.resolve()),
        count_events,
        int(stat.st_size) if stat else -1,
        int(stat.st_mtime_ns) if stat else -1,
    )
    if key not in _SIM_HEADER_CACHE:
        _SIM_HEADER_CACHE[key] = sim_header(path, count_events=count_events)
    return _SIM_HEADER_CACHE[key]


def gate(status: str, *, problems: list[str] | None = None, missing: list[str] | None = None, **evidence: Any) -> dict[str, Any]:
    return {
        "status": status,
        "problems": problems or [],
        "missing": missing or [],
        **evidence,
    }


def _prompt_gate() -> dict[str, Any]:
    required = [PROMPT_SUMMARY, PROMPT_NORM, PROMPT_MANIFEST]
    missing = [rel(path) for path in required if not path.is_file()]
    if missing:
        return gate("PENDING_PRODUCTION", missing=missing, expected_jobs=68)

    rows = load_json(PROMPT_SUMMARY)
    manifest_rows = read_csv(PROMPT_MANIFEST)
    problems: list[str] = []
    if not isinstance(rows, list) or len(rows) != 68:
        problems.append(f"run_summary_rows={len(rows) if isinstance(rows, list) else 'not-list'} expected=68")
        rows = rows if isinstance(rows, list) else []
    counts = Counter(str(row.get("particle", "")) for row in rows)
    if dict(counts) != EXPECTED_PROMPT_COUNTS:
        problems.append(f"particle_counts={dict(counts)} expected={EXPECTED_PROMPT_COUNTS}")
    if len(manifest_rows) != 68:
        problems.append(f"run_manifest_rows={len(manifest_rows)} expected=68")

    source_rows = {row.get("job_name", ""): row for row in manifest_rows}
    audited: list[dict[str, Any]] = []
    for row in rows:
        name = str(row.get("job_name", ""))
        sim = resolve_repo_path(str(row.get("sim_path", "")))
        dat = resolve_repo_path(str(row.get("dat_path", "")))
        header = cached_sim_header(sim)
        source_row = source_rows.get(name, {})
        temp_source = resolve_repo_path(str(source_row.get("temp_source", ""))) if source_row.get("temp_source") else Path()
        geoms = source_geometry(temp_source) if source_row else []
        vals = tt_values(dat)
        local: list[str] = []
        if row.get("status") not in ("PASS", "SKIP"):
            local.append(f"status={row.get('status')}")
        if int(row.get("generated_particles") or -1) != int(row.get("events") or -2):
            local.append("generated_particles!=events")
        if not sim.is_file() or not dat.is_file():
            local.append("missing SIM or DAT")
        if len(vals) != 1 or not math.isfinite(vals[0]) or vals[0] <= 0.0:
            local.append(f"TT={vals}")
        if not exact_geometry(header.get("geometry")):
            local.append(f"SIM geometry={header.get('geometry')}")
        if len(geoms) != 1 or not exact_geometry(geoms[0]):
            local.append(f"source geometry={geoms}")
        problems.extend(f"{name}: {item}" for item in local)
        audited.append(
            {
                "job_name": name,
                "particle": row.get("particle"),
                "events": row.get("events"),
                "generated_particles": row.get("generated_particles"),
                "sim": rel(sim),
                "dat": rel(dat),
                "source": rel(temp_source) if source_row else None,
                "tt_s": vals[0] if len(vals) == 1 else vals,
                "geometry": header.get("geometry"),
                "status": "PASS" if not local else "FAIL",
            }
        )

    source_manifest = load_json(PROMPT_SOURCE_MANIFEST) if PROMPT_SOURCE_MANIFEST.is_file() else {}
    if source_manifest.get("status") != "PASS_S3D_O9_ALL8_SOURCE_CARDS":
        problems.append(f"source_migration_status={source_manifest.get('status')}")
    norm = load_json(PROMPT_NORM)
    if int(norm.get("gamma_splits") or -1) != 12:
        problems.append(f"gamma_splits={norm.get('gamma_splits')}")
    if int(norm.get("non_gamma_replicas") or -1) != 8:
        problems.append(f"non_gamma_replicas={norm.get('non_gamma_replicas')}")
    return gate(
        "PASS" if not problems else "FAIL",
        problems=problems,
        expected_jobs=68,
        particle_counts=dict(counts),
        audited_jobs=audited,
        normalization=rel(PROMPT_NORM),
        normalization_rule="per-family rate = 1 / sum(TT_s); never one common prompt time",
    )


def _delayed_gate() -> dict[str, Any]:
    required = [EXACT_SUMMARY, DELAYED_SIM, FIX_AUDIT, FIXED_SOURCE, GROUNDSTATE, NUBASE]
    missing = [rel(path) for path in required if not path.is_file()]
    if missing:
        return gate("PENDING_PRODUCTION", missing=missing, scope="neutron-only activation")
    summary = load_json(EXACT_SUMMARY)
    audit = load_json(FIX_AUDIT)
    campaign = load_json(DELAY_CAMPAIGN) if DELAY_CAMPAIGN.is_file() else {}
    problems: list[str] = []
    transport = summary.get("delayed_transport") or {}
    if not str(summary.get("status", "")).startswith("PASS"):
        problems.append(f"exact_summary_status={summary.get('status')}")
    if transport.get("SE") != DELAYED_EVENTS or transport.get("ID") != DELAYED_EVENTS:
        problems.append(f"delayed_SE_ID={transport.get('SE')}/{transport.get('ID')}")
    if not exact_geometry(str(transport.get("geometry", "")).strip()):
        problems.append(f"delayed_geometry={transport.get('geometry')}")
    transport_path = resolve_repo_path(str(transport.get("path", "")))
    if transport_path.resolve() != DELAYED_SIM.resolve():
        problems.append(f"delayed_transport_path={rel(transport_path)} expected={rel(DELAYED_SIM)}")
    if summary.get("n_pointsource_blocks") != 50_000 or summary.get("seed") != 260613:
        problems.append(f"M_seed={summary.get('n_pointsource_blocks')}/{summary.get('seed')}")
    sampling = summary.get("sampling_audit") or {}
    if sampling.get("status") != "PASS" or sampling.get("problems"):
        problems.append(f"sampling_audit={sampling.get('status')} problems={sampling.get('problems')}")
    fixed_activity = float(summary.get("fixed_total_activity_Bq") or 0.0)
    source_sum = float(summary.get("source_text_sum_flux_Bq") or 0.0)
    delta = abs(source_sum - fixed_activity)
    if fixed_activity <= 0.0 or delta > max(1.0e-6, fixed_activity * 1.0e-8):
        problems.append(f"source_flux_closure={source_sum} vs activity={fixed_activity}")
    if audit.get("status") != "PASS" or audit.get("problems"):
        problems.append(f"groundstate_fix={audit.get('status')} problems={audit.get('problems')}")
    division_rows = audit.get("rows") or []
    if len(division_rows) != 1:
        problems.append(f"TT_division_rows={len(division_rows)} expected=1")
    else:
        row = division_rows[0]
        expected = {"tag": "n", "files": 8, "division": 8.0, "tt_count": 8, "tt_files": 8, "tt_line_count": 8}
        for key, value in expected.items():
            actual = row.get(key)
            if str(actual) != str(value) and not (
                isinstance(value, (int, float)) and actual is not None and float(actual) == float(value)
            ):
                problems.append(f"TT_division_{key}={actual} expected={value}")
    fixed_geoms = source_geometry(FIXED_SOURCE)
    if len(fixed_geoms) != 1 or not exact_geometry(fixed_geoms[0]):
        problems.append(f"fixed_source_geometry={fixed_geoms}")
    gs_rows = read_csv(GROUNDSTATE)
    if not gs_rows:
        problems.append("groundstate_activity_corrections is empty")
    required_cols = {"VN", "ZA", "nuclide", "new_groundstate_activity_Bq", "nubase_half_life_s"}
    if gs_rows and not required_cols.issubset(gs_rows[0]):
        problems.append(f"groundstate_columns_missing={sorted(required_cols - set(gs_rows[0]))}")
    nubase_hash = sha256(NUBASE)
    recorded_hash = campaign.get("groundstate_fix", {}).get("nubase_sha256")
    if campaign.get("status") != "PASS_S3D_O9_NEUTRON_DELAYED_TRANSPORT":
        problems.append(f"delayed_campaign_status={campaign.get('status')}")
    if recorded_hash != nubase_hash:
        problems.append(f"NUBASE_hash={recorded_hash} expected={nubase_hash}")
    exact_manifest_path = resolve_repo_path(str(summary.get("manifest", "")))
    exact_manifest = load_json(exact_manifest_path) if exact_manifest_path.is_file() else {}
    provenance = exact_manifest.get("provenance_contract") or {}
    if not exact_manifest:
        problems.append(f"missing exact-position manifest: {rel(exact_manifest_path)}")
    if provenance.get("nubase_sha256") != nubase_hash:
        problems.append(f"exact-position NUBASE provenance={provenance.get('nubase_sha256')}")
    if int(provenance.get("non_gamma_div") or -1) != 8:
        problems.append(f"exact-position TT division provenance={provenance.get('non_gamma_div')}")
    if provenance.get("geometry_setup") != rel(S3D_GEOMETRY_SETUP):
        problems.append(f"exact-position geometry provenance={provenance.get('geometry_setup')}")
    return gate(
        "PASS" if not problems else "FAIL",
        problems=problems,
        scope="neutron-only activation; not a full-particle activation inventory",
        exact_summary=rel(EXACT_SUMMARY),
        delayed_sim=rel(DELAYED_SIM),
        delayed_transport=transport,
        fixed_total_activity_Bq=fixed_activity,
        source_text_sum_flux_Bq=source_sum,
        source_flux_abs_delta_Bq=delta,
        groundstate_rows=len(gs_rows),
        nubase=rel(NUBASE),
        nubase_sha256=nubase_hash,
        tt_division_rows=division_rows,
        exact_position_manifest=rel(exact_manifest_path),
        provenance_contract=provenance,
    )


def _eventlist_rows_and_hash() -> tuple[int, str | None]:
    if not EVENTLIST.is_file():
        return 0, None
    count = 0
    with EVENTLIST.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if line and not line.startswith("#"):
                count += 1
    return count, sha256(EVENTLIST)


def _signal_gate(deep: bool) -> dict[str, Any]:
    required = [SIGNAL_SOURCE, SIGNAL_SIM, SIGNAL_MANIFEST, EVENTLIST]
    missing = [rel(path) for path in required if not path.is_file()]
    if missing:
        return gate("PENDING_PRODUCTION", missing=missing, expected_events=SIGNAL_EVENTS)
    problems: list[str] = []
    header = cached_sim_header(SIGNAL_SIM, count_events=deep)
    if not exact_geometry(header.get("geometry")):
        problems.append(f"signal_geometry={header.get('geometry')}")
    if header.get("seed") != 260616:
        problems.append(f"signal_seed={header.get('seed')}")
    if deep and (header.get("SE") != SIGNAL_EVENTS or header.get("ID") != SIGNAL_EVENTS):
        problems.append(f"signal_SE_ID={header.get('SE')}/{header.get('ID')}")
    geoms = source_geometry(SIGNAL_SOURCE)
    if len(geoms) != 1 or not exact_geometry(geoms[0]):
        problems.append(f"signal_source_geometry={geoms}")
    rows, digest = _eventlist_rows_and_hash()
    if rows != SIGNAL_EVENTS:
        problems.append(f"eventlist_rows={rows}")
    manifest = load_json(SIGNAL_MANIFEST)
    event_audit = manifest.get("reference_authority", {}).get("eventlist_audit", {})
    if event_audit.get("rows") != SIGNAL_EVENTS or event_audit.get("sha256") != digest:
        problems.append("signal manifest EventList rows/hash mismatch")
    contract = manifest.get("matched_contract", {})
    if contract.get("triggers") != SIGNAL_EVENTS or not contract.get("canonical_sources_identical_except_geometry_run_output"):
        problems.append("signal matched C0/S3d source contract is not PASS")
    return gate(
        "PASS" if not problems else "FAIL",
        problems=problems,
        deep_count_audit=deep,
        header=header,
        eventlist=rel(EVENTLIST),
        eventlist_rows=rows,
        eventlist_sha256=digest,
        manifest=rel(SIGNAL_MANIFEST),
    )


def _atm_gate(deep: bool) -> dict[str, Any]:
    required = [ATM_SOURCE, ATM_SIM, ATM_LOG, ATM_MANIFEST, ATM_SUMMARY]
    missing = [rel(path) for path in required if not path.is_file()]
    if missing:
        return gate("PENDING_PRODUCTION", missing=missing, expected_events=ATM_EVENTS)
    analyzed = load_json(ATM_SUMMARY)
    if analyzed.get("status") != "PASS_S3D_ATM511_4PI_SIDECAR_REPLAY":
        return gate(
            "PENDING_PRODUCTION",
            missing=list(analyzed.get("pending_inputs") or [
                f"atmospheric analyzer status={analyzed.get('status')}"
            ]),
            expected_events=ATM_EVENTS,
            analyzer_summary=rel(ATM_SUMMARY),
            analyzer_status=analyzed.get("status"),
        )
    problems: list[str] = []
    header = (
        cached_sim_header(ATM_SIM, count_events=True)
        if deep
        else analyzed.get("sim_header") or cached_sim_header(ATM_SIM)
    )
    if not exact_geometry(header.get("geometry")):
        problems.append(f"atm511_geometry={header.get('geometry')}")
    if header.get("seed") != 26070917:
        problems.append(f"atm511_seed={header.get('seed')}")
    transport = analyzed.get("transport") or {}
    catalog = analyzed.get("catalog") or {}
    generated = transport.get("events_generated", catalog.get("generated_events"))
    if generated != ATM_EVENTS:
        problems.append(f"atm511_generated={generated}")
    if deep:
        se_value = header.get("SE", transport.get("SE", catalog.get("SE")))
        id_value = header.get("ID", transport.get("ID", catalog.get("ID", generated)))
        if se_value != ATM_EVENTS or id_value != ATM_EVENTS:
            problems.append(f"atm511_SE_ID={se_value}/{id_value}")
    geoms = source_geometry(ATM_SOURCE)
    if len(geoms) != 1 or not exact_geometry(geoms[0]):
        problems.append(f"atm511_source_geometry={geoms}")
    manifest = load_json(ATM_MANIFEST)
    contract = manifest.get("selection_contract") or {}
    if float(contract.get("active_veto_threshold_keV") or -1.0) != ACTIVE_VETO_THRESHOLD_KEV:
        problems.append(f"atm511_veto_threshold={contract.get('active_veto_threshold_keV')}")
    if "monotonic" not in str(contract.get("side_compton_fov", {}).get("knob0_policy", "")).lower():
        problems.append("atm511 Knob0 contract is not monotonic/frozen")
    volume_rule = str(contract.get("active_veto_volume_rule", ""))
    if "w/al" not in volume_rule.lower() or "excluded" not in volume_rule.lower():
        problems.append(f"atm511 active-veto material exclusion={volume_rule}")
    obs = analyzed.get("normalization", {}).get(
        "observation_time_s", analyzed.get("catalog", {}).get("observation_time_s")
    )
    if obs is None or float(obs) <= 0.0:
        problems.append(f"atm511_observation_time_s={obs}")
    required_catalog = (
        "generated_events",
        "kept_events_tes_or_active",
        "detector_catalog_event_rate_cps",
    )
    absent_catalog = [key for key in required_catalog if catalog.get(key) is None]
    if absent_catalog:
        problems.append(f"atm511_catalog_fields_missing={absent_catalog}")
    for selection in WINDOWS:
        window = analyzed.get("windows", {}).get(selection, {})
        required_window = (
            "raw_events", "active_veto_pass_events", "side_compton_fov_pass_events",
            "raw_rate_cps", "active_rate_cps", "final_rate_cps",
        )
        absent_window = [key for key in required_window if window.get(key) is None]
        if absent_window:
            problems.append(f"atm511_{selection}_fields_missing={absent_window}")
    return gate(
        "PASS" if not problems else "FAIL",
        problems=problems,
        deep_count_audit=deep,
        header=header,
        observation_time_s=obs,
        source_model=analyzed.get("source_model"),
        model_scope="semiempirical atmospheric 511-keV sidecar; not native EXPACS",
        manifest=rel(ATM_MANIFEST),
        analyzer_summary=rel(ATM_SUMMARY),
    )


def _policy_gate() -> dict[str, Any]:
    contract = selection_contract()
    det = S3D_GEOMETRY_SETUP.with_suffix("").with_suffix(".det")
    # The setup basename ends in .geo.setup; construct the sibling explicitly.
    det = S3D_GEOMETRY_SETUP.parent / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det"
    text = det.read_text(encoding="utf-8", errors="replace") if det.is_file() else ""
    native = [float(value) for value in re.findall(r"^BGO_S3D_\S+\.TriggerThreshold\s+([-+0-9.eE]+)\s*$", text, re.M)]
    problems: list[str] = []
    if float(contract.get("active_veto_threshold_keV") or -1) != ACTIVE_VETO_THRESHOLD_KEV:
        problems.append("analysis veto threshold is not 50 keV")
    if len(native) != 3 or any(value != NATIVE_BGO_THRESHOLD_KEV for value in native):
        problems.append(f"native_BGO_thresholds={native} expected three 80-keV values")
    knob0 = contract.get("side_compton_fov", {}).get("knob0_policy", "")
    if "monotonic" not in str(knob0).lower() or "literal" not in str(knob0).lower():
        problems.append(f"Knob0_policy={knob0}")
    return gate(
        "PASS" if not problems else "FAIL",
        problems=problems,
        selection_contract=contract,
        analysis_veto_threshold_keV=ACTIVE_VETO_THRESHOLD_KEV,
        native_BGO_detector_thresholds_keV=native,
        systematic_disclosure=(
            "Cosima native BGO detector blocks use 80 keV, while postprocessing sums "
            "matched active deposits and applies <50 keV; both are frozen across comparison branches."
        ),
    )


def _comparison_gate() -> dict[str, Any]:
    required = [
        C0_CONTEXT,
        SCREENING_ANALYSIS,
        SIGNAL_REPLAY_SUMMARY,
        REFERENCE_STEP05,
        REFERENCE_STEP08,
    ]
    missing = [rel(path) for path in required if not path.is_file()]
    if missing:
        return gate("PENDING_PRODUCTION", missing=missing)
    screening = load_json(SCREENING_ANALYSIS)
    signal = load_json(SIGNAL_REPLAY_SUMMARY)
    problems: list[str] = []
    if str(screening.get("status", "")).startswith("FAIL"):
        problems.append(f"matched_screening_status={screening.get('status')}")
    if str(signal.get("status", "")).startswith("FAIL"):
        problems.append(f"matched_signal_status={signal.get('status')}")
    if problems:
        return gate("FAIL", problems=problems)
    pending: list[str] = []
    if screening.get("status") != "PASS_S3D_SCREENING_PROMOTION_GATES":
        pending.append(f"matched screening status={screening.get('status')}")
    if signal.get("status") != "PASS_MATCHED_S3C_C0_S3D_SIGNAL_REPLAY_ANALYZED":
        pending.append(f"matched signal status={signal.get('status')}")
    if pending:
        return gate("PENDING_PRODUCTION", missing=pending)
    reference = reference_detector_baseline_context()
    heavy = heavy_control_direct_comparison()
    if heavy.get("status") != "PASS_MATCHED_HEAVY_CONTROL_DIRECT_COMPARISON":
        return gate("FAIL", problems=[f"heavy-control comparison={heavy.get('status')}"])
    return gate(
        "PASS",
        heavy_control_authority=rel(SCREENING_ANALYSIS),
        reference_detector_authority={
            "step05": rel(REFERENCE_STEP05),
            "step08": rel(REFERENCE_STEP08),
        },
        manuscript_display_names=MANUSCRIPT_DISPLAY,
        reference_status=reference["status"],
    )


def build_preflight(deep: bool = False) -> dict[str, Any]:
    try:
        geometry = gate("PASS", authority=audit_geometry_authority())
    except AuditError as exc:
        geometry = gate("FAIL", problems=[str(exc)])
    gates = {
        "geometry": geometry,
        "prompt_all8": _prompt_gate(),
        "neutron_delayed": _delayed_gate(),
        "focused_signal": _signal_gate(deep),
        "atm511_sidecar": _atm_gate(deep),
        "selection_policy": _policy_gate(),
        "comparison_authorities": _comparison_gate(),
    }
    failed = [name for name, item in gates.items() if item["status"] == "FAIL"]
    pending = [name for name, item in gates.items() if item["status"].startswith("PENDING")]
    status = "FAIL_CLOSED" if failed else "PENDING_PRODUCTION_INPUTS" if pending else "PASS_READY_FOR_STEP05_08"
    payload = {
        "status": status,
        "generated_at_utc": now_utc(),
        "deep_SE_ID_audit": deep,
        "geometry_setup": rel(S3D_GEOMETRY_SETUP),
        "gates": gates,
        "failed_gates": failed,
        "pending_gates": pending,
        "production_launched": False,
        "claim_boundary": (
            "PENDING is not zero and is not transport evidence. No Step05--Step08 result "
            "summary is created until every present input passes and no input is missing."
        ),
        "output_scope": rel(FULLCHAIN),
    }
    write_json(PREFLIGHT_JSON, payload)
    return payload


def require_ready(deep: bool = True) -> dict[str, Any]:
    shallow = build_preflight(deep=False)
    if shallow["failed_gates"]:
        raise ClosureGateError("preflight failed: " + ", ".join(shallow["failed_gates"]))
    if shallow["pending_gates"]:
        return shallow
    payload = build_preflight(deep=deep)
    if payload["failed_gates"]:
        raise ClosureGateError("deep preflight failed: " + ", ".join(payload["failed_gates"]))
    return payload


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def is_s3d_active_veto_volume(volume: str) -> bool:
    upper = str(volume).upper()
    if upper.startswith("CSI_") or "ACTIVE_SHIELD" in upper or "CEBR3" in upper or "BGO" in upper:
        return True
    return upper.startswith("GEOOPT_S2B_CRYOSHELL_PLASTIC")


def configure_step05(module: Any) -> None:
    module.ROOT = ROOT
    module.TOOLS = ROOT / "old/code/tools"
    module.OUT = STEP05_OUT
    module.SUMMARY_JSON = STEP05_CORE_JSON
    module.SUMMARY_MD = STEP05_OUT / "step05_s3d_o9_core_no_atm511_summary.md"
    module.RATES_CSV = STEP05_OUT / "step05_s3d_o9_core_no_atm511_rates.csv"
    module.TIMELINE_CSV = STEP05_OUT / "step05_s3d_o9_core_no_atm511_timeline_rates.csv"
    module.PROMPT_DIR = PROMPT_DIR
    module.PROMPT_NORM = PROMPT_NORM
    module.DELAYED_SIM = DELAYED_SIM
    module.FIXED_SOURCE = FIXED_SOURCE
    module.STEP02_SUMMARY = EXACT_SUMMARY
    module.SCIENCE_SIM = SIGNAL_SIM
    module.STEP09_SUMMARY = BRIDGE_SUMMARY
    module.F10M_A1_AEFF = AEFF_AUTHORITY
    module.SCIENCE_RATE_LEDGER = SCIENCE_LEDGER
    module.BOUNDARY_CLOSURE_SUMMARY = BOUNDARY_SUMMARY
    module.ACTIVE_VETO_THRESHOLD_KEV = ACTIVE_VETO_THRESHOLD_KEV
    module.ACTIVE_VETO_MATCH_DESCRIPTION = (
        "S3d BGO/CsI/ActiveShield/CEBR3 and retained active plastic volumes; "
        "W/Al/Kapton mechanical volumes excluded"
    )
    module.is_v3p5_active_veto_volume = is_s3d_active_veto_volume
    module._PROMPT_NORMALIZATION_AUDIT = None


def build_timeline_response(step05: Any, cat: dict[str, Any], disk: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    full_obs = float(step05.delayed_time_s())
    total_rate = float(np.sum(np.asarray(cat["rate_hz"], dtype=np.float64)))
    full_lambda = total_rate * full_obs
    if full_lambda <= MAX_TIMELINE_DRAW_LAMBDA:
        obs = full_obs
        mode = "FULL_INTERVAL_POISSON_DRAW_CORE_STREAMS"
    else:
        obs = MAX_TIMELINE_DRAW_LAMBDA / total_rate
        mode = "ADAPTIVE_BOUNDED_HIGH_RATE_POISSON_DRAW_CORE_STREAMS"
    rng = np.random.default_rng(step05.RNG_SEED)
    draw = step05.draw_timeline(cat, obs, rng)
    timeline = step05.analyze_timeline(cat, draw, obs, disk, "keep")
    return timeline, draw["draw_summary"], {
        "mode": mode,
        "full_obs_time_s": full_obs,
        "timeline_obs_time_s": obs,
        "full_interval_expected_instances": full_lambda,
        "max_timeline_draw_lambda": MAX_TIMELINE_DRAW_LAMBDA,
        "scope": "prompt+neutron-delayed+focused-signal diagnostic only; atm511 occupancy is merged analytically below",
    }


def poisson_upper_95(count: int) -> float:
    return float(0.5 * chi2.ppf(1.0 - ALPHA_TWO_SIDED / 2.0, 2.0 * (count + 1)))


def binomial_lower_95(successes: int, trials: int) -> float:
    if successes <= 0 or trials <= 0:
        return 0.0
    if successes >= trials:
        return float(beta.ppf(ALPHA_TWO_SIDED / 2.0, successes, 1))
    return float(beta.ppf(ALPHA_TWO_SIDED / 2.0, successes, trials - successes + 1))


def analyze_atm(step05: Any) -> dict[str, Any]:
    """Consume the independent screening analyzer's atmospheric authority.

    The screening analyzer owns ``ATM_SUMMARY``.  This closure validates and
    consumes that result rather than overwriting it or silently recomputing a
    competing catalog.
    """
    del step05
    payload = load_json(ATM_SUMMARY)
    if payload.get("status") != "PASS_S3D_ATM511_4PI_SIDECAR_REPLAY":
        raise ClosureGateError(f"atmospheric analyzer is not PASS: {payload.get('status')}")
    check = _atm_gate(deep=True)
    if check["status"] != "PASS":
        raise ClosureGateError("atmospheric analyzer gate failed: " + "; ".join(check["problems"]))
    return payload


def selected_prompt_components(cat: dict[str, Any], step05: Any, bounds: tuple[float, float], disk: dict[str, Any]) -> list[dict[str, Any]]:
    lo, hi = bounds
    selected: dict[str, dict[str, Any]] = {
        tag: {
            "tag": tag,
            "events": 0,
            "rate_cps": 0.0,
            "event_weight_cps": float(weight),
        }
        for tag, weight in step05.prompt_rate_by_tag().items()
    }
    mask = (
        (cat["stream"] == "prompt")
        & (cat["tes_total_keV"] >= lo)
        & (cat["tes_total_keV"] < hi)
        & (cat["bgo_total_keV"] < ACTIVE_VETO_THRESHOLD_KEV)
    )
    for index in np.flatnonzero(mask):
        keep, _cls = step05.side_keep_from_hits(step05.event_hits(cat, int(index)), disk, "keep")
        if not keep:
            continue
        tag = str(cat["tag"][index])
        if tag not in selected:
            raise ClosureGateError(f"selected prompt tag {tag!r} is absent from the TT audit")
        rec = selected[tag]
        rec["events"] += 1
        rec["rate_cps"] += float(cat["rate_hz"][index])
    for rec in selected.values():
        rec["rate_upper95_cps"] = poisson_upper_95(int(rec["events"])) * float(rec["event_weight_cps"])
    return [selected[tag] for tag in sorted(selected)]


def merge_step05_window(
    item: dict[str, Any],
    atm: dict[str, Any],
    prompt_components: list[dict[str, Any]],
    science_trials: int,
    delayed_event_weight_cps: float,
) -> None:
    item["by_stream"]["atm511_sidecar"] = {
        "raw_events": atm["raw_events"],
        "active_veto_pass_events": atm["active_veto_pass_events"],
        "side_compton_fov_pass_events": atm["side_compton_fov_pass_events"],
        "raw_rate_s-1": atm["raw_rate_cps"],
        "active_veto_pass_rate_s-1": atm["active_rate_cps"],
        "side_compton_fov_pass_rate_s-1": atm["final_rate_cps"],
        "side_compton_class_counts": atm["side_compton_class_counts"],
    }
    for stage, event_key, rate_key in (
        ("raw", "raw_events", "raw_rate_s-1"),
        ("active_veto_pass", "active_veto_pass_events", "active_veto_pass_rate_s-1"),
        ("side_compton_fov_pass", "side_compton_fov_pass_events", "side_compton_fov_pass_rate_s-1"),
    ):
        item["total"][stage] = {
            "events": sum(int(row[event_key]) for row in item["by_stream"].values()),
            "rate_s-1": sum(float(row[rate_key]) for row in item["by_stream"].values()),
        }
    by = item["by_stream"]
    prompt = float(by["prompt"]["side_compton_fov_pass_rate_s-1"])
    delayed = float(by["delayed"]["side_compton_fov_pass_rate_s-1"])
    atm_rate = float(atm["final_rate_cps"])
    science_unit = float(by["science"]["side_compton_fov_pass_rate_s-1"])
    phys = item["physical_reference_flux"]
    injection = float(phys["rate_to_v3p5_injection_plane_s-1"])
    signal = science_unit * injection
    background = prompt + delayed + atm_rate
    mission_s = MISSION_DAYS * SECONDS_PER_DAY
    z = signal * mission_s / math.sqrt(background * mission_s) if background > 0.0 else math.inf
    delayed_events = int(by["delayed"]["side_compton_fov_pass_events"])
    delayed_upper = poisson_upper_95(delayed_events) * delayed_event_weight_cps
    prompt_upper = sum(float(row["rate_upper95_cps"]) for row in prompt_components)
    atm_weight = float(
        atm.get(
            "event_rate_weight_cps",
            float(atm["final_rate_cps"]) / max(int(atm["side_compton_fov_pass_events"]), 1),
        )
    )
    atm_upper = float(
        atm.get(
            "final_rate_upper95_cps",
            poisson_upper_95(int(atm["side_compton_fov_pass_events"])) * atm_weight,
        )
    )
    signal_events = int(by["science"]["side_compton_fov_pass_events"])
    eff = signal_events / science_trials
    eff_lower = binomial_lower_95(signal_events, science_trials)
    signal_lower = signal * eff_lower / eff if eff > 0.0 else 0.0
    background_upper = prompt_upper + delayed_upper + atm_upper
    z_lower = signal_lower * mission_s / math.sqrt(background_upper * mission_s) if background_upper > 0.0 else 0.0
    phys.update(
        {
            "prompt_background_cps": prompt,
            "delayed_background_cps": delayed,
            "atm511_sidecar_background_cps": atm_rate,
            "background_cps": background,
            "signal_cps_at_reference_flux": signal,
            "source_counts_20d": signal * mission_s,
            "background_counts_20d": background * mission_s,
            "Z20d_direct_s_over_sqrt_b": z,
            "T3_day_constant_rate_direct": MISSION_DAYS * (3.0 / z) ** 2,
            "T5_day_constant_rate_direct": MISSION_DAYS * (5.0 / z) ** 2,
            "flux_3sigma_20d_ph_cm2_s": REFERENCE_FLUX * 3.0 / z,
            "low_stat_final_background_events": (
                sum(int(row["events"]) for row in prompt_components)
                + delayed_events
                + int(atm["side_compton_fov_pass_events"])
            ),
            "uncertainty_95": {
                "method": "independent Garwood two-sided 95% upper counts per background component; Clopper-Pearson two-sided 95% lower signal acceptance",
                "prompt_components": prompt_components,
                "prompt_background_upper95_cps": prompt_upper,
                "delayed_background_upper95_cps": delayed_upper,
                "atm511_background_upper95_cps": atm_upper,
                "background_upper95_cps": background_upper,
                "signal_trials": science_trials,
                "signal_successes": signal_events,
                "signal_acceptance": eff,
                "signal_acceptance_lower95": eff_lower,
                "signal_cps_lower95_at_reference_flux": signal_lower,
                "Z20d_conservative_95": z_lower,
                "flux_3sigma_20d_conservative_95_ph_cm2_s": REFERENCE_FLUX * 3.0 / z_lower if z_lower > 0.0 else math.inf,
            },
        }
    )


def write_step05_rates(payload: dict[str, Any]) -> None:
    rows: list[dict[str, Any]] = []
    for selection, item in payload["windows"].items():
        for stream, record in item["by_stream"].items():
            for stage, event_key, rate_key in (
                ("raw", "raw_events", "raw_rate_s-1"),
                ("active_veto_pass", "active_veto_pass_events", "active_veto_pass_rate_s-1"),
                ("side_compton_fov_pass", "side_compton_fov_pass_events", "side_compton_fov_pass_rate_s-1"),
            ):
                rows.append({"selection_id": selection, "stream": stream, "stage": stage, "events": record[event_key], "rate_cps": record[rate_key]})
    write_csv(STEP05_RATES, rows)


def run_step05(workers: int, rebuild_cache: bool = False) -> dict[str, Any]:
    preflight = require_ready(deep=True)
    if preflight["status"] != "PASS_READY_FOR_STEP05_08":
        return preflight
    step05 = load_module(STEP05_SCRIPT, "s3d_o9_step05_core")
    configure_step05(step05)
    STEP05_OUT.mkdir(parents=True, exist_ok=True)
    prompt_audit = step05.prompt_normalization_audit()
    step05.write_prompt_normalization_audit(prompt_audit)
    if prompt_audit.get("problems"):
        raise ClosureGateError("Step05 prompt TT audit failed: " + "; ".join(prompt_audit["problems"]))
    adr = step05.load_adr_module()
    step05.configure_parser(adr)
    cat = adr.load_or_build_catalog(STEP05_OUT, workers=workers, science_flux=1.0, rebuild=rebuild_cache)
    refreshed = step05.refresh_prompt_event_rates(cat)
    if refreshed:
        cache = STEP05_OUT / "work/event_catalog.pkl"
        cache.parent.mkdir(parents=True, exist_ok=True)
        with cache.open("wb") as handle:
            pickle.dump(cat, handle, protocol=pickle.HIGHEST_PROTOCOL)
    disk = step05.side_entry_disk()
    windows = {name: step05.summarize_window(cat, *bounds, disk=disk, reject_policy="keep") for name, bounds in WINDOWS.items()}
    science_norm = step05.load_science_physical_normalization()
    step05.add_physical_reference_to_windows(windows, science_norm)
    timeline, draw_summary, timeline_model = build_timeline_response(step05, cat, disk)
    core = {
        "status": "PASS_S3D_O9_STEP05_CORE_ALL8_PROMPT_NEUTRON_DELAYED_MATCHED_SIGNAL_NO_ATM511",
        "statistics_label": "s3d_o9_fullchain_20260712",
        "generated_at_utc": now_utc(),
        "claim_level": "S3D_O9_CORE_STEP05_ONLY_NOT_FULL_BACKGROUND",
        "preflight": preflight,
        "inputs": {"prompt_dir": rel(PROMPT_DIR), "delayed_sim": rel(DELAYED_SIM), "science_sim": rel(SIGNAL_SIM), "signal_manifest": rel(SIGNAL_MANIFEST)},
        "normalization": {
            "prompt_rate_rule": "per-family event rate = 1 / sum(TT_s)",
            "prompt_normalization_audit": prompt_audit,
            "delayed_time_s": step05.delayed_time_s(),
            "science_unit_injection_rate_s-1": 1.0,
            "active_veto_threshold_keV": ACTIVE_VETO_THRESHOLD_KEV,
            "native_BGO_detector_threshold_keV": NATIVE_BGO_THRESHOLD_KEV,
            "reject_policy": "keep",
            "knob0_policy": "frozen monotonic current policy; no literal S0/S1 event resurrection",
            "coincidence_window_s": COINCIDENCE_WINDOW_S,
        },
        "science_physical_normalization": science_norm,
        "catalog": {
            "events_kept": int(len(cat["stream"])),
            "pixel_hits_kept": int(len(cat["pix_e"])),
            "by_stream_events": {stream: int(np.sum(cat["stream"] == stream)) for stream in ("prompt", "delayed", "science")},
            "by_stream_event_rate_hz": {stream: float(np.sum(cat["rate_hz"][cat["stream"] == stream])) for stream in ("prompt", "delayed", "science")},
        },
        "windows": windows,
        "timeline": timeline,
        "timeline_draw_summary": draw_summary,
        "timeline_model": timeline_model,
    }
    write_json(STEP05_CORE_JSON, core)
    atm_summary = analyze_atm(step05)
    for name, item in windows.items():
        prompt_components = selected_prompt_components(cat, step05, WINDOWS[name], disk)
        merge_step05_window(
            item,
            atm_summary["windows"][name],
            prompt_components,
            SIGNAL_EVENTS,
            1.0 / float(step05.delayed_time_s()),
        )
    core["status"] = "PASS_S3D_O9_STEP05_FULLCHAIN_ALL8_PROMPT_NEUTRON_DELAYED_ATM511_MATCHED_SIGNAL"
    core["claim_level"] = "S3D_O9_PAPER_GRADE_STEP05_RATE_AUTHORITY_NOT_STEP08"
    core["inputs"]["atm511_sim"] = rel(ATM_SIM)
    core["inputs"]["atm511_summary"] = rel(ATM_SUMMARY)
    core["normalization"]["atm511_observation_time_s"] = atm_summary["normalization"]["observation_time_s"]
    core["normalization"]["atm511_phi_4pi_day15_ph_cm2_s"] = atm_summary["source_model"]["phi_4pi_ph_cm2_s"]
    core["catalog"]["atm511_sidecar"] = atm_summary["catalog"]
    core["catalog"]["full_background_occupancy_day15_hz"] = (
        core["catalog"]["by_stream_event_rate_hz"]["prompt"]
        + core["catalog"]["by_stream_event_rate_hz"]["delayed"]
        + atm_summary["catalog"]["detector_catalog_event_rate_cps"]
    )
    core["timeline_draw_summary"]["atm511_sidecar"] = {
        "rate_hz": atm_summary["catalog"]["detector_catalog_event_rate_cps"],
        "mode": "analytic independent Poisson occupancy merged downstream",
        "pending_is_zero": False,
    }
    core["method_disclosures"] = [
        "Atmospheric-511 is a semiempirical sidecar, not native EXPACS.",
        "Its day-15 angular transfer is held fixed while Step06 scales phi_4pi with depth and rigidity.",
        "The 50-keV postprocessing veto and native 80-keV BGO detector threshold are distinct frozen settings.",
        "The monotonic Knob0 policy never resurrects an event rejected by the retained selection.",
    ]
    reference = reference_detector_baseline_context()
    optimized_w2 = core["windows"]["w2_510p58_511p42"]["physical_reference_flux"]
    core["comparisons"] = {
        "mass_reduction_direct_heavy_control": heavy_control_direct_comparison(),
        "whole_optimization_vs_reference_detector": {
            "status": "PASS_STEP05_RATE_COMPARISON",
            "manuscript_display_names": {
                "optimized": MANUSCRIPT_DISPLAY["optimized"],
                "baseline": MANUSCRIPT_DISPLAY["reference_baseline"],
            },
            "reference_authority": reference,
            "optimized_over_reference_background_cps": (
                float(optimized_w2["background_cps"])
                / float(reference["step05_w2_background_cps"])
            ),
            "optimized_over_reference_signal_cps": (
                float(optimized_w2["signal_cps_at_reference_flux"])
                / float(reference["step05_w2_signal_cps_at_reference_flux"])
            ),
            "causal_interpretation": (
                "This reports the outcome of the complete optimized design relative to the "
                "paper reference detector; it must not be attributed to mass reduction alone."
            ),
        },
    }
    write_step05_rates(core)
    write_json(STEP05_JSON, core)
    return core


def f_r_harris(rc_gv: float) -> float:
    if rc_gv < 7.0:
        return 1.000
    if rc_gv < 9.0:
        return 0.805
    if rc_gv < 11.0:
        return 0.624
    if rc_gv < 13.0:
        return 0.532
    return 0.479


def atm_phi_4pi(model: dict[str, Any], depth: float, rc_gv: float) -> float:
    phi_ref = float(model["phi_ref_ph_cm2_s"])
    eta = float(model["eta"])
    x_ref = float(model["X_ref_g_cm2"])
    return phi_ref * f_r_harris(rc_gv) * (depth / x_ref) ** eta


def run_step06() -> dict[str, Any]:
    if not STEP05_JSON.is_file():
        raise ClosureGateError("Step05 fullchain summary is absent")
    step05 = load_json(STEP05_JSON)
    if step05.get("status") != "PASS_S3D_O9_STEP05_FULLCHAIN_ALL8_PROMPT_NEUTRON_DELAYED_ATM511_MATCHED_SIGNAL":
        raise ClosureGateError(f"Step05 status is not authoritative: {step05.get('status')}")
    module = load_module(STEP06_SCRIPT, "s3d_o9_step06_helpers")
    module.ROOT = ROOT
    module.GROUNDSTATE = GROUNDSTATE
    module.SECONDS_PER_DAY = SECONDS_PER_DAY
    trajectory, atmosphere = module.build_trajectory(
        float(step05["science_physical_normalization"]["atmospheric_transmission"]["T_atm"])
    )
    per_key, totals, activity_audit = module.integrate_activity(trajectory)
    activity_scale = {int(row["time_bin_id"]): float(row["activity_scale_to_day15"]) for row in totals}
    atm_model = load_json(ATM_MANIFEST)["source_model_frozen_from_c0"]
    phi_day15 = float(atm_model["phi_4pi_ph_cm2_s"])
    prompt_occ = float(step05["catalog"]["by_stream_event_rate_hz"]["prompt"])
    delayed_occ = float(step05["catalog"]["by_stream_event_rate_hz"]["delayed"])
    atm_occ = float(step05["catalog"]["atm511_sidecar"]["detector_catalog_event_rate_cps"])
    bg_rows: list[dict[str, Any]] = []
    for selection, window in step05["windows"].items():
        by = window["by_stream"]
        uncertainty = window["physical_reference_flux"]["uncertainty_95"]
        science_scale_rate = float(window["physical_reference_flux"]["signal_cps_at_reference_flux"])
        science_lower_rate = float(uncertainty["signal_cps_lower95_at_reference_flux"])
        for trow in trajectory:
            idx = int(trow["time_bin_id"])
            pscale = float(trow["prompt_scale_to_day15"])
            dscale = activity_scale[idx]
            sscale = float(trow["science_atm_scale_to_day15"])
            phi = atm_phi_4pi(atm_model, float(trow["depth_g_cm2"]), float(trow["Rc_GV"]))
            ascale = phi / phi_day15
            row: dict[str, Any] = {
                "selection_id": selection,
                "time_bin_id": idx,
                "time_mid_s": trow["time_mid_s"], "day_mid": trow["day_mid"], "dt_s": trow["dt_s"],
                "prompt_scale_to_day15": pscale,
                "delayed_activity_scale_to_day15": dscale,
                "science_atm_scale_to_day15": sscale,
                "atm511_phi_4pi_ph_cm2_s": phi,
                "atm511_phi_4pi_scale_to_day15": ascale,
                "atm511_fixed_day15_angular_transfer": True,
                "T_atm_511": trow["T_atm_511"],
                "prompt_event_rate_hz": prompt_occ * pscale,
                "delayed_event_rate_hz": delayed_occ * dscale,
                "atm511_event_rate_hz": atm_occ * ascale,
            }
            for stage, key in (("raw", "raw_rate_s-1"), ("active", "active_veto_pass_rate_s-1"), ("final", "side_compton_fov_pass_rate_s-1")):
                prompt = float(by["prompt"][key]) * pscale
                delayed = float(by["delayed"][key]) * dscale
                atm = float(by["atm511_sidecar"][key]) * ascale
                science_unit = float(by["science"][key])
                injection = float(step05["science_physical_normalization"]["rate_to_v3p5_injection_plane_s-1"])
                science = science_unit * injection * sscale
                row[f"prompt_{stage}_cps"] = prompt
                row[f"delayed_{stage}_cps"] = delayed
                row[f"atm511_{stage}_cps"] = atm
                row[f"background_{stage}_cps"] = prompt + delayed + atm
                row[f"science_{stage}_cps_at_ref_flux"] = science
            row["prompt_final_upper95_cps"] = float(uncertainty["prompt_background_upper95_cps"]) * pscale
            row["delayed_final_upper95_cps"] = float(uncertainty["delayed_background_upper95_cps"]) * dscale
            row["atm511_final_upper95_cps"] = float(uncertainty["atm511_background_upper95_cps"]) * ascale
            row["background_final_upper95_cps"] = row["prompt_final_upper95_cps"] + row["delayed_final_upper95_cps"] + row["atm511_final_upper95_cps"]
            row["science_final_lower95_cps_at_ref_flux"] = science_lower_rate * sscale
            bg_rows.append(row)
    STEP06_OUT.mkdir(parents=True, exist_ok=True)
    write_csv(STEP06_OUT / "trajectory_profile.csv", trajectory)
    write_csv(STEP06_OUT / "atmosphere_transmission_511_by_time.csv", trajectory)
    write_csv(STEP06_OUT / "activity_by_time_nuclide_volume.csv", per_key)
    write_csv(STEP06_OUT / "total_activity_by_time.csv", totals)
    write_csv(STEP06_BG, bg_rows)
    w2 = [row for row in bg_rows if row["selection_id"] == "w2_510p58_511p42"]
    day15 = min(w2, key=lambda row: abs(float(row["day_mid"]) - 15.0))
    dt = sum(float(row["dt_s"]) for row in w2)
    payload = {
        "status": "PASS_S3D_O9_STEP06_FULLCHAIN_TIME_AXIS",
        "generated_at_utc": now_utc(),
        "inputs": {"step05_summary": rel(STEP05_JSON), "groundstate_activity_corrections": rel(GROUNDSTATE), "atm511_summary": rel(ATM_SUMMARY)},
        "normalization": {
            "reference_flux_ph_cm2_s": REFERENCE_FLUX,
            "coincidence_window_s": COINCIDENCE_WINDOW_S,
            "separate_scales": ["prompt_scale_to_day15", "delayed_activity_scale_to_day15", "science_atm_scale_to_day15", "atm511_phi_4pi_scale_to_day15"],
        },
        "trajectory": {"mission_days": MISSION_DAYS, "step_day": module.STEP_DAY, "bins": len(trajectory)},
        "activity": activity_audit,
        "atmosphere_model": atmosphere,
        "atm511_model": {
            "source": "semiempirical 4pi sidecar",
            "day15_phi_4pi_ph_cm2_s": phi_day15,
            "mission_scaling": "phi_ref * f_R(Rc) * (depth/X_ref)^eta",
            "angular_transfer": "fixed at transported day-15 S1 angular distribution; only total phi_4pi is scaled",
        },
        "checks": {
            "w2_day15_background_final_cps": day15["background_final_cps"],
            "w2_day15_background_final_upper95_cps": day15["background_final_upper95_cps"],
            "w2_day15_science_final_cps_at_ref_flux": day15["science_final_cps_at_ref_flux"],
            "w2_day15_science_final_lower95_cps_at_ref_flux": day15["science_final_lower95_cps_at_ref_flux"],
            "w2_mission_mean_background_final_cps": sum(float(row["background_final_cps"]) * float(row["dt_s"]) for row in w2) / dt,
            "w2_mission_mean_atm511_final_cps": sum(float(row["atm511_final_cps"]) * float(row["dt_s"]) for row in w2) / dt,
        },
        "outputs": {"summary_json": rel(STEP06_JSON), "background_time_variation": rel(STEP06_BG)},
        "method_caveats": [
            "No per-time-bin Cosima replay is performed.",
            "Atmospheric-line total flux changes with depth/Rc while the transported day-15 angular transfer remains fixed.",
            "Prompt, delayed activity, science transmission, and atmospheric-line scales are never collapsed into one factor.",
        ],
    }
    write_json(STEP06_JSON, payload)
    return payload


def build_response_rows(step05: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for selection, item in step05["windows"].items():
        phys = item["physical_reference_flux"]
        unc = phys["uncertainty_95"]
        response = float(phys["signal_cps_at_reference_flux"]) / REFERENCE_FLUX
        response_lower = float(unc["signal_cps_lower95_at_reference_flux"]) / REFERENCE_FLUX
        rows.append(
            {
                "selection_id": selection,
                "lo_keV": item["window_keV"][0], "hi_keV": item["window_keV"][1],
                "reference_flux_ph_cm2_s": REFERENCE_FLUX,
                "science_final_response_cps_per_ph_cm2_s": response,
                "science_final_response_lower95_cps_per_ph_cm2_s": response_lower,
                "background_final_cps_day15": phys["background_cps"],
                "background_final_upper95_cps_day15": unc["background_upper95_cps"],
                "prompt_background_cps_day15": phys["prompt_background_cps"],
                "delayed_background_cps_day15": phys["delayed_background_cps"],
                "atm511_background_cps_day15": phys["atm511_sidecar_background_cps"],
            }
        )
    return rows


def build_source_case_rates(response_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for response_row in response_rows:
        selection = response_row["selection_id"]
        response = float(response_row["science_final_response_cps_per_ph_cm2_s"])
        response_lower = float(response_row["science_final_response_lower95_cps_per_ph_cm2_s"])
        background = float(response_row["background_final_cps_day15"])
        background_upper = float(response_row["background_final_upper95_cps_day15"])
        common = {
            "selection_id": selection,
            "background_final_cps_day15": background,
            "background_final_upper95_cps_day15": background_upper,
            "response_cps_per_ph_cm2_s": response,
            "response_lower95_cps_per_ph_cm2_s": response_lower,
        }
        for flux in POINT_FLUX_SCAN:
            rows.append({**common, "analysis_case_id": f"A_point_{selection}_F{flux:.3g}", "source_case_id": "A_GC_CENTRAL_COMPACT_POINT", "source_class": "point_steady", "model_id": "mono_511", "flux_ph_cm2_s": flux, "duration_s": "", "final_rate_day15_cps": response * flux, "final_rate_lower95_day15_cps": response_lower * flux})
        rows.append({**common, "analysis_case_id": f"B_diffuse_proxy_{selection}", "source_case_id": "B_GC_DIFFUSE_BULGE_DISK_PROXY", "source_class": "extended_steady", "model_id": "routeB_fov_flux_proxy", "flux_ph_cm2_s": DIFFUSE_FOV_FLUX_PROXY, "duration_s": "", "final_rate_day15_cps": response * DIFFUSE_FOV_FLUX_PROXY, "final_rate_lower95_day15_cps": response_lower * DIFFUSE_FOV_FLUX_PROXY})
        for flux in TRANSIENT_FLUX_SCAN:
            for duration in TRANSIENT_DURATIONS_S:
                rows.append({**common, "analysis_case_id": f"C_transient_{selection}_F{flux:.3g}_T{int(duration)}s", "source_case_id": "C_V404_TRANSIENT_BENCHMARK", "source_class": "point_transient", "model_id": "mono_511_transient", "flux_ph_cm2_s": flux, "duration_s": duration, "final_rate_day15_cps": response * flux, "final_rate_lower95_day15_cps": response_lower * flux})
    return rows


def run_step07() -> dict[str, Any]:
    if not STEP05_JSON.is_file() or not STEP06_JSON.is_file():
        raise ClosureGateError("Step05/Step06 authority is absent")
    step05, step06 = load_json(STEP05_JSON), load_json(STEP06_JSON)
    if not str(step05.get("status", "")).startswith("PASS_S3D_O9_STEP05_FULLCHAIN") or step06.get("status") != "PASS_S3D_O9_STEP06_FULLCHAIN_TIME_AXIS":
        raise ClosureGateError("Step05/Step06 status is not authoritative")
    signal_gate = _signal_gate(deep=True)
    if signal_gate["status"] != "PASS" or signal_gate.get("eventlist_rows") != SIGNAL_EVENTS:
        raise ClosureGateError("matched focused-signal provenance gate failed")
    response = build_response_rows(step05)
    rates = build_source_case_rates(response)
    STEP07_OUT.mkdir(parents=True, exist_ok=True)
    write_csv(STEP07_OUT / "s3d_o9_response_authority.csv", response)
    write_csv(STEP07_RATES, rates)
    w2 = next(row for row in response if row["selection_id"] == "w2_510p58_511p42")
    payload = {
        "status": "PASS_S3D_O9_STEP07_MATCHED_SIGNAL_SOURCE_CASES",
        "generated_at_utc": now_utc(),
        "inputs": {"step05_summary": rel(STEP05_JSON), "step06_summary": rel(STEP06_JSON), "signal_manifest": rel(SIGNAL_MANIFEST), "signal_sim": rel(SIGNAL_SIM)},
        "authority": {
            "geometry_setup": rel(S3D_GEOMETRY_SETUP),
            "eventlist": rel(EVENTLIST), "eventlist_rows": SIGNAL_EVENTS,
            "eventlist_sha256": signal_gate["eventlist_sha256"],
            "SE": signal_gate["header"].get("SE"), "ID": signal_gate["header"].get("ID"),
            "no_signal_substitution": "Mass_model/fix5/retained generic signal products are not consumed",
        },
        "checks": {"source_case_rows": len(rates), "w2_response_cps_per_ph_cm2_s": w2["science_final_response_cps_per_ph_cm2_s"], "w2_background_final_cps": w2["background_final_cps_day15"]},
        "outputs": {"summary_json": rel(STEP07_JSON), "response_authority": rel(STEP07_OUT / "s3d_o9_response_authority.csv"), "source_case_rates": rel(STEP07_RATES)},
    }
    write_json(STEP07_JSON, payload)
    return payload


def f(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = row.get(key, default)
    return default if value in ("", None) else float(value)


def active_dt(case: dict[str, Any], elapsed: float, dt_s: float) -> float:
    if case["source_class"] != "point_transient":
        return dt_s
    duration = f(case, "duration_s")
    return max(0.0, min(elapsed + dt_s, duration) - elapsed)


def crossing_time(days: list[float], values: list[float], threshold: float) -> float | None:
    for index, value in enumerate(values):
        if value < threshold:
            continue
        if index == 0:
            return days[0]
        x0, x1 = days[index - 1], days[index]
        y0, y1 = values[index - 1], values[index]
        return x1 if y1 == y0 else x0 + (threshold - y0) * (x1 - x0) / (y1 - y0)
    return None


def extrapolated_time(final_day: float, final_z: float, threshold: float) -> float | None:
    return None if final_z <= 0.0 else final_day * (threshold / final_z) ** 2


def fold_cases(cases: list[dict[str, Any]], background: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in background:
        grouped.setdefault(str(row["selection_id"]), []).append(row)
    for rows in grouped.values():
        rows.sort(key=lambda row: int(row["time_bin_id"]))
    cumulative: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    accidentals: list[dict[str, Any]] = []
    for selection, rows in grouped.items():
        for row in rows:
            occupancy = f(row, "prompt_event_rate_hz") + f(row, "delayed_event_rate_hz") + f(row, "atm511_event_rate_hz")
            live = math.exp(-occupancy * COINCIDENCE_WINDOW_S)
            accidentals.append({"selection_id": selection, "time_bin_id": row["time_bin_id"], "day_mid": row["day_mid"], "prompt_event_rate_hz": row["prompt_event_rate_hz"], "delayed_event_rate_hz": row["delayed_event_rate_hz"], "atm511_event_rate_hz": row["atm511_event_rate_hz"], "coincidence_occupancy_rate_hz": occupancy, "coincidence_window_s": COINCIDENCE_WINDOW_S, "accidental_live_factor": live, "accidental_loss_fraction": 1.0 - live})
    for case in cases:
        rows = grouped[str(case["selection_id"])]
        elapsed = cum_s = cum_b = cum_s_low = cum_b_up = 0.0
        days: list[float] = []
        zs: list[float] = []
        zs_conservative: list[float] = []
        for row in rows:
            dt_s = f(row, "dt_s")
            use_dt = active_dt(case, elapsed, dt_s)
            occupancy = f(row, "prompt_event_rate_hz") + f(row, "delayed_event_rate_hz") + f(row, "atm511_event_rate_hz")
            live = math.exp(-occupancy * COINCIDENCE_WINDOW_S)
            science_scale = f(row, "science_atm_scale_to_day15")
            source = f(case, "final_rate_day15_cps") * science_scale
            source_low = f(case, "final_rate_lower95_day15_cps") * science_scale
            bkg = f(row, "background_final_cps")
            bkg_up = f(row, "background_final_upper95_cps")
            if use_dt > 0.0:
                cum_s += source * live * use_dt
                cum_b += bkg * live * use_dt
                cum_s_low += source_low * live * use_dt
                cum_b_up += bkg_up * live * use_dt
            day = (elapsed + dt_s) / SECONDS_PER_DAY
            z = cum_s / math.sqrt(cum_b) if cum_b > 0.0 else 0.0
            z_cons = cum_s_low / math.sqrt(cum_b_up) if cum_b_up > 0.0 else 0.0
            days.append(day); zs.append(z); zs_conservative.append(z_cons)
            cumulative.append({"analysis_case_id": case["analysis_case_id"], "source_case_id": case["source_case_id"], "source_class": case["source_class"], "selection_id": case["selection_id"], "time_bin_id": row["time_bin_id"], "day_mid": row["day_mid"], "elapsed_stop_day": day, "dt_s": dt_s, "dt_active_s": use_dt, "atm511_event_rate_hz": row["atm511_event_rate_hz"], "coincidence_occupancy_rate_hz": occupancy, "accidental_live_factor": live, "source_final_cps_noacc": source, "source_final_lower95_cps_noacc": source_low, "background_final_cps_noacc": bkg, "background_final_upper95_cps_noacc": bkg_up, "cumulative_source_counts": cum_s, "cumulative_background_counts": cum_b, "cumulative_source_lower95_counts": cum_s_low, "cumulative_background_upper95_counts": cum_b_up, "counting_Z": z, "counting_Z_conservative95": z_cons})
            elapsed += dt_s
        final_day = days[-1]
        t3, t5 = crossing_time(days, zs, 3.0), crossing_time(days, zs, 5.0)
        t3c, t5c = crossing_time(days, zs_conservative, 3.0), crossing_time(days, zs_conservative, 5.0)
        summaries.append({**case, "total_source_counts": cum_s, "total_background_counts": cum_b, "total_source_lower95_counts": cum_s_low, "total_background_upper95_counts": cum_b_up, "final_counting_Z": zs[-1], "final_counting_Z_conservative95": zs_conservative[-1], "T3_day_counting": t3 if t3 is not None else extrapolated_time(final_day, zs[-1], 3.0), "T5_day_counting": t5 if t5 is not None else extrapolated_time(final_day, zs[-1], 5.0), "T3_day_conservative95": t3c if t3c is not None else extrapolated_time(final_day, zs_conservative[-1], 3.0), "T5_day_conservative95": t5c if t5c is not None else extrapolated_time(final_day, zs_conservative[-1], 5.0)})
    return cumulative, summaries, accidentals


def c0_screening_context() -> dict[str, Any]:
    data = load_json(C0_CONTEXT)
    current = next(row for row in data["mass_trade"]["candidates"] if row["variant"] == "S3c-C0 current")
    return {
        "authority": rel(C0_CONTEXT),
        "scope": "retained S3c screening estimate, not a matched all-eight-family Step05--Step08 closure",
        "estimated_f3_20d_ph_cm2_s": float(current["estimated_f3_20d_ph_cm2_s"]),
        "estimated_background_cps": float(data["background"]["estimated_total_background_cps"]),
    }


def heavy_control_direct_comparison() -> dict[str, Any]:
    """Return the otherwise-identical heavy-control screening comparison.

    This is the only comparison in this runner interpreted as isolating the
    mass-reduction geometry delta.  It is intentionally limited to matched
    screening components and the matched focused EventList acceptance.
    """
    signal: dict[str, Any] = {}
    if SIGNAL_REPLAY_SUMMARY.is_file():
        signal_payload = load_json(SIGNAL_REPLAY_SUMMARY)
        if signal_payload.get("status") == "PASS_MATCHED_S3C_C0_S3D_SIGNAL_REPLAY_ANALYZED":
            signal = {
                "optimized_over_heavy_control_final_acceptance": signal_payload["comparison"]["s3d_over_c0_final_acceptance"],
                "ratio_counting_95": signal_payload["comparison"]["risk_ratio_counting_95_katz"],
                "relative_signal_loss": signal_payload["comparison"]["relative_signal_loss"],
                "promotion_gate_pass": signal_payload["comparison"]["promotion_gate_pass"],
                "authority": rel(SIGNAL_REPLAY_SUMMARY),
            }
    if not SCREENING_ANALYSIS.is_file():
        return {
            "status": "PENDING_MATCHED_SCREENING",
            "manuscript_display_names": MANUSCRIPT_DISPLAY,
            "signal": signal,
        }
    screening = load_json(SCREENING_ANALYSIS)
    gates = screening.get("promotion_gates")
    if screening.get("status") != "PASS_S3D_SCREENING_PROMOTION_GATES" or not gates:
        return {
            "status": "PENDING_MATCHED_SCREENING",
            "manuscript_display_names": MANUSCRIPT_DISPLAY,
            "authority": rel(SCREENING_ANALYSIS),
            "authority_status": screening.get("status"),
            "signal": signal,
            "pending_inputs": screening.get("pending_inputs"),
        }
    dominant = gates["dominant_subset"]
    delayed_section = screening.get("sections", {}).get("neutron_only_delayed", {})
    delayed_c0 = delayed_section.get("s3c_c0", {}).get("selection", {})
    delayed_optimized = delayed_section.get("s3d_o9", {}).get("selection", {})
    delayed_c0_rate = float(delayed_c0.get("side_compton_fov_pass_rate_s-1", 0.0))
    delayed_optimized_rate = float(
        delayed_optimized.get("side_compton_fov_pass_rate_s-1", 0.0)
    )
    if not delayed_c0 or not delayed_optimized:
        return {
            "status": "FAIL_MATCHED_SCREENING_DELAYED_SELECTION_MISSING",
            "authority": rel(SCREENING_ANALYSIS),
            "manuscript_display_names": MANUSCRIPT_DISPLAY,
        }
    signal_ratio = float(
        signal.get(
            "optimized_over_heavy_control_final_acceptance",
            gates["signal"]["s3d_over_c0_final_acceptance"],
        )
    )
    matched_c0_background = float(dominant["c0_rate_cps"]) + delayed_c0_rate
    matched_optimized_background = float(dominant["s3d_rate_cps"]) + delayed_optimized_rate
    background_ratio = matched_optimized_background / matched_c0_background
    f3_proxy_ratio = math.sqrt(background_ratio) / signal_ratio
    return {
        "status": "PASS_MATCHED_HEAVY_CONTROL_DIRECT_COMPARISON",
        "manuscript_display_names": {
            "optimized": MANUSCRIPT_DISPLAY["optimized"],
            "control": MANUSCRIPT_DISPLAY["heavy_control"],
        },
        "authority": rel(SCREENING_ANALYSIS),
        "scope": (
            dominant["definition"]
            + " + neutron-only day-15 delayed W2 transport"
        ),
        "excluded_from_direct_proxy": dominant["excludes"],
        "heavy_control_matched_background_cps": matched_c0_background,
        "optimized_matched_background_cps": matched_optimized_background,
        "heavy_control_neutron_delayed_cps": delayed_c0_rate,
        "optimized_neutron_delayed_cps": delayed_optimized_rate,
        "optimized_over_heavy_control_background": background_ratio,
        "optimized_over_heavy_control_signal_acceptance": signal_ratio,
        "optimized_over_heavy_control_F3_screening_proxy": f3_proxy_ratio,
        "performance_preservation_fraction_screening_proxy": 1.0 / f3_proxy_ratio,
        "signal": signal,
        "causal_interpretation": (
            "Because the two screening branches are otherwise identical apart from the "
            "active-shield mass delta, this matched proxy addresses whether the mass-reduction "
            "step preserves performance. It does not replace the full-chain result."
        ),
    }


def reference_detector_baseline_context() -> dict[str, Any]:
    if not REFERENCE_STEP05.is_file() or not REFERENCE_STEP08.is_file():
        raise ClosureGateError("paper reference detector Step05/Step08 authority is missing")
    step05 = load_json(REFERENCE_STEP05)
    step08 = load_json(REFERENCE_STEP08)
    if not str(step05.get("status", "")).startswith("PASS_") or not str(step08.get("status", "")).startswith("PASS_"):
        raise ClosureGateError("paper reference detector baseline is not PASS")
    phys = step05["windows"]["w2_510p58_511p42"]["physical_reference_flux"]
    checks = step08["checks"]
    return {
        "status": "PASS_REFERENCE_DETECTOR_BASELINE_AUTHORITY",
        "manuscript_display_name": MANUSCRIPT_DISPLAY["reference_baseline"],
        "step05_authority": rel(REFERENCE_STEP05),
        "step08_authority": rel(REFERENCE_STEP08),
        "step05_w2_prompt_background_cps": float(phys["prompt_background_cps"]),
        "step05_w2_delayed_background_cps": float(phys["delayed_background_cps"]),
        "step05_w2_background_cps": float(phys["background_cps"]),
        "step05_w2_signal_cps_at_reference_flux": float(phys["signal_cps_at_reference_flux"]),
        "step08_Z20d": float(checks["A_reference_w2_Z20d_time_dependent"]),
        "step08_F3_20d_ph_cm2_s": float(checks["A_reference_w2_flux_3sigma_20d_ph_cm2_s"]),
        "scope_note": (
            "This is the paper's original reference detector result. It does not isolate the "
            "mass-reduction step; differences include the complete optimization stack and "
            "the reference chain's historical background scope."
        ),
    }


def run_step08() -> dict[str, Any]:
    if not STEP05_JSON.is_file() or not STEP06_JSON.is_file() or not STEP07_JSON.is_file() or not STEP06_BG.is_file() or not STEP07_RATES.is_file():
        raise ClosureGateError("Step05--Step07 authority is incomplete")
    step05, step06, step07 = load_json(STEP05_JSON), load_json(STEP06_JSON), load_json(STEP07_JSON)
    if step06.get("status") != "PASS_S3D_O9_STEP06_FULLCHAIN_TIME_AXIS" or step07.get("status") != "PASS_S3D_O9_STEP07_MATCHED_SIGNAL_SOURCE_CASES":
        raise ClosureGateError("Step06/Step07 status is not authoritative")
    background = read_csv(STEP06_BG)
    cases = read_csv(STEP07_RATES)
    cumulative, summaries, accidentals = fold_cases(cases, background)
    STEP08_OUT.mkdir(parents=True, exist_ok=True)
    write_csv(STEP08_OUT / "cumulative_significance_by_case.csv", cumulative)
    write_csv(STEP08_OUT / "t3_t5_summary.csv", summaries)
    write_csv(STEP08_OUT / "accidental_veto_by_time.csv", accidentals)
    reference = next(row for row in summaries if row["analysis_case_id"] == "A_point_w2_510p58_511p42_F0.0001")
    z = float(reference["final_counting_Z"])
    z_cons = float(reference["final_counting_Z_conservative95"])
    f3 = REFERENCE_FLUX * 3.0 / z if z > 0.0 else math.inf
    f3_cons = REFERENCE_FLUX * 3.0 / z_cons if z_cons > 0.0 else math.inf
    c0 = c0_screening_context()
    heavy_direct = heavy_control_direct_comparison()
    reference_baseline = reference_detector_baseline_context()
    losses = [float(row["accidental_loss_fraction"]) for row in accidentals]
    if not accidentals or any(float(row["atm511_event_rate_hz"]) <= 0.0 for row in accidentals):
        raise ClosureGateError("atmospheric detector occupancy is absent or non-positive in Step08")
    payload = {
        "status": "PASS_S3D_O9_STEP08_FULLCHAIN_TIME_DEPENDENT",
        "generated_at_utc": now_utc(),
        "claim_level": "S3D_O9_ALL8_PROMPT_NEUTRON_DELAYED_ATM511_MATCHED_SIGNAL_COUNTING_PROJECTION",
        "inputs": {"step05_summary": rel(STEP05_JSON), "step06_summary": rel(STEP06_JSON), "step06_background_time_variation": rel(STEP06_BG), "step07_summary": rel(STEP07_JSON), "step07_source_case_rates": rel(STEP07_RATES)},
        "checks": {
            "A_reference_w2_Z20d_time_dependent": z,
            "A_reference_w2_Z20d_conservative95": z_cons,
            "A_reference_w2_flux_3sigma_20d_ph_cm2_s": f3,
            "A_reference_w2_flux_3sigma_20d_conservative95_ph_cm2_s": f3_cons,
            "A_reference_w2_T3_day": reference["T3_day_counting"],
            "A_reference_w2_T5_day": reference["T5_day_counting"],
            "A_reference_w2_T3_day_conservative95": reference["T3_day_conservative95"],
            "A_reference_w2_T5_day_conservative95": reference["T5_day_conservative95"],
            "accidental_loss_min": min(losses), "accidental_loss_max": max(losses),
            "atm511_occupancy_included": all(float(row["atm511_event_rate_hz"]) > 0.0 for row in accidentals),
        },
        "comparison_to_s3c_c0": {
            **c0,
            "s3d_central_over_c0_screening_estimate": f3 / c0["estimated_f3_20d_ph_cm2_s"],
            "s3d_conservative95_over_c0_screening_estimate": f3_cons / c0["estimated_f3_20d_ph_cm2_s"],
            "central_within_1p05_context_gate": f3 <= 1.05 * c0["estimated_f3_20d_ph_cm2_s"],
            "conservative95_within_1p10_context_gate": f3_cons <= 1.10 * c0["estimated_f3_20d_ph_cm2_s"],
            "promotion_status": "PENDING_MATCHED_S3C_C0_FULLCHAIN; screening estimate is context, not a like-for-like authority",
        },
        "comparisons": {
            "mass_reduction_direct_heavy_control": heavy_direct,
            "whole_optimization_vs_reference_detector": {
                "status": "PASS_FULLCHAIN_REFERENCE_COMPARISON",
                "manuscript_display_names": {
                    "optimized": MANUSCRIPT_DISPLAY["optimized"],
                    "baseline": MANUSCRIPT_DISPLAY["reference_baseline"],
                },
                "reference_authority": reference_baseline,
                "optimized_F3_20d_ph_cm2_s": f3,
                "optimized_F3_conservative95_20d_ph_cm2_s": f3_cons,
                "reference_F3_20d_ph_cm2_s": reference_baseline["step08_F3_20d_ph_cm2_s"],
                "optimized_over_reference_F3": f3 / reference_baseline["step08_F3_20d_ph_cm2_s"],
                "optimized_conservative95_over_reference_F3": f3_cons / reference_baseline["step08_F3_20d_ph_cm2_s"],
                "central_sensitivity_improvement_fraction": 1.0 - f3 / reference_baseline["step08_F3_20d_ph_cm2_s"],
                "optimized_over_reference_Z20d": z / reference_baseline["step08_Z20d"],
                "causal_interpretation": (
                    "This is the net outcome of the complete optimized detector relative to "
                    "the paper reference detector. It is not an estimate of the isolated "
                    "causal effect of removing shield mass."
                ),
                "scope_warning": (
                    "The historical reference chain predates the explicit atmospheric-511 "
                    "sidecar merge; report component scope alongside the numerical ratio."
                ),
            },
        },
        "uncertainty_method": "Garwood 95% upper per independently normalized background component plus Clopper-Pearson 95% lower focused-signal acceptance; propagated through the same mission fold",
        "outputs": {"summary_json": rel(STEP08_JSON), "cumulative_significance": rel(STEP08_OUT / "cumulative_significance_by_case.csv"), "t3_t5_summary": rel(STEP08_OUT / "t3_t5_summary.csv"), "accidental_veto_by_time": rel(STEP08_OUT / "accidental_veto_by_time.csv")},
        "method_caveats": [
            "Atmospheric detector occupancy is included in the accidental live factor in every time bin.",
            "The atmospheric day-15 angular transfer is held fixed while phi_4pi is scaled with depth/Rc.",
            "The S3c comparator is a retained screening estimate; a matched S3c all-eight-family closure remains required for a strict promotion gate.",
            "No spatial/profile likelihood gain is claimed.",
        ],
    }
    write_json(STEP08_JSON, payload)
    return payload


def run_self_test() -> dict[str, Any]:
    checks: dict[str, bool] = {}
    checks["poisson_upper_positive"] = poisson_upper_95(0) > 0.0 and poisson_upper_95(6) > 6.0
    checks["binomial_lower_bounded"] = 0.0 < binomial_lower_95(100, 200) < 0.5
    checks["rigidity_piecewise"] = f_r_harris(10.9) == 0.624 and f_r_harris(11.0) == 0.532
    toy_bg = [{"selection_id": "w2", "time_bin_id": 0, "day_mid": 0.0, "dt_s": 10.0, "science_atm_scale_to_day15": 1.0, "prompt_event_rate_hz": 1.0, "delayed_event_rate_hz": 2.0, "atm511_event_rate_hz": 3.0, "background_final_cps": 4.0, "background_final_upper95_cps": 9.0}]
    toy_case = [{"analysis_case_id": "toy", "source_case_id": "toy", "source_class": "point_steady", "selection_id": "w2", "flux_ph_cm2_s": REFERENCE_FLUX, "duration_s": "", "final_rate_day15_cps": 2.0, "final_rate_lower95_day15_cps": 1.0}]
    _cum, summary, accidentals = fold_cases(toy_case, toy_bg)
    checks["atm_occupancy_merged"] = math.isclose(float(accidentals[0]["coincidence_occupancy_rate_hz"]), 6.0)
    checks["conservative_z_not_larger"] = float(summary[0]["final_counting_Z_conservative95"]) <= float(summary[0]["final_counting_Z"])
    forbidden = ("s3d", "s3c", "mass_model_511")
    checks["manuscript_display_names_clean"] = all(
        not any(token in value.lower() for token in forbidden)
        for value in MANUSCRIPT_DISPLAY.values()
    )
    reference = reference_detector_baseline_context()
    checks["reference_detector_schema"] = (
        reference["step05_w2_background_cps"] > 0.0
        and reference["step05_w2_signal_cps_at_reference_flux"] > 0.0
        and reference["step08_F3_20d_ph_cm2_s"] > 0.0
    )
    if not all(checks.values()):
        raise ClosureGateError(f"self-test failed: {checks}")
    return {"status": "PASS_LIGHTWEIGHT_SELF_TEST", "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("preflight", "step05", "step06", "step07", "step08", "all", "self-test"), nargs="?", default="preflight")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--deep-preflight", action="store_true", help="scan full signal/atm SIMs for SE/ID")
    parser.add_argument("--rebuild-cache", action="store_true")
    args = parser.parse_args()
    try:
        if args.stage == "self-test":
            payload = run_self_test()
        elif args.stage == "preflight":
            payload = build_preflight(deep=args.deep_preflight)
        else:
            ready = require_ready(deep=True)
            if ready["status"] != "PASS_READY_FOR_STEP05_08":
                payload = ready
            else:
                payload = ready
                if args.stage in ("step05", "all"):
                    payload = run_step05(args.workers, args.rebuild_cache)
                if args.stage in ("step06", "all"):
                    payload = run_step06()
                if args.stage in ("step07", "all"):
                    payload = run_step07()
                if args.stage in ("step08", "all"):
                    payload = run_step08()
        console = {
            "status": payload["status"],
            "preflight": rel(PREFLIGHT_JSON),
            "result": rel(STEP08_JSON) if STEP08_JSON.is_file() else None,
        }
        if "checks" in payload and args.stage == "self-test":
            console["checks"] = payload["checks"]
        if "pending_gates" in payload:
            console["pending_gates"] = payload["pending_gates"]
        print(json.dumps(console, indent=2, ensure_ascii=False))
        return 2 if str(payload["status"]).startswith("FAIL") else 0
    except (ClosureGateError, AuditError, KeyError, ValueError) as exc:
        failure = {"status": "FAIL_CLOSED", "generated_at_utc": now_utc(), "error": str(exc), "production_launched": False}
        write_json(PREFLIGHT_JSON, failure)
        print(json.dumps(failure, indent=2, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
