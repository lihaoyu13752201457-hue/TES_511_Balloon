#!/usr/bin/env python3
"""Create the G7 pilot transport resource/approval gate."""

from __future__ import annotations

import json
import csv
import re
from datetime import datetime, timezone
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any


getcontext().prec = 80

PHASE_DIR = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
OUT = PHASE_DIR / "07_transport"
PILOT_INPUTS = OUT / "pilot_inputs"

WP04_MANIFEST = PHASE_DIR / "04_custom_source_v2/source_v2_manifest.json"
WP05_SUMMARY = PHASE_DIR / "05_native_activation/summary.json"
WP06_SUMMARY = PHASE_DIR / "06_time_constant/summary.json"
V2_EVENTLIST = PHASE_DIR / "04_custom_source_v2/source_v2_eventlist.dat"
V2_WEIGHTS = PHASE_DIR / "04_custom_source_v2/source_v2_event_weights.csv"
NATIVE_STORE = PHASE_DIR / "04_custom_source_v2/source_v2_native_activity_store_total.dat"
GEOMETRY = (
    ROOT
    / "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/"
    / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
PLAN_JSON = OUT / "pilot_transport_resource_plan.json"
PLAN_MD = OUT / "pilot_transport_resource_plan.md"
PILOT_INPUT_MANIFEST = OUT / "pilot_input_manifest.json"
SUMMARY_JSON = OUT / "summary.json"
SUMMARY_MD = OUT / "summary.md"

LEGACY_CANDIDATES = [
    ROOT / "runs/step02_delay_fix_fix5_fullstat_v2/activation_decay_day15_groundstate_fixed_exactpos_m50000_s260613.source",
    ROOT / "runs/step02_delay_fix_fix5_1of10_v2/activation_decay_day15_groundstate_fixed_exactpos_m5000_s260613.source",
    ROOT / "runs/step02_delayed_transport_fix5_fullstat_v2_exactpos_m50000_s260613/activation_decay_day15_groundstate_fixed_exactpos_m50000_s260613.source",
]


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def dec(text: str | Decimal | None) -> Decimal:
    if isinstance(text, Decimal):
        return text
    if text is None or text == "":
        return Decimal(0)
    return Decimal(str(text))


def fmt_dec(value: Decimal) -> str:
    return format(value.normalize(), "f") if value else "0"


def build_v2_pilot_subset(sample_size: int = 1000) -> dict[str, Any]:
    PILOT_INPUTS.mkdir(parents=True, exist_ok=True)
    event_lines = V2_EVENTLIST.read_text(encoding="utf-8").splitlines()
    with V2_WEIGHTS.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if len(event_lines) != len(rows):
        raise RuntimeError("v2 EventList and weight ledger row counts differ")
    weights = [dec(row["event_weight_Bq"]) for row in rows]
    total = sum(weights, Decimal(0))
    selected: list[int] = []
    cumulative = Decimal(0)
    cursor = 0
    for i in range(sample_size):
        threshold = (Decimal(i) + Decimal("0.5")) * total / Decimal(sample_size)
        while cursor < len(weights) - 1 and cumulative + weights[cursor] < threshold:
            cumulative += weights[cursor]
            cursor += 1
        selected.append(cursor)

    subset_eventlist = PILOT_INPUTS / "v2_eventlist_pilot1000.dat"
    subset_weights = PILOT_INPUTS / "v2_event_weights_pilot1000.csv"
    subset_source = PILOT_INPUTS / "v2_eventlist_pilot1000.source"
    pilot_weight = total / Decimal(sample_size)

    with subset_eventlist.open("w", encoding="utf-8") as ev, subset_weights.open("w", newline="", encoding="utf-8") as wf:
        fieldnames = ["pilot_event_id", "original_event_id", "sampling_method", "pilot_event_weight_Bq"] + list(rows[0].keys())
        writer = csv.DictWriter(wf, fieldnames=fieldnames)
        writer.writeheader()
        for pilot_id, original_idx in enumerate(selected):
            parts = event_lines[original_idx].split()
            if len(parts) != 15:
                raise RuntimeError(f"bad EventList row at {original_idx}")
            parts[0] = str(pilot_id)
            parts[4] = f"{pilot_id * 1e-9:.12e}"
            ev.write(" ".join(parts) + "\n")
            out_row = {
                "pilot_event_id": pilot_id,
                "original_event_id": original_idx,
                "sampling_method": "weighted_systematic_pps",
                "pilot_event_weight_Bq": fmt_dec(pilot_weight),
            }
            out_row.update(rows[original_idx])
            writer.writerow(out_row)

    subset_source.write_text(
        f"""# G7 pilot-only v2 weighted EventList source. Not authority.
Version 1
Geometry {rel(GEOMETRY)}
PhysicsListEM LivermorePol
PhysicsListRadioactiveDecay true
DecayMode ActivationDelayedDecay
StoreSimulationInfo all
DiscretizeHits true
DetectorTimeConstant 1e-9

Run DelayedSourceV2Pilot
DelayedSourceV2Pilot.FileName {rel(OUT / "pilot_runs/v2_eventlist_pilot1000")}
DelayedSourceV2Pilot.Triggers {sample_size}
DelayedSourceV2Pilot.Source DelayedSourceV2Pilot_EventList

DelayedSourceV2Pilot_EventList.EventList {rel(subset_eventlist)}
""",
        encoding="utf-8",
    )
    return {
        "source": rel(subset_source),
        "eventlist": rel(subset_eventlist),
        "weights": rel(subset_weights),
        "sample_size": sample_size,
        "full_eventlist_rows": len(rows),
        "sampling_method": "weighted_systematic_pps",
        "pilot_event_weight_Bq": fmt_dec(pilot_weight),
        "represented_total_activity_Bq": fmt_dec(pilot_weight * Decimal(sample_size)),
    }


def build_native_pilot_source(sample_size: int = 1000) -> dict[str, Any]:
    PILOT_INPUTS.mkdir(parents=True, exist_ok=True)
    source = PILOT_INPUTS / "native_activation_sources_pilot1000.source"
    source.write_text(
        f"""# G7 pilot-only native volume-level ActivationSources source.
Version 1
Geometry {rel(GEOMETRY)}
PhysicsListEM LivermorePol
PhysicsListRadioactiveDecay true
DecayMode ActivationDelayedDecay
StoreSimulationInfo all
DetectorTimeConstant 1e-9
Seed 51007

Run NativeActivationPilot
NativeActivationPilot.FileName {rel(OUT / "pilot_runs/native_activation_pilot1000")}
NativeActivationPilot.Triggers {sample_size}
NativeActivationPilot.ActivationSources {rel(NATIVE_STORE)}
""",
        encoding="utf-8",
    )
    return {"source": rel(source), "triggers": sample_size, "activation_store": rel(NATIVE_STORE)}


def build_legacy_pilot_source(legacy: Path | None, sample_size: int = 1000) -> dict[str, Any]:
    if legacy is None:
        return {"source": "", "triggers": sample_size, "legacy_source_found": False}
    PILOT_INPUTS.mkdir(parents=True, exist_ok=True)
    text = legacy.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"(?m)^(DecayRun\.FileName\s+).*$", rf"\1{rel(OUT / 'pilot_runs/legacy_l0_pilot1000')}", text)
    text = re.sub(r"(?m)^(DecayRun\.Triggers\s+).*$", rf"\g<1>{sample_size}", text)
    source = PILOT_INPUTS / "legacy_l0_pilot1000.source"
    source.write_text(
        "# G7 pilot-only copy of legacy L0 delayed source. Not authority.\n" + text,
        encoding="utf-8",
    )
    return {"source": rel(source), "triggers": sample_size, "legacy_source": rel(legacy), "legacy_source_found": True}


def build_pilot_inputs(legacy: Path | None) -> dict[str, Any]:
    PILOT_INPUTS.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "READY_NOT_RUN",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "claim_boundary": "pilot input preparation only; no Cosima transport launched",
        "legacy_l0": build_legacy_pilot_source(legacy),
        "v2_weighted_eventlist": build_v2_pilot_subset(),
        "native_volume_activation": build_native_pilot_source(),
    }
    write_json(PILOT_INPUT_MANIFEST, payload)
    return payload


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    wp04 = json.loads(WP04_MANIFEST.read_text(encoding="utf-8"))
    wp05 = json.loads(WP05_SUMMARY.read_text(encoding="utf-8"))
    wp06 = json.loads(WP06_SUMMARY.read_text(encoding="utf-8"))
    legacy = first_existing(LEGACY_CANDIDATES)
    pilot_inputs = build_pilot_inputs(legacy)
    status = "BLOCKED_RESOURCE_APPROVAL"
    plan = {
        "status": status,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "claim_boundary": "resource plan only; no pilot selected-rate authority",
        "blocking_reasons": [
            "pilot transport would create new Cosima simulation outputs",
            "v2 exact-position EventList has 254704 weighted rows",
            f"G5 native oracle status is {wp05.get('status')}; selected-rate promotion still requires pilot/full transport and Step05 ingestion",
        ],
        "required_user_approval": {
            "approve_cosima_pilot_transport": False,
            "minimum_matrix": [
                "legacy L0 delayed source",
                "v2 weighted exact-position EventList source",
                "native volume-level ActivationSources source",
            ],
        },
        "candidate_inputs": {
            "legacy_l0_source": rel(legacy) if legacy else "",
            "legacy_l0_source_found": legacy is not None,
            "v2_eventlist_source": wp04["outputs"]["source_card"],
            "v2_eventlist_rows": wp04["eventlist_rows"],
            "native_activation_sources_probe": rel(PHASE_DIR / "05_native_activation/native_activation_sources_probe.source"),
            "timing_authority": rel(PHASE_DIR / "06_time_constant/timing_authority.json"),
            "pilot_input_manifest": rel(PILOT_INPUT_MANIFEST),
        },
        "prepared_pilot_inputs": pilot_inputs,
        "recommended_bounded_pilot": {
            "legacy_triggers": 1000,
            "v2_eventlist_rows": "first deterministic 1000-row slice or stratified weighted subset; do not overwrite source-v2 authority",
            "native_triggers": 1000,
            "outputs_dir": rel(OUT / "pilot_runs"),
            "selection": "existing Step05 selection only; no veto/W2/geometry changes",
        },
        "promotion_allowed_after_this_gate": False,
        "wp05_status": wp05.get("status"),
        "wp06_status": wp06.get("status"),
    }
    write_json(PLAN_JSON, plan)
    PLAN_MD.write_text(
        "\n".join(
            [
                "# Pilot Transport Resource Plan",
                "",
                f"status: `{status}`",
                "",
                "No pilot transport was launched.",
                "",
                "Blocking reasons:",
                "- Pilot transport would create new Cosima simulation outputs.",
                "- The v2 exact-position EventList contains 254704 weighted rows.",
                f"- G5 native oracle status is `{wp05.get('status')}`; selected-rate promotion still requires transport and Step05 ingestion.",
                "",
                "Candidate inputs:",
                f"- legacy L0 source: `{rel(legacy) if legacy else 'not found'}`",
                f"- v2 source: `{wp04['outputs']['source_card']}`",
                f"- native source: `engineering/delayed_source_authority_v2_20260624/05_native_activation/native_activation_sources_probe.source`",
                f"- prepared pilot input manifest: `{rel(PILOT_INPUT_MANIFEST)}`",
                "",
                "Recommended bounded pilot after approval:",
                "- 1000 triggers legacy L0",
                "- deterministic 1000-row v2 weighted subset or equivalent stratified slice",
                "- 1000 triggers native volume-level source",
                "- existing Step05 selection only; no geometry, veto, W2, prompt, or signal changes",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    summary = {
        "status": status,
        "outputs": [
            rel(PLAN_JSON),
            rel(PLAN_MD),
            rel(PILOT_INPUT_MANIFEST),
            pilot_inputs["legacy_l0"].get("source", ""),
            pilot_inputs["v2_weighted_eventlist"]["source"],
            pilot_inputs["v2_weighted_eventlist"]["eventlist"],
            pilot_inputs["v2_weighted_eventlist"]["weights"],
            pilot_inputs["native_volume_activation"]["source"],
            rel(SUMMARY_MD),
        ],
        "findings": [
            "No pilot transport launched.",
            "Explicit resource approval required before Cosima pilot matrix.",
            f"G5 status remains {wp05.get('status')}; no promotion allowed from current state.",
        ],
        "next_gate": "user approval for bounded G7 pilot transport, or tag-aware native Activator oracle first",
        "user_decision_required": True,
    }
    write_json(SUMMARY_JSON, summary)
    SUMMARY_MD.write_text(
        "\n".join(
            [
                "# WP07 Pilot Transport Summary",
                "",
                f"status: `{status}`",
                "",
                "No transport was launched. See resource plan:",
                f"`{rel(PLAN_JSON)}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"WP07 {status}")
    print(json.dumps(plan, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
