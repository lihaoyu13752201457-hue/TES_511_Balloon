# M05NEW English manuscript package

This directory contains the new English LaTeX manuscript on background
suppression with a laterally relocated chimney TES focal plane and active BGO
anticoincidence. The original M05 manuscript remains separate and read only.

## Primary paper

- `balloon511_ea_m05new_en.tex`: complete anonymized review manuscript.
- `balloon511_ea_m05new_en.pdf`: compiled 11-page paper.
- `references.bib`: author--year bibliography used by the paper.
- `MANUSCRIPT_BUILD_VALIDATION.md`: build, content, and constraint checks.

Build from this directory with:

```bash
latexmk -xelatex -interaction=nonstopmode -halt-on-error balloon511_ea_m05new_en.tex
```

## Publication figures

- `figures/fig_geometry_causal_section.*`: TES displacement, BGO enclosure,
  and selected delayed-event origin comparison.
- `figures/fig_matched_cutflow_performance.*`: fixed-source-state background
  cut flow and matched performance ratios.
- `figures/fig_mission_significance_sensitivity.*`: 20-day significance and
  3-sigma line-flux thresholds.
- `scripts/build_publication_figures.py`: rebuilds the three figures from
  retained aggregate CSV and JSON products only.
- `figures/FIGURE_PROVENANCE.md`: figure inputs and numerical definitions.

Each publication figure is supplied as vector PDF, editable SVG, and 600 dpi
PNG. The older internal cross-section graphic is retained only as an audit
input and is not referenced by the paper.

## Headline comparison

- Final focused effective area: `15.08544 ± 0.04503 cm2`, retaining `99.75%`
  of the reference value.
- Matched day-15 background: `0.009280 s-1`, or `18.10%` of the reference.
- Twenty-day Gaussian 3-sigma line-flux threshold:
  `(2.229 ± 0.209) × 10^-5 ph cm^-2 s^-1`, a `2.43`-fold improvement.
- Selected delayed contribution from the central cryogenic stages:
  `32.18%` in the reference and `3.92%` in the chimney geometry.

All quoted uncertainties are Monte Carlo statistical uncertainties. Detector
calibration, atmospheric-source, nuclear-yield, structural, pointing, and
other mission systematics are outside the present scope.

## Supporting review files

- `M05_PAPER_DATA_TABLE.csv`: numerical manuscript data table.
- `REFERENCES.md`: local authority map for the supporting products.
- `M05NEW_VALIDATION.json` and `SG3B_OPTV3_COMPARISON.json`: retained numerical
  closure records.
- `NEW_PAPER_SESSION_HANDOFF_20260821.md`: governing session handoff.

The polyethylene/plastic review is retained only as an earlier boundary study;
it is not part of the paper's optimization proposal. No new transport,
activation, detector-response, or hash-verification run is required to build
the manuscript or its figures.
