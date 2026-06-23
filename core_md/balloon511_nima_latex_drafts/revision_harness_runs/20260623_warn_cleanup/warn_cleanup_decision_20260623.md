# WARN Cleanup Decision 20260623

Scope: paper-useful WARN cleanup after the immediate-fixes harness. This pass changed audit/provenance records only. It did not edit manuscript text, regenerate figures, redesign geometry, or overwrite simulation authority outputs.

## Resolved Or Clarified

- PI-03 source normalization:
  - Replaced residual machine-readable `TO_RECOVER` entries for `activation_delayed_fix5` and `upstream_ge_proxy_archived` with scoped provenance objects.
  - Clarified that activation delayed normalization is not an EXPACS/PARMA direct input; it is activation-inventory plus ground-state correction plus exact-position source sampling.
  - Replaced `megalib_cards.focused_signal_fix5 = TO_RECOVER` with Step05/Step08 focused-signal provenance.

- PI-04 reproducibility configuration:
  - Recovered ROOT version as `6.36.06` from the MEGAlib external ROOT tree.
  - Recovered radioactive-decay-related Geant4 data tree entries: `RadioactiveDecay4.3.2`, `G4ENSDFSTATE1.2.3`, and `PhotonEvaporation3.2`.
  - Replaced `custom_megalib_or_geant4_patches = UNKNOWN` with a scoped statement from the optics audit: no Geant4 toolkit bottom-code modification identified for Laue optics; custom Laue branch counters are application-level optics code.
  - Changed `production_cuts = TO_RECOVER` to an explicit limitation: numeric G4ProductionCuts values were not printed in the recovered fix5 run log. This avoids inventing a cut table.

- PI-05 figure provenance:
  - Recovered the EXPACS figure command: `python3 core_md/balloon511_nima_latex_drafts/paper_resource/build_expacs_flux_figure.py`.
  - Converted mass-model figure script gaps into explicit copy provenance from the geometry-closure render output.
  - Converted delayed-position/sampling figure script gaps into source-data-only provenance and explicitly marked them as diagnostics, not PI-02 convergence proof.

## Intentionally Retained

- `benchmark_alignment_old_new_geo_re = NOT_ALIGNED_REPORT_ONLY` remains unchanged. It is a method caveat for comparing to the old prompt chain, not a missing file to force into PASS.
- Figure visual QA WARNs remain because no figures were redrawn in this pass. They are review-driven presentation improvements, not blockers for the provenance records.
- Production-cut numeric values remain unrecovered because the recovered run log does not print explicit `G4ProductionCuts` values.

## Edited Audit Files

- `core_md/balloon511_nima_latex_drafts/source_normalization_audit_20260623.json`
- `core_md/balloon511_nima_latex_drafts/source_normalization_audit_20260623.md`
- `core_md/balloon511_nima_latex_drafts/simulation_config_authority_20260623.json`
- `core_md/balloon511_nima_latex_drafts/simulation_config_table_20260623.md`
- `core_md/balloon511_nima_latex_drafts/figures_audit_20260623.json`
- `core_md/balloon511_nima_latex_drafts/figures_audit_20260623.md`
