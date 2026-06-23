# Review: Science and Instrument Requirements Section

Status: draft review for Section 2 resources; refreshed to match the current
paper-facing rate basis.
Date: 2026-06-14; refreshed 2026-06-17 and edited for manuscript-facing wording.

## Scope

This review covers the manuscript section `Science and instrument requirements` and the resources in this directory. It does not revalidate the full detector chain; it checks whether the section's requirement claims are traceable to current local source files and whether the resources introduce unsupported claims.

## Evidence Checked

- Current rate basis: the M=50000 full-statistics exact-position line-window
  chain.
- Exact-position convergence: the archived M/seed convergence summary for the exact-position delayed-source branch.
- Method skeleton: `paper_draft/methodology_skeleton_20260614.md`.
- Draft manuscript files:
  - `core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.tex`
  - `core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_zh.tex`

## Scientific Review

- The section is correctly framed as a pointed, narrow-line compact-source analysis, not an all-sky diffuse-imaging forecast.
- The four requirements are scientifically coherent:
  1. photon concentration for a small TES focal plane;
  2. a sub-keV 511 keV line window;
  3. detector-coupled prompt and activation background suppression;
  4. a mission-time rate fold with delayed-source convergence.
- The numerical values used in the traceability table match the current
  M=50000 exact-position rate basis:
  - `A_eff(511)=20.08476 cm2`;
  - line window `510.58-511.42 keV`;
  - selected `B/S=0.0392162/0.00118587 cps`;
  - mission-folded `Z20d=7.79950`, `F_3sigma(20d)=3.84640e-5 ph cm^-2 s^-1`.
- Remaining scientific risk: TES energy resolution, saturation, and pile-up are still assumptions or external-design inputs, not validated by this repository. The section should keep the wording as "requirement" or "analysis assumption" until measured or literature-anchored TES performance is added.

## Code and Resource Review

- No simulation code was changed for this section.
- The new resources are manuscript-facing summaries and include an explicit source policy in `README.md`.
- Editable vector figure sources should be converted to manuscript-facing PDF
  or PNG assets before inclusion in the current XeLaTeX build.
- The LaTeX tables are stored separately and should remain synchronized with the exact-position closure reports.

## Engineering Review

- The current selected-rate calculation still uses post-processing active-veto logic. This is acceptable for this paper section if stated explicitly, but it is not the same as native trigger/veto production filtering.
- Exact-position delayed-source convergence now supports using the M=50000
  exact-position chain as the line-window rate basis; a one-block-per-RPIP
  stress test remains an engineering upgrade, not a blocker for this
  requirement narrative.
- The final flight CAD, optics self-background, and full Revan/Mimrec reconstruction are outside this section's current evidence base and should remain in limitations/future work.
- PDF regeneration is verified for this draft state. The system TeX tree still
  does not have an installed `elsarticle.cls`, so the build uses a temporary
  Elsevier class tree under `/tmp/elsarticle_tmp/elsarticle` supplied through
  `TEXINPUTS`. Both English and Chinese drafts compiled successfully to PDF
  from the current `.tex` sources.
- Remaining render risk is layout polish, not a build blocker: the new requirements table has only a small overfull box warning, while larger overfull warnings remain in existing result tables outside this section.

## Verification Log

- `git diff --check` passed for the edited manuscript and `paper_resource` files.
- The English and Chinese drafts include the expected traceability-table inputs:
  - `\input{paper_resource/table_requirements_traceability_en.tex}`;
  - `\input{paper_resource/table_requirements_traceability_zh.tex}`.
- A structured JSON check against the current exact-position source files passed
  for the resource values used in the manuscript-facing tables.
- Full LaTeX compilation passed:
  - `latexmk -g -xelatex -interaction=nonstopmode -halt-on-error balloon511_nima_draft_en.tex`;
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error balloon511_nima_draft_zh.tex`.
- Current render outputs after cleanup: English draft PDF has 36 pages; Chinese draft PDF has 34 pages.
