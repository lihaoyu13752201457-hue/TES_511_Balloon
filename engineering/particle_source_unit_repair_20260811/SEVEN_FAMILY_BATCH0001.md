# Corrected-keV seven-family batch0001

Status: `PASS__BATCH0001_MERGE_ELIGIBLE`

This is the first production-contributing batch after the mergeable all-eight
SMOKE.  It runs the canonical corrected-keV continuum through
`Mass_model_511` and `S3d-O8`, in separate `instant` and `buildup` campaigns,
while deliberately excluding protons.

## Fixed scope

- included: `gamma`, `n`, `eminus`, `eplus`, `alpha`, `muminus`, `muplus`;
- excluded: `p`;
- gamma: 100,000 events split into four independent jobs;
- each non-gamma family: one flux-scaled job;
- 10 jobs and 116,673 primaries per geometry/mode;
- 40 jobs and 466,692 primaries over the four campaigns;
- full original 20 angular bins, Flux values, corrected spectra, geometry,
  physics lists, `StoreSimulationInfo all`, and isotope store are retained.

The source contract is pinned to
`5424eeca35b20affb153c0e07c31a6582e575f511922bf55f40a5a0f77ab4326`.
The batch is also chained to the PASS batch0000 ledger with SHA-256
`036335b186bb1e8d9dbec53e0e8994dd8cb1fc055b930469b8d7d144f60b263f`.

Instant seeds use the explicit 83.1-million namespace and buildup seeds use
the 84.1-million namespace.  They are disjoint from batch0000's 81/82-million
sets and from the reserved full-target namespace beginning at 860,811,003.
The same-mode seed equality between Mass and O8 is intentional matched-A/B
provenance; raw results are never pooled across geometries.

## Resource gate

The preflight estimator reads only the hash-pinned corrected-keV batch0000
SMOKE summaries.  It does not use the shared runner's obsolete
`_2602units` estimator.  On the 2026-08-11 preflight:

- point output estimate: 1.399 GB;
- gated estimate at 2x: 2.799 GB;
- mandatory free-space reserve: 20 GB;
- required free space: 22.799 GB;
- observed free space: 138.238 GB;
- disk gate: `PASS`.

These were noisy small-sample extrapolations, so the wrapper verified the
source/geometry/transport hashes immediately around every campaign and never
allowed the 20 GB reserve to be consumed by the planned batch.  The completed
four campaigns occupy about 2.332 GB; the filesystem retained about 136 GB
free after the run.

## Commands

Read-only preflight; this never creates run outputs or launches Cosima:

```bash
python3 engineering/particle_source_unit_repair_20260811/code/run_mergeable_two_geometry_seven_family_batch0001.py \
  --print-plan --workers 4
```

Execute the fixed write-once batch:

```bash
python3 engineering/particle_source_unit_repair_20260811/code/run_mergeable_two_geometry_seven_family_batch0001.py \
  --workers 4
```

After transport, the wrapper automatically runs the dynamic validator.  A
read-only repeat is:

```bash
python3 engineering/particle_source_unit_repair_20260811/code/validate_mergeable_two_geometry_seven_family_batch0001.py \
  --check
```

The completed authority files are:

- `runs/particle_source_unit_repair_20260811/seven_family_batch0001_v1_contract.json`;
- `runs/particle_source_unit_repair_20260811/seven_family_batch0001_v1_validation.json`;
- `runs/particle_source_unit_repair_20260811/seven_family_batch0001_v1_ledger.json`.

Dynamic validation passed 40/40 jobs and 466,692/466,692 `IA INIT` records,
with 800 corrected spectrum references, zero legacy references, and no proton
job.  The validation status is `PASS`; the ledger is
`PASS__BATCH0001_MERGE_ELIGIBLE` (SHA-256
`bb89c618d519a6a8570c8c746012c9ad0e81cb427b2a23145084a429c34c5df4`).
Prompt quantities merge as
`sum(selected)/sum(TT)` within one geometry, mode, and family.  Activation
quantities merge as `sum(RP)/sum(TT)` within one geometry, mode, family,
production volume, and isotope state, including TT from registered zero-RP
batches.  No hardcoded replica divisor is permitted.

## Full-stat boundary

The historical full target is 10,000,000 gamma events plus eight flux-scaled
replicas for each other family, separately for both geometries and both modes.
After crediting batch0000 and batch0001, 92,882,280 primaries remain.  Scaling
the 40 completed batch0001 jobs gives a retain-all point estimate of about
1.091 TB and 383.93 CPU-hours.  A minimal 2x disk margin plus the mandatory
20 GB reserve requires about 2.202 TB free; at least 2.5 TB is recommended.
The local filesystem has only about 136 GB free, so retain-all full statistics
remain fail-closed until an external-transfer or validated staged-retention
strategy exists.  Passing batch0001 provides valid additional transport
statistics; it does not by itself restore delayed-chain, detector-response,
physics-rate, sensitivity, or geometry-promotion authority.
