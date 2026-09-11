# Independent evaluator feedback 01 — transport remains blocked

Date: 2026-08-12

The external/installed implementation review is sufficient to continue
contract, scorer, build, and preflight work, but it is not yet sufficient to
launch transport.  Resolve the following in documentation, frozen schema,
code, tests, and preflight before the first Cosima event:

1. **EventList root/driver provenance.**  `MCSource.cc` parses the EventList
   row ID, but the installed implementation does not propagate that ID into
   the simulated event, and file-event-list sources have an empty volume name.
   A common tape therefore proves the primary state only.  Freeze a tape
   sidecar containing row index, stable root ID, driver, family, source-card
   provenance, and the complete primary tuple.  Validate exact
   `tape row <-> generated event <-> IA INIT` one-to-one order and tuple hashes
   in every arm.  The compact scorer must not consume RNG.

2. **Exact BUILDUP RP completeness.**  The installed `IP RP` comment has
   physical volume, position, ZA/state/time, track/parent/process/particle
   fields, but does not itself contain the required primary/root ID, material,
   or explicit logical volume.  The native isotope DAT contains only TT and
   aggregate volume/ZA/state/count.  Capture the missing fields at the exact
   `AddIsotope` production point in the isolated scorer/engine hook, or prove a
   lossless reconstruction.  Require every stored RP sidecar row to match one
   and only one actual isotope production, and require its aggregate to equal
   the native DAT.  Zero-RP BUILDUP jobs must still retain their positive TT.
   An event-relegator selected-truth record by itself is not sufficient.

3. **Frozen external identities.**  Do not label unversioned arXiv URLs as v1;
   pin explicit versioned arXiv URLs and/or the journal DOI.  GitHub
   `main`/`develop` pages without an immutable commit are supplemental design
   evidence only.  Use commit/blob URLs where available and bind installed
   local file hashes as the actual executable implementation authority.

4. **Full seven-family projection.**  The required transport smoke covers
   gamma, neutron, e+, and alpha, but production also includes e- and muons.
   Any full-target disk/speed projection must include unmeasured families with
   an explicit conservative no-benefit bound (or add measured cells); never
   renormalize the measured four families to 100%.

5. **Receipt discovery.**  Resolve inputs only through canonical benchmark
   manifests/ledgers.  Do not recursively glob all historical receipts:
   batch0003 contains an extra unpaired 25,000-event Mass receipt which is not
   part of the authoritative ordinal-76 prefix.

Update `EXECUTION_STATUS.json` atomically if these checks force WAIT/NO-GO.
Do not launch transport merely because the external-review Markdown says PASS.
After implementing the fixes, run strict unit/preflight tests and leave the
contract, code, source/build hashes, and preflight artifacts for a second
independent review.  Only then may transport launch.
