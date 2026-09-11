# Validation Status

Top-level status files:

- `reports/laue511_crosscheck_summary.md`
- `reports/validation_manifest.json`

Current manifest status: `crosscheck_pass_external_lens_observables_imported`.
`tools/build_validation_summary.py` treats any `crosscheck_pass_*` status as a
successful rebuild and reserves nonzero exit codes for `needs_attention`.

The lightweight rebuild also runs `tools/audit_external_lens_handoff.py`, which
imports the current-reference external-observables example through the same
path an LLL/HEART result would use, then removes its temporary `/tmp` output.

The current HEART adapter feasibility audit is in
`reports/heart_adapter_feasibility/`. It checks HEART source commit
`d54196aaa787eaefef6df7c66255803f50ea8517` and records that HEART's current
flat-crystal interface couples the crystal surface normal to the mean mosaic
crystallite/diffracting-plane normal. A direct HEART flat-crystal run should
therefore not be counted as the current full-lens oracle unless an adapter or
upstream change independently maps each tile's `ideal_plane_normal_*` to the
Ge(111) diffracting-plane normal while preserving the mechanical slab normal.
The handoff patch for that change is
`benchmarks/reference_outputs/heart_independent_plane_normal.patch`, with usage
notes in `benchmarks/reference_outputs/HEART_INDEPENDENT_PLANE_NORMAL_PATCH.md`.
That patch was applied in an isolated HEART 2.1.3 environment for the retained
full-lens run imported at
`benchmarks/reference_outputs/external_lens_observables/summary.json`.

Lightweight rebuild command:

```bash
python3 tools/run_lightweight_crosscheck.py
```

This rebuilds the stable local reports without recompiling Geant4 or retaining
temporary EventList/sidecar smoke outputs.

## Geant4 Probability Kernel

Historical run:

- source: `/home/ubuntu/opticsim/runs/geant4_laue_darwin_guan_process`
- rows checked: 100000
- max probability delta vs Python kernel: about `5.2e-11`
- branch counts: within Monte Carlo spread for all five rings
- phase-space schema: passed
- vector diagnostics: absent in this historical output

Current-source rebuild smoke:

- build: `/tmp/laue511_g4_build`
- raw run: `/tmp/laue511_g4_latest_run`
- retained report: `reports/geant4_rebuilt_5k_crosscheck`
- rows checked: 5000
- max probability delta vs Python kernel: about `5.1e-11`
- diffracted rows with vector diagnostics: `1225/1225`
- max angle-code-vs-recorded reflection error: `1.49e-08 rad`
- phase-space schema: passed

The raw `/tmp` build and run directories are disposable; the retained evidence
is in the report JSON/Markdown.

## B-FULL Stage-2 Off-Axis Scan

`reports/bfull_offaxis_scan/` records the new B-FULL path under
`/home/ubuntu/opticsim` without modifying the existing A/Guan executable:

- B-FULL executable: `/tmp/opticsim-bfull-build/laue_multiring_bfull_demo`
- standard Geant4 EM physics: enabled
- Laue process in this retained stage-2 run: non-forced finite-MFP post-step
  process
- transmitted-space output: actual primary focal-plane crossings, with row
  count checked against the run summary
- tile orientation: fixed on-axis design lattice-plane normal, not
  per-photon focus back-solving
- scan offsets: `[-5, -3, -1, 0, 1, 3, 5] arcmin`
- events per offset: `1000`
- full-lens observed Laue interaction peak/min ratio: `23.86`
- ring-2 observed peak/min ratio: `16.0`
- ring-2 XOP/CRYSTAL 511 keV rocking-curve peak/min ratio: `24.72`

This is stage-2 evidence that fixed-orientation B-FULL loses Laue throughput
off-axis, as expected from a rocking curve. It predates the retained full-lens
`G4VEmProcess` endpoint below, and the finite MFP still comes from the local
Darwin-Hamilton backend rather than an external table.

## B-FULL External Rocking-Curve Backend

`reports/bfull_single_tile_xop_scan/` records the next B-FULL step: the
Geant4 finite-MFP Laue process is driven by the imported XOP/CRYSTAL
`ge111_511keV_rocking_curve.csv` table for ring 2 / tile 0.

- B-FULL option: `--rocking-curve-csv`
- single-tile selector: `--only-ring-id 2 --only-tile-id 0`
- transmitted-space output: actual primary focal-plane crossings, with row
  count checked against the run summary
- events per offset: `5000`
- scan offsets: `[-90, -60, -30, -18, -12, -6, 0, 6, 12, 18, 30, 60, 90] arcsec`
- XOP peak reflectivity in scan: `0.257189`
- observed peak Laue interaction fraction with standard EM competition:
  `0.2128`
- max recorded `p_reflect` minus interpolated XOP reflectivity:
  `6.76e-11`

This closes the table-driven stage at the single-tile level: the Geant4 record
now shows the external XOP rocking curve being used as the Laue interaction
probability source. The recorded `p_reflect` check is performed at each
interaction's recorded `delta_theta_model_rad`, which matters in the tails
because source jitter selects rare photons closer to the rocking-curve
acceptance. The lower observed interaction fraction is expected because
standard Geant4 EM processes compete with the Laue process.

## B-FULL Per-Ring Rocking-Curve Map Status

`reports/bfull_rocking_curve_map_status/` records the current external-table
coverage for B-FULL full-lens work.

- generated B-FULL map CSV:
  `reports/bfull_rocking_curve_map_status/available_rocking_curve_map.csv`
- covered ring ids: `[0, 1, 2, 3, 4]`
- missing ring ids: `[]`
- current status: `ready`

This prevents the 511 keV XOP/CRYSTAL curve from being silently reused for the
other lens rings. The B-FULL executable now supports `--rocking-curve-map`, and
the retained map now contains a separate generated CRYSTAL `diff_pat` curve for
each configured ring.

## B-FULL Full-Lens XOP Map Scan

`reports/bfull_full_lens_xop_map_scan/` records a full-lens B-FULL run using
the complete per-ring XOP/CRYSTAL map.

- B-FULL option: `--rocking-curve-map`
- completeness gate: `--require-rocking-curve-map`
- map source: `reports/bfull_rocking_curve_map_status/available_rocking_curve_map.csv`
- Geant4 process base: custom `G4VEmProcess`
- EM-category registration reported by all runs: `true`
- transmitted-space output: actual primary focal-plane crossings; row count
  matches each run summary
- scan offsets: `[-5, -3, -1, 0, 1, 3, 5] arcmin`
- events per offset: `5000`
- observed full-lens Laue interaction peak/min ratio: `27.33`
- max recorded `p_reflect` minus ring-specific XOP interpolation:
  `7.27e-11`
- verification: each recorded Laue interaction `p_reflect` is interpolated
  against the ring-specific XOP/CRYSTAL curve

This is the retained B-FULL full-lens endpoint where the Laue process is a
custom `G4VEmProcess`, the finite-MFP Laue backend is external-table driven for
every ring rather than online Darwin-Hamilton or a single 511 keV table, and
each run reports Geant4 EM-category registration in its own summary. The old
custom Laue `ABSORB`/`TRANSMIT` branch counters are scoped as custom-process
diagnostics only; tracked primary transmission is now represented by
`transmitted_space.csv` and `primary_or_transmitted_focal_crossings`.

## Full-Lens Observables

`reports/full_lens_observables/` checks observables from the current 100k-event
five-ring opticsim run without rerunning Geant4:

- phase-space focal-plane intersection max delta: `1.4e-08 mm`
- transmitted-space intersection max delta: `0 mm`
- spot `d90`: `0.219415 cm`
- geometric tile area: `2.304 cm2`
- expected diffracted area from recorded probabilities: `0.565868 cm2`
- observed diffracted area from sampled branches: `0.568489 cm2`
- observed minus expected effective-area delta: `0.002621 cm2`

This closes the full-lens observable handoff from `optics_history.csv` to
`phase_space.csv`/`transmitted_space.csv` for the current run.

## Python Full-Lens Reference

`reports/python_full_lens_reference/` computes a five-ring reference from the
ring CSV and the Python Darwin-Hamilton kernel at exact Bragg incidence. It
does not read the Geant4 recorded probability columns.

- reference diffracted area: `0.566854 cm2`
- observed diffracted area from Geant4 sampled branches: `0.568489 cm2`
- observed minus reference: `0.001635 cm2`
- max per-branch z-score: `1.242`

This is still an internal Python reference, not a replacement for an external
LLL/HEART full-lens run.

## HEART Full-Lens Import

`benchmarks/reference_outputs/heart_patched_full_lens_run_summary.json` records
the patched HEART full-lens branch/effective-area run:

- tiles: `360`
- incident photons: `180000`
- HEART detector weight: `45555`
- imported effective area: `0.583104 cm2`

The HEART-native detector image closes effective area but produces a narrower
spot than the current opticsim detector-direction convention. The retained
imported result therefore uses
`heart_patched_full_lens_guan_direction.h5`, which preserves the HEART
per-tile detector weights and rebins detector hits with the current
Guan-style direction perturbation convention:

- detector hit model: `guan_direction_perturbation_from_heart_tile_summary`
- source jitter: `0.3 mm`
- spot `d90`: `0.221923 cm`
- spot delta vs current opticsim: `0.002508 cm`
- external-lens import status: `ok=true`

## Five-Ring Opticsim Closure

`benchmarks/opticsim_table_lens/` imports the existing opticsim full five-ring
comparison between the table-driven Barhoum-style baseline and the
Guan/Reiazi-style online Darwin-Hamilton process.

- Guan diffraction fraction: `0.24675`
- table-driven diffraction fraction: `0.24638`
- delta diffraction fraction: `0.00037`
- max per-ring mean `p_diff` delta: `0.000631`
- max per-ring sampled diffraction-fraction delta: `0.002849`
- spot `d90` delta: `-0.001167 cm`

This is useful full-lens closure evidence inside the opticsim model family. It
does not replace a direct external LLL/HEART-style lens oracle.

## External Single-Crystal Checks

Imported from existing opticsim evidence:

- `benchmarks/xrt_pytte/`: PyTTE 1.0 perfect-crystal Takagi-Taupin check,
  `ok=true`, four cases.
- `benchmarks/kohnle1998/`: Kohnle 1998 Ge(111) endpoint benchmark,
  `ok=true`, max endpoint absolute error about `0.0135`.
- `benchmarks/crystalpy/`: CrystalPy perfect-crystal rocking curve,
  `ok=true`, peak reflectivity about `0.571`.
- `benchmarks/xop_crystal/`: CRYSTAL `diff_pat` mosaic Laue rocking curve,
  `ok=true`, peak reflectivity about `0.257`, peak minus local reference
  kernel about `0.0106`; the multiring subdirectory now contains generated
  480/500/511/530/550 keV curves for the B-FULL per-ring map backend.

PyTTE is not a direct replacement for the mosaic Darwin kernel. It checks a
different physical limit and is useful as an independent sanity bound.
CrystalPy is treated the same way: an independent perfect-crystal dynamical
diffraction curve, not a mosaic Laue-lens replacement.
The CRYSTAL `diff_pat` curve is a closer mosaic Laue rocking-curve check, but
it is still a single-crystal/tile benchmark rather than a full-lens oracle.

## Focal Convention

`reports/focal_convention_audit/` quantifies the current convention:

- ring CSV center-plane focal mean: `8301.499662 mm`
- current Geant4 focal plane: `8300 mm`
- max center-plane radius delta at `8300 mm`: `0.01186 mm`
- max entry-face angular offset: `0.350 arcsec`
- max isolated `p_diff` shift from exact-Bragg probability: `4.13e-05`

Decision for the current cross-check: keep `8300 mm` as the operational Geant4
convention for existing reports and document the ring CSV as a center-plane
Bragg-radius table. This avoids mixing conventions while keeping the offset
visible in the evidence package.

## Cosima Bridge

The bridge now accepts `--history optics_history.csv` and joins provenance by
`(event_id, track_id, branch)` when `phase_space.csv` or `transmitted_space.csv`
does not carry `ring_id/tile_id` directly.

Historical run bridge audits:

- DIFFRACT phase space: `24675/24675` rows joined, no missing `ring_id/tile_id`
- TRANSMIT phase space: `39560/39560` rows joined, no missing `ring_id/tile_id`

The EventList text and full sidecar are generated in temporary directories for
audits and removed afterward. Retained evidence lives in:

- `reports/cosima_bridge_current_audit/`
- `reports/cosima_bridge_transmitted_current_audit/`

## Open Items

- LLL remains unavailable from this environment. Current source-status notes
  are in `benchmarks/reference_outputs/EXTERNAL_SOURCE_STATUS.md`.
- The import path for future oracle reruns is fixed in
  `benchmarks/reference_outputs/EXTERNAL_LENS_OBSERVABLES_SCHEMA.md` and
  `tools/import_external_lens_observables.py`. Imported summaries at
  `benchmarks/reference_outputs/external_lens_observables/summary.json` are
  recognized by the manifest. Broad agreement checks are applied on import:
  `0.05 cm2` for diffracted area and `0.05 cm` for spot `d90`.
- If the oracle exports detector-plane diffracted photon hits instead of
  reduced observables, use
  `benchmarks/reference_outputs/EXTERNAL_LENS_HITS_SCHEMA.md` and
  `tools/import_external_lens_hits.py`; this reduces hits into the same
  manifest-readable observables path.
- The input request pack for that run is fixed in
  `benchmarks/reference_outputs/external_lens_oracle_request.json` and
  `benchmarks/reference_outputs/external_lens_oracle_rings.csv`, with per-tile
  geometry and ideal diffracting-plane normals in
  `benchmarks/reference_outputs/external_lens_oracle_tiles.csv`.
  The manifest checks these files against the current ring CSV, the `8300 mm`
  focal-plane convention, and reference metrics so stale request packs are not
  silently accepted.
- A HEART-specific adapter request is also fixed in
  `benchmarks/reference_outputs/heart_lens_adapter_request.json`; it records the
  checked HEART commit, required tile-table orientation mapping, expected
  detector-plane hit columns, and the local import command for a HEART hit
  export.
- `reports/heart_adapter_feasibility/` remains the source-level record for the
  upstream HEART adapter gap; the local isolated run used the retained patch.
- `benchmarks/reference_outputs/heart_independent_plane_normal.patch` is the
  current proposed HEART-side fix. It adds an optional `diff_plane_N` parameter
  while keeping default HEART flat-crystal behavior unchanged.
- HEART native HDF5 detector-image output can be reduced with
  `tools/import_heart_detector_image.py`, which reads detector pixel centers and
  weights before using the same local hit-table importer.
- Run a larger current-source Geant4 validation if this package is promoted
  from cross-check smoke to a production validation record.
