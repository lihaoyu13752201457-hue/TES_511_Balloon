# Paper Resources for Science and Instrument Requirements

This directory holds manuscript resources for Section 2, "Science and instrument requirements".

Files:

- `table_requirements_traceability_en.tex`: English LaTeX table mapping science drivers to instrument/simulation requirements and local evidence.
- `table_requirements_traceability_zh.tex`: Chinese LaTeX table with the same content.
- `table_simulation_workflow_en.tex`: English LaTeX table describing the layered simulation workflow and interpretation boundaries.
- `table_simulation_workflow_zh.tex`: Chinese LaTeX table with the same workflow content.
- `fig_requirements_chain.svg`: editable line-art figure for the requirements chain.
- `fig_requirements_chain_caption.md`: caption text and source notes for the figure.
- `requirements_review.md`: review notes for the section, including scientific, code, and engineering confidence checks.
- `manuscript_review_20260615.md`: manuscript-wide fill-and-review log for the current LaTeX draft state.
- `manuscript_review_20260617.md`: reviewer-style refinement log covering the Claude R4 follow-up, public-paper anchors, workflow wording, Compton/FoV keep-policy, atmospheric-transmission boundary, and limitation wording.
- `reference_verification_20260617.md`: bibliography metadata and DOI verification pass for the current English/Chinese drafts.
- `claude_r4_recheck_20260617.md`: Codex recheck of Claude R4 against the current M=50000 paper-facing rate basis and regenerated lightweight checks.
- `build_delayed_distribution_invariance_smoke.py`: local PARMA trajectory-probe smoke test for the mission-time delayed-activation distribution-invariance approximation.
- `delayed_distribution_invariance_smoke_20260617.{json,md,csv}`: generated smoke-test summary and metrics; supports the scalar delayed-production fold only at the particle-family reweighting layer.

Source policy:

- These files are paper-facing summaries, not the primary numerical source.
- Primary numerical values remain in the validation and closure outputs under `outputs/reports/` and `stepwise_maintenance/`.
- If a value differs between this directory and the closure reports, the closure reports win and this directory must be updated.
- `opticsim_full` is the raw external B-FULL run environment referenced by
  the optics configuration JSON. Paper-facing optical source material is the repo copy in
  `stepwise_maintenance/step04_opticsim/` plus the focused-signal
  event-table bridge summaries.
