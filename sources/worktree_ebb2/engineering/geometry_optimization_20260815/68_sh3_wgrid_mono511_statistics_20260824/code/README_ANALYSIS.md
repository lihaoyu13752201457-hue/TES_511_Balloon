# SH3+W-grid PARMA mono-511 analysis handoff

`analyze_wgrid_mono511.py` imports and invokes the hash-frozen package-67
`analyze_mono_line.py` with model-B physics.  It requires the new campaign to
match the open SH3 authority at 15,709,417 incident photons, 8343.62808 s, and
one common event weight.  It also verifies that the new transport seeds do not
overlap the 70 open-SH3 seeds before using independent-error propagation.

Formal invocation:

```bash
python3 analyze_wgrid_mono511.py \
  --line-root /absolute/local/path/to/completed/wgrid/transport \
  --expected-geometry-setup /absolute/path/to/WGrid_60cm.geo.setup \
  --output /absolute/local/path/to/new/nonexistent/analysis_output
```

The output directory is never written directly.  A unique sibling staging
directory receives the response, frozen authorities, comparison tables, and
receipts; `os.rename` then promotes the complete directory atomically.  Existing
destinations are rejected.  Failed staging is retained under a unique
`.failed-*` name.

Main artifacts:

- `comparison_cutflow_10rows.csv`: both windows × five response stages.
- `comparison_summary.json`: final-window pre-veto/final differences, ratios,
  independent uncertainties, and up/down summaries.
- `comparison_final_by_source_bin80.csv`: all 80 equal-mu PARMA components.
- `comparison_up_down.csv`: bins 0–39 (`down`) and 40–79 (`up`).
- `incremental_statistics_decision.json`: line-rate and new/open-ratio ESS
  gates at configurable relative-MC targets (10% by default).  It never starts
  a top-up automatically.
- `PROVENANCE.json`, `ARTIFACT_MANIFEST.json`, and frozen small authorities.

Run the black-box static-input self-test with:

```bash
python3 test_analyze_wgrid_mono511.py
```
