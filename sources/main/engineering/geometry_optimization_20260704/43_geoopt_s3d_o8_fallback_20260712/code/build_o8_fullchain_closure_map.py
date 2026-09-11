#!/usr/bin/env python3
"""Write the explicit O8 screening-to-Step08 path and gate contract."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _o8_promotion_gate import audit_screening_promotion
from _o8_replay_common import PACKAGE, ROOT, S3D_GEOMETRY_SETUP, rel, sha256


OUT_JSON = PACKAGE / "data/s3d_o8_fullchain_closure_map.json"
OUT_MD = PACKAGE / "FULLCHAIN_CLOSURE_MAP.md"
DELAY_RUNNER = PACKAGE / "code/run_o8_delayed_activation.py"
CLOSURE_RUNNER = PACKAGE / "code/run_o8_step05_08_closure.py"
PROMOTION_HELPER = PACKAGE / "code/_o8_promotion_gate.py"
SHARED_DELAY = (
    ROOT
    / "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712"
    / "code/run_s3d_delayed_activation.py"
)
SHARED_CLOSURE = (
    ROOT
    / "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712"
    / "code/run_s3d_step05_08_closure.py"
)


def now_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def item(path: str) -> dict[str, Any]:
    full = ROOT / path
    return {"path": path, "exists": full.exists()}


def build() -> dict[str, Any]:
    promotion = audit_screening_promotion()
    stages = [
        {
            "order": 0,
            "stage": "screening_promotion",
            "role": "mandatory matched heavy-control/O8 promotion gate before any full-chain production",
            "inputs": [
                "engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/data/s3d_o8_screening_analysis.json"
            ],
            "outputs": [],
            "gate": (
                "status=PASS_O8_SCREENING_PROMOTION_GATES; dominant_subset and "
                "signal evaluation_status=PASS and promotion_gate_pass=true; all "
                "required gates evaluated; no pending inputs or audit failures"
            ),
        },
        {
            "order": 1,
            "stage": "geometry",
            "role": "single O8 geometry authority for every generated source and SIM header",
            "inputs": [],
            "outputs": [
                rel(S3D_GEOMETRY_SETUP),
                rel(PACKAGE / "data/s3d_o8_geometry_manifest.json"),
                rel(PACKAGE / "data/s3d_o8_independent_geometry_validation.json"),
                rel(PACKAGE / "data/cosima_overlap_s3d_o8_summary.json"),
            ],
            "gate": "static diff, independent validation, overlap/load, and frozen hashes all PASS",
        },
        {
            "order": 2,
            "stage": "prompt_all8",
            "role": "paper-grade prompt background; the 16-job e+/n screening run is not accepted",
            "inputs": [
                rel(PACKAGE / "config/full_prompt_all8/source_cards/source_migration_manifest.json")
            ],
            "outputs": [
                "runs/geometry_optimization_20260704/s3d_o8_fullstat_prompt_all8_20260712/normalization.json",
                "runs/geometry_optimization_20260704/s3d_o8_fullstat_prompt_all8_20260712/run_summary.json",
            ],
            "statistics": "68 jobs: gamma 10M in 12 splits; alpha/e-/e+/mu-/mu+/n/p each 8 replicas",
            "gate": "68 PASS/SKIP; generated=requested; one positive TT/file; every source and SIM geometry exact",
        },
        {
            "order": 3,
            "stage": "neutron_buildup",
            "role": "eight-replica neutron ActivationBuildUp authority",
            "inputs": [
                rel(PACKAGE / "config/full_prompt_all8/source_cards/source_migration_manifest.json")
            ],
            "outputs": [
                "runs/geometry_optimization_20260704/step02_buildup_s3d_o8_neutron_delayed_m50000_20260712/run_summary.json"
            ],
            "statistics": "8 neutron replicas; exactly one TT record per replica",
            "gate": "8 PASS/SKIP, generated=requested, ActivationBuildUp source and SIM geometry exact",
        },
        {
            "order": 4,
            "stage": "nubase_exact_position_source",
            "role": "neutron-only corrected inventory and exact-position delayed source",
            "inputs": [
                "runs/geometry_optimization_20260704/step02_buildup_s3d_o8_neutron_delayed_m50000_20260712/run_summary.json",
                "inputs/nubase/nubase_2020.txt",
            ],
            "outputs": [
                "runs/geometry_optimization_20260704/step02_delay_fix_s3d_o8_neutron_delayed_m50000_20260712/normalization_audit_groundstate_fix.json",
                "runs/geometry_optimization_20260704/step02_delay_exactpos_s3d_o8_neutron_delayed_m50000_20260712/activation_decay_day15_groundstate_fixed_exactpos_m50000.source",
                rel(PACKAGE / "fullchain/delayed_source/delayed_source_exactpos_summary.json"),
            ],
            "statistics": "TT/8; N_SAMPLE=2,000,000; raw triggers=1,000,000; M=50,000; seed=260613",
            "gate": "NUBASE ground-state correction PASS, family TT guard exactly 8/8, source/inventory and exact-position provenance PASS",
        },
        {
            "order": 5,
            "stage": "delayed_transport",
            "role": "one-million-event O8 neutron-only delayed transport",
            "inputs": [
                "runs/geometry_optimization_20260704/step02_delay_exactpos_s3d_o8_neutron_delayed_m50000_20260712/activation_decay_day15_groundstate_fixed_exactpos_m50000.source"
            ],
            "outputs": [
                "runs/geometry_optimization_20260704/step02_delayed_transport_s3d_o8_neutron_delayed_m50000_20260712/DelayedDecayS3dO8NeutronM50000.inc1.id1.sim.gz",
                rel(PACKAGE / "data/s3d_o8_delayed_activation_campaign.json"),
            ],
            "statistics": "SE=ID=1,000,000; explicit seed 260613",
            "gate": "source and SIM geometry exact, source-flux closure PASS, SE=ID=1M",
        },
        {
            "order": 6,
            "stage": "matched_sidecar_and_signal",
            "role": "screening-produced atmospheric-line and focused-signal authorities consumed read-only",
            "inputs": [
                rel(PACKAGE / "data/s3d_o8_atm511_replay_summary.json"),
                rel(PACKAGE / "data/s3d_o8_signal_replay_summary.json"),
            ],
            "outputs": [],
            "gate": "atm511 SE=ID=3M and signal SE=ID=37,194; exact O8 geometry; frozen 50-keV analysis policy",
        },
        {
            "order": 7,
            "stage": "step05",
            "role": "merge all-eight prompt, neutron delayed, atmospheric-511, and geometry-local signal",
            "inputs": [
                "runs/geometry_optimization_20260704/s3d_o8_fullstat_prompt_all8_20260712/run_summary.json",
                rel(PACKAGE / "fullchain/delayed_source/delayed_source_exactpos_summary.json"),
                rel(PACKAGE / "data/s3d_o8_atm511_replay_summary.json"),
                rel(PACKAGE / "data/s3d_o8_signal_replay_summary.json"),
            ],
            "outputs": [
                rel(PACKAGE / "fullchain/step05/step05_s3d_o8_fullchain_l1_response_summary.json")
            ],
            "gate": "per-family 1/sum(TT), 50-keV analysis veto, native 80-keV threshold disclosed, no pending stream substituted by zero",
        },
        {
            "order": 8,
            "stage": "step06_step07_step08",
            "role": "separate mission scalings, source-case authority, and 20-day counting projection",
            "inputs": [
                rel(PACKAGE / "fullchain/step05/step05_s3d_o8_fullchain_l1_response_summary.json")
            ],
            "outputs": [
                rel(PACKAGE / "fullchain/step06/step06_s3d_o8_fullchain_summary.json"),
                rel(PACKAGE / "fullchain/step07/source_case_summary.json"),
                rel(PACKAGE / "fullchain/step08/step08_s3d_o8_fullchain_time_dependent_summary.json"),
            ],
            "gate": "prompt/delayed/science/atmospheric scales remain separate; atmospheric occupancy included; central and conservative-95 results reported",
        },
    ]

    for stage in stages:
        stage["input_state"] = [item(path) for path in stage.get("inputs", [])]
        stage["output_state"] = [item(path) for path in stage.get("outputs", [])]

    delay = rel(DELAY_RUNNER)
    closure = rel(CLOSURE_RUNNER)
    commands = [
        {
            "purpose": "safe source/job preparation only",
            "command": f"python3 {delay} prepare --workers 1",
            "launches_cosima": False,
        },
        {
            "purpose": "all-eight prompt transport after final screening PASS",
            "command": f"python3 {delay} run-full-prompt --workers 8 --allow-heavy-run --confirm RUN_O8_FULL_PROMPT_ALL8",
            "launches_cosima": True,
        },
        {
            "purpose": "assemble neutron instant provenance from completed all-eight prompt",
            "command": f"python3 {delay} assemble-instant",
            "launches_cosima": False,
        },
        {
            "purpose": "neutron buildup transport after final screening PASS",
            "command": f"python3 {delay} run-buildup --workers 8 --allow-heavy-run --confirm RUN_O8_NEUTRON_BUILDUP",
            "launches_cosima": True,
        },
        {
            "purpose": "NUBASE correction and exact-position M=50,000 source build",
            "command": f"python3 {delay} prepare-delay --workers 8 --allow-heavy-run --confirm BUILD_O8_DELAYED_SOURCE_M50000",
            "launches_cosima": False,
        },
        {
            "purpose": "one-million-event delayed transport after final screening PASS",
            "command": f"python3 {delay} run-delay --allow-heavy-run --confirm RUN_O8_DELAYED_TRANSPORT_1M",
            "launches_cosima": True,
        },
        {
            "purpose": "fail-closed Step05-Step08 preflight",
            "command": f"python3 {closure} preflight",
            "launches_cosima": False,
        },
        {
            "purpose": "pure-function and path-binding self-test",
            "command": f"python3 {closure} self-test",
            "launches_cosima": False,
        },
        {
            "purpose": "dedicated postprocessing only after every gate PASS",
            "command": f"python3 {closure} all --workers 8 --allow-closure-run --confirm RUN_O8_STEP05_08_CLOSURE",
            "launches_cosima": False,
        },
    ]

    status = (
        "PASS_O8_FULLCHAIN_PATH_CONTRACT_READY_TO_LAUNCH"
        if promotion["status"] == "PASS_SCREENING_PROMOTION_GATE"
        else "PASS_O8_FULLCHAIN_PATH_CONTRACT_PENDING_SCREENING_GATE"
    )
    return {
        "status": status,
        "generated_at_utc": now_utc(),
        "screening_promotion": promotion,
        "geometry_setup": rel(S3D_GEOMETRY_SETUP),
        "claim_scope": "audited path/gate contract and prepared job cards; no new transport result",
        "stages": stages,
        "commands": commands,
        "implementation_authority": {
            "promotion_gate": {
                "path": rel(PROMOTION_HELPER),
                "sha256": sha256(PROMOTION_HELPER),
            },
            "o8_delayed_runner": {
                "path": delay,
                "sha256": sha256(DELAY_RUNNER),
            },
            "o8_closure_runner": {
                "path": closure,
                "sha256": sha256(CLOSURE_RUNNER),
            },
            "reviewed_shared_algorithms": [
                {"path": rel(SHARED_DELAY), "sha256": sha256(SHARED_DELAY)},
                {"path": rel(SHARED_CLOSURE), "sha256": sha256(SHARED_CLOSURE)},
            ],
            "reuse_boundary": "package 42 supplies reviewed algorithms only; all mutable O8 bindings are package-local and fail-closed audited",
        },
        "resources": {
            "measured_analogs": {
                "all8_prompt_disk": "about 6.7 GB",
                "neutron_buildup_disk": "about 4.0 GB",
                "delayed_1m_disk": "about 0.78 GB",
            },
            "minimum_free_space_before_launch_gb": 20,
            "worker_guidance": "8 transport workers after checking concurrent Cosima/RAM pressure",
        },
        "hard_boundaries": [
            "No full-chain production is authorized until the final O8 screening JSON and every required promotion gate are PASS.",
            "The completed O9 campaign is implementation context only and cannot satisfy the O8 screening gate.",
            "The 16-job e+/n screen is never accepted as all-eight prompt authority.",
            "Delayed activation is neutron-only, uses NUBASE ground-state correction and the eight-file TT division guard, and is not a full-particle inventory.",
            "Exact-position sampling is M=50,000 with source/inventory/RPIP provenance; visually plausible sources are not accepted.",
            "Every source and SIM header must resolve to the package-43 O8 geometry.",
            "No package-42, screening-run, retained mainline, or central stepwise product is overwritten.",
        ],
    }


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# O8 full-chain closure map",
        "",
        f"Status: `{payload['status']}`",
        "",
        f"Screening promotion: `{payload['screening_promotion']['status']}`",
        "",
        "This is a path and gate contract. Prepared source/job cards are not transport evidence, and PENDING is never converted to zero.",
        "",
        "| order | stage | role | gate |",
        "| ---: | --- | --- | --- |",
    ]
    for stage in payload["stages"]:
        lines.append(
            f"| {stage['order']} | `{stage['stage']}` | {stage['role']} | {stage['gate']} |"
        )
    lines.extend(["", "## Commands", ""])
    for command in payload["commands"]:
        kind = "Cosima production" if command["launches_cosima"] else "no Cosima"
        lines.extend(
            [
                f"- {command['purpose']} ({kind})",
                f"  - `{command['command']}`",
            ]
        )
    lines.extend(["", "## Hard boundaries", ""])
    lines.extend(f"- {row}" for row in payload["hard_boundaries"])
    lines.extend(["", "## Resource floor", ""])
    lines.append(
        f"- Minimum free space before launch: `{payload['resources']['minimum_free_space_before_launch_gb']} GB`."
    )
    lines.append(f"- {payload['resources']['worker_guidance']}.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    payload = build()
    write_json(OUT_JSON, payload)
    OUT_MD.write_text(markdown(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "screening_promotion": payload["screening_promotion"]["status"],
                "json": rel(OUT_JSON),
                "markdown": rel(OUT_MD),
                "production_launched": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
