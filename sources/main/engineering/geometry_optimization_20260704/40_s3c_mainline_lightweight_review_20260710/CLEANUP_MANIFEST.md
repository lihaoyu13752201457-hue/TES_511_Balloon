# Legacy S3/S3a/S3b cleanup manifest

Executed: 2026-07-10  
Cleanup script: `code/cleanup_legacy_s3_data.sh --execute`

## Result

- Deleted 36 legacy run/output directories covering S3, S3a, and S3b prompt,
  atmospheric-511, buildup, instant, exact-position, decay-source, delayed
  transport, and Step09/Step05 response products.
- Deleted two invalid/partial legacy engineering directories.
- Deleted seven obsolete root-level S3abc builders, validators, and run-plan
  files after moving the S3c rebuild dependency into this package.
- Pruned twelve legacy engineering packages to an exact allowlist of 27
  Markdown conclusion documents.
- Dry-run inventory before execution targeted 63,101,511,681 bytes
  (58.768 GiB). Filesystem free space increased from roughly 34 GB to 93 GB;
  the final filesystem usage is 68%.

The cleanup script rejects absolute paths, parent traversal, and any target
containing `s3c`. It is idempotent and defaults to `--dry-run`.

## Retained conclusion authority

The original legacy engineering directories now contain exactly 27 `.md`
files and no other file type. Three compact machine-readable conclusion
snapshots are additionally frozen under `retained_conclusions/` so the S3c
analysis can reproduce historical comparison points without restoring any raw
legacy simulation.

The three root-level S3abc final review Markdown documents and the retained
Mass511-to-S3 conclusion presentation remain conclusion products; they are not
simulation run directories.

## Post-cleanup verification

`code/validate_s3c_mainline.py` reports:

- 16/16 retained S3c prompt jobs present with matching geometry headers;
- retained 3M atm511 source, SIM, log, and summary present and geometry-valid;
- retained S3c dominant-background summary geometry-valid;
- clean neutron-only delayed normalization and transport valid, including
  NUBASE status, eight files, TT division eight, `M=50000`, and
  `SE=ID=1000000`;
- no legacy S3/S3a/S3b run directory remains in the scoped campaign;
- exactly 27 legacy conclusion Markdown files remain, with zero non-document
  files in the pruned packages;
- all explicit removal targets are absent;
- the technical report payload exactly matches the reviewed analysis rows and
  its desktop/narrow/no-JavaScript render QA passes.

Validator terminal status: `PASS_S3C_MAINLINE_AND_LEGACY_CLEANUP`.

