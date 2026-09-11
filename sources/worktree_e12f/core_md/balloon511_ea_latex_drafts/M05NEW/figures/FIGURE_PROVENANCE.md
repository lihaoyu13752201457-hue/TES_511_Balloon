# Publication figure provenance

All three figures are derived products. The build reads retained CSV and JSON
files only. It does not open an NPZ or SIM payload, run detector response, start
transport, or calculate file hashes.

## `fig_geometry_causal_section`

- Component coordinates: `engineering/geometry_optimization_20260815/66_m05new_mxc_bpe_veto_review_20260821/data/cross_section_geometry_contract.csv`.
- Exact cold-stage fractions: `engineering/geometry_optimization_20260815/66_m05new_mxc_bpe_veto_review_20260821/data/cold_stage_origin_share.csv`.
- Retained BGO and chimney dimensions: `engineering/geometry_optimization_20260815/66_m05new_mxc_bpe_veto_review_20260821/outputs/assessment.json`.
- Reference selected delayed-source positions and day-15 weights: `engineering/geometry_optimization_20260815/59_sg3b_prompt_activation_coupling_20260818/outputs/02_coupling_analysis/selected_event_lineage.csv`.
- Optimized selected delayed-source positions and day-15 weights: `engineering/geometry_optimization_20260815/63_m05new_sg3b_signal_statistics_20260820/outputs/05_optv3_delayed_origins/optv3_delayed_selected_events.csv`.
- Paper values: 32.1833027% and 3.9223084%, printed as 32.18% and 3.92%.

The publication rendering intentionally excludes the historical polyethylene
and plastic layers. It shows only the cryogenic stages, TES, active BGO,
chimney wall, focused path, and selected delayed-source locations needed for
the causal comparison.

## `fig_matched_cutflow_performance`

- Reference background cut-flow: sums of `weighted_rate_cps` in `engineering/geometry_optimization_20260815/63_m05new_sg3b_signal_statistics_20260820/outputs/03_expanded_catalog/expanded_direct_cutflow.csv` for the science window and the three displayed stages.
- Optimized background cut-flow: `DEEPSEEK_CODE/outputs/04_event_catalog_step05_m05_fixed_20260820/direct_cutflow_totals.csv`.
- Effective-area, mature-background, and Gaussian threshold ratios: `core_md/balloon511_ea_latex_drafts/M05NEW/SG3B_OPTV3_COMPARISON.json`.

The displayed direct background rates are 5.959678565, 0.06318020323, and
0.05429822930 s^-1 for the reference geometry and 2.362629842, 0.009813272054,
and 0.009418680739 s^-1 for the optimized geometry. The middle point is the
active-BGO stage itself, not a combined-veto stage.

## `fig_mission_significance_sensitivity`

- Reference 81-node mission curve: `engineering/geometry_optimization_20260815/63_m05new_sg3b_signal_statistics_20260820/outputs/04_candidate_timeline/mission_mature_flux_threshold.csv`.
- Optimized 81-node mission curve: `DEEPSEEK_CODE/outputs/05_mature_timeline_m05_fixed_20260820/mission_timeline_81nodes.csv`.
- Endpoint statistical errors: `core_md/balloon511_ea_latex_drafts/M05NEW/M05NEW_VALIDATION.json`.

Gaussian significance is calculated from the tabulated cumulative signal
kernel and cumulative background as `F0 * K / sqrt(B)` with `F0 = 1e-4 ph
cm^-2 s^-1`. Asimov significance uses the standard single-bin counting
expression. Gaussian and Asimov flux-threshold curves are read directly from
the two mission CSV files.

## Rebuild

From the repository root:

```bash
python3 core_md/balloon511_ea_latex_drafts/M05NEW/scripts/build_publication_figures.py
```

Each figure is exported as PDF and SVG vector art and as a 600 dpi PNG.
