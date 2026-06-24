#!/usr/bin/env python3
"""Generate WP10 manuscript-support documents for NO_RATE_AUTHORITY."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PHASE_DIR = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
OUT = PHASE_DIR / "10_manuscript_support"

WP04 = PHASE_DIR / "04_custom_source_v2/source_v2_manifest.json"
WP05 = PHASE_DIR / "05_native_activation/tag_aware_native_vs_direct_comparison.json"
WP08 = PHASE_DIR / "08_promotion/promotion_decision.json"
WP09 = PHASE_DIR / "09_downstream/summary.json"

FINAL_RATIONALE = OUT / "TES_511_delayed_source_modification_requirements_and_paper_impact_final.md"
INSERTIONS = OUT / "manuscript_insertions_en.md"
CHANGES_REQUIRED = OUT / "manuscript_changes_required.md"
CLAIM_BOUNDARY = OUT / "manuscript_claim_boundary.md"
SUPPLEMENT_TABLES = OUT / "supplement_tables.md"
FIGURE_SPEC = OUT / "source_method_figure_spec.md"
SUMMARY_JSON = OUT / "summary.json"
SUMMARY_MD = OUT / "summary.md"
WORK_PACKET = PHASE_DIR / "work_packets/WP10_manuscript_support_no_rate_authority.md"
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
        if line.startswith("WP10:"):
            lines[i] = f"WP10: {status}"
            updated = True
            break
    if not updated:
        lines.append(f"WP10: {status}")
    DECISION_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_work_packet() -> None:
    WORK_PACKET.parent.mkdir(parents=True, exist_ok=True)
    WORK_PACKET.write_text(
        "\n".join(
            [
                "# WP10 Manuscript Support No-Rate-Authority",
                "",
                "Task: generate manuscript support guidance without applying manuscript changes or promoting numbers.",
                "",
                "Input allowlist:",
                f"- `{rel(WP04)}`",
                f"- `{rel(WP05)}`",
                f"- `{rel(WP08)}`",
                f"- `{rel(WP09)}`",
                "",
                "Forbidden actions:",
                "- no manuscript source overwrite",
                "- no derived manuscript copy",
                "- no promoted delayed-rate/sensitivity number",
                "- no internal path in proposed paper prose",
                "",
                "Acceptance gate: produce guidance that distinguishes source-v2 method evidence from absent selected-rate authority.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    wp04 = load_json(WP04)
    wp05 = load_json(WP05)
    wp08 = load_json(WP08)
    wp09 = load_json(WP09)
    status = "NO_RATE_AUTHORITY"

    FINAL_RATIONALE.write_text(
        "\n".join(
            [
                "# Delayed Source v2 Paper Impact",
                "",
                "Status: `NO_RATE_AUTHORITY`.",
                "",
                "The engineering chain reconstructed a state-resolved, raw-volume-preserving delayed-source candidate from raw activation-production products. The source construction preserves production tag, raw logical volume, ZA, and excitation-state identity, and the source-level activity closes to the raw-inventory authority.",
                "",
                "This does not promote a new paper-facing delayed selected-rate number. The available v2 and native transports are 1000-trigger diagnostics only, and the required full-stat selected-rate convergence, seed variance, and `sum_w2` ledger are absent.",
                "",
                "Paper impact: do not change delayed background, total background, sensitivity, or BGO delayed-comparison numbers from this Phase-2 run. At most, use the source-v2 method as a described engineering candidate and state that no selected-rate replacement was promoted.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    INSERTIONS.write_text(
        "\n".join(
            [
                "# Manuscript Insertions (English Draft, Not Applied)",
                "",
                "No insertion is authorized for the current manuscript because no v2 selected-rate authority exists.",
                "",
                "Allowed future Methods language after a promotion decision:",
                "",
                "> We constructed a state-resolved production-position-sampled delayed source from activation-production records, preserving production family, raw logical volume, nuclide, and excitation-state identity through source generation. The source was compared with a native volume-based activation calculation to separate source-construction effects from decay-model and volume-approximation differences.",
                "",
                "Do not use this paragraph in a results section with numerical delayed-rate or sensitivity claims until WP08 is no longer `NO_RATE_AUTHORITY`.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    CHANGES_REQUIRED.write_text(
        "\n".join(
            [
                "# Manuscript Changes Required",
                "",
                "Current status: `NO_RATE_AUTHORITY`; no manuscript edit is required or authorized.",
                "",
                "Required before any delayed-number update:",
                "1. v2 full-stat selected-rate convergence with uncertainty and seed variance.",
                "2. WP08 promotion decision replacing `NO_RATE_AUTHORITY` with a promoted or retained-number verdict.",
                "3. WP09 downstream rebuild or explicit retained-number manifest for every delayed-dependent Step05-Step08 and BGO artifact.",
                "4. Manuscript-number manifest with rounded, traceable values.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    CLAIM_BOUNDARY.write_text(
        "\n".join(
            [
                "# Manuscript Claim Boundary",
                "",
                "Do not claim:",
                "- a promoted v2 delayed selected-rate result;",
                "- updated total background or sensitivity;",
                "- full decay-chain completeness;",
                "- BGO delayed comparison replacement;",
                "- flight-performance forecast.",
                "",
                "Allowed statement:",
                "- source-v2 construction is an audited engineering candidate with raw-volume, production-tag, and state identity preserved at source level.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    SUPPLEMENT_TABLES.write_text(
        "\n".join(
            [
                "# Supplement Tables",
                "",
                "Suggested tables after future promotion:",
                "",
                "| table | status now | required source |",
                "|---|---|---|",
                "| raw state-resolved inventory closure | available as engineering evidence | WP01 raw inventory ledger |",
                "| RPIP key coverage and canonicalization audit | available as engineering evidence | WP02 alignment ledger |",
                "| source-v2 activity closure | available as engineering evidence | WP04 source-v2 manifest |",
                "| native activation comparison | available as engineering evidence with model-difference caveat | WP05 native comparison |",
                "| v2 selected-rate energy bands | not available | future full-stat selected-rate run |",
                "| downstream sensitivity update | not available | future Step05-Step08 rebuild |",
                "",
                f"Source-v2 event rows: `{wp04['eventlist_rows']}`. Inventory total: `{wp04['inventory_total_activity_Bq']}` Bq.",
                f"Native/direct total relative delta: `{wp05['total_relative_delta']}`.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    FIGURE_SPEC.write_text(
        "\n".join(
            [
                "# Source Method Figure Spec",
                "",
                "Figure purpose: show the delayed-source v2 data lineage without implying a promoted rate.",
                "",
                "Panels:",
                "1. Raw activation-production records to state-resolved inventory keyed by production tag, raw volume, ZA, and state.",
                "2. RPIP position support joined on the same full key.",
                "3. Weighted exact-position EventList source and native volume-based activation-source cross-check.",
                "4. Blocked selected-rate promotion gate showing required full-stat convergence evidence.",
                "",
                "Caption must state that selected-rate and sensitivity numbers are not promoted by the current Phase-2 run.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    write_work_packet()
    summary = {
        "status": status,
        "inputs": [rel(WP04), rel(WP05), rel(WP08), rel(WP09)],
        "outputs": [
            rel(FINAL_RATIONALE),
            rel(INSERTIONS),
            rel(CHANGES_REQUIRED),
            rel(CLAIM_BOUNDARY),
            rel(SUPPLEMENT_TABLES),
            rel(FIGURE_SPEC),
            rel(SUMMARY_MD),
        ],
        "findings": [
            "Generated manuscript support guidance only; no manuscript source was modified.",
            "No delayed-rate, sensitivity, or BGO delayed number is promoted.",
            "Allowed language is limited to source-v2 method candidate context.",
        ],
        "claim_impact": [
            "The current manuscript should not be updated with v2 numerical results.",
            "Future manuscript changes require a non-NO_RATE_AUTHORITY WP08 decision and WP09 downstream closure.",
        ],
        "next_gate": "User decision: approve future full-stat v2 selected-rate convergence or accept NO_RATE_AUTHORITY endpoint.",
        "user_decision_required": True,
        "wp08_status": wp08["status"],
        "wp09_status": wp09["status"],
    }
    write_json(SUMMARY_JSON, summary)
    SUMMARY_MD.write_text(
        "\n".join(
            [
                "# WP10 Manuscript Support Summary",
                "",
                f"status: `{status}`",
                "",
                "Manuscript support documents were generated, but no manuscript source was modified and no v2 numbers were promoted.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    update_decision_log(status)
    print(json.dumps({"status": status, "summary": rel(SUMMARY_JSON)}, indent=2))


if __name__ == "__main__":
    main()
