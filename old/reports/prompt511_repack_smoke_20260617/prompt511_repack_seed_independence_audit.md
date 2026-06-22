# Prompt-511 Repack Seed Independence Audit

Status: `PASS_CLI_SEED_REPACK_INDEPENDENT_LEGACY_NOT_INDEPENDENT`

This audit checks whether prompt-repack replicas are independent. It is a
method/provenance audit for the W-liner diagnostic, not a rate authority.

## Repack SIM Hashes

Large repack SIMs use a prefix hash over `8388608` bytes,
then cross-check selected-event signatures from the L1 proxy summary.

| tag | files | unique prefix SHA256 | duplicate groups |
|---|---:|---:|---:|
| legacy_eplus | 4 | 1 | 1 |
| legacy_n | 16 | 4 | 3 |
| cli_seed_eplus | 4 | 4 | 0 |
| cli_seed_n | 16 | 16 | 0 |

## Selected-Event Signatures

| tag | files | unique selected signatures |
|---|---:|---:|
| eplus | 4 | 4 |
| n | 16 | 16 |

## Seed Checks

| check | files | unique SHA256 | interpretation |
|---|---:|---:|---|
| source_seed_eplus_g2e4_r2 | 2 | 1 | repeated output |
| cli_seed_eplus_g2e4_r2 | 2 | 2 | different outputs |

## Conclusion

- The source-card `Seed` field is not sufficient for independent replicas in
  this runner path: the source-seed eplus check produced two identical SIM
  hashes despite different kept source files.
- Passing `-s <seed>` to `cosima` fixes the small seed check: the two CLI-seed
  replicas have different SIM hashes.
- Legacy W-liner eplus and n repack rows must be treated as repeated-seed
  diagnostics. Their central rates are at best few-sequence estimates under
  the replica weight convention, and their counting uncertainties/high-stat
  claims are not valid.
- CLI-seed repack rows, when present with one unique prefix hash per file,
  replace the legacy repeated-seed rows for quantitative prompt diagnostics.
