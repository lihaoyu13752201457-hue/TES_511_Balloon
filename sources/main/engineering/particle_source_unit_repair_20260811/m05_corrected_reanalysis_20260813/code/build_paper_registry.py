#!/usr/bin/env python3
"""Build the single M05 number/source and table/figure disposition registry."""

from __future__ import annotations

import csv
import json
import math
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

import check_inputs


HERE = Path(__file__).resolve()
PACKAGE = HERE.parent.parent
ROOT = check_inputs.ROOT
OUTPUT = PACKAGE / "outputs/07_paper_registry"
INPUTS = PACKAGE / "analysis_inputs.json"
ACTIVATION = PACKAGE / "outputs/02_activation/day15_summary.json"
DELAYED = PACKAGE / "outputs/03_delayed/summary.json"
COMMON = PACKAGE / "outputs/04_common_response/summary.json"
MATCHED = PACKAGE / "outputs/05_matched_comparison/summary.json"
MISSION = PACKAGE / "outputs/06_mission/summary.json"
GEOMETRIES = ("Mass_model_511", "S3d_O8")


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def manuscript_objects() -> list[dict[str, str]]:
    stage04 = relative(PACKAGE / "outputs/04_common_response")
    stage05 = relative(PACKAGE / "outputs/05_matched_comparison")
    stage06 = relative(PACKAGE / "outputs/06_mission")
    source_contract = "engineering/particle_source_unit_repair_20260811/data/source_contract_manifest.json"
    old_assets = "core_md/balloon511_ea_latex_drafts/paper_source_figure_table"
    return [
        {
            "manuscript_object_id": "fig_mass_model", "kind": "figure",
            "en_label": "fig:mass_model", "zh_label": "fig:mass_model",
            "disposition": "inherit_geometry_redraw_if_needed", "readiness": "READY_GEOMETRY_ONLY",
            "source_stage": "geometry authority",
            "source_artifacts": "engineering/Mass_model_511_nearfield_migration_20260701/00_manifest/authority_manifest.json",
            "reuse_target": f"{old_assets}/build_background_optimization_story_20260713.py (geometry-only renderer)",
            "scope_caveat": "Geometry is reusable; old simulation-derived annotations are not.",
        },
        {
            "manuscript_object_id": "fig_workflow", "kind": "figure",
            "en_label": "fig:workflow", "zh_label": "fig:workflow",
            "disposition": "redraw", "readiness": "READY_FOR_REGENERATION",
            "source_stage": "00-06", "source_artifacts": f"{relative(INPUTS)};{source_contract}",
            "reuse_target": f"{old_assets}/fig_simulation_workflow_m04_en_20260810.tex",
            "scope_caveat": "Remove the additive atmospheric mono-511 branch; corrected broadband gamma already contains the bump.",
        },
        {
            "manuscript_object_id": "fig_expacs_fullsphere_flux", "kind": "figure",
            "en_label": "fig:expacs_fullsphere_flux", "zh_label": "fig:expacs_fullsphere_flux",
            "disposition": "regenerate_corrected_energy_axis", "readiness": "READY_FOR_REGENERATION",
            "source_stage": "00/06", "source_artifacts": f"{source_contract};{relative(PACKAGE / 'data/parma_energy_integrated_family_scales_81bins.csv')}",
            "reuse_target": "core_md/balloon511_nima_latex_drafts/paper_resource/build_expacs_flux_figure.py",
            "scope_caveat": "Use corrected-keV spectra and dE-integrated mission ratios; do not reuse the legacy energy axis.",
        },
        {
            "manuscript_object_id": "fig_s33_poisson", "kind": "figure",
            "en_label": "fig:s33_poisson", "zh_label": "fig:s33_poisson",
            "disposition": "replace_hardcoded_inputs", "readiness": "PARTIAL_METHOD_FIGURE",
            "source_stage": "04/06", "source_artifacts": f"{stage04}/common_fullband_occupancy.csv;{stage06}/mission_timeline.csv",
            "reuse_target": f"{old_assets}/build_s33_poisson_normalization_figure.py",
            "scope_caveat": "Current mission live factor is analytic; the historical time-catalog coincidence counts are retired.",
        },
        {
            "manuscript_object_id": "fig_s33_spec_norm", "kind": "figure",
            "en_label": "fig:s33_spec_norm", "zh_label": "fig:s33_spec_norm",
            "disposition": "regenerate", "readiness": "READY_FOR_REGENERATION",
            "source_stage": "04", "source_artifacts": f"{stage04}/common_spectrum_480_550.csv",
            "reuse_target": f"{old_assets}/build_s33_spectra_figures.py",
            "scope_caveat": "Pivot the common long table by stream; do not fill delayed or science with synthetic zeros.",
        },
        {
            "manuscript_object_id": "fig_s33_spec_anti", "kind": "figure",
            "en_label": "fig:s33_spec_anti", "zh_label": "fig:s33_spec_anti",
            "disposition": "regenerate", "readiness": "READY_FOR_REGENERATION",
            "source_stage": "04", "source_artifacts": f"{stage04}/common_spectrum_480_550.csv",
            "reuse_target": f"{old_assets}/build_s33_spectra_figures.py",
            "scope_caveat": "Use the nominal exact-volume 50-keV veto domain.",
        },
        {
            "manuscript_object_id": "fig_s33_compton_mult", "kind": "figure",
            "en_label": "fig:s33_compton_mult", "zh_label": "fig:s33_compton_mult",
            "disposition": "regenerate", "readiness": "READY_FOR_REGENERATION",
            "source_stage": "04", "source_artifacts": f"{stage04}/common_multiplicity.csv",
            "reuse_target": f"{old_assets}/build_s33_spectra_figures.py",
            "scope_caveat": "Signal errors are fixed-trial binomial; background errors are weighted Poisson MC.",
        },
        {
            "manuscript_object_id": "fig_background_origin_story", "kind": "figure",
            "en_label": "fig:background_origin_story", "zh_label": "fig:background_origin_story_zh",
            "disposition": "redraw_as_corrected_comparison", "readiness": "READY_WITH_MC_CAVEATS",
            "source_stage": "05", "source_artifacts": f"{stage05}/mass_reference_w2_budget.csv;{stage05}/w2_delayed_parent_top10_plus_other.csv;{stage05}/w2_delayed_material_breakdown.csv",
            "reuse_target": f"{old_assets}/build_background_optimization_story_20260713.py",
            "scope_caveat": "Read particle names by key, remove atm511 sidecar, and do not present the comparison as proof of which individual layer caused the change.",
        },
        {
            "manuscript_object_id": "fig_optimized_mission_significance", "kind": "figure",
            "en_label": "fig:optimized_mission_significance", "zh_label": "fig:optimized_mission_significance_zh",
            "disposition": "regenerate_as_scenario", "readiness": "ANALYTIC_SCENARIO_ONLY",
            "source_stage": "06", "source_artifacts": f"{stage06}/mission_timeline.csv;{stage06}/mission_comparison.csv",
            "reuse_target": f"{old_assets}/build_background_optimization_story_20260713.py (mission panel)",
            "scope_caveat": "Synthetic trajectory and family-scalar fold; not corrected multipoint transport or final promotion authority.",
        },
        {
            "manuscript_object_id": "tab_background_source_model", "kind": "table",
            "en_label": "tab:background_source_model", "zh_label": "tab:background_source_model",
            "disposition": "rewrite", "readiness": "READY_FOR_REWRITE",
            "source_stage": "00", "source_artifacts": f"{source_contract};{relative(INPUTS)}",
            "reuse_target": "M05 table skeleton",
            "scope_caveat": "Corrected keV, eight families, unit_only_total_gamma, and no additive mono-511.",
        },
        {
            "manuscript_object_id": "tab_phase2_cutflow", "kind": "table",
            "en_label": "tab:phase2_cutflow", "zh_label": "tab:phase2_cutflow",
            "disposition": "recompute", "readiness": "READY_WITH_LOW_PROMPT_MC_SUPPORT",
            "source_stage": "04", "source_artifacts": f"{stage04}/common_cutflow.csv",
            "reuse_target": "M05 table skeleton",
            "scope_caveat": "Prompt W2 final support is only 7 Mass and 2 S3d events.",
        },
        {
            "manuscript_object_id": "tab_reference_background_budget", "kind": "table",
            "en_label": "tab:reference_background_budget", "zh_label": "tab:reference_background_budget_zh",
            "disposition": "recompute", "readiness": "READY_WITH_MC_CAVEATS",
            "source_stage": "05", "source_artifacts": f"{stage05}/mass_reference_w2_budget.csv",
            "reuse_target": "M05 table skeleton",
            "scope_caveat": "Mass constant-environment day-15 reference; separate counting and source-mixture uncertainty.",
        },
        {
            "manuscript_object_id": "tab_final_geometry", "kind": "table",
            "en_label": "tab:final_geometry", "zh_label": "tab:final_geometry_zh",
            "disposition": "inherit_geometry_reword_candidate", "readiness": "READY_GEOMETRY_ONLY",
            "source_stage": "geometry authority", "source_artifacts": "engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/data/s3d_o8_geometry_manifest.json",
            "reuse_target": "M05 table skeleton",
            "scope_caveat": "Include BPE20 and plastic10; call S3d-O8 the evaluated candidate rather than a promoted optimum.",
        },
        {
            "manuscript_object_id": "tab_optimized_cutflow", "kind": "table",
            "en_label": "tab:optimized_cutflow", "zh_label": "tab:optimized_cutflow_zh",
            "disposition": "recompute", "readiness": "READY_WITH_LOW_PROMPT_MC_SUPPORT",
            "source_stage": "04/05", "source_artifacts": f"{stage04}/background_prompt_delayed_cutflow.csv;{stage05}/matched_day15_comparison.csv",
            "reuse_target": "M05 table skeleton",
            "scope_caveat": "Report the matched candidate comparison, not a geometry promotion.",
        },
        {
            "manuscript_object_id": "tab_optimized_component_precision", "kind": "table",
            "en_label": "tab:optimized_component_precision", "zh_label": "tab:optimized_component_precision_zh",
            "disposition": "recompute", "readiness": "READY_WITH_SEPARATE_SYSTEMATICS",
            "source_stage": "04/05", "source_artifacts": f"{stage05}/w2_stream_family_budget.csv;{stage05}/w2_delayed_family_parent_material_supplement.csv",
            "reuse_target": "M05 table skeleton",
            "scope_caveat": "Garwood/MC counting, source-mixture TV, and holdout activity remain separate.",
        },
        {
            "manuscript_object_id": "tab_primary_sensitivity", "kind": "table",
            "en_label": "tab:primary_sensitivity", "zh_label": "tab:primary_sensitivity_zh",
            "disposition": "replace_with_scenario_table", "readiness": "ANALYTIC_SCENARIO_ONLY",
            "source_stage": "06", "source_artifacts": f"{stage06}/mission_comparison.csv",
            "reuse_target": "M05 table skeleton",
            "scope_caveat": "Top-of-atmosphere flux under a synthetic 20-day family-scalar scenario; final sensitivity remains blocked.",
        },
        {
            "manuscript_object_id": "claim_source_dominance", "kind": "claim",
            "en_label": "Results/Discussion source hierarchy", "zh_label": "结果/讨论中的源项排序",
            "disposition": "replace", "readiness": "READY_WITH_SPARSE_COMPONENT_FLAGS",
            "source_stage": "05", "source_artifacts": f"{stage05}/w2_delayed_parent_top10_plus_other.csv",
            "reuse_target": "M05 Results and Discussion",
            "scope_caveat": "Cu-62 is the current leading selected delayed parent; sparse one-event components must not be ranked strongly.",
        },
        {
            "manuscript_object_id": "claim_geometry_promotion", "kind": "claim",
            "en_label": "Abstract/Discussion/Conclusion promotion claim", "zh_label": "摘要/讨论/结论中的晋级结论",
            "disposition": "block", "readiness": "BLOCKED_FINAL_AUTHORITY",
            "source_stage": "05/06", "source_artifacts": f"{stage05}/summary.json;{stage06}/summary.json",
            "reuse_target": "M05 Abstract, Discussion, and Conclusion",
            "scope_caveat": "Central comparison favors S3d-O8, but prompt support and mission/systematic boundaries do not support final promotion.",
        },
    ]


def run(output: Path = OUTPUT) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f".{output.name}.work-", dir=output.parent))
    try:
        config = json.loads(INPUTS.read_text(encoding="utf-8"))
        activation = json.loads(ACTIVATION.read_text(encoding="utf-8"))
        delayed = json.loads(DELAYED.read_text(encoding="utf-8"))
        common = json.loads(COMMON.read_text(encoding="utf-8"))
        matched = json.loads(MATCHED.read_text(encoding="utf-8"))
        mission = json.loads(MISSION.read_text(encoding="utf-8"))
        entries: list[dict[str, Any]] = []

        def add(key: str, value: Any, unit: str, source: Path, selector: str, evidence: str, caveat: str = "") -> None:
            entries.append({
                "numeric_key": key, "value": value, "unit": unit, "source_path": relative(source),
                "source_selector": selector, "evidence_status": evidence, "scope_caveat": caveat,
            })

        expected = config["expected_selection_summary"]
        for mode in ("instant", "buildup"):
            add(f"transport.{mode}.jobs", expected["by_mode"][mode]["jobs"], "jobs", INPUTS, f"expected_selection_summary.by_mode.{mode}.jobs", "COMPLETE")
            add(f"transport.{mode}.histories", expected["by_mode"][mode]["histories"], "primary histories", INPUTS, f"expected_selection_summary.by_mode.{mode}.histories", "COMPLETE")
        add("transport.total.jobs", expected["totals"]["jobs"], "jobs", INPUTS, "expected_selection_summary.totals.jobs", "COMPLETE")
        add("transport.total.histories", expected["totals"]["histories"], "primary histories", INPUTS, "expected_selection_summary.totals.histories", "COMPLETE")
        add("delayed.transport.triggers", delayed["transport_triggers"], "triggers", DELAYED, "transport_triggers", "COMPLETE_GROUND_STATE")

        activation_by_geometry = {row["geometry"]: row for row in activation["day15_by_geometry"]}
        for geometry in GEOMETRIES:
            short = "mass" if geometry == "Mass_model_511" else "s3d_o8"
            act = activation_by_geometry[geometry]
            for field in ("known_all_state_activity_Bq", "transported_ground_activity_Bq", "known_holdout_activity_Bq"):
                add(f"activation.{short}.{field}", act[field], "Bq", ACTIVATION, f"day15_by_geometry[{geometry}].{field}", "COMPLETE_CONSTANT_ENVIRONMENT_DAY15")
            w2 = common["final_measured"][geometry]["w2_510p58_511p42"]
            signal = common["final_measured"][geometry]["signal_w2_510p58_511p42"]
            for stream in ("prompt", "delayed"):
                add(f"response.{short}.w2.{stream}.events", w2[f"{stream}_events"], "MC events", COMMON, f"final_measured.{geometry}.w2_510p58_511p42.{stream}_events", "LOW_MC_SUPPORT" if stream == "prompt" else "COMPLETE_MC_COUNTING")
                add(f"response.{short}.w2.{stream}.rate", w2[f"{stream}_rate_cps"], "cps", COMMON, f"final_measured.{geometry}.w2_510p58_511p42.{stream}_rate_cps", "LOW_MC_SUPPORT" if stream == "prompt" else "COMPLETE_MC_COUNTING")
                add(f"response.{short}.w2.{stream}.mc_sigma", w2[f"{stream}_stat_sigma_cps"], "cps", COMMON, f"final_measured.{geometry}.w2_510p58_511p42.{stream}_stat_sigma_cps", "MC_COUNTING_ONLY")
            add(f"response.{short}.w2.total_background.rate", w2["total_background_rate_cps"], "cps", COMMON, f"final_measured.{geometry}.w2_510p58_511p42.total_background_rate_cps", "CENTRAL_WITH_CAVEATS")
            add(f"response.{short}.w2.total_background.mc_sigma", w2["total_background_stat_sigma_cps"], "cps", COMMON, f"final_measured.{geometry}.w2_510p58_511p42.total_background_stat_sigma_cps", "MC_COUNTING_ONLY")
            add(f"signal.{short}.w2.selected_events", signal["selected_events"], "events", COMMON, f"final_measured.{geometry}.signal_w2_510p58_511p42.selected_events", "COMPLETE_POST_BE_SCOPE")
            add(f"signal.{short}.w2.selected_aeff", signal["selected_effective_area_cm2"], "cm2", COMMON, f"final_measured.{geometry}.signal_w2_510p58_511p42.selected_effective_area_cm2", "COMPLETE_POST_BE_SCOPE", "Conditional on the post-Be EventList injection plane.")
            mission_geometry = mission["geometries"][geometry]
            for field, unit in (
                ("Z20d", "sigma"), ("T3_day", "day"), ("T5_day", "day"),
                ("flux_3sigma_20d_ph_cm2_s", "ph cm-2 s-1"),
                ("Z20d_conditional_endpoint_proxy", "sigma"),
                ("flux_3sigma_20d_conditional_endpoint_proxy_ph_cm2_s", "ph cm-2 s-1"),
            ):
                add(f"mission_scenario.{short}.{field}", mission_geometry[field], unit, MISSION, f"geometries.{geometry}.{field}", "ANALYTIC_FAMILY_SCALAR_SCENARIO", "Not corrected multipoint transport or final sensitivity authority.")

        mass_w2 = common["final_measured"]["Mass_model_511"]["w2_510p58_511p42"]
        o8_w2 = common["final_measured"]["S3d_O8"]["w2_510p58_511p42"]
        mass_signal = common["final_measured"]["Mass_model_511"]["signal_w2_510p58_511p42"]
        o8_signal = common["final_measured"]["S3d_O8"]["signal_w2_510p58_511p42"]
        background_ratio = o8_w2["total_background_rate_cps"] / mass_w2["total_background_rate_cps"]
        signal_ratio = o8_signal["selected_effective_area_cm2"] / mass_signal["selected_effective_area_cm2"]
        fom_ratio = (
            o8_signal["selected_effective_area_cm2"] / math.sqrt(o8_w2["total_background_rate_cps"])
        ) / (
            mass_signal["selected_effective_area_cm2"] / math.sqrt(mass_w2["total_background_rate_cps"])
        )
        add("comparison.day15.background.s3d_to_mass", background_ratio, "ratio", MATCHED, "w2.total_background.central_ratio", "CENTRAL_WITH_CAVEATS")
        add("comparison.signal_aeff.s3d_to_mass", signal_ratio, "ratio", COMMON, "derived from final_measured signal W2 Aeff", "COMPLETE_POST_BE_SCOPE")
        add("comparison.day15.detector_plane_fom.s3d_to_mass", fom_ratio, "ratio", MATCHED, "Aeff/sqrt(B) central ratio", "DIAGNOSTIC_ONLY")
        for geometry in GEOMETRIES:
            short = "mass" if geometry == "Mass_model_511" else "s3d_o8"
            top = matched["top_delayed_parents"][geometry][0]
            add(f"source.{short}.top_delayed_parent_ZA", int(top["source_parent_ZA"]), "ZA", MATCHED, f"top_delayed_parents.{geometry}[0].source_parent_ZA", "SELECTED_DAY15_CENTRAL")
            add(f"source.{short}.top_delayed_parent_rate", top["rate_cps"], "cps", MATCHED, f"top_delayed_parents.{geometry}[0].rate_cps", "SELECTED_DAY15_CENTRAL")

        objects = manuscript_objects()
        status = "PASS__M05_PAPER_NUMBER_AND_OBJECT_REGISTRY_READY__MANUSCRIPT_NOT_EDITED"
        numbers = {
            "schema_version": 1,
            "status": status,
            "authority_boundary": (
                "SINGLE_NUMBER_SOURCE_FOR_M05_REWRITE__MISSION_VALUES_REMAIN_ANALYTIC_SCENARIO__"
                "FINAL_GEOMETRY_PROMOTION_BLOCKED"
            ),
            "entries": {row["numeric_key"]: {key: value for key, value in row.items() if key != "numeric_key"} for row in entries},
        }
        write_csv(work / "number_source_map.csv", entries)
        write_csv(work / "manuscript_object_registry.csv", objects)
        (work / "paper_numbers.json").write_text(json.dumps(numbers, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        readiness_counts: dict[str, int] = {}
        for row in objects:
            readiness_counts[row["readiness"]] = readiness_counts.get(row["readiness"], 0) + 1
        summary = {
            "schema_version": 1, "status": status,
            "numeric_key_count": len(entries), "manuscript_object_count": len(objects),
            "readiness_counts": readiness_counts,
            "old_m05_simulation_numbers": "RETIRED__DO_NOT_COPY",
            "next_step": "regenerate tables/figures from this registry, then update English and Chinese M05 Methods/Results as a pair",
            "authority_boundary": numbers["authority_boundary"],
        }
        (work / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        report = [
            "# M05 paper registry", "", f"Status: `{status}`", "",
            f"The registry exposes {len(entries)} numeric keys and maps {len(objects)} M05 figures, tables, and claims to their corrected sources.", "",
            "## Rewrite boundary", "",
            "- Geometry and Methods contracts are ready to inherit or redraw.",
            "- Constant-environment day-15 response and matched comparison tables are ready with explicit MC/source-mixture caveats.",
            "- Mission values are an analytic family-scalar scenario, not corrected multipoint transport or final sensitivity authority.",
            "- The old M05 simulation-derived rates, nuclide hierarchy, sensitivity, and promotion claims are retired.",
            "", "## Headline replacement numbers", "",
            "| Metric | Mass | S3d-O8 |", "|---|---:|---:|",
            f"| Constant-environment day-15 W2 background (cps) | {mass_w2['total_background_rate_cps']:.6g} | {o8_w2['total_background_rate_cps']:.6g} |",
            f"| Selected W2 signal Aeff (cm2) | {mass_signal['selected_effective_area_cm2']:.6g} | {o8_signal['selected_effective_area_cm2']:.6g} |",
            f"| Analytic-scenario Z20 | {mission['geometries']['Mass_model_511']['Z20d']:.6g} | {mission['geometries']['S3d_O8']['Z20d']:.6g} |",
            f"| Analytic-scenario F3, 20 d (ph cm-2 s-1) | {mission['geometries']['Mass_model_511']['flux_3sigma_20d_ph_cm2_s']:.6g} | {mission['geometries']['S3d_O8']['flux_3sigma_20d_ph_cm2_s']:.6g} |",
            "",
        ]
        (work / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
        manifest = {
            "schema_version": 1, "status": status, "analysis_code": relative(HERE),
            "inputs": [relative(path) for path in (INPUTS, ACTIVATION, DELAYED, COMMON, MATCHED, MISSION)],
            "outputs": ["manuscript_object_registry.csv", "number_source_map.csv", "paper_numbers.json", "summary.json", "REPORT.md"],
            "hash_policy": "small source paths and selectors only; no raw SIM copy or large-artifact hash pass",
        }
        (work / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.rename(work, output)
        print(f"{status}: {output}")
        return summary
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise


if __name__ == "__main__":
    run()
