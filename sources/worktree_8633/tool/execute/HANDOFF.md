# Canonical Cosima execution handoff

## Authority decision

`tool/execute/` is the single execution-code entry for subsequent project
Cosima transports.  Do not create another stage-specific multiprocessing
runner or progress monitor.  New prompt, activation, delayed or signal stages
may provide their own physics/source builder, but must emit a compatible
`generated/job_plan.json`, seed registry, source manifest and preflight, then
delegate process execution to `run.py` and monitoring to `progress.py`.

This decision standardizes execution mechanics only.  It does not merge or
weaken the candidate-own activation/inventory, exact-position delayed, focused
signal, response/veto, Step05 or mission-fold physics contracts.

## Canonical files

- `config.json`: candidate identity, authority paths, concurrency and resource
  policy.  A new candidate/profile must use a new generated root and run root.
- `common.py`: schema validation, job/seed/source/preflight interlock and bound
  receipt validation.
- `prepare.py`: the current SG3B corrected-keV background adapter.  Future
  stage adapters may be separate, but they must not copy the executor.
- `run.py`: production canary, controller lock, guarded Cosima subprocesses,
  whole-job retry, attempt isolation and write-once receipts.
- `progress.py`: read-only terminal dashboard based on state, receipt and text
  log tails.  It does not scan or digest SIM payloads.

## Required workflow

1. Set a new `profile_id`, generated root and run root; never point a new
   candidate at an earlier candidate's receipts or active directories.
2. Run the applicable stage-specific preparation and its static check.  For
   the present SG3B background adapter these are:

   ```bash
   python3 tool/execute/prepare.py --prepare
   python3 tool/execute/prepare.py --check
   ```

3. Start exactly one controller.  The file lock rejects a second controller:

   ```bash
   python3 tool/execute/run.py --workers 5
   ```

4. Monitor in a separate terminal:

   ```bash
   python3 tool/execute/progress.py
   ```

5. Count a job only when its canonical receipt is PASS and is bound to the
   current profile, job ID, candidate, mode/family, events, seed, source,
   setup, SIM-header evidence and existing attempt artifacts.  A stale or
   foreign receipt is fail-closed and is never silently counted.

## Safety and resource contract

- The stored default remains four workers; this SG3B recovery permits at most
  five by explicit user direction.  Never exceed `max_workers`.
- Admission includes free disk, MemAvailable, SwapFree and memory full-PSI.
  There is no fixed aggregate-RSS ceiling: launch and runtime safety use a
  1-GiB `MemAvailable` floor.  A resource breach sheds only the single largest
  relevant worker; it does not set controller-wide STOP or kill healthy jobs.
- A failed or interrupted attempt never contributes partial events.  Retry
  starts from event zero with the job's registered seed and a new attempt
  directory.
- SIM validation is header-only (at most 80 decompressed lines) for geometry
  and seed.  No full SIM scan or SIM digest is part of execution validation.
- A stale `active/` directory is not overwritten automatically.  Resolve its
  owning process and artifacts explicitly before a later controller restart.

The first SG3B production canary demonstrated a single-process peak RSS of
about 3.62 GB, and an instant e+ attempt later reached about 5.59 GiB.  At
2026-08-16T13:33Z the former 7.5-GiB aggregate cap incorrectly caused a global
stop.  That failed evidence is retained.  The recovery keeps the same profile,
source cards and seeds, disables that aggregate cap, and grants attempt03 only
to the affected n/e-/e+ jobs.  Every retry still starts at event zero.

## Current implementation boundary

The checked-in `prepare.py` and current config cover the 21 SG3B Plan-1
corrected-keV INSTANT/BUILDUP background jobs only.  They do not build
activation inventory, delayed sources, focused-signal jobs or downstream
paper analysis.  Those stages must preserve their own small authorities while
using this executor rather than cloning its process-management code.

## Chained extra-2x SG3B background profile

The non-overwriting follow-on profile is
`profiles/sg3b_plan1_extra2x_20260816_v1.json`.  Here "extra 2x" means a new
sample containing twice the Plan-1 background histories (2,561,386 INSTANT and
2,030,984 BUILDUP); combined with the first profile this yields 3x Plan-1
background histories.  It has its own generated root, run root and 21 fresh
seeds explicitly checked against the first SG3B registry.

`chain_after_complete.py` is the sequential gate.  It launches the extra-2x
profile only after the first controller records the matching profile as
COMPLETE with all 21 jobs and no active workers.  It then requires the full
estimated extra-2x artifact budget plus the 8-GiB reserve before re-running
preflight and replacing itself with the canonical runner.  The chain reads
small JSON authorities only and never opens, scans or hashes SIM payloads.
