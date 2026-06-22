# Legacy Validator Output Placeholder

This legacy DEMO2 validator output directory is intentionally not the current
authority for this checkout. The broad `validate_new_geo_re.py` checks target
the old DEMO2/mainline path set and are superseded for the 2026-06-12 R2
closure by:

```bash
python3 code/tools/validate_v3p5_fullstat_r2.py
```

The current R2 validator covers the v3p5 full-stat Step05 prompt-normalization
audit, Step05/06/08/1 Ms headline values, compare-report relabeling,
decay-source audits, and v3p5 `spot_r90` spatial sidecar invariants.
