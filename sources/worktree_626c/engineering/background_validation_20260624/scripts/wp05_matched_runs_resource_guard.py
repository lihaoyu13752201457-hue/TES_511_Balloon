#!/usr/bin/env python3
"""WP05/G5-G6 resource guard for matched CsI/BGO simulations.

This script prepares BGO source-card parity artifacts and stops before any
heavy transport. The full matched production matrix exceeds the HARNESS_20260624
resource guard and requires explicit approval.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
ENG = Path(__file__).resolve().parents[1]
OUT = ENG / "05_matched_runs_resource_guard"
CSI_SOURCE_DIR = ROOT / "config/megalib_sources_fullsphere20_fix5_tilt45"
BGO_SOURCE_DIR = OUT / "config_bgo_sources_fullsphere20_fix5_tilt45"
G1_AUDIT = ENG / "01_prompt_source_audit/prompt_normalization_audit.json"
G4_MANIFEST = ENG / "04_bgo_variant/bgo_geometry_manifest.json"

MAX_EVENTS_WITHOUT_APPROVAL = 5_000_000
MAX_OUTPUT_BYTES_WITHOUT_APPROVAL = 100 * 1024**3
MAX_CPU_DAYS_WITHOUT_APPROVAL = 7.0


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except Exception:
        return str(path)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def physics_source_text(text: str) -> str:
    rows = []
    for line in text.splitlines():
        if line.startswith("Geometry "):
            rows.append("Geometry <GEOMETRY_PATH>")
        elif re.match(r"^#\s*source_dir_label\s*=", line):
            rows.append("# source_dir_label = <LABEL>")
        else:
            rows.append(line)
    return "\n".join(rows) + "\n"


def parse_flux_sum(text: str) -> float:
    total = 0.0
    for line in text.splitlines():
        m = re.match(r"^\S+\.Flux\s+([-+0-9.eE]+)\s*$", line.strip())
        if m:
            total += float(m.group(1))
    return total


def build_bgo_source_cards(bgo_setup: Path) -> list[dict[str, Any]]:
    BGO_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for csi_path in sorted(CSI_SOURCE_DIR.glob("Background_*_fullsphere20.source")):
        text = csi_path.read_text(encoding="utf-8", errors="replace")
        out_lines = []
        for line in text.splitlines():
            if line.startswith("Geometry "):
                out_lines.append(f"Geometry {bgo_setup.resolve()}")
            elif re.match(r"^#\s*source_dir_label\s*=", line):
                out_lines.append("# source_dir_label = fix5_bgo_same_envelope_resource_guard")
            else:
                out_lines.append(line)
        bgo_path = BGO_SOURCE_DIR / csi_path.name
        bgo_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
        csi_text = csi_path.read_text(encoding="utf-8", errors="replace")
        bgo_text = bgo_path.read_text(encoding="utf-8", errors="replace")
        rows.append(
            {
                "particle": csi_path.name.removeprefix("Background_").removesuffix("_fullsphere20.source"),
                "csi_source": rel(csi_path),
                "bgo_source": rel(bgo_path),
                "csi_sha256": sha256(csi_path),
                "bgo_sha256": sha256(bgo_path),
                "physics_source_hash_equal_excluding_geometry": sha256_text(physics_source_text(csi_text))
                == sha256_text(physics_source_text(bgo_text)),
                "csi_flux_sum_cm2_s": parse_flux_sum(csi_text),
                "bgo_flux_sum_cm2_s": parse_flux_sum(bgo_text),
                "geometry_line_points_to_bgo": f"Geometry {bgo_setup.resolve()}" in bgo_text,
            }
        )
    return rows


def copy_run_manifest_inputs() -> dict[str, Any]:
    g1 = load_json(G1_AUDIT)
    run_manifest = g1["run_manifest"]
    generated_by_particle = {particle: int(value) for particle, value in sorted(run_manifest["generated_by_particle"].items())}
    return {
        "farfield_radius_cm": g1["farfield"]["radii"]["setup_surrounding_sphere_cm"],
        "generated_by_particle": generated_by_particle,
        "total_prompt_events_per_mode": sum(generated_by_particle.values()),
        "gamma_events": generated_by_particle.get("gamma", 0),
        "gamma_splits": int(run_manifest["gamma_splits"]),
        "non_gamma_replicas": int(run_manifest["non_gamma_replicas"]),
    }


def build() -> dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    g4 = load_json(G4_MANIFEST)
    bgo_setup = ROOT / g4["outputs"]["derived_setup"]
    source_rows = build_bgo_source_cards(bgo_setup)
    write_csv(OUT / "bgo_source_card_manifest.csv", source_rows)

    matrix = copy_run_manifest_inputs()
    per_variant_prompt_buildup_events = 2 * int(matrix["total_prompt_events_per_mode"])
    matched_two_variant_prompt_buildup_events = 2 * per_variant_prompt_buildup_events
    max_single_launch = max(int(matrix["gamma_events"]), int(matrix["total_prompt_events_per_mode"]))
    p2_guard_exceeded = max_single_launch > MAX_EVENTS_WITHOUT_APPROVAL or matched_two_variant_prompt_buildup_events > MAX_EVENTS_WITHOUT_APPROVAL
    physics_hash_equal = all(bool(row["physics_source_hash_equal_excluding_geometry"]) for row in source_rows)
    flux_equal = all(abs(float(row["csi_flux_sum_cm2_s"]) - float(row["bgo_flux_sum_cm2_s"])) <= 1.0e-15 for row in source_rows)
    bgo_geometry_ok = all(bool(row["geometry_line_points_to_bgo"]) for row in source_rows)
    status = "BLOCKED_RESOURCE_APPROVAL" if p2_guard_exceeded else "READY_FOR_MATCHED_P0"

    payload = {
        "artifact_type": "wp05_matched_runs_resource_guard",
        "status": status,
        "created_utc": now_utc(),
        "inputs": {
            "g1_prompt_normalization_audit": rel(G1_AUDIT),
            "g4_bgo_geometry_manifest": rel(G4_MANIFEST),
            "csi_source_dir": rel(CSI_SOURCE_DIR),
        },
        "derived_sources": {
            "bgo_source_dir": rel(BGO_SOURCE_DIR),
            "manifest_csv": rel(OUT / "bgo_source_card_manifest.csv"),
            "source_card_count": len(source_rows),
            "physics_source_hash_equal_excluding_geometry": physics_hash_equal,
            "flux_sums_equal": flux_equal,
            "all_geometry_lines_point_to_bgo_setup": bgo_geometry_ok,
        },
        "matched_matrix": {
            **matrix,
            "per_variant_prompt_plus_buildup_events": per_variant_prompt_buildup_events,
            "two_variant_prompt_plus_buildup_events": matched_two_variant_prompt_buildup_events,
            "delayed_decays_per_fullstat_variant_nominal": 1_000_000,
            "position_sample_M": 50_000,
            "common_random_seed_policy": {
                "prompt_instant": "reuse fix5 fullstat seed matrix",
                "activation_buildup": "reuse fix5 fullstat seed matrix",
                "position_sampling": "use existing seed 260613 first; PI-02 seeds 260614/260615/260617 for convergence if approved",
                "delayed_transport": "same seed tags as position sampling for paired audit",
                "science_replay": "reuse fix5 focused signal source pattern with BGO setup",
            },
        },
        "resource_guard": {
            "max_events_without_approval_per_launch_batch": MAX_EVENTS_WITHOUT_APPROVAL,
            "max_estimated_output_without_approval_bytes": MAX_OUTPUT_BYTES_WITHOUT_APPROVAL,
            "max_estimated_cpu_without_approval_cpu_days": MAX_CPU_DAYS_WITHOUT_APPROVAL,
            "max_single_existing_fullstat_launch_events": max_single_launch,
            "full_matched_production_exceeds_event_guard": p2_guard_exceeded,
        },
        "requested_approval": {
            "needed": p2_guard_exceeded,
            "minimum_to_continue": "Approve a staged matched CsI/BGO run plan. Recommended next approved action is P0/P1 only, not full P2 production.",
            "recommended_first_batch": {
                "stage": "P0 syntax/geometry smoke",
                "gamma_events": 1000,
                "gamma_splits": 1,
                "non_gamma_replicas": 1,
                "delayed_decays": 1000,
                "purpose": "parser/syntax/isotope-store sanity only; no material conclusion",
            },
            "full_p2_requires_separate_approval": True,
        },
        "failure_contract": {
            "status": status,
            "evidence": [
                rel(OUT / "bgo_source_card_manifest.csv"),
                rel(OUT / "matched_run_resource_plan.json"),
                rel(OUT / "RESOURCE_APPROVAL_REQUIRED.md"),
                rel(G1_AUDIT),
                rel(G4_MANIFEST),
            ],
            "affected_claim": (
                "No CsI/BGO material-comparison rate, ratio, uncertainty, or design preference can be claimed "
                "until matched CsI/BGO transport and identical Step05 selection are run."
            ),
            "minimal_next_action": "Approve and run the staged P0 syntax/geometry smoke batch, then review P0 before any P1/P2 escalation.",
            "requires_user_decision": p2_guard_exceeded,
            "unexecuted_phases": [
                "WP05 P0/P1/P2 matched prompt instant transport",
                "WP05 matched activation buildup transport",
                "WP05 matched delayed source and delayed decay transport",
                "WP05 matched focused science replay",
                "WP06 CsI/BGO comparison",
            ],
        },
        "outputs": {
            "summary_json": rel(OUT / "summary.json"),
            "summary_md": rel(OUT / "summary.md"),
            "resource_approval_required_md": rel(OUT / "RESOURCE_APPROVAL_REQUIRED.md"),
        },
        "problems": [] if status == "BLOCKED_RESOURCE_APPROVAL" else [],
    }
    if not (physics_hash_equal and flux_equal and bgo_geometry_ok):
        payload["status"] = "FAIL_SELECTION_PARITY"
        payload["problems"] = []
        if not physics_hash_equal:
            payload["problems"].append("physics_source_hash_mismatch")
        if not flux_equal:
            payload["problems"].append("flux_sum_mismatch")
        if not bgo_geometry_ok:
            payload["problems"].append("bgo_geometry_line_missing")

    write_json(OUT / "matched_run_resource_plan.json", payload)
    write_json(OUT / "summary.json", payload)
    md = markdown(payload)
    (OUT / "summary.md").write_text(md, encoding="utf-8")
    (OUT / "RESOURCE_APPROVAL_REQUIRED.md").write_text(resource_approval_md(payload), encoding="utf-8")
    return payload


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# WP05 Matched CsI/BGO Resource Guard",
        "",
        f"Status: `{payload['status']}`.",
        "",
        f"BGO source cards: `{payload['derived_sources']['source_card_count']}`.",
        f"Physics source hash equal excluding geometry: `{payload['derived_sources']['physics_source_hash_equal_excluding_geometry']}`.",
        f"Flux sums equal: `{payload['derived_sources']['flux_sums_equal']}`.",
        f"Full matched production exceeds event guard: `{payload['resource_guard']['full_matched_production_exceeds_event_guard']}`.",
        "",
        "Failure contract:",
        f"- affected claim: {payload['failure_contract']['affected_claim']}",
        f"- minimal next action: {payload['failure_contract']['minimal_next_action']}",
        f"- requires user decision: `{payload['failure_contract']['requires_user_decision']}`",
        "",
        "Outputs:",
        f"- BGO source manifest: `{payload['derived_sources']['manifest_csv']}`",
        f"- approval request: `{payload['outputs']['resource_approval_required_md']}`",
    ]
    return "\n".join(lines) + "\n"


def resource_approval_md(payload: dict[str, Any]) -> str:
    m = payload["matched_matrix"]
    g = payload["resource_guard"]
    return "\n".join(
        [
            "# RESOURCE_APPROVAL_REQUIRED",
            "",
            "Status: `BLOCKED_RESOURCE_APPROVAL`.",
            "",
            "The BGO same-envelope geometry and BGO source cards are ready, but matched production must not start without approval.",
            "",
            f"- fullstat gamma events per variant: `{m['gamma_events']}`",
            f"- prompt+buildup events per variant: `{m['per_variant_prompt_plus_buildup_events']}`",
            f"- prompt+buildup events for CsI+BGO: `{m['two_variant_prompt_plus_buildup_events']}`",
            f"- event guard per launch batch: `{g['max_events_without_approval_per_launch_batch']}`",
            "",
            "## Failure Contract",
            "",
            f"- affected claim: {payload['failure_contract']['affected_claim']}",
            f"- minimal next action: {payload['failure_contract']['minimal_next_action']}",
            f"- requires user decision: `{payload['failure_contract']['requires_user_decision']}`",
            "- unexecuted phases:",
            *[f"  - {phase}" for phase in payload["failure_contract"]["unexecuted_phases"]],
            "",
            "Evidence:",
            *[f"- `{item}`" for item in payload["failure_contract"]["evidence"]],
            "",
            "Recommended next approved batch:",
            "- P0 syntax/geometry smoke only",
            "- gamma_events=1000, gamma_splits=1, non_gamma_replicas=1",
            "- delayed_decays=1000",
            "- no rate/material conclusion from P0",
            "",
            "Full P2 production requires a separate explicit approval after P0/P1 evidence.",
            "",
        ]
    )


def main() -> int:
    payload = build()
    print(
        json.dumps(
            {
                "status": payload["status"],
                "bgo_source_dir": payload["derived_sources"]["bgo_source_dir"],
                "approval_required": payload["requested_approval"]["needed"],
                "out": payload["outputs"]["summary_json"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if payload["status"] in {"BLOCKED_RESOURCE_APPROVAL", "READY_FOR_MATCHED_P0"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
