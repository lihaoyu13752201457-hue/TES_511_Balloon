#!/usr/bin/env python3
"""Publish the answer-first, append-only batch0007 campaign review.

This builder reads only small terminal/analysis authorities.  It does not open
SIM payloads, rerun transport, or recompute large artifact hashes.  Publication
is write-once via a sibling ``.partial`` directory followed by atomic rename.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path("/home/ubuntu/TES_511_Balloon")
ENG = (
    ROOT
    / "engineering/particle_source_unit_repair_20260811"
    / "m05_paper_closure_topup_batch0007_3h_20260813"
)
RUN = (
    ROOT
    / "runs/particle_source_unit_repair_20260811"
    / "m05_paper_closure_topup_batch0007_3h_v1"
)

TOPUP_VALIDATION = RUN / "final_validation.json"
PROMPT_SUMMARY = RUN / "analysis_prompt_activation/summary.json"
CATALOG = RUN / "delayed_phase02/catalog_v1/catalog.json"
EPSILON_SMOKE = (
    RUN
    / "delayed_phase02/state_aware_exactpos_v1"
    / "spectrum_epsilon_repair_smoke0001/smoke_validation.json"
)
RECOVERY = (
    RUN
    / "delayed_phase02/state_aware_exactpos_v1"
    / "spectrum_epsilon_formal_partial_recovery0002"
)
REVALIDATION1 = RECOVERY / "revalidation0001/formal_partial_revalidation.json"
REVALIDATION2 = (
    RECOVERY
    / "revalidation0002/no_deca_epsilon_subthreshold_true_deposit_audit.json"
)
DELAYED_SUMMARY = RUN / "analysis_delayed_response_recovery0002_revalidation0001/summary.json"

OUTPUT = RUN / "final_campaign_review"
REPORT = OUTPUT / "REPORT.md"
SUMMARY = OUTPUT / "summary.json"
MANIFEST = OUTPUT / "MANIFEST.json"


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def atomic_write(path: Path, payload: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def build() -> tuple[dict[str, Any], str]:
    topup = load(TOPUP_VALIDATION)
    prompt = load(PROMPT_SUMMARY)
    catalog = load(CATALOG)
    smoke = load(EPSILON_SMOKE)
    reval1 = load(REVALIDATION1)
    reval2 = load(REVALIDATION2)
    delayed = load(DELAYED_SUMMARY)

    require(
        topup.get("status") == "PASS__BATCH0007_SUPPLEMENTAL_TRANSPORT_COMPLETE",
        "batch0007 topup is not terminal PASS",
    )
    require(
        prompt.get("status") == "PASS__BATCH0007_READ_ONLY_PROMPT_ACTIVATION_SCREENING",
        "prompt/activation analysis is not PASS",
    )
    require(
        catalog.get("status") == "PASS__CORRECTED_BUILDUP_CATALOG_READY",
        "corrected BUILDUP catalog is not PASS",
    )
    require(
        smoke.get("status") == "PASS__EPSILON_MONO_TWO_GEOMETRY_SMOKE",
        "epsilon source smoke is not PASS",
    )
    require(
        reval1.get("status")
        == "PASS__REVALIDATION0001_SIX_CELL_DELAYED_PARTIAL_SCREENING_COMPATIBLE",
        "formal delayed revalidation0001 is not PASS",
    )
    require(
        reval2.get("status")
        == "PASS__REVALIDATION0002_DECA_99P9_CURRENT_RDM_ZERO_SECONDARY_EDGE_DOCUMENTED",
        "strengthened RDM/no-DECA audit is not PASS",
    )
    require(
        delayed.get("status")
        == "PASS__RECOVERY0002_THREE_FAMILY_DELAYED_RESPONSE_PARTIAL_SCREENING",
        "formal delayed-response analysis is not PASS",
    )

    prompt_by_geometry = {str(row["geometry"]): row for row in prompt["prompt"]}
    require(set(prompt_by_geometry) == {"Mass_model_511", "S3d_O8"}, "prompt geometry coverage drift")
    prompt_mass = prompt_by_geometry["Mass_model_511"]
    prompt_o8 = prompt_by_geometry["S3d_O8"]
    delayed_mass = delayed["geometry"]["Mass_model_511"]
    delayed_o8 = delayed["geometry"]["S3d_O8"]

    usable_events = 1_008_000 + 2_000 + 1_500_000
    result = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS__BATCH0007_3H_CAMPAIGN_REVIEW_READY",
        "decision": {
            "transport_and_analysis_chain": "READY_FOR_PARTIAL_SCREENING",
            "main_result": (
                "The corrected-keV prompt/activation chain and repaired epsilon delayed chain "
                "both produced analyzable M05 observables.  The campaign materially improves "
                "paper-closure evidence, but does not yet establish the complete delayed or "
                "mission-sensitivity rate."
            ),
            "continue_targeted_closure_work": True,
            "full_M05_rate_closure_claimed": False,
            "geometry_promotion_claimed": False,
        },
        "new_valid_transport": {
            "usable_jobs": 32,
            "usable_events": usable_events,
            "topup": {
                "jobs": 24,
                "events": 1_008_000,
                "cells": [
                    "eminus instant: 220,000 per geometry",
                    "eminus buildup: 220,000 per geometry",
                    "muminus buildup: 64,000 per geometry",
                ],
            },
            "epsilon_source_smoke": {"jobs": 2, "events": 2_000},
            "formal_delayed_partial": {
                "jobs": 6,
                "events": 1_500_000,
                "families": ["p", "n", "alpha"],
                "events_per_geometry_family": 250_000,
            },
            "rejected_2MeV_fallback_attempts_included": False,
        },
        "prompt_eminus": {
            "events": 440_000,
            "method": "TES pixel sum -> 0.420 keV FWHM -> measured hit <0.3 keV discard -> W2 -> exact active veto",
            "Mass_model_511": {
                "measured_W2": prompt_mass["measured_W2_count"],
                "active_pass_50": prompt_mass["W2_pass_50_count"],
                "zero_count_95_upper_rate_cps": prompt_mass[
                    "W2_pass_50_zero_count_95_upper_rate_cps"
                ],
            },
            "S3d_O8": {
                "measured_W2": prompt_o8["measured_W2_count"],
                "active_pass_50": prompt_o8["W2_pass_50_count"],
                "zero_count_95_upper_rate_cps": prompt_o8[
                    "W2_pass_50_zero_count_95_upper_rate_cps"
                ],
            },
        },
        "delayed_p_n_alpha": {
            "events": delayed["raw_scan"]["events"],
            "typed_CC_HIT": delayed["raw_scan"]["CC_HIT"],
            "TES_steps": delayed["raw_scan"]["TES_steps"],
            "Mass_model_511": {
                "measured_W2_count": delayed_mass["counts"]["measured_W2"],
                "measured_W2_rate_cps": delayed_mass["rates_cps"]["measured_W2"],
                "active_pass_50_count": delayed_mass["counts"]["W2_active_pass_50"],
                "active_pass_50_rate_cps": delayed_mass["rates_cps"]["W2_active_pass_50"],
                "topology_pass_50_count": delayed_mass["counts"][
                    "W2_active_topology_pass_50"
                ],
                "topology_pass_50_rate_cps": delayed_mass["rates_cps"][
                    "W2_active_topology_pass_50"
                ],
            },
            "S3d_O8": {
                "measured_W2_count": delayed_o8["counts"]["measured_W2"],
                "measured_W2_rate_cps": delayed_o8["rates_cps"]["measured_W2"],
                "active_pass_50_count": delayed_o8["counts"]["W2_active_pass_50"],
                "active_pass_50_rate_cps": delayed_o8["rates_cps"]["W2_active_pass_50"],
                "topology_pass_50_count": delayed_o8["counts"][
                    "W2_active_topology_pass_50"
                ],
                "topology_pass_50_rate_cps": delayed_o8["rates_cps"][
                    "W2_active_topology_pass_50"
                ],
            },
        },
        "quality_findings": {
            "old_exact_position_source_bug": (
                "Missing Spectrum caused MEGAlib's invalid-spectrum fallback to inject 2 MeV "
                "kinetic energy into parent ions.  The affected current attempt and historical "
                "exact-position delayed rates/rankings are rejected as physical authority."
            ),
            "repair": "Every parent source now declares Spectrum Mono 1e-6 keV; two-geometry smoke and formal transport contain zero 2 MeV artifacts.",
            "RDM_model_edge": {
                "events": reval2["total_events_without_IA_DECA"],
                "fraction": reval2["aggregate_no_DECA_fraction"],
                "isotope_ZA_counts": reval2[
                    "aggregate_no_DECA_initial_isotope_ZA_counts"
                ],
                "disposition": (
                    "Retained in the denominator and reported as an installed-Geant4 RDM "
                    "zero-secondary modeling caveat; not interpreted as proven physical zero response."
                ),
            },
        },
        "scope_and_limits": {
            "supported": [
                "corrected-keV transport compatibility",
                "M05 TES/response/W2/active-veto/Step05 analysis compatibility",
                "prompt e- and delayed p/n/alpha partial screening",
                "exact activation volume/isotope/state/position provenance",
            ],
            "not_supported": [
                "all-family final prompt rate",
                "all-family final delayed rate",
                "non-zero-excitation-state closure",
                "mission sensitivity",
                "final structure ranking",
                "geometry promotion",
            ],
            "catalog_DAT": catalog["coverage"]["N_DAT"],
            "catalog_cells": catalog["coverage"]["cells"],
            "catalog_sum_TT_s": catalog["coverage"]["sum_TT_s"],
            "catalog_sum_RP": catalog["coverage"]["sum_RP"],
        },
        "recommended_next_steps": [
            "Make explicit delayed parent spectrum and zero-2MeV checks permanent source/transport gates.",
            "Repair, upgrade, or separately calibrate the five affected RDM isotopes before final delayed-rate authority.",
            "Run corrected epsilon delayed gamma/e-/mu- next, then pilot e+/mu+; preserve matched geometry seeds and per-family normalization.",
            "Repeat independent position strata/seeds and stop on selected W2+veto+topology counts, not primary counts alone.",
            "Complete the all-authority prompt W2+veto+topology scan before allocating further prompt transport.",
        ],
        "sources": {},
    }

    for label, path in {
        "topup_validation": TOPUP_VALIDATION,
        "prompt_analysis": PROMPT_SUMMARY,
        "corrected_buildup_catalog": CATALOG,
        "epsilon_smoke": EPSILON_SMOKE,
        "delayed_revalidation0001": REVALIDATION1,
        "delayed_revalidation0002": REVALIDATION2,
        "delayed_response": DELAYED_SUMMARY,
    }.items():
        result["sources"][label] = {
            "path": rel(path),
            "sha256": sha256(path),
            "status": load(path).get("status"),
        }

    md = f"""# Batch0007 corrected-keV 3-hour closure campaign review

## Technical summary

**The campaign succeeded as targeted partial closure work.** It produced **32 valid transport jobs and {usable_events:,} usable events**: 1,008,000 prompt/activation top-up events, a 2,000-event two-geometry delayed-source smoke, and 1,500,000 corrected epsilon delayed events for p/n/alpha. The prompt/activation and delayed detector-response readers both constructed the M05 TES, response, W2, exact active-veto, and topology observables from real rich SIM payloads.

**It is not a full M05 rate closure.** Prompt coverage is still only the new e- top-up; delayed response covers ground-state p/n/alpha with a 10,000-position stride subsample. Gamma, e-/mu- delayed transport, e+/mu+, excited-state holdouts, mission sensitivity, final structure ranking, and geometry promotion remain outside this authority.

## Active veto is measurable in both prompt and delayed data

For prompt e-, Mass produced {prompt_mass['measured_W2_count']} measured W2 events and O8 produced {prompt_o8['measured_W2_count']}; **all were rejected by the exact 50/70/80 keV active veto**. The resulting per-geometry 95% zero-count upper limits are {prompt_mass['W2_pass_50_zero_count_95_upper_rate_cps']:.5f} and {prompt_o8['W2_pass_50_zero_count_95_upper_rate_cps']:.5f} cps. These are e--only partial-screening limits, not total prompt-background limits.

The corrected delayed p/n/alpha screen produced:

| Geometry | Measured W2 | Active 50-keV pass | Active + topology pass |
|---|---:|---:|---:|
| Mass | {delayed_mass['counts']['measured_W2']} / {delayed_mass['rates_cps']['measured_W2']:.6f} cps | {delayed_mass['counts']['W2_active_pass_50']} / {delayed_mass['rates_cps']['W2_active_pass_50']:.6f} cps | {delayed_mass['counts']['W2_active_topology_pass_50']} / {delayed_mass['rates_cps']['W2_active_topology_pass_50']:.6f} cps |
| S3d-O8 | {delayed_o8['counts']['measured_W2']} / {delayed_o8['rates_cps']['measured_W2']:.6f} cps | {delayed_o8['counts']['W2_active_pass_50']} / {delayed_o8['rates_cps']['W2_active_pass_50']:.6f} cps | {delayed_o8['counts']['W2_active_topology_pass_50']} / {delayed_o8['rates_cps']['W2_active_topology_pass_50']:.6f} cps |

The 50/70/80 keV delayed results are identical in this sample. Aggregate Mass topology survivors (173) support a useful partial rate screen; O8 has only 28, and individual family cells can be as low as 3, so detailed family/structure comparisons remain statistically weak.

## A latent delayed-source bug was found, rejected, and repaired

The first exact-position source cards omitted `Spectrum`. MEGAlib therefore used its invalid-spectrum fallback and assigned parent ions 2 MeV kinetic energy. That attempt and historical exact-position delayed rates/rankings sharing the same source pattern are **not physical authority**.

The repair adds `Spectrum Mono 1e-6` keV to every parent source. A two-geometry smoke and the 1.5M-event formal rerun have zero 2 MeV artifacts, correct geometry/seeds, complete gzip/ID framing, and closed full-activity flux after the 10k-position stride selection.

## The formal delayed subset passes with a documented RDM limitation

DECA coverage is {reval2['total_events_with_IA_DECA']:,}/{reval2['total_events']:,} ({100.0 * reval2['aggregate_IA_DECA_coverage_fraction']:.5f}%). The remaining {reval2['total_events_without_IA_DECA']} triggers are confined to Cs-120, Lu-162, Lu-165, Re-172, and Tl-188 and match a current installed-Geant4 radioactive-decay-model zero-secondary edge. They stay in the denominator and are a {100.0 * reval2['aggregate_no_DECA_fraction']:.5f}% trigger-level modeling caveat; they are not claimed as physically proven zero response.

## Scope, definitions, and uncertainty

- Prompt rate denominator: each e- geometry's own transported exposure; families are never pooled by TT.
- Delayed rate denominator: 250,000 triggers per geometry/family weighted by the full ground-state cell activity. The 10k retained positions have flux multiplied by five to close the original 50k-position activity.
- Detector response: per-pixel 0.420 keV FWHM Gaussian response, measured hits below 0.3 keV discarded, W2=[510.58,511.42) keV, exact active blocks at 50/70/80 keV, then retained Step05 topology.
- Count-based Poisson errors do not include position-subsampling uncertainty, nuclear-data error, or omitted-family/state uncertainty.
- Exact activation volume/isotope/state/position fields are retained and sufficient to execute structure attribution, but final structure ranking awaits all-family delayed closure and stronger selected-event counts.

## Recommended next steps

1. Make the explicit delayed-parent spectrum, header spectral type, and zero-2MeV checks permanent hard gates.
2. Repair/upgrade or independently calibrate the five RDM-edge isotopes before claiming a final delayed physical rate.
3. Run corrected epsilon delayed gamma/e-/mu- next; pilot e+/mu+ afterward, keeping matched geometry seeds and family-specific normalization.
4. Add independent position strata/seeds and stop on final W2+veto+topology survivor targets, not raw primary counts.
5. Complete the current-authority all-family prompt reader scan before spending more prompt transport time.

## Further questions

- How stable are the Mass/O8 delayed ratios across independent position strata?
- Which exact structure-volume bins dominate the final topology survivors once all delayed families are included?
- How much do corrected nuclear data for the five RDM-edge isotopes shift W2 and veto survivors?
"""
    return result, md


def publish() -> dict[str, Any]:
    if OUTPUT.exists() or OUTPUT.with_name(OUTPUT.name + ".partial").exists():
        raise FileExistsError(f"write-once output collision: {OUTPUT}")
    summary, report = build()
    partial = OUTPUT.with_name(OUTPUT.name + ".partial")
    partial.mkdir(parents=False, exist_ok=False)
    summary_payload = json_bytes(summary)
    report_payload = report.encode("utf-8")
    atomic_write(partial / "summary.json", summary_payload)
    atomic_write(partial / "REPORT.md", report_payload)
    manifest = {
        "schema_version": 1,
        "status": "PASS__WRITE_ONCE_ATOMIC_PUBLICATION",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "canonical_directory": rel(OUTPUT),
        "builder": {"path": rel(Path(__file__)), "sha256": sha256(Path(__file__))},
        "members": [
            {
                "path": "REPORT.md",
                "bytes": len(report_payload),
                "sha256": hashlib.sha256(report_payload).hexdigest(),
            },
            {
                "path": "summary.json",
                "bytes": len(summary_payload),
                "sha256": hashlib.sha256(summary_payload).hexdigest(),
            },
        ],
    }
    atomic_write(partial / "MANIFEST.json", json_bytes(manifest))
    os.replace(partial, OUTPUT)
    return {
        "status": summary["status"],
        "output": rel(OUTPUT),
        "report_sha256": sha256(REPORT),
        "summary_sha256": sha256(SUMMARY),
        "manifest_sha256": sha256(MANIFEST),
    }


def check() -> dict[str, Any]:
    required = [
        TOPUP_VALIDATION,
        PROMPT_SUMMARY,
        CATALOG,
        EPSILON_SMOKE,
        REVALIDATION1,
        REVALIDATION2,
        DELAYED_SUMMARY,
    ]
    return {
        "status": "READY" if all(path.is_file() for path in required) else "WAITING",
        "missing": [rel(path) for path in required if not path.is_file()],
        "output_exists": OUTPUT.exists(),
        "SIM_opened": False,
        "transport_launched": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true")
    action.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    result = check() if args.check else publish()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
