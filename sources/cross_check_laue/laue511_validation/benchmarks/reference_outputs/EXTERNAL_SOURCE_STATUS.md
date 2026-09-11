# External Source Status

Checked on 2026-05-28.

## Laue Lens Library

- Project page: `https://larixfacility.unife.it/?page_id=309`
- Status: the project page is public and describes a Python Monte Carlo
  Laue-lens library.
- Download status: the page exposes a "Download Laue Lens Library" link. That
  link resolved to `https://larixfacility.unife.it/download-lll/`, which
  returned HTTP 404 from this environment during the check.
- Alternate status page: `https://mcs.unife.it/fermi/RP.html` is indexed and
  describes LLL, but command-line TLS verification failed here because the
  server presented a self-signed certificate.
- Local status: no LLL code or exported LLL curve is present in this workspace.
- Action needed: obtain the package or exported benchmark curve manually, then
  import it through `tools/import_external_lens_observables.py`.

## XOP / CRYSTAL

- Repository: `https://github.com/srio/CRYSTAL`
- Status: public Fortran source for the XOP crystal-diffraction code exists.
- Local status: a CRYSTAL `diff_pat` Ge(111) 511 keV mosaic Laue rocking curve
  is present in `benchmarks/xop_crystal/`.
- Provenance: CRYSTAL commit
  `9a255d904bc331ebc5deea02a95bedf1bb4e4324`, `diff_pat` v1.8,
  `xoppylib` 1.0.53, local DABAX 1.0.12.
- Import command used:

```bash
python3 tools/import_xop_crystal_diffpat.py --diffpat-dat path/to/diff_pat.dat --diffpat-par path/to/diff_pat.par
python3 tools/build_validation_summary.py
```

## xrt / pyTTE / CrystalPy

- xrt documents material tests comparing reflectivity/transmittivity with XOP
  and other programs.
- Local PyTTE and CrystalPy evidence has been generated/imported:
  - `benchmarks/xrt_pytte/`
  - `benchmarks/crystalpy/`
- These remain single-crystal/perfect-crystal checks, not replacement
  full-lens oracle curves.

## HEART

- Repository: `https://gitlab.com/heart-ray-tracing/HEART`
- Documentation: `https://heart-ray-tracing.gitlab.io/HEART/`
- Status: public Python Monte Carlo x-ray tracing package for mosaic crystal
  spectrometers, with active upstream changes.
- Local status: a patched HEART 2.1.3 full-lens branch/effective-area run has
  been generated and imported. The HEART-native detector image is retained as
  `heart_patched_full_lens.h5`; it closes effective area but gives a narrower
  HEART-native spot than the current opticsim detector-direction convention.
- Import status: `external_lens_observables/summary.json` is now imported with
  `ok=true` from `heart_patched_full_lens_guan_direction.h5`, which reuses the
  full 360-tile HEART detector weights and bins detector hits with the current
  Guan-style direction perturbation convention.
- Adapter request: `heart_lens_adapter_request.json` records the current HEART
  HEAD checked for handoff, expected units, detector-plane hit columns, and the
  local import command.
- Tile handoff: `external_lens_oracle_tiles.csv` now records all 360 current
  lens tiles with entry-face centers, expected diffracted directions, local
  radial/tangential axes, and the ideal Ge(111) diffracting-plane normal each
  external runner must reproduce for a comparable full-lens oracle.
- Feasibility audit: `reports/heart_adapter_feasibility/` checks HEART source
  commit `d54196aaa787eaefef6df7c66255803f50ea8517` and records that the
  current HEART flat-crystal interface does not provide a direct independent
  mapping for mechanical slab normal versus Ge(111) diffracting-plane normal.
- Handoff patch: `heart_independent_plane_normal.patch` adds an optional
  `diff_plane_N` flat-crystal argument to HEART so `axis_N` can remain the
  mechanical slab normal while `diff_plane_N` is used as the mean
  mosaic/diffracting-plane normal. Default HEART behavior is unchanged when the
  argument is omitted. The same patch also handles flat-crystal intersection
  intervals for rays parallel to a cuboid axis slab, which is needed by the
  current parallel on-axis source.
- Local smoke status: HEART 2.1.3 was installed in an isolated `/tmp` Python
  3.10 environment, imported successfully outside the sandbox where MPI socket
  initialization is permitted, and produced an HDF5 detector-image file from a
  small official-style flat-crystal run. The smoke output was not retained as
  validation evidence because it is not the current Laue lens.
- Full-lens imported evidence:
  - `heart_patched_full_lens_run_summary.json`: 360 tiles, 180000 photons,
    detector weight `45555`, effective area `0.583104 cm2` under the local
    importer.
  - `heart_patched_full_lens_guan_direction_run_summary.json`: same HEART
    detector weights, detector hit model
    `guan_direction_perturbation_from_heart_tile_summary`, source jitter
    `0.3 mm`, spot `d90` imported as `0.221923 cm`.

## Opticsim Table-Lens Closure

- Local status: `benchmarks/opticsim_table_lens/` imports the existing full
  five-ring opticsim comparison between the table-driven Barhoum-style baseline
  and the Guan/Reiazi-style online Darwin-Hamilton process.
- Result: `ok=true`, full-lens diffraction-fraction delta `0.00037`, max
  per-ring mean `p_diff` delta `0.000631`, and spot `d90` delta `-0.001167 cm`.
- Boundary: this is full-lens closure evidence inside the opticsim model
  family, not an external LLL/HEART oracle.

## Full-Lens Oracle Status

- A HEART-derived full-lens detector-image result has been imported at
  `external_lens_observables/summary.json` with `ok=true`.
- The expected external-observable CSV schema is documented in
  `EXTERNAL_LENS_OBSERVABLES_SCHEMA.md`; a current-reference schema example is
  present as `external_lens_observables_schema_example.csv`.
- `tools/import_heart_detector_image.py` created
  `external_lens_observables/summary.json`; the manifest now reports the
  external lens result as `imported`.
- The current lens input request for an external oracle is present as
  `external_lens_oracle_request.json`, with a ring table in
  `external_lens_oracle_rings.csv` and a per-tile orientation handoff table in
  `external_lens_oracle_tiles.csv`.
- A HEART/LLL result should not be counted as the current full-lens oracle
  unless its tile model maps the CSV `ideal_plane_normal_*` columns to the
  Ge(111) diffracting-plane normal, not merely to the mechanical slab normal.
- The current manifest status is
  `crosscheck_pass_external_lens_observables_imported`.
