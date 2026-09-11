#!/usr/bin/env python3
"""Build the final manuscript review-packet manifest and validation log."""

from __future__ import annotations

import csv
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
R2 = ROOT / "reports2.0"
MANUSCRIPT = R2 / "07_NIMA_MANUSCRIPT"
VALIDATION = R2 / "06_VALIDATION"


ARTIFACTS = [
    ("07_NIMA_MANUSCRIPT/nima_detailed_paper_zh.pdf", "detailed Chinese NIMA-style PDF"),
    ("07_NIMA_MANUSCRIPT/nima_detailed_paper_zh.html", "detailed Chinese NIMA-style HTML"),
    ("07_NIMA_MANUSCRIPT/nima_detailed_paper_zh.md", "detailed Chinese source-index Markdown"),
    ("07_NIMA_MANUSCRIPT/tes511_balloon_background_nima_en.pdf", "English NIMA-style PDF"),
    ("07_NIMA_MANUSCRIPT/tes511_balloon_background_nima_en.html", "English NIMA-style HTML"),
    ("07_NIMA_MANUSCRIPT/tes511_balloon_background_nima_en.md", "English NIMA-style Markdown draft"),
    ("07_NIMA_MANUSCRIPT/tes511_balloon_background_nima_zh.pdf", "Chinese NIMA-style short PDF"),
    ("07_NIMA_MANUSCRIPT/tes511_balloon_background_nima_zh.html", "Chinese NIMA-style short HTML"),
    ("07_NIMA_MANUSCRIPT/tes511_balloon_background_nima_zh.md", "Chinese NIMA-style short Markdown draft"),
    ("07_NIMA_MANUSCRIPT/final_numerical_lineage.csv", "final numerical lineage table"),
    ("07_NIMA_MANUSCRIPT/final_numerical_lineage.json", "final numerical lineage JSON"),
    ("07_NIMA_MANUSCRIPT/references.bib", "bibliography"),
    ("memoryforPPT.md", "updatable context memory for the Phase07-12 progress PPT"),
    ("PPT_FULL_PROGRESS_REPORT/cosmosray_bg_2605_nima_foundation_phase08_12_extension_report.pptx", "primary NIMA-centered Phase08-12 extension PowerPoint"),
    ("PPT_FULL_PROGRESS_REPORT/cosmosray_bg_2605_phase07_12_progress_report.pptx", "detailed Phase07-12 progress PowerPoint"),
    ("PPT_FULL_PROGRESS_REPORT/phase07_12_progress_report.md", "Markdown source summary for the Phase07-12 progress PPT"),
    ("PPT_FULL_PROGRESS_REPORT/memoryforPPT.md", "local copy of PPT context memory"),
    ("PPT_FULL_PROGRESS_REPORT/ppt_manifest.csv", "Phase07-12 progress PPT artifact manifest"),
    ("03_NEXT_PHASE_SUPPORT/optics_focused_gamma_background/focused_gamma_background_summary.csv", "focused gamma background rate ledger"),
    ("03_NEXT_PHASE_SUPPORT/optics_focused_gamma_background/focused_gamma_sensitivity_addendum.csv", "focused gamma sensitivity addendum"),
    ("03_NEXT_PHASE_SUPPORT/activation_rpip_sampling/activation_geometry_volume_summary.csv", "activation geometry group summary"),
    ("03_NEXT_PHASE_SUPPORT/activation_rpip_sampling/plot_check_day15_2602.png", "RPIP day-15 sampling evidence"),
    ("03_NEXT_PHASE_SUPPORT/parent_feed_data_note/top511_parent_feed_data_note.md", "parent-feed top-contributor data note"),
    ("04_FIGURES/nima_update/rpip_sampling_geometry_context.png", "RPIP sampling with geometry context"),
    ("04_FIGURES/nima_update/activation_geometry_volume_map.png", "activation geometry volume map"),
    ("04_FIGURES/nima_update/optics_focused_gamma_background_addendum.png", "focused gamma addendum figure"),
    ("04_FIGURES/nima_update/nima_small_stat_dashboard.png", "small statistical dashboard"),
    ("08_DESIGN_OPTIMIZATION_ADDON/WP_D5_design_recommendation/design_optimization_summary.md", "add-on design optimization summary"),
    ("08_DESIGN_OPTIMIZATION_ADDON/WP_D5_design_recommendation/design_recommendation_table.csv", "add-on design recommendation table"),
    ("08_DESIGN_OPTIMIZATION_ADDON/WP_D5_design_recommendation/minimal_delta_variant_screen.csv", "V1/V2/V3 minimal variant screen"),
    ("08_DESIGN_OPTIMIZATION_ADDON/WP_D1_selection_pareto_highstat/selection_pareto_highstat.csv", "high-stat selection Pareto table"),
    ("08_DESIGN_OPTIMIZATION_ADDON/WP_D1_selection_pareto_highstat/highstat_q_vs_background.png", "high-stat Q versus background plot"),
    ("08_DESIGN_OPTIMIZATION_ADDON/WP_D1_selection_pareto_highstat/highstat_source_acceptance_vs_background.png", "high-stat source acceptance versus background plot"),
    ("08_DESIGN_OPTIMIZATION_ADDON/WP_D3_material_geometry_bound/removal_bound_table.csv", "activation material/geometry removal bound"),
    ("09_SOURCE_CASES_ABC/source_case_summary.md", "A/B/C 511-keV source-case summary"),
    ("09_SOURCE_CASES_ABC/source_case_summary.json", "A/B/C source-case machine summary"),
    ("09_SOURCE_CASES_ABC/source_case_rates.csv", "A/B/C source-case folded rate table"),
    ("09_SOURCE_CASES_ABC/detectability_A_GC_POINT.csv", "A source point-source detectability table"),
    ("09_SOURCE_CASES_ABC/diffuse_aperture_foreground.csv", "B diffuse FoV aperture foreground table"),
    ("09_SOURCE_CASES_ABC/v404_bandpass_loss.csv", "C V404 bandpass-risk table"),
    ("09_SOURCE_CASES_ABC/cosima_source_manifest.csv", "A/C point-source Cosima source manifest; B intentionally skipped"),
    ("09_SOURCE_CASES_ABC/figures/A_GC_POINT_detectability.png", "A source detectability figure"),
    ("09_SOURCE_CASES_ABC/figures/B_diffuse_flux_fraction_vs_fov.png", "B diffuse FoV fraction figure"),
    ("09_SOURCE_CASES_ABC/figures/B_diffuse_expected_line_background.png", "B diffuse foreground rate figure"),
    ("09_SOURCE_CASES_ABC/figures/abc_source_spectra_and_bandpass.png", "A/B/C source spectra and placeholder bandpass figure"),
    ("10_POINT_DIFFUSE_DISCRIMINATION/README.md", "Phase 10 point/diffuse discrimination scaffold entry"),
    ("10_POINT_DIFFUSE_DISCRIMINATION/phase10_summary.json", "Phase 10 machine summary"),
    ("10_POINT_DIFFUSE_DISCRIMINATION/point_diffuse_discrimination.csv", "A compact-source vs B diffuse-null discrimination table"),
    ("10_POINT_DIFFUSE_DISCRIMINATION/selection_best_measured_energy_audit.csv", "selection-only best measured-energy audit"),
    ("10_POINT_DIFFUSE_DISCRIMINATION/optics_requirements_matrix.csv", "511-keV optics requirements matrix"),
    ("10_POINT_DIFFUSE_DISCRIMINATION/source_case_manifest_phase10.csv", "Phase 10 source-case manifest and run status guard"),
    ("10_POINT_DIFFUSE_DISCRIMINATION/claim_control_phase10.md", "Phase 10 claim-control guard"),
    ("10_POINT_DIFFUSE_DISCRIMINATION/phase10_validation.md", "Phase 10 dedicated validation report"),
    ("10_POINT_DIFFUSE_DISCRIMINATION/figures/A_vs_B_expected_counts.png", "Phase 10 A-vs-B counts figure"),
    ("10_POINT_DIFFUSE_DISCRIMINATION/figures/A_vs_B_detection_probability.png", "Phase 10 probability figure with placeholder penalties"),
    ("10_POINT_DIFFUSE_DISCRIMINATION/figures/B_diffuse_foreground_fov_scan.png", "B diffuse FoV monotonicity figure"),
    ("10_POINT_DIFFUSE_DISCRIMINATION/figures/selection_best_true_vs_measured.png", "selection true-vs-measured audit figure"),
    ("10_POINT_DIFFUSE_DISCRIMINATION/figures/phase10_claim_boundary_map.png", "Phase 10 claim-boundary map"),
    ("11_METRIC_RECONCILIATION_AND_OPTICS_GATE/README.md", "Phase 11 metric reconciliation and optics gate entry"),
    ("11_METRIC_RECONCILIATION_AND_OPTICS_GATE/phase11_summary.json", "Phase 11 machine summary"),
    ("11_METRIC_RECONCILIATION_AND_OPTICS_GATE/metric_crosswalk_phase11.csv", "Phase 11 metric crosswalk table"),
    ("11_METRIC_RECONCILIATION_AND_OPTICS_GATE/metric_crosswalk_phase11.json", "Phase 11 metric crosswalk machine output"),
    ("11_METRIC_RECONCILIATION_AND_OPTICS_GATE/phase10_vs_phase9_number_reconciliation.md", "Phase 10 vs Phase 9 number reconciliation"),
    ("11_METRIC_RECONCILIATION_AND_OPTICS_GATE/phase10_vs_phase9_number_reconciliation.json", "Phase 10 vs Phase 9 number reconciliation machine output"),
    ("11_METRIC_RECONCILIATION_AND_OPTICS_GATE/selection_best_upgrade_decision.md", "selection-only upgrade decision"),
    ("11_METRIC_RECONCILIATION_AND_OPTICS_GATE/selection_best_upgrade_decision.json", "selection-only upgrade decision machine output"),
    ("11_METRIC_RECONCILIATION_AND_OPTICS_GATE/optics_response_511_production_schema.yaml", "production optics schema gate"),
    ("11_METRIC_RECONCILIATION_AND_OPTICS_GATE/optics_requirements_matrix_v2.csv", "Phase 11 optics requirements matrix v2"),
    ("11_METRIC_RECONCILIATION_AND_OPTICS_GATE/point_diffuse_template_TS_phase11.csv", "Phase 11 A+B vs B-only template TS scaffold"),
    ("11_METRIC_RECONCILIATION_AND_OPTICS_GATE/point_diffuse_template_TS_phase11.json", "Phase 11 template TS scaffold machine summary"),
    ("11_METRIC_RECONCILIATION_AND_OPTICS_GATE/claim_control_phase11.md", "Phase 11 claim-control guard"),
    ("11_METRIC_RECONCILIATION_AND_OPTICS_GATE/claim_control_phase11.json", "Phase 11 claim-control machine guard"),
    ("11_METRIC_RECONCILIATION_AND_OPTICS_GATE/figures/metric_F3_comparison.png", "Phase 11 metric F3 comparison"),
    ("11_METRIC_RECONCILIATION_AND_OPTICS_GATE/figures/metric_P3_comparison.png", "Phase 11 metric P3 comparison"),
    ("11_METRIC_RECONCILIATION_AND_OPTICS_GATE/figures/selection_upgrade_decision_tree.png", "Phase 11 selection upgrade gate figure"),
    ("11_METRIC_RECONCILIATION_AND_OPTICS_GATE/figures/optics_schema_overview.png", "Phase 11 optics schema overview"),
    ("11_METRIC_RECONCILIATION_AND_OPTICS_GATE/figures/point_diffuse_TS_projection.png", "Phase 11 template TS projection"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/README.md", "Phase 12 terminal final compact-source analysis entry"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/FINAL_DECISION.md", "Phase 12 final A/B/C decision"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/final_claim_control.md", "Phase 12 final claim-control guard"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/phase12_summary.json", "Phase 12 final machine summary"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/inputs_manifest_final.csv", "Phase 12 final inputs manifest"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/authority_manifest_final.csv", "Phase 12 final authority manifest"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/metric_closure_final.csv", "Phase 12 final metric closure table"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/metric_closure_final.json", "Phase 12 final metric closure machine output"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/phase9_phase10_phase12_reconciliation.md", "Phase 9/10/12 final metric reconciliation"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/selection_upgrade_decision_final.md", "Phase 12 final selection upgrade decision"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/selection_upgrade_decision_final.json", "Phase 12 final selection upgrade machine output"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/optics_model_status_final.md", "Phase 12 final optics model status"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/optics_model_status_final.json", "Phase 12 final optics machine status"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/optics_requirements_final.csv", "Phase 12 final optics requirements table"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/requirements_closure_final.csv", "Phase 12 final requirements closure table"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/AB_template_likelihood_final.csv", "Phase 12 final A+B vs B-only template likelihood"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/AB_template_likelihood_final.json", "Phase 12 final template likelihood machine output"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/AB_injection_recovery_final.csv", "Phase 12 deterministic injection-recovery proxy"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/source_case_status_final.csv", "Phase 12 final source-case status table"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/final_tables_for_paper/table_metric_closure_final.csv", "Phase 12 final paper metric table"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/final_tables_for_paper/table_AB_detectability_final.csv", "Phase 12 final paper A/B detectability table"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/final_tables_for_paper/table_optics_requirements_final.csv", "Phase 12 final paper optics requirements table"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/final_tables_for_paper/table_claim_boundary_final.csv", "Phase 12 final paper claim boundary table"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/final_figures/metric_closure_phase9_phase10_phase12.png", "Phase 12 final metric closure figure"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/final_figures/AB_template_overlap.png", "Phase 12 final A/B template overlap figure"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/final_figures/TS_vs_A_flux.png", "Phase 12 final TS-vs-flux figure"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/final_figures/exposure_requirement_vs_flux.png", "Phase 12 final exposure requirement figure"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/validation/validate_final_workspace_summary.json", "Phase 12 final validation summary"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/first_principles_channeling_optics/README.md", "first-principles channeling optics coupling entry"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/first_principles_channeling_optics/focal_spot_discrepancy_error_sources_for_gptpro.md", "first-principles focal-spot discrepancy handoff for external review"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/first_principles_channeling_optics/first_principles_model_freeze.json", "first-principles optics frozen model card"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/first_principles_channeling_optics/first_principles_onaxis_summary.json", "canonical first-principles on-axis summary"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/first_principles_channeling_optics/first_principles_onaxis_samples.csv", "canonical first-principles L2 on-axis ray samples"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/first_principles_channeling_optics/first_principles_optics_coupling_summary.json", "first-principles optics coupling machine summary"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/first_principles_channeling_optics/phase12_firstprinciples_optics_coupling.csv", "Phase 12 scalar coupling with first-principles optics Aeff"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/first_principles_channeling_optics/optics_response_firstprinciples_channeling_v1.yaml", "first-principles optics response card"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/first_principles_channeling_optics/first_principles_claim_boundary.md", "first-principles optics claim boundary"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/first_principles_channeling_optics/first_principles_sanity_checks.csv", "first-principles optics sanity checks"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/first_principles_channeling_optics/first_principles_vs_cam511_after_freeze.csv", "post-freeze first-principles vs CAM511 comparison"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/first_principles_channeling_optics/first_principles_onaxis_summary_L2_parratt.json", "L2 Parratt on-axis summary"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/first_principles_channeling_optics/first_principles_matrix_summary.csv", "coarse first-principles optics response matrix summary"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/first_principles_channeling_optics/optics_response_matrix_coarse_summary.json", "coarse first-principles optics response matrix machine summary"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/no_direct_scaling_optics_alignment/README.md", "no-direct-scaling optics alignment diagnostic entry"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/no_direct_scaling_optics_alignment/tables/spot_metric_definitions.csv", "spot metric definition separation table"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/no_direct_scaling_optics_alignment/tables/cam511_comparison_metric_map.csv", "CAM511 comparison metric map without direct scaling"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/no_direct_scaling_optics_alignment/tables/fov_footprint_summary.csv", "full-FoV footprint diagnostic summary"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/no_direct_scaling_optics_alignment/tables/ringwise_focus_diagnostics.csv", "ring-wise focus diagnostics"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/no_direct_scaling_optics_alignment/tables/aeff_transport_debug.csv", "Aeff transport decomposition diagnostics"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/no_direct_scaling_optics_alignment/validation_no_direct_scaling_alignment.csv", "no-direct-scaling alignment validation"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/no_direct_scaling_optics_alignment/figures/onaxis_core_vs_full_fov_footprint.png", "intrinsic core versus full-FoV footprint figure"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/no_direct_scaling_optics_alignment/figures/ringwise_centroid_map.png", "ring-wise centroid diagnostic figure"),
    ("12_FINAL_COMPACT_SOURCE_ANALYSIS/no_direct_scaling_optics_alignment/figures/aeff_by_ring_and_bounce.png", "Aeff by ring and bounce diagnostic figure"),
    ("05_SCRIPTS_AND_CONFIG/tools/make_nima_detailed_paper.py", "detailed manuscript generator"),
    ("05_SCRIPTS_AND_CONFIG/tools/build_nima_centered_phase07_12_ppt.py", "primary NIMA-centered Phase08-12 PPT generator"),
    ("05_SCRIPTS_AND_CONFIG/tools/build_phase07_12_progress_ppt.py", "Phase07-12 progress PPT generator"),
    ("05_SCRIPTS_AND_CONFIG/tools/run_design_optimization_addon.py", "add-on design optimization runner"),
    ("05_SCRIPTS_AND_CONFIG/tools/build_bilingual_nima_html.py", "bilingual HTML generator"),
    ("05_SCRIPTS_AND_CONFIG/tools/estimate_optics_focused_gamma_background.py", "focused gamma background estimator"),
    ("05_SCRIPTS_AND_CONFIG/tools/make_nima_issue_update_visuals.py", "NIMA update figure generator"),
    ("05_SCRIPTS_AND_CONFIG/tools/make_511_source_case_report.py", "A/B/C source-case report generator"),
    ("05_SCRIPTS_AND_CONFIG/tools/make_511_phase10_point_diffuse_report.py", "Phase 10 point/diffuse scaffold generator"),
    ("05_SCRIPTS_AND_CONFIG/tools/validate_phase10_point_diffuse.py", "Phase 10 dedicated validator"),
    ("05_SCRIPTS_AND_CONFIG/tools/update_source_case_ids_phase10.py", "Phase 10 source-case ID updater"),
    ("05_SCRIPTS_AND_CONFIG/tools/audit_selection_best_measured_energy.py", "Phase 10 measured-energy audit runner"),
    ("05_SCRIPTS_AND_CONFIG/tools/make_511_optics_requirements_matrix.py", "Phase 10 optics requirements writer"),
    ("05_SCRIPTS_AND_CONFIG/tools/make_phase11_metric_crosswalk.py", "Phase 11 metric crosswalk generator"),
    ("05_SCRIPTS_AND_CONFIG/tools/make_phase11_number_reconciliation.py", "Phase 11 number reconciliation writer"),
    ("05_SCRIPTS_AND_CONFIG/tools/make_phase11_selection_upgrade_decision.py", "Phase 11 selection upgrade writer"),
    ("05_SCRIPTS_AND_CONFIG/tools/init_phase11_optics_schema.py", "Phase 11 optics schema initializer"),
    ("05_SCRIPTS_AND_CONFIG/tools/make_phase11_optics_requirements.py", "Phase 11 optics requirements writer"),
    ("05_SCRIPTS_AND_CONFIG/tools/make_phase11_point_diffuse_template_ts.py", "Phase 11 template TS writer"),
    ("05_SCRIPTS_AND_CONFIG/tools/validate_phase11_metric_crosswalk.py", "Phase 11 metric crosswalk validator"),
    ("05_SCRIPTS_AND_CONFIG/tools/validate_phase11_selection_upgrade.py", "Phase 11 selection upgrade validator"),
    ("05_SCRIPTS_AND_CONFIG/tools/validate_phase11_optics_schema.py", "Phase 11 optics schema validator"),
    ("05_SCRIPTS_AND_CONFIG/tools/validate_phase11_claim_control.py", "Phase 11 claim-control validator"),
    ("05_SCRIPTS_AND_CONFIG/tools/make_phase12_final_closure.py", "Phase 12 final closure package generator"),
    ("05_SCRIPTS_AND_CONFIG/tools/validate_phase12_final_closure.py", "Phase 12 final closure validator"),
    ("05_SCRIPTS_AND_CONFIG/tools/build_parratt_reflectivity_table.py", "first-principles W/Si Parratt reflectivity table builder"),
    ("05_SCRIPTS_AND_CONFIG/tools/validate_firstprinciples_optics.py", "first-principles optics validator"),
    ("05_SCRIPTS_AND_CONFIG/tools/compare_firstprinciples_to_cam511_after_freeze.py", "first-principles post-freeze comparison writer"),
    ("05_SCRIPTS_AND_CONFIG/tools/build_firstprinciples_optics_matrix_coarse.py", "coarse first-principles optics response matrix builder"),
    ("05_SCRIPTS_AND_CONFIG/tools/couple_firstprinciples_optics_to_phase12.py", "first-principles optics Phase 12 coupling writer"),
    ("05_SCRIPTS_AND_CONFIG/tools/diagnose_spot_definition.py", "no-direct-scaling spot definition diagnostic"),
    ("05_SCRIPTS_AND_CONFIG/tools/diagnose_ringwise_focus.py", "no-direct-scaling ring-wise focus diagnostic"),
    ("05_SCRIPTS_AND_CONFIG/tools/debug_aeff_transport.py", "no-direct-scaling Aeff transport diagnostic"),
    ("05_SCRIPTS_AND_CONFIG/tools/validate_no_direct_scaling_alignment.py", "no-direct-scaling alignment validator"),
    ("05_SCRIPTS_AND_CONFIG/tools/build_astro_511_spectra.py", "A/B/C source spectra builder"),
    ("05_SCRIPTS_AND_CONFIG/tools/build_511_sky_models.py", "B diffuse sky model builder"),
    ("05_SCRIPTS_AND_CONFIG/tools/fold_511_source_cases.py", "A/B/C source-case folding runner"),
    ("05_SCRIPTS_AND_CONFIG/tools/build_cosima_sources_from_plane_cases.py", "A/C point-source Cosima source builder"),
]


def write_manifest() -> None:
    rows = []
    for rel, role in ARTIFACTS:
        path = R2 / rel
        rows.append(
            {
                "relative_path": f"reports2.0/{rel}",
                "exists": path.exists(),
                "bytes": path.stat().st_size if path.exists() else "",
                "role": role,
            }
        )
    out = MANUSCRIPT / "artifact_manifest.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["relative_path", "exists", "bytes", "role"])
        writer.writeheader()
        writer.writerows(rows)


def write_validation_log() -> int:
    VALIDATION.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["python3", "tools/validate_workspace.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    log = VALIDATION / "validation_log.txt"
    log.write_text(result.stdout + result.stderr, encoding="utf-8")
    print(result.stdout, end="")
    print(result.stderr, end="")
    return result.returncode


def main() -> int:
    code = write_validation_log()
    write_manifest()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
