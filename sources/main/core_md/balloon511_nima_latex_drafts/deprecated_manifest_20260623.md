# Deprecated Manifest 20260623

Created UTC: 2026-06-23T08:38:09+00:00

This file marks known stale or non-authoritative material encountered by the immediate-fixes harness. It does not delete, overwrite, or rewrite any of these sources.

| Path | Deprecation tag | Evidence | Replacement / rule |
|---|---|---|---|
| `old/stepwise_maintenance/step11_upstream_optics_background/outputs_ge_proxy_delayed_response/step11_ge_proxy_delayed_detector_response_summary.json` | archived-with-stale-derived-rate | `/zero_count_upper_limits/W2/final_rate_s-1 = 0.00012534045848433615`; `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/phase1_project_audit.md` lines 77-111 identify the physical normalization issue. | Keep `total_activity_Bq`, `generated_events_seen`, and zero selected events as archived evidence; use corrected upper rate `6.38e-5 cps`. |
| `old/stepwise_maintenance/step11_upstream_optics_background/status.json` | archived-with-stale-derived-rate | `/detector_response/zero_count_95_rate_s-1 = 0.00012534045848433615`; underlying activity and generated-decay fields remain useful. | Use `paper_evidence_manifest_20260623.json` entries `upstream_ge_proxy_*`. |
| `core_md/balloon511_nima_latex_drafts/paper_resource/table_simulation_workflow_en.tex` | stale-risk/supporting-only | `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/phase1_project_audit.md` lines 233-237 flag seed/upper-limit inconsistency; `paper_resource/README.md` lines 21-29 says closure reports win over paper_resource tables. | Do not use as numeric authority until regenerated against current manifests. |
| `core_md/balloon511_nima_latex_drafts/paper_resource/table_simulation_workflow_zh.tex` | stale-risk/supporting-only | Same table family as the English workflow table; not independently promoted by the closure reports. | Treat as supporting draft material only pending table regeneration. |
| `core_md/balloon511_nima_latex_drafts/paper_resource/*` numeric snippets | supporting-only | `paper_resource/README.md` lines 21-29 assigns priority to closure reports and manuscript source. | Use `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/` and Step05--Step08 outputs as authority. |
| deleted/replaced figure files `fig_delayed_exactpos_rpip_distribution.png` and `fig_exactpos_sampling_necessity.png` | replaced | Current manuscript includes `fig_delayed_position_rpip_distribution.png` and `fig_position_sampling_necessity.png` instead. | Audit current files in `figures_audit_20260623.*`. |

## Rule

A value in this manifest is not valid manuscript evidence unless it is also listed as current or archived evidence in `paper_evidence_manifest_20260623.json` with a nonempty source path and locator.
