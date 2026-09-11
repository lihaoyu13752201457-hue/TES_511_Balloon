# SE3/SF3 Plan-1 execution-code reference

This directory is a source-faithful review snapshot of the Python code used by
the completed SE3 and SF3 Plan-1 chains.  It is stored under `code/tools` so a
future candidate can be derived from the audited implementation without
modifying either historical package.

## Source packages

- `se3/` was copied byte-for-byte from:
  `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/geometry_optimization_20260815/47_se3_plan1_transport_20260815/code/`
- `sf3/` was copied byte-for-byte from the non-full-stat Plan-1 portion of:
  `/home/ubuntu/.codex/worktrees/ddb4/TES_511_Balloon/engineering/geometry_optimization_20260815/49_sf3_plan1_transport_20260816/code/`

The snapshot intentionally excludes `__pycache__`, SIM files, source cards,
job plans, seed registries, receipts, catalogs, and all SF3 `fullstat` scripts.
SF3 failed its Plan-1 promotion gate, so those full-stat scripts were prepared
templates rather than an executed SF3 simulation path.

## Execution model recovered from the code

1. Candidate-specific source builders create the corrected-keV background job
   plan and fresh seeds; the signal preparer binds the frozen 37,194-ray bank.
2. `run_*_plan1.py` acquires one controller lock, runs a production canary,
   schedules the remaining background jobs, and later transports candidate-own
   delayed sources and the fresh signal job.
3. Each Cosima attempt runs as `cosima -s <registered-seed> <source-card>` in an
   isolated process group.  The controller validates the DAT/SIM header,
   geometry, seed, generated histories, TT/RP metadata, and output size before
   publishing a write-once canonical receipt.
4. A failed or interrupted attempt is never credited.  A retry leaves the
   worker, re-enters disk/RSS admission, starts from event zero, and keeps the
   same registered seed; at most two attempt ordinals are allowed.
5. SE3 used an adaptive controller with a four-worker floor and guarded live
   expansion up to six.  SF3 retained the transport controller but its
   crash-safe follow-up executes heavy stages with four workers.
6. `run_sf3_plan1_followup.py` resumes from named canonical small authorities,
   never from its journal: background receipt validation -> prompt analysis ->
   candidate-own activation/delayed-source construction -> delayed transport
   and validation -> delayed analysis -> fresh signal transport and validation
   -> common response -> matched comparison -> mission -> final audit.
7. `guard_sf3_service_pressure.py` observes cgroup pressure, MemAvailable,
   SwapFree, and optional disk reserve.  It throttles the shared service CPU
   quota from 400% to 300% under pressure and restores 400% on clean exit; it
   never changes events, seeds, source cards, or physics statistics.

## Safety and reuse boundary

These files are a provenance/reference snapshot, not a portable run package.
They retain historical SE3/SF3 identities, absolute authority paths, volume
maps, status strings, and candidate-specific assertions.  Do not execute them
from this tools directory against a new candidate.

For a new candidate, copy the SF3 Plan-1 code into a new write-once candidate
package, then replace and audit the package/run roots, candidate/setup identity,
job/card/output prefixes, volume/material lineage, active/passive map, source
manifest, and globally fresh seeds.  Preserve the corrected source,
normalization, response, veto, retry, receipt, and mission contracts.  Start
with four workers; full-stat code remains unavailable until the candidate's
Plan-1 central gate passes.

## Review verification

The following synthetic self-tests passed during this review without opening
production SIM files or launching transport:

- `run_se3_plan1.py --self-test`
- `run_sf3_plan1.py --self-test`
- `run_sf3_plan1_followup.py --self-test`
- `guard_sf3_service_pressure.py --self-test`
- `validate_sf3_receipts.py --self-test`

