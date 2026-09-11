# Independent evaluator feedback 02 — transport remains blocked

Date: 2026-08-12 14:00 Asia/Shanghai  
Scope: isolated package `engineering/particle_source_unit_repair_20260811/m05_complete_compact_smoke_20260812/`  
Decision: **NO-GO for the first Cosima event; GO only for remediation, compile-only checks, fixtures, and read-only preflight.**

The second-opinion session has made useful progress: public COSI/MEGAlib patterns are now versioned, a local shadow engine can be built without modifying the installed MEGAlib tree, and the proposed hook reaches sensitive deposits and the native isotope commit point. None of those facts yet establishes a runnable or M05-complete compact arm. Keep `transport_authorized=false` and `transport_events_launched=0` until every item below is closed and independently re-reviewed.

## P0 — deterministic runtime and physics failures

1. **Fix the Geant4 event lifecycle.** `GeneratePrimaries()` runs before `BeginOfEventAction()`. The current hook calls `RecordGenerated()` in the former but `BeginEvent()` only in the latter, so the first event fails (or later `BeginEvent()` clears the just-recorded primary). Use an explicit lifecycle such as `BeginGeneratedEvent(event_id)` before the EventList row is consumed, `RecordGenerated(...)` after the gun is configured, and a later `ConfirmEventStarted(event_id)` that only verifies and never clears state. Add a compile-time/source-order test and a zero-transport lifecycle fixture.

2. **Close aborted/native-populated event semantics.** Pass `aborted` and `native_event_populated` to `EndEvent`. A candidate/control event may be serialized only when native IA/HT content has actually been populated. Either fail on any aborted event or count it explicitly and require `aborted_count == 0` for PASS. Generated/root/completed/SE/ID/unique-IA-INIT counts must all equal the tape length.

3. **Configure only after successful parse and initialization.** `ConfigureFromEnvironment()` must not truncate or reserve outputs before command-line parsing and `MCMain::Initialize()` succeed. After initialization and before execute, interrogate the actual parameter file and require exactly one run, `PreTriggerMode Everything`, `StoreSimulationInfo All`, and no one-hit-only mode. Help, bad CLI, failed initialization, SIGTERM, timeout, or exception must leave only quarantined partials and no final authority.

4. **Keep the shadow executable single-threaded.** The scorer is a mutable singleton and is not MT-safe. The runner/preflight must reject `G4MTRunManager`/application MT and represent six cores only as up to six independent processes, subject to family-aware RSS tokens. This is not optional documentation.

## P0 — representation must remain M05-complete

5. **Make truth a valid, independently readable SIM, or supply a proven materializer.** Concatenated `ToSimString()` event fragments lack `Type sim`, `Version`, geometry and `EN`; MEGAlib cannot safely parse them as a standalone SIM. Either write a valid envelope or publish a hash-bound materializer and prove a real `MFileEventsSim`/Revan round-trip with event/IA/HT counts and hashes unchanged.

6. **Use the correct compact selection grain.** Full native truth should be retained for **every raw TES-positive event**, independent of energy window, veto, response smear, or downstream cut. Veto-only events need all-event per-block active-shield summaries but do not need duplicate full IA/HT truth. Add a pre-registered deterministic TES-zero control set with at least one root per geometry × mode × family × subshard; `hash % 100` alone may yield no control in a 100-event shard. Activation remains all-RP, independent of this selection.

7. **Preserve typed veto blocks, not only totals.** The physical contract needs eventwise entries for all 24 Mass CsI blocks, all 3 O8 BGO blocks, and all 3 O8 plastic blocks, with detector UID/type/energy/time and a hash-bound whitelist. Kapton, BPE, W, and Al must be excluded from active veto. Validate block completeness, block-to-type sums, event totals, and 50/70/80-keV decisions against F. A wide per-step diagnostic TSV may be kept for the smoke, but it cannot be assumed necessary in the projected production representation unless the consumer test proves it.

8. **Fix time semantics.** The compact pixel time currently mixes PRE-time weighting/min with POST-time max, while native `CC HIT` uses POST time. Define and version the interval semantics; for an exact F/C regression, reproduce the native POST-time observable and retain any additional interval fields separately.

9. **Replace column-name pseudo-schemas with real record validation.** Every TSV/table needs exact header, required fields, scalar/vector types, finite and range checks, enums, hash regexes, unique/composite keys, foreign-key joins, row counts, and `additionalProperties=false` equivalent behavior. The current logical schema must be satisfiable (do not require more unique enum values than exist). A `rules` prose constant is not an executable gate. Add negative fixtures for malformed types, NaN/Inf, duplicate keys/rows, missing detector blocks, broken joins, and altered hashes.

10. **Make output publication transactional and durable.** Before any output is opened, reject every existing final target. Use exclusive partial creation in an allowlisted run directory. Before publication, flush/check/close/check every stream; verify expected sizes/digests; fsync files and parent directory; rename all data files; publish the footer/manifest last as the commit marker. Disk-full or any exception must never leave a final-looking partial set.

## P0 — root, source, RP and authority closure

11. **Do not call the inferred direction bin an exact original driver.** The donor SIM stores rounded directions and a boundary event can map to multiple angular bins. Record `driver_inference`, ambiguity set and quality, or define the benchmark driver as the EventList tape/root identity. `stable_root_id` is an ordered benchmark identity, not the original atmospheric-source ID. The scientific source normalization must bind all 20 corrected-keV spectra and fluxes.

12. **Prove tape row ↔ generated primary ↔ IA INIT at the correct precision.** Implement an observed high-precision generated-tuple hook plus a separately defined serialized-IA tolerance/format. Validate exact count/order/no duplicate/no missing across every F/U/N1/C arm. Recompute every stable-root/raw-line/tuple digest from fields; reject duplicate TI, malformed ID/EN, nonfinite state, invalid direction norm, wrong particle/family/source hash, or successor rows. Publish tape and sidecar atomically with a manifest.

13. **Finish exact RP validation.** Recompute the excitation IEEE-754 bits from the displayed value; require valid Z/A/state/time/track ranges; require ancestry to be an integer chain from the primary to the produced track; join every RP row to roots/tape and to a geometry classification manifest; verify physical/logical/touchable/material/driver/family/root. Native DAT only offers aggregate closure, so state the evidence accurately as runtime native-commit serial/count plus exact DAT aggregate reconciliation, not DAT row-by-row identity. Zero-RP BUILDUP must still have positive TT.

14. **Pin ledger + validation pairs and deepen the canonical checks.** For batch0001 and prefix76, pin and verify both report and ledger path/SHA/status/canonical bytes. Explicitly require batch0001 errors `[]`, four campaigns, ten jobs per campaign, forty jobs/466,692 events, seven-family set, source-contract hash and both geometry bundles. Prefix76 must require its recorded validation SHA/status and exact ordinals 1…76. Continue to forbid recursive receipt discovery and exclude the unpaired Mass ordinal77.

15. **Reject duplicate-key JSON and lexical symlinks everywhere.** Use a duplicate-key rejecting JSON parser before canonical-byte comparison. Check each lexical path component with `lstat` before `resolve`; a repo-internal symlink must not bypass the authority-path gate.

## P0 — reproducible shadow build

16. **Regenerate an exact-current-tree patch.** Pin every patched file, including `MCRun.hh` and `MCRunManager.cc`, before copy. Apply with zero fuzz and reject `FAILED`, reversed, offset/fuzz not explicitly authorized, or hash drift. Record complete pre-patch and post-patch manifests, extension sources, compiler/ROOT/Geant4 configuration, linked-library/RPATH manifest, logs, and final binary hash. A compile-only PASS is useful but cannot override the physics/data blockers above.

17. **Do not self-authorize transport.** A successful executor preflight must end at `WAIT__PREFLIGHT_PASS__TRANSPORT_BLOCKED_PENDING_INDEPENDENT_REREVIEW`. The independent reviewer will hash the final contract, sources, patch, binary, schemas, tapes, generated cards and preflight report, then issue a separate write-once authorization token if and only if all gates pass.

## Full-seven-family decision boundary

18. The current minimum matrix measures only 12 of 28 geometry × mode × family cells. Its conservative full-target disk conclusion is correctly **NO-GO**, not a capacity optimization verdict. For the user's paper-preserving objective, expand the representation smoke to all 28 cells before claiming full-seven-family performance: both geometries; instant and BUILDUP; gamma, neutron, electron, positron, alpha, muon-plus and muon-minus; at least three matched subshards per cell. Counts for e− and muons may be small, but must estimate their own representation/runtime and exercise zero/nonzero-RP cases. Heavy gamma/n/e+/alpha counts and stress cassettes must remain as contracted. If this expansion is not run, the final status must remain `PARTIAL__NO_GO_FULL_TARGET`.

19. Rewrite the projection as two explicit quantities: historical total and remaining-after-pinned-batch0000…0005 credits, with no duplicated identity and current retained disk included. Separate fixed bytes/job from bytes/event; call the Cosima timer `beam_on_elapsed_s`, not OS CPU; handle impossible speed denominators as null/blocked. Final disk upper95 and reduction lower95 must come from matched smoke distributions and per-cell heavy-tail bounds, not point estimates.

20. Performance comparisons require at least three matched, arm-order-rotated subshards and paired log-ratio intervals by cell. Report wall, BeamOn elapsed, OS CPU, peak process-group RSS, bytes by artifact type, serialization/compression time, and validation cost. No N0 means no claim that Geant4 transport itself was accelerated; F/U/N1/C may establish capacity savings and output-path wall savings only.

## Next permitted actions

- Fix code/contracts/tests only inside the isolated dated package.
- Re-run unit/negative fixtures, exact zero-fuzz shadow build, and read-only/write-once preflight.
- Update `EXECUTION_STATUS.json` with this file path/SHA and keep zero transport.
- Stop and request independent re-review. Do **not** launch F, U, N1, C, EventList capture, or any Cosima event yet.

