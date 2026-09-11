# M05NEW manuscript build validation

## Primary deliverables

- `balloon511_ea_m05new_en.tex`
- `balloon511_ea_m05new_en.pdf`
- `references.bib`
- Three publication figures in PDF, SVG, and 600 dpi PNG formats
- `scripts/build_publication_figures.py` and `figures/FIGURE_PROVENANCE.md`

## Build

From this directory:

```bash
latexmk -xelatex -interaction=nonstopmode -halt-on-error balloon511_ea_m05new_en.tex
```

The final build completed successfully with XeLaTeX, BibTeX, and xdvipdfmx.
The PDF is A4, 11 pages, unencrypted, and contains the three vector figures.
The final log contains no undefined citations, undefined references, errors,
or overfull boxes. Two non-blocking underfull-box notices remain in ordinary
prose and do not clip or overlap content.

The final automated artifact, citation, terminology, headline-value, and log
audit passed 32 of 32 checks.

## Manuscript checks

- Abstract: 240 words.
- Keywords: 6.
- Citations: 19 cited records and 19 matching bibliography entries.
- Citation style: author--year; reference list alphabetized by BibTeX.
- Headline comparison: 99.75% effective-area retention, 81.90% lower matched
  day-15 background, and a 2.43-fold improvement in the Gaussian 20-day
  3-sigma line-flux threshold.
- Fixed-source-state cut-flow rates are explicitly separated from mission-fold
  day-15 rates.
- Monte Carlo statistical uncertainties are distinguished from unmodeled
  detector, atmospheric, nuclear, structural, and pointing systematics.
- The 50 keV BGO criterion is identified as an idealized offline deposited-energy
  veto, distinct from the 80 keV native transport trigger.
- The different 20 ks and 200 ks anchor exposures are disclosed, while the
  matched physical nodes, response, selection, and mission definitions are
  retained.

## Constraint audit

- The paper's optimization narrative is the laterally relocated chimney TES
  focal plane with active BGO anticoincidence.
- The manuscript source contains no internal geometry labels, project paths,
  processing-stage names, hashes, or polyethylene/plastic optimization branch.
- The publication figures contain no internal geometry labels, paths, hashes,
  or polyethylene/plastic layers.
- The original M05 directory was read only; no write operation targeted it.
- No transport, activation, or detector-response simulation was run.
- No new hash or hash-verification step was added.

Author identities, affiliations, funding details, and individual author
contributions remain intentionally anonymized for the review copy and must be
restored by the submitting authors.
