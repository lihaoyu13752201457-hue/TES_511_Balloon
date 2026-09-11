#!/usr/bin/env python3
"""Final-status guard for the user-authorized recovery0002 controller.

The scheduling amendment itself is immutable.  This wrapper changes no job,
deadline, source, geometry, physics, retry, or resource gate.  It only promotes
a Stage20 validation error into the final fatal state, preventing a real proton
transport/resource/authority failure from being mislabeled as a clean finish.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import resume_m05_campaign_batch0006_recovery0002_early_stages as base


GUARD_ID = "batch0006_recovery0002_final_failure_guard0001"
GUARD_AUTHORITY = (
    base.campaign.RUN_ROOT / "recovery0002_final_failure_guard0001_authority.json"
)


def guard_payload() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "guard_id": GUARD_ID,
        "status": "PASS__FINAL_FAILURE_PROPAGATION_GUARD",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scope": (
            "if Stage20 validation.errors is non-empty, publish the existing "
            "recovery0002 final namespace with fatal/WITH_ERROR semantics"
        ),
        "scheduling_authority": base.campaign.rel(base.AUTHORITY),
        "scheduling_authority_sha256": base.campaign.sha256(base.AUTHORITY),
        "base_controller": {
            "path": base.campaign.rel(Path(base.__file__).resolve()),
            "sha256": base.campaign.sha256(Path(base.__file__).resolve()),
        },
        "guard_controller": {
            "path": base.campaign.rel(Path(__file__).resolve()),
            "sha256": base.campaign.sha256(Path(__file__).resolve()),
        },
        "global_contract_sha256": base.campaign.sha256(base.campaign.GLOBAL_CONTRACT),
        "unchanged": {
            "t0_deadline_and_stage_boundaries": True,
            "jobs_seeds_events": True,
            "sources_geometries_physics": True,
            "validation_retry_and_resource_gates": True,
            "publication_namespace": True,
        },
        "predecessor_launch_observation": {
            "base_controller_transport_events_launched": 0,
            "cosima_process_observed": False,
            "active_partial_attempt_observed": False,
        },
    }


def load_or_publish_guard(*, publish: bool) -> dict[str, Any]:
    if GUARD_AUTHORITY.is_file():
        payload = base.campaign.load_json(GUARD_AUTHORITY)
    else:
        payload = guard_payload()
        if not publish:
            return payload
        base.campaign.atomic_write_once_json(GUARD_AUTHORITY, payload)
        payload = base.campaign.load_json(GUARD_AUTHORITY)
    expected = {
        "guard_id": GUARD_ID,
        "status": "PASS__FINAL_FAILURE_PROPAGATION_GUARD",
        "scheduling_authority_sha256": base.campaign.sha256(base.AUTHORITY),
        "global_contract_sha256": base.campaign.sha256(base.campaign.GLOBAL_CONTRACT),
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise RuntimeError(f"recovery0002 final guard drift: {key}")
    if payload.get("base_controller", {}).get("sha256") != base.campaign.sha256(
        Path(base.__file__).resolve()
    ):
        raise RuntimeError("recovery0002 base controller drift after guard publication")
    if payload.get("guard_controller", {}).get("sha256") != base.campaign.sha256(
        Path(__file__).resolve()
    ):
        raise RuntimeError("recovery0002 guard controller drift after publication")
    return payload


def guarded_run_campaign(
    plan: list[dict[str, Any]],
    contract: dict[str, Any],
    environment: dict[str, str],
) -> int:
    fatal: str | None = None
    try:
        validation10, _ledger10 = base.recovery1.run_stage(
            "stage10_seven_family", plan, contract, environment
        )
        if validation10.get("errors"):
            raise RuntimeError(
                "Stage10 ended with a transport/resource/authority failure; "
                "Stage20 early launch forbidden: "
                + "; ".join(str(x) for x in validation10["errors"][:10])
            )
        validation20, _ledger20 = base.recovery1.run_stage(
            "stage20_proton", plan, contract, environment
        )
        if validation20.get("errors"):
            raise RuntimeError(
                "Stage20 ended with a transport/resource/authority failure: "
                + "; ".join(str(x) for x in validation20["errors"][:10])
            )
    except Exception as exc:
        fatal = str(exc)
    finally:
        base.recovery1.publish_final(plan, contract, fatal)
        completed = sum(
            base.campaign.receipt_path(job).is_file() for job in plan
        )
        base.campaign.update_state(
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
    parser.add_argument("--publish-guard-only", action="store_true")
    parser.add_argument("--cosima", type=Path, default=base.campaign.COSIMA_DEFAULT)
    args = parser.parse_args()
    payload = load_or_publish_guard(publish=True)
    if args.publish_guard_only:
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "guard_authority": base.campaign.rel(GUARD_AUTHORITY),
                    "guard_authority_sha256": base.campaign.sha256(GUARD_AUTHORITY),
                    "guard_controller_sha256": payload["guard_controller"]["sha256"],
                    "transport_launched": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    base.run_campaign = guarded_run_campaign
    sys.argv = [sys.argv[0], "--cosima", str(args.cosima)]
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
