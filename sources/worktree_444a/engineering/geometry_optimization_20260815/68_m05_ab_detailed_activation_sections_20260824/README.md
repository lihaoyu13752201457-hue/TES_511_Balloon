# M05 detailed Model-A/Model-B activation sections

This package builds two paper-review figures without running transport or a
detector simulation.

- The geometry layer is the exact intersection of each retained native Geant4
  WRL mesh with the InstrumentFrame plane `y'=0`.
- The source layer contains the three-dimensional mother-nuclide positions of
  delayed events that survive the final W2 selection, projected onto `x'-z'`.
- Filled markers have `|y'| <= 1 cm`; hollow markers are farther from the
  section plane.  Neither marker style asserts that the source lies on the
  section itself.
- Marker areas use one shared absolute mapping for Models A and B.
- Model B reference-event weights are rescaled by incident family to the
  current same-state day-15 cutflow.  This changes the displayed total from
  `0.003624666351900698` to `0.0035805378117859145 cps`; positions are
  unchanged.  Model A already closes directly at
  `0.037720860604326306 cps`.

Run from the repository root:

```bash
MPLCONFIGDIR=/tmp/mpl-m05-ab-sections \
python3 engineering/geometry_optimization_20260815/68_m05_ab_detailed_activation_sections_20260824/code/build_ab_detailed_activation_sections.py
```

The script writes PNG, SVG and PDF versions of both figures plus
`outputs/figure_summary.json`.  The summary records geometry counts, section
segment counts, event/rate closure, Model-B family factors and the plotted
top-group definitions.  No hashes, binary manifest or simulation products are
created.
