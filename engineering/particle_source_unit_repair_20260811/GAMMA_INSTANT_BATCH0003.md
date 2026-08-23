# Corrected-keV instant-gamma batch0003 controller

Status: controller and validator implemented; transport not launched by this
preparation step.

This batch is the bounded gamma-first campaign for the two retained geometries:

- Mass_model_511;
- S3d-O8.

It credits the already merge-eligible 1,000-event batch0000 and 100,000-event
batch0001 instant-gamma samples only after proving that their normalized
transport fingerprints and complete geometry bundles are exactly equal to the
new run. The frozen ceiling adds exactly 9,899,000 corrected-keV primaries per
geometry. The default execution stops after adding 4,899,000 per geometry and
publishes the independently merge-eligible 5,000,000 cumulative checkpoint. A
10,000,000 cumulative extension is optional, explicit, and possible only
inside the same frozen 12-hour execution window; an expired window requires a
new rollover batch with disjoint seeds.

## Fixed shard and seed contract

There are 396 operationally paired shard ordinals. Ordinals 1--195 contain
25,000 primaries per geometry, ordinal 196 contains 24,000 and closes 5M, and
ordinals 197--396 contain 25,000 and close 10M. The two geometries use the same
registered seed and event count at a given ordinal; all 396 seeds are unique
and disjoint from batches 0000--0002. A retry keeps the same seed and uses a
new write-once attempt directory.

The pairing is administrative: equal-N, same-seed operational commit and
provenance. Geometry-dependent transport causes the random streams to diverge,
so this is not common-random-number sampling, gives no paired-estimator or
variance-reduction authority, and geometry rates must be normalized and
compared independently. Events are never pooled across geometry, mode, or
particle family.

## Safety envelope

- default worker cap: 4;
- requested maximum: 8, reached only through measured process-group RSS gates
  (4 to 6 to 8); an uncalibrated `--workers 8` does not launch eight jobs;
- no new attempt after T+8h; live transport is terminated by T+9h; T+9--T+12
  is reserved for receipt adoption, full validation, and authority publication;
- 20 GiB retained-free-space contract plus an approximately 6.15 GB emergency
  abort margin during active transport, checked every 2 seconds;
- 2x remaining-output disk gate plus a worst-case active-attempt burst margin;
- per-attempt output cap, 1.5 GB hard low-memory abort, and 15-minute no-CPU plus
  no-output-growth hang watchdog;
- one controller process lock, stale-child refusal, and SIGINT/SIGTERM cleanup
  of all registered process groups;
- no automatic deletion of SIM, DAT, log, source, code, paper, or prior data.

Each attempt hashes the source contract, 20 corrected spectra, source card,
transitive geometry bundle, transport executable/libraries/data environment,
and toolchain immediately before transport, on heartbeats, and immediately
after transport. A shard is credited only after the validator reads the gzip
to EOF and proves exact `SE`, `ID 1..N`, one gamma `IA INIT` per event,
corrected per-bin energy support, geometry header, seed, positive matching
DAT/log `TT`, command, return code, and artifact hashes.

Canonical stage reports and ledgers are published only on PASS. `--check`
requires an existing report/ledger pair to equal a fresh full revalidation;
failed checks never overwrite authority. A crash after report publication but
before ledger publication can be resumed only when the report is byte-content
equivalent to the fresh expected report.

## Commands

Read-only planning and all prior-batch revalidation. This never launches
transport; it may invoke `cosima --help` solely to fingerprint the executable:

```bash
python3 engineering/particle_source_unit_repair_20260811/code/run_mergeable_gamma_instant_batch0003.py \
  --print-plan --workers 4 --wall-limit-hours 12
```

Run the frozen campaign only after the printed live disk gate is PASS:

```bash
python3 engineering/particle_source_unit_repair_20260811/code/run_mergeable_gamma_instant_batch0003.py \
  --workers 4 --wall-limit-hours 12 --stop-after 5m
```

The command exits zero immediately after the 5M PASS report and ledger and does
not dispatch shard ordinal 197 or later. To request the 10M ceiling explicitly
within that same unexpired execution window, use `--stop-after 10m`.

Read-only checkpoint revalidation, after the corresponding authority exists:

```bash
python3 engineering/particle_source_unit_repair_20260811/code/validate_mergeable_gamma_instant_batch0003.py \
  --stage 5m --check
python3 engineering/particle_source_unit_repair_20260811/code/validate_mergeable_gamma_instant_batch0003.py \
  --stage 10m --check
```

The fixed 10M ceiling remains in the contract when execution intentionally
stops at 5M. Partial receipts below a fixed checkpoint are not merge authority;
they remain write-once resume evidence within the frozen deadline. An expired
incomplete campaign requires an explicit, disjoint-seed rollover contract
rather than silently extending its deadline.
