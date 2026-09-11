# External Lens Observables Schema

Use this schema when importing a full-lens result from LLL, HEART, or another
external Laue-lens oracle. A current-reference CSV example is stored next to
this file as `external_lens_observables_schema_example.csv`; it is useful for
checking format and thresholds, but it is not external-oracle evidence.

Required CSV columns:

```text
scope,metric,value,unit,source_tool,source_version
```

Required rows:

```text
lens,diffracted_area_cm2,<value>,cm2,<tool>,<version>
lens,spot_d90_cm,<value>,cm,<tool>,<version>
```

Optional rows may add `diffraction_fraction`, `geometric_area_cm2`, `n_rays`,
or per-ring metrics using scopes such as `ring:0`, `ring:1`, and so on.

Import command:

```bash
python3 tools/import_external_lens_observables.py --input path/to/external_lens_observables.csv
python3 tools/build_validation_summary.py
```

If an external tool exports detector-plane photon hits instead of these reduced
rows, use `EXTERNAL_LENS_HITS_SCHEMA.md` and
`tools/import_external_lens_hits.py`; that path reduces the hit table into this
same observables schema.

The default import location is
`benchmarks/reference_outputs/external_lens_observables/summary.json`; the
top-level manifest reads that summary automatically when it exists.

The importer records deltas against the current opticsim sampled observables
and the Python-only full-lens reference. It uses deliberately broad agreement
checks: `0.05 cm2` for diffracted area and `0.05 cm` for spot `d90`.
Failures are reported as `needs_attention`, because external runs may use
different source, packing, or detector-plane conventions.
