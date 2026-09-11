#!/usr/bin/env python3
"""Build the fixed SF3 full-stat resource/guard timeline authority.

Only named compact Plan-1/full-stat CSV, JSON and JSONL authorities are read.
SIM paths that may appear as receipt metadata are never opened, stated,
discovered or hashed.  The auditor never launches transport or calls systemd.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence

import run_sf3_fullstat_followup as followup
from sf3_plan1_common import PROFILE_ID as PLAN1_PROFILE_ID
from sf3_plan1_common import RUN_ROOT as PLAN1_RUN_ROOT


HERE = Path(__file__).resolve()
PACKAGE_ROOT = HERE.parent.parent
OUTPUT = PACKAGE_ROOT / "audit/sf3_fullstat_resource_timeline.json"
MANIFEST = PACKAGE_ROOT / "data/sf3_fullstat_followup_execution_manifest.json"
PLAN1_AGGREGATE = PACKAGE_ROOT / "audit/sf3_plan1_transport_receipts.json"
PLAN1_PLAN = PACKAGE_ROOT / "data/sf3_plan1_job_plan.csv"
TOPUP_PLAN = PACKAGE_ROOT / followup.TOPUP_PLAN
TOPUP_AGGREGATE = PACKAGE_ROOT / followup.TOPUP_AGGREGATE
ACTIVATION_VALIDATION = PACKAGE_ROOT / followup.FULLSTAT_ACTIVATION_VALIDATION
DELAYED_PLAN = PACKAGE_ROOT / followup.FULLSTAT_DELAYED_PLAN
DELAYED_AGGREGATE = PACKAGE_ROOT / followup.FULLSTAT_DELAYED_AGGREGATE
GUARD_LOG = followup.GUARD_EVENT_LOG
RESOURCE_LOG = followup.RESOURCE_EVENT_LOG
GUARD_SESSION_WAL = followup.GUARD_SESSION_WAL
TOPUP_RUN_ROOT = PLAN1_RUN_ROOT.parent / "sf3_fullstat_prompt_buildup_topup_v1"
DELAYED_RUN_ROOT = PLAN1_RUN_ROOT.parent / "sf3_fullstat_delayed_v1"
TOPUP_PROFILE_ID = "SF3_FULLSTAT_PROMPT_BUILDUP_TOPUP_V1"
DELAYED_PROFILE_ID = "SF3_FULLSTAT_DELAYED_V1"
PLAN1_ZERO_REASON = "ZERO_A15__NO_DELAYED_TRANSPORT__FINITE_UPPER_LIMIT_ONLY"

PROFILE_ID = "SF3_FULLSTAT_RESOURCE_TIMELINE_V1"
PASS_STATUS = "PASS__SF3_FULLSTAT_RESOURCE_GUARD_TIMELINE_COMPLETE"
READY_STATUS = "READY__SF3_FULLSTAT_RESOURCE_GUARD_TIMELINE_AUTHORITIES_COMPLETE"
NOT_READY_STATUS = "NOT_READY__SF3_FULLSTAT_RESOURCE_GUARD_TIMELINE_AUTHORITIES_INCOMPLETE"
FAIL_STATUS = "FAIL__SF3_FULLSTAT_RESOURCE_GUARD_TIMELINE_CONTRACT"
EXPECTED_LABELS = followup.GUARDED_STEPS
EXPECTED_PHASES = followup.PHASE_BY_GUARDED_STEP
MEM_FLOOR = followup.MEM_FLOOR
SWAP_FLOOR = followup.SWAP_FLOOR
DISK_RESERVE = followup.DISK_RESERVE
MAX_SMALL_BYTES = 64 * 1024**2
SIM_SUFFIXES = (".sim", ".sim.gz", ".sim.bz2", ".sim.xz")
SAFE_JOB_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def norm(path: str | Path) -> str:
    return os.path.abspath(os.fspath(path))


def json_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def reject_sim(path: Path) -> None:
    if str(path).lower().endswith(SIM_SUFFIXES):
        raise RuntimeError(f"SIM payload path rejected before filesystem access: {path}")


def read_small(path: Path) -> bytes:
    reject_sim(path)
    with path.open("rb") as handle:
        raw = handle.read(MAX_SMALL_BYTES + 1)
    if not raw or len(raw) > MAX_SMALL_BYTES:
        raise RuntimeError(f"compact authority empty/oversized: {path} ({len(raw)})")
    return raw


def record(path: Path, raw: bytes) -> dict[str, Any]:
    return {"path": norm(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def parse_json(raw: bytes, path: Path) -> dict[str, Any]:
    value = json.loads(raw.decode("utf-8"), parse_constant=lambda token: (_ for _ in ()).throw(ValueError(f"non-finite JSON token {token}")))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON root is not an object: {path}")
    return value


def parse_jsonl(raw: bytes, path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise RuntimeError(f"JSONL row is not an object: {path}:{index}")
        rows.append(value)
    if not rows:
        raise RuntimeError(f"compact JSONL is empty: {path}")
    return rows


def parse_csv(raw: bytes, path: Path) -> list[dict[str, str]]:
    with io.StringIO(raw.decode("utf-8-sig"), newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise RuntimeError(f"CSV header missing: {path}")
        return list(reader)


def exact_int(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} is boolean")
    result = int(value)
    if isinstance(value, str) and value.strip() != str(result):
        raise ValueError(f"{label} is not an exact integer: {value!r}")
    return result


def finite_float(value: Any, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} is non-finite")
    return result


def parse_time(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} timestamp missing")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"{label} timestamp lacks offset")
    return parsed.astimezone(timezone.utc)


class Check:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.missing: list[str] = []
        self.pending: list[str] = []
        self.authorities: dict[str, dict[str, Any]] = {}

    def expect(self, condition: bool, message: str) -> None:
        if not condition:
            self.errors.append(message)

    def wait(self, condition: bool, message: str) -> None:
        if not condition:
            self.pending.append(message)

    def raw(self, label: str, path: Path) -> bytes | None:
        reject_sim(path)
        if not path.is_file():
            self.missing.append(f"{label}:{norm(path)}")
            return None
        try:
            raw = read_small(path)
            self.authorities[label] = record(path, raw)
            return raw
        except Exception as exc:
            self.errors.append(f"{label} invalid: {exc}")
            return None

    def json(self, label: str, path: Path) -> dict[str, Any] | None:
        raw = self.raw(label, path)
        if raw is None:
            return None
        try:
            return parse_json(raw, path)
        except Exception as exc:
            self.errors.append(f"{label} invalid: {exc}")
            return None

    def csv(self, label: str, path: Path) -> list[dict[str, str]] | None:
        raw = self.raw(label, path)
        if raw is None:
            return None
        try:
            return parse_csv(raw, path)
        except Exception as exc:
            self.errors.append(f"{label} invalid: {exc}")
            return None


def load_canonical_receipt(
    root: Path,
    relative_root: str,
    selected: dict[str, Any],
    job_id: str,
    authority_label: str,
    check: Check,
) -> dict[str, Any] | None:
    """Read one named compact receipt after exact path binding; never touch SIM."""

    if not SAFE_JOB_ID_RE.fullmatch(job_id):
        check.errors.append(f"{authority_label} unsafe canonical receipt job ID rejected: {job_id!r}")
        return None
    expected_path = root / relative_root / f"{job_id}.json"
    observed_path = selected.get("receipt_path")
    if not isinstance(observed_path, str) or norm(observed_path) != norm(expected_path):
        check.errors.append(f"{authority_label} canonical receipt path differs: {job_id}")
    raw = check.raw(f"{authority_label}_canonical_receipt_{job_id}", expected_path)
    if raw is None:
        return None
    if selected.get("receipt_sha256") != hashlib.sha256(raw).hexdigest():
        check.errors.append(f"{authority_label} canonical receipt digest differs: {job_id}")
    try:
        return parse_json(raw, expected_path)
    except Exception as exc:
        check.errors.append(f"{authority_label} canonical receipt invalid {job_id}: {exc}")
        return None


def validate_attempt_metadata(
    receipt: dict[str, Any], job_id: str, run_root: Path, check: Check
) -> None:
    try:
        attempt = exact_int(receipt.get("attempt"), f"{job_id} receipt attempt")
        expected_attempt = run_root / "jobs" / job_id / "attempts" / f"attempt{attempt:02d}"
        if (
            attempt <= 0
            or receipt.get("status") != "PASS"
            or receipt.get("errors") != []
            or exact_int(receipt.get("returncode"), f"{job_id} receipt returncode") != 0
            or norm(receipt.get("attempt_dir", "")) != norm(expected_attempt)
            or norm(receipt.get("sim_path", ""))
            != norm(expected_attempt / f"{job_id}.inc1.id1.sim.gz")
            or norm(receipt.get("log_path", "")) != norm(expected_attempt / f"{job_id}.log")
        ):
            check.errors.append(f"canonical receipt attempt metadata differs: {job_id}")
    except Exception as exc:
        check.errors.append(f"canonical receipt attempt metadata invalid {job_id}: {exc}")


def validate_plan1_background(
    payload: dict[str, Any] | None,
    plan_rows: list[dict[str, str]] | None,
    check: Check,
) -> list[str]:
    if payload is None or plan_rows is None:
        return []
    selected = payload.get("selected_receipts")
    if not isinstance(selected, list):
        check.errors.append("Plan-1 aggregate selected_receipts is not an array")
        return []
    try:
        plan = {str(row.get("job_id", "")): row for row in plan_rows}
        check.expect(len(plan_rows) == 30 and len(plan) == 30 and all(plan), "Plan-1 plan is not 30 unique jobs")
        check.expect(all(row.get("geometry") == "SF3" for row in plan_rows), "Plan-1 plan geometry differs from SF3")
        background_plan = {job_id: row for job_id, row in plan.items() if row.get("stage") == "background"}
        delayed_plan = {job_id: row for job_id, row in plan.items() if row.get("stage") == "delayed"}
        signal_plan = {job_id: row for job_id, row in plan.items() if row.get("stage") == "signal"}
        check.expect(len(background_plan) == 21 and len(delayed_plan) == 8 and len(signal_plan) == 1, "Plan-1 stage cardinalities are not 21+8+1")
        exclusions = payload.get("execution_exclusions")
        if not isinstance(exclusions, dict):
            raise RuntimeError("Plan-1 execution_exclusions is not an object")
        effective_ids = set(plan) - (set(exclusions) & set(plan))
        for job_id in set(exclusions) & set(plan):
            row = plan[job_id]
            check.expect(row.get("stage") == "delayed" and exclusions.get(job_id) == PLAN1_ZERO_REASON, f"Plan-1 in-plan exclusion is not canonical zero-A15 delayed: {job_id}")
        selected_ids: list[str] = []
        for row in selected:
            job_id = str(row.get("job_id", ""))
            expected = plan.get(job_id)
            if expected is None or job_id in selected_ids:
                check.errors.append(f"Plan-1 selected receipt identity unknown/duplicate: {job_id!r}")
                continue
            selected_ids.append(job_id)
            check.expect(
                row.get("stage") == expected.get("stage")
                and row.get("mode") == expected.get("mode")
                and row.get("family") == expected.get("family")
                and exact_int(row.get("events"), f"{job_id} aggregate events") == exact_int(expected.get("events"), f"{job_id} plan events")
                and exact_int(row.get("seed"), f"{job_id} aggregate seed") == exact_int(expected.get("seed"), f"{job_id} plan seed"),
                f"Plan-1 selected receipt metadata differs from plan: {job_id}",
            )
        effective_count = len(effective_ids)
        expected_status = f"PASS__ALL_{effective_count}_EFFECTIVE_SF3_ONLY_TRANSPORT_JOBS"
        background_ids = [job_id for job_id in selected_ids if job_id in background_plan]
        check.expect(payload.get("profile_id") == PLAN1_PROFILE_ID, "Plan-1 aggregate profile differs")
        check.expect(payload.get("status") == expected_status, "Plan-1 aggregate exact complete status differs")
        check.expect(payload.get("sim_digest_policy") == "NO_REOPEN_OR_REHASH__RECEIPT_PATH_SIZE_HEADER_ONLY", "Plan-1 aggregate SIM policy differs")
        check.expect(exact_int(payload.get("planned_jobs"), "Plan-1 planned jobs") == 30, "Plan-1 planned count differs")
        check.expect(exact_int(payload.get("effective_planned_jobs"), "Plan-1 effective jobs") == effective_count, "Plan-1 effective count differs")
        check.expect(exact_int(payload.get("validated_jobs"), "Plan-1 validated jobs") == effective_count, "Plan-1 validated count differs")
        check.expect(set(selected_ids) == effective_ids and len(selected_ids) == len(set(selected_ids)), "Plan-1 selected identities do not exactly close effective plan")
        check.expect(set(background_ids) == set(background_plan) and len(background_ids) == 21, "Plan-1 background receipt closure differs from exact plan IDs")
        check.expect(exact_int(payload.get("background_planned_jobs"), "Plan-1 background planned") == 21, "Plan-1 background planned count differs")
        check.expect(exact_int(payload.get("background_validated_jobs"), "Plan-1 background validated") == 21, "Plan-1 background validated count differs")
        return background_ids
    except Exception as exc:
        check.errors.append(f"Plan-1 aggregate/plan validation failed: {exc}")
        return []


def validate_topup(
    root: Path,
    plan_rows: list[dict[str, str]] | None,
    payload: dict[str, Any] | None,
    expected_run_root: Path,
    check: Check,
) -> list[str]:
    if plan_rows is None or payload is None:
        return []
    try:
        plan = {str(row["job_id"]): row for row in plan_rows}
        check.expect(len(plan_rows) == 28 and len(plan) == 28, "top-up plan is not 28 unique jobs")
        check.expect(sum(row.get("mode") == "instant" for row in plan_rows) == 15, "top-up instant jobs !=15")
        check.expect(sum(row.get("mode") == "buildup" for row in plan_rows) == 13, "top-up buildup jobs !=13")
        check.expect(all(row.get("stage") == "fullstat_topup_background" and row.get("geometry") == "SF3" for row in plan_rows), "top-up plan stage/geometry differs")
        check.expect(
            all(norm(row.get("run_root", "")) == norm(expected_run_root) for row in plan_rows),
            "top-up plan run_root differs from the fixed fresh namespace",
        )
        rows = payload.get("selected_receipts")
        if not isinstance(rows, list):
            raise RuntimeError("top-up aggregate selected_receipts is not an array")
        ids: list[str] = []
        for row in rows:
            job_id = str(row.get("job_id", ""))
            expected = plan.get(job_id)
            if expected is None or job_id in ids:
                check.errors.append(f"top-up receipt ID unknown/duplicate: {job_id!r}")
                continue
            ids.append(job_id)
            check.expect(row.get("registered_stage") == "fullstat_topup_background", f"top-up registered stage differs: {job_id}")
            check.expect(row.get("receipt_stage") == "background", f"top-up receipt stage differs: {job_id}")
            check.expect(row.get("geometry") == "SF3", f"top-up receipt geometry differs: {job_id}")
            check.expect(row.get("family") == expected.get("family") and row.get("mode") == expected.get("mode"), f"top-up family/mode differs: {job_id}")
            check.expect(exact_int(row.get("events"), f"{job_id} events") == exact_int(expected.get("events"), f"{job_id} plan events"), f"top-up events differ: {job_id}")
            check.expect(exact_int(row.get("seed"), f"{job_id} seed") == exact_int(expected.get("seed"), f"{job_id} plan seed"), f"top-up seed differs: {job_id}")
            receipt = load_canonical_receipt(
                root, followup.TOPUP_RECEIPT_ROOT, row, job_id, "topup", check
            )
            if receipt is not None:
                validate_attempt_metadata(receipt, job_id, expected_run_root, check)
                setup = expected.get("setup_path", "")
                header = receipt.get("sim_header") or {}
                dat = receipt.get("isotope_dat") or {}
                expected_attempt = expected_run_root / "jobs" / job_id / "attempts" / f"attempt{exact_int(receipt.get('attempt'), f'{job_id} receipt attempt'):02d}"
                check.expect(
                    receipt.get("profile_id") == TOPUP_PROFILE_ID
                    and receipt.get("job_id") == job_id
                    and receipt.get("stage") == "background"
                    and receipt.get("geometry") == "SF3"
                    and receipt.get("mode") == expected.get("mode")
                    and receipt.get("family") == expected.get("family")
                    and exact_int(receipt.get("events"), f"{job_id} receipt events") == exact_int(expected.get("events"), f"{job_id} plan events")
                    and exact_int(receipt.get("seed"), f"{job_id} receipt seed") == exact_int(expected.get("seed"), f"{job_id} plan seed")
                    and norm(receipt.get("setup_path", "")) == norm(setup)
                    and norm(header.get("geometry", "")) == norm(setup)
                    and exact_int(header.get("seed"), f"{job_id} header seed") == exact_int(expected.get("seed"), f"{job_id} plan seed")
                    and header.get("policy") == "HEADER_ONLY__NO_FULL_SIM_SCAN_OR_DIGEST"
                    and receipt.get("sim_digest_policy") == "OMITTED_BY_CONTRACT__PATH_SIZE_HEADER_RECEIPT_ONLY"
                    and norm(receipt.get("isotope_dat_path", "")) == norm(expected_attempt / f"{job_id}.dat.inc1.dat")
                    and finite_float(dat.get("TT_s"), f"{job_id} DAT TT") > 0.0
                    and exact_int(dat.get("RP_record_count"), f"{job_id} DAT RP") >= 0
                    and dat.get("terminal_EN") is True
                    and dat.get("errors") in ([], None),
                    f"top-up canonical compact receipt payload differs: {job_id}",
                )
                check.expect(
                    exact_int(row.get("artifact_bytes"), f"{job_id} aggregate artifact bytes") == exact_int(receipt.get("artifact_bytes"), f"{job_id} receipt artifact bytes")
                    and exact_int(row.get("peak_process_group_rss_bytes"), f"{job_id} aggregate peak") == exact_int(receipt.get("peak_process_group_rss_bytes"), f"{job_id} receipt peak"),
                    f"top-up aggregate resource fields differ from canonical receipt: {job_id}",
                )
        check.expect(payload.get("profile_id") == TOPUP_PROFILE_ID, "top-up aggregate profile differs")
        check.expect(payload.get("status") == "PASS__ALL_28_SF3_FULLSTAT_TOPUP_BACKGROUND_JOBS", "top-up aggregate status differs")
        check.expect(int(payload.get("planned_jobs", -1)) == 28 and int(payload.get("validated_jobs", -1)) == 28, "top-up aggregate counts differ")
        check.expect(set(ids) == set(plan), "top-up aggregate receipt identities differ from plan")
        check.expect(
            norm(payload.get("attempt_namespace", "")) == norm(expected_run_root / "jobs"),
            "top-up aggregate attempt namespace differs",
        )
        check.expect(payload.get("plan1_mutation") is False, "top-up aggregate mutates Plan-1")
        return ids
    except Exception as exc:
        check.errors.append(f"top-up authority validation failed: {exc}")
        return []


def validate_delayed(
    root: Path,
    activation: dict[str, Any] | None,
    plan_rows: list[dict[str, str]] | None,
    aggregate: dict[str, Any] | None,
    expected_run_root: Path,
    check: Check,
) -> tuple[list[str], list[str]]:
    if activation is None or plan_rows is None or aggregate is None:
        return [], []
    try:
        cards = activation.get("source_cards")
        if not isinstance(cards, list) or len(cards) != 8:
            raise RuntimeError("activation source-card registry is not eight")
        plan = {str(row.get("job_id", "")): row for row in plan_rows}
        check.expect(len(plan_rows) == 8 and len(plan) == 8, "full-stat delayed plan is not eight unique jobs")
        check.expect(
            {str(row.get("family", "")) for row in plan_rows} == set(followup.FAMILIES),
            "full-stat delayed plan family set differs from the exact eight-family authority",
        )
        check.expect(
            all(
                row.get("stage") == "fullstat_delayed"
                and row.get("geometry") == "SF3"
                and row.get("mode") == "delayed"
                for row in plan_rows
            ),
            "full-stat delayed plan stage/geometry/mode differs",
        )
        check.expect(
            all(norm(row.get("run_root", "")) == norm(expected_run_root) for row in plan_rows),
            "full-stat delayed plan run_root differs from the fixed fresh250k namespace",
        )
        check.expect(activation.get("status") == "PASS__SF3_FULLSTAT_ACTIVATION_VALIDATION", "full-stat activation validation status differs")
        positive: list[str] = []
        zero: list[str] = []
        card_ids: list[str] = []
        for card in cards:
            job_id = str(card.get("job_id", ""))
            card_ids.append(job_id)
            row = plan.get(job_id)
            if row is None:
                check.errors.append(f"activation job absent from delayed plan: {job_id}")
                continue
            disposition = card.get("execution_disposition")
            eligible = str(row.get("transport_eligible", "")).lower() == "true"
            check.expect(card.get("family") == row.get("family"), f"activation family differs from plan: {job_id}")
            check.expect(exact_int(card.get("seed"), f"{job_id} card seed") == exact_int(row.get("seed"), f"{job_id} plan seed"), f"activation seed differs: {job_id}")
            check.expect(exact_int(card.get("registered_events"), f"{job_id} registered") == 250_000 and exact_int(row.get("registered_events"), f"{job_id} plan registered") == 250_000, f"activation registered events differ: {job_id}")
            check.expect(exact_int(card.get("actual_transport_events"), f"{job_id} card actual") == exact_int(row.get("actual_transport_events"), f"{job_id} plan actual"), f"activation actual events differ: {job_id}")
            check.expect(disposition == row.get("execution_disposition"), f"activation disposition differs from plan: {job_id}")
            check.expect(norm(card.get("path", "")) == norm(row.get("source_path", "")), f"activation source-card path differs from plan: {job_id}")
            check.expect(
                isinstance(card.get("sha256"), str)
                and len(card.get("sha256")) == 64
                and all(character in "0123456789abcdef" for character in card.get("sha256")),
                f"activation source-card digest metadata malformed: {job_id}",
            )
            check.expect(exact_int(card.get("position_stride"), f"{job_id} position stride") == 5, f"activation source-card position stride differs: {job_id}")
            if disposition == "RUN_FRESH_250000":
                check.expect(exact_int(row.get("events"), f"{job_id} plan events") == 250_000 and exact_int(row.get("actual_transport_events"), f"{job_id} plan actual") == 250_000 and eligible, f"positive delayed plan is not fresh250k/eligible: {job_id}")
                check.expect(finite_float(card.get("transported_ground_activity_Bq"), f"{job_id} activity") > 0.0, f"positive delayed activity is nonpositive: {job_id}")
                check.expect(exact_int(card.get("original_blocks"), f"{job_id} original blocks") == 50_000 and exact_int(card.get("transport_blocks"), f"{job_id} transport blocks") == 10_000, f"positive delayed 50k/10k mixture differs: {job_id}")
                positive.append(job_id)
            elif disposition == "SKIP_ZERO_A15":
                check.expect(exact_int(row.get("events"), f"{job_id} zero events") == 0 and exact_int(row.get("actual_transport_events"), f"{job_id} zero actual") == 0 and not eligible, f"zero delayed plan event/eligibility contract differs: {job_id}")
                check.expect(finite_float(card.get("transported_ground_activity_Bq"), f"{job_id} zero activity") == 0.0, f"zero delayed central activity differs: {job_id}")
                check.expect(finite_float(card.get("transported_ground_A15_upper95_Bq_conservative"), f"{job_id} upper") > 0.0, f"zero delayed card lacks finite upper: {job_id}")
                check.expect(finite_float(card.get("transported_ground_rate_upper95_s-1"), f"{job_id} rate upper") > 0.0, f"zero delayed card lacks finite rate upper: {job_id}")
                check.expect(exact_int(card.get("original_blocks"), f"{job_id} zero original blocks") == 0 and exact_int(card.get("transport_blocks"), f"{job_id} zero transport blocks") == 0, f"zero delayed source has blocks: {job_id}")
                zero.append(job_id)
            else:
                check.errors.append(f"unknown full-stat delayed disposition: {job_id}/{disposition}")
        check.expect(
            len(card_ids) == len(set(card_ids)) and set(card_ids) == set(plan),
            "activation source-card identities do not exactly cover the delayed plan",
        )
        check.expect(len(positive) + len(zero) == 8, "full-stat delayed disposition count differs from eight")
        selected = aggregate.get("selected_receipts")
        if not isinstance(selected, list):
            raise RuntimeError("full-stat delayed selected_receipts is not an array")
        selected_ids = [str(row.get("job_id", "")) for row in selected]
        for row in selected:
            job_id = str(row.get("job_id", ""))
            expected = plan.get(job_id)
            if expected is None:
                check.errors.append(f"delayed aggregate receipt is outside plan: {job_id}")
                continue
            check.expect(
                row.get("family") == expected.get("family")
                and row.get("stage") == "fullstat_delayed"
                and int(row.get("registered_events", -1)) == 250_000
                and int(row.get("events", -1)) == 250_000
                and int(row.get("actual_transport_events", -1)) == 250_000
                and int(row.get("seed", -1)) == int(expected.get("seed", -2)),
                f"delayed aggregate receipt is not exact fresh250k plan binding: {job_id}",
            )
            check.expect(row.get("execution_disposition") == "RUN_FRESH_250000" and row.get("transport_eligible") is True, f"delayed receipt disposition differs: {job_id}")
            receipt = load_canonical_receipt(
                root, followup.FULLSTAT_DELAYED_RECEIPT_ROOT, row, job_id, "fresh250k_delayed", check
            )
            if receipt is not None:
                validate_attempt_metadata(receipt, job_id, expected_run_root, check)
                setup = expected.get("setup_path", "")
                header = receipt.get("sim_header") or {}
                check.expect(
                    receipt.get("profile_id") == DELAYED_PROFILE_ID
                    and receipt.get("job_id") == job_id
                    and receipt.get("stage") == "fullstat_delayed"
                    and receipt.get("geometry") == "SF3"
                    and receipt.get("mode") == "delayed"
                    and receipt.get("family") == expected.get("family")
                    and exact_int(receipt.get("registered_events"), f"{job_id} receipt registered") == 250_000
                    and exact_int(receipt.get("events"), f"{job_id} receipt events") == 250_000
                    and exact_int(receipt.get("actual_transport_events"), f"{job_id} receipt actual") == 250_000
                    and exact_int(receipt.get("seed"), f"{job_id} receipt seed") == exact_int(expected.get("seed"), f"{job_id} plan seed")
                    and norm(receipt.get("setup_path", "")) == norm(setup)
                    and receipt.get("source_status") == expected.get("source_status")
                    and receipt.get("execution_disposition") == "RUN_FRESH_250000"
                    and receipt.get("transport_eligible") is True
                    and receipt.get("seed_namespace") == DELAYED_PROFILE_ID
                    and receipt.get("plan1_83334_role") == "SCREENING_ONLY__DO_NOT_CONSUME_OR_MERGE"
                    and receipt.get("incremental_merge_allowed") is False
                    and norm(receipt.get("receipt_namespace", "")) == norm(root / followup.FULLSTAT_DELAYED_RECEIPT_ROOT)
                    and receipt.get("isotope_dat_path") is None
                    and norm(header.get("geometry", "")) == norm(setup)
                    and exact_int(header.get("seed"), f"{job_id} header seed") == exact_int(expected.get("seed"), f"{job_id} plan seed")
                    and header.get("policy") == "HEADER_ONLY__NO_FULL_SIM_SCAN_OR_DIGEST"
                    and receipt.get("sim_digest_policy") == "OMITTED_BY_CONTRACT__PATH_SIZE_HEADER_RECEIPT_ONLY",
                    f"fresh250k delayed canonical compact receipt payload differs: {job_id}",
                )
                check.expect(
                    exact_int(row.get("artifact_bytes"), f"{job_id} aggregate artifact bytes") == exact_int(receipt.get("artifact_bytes"), f"{job_id} receipt artifact bytes")
                    and exact_int(row.get("peak_process_group_rss_bytes"), f"{job_id} aggregate peak") == exact_int(receipt.get("peak_process_group_rss_bytes"), f"{job_id} receipt peak"),
                    f"fresh250k delayed aggregate resource fields differ from canonical receipt: {job_id}",
                )
        exclusions = aggregate.get("execution_exclusions") or {}
        check.expect(aggregate.get("profile_id") == DELAYED_PROFILE_ID, "full-stat delayed aggregate profile differs")
        check.expect(aggregate.get("status") == "PASS__SF3_FULLSTAT_DELAYED_FRESH250K_COMPLETE", "full-stat delayed aggregate status differs")
        check.expect(exact_int(aggregate.get("registered_families"), "delayed registered families") == 8, "full-stat delayed registered family count differs")
        check.expect(exact_int(aggregate.get("planned_transport_jobs"), "delayed planned jobs") == len(positive) and exact_int(aggregate.get("validated_transport_jobs"), "delayed validated jobs") == len(positive), "full-stat delayed positive job counts differ")
        check.expect(exact_int(aggregate.get("fresh_triggers_per_positive_family"), "delayed fresh triggers") == 250_000, "full-stat delayed fresh trigger count differs")
        check.expect(set(selected_ids) == set(positive) and len(selected_ids) == len(set(selected_ids)), "full-stat delayed positive receipt identities differ")
        check.expect(set(exclusions) == set(zero) and all(exclusions.get(job_id) == followup.ZERO_REASON for job_id in zero), "full-stat delayed zero exclusions differ")
        check.expect(norm(aggregate.get("run_root", "")) == norm(expected_run_root), "full-stat delayed aggregate run_root differs")
        check.expect(aggregate.get("plan1_83334_read") is False and aggregate.get("plan1_83334_pooled") is False and aggregate.get("incremental_merge_used") is False, "Plan-1 delayed 83334 entered full-stat delayed")
        return positive, zero
    except Exception as exc:
        check.errors.append(f"full-stat delayed validation failed: {exc}")
        return [], []


def validate_transport_metrics(
    label: str,
    raw: bytes | None,
    expected_ids: Sequence[str],
    selected_receipts: Sequence[dict[str, Any]],
    run_root: Path,
    check: Check,
) -> dict[str, Any]:
    """Bind the runner's compact per-attempt ledger to canonical receipts.

    Failed finalized attempts may precede a successful retry.  There must be
    exactly one PASS ledger row for every canonical receipt, no PASS for any
    other identity, and every finalized attempt must retain the dynamic 8 GiB
    disk reserve.  The ledger never requires opening an artifact path.
    """

    expected = set(expected_ids)
    receipt_by_id = {
        str(row.get("job_id", "")): row
        for row in selected_receipts
        if isinstance(row, dict)
    }
    summary: dict[str, Any] = {
        "namespace": norm(run_root),
        "resource_metrics_path": norm(run_root / "resource_metrics.jsonl"),
        "expected_successful_jobs": len(expected),
        "successful_jobs": [],
        "failed_finalized_attempts": 0,
        "total_finalized_attempts": 0,
        "min_free_bytes": None,
        "dynamic_disk_reserve_bytes": DISK_RESERVE,
        "all_finalized_attempts_reserve_pass": False,
        "all_canonical_receipts_have_exactly_one_pass_metric": False,
    }
    if raw is None:
        return summary
    try:
        rows = parse_jsonl(raw, run_root / "resource_metrics.jsonl")
        seen_attempts: set[tuple[str, int]] = set()
        pass_by_id: dict[str, dict[str, Any]] = {}
        attempts_by_id: dict[str, list[tuple[int, str]]] = {job_id: [] for job_id in expected}
        free_values: list[int] = []
        failed = 0
        for index, row in enumerate(rows, 1):
            job_id = str(row.get("job_id", ""))
            if job_id not in expected:
                raise ValueError(f"unknown/non-transport job ID at row {index}: {job_id!r}")
            attempt = exact_int(row.get("attempt"), f"{label} row {index} attempt")
            if attempt <= 0 or (job_id, attempt) in seen_attempts:
                raise ValueError(f"nonpositive/duplicate attempt identity: {job_id}/attempt{attempt}")
            seen_attempts.add((job_id, attempt))
            status = row.get("status")
            if status not in ("PASS", "FAIL"):
                raise ValueError(f"unknown finalized attempt status: {job_id}/{status!r}")
            attempts_by_id[job_id].append((attempt, status))
            parse_time(row.get("at"), f"{label} row {index}")
            wall_s = finite_float(row.get("wall_s"), f"{label} row {index} wall_s")
            peak_rss = exact_int(row.get("peak_rss"), f"{label} row {index} peak_rss")
            artifact_bytes = exact_int(row.get("artifact_bytes"), f"{label} row {index} artifact_bytes")
            free_bytes = exact_int(row.get("free_bytes"), f"{label} row {index} free_bytes")
            if wall_s < 0.0 or peak_rss < 0 or artifact_bytes < 0:
                raise ValueError(f"negative finalized attempt metric: {job_id}/attempt{attempt}")
            if free_bytes < DISK_RESERVE:
                raise ValueError(f"dynamic 8 GiB reserve breached: {job_id}/attempt{attempt}/{free_bytes}")
            free_values.append(free_bytes)
            if status == "FAIL":
                failed += 1
                continue
            if job_id in pass_by_id:
                raise ValueError(f"duplicate PASS metric for canonical job: {job_id}")
            receipt = receipt_by_id.get(job_id)
            if receipt is None:
                raise ValueError(f"PASS metric lacks selected canonical receipt: {job_id}")
            if peak_rss != exact_int(receipt.get("peak_process_group_rss_bytes"), f"{job_id} receipt peak"):
                raise ValueError(f"PASS peak RSS differs from canonical receipt: {job_id}")
            if artifact_bytes != exact_int(receipt.get("artifact_bytes"), f"{job_id} receipt artifact bytes"):
                raise ValueError(f"PASS artifact bytes differ from canonical receipt: {job_id}")
            pass_by_id[job_id] = {
                "job_id": job_id,
                "attempt": attempt,
                "at": row.get("at"),
                "wall_s": wall_s,
                "peak_rss_bytes": peak_rss,
                "artifact_bytes": artifact_bytes,
                "free_bytes": free_bytes,
            }
        if set(receipt_by_id) != expected:
            raise ValueError("selected canonical receipt identities differ from expected metric scope")
        if set(pass_by_id) != expected:
            missing = sorted(expected - set(pass_by_id))
            raise ValueError(f"canonical jobs lacking exactly one PASS metric: {missing}")
        for job_id, attempts in attempts_by_id.items():
            if [attempt for attempt, _ in attempts] != sorted(attempt for attempt, _ in attempts):
                raise ValueError(f"per-job finalized attempts are not append-ordered: {job_id}")
            if not attempts or attempts[-1][1] != "PASS":
                raise ValueError(f"canonical PASS is not the terminal finalized attempt: {job_id}")
        summary.update({
            "successful_jobs": [pass_by_id[job_id] for job_id in sorted(pass_by_id)],
            "failed_finalized_attempts": failed,
            "total_finalized_attempts": len(rows),
            "min_free_bytes": min(free_values),
            "all_finalized_attempts_reserve_pass": True,
            "all_canonical_receipts_have_exactly_one_pass_metric": True,
        })
    except Exception as exc:
        check.errors.append(f"{label} resource_metrics validation failed: {exc}")
    return summary


def parse_guard_slice(raw: bytes, start: int, end: int, label: str) -> list[dict[str, Any]]:
    if not (0 <= start < end <= len(raw)):
        raise ValueError(f"guard byte range invalid for {label}: {start}:{end}/{len(raw)}")
    if start > 0 and raw[start - 1:start] != b"\n":
        raise ValueError(f"guard byte range does not start at a JSONL boundary: {label}")
    selected = raw[start:end]
    if not selected.endswith(b"\n"):
        raise ValueError(f"guard byte range does not end at a JSONL boundary: {label}")
    return parse_jsonl(selected, Path(f"guard-slice:{label}"))


def validate_entire_guard_log(guard_raw: bytes, root: Path, check: Check) -> dict[str, Any]:
    """Audit every session, including clean failed/retried controller attempts."""

    summary: dict[str, Any] = {
        "all_bytes_audited": False,
        "all_sessions_cleanly_closed": False,
        "session_count": 0,
        "sessions_by_label": {},
        "sessions": [],
    }
    try:
        lines = guard_raw.splitlines(keepends=True)
        if not lines or any(not line.endswith(b"\n") or not line.strip() for line in lines):
            raise ValueError("complete guard log has a blank or non-newline-closed row")
        rows = parse_jsonl(guard_raw, Path("fullstat-guard-complete-log"))
        if len(rows) != len(lines):
            raise ValueError("complete guard log byte-line accounting differs")
        sessions: list[dict[str, Any]] = []
        current: list[dict[str, Any]] = []
        current_start = 0
        byte_offset = 0
        for index, (event, line) in enumerate(zip(rows, lines), 1):
            if not current:
                current_start = byte_offset
            label = str(event.get("session_label", ""))
            if label not in EXPECTED_LABELS:
                raise ValueError(f"complete guard log row {index} has unknown label: {label!r}")
            if current and current[-1].get("decision_reasons") != ["guard_exit_restore_normal"] and label != current[0].get("session_label"):
                raise ValueError(f"complete guard log changes label before clean closure: row {index}")
            reasons = event.get("decision_reasons")
            if not isinstance(reasons, list) or any(not isinstance(reason, str) for reason in reasons):
                raise ValueError(f"complete guard log row {index} reasons malformed")
            if event.get("error") or any(reason.endswith("_hard_floor_breach") or reason == "guard_exit_restore_failed" for reason in reasons):
                raise ValueError(f"complete guard log row {index} records hard-floor/restore failure")
            if event.get("unit") != followup.DEFAULT_SERVICE_UNIT:
                raise ValueError(f"complete guard log row {index} service unit differs")
            quota = exact_int(event.get("quota_percent"), f"complete guard row {index} quota")
            observed = exact_int(event.get("observed_quota_percent"), f"complete guard row {index} observed quota")
            if quota not in (300, 400) or observed not in (300, 400):
                raise ValueError(f"complete guard log row {index} quota is outside exact 300/400")
            if not isinstance(event.get("quota_changed"), bool):
                raise ValueError(f"complete guard log row {index} quota_changed is not boolean")
            if current:
                prior_quota = exact_int(current[-1].get("quota_percent"), f"complete guard row {index - 1} quota")
                if event.get("quota_changed") is not (quota != prior_quota):
                    raise ValueError(f"complete guard log row {index} quota_changed disagrees with transition")
            event_time = parse_time(event.get("at"), f"complete guard row {index}")
            if current and event_time <= current[-1]["_parsed_at"]:
                raise ValueError(f"complete guard session timestamps do not increase: row {index}")
            event = dict(event)
            event["_parsed_at"] = event_time
            mem = exact_int(event.get("mem_available_bytes"), f"complete guard row {index} MemAvailable")
            swap = exact_int(event.get("swap_free_bytes"), f"complete guard row {index} SwapFree")
            disk = exact_int(event.get("disk_free_bytes"), f"complete guard row {index} DiskFree")
            if mem < MEM_FLOOR or swap < SWAP_FLOOR or disk < DISK_RESERVE:
                raise ValueError(f"complete guard log row {index} breaches a hard floor")
            if (
                exact_int(event.get("mem_floor_bytes"), f"complete guard row {index} mem floor") != MEM_FLOOR
                or exact_int(event.get("swap_floor_bytes"), f"complete guard row {index} swap floor") != SWAP_FLOOR
                or exact_int(event.get("disk_floor_bytes"), f"complete guard row {index} disk floor") != DISK_RESERVE
                or norm(event.get("disk_path", "")) != norm(root)
            ):
                raise ValueError(f"complete guard log row {index} resource floor/path constants differ")
            if isinstance(event.get("cgroup_pressure"), dict):
                if event.get("unit_state") not in ("active", "activating"):
                    raise ValueError(f"complete guard log row {index} sampled unit is not active")
            elif reasons != ["guard_exit_restore_normal"]:
                raise ValueError(f"complete guard log row {index} non-sampled event is not clean closure")
            current.append(event)
            byte_offset += len(line)
            if reasons == ["guard_exit_restore_normal"]:
                sampled = [row for row in current if isinstance(row.get("cgroup_pressure"), dict)]
                if not sampled or quota != 400:
                    raise ValueError(f"complete guard session lacks sample/final restore400: {label}")
                sequence: list[int] = []
                for row in current:
                    value = exact_int(row.get("quota_percent"), f"complete guard session {label} quota")
                    if not sequence or sequence[-1] != value:
                        sequence.append(value)
                sessions.append({
                    "session_label": label,
                    "sample_count": len(sampled),
                    "quota_percent_sequence": sequence,
                    "closure": "GUARD_EXIT_RESTORE_NORMAL",
                    "guard_log_start_byte": current_start,
                    "guard_log_end_byte": byte_offset,
                    "completion_mem_available_bytes": mem,
                    "completion_swap_free_bytes": swap,
                    "completion_disk_free_bytes": disk,
                    "started_at": current[0].get("at"),
                    "closed_at": current[-1].get("at"),
                })
                current = []
        if current:
            raise ValueError(f"complete guard log ends with an unclosed session: {current[0].get('session_label')}")
        by_label = {
            label: sum(session["session_label"] == label for session in sessions)
            for label in EXPECTED_LABELS
        }
        if any(count < 1 for count in by_label.values()):
            raise ValueError(f"complete guard log does not cover every heavy label: {by_label}")
        summary.update({
            "all_bytes_audited": True,
            "all_sessions_cleanly_closed": True,
            "session_count": len(sessions),
            "sessions_by_label": by_label,
            "sessions": sessions,
        })
    except Exception as exc:
        check.errors.append(f"complete guard event log invalid: {exc}")
    return summary


def validate_guard_session_wal(
    wal_rows: Sequence[dict[str, Any]],
    root: Path,
    manifest_sha: str,
    complete_guard_sessions: Sequence[dict[str, Any]],
    check: Check,
) -> tuple[dict[tuple[str, int], list[dict[str, Any]]], dict[str, Any]]:
    by_key: dict[tuple[str, int], list[dict[str, Any]]] = {}
    seen_rows: set[tuple[str, int, str]] = set()
    for index, row in enumerate(wal_rows, 1):
        try:
            label = str(row.get("session_label", ""))
            start = exact_int(row.get("guard_log_start_byte"), f"WAL row {index} guard start")
            at = str(row.get("at", ""))
            parse_time(at, f"WAL row {index}")
            identity = (label, start, at)
            if identity in seen_rows:
                raise ValueError(f"duplicate WAL row identity: {identity}")
            seen_rows.add(identity)
            if label not in EXPECTED_LABELS or start < 0:
                raise ValueError(f"unknown label/negative start: {label!r}/{start}")
            if (
                row.get("schema_version") != 1
                or row.get("status") != "STARTED__WRITE_AHEAD_BEFORE_GUARD_OR_STAGE"
                or row.get("service_unit") != followup.DEFAULT_SERVICE_UNIT
                or row.get("followup_manifest_sha256") != manifest_sha
                or row.get("completion_authority") != followup.EXPECTED_STEP_METADATA[label][2]
                or norm(row.get("disk_path", "")) != norm(root)
                or exact_int(row.get("dynamic_disk_reserve_bytes"), f"WAL row {index} disk reserve") != DISK_RESERVE
                or row.get("stage_started") is not False
                or row.get("SIM_opened_statted_discovered_or_hashed") is not False
            ):
                raise ValueError(f"WAL contract fields differ: {label}/{start}")
            by_key.setdefault((label, start), []).append(row)
        except Exception as exc:
            check.errors.append(f"guard session WAL row {index} invalid: {exc}")
    guard_keys = {
        (str(session.get("session_label", "")), int(session.get("guard_log_start_byte", -1)))
        for session in complete_guard_sessions
    }
    missing_keys = sorted(guard_keys - set(by_key))
    check.expect(not missing_keys, f"clean guard sessions lack write-ahead WAL starts: {missing_keys}")
    for session in complete_guard_sessions:
        key = (str(session["session_label"]), int(session["guard_log_start_byte"]))
        started = parse_time(session.get("started_at"), f"guard session {key} start")
        candidates = by_key.get(key, [])
        check.expect(
            bool(candidates) and all(parse_time(row.get("at"), f"WAL {key}") < started for row in candidates),
            f"guard session WAL is not durably earlier than its first event: {key}",
        )
    summary = {
        "rows": len(wal_rows),
        "guard_session_keys": len(guard_keys),
        "all_clean_guard_sessions_have_write_ahead_start": not missing_keys,
        "orphan_pre_guard_crash_rows": sum(
            len(rows) for key, rows in by_key.items() if key not in guard_keys
        ),
        "duplicate_key_rows_from_pre_guard_crash_allowed_only_when_timestamp_distinct": True,
    }
    return by_key, summary


def validate_guarded_completion_authorities(
    root: Path, check: Check
) -> dict[str, dict[str, Any]]:
    expected_status = {
        "transport_topup": "PASS__ALL_28_SF3_FULLSTAT_TOPUP_BACKGROUND_JOBS",
        "build_fullstat_prompt": "PASS__SF3_FULLSTAT_PROMPT_COMPLETE",
        "transport_fullstat_delayed": "PASS__SF3_FULLSTAT_DELAYED_FRESH250K_COMPLETE",
        "analyze_fullstat_delayed": "PASS__SF3_FULLSTAT_DELAYED_RAW_CATALOG_8_REGISTERED_SOURCE_CELLS_COMPLETE",
        "build_fullstat_common_response": "PASS__SF3_FULLSTAT_COMMON_RESPONSE_AND_REUSED_FULL_ENVELOPE_SIGNAL_COMPLETE",
    }
    result: dict[str, dict[str, Any]] = {}
    for label in EXPECTED_LABELS:
        relative = str(followup.EXPECTED_STEP_METADATA[label][2])
        authority_label = f"guarded_completion_{label}"
        payload = check.json(authority_label, root / relative)
        if payload is None:
            continue
        check.expect(payload.get("status") == expected_status[label], f"guarded completion authority status differs: {label}")
        authority_record = dict(check.authorities[authority_label])
        authority_record["status"] = payload.get("status")
        authority_record["relative_path"] = relative
        if label in {
            "build_fullstat_prompt",
            "analyze_fullstat_delayed",
            "build_fullstat_common_response",
        }:
            manifest_relative = str(Path(relative).parent / "manifest.json")
            manifest_label = f"guarded_completion_{label}_manifest"
            manifest = check.json(manifest_label, root / manifest_relative)
            if manifest is None:
                continue
            check.expect(manifest.get("status") == expected_status[label], f"guarded completion companion manifest status differs: {label}")
            authority_record["companion_manifest"] = {
                **check.authorities[manifest_label],
                "relative_path": manifest_relative,
                "status": manifest.get("status"),
            }
        result[label] = authority_record
    check.wait(
        set(result) == set(EXPECTED_LABELS),
        f"canonical guarded completion authorities are {len(result)}/{len(EXPECTED_LABELS)}",
    )
    return result


def validate_sessions(
    guard_raw: bytes,
    resource_rows: Sequence[dict[str, Any]],
    manifest_sha: str,
    wal_by_key: dict[tuple[str, int], list[dict[str, Any]]],
    completion_authorities: dict[str, dict[str, Any]],
    root: Path,
    check: Check,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_label: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(resource_rows, 1):
        label = str(row.get("session_label", ""))
        if label not in EXPECTED_LABELS or label in by_label:
            check.errors.append(f"resource completion label unknown/duplicate: {label!r}")
            continue
        by_label[label] = row
        try:
            start = exact_int(row.get("guard_log_start_byte"), f"{label} guard start")
            wal_candidates = wal_by_key.get((label, start), [])
            matching_wal = [
                wal for wal in wal_candidates
                if wal.get("at") == row.get("guard_session_wal_started_at")
            ]
            check.expect(len(matching_wal) == 1, f"resource completion lacks one exact WAL start binding: {label}")
            check.expect(row.get("schema_version") == 1 and row.get("status") == "PASS", f"resource completion row is not PASS: {label}")
            check.expect(row.get("phase") == EXPECTED_PHASES[label], f"resource completion phase differs: {label}")
            check.expect(row.get("service_unit") == followup.DEFAULT_SERVICE_UNIT, f"resource completion service differs: {label}")
            check.expect(exact_int(row.get("actual_workers"), f"{label} workers") == 4, f"resource completion workers differ: {label}")
            check.expect(exact_int(row.get("configured_cpu_budget_max"), f"{label} max budget") == 6, f"resource completion max budget differs: {label}")
            check.expect(exact_int(row.get("quota_percent"), f"{label} terminal quota") == 400, f"resource completion terminal quota differs: {label}")
            check.expect(row.get("quota_percent_is_worker_count") is False, f"resource completion conflates quota/workers: {label}")
            check.expect(exact_int(row.get("mem_floor_bytes"), f"{label} mem floor") == MEM_FLOOR, f"resource completion mem floor differs: {label}")
            check.expect(exact_int(row.get("swap_floor_bytes"), f"{label} swap floor") == SWAP_FLOOR, f"resource completion swap floor differs: {label}")
            check.expect(exact_int(row.get("dynamic_disk_reserve_bytes"), f"{label} disk reserve") == DISK_RESERVE, f"resource completion disk reserve differs: {label}")
            check.expect(exact_int(row.get("mem_available_bytes"), f"{label} mem") >= MEM_FLOOR, f"resource completion mem floor failed: {label}")
            check.expect(exact_int(row.get("swap_free_bytes"), f"{label} swap") >= SWAP_FLOOR, f"resource completion swap floor failed: {label}")
            check.expect(exact_int(row.get("disk_free_after_projection_bytes"), f"{label} disk") >= DISK_RESERVE, f"resource completion disk reserve failed: {label}")
            normal = (
                type(row.get("stage_returncode")) is int
                and row.get("stage_returncode") == 0
                and row.get("completion_authority_inferred_success") is False
                and row.get("recovered_after_controller_crash") is False
            )
            recovered = (
                row.get("stage_returncode") is None
                and row.get("completion_authority_inferred_success") is True
                and row.get("recovered_after_controller_crash") is True
            )
            check.expect(normal is not recovered and (normal or recovered), f"resource completion normal/recovery XOR differs: {label}")
            check.expect(row.get("followup_manifest_sha256") == manifest_sha, f"resource completion manifest binding differs: {label}")
            check.expect(row.get("SIM_opened_statted_discovered_or_hashed_by_controller") is False, f"resource completion SIM safety marker differs: {label}")
            check.expect(label in completion_authorities, f"resource completion lacks independently validated canonical authority: {label}")
        except Exception as exc:
            check.errors.append(f"resource completion row {index} invalid: {exc}")
    check.wait(set(by_label) == set(EXPECTED_LABELS), f"guarded resource completion sessions are {len(by_label)}/{len(EXPECTED_LABELS)}")
    sessions: list[dict[str, Any]] = []
    timeline: list[dict[str, Any]] = []
    prior_end = -1
    for label in EXPECTED_LABELS:
        row = by_label.get(label)
        if row is None:
            continue
        try:
            start = exact_int(row.get("guard_log_start_byte"), f"{label} guard start")
            end = exact_int(row.get("guard_log_end_byte"), f"{label} guard end")
            if start < prior_end:
                raise ValueError(f"guard byte ranges overlap/out-of-order at {label}")
            prior_end = end
            events = parse_guard_slice(guard_raw, start, end, label)
            if any(event.get("session_label") != label for event in events):
                raise ValueError(f"guard slice contains another session label: {label}")
            sampled: list[dict[str, Any]] = []
            quota_sequence: list[int] = []
            event_times: list[datetime] = []
            for event_index, event in enumerate(events, 1):
                reasons = event.get("decision_reasons")
                if not isinstance(reasons, list) or any(not isinstance(reason, str) for reason in reasons):
                    raise ValueError(f"guard reasons malformed: {label}/{event_index}")
                if event.get("error") or any(reason.endswith("_hard_floor_breach") or reason == "guard_exit_restore_failed" for reason in reasons):
                    raise ValueError(f"guard session records hard-floor/restore failure: {label}/{reasons}")
                quota = exact_int(event.get("quota_percent"), f"{label} quota")
                if quota not in (300, 400):
                    raise ValueError(f"guard quota outside exact 300/400: {label}/{quota}")
                observed_quota = exact_int(event.get("observed_quota_percent"), f"{label} observed quota")
                if observed_quota not in (300, 400):
                    raise ValueError(f"guard observed quota outside exact 300/400: {label}/{observed_quota}")
                quota_sequence.append(quota)
                event_times.append(parse_time(event.get("at"), f"{label} event {event_index}"))
                if event.get("unit") != followup.DEFAULT_SERVICE_UNIT:
                    raise ValueError(f"guard unit differs: {label}/{event.get('unit')}")
                if not isinstance(event.get("quota_changed"), bool):
                    raise ValueError(f"guard quota_changed is not boolean: {label}/{event_index}")
                if event_index > 1 and event.get("quota_changed") is not (quota != quota_sequence[-2]):
                    raise ValueError(f"guard quota_changed disagrees with transition: {label}/{event_index}")
                if isinstance(event.get("cgroup_pressure"), dict):
                    mem = exact_int(event.get("mem_available_bytes"), f"{label} MemAvailable")
                    swap = exact_int(event.get("swap_free_bytes"), f"{label} SwapFree")
                    disk = exact_int(event.get("disk_free_bytes"), f"{label} DiskFree")
                    if mem < MEM_FLOOR or swap < SWAP_FLOOR or disk < DISK_RESERVE:
                        raise ValueError(f"guard sampled hard floor failed: {label}")
                    if exact_int(event.get("mem_floor_bytes"), f"{label} sampled mem floor") != MEM_FLOOR or exact_int(event.get("swap_floor_bytes"), f"{label} sampled swap floor") != SWAP_FLOOR or exact_int(event.get("disk_floor_bytes"), f"{label} sampled disk floor") != DISK_RESERVE or norm(event.get("disk_path", "")) != norm(root):
                        raise ValueError(f"guard sampled floor constants differ: {label}")
                    if event.get("unit_state") not in ("active", "activating"):
                        raise ValueError(f"guard sampled unit is not active: {label}")
                    sampled.append(event)
                    timeline.append({
                        "at": event.get("at"),
                        "phase": EXPECTED_PHASES[label],
                        "session_label": label,
                        "actual_workers": 4,
                        "quota_percent": quota,
                        "quota_percent_is_worker_count": False,
                        "mem_available_bytes": mem,
                        "swap_free_bytes": swap,
                        "disk_free_after_projection_bytes": disk,
                        "decision_reasons": reasons,
                    })
                elif reasons != ["guard_exit_restore_normal"]:
                    raise ValueError(f"non-sampled guard event is not the exact clean closure: {label}/{event_index}")
            if not sampled:
                raise ValueError(f"guard session has no sampled resource event: {label}")
            if any(event_times[index] <= event_times[index - 1] for index in range(1, len(event_times))):
                raise ValueError(f"guard timestamps are not strictly increasing: {label}")
            if parse_time(row.get("at"), f"{label} completion") <= event_times[-1]:
                raise ValueError(f"resource completion precedes guard closure: {label}")
            terminal = events[-1]
            terminal_reasons = terminal.get("decision_reasons") or []
            closure_indexes = [
                index for index, event in enumerate(events)
                if event.get("decision_reasons") == ["guard_exit_restore_normal"]
            ]
            if closure_indexes != [len(events) - 1]:
                raise ValueError(f"guard session lacks exactly one final clean closure: {label}/{closure_indexes}")
            if terminal_reasons != ["guard_exit_restore_normal"] or exact_int(terminal.get("quota_percent"), f"{label} terminal quota") != 400:
                raise ValueError(f"guard session does not close restored at 400: {label}")
            terminal_mem = exact_int(terminal.get("mem_available_bytes"), f"{label} terminal mem")
            terminal_swap = exact_int(terminal.get("swap_free_bytes"), f"{label} terminal swap")
            terminal_disk = exact_int(terminal.get("disk_free_bytes"), f"{label} terminal disk")
            if (
                terminal_mem < MEM_FLOOR
                or terminal_swap < SWAP_FLOOR
                or terminal_disk < DISK_RESERVE
                or exact_int(terminal.get("mem_floor_bytes"), f"{label} terminal mem floor") != MEM_FLOOR
                or exact_int(terminal.get("swap_floor_bytes"), f"{label} terminal swap floor") != SWAP_FLOOR
                or exact_int(terminal.get("disk_floor_bytes"), f"{label} terminal disk floor") != DISK_RESERVE
                or norm(terminal.get("disk_path", "")) != norm(root)
            ):
                raise ValueError(f"guard terminal resource snapshot differs: {label}")
            if (
                exact_int(row.get("mem_available_bytes"), f"{label} row mem") != terminal_mem
                or exact_int(row.get("swap_free_bytes"), f"{label} row swap") != terminal_swap
                or exact_int(row.get("disk_free_after_projection_bytes"), f"{label} row disk") != terminal_disk
            ):
                raise ValueError(f"resource completion row does not use original guard closure snapshot: {label}")
            nested = row.get("guard_session")
            if not isinstance(nested, dict) or (
                nested.get("session_label") != label
                or exact_int(nested.get("samples"), f"{label} nested samples") != len(sampled)
                or nested.get("closure") != "guard_exit_restore_normal"
                or exact_int(nested.get("restored_quota_percent"), f"{label} nested quota") != 400
                or exact_int(nested.get("hard_floor_breaches"), f"{label} nested breaches") != 0
                or exact_int(nested.get("completion_mem_available_bytes"), f"{label} nested mem") != terminal_mem
                or exact_int(nested.get("completion_swap_free_bytes"), f"{label} nested swap") != terminal_swap
                or exact_int(nested.get("completion_disk_free_bytes"), f"{label} nested disk") != terminal_disk
            ):
                raise ValueError(f"resource completion nested guard summary differs: {label}")
            compressed: list[int] = []
            for value in quota_sequence:
                if not compressed or compressed[-1] != value:
                    compressed.append(value)
            sessions.append({
                "session_label": label,
                "phase": EXPECTED_PHASES[label],
                "actual_workers": 4,
                "guard_log_start_byte": start,
                "guard_log_end_byte": end,
                "sample_count": len(sampled),
                "quota_percent_sequence": compressed,
                "quota_values_allowed_exactly_300_or_400": True,
                "terminal_quota_percent": 400,
                "closure": "GUARD_EXIT_RESTORE_NORMAL",
                "hard_floor_breach_observed": False,
                "minimum_mem_available_bytes": min(exact_int(event["mem_available_bytes"], f"{label} mem") for event in sampled),
                "minimum_swap_free_bytes": min(exact_int(event["swap_free_bytes"], f"{label} swap") for event in sampled),
                "minimum_disk_free_bytes": min(exact_int(event["disk_free_bytes"], f"{label} disk") for event in sampled),
                "completion_mem_available_bytes": terminal_mem,
                "completion_swap_free_bytes": terminal_swap,
                "completion_disk_free_bytes": terminal_disk,
                "completion_record_mode": "RECOVERED_FROM_WAL_AND_ORIGINAL_GUARD_CLOSURE" if row.get("recovered_after_controller_crash") is True else "NORMAL_STAGE_RETURNCODE_ZERO",
                "guard_session_wal_started_at": row.get("guard_session_wal_started_at"),
                "canonical_completion_authority": completion_authorities.get(label),
                "manifest_sha256": manifest_sha,
            })
        except Exception as exc:
            check.errors.append(f"guard session invalid {label}: {exc}")
    return sessions, timeline


def evaluate(
    root: Path = PACKAGE_ROOT,
    output: Path | None = None,
    *,
    topup_run_root: Path = TOPUP_RUN_ROOT,
    delayed_run_root: Path = DELAYED_RUN_ROOT,
) -> dict[str, Any]:
    output = output or (root / "audit/sf3_fullstat_resource_timeline.json")
    check = Check()
    gate, gate_errors = followup.plan1_gate(root)
    if gate_errors:
        check.errors.extend(gate_errors)
    if gate is None:
        return {
            "schema_version": 1, "profile_id": PROFILE_ID, "status": NOT_READY_STATUS,
            "ready": False, "pass": False, "checked_at": utc_now(),
            "missing": [str(root / followup.PLAN1_FINAL)] if not (root / followup.PLAN1_FINAL).is_file() else [],
            "pending": ["Plan-1 stage07 central gate is not available"], "errors": check.errors,
            "SIM_opened_statted_discovered_or_hashed": False, "transport_launched_by_auditor": False,
        }
    if gate["topup_required"] is not True:
        return {
            "schema_version": 1, "profile_id": PROFILE_ID,
            "status": "NOT_APPLICABLE__SF3_FULLSTAT_STOPPED_BY_PLAN1_CENTRAL_GATE",
            "ready": False, "pass": False, "checked_at": utc_now(), "missing": [],
            "pending": ["central gate did not authorize full-stat"], "errors": check.errors,
            "SIM_opened_statted_discovered_or_hashed": False, "transport_launched_by_auditor": False,
        }

    manifest_path = root / "data/sf3_fullstat_followup_execution_manifest.json"
    manifest_raw = check.raw("fullstat_followup_manifest", manifest_path)
    manifest: dict[str, Any] | None = None
    manifest_sha = ""
    if manifest_raw is not None:
        try:
            manifest = followup.validate_manifest(parse_json(manifest_raw, manifest_path))
            manifest_sha = hashlib.sha256(manifest_raw).hexdigest()
        except Exception as exc:
            check.errors.append(f"fullstat followup manifest invalid: {exc}")
    if manifest is not None:
        guard_policy = (manifest.get("policies") or {}).get("pressure_guard") or {}
        check.expect(guard_policy.get("guarded_steps") == list(EXPECTED_LABELS), "followup manifest guarded-session registry differs")
        check.expect((manifest.get("policies") or {}).get("workers") == 4, "followup manifest workers differ from 4")

    plan1_plan_rows = check.csv("plan1_job_plan", root / "data/sf3_plan1_job_plan.csv")
    plan1 = check.json("plan1_aggregate", root / "audit/sf3_plan1_transport_receipts.json")
    plan1_ids = validate_plan1_background(plan1, plan1_plan_rows, check)
    topup_plan_rows = check.csv("topup_plan", root / followup.TOPUP_PLAN)
    topup = check.json("topup_aggregate", root / followup.TOPUP_AGGREGATE)
    topup_ids = validate_topup(root, topup_plan_rows, topup, topup_run_root, check)
    activation = check.json("fullstat_activation_validation", root / followup.FULLSTAT_ACTIVATION_VALIDATION)
    delayed_plan_rows = check.csv("fullstat_delayed_plan", root / followup.FULLSTAT_DELAYED_PLAN)
    delayed = check.json("fullstat_delayed_aggregate", root / followup.FULLSTAT_DELAYED_AGGREGATE)
    positive_ids, zero_ids = validate_delayed(
        root, activation, delayed_plan_rows, delayed, delayed_run_root, check
    )
    check.expect(len(set(plan1_ids + topup_ids + positive_ids)) == len(plan1_ids) + len(topup_ids) + len(positive_ids), "transport receipt identities overlap across namespaces")

    topup_metrics: dict[str, Any] = {
        "namespace": norm(topup_run_root),
        "expected_successful_jobs": len(topup_ids),
    }
    if topup_plan_rows is not None and topup is not None:
        topup_metrics_raw = check.raw(
            "fullstat_topup_transport_resource_metrics",
            topup_run_root / "resource_metrics.jsonl",
        )
        selected_topup = topup.get("selected_receipts")
        topup_metrics = validate_transport_metrics(
            "full-stat top-up transport",
            topup_metrics_raw,
            topup_ids,
            selected_topup if isinstance(selected_topup, list) else [],
            topup_run_root,
            check,
        )
    delayed_metrics: dict[str, Any] = {
        "namespace": norm(delayed_run_root),
        "expected_successful_jobs": len(positive_ids),
        "successful_jobs": [],
        "failed_finalized_attempts": 0,
        "total_finalized_attempts": 0,
        "min_free_bytes": None,
        "dynamic_disk_reserve_bytes": DISK_RESERVE,
        "all_finalized_attempts_reserve_pass": not positive_ids,
        "all_canonical_receipts_have_exactly_one_pass_metric": not positive_ids,
        "zero_positive_transport_disposition": not positive_ids and bool(zero_ids),
    }
    if positive_ids and delayed_plan_rows is not None and delayed is not None:
        delayed_metrics_raw = check.raw(
            "fullstat_fresh250k_delayed_transport_resource_metrics",
            delayed_run_root / "resource_metrics.jsonl",
        )
        selected_delayed = delayed.get("selected_receipts")
        delayed_metrics = validate_transport_metrics(
            "full-stat fresh250k delayed transport",
            delayed_metrics_raw,
            positive_ids,
            selected_delayed if isinstance(selected_delayed, list) else [],
            delayed_run_root,
            check,
        )

    completion_authorities = validate_guarded_completion_authorities(root, check)

    guard_raw = check.raw("fullstat_guard_event_log", root / "audit/sf3_fullstat_followup_pressure_guard.jsonl")
    wal_raw = check.raw("fullstat_guard_session_wal", root / "audit/sf3_fullstat_followup_guard_session_wal.jsonl")
    resource_raw = check.raw("fullstat_resource_completion_log", root / "audit/sf3_fullstat_followup_resource_events.jsonl")
    wal_rows: list[dict[str, Any]] = []
    if wal_raw is not None:
        try:
            wal_rows = parse_jsonl(wal_raw, root / "audit/sf3_fullstat_followup_guard_session_wal.jsonl")
        except Exception as exc:
            check.errors.append(f"guard session WAL invalid: {exc}")
    resource_rows: list[dict[str, Any]] = []
    if resource_raw is not None:
        try:
            resource_rows = parse_jsonl(resource_raw, root / "audit/sf3_fullstat_followup_resource_events.jsonl")
        except Exception as exc:
            check.errors.append(f"resource completion log invalid: {exc}")
    sessions: list[dict[str, Any]] = []
    timeline: list[dict[str, Any]] = []
    complete_guard_log_audit: dict[str, Any] = {
        "all_bytes_audited": False,
        "all_sessions_cleanly_closed": False,
        "session_count": 0,
        "sessions_by_label": {},
        "sessions": [],
    }
    wal_by_key: dict[tuple[str, int], list[dict[str, Any]]] = {}
    wal_audit: dict[str, Any] = {
        "rows": 0,
        "guard_session_keys": 0,
        "all_clean_guard_sessions_have_write_ahead_start": False,
        "orphan_pre_guard_crash_rows": 0,
    }
    if guard_raw is not None:
        complete_guard_log_audit = validate_entire_guard_log(guard_raw, root, check)
    if wal_rows and manifest_sha:
        wal_by_key, wal_audit = validate_guard_session_wal(
            wal_rows,
            root,
            manifest_sha,
            complete_guard_log_audit.get("sessions") or [],
            check,
        )
    if guard_raw is not None and resource_rows and manifest_sha and wal_by_key:
        sessions, timeline = validate_sessions(
            guard_raw,
            resource_rows,
            manifest_sha,
            wal_by_key,
            completion_authorities,
            root,
            check,
        )

    check.wait(len(plan1_ids) == 21, f"Plan-1 background receipts are {len(plan1_ids)}/21")
    check.wait(len(topup_ids) == 28, f"top-up background receipts are {len(topup_ids)}/28")
    check.wait(bool(positive_ids) or bool(zero_ids), "full-stat delayed dispositions are unavailable")
    check.wait(
        topup_metrics.get("all_canonical_receipts_have_exactly_one_pass_metric") is True,
        "top-up per-job resource metrics are not closed",
    )
    check.wait(
        delayed_metrics.get("all_canonical_receipts_have_exactly_one_pass_metric") is True,
        "fresh250k delayed per-job resource metrics are not closed",
    )
    check.wait(len(sessions) == len(EXPECTED_LABELS), f"closed guarded sessions are {len(sessions)}/{len(EXPECTED_LABELS)}")
    check.wait(bool(timeline), "full-stat resource timeline has no sampled rows")
    check.wait(
        complete_guard_log_audit.get("all_sessions_cleanly_closed") is True,
        "complete full-stat guard event log is not cleanly closed",
    )
    check.wait(
        wal_audit.get("all_clean_guard_sessions_have_write_ahead_start") is True,
        "full-stat guard sessions are not all bound to durable WAL starts",
    )

    ready = not check.errors and not check.missing and not check.pending
    status = READY_STATUS if ready else FAIL_STATUS if check.errors else NOT_READY_STATUS
    sample_mem_values = [int(row["mem_available_bytes"]) for row in timeline]
    sample_swap_values = [int(row["swap_free_bytes"]) for row in timeline]
    sample_disk_values = [int(row["disk_free_after_projection_bytes"]) for row in timeline]
    closure_mem_values = [int(row["completion_mem_available_bytes"]) for row in sessions]
    closure_swap_values = [int(row["completion_swap_free_bytes"]) for row in sessions]
    closure_disk_values = [int(row["completion_disk_free_bytes"]) for row in sessions]
    mem_values = sample_mem_values + closure_mem_values
    swap_values = sample_swap_values + closure_swap_values
    disk_values = sample_disk_values + closure_disk_values
    transport_disk_values = [
        int(value)
        for value in (topup_metrics.get("min_free_bytes"), delayed_metrics.get("min_free_bytes"))
        if value is not None
    ]
    quota_values = sorted({int(row["quota_percent"]) for row in timeline})
    observed_exact_label_phase = {
        row["session_label"]: [row["phase"]]
        for row in sessions
    }
    payload = {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "status": status,
        "ready": ready,
        "pass": ready,
        "checked_at": utc_now(),
        "scope": "SF3_FULLSTAT_49_BACKGROUND_FRESH250K_DELAYED_AND_FIVE_GUARDED_HEAVY_STEPS",
        "configured_cpu_budget_max": 6,
        "adaptive_workers_min": 4,
        "adaptive_workers_max": 6,
        "production_controller_workers": 4,
        "mem_available_floor_bytes": MEM_FLOOR,
        "swap_free_floor_bytes": SWAP_FLOOR,
        "dynamic_disk_reserve_bytes": DISK_RESERVE,
        "quota_percent_is_worker_count": False,
        "quota_transition_percent": [400, 300, 400],
        "quota_transition_field_semantics": "NORMAL_THROTTLE_RESTORE_POLICY__300_IS_CONDITIONAL_AND_NEVER_A_WORKER_OR_STATISTICS_COUNT",
        "quota_percent_allowed_values": [300, 400],
        "quota_percent_observed": quota_values,
        "safe_all_400_quota_sessions_are_pass_eligible": True,
        "artificial_throttle_required": False,
        "job_scope": {
            "plan1_background_jobs": len(plan1_ids),
            "topup_background_jobs": len(topup_ids),
            "fullstat_background_jobs": len(plan1_ids) + len(topup_ids),
            "delayed_registered_families": len(positive_ids) + len(zero_ids),
            "delayed_positive_transport_jobs": len(positive_ids),
            "delayed_zero_skips": len(zero_ids),
            "total_transport_jobs": len(plan1_ids) + len(topup_ids) + len(positive_ids),
            "Plan1_83334_read_or_pooled": False,
        },
        "transport_receipt_ids": {
            "plan1_background": sorted(plan1_ids),
            "topup_background": sorted(topup_ids),
            "fresh250k_delayed": sorted(positive_ids),
            "zero_A15_skips": sorted(zero_ids),
        },
        "transport_completion_disk_metrics": {
            "topup_background": topup_metrics,
            "fresh250k_delayed": delayed_metrics,
            "all_new_transport_receipts_have_exactly_one_pass_metric": (
                topup_metrics.get("all_canonical_receipts_have_exactly_one_pass_metric") is True
                and delayed_metrics.get("all_canonical_receipts_have_exactly_one_pass_metric") is True
            ),
            "all_finalized_attempts_dynamic_8GiB_reserve_pass": (
                topup_metrics.get("all_finalized_attempts_reserve_pass") is True
                and delayed_metrics.get("all_finalized_attempts_reserve_pass") is True
            ),
            "min_free_bytes": min(transport_disk_values) if transport_disk_values else None,
        },
        "followup_manifest_binding": {
            "path": norm(manifest_path),
            "status": None if manifest is None else manifest.get("status"),
            "bytes": 0 if manifest_raw is None else len(manifest_raw),
            "sha256": manifest_sha,
            "guarded_steps": list(EXPECTED_LABELS),
        },
        "required_guarded_session_labels": list(EXPECTED_LABELS),
        "observed_guarded_session_labels": [row["session_label"] for row in sessions],
        "guarded_completion_authorities": completion_authorities,
        "all_guarded_completion_authorities_independently_validated": set(completion_authorities) == set(EXPECTED_LABELS),
        "exact_session_label_to_phase": dict(EXPECTED_PHASES),
        "required_exact_label_stage_coverage": dict(EXPECTED_PHASES),
        "observed_closed_exact_label_stage_coverage": observed_exact_label_phase,
        "all_required_exact_label_stage_bindings_pass": (
            observed_exact_label_phase
            == {label: [phase] for label, phase in EXPECTED_PHASES.items()}
        ),
        "guard_sessions": sessions,
        "guard_session_wal_audit": wal_audit,
        "normal_completion_records": sum(row.get("completion_record_mode") == "NORMAL_STAGE_RETURNCODE_ZERO" for row in sessions),
        "crash_recovered_completion_records": sum(row.get("completion_record_mode") == "RECOVERED_FROM_WAL_AND_ORIGINAL_GUARD_CLOSURE" for row in sessions),
        "normal_or_crash_recovery_record_XOR_pass": len(sessions) == len(EXPECTED_LABELS),
        "all_completion_resources_from_original_guard_closure_not_live_inference": len(sessions) == len(EXPECTED_LABELS),
        "complete_guard_event_log_audit": complete_guard_log_audit,
        "superseded_or_retried_clean_guard_sessions": max(
            0, int(complete_guard_log_audit.get("session_count", 0)) - len(EXPECTED_LABELS)
        ),
        "all_guard_sessions_closed": len(sessions) == len(EXPECTED_LABELS) and all(row["closure"] == "GUARD_EXIT_RESTORE_NORMAL" for row in sessions),
        "all_guard_sessions_exactly_one_clean_closure": len(sessions) == len(EXPECTED_LABELS),
        "all_guard_sessions_terminal_quota_400": len(sessions) == len(EXPECTED_LABELS) and all(row["terminal_quota_percent"] == 400 for row in sessions),
        "all_guard_samples_hard_floors_pass": len(sessions) == len(EXPECTED_LABELS) and all(row["hard_floor_breach_observed"] is False for row in sessions),
        "actual_workers_observed": sorted({int(row["actual_workers"]) for row in timeline}),
        "timeline_rows": len(timeline),
        "min_mem_available_bytes": min(mem_values) if mem_values else None,
        "min_swap_free_bytes": min(swap_values) if swap_values else None,
        "min_disk_free_after_projection_bytes": min(disk_values) if disk_values else None,
        "min_guard_sample_disk_free_bytes": min(sample_disk_values) if sample_disk_values else None,
        "min_guard_completion_disk_free_bytes": min(closure_disk_values) if closure_disk_values else None,
        "min_new_transport_completion_free_bytes": min(transport_disk_values) if transport_disk_values else None,
        "min_all_dynamic_disk_observations_bytes": (
            min(disk_values + transport_disk_values)
            if disk_values or transport_disk_values else None
        ),
        "timeline": timeline,
        "source_event_log": check.authorities.get("fullstat_guard_event_log", {"path": norm(root / "audit/sf3_fullstat_followup_pressure_guard.jsonl"), "bytes": 0, "sha256": ""}),
        "guard_session_wal": check.authorities.get("fullstat_guard_session_wal", {"path": norm(root / "audit/sf3_fullstat_followup_guard_session_wal.jsonl"), "bytes": 0, "sha256": ""}),
        "resource_completion_event_log": check.authorities.get("fullstat_resource_completion_log", {"path": norm(root / "audit/sf3_fullstat_followup_resource_events.jsonl"), "bytes": 0, "sha256": ""}),
        "input_authorities": check.authorities,
        "missing": sorted(set(check.missing)),
        "pending": sorted(set(check.pending)),
        "errors": check.errors,
        "SIM_opened_statted_discovered_or_hashed": False,
        "transport_launched_by_auditor": False,
        "systemd_or_service_action_performed_by_auditor": False,
    }
    return payload


def write_once(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.tmp-", delete=False) as handle:
            handle.write(json_text(payload))
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.link(temporary, path)
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def build() -> dict[str, Any]:
    checked = evaluate()
    if not checked.get("ready"):
        raise RuntimeError(json_text(checked))
    if OUTPUT.exists():
        raise FileExistsError(f"refusing to overwrite full-stat resource timeline: {OUTPUT}")
    payload = dict(checked)
    payload.update({"status": PASS_STATUS, "built_at": utc_now(), "write_contract": "ATOMIC_HARDLINK_PUBLICATION__WRITE_ONCE"})
    write_once(OUTPUT, payload)
    return payload


def fixture_json(root: Path, relative: str, payload: dict[str, Any]) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json_text(payload), encoding="utf-8")


def fixture_csv(root: Path, relative: str, rows: list[dict[str, Any]]) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def self_test() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="sf3-fullstat-resource-selftest-") as temporary:
        fixture_base = Path(temporary)
        root = fixture_base / "repo/engineering/geometry_optimization_20260815/49_sf3_plan1_transport_20260816"
        topup_run_root = fixture_base / "repo/runs/geometry_optimization_20260816/sf3_fullstat_prompt_buildup_topup_v1"
        delayed_run_root = fixture_base / "repo/runs/geometry_optimization_20260816/sf3_fullstat_delayed_v1"
        followup.fixture_gate(root, True)
        fixture_json(root, "data/sf3_fullstat_followup_execution_manifest.json", followup.load_manifest())
        fixture_manifest_sha = hashlib.sha256(
            (root / "data/sf3_fullstat_followup_execution_manifest.json").read_bytes()
        ).hexdigest()
        plan1_ids = [f"plan1_bg_{index:02d}" for index in range(21)]
        plan1_rows = [{"job_id": job_id, "stage": "background", "geometry": "SF3", "mode": "instant" if index < 11 else "buildup", "family": f"f{index % 8}", "events": 100 + index, "seed": 1000 + index} for index, job_id in enumerate(plan1_ids)]
        plan1_delayed = [{"job_id": f"plan1_delayed_{index}", "stage": "delayed", "geometry": "SF3", "mode": "delayed", "family": f"f{index}", "events": 83334, "seed": 1100 + index} for index in range(8)]
        plan1_signal = [{"job_id": "plan1_signal", "stage": "signal", "geometry": "SF3", "mode": "signal", "family": "focused_gamma", "events": 37194, "seed": 1200}]
        fixture_csv(root, "data/sf3_plan1_job_plan.csv", plan1_rows + plan1_delayed + plan1_signal)
        zero_plan1_id = plan1_delayed[-1]["job_id"]
        plan1_selected_plan = plan1_rows + plan1_delayed[:-1] + plan1_signal
        fixture_json(root, "audit/sf3_plan1_transport_receipts.json", {"profile_id": PLAN1_PROFILE_ID, "status": "PASS__ALL_29_EFFECTIVE_SF3_ONLY_TRANSPORT_JOBS", "sim_digest_policy": "NO_REOPEN_OR_REHASH__RECEIPT_PATH_SIZE_HEADER_ONLY", "planned_jobs": 30, "effective_planned_jobs": 29, "execution_exclusions": {zero_plan1_id: PLAN1_ZERO_REASON}, "validated_jobs": 29, "background_planned_jobs": 21, "background_validated_jobs": 21, "background_validated_events": sum(row["events"] for row in plan1_rows), "selected_receipts": [{"job_id": row["job_id"], "stage": row["stage"], "mode": row["mode"], "family": row["family"], "events": row["events"], "seed": row["seed"]} for row in plan1_selected_plan]})
        setup_path = root / "geometry/DEMO2_DR_v3p5_SF3.geo.setup"
        topup_rows = [{"job_id": f"topup_{index:02d}", "stage": "fullstat_topup_background", "geometry": "SF3", "mode": "instant" if index < 15 else "buildup", "family": f"f{index % 8}", "events": 1000 + index, "seed": 5000 + index, "setup_path": str(setup_path), "run_root": str(topup_run_root)} for index in range(28)]
        fixture_csv(root, followup.TOPUP_PLAN, topup_rows)
        topup_selected: list[dict[str, Any]] = []
        for index, row in enumerate(topup_rows):
            job_id = row["job_id"]
            attempt_dir = topup_run_root / "jobs" / job_id / "attempts/attempt01"
            receipt = {"status": "PASS", "errors": [], "profile_id": TOPUP_PROFILE_ID, "job_id": job_id, "stage": "background", "geometry": "SF3", "mode": row["mode"], "family": row["family"], "events": row["events"], "seed": row["seed"], "setup_path": str(setup_path), "returncode": 0, "attempt": 1, "attempt_dir": str(attempt_dir), "sim_path": str(attempt_dir / f"{job_id}.inc1.id1.sim.gz"), "log_path": str(attempt_dir / f"{job_id}.log"), "isotope_dat_path": str(attempt_dir / f"{job_id}.dat.inc1.dat"), "sim_header": {"geometry": str(setup_path), "seed": row["seed"], "policy": "HEADER_ONLY__NO_FULL_SIM_SCAN_OR_DIGEST"}, "isotope_dat": {"TT_s": 1.0, "RP_record_count": index, "terminal_EN": True, "errors": []}, "sim_digest_policy": "OMITTED_BY_CONTRACT__PATH_SIZE_HEADER_RECEIPT_ONLY", "peak_process_group_rss_bytes": 10_000 + index, "artifact_bytes": 20_000 + index}
            relative_receipt = f"{followup.TOPUP_RECEIPT_ROOT}/{job_id}.json"
            fixture_json(root, relative_receipt, receipt)
            receipt_path = root / relative_receipt
            topup_selected.append({"job_id": job_id, "registered_stage": "fullstat_topup_background", "receipt_stage": "background", "geometry": "SF3", "mode": row["mode"], "family": row["family"], "events": row["events"], "seed": row["seed"], "receipt_path": str(receipt_path), "receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(), "peak_process_group_rss_bytes": receipt["peak_process_group_rss_bytes"], "artifact_bytes": receipt["artifact_bytes"]})
        fixture_json(root, followup.TOPUP_AGGREGATE, {"profile_id": TOPUP_PROFILE_ID, "status": "PASS__ALL_28_SF3_FULLSTAT_TOPUP_BACKGROUND_JOBS", "planned_jobs": 28, "validated_jobs": 28, "plan1_mutation": False, "attempt_namespace": str(topup_run_root / "jobs"), "selected_receipts": topup_selected})
        families = ["p", "n", "alpha", "gamma", "eminus", "eplus", "muminus", "muplus"]
        delayed_rows: list[dict[str, Any]] = []
        cards: list[dict[str, Any]] = []
        for index, family in enumerate(families):
            positive = index < 7
            job_id = f"full_delayed_{family}"
            source_path = root / f"config/fullstat_delayed_source_cards/{job_id}.source"
            delayed_rows.append({"job_id": job_id, "stage": "fullstat_delayed", "geometry": "SF3", "mode": "delayed", "family": family, "seed": 7000 + index, "registered_events": 250000, "events": 250000 if positive else 0, "actual_transport_events": 250000 if positive else 0, "execution_disposition": "RUN_FRESH_250000" if positive else "SKIP_ZERO_A15", "transport_eligible": str(positive).lower(), "source_path": str(source_path), "source_status": "POSITIVE_SOURCE" if positive else "ZERO_SOURCE", "setup_path": str(setup_path), "seed_namespace": DELAYED_PROFILE_ID, "plan1_83334_role": "SCREENING_ONLY__DO_NOT_CONSUME_OR_MERGE", "incremental_merge_allowed": "false", "run_root": str(delayed_run_root)})
            cards.append({"job_id": job_id, "family": family, "path": str(source_path), "sha256": f"{index + 1:064x}", "seed": 7000 + index, "registered_events": 250000, "actual_transport_events": 250000 if positive else 0, "execution_disposition": "RUN_FRESH_250000" if positive else "SKIP_ZERO_A15", "transported_ground_activity_Bq": 1.0 if positive else 0.0, "transported_ground_rate_upper95_s-1": None if positive else 0.01, "transported_ground_A15_upper95_Bq_conservative": None if positive else 0.01, "original_blocks": 50000 if positive else 0, "transport_blocks": 10000 if positive else 0, "position_stride": 5})
        fixture_csv(root, followup.FULLSTAT_DELAYED_PLAN, delayed_rows)
        fixture_json(root, followup.FULLSTAT_ACTIVATION_VALIDATION, {"status": "PASS__SF3_FULLSTAT_ACTIVATION_VALIDATION", "source_cards": cards})
        positive_ids = [row["job_id"] for row in delayed_rows[:7]]
        zero_id = delayed_rows[-1]["job_id"]
        delayed_selected: list[dict[str, Any]] = []
        for index, row in enumerate(delayed_rows[:7]):
            job_id = row["job_id"]
            attempt_dir = delayed_run_root / "jobs" / job_id / "attempts/attempt01"
            receipt = {"status": "PASS", "errors": [], "profile_id": DELAYED_PROFILE_ID, "job_id": job_id, "stage": "fullstat_delayed", "geometry": "SF3", "mode": "delayed", "family": row["family"], "registered_events": 250000, "events": 250000, "actual_transport_events": 250000, "seed": row["seed"], "setup_path": str(setup_path), "source_status": "POSITIVE_SOURCE", "execution_disposition": "RUN_FRESH_250000", "transport_eligible": True, "seed_namespace": DELAYED_PROFILE_ID, "plan1_83334_role": "SCREENING_ONLY__DO_NOT_CONSUME_OR_MERGE", "incremental_merge_allowed": False, "receipt_namespace": str(root / followup.FULLSTAT_DELAYED_RECEIPT_ROOT), "returncode": 0, "attempt": 1, "attempt_dir": str(attempt_dir), "sim_path": str(attempt_dir / f"{job_id}.inc1.id1.sim.gz"), "log_path": str(attempt_dir / f"{job_id}.log"), "isotope_dat_path": None, "sim_header": {"geometry": str(setup_path), "seed": row["seed"], "policy": "HEADER_ONLY__NO_FULL_SIM_SCAN_OR_DIGEST"}, "sim_digest_policy": "OMITTED_BY_CONTRACT__PATH_SIZE_HEADER_RECEIPT_ONLY", "peak_process_group_rss_bytes": 30_000 + index, "artifact_bytes": 40_000 + index}
            relative_receipt = f"{followup.FULLSTAT_DELAYED_RECEIPT_ROOT}/{job_id}.json"
            fixture_json(root, relative_receipt, receipt)
            receipt_path = root / relative_receipt
            delayed_selected.append({"job_id": job_id, "family": row["family"], "stage": "fullstat_delayed", "seed": row["seed"], "registered_events": 250000, "events": 250000, "actual_transport_events": 250000, "execution_disposition": "RUN_FRESH_250000", "transport_eligible": True, "receipt_path": str(receipt_path), "receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(), "peak_process_group_rss_bytes": receipt["peak_process_group_rss_bytes"], "artifact_bytes": receipt["artifact_bytes"]})
        fixture_json(root, followup.FULLSTAT_DELAYED_AGGREGATE, {"profile_id": DELAYED_PROFILE_ID, "status": "PASS__SF3_FULLSTAT_DELAYED_FRESH250K_COMPLETE", "registered_families": 8, "planned_transport_jobs": 7, "validated_transport_jobs": 7, "fresh_triggers_per_positive_family": 250000, "run_root": str(delayed_run_root), "selected_receipts": delayed_selected, "execution_exclusions": {zero_id: followup.ZERO_REASON}, "plan1_83334_read": False, "plan1_83334_pooled": False, "incremental_merge_used": False})
        for label, status in {
            "build_fullstat_prompt": "PASS__SF3_FULLSTAT_PROMPT_COMPLETE",
            "analyze_fullstat_delayed": "PASS__SF3_FULLSTAT_DELAYED_RAW_CATALOG_8_REGISTERED_SOURCE_CELLS_COMPLETE",
            "build_fullstat_common_response": "PASS__SF3_FULLSTAT_COMMON_RESPONSE_AND_REUSED_FULL_ENVELOPE_SIGNAL_COMPLETE",
        }.items():
            summary_relative = str(followup.EXPECTED_STEP_METADATA[label][2])
            fixture_json(root, summary_relative, {"status": status})
            fixture_json(root, str(Path(summary_relative).parent / "manifest.json"), {"status": status})

        topup_run_root.mkdir(parents=True, exist_ok=True)
        topup_metric_rows = [{"at": (datetime(2026, 8, 16, tzinfo=timezone.utc) + timedelta(seconds=index)).isoformat(), "job_id": receipt["job_id"], "attempt": 1, "status": "PASS", "wall_s": 1.0 + index, "peak_rss": receipt["peak_process_group_rss_bytes"], "artifact_bytes": receipt["artifact_bytes"], "free_bytes": DISK_RESERVE + 10_000 + index} for index, receipt in enumerate(topup_selected)]
        (topup_run_root / "resource_metrics.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in topup_metric_rows), encoding="utf-8")
        delayed_run_root.mkdir(parents=True, exist_ok=True)
        delayed_metric_rows = [{"at": (datetime(2026, 8, 16, tzinfo=timezone.utc) + timedelta(minutes=1, seconds=index)).isoformat(), "job_id": receipt["job_id"], "attempt": 1, "status": "PASS", "wall_s": 2.0 + index, "peak_rss": receipt["peak_process_group_rss_bytes"], "artifact_bytes": receipt["artifact_bytes"], "free_bytes": DISK_RESERVE + 20_000 + index} for index, receipt in enumerate(delayed_selected)]
        (delayed_run_root / "resource_metrics.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in delayed_metric_rows), encoding="utf-8")

        origin = datetime(2026, 8, 16, tzinfo=timezone.utc)
        guard = bytearray()
        wal_rows: list[dict[str, Any]] = []
        retry_label = EXPECTED_LABELS[0]
        retry_wal_at = (origin - timedelta(minutes=3)).isoformat()
        wal_rows.append({"schema_version": 1, "status": "STARTED__WRITE_AHEAD_BEFORE_GUARD_OR_STAGE", "at": retry_wal_at, "session_label": retry_label, "service_unit": followup.DEFAULT_SERVICE_UNIT, "guard_log_start_byte": 0, "followup_manifest_sha256": fixture_manifest_sha, "completion_authority": followup.EXPECTED_STEP_METADATA[retry_label][2], "disk_path": str(root), "dynamic_disk_reserve_bytes": DISK_RESERVE, "stage_started": False, "SIM_opened_statted_discovered_or_hashed": False})
        retry_sample = {"at": (origin - timedelta(minutes=2)).isoformat(), "unit": followup.DEFAULT_SERVICE_UNIT, "session_label": retry_label, "unit_state": "active", "observed_quota_percent": 400, "quota_percent": 400, "quota_changed": False, "decision_reasons": ["hold"], "safe_streak": 0, "cgroup_pressure": {"some_avg10": 0.0, "full_avg10": 0.0, "some_total": 1.0, "full_total": 0.0}, "mem_available_bytes": MEM_FLOOR + 500, "swap_free_bytes": SWAP_FLOOR + 500, "mem_floor_bytes": MEM_FLOOR, "swap_floor_bytes": SWAP_FLOOR, "disk_path": str(root), "disk_free_bytes": DISK_RESERVE + 500, "disk_floor_bytes": DISK_RESERVE}
        retry_closure = {"at": (origin - timedelta(minutes=1)).isoformat(), "unit": followup.DEFAULT_SERVICE_UNIT, "session_label": retry_label, "unit_state": "active", "observed_quota_percent": 400, "quota_percent": 400, "quota_changed": False, "decision_reasons": ["guard_exit_restore_normal"], "safe_streak": 0, "mem_available_bytes": MEM_FLOOR + 500, "swap_free_bytes": SWAP_FLOOR + 500, "mem_floor_bytes": MEM_FLOOR, "swap_floor_bytes": SWAP_FLOOR, "disk_path": str(root), "disk_free_bytes": DISK_RESERVE + 500, "disk_floor_bytes": DISK_RESERVE}
        guard.extend((json.dumps(retry_sample, sort_keys=True) + "\n").encode())
        guard.extend((json.dumps(retry_closure, sort_keys=True) + "\n").encode())
        resource_rows: list[dict[str, Any]] = []
        for index, label in enumerate(EXPECTED_LABELS):
            start = len(guard)
            wal_started_at = (origin + timedelta(minutes=index * 10) - timedelta(seconds=1)).isoformat()
            wal_rows.append({"schema_version": 1, "status": "STARTED__WRITE_AHEAD_BEFORE_GUARD_OR_STAGE", "at": wal_started_at, "session_label": label, "service_unit": followup.DEFAULT_SERVICE_UNIT, "guard_log_start_byte": start, "followup_manifest_sha256": fixture_manifest_sha, "completion_authority": followup.EXPECTED_STEP_METADATA[label][2], "disk_path": str(root), "dynamic_disk_reserve_bytes": DISK_RESERVE, "stage_started": False, "SIM_opened_statted_discovered_or_hashed": False})
            quotas = [400, 300] if index == 0 else [400]
            for subindex, quota in enumerate(quotas):
                event = {"at": (origin + timedelta(minutes=index * 10, seconds=subindex)).isoformat(), "unit": followup.DEFAULT_SERVICE_UNIT, "session_label": label, "unit_state": "active", "observed_quota_percent": quota, "quota_percent": quota, "quota_changed": subindex > 0, "decision_reasons": ["hold"], "safe_streak": 0, "cgroup_pressure": {"some_avg10": 0.0, "full_avg10": 0.0, "some_total": 1.0, "full_total": 0.0}, "mem_available_bytes": MEM_FLOOR + 100 + index, "swap_free_bytes": SWAP_FLOOR + 200 + index, "mem_floor_bytes": MEM_FLOOR, "swap_floor_bytes": SWAP_FLOOR, "disk_path": str(root), "disk_free_bytes": DISK_RESERVE + 400 + index, "disk_floor_bytes": DISK_RESERVE}
                guard.extend((json.dumps(event, sort_keys=True) + "\n").encode())
            closure_mem = MEM_FLOOR + 100
            closure_swap = SWAP_FLOOR + 200
            closure_disk = DISK_RESERVE + 300
            closure = {"at": (origin + timedelta(minutes=index * 10, seconds=5)).isoformat(), "unit": followup.DEFAULT_SERVICE_UNIT, "session_label": label, "unit_state": "active", "observed_quota_percent": quotas[-1], "quota_percent": 400, "quota_changed": quotas[-1] != 400, "decision_reasons": ["guard_exit_restore_normal"], "safe_streak": 0, "mem_available_bytes": closure_mem, "swap_free_bytes": closure_swap, "mem_floor_bytes": MEM_FLOOR, "swap_floor_bytes": SWAP_FLOOR, "disk_path": str(root), "disk_free_bytes": closure_disk, "disk_floor_bytes": DISK_RESERVE}
            guard.extend((json.dumps(closure, sort_keys=True) + "\n").encode())
            end = len(guard)
            recovered = index == 2
            resource_rows.append({"schema_version": 1, "status": "PASS", "at": (origin + timedelta(minutes=index * 10, seconds=6)).isoformat(), "phase": EXPECTED_PHASES[label], "session_label": label, "service_unit": followup.DEFAULT_SERVICE_UNIT, "actual_workers": 4, "configured_cpu_budget_max": 6, "quota_percent": 400, "quota_percent_is_worker_count": False, "followup_manifest_sha256": fixture_manifest_sha, "guard_log_start_byte": start, "guard_log_end_byte": end, "mem_floor_bytes": MEM_FLOOR, "swap_floor_bytes": SWAP_FLOOR, "dynamic_disk_reserve_bytes": DISK_RESERVE, "mem_available_bytes": closure_mem, "swap_free_bytes": closure_swap, "disk_free_after_projection_bytes": closure_disk, "stage_returncode": None if recovered else 0, "completion_authority_inferred_success": recovered, "recovered_after_controller_crash": recovered, "guard_session_wal_started_at": wal_started_at, "guard_session": {"session_label": label, "samples": len(quotas), "closure": "guard_exit_restore_normal", "restored_quota_percent": 400, "hard_floor_breaches": 0, "completion_mem_available_bytes": closure_mem, "completion_swap_free_bytes": closure_swap, "completion_disk_free_bytes": closure_disk}, "SIM_opened_statted_discovered_or_hashed_by_controller": False})
        guard_path = root / "audit/sf3_fullstat_followup_pressure_guard.jsonl"
        guard_path.parent.mkdir(parents=True, exist_ok=True)
        guard_path.write_bytes(bytes(guard))
        wal_path = root / "audit/sf3_fullstat_followup_guard_session_wal.jsonl"
        wal_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in wal_rows), encoding="utf-8")
        resource_path = root / "audit/sf3_fullstat_followup_resource_events.jsonl"
        resource_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in resource_rows), encoding="utf-8")

        checked = evaluate(root, topup_run_root=topup_run_root, delayed_run_root=delayed_run_root)
        if not checked["ready"] or checked["errors"] or checked["missing"] or checked["pending"]:
            raise AssertionError(f"synthetic full-stat resource closure failed: {checked}")
        if checked["job_scope"]["fullstat_background_jobs"] != 49 or checked["job_scope"]["total_transport_jobs"] != 56:
            raise AssertionError("synthetic 49+positive delayed receipt scope failed")
        if checked["actual_workers_observed"] != [4] or set(checked["quota_percent_observed"]) != {300, 400}:
            raise AssertionError("synthetic workers/quota separation failed")
        disk_metrics = checked["transport_completion_disk_metrics"]
        if (
            disk_metrics["all_new_transport_receipts_have_exactly_one_pass_metric"] is not True
            or disk_metrics["all_finalized_attempts_dynamic_8GiB_reserve_pass"] is not True
        ):
            raise AssertionError("synthetic per-job transport resource closure failed")
        if checked["superseded_or_retried_clean_guard_sessions"] != 1:
            raise AssertionError("synthetic clean retried guard session was not fully audited")
        if (
            checked["normal_completion_records"] != 4
            or checked["crash_recovered_completion_records"] != 1
            or checked["normal_or_crash_recovery_record_XOR_pass"] is not True
            or checked["all_completion_resources_from_original_guard_closure_not_live_inference"] is not True
            or checked["guard_session_wal_audit"]["all_clean_guard_sessions_have_write_ahead_start"] is not True
            or checked["all_guarded_completion_authorities_independently_validated"] is not True
        ):
            raise AssertionError("synthetic WAL-bound normal/recovery XOR closure failed")

        prompt_summary = root / str(followup.EXPECTED_STEP_METADATA["build_fullstat_prompt"][2])
        prompt_summary_raw = prompt_summary.read_bytes()
        prompt_summary.unlink()
        missing_completion = evaluate(root, topup_run_root=topup_run_root, delayed_run_root=delayed_run_root)
        if missing_completion["ready"] or not any(str(prompt_summary) in value for value in missing_completion["missing"]):
            raise AssertionError("missing canonical guarded prompt completion authority was accepted")
        prompt_summary.write_bytes(prompt_summary_raw)

        plan1_aggregate_path = root / "audit/sf3_plan1_transport_receipts.json"
        plan1_aggregate_good = parse_json(read_small(plan1_aggregate_path), plan1_aggregate_path)
        plan1_bad = dict(plan1_aggregate_good)
        plan1_bad["status"] = "PASS__ALL_WRONG_BUT_PREFIX_MATCHES"
        fixture_json(root, "audit/sf3_plan1_transport_receipts.json", plan1_bad)
        if not evaluate(root, topup_run_root=topup_run_root, delayed_run_root=delayed_run_root)["errors"]:
            raise AssertionError("noncanonical Plan-1 PASS prefix/status was accepted")
        fixture_json(root, "audit/sf3_plan1_transport_receipts.json", plan1_aggregate_good)

        topup_aggregate_path = root / followup.TOPUP_AGGREGATE
        topup_aggregate_good = parse_json(read_small(topup_aggregate_path), topup_aggregate_path)
        topup_bad_digest = json.loads(json.dumps(topup_aggregate_good))
        topup_bad_digest["selected_receipts"][0]["receipt_sha256"] = "0" * 64
        fixture_json(root, followup.TOPUP_AGGREGATE, topup_bad_digest)
        if not evaluate(root, topup_run_root=topup_run_root, delayed_run_root=delayed_run_root)["errors"]:
            raise AssertionError("top-up canonical small-receipt digest mismatch was accepted")
        fixture_json(root, followup.TOPUP_AGGREGATE, topup_aggregate_good)

        first_topup_receipt_path = root / followup.TOPUP_RECEIPT_ROOT / f"{topup_rows[0]['job_id']}.json"
        first_topup_receipt_good = parse_json(read_small(first_topup_receipt_path), first_topup_receipt_path)
        first_topup_receipt_bad = dict(first_topup_receipt_good)
        first_topup_receipt_bad["geometry"] = "SE3"
        fixture_json(root, f"{followup.TOPUP_RECEIPT_ROOT}/{topup_rows[0]['job_id']}.json", first_topup_receipt_bad)
        topup_bad_core = json.loads(json.dumps(topup_aggregate_good))
        topup_bad_core["selected_receipts"][0]["receipt_sha256"] = hashlib.sha256(first_topup_receipt_path.read_bytes()).hexdigest()
        fixture_json(root, followup.TOPUP_AGGREGATE, topup_bad_core)
        if not evaluate(root, topup_run_root=topup_run_root, delayed_run_root=delayed_run_root)["errors"]:
            raise AssertionError("digest-consistent wrong-geometry canonical receipt was accepted")
        fixture_json(root, f"{followup.TOPUP_RECEIPT_ROOT}/{topup_rows[0]['job_id']}.json", first_topup_receipt_good)
        fixture_json(root, followup.TOPUP_AGGREGATE, topup_aggregate_good)

        bad_rows = [dict(row) for row in resource_rows]
        bad_rows[0]["phase"] = EXPECTED_PHASES[EXPECTED_LABELS[1]]
        resource_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in bad_rows), encoding="utf-8")
        if not evaluate(root, topup_run_root=topup_run_root, delayed_run_root=delayed_run_root)["errors"]:
            raise AssertionError("mislabeled guarded phase was accepted")
        resource_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in resource_rows), encoding="utf-8")

        bad_recovery_rows = [dict(row) for row in resource_rows]
        bad_recovery_rows[2]["stage_returncode"] = 0
        resource_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in bad_recovery_rows), encoding="utf-8")
        if not evaluate(root, topup_run_root=topup_run_root, delayed_run_root=delayed_run_root)["errors"]:
            raise AssertionError("mixed normal/recovery completion shape was accepted")
        resource_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in resource_rows), encoding="utf-8")

        bad_closure_binding_rows = [dict(row) for row in resource_rows]
        bad_closure_binding_rows[0]["disk_free_after_projection_bytes"] += 1
        resource_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in bad_closure_binding_rows), encoding="utf-8")
        if not evaluate(root, topup_run_root=topup_run_root, delayed_run_root=delayed_run_root)["errors"]:
            raise AssertionError("completion resource value not from original closure was accepted")
        resource_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in resource_rows), encoding="utf-8")

        bad_wal_rows = [dict(row) for row in wal_rows]
        bad_wal_rows[1]["completion_authority"] = "outputs/fullstat/WRONG"
        wal_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in bad_wal_rows), encoding="utf-8")
        if not evaluate(root, topup_run_root=topup_run_root, delayed_run_root=delayed_run_root)["errors"]:
            raise AssertionError("noncanonical WAL completion authority was accepted")
        wal_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in wal_rows), encoding="utf-8")

        topup_metric_path = topup_run_root / "resource_metrics.jsonl"
        bad_metric_rows = [dict(row) for row in topup_metric_rows]
        bad_metric_rows[0]["free_bytes"] = DISK_RESERVE - 1
        topup_metric_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in bad_metric_rows), encoding="utf-8")
        if not evaluate(root, topup_run_root=topup_run_root, delayed_run_root=delayed_run_root)["errors"]:
            raise AssertionError("per-job dynamic disk reserve breach was accepted")
        topup_metric_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in topup_metric_rows), encoding="utf-8")

        duplicate_pass_rows = [dict(row) for row in topup_metric_rows]
        duplicate = dict(duplicate_pass_rows[0])
        duplicate["attempt"] = 2
        duplicate_pass_rows.append(duplicate)
        topup_metric_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in duplicate_pass_rows), encoding="utf-8")
        if not evaluate(root, topup_run_root=topup_run_root, delayed_run_root=delayed_run_root)["errors"]:
            raise AssertionError("duplicate PASS resource metric was accepted")
        topup_metric_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in topup_metric_rows), encoding="utf-8")

        pass_then_fail_rows = [dict(row) for row in topup_metric_rows]
        late_fail = dict(pass_then_fail_rows[0])
        late_fail.update({"attempt": 2, "status": "FAIL"})
        pass_then_fail_rows.append(late_fail)
        topup_metric_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in pass_then_fail_rows), encoding="utf-8")
        if not evaluate(root, topup_run_root=topup_run_root, delayed_run_root=delayed_run_root)["errors"]:
            raise AssertionError("finalized FAIL after canonical PASS was accepted")
        topup_metric_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in topup_metric_rows), encoding="utf-8")

        corrupted = bytes(guard).replace(str(MEM_FLOOR + 100).encode(), str(MEM_FLOOR - 1).encode(), 1)
        guard_path.write_bytes(corrupted)
        if not evaluate(root, topup_run_root=topup_run_root, delayed_run_root=delayed_run_root)["errors"]:
            raise AssertionError("hard-floor guard sample was accepted")
        guard_path.write_bytes(bytes(guard))

        disk_corrupted = bytes(guard).replace(str(DISK_RESERVE + 300).encode(), str(DISK_RESERVE - 1).encode(), 1)
        guard_path.write_bytes(disk_corrupted)
        if not evaluate(root, topup_run_root=topup_run_root, delayed_run_root=delayed_run_root)["errors"]:
            raise AssertionError("original guard closure disk-floor breach was accepted")

        try:
            read_small(Path("/synthetic/forbidden.sim.gz"))
        except RuntimeError as exc:
            if "rejected before filesystem access" not in str(exc):
                raise
        else:
            raise AssertionError("SIM path was queried instead of rejected")
    return {
        "schema_version": 1,
        "status": "PASS__SF3_FULLSTAT_RESOURCE_TIMELINE_PURE_SYNTHETIC_SELF_TEST",
        "checks": [
            "manifest_byte_hash_and_exact_five_guarded_steps",
            "exact_session_label_to_phase_and_mislabeled_negative_test",
            "five_clean_guard_exit_restore_400_sessions",
            "complete_guard_log_all_bytes_and_clean_retried_sessions_audited",
            "WAL_bound_normal_XOR_crash_recovery_without_live_inference",
            "bad_WAL_mixed_recovery_shape_and_closure_snapshot_negative_tests",
            "five_independent_canonical_guarded_completion_authorities_and_missing_prompt_negative_test",
            "workers_exactly4_and_quota_exactly300_or400_are_not_conflated",
            "hard_MemAvailable_and_SwapFree_floor_samples",
            "dynamic_8GiB_disk_reserve_at_each_stage_completion",
            "per_new_transport_job_resource_metrics_exact_PASS_and_dynamic_8GiB_reserve",
            "duplicate_PASS_PASS_then_FAIL_and_per_job_disk_floor_negative_tests",
            "21_Plan1_plus28_topup_equals49_background_receipts",
            "Plan1_exact_30row_plan_profile_status_and_identity_closure_negative_test",
            "canonical_small_receipt_path_digest_and_core_payload_negative_tests",
            "fresh250k_positive_delayed_and_zero_finite_upper_skip",
            "Plan1_83334_never_read_or_pooled",
            "SIM_rejected_before_stat_open_or_hash",
        ],
        "production_authorities_accessed": False,
        "production_output_written": False,
        "SIM_opened_statted_discovered_or_hashed": False,
        "transport_launched_by_auditor": False,
        "systemd_or_service_action_performed_by_auditor": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--self-test", action="store_true")
    actions.add_argument("--check-prerequisites", action="store_true")
    actions.add_argument("--build", action="store_true")
    args = parser.parse_args()
    try:
        result = self_test() if args.self_test else evaluate() if args.check_prerequisites else build()
        print(json_text(result), end="")
        if args.check_prerequisites and not result.get("ready"):
            return 1 if result.get("errors") else 2
        return 0
    except Exception as exc:
        print(json_text({"schema_version": 1, "profile_id": PROFILE_ID, "status": "FAIL__SF3_FULLSTAT_RESOURCE_TIMELINE_ADAPTER", "error": str(exc), "SIM_opened_statted_discovered_or_hashed": False, "transport_launched_by_auditor": False}), end="")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
