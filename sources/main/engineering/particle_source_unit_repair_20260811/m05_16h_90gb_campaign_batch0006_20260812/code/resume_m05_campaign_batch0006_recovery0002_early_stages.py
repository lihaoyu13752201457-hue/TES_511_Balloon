#!/usr/bin/env python3
"""User-authorized scheduling-only amendment for M05 batch0006.

The recovery0001 smoke is complete and an independent analysis session returned
``VERDICT=ANALYSIS_READY_CONTINUE``.  The user then explicitly authorized
starting production immediately instead of idling until the originally planned
stage boundaries.  This controller removes only the *start waits* for Stage10
and Stage20.  It preserves the frozen T0, stop-launch and hard-end deadlines,
all jobs/seeds/events, corrected sources, geometry, transport fingerprint,
physics, validation, disk/RSS gates, retry policy, and merge domains.

Recovery0001 smoke authority remains immutable.  Stage10, Stage20, and final
publications use a recovery0002 namespace and bind this amendment.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import resume_m05_campaign_batch0006_recovery0001 as recovery1
import run_m05_16h_campaign_batch0006 as campaign


RECOVERY_ID = "batch0006_recovery0002_user_authorized_early_stages"
AUTHORITY = campaign.RUN_ROOT / "recovery0002_early_stages_authority.json"
RECOVERY1_AUTHORITY = campaign.RUN_ROOT / "recovery0001_authority.json"
RECOVERY1_SMOKE_DECISION = campaign.RUN_ROOT / "smoke_decision.recovery0001.json"

STAGE_PATHS = {
    "stage00_mergeable_smoke": (
        campaign.RUN_ROOT / "checkpoint_authority/smoke_validation.recovery0001.json",
        campaign.RUN_ROOT / "checkpoint_authority/smoke_ledger.recovery0001.json",
    ),
    "stage10_seven_family": (
        campaign.RUN_ROOT / "seven_family_validation.recovery0002.json",
        campaign.RUN_ROOT / "seven_family_ledger.recovery0002.json",
    ),
    "stage20_proton": (
        campaign.RUN_ROOT / "proton_validation.recovery0002.json",
        campaign.RUN_ROOT / "proton_ledger.recovery0002.json",
    ),
}

FINAL_VALIDATION = campaign.RUN_ROOT / "final_validation.recovery0002.json"
FINAL_LEDGER = campaign.RUN_ROOT / "final_ledger.recovery0002.json"
FINAL_UMBRELLA = campaign.RUN_ROOT / "final_umbrella.recovery0002.json"


def recovery2_stage_paths(stage: str) -> tuple[Path, Path]:
    return STAGE_PATHS[stage]


def bind_stage_recovery2(
    stage: str, validation: dict[str, Any], ledger: dict[str, Any]
) -> None:
    validation_path, ledger_path = recovery2_stage_paths(stage)
    binding = (
        campaign.RUN_ROOT
        / "checkpoint_authority"
        / f"{stage}.recovery0002.binding.json"
    )
    campaign.atomic_write_once_json(
        binding,
        {
            "schema_version": 1,
            "recovery_id": RECOVERY_ID,
            "status": "PASS__HASH_BOUND_RECOVERY0002_PUBLICATION",
            "scheduling_amendment": campaign.rel(AUTHORITY),
            "scheduling_amendment_sha256": campaign.sha256(AUTHORITY),
            "global_contract_sha256": recovery1.FROZEN_GLOBAL_CONTRACT_SHA256,
            "validation": campaign.rel(validation_path),
            "validation_sha256": campaign.sha256(validation_path),
            "ledger": campaign.rel(ledger_path),
            "ledger_sha256": campaign.sha256(ledger_path),
            "validation_status": validation["status"],
            "ledger_status": ledger["status"],
        },
    )


def load_frozen_inputs() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    contract = recovery1.frozen_contract()
    plan = campaign.build_plan()
    if contract.get("planned_jobs_sha256") != campaign.json_sha256(plan):
        raise RuntimeError("current job plan differs from the frozen global contract")
    if not RECOVERY1_AUTHORITY.is_file() or not RECOVERY1_SMOKE_DECISION.is_file():
        raise RuntimeError("recovery0001 authority or smoke decision is missing")
    smoke = campaign.load_json(RECOVERY1_SMOKE_DECISION)
    if (
        smoke.get("status") != "PASS__BATCH0006_STAGE00_MERGE_ELIGIBLE"
        or smoke.get("production_may_continue") is not True
    ):
        raise RuntimeError("recovery0001 smoke does not authorize production")
    validation = STAGE_PATHS["stage00_mergeable_smoke"][0]
    ledger = STAGE_PATHS["stage00_mergeable_smoke"][1]
    if (
        not validation.is_file()
        or not ledger.is_file()
        or campaign.load_json(validation).get("validated_jobs") != 100
        or campaign.load_json(validation).get("validated_events") != 55_424
        or campaign.load_json(ledger).get("status")
        != "PASS__BATCH0006_STAGE00_MERGE_ELIGIBLE"
    ):
        raise RuntimeError("recovery0001 smoke validation/ledger closure differs")
    for stage in ("stage10_seven_family", "stage20_proton"):
        for path in STAGE_PATHS[stage]:
            if path.exists():
                raise RuntimeError(f"recovery0002 canonical output already exists: {path}")
    for path in (FINAL_VALIDATION, FINAL_LEDGER, FINAL_UMBRELLA):
        if path.exists():
            raise RuntimeError(f"recovery0002 final output already exists: {path}")
    return contract, plan


def authority_payload(
    contract: dict[str, Any], plan: list[dict[str, Any]], authorized_at: datetime
) -> dict[str, Any]:
    original_stages = {
        row["id"]: row for row in contract["wall_clock"]["stages"]
    }
    stage00_validation, stage00_ledger = STAGE_PATHS["stage00_mergeable_smoke"]
    analysis_thread = "019ff5e1-6885-78b2-a9b4-8e6b2d060453"
    return {
        "schema_version": 1,
        "recovery_id": RECOVERY_ID,
        "status": "PASS__USER_AUTHORIZED_SCHEDULING_ONLY_AMENDMENT",
        "batch_id": campaign.BATCH_ID,
        "created_at": authorized_at.isoformat(),
        "authorization": {
            "source": "direct user instruction in the controlling Codex thread",
            "source_thread_id": "019ff59f-61a0-7852-9bad-322556e62ff4",
            "instruction": (
                "start production now; no need to wait because the independent "
                "session has audited the data as sufficient"
            ),
            "scope": "remove idle stage-start waits only",
        },
        "independent_analysis": {
            "thread_id": analysis_thread,
            "verdict": "ANALYSIS_READY_CONTINUE",
            "scope": (
                "corrected-keV smoke and analysis-pipeline compatibility; partial "
                "screening only, not final delayed response/sensitivity/promotion"
            ),
        },
        "global_contract": campaign.rel(campaign.GLOBAL_CONTRACT),
        "global_contract_sha256": campaign.sha256(campaign.GLOBAL_CONTRACT),
        "recovery0001_authority": campaign.rel(RECOVERY1_AUTHORITY),
        "recovery0001_authority_sha256": campaign.sha256(RECOVERY1_AUTHORITY),
        "recovery0001_smoke_decision": campaign.rel(RECOVERY1_SMOKE_DECISION),
        "recovery0001_smoke_decision_sha256": campaign.sha256(
            RECOVERY1_SMOKE_DECISION
        ),
        "recovery0001_smoke_validation": campaign.rel(stage00_validation),
        "recovery0001_smoke_validation_sha256": campaign.sha256(
            stage00_validation
        ),
        "recovery0001_smoke_ledger": campaign.rel(stage00_ledger),
        "recovery0001_smoke_ledger_sha256": campaign.sha256(stage00_ledger),
        "controller": {
            "path": campaign.rel(Path(__file__).resolve()),
            "sha256": campaign.sha256(Path(__file__).resolve()),
        },
        "recovery0001_controller": {
            "path": campaign.rel(Path(recovery1.__file__).resolve()),
            "sha256": campaign.sha256(Path(recovery1.__file__).resolve()),
        },
        "planned_jobs_sha256": campaign.json_sha256(plan),
        "planned_jobs": len(plan),
        "planned_events": sum(int(row["events"]) for row in plan),
        "original_schedule": original_stages,
        "amended_schedule": {
            "stage10_seven_family": {
                "start": "immediately when this amendment controller passes preflight",
                "stop_launch_s_from_frozen_t0": original_stages[
                    "stage10_seven_family"
                ]["stop_launch_s"],
                "hard_end_s_from_frozen_t0": original_stages[
                    "stage10_seven_family"
                ]["hard_end_s"],
            },
            "stage20_proton": {
                "start": "immediately after Stage10 returns",
                "stop_launch_s_from_frozen_t0": original_stages[
                    "stage20_proton"
                ]["stop_launch_s"],
                "hard_end_s_from_frozen_t0": original_stages[
                    "stage20_proton"
                ]["hard_end_s"],
            },
            "campaign_deadline": contract["wall_clock"]["deadline"],
        },
        "unchanged": {
            "t0": contract["wall_clock"]["t0"],
            "deadline": contract["wall_clock"]["deadline"],
            "jobs": True,
            "seeds": True,
            "events": True,
            "source_cards": True,
            "geometries": True,
            "cosima_and_g4_fingerprint": True,
            "physics_and_cut": True,
            "validation_and_retry": True,
            "disk_rss_and_merge_gates": True,
        },
        "post_mainline_statistics_intent": {
            "authorized": True,
            "executed_by_this_amendment": False,
            "rule": (
                "after the frozen mainline is complete, assess time/disk/memory and "
                "use a separate write-once continuation with fresh collision-free "
                "seeds and the same physics contract if extra statistics are safe"
            ),
        },
        "publication_namespace": {
            "stage00": "recovery0001 immutable authority",
            "stage10": campaign.rel(STAGE_PATHS["stage10_seven_family"][1]),
            "stage20": campaign.rel(STAGE_PATHS["stage20_proton"][1]),
            "final": campaign.rel(FINAL_UMBRELLA),
        },
    }


def load_or_publish_authority(
    contract: dict[str, Any],
    plan: list[dict[str, Any]],
    *,
    publish: bool,
) -> dict[str, Any]:
    """Load the immutable amendment, or publish it exactly once.

    Publication is deliberately available before controller-lock acquisition so
    the scheduling authority exists before the idle recovery0001 process is
    force-stopped.  A later transport launch must revalidate every bound hash.
    """
    if AUTHORITY.is_file():
        payload = campaign.load_json(AUTHORITY)
    else:
        payload = authority_payload(contract, plan, datetime.now(timezone.utc))
        if not publish:
            return payload
        campaign.atomic_write_once_json(AUTHORITY, payload)
        payload = campaign.load_json(AUTHORITY)
    expected = {
        "recovery_id": RECOVERY_ID,
        "status": "PASS__USER_AUTHORIZED_SCHEDULING_ONLY_AMENDMENT",
        "global_contract_sha256": campaign.sha256(campaign.GLOBAL_CONTRACT),
        "recovery0001_authority_sha256": campaign.sha256(RECOVERY1_AUTHORITY),
        "recovery0001_smoke_decision_sha256": campaign.sha256(
            RECOVERY1_SMOKE_DECISION
        ),
        "recovery0001_smoke_validation_sha256": campaign.sha256(
            STAGE_PATHS["stage00_mergeable_smoke"][0]
        ),
        "recovery0001_smoke_ledger_sha256": campaign.sha256(
            STAGE_PATHS["stage00_mergeable_smoke"][1]
        ),
        "planned_jobs_sha256": campaign.json_sha256(plan),
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise RuntimeError(f"recovery0002 amendment drift: {key}")
    controller = payload.get("controller", {})
    if controller.get("sha256") != campaign.sha256(Path(__file__).resolve()):
        raise RuntimeError("recovery0002 controller differs from amendment authority")
    if payload.get("unchanged", {}).get("deadline") != contract["wall_clock"][
        "deadline"
    ]:
        raise RuntimeError("recovery0002 amendment changed the frozen deadline")
    return payload


def configure_runtime() -> None:
    # recovery0001 set this in its main(); importing the module alone does not.
    # The underlying validator still consults campaign.ID_RE at runtime.
    campaign.ID_RE = recovery1.re.compile(recovery1.CORRECT_ID_PATTERN)
    recovery1.RECOVERY_ID = RECOVERY_ID
    recovery1.RECOVERY_AUTHORITY = AUTHORITY
    recovery1.RECOVERY_STAGE_PATHS = STAGE_PATHS
    recovery1.RECOVERY_FINAL_VALIDATION = FINAL_VALIDATION
    recovery1.RECOVERY_FINAL_LEDGER = FINAL_LEDGER
    recovery1.RECOVERY_FINAL_UMBRELLA = FINAL_UMBRELLA
    recovery1.bind_stage = bind_stage_recovery2
    campaign.stage_paths = recovery2_stage_paths
    campaign.validate_attempt = recovery1.strict_validate_attempt
    campaign.ensure_job = recovery1.strict_ensure_job
    # Only remove idle start waits.  Stop-launch and hard-end values remain
    # exactly those frozen in the original contract and in STAGES.
    campaign.STAGES["stage10_seven_family"]["start_s"] = 0
    campaign.STAGES["stage20_proton"]["start_s"] = 0


def run_campaign(
    plan: list[dict[str, Any]], contract: dict[str, Any], environment: dict[str, str]
) -> int:
    fatal: str | None = None
    try:
        validation10, _ledger10 = recovery1.run_stage(
            "stage10_seven_family", plan, contract, environment
        )
        if validation10.get("errors"):
            raise RuntimeError(
                "Stage10 ended with a transport/resource/authority failure; "
                "Stage20 early launch forbidden: "
                + "; ".join(str(x) for x in validation10["errors"][:10])
            )
        recovery1.run_stage("stage20_proton", plan, contract, environment)
    except Exception as exc:
        fatal = str(exc)
    finally:
        recovery1.publish_final(plan, contract, fatal)
        completed = sum(campaign.receipt_path(job).is_file() for job in plan)
        campaign.update_state(
            contract,
            status=(
                "FINALIZED_RECOVERY0002"
                if fatal is None
                else "FINALIZED_RECOVERY0002_WITH_ERROR"
            ),
            stage="final",
            completed_jobs=completed,
            last_error=fatal,
        )
    if fatal:
        raise SystemExit(fatal)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-amendment-plan", action="store_true")
    parser.add_argument("--publish-amendment-only", action="store_true")
    parser.add_argument("--cosima", type=Path, default=campaign.COSIMA_DEFAULT)
    args = parser.parse_args()
    contract, plan = load_frozen_inputs()
    proposed = load_or_publish_authority(contract, plan, publish=False)
    if args.print_amendment_plan:
        print(
            json.dumps(
                {
                    "status": "PASS__READ_ONLY_RECOVERY0002_PLAN",
                    "recovery_id": RECOVERY_ID,
                    "global_contract_sha256": proposed["global_contract_sha256"],
                    "smoke_status": campaign.load_json(RECOVERY1_SMOKE_DECISION)[
                        "status"
                    ],
                    "analysis_verdict": proposed["independent_analysis"]["verdict"],
                    "amended_schedule": proposed["amended_schedule"],
                    "unchanged": proposed["unchanged"],
                    "controller_sha256": proposed["controller"]["sha256"],
                    "transport_launched": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.publish_amendment_only:
        published = load_or_publish_authority(contract, plan, publish=True)
        print(
            json.dumps(
                {
                    "status": "PASS__RECOVERY0002_AMENDMENT_WRITE_ONCE",
                    "authority": campaign.rel(AUTHORITY),
                    "authority_sha256": campaign.sha256(AUTHORITY),
                    "controller_sha256": published["controller"]["sha256"],
                    "transport_launched": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    lock = campaign.acquire_lock()
    previous: dict[int, Any] = {}
    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.getsignal(signum)
            signal.signal(signum, campaign._signal_handler)
        load_or_publish_authority(contract, plan, publish=True)
        configure_runtime()
        loaded_contract, environment = campaign.create_or_load(
            plan, args.cosima.resolve(), datetime.now(timezone.utc)
        )
        campaign.update_state(
            loaded_contract,
            status="RUNNING__RECOVERY0002__EARLY_STAGE10",
            stage="stage10_seven_family",
            completed_jobs=sum(campaign.receipt_path(job).is_file() for job in plan),
        )
        return run_campaign(plan, loaded_contract, environment)
    finally:
        if campaign._ACTIVE_PROCESS is not None:
            campaign.terminate_group(campaign._ACTIVE_PROCESS)
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()


if __name__ == "__main__":
    raise SystemExit(main())
