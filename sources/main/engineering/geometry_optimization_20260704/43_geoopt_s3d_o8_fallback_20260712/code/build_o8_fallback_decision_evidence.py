#!/usr/bin/env python3
"""Reproduce the transport evidence that triggers the O8 fallback geometry."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
WORK = Path(__file__).resolve().parents[1]
OUTPUT = WORK / "data/o8_fallback_decision_evidence.json"

GEOOPT = ROOT / "engineering/geometry_optimization_20260704"
ENTRY_AUTHORITY = (
    GEOOPT
    / "40_s3c_mainline_lightweight_review_20260710/code/build_s3c_lightweight_analysis.py"
)
SCREENING = (
    GEOOPT
    / "42_geoopt_s3d_lightweight_20260712/data/s3d_screening_analysis.json"
)
C0_ATM = (
    GEOOPT
    / "32_s3c_dominant_backgrounds_20260709/s3c_atm511_sidecar_3m_summary.json"
)
O9_ATM = (
    GEOOPT
    / "42_geoopt_s3d_lightweight_20260712/data/s3d_atm511_replay_summary.json"
)

W2 = "w2_510p58_511p42"
GATE_LIMIT_CPS = 0.0052
sys.dont_write_bytecode = True


def rel(path: Path | str) -> str:
    value = Path(path)
    if not value.is_absolute():
        value = ROOT / value
    return value.resolve().relative_to(ROOT).as_posix()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_entry_authority():
    spec = importlib.util.spec_from_file_location(
        "o8_fallback_entry_authority", ENTRY_AUTHORITY
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load entry authority: {ENTRY_AUTHORITY}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def entry_audit(authority, summary: dict) -> dict:
    window = summary["windows"][W2]
    ids = {int(value) for value in window["final_event_ids"]}
    sim = ROOT / summary["inputs"]["sim"]
    inits = authority.scan_target_inits(sim, ids)
    rows = []
    for event_id in sorted(ids):
        init = inits[event_id]
        rows.append(
            {
                "event_id": event_id,
                **init,
                **authority.classify_entry(init),
            }
        )
    counts = Counter(row["entry_surface"] for row in rows)
    return {
        "sim": rel(sim),
        "sim_sha256": sha256(sim),
        "selected_final_w2_events": len(rows),
        "entry_surface_counts": dict(sorted(counts.items())),
        "side_fraction": counts.get("side", 0) / len(rows),
        "events": rows,
    }


def main() -> int:
    for path in (ENTRY_AUTHORITY, SCREENING, C0_ATM, O9_ATM):
        if not path.exists():
            raise RuntimeError(f"missing decision-evidence prerequisite: {path}")

    authority = load_entry_authority()
    screening = load_json(SCREENING)
    c0 = load_json(C0_ATM)
    o9 = load_json(O9_ATM)

    prompt_cases = screening["sections"]["prompt"]["cases"]
    prompt_parts = {
        particle: float(case["summary"]["side_compton_fov_pass_rate_s-1"])
        for particle, case in prompt_cases.items()
    }
    if set(prompt_parts) != {"eplus", "n"}:
        raise RuntimeError(f"unexpected prompt-screening components: {prompt_parts}")
    prompt_rate = sum(prompt_parts.values())
    atm_rate = float(o9["windows"][W2]["final_rate_cps"])
    combined_rate = prompt_rate + atm_rate

    c0_entry = entry_audit(authority, c0)
    o9_entry = entry_audit(authority, o9)
    expected_c0 = {"bottom": 1, "side": 5}
    expected_o9 = {"bottom": 1, "side": 17}
    if c0_entry["entry_surface_counts"] != expected_c0:
        raise RuntimeError(
            f"C0 entry-direction reproduction changed: {c0_entry['entry_surface_counts']}"
        )
    if o9_entry["entry_surface_counts"] != expected_o9:
        raise RuntimeError(
            f"O9 entry-direction reproduction changed: {o9_entry['entry_surface_counts']}"
        )
    if combined_rate <= GATE_LIMIT_CPS:
        raise RuntimeError(
            f"O9 gate is no longer failed: {combined_rate} <= {GATE_LIMIT_CPS} cps"
        )

    c0_atm_rate = float(c0["windows"][W2]["final_rate_cps"])
    payload = {
        "status": "PASS_REPRODUCED_O9_GATE_FAILURE_AND_ENTRY_DIRECTIONS",
        "claim_boundary": (
            "This is a reproducible decision audit over retained O9/C0 transport "
            "outputs. It is not an O8 transport result."
        ),
        "algorithm_authority": {
            "path": rel(ENTRY_AUTHORITY),
            "sha256": sha256(ENTRY_AUTHORITY),
            "records": "IA INIT",
            "classifier": "classify_entry",
        },
        "input_authorities": {
            "screening": {"path": rel(SCREENING), "sha256": sha256(SCREENING)},
            "c0_atm511": {"path": rel(C0_ATM), "sha256": sha256(C0_ATM)},
            "o9_atm511": {"path": rel(O9_ATM), "sha256": sha256(O9_ATM)},
        },
        "o9_transport_gate": {
            "policy": "matched eplus + neutron + atmospheric-511 final W2 rate <= 0.0052 cps",
            "prompt_components_cps": prompt_parts,
            "prompt_eplus_plus_neutron_cps": prompt_rate,
            "atmospheric_511_cps": atm_rate,
            "combined_cps": combined_rate,
            "limit_cps": GATE_LIMIT_CPS,
            "excess_cps": combined_rate - GATE_LIMIT_CPS,
            "pass": False,
        },
        "atmospheric_final_w2_entry_audit": {
            "c0": c0_entry,
            "o9": o9_entry,
            "o9_over_c0_event_count_ratio": (
                o9_entry["selected_final_w2_events"]
                / c0_entry["selected_final_w2_events"]
            ),
            "o9_over_c0_normalized_rate_ratio": atm_rate / c0_atm_rate,
        },
        "fallback_inference": {
            "selected_profile": "O8 side40/bottom30/top10/no-outer-W2/Al3",
            "reason": (
                "The failed O9 screen is side-dominated: 17/18 O9 atmospheric "
                "final-W2 survivors enter through the side, versus 5/6 for C0, "
                "while the O9 atmospheric survivor count triples. Retaining the "
                "40 mm side BGO is therefore the data-driven first fallback; "
                "bottom/top thinning remains the lower-exposure mass lever."
            ),
            "causal_boundary": (
                "The directional concentration motivates the fallback but does "
                "not prove O8 performance; O8 requires its own matched transport."
            ),
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "output": rel(OUTPUT),
                "combined_cps": combined_rate,
                "c0_entries": c0_entry["entry_surface_counts"],
                "o9_entries": o9_entry["entry_surface_counts"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
