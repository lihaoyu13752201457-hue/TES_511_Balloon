# SE3 Plan 1 approximately one-third transport

Status: `W2_SE3_ONLY_BACKGROUND_PRODUCTION_IN_PROGRESS`

This fresh, non-overwriting package executes the contract in:

`/home/ubuntu/.codex/worktrees/626c/TES_511_Balloon/engineering/geometry_optimization_20260815/46_se3_one_third_transport_handoff_20260815/SE3_ONE_THIRD_TRANSPORT_HANDOFF.md`

It is explicitly a `PLAN1_APPROX_ONE_THIRD_PHYSICS_SCREEN`, not full-stat or
publication-level transport authority and not an automatic geometry promotion.

The chain is candidate-owned: corrected-keV instant transport supplies prompt
background; corrected-keV buildup supplies SE3 production histories; those
histories are converted to a day-15 ground-state inventory and exact-position
delayed sources; delayed transport, prompt transport, and the SE3 full-envelope
signal transport then share one detector response, veto, W2, and Step05 policy.
The resulting selected rates are folded through the same 81-node, 20-day
mission scenario to obtain central and componentwise-proxy F3 values.

The user's 2026-08-15 scope correction forbids any S3d rerun.  S3d prompt,
activation, delayed, response, and mission inputs are read-only frozen small
tables.  The prepared S3d full-envelope signal card is explicitly excluded from
execution.  The retained S3d signal is post-Be-window only, so it is continuity
context rather than a fair full-envelope F3-ratio denominator.

Raw transport lives below:

`/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1`

The source and receipt workflow never re-hashes large SIM files.  Source cards,
plans, seeds, receipts, and small authority files receive one provenance digest;
SIM artifacts are identified by absolute path, byte count, source/header checks,
generated-event log evidence, and the receipt chain.

## Commands

```bash
python3 -B code/build_se3_sources.py
python3 -B code/run_se3_plan1.py --phase canary
python3 -B code/run_se3_plan1.py --phase remaining-background --cpu-budget 6
python3 -B code/validate_se3_receipts.py --stage background
```

The canary is the first `gamma instant / 267312` production shard and is credited
to the final statistics.  It must pass alone before any remaining background job
is admitted.
