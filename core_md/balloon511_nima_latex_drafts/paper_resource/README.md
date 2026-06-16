# Paper Resources for Science and Instrument Requirements

This directory holds manuscript resources for Section 2, "Science and instrument requirements".

Files:

- `table_requirements_traceability_en.tex`: English LaTeX table mapping science drivers to instrument/simulation requirements and local evidence.
- `table_requirements_traceability_zh.tex`: Chinese LaTeX table with the same content.
- `table_simulation_workflow_en.tex`: English LaTeX table describing the stepwise simulation workflow and authority boundaries.
- `table_simulation_workflow_zh.tex`: Chinese LaTeX table with the same workflow content.
- `fig_requirements_chain.svg`: editable line-art figure for the requirements chain.
- `fig_requirements_chain_caption.md`: caption text and source notes for the figure.
- `requirements_review.md`: review notes for the section, including scientific, code, and engineering confidence checks.
- `manuscript_review_20260615.md`: manuscript-wide fill-and-review log for the current LaTeX draft state.

Authority policy:

- These files are paper-facing summaries, not primary numerical authority.
- Numerical authority remains in the validation and closure outputs under `outputs/reports/` and `stepwise_maintenance/`.
- If a value differs between this directory and the closure reports, the closure reports win and this directory must be updated.
- `opticsim_full` is the raw external B-FULL run environment referenced by
  the Step04 authority JSON. Paper-facing optical authority is the repo copy in
  `stepwise_maintenance/step04_opticsim/` plus the Step09 focused-signal
  event-table bridge summaries.
