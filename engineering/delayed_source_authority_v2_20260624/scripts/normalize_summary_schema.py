#!/usr/bin/env python3
"""Normalize WP summary.json files to the harness-required schema."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


PHASE_DIR = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
AUDIT_PATH = PHASE_DIR / "00_manifest/summary_schema_audit.json"

REQUIRED_KEYS = [
    "status",
    "inputs",
    "outputs",
    "findings",
    "claim_impact",
    "next_gate",
    "user_decision_required",
]

DEFAULTS_BY_WP = {
    "03_source_semantics": {
        "inputs": [
            "/home/ubuntu/MEGAlib_Install/megalib-main/doc/Cosima.pdf",
            "engineering/delayed_source_authority_v2_20260624/02_rpip_alignment/summary.json",
        ],
        "claim_impact": [
            "ParticleType-only delayed source cards are insufficient for v2 state-resolved claims.",
            "EventList and native ActivationSources semantics are the only supported transport paths tested here.",
        ],
    },
    "04_custom_source_v2": {
        "inputs": [
            "engineering/delayed_source_authority_v2_20260624/01_raw_inventory/raw_inventory_ledger.csv",
            "engineering/delayed_source_authority_v2_20260624/02_rpip_alignment/rpip_alignment.csv",
            "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup",
        ],
        "claim_impact": [
            "Custom source-v2 EventList inventory is available for diagnostic transport.",
            "No delayed selected-rate claim is made at source-build stage.",
        ],
    },
    "05_native_activation": {
        "inputs": [
            "engineering/delayed_source_authority_v2_20260624/04_custom_source_v2/source_v2_native_activity_store_total.dat",
            "engineering/delayed_source_authority_v2_20260624/04_custom_source_v2/source_v2_manifest.json",
            "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup",
        ],
        "claim_impact": [
            "Native activation oracle is usable as an explained-model diagnostic.",
            "Native and custom models are not interchangeable selected-rate authorities without promotion evidence.",
        ],
    },
    "06_time_constant": {
        "inputs": [
            "engineering/delayed_source_authority_v2_20260624/05_native_activation/native_activation_oracle_summary.json",
            "engineering/delayed_source_authority_v2_20260624/05_native_activation/tag_aware_native_vs_direct_comparison.json",
        ],
        "claim_impact": [
            "DetectorTimeConstant handling is stable for the audited delayed-source boundary.",
            "Timing audit alone does not authorize v2 rate promotion.",
        ],
    },
    "07_transport": {
        "inputs": [
            "engineering/delayed_source_authority_v2_20260624/07_transport/pilot_inputs/v2_eventlist_pilot1000.source",
            "engineering/delayed_source_authority_v2_20260624/07_transport/pilot_inputs/native_activation_sources_pilot1000.source",
            "engineering/delayed_source_authority_v2_20260624/07_transport/pilot_inputs/legacy_l0_pilot1000.source",
            "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup",
        ],
        "claim_impact": [
            "Pilot transport is diagnostic only.",
            "No full-stat v2 delayed selected-rate authority or manuscript number is promoted.",
        ],
    },
}


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def missing_keys(data: dict) -> list[str]:
    return [key for key in REQUIRED_KEYS if key not in data]


def ordered_summary(data: dict) -> dict:
    ordered = {key: data[key] for key in REQUIRED_KEYS}
    for key, value in data.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def normalize_summary(path: Path) -> tuple[list[str], list[str], bool]:
    data = json.loads(path.read_text(encoding="utf-8"))
    before = missing_keys(data)
    wp_key = path.parent.name
    defaults = DEFAULTS_BY_WP.get(wp_key, {})
    for key in REQUIRED_KEYS:
        if key in data:
            continue
        if key in defaults:
            data[key] = defaults[key]
        elif key in {"inputs", "outputs", "findings", "claim_impact"}:
            data[key] = []
        elif key == "status":
            data[key] = "NOT_RUN"
        elif key == "next_gate":
            data[key] = ""
        elif key == "user_decision_required":
            data[key] = False
    after = missing_keys(data)
    changed = bool(before)
    if changed:
        path.write_text(json.dumps(ordered_summary(data), indent=2) + "\n", encoding="utf-8")
    return before, after, changed


def append_manifest_output() -> None:
    summary_path = PHASE_DIR / "00_manifest/summary.json"
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    outputs = data.setdefault("outputs", [])
    audit_rel = rel(AUDIT_PATH)
    if audit_rel not in outputs:
        outputs.append(audit_rel)
    findings = data.setdefault("findings", [])
    finding = "Harness summary schema audit completed with zero missing required keys after normalization."
    if finding not in findings:
        findings.append(finding)
    summary_path.write_text(json.dumps(ordered_summary(data), indent=2) + "\n", encoding="utf-8")


def main() -> None:
    summary_paths = sorted(PHASE_DIR.glob("[0-9][0-9]*/summary.json"))
    before_rows = []
    after_rows = []
    changed_paths = []
    for path in summary_paths:
        before, after, changed = normalize_summary(path)
        if before:
            before_rows.append({"path": rel(path), "missing": before})
        if after:
            after_rows.append({"path": rel(path), "missing": after})
        if changed:
            changed_paths.append(rel(path))

    append_manifest_output()

    final_missing = []
    for path in summary_paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        missing = missing_keys(data)
        if missing:
            final_missing.append({"path": rel(path), "missing": missing})

    audit = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "required_keys": REQUIRED_KEYS,
        "checked_count": len(summary_paths),
        "changed": changed_paths,
        "missing_before": before_rows,
        "missing_after_initial_pass": after_rows,
        "missing_after_manifest_update": final_missing,
        "status": "PASS" if not final_missing else "FAIL",
    }
    AUDIT_PATH.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": audit["status"], "changed_count": len(changed_paths), "missing_count": len(final_missing)}, indent=2))


if __name__ == "__main__":
    main()
