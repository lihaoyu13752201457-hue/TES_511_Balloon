# GPT-5.6-Sol ultra continuation: implement and run the isolated smoke

You are resuming the exact independent-review conversation that produced the
Scheme-B / M05-complete-compact recommendation.  The user now explicitly asks
you to think, implement, and run a small optimization smoke.  The primary Codex
session will independently audit your code, physics equivalence, timing, disk,
and RSS results and retains final GO/NO-GO authority.

## Authorization and isolation

- You may create code, tests, build products, manifests, and smoke outputs only
  in new dated locations:
  - `engineering/particle_source_unit_repair_20260811/m05_complete_compact_smoke_20260812/`
  - `runs/particle_source_unit_repair_20260811/m05_complete_compact_smoke_20260812/`
- Do not edit or overwrite retained geometry, source, ledger, validator, paper,
  batch0000--0005, MEGAlib installation, or prior results.
- Do not delete or compact any existing project data.  Keep every smoke arm for
  the independent audit.  New smoke material must stay below 10 GB and the live
  disk reserve must remain at least 20 GiB.
- All outputs are `NON_MERGEABLE_BENCHMARK`; never credit their events, TT,
  seeds, RP, or rates to production.
- Use only the corrected-keV source contract and the two frozen canonical
  geometries: Mass_model_511 bundle `6170bfaa...7a0b61` and S3d-O8 bundle
  `8cdb6577...a73492`.  Recompute and record full hashes rather than trusting
  these abbreviations.
- If implementation would require changing physics, production cuts, energy
  support, geometry, material, physics list, Geant4 data, or the installed
  MEGAlib tree, stop that branch and report the blocker.  A repo-local copied or
  patched build is allowed only if its complete source/build/toolchain identity
  is frozen and the reference arm remains the current production binary.
- Read-only network research is authorized for public primary documentation,
  papers, and source repositories because the user explicitly requested
  comparison with COSI and similar projects.  Do not upload project data,
  download or execute unpinned dependencies, or alter external systems.  No
  destructive actions.

## Non-negotiable physics contract

Optimization means the simulation algorithm and runtime itself, not rewriting
unrelated analysis or manuscript code to make the benchmark appear faster.
You are explicitly invited to investigate output/storage design, process and
thread scheduling, Geant4 region/production cuts, enabled physical mechanisms,
energy/direction strata or support restriction, variance reduction, and other
transport-level methods.  These are candidate arms, not automatically accepted
physics.  Preserve and independently validate at least:

1. primary root/event/family/E/position/direction/time and driver provenance;
2. eventwise TES pixel UID/layer, energy, centroid/time, multiplicity, order and
   the truth needed for the 420-eV-FWHM response and 0.3-keV threshold;
3. exact typed active-shield sums for Mass CsI and O8 BGO, O8 plastic separately,
   with Kapton excluded, plus the information needed to scan 50/70/80-keV veto;
4. primary/pair/annihilation/process ancestry for every M05 candidate and every
   pre-registered full-truth control event;
5. interaction order/position and input truth required by analytic Compton/FoV
   and Revan/ARM checks; do not replace these with only a final boolean;
6. coincidence/full-band event templates and source time needed for occupancy;
7. BUILDUP TT for every job including zero-RP jobs, plus every RP's ZA, state,
   material/volume, exact production position and root lineage needed for the
   NUBASE inventory, exact-position delayed source, common response, and
   mission-time fold;
8. hashes/schema sufficient to prove source/geometry/transport/scorer/seed and
   input-state identity.

The unmodified corrected-keV analog arm remains the reference.  A cut change,
physical-process change, primary-energy restriction, Russian roulette,
splitting, or importance-weighted arm is allowed only as an explicitly named
simulation candidate with a frozen support/weight contract and a matched
baseline.  It must demonstrate closure for the M05 observables above and must
retain high-energy shower -> pair -> annihilation, veto, and activation
contributions either directly or with proven unbiased weights.  Never infer
that an energy band is irrelevant merely because a tiny pilot has zero final
survivors.  Prompt and activation require separate weight/variance validation.
If equivalence or unbiasedness cannot be established, label that arm NO_GO;
do not silently weaken the physics to obtain a speed number.

Do not modify the existing analysis, geometry, source-authority, paper, or
production harness code.  Any engine/scorer/cut/biasing implementation belongs
only to the isolated smoke package (and, if needed, a repo-local isolated build)
with an auditable patch against the current production engine.

## Required executable smoke

## External implementation review is a pre-implementation hard gate

Do not design only from this repository.  Before freezing candidate arms or
changing/compiling the engine, search and read primary public sources and
official code from comparable projects.  At minimum investigate:

- COSI/COSI-balloon/COSI-SMEX use of MEGAlib/Cosima, detailed mass models,
  detector-effects engine, standard reconstruction pipeline and response
  generation;
- the COSI bottom-up atmospheric/cosmic/activation background simulation and
  how prompt and activation/delayed components, normalization and validation
  against flight/calibration data are separated;
- COSI anticoincidence simulations, including the published strategy of
  replacing prohibitively expensive optical-photon transport with a separately
  benchmarked spatial/energy response function;
- cositools/cosipy public response/event representations and any official
  parallel simulation or response-generation tooling;
- ComPair or similar balloon instruments using EXPACS + Cosima + detector
  effects + offline ACD/veto and Compton/pair reconstruction;
- official Geant4 documentation and examples for multithreading/tasking,
  region production cuts, generic biasing/importance/splitting/Russian
  roulette, scoring/ntuples, phase-space or parallel-world techniques.

Prefer collaboration/NASA/CERN/Geant4/MEGAlib official documentation, public
source repositories and peer-reviewed papers.  Record direct URLs, repository
paths/commit identities, access date and the exact implementation pattern;
separate facts found in sources from your inference.  For each pattern state
what information it preserves, what it drops, and whether it transfers to
TES pixels, exact veto, Compton/FoV/Revan, pair-annihilation feed-down and
activation exact-position lineage.  An external precedent is design evidence,
not proof for this instrument: every adopted method still needs the matched
M05-equivalence smoke.

Write `EXTERNAL_IMPLEMENTATION_REVIEW.md` and strict
`external_sources.json` before the first transport launch.  If reliable source
access is unavailable, publish `WAIT__EXTERNAL_REVIEW_INCOMPLETE` and do not
freeze or run candidate physics arms.

The installed MEGAlib source tree is itself a primary implementation source and
must be audited before inventing new machinery.  In particular inspect and cite
the actual behavior/code of:

- `${MEGALIB}/resource/examples/geomega/cosiballoon/` (official 2016 COSI
  balloon mass model, detector/shield triggers, detector-head vs gondola
  simulation scope and surrounding-sphere cost tradeoff);
- `${MEGALIB}/resource/examples/advanced/ModifiedCosimaOutput/` (custom Cosima
  output hooks and quick parser);
- `${MEGALIB}/resource/examples/advanced/EventList/` (frozen primary event-list
  input suitable for matched histories);
- `${MEGALIB}/resource/examples/advanced/DetectorEffectsEngine/`;
- `${MEGALIB}/resource/examples/advanced/Background/`, `ActivationPlotter/`,
  and `CoolDown/`;
- `${MEGALIB}/resource/examples/advanced/Pipeline/` and response/Revan examples;
- installed `dcosima`, `mcosima`, and `mpicosima` scripts/binaries, determining
  whether they provide process distribution, MPI, or true thread-level
  transport and how seeds/output assembly are handled;
- `MCEventAction`, `MCSteppingAction`, `MCIsotopeStore`, `MCActivator`,
  `MCRegion`, `MCPhysicsList`, sensitive-detector hit classes, and relevant
  parameter parsing.

Map each reusable local pattern to an isolated benchmark arm.  Prefer adapting
an official MEGAlib extension point or example in the new smoke package over
editing unrelated project code.  Do not modify the installed MEGAlib tree.

Lead the design, but the executed benchmark must include both geometries and
the following minimum stress coverage unless a measured resource gate forces a
fail-closed partial result:

- prompt gamma: 10,000 primaries per geometry;
- BUILDUP neutron: 2,000 primaries per geometry;
- prompt e+: 500 primaries per geometry;
- BUILDUP e+: 500 primaries per geometry;
- prompt alpha: 100 primaries per geometry;
- BUILDUP alpha: 100 primaries per geometry.

Use a frozen initial-state tape or an equivalently exact method so that output
arms within a geometry/mode/family consume identical primary states and
transport RNG without the scorer consuming RNG.  Sharing seeds alone is not
proof of matched primaries.  Across geometries, identical states are desirable
but post-transport event identity must not be assumed.

Implement the five causal arms from your audit wherever technically possible:

- `N0`: rich record/object/string hooks disabled, no event file;
- `N1`: current rich records constructed but no file;
- `U`: current rich uncompressed;
- `F`: current production rich gzip;
- `C`: proposed M05-complete compact scorer/sidecars and selected/control truth.

Split into at least three subshards per cell and rotate arm order.  Serialize
high-RSS O8 n/e+/alpha work; do not blindly occupy six workers.  Record BeamOn,
process wall, CPU, peak process-group RSS, logical/uncompressed and on-disk
bytes, record-type counts, and validation time separately.  If N0/N1 require an
unsafe or infeasible engine change, prove that precisely; still execute the
safe matched F/C/U subset, and do not claim a transport-speed decomposition or
wall-speed GO.

Also run a representation-regression cassette over existing corrected rich
gamma/n/e+/alpha inputs containing TES, W2, pair/annihilation, veto, and RP
cases.  It is for structural equivalence, never for rates.

## Hard equivalence and performance gates

For matched histories, compare exact integer/UID/volume/process fields and use
`abs <= 1e-6 keV` or `rel <= 1e-9` only for serialized floating values.  Require
event-level and aggregate closure for TES pixel sums/centroids/times,
multiplicity, 480--550 keV, W2 510.58--511.42 keV, shield/plastic deposits and
veto bits, Compton/FoV class and required input truth, candidate/control
ancestry, TT, and RP one-to-one ZA/state/volume/position/root matching.

Using identical response/time seeds, require exact downstream response,
cut-flow, spectra, coincidence/occupancy, Revan candidate/control input and
status, NUBASE inventory, delayed-source hash/position-parent match, and
mission-fold equality for the smoke/cassette support.  If a downstream stage
cannot be meaningfully exercised at smoke statistics, run a deterministic
fixture that proves schema equivalence and clearly label it as a fixture.

Performance is accepted only if the measured paired analysis supports:

- physics/provenance gates: all PASS;
- projected full-target disk 95% upper bound below 80 GB (at least about 13.6x
  reduction from retain-all);
- paired wall-speedup 95% lower bound at least 1.5x;
- compact peak RSS no more than 1.2x the full arm.

If only capacity passes, call it capacity-only.  If N0/N1 were not executable,
do not claim the origin or magnitude of transport speedup.  Sparse smoke counts
cannot establish physical rates or geometry ranking.

## Required durable deliverables

Before transport, create a write-once benchmark contract and preflight report.
After the run, retain raw timing/RSS/size tables, initial-state hashes, per-arm
manifests, event-equivalence tables, downstream fixture/consumer tests, and all
validation output.  Produce at least:

- `EXECUTOR_REPORT.md` with proposal, implementation, evidence, limitations,
  and your own provisional GO/NO-GO;
- `benchmark_contract.json`;
- `preflight_validation.json`;
- `raw_metrics.csv`;
- `physics_equivalence.json`;
- `performance_summary.json`;
- `FINAL_VALIDATION.json`.

All JSON must be strict/canonical and all deliverables must bind actual hashes.
Never publish PASS if an expected arm/cell/consumer is absent; use explicit
`PARTIAL`, `WAIT`, or `NO_GO`.  Do not modify your previous audit package except
for reading it.  Begin now: inspect the dirty worktree, develop in the isolated
directory, self-review, run the smoke, and leave the terminal at a concise
status prompt so the primary session can ask follow-up questions.

The first writable continuation terminated unexpectedly during engine/build
feasibility inspection before creating the isolated package or launching
Cosima.  On resume, continue from that evidence.  Create a small durable
`EXECUTION_STATUS.json` before lengthy implementation/build/transport work and
update it atomically to `RUNNING`, `WAIT`, `NO_GO`, or final status so another
terminal exit can never look like a successful or unstarted benchmark.
