#!/usr/bin/env python3
"""Build the WP08 promotion/no-rate-authority decision artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any


getcontext().prec = 80

PHASE_DIR = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
OUT = PHASE_DIR / "08_promotion"

WP04 = PHASE_DIR / "04_custom_source_v2/source_v2_manifest.json"
WP05 = PHASE_DIR / "05_native_activation/tag_aware_native_vs_direct_comparison.json"
WP06 = PHASE_DIR / "06_time_constant/timing_authority.json"
WP07 = PHASE_DIR / "07_transport/summary.json"

LEGACY_SOURCE_SUMMARY = ROOT / "outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_delayed_source_exactpos_summary.json"
LEGACY_STEP05 = (
    ROOT
    / "stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/"
    / "step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_response_summary.json"
)
LEGACY_PROMOTION = ROOT / "outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_promotion_decision.json"
LEGACY_FINAL_REPORT = ROOT / "outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_final_closure_report.json"

LEGACY_V2_CSV = OUT / "legacy_v2_comparison.csv"
LEGACY_V2_MD = OUT / "legacy_v2_comparison.md"
AFFECTED_JSON = OUT / "affected_artifacts_manifest.json"
STALE_MD = OUT / "stale_artifacts_manifest.md"
DECISION_JSON = OUT / "promotion_decision.json"
DECISION_MD = OUT / "promotion_decision.md"
MANUSCRIPT_NUMBERS_JSON = OUT / "manuscript_numbers_manifest.json"
SUMMARY_JSON = OUT / "summary.json"
SUMMARY_MD = OUT / "summary.md"
WORK_PACKET = PHASE_DIR / "work_packets/WP08_promotion_decision.md"
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


def dec(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None or value == "":
        return Decimal(0)
    return Decimal(str(value))


def fmt_dec(value: Decimal) -> str:
    return format(value.normalize(), "f") if value else "0"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def w2_delayed(summary: dict[str, Any]) -> dict[str, Any]:
    return summary["windows"]["w2_510p58_511p42"]["by_stream"]["delayed"]


def broad_delayed(summary: dict[str, Any]) -> dict[str, Any]:
    return summary["windows"]["broad_480_550"]["by_stream"]["delayed"]


def rate_sigma(rate: float, events: int) -> float | None:
    if events <= 0 or rate <= 0:
        return None
    return rate / math.sqrt(events)


def find_wp07_diag(wp07: dict[str, Any], name: str) -> dict[str, Any] | None:
    for item in wp07.get("selection_diagnostics", []):
        if item.get("name") == name:
            return item
    return None


def comparison_rows(
    legacy_source: dict[str, Any],
    legacy_step05: dict[str, Any],
    wp04: dict[str, Any],
    wp05: dict[str, Any],
    wp07: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    legacy_activity = dec(legacy_source["fixed_total_activity_Bq"])
    v2_activity = dec(wp04["inventory_total_activity_Bq"])
    rows.append(
        {
            "metric": "day15_total_activity_Bq",
            "legacy_value": fmt_dec(legacy_activity),
            "v2_value": fmt_dec(v2_activity),
            "absolute_delta": fmt_dec(v2_activity - legacy_activity),
            "relative_delta_vs_legacy": fmt_dec(abs(v2_activity - legacy_activity) / legacy_activity),
            "evidence": rel(WP04),
            "verdict": "SOURCE_LEVEL_V2_DIFFERS_NOT_RATE_PROMOTED",
            "notes": "v2 inventory is direct raw .dat authority; legacy is retained only as current legacy method until selected-rate promotion exists.",
        }
    )
    w2 = w2_delayed(legacy_step05)
    broad = broad_delayed(legacy_step05)
    for window, item in (("w2_510p58_511p42", w2), ("broad_480_550", broad)):
        rate = float(item["side_compton_fov_pass_rate_s-1"])
        events = int(item["side_compton_fov_pass_events"])
        rows.append(
            {
                "metric": f"legacy_{window}_delayed_side_compton_fov_cps",
                "legacy_value": f"{rate:.12g}",
                "v2_value": "",
                "absolute_delta": "",
                "relative_delta_vs_legacy": "",
                "evidence": rel(LEGACY_STEP05),
                "verdict": "NO_V2_FULLSTAT_SELECTED_RATE",
                "notes": f"legacy selected events={events}, sigma~{rate_sigma(rate, events):.12g}; no v2 full-stat selected-rate authority exists.",
            }
        )
    v2_diag = find_wp07_diag(wp07, "v2_weighted_eventlist")
    native_diag = find_wp07_diag(wp07, "native_volume_activation")
    if v2_diag:
        w2_v2 = v2_diag["windows"]["w2_510p58_511p42"]["by_stream"]["delayed"]
        rows.append(
            {
                "metric": "v2_pilot_w2_delayed_side_compton_fov_cps",
                "legacy_value": "",
                "v2_value": f"{float(w2_v2['side_compton_fov_pass_rate_s-1']):.12g}",
                "absolute_delta": "",
                "relative_delta_vs_legacy": "",
                "evidence": rel(WP07),
                "verdict": "PILOT_DIAGNOSTIC_ONLY",
                "notes": f"1000-trigger pilot; final events={w2_v2['side_compton_fov_pass_events']}; weight mapping={v2_diag.get('event_weight_mapping', {}).get('status')}.",
            }
        )
    if native_diag:
        w2_native = native_diag["windows"]["w2_510p58_511p42"]["by_stream"]["delayed"]
        rows.append(
            {
                "metric": "native_pilot_w2_delayed_side_compton_fov_cps",
                "legacy_value": "",
                "v2_value": f"{float(w2_native['side_compton_fov_pass_rate_s-1']):.12g}",
                "absolute_delta": "",
                "relative_delta_vs_legacy": "",
                "evidence": rel(WP07),
                "verdict": "VOLUME_NATIVE_PILOT_DIAGNOSTIC_ONLY",
                "notes": f"1000-trigger volume-based native pilot; final events={w2_native['side_compton_fov_pass_events']}; not exact-position v2 authority.",
            }
        )
    rows.append(
        {
            "metric": "tag_aware_native_total_activity_Bq",
            "legacy_value": "",
            "v2_value": wp05["tag_native_total_Bq"],
            "absolute_delta": "",
            "relative_delta_vs_legacy": "",
            "evidence": rel(WP05),
            "verdict": wp05["status"],
            "notes": f"native/direct total relative delta={wp05['total_relative_delta']}; native-only keys={wp05['native_only_key_count']}.",
        }
    )
    return rows


def write_comparison_csv(rows: list[dict[str, Any]]) -> None:
    fields = [
        "metric",
        "legacy_value",
        "v2_value",
        "absolute_delta",
        "relative_delta_vs_legacy",
        "evidence",
        "verdict",
        "notes",
    ]
    with LEGACY_V2_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_comparison_md(rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Legacy vs v2 Comparison",
        "",
        "Status: `NO_RATE_AUTHORITY`.",
        "",
        "| metric | legacy | v2 / diagnostic | verdict |",
        "|---|---:|---:|---|",
    ]
    for row in rows:
        lines.append(f"| {row['metric']} | {row['legacy_value']} | {row['v2_value']} | {row['verdict']} |")
    lines.extend(
        [
            "",
            "The v2 source-level authority is closed, but the harness G8 selected-rate requirements are not closed:",
            "- no v2 full-stat selected-rate extraction;",
            "- no pooled final W2 selected-event count >= 300;",
            "- no v2 source/transport seed variance or `sum_w2` selected-rate ledger;",
            "- legacy L0 comparator pilot timed out before producing SIM output.",
            "",
        ]
    )
    LEGACY_V2_MD.write_text("\n".join(lines), encoding="utf-8")


def build_affected_artifacts() -> dict[str, Any]:
    retained_legacy = [
        {
            "path": rel(LEGACY_STEP05),
            "role": "current legacy Step05 selected-rate authority",
            "status": "RETAINED_AS_LEGACY_REFERENCE_NOT_V2_PROMOTED",
        },
        {
            "path": rel(LEGACY_PROMOTION),
            "role": "previous fix5 promotion decision using legacy delayed source",
            "status": "RETAINED_AS_LEGACY_REFERENCE_NOT_V2_PROMOTED",
        },
        {
            "path": rel(LEGACY_FINAL_REPORT),
            "role": "previous fix5 closure report using legacy delayed source",
            "status": "RETAINED_AS_LEGACY_REFERENCE_NOT_V2_PROMOTED",
        },
    ]
    delayed_dependent_if_promoted = [
        "Step05 delayed stream and combined background",
        "Step06 delayed mission-time fold",
        "Step07 source-case ledger",
        "Step08 significance/sensitivity tables",
        "BGO delayed inventory/rate dependency if the same legacy builder is used",
        "manuscript delayed-background numbers and derived sensitivity rows",
    ]
    return {
        "status": "NO_RATE_AUTHORITY",
        "generated_at": now_utc(),
        "claim_boundary": "No downstream artifact is replaced because v2 selected-rate authority is absent.",
        "retained_legacy_artifacts": retained_legacy,
        "delayed_dependent_artifacts_to_rebuild_if_v2_is_later_promoted": delayed_dependent_if_promoted,
        "not_rebuilt_now": delayed_dependent_if_promoted,
        "unaffected_artifacts": [
            "fix5 geometry",
            "prompt source cards and prompt normalization",
            "focused signal/optics transport",
            "Step05 selection definitions: W2, 50 keV active-veto, 1 us coincidence, side-entry FoV/topology",
        ],
    }


def write_stale_md(affected: dict[str, Any]) -> None:
    lines = [
        "# Stale Artifact Manifest",
        "",
        "Status: `NO_RATE_AUTHORITY`.",
        "",
        "No existing artifact was overwritten or replaced. The following artifacts remain usable only as legacy-reference artifacts for the pre-v2 delayed source method:",
        "",
    ]
    for item in affected["retained_legacy_artifacts"]:
        lines.append(f"- `{item['path']}`: {item['status']}")
    lines.extend(
        [
            "",
            "If v2 is later promoted with full-stat selected-rate evidence, these delayed-dependent products must be regenerated:",
        ]
    )
    for item in affected["delayed_dependent_artifacts_to_rebuild_if_v2_is_later_promoted"]:
        lines.append(f"- {item}")
    STALE_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_decision(wp04: dict[str, Any], wp05: dict[str, Any], wp06: dict[str, Any], wp07: dict[str, Any]) -> dict[str, Any]:
    source_card = ROOT / wp04["outputs"]["source_card"]
    return {
        "status": "NO_RATE_AUTHORITY",
        "generated_at": now_utc(),
        "decision": "DO_NOT_PROMOTE_V2_DELAYED_SELECTED_RATE",
        "decision_reason": (
            "G4 source-v2 and G6 timing are closed, and G5 native difference is explained, "
            "but G7 has only 1000-trigger v2/native pilot diagnostics and the legacy L0 comparator timed out. "
            "No full-stat v2 selected-rate convergence, seed variance, or sum_w2 ledger exists."
        ),
        "promoted_source": {
            "path": wp04["outputs"]["source_card"],
            "sha256": sha256(source_card) if source_card.exists() else "",
            "status": "SOURCE_CONSTRUCTION_AUTHORITY_ONLY_NOT_SELECTED_RATE_PROMOTED",
        },
        "inventory_model": "direct_production_only_from_raw_dat_with_tag_raw_volume_ZA_state_keys",
        "inventory_total_activity_Bq": wp04["inventory_total_activity_Bq"],
        "timing_authority_s": wp06["timing_authority_s"],
        "native_comparison_status": wp05["status"],
        "selected_rate_authority": {
            "status": "MISSING_FULLSTAT_V2_SELECTED_RATE",
            "required_by_harness": [
                "pooled final W2 selected events >= 300 or relative MC uncertainty <= 10%",
                "at least 3 position-sampling seeds or documented resource reduction",
                "at least 3 decay-transport seeds or documented orthogonal reduction",
                "sum_w, sum_w2, and between-seed variance",
            ],
            "available_evidence": rel(WP07),
            "available_status": wp07["status"],
        },
        "replaced_numbers": [],
        "retained_numbers": [
            {
                "name": "legacy fix5 delayed W2 selected cps",
                "value": "0.0025752034889400762",
                "status": "RETAINED_AS_LEGACY_REFERENCE_NOT_V2_PROMOTED",
                "evidence": rel(LEGACY_STEP05),
            }
        ],
        "stale_artifacts": "none replaced now; delayed-dependent legacy artifacts are stale only for a future v2-method claim",
        "unresolved_limitations": [
            "No v2 full-stat selected-rate authority.",
            "No v2 selected-rate seed variance or sum_w2 ledger.",
            "Legacy L0 pilot comparator did not produce a SIM output within the bounded 300 s cap.",
            "Native volume-based pilot is diagnostic and not an exact-position selected-rate replacement.",
        ],
        "next_minimum_step": (
            "Generate an explicit resource/approval plan for v2 full-stat selected-rate convergence, "
            "or accept NO_RATE_AUTHORITY as the legal endpoint for this harness run."
        ),
        "user_decision_required": True,
    }


def build_manuscript_manifest(decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "NO_RATE_AUTHORITY",
        "generated_at": now_utc(),
        "apply_manuscript_changes": False,
        "promoted_manuscript_numbers": {},
        "retained_legacy_numbers_for_current_text_only": decision["retained_numbers"],
        "numbers_not_allowed_for_manuscript": [
            "v2_weighted_eventlist 1000-trigger pilot W2 rate",
            "native_volume_activation 1000-trigger pilot W2 rate",
            "any full-stat v2 delayed selected rate",
            "any Step06-Step08 sensitivity update from v2",
        ],
        "required_before_manuscript_number_update": [
            "v2 full-stat selected-rate convergence",
            "promotion_decision status V2_PROMOTED or LEGACY_RETAINED with quantified v2 comparison",
            "downstream delayed-dependent Step05-Step08 rebuild or explicit retained-number verdict",
        ],
        "allowed_textual_support_now": [
            "Methods-draft language may describe the source-v2 construction as an engineering candidate.",
            "Text must state that no v2 selected-rate or sensitivity number is promoted.",
        ],
    }


def write_decision_md(decision: dict[str, Any]) -> None:
    lines = [
        "# WP08 Promotion Decision",
        "",
        f"Status: `{decision['status']}`.",
        "",
        decision["decision_reason"],
        "",
        "Promoted numbers: none.",
        "",
        "Retained numbers:",
    ]
    for item in decision["retained_numbers"]:
        lines.append(f"- `{item['name']}` = `{item['value']}` ({item['status']})")
    lines.extend(["", "Unresolved limitations:"])
    for item in decision["unresolved_limitations"]:
        lines.append(f"- {item}")
    lines.extend(["", f"Next minimum step: {decision['next_minimum_step']}", ""])
    DECISION_MD.write_text("\n".join(lines), encoding="utf-8")


def write_summary_md(summary: dict[str, Any]) -> None:
    lines = [
        "# WP08 Summary",
        "",
        f"status: `{summary['status']}`",
        "",
        "Findings:",
    ]
    for item in summary["findings"]:
        lines.append(f"- {item}")
    lines.extend(["", "Claim impact:"])
    for item in summary["claim_impact"]:
        lines.append(f"- {item}")
    lines.extend(["", f"Next gate: {summary['next_gate']}", ""])
    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")


def write_work_packet() -> None:
    WORK_PACKET.parent.mkdir(parents=True, exist_ok=True)
    WORK_PACKET.write_text(
        "\n".join(
            [
                "# WP08 Promotion Decision",
                "",
                "Task: decide whether source-v2 evidence can promote a delayed selected-rate authority and identify downstream impacts.",
                "",
                "Input allowlist:",
                f"- `{rel(WP04)}`",
                f"- `{rel(WP05)}`",
                f"- `{rel(WP06)}`",
                f"- `{rel(WP07)}`",
                f"- `{rel(LEGACY_SOURCE_SUMMARY)}`",
                f"- `{rel(LEGACY_STEP05)}`",
                "",
                "Forbidden actions:",
                "- no Cosima transport",
                "- no Step05-Step08 rebuild",
                "- no manuscript overwrite",
                "- no geometry/prompt/selection edits",
                "",
                "Acceptance gate: emit V2_PROMOTED, LEGACY_RETAINED, or NO_RATE_AUTHORITY with evidence, affected artifacts, and manuscript-number manifest.",
                "",
                "Termination status: NO_RATE_AUTHORITY if full-stat v2 selected-rate evidence is absent.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def update_decision_log(status: str) -> None:
    if not DECISION_LOG.exists():
        return
    lines = DECISION_LOG.read_text(encoding="utf-8").splitlines()
    updated = False
    for i, line in enumerate(lines):
        if line.startswith("WP08:"):
            lines[i] = f"WP08: {status}"
            updated = True
            break
    if not updated:
        lines.append(f"WP08: {status}")
    DECISION_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    wp04 = load_json(WP04)
    wp05 = load_json(WP05)
    wp06 = load_json(WP06)
    wp07 = load_json(WP07)
    legacy_source = load_json(LEGACY_SOURCE_SUMMARY)
    legacy_step05 = load_json(LEGACY_STEP05)

    rows = comparison_rows(legacy_source, legacy_step05, wp04, wp05, wp07)
    write_comparison_csv(rows)
    write_comparison_md(rows)
    affected = build_affected_artifacts()
    write_json(AFFECTED_JSON, affected)
    write_stale_md(affected)
    decision = build_decision(wp04, wp05, wp06, wp07)
    write_json(DECISION_JSON, decision)
    write_decision_md(decision)
    manuscript = build_manuscript_manifest(decision)
    write_json(MANUSCRIPT_NUMBERS_JSON, manuscript)
    write_work_packet()
    status = "NO_RATE_AUTHORITY"
    summary = {
        "status": status,
        "inputs": [
            rel(WP04),
            rel(WP05),
            rel(WP06),
            rel(WP07),
            rel(LEGACY_SOURCE_SUMMARY),
            rel(LEGACY_STEP05),
        ],
        "outputs": [
            rel(LEGACY_V2_CSV),
            rel(LEGACY_V2_MD),
            rel(AFFECTED_JSON),
            rel(STALE_MD),
            rel(DECISION_JSON),
            rel(DECISION_MD),
            rel(MANUSCRIPT_NUMBERS_JSON),
            rel(SUMMARY_MD),
        ],
        "findings": [
            "source-v2 construction and timing authority are closed, but selected-rate authority is not",
            "v2 full-stat selected-rate convergence, sum_w2, and seed variance are missing",
            "legacy L0 pilot comparator timed out; v2/native pilot rates are diagnostic only",
            "no Step05-Step08, BGO, sensitivity, or manuscript number was replaced",
        ],
        "claim_impact": [
            "No v2 delayed selected-rate or sensitivity number may be used as manuscript authority.",
            "Legacy fix5 delayed selected rates remain retained as legacy-reference numbers only.",
            "Downstream delayed-dependent artifacts must be rebuilt only after a future promotion decision.",
        ],
        "next_gate": "User decision: approve a v2 full-stat selected-rate convergence/resource plan, or accept NO_RATE_AUTHORITY endpoint.",
        "user_decision_required": True,
    }
    write_json(SUMMARY_JSON, summary)
    write_summary_md(summary)
    update_decision_log(status)
    print(json.dumps({"status": status, "summary": rel(SUMMARY_JSON), "decision": rel(DECISION_JSON)}, indent=2))


if __name__ == "__main__":
    main()
