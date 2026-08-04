#!/usr/bin/env python3
"""O8-bound all-eight prompt and neutron delayed-production harness.

The numerical implementation is reused from the reviewed O9 runner, but every
mutable geometry, label, run directory, log, source card, manifest, and status
is rebound to this O8 package.  Preparation never launches Cosima.  Every
production stage requires all three conditions below:

1. the final package-local screening authority is fully PASS;
2. ``--allow-heavy-run`` is present; and
3. ``--confirm`` exactly matches the stage-specific token.

The delayed contract remains neutron-only: eight ActivationBuildUp replicas,
TT division by eight, NUBASE-2020 ground-state correction, exact RPIP source
positions, M=50,000, and one million delayed-transport events.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _o8_promotion_gate import (
    audit_screening_promotion,
    require_screening_promotion,
)
from _o8_replay_common import (
    DATA,
    PACKAGE,
    ROOT,
    S3D_GEOMETRY_SETUP,
    audit_geometry_authority,
    cosima_environment,
    geometry_header_matches,
    rel,
    sha256,
    sim_header,
)


SHARED_RUNNER = (
    ROOT
    / "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712"
    / "code/run_s3d_delayed_activation.py"
)
SHARED_CODE = SHARED_RUNNER.parent

GEOMETRY_REL = rel(S3D_GEOMETRY_SETUP)
FULL_PROMPT_LABEL = "s3d_o8_fullstat_prompt_all8_20260712"
DELAY_LABEL = "s3d_o8_neutron_delayed_m50000_20260712"
RUN_ROOT = ROOT / "runs/geometry_optimization_20260704"
FULL_PROMPT_DIR = RUN_ROOT / FULL_PROMPT_LABEL
INSTANT_DIR = RUN_ROOT / f"step02_instant_{DELAY_LABEL}"
BUILDUP_DIR = RUN_ROOT / f"step02_buildup_{DELAY_LABEL}"
RAW_DIR = RUN_ROOT / f"step02_decay_source_{DELAY_LABEL}"
FIX_DIR = RUN_ROOT / f"step02_delay_fix_{DELAY_LABEL}"
EXACT_DIR = RUN_ROOT / f"step02_delay_exactpos_{DELAY_LABEL}"
DELAYED_TRANSPORT_DIR = RUN_ROOT / f"step02_delayed_transport_{DELAY_LABEL}"
SOURCE_PREFIX = DELAYED_TRANSPORT_DIR / "DelayedDecayS3dO8NeutronM50000"

CONFIG = PACKAGE / "config/full_prompt_all8"
SOURCE_CARDS = CONFIG / "source_cards"
LOGS = PACKAGE / "logs/fullchain_delayed"
DELAYED_REPORT_DIR = PACKAGE / "fullchain/delayed_source"
GEOMETRY_MANIFEST = DATA / "s3d_o8_geometry_manifest.json"
JOB_PREFLIGHT = DATA / "s3d_o8_full_prompt_and_delayed_job_preflight.json"
PREFLIGHT = DATA / "s3d_o8_full_prompt_and_delayed_preflight.json"
CAMPAIGN_MANIFEST = DATA / "s3d_o8_delayed_activation_campaign.json"

CONFIRM_TOKENS = {
    "run-full-prompt": "RUN_O8_FULL_PROMPT_ALL8",
    "run-buildup": "RUN_O8_NEUTRON_BUILDUP",
    "prepare-delay": "BUILD_O8_DELAYED_SOURCE_M50000",
    "run-delay": "RUN_O8_DELAYED_TRANSPORT_1M",
    "all": "RUN_O8_FULLCHAIN_TRANSPORT_ALL",
}

_STRING_REPLACEMENTS = (
    ("PASS_S3D_O9_ALL8_SOURCE_CARDS", "PASS_S3D_O8_ALL8_SOURCE_CARDS"),
    ("FAIL_S3D_O9_ALL8_SOURCE_CARDS", "FAIL_S3D_O8_ALL8_SOURCE_CARDS"),
    (
        "PASS_S3D_O9_FULL_PROMPT_DELAYED_PREFLIGHT",
        "PASS_S3D_O8_FULL_PROMPT_DELAYED_JOB_PREFLIGHT",
    ),
    (
        "FAIL_S3D_O9_FULL_PROMPT_DELAYED_PREFLIGHT",
        "FAIL_S3D_O8_FULL_PROMPT_DELAYED_JOB_PREFLIGHT",
    ),
    (
        "PASS_S3D_O9_NEUTRON_INSTANT_PROVENANCE",
        "PASS_S3D_O8_NEUTRON_INSTANT_PROVENANCE",
    ),
    (
        "FAIL_S3D_O9_NEUTRON_INSTANT_PROVENANCE",
        "FAIL_S3D_O8_NEUTRON_INSTANT_PROVENANCE",
    ),
    (
        "PASS_S3D_O9_NEUTRON_DELAYED_TRANSPORT",
        "PASS_S3D_O8_NEUTRON_DELAYED_TRANSPORT",
    ),
    (
        "S3D_O9_NEUTRON_DELAYED_CHAIN_INCOMPLETE",
        "S3D_O8_NEUTRON_DELAYED_CHAIN_INCOMPLETE",
    ),
    ("s3d_o9_full_prompt_and_neutron_only_delayed_chain", "s3d_o8_full_prompt_and_neutron_only_delayed_chain"),
    ("S3d-O9", "S3d-O8"),
    ("S3d O9", "S3d O8"),
    ("S3D_O9", "S3D_O8"),
    ("s3d_o9", "s3d_o8"),
)


class HarnessGateError(RuntimeError):
    """A fail-closed preparation or launch requirement was not met."""


def now_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _o8ize_string(value: str) -> str:
    out = value
    for old, new in _STRING_REPLACEMENTS:
        out = out.replace(old, new)
    if out == (
        "S3d O8: uniform 30 mm BGO, no outer W, retained 3 mm Al/Kapton "
        "and unchanged inner detector"
    ):
        out = (
            "S3d O8: retained 40 mm side BGO, 30 mm bottom BGO, 10 mm top "
            "BGO, no outer W, retained 3 mm Al/Kapton and unchanged inner detector"
        )
    return out


def o8ize(value: Any) -> Any:
    if isinstance(value, str):
        return _o8ize_string(value)
    if isinstance(value, list):
        return [o8ize(item) for item in value]
    if isinstance(value, tuple):
        return tuple(o8ize(item) for item in value)
    if isinstance(value, dict):
        return {o8ize(key): o8ize(item) for key, item in value.items()}
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(o8ize(payload), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def materialize_run_summary_json(run_dir: Path) -> dict[str, Any]:
    """Create the JSON-list compatibility view from the runner's CSV authority.

    The shared delayed-source implementation consumes ``run_summary.json``,
    while the actual transport runner emits only ``run_summary.csv``.  The CSV
    remains authoritative; this deterministic mirror is verified byte-for-byte
    on reuse and is confined to the new O8 run directories.
    """
    csv_path = run_dir / "run_summary.csv"
    json_path = run_dir / "run_summary.json"
    if not csv_path.is_file():
        raise RuntimeError(f"run summary CSV is absent: {rel(csv_path)}")
    with csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        schema = list(reader.fieldnames or [])
        rows = list(reader)
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
    if schema != expected_schema:
        raise RuntimeError(
            f"run summary CSV schema changed for {rel(csv_path)}: {schema}"
        )
    manifest_path = run_dir / "run_manifest.csv"
    if not manifest_path.is_file():
        raise RuntimeError(f"run manifest is absent: {rel(manifest_path)}")
    with manifest_path.open(encoding="utf-8", newline="") as handle:
        manifest_rows = list(csv.DictReader(handle))
    manifest_by_name = {row.get("job_name", ""): row for row in manifest_rows}
    row_names = [row.get("job_name", "") for row in rows]
    problems: list[str] = []
    if len(manifest_by_name) != len(manifest_rows):
        problems.append("run manifest has duplicate job names")
    if set(row_names) != set(manifest_by_name):
        problems.append("run summary and manifest job-name sets differ")
    audited: list[dict[str, Any]] = []
    for row in rows:
        name = row.get("job_name", "")
        manifest = manifest_by_name.get(name, {})
        sim = Path(row.get("sim_path", ""))
        dat = Path(row.get("dat_path", ""))
        if not sim.is_absolute():
            sim = ROOT / sim
        if not dat.is_absolute():
            dat = ROOT / dat
        header = sim_header(sim)
        tt_values: list[float] = []
        if dat.is_file():
            for raw in dat.read_text(encoding="utf-8", errors="replace").splitlines():
                fields = raw.split()
                if len(fields) == 2 and fields[0] == "TT":
                    try:
                        tt_values.append(float(fields[1]))
                    except ValueError:
                        pass
        local: list[str] = []
        events = int(row.get("events") or -1)
        generated = int(row.get("generated_particles") or -2)
        if row.get("status") not in ("PASS", "SKIP"):
            local.append(f"status={row.get('status')}")
        if generated != events:
            local.append("generated_particles!=events")
        if manifest and int(manifest.get("events") or -3) != events:
            local.append("manifest events differ from summary")
        if not sim.is_file() or not dat.is_file():
            local.append("missing SIM or DAT")
        if not geometry_header_matches(header.get("geometry"), S3D_GEOMETRY_SETUP):
            local.append(f"SIM geometry={header.get('geometry')}")
        if manifest and int(header.get("seed") or -1) != int(manifest.get("seed") or -2):
            local.append(
                f"SIM seed={header.get('seed')} manifest seed={manifest.get('seed')}"
            )
        if len(tt_values) != 1 or not math.isfinite(tt_values[0]) or tt_values[0] <= 0.0:
            local.append(f"TT={tt_values}")
        problems.extend(f"{name}: {item}" for item in local)
        audited.append(
            {
                "job_name": name,
                "events": events,
                "generated_particles": generated,
                "sim": rel(sim),
                "dat": rel(dat),
                "seed": header.get("seed"),
                "geometry": header.get("geometry"),
                "tt_s": tt_values[0] if len(tt_values) == 1 else tt_values,
                "status": "PASS" if not local else "FAIL",
            }
        )
    if problems:
        raise RuntimeError(
            f"completed-run audit failed for {rel(run_dir)}: " + "; ".join(problems)
        )
    text = json.dumps(rows, indent=2, ensure_ascii=False) + "\n"
    if json_path.exists():
        existing = load_json(json_path)
        normalized_existing = [
            {key: str(value) for key, value in row.items()}
            for row in existing
        ] if isinstance(existing, list) else []
        normalized_csv = [
            {key: str(value) for key, value in row.items()}
            for row in rows
        ]
        if normalized_existing != normalized_csv:
            raise RuntimeError(
                f"runner JSON and CSV summaries disagree: {rel(json_path)}"
            )
        state = "REUSED_RUNNER_JSON_SEMANTIC_MATCH"
    else:
        json_path.write_text(text, encoding="utf-8")
        state = "CREATED_FROM_CSV"
    return {
        "status": "PASS_RUN_SUMMARY_CSV_TO_JSON_COMPATIBILITY_VIEW",
        "csv": rel(csv_path),
        "csv_sha256": sha256(csv_path),
        "json": rel(json_path),
        "json_sha256": sha256(json_path),
        "rows": len(rows),
        "schema": schema,
        "completed_run_audit": audited,
        "state": state,
        "authority": "CSV",
    }


def materialize_completed_summaries() -> dict[str, Any]:
    evidence: dict[str, Any] = {}
    for name, run_dir in (
        ("full_prompt", FULL_PROMPT_DIR),
        ("neutron_buildup", BUILDUP_DIR),
    ):
        if (run_dir / "run_summary.csv").is_file():
            evidence[name] = materialize_run_summary_json(run_dir)
    return evidence


def _load_shared() -> Any:
    if str(SHARED_CODE) not in sys.path:
        sys.path.insert(0, str(SHARED_CODE))
    spec = importlib.util.spec_from_file_location(
        "o8_fullchain_shared_delayed", SHARED_RUNNER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load shared delayed runner: {rel(SHARED_RUNNER)}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


shared = _load_shared()


def _correct_exactpos_boundary(
    module: Any, manifest: dict[str, Any], transport: dict[str, Any] | None
) -> dict[str, Any]:
    manifest["boundary"] = [
        "The exact-position source uses the O8 neutron-only eight-replica buildup and day-15 NUBASE ground-state-corrected activity.",
        "It is a transport artifact, not a detector-selected rate authority until the dedicated Step05-Step08 closure is complete.",
        (
            f"Sampling uses M={shared.M_BLOCKS}, seed={shared.SEED}, "
            f"N_SAMPLE={shared.N_SAMPLE}, raw triggers={shared.RAW_TRIGGERS}, "
            f"and neutron TT division={shared.NON_GAMMA_DIV}."
        ),
    ]
    manifest["provenance_contract"] = {
        "geometry_setup": GEOMETRY_REL,
        "full_prompt_instant": rel(FULL_PROMPT_DIR),
        "assembled_neutron_instant": rel(INSTANT_DIR),
        "neutron_buildup": rel(BUILDUP_DIR),
        "nubase": rel(shared.NUBASE),
        "nubase_sha256": sha256(shared.NUBASE),
        "non_gamma_div": shared.NON_GAMMA_DIV,
        "n_sample": shared.N_SAMPLE,
        "raw_triggers": shared.RAW_TRIGGERS,
        "m_pointsource_blocks": shared.M_BLOCKS,
        "seed": shared.SEED,
        "variant": "s3d_o8_side40_bottom30_top10_no_outer_w2_al3",
    }
    module.write_json(module.MANIFEST, o8ize(manifest))
    module.write_summary(o8ize(manifest), o8ize(transport))
    return o8ize(manifest)


def configure_shared() -> None:
    """Rebind every mutable shared-runner authority to new O8 paths."""
    bindings = {
        "ROOT": ROOT,
        "WORK": PACKAGE,
        "DATA": DATA,
        "CONFIG": CONFIG,
        "SOURCE_CARDS": SOURCE_CARDS,
        "LOGS": LOGS,
        "GEOMETRY_REL": GEOMETRY_REL,
        "GEOMETRY": S3D_GEOMETRY_SETUP,
        "GEOMETRY_MANIFEST": GEOMETRY_MANIFEST,
        "RUN_ROOT": RUN_ROOT,
        "FULL_PROMPT_LABEL": FULL_PROMPT_LABEL,
        "FULL_PROMPT_DIR": FULL_PROMPT_DIR,
        "DELAY_LABEL": DELAY_LABEL,
        "INSTANT_DIR": INSTANT_DIR,
        "BUILDUP_DIR": BUILDUP_DIR,
        "RAW_DIR": RAW_DIR,
        "FIX_DIR": FIX_DIR,
        "EXACT_DIR": EXACT_DIR,
        "DELAYED_TRANSPORT_DIR": DELAYED_TRANSPORT_DIR,
        "DELAYED_REPORT_DIR": DELAYED_REPORT_DIR,
        "CAMPAIGN_MANIFEST": CAMPAIGN_MANIFEST,
        "PREPARED_AUDIT": JOB_PREFLIGHT,
        "SOURCE_PREFIX": SOURCE_PREFIX,
        "audit_geometry_authority": audit_geometry_authority,
        "cosima_environment": cosima_environment,
        "write_json": write_json,
        "correct_exactpos_boundary": _correct_exactpos_boundary,
    }
    for name, value in bindings.items():
        setattr(shared, name, value)


configure_shared()


def _path_binding_audit() -> dict[str, Any]:
    paths = {
        "package": PACKAGE,
        "geometry": shared.GEOMETRY,
        "source_cards": shared.SOURCE_CARDS,
        "full_prompt": shared.FULL_PROMPT_DIR,
        "instant": shared.INSTANT_DIR,
        "buildup": shared.BUILDUP_DIR,
        "raw": shared.RAW_DIR,
        "fix": shared.FIX_DIR,
        "exact": shared.EXACT_DIR,
        "delayed_transport": shared.DELAYED_TRANSPORT_DIR,
        "delayed_report": shared.DELAYED_REPORT_DIR,
        "campaign_manifest": shared.CAMPAIGN_MANIFEST,
    }
    problems: list[str] = []
    for name, path in paths.items():
        text = str(path)
        if "42_geoopt_s3d_lightweight_20260712" in text:
            problems.append(f"mutable {name} still points to package 42: {text}")
        if name != "geometry" and name != "package" and "s3d_o9" in text.lower():
            problems.append(f"mutable {name} retains O9 label: {text}")
    if shared.GEOMETRY.resolve() != S3D_GEOMETRY_SETUP.resolve():
        problems.append("shared geometry is not the O8 setup")
    return {
        "status": "PASS" if not problems else "FAIL",
        "shared_algorithm_authority": rel(SHARED_RUNNER),
        "shared_algorithm_sha256": sha256(SHARED_RUNNER),
        "mutable_bindings": {name: rel(path) for name, path in paths.items()},
        "problems": problems,
    }


def build_preflight(job_audit: dict[str, Any] | None = None) -> dict[str, Any]:
    promotion = audit_screening_promotion()
    try:
        geometry = {"status": "PASS", "authority": audit_geometry_authority()}
    except Exception as exc:  # retained verbatim in the fail-closed audit
        geometry = {"status": "FAIL", "problems": [str(exc)]}
    binding = _path_binding_audit()
    source_manifest_path = SOURCE_CARDS / "source_migration_manifest.json"
    source_manifest = (
        load_json(source_manifest_path) if source_manifest_path.is_file() else {}
    )
    if job_audit is None and JOB_PREFLIGHT.is_file():
        job_audit = load_json(JOB_PREFLIGHT)
    job_audit = job_audit or {}

    failures: list[str] = []
    if geometry["status"] != "PASS":
        failures.append("geometry")
    if binding["status"] != "PASS":
        failures.append("path_bindings")
    if source_manifest and source_manifest.get("status") != "PASS_S3D_O8_ALL8_SOURCE_CARDS":
        failures.append("source_cards")
    if job_audit and job_audit.get("status") != "PASS_S3D_O8_FULL_PROMPT_DELAYED_JOB_PREFLIGHT":
        failures.append("prepared_jobs")
    if promotion["status"] == "FAIL_SCREENING_GATE":
        failures.append("screening_promotion")

    status = (
        "FAIL_CLOSED"
        if failures
        else "PENDING_SCREENING_GATE"
        if promotion["status"] != "PASS_SCREENING_PROMOTION_GATE"
        else "PASS_O8_FULL_PROMPT_DELAYED_PREFLIGHT"
        if source_manifest and job_audit
        else "PENDING_PREPARATION_INPUTS"
    )
    payload = {
        "status": status,
        "generated_at_utc": now_utc(),
        "production_launched": False,
        "geometry_setup": GEOMETRY_REL,
        "screening_promotion": promotion,
        "geometry": geometry,
        "path_binding_audit": binding,
        "source_cards": {
            "manifest": rel(source_manifest_path),
            "status": source_manifest.get("status"),
        },
        "prepared_jobs": {
            "audit": rel(JOB_PREFLIGHT),
            "status": job_audit.get("status"),
        },
        "failed_gates": failures,
        "heavy_confirmation_contract": {
            "flag": "--allow-heavy-run",
            "stage_tokens": CONFIRM_TOKENS,
            "both_required_after_screening_pass": True,
        },
        "statistics": {
            "prompt_jobs": 68,
            "gamma_events": shared.GAMMA_EVENTS,
            "gamma_splits": shared.GAMMA_SPLITS,
            "non_gamma_replicas": shared.NON_GAMMA_REPLICAS,
            "neutron_buildup_jobs": 8,
            "neutron_tt_division": shared.NON_GAMMA_DIV,
            "n_sample": shared.N_SAMPLE,
            "raw_triggers": shared.RAW_TRIGGERS,
            "exact_position_blocks": shared.M_BLOCKS,
            "seed": shared.SEED,
        },
        "claim_boundary": (
            "Preparation and audit only. PENDING_SCREENING_GATE is not a transport "
            "result and cannot be replaced by historical O9 evidence."
        ),
    }
    write_json(PREFLIGHT, payload)
    return payload


def require_heavy_permission(args: argparse.Namespace, stage: str) -> dict[str, Any]:
    token = CONFIRM_TOKENS[stage]
    if not args.allow_heavy_run:
        raise HarnessGateError(
            f"{stage} requires --allow-heavy-run and --confirm {token}"
        )
    if args.confirm != token:
        raise HarnessGateError(
            f"{stage} confirmation mismatch; expected --confirm {token}"
        )
    try:
        return require_screening_promotion()
    except RuntimeError as exc:
        raise HarnessGateError(str(exc)) from exc


def require_prepared() -> None:
    if not JOB_PREFLIGHT.is_file():
        raise HarnessGateError(
            f"missing prepared-job audit; run prepare first: {rel(JOB_PREFLIGHT)}"
        )
    payload = load_json(JOB_PREFLIGHT)
    if payload.get("status") != "PASS_S3D_O8_FULL_PROMPT_DELAYED_JOB_PREFLIGHT":
        raise HarnessGateError(
            f"prepared-job audit is not PASS: {payload.get('status')}"
        )


def write_campaign() -> dict[str, Any]:
    payload = o8ize(shared.current_status())
    transport_ready = payload["delayed_transport"]["status"] == "PASS"
    payload["status"] = (
        "PASS_S3D_O8_NEUTRON_DELAYED_TRANSPORT"
        if transport_ready
        else "S3D_O8_NEUTRON_DELAYED_CHAIN_INCOMPLETE"
    )
    payload["screening_promotion"] = audit_screening_promotion()
    payload["path_binding_audit"] = _path_binding_audit()
    payload["shared_algorithm_authority"] = {
        "path": rel(SHARED_RUNNER),
        "sha256": sha256(SHARED_RUNNER),
        "reuse_boundary": "algorithm only; every mutable authority is rebound and audited above",
    }
    write_json(CAMPAIGN_MANIFEST, payload)
    return payload


def run_self_test() -> dict[str, Any]:
    binding = _path_binding_audit()
    promotion = audit_screening_promotion()
    checks = {
        "path_bindings_o8_only": binding["status"] == "PASS",
        "screening_gate_has_three_state_status": promotion["status"]
        in {
            "PASS_SCREENING_PROMOTION_GATE",
            "PENDING_SCREENING_GATE",
            "FAIL_SCREENING_GATE",
        },
        "historical_substitution_forbidden": promotion.get(
            "historical_substitution_allowed"
        )
        is False,
        "four_unique_confirmation_tokens": len(set(CONFIRM_TOKENS.values()))
        == len(CONFIRM_TOKENS),
        "exact_position_m50000": shared.M_BLOCKS == 50_000,
        "neutron_tt_division_guard": shared.NON_GAMMA_DIV == 8,
        "nubase_present": shared.NUBASE.is_file(),
        "shared_runner_is_read_only_authority": SHARED_RUNNER.is_file(),
    }
    fake = argparse.Namespace(allow_heavy_run=False, confirm=None)
    try:
        require_heavy_permission(fake, "run-full-prompt")
        checks["missing_double_confirmation_denied"] = False
    except HarnessGateError:
        checks["missing_double_confirmation_denied"] = True
    if not all(checks.values()):
        raise HarnessGateError(f"self-test failed: {checks}")
    return {
        "status": "PASS_O8_DELAYED_HARNESS_SELF_TEST",
        "checks": checks,
        "screening_gate_observed": promotion,
        "production_launched": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "stage",
        choices=(
            "preflight",
            "prepare",
            "run-full-prompt",
            "assemble-instant",
            "run-buildup",
            "prepare-delay",
            "run-delay",
            "status",
            "all",
            "self-test",
        ),
        nargs="?",
        default="preflight",
    )
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--allow-heavy-run", action="store_true")
    parser.add_argument("--confirm")
    args = parser.parse_args()

    try:
        if args.stage == "self-test":
            payload = run_self_test()
        elif args.stage == "preflight":
            payload = build_preflight()
        else:
            if args.stage in CONFIRM_TOKENS:
                require_heavy_permission(args, args.stage)

            job_audit: dict[str, Any] | None = None
            if args.stage in ("prepare", "all"):
                shared.migrate_source_cards()
                shared.prepare_job_sources(args.workers)
                job_audit = o8ize(shared.inspect_prepared_jobs())
            if args.stage in ("run-full-prompt", "all"):
                require_prepared()
                shared.run_equiv_transport(
                    "instant", FULL_PROMPT_DIR, args.workers, "", args.force
                )
                materialize_run_summary_json(FULL_PROMPT_DIR)
            if args.stage in ("assemble-instant", "all"):
                materialize_run_summary_json(FULL_PROMPT_DIR)
                shared.assemble_instant_neutron()
            if args.stage in ("run-buildup", "all"):
                require_prepared()
                shared.run_equiv_transport(
                    "buildup", BUILDUP_DIR, args.workers, "n", args.force
                )
                materialize_run_summary_json(BUILDUP_DIR)
            if args.stage in ("prepare-delay", "all"):
                materialize_completed_summaries()
                shared.build_raw_source(args.workers, args.force)
                shared.build_fixed_source(args.force)
                shared.build_exactpos_source(args.force)
            if args.stage in ("run-delay", "all"):
                shared.run_delayed_transport(args.force)

            compatibility_views = materialize_completed_summaries()
            campaign = write_campaign()
            preflight = build_preflight(job_audit)
            payload = {
                "status": preflight["status"],
                "campaign_status": campaign["status"],
                "campaign_manifest": rel(CAMPAIGN_MANIFEST),
                "preflight": rel(PREFLIGHT),
                "run_summary_compatibility_views": compatibility_views,
                "production_launched": args.stage in CONFIRM_TOKENS,
            }
        print(json.dumps(o8ize(payload), indent=2, ensure_ascii=False))
        return 2 if str(payload["status"]).startswith("FAIL") else 0
    except (HarnessGateError, RuntimeError, ValueError, KeyError) as exc:
        failure = {
            "status": "FAIL_CLOSED",
            "generated_at_utc": now_utc(),
            "error": str(exc),
            "production_launched": False,
            "screening_promotion": audit_screening_promotion(),
        }
        write_json(PREFLIGHT, failure)
        print(json.dumps(failure, indent=2, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
