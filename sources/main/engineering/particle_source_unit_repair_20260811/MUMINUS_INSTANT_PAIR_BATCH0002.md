# Corrected-keV paired muminus instant batch0002

Status: `PASS__BATCH0002_MERGE_ELIGIBLE`

This write-once production-contributing shard transports only negative muons
through the two comparison geometries in instant mode:

- Mass_model_511: 10,000 primaries;
- S3d-O8: 10,000 primaries;
- paired seed: `860915732`;
- corrected-keV, 20-angle-bin source profile;
- proton and buildup transport: excluded.

The source contract SHA-256 is
`5424eeca35b20affb153c0e07c31a6582e575f511922bf55f40a5a0f77ab4326`.
The shard is chained to the merge-eligible batch0000 and batch0001 ledgers.

## Result

Both jobs completed with return code zero. Dynamic validation re-read all
20,000 events and found zero bad energy, particle, direction, seed, or
geometry records. Each corrected source card resolved 20 package spectra and
zero legacy `_2602units` spectra. DAT and log observation times match and are
positive.

- Mass_model_511: 10,000/10,000, 58.1871 CPU-s, 180.540 s exposure,
  59,154,266 bytes in the campaign directory;
- S3d-O8: 10,000/10,000, 144.862 CPU-s, 176.851 s exposure,
  133,153,543 bytes in the campaign directory.

The validation status is `PASS`. The ledger status is
`PASS__BATCH0002_MERGE_ELIGIBLE`, with ledger SHA-256
`742a4deb1bc3ab4585e479884d7e0ec376a0622f19391c8d87a2e66b92779a62`.
The standard `jobs:[...]` records register the seed for future collision
checks. A read-only revalidation also passes.

Authority files:

- `runs/particle_source_unit_repair_20260811/muminus_instant_pair_batch0002_v1_contract.json`;
- `runs/particle_source_unit_repair_20260811/muminus_instant_pair_batch0002_v1_validation.json`;
- `runs/particle_source_unit_repair_20260811/muminus_instant_pair_batch0002_v1_ledger.json`.

## Boundary

This shard may be merged only within the same geometry, instant mode, and
muminus family using the recorded TT exposure. Same-seed Mass/O8 output is a
paired A/B comparison and must not be pooled across geometries. It is not a
full seven-family completion, buildup result, delayed-chain result, detector
response, or geometry-promotion authority.
