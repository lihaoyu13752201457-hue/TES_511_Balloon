#!/usr/bin/env python3
"""Write the explicit S3d-O9 transport-to-Step08 closure contract."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
WORK = Path(__file__).resolve().parents[1]
OUT_JSON = WORK / "data/s3d_fullchain_closure_map.json"
OUT_MD = WORK / "FULLCHAIN_CLOSURE_MAP.md"

GEOMETRY = (
    "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/geometry/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
DELAY_RUNNER = (
    "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/"
    "code/run_s3d_delayed_activation.py"
)
CLOSURE_RUNNER = (
    "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/"
    "code/run_s3d_step05_08_closure.py"
)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def exists(path: str) -> bool:
    return (ROOT / path).exists()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build() -> dict[str, Any]:
    stages = [
        {
            "order": 1,
            "stage": "geometry",
            "role": "single geometry authority for every source and SIM header",
            "inputs": [],
            "outputs": [
                GEOMETRY,
                "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/data/s3d_geometry_manifest.json",
                "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/data/s3d_independent_geometry_validation.json",
                "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/data/cosima_overlap_s3d_summary.json",
            ],
            "gate": "all static/independent/overlap checks PASS and geometry hash frozen",
        },
        {
            "order": 2,
            "stage": "prompt_all8",
            "role": "paper-grade prompt background; the e+/n screen is not accepted here",
            "inputs": [
                "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/config/full_prompt_all8/source_cards/source_migration_manifest.json"
            ],
            "outputs": [
                "runs/geometry_optimization_20260704/s3d_o9_fullstat_prompt_all8_20260712/normalization.json",
                "runs/geometry_optimization_20260704/s3d_o9_fullstat_prompt_all8_20260712/run_summary.json",
            ],
            "statistics": "68 jobs: gamma 10M in 12 splits; alpha/e-/e+/mu-/mu+/n/p each 8 replicas",
            "gate": "68 PASS/SKIP, generated=requested, 68 SIM+DAT files, one TT/file, all source and SIM geometry headers exact",
        },
        {
            "order": 3,
            "stage": "atm511_sidecar",
            "role": "semiempirical atmospheric 511-keV line, never relabeled as native EXPACS",
            "inputs": [
                "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/data/s3d_atm511_replay_manifest.json"
            ],
            "outputs": [
                "runs/geometry_optimization_20260704/s3d_o9_atm511_sidecar_3m_20260712/Atm511SidecarS3dO9_3M.inc1.id1.sim.gz",
                "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/data/s3d_atm511_replay_summary.json",
            ],
            "statistics": "3,000,000 events; 20 directional bins; nominal S1 4pi line model",
            "gate": "SE=ID=3M, exact geometry, 50-keV analysis veto, W/Al excluded, W2/broad rates and total catalog occupancy reported",
        },
        {
            "order": 4,
            "stage": "neutron_delayed",
            "role": "neutron-only activation inventory and exact-position delayed transport",
            "inputs": [
                "runs/geometry_optimization_20260704/s3d_o9_fullstat_prompt_all8_20260712/run_summary.json",
                "inputs/nubase/nubase_2020.txt",
            ],
            "outputs": [
                "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/data/s3d_delayed_activation_campaign.json",
                "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/fullchain/delayed_source/delayed_source_exactpos_summary.json",
                "runs/geometry_optimization_20260704/step02_delayed_transport_s3d_o9_neutron_delayed_m50000_20260712/DelayedDecayS3dO9NeutronM50000.inc1.id1.sim.gz",
            ],
            "statistics": "8 neutron buildup reps; TT/8; N_SAMPLE=2M; raw triggers=1M; M=50,000; seed=260613; delayed SE=ID=1M",
            "gate": "NUBASE ground-state PASS, exact support/provenance PASS, source flux closure PASS, delayed geometry/SE/ID PASS",
        },
        {
            "order": 5,
            "stage": "focused_signal",
            "role": "full 37,194-row f10m-A1 EventList replay through the same geometry",
            "inputs": [
                "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/eventlists/Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat"
            ],
            "outputs": [
                "runs/geometry_optimization_20260704/s3d_o9_f10m_a1_signal_replay_37194_20260712/Opticsim_laue_f10m_a1_s3d_o9_signal37194.inc1.id1.sim.gz",
                "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/data/s3d_signal_replay_manifest.json",
            ],
            "statistics": "37,194 triggers; SE=ID=37,194",
            "gate": "EventList hash/row provenance, exact source/SIM geometry, SE=ID=37,194",
        },
        {
            "order": 6,
            "stage": "step05_core_and_atm_merge",
            "role": "one selection implementation for prompt, delayed, signal, and atmospheric-line sidecar",
            "inputs": [
                "runs/geometry_optimization_20260704/s3d_o9_fullstat_prompt_all8_20260712/run_summary.json",
                "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/fullchain/delayed_source/delayed_source_exactpos_summary.json",
                "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/data/s3d_atm511_replay_summary.json",
                "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/data/s3d_signal_replay_manifest.json",
            ],
            "outputs": [
                "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/fullchain/step05/step05_s3d_o9_core_no_atm511_summary.json",
                "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/fullchain/step05/step05_s3d_o9_fullchain_l1_response_summary.json",
            ],
            "gate": "50-keV analysis veto frozen; native BGO detector threshold (80 keV) disclosed as a systematic; final background=8-family prompt+neutron delayed+atm511; signal geometry-local",
        },
        {
            "order": 7,
            "stage": "step06",
            "role": "mission time fold",
            "inputs": [
                "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/fullchain/step05/step05_s3d_o9_fullchain_l1_response_summary.json",
                "runs/geometry_optimization_20260704/step02_delay_fix_s3d_o9_neutron_delayed_m50000_20260712/groundstate_activity_corrections.csv",
            ],
            "outputs": [
                "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/fullchain/step06/step06_s3d_o9_fullchain_summary.json",
                "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/fullchain/step06/background_time_variation.csv",
            ],
            "gate": "prompt, delayed activity, science transmission, and atm511 phi_4pi scales kept separate; atm angular-transfer constancy disclosed",
        },
        {
            "order": 8,
            "stage": "step07",
            "role": "source-case rate authority",
            "inputs": [
                "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/fullchain/step06/step06_s3d_o9_fullchain_summary.json"
            ],
            "outputs": [
                "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/fullchain/step07/source_case_summary.json",
                "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/fullchain/step07/source_case_rates.csv",
            ],
            "gate": "focused signal manifest supplies 37,194 rows; no Mass_model/fix5 signal substitution",
        },
        {
            "order": 9,
            "stage": "step08",
            "role": "20-day time-dependent counting significance",
            "inputs": [
                "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/fullchain/step06/background_time_variation.csv",
                "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/fullchain/step07/source_case_rates.csv",
            ],
            "outputs": [
                "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/fullchain/step08/step08_s3d_o9_fullchain_time_dependent_summary.json",
                "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/fullchain/step08/t3_t5_summary.csv",
            ],
            "gate": "atm511 occupancy included when available; never silently set pending occupancy to zero; compare central and uncertainty-aware F3 against S3c C0",
        },
    ]

    commands = [
        {
            "purpose": "lightweight source/job preflight (safe now)",
            "command": f"python3 {DELAY_RUNNER} prepare --workers 1",
            "heavy": False,
        },
        {
            "purpose": "all-eight-family prompt production",
            "command": f"python3 {DELAY_RUNNER} run-full-prompt --workers 8 --allow-heavy-run",
            "heavy": True,
        },
        {
            "purpose": "assemble neutron instant provenance from the all-eight-family run",
            "command": f"python3 {DELAY_RUNNER} assemble-instant",
            "heavy": False,
        },
        {
            "purpose": "neutron ActivationBuildUp production",
            "command": f"python3 {DELAY_RUNNER} run-buildup --workers 8 --allow-heavy-run",
            "heavy": True,
        },
        {
            "purpose": "RPIP raw source, NUBASE fix, and exact-position M=50k source",
            "command": f"python3 {DELAY_RUNNER} prepare-delay --workers 8 --allow-heavy-run",
            "heavy": True,
        },
        {
            "purpose": "one-million-event delayed transport",
            "command": f"python3 {DELAY_RUNNER} run-delay --allow-heavy-run",
            "heavy": True,
        },
        {
            "purpose": "prepare/audit atmospheric source without transport",
            "command": "python3 engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/code/prepare_s3d_atm511_replay.py",
            "heavy": False,
        },
        {
            "purpose": "atmospheric 3M production (explicit confirmation token)",
            "command": "python3 engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/code/prepare_s3d_atm511_replay.py --execute --confirm Atm511SidecarS3dO9_3M",
            "heavy": True,
        },
        {
            "purpose": "Step05-Step08 fail-closed preflight (writes PENDING while production is incomplete)",
            "command": f"python3 {CLOSURE_RUNNER} preflight",
            "heavy": False,
        },
        {
            "purpose": "Step05-Step08 pure-function lightweight self-test",
            "command": f"python3 {CLOSURE_RUNNER} self-test",
            "heavy": False,
        },
        {
            "purpose": "Step05-Step08 postprocessing after every transport gate is PASS",
            "command": f"python3 {CLOSURE_RUNNER} all --workers 8",
            "heavy": False,
        },
    ]

    for stage in stages:
        stage["output_exists"] = {path: exists(path) for path in stage.get("outputs", [])}
    payload = {
        "status": "PASS_S3D_O9_FULLCHAIN_PATH_CONTRACT",
        "generated_at_utc": now_utc(),
        "geometry_setup": GEOMETRY,
        "claim_scope": "paper-grade path and gate contract; not a claim that pending transport has completed",
        "stages": stages,
        "commands": commands,
        "resources": {
            "measured_analogs": {
                "all8_prompt_disk": "6.7 GB (retained Mass_model full-stat analog)",
                "neutron_eplus_screen_disk": "5.3 GB (retained S3c e+/n analog)",
                "neutron_buildup_disk": "4.0 GB (retained S3c analog)",
                "delayed_1m_disk": "0.78 GB (retained S3c analog)",
                "atm511_3m_disk": "1.1 GB (retained S3c analog)",
                "focused_signal_disk": "0.032 GB (retained geo-opt analog)",
            },
            "minimum_free_space_before_launch_gb": 20,
            "worker_guidance": "8 transport workers is the normal launch point; reduce if RAM pressure or concurrent Cosima work exists",
        },
        "known_gaps": [
            "The dedicated run_s3d_step05_08_closure.py postprocessor is present and lightweight-tested; it remains PENDING until every production input passes its fail-closed preflight.",
            "Step05 explicitly merges all-eight-family prompt, neutron-only delayed, atmospheric-511, and geometry-local focused signal using the retained selection at a 50-keV analysis veto.",
            "Step06 keeps prompt, delayed activity, science transmission, and atmospheric phi_4pi scales separate and discloses the fixed day-15 atmospheric angular-transfer approximation.",
            "Step08 includes atmospheric detector-catalog occupancy in the accidental live factor and never substitutes a pending occupancy with zero.",
            "The runner emits a matched heavy-control screening comparison for the isolated mass-reduction question and a separate full-chain comparison to the paper reference detector; manuscript display names omit internal engineering labels.",
            "Direct use of the retained generic Step06-Step08 scripts with an arbitrary S3d label remains non-authoritative.",
        ],
        "hard_boundaries": [
            "The 16-job e+/n screening run is never accepted as all-family Step05 prompt authority.",
            "The atmospheric line is a semiempirical sidecar, not a native EXPACS 511-keV prediction.",
            "The delayed result is neutron-only and must be described as such; it is not a full-particle activation inventory.",
            "Every source and SIM header must resolve to the S3d geometry above.",
            "No retained S3c, Mass_model, fix5, or central stepwise output is overwritten.",
            "Internal design labels are engineering provenance and must be replaced by descriptive configuration names in the manuscript.",
        ],
    }
    return payload


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# S3d-O9 full-chain closure map",
        "",
        f"Status: `{payload['status']}`",
        "",
        "This is a path/gate contract. A listed output can still be pending; the contract never promotes a prepared source or manifest into measured transport evidence.",
        "",
        "| order | stage | role | gate |",
        "| ---: | --- | --- | --- |",
    ]
    for stage in payload["stages"]:
        lines.append(f"| {stage['order']} | `{stage['stage']}` | {stage['role']} | {stage['gate']} |")
    lines.extend(["", "## Commands", ""])
    for row in payload["commands"]:
        kind = "heavy" if row["heavy"] else "lightweight"
        lines.extend([f"- {row['purpose']} ({kind})", f"  - `{row['command']}`"])
    lines.extend(["", "## Boundaries", ""])
    lines.extend(f"- {item}" for item in payload["hard_boundaries"])
    lines.extend(["", "## Resources", ""])
    for name, value in payload["resources"]["measured_analogs"].items():
        lines.append(f"- `{name}`: {value}")
    lines.append(f"- minimum free space before launch: `{payload['resources']['minimum_free_space_before_launch_gb']} GB`")
    lines.append(f"- workers: {payload['resources']['worker_guidance']}")
    lines.extend(["", "## Step05-Step08 implementation status", ""])
    lines.extend(f"- {item}" for item in payload["known_gaps"])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    payload = build()
    write_json(OUT_JSON, payload)
    OUT_MD.write_text(markdown(payload), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "json": str(OUT_JSON.relative_to(ROOT)), "markdown": str(OUT_MD.relative_to(ROOT))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
