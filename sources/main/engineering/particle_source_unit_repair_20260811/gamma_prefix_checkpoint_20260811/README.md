# Batch0003 committed-pair prefix checkpoint

Status: `IMPLEMENTED__UNIT_AND_ORDINAL1_READ_ONLY_INTEGRATION_PASS__NO_PREFIX_AUTHORITY_PUBLISHED`

This dated package provides a safe fallback when the running corrected-keV
instant-gamma batch0003 does not reach its canonical 5M checkpoint before the
frozen time window closes.  It publishes only a complete continuous prefix of
already committed two-geometry pair receipts.  It does not run transport.

## Why the existing stage validator is not called directly

The frozen batch0003 validator is authoritative for the fixed 5M and 10M
stages, but its stage path reads the mutable execution-state file and requires
one of those two endpoints.  That is unsuitable for an independent prefix
fallback while the controller may still exist.

The prefix publisher reuses only the frozen validator's read-only
`validate_attempt()` logic, after a PASS pair receipt and its two hash-bound
geometry receipts have been snapshotted.  This retains the exact gzip EOF,
SE/ID/IA INIT, corrected-energy support, particle, direction, seed, geometry,
source-card, artifact, log, and isotope-DAT TT gates.  It never calls the
stage validator, never calls its shard writer, and never discovers attempt
directories.

## Hard isolation properties

- no read of `gamma_instant_batch0003_v1_state.json`;
- no read of `gamma_instant_batch0003_v1_controller.lock`;
- no attempt-directory glob or scan;
- no access to an attempt until an immutable PASS pair receipt and both
  receipt-bound geometry receipts validate;
- no Cosima process, including no `cosima --help`; transport is checked by
  executable/library/setup/G4-data content hashes only;
- no change to the runner, frozen validator, global contract, campaign
  controls, receipts, attempts, or live outputs;
- deterministic, independent, write-once report and ledger paths;
- existing authority is accepted only when the report's actual SHA-256 equals
  the expected canonical-report SHA-256 and the ledger-bound report SHA-256,
  and when the ledger itself has the exact expected canonical JSON bytes;
- a failed validation writes no authority file.

## Supported prefixes

The preferred operational checkpoints are:

| End ordinal | New events/geometry | Prior credit/geometry | Cumulative/geometry |
|---:|---:|---:|---:|
| 76 | 1,900,000 | 101,000 | 2,001,000 |
| 116 | 2,900,000 | 101,000 | 3,001,000 |
| 156 | 3,900,000 | 101,000 | 4,001,000 |

Any ordinal from 1 through the highest complete continuous committed prefix is
also supported.  No geometry-only shard, unpaired receipt, later shard beyond
a gap, or active/unreceipted attempt contributes any event.

Receipt-only discovery is safe during transport and does not touch attempts:

```bash
python3 engineering/particle_source_unit_repair_20260811/gamma_prefix_checkpoint_20260811/code/validate_gamma_batch0003_prefix_checkpoint.py \
  --discover
```

After transport has drained, validate an exact preferred prefix without
writing:

```bash
python3 engineering/particle_source_unit_repair_20260811/gamma_prefix_checkpoint_20260811/code/validate_gamma_batch0003_prefix_checkpoint.py \
  --prefix-ordinal 76 --check
```

Select the highest available preferred checkpoint (`76`, `116`, or `156`):

```bash
python3 engineering/particle_source_unit_repair_20260811/gamma_prefix_checkpoint_20260811/code/validate_gamma_batch0003_prefix_checkpoint.py \
  --prefix-ordinal milestone --check
```

Select the exact continuous prefix present when validation begins:

```bash
python3 engineering/particle_source_unit_repair_20260811/gamma_prefix_checkpoint_20260811/code/validate_gamma_batch0003_prefix_checkpoint.py \
  --prefix-ordinal auto --check
```

Remove `--check` only when the selected prefix is final and should be
published.  Outputs are created under the independent directory
`runs/particle_source_unit_repair_20260811/gamma_instant_batch0003_prefix_checkpoints_20260811/`.

## Validation and authority boundary

Before publication the tool revalidates:

- the pinned global/source/static contracts and all three prior ledger hashes,
  identities, statuses, and validation-report consistency;
- prior batch0000/batch0001 transport-core and geometry equivalence;
- the current Cosima executable, shared libraries, MEGAlib setup script,
  Geant4 data contents, corrected spectra/source cards, and transitive geometry
  bundles without starting Cosima;
- every credited prior instant-gamma artifact, source transformation, SIM
  event/INIT count, seed, geometry, energy support, DAT/log TT, and artifact
  hash (101,000 events per geometry);
- every selected pair receipt, geometry receipt, attempt-validation hash,
  attempt/artifact hash, exact event count, and positive matching TT;
- all source/transport/geometry/prior inputs again after the scan.

The ledger status is exactly `PARTIAL_PREFIX_MERGE_ELIGIBLE`.  It authorizes
merge of corrected-keV instant gamma samples only within each geometry using
`sum(selected)/sum(TT)`.  It is explicitly not canonical batch0003 5M/10M
stage authority, eight-family completion, delayed/response closure, a physics
rate or sensitivity result, or geometry-promotion authority.

## Tests

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s engineering/particle_source_unit_repair_20260811/gamma_prefix_checkpoint_20260811/tests \
  -p 'test_*.py' -v
```
