# C/N1 shadow runtime contract (pre-transport review)

This contract describes the isolated shadow only. It does not authorize an
event. F/U still use installed production Cosima. A hash-bound MCRun
LD_PRELOAD post-GPS observer exists only as a dormant compile-only candidate;
P12 remains blocked until a separately authorized installed plain-versus-
preload 672-event sentinel and independent rereview pass. All 448 planned jobs
remain non-runnable and transport events remain zero.

The shadow is configured only after command-line parse and `MCMain::Initialize`
succeed. It requires exactly one run, `PreTriggerMode Everything`,
`StoreSimulationInfo All`, `StoreOneHitPerEvent false`, an event-count stop
equal to the frozen tape length, and no native rich-SIM `FileName` for C/N1.
It rejects a Geant4 MT application; host concurrency is independent sequential
processes only.

Required environment (all values nonempty):

- `TES511_SMOKE_ARM` (`C` or `N1`)
- `TES511_GEOMETRY` (`mass_model_511` or `s3d_o8`)
- `TES511_MODE`, `TES511_FAMILY`, `TES511_JOB_ID`
- `TES511_SHARD_INDEX`, `TES511_SEED`
- `TES511_TAPE_ROOT_SIDECAR`
- `TES511_OUTPUT_PREFIX` (absolute final prefix, without `.m05cc`)
- `TES511_ALLOWED_RUN_DIRECTORY` (the resolved output-prefix parent)
- `TES511_RECORD_SCHEMA_SHA256`
- `TES511_N1_COMMIT_SCHEMA_SHA256`
- `TES511_VETO_WHITELIST_SHA256`
- `TES511_GEOMETRY_CLASSIFICATION_SHA256`
- `TES511_GEOMETRY_BUNDLE_SHA256`
- `TES511_TAPE_ROOT_SIDECAR_SHA256`
- `TES511_RUNTIME_SOURCE_CARD_SHA256` (generated EventList source card)
- `TES511_CORRECTED_SOURCE_CARD_SHA256` (corrected 20-driver source card bound by tape)
- `TES511_SOURCE_CONTRACT_SHA256`

For C/N1, the source card must set `IsotopeProductionFile` to exactly
`<TES511_OUTPUT_PREFIX>.m05cc.partial/native`. Native `SaveIsotopeStore()` then
resolves the durable file as `native.inc<I>.dat` or
`native.p<P>.inc<I>.dat`; the scorer verifies the actual path against native
parallel/incarnation IDs before publication. All table files and native DAT
remain inside the mode-0700 partial directory. Streams and DAT are checked,
fsynced and hash-bound; `record_bundle.json` (C) or `commit.json` (N1) is
created last, then the complete directory is atomically published to `.m05cc`
with Linux `renameat2(RENAME_NOREPLACE)` and no ordinary-rename fallback.
Signal, timeout, exception, abort, count mismatch, collision, or I/O failure
leaves only conspicuous non-authoritative `.m05cc.partial` or collision-safe
`.m05cc.failed*` evidence. In particular, a parent-directory fsync failure
after stage-to-final rename moves only the exact just-published owned inode out
of the final name before the process reports failure; a foreign incumbent is
never moved or replaced.

Both C and N1 transactionally retain one `generated_observations.tsv` row per
tape row. C additionally retains the M05 compact tables/truth controls and
publishes only `record_bundle.json`, validated by the m05cc-v2 physical-bundle
validator. N1 publishes only `commit.json` under the independent canonical
`m05cc-n1-v1-commit` schema. Its strict `code/n1_validation.py` authority binds
and checks exact directory membership, root/generated/footer/tape row counts,
file sizes and hashes, lifecycle closure, stable-root/driver/raw and generated
binary64/IA joins, runtime and corrected source cards, source contract,
geometry classification and bundle, whitelist, positive native TT, and the
native aggregate isotope count. N1 has no RP lineage sidecar and is never an
input to the standalone-SIM materializer; only C can satisfy that consumer.
The tape is opened once with `O_NOFOLLOW`, checked as a regular single-link
file, read and hashed through that descriptor, then the same frozen bytes are
parsed and copied into the transaction. C uses streaming pixel/block
aggregates; production `deposits.tsv` is header-only. Native full truth is
selected by `rawTES || preregistered_control`; active-veto-only roots retain
typed block aggregates without full truth.
