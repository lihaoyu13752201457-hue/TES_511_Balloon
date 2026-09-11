# M05 SG3/SH3 prompt-statistics integration (2026-08-28)

This package is a non-overwriting bridge from the receipt-PASS prompt
supplements prepared by package 67 to compact event/deposit caches.  It does
not run Cosima, hash a SIM payload, merge models or setup strata, assign the
final old-plus-new normalization, run a Poisson timeline, or edit the paper.

The retained inputs are deliberately narrow:

- SG3 mass model A, main setup stratum: 11 completed receipt-PASS jobs;
- SH3 mass model B, main setup stratum: 310 completed receipt-PASS jobs;
- seven corrected-keV atmospheric prompt families only;
- the package-62 SG3 scanner and the current Step05-exact SH3 scanner.

The receipts still contain the historical `/mnt/data` prefix.  The builder
accepts that prefix only and maps it to the mounted read-only NTFS volume
`/media/ubuntu/903261CE3261BA3C`.  It fails if the mount is not read-only, if a
mapped path escapes the mount, or if receipt/controller/job-plan/source/setup/
SIM-header/seed/size closure differs.  Source cards and small setup/config/code
authorities are SHA-256 checked; SIM files are never hashed.

## Usage

Preflight is the default and is safe to repeat:

```bash
python3 code/build_supplement_compacts.py --preflight --model both
```

Full streaming compaction requires the explicit execution flag:

```bash
python3 code/build_supplement_compacts.py --execute --model both --workers 2
```

Execution writes only below `outputs/sg3/` and `outputs/sh3/`.  Each raw SIM is
streamed once by the retained scanner into an independent per-job NPZ/JSON
cache.  The model-level `jobs.json` records actual per-family exposure,
provenance, seeds, cache paths, and base-lineage overlap audit.  Its per-job
`weight_cps` is intentionally zero/deferred: the downstream merger must assign
one common `1/(TT_old+TT_new)` weight to every old and new prompt template of a
given model/family/setup stratum.

## Outputs

- `outputs/preflight_audit.json`: targeted, header-only input closure;
- `outputs/<model>/job_catalogs/`: independent retained-parser compact caches;
- `outputs/<model>/jobs.json`: downstream merge contract;
- `outputs/<model>/scan_audit.json`: execution and compact closure.

No output from task `01a02314-a50b-78d2-bb8c-b43ffa350704` is referenced or
read by this package.
