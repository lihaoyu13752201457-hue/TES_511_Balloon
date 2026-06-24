#!/usr/bin/env python3
"""Emit WP09 downstream manifests for the NO_RATE_AUTHORITY endpoint."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PHASE_DIR = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
OUT = PHASE_DIR / "09_downstream"

WP08 = PHASE_DIR / "08_promotion/promotion_decision.json"
STEP05_MANIFEST = OUT / "step05_rebuild_manifest.json"
STEP06_STEP08_MANIFEST = OUT / "step06_step08_rebuild_manifest.json"
BGO_VERDICT = OUT / "bgo_delayed_dependency_verdict.json"
CONSISTENCY = OUT / "downstream_consistency_check.json"
SUMMARY_JSON = OUT / "summary.json"
SUMMARY_MD = OUT / "summary.md"
WORK_PACKET = PHASE_DIR / "work_packets/WP09_downstream_no_rate_authority.md"
DECISION_LOG = PHASE_DIR / "00_manifest/decision_log.md"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except Exception:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def update_decision_log(status: str) -> None:
    if not DECISION_LOG.exists():
        return
    lines = DECISION_LOG.read_text(encoding="utf-8").splitlines()
    updated = False
    for i, line in enumerate(lines):
        if line.startswith("WP09:"):
            lines[i] = f"WP09: {status}"
            updated = True
            break
    if not updated:
        lines.append(f"WP09: {status}")
    DECISION_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_work_packet() -> None:
    WORK_PACKET.parent.mkdir(parents=True, exist_ok=True)
    WORK_PACKET.write_text(
        "\n".join(
            [
                "# WP09 Downstream No-Rate-Authority Manifests",
                "",
                "Task: document downstream rebuild status after WP08 returned NO_RATE_AUTHORITY.",
                "",
                "Input allowlist:",
                f"- `{rel(WP08)}`",
                "",
                "Forbidden actions:",
                "- no Step05, Step06, Step07, or Step08 rebuild",
                "- no BGO transport",
                "- no `runs/`, `outputs/`, or `stepwise_maintenance/` writes",
                "- no manuscript edits",
                "",
                "Acceptance gate: downstream artifacts explicitly state not rebuilt and list minimum future rebuild requirements.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    wp08 = load_json(WP08)
    status = "NO_RATE_AUTHORITY"
    common_reason = (
        "WP08 did not promote a v2 delayed selected-rate authority. "
        "Full-stat v2 selected-rate convergence, sum_w2, and seed variance are missing."
    )
    step05 = {
        "status": status,
        "generated_at": now_utc(),
        "input_decision": rel(WP08),
        "rebuild_performed": False,
        "reason": common_reason,
        "retained_legacy_step05": [
            item for item in wp08.get("retained_numbers", []) if "delayed W2 selected" in item.get("name", "")
        ],
        "future_rebuild_required_before_v2_claim": [
            "Parse v2 full-stat delayed transport with Step05 detector response.",
            "Produce selected-rate ledger with W2 and required broad energy bands.",
            "Record sum_w, sum_w2, between-seed variance, and source/transport seed provenance.",
            "Regenerate combined prompt+delayed+signal Step05 only after v2 selected-rate authority is accepted.",
        ],
        "unchanged_by_this_wp": [
            "Step05 selection definitions",
            "prompt Step05 event catalog",
            "focused signal Step05 event catalog",
            "legacy fix5 Step05 outputs",
        ],
    }
    step06_step08 = {
        "status": status,
        "generated_at": now_utc(),
        "rebuild_performed": False,
        "reason": common_reason,
        "blocked_products": [
            "Step06 delayed mission-time fold",
            "Step07 source-case ledger",
            "Step08 significance/sensitivity tables",
            "any total-background or sensitivity number derived from v2 delayed rates",
        ],
        "minimum_future_inputs": [
            "promoted Step05 v2 delayed selected-rate table",
            "promotion_decision status V2_PROMOTED or LEGACY_RETAINED with quantified v2 comparison",
        ],
    }
    bgo = {
        "status": status,
        "generated_at": now_utc(),
        "bgo_delayed_rebuild_performed": False,
        "reason": common_reason,
        "verdict": "BGO delayed dependency not evaluated for replacement because v2 delayed source is not promoted.",
        "future_policy_if_v2_promoted": [
            "Check whether the BGO delayed result used the same legacy delayed builder hash.",
            "If yes, rerun only BGO activation/delayed chain; do not rerun BGO prompt, signal, or geometry comparison.",
            "If BGO delayed comparison is excluded from manuscript claims, record exclusion instead of consuming compute.",
        ],
    }
    consistency = {
        "status": status,
        "generated_at": now_utc(),
        "claim_boundary": "No downstream physics products were regenerated in WP09.",
        "forbidden_write_policy": [
            "no `runs/` writes",
            "no `outputs/` writes",
            "no `stepwise_maintenance/` writes",
            "no manuscript writes",
        ],
        "downstream_rebuild_state": {
            "step05": "not run",
            "step06_step08": "not run",
            "bgo_delayed": "not run",
        },
    }
    write_json(STEP05_MANIFEST, step05)
    write_json(STEP06_STEP08_MANIFEST, step06_step08)
    write_json(BGO_VERDICT, bgo)
    write_json(CONSISTENCY, consistency)
    write_work_packet()
    summary = {
        "status": status,
        "inputs": [rel(WP08)],
        "outputs": [
            rel(STEP05_MANIFEST),
            rel(STEP06_STEP08_MANIFEST),
            rel(BGO_VERDICT),
            rel(CONSISTENCY),
            rel(SUMMARY_MD),
        ],
        "findings": [
            "No delayed-dependent Step05-Step08 product was rebuilt.",
            "No BGO delayed dependency was rerun or promoted.",
            "Downstream rebuilds are blocked by WP08 NO_RATE_AUTHORITY.",
        ],
        "claim_impact": [
            "No v2 delayed background, sensitivity, or BGO-delayed number may be quoted.",
            "Existing downstream numbers are retained only under their legacy delayed-source method.",
        ],
        "next_gate": "G10 manuscript support may only emit no-promoted-number guidance unless user approves future full-stat v2 work.",
        "user_decision_required": True,
    }
    write_json(SUMMARY_JSON, summary)
    SUMMARY_MD.write_text(
        "\n".join(
            [
                "# WP09 Downstream Summary",
                "",
                f"status: `{status}`",
                "",
                "No Step05-Step08 or BGO delayed rebuild was run because WP08 did not produce a v2 rate authority.",
                "",
                "Blocked products:",
                "- Step05 v2 delayed selected-rate authority",
                "- Step06-Step08 delayed-dependent rates and sensitivity",
                "- BGO delayed dependency replacement",
                "",
            ]
        ),
        encoding="utf-8",
    )
    update_decision_log(status)
    print(json.dumps({"status": status, "summary": rel(SUMMARY_JSON)}, indent=2))


if __name__ == "__main__":
    main()
