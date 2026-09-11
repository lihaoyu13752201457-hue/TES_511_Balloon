#!/usr/bin/env python3
"""Dedicated, fail-closed O8 Step05--Step08 closure harness.

This harness reuses the reviewed numerical implementation in package 42 while
binding every mutable input, output, status, label, and geometry check to the
O8 campaign in package 43.  It never launches Cosima.  Missing full-production
inputs remain PENDING, and the final matched O8 screening promotion gate must
be fully PASS before any Step05--Step08 result can be generated.

Postprocessing is also guarded against accidental launch: result-producing
stages require both ``--allow-closure-run`` and the exact confirmation token
``RUN_O8_STEP05_08_CLOSURE``.  Preflight and self-test need neither flag.
"""

from __future__ import annotations

import argparse
import copy
import csv
import importlib.util
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from _o8_promotion_gate import audit_screening_promotion
from _o8_replay_common import (
    AuditError,
    DATA,
    PACKAGE,
    ROOT,
    S3D_GEOMETRY_SETUP,
    audit_geometry_authority,
    rel,
    selection_contract,
    sha256,
    sim_header,
)


SHARED_RUNNER = (
    ROOT
    / "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712"
    / "code/run_s3d_step05_08_closure.py"
)
SHARED_CODE = SHARED_RUNNER.parent

FULLCHAIN = PACKAGE / "fullchain"
STEP05_OUT = FULLCHAIN / "step05"
STEP06_OUT = FULLCHAIN / "step06"
STEP07_OUT = FULLCHAIN / "step07"
STEP08_OUT = FULLCHAIN / "step08"

PREFLIGHT_JSON = DATA / "s3d_o8_step05_08_closure_preflight.json"
STEP05_CORE_JSON = STEP05_OUT / "step05_s3d_o8_core_no_atm511_summary.json"
STEP05_JSON = STEP05_OUT / "step05_s3d_o8_fullchain_l1_response_summary.json"
STEP05_RATES = STEP05_OUT / "step05_s3d_o8_fullchain_l1_rates.csv"
STEP06_JSON = STEP06_OUT / "step06_s3d_o8_fullchain_summary.json"
STEP06_BG = STEP06_OUT / "background_time_variation.csv"
STEP07_JSON = STEP07_OUT / "source_case_summary.json"
STEP07_RATES = STEP07_OUT / "source_case_rates.csv"
STEP08_JSON = STEP08_OUT / "step08_s3d_o8_fullchain_time_dependent_summary.json"

PROMPT_DIR = (
    ROOT
    / "runs/geometry_optimization_20260704/s3d_o8_fullstat_prompt_all8_20260712"
)
PROMPT_SUMMARY = PROMPT_DIR / "run_summary.csv"
PROMPT_NORM = PROMPT_DIR / "normalization.json"
PROMPT_MANIFEST = PROMPT_DIR / "run_manifest.csv"
PROMPT_SOURCE_MANIFEST = (
    PACKAGE / "config/full_prompt_all8/source_cards/source_migration_manifest.json"
)

DELAY_LABEL = "s3d_o8_neutron_delayed_m50000_20260712"
DELAYED_SIM = (
    ROOT
    / "runs/geometry_optimization_20260704"
    / f"step02_delayed_transport_{DELAY_LABEL}"
    / "DelayedDecayS3dO8NeutronM50000.inc1.id1.sim.gz"
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
DELAY_CAMPAIGN = DATA / "s3d_o8_delayed_activation_campaign.json"

SIGNAL_RUN_DIR = (
    ROOT
    / "runs/geometry_optimization_20260704"
    / "s3d_o8_f10m_a1_signal_replay_37194_20260712"
)
SIGNAL_NAME = "Opticsim_laue_f10m_a1_s3d_o8_signal37194"
SIGNAL_SOURCE = SIGNAL_RUN_DIR / f"{SIGNAL_NAME}.source"
SIGNAL_SIM = SIGNAL_RUN_DIR / f"{SIGNAL_NAME}.inc1.id1.sim.gz"
SIGNAL_MANIFEST = DATA / "s3d_o8_signal_replay_manifest.json"
SIGNAL_REPLAY_SUMMARY = DATA / "s3d_o8_signal_replay_summary.json"

ATM_RUN_DIR = (
    ROOT
    / "runs/geometry_optimization_20260704/s3d_o8_atm511_sidecar_3m_20260712"
)
ATM_NAME = "Atm511SidecarS3dO8_3M"
ATM_SOURCE = ATM_RUN_DIR / f"{ATM_NAME}.source"
ATM_SIM = ATM_RUN_DIR / f"{ATM_NAME}.inc1.id1.sim.gz"
ATM_LOG = ATM_RUN_DIR / f"cosima_{ATM_NAME}.log"
ATM_MANIFEST = DATA / "s3d_o8_atm511_replay_manifest.json"
ATM_SUMMARY = DATA / "s3d_o8_atm511_replay_summary.json"
SCREENING_ANALYSIS = DATA / "s3d_o8_screening_analysis.json"

CONFIRM_TOKEN = "RUN_O8_STEP05_08_CLOSURE"

_STATUS_TO_LEGACY = {
    "PASS_S3D_O8_ALL8_SOURCE_CARDS": "PASS_S3D_O9_ALL8_SOURCE_CARDS",
    "PASS_S3D_O8_NEUTRON_DELAYED_TRANSPORT": "PASS_S3D_O9_NEUTRON_DELAYED_TRANSPORT",
    "PASS_O8_ATM511_4PI_SIDECAR_REPLAY": "PASS_S3D_ATM511_4PI_SIDECAR_REPLAY",
    "PASS_O8_SCREENING_PROMOTION_GATES": "PASS_S3D_SCREENING_PROMOTION_GATES",
    "PASS_MATCHED_HEAVY_CONTROL_O8_SIGNAL_REPLAY_ANALYZED": "PASS_MATCHED_S3C_C0_S3D_SIGNAL_REPLAY_ANALYZED",
    "PASS_S3D_O8_STEP05_CORE_ALL8_PROMPT_NEUTRON_DELAYED_MATCHED_SIGNAL_NO_ATM511": "PASS_S3D_O9_STEP05_CORE_ALL8_PROMPT_NEUTRON_DELAYED_MATCHED_SIGNAL_NO_ATM511",
    "PASS_S3D_O8_STEP05_FULLCHAIN_ALL8_PROMPT_NEUTRON_DELAYED_ATM511_MATCHED_SIGNAL": "PASS_S3D_O9_STEP05_FULLCHAIN_ALL8_PROMPT_NEUTRON_DELAYED_ATM511_MATCHED_SIGNAL",
    "PASS_S3D_O8_STEP06_FULLCHAIN_TIME_AXIS": "PASS_S3D_O9_STEP06_FULLCHAIN_TIME_AXIS",
    "PASS_S3D_O8_STEP07_MATCHED_SIGNAL_SOURCE_CASES": "PASS_S3D_O9_STEP07_MATCHED_SIGNAL_SOURCE_CASES",
    "PASS_S3D_O8_STEP08_FULLCHAIN_TIME_DEPENDENT": "PASS_S3D_O9_STEP08_FULLCHAIN_TIME_DEPENDENT",
}

_STRING_TO_O8 = (
    ("PASS_READY_FOR_STEP05_08", "PASS_READY_FOR_O8_STEP05_08"),
    ("S3D_O9", "S3D_O8"),
    ("s3d_o9", "s3d_o8"),
    ("S3d-O9", "S3d-O8"),
    ("S3d O9", "S3d O8"),
    ("S3d BGO", "O8 BGO"),
)

_KEY_TO_O8 = {
    "comparison_to_s3c_c0": "comparison_to_heavy_control_screening_context",
    "s3d_central_over_c0_screening_estimate": "o8_central_over_heavy_control_screening_estimate",
    "s3d_conservative95_over_c0_screening_estimate": "o8_conservative95_over_heavy_control_screening_estimate",
    "s3d_over_c0_final_acceptance": "o8_over_heavy_control_final_acceptance",
}


class O8ClosureGateError(RuntimeError):
    """A package-local closure gate denied result production."""


def now_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _raw_load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _o8_string(value: str) -> str:
    out = value
    for old, new in _STRING_TO_O8:
        out = out.replace(old, new)
    return out


def o8ize(value: Any) -> Any:
    if isinstance(value, str):
        return _o8_string(value)
    if isinstance(value, list):
        return [o8ize(item) for item in value]
    if isinstance(value, tuple):
        return tuple(o8ize(item) for item in value)
    if isinstance(value, dict):
        return {
            _KEY_TO_O8.get(o8ize(key), o8ize(key)): o8ize(item)
            for key, item in value.items()
        }
    return value


def _o8_path(path: Path) -> Path:
    text = str(path).replace("s3d_o9", "s3d_o8").replace("S3dO9", "S3dO8")
    return Path(text)


def write_json(path: Path, payload: Any) -> None:
    target = _o8_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(o8ize(payload), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    # Reuse the reviewed CSV schema implementation, but rewrite any residual
    # filename literal before it reaches the filesystem.
    shared._o8_raw_write_csv(_o8_path(path), o8ize(list(rows)))


def _load_shared() -> Any:
    if str(SHARED_CODE) not in sys.path:
        sys.path.insert(0, str(SHARED_CODE))
    spec = importlib.util.spec_from_file_location(
        "o8_fullchain_shared_closure", SHARED_RUNNER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load shared closure runner: {rel(SHARED_RUNNER)}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


shared = _load_shared()
shared._o8_raw_write_csv = shared.write_csv


def compat_load_json(path: Path) -> Any:
    """Expose O8 authorities through the reviewed implementation's schema."""
    payload = _raw_load_json(path)
    if not isinstance(payload, dict):
        return payload
    out = copy.deepcopy(payload)
    status = out.get("status")
    if status in _STATUS_TO_LEGACY:
        out["status"] = _STATUS_TO_LEGACY[status]

    resolved = path.resolve()
    if resolved == ATM_MANIFEST.resolve():
        if "source_model_frozen_from_c0" not in out:
            model = out.get("source_model_frozen_from_heavy_control")
            if model is not None:
                out["source_model_frozen_from_c0"] = model
    if resolved == SIGNAL_REPLAY_SUMMARY.resolve():
        comparison = out.setdefault("comparison", {})
        if "s3d_over_c0_final_acceptance" not in comparison:
            comparison["s3d_over_c0_final_acceptance"] = comparison.get(
                "o8_over_heavy_control_final_acceptance"
            )
    if resolved == SCREENING_ANALYSIS.resolve():
        gates = out.setdefault("promotion_gates", {})
        dominant = gates.setdefault("dominant_subset", {})
        dominant.setdefault(
            "c0_rate_cps", dominant.get("heavy_control_rate_cps")
        )
        dominant.setdefault("s3d_rate_cps", dominant.get("o8_rate_cps"))
        signal = gates.setdefault("signal", {})
        signal.setdefault(
            "s3d_over_c0_final_acceptance",
            signal.get("o8_over_heavy_control_final_acceptance"),
        )
    return out


def configure_step05(module: Any) -> None:
    module.ROOT = ROOT
    module.TOOLS = ROOT / "old/code/tools"
    module.OUT = STEP05_OUT
    module.SUMMARY_JSON = STEP05_CORE_JSON
    module.SUMMARY_MD = STEP05_OUT / "step05_s3d_o8_core_no_atm511_summary.md"
    module.RATES_CSV = STEP05_OUT / "step05_s3d_o8_core_no_atm511_rates.csv"
    module.TIMELINE_CSV = (
        STEP05_OUT / "step05_s3d_o8_core_no_atm511_timeline_rates.csv"
    )
    module.PROMPT_DIR = PROMPT_DIR
    module.PROMPT_NORM = PROMPT_NORM
    module.DELAYED_SIM = DELAYED_SIM
    module.FIXED_SOURCE = FIXED_SOURCE
    module.STEP02_SUMMARY = EXACT_SUMMARY
    module.SCIENCE_SIM = SIGNAL_SIM
    module.STEP09_SUMMARY = shared.BRIDGE_SUMMARY
    module.F10M_A1_AEFF = shared.AEFF_AUTHORITY
    module.SCIENCE_RATE_LEDGER = shared.SCIENCE_LEDGER
    module.BOUNDARY_CLOSURE_SUMMARY = shared.BOUNDARY_SUMMARY
    module.ACTIVE_VETO_THRESHOLD_KEV = shared.ACTIVE_VETO_THRESHOLD_KEV
    module.ACTIVE_VETO_MATCH_DESCRIPTION = (
        "O8 BGO/CsI/ActiveShield/CEBR3 and retained active plastic volumes; "
        "W/Al/Kapton mechanical volumes excluded"
    )
    module.is_v3p5_active_veto_volume = shared.is_s3d_active_veto_volume
    module._PROMPT_NORMALIZATION_AUDIT = None


def policy_gate() -> dict[str, Any]:
    contract = selection_contract()
    det = (
        S3D_GEOMETRY_SETUP.parent
        / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det"
    )
    text = det.read_text(encoding="utf-8", errors="replace") if det.is_file() else ""
    native = [
        float(value)
        for value in re.findall(
            r"^BGO_(?:S3C|S3D)_\S+\.TriggerThreshold\s+([-+0-9.eE]+)\s*$",
            text,
            re.M,
        )
    ]
    problems: list[str] = []
    if float(contract.get("active_veto_threshold_keV") or -1.0) != 50.0:
        problems.append("analysis veto threshold is not 50 keV")
    if len(native) != 3 or any(value != 80.0 for value in native):
        problems.append(f"native_BGO_thresholds={native} expected three 80-keV values")
    knob0 = contract.get("side_compton_fov", {}).get("knob0_policy", "")
    if "monotonic" not in str(knob0).lower() or "literal" not in str(knob0).lower():
        problems.append(f"Knob0_policy={knob0}")
    return shared.gate(
        "PASS" if not problems else "FAIL",
        problems=problems,
        selection_contract=contract,
        analysis_veto_threshold_keV=50.0,
        native_BGO_detector_thresholds_keV=native,
        scorer_scope=(
            "retained byte-identical 40-mm side scorer plus O8 30-mm bottom "
            "and 10-mm top scorers"
        ),
        systematic_disclosure=(
            "Cosima native BGO detector blocks use 80 keV, while postprocessing "
            "sums matched active deposits and applies <50 keV; both settings are "
            "frozen across the matched heavy-control/O8 comparison."
        ),
    )


def prompt_gate_csv() -> dict[str, Any]:
    """Audit the CSV summary emitted by the actual all-eight runner.

    The reviewed package-42 closure expected a JSON list that its transport
    runner never creates.  O8 treats the runner's 15-column CSV plus the job
    manifest as the authority and preserves the original geometry/TT checks.
    """
    required = [PROMPT_SUMMARY, PROMPT_NORM, PROMPT_MANIFEST]
    missing = [rel(path) for path in required if not path.is_file()]
    if missing:
        return shared.gate("PENDING_PRODUCTION", missing=missing, expected_jobs=68)

    expected_schema = [
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
    with PROMPT_SUMMARY.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        schema = list(reader.fieldnames or [])
        rows = list(reader)
    manifest_rows = shared.read_csv(PROMPT_MANIFEST)
    problems: list[str] = []
    if schema != expected_schema:
        problems.append(f"run_summary_schema={schema} expected={expected_schema}")
    if len(rows) != 68:
        problems.append(f"run_summary_rows={len(rows)} expected=68")
    if len(manifest_rows) != 68:
        problems.append(f"run_manifest_rows={len(manifest_rows)} expected=68")

    counts = Counter(str(row.get("particle", "")) for row in rows)
    if dict(counts) != shared.EXPECTED_PROMPT_COUNTS:
        problems.append(
            f"particle_counts={dict(counts)} expected={shared.EXPECTED_PROMPT_COUNTS}"
        )
    row_names = [str(row.get("job_name", "")) for row in rows]
    manifest_names = [str(row.get("job_name", "")) for row in manifest_rows]
    if len(set(row_names)) != len(row_names):
        problems.append("run_summary has duplicate job_name values")
    if len(set(manifest_names)) != len(manifest_names):
        problems.append("run_manifest has duplicate job_name values")
    if set(row_names) != set(manifest_names):
        problems.append("run_summary/run_manifest job-name sets differ")

    source_rows = {str(row.get("job_name", "")): row for row in manifest_rows}
    audited: list[dict[str, Any]] = []
    for row in rows:
        name = str(row.get("job_name", ""))
        source_row = source_rows.get(name, {})
        sim = shared.resolve_repo_path(str(row.get("sim_path", "")))
        dat = shared.resolve_repo_path(str(row.get("dat_path", "")))
        temp_source = (
            shared.resolve_repo_path(str(source_row.get("temp_source", "")))
            if source_row.get("temp_source")
            else Path()
        )
        header = shared.cached_sim_header(sim)
        geoms = shared.source_geometry(temp_source) if source_row else []
        vals = shared.tt_values(dat)
        local: list[str] = []
        if row.get("status") not in ("PASS", "SKIP"):
            local.append(f"status={row.get('status')}")
        events = int(row.get("events") or -1)
        generated = int(row.get("generated_particles") or -2)
        if generated != events:
            local.append("generated_particles!=events")
        if source_row and int(source_row.get("events") or -3) != events:
            local.append("manifest events differ from summary")
        if not sim.is_file() or not dat.is_file():
            local.append("missing SIM or DAT")
        if row.get("sim_exists") != "True" or row.get("dat_exists") != "True":
            local.append("summary output-exists flags are not true")
        if int(row.get("sim_size_bytes") or 0) <= 0 or int(row.get("dat_size_bytes") or 0) <= 0:
            local.append("summary output size is not positive")
        if float(row.get("cpu_s") or 0.0) <= 0.0 or float(row.get("observation_time_s") or 0.0) <= 0.0:
            local.append("CPU or observation time is not positive")
        if len(vals) != 1 or not math.isfinite(vals[0]) or vals[0] <= 0.0:
            local.append(f"TT={vals}")
        if not shared.exact_geometry(header.get("geometry")):
            local.append(f"SIM geometry={header.get('geometry')}")
        if len(geoms) != 1 or not shared.exact_geometry(geoms[0]):
            local.append(f"source geometry={geoms}")
        if source_row and int(header.get("seed") or -1) != int(source_row.get("seed") or -2):
            local.append(
                f"SIM seed={header.get('seed')} manifest seed={source_row.get('seed')}"
            )
        if source_row:
            if Path(str(row.get("sim_path", ""))).resolve() != Path(
                str(source_row.get("sim_path", ""))
            ).resolve():
                local.append("summary/manifest SIM paths differ")
            if Path(str(row.get("dat_path", ""))).resolve() != Path(
                str(source_row.get("dat_path", ""))
            ).resolve():
                local.append("summary/manifest DAT paths differ")
        problems.extend(f"{name}: {item}" for item in local)
        audited.append(
            {
                "job_name": name,
                "particle": row.get("particle"),
                "events": events,
                "generated_particles": generated,
                "sim": rel(sim),
                "dat": rel(dat),
                "source": rel(temp_source) if source_row else None,
                "tt_s": vals[0] if len(vals) == 1 else vals,
                "geometry": header.get("geometry"),
                "seed": header.get("seed"),
                "status": "PASS" if not local else "FAIL",
            }
        )

    source_manifest = (
        compat_load_json(PROMPT_SOURCE_MANIFEST)
        if PROMPT_SOURCE_MANIFEST.is_file()
        else {}
    )
    if source_manifest.get("status") != "PASS_S3D_O9_ALL8_SOURCE_CARDS":
        problems.append(f"source_migration_status={source_manifest.get('status')}")
    norm_payload = compat_load_json(PROMPT_NORM)
    if int(norm_payload.get("gamma_splits") or -1) != 12:
        problems.append(f"gamma_splits={norm_payload.get('gamma_splits')}")
    if int(norm_payload.get("non_gamma_replicas") or -1) != 8:
        problems.append(f"non_gamma_replicas={norm_payload.get('non_gamma_replicas')}")
    return shared.gate(
        "PASS" if not problems else "FAIL",
        problems=problems,
        expected_jobs=68,
        particle_counts=dict(counts),
        audited_jobs=audited,
        run_summary=rel(PROMPT_SUMMARY),
        run_summary_sha256=sha256(PROMPT_SUMMARY),
        normalization=rel(PROMPT_NORM),
        normalization_rule="per-family rate = 1 / sum(TT_s); never one common prompt time",
    )


def heavy_control_direct_comparison() -> dict[str, Any]:
    promotion = audit_screening_promotion()
    if promotion["status"] != "PASS_SCREENING_PROMOTION_GATE":
        return {
            "status": promotion["status"],
            "authority": rel(SCREENING_ANALYSIS),
            "manuscript_display_names": shared.MANUSCRIPT_DISPLAY,
            "problems": promotion["problems"],
            "pending": promotion["pending"],
        }
    screening = _raw_load_json(SCREENING_ANALYSIS)
    gates = screening["promotion_gates"]
    dominant = gates["dominant_subset"]
    signal = gates["signal"]
    control_background = float(dominant["heavy_control_rate_cps"])
    optimized_background = float(dominant["o8_rate_cps"])
    signal_ratio = float(signal["o8_over_heavy_control_final_acceptance"])
    background_ratio = optimized_background / control_background
    f3_proxy_ratio = math.sqrt(background_ratio) / signal_ratio
    return {
        "status": "PASS_MATCHED_HEAVY_CONTROL_DIRECT_COMPARISON",
        "manuscript_display_names": {
            "optimized": shared.MANUSCRIPT_DISPLAY["optimized"],
            "control": shared.MANUSCRIPT_DISPLAY["heavy_control"],
        },
        "authority": rel(SCREENING_ANALYSIS),
        "scope": dominant["definition"],
        "excluded_from_direct_proxy": (
            "all other prompt families and delayed activation; those are evaluated "
            "only in the optimized full chain because no matched heavy-control "
            "all-eight/delayed replay is part of this screening campaign"
        ),
        "heavy_control_matched_background_cps": control_background,
        "optimized_matched_background_cps": optimized_background,
        "optimized_over_heavy_control_background": background_ratio,
        "optimized_over_heavy_control_signal_acceptance": signal_ratio,
        "optimized_over_heavy_control_F3_screening_proxy": f3_proxy_ratio,
        "performance_preservation_fraction_screening_proxy": 1.0 / f3_proxy_ratio,
        "signal": {
            "ratio_counting_95": signal.get("risk_ratio_counting_95_katz"),
            "relative_signal_loss": signal.get("relative_signal_loss"),
            "promotion_gate_pass": signal.get("promotion_gate_pass"),
            "authority": rel(SIGNAL_REPLAY_SUMMARY),
        },
        "causal_interpretation": (
            "This matched screening proxy isolates the active-shield mass delta for "
            "the preregistered dominant subset and focused-signal acceptance. It does "
            "not replace the optimized all-eight prompt plus delayed full-chain result."
        ),
    }


def heavy_control_screening_context() -> dict[str, Any]:
    data = compat_load_json(shared.C0_CONTEXT)
    current = next(
        row
        for row in data["mass_trade"]["candidates"]
        if row["variant"] == "S3c-C0 current"
    )
    return {
        "authority": rel(shared.C0_CONTEXT),
        "scope": (
            "retained heavy-control screening estimate, not a matched all-eight-family "
            "Step05-Step08 closure"
        ),
        "estimated_f3_20d_ph_cm2_s": float(
            current["estimated_f3_20d_ph_cm2_s"]
        ),
        "estimated_background_cps": float(
            data["background"]["estimated_total_background_cps"]
        ),
    }


def comparison_gate() -> dict[str, Any]:
    promotion = audit_screening_promotion()
    if promotion["status"] == "FAIL_SCREENING_GATE":
        return shared.gate("FAIL", problems=promotion["problems"])
    if promotion["status"] != "PASS_SCREENING_PROMOTION_GATE":
        return shared.gate(
            "PENDING_SCREENING_GATE",
            missing=promotion["pending"],
            authority=rel(SCREENING_ANALYSIS),
        )
    required = [
        shared.C0_CONTEXT,
        SIGNAL_REPLAY_SUMMARY,
        shared.REFERENCE_STEP05,
        shared.REFERENCE_STEP08,
    ]
    missing = [rel(path) for path in required if not path.is_file()]
    if missing:
        return shared.gate("PENDING_PRODUCTION", missing=missing)
    signal = _raw_load_json(SIGNAL_REPLAY_SUMMARY)
    if signal.get("status") != "PASS_MATCHED_HEAVY_CONTROL_O8_SIGNAL_REPLAY_ANALYZED":
        return shared.gate(
            "FAIL", problems=[f"matched signal status={signal.get('status')}"]
        )
    reference = shared.reference_detector_baseline_context()
    direct = heavy_control_direct_comparison()
    if direct.get("status") != "PASS_MATCHED_HEAVY_CONTROL_DIRECT_COMPARISON":
        return shared.gate(
            "FAIL", problems=[f"heavy-control comparison={direct.get('status')}"]
        )
    return shared.gate(
        "PASS",
        screening_promotion=promotion,
        heavy_control_authority=rel(SCREENING_ANALYSIS),
        reference_detector_authority={
            "step05": rel(shared.REFERENCE_STEP05),
            "step08": rel(shared.REFERENCE_STEP08),
        },
        manuscript_display_names=shared.MANUSCRIPT_DISPLAY,
        reference_status=reference["status"],
    )


def build_preflight(deep: bool = False) -> dict[str, Any]:
    try:
        geometry = shared.gate("PASS", authority=audit_geometry_authority())
    except AuditError as exc:
        geometry = shared.gate("FAIL", problems=[str(exc)])
    promotion = audit_screening_promotion()
    promotion_gate = shared.gate(
        promotion["status"],
        problems=promotion["problems"],
        missing=promotion["pending"],
        authority=promotion,
    )
    gates = {
        "geometry": geometry,
        "screening_promotion": promotion_gate,
        "prompt_all8": shared._prompt_gate(),
        "neutron_delayed": shared._delayed_gate(),
        "focused_signal": shared._signal_gate(deep),
        "atm511_sidecar": shared._atm_gate(deep),
        "selection_policy": policy_gate(),
        "comparison_authorities": comparison_gate(),
    }
    failed = [name for name, item in gates.items() if item["status"] == "FAIL"]
    failed.extend(
        name
        for name, item in gates.items()
        if item["status"] == "FAIL_SCREENING_GATE" and name not in failed
    )
    pending = [
        name for name, item in gates.items() if item["status"].startswith("PENDING")
    ]
    status = (
        "FAIL_CLOSED"
        if failed
        else "PENDING_SCREENING_GATE"
        if promotion["status"] != "PASS_SCREENING_PROMOTION_GATE"
        else "PENDING_PRODUCTION_INPUTS"
        if pending
        else "PASS_READY_FOR_O8_STEP05_08"
    )
    payload = {
        "status": status,
        "generated_at_utc": now_utc(),
        "deep_SE_ID_audit": deep,
        "geometry_setup": rel(S3D_GEOMETRY_SETUP),
        "gates": gates,
        "failed_gates": failed,
        "pending_gates": pending,
        "production_launched": False,
        "postprocess_confirmation_contract": {
            "flag": "--allow-closure-run",
            "token": CONFIRM_TOKEN,
            "both_required": True,
        },
        "claim_boundary": (
            "PENDING is not zero and is not transport evidence. No Step05-Step08 "
            "result summary is created until screening and every production input pass."
        ),
        "output_scope": rel(FULLCHAIN),
        "shared_algorithm_authority": {
            "path": rel(SHARED_RUNNER),
            "sha256": sha256(SHARED_RUNNER),
            "reuse_boundary": (
                "numerical algorithms only; O8 mutable bindings are declared and "
                "audited by this runner"
            ),
        },
    }
    write_json(PREFLIGHT_JSON, payload)
    return payload


def require_ready(deep: bool = True) -> dict[str, Any]:
    shallow = build_preflight(deep=False)
    if shallow["failed_gates"]:
        raise O8ClosureGateError(
            "preflight failed: " + ", ".join(shallow["failed_gates"])
        )
    if shallow["status"] != "PASS_READY_FOR_O8_STEP05_08":
        return shallow
    payload = build_preflight(deep=deep)
    if payload["failed_gates"]:
        raise O8ClosureGateError(
            "deep preflight failed: " + ", ".join(payload["failed_gates"])
        )
    return payload


def shared_require_ready(deep: bool = True) -> dict[str, Any]:
    """Compatibility view used only inside the reviewed package-42 algorithm.

    The shared ``run_step05`` implementation compares its preflight status to
    its original literal.  Mutable files and console output still receive the
    package-local O8 status through ``o8ize``.
    """
    payload = require_ready(deep=deep)
    if payload.get("status") == "PASS_READY_FOR_O8_STEP05_08":
        payload = copy.deepcopy(payload)
        payload["status"] = "PASS_READY_FOR_STEP05_08"
    return payload


def configure_shared() -> None:
    bindings = {
        "ROOT": ROOT,
        "WORK": PACKAGE,
        "DATA": DATA,
        "FULLCHAIN": FULLCHAIN,
        "STEP05_OUT": STEP05_OUT,
        "STEP06_OUT": STEP06_OUT,
        "STEP07_OUT": STEP07_OUT,
        "STEP08_OUT": STEP08_OUT,
        "PREFLIGHT_JSON": PREFLIGHT_JSON,
        "STEP05_CORE_JSON": STEP05_CORE_JSON,
        "STEP05_JSON": STEP05_JSON,
        "STEP05_RATES": STEP05_RATES,
        "STEP06_JSON": STEP06_JSON,
        "STEP06_BG": STEP06_BG,
        "STEP07_JSON": STEP07_JSON,
        "STEP07_RATES": STEP07_RATES,
        "STEP08_JSON": STEP08_JSON,
        "PROMPT_DIR": PROMPT_DIR,
        "PROMPT_SUMMARY": PROMPT_SUMMARY,
        "PROMPT_NORM": PROMPT_NORM,
        "PROMPT_MANIFEST": PROMPT_MANIFEST,
        "PROMPT_SOURCE_MANIFEST": PROMPT_SOURCE_MANIFEST,
        "DELAY_LABEL": DELAY_LABEL,
        "DELAYED_SIM": DELAYED_SIM,
        "FIX_DIR": FIX_DIR,
        "FIXED_SOURCE": FIXED_SOURCE,
        "FIX_AUDIT": FIX_AUDIT,
        "GROUNDSTATE": GROUNDSTATE,
        "EXACT_SUMMARY": EXACT_SUMMARY,
        "DELAY_CAMPAIGN": DELAY_CAMPAIGN,
        "SIGNAL_RUN_DIR": SIGNAL_RUN_DIR,
        "SIGNAL_NAME": SIGNAL_NAME,
        "SIGNAL_SOURCE": SIGNAL_SOURCE,
        "SIGNAL_SIM": SIGNAL_SIM,
        "SIGNAL_MANIFEST": SIGNAL_MANIFEST,
        "SIGNAL_REPLAY_SUMMARY": SIGNAL_REPLAY_SUMMARY,
        "ATM_RUN_DIR": ATM_RUN_DIR,
        "ATM_NAME": ATM_NAME,
        "ATM_SOURCE": ATM_SOURCE,
        "ATM_SIM": ATM_SIM,
        "ATM_LOG": ATM_LOG,
        "ATM_MANIFEST": ATM_MANIFEST,
        "ATM_SUMMARY": ATM_SUMMARY,
        "SCREENING_ANALYSIS": SCREENING_ANALYSIS,
        "S3D_GEOMETRY_SETUP": S3D_GEOMETRY_SETUP,
        "AuditError": AuditError,
        "audit_geometry_authority": audit_geometry_authority,
        "selection_contract": selection_contract,
        "sim_header": sim_header,
        "rel": rel,
        "sha256": sha256,
        "load_json": compat_load_json,
        "write_json": write_json,
        "write_csv": write_csv,
        "configure_step05": configure_step05,
        "_policy_gate": policy_gate,
        "_prompt_gate": prompt_gate_csv,
        "_comparison_gate": comparison_gate,
        "heavy_control_direct_comparison": heavy_control_direct_comparison,
        "c0_screening_context": heavy_control_screening_context,
        "build_preflight": build_preflight,
        "require_ready": shared_require_ready,
    }
    for name, value in bindings.items():
        setattr(shared, name, value)


configure_shared()


def path_binding_audit() -> dict[str, Any]:
    paths = {
        "package": shared.WORK,
        "geometry": shared.S3D_GEOMETRY_SETUP,
        "prompt": shared.PROMPT_DIR,
        "delayed_sim": shared.DELAYED_SIM,
        "fixed_source": shared.FIXED_SOURCE,
        "exact_summary": shared.EXACT_SUMMARY,
        "signal": shared.SIGNAL_SIM,
        "atm511": shared.ATM_SIM,
        "screening": shared.SCREENING_ANALYSIS,
        "step05": shared.STEP05_JSON,
        "step06": shared.STEP06_JSON,
        "step07": shared.STEP07_JSON,
        "step08": shared.STEP08_JSON,
    }
    problems: list[str] = []
    for name, path in paths.items():
        text = str(path)
        if "42_geoopt_s3d_lightweight_20260712" in text:
            problems.append(f"mutable {name} points to package 42: {text}")
        if name not in {"package", "geometry"} and "s3d_o9" in text.lower():
            problems.append(f"mutable {name} retains O9 label: {text}")
    if shared.S3D_GEOMETRY_SETUP.resolve() != S3D_GEOMETRY_SETUP.resolve():
        problems.append("closure geometry is not O8")
    return {
        "status": "PASS" if not problems else "FAIL",
        "bindings": {name: rel(path) for name, path in paths.items()},
        "shared_algorithm_authority": rel(SHARED_RUNNER),
        "shared_algorithm_sha256": sha256(SHARED_RUNNER),
        "problems": problems,
    }


def require_postprocess_permission(args: argparse.Namespace) -> None:
    if not args.allow_closure_run:
        raise O8ClosureGateError(
            f"result-producing stages require --allow-closure-run --confirm {CONFIRM_TOKEN}"
        )
    if args.confirm != CONFIRM_TOKEN:
        raise O8ClosureGateError(
            f"closure confirmation mismatch; expected --confirm {CONFIRM_TOKEN}"
        )


def run_self_test() -> dict[str, Any]:
    numerical = shared.run_self_test()
    binding = path_binding_audit()
    promotion = audit_screening_promotion()
    checks = {
        "reviewed_numerical_self_test": numerical.get("status")
        == "PASS_LIGHTWEIGHT_SELF_TEST",
        "all_mutable_paths_o8_bound": binding["status"] == "PASS",
        "screening_gate_three_state": promotion["status"]
        in {
            "PASS_SCREENING_PROMOTION_GATE",
            "PENDING_SCREENING_GATE",
            "FAIL_SCREENING_GATE",
        },
        "historical_screening_substitution_forbidden": promotion.get(
            "historical_substitution_allowed"
        )
        is False,
        "dedicated_output_scope": FULLCHAIN.parent.resolve() == PACKAGE.resolve(),
        "shared_runner_present": SHARED_RUNNER.is_file(),
    }
    fake = argparse.Namespace(allow_closure_run=False, confirm=None)
    try:
        require_postprocess_permission(fake)
        checks["missing_double_confirmation_denied"] = False
    except O8ClosureGateError:
        checks["missing_double_confirmation_denied"] = True
    if not all(checks.values()):
        raise O8ClosureGateError(f"self-test failed: {checks}")
    return {
        "status": "PASS_O8_STEP05_08_HARNESS_SELF_TEST",
        "checks": checks,
        "screening_gate_observed": promotion,
        "path_binding_audit": binding,
        "production_launched": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "stage",
        choices=("preflight", "step05", "step06", "step07", "step08", "all", "self-test"),
        nargs="?",
        default="preflight",
    )
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--deep-preflight", action="store_true")
    parser.add_argument("--rebuild-cache", action="store_true")
    parser.add_argument("--allow-closure-run", action="store_true")
    parser.add_argument("--confirm")
    args = parser.parse_args()

    try:
        if args.stage == "self-test":
            payload = run_self_test()
        elif args.stage == "preflight":
            payload = build_preflight(deep=args.deep_preflight)
        else:
            require_postprocess_permission(args)
            ready = require_ready(deep=True)
            if ready["status"] != "PASS_READY_FOR_O8_STEP05_08":
                payload = ready
            else:
                payload = ready
                if args.stage in ("step05", "all"):
                    payload = shared.run_step05(args.workers, args.rebuild_cache)
                if args.stage in ("step06", "all"):
                    payload = shared.run_step06()
                if args.stage in ("step07", "all"):
                    payload = shared.run_step07()
                if args.stage in ("step08", "all"):
                    payload = shared.run_step08()
        payload = o8ize(payload)
        console = {
            "status": payload["status"],
            "preflight": rel(PREFLIGHT_JSON),
            "result": rel(STEP08_JSON) if STEP08_JSON.is_file() else None,
            "production_launched": False,
        }
        if "checks" in payload:
            console["checks"] = payload["checks"]
        if "pending_gates" in payload:
            console["pending_gates"] = payload["pending_gates"]
        print(json.dumps(console, indent=2, ensure_ascii=False))
        return 2 if str(payload["status"]).startswith("FAIL") else 0
    except (O8ClosureGateError, shared.ClosureGateError, AuditError, KeyError, ValueError) as exc:
        failure = {
            "status": "FAIL_CLOSED",
            "generated_at_utc": now_utc(),
            "error": str(exc),
            "production_launched": False,
            "screening_promotion": audit_screening_promotion(),
        }
        write_json(PREFLIGHT_JSON, failure)
        print(json.dumps(failure, indent=2, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
