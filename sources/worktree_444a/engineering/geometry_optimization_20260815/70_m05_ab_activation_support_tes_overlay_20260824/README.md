# M05 A/B activation-support and TES-impact overlay

This package makes two Chinese review figures using only compact retained
sources and native WRL geometry meshes.  It does not read a SIM file and does
not run transport.

Each figure separates two populations:

1. the complete stride-retained delayed-source catalogue actually used by the
   transport source cards: 8 incident families times 10,000 source blocks;
2. mother-nuclide sites of delayed events that survive the current final-W2
   response selection and therefore contribute background to TES.

The first population is not the lossless set of every raw RP production record
inside the large BUILDUP SIM.  It is the deterministic, day-15-activity-weighted
exact-position source catalogue derived from those records.  Coincident source
blocks are aggregated for plotting while preserving multiplicity and activity.

Run from the repository root:

```bash
MPLCONFIGDIR=/tmp/mpl-m05-activation-support \
python3 engineering/geometry_optimization_20260815/70_m05_ab_activation_support_tes_overlay_20260824/code/build_activation_support_tes_overlay.py
```

Outputs are written as PNG, SVG and PDF together with
`outputs/figure_summary.json`.  The summary records the source-block, unique
site, nuclide, geometry and final-W2 rate closures.  No hashes or binary
manifests are produced.
