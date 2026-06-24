# Limited Manuscript Integration - 2026-06-24

Status: `READY_FOR_REVIEW_NOT_APPLIED`.

Scope: limited paper integration of the background-validation pass. This file
does not modify the manuscript source because HARNESS section 14.3 requires
`APPLY_MANUSCRIPT_CHANGES=true` before manuscript-derived files or source edits.

## Minimal Changes Proposed

1. Add one short Methods/source-model paragraph after the prompt source
   normalization equation. This paragraph documents that the prompt selected
   rate was independently reconstructed from far-field source definitions and
   detector-level event weights. It also records that the selected
   positron-primary prompt survivors in the 511 keV window were traced to
   annihilation-photon histories entering through the detector aperture.

2. Add one Discussion sentence group after the shield-material trade-study
   sentence. This records that a same-envelope BGO shield variant has been
   built and overlap-checked, while explicitly stating that no matched
   CsI/BGO transport, ratio, or material preference is claimed.

## Rationale

The manuscript already contains the delayed selected-rate convergence result in
the Results section and in Table 1. Repeating that material would add length
without changing the claim boundary. The useful new paper-facing content is
therefore limited to source-normalization provenance and the non-claim boundary
for CsI/BGO comparison.

## Claim Boundary

Allowed:
- prompt source normalization was independently reconstructed at selected-rate
  level;
- selected positron-primary prompt survivors were traced to physical
  annihilation-photon histories;
- delayed convergence is already reflected in the current manuscript;
- a material-only same-envelope BGO geometry exists and passed static geometry
  and overlap checks.

Not allowed:
- changing the headline selected background, signal, significance, or flux
  threshold values from this validation pass alone;
- claiming a BGO/CsI background ratio or shield-material preference;
- citing internal paths, run labels, random seeds, gate names, or debug status
  terms in the paper text.

## Patch Artifact

The concrete proposed diff is stored in:

`engineering/background_validation_20260624/07_manuscript_support/limited_manuscript_integration_20260624.patch`

