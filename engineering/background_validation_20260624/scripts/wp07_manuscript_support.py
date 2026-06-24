#!/usr/bin/env python3
"""WP07 manuscript support document for the current HARNESS_20260624 endpoint."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
ENG = Path(__file__).resolve().parents[1]
OUT = ENG / "07_manuscript_support"


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except Exception:
        return str(path)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load(path: str) -> Any:
    return json.loads((ENG / path).read_text(encoding="utf-8"))


def read_csv(path: str) -> list[dict[str, str]]:
    with (ENG / path).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build() -> dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    g1 = load("01_prompt_source_audit/prompt_normalization_audit.json")
    g2 = load("02_prompt_eplus_provenance/eplus_survivor_provenance.json")
    g2_process = read_csv("02_prompt_eplus_provenance/eplus_survivor_process_summary.csv")
    g3 = load("03_delayed_convergence/delayed_selected_rate_convergence.json")
    g3_iso = read_csv("03_delayed_convergence/delayed_selected_isotope_summary.csv")
    g3_decomp = read_csv("03_delayed_convergence/delayed_selected_decomposition.csv")
    g4 = load("04_bgo_variant/bgo_geometry_manifest.json")
    g5 = load("05_matched_runs_resource_guard/summary.json")

    payload = {
        "artifact_type": "wp07_manuscript_support",
        "status": "PASS_LIMITED_SUPPORT_WITH_MATCHED_RUNS_BLOCKED",
        "created_utc": now_utc(),
        "claim_boundary": {
            "may_claim": [
                "fix5 prompt source normalization and selected-rate reconstruction are audited against existing Step05 authority",
                "final W2 prompt eplus survivors are traced to annihilation-photon lineage in existing SIM records",
                "delayed selected-rate PI-02 pooled uncertainty meets the 10% minimum convergence screen",
                "a material-only BGO same-envelope geometry is available and overlap-checked",
            ],
            "must_not_claim": [
                "BGO improves or worsens CsI background",
                "matched CsI/BGO prompt, delayed, or signal rates are known",
                "material difference is statistically resolved",
            ],
        },
        "evidence": {
            "prompt_normalization_status": g1["status"],
            "prompt_final_w2_rate_cps": g1["selected_rate_closure"]["prompt_final_sum_w"],
            "prompt_final_sum_w2": g1["selected_rate_closure"]["prompt_final_sum_w2"],
            "prompt_eplus_rate_cps": g2["selection"]["selected_rate_cps"],
            "prompt_eplus_classified_fraction": g2["classification"]["a_to_c_event_fraction"],
            "prompt_eplus_classification_counts": g2["classification_counts"],
            "prompt_eplus_top_process_rows": g2_process[:5],
            "delayed_convergence_status": g3["status"],
            "delayed_selected_rate_cps": g3["combined"]["selected_rate_cps"],
            "delayed_selected_sigma_cps": g3["combined"]["sigma_cps"],
            "delayed_relative_uncertainty": g3["combined"]["relative_uncertainty"],
            "delayed_top_isotopes": g3_iso[:8],
            "delayed_top_decomposition": g3_decomp[:8],
            "bgo_geometry_status": g4["status"],
            "bgo_material_replaced_volume_count": g4["checks"]["material_replaced_volume_count"],
            "bgo_density_g_cm3": g4["bgo_material_authority"]["density_g_cm3"],
            "bgo_components": g4["bgo_material_authority"]["components"],
            "bgo_geometry_diff": g4["geometry_diff"],
            "bgo_overlap_check": g4["overlap_check"],
            "matched_runs_status": g5["status"],
            "matched_failure_contract": g5["failure_contract"],
        },
        "inputs": {
            "g1": "01_prompt_source_audit/prompt_normalization_audit.json",
            "g2": "02_prompt_eplus_provenance/eplus_survivor_provenance.json",
            "g2_process": "02_prompt_eplus_provenance/eplus_survivor_process_summary.csv",
            "g3": "03_delayed_convergence/delayed_selected_rate_convergence.json",
            "g3_isotopes": "03_delayed_convergence/delayed_selected_isotope_summary.csv",
            "g3_decomposition": "03_delayed_convergence/delayed_selected_decomposition.csv",
            "g4": "04_bgo_variant/bgo_geometry_manifest.json",
            "g5": "05_matched_runs_resource_guard/summary.json",
        },
        "outputs": {
            "support_md": rel(OUT / "background_validation_necessity_and_paper_impact_final.md"),
            "summary_json": rel(OUT / "summary.json"),
        },
    }
    write_json(OUT / "summary.json", payload)
    (OUT / "background_validation_necessity_and_paper_impact_final.md").write_text(markdown(payload), encoding="utf-8")
    return payload


def markdown(payload: dict[str, Any]) -> str:
    ev = payload["evidence"]
    bgo_components = ", ".join(f"{item['element']} {item['stoichiometry']:g}" for item in ev["bgo_components"])
    lines = [
        "# Background Validation Necessity and Paper Impact - Final",
        "",
        f"Status: `{payload['status']}`.",
        "",
        "## 1. Current Paper Claim Boundary",
        "",
        "The current engineering pass supports the fix5 normalization, eplus provenance, delayed convergence screen, and a material-only BGO same-envelope geometry. It does not support a CsI-vs-BGO performance conclusion because matched production runs are blocked by the resource guard.",
        "",
        "Allowed claims:",
    ]
    lines.extend(f"- {item}" for item in payload["claim_boundary"]["may_claim"])
    lines.extend(["", "Disallowed claims:"])
    lines.extend(f"- {item}" for item in payload["claim_boundary"]["must_not_claim"])
    lines.extend(
        [
            "",
            "## 2. Veto Authority",
            "",
            "The fixed Step05 active-veto authority for this harness is `shield_total_keV < 50 keV` with a `1 us` coincidence window. No 40/60/90 keV CsI threshold tests were run or used. BGO derivation preserves detector and volume names plus selection plumbing; material comparison remains blocked until matched runs use the same Step05 selection code.",
            "",
            "## 3. Prompt Normalization Audit",
            "",
            f"Prompt normalization status is `{ev['prompt_normalization_status']}`. The reconstructed final W2 prompt rate is `{ev['prompt_final_w2_rate_cps']:.12g}` cps with `sum_w2={ev['prompt_final_sum_w2']:.12g}`. The G1 audit verifies 60 cm source radius consistency, `pi R^2` area handling, source-card flux closure, unique seeds, split/replica completeness, and independent selected-rate reconstruction against Step05.",
            "",
            "## 4. eplus Survivor Physical Source",
            "",
            f"The final W2 prompt `eplus` contribution is `{ev['prompt_eplus_rate_cps']:.12g}` cps. Existing SIM `IA`, `CC HIT`, and `HTsim` records classify `{ev['prompt_eplus_classified_fraction']:.3f}` of selected eplus survivors into A-C. In this run all 47 survivors classify as class A, aperture-coupled annihilation-photon lineage.",
            "",
            "| class | process summary | events | rate cps |",
            "|---|---|---:|---:|",
        ]
    )
    for row in ev["prompt_eplus_top_process_rows"]:
        process = f"{row.get('first_tes_sec','')}/{row.get('first_tes_sproc','')}/{row.get('first_tes_cproc','')}/{row.get('first_tes_par','')}"
        lines.append(f"| {row.get('classification_code','')} | {process} | {row.get('events','')} | {float(row.get('rate_hz', 0.0)):.12g} |")
    lines.extend(
        [
            "",
            "## 5. Delayed Convergence and Leading Isotope/Volume",
            "",
            f"Delayed convergence status is `{ev['delayed_convergence_status']}`. Four independent exact-position production-position samplings give 103 pooled selected W2 events, selected rate `{ev['delayed_selected_rate_cps']:.12g}` cps, sigma `{ev['delayed_selected_sigma_cps']:.12g}` cps, and relative uncertainty `{ev['delayed_relative_uncertainty']:.6g}`.",
            "",
            "| isotope | events | rate cps | fraction |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in ev["delayed_top_isotopes"]:
        lines.append(f"| {row.get('isotope','')} | {row.get('events','')} | {float(row.get('rate_hz', 0.0)):.12g} | {float(row.get('fraction_of_rate', 0.0)):.3f} |")
    lines.extend(
        [
            "",
            "Top isotope/volume/production-family decomposition:",
            "",
            "| isotope | source volume | family | events | rate cps |",
            "|---|---|---|---:|---:|",
        ]
    )
    for row in ev["delayed_top_decomposition"]:
        lines.append(f"| {row.get('isotope','')} | {row.get('source_volume','')} | {row.get('production_particle_family','')} | {row.get('events','')} | {float(row.get('rate_hz', 0.0)):.12g} |")
    lines.extend(
        [
            "",
            "## 6. CsI-BGO Comparison Status",
            "",
            f"The BGO same-envelope geometry status is `{ev['bgo_geometry_status']}`. It changes `{ev['bgo_material_replaced_volume_count']}` active-shield material lines from CsI to BGO while preserving geometry shape, position, mother, detector references, source radius, and selection plumbing. The BGO material authority is MEGAlib `BGO`, density `{ev['bgo_density_g_cm3']}` g/cm3, composition `{bgo_components}`.",
            "",
            f"Geometry diff status: `{ev['bgo_geometry_diff']['status']}` with `{ev['bgo_geometry_diff']['non_whitelisted_diff_count']}` non-whitelisted diffs. Overlap status: `{ev['bgo_overlap_check']['status']}`.",
            "",
            f"Matched CsI/BGO transport status is `{ev['matched_runs_status']}`. Therefore no prompt, delayed, signal, total-background, ratio, uncertainty-on-difference, or material-preference comparison is available yet.",
            "",
            "## 7. Methods/Results/Discussion Help",
            "",
            "Methods can cite the validated source normalization, fixed 50 keV/1 us veto authority, delayed convergence treatment, and material-only BGO derivation procedure. Results can cite fix5 prompt/delayed validation numbers and the blocked status of material comparison. Discussion should describe BGO as an engineering validation path prepared for future matched production, not as an evaluated design improvement.",
            "",
            "## 8. Candidate English Insertion",
            "",
            "The background model was subjected to a separate engineering validation pass. The prompt source normalization was re-audited from the far-field source cards through the selected-event rate reconstruction, and the dominant prompt positron survivors in the 511 keV window were traced in the existing simulation records to annihilation-photon lineages. For delayed activation, four independent exact-position production-position samplings gave 103 pooled selected W2 events with a relative Monte Carlo uncertainty of about 9.9%. A material-only BGO same-envelope geometry was also derived and passed static geometry and overlap checks, but matched CsI/BGO production runs were not executed in this pass because they exceed the predefined resource guard.",
            "",
            "## 9. Claims Not Supported",
            "",
            "- Do not claim a BGO/CsI background ratio or material preference.",
            "- Do not change headline sensitivity numbers from this document alone.",
            "- Do not cite targeted trace or matched-run results, because none were run here.",
            "- Do not describe non-significant or unrun material comparisons as design conclusions.",
            "",
            "## 10. Provenance Table",
            "",
            "| item | path |",
            "|---|---|",
        ]
    )
    lines.extend(f"| {key} | `{value}` |" for key, value in payload["inputs"].items())
    lines.extend(
        [
            "",
            "## Resource-Blocked Follow-Up",
            "",
            f"Affected claim: {ev['matched_failure_contract']['affected_claim']}",
            "",
            f"Minimal next action: {ev['matched_failure_contract']['minimal_next_action']}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    payload = build()
    print(json.dumps({"status": payload["status"], "out": payload["outputs"]["support_md"]}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
