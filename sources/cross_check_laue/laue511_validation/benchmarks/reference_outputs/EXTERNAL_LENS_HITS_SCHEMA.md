# External Lens Hit Table Schema

Use this schema when an external Laue-lens oracle exports detector-plane
diffracted hits instead of already-reduced observables.

Default required CSV columns:

```text
x_cm,y_cm
```

Optional columns:

```text
weight,event_id,ring_id,tile_id,energy_keV
```

The hit table should contain diffracted photons at the focal detector plane
only. Coordinates are relative to the optical axis. If the external file uses
millimetres or different column names, pass `--position-unit`, `--x-column`,
and `--y-column`.

Import command:

```bash
python3 tools/import_external_lens_hits.py \
  --input path/to/external_lens_hits.csv \
  --incident-weight <total incident ray weight>
python3 tools/build_validation_summary.py
```

By default the importer uses the current opticsim geometric area from
`reports/full_lens_observables/metrics.json`. Override it with
`--geometric-area-cm2` if the external oracle used a different illuminated
geometric area.

Computed observables:

```text
diffracted_area_cm2 = geometric_area_cm2 * sum(hit weights) / incident_weight
spot_d90_cm = weighted 90% containment diameter in the detector plane
```

The tool writes both the copied hit table and the reduced
`external_lens_observables.csv` into
`benchmarks/reference_outputs/external_lens_observables/`; the manifest then
uses the same imported-summary path as the aggregate-observables importer.

For native HEART HDF5 output, use:

```bash
python3 tools/import_heart_detector_image.py --input path/to/heart_output.h5
```

That importer reads `Results/detector_image` plus `Detector/detector_L_pos` and
`Detector/detector_W_pos`, then creates a weighted hit table from nonzero pixel
centers before applying the same reduction.
