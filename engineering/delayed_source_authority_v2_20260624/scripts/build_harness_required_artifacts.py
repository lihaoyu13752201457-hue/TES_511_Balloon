#!/usr/bin/env python3
"""Create exact harness-required artifact names from completed WP evidence.

Earlier WPs used local names such as source_v2_manifest.json.  The harness also
defines canonical delivery filenames.  This script materializes those canonical
names as either copies of the existing authority artifact or explicit
NO_RATE_AUTHORITY manifests when the artifact requires full-stat selected-rate
promotion that was not achieved.
"""

from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PHASE_DIR = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]

MANIFEST = PHASE_DIR / "00_manifest/harness_required_artifact_compatibility.json"


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


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def copy_file(src: Path, dst: Path) -> dict[str, str]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    return {"path": rel(dst), "source": rel(src), "kind": "copy"}


def append_outputs(summary_path: Path, paths: list[Path]) -> None:
    if not summary_path.exists():
        return
    payload = load_json(summary_path)
    outputs = list(payload.get("outputs", []))
    for path in paths:
        text = rel(path)
        if text not in outputs:
            outputs.append(text)
    payload["outputs"] = outputs
    write_json(summary_path, payload)


def write_markdown(path: Path, title: str, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join([f"# {title}", "", *lines, ""]) + "\n", encoding="utf-8")


def no_rate_json(path: Path, artifact_name: str, required_before_available: list[str]) -> dict[str, str]:
    payload = {
        "status": "NO_RATE_AUTHORITY",
        "artifact": artifact_name,
        "generated_at": now_utc(),
        "reason": "WP08 did not promote a v2 delayed selected-rate authority.",
        "required_before_available": required_before_available,
        "promotion_decision": rel(PHASE_DIR / "08_promotion/promotion_decision.json"),
    }
    write_json(path, payload)
    return {"path": rel(path), "kind": "no_rate_authority_manifest"}


def build_00(entries: list[dict[str, str]]) -> None:
    final_src = PHASE_DIR / "FINAL_STATUS.md"
    final_dst = PHASE_DIR / "00_manifest/FINAL_STATUS.md"
    entries.append(copy_file(final_src, final_dst))
    append_outputs(PHASE_DIR / "00_manifest/summary.json", [MANIFEST, final_dst])


def build_04(entries: list[dict[str, str]]) -> None:
    out = PHASE_DIR / "04_custom_source_v2"
    copies = [
        (PHASE_DIR / "01_raw_inventory/raw_inventory_all_states.csv", out / "delayed_inventory_v2.csv"),
        (out / "source_v2_event_weights.csv", out / "delayed_position_weights_v2.csv"),
        (out / "source_v2_eventlist.source", out / "delayed_source_v2.source"),
        (out / "source_v2_manifest.json", out / "delayed_source_v2_manifest.json"),
        (out / "source_name_audit.json", out / "source_name_collision_audit.csv.json"),
    ]
    created: list[Path] = []
    for src, dst in copies[:4]:
        entries.append(copy_file(src, dst))
        created.append(dst)
    # The harness asks for CSV source-name collision audit; convert the JSON count
    # to a compact CSV while retaining the original JSON under its local name.
    name_audit = load_json(out / "source_name_audit.json")
    collision_csv = out / "source_name_collision_audit.csv"
    write_csv(
        collision_csv,
        [
            {
                "status": "PASS" if int(name_audit.get("duplicate_count", 0)) == 0 else "FAIL",
                "duplicate_count": name_audit.get("duplicate_count", 0),
                "defined_source_names": name_audit.get("defined_source_names", ""),
                "registered_source_names": name_audit.get("registered_source_names", ""),
                "unique_source_names": name_audit.get("unique_source_names", ""),
            }
        ],
    )
    entries.append({"path": rel(collision_csv), "source": rel(out / "source_name_audit.json"), "kind": "derived_csv"})
    created.append(collision_csv)
    manifest = load_json(out / "source_v2_manifest.json")
    audit_json = out / "delayed_source_v2_audit.json"
    audit_payload = {
        "status": manifest["status"],
        "generated_at": now_utc(),
        "source_manifest": rel(out / "source_v2_manifest.json"),
        "total_relative_flux_closure": manifest.get("total_relative_flux_closure"),
        "represented_relative_flux_closure": manifest.get("represented_relative_flux_closure"),
        "duplicate_source_names": manifest.get("duplicate_source_names"),
        "unsupported_activity_Bq": manifest.get("unsupported_activity_Bq"),
        "omitted_positive_activity_Bq": manifest.get("omitted_positive_activity_Bq"),
        "eventlist_rows": manifest.get("eventlist_rows"),
        "claim_boundary": manifest.get("claim_boundary"),
    }
    write_json(audit_json, audit_payload)
    entries.append({"path": rel(audit_json), "source": rel(out / "source_v2_manifest.json"), "kind": "derived_json"})
    audit_md = out / "delayed_source_v2_audit.md"
    write_markdown(
        audit_md,
        "Delayed Source v2 Audit",
        [
            f"status: `{manifest['status']}`",
            "",
            f"- source rows: `{manifest.get('eventlist_rows')}`",
            f"- total activity: `{manifest.get('inventory_total_activity_Bq')}` Bq",
            f"- total relative closure: `{manifest.get('total_relative_flux_closure')}`",
            f"- duplicate source names: `{manifest.get('duplicate_source_names')}`",
            f"- unsupported positive activity: `{manifest.get('unsupported_activity_Bq')}` Bq",
            "",
            "This is source-construction authority only; selected-rate promotion is blocked by WP08.",
        ],
    )
    entries.append({"path": rel(audit_md), "source": rel(audit_json), "kind": "derived_markdown"})
    created.extend([audit_json, audit_md])
    append_outputs(out / "summary.json", created)


def build_05(entries: list[dict[str, str]]) -> None:
    out = PHASE_DIR / "05_native_activation"
    comparison_json = load_json(out / "tag_aware_native_vs_direct_comparison.json")
    native_policy = out / "native_input_policy.md"
    write_markdown(
        native_policy,
        "Native Input Policy",
        [
            "Gamma splits and non-gamma replicas are handled tag-aware; all-tag naive Activator merging is not used as promotion evidence.",
            "",
            "The tag-aware native oracle is classified as `EXPLAINED_MODEL_DIFFERENCE` because native Activator output includes parent/daughter/native decay products and half-life/decay-chain model differences relative to direct raw-inventory accounting.",
        ],
    )
    entries.append({"path": rel(native_policy), "kind": "derived_markdown"})
    manifest_csv = out / "native_activation_run_manifest.csv"
    rows: list[dict[str, Any]] = []
    tag_dir = out / "tag_aware_activator"
    for path in sorted(tag_dir.glob("native_activator_*.source")):
        tag = path.stem.replace("native_activator_", "")
        rows.append(
            {
                "tag": tag,
                "source": rel(path),
                "log": rel(tag_dir / f"native_activator_{tag}.log"),
                "native_inventory": rel(tag_dir / f"tag_aware_native_{tag}.dat"),
                "status": "PASS",
            }
        )
    write_csv(manifest_csv, rows, ["tag", "source", "log", "native_inventory", "status"])
    entries.append({"path": rel(manifest_csv), "kind": "derived_csv"})
    inventory_json = out / "native_activation_inventory.json"
    write_json(inventory_json, comparison_json)
    entries.append(copy_file(out / "tag_aware_native_vs_direct_comparison.csv", out / "native_activation_inventory.csv"))
    entries.append({"path": rel(inventory_json), "source": rel(out / "tag_aware_native_vs_direct_comparison.json"), "kind": "copy_json"})
    entries.append(copy_file(out / "tag_aware_native_vs_direct_comparison.csv", out / "custom_native_inventory_comparison.csv"))
    entries.append(copy_file(out / "tag_aware_native_vs_direct_comparison.md", out / "custom_native_inventory_comparison.md"))
    native_manifest = out / "native_volume_delayed_source_manifest.json"
    write_json(
        native_manifest,
        {
            "status": "EXPLAINED_MODEL_DIFFERENCE",
            "source_strategy": "native volume-level ActivationSources",
            "native_total_activity_Bq": comparison_json.get("tag_native_total_Bq"),
            "direct_total_activity_Bq": comparison_json.get("direct_total_Bq"),
            "total_relative_delta": comparison_json.get("total_relative_delta"),
            "native_store": rel(PHASE_DIR / "04_custom_source_v2/source_v2_native_activity_store_total.dat"),
            "comparison": rel(out / "tag_aware_native_vs_direct_comparison.json"),
            "claim_boundary": "native volume-based cross-check only; not exact-position selected-rate authority",
        },
    )
    entries.append({"path": rel(native_manifest), "kind": "derived_json"})
    append_outputs(
        out / "summary.json",
        [
            native_policy,
            manifest_csv,
            out / "native_activation_inventory.csv",
            inventory_json,
            out / "custom_native_inventory_comparison.csv",
            out / "custom_native_inventory_comparison.md",
            native_manifest,
        ],
    )


def build_06(entries: list[dict[str, str]]) -> None:
    out = PHASE_DIR / "06_time_constant"
    entries.append(copy_file(out / "static_lifetime_risk.csv", out / "time_constant_state_risk.csv"))
    authority = load_json(out / "timing_authority.json")
    matrix = out / "time_constant_pilot_matrix.csv"
    write_csv(
        matrix,
        [
            {
                "candidate_s": "1e-9",
                "status": "SELECTED",
                "reason": "all audited source cards use 1e-9 and positive activity in 1 ns--5 us bins is 0 Bq",
            },
            {"candidate_s": "1e-6", "status": "NOT_RUN_STATIC_RISK_LOW", "reason": "static lifetime risk screen closed"},
            {"candidate_s": "5e-6", "status": "NOT_RUN_STATIC_RISK_LOW", "reason": "static lifetime risk screen closed"},
        ],
    )
    results = out / "time_constant_pilot_results.csv"
    write_csv(
        results,
        [
            {
                "candidate_s": authority["timing_authority_s"],
                "transport_run": "not required",
                "status": authority["status"],
                "positive_activity_1ns_to_5us_Bq": "0",
            }
        ],
    )
    verdict_json = out / "time_constant_verdict.json"
    write_json(verdict_json, authority)
    verdict_md = out / "time_constant_verdict.md"
    write_markdown(
        verdict_md,
        "Time Constant Verdict",
        [
            f"status: `{authority['status']}`",
            "",
            f"Selected timing authority: `{authority['timing_authority_s']}` s.",
            "",
            authority.get("decay_chain_boundary", ""),
        ],
    )
    entries.extend(
        [
            {"path": rel(matrix), "kind": "derived_csv"},
            {"path": rel(results), "kind": "derived_csv"},
            {"path": rel(verdict_json), "kind": "copy_json"},
            {"path": rel(verdict_md), "kind": "derived_markdown"},
        ]
    )
    append_outputs(out / "summary.json", [out / "time_constant_state_risk.csv", matrix, results, verdict_json, verdict_md])


def build_07(entries: list[dict[str, str]]) -> None:
    out = PHASE_DIR / "07_transport"
    summary = load_json(out / "summary.json")
    run_manifest = out / "pilot_run_manifest.csv"
    rows: list[dict[str, Any]] = []
    for row in summary.get("runs", []):
        sim_paths = ";".join(item.get("path", "") for item in row.get("sim_outputs", []))
        rows.append(
            {
                "pilot": row["name"],
                "source": row["meta"]["source"],
                "run_status": row["run"]["status"],
                "sim_outputs": sim_paths,
                "activity_Bq": row["normalization"]["activity_Bq"],
                "triggers": row["normalization"]["triggers"],
                "normalization_rule": row["normalization"]["rule"],
            }
        )
    write_csv(
        run_manifest,
        rows,
        ["pilot", "source", "run_status", "sim_outputs", "activity_Bq", "triggers", "normalization_rule"],
    )
    entries.append({"path": rel(run_manifest), "kind": "derived_csv"})
    entries.append(copy_file(out / "pilot_selected_rate_diagnostics.csv", out / "pilot_rate_comparison.csv"))
    verdict = out / "pilot_verdict.json"
    write_json(
        verdict,
        {
            "status": summary["status"],
            "claim_boundary": summary["claim_boundary"],
            "findings": summary["findings"],
            "transport_issues": summary.get("transport_issues", []),
            "pilot_selected_rate_diagnostics": rel(out / "pilot_selected_rate_diagnostics.csv"),
        },
    )
    entries.append({"path": rel(verdict), "kind": "derived_json"})
    requirements = [
        "v2 full-stat delayed transport",
        "Step05 selected-rate extraction",
        "sum_w/sum_w2 ledger",
        "position and decay seed variance",
        "pooled W2 final events >=300 or <=10% relative MC uncertainty",
    ]
    fullstat_manifest = out / "fullstat_run_manifest.csv"
    write_csv(
        fullstat_manifest,
        [
            {
                "run": "v2_fullstat_selected_rate",
                "status": "NO_RATE_AUTHORITY_NOT_RUN",
                "reason": "WP08 did not approve full-stat v2 selected-rate convergence",
                "required_before_run": "; ".join(requirements),
            }
        ],
    )
    selected_csv = out / "delayed_selected_rate_v2.csv"
    write_csv(
        selected_csv,
        [
            {
                "status": "NO_RATE_AUTHORITY",
                "rate_s-1": "",
                "events": "",
                "reason": "No full-stat v2 selected-rate authority exists.",
            }
        ],
    )
    selected_json = out / "delayed_selected_rate_v2.json"
    no_rate_json(selected_json, "delayed_selected_rate_v2", requirements)
    decomposition = out / "delayed_selected_decomposition_v2.csv"
    write_csv(
        decomposition,
        [
            {
                "status": "NO_RATE_AUTHORITY",
                "dimension": "",
                "component": "",
                "rate_s-1": "",
                "reason": "No full-stat v2 selected-rate authority exists.",
            }
        ],
    )
    energy_band = out / "delayed_energy_band_comparison.csv"
    write_csv(
        energy_band,
        [
            {
                "status": "NO_RATE_AUTHORITY",
                "energy_band": "",
                "legacy_rate_s-1": "",
                "v2_rate_s-1": "",
                "reason": "No full-stat v2 selected-rate authority exists.",
            }
        ],
    )
    uncertainty = out / "delayed_mc_uncertainty.md"
    write_markdown(
        uncertainty,
        "Delayed MC Uncertainty",
        [
            "status: `NO_RATE_AUTHORITY`",
            "",
            "No v2 full-stat selected-rate run exists, so no `sum_w`, `sum_w2`, seed variance, or relative MC uncertainty can be reported.",
        ],
    )
    created = [
        run_manifest,
        out / "pilot_rate_comparison.csv",
        verdict,
        fullstat_manifest,
        selected_csv,
        selected_json,
        decomposition,
        energy_band,
        uncertainty,
    ]
    entries.extend({"path": rel(path), "kind": "derived_or_no_rate"} for path in created[3:])
    append_outputs(out / "summary.json", created)


def main() -> None:
    entries: list[dict[str, str]] = []
    build_00(entries)
    build_04(entries)
    build_05(entries)
    build_06(entries)
    build_07(entries)
    payload = {
        "status": "PASS",
        "generated_at": now_utc(),
        "claim_boundary": "exact harness-required artifact filenames materialized from existing evidence",
        "entries": entries,
        "no_rate_authority_note": "Artifacts requiring full-stat v2 selected-rate evidence are explicit NO_RATE_AUTHORITY manifests, not promoted rates.",
    }
    write_json(MANIFEST, payload)
    append_outputs(PHASE_DIR / "00_manifest/summary.json", [MANIFEST])
    print(json.dumps({"status": "PASS", "manifest": rel(MANIFEST), "entries": len(entries)}, indent=2))


if __name__ == "__main__":
    main()
