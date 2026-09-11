# SG3B corrected-keV background execution package

The execution mechanics in this directory are now the project's canonical
Cosima runner.  Read `HANDOFF.md` before adding a later transport stage.  New
stages may add source/plan preparation, but must reuse `run.py`, `common.py`
and `progress.py` instead of copying another multiprocessing controller.

This package does one job only: prepare and run the 21 SG3B Plan-1 cosmic-ray
background transports (INSTANT and BUILDUP) with four concurrent Cosima
processes and a read-only terminal dashboard.

It intentionally does not contain activation/inventory construction, delayed
transport, focused-signal transport, detector response, veto, Step05, mission
folding, or paper post-processing.  Those stages remain separate and may run
only after the background receipts are complete and audited.

## Files

- `config.json`: SG3B geometry, corrected source, statistics and resource gates.
- `common.py`: JSON/write-once/environment helpers plus strict plan,
  manifest/preflight and receipt identity binding.
- `prepare.py`: imports the eight-family corrected-keV source templates,
  creates fresh SG3B identities/seeds, writes 21 source cards and performs the
  static preflight.
- `run.py`: maximum-four-worker, resumable Cosima controller with a production
  canary, process-group termination, resource admission, event-zero whole-job
  retry, header/DAT validation and canonical receipts.
- `progress.py`: progress bars, event rate, ETA, RSS, memory, swap and disk.
  It reads active text-log tails and small receipts only; it does not scan or
  hash SIM payloads.

## Frozen scope

- Candidate: `DEMO2_DR_v3p5_SG3B`
- Source profile: `unit_only_total_gamma`
- Additive atmospheric mono-511: disabled
- Jobs: 21 background jobs only
- INSTANT histories: 1,280,693
- BUILDUP histories: 1,015,492
- Workers: 4 default, 5 maximum for the audited SG3B recovery
- Admission: disk, SwapFree, memory PSI and a 1-GiB MemAvailable floor; the
  former fixed aggregate-RSS ceiling is disabled
- Resource pressure: terminate only the largest relevant worker, never set a
  controller-wide STOP for healthy jobs
- Retry: two whole attempts by default; the retained 2026-08-16 resource-stop
  evidence authorizes attempt03 only for n/e-/e+.  Every retry uses the
  registered seed and starts from event zero

## Commands

```bash
python3 tool/execute/prepare.py --prepare
python3 tool/execute/prepare.py --check
python3 tool/execute/run.py --workers 5
python3 tool/execute/progress.py
```

Multiple non-overlapping profiles use an explicit config and separate
generated/run roots:

```bash
python3 tool/execute/prepare.py --config tool/execute/profiles/sg3b_plan1_extra2x_20260816_v1.json --check
python3 tool/execute/run.py --config tool/execute/profiles/sg3b_plan1_extra2x_20260816_v1.json --workers 5
python3 tool/execute/progress.py --config tool/execute/profiles/sg3b_plan1_extra2x_20260816_v1.json
```

`chain_after_complete.py` may gate the next profile on an exact COMPLETE state
and the full estimated artifact budget plus the configured disk reserve.  It
does not inspect SIM payloads.

Generated source cards and small manifests are written under
`tool/execute/generated/`.  Transport artifacts and receipts are written under
`runs/geometry_optimization_20260816/sg3b_plan1_background_v1/`.
