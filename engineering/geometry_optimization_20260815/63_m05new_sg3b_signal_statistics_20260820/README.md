# M05NEW SG3B baseline closure

This non-overwriting package supplies the minimum missing SG3B baseline data
needed by the M05NEW paper comparison:

1. candidate-own transport of the frozen 37,194-ray Step09 EventList;
2. additional corrected-keV SG3B prompt-gamma statistics, stopped by a
   predeclared final-selection precision criterion;
3. a recomputed mature 81-node sensitivity result using SG3B signal and
   background only; and
4. a provenance-preserving update of the M05NEW comparison table.

The paper logic is **SG3B baseline -> diagnosed limitation -> OptV3 optimized
geometry -> matched quantitative comparison**.  No legacy factor-1000 source,
separate mono-511 component, or cross-geometry event pooling is permitted.

An initial launcher attempt omitted Cosima's required command-line `-s` seed
argument.  Its four completed gamma SIMs were byte-identical, and the initial
signal SIM also lacked the registered header seed; both were rejected before
catalog construction.  All completed/partial artifacts were moved to
paths ending in `_invalid_missing_cli_seed`.  The retained launcher requires
both the source-card seed and `cosima -s SEED`, and rejects any SIM whose header
seed differs.

A later desktop-session interruption left shard 17 fully closed but without a
receipt and left seven other SIMs partial.  Shard 17 was recovered only after a
full gzip CRC pass, exact header-seed/geometry checks, terminal
`ID 534624 / EN / TE / TS 534624` closure, and a fresh SHA-256.  The partial
SIMs were moved, not deleted, to an `interrupted_partial` quarantine.  A first
resume shell also lacked the MEGAlib dynamic-library environment; all 29
zero-byte return-code-127 attempts and their FAIL receipts were quarantined
before transport resumed.  The retained runner now loads and preflights the
MEGAlib/ROOT/Geant4 environment itself.  Production concurrency is capped at
four workers for RAM safety.

## Statistical stopping rule

The prompt-gamma supplement was accumulated in independent 534,624-event
shards.  The original diagnostic target was at least 10 combined W2-final raw
gamma survivors.  The retained 32 compact shards contain 17,107,968 new
primaries and six combined W2-final gamma survivors.  The gamma-only relative
uncertainty is therefore explicitly retained as 40.82%; it is not hidden by a
Gaussian claim.

The paper acceptance rule is instead the quantity that controls the reported
sensitivity: total direct-final day-15 relative statistical uncertainty below
20%.  The expanded catalog gives
`0.0542982 +/- 0.0080348 cps` (14.80%, effective N=45.67), so this rule passes.
The resulting SG3B 20-day Gaussian 3-sigma flux threshold is
`(5.4058 +/- 0.4014)e-5 ph cm^-2 s^-1` (7.42% relative error).

Four simultaneous Cosima processes were found unsafe for the largest shards:
available RAM fell below 1 GiB.  The incomplete jobs were interrupted and
quarantined, orphan Cosima processes were terminated, and the safe transport
ceiling was reduced to two workers.  Parser-only work used at most four small
streaming processes with no simultaneous Cosima transport.

The host rebooted on 2026-08-21 and the external `/mnt/data` device did not
re-enumerate.  Before the reboot, 32 compact catalogs had passed receipt,
source/SIM seed, geometry, source-hash, event-count, and cache metadata checks.
The final merge uses those retained catalogs.  Their normalization uses the
pooled exact exposure per primary from the first 15 retained activation-TT
records; all shards have the identical source contract and event count.  No
failed, zero-byte, partial, or seed-invalid attempt enters the catalog.

## Final comparison

- SG3B candidate-own W2-final Aeff: `15.12324 +/- 0.04492 cm2`.
- SG3B day-15 mature background: `0.05128019 cps`.
- SG3B 20-day 3-sigma Fmin: `(5.4058 +/- 0.4014)e-5 ph cm^-2 s^-1`.
- SH3 OptV3 20-day 3-sigma Fmin: `(2.2294 +/- 0.2086)e-5 ph cm^-2 s^-1`.
- Independent M05NEW validation: `21/21 PASS`.
